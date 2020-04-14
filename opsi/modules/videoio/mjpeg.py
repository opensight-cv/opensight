import asyncio
import logging
import queue
import re
from datetime import datetime
from pathlib import Path

import jinja2
from starlette.routing import Route, Router

from opsi.manager.manager_schema import Hook
from opsi.util.concurrency import AsyncThread, Snippet
from opsi.util.cv import Mat, Point
from opsi.util.networking import choose_port
from opsi.util.templating import LiteralTemplate

try:
    from opsi.manager.netdict import NetworkDict

    NT_AVAIL = True
except ImportError:
    NT_AVAIL = False

LOGGER = logging.getLogger(__name__)
logging.getLogger("asyncio").setLevel(logging.ERROR)

# -----------------------------------------------------------------------------
# Reusable ASGI framework

# Takes care of waiting to start sending
# Nice way to be peacefully notified when the client has left
# Usage: ```
#     async with ASGILifespan(receive) as lifespan:
#         # do your thing, and periodically, do
#         if lifespan.end:
#             # cleanup tasks
#             return
# ```
class ASGILifespan:
    def __init__(self, receive):
        self._receive = receive
        self._task = None

    @staticmethod
    def is_msg_start(message):
        return (message["type"] == "http.request") and (not message["more_body"])

    @staticmethod
    def is_msg_end(message):
        return message["type"] == "http.disconnect"

    # Blocks until it is time to start the response
    # Private, internal use only
    async def _task_start(self):
        while True:
            message = await self._receive()

            if self.is_msg_start(message) or self.is_msg_end(message):
                return

    # Blocks until it is time to end the response
    # Private, internal use only
    async def _task_end(self):
        while True:
            message = await self._receive()

            if self.is_msg_end(message):
                return

    # Blocks until it is time to end the response
    # Why would you use this, though?
    async def wait_end(self):
        if self.end:
            return
        await self._task

    # Returns True if it is time to end the response
    @property
    def end(self):
        if self._task is None:
            return True  # Invalid state
        return self._task.done()

    # Blocks until it is time to start the response
    async def __aenter__(self):
        await self._task_start()

        if self._task is None:
            self._task = asyncio.ensure_future(self._task_end())

        return self

    async def __aexit__(self, *exc_info):
        if self._task is not None:
            self._task.cancel()

        self._task = None


# Takes care of all headers, preamble, and postamble
# Usage: ```
#     async with ASGIApplication(receive, send) as app:
#         # do your thing, and periodically, do
#         if app.end:
#             # cleanup tasks
#             return
# ```
class ASGIApplication(ASGILifespan):
    def __init__(self, receive, send, *, status=200, headers={}):
        self._send = send

        self._status = status
        self._headers = headers

        super().__init__(receive)

    @staticmethod
    def _encode_bytes(val):
        return val.encode("latin-1")

    @classmethod
    def _convert_headers(cls, headers={}):
        return [
            (cls._encode_bytes(k), cls._encode_bytes(v)) for k, v in headers.items()
        ]

    async def send(self, data):
        await self._send(
            {"type": "http.response.body", "body": data, "more_body": True}
        )

    async def __aenter__(self):
        await super().__aenter__()

        await self._send(
            {
                "type": "http.response.start",
                "status": self._status,
                "headers": self._convert_headers(self._headers),
            }
        )

        return self

    async def __aexit__(self, *exc_info):
        await self._send({"type": "http.response.body"})

        return await super().__aexit__(*exc_info)


# Takes care of streaming with multipart/x-mixed-replace
# Usage: ```
#     async with ASGIStreamer(receive, send) as app:
#         # do your thing, and periodically, do
#         if app.end:
#             # cleanup tasks
#             return
# ```
class ASGIStreamer(ASGIApplication):
    def __init__(self, receive, send, *, boundary="frame", status=200, headers={}):
        self._boundary = self._encode_bytes(f"\r\n--{boundary}\r\n")

        headers["Content-Type"] = f"multipart/x-mixed-replace; boundary={boundary}"
        headers["Connection"] = "close"

        super().__init__(receive, send, status=status, headers=headers)

    async def send(self, data):
        try:
            await super().send(self._boundary + data)
        except (asyncio.CancelledError, RuntimeError):
            return


# -----------------------------------------------------------------------------


# An ASGI application that streams mjpeg from a jpg iterable
class MjpegResponse:
    HEADERS = ASGIApplication._encode_bytes("Content-Type: image/jpeg\r\n\r\n")

    def __init__(self, request, src):
        self.request = request
        self.src = src

    async def send_images(self, app, quality, fps, resolution):
        async for img in self.src.get_img(app, quality, fps, resolution):
            if img is None:
                break
            asyncio.create_task(app.send(self.HEADERS + img))

    def get_values(self):
        quality = 70
        fps = 30
        resolution = None
        try:
            quality = 100 - int(self.request.query_params.get("compression", 30))
            fps = int(self.request.query_params.get("fps", 30))
            resolution = self.request.query_params.get("resolution")
        except (TypeError, ValueError):
            LOGGER.error("Failed to parse URL parameters", exc_info=True)
        return quality, fps, resolution

    async def __call__(self, scope, receive, send):
        async with ASGIStreamer(receive, send) as app:
            quality, fps, resolution = self.get_values()
            self.src.thread.run_coro(self.send_images(app, quality, fps, resolution))
            while True:
                if app.end:
                    return
                if self.src._shutdown:
                    return
                try:
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    return


# -----------------------------------------------------------------------------


class CamHook(Hook):
    # Matches both "camera.mjpg" and "camera.mjpeg"
    ROUTE_URL = "/{func}.mjpe?g"  # Route to bind to
    STREAM_URL = "/{func}.mjpeg"  # Canonical path

    path = Path(__file__).parent
    with open(path / "mjpeg.html") as f:
        TEMPLATE = f.read()
    TEMPLATE = jinja2.Template(TEMPLATE)

    CAMERA_NAME = "OpenSight: {func}"
    CAMERA_URL_NT = f"mjpeg:{{url}}{STREAM_URL}?"
    CAMERA_URL_WEB = f"{{url}}{STREAM_URL}"

    def __init__(self):
        super().__init__()

        self.app = Router()
        if NT_AVAIL:
            self.netdict = NetworkDict("/CameraPublisher")
        self.funcs = {}  # {name: route}
        self.cams = {}  # {name: url}
        self.index_route = [Route("/", LiteralTemplate(self.TEMPLATE, cams=self.cams))]
        self.listeners = {"startup": set(), "shutdown": set(), "pipeline_update": set()}

        self._update()

    def _update(self):
        self.app.routes = self.index_route + list(self.funcs.values())

    def endpoint(self, func):
        def image(request):
            return MjpegResponse(request, func.src.src)

        return image

    def register(self, func):
        if func.id in self.funcs:
            raise ValueError("Cannot have duplicate name")

        self.funcs[func.id] = Route(
            self.ROUTE_URL.format(func=func.id), self.endpoint(func)
        )
        self.cams[func.id] = self.CAMERA_URL_WEB.format(url=self.url, func=func.id)
        self._update()

        # https://github.com/wpilibsuite/allwpilib/blob/ec9738245d86ec5a535a7d9eb22eadc78dee88b4/wpilibj/src/main/java/edu/wpi/first/wpilibj/CameraServer.java#L313
        if NT_AVAIL:
            ntdict = self.netdict.get_subtable(self.CAMERA_NAME.format(func=func.id))
            ntdict["streams"] = [self.CAMERA_URL_NT.format(url=self.url, func=func.id)]

    def unregister(self, func):
        try:
            del self.funcs[func.id]
            del self.cams[func.id]
        except KeyError:
            pass

        if NT_AVAIL:
            self.netdict.delete_table(self.CAMERA_NAME.format(func=func.id))

        self._update()


class MjpegCameraServer:
    def __init__(self):
        pass

    def run(self, inputs):
        pass

    def dispose(self):
        pass

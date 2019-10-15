import queue
import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import datetime

import re
import cv2
import jinja2
import numpy as np
from starlette.applications import Starlette
from starlette.routing import Route, Router

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.netdict import NetworkDict
from opsi.manager.types import Mat, Slide
from opsi.util.templating import LiteralTemplate
from opsi.util.concurrency import AsyncThread, ShutdownThread

__package__ = "demo.server"
__version__ = "0.123"

LOGGER = logging.getLogger(__name__)

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
        await super().send(self._boundary + data)


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
            await app.send(self.HEADERS + img)

    def get_values(self):
        quality = 100
        fps = 90
        resolution = None
        try:
            quality = 100 - int(self.request.query_params.get("compression", 0))
            fps = int(self.request.query_params.get("fps", 90))
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
                await asyncio.sleep(0.1)


# -----------------------------------------------------------------------------


class Hook(Hook):
    # Matches both "camera.mjpg" and "camera.mjpeg"
    ROUTE_URL = "/{func}.mjpe?g"  # Route to bind to
    STREAM_URL = "/{func}.mjpeg"  # Canonical path

    TEMPLATE = jinja2.Template(
        """
<html>
    <head>
        <title>CameraServer: {{ funcs|length }}</title>
    </head>
    <body>
        <h1>CameraServer</h1>
        <ul>
        {% for func in funcs %}
            <li><a href=".URL">{{ func }}</a></li>
        {% else %}
            <li>None</li>
        {% endfor %}
        </ul>
    </body>
</html>
""".replace(
            "URL", STREAM_URL.replace("{", "{{ ").replace("}", " }}")
        )  # {func} --> {{ func }}
    )

    CAMERA_NAME = "OpenSight: {func}"
    CAMERA_URL = f"mjpeg:{{url}}{STREAM_URL}?"

    def __init__(self):
        self.app = Router()
        self.netdict = NetworkDict("/CameraPublisher")
        self.funcs = {}  # {name: route}
        self.index_route = [
            Route("/", LiteralTemplate(self.TEMPLATE, funcs=self.funcs.keys()))
        ]

        self._update()

    def _update(self):
        self.app.routes = self.index_route + list(self.funcs.values())

    def endpoint(self, func):
        def image(request):
            return MjpegResponse(request, func.src)

        return image

    def register(self, func):
        self.funcs[func.id] = Route(
            self.ROUTE_URL.format(func=func.id), self.endpoint(func)
        )
        self._update()

        # https://github.com/wpilibsuite/allwpilib/blob/ec9738245d86ec5a535a7d9eb22eadc78dee88b4/wpilibj/src/main/java/edu/wpi/first/wpilibj/CameraServer.java#L313
        ntdict = self.netdict.get_subtable(self.CAMERA_NAME.format(func=func.id))
        ntdict["streams"] = [self.CAMERA_URL.format(url=self.url, func=func.id)]

    def unregister(self, func):
        try:
            del self.funcs[func.id]
        except KeyError:
            pass

        self.netdict.delete_table(self.CAMERA_NAME.format(func=func.id))
        self._update()


HookInstance = Hook()


class CameraSource:
    def __init__(self):
        self.queue = queue.Queue()
        self.thread = AsyncThread(timeout=0.5, name="CameraSource")
        self.events = []
        self._img = None
        self._shutdown = False

    @property
    def quality(self):
        return self._quality

    @quality.setter
    def quality(self, quality):
        self._quality = quality

    @property
    def img(self):
        return self._img

    @img.setter
    def img(self, img):
        self._img = img
        self.thread.run_coro(self.notify_generators())

    # return true if no time was spent waiting
    async def event_wait(self, event):
        while not event.is_set():
            if self._shutdown:
                return
            await asyncio.sleep(0.01)
        return

    async def event_clear_wait(self, event):
        while event.is_set():
            if self._shutdown:
                return
            await asyncio.sleep(0.01)
        return

    async def notify_generators(self):
        for e in self.events:
            e.set()
            await self.event_clear_wait(e)

    async def get_img(self, app, quality: int, fps_limit: int, resolution=None):
        event = threading.Event()
        self.events.append(event)

        res = None
        if resolution:
            m = re.search("(\d+)x(\d+)", resolution)
            try:
                res = (int(m.group(1)), int(m.group(2)))
            except (TypeError, AttributeError):
                LOGGER.debug("Invalid resolution", exc_info=True)

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        time = datetime.now()
        while True:
            await self.event_wait(event)

            # if not enough time has passed since last frame, wait until it has
            delay = 1 / fps_limit
            passed = (datetime.now() - time).total_seconds()
            if delay > passed:
                await asyncio.sleep(delay - passed)
                continue
            time = datetime.now()

            mat = self.img
            if mat is None:
                break

            if app.end:
                break

            if res:
                mat = cv2.resize(mat, res)
            img = cv2.imencode(".jpg", mat, encode_param)[1].tobytes()

            yield img
            event.clear()
        self.events.remove(event)

    def shutdown(self):
        self._shutdown = True
        self.img = None
        self.thread.shutdown()


class CameraServer(Function):
    has_sideeffect = True

    def on_start(self):
        self.src = CameraSource()
        HookInstance.register(self)

    @dataclass
    class Settings:
        name: str = "camera"

    @dataclass
    class Inputs:
        img: Mat

    def run(self, inputs):
        self.src.img = inputs.img
        return self.Outputs()

    def dispose(self):
        self.src.shutdown()
        HookInstance.unregister(self)

    # Returns a unique string for each CameraServer instance
    @property
    def id(self):
        return self.settings.name

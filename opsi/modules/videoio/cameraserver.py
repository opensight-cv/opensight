import asyncio
import logging
import queue
import re
from datetime import datetime

import jinja2
from starlette.routing import Route, Router

from opsi.manager.manager_schema import Hook
from opsi.util.concurrency import AsyncThread, Snippet
from opsi.util.cv import Mat, Point
from opsi.util.templating import LiteralTemplate

try:
    from opsi.manager.netdict import NetworkDict

    NT_AVAIL = True
except ImportError:
    NT_AVAIL = False

__package__ = "opsi.camserv"
__version__ = "0.123"

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
        except asyncio.CancelledError:
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
                try:
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    return


# -----------------------------------------------------------------------------


class CamHook(Hook):
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

    def __init__(self, visible=True):
        self.visible = visible
        self.app = Router()
        if NT_AVAIL:
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
        if func.id in self.funcs:
            raise ValueError("Cannot have duplicate name")

        self.funcs[func.id] = Route(
            self.ROUTE_URL.format(func=func.id), self.endpoint(func)
        )
        self._update()

        # https://github.com/wpilibsuite/allwpilib/blob/ec9738245d86ec5a535a7d9eb22eadc78dee88b4/wpilibj/src/main/java/edu/wpi/first/wpilibj/CameraServer.java#L313
        if NT_AVAIL:
            ntdict = self.netdict.get_subtable(self.CAMERA_NAME.format(func=func.id))
            ntdict["streams"] = [self.CAMERA_URL.format(url=self.url, func=func.id)]

    def unregister(self, func):
        try:
            del self.funcs[func.id]
        except KeyError:
            pass

        if NT_AVAIL:
            self.netdict.delete_table(self.CAMERA_NAME.format(func=func.id))

        self._update()


class CameraSource:
    def __init__(self):
        self.queue = queue.Queue()
        self.thread = AsyncThread(timeout=0.5, name="CameraSource")
        self.snippets = []
        self._img: Mat = None
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
        if self._shutdown:
            for snip in self.snippets:
                snip.run_abandon()  # run each snippet one last time to close request
            return
        self.thread.run_coro(self.notify_generators())

    async def notify_generators(self):
        for snip in self.snippets:
            try:
                await snip.run()
            except asyncio.CancelledError:
                return

    async def get_img(self, app, quality: int, fps_limit: int, resolution=None):
        snippet = Snippet()
        self.snippets.append(snippet)

        res = None
        if resolution:
            m = re.search("(\d+)x(\d+)", resolution)
            try:
                res = Point(int(m.group(1)), int(m.group(2)))
            except (TypeError, AttributeError):
                LOGGER.debug("Invalid resolution", exc_info=True)

        time = datetime.now()
        while True:

            await snippet.start()

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

            if app.end or self._shutdown:
                break

            if res:
                mat = mat.resize(res)
            img = mat.encode_jpg(quality)

            yield img

            snippet.done()
        snippet.done()

        self.snippets.remove(snippet)

    def shutdown(self):
        self._shutdown = True
        self.img = None
        self.thread.shutdown()

import asyncio
import threading
from dataclasses import dataclass

import cv2
import jinja2
import numpy as np
from starlette.applications import Starlette
from starlette.routing import Route, Router

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.netdict import NetworkDict
from opsi.manager.types import Mat, Slide
from opsi.util.templating import LiteralTemplate

__package__ = "demo.server"
__version__ = "0.123"


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

    def __init__(self, src):
        self.src = src

    async def __call__(self, scope, receive, send):
        async with ASGIStreamer(receive, send) as app:
            while True:
                async for img in self.src.get_img():
                    if img is None:
                        return
                    if app.end:
                        return
                    await app.send(self.HEADERS + img)


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
            return MjpegResponse(func.src)

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
    def __init__(self, quality, fps_limit):
        self.event = threading.Event()
        self._img = None
        self.mat = None
        self._shutdown = False

        self.fps_limit = fps_limit

        self.quality = quality

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
    def img(self, mat):
        if not np.array_equal(self.mat, mat):
            self.mat = mat
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
            self._img = cv2.imencode(".jpg", mat, encode_param)[1].tobytes()
            self.event.set()

    async def get_img(self):
        old = None
        while True:
            img = self.img
            if not np.array_equal(img, old):
                yield img
            old = img
            await asyncio.sleep(1 / self.fps_limit)

    def shutdown(self):
        self._shutdown = True


class CameraServer(Function):
    has_sideeffect = True

    def on_start(self):
        self.src = CameraSource(self.settings.quality, self.settings.fps_limit)
        HookInstance.register(self)

    @dataclass
    class Settings:
        name: str = "camera"
        quality: Slide(0, 100) = 100
        fps_limit: int = 90

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

import asyncio
from dataclasses import dataclass
from time import sleep

import cv2
import jinja2
from starlette.applications import Starlette
from starlette.routing import Route, Router
from starlette.templating import _TemplateResponse

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.types import Mat

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
                img = self.src.get_image()
                if img is None:
                    return
                if app.end:
                    return
                await app.send(self.HEADERS + self.src.get_image())
                await asyncio.sleep(0.015)


# -----------------------------------------------------------------------------


# Returns a unique string for each CameraServer instance
def func_id(func):
    return str(func.settings.name)


class Hook(Hook):
    TEMPLATE = jinja2.Template("""
<html>
    <head>
        <title>CameraServer: {{ funcs|length }}</title>
    </head>
    <body>
        <h1>CameraServer</h1>
        <ul>
        {% for func in funcs %}
            <li><a href="./{{ func }}.mjpg">{{ func }}</a></li>
        {% else %}
            <li>None</li>
        {% endfor %}
        </ul>
    </body>
</html>
""")

    def __init__(self):
        self.app = Router()
        self.index_route = [Route("/", self.index)]
        self.funcs = {}  # {name: route}

        self._update()

    def _update(self):
        self.app.routes = self.index_route + list(self.funcs.values())

    def index(self, request):
        return _TemplateResponse(
            self.TEMPLATE, {"request": request, "funcs": self.funcs.keys()}
        )

    def endpoint(self, func):
        def image(request):
            return MjpegResponse(func.src)

        return image

    def register(self, func):
        # The url "camera.mjpe?g" matches both "camera.mjpg" and "camera.mjpeg"
        self.funcs[func_id(func)] = Route(
            "/" + func_id(func) + ".mjpe?g", self.endpoint(func)
        )
        self._update()

    def unregister(self, func):
        del self.funcs[func_id(func)]
        self._update()


HookInstance = Hook()


class CameraSource:
    def __init__(self):
        self.image = None

    def get_image(self):
        return self.image

    def set_image(self, mat):
        self.image = cv2.imencode(".jpg", mat)[1].tobytes()


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
        self.src.set_image(inputs.img)
        return self.Outputs()

    def dispose(self):
        HookInstance.unregister(self)

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import BaseModel

from opsi.util.cv import Point

LOGGER = logging.getLogger(__name__)
# logging.getLogger("asyncio").setLevel(logging.ERROR)

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

    def __init__(self, request, camserv):
        self.request = request
        self.camserv = camserv

    class Params(BaseModel):
        compression: int = 30
        fps: int = 30
        resolution: Point = None

    def get_params(self):
        query = dict(self.request.query_params)

        # parse resolution (in format XXxYY)
        res = query.get("resolution")
        if res:
            try:
                r = res.split("x")
                query["resolution"] = Point(int(r[0]), int(r[1]))
            except (ValueError, AttributeError):
                LOGGER.error("Invalid resolution: %s", res)
                query["resolution"] = None

        params = self.Params.parse_obj(query)
        return params

    async def __call__(self, scope, receive, send):
        # call app.send(self.HEADERS + frame) to send frame
        sink = self.camserv.src.src
        params = self.get_params()
        async with ASGIStreamer(receive, send) as app:
            while True:
                if app.end or sink.end:
                    return
                time = sink.next_frame_time(params.fps)

                if not sink.pendingFrame:
                    await asyncio.sleep(0.01)
                    continue

                frame = sink.frame
                res = params.resolution
                if res:
                    frame = frame.resize(res)
                frame = frame.encode_jpg(100 - params.compression)

                await app.send(self.HEADERS + frame)
                if time > 0:
                    await asyncio.sleep(time)


# -----------------------------------------------------------------------------


class Sink:
    def __init__(self):
        self.pendingFrame = False
        self.lastTime = datetime.now()
        self.end = False

        self._frame = None

    @property
    def frame(self):
        self.lastTime = datetime.now()
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame
        self.pendingFrame = True

    def next_frame_time(self, fps):
        return (
            (self.lastTime + timedelta(seconds=1 / fps)) - datetime.now()
        ).total_seconds()

    def dispose(self):
        self.end = True


class MjpegCameraServer:
    def __init__(self):
        self.src = Sink()

    def run(self, inputs):
        self.src.frame = inputs.img

    def dispose(self):
        self.src.dispose()

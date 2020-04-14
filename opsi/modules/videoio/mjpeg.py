import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import BaseModel

from opsi.util.asgi import ASGIStreamer
from opsi.util.cv import Point

LOGGER = logging.getLogger(__name__)
# logging.getLogger("asyncio").setLevel(logging.ERROR)


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

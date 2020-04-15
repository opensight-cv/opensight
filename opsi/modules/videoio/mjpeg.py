import asyncio
import logging
from datetime import datetime, timedelta
from typing import Tuple

from pydantic import BaseModel, Field, ValidationError, validator

from opsi.util.asgi import ASGIStreamer
from opsi.util.cv import Point

LOGGER = logging.getLogger(__name__)


class Params(BaseModel):
    @validator("compression", "fps", pre=True)
    def parse_float_str(cls, v):
        # typically, with a field of type int,
        #    30    -> 30
        #   "30"   -> 30
        #    30.9  -> 30
        #   "30.9" -> error
        # this fixes that

        try:
            return int(v)
        except ValueError:
            return int(float(v.strip("'\"")))

    @validator("resolution", pre=True)
    def parse_resolution(cls, v):
        # parse "widthXheight" str to ("width", "height") tuple

        if v is None:
            return v

        return v.lower().split("x")

    @validator("resolution")
    def convert_resolution(cls, v):
        # convert Tuple[int, int] to Point

        if v is None or isinstance(v, Point):
            return v

        w, h = int(v[0]), int(v[1])

        if not (w > 0 and h > 0):
            raise ValueError("Must be positive resolution")

        return Point(w, h)

    @classmethod
    def create(cls, query=None):
        if query is None or not len(query):
            return cls()

        try:
            return cls.parse_obj(query)
        except ValidationError as e:
            # remove the broken keys, keep the working ones
            # {"fps": "foobar", "compression": 10} -> Params(compression=10, fps=default, ...)

            query = dict(query)  # original query is immutable

            for error in e.errors():
                try:
                    key = error["loc"][0]
                    value = query.pop(key)
                    LOGGER.info("Ignoring invalid argument: %r = %r", key, value)
                except KeyError:  # multiple errors in same key
                    pass

            try:
                return cls.parse_obj(query)
            except ValidationError:
                return cls()

    compression: int = Field(30, ge=0, le=100)
    fps: int = Field(30, gt=0)
    resolution: Tuple[int, int] = None  # actually type: Point


# An ASGI application that streams mjpeg from a jpg iterable
class MjpegResponse:
    HEADERS = ASGIStreamer._encode_bytes("Content-Type: image/jpeg\r\n\r\n")

    def __init__(self, request, camserv):
        self.request = request
        self.camserv = camserv

    async def __call__(self, scope, receive, send):
        # call app.send(self.HEADERS + frame) to send frame
        sink = self.camserv.src.src
        query = dict(self.request.query_params)
        params = Params.create(query)

        # LOGGER.debug("Parsed params: %r -> %r", query, params)

        async with ASGIStreamer(receive, send) as app:
            while True:
                if app.end or sink.end:
                    return

                if not sink.pendingFrame:
                    await asyncio.sleep(0.01)
                    continue

                frame = sink.frame
                res = params.resolution
                if res:
                    frame = frame.resize(res)
                frame = frame.encode_jpg(100 - params.compression)
                await app.send(self.HEADERS + frame)

                time = sink.next_frame_time(params.fps)
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

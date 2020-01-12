import datetime
from dataclasses import dataclass

import cv2
import numpy as np

from opsi.manager.manager_schema import Function
from opsi.util.cv import Mat


class FPS:
    def __init__(self):
        self._start = None
        self._end = None
        self._numFrames = 0

    def start(self):
        self._start = datetime.datetime.now()
        return self

    def end(self):
        self._end = datetime.datetime.now()

    def update(self):
        self._numFrames += 1

    def elapsed(self):
        return (datetime.datetime.now() - self._start).total_seconds()

    def fps(self):
        return self._numFrames / self.elapsed()


class DrawFPS(Function):
    force_enabled = True

    def on_start(self):
        self.f = FPS()
        self.f.start()

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        self.f.update()
        fps_str = str(round(self.f.fps(), 1))
        draw = np.copy(inputs.img.mat.img)
        cv2.putText(
            draw,
            fps_str,
            (30, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            lineType=cv2.LINE_AA,
        )
        draw = Mat(draw)
        return self.Outputs(img=draw)

from dataclasses import dataclass

import cv2
import numpy as np

import opsi.modules.fps as fps
from opsi.manager.manager_schema import Function
from opsi.manager.types import Contours, Mat, MatBW

__package__ = "opsi.draw"
__version__ = "0.123"


class DrawContours(Function):
    @dataclass
    class Inputs:
        contours: Contours
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        draw = np.copy(inputs.img.mat)
        cv2.drawContours(draw, inputs.contours, -1, (255, 255, 0), 3)
        draw = draw.view(Mat)
        return self.Outputs(img=draw)


class DrawFPS(Function):
    def on_start(self):
        self.f = fps.FPS()
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
        img = cv2.putText(
            inputs.img.mat,
            fps_str,
            (30, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            lineType=cv2.LINE_AA,
        ).view(Mat)
        return self.Outputs(img=img)


class BitwiseAND(Function):
    @dataclass
    class Inputs:
        img: Mat
        mask: MatBW

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = cv2.bitwise_and(inputs.img.mat, inputs.img.mat, mask=inputs.mask.matBW).view(Mat)
        return self.Outputs(img=img)

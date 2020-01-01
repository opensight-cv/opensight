from dataclasses import dataclass

import numpy as np

import cv2
from opsi.manager.manager_schema import Function
from opsi.manager.types import Contours, Mat, MatBW

from .fps import DrawFPS
from .shapes import DrawCircles

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


class BitwiseAND(Function):
    @dataclass
    class Inputs:
        img: Mat
        mask: MatBW

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = cv2.bitwise_and(
            inputs.img.mat, inputs.img.mat, mask=inputs.mask.matBW
        ).view(Mat)
        return self.Outputs(img=img)

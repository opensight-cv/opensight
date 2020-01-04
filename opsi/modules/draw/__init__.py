from dataclasses import dataclass

import cv2
import numpy as np

from opsi.manager.manager_schema import Function
from opsi.manager.types import Contours, Mat, MatBW

from .fps import DrawFPS
from .shapes import DrawCircles, DrawSegments

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
        draw = np.copy(inputs.img.mat.img)
        cv2.drawContours(draw, inputs.contours, -1, (255, 255, 0), 3)
        draw = Mat(draw)
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
        img = inputs.img.mat.img
        mask = inputs.mask.matBW.img

        out = Mat(cv2.bitwise_and(np.copy(img), img, mask))

        return self.Outputs(img=out)

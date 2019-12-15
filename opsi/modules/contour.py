import math
from dataclasses import dataclass

import numpy as np
import cv2
from opsi.manager.manager_schema import Function
from opsi.manager.types import Contours, Mat, MatBW, Point, Slide

__package__ = "opsi.contours"
__version__ = "0.123"


class FindContours(Function):
    @dataclass
    class Inputs:
        imgBW: MatBW

    @dataclass
    class Outputs:
        contours: Contours

    def run(self, inputs):
        contours = Contours.from_img(inputs.imgBW)
        return self.Outputs(contours=contours)


class ConvexHulls(Function):
    @dataclass
    class Inputs:
        contours: Contours

    @dataclass
    class Outputs:
        contours: Contours

    def run(self, inputs):
        contours = inputs.contours.convex_hulls
        return self.Outputs(contours=contours)


class ContourApproximate(Function):
    @dataclass
    class Settings:
        epsilon: Slide(0, 1)

    @dataclass
    class Inputs:
        contours: Contours

    @dataclass
    class Outputs:
        contours: Contours

    def run(self, inputs):
        contours = inputs.contours.approximate(self.settings.epsilon)
        return self.Outputs(contours=contours)


class FindCenter(Function):
    @dataclass
    class Settings:
        draw: bool

    @dataclass
    class Inputs:
        contours: Contours
        img: Mat

    @dataclass
    class Outputs:
        center: ()
        visual: Mat
        success: bool

    def run(self, inputs):
        if len(inputs.contours.l) == 0:
            return self.Outputs(center=(), success=False, visual=inputs.img)

        center = inputs.contours.centroid_of_all

        if self.settings.draw:
            img = np.copy(inputs.img.mat.img)

            for contour in inputs.contours.l:
                cv2.circle(img, contour.centroid, 5, (0, 0, 255), 3)

            cv2.circle(img, center, 10, (255, 0, 0), 5)

        normalized = inputs.contours.res.normalize(center)

        return self.Outputs(center=normalized, success=True, visual=draw)


class FindAngle(Function):
    disabled = True

    @dataclass
    class Settings:
        draw: bool

    @dataclass
    class Inputs:
        pnt: ()
        img: Mat

    @dataclass
    class Outputs:
        angle: int
        visual: Mat

    def run(self, inputs):
        width = inputs.img.shape[1] // 2
        height = inputs.img.shape[0] // 2
        x = inputs.pnt[0]
        y = inputs.pnt[1]
        delta = (width - x, height - y)
        deg = math.degrees(math.atan2(delta[1], delta[0]))
        draw = None
        if self.settings.draw:
            draw = np.copy(inputs.img)
            line = cv2.line(draw, (width, height), (x, y), (0, 255, 0), 2)
            return self.Outputs(angle=deg, visual=line)
        else:
            return self.Outputs(angle=deg, visual=(draw or inputs.img))

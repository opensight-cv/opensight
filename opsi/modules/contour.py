import math
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np

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
        center: Point
        visual: Mat
        success: bool

    def run(self, inputs):
        if len(inputs.contours.l) == 0:
            return self.Outputs(center=None, success=False, visual=inputs.img)

        center = inputs.contours.centroid_of_all

        if self.settings.draw:
            img = np.copy(inputs.img.mat.img)

            for contour in inputs.contours.l:
                cv2.circle(img, contour.centroid, 5, (0, 0, 255), 3)

            cv2.circle(img, center, 10, (255, 0, 0), 5)

        normalized = inputs.contours.res.normalize(center)

        return self.Outputs(center=normalized, success=True, visual=img)


class FindAngle(Function):
    @classmethod
    @lru_cache(maxsize=2 ** 4)  # cache once for each set of params
    def calculate_focal_length(cls, diagonalFOV, horizontalAspect, verticalAspect):
        # Thanks Peter for making ChickenVision
        # https://github.com/team3997/ChickenVision/blob/4587503a2c524c6149620b7ba6dc245a19d85436/ChickenVision.py#L155

        diagonalView = math.radians(diagonalFOV)

        # Reasons for using diagonal aspect is to calculate horizontal field of view.
        diagonalAspect = math.hypot(horizontalAspect, verticalAspect)
        # Calculations: http://vrguy.blogspot.com/2013/04/converting-diagonal-field-of-view-and.html
        horizontalView = (
            math.atan(math.tan(diagonalView / 2) * (horizontalAspect / diagonalAspect))
            * 2
        )
        # verticalView = math.atan(math.tan(diagonalView/2) * (verticalAspect / diagonalAspect)) * 2

        # Since point is -1 <= (x, y) <= 1: width, height = 2; center = (0, 0)

        # Focal Length calculations: https://docs.google.com/presentation/d/1ediRsI-oR3-kwawFJZ34_ZTlQS2SDBLjZasjzZ-eXbQ/pub?start=false&loop=false&slide=id.g12c083cffa_0_165
        H_FOCAL_LENGTH = 2 / (2 * math.tan((horizontalView / 2)))
        # V_FOCAL_LENGTH = 2 / (2*math.tan((verticalView/2)))

        return H_FOCAL_LENGTH

    @dataclass
    class Settings:
        diagonalFOV: float = 68.5

    @dataclass
    class Inputs:
        pnt: Point
        img: Mat

    @dataclass
    class Outputs:
        radians: float

    def run(self, inputs):
        width = inputs.img.shape[1]
        height = inputs.img.shape[0]

        center_x = 0
        x = inputs.point[0]

        H_FOCAL_LENGTH = self.calculate_focal_length(
            self.settings.diagonalFOV, width, height
        )
        radians = math.atan2(x, H_FOCAL_LENGTH)

        return self.Outputs(radians=radians)

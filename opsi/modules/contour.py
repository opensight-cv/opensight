import math
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np

import opsi.manager.cvwrapper as cvw
from opsi.manager.manager_schema import Function
from opsi.manager.types import Contours, Mat, MatBW

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
        contours = cvw.find_contours(inputs.imgBW)
        return self.Outputs(contours=contours)


class ConvexHulls(Function):
    @dataclass
    class Inputs:
        contours: Contours

    @dataclass
    class Outputs:
        contours: Contours

    def run(self, inputs):
        contours = cv2.convex_hulls(inputs.contours)
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
        midpoint = None
        offset = None
        draw = None
        cnt = None
        mids = []
        if len(inputs.contours) == 0:
            return self.Outputs(center=(), success=False, visual=inputs.img)
        for i in range(len(inputs.contours)):
            cnt = inputs.contours[i]
            x, y, w, h = cv2.boundingRect(cnt)
            cx = (x + (x + w)) // 2
            cy = (y + (y + h)) // 2
            midpoint = (cx, cy)
            mids.append(midpoint)
            draw = inputs.img.mat
            if self.settings.draw:
                draw = np.copy(inputs.img.mat)
                cv2.rectangle(draw, (x, y), (x + w, y + h), (234, 234, 0), thickness=2)
                cv2.circle(draw, midpoint, 10, (0, 0, 255), 3)
                if len(mids) > 1:
                    mid1 = mids[0]
                    mid2 = mids[-1]
                    mx = (mid1[0] + mid2[0]) // 2
                    my = (mid1[1] + mid2[1]) // 2
                    midpoint = (mx, my)
                    cv2.circle(draw, midpoint, 15, (90, 255, 255), 3)
                    cv2.line(draw, mid1, mid2, (0, 255, 20), thickness=3)
            imgh, imgw, _ = inputs.img.shape
            imgh, imgw = (imgh // 2, imgw // 2)

            offset = (imgw - midpoint[0], imgh - midpoint[1])
            normalized = (offset[0] / -imgw, offset[1] / -imgh)
        return self.Outputs(center=normalized, success=True, visual=draw)


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
        point: ()
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

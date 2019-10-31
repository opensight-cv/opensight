import math
from dataclasses import dataclass

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
        contours = cvw.convex_hulls(inputs.contours)
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

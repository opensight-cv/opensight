import math
from dataclasses import dataclass

import cv2
import numpy as np

import opsi.manager.cvwrapper as cvw
import opsi.modules.fps as fps
from opsi.manager.manager_schema import Function
from opsi.manager.types import Contours, Mat, MatBW, RangeType, Slide

__package__ = "opsi.cv"
__version__ = "0.123"


class Blur(Function):
    @dataclass
    class Settings:
        radius: int

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = cvw.blur(inputs.img, self.settings.radius)
        return self.Outputs(img=img)


class HSVRange(Function):
    @dataclass
    class Settings:
        hue: RangeType(0, 179, decimal=True)
        sat: RangeType(0, 255, decimal=True)
        val: RangeType(0, 255, decimal=True)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        imgBW: MatBW

    def run(self, inputs):
        imgBW = cvw.hsv_threshold(
            inputs.img, self.settings.hue, self.settings.sat, self.settings.val
        )
        return self.Outputs(imgBW=imgBW)


class Erode(Function):
    @dataclass
    class Settings:
        size: int

    @classmethod
    def validate_settings(cls, settings):
        if settings.size < 0:
            raise ValueError("Size cannot be negative")

        return settings

    @dataclass
    class Inputs:
        imgBW: MatBW

    @dataclass
    class Outputs:
        imgBW: MatBW

    @classmethod
    def _impl(cls, imgBW, size):
        return cvw.erode(imgBW, size)

    def run(self, inputs):
        imgBW = self._impl(inputs.imgBW, self.settings.size)
        return self.Outputs(imgBW=imgBW)


class Dilate(Erode):
    @classmethod
    def _impl(cls, imgBW, size):
        return cvw.dilate(imgBW, size)


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


class DrawContours(Function):
    @dataclass
    class Inputs:
        contours: Contours
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        draw = np.copy(inputs.img)
        cv2.drawContours(draw, inputs.contours, -1, (255, 255, 0), 3)
        return self.Outputs(img=draw)


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
            draw = inputs.img
            if self.settings.draw:
                draw = np.copy(inputs.img)
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


class BitwiseAND(Function):
    @dataclass
    class Inputs:
        img: Mat
        mask: MatBW

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = cv2.bitwise_and(inputs.img, inputs.img, mask=inputs.mask)
        return self.Outputs(img=img)


class ConvexHulls(Function):
    @dataclass
    class Inputs:
        contours: Contours

    @dataclass
    class Outputs:
        contours: Contours

    def run(self, inputs):
        contours = [cv2.convexHull(contour) for contour in inputs.contours]
        return self.Outputs(contours=contours)


class MatBWToMat(Function):
    @dataclass
    class Inputs:
        imgBW: MatBW

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = cv2.cvtColor(inputs.imgBW, cv2.COLOR_GRAY2BGR)
        return self.Outputs(img=img)


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
            inputs.img,
            fps_str,
            (30, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            lineType=cv2.LINE_AA,
        )
        return self.Outputs(img=img)

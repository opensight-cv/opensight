from dataclasses import dataclass

import cv2

import opsi.manager.cvwrapper as cvw
from opsi.manager.manager_schema import Function
from opsi.manager.types import Mat, MatBW, Contours

ERODE_DILATE_CONSTS = {
    "kernel": None,
    "anchor": (-1, -1),
    "borderType": cv2.BORDER_CONSTANT,
    "borderValue": -1,
}

FIND_CONTOURS_CONSTS = {"mode": cv2.RETR_LIST, "method": cv2.CHAIN_APPROX_SIMPLE}

__package__ = "demo.cv"
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
        blurred: Mat

    def run(self, inputs):
        blurredImg = cvw.blur(inputs.img, self.settings.radius)
        return self.Outputs(blurred=blurredImg)


class HSLThreshold(Function):
    @dataclass
    class Settings:
        hue: int
        sat: int
        lum: int

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: MatBW

    def run(self, inputs):
        ranges = tuple(zip(self.settings.hue, self.settings.lum, self.settings.sat))
        thresh = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HLS), *ranges)
        return self.Outputs(img=thresh)


class Erode(Function):
    @dataclass
    class Settings:
        size: int

    @dataclass
    class Inputs:
        img: MatBW

    @dataclass
    class Outputs:
        eroded: MatBW

    def run(self, inputs):
        eroded = cv2.erode(
            inputs.img, interations=round(self.settings.size), **ERODE_DILATE_CONSTS
        )
        return self.Outputs(eroded=eroded)


class Dilate(Function):
    @dataclass
    class Settings:
        size: int

    @dataclass
    class Inputs:
        img: MatBW

    @dataclass
    class Outputs:
        dilated: MatBW

    def run(self, inputs):
        dilated = cv2.dilate(
            inputs.img, iterations=round(self.settings.size), **ERODE_DILATE_CONSTS
        )
        return self.Outputs(dilated=dilated)


class FindContours(Function):
    @dataclass
    class Settings:
        draw: bool

    @dataclass
    class Inputs:
        img: MatBW

    @dataclass
    class Outputs:
        contours: Contours
        visual: MatBW

    def run(self, inputs):
        vals = cv2.findContours(inputs.img, **FIND_CONTOURS_CONSTS)
        if self.settings.draw:
            cv2.drawContours(inputs.mat, vals, -1, (255, 255, 255), 3)
        if OPENCV3:
            return self.Outputs(contours=vals[1], visual=inputs.img)
        else:
            return self.Outputs(contours=vals[0], visual=inputs.img)

class FindCenter(Function):
    @dataclass
    class Settings:
        draw: bool

    @dataclass
    class Inputs:
        contours: Contours
        img: MatBW

    @dataclass
    class Outputs:
        center: int
        visual: MatBW

    def run(self, inputs):
        for cnt in inputs.contours:
            x, y, w, h = cv2.boundingRect(cnt)
            cx = (x + (x + w)) // 2
            cy = (y + (y + h)) // 2
            midpoint = (cx, cy)
            if self.settings.draw:
                cv2.circle(inputs.img, midpoint, (255, 255, 255), 3)
        return self.Outputs(center=midpoint, visual=inputs.img)


class ConvexHulls(Function):
    @dataclass
    class Inputs:
        contours: Contours

    @dataclass
    class Outputs:
        contours: Contours

    def run(self, inputs):
        conts = [cv2.convexHull(contour) for contour in inputs.contours]
        return self.Outputs(contours=conts)


class MatBWToMat(Function):
    @dataclass
    class Inputs:
        img: MatBW

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        return self.Outputs(img=cv2.cvtColor(inputs.img, cv2.COLOR_GRAY2BGR))

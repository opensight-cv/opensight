from dataclasses import dataclass

import numpy as np

import opsi.manager.cvwrapper as cvw
from opsi.manager.manager_schema import Function
from opsi.manager.types import Mat, MatBW, RangeType, Slide

__package__ = "opsi.colorops"
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
        hue: RangeType(0, 359)
        sat: RangeType(0, 255)
        val: RangeType(0, 255)

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


class Greyscale(Function):
    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = cvw.greyscale(inputs.img)
        return self.Outputs(img=img)


class Canny(Function):
    @dataclass
    class Settings:
        threshold: RangeType(0, 255)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        imgBW: MatBW

    def run(self, inputs):
        return self.Outputs(
            imgBW=cvw.canny(
                inputs.img, self.settings.threshold[0], self.settings.threshold[1]
            )
        )


class AbsoluteDifferenceRGB(Function):
    @dataclass
    class Settings:
        red: Slide(min=0, max=255, decimal=False)
        green: Slide(min=0, max=255, decimal=False)
        blue: Slide(min=0, max=255, decimal=False)
        to_greyscale: bool
        clamp_max: bool
        clamp_value: Slide(min=0, max=255, decimal=False)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        diff = cvw.abs_diff(
            inputs.img,
            np.array(
                [self.settings.blue, self.settings.green, self.settings.red],
                dtype=np.float,
            )[None],
        ).view(Mat)

        if self.settings.to_greyscale:
            diff = cvw.greyscale(diff)

        if self.settings.clamp_max:
            diff = np.minimum(diff, self.settings.clamp_value)

        return self.Outputs(img=diff)


class AbsoluteDifferenceHSV(Function):
    @dataclass
    class Settings:
        hue: Slide(min=0, max=359, decimal=False)
        hue_sensitivity: int
        sat: Slide(min=0, max=255, decimal=False)
        sat_sensitivity: int
        val: Slide(min=0, max=255, decimal=False)
        val_sensitivity: int
        clamp_max: bool
        clamp_value: Slide(min=0, max=255, decimal=False)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img_hsv = cvw.bgr_to_hsv(inputs.img)
        diff_hsv = cvw.abs_diff(
            inputs.img,
            np.array(
                [self.settings.hue, self.settings.sat, self.settings.val],
                dtype=np.float,
            )[None],
        ).view(Mat)

        scaled_diff = np.multiply(
            diff_hsv,
            np.array(
                [
                    self.settings.hue_sensitivity,
                    self.settings.sat_sensitivity,
                    self.settings.val_sensitivity,
                ],
                dtype=np.uint16,
            ),
        ).astype(np.uint16)

        greyscale = cvw.greyscale(scaled_diff)

        if self.settings.clamp_max:
            greyscale = np.minimum(greyscale, self.settings.clamp_value).astype(
                np.uint8
            )
        else:
            greyscale = np.minimum(greyscale, 255).astype(np.uint8)

        return self.Outputs(img=greyscale)


class ClampMax(Function):
    @dataclass
    class Settings:
        max_value: Slide(min=0, max=255, decimal=False)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        return self.Outputs(img=np.minimum(inputs.img, self.settings.max_value))


class ClampMin(Function):
    @dataclass
    class Settings:
        min_value: Slide(min=0, max=255, decimal=False)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        return self.Outputs(img=np.maximum(inputs.img, self.settings.min_value))

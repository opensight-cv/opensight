from dataclasses import dataclass

import cv2
import numpy as np

from opsi.manager.manager_schema import Function
from opsi.manager.types import Color, Mat, MatBW, RangeType, Slide

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
        img = inputs.img.blur(self.settings.radius)
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
        imgBW = inputs.img.hsv_threshold(
            self.settings.hue, self.settings.sat, self.settings.val
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
        img = inputs.img.mat.greyscale
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
            imgBW=inputs.img.canny(
                self.settings.threshold[0], self.settings.threshold[1]
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
        diff = inputs.img.abs_diff(
            np.array(
                [self.settings.blue, self.settings.green, self.settings.red],
                dtype=np.float,
            )[None],
        )

        if self.settings.to_greyscale:
            diff = diff.greyscale

        if self.settings.clamp_max:
            diff = Mat(np.minimum(diff.img, self.settings.clamp_value))

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
        img_hsv = inputs.img.hsv
        # cvw.bgr_to_hsv(inputs.img)
        diff_hsv = img_hsv.abs_diff(
            np.array(
                [self.settings.hue, self.settings.sat, self.settings.val],
                dtype=np.float,
<<<<<<< HEAD
            )[
                None
            ],  # [None] adds a dimension to the ndarray object created by np.array() -
            # See https://stackoverflow.com/questions/37867354/in-numpy-what-does-selection-by-none-do
        )
=======
            )[None],  # [None] adds a dimension to the ndarray object created by np.array() -
            # See https://stackoverflow.com/questions/37867354/in-numpy-what-does-selection-by-none-do
        ).view(Mat)
>>>>>>> Added ColorSampler node

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

        greyscale = Mat(scaled_diff).greyscale

        if self.settings.clamp_max:
            greyscale = Mat(
                np.minimum(greyscale.img, self.settings.clamp_value).astype(np.uint8)
            )
        else:
            greyscale = Mat(np.minimum(greyscale.img, 255).astype(np.uint8))

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


class ColorSampler(Function):
    @dataclass
    class Settings:
        x: int
        y: int
        draw_point: bool

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        color: Color
        img: Mat

    def run(self, inputs):
        draw = None
        if self.settings.draw_point:
            draw = np.copy(inputs.img.mat)
            # Draw a small circle (of radius 5) to show the point.
            cv2.circle(draw, (self.settings.x, self.settings.y), 5, (0, 0, 255), 3)
            draw = draw.view(Mat)

        return self.Outputs(color=inputs.img[self.settings.y, self.settings.x], img=draw)

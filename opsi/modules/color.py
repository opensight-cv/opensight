from dataclasses import dataclass

import cv2
import numpy as np

from opsi.manager.manager_schema import Function
from opsi.manager.types import RangeType, Slide
from opsi.util.cv import Mat, MatBW
from opsi.util.cv.mat import Color
from opsi.util.cv.shape import Point

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
        img = inputs.img.mat.blur(self.settings.radius)
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
        imgBW = inputs.img.mat.hsv_threshold(
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
            imgBW=inputs.img.mat.canny(
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
        diff = inputs.img.mat.abs_diff(
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
        img_hsv = inputs.img.mat.hsv
        diff_hsv = img_hsv.abs_diff(
            np.array(
                [self.settings.hue, self.settings.sat, self.settings.val],
                dtype=np.float,
            )[
                None
            ],  # [None] adds a dimension to the ndarray object created by np.array() -
            # See https://stackoverflow.com/questions/37867354/in-numpy-what-does-selection-by-none-do
        )

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
        x_pct: Slide(min=0, max=100)
        y_pct: Slide(min=0, max=100)
        draw_color: bool
        draw_hsv: bool

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        color: Color
        img: Mat

    def run(self, inputs):
        # Find the pixel coordinates to sample in the image
        height, width = inputs.img.mat.img.shape[:2]

        sample_coords = (
            int(width * self.settings.x_pct / 100.0 + 10),
            int(height * self.settings.y_pct / 100.0 + 10),
        )
        color_bgr = inputs.img.mat.img[sample_coords[1], sample_coords[0]]
        draw = inputs.img.mat
        if self.settings.draw_color:
            draw = np.copy(inputs.img.mat.img)
            # Draw a small circle (of radius 5) to show the point.
            cv2.circle(draw, sample_coords, 5, (0, 0, 255), 3)

            # Find the color in HSV to make a contrasting color
            color_hsv = Mat(np.uint8([[color_bgr]])).img[0][0]

            color_hsv[0] *= 2  # Scale the hue value to be in a range of 0-359

            # Create a string to represent the color in either RGB or HSV
            if self.settings.draw_hsv:
                color_str = "H{} S{} V{}".format(*color_hsv)
            else:
                color_str = "B{} G{} R{}".format(*color_bgr)

            # Choose a (Hopefully) Contrasting color
            draw_color = (
                int(255 - color_bgr[0]),
                int(255 - color_bgr[1]),
                int(255 - color_bgr[2]),
            )

            cv2.putText(
                draw,
                color_str,
                (sample_coords[0] + 10, sample_coords[1] + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                draw_color,
                lineType=cv2.LINE_AA,
            )

            draw = Mat(draw)

        color = Color(color_bgr[2], color_bgr[1], color_bgr[0])
        return self.Outputs(color=color, img=draw)


class ColorDetector(Function):
    @dataclass
    class Settings:
        red_hue: Slide(min=0, max=359, decimal=False)
        yellow_hue: Slide(min=0, max=359, decimal=False)
        green_hue: Slide(min=0, max=359, decimal=False)
        blue_hue: Slide(min=0, max=359, decimal=False)

    @dataclass
    class Inputs:
        color: Color

    @dataclass
    class Outputs:
        color_string: str

    def run(self, inputs):
        def hue_dist(test: int, reference: int):
            return min(abs(reference - test), abs(reference + 360 - test))

        color_hue = (
            Mat(
                np.uint8([[[inputs.color.blue, inputs.color.green, inputs.color.red]]])
            ).hsv.img[0][0][0]
            * 2
        )

        hue_strings = {
            self.settings.red_hue: "R",
            self.settings.yellow_hue: "Y",
            self.settings.green_hue: "G",
            self.settings.blue_hue: "B",
        }

        output_str = ""

        min_dist = 360

        for hue in hue_strings.keys():
            dist = hue_dist(hue, color_hue)
            if dist < min_dist:
                min_dist = dist
                output_str = hue_strings[hue]

        return self.Outputs(color_string=output_str)


class Resize(Function):
    @dataclass
    class Settings:
        width: int
        height: int

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = inputs.img.mat.resize(Point(self.settings.width, self.settings.height))
        return self.Outputs(img=img)


class ColorBalance(Function):
    @dataclass
    class Settings:
        red_balance: Slide(min=0, max=100)
        blue_balance: Slide(min=0, max=100)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = inputs.img.mat.color_balance(
            self.settings.red_balance / 100.0, self.settings.blue_balance / 100.0
        )
        return self.Outputs(img=img)

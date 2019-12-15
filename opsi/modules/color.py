from dataclasses import dataclass

import opsi.util.cv._wrappers as cvw
from opsi.manager.manager_schema import Function
from opsi.manager.types import Mat, MatBW, RangeType

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

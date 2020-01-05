from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.types import RangeType

from opsi.util.cv import Mat, MatBW

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

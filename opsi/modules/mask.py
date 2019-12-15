from dataclasses import dataclass

import opsi.util.cv._wrappers as cvw
from opsi.manager.manager_schema import Function
from opsi.manager.types import MatBW

__package__ = "opsi.mask"
__version__ = "0.123"


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


class Invert(Function):
    @dataclass
    class Inputs:
        imgBW: MatBW

    @dataclass
    class Outputs:
        imgBW: MatBW

    def run(self, inputs):
        imgBW = cvw.invert(inputs.imgBW)
        return self.Outputs(imgBW=imgBW)


class Join(Function):
    @dataclass
    class Inputs:
        imgBW1: MatBW
        imgBW2: MatBW

    @dataclass
    class Outputs:
        imgBW: MatBW

    def run(self, inputs):
        imgBW = cvw.joinBW(inputs.imgBW1, inputs.imgBW2)
        return self.Outputs(imgBW=imgBW)

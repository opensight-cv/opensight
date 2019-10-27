from dataclasses import dataclass

import opsi.manager.cvwrapper as cvw
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

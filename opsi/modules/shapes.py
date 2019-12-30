from dataclasses import dataclass

import opsi.manager.cvwrapper as cvw
from opsi.manager.manager_schema import Function
from opsi.manager.types import Circles, Mat, MatBW, RangeType

__package__ = "opsi.shapeops"
__version__ = "0.123"


class FindCircles(Function):
    @dataclass
    class Settings:
        dp: int
        min_dist: int
        param: RangeType(0, 255)
        min_radius: int
        max_radius: int

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        circles: Circles

    def run(self, inputs):
        return self.Outputs(
            circles=cvw.hough_circles(
                inputs.img,
                self.settings.dp,
                self.settings.min_dist,
                self.settings.param,
                self.settings.min_radius,
                self.settings.max_radius,
            )
        )

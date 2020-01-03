from dataclasses import dataclass

import opsi.manager.cvwrapper as cvw
from opsi.manager.manager_schema import Function
from opsi.manager.types import Circles, Mat, MatBW, RangeType, Segments

__package__ = "opsi.shapeops"
__version__ = "0.123"


class FindCircles(Function):
    @dataclass
    class Settings:
        resolution_divisor: int
        min_dist: int
        edge_detection_threshold: RangeType(0, 255)
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
                self.settings.resolution_divisor,
                self.settings.min_dist,
                self.settings.edge_detection_threshold,
                self.settings.min_radius,
                self.settings.max_radius,
            )
        )


class FindLines(Function):
    @dataclass
    class Settings:
        resolution_divisor: int
        threshold: int
        min_length: int
        max_gap: int

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        segments: Segments

    def run(self, inputs):
        return self.Outputs(
            segments=cvw.hough_lines(
                inputs.img,
                self.settings.resolution_divisor,
                self.settings.threshold,
                self.settings.min_length,
                self.settings.max_gap,
            )
        )

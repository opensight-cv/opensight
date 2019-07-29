from dataclasses import dataclass

from hbll.backend.manager_schema import Function
from hbll.backend.types import RangeType

__package__ = "demo.seven"
__version__ = "0.123"


class IsInRange(Function):
    @dataclass
    class Settings:
        range: RangeType(0, 100)

    @dataclass
    class Inputs:
        num: float

    @dataclass
    class Outputs:
        in_range: bool

    def run(self, inputs):
        in_range = self.settings.range.min <= inputs.num <= self.settings.range.max

        return self.Outputs(in_range=in_range)

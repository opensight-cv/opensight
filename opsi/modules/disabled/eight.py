from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.types import Slide
from opsi.util.cv import Point

__package__ = "demo.eight"


class TupleTest(Function):
    @dataclass
    class Settings:
        val1: Slide(0, 10)
        val2: Slide(0, 10)

    @dataclass
    class Outputs:
        value: ()

    def run(self, inputs):
        return self.Outputs(value=(self.settings.val1, self.settings.val2))


class PointTest(Function):
    @dataclass
    class Settings:
        val1: Slide(0, 10)
        val2: Slide(0, 10)

    @dataclass
    class Outputs:
        value: Point

    def run(self, inputs):
        return self.Outputs(value=Point(self.settings.val1, self.settings.val2))

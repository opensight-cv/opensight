from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.types import Slide


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

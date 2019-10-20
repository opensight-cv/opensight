from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.netdict import NetworkDict
from opsi.manager.types import AnyType

__package__ = "demo.nt"
__version__ = "0.123"


class PutNT(Function):
    def on_start(self):
        self.table = NetworkDict(self.settings.path)

    @dataclass
    class Settings:
        path: str = "/OpenSight"
        key: str = ""

    @dataclass
    class Inputs:
        val: AnyType

    def run(self, inputs):
        self.table[self.settings.key] = inputs.val

        return self.Outputs()


class PutCoordinate(PutNT):
    @dataclass
    class Inputs:
        val: tuple()

    def run(self, inputs):
        x, y, *_ = inputs.val

        self.table[f"{self.settings.key}-x"] = x
        self.table[f"{self.settings.key}-y"] = y

        return self.Outputs()

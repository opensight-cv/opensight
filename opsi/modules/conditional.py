from dataclasses import dataclass

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.types import AnyType

__package__ = "opsi.conditional"
__version__ = "0.123"

HookInstance = Hook(visible=False)


class Switch(Function):
    def on_start(self):
        self.last = None

    @dataclass
    class Settings:
        enable: bool

    @dataclass
    class Inputs:
        thru: AnyType

    @dataclass
    class Outputs:
        out: AnyType = None

    def run(self, inputs):
        if self.settings.enable:
            self.last = inputs.thru
            return self.Outputs(out=inputs.thru)
        HookInstance.cancel_dependents()
        return self.Outputs(out=self.last)

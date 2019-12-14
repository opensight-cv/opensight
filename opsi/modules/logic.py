from dataclasses import dataclass

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.types import AnyType

__package__ = "opsi.logic"
__version__ = "0.123"

HookInstance = Hook(visible=False)


class Switch(Function):
    @dataclass
    class Settings:
        state: bool

    @dataclass
    class Inputs:
        thru: AnyType

    @dataclass
    class Outputs:
        on: AnyType = None
        off: AnyType = None

    def run(self, inputs):
        if self.settings.state:
            HookInstance.cancel_output("off")
            return self.Outputs(on=inputs.thru)
        HookInstance.cancel_output("on")
        return self.Outputs(off=inputs.thru)

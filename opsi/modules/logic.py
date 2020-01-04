from dataclasses import dataclass

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.types import AnyType

__package__ = "opsi.logic"
__version__ = "0.123"

HookInstance = Hook(visible=False)


class Freeze(Function):
    @dataclass
    class Settings:
        freeze: bool

    @dataclass
    class Inputs:
        thru: AnyType

    @dataclass
    class Outputs:
        out: AnyType = None

    def run(self, inputs):
        if not self.settings.freeze:
            return self.Outputs(out=inputs.thru)
        HookInstance.cancel_dependents()
        return self.Outputs()

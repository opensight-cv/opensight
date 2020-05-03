from dataclasses import dataclass

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.types import AnyType

__package__ = "opsi.logic"
__version__ = "0.123"

HookInstance = Hook()


class Toggle(Function):
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
        HookInstance.cancel_current()
        return self.Outputs()


class Freeze(Function):
    @dataclass
    class Inputs:
        thru: AnyType
        freeze: bool

    @dataclass
    class Outputs:
        out: AnyType = None

    def run(self, inputs):
        if not inputs.freeze:
            return self.Outputs(out=inputs.thru)
        HookInstance.cancel_current()
        return self.Outputs()


class If(Function):
    @dataclass
    class Inputs:
        input: int

    @dataclass
    class Settings:
        operation: ("=", "≠", ">", "<", "≥", "≤") = "="
        value: int = 0

    @dataclass
    class Outputs:
        boolean: bool = False

    def run(self, inputs):
        out = False
        if self.settings.operation == "=":
            out = inputs.input == self.settings.value
        elif self.settings.operation == "≠":
            out = inputs.input != self.settings.value
        elif self.settings.operation == ">":
            out = inputs.input > self.settings.value
        elif self.settings.operation == "<":
            out = inputs.input < self.settings.value
        elif self.settings.operation == "≥":
            out = inputs.input >= self.settings.value
        elif self.settings.operation == "≤":
            out = inputs.input <= self.settings.value
        return self.Outputs(boolean=out)


class SwitchBoolean(Function):
    @dataclass
    class Inputs:
        thru0: AnyType
        thru1: AnyType
        switch: bool = False

    @dataclass
    class Outputs:
        thru: AnyType = None

    def run(self, inputs):
        if inputs.switch:
            return self.Outputs(thru=inputs.thru1)
        return self.Outputs(thru=inputs.thru0)


class SwitchNumber(Function):
    @dataclass
    class Inputs:
        thru0: AnyType
        thru1: AnyType
        thru2: AnyType
        thru3: AnyType
        num: int = 0

    @dataclass
    class Outputs:
        thru: AnyType

    def run(self, inputs):
        out = [inputs.thru0, inputs.thru1, inputs.thru2, inputs.thru3][int(inputs.num)]
        return self.Outputs(thru=out)


class NOP(Function):
    @dataclass
    class Outputs:
        nop: AnyType = None

    def run(self, inputs):
        return self.Outputs(nop=None)

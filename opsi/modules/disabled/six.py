import random
from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.types import AnyType

__package__ = "demo.six"
__version__ = "0.123"


class Boolean(Function):
    @dataclass
    class Settings:
        val: bool

    @dataclass
    class Outputs:
        val: bool

    def run(self, inputs):
        return self.Outputs(val=self.settings.val)


class Number(Function):
    @dataclass
    class Settings:
        val: int

    @dataclass
    class Outputs:
        val: int

    def run(self, inputs):
        return self.Outputs(val=self.settings.val)


class String(Function):
    @dataclass
    class Settings:
        val: str

    @dataclass
    class Outputs:
        val: str

    def run(self, inputs):
        return self.Outputs(val=self.settings.val)


class ToString(Function):
    @dataclass
    class Inputs:
        number: int

    @dataclass
    class Outputs:
        string: str

    def run(self, inputs):
        return self.Outputs(string=str(inputs.number))


class Concat(Function):
    @dataclass
    class Inputs:
        str1: str
        str2: str

    @dataclass
    class Outputs:
        out: str

    def run(self, inputs):
        return self.Outputs(out=(inputs.str1 + inputs.str2))


class Add(Function):
    @dataclass
    class Inputs:
        num1: int
        num2: int

    @dataclass
    class Outputs:
        sum: int

    def run(self, inputs):
        return self.Outputs(sum=(inputs.num1 + inputs.num2))


class Subtract(Function):
    @dataclass
    class Inputs:
        num1: int
        num2: int

    @dataclass
    class Outputs:
        difference: int

    def run(self, inputs):
        return self.Outputs(difference=(inputs.num1 - inputs.num2))


class Multiply(Function):
    @dataclass
    class Inputs:
        num1: int
        num2: int

    @dataclass
    class Outputs:
        product: int

    def run(self, inputs):
        return self.Outputs(product=(inputs.num1 * inputs.num2))


class Divide(Function):
    @dataclass
    class Inputs:
        num1: int
        num2: int

    @dataclass
    class Outputs:
        quotient: int

    def run(self, inputs):
        return self.Outputs(quotient=(inputs.num1 / inputs.num2))


class Random(Function):
    @dataclass
    class Outputs:
        val: str

    def run(self, inputs):
        return self.Outputs(val=str(random.random()))


class Print(Function):
    has_sideeffect = True

    @dataclass
    class Inputs:
        val: AnyType

    def run(self, inputs):
        print(f"Print node: {str(inputs.val)}")

        return self.Outputs()

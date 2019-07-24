from dataclasses import dataclass

from hbll.backend.manager_schema import Function

__package__ = "demo.five"
__version__ = "0.123"


class Five(Function):
    @dataclass
    class Outputs:
        five: int

    def run(self, inputs):
        return self.Outputs(five=5)


class Sum(Function):
    @dataclass
    class Inputs:
        num1: int
        num2: int

    @dataclass
    class Outputs:
        out: int

    def run(self, inputs):
        out = inputs.num1 + inputs.num2

        return self.Outputs(out=out)


class Multiply(Function):
    @dataclass
    class Inputs:
        num1: int
        num2: int

    @dataclass
    class Outputs:
        product: int

    def run(self, inputs):
        product = inputs.num1 * inputs.num2

        return self.Outputs(product=product)


class Print(Function):
    has_sideeffect = True

    @dataclass
    class Inputs:
        val: int

    def run(self, inputs):
        print(f"Print node: {inputs.val}")

        return self.Outputs()

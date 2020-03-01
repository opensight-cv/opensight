from dataclasses import dataclass

import gpiozero

from opsi.manager.manager_schema import Function

__package__ = "opsi.gpio"
__version__ = "0.123"


class LED(Function):
    has_sideeffect = True

    def on_start(self):
        self.LED = gpiozero.LED(self.settings.pin)

    @dataclass
    class Settings:
        pin: int

    @dataclass
    class Inputs:
        on: bool

    def run(self, inputs):
        if int(inputs.on) != self.LED.value:
            self.LED.value = int(inputs.on)
        return self.Outputs()


class PWMLED(LED):
    has_sideeffect = True

    def on_start(self):
        self.LED = gpiozero.PWMLED(self.settings.pin)

from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.types import Slide
from opsi.util.cv.mat import Mat

__package__ = "opsi.imageops"
__version__ = "0.123"


class Rotate(Function):
    @dataclass
    class Settings:
        angle: Slide(0, 360)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = inputs.img.mat.rotate(self.settings.angle)
        return self.Outputs(img=img)


class RotateNoCrop(Function):
    @dataclass
    class Settings:
        angle: Slide(0, 360)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = inputs.img.mat.rotate_no_crop(self.settings.angle)
        return self.Outputs(img=img)


class Flip(Function):
    @dataclass
    class Settings:
        flipHorizontally: bool
        flipVertically: bool

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        img = inputs.img

        if self.settings.flipHorizontally:
            img = img.flip_horizontally()

        if self.settings.flipVertically:
            img = img.flip_vertically()

        return self.Outputs(img)

from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.types import RangeType
from opsi.util.cv import Mat, MatBW
from opsi.util.cv.cuda.wrappers import (
    CudaBlurWrapper,
    CudaGreenMinusRedWrapper,
    CudaThresholdAndBlurWrapper,
    CudaThresholdWrapper,
)

__package__ = "opsi.gpu"
__version__ = "0.123"


class ThresholdGPU(Function):
    def on_start(self):
        self.gpu_thresh = CudaThresholdWrapper(*self.lower_upper_from_settings())

    @dataclass
    class Settings:
        hue: RangeType(0, 255)
        sat: RangeType(0, 255)
        val: RangeType(0, 255)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: MatBW

    def lower_upper_from_settings(self):
        lower = (self.settings.hue[0], self.settings.sat[0], self.settings.val[0])
        upper = (self.settings.hue[1], self.settings.sat[1], self.settings.val[1])
        return lower, upper

    def run(self, inputs):
        if inputs.img is None:  # Do not write None values to NT
            return self.Outputs()

        lower, upper = self.lower_upper_from_settings()
        self.gpu_thresh.update_kernel(lower, upper)

        processed = self.gpu_thresh.apply(inputs.img.img)

        return self.Outputs(MatBW(processed))


class BlurGPU(Function):
    def on_start(self):
        self.gpu_blur = CudaBlurWrapper(self.settings.radius)

    @dataclass
    class Settings:
        radius: int = 3

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        if inputs.img is None:  # Do not write None values to NT
            return self.Outputs()

        self.gpu_blur.update_radius(self.settings.radius)

        processed = self.gpu_blur.apply(inputs.img.img)

        return self.Outputs(Mat(processed))


class BlurAndThreshold(Function):
    def on_start(self):
        lower, upper = self.lower_upper_from_settings()
        self.gpu_blur_thresh = CudaThresholdAndBlurWrapper(
            lower, upper, self.settings.blur_radius
        )

    @dataclass
    class Settings:
        hue: RangeType(0, 359)
        sat: RangeType(0, 255)
        val: RangeType(0, 255)
        blur_radius: int = 3

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: MatBW

    def lower_upper_from_settings(self):
        lower = (self.settings.hue[0], self.settings.sat[0], self.settings.val[0])
        upper = (self.settings.hue[1], self.settings.sat[1], self.settings.val[1])
        return lower, upper

    def run(self, inputs):
        if inputs.img is None:  # Do not write None values to NT
            return self.Outputs()

        lower, upper = self.lower_upper_from_settings()
        self.gpu_blur_thresh.update_kernel(lower, upper)
        self.gpu_blur_thresh.update_radius(self.settings.blur_radius)

        processed = self.gpu_blur_thresh.apply(inputs.img.img)

        return self.Outputs(MatBW(processed))


class GreenMinusRed(Function):
    def on_start(self):
        self.gpu_thresh = CudaGreenMinusRedWrapper(self.settings.threshold)

    @dataclass
    class Settings:
        threshold: int = 100

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: MatBW

    def run(self, inputs):
        if inputs.img is None:
            return self.Outputs()

        self.gpu_thresh.update_kernel(self.settings.threshold)

        processed = self.gpu_thresh.apply(inputs.img.img)

        return self.Outputs(MatBW(processed))

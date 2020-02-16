from dataclasses import dataclass
import math
import cupy as cp
import numpy as np
from opsi.manager.manager_schema import Function
from opsi.manager.types import RangeType

from opsi.util.cv import Mat, MatBW

__package__ = "opsi.gpu"
__version__ = "0.123"

DIM_BLOCK = 32


class ThresholdGPU(Function):
    def on_start(self):
        self.gpu_thresh = CudaThresholdWrapper()

    @dataclass
    class Settings:
        hue: RangeType(0, 359)
        sat: RangeType(0, 255)
        val: RangeType(0, 255)

    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: MatBW

    def run(self, inputs):
        if inputs.img is None:  # Do not write None values to NT
            return self.Outputs()

        lower = (self.settings.hue[0], self.settings.sat[0], self.settings.val[0])
        upper = (self.settings.hue[1], self.settings.sat[1], self.settings.val[1])

        processed = self.gpu_thresh.apply(inputs.img.img, lower, upper)

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


class CudaThresholdWrapper:
    def __init__(self):
        self.cuda_module = cp.RawModule(code=open('./opsi_cuda/threshold.cu').read())
        self.apply_filter = self.cuda_module.get_function("applyFilter")

    def apply(self, source_array, lower, upper):
        red_channel = cp.asarray(source_array[:, :, 0])  # TODO Make work for greyscale images
        green_channel = cp.asarray(source_array[:, :, 1])
        blue_channel = cp.asarray(source_array[:, :, 2])

        height, width = source_array.shape[:2]

        result_array = cp.empty((height, width, 1), dtype=cp.uint8)

        dim_grid_x = math.ceil(width / DIM_BLOCK)
        dim_grid_y = math.ceil(height / DIM_BLOCK)

        self.apply_filter(
                (dim_grid_x, dim_grid_y),
                (DIM_BLOCK, DIM_BLOCK),
                (
                    red_channel, green_channel, blue_channel,
                    result_array,
                    cp.uint32(width),
                    cp.uint32(height),
                    lower[0], upper[0],
                    lower[1], upper[1],
                    lower[2], upper[2]
                )
            )

        return cp.asnumpy(result_array)


class CudaBlurWrapper:
    def __init__(self, radius):
        self.cuda_module = cp.RawModule(code=open('./opsi_cuda/gaussian.cu').read())
        self.apply_filter = self.cuda_module.get_function("applyFilter")

        self.radius = radius
        self.make_kernel(radius)

    def update_radius(self, radius):
        if self.radius != radius:
            self.radius = radius
            self.make_kernel(radius)

    # Create gaussian kernel for blurring
    def make_kernel(self, radius):
        self.radius = radius
        self.filter_width = radius * 2 + 1

        # Crazy math below
        sigma = 0.3 * ((self.filter_width - 1) * 0.5 - 1) + 0.8

        gaussian_kernel = cp.empty((self.filter_width, self.filter_width), np.float32)
        kernel_half_width = self.filter_width // 2
        for i in range(-kernel_half_width, kernel_half_width + 1):
            for j in range(-kernel_half_width, kernel_half_width + 1):
                gaussian_kernel[i + kernel_half_width][j + kernel_half_width] = (
                        np.exp(-(i ** 2 + j ** 2) / (2 * sigma ** 2))
                        / (2 * np.pi * sigma ** 2)
                )

        # Normalize the kernel so that its sum is 1
        self.gaussian_kernel = gaussian_kernel / gaussian_kernel.sum()

    def apply(self, source_array):
        result_array = np.empty_like(source_array)
        red_channel = cp.asarray(source_array[:, :, 0])  # TODO Make work for greyscale images
        green_channel = cp.asarray(source_array[:, :, 1])
        blue_channel = cp.asarray(source_array[:, :, 2])

        height, width = source_array.shape[:2]

        dim_grid_x = math.ceil(width / DIM_BLOCK)
        dim_grid_y = math.ceil(height / DIM_BLOCK)

        for channel in (red_channel, green_channel, blue_channel):
            self.apply_filter(
                (dim_grid_x, dim_grid_y),
                (DIM_BLOCK, DIM_BLOCK),
                (
                    channel,
                    channel,
                    cp.uint32(width),
                    cp.uint32(height),
                    self.gaussian_kernel,
                    cp.uint32(self.filter_width)
                )
            )

        result_array[:, :, 0] = cp.asnumpy(red_channel)
        result_array[:, :, 1] = cp.asnumpy(green_channel)
        result_array[:, :, 2] = cp.asnumpy(blue_channel)

        return result_array

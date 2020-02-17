import math

import cupy as cp
import numpy as np

DIM_BLOCK = 32

cuda_rgb2hsv = cp.ElementwiseKernel(
    'uint8 r, uint8 g, uint8 b',
    'uint8 h, uint8 s, uint8 v',
    '''
    unsigned char rgbMin, rgbMax;

    rgbMin = r < g ? (r < b ? r : b) : (g < b ? g : b);
    rgbMax = r > g ? (r > b ? r : b) : (g > b ? g : b);

    v = rgbMax;
    if (v == 0)
    {
        h = 0;
        s = 0;
        return;
    }

    s = 255 * long(rgbMax - rgbMin) / v;
    if (s == 0)
    {
        h = 0;
        return;
    }

    if (rgbMax == r)
        h = 0 + 43 * (g - b) / (rgbMax - rgbMin);
    else if (rgbMax == g)
        h = 85 + 43 * (b - r) / (rgbMax - rgbMin);
    else
        h = 171 + 43 * (r - g) / (rgbMax - rgbMin);

    
    ''',
    'rgb2hsv'
)


class CudaThresholdWrapper:
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper
        self.cuda_kernel = self.compile_kernel(lower, upper)

    def update_kernel(self, lower, upper):
        if lower != self.lower or upper != self.upper:
            self.lower = lower
            self.upper = upper
            self.cuda_kernel = self.compile_kernel(lower, upper)

    def compile_kernel(self, lower, upper):
        return cp.ElementwiseKernel(
            'uint8 r, uint8 g, uint8 b',
            'uint8 out',
            f'if(r >= {lower[0]} && r <= {upper[0]} && g >= {lower[1]} && g <= {upper[1]} && b >= {lower[2]} && b <= {upper[2]}) {{ out = 255; }} else {{ out = 0; }}',
            'threshold'
        )

    def apply(self, source_array):
        blue_channel = cp.asarray(source_array[:, :, 0])  # TODO Make work for greyscale images
        green_channel = cp.asarray(source_array[:, :, 1])
        red_channel = cp.asarray(source_array[:, :, 2])

        hue_channel, sat_channel, val_channel = cuda_rgb2hsv(red_channel, green_channel, blue_channel)

        result_array = self.cuda_kernel(hue_channel, sat_channel, val_channel)

        return cp.asnumpy(result_array)


class CudaBlurWrapper:
    def __init__(self, radius):
        self.cuda_module = cp.RawModule(code=open('./opsi/util/cv/cuda/gaussian.cu').read())
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
        # Numpy array to store the output
        result_array = np.empty_like(source_array)

        # Split image into channels as cupy (GPU) arrays
        red_channel = cp.asarray(source_array[:, :, 0])  # TODO Make work for greyscale images
        green_channel = cp.asarray(source_array[:, :, 1])
        blue_channel = cp.asarray(source_array[:, :, 2])

        # Determine parameters for CUDA Blur
        height, width = source_array.shape[:2]

        dim_grid_x = math.ceil(width / DIM_BLOCK)
        dim_grid_y = math.ceil(height / DIM_BLOCK)

        # Blur each channel of the image
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

        # Convert the results back to a single numpy array
        result_array[:, :, 0] = cp.asnumpy(red_channel)
        result_array[:, :, 1] = cp.asnumpy(green_channel)
        result_array[:, :, 2] = cp.asnumpy(blue_channel)

        return result_array


class CudaThresholdAndBlurWrapper:
    def __init__(self, lower, upper, radius):
        self.lower = lower
        self.upper = upper
        self.cuda_kernel = self.compile_kernel(lower, upper)
        self.cuda_module = cp.RawModule(code=open('./opsi/util/cv/cuda/gaussian.cu').read())
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

    def update_kernel(self, lower, upper):
        if lower != self.lower or upper != self.upper:
            self.lower = lower
            self.upper = upper
            self.cuda_kernel = self.compile_kernel(lower, upper)

    def compile_kernel(self, lower, upper):
        return cp.ElementwiseKernel(
            'uint8 r, uint8 g, uint8 b',
            'uint8 out',
            f'if(r >= {lower[0]} && r <= {upper[0]} && g >= {lower[1]} && g <= {upper[1]} && b >= {lower[2]} && b <= {upper[2]}) {{ out = 255; }} else {{ out = 0; }}',
            'threshold'
        )

    def apply(self, source_array):
        # Split image into channels as cupy (GPU) arrays
        blue_channel = cp.asarray(source_array[:, :, 0])
        green_channel = cp.asarray(source_array[:, :, 1])
        red_channel = cp.asarray(source_array[:, :, 2])

        # Determine parameters for CUDA Blur
        height, width = source_array.shape[:2]

        dim_grid_x = math.ceil(width / DIM_BLOCK)
        dim_grid_y = math.ceil(height / DIM_BLOCK)

        # Blur each channel of the image
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

        # Convert RGB to HSV
        hue_channel, sat_channel, val_channel = cuda_rgb2hsv(red_channel, green_channel, blue_channel)

        # Threshold the image
        result_array = self.cuda_kernel(hue_channel, sat_channel, val_channel)

        # Convert back to numpy array
        return cp.asnumpy(result_array)

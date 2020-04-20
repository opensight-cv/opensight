extern "C" {
__global__ void applyFilter(const unsigned char* inputChannel,
                            unsigned char* outputChannel,
                            const unsigned int width, const unsigned int height,
                            const unsigned int filterWidth) {
    unsigned int y;
    unsigned int x;
    unsigned int blur;
    int filterHalf;
    unsigned int row = threadIdx.y + blockIdx.y * blockDim.y;
    unsigned int col = threadIdx.x + blockIdx.x * blockDim.x;
    if (row < height && col < width) {
        // Unwrapped/optimized versions for small filters
        if (filterWidth == 1) {  // 1x1 filter (Do nothing)
            outputChannel[col + row * width] = inputChannel[col + row * width];
            return;
        } else if (filterWidth == 3 && row > 0 && row < height - 1 && col > 0 &&
                   col < width - 1) {  // 3x3 filter
            blur = 0;
            blur += inputChannel[col + 1 + row * width + width];
            blur += inputChannel[col + 1 + row * width];
            blur += inputChannel[col + 1 + row * width - width];
            blur += inputChannel[col + row * width + width];
            blur += inputChannel[col + row * width];
            blur += inputChannel[col + row * width - width];
            blur += inputChannel[col - 1 + row * width + width];
            blur += inputChannel[col - 1 + row * width];
            blur += inputChannel[col - 1 + row * width - width];
            outputChannel[col + row * width] = blur / 9;
        }

        filterHalf = filterWidth / 2;
        blur = 0;
        for (int i = -filterHalf; i <= filterHalf; i++) {
            for (int j = -filterHalf; j <= filterHalf; j++) {
                y = max(0, min(height - 1, row + i));
                x = max(0, min(width - 1, col + j));
                blur += inputChannel[x + y * width];
            }
        }
        outputChannel[col + row * width] = blur / (filterWidth * filterWidth);
    }
}
}
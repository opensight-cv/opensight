extern "C"{
__global__ void applyFilter(const unsigned char *inputChannel, unsigned char *outputChannel,
                             const unsigned int width, const unsigned int height,
                             const float *gaussianKernel, const unsigned int filterWidth) {
    const unsigned int row = threadIdx.y + blockIdx.y * blockDim.y;
    const unsigned int col = threadIdx.x + blockIdx.x * blockDim.x;
    if(row < height && col < width) {
        const int filterHalf = filterWidth / 2;
        float blur = 0.0;
        for(int i = -filterHalf; i <= filterHalf; i++) {
            for(int j = -filterHalf; j <= filterHalf; j++) {
                const unsigned int y = max(0, min(height - 1, row + i));
                const unsigned int x = max(0, min(width - 1, col + j));

                const float w = gaussianKernel[(j + filterHalf) + (i + filterHalf) * filterWidth];
                blur += w * inputChannel[x + y * width];
            }
        }
        outputChannel[col + row * width] = static_cast<unsigned char>(blur);
    }
}
}
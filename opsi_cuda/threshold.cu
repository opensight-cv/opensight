extern "C"{
__global__ void applyFilter(unsigned char *inputRed, unsigned char *inputGreen, unsigned char *inputBlue,
                             unsigned char *outputChannel,
                             const unsigned int width, const unsigned int height,
                             int lbc0, int ubc0, int lbc1, int ubc1, int lbc2, int ubc2) {
    const unsigned int row = threadIdx.y + blockIdx.y * blockDim.y;
    const unsigned int col = threadIdx.x + blockIdx.x * blockDim.x;

   if(row < height && col < width) {
        uchar3 v = make_uchar3(inputRed[row + col * width], inputGreen[row + col * width], inputBlue[row + col * width]);
        if (v.x >= lbc0 && v.x <= ubc0 && v.y >= lbc1 && v.y <= ubc1 && v.z >= lbc2 && v.z <= ubc2)
        outputChannel[row + col * width] = 255;
        else
        outputChannel[row + col * width] = 0;
    }
}
}
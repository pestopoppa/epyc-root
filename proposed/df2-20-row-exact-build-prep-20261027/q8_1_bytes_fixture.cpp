#include <ggml.h>
#include <hip/hip_runtime.h>
#include <cstdint>
#include <cstdio>
#include <vector>
#include <cstring>
#include <cstdlib>

void quantize_row_q8_1_cuda(const float *, const int32_t *, void *, ggml_type,
                            int64_t, int64_t, int64_t, int64_t,
                            int64_t, int64_t, int64_t, int64_t, hipStream_t);
#define HIP(call) do { hipError_t e = (call); if (e != hipSuccess) { \
    std::fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, hipGetErrorString(e)); return 2; } } while (0)
int main() {
    HIP(hipSetDevice(0));
    const int widths[] = {2, 3, 4, 5, 8};
    const int sizes[] = {5120, 6144, 17408};
    const ggml_type types[] = {GGML_TYPE_Q8_0, GGML_TYPE_Q4_K};
    for (ggml_type type : types) for (int n : sizes) for (int width : widths) {
        const int64_t padded = ((n + 511) / 512) * 512;
        const size_t qbytes = padded / ggml_blck_size(GGML_TYPE_Q8_1) * ggml_type_size(GGML_TYPE_Q8_1);
        std::vector<float> input(static_cast<size_t>(n) * width);
        for (size_t i = 0; i < input.size(); ++i) input[i] = float(int((i * 7919 + 37) % 2003) - 1001) / 103.0f;
        float * in = nullptr; float * one = nullptr; char * batched = nullptr; char * ref = nullptr;
        HIP(hipMalloc(&in, input.size() * sizeof(float))); HIP(hipMalloc(&one, n * sizeof(float)));
        HIP(hipMalloc(&batched, qbytes * width)); HIP(hipMalloc(&ref, qbytes));
        HIP(hipMemcpy(in, input.data(), input.size() * sizeof(float), hipMemcpyHostToDevice));
        HIP(hipMemset(batched, 0xa5, qbytes * width));
        for (int row = 0; row < width; ++row)
            quantize_row_q8_1_cuda(in + row * n, nullptr, batched + row * qbytes, type,
                                   n, n, n, n, padded, 1, 1, 1, nullptr);
        HIP(hipDeviceSynchronize());
        std::vector<char> got(qbytes * width), expected(qbytes);
        HIP(hipMemcpy(got.data(), batched, got.size(), hipMemcpyDeviceToHost));
        for (int row = 0; row < width; ++row) {
            HIP(hipMemcpy(one, input.data() + row * n, n * sizeof(float), hipMemcpyHostToDevice));
            HIP(hipMemset(ref, 0x5a, qbytes));
            quantize_row_q8_1_cuda(one, nullptr, ref, type, n, n, n, n, padded, 1, 1, 1, nullptr);
            HIP(hipDeviceSynchronize()); HIP(hipMemcpy(expected.data(), ref, qbytes, hipMemcpyDeviceToHost));
            if (std::memcmp(got.data() + row * qbytes, expected.data(), qbytes)) {
                std::fprintf(stderr, "FAIL type=%s n=%d width=%d row=%d\n", ggml_type_name(type), n, width, row); return 1;
            }
        }
        std::printf("PASS type=%s n=%d width=%d bytes_per_row=%zu\n", ggml_type_name(type), n, width, qbytes);
        HIP(hipFree(in)); HIP(hipFree(one)); HIP(hipFree(batched)); HIP(hipFree(ref));
    }
    return 0;
}

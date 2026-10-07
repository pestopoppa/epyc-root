// Hosted generated control: compile the actual reviewed backend test translation unit.
#define main epyc_original_backend_ops_main
#include "test-backend-ops.cpp"
#undef main
#include <fstream>
#include <iostream>
#include <filesystem>

static std::vector<uint8_t> initialize_actual(uint64_t seed) {
    ggml_init_params params = { 64 * 1024 * 1024, nullptr, true };
    ggml_context * ctx = ggml_init(params);
    if (!ctx) throw std::runtime_error("ggml context allocation failed");
    ggml_backend_t backend = ggml_backend_cpu_init();
    if (!backend) { ggml_free(ctx); throw std::runtime_error("CPU backend unavailable"); }
    test_ssm_scan_rollback actual(GGML_TYPE_F32, 128, 64, 16, 2, 8, 2, 3);
    ggml_tensor * out = actual.build_graph(ctx);
    ggml_backend_buffer_t buffer = ggml_backend_alloc_ctx_tensors(ctx, backend);
    if (!buffer) { ggml_backend_free(backend); ggml_free(ctx); throw std::runtime_error("tensor allocation failed"); }
    // Same actual seed context entry used by test_case::eval, not a replacement RNG.
    suite_seed_begin(seed, 0, actual.op_desc(out));
    actual.initialize_tensors(ctx);
    std::vector<uint8_t> bytes;
    size_t integer_tensors = 0;
    for (ggml_tensor * tensor = ggml_get_first_tensor(ctx); tensor; tensor = ggml_get_next_tensor(ctx, tensor)) {
        if (tensor->type != GGML_TYPE_I32 || ggml_is_view_op(tensor->op)) continue;
        ++integer_tensors;
        const size_t offset = bytes.size();
        bytes.resize(offset + ggml_nbytes(tensor));
        ggml_backend_tensor_get(tensor, bytes.data() + offset, 0, ggml_nbytes(tensor));
    }
    ggml_backend_buffer_free(buffer);
    ggml_backend_free(backend);
    ggml_free(ctx);
    if (integer_tensors != 1 || bytes.size() != 2 * sizeof(int32_t)) {
        throw std::runtime_error("actual rollback integer-input shape changed");
    }
    return bytes;
}

int main(int argc, char ** argv) {
    if (argc != 2 || !std::filesystem::is_directory(argv[1])) return 2;
    try {
        std::vector<std::vector<uint8_t>> seed_rows;
        for (uint64_t seed = 0; seed < 16; ++seed) {
            auto first = initialize_actual(seed);
            auto second = initialize_actual(seed);
            if (first != second) throw std::runtime_error("actual initializer changed across same-seed replay");
            for (int replay = 0; replay < 2; ++replay) {
                const auto path = std::filesystem::path(argv[1]) / ("seed-" + std::to_string(seed) + "-replay-" + std::to_string(replay) + ".bin");
                if (std::filesystem::exists(path)) throw std::runtime_error("raw output already exists");
                std::ofstream output(path, std::ios::binary);
                if (!output) throw std::runtime_error("raw output cannot be created");
                const auto & captured = replay == 0 ? first : second;
                output.write(reinterpret_cast<const char *>(captured.data()), captured.size());
                output.close();
                if (!output) throw std::runtime_error("raw output write failed");
            }
            seed_rows.push_back(first);
        }
        bool varied = false;
        for (const auto & row : seed_rows) varied = varied || row != seed_rows.front();
        if (!varied) throw std::runtime_error("seed variation control produced no integer-input variation");
        std::cout << "actual SSM_SCAN_ROLLBACK integer initializer: 16 seeds x 2 exact replays; variation present\n";
        return 0;
    } catch (const std::exception & error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

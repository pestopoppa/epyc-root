#include "ggml-alloc.h"
#include "ggml-cpu.h"
#include "gguf.h"
#include "llama.h"

#include <immintrin.h>
#include <omp.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int qk = 32;
constexpr int decisions_per_prompt = 6;

struct Q8Block {
    ggml_fp16_t scale;
    int8_t values[qk];
};
static_assert(sizeof(Q8Block) == 34);

struct Q15Block {
    float scale;
    int16_t values[qk];
};

struct Fixture {
    std::string id;
    std::string kind;
    std::vector<llama_token> prefix;
    std::vector<float> activation;
    std::vector<float> captured_logits;
    std::array<int, 2> stress_tokens{-1, -1};
    float target_gap = 0.0f;
};

void require(bool condition, const std::string &message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template<typename T>
void write_vector(std::ostream &stream, const std::vector<T> &data) {
    stream.write(reinterpret_cast<const char *>(data.data()), data.size() * sizeof(T));
    require(bool(stream), "could not write frozen fixture");
}

struct Capture {
    int width;
    std::vector<float> activation;
    ggml_tensor *weights = nullptr;
};

bool capture_head(ggml_tensor *tensor, bool ask, void *userdata) {
    auto &capture = *static_cast<Capture *>(userdata);
    const bool norm = strcmp(tensor->name, "result_norm") == 0;
    const bool output = strcmp(tensor->name, "result_output") == 0;
    if (ask) {
        return norm || output;
    }
    if (norm) {
        if (tensor->type != GGML_TYPE_F32 || tensor->ne[0] != capture.width ||
            tensor->ne[1] != 1 || tensor->nb[0] != sizeof(float)) {
            capture.activation.clear();
            return true;
        }
        capture.activation.resize(capture.width);
        ggml_backend_tensor_get(tensor, capture.activation.data(), 0, capture.width * sizeof(float));
    }
    if (output) {
        capture.weights = tensor->src[0];
    }
    return true;
}

std::vector<llama_token> tokenize(const llama_vocab *vocab, const std::string &prompt) {
    std::vector<llama_token> tokens(prompt.size() + 16);
    const int n = llama_tokenize(vocab, prompt.data(), prompt.size(), tokens.data(), tokens.size(), true, false);
    require(n > 0, "could not tokenize prompt");
    tokens.resize(n);
    return tokens;
}

std::vector<Fixture> capture_fixtures(llama_model *model, Capture &capture,
                                      const std::string &prompts_path, bool smoke) {
    llama_context_params params = llama_context_default_params();
    params.n_ctx = 512;
    params.n_batch = 128;
    params.n_ubatch = 128;
    params.n_threads = smoke ? 1 : 8;
    params.n_threads_batch = params.n_threads;
    params.cb_eval = capture_head;
    params.cb_eval_user_data = &capture;
    auto *ctx = llama_init_from_model(model, params);
    require(ctx != nullptr, "could not open CPU context");
    const auto *vocab = llama_model_get_vocab(model);
    const int n_vocab = llama_vocab_n_tokens(vocab);
    auto *greedy = llama_sampler_init_greedy();

    std::vector<Fixture> fixtures;
    std::ifstream prompts(prompts_path);
    require(bool(prompts), "could not open prompts");
    std::string line;
    int prompt_index = 0;
    while (std::getline(prompts, line)) {
        const auto separator = line.find('\t');
        require(separator != std::string::npos, "prompt misses split label");
        const auto kind = line.substr(0, separator);
        auto tokens = tokenize(vocab, line.substr(separator + 1));
        llama_memory_clear(llama_get_memory(ctx), true);
        capture.activation.clear();
        require(llama_decode(ctx, llama_batch_get_one(tokens.data(), tokens.size())) == 0, "prompt decode failed");
        const int count = smoke ? 1 : decisions_per_prompt;
        for (int step = 0; step < count; ++step) {
            auto *logits = llama_get_logits_ith(ctx, -1);
            require(logits && int(capture.activation.size()) == capture.width && capture.weights,
                    "could not observe single-row pre-head activation, weights and logits");
            Fixture fixture;
            fixture.id = "p" + std::to_string(prompt_index) + "-s" + std::to_string(step);
            fixture.kind = kind;
            fixture.prefix = tokens;
            fixture.activation = capture.activation;
            fixture.captured_logits.assign(logits, logits + n_vocab);
            fixtures.push_back(std::move(fixture));
            if (step + 1 < count) {
                auto next = llama_sampler_sample(greedy, ctx, -1);
                tokens.push_back(next);
                capture.activation.clear();
                require(llama_decode(ctx, llama_batch_get_one(&next, 1)) == 0, "continuation decode failed");
            }
        }
        ++prompt_index;
        if (smoke) {
            break;
        }
    }
    require(prompt_index == (smoke ? 1 : 12), "prompt frame changed");
    llama_sampler_free(greedy);
    llama_free(ctx);
    return fixtures;
}

struct NativeHead {
    ggml_context *ctx;
    ggml_backend_t backend;
    ggml_backend_buffer_t buffer;
    ggml_tensor *input;
    ggml_tensor *output;
    ggml_cgraph *graph;
    ggml_threadpool_t pool;

    explicit NativeHead(ggml_tensor *weights, int threads) {
        ctx = ggml_init({ggml_tensor_overhead() * 4 + ggml_graph_overhead_custom(8, false), nullptr, true});
        require(ctx != nullptr, "could not create native head context");
        input = ggml_new_tensor_1d(ctx, GGML_TYPE_F32, weights->ne[0]);
        output = ggml_mul_mat(ctx, weights, input);
        graph = ggml_new_graph_custom(ctx, 8, false);
        ggml_build_forward_expand(graph, output);
        backend = ggml_backend_cpu_init();
        require(backend != nullptr, "could not create CPU backend");
        buffer = ggml_backend_alloc_ctx_tensors(ctx, backend);
        require(buffer != nullptr, "could not allocate native head tensors");
        ggml_backend_cpu_set_n_threads(backend, threads);
        auto params = ggml_threadpool_params_default(threads);
        pool = ggml_threadpool_new(&params);
        require(pool != nullptr, "could not create native head threadpool");
        ggml_backend_cpu_set_threadpool(backend, pool);
    }

    ~NativeHead() {
        ggml_backend_free(backend);
        ggml_threadpool_free(pool);
        ggml_backend_buffer_free(buffer);
        ggml_free(ctx);
    }

    void run(const float *x, float *y) {
        ggml_backend_tensor_set(input, x, 0, ggml_nbytes(input));
        require(ggml_backend_graph_compute(backend, graph) == GGML_STATUS_SUCCESS, "native head failed");
        ggml_backend_tensor_get(output, y, 0, ggml_nbytes(output));
    }
};

void pack_q15(const float *input, Q15Block *packed, int nb) {
    const __m512 signless = _mm512_castsi512_ps(_mm512_set1_epi32(0x7fffffff));
    for (int block = 0; block < nb; ++block) {
        const auto lo = _mm512_loadu_ps(input + block * qk);
        const auto hi = _mm512_loadu_ps(input + block * qk + 16);
        const auto absolute = _mm512_max_ps(_mm512_and_ps(lo, signless), _mm512_and_ps(hi, signless));
        const float maximum = _mm512_reduce_max_ps(absolute);
        packed[block].scale = maximum / 32767.0f;
        const auto inv = _mm512_set1_ps(maximum ? 32767.0f / maximum : 0.0f);
        constexpr int rounding = _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC;
        const auto alo = _mm512_cvt_roundps_epi32(_mm512_mul_ps(lo, inv), rounding);
        const auto ahi = _mm512_cvt_roundps_epi32(_mm512_mul_ps(hi, inv), rounding);
        _mm256_storeu_si256(reinterpret_cast<__m256i *>(packed[block].values), _mm512_cvtsepi32_epi16(alo));
        _mm256_storeu_si256(reinterpret_cast<__m256i *>(packed[block].values + 16), _mm512_cvtsepi32_epi16(ahi));
    }
}

__m512i q15_pairs(const int8_t *weight, const int16_t *activation) {
    const auto weights = _mm512_cvtepi8_epi16(_mm256_loadu_si256(reinterpret_cast<const __m256i *>(weight)));
    return _mm512_dpwssd_epi32(_mm512_setzero_si512(), weights, _mm512_loadu_si512(activation));
}

float q15_dot(const Q8Block *weight, const Q15Block *activation, int nb) {
    auto sums = _mm512_setzero_ps();
    for (int i = 0; i < nb; ++i) {
        const auto products = q15_pairs(weight[i].values, activation[i].values);
        const auto scale = _mm512_set1_ps(_cvtsh_ss(weight[i].scale) * activation[i].scale);
        sums = _mm512_fmadd_ps(_mm512_cvtepi32_ps(products), scale, sums);
    }
    return _mm512_reduce_add_ps(sums);
}

float fp32_dot(const Q8Block *weight, const float *activation, int nb) {
    auto lo = _mm512_setzero_ps();
    auto hi = _mm512_setzero_ps();
    for (int i = 0; i < nb; ++i) {
        const auto scale = _mm512_set1_ps(_cvtsh_ss(weight[i].scale));
        const auto wlo = _mm512_cvtepi32_ps(_mm512_cvtepi8_epi32(
            _mm_loadu_si128(reinterpret_cast<const __m128i *>(weight[i].values))));
        const auto whi = _mm512_cvtepi32_ps(_mm512_cvtepi8_epi32(
            _mm_loadu_si128(reinterpret_cast<const __m128i *>(weight[i].values + 16))));
        lo = _mm512_fmadd_ps(_mm512_loadu_ps(activation + i * qk), _mm512_mul_ps(wlo, scale), lo);
        hi = _mm512_fmadd_ps(_mm512_loadu_ps(activation + i * qk + 16), _mm512_mul_ps(whi, scale), hi);
    }
    return _mm512_reduce_add_ps(_mm512_add_ps(lo, hi));
}

double fp64_dot(const Q8Block *weight, const float *activation, int nb) {
    double sum = 0.0;
    for (int i = 0; i < nb; ++i) {
        const double scale = ggml_fp16_to_fp32(weight[i].scale);
        for (int j = 0; j < qk; ++j) {
            sum += scale * weight[i].values[j] * activation[i * qk + j];
        }
    }
    return sum;
}

enum class Arm { fp32, q8, q15, q15_prepacked };

struct ReplayHead {
    const std::vector<Q8Block> &weights;
    int width;
    int n_vocab;
    int nb;
    int threads;
    const ggml_type_traits_cpu *q8_traits = ggml_get_type_traits_cpu(GGML_TYPE_Q8_0);
    std::vector<Q8Block> packed_q8;
    std::vector<Q15Block> packed_q15;

    ReplayHead(const std::vector<Q8Block> &weights, int width, int n_vocab, int threads)
        : weights(weights), width(width), n_vocab(n_vocab), nb(width / qk), threads(threads),
          packed_q8(nb), packed_q15(nb) {}

    void run(Arm arm, const float *input, float *out) {
        if (arm == Arm::q8) {
            q8_traits->from_float(input, packed_q8.data(), width);
            #pragma omp parallel for schedule(static) num_threads(threads)
            for (int row = 0; row < n_vocab; ++row) {
                q8_traits->vec_dot(width, out + row, 0, weights.data() + row * nb, 0, packed_q8.data(), 0, 1);
            }
        } else if (arm == Arm::fp32) {
            #pragma omp parallel for schedule(static) num_threads(threads)
            for (int row = 0; row < n_vocab; ++row) {
                out[row] = fp32_dot(weights.data() + row * nb, input, nb);
            }
        } else {
            if (arm == Arm::q15) {
                pack_q15(input, packed_q15.data(), nb);
            }
            #pragma omp parallel for schedule(static) num_threads(threads)
            for (int row = 0; row < n_vocab; ++row) {
                out[row] = q15_dot(weights.data() + row * nb, packed_q15.data(), nb);
            }
        }
    }
};

std::array<int, 2> top2(const std::vector<float> &logits) {
    std::array<int, 2> ids{-1, -1};
    for (int id = 0; id < int(logits.size()); ++id) {
        if (ids[0] < 0 || logits[id] > logits[ids[0]]) {
            ids[1] = ids[0];
            ids[0] = id;
        } else if (ids[1] < 0 || logits[id] > logits[ids[1]]) {
            ids[1] = id;
        }
    }
    return ids;
}

int native_greedy(llama_sampler *sampler, const std::vector<float> &logits) {
    std::vector<llama_token_data> data;
    data.reserve(logits.size());
    for (int id = 0; id < int(logits.size()); ++id) {
        data.push_back({id, logits[id], 0.0f});
    }
    llama_token_data_array candidates{data.data(), data.size(), -1, false};
    llama_sampler_apply(sampler, &candidates);
    require(candidates.selected >= 0, "greedy sampler did not select a token");
    return candidates.data[candidates.selected].id;
}

std::vector<Fixture> stress_fixtures(const std::vector<Fixture> &natural, ReplayHead &head) {
    constexpr std::array<float, 8> gaps{0.00025f, -0.00025f, 0.001f, -0.001f, 0.01f, -0.01f, 0.25f, -0.25f};
    std::vector<Fixture> stress;
    std::vector<float> logits(head.n_vocab);
    int calibration_cases = 0;
    for (const auto &source : natural) {
        if (source.kind != "calibration" || calibration_cases == 2) {
            continue;
        }
        head.run(Arm::fp32, source.activation.data(), logits.data());
        const auto ids = top2(logits);
        const auto *wa = head.weights.data() + ids[0] * head.nb;
        const auto *wb = head.weights.data() + ids[1] * head.nb;
        std::vector<double> direction(head.width);
        double norm_squared = 0.0;
        for (int i = 0; i < head.width; ++i) {
            const int block = i / qk;
            const int j = i % qk;
            direction[i] = double(ggml_fp16_to_fp32(wa[block].scale)) * wa[block].values[j] -
                           double(ggml_fp16_to_fp32(wb[block].scale)) * wb[block].values[j];
            norm_squared += direction[i] * direction[i];
        }
        require(norm_squared > 0, "top-two weights are identical");
        const double gap = fp64_dot(wa, source.activation.data(), head.nb) - fp64_dot(wb, source.activation.data(), head.nb);
        for (int i = 0; i < int(gaps.size()); ++i) {
            Fixture fixture{source.id + "-g" + std::to_string(i), "stress", source.prefix, source.activation, {}, ids, gaps[i]};
            const double shift = (gaps[i] - gap) / norm_squared;
            for (int j = 0; j < head.width; ++j) {
                fixture.activation[j] = float(fixture.activation[j] + shift * direction[j]);
            }
            stress.push_back(std::move(fixture));
        }
        ++calibration_cases;
    }
    require(stress.size() == 16, "stress frame changed");
    return stress;
}

void check_signed_pairs(std::ostream &out) {
    std::mt19937 rng(19031);
    std::uniform_int_distribution<int> weight_dist(-128, 127);
    std::uniform_int_distribution<int> activation_dist(-32767, 32767);
    int64_t max_abs_block = 0;
    constexpr int cases = 4098;
    for (int c = 0; c < cases; ++c) {
        std::array<int8_t, qk> weight{};
        std::array<int16_t, qk> activation{};
        for (int j = 0; j < qk; ++j) {
            weight[j] = c < 2 ? -128 : weight_dist(rng);
            activation[j] = c < 2 ? (c ? -32767 : 32767) : activation_dist(rng);
        }
        std::array<int32_t, qk / 2> pairs{};
        _mm512_storeu_si512(pairs.data(), q15_pairs(weight.data(), activation.data()));
        int64_t sum = 0;
        for (int pair = 0; pair < qk / 2; ++pair) {
            const int j = pair * 2;
            const int64_t ref = int64_t(weight[j]) * activation[j] + int64_t(weight[j + 1]) * activation[j + 1];
            require(pairs[pair] == ref, "signed-word pair disagrees with scalar int64");
            sum += ref;
        }
        max_abs_block = std::max(max_abs_block, std::abs(sum));
    }
    const auto minimum = _mm512_set1_epi16(std::numeric_limits<int16_t>::min());
    const auto zero = _mm512_setzero_si512();
    auto wrap = _mm512_dpwssd_epi32(zero, minimum, minimum);
    auto saturate = _mm512_dpwssds_epi32(zero, minimum, minimum);
    const auto wrap_first = _mm_cvtsi128_si32(_mm512_castsi512_si128(wrap));
    const auto sat_first = _mm_cvtsi128_si32(_mm512_castsi512_si128(saturate));
    const int64_t exact = 2LL * -32768 * -32768;
    require(wrap_first == std::numeric_limits<int32_t>::min() &&
            sat_first == std::numeric_limits<int32_t>::max() && exact == 2147483648LL,
            "signed-word extrema overflow semantics changed");
    out << "cases,max_abs_q8_q15_block,full_signed_pair_exact,dpwssd_wrap,dpwssds_sat\n"
        << cases << ',' << max_abs_block << ',' << exact << ',' << wrap_first << ',' << sat_first << '\n';
}

void trace_accumulators(std::ostream &out, const Fixture &fixture, const ReplayHead &head,
                        const std::vector<float> &reference, const std::vector<int> &ids) {
    for (int id : ids) {
        const auto *weights = head.weights.data() + id * head.nb;
        for (int i = 0; i < head.nb; ++i) {
            std::array<int32_t, qk / 2> pairs{};
            _mm512_storeu_si512(pairs.data(), q15_pairs(weights[i].values, head.packed_q15[i].values));
            int64_t q8 = 0;
            int64_t q15 = 0;
            double fp64 = 0.0;
            for (int j = 0; j < qk; j += 2) {
                const auto *w = weights[i].values;
                const auto *xq8 = head.packed_q8[i].values;
                const auto *xq15 = head.packed_q15[i].values;
                const int64_t expected = int64_t(w[j]) * xq15[j] + int64_t(w[j + 1]) * xq15[j + 1];
                require(pairs[j / 2] == expected, "model signed-word pair disagrees with scalar int64");
                q15 += pairs[j / 2];
                q8 += int64_t(w[j]) * xq8[j] + int64_t(w[j + 1]) * xq8[j + 1];
                fp64 += double(w[j]) * fixture.activation[i * qk + j] +
                        double(w[j + 1]) * fixture.activation[i * qk + j + 1];
            }
            out << fixture.id << ',' << id << ',' << i << ',' << q8 << ',' << q15 << ',' << fp64 << ','
                << ggml_fp16_to_fp32(weights[i].scale) << ',' << ggml_fp16_to_fp32(head.packed_q8[i].scale)
                << ',' << head.packed_q15[i].scale << '\n';
        }
        require(std::abs(reference[id] - fp64_dot(weights, fixture.activation.data(), head.nb)) < 0.00002,
                "FP32 reference diverges from FP64 top-two cross-check");
    }
}

void row_result(std::ostream &out, const Fixture &fixture, int threads, const std::string &arm,
                const std::vector<float> &logits, const std::vector<float> &reference, llama_sampler *greedy) {
    const auto ids = top2(logits);
    const int sampled = native_greedy(greedy, logits);
    require(sampled == ids[0], "native greedy winner differs from first argmax");
    const auto reference_ids = top2(reference);
    double max_error = 0.0;
    double squared_error = 0.0;
    for (size_t i = 0; i < logits.size(); ++i) {
        require(std::isfinite(logits[i]), "nonfinite head logit");
        const double error = double(logits[i]) - reference[i];
        max_error = std::max(max_error, std::abs(error));
        squared_error += error * error;
    }
    out << fixture.id << ',' << fixture.kind << ',' << threads << ',' << arm << ','
        << sampled << ',' << ids[1] << ',' << logits[ids[0]] << ',' << logits[ids[1]] << ','
        << (logits[ids[0]] - logits[ids[1]]) << ',' << reference_ids[0] << ',' << reference_ids[1] << ','
        << (reference[reference_ids[0]] - reference[reference_ids[1]]) << ',' << max_error << ','
        << std::sqrt(squared_error / logits.size()) << ',' << fixture.stress_tokens[0] << ','
        << fixture.stress_tokens[1] << ',' << fixture.target_gap << ',';
    if (fixture.stress_tokens[0] >= 0) {
        out << logits[fixture.stress_tokens[0]] - logits[fixture.stress_tokens[1]];
    }
    out << '\n';
}

using Clock = std::chrono::steady_clock;

template<typename Func>
double time_ns(Func op, int repeats) {
    const auto start = Clock::now();
    for (int i = 0; i < repeats; ++i) {
        op();
    }
    return std::chrono::duration<double, std::nano>(Clock::now() - start).count() / repeats;
}

void benchmark(std::ostream &out, NativeHead &native, ReplayHead &head,
               const std::vector<Fixture> &fixtures) {
    constexpr std::array<const char *, 5> names{"native_q8", "q8", "q8_repeat", "q15", "q15_prepacked"};
    std::vector<float> logits(head.n_vocab);
    for (int round = 0; round < 8; ++round) {
        const auto &fixture = fixtures[round];
        const auto *input = fixture.activation.data();
        pack_q15(input, head.packed_q15.data(), head.nb);
        for (int position = 0; position < int(names.size()); ++position) {
            const int arm = (round + ((round % 2) ? (int(names.size()) - 1 - position) : position)) % names.size();
            auto op = [&] {
                if (arm == 0) {
                    native.run(input, logits.data());
                } else if (arm < 3) {
                    head.run(Arm::q8, input, logits.data());
                } else {
                    head.run(arm == 3 ? Arm::q15 : Arm::q15_prepacked, input, logits.data());
                }
            };
            op();
            const double ns = time_ns(op, 4);
            out << head.threads << ',' << round << ',' << position << ',' << fixture.id << ','
                << names[arm] << ',' << ns << ',' << logits[fixture.captured_logits.size() / 2] << '\n';
        }
        const auto q8_pack = [&] {
            head.q8_traits->from_float(input, head.packed_q8.data(), head.width);
            asm volatile("" : : "r"(head.packed_q8.data()) : "memory");
        };
        const auto q15_pack = [&] {
            pack_q15(input, head.packed_q15.data(), head.nb);
            asm volatile("" : : "r"(head.packed_q15.data()) : "memory");
        };
        const double q8_ns = time_ns(q8_pack, 16384);
        const double q15_ns = time_ns(q15_pack, 16384);
        out << head.threads << ',' << round << ",5," << fixture.id << ",pack_q8," << q8_ns << ",0\n"
            << head.threads << ',' << round << ",6," << fixture.id << ",pack_q15," << q15_ns << ",0\n";
    }
    out.flush();
}

std::vector<Q8Block> freeze_weights(const std::string &model_path, const std::filesystem::path &out,
                                    int width, int n_vocab) {
    auto *metadata = gguf_init_from_file(model_path.c_str(), {true, nullptr});
    require(metadata != nullptr, "could not open GGUF metadata");
    std::string name = "output.weight";
    int64_t id = gguf_find_tensor(metadata, name.c_str());
    if (id < 0) {
        name = "token_embd.weight";
        id = gguf_find_tensor(metadata, name.c_str());
    }
    require(id >= 0 && gguf_get_tensor_type(metadata, id) == GGML_TYPE_Q8_0, "GGUF output/tied weights are not Q8_0");
    size_t offset = gguf_get_data_offset(metadata) + gguf_get_tensor_offset(metadata, id);
    size_t size = gguf_get_tensor_size(metadata, id);
    gguf_free(metadata);
    std::vector<Q8Block> weights(n_vocab * (width / qk));
    require(size == weights.size() * sizeof(Q8Block), "GGUF output weight size disagrees with head shape");
    std::ifstream model_file(model_path, std::ios::binary);
    model_file.seekg(offset);
    model_file.read(reinterpret_cast<char *>(weights.data()), size);
    require(bool(model_file), "could not read frozen GGUF head bytes");
    std::ofstream bytes(out / "weights.q8_0", std::ios::binary);
    write_vector(bytes, weights);
    std::ofstream desc(out / "weights.tsv");
    desc << "tensor\toffset\tbytes\twidth\tvocab\n"
         << name << '\t' << offset << '\t' << size << '\t' << width << '\t' << n_vocab << '\n';
    return weights;
}

void compare(const std::string &mode, const std::string &model_path, const std::string &prompts,
             const std::filesystem::path &out) {
    std::filesystem::create_directories(out);
    const bool smoke = mode == "smoke";
    omp_set_dynamic(0);
    llama_backend_init();
    auto params = llama_model_default_params();
    params.n_gpu_layers = 0;
    auto *model = llama_model_load_from_file(model_path.c_str(), params);
    require(model != nullptr, "CPU model load failed");
    const int width = llama_model_n_embd(model);
    const int n_vocab = llama_vocab_n_tokens(llama_model_get_vocab(model));
    require(width > 0 && width % qk == 0 && n_vocab > 1, "unsupported head shape");
    Capture capture{width, {}, nullptr};
    auto fixtures = capture_fixtures(model, capture, prompts, smoke);
    require(capture.weights->type == GGML_TYPE_Q8_0 && capture.weights->ne[0] == width &&
            capture.weights->ne[1] == n_vocab && capture.weights->buffer, "native graph head tensor differs from pinned Q8_0 shape");
    std::cout << "CAPTURED " << fixtures.size() << " rows from head buffer "
              << ggml_backend_buffer_name(capture.weights->buffer) << " width " << width << " vocab " << n_vocab << std::endl;
    std::cout << "Q15_NATIVE_HEAD_PROGRESS" << std::endl;
    auto weights = freeze_weights(model_path, out, width, n_vocab);
    std::ofstream oracle(out / "signed-pairs.csv");
    check_signed_pairs(oracle);
    if (!smoke) {
        ReplayHead calibration(weights, width, n_vocab, 8);
        auto stress = stress_fixtures(fixtures, calibration);
        fixtures.insert(fixtures.end(), std::make_move_iterator(stress.begin()), std::make_move_iterator(stress.end()));
    }
    std::ofstream metadata(out / "fixtures.tsv");
    metadata << "index\tid\tkind\tstress_token_0\tstress_token_1\ttarget_signed_gap\tprefix_tokens\n";
    std::ofstream activations(out / "activations.f32", std::ios::binary);
    std::ofstream native_captured(out / "captured-logits.f32", std::ios::binary);
    int index = 0;
    for (const auto &fixture : fixtures) {
        require(std::all_of(fixture.activation.begin(), fixture.activation.end(), [](float x) { return std::isfinite(x); }),
                "nonfinite head activation");
        metadata << index++ << '\t' << fixture.id << '\t' << fixture.kind << '\t'
                 << fixture.stress_tokens[0] << '\t' << fixture.stress_tokens[1] << '\t' << fixture.target_gap << '\t';
        for (const int token : fixture.prefix) {
            metadata << token << ',';
        }
        metadata << '\n';
        write_vector(activations, fixture.activation);
        if (!fixture.captured_logits.empty()) {
            write_vector(native_captured, fixture.captured_logits);
        }
    }
    std::ofstream rows(out / "decisions.csv");
    rows << std::setprecision(10)
         << "fixture,kind,threads,arm,greedy_id,second_id,logit_1,logit_2,gap,fp32_id,fp32_second_id,fp32_gap,max_abs_error,"
            "rmse,stress_token_0,stress_token_1,stress_target_signed_gap,stress_realized_signed_gap\n";
    std::ofstream trace(out / "block-accumulators.csv");
    trace << std::setprecision(12) << "fixture,token,block,q8_i64,q15_i64,fp64_unscaled,weight_scale,q8_scale,q15_scale\n";
    std::ofstream timings(out / "timings.csv");
    timings << std::setprecision(10) << "threads,round,position,fixture,arm,ns_per_run,output_witness\n";
    auto *greedy = llama_sampler_init_greedy();
    std::vector<float> golden(n_vocab), q8(n_vocab), q15(n_vocab), replay_native(n_vocab);
    const auto thread_counts = smoke ? std::vector<int>{1} : std::vector<int>{1, 8, 24};
    for (const int threads : thread_counts) {
        std::cout << "REPLAY threads=" << threads << std::endl;
        NativeHead native(capture.weights, threads);
        ReplayHead head(weights, width, n_vocab, threads);
        if (!smoke) {
            benchmark(timings, native, head, fixtures);
        }
        std::ofstream logits(out / ("head-t" + std::to_string(threads) + ".f32"), std::ios::binary);
        for (const auto &fixture : fixtures) {
            const float *x = fixture.activation.data();
            head.run(Arm::fp32, x, golden.data());
            head.run(Arm::q8, x, q8.data());
            head.run(Arm::q15, x, q15.data());
            native.run(x, replay_native.data());
            if (threads == thread_counts.front()) {
                if (!fixture.captured_logits.empty()) {
                    row_result(rows, fixture, smoke ? 1 : 8, "captured", fixture.captured_logits, golden, greedy);
                }
                std::vector<int> trace_ids;
                for (const auto *values : {&golden, &q8, &q15, &replay_native}) {
                    const auto ids = top2(*values);
                    trace_ids.insert(trace_ids.end(), ids.begin(), ids.end());
                }
                std::sort(trace_ids.begin(), trace_ids.end());
                trace_ids.erase(std::unique(trace_ids.begin(), trace_ids.end()), trace_ids.end());
                trace_accumulators(trace, fixture, head, golden, trace_ids);
            }
            row_result(rows, fixture, threads, "fp32", golden, golden, greedy);
            row_result(rows, fixture, threads, "q8", q8, golden, greedy);
            row_result(rows, fixture, threads, "q15", q15, golden, greedy);
            row_result(rows, fixture, threads, "native_q8", replay_native, golden, greedy);
            for (const auto *values : {&golden, &q8, &q15, &replay_native}) {
                write_vector(logits, *values);
            }
        }
        rows.flush();
        require(bool(rows) && bool(trace) && bool(timings), "could not persist replay outputs");
        std::cout << "FINISHED threads=" << threads << " fixtures=" << fixtures.size() << std::endl;
    }
    llama_sampler_free(greedy);
    llama_model_free(model);
    llama_backend_free();
}
}  // namespace

int main(int argc, char **argv) {
    try {
        require(argc == 5, "usage: replay smoke|run MODEL PROMPTS OUTPUT_DIR");
        const std::string mode = argv[1];
        require(mode == "smoke" || mode == "run", "unknown replay mode");
        compare(mode, argv[2], argv[3], argv[4]);
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

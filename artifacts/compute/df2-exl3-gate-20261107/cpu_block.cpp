// DF2-EXL3 gate: decode ONE real 128x128 EXL3 block with the EXL3-2 CPU codec reference (experiments/exl3_cpu).
// usage: cpu_block DIR K OUT_PREFIX   (DIR holds trellis.bin suh.bin svh.bin act.f32 [3x128 float])
// writes OUT.W.f32 (reconstruct(): canonical [k=128,n=128], stage-rounded) and OUT.Y.f32 (dense() fused, scalar ISA, 3 rows).
#include "exl3_cpu.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
static std::vector<char> slurp(const std::string& p) {
    std::ifstream f(p, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open " + p);
    return std::vector<char>(std::istreambuf_iterator<char>(f), {});
}
static float half(uint16_t u) { _Float16 h; std::memcpy(&h, &u, 2); return float(h); }
int main(int argc, char** argv) try {
    if (argc != 4) throw std::runtime_error("usage: cpu_block DIR K OUT_PREFIX");
    std::string d = argv[1]; unsigned K = std::stoul(argv[2]);
    exl3::Matrix w{}; w.k = w.n = w.padded_k = w.padded_n = 128; w.bits = K;
    w.codebook = exl3::Codebook::mul1; w.layout = exl3::Layout::native;
    auto t = slurp(d + "/trellis.bin");
    if (t.size() != size_t(128) * 128 * K / 8) throw std::runtime_error("trellis size");
    w.trellis.resize(t.size() / 2); std::memcpy(w.trellis.data(), t.data(), t.size());
    for (auto pr : {std::make_pair("suh.bin", &w.suh), std::make_pair("svh.bin", &w.svh)}) {
        auto b = slurp(d + "/" + pr.first);
        if (b.size() != 256) throw std::runtime_error("scale size");
        for (int i = 0; i < 128; ++i) { uint16_t u; std::memcpy(&u, &b[2 * i], 2); pr.second->push_back(half(u)); }
    }
    auto a = slurp(d + "/act.f32");
    if (a.size() != 3 * 128 * 4) throw std::runtime_error("act size");
    std::vector<float> x(384); std::memcpy(x.data(), a.data(), a.size());
    exl3::validate(w);
    auto W = exl3::reconstruct(w);
    std::vector<float> y(3 * 128);
    exl3::dense(w, x.data(), 3, 128, y.data(), 128, exl3::ISA::scalar);
    std::string o = argv[3];
    std::ofstream(o + ".W.f32", std::ios::binary).write(reinterpret_cast<char*>(W.data()), W.size() * 4);
    std::ofstream(o + ".Y.f32", std::ios::binary).write(reinterpret_cast<char*>(y.data()), y.size() * 4);
    std::printf("{\"w_elems\":%zu}\n", W.size());
    return 0;
} catch (const std::exception& e) { std::fprintf(stderr, "REFUSE %s\n", e.what()); return 3; }

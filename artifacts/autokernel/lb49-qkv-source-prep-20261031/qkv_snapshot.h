#pragma once
#include "ggml-backend.h"
#include "ggml.h"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace qkv {
// Versioned, host-independent field writes; little-endian host required
// explicitly.
constexpr uint64_t MAX_BYTES = 256ULL * 1024 * 1024;
struct Tensor {
  int32_t type = 0;
  std::array<int64_t, 4> ne{};
  std::array<uint64_t, 4> nb{};
  std::array<int32_t, GGML_MAX_OP_PARAMS / 4> params{};
  std::vector<unsigned char> raw;
};
template <class T> inline void write(std::ostream &o, const T &v) {
  o.write(reinterpret_cast<const char *>(&v), sizeof v);
  if (!o)
    throw std::runtime_error("write");
}
template <class T> inline void read(std::istream &o, T &v) {
  o.read(reinterpret_cast<char *>(&v), sizeof v);
  if (!o)
    throw std::runtime_error("truncated header");
}
inline Tensor take(ggml_tensor *t) {
  if (!t)
    throw std::runtime_error("null tensor");
  Tensor b;
  b.type = t->type;
  for (int i = 0; i < 4; i++) {
    b.ne[i] = t->ne[i];
    b.nb[i] = t->nb[i];
  }
  std::memcpy(b.params.data(), t->op_params, GGML_MAX_OP_PARAMS);
  size_t n = ggml_nbytes(t);
  if (!n || n > MAX_BYTES)
    throw std::runtime_error("size limit");
  b.raw.resize(n);
  ggml_backend_tensor_get(t, b.raw.data(), 0, n);
  return b;
}
inline void save(const std::string &p, const Tensor &b) {
  uint16_t endian = 1;
  if (*reinterpret_cast<unsigned char *>(&endian) != 1)
    throw std::runtime_error("little endian required");
  std::ofstream o(p, std::ios::binary);
  o.write("EPYCQKV1", 8);
  write(o, b.type);
  for (auto v : b.ne)
    write(o, v);
  for (auto v : b.nb)
    write(o, v);
  for (auto v : b.params)
    write(o, v);
  write(o, uint64_t(b.raw.size()));
  o.write(reinterpret_cast<const char *>(b.raw.data()), b.raw.size());
  if (!o)
    throw std::runtime_error("raw write");
}
// Validate both the serialized strided span and ggml's initial contiguous
// allocation size before any shape reaches ggml_new_tensor/ggml_nbytes.
inline uint64_t bounded_span(const Tensor &b) {
  if (b.type < 0 || b.type >= GGML_TYPE_COUNT)
    throw std::runtime_error("bad type");
  const auto type = ggml_type(b.type);
  const uint64_t unit = ggml_type_size(type);
  const int64_t block = ggml_blck_size(type);
  if (!unit || block <= 0)
    throw std::runtime_error("unsupported storage type");
  for (auto n : b.ne)
    if (n <= 0 || n > INT32_MAX)
      throw std::runtime_error("bad shape");
  if (b.ne[0] % block || b.nb[0] != unit)
    throw std::runtime_error("invalid block/element stride");
  for (auto stride : b.nb)
    if (!stride || stride > MAX_BYTES)
      throw std::runtime_error("stride limit");
  auto mul = [](uint64_t a, uint64_t z) {
    if (a && z > MAX_BYTES / a)
      throw std::runtime_error("bounded span overflow");
    return a * z;
  };
  uint64_t contiguous = mul(unit, uint64_t(b.ne[0]) / block);
  for (int i = 1; i < 4; ++i)
    contiguous = mul(contiguous, uint64_t(b.ne[i]));
  uint64_t span = block == 1 ? unit : mul(uint64_t(b.ne[0]) / block, b.nb[0]);
  for (int i = block == 1 ? 0 : 1; i < 4; ++i) {
    const uint64_t term = mul(uint64_t(b.ne[i] - 1), b.nb[i]);
    if (term > MAX_BYTES - span)
      throw std::runtime_error("bounded span overflow");
    span += term;
  }
  return span;
}
inline Tensor load(const std::string &p) {
  std::ifstream o(p, std::ios::binary);
  char magic[8]{};
  o.read(magic, 8);
  if (!o)
    throw std::runtime_error("truncated magic");
  if (std::memcmp(magic, "EPYCQKV1", 8))
    throw std::runtime_error("bad magic");
  Tensor b;
  read(o, b.type);
  for (auto &v : b.ne)
    read(o, v);
  for (auto &v : b.nb)
    read(o, v);
  for (auto &v : b.params)
    read(o, v);
  uint64_t n;
  read(o, n);
  if (!n || n > MAX_BYTES)
    throw std::runtime_error("size limit");
  if (bounded_span(b) != n)
    throw std::runtime_error("stride/span mismatch");
  b.raw.resize(n);
  o.read(reinterpret_cast<char *>(b.raw.data()), n);
  if (!o || o.peek() != EOF)
    throw std::runtime_error("raw length");
  return b;
}
inline ggml_tensor *restore(ggml_context *c, Tensor &b) {
  if (bounded_span(b) != b.raw.size())
    throw std::runtime_error("stride/span mismatch");
  auto *t = ggml_new_tensor(c, ggml_type(b.type), 4, b.ne.data());
  for (int i = 0; i < 4; i++)
    t->nb[i] = b.nb[i];
  if (ggml_nbytes(t) != b.raw.size())
    throw std::runtime_error("stride/span mismatch");
  t->data = b.raw.data();
  std::memcpy(t->op_params, b.params.data(), GGML_MAX_OP_PARAMS);
  return t;
}
struct Capture {
  std::string prefix;
  int count = 0;
  bool failed = false;
  std::array<std::vector<unsigned char>, 5> early;
  bool probe_early = false;
  int threads = 1;
  bool iqk_on = false;
};
inline bool callback(ggml_tensor *t, bool ask, void *user) {
  auto &c = *static_cast<Capture *>(user);
  if (t->op != GGML_OP_FLASH_ATTN_EXT)
    return ask ? false : true;
  if (ask) {
    if (c.probe_early && c.count == 0)
      for (int i = 0; i < 5; i++)
        if (t->src[i])
          c.early[i] = take(t->src[i]).raw;
    return true;
  }
  if (c.count++)
    return true;
  try {
    std::ofstream meta(c.prefix + ".meta");
    meta << "schema=1\nthreads=" << c.threads << "\niqk_on=" << c.iqk_on
         << "\nphase=after_backend_synchronize\nname=" << t->name << "\n";
    for (int i = 0; i < 5; i++) {
      auto *s = t->src[i];
      meta << "present" << i << "=" << (s ? 1 : 0) << "\n";
      if (!s)
        continue;
      int alias = -1;
      for (int j = 0; j < i; j++)
        if (t->src[j]) {
          auto *p = t->src[j];
          auto a = reinterpret_cast<uintptr_t>(s->data),
               b = reinterpret_cast<uintptr_t>(p->data);
          bool overlap = a < b + ggml_nbytes(p) && b < a + ggml_nbytes(s);
          if (overlap && (a != b || ggml_nbytes(s) != ggml_nbytes(p)))
            throw std::runtime_error(
                "partial-overlap alias unsupported; refuse, do not normalize");
          if (a == b)
            alias = j;
        }
      meta << "alias" << i << "=" << alias << "\n";
      save(c.prefix + ".src" + std::to_string(i), take(s));
    }
    save(c.prefix + ".out", take(t));
    if (!meta)
      throw std::runtime_error("meta write");
  } catch (const std::exception &e) {
    std::fprintf(stderr, "capture error: %s\n", e.what());
    c.failed = true;
    return false;
  }
  return true;
}
} // namespace qkv

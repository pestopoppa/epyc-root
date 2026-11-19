#pragma once
#include <native_carrier.h>
#include <fstream>
#include <filesystem>

namespace am_carrier {

// No packed-struct ABI, endian assumptions or unbounded allocation from file.
inline std::vector<layer_fit> read_bundle(const std::filesystem::path & path) {
    const uint32_t endian = 1;
    require(*reinterpret_cast<const unsigned char *>(&endian) == 1 && sizeof(float) == 4,
            "bundle requires little-endian IEEE float32 host");
    require(std::filesystem::file_size(path) <= (uint64_t(1) << 30), "bundle exceeds 1 GiB budget");
    std::ifstream input(path, std::ios::binary);
    auto read = [&](void * dst, size_t n) {
        if (!input.read(static_cast<char *>(dst), n)) throw std::invalid_argument("truncated carrier bundle");
    };
    char magic[8]; read(magic, 8);
    require(std::memcmp(magic, "EPYCAM03", 8) == 0, "carrier magic mismatch");
    uint32_t count, kept; read(&count, 4); read(&kept, 4);
    require(count > 0 && count <= 256 && kept >= 2 && kept <= 36864, "invalid bundle counts");
    std::vector<int64_t> positions(kept); read(positions.data(), kept*8);
    std::vector<layer_fit> layers;
    size_t consumed = 16 + kept*8;
    const auto size = std::filesystem::file_size(path);
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t id, heads, width; read(&id, 4); read(&heads, 4); read(&width, 4);
        require(id < 256 && heads > 0 && heads <= 256 && width > 0 && width <= 512,
                "invalid bundle layer geometry");
        const uint64_t bytes = uint64_t(heads)*kept*(1 + width)*4;
        consumed += 12;
        require(consumed <= size && bytes <= size - consumed, "truncated layer arrays");
        consumed += bytes;
        layer_fit fit;
        fit.layer = id; fit.kv_heads = heads; fit.value_width = width; fit.positions = positions;
        fit.beta.resize(size_t(heads)*kept); fit.values.resize(size_t(heads)*kept*width);
        read(fit.beta.data(), fit.beta.size()*4); read(fit.values.data(), fit.values.size()*4);
        fit.validate();
        layers.push_back(std::move(fit));
    }
    require(consumed == size, "trailing carrier bytes");
    validate_layers(layers);
    return layers;
}

} // namespace am_carrier

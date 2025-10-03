#include "count_min_sketch.hpp"

#include <array>
#include <cstring>
#include <stdexcept>

namespace engagehub {
namespace {

std::uint64_t rotl64(std::uint64_t x, int8_t r) {
    return (x << r) | (x >> (64 - r));
}

std::uint64_t fmix64(std::uint64_t k) {
    k ^= k >> 33;
    k *= 0xff51afd7ed558ccdULL;
    k ^= k >> 33;
    k *= 0xc4ceb9fe1a85ec53ULL;
    k ^= k >> 33;
    return k;
}

std::uint64_t murmurhash3_64(const void* key, std::size_t len, std::uint64_t seed) {
    const std::uint8_t* data = static_cast<const std::uint8_t*>(key);
    const int nblocks = static_cast<int>(len / 16);

    std::uint64_t h1 = seed;
    std::uint64_t h2 = seed;

    const std::uint64_t c1 = 0x87c37b91114253d5ULL;
    const std::uint64_t c2 = 0x4cf5ad432745937fULL;

    // body
    const std::uint64_t* blocks = reinterpret_cast<const std::uint64_t*>(data);
    for (int i = 0; i < nblocks; ++i) {
        std::uint64_t k1 = blocks[i * 2 + 0];
        std::uint64_t k2 = blocks[i * 2 + 1];

        k1 *= c1;
        k1 = rotl64(k1, 31);
        k1 *= c2;
        h1 ^= k1;

        h1 = rotl64(h1, 27);
        h1 += h2;
        h1 = h1 * 5 + 0x52dce729;

        k2 *= c2;
        k2 = rotl64(k2, 33);
        k2 *= c1;
        h2 ^= k2;

        h2 = rotl64(h2, 31);
        h2 += h1;
        h2 = h2 * 5 + 0x38495ab5;
    }

    // tail
    const std::uint8_t* tail = data + nblocks * 16;
    std::uint64_t k1 = 0;
    std::uint64_t k2 = 0;

    switch (len & 15) {
        case 15: k2 ^= static_cast<std::uint64_t>(tail[14]) << 48; [[fallthrough]];
        case 14: k2 ^= static_cast<std::uint64_t>(tail[13]) << 40; [[fallthrough]];
        case 13: k2 ^= static_cast<std::uint64_t>(tail[12]) << 32; [[fallthrough]];
        case 12: k2 ^= static_cast<std::uint64_t>(tail[11]) << 24; [[fallthrough]];
        case 11: k2 ^= static_cast<std::uint64_t>(tail[10]) << 16; [[fallthrough]];
        case 10: k2 ^= static_cast<std::uint64_t>(tail[9]) << 8; [[fallthrough]];
        case 9:  k2 ^= static_cast<std::uint64_t>(tail[8]) << 0;
                 k2 *= c2;
                 k2 = rotl64(k2, 33);
                 k2 *= c1;
                 h2 ^= k2;
                 [[fallthrough]];
        case 8:  k1 ^= static_cast<std::uint64_t>(tail[7]) << 56; [[fallthrough]];
        case 7:  k1 ^= static_cast<std::uint64_t>(tail[6]) << 48; [[fallthrough]];
        case 6:  k1 ^= static_cast<std::uint64_t>(tail[5]) << 40; [[fallthrough]];
        case 5:  k1 ^= static_cast<std::uint64_t>(tail[4]) << 32; [[fallthrough]];
        case 4:  k1 ^= static_cast<std::uint64_t>(tail[3]) << 24; [[fallthrough]];
        case 3:  k1 ^= static_cast<std::uint64_t>(tail[2]) << 16; [[fallthrough]];
        case 2:  k1 ^= static_cast<std::uint64_t>(tail[1]) << 8;  [[fallthrough]];
        case 1:  k1 ^= static_cast<std::uint64_t>(tail[0]) << 0;
                 k1 *= c1;
                 k1 = rotl64(k1, 31);
                 k1 *= c2;
                 h1 ^= k1;
                 break;
        default:;
    }

    h1 ^= static_cast<std::uint64_t>(len);
    h2 ^= static_cast<std::uint64_t>(len);

    h1 += h2;
    h2 += h1;

    h1 = fmix64(h1);
    h2 = fmix64(h2);

    h1 += h2;
    // intentionally ignore h2 for 64bit variant
    return h1;
}

} // namespace

CountMinSketch::CountMinSketch(std::size_t width, std::size_t depth, std::uint64_t seed)
    : width_(width), depth_(depth), seed_(seed), table_(width * depth, 0) {
    if ((width_ & (width_ - 1)) != 0) {
        throw std::invalid_argument("CountMinSketch width must be power of two");
    }
    if (depth_ == 0) {
        throw std::invalid_argument("CountMinSketch depth must be greater than zero");
    }
}

void CountMinSketch::increment(const std::string& key, std::uint64_t count) {
    for (std::size_t i = 0; i < depth_; ++i) {
        const std::uint64_t h = hash(key, i);
        const std::size_t idx = (i * width_) + (h & (width_ - 1));
        table_[idx] += count;
    }
}

std::uint64_t CountMinSketch::estimate(const std::string& key) const {
    std::uint64_t result = UINT64_MAX;
    for (std::size_t i = 0; i < depth_; ++i) {
        const std::uint64_t h = hash(key, i);
        const std::size_t idx = (i * width_) + (h & (width_ - 1));
        result = std::min(result, table_[idx]);
    }
    return result == UINT64_MAX ? 0 : result;
}

std::uint64_t CountMinSketch::hash(const std::string& key, std::size_t index) const {
    const std::uint64_t salt = seed_ + static_cast<std::uint64_t>(index) * 0x9e3779b97f4a7c15ULL;
    return murmurhash3_64(key.data(), key.size(), salt);
}

} // namespace engagehub

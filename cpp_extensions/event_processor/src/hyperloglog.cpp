#include "hyperloglog.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
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

    constexpr std::uint64_t c1 = 0x87c37b91114253d5ULL;
    constexpr std::uint64_t c2 = 0x4cf5ad432745937fULL;

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
    return h1;
}

} // namespace

HyperLogLog::HyperLogLog(std::uint8_t precision)
    : precision_(precision),
      register_count_(1ULL << precision),
      registers_(register_count_, 0) {
    if (precision_ < 4 || precision_ > 18) {
        throw std::invalid_argument("HyperLogLog precision must be between 4 and 18");
    }
}

void HyperLogLog::add(const std::string& value) {
    const auto hash = murmurhash3_64(value.data(), value.size(), 0xadc83b19ULL);
    const std::size_t index = hash >> (64 - precision_);
    const std::uint64_t remaining = (hash << precision_);
    const std::uint8_t rank = rho(remaining, static_cast<std::uint8_t>(64 - precision_));
    registers_[index] = std::max(registers_[index], rank);
}

void HyperLogLog::merge(const HyperLogLog& other) {
    if (other.precision_ != precision_) {
        throw std::invalid_argument("Cannot merge HyperLogLog with different precision");
    }
    for (std::size_t i = 0; i < register_count_; ++i) {
        registers_[i] = std::max(registers_[i], other.registers_[i]);
    }
}

std::uint64_t HyperLogLog::cardinality() const {
    const double alpha_m = alpha(register_count_);
    double sum = 0.0;
    for (std::uint8_t reg : registers_) {
        sum += std::pow(2.0, -static_cast<int>(reg));
    }

    double estimate = alpha_m * register_count_ * register_count_ / sum;
    const std::size_t zeros = static_cast<std::size_t>(std::count(registers_.begin(), registers_.end(), 0));

    if (estimate <= 5.0 * register_count_) {
        if (zeros != 0) {
            estimate = register_count_ * std::log(static_cast<double>(register_count_) / zeros);
        }
    } else if (estimate > (1ULL << 32) / 30.0) {
        estimate = -static_cast<double>(1ULL << 32) * std::log(1.0 - estimate / (1ULL << 32));
    }

    if (estimate < 0.0) {
        estimate = 0.0;
    }

    return static_cast<std::uint64_t>(estimate + 0.5);
}

double HyperLogLog::alpha(std::size_t m) {
    switch (m) {
        case 16: return 0.673;
        case 32: return 0.697;
        case 64: return 0.709;
        default: return 0.7213 / (1.0 + 1.079 / static_cast<double>(m));
    }
}

std::uint8_t HyperLogLog::rho(std::uint64_t x, std::uint8_t max_bits) {
    std::uint8_t count = 1;
    while (count <= max_bits) {
        if (x & (1ULL << (64 - 1))) {
            break;
        }
        ++count;
        x <<= 1U;
    }
    return count;
}

} // namespace engagehub

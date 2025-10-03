#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace engagehub {

class HyperLogLog {
public:
    explicit HyperLogLog(std::uint8_t precision = 14);

    void add(const std::string& value);
    void merge(const HyperLogLog& other);

    std::uint64_t cardinality() const;
    std::uint8_t precision() const noexcept { return precision_; }

private:
    static double alpha(std::size_t m);
    static std::uint8_t rho(std::uint64_t x, std::uint8_t max_bits);

    std::uint8_t precision_;
    std::size_t register_count_;
    std::vector<std::uint8_t> registers_;
};

} // namespace engagehub

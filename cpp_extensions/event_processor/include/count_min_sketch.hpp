#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace engagehub {

class CountMinSketch {
public:
    CountMinSketch(std::size_t width = 2048, std::size_t depth = 4, std::uint64_t seed = 12345);

    void increment(const std::string& key, std::uint64_t count = 1);
    std::uint64_t estimate(const std::string& key) const;

    std::size_t width() const noexcept { return width_; }
    std::size_t depth() const noexcept { return depth_; }

private:
    std::uint64_t hash(const std::string& key, std::size_t index) const;

    std::size_t width_;
    std::size_t depth_;
    std::uint64_t seed_;
    std::vector<std::uint64_t> table_;
};

} // namespace engagehub

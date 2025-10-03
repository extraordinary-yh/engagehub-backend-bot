#include "time_decay.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace engagehub::leaderboard {

TimeDecay::TimeDecay(double decay_factor)
    : decay_factor_(decay_factor) {
    if (decay_factor_ <= 0.0 || decay_factor_ > 1.0) {
        throw std::invalid_argument("Decay factor must be in (0, 1]");
    }
}

double TimeDecay::apply(double base_score, std::int64_t last_update_timestamp, std::int64_t current_timestamp) const {
    if (current_timestamp <= last_update_timestamp) {
        return base_score;
    }
    const auto delta = static_cast<double>(current_timestamp - last_update_timestamp);
    const double days = delta / 86400.0;
    if (days <= 0.0) {
        return base_score;
    }
    const double factor = std::pow(decay_factor_, days);
    return base_score * factor;
}

} // namespace engagehub::leaderboard

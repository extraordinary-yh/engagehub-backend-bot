#pragma once

#include <cstdint>

namespace engagehub::leaderboard {

class TimeDecay {
public:
    explicit TimeDecay(double decay_factor = 0.95);

    double apply(double base_score, std::int64_t last_update_timestamp, std::int64_t current_timestamp) const;
    double decay_factor() const noexcept { return decay_factor_; }

private:
    double decay_factor_;
};

} // namespace engagehub::leaderboard

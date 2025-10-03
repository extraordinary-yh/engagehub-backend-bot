#pragma once

#include "skip_list.hpp"
#include "time_decay.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace engagehub::leaderboard {

struct RankEntry {
    std::string user_id;
    double score;
    std::size_t rank;
    std::int64_t last_update;
};

using RankInfo = RankEntry;

class Leaderboard {
public:
    explicit Leaderboard(double decay_factor = 0.95, std::size_t max_users = 100000);

    void update_user(const std::string& user_id, double points, std::int64_t timestamp);

    std::vector<RankEntry> get_top_users(std::size_t k);
    std::optional<RankInfo> get_user_rank(const std::string& user_id);

    void save_to_json(const std::string& filepath);
    void load_from_json(const std::string& filepath);

    std::size_t size() const;

    double get_current_time() const;

    void set_time_source(std::function<std::int64_t()> clock_fn);

private:
    void refresh_scores_locked(std::int64_t now);

    SkipList skip_list_;
    TimeDecay decay_;
    std::size_t max_users_;

    std::function<std::int64_t()> clock_fn_;
    mutable std::mutex mutex_;
};

} // namespace engagehub::leaderboard

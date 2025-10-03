#include "leaderboard.hpp"

#include <chrono>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace engagehub::leaderboard {
namespace {
std::int64_t default_now_seconds() {
    using namespace std::chrono;
    return duration_cast<seconds>(system_clock::now().time_since_epoch()).count();
}

std::string trim(const std::string& input) {
    const auto begin = input.find_first_not_of(" \t\n\r");
    if (begin == std::string::npos) {
        return "";
    }
    const auto end = input.find_last_not_of(" \t\n\r");
    return input.substr(begin, end - begin + 1);
}

std::string escape_json(const std::string& input) {
    std::string out;
    out.reserve(input.size());
    for (char ch : input) {
        switch (ch) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            default: out += ch; break;
        }
    }
    return out;
}

} // namespace

Leaderboard::Leaderboard(double decay_factor, std::size_t max_users)
    : skip_list_(16, 0.5),
      decay_(decay_factor),
      max_users_(max_users),
      clock_fn_(default_now_seconds) {}

void Leaderboard::set_time_source(std::function<std::int64_t()> clock_fn) {
    std::lock_guard<std::mutex> lock(mutex_);
    clock_fn_ = std::move(clock_fn);
}

void Leaderboard::update_user(const std::string& user_id, double points, std::int64_t timestamp) {
    std::lock_guard<std::mutex> lock(mutex_);
    const std::int64_t now = timestamp > 0 ? timestamp : clock_fn_();
    if (points == 0.0 && skip_list_.find(user_id) == nullptr) {
        return;
    }

    double new_score = points;
    if (auto* existing = skip_list_.find(user_id)) {
        const double decayed = decay_.apply(existing->score, existing->last_update, now);
        new_score = decayed + points;
    }

    skip_list_.upsert(user_id, new_score, now);

    if (max_users_ > 0 && skip_list_.size() > max_users_) {
        if (auto* tail = skip_list_.tail()) {
            if (tail->user_id != user_id || skip_list_.size() > max_users_) {
                skip_list_.erase(tail->user_id);
            }
        }
    }
}

std::vector<RankEntry> Leaderboard::get_top_users(std::size_t k) {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto now = clock_fn_();
    refresh_scores_locked(now);
    std::vector<RankEntry> results;
    const auto nodes = skip_list_.top_k(k);
    results.reserve(nodes.size());
    std::size_t rank = 1;
    for (const auto* node : nodes) {
        results.push_back(RankEntry{node->user_id, node->score, rank++, node->last_update});
    }
    return results;
}

std::optional<RankInfo> Leaderboard::get_user_rank(const std::string& user_id) {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto now = clock_fn_();
    refresh_scores_locked(now);

    const auto* node = skip_list_.find(user_id);
    if (!node) {
        return std::nullopt;
    }
    const auto rank = skip_list_.rank_of(user_id);
    return RankInfo{node->user_id, node->score, rank, node->last_update};
}

void Leaderboard::save_to_json(const std::string& filepath) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::ofstream out(filepath);
    if (!out) {
        throw std::runtime_error("Failed to open file for writing: " + filepath);
    }

    out << "{\n";
    out << "  \"decay_factor\": " << decay_.decay_factor() << ",\n";
    out << "  \"max_users\": " << max_users_ << ",\n";
    out << "  \"entries\": [\n";
    bool first = true;
    skip_list_.for_each([&](const SkipList::Node& node) {
        if (!first) {
            out << ",\n";
        }
        first = false;
        out << "    {\"user_id\": \"" << escape_json(node.user_id) << "\", "
            "\"score\": " << node.score << ", \"last_update\": " << node.last_update << "}";
    });
    out << "\n  ]\n";
    out << "}\n";
}

void Leaderboard::load_from_json(const std::string& filepath) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::ifstream in(filepath);
    if (!in) {
        throw std::runtime_error("Failed to open file for reading: " + filepath);
    }
    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());

    const auto extract_numeric = [&](const std::string& key) -> std::optional<std::string> {
        const std::string needle = "\"" + key + "\"";
        const auto key_pos = content.find(needle);
        if (key_pos == std::string::npos) {
            return std::nullopt;
        }
        const auto colon = content.find(':', key_pos);
        if (colon == std::string::npos) {
            return std::nullopt;
        }
        const auto end = content.find_first_of(",}\n", colon + 1);
        return trim(content.substr(colon + 1, end - colon - 1));
    };

    if (auto decay_value = extract_numeric("decay_factor")) {
        decay_ = TimeDecay(std::stod(*decay_value));
    }
    if (auto max_users_value = extract_numeric("max_users")) {
        max_users_ = static_cast<std::size_t>(std::stoull(*max_users_value));
    }

    skip_list_.clear();

    const auto entries_pos = content.find("\"entries\"");
    if (entries_pos == std::string::npos) {
        return;
    }
    const auto array_start = content.find('[', entries_pos);
    const auto array_end = content.find(']', array_start);
    if (array_start == std::string::npos || array_end == std::string::npos) {
        return;
    }
    std::string entries_block = content.substr(array_start + 1, array_end - array_start - 1);

    std::size_t pos = 0;
    while (true) {
        const auto obj_start = entries_block.find('{', pos);
        if (obj_start == std::string::npos) {
            break;
        }
        const auto obj_end = entries_block.find('}', obj_start);
        if (obj_end == std::string::npos) {
            break;
        }
        const std::string obj = entries_block.substr(obj_start + 1, obj_end - obj_start - 1);

        auto extract_value = [&](const std::string& key) -> std::optional<std::string> {
            const std::string needle = "\"" + key + "\"";
            const auto key_position = obj.find(needle);
            if (key_position == std::string::npos) {
                return std::nullopt;
            }
            const auto colon_pos = obj.find(':', key_position);
            if (colon_pos == std::string::npos) {
                return std::nullopt;
            }
            if (key == "user_id") {
                const auto first_quote = obj.find('"', colon_pos + 1);
                if (first_quote == std::string::npos) {
                    return std::nullopt;
                }
                const auto second_quote = obj.find('"', first_quote + 1);
                if (second_quote == std::string::npos) {
                    return std::nullopt;
                }
                return obj.substr(first_quote + 1, second_quote - first_quote - 1);
            }
            const auto value_end = obj.find_first_of(",}\n", colon_pos + 1);
            return trim(obj.substr(colon_pos + 1, value_end - colon_pos - 1));
        };

        const auto user_opt = extract_value("user_id");
        const auto score_opt = extract_value("score");
        const auto timestamp_opt = extract_value("last_update");

        if (user_opt && score_opt && timestamp_opt) {
            const auto user = *user_opt;
            const double score = std::stod(*score_opt);
            const std::int64_t ts = std::stoll(*timestamp_opt);
            skip_list_.upsert(user, score, ts);
        }

        pos = obj_end + 1;
    }
}

std::size_t Leaderboard::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return skip_list_.size();
}

double Leaderboard::get_current_time() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return static_cast<double>(clock_fn_());
}

void Leaderboard::refresh_scores_locked(std::int64_t now) {
    std::vector<std::pair<std::string, double>> updates;
    updates.reserve(skip_list_.size());
    skip_list_.for_each([&](const SkipList::Node& node) {
        const double decayed = decay_.apply(node.score, node.last_update, now);
        if (std::fabs(decayed - node.score) > 1e-6 || node.last_update != now) {
            updates.emplace_back(node.user_id, decayed);
        }
    });
    for (const auto& [user, score] : updates) {
        skip_list_.upsert(user, score, now);
    }
}

} // namespace engagehub::leaderboard

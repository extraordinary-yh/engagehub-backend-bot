#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

namespace engagehub::leaderboard {

class SkipList {
public:
    struct Node {
        std::string user_id;
        double score;
        std::int64_t last_update;
        std::vector<Node*> forward;
    };

    SkipList(int max_levels = 16, double probability = 0.5);
    ~SkipList();

    Node* upsert(const std::string& user_id, double score, std::int64_t timestamp);
    Node* find(const std::string& user_id) const;
    bool erase(const std::string& user_id);
    std::size_t size() const noexcept { return size_; }
    Node* tail() const;
    void clear();

    std::vector<const Node*> top_k(std::size_t k) const;
    std::size_t rank_of(const std::string& user_id) const;

    template <typename Fn>
    void for_each(Fn&& fn) const {
        Node* current = header_->forward[0];
        while (current) {
            fn(*current);
            current = current->forward[0];
        }
    }

private:
    int random_level();
    bool comes_before(const Node* lhs, double score, const std::string& user_id) const;
    void insert_node(Node* node, int level, const std::vector<Node*>& update);

    std::unique_ptr<Node> header_;
    int max_levels_;
    double probability_;
    int current_level_;
    std::size_t size_;
    mutable std::mt19937_64 rng_;
    std::unordered_map<std::string, Node*> index_;
};

} // namespace engagehub::leaderboard

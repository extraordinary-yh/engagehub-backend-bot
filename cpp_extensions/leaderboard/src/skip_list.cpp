#include "skip_list.hpp"

#include <algorithm>
#include <stdexcept>

namespace engagehub::leaderboard {

namespace {
constexpr int kMaxSupportedLevels = 32;
}

SkipList::SkipList(int max_levels, double probability)
    : header_(std::make_unique<Node>()),
      max_levels_(max_levels),
      probability_(probability),
      current_level_(1),
      size_(0),
      rng_(std::random_device{}()) {
    if (max_levels_ <= 0 || max_levels_ > kMaxSupportedLevels) {
        throw std::invalid_argument("SkipList max_levels out of supported range");
    }
    if (probability_ <= 0.0 || probability_ >= 1.0) {
        throw std::invalid_argument("SkipList probability must be in (0,1)");
    }
    header_->score = 0.0;
    header_->last_update = 0;
    header_->forward.assign(static_cast<std::size_t>(max_levels_), nullptr);
}

SkipList::~SkipList() {
    Node* current = header_->forward[0];
    while (current) {
        Node* next = current->forward[0];
        delete current;
        current = next;
    }
}

int SkipList::random_level() {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    int level = 1;
    while (level < max_levels_ && dist(rng_) < probability_) {
        ++level;
    }
    return level;
}

bool SkipList::comes_before(const Node* lhs, double score, const std::string& user_id) const {
    if (lhs->score > score) {
        return true;
    }
    if (lhs->score < score) {
        return false;
    }
    return lhs->user_id < user_id;
}

SkipList::Node* SkipList::upsert(const std::string& user_id, double score, std::int64_t timestamp) {
    erase(user_id);

    const int node_level = random_level();
    auto* node = new Node{user_id, score, timestamp, std::vector<Node*>(static_cast<std::size_t>(node_level), nullptr)};

    std::vector<Node*> update(static_cast<std::size_t>(max_levels_), nullptr);
    Node* current = header_.get();
    for (int level = current_level_ - 1; level >= 0; --level) {
        while (current->forward[level] && comes_before(current->forward[level], score, user_id)) {
            current = current->forward[level];
        }
        update[static_cast<std::size_t>(level)] = current;
    }

    if (node_level > current_level_) {
        for (int level = current_level_; level < node_level; ++level) {
            update[static_cast<std::size_t>(level)] = header_.get();
        }
        current_level_ = node_level;
    }

    insert_node(node, node_level, update);
    index_[user_id] = node;
    ++size_;
    return node;
}

SkipList::Node* SkipList::find(const std::string& user_id) const {
    const auto it = index_.find(user_id);
    if (it == index_.end()) {
        return nullptr;
    }
    return it->second;
}

bool SkipList::erase(const std::string& user_id) {
    const auto it = index_.find(user_id);
    if (it == index_.end()) {
        return false;
    }
    Node* target = it->second;

    std::vector<Node*> update(static_cast<std::size_t>(max_levels_), nullptr);
    Node* current = header_.get();
    for (int level = current_level_ - 1; level >= 0; --level) {
        while (current->forward[level] && current->forward[level] != target &&
               comes_before(current->forward[level], target->score, target->user_id)) {
            current = current->forward[level];
        }
        update[static_cast<std::size_t>(level)] = current;
    }

    bool removed = false;
    for (int level = 0; level < static_cast<int>(target->forward.size()); ++level) {
        if (update[static_cast<std::size_t>(level)]->forward[level] == target) {
            update[static_cast<std::size_t>(level)]->forward[level] = target->forward[level];
            removed = true;
        }
    }

    if (!removed) {
        return false;
    }

    while (current_level_ > 1 && header_->forward[current_level_ - 1] == nullptr) {
        --current_level_;
    }

    index_.erase(it);
    --size_;
    delete target;
    return true;
}

void SkipList::clear() {
    Node* current = header_->forward[0];
    while (current) {
        Node* next = current->forward[0];
        delete current;
        current = next;
    }
    for (auto& ptr : header_->forward) {
        ptr = nullptr;
    }
    index_.clear();
    size_ = 0;
    current_level_ = 1;
}

std::vector<const SkipList::Node*> SkipList::top_k(std::size_t k) const {
    std::vector<const Node*> results;
    results.reserve(std::min(k, size_));
    Node* current = header_->forward[0];
    while (current && results.size() < k) {
        results.push_back(current);
        current = current->forward[0];
    }
    return results;
}

std::size_t SkipList::rank_of(const std::string& user_id) const {
    std::size_t rank = 1;
    Node* current = header_->forward[0];
    while (current) {
        if (current->user_id == user_id) {
            return rank;
        }
        ++rank;
        current = current->forward[0];
    }
    return 0;
}

SkipList::Node* SkipList::tail() const {
    Node* current = header_->forward[0];
    if (!current) {
        return nullptr;
    }
    while (current->forward[0]) {
        current = current->forward[0];
    }
    return current;
}

void SkipList::insert_node(Node* node, int level, const std::vector<Node*>& update) {
    for (int i = 0; i < level; ++i) {
        node->forward[i] = update[static_cast<std::size_t>(i)]->forward[i];
        update[static_cast<std::size_t>(i)]->forward[i] = node;
    }
}

} // namespace engagehub::leaderboard

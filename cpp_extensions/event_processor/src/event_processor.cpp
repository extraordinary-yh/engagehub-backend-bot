#include "event_processor.hpp"

#include <algorithm>
#include <chrono>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <thread>

namespace engagehub {
namespace {
constexpr std::int64_t kWindowSpanSeconds = 3600;
constexpr std::int64_t kBucketSpanSeconds = 60;

std::int64_t bucket_start(std::int64_t timestamp) {
    if (timestamp <= 0) {
        timestamp = static_cast<std::int64_t>(
            std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::system_clock::now().time_since_epoch())
                .count());
    }
    return (timestamp / kBucketSpanSeconds) * kBucketSpanSeconds;
}
} // namespace

EventStreamProcessor::EventStreamProcessor(std::size_t buffer_size,
                                           std::size_t num_threads,
                                           std::size_t batch_size,
                                           std::size_t flush_interval_ms)
    : batch_size_(batch_size == 0 ? 1 : batch_size),
      flush_interval_(std::chrono::milliseconds(flush_interval_ms == 0 ? 1 : flush_interval_ms)),
      buffer_(buffer_size == 0 ? 1024 : buffer_size),
      thread_pool_(num_threads == 0 ? std::thread::hardware_concurrency() : num_threads),
      channel_frequency_(),
      last_flush_time_(std::chrono::steady_clock::now()) {
    pending_batch_.reserve(batch_size_ * 2);
    running_.store(true, std::memory_order_release);
    consumer_thread_ = std::thread([this]() { consume_loop(); });
}

EventStreamProcessor::~EventStreamProcessor() {
    running_.store(false, std::memory_order_release);
    flush_requested_.store(true, std::memory_order_release);
    data_cv_.notify_all();
    if (consumer_thread_.joinable()) {
        consumer_thread_.join();
    }

    thread_pool_.shutdown();
}

bool EventStreamProcessor::push_event(const std::string& event_type,
                                      const std::string& user_id,
                                      const std::string& channel_id,
                                      std::int64_t timestamp) {
    Event event{event_type, user_id, channel_id, timestamp};
    const bool pushed = buffer_.push(std::move(event));
    if (!pushed) {
        events_dropped_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
    drained_.store(false, std::memory_order_release);
    data_cv_.notify_one();
    return true;
}

std::uint64_t EventStreamProcessor::get_unique_users_last_hour() {
    HyperLogLog aggregate;
    const auto now_seconds = static_cast<std::int64_t>(
        std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch())
            .count());
    const auto cutoff = now_seconds - kWindowSpanSeconds;

    std::lock_guard<std::mutex> lock(stats_mutex_);
    while (!windows_.empty() && windows_.front().window_start < cutoff) {
        windows_.pop_front();
    }
    for (const auto& window : windows_) {
        aggregate.merge(window.sketch);
    }
    return aggregate.cardinality();
}

std::vector<std::pair<std::string, std::uint64_t>> EventStreamProcessor::get_top_channels(std::size_t k) {
    std::vector<std::pair<std::string, std::uint64_t>> entries;
    {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        entries.reserve(channel_counts_.size());
        for (const auto& kv : channel_counts_) {
            entries.emplace_back(kv.first, kv.second);
        }
    }
    if (entries.size() > k) {
        std::partial_sort(entries.begin(), entries.begin() + k, entries.end(),
                          [](const auto& lhs, const auto& rhs) {
                              return lhs.second > rhs.second;
                          });
        entries.resize(k);
    } else {
        std::sort(entries.begin(), entries.end(),
                  [](const auto& lhs, const auto& rhs) {
                      return lhs.second > rhs.second;
                  });
    }
    return entries;
}

void EventStreamProcessor::set_flush_callback(std::function<void(std::vector<Event>)> callback) {
    std::lock_guard<std::mutex> lock(callback_mutex_);
    flush_callback_ = std::move(callback);
}

void EventStreamProcessor::flush_now() {
    flush_requested_.store(true, std::memory_order_release);
    data_cv_.notify_all();

    std::unique_lock<std::mutex> lock(flush_mutex_);
    flush_cv_.wait(lock, [this]() {
        return !flush_requested_.load(std::memory_order_acquire);
    });
    lock.unlock();

    std::unique_lock<std::mutex> pending_lock(pending_mutex_);
    pending_cv_.wait(pending_lock, [this]() {
        return pending_flush_tasks_.load(std::memory_order_acquire) == 0;
    });
    pending_lock.unlock();

    notify_idle_state();

    std::unique_lock<std::mutex> drain_lock(drain_mutex_);
    drain_cv_.wait(drain_lock, [this]() {
        return drained_.load(std::memory_order_acquire);
    });
}

void EventStreamProcessor::consume_loop() {
    last_flush_time_ = std::chrono::steady_clock::now();

    while (running_.load(std::memory_order_acquire) || !buffer_.empty()) {
        Event event;
        if (buffer_.pop(event)) {
            process_event(event);
            total_processed_.fetch_add(1, std::memory_order_relaxed);

            bool reached_batch = false;
            {
                std::lock_guard<std::mutex> lock(batch_mutex_);
                pending_batch_.push_back(std::move(event));
                reached_batch = pending_batch_.size() >= batch_size_;
            }

            if (reached_batch) {
                std::vector<Event> batch;
                {
                    std::lock_guard<std::mutex> lock(batch_mutex_);
                    batch.swap(pending_batch_);
                }
                flush_batch(batch);
                last_flush_time_ = std::chrono::steady_clock::now();
                notify_idle_state();
            }
            continue;
        }

        const auto now = std::chrono::steady_clock::now();
        bool should_flush = false;
        {
            std::lock_guard<std::mutex> lock(batch_mutex_);
            should_flush = !pending_batch_.empty() &&
                           (now - last_flush_time_ >= flush_interval_);
        }

        if (should_flush || flush_requested_.load(std::memory_order_acquire)) {
            std::vector<Event> batch;
            {
                std::lock_guard<std::mutex> lock(batch_mutex_);
                batch.swap(pending_batch_);
            }
            if (!batch.empty()) {
                flush_batch(batch);
            }
            last_flush_time_ = std::chrono::steady_clock::now();
            flush_requested_.store(false, std::memory_order_release);
            {
                std::lock_guard<std::mutex> lock(flush_mutex_);
                flush_cv_.notify_all();
            }
            notify_idle_state();
            continue;
        }

        std::unique_lock<std::mutex> lock(data_mutex_);
        data_cv_.wait_for(lock, std::chrono::milliseconds(5), [this]() {
            return !running_.load(std::memory_order_acquire) ||
                   !buffer_.empty() ||
                   flush_requested_.load(std::memory_order_acquire);
        });
        lock.unlock();
        notify_idle_state();
    }

    // drain remaining events
    std::vector<Event> remaining;
    {
        std::lock_guard<std::mutex> lock(batch_mutex_);
        remaining.swap(pending_batch_);
    }
    if (!remaining.empty()) {
        flush_batch(remaining);
    }
    flush_requested_.store(false, std::memory_order_release);
    {
        std::lock_guard<std::mutex> lock(flush_mutex_);
        flush_cv_.notify_all();
    }
    notify_idle_state();
}

void EventStreamProcessor::process_event(const Event& event) {
    const auto bucket = bucket_start(event.timestamp);
    const auto cutoff = bucket - kWindowSpanSeconds;

    std::lock_guard<std::mutex> lock(stats_mutex_);
    channel_frequency_.increment(event.channel_id);
    channel_counts_[event.channel_id] += 1;

    // maintain time windows for unique user estimation
    while (!windows_.empty() && windows_.front().window_start < cutoff) {
        windows_.pop_front();
    }

    auto it = std::find_if(windows_.begin(), windows_.end(), [&](const HyperLogLogWindow& window) {
        return window.window_start == bucket;
    });
    if (it == windows_.end()) {
        HyperLogLogWindow window{bucket, HyperLogLog()};
        window.sketch.add(event.user_id);
        windows_.push_back(std::move(window));
        std::sort(windows_.begin(), windows_.end(), [](const HyperLogLogWindow& lhs, const HyperLogLogWindow& rhs) {
            return lhs.window_start < rhs.window_start;
        });
    } else {
        it->sketch.add(event.user_id);
    }
}

void EventStreamProcessor::flush_batch(std::vector<Event>& batch) {
    if (batch.empty()) {
        return;
    }

    std::function<void(std::vector<Event>)> callback;
    {
        std::lock_guard<std::mutex> lock(callback_mutex_);
        callback = flush_callback_;
    }

    if (!callback) {
        std::lock_guard<std::mutex> lock(batch_mutex_);
        pending_batch_.insert(pending_batch_.end(),
                              std::make_move_iterator(batch.begin()),
                              std::make_move_iterator(batch.end()));
        batch.clear();
        return;
    }

    auto payload_data = std::make_shared<std::vector<Event>>(std::move(batch));
    batch.clear();

    pending_flush_tasks_.fetch_add(1, std::memory_order_acq_rel);
    try {
        thread_pool_.enqueue([this, callback, payload_data]() mutable {
            auto payload = std::move(*payload_data);
            payload_data->clear();
            try {
                callback(std::move(payload));
            } catch (...) {
                pending_flush_tasks_.fetch_sub(1, std::memory_order_acq_rel);
                pending_cv_.notify_all();
                notify_idle_state();
                throw;
            }
            pending_flush_tasks_.fetch_sub(1, std::memory_order_acq_rel);
            pending_cv_.notify_all();
            notify_idle_state();
        });
    } catch (...) {
        auto payload = std::move(*payload_data);
        payload_data->clear();
        try {
            callback(std::move(payload));
        } catch (...) {
            pending_flush_tasks_.fetch_sub(1, std::memory_order_acq_rel);
            pending_cv_.notify_all();
            notify_idle_state();
            throw;
        }
        pending_flush_tasks_.fetch_sub(1, std::memory_order_acq_rel);
        pending_cv_.notify_all();
        notify_idle_state();
    }
}

void EventStreamProcessor::notify_idle_state() {
    if (!buffer_.empty()) {
        drained_.store(false, std::memory_order_release);
        return;
    }

    bool batch_empty = false;
    {
        std::lock_guard<std::mutex> batch_lock(batch_mutex_);
        batch_empty = pending_batch_.empty();
    }
    if (!batch_empty) {
        drained_.store(false, std::memory_order_release);
        return;
    }

    if (pending_flush_tasks_.load(std::memory_order_acquire) != 0) {
        drained_.store(false, std::memory_order_release);
        return;
    }

    drained_.store(true, std::memory_order_release);
    std::lock_guard<std::mutex> lock(drain_mutex_);
    drain_cv_.notify_all();
}

} // namespace engagehub

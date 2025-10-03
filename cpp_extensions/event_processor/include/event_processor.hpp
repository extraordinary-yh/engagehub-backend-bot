#pragma once

#include "count_min_sketch.hpp"
#include "hyperloglog.hpp"
#include "ring_buffer.hpp"
#include "thread_pool.hpp"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>
#include <thread>

namespace engagehub {

struct Event {
    std::string event_type;
    std::string user_id;
    std::string channel_id;
    std::int64_t timestamp;
};

class EventStreamProcessor {
public:
    EventStreamProcessor(std::size_t buffer_size,
                         std::size_t num_threads,
                         std::size_t batch_size,
                         std::size_t flush_interval_ms);
    ~EventStreamProcessor();

    bool push_event(const std::string& event_type,
                    const std::string& user_id,
                    const std::string& channel_id,
                    std::int64_t timestamp);

    std::uint64_t get_unique_users_last_hour();
    std::vector<std::pair<std::string, std::uint64_t>> get_top_channels(std::size_t k);

    void set_flush_callback(std::function<void(std::vector<Event>)> callback);
    void flush_now();

    std::uint64_t total_events_processed() const noexcept { return total_processed_.load(std::memory_order_relaxed); }
    std::uint64_t events_dropped() const noexcept { return events_dropped_.load(std::memory_order_relaxed); }

private:
    using Buffer = LockFreeRingBuffer<Event, 0>;

    struct HyperLogLogWindow {
        std::int64_t window_start;
        HyperLogLog sketch;
    };

    void consume_loop();
    void process_event(const Event& event);
    void flush_batch(std::vector<Event>& batch);
    void notify_idle_state();

    std::size_t batch_size_;
    std::chrono::milliseconds flush_interval_;

    Buffer buffer_;
    ThreadPool thread_pool_;

    std::function<void(std::vector<Event>)> flush_callback_;
    mutable std::mutex callback_mutex_;

    std::atomic<bool> running_;
    std::thread consumer_thread_;

    std::atomic<std::uint64_t> total_processed_{0};
    std::atomic<std::uint64_t> events_dropped_{0};

    CountMinSketch channel_frequency_;

    std::mutex stats_mutex_;
    std::deque<HyperLogLogWindow> windows_;
    std::unordered_map<std::string, std::uint64_t> channel_counts_;

    std::mutex batch_mutex_;
    std::vector<Event> pending_batch_;

    std::mutex data_mutex_;
    std::condition_variable data_cv_;

    std::mutex flush_mutex_;
    std::condition_variable flush_cv_;
    std::atomic<bool> flush_requested_{false};

    std::chrono::steady_clock::time_point last_flush_time_;

    std::atomic<std::size_t> pending_flush_tasks_{0};
    std::mutex pending_mutex_;
    std::condition_variable pending_cv_;

    std::mutex drain_mutex_;
    std::condition_variable drain_cv_;
    std::atomic<bool> drained_{true};
};

} // namespace engagehub

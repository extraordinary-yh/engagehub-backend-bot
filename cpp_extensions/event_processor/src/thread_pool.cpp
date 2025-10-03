#include "thread_pool.hpp"

#include <stdexcept>

namespace engagehub {

ThreadPool::ThreadPool(std::size_t num_threads)
    : stopping_(false) {
    if (num_threads == 0) {
        num_threads = 1;
    }
    workers_.reserve(num_threads);
    for (std::size_t i = 0; i < num_threads; ++i) {
        workers_.emplace_back([this]() { worker_loop(); });
    }
}

ThreadPool::~ThreadPool() {
    shutdown();
}

void ThreadPool::enqueue(std::function<void()> task) {
    if (stopping_.load(std::memory_order_acquire)) {
        throw std::runtime_error("ThreadPool enqueue on stopped pool");
    }
    {
        std::lock_guard<std::mutex> lock(mutex_);
        tasks_.push(std::move(task));
    }
    cv_.notify_one();
}

void ThreadPool::shutdown() {
    bool expected = false;
    if (!stopping_.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) {
        return; // already stopped
    }

    cv_.notify_all();
    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    workers_.clear();

    {
        std::lock_guard<std::mutex> lock(mutex_);
        while (!tasks_.empty()) {
            tasks_.pop();
        }
    }
}

void ThreadPool::worker_loop() {
    while (true) {
        std::function<void()> task;
        {
            std::unique_lock<std::mutex> lock(mutex_);
            cv_.wait(lock, [this]() { return stopping_.load(std::memory_order_acquire) || !tasks_.empty(); });
            if (stopping_.load(std::memory_order_acquire) && tasks_.empty()) {
                return;
            }
            task = std::move(tasks_.front());
            tasks_.pop();
        }
        try {
            task();
        } catch (...) {
            // swallow exceptions to keep pool alive
        }
    }
}

} // namespace engagehub

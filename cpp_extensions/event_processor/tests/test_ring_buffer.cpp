#include <catch2/catch_test_macros.hpp>

#include "ring_buffer.hpp"

#include <atomic>
#include <thread>
#include <vector>

using engagehub::LockFreeRingBuffer;

TEST_CASE("LockFreeRingBuffer single-thread operations") {
    LockFreeRingBuffer<int, 0> buffer(8);

    for (int i = 0; i < 8; ++i) {
        REQUIRE(buffer.push(i));
    }
    REQUIRE_FALSE(buffer.push(42));

    int value = 0;
    for (int i = 0; i < 8; ++i) {
        REQUIRE(buffer.pop(value));
        REQUIRE(value == i);
    }
    REQUIRE_FALSE(buffer.pop(value));
}

TEST_CASE("LockFreeRingBuffer multi producer multi consumer") {
    constexpr int producer_count = 4;
    constexpr int consumer_count = 4;
    constexpr int values_per_producer = 2000;
    LockFreeRingBuffer<int, 0> buffer(1024);

    std::atomic<int> produced{0};
    std::atomic<int> consumed{0};

    std::vector<std::thread> producers;
    producers.reserve(producer_count);
    for (int p = 0; p < producer_count; ++p) {
        producers.emplace_back([&buffer, &produced]() {
            for (int i = 0; i < values_per_producer; ++i) {
                while (!buffer.push(i)) {
                    std::this_thread::yield();
                }
                ++produced;
            }
        });
    }

    std::vector<std::thread> consumers;
    consumers.reserve(consumer_count);
    for (int c = 0; c < consumer_count; ++c) {
        consumers.emplace_back([&buffer, &consumed, total = producer_count * values_per_producer]() {
            int value = 0;
            while (consumed.load(std::memory_order_relaxed) < total) {
                if (buffer.pop(value)) {
                    ++consumed;
                } else {
                    std::this_thread::yield();
                }
            }
        });
    }

    for (auto& thread : producers) {
        thread.join();
    }
    for (auto& thread : consumers) {
        thread.join();
    }

    REQUIRE(produced.load() == producer_count * values_per_producer);
    REQUIRE(consumed.load() == producer_count * values_per_producer);
}

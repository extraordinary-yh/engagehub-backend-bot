#include <catch2/benchmark/catch_benchmark.hpp>
#include <catch2/catch_test_macros.hpp>

#include "event_processor.hpp"

#include <atomic>

using engagehub::EventStreamProcessor;

TEST_CASE("Event processor benchmark", "[benchmark]") {
    EventStreamProcessor processor(4096, 4, 256, 100);
    std::atomic<int> flushed{0};
    processor.set_flush_callback([&flushed](std::vector<engagehub::Event> events) {
        flushed.fetch_add(static_cast<int>(events.size()), std::memory_order_relaxed);
    });

    BENCHMARK("push_event") {
        processor.push_event("message", "user", "channel", 1696284800);
    };

    processor.flush_now();
    REQUIRE(flushed.load() >= 0);
}

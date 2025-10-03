#include <catch2/catch_test_macros.hpp>

#include "count_min_sketch.hpp"
#include "hyperloglog.hpp"

#include <cmath>
#include <string>

using engagehub::CountMinSketch;
using engagehub::HyperLogLog;

TEST_CASE("CountMinSketch approximates frequencies") {
    CountMinSketch sketch(2048, 4, 1337);

    for (int i = 0; i < 1000; ++i) {
        sketch.increment("alpha");
    }
    for (int i = 0; i < 500; ++i) {
        sketch.increment("beta");
    }
    for (int i = 0; i < 50; ++i) {
        sketch.increment("gamma");
    }

    REQUIRE(sketch.estimate("alpha") >= 1000);
    REQUIRE(sketch.estimate("beta") >= 500);
    REQUIRE(sketch.estimate("gamma") >= 50);

    const auto alpha_over = sketch.estimate("alpha") - 1000;
    REQUIRE(alpha_over <= 50);
}

TEST_CASE("HyperLogLog estimates unique counts") {
    HyperLogLog hll(14);

    for (int i = 0; i < 8000; ++i) {
        hll.add("user-" + std::to_string(i));
    }

    const auto estimate = hll.cardinality();
    REQUIRE(estimate > 7600);
    REQUIRE(estimate < 8400);
}

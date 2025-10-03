#include <catch2/benchmark/catch_benchmark.hpp>
#include <catch2/catch_test_macros.hpp>

#include "leaderboard.hpp"

#include <string>

using engagehub::leaderboard::Leaderboard;

TEST_CASE("Leaderboard benchmark", "[benchmark]") {
    Leaderboard board(0.95, 100000);
    const auto base_time = static_cast<std::int64_t>(1696284800);

    BENCHMARK("update_user") {
        static int counter = 0;
        const std::string user = "user" + std::to_string(counter++);
        board.update_user(user, 10.0, base_time + counter);
    };

    const auto top = board.get_top_users(5);
    REQUIRE(top.size() <= 5);
}

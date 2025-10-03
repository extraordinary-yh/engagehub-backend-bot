#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>

#include "leaderboard.hpp"
#include "skip_list.hpp"

#include <cmath>
#include <vector>

using Catch::Approx;
using engagehub::leaderboard::Leaderboard;
using engagehub::leaderboard::RankEntry;
using engagehub::leaderboard::SkipList;

TEST_CASE("SkipList maintains sorted order") {
    SkipList list;
    list.upsert("alice", 50.0, 1000);
    list.upsert("bob", 150.0, 1000);
    list.upsert("carol", 100.0, 1000);

    const auto top = list.top_k(3);
    REQUIRE(top.size() == 3);
    REQUIRE(top[0]->user_id == "bob");
    REQUIRE(top[1]->user_id == "carol");
    REQUIRE(top[2]->user_id == "alice");

    REQUIRE(list.rank_of("bob") == 1);
    REQUIRE(list.rank_of("alice") == 3);
}

TEST_CASE("Leaderboard applies time decay") {
    Leaderboard board(0.95, 10);
    board.set_time_source([]() { return static_cast<std::int64_t>(1696284800); });

    board.update_user("alice", 100.0, 1696284800);

    // Fast forward 2 days using injected clock
    board.set_time_source([]() { return static_cast<std::int64_t>(1696284800 + 2 * 86400); });

    const auto maybe_rank = board.get_user_rank("alice");
    REQUIRE(maybe_rank.has_value());
    const auto rank = maybe_rank.value();

    const double expected = 100.0 * std::pow(0.95, 2.0);
    REQUIRE(rank.score == Approx(expected).epsilon(0.05));
}

TEST_CASE("Leaderboard top-k returns ranked entries") {
    Leaderboard board(0.95, 10);
    const auto base_time = static_cast<std::int64_t>(1696284800);
    board.update_user("alice", 50.0, base_time);
    board.update_user("bob", 75.0, base_time);
    board.update_user("carol", 30.0, base_time);

    const auto top = board.get_top_users(2);
    REQUIRE(top.size() == 2);
    REQUIRE(top[0].user_id == "bob");
    REQUIRE(top[0].rank == 1);
    REQUIRE(top[1].user_id == "alice");
    REQUIRE(top[1].rank == 2);
}

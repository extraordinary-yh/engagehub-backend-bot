import math
import time

import pytest

import cpp_leaderboard


def test_leaderboard_update_and_query(tmp_path):
    board = cpp_leaderboard.Leaderboard(decay_factor=0.95, max_users=100)
    now = int(time.time())

    board.update_user("alice", 100.0, now)
    board.update_user("bob", 75.0, now)
    board.update_user("carol", 50.0, now)

    top = board.get_top_users(2)
    assert len(top) == 2
    assert top[0]["user_id"] == "alice"
    assert top[0]["rank"] == 1
    assert top[1]["user_id"] == "bob"
    assert top[1]["rank"] == 2

    rank_info = board.get_user_rank("carol")
    assert rank_info is not None
    assert rank_info["rank"] == 3

    snapshot = tmp_path / "leaderboard.json"
    board.save_to_json(str(snapshot))

    restored = cpp_leaderboard.Leaderboard()
    restored.load_from_json(str(snapshot))

    restored_rank = restored.get_user_rank("alice")
    assert restored_rank is not None
    assert pytest.approx(restored_rank["score"], rel=1e-3) == top[0]["score"]


def test_leaderboard_decay():
    board = cpp_leaderboard.Leaderboard(decay_factor=0.95)
    start = 1696284800
    board.update_user("user", 100.0, start)

    # Query 3 days later
    later = start + 3 * 86400
    board.update_user("user", 0.0, later)
    board.set_time_source(lambda: later)

    rank = board.get_user_rank("user")
    assert rank is not None
    expected = 100.0 * math.pow(0.95, 3.0)
    assert rank["score"] == pytest.approx(expected, rel=0.05)

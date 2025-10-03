"""Example integration of the EngageHub C++ extensions with a Django-style workflow."""

from __future__ import annotations

import time
from typing import List, Mapping

import cpp_event_processor
import cpp_leaderboard


processor = cpp_event_processor.EventStreamProcessor(
    buffer_size=16384,
    num_threads=4,
    batch_size=512,
    flush_interval_ms=500,
)


def flush_to_database(events: List[Mapping[str, object]]) -> None:
    """Persist a batch of events using Django's bulk APIs."""
    # In production this would translate each event dict into a Django ORM instance.
    # For illustration we just print the batch size.
    print(f"[flush] Persisting {len(events)} events to PostgreSQL")


processor.set_flush_callback(flush_to_database)

leaderboard = cpp_leaderboard.Leaderboard(decay_factor=0.95, max_users=100000)


def record_message(user_id: str, channel_id: str) -> None:
    now = int(time.time())
    processor.push_event("message", user_id, channel_id, now)
    leaderboard.update_user(user_id, points=5.0, timestamp=now)


def show_top_users(limit: int = 10) -> None:
    top_users = leaderboard.get_top_users(limit)
    print("=== CURRENT LEADERBOARD ===")
    for entry in top_users:
        print(f"#{entry['rank']:>2} {entry['user_id']:<16} {entry['score']:.2f} pts")


if __name__ == "__main__":
    for i in range(100):
        record_message(user_id=f"user-{i % 8}", channel_id="general")
    processor.flush_now()
    show_top_users(5)

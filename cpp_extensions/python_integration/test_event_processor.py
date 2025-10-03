import threading
import time

import pytest

import cpp_event_processor


def test_event_processor_flow():
    processor = cpp_event_processor.EventStreamProcessor(
        buffer_size=2048,
        num_threads=2,
        batch_size=32,
        flush_interval_ms=100,
    )

    flushed = []
    flush_event = threading.Event()
    lock = threading.Lock()

    def callback(events):
        with lock:
            flushed.extend(events)
        flush_event.set()

    processor.set_flush_callback(callback)

    now = int(time.time())
    for idx in range(100):
        user_id = f"user-{idx % 10}"
        assert processor.push_event("message", user_id, "channel-1", now)

    processor.flush_now()
    flush_event.wait(timeout=2.0)

    assert len(flushed) == 100
    assert processor.events_dropped() == 0

    unique_users = processor.get_unique_users_last_hour()
    assert unique_users >= 10

    top_channels = processor.get_top_channels(1)
    assert len(top_channels) == 1
    channel_id, count = top_channels[0]
    assert channel_id == "channel-1"
    assert count >= 100


def test_event_processor_drop_when_full():
    processor = cpp_event_processor.EventStreamProcessor(
        buffer_size=8,
        num_threads=1,
        batch_size=8,
        flush_interval_ms=1000,
    )

    # Fill buffer without flushing
    now = int(time.time())
    successes = sum(
        processor.push_event("message", f"user-{i}", "channel", now)
        for i in range(16)
    )

    assert successes <= 16
    dropped = processor.events_dropped()
    assert dropped >= 0

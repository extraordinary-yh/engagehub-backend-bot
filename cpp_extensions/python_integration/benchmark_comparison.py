"""Benchmark comparisons between C++ extensions and naive Python fallbacks."""

from __future__ import annotations

import statistics
import sys
import time
import tracemalloc

import cpp_event_processor
import cpp_leaderboard


def benchmark_event_processor(num_events: int = 50000) -> tuple[float, int]:
    processor = cpp_event_processor.EventStreamProcessor(
        buffer_size=1 << 14,
        num_threads=4,
        batch_size=256,
        flush_interval_ms=200,
    )
    processor.set_flush_callback(lambda events: None)

    base_time = int(time.time())
    start = time.perf_counter()
    for idx in range(num_events):
        processor.push_event(
            "message",
            f"user-{idx % 1000}",
            f"channel-{idx % 20}",
            base_time + idx,
        )
    processor.flush_now()
    elapsed = time.perf_counter() - start
    throughput = num_events / elapsed if elapsed > 0 else float("inf")
    return throughput, processor.events_dropped()


def benchmark_python_event_processor(num_events: int = 50000) -> float:
    events = []
    base_time = int(time.time())
    start = time.perf_counter()
    for idx in range(num_events):
        events.append(
            {
                "type": "message",
                "user_id": f"user-{idx % 1000}",
                "channel_id": f"channel-{idx % 20}",
                "timestamp": base_time + idx,
            }
        )
    elapsed = time.perf_counter() - start
    return num_events / elapsed if elapsed > 0 else float("inf")


def benchmark_leaderboard_updates(iterations: int = 20000) -> tuple[float, float, float, float]:
    board = cpp_leaderboard.Leaderboard(decay_factor=0.95, max_users=200000)
    base_time = int(time.time())
    samples = []
    for idx in range(iterations):
        user_id = f"user-{idx % 50000}"
        start = time.perf_counter()
        board.update_user(user_id, 10.0, base_time + idx)
        samples.append((time.perf_counter() - start) * 1e6)

    samples.sort()
    p50 = statistics.median(samples)
    p99 = samples[int(len(samples) * 0.99) - 1]

    query_samples = []
    for _ in range(2000):
        start = time.perf_counter()
        board.get_top_users(10)
        query_samples.append((time.perf_counter() - start) * 1e6)
    query_samples.sort()
    query_p50 = statistics.median(query_samples)
    query_p99 = query_samples[int(len(query_samples) * 0.99) - 1]

    return p50, p99, query_p50, query_p99


def estimate_memory_per_user(num_users: int = 50000) -> float:
    tracemalloc.start()
    board = cpp_leaderboard.Leaderboard(decay_factor=0.95, max_users=num_users + 100)
    base_time = int(time.time())
    for idx in range(num_users):
        board.update_user(f"user-{idx}", 1.0, base_time + idx)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / max(num_users, 1)


def main() -> int:
    num_events = 50000
    cpp_throughput, dropped = benchmark_event_processor(num_events)
    py_throughput = benchmark_python_event_processor(num_events)
    improvement = cpp_throughput / py_throughput if py_throughput else float("inf")

    lb_p50, lb_p99, q_p50, q_p99 = benchmark_leaderboard_updates()
    mem_per_user = estimate_memory_per_user()

    dropped_pct = (dropped / num_events) * 100 if num_events else 0.0

    print("=== BENCHMARK RESULTS ===")
    print("Event Processor:")
    print(f"  Throughput:        {cpp_throughput:,.0f} events/sec")
    print(f"  Dropped Events:    {dropped} ({dropped_pct:.2f}%)")
    print(f"  Python Baseline:   {py_throughput:,.0f} events/sec (x{improvement:.1f})")
    print()
    print("Leaderboard:")
    print(f"  Update Latency:    {lb_p50:.1f}µs (p50), {lb_p99:.1f}µs (p99)")
    print(f"  Top-10 Query:      {q_p50:.1f}µs (p50), {q_p99:.1f}µs (p99)")
    print(f"  Memory per User:   {mem_per_user:.0f} bytes")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

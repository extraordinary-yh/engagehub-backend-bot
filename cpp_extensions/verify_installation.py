#!/usr/bin/env python3
"""Quick verification that C++ extensions work correctly."""

import sys
import time

try:
    import cpp_event_processor
    import cpp_leaderboard
    print("✅ C++ modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)

# Test event processor
try:
    processor = cpp_event_processor.EventStreamProcessor(
        buffer_size=1000,
        num_threads=2,
        batch_size=50,
        flush_interval_ms=100
    )
    
    events_received = []
    processor.set_flush_callback(lambda e: events_received.extend(e))
    
    # Push some events
    timestamp = int(time.time())
    for i in range(100):
        processor.push_event("message", f"user{i}", "channel1", timestamp + i)
    
    processor.flush_now()
    
    unique_users = processor.get_unique_users_last_hour()
    top_channels = processor.get_top_channels(5)
    
    print(f"✅ Event Processor working:")
    print(f"   - Processed: {processor.total_events_processed()} events")
    print(f"   - Dropped: {processor.events_dropped()} events")
    print(f"   - Flushed: {len(events_received)} events")
    print(f"   - Unique users: {unique_users}")
    print(f"   - Top channels: {len(top_channels)}")
    
except Exception as e:
    print(f"❌ Event processor test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test leaderboard
try:
    lb = cpp_leaderboard.Leaderboard(decay_factor=0.95, max_users=1000)
    
    timestamp = int(time.time())
    lb.update_user("alice", 100.0, timestamp)
    lb.update_user("bob", 75.0, timestamp)
    lb.update_user("carol", 50.0, timestamp)
    
    top_3 = lb.get_top_users(3)
    alice_rank = lb.get_user_rank("alice")
    
    print(f"✅ Leaderboard working:")
    print(f"   - Size: {lb.size()} users")
    print(f"   - Top user: {top_3[0]['user_id']} (rank {top_3[0]['rank']}, score {top_3[0]['score']:.1f})")
    print(f"   - Alice rank: {alice_rank['rank']} (score {alice_rank['score']:.1f})")
    
except Exception as e:
    print(f"❌ Leaderboard test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 All verifications passed! Extensions are working correctly.")
print("\n📊 Quick Performance Test:")

# Quick perf test
start = time.perf_counter()
for i in range(10000):
    lb.update_user(f"user{i % 1000}", 10.0, timestamp + i)
elapsed = time.perf_counter() - start
throughput = 10000 / elapsed

print(f"   - 10K updates in {elapsed:.3f}s = {throughput:,.0f} updates/sec")
print(f"   - Avg latency: {(elapsed / 10000) * 1e6:.1f}µs per update")

start = time.perf_counter()
for i in range(1000):
    _ = lb.get_top_users(10)
elapsed = time.perf_counter() - start

print(f"   - 1K top-10 queries in {elapsed:.3f}s")
print(f"   - Avg query latency: {(elapsed / 1000) * 1e6:.1f}µs per query")

print("\n✅ READY FOR INTERVIEWS!")


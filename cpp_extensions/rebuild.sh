#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "=== Rebuilding C++ Extensions ==="
cd build

echo "Building event_processor..."
make cpp_event_processor -j4

echo "Building leaderboard..."
make cpp_leaderboard -j4

echo "=== Build Complete ===" 
echo "Event Processor: build/event_processor/cpp_event_processor.*.so"
echo "Leaderboard: build/leaderboard/cpp_leaderboard.*.so"


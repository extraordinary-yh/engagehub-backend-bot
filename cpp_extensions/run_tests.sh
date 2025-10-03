#!/bin/bash
set -e

cd "$(dirname "$0")"

export PYTHONPATH="$(pwd)/build/event_processor:$(pwd)/build/leaderboard:$PYTHONPATH"

echo "=== Running Python Integration Tests ==="
/usr/bin/python3 -m pytest python_integration/ -v -s

echo ""
echo "=== Running C++ Unit Tests ==="
./build/event_processor/event_processor_tests
./build/leaderboard/leaderboard_tests

echo ""
echo "=== All Tests Passed! ==="


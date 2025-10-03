#!/bin/bash
cd "$(dirname "$0")"

export PYTHONPATH="$(pwd)/build/event_processor:$(pwd)/build/leaderboard:$PYTHONPATH"

echo "=== Running Performance Benchmarks ==="
echo ""
/usr/bin/python3 python_integration/benchmark_comparison.py


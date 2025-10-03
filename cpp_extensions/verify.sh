#!/bin/sh
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/build/event_processor:$(pwd)/build/leaderboard"
python3 verify_installation.py


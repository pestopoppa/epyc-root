#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
./build.sh
./fixture_qkv "$PWD/fixture"
for nth in 1 16 32 64 96; do
 ./replay_qkv "$PWD/fixture" "$nth"
done
python3 ./check_negative.py

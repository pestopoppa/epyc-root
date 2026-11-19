#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=/mnt/raid0/llm/tmp/df2/cafe3-adaptive
mkdir -p "$ROOT"
TEST_BIN=$(mktemp "$ROOT/controller-test.XXXXXX")
trap 'rm -f -- "$TEST_BIN"' EXIT
for TEST_SOURCE in test_controller.cpp test_round_lifecycle.cpp; do
    "${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror -pedantic \
        -fsanitize=address,undefined -g "$HERE/$TEST_SOURCE" -o "$TEST_BIN"
    "$TEST_BIN"
done
python3 "$HERE/test_native_port.py"
python3 "$HERE/test_server_port.py"

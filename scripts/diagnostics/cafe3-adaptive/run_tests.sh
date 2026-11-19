#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=/mnt/raid0/llm/tmp/df2/cafe3-adaptive
mkdir -p "$ROOT"
TEST_BIN=$(mktemp "$ROOT/controller-test.XXXXXX")
trap 'rm -f -- "$TEST_BIN"' EXIT
"${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -g "$HERE/test_controller.cpp" -o "$TEST_BIN"
"$TEST_BIN"

#!/bin/sh
# Isolated synthetic canary. STAGE and ORIGIN optionally select a staged install and reference.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec nice -n 19 taskset -c 84-87 python3 -I -B "$HERE/../tests/fixtures/ak_canary/canary.py"

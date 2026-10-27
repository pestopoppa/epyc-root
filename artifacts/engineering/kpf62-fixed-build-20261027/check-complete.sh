#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build
[[ -f $B/BUILD-ATTEMPT && ! -L $B/BUILD-ATTEMPT && -f $B/BUILD-COMPLETE && ! -L $B/BUILD-COMPLETE && -s $B/build-receipt.json && ! -L $B/build-receipt.json ]]
attempt=$(cat "$B/BUILD-ATTEMPT")
sha=$(sha256sum "$B/build-receipt.json"); sha=${sha%% *}
cmp -s "$B/BUILD-COMPLETE" <(printf 'attempt=%s\nreceipt_sha256=%s\nrc=0\ndrain=verified\n' "$attempt" "$sha")

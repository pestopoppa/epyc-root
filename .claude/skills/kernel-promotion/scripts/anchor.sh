#!/bin/bash
# STEP 0: archive the OUTGOING kernel and PROVE the rewind. Run BEFORE anything moves.
#
# kernels/archive/ was empty 2026-07-31 -> 2026-09-21 because the runbook said to archive "the old
# build dir" while production/<B> pointed INSIDE a source tree at an accretive artifact directory.
# There was no old build dir, so the step was unexecutable and no freeze was ever recorded through
# the store. The anchor was materialised on 09-21 and NEEDED within hours, when a promoted kernel
# proved to be incomplete. An anchor is not paperwork; it is the only thing that makes a bad
# promotion survivable.
#
# usage: anchor.sh <backend>
set -euo pipefail
B="${1:?usage: anchor.sh <backend>}"
K=/mnt/raid0/llm/kernels
LINK="$K/production/$B"
[ -L "$LINK" ] || { echo "FAIL: $LINK is not a symlink"; exit 1; }
OLD=$(readlink -f "$LINK") || { echo "FAIL: $LINK does not resolve"; exit 1; }
[ -d "$OLD" ] || { echo "FAIL: resolves to a non-directory: $OLD"; exit 1; }

case "$OLD" in
  "$K"/builds/*) : ;;
  *) echo "WARN: the outgoing kernel is NOT in kernels/builds/ -- it is at:"
     echo "        $OLD"
     echo "      That is the pre-store state. Copy it into a versioned dir FIRST; an anchor that"
     echo "      points into a live source tree is not a rollback target, because a rebuild or"
     echo "      checkout there mutates production in place."
     exit 2 ;;
esac

BIN=$(ls "$OLD" | grep -E '^(llama|whisper|tts)-server$' | head -1)
[ -n "$BIN" ] || { echo "FAIL: no server binary in $OLD"; exit 1; }
VER=$(env -u LD_LIBRARY_PATH "$OLD/$BIN" --version 2>&1 | head -1)
SHA=$(echo "$VER" | grep -oE '\(([0-9a-f]{7,})\)' | tr -d '()' || true)
echo "outgoing: $OLD"
echo "          $VER"

echo "-- proving the rewind is USABLE, not merely that the path exists --"
env -u LD_LIBRARY_PATH bash \
  /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh \
  "$OLD/$BIN" "$OLD" >/dev/null 2>&1 \
  || { echo "FAIL: the outgoing kernel is not self-contained; rewinding to it would load ggml from"
       echo "      somewhere else. An unusable anchor is worse than none -- it reads as a safety net."
       exit 1; }
echo "   linkage OK with LD_LIBRARY_PATH unset"

A="$K/archive/$B-$(date -u +%Y%m%d)-${SHA:-unknown}"
if [ -L "$A" ]; then echo "   anchor already exists: $A"; else ln -sfn "${OLD%/bin}" "$A"; echo "   anchor created: $A"; fi
echo "REWIND COMMAND (record this in the ratification package):"
echo "   ln -sfn $OLD $LINK"

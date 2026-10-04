#!/bin/bash
# FOLD-CANDIDATE.md §5 steps 0-3 (guarded champion fast-forward), run by workspace-ec after gpu_slot_fold.sh PASS
# (slot-20261004T073429Z). Step 4 (standing receipt) is run separately.
set -euo pipefail
L=/mnt/raid0/llm/llama.cpp
OLD=90c12df4247e417053ffc59e2188294826d04ca2
NEW=1bceceb0514d423ad220888313eafcddc30e485e
REF=refs/heads/ak/champion/llama-cpp-ffc1bac82eec
T=/mnt/raid0/llm/tmp/ak-loop-tree
test "$(git -C $L rev-parse $REF)" = $OLD
test "$(git -C $L ls-remote fork $REF | cut -f1)" = $OLD
test "$(git -C $L ls-remote fork refs/heads/fold/champion-kvu19-20261004 | cut -f1)" = $NEW
git -C $L merge-base --is-ancestor $OLD $NEW
test "$(git -C $T rev-parse HEAD)" = $OLD
test -z "$(git -C $T status --porcelain --untracked-files=no)"
test "$(git -C $L branch --show-current)" = production-consolidated-v10
echo "preconditions OK"
git -C $L update-ref -m "fold: KVU-19a (ac97e305a, a0d0ae238) + KVU-19b commit 1 (1bceceb05) [champion-fold-kvu19-20261004]" $REF $NEW $OLD
git -C $T read-tree -m -u $OLD $NEW
test -z "$(git -C $T status --porcelain --untracked-files=no)"
git -C $L push fork $NEW:$REF
test "$(git -C $L ls-remote fork $REF | cut -f1)" = $NEW
echo "champion advanced to $NEW (local + fork); ak-loop-tree clean"

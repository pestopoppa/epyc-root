#!/bin/bash
# standing_receipt.sh: the ONE-champion standing receipt for the KVU-19 fold. Run by the session that moved the
# champion ref, AFTER the update-ref + push in FOLD-CANDIDATE.md, in an MI210 window (:8083 and all GPU users down).
#
# SINGLE ARM (operator ruling 2026-10-04: "We have the production numbers already. You just need to measure the
# champion."). Measures ONLY the champion GPU build gpu-20261004-1bceceb05: 1 warm-up + 20 launches of
#   taskset -c 184-191 numactl --interleave=all llama-bench -m Qwen3.8-27B-Q8_0 -p 0 -n 128 -r 9 -ngl 99 -fa 1 -o json
# (the exact argv/env/parse of bench.run_once at research 4ede0e03, i.e. NO --autokernel-harden), ~14.4 min device time.
# Baseline = the CITED RECORD /mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json g5_full.candidate_samples
# (ef81196d5, 20 launches, 2026-09-08, median 31.301 tok/s; sha256 pinned in standing_receipt.py), never re-measured.
# Writes ONLY via production.refresh -> /mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json
# (+ .<sha12>.json evidence). Never touches the set-aside .pre-v10-20260922 / .pre-reconcile files.
#
# usage: standing_receipt.sh [--dry-run]
set -euo pipefail
EXPECT_TIP=1bceceb0514d423ad220888313eafcddc30e485e      # the fold candidate == the new champion tip
EXPECT_FROZEN=ffc1bac82eeca6f9099e1ccd9ba49703c460a115   # production-consolidated-v10
CHAMP_BUILD=/mnt/raid0/llm/kernels/builds/gpu-20261004-1bceceb05
BASE_BUILD=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82   # = kernels/production/gpu; recorded as baseline.build, NOT run
LLAMA=/mnt/raid0/llm/llama.cpp
RESEARCH=/mnt/raid0/llm/epyc-inference-research
F=/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004
NOTE="PROVENANCE (not an instrument excursion). (1) First standing receipt of the v10 lineage: the champion ak/champion/llama-cpp-ffc1bac82eec was advanced by hand ffc1bac82 -> 90c12df42 (5 manual folds, no receipt), then fast-forwarded 90c12df42 -> 1bceceb05 (KVU-19a ac97e305a+a0d0ae238, KVU-19b commit 1) on $(date -u +%F); this receipt measures 1bceceb05. (2) BYPASS + UNPAIRED, per operator ruling 2026-10-04: production was NOT re-measured. anchor_samples are the 20 recorded launches of ef81196d5 (/mnt/raid0/llm/tmp/build-fold-ef81196d5) from /mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json g5_full.candidate_samples (FOLD-2 G5, 2026-09-08 ~11:16Z, sha256 71344d34...). No recorded v10 (ffc1bac82) tg128 measurement under this protocol exists; ef81196d5 differs from v10 only by d0d70c5fe (gemma4-assistant NextN read order) and ffc1bac82 (MoE top-k fusion gated to CPU-only graphs), neither of which touches the dense Qwen3.8-27B GPU graph, with identical build-recipe flags; baseline.commit/build name the v10 freeze as the writer requires, but the samples are that ef81196d5 record. The champion arm reproduces the record's protocol exactly (bench.run_once @ research 4ede0e03: no --autokernel-harden, -r 9, taskset 184-191, numactl interleave, 1 warm-up + 20 launches). (3) CAVEAT: the arms are unpaired and 26 days apart, across the 2026-09-21 BIOS change (memory interleave on, 5600 MT/s). The host drifts ~3% over hours, so the effect carries at least that uncertainty; the 0.638% paired floor does NOT apply (noise_floor_pct null, calibrated false) and the confidence_interval field, computed by pairing ordinals, is not a valid paired interval. Written via standing_receipt.py (production.refresh, injected single-arm compare) by the fold session."
DRY=${1:-}

tip=$(git -C "$LLAMA" rev-parse refs/heads/ak/champion/llama-cpp-ffc1bac82eec)
fork_tip=$(git -C "$LLAMA" ls-remote fork refs/heads/ak/champion/llama-cpp-ffc1bac82eec | cut -f1)
frozen=$(git -C "$LLAMA" rev-parse HEAD); branch=$(git -C "$LLAMA" branch --show-current)
echo "champion local=$tip fork=$fork_tip  frozen=$frozen ($branch)"
if [ "$tip" != "$EXPECT_TIP" ] || [ "$fork_tip" != "$EXPECT_TIP" ]; then
    if [ "$DRY" = --dry-run ]; then echo "NOTE: champion ref not yet advanced (dry run continues)";
    else echo "REFUSED: champion ref is not $EXPECT_TIP locally and on fork; move the ref first"; exit 3; fi
fi
[ "$frozen" = "$EXPECT_FROZEN" ] && [ "$branch" = production-consolidated-v10 ] \
    || { echo "REFUSED: frozen tree is $frozen ($branch), not v10 $EXPECT_FROZEN; re-derive the baseline build"; exit 3; }
[ "$(readlink -f /mnt/raid0/llm/kernels/production/gpu)" = "$BASE_BUILD/bin" ] \
    || { echo "REFUSED: kernels/production/gpu no longer points at $BASE_BUILD/bin"; exit 3; }
[ -z "$(git -C "$LLAMA" status --porcelain --untracked-files=no)" ] || { echo "REFUSED: frozen tree dirty"; exit 3; }
LV=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
"$LV" "$CHAMP_BUILD/bin/llama-bench" "$CHAMP_BUILD/bin" > /dev/null || { echo "REFUSED: champion linkage"; exit 3; }

ARGS=(--champion-build "$CHAMP_BUILD" --champion-commit "$EXPECT_TIP" --baseline-build "$BASE_BUILD" --note "$NOTE")
if [ "$DRY" = --dry-run ]; then
    cd "$RESEARCH" && exec .venv/bin/python "$F/standing_receipt.py" "${ARGS[@]}" --dry-run
fi
kfd=$(ls /sys/class/kfd/kfd/proc 2>/dev/null | grep -c . || true)
[ "$kfd" = 0 ] || { echo "REFUSED: $kfd KFD process(es) on the GPU; free the MI210 first"; exit 3; }
cd "$RESEARCH"
exec /workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list 0-95 --role bench --tag champion-standing -- \
    .venv/bin/python "$F/standing_receipt.py" "${ARGS[@]}"

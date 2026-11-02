# R23-62 replay: estimand, order and contention

These are historical **CANDIDATE observations**, decode tokens/s, higher better, experimental CPU server instrument, uniform IQ4_XS model, 2026-09-07 and 2026-09-08. They are not production rates or new measurements. Extract `raw-evidence.tar.gz` as described in README and verify `SHA256SUMS` before replay.

The old 1.7151 is the **mean of 60 within-round, per-prompt ratios**, after excluding predictions shorter than 16 tokens; prompts from the same process are not independent launches. The newer 2.1857 is the **ratio of mean per-launch token-weighted rates**, six champion and three pristine launches. Replaying the old rows with the newer point-estimator definition gives **1.71275** (three champion and three pristine process launches); the later rows give **2.18567** (six and three). This descriptive harmonization changes the old point by about 0.14%, so this estimator difference cannot by itself account for the observed historical ratio gap. It does not validate either comparison, resolve precision, or isolate source, configuration or host effects.

The old driver rotates launch order: round 1 pristine → champion-1 → champion-3; round 2 champion-3 → champion-1 → pristine; round 3 champion-1 → pristine → champion-3. Within-round per-prompt means replay as 1.6881, 1.7534 and 1.7038 (20 prompt pairs each). The saved co-residency logs show the GPU-lane `llama-bench` in **17/17 samples for pristine round 1**, and in **0/18 and 0/17** for pristine rounds 2 and 3; none of the three champion-3 logs observed it (0/10 each). These samples are not atomic placement or bandwidth measurements; they show unequal observed exposure, not its size or causation. The old report also flags overlapping SMT work and warns the per-prompt interval understates uncertainty. Thus rotation did not ensure equal exposure, and prompt-level pairing does not establish common-mode contention cancellation. No retrospective sample is deleted.

To reproduce the point-estimator comparison from the extracted archive:

```sh
python3 - <<'PY'
import json, statistics
from pathlib import Path

def rate(path):
    rows = [r for line in path.open() if (r := json.loads(line)).get('pred_n', 0) >= 16 and r.get('pred_ms')]
    return 1000 * sum(r['pred_n'] for r in rows) / sum(r['pred_ms'] for r in rows)
old = Path('runs'); new = Path('later-final')
ratio = lambda a, b: statistics.mean(map(rate, b)) / statistics.mean(map(rate, a))
print('old', ratio([old / f'R_P_r{i}.rows.jsonl' for i in range(1,4)], [old / f'R_C3_r{i}.rows.jsonl' for i in range(1,4)]))
print('later', ratio([new / f'fpp{i}.rows.jsonl' for i in range(1,4)], [new / f'fcp{i}.rows.jsonl' for i in range(1,7)]))
PY
```

The earlier proposed shim-OFF repeat cannot identify the old gap: even a perfectly controlled present-day contrast cannot recreate the old contention or retired model, and an off/on test isolates a different factor. A useful **prospective diagnostic**, not a reconstruction of September, is a same-window, same-model comparison of retained build 10241 champion-3 versus the retained 10303 instrument with its four champion-control knobs explicitly set and process THP disabled in neither arm. Run 12 order-balanced pairs, one server process per arm, the same served UD shards, CPU placement and 24-prompt workload; estimate the ratio of mean launch rates with process-level uncertainty, and preserve all arm-level screens and artifacts. This asks only whether the instrument/build difference has a material effect on today's UD workload. It cannot attribute the historical ratio gap or transfer its size to the retired uniform model. Pre-register a materiality boundary and failure/stopping rule before collection; an inconclusive interval remains inconclusive.

Before any run, prove executable and every DSO against the historical manifests and linkage, check model-shard digests, flag support, knob-page mapping and readback, THP enabled in both arms, identical non-treatment semantics and output equivalence. The existing `scripts/benchmark/serve_qwen38_flash_next.sh` and recipe default to process-THP ON and assert a particular champion identity; do not assume they can express this diagnostic. First construct and dry-run a suitable codified experiment recipe, validate that it changes exactly the declared binary/control state, and establish a legal preflight and held region claim. At audit time the host exceeded the Annex B one-week uptime threshold; no applicable serving-contrast exception was verified. No launcher was executed or claimed ready here.

Read-only launcher check, 2026-11-02: `serve_qwen38_flash_next.sh --bindir <each retained bin> --plain --skip-digests --dry-run` returned 0 for both and emitted the UD recipe with `GGML_NOHUGEPAGE_PROCESS=1`. This demonstrates flag/plan emission only: digests were deliberately skipped, neither server was launched, the desired OFF state and instrument knob-page controls were not emitted, and no experimental runner was validated. It is not a suitable command for the proposed contrast.

Further preflight, 2026-11-02 13:29Z: all three retained UD shard paths exist and their byte sizes match the recipe manifest; this is an availability check, not a digest check. `sha256sum -c` passed both retained binary manifests, but these manifests do not necessarily bind every loaded dependency, so complete DSO closure and runtime maps remain required. Uptime was 1,748,653 seconds (about 20.2 days). Annex B `P-BENCH-1` requires reboot at at least one week; the general host-health rule in `agents/shared/OPERATING_CONSTRAINTS.md` likewise applies before trusting a measurement. No applicable exception for this diagnostic was located. No benchmark launched.

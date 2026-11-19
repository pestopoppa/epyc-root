# HS-TD-2 worker self-check authored screen — 2026-11-19

Row `hs-td2-worker-selfcheck-cpu-v1-20261119` ended rc=0 at 2026-11-19T07:11:42Z. Verdict: **pass for completion of the prospective descriptive screen**, with two incorrect judgments. HS-TD-2 remains open for actual per-turn shadow integration through HS-TD-4's envelope. This is no promotion gate, live-session acceptance or production-overhead claim.

Sixteen frozen authored turns were evaluated twice (seeds 42/43, temperature 0), using registered worker Qwen3.6-35B-A3B-MTP-Q8_0 on the frozen v10 CPU server without MTP. The planned denominator is 32; smoke is excluded. Observed/planned = 32/32, valid/planned = 32/32, unknown/planned = 0/32. Reference agreement = 30/32 (93.75%). Higher validity/agreement is better; lower extra-call wall cost is better. Mean valid call cost = 5.193499 s; nearest-rank p95 = 8.514656 s; all-attempt call wall time = 166.191977 s. These describe the calls in this allocation, not an isolated baseline comparison. Confidence mean = 0.9875, range 0.9–1.0; self-reported confidence is uncalibrated. Seed repeats are not independent population samples; no population uncertainty claim is made.

## Disagreement review

Both disagreements (the entire sample, below the prospective limit of five) concern `arithmetic-incomplete`: task asks for 17 plus 26, number only; candidate is `42`. The reference is false because the sum is 43. In both repeats the model returned satisfied=true, confidence=1.0, and explicitly claimed 42 was the correct sum. The reference rationale is correct; these are confidently wrong semantic judgments, not schema failures. Formatting compliance alone does not satisfy the task. All other 30 judgments agreed with their references. Keep this signal logging-only as specified; the screen does not establish calibrated confidence or safe gating.

## Evidence identities

Native files are cited by path and SHA-256, not copied. Source corpus and producer are `scripts/harness/hs_td2_cases.json` and `scripts/harness/hs_td2_probe.py` at ROOT commit `b6101dfc813facb05f58a495d5f6ed33bc5ed563`.

- `/mnt/raid0/llm/tmp/repl-turn-efficiency/hs-td2-worker-v1/RESULT.json`: `986781191c734f8a152630d2e0ebeb222fb427807d4f436181dc96f0db53d794`.
- Same job's `results.jsonl` (contains smoke and full records; only full records summarized): `1bc1837d4cc0d45d2a341bb066d11f226920029a2ccfa77ec243a269767a57c2`.
- Same job's full-phase seed-42 `arithmetic-incomplete` native record (exact `record_path` in `results.jsonl`): `96130e40192e74604d46760ed1d298bf3c3ace895b1ad475e00378a1b0006b4b`.
- Same job's full-phase seed-43 `arithmetic-incomplete` native record (exact `record_path` in `results.jsonl`): `d9417879156ea626d75c681b33174cd6166cb4e05b3d7eb515eca936e046ea57`.

The prospective HS-TD-2 source row in `scripts/vidya/adapters/README.md` and existing `VB-PARK-HARNESS-EVAL` source-extension task in `handoffs/active/vidya-belief-substrate-program.md` already cover this producer. This filing is a committed conclusion, not a reconstructed measurement warrant or a claim that projection/planning-context wiring is complete. [belief: cc]

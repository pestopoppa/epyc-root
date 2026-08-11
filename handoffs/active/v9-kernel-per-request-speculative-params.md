# v9 kernel candidate — expose per-request speculative parameters

**Filed** 2026-07-31 · **Owner** operator (kernel promotion) · **Status** PROMOTED AND FROZEN as production v9 on 2026-08-11; resident fast-path follow-up remains open
**Production** `production-consolidated-v9` @ `0db32c06e3e550065b78311a6031ef3dd2c4f27c` (binary 10125), exact v8 base/rollback `67a433bf45a8a091d83b4ea0b32ff0735fd51800`

---

## 0. What this is, in one paragraph

Frozen v8 accepts no per-request speculative parameters. Experimental v9 now exposes exactly one:
`speculative.n_max`. It is a request-local cap bounded by the launch-time maximum; `0` disables
speculation for that request, the effective value is returned in `generation_settings`, and slot
reuse does not leak a prior request's cap. The other speculative fields remain unavailable because
their request-local behavior is not wired or proven. This corrects the original proposal, which
treated deleting the whole `#if 0` block as sufficient.

## 1. The finding, verified in source

`/mnt/raid0/llm/llama.cpp/tools/server/server-schema.cpp`, lines 204-233:

```cpp
    // TODO: to keep things simple, we disable speculative parameter adjustments for now
#if 0
    // TODO: for now, be able to adjust only the draft-model based speculative parameters
    add((new field_num("speculative.n_max", params.speculative.draft.n_max)) ...
    add((new field_num("speculative.n_min", params.speculative.draft.n_min)) ...
    add((new field_num("speculative.p_min", params.speculative.draft.p_min)) ...
    add((new field_str("speculative.type")) ...
    add((new field_num("speculative.ngram_size_n", ...)) ...
    add((new field_num("speculative.ngram_size_m", ...)) ...
    add((new field_num("speculative.ngram_min_hits", ...)) ...
#endif
```

**Everything speculative is inside the `#if 0`.** Including `speculative.type`,
which would have allowed per-request selection between `ngram-mod` and
`draft-mtp` — exactly the selective control we wanted.

### The trap that produced a confident wrong answer

This was first reported (by me) as "these ARE per-request fields", because:
1. `grep` finds the `add((new field_num("speculative.n_max" ...` registrations and
   they look live; the `#if 0` is 4 lines above and does not appear in the match.
2. `tools/server/README.md` shows `speculative.n_max` in its JSON examples — but
   those are **`generation_settings` echoes of launch defaults**, not accepted
   request fields.

Source registration plus a README example reads as corroboration from two
independent places, when neither is evidence. **Lesson: when a grep hit decides a
capability question, read the enclosing preprocessor context before answering.**

## 2. Why it matters now

Production launches `--spec-type ngram-mod,draft-mtp` (composed). That recipe
costs a measured **−1.6 % mean** on ordinary prose/code and is carried
deliberately for the repetitive-context upside. With no runtime control:

- That ~1.6 % is paid on **every drafted request**, forever, with no way to skip it
  on traffic known to be non-repetitive.
- Autopilot cannot raise the draft budget on repetitive workloads where the
  composed drafter would actually pay off.
- `n_max: 0` — the natural "just turn speculation off for this call" escape hatch —
  does not exist either.

## 3. Tasks

- [x] **V9-1. Expose only functional `speculative.n_max`** on an experimental branch; preserve the
  frozen production tree ✅ 2026-08-10
- [x] **V9-2. Prove request-local plumbing:** `0` disables, positive values cap the launch maximum,
  over-large values clamp, omission restores the launch default, and reused slots remain isolated
  ✅ 2026-08-10
- [x] **V9-3. Report the effective value** in every completion's `generation_settings`, so a harness
  can attribute results to the actual draft cap ✅ 2026-08-10
- [x] **V9-4. Keep unwired controls unavailable.** `n_min`, `p_min`, type selection, and ngram fields
  were deliberately not exposed; source presence is not runtime wiring ✅ 2026-08-10
- [x] **V9-5. Regression-check ordinary speculative requests.** Focused server tests pass on the
  final candidate (`2 passed in 56.14s`), and the real DSpark smoke reports effective caps 0 and 3
  independently on one reused slot ✅ 2026-08-10
- [x] **V9-6. Complete the kernel-promotion qualification procedure** against frozen v8: rebuild CPU
  and HIP from the repaired final tip, validate linkage/functionality, and run every incumbent-role,
  correctness, quality, topology, rollback, and measurement gate ✅ 2026-08-11
- [x] **V9-7. Execute the authorized `production-consolidated-v9` cutover** and production-named
  GPU/DFlash/DSpark certification ✅ 2026-08-11. GPU roles and `-np 1` Q8 DSpark exact parity pass.
  Qwen3.6-27B Q8 DFlash is capability-certified but lineup-ineligible under P-DFLASH-LINEUP-1:
  acceptance 35.954% < 60%, despite a 2.458× aggregate decode gain; the lane remains disabled.
- [ ] **V9-8. Implement and prospectively ratify the resident promotion fast path** described in
  [`kernel-promotion-resident-fast-path.md`](https://github.com/pestopoppa/epyc-inference-research/blob/main/docs/design/kernel-promotion-resident-fast-path.md): sealed candidate hot stack, exact-parity pack, resident per-request speculation schedule, and automatic fallback to the existing fresh-server instrument.

## 3.1 Evidence

- Candidate commit: `84c84fafe36c7e5deab7ff5301b1a7a1cde9b920` (feature), included in final
  candidate `2ac4b32a01a6d97af1c85889443472fbd4a1e12e`.
- Final bounded Q8 smoke: vanilla and DSpark produced identical 16-token arrays; DSpark drafted 18
  and accepted 7 tokens at effective `n_max=3`.
- Durable receipt: [`artifacts/audit/v9-dspark-autokernel-base-20260810.json`](../../artifacts/audit/v9-dspark-autokernel-base-20260810.json).
- Qualified final candidate and production tip: `0db32c06e3e550065b78311a6031ef3dd2c4f27c`
  (version 10125; CPU SHA-256 `8ebb1355…`, HIP `21cfb750…`).
- Final freeze: [`ratify_v9_final_freeze_20260811.json`](../../artifacts/operator/ratify_v9_final_freeze_20260811.json).
- Production certification evidence is pinned in
  [`v9-kernel-promotion-attestation.json`](v9-kernel-promotion-attestation.json), including the
  region-locked GPU role pass, region-locked DSpark parity pass, and DFlash lane-specific no-go.

## 3.2 Promotion boundary (completed)

The complete qualification repaired the starting candidate to `0db32c06e…`, rebuilt and re-ran the
full gate set, cut over the versioned production tree, certified the production-named GPU and
speculation paths, and froze v9. v8 remains the tested rollback anchor. AutoKernel initialization and
its hypothesis queue were explicitly outside this promotion goal.

## 4. NOT in scope here — draft-max tuning is a TODAY task

`--spec-draft-n-max` is a **launch flag on the current kernel**. It needs no kernel
change and must not wait for v9. It is being swept now; see
`handoffs/active/draft-max-sweep-20260731.md`. Recorded here only so nobody files
it against this handoff by association.

## 5. Do not do this

- **Do not patch the frozen production tree** (`/mnt/raid0/llm/llama.cpp`,
  `production-consolidated-v8` @ `67a433bf4`). All kernel work happens on
  `llama.cpp-experimental`, per the four-step workflow in `CLAUDE.md`.
- **Do not treat this as a prerequisite for the speech or vision work.** Qwen3-ASR
  and qwentts.cpp need no kernel change at all; this is orthogonal.

## 6. Cross-references

- Master index row **N28**; tasks SW-1..SW-4.
- `speculative-decoding-mtp-refresh.md` — carries the ngram retraction banner and
  the T1 draft_max evidence.
- Design decision to carry composed ngram, with its measured −1.6 % cost:
  artifact §01 "Design decision — the recipe carries `ngram-mod`".

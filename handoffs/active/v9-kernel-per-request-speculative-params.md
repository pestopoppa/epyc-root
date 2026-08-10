# v9 kernel candidate — expose per-request speculative parameters

**Filed** 2026-07-31 · **Owner** operator (kernel promotion) · **Status** IMPLEMENTED on experimental v9; full promotion qualification authorized and started 2026-08-10
**Candidate** `experimental-v9-dspark-autokernel-base` @ `2ac4b32a01a6d97af1c85889443472fbd4a1e12e` (binary 10123), exact v8 base `67a433bf45a8a091d83b4ea0b32ff0735fd51800`

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
- [ ] **V9-6. Complete the kernel-promotion qualification procedure** against frozen v8: rebuild CPU
  and HIP from this exact tip, validate linkage/functionality, reboot before measurement, then run
  every incumbent-role, correctness, quality, topology, rollback, and measurement gate.
- [ ] **V9-7. Execute the authorized `production-consolidated-v9` cutover only if V9-6 passes**;
  then perform production-named P-GPU-1 and DFlash certification. DSpark remains limited to its
  validated `-np 1` path; failure retains v8 and requires repair plus a full candidate re-run.
- [ ] **V9-8. Follow-up after the current qualification:** implement and prospectively ratify the
  paired-resident promotion fast path in the
  [research design](https://github.com/pestopoppa/epyc-inference-research/blob/v9-promotion-instrument-20260810/docs/design/kernel-promotion-resident-fast-path.md),
  including the sealed candidate hot stack, broad exact-parity pack, per-request DSpark/DFlash
  schedule, acceptance tests, and automatic fallback to the existing fresh-server instrument. This
  task does not alter or regrade the in-flight v9 evidence.

## 3.1 Evidence

- Candidate commit: `84c84fafe36c7e5deab7ff5301b1a7a1cde9b920` (feature), included in final
  candidate `2ac4b32a01a6d97af1c85889443472fbd4a1e12e`.
- Final bounded Q8 smoke: vanilla and DSpark produced identical 16-token arrays; DSpark drafted 18
  and accepted 7 tokens at effective `n_max=3`.
- Durable receipt: [`artifacts/audit/v9-dspark-autokernel-base-20260810.json`](../../artifacts/audit/v9-dspark-autokernel-base-20260810.json).

## 3.2 Promotion boundary (authorized, no new gate passed)

The operator authorized the complete v9 promotion procedure on 2026-08-10. It begins from this exact
candidate and treats v8 as immutable. The bounded smoke and build checks above are candidate evidence,
not completion of any promotion gate. AutoKernel initialization and its hypothesis queue are explicitly
outside this promotion goal; they require a separately authorized follow-on after a successful v9
release boundary.

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

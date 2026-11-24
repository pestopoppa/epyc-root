# Speculative-decoding identity and distribution gates (SPEC-ID-GATE-1 / SPEC-PIT.1)

Status: agent-workflow guide (2026-11-23, autokernel). It does not amend `MEASUREMENT.md` or
`measurement/protocols/`. If the operator wants it to be normative, it would go in as an amendment to
`measurement/protocols/divergence.md`; that is a human-only edit.
Code: research `scripts/kernel_rnd/dist_gate/spec_dist_gate.py` (`gate`, `margin_class`,
`classify_divergence`, `paired_count_test`), tested by `test_spec_dist_gate.py`.
Handoff: `handoffs/active/speculative-decoding.md` → SPEC-ID-GATE-1, SPEC-PIT.1.

## 1. What question does the gate answer?

A speculative-decoding change (a new draft width, `--spec-draft-p-min`, an adaptive controller, a
verify kernel, a fold) must not change **the output law**. Throughput is judged separately (A/A floor).
The gate you use depends on the regime:

| Regime | Gate |
|---|---|
| T = 0, and the exact-identity regime holds (§2) | exact token identity; floor 0 |
| T = 0, outside that regime | margin-class divergence gate (§3) plus a paired count test (§4) |
| T > 0 (served sampler) | SPEC-PIT.1 distribution gate (§5); identity is meaningless |

## 2. When exact identity applies

Exact token identity is a valid check only when **all** of these hold:

- same server build and the same launch config (a cross-server comparison needs its own same-server A/A arm);
- one request at a time (concurrency 1; no np4, no batched slots);
- the same verify-width class on both arms, or `LLAMA_SPEC_EXACT=serial` / `GGML_ROWEXACT_N` on both
  (pinning one kernel backend does not remove verify-path divergence, intake-2842#04);
- a configuration measured as deterministic across launches;
- the same cache state and KV provenance on both arms (preconditions checklist below).

### Preconditions checklist (SPEC-ID-GATE-2 (b), (c))

Tick every line for both arms before comparing tokens. A line that cannot be ticked puts the comparison
outside the exact-identity regime (use §3/§4), or makes it INCONCLUSIVE.

| # | Precondition | Both arms |
|---|---|---|
| P1 | `cache_prompt: false` on every request | same value |
| P2 | `--cache-ram 0` (or a verified identical prefix-cache state, logged as `cache_n` per request) | same value |
| P3 | prefill ubatch `-ub` (and `-b`) | identical |
| P4 | KV dtype `-ctk` / `-ctv` | identical |
| P5 | spec width / verify-width class (`--spec-draft-n-max`, p-min, or `LLAMA_SPEC_EXACT=serial` on both) | identical |
| P6 | fresh decode, not redecode or resume (redecode and resume reuse verify-written KV/GDN state) | fresh |
| P7 | np, concurrency, sampler chain, BOS/EOS, penalties (config dump equal across builds) | identical |

Floors measured with P1+P2 hold are labelled **cache-off**; the SPEC-ID-NOISE-1 floors below are
cache-off. A cache-hit path needs its own floor (PFXC-ID-REPLICA-1).

### Cache-hit path template (PFXC-ID-REPLICA-1)

A cached request breaks P1/P2 by design, so it is judged against the cold path, never against a
cache-off floor alone:

1. Per launch L (>= 3 launches, served flags, `cache_prompt: true`, `--cache-ram` as served), per prompt:
   COLD_L = the target request with `cache_prompt: false`; then a priming request (same prompt, 1 token,
   `cache_prompt: true`); then HIT_L = the target request with `cache_prompt: true`. Log `timings.cache_n`
   on every request; a HIT with `cache_n` = 0 is a cache miss and is reported, not judged.
2. Per-path floors: `replica_floor([COLD_1..n])` and `replica_floor([HIT_1..n])` (largest pair).
3. Gate: `identity_replica_gate(HIT_k, [COLD_1..n], margins=...)` for every k. Any FAIL, or any HIT-vs-COLD
   count above the larger per-path floor, marks cached requests **outside the exact regime** for that
   device and recipe; record it here. All PASS: the cache-hit path is within the cold-path floor.

Measured (SPEC-ID-NOISE-1, 2026-11-23, CPU `cbccfef9c`, GPU `a260774b3`; all floors **cache-off**):

- CPU (Q38FN + MTP, C19): spec-off and MTP at concurrency 1 are bit-deterministic across launches
  (0/64 divergences, w1 delta-logit exactly 0). **Floor 0.**
- GPU (27B Q8_0 + DFlash2, MI210): spec-off at concurrency 1 is deterministic across launches (0/64).
  **The DFlash2 path is not**: M1 vs M2 diverge on 20/64 one-at-a-time, across launches.
  `serial` does not restore width-1 identity on GPU. An exact-identity gate on the GPU spec path is
  unsatisfiable even A/A.
- Every batched or cross-width comparison (np1 vs np4, spec-off np4, MTP np1 vs width 1, serial vs
  redecode) sits at about 1-2.5 near-tie divergences per 4 prompts per 128 tokens, on both devices.

A change in draft width (p-min, adaptive width) changes the verify batch shape, so its arms are in
**different width classes**. They are outside §2 by construction, even on CPU at concurrency 1.

Never import a literature exact-match rate as a threshold (intake-2844#record). The floor is what our
same-run A/A arm measures.

### Replica table (SPEC-ID-GATE-2 (a))

A floor is the **largest pair** over all pairs of reference launches of the unchanged config, never a
single A/A pair. At least one launch is reordered (prompt order permuted) or np-shuffled.

| Use | Reference launches | Pairs | Floor |
|---|---|---|---|
| ordinary gate | >= 3 | all C(n,2) (3 for n=3) | largest pair divergence count |
| promotion gate | >= 5 | all C(n,2) (10 for n=5) | largest pair divergence count |
| fewer launches | < 3 (< 5 for promotion) | - | none: **INCONCLUSIVE** |

Code: `replica_floor` and `identity_replica_gate` in `spec_dist_gate.py`. The candidate's count is its
largest count against any reference launch; it fails above the floor or on any non-NOISE first divergence
(§3), and with no retained margins it is INCONCLUSIVE.

## 3. Margin classes: classify every first divergence

For each prompt where two arms diverge, take the **top-2 margin** (nats, log-prob of top-1 minus top-2
of the reference arm) at the first divergent position. `margin_class`:

| class | margin | Reading |
|---|---|---|
| `exact0` | = 0 | exact tie. Measured share among A/A divergences: 0 |
| `le0.1` | (0, 0.1] | near-tie flip; 94% of all 235 measured GPU first divergences |
| `le0.5` | (0.1, 0.5] | near-tie flip if within the class tau |
| `gt0.5` | > 0.5 | never observed in any A/A or cross-width pair; **defect candidate** |

Class tau (the noise tolerance for a width class) comes from the SPEC-ID-NOISE-1 RESULT.json files
(CPU `/mnt/raid0/llm/tmp/ak-spec-id-noise-q38fn-cpu-20261123-r2/out/RESULT.json`, GPU
`/mnt/raid0/llm/tmp/ak-spec-id-noise-27b-dflash2-gpu-20261123/out/RESULT.json`). GPU near-top tau is
0.22-0.60 nats in every DFlash2, serial, redecode and np4 class, and 0 for w1. Both verdicts were
TAU_UNSTABLE, so **use 0.5 nats as the default class tau** (the observed upper bound) unless a stable
per-class value is measured. `classify_divergence` verdicts:

- `NOISE`: margin <= tau, outside the exact-identity regime.
- `DEGEN_AFTER_TIE`: the arm falls into a repeat loop after the divergence and the speculation-off np4
  control shows none (intake-2844#02). This is a defect.
- `DEFECT_CANDIDATE`: margin > tau; or **any** divergence inside the exact-identity regime (floor 0).
- `UNCLASSIFIABLE`: no logprobs retained. Re-run with top-k logprobs; do not judge by count.

Margin classes are only comparable between arms that pass the §2 preconditions P1-P6; a class tau measured
cache-off does not transfer to a cache-hit or resumed path.

A gate run must therefore retain top-2 logprobs at every emitted position (or at least at first
divergences). A run that kept only tokens can say "identical" or "not identical", and nothing more.

## 4. Counts: same-run A/A and the paired d test

Outside the exact-identity regime, a divergence **count** is never judged on its own. Every run carries
a same-run A/A arm (same config twice, interleaved with the arms under test). Per block,
d = divergences(arm vs ref) − divergences(A/A). `paired_count_test` gives a one-sided sign-flip p and a
95% t interval for mean d. A count is excess only if p < 0.05 and the CI excludes 0. Even then, the
margin classes of §3 decide whether the excess is a defect (`gt0.5` / DEGEN) or a larger number of
near-tie flips. Single triples or one-off counts (for example ON 7 vs OFF 0) decide nothing.

The A/A side of the count uses the replica floor (§2 replica table), not one pair. Where a scored corpus
exists, report graded flips beside the count (SPEC-ID-GATE-2 (e)): worse, better, wrong-to-wrong, and net.

### RESULT.json fields (SPEC-ID-GATE-2 (d))

Every identity or margin-class gate RESULT.json carries:

| Field | Content |
|---|---|
| `env_knobs` | every kernel-selection env var set for each arm (`GGML_HIP_*`, `GGML_ROWEXACT_N`, `LLAMA_SPEC_EXACT`, `GGML_IQK*`, ...), unset ones listed as null |
| `route_histogram` | per verify width: count of calls per kernel route |
| `binary_sha256` | SHA-256 of `llama-server` and each loaded `libggml*.so`, per arm |
| `config_dump` | sampler chain, BOS/EOS, penalties, prefix-cache state (`cache_prompt`, `--cache-ram`), np, `-ub`, `-ctk`/`-ctv`, spec width |
| `config_dump_equal` | true/false; a cross-build row with false is not judged |
| `replica_floor` | `replica_floor()` output: launches, pair list, largest pair |
| `cache_label` | `cache-off` or `cache-hit` |
| `graded_flips` | worse / better / wrong-to-wrong / net, when a scored corpus exists |

## 5. T > 0: the SPEC-PIT.1 distribution gate

At T > 0 the speculative path must leave the law of the sampled token unchanged. Record, per emitted
token, the post-sampler target distribution (top-k probs after top_k → top_p → min_p → temperature,
`post_sampler_probs`) and the token. `gate(arm, ref, select=... | match_keys=True)`:

1. **Randomized PIT KS (primary, needs no reference).** u = F(x−) + U·m(x) is Uniform(0,1) iff the
   sampler is exact. FAIL if KS p <= 1e-5, or if any token is outside the target support.
2. **Rank chi-square vs the reference (secondary).** Top-20 + other rank histogram against the
   speculation-off (or p-min 0) arm. It is valid only if **both** of these hold:
   - *selection-matched*: compare only co-captured positions (`match_keys`), or apply the arm's own
     draft-selection rule to the reference (`select`). An arm that drafts only at confident positions
     over-represents rank 0, and an unmatched test fails it with the law unchanged (CAFE-1 r2 P075 T1.0:
     naive p 1.6e-16 → matched + request-permutation p 0.63/0.79);
   - *request-level*: the p-value comes from permuting whole requests between arms (2000 permutations),
     never from pooled token counts.

   FAIL if the permutation p < 1e-3.
3. **INCONCLUSIVE** if there are < 2000 PIT values, < 8 requests per arm after matching, or the reference
   arm fails its own KS (the instrument is not calibrated).

The box's full run (≥128 trajectories × 1024 tokens at (T, top_p) ∈ {(1,1), (1,0.95), (4,0.95)}, plain vs
MTP/DFlash2/DSpark) uses this function unchanged.

## 6. How C-build fold gates must apply this

For any champion fold (C-build) touching the spec or verify path:

1. **CPU, concurrency 1, same width class:** exact identity against the previous champion is required;
   the floor is 0. Any divergence → `classify_divergence(identity_floor_zero=True)` → DEFECT_CANDIDATE.
   Investigate before folding. A real, intended numerics change must be named in the fold notes.
2. **GPU spec path (DFlash2) or any batched/np>1 path:** do not require identity. Run a same-run A/A
   arm (old champion twice) beside old vs new. PASS if every first divergence is `NOISE` (margin <= class
   tau, default 0.5), there is no `DEGEN_AFTER_TIE`, and `paired_count_test` shows no excess. A `gt0.5`
   divergence or a DEGEN is a fold blocker until explained.
3. **Width-changing features** (p-min, adaptive width, CAFE-3): the T=0 identity across arms is not a
   gate, per §2. Use the §3 margin classes for T=0 and §5 for the served T.
4. **Cross-server comparisons** (replay vs snapshot, r9 style): include a same-server A/A arm and judge by
   margin class. A cross-server count without A/A is not evidence.
5. Every fold-gate run retains top-2 logprobs. Without them the result is UNCLASSIFIABLE, and the gate
   is INCONCLUSIVE rather than PASS.
6. **Replicas and preconditions (SPEC-ID-GATE-2):** the A/A floor in steps 2 and 4 is the largest pair
   over >= 3 reference launches (>= 5 for a promotion gate); with fewer, `identity_replica_gate` returns
   INCONCLUSIVE. Tick the §2 preconditions checklist for both arms, write the §4 RESULT.json fields, and
   prove `config_dump_equal` before judging a cross-build row.

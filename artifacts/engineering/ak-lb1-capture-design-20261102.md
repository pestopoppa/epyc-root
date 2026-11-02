# AK-PORT-LB1.1 capture design

Status: design only. No candidate, capture harness, or correctness run is currently available.

## Required carrier

Capture one immutable case set as three arms, with one row per identical target-token position:

| Arm | Build | Forward width | Purpose |
|---|---|---:|---|
| `incumbent_n1` | pinned incumbent | 1 | Reference logits and incumbent greedy token |
| `incumbent_nm` | same pinned incumbent | N, N > 1 | Measure incumbent batching noise |
| `candidate_nm` | candidate build | same N | Measure candidate divergence |

The carrier is a versioned JSON (or JSONL plus manifest) record containing `schema`, case-set ID,
prompt/token sequence, N, model and tokenizer identities, and all three arm records. Each arm must
record source commit, build-manifest or binary digest, executable/backend identity, runtime settings,
and the actual forward width observed by the capture path. Store full-vocabulary finite logits for
every scored position, with explicit vocabulary/token-index mapping; do not store only top-k or
sampled probabilities. Preserve raw outputs and a content digest. `incumbent_n1` and `incumbent_nm`
must use the same model/build; only the candidate source/build may differ.

## Identity and position binding

Bind every row to `(case_set_id, prompt_sha256, position, target_token_id, context_prefix_sha256)`.
The same ordered tuple set must occur exactly once in each arm. Also bind all arms to identical
model weights, tokenizer/vocabulary, prompt bytes, template, context, and scoring convention; record
the intentional build difference explicitly. Position means the target prediction position after
the same context prefix, not an output-array offset inferred from a truncated response. Verify the
captured width is truly a multi-row target forward (N > 1); prompt prefill batching or sequential
one-token decode does not qualify. A `/completion n_probs` endpoint is only a possible transport:
accept it only after proving it returns complete per-position logits and the actual N-wide forward.

## Gate and failure behavior

Bind the candidate to research source containing the LB1 implementation; the cited commit is
already an ancestor of local research main. Attach this check only to the first admitted,
non-bit-exact multi-row candidate, after its route and changed-source identity are resolved. Pass
the three matrices to `check_noise_relative_tolerance` as a blocking pre-keep check, conjoined with
existing operator, route-witness, identity, and whole-model gates. The existing `route_references`
seam is CPU-path-specific; identify and wire the corresponding blocking path for both CPU and GPU,
rather than assuming a CPU reference runs for GPU candidates. Any verdict with `passed == false`
blocks keep, including `reference_comparison` verdicts; the verdict name alone does not signal pass.
Keep current exact gates for N=1 and all
other surfaces. Missing carrier/arm, stale or mismatched identity, duplicate/missing positions,
wrong N, incompatible vocabulary or shapes, fewer than eight positions, or invalid incumbent
reference, or no position reaching the incumbent top-2 margin threshold => `oracle_unavailable`
and candidate cannot be kept. Non-finite candidate logits or a
failed comparison => reject. Do not substitute a single arm, interpolate rows, or relax limits.
The source default is max aggregation, ratio 1.5, and greedy-flip margin threshold
`max(0.25, 2 * floor)`; zero floor requires bit-exactness.

## Fixture validation before hardware

Implement a pure parser/validator stage and fixtures that prove:

1. A valid synthetic three-arm carrier with >=8 aligned positions reaches the existing checker and
   yields its expected result.
2. Changing any arm's prompt, token, position, model/tokenizer/build pin, N, or vocabulary is
   rejected as unavailable before comparison; reordered rows are either canonically realigned by
   the full position key or rejected, never silently zipped by array offset.
3. Missing/duplicate rows, truncated logits, top-k-only payloads, NaN/Inf reference values, fewer
   than eight rows, and a sequential-decode or prefill-only `N>1` decoy all fail closed.
4. Candidate NaN/Inf and an intentional high-margin greedy flip reject; a zero-noise fixture accepts
   only bit-identical candidate logits.
5. Serialization round-trip preserves exact position keys, full logits and manifest digests.

Only after these pass should a harness prove the true N-wide path on a small fixture/model, then bind
the first eligible candidate and schedule correctness runs on both GPU and CPU; the handoff requires
no quiet window. No hardware run is schedulable until
candidate identity, carrier, and actual verify-width evidence exist.

## Source anchors

- Root handoff intake row: `handoffs/active/autokernel-research-loop.md` (AK-PORT-LB1.1, under
  “Research intake 2026-10-22 — Locals + Beacon”): three required arms, gate limits, merge prerequisite,
  and GPU/CPU correctness follow-up.
- Research commit `f8df555cf76a718f11bcabc8588fc1d8ab07cc69`,
  `scripts/kernel_rnd/autokernel/loop/noise_relative_tolerance.py`: three aligned per-position
  matrices, minimum eight positions, shape/finite handling, ratio/margin defaults, and zero-floor
  exactness.
- Same commit, `scripts/kernel_rnd/autokernel/loop/gates.py`,
  `check_noise_relative_tolerance`: `unavailable` maps to `oracle_unavailable`.
- Same commit, `scripts/kernel_rnd/autokernel/loop/run.py`, around `route_references` and
  `admitted_route.model_identity`: candidate integration seam and existing blocking references.
- Same commit, `scripts/kernel_rnd/autokernel/loop/program.md`, verify-width note (2026-10-06):
  current completion/perplexity probes decode one token at a time; prompt batching is not speculative
  VERIFY width.
- Inspection note: `/mnt/raid0/llm/tmp/compute-flags/handoff-sessions/autokernel-research-loop/port-gate-next.txt`.

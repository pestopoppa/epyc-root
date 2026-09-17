# AutoKernel AK-integrity / AK-promotion controls audit — 2026-09-17

Scope: the two unchecked rows under `handoffs/active/autokernel-research-loop.md`'s
2026-09-17 Dream-RSI update, read with intake-1447, intake-1451 and intake-1454.
This is a code audit and implementation specification, not an experiment result.
No provider, build, inference, benchmark, or loop run was started for this task.

## AK-integrity: avoid duplicating guards; close the actual gap

The current GPU loop already supplies the two basic SimpleTES-style protections:

- `scripts/kernel_rnd/autokernel/loop/bench.py:273-299` invokes hardened
  `llama-bench` for every arm and refuses a missing hardening receipt.
  `execution/microbench.py:1765-1815` requires distinct per-repetition input
  digests, rotated input/context addresses, stable threads, and completed
  synchronization checks. This is stronger against content/pointer memoization
  than merely requesting fresh data.
- `loop/integrity.py:258-290` derives the complete dirty set before build,
  refuses undeclared and evaluator paths, and applies the versioned
  `execution/reward_hack_scan.py` detectors to the whole candidate diff.
  The scan includes environment/timing probes, pointer memoization, capture
  replay, and content specialization. It is the existing static deny screen;
  another generic blocklist would create parallel and divergent policy.

One narrower gap remains: the timed GPU receipt checks *output invariance*
for each fresh content vector across two addresses; it does not independently
compare that vector's candidate output to a trusted reference. The earlier
`loop/gates.py:90-125` `test-backend-ops` correctness suite is a separate input
sample. A candidate can therefore pass that suite and be consistently wrong
on a timed input. For CPU serving, `loop/serving.py:899-904,973-981` intentionally
reuses the original frozen request bytes under `cache_prompt=false`; varying
ranked requests would change the target instrument rather than harden it.

Narrow next change: a *separate* fresh-input reference check adjacent to each
timed arm, outside its ranked interval. Predeclare a bounded, target-compatible
input family from the sealed surface/recipe; derive the seed before acquisition;
run candidate and trusted anchor/reference on the same new input; bind their
outputs, input digest, source/binary identities and measurement-arm ID in a
receipt. A mismatch is a correctness/integrity refusal, never a speed sample.
Do not alter the ranked frozen request or rebuild an evaluator from candidate
source. First run planted wrong-on-timed-input and clean controls with no
hardware; a live check needs the existing benchmark-window claim. This is the
specific unimplemented part of the row, not a reason to replace the guards above.

The AIChilles-inspired extension belongs in the existing §9.5 cheap suites:
derive a legal shape/route grammar from sealed recipe and evaluator constraints,
then compare candidate against the exact sealed anchor on correctness, runtime,
memory and fallback/dispatch. Record distinct divergence *paths*, not merely
far-apart input values. It is a bounded report-only probe until its cost and
false-refusal rate are measured. Pre-register the cost that robust gating can
erase a headline gain, as [AIChilles §V-D](https://arxiv.org/html/2606.15834v2)
reports; no performance result or promotion authority is inferred from that
external study.

## AK-promotion controls: prospective evidence, not retroactive replay

`loop/actors.py:662-690` builds the exact authoring prompt and passes it to
`_run_agent`, whose `:153-173` subprocess path does not persist prompt bytes.
`loop/run.py:1972-2011` records a serving-gate result and advances the champion
of record on `PROMOTE`; it does not capture or replay the author prompt.
Therefore historical keeps cannot honestly be labelled same-prompt replayable.
Matching by mechanism name or timestamp would not identify the prompt that
produced a particular committed candidate.

At a future explicit run boundary, add a **default-off** receipt at
`AgentPlanner.author` before provider invocation: exact assembled prompt bytes
and SHA-256, complete provider route/model/effort and executable digest,
pre-author clean parent commit/tree, target/surface and recipe epoch. Write one
immutable mode-0600 artifact with a hard 1 MiB prompt cap; do not put raw prompt
bytes in the dashboard or `experiments.db`. Link its content digest and locator
through the outcome's exact attempt identity to the measured tree and kept
commit. Refuse an opt-in invocation if capture fails; default-off operation is
unchanged. GitNexus impact for `_run_agent` on the indexed research clone was
LOW (5 upstream symbols, one Loop module; index at `ae8e5ef`), but validate the
fresh call sites before that later edit. A fixture must replay two same-named
mechanisms and prove they cannot cross-join receipts; another must prove capture
failure prevents an opt-in provider call. This capture is not implemented here.

After a decisive promotion, an **explicit metered, inference-gated** command may
run ten independent exact-prompt replays from the recorded clean parent in
isolated worktrees. Apply the existing correctness and matched measurement
gates to each resulting candidate; report runnable/correct, byte-identical
diff, and signed gain-recovery distributions. Replays are observations and can
neither alter the original promotion verdict nor enter the champion branch.
This follows the replay question in [EvoReplay §5.3](https://arxiv.org/html/2605.20086v1),
not its cross-domain score ratio as an AutoKernel threshold.

The BO tuning-ceiling probe uses **one immutable intermediate kept commit**,
not an overwritten patch. Predeclare numeric constant locations, legal bounds,
metric direction, fixed evaluator/recipe, and budget before observing values;
hold source structure fixed. The paper's comparable budget is 24 evaluations
(8 initial random, 16 BO), but that is a future metered study, not authorization
to spend it. Report best validated BO effect versus the final promoted effect;
invert lower-is-better metrics before comparison. No BO library, exposed-knob
manifest, prompt receipt, or budgeted command is installed by this audit, and
no replay/BO result is claimed. See [EvoReplay §B.9](https://arxiv.org/html/2605.20086v1).

The two controls remain report-only; adoption into a keep/promotion gate would
require the standing independent confirmation contract and an operator-gated
run boundary. No handoff checkbox is flipped by this document.

## Follow-up implementation (same day)

Research branch `sub/ak-integrity-promotion-20260917` commit `6c5bd9bb`
adds `loop/fresh_correctness.py` and hermetic fixtures. The helper is opt-in
and report-only: it accepts a runner from the resource-owning caller and has
no live loop callsite. It refuses a swapped binary or modified test instrument
before invoking anything; probes the selected binary for seeded/property
capabilities; then uses the existing `t0_provider` constructor and strict
console parser. Its separate status/verdict fields distinguish a reviewed
GPU-source structured reference (`reference_valid`), independent host property
only (`property_only`), and missing capability/evidence (`oracle_unavailable`).
With no usable oracle, even a nonzero suite exit remains an operational fact,
not a correctness verdict. The suite's documented `--help` exit code is 1;
strict help-banner and flag parsing establishes capabilities instead.
It does not claim token-level parity, alter ranked requests, or relax the
unresolved CPU cross-build oracle limitation above. Focused adjacent suites:
259 passed and 19 subtests; Ruff and diff checks clean. No hardware was run.

## Opt-in GPU comparison seam (same day)

Research commit `adc5e2a4` adds a `fresh_check` observer to the existing
`loop/bench.py` GPU A/B comparison. It is default-off, has no live caller, and
runs only after each measured `llama-bench` invocation, not warmups. The
resource-owning caller supplies the full receipt writer/collector; the
comparison retains only bounded identity/status/hash summaries, excluding raw
op-suite output. Observer errors record `oracle_unavailable` and cannot make a
correctness claim or veto a timed diagnostic sample. Because intervening GPU checks can
alter later timing conditions, opt-in refuses `calibrated=True` before launch:
its effect is diagnostic and `decisive=None` until a separate A/A calibration
of that exact protocol exists. Default comparisons are unchanged. Hermetic
fixtures cover real receipt collection through the seam, warmup exclusion,
default-off behavior, observer failure, and nonpromotability. Focused suites:
262 passed and 19 subtests; Ruff and diff checks clean. No GPU or CPU inference
was run.

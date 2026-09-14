# 2026-09-14 — zero-inference backlog sweep (session `noninf-20260914`)

**Session**: zero-inference backlog sweep, 14 dispatched items, main thread + Opus-5 subagents fanned
out 3–5 wide. No inference, no benchmarks, no process management, no pushes; every branch below is
local and unmerged. This file folds the twelve wrap-up fragments that were final at wrap time
(`tmp/noninf-wrapup/`); two further items (`invlog`, `floorunit`) were still in flight and are not
recorded here.

---

## WRAP-10 + MEAS-2 — INF-70 recipe module and the locked-build idiom out of scratch

INF-70 WRAP-10 and MEAS-2 landed together in `epyc-inference-research` (`fc8c44de`, `932bf5c4`, branch
`fix/noninf-wrap10`, not pushed). PROD-1's Qwen3.8-Flash-Next CPU serving recipe, its 54-test anti-drift
suite, the only sanctioned CPU launcher and MEAS-2's region-locked build wrapper had existed solely under
`/mnt/raid0/llm/tmp/inf70/` and would have died with scratch; they are now in git with the test file wired
into the Makefile's PYTEST_SMOKE list. The champion record was reconciled against CURRENT-CAMPAIGN.md: the
draft named the fold-candidate branch, which is where the merge was staged, not where the consolidated
champion lives, and the full sha ef81196d5bdd4190b46dff4ae7eecc333a46c8ce is now recorded. No measured
number was relabelled — the champion3 constants (9c4f73e29, build 10241) stay put and are marked as the
measurement pin, an ancestor. Two digested builds of ef81196d5 were located and recorded, one per surface,
both build 10301: the HIP fold build (whose digests reproduce the champion-max-performance doc byte for
byte) and a previously unrecorded CPU build whose cmake matches the recipe's own. The binary pin
nevertheless stays unresolved, and for a sharper reason than before: the 18-launch final-characterisation
run names its champion arm `bin-r1 (10303)`, so the canonical headline came off the retest1-fix1 instrument
tree rather than either digested build, and nothing was ever measured on the ef81196d5 CPU build. The
module refuses to certify the current champion instead of papering over it. The headline's own binary was
then captured out of scratch before it could be collected: HEADLINE_BINARY records build 10303
(2516c9807b8a92d472c8e75a0a1ce8558d2e34a7 on inf70/retest1-fix1) with five object digests, four of which
reproduce the digest file the build script wrote at build time. That tree descends from ef81196d5 by exactly
two instrumentation commits, so the headline's "ef81196d5" label is an unstated delta rather than a wrong
lineage — a materially better reading than the day's first, and still not a valid pin, since two of the
instrument's knobs default ON for a measured -2.136%. This session ran zero inference; the only binary
invocations were the suite's sub-second argument-parse dry-runs. Still open: closing the pin needs a
measurement on a digested ef81196d5 CPU build, WRAP-12 should correct the "measured on ef81196d5" label
wherever it was propagated, and WRAP-11's branch push remains with the operator.

## RTG-55 MHS-1 + MHS-2 — PromptForge mutation safety

Closed RTG-55 MHS-1 and MHS-2 on `epyc-orchestrator` branch `fix/noninf-mhs` (`7d4b40a8`, `c27eec6c`; 4 files,
+1122/−63; zero inference). PromptForge's Tier-2 mutation validator was writing the model-generated candidate over
the live repo file and then importing it in-process (`prompt_forge.py:1149`/`:1157` at `origin/main`), so every
proposal's module top level executed unsandboxed with the autopilot's authority, and the live file briefly *was*
the unvalidated candidate. Layer 4 is now `screen_static_safety()` — `ast.parse` plus an explicit AST denylist over
module-level side effects, imports outside a 30-entry stdlib allowlist, banned calls and modules, dunder attribute
access, and a strict inertness profile for `new_file` proposals — with no repo write and no in-process execution;
dynamic validation was removed rather than sandboxed because no caller consumed runtime behaviour. Capabilities the
original file already used are grandfathered, so a mutation is judged on what it adds; a parameterized test asserts
a no-op mutation of all five allowlisted files still passes. MHS-1 landed the closed `MutationEffect` enum
(`inert|constrain|expand|replace|unsafe|unknown`, total normalization, truncated), carried on `CodeMutation` and
refused by both apply paths when `unsafe`; the CONSTRAIN/REPLACE split is derived mechanically from the candidate,
which answers the handoff's Open Question 3. Enforcing inertness surfaced a second defect: the MH-9 AutoMem
`schema_evolution` prompt asked for a class-based contract the ratified denylist rejects, which would have made the
lane propose only rejects, silently — per coordinator ruling the denylist was kept and the prompt rewritten, with
the shape example shipped as a module constant that a test screens, so prompt/denylist drift cannot recur. Test
selection `-k "prompt_forge or code_mutation"` went 40 → 140 passed / 6 skipped (100 new tests), `ruff check`
clean; the one failure in the wider `-k autopilot` selection is pre-existing on a pristine checkout at the same
HEAD. Still open: MHS-3 through MHS-6, whether the strict profile should admit an inert `ClassDef`, and that
`apply_code_mutation` still writes the live tree rather than staging.

## EVL-13 ETR-2 + ETR-3 — the unread quality guard and the silent-scoring hole

Closed EVL-13 ETR-2 and ETR-3 in `epyc-orchestrator` (`250a5d13`, branch `fix/noninf-etr`, +641/−16 over
`origin/main` `35b05fde`; zero inference). ETR-2 was a guard computed, documented and never consulted:
`EvalResult.quality_measured` was declared at `safety_gate.py:602` and read by neither `check()` nor
`update_baseline()`, so a trial that scored nothing entered the promotion gate as a literal 0.0 candidate
and only the independent REL-1 reliability floor happened to stop it. The gate now fails closed on the
flag with its own `quality_not_measured` category, suppresses (rather than charges) the quality legs so a
non-measurement can never be written into `failure_analysis` as a fabricated regression, and refuses the
baseline write with `ineligible_reason="quality_not_measured"`. The write side was equally at fault:
eleven early-return placeholders in `eval_tower.py` and the consult-gate probe in `actions.py` built
`quality=0` while leaving the flag at its `True` default — all now declare `quality_measured=False` with a
named reason, and every journal row carries the distinction via `_eval_details_from_result()`. ETR-3 was
closed with a structural signal already present but unread: a non-blank answer whose response reports zero
generated tokens did not come from a decode, so it is excluded as `answer_without_generation` on
measurement paths (eval tower, seeding calibration) and deliberately left scoring on the live-serving
reward path. 26 new unit tests, including an AST guard over the producer module so a new placeholder cannot
reintroduce the defect; the two failures in the touched areas reproduce on a clean `origin/main` worktree
and are not from this work. **No quality number already on record changes** — the edits affect
promotability and disposition only. Still open: ETR-1 (agent-vs-platform failure scoring) remains an
operator decision (OP-20), and the branch is unpushed/unmerged.

## EVL-14 EV-14d + EV-14e — short draws and the baseline pin

Closed the two non-inference defects in the EVL-14 EV-14 block on `epyc-orchestrator`
`fix/noninf-ev14`, commit `4555677e` (6 files, +868/−5, zero inference).

EV-14e: the baseline a trial was judged against had no field on `JournalEntry` at all — it reached
the journal as prose in `failure_analysis` and was parsed back out by
`experiment_journal.py:99`'s `_BASELINE_QUALITY_RE`. A regex over a sentence recovers a number but
never the comparison's identity, and the prose is written only on a regression, so every passing
trial recorded no baseline whatsoever. `baseline_pin` now carries tier, reference quality, the
EV-14c revision, both instrument eras, the per-suite reference map and counts, and the stored
delta; it is captured via `Baseline.pin_tier(register=False)` before `update_baseline()` can move
the reference, which is why a write-time reconstruction would have recorded the candidate's own
promoted number as its incumbent. The reader falls back to the regex for legacy rows only, and says
so in a warning.

EV-14d: `_eval_batch` returns `[r for r in results if r is not None]`, so four per-role writers
that set `n_questions = len(results)` (calibration, math_rebaseline, question_subset,
resume_incomplete) made 40-of-50 indistinguishable from a complete draw of 40. `n_questions` is now
the requested count, with completed/missing/ratio/`draw_complete` beside it and a top-level fold;
the eval-batch window runner's arm and verifier blockers refuse a recorded requested/completed gap.

28 new unit tests. `pytest tests -k "eval_tower or journal"`: 402 passed / 0 failed both before and
after (441 with the new files). Still open in EV-14: EV-14a (held on the architect_general and
worker_vision lanes), EV-14b and EV-14b′ (operator decisions), EV-14f.

## RTG-23 — absent quality is not zero; the objective gate checks all four axes

RTG-23 closed the half of the W3d zero-quality objection that does not depend on the operator's
goodput-vs-raw-rate choice. `tier_specs.py` read every objective axis but the rate through `float(x or
0.0)`, so a never-measured quality entered the live 4D dominance vector as a real 0.0 — and a point holding
the max rate is unbeatable on rate, so dominance can never remove such a point. `objectives_measurable`
compounded it by promising to check every axis and checking only the rate: on origin/main a result with no
quality and no reliability attribute at all returned True. `epyc-orchestrator` `fb16d860` gives absence its
own state on every axis (`None` on the read side, `UnmeasuredObjectiveError` on construction), makes the
measurability gate delegate to the builder it gates so the two cannot diverge, and teaches the dashboard,
planner-evidence and journal-write consumers to report absence as absence rather than as zero. Offline
replay over both AutoPilot journal shards (1,372 trial rows, journals unmodified, zero inference) moved
builder-refused rows from 0 to 225 and T0 audit entries from 318 to 233 while leaving every frontier size
unchanged (legacy T1/T2/T3 11/4/1, rate T1/T2 13/8). That replay also corrected the record: the 231
falsy-quality rows are 225 whose eval never ran (224 T0 sentinel, 1 bug-corrupted T1) plus 6 genuine
measured zeros, and zero-quality frontier points were 0 both before and after — the data defect was real,
the frontier corruption it was believed to have caused had not occurred. Still open: the dominance hole
itself (operator options a/b/c) and W3e's positional objective-tuple consumers. Tests:
`tests/unit/test_objective_absent_quality.py` (12 new), the objective/pareto selection 143 passed / 0
failed before and after, and the 5 failures in the wider unit sweep were reproduced on origin/main.

## RTG-15 EPD-3-R2 + EPD-3-R3 — one embedding convention, one builder

Closed RTG-15's EPD-3-R2 and EPD-3-R3 in `epyc-orchestrator` (`9096a600`, branch
`fix/noninf-epd3`). The finding was not a bad format but a bad process: the episodic store sits on the
2026-07-27 canonical embedding text, yet `MemoryRecord.embedding_text()` had no live callers — only
the reseed tool and the degeneracy guard — while the three writers that actually run each re-spelled
the convention and had already drifted from it. `embedder._serialize_task_ir` keyed on field presence
rather than truthiness (emitting a literal `priority:None`), skipped `.strip()` and the 2000-char cap,
and appended `constraints:`/`input_types:` segments no other site emits; it is also the live *query*
serializer, so the drift cost recall silently. `seeding_injection._precompute_embedding` hard-coded
`type:chat`, which mislabels the vectors of 3,795 `math`, 3,787 `hotpotqa` and 3,585 `coder` rows
whose own stored context says otherwise. `seed_loader` embedded the raw task string with no prefix,
the shape all 94 post-reseed `seed` rows carry. All three now route through one new thin entry point,
`memory_record.embedding_text_for()`. The 26-test guard pins them to goldens lifted from REAL live
store rows (read-only) rather than to each other, and asserts delegation by monkeypatching the builder
so a future re-spelling that happens to agree today still fails; restoring one drift fails 3 tests.
`pytest -k "embed or seed or routing"` went 1113 -> 1139 passed with the same 9 pre-existing
`test_e8_quality_baseline_reseed` failures. Zero inference. Still open: EPD-3-R1 (dropping `priority`
from the canonical text) remains operator-gated — the recipe change and the corpus re-embed must flip
in the same window.

## PREFIX-1 (web half) — the web ColBERT reranker routed through the shared encoder

Closed the web half of PREFIX-1. `src/retrieval/colbert_encoder.py` was extracted in 2026-08 for two
consumers, but only the KB side was ever migrated: `src/tools/web/colbert_reranker.py` kept its own
`_encode` (`:153-196`) and so received none of the `fe55b228`/`4e5e84c0` fixes — no `[Q]`/`[D]` role
prefix, a hardcoded two-input feed that returns `None` on any graph declaring `token_type_ids`, no
`do_lower_case`, failures logged at DEBUG, and `_MAX_QUERY_TOKENS = 48` (GTE's number) against the
LateOn slot's declared `query_length: 32`. The flag is off by default, so nothing served wrong
answers; what was lost is measurability — the missing prefix moves MaxSim by max |Δ| 1.63e-01 and
flips top-1 on 37.5% of queries, ≈25× the INT8 perturbation, so the S5 A/B would have measured the
encoder rather than the models. `epyc-orchestrator` `f876d989` makes the reranker a thin consumer:
the private encoder, both token constants and the duplicate ONNX session are gone; roles are
`ROLE_QUERY`/`ROLE_DOCUMENT` per call with a both-sides `ROLE_NONE` fallback; token caps come from
the checkpoint's own `query_length`/`document_length` via two new encoder accessors (GTE 48/300,
LateOn 32/300, Reason-mxbai 256/2048), the document cap clamped to the 64-token snippet budget the
2026-08-12 latency numbers were taken at. No re-embed was needed — there is no stored web index. The
three-slot selector moved into the encoder, which owns the single session, and re-pointing it now
drops a session loaded for another checkpoint instead of serving the old one under the new name.
Reranker tests went 51 → 74 passed with zero failures and the suite got faster (26.5 s → 7.4 s)
because the encoder is now mocked where the old tests loaded the real 144 MB graph; four guards were
mutation-tested (2–4 named failures each), and one first-draft guard was found vacuous that way and
rewritten. Zero inference. PREFIX-1 stays open on the KB corpus re-embed (OP-24).

## EVL-04 SEQ-B2 — the sequential refutation counterfactual, captured at stop time

SEQ-B2 (EVL-04) landed the write side of the sequential refutation counterfactual. Before
today, `safety_gate.py::_sequential_verdict` journaled only the JOINT `state` when a
sequential candidate was stopped; which axis refuted it and the surviving margin on the
other axis existed only post hoc, in a second independent copy of the refutation predicate
inside `readjudicate_sequential_candidates.py`, valid only under the current policy
constants. Because a stopped candidate's missing trials can never be recovered, that
attribution was capturable at stop time or never — the belief-kernel write-side rule in its
strictest form. `epyc-orchestrator` `4c220b11` adds one canonical definition
(`sequential_verdict.axis_refutation` / `refutation_record`, schema `seq-refutation-v1`),
writes it into the journal block on the refuted branch only (additive; legacy rows and
non-stop rows load unchanged; no journal file on disk was touched), and reduces the analysis
script to a thin delegation that prefers the live field and marks reconstructions as such.
The margin sign convention is now stated (`wealth - threshold`, negative = refuted, futility
inclusive / budget strict) and the both-axes case is deterministic (quality first, with
`both_axes_refuted` carried separately). 17 new tests, including live-vs-reconstructed
agreement on a synthetic candidate run through the real gate;
`pytest tests -k "sequential or safety_gate or readjudicat"` went 268 → 271 passed with no
failures, and `git merge-tree` confirms a clean merge with `fix/noninf-etr` (`250a5d13`).
Still open and untouched: SEQ-B1, the joint-gate-vs-quality-primary policy question, which
is human-amendment-only and was deferred by the operator on 2026-08-11.

## EVL-10 M-12e + EVL-47 SC67 — Tulving scorer subsets and the belief-kernel write hook

Closed EVL-10 M-12e, the zero-compute scorer prerequisite that gates every M-12 arm. The Tulving
scorer had three subset defects, all settled by counting against the benchmark authors' own shipped
artifacts rather than by reading prose: Simple Recall was computed over all 456 questions instead of
the 366 `get=="all"` recall questions; Kendall tau had no coverage requirement, so a correctly ordered
partial list scored 1.0 and the metric paid for withholding; and the five bins keyed on ground-truth
item count where the paper bins on matching events (`n_chapters_correct_answer` reproduces the
authors' own bin column 686/686, item count only 629/686). Re-scored run `20260619_141212` offline
from stored responses — no model loaded, no socket opened — writing a new artifact beside the
untouched original. Simple Recall moved 0.5530 → 0.5684 (subset fix alone 0.5755, bin fix alone
0.5402); Chronological Awareness stayed at 0.1593, but only because no partial-coverage question on
this run matched two items, so the tau defect is latent rather than absent — 37 of 45 chronological
questions are now labelled partial, and 30 of those 45 carry fewer than two ground-truth items, which
makes two thirds of the tau leg structurally zero and is a CAS construction problem in its own right.
`SCORER_VERSION = 2` now rides in every scored artifact. Also landed EVL-47 SC67: the Tulving
belief-kernel write hook (root `baaa6741`, research CLI hook in `dcb769c1`) — two claims per arm over
the disjoint subsets, locator pinned to the run, `--arm` mandatory, and pre-M-12e scorer versions
refused at both ends. Pre-hook runs including `20260619_141212` emit zero rows, permanently. Research
tests 85 → 108; root vidya suite 1068 → 1092 passed with pre-existing failures unchanged. Still open:
M-12a–M-12d remain compute-gated. (The four wiki paragraphs quoting the old SRS/CAS were refreshed in
this wrap-up — see below.)

## RTG-02 — era-stamp reachability (the mutually blocking provenance fences)

RTG-02 landed in `epyc-orchestrator` `d03218fc`: both AutoPilot instrument-era stamps are now reachable.
The speed-era stamp had sat ~220 lines behind the eval-quality re-baseline hold's early return in
`update_baseline()`, so with both eras active it was unreachable code — the quality hold's remedy is an
era-stamped baseline, and the stamp only ran inside the promotion the hold refuses, latching both fences
permanently and leaving every cross-era throughput violation demoted to a warning. The two axes are
different instruments and now clear independently: a new narrow helper re-anchors `frontdoor_speed` plus
`autopilot_speed_era` from the same in-era measurement on the refusal path, gated on exactly the
conditions under which the baseline would itself have re-measured that speed, while the quality refusal
stays fail-closed. The second half fixed `_apply_calibrated_baseline_result`, which wrote every baseline
value and never `eval_quality_era`: the calibration now stamps the era of the instrument that produced
the result (carried on the result by `eval_tower._stamp_eval_instrument` from the human-owned era
registry) and refuses an unstamped or unresolved result instead of guessing the era current at write
time. The trust boundary was checked rather than assumed — both stamps land only in
`autopilot_state.json`, which `human_only_paths.yaml` does not enumerate, and no era field can reach the
human-only YAML seed. 23 new tests in `tests/unit/test_era_stamp_reachability.py` (18 red before the fix,
including the deadlock reproduction); the briefed selection went 1674 → 1696 passed with the same 20
pre-existing failures. Zero inference, zero process management. Still open: whether an autonomous
provenance write should emit a journal receipt (decision package prepared, recommendation B).

## INF-50 SW-4 — spec-dec runtime switchability recorded from v9 source

INF-50 SW-4 landed, and it corrected the box it was built on. Reading the frozen production kernel
(`/mnt/raid0/llm/llama.cpp` @ `production-consolidated-v9`, `0db32c06e3e550065b78311a6031ef3dd2c4f27c`)
showed SW-1's 2026-07-31 conclusion — that the whole per-request speculative surface is compiled out —
is true of v8 and false of v9: the `#if 0` now opens at `server-schema.cpp:210`, below the
`speculative.n_max` registration at `:205`, and `:542-547` adds a clamp whose only purpose is to bound
the newly-live field. So a request can LOWER the draft budget (0 disables drafting for that request)
and can never raise it above `--spec-draft-n-max`; spec type, draft model, the ngram parameters,
`n_min` and `p_min` remain launch-fixed, and no request can disable one lane while leaving the other
on. That table, with file:line plus the kernel hash against every row, is now
`speculative_decoding_policy.runtime_switchability` in the MASTER registry
(epyc-inference-research `d28ab833`); the orchestrator's lean view was regenerated from it
(`a1d36daf`). The same pass closed a self-contradiction: four per-role records still described a
composed `ngram-mod,draft-mtp` launch stack 880 lines below `production_recipe: draft-mtp`. Production
launches `draft-mtp` alone — every `spec_type` in `derived/stack_priors.yaml` is `draft-mtp`, `none` or
`baseline`, and `orchestrator_stack.py:407` emits that value verbatim — and the composed recipe was
reversed on 2026-07-31 by `a126e43d` ("draft-mtp alone, ngram nowhere") and propagated by `ed891211`.
All four now cite the reversal. No launch value changed; ngram **measurement** records were left
intact. Zero inference. Tests `-k "registry or stack_prior or descriptor or spec"`: 838 passed, 6
skipped, before and after; `stack_change_pipeline check` unchanged at 57 pre-existing errors, none
spec-related. Still open: SR-5's reconciliation narrative; SW-2 and SW-3 were rewritten/amended in
this wrap-up rather than answered, because SW-2's predicted outcome is the v8 behaviour and SW-3's
premise (the budget surface does not exist) is no longer true.

## INF-40 — MoE-Spec surface reconciliation and the `architect_critic` decision package

INF-40's two contradictory MoE-Spec numbers were reconciled from artifacts already on disk, with zero
inference. The GPU **−2.92%** row (`champion_anchor_20260828/champion_anchor_validation.json`, CH-4)
was measured on Qwen3.8-27B-Q8_0, which is **dense** — `general.architecture qwen35`, 0 of 866 tensors
match `*exps*`/`ffn_gate_inp`, no `*.expert_count` key in the GGUF — while `--moe-spec-budget` masks
inside `build_moe_ffn` (`src/llama-graph.cpp:1985`), a subgraph a dense model never builds. Both GPU
arms therefore ran identical code: the `pp512` arm is inert for a *stronger* reason than the `tg128`
arm the record had already voided. It is also non-significant on its own six samples (medians −2.92%,
means −1.75%, Welch t = −0.87, ranges fully overlapping), so it is usable only as a ±3.7% noise reading
for that GPU surface. Net: the handoff's "countervailing surface" does not exist, and the only live
objection to the CPU **+10.7%** (10.84 → 12.00 t/s, α −2.4pp, era E9) is its own thinness — n=3,
Δ ≈ 2.9σ, below the ≥5-rep bar for a ≥5% claim, with the 5-rep confirm declined on 2026-08-27. Both
numbers are OBSERVATIONS: neither record carries a protocol-id. A four-part operator decision package
for `architect_critic`'s `moe_spec_budget: 128` was prepared (recommendation: buy the 5-rep confirm
first, since that run also re-measures acceptance), plus a spec for the genuine MoE-on-GPU cell
(35B-A3B-Q8 at ≥5 reps in a batched posture that crosses `min_batch 4`). Five downstream sites quote
the void number as a general regression verdict; the wiki and handoff corrections landed in this
wrap-up. No registry or index write was applied.

## RTG-02 invlog — per-request tool telemetry and the dropped `assigned_role`/`work` payload

RTG-02 closed both paired boxes in the autopilot handoff's 2026-08-03 adversarial-sweep section.
The orchestrator's tool registry is one object per API process, and four request-scoped readers were
building per-request telemetry out of its shared invocation log — so a durable episodic record
persisted other concurrent requests' tool calls, and two SSE emitters streamed other requests' tool
events to the wrong client. Fixed by scoping structurally rather than by clearing: all four now read
the request-local `REPLEnvironment._invoked_tools` buffer already captured at the `_invoke_tool`
chokepoint, which is exact, lock-free and released with the request even on exception. The shared log
became a bounded diagnostic ring (deque, cap 1000, env override), ending an unbounded growth path
that had no clearing caller anywhere in `src/`. An `ast` test now forbids any request-scoped module
from calling `get_invocation_log()`; it flags all four pre-fix call sites.
The paired write-path defect had the same signature — data computed and dropped at a boundary. Both
`assigned_role` and the `work` payload were only ever written by `EpisodicStore.store()`, which every
UPDATE branch in `QScorer` returns before reaching; since the find-or-update branch fires ~11x more
often than create, neither field was effectively ever populated. New `merge_row_metadata()` carries
both onto the existing row with merge-not-overwrite semantics. The third hole named in the same box
was confirmed by measurement and fixed too: the work-sanitize policy runs twice on the live create
path and was not idempotent, so a 32,500-char answer was stored reporting `total was 32049` and a
50-entry elision reported `_elided_entries: 1` while silently discarding the first retained entry.
Commits `d65a4e93` and `b69bda61` on `fix/noninf-invlog`; 14 files, +904/-79. Assigned suite 1131 →
1146 passed, 12 skipped; a wider 808-test sweep clean. Non-vacuity was checked by neutering the fix
and by running the guard against `origin/main`. Two `e8_quality_baseline` failures seen in a wide
sweep reproduce on a clean `origin/main` worktree and are logged as pre-existing, unowned.

## INF-66 R23-55 + INF-73 U2 — every floor record carries its `unit`, and a cross-unit gate REFUSES

Closed INF-66 R23-55 and the INF-73 U2 floor-`unit` box in `epyc-inference-research` `eb8a88de`, on branch
`fix/noninf-floorunit` (zero inference). Every autokernel floor record now carries the `unit` its
dispersion was measured in and the `n` it was estimated from, and the two fields are enforced where they
cannot be faked: `write_floor` has no default unit and refuses an omitted, unknown, contradicted or
`n`-less row without writing anything, while `FloorReading.gate_floor` is the single point at which a floor
becomes a gate bar and refuses a legacy or cross-unit one — naming the file, both units, the measured
0.501% (arm) vs 2.793% (process-launch) spreads and the recalibration command. The unit is derived from the
harness rather than passed in: `serving.calibrate_floor` and `serving.compare` relaunch the server per
sample, so both are `process`-unit by construction, and the bench/screen instrument is the same because its
arms alternate across `llama-bench` invocations. Pre-rule records were left byte-identical on disk: a
serving floor's silence is unresolvable and refuses, while a bench record derives its unit from its
single-writer schema, which closed the rule over all 7 live calibration artifacts with no rewrite. Added
`test_floor_unit.py` (31 tests) covering the write refusals, the legacy-load refusal, matching units
passing, a mismatch naming both, and a full record round-trip; the loop suite reads 155 failed / 2596
passed against 176 / 2509 on `origin/main`, with zero new failures by name (the remainder are pre-existing
and environmental). Still open on that program: the CPU A/A calibration itself, per-surface bundles,
headline admissibility from ≥N independent launches, and the between-launch variance investigation — all
host-time work.

---

## Cross-cutting findings

- **The campaign headline was measured on build 10303, not `ef81196d5`** (wrap10 §7). The run record
  (`/mnt/raid0/llm/tmp/inf70/agents/retest1/CHAMPION-FINAL.md:45`) names its champion arm
  `bin-r1 (10303)` while its own header says "baseline `ef81196d5`", and every downstream quotation of
  the 43.281 t/s / 2.1857× / ≥117% / ≥81% figures inherits that. The numbers are not wrong and the
  lineage is not wrong — `2516c9807` descends from `ef81196d5` by exactly two instrumentation commits —
  but the **delta is unstated**, and two of that instrument's five knobs default ON for a measured
  −2.136%, so the label is load-bearing. Belongs in WRAP-12's prose sweep.
- **A dense-model null is not a MoE counter-result** (inf40). A flag whose effect lives inside a
  subgraph the model never builds produces two arms of identical code; the resulting "regression" is a
  noise reading, not evidence. The structural test is the model class (expert tensors / `expert_count`
  key), checked before the number is quoted — and it is a *stronger* precondition failure than the
  batch-size one the same record had already voided.
- **SW-1's v9 falsification** (sw4). A source-derived claim about the per-request speculative surface is
  only as good as the kernel commit it was read at: the `#if 0` moved between v8 and v9, so
  `speculative.n_max` is now a live per-request, lower-only field. Never restate that surface without
  the kernel hash.
- **Baseline: 29 pre-existing `pytest tests/unit` failures on `epyc-orchestrator` `origin/main`
  `35b05fde`** (etr §2), with 12,667 passing. The sorted FAILED list is byte-identical before and after
  `fix/noninf-etr`. They sit in e8-quality-baseline (reseed / v5 / recovery-finalizer, 16), dashboard
  helpers+panels (3), baseline-authority/ledger (3), `test_autopilot_actions` recency window,
  `test_debug_scorer_code_execution`, `test_e8_final_c1_retry` (2), `test_orchestrator_stack_reload`,
  `test_compact_row_and_aggregate_accept_duck_typed_rows` and
  `test_pairwise_holdout_writes_guarded_collection_manifest_and_script`. Any session reading a failure
  count on this repo should subtract these first.
- **Every live serving floor is now `legacy` and refuses to gate** (floorunit §7). The `unit` + `n`
  enforcement is fail-closed by design: every serving-floor file on disk predates the rule, so
  `FloorReading.gate_floor` refuses each of them rather than gating on a floor whose dispersion unit is
  unknown. No file was rewritten. The binding successor is **R23-61a** — recalibrate the serving floor
  through `recal_serving_floor --apply` (which now stamps `unit` and `n`) at n ≥ 24 with a CI under the
  recipe in force; it needs the GPU, ~30 min. The next serving gate cannot run until then. The bench
  half did *not* need this: a pre-rule bench record's unit is derivable from its single-writer schema.

## Branches to merge

Every branch below is local and unpushed.

| Repo | Branch | Commit(s) | Task |
|---|---|---|---|
| epyc-inference-research | `fix/noninf-wrap10` | `fc8c44de`, `932bf5c4`, `45d6ecce` | wrap10 (WRAP-10, MEAS-2) |
| epyc-orchestrator | `fix/noninf-mhs` | `7d4b40a8`, `c27eec6c` | mhs (MHS-1, MHS-2) |
| epyc-orchestrator | `fix/noninf-etr` | `250a5d13` | etr (ETR-2, ETR-3) |
| epyc-orchestrator | `fix/noninf-ev14` | `4555677e` | ev14 (EV-14d, EV-14e) |
| epyc-orchestrator | `fix/noninf-rtg23` | `fb16d860`, `551d0e48` | rtg23 (W3d absent-quality half) |
| epyc-orchestrator | `fix/noninf-epd3` | `9096a600` | epd3 (EPD-3-R2, EPD-3-R3) |
| epyc-orchestrator | `fix/noninf-colbert` | `f876d989` | colbert (PREFIX-1 web half) |
| epyc-orchestrator | `fix/noninf-seqb2` | `4c220b11` | seqb2 (SEQ-B2) |
| epyc-inference-research | `fix/noninf-tulving` | `dcb769c1` | tulving (M-12e) |
| epyc-root | `lane/noninf-20260914` | `baaa6741` | tulving (SC67 write side) + this wrap-up |
| epyc-orchestrator | `fix/noninf-erastamp` | `d03218fc` | erastamp (RTG-02) |
| epyc-inference-research | `fix/noninf-sw4-research` | `d28ab833` | sw4 (master registry — **must merge or the work has no effect**) |
| epyc-orchestrator | `fix/noninf-sw4` | `a1d36daf` | sw4 (regenerated lean view; overwritten by the next stack start if the master is not merged) |
| epyc-orchestrator | `fix/noninf-invlog` | `d65a4e93`, `b69bda61` | invlog (RTG-02 per-request tool telemetry + `assigned_role`/`work` on the update path) |
| epyc-inference-research | `fix/noninf-floorunit` | `eb8a88de` | floorunit (R23-55, INF-73 U2 floor `unit`) |
| — | — | none | inf40 (analysis only; no git writes) |

Merge notes carried from the fragments: `safety_gate.py` is touched by `fix/noninf-etr`,
`fix/noninf-seqb2` and `fix/noninf-erastamp` at disjoint hunks (`merge-tree` exit 0 for etr↔seqb2;
erastamp's hunks are adjacent to etr's, resolve in the order etr → erastamp). The sw4 research
worktree `/mnt/raid0/llm/worktrees/noninf-sw4-research` carries 9 untracked symlinks that exist only
to satisfy `check_evidence_durability.py`; remove the worktree with `git worktree remove` after the
merge.

## Follow-ups discovered (not fixed this session)

Consolidated list, grouped by owning handoff: [`2026-09-14-noninf-backlog-followups.md`](2026-09-14-noninf-backlog-followups.md).

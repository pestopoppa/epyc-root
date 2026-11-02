# Critical review of the operator's comments (2026-11-02)

Scope: the v5 amendment message (8 items), the second-pass review (`backlog-refactor-second-pass-audit-20261102.md`), and the measurement-sufficiency guide + audit README (lane copy `/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-ready-20261102/…`; **not on `origin/main` at the audited sha `3ac825873dfb` — `/workspace/docs/guides/agent-workflows/measurement-sufficiency.md` does not exist there**, so the OPERATING_CONSTRAINTS link is a lane fact until RTG-58 lands). Verdicts: agree / partially agree / disagree, with evidence and the consequence for the plan. Candid where warranted.

## A. The v5 amendment message

| # | comment | verdict | evidence and reasoning | consequence |
|---|---|---|---|---|
| 1a | EXP-01: drop the imported 2.793 % threshold; 3 launches/arm cannot set a floor; no final rejection | **agree** | `MEASUREMENT_POLICY.md:104-:111@3ac825873`: the 2.793 % is the *process-launch* sd of the serving instrument; `ik_llama.cpp` is a different instrument and a floor needs n ≥ 24. | Applied: pilot records observed spread only; EXPAND/REVISE/INCONCLUSIVE, never STOP. |
| 1b | EXP-04: no negative conclusion at 8K; resource = whole host + idle MI210 | **partially agree** | Correct that 8K cannot exclude 16K/32K (PF1 rule is "smallest L where…", `mi210-big-model…:235-:243`). But PF1's own text says "whole-host request max 24 h / min 4 h" for the *full* matrix; demanding the whole host for a 60-min *screen* makes the pilot compete with every CPU quarter row and the drain rule (`backlog-churn-flow.md` → quiet-host rows are drain-scheduled). **A0 only needs the production CPU shape, which is the whole host for Q38FN as served** — so the request is technically forced by identity, not by the pilot's size. | Applied as whole-host + idle MI210, but the pilot should be booked *inside* an already-granted quiet window (e.g. piggyback the first 60 min of a PF1-class or E5 window) rather than as its own drain; otherwise it will not be scheduled for weeks. Flagged as over-strict in effect, correct in principle. |
| 1c | EXP-09: four arms | **agree** | `tool-output-compression.md:552` + the second-pass §2 row list four arms (current summary, verified quote, deterministic shape header, pointer only); my v5 dropped one. | Restored. |
| 1d | CAP-04: separate sweeps cannot identify effort × budget; add a crossed cell or mark TB-4 uncovered; knee ≠ E-2/E-3; keep both denominators | **agree, with a cost caveat** | Interaction needs a factorial; `reasoning-effort-levels.md:116` says TB-4 "folds into E-2/E-6" and `:331` E-2 is on the pinned GPQA items — so the crossed cell belongs on GPQA. A 2 effort × 2 budget × 10-item cell at 32k budget on a ~10 t/s CPU model is ~40 generations × up to 32k tokens ≈ **up to 3–4 h worst case**, which breaks the ≤ 2 h pilot cap. | Added as a 2×2×10 *screen* with the cap raised to 2.5 h and an explicit "TB-4 UNCOVERED if dropped" clause; the operator should expect the crossed cell to be the first thing cut when the window is short. |
| 2 | Authorization parser: detect unresolved choices independently of approvals | **agree** — this was a real defect | `task_lint_v2.py:67` (v5) gated PENDING behind `not AUTH_ISSUED`; a box with "(operator 2026-10-25 authorized …) … the operator must choose between" was classified issued. | Fixed (`UNRESOLVED` checked first), 2 regression tests, 17/17 pass; pending choices **158** (was 134), executable 913. |
| 3 | EXL3: no partial native rows | **agree** | `exl3-cpu-mi210-implementation.md:142@3ac825873`: the 10-31 inventory "adds no rows, frames or grade"; the writer binds the run identity (`evidence.py write()` "identities from their digests"). My v5 "emit rows for the fields the copy carries" would have invented warrant — exactly what CLAUDE.md's belief-kernel rule forbids. | Reclassified as retained historical conclusions + prospective capture; `substitutes_run: False`. |
| 4 | E5: valid / demonstrated-invalid / unresolved-missing-evidence | **agree** | `batched-decode-measurement.md:852`: the Gemma C1b cells *demonstrate* straddling with `policy=none`; the other cells lack a cache-drop/policy witness, which is absence of proof, not proof of absence (CLAUDE.md → Observation Windows). | Applied as three dispositions. |
| 5 | Replays are CANDIDATES until coverage is established | **partially agree** | Correct for KPF (mixed) and C6 (unchanged predicates only). For STT and KB the retained banks are complete and already filed (`internal-kb-rag.md:1002` G11 R2 59/70 recorded; STT 5,536 validation files) — calling them "candidates" adds a review step before an analysis that is itself zero-inference. **Risk: "candidate" status can stall the deterministic tails the review itself puts first** if a session reads it as "do not start". | Applied, with coverage statements per replay and an explicit rule that candidate status never blocks starting the zero-inference analysis — only the *ticking* waits for coverage. |
| 6 | KEEP marker exists on `ws58-csh/` | **agree** | Observed on disk. | §7 wording refreshed; note that the marker covers the audit dir, not the 27 evidence paths. |
| 7 | Apply-time reconciliation against current task state | **agree, and it is the most important item** | RTG-58 advanced after the pin (audit README); `handoff-sessions.json` shows live Codex sessions. Migrating pinned unchecked state over a since-ticked box would re-schedule finished inference. | Added to the per-fold gate: re-parse the current file, three-way merge (pinned baseline, current, destination), never move a box that is ticked in current, never publish a row for it. |
| 8 | Integrate measurement-sufficiency guidance | **agree, with two conflicts noted below (C)** | — | Stop contract per package; pilot fields per the audit; EXP-01 owner transferred to INF-26 per the audit. |

## B. The second-pass review (§1–§7)

| item | verdict | evidence / reasoning |
|---|---|---|
| §1 nearby-text derivations are wrong | **agree** | `task_audit.py:49-:64` searched the section context; EvalPerf `architect-model-selection-bench.md:627` has no done clause of its own. Fixed in v4. |
| §1 classifications wrong (Q38 floor, TOC-SP-3/5, EvalPerf, scorer) | **agree** | Verified each at the pinned lines in v4. |
| §1 authorizations re-queued | **agree** | TD-23 `typed-decision-plane.md:600` quotes ruling Q1; CH-27 `:207` is a dated decision. |
| §1 `track_gate` substituted for prerequisites | **agree** | `task_audit.py:69-:70` did exactly that. |
| §1 numeric splits | **agree** | v3 `<id>.<n>` children had no deliverables. |
| §1 lint tags contract | **agree** | v1 lint had no modes. |
| §1 companions disagree (8,130/8,089) | **agree** | Reconciled: sha drift −59, parser +18. |
| §1 thesis stale | **agree** | `thesis…md:3` ACTIVE 2026-10-29. |
| §1 "a prior measured runtime cannot be mandatory" | **agree** | Circular for first experiments; provisional + pilot adopted. |
| §2 the 12 fusions | **agree on 11; partially on EXP-02** | EXP-02 lists AKX-AUTO-11 "registry checks" as a consumer, but `autokernel-all-devices…:129-:130` shows the floor-registry tests already ran in a granted window on 2026-10-22; what AKX-AUTO-11 still needs is the *landing* of `f8/floor-…`, a non-inference step. Consumer kept but its clause is "registry entries match the measured cells", not a measurement. |
| §3 the 8 captures | **agree** | — |
| §4 replays | **partially agree** | NEMO and HIL-16a were mis-stated in *my* v4, and the operator's v5 corrections were right; but the second-pass itself listed "HIL-16a: verify recordings offline" as open work when the handoff shows it done on 2026-10-24 (`harness-improvement-loop.md:158`). Internal inconsistency in the source list, now resolved. |
| §5 do-not-fuse limits | **agree** | — |
| §6 experiment manifest fields | **agree** | — |
| §7 order: deterministic tails → pilots → cells → folds | **agree, one practical disagreement** | Putting *file consolidation last* means the 63-file route-1a folds (which are readiness-neutral and zero-inference) wait behind pilots that need GPU/host windows. The folds and the deterministic tails do not compete for anything; serialising them is a schedule cost with no safety benefit. **Recommendation: run route-1a folds in parallel with step 4, not after step 6.** |

## C. Measurement-sufficiency guide and audit README

| point | verdict | evidence / reasoning |
|---|---|---|
| Guide: "stop as soon as valid evidence settles the scoped decision or a predeclared futility rule fires"; planned interim looks | **partially agree — a real tension with the constitution's gate rules** | `MEASUREMENT_POLICY.md:104-:111`: floors gate only at n ≥ 24 with a recorded unit; `OP-ABSEQ` (master index queue) still recommends **no** sequential paired e-process amendment; `OP-PQP`/`OP-ALPHAWIN` likewise. The guide says the constitution stays authoritative, so for *gate-class* cells interim looks can only stop for futility or an operational decision, never declare a gate early. That is consistent, but the guide's "Gate satisfied or failed … only when the protocol permits" line is doing all the work and is easy to miss. **Consequence**: every package's stop contract states "no early gate verdict"; the guide should say explicitly that until OP-ABSEQ/OP-PQP are decided, interim looks are futility-only for gates. |
| Guide: "Verify the harness writes usable incremental records … safe stop between units" | **agree** | Matches rowflow's first-unit PASS rule (`backlog-churn-flow.md`). |
| Audit: the 927 are structural candidates, not launch-ready; 761 is not a subset of 927 | **agree** | True by construction (classes vs executability); v6 states both. |
| Audit: EXP-01's KT gates to INF-26, tq3 as consumer | **agree** | `iqk-iquant-enablement.md:156-:157` holds T2/T3 with the ≥95 % tg128 rule; tq3 STEP 2/3 restate it. Applied. |
| Audit: EXP-04 8K pilot is a screen, not the gate | **agree** | Applied (no negative verdict). |
| Audit: CAP-04 generate at each budget; no silent reuse of lower-budget generations | **agree** | Applied; note this is what makes the crossed cell expensive (B.1d). |
| Audit: provisional status must not stop authorized reuse/adjudication/preparation | **agree** | Applied as a note in every stop contract. |
| Audit: journal paths share a parent marker | **agree** | `orchestration/` parent; KEEP list now names the two shards and says the parent marker's scope must be checked against the particular reaper rule (a parent KEEP protects children only if the reaper walks ancestors — `scratch_cleanup.py` does; `reap_idle_lanes.py` does not read KEEP at all). |
| Audit: "RTG-58 advanced subsequently" | **agree — this is the strongest argument for item A.7** | — |

## D. Things that are wrong, over-strict, inconsistent, or would block useful work (summary)

1. **Over-strict in effect**: EXP-04 whole-host for a 60-min screen (A.1b) — correct identity, impractical booking; piggyback a granted window.
2. **Cost not acknowledged**: CAP-04 crossed cell (A.1d) can exceed the pilot cap; TB-4 will likely be "uncovered" in practice.
3. **Could stall**: "replays are candidates" (A.5) if read as a start gate; it is a tick gate.
4. **Schedule cost**: §7's "consolidation last" (B.§7) serialises zero-inference folds behind GPU-window pilots.
5. **Doctrine gap**: the sufficiency guide's early-stopping language vs the undecided OP-ABSEQ/OP-PQP/OP-ALPHAWIN (C.1) — not a conflict in text, but a trap for a session that reads the guide without the constitution.
6. **Not on main**: the guide is cited as linked from OPERATING_CONSTRAINTS but lives only in the RTG-58 lane at the audited sha; folds that cite it must wait for that lane to land or cite the lane commit.
7. **Internal inconsistency in the source list**: HIL-16a listed as open replay work while the handoff records it done (B.§4).

# AutoKernel parallel loop — design (from the 2026-11-21 audit)

## Status / phases

- **Approved**: operator approved implementing the whole plan (P0..P6), 2026-11-21. Owner: pipeline-mgmt.
- **Program boxes**: `handoffs/active/churn-pipeline.md` → AKPL-P0 .. AKPL-P6 (one per phase, each with a brief).
- **Source**: audit `/mnt/raid0/llm/tmp/ak-parallel-loop-audit-20261121/REPORT.md` (read-only audit; copied
  below verbatim apart from this header).
- **Phase state** (update as phases land):
  - P0 instrument + estimate-from-history — code landed (2026-11-21): `tail_timing` RESULT export
    (`$AK_RESULT_JSON`, key `tail_path_timing_summary`), `scripts/coordination/rowflow/estimate_history.py`,
    default estimate in `row_scaffold.py`. Open on one clause: ≥30 iterations of stage timings need a loop run.
  - P1 gate evaluator — `scripts/kernel_rnd/autokernel/loop/gate_eval.py` (research repo); replay report
    [autokernel-parallel-loop-p1-replay.md](autokernel-parallel-loop-p1-replay.md).
  - P2..P6 — not started.
- **Hard limits that hold at every phase**: production kernels frozen, promotion operator-only, all scheduling
  through rowflow (no second keeper), main sessions remain the only row publishers.

---

# AutoKernel management session → parallel AutoKernel loop: audit (2026-11-21, read-only)

Sources: transcript `7b25c5ae-26b3-499f-bce1-07c4ba197b8c.jsonl` (2026-11-06 → 11-21, 56k lines, 1300 subagent
files; sampled, not read), loop code `epyc-inference-research/scripts/kernel_rnd/autokernel/loop/`, rowflow,
row-owner-loop skill, taskflow design docs. No contact with the session; nothing written outside this directory.

## 0. Shape of the session (numbers)

- 10,192 assistant turns over 16 days; 3,456 Bash, **523 Agent spawns, 514 SendMessage (all to its own subagents =
  continuing an agent instead of respawning)**, 197 Write, **46 Read**, 130 AskUserQuestion, 61 TaskStop.
- Model routing is explicit: sonnet 252 spawns (40 at `lower`), opus 158 (16 at `higher`), fable 4, haiku 1.
- Inbound: 530 subagent hand-backs, 182 cross-session messages (Pipeline Management / Inference Research), **309 genuine
  operator turns** (median ~12/day, peaks 62-63 on decision days), 23 context-continuations.
- The main thread almost never reads files or edits code itself (46 Read, 24 Edit in 16 days). It briefs, verifies,
  publishes rows, files verdicts, and asks decisions. That is the whole operating model.

## 1. Success factors, with evidence

| # | Factor | Evidence | Judgment (LLM) or protocol? |
|---|---|---|---|
| S1 | **Main thread = dispatcher/reviewer, never worker.** 523 spawns, 46 reads. Each brief is a self-contained contract: *finding → goal → numbered Do → hard rules → report shape*. | Briefs 11-18 20:56 (C14 r3 row prep), 11-10 14:12 (dense nondeterminism bisect), 11-09 14:26 (take 71 akx boxes) | Protocol. Brief template is already `brief.py` + HARD-RULES v1. |
| S2 | **Subagents prepare, owner publishes.** "Prepare two rows. Neither gets published by you." Rows are published, filed and ticked only by the main thread. Single-writer per surface. | 11-18 20:56 brief; `publish_row.py` and `file_result.py --filed-by autokernel` only in main Bash | Protocol (INVARIANTS single-writer). |
| S3 | **Versioned hard rules in every brief**: FROZEN production, no builds on quarters a row holds, no GPU outside a grant, `HIP_VISIBLE_DEVICES=-1`, no kill-by-name, literal write paths, no `--force/prune/gc`, pinned-file fingerprint rule, "if denied, stop and report". | 8 sampled rule blocks, identical wording across weeks | Protocol. Already codified as HARD-RULES v1; enforced by hooks. |
| S4 | **Every hand-back is verified before it is believed.** Patches re-tested ("the patch appears to break two tests... 7 failures against a baseline of 2"), fusions found "not actually getting" fired, corrections issued to the operator within minutes ("Two corrections to what I told you"). | 11-07 13:54, 11-15 19:28, 11-09 13:15 | Mixed: *what* to check is protocol (handback-checklist); *reading the result* is judgment. |
| S5 | **Zero-token watchers as the scheduler.** `while :; do find grants -name '*.ended' -newer $M ...; sleep 120` loops over grants/, dryrun/FAIL-*.json, filing-done/. "The watcher is armed again" is the closing line of most status turns. The keeper decides *when*; the session only reacts to `.ended`. | 12+ watcher commands sampled; 54 "watcher armed / meanwhile" hits | Protocol. `watch_rows.sh` exists. |
| S6 | **Never idle: publish ahead, overlap builds with gates.** "Building now means that when the C15 checks pass, the C16 GPU and CPU check rows can start straight away." Repeatability rows published "meanwhile" while big rows wait on the hold. Operator still caught idle compute once (11-09 10:32) → immediate root-cause (phantom hold / stale ready list) and rules saved. | 11-18 23:00, 11-19 01:37, 11-09 13:13 | Judgment to pick the filler; protocol to require one armed row per bin (skill §"Stock every bin"). |
| S7 | **Rows, not sessions, carry the measurement contract.** Every row has QUESTION/RULE/STOP, estimate, region shape, FUTILITY on missing input, rc 75 only on STOP, supersedes chain (`-r2 → -r3`), and cites prior rows' results instead of re-running them ("Skip tbo and KLD. Cite r2's tbo result"). | 11-18 20:56 brief; `c14-fold-gpu-20261118-r{2,3}` | Protocol (row_scaffold / lint). Reuse-valid-evidence is judgment today. |
| S8 | **Lineage bookkeeping as an explicit artifact.** A subagent maps "each keep, its commit, whether it's in C16, and the action. Forgotten keeps get a C17 fold box, one feature per commit with its test. C16 itself isn't touched, since it's mid-gate." Build on C14 while C15 gates; C16 rows held until C15 reports; C17 list accumulates. | 11-20 22:22, 11-18 23:00, 11-21 02:44 | Protocol: keep→fold-list→composite-build→gate is a DAG. Deciding *what* to drop is judgment. |
| S9 | **Decisions reach the operator as 3-option packages, recommended first**, 130 times; each unblocks exactly one item and work continues elsewhere. | 11-20 12:05 (dcp12 defer), 11-10 23:08 (iqk route), 11-18 23:41 (DS41 park) | Protocol (decision-package contract). |
| S10 | **Learning is persisted immediately**: "behaviour rules saved to memory: publish ready rows immediately, no local load during quiet grants, 45-second smokes, one publish at a time"; a running hand-back ledger so re-spawned wrap-up agents lose nothing; "harvest" subagents mine other sessions' commits into AK boxes. | 11-09 11:30, 11-20 20:04, 11-07 20:39 | Protocol (ledger, harvest) — content is judgment. |
| S11 | **Defects are routed, not absorbed.** Keeper/rowflow bugs go to Pipeline Management as classified lists with artifacts (AK-FAILRULE-1: 1,262 verdicts classified into harness vs candidate failures); the session keeps measuring. | 11-06 20:06, 11-09 11:30 | Protocol (classification) once categories exist. |
| S12 | **Operator in the loop at the right altitude**: ~12 real turns/day, mostly rulings (27B-anchored gate, C14 fold, holds) and "is anything happening?" probes. The session translates each ruling into a gate constant the same day. | 11-18 20:56 (ruling → gate rule), 11-09 10:32 | Judgment (operator). |

Separation: S1-S3, S5, S7, S9 are pure protocol and already partly codified (row-owner-loop, HARD-RULES v1, keeper).
S4, S6, S8, S10, S11 are protocol *shells* with a judgment *core* (verify a claim, pick a filler, decide a fold).
Only S12 and the candidate-level reasoning (what to try next, why a result is noise) are irreducibly strong judgment.

## 2. What blocks the serial loop, and a parallel shape

Current loop (`loop.py:3-11`, `pipeline.py:13-20`): planner (gpt-5.6-sol via codex) → critic (Fable) ≤3 rounds →
author → critic ≤2 rounds, **concurrently across ≤7 lanes** (`DEFAULT_WORKERS` pipeline.py:76), then ONE locked
**tail**: build, op oracle, gates, A/B n≥5, commit (`loop.py:2080-2235`, `SerializedTail` pipeline.py:163).
So "serial planner → drafter → measurement" is already half-false: formation is parallel; **the tail is the serial
bottleneck**, and it is 100% deterministic work. Measured cost: run 11 spent 15.8% of time on device
(pipeline.py:5-11); run 27 saw 54-71% GPU idle (actors.py:257). Stalls:

1. **Build + oracle + gate + timing + commit share one lock** although only the quiet timing window and the
   compare-and-swap commit need exclusivity. Builds (64 of 88 lane cores) could overlap gates of another candidate.
   Already filed as AK-TAIL-SPLIT (autokernel-loop.md:5771) with a DESIGN.md, gated on ≥30 iterations of
   `tail_timing` data — a gate that itself waits for a campaign that waits for the launch hold.
2. **Supersession is discovered under the lock** (pipeline.py:32-38): a lane whose base moved learns it only when it
   finally gets the tail, then its hypothesis is redrawn. Cheap rebase-and-retest is not attempted.
3. **The loop owns compute monolithically**: it runs inside one keeper GPU hold (`claim.py:402,469-499`) and
   measures in-process; it never publishes per-candidate rows. The keeper therefore cannot interleave AK gates with
   other sessions' rows or pack CPU-only gates (KLD/PPL on quarters) while the GPU times something else.
4. **Drain only between formation stages** (loop.py:1108-1113): a stop request waits for the whole tail.
5. **Champion fold to the C-series is manual** (hand-made `llama.cpp-experimental-c14-fa-fold-*` branches); keeps
   compound on `ak/champion/llama-cpp-ffc1bac82eec` (champion.py:56) but the fold list / DO-NOT-FOLD ledger /
   Spec-D re-check (akx-program.md:489-508) are prose boxes the management session drives by hand.

### Parallel loop (reusing rowflow + taskflow)

- **N candidate lanes** (keep `pool.py` worktrees): planner/critic/author as today, but a lane's output is a
  *candidate record* (base sha, patch sha, hypothesis id, predicted effect) — not a tail entry.
- **Shared row queue via rowflow**: each candidate becomes a *chain* of epyc.row.v3 rows with `lineage=<cand>`,
  `supersedes`, and a `gate:` dependency, scaffolded by code: `build` (cpu, any quarter, class diagnostic) →
  `oracle+kld` (cpu or gpu quiet-only, correctness) → `ab-timing` (block-timing-quiet, gpu or quarter) → `fold-check`.
  The keeper packs them like any other row: quiet rows first, builds before dependents, GPU timing holds 88-95.
  The AK campaign stops being one hold and becomes many small rows that other sessions' rows interleave with.
- **Deterministic gates** already exist as code (`graph_kld_policy.json`: 27B KLD ≤0.003, |dPPL| ≤0.5%, Q38FN
  top-1 ≥93%; PPL contract floor 0.98 gates.py:3244; speed floors bench.py:63-79). Wrap them as a *gate evaluator*
  that reads a row's RESULT.json and writes verdict.json (PASS/FAIL/NOISE/FUTILITY) with the gate id and thresholds
  — no LLM.
- **Champion-fold step**: a KEEP verdict triggers `advance_champion` (compare-and-swap, pool.py:270-293). Lanes
  whose base is stale get an automatic *rebase-and-recheck* row (oracle only; timing rerun only if the diff
  touches the measured path) rather than a redraw.
- **Merge/lineage manager**: a small ledger (keep sha, hypothesis, gate results, in-champion?, in-C-fold?,
  DO-NOT-FOLD?) replacing the hand-driven "map each keep against C16" subagent. Emits the fold list for the next
  composite (one feature per commit + its test, the V6R-4b rule) and the presence-gate manifest.
- **Packing onto the keeper**: builds are CPU quarters (not q3 when GPU timing runs — host-thread rule), KLD/PPL
  on CPU quarters or GPU quiet-only, timing on the GPU with 88-95 held. Keep one armed row per bin ahead; use
  `priority_rank` so a champion-fold check outranks exploration; `max_window_s`/`resumable` so a 30-min build
  can be killed and resumed by the keeper rather than block a quiet grant.
- **Promotion stays operator-only**: nothing above touches `production-consolidated-v10`; the manager stops at
  "C-next candidate built + presence gate + ratify package drafted".

## 3. Distillation estimate

| Workflow element (as the session does it) | Class | Component to build |
|---|---|---|
| Brief rendering with hard rules, report shape | deterministic | `brief.py` (exists); add row-chain brief templates |
| Row scaffold, estimate, lint, publish, prove queued | deterministic | `row_scaffold.py` (exists) + **row-chain scaffolder** (build→oracle→timing→fold-check from one candidate record) |
| Estimate_s | deterministic | **estimate-from-history**: per `unit_key` runtime percentiles from past `.ended`/RESULT, ×1.25; flag >1.5× overrun |
| Watch `.ended` / FAIL / filing-done, re-arm | deterministic | `watch_rows.sh` (exists); make it emit taskflow `kind=file` events |
| Triage run end → verdict | deterministic for gated rows | **gate evaluator** (KLD/PPL/top-1/speed floor → verdict.json); `runend.py` for the rest |
| Supersede / republish `-rN` when a gate rule or cap changes | deterministic | **auto-republish-on-cap**: successor row with `supersedes`, cited prior evidence, changed clause only |
| File verdict, tick box with belief tag, register row | deterministic | `file_result.py`, `done_when.py` (exist); wire from evaluator |
| Keep → champion CAS, stale-lane rebase row | deterministic | `advance_champion` (exists) + **rebase-and-recheck emitter** |
| Keep ledger, fold list, presence manifest, DO-NOT-FOLD | deterministic | **lineage/fold manager** |
| Classify failures harness vs candidate (AK-FAILRULE-1 taxonomy) | cheap model (or rules once taxonomy stable) | failure classifier over RESULT/launcher.out |
| Verify hand-back claims (branch contains sha, ready/ exists, tests ran) | deterministic for the checklist; cheap model to read diffs | **handback verifier** running `handback-checklist.md` mechanically |
| Choose filler to keep bins stocked | cheap model over a ranked backlog | taskflow `select.py` (exists, deterministic) |
| Decide noise vs regression on ambiguous cells; attribute a bisect | strong judgment | stays LLM (critic tier) |
| Hypothesis generation / patch authoring / fold-drop decisions | strong judgment | planner/author/critic as today |
| Operator decision packages | strong judgment to write; deterministic to detect the need (`gate:` unresolved, hold hit) | **decision-needed detector** → AskUserQuestion |

Estimate: by turn count, ≈60% of the session's effective work (watching, scaffolding, publishing, filing, ticking,
republishing, lineage bookkeeping, status reports, brief boilerplate) is deterministic-codifiable; ≈15% is cheap-model
(failure classification, hand-back reading, filler choice); ≈25% is strong judgment (operator rulings, noise calls,
fold decisions, candidate ideas). For the *loop* itself, the tail is 100% deterministic today and the only reason an
LLM touches a measurement is to read it — the gate evaluator removes that.

## 4. Staged plan

- **P0 — Instrument, no behaviour change.** Run `tail_timing` on the next granted campaign; export per-stage
  durations and lock-wait to RESULT. Build **estimate-from-history** from existing `.ended`/RESULT files.
  *Done when:* ≥30 iterations of stage timings and a per-`unit_key` estimate table exist and `row_scaffold.py`
  can consume it (AK-TAIL-SPLIT GO/NO-GO data is a by-product).
- **P1 — Gate evaluator + verdict filer.** Pure function RESULT.json + `graph_kld_policy.json` + bench floors →
  verdict.json; wire to `watch_rows.sh`/taskflow `kind=file`. Replays all filed AK verdicts since 11-06 and must
  reproduce the human verdicts (differences are either bugs or recorded rule changes).
  *Done when:* replay agreement ≥95% with every disagreement explained; new rows file with zero LLM turns.
- **P2 — Row-chain scaffolder + auto-republish.** One candidate record → build/oracle/timing/fold-check rows with
  `lineage`, `supersedes`, `gate:` deps; successor emitter on cap/rule change. Uses `row_scaffold.py`, `publish_row.py`.
  *Done when:* a management-session candidate (e.g. a C17 fold check) is driven end to end by the chain with the
  owner only approving the publish.
- **P3 — Tail split (AK-TAIL-SPLIT) via rowflow.** The loop stops measuring in-process: lanes emit candidate records,
  the chain scaffolder publishes rows, the keeper packs them; only `advance_champion` CAS and the quiet timing row
  are exclusive. Stale-lane rebase-and-recheck replaces redraw. Keep `--workers 1` legacy path for rollback.
  *Done when:* two candidates are in build/gate concurrently while a third times on the GPU; device-busy fraction
  rises above the run-11 baseline (15.8%) on a measured campaign; no keep lands on a base it was not built from.
- **P4 — Lineage/fold manager.** Keep ledger, fold list (one feature per commit + test), presence manifest,
  DO-NOT-FOLD, Spec-D re-check rows auto-scaffolded. Replaces the hand-driven C16/C17 mapping subagents.
  *Done when:* the C-next fold list and presence gate are generated, not written, and the manager refuses a fold
  missing a test (DS41-C116 gate).
- **P5 — Hand-back verifier + failure classifier.** Mechanical `handback-checklist.md`; AK-FAILRULE-1 taxonomy
  as rules with a cheap-model fallback; harness failures auto-routed to the pipeline inbox.
  *Done when:* every subagent hand-back carries a machine VERIFIED/UNVERIFIED stamp and harness failures no longer
  consume a main-thread turn.
- **P6 — Decision-needed detector.** Unresolved `gate:`/hold/cap → draft 3-option package for the owner to send.
  *Done when:* each AskUserQuestion in a week traces to a detector event. Promotion remains outside scope:
  the pipeline ends at a ratify package the operator signs (kernel-promotion skill).

Constraints honoured: production tree untouched at every stage; promotion operator-only; all scheduling through
rowflow (no second keeper); dispatch through taskflow lanes; main sessions remain the only row publishers.

---
Notes for the caller: (a) `/workspace/agents/autokernel.md` does not exist and `/workspace/scripts/kernel_rnd/autokernel/loop` is an empty stub — the loop lives only in the research repo; (b) taskflow docs/code are not in the /workspace checkout (found in worktree `.worktrees/ak-corr-20261121`), so the plan's taskflow references assume origin/main; (c) the loop has no "drafter" role in code — the stage is called "author"."}
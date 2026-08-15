# 2026-08-15 — research-intake: MEGA + Phantom Guardrails cohort, SOL-ExecBench gate closed, gfx90a datapath settled

**Session type**: interactive (no roster lane worktree; operated directly on `main` in `/workspace`,
the shared clone — `scripts/coordination/check_lane_worktree.py --strict` exits **3**). No roster id
assigned; filed under `research-intake`, same convention as `2026-08-13-research-intake.md`.

**Mid-flight wrap-up.** A GPU benchmark owned by a parallel session ran throughout (PID 3568603,
`llama-server` on `Qwen3.8-27B-Q8_0`, ROCm0, started 19:37:35Z) and was not touched. A CPU-side
quant ladder of this session's own is still in flight — see *Still in flight* below.

## Problem

Operator submitted two arXiv papers — **MEGA** (`arXiv:2608.10504`, self-evolving agent optimization
via a Wisdom Graph) and **Phantom Guardrails** (`arXiv:2607.13083`, self-improving harnesses that
fabricate the failures they then "fix") — and asked for the full four-stage intake. A second,
unrelated gate had been open since 2026-08-11: intake-1102/1103 (SOL-ExecBench ROCm port + its
NVIDIA upstream) were awaiting dive selection and had been carried, untouched, across two sessions.

## What happened, by stage

**Stage 1** — 2 submitted + 10 expansion sources. Unbounded dedup sweep over all 1,123 pre-existing
entries: **0 collisions**; neither arXiv id appeared anywhere in the file, including inside
`referenced_arxiv_ids`. Expansion cap (10) reached.

**Stage 2 / 2b** — 6 operator-selected dives, then 8 more sources ingested-and-dived uncapped.
Final cohort **intake-1128…1147 = 20 entries**, of which **14 carry claim anchors** (i.e. were
dive-verified or dive-overturned), **114 claim anchors** and **63 per-claim corrections** in total.
One dive-overturned outright (intake-1131: fails the job it was filed for, novelty high→low);
intake-1139's headline 66.56 was shown **absent from its own source**.

**Stage 3** — plan mode, operator-approved 2026-08-15. Plan file:
`/home/node/.claude/plans/enumerated-scribbling-aho.md`.

**Stage 4** — applied as `6d783fbd`. Deliberately **0 new handoffs and 0 new index rows**: the filed
work promotes instruments we already have from advisory to enforcing rather than building new ones.

**Prior-session gate, closed the same day** — dived intake-1102/1103 (`f825adae`), then filed the
follow-ons (`1511267c`). Verdict on the SOL-ExecBench ROCm port's eleven reward-hacking checks:
they **pass** the documented-but-unimplemented test — every check raises, every one is wired to a
live call site, detection is fail-closed at the record level. Apache-2.0, and every mechanism we
want from it is architecture-independent.

## The findings that are the actual output

- **EV-10a already existed.** The per-task regression gate that four separate dives converged on was
  already built — decision logic 2026-05-27, default-off live-branch wiring 2026-06-13 (`924ca50`).
  Filing it would have re-proposed finished work; it was recorded as *evidence only, no new task*.
  (Precise state: EV-10a is still `- [ ]` because deploy/restart + paired-mutation A/B validation
  remain, tracked as K-SKILL-1 in `bulk-inference-campaign.md`. "Already existed" is about the
  mechanism, not the checkbox.)
- **Nothing in this literature requires an accepted edit to cite the failure it fixes** — zero of
  five sources — and neither do we. Verified in source: `SafetyGate.check()`
  (`epyc-orchestrator/scripts/autopilot/safety_gate.py:1591`) receives an `EvalResult` plus bare
  identifier strings; **it never sees the mutation payload**, so it structurally cannot require a
  warrant. Filed as SG-W2 (telemetry, explicitly NOT a gate).
- **`quality_measured` is computed and never read** — latent defect. Computed at
  `eval_tower.py:5170`, declared at `safety_gate.py:565`; grep over `autopilot.py`,
  `experiment_journal.py` and `src/` returns **zero** readers, and neither `check()` nor
  `update_tier()` consults it. Placeholder results therefore enter the gate as a literal 0.0 score,
  and it is an unrelated guard (`RELIABILITY_FLOOR = 0.8`) that happens to save them. Filed as ETR-2.
- **The baseline reaches the journal only as free prose** — `safety_gate.py:1759/1765` formats
  `"… vs baseline {baseline_q:.3f}"` into `failure_analysis` — and a regex already exists to parse it
  back out (`experiment_journal.py:99`, `_BASELINE_QUALITY_RE`). Filed as EV-14e: record the pin
  inside the trial record, beside the delta.
- **Both failure classes leave the quality denominator.** `eval_tower.py:5129` is
  `scored_results = [r for r in results if not r.error]`, so agent-caused and platform-caused
  failures are dropped alike — a config that crashes more gets a *smaller* denominator and is not
  penalised for it. Filed as ETR-1 (decide whether agent-caused should score 0).
- **SOL-ExecBench: "no measured constants for gfx90a" is NOT "unusable on gfx90a."** Compilation and
  correctness checking run on the MI210 **today**; only SOL *scoring* needs the constant port. And
  the bounds we do have are uneven: **four of eight C5 seeds are vacuous** (k154 506×, k227 3,690×,
  k225 5,710×, k228 36,837×) against k215 at a usable 6.8×. Filed as C5-4 — stop quoting `S` where
  it is meaningless.
- **gfx90a low-precision datapath, settled at ISA level** (zero GPU, zero inference). All 39 MFMA
  mnemonics assembled under `llvm-mc` across gfx908/gfx90a/gfx942, re-run against a second
  toolchain: **gfx90a has 27 MFMA instructions and FP16 and INT8 have identical shape sets**, so
  int8 MFMA is **1× fp16 (both 181.0), not 2×** — routing a quantized GEMM through int8 MFMA here
  has zero peak-rate advantage. No FP8 (`fp8-insts` absent), no xf32, no sparse; **INT4 has no
  matrix path on any CDNA generation** (zero `i4` mnemonics; it is VALU `v_dot8_i32_i4` only).
  Decode sits **31–113× below the ridge**, so MFMA decode kernels are worth exactly zero. The
  low-quant gap is therefore **VALU bit-unpacking and occupancy**, which is what the 2026-08-12
  disassembly diff independently found. New benchmarking trap recorded: Composable Kernel does not
  refuse fp8 on gfx90a, it **silently lowers each fp8 MFMA into 8 sequential fp32 ops**, so a "CK
  fp8 GEMM on MI210" measures fp32 emulation, not a datapath.
  - **Recorded as a LATENT exposure, at operator emphasis — not as "not a problem."** Nothing in
    production is exposed to the VALU penalty *yet*, because no IQ-format role is GPU-resident. That
    flips the moment one is. A tripwire with an explicit reopen condition is filed in
    `mi210-q8-dequant-gemv-roofline.md` (see below) precisely so this does not get closed by mistake.

## Changes made

| Repo | Files | What |
|---|---|---|
| epyc-root | `research/intake_index.yaml` | +20 entries (intake-1128…1147), 114 claim anchors, 63 claim_corrections; intake-1102/1103 rewritten to `verification: dive-verified`, `integration_disposition: knowledge_only` |
| epyc-root | `handoffs/active/eval-tower-verification.md` | +7 tasks EV-14a, 14b, **14b′**, 14c–14f (resolution band, blocking decision, candidate/baseline asymmetry, baseline last-write-wins, case-count assertion, in-record baseline pin, known-null corpus) + an EV-10a corroboration block filed as evidence only |
| epyc-root | `handoffs/active/canonical-judge-suite-revamp.md` | +8 tasks CJ-6a…CJ-6h |
| epyc-root | `handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md` | +3 tasks ETR-1/2/3 |
| epyc-root | `handoffs/active/safetygate-rlvr-provenance-audit-2026-07-22.md` | +3 tasks SG-W1/W2/W3 — **see the collision under Deferred work** |
| epyc-root | `handoffs/active/autopilot-continuous-optimization.md` | +3 tasks P17.BT-5a/5b/5c |
| epyc-root | `handoffs/active/routing-intelligence.md` | record-only note (harness selection as a routing dimension, intake-1140); 0 checkboxes, deliberately |
| epyc-root | `handoffs/active/agentic-rocm-kernel-authoring.md` | +3 tasks C5-3/4/5 (gfx90a correctness oracle, seed bound-quality classification, kNNN↔slug persistence) |
| epyc-root | `handoffs/active/rocm-verify-profile-backend.md` | +3 tasks, reward-integrity imports (phase-detection case, capture-and-replay case, stream fence/join for the non-syncing timing loop) |
| epyc-root | `handoffs/active/vidya-belief-substrate-program.md`, `scripts/vidya/adapters/README.md` | SC37 + adapter source-table row — the eval-tower resolution band's **write side, filed before the producer exists** |
| epyc-root | `wiki/hardware-optimization.md` | CDNA2 int8 line disambiguated, vendor citations added (it carried none, marked `[D]`), ISA verification + the CK-fp8 trap |
| epyc-root | `handoffs/active/master-handoff-index.md` | generated rollup regenerated twice |

### Landed at wrap-up (this file's own commit)

| File | What |
|---|---|
| `handoffs/active/rocm-verify-profile-backend.md` | **Defect fix**: the three new tasks were filed as RVP-C6-8/9/10, colliding with three *already-completed* `[x]` tasks of the same names in the same file (~lines 802/903/911). Renumbered **RVP-C6-11/12/13** with an ID note; any pre-2026-08-15 reference to C6-8/9/10 still means the completed ones |
| `handoffs/active/agentic-rocm-kernel-authoring.md` | **C5-5 premise correction**: a `c5_seed_corpus.json` with all eight seeds and a populated `slug` field already exists — but only inside two throwaway `tmp/` verification snapshots. `git ls-files` finds none in either repo. The mapping is not missing, it is *unpersisted*; land the file under version control first |
| `handoffs/active/mi210-q8-dequant-gemv-roofline.md` | +1 `[x]` (the ISA-level datapath settlement, ✅ 2026-08-15) and +1 `[ ]` **TRIPWIRE** with an explicit reopen condition: any registry change that makes an IQ1/IQ2/IQ3/IQ4 GGUF resident on ROCm0 in a serving role |
| `.research-session.json` | Two stale gates corrected: `prior_session_gate` still said intake-1102/1103 were "STILL OPEN … untouched by this session" (written 12:18Z, invalidated by the 12:47Z dive); `operator_surface` still said the EV-14a belief-kernel wiring was deliberately withheld, which SC37 superseded at 12:25Z |

## Verification

- **Checkbox accounting**, scoped to this session's range `25987e71..HEAD` plus the working tree:
  - `git diff 25987e71..HEAD -- handoffs/ | grep -cE '^\+\s*[-*] \[ \]'` → **31** new open tasks
    (24 from `6d783fbd`, 6 from `1511267c`, 1 from `13babe98`).
  - `- [x]` flips in those commits → **0**, and that is correct, not a miss: a targeted sweep for
    pre-existing boxes satisfied by this session's work found **none** in any category — no box
    tracked the intake-1102/1103 dive (it lived only in a JSON gate field), none tracked the wiki
    CDNA2 ambiguity (the correction closed an *undocumented* defect), and intake stage tracking is
    not checkbox-shaped at all. The nearest call, `autokernel-research-loop.md:3636` ("seed external
    kernel-authoring suites only after license, gfx90a, honest baseline, quarantine and
    evaluator-integrity gates pass"), had **two** of its five gates cleared by the dive and stays
    correctly open — it gates an action, not a finding.
  - Wrap-up commit adds **1 `[x]`** (ISA settlement) and **1 `[ ]`** (tripwire). Session total:
    **1 flip, 32 new open tasks.**
- **Commit message vs reality**: `6d783fbd` says "24 task lines"; the raw count is indeed 24, but the
  per-handoff breakdown in its own message sums to 23. The 24th line is `EV-14b′`, which the
  breakdown does not name. Total right, enumeration off by one — recorded here rather than amended.
- `python3 scripts/handoffs/index_state.py --check` → **0 problem(s)**, exit **0**, when run at the
  start of this wrap-up. Re-run at the end it exits **1** with **2 problems**, both of them caused by
  a handoff a parallel session created at 20:00Z while this wrap-up was in progress:
  `ORPHAN: loop-owned-fleet-implementation.md has no index row` and the consequent
  `FRESHNESS: master index generated block is stale`. **The regen was deliberately not committed.**
  Running `index_state.py` does fix both, but it auto-files an `RTG-52` row in
  `routing-and-optimization-index.md` pointing at a file that is still **untracked** — committing
  that publishes a dangling handoff link on `main`, which is itself a `--check` failure. The
  generated block is left exactly as `27cbc7fc` wrote it, one open task short of the working tree
  (this wrap-up's tripwire). Owner of the fix: whoever commits `loop-owned-fleet-implementation.md`,
  in the same commit.
- `python3 .claude/skills/project-wiki/scripts/check_readme_freshness.py` → exit **0**, no warnings.
- `bash scripts/validate/validate_intake.sh` → exit 0 (during Stage 4, per the stage gate record).
- Index ownership re-audited: `agentic-rocm-kernel-authoring`, `rocm-verify-profile-backend` and
  `vidya-belief-substrate-program` are each owned by **exactly one** domain index row (INF-03,
  INF-48, EVL-47). Zero double-ownership fleet-wide.

## Still in flight (not deferred — running now)

**Single-model GPU quant ladder, Goedel-Code-Prover-8B**, CPU-side, operator-authorized; the GPU
window waits on the parallel session's benchmark finishing.

- Three rungs built from the f16 source with `llama-quantize … 64` and **no** imatrix:
  **Q6_K** 6.26 GB (12 s), **Q5_K_M** 5.45 GB (12 s), **IQ4_XS** 4.28 GB (26 s), all rc=0.
- **IQ2_XXS hard-requires an imatrix** — the probe failed fast and produced no artifact. An imatrix
  was therefore built and **completed rc=0 at 20:02:15Z** (`llama-imatrix`, wikitext2_test 1.23 MB,
  40 chunks, `-t 64 -ngl 0`, 5.35 MB output at
  `/mnt/raid0/llm/tmp/quant-ladder/goedel8b.imatrix`). Note it writes GGUF-format imatrix with a
  non-`.gguf` suffix; `--output-format dat` is the legacy form if a consumer needs it.
- Disk is the live constraint: raid0 at **98%**, ~100 GB free, with three rungs already occupying
  ~16 GB of it.

**This ladder is owned by no handoff.** `tq3-quantization-evaluation.md` contains zero mentions of
Goedel; the only Goedel ownership anywhere is `non-inference-backlog.md` NIB2-15, **closed
2026-06-13**, covering f16/Q4_K_M/Q8_0 artifact generation only — no ladder, no IQ formats, no
imatrix. The IQ2_XXS-needs-an-imatrix precondition is recorded **nowhere** in `handoffs/active/`.
Filing a new stub needs operator approval, so it is recorded here and surfaced in the wrap-up report
rather than filed unilaterally.

## Deferred work — with named blockers

1. **`safetygate-rlvr-provenance-audit-2026-07-22.md` was archived upstream while this session added
   three open tasks to it.** `origin/main` has `git mv`'d the handoff to `handoffs/completed/` and
   deleted its EVL-40 index row, on the (then-true) basis "all 9 boxes closed". This session's
   `6d783fbd` added SG-W1/W2/W3 to the **active** copy, so the handoff is no longer complete —
   upstream's completed copy has **0** open boxes and **0** SG-W lines. A naive merge resolves this
   as rename-plus-modify and would silently file three live tasks inside `handoffs/completed/`.
   **Blocker**: this is another session's archival decision, and reverting it from a wrap-up is
   exactly the cross-session sweep the pathspec rule exists to prevent. **Recommendation**: restore
   the handoff to `handoffs/active/` with SG-W1/W2/W3 open and re-add EVL-40 to
   `research-evaluation-index.md` — the archive premise is simply no longer true.
2. **Wiki compilation (wrap-up Step 5) not run.** `compile_sources.py` reports **`total_new = 25`**,
   but 22 of those are *other sessions'* handoffs, and `wiki/source_manifest.json` is currently
   **dirty in a parallel session's working tree**. Compiling a subset and then `--touch`ing the
   shared watermark would move it past sources nobody wrote pages for — the exact silent loss the
   step warns about. **Blocker**: the parallel session's uncommitted manifest. Per
   `wrap-up-division-of-labor-policy.md` (operator, 2026-08-13) the wiki is the **auditor's** wrap-up
   step at its own cadence, so this is that owner's, not this session's, to run.
3. **Push rejected and promotion BLOCKED — this is fleet-level, not this session's to resolve.**
   Measured, not assumed:
   - `git push --dry-run origin main` → `! [rejected] main -> main (non-fast-forward)`.
   - The shared clone's `main` carries **34 unpushed commits** and is **109 behind** `origin/main`.
     Only 8 of the 34 are this session's; the rest belong to at least five other sessions
     (`coordinator-agent`, the RTG-51 handoff work, `docs`/AutoKernel, `dashboard`, `fix`).
   - The promotion was attempted the sanctioned way — an isolated detached worktree on `origin/main`,
     which never touches the live tree — and **conflicted in 9 files**: `dashboard/static/kernel.html`,
     `handoffs/active/autokernel-research-loop.md`, `inference-research-index.md`,
     `master-handoff-index.md`, `routing-and-optimization-index.md`,
     `wrap-up-division-of-labor-policy.md` (add/add), `progress/2026-08/2026-08-13-root.md`,
     `scripts/coordination/session_bus_coordinator.py`, `scripts/vidya/adapters/README.md`.
     `merge --abort` was run, the worktree removed with `worktree remove --force` (never `prune`),
     and `origin/main` is untouched.
   - The merge also confirmed hazard (1) empirically: git rename-detected the archived handoff and
     reported `Auto-merging handoffs/completed/safetygate-rlvr-provenance-audit-2026-07-22.md` — i.e.
     an unattended merge really would have filed SG-W1/W2/W3 inside `handoffs/completed/`.
   - In-place merge in `/workspace` is separately impossible: the incoming set touches
     `dashboard/README.md`, `dashboard/server.py` and `dashboard/static/kernel.html`, all of which a
     parallel session holds **uncommitted** here.
   **Blocker**: a 34-commit multi-session backlog on the shared clone's `main` needs one owner to
   reconcile against 109 upstream commits. Never force-pushed; nothing was auto-resolved.

Nothing else. No item recurs from a prior wrap-up under an unchanged blocker.

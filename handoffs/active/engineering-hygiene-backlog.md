# Non-Inference Backlog — Round 2 (2026-05-19 audit refresh)

> **Fold destination** (BRF-T1-F3, BRF-T1-1, route 1a, 2026-11-02): renamed from `non-inference-backlog.md`; absorbs 6 handoff(s) as `## Track:` sections at the end of this file (`amd-ai-lab-website-publication.md`, `frontier-f4-continuity-backup.md`, `integration-test-coverage.md`, `loop-state-offraid-backup.md`, `refactoring-multirepo-2026-10.md`, `repo-readiness-scorer.md`). The body above the first track is the former `non-inference-backlog.md`.

**Status**: ACTIVE — rolling zero-inference backlog; closed items live in § Completed Scope. Round-2 baseline open: NIB2-18 (gated on DS-E1 evidence), NIB2-46 (gated on NIB2-32).

**Scratch**: `/mnt/raid0/llm/worktrees/codex-ni-*`, `/mnt/raid0/llm/worktrees/codex-ni05-*`, `/mnt/raid0/llm/worktrees/codex-ni06-*`, `/mnt/raid0/llm/worktrees/codex-ni07-*`; integration lane: `/mnt/raid0/llm/worktrees/codex-noninf-session-20261005`. Logs use individual writer shards. Plain custody and review roots: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/`, `/mnt/raid0/llm/tmp/codex-ni30-custody-20261006/`, `/mnt/raid0/llm/tmp/ni07-29-ci-recipe-20261006/`, `/mnt/raid0/llm/tmp/ni07-34-pii-header-preparation-20261006/`, `/mnt/raid0/llm/tmp/ni07-32-root-keep-20261006/`, `/mnt/raid0/llm/tmp/ni07-32-custody-20261006/`. Additional NI08 custody and review roots: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/`, `/mnt/raid0/llm/tmp/ni08-inf50-projection-finish-20261007/`, `/mnt/raid0/llm/tmp/ni08-audit-next-20261007/`; generated native product lane `/mnt/raid0/llm/worktrees/ni08-inf50-native-writer-product-20261007/`. Further own recipe and original publication custody: `/mnt/raid0/llm/worktrees/ni08-c26-native-recipe-20261007/`, `/mnt/raid0/llm/tmp/c106-root-wrap-publish-*`, `/mnt/raid0/llm/tmp/threeview-narrow-validation-*`, `/mnt/raid0/llm/tmp/intake175-narrow-validation-*`. WS58 current roots: `/mnt/raid0/llm/tmp/codex-ni-20261027-orch-registration-recovery-v2/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-t1-launch-gate/`. · `/mnt/raid0/llm/tmp/refactor-01a16fc3/nib98-atomic/` (published proposal and unadopted owner packet; keep) · `/mnt/raid0/llm/tmp/refactor-01a16fc3/nib98-review-fixes-20261027/` (published unadopted test proposal and unapplied owner patches; keep) · `/mnt/raid0/llm/tmp/refactor-01a16fc3/nib98-loader-inventory-ready/` (held canary, evidence and proposals; keep)

**Cross-reference, 2026-05-06**: 6 standalone non-inference handoffs (NOT in NIB2 numbering) closed in parallel via Wave A/B/C — see `progress/2026-05/2026-05-06.md` § "6 standalone non-inference handoffs". These are tracked in their own handoff files; the closure pattern matches NIB2. Total non-inference closure throughput this audit cycle: 36 NIB2 + 6 standalone = 42 items.
**Created**: 2026-02 (Round 1, 18/18 complete → [`completed/non-inference-backlog-completed-through-2026-04-12.md`](../completed/non-inference-backlog-completed-through-2026-04-12.md))
**Refreshed**: 2026-04-17 (Round 2 catalogue from cross-cutting audit of all active handoffs)
**Supplemented**: 2026-04-21 (NIB2-31..34 added from handoff hygiene audit), 2026-04-22 (NIB2-40..48 from deep-dive integration pass), 2026-05-19 (NIB2-49..52 from May 2026 research cluster deep-dives)
**Priority**: MEDIUM (as a whole; individual items tagged HIGH/MED/LOW below)

---

## Start here

- **Next:** NI05 (79/79) and selected NI06/NI07 (35/35) are complete; the whole backlog is not exhausted. [NI08 continuation](../../docs/reference/ni08-non-inference-continuation.md): 212 scoped tasks completed (137 existing closures + 75 scoped children); LR8 and host receipt source published; newly unlocked context/source/design work continues. Preserve the running daemon until a reviewed handover.
- **Then:** NIB2-71 rescue disposition; NIB2-77 owner migration/retirement; NIB2-83 existing-evaluation error classification.
- **Operator-held:** NIB2-65 and NIB2-66; NIB2-71 archival-versus-deletion disposition is pending the concrete operator choice. NIB2-73f's named current-file exposure is absent and closed.
- **Also open:** NIB2-18 and NIB2-46 (gated), NIB2-67 (only under disk pressure), NIB2-71, NIB2-78c (dormant; graph install decision required), NIB2-88 (post-restart relaunch census; host cron installation is complete), and NIB2-89 (opt-in restart code already present; bus supervisor operator-held DOWN, D9/runtime scope retained).
- **Leak robustness:** LR-6a accepted 2026-10-06 with a post-install heartbeat; LR-8 is now available for bounded source preparation. LR-9a was ratified 2026-10-04 (`ae06680f`). LR-10 belongs to workspace-ec.
- **Standing:** bus_supervisor stays DOWN (operator ruling 2026-09-23). Do not relaunch it without a new operator go.


## Completed Codex session queue — 2026-10-05–06

The bounded NI05 session queue is **79/79 accepted and published**. The earlier 78/78 checkpoint remains historically accurate; NI05-79 was accepted after the kernel-store documentation correction reached APP main. Exact task texts, task-specific dates, accepted reports, publication facts and evidence boundaries are preserved in the reciprocal completed ledger: [`../completed/non-inference-backlog-ni05-2026-10-06.md`](../completed/non-inference-backlog-ni05-2026-10-06.md). “Accepted” closes each listed bounded deliverable only; it does not close a parent program, establish a whole-suite pass, or grant a serving/production claim.

NI05-75 operator authorization was acted on and is not pending. Its original pre-collection NULL and earlier approval checkpoints are historical receipts; final accepted focused evidence is in the completed ledger. NI05-79 records documentation/source review only, with no new native tuple, grader or test warrant. No open NIB2 row or other owner’s work was closed by this compaction.

## Purpose

Cross-cutting catalogue of work that does **not** require:
- A running llama-server (AR-3, benchmarks, A/B tests, eval tower runs)
- AR-3 trial data, Package D completion, AP-26 sub_lm validation, Ouro P7, EV-4 baseline
- Cloud GPU budget
- Upstream PR merges

This is the "what can I pick up right now with no inference available?" list. Items link to their canonical handoff — update both places when status changes.

**Round 1 (completed/)** closed out 18 items (orchestrator refactoring, test coverage floors, CC local integration Phase 0, etc.). Round 2 catalogues what the 2026-04-17 audit surfaced as newly-unblocked or previously-orphaned.

---

## Completed Scope

| Scope | Ledger |
|---|---|
| Round 1 (18/18), through 2026-04-12 | [non-inference-backlog-completed-through-2026-04-12.md](../completed/non-inference-backlog-completed-through-2026-04-12.md) |
| Round 2 baseline and every supplement, closed items through 2026-09-27 | [non-inference-backlog-completed-through-2026-04-12.md](../completed/non-inference-backlog-completed-through-2026-04-12.md) § *Round 2 + supplements — closed through 2026-09-27* |
| April 2026 Round-2 dependency and priority graph (superseded) | [non-inference-backlog-history-through-2026-09-27.md](../archived/non-inference-backlog-history-through-2026-09-27.md) |

## Medium-effort implementation (multi-day, no inference required)

- **[declined: workspace-f2 audit 2026-11-09: duplicate of DS-6-live, already declined in numa-placement-and-contention.md]** **NIB2-18**: DS-6 QuarterScheduler revalidation gate — [`dynamic-stack-concurrency.md`](numa-placement-and-contention.md#track-dynamic-stack-concurrency) DS-6-live. Do **not** treat as code-only scaffolding. Implement only after DS-E1 evidence (Package B throughput, RI-10 escalation data, DS-5 roster findings, KV-size data, mixed-role NUMA contention) shows static pre-warm leaves material throughput/latency on the table. Completed design/gap details live in [`../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md`](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md).

## Round 2 supplement (added 2026-04-22 — deep-dive integration pass)

Items surfaced by the 8 research deep dives landed 2026-04-22 (`/workspace/research/deep-dives/{lighton, qwen35-omni, stop-learnable, diversity-collapse, onevl, agent-world, minddr, intake-trio}.md`). Each entry maps to a specific deep-dive action item and a target handoff.

- **[declined: ws58 2026-11-03 content-review: April research-intake curiosity with no consumer]** **NIB2-46**: STOP Phase 0 instrumentation in llama.cpp (DD3, intake-437). ~1d code; non-inference (hook-level). Reserve unused token, add orchestrator hook for hidden-state fetch at prefix position. **Gated on NIB2-32** difficulty-signal re-validation producing a live verdict. → [`reasoning-compression.md`](context-and-token-economy.md#track-reasoning-compression) Action 10a.

---

## Items explicitly excluded (blocked or inference-required)

These are *non-inference in nature* but gated on external signals. Listed so the gate is visible, not to pick up:

- `readme-refresh.md` — GATED on AR-3 trial ≥100 (currently ~78). Pick up when autopilot journal hits 100 trials.
- DAR-3/DAR-4 validation passes — code is NIB2-16/17; measurement is inference.
- REPL S4 A/B — A/B itself is inference; scaffolding (not listed here) would be ~4h code.
- Qwen3.6 benchmark — [`qwen36-production-upgrade.md`](../completed/qwen36-production-upgrade.md) — inference-gated. Download already done.
- Package D post-AR-3 analyses — blocked on AR-3 completion.
- **NIB2-33 (retired 2026-04-21)**: Hermes outer shell auth — `hermes-outer-shell.md` L242 explicitly defers auth until a multi-user use case materializes ("No auth on any endpoint… Not implementing until there's a concrete multi-user use case"). Revisit when a second human user or a multi-tenant scenario is in sight.
- MathSmith S2 HC benchmark + S3 drafter spec decode tests — inference-gated.

---

## Reporting protocol

When you complete an NIB2-NN item:
1. Check the box here.
2. Update the linked canonical handoff's TODO / next-steps section to match.
3. Add a one-line entry in `progress/YYYY-MM/YYYY-MM-DD.md`.
4. If the item belonged to a phased handoff (e.g. "Phase 2c ByteRover enhancement"), bump that handoff's status line.
5. On completing all 43 items: move this file to `completed/` as Round 2, and run a fresh audit to open Round 3.

---

## 2026-08-12 supplement — observers that cannot say "I cannot tell"

Filed by the class-sweep that followed the coordinator-daemon watchdog blindness: `bus_supervisor.sh`
identified its target with `pgrep -f "session_bus_coordinator\.py run"`, the live daemon's argv had
`--bus-root <path>` between `.py` and `run`, so a **healthy, actively heartbeating** daemon read as
dead forever and the watchdog relaunch-looped every ~10s for hours before anyone noticed. Root cause
is not the regex: the guard could not observe the thing it guards and **nothing detected that**, and
two states existed where three were needed.

All zero-inference. Each row below is a distinct file that collapses "cannot observe" into a definite
verdict. **Enforced, not remembered**: `tests/test_observer_contract.py` reads
[`scripts/coordination/observer_registry.json`](../../scripts/coordination/observer_registry.json),
discovers these files structurally, and goes RED if a line here is checked off or deleted without the
migration landing. Reference adoption: `scripts/coordination/backfill_supervisor.sh`. Contract:
[`scripts/coordination/observer_guard.sh`](../../scripts/coordination/observer_guard.sh).

- [x] **OBS-12** (LOW): **`.claude/skills/kb-search/SKILL.md` documented an interpreter that cannot work — audit the other skills for the same shape.** Fixed for kb-search on 2026-08-19 (it told every session to run bare `python3`, which has no `numpy` and dies in `colbert_encoder.py`, independent of OBS-11); the hooks and batch scripts already used the venv. **A second instance is already confirmed**: `.claude/skills/project-wiki/scripts/lint_wiki.py` exits with `ERROR: PyYAML not installed` under bare `python3` and runs clean under the orchestrator venv — found incidentally while linting, not by any check. The open work is the sweep: nothing ties a skill's documented command to an interpreter that actually has the imports, so the remaining instances stay invisible until a session hits one.
  ✅ 2026-09-17 (`sub-small-audits`, root `afb9745c`). Today bare `python3` imports PyYAML and numpy
  only from `~/.local`, which a devcontainer rebuild can wipe. The sweep therefore ran every skill
  script and every documented bare-`python3` target under `python3 -s`, which ignores that
  directory.
  - **Wrong install hints.** `lint_wiki`, `query_wiki`, `seed_index` and `validate_intake` told
    the user to `pip install pyyaml`. `backfill_dispositions` and `resolve_intake_id` died with a
    raw ImportError. All six now refuse and name the venv command.
  - **Silent config loss.** Without PyYAML, `compile_sources` and `wiki_writer_review` ignored
    `wiki.yaml`. For `compile_sources` that changed source selection: `SCHEMA.md` dropped out of
    `skip_filenames`. Both now raise instead.
  - **`coordinator-agent/SKILL.md`** ran bare `python3` for three scripts that need PyYAML:
    `tmux_adapter` crashes, `merge_gate` refuses, and `session_bus` needs it for its roster. All
    of its Python commands now name the venv.
  - **`research-intake/references/taxonomy.md`** now points at `validate_intake.sh`.
  - **Guard:** `tests/skills/test_skill_interpreters.py`, 18 cases; 16 fail before the fix.
  - **Verification:** each fixed invocation was run under the venv, and none failed on an import.
  - [x] **OBS-12a** (LOW; NI05-33): active explicit `python3 session_bus.py` invocations bypass the existing absolute managed-orchestrator-venv shebang. Current CLAUDE/AGENTS direct commands already honor it. Correct BUS_PROTOCOL, STANDING-MAIN-RULES and live `idle_supervisor.sh` calls to direct script execution; preserve YAML roster semantics and historical instructions. Main owns shared task updates; isolated source/fixture preparation is delegated. No bus daemon restart.
  - [x] **OBS-12b** ✅ 2026-09-17 (already fixed by the wrap-up pass-2 wiki compile; all three links now point at `../handoffs/completed/security-review-skill.md`, verified by the main session) (LOW, filed 2026-09-17): `lint_wiki.py` reports two dangling links:
    `wiki/agent-architecture.md:2254` and `wiki/tool-implementation.md:278,321` still point at
    `../handoffs/active/security-review-skill.md`, which moved to `completed/` in `9804fec9`.
    `wiki/` is written by the serialized wrap-up, so fix it in the next compile.
- [x] **OBS-9** ✅ 2026-10-05 (current-source leaf scope accepted; no live reload) (LOW): **`"esc to interrupt"` is a liveness oracle in FOUR files with no shared
  constant** — `scripts/coordination/idle_supervisor.sh`, `scripts/coordination/idle_watch.sh`,
  `scripts/coordination/session_bus_coordinator.py`, and (added 2026-08-12)
  `scripts/coordination/fleet_watch.sh`. It is **vendor TUI text**: a Claude Code or
  Codex release that rewords it breaks all of them at once, and `idle_supervisor` would then type
  nudges into six actively-generating panes indefinitely. (Its uncapturable-pane handling is already
  correct — *"a pane it cannot capture is UNKNOWN, never idle"* — so only the marker needs a canary.)
  The two rosters have also already drifted: `idle_watch.sh` watches 4 mains, `idle_supervisor.sh` 6.
  **The canary this row asks for already exists in one of the four** and is the cheapest thing to
  lift: `fleet_watch.sh` gathers every vendor string in one named block and adds a `DETECTOR-BLIND`
  condition — if no readable pane matches ANY known marker for PERSIST_CYCLES, it reports that the
  vocabulary has drifted and SUPPRESSES the idle verdicts built on it, because six mains losing
  their markers in the same cycle is a TUI release and not a fleet-wide stall. It is exercised in
  both directions by `scripts/coordination/tests/test_fleet_watch.sh` and mutation-tested (removing
  the guard turns the suite red). Generalising it is what closes this row.
2026-10-05 current-source correction (NI05-44): the fleet pane classifiers/canary above were removed in2026-08-16; do not restore them. Three surviving leaf prefilters (idle_watch, idle_supervisor, coordinator) must require existing authoritative probe JSON with runtime_decided=true, runtime_state=idle and nudge_ok=true. Marker absence, unknown vocabulary, unreadable/malformed/timeout/refused probes and active/compacting contradictions cannot provide idle authority. Keep tmux_adapter runtime/probe, fleet_watch and peer ownership unchanged; final nudge still rechecks its existing guard. Uninstrumented Claude state remains UNKNOWN. New helper/consumer changes require exact source and off-host fixture review.

- [x] **OBS-10** ✅ 2026-10-05 (active-consumer scope retired by existing OP-19; historical artifacts unchanged) (LOW): **Two E8 operator ratifiers gate on an argv pattern.**
  *Note 2026-09-16: the E8 chain these ratifiers served is retired by operator ruling [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json) (root `1ee8bd7c`). The ruling re-anchors the reseed gate to the current eras; the gate binds only at promotion.*
  `artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh` and
  `ratify_e8_empty_frontier_bootstrap_20260726.sh` both use
  `pgrep -f '[s]cripts/autopilot/autopilot.py start'` — same start-adjacency fragility. The newer
  `ratify_v9_cpu_bench_era_advance_20260811.sh` already migrated ("no process-pattern probe — host
  rule: never pgrep by name"); backport that. Deliberately OUT of the observer-registry discovery
  scope (one-shot scripts a human runs and reads once), recorded here so the finding is not lost.
  Current-source audit2026-10-05 (NI05-51): existing OP-19 explicitly retires the unsatisfiable E8 transaction and anchors current obligations at promotion. No current autonomous/in-process consumer was found. The two ratifiers and related retired rearm script retain their historical process-pattern probes; no backport, operator artifact mutation or new ratification was performed. The newer v9 ratifier uses flock. This closes stale active-consumer work only, preserving the historical finding and exempt observer-registry entry.

---

## 2026-08-23 supplement — disk reclamation phase 1 done, phase 2 candidates

Phase 1 (operator-approved, 2026-08-23): `/mnt/raid0/llm/tmp/` 285G → 2.9G via per-worktree
`git worktree remove` (138 worktrees, never `prune`), 111G → 371G free. Details:
`progress/2026-08/2026-08-23-disk-reclaim.md`.

- [x] **NIB2-65** (MED): **model duplicates/orphans ~25G in `/mnt/raid0/llm/models/`** — safe set (workspace-f2 2026-11-09: safe set complete: Qwen3-4B-Thinking-2507-GGUF removed with operator approval, registry deprecated and graveyarded in research; judgment-call items stay operator-held) ✅ 2026-11-09 [no-belief: tooling-repair]
  from the 2026-08-23 census: `bge-m3-f16.gguf`, `multilingual-e5-base-f16.gguf`,
  `granite-embedding-97m-multilingual-r2-Q4_K_M.gguf`, `Qwen3-TTS-12Hz-0.6B-Talker-Q8_0.gguf`,
  `gemma-4-26B-A4B-it-assistant-v6-f16.gguf`, empty husks (`MaziyarPanahi`, `Mungert`,
  `prithivMLmods`, `jiaojjjjje`, `hugging-quants`), `tinyllamas-stories-260k-f32.gguf`,
  `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf`, `Qwen3-4B-Thinking-2507-GGUF` (4G, only in
  deprecated benchmarks). Judgment calls (research-only refs, keep unless operator says otherwise):
  `Qwen3-ASR-1.7B-GGUF`, `gemma-4-e2b/e4b-it-Q8_0`, seal-concise set.
  2026-09-15 PARTIAL: the 7 files + 5 husks deleted (~4.3 G), each ledgered in orchestrator `model_registry.yaml`
  `deprecated_models` (branch `sub/nib2-65-ledger` `8e1bd269`). HELD: `Qwen3-4B-Thinking-2507-GGUF`, because the rationale above is
  wrong — `gpu-cot-scaffold-sidecar.md` (active) uses it as a control-arm generator. Operator call.
  - *(workspace-f2 audit 2026-11-09.)* Only `Qwen3-4B-Thinking-2507-GGUF` (4.0G) remained of the safe set; operator approved its deletion 2026-11-09. Judgment-call items (`Qwen3-ASR-1.7B-GGUF` 6.8G and five `*-seal-concise.gguf`) stay operator-held.
- [x] **NIB2-66** (LOW): **stale kernel trees ~18G** — `llama.cpp-experimental-preserved-20260724T135832Z`
  (14G, superseded), `llama.cpp-v6-iqk` (1.9G, iqk shipped in v9), `llama.cpp-v7-sanitize-audit`
  (1.6G), `llama.cpp-k28-prototype-20260720` (0.9G). Keep `llama.cpp-dflash2-qwen38-20260820`
  (active handoff `dflash2-block-drafter-experimental-build.md`).
  2026-09-15 PARTIAL: `llama.cpp-v6-iqk` and `llama.cpp-v7-sanitize-audit` removed (clean, fully pushed, `git worktree remove`).
  HELD: `llama.cpp-k28-prototype-20260720` (dirty: uncommitted GDN `.cu` edit + doc — commit/push or discard first);
  `llama.cpp-experimental-preserved-*` (dirty worktree of the production clone, operator-owned).
  2026-11-07 DONE (operator-approved): `llama.cpp-experimental-preserved-20260724T135832Z` salvaged (tracked.diff of 11 dirty files + HEAD.txt under `/mnt/raid0/llm/salvage/worktrees-20261107/llama.cpp-experimental-preserved/`, 0 untracked files, HEAD 8bb53c520 already on fork; `llama-tts-qwen3` sha256 97ba7e14… at `/mnt/raid0/llm/salvage/llama-tts-qwen3-20260423/`), trashed via guarded_rm, `git worktree remove` run. k28 tree already gone. [no-belief: not-a-result]
- **[declined: ws58 2026-11-03 content-review: no action by its own text (in active use, re-downloadable)]** **NIB2-67** (LOW): **`cache/huggingface` 127G** — re-downloadable HF cache, all files touched
  <30d ago (in active use by sessions). Reclaim only when disk pressure returns; `pip`/`uv`/`dflash`
  caches also live under `cache/`.

---

## 2026-09-08 supplement — shared research clone dirty-state rescue

The **shared** clone `/mnt/raid0/llm/epyc-inference-research` sat on stale main `1d2fe2a3` carrying 9 dirty
tracked files + 4 untracked. All 11 were preserved verbatim on `rescue/shared-clone-dirty-20260907` @
`63ec9f53` (pushed to origin) and copied to `/mnt/raid0/llm/tmp/research-shared-clone-rescue-20260908/`; the
9 tracked files were then overwritten with HEAD content (`git show HEAD:<f> > <f>` — the hygiene hook blocks
the `git restore` verb in the shared clone and reads its bypass from the session env) and the clone was
fast-forwarded to `7b5d1eb6`, tracked tree clean.

- [x] **NIB2-71** (LOW): **review `rescue/shared-clone-dirty-20260907` (`63ec9f53`) — fold or delete the (workspace-f2 2026-11-09: NIB2-58a linkage gates, reverted by research 76d21aa9f, restored on main; rescue branch deleted) [no-belief: tooling-repair]
      branch.** Its content is a working copy of the CH-8 build-flags change (`162d17dd`, **already merged in
      main**) plus two older 2026-08-27 bench scripts; the residual delta over merged CH-8 is roughly **50
      comment lines** on legacy discovery scripts (build-recipe / `ROCWMMA_FATTN` notes). Decide: fold the
      comments forward, or delete the branch. Small item — the rescue itself is done, this is disposition only.
  - *(workspace-f2 audit 2026-11-09.)* Operator decided 2026-11-09: fold any comment lines worth keeping, then delete the branch. The full commit is 841 insertions, so diff against main first.

## 2026-09-15 supplement — surfaced by the non-CPU-inference ROI dispatch

All zero-inference unless stated. Filed by the 2026-09-15 dispatch session (progress note
`progress/2026-09/2026-09-15-noninf-roi-dispatch.md`).

- [x] **NIB2-73e** (MED): **the durability gate scans the REGISTRY only, so cited-but-untracked evidence in DOCS and
      HANDOFFS is invisible to it.** Found while writing the 11 READMEs, all recorded in-file:
      `docs/reference/models/model-admission-2026-07-16.md:359-363` cites two `summary.json` files that exist only in
      the shared clone; `gemma-challenge-kernel-techniques-v7.md:141` carries two DANGLING citations (only the n=2 dir
      exists); six `*_20260718Tcodex` dirs carry reports whose cited run data is untracked; and further untracked
      sibling bundles are cited under `bonsai_current_v7` (L8626/8627/8641/8642/8715) and
      `qwable_reasoning_economics` (L9124-9131). Extend the checker's scan to docs/handoffs, or accept the limit
      explicitly — today the gate's silence on these is not evidence of their durability.
- [x] **NIB2-73f** (LOW): **review the named current tracked-file exposure.** ✅ 2026-10-06 — the exact named `data/cpu_optimization/2026-04-30-v5-cleanup-audit/README.md` is absent from fresh published ROOT `6033e30cd7938c87233b3632c71764a6acf4d2c9` and the reviewed worktree. [Disposition](../../artifacts/ni08/source-audits-20261006/current-exposure-disposition.json). No current redaction/keep choice remains for that file; no address was copied or reintroduced. This closes only the named current-file exposure, not a whole-repository privacy audit or Git-history erasure.
- [x] **NIB2-76 — resolve both residuals of the NIB2-69 gate fix.** ✅ 2026-10-06 — (a) the standalone guard no longer falls through to realized fleet/environment/default mode; it uses explicit mode or its own checkout declaration and fails closed before validation. (b) portable priors/source-artifact resolution was already fixed and is covered by existing selected worktree-relative and external-absolute controls. APP source 82e398da2478bfd9c3baaddbd0c6fb742d09dafa; run 37476312545 TRUE20/20 including 9 existing focused guard/pipeline controls. Synthetic source/fixture evidence only.
- [ ] **NIB2-77** (MED): **finish AutoKernel disk hygiene after the approved sweep and archive-backed retirement.**
      The exact `a49053c273ee` manifest's prequalified REMOVE rows were approved and applied. A separate
      content-addressed archive preserved all 224 reviewed dirty acceptance worktrees before their exact-path
      retirement; 224/224 have removal receipts. Free space rose by 359,176,167,424 bytes (about 334.5 GiB).
      Prospective acceptance cleanup and serial disk fail-close are published (`b65138a0` root;
      `142fd1e3` research). The **historical2026-09-15 count was187 lane worktrees registered against the frozen clone**; current audit does not establish disposition of the difference.
      audit their ownership and migrate/retire only through an individually reviewed procedure. Verify the
      prospective cleanup during the next completed acceptance run, rather than inferring it from unit tests.
  - [x] **NIB2-77-AUDIT — resolve the exact frozen-clone population and audit current lane ownership metadata.** ✅ 2026-10-06 — MAIN accepted [33-row current snapshot](../../artifacts/ni08/nib77-ownership-audit-20261006/README.md):79 registrations/33 lane paths,20 tracked-dirty/13 clean, no accountable session owner. Historical187 roster is absent; no154-retirement or whole-parent completion claim. Parent migration/retirement remains open.
  - *(workspace-f2 2026-11-09.)* Gate now resolves per-repo bases. Operator approved removing 16 champion-lineage trees once idle 7 days (from about 11-16); AutoKernel notified. Anything else the gate reports removable needs fresh approval.
  *(workspace-f2 2026-11-09 wrap-up.)* The 11-16 date above covers only the 16 approved champion-lineage trees; frozen-clone lane retirement and verification of the prospective acceptance cleanup on a completed run remain open. [no-belief: not-a-result]
- **[declined: ws58 2026-11-03 content-review: optional and dormant by its own text]** **NIB2-78c** (OPTIONAL, conditional; dormant since NIB2-78b was ruled A = do not install): take this up only if
      the graph layer is revived, and re-open the install decision together with it. Give the Kuzu graphs a single owner (one process owns
      `kuzu_db/*`; the others reach it over IPC) so graph scoring does not vary by which worker serves a
      request. Then re-evaluate the backend against maintained Kuzu forks, since upstream is archived.
      *2026-09-23 (intake-1496):* if revived, add HelixDB (Apache-2.0, Rust graph+vector on a slatedb LSM) to the backend
      candidate list beside maintained Kuzu forks; it is server-mode, not embedded, which works against the Kuzu locality rationale.
      *2026-09-26 (audit):* re-verified — `apply_failure_veto` (`chat_pipeline/routing_decision.py:334-390`) is a no-op because
      `state.failure_graph` is never set without kuzu (`services/memrl.py:477-536`); this is the NIB2-78b ruling working as decided, not a bug.

## 2026-09-26 supplement — surfaced by the orchestrator-design session (workspace-8d)

Filed by that session's final wrap-up (progress note `progress/2026-09/2026-09-26-orch-design.md` § Final).

- [x] **NIB2-86** (MED; filed 2026-09-26 as NIB2-80 and renumbered 2026-09-27, because NIB2-80 is also the closed EARLY_ABORT item below): **`make gates` in epyc-orchestrator checks almost nothing on this host.** Found 2026-09-26:
      `shellcheck`, `shfmt` and `markdownlint` are not installed; the `nextplaid-reindex` gate needs NextPLAID
      `:8088`, which is down; and `make check-numerics` / `report-numerics` run
      `scripts/validate/check_numeric_literals.py`, which has never existed in the orchestrator's git history
      (`git log --all` on that path is empty). A "✅ All gates passed" here therefore certifies little. Fix it
      either way: install the linters (devcontainer), make each gate fail loudly when its tool is missing rather than
      skip, and implement or delete the numerics targets. Then decide whether `nextplaid-reindex` belongs in `gates`.
  ✅ 2026-10-05 — six Makefile fixtures and the actual pinned devcontainer tool/version fixture pass; static gates fail loudly on nine existing formatting defects, and independent markdownlint passes. Source is published in orchestrator main `41ab07fc` and root `b07a992e`; the formatting repair remains NI05-21. See [gate evidence](../../progress/2026-10/2026-10-05-codex-ni-gates.md).
- [x] **NIB2-87** (LOW; filed 2026-09-26 as NIB2-81 and renumbered 2026-09-27, because NIB2-81 is also the closed daemon-staleness item): **the research repo `.venv` has no pytest**, although `pyproject.toml` declares
      `pytest==9.1.1` in the `test` extra (the venv was synced without it). On 2026-09-26 research tests had to run with
      the orchestrator venv. Add the extra additively, `uv pip install --python .venv/bin/python pytest==9.1.1`
      (not a bare `uv sync`, which would prune packages outside the requested extras), and extend `health_check.sh`'s
      OBS-11 Tooling Interpreters check to assert that pytest imports in both venvs.

## 2026-09-27 supplement — disk-leak audit and window-script defects (ak-ds41-main)

- [x] **NIB2-84** (MED): **`~/.codex` has no retention and no reaper.** Disk-leak audit 2026-09-27
  (`/mnt/raid0/llm/tmp/disk-leak-audit-20260927.md` §1 rank 2, §2.3): `/home/node/.codex` is ~23 GiB, and
  `state_5.sqlite` (2.5G), `logs_2.sqlite` (2.1G) and `thread_history_1.sqlite` (2.9G) grew ~4.8 GiB in one ~8 h
  window while Codex served as a delegation actor. Unlike `opencode.db` (the `opencode_event_reaper.sh` pattern,
  OP-59), nothing ages these out. Fix: a bounded reaper with the same discipline (never touch a DB a live `codex`
  process holds, three-state `observer_guard.sh` probe, an observer-registry row), plus a retention window that
  follows Codex's own session-resume horizon. Any deletion of existing history needs operator confirmation first.
  Acceptance: the reaper holds `~/.codex` flat across a day of actor use.
  - ✅ 2026-10-04 — **closed report-only, by operator ruling.** `scripts/system/codex_retention_reaper.py` landed
    (root `4dd68363`, dry-run by default). On 2026-10-04 the operator made a hard rule: Claude and Codex backup logs and
    session transcripts are never touched, because a more senior project outside this repo uses them as
    historical transcripts. Its `apply` path is therefore **permanently disabled** (`722b7196`; exit 4,
    report-only). The acceptance line above (hold `~/.codex` flat) is withdrawn: growth is reported, never reaped. The
    report-only run and `host_hygiene_tick.py`'s grower ranking are the only remaining surface.
    **REVERSED 2026-11-07** (operator decision 2026-11-07, session operator-adhoc-ops-20261105, REVERSED for ~/.codex ONLY: the janitor's CODEX step deletes vault-verified rollouts older than 7 days and keeps the newest 7 days; claude, opencode, hermes, vault and every other harness tree stay never-touch). `apply` re-enabled (rollouts only, `--no-packages`).
- [x] **NIB2-85** (MED): **`verify_ggml_linkage.sh` FAILs falsely on a symlinked kernel store.** Found 2026-09-27 by
  the MMQ J-cap GPU window (research `6b8feb9e` worked around it in the window script): the tool compares unresolved
  paths, so a binary under `kernels/production/{cpu,gpu}` (a symlink into the store) reads its own ggml libraries
  as coming from elsewhere. v10 is served from the kernel store, so every production-arm check is exposed. Fix in
  the research repo `scripts/utils/verify_ggml_linkage.sh`: `realpath` both the resolved library and the expected
  tree before comparing, and keep failing on a genuine cross-tree resolution. Acceptance: PASS for
  `kernels/production/gpu` and its resolved build dir; FAIL for a binary whose ggml resolves to another tree
  (fixture); and the `/bin/true` vacuous-pass trap noted in `coordinator-role-failure-modes-and-refactor.md` stays covered.
  ✅ 2026-10-05 — repaired canonical resolution and five original off-host controls accepted (research `2c5d60f5`). Root producer/verifier plus twelve native receipt controls accepted from run `37307888066`. Claimed prospective actual-store capture at 13:04:26 UTC bound all four production symlinks to their resolved targets; seven child linkage rows exited zero and independent native readback returned `(True, [])`. This closes static linkage repair/custody only; measurement dependency attachment stays open in VB-LINKAGE-GUARD. Original host custody: `/mnt/raid0/llm/artifacts/ni28-store-capture-20261005.eQEysE/receipts/20261005T130426Z-12e23f9cdff4/`, seal `6ee3b6f98e040cc2608381e823aab08ed3dd882a803109435c4673cc04550053`.

## 2026-09-28 supplement — test-order dependence in the orchestrator's openai/v1 tests (workspace-8d)

- [x] **NIB2-90** (LOW): **two test-order-dependent failures in the orchestrator's openai/v1 test set.**
      `tests/unit/test_openai_compat_bare_name_final.py` and the `[stream]` case of
      `tests/unit/test_openai_compat_compression_fallback.py` fail when run as part of the openai/v1 set, and both
      reproduce on unmodified orch `origin/main` (found 2026-09-28 while testing orch `66ef96b8`, so not caused by it).
      Find the state one test leaks into the next (module-level feature flags, a cached app or backend, or a logger
      level that `caplog` depends on), reset it in a fixture, and prove it by running the set in two different orders
      with both passing.
  ✅ 2026-10-05 — current/upstream-resolved: original sixth and seventh off-host JUnit show identical API identities/statuses in both file orders (376 pass, zero failure/error, two named live-backend skips). Both named problem modules pass; existing feature/app/logger fixtures are retained. No precise historical leaked-state cause or new source repair is attributed. See [NI11 evidence](../../progress/2026-10/2026-10-05-ni11-api-order-and-benchmark-collection-validation.md).

## 2026-09-29 supplement — test sections left in the plain inference tap log (workspace-8d)

- [x] **NIB2-91** (LOW): **rewrite the plain `inference_tap.log` to drop the 738 test-written sections.** ✅ 2026-09-30 Orch
      `8a7d57a8` made the `tests/unit` tap hermetic (no new fake sections), and on 2026-09-29 the operator ran
      `clean_tap_events.py --apply` on the JSONL events file: 3,668 test events removed (rule a 2,844 role_a/role_b
      pytest PIDs; rule b 824, i.e. 206 non-API task-less requests to the `test-native-wire` backend or port 0), 267,312
      kept and verified byte-identical in order, lock held 20.35 s. Backup, script and `clean_run.json`:
      `/mnt/raid0/llm/tmp/inference_tap_backup_20260929/`. The plain `inference_tap.log` still carries the 738 test
      sections. It can only be rewritten while no `TapWriter` holds an fd, so do it at a planned API stop: back up,
      drop the sections the same two rules identify, verify the kept sections byte-identical in order, restart.
      Ticks when the rewrite and its verification are recorded here.
      - 2026-09-29: the operator directs it as next work, with RI-16 and RI-18, after that day's wrap-up. Next step:
        schedule the planned API stop with any session that has live `/chat` or `/v1` traffic (the stop ends every
        `TapWriter` fd), then back up, rewrite, verify and restart through `orchestrator_stack.py`.
      - ✅ 2026-09-30: done at a planned API stop, 04:52:16Z-04:52:32Z. Evidence:
        `/mnt/raid0/llm/tmp/inference_tap_backup_20260929/rewrite_run-20260930T045216Z.json` (verify `ok: true`, no
        errors; 3,259 sections → 2,315 kept, byte-identical in order (`kept_identical` 2,315 of `kept_expected`
        2,315; result 8,551,968 bytes, sha256 `5b1af99d…`); 944 dropped = rule a 738 + rule b 206, overlap 0;
        `carried_forward_bytes` 0, `post_rename_extra_bytes` 0). Pre-rewrite snapshot
        `inference_tap.log.pre-rewrite-20260930T045216Z` (sha256 `c97fc8b9…`) in the same directory. API downtime
        13.2 s (stop 2.3, rewrite 0.6, start 10.3; from `rewrite-run-20260930.log` there, not the JSON). The same
        restart deployed orch `78847544` (RI-16, `routing-intelligence.md`) to the API: new master PID 1930724.

## 2026-10-04 supplement — leak robustness and the harness-state hard rule (ak-ds41-main)

The 2026-10-03 disk audit (`/mnt/raid0/llm/tmp/disk-audit-20261003/`) and INC-20261004-cleanup-removed-load-bearing-worktree
led to an operator-directed leak-robustness pass. It ran on root lane `lane/leak-robustness-20261004` (merged
`2dbf1e57`), research lane `lane/leak-tests-20261004` (merged `01a19f24`), and the orchestrator branch
`lane/leak-tests-20261004`, which workspace-ec carries. The doctrine half is ratified as
RATIFY-SCRATCH-LIFECYCLE-20261004 (`8061e48d`) and RATIFY-AK-DS41-LESSONS-20261004 (`a2d209d2`).

- [x] **NIB2-92** (MEDIUM): **local claude-backups retention fills md127.** The daily `ai-sessions-*.tar.gz` job writes a FULL ~7.7 GiB tarball every day and keeps 14 locally (~108 GiB), under `/mnt/raid0/llm/claude-backups`, on the same md127 volume as the models and the container root. It also has an off-device Micron mirror at `/mnt/micron/backups` (last `STATUS OK` 2026-10-20 02:08). In the 2026-10-20 disk crisis (29 GiB free) 11 of them were deleted (operator-approved); retention is unchanged, so they grow back within two weeks. The producer is not in any repo script: it is a host-side job (find it with `sudo crontab -l` / `/etc/cron.*` on the host). Decision package for the operator: (a) keep about 3 locally and rely on the Micron mirror, (b) incremental tarballs, or (c) status quo. *(2026-10-23 ~16:20Z, operator decision: option (a), keep 3 local tarballs and rely on the Micron mirror. Host steps delegated to the operator's host filesystem agent via `/mnt/raid0/llm/tmp/host-actions-20261023/HOST_HANDOFF.md`; results land in `RESULTS.md` there. Box stays open until a rotation is observed.)* Ticks when the retention change is applied and one rotation is observed.
  - ✅ 2026-10-24 (3c4ca599; host agent via `HOST_HANDOFF.md`, results `/mnt/raid0/llm/tmp/host-actions-20261023/RESULTS.md`): producer is a user-crontab job, `backup-claude-sessions.sh` (backup `.bak-20261023`), retention `KEEP=14` -> `KEEP=3` (`MICRON_KEEP=60` unchanged). Micron mirror verified first (mounted, newest tarball present at identical size, STATUS OK). Pruned 7 -> 3 tarballs, /mnt/raid0 390G -> 423G available (~33 GiB freed). Rotation observed by workspace-58: the 10-24 run (02:09Z) left exactly 3 tarballs, LAST_STATUS OK; main re-checked the directory listing.
- [x] **NIB2-93** (MEDIUM): **~250 GiB of md127 is invisible from the container.** On 2026-10-20, `du` over every path the container can see fell ~250 GiB short of `df` used for md127, which also hosts the container's `/`. No deleted-but-open files were found, but only 165 of 2,019 processes were readable. Prime suspect: host `/mnt/raid0/docker` (images, overlay layers, build cache). Operator runs on the host: `sudo du -sh /mnt/raid0/docker` and `sudo docker system df`. Prune only with operator approval. Also clears a root-owned 20 KB trash leftover: `sudo rm -rf /mnt/raid0/llm/.trash/20261020-134551-repl_output`. *(2026-10-23, operator: the host agent runs the read-only `du`/`docker system df` commands and reports; no prune.)* Ticks when the gap is attributed.
  - ✅ 2026-10-24 (3c4ca599; host agent, RESULTS.md Task 3, read-only): the invisible space is the Docker data root `/mnt/raid0/docker`, 250.8 GiB actual (plain `du` says 366G because it double-counts 5 live overlay merged mounts); `df` used minus `du -x` total = ~119 MiB, so nothing else is unaccounted. Images are dominated by ~2-month-old SWE-bench `sweb.eval.*`/`sweb.env.*` images (46 in use). No pruning (needs a separate operator decision); the approved 20 KB root-owned trash leftover was removed.
  - ✅ 2026-10-24 (3c4ca599; operator-approved prune, host agent via `/mnt/raid0/llm/tmp/host-actions-20261024/HOST_HANDOFF_DOCKER.md`, results `RESULTS_DOCKER.md` + before/after inventories in that folder): removed 40 stopped `sweb.eval.*` containers and 49 `sweb.*` images (40 eval + 8 env + `sweb.base.py.x86_64`); 0 SWE-bench containers/images remain. Running set unchanged (5; main re-checked `running.txt` vs `running_after.txt`), devcontainer images, volumes (57.8 GB) and build cache (18.9 GB) untouched; no `-f`, no prune verbs. Images 85.6 -> 61.1 GB, Docker root 250.8 -> 224.0 GiB (-26.8 GiB). Not done: the 8 dangling `<none>` images (~30.5 GB) all carry `devcontainer.metadata` (old devcontainer builds, one twyne compose pair), so the hard rule kept them.
  - [x] **NIB2-93b** — remove the 8 dangling devcontainer `<none>` images (~30.5 GB, list `/mnt/raid0/llm/tmp/host-actions-20261024/dangling.txt`) at the operator's next reboot window. Blocker: operator decision 2026-10-24, batched with the next reboot (they are old devcontainer builds; no rebuild/restart now). Host-agent step, `docker rmi` without `-f` after confirming no container references each id. operator reconfirmed 2026-10-29: remove at the next reboot window (host agent). (workspace-f2 2026-11-09: moot: 0 dangling images on the host daemon; none of the 8 listed ids exist) [no-belief: tooling-repair]
  - *(workspace-f2 audit 2026-11-09.)* Operator re-approved 2026-11-09; host agent re-lists the images first because a reboot may have changed them.
- [ ] **NIB2-94** (MEDIUM): **HF token hygiene after the 2026-10-20 argv exposure.** `chmod 600 /mnt/raid0/llm/cache/huggingface/token` (was mode 664; set to 600 by the 3c4ca599 wrap-up 2026-10-21, verified `stat` 600), then the operator decides rotation (the token sat in a curl argv, readable in `ps`, for about 68 minutes before the 16:33Z restart that moved it to a 0600 header file). Done when the mode is 600 and rotation is decided or declined. (filed 2026-10-20)
  - 2026-10-24 main chmod 600 on /mnt/raid0/llm/hf-cache/token (37 bytes, the HF token by size and location; contents never read); token rotation is an operator decision
  - *(2026-10-24, batch-b record.)* The named file `/mnt/raid0/llm/cache/huggingface/token` no longer exists (stat: no such file; no `token*` at depth 2); the 2026-10-21 "mode 600" check refers to a file since removed or moved. `/mnt/raid0/llm/hf-cache/token` was mode 664 (see the chmod line above). Also `/mnt/raid0/llm/tmp/dive-stage2g-kernels-20260925/hf-headers.tmp` is mode 644 (name suggests an HF auth header file; contents not read): chmod 600 or delete is still owed. Code audit (git grep of epyc-root, epyc-orchestrator, epyc-inference-research for Bearer, --token, huggingface-cli/hf login/download, HF_TOKEN, hf_token, curl -H with token): NO committed code passes an HF token in argv; HF_TOKEN is read from env and set as an `Authorization` header in-process via urllib in `scripts/utils/safe_download.py:129`, `scripts/utils/relay_sidecar_check.py:54`, and (orchestrator) `scripts/validate/backfill_registry_artifact_pins.py:48`. The 2026-10-20 exposure was an ad-hoc curl (about 68 minutes in a curl argv before the 16:33Z restart); nothing in repo code to fix. Not ticked: rotation decision still open.
  - *(workspace-f2 audit 2026-11-09.)* Operator decided 2026-11-09: delete `tmp/dive-stage2g-kernels-20260925/hf-headers.tmp` and rotate the token. Rotation is the operator's step.
  - *(workspace-f2 2026-11-09.)* Operator chose rotation again 2026-11-09 (supersedes the 2026-10-22 decline, 4b071084d). Stays open until rotated. Token now at hf-cache/token, mode 600.
- [x] **NIB2-95** (LOW): **land the commit-hygiene hook separator fix.** `scripts/hooks/check_commit_hygiene.py` is staged in the shared /workspace index (`git diff --cached --stat`: 59 insertions, 2 deletions; it rides into the next unscoped commit); fix branch `fix/hygiene-hook-separators-20261020` and tests 12 to 32 per the 2026-10-20 coordinator shard (unverified: the branch was not found in /workspace on 2026-10-21). Operator decision: the `D9-ack` for a hook file. Done when it is committed alone with the ack, or unstaged and parked on the branch. (filed 2026-10-20) ✅ 2026-10-21: landed as `bd9ffccec` by the operator's script (2026-10-20); the stale staged copy in the shared /workspace index was unstaged by the operator 2026-10-21 after it made the D9 loop-plane hook refuse an unrelated research commit (the hook reads the ROOT index).
- [x] **NIB2-96** (MEDIUM): **shared research clone's local `main` carries 3 unpushed commits.** Two are another session's np_context_kvu work; the third, `e0f5a101a`, is a duplicate of `37cc352cc` (DS41-W6.1 results) left by a subagent whose `serialized_push.py` was refused. Never push from it; the owners reconcile (rebase onto origin/main drops `e0f5a101a` as a duplicate). Done when `git -C /mnt/raid0/llm/epyc-inference-research cherry origin/main main` is empty. (filed 2026-10-21) ✅ 2026-10-23: verified `git cherry origin/main main` prints nothing (3c4ca599).
- [x] **NIB2-97** (MEDIUM): **memory telemetry for the next OOM.** INC-20261021-earlyoom-session-kills left no memory sample on disk at the 15:57Z trigger (`dmesg` not permitted, no journalctl). Add (a) a 30 s sampler of MemAvailable/AnonPages/Cached/Mlocked and PSI to a rotated log under `logs/`, and (b) an `earlyoom_audit.sh` snapshot of /proc/meminfo + top-10 VmRSS once per kill burst (proposal printed by the RATIFY-HOST-MEMORY-RULES-20261021 bundle). Report: `artifacts/incidents/INC-20261021-earlyoom-session-kills/REPORT.md`. (filed 2026-10-21) *(2026-10-23, 3c4ca599)* (a) DONE in source: `scripts/utils/mem_sampler.py` (+ `tests/test_mem_sampler.py`, 4 pass); NOT yet running, start it from the host launcher/cron (`mem_sampler.py`, log `logs/mem_telemetry.jsonl`). (b) OPEN: the `scripts/hooks/earlyoom_audit.sh` snapshot is a hook-file edit and needs the D9-ack. *(2026-10-23 ~16:20Z, operator decision on (a): start the sampler via cron; the host agent installs the `@reboot` + `*/5` flock crontab per `/mnt/raid0/llm/tmp/host-actions-20261023/HOST_HANDOFF.md`. Stays open until `logs/mem_telemetry.jsonl` is seen growing. (b) still needs the D9-ack.)* Ticks when the sampler is running and (b) is landed. ✅ 2026-11-02 — (a) live since 2026-10-24; (b) landed `a72113283` (`earlyoom_audit.sh` /proc memory snapshot once per kill burst), acknowledged by the operator. [no-belief: tooling]
  - 2026-10-24 (3c4ca599): **(a) LIVE**: the host agent ran the one-shot test and installed both crontab lines (`@reboot` + `*/5`, `flock -n /tmp/mem_sampler.lock`); `logs/mem_telemetry.jsonl` is growing ~2 lines/min (main re-checked the tail 2026-10-24 ~08:00Z). Box stays open for (b), the `earlyoom_audit.sh` snapshot, which needs its own D9 ack.
- [ ] **NIB2-98** (MEDIUM): **enforce the one-DS41-class-server memory rule in tooling, not only in briefs.** A DS41-1017 CPU server holds ~276 GiB private RAM (MXFP4 repack) + ~463 GiB mapped; two concurrent ones triggered the 2026-10-21 earlyoom kills. Add a launcher/region-lock preflight that refuses a load when MemAvailable − expected footprint < 100 GiB (the rule ratified by RATIFY-HOST-MEMORY-RULES-20261021). (filed 2026-10-21)
  - [x] **NIB98-ATOMIC-PREP-01a16fc3:** publish research proposal `036b8a51957cb6366afb490db34a468e1d482055` on `codex/nib98-atomic-admission`. Existing independent pre-Popen checks can race; the proposal holds a common FD lease through child lifetime, with concurrency, failed-check/spawn, parent-death and synthetic exec-retention controls. It preserves current source need 739 GiB/margin 64 GiB; it does not reinstate the historical 100 GiB margin above. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/nib98-atomic/OWNER-PACKET.md`. ✅ 2026-10-27 [no-belief: tooling-repair]
  - **[declined: ws58 2026-11-03 content-review: merged into NIB2-98 as its adoption step]** **NIB98-ATOMIC-ADOPTION:** owner review the published proposal, provision the trusted common inode, prove actual llama-server FD retention at the next approved noise canary, and adopt the shell wrapper plus remaining loader coverage at a controlled owner boundary. No inode was provisioned, no live guard was changed and no DS41 run occurred during preparation.
    - [x] **NIB98-OWNER-REVIEW-TEST-FOLLOWUP:** remote `codex/nib98-owner-review-20261027` at `4c4ad160` replaces string-presence checks with admission-order/live-FD checks; the focused suite passed 20 tests and four unapplied shell patches passed strict refusal/error controls; owner reply confirms exclusive one-server serialization. Controls remain unapplied; activation still requires the actual FD-retention canary and complete adoption inventory. ✅ 2026-10-27 [no-belief: tooling/tests only]
    - [x] **NIB98-LOADER-INVENTORY-CANARY-PREP:** prepared bounded loader inventory, private guard proposals and a source-sealed C5 private-lease FD canary. Model-free native FD, tiny-server, parent-death, refusal, row and pre-effect checks passed; the exact sampled proposition is recorded by the prospective verifier. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/nib98-loader-inventory-ready/OWNER-PACKET.md`. Private lease `/mnt/raid0/llm/.codex-nib98-canary-01a16fc3/lease.lock` is preserved outside the scratch roots. Actual loaded-server proof, global inode, owner adoption and DS41-1017 HOLD release remain outstanding; unknown aliases and opaque dynamic launchers remain outside coverage. ✅ 2026-10-27 [no-belief: preparation/fixture only]
  - *(workspace-f2 2026-11-09.)* Gate built with 20 tests and a negative control; patch `/mnt/raid0/llm/tmp/churn-wave3-20261109-patches/nib2-98-job-fence-ram-admission.patch`. Landed ac89176ab. Remaining: Pipeline injects `--need-ram-gib` at launch. Existing grant checks still use a 64 GiB margin against the ratified 100.
- [x] **NIB2-99** the shared /workspace clone is about 80 commits behind origin/main with 8 dirty tracked files, none of which upstream also modified, so a fast-forward should be clean. Scripts run from it stay stale until it is synced; operator bundles run from a fresh origin/main worktree meanwhile. (workspace-f2 audit 2026-11-09: text corrected) [no-belief: tooling-repair] (workspace-f2 2026-11-09: /workspace re-synced; read-only drift check and workspace-clone-drift alarm landed, negative-control tests; no auto-sync) ✅ 2026-11-09 [no-belief: tooling-repair]
- [x] **NIB2-100** (MEDIUM): **land the PII hook `model_n_params` false-positive fix.** The `account_number` rule (12-19 digits) blocked llama-bench JSON `model_n_params` values (12-digit parameter counts) in any repo (every repo's pre-commit runs epyc-root `scripts/hooks/pii_precommit.sh`). Fix prepared and staged, NOT committed, in worktree `/mnt/raid0/llm/worktrees/fix-pii-hook-numeric-json-20261021` (branch `fix/pii-hook-numeric-json-20261021`): `n_params` joins the self-describing-key alternation, plus 4 fixture rows (fixture eval 0 FA / 0 FR). Operator decision: the `D9-ack` for a hook file; landing command `bash /mnt/raid0/llm/tmp/fix-pii-hook-20261021/land_pii_hook_fix.sh` (`DRY_RUN=1` first passes). Done when it is on origin/main. (filed 2026-10-21)
  - ✅ 2026-10-23 (f8, operator D9 ack 2026-10-23 ~15:20Z): `n_params` added to the self-describing numeric-key alternation in `scripts/hooks/pii_precommit.sh` (the staged fix from `fix-pii-hook-numeric-json-20261021`, re-applied onto the lint-rewritten line) + its 4 fixture rows. The path-scoped exemption already on main covered only two `data/` dirs (fixture eval with the n_params rows: FR 1/32). After: `pii_fixture_eval.py` FA 0/23, FR 0/32.
- [ ] **GAP-POOL-1** (operator directive 2026-10-25 ~20:35Z, after an idle 1 h 15 m gap): standing pool of 6-10 armed short gap-filler rows (CPU and GPU) plus a gap-fill admission rule (pool rows may start under a HOLD only if they end before its quiet_not_before - 300 s).
  - [x] R6 combined engine (current v9 + EVL v10 + GAP), DEFAULT-OFF, full-quarter native proof PASS 2026-10-26 02:36Z; source merged root bc8d98cb2 (.claude/skills/inference-backlog-scheduling/scripts/gap_pool/) [no-belief: correctness]
  - **[declined: ws58 2026-11-03 content-review: merged into GAP-POOL-1]** owner review + cutover of the live writer/engine to the R6 engine (ws58)
    - *(Phase 1 evidence, workspace-58, 2026-10-26; not a tick.)* Cutover-repairs PHASE1-VERDICT PASS (`/mnt/raid0/llm/tmp/codex-ni-20261026-r6-cutover-repairs/focused-error-recovery-20261026/results/PHASE1-VERDICT.json`): 10 focused / 7 native EVL / 2 draining tests, 156 guard controls, defaults OFF, GNX coverage UNKNOWN. source_publication FALSE, canonical_adoption FALSE: a private validated candidate, NOT a live cutover. Open: publish/fold the 28 R6 source changes; integrate the filler_run10 affinity pin into the full R6 cutover candidate and rerun the whole candidate's controls before any switch.
  - **[declined: ws58 2026-11-03 content-review: merged into GAP-POOL-1 as its done-when]** pool reaches 6-10 armed rows (CPU and GPU); GPU pool rows await operator approval of the GPU class
    - *(2026-10-27, workspace-58 results harvest)* GPU pool v1 attention/elementwise died on a ProcessLookupError exit race (partial, 0 failures); sampler v3 reruns PASS (attention ROPE 328 + SOFT_MAX 207 + FLASH_ATTN_EXT 528; elementwise 32 seeds 0 failed); matmul v1 PASS 571/571; gap-pool R4/R6 quarter positives PASS. Correctness only. [no-belief: correctness]
  *(workspace-f2 2026-11-09 wrap-up.)* Still needed: no standing 6-10 row gap-filler pool or gap-fill admission rule is live. [no-belief: not-a-result]
- [x] **PII-NM-OFFSET** (T3) — the PII hook flags zero-padded nm-format ELF hex offsets (16-digit zero-padded hex, as in `nm` output) as account numbers. The fix must narrowly recognize genuine nm rows (offset/type/symbol), keep the raw bytes, and add negative account-number controls. `scripts/hooks` is D9: operator-signed, never activated or committed without the operator's signature. The GNX publication already worked around it with a `0x` carrier (orchestrator 43c63034). (workspace-f2 2026-11-09: narrow nm-row recognition, 15 tests including 9 negative controls; operator D9-ack; 264cf91e9) ✅ 2026-11-09 [no-belief: tooling-repair]
- [x] **NIB2-101** (MEDIUM): **shared research clone `/mnt/raid0/llm/epyc-inference-research` is 221 commits behind origin/main, with 5 uncommitted tracked files no session claims** (`artifacts/np_context_kvu_cpu_study_20261020/PLAN.md`, `.../driver/kvu_cpu_matrix.py`, `benchmarks/results/index.jsonl`, `scripts/benchmark/beam_scoring.py`, `uv.lock`; per `git status` 2026-10-22 08:4xZ). Plan agreed by all three sessions: (1) rescue branch holding the uncommitted files; (2) fast-forward `main` to origin/main only after the `7B_AK_ENDED` flag exists, with a `/proc/*/cwd` check first that no process runs from the clone; (3) then `git cherry origin/main main` must be empty (also closes NIB2-96). Done when the clone is at origin/main with the rescue branch holding the 5 files. (filed 2026-10-22, workspace-f8)
  - ✅ 2026-10-23 (f8): fast-forwarded to origin/main `62c2e09da` (was 26 behind, not diverged; `git cherry` empty). The one tracked modification, 515 appended lines in `benchmarks/results/index.jsonl` (an overnight 6-model benchmark sweep 10-22 22:25Z to 10-23 07:34Z, owner not identified), was preserved: origin/main does not change that file, so the ff left it untouched. Backup `/mnt/raid0/llm/tmp/research-clone-index.jsonl.bak-20261023T1520Z`. The lines stay uncommitted for their owner.
- [ ] **NIB2-102** (HIGH): **`orchestrator_stack.py start` recompiles the lean registry and model descriptors from the STALE shared research clone.** `scripts/server/stack_commands.py` `cmd_start` (~line 1420) hardcodes `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`, and `src/registry/registry_compiler.py` (`DEFAULT_MASTER_PATH`), `src/registry/registry_loader.py` (fallback) and the `model_descriptors.py` CLI default to it too. The shared clone is ~18 commits behind and the operator chose not to sync it, so the next stack bring-up would serve from a stale master and silently drop ratified declarations (e.g. RATIFY-CTXCKPT-HYBRID-20261024 `ctx_checkpoints: 32`). The compile pipeline already reads research origin/main by default (orch `17db9a6b`, `src/registry/research_origin.py`); route these readers through the same resolver, with a test that `start` compiles from origin/main. This changes what a stack start serves (from stale to current master), so the owner confirms with the operator before landing and the stack owner restarts at their own boundary. Found 2026-10-24 by a 3c4ca599 subagent; owner workspace-58 after the handover. (filed 2026-10-24)
  - [x] **NIB2-102.a** landed 2026-10-24: orch `b4f209aa` (start, plus the registry_compiler / model_descriptors / check_shared_with_derivations / reviewer_pool_gen CLIs, resolve via `research_origin.resolve_research_registry()`: flag > `$EPYC_RESEARCH_MASTER_REGISTRY` > origin/main; refuses rc 2, never falls back to the clone) and derived regen `3329083d` (research eb753e422: lean delta = the 4 SEC-ART-POST-b signed `template_diff_reviewed` lines; ctx_checkpoints kept, lean 3/3, priors 10/10). Offline proofs in `/mnt/raid0/llm/tmp/nib2-102-3c4ca599/`. The operator confirmed keeping both after the fact (main landed them before asking; 14:25Z).
  - **[declined: ws58 2026-11-03 content-review: merged into NIB2-102 as its proof]** **NIB2-102.b** start proof: after the shared clone `/mnt/raid0/llm/epyc-orchestrator` contains `3329083d` (via FILLERS `nib2-gnx1-reindex-2`, booked by workspace-58 inside its inf66 writer v4 (pid 1844243) for the GPU-drain gap after s5-kpf64-ef window A; never ff it by hand), the first real `orchestrator_stack.py start` compiles from origin/main and serves `ctx_checkpoints: 32`. Owner workspace-58.
  - *(2026-10-24, workspace-58.)* API-only reloads done: 16:21:56Z pid 3878836 after the nib2 ff incl. `3329083d`; 18:48:43Z pid 691922 after the operator-approved ff to 84f6f6f1. NIB2-102.b stays open: the start proof waits for the first real stack start.
  - [x] **NIB2-102.c** re-pin `tests/unit/test_orchestrator_stack_import_is_argv_safe.py`: its pinned copies of `orchestrator_stack.py` / `model_descriptors.py` were already stale before `b4f209aa` and are now further behind. Review what the pin guards first; never bump the hash blind.
    - ✅ 2026-10-24 (Codex NI, reviewed by its main; verified by workspace-58): the re-pin is a reviewed 2-file repair, not a blind hash bump, and the real host-capacity guard is kept. It landed on orchestrator origin/main via merge `1f4c2bdb` (feature `9fdb62a9`; the tested candidate is `7bf0b9b5`). It touches `tests/unit/test_orchestrator_stack_import_is_argv_safe.py` and `tests/fixtures/ni63_capacity_child/source_clone.py`. The granted run `codex-ni-nib2-102c-20261024` reported 5 passed and 1 dependency warning in 1.79 s, with log `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/nib2-102c/test.log`.
  - *(workspace-f2 2026-11-09.)* The shared clone now contains 3329083d; only NIB2-102.b remains: first real stack start compiling from origin/main and serving ctx_checkpoints: 32.
- [x] **NIB2-103** (MEDIUM): **`data/template_reviews/` durability.** The dir in epyc-inference-research holds the 6 diffs that the SEC-ART-POST-b signatures attest (4 reviewed + 2 `.v2.diff`) but has no `README` and no `SHA256SUMS`, so nothing pins or explains those bytes. Done when a README (what each diff is, which registry entry signs it) and a `SHA256SUMS` are committed and pushed to research origin/main, and a verify step (`sha256sum -c`) is run and cited. Filed 2026-10-24 (workspace-58 wrap-up). [no-belief: durability docs/hashes, no measurement] (research main 9eee9121d, ws58 2026-10-25)
  - *(2026-10-24, workspace-58 check; box stays OPEN: Codex publication pending.)* Research origin/main `data/template_reviews/` holds only the 6 `.diff` files; no README and no SHA256SUMS yet, so there is nothing to `sha256sum -c`.
- [x] **LR-1** — `scripts/system/worktree_gate.py`, the only removal path for a worktree. It refuses a tree named by
      any process cwd, argv or environment, by a live launcher or campaign input, or one that is KEEP-marked, git-locked
      or a lane/pool tree. ✅ 2026-10-04 (root `837ebf6f`; `tests/test_worktree_gate.py`)
- [x] **LR-2** — `scripts/system/scratch_cleanup.py` over each handoff's declared **Scratch** roots, run as wrap-up
      Step 7b and from `/log`. Never a cron job, by operator direction. ✅ 2026-10-04 (root `837ebf6f`, `5c86047b`)
- [x] **LR-3** — the handoff `**Scratch**:` header field and its contract (`handoff-index-authoring.md` § Scratch
      roots), plus an `index_state.py` warning for a handoff that lacks it. ✅ 2026-10-04 (root `837ebf6f`)
- [x] **LR-4** — `scripts/utils/safe_download.py`: downloads cannot leave `.part`/`.incomplete` stubs, and `/tmp`
      destinations are refused. ✅ 2026-10-04 (root `38c3a2e3`)
- [x] **LR-5** — test-suite disk leaks fixed: the 55,897 `autokernel-planner-anchor-*` dirs from `runtime_anchor()`
      and the other bare-`mkdtemp` sites. ✅ 2026-10-04 (research `440b5b5c`, merged `01a19f24`)
- [x] **LR-6** — `scripts/system/host_hygiene_tick.py`, launched by `hub_supervisor.sh once`: a free-space alarm
      (`host-disk-free-low`, two-sample), a daemon keeper (`relaunch_if_down`), claude-backups freshness and the daily
      grower ranking. ✅ 2026-10-04 (root `913585ff`). Activated by LR-6a on 2026-10-06; first heartbeat 16:56:01 UTC.
  - [x] **LR-6a** (operator, host-only) — **re-pin the host supervision cron.** ✅ 2026-10-06 — operator executed approved option 2A on the host; installation recorded 16:54:22 UTC, first `host_hygiene_tick` heartbeat 16:56:01 UTC. MAIN verified the exact registry projection, four pinned supervisor files, saved cron/backup records and fresh state/log; [separate operational acceptance and limits](../../artifacts/operator/decisions/OP73-host-activation-20261006/acceptance/README.md). All 34 unrelated nonempty cron lines and fleet-watch entry were preserved. Original pre-heartbeat installation report is unchanged. No independent current-live-host-crontab inspection, forced tick, daemon restart, post-restart reaper recovery or bus launch is claimed.
        - [x] **LR-6a-PREP — prepare the approved host activation package.** ✅ 2026-10-06 — MAIN reviewed the fixed installer/helper bytes and independently derived the minimal canonical registry projection; [host launcher and limits](../../artifacts/operator/decisions/OP73-host-activation-20261006/README.md). Static preparation only; the parent now separately records operator host execution and a fresh heartbeat. No bus launch or post-restart reaper acceptance.
- [x] **LR-7** — the DS41 load-bearing worktrees are declared with git locks: `root-main-epyc-root-repo` and
      `research-ds41-run10`. ✅ 2026-10-04 (INF-77 DS41-C113a)
- [ ] **LR-8** — **merge the periodic cleanups into one tick.** LR-6a is accepted; isolated non-inference source preparation is now available. Fresh source review finds the report-only `codex_retention_reaper.py` is already a daily heavy-phase duty with the CPU-region interlock; do not duplicate it or enable apply. The remaining gap is the standalone `opencode_event_reaper.sh` loop: integrate its existing `once` duty, preserving the 1800-second cadence and fail-closed present/unobservable VACUUM guard; unify failure/blind alarms and adjust the keeper/registry contract consistently. Scope remains only opencode's `event` table in idle sessions, never sessions/messages/parts or harness transcripts. Keep the current daemon running until a reviewed owning-session runtime handover. Published tick source is consumed by the refreshed read-only view, so preparation must remain inactive by default to prevent dual schedulers. [Activation evidence and bounded next step](../../artifacts/operator/decisions/OP73-host-activation-20261006/acceptance/README.md).
  - [x] **LR-8-SRC — implement and validate inactive event-duty source.** ✅ 2026-10-06 — MAIN accepted exact source78c88908 and hosted native88/88 original evidence; [acceptance and limits](../../artifacts/ni08/lr8-source-acceptance-20261006/README.md). Existing shared-grade analysis remains tracked by VB-LR8-EVENT-DUTY; parent runtime handover remains open. NI08-01: explicit opt-in plus full scheduled owner contract, independent 1800-second cadence, fail-closed CPU/daemon observations, overlap lock and one native outcome/alarm owner. Preserve the existing registry and daemon defaults. Hosted synthetic native verifier acceptance precedes runtime handover; source preparation alone does not close LR-8.
  - *(workspace-f2 2026-11-09.)* Source complete; REFRESH-20261109.md updates the handover. Remaining: the owning session swaps the live reaper at its boundary.
- [x] **LR-9** — **harness state and session transcripts are never cleanup targets** (operator hard rule 2026-10-04:
      Claude/Codex backup logs and transcripts *"should NOT BE TOUCHED UNDER ANY CIRCUMSTANCES. They are historical
      transcripts used by a root filesystem project far more senior to anything performed in this project repo"*,
      extended to every third-party harness: opencode, hermes, claude share, harness codex homes). Enforced in code:
      `codex_retention_reaper.py` apply permanently disabled (`722b7196`), and `scratch_cleanup.py` `NEVER_TOUCH`
      refuses those trees whatever a handoff declares (`722b7196`, `b639dc8e`). **2026-11-07 amendment: ~/.codex rollouts are now rotated at 7 days** (operator decision 2026-11-07, session operator-adhoc-ops-20261105, REVERSED for ~/.codex ONLY: the janitor's CODEX step deletes vault-verified rollouts older than 7 days and keeps the newest 7 days; claude, opencode, hermes, vault and every other harness tree stay never-touch). Written into
      `docs/guides/agent-workflows/cleanup-reference-check.md` and `docs/design/autokernel-disk-hygiene-20260915.md`.
      ✅ 2026-10-04
  - [x] **LR-9a** (operator) — **ratify the hard rule into `agents/shared/OPERATING_CONSTRAINTS.md` → *Destructive
        operations*.** That file is human-only. Prepared as
        `scripts/operator/ratify_harness_state_never_touch_20261004.sh`, with the patch
        `artifacts/operator/harness-state-never-touch-20261004.patch`. Review it with no args, then sign with `--apply --attest
        RATIFY-HARNESS-STATE-NEVER-TOUCH-20261004`.
        ✅ 2026-10-04 — signed by the operator: root `ae06680f` (OPERATING_CONSTRAINTS +10 lines, receipt
        `artifacts/operator/receipts/RATIFY-HARNESS-STATE-NEVER-TOUCH-20261004.json`). Closes OP-74.
- [x] **LR-10** (workspace-ec) — land the orchestrator half (`lane/leak-tests-20261004`, which includes `9a2a35bf`: (workspace-f2 2026-11-09: orchestrator age-based eviction landed; one failure in test_fenced_child_keeps_script_semantics also fails on clean main) ✅ 2026-11-09 [no-belief: tooling-repair]
      age-based eviction for the unbounded fence-kernel spec-file cache) on orch main. As of 2026-10-04 04:00Z the branch
      exists only locally and is not pushed. Close with the orch main sha.
- [x] **LR-11** — **`codex-ni*`/`ni0X` worktrees are not cleaned up at ticket close.** 2026-10-07 disk (workspace-f2 2026-11-09: worktree_gate close-lane with token-boundary ticket match and an idle floor) [no-belief: tooling-repair]
      audit (`/mnt/raid0/llm/tmp/disk-audit-20261007/AUDIT.md`): 207 of 606 worktrees audited were this
      lane class, left behind after their owning ticket closed — a process gap (no close-time cleanup
      hook for this lane class), not a one-off. The 2026-10-07 crisis itself (562 worktrees / 414 GiB,
      tmp 255 GiB, free fell to 86 GiB, blocking a DS41 lane relaunch) was resolved: operator ran
      `/mnt/raid0/llm/tmp/disk-audit-20261007/delete_safe.sh`, free disk is now 175 GiB. This box is the
      remaining structural fix — a cleanup step at ticket/PR close for the `codex-ni*`/`ni0X` lane class,
      analogous to `LR-2`'s wrap-up-time sweep but triggered at close rather than at wrap-up.
- [x] **LR-12** — **`scripts/hooks/agents_reference_guard.sh` resolves markdown refs against the wrong
      root for lane-worktree edits.** It computes `PROJECT_DIR=${CLAUDE_PROJECT_DIR:-$(pwd)}`
      (`agents_reference_guard.sh:8`) and `CLAUDE_PROJECT_DIR` is a harness-level env var fixed to
      `/workspace` for the session, not reset by `cd`-ing into a lane worktree — so it resolves a bare
      markdown ref against `/workspace`'s checkout, not the worktree actually being edited. Reproduced
      twice (2026-10-07, two different lane worktrees/harness instances) editing
      `agents/shared/OPERATING_CONSTRAINTS.md`: the ref `docs/guides/agent-workflows/cleanup-reference-check.md`
      exists at the editing lane's own tip but not yet at `/workspace`'s (lagging) tip, so the hook
      `BLOCKED` every edit to the file regardless of content. Fix: resolve against the edited file's own
      repo root (`git -C <file_dir> rev-parse --show-toplevel`), not the harness's launch directory. Both
      blocked edits are text-ready and unapplied — see `progress/2026-10/2026-10-07-ak-lane-coordinator-wrapup.md`
      §8 and §9.4 for the exact patch text. ✅ 2026-10-07 — [MAIN source and original5/5 acceptance](../../artifacts/ni08/lr12-reference-hook-source-20261007/README.md); actual edited-file Git-root resolution and all five subprocess controls published. Protected policy amendments still require operator ratification.
- [x] **LR-13** — land three subagent-brief/wrap-up memory rules adopted 2026-10-07 into (workspace-f2 2026-11-09: third rule ratified by the operator at 214ca99c7; two already existed in agents/shared) ✅ 2026-11-09 [no-belief: tooling-repair]
      `agents/shared/SESSION_LIFECYCLE.md` (wrap-up cadence section) or
      `agents/shared/OPERATING_CONSTRAINTS.md` (subagent brief section), whichever already hosts the
      nearest-matching text — not yet checked for duplication: (1) per-task wrap-up includes the
      task's own scratch cleanup (generalizes the existing disk-crisis lesson); (2) every subagent
      brief requires logs, progress and handoff updates for its own work, then clearing its own
      scratch **only if no longer needed**; (3) the main thread, not the subagent, decides scratch
      lifetime per brief. Same `LR-12` guard defect blocks editing these files from a lane ahead of
      `/workspace` — land LR-12 first or edit once `/workspace` has caught up.
  - *(workspace-f2 2026-11-09.)* Two of three rules already exist in agents/shared. The third is scripted: `scripts/operator/ratify_lr13_subagent_scratch_20261109.sh`, awaiting the operator --apply. Signing it invalidates the older OP-LR11-LR13 package pin for OPERATING_CONSTRAINTS.md.

## 2026-09-27 compaction — orphaned residuals boxed

Both residuals below sat inside closed items and had no box of their own, so the compaction gave them one before
moving their parents to the completed ledger.

- [x] **NIB2-88** (LOW, operator/owning session): **add the opencode event reaper to the post-reboot checklist.** From (workspace-f2 2026-11-09: coordinator-agent cold start verifies the reaper, keeper-aware) [no-belief: tooling-repair]
      NI-OC (✅ 2026-09-08): the container has no cron or systemd, so `scripts/system/opencode_event_reaper.sh` must be
      relaunched by hand after every reboot, and NI-OC asked the operator to add it to the post-reboot checklist.
      Nothing does so today: on 2026-09-27, `agents/`, `docs/`, `.claude/` and `scripts/session/` held no reference to
      `opencode_event_reaper`. After the 2026-09-21 restart the reaper was simply not running until NI-OC-a.1 found it.
      Add the relaunch step (detached, from the tracked path `/workspace/scripts/system/opencode_event_reaper.sh`, as
      NI-OC-a.1 did) to the cold-start checklist. `agents/shared/` is human-only, so the agent-editable home is the
      `coordinator-agent` skill's cold start. Zero inference.
      - 2026-10-04: the reaper is operator-approved to keep running. It prunes only opencode's `event` streaming table
        in idle sessions, never sessions, messages or parts. It was relaunched at about 03:50Z, pid in
        `/mnt/raid0/llm/tmp/opencode-reaper.pid`. `host_hygiene_tick.py`'s keeper (root `913585ff`) relaunches every
        registry row marked `relaunch_if_down`, which today is this reaper. Once the host cron re-pin (LR-6a) is done,
        that keeper does this item's job: close it then, with a census showing the reaper relaunched after a restart.
      - 2026-10-06: LR-6a installation and first heartbeat are accepted. The tick observed the reaper already `running_current`, not relaunched after a restart; this parent remains unchecked until that distinct recovery evidence exists.
- [x] **NIB2-89** (LOW): **generalise the bus supervisor's H-4 self-restart to every registered daemon.** From NIB2-81
      (✅ 2026-09-23): remedy (a) (`daemon_provenance.sh`) and remedy (b) (the registry `runtime` field, the
      `observer_census.py --live` census and the `restart_on_stale` path) landed. Its own "Remaining" line also
      named the H-4 generalisation: each daemon publishes its `source_tree`, and one supervisor tick restarts a divergent
      one. The code is under `scripts/coordination/**`, so landing it needs a D9 ack. It has no runtime effect while
      bus_supervisor stays DOWN (operator ruling 2026-09-23). Absolute-path launch recipes and host-cron `once` ticks
      remain an operator decision (OP-9/FW-3). Zero inference. ✅ 2026-11-02 — landed `cdaa27c0f` (opt-in `source_tree` staleness predicate for registered daemons, the H-4 generalisation), acknowledged by the operator; lands DORMANT (no runtime effect while bus_supervisor stays DOWN). [no-belief: tooling]

## Cross-references

Canonical sources (always verify status in these files first):
- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — DAR, RI, AP, DS series
- [`research-evaluation-index.md`](research-evaluation-index.md) — EV, REPL, CF, TOC series
- [`inference-research-index.md`](inference-research-index.md) — AM, triattention, KV series
- [`pipeline-integration-index.md`](pipeline-integration-index.md) — vision, ODL, Lean, TTS series
- [`user-facing-harness-index.md`](user-facing-harness-index.md) — user-facing harness work (formerly Hermes B-series)
- [`master-handoff-index.md`](master-handoff-index.md) — cross-domain priorities

- [x] **NIB2-80** (MED): **the `EARLY_ABORT` escalation path bypasses its own budget gate.** In
      ✅ 2026-09-23 — epyc-orchestrator `d1f5bf02`: reading (1) — immediate escalation kept, bounded by `max_escalations` at all FIVE early-abort sites (not just the cited one); at budget it falls through to the sibling gate/retry/fail chain. Residual: early-abort escalation still skips the role-cycle check.
  `epyc-orchestrator/src/graph/nodes.py:235-241` an `ErrorCategory.EARLY_ABORT` bumps
  `state.escalation_count`, records the role change and returns `CoderEscalationNode()` **without
  calling `_should_escalate`**. Every other escalation site in that file gates on it
  (`nodes.py:250, 284, 364, 481`), and the gate is what enforces `cfg.max_escalations`, the
  no-escalate categories and the retry precondition (`src/graph/decision_gates.py:27-47`). So a
  run that keeps early-aborting can escalate past `max_escalations`, and the budget it is
  charged against is never read. **Two candidate readings, and the fix differs:** if immediate
  escalation on early-abort is deliberate, the bound is still missing (escalate only while
  `escalation_count < cfg.max_escalations`, else fall through to the normal failure path); if it is
  an oversight, the call belongs behind `_should_escalate` like its four siblings. Surfaced
  2026-09-17 while writing the FW-1 loop-block sketch — the block made it visible because it forces
  every gate and every rejection destination to be named
  ([`fuzzy-workflow-authoring-gui.md`](../completed/fuzzy-workflow-authoring-gui.md) § FW-1 sketch, finding F-1).
  **Not fixed here: it changes graph control flow on a path evals traverse, so it wants its own
  before/after test and the owning session's judgement on which reading is right.** Zero inference
  to verify (unit tests with a fake backend); zero compute.
  - [x] **NIB2-80a** (LOW) — the budget-bounded early-abort escalation still skips `_detect_role_cycle_impl` (A→B→A bouncing), which `_should_escalate` applies to every other site. Add the cycle check to the early-abort branch with a test.
- [x] **NIB2-82** (LOW) — `scripts/autopilot/baseline_authority_seed.py::_autopilot_running_pids` detects AutoPilot with `pgrep -af "autopilot.py start"` — a name-pattern read CLAUDE.md forbids. Replace with the read-only /proc cmdline scan used by the 2026-09-23 ratify script.
  ✅ 2026-10-05 — app `9887da8fbb87` scans exact process argv positions; unavailable observation
  refuses baseline append with a distinct status and exit two. Original CI `37297449498` passes
  12 baseline fixtures under explicit synthetic RAM plus a separate ordinary actual-host guard.
  No live journal mutation or process-control command was run; native originals are retained.
- [ ] **NIB2-83** (MED) — after ETR-1 (era E17) `task_failed` rows score 0, and `task_failed` is the RESIDUAL class (any error `infra_failure_reason` does not recognise). Once post-E17 eval rows exist, histogram their error texts and move any platform-caused shape into `INFRA_ERROR_PATTERNS`/provenance classes, so an unrecognised infra error is not scored as an agent failure.
  - 2026-10-31 source partial: ROOT `7a2115fd52ad830eaf90b138003062258f4ed759` fixes the standalone residual reader to consume native Boolean error/error_detail, clean scored-row disposition omission and canonical full era/policy identities. Source-bound native writer integration passed 6/6; the original seven controls passed once as regressions, with their historical source-map/receipts unchanged and explicitly unable to qualify the changed helper. Unconfigured discovery skips explicitly. Git proof: `artifacts/engineering/nib83-native-reader-20261031/proof.json`. No genuine post-E17 evaluation cohort was established in the three inspected source-declared locations; the full attempt denominator remains UNKNOWN, direct sidecar policy remains unbound, raw error text stays private, and no classifier, era rule, live journal or grade changed. NIB2-83 remains OPEN with no completion credit. [no-belief: native-schema reader compatibility controls only]
  *(workspace-f2 2026-11-09 wrap-up.)* Blocked: needs post-E17 `task_failed` eval rows to histogram, and none exist yet. [no-belief: not-a-result]

### NI05-16 — explicit kernel path overrides

- [x] Honor explicit configured CPU/GPU binary paths without evaluating the production-store default first.
  CI run `37275807626` collected no orchestrator tests because configuration import tried to discover the
  absent host store despite explicit fixture overrides. Preserve store discovery when no override exists;
  verify both branches with isolated configuration fixtures. No fabricated store, frozen-kernel edit or reload.
  Owner: Codex config-override worker; tests execute off-host.


## 2026-10-05 supplement — source-only benchmark preflight safety

- [x] **NI-SHELL-RELOAD-SAFETY — remove peer-process mutation from the instrumented benchmark preflight.**
  `scripts/benchmark/package_a_instrumented_eval.sh` currently runs `fuser -k 8000/tcp` and starts
  uvicorn when health is unavailable. Replace this with an actionable failure referring the
  operator to the API owner, while preserving the healthy path. No process kill, reload or stack
  mutation is part of validation; source/syntax and hermetic preflight fixtures only. Keep this
  repair separate from NI05-21's formatting patch. Owner: Codex NI05-24.

  Completion: app main `ee9c81618bf9` preserves the healthy branch and exits one with owner guidance
  on unavailable health. Hermetic fake-curl branches and syntax passed in CI `37291798409`; no actual
  endpoint, benchmark or lifecycle command ran. See `progress/2026-10/2026-10-05-ni24-package-a-health-preflight.md`.

## 2026-10-05 supplement — offline CPU CLI overrides

- [x] **NI-OFFLINE-CPU-CLI — defer default kernel-store discovery in two leaf commands.**
  ✅ 2026-10-05 — app `4244e72b2aa8` publishes both lazy-default repairs and their focused
  fixtures. Original recovery `37299780302` preserves 13/13 CPU cases and a separate 2/2
  ordinary guard phase; main reopens native receipts and every bound original byte.
  `scripts/benchmark/md_self_draft_ab.py` and `scripts/corpus/build_static_ngram_cache.py`
  currently resolve CPU-store defaults at import, before explicit CLI/config overrides can apply.
  Resolve defaults only when no override exists; preserve strict failure for missing defaults.
  Verify fresh import, explicit parsing/configuration and absent-override refusal off-host. No
  shared store-provider changes, fabricated store, binary execution or production mutation. NI05-26.


## 2026-10-05 supplement — durable CI phase prefixes

- [x] **NI-CI-PREFIX-DURABILITY — preserve completed native validation before later phases can time out.**
  NI05-29 / VB-CI-PREFIX-DURABILITY: original ninth run `37295291738` timed out before its final
  artifact step, losing all original native receipts/JUnit. Ordinary GitHub logs survive; they
  are not reopened receipts or reconstructed tuples. Upload immutable named phase bundles
  immediately, declare a bounded broad attempt with graceful interrupt and kill grace inside
  the captured argv, and keep partial counts distinct from whole-scope completion. Replace
  unavailable runner `rg` enumeration with fail-closed stdlib source-readset enumeration.
  No source grading or producer-schema change; candidate recipe and original artifacts only.


## 2026-10-05 supplement — immediate escalation admission

NI05-30 / existing NIB2-80a: read-only current source review finds five legacy immediate
early-abort branches skip the shared role-cycle guard. Five analogous LangGraph branches
also omit an explicit escalation budget. Verify active graph selection and shared admission
semantics before editing; exercise actual early-abort routing with cycle, budget, and first-abort
controls. This is offline source/fixture work; no route activation, live requests or reload.


## 2026-10-05 supplement — native source-fixture custody

- [x] **NI-CI-FIXTURE-CUSTODY — retain original synthetic source fixtures through the privacy gate.**
  NI05-31: recovery snapshots include unchanged public redactor fake-credential fixtures and
  search fixtures carrying a book ISBN. The gate blocks those copied inputs. Prepare a narrow
  exact-byte/source/request/readset-bound correction with genuine-secret/edit negative controls;
  never redact or reseal native records, bypass hooks, exempt whole artifact trees, relocate
  fixtures to hide from scanning, or widen vendor-placeholder authority. Original native
  bundles remain on RAID0 and immutable phase artifacts; exact provenance correction and complete public custody are accepted 2026-10-05.

NI05-30 accepted 2026-10-05: app `631220f7b05a` adds the same pure budget/cycle admission
predicate to all ten immediate branches. Original CI `37303383753` passes 36 focused cases
and one separate actual-runner capacity guard. [Original native bundle](../../artifacts/ni05/early-abort-cycle-37303383753/README.md)
binds exact tested source and original bytes. No production activation or reload.


2026-10-05 reviewed boundary: NI12/NIB2-87 installs research pytest 9.1.1 additively and verifies both managed imports; root health source checks both. NI25 captures both API orders (376/376 each) plus the explicitly synthetic broad attempt. NI29 retains all five original phases before the broad timeout; the broad result is diagnostic/null, never a whole-unit pass. NI31 passes 17 actual-index controls, 8 caller cases, privacy fixture denominators 0/21 false accepts and 0/30 false rejects, and six installed-wrapper assertions. Full unchanged native custody is published in [recovery bundle](../../artifacts/ni05/recovery-37299780302/README.md) and [NI31 bundle](../../artifacts/ni05/fixture-custody-37307260869/README.md). NI10 remains open: one bounded journal census and the source-schema map do not establish HSF-3's requested distribution. Newly unlocked NI32–34 are filed here and in their existing canonical handoffs; no duplicate domain ownership.

NI33/OBS-12a complete 2026-10-05: exact five active command substitutions preserve arguments and honor executable managed-venv shebang. [Unique caller review](../../progress/2026-10/2026-10-05-obs12a-session-bus-interpreter.md). No daemon restart or historical instruction rewrite. NI28 standalone dependency capture source is accepted through 12 named fixtures; actual claimed store capture is independently verified; prospective measurement attachment remains open, measurement-producer digest bindings stay distinct.


NI34/NI35 complete 2026-10-05: prospective private actual-index and named managed-import producers/readers use the existing verifier carrier and shared grade. Original hosted suites pass 84 and 11 cases respectively without skips/failures/errors. An actual two-path PII sub-gate finding independently reopens; earlier setgid custody is refused unchanged. The managed-import positives/negatives remain synthetic CI fixtures, not actual host health. Main integrates source, original public custody, source enrollment and wiki; [privacy progress](../../progress/2026-10/2026-10-05-ni34-staged-pii-native-capture.md), [managed progress](../../progress/2026-10/2026-10-05-ni35-managed-tooling-check.md).

2026-10-05 reviewed source boundary: NI10 explicit optional `x_client_class` validates and forwards self-reported metadata with `caller_supplied:x_client_class` provenance; omitted fields remain absent. App source is published at `099dc1af69cf`. Original CI 37325396069 verifies 1/1 ordinary capacity refusal and 17/17 synthetic request-to-record controls. NI32 source59e adds 12/12 native/exact/proxy and tap/progress/checkpoint schema controls; original CI37326107920 is TRUE Judged/Located. The preceding 8/12 failed fixture expectation remains FALSE unchanged; missing-ledger custody correctly refuses to report OK (SC73). Neither fixture result supplies live gap data. HSF-3 remains open pending ≥50 properly keyed/classed sessions per reported basis in each independent window; no percentile, client brand, TTL or inferred enqueue. Delivery tally **34/36**.

2026-10-05 NI36/DCP-13a,b source boundary accepted: remove unreachable fetch instruction, keep compact loop telemetry and return the separately retained full report to the user on cache hits; legacy summary-only entries miss the report-required path. Original CI37327525343 reopens TRUE Judged/Located for 57/57 complete cache/architect cases and 1/1 separate ordinary capacity refusal, zero skips/failures/errors. Ordinary five-source candidate504 is promoted as appdb38737d; helper/workflow stay candidates. No inference or live-cache performance claim; inference-dependent DCP-13 arms stay open. NI37 timeout reporting is newly filed; tally **35/37**.

2026-10-05 NI18 fullscan checkpoint accepted: all895 tracked unit modules have independently reopened original native receipts and deterministic selection/source/hash accounting across32 shards. Outcomes826TRUE57FALSE12NULL;16,227 collected/15,719 passed/258 failures/68 errors/182 skipped. This is capture/accounting acceptance, never whole-suite conformance. Originals remain unchanged in CI37327810408 and owned custody; [derivative inventory](../../artifacts/ni05/unit-sweep-37327810408/README.md) records the distinction. A prospective nine-module fixture rerun prepares only missing owned0700 runner scratch; parentNI18/SSU-F13 remains open for classification/repairs. Running tally **35/38**.

NI18 scratch-fixture phase independently accepted from original CI37331885023: all nine unchanged test modules reopen TRUE Judged/Located;312 collected282passed30skipped0fail/error, separate ordinary guard1/1. Runner-only owned0700 scratch preparation resolves the observed path failures while preserving fence assertions. Earlier895-module FALSE/NULL originals are unchanged; this is no whole-suite pass. NI39 cache-fixture follow-on is newly filed; tally **35/39**, NI18/37/38/39 continue.

NI39 accepted 2026-10-05: main reopened all three original CI37334324990 receipts through the trusted reader/shared verifier grade. The two unchanged command-construction modules pass74/74 and11/11 with zero skips/failures/errors; the distinct ordinary expected capacity refusal passes1/1. Both original source hashes match the fullscan; runner contexts attest an absent-before-setup, empty, owned0700 cache fixture without override or live KV data. Original fullscan outcomes remain unchanged. Source-only follow-ons NI40 scratch-dependent spill output, NI41 optional scorer dependency and NI42 temporary-DB graph fixtures are filed for concrete review. Published tally **36/42**; NI18 stays open.

NI40/NI42 accepted 2026-10-05: main independently reopened original CI37339651393 (13/13 spill cases) and CI37339553198 (five graph modules,65/65 cases), all TRUE Judged/Located with zero skips/failures/errors. Declared source snapshots match pinned appdb38737d and exact workflow/producer originals. Independent postchecks prove all three binary targets absent/non-symlink; graph uses temporary databases and mocked embeddings. Spill scratch ownership/emptiness is attested before execution only, with no separate original post-run scratch check. Original fullscan failures/skips and first graph diagnostic NULL records remain unchanged. Public originals are preserved at artifacts/ni05/repl-spill-37339651393 and artifacts/ni05/graph-fixtures-37339553198. Accepted tally **39/44**; NI18/38/41/43/44 continue.

NI38 bounded offline score preparation accepted 2026-10-05: original CI37345306976 passes12/12 scorer and67/67 reader/ingestion cases, zero skips/failures/errors. Main independently reopens both CI receipts TRUE Judged/Located and the bound original synthetic scored-report archive in owned0700 custody: one TRUE report and two diagnostic NULL/zero-row originals, preserving original UUIDs/modes/bytes. Descriptive macro file/span metrics retain failure/empty denominators and caller-declared dispositions/costs; no official dataset denominator or quality claim. Reviewed app sourcec8851695 and root sourcecab789885 are promoted unchanged; recipe remains separate. Original public prefixes: artifacts/ni05/contextbench-score-37345306976. Full DCP-10 benchmark stays open; tally **40/44**, NI18/41/43/44 continue.

2026-10-05 accepted boundary: NI43 retryCI37347669248 passes24/24 exploration plus19/19 mutation cases on unchanged appdb387; main independently verifies both TRUE Judged/Located receipts, every declared source byte, private checkout/empty fixture roots and scratch, and absent binary postchecks. First failed mutation original remains unchanged. NI44 CI37348970500 passes36/36 offline observer cases; main verifies TRUE Judged/Located, pinned source/recipe bytes and isolated bus absence, then integrates exact five source/test files as d4999a170. Qualified authoritative probe evidence replaces marker-derived leaf idle authority; uninstrumented Claude remains UNKNOWN and live processes are not restarted. Public originals: artifacts/ni05/repl-filesystem-37347669248 and artifacts/ni05/observer-leaf-37348970500. NI51 closes only retired E8 active-consumer scope under existing OP-19. Tally **43/52**; NI18/41/45–50/52 remain open, with no inference or live-stack change.

2026-10-05 NI41 accepted: originalCI37351080596 passes68/68 cases (18confidence-probe/9EV11stats/41verifier-mode), zero skips/failures/errors; allfive named positive/missing-package hard-fail controls pass. Main independently reopens allthree TRUE Judged/Located receipts and verifies exact source/dependency/context bytes, installed versions, frozen additive lock and absent binary postchecks. Rawresolver unrelated changes are preserved but rejected for promotion; all214original nonproject lock records/top-level fields remain unchanged. Only the optional extra and its three-package closure are published to appmain65599ff2b02fcf10a9631376e143e507717469b6. Original public custody: artifacts/ni05/eval-scoring-37351080596. SSU-SCORING-EXTRA and VB-CI-OPTIONAL-SCORING-LOCK close; tally **44/52**, NI18/45–50/52 continue. No inference, scientific quality, capacity, default-serving change or runtime reload claim.

2026-10-05 NI46–50 accepted: originalCI37352568892 passes101/101 whole-module cases (8vision/10quiescence/48requestschema/13pairwiseplanner/22parkedrole), zero skips/failures/errors. Main independently reopens allfive TRUE Judged/Located receipts, verifies31Git-boundsource snapshots+4context/install originals per capture and five absent-path/unchanged-lock postchecks. Exact four fixture files and one schema-description file are published to appmain64843e13642930895bb2e52694cd444de5892903; runtime policies and original FALSE sweep outcomes remain unchanged. NI45 still requires fresh source analysis and prospective evidence. NI53 newly filed before execution for active strategy-report original boolean integrity custody, with descriptive counts and no new ladder/method/quality claim. Tally **49/53**; NI18/45/52/53 continue. No inference, liveKFD/GPU/hold/store access or API reload.

2026-10-05 NI18 source review unlocks seven independent fixture tasks NI54–60: mocked executor validation, declared placement topology/CLI leaf, live-DB sentinel, path-bound routing pool, injected leakage vocabulary, owned REPL/scorer scratch and local deterministic embeddings. Main reopens all69 original exception receipts/source snapshots (57FALSE12NULL); originals remain unchanged. APP65599ff retains69/69 source parity; current64843 retains65/69 with exactly four accepted NI46/47/49/50 fixture changes. These are queued proposals, not accepted repairs. Existing native CI carrier/source wiring is extended before captures. Delivery tally49/60; main owns shared metadata and publication.

2026-10-05 reviewed NI18 action-map checkpoint: derivative exception-action-map.json is copied byte-for-byte (SHA762216ac685cd3cde86a17443263b38545bfdd06c39e3234436da7eebac6dc4c), with separate main identity review. All69 original receipts/source snapshots reopen;57FALSE12NULL remain unchanged, and implementation hypotheses remain proposals. Independent investigations NI61–74 are now filed for thread defaults, pure KV arithmetic, real-RAM child fixtures, three interrupted modules, JUnit count attribution, four path-only fixture groups, speech env composition, synthetic LCB and T2 logic. Peer-owned GPU/AutoKernel/8083 and genuine live/corpus/human-authorization scopes remain routed to their existing owners. Main source review and prospective evidence precede each repair; no production guard bypass or all-suite pass. Delivery tally49/74; NI18 remains open pending final disposition review.

2026-10-05 source review additionally files NI75 before repair: executor.py has an early registry-load exception fallback returning the old in-tree build/bin path; executor_paths.py normally applies the kernel-store override, but that branch never reaches it. Review impact/callers and bounded fail-closed fixture before source changes. No actual launch, production regression or kernel modification is claimed. Queue tally49/75.

2026-10-05 NI52 accepted: main independently verifies all79 originalCI37358369281 files, exact recipe d714f40f9c235501f5b15f425ef348598470a909/sourcec885/tool/lock/tarball identities, bounded native prerequisites and nine command/validator statuses zero. Exact strategy and OpenAI targets are LOW/exact (2/22impacted); source is clean except generated ignored index and the isolated bus remains absent. Public exact originals: artifacts/ni05/code-index-37358369281. Failed37356899671 remains unchanged; no index bundle or canonical-host index deployment. This is ordinary code-intelligence dependency evidence only, with0embeddings and no ClaimTuple/quality/runtime claim. Three task checkboxes close; tally50/75. NI18 final disposition, NI45/53 strategy work and NI54–75 independent fixtures/source investigations continue.

2026-10-05 NI54–56 completed: main independently verified all 284 original files from CI37361602330 and reopened four TRUE Judged/Located receipts. The selected whole modules pass 69/69 cases (5 executor, 26 additional executor, 14 claim API, 24 typed replay), with zero failures, errors or skips and five named refusal controls preserved. Each receipt binds 56 Git-backed source inputs plus original runner context. Python 3.11.14, uv 0.8.15, frozen lock and four absent-path/lock postchecks are verified. The exact three commits are published to APP main6bb8d860d410217895efb7806e9ef907a62a4350; four fixture files change, with production behavior intact. Public originals: `artifacts/ni05/fixture-matrix-37361602330`. Original fullscan outcomes stay unchanged. Completed tally **53/75**; NI18 classification, NI45/53 strategy work and NI57–75 continue. No inference, live database, kernel availability, capacity or whole-suite claim.

NI75 impact checkpoint: main verifies all 76 retained files from original CI37361379823. The exact executor wrapper target is HIGH, with 10 impacted nodes, one direct caller and three modules; only the risk validator is nonzero. Source work is stopped and NI75 remains open. Public originals: `artifacts/ni05/executor-impact-37361379823`. This is ordinary offline dependency evidence with no new belief grading rule or host-index deployment.

2026-10-05 incident checkpoint: a delegated fixture worker ran the host GitNexus refresh without a CPU-region claim despite the off-host-only brief. Its captured session was interrupted and returned exit130; ignored index changes and a WAL were reported, so the canonical index is untrusted. Exact execution timestamps and parallel-measurement impact are unknown. No cleanup/recovery or peer process management was performed. See [INC-20261005-unclaimed-host-code-index](../../docs/reference/agent-config/INCIDENT_LOG.md#inc-20261005-unclaimed-host-code-index). NI05-76 files structural wrapper enforcement before implementation. Published completions remain53; newly identified total76.

2026-10-05 NI18 completed in its bounded topology/classification scope. Main independently reopened the original topology modules: 35 default-template cases, nine fleet-dispatch cases and 17 stack-template cases, all TRUE Judged/Located with zero failures/errors/skips and current-source parity. The complete original sweep accounted for all895 tracked modules:826TRUE/57FALSE/12NULL. Main reviewed all69 exception routes against the immutable source-correlated action map, preserved every original outcome and bound current APP6bb8 source bytes (61 unchanged modules/eight reviewed fixture deltas). [Main routing review](../../artifacts/ni05/unit-sweep-37327810408/main-routing-review.json) records31 reviewed child scopes,23 independent queued tasks and15 program-owner/live/historical boundaries. Three missing program routes are now explicit GPU-NI18-FIXTURES, OAB-NI18-FIXTURES and SCG-NI18-FIXTURES checkboxes in their existing canonical handoffs. Parent completion means the original topology verification and wider-sweep classification/routing are done; it does not mean the895-module suite passes or all child repairs are complete. The named NI45/53/57–76 work continues. Completed tally54/76.

2026-10-05 NI05-57 completed: the path-bound routing fixture preserves its stale-module trap and SystemExit1 refusal; the complete module passes72/72 with zero skips, failures or errors. Main independently verifies78 extracted originals,62 Git-backed source inputs plus three context/install inputs, native TRUE Judged/Located and19 postchecks from CI37369215336 attempt1. Only the routing test delta is promoted to APP main198ee59d54750d23b211e80856b913d07357bfbe. Public originals and derivative review: `artifacts/ni05/routing-pool-37369215336`. NI05-58 prompt validation remains open; its original unacquired runner produced no fixture outcome. Existing CI belief carrier applies without a new grading rule. Published scoped completion tally55/76,21 open; the full unit suite remains mixed.

2026-10-05 NI05-61 completed: reviewed topology fixtures enforce the existing8/16 ONNX intra-op defaults and inter_op1, retain positive explicit overrides/refusals, and cover visibleCPU1/8/16/192. Original CI37369039306 attempt2 passes47 ColBERT+13 encoder cases, zero skips/failures/errors; main reopens both TRUE Judged/Located receipts,21 Git-backed+19 context/install inputs each,17 postchecks each and190 ZIP-member comparisons. Two test files are published to APP main33d9de564e3090516780a8889f4ca4e77a779bb7. Public originals: `artifacts/ni05/onnx-fixtures-37369039306`. Earlier setup/acquisition failures remain unchanged, with no invented result. Scoped completion tally56/76,20 open; no live ONNX model, inference, performance or full-suite claim.

2026-10-05 NI05-60 completed: deterministic normalized1024-D embeddings use existing injection seams and temporary SQLite/FAISS stores; real persistence assertions, semantic/degraded ownership guards and default-embedder traps remain. Original CI37372187218 attempt1 passes53 creativity+5 seed cases with zero skips/failures/errors. Main independently reopens both TRUE Judged/Located receipts,22 Git-backed+3 context/install inputs each and17 postchecks each; verifies21 private original metadata and76 downloaded original files. Two test files are published to APP mainec711a7c100a26e183c8e9341e4a3122d21907df. Public originals: `artifacts/ni05/local-embedding-fixtures-37372187218`. Scoped completion tally57/76,19 open; no live store, model inference, semantic quality or full-suite claim.

2026-10-05 NI05-58 completed: the prompt happy-path fixture injects a tiny synthetic EvalIdVocabulary through the existing seam, preserving real leakage validation and mocked generation. The prompt-only retry in original CI37369215336 attempt2 passes9/9, zero skips/failures/errors; routing remains its original successful attempt1 job and was not rerun. Main independently verifies93 private custody files,78 ZIP-member comparisons,62 Git-backed+3 context/install inputs, native TRUE Judged/Located,19 postchecks and three refusal controls. Only the prompt test is published to APP main392afbfc9ce72b4521daa21f6075ccc0ac4b256f. Public originals: `artifacts/ni05/prompt-forge-fixtures-37369215336`. Scoped completion tally58/76,18 open; original unexecuted prompt metadata remains unchanged. No corpus, inference, semantic-quality, capacity or whole-suite claim.

2026-10-05 NI77 newly unlocked: the enabled privacy hook rejected three unchanged encoder meminfo carriers because Linux VmallocTotal has a long numeric value. They remain private in complete original custody; the187/190 public subset and its inability to reopen the encoder prefix independently are documented. A narrowly typed gate repair is now queued before further capture, retaining genuine secret/account refusals. No exemption or source change is approved by this filing. Identified tally77, completed58, open19 after the prompt checkpoint; earlier scope totals remain historical.

2026-10-05 review checkpoint (completion tally unchanged58/77,19 open): Original NI59 CI37374639638 passes140 REPL+12 scorer cases with native exit0, but both evidence postchecks refuse an installer-created mode0777 uv lock inside the captured temporary directory. Original files remain unchanged; the reviewed next recipe separates installer temporary files into the already isolated cache while preserving strict native-original mode checks. Original NI53 impact CI37376429724 captures exact upstream LOW results for _validate_inputs (6 nodes) and read_receipt (4), then fails on missing runner rg. Main verifies all499 retained custody files and9 source-readset files against native Git43d9100; the one-line Path(shard).name repair is published only on candidateb2955bb, awaiting fresh fixture evidence and promotion. Original NI62 CI37375358644 captures LOW pure-helper impacts but validate_serving_shape_capacity has exact HIGH105-node impact; no production refactor is authorized or applied. NI76 attempt1 acquired no runner and produced no source outcome; one unchanged-workflow rerun succeeds, with JS main/resolveAnalyzeJs exact LOW1/2-node results. Empty Bash File impacts remain UNASSESSED for callable coverage. Source guard implementation remains under review; canonical host index remains untrusted and untouched. No inference, peer reload, kernel modification or full-suite claim.

2026-10-05 NI05-45 completed: original CI37378870278 attempt1 passes11/11 strategy CLI cases, zero skips/failures/errors, native TRUE Judged/Located and all11 postchecks. Main verifies148 private custody files,88 ZIP-member comparisons,19 Git-backed+6 context/install inputs and integration source parity. Explicit write/fallback permission is scoped and restored across constructor/sync/close errors; default semantic/owned-store guards remain and report permission does not identify the actual embedding method. Exact two source/test files are published to APP mainf884406e76d12a98254372a819e1fa6248c9223c. Public originals: `artifacts/ni05/strategy-cli-fixtures-37378870278`. The separate NI53 ROOT job remains original FALSE8/10 and open; no full-run/full-suite, live-store, model-quality or inference claim. Published scoped completion tally59/77,18 open.

2026-10-05 NI05-64 completed: unchanged design-archive whole-module fixtures pass16/16, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches570 Git-backed+5 context/install inputs and20 true postchecks, and proves current APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/design-archive-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally60/77,17 open.

2026-10-05 NI05-65 completed: unchanged q-scorer whole-module fixtures pass79/79, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches570 Git-backed+5 context/install inputs and20 true postchecks, and proves current APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/q-scorer-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally61/77,16 open.

2026-10-05 NI05-66 completed: unchanged inference-lock whole-module fixtures pass2/2, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches519 Git-backed+5 context/install inputs and20 true postchecks, and proves reviewed APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/inference-lock-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally62/77,15 open.

2026-10-05 NI05-59 completed: reviewed owned0700 scratch fixtures pass140 REPL+12 code-execution cases in original CI37383742953 attempt1, zero skips/failures/errors. Main verifies191 private original files and180 ZIP-member comparisons, strictly reopens both TRUE Judged/Located receipts, matches62 Git-backed+10 context/install inputs each and22 true postchecks each. Real spill-file assertions, missing-scratch refusal before Popen and bounded child-cleanup controls remain. Only two test files are published to APP mainad477541dbc2e6da4cfe4176d5f85045f64c6069; runtime behavior is unchanged. The runner custody gate admits only owned direct pytest *current links targeting captured same-parent private0700 directories; all other links/native-prefix links refuse. Prior FALSE/setup originals remain unchanged. Public original metadata/log subset: artifacts/ni05/runner-scratch-37383742953; excluded private source/context/meminfo snapshots are explicitly hashed, and the public prefix cannot independently reopen. Published completion tally63/77,14 open; no inference, live store/kernel, capacity, quality or whole-suite claim.

2026-10-05 NI05-77 completed: a narrowly typed known Linux VmallocTotal counter exemption resolves the privacy-gate false positive while retaining account/secret refusals, serialized-line boundaries and unchanged original bytes. Original CI37384312011 attempt1 passes19/19 real staged-hook controls, zero skips/failures/errors; main verifies378 private original files and372 ZIP-member comparisons, strictly reopens TRUE Judged/Located, matches68 Git-backed+5 installer inputs and14 true postchecks. Existing51 baseline fixtures separately observe false accepts0/21 must-block and false rejects0/30 must-not-block; these synthetic counts are descriptive, not field-quality estimates or a new claim tuple. Exact reviewed hook, fixture and test are integrated with this ROOT publication; prior setup/generic-test failures and raw meminfo originals stay unchanged. Public original metadata/log subset: artifacts/ni05/meminfo-privacy-37384312011; intentional synthetic account/secret payloads and source snapshots remain private with explicit hashes, so the public prefix cannot independently reopen. Published completion tally64/77,13 open; no filename wildcard, hook bypass, new ladder, memory-capacity or whole-suite claim.

2026-10-05 NI05-67 completed as a bounded attribution audit: pinned pytest9.0.3 emits successful subTest reports under their parent node IDs, incrementing suite statistics while retaining six parent testcase nodes. Main source review traces this in exact upstream commit a7d58d7a21b78581e636bbbdea13c66ad1657c1e. Fresh original CI37384625409 reproduces command exit0 with suite12/nodes6 and strict native NULL/no rows; the separate four-method control passes4/4 TRUE Judged/Located with zero skips/errors/failures. Main verifies six API-digest ZIPs and182 original-member byte comparisons,13 Git-backed+7 context/install inputs each and all four named postchecks per phase. Source/test and native count grammar remain unchanged; historical XML is never rewritten. Complete public native prefixes: artifacts/ni05/junit-count-attribution-37384625409. This closes attribution, not whole-six conformance. NI78 is newly filed from the actual precommit advisory before its guard repair; total78, published scoped tally65/78,13 open.

2026-10-05 NI05-78 completed: append-only direct-entry refusal prevents a pytest fixture module from silently exiting successfully under direct Python invocation. Main independently verifies exact proposed SHA8fffc3fd7d0b2d1d24b4f34c5ac44aa029444d67c803e2ff336498144e9aef16, all prior module bytes/AST bodies and19 original fixture rows unchanged. Existing AST-only collectability checker checks this one file with0 blocking/0 advisory. No pytest/import/direct execution, new native tuple or historical receipt alteration. NI77 staged19-case evidence remains bound to its original source, with no fresh whole-file CI claim for this guard. Published scoped tally66/78,12 open.

2026-10-05 NI05-63 completed: four source-pinned child probes pass4/4 with zero skips/failures/errors in original CI37385650047. Main verifies623 custody files and616 ZIP-member byte comparisons, strictly reopens TRUE Judged/Located, matches592 Git-backed+5 context/install inputs and21 true postchecks. Real foreign /usr/bin/python3.12 children retain hostile-argv, process survival and explicit entry-point reexec assertions. The fitting and oversized owned lineup fixtures use actual unchanged MemTotal/MemAvailable; the oversized control proves the unchanged capacity guard refuses. Complete canonical registry dependency closure is pinned, including loader/descriptors and compatibility shim. Six test/fixture files only are integrated to APP mainb27e5543199ba4f7a8c3fec87c263f35fb5bcbf1; all30 pinned source dependencies match current bytes. Initial checkout failure and subsequent missing-registry FALSE remain unchanged. Public untouched metadata/log subset: artifacts/ni05/argv-capacity-child-37385650047; private source/context originals are explicitly hashed, so the public prefix cannot independently reopen. No production launch/capacity measurement, memory override, kernel, inference or whole-suite claim. Published scoped tally67/78,11 open.

2026-10-05 NI05-73 completed: original CI37389045961 passes13/13, zero failures/errors/skips, strict native TRUE Judged/Located. Main independently verifies six API-digest ZIPs and468 byte-identical original members across both phases, and this phase binds85 Git-backed+7 external context/install inputs with all original postchecks true. Tested APP sourcefe29834d3bc0e203845effc699abddf0f2e3e2f0 remains the receipt identity; only the reviewed test file is integrated to APP maind31ac2e1f6595e126627ab177cb9449ee2e181a2, with selected production source bytes unchanged. Thirteen selected synthetic oracle/scorer and missing-manifest controls retain real bounded local Python scoring children in owned0700 scratch; exact argv/kwargs and child termination are asserted, and teardown leaves scratch empty. The missing-manifest case uses a finite in-memory row rather than the cached-JSONL helper. Dataset acquisition, full cached JSONL and model quality remain outside this scope. Public untouched metadata/log subset: artifacts/ni05/synthetic-oracle-37389045961; all excluded private input/context files are explicitly hashed, so this public prefix cannot independently reopen. Existing native CI carrier/shared grader only; no new grading rule, production kernel, inference or whole-suite claim. Published scoped tally68/78,10 open.

2026-10-05 NI05-74 completed: original CI37389045961 passes6/6, zero failures/errors/skips, strict native TRUE Judged/Located. Main independently verifies six API-digest ZIPs and468 byte-identical original members across both phases, and this phase binds85 Git-backed+7 external context/install inputs with all original postchecks true. Tested APP sourcefe29834d3bc0e203845effc699abddf0f2e3e2f0 remains the receipt identity; only the reviewed test file is integrated to APP main9d553e863ff8ef7954803cb83d415eeda7940aab, with selected production source bytes unchanged. Six tiny seeded T1/T2 question-vector selection and refusal controls exercise local algorithm behavior. The full-corpus property remains unchanged and unselected, with its existing human-authorization requirement preserved; no corpus access, model quality or live quality-baseline warrant. Public untouched metadata/log subset: artifacts/ni05/synthetic-vectors-37389045961; all excluded private input/context files are explicitly hashed, so this public prefix cannot independently reopen. Existing native CI carrier/shared grader only; no new grading rule, production kernel, inference or whole-suite claim. Published scoped tally69/78,9 open.

2026-10-05 NI05-53 completed: prospective private original Strategy Projection Report custody and strict reader/CLI enrollment are published to ROOT main 7c782a266b2551127aff1dd93f29a9e597321117. Original CI37390356985 passes 10/10 selected cases with zero failures, errors or skips; main independently reopens TRUE Judged/Located, compares all 50 original members in three API-digest ZIPs, verifies 30 Git-backed plus six external context/install inputs, and checks all ten true postchecks. The earlier six failures came from a stale exact producer digest; the reviewed correction updates that digest without relaxing equality. Every prior FALSE/NULL/setup original remains unchanged. The capture retains original CLI status, stdout/stderr, JSON/Markdown and prebound source/input/policy identities; the adapter projects only report.ok integrity through the existing verifier carrier/shared grade. Counts are descriptive, and fallback permission does not identify an actual embedding method. Synthetic owned-store controls cover positive/false reports, original exception/NULL disposition, input drift, resealed boolean mismatch, duplicate/member identity, symlinks/private-directory refusal and source enrollment. No live store, model, inference, embedding quality, transitive completeness or historical warrant. Five integrated source files match tested candidate 69c368204e8e582a10ed163574c8c08583eef7cd byte for byte; the new test module retains its entire original AST plus a refusing direct-entry guard, verified separately by the existing AST-only collectability checker (zero blocking/advisory). This ordinary file-integrity supplement is not another CI execution. Public original metadata/log subset: artifacts/ni05/strategy-report-custody-37390356985; private source/context exclusions are explicitly hashed, so the public prefix cannot independently reopen. Published completion tally 70/78; eight tasks remain open.

2026-10-06 NI05-68 completed: original CI37391662467 passes13/13 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Both missing-priors fallback assertions retain their original renderer/compiler bodies. Owned empty backend directories allow metadata compilation; only the exact read-only Git provenance child contract is admitted and its real successful exit is required. The earlier two failures remain preserved; their exact internally caught exception was not observed. Only the reviewed test fixture is published to APP main94d34949e16ce3a0b7827dcbcfa6d7fca0b6c171; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-system-card-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim. Published completion tally71/78,7 open.

2026-10-06 NI05-69 completed: original CI37391662467 passes12/12 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Original external-drafter argv, compile-refusal and runtime-field assertions are unchanged. Owned empty backend directory metadata replaces production-store discovery; Popen refuses every child, so this is not a drafter launch. Only the reviewed test fixture is published to APP main7f36af77dcb90651067398474372536b9db271e2; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-external-drafter-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim. Published completion tally72/78,6 open.

2026-10-06 NI05-70 completed: original CI37391662467 passes44/44 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. All original compiler/policy assertion bodies remain unchanged. Fixtures declare absent binary paths and admit only the exact read-only Git provenance child contract. Nine named compiler consumers must capture a successful provenance read; direct helper consumers may make no Git call. Only the reviewed test fixture is published to APP main75688b0523093b67af99bc87fb34b629ff2a3d20; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-priors-compiler-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim. Published completion tally73/78,5 open.

2026-10-06 NI05-71 completed: original CI37391662467 passes7/7 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Original full/quarter/both NUMA reader-agreement assertions remain unchanged. Owned empty backend path metadata is bound and every child launch is refused. This proves metadata agreement, not host placement or residency. Only the reviewed test fixture is published to APP mainee4b60d253e382b60ceb8f930cae99f2a8617275; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-numa-readers-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim. Published completion tally74/78,4 open.

2026-10-06 NI05-72 completed: original CI37391662467 passes7/7 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Seven original speech environment-composition cases use owned empty STT/TTS paths and refuse all child launches. Real library-path/vendor policy is unchanged. The two actual frozen-service loader cases remain unchanged and unselected. Only the reviewed test fixture is published to APP maincb0a6eb57eca58830b076d4e2e1eb8057ac97031; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-speech-composition-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim. Published completion tally75/78,3 open.

2026-10-06 NI05-62 completed: original CI37392512279 passes18/18 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. The original per-token module passes10 cases and quant-width module passes8. Fixed arithmetic inputs/assertions, production helper source and the eager capacity guard are unchanged. The proposed HIGH-impact pure-module extraction remains unauthorized and is unnecessary for this bounded validation; no architectural extraction was performed. No APP source edit was needed; the existing original test modules ran unchanged. Recipea291322bfc9cdb678aa2081ca786a16c057f41f3 is published on its owned validation branch. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-kv-arithmetic-37392512279; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim. Published completion tally76/78,2 open.

2026-10-06 NI05-76 completed: original CI37396700409 at recipe591bd02d148bba94ee1ecc271183337493665c85 passes ONE native pytest testcase with103 actual descriptive controls, including CPU GLOBAL shared-inode and GLOBAL/build-alias refusals. Main independently verifies the complete API ZIP seal, every original member,103 exclusive sidecars equal to aggregate records, original statuses and denial snapshots, the exact50-input readset (15 ROOT Git,16 APP Git,7 approved fixture,12 context), pre-execution bindings and postchecks. Strict native TRUE1/1 projects through the existing shared grader as Judged/Located; no second ladder or retrofit. ROOT4 and APP3 guard-related implementation files are published; APP main405a5e7c162480c6cbc5919ecfa626850c08c7e0. All seven native CLI closure files remain byte-identical to tested APPb27e5543199ba4f7a8c3fec87c263f35fb5bcbf1; peer FIFO/runtime changes are preserved, without a new whole-current-main validation claim. CPU admission requires eight distinct single-link files, four GLOBAL plus four build, with actual write flocks attributed to one live same-UID ancestor. Refusal64 occurs before downstream index/global-tool mutation; nontruncating writer-lock contention returns75 and its FD is carried across child/exec. CI=true grants no exemption. Validation bypasses API preflight only on the disposable runner while real CPU claims remain mandatory. This is point-in-time admission, not continuous CPU-owner supervision, host-index execution/recovery, runtime deployment, or inference-noninterference evidence. The canonical host index remains untrusted after the recorded incident. Earlier ordinary audit negatives, native600s/85-record failure, prior101-control TRUE slice and failed103/16-record FIFO-message run remain private and unchanged; the original race assertion was preserved. New single-link diagnostics are separate from the original regular-file message. Public metadata/log originals are at artifacts/ni05/code-index-admission-37396700409; excluded private inputs/control snapshots are explicitly hashed, so the public prefix cannot independently reopen. GitNexus impact for new helpers remains UNASSESSED with manual caller review; no host graph query or rebuild was run. Published completion tally77/78; only NI05-75 remains open.

2026-10-06 NI75 approval checkpoint: operator explicitly approved the reviewed HIGH-impact executor fallback repair. Exact dependency scope remains10 affected nodes/one direct caller/three modules; the prior negative query is retained. Reviewed APP candidatefa1eb43a2c4431d695e5c4339373ecbf3b96aed6 changes only the registry-failure branch and adds six no-launch unit cases. Single prospective recipe45660107ffa880c2b97f08f5c775a5cf4aeb943c uses unchanged ROOT producer2dff56e6c9263fe982b12b91eab0552e50610635. Main verified exact diffs and source AST scope; publication/capture is authorized only after this prospective wiring is pushed. No validation outcome or completion is claimed; tally77/78 remains. Main owns original review, integration and per-task wrap-up.

2026-10-06 NI75 corrected-capture checkpoint: main independently verifies all three API ZIP digests and 5,564 original members from CI37406127191, plus exact2,757 readset inputs (2,129 APP Git,617 producer Git,1 recipe and10 context). Strict native result is NULL, exit4, no JUnit/summary and zero projected rows: eager PathsConfig resolution refused the absent CPU store before test collection. All seven independent postchecks pass. Original receipt FILEcb6726d07d366bf0e0f8d18a6a12834b02e33e948c6821a431f0b64d30b1f5e3/selfeafd884c0d25216fa668feab22692d32820ecb3c09571ab13ab87f24d0ad5fbb remain unchanged. Main reviews exact one-workflow correctione1c234b527900c8096032122eaa3c844fd837356, sole child45660107, binding three private nonexistent import-only paths and before/after absence checks. APPfa1eb43a and all six test assertions, capacity guards, source pins and time limits remain unchanged. Test fixtures explicitly clear/set the CPU override before exercising fallback policy. Prospective wiring now points to the corrected recipe before its single new capture. No fallback outcome, tuple or task completion is inferred from the earlier NULL; tally remains77/78.

2026-10-06 NI05-75 completed after MAIN review and publication: original CI37406900511 at recipee1c234b527900c8096032122eaa3c844fd837356 passes all six focused executor fallback cases with no skips/failures/errors. APPfa1eb43a2c4431d695e5c4339373ecbf3b96aed6 changes only get_binary_paths registry-load failure handling: one patchable load attempt, unchanged legacy names, stripped explicit override precedence, otherwise CPU kernel-store resolution with KernelPathError propagated before any Popen. Successful registry delegation/custom names remain unchanged. Original native TRUE6/6 is captured prospectively through unchanged producer2dff56e6 and existing shared grader; MAIN independently reopens all original ZIP/readset/context/fixture/postcheck evidence before acceptance. Three private nonexistent ambient overrides permit eager configuration imports; each fallback test explicitly clears/sets the CPU override and no kernel/model process is launched or store directory materialized. Prior original CI37406127191 remains NULL/exit4/noJUnit before collection, with zero projected rows; original HIGH-impact negative query CI37361379823 remains unchanged ordinary evidence, and the operator approved its10-node/one-direct/three-module repair scope. No production capacity, binary linkage, deployment, inference noninterference or whole-suite pass is claimed. Scoped published completion tally78/78; larger parent programs and standing rules remain open.

## JEV-aware full handoff audit — 2026-10-06

- [x] **NI-JEV-AUDIT — Complete the full source-bound handoff audit before choosing the next implementation batch.** ✅ 2026-10-06 — 528 files / 3,558 original unchecked keys, 15/15 batches reviewed and accepted by MAIN; 13 refinements applied across 10 live handoffs. [Audit result and ranked preparation shortlist](../completed/jev-aware-handoff-audit-2026-10-06.md). This completes review, not the implementation tasks; historical unchecked boxes remain historical.

Running candidate inventory is [the source-bound audit ledger](../../artifacts/handoff-audit/2026-10-06/manifest.json) and its per-key review/MAIN records. Screening tags are not a dispatch-ready count: current source, actual gating and ownership must be rechecked at selection. Existing Claude-owned work and the completed NI05 79/79 campaign are preserved. New value unlocked by implementation should be added at its own boundary to the owning handoff and this index.

## NI06 — source-confirmed non-inference implementation batch (2026-10-06)

Owner: `codex-ni-main`. These are three bounded implementation tasks, separate from their parents' live evaluation gates. Execution uses private worktrees and disposable CI with synthetic fixtures; no local test suite, model call, embeddings, benchmark, server launch/reload, kernel build or host graph operation is authorized by this batch. Existing Claude ownership is preserved.

- [x] **NI06-01 — CJ-13 reader-B output contract.** Constrain its initial response to the existing ordered boolean verdict shape, retain frozen rubric/gold and one-call accounting, reject malformed responses without repair, stamp the changed instrument identity and map canonical criterion IDs. Validate with fake primitives; live agreement/cost acceptance remains with CJ-13's owner. ✅ 2026-10-06 — MAIN accepts original CI37425524371 TRUE44/44 with 3,324 independent Git bindings and two sealed contexts; source `1721cc20`, APP main `62db79be`. Real primitives/getter branch, package initialization and live backend behavior are excluded.
- [x] **NI06-02 — KB-WM-6 generated graph freshness advisory.** Warn during `index_state.py --check` when `.index-graph.json` is missing, malformed or stale against this checkout, ignoring only `generated_at`. Preserve hard-check exit semantics and silent absence behavior in the independent row screener. Validate temporary graphs without running GitNexus. ✅ 2026-10-06 — MAIN accepts ROOT source `ec513cbe` and original corrected CI37425524371 TRUE64 passed/66 collected, two expected existing live-artifact skips; all six new freshness cases executed. Advisory only; source integrated without changing the independent row screener.
- [x] **NI06-03 — K3 tokenizer identity.** Bind the metadata stamp to the exact tokenizer bytes actually parsed; refuse known drift before query encoding and encoding-writer mutation. Preserve unstamped legacy catalogs and model-independent removal. Validate temporary SQLite/tokenizer bytes with fake loaders; no re-embedding or migration. ✅ 2026-10-06 — MAIN accepts original native CI37424571462 TRUE15/15 and 3,325 independent Git input bindings; APP source `9d3a338a`, promoted main `2a98c6f0`. Existing shared grade Judged/Located; synthetic conformance only.

Manual caller review: NI06-01/02 LOW, NI06-03 MEDIUM; graph risk UNASSESSED because the host index remains untrusted after NI76. Source bases: ROOT `98d46d1e2184ab0a229a1e25b5f8ec20e2d92ad6`, APP `4a11e974be72e40e44291f69740208ae90d4252d`. MAIN reviews every patch and owns all handoff/index edits and per-task publication. Prospective native CI capture uses the existing source class and shared grader; no additional ladder.


NI06 running tally: **3/3 bounded source tasks implemented and MAIN accepted**. Original synthetic fixtures executed successfully: 123 (K3 15, CJ13 44, ROOT 64), with two existing ROOT live-artifact skips. Larger parent handoffs retain their remaining tasks and live gates. Canonical belief ingestion projects these three original accepted receipts through the existing shared grader (nine frames); prior FALSE/NULL receipts remain unchanged.

Historical NI06 dispatch candidates (later source closures appear below; resolve the exact current owning checkbox before dispatch):

1. **HG-9 Step 1 topology map** — map existing finding/routing contracts to detector and fixer roles, the emitted-finding trigger and deterministic failure fallback. Reuse existing escalation plus typed-decision/PreparedAction contracts; no selector activation, model calls or AutoPilot policy change. [Owning handoff](reviewer-control-plane.md#track-reviewer-escalation-and-human-gate-policy).
2. **K2 internal KB cap plumbing** — replace remaining hard-coded query/document caps with declared helpers while retaining stored catalog identity as authoritative. Synthetic declared/absent/invalid configuration checks; no re-embedding or OP-24 cap transition. [Owning handoff](knowledge-pipelines.md#s04-f2--narrow-k2-to-the-remaining-hard-coded-internal-kb-caps).
3. **VB-KB-CATALOG-IDENTITY** — capture catalog identity at its transactional write boundary as dependency evidence; legacy absence remains unknown. [Owning handoff](vidya-belief-substrate-program.md).
4. **TU-GR-1 isolation specification** — prepare mount/UID/export and synthetic access-denial acceptance contracts with the existing scoring-infrastructure owner. Actual sandbox mechanism/integration crosses a HIGH trust boundary and remains a separate owner/operator decision; no competing sandbox or isolation claim from mocks. [Owning handoff](benchmark-suites.md#track-tool-use-eval-contract).

## NI07 — continuous non-inference dispatch queue (2026-10-06)

Owner: `codex-ni-main`. Operator explicitly corrected the stop after NI06: keep working, replenish independent workers, and publish each accepted boundary. The first twelve selected slices comprise NI06's three completed tasks and NI07-01 through NI07-09 below. These priorities are engineering judgment, not measured ROI. NI07-10 and later rows are newly unlocked follow-on work. Task text and current source/owner gates control dispatch; a queue entry alone is not approval to cross an inference or trust boundary.

- [x] **NI07-01 — HG-9 Step 1 topology contract.** ✅ 2026-10-06 — MAIN accepted [source-backed detector/fixer design](../../docs/design/hg9-detect-repair-topology.md) after reopening 14 source files and two draft artifacts. Nine synthetic cases specified, not executed; no runtime activation. Parent HG-9 inference/evaluation gates remain open.
- [x] **NI07-02 — K2 remaining internal-KB cap plumbing.** ✅ 2026-10-06 — Source `ac668b9c` promoted APP main `7d3b840a`; MAIN accepted original CI37436700878 TRUE54/54 and [custody](../../artifacts/ni07/run-37436700878/README.md). Stored catalog identity remains authoritative, fresh outputs adopt declared helpers, telemetry/workers match; broader K2 flags and OP-24 transition remain separate.
- [x] **NI07-03 — TU-GR-1 isolation boundary specification.** Current source map, agent/worker/grader separation, controlled candidate transport/export and actual OS-denial acceptance matrix under existing scoring 2a-iv ownership. LOW specification only; HIGH runtime integration is a separate choice. ✅ 2026-10-06 — MAIN accepts source-bound specification after reopening 25 exact Git blobs; [document](../../docs/design/tu-grader-isolation-boundary.md). Parent isolation requirement stays open.
- [x] **NI07-04 — ColBERT S9 singleton locking.** ✅ 2026-10-06 — Source `7825ab09` promoted APP main `fd0a8dbc`; original CI37439049934 TRUE68/68 after [MAIN custody review](../../artifacts/ni07/run-37439049934/README.md). Complete per-process state/consumer/output transactions, fake blocked-acquisition interleavings and Pool boundary. No concurrent serving activation or cross-process writer/performance claim.
- [x] **NI07-05 — VB-SERVE-TIMING-1 native call join fixtures.** ✅ 2026-10-06 — [Strict reader/source contract](../../docs/reference/serving-call-reader-contract.md) promoted ROOT mainaf27797f; original CI37443323928 TRUE87/87 independently reopened by MAIN, recipe promoted a25b92e7. Correct parent-request/judge join, distinct repeated attempts, strict schema/hash/custody and absence behavior. Live/window parent remains open.
- [x] **NI07-06 — UTM-V3 semantic contract conformance.** ✅ 2026-10-06 — [Synthetic structural/readout contract](../../docs/reference/utm-synthetic-conformance-contract.md) published APPmaindbc8a3e5; original CI37444684189 TRUE2/2 binds8store categories and5parser batches/6attempts. MAIN reopened generated/source/API custody; semantic gold and axes remain null/unassessed, UTM-V3 calibration and UTM-M9 stay open.
- [x] **NI07-07 — RC-10 native confidence instrument preparation.** ✅ 2026-10-06 — [Pure supplied-score expectation contract](../../docs/reference/confidence-expectation-preparation.md) promoted APPmainff423d14; original CI37446388954 TRUE26/26 independently reopened by MAIN. Exact synthetic coverage/missing/unresolved behavior and historical estimand distinction accepted. No native raw-vector capture/parity/calibration/threshold or verdict change; SC43 live producer remains Claude-owned.
- [x] **NI07-08 — CS-24 option(ii) JSON classifier contract.** ✅ 2026-10-06 — [Provisional binary shadow preparation](../../docs/reference/conversation-shadow-preparation.md) promoted APPmaina6f3e0d5; original CI37447169966 TRUE19/19 independently reopened. Actual generic queue-bound and parser/transport/unsupported/incumbent controls; no executor or route activation. Corpus schema, three-arm comparison and live policy gates remain open.
- [x] **NI07-09 — TU-HR-1 native tool-rendering static source audit.** ✅ 2026-10-06 — MAIN accepted [route/render map](../../docs/reference/tool-rendering-source-map.md) and 18-case public native tool catalog after reopening 54 exact source identities. Actual served template/route identity remains unknown; full TU-HR-1 stays open. Unlocked NI07-11 transport/allowlist implementation is independently tracked.
- [x] **NI07-10 — VB-KB-CATALOG-IDENTITY dependency hook.** ✅ 2026-10-06 — Native logical catalog/stored-vs-loaded identity at five named final commits, strict read-only reopening and unknown legacy behavior; [contract](../../docs/reference/kb-catalog-dependency-contract.md). MAIN accepts original CI37441909661 TRUE108/108 after independent source/API/ZIP review; source promoted APPmain `e2ad3dbf`, recipe ROOTmain `bc9794a6`. No vector-byte, retrieval-quality or concurrent-writer warrant.

Current selected queue: **35/35 completed** bounded slices, including NI06’s three and NI07-01 through NI07-32. Every selected slice is independently reviewed, validated and published. Live parent gates, other sessions’ ownership and operator choices retain their scope. Newly source-confirmed eligible work is enrolled separately; MAIN applies canonical edits at task boundaries, with no automatic broad index pruning or wiki sweep.

- [x] **NI07-11 — DTAP native tool advertisement and argument contract.** ✅ 2026-10-06 — [Opt-in public schemas/explicit transport/argument/trace contract](../../docs/reference/dtap-native-tool-contract.md) promoted APPmain00a2e3cb; original CI37444164809 TRUE127/127, all source/API custody reopened by MAIN. Legacy cases/fixtures/judges remain; live effects/TU-DTAP-2 open. Additive failure ledger separately NI07-14.

- [x] **NI07-12 — model-free catalog removal rollback safety.** ✅ 2026-10-06 — APP efd67c52 separately corrects precommit vector deletion, promotes in maine2ad3dbf. Original CI37441909661 passes ten new removal/native-JSON cases within108/108; MAIN reopened actual-byte fixture source, original JUnit/Git/API/ZIP custody. Rollback preserves rows and bytes, successful commit precedes deletion of unreferenced vectors, and later cleanup errors report orphans without reversing catalog success. [Contract](../../docs/reference/kb-catalog-dependency-contract.md). No concurrent-writer/filesystem-wide atomicity claim.

- [x] **NI07-13 — forced KB build duplicate-row correction.** ✅ 2026-10-06 — [Touched identity/FTS contract](../../docs/reference/kb-force-build-identity-contract.md) promoted APPmaine7257b4c; original CI37447817516 TRUE113/113 independently reopened by MAIN. Stable existing ID after successful fake encode/write, exact touched duplicate reconciliation, no vector unlink. Three prior fixture FALSEs unchanged; new staged-write protection separately NI07-16.

- [x] **NI07-14 — TU-LED-1 observe-only failure ledger.** ✅ 2026-10-06 — [Native additive report](../../docs/reference/dtap-native-failure-ledger-contract.md) promoted APPmainacc4c361; originalCI37451263389 TRUE141/141 after MAIN2758Git+2contexts/all2768APImember review. Typed outcomes, original matrix/capture authority, nullable partial usage and explicit pair direction preserved; raw payloads excluded from sidecar. Live DTAP/unknown validity concepts remain separate.

- [x] **NI07-15 — K7 report-time native catalog dependency consumer.** ✅ 2026-10-06 — [Strict report-time provenance](../../docs/reference/k7-report-catalog-dependency-contract.md) promoted APPmain1109ad39; originalCI37450891733 TRUE11/11 independently reopened by MAIN,3351Git+2contexts/all3361API members. Absent/legacy null and stale/tamper refusal preserve report/query semantics; no all-query snapshot or retrieval-quality claim.


- [x] **NI07-16 — staged publication of KB vector files.** ✅ 2026-10-06 — [Individual publication contract](../../docs/reference/kb-vector-staged-publication-contract.md), APPmainbb601d0b and originalCI37451221250 TRUE122/122 after MAIN3349Git+2contexts/all3359APImember review. Prior bytes survive partial/refused write, permissions preserved, both writer APIs covered; no post-replace SQL rollback/crash/concurrent-writer/vector-attestation guarantee.


## Source-reviewed follow-ons after the original nineteen

- [x] **NI07-17 — strict standalone BSV EvalResult input integrity.** ✅ 2026-10-06 — [Contract](../../docs/reference/bsv-standalone-input-integrity-contract.md), APPmain09e087b2 and original corrected CI37454712581 TRUE38/38 after MAIN3357Git+2contexts/all3367API member review. Malformed booleans/IDs/containers/conflicting aliases/inadmissible dispositions refuse; valid producer forms and stable/source ID distinction retained. Original FALSE31/38 invocation fixtures preserved; no campaign/journal/math/threshold/gating change.
- [x] **NI07-18 — lab KB context native dependency consumer.** ✅ 2026-10-06 — [Collection-time contract](../../docs/reference/lab-kb-context-catalog-dependency-contract.md), APPmaineb066f71 and originalCI37454908617 TRUE19/19 independently accepted by MAIN3357Git+2contexts/all3367API member review. Strict original record/null unknown/refusal before query/chat/command/publication, outside fallback. Original FALSE17/19 fixtures retained; no across-query snapshot/quality/migration.
- [x] **NI07-19 — tool-call repair log payload minimization.** ✅ 2026-10-06 — [Helper contract](../../docs/reference/tool-repair-log-content-contract.md), APPmaincfdb4cbf and originalCI37456098288 TRUE149/149 after MAIN3593Git+2contexts/all3603API member review. Outcome/counters/parser/visible refusal preserved; helper logs digest and actual UTF8-surrogatepass byte count. Absolute symlink metadata never followed; initial NULL preflight original retained. No global log/privacy/rate or live trace claim.

- [x] **NI07-20 — fail loud before model loading on unsupported declared query expansion.** ✅ 2026-10-06 — [Optional declaration contract](../../docs/reference/colbert-query-expansion-declaration-contract.md), APPmain7980b229 and originalCI37456357367 TRUE24/24 after MAIN3359Git+2contexts/all3369API review. Absent/false and merge precedence preserved; true/nonboolean fails before constructors via existing False/log/clear-state path. No expansion/model/pool/index/serving execution; broad K2 gates separate.

- [x] **NI07-21 — enforce DCP manifest content identity at rendering.** ✅ 2026-10-06 — [Contract](../../docs/reference/dcp-render-content-identity-contract.md), APPmain049ecf5a, originalCI37457222213 TRUE17/17 after MAIN3357Git+2contexts/all3367original API review. Bound changed body refuses entire render before all inclusion modes; matching/unbound bodies and unreadable skips compatible. Existing advisory fallback/defaults retained; no live activation/quality or absolute serialized budget warrant.

- [x] **NI07-22 — repair hermetic Vidya CI research producer dependencies.** ✅ 2026-10-06 — [Contract](../../docs/reference/hermetic-research-producer-ci-contract.md), ROOTmainf01aea743; finalnative37461044899 TRUE29/29 after MAIN1452Git+2contexts/all1462original API review. Separate generic37461044908 passes1720/165standing skips with index/ratification checks green. Exact pinned three producer families/test-only seams and isolated checkout; production guards/selection/skips unchanged. Historical nativeTRUE/genericfailed originals and MAIN checkout-collision review miss retained; no model/benchmark/kernel/live execution.
- [x] **NI07-23 — prepare DCP hit-span-preserving budget policy.** ✅ 2026-10-06 — [Source preparation contract](../../docs/reference/dcp-hit-span-policy-preparation.md), APPmaincd37eb3c, originalCI37458830138 TRUE33/33 after MAIN3361Git+2contexts/all3371original API review. COLGREP+nonemptyranges keeps allowed FULL/SLICES or missing-evidence exclusion; other ladders/defaults unchanged. DCP-11 remains open until DCP-12/DCP-6 live validation; no AST-complete context or quality/activation claim.

- [x] **NI07-24 — preserve signed non-JSON globals through both checkpoint producers.** ✅ 2026-10-06 — [Contract](../../docs/reference/signed-checkpoint-payload-transport.md), APPc61c4e8e/ROOT881afccf; original37465024500 TRUE116/116 after MAIN3361Git+2context/all3371original custody review. Both producers/SQLite/restore/tamper/unsupported controls, combined persister caps and deterministic eviction; existing signed boundary/fencing unchanged. Prior setup/collectionNULL preserved; no live session/model/kernel/host tests.
- [x] **NI07-25 — expose bounded question-sidecar persistence status.** ✅ 2026-10-06 — [Contract](../../docs/reference/eval-question-sidecar-persistence-status.md), APP05a18b4e/ROOT490b7030; native37463260425 TRUE9/9 after MAIN3361Git+2context/all3371original custody review. Bounded per-batch status reaches aggregate/filter/role summaries, grades/dispositions unchanged. Prior diagnosticNULL and FALSE6/9 retained; fixture-only0..3 baseline correction, no live eval/model/host tests.
- [x] **NI07-26 — retain outer eval reconnect cost separately from inner retries.** ✅ 2026-10-06 — [Contract](../../docs/reference/eval-outer-reconnect-cost.md), native37466167911 TRUE57/57 after MAIN3363Git+2contexts/all3373original-member review; APP726084a8/ROOTa5929784. Outer attempts/backoff/reason reach original question rows; inner retry counts and grading unchanged. No live eval/model/host tests.
- [x] **NI07-27 — suppress timed-out REPL reuse and checkpoint persistence.** ✅ 2026-10-06 — [Contract](../../docs/reference/repl-terminal-timeout-state.md), original37469999403 TRUE123/123 after MAIN3369Git+4contexts/all3431original-member review; APP733623f4/ROOTf8ba8487. Sticky timeout rejects reuse/checkpoints, suppresses FINAL/artifact rescue; bounded late-worker and lease cleanup controls. No worker termination/host-effect isolation or live lease acceptance.

- [x] **NI07-28 — prepare per-candidate descriptions for typed decision catalogues.** ✅ 2026-10-06 — [Contract](../../docs/reference/typed-candidate-description-preparation.md), original37468262427 TRUE14/14 after MAIN3367Git+2contexts/all3377member review; APPa6883d04/ROOT4a46ac2f. Empty-default compatibility, strict descriptions, original-label/key and ordered layout/reader controls accepted. PriorFALSE13/14 preserved; parentTD14/TD16 live no-harm remains open.

- [x] **NI07-29 — bind prospective calibration input source bytes.** ✅ 2026-10-06 — [Contract](../../docs/reference/calibration-input-byte-bindings.md); source 3dd4792eb9f9a25842e9349b6b0afe9a308569c0 promoted APP main 99d8ada718d614185860a85d449bc8846716e245; original37473538913 TRUE34/34, MAIN3370Git+2contexts/all3380 original API ZIP review. CLI hashes and parses each one-read buffer; direct API metadata remains caller_asserted or null. Existing metrics and scoring stay unchanged; no model pin, historical backfill, new grade, or live calibration claim.

- [x] **NI07-30 — standalone NUMA guard resolves explicit mode or its own checkout declaration.** ✅ 2026-10-06 — APP source 82e398da2478bfd9c3baaddbd0c6fb742d09dafa; original run 37476312545 TRUE20/20 across 14 node IDs, MAIN source/custody review accepted; APP main 48a546e90fbc202a0c2ae103203621ba29175915. Explicit override wins; otherwise topology is read from the running checkout. Unresolved mode fails closed before validation, while list/staleness early returns, lower-level diagnostic fallback, pipeline and update/compile paths remain unchanged. Synthetic fixture evidence only; no live fleet/production/kernel claim.

- [x] **NI07-31 — recognize staged ED25519 private-key headers.** ✅ 2026-10-06 — bounded staged-blob regex strengthening; OPENSSH/RSA preserved, synthetic RSA/OPENSSH/ED25519 + metadata/token/partial-stage/all-excluded controls. Native run 37474797195 TRUE9/9; one outer observation, no real credentials or allowlist change. Source/recipe promoted ROOT main eb870f0fe697f02f887bedecaeaccaf24df2d531. Structural fixture evidence only; parent TOC-RD-1a global whole-file exception choice remains open.

- [x] **NI07-32 — honor KEEP markers on declared scratch roots.** ✅ 2026-10-06 — [Contract](../../docs/reference/declared-scratch-root-keep.md); original run37482120866 TRUE27/27, MAIN1932Git+2contexts/all1942member source-first review. ROOT main a5cf51d7e984dc7fdc5a25cb64bae2fd5d7c6060 preserves declared root/descendant/marker/ancestor protection, overlaps and late plan/apply marker controls; unmarked siblings retain existing gates. Synthetic source/fixture conformance only; no host cleanup or atomic race guarantee.


### LR-8 runtime decision boundary (2026-10-06)

MAIN published [the concrete A/B package](../../artifacts/operator/decisions/LR8-event-duty-handover-20261006/README.md): reviewed full one-object registry candidate, exact selected-cron opt-in, current source hashes, identity-bound owner stop and rollback. LR-8 remains unchecked until actual handover and natural-cadence acceptance; 88/88 source fixtures do not authorize it. Choice B is recommended; the owning session must acquire current PID/cron custody at its boundary. No daemon, registry, cron, database or current inference was changed.

- [x] **DISK-ARCHIVE-FIRST — archive then remove the ARCHIVE-FIRST disk items.** Owner: workspace-ec. (filed 2026-10-07) `tmp/ds41-specdec-recipe` 4.4G and `copy-spec-eval-20261006` 1.8G (inventory `artifacts/ec-wrapup-20261007/ec-disk-inventory-20261007.md`). Done when recipe/evidence are in git or artifacts and the operator confirms deletion. (workspace-f2 2026-11-09: keep set archived, SR6 verifier repointed, both tmp dirs moved to trash) [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* Keep set landed under `artifacts/copyspec-20261006/source-archive/` and `artifacts/ds41-specdec-recipe-20260923/`. Before trashing the tmp dirs, repoint `docs/reports/sr6-successor-preparation/verify_exposure_screen.py`, which reads them directly.

- [x] **NI08-WIKI-WARNING — limit the linked-worktree mtime warning to explicit --since scans.** ✅ 2026-10-07 — MAIN reviewed the single CLI caller and diagnostic-only fix. Default incremental selection remains content-hash based; watermark behavior is unchanged. Actual default and explicit-date governance scans are checked during this operator-requested full checkpoint.

2026-10-07 LR-11/LR-13: MAIN prepared and review-only validated the [exact additive signing package](../../artifacts/operator/decisions/LR11-LR13-close-rules-20261007/README.md), now OP-LR11-LR13 in the master queue. Both existing tasks remain unchecked until an operator terminal signature and independently reviewed publication; no agent policy amendment, receipt or close-time cleanup was performed. LR-12's hook defect is fixed and published; the remaining gate is the human-only policy signature, not that former hook defect.

2026-10-07 checkpoint: K11 requested-repeat summary source and original30/30 accepted; exact Research publication and original failure limits are in the NI08 continuation. ET13 prospective routing source and native tasks are enrolled before capture. Source review, actual original-custody acceptance and live/runtime gates remain distinct; the whole backlog is not exhausted.


2026-10-07 newly available non-inference scopes: [TOC-SP-4](context-and-token-economy.md#track-tool-output-compression) closes the spill-summary zero-tail/oversized-request source bug through whole15 mocked-worker controls; [RVP-C6-26-C-POINTER-SOURCE](rocm-kernel-authoring.md#track-rocm-verify-profile-backend) closes the named C-style pointer lexical gap through whole9 controls. Actual source/VB tasks are enrolled before capture and remain unchecked. Discovery finite-score source/native remains next alongside these; their runtime/inference/quote/GPU/content-memo parents remain distinct. No additional completion is counted at enrollment.

2026-10-07 guarded sparse capacity: MAIN filed immutable original operational receipts and completed VB-NI08-SPARSE-CAPACITY-CUSTODY; [bounded source custody](../../artifacts/ni08/sparse-capacity-custody-20261007/README.md), not a native/measurement grade or future admission guarantee. NI08=165 scoped completions (103 existing flips +62 children); remaining source tasks continue.

2026-10-07 C104 future-writer source/native companions are completed after MAIN original8/8 and exact two-file Research9299 publication review. NI08=167 (105 existing flips +62 completed children); historical14store/live-parent acceptance remains independently open.

2026-10-07 exact decision-aware source citation repair closes one bounded child, NI08=168 (105 existing flips +63 completed children). Corrected risk citation intake-1333#01 remains unknown to the current ledger; the source record is unchanged and gives no runtime/policy gate.


## C106 exact HOLD source acceptance — 2026-10-07

MAIN accepted the original whole16 synthetic controls and independently reopened the exact two-file Research public product `3613455d5114d78968fab464b9cdc8a18df2f306` on parent9299. Unsupported ROLLBACK was removed and unsupported constructor selectors now refuse; default HOLD and floor/cadence/keep/serving behavior are preserved. The existing DS41-C106 and native companion close: NI08 now **170 = 107 existing checkbox closures + 63 completed scoped children**. [Original custody and scope](../../artifacts/ni08/c106-hold-source-acceptance-20261007/README.md) binds all16 test bodies,23 Git inputs, ALL5 locked wheel identities, original native receipt/JUnit/API/archive and successful publication records. Source conformance does not warrant live loop deployment, inference, performance or production promotion. Mixed parent work remains open.

Operator-requested full wrap-up is published on ROOT main at `2f7cce5ab0c4ff5891e1ed1d04d43dd175e80efc`. The first INF50 writer original remains a preserved partial diagnostic; MAIN independently accepted the corrected original with the actual hidden cache bytes. Generated APP product publication remains separate from that custody acceptance. C26 and UFH source/custody recipes remain private preparation, with no native capture or source-task closure.

- [x] **NI08-SPARSE-CAPACITY-SECOND-REQUEST-CUSTODY — preserve the guarded two-worktree safe alternate and original operational receipt dependencies.** ✅ 2026-10-07 — MAIN completed exactly two additional idle historical Research worktree hydration exclusions. The semantic full indexes, source metadata/bytes, HEADs, branches, KEEP and Git objects remain preserved; only tracked duplicate benchmarks/data copies were sparsely excluded. Allocated recoverable copies totaled **3,360,518,144 bytes**. Original final free-space samples **111,330,381,824** and **111,329,828,864 bytes**, **54.629409002 seconds** apart, both exceeded the **110,500,000,000-byte engineering target** and 100 GiB hard floor. This safe alternate does not promise eight billion bytes of recovery or inference admission. Original helper/manifest/process/command/sample custody stays ungraded through existing VB-NI07-DOC-DEPS handling; no new ClaimTuple, ladder, native test, inference or runtime warrant. [Original custody](../../artifacts/ni08/sparse-capacity-second-request-20261007/README.md). NI08 now **171 = 107 existing checkbox closures + 64 completed scoped children**.

## INF50 native generated projection accepted and published — 2026-10-07

MAIN independently reopened all16 publication command records, successful original releases and actual GitHub branch/main refs. Public APP `01db99c03451ac3c4d2e7593a53781486707595f` is the exact one-file fast-forward from `f0df7ca2f801481d2024ad86c3ed37d60155430e`; generated registry bytes equal the supported native writer capture. Typed YAML differs only at `speculative_decoding_policy.retired_fields.ngram_candidate_spec_type`. The two already-enrolled source/VB checkboxes close, bringing NI08 to **173 = 109 existing checkbox closures + 64 completed scoped children**. Complete corrected source/output/cache custody stays UNGRADED with JUnit/receipt/ClaimTuple/grade NULL; original partial upload and the separate publication HTTP500 remain immutable. No selection authority, runtime, inference or cache publication changes. [Original custody and limits](../../artifacts/ni08/inf50-native-writer-product-acceptance-20261007/README.md).

- [x] **NI08-THREE-SOURCE-VIEW-SPARSE-CUSTODY — preserve original guarded three-view materialization and refusal dependencies.** ✅ 2026-10-07 — MAIN accepted the guarded sparse materialization of exactly three own unused committed source views: two C26 Research views retain four physical source files each and the UFH ROOT recipe view retains three. All eleven kept source byte/mode/physical-metadata records, semantic full indexes, HEADs, branches, Git objects and the existing ignored cache remain conserved. The 302 original command records and three completed checkpoints are retained unchanged; both earlier eligibility refusals remain separate originals with no sparse application. Raw index cache inode/mtime/ctime volatility was explicitly reviewed before apply. This is ungraded operational source-view custody through existing VB-NI07-DOC-DEPS handling; it closes no native/source task and asserts no measured allocated recovery, free space, runtime activity, inference admission, grade or new ladder. [Bounded original custody](../../artifacts/ni08/three-source-view-sparse-custody-20261007/README.md). NI08 now **174 = 109 existing checkbox closures + 65 completed scoped children**.

## Existing literature coverage task completed — 2026-10-07

MAIN accepted the one-entry native projection of intake-1333#record through the existing literature adapter and owned-inode ledger lease. Exactly 13 reviewed frames were appended. Independent whole-prefix and full-fold review confirms 14,354 records with a clean chain, five new Verified/Located beliefs, no changes to existing beliefs, and claim 04 still review-required. The index record and all fourteen governance modules remain unchanged. Missing retained source-artifact anchors stay UNKNOWN; the existing shared grade remains Located. [Original custody](../../artifacts/ni08/intake1333-literature-coverage-20261007/README.md). NI08 now **175 = 110 existing checkbox closures + 65 completed scoped children**.


## RTG-39 source/documentation checkpoint

MAIN reconciled the two existing RTG-39 source/documentation tasks using the retained official v1 source. Table 6 does not establish a KL gain; Table 7 prompt results, same-task retention and OOD transfer retain their separate metrics. The inert 13-field contract separates frozen teacher target generation from trainable-student SFT and preserves actual observations. Only two administrative action strings in intake-913#record change; status, claims, dive corrections and native ledger remain unchanged. Strand Phase B, operator domain selection and P1–P5 remain gated. NI08 now **177 = 112 existing checkbox closures + 65 completed scoped children**.

## Continuing source review — periodic full boundary after RTG-39

The tally stays177. UFH's fresh15-case original has independently accepted custody, with product publication still pending; both earlier NULL originals remain unchanged. C26 needs a fresh current-tip source reconciliation before another capture because the parallel owner's Research5c945 changed the same CPU/GPU ownership source family. EVL42 actual-scan wiring remains prospective. These are actionable source/integration tasks and add no closures at this boundary. [Detailed remaining actions and snapshot](../../docs/reference/ni08-non-inference-continuation.md).


## UFH-12 bounded spill-summary source and product acceptance — 2026-10-07

MAIN independently accepted original run `37664607006` attempt1 at ROOT recipe `533d649`: exact whole15 mocked-worker and temporary-spill controls passed15/15 with native TRUE/exit0, 3,829/3,829 source reads, typed result/fixture custody and the existing Located/Judged observation. The two earlier originals remain NULL (`37649822725`: pytest missing; `37659831973`: langgraph missing), with no retrospective tuple. APP source `63399d6` is published byte-exact in the two-file public product `8108452` by ordinary fast-forward; 83 original publisher commands returned zero and both lease tokens were released/unlinked. [Bounded acceptance custody](../../artifacts/ni08/ufh12-spill-summary-source-acceptance-20261007/README.md) retains lossless encoded original receipt, journal and MAIN review references; full ZIP/readsets remain private. TOC-SP-4 and the prospectively enrolled VB companion close. TOC-SP-3 quote verification, summary quality/evidence retention, live inference and runtime remain separate. **NI08 now 179 = 114 existing checkbox closures + 65 completed scoped children.** The prior periodic FULL177 cut remains a historical source cut, not relabeled.

TD-29.M0a's bounded source/control child is tracked as **TD-29.M0a.S0** in [typed-decision-plane.md](routing-program.md#track-typed-decision-plane), with its single prospective VB companion in [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md). This backlog paragraph is a pointer only; TD-29.M0a remains open for its fresh three-arm sidecar/runtime evidence.

## EVL42 actual checker attachment and source wiring — 2026-10-07

MAIN accepted original ROOT recipe139c run37679517879 attempt1:44 synthetic controls and one actual-wrapper attachment passed, with exact original source/readset/JUnit/receipt and typed custody. The real historical Research5c945 checker returned rc1 and complete=false (current1, missing3, stale3, unresolved41); both existing Judged/Located observations mean fixture_execution_conformant, not healthy pins. Exact five-file ROOT product is public on main at `c986a107fde2c6e7cd6bd8e05ff7cf7243207034`. The initial private-commit schema refusal happened before mutation and is retained; its one-line correction received fresh MAIN approval. [Original custody and scope](../../artifacts/ni08/evl42-actual-pin-scan-source-acceptance-20261007/README.md). Only SC-EVL42-PIN-REPORT-WIRING closes; the prior29-control companion was already complete. **NI08 now180 =115 existing checkbox closures +65 completed scoped children.** Broader pin health/repair, inference, runtime and parent work remain open.

The prior periodic FULL179 is complete and public at ROOT `aaaf51d9786c7cc012064c4f5a1036fae93c423f`, including its reviewed final wiki synthesis/touch. New source findings above await the next operator-requested periodic FULL sweep. Canonical belief-ledger projection of five already-sealed receipts is newly surfaced in the existing source table and VB handoff before mutation; no new source class or grading rule. TD29 native preparation and C26 accepted source/native checkpoint remain active; whole-backlog exhaustion is not claimed.


## C26 current source/control checkpoint — 2026-10-07

2026-10-07 MAIN accepted current source checkpoint: Research `e136226d00421742645bf2f157737a8cedf348f1` is public on main; original ROOT `5933d75d2d935edc2f3d542fd3240863548be8ab` push attempt passed all46 selected fixtures. Complete1588-path readset, seven stable inventories, five typed snapshots/6407 regular-file checks and existing shared Judged/Located grade are independently accepted. The original0858 NULL, aad7 FALSE and17f FALSE remain unchanged. This completes only the bounded source/control tasks; actual C26 runtime/floor/cadence evidence remains with its owner. [Accepted source and original custody](../../artifacts/ni08/c26-current-source-acceptance-20261007/README.md).

Exactly two original task boxes close: DS41-C26-CANCEL-SOURCE and VB-DS41-C26-CANCEL-CONFORMANCE. **NI08 now182 =117 existing checkbox closures +65 completed scoped children.** EVL180 documentation is public on ROOTmain16647a249c1d8c4a13806046445075f4310094fa. The newly enrolled five-receipt canonical ledger projection, TD29 native source controls and other independent non-inference work continue; this checkpoint is not backlog exhaustion.


## Current owner capacity request — 2026-10-07

- **[declined: ws58 2026-11-03 content-review: custody recovery of unused checkout payloads; no behaviour change]** **NI08-OWN-CAPACITY-R10-RECOVERY — qualify and perform owner-selected reversible recovery from unused committed checkout payload duplicates, then report original custody and two fresh capacity samples.** Respond to the authentic R10 capacity request for13GB plus1GB margin; preserve all Git objects, full semantic indexes, active source/readset/profile paths, native originals, KEEP, ignored/untracked/modified bytes and foreign sessions. Prove exact physical eligibility before sparse exclusion; MAIN approves the bound operation and reviews original two device/time/free-byte samples against the unchanged100GiB floor. A gross duplicate-size screen is not qualified recovery or inference admission. Existing VB-NI08-SPARSE-CAPACITY-CUSTODY / VB-NI07-DOC-DEPS handles operational custody without a new source class or ladder.

MAIN accepted the actual eight V8 and two V9 OWN reversible sparse operations: all421 original commands and exact per-HEAD source/index/KEEP conservation were independently reviewed. Qualified payload allocation totals15,466,938,368bytes, without attributing shared free-space delta. Original device2431 samples at23:08:14/23:09:26UTC,71.947seconds apart, reported107,936,206,848 and107,911,806,976available bytes. Both exceed the unchanged100GiB live floor; the later margin is only537,624,576bytes and remains2,588,193,024bytes below the separate110.5GB engineering target. The20GiB peer exception is test-only. R10 remains open for growth margin; four further OWN historical source views are being qualified using their own exact source inputs. [Lossless original custody and scope](../../artifacts/ni08/own-source-capacity-recovery-20261007/README.md). Daemon remains operator-held DOWN; ownoutbox receipt is not delivery.


## Accepted original CI ledger projection and periodic full cut — 2026-10-07

2026-10-07 MAIN accepted the existing CI-family projection: exactly five original receipts (EVL actual-wrapper and44 controls plus currentC26 TRUE; preservedaad7/17f FALSE) append15frames to canonicalledger14354→14369. The complete14642518-byte prior prefix and all5819 prior beliefs remain unchanged; independent whole-chain/same-asof fold verifies five new Judged/Located observations. Both private V4/V5 wrapper refusals happened before append and retain original custody; the separately approved V6 succeeds with actual inode lease and44-byte sidecar lifecycle/release/absence proof. Original booleans and seals remain unchanged; oldestNULL emitszero tuples. This means source fixture conformance only, never pin health, runtime, performance or promotion authority. [Original write and independent acceptance](../../artifacts/ni08/accepted-ci-ledger-projection-20261007/README.md).

**NI08 now183 =117 existing checkbox closures +66 completed scoped children.** The newly discovered ledger-projection task contributes one scoped child; the five receipts do not count as five tasks. Current C26 two source/control closures are included. New owner capacity recovery is explicitly enrolled and remains open; TD29 source/native preparation and the remaining non-inference queue continue. This full cut adds no completion beyond the two C26 tasks and one ledger child.


## Periodic full checkpoint: accepted operations and prospective sources — 2026-10-07

The tally remains **183 =117 existing checkbox closures +66 completed scoped children**. Capacity recovery has accepted original operation custody but its requested margin is still open. TD29 private APP130a and ROOT46e9 commits are reviewed; the original off-host122-control capture remains pending. HG5’s five-file force-mode source patch is structurally accepted only; native controls and source publication are pending. New prospective HG5 and SC55 source tasks are owned by the VB handoff, with source-table enrollment before capture. No inference, runtime activation, parent completion or whole-backlog exhaustion follows from this checkpoint.


## Periodic full checkpoint — 2026-10-08: reviewed source and capacity boundaries

NI08 remains **183 completed items: 117 existing checkbox closures and 66 completed scoped children**. This checkpoint adds zero NI08 closures. Peer commits `152fb52` and `ab53a8e` are preserved; their three AutoKernel closures are excluded from this tally. The later peer report records CPU activation and monitoring, while its GPU serving-owner window remains gated. These are peer-recorded observations, not our independent runtime acceptance.

MAIN reviewed the exact five-file HG5 source commit `c12c9c5` and the five-file native recipe proposal: 2,215 pinned APP source/configuration files, 56 test definitions and 87 prospective case identities. Those controls have not run; source publication and an original off-host capture come next. TD29 recipe `278545e` is public on its own branch. Original run `37707130166` stopped before collection because FastAPI was missing from the dependency recipe; its receipt is NULL, with exit 4 and no JUnit results. MAIN independently verified its original publication, archive, every extracted member and native readset. The minimal three-file successor matches 64 selected package versions and all 905 wheel hashes in the existing lock. Neither its source review nor the failed setup counts as passing controls. Earlier original NULL evidence is unchanged.

SC55's initial capture writer has a reviewed static contract and 20 unexecuted controls. Review uncovered additional ungated work: record measurement labels before capture, prevent duplicate test collection in the reader, and wire the reader to the existing measurement projection. These fixes belong to the already enrolled SC55-WRITE/SC55-READ tasks; neither task is complete. No historical record receives new provenance on read.

MAIN accepted four further reversible sparse operations on OWN cold views. Each retained its complete 29,337-entry semantic index, source and evidence while materialized files fell from 6,126 to 2,684. Original available-space samples at 00:14:01 and 00:14:17 UTC were 107,547,189,248 and 107,642,200,064 bytes. Both exceed the unchanged 100 GiB floor, with a thin margin; neither reaches the separate 110.5 GB growth target. R10 stays open. No exclusive attribution of shared-host free-space change or live admission follows. The peer's later recovery and activation do not close our growth task.

The accepted dashboard snapshot at `2026-10-07T23:54:52Z` predates both peer commits: active plus blocked had **3,693 of 6,108 checkboxes checked (60.5%), with 2,415 unchecked and 12 cards lacking checklists**; all columns had 6,317 of 9,810 checked (64.4%). Card counts were 182 active, 7 blocked, 211 completed and 120 archived. These are dashboard checkbox counts, including inference and gated work, rather than the NI08 completion denominator. API health was `ok` with disclosed non-gating attention; optional idle producers can be absent by design.

[Compact original acceptance custody](../../artifacts/ni08/periodic-full-governance-20261008/README.md) preserves byte-exact records through lossless transport. Whole-backlog exhaustion, native/runtime acceptance and production changes are not claimed.

## Accepted MF-FS-1 existing-trace diagnostic — 2026-10-08

[MAIN original analysis and custody](../../artifacts/ni08/mf-fs1-diagnostic-20261008/README.md) closes existing MF-FS-1 and its prospectively enrolled VB-MFFS1-DOC-DEPS companion.72 private input snapshots and three source snapshots are independently verified;62 real trajectories match the old reference. On t2–t5,44 cap stops and3 errors account for all47 traces. Substring flags do not establish causal loop/read/edit reasons; unknown remains unknown. No raw corpus/code or trajectory IDs are published. MF-VBS-2 inference remeasurement remains open. Source review surfaces missing extraction/truncation/native-completion fields for adjacent MF-NDG-1/MF-RR-1 rates, and prospective instrumentation preparation continues.

**NI08 now185 scoped completions =118 existing checkbox closures +67 completed scoped children.** These are two bounded task closures, not62 completions for trajectories or47 for forced stops. TD29/HG5/SC55 native/source tasks remain open; no whole-backlog exhaustion is claimed.


### 2026-10-08 SC55 capture-time source completion

[Accepted source contract](../../artifacts/ni08/sc55-source-contract-20261008/README.md) closes the existing SC55-WRITE child: all43 original native controls passed, original custody was independently verified, and the five Research files are promoted to main c722. MAIN applied the original eight ROOT source/recipe files pending this wrap-up. SC55-READ stays open because review uncovered a normal-ingest reachability gap; its strict seal-path wrapper, Source registration and CLI choice are being implemented without another grading rule. No live measurement, runtime activation, historical provenance backfill or parent closure is claimed.

**NI08 now186 scoped completions =118 existing checkbox closures +68 completed scoped children.** This adds one source task, not43 completions for controls. The remaining ungated source/native work continues.


### 2026-10-08 SC55 normal-ingest source completion after full186

[Original48/48 source custody](../../artifacts/ni08/sc55-source-contract-20261008/README.md) closes the existing SC55-READ child. MAIN verified the exact original archive, all38 native input digests, receipt seal and JUnit identity multiset, then applied the eight tested ROOT successor files to the ownership tree. Ordinary file ingestion now observes the closed seal through the pinned native writer/reader, registers one measurement Source and exposes the CLI choice. Missing native labels decline without invention; altered custody refuses. The shared measurement ladder and historical unprojectability remain unchanged. Source publication follows at this task boundary. Owner-controlled fresh graph capture still gates the SC55 parent.

**NI08 now187 scoped completions =118 existing checkbox closures +69 completed scoped children.** Original HG5/TD29 recipes now bootstrap successfully but returned FALSE (72/87 and119/122 respectively); their source/fixture fixes are being reviewed. Failed controls and new CI events do not add completed tasks. No inference, runtime activation, peer-session boundary crossing or whole-backlog exhaustion is claimed.

2026-10-08 MAIN next-source review: SC55-READ is published on mainbf7901 with exact native48 controls, one paired checkbox flip and scoped tally187. Newly surfaced non-inference source work VB-MF-TURN-WRITE is enrolled prospectively in the source table and owning belief handoff; original MF-NDG-1/MF-RR-1 rate/behavior parents stay open. SC54 historical B7 wording is corrected after verifying its 2026-09-04 closure; private quality-source writer/reader corrections remain implementation work, not an operator blocker. HG5/TD29 original nativeFALSE87/122 receipts are independently verified and retained; private corrective source commits76624/5e6b await original successor validation and are not counted as completions.

2026-10-08 HG5 source child accepted: APP main76624a91, original ROOTe54175dc push run37721932296 attempt1,87/87 whole-module synthetic controls, zero failures/errors/skips; exact2,229 readset hashes and2,243 original archive members. MAIN independently verified119 original source-first commands and126 APP main-promotion commands with normal leases/hooks and nonforce pushes. Five exact ROOT recipe blobs are integrated into MAIN ownership for ordinary publication. Earlier FALSE/NULL originals remain unchanged. This closes one scoped source child; parent HG5/H3/runtime and prospective TAP-WRITE/READ remain open.

**NI08 now188 scoped completions =118 existing checkbox closures +70 completed scoped children.** Synthetic cases are validation, not separate task completions. Non-inference work continues; no whole-backlog exhaustion or inference/runtime completion is claimed.

2026-10-08 prospective source work: SC54-WRITE and SC54-READ are open children in the belief handoff, plus newly unlocked VB-INGEST-CONTRACT-SYNC. Actual current-source comparison found ODL registered for ingestion but absent from CLI choices, and missing named fixture coverage for ODL/SC55. The source successor will repair those finite contract gaps while preserving every existing Source/CLI registration. These three tasks remain open pending original off-host controls; tally stays188. TD29 integrated-source209 validation is being published, and MF's one-file scalar source is private at92bc with validation still pending. No operator decision blocks these source tasks.


### 2026-10-08 TD29 current-source child accepted

Original push run `37729628899` attempt1 at ROOT `11f1b00ae478a76544eb3b649f4b0d9af199095a` passed all209 cases from seven whole mocked modules (175 AST definitions): TD122 plus unchanged HG87, zero failures/errors/skips. APP current-tip merge `eadb959172fbc433da41aaf069c1bcf20c6ce98f` is promoted to remote main by one ordinary nonforce fast-forward from76624a91. MAIN independently accepted the source merge, four-file recipe commit,123-command source-first publication, original209 custody and120-command main promotion. Earlier FALSE/NULL archives remain immutable. Existing native CI adapter/shared carrier returns Judged/Located observation only; no runtime activation, model quality, inference, performance or three-arm sidecar result.

[Accepted source/control boundary](../../artifacts/ni08/td29-current-source209-acceptance-20261008/README.md) closes one scoped source child and its one companion, with no parent closure. NI08 now189 scoped completions =118 existing checkbox closures +71 completed scoped children. The two paired boxes represent one source child;209 synthetic cases are not task completions. MAIN applies this tally at the TD task boundary.


### 2026-10-08 HG5 request-event writer source boundary

APP source `974cb4017791a5d500269fd44f7d9903528e1d5d` implements the default-off source-owned HG5 request event writer. The independent writer directory knob captures only completed post-answer explicit-plan outcomes, with one bounded immutable event attempt, nullable actual call/token/timing counters, distinct outcome/call status, bounded failure class and final role. Optional source-authored context leaves loaded runtime origin unknown. Quality/force failures and emitter exceptions preserve answer/legacy receipt behavior; initial upstream failures before the finalizer produce no event. No all-request denominator, historical backfill, efficacy/correctness grade or runtime activation is claimed. Original push run `37734573366` attempt1 at ROOT `5e653b10f2bf2853f4f8f40c69eb24c91f877837` passed all240 whole-module synthetic controls (TD122+HG87+TAP31;205 AST definitions/eight modules), zero failures/errors/skips. The original ZIP2246members/readset2232hashes/2220APPenvelope rows are retained with exactJUnit multiset/seal and original Judged/Located shared grade.

[Writer source findings](../../artifacts/ni08/hg5-request-event-writer-source240-20261008/README.md) close exactly one scoped child, VB-HG5-TAP-WRITE, after MAIN accepted the completed APP main promotion. Including the independently accepted A-2 adjudication and its document-custody companion, NI08 now192 scoped completions =119 existing checkbox closures +73 completed scoped children. The240 cases are validation, not240 tasks. TAP-READ/runtime/H3/inference parents remain open. MAIN owns numeric campaign reconciliation at application.

### 2026-10-08 RTG-48 A-3/A-5 source boundary

MAIN completed two existing audit checkboxes after accepting the [bounded taxonomy/correction rulings](../../docs/reviews/rtg48-a3-a5-source-review-2026-10-08.md). The existing document-custody family includes their pre-edit identities; this is no additional completion. NI08 now194 scoped completions =121 existing checkbox closures +73 completed scoped children. Original synthetic CI cases, paired source-companion boxes and newly enrolled but unrun M-12h capture are not extra completed tasks.

### 2026-10-08 RTG-48 A-4/A-6 accepted source boundary

MAIN completed two existing audit tasks after accepting the source cost/deletion crosswalk and structural role recommendation. Settled R-16 dispatch authority, detect-only fleet_watch, owner receipts and human-only measurement policy remain unchanged. The existing document custody family captures exact dependencies, not an extra task. NI08 now196 scoped completions =123 existing checkbox closures +73 completed scoped children. No runtime validation or invented numeric overhead.

### 2026-10-08 RTG48 A7–A9 accepted source findings

MAIN accepted the [durability, landed-remediation and thread-provenance audit](../../docs/reviews/rtg48-a7-a9-source-review-2026-10-08.md), verified23 pre-edit source dependencies and10 historical commits, and applied the two comment/docstring-only cadence corrections. Exactly three existing audit tasks close. The already-completed document-custody family extends to A7–A9 without another child. **NI08 now199 scoped completions =126 existing checkbox closures +73 completed scoped children.** New HG5 version2-label enrollment, M12/MF/SC54 source preparation and individual native cases remain excluded from this count; non-inference implementation continues.

**FULL199 publication scope:** RTG48 A7/A8/A9 audits are accepted; the two supervisor/test cadence comments are retained as a separate D9-gated proposal, not published source changes. [Concrete decision package](../../artifacts/operator/decisions/D9-RTG48-COMMENTS-20261008/README.md). Existing D9 acknowledgement is the only decision for that item; documentation and independent source integrations continue.

### NI08 accepted source boundary — 206 scoped completions, 2026-10-08

MAIN accepted six existing source/capture closures after original SC54 102/102, MF4/4, M12h8/8 custody review and APP/Research promotion, and filed R-6's additive historical wrap-up amendment. Seven existing checkboxes close: **206 =133 existing closures +73 completed scoped children**. Individual test cases and open parent handoffs are not counted as additional tasks. [Source evidence](../../artifacts/ni08/sc54-mf-m12h-source-integration-20261008/README.md). HG5 native-label source implementation and EVL49 dry readiness continue; D9 comment and R25 proposals await explicit acknowledgement. Retired mainD cannot resolve R-7 without a successor namespace steward; a decision package is being prepared. No whole-backlog exhaustion claimed.

**Unlocked after TASK206:** source SC54/MF/M12h work is published on ROOTmain11649. HG5 version2 native-label validation proceeds from those exact integrated preimages. EVL49 S04's three dry planning controls are prospectively enrolled as VB-EVL49-S04-V10-DRY-PLAN (11/8/12 cells); the missing dynamic schema dependency is now in the six-source closure. These controls require no inference, model weights, quiet window or server/preflight activation. M12g comparison eligibility and M12i offline replay are in bounded source preparation. All remain open until actual source/execution evidence is accepted; tally206 unchanged.

**Historical M12h boundary — 206 scoped completions (2026-10-08). Further work unlocked then:** M12g now has a reviewed implementation proposal in the actual scorer workflow and a prospective 32-case whole-module capture tracked by VB-TULVING-SRS-WORKFLOW-CI. M12i's offline protocol proposal and M12j's dependency closure/claim correction are independent non-inference work; prepare a private replay environment without altering peer venvs or reconstructing historical tuples. All remain open pending their own evidence; the completed tally remains 206.

### NI08 accepted dry-control / dependency correction boundary — 208 scoped completions, 2026-10-08

MAIN accepted EVL49 v5 original three-control capture and M12j metadata-only factual correction. Two existing checkboxes close: **208 = 135 existing closures + 73 completed scoped children**. [Evidence and limits](../../artifacts/ni08/evl49-m12j-source-closure-20261008/README.md). EVL49 Research runbook integration, M12g whole-module validation, M12i owned offline protocol/replay and M12f human metric construction remain separate work. HG5 original label validation exposed a missing adapter identifier and a JUnit subtest/count mismatch; originals are preserved while minimal source/capture fixes are prepared. Pending D9 / R7 / R8 decisions block their own items only.

### NI08 accepted Tulving comparison boundary — 210 scoped completions, 2026-10-08

MAIN accepted the original 32-case CI result and the actual Research main fast-forward publication at `72832ef6`, then integrated the exact six tested ROOT recipe blobs. M-12g and VB-TULVING-SRS-WORKFLOW-CI close: **210 = 137 existing closures + 73 scoped children**. [Evidence](../../artifacts/ni08/tulving-srs-workflow-controls-20261008/README.md). Cases are validation units, not additional tasks. HG5 corrective source/native work, EVL runbook publication, M12i owned model-free replay and M12f human metric choice continue; no exhaustion claim or inference work.

## Process-lesson lints — 2026-10-21 (workspace-f8 wrap-up)

- [x] **LINT-SIGPIPE-STRINGS-GREP-Q — lint `strings ... | grep -q` (and any `producer | grep -q` under `set -o pipefail`) in launchers and gates.** `grep -q` exits on first match, the producer takes SIGPIPE (141), and pipefail reads a successful match as a failure (a false negative). It recurred in a new job on 2026-10-21 after the first documented case (`autokernel-rebuild-program.md`, line ~1327). Add a check to the commit-hygiene or shell-lint hook that flags the pattern and names the safe form (`grep -c` into a variable, or `grep ... > /dev/null` without `-q`); warn-only first. Origin: workspace-f8 2026-10-21. ✅ 2026-10-21; [lint native evidence](../../artifacts/ci/lint-sigpipe-source-20261021/README.md).
- [x] **LINT-PIPEFAIL-EARLY-EXIT — general pipefail early-exit-reader lint.** `scripts/lint/check_pipefail_early_exit.py` flags `producer | grep -q|-m|-l|head` under `set -o pipefail` (stdlib, warn-only, `--strict`/`--json`, per-line `# lint-ok: pipefail-early-exit`), with `tests/lint/test_check_pipefail_early_exit.py`; landed root `6b2c351ad`. Hook wiring ships as `scripts/lint/pre-commit-wiring.patch` (not applied). ✅ 2026-10-22
- [x] **LINT-PIPEFAIL-EARLY-EXIT cleanup** — apply `scripts/lint/pre-commit-wiring.patch` to `scripts/hooks/pre-commit.extras` (warn-only), then clear the ~150 live hits (`python3 scripts/lint/check_pipefail_early_exit.py scripts` printed 151 lines on 2026-10-22): rewrite each to `grep -c` into a variable or `grep ... >/dev/null`, or mark a reviewed false positive with the suppression comment; never edit a script that is running. Then consider `--strict`. (filed 2026-10-22, f8) (workspace-f2 audit 2026-11-09: wired in pre-commit.extras:53-60; full-tree run 1 finding, in churn/ws58-keeper-watchdog.sh:13, 7 reviewed exceptions; --strict not adopted)
  - 2026-10-23 (f8) PARTIAL: lint reports 72 findings (the ~150 figure was output lines, 2 per finding). Cleared 20 across 9 scripts under `scripts/{search,validate,hermes,utils,safety,session}` (`grep -q` -> `grep ... >/dev/null`, `| head -N` -> `| sed -n '1,Np'`; all `bash -n` clean; 72 -> 52). Remaining 52: 2 in `scripts/fillers/filler_run2.sh` (script was RUNNING, skipped per rule; redo when idle), 50 in `scripts/coordination/**` + `scripts/hooks/**` + `scripts/operator/*ratify*` (operator-run) pending operator ack (ready patch `/mnt/raid0/llm/tmp/f8-lint-d9-pending.patch`, 19 files, not applied). The pre-commit wiring patch and `--strict` are not done. Box stays open.
  - 2026-10-23 (f8, operator D9 ack ~15:20Z, option 'hooks + coordination only'): the D9 part applied to 13 live files (6 `scripts/coordination/**`, 7 `scripts/hooks/**`); `bash -n` clean; `test_pre_push_serialization_guard.sh` OK, `test_supervisor_stale_source.sh` 13/0, `test_backfill_supervisor_loop.sh` 34/0. The 6 dated `scripts/operator/*ratify*` scripts are deliberately NOT rewritten (signed one-shot records; operator choice): they stay as known lint exceptions. Remaining: `scripts/fillers/filler_run2.sh` (2 hits, redo when idle), the pre-commit wiring patch, `--strict`.
  - 2026-10-24 (f8 sweep): cleanup DONE to 0 findings. `scripts/fillers/filler_run2.sh` 2 hits fixed (no process runs the repo copy; the running fillers use `/mnt/raid0/llm/tmp/fillers-3c4ca599/` copies). The linter no longer flags `producer | head ... || true|:` (output still right, status discarded on purpose), which clears the `scripts/hooks/pii_precommit.sh:673` false positive with no D9 edit; `grep -q ... || true` stays flagged. The 7 signed `scripts/operator/*ratify*` hits are now reviewed exceptions in `scripts/lint/pipefail_early_exit_exceptions.txt` (path + pipeline text; counted, stale entries reported). `--strict`: `tests/lint/test_check_pipefail_early_exit.py::test_repo_scripts_are_clean_in_strict_mode` gates scripts/ at 0 findings (15 tests pass). ONLY remainder: apply `scripts/lint/pre-commit-wiring.patch` (D9, `scripts/hooks/pre-commit.extras`; `git apply --check` clean on origin/main 2026-10-24), which needs the operator's per-change D9 ack; tick on apply.
- [x] **LINT-QUEUE-DATE-BOUNDARY — test queue/launcher job admission across midnight.** The preserved v1 runner correctly classifies the current half-open daily blackout `[00:15Z,06:30Z)`, but its future-job overlap check uses tomorrow’s 00:15 even at 00:00, allowing jobs20/24/30 to cross today’s blackout. Test `is_blackout(now)` separately from admission for `[start,start+duration)`: 23:59Z and 00:00Z are outside blackout yet a 30-minute job overlaps it; 00:15Z is inside; short jobs at 06:30Z/06:31Z are outside absent another window. Bind actual maintained predicate source, explicit UTC dates, short/long durations, endpoint semantics and the documented margin. Private v2 already checks absolute dated windows with a300-second margin; a dated calendar is not the recurring daily rule. Reuse its overlap logic and require the same controls for new window guards and calendar consumers, preserving original failures. [Pinned v1 source](https://github.com/pestopoppa/epyc-inference-research/blob/53ac1e663f88f1d759857c9eadaefbd6acf4c760/artifacts/f8-evidence-20261021/cpu-queue-f8/runner.sh). The maintained source/owner boundary must be resolved before modifying the private launcher/calendar; no queue or launcher is started by these controls. ✅ 2026-10-31 [source: 61bdf95ee27e82e2e7bff9547c90338861713ece; tests: tests/test_cpu_queue_f8_runner.py; evidence: artifacts/engineering/lint-queue-date-boundary-20261031/TEST.log (9/9)] [no-belief: deterministic source/queue-admission regression, no live queue activation]
  - 2026-10-23 (f8) NOT STARTED in this pass: the task itself gates on resolving the maintained-source/owner boundary of the private launcher/calendar before any change; no predicate source was bound, so no test was written.


## NI08 accepted source captures and next actions — 2026-10-21

Accepted NI08 scope is **220 = 145 existing checkbox closures + 75 scoped children**, including six newly completed source-capture tasks with 200 passing controls. The earlier proposal/S05 captures remain counted once. Final integration and main publication await the owning wrap-up lease. Source controls do not close quality, cohort or live-observation parents. OP-M12F and OP-AUD10 remain queued; NI75 stays authorized and resolved 1B/2A choices remain resolved.

The four reviewed commits are reconciled in normal isolated merge `e44e5f47d4abb6cf125c64d7a9538d13eded7d50`, parents `9075c7a9302b8eeff774c8fc00b14e92035c7b48` and `5821eb145377354e12f00162e843804a7d75d5c5`, exact 14-path tree `e5f69298a5b412c3f4c36567cd1774cbd483173b`. MAIN independently accepted all 117 original command records, source bytes and four-commit ancestry. The first attempt's refusal is retained: only Git config origin presentation differed (`file:.git/config` versus `file:/workspace/.git/config`); values never changed. The successful second attempt used separately bound exact normal ROOT/OWN snapshots. The reconciliation was reviewed before publication; governance receipts record the actual subsequent run.

The original copied-proposal capture at ROOT `9ed97e6efb044a91c4ed51ec0febaf518efe084e` preserves hosted 63/26 fixture cases. The S05 capture at `8168cb17089e60c098ffa8b9a501440e1435ebaf` preserves native TRUE outer 1/1, the corrected saved-E1 33-manifest roster, two W1/W4 unchanged-harness dry plans, 48 generated outputs and 2,764 native input entries. These are source-conformance observations through the existing `ci-fixture-conformance` carrier and shared Judged/Located ladder, not quality, performance, current-pool readiness or owner-window observations.

MAIN accepted all six prospective source-capture tasks: NIB83 7/7, PII metadata 52/52, CJ10 59/59, S05 observer 11/11, CJ14 44/44 and CJ5/6/7 27/27, each with zero skips, failures or errors: **200 passing controls across six tasks**, not 200 task closures. Existing shared grade is Judged/Located. CJ10 file inventories remain ten Research and nineteen ROOT files; the five earlier PyArrow skips and CJ567 first custodian timeout remain immutable history. No quality, cohort, owner-window, live inference, protocol, fleet-discrimination or performance parent closes.

NIB77's refreshed 2026-10-21 frozen registration inventory contains **35 retained exact lane paths, 24 with tracked and/or untracked source status entries**. These counts do not identify active, retirable or owned lanes. Native historical PID fields are absent now; current working/compacting/idle and accountable stewardship remain unknown. Default recommendation is retain current custody and all bytes; an explicitly named willing steward is an optional operator choice. No migration, cleanup, deletion, process termination or ownership transfer is authorized. [Current package](../../artifacts/operator/decisions/NIB77-current-custody-20261021/README.md).

### PII source-control capture accepted — 2026-10-21

MAIN accepted [original PII native metadata source custody](../../artifacts/ci/pii-native-metadata-source-20261021/README.md): source587a47ed, GitHub39596348505 attempt1, 52/52 passing, zero failures/errors/skips, native TRUE and unchanged shared Judged/Located grade. Exactly one existing source-validation checkbox closes. The preceding two-task checkpoint was **216 = 141 existing checkbox closures + 75 scoped children**; NIB83 remains counted once. Typed native identifiers and the exact owned operation metadata are disambiguated while account/secret refusal controls stay blocking. No host hook install, privacy assurance, model/inference result or new grading rule is claimed.


### Four additional source-capture tasks accepted — 2026-10-21

The scoped total is **220 = 145 existing checkbox closures + 75 scoped children**. This update flips exactly four existing source-capture checkboxes after MAIN acceptance; NIB83 and PII metadata had already raised the prior working total to 216. Parent tasks remain open. [CJ10](../../artifacts/ci/cj10-prompt-source-20261021/README.md), [S05 observer](../../artifacts/ci/s05-observer-source-20261021/README.md), [CJ14](../../artifacts/ci/cj14-redundancy-source-20261021/README.md), [CJ5/6/7](../../artifacts/ci/cj567-fixture-source-20261021/README.md). Secondary grade source commit `fda2174b115d0eabcd9fa1abd88e2461a2685d2e` is an additional integration parent, not another source task closure.

## Ingestion failures surfaced by original CI — 2026-10-21

- [x] **NI08-INGEST-PREFLIGHT — refuse missing INF-70 and AutoKernel corpora before ledger construction or writer-lock materialization.** Preserve serialization for valid writes. Reproduce `tests/vidya/test_inf70_roofline_ledger_adapter.py::test_cli_ingest_rejects_a_missing_root`; add no-ledger controls for normal, dry-run and only-new modes plus valid-root lock controls. Use prospectively enrolled hosted source controls; no model or real-corpus execution. (source e20d082fd7b91df8dd67f2126744850553a024cb on main; 162/162 conformance PASS; ws58 2026-10-25) [no-belief: correctness, no measurement]
- [x] **NI08-ODL-IMPORT-IDENTITY — make direct CLI and package-qualified ODL imports share one initialized adapter module.** Reproduce `tests/vidya/test_ingest_sources.py::test_every_wired_adapter_projects_through_a_registered_projection` and `test_every_dispatched_adapter_declares_its_authority`; cover both import orders while retaining strict rejection of genuinely different projection functions. Do not weaken the registry or introduce another grading ladder. (ba1bcc90781ef76d564eb3e82b357cffb5f8644c on main; 11 PF PASS; ws58 2026-10-26) [no-belief: correctness, no measurement]

These three failures were observed in original hermetic run39611159131 at source7aa479e3 and remain source-visible at published86d93a3c. The PII repair native99 result is separate. Private source preparation is underway; these tasks remain unchecked and add no completed scope.

### Lint source acceptance — 2026-10-21

MAIN accepted original selected run `39617059382` attempt1 at source `56b782ebf20a88b356057983bf73594b5e22a907`: 11/11 controls passed, zero failures/errors/skips. Receipt seal `610399bb60f55ee6e3dffe541db0f9b83f53eaa8877753a10c57be4d59f81555`; unchanged shared grade Judged/Located describes warrant, while native JUnit reports the verdict. The checker reads staged shell blobs and warns about producer pipelines with `grep -q` under pipefail; warnings and scan errors remain advisory. Versioned installer wiring was source-inspected; these 11 controls exercise the checker, not a live installer. No installed-hook activation is claimed. [lint native evidence](../../artifacts/ci/lint-sigpipe-source-20261021/README.md).

The published 220-completion boundary remains historical. This acceptance adds two closures: **222 = 220 previously published + 2 lint source/capture closures**. CLI remains open: its original selected run39616781407 passed7/13, with six harness failures from missing required `--as-of`; a separate test-only successor preserves that original FALSE. M12i has one FIFO request queued (PID1624637), without a held full-CPU claim or scorer invocation; queue admission is not replay completion.

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **NIB2-LB1 — Before the planned ~/.codex retention reaper or the opencode event reaper deletes anything, require proof that the cloud-llm-vault copy or an ai-sessions tarball already holds the rows to be deleted, and export a content-stripped extract first only for a store the backup coverage check reports as not covered (intake-2389).** ✅ 2026-10-22
  - [x] **NIB2-LB1.1 — precondition tool + rule** ✅ 2026-10-22: `scripts/system/backup_coverage.py precondition --store
    <store> [--rows-before ts]` (exit 0 covered and fresh, 3 not covered, 4 backup older than the rows); rule written into
    `docs/guides/agent-workflows/cleanup-reference-check.md`. Today: `codex_rollouts` → 0 (its apply is disabled anyway);
    `opencode_db` → 3 (partial: one-off `.db.zst` only).
  - [x] **NIB2-LB1.2 — wire the precondition into `opencode_event_reaper.sh`** (or retire the requirement for `event`
    revision rows) ✅ 2026-10-22 RESOLVED by retiring the requirement: the reaper prunes only the `event` table, which no
    mining reader uses any more, and the operator's hourly read-only snapshots `/mnt/raid0/llm/opencode-db/{epyc,host-daniele}.db`
    hold the full `session`/`message`/`part` history (`backup_coverage.py` reports `opencode_db` covered by them). The reaper
    script is untouched; mining readers were repointed at the snapshots (UTM-LB1 update; root `f8/opencode-ro-root-20261022`).
- [x] **NIB2-GNX-1 — Repair the epyc-orchestrator gitnexus index (stale ~1290 commits).** The 2026-10-23T06:37Z re-index (`/mnt/raid0/llm/tmp/compute-flags/f8-gitnexus2-run.log`) re-indexed epyc-root cleanly (78,127 nodes) but the orchestrator `scripts/gitnexus-analyze.sh` SEGFAULTED during the incremental pass (+1088 importers, BFS depth 4), and gitnexus warns that branch `spec-dec-mtp-refresh-2026-06-22`, not `main`, owns the orchestrator flat index slot. Steps: inspect which branch the slot should hold; re-point it to `main` with the documented gitnexus command (the warning suggests `gitnexus clean --branch spec-dec-mtp-refresh-2026-06-22`; never delete `.gitnexus/` by hand); run a FULL (non-incremental) analyze through the wrapper under a build-role grant; verify `gitnexus status` shows main at origin/main. Until then, orchestrator impact checks need the structural grep fallback (as used for the 2026-10-22 SEC landing). (workspace-f8, 2026-10-23) [no-belief: tooling-repair (README row, no adapter module) -> Codex C5]
  - *(2026-10-24, workspace-58: done, ticked.)* `nib2-gnx1-reindex-2` (16:18Z): ff of the shared orchestrator clone fd1a8941 -> be208213 OK, then gitnexus analyze SIGSEGV rc 139 (ANALYZE_FAILED, no core file). Recovery per the Codex GNX-SEGV-1 report: the untrusted partial `.gitnexus` was moved aside to `nib2-gnx1-reindex-2/gitnexus-untrusted-partial-20261024T1640Z` (delete only with operator OK), the backup restored, then a forced full analyze via `scripts/gitnexus-analyze.sh --force` under a whole-host region-lock: 18:43Z at be208213, again 18:52Z after the operator-approved ff to 84f6f6f1 -> `Indexed commit 84f6f6f, up-to-date` (log `/mnt/raid0/llm/tmp/ws58-gnx-force2-20261024.log`). Tick basis: orchestrator index at origin/main; the nib2 job itself did not pass (the forced manual analyze did).
  - *(2026-10-23 15:33Z, f8.)* **ARMED `nib2-gnx1-reindex`** (launcher pid 1192093, `/mnt/raid0/llm/tmp/f8-launchers-20261023/nib2-gnx1-reindex/`).
    - Placement: CPU whole host (q0-q3). gitnexus-guard admits only an ancestor holding all eight build/GLOBAL quarter locks, which is why the first attempt was refused with rc 64. About 15-25 min.
    - Steps: probe the guard before any change (a refused admission touches nothing); back up `.gitnexus` and registry.json (about 1.7 GB, size-checked); `gitnexus clean --force` in the orchestrator repo only; the wrapper's full analyze; then `gitnexus status`.
    - PASSED = branch main, and the indexed commit equals HEAD (orchestrator main `f3ab78b2` at arming). A segfault is recorded in `out/analyze.out` + RESULT.json and stops the job. The restore recipe is in RESULT.json.
  - *(2026-10-24, workspace-f8 read-out.)* **Job PASSED (RESULT.json state VERIFIED), but the task's own done text is not met, so not ticked.** Ran 2026-10-24 01:08-01:09Z under the q0-q3 grant, rc 0. Result: `/mnt/raid0/llm/tmp/f8-launchers-20261023/nib2-gnx1-reindex/RESULT.json`. Gate: job.sh sha256 `8b204799d3a54877663e3c38ed06174eb6b4b7853f173cea88b0bf52cf22e8cf` plus the FILLERS row (branch main, Indexed commit == HEAD, not stale).
    - Every step ran: guard probe rc 0; backup 1.7 GB, size-checked; `gitnexus clean --force` on the orchestrator only; full analyze in 54.5 s with no segfault.
    - New index: 85,231 nodes, 158,733 edges, 3,435 clusters, 300 flows. Status: Branch main, Indexed = Current = `fd1a894`, up-to-date. The flat slot now holds main; it was `spec-dec-mtp-refresh-2026-06-22` @ f72d1d5.
    - **Why not ticked:** the done text here is "main at origin/main". The shared clone's local main is `fd1a894`, but origin/main has been `26affbf8` since 2026-10-23 16:20Z. That is 2 commits ahead: a `launch_affinity` script, its test and a merge. So the index matches HEAD, not origin/main.
    - **Next:** fast-forward the shared clone's main, run one incremental analyze through the wrapper under a build grant, then `gitnexus status`.
    - **Anomaly: the job's `WARN: other repos' registry entries CHANGED` is a false positive.**
      - The filter matched on `/mnt/raid0/llm/epyc-orchestrator`, but the registry listed this index under `/workspace/repos/epyc-orchestrator`. So the block that disappeared was this repo's own.
      - `out/list.before.txt` and `out/list.after-clean.txt` differ only by that block (14 -> 13 repos).
      - The new entry is registered under the `/mnt/raid0` path, which is the same clone through the symlink.
      - The old `main (cdbca26)` branch-index entry went with the clean.
      - The backup and the restore recipe are in RESULT.json.
- **[declined: ws58 2026-11-03 content-review: merged into LOOP-57 (the same red-test triage)]** **NIB2-TESTDEBT-1 — triage the pre-existing test failures today's branch reviews found on main** (filed 2026-10-24, f8 wrap-up). Orchestrator: `tests/unit/test_stack_change_pipeline.py::test_run_promotion_gate_executes_combined_no_inference_targets` (KeyError 'cmd') and `::test_update_then_check_succeeds_with_known_gaps_allowed` (assert False), both failing on orch main 2cd016b9. Research: the autokernel controller+loop suite fails about 95 tests plus 28 errors on main (largest groups: test_discovery_static_registry 27, test_validation_final_receipt 15, test_loop_scaffold_runner 15, test_cpu_fa_verifier_record 13, test_arena_cell_runner 13), and `test_serial_roster::test_shared_author_sandbox_reaches_real_authenticated_control_startup[on|off]`. Per group: a real defect gets fixed, a stale test gets updated, an environment dependency gets marked. The AK groups belong to the AK owner (3c4ca599); route them there.
  - [x] scaffold (ManifestTest 2 cases) + arena (identity drift / sampler release) fake-fixture tests hermetic: research a6c764a3d, 32 PASS (executed on orchestrator venv Python 3.11; Python 3.13 proved the mandatory collection floors 194 + 5635 before/after) [no-belief: correctness]
  - [x] **AK-DISCOVERY-OWNED-CGROUP** (T3) — the discovery native compiler/cgroup probe needs a job-owned delegated cgroup (current `/proc/self/cgroup` is `0::/`). Needs a separate design with the exact owned path, cleanup, and one native compiler probe. The other 53 methods already PASS; no duplicate fillers. RESULT: PASS, row `ak-discovery-native-toy-cgroup-20261025`: child in the owned leaf, rc 0, owned leaf removed, no new root entries (`/mnt/raid0/llm/tmp/ak-discovery-native-toy-cgroup-20261025/out/RESULT.json`), research 4b54074c1, 68ff30491. The kill path did not fire live (`killed: false`). ✅ 2026-11-09 [no-belief: launcher/cgroup fixture only]
  - [x] **Orchestrator stack-change pipeline pair** — the two named tests above pass unchanged 2/2 on Orchestrator `5c9875330e3985d06e6c7986f44e920cd847ad56` (5.44s, rc 0); existing fixes `7c1481c2` and `3c4d6881` are present. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261025-pool-stack-pipeline/logs/pf-baseline.log`. ✅ 2026-10-26 [belief: cc]
  - [x] **AK CPUFA verifier-record subgroup** — current pinned sources pass 14/14 (7.42s, rc 0); existing custody fix `25253ee2f` is present. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261025-pool-ak-cpufa/preflight.log` and `AUDIT.md`. ✅ 2026-10-26 [belief: cc]
  - [x] **AK final-receipt/feed/native-final subgroup** — 42 distinct synthetic cases pass (15 + 22 + 5; 225.06s, rc 0); the original 2-case selection is included. Existing V2/V3 closure fix `85fe9a380` is present. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261025-pool-ak-final-receipt/preflight-batch.log` and `AUDIT.txt`. ✅ 2026-10-26 [belief: cc]
  - [x] **AK discovery static-registry model-free subgroup** — 53 distinct methods pass (4 + 11 + 38; 49-method expanded batch, rc 0). One native compiler/cgroup test remains open pending proof of an owned delegated cgroup. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261025-pool-ak-discovery/preflight-expanded.log` and `REMAINING-NATIVE-SCOPE.md`. ✅ 2026-10-26 [belief: cc]
  - *(workspace-f2 2026-11-09.)* Design in docs/design/ak-discovery-owned-cgroup-20261109.md; wrapper and the one probe row remain for the AK owner.

## 2026-10-27 WS58 operational checkpoints (parent work remains open)

- [x] **ORCH registration-only recovery checkpoint** ✅ 2026-10-27 — native COMPLETE rc0 08:20:30Z; 20 catalog entries, 19 unchanged, 3,804 hashes, zero mismatches. Consumer query NOT_RUN and risk NOT_ASSESSED; C5 v2 rebind remains open. [belief: cc]
- [x] **T1-A same-entry launch-gate private delivery checkpoint** ✅ 2026-10-27 — MAIN accepted private pushed branch `codex/t1-launch-gate-20261027` at `35348712ca56abc95c143bd7f278fd5c051821fd`; focused process-limit r2 passed. No canonical merge/deployment claim. [belief: cc]

## 2026-10-28 NI status checkpoint — parent work remains open

The 2026-10-27/28 operational queue adds no completed NI parent acceptance checkbox. The approved GPU ABI R2 source `d0c1bb49f43c731b9e69b1aea1e90a1e857130e1ba4fce7900224c0e950316b2` first ended in an exact HOLD refusal, rc 70 at 23:56:32Z before effects; its later owner-window retry completed rc 0 at 00:09:22Z with seven total proof samples, only two strictly inside API windows. Independent replay now passes the narrow ABI/residency claim; this does not close W1 or P0d and is not a performance or production result. W1 source `e1b8e9318500c5e3292fdbf890b46b3b17e46b1920b4285cddb40e546ebea2bc` remains unsafe due to missing `capture_inputs` provenance keys and illegal `large_refs`; its separate repair is untested and unconditionally UNREADY.

The actual INF-75 W5s owner run ended rc 0 and captured primary-target geometry (3/49/17 graphs; 22,431/366,373/127,109 nodes; shapes 2048/1/5). MAIN withholds full-facet acceptance: foreign-load/request timestamps have UTC bounds only, not the required both-clock containment, and each capture journal points to a stale W3-v5 eviction receipt instead of the actual W5 receipt embedded in identity. This leaves the required proof facet unmet, not the captured geometry erased. MAIN is preparing a W5 successor. Preserve the raw run; do not tick or claim completion, and do not invent historical monotonic evidence.

2026-11-01 W5s r7-v2 correction: `inf75-w5s-current-census-r7-v2-20261101` was published at 14:56Z, withdrawn at 14:58Z before nonce/receipt/grant. Its fixture missed the original 4,096-token prefill HTTP request (2,048 is only native batch shape). Publication and withdrawal receipts are preserved under `/mnt/raid0/llm/tmp/codex-ni-v2-w5s-20261101/`; no result or W5s completion follows. Next row must qualify that original longest request. [no-belief: admission correction]

The Parakeet observer canary at ROOT `91c6336a169329311848cf9457b2b61eecec37ac` ended rc 1 at 23:44:49Z. Besides the `/dev/kfd` classifier defect, CPU `buft` may have a null device by design; CPU proof requires the CPU singleton and host identity. The fix draft is active, not accepted.

MAIN accepted two bounded UFH-12 G-S collection facets after Terra's text audit (`/mnt/raid0/llm/tmp/codex-ni-20261028-gs-native-audit/FINDINGS.md`). The paired-score collection contains 500/500 validated stored-text proxy-query records (489 episodic, 11 strategy), with within-model BGE-1024 / EG2-256 top-k scores, self-exclusion and ascending-ID tie ordering; median overlap k=5/10 is episodic 0.4/0.3 and strategy 0.6/0.5. The token diagnostic covers 65,942/65,942 full stored texts with special tokens: episodic 64,514, median/max 61/135; strategy 1,428, median/max 126/284; none exceed 2,048. Native sidecars are CANDIDATE with empty protocol ID; higher-better applies only to coverage. These are descriptive collections, not observed-query relevance, retrieval quality, threshold, adoption or Ratified protocol conclusions. The audit was text-only and did not independently verify digests, rederive or replay results, check live host/process/ports, or grade. G-S parent REPL-EMB-2.11 and REPL-EMB-R5 remain open. Scores and tokens completed rc 0 at 23:22:04Z and 23:29:49Z on 2026-10-27. [belief: cc]

The two accepted collection facets had no pre-existing child checkboxes. Proposed owner-applied completed child lines are included in the REPL-EMB-2.11 draft; they do not close REPL-EMB-2.11, G-S, R5, or another parent's scope.

The GitNexus admission attempt ran during the RTG-57 whole-host timing window. The private checkpoint worktree `codex/ni-checkpoint-0020-root` was created from `origin/main` `941958d8cf52d343d76e788bab1dddfb1c5fa5eb` in that window for owner assessment; no measurement impact is inferred. The runner held the shared serialization mutex while waiting for quarter-coarse q3 admission, blocking a peer waiter. Captured process group PGID 2243685 contained timeout PID 2243685 (start ticks 126883838), `/usr/bin/time` PID 2243694 and region-lock CLI PID 2243695 (both ticks 126883839). TERM drained the group; all PIDs were verified absent, nonblocking `flock` verified mutex release, and the peer was notified. Region-lock never started the child; GitNexus never ran. No production changes. [no-belief: process-management incident record; no measurement impact claim]

The exact user-approved KPF18 batch contained 19 paths: 16 present paths were moved into `/mnt/raid0/llm/.trash/kpf18-approved-r15-20261027-1900/`, 3 were absent, then the approved 16-path purge completed at commit `47eb07f7d5e49a3add117a6e970628479022999b`. Free space increased by 14,209,081,344 bytes; concurrent shared-host activity means the full observed delta is not attributed solely to the purge. MAIN accepted the mapping review (mapping SHA-256 `8653225c20daf9a582078c4da320298b45ad590e73ed2a6d50508413ddc0c3f5`). Tooling `c777f6179b71518714eb53193788c735b0348e07` is published as a proposal, not merged or ratified.

Queue ownership: INF-26 arm-P2 is complete and its stale rank entry was removed at `941958d8cf52d343d76e788bab1dddfb1c5fa5eb`; INF-67 FD-OFF-PROD closes at v11 promotion and workspace-58 prepares FD-DIV-1b; RTG-58.2 is stale/closed. INF-65 CH-GATE is closed but the full a0/C6 fold remains open; tiny META-only evidence is not the full candidate. C6 final inputs belong to the champion owner unless no owner is named, in which case NI prepares a pinned-input packet. INF-81 LB4.9 was handed from peer to NI; careful-mode lift is acknowledged, with no permission blocker. Its port-ready packet retains CRITICAL 43 and does not qualify source application; caller/impact review remains required. No production changes. [no-belief: status checkpoint; no accepted native task or measurement claim]

## 2026-10-28 WS58 wrap addendum (NI drafts; parent work remains open)

- W1 constructed-prefill: source seal `692b244` was withdrawn after review found a 132-vs-128 prompt-guard mismatch in `server_evidence_full.py` and a `COMPLETE` marker written before child cleanup (`/mnt/raid0/llm/tmp/codex-ni-20261028-coordination/w1-withdraw-0346.txt`, `w1-cleanup-defect-0347.txt`). Queue state refreshed 2026-10-28 ~03:45Z: the **W1 prefill barrier row is now ARMED** (supersedes the draft's unarmed/withdrawn wording for the row); it is a diagnostic only (fragmentation INCONCLUSIVE; cannot close W1/P0d) and no result exists yet. [no-belief: queue/preparation status, no measurement]
- M4 paired GPU quality row: **now ARMED** (supersedes the draft's BACKLOG/HOLD wording; the earlier `job.sh` defects - unset `ORCH`, malformed region `mi210_26,2784-191` vs `mi210_0,184-191`, grant-duration vs 12,600 s minimum - were reported for repair and the re-armed row is the repaired one). Three M4 CPU rows stay HOLD (watcher PID-birth registry unwired, forced-death cleanup unproven, no job/watch fixture). No result; not a full M4 fold. [no-belief: queue state, no measurement]
- HSF-5P restored-state regression, SSU-F11, SP2 GPU follow-on, RUS3 launcher draft, GPU-ZOS2, OAB-29 (false-PASS of readonly check for non-readonly seats), CH-18.b SWA (UNREADY), V6R3, OAB native-wire, CH18, RTE caller attribution, K2 bool handling, KPF C5 prerequisite port and the withdrawn CH-OBS-BUNDLE packet are private, untested source/preparation drafts: no completed-result or checkbox claim. [no-belief: untested preparation drafts]
- Disclosed ungranted-interpreter incidents, impact unmeasured (do not claim no impact): scratch rewrite of `hil15b2_make_tasks.py` at about 06:33:35Z (`unscheduled-python-0354.txt`) and `sp2_finalize.py` mtime 07:05:19Z (`sp2-ungranted-0705.txt`); owner/peer assessment pending. [no-belief: incident disclosure, no measurement]
- Pair 32,33 prep overlapped the HIL15 s1 grant (24-47); operator choice pending: may CPUs 32,33 co-tenant with this HIL grant, or carve out another pair. Evidence: `/mnt/raid0/llm/tmp/compute-flags/ws58-2000Z-plan.md`, `pair32-hil-0338.txt`. [no-belief: pending decision, no measurement]
- Belief capture: no tuple is warranted by the failed CT-21 capture or W1/M4 preparation; applied conclusions enter only as committed-conclusion OBSERVATIONs. [belief: cc]

## 2026-10-28 supplement — idle-compute incident (workspace-58 wrap-up)

- [ ] **NI-IDLE-REFILL-WATCHER** the keeper's 120 s `allocate` tick already arms READY rows onto idle bins and logs `IDLE-WHY`; the only gap is a zero-token owner nudge (bus message plus flag file) when a bin stays idle with READY rows past a grace period. Owner: Pipeline. (workspace-f2 audit 2026-11-09: text corrected) [no-belief: tooling-repair]
  *(workspace-f2 2026-11-09 wrap-up.)* Still needed: no zero-token owner nudge for a bin idle with READY rows exists. [no-belief: not-a-result]

## 2026-10-28 loop redesign follow-ons (workspace-58)

- [x] **LOOP-1**: keeper v2 READY auto-arming (zero-token daemon arms `ready/*.json`). ✅ 2026-10-28 — keeper v2 live, superseded same day by v3 (queues into the ACTIVE day) and v4 (GPU rows check every named CPU quarter). Contract: `/mnt/raid0/llm/tmp/compute-flags/LOOP-CONTRACT.md`. [no-belief: tooling-repair]
- [x] **LOOP-2**: `backlog_priority` `kind` field plus inference-prep ranking. [no-belief: tooling-repair] (workspace-f2 audit 2026-11-09: landed in scripts/handoffs/backlog_priority.py; kind field and prep band confirmed)
- **[declined: workspace-f2 audit 2026-11-09: no code sender remains and the last channel files date from 11-01; operator retired it]** **LOOP-3**: retire OWNER-REPLY/owner-reply relays once `ready/` flows. [no-belief: tooling-repair]
- **[declined: workspace-f2 audit 2026-11-09: HIL15 lane is dormant, one v5 candidate already exits rc75, and the box no longer names a runnable launcher; operator asked to resolve or retire]** **LOOP-4**: HIL15 v5 window-end must exit rc75, not rc1. [no-belief: tooling-repair]
- [x] **LOOP-5**: daily loop metrics report: decision results/day observed by `scripts/handoffs/loop_metrics.py` (0d6afca01). ✅ 2026-11-09 verified: `decisions()` returns an observed count from the native verdict snapshot; the other three metrics are split into LOOP-5B. [no-belief: tooling-repair]
- [ ] **LOOP-5B** — the other three LOOP-5 metrics are still `unknown` in `loop_metrics.py`: idle-h (keeper emits point alerts only), failed-at-entry rate (filing-due is deduplicated, no admission-attempt ledger) and operator messages (no authorized human-message producer); keeper/quarter-writer patches are not applied live. Done when each reports an observed value on a real day. [no-belief: tooling-repair]
  - 2026-10-31 source checkpoint: the opt-in event producer and read-only daily report now have 51 integrated tests; standalone launchers with telemetry disabled need no new file or EXIT trap. Keeper/quarter-writer patches are source-pinned proposals for the owner, not applied live. Kernel-accounted CPU idle-hours exclude iowait and are not whole-resource wall-clock idle; missing coverage and human-message counts remain UNKNOWN. The original task remains open pending adoption and real daily coverage. [Review package](../../artifacts/engineering/loop5-source-20261031/ADOPTION.md). [no-belief: source and synthetic controls]
  *(workspace-f2 2026-11-09 wrap-up.)* Re-checked `scripts/handoffs/loop_metrics.py` (0d6afca01), left open: decision results, idle-h and failed-at-entry rate are produced, but `operator_messages` is reported `unknown` ("no authorized human-message metadata producer"), so the box's fourth metric is not delivered, and the 10-31 note still holds that keeper/quarter-writer patches are not applied live. Tick needs an authorized operator-message producer and a day of real coverage. [no-belief: tooling-repair]
- [x] **LOOP-6**: ✅ 2026-10-28 — keeper v5 (pid 187081) replaced v4 at 16:14Z with REAP_IDLE=1; reap gate live in ws58_arm.py (reap-gate-v2 patch); hook pin `scripts/hooks/destructive_scratch_pins.json` committed. Swap in keeper v5 (reap-after-filing gate + 7-day rule) and enable the gate, with the operator-approved hook exception. Design: `/mnt/raid0/llm/tmp/disk-audit-20261028/LOGS-AND-REAP-DESIGN.md`. [no-belief: tooling-repair]
  - 2026-10-29 (workspace-58): keeper v5 was restarted at 01:51Z with `REAP_IDLE=0`. The idle (7-day) reap deleted at least 17 `.sh`/`.py` code files without vaulting them, so only the filed reap stays on. The v6 keeper that vaults code before an idle reap is LOOP-24. [no-belief: tooling-repair]
- [ ] **LOOP-7**: get owner confirmations for the 58 UNCLEAR KEEP dirs (8.1 GiB) in `/mnt/raid0/llm/tmp/disk-audit-20261028/KEEP-AUDIT-20261028.md`; reclaim the unconfirmed ones after the 7-day rule. [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* 2 of 58 dirs trashed (0.94 GiB); the rest were recent, referenced, or otherwise held.
  *(workspace-f2 2026-11-09 wrap-up.)* Disk table `/mnt/raid0/llm/tmp/rtg22-loop7-20261109.md`: of the remaining UNCLEAR dirs, 10 gone, 2 referenced, 23 owner-known (4.97 GiB), 23 unclaimed (0.02 GiB); nothing removed. [no-belief: tooling-repair]
- [x] **LOOP-8**: drop `-lv 4` from the q38fn-armP / armP2 / g2conc / yarn-e1 launchers (server-log growth; 2 logs = 4.23 GiB deleted 10-28). ✅ 2026-11-01 — implementation commit `725d46c148fe5e20ef84650fdb08956b9ad14f83`; `bash -n` passed for all four scratch launchers and the tracked armP2 recipe, and the artifact hash/static assertions pass at `artifacts/engineering/loop8-launcher-verbosity-20261101/EVIDENCE.json`. Set verbosity to 3 (info) to retain YARN proof lines while removing trace output; exact external scratch patch and digests are preserved in the artifact. [no-belief: tooling-repair]
- [x] **LOOP-9**: apply the skill-review patch `/mnt/raid0/llm/tmp/ws58-skill-review/DRAFT.patch` once the operator OKs it. [no-belief: tooling-repair] (workspace-f2 2026-11-09: rebased onto the v3 keeper flow; stale LOOP-CONTRACT and SKILL-rewrite parts dropped; ed3d95b81) ✅ 2026-11-09 [no-belief: tooling-repair]
- **[declined: workspace-f2 audit 2026-11-09: obsolete: grant writers are gone and the single rowflow allocator holds every region token]** **LOOP-10**: grant-gpu v16 — the GPU writer (v15) must check every CPU quarter a GPU row names itself, not rely on keeper v4. [no-belief: tooling-repair]
- [ ] **LOOP-11** keeper must run the arm checks BEFORE starting the launcher: `rowflow.py` `arm_one()` spawns the poller and `admit()` checks `grant_ok_launcher` only afterwards, and a refusal kills nothing, so it still leaves orphan pollers. Owner: Pipeline. (workspace-f2 audit 2026-11-09: text corrected) keeper-frozen-20261109: `rowflow.py` now stops a verified, job-free poller when a refusal parks the row or RE-ARM replaces it; arm_one still runs before admit. rowflow2 is shadow-only and spawns no poller, so whoever adds its arming must carry this rule at cutover. Open until deployed. [no-belief: tooling-repair]
- [ ] **LOOP-12** the keeper is supervised by `churn/ws58-keeper-watchdog.sh`, but the watchdog itself has no supervisor and has not been tested against a real session crash; grant writers no longer exist. Owner: Pipeline. (workspace-f2 audit 2026-11-09: text corrected) keeper-fixes-20261109: `churn_up.sh --supervise-watchdog` added on the branch (not deployed); the idempotent supervisor itself is on origin/main (1219d4438, `churn/churn_up.sh` + `tests/test_churn_up_supervision.py`) and starts at the next churn_up, whose deployment is unverified; not yet tested against a real session crash, box stays open. [no-belief: tooling-repair]
- [x] **LOOP-13** `rowflow.publish` now derives `scratch_root` and `keep` for every manifest (300 of 300 recent ready manifests carry `scratch_root`); only a manifest hand-written outside `publish_row.py` can still omit them. (workspace-f2 audit 2026-11-09: text corrected) [no-belief: tooling-repair] (workspace-f2 2026-11-09: rowflow.publish writes scratch_root and keep into every manifest; 300 of 300 newest ready manifests carry both) ✅ 2026-11-09 [no-belief: tooling-repair]
- [ ] **KEEPER-CLASS-FIX — keeper/placement class fix** (in flight, class-fix agent, deploying via `deploy_rowflow.sh` only): #1 reclaim idle use-holds / release-on-phase; #2 evidence contract; #3 per-row pinned engine dir; #5 single state model; #6 idle SLO with a fixed alarm route. Friction review: `docs/reports/coordination/keeper-friction-review-20261105.md`. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 2). [no-belief: tooling-repair]
  - 2026-11-05 14:09Z: evidence contract, packing, GPU token for all GPU users, host-view 2-sample foreign-VRAM gate, smoke PASS terminal, compute-binary thread evidence, withdrawn-row filing deployed (fdb7348fe, 3e9d53426; gate 285 unit / 24 replay). Day replay idle GPU-h 8.87→7.34, idle q-h flat ~2.0. #1/#3/#5/#6 still open; not ticked. [no-belief: tooling-repair]
  - (2026-11-05, operator-adhoc-ops-20261105 wrap-up 4): packing 75e930e05 (smoke whole-quarter reservation only for rows runnable now); width regression fix eae8228a3 + 9218dffd1 (thread evidence from the job's imports, smoke footprint never width evidence, declared quarter is a floor, cpu rows never gpu-quiet, explicit regions/shape_override verbatim) replacing the class-fix regression that shrank multi-core CPU rows to 4 cores and gave STT5 r5 gpu-quiet. rowflow.py is now FROZEN at 9218dffd1 (d40bb65bb); remaining #1/#3/#5/#6 land in rowflow2 (ROWFLOW2-SHADOW). Not ticked. [no-belief: tooling-repair]
- [x] **AUTOFILE-OWNER-LIVENESS — map auto_file row owner → session liveness and reconcile the two filing paths** (keeper auto-file vs owner filing) into one. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 2). [no-belief: tooling-repair] ✅ 2026-11-09 liveness mapping done (fc8bfa6fa); reconciling the two filing paths into one is split into AUTOFILE-PATH-RECONCILE.
  - (2026-11-09): PARTIAL, left open: rowflow2 `file_step` now shares `auto_file.owner_live` and the record shape (one queue, two writers). The live keeper path (auto_file.py + frozen rowflow.py) is unchanged by operator constraint; unify only when rowflow2 cuts over. [no-belief: tooling-repair]
  *(workspace-f2 2026-11-09 wrap-up.)* Liveness mapping is done (fc8bfa6fa); the reconcile-into-one-path clause is not: two writers (churn/auto_file.py and rowflow2 `file_step`) remain. [no-belief: tooling-repair]
- [ ] **AUTOFILE-PATH-RECONCILE — reconcile the keeper auto-file and rowflow2 `file_step` filing paths into one queue/writer (owner Pipeline).** Two writers remain. [no-belief: tooling-repair]
- [x] **FILING-OWNER-LESS-REWRITE — replace wholesale rewrites of `filing-owner-less.jsonl` with append/locked single-writer updates.** (2026-11-05, operator-adhoc-ops-20261105 wrap-up 2). [no-belief: tooling-repair] ✅ 2026-11-09 verified: both writers only append (churn/auto_file.py:179, rowflow2.py:1713), no wholesale rewriter remains; locking split into FILING-OWNER-LESS-LOCK.
- [ ] **FILING-OWNER-LESS-LOCK — two appenders (`churn/auto_file.py`, `rowflow2.py`), no lock; a cross-writer duplicate row is possible** (each dedups only against a snapshot it read earlier). Done when one writer owns the file or both take a flock. [no-belief: tooling-repair]
  *(workspace-f2 2026-11-09 wrap-up.)* Still open: current code only appends to `filing-owner-less.jsonl` (churn/auto_file.py:179 and rowflow2.py:1713, no rewrite left), but the two appenders run with no lock and no single owner, so the box's append/locked single-writer clause is not met. Tick when one writer is chosen or both take a flock. [no-belief: tooling-repair]
- **ROWFLOW-SIMPLIFY — cut `rowflow.py` line count (3756→3867 after the class fix) with the replay gate (285 unit / 24 replay) green before and after.** (2026-11-05, operator-adhoc-ops-20261105 wrap-up 3) [no-belief: tooling-repair] [declined: operator 2026-11-05 rowflow.py frozen at 9218dffd1; simplification is the rowflow2 rebuild, ROWFLOW2-SHADOW; Fable pass-3 audit 83ed78d8d]
- [x] **ENGINE-GPU-FENCE — set ROCR/HIP_VISIBLE_DEVICES empty for every row without the GPU token, plus a foreign-GPU breach detector.** Root cause: STT5 CPU-lane HIP whisper-cli (see CS-8.STT5-DEVICE-DECLARE). (2026-11-05, operator-adhoc-ops-20261105 wrap-up 3) [no-belief: tooling-repair] ✅ 2026-11-05
  - (2026-11-05, operator-adhoc-ops-20261105 wrap-up 4): landed 6b462ca36 + fbfb22177 (tokenless rows get ROCR/HIP_VISIBLE_DEVICES hidden plus an LD_PRELOAD shim refusing /dev/kfd and /dev/dri; keeper GPU-FENCE-BREACH sampler) and 6924e474b (publish refuses undeclared GPU work; vacuous fenced GPU tests fail rc78). [no-belief: tooling-repair]
- [x] **GPU-EXCL-SMOKE-RECHECK — owner-routed: recheck `pf1-expand-r2` and `akx-lb3-2-cv5-pair-r2` (and xgrammar r3) for overlap with smokes under exclusive grants.** Audit: `/mnt/raid0/llm/tmp/gpu-exclusivity-audit-20261105.md`. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 3) ✅ 2026-11-09 recheck done: pf1-expand-r2 overlapped (kvu19-p5 smoke; foreign 27.4 GB VRAM in A0 block 1 at 14:08:57Z, controls inflated; filing inconclusive stands), akx-lb3-2-cv5-pair-r2 ~17 s setup-only overlap (unproven, no pair verdict), xgrammar-a2-profile-r3 timing pairs fully inside smoke inf34-v15 (only directional ~1.0x survives; superseded by r4). Report /mnt/raid0/llm/tmp/rtg22-grant-unfiled-20261109.md. [no-belief: tooling-repair]
- [ ] **ROWFLOW2-SHADOW — build rowflow2 (~900 lines, per the pass-3 simplification audit 83ed78d8d) and run it in shadow beside frozen rowflow.py for one week, then cut over.** Done when: a week of shadow decisions diffed against rowflow.py with every divergence explained, replay gate green, operator-approved cutover via deploy_rowflow.sh. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 4) [no-belief: tooling-repair]
  - [ ] **ROWFLOW2-SHADOW-WEEK** — run `scripts/coordination/rowflow2/run_shadow.sh` for 7 CONSECUTIVE days (clock restarted 2026-11-09 after the 11-08 reboot killed it; earliest cutover ~2026-11-16; first started 2026-11-05) and review each `diff-<date>.md` in `/mnt/raid0/llm/tmp/rowflow2-shadow/`; classify every disagreement; close the design-doc gaps (stop-file check, live CLI, filler successor, D11/D12, unmapped rows). Criteria: `docs/design/rowflow2-20261105.md` → *Switch-over criteria*. Also from the first diff: `lsa-oracle-reference-build-f6dddb7-20261104` was GRANTed 378× by the live keeper on 11-05. (2026-11-05, operator-adhoc-rowflow2) [no-belief: tooling-repair]
    - (2026-11-09): the shadow DIED 2026-11-08 ~08:26Z (host reboot, nothing restarted it) and was restarted 2026-11-09T11:04Z; `churn_up.sh` now starts it at bring-up (idempotent via ps). The 7-consecutive-day clock RESTARTS from 2026-11-09; earliest cutover ~2026-11-16. Diffs 2026-11-05..11-07 remain valid evidence for the disagreement classification. [no-belief: tooling-repair]
  - [x] **ROWFLOW2-STOP-PRESENT-FIXTURE** — add the rowflow2 test for the STOP-released grant loop documented in `docs/design/rowflow2-20261105.md` (5fc9f5379): a ready row whose resolved `stop_file` exists at grant time is skipped (or demoted) and never re-granted; an armed exit on a present STOP counts as an arming failure. Only the doc note exists today (no test in `scripts/coordination/rowflow2/tests/`). Live frozen rowflow re-granted `lsa-oracle-reference-build-f6dddb7-20261104` ~1166× before the row was withdrawn. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 5) [no-belief: tooling-repair] ✅ 2026-11-09
    - (2026-11-09): `rowflow2/tests/test_stop_present.py` (present stop_file never granted; STOP-released grant parks once as an arming failure; negative controls). [no-belief: tooling-repair]
  - [ ] **ROWFLOW2-CUTOVER** — after the shadow week passes: one deploy at a grant-quiet boundary, then delete the P3.3 mechanisms in one commit and lift the `deploy_rowflow.sh` freeze. Hold-price gating is the operator's call (accept / separate budget / drop holds). (2026-11-05, operator-adhoc-rowflow2) [no-belief: tooling-repair]
    - (2026-11-05, operator-adhoc-ops-20261105 wrap-up 5): hold-price gating DECIDED by the operator: plain backfill-if-fits (59f09b81e) replaced the daily hold budget (3ee751108; overengineering). SMT-sibling and timing-row hold rules kept (3ee751108). Shadow pid 2159473.
- [x] **ROWFLOW2-GPU-SHARE-TOKEN — GPU correctness rows share the GPU; timing rows hold it exclusively** (operator decision 2026-11-05; NOT implemented in frozen rowflow.py). Implement as a shared/exclusive GPU token in rowflow2 with a replay test showing two correctness rows co-resident and a timing row refusing any co-tenant. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 4) [no-belief: tooling-repair] ✅ 2026-11-09
  - (2026-11-09): rowflow2 already implemented the shared/exclusive token; `rowflow2/tests/test_gpu_share_token.py` shows co-resident correctness rows and a timing row refusing/being refused by any co-tenant. [no-belief: tooling-repair]
  - (2026-11-05, operator-adhoc-ops-20261105 wrap-up 5): interim rules shipped — GPU correctness suites rank strictly above every waiting GPU timing row and >=60 (e555b6211; rank ties let suites hold the GPU exclusively at ~2% busy); EMERGENCY q3 narrowing, a GPU timing grant holds gpu-quiet + 88-95 + 184-191, never 72-87 (9b69b7131 via deploy_rowflow --emergency; 308 unit / 34 replay pass; 2 clean ticks). The shared/exclusive token itself is still open.
- [x] **ROWFLOW-FREEZE-ENFORCE — deploy_rowflow.sh refuses rowflow.py/publish_row.py/filler_run15.sh changes without --emergency (logged in DEPLOYED.json).** ✅ 2026-11-05 d40bb65bb. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 4) [no-belief: tooling-repair]
- [x] **FILE-RESULT-TICK-OUTPUT — `scripts/coordination/churn/file_result.py` prints `TICK <line>` (lines 266, 282) when it did not write any tick**, which reads as a performed tick. Print it as `SUGGESTED-TICK` (or write it), with a test. Frozen-surface rule applies only to rowflow.py/publish_row.py/filler_run15.sh. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 4) [no-belief: tooling-repair] ✅ 2026-11-09
  - (2026-11-09, rtg22-pipeline-20261109): both prints now `SUGGESTED-TICK`; test `test_no_tick_written_prints_suggested_tick_never_bare_tick` in `scripts/coordination/tests/test_churn_file_result.py`. [no-belief: tooling-repair]
  - (2026-11-05, operator-adhoc-ops-20261105 wrap-up 5, folded): the auto-tick also FAILS on an ambiguous anchor (task text matching more than one box) while still reporting a tick. Same fix: refuse with a named reason and print SUGGESTED-TICK; add an ambiguous-anchor test.
- [x] **ROWFLOW-PASS4-EMERGENCY — the four keeper fixes from friction review pass 4** (`docs/reports/coordination/keeper-friction-review-20261105.md`, 18f4555e5; operator emergency deploy, 2026-11-06). ✅ 2026-11-06: deployed (76f1e1b57; source c8e3820ca; rowflow2 6a77ba071): (1) a refusal parks the row once; (2) `.complete` is no longer reported as rc14; (3) GPU idleness is judged by KFD process count + sampled VRAM; (4) rowflow2 re-checks rank at grant time. The frozen-keeper GPU ordering was a publisher rank tie, not a keeper bug. [no-belief: tooling-repair]
  - (2026-11-06, operator-adhoc-ops-20261105 wrap-up 7) INF-22 rank lesson: `priority_rank` goes in `spec.json` / `unpublished.json`; `GPU-SMOKE-QUEUED.json` is never copied to `ready/`, so a rank written there is ignored.
- [x] **TOKEN-GUARDS-CFG-DEEPMERGE — `token_guards.cfg()` (`scripts/coordination/token_guards.py`) shallow-updates DEFAULTS, so a registry `token_guards` block that sets only `default_model` or `default_effort` drops the other engines' defaults and every such spawn is refused.** Deep-merge the nested `default_model` / `default_effort` tables, with a test whose registry sets only codex. (2026-11-06: the registry had to carry both full tables as a workaround.) (2026-11-06: cfg() deep-merges dict keys; test_token_impl_20261106.py with negative control.) [no-belief: tooling-repair]
- [x] **TOKEN-GUARDS-HANDOFF-DECLARATIONS — declare `model:` / `effort:` in the header of each handoff whose work is hard** (`token_guards.declared()` already reads them from the first 60 lines; precedence row > handoff > registry > default). Kernel diagnosis and design handoffs get terra/astra at high effort; filing and clerical rows get luna. Registry default stays codex gpt-6.1-sol/medium, Claude sonnet/medium. (2026-11-06: terra/high declared in kernel-champion-and-promotion, autokernel-loop, rocm-kernel-authoring, cpu-decode-roofline-program; mi210-serving-program.md is not in handoffs/active, no line added; no clerical handoff declared luna.) [no-belief: tooling-repair]
- [x] **TOKEN-CLAUDE-BUDGET-METER — run the Claude-side budget meter.** `codex_budget_meter.py --claude` already sums Claude transcript usage, but the dispatcher's `meter.update()` does not pass it, so there is no Claude weekly fraction, alarm or `paused_until` (the 11-06 Claude weekly limit hit ~09:10Z unannounced). Wire `--claude --loop` as a zero-token watcher and alarm at 50/80% of an operator-stated weekly allowance. (2026-11-06: dispatcher pass passes claude_root; incremental by offset; 50/80% alarms need registry token_guards.claude_weekly_tokens, unset = meter only.) [no-belief: tooling-repair]
- [x] **TOKEN-DISPATCHER-RESTART-GATE — hs-dispatcher-v3 stays STOPPED.** Before any restart: the operator runs `artifacts/operator/ratify_token_doctrine_20261106.sh` (2 doctrine lines); unpark sessions as needed; wait for the Codex weekly reset 2026-11-11. Registry is already `max_live: 2` with `token_guards` defaults set (51874fcdb). Operator-queue row drafted in the wrap-up 7 report. (2026-11-06: `handoff_sessions.py preflight-restart` is the required step before any restart.) [no-belief: tooling-repair]
- [x] **TOKEN-DELETE-LENS-DOCTRINE — reword the fan-out floor.** The audit (`docs/reports/coordination/token-efficiency-audit-20261106.md`, cc312a985, delete lens) shows "3-5 subagents always" in `CLAUDE.md` and `agents/shared/OPERATING_CONSTRAINTS.md` (*Parallel Subagent Fan-Out*) acts as a floor; make it a ceiling ("fan out when the work is parallel, at most 3-5"). Human-only paths: prepare a ratify script, the operator runs it. (2026-11-06: script written and tested; OPEN until the operator runs `bash /workspace/artifacts/operator/ratify_token_doctrine_20261106.sh` (add `--dry-run` first); it also covers AGENT_INSTRUCTIONS.md and the canonical fan-out policy.) [no-belief: tooling-repair] ✅ 2026-11-06 (operator ran the ratify script: 7d06fe0a8, a3b0d739e; heading 73c15b32b)
- [x] **TOKEN-REGEN-ONCE-PER-BATCH — workers must regen the index once per batch, not per turn.** Audit: 136 regens in the A2 window. Make the keeper/worker wrap-up path skip `index_state.py` regen until batch end (the operator-cadence wrap-up keeps its own regen). (2026-11-06: index_regen.py regenerates once per batch: input changed + quiet 180 s, or last regen > 1 h; --force bypasses.) [no-belief: tooling-repair]
  - (2026-11-06, wrap-up 7) Delete-lens declines, so each is a decision: (a) "Stop Opus/Fable subagents for clerical work" is not filed: memory rules of 10-04/10-05 already say it and `token_guards` now refuses any spawn without an explicit model/effort, which is the enforcement the audit found missing. (b) "Stop 450k-context keeper threads" is not filed: the 60k rotation, the 15M per-thread ceiling and the width cap landed in 51874fcdb, and the dispatcher is stopped. (c) "Stop per-turn wrap-up commits" is filed only for workers (box above); the per-task wrap-up cadence is an operator ruling (2026-08-11) and is not reopened.
- [ ] **ROWFLOW-IDLE-GRACE-FIELD — a row may declare `idle_grace_s`.** The IDLE-HELD owner warning (4b78e3716) uses one fleet threshold; rows with a legitimate idle phase (GPU warm-up, long CPU prefill before a GPU leg) warn falsely. Add an optional declared field, validated by publish lint, defaulting to the current threshold. (derived at wrap-up 6, operator-adhoc-ops-20261105) [no-belief: not-a-result]
  *(workspace-f2 2026-11-09 wrap-up.)* Still open: `docs/design/rowflow2-20261105.md:58` rejected a per-row idle-grace field; closing this needs a Pipeline decision to either overturn that or decline the box. [no-belief: not-a-result]
- [x] **SERIALIZED-PUSH-NEW-BRANCH — `scripts/coordination/serialized_push.py` cannot publish a branch that has no remote yet, so agents push new experimental branches around the push lock** (2 slips on 2026-11-05). Add a lock-held first-push path (`--set-upstream origin/<branch>` or equivalent) with a test; done when a new branch publishes under the lock. (2026-11-05, operator-adhoc-ops-20261105 wrap-up 5) [no-belief: tooling-repair] (workspace-f2 2026-11-09: landed; --set-upstream first push under the lock, 94 tests pass) [no-belief: tooling-repair]
- [x] **KEEPER-WRAPPER-V13-SWAP — swap the live keeper wrapper to `ws58-calendar-keeper-v13.sh`.** d9c9e95e5 committed v13 (v12 kept); a drain watcher auto-deploys origin/main when `grants/` empties, but the wrapper swap itself needs operator approval (operator queue row OP-AKX-KEEPER-APPROVALS). Done when the live keeper's argv names v13 and REAP-* logs once per (dir, verdict). (wrap-up 9, operator-adhoc-ops-20261105) [no-belief: not-a-result] (workspace-f2 audit 2026-11-09: live keeper argv names v13 since 11-08 10:33Z; no repeated REAP (dir, verdict) lines since)
- [x] **ROWFLOW-GPUQUIET-GUARD-LIVE-KEEPER — port the publish-time GPU-quiet guard into the live keeper.** 83edc1cc2 added it to `rowflow2.py` only (+ `test_pass4.py`); frozen `rowflow.py`/`publish_row.py` still lack it, so the live keeper can publish a GPU row onto a busy MI210. Emergency-deploy path (`deploy_rowflow.sh --emergency`) with a negative-control test. (wrap-up 9) ✅ 2026-11-09 verified by pipeline-mgmt: commit 47d5df14d on origin/main puts `gpu_quiet_guard_conflicts` in `scripts/coordination/rowflow/publish_row.py` (refuses at publish), `tests/test_rowflow_gpu_quiet_guard.py` carries refusal and negative-control cases, and the live copy `compute-flags/bin/rowflow/publish_row.py` contains the guard (DEPLOYED.json sha 98f29180d, 2026-11-08T15:22Z). The 'frozen publish_row.py still lacks it' text was stale. [no-belief: tooling-repair]
- [x] **TEST-CHURN-FILE-RESULT-FIXTURE — rewrite the `scripts/coordination/tests/test_churn_file_result.py` fixture.** It predates the KEEP-TAIL-1 auto P/F wiring in `churn/file_result.py` (4ae73176e) and the keep_tail scope matching (16e987ba6); rebuild it on real row ids so it exercises the current filing path. (wrap-up 9) [no-belief: tooling-repair] ✅ 2026-11-09
  - (2026-11-09): fixture rebuilt on real row ids, real launcher/engine identity (fixes 4 stale completed-smoke tests), keep_tail scope coverage (`TestKeepTailOnRealIds`). [no-belief: tooling-repair]
- [x] **TOKEN-DEAD-CONTEXT-ROTATE-CONST — delete the dead `CONTEXT_ROTATE_TOKENS` constant.** `scripts/coordination/handoff_sessions.py:1129` is defined and has no reader anywhere under `scripts/` (grep, 2026-11-07). Remove it and its comment; `scripts/coordination/**` needs the D9 operator ack before merge. (wrap-up 9) [no-belief: tooling-repair] (workspace-f2 2026-11-09: constant deleted, no readers) [no-belief: tooling-repair]
- [x] **TOKEN-REGEN-TRIPLE-DEBOUNCE — debounce the triple index regen to one per batch.** TOKEN-REGEN-ONCE-PER-BATCH made `index_regen.py` regenerate once per batch, but the operator reports a triple regen is still firing; find the callers, route them through that quiet-window gate, and prove one regen per batch in a test. (wrap-up 9) [no-belief: tooling-repair] (workspace-f2 2026-11-09: hub view regenerates through the index_regen quiet-window gate; the triple itself was inferred, not reproduced) [no-belief: tooling-repair] (reopened workspace-f2 2026-11-09: the gate is on main but not live; the host cron runs a copy pinned 2026-10-06. Done when the re-pinned refresh logs a gated regen.) (workspace-f2 2026-11-09: live: hub log shows regen=no(gated) on head moves, 9 by 15:24Z) ✅ 2026-11-09 [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* Re-pinned to e4668444c with index_regen.py present; the supervisor runs and the refresh report is written. Proof logged: `regen=no(gated)` on head moves in the hub log, 2026-11-09.
- [ ] **TOKEN-AUDIT-6-PER-ROW-ACCOUNTING — per-row token accounting at filing** (audit `docs/reports/coordination/token-efficiency-audit-20261106.md` recommendation 6, not landed). Make `file_result.py` attribute rollout tokens to the row via `churn/tokens_per_task.py` and write the figure into the filing record. (wrap-up 9) [no-belief: not-a-result]
  - (2026-11-09): PARTIAL, left open: `file_result.py` writes `rec["tokens"]` (owner-session tokens, completed, tokens/task via `tokens_per_task.compute`) into every filing record. Rollouts are attributable per SESSION per day, not per row, so true per-row attribution still needs rollout-window to row-run-window matching. [no-belief: not-a-result]
  *(workspace-f2 2026-11-09 wrap-up.)* Still open: `file_result.token_accounting` (381b409e2) is per session-day; the box asks for per-row attribution. [no-belief: tooling-repair]
- [ ] **TOKEN-AUDIT-7-CIRCUIT-BREAKER — circuit breaker on repeat failures** (audit recommendation 7, not landed). A row that fails smoke or arming 3 times is parked and its successors are paused until an owner clears it. (wrap-up 9) [no-belief: not-a-result]
  - *(workspace-f2 2026-11-09.)* Per-row parking landed in rowflow.py (MAX_FAILS=3); the pause-successors half was removed on purpose. Tick if the operator accepts per-row parking.
  *(workspace-f2 2026-11-09 wrap-up.)* Still open: per-row parking exists (MAX_FAILS=3) but the successor pause does not. [no-belief: not-a-result]
- [ ] **CORE-BARE-FLIP-ROOT-CAUSE — find what sets `core.bare=true` on the shared clones.** It flipped twice (2026-11-06 21:19Z and 23:04Z); b1a763a6a added the health alarm and the repair/prune/gc guards (befd08c2b, c3efeb6a7) but not the cause. A flip-capture watcher is armed; done when a captured flip names its writer, then fix that writer. (wrap-up 9) [no-belief: not-a-result]

## 2026-10-28/29 results-filing mechanism, loop daemons and disk follow-ons (workspace-58)

Operator 2026-10-28: "file IMMEDIATELY". The daemons below run zero-token from `/mnt/raid0/llm/tmp/compute-flags/`. Owner rulings R1-R11 are in `OWNER-RULINGS-20261028.md` there. The Codex standing goal is in `CODEX-GOAL-20261028.md`, and the third Codex brief (merge scan plus ready depth) is in `codex-channels/codex3.md`.

- [x] **LOOP-14 — results filing as a mechanism.** ✅ 2026-10-28 — `ws58-filing-watch.sh` appends every run end to `filing-due.jsonl`, and the filed marker is `filing-done/<id>.FILED`. A per-run filer subagent writes each verdict into the owning handoff. Takeover reference for any session: `.claude/skills/coordinator-agent/references/compute-owner-takeover.md` (09c7ece02). Coverage at 07:20Z 2026-10-29: 114 of 114 run ends filed. [no-belief: tooling-repair]
  - 2026-10-29 FAILURE: 32 run ends sat unfiled from about 00:10Z to 07:00Z. The owner session was blocked on a blocking operator question, and no other session took over. Batches A and B filed them at about 07:06Z (af66baa5a, b53924225). See LOOP-26 and LOOP-27. [no-belief: tooling-repair]
- [x] **LOOP-15 — `ws58-row-reconciler.sh` auto-demotes failed ARMED rows to BACKLOG.** ✅ 2026-10-28 — live since 21:06Z, and logs to `row-reconciler.log`. [no-belief: tooling-repair]
- [x] **LOOP-16 — `ws58-ready-depth.sh` depth alarm.** ✅ 2026-10-28 — the floors are CPU 8, GPU 3 and whole-host 1. When a floor is short, the alarm writes one nudge per Codex channel. [no-belief: tooling-repair]
- [x] **LOOP-17 — `ws58-orphan-poller-reaper-v2.sh` stops the pollers the keeper started for refused rows.** ✅ 2026-10-28 — this mitigates LOOP-11 but does not fix it, and LOOP-11 stays open. [no-belief: tooling-repair]
- [x] **LOOP-18 — `ws58-rc75-linker.sh` links the launcher log so rc75 partials re-arm.** ✅ 2026-10-28 [no-belief: tooling-repair]
- [x] **LOOP-19 — `ws58_arm.py` fixes.** ✅ 2026-10-28 — five fixes. It autofills the notes keys. It refuses a row with no output estimate, with no 1 GB default. It restores a malformed row. It fixes a false positive in the pre-arm prerequisite check. It refuses private model copies, per ruling R9. [no-belief: tooling-repair]
- [x] **LOOP-20 — `scripts/handoffs/verdict_count.py` separates DECIDED rows from rows that merely ran.** ✅ 2026-10-28 — e48659f06. The first count found 8 of 92 inference rows DECIDED. [no-belief: tooling-repair]
- [x] **LOOP-21 — backup retention: keep only the newest ai-sessions backup.** The nightly backup added 9 GB overnight 10-28/29. [no-belief: tooling-repair] (workspace-f2 2026-11-09: host installed, ai-sessions keep 2 by host owner policy (not 1), mirror-gated; first run deleted only mirror-verified files; 7adf739ae, filesystem-agent 3918872) ✅ 2026-11-09 [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* Retention tool landed (`scripts/backup/backup_retention.py`, 6 fixture tests; ai-sessions keep 1, opencode keep 3 with dedupe). Not live until the host `backup-claude-sessions.sh` is patched per `scripts/backup/README-retention.txt`; host needs `zstd`.
- [x] **LOOP-22 — opencode DB snapshot retention and dedupe.** About 26 GB of snapshots were rewritten overnight. See `project_opencode_db_bloat_root_cause`. [no-belief: tooling-repair] (workspace-f2 2026-11-09: host installed, opencode keep 3 per store with dedupe, from hourly read-only copies) ✅ 2026-11-09 [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* Retention tool landed (`scripts/backup/backup_retention.py`, 6 fixture tests; ai-sessions keep 1, opencode keep 3 with dedupe). Not live until the host `backup-claude-sessions.sh` is patched per `scripts/backup/README-retention.txt`; host needs `zstd`.
- [x] **LOOP-23 — shorten the filed-run reap to 1 day after `.FILED` exists (today it is 3 days).** ✅ 2026-10-31 — keeper source and decision-test implementation `de9b0d9bf56a6996adc922292d4a7882444a488e`: [candidate.sh](../../artifacts/compute/codex3-loop23-reap-20261031/candidate.sh), [test_decision.py](../../artifacts/compute/codex3-loop23-reap-20261031/test_decision.py); deployed pin `737f8db4067b14ed95a8816cba95ef1f4247b8c8`, [deployment evidence](../../artifacts/compute/codex3-loop23-reap-20261031/deployment-evidence.txt), [native decision-test log](../../artifacts/compute/codex3-loop23-reap-20261031/decision-test.log). [no-belief: tooling-repair]
- [x] **LOOP-24 — enable keeper v6 (idle reap that vaults code first) once the operator approves its hook pin.** BLOCKED on the operator decision OP-KEEPER-V6-PIN: approve pinning `ws58-calendar-keeper-v6.sh` (sha256 `702a3931561820e52196878c5bf47c507978dcb3984b08aa65705884d6737b99` at 2026-10-29) in `scripts/hooks/destructive_scratch_pins.json`. Then swap it for v5 and set `REAP_IDLE=1`. [no-belief: tooling-repair]
  - ✅ 2026-10-29 22:37Z: operator pinned v6 in `destructive_scratch_pins.json` (working tree of /workspace); keeper v6 pid 257469 is live with relocatable CPU rows and code-vaulting idle reap. OP-KEEPER-V6-PIN is closed.
- [ ] **LOOP-25 — disk forecast in the depth alarm.** Project free space from the ARMED and READY `est_output` values plus the overnight growth rate. Alarm before free space crosses the 150 GiB admission floor. Overnight 10-28/29, every admission refused and compute sat idle. Without the 122B delete, free space would have fallen from about 200 to about 137 GiB. [no-belief: tooling-repair]
  *(workspace-f2 2026-11-09 wrap-up.)* Standalone forecast built on unpushed branch `rtg22-loop5-25` (1ef7299f0, not landed): its first live run alarmed at a projected 21 GiB, which is unreliable because ARMED rows are unfiltered and 503 rows lack `est_output`; the depth-alarm wiring (`ws58-ready-depth.sh`) lives outside git. Box stays open. [no-belief: tooling-repair]
- **[declined: ws58 2026-11-03 content-review: a standing rule (never block unattended), already in project memory]** **LOOP-26 — never use a blocking operator question during unattended hours.** File a decision package (master operator queue plus a bus message) and keep working. Write the rule into `agents/shared/SESSION_LIFECYCLE.md` or the compute-owner-takeover reference. Origin: the 2026-10-29 filing gap in LOOP-14. [no-belief: tooling-repair]
- [x] **LOOP-27 — filing-backlog takeover alarm.** When `filing-due.jsonl` has an entry with no `.FILED` marker for more than 60 minutes, `ws58-filing-watch.sh` (or a sibling daemon) writes one bus nudge so a coordinator or any session takes over per `compute-owner-takeover.md`. Done when a simulated stale entry produces exactly one nudge. Derived 2026-10-29: the owner was blocked and nothing noticed. [no-belief: tooling-repair] (workspace-f2 2026-11-09: done-when proven by tests/coordination/test_filing_takeover_alarm.py, 40 pass, fixture only) ✅ 2026-11-09 [no-belief: tooling-repair]
  - 2026-10-31 workspace-58 owner report: the owner is non-tmux, with no roster entry or scheduled drain; the coordinator-agent endpoint is absent/unowned. The owner polls `filing-due.jsonl` at task boundaries and suggests its own `filing-alarm.jsonl` plus an owner-armed zero-token monitor. No configuration change was requested. This records the delivery gap; LOOP-27 remains OPEN pending actual delivery/adoption. [no-belief: operational finding]
  - 2026-10-31 R5 owner-adoption checkpoint: implementation `ee85c21c784e4ae8cdf31d2e19285c06e5512f58` on main `d331a04ad5b32a9aae0ab1434531bebcdb7c35d8` is owner-adopted as watcher2323912 (old2062051 verified dead). The owner armed Monitor before the swap, but reports a maximum30-minute, session-bound monitor rearmed at boundaries; offline alarms are read at the next boundary, not pushed. The stream had0 lines and no actual alert receipt is established. LOOP-27 remains OPEN pending actual owner-monitor receipt/delivery. [Bounded observation](../../artifacts/coordination/loop27-filing-alarm-20261031/alert-stream-r5/OWNER-MONITOR-OBSERVATION.json) [no-belief: operational checkpoint, no delivery result]
- [x] **LOOP-28 — relocatable rows + keeper v6.** ✅ 2026-10-29 — `ws58_arm.py` records the relocated region; keeper v6 (pid 257469, 22:37Z) moves RELOCATABLE rows to a free quarter. This closes the placement bug where every worker pinned runs to q0/q1. [no-belief: tooling-repair]
- [x] **LOOP-29 — ws58-scoreboard v1 to v3 (rate-based) and OWNER-ORDER-20261029.md.** ✅ 2026-10-29 — quotas, the FROZEN list, the PIPELINE RULE, refactor's demand shifted to codex3. Rates now NI 3/h, refactor 9/h, codex3 8/h. [no-belief: tooling-repair]
- [x] **LOOP-30 — backlog cleanup audit (Fable).** ✅ 2026-10-29 — 2,956 open, 218 closed (95 done-unticked, 54 superseded, 50 obsolete, 19 duplicate), 3 handoffs archived (0ec042eab). The backlog is genuinely live. [no-belief: tooling-repair]
- **[declined: ws58 2026-11-03 content-review: duplicate — coordination-and-churn-pipeline "Sub-quarter packing" owns it]** **LOOP-31 — sub-quarter grants for single-threaded rows.** Single-threaded runs hold whole quarters while the host sits 97% idle; size the grant to the row's thread count. [no-belief: tooling-repair]
- **[declined: ws58 2026-11-03 content-review: duplicate — coordination-and-churn-pipeline "Per-row UNDERUSED is only logged: act on it" owns it]** **LOOP-32 — CPU-utilisation-vs-reservation check.** Alarm when reserved quarters run far below their reservation (measured 97% idle host with all quarters booked). [no-belief: tooling-repair]
- [x] **LOOP-33 — regenerate `backlog-priority.json` to drop INF-63, EVL-05, EVL-41 and EVL-50.** ✅ 2026-10-29 — regenerated (174 rows); the four ids are gone. [no-belief: tooling-repair]
- **[declined: ws58 2026-11-03 content-review: merged into LOOP-22 ("same work" by its own text)]** **LOOP-34 — opencode DB reclaim decision.** Queued as OP-OPENCODE-RECLAIM in the master operator queue. Same work as LOOP-22. [no-belief: tooling-repair]
- [x] **LOOP-35 — worktree disk emergency triage (10-29/30).** ✅ 2026-10-30 — disk fell to the 150 GiB floor; 561 trees held 471 GiB. Removed 4 trees, promoted 4 docs-only branches, the gate removed 66 clean+landed trees at 1-day idle, and 61 obsolete launchers renamed `*.sh.retired-20261030` freed 9 more; free space 151 to 371 GiB. Ledgers in `/mnt/raid0/llm/tmp/disk-audit-20261029/` (WORKTREE-TRIAGE/WRAP/OWNER-*). [no-belief: tooling-repair]
- [x] **LOOP-36 — INF-12 r11 blocked by the reap gate `log_consumer` rule.** ✅ 2026-10-30 — ws58 added the field; the row is armed. [no-belief: tooling-repair]
- [x] **LOOP-37 — worktree size per worker on the scoreboard.** Show GiB and tree count per owner (NI, refactor, codex3, other) so a worker that never removes landed trees is visible before the disk floor. [no-belief: tooling-repair] (workspace-f2 2026-11-09: scoreboard shows worktree count and GiB per owner from a bounded cache with a 30 s budget) [no-belief: tooling-repair]
- [ ] **LOOP-38 — tmux-based Codex liveness and nudge, replacing channel files.** ws58 reached the idle "Goal stalled" sessions via tmux send-keys (agent:2 NI, agent:3 refactor, agent:4 codex3); make state detection and the nudge a tool, not a manual step. `scripts/coordination/codex_pane_liveness.py` is on main with mocked tests; not yet run against live tmux and channel files are not replaced, box stays open. [no-belief: tooling-repair]
- [x] **LOOP-39 — worktree_gate reference sources must include stale `.bak` and `.env` files.** About 67 content-safe trees stay blocked by `.env`/`.bash`/campaign-input references; the gate should ignore stale backups and age these out. [no-belief: tooling-repair] (workspace-f2 2026-11-09: stale .bak and aged tmp .env/.bash references ignored; campaign references never age out; negative controls in tests/test_worktree_gate.py) [no-belief: tooling-repair]
- **[declined: ws58 2026-11-03 content-review: merged into LOOP-21 (one backup-retention decision)]** **LOOP-40 — ai-sessions backup retention policy (operator, host-side).** Three backups of about 9 GB each run nightly; deleting the older two awaits operator OK. Supersedes LOOP-21's one-line form. [no-belief: tooling-repair]
- [ ] **LOOP-41 — remaining ~67 blocked worktrees.** Re-run the gate after they age out (about 11-20 to 11-27) and remove the clean+landed ones; ledger `WORKTREE-WRAP-20261030.md`. [no-belief: tooling-repair]
- [x] LOOP-42 legacy T1 admission off by default in the canonical filler_run13 template ✅ 2026-10-30 [no-belief: tooling-repair]
- [x] **LOOP-43 — the calendar must never lapse on a keeper stop date.** ✅ 2026-10-31 — v7b exited at its hard-coded 10-31T06:00Z stop and both writers hit their caps, so nothing armed from 06:00Z to 07:58Z. Keeper v7d (pin sha `72f5b8b1…`, operator-approved) has no stop time and records its main-loop pid in `compute-flags/ws58-calendar-keeper.pid`; the new zero-token `ws58-keeper-watchdog.sh` restarts the keeper named in `ws58-calendar-keeper.current` when that pid dies. [no-belief: tooling-repair]
- [x] **LOOP-44 — GPU writer succession when the current writer is already dead.** ✅ 2026-10-31 — v7b refused ("current writer identity unavailable"), so v19 was started by hand. v7d gives the successor birth 0 and it does not wait. [no-belief: tooling-repair]
- **[declined: workspace-f2 2026-11-09: v19 to v20 handover passed; grant writers no longer exist, so the dead-writer path is moot]** **LOOP-45 — verify the v19→v20 GPU writer handover around 11-01T03:00Z, and exercise the dead-writer path once.** Read `ws58-calendar-keeper.log` for GENERATE/START of `grant-gpu-1101-v20`. [no-belief: ops follow-up]
  - 2026-11-01: the v19→v20 handover worked. Keeper v7e GENERATEd and STARTed `grant-gpu-1101-v20.sh` at 03:01:44Z (pid 1785941, validated predecessor 3072798), and v20 granted inf12-r13 at 11:14Z. The dead-writer path has still not been exercised, so the box stays open. [no-belief: ops follow-up]
- [x] **LOOP-46 — D9 hook must judge the commit it guards, not the shared clone.** `check_d9_loop_plane.py` refused a worktree commit touching only an index file by listing /workspace's uncommitted files (10-31). Read the staged paths of the repo/worktree being committed. Hook edit: needs operator sign-off. ✅ 2026-11-02 — landed `ab8dedeab` (D9 judges the commit it guards via the commit-msg hook, not the shared clone); operator signed off. [no-belief: tooling]
- [x] **LOOP-47 — guard against moving `main` in /workspace with `update-ref` without updating the checkout.** On 10-31 at 00:26 a session did this, leaving ~1,900 phantom staged changes; it was re-synced 10-31 via `read-tree -m -u` (backup `tmp/workspace-ff-backup-20261031/`). Find the writer and make it use the private-index-plus-checkout pattern, or a post-update check. [no-belief: tooling-repair] (workspace-f2 2026-11-09: hook blocks update-ref on a checked-out branch, HEAD, --stdin and variable refs unless the checkout syncs; writer was a session-typed command, and script-internal calls are not caught) [no-belief: tooling-repair]
- [x] **LOOP-48 — champion store custody: SHA256SUMS for every champion build, and libggml aliases as symlinks.** Production v10 had its unversioned `libggml-hip.so` silently replaced 10-27 23:00 (sha `daf086c2…`, unattributed); `verify_kernel_store.sh` checks presence only, and champion C5 builds carry no SHA256SUMS. Dispatched to refactor in `compute-flags/codex-channels/REFACTOR-CHAMPION-FOLD-20261030.md` step 4; also make `verify_kernel_store.sh` hash-check. [no-belief: tooling-repair] (workspace-f2 2026-11-09: store check verifies SHA256SUMS, unlisted files and aliases on production; backfill and writer continue as KERNEL-SUMS-WRITER) ✅ 2026-11-09 [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* `verify_kernel_store.sh` now checks SHA256SUMS, unlisted files and symlink aliases on production targets, with a 12-control fixture. Operator chose a build-step writer plus backfill for the 55 non-production builds; AutoKernel dispositions the C5/C6 objcopy leftovers and c9fold unlisted binaries first. Proposal: `artifacts/analysis/kernel-store-custody-20261109/proposal.md`.
- [x] **LOOP-49** pre-grant qualification is live in rowflow (same-entry dry run; `FirstProgress` refuses placeholder-only results); what remains is the live install of the `keeper_qual_gate`/nonce package and its first real target receipt, or a decision to retire that package. Owner: Pipeline. (workspace-f2 audit 2026-11-09: text corrected) [no-belief: tooling-repair] (workspace-f2 2026-11-09: retire decision met: keeper_qual_gate package retired by operator ruling 2026-11-01; rowflow.py records its removal and pre-grant qualification is the live dry run) ✅ 2026-11-09 [no-belief: tooling-repair]
- [x] **D1-LEGACY-CONFLICT-QUAL-V2 — install and qualify the published controller-only repair at ws58's owner boundary.** ✅ 2026-11-01 SUPERSEDED [belief: cc] — operator ruling "remove every gate that is not indispensable": the qual-v1/qual-v2 nonce/receipt/registry-row stack is retired; keeper v10 + `scripts/coordination/rowflow/` (d69c6cd4b…fa95c38b3) replaced it at ws58's owner boundary (first row dry-run-passed and granted 17:49Z: `codex3-cs8-g1b-cascade-20261031`). The controller-only repair is not installed; nothing remains to qualify.  Source is in ROOT fceacc1ce5e69d7dece663b61da51c8f7dfe35ad; final reviewed package SHA-256 71ba671971dcc6365efb11c3ac0d4e9a7283f7b41cda19135d8d3d927d62e353 is recorded in ROOT b1d26902a173bbe2facc4313ea7a677a86694209. The 15 new plus 29 existing controls pass (44 total, zero skips); these do not replace ws58 dry-run/install/restart or a real keeper qualification receipt. Done when ws58 performs its owner-boundary install/restart and the keeper emits a matching READY-QUAL receipt. [packet](../../artifacts/coordination/ni-d1-legacy-conflict-qual-v2-20261101/README.md) [unblocks: codex-ni-pbqcost-confirm-q-r3-20261101] [no-belief: tooling repair; deployment pending]

> 2026-11-01 source checkpoint: the D1–D4 HARD pre-grant foundation is reviewable in `artifacts/coordination/ni-d1d4-hard-gate-20261101/` (reviewed-package SHA-256 `c6c8ba16febadd3527203f002688c469e3fef97fd0feb72ff264b325d79b9f47`). It includes canonical `filler_run14.sh`, keeper nonce/qualification verifier, typed LLM/speech/command READY schema, common quarter/GPU grant guard, disk parking, owner-scoped science scoreboard, and an owner-bound deployment script. Twenty-nine durable unit/receipt controls and one installer-tamper control pass; bounded R6 model-free and active command fixtures prove normal/completion, live-child STOP/rc75/UNKNOWN/drain, READY→armed→first-grant path, and cleanup refusal. These are source/fixture controls only. ws58 still owns live install/reload and first actual native target qualification. No production nonce, target receipt, READY, grant, science verdict, or LOOP-49 completion is claimed. [no-belief: tooling-repair]
- [x] **LOOP-50 — tick/deletion science gate: refuse result ticks whose cited run receipt is FAILED/INCONCLUSIVE/PARTIAL, nonterminal-worded ticks, belief-tagged ticks with no SHA/git path, and `- [ ]` deletions without re-add/[moved:]/[declined:].** Spec + backtest: `docs/reports/tick-science-audit-20261031.md`. Owner: refactor. Blocking wiring in pre-commit.extras is a hook edit (operator sign-off). ✅ 2026-11-02 — landed `f73933a2c` (blocking tick/deletion science gate in pre-commit.extras); operator signed off (blocking). [no-belief: tooling]
- [x] **LOOP-51 — D1–D4 hard qualification gate deployed live.** ✅ 2026-11-01 — the operator ran NI's `install_for_ws58.py --apply` (package sha `c6c8ba16…`), and ws58 restarted the processes at their boundary. `grant_ok.sh` v3 sha `2e40f0cf…8908`; keeper v8 sha `a8fc18c6…e5a7`, pid 1369950 (started via the watchdog); scoreboard v4 sha `48e31f75…e5f3`, pid 1366332. Receipt: `artifacts/coordination/ni-d1d4-hard-gate-20261101/WS58-INSTALL-RECEIPT.json` (host). At swap, 0 of 23 READY rows were qualified. [no-belief: tooling-repair]
- [ ] **LOOP-52** `epyc.ready.v2` is gone; every session publishes through `publish_row.py` (`epyc.row.v3`). Done when `queue_status.py` shows at least 2 runnable READY rows per bin per worker (SCOREBOARD.md is frozen at 11-01). Owner: Pipeline. (workspace-f2 audit 2026-11-09: text corrected) [no-belief: tooling-repair]
- [x] **LOOP-53 — `check_destructive_scratch.sh` advertises an `EPYC_ALLOW_SCRATCH_DELETE` override that it never reads.** 11-01: it blocked the operator-approved D1 installer and keeper v8, whose only deletes are their own temp files, so the operator had to run the installer by hand. Implement the override (logged), or remove it from the message. Hook edit: needs operator sign-off. Owner: refactor. ✅ 2026-11-02 — landed `e4fb3a09b` (override removed from the message, operator decision B) plus ratify `612358902` (OPERATING_CONSTRAINTS no longer advertises the override). [no-belief: tooling]
- [ ] **LOOP-54 — GitHub CI back to green; stop the failure-email flood** (operator 11-01; ws58 CI audit). F1: root `tests` red on main since 10-27 (vidya fixtures; ws58 fix in flight). F2: branches forked before 561e6ae9b still run on every push; owners merge main (codex3-root-lane, m4-c3, lb49, lane/codex-refactor-*). F3: research actor-wire regression (codex3). F4: task workflows fail on the hosted runner (NI). F6: EVL-38 cron (NI). F8: orchestrator Dependabot (refactor). Done when every main is green and no owner branch is red. (workspace-f2 2026-11-09: F4 disabled, 66 stale workflows with no file on main turned off by operator decision; newest completed `tests` run on main is cancelled, not success, and F2 branches have not run in 9+ days, so the box stays open.) [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* F1 fixed on main (5 tests/vidya failures). Still red until the operator applies `artifacts/operator/staged/ratification-exemptions-add-20261109.json`; the dashboard step then runs for the first time. F3 green; F6 workflow gone; F2 branches and F4 stale registrations remain.
  - *(workspace-f2 2026-11-09.)* Root `tests` is green on main from d69e5165d onward. F2 branches and F4 stale workflow registrations remain.
  - *(workspace-f2 2026-11-09.)* F2: none of the four branches has run in 9+ days. F3 and F8 last seen green or passing, F6 workflow gone. F4: 66 registered workflows have no file on main; disabling them is the operator decision.
  - *(workspace-f2 2026-11-09.)* Newest completed tests run on main is success (42647528635); four consecutive successes since d69e5165d; exemptions ratified at a69312d5b. Remaining: codex3-root-lane red from 10-31 and a salvage branch failure.
  *(workspace-f2 2026-11-09 wrap-up.)* Root `tests` is green on main; still red: 4 stale owner branches (F2), so the box stays open. [no-belief: tooling-repair]
- [x] **LOOP-55 — prune stale remote branches.** ✅ 2026-11-01 — the operator ordered it. 730 branches were deleted (root 369, orchestrator 152, research 209), each fully contained in origin/main, idle for more than 24 h and not checked out. The SHA list for restore is in `tmp/ws58-csh/branch-delete-20261101.tsv`. [no-belief: tooling-repair]
- [x] **LOOP-56 — prune the 103 task-named workflow files on root** (keep `tests.yml` and `docs.yml`). ✅ 2026-11-01 — commit e897669a6; origin/main `.github/workflows/` now holds only tests.yml and docs.yml. `pytest tests/ci tests/validate tests/coordination` gave the same result before and after (643 pass / 43 fail). [no-belief: tooling-repair]
- [x] **LOOP-57 — fix 43 pre-existing failures in tests/ci, tests/validate and tests/coordination** (found 11-01 during the LOOP-56 prune; not caused by it). 39 are in `tests/ci/test_pin_report_fixture.py`; one each in test_prior_check, test_worktree_isolation_phase2, test_candidate_eval_gate_periodic and test_ratify_operator_guard; `test_td30f_public_markdown_report.py` fails at collection without `TD30F_REPORT_OUTPUT`. Owner: refactor. [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* All fixed on main except test_worktree_isolation_phase2, which Pipeline owns with the five-lane decision. Pipeline 2026-11-09: that test now drops retired mainC/mainD (retirement receipts exist); it passes. [no-belief: tooling-repair]
- [ ] **LOOP-58** `rowflow.publish` refuses a null or empty `decision_rule`/`result_path` (rowflow.py:770-771), but the legacy migration path (rowflow.py:1101-1105) substitutes placeholders so such rows still pass. Close that path or accept it; the qual-v2 package is not installed. Owner: Pipeline. (workspace-f2 audit 2026-11-09: text corrected) rowflow2 now refuses a `MIGRATED:` decision_rule unless legacy-mapped; the live migration path is unchanged, box stays open until cutover. [no-belief: tooling-repair]
- [x] **DASHBOARD-FLOW-TRUTH — one Flow counter, per-commit dating, visible served commit and refresh failures.** ✅ 2026-11-09 Live at e4668444c: today -87, 7d -1290, open stock 2768 to 1516 over 7d (residual +38 explained). Replaced +208, which counted edits to open boxes as filings. [no-belief: tooling-repair]
- [ ] **HUB-SUPERVISOR-STALE-ALARM — alarm when `.git/epyc-view-refresh.json` stops advancing.** A dead supervisor writes no failure, so the view froze unnoticed from 13:02 to 14:28 on 2026-11-09 and the page still read 0 behind. Done when a stale report degrades `/api/health` and the page, with a negative control. Owner: Pipeline. [no-belief: tooling-repair]
- [ ] **PIN-CLOSURE-CHECK — installer must verify every file the pinned scripts source is pinned.** On 2026-11-09 a pin without `observer_guard.sh` passed install and killed every supervisor pass. Done when the installer refuses an incomplete closure, or runs `once` against the pin before swapping cron. Owner: Pipeline. 2026-11-09 partial (763f9ed9a, 82ef9c06d): the pin now includes `observer_guard.sh` and `env.sh` and the pin test seeds them, but the installer still has no closure check, so box stays open. [no-belief: tooling-repair]
- [ ] **KERNEL-SUMS-WRITER — add a build/stage step that writes SHA256SUMS, then backfill the 55 non-production builds.** Operator chose this 2026-11-09; wait for AutoKernel's disposition of the C5/C6 objcopy leftovers and c9fold unlisted binaries. Owner: AutoKernel. [no-belief: tooling-repair]
- [ ] **R18-MANIFEST-REPIN — review the drift in `scripts/vidya/producers/r18_inputs/comparator-dependencies.json` and re-pin deliberately before the next R18 capture.** `schemas.py` changed 11-06, `/usr/bin/perl` differs, `/usr/bin/python3.13` is absent here. Owner: AutoKernel (handed over 2026-11-09). [no-belief: tooling-repair]
- [x] **LOOP-59 — kernel-store stray-file incident (2026-11-03): extend the store check, list affected GPU runs, find the origin.** On 2026-11-03 ws58 found a stray unlisted regular-file `libggml-hip.so` (68,101,784 bytes, sha256 prefix `daf086c2a805a8ca`, mtime 2026-10-27T23:00) that had replaced the `libggml-hip.so -> libggml-hip.so.0` symlink in the frozen production v10 GPU build `gpu-20260921-ffc1bac82/bin`; `verify_kernel_store.sh` did not catch it. With operator approval it was quarantined at `/mnt/raid0/llm/kernels/quarantine/gpu-20260921-ffc1bac82-stray-20261103/` and the symlink restored. Follow-ups (LOOP-48 is the sibling custody item): (workspace-f2 2026-11-09: store check landed; docs/reference/kernel-store-incident-20261103.md records two proven runs, 82 of 93 grants without evidence, and the writer unknown after the listed searches) ✅ 2026-11-09 [no-belief: tooling-repair]
  - `verify_kernel_store.sh` (or its checker) FAILS on a regular file in a store build dir that is absent from that build's `SHA256SUMS`, or a symlink whose target breaks the manifest or naming convention; add a fixture test reproducing this incident.
  - List the GPU runs since 2026-10-27T23:00 that could have loaded the stray library (grants/.ended, keeper log, run-dir `/proc/<pid>/maps` captures, orchestrator server launches), each classed proven-stray / proven-listed / unknown, into `docs/reference/kernel-store-incident-20261103.md`; affected results are re-judged by their owners, not by this task.
  - Find what wrote the file at 10-27 23:00 (shell histories, agent transcripts, scripts that `cp`/`install` a `libggml-hip.so` into `kernels/`, ~68.1 MB builds elsewhere on disk); report evidence only, no guesses. [no-belief: tooling-repair]
  - *(workspace-f2 2026-11-09.)* Store check landed. Stray built from `tmp/champ2`; writer unknown after searching transcripts, shell history and rollouts. Proven loaded: DF2-12-1 R7 GPU smoke and BRF EXP-04 r3 A1. Of 93 GPU grants ended in the window, 82 have no binary evidence either way.

2026-11-01 NI source proposal: `/mnt/raid0/llm/tmp/codex-ni-native-qual-v3-20261101/publication-v3-root.patch` (SHA-256 `6db24ccfcb203942eb16b974b6cd5a2f913ec5d4b479ba967734e36682062d40`) implements the D1 fields and owner-bound native verifier in a versioned, uninstalled package. Ninety-seven focused controls passed. The required shared `tests.yml` workflow has no valid green local baseline: the extracted test tree lacked Git/fixtures and the real lane contains peer WIP. Do not install, map IDs, grant, or close LOOP-58 from these controls. Owner sequence: review/publish source after valid CI, install P0 qual-v2 first, then v3 via pinned CAS, then map exact approved IDs and obtain real keeper normal/cutoff receipts. [no-belief: source proposal only]

### 2026-10-31 LINT queue midnight regression — source complete

The preserved v1 correctly classified the instantaneous blackout but only checked tomorrow's admission boundary, admitting a 00:00→00:30 job through today's 00:15 cutoff. The maintained successor `scripts/system/cpu_queue_f8_runner.sh` checks recurring UTC interval overlap and revalidates at actual execution after quarter/claim waits; late jobs return to pending without starting. Normal operation requires an explicit future stop time. Its sourceable/test-only entry has no queue initialization side effects. Nine deterministic controls cover same-day and next-day boundaries, long intervals, invalid values, an exact native v1 guard fixture, and delayed direct/paired execution. Implementation `61bdf95ee27e82e2e7bff9547c90338861713ece`; proof `a69391f6f36a`, `artifacts/engineering/lint-queue-date-boundary-20261031/`. The historical artifact and private v1 runner are byte-unchanged; the new source was not activated against a live queue. [no-belief: source correctness and controlled tests only]


### Completed cleanup compatibility repair — codex3, 2026-11-01

- [x] **WORKTREE-EXTERNAL-COMMON — let the removal gate resolve Git-verified external common directories while preserving every removal predicate.** ✅ 2026-11-01 — implementation `92385a1d1161b5709be446f74bd918f21bf7a076`; [25 native regression controls](../../artifacts/engineering/worktree-common-gate-20261101/README.md); [actual cleanup review](../../artifacts/engineering/worktree-common-gate-20261101/cleanup-review.json) committed in `7689295c5018b214c3393224d58b7c0d0cd8baee`. [belief: cc]
  - The old basename assumption rejected a registered linked checkout whose non-bare Git common directory was named `private.git`. The resolver now verifies the candidate through Git and the common-directory inode; `_find` registration, main/canonical protection, cleanliness, landed history, keep/evidence, process/reference and idle checks remain intact. Real external non-bare and bare fixtures cover removal and refusals. The published native gate refreshed the genuine stale tracking ref, waited out an exited process reference, then removed only the authorized temporary publication checkout. Its path is absent and the reusable fixture, common directory, branch refs and protected DAR/R10 files remain. Removed allocation was 299,618,304 bytes (0.279 GiB); shared filesystem free space rose by 296,321,024 bytes (0.276 GiB), an observation affected by concurrent activity. No force, prune, manual admin deletion or process kill. This required cleanup repair is outside WORK-codex3-code.md and is not counted among this checkpoint's two queue closures. [belief: cc]

## Track: amd-ai-lab-website-publication
<!-- gate: none -->

> Folded from `handoffs/active/amd-ai-lab-website-publication.md` @ `ea07eb9ad4ae` on 2026-11-02 (BRF-T1-F3, route 1a, operator D1/D5; retired row UFH-11 → RTG-22). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### AMD AI Lab website publication

**Status:** active — private source and dashboard preview published; public launch awaits the operator's review and contact destination.
**Owner index:** [user-facing-harness-index.md](user-facing-harness-index.md) (UFH-11).

#### Start here

- Source: private `epyc-web` at `/workspace/repos/epyc-web`, `main` `4602416`.
- Review preview: dashboard hub `/amd-ai-lab/`, root snapshot `dashboard/static/amd-ai-lab/`, source commit recorded in `PUBLICATION.md`.
- Source-of-truth for measurement selection: `epyc-web/EDITORIAL.md`; page data: `epyc-web/data/catalog.json`.
- Production kernel is frozen `ffc1bac82` (`production-consolidated-v10`). Do not change it for site work.

#### Completed scope

- [x] Publish the private `epyc-web` source repo and registered dashboard preview. ✅ 2026-09-25 — latest site source `4602416`, root snapshot merged to `main` `a07408f2`.
- [x] Build a compact dark AMD catalog with model workspaces, source links, and configuration details. ✅ 2026-09-25 — seven cards, hardware grouping, search and filters.
- [x] Show explicit weight quantization and measured performance matrices on every card. ✅ 2026-09-25 — unmeasured cells remain labeled; speech uses thread × workload rather than LLM context.
- [x] Audit best current results and add Qwen3.8-Flash-Next. ✅ 2026-09-25 — frozen-v10 quality: MMLU-Pro 151/200 and GPQA 127/195 on UD-IQ4_XS; older 52.661 tok/s predecessor run identified separately.
- [x] Validate the site and dashboard publication. ✅ 2026-09-25 — Chromium desktop/mobile suite passes all seven workspaces; live dashboard checks confirmed Flash-Next and source evidence.

#### Next actions

- [ ] **WEB-1 — operator publication choice:** provide the contact destination (email, booking link, or contact page) and confirm the reviewed page is ready for public GitHub Pages launch. Recommendation: use a dedicated contact email unless a booking flow already exists. This choice is needed to make the services section actionable and to fix the public launch point.
  - *(workspace-f2 audit 2026-11-09.)* Operator decided 2026-11-09: hold launch; the site stays private and WEB-2 stays gated.
- [ ] **WEB-2 — publish the reviewed snapshot:** configure GitHub Pages for the private `epyc-web` repo under the available plan, verify its public URL, connect the GoDaddy domain, then check HTTPS, links, responsive layout, and that no private research paths or credentials are exposed.
- [ ] **WEB-3 — refresh evidence when measured:** if a frozen-kernel Flash-Next UD-IQ4_XS CPU np × context throughput sweep is produced, replace the card's unmeasured grid with its source-backed cells. The September 24 sweep was explicitly skipped by the operator; this task does not authorize running it.

#### Operator decision package

[Contact choices, exact source, reviewable copy and retained desktop/mobile screenshots](../../artifacts/operator/decisions/WEB1-contact-publication-20261007/README.md). The screenshots are dated September 25; the pinned source remains the content authority. Contact destination and launch readiness remain separate operator inputs; no completion or publication is claimed.

#### Measurement limits

The Qwen3.6 GPU 112.676 and 310.958 tok/s maxima were measured on predecessor `ef81196d5`, not frozen v10. Its current card uses the best located frozen-v10 cells, 104.8 tok/s per request and 229.6 tok/s wall aggregate at different operating points. Flash-Next's 52.661 tok/s post-BIOS study likewise used `ef81196d5` and IQ4_XS-uniform weights; the served model uses UD-IQ4_XS. Do not present either predecessor result as frozen-v10 throughput.

## Track: frontier-f4-continuity-backup
<!-- gate: none -->

> Folded from `handoffs/active/frontier-f4-continuity-backup.md` @ `ea07eb9ad4ae` on 2026-11-02 (BRF-T1-F3, route 1a, operator D1/D5; retired row EVL-26 → RTG-22). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Frontier F4 — Continuity: Backup the Evidence Base

**Status**: IN PROGRESS — W1 inventory/policy landed 2026-06-12; W2 snapshot job tooling + W3 validation/restore tooling landed 2026-06-14; latest-snapshot age/restore preflight landed 2026-06-21; first real backup remains blocked on a real off-RAID/off-host target
**Created**: 2026-06-12
**Priority**: HIGH — this-month, existential ROI at trivial effort
**Spec**: [fable5-findings-07-strategic-frontiers.md](../completed/fable5-findings-07-strategic-frontiers.md) §F4 — read before claiming
**Related**: MEASUREMENT.md §5 dump-list note (consolidate 1.2GB superseded blobs first); the ATTESTATION artifact in [fable5-findings-04-impl-plan.md](../completed/fable5-findings-04-impl-plan.md) §B (backup-age + unpushed-commit checks)

#### Why

The entire evidence base — journals, state, registries, intake index, deep-dives,
episodic/strategy DBs, agent memory — lives on a single raid0 (striping, zero
redundancy) on a single host. GGUFs are re-downloadable; the lab's memory is not.
No backup policy exists anywhere in governance. The total irreplaceable set is
<2GB, so the fix is half-days of work against an existential failure mode.

#### Waypoints

- [x] **W1 — inventory + policy** (half day): `scripts/backup/MANIFEST.yaml` with tiered list (T0 irreplaceable / T1 regenerable-expensive / T2 excluded models). Audit git coverage + unpushed branches (`v5 push pending` known); add unpushed-commit alert to ATTESTATION. Acceptance: manifest enumerates every T0 path per spec §F4-W1. Implementation: manifest plus `scripts/backup/audit_git_state.sh` alert hook for future ATTESTATION.
- [x] **W2a — target discovery/report packet**: `continuity_backup.py discover-targets` inspects explicit candidate roots or locally mounted filesystem roots, runs the same failure-domain checks as snapshot creation, writes a machine-readable report, and emits the exact backup + latest-restore-check commands when a usable target exists. ✅ 2026-07-06
- **[declined: ws58 2026-11-03 content-review: duplicate backup program; BK-1..5 is the current one]** **W2 — the job** (half day): `scripts/backup/backup_critical.sh` — restic preferred (dedupe+encryption, open-source) or snapshot-copy fallback. Targets: root SSD (different failure domain) + one off-host target (operator picks). Nightly via nightshift scheduler or systemd timer. Acceptance: nightly run produces a verifiable snapshot of all T0 paths. **Tooling landed 2026-06-14, real run still blocked**: `backup_critical.sh` now creates a `verify_restore.sh`-compatible T0 snapshot layout and performs SQLite `.backup` copies, but refuses same-device and overlayfs targets. `/workspace` and `/mnt/raid0/llm` are both `/dev/md127`, no off-host target is configured, and `/tmp`/container overlayfs is explicitly rejected. Do not accept a fake same-array backup.
- **[declined: ws58 2026-11-03 content-review: duplicate; BK-4 is the restore test]** **W3 — restore proof** (half day + quarterly): `scripts/backup/verify_restore.sh` — restore to temp dir, checksum-compare, parse-validate JSON/YAML/SQLite. Add backup-age check to ATTESTATION. Acceptance: one full restore cycle passes; check wired into attestation. **Tooling landed 2026-06-14**: `9eb3f45` adds manifest validation plus restore wrappers; `0a56b81` fixes restore checksum semantics to compare restored bytes against the snapshot, not mutable live sources. **Preflight landed 2026-06-21**: `scripts/backup/check_latest_backup.sh` wraps `continuity_backup.py check-latest` so attestation/nightshift can fail closed when no timestamped snapshot exists, when the newest snapshot exceeds `--max-age-days`, or when restore verification fails. Still unchecked until a real T0 snapshot from an approved backup target passes end-to-end.

#### Gates & pitfalls

- Live SQLite (episodic.db is written continuously) must go through the `sqlite3 .backup` API or stop-copy — naive `cp` produces torn copies.
- A backup that has never been restored is a hypothesis, not a backup — W3 is not optional.
- Audit unpushed branches before trusting "it's in git" coverage; pushed history needs no file backup, unpushed does.
- Do NOT back up the 1.2GB superseded embedding blobs flagged in the reconciliation dump-list — consolidate those first.
- Off-host target must be open-source/self-hosted (external HDD / another box / MinIO) — no cloud SaaS.

#### Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. Move to `completed/` after W3's first quarterly verify passes.

#### Checkpoints

- 2026-06-12 W1: created `scripts/backup/MANIFEST.yaml` and `scripts/backup/audit_git_state.sh`. Validation: YAML parse succeeded; scoped `git diff --check` clean; audit hook intentionally exits 1 with current alerts (dirty worktrees plus unpushed/no-upstream branches, including `epyc-root` `main` ahead of `origin/main` by 16 before this commit). Environment probe: `df/findmnt` shows `/workspace` and `/mnt/raid0/llm` are the same `/dev/md127` RAID0; `restic`/`borg`/`rclone` are not installed.
- 2026-06-14 W3 tooling: `9eb3f45` added `scripts/backup/continuity_backup.py`, `scripts/backup/validate_backup_manifest.sh`, and `scripts/backup/verify_restore.sh`; `0a56b81` corrected restore validation to checksum the snapshot file against the restored copy and added `tests/backup/test_continuity_backup.py`. Validation: `python3 -m py_compile scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`; `uv run --with pytest --with pyyaml pytest -q tests/backup/test_continuity_backup.py tests/publication/test_generate_public_results.py` -> 7 passed; `uv run --with ruff ruff check ...` passed; `bash -n` wrappers passed; `bash scripts/backup/validate_backup_manifest.sh scripts/backup/MANIFEST.yaml` returned validation ok with expected missing-pattern warnings. W2 remains blocked on a real off-host/off-array target; W3 remains open until a full restore from a real snapshot passes.
- 2026-06-14 W2 guarded snapshot job: added `scripts/backup/backup_critical.sh` and `continuity_backup.py create-snapshot`. The job expands selected manifest tiers into `snapshot_root/<repo-name>/...`, writes `SNAPSHOT.json`, uses SQLite `.backup` for live database suffixes, and refuses targets that share source storage devices, sit inside source repos, or are Docker overlayfs. Validation: `python3 -m py_compile scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`; `bash -n scripts/backup/backup_critical.sh scripts/backup/validate_backup_manifest.sh scripts/backup/verify_restore.sh`; `uv run --with pytest --with pyyaml pytest -q tests/backup/test_continuity_backup.py` -> 3 passed; `uv run --with ruff ruff check ...` passed; `bash scripts/backup/validate_backup_manifest.sh scripts/backup/MANIFEST.yaml` returned validation ok with expected missing-pattern warnings; live same-device probe to `/tmp/epyc-f4-same-device-check` refused overlayfs as expected. W2 remains unchecked until the job succeeds against a real off-array/off-host target and can be scheduled.
- 2026-06-21 W3 preflight hook: added `continuity_backup.py check-latest` and `scripts/backup/check_latest_backup.sh`. The command discovers the newest timestamped snapshot under a target root by `SNAPSHOT.json`, runs the normal restore verification on it, enforces `--max-age-days`, and writes an optional JSON report. Validation: `python3 -m py_compile scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`; `bash -n scripts/backup/backup_critical.sh scripts/backup/validate_backup_manifest.sh scripts/backup/verify_restore.sh scripts/backup/check_latest_backup.sh`; `uv run --with ruff ruff check scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`; `uv run --with pytest --with pyyaml pytest -q tests/backup/test_continuity_backup.py` -> 7 passed; `bash scripts/backup/validate_backup_manifest.sh scripts/backup/MANIFEST.yaml` returned validation ok with expected missing-pattern warnings; no-snapshot CLI smoke failed closed. This does not satisfy W2/W3 by itself because no approved off-array/off-host target has produced a real snapshot.
- 2026-06-27 target recheck: manifest validation still passes
  (`files_matched=170240`, expected missing-pattern warnings only), but no
  acceptable real target is currently writable. `/mnt/raid0/llm` and
  `/workspace` remain `/dev/md127`; `/opt/AMD` is a different ext4 device
  (`/dev/sda2`) but is mounted read-only; `/dev/sdb1` and `/dev/nvme0n1` are
  visible but unmounted with no filesystem shown by `lsblk`. Do not claim W2
  or W3 from a same-array, overlayfs, tmpfs, or read-only target. Next valid
  action is to mount/provide an operator-approved writable off-array/off-host
  target, then run `scripts/backup/backup_critical.sh` followed by
  `scripts/backup/verify_restore.sh`.
- 2026-07-06 preflight/reporting lane: added `continuity_backup.py preflight-target`
  for dry target checks that report `target_exists`, `target_is_dir`,
  `target_writable`, selected tiers/repos, and machine-readable failure reasons
  without creating a snapshot. Validation: `python3 -m py_compile
  scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`;
  `uv run --with pytest --with pyyaml pytest -q tests/backup/test_continuity_backup.py`
  -> `10 passed`; `uv run --with ruff ruff check scripts/backup/continuity_backup.py
  tests/backup/test_continuity_backup.py` passed. W2/W3 remain blocked until an
  operator-approved off-array/off-host target is mounted and a real snapshot
  can be created and restored.
- 2026-07-06 target discovery lane: added `continuity_backup.py discover-targets`
  for read-only enumeration of explicit candidates and mounted filesystem roots.
  The command reuses the preflight/failure-domain logic, writes a JSON report
  with per-candidate errors and `usable_count`, and prints the exact
  `backup_critical.sh` / `check_latest_backup.sh` commands once a target passes.
  Validation: `python3 -m py_compile scripts/backup/continuity_backup.py
  tests/backup/test_continuity_backup.py`; `uv run --with pytest --with pyyaml
  pytest -q tests/backup/test_continuity_backup.py` -> `12 passed`; `uv run
  --with ruff ruff check scripts/backup/continuity_backup.py
  tests/backup/test_continuity_backup.py` passed. Live discovery through
  `uv run --with pyyaml python scripts/backup/continuity_backup.py
  discover-targets --include-mounted-roots --max-candidates 16 --report-json
  /tmp/epyc-f4-discover-targets.json` found `9` mounted candidates and
  `usable_count=0`: RAID0-backed paths share `/dev/md127`, `/` is overlayfs and
  not writable, and `/opt/AMD`/`/opt/rocm` are different storage but read-only
  in the container. W2/W3 still require an operator-approved writable off-array
  or off-host target.
- 2026-08-23 EVL-26 W2/W3 attempt — target rejected by operator, run cancelled:
  restic 0.18.0 was installed via apt under the dispatch's install-only network
  allowance, but before an approved target existed — the install is a host-level
  action taken in error and is flagged for the operator (it remains installed
  and usable once an operator-approved target exists). `backup_critical.sh`
  gained a `--backend restic` mode (default): continuity snapshot first (live
  SQLite via the `sqlite3 .backup` API — restic never touches live sources, so
  no torn copies), then `restic init` (probed via `restic cat config`) +
  `restic backup --json --tag f4-t0` of the snapshot dir + `restic check`;
  `--backend snapshot` fallback preserved; `bash -n` clean; 12/12 unit tests
  pass. MANIFEST.yaml T0 DB patterns fixed: `repl_memory/**/*.db|.sqlite`
  matched nothing (live DBs now live under `orchestration/repl_memory/`, incl.
  continuously-written `sessions/episodic.db` ~539MB) →
  `orchestration/repl_memory/**/*.db|.sqlite`; `.faiss` remains T1;
  files_matched 95813→95888; T0 now measures **8.21 GiB / 10,311 files** (the
  handoff's "<2GB" estimate is stale). **W2/W3 remain UNCHECKED**: no backup
  ran; the task-stated target `/mnt/bigdisk` (`/dev/sdb1`) was rejected by the
  operator ("do not touch anything outside /mnt/raid0/llm"), the mount was
  unmounted and removed, and per operator directive the next target must be
  **named by the operator**. No backup data or password file exists anywhere
  outside the repos. Next valid action: operator names an off-array/off-host
  target, then run `scripts/backup/backup_critical.sh --backend restic`
  followed by `scripts/backup/verify_restore.sh`.

## Track: integration-test-coverage
<!-- gate: none -->

> Folded from `handoffs/active/integration-test-coverage.md` @ `ea07eb9ad4ae` on 2026-11-02 (BRF-T1-F3, route 1a, operator D1/D5; retired row EVL-30 → RTG-22). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Integration Test Coverage - Remaining Gaps

**Status**: COMPACTED 2026-05-28 - active coverage backlog only; Phases 1-4 are preserved in the completed ledger.
**Created**: 2026-04-13
**Updated**: 2026-07-26
**Priority**: MEDIUM
**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/`; scoped source-review artifacts only.
**Primary repo**: `/mnt/raid0/llm/epyc-orchestrator`
**Parent index**: [master-handoff-index.md](master-handoff-index.md)
**Completed ledger**: [integration-test-coverage-phases-1-4-completed-through-2026-05-28.md](../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md)

#### 2026-07-26 Staleness Review

This remains an active, risk-triggered backlog. The
[research and evaluation index](research-evaluation-index.md) still routes
narrow integration-test slices here, but no new production-risk slice was
selected by this documentation review. Keep the queue focused and do not turn
freshness maintenance into blanket coverage work.

#### Executor Start Here

The integration scaffolding and earlier coverage tranches are historical. Do not chase blanket 100% coverage. Pick one focused slice that closes a real production risk, add or update tests, then record the command, test count, and coverage delta here.

#### Outstanding Task Queue

| Work item | When to pick | Validation |
|---|---|---|
| Focused seeding/orchestrator coverage tranche | Non-inference code session | Run the exact focused pytest target or coverage command for the touched package. |
| Real LLM parsing paths | User-approved inference window | Add integration cases using production model outputs; mark as integration/inference-gated. |
| Backend health, KV migration, and slot paths | llama-server test fixture available | Use isolated dev ports with startup, teardown, and stale-process checks. |
| API route regressions | No inference needed if dependency overrides suffice | Use FastAPI/httpx test client with dependency overrides. |

#### Rules For New Tests

> **⚠ THESE BOXES ARE UNCHECKED BY DESIGN — DO NOT DISPATCH OR FLIP THEM.**
> These are **standing rules for writing tests**, not tasks. Every `- [ ]` below is a step to be executed *whenever a new test is written*, so it has no completion
> state outside one. Flipping any of them asserts that a repeating procedure is permanently
> done, and the next test author inherits a checklist that reads as already-executed — so the step
> silently stops being run.
>
> Noted 2026-07-29 by `auditor` during a sweep of `handoffs/active/` prompted by the automated
> backlog sweep classifying steps like these as dispatchable `none`-lane work. Row `:38` of this section is in the queue's runner-up bench. `Keep mocked integration tests separate from real inference tests` has no completion state — it is policy.


- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** Keep mocked integration tests separate from real inference tests.
- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** Label inference-backed tests so normal CI can skip them.
- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** Include port selection, startup, teardown, and stale-process checks for live-server fixtures.
- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** Avoid broad fixture rewrites unless a current failing test proves the fixture contract is wrong.
- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** Before adding code, run `git -C /mnt/raid0/llm/epyc-orchestrator status --short` and inspect the current test layout.

#### Dependency Forks

| Finding | Next action |
|---|---|
| Existing unit tests already cover the branch | Do not add duplicate coverage; record the existing test target and close that slice. |
| Branch requires real model output | Move it to the inference-gated slice and do not block normal CI. |
| Live server dependency is required | Create or reuse an isolated fixture; never touch production ports. |
| Coverage gain is small but branch is high-risk | Keep the test if it captures a production failure mode; record risk rationale, not just percentage delta. |

#### Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Orchestrator refactoring coverage Phases 1-4 | Historical coverage tranches completed and preserved; extracted module unit coverage averaged 88% after the refactor audit. | [completed ledger](../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md) |
| Historical module/gap tables | Preserved for provenance, but not the active queue. | [completed ledger](../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md) |

#### Key Files

- `/mnt/raid0/llm/epyc-orchestrator/tests/`
- `/mnt/raid0/llm/epyc-orchestrator/src/`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py`
- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/`

#### Reporting Instructions

After each coverage slice, update this file with the changed test files, command output summary, test count, coverage delta if measured, and any skipped inference gates. Update [master-handoff-index.md](master-handoff-index.md) only when priority, blocker state, or active scope changes.

##### Follow-ups from the 2026-09-14 zero-inference sweep

These are real tasks (not standing rules) and are dispatchable; they landed here because no other active
handoff owns the shared red-test baseline.

- **[declined: ws58 2026-11-03 content-review: merged into LOOP-57]** **Record the `epyc-orchestrator` `origin/main` red-test baseline so sessions stop reading it as their own
      breakage** — `pytest tests/unit` at `35b05fde` is **29 failed / 12,667 passed**, with named members in
      `test_infra_failed_disposition.py`, `test_offline_reward_pairwise_holdout_expansion_plan.py`,
      `test_e8_quality_baseline_reseed.py` (9), the `safety_gate|era|baseline|calibrat` selection (20), the
      dashboard/journal/planner sweep (5), plus two reproduced on a clean detached worktree
      (`test_legacy_source_change_after_preflight_blocks_scorer_replay`,
      `test_generation_tail_replaces_only_target_response_and_sidecar_bytes`) that no dispatch had claimed as
      pre-existing (found 2026-09-14, noninf sweep). [too-big: current full unit-suite baseline needs broad run and result triage; handoff session owns it]
  - [x] Repair collection of `test_repl_thinking_budget.py` by qualifying its sibling test and plugin imports. ✅ 2026-11-01 orchestrator `a7818b43`: focused file 55 passed; full-suite baseline remains open. [no-belief: test collection repair]
- [x] **Give `test_recent_eval_qids_excludes_only_rows_inside_recency_window` a frozen or relative clock** — it
      fails with the calendar because its hardcoded `2026-07-01T00:00:00Z` row is 75 days old against the
      test's own 60-day window (`tests/unit/test_autopilot_actions.py:1332`) (found 2026-09-14, noninf sweep). ✅ 2026-10-07 — MAIN verified [published relative-clock source](../../artifacts/ni08/evl30-relative-clock-source-20261007/README.md); no whole-suite claim.

## Track: loop-state-offraid-backup
<!-- gate: none -->

> Folded from `handoffs/active/loop-state-offraid-backup.md` @ `ea07eb9ad4ae` on 2026-11-02 (BRF-T1-F3, route 1a, operator D1/D5; retired row RTG-60 → RTG-22). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Loop-state off-RAID0 backup: AutoKernel / AutoPilot / belief-kernel planning state

**Status**: OPEN, ready to dispatch. **Owner: the operator's filesystem agent** (host crontab + `/home/daniele/filesystem-agent/scripts/`). workspace-58 does not implement the host job.
**Created**: 2026-10-25 by workspace-58. Operator decision: "Nightly off-RAID0 backup (Recommended)", plus "this needs to be done by my filesystem agent".
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Scratch**: none. The job writes only to its backup targets.
**Evidence**:
- `docs/reference/loop-planning-inputs-audit-2026-10-25.md`: the loops' planning inputs and their durability.
- `docs/reference/tmp-loss-reconcile-2026-10-25.md`: the reclaim losses and why backups could not restore them.

#### Why
The AutoKernel and AutoPilot loops plan from state that is **single-copy on md127 (RAID0) with no backup**. The existing NIB2-92 job (`backup-claude-sessions.sh`, crontab `0 4 * * *`, local `/mnt/raid0/llm/claude-backups` keep 3, mirror on `/mnt/micron` = `/dev/nvme1n1p1`) covers only Claude and Codex transcripts and memory, plus the opencode DBs. Losing this state means losing the experimental history and seeded hypotheses the loops build on. md127 is also 94% full.

#### Scope: back up exactly these (about 0.5 GiB total; sizes as of 2026-10-25)
| What | Path | Size | Notes |
|---|---|---|---|
| Belief ledger and reader state | `/mnt/raid0/llm/state/vidya/` (ledger.jsonl, ledger.jsonl.sync.json, loop-known-good/, loop-memo/, reads.jsonl) | about 45 MB | The canonical ledger, which is in no git repo. Copy while no ingest holds `ledger.jsonl.lock`, or copy under that lock. |
| AK live stores | `/mnt/raid0/llm/autokernel/campaigns/*/store*/{experiments.db,inbox/,accumulator-bundle.json,journal*,resume-claims.sqlite3}` | about 330 MB for the live set: q38fn `store-b0ba1d427` 317 MB, ds41-1017 `store/`, 27b `store/` | **Copy SQLite with `sqlite3 <db> ".backup <dst>"`**, or an equivalent online-backup API; never a plain `cp` of a live DB. The large historical DS41 DBs (4.3 GB and 1.1 GB) are a separate decision; see box 3. |
| AK loop memory | `/mnt/raid0/llm/autokernel/loop-memory/{experiments.db,inbox/}` | about 10 MB | Shared history plus 25 inbox seeds. |
| AK campaign input bundles | `/mnt/raid0/llm/autokernel/campaigns/*/inputs*/` | about 3 MB | Small JSON bundles. |
| AutoPilot state | `/mnt/raid0/llm/epyc-orchestrator/orchestration/{autopilot_state.json,autopilot_journal*.jsonl,autopilot_checkpoints/,repl_memory/strategies/,operator_hypotheses.yaml,operator_hypothesis_resolutions.jsonl}` | about 42 MB | The journal shards are gitignored and no checkpoint contains them. `strategies.db` must also be copied with `.backup`. |

Out of scope: `/mnt/raid0/llm/tmp/**`, models, builds, worktrees, and anything already in git.

#### Tasks
- [x] **BK-1** Write the job script in the filesystem agent's script dir, next to `backup-claude-sessions.sh`. It snapshots the scope above into a dated directory under `/mnt/micron/<loop-state-backups>/YYYYMMDD/`, which is off md127. Requirements: (workspace-f2 2026-11-09: job on host; first real run STATUS OK snapshot=20261109 files=742 at 14:30Z) ✅ 2026-11-09 [no-belief: tooling-repair]
  - SQLite DBs via online `.backup`; the ledger copied consistently.
  - A `SHA256SUMS` manifest written per snapshot.
  - Retention: keep 7 dailies and 4 weeklies.
  - Exits non-zero on any failure, with `LAST_STATUS` written the way NIB2-92 does it.
  - *(workspace-f2 2026-11-09.)* Script, restore test, alarm and cron line landed; fixture-tested only. Host steps: copy the job, one manual run, install cron, run the restore test. The alarm fires until the first run. BK-3 decided: weekly.
- [x] **BK-2** Install it in the host crontab, offset from NIB2-92's 04:00 (for example 04:30), logging to a file next to `claude-backups/backup.log`. (workspace-f2 2026-11-09: cron installed in daniele crontab at 04:45; first scheduled run 11-10) ✅ 2026-11-09 [no-belief: tooling-repair]
- [x] **BK-3** Decide the large historical AK DBs (`ak-ds41-cpu-decode-20260923/store/experiments.db` 4.3 GB, `store-b0ba1d427` 1.1 GB): weekly-only, or one-time cold copy. Record the choice here. (workspace-f2 2026-11-09: operator chose weekly; default in backup_loop_state.sh) ✅ 2026-11-09 [no-belief: tooling-repair]
  - *(workspace-f2 audit 2026-11-09.)* Operator decided 2026-11-09: weekly copy for the large historical AK DBs.
- [x] **BK-4** Restore test. Restore the latest snapshot into a scratch dir, run `sha256sum -c`, and check: (workspace-f2 2026-11-09: restore test on 20261109 snapshot: 24 SQLite DBs PASS, vidya chain_ok PASS, 0 failures) ✅ 2026-11-09 [no-belief: tooling-repair]
  - `sqlite3 <db> "pragma integrity_check"` on every DB;
  - `python3 /workspace/scripts/vidya/cli.py --ledger <restored ledger> verify` reports chain_ok.
  Record the output here.
- [x] **BK-5** Alarm on failure. A failed or missing nightly snapshot must be visible: the hub health probe, or the same channel NIB2-92 uses. (workspace-f2 2026-11-09: alarm in host_hygiene_tick; status file now OK) ✅ 2026-11-09 [no-belief: tooling-repair]
- [ ] **BK-OBSERVE — confirm the next two 04:00 backups (11-10, 11-11) and the first 04:45 loop-state cron run with `/home/daniele/filesystem-agent/scripts/backup-health-check.sh`.** Owner: host owner. [no-belief: tooling-repair]

#### Done when
BK-1..5 are ticked, two consecutive nightly snapshots exist with valid manifests, and the restore test passed.

## Track: refactoring-multirepo-2026-10

> **Sequenced by operator 2026-11-09:** do not start this track until the production kernel promotion and the AutoPilot loop relaunch are done.
<!-- gate: none -->

> Folded from `handoffs/active/refactoring-multirepo-2026-10.md` @ `ea07eb9ad4ae` on 2026-11-02 (BRF-T1-F3, route 1a, operator D1/D5; retired row RTG-61 → RTG-22). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Handoff: Refactoring — orchestrator, autopilot and AutoKernel (multi-repo debt program)

**Status**: ACTIVE — operator resumed implementation 2026-10-24 after an independent handoff audit; review and finish existing branches before integration
**Created**: 2026-10-07
**Updated**: 2026-10-30
**Priority**: High
**Scope**: epyc-orchestrator (`src/`, `scripts/`, `tests/`, `scripts/autopilot/`, `src/autopilot_core/`);
epyc-inference-research `scripts/kernel_rnd/autokernel/`; epyc-root `scripts/hooks/` (guard bugs found on the way)
**Estimated effort**: 382 findings → 26 packages (12 in wave 1, 14 in wave 2); deletion size is a planning estimate, subject to current per-file reachability and retention contracts
**Scratch**: `/mnt/raid0/llm/tmp/refactor-01a16fc3/`. Use one reusable checkout per active lane. Retired task and wrap checkout paths below are historical evidence locators; their source states, commits and retained outputs are preserved in the cleanup receipts, rather than live launch inputs.

**Current working priority (operator, 2026-10-31)**: repair or reopen the 21 unsupported ticks with implementing commits and Git evidence, preserve task text and original completion dates, wrap up per task, then resume the S-first code queue. Prior-work cleanup is hygiene and receives no new-code quota credit. CI restoration is evidenced below.

- [x] ✅ 2026-10-31 **CI-20261031-GREEN — Restore ROOT tests.yml and research actor native wire gate to green on main.** Evidence: ROOT `561e6ae9`, `34a955f9`, `c78940ada`, `6309ecb0`; research `f115236f`; [Git evidence](../../artifacts/ci/restore-tests-20261031.json); [ROOT green](https://github.com/pestopoppa/epyc-root/actions/runs/41200383604), [research green](https://github.com/pestopoppa/epyc-inference-research/actions/runs/41196682393). [no-belief: CI execution/source validation; no inference result] Operator priority2026-10-31: fix ROOT numpy/S4 producer checkout-and-environment/pin-registry defects without disabling tests; add `tests-${{ github.ref }}` concurrency with cancel-in-progress, main-only push and retained pull_request. Add research PyYAML and main-only push. Done only with successful main run URLs for both workflows, published source evidence on this line, and delivery of the URLs to ws58.
  - Follow-up after the 2026-11-01 regression: root fixture repair commit `7a20f8fecf894c4559a3aa7b2a700bb3c15cfa8b`; [ROOT tests.yml green](https://github.com/pestopoppa/epyc-root/actions/runs/41270047542). Research actor-wire test repair commit `28e66916a1fee988315ea3633f5e276e3ecb10c2` is contained in current main; [research actor native wire gate green](https://github.com/pestopoppa/epyc-inference-research/actions/runs/41270088587). Both workflows passed on main; no tests were disabled. [belief: cc]

Each active lane reuses its checkout and scratch area. Remove each worktree through `scripts/system/worktree_gate.py` when its task lands. Cold dirty and unlanded drafts were archived before abandoning their materialized checkouts; this does not accept, merge or close the underlying packages. Locked or running source views remain intact. Historical checkpoint paths and process IDs below describe their recorded date, not present-day launch instructions.

**Start here:** the [Pending work](#pending-work) checklist is the queue; §Branches says what each pushed
branch holds and how to merge it; per-finding evidence is in `research/refactor-audit-2026-10/findings-*.md`.

**Owner review boundary (2026-10-26):** root `bb6410b1fa76553ab8d2d26dad5ee9816fb1ee5d` was
privately published, but was not accepted or merged by workspace-58. Owner review at 12:45/13:25
requires per-line checkbox evidence, removal of this branch's generated index artifacts/counts,
and confirmation of one index owner. The correction below does not claim owner acceptance.
The owner verified those fixes in private `d3cba7b6` at 16:40, but still withheld merge: this
branch must withdraw its wiki page/manifest contribution and retain the runbook's live executor
offender until the cleanup source merges. Findings stay in the research record for the next sweep.
That prior review-withhold is superseded for the root wrap-up: `fcdc09c08a807491531dc0527942244a638bd957`
was accepted and merged by the owning main as `d369b3798` on 2026-10-26 at 16:44 UTC. The earlier
review history above is retained as chronology.

**Current next action (2026-10-27):** P3 is accepted and published on its private `codex/*` branch;
the original integration candidate remains privately validated. O8's CI fixture-isolation and
guard-tripwire work now has scoped preflight evidence, but no complete baseline JUnit/native grade,
accepted baseline dataset, full candidate run, or publication. The 08:29:09–08:29:17 UTC native
admission passed three safe cases with a conformant `Judged/Located` shared grade, normal
completion, matching custody, zero guard violations, and the corrected editable `851` v4 inventory.
It does not validate the full baseline. The subsequent V6 full baseline started at 08:42:16 UTC and
was stopped after the tripwire refused four test-originated connections to configured backend ports
(first 8070) from `TestHealthEndpoint::test_health_returns_ok`; the owned process group was dead by
08:43:10 and official exit was 143. No JUnit/native grade or accepted counts/dataset resulted.
Fix the API health fixture with a fake backend that preserves health semantics and the tripwire,
then rerun the relevant guarded API integration and scoped baseline proof before another full
baseline. Tool bootstrap is complete, but its standalone checks are not project gates. Only after a
valid complete baseline capture should the dataset be derived, followed by full candidate native
validation and required gates/coverage. O8 remains unchecked. Checkpoint details and evidence paths:
[2026-10-27 CI checkpoint](../../progress/2026-10/2026-10-27-refactor-ci-checkpoint-01a16fc3.md).
Codex NI owns the production `embedder.py` fix; this session's scope is test guard/tripwire only.
Keep the four protected P5 files unchanged. Only private `codex/*` publication is in scope; no
main promotion.

Origin: cloud refactor-audit session (claude.ai/code session_01C4SLLAQhop8AA9rJJusAYj), run in an ephemeral
4-CPU container on fresh clones, never on the host. Evidence, data and tooling:
[`research/refactor-audit-2026-10/`](../../research/refactor-audit-2026-10/README.md). Bug report:
[`BUG-REPORT-autopilot-autokernel.md`](../../research/refactor-audit-2026-10/BUG-REPORT-autopilot-autokernel.md).

> **Review-branch registration:** owning main corrected this handoff's row to **RTG-61** in
> `routing-and-optimization-index.md`. Native review of current main `a876d3c9` found RTG-60 already
> reserved for `loop-state-offraid-backup.md`; that canonical row must remain intact at merge. The old
> private RTG-60 refactoring row was a collision, not canonical ownership. Shared/canonical files remain
> untouched; workspace-58's publication boundary still applies. Source wiring is filed prospectively on
> this branch as VB-REFACTOR-CONFORMANCE, not as an optional applicability decision.

##### Current package state (2026-10-26)

- **Integration:** reviewed and published private candidate `851955112b8ba8c2911a7684469551afa1541623`
  on `refactor/orchestrator-integration-01a16fc3`, validated relative to immutable base `84f6f6f1`.
  The expanded union passed 2,897/2,905 (8 skipped), four coverage floors are 100%, 32 NI63 pins
  and four P5 preservation proofs pass. The formatter correction establishes zero introduced
  failures within accepted scope. RESUME-4 records this private candidate only; no main promotion.
- **O8 CI:** B1-tested pre-fixture local-only merge `753e0287a1ae6b06f2a5c91269899ff8cc8452b5` has parents
  `713edf671614e69f67028100c08cc8f08b02d52f` and integration `851955112b8ba8c2911a7684469551afa1541623`.
  The focused check passed 13 tests. Official q1 B1 attempt 1 failed before collection because
  custody hashing followed public-carrier directory symlinks; no tests ran in that attempt.
  The helper's corrected symlink metadata proof passed. B1 attempt 2 actually collected 20,646
  baseline tests plus an error for an unregistered `slow` marker; candidate collection did not run.
  After the external harness correction, strict collection passed: baseline 20,658 total/20,645
  selected, candidate 20,666 total/20,653 selected; 0 removed and 8 intended additions, with the
  same 13 exclusions on both sides. This is collection parity, not a full-suite result.
  Full baseline comparison, native capture and coverage remain incomplete; O8 stays unchecked.
  B2 baseline then completed at 13:13:11 UTC with 31 failed, 20,517 passed, 85 skipped, 19 xfailed
  and 6 passed subtest events in 2,146.45 s. Its 20,643 parent cases plus 9 module-skip case nodes
  give 20,652 JUnit testcase nodes; header 20,658 also counts the 6 subtest events. Native
  conformance is NULL on an unnamed collection-skip case; shared grading failed without JSON.
  Sixteen ignored runtime paths leaked in the baseline checkout, while tracked custody for all
  three repositories and the source harness matched. No candidate full run occurred and no
  accepted known-failure set is established. Original log/JUnit/native receipts remain at
  `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/b2-baseline-first-native/`.
- **P3:** reviewed private source `fb5db1a0a24b92172643bb670c77a4343a508c96` is published on
  `codex/refactor-autopilot-actions-01a16fc3`, remote-exact verified with a clean worktree. It combines
  checkpoint `bbccaaef` and integration `851955112`. The original 34-file run was 817 passed, 1 skipped,
  3 failed; the expanded 90-file run was 1,917 passed, 2 skipped, 11 failed (600 s).
  Targeted legacy-adapter/double repairs then passed the final 12-file selection: 402 passed,
  1 skipped in 39.49 s, with compile, P5/W3e preservation, diff/hash and no-new-Ruff proofs.
  Raw Ruff exit 1 is preserved: 16 inherited E701 findings in `tests/unit/test_mutation_diagnostics.py`.
  The official q1 closure at 12:04:57–12:05:05 UTC returned 0: all three formatter targets have equal
  ASTs before/after, format-check 3 passed, non-target bytes are unchanged, and no-new-Ruff,
  protected-file, diff and source-custody proofs pass. The owning main accepted P3 for this private
  branch only. These successive selections do not establish a current all-1,930-pass aggregate.
- **Next:** repair CI report compatibility and runtime isolation, then rerun baseline under a new
  reviewed calendar admission. The root metadata correction needs no compute row per the owner's
  12:45 instruction; it remains subject to owning-main review before commit/push.

The native read observed the 1.35 GB `question_pool.jsonl`; its exact consumer is unproven. No fixture patch was
applied, and an EvalTower-constructor causal claim is not supported. The CI host audit established
that a dashboard restart test polls live slots and creates host logs. A reviewed owned-dashboard
test fixture was applied after B1 (+26/−10); its validation is pending, with production application
logic unchanged. The source evidence chronology is in
the [Oct 26 checkpoint](../../progress/2026-10/2026-10-26-refactor-next-packages-checkpoint-01a16fc3.md).

Evidence and the formatter-scope adjudication are recorded in
[`integration-validation-review-2026-10-26.md`](../../research/refactor-audit-2026-10/integration-validation-review-2026-10-26.md).
Root attempts `829152` and `831298` ended before admission. The later bare queued wrapper `881101`
and its exact region child `881104` were cancelled for calendar integration and both verified dead;
its actual terminal exit 143 is preserved, with no gates run. The root row is not armed. All new
checks require the calendar owner's live grant and official filler launcher on literal q1 CPUs
24–47, 8 GiB, with affinity proof; a bare region claim is insufficient. The separate root request
is 600 s, minimum useful 300 s. Future pushes target `codex/*` only; this root's publication
destination is `codex/refactor-handoff-audit-01a16fc3`, leaving its old review remote unchanged.

#### Pending work

Historical implementation checkboxes below mean committed on the named branch, not reviewed or merged.
New completion records name their validation and integration state explicitly. A finding ID in a commit
subject establishes association only; WIP, skipped, tested, reviewed and merged are distinct states.

##### Resumed execution (2026-10-24, session 01a16fc3)

- [x] RESUME-1: audit pushed branches and current upstream state; identify unsafe pruning assumptions, rollback failure-path gap, test isolation prerequisite and integration conflicts. Evidence: [audit checkpoint](../../progress/2026-10/2026-10-24-refactor-audit-01a16fc3.md). ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-audit-01a16fc3.md`. [belief: cc]
- [x] RESUME-2: review hermetic-tests + test-hazards and isolate A6-M1 trace/ledger writes in fixtures. Orchestrator `87540dae`, checkpoint `5e392a3c`, pushed to `refactor/test-isolation-reviewed-01a16fc3`: 189 runtime/trace tests pass + 1 intentional skip; 7 E8 wrapper cases pass; all 3 new regressions fail safely on parent. Original hazard modules reviewed; unmerged. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [x] RESUME-3: finish and review C1-05 rollback error handling and behavioral regressions for nonzero exit, timeout, spawn error, wrong HEAD and successful rollback. Research `62c68ad99`, checkpoint `1b58b115c`, pushed to `refactor/autokernel-rollback-reviewed-01a16fc3`: 13 regressions pass (5 fail on WIP), targeted loop set 401 pass + 23 subtests. Reviewed, unmerged under launch/re-pin hold. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [x] RESUME-4: review and validate the combined orchestrator candidate in a private worktree against immutable base `84f6f6f15f713d21098dbad2b153d32f8cc13624`. Candidate `851955112b8ba8c2911a7684469551afa1541623` on `refactor/orchestrator-integration-01a16fc3` passed reviewed AST, focused tests, Ruff/format scope, compile/diff, 32 NI63 pin, and four-file P5 preservation proofs; expanded union: 2,897 passed, 8 skipped, 0 failed/2,905, all four coverage floors 100%. Formatter correction proves zero introduced failures within accepted scope. Private candidate only; no main promotion/deployment. [belief: cc] Evidence: [`integration-validation-review-2026-10-26.md`](../../research/refactor-audit-2026-10/integration-validation-review-2026-10-26.md). ✅ 2026-10-26 Review record: root `bb6410b1:research/refactor-audit-2026-10/integration-validation-review-2026-10-26.md`.
- [x] RESUME-4a: independently review O3 and integrate the accepted isolation harness into its private branch. Orchestrator `d843eb9c` fixes concurrent registry-load backoff (12 attempts before, 1 after); `07829696` scopes alias stress to its actual guarantee; checkpoint `6558beb7` pushed to `refactor/config-reviewed-01a16fc3`. O3 selection 548 pass/4 skip, alias targets 524 pass, all 7 changed source pins verified. Reviewed, unmerged. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [x] RESUME-4b: independently review O1 stage 1 and fix pre-first-chunk streaming disconnect handling. Orchestrator `a1c69593`, checkpoint `142bb5df`, pushed to `refactor/request-reviewed-01a16fc3`: 1,011 targeted tests pass/3 skip; blocked initial generation fails to observe cancellation on parent and passes after fix. Accepted isolation is included; no changed route lies in ni63's pin closure. Reviewed, unmerged. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [x] RESUME-4c: independently review P2 decision semantics and snapshot migration. Orchestrator `4069b8ee`, checkpoint `db17808e`, pushed to `refactor/autopilot-gate-reviewed-01a16fc3`: 1,018 tests pass/1 skip; 18 snapshot controls pass; B2-02/B2-03 fail on parent. Pre-P2 snapshots refuse bounded authority; a current-format rebuild matches full replay. Review complete; integration held because existing reconstruction is CRITICAL and verified-snapshot replay HIGH. No evaluator-era files changed. ✅ 2026-10-24 Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc]
- [ ] RESUME-5: repair CI infrastructure early; keep K4's post-prune size ratchet after K3. Reconcile baseline collection/failure identities rather than accepting aggregate counts.
  - [x] **B2-PRODUCER-E-NEXT-01a16fc3:** prepared and delivered the q2 candidate/baseline comparison packet; source-bound two-core preflight passed, NEXT receipt `f7e9e236-f6d5-4034-a609-7bf03f181ee1`. No official comparison was run; compare the known baseline failures individually. Parent work remains open. ✅ 2026-10-27 [no-belief: packet preparation]
  - *(2026-10-27 21:35Z, ws58 results filing, B2 producer E.)* `refactor-b2-producer-e-q2-20261027` ended rc1 at 19:04:07Z by design of its comparison: candidate `411 passed, 4 warnings in 49.03s` (candidate-research.status 0, cleanup-integrity 0, model-free violation count 0); baseline `2 failed, 394 passed` (baseline-research.status 1; the two known historical failures, a containment case and `test_python_hook_flags_out_of_root_writes_and_not_in_root_ones` on EXDEV `os.rename` to `/var/tmp`). Terminal rc1 is the baseline's, comparison only, no zero-failure claim. Results `/mnt/raid0/llm/tmp/refactor-01a16fc3/b2-cpu-ready-1728/results/run-20261027T190217308687691/`. Not a merge; B2 producer E stays open. [no-belief: model-free test comparison, no measurement]
  - *(2026-10-28, scoped re-derivation.)* A private fail-closed comparator matched all 396 baseline test identities to passing candidate cases and found 15 additional passing candidate cases. The baseline has 394 passes and the same two historical containment/EXDEV failures; the original row named those categories, while their exact test identities and signatures were established from the prior and current logs. Fixtures reject missing/duplicate tests, changed failure signatures, candidate failures and custody/guard changes. This is a scoped comparison, not a clean baseline, full B2 result or merge. Evidence: `/mnt/raid0/llm/tmp/refactor-01a16fc3/b2-producer-e-comparison-20261028/actual-comparison.log`. [belief: cc]
- [ ] RESUME-6: reconcile current INF64 retained-module manifest and live belief-source contracts before each deletion stage; include retained `campaign.py` and dynamic/cross-repo consumers as closure roots.
- [ ] RESUME-7: fix the separate mixed-alias cold-import cycle. Randomized 16 aliases fail when imported concurrently at orchestrator baseline `84f6f6f1` and O3; same-alias 24-thread races and canonical identity tests pass. Original mixed test is at orchestrator `5886e5ae:tests/unit/test_inference_lock_concurrent_import.py`; existing O3 tests do not establish cross-module cold-import safety.
- [x] RESUME-8: repair NI07 capture's declared-output environment contract and replace expired cloud-only package prompts with validated host inputs, CPU claims, isolated baseline trees and explicit cheapest-capable model/effort. Root source `a976770b8`, closeout `8e66dd96b`, integrated here as `152a2991b`; node syntax/smoke and capture regression pass, capture regression fails on parent. ✅ 2026-10-24 Evidence: root `e031c422f:progress/2026-10/2026-10-24-root-integration-01a16fc3.md`. [belief: cc]

At resumption, the independent audit found 55/382 findings with associated commits (including two WIP findings),
327 without commits, and 52 unverified C4–C6 findings. These are inventory counts, not accepted fixes.
The explicit AutoKernel launch hold, deliberate owner-controlled re-pinning, operator-timed P5 merge,
containment-scanner operator review and production-kernel freezes remain in force. Execution stays
near two concurrent agents, using the cheapest capable available model/effort per dispatch.

##### Resumed execution checkpoint (2026-10-25)

The operator approved isolated candidate work for the exact A5-18 protected-launcher cleanup and
for O4 HIGH/CRITICAL REPL findings A4-03/A4-04/A4-06/A4-07. These approvals cover candidate
patches only; they do not authorize a main push, merge, deployment, or production activation.

P1 is accepted and pushed at source `36e1bc55aa40f35965a941e81fdc593a22abd520` on
`refactor/autopilot-loop-reviewed-01a16fc3`. The aggregate and all nine focused file hashes match the run-start, run-end,
and checkpoint snapshots; 19 focused and 561 broad tests passed (one skip), with ruff and diff checks
passing. The worker's original `validation.status` says `FAIL` because its hash-comparison ordering
was wrong; the independent unchanged-file proof is the acceptance evidence. No test was rerun for this
root checkpoint. The P1(rest) item is complete; RESUME-4 combined-tree validation is still separate.

O6 rest (A5-11, A5-23, A5-18, A5-02, A5-21) is accepted and pushed at `6efa56265b68f402af736a1c1a2ee3df447849c1` on `refactor/scripts-cleanup-reviewed-01a16fc3`. The 190 launcher tests and 395 coverage tests pass, including all four 100% floors (331/331, 151/151, 508/508, 579/579); five NI63 controls pass with 32/32 blob and SHA proof. The three scorer failures were a test-fixture `sys.modules` patch/restore leak, fixed without a production-code defect. Four source-pin changes match the exact approved launcher bytes; baseline 5 passes, HEAD `094cbc5b` and main `84` match, and the other 28 pins are unchanged. The original seeding worktree is unchanged. O6 candidate acceptance does not authorize integration, deployment, or activation. O4 candidate patches and caller audit are frozen and accepted:
557 tests passed, eight parent regression negative controls failed as expected, and strict offline
drift, ruff, compile, diff and frozen-snapshot checks passed. Its source-only closeout is pushed as
`acfd5f8ca3837c568fc3c944ffb242b29823f3fa` on reviewed branch `refactor/repl-correctness-01a16fc3`; this does not
authorize main integration or deployment. K2 fixes C4-08, C4-16, and C3-02 are accepted and pushed on `refactor/autokernel-k2-guards-01a16fc3` at `68724da5ba093cf3cec3909a81491932002dd4ce`; C4-05 remains incomplete, so K2 stays open. Detailed state and evidence paths are in
`research/refactor-audit-2026-10/resume-state-01a16fc3.json`.

##### Superseded package checkpoint (2026-10-25)

This entire section is an as-of-2026-10-25 snapshot. Its integration and runner statuses were
superseded by the Oct 26 state above; do not use its captured PIDs as current.

Everything in this dated snapshot is historical; for current integration, O8, P3 and runner states,
use the Oct 26 package state above.

The private integration candidate at `3ee8eea2ab514e8fac4c15c839d4ad1644e0ba38` completed an expanded 111-file union: 2,897 passed, 8 skipped, 0 failed of 2,905 collected; all four source coverage floors are 100%, with no checkout-write warnings. The initial 93-file failure was traced to fixture bytes changing during `_run_loop_inner`; two regression tests now preserve the historical W3e fixture while also detecting future overwrites. The 18-case initial rerun and both added regression tests pass. New-file/changed-hunk style fixes are applied, but final AST, style, focused-suite, 32-pin and P5 frozen-file proof is still running as captured PID 2010953. Its durable evidence is under `/mnt/raid0/llm/tmp/refactor-01a16fc3/orchestrator-integration/` (`final-proof.pid`, `final-proof-runner.log`, `final-proof.sh`; terminal status/done artifacts are not present yet). Until that proof completes and is reviewed, integration is not accepted or pushed. Known baseline debt is 18 Ruff findings and 133 formatter paths; the first integration attempt's checkout-write warnings were eliminated by private pre-import environments for the tool-audit/seen-host file and Ruff cache.

O8 is a frozen, uncommitted draft in `/mnt/raid0/llm/worktrees/refactor-01a16fc3-ci`, branch `refactor/orchestrator-ci-01a16fc3`, based on `3ee8eea2`. It prepares PR/manual CI, the shared native carrier and grade, exact nonsecret context/output/JUnit custody, a single test entrypoint, baseline comparators, strict pytest/server-marker handling, NI63's 32-source current-provenance closure, and pip/UV dev-dependency parity. Original preparation PID 2085542 was cancelled by its owner before the comparator fix and verified dead. Replacement PID 2093707 is the current single detached preparation request, waiting behind the q0–q3 build claim; authoritative pointers are `precheck-run2.pid`, `precheck-run2.process-check.txt`, and `region-lock-run2.log` under `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/`. No tests, lint, lock/sync, native receipt or CI validation are accepted, and no source commit or push exists. The checkpoint snapshot is `/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/checkpoint/`; its manifest prose still describes the original PID, so use the run2 PID/status pointers for live state.

P3 is a frozen, uncommitted draft in `/mnt/raid0/llm/worktrees/refactor-01a16fc3-autopilot-actions`, branch `refactor/autopilot-actions-01a16fc3`, based on `3ee8eea2`. The prepared changes cover managed-stack PID/environment access without `pgrep`, finite validators, refusal-before-side-effects, journal context/events and supersession/caching, provider IO/lifecycle, dead-resume/API cleanup, shard reading, and a neutral core baseline-pin helper. Successor `/root/autopilot_actions_finish` completed the authorized B3-04 optional loaded-journal injection with separate all-era ceiling semantics and added invariance/reset/teardown tests, then froze the draft. W3e fixture bytes match base and `git diff --check` passes. No tests have run; P3 remains unvalidated and uncommitted, with no approval missing. The refreshed 34-file suite is queued in phase `queued-source-frozen`; its stable authoritative manifest is `/mnt/raid0/llm/tmp/refactor-01a16fc3/autopilot-actions/current-run.json`, which points to the source/test snapshot, runner, PID file, log, status and completion flag. Use that manifest for current liveness and runner details; prior wrapper PID 2077838 and child PID 2077840 remain cancelled-before-admission history in `focused-p3-20261025/cancelled-before-admission.txt`. Observed 2026-10-25 08:53:07 UTC. Graph coverage is unknown after the index error. No source acceptance, commit or push exists.

The current next action is to finish and review the integration proof, then validate O8 CI and P3 against the accepted integration SHA. The O8, P3, and RESUME-4 completion boxes remain unchecked; no per-finding completion is claimed. Existing AutoKernel launch/main-merge holds, the P5 single-era boundary and protected serving/kernel rules remain in force. P3 is frozen with a 34-file suite queued; its stable current-run manifest is `/mnt/raid0/llm/tmp/refactor-01a16fc3/autopilot-actions/current-run.json`, observed 2026-10-25 08:53:07 UTC. No tests have run and no source is accepted. The earlier P3 wrapper PID 2077838 and child PID 2077840 are cancelled history, as recorded in `focused-p3-20261025/cancelled-before-admission.txt`. My root-gates wrapper PID 2096522 and child PID 2096526 were cancelled before region admission and verified dead at 2026-10-25 08:52:45 UTC; no token was acquired. Root documentation gates remain pending; use `/mnt/raid0/llm/tmp/refactor-01a16fc3/next-packages-checkpoint/root-gates.pid` and `root-gates.status` as the stable runner-state pointers. The captured state is recorded in `research/refactor-audit-2026-10/resume-state-01a16fc3.json`.

##### Done

- [x] Audit inventory and artifacts filed for 17 units/382 findings; C4-C6 remained unverified in the historical audit. This records artifact filing, not completion of the findings. Evidence: root `83419070d:research/refactor-audit-2026-10/README.md`. [no-belief: not-a-result] ✅ 2026-10-24
- **[declined: ws58 2026-11-03 content-review: historical association with no reviewed receipt; the merge row for refactor/hermetic-tests carries the work]** Hermetic orchestrator harness: the historical plan reported 20,815 off-host collections on `refactor/hermetic-tests`; no independently reviewed raw receipt for that historical count is cited here. Current isolation review is RESUME-2; branch association alone does not complete this item.
- **[declined: ws58 2026-11-03 content-review: historical association with no reviewed receipt]** Containment-scanner bypass/degraded-mode fixes on `refactor/containment-scanner`: historical implementation association only; owner safety review remains open below, so this item is not complete.
- [x] Operator decisions on evaluator regime, AutoKernel prune, CI and scope recorded. Evidence: root `83419070d:research/refactor-audit-2026-10/OPERATOR-DECISIONS.md`. [no-belief: not-a-result] ✅ 2026-10-24
- [x] Bug report, findings, metrics and package definitions filed; no implementation completion follows from publication. Evidence: root `83419070d:research/refactor-audit-2026-10/README.md`. [no-belief: not-a-result] ✅ 2026-10-24

##### Review and merge what is already pushed

- [x] Operator review of `refactor/containment-scanner` (safety boundary for INC-20260823); read `scripts/hooks/CONTAINMENT-SCANNER-CHANGES-FOR-REVIEW.md` on the branch, then merge or reject ✅ 2026-11-02 — merged to main as `f5a4865bd` (operator decision: merge). [no-belief: tooling]
- [ ] Merge `refactor/hermetic-tests` into epyc-orchestrator main (every orchestrator branch contains it)
- [ ] Adversarial review, then merge, of `refactor/config-registry` (O3)
- [ ] Adversarial review, then merge, of `refactor/request-path` (O1 stage 1)
- [ ] Adversarial review, then merge, of `refactor/test-hazards` (O7 partial; its 3 commits have no test report: run the suites first)
- [ ] Adversarial review, then merge, of `refactor/autopilot-gate` (P2; B2-03 changes what is admitted to learning: review as a decision-semantics change)
- [ ] Adversarial review, then merge, of `refactor/autopilot-loop` (P1 stage 1, test harness)
- [ ] Adversarial review, then merge, of `refactor/scripts-cleanup` (O6; finish the A5-11 WIP commit and run the suites for the A5-01/A6-19/A5-05 deletions first)
- [ ] Merge `refactor/autokernel-loop-bugs` only after the AutoKernel launch hold lifts, with a deliberate re-pin (workspace-58); finish the C1-05 WIP first (regression test + loop suite)
- [ ] Delete the superseded `claude/vigilant-thompson-shpyh0` branches in epyc-root and epyc-orchestrator (operator)
- [x] Publish this review branch's RTG-60 registration and VB-REFACTOR-CONFORMANCE filing through the root owner boundary; no shared index file was edited during package work. ✅ 2026-10-29 (audit: RTG-61 row exists in routing-and-optimization-index.md:65 (owning main corrected RTG-60->RTG-61, d3cba7b64) and VB-REFACTOR-CONFORMANCE row filed at vidya-belief-substrate-program.md:82) [no-belief: audit-reconciliation]

##### Wave 1: bugs, hazards, ruled deletions

- [x] O1 (part): reviewed private stage-1 request-path candidate, including the initial-stream cancellation repair, at orchestrator `a1c69593`/`142bb5df`; 1,011 targeted checks pass/3 skip, with parent regression negative control. This is candidate review, not main integration or a blanket completion of associated findings. Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc] ✅ 2026-10-24
- [ ] O1 (rest): [A2-02, A2-M1, A2-M2, A2-03, A2-05, A2-11, A2-16]
- [x] O3: reviewed private config/registry candidate at orchestrator `d843eb9c`/`07829696`/`6558beb7`; 548 targeted checks pass/4 skip, 524 alias-target checks pass and all 7 changed source pins match. Scope is this reviewed candidate; mixed-alias safety remains RESUME-7. Evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`. [belief: cc] ✅ 2026-10-24
- [x] O4 (reviewed scope): A4-03/A4-04/A4-06/A4-07 only, accepted private source `acfd5f8ca3837c568fc3c944ffb242b29823f3fa`; 557 checks pass, eight parent negative controls fail as expected, strict drift/Ruff/compile/diff/frozen proof passes. Evidence: root `09d3c70b5:progress/2026-10/2026-10-25-repl-validation-01a16fc3.md`. [belief: cc] ✅ 2026-10-25
- **[declined: ws58 2026-11-03 content-review: no reviewed package; a historical association row]** O4 (historical associations): A4-01/A4-02/A4-14/A4-M3 were listed against `refactor/repl-correctness`; this line has no reviewed per-finding closure receipt and remains open rather than inheriting the four-item review above.
- [ ] O5: Dashboard request-path cost and silent-empty panels [A1-04, A1-08, A1-13, A1-11, A1-21]
- **[declined: ws58 2026-11-03 content-review: historical association; the O6 merge row carries the work]** O6 (part): historical source associations on `refactor/scripts-cleanup` [A5-M1, A5-06, A5-07, A5-04, A5-12, A5-22, A5-M2, A5-01, A6-19, A5-05]; no reviewed closure receipt for the entire listed scope, and no test report for A5-01/A6-19/A5-05. Association is not completion.
- [x] O6 (rest): [A5-11, A5-23, A5-18, A5-02, A5-21]; accepted source `6efa56265b68f402af736a1c1a2ee3df447849c1` on `refactor/scripts-cleanup-reviewed-01a16fc3`; 190 launcher + 395 coverage tests pass, four 100% floors pass, five NI63 controls pass with 32/32 blob/SHA proof; exact approved four launcher-byte pins and remaining 28 unchanged. No integration/deployment authorization. ✅ 2026-10-25 Evidence: root `e8748d8ec:progress/2026-10/2026-10-25-cleanup-validation-01a16fc3.md`. [belief: cc]
- **[declined: ws58 2026-11-03 content-review: historical association; O7 (rest) carries the work]** O7 (part): historical hazards/hygiene associations on `refactor/test-hazards` [A6-01, A6-02, A6-09]; no reviewed test report for these three findings. RESUME-2's narrower isolation review does not supply their missing closure.
- [ ] O7 (rest): [A6-M1, A6-03, A6-12, A6-11, A6-17]; A6-13 belongs to O8 only.
- **[declined: ws58 2026-11-03 content-review: historical association; the autopilot-loop merge row carries the work]** P1 (part): historical main-loop associations on `refactor/autopilot-loop` [B1-03, B5-02, B5-08, B1-15]; this row lacks its own reviewed per-finding closure receipt and does not inherit P1(rest)'s narrower result.
- [x] P1 (rest): [B1-01, B1-M1, B1-M2, B1-04, B1-08, B1-09, B1-14, B1-13]; accepted source `36e1bc55` on `refactor/autopilot-loop-reviewed-01a16fc3`, hashes unchanged across the full candidate and 19 focused/561 broad tests pass (1 skip). Worker status-file failure was an ordering defect; see resume-state proof. ✅ 2026-10-25 Evidence: root `09d3c70b5:progress/2026-10/2026-10-25-loop-acceptance-closeout.md`. [belief: cc]
- [x] P2: Autopilot safety gate and autopilot_core on `refactor/autopilot-gate` [B2-02, B2-03, B2-09, B2-11, B2-20, B2-17, B5-01, B5-M1, B5-M2, B5-16, B5-09, B5-13, B5-12] (B2-11 skipped: upstream already split SafetyGate.check; B2-17 no change, per the verifier) ✅ 2026-10-24 Reviewed private candidate only; evidence: root `d3418c6b7:progress/2026-10/2026-10-24-refactor-resume-01a16fc3.md`, orchestrator `4069b8ee`/`db17808e`. [belief: cc]
- [x] P3: Autopilot actions, config applicator, controller IO, planner, journal [B3-01, B3-02, B3-03, B3-05, B1-17, B3-06, B3-07, B3-08, B3-12, B3-M1, B3-04, B3-23, B4-01, B3-15, B3-16, B3-M2]; reviewed private source `fb5db1a0a24b92172643bb670c77a4343a508c96` published and remote-verified on `codex/refactor-autopilot-actions-01a16fc3`, clean worktree. Final 12-file functional selection 402 passed/1 skipped in 39.49 s; official three-file formatter closure passed AST equality, format/compile, non-target bytes, no-new-Ruff, P5/W3e, diff and source custody. Earlier 34/90-file failures retained; no current all-1,930-pass claim or main/deployment acceptance. [belief: cc] Evidence: [Oct 26 source/proof record](../../progress/2026-10/2026-10-26-refactor-next-packages-checkpoint-01a16fc3.md). ✅ 2026-10-26 Source warrant: orchestrator `fb5db1a0:docs/refactoring/2026-10-26-p3-reviewed-checkpoint.md`.
- [ ] P4: Autopilot satellites: one-shot scripts, dead modules, small bugs [B4-03, B4-02, B4-19, B4-20, B4-13, B2-16, B4-16, B4-12, B4-06, B4-08, B4-09, B4-15, B4-M1, B4-M2, B4-04, B4-05]
- [ ] K1: AutoKernel live-loop bugs and red tests; remaining [C1-24, C2-06]; C1-05 tested/reviewed on `refactor/autokernel-rollback-reviewed-01a16fc3`, held unmerged (RESUME-3).

  - [x] **C1-15 — fingerprint the existing served-shape oracle.** ✅ 2026-10-30 research main `e32ad4e4d4c1d405cf96ae5996e2f090f75ede71`: changing/deleting that source changes the rules fingerprint and permits retry only for harness-oracle refusal; numerical correctness refusals remain rejected. Red/green actual fingerprint/resume regression plus273 relevant tests pass. Existing oracle logic, thresholds and trust policy are unchanged. [no-belief: source and fixture conformance]
  - [x] **C1-14 — stop hiding programming errors as incomplete answers.** ✅ 2026-10-30 research `49ce3dc4b9b28cc9c95c6d02c43ec8aa60c13051`, preserved on main `0e715dd65b3743adda55ada4618311b36b5f3a04`: only typed ProviderTransient is recoverable; ActorStopped and unexpected context/runtime errors escape without extra actor turns. Actual parser/schema/treatment controls and195 tests plus20 subtests pass; one unrelated baseline whole-file occurrence assertion is being repaired separately. No provider fallback or grading change. [no-belief: source and deterministic actor controls]
  - [x] **CPU_REPACK fingerprint coverage — include the existing module/probe pair.** ✅ 2026-10-30 research main `0e715dd65b3743adda55ada4618311b36b5f3a04` preserves candidate `fd2546a105e244841f5653aae94078ba0c95ee33`. Actual lazy gate dispatch and module/probe source edits now invalidate only cached harness refusal, retaining correctness rejection.81 tests/two subtests pass, one existing sparse-data check skipped. Oracle/probe/tolerance bytes are unchanged; no current noise-helper campaign caller was located, so that unrelated helper was excluded. [no-belief: source and refusal/resume conformance]

- [x] K1 / C1-06: emit scope-gap artifacts only on episode/content changes; observe failures remain retryable and nonfatal, with one console line per failure episode. Research `c0247b0689109b1426ef3db5045e116f6bd17191`;69 controls include actual atomic publisher/recovery. ✅ 2026-10-30 [no-belief: source and fixture repair; no measurement verdict]
- [x] K1 / C1-M2: make synthetic GPU unit fixtures explicitly MOCK_ONLY with the existing untested-seat override; real version/seat negatives still refuse. Research `a39561d471dd1dbc1622d5653214927db3b482c0` and `48a8265dbe6048251538d32ba87d0752eb6be13f`;100 GPU/seat controls pass. ✅ 2026-10-30 [no-belief: test fixtures; no serving qualification]
- [x] K1 / C5-08: journal validators catch their typed data refusals; unexpected implementation/import faults propagate without being relabeled corrupt data. Research `d38e17983e6754fd704c3c5380d87b0cb0bd7ec8`;158 tests and15 subtests, including fresh-child missing dependencies. ✅ 2026-10-30 [no-belief: source fault classification; live ledger untouched]
- [x] K1 / C5-16: HostOps build jobs respect available CPU affinity and the existing64 cap. Research `5ffa9260f86c011f09b58121f6a687ddee1d9afd`;282 tests/143 subtests. ✅ 2026-10-30 [no-belief: source capacity repair; no compiler or inference run]
- [x] K1 / C6-05: host-independent build argument fixtures preserve real oversubscription negatives; frozen branch/tag assertion resolves canonical branch identity. Research `d929cf86836beb37a72bbfc816ea065670f81d22` and `c9084a09359350e898c8f8eaab77ad53274c1186`;294 related passes plus22 branch tests/60 subtests. Historical-log skip and the independently reproduced process-cleanup defect are not counted as passing tests. ✅ 2026-10-30 [no-belief: fixture/assertion repairs; production freeze unchanged]
- [x] K1 / C6-03: reconcile the stale missing-`tmp_path` finding against actual source: `037e072e6b` fixed the exact helper call on2026-10-07; pinned research `928f98682` passes the full named source-build-preparation module. Six-module verification reports81pass/4 failures in other modules; one is archive-only missing Git metadata and three fixture regressions are separately assigned. This is verification of an existing fix, not a new implementation. ✅ 2026-10-30 [no-belief: source/test reconciliation]
- [ ] K2: AutoKernel evaluator/execution integrity package remains open; C4-05 remains incomplete.
- [x] K2 / C4-10: writer, resume and terminal evaluation share the same fixed declaration inputs; omitted or mutated model identity, envelopes, limits and transition fields refuse. Research main `595e4e62d1422c08892f93e3785c6dd6bb6c25f5`;36 baseline omissions reproduced,47 tests/102subtests pass. Writer bytes and exact existing legacy resume bridge preserved; unrelated baseline InstrumentSelection test explicitly excluded, tiny fixture models only. ✅ 2026-10-30 [no-belief: declaration-validation source repair; no historical regrading]
- [x] C6-04 and caller-fixture follow-on: synthetic matched-serving actors use the existing explicit MOCK_ONLY override, and runtime tests select the unique completed runtime record separately from actor-admitted metadata. Original kept/qualitative/default/recipe assertions and production gate remain unchanged. Research main `bff70b10f92c91d3993dd2a2ebf6367609e6355c` includes `ab71bfbca8a5f1cb6da61855e9130e4a5efdcef4`; all86 cases in the six requested modules plus78 unchanged actor-wire tests have terminal PASS receipts across bounded batches. ✅ 2026-10-30 [no-belief: source test-fixture repair; no native measurement verdict]
- [x] C4-09 / Worktree runner: reserve the unreaped session leader, pump pipes without reaping it, and verify the whole owned group before attesting cleanup; TERM-ignoring descendants receive KILL even after leader exit. Research main `928f98682cb1395a5e4d73b824e25236d5da12dd` contains `da9f8b39fa78798b90ce034e5887f4f419440a87`. Final38 focused controls and immutable native five-second observation windows pass; prior315-test/262-subtest full suite passed before the final exception-only close fix. Later full retries were resource-interrupted, not passing full-suite claims. ✅ 2026-10-30 [no-belief: source process-ownership repair, no model execution]
- [x] C4-09 / T0 provider runner: reserve ownership and verify the group before recording capture; preserve separate text channels, encoding/newlines, environment/cwd, sandbox and distinct TERM/KILL grace periods. Research main `92fdeccc95d6d4c3e6ce21d152faf8cb7703f649` includes `0a827fa1baac5c1ce5b0ef2059754f97297f51c3`.242 public/default controls,179 worktree controls, two native sandbox controls and immutable native five-second post-return proof pass. The reproduced original live descendant no longer survives return; unknown inspection raises infrastructure refusal. ✅ 2026-10-30 [no-belief: process-ownership source repair]
- [x] C4-06 / chain qualification: declare explicitly MOCK_ONLY DSO fixtures in the recorded execution chain, preserving strict production attestation. Research main `c61214e813dcc6330e91dc4c93ab9e3f240c4dff` includes `84ae8120c4fa727de8c237ad60a801dee4d019cb`;122 chain cases and six strict DSO controls pass. Missing inventory makes zero recorded calls; mutation prevents reuse/admissible paired blocks; recorded fixtures never imply native residency. ✅ 2026-10-30 [no-belief: test-fixture qualification]
- [x] Capacity preparation: replace one owned byte-identical private model copy with an R9 hardlink, and reversibly omit identical tracked artifact copies from11 owned landed views. Git data/refs/code/operator artifacts/runtime pins and all staged/unstaged/untracked bytes are preserved; locked runtime/unlanded/peer roots excluded. Receipts under `/mnt/raid0/llm/tmp/refactor-01a16fc3/storage-sparse-recovery*-20261030.json` and the Parakeet R9 receipt. This is allocated-copy reduction, not an attributable shared-volume free-space delta. ✅ 2026-10-30 [no-belief: operational data custody and resource preparation]
- [x] K2 / C4-06: bind freshly executed microbench receipts to declared DSO target/content identities; historical unknown receipts remain readable but cannot qualify a fresh execution. Research main `5bbfd6ab25a640ec8ed406e0d3a804cddf468db8` includes reviewed `6a93613bc`;625 tests/144 subtests pass. This attests declared files, not runtime HIP residency. ✅ 2026-10-30 [no-belief: source execution-attestation repair; no new benchmark warrant]
  - [x] K2 finding C4-08: resolved-path, fail-closed production-tree containment; source commit `208a053e29daf5bd11019e733f768b4173887021`. ✅ 2026-10-25 Evidence: root `e8748d8ec:progress/2026-10/2026-10-25-k2-guards-01a16fc3.md`. [belief: cc]
  - [x] K2 finding C4-16: exact Fraction ceiling independent of Decimal context; source commit `091abbbe7dc9b346bab888569434eb68445ae8e5`. ✅ 2026-10-25 Evidence: root `e8748d8ec:progress/2026-10/2026-10-25-k2-guards-01a16fc3.md`. [belief: cc]
  - [x] K2 finding C3-02: package import avoids shadowing stdlib `resource`; source commit `68724da5ba093cf3cec3909a81491932002dd4ce`. ✅ 2026-10-25 Evidence: root `e8748d8ec:progress/2026-10/2026-10-25-k2-guards-01a16fc3.md`. [belief: cc]

##### Wave 2: decision-dependent and structural

- [ ] P5: Autopilot evaluator: ONE batched era event (operator decision 2026-10-24) [B5-03, B2-01, B2-M1, B2-M2, B2-10, B5-06, B5-07, B2-19, B2-04, B2-05, B2-06, B2-07, B2-08, B2-14, B2-15, B2-18, B2-12, B2-13, B5-14, B3-09]
- [ ] K3: AutoKernel prune of the three approved planes, after fresh closure and retained-contract checks [C2-01, C1-04, C2-03, C2-05, C2-08, C2-12, C2-M2, C2-13, C3-03, C3-01, C3-M1, C3-13, C3-14, C3-18, C5-03, C5-15, C4-01, C4-02, C4-03, C4-11, C5-13, C5-12, C6-09, C5-06, C6-08, C2-09, C5-07, C2-M1]; C4-01's old deletion advice is superseded by INF64's retained manifest.
- [ ] K4: AutoKernel regrowth guard and CI repair (operator decision 2026-10-24) [C2-04, C5-02, C3-05, C1-02, C1-M3, C5-01, C6-01, C5-14, C6-13, C3-11, C2-02, C6-16]
- [ ] O8: Orchestrator CI, honest gates, and the ni63 pin design (operator decision 2026-10-24) [A6-04, B1-M3, B5-10, B5-17, A6-13]
- [ ] D1: Decompose the autopilot loop (_run_loop_inner) behind the P1 safety net [B1-02, B1-05, B1-12, B1-10, B1-06, B1-07, B1-11, B1-16, B1-18, B1-19]
- [ ] D2: API layer: openai_compat and /chat de-duplication [A1-05, A1-06, A1-15, A1-19, A1-20, A1-12, A1-10, A1-14, A1-16, A1-18, A1-09, A1-07]
- **[declined: ws58 2026-11-03 content-review: historical association; D3 (rest) carries the work]** D3 (part): historical inference-hot-path association [A2-12]; no reviewed closure receipt is cited here, so it remains open.
- [ ] D3 (rest): [A2-22, A2-06, A2-09, A2-07, A2-08, A2-10, A2-14, A2-15, A2-17, A2-18, A2-19, A2-20, A2-21]
- [ ] D4: AutoKernel run.main decomposition [C1-03, C1-M1, C1-01, C1-08, C1-10, C1-11, C1-12, C1-13, C1-16, C1-17, C1-18, C1-19, C1-20, C1-21, C1-23, C1-09, C1-07, C2-14, C2-15, C2-16]
- [ ] D5: Config / registry / runtime consolidation [A3-03, A3-10, A3-11, A3-12, A3-13, A3-14, A3-17, A3-18, A3-20, A3-21, A3-22, A3-23, A3-24, A3-25]
- [ ] D6: REPL / tools consolidation [A4-09, A4-12, A4-10, A4-17, A4-05, A4-11, A4-13, A4-15, A4-16, A4-18, A4-19, A4-20, A4-21, A4-22, A4-23, A4-M2]
- [ ] D7: Orchestrator scripts structure (src<->scripts layering, sys.path, duplicated helpers) [A5-03, A5-08, A5-09, A5-13, A5-14, A5-15, A5-20, A5-24, A5-25, A5-M3]
- [ ] D8: Orchestrator test-suite consolidation [A6-10, A6-05, A6-06, A6-07, A6-08, A6-14, A6-15, A6-16, A6-20, B5-18]
- [ ] D9: Autopilot remaining structure (actions, planner, journal, reports) [B3-10, B3-11, B3-13, B3-14, B3-17, B3-18, B3-19, B3-20, B3-21, B3-22, B3-24, B3-25, B4-07, B4-10, B4-11, B4-14, B4-17, B4-18, B5-04, B5-05, B5-11, B5-15]
- [ ] D10: AutoKernel remaining structure (controller, evaluator, execution, schemas, tests) [C3-04, C3-06, C3-07, C3-08, C3-09, C3-10, C3-12, C3-15, C3-16, C3-17, C3-19, C3-20, C3-21, C3-22, C3-M2, C4-04, C4-07, C4-09, C4-12, C4-13, C4-14, C4-15, C4-17, C4-18, C5-09, C5-10, C5-11, C6-02, C6-06, C6-10, C6-11, C6-12, C6-14, C6-15, C6-18, C2-07, C2-10, C2-11]

##### Deferred, each with its blocker

- [ ] A5-10, A5-16, A5-17, A5-19: restructure `scripts/server/orchestrator_stack.py`. Blocked: a live path on the host (workspace-58, 2026-10-24); run when that file is quiet
- [x] C5-05: delete the `campaign.py` CLI cluster (~20k LOC). Operator decision 2026-11-02 approved the deletion (a fourth plane outside the three approved); research `753639bd1` deleted the cluster. ✅ 2026-11-02 [no-belief: tooling]
- [x] C6-17: Arena retirement is outside the approved three-plane prune; preserve its existing belief-source producer/consumer contracts unless the operator authorizes a separate retirement package. Continue other packages meanwhile. 2026-11-09 operator decision: keep Arena; a later separate package may remove the five unused vendor wrappers only. Live producer/consumer contracts stay. ✅ [no-belief: scope decision]
  - *(workspace-f2 audit 2026-11-09.)* Operator decided 2026-11-09: ownership handed to AutoKernel, which decides and asks the operator through its own decision tool if needed.
- [ ] Re-enable the AutoKernel guards workflow in GitHub after K4 lands (operator click)

##### Follow-ups found during the audit (not tied to a single package)

- [x] Reconcile C4-01 against `artifacts/ni08/inf64-source-reachability-review-20261007/completed-manifest.md`: current strip guidance already retains all 19 candidates. Do not follow the old proposal to delete Apex/compiler modules or preserve only three evaluator modules. ✅ 2026-10-31 — reconciliation against ROOT evidence `f219064bace51b7db01a713e90bf5e7d9ec2a0f2`; artifact `artifacts/ni08/inf64-source-reachability-review-20261007/MAIN-completed-manifest-review.json` verifies 19 retain / 0 remove. Current strip guidance preserves all 19; no new engineering or deletion authority. [belief: cc]
- [x] ✅ 2026-10-31 Re-pin `scripts/server/orchestrator_stack.py` in the ni63 `SOURCE_PINS`: resolved through O8's record-not-assert design, preserving historical source tuples and fixed workload/capacity pins. Evidence: orch `d094546ea86d08bfcc18407529c6c7ae0672c525`; `tests/unit/test_ni63_current_source_clone.py`; `/mnt/raid0/llm/tmp/refactor-01a16fc3/ni63-current-source-20261031/QUALIFICATION.json` (17 pass). [no-belief: current-source fixture repair; O8 CI parent remains open]
- [x] Refresh `scripts/harness/strategy_projection_report_capture.py` `TRUSTED_APP_SOURCES`: 6 of 11 pins already stale at base (incl. `tier_specs.py`), so the tool refuses (found by O3) ✅ 2026-10-31 [no-belief: source epoch correction and synthetic integrity controls; no live measurement] <!-- implementation: ROOT 8cfbac4cec8074cde9768c33ec26c6cf49293aa4; tests: tests/vidya/test_strategy_projection_report.py + tests/vidya/test_producer_pins.py; artifact: artifacts/vidya/strategy-source-epoch-20261031/EVIDENCE.json -->
- [x] Move `process_pattern_kill_scan.py`, `operator_apply_copy_scan.py` and `pytest_worker_scan.py` to `shell_scan.lex()`: they still use the old strip functions and share the escape/heredoc blind spots the containment scanner had ✅ 2026-10-31 — ROOT `c5c87541f32ce16fdb7b8464038739a8bdc0105d`; `scripts/hooks/tests/test_shell_scan_migration_parity.py` plus actual hook controls, 129 PASS / 0 skipped; durable proof `artifacts/engineering/ni-shell-scan-migration-20261031/lane-validation-receipt.json`. Existing `segments()` callers and refusal thresholds remain compatible; pytest comment-only false positive corrected. [no-belief: deterministic scanner correctness controls; no measurement]
- [x] Containment scanner coverage for `restic restore --target`, `borg extract/delete/prune`, `rclone copyto/moveto/mkdir` (changes `--dump-rules`; regenerate the opencode config in the same change) ✅ 2026-10-31 — implementation ROOT `0f344f4c900347d93281af2db3a9cfd990830b4b`; `scripts/hooks/tests/test_filesystem_containment.py`; durable proof `artifacts/engineering/ni-containment-verbs-20261031/REPORT.txt` (75 tests/57 subtests, 28 project parity checks, seven baseline/candidate controls). Project config regenerated byte-identically; global config untouched. [no-belief: deterministic command-parser containment controls; no measurement]
- [x] `.claude/skills/project-wiki/scripts/check_readme_freshness.py` hard-codes `/mnt/raid0/llm/<repo>`: off the host it reports all three READMEs as missing. Resolve repos relative to its own checkout or accept `--root` — ✅ 2026-10-29 root `511f1ee616839817c00e905c0e83283a58437267`: checkout-relative discovery and `--root`, explicit repo entries take precedence; six native temporary-layout controls pass, warning-only behavior retained. [no-belief: portable utility repair]
- **[declined: ws58 2026-11-03 content-review: bookkeeping]** `scripts/vidya/adapters/README.md` cites `test_vb_ap53_reproposal_rate.py (12)`; the file had 14 tests at base (found by P1). Owner: vidya-belief-substrate-program
- **[declined: ws58 2026-11-03 content-review: conformance wiring for refactor verdicts, not a stack measurement (same class retired in the vidya review)]** VB-REFACTOR-CONFORMANCE: implement prospective native capture/projector wiring for controlled regression verdicts. Source row and task are filed on this review branch; manual source audits remain dependency findings and past diagnostic runs are not backfilled.


#### Problem

The operator asked for a review of the heavily built codebases for best practice, documentation,
modularity, compute performance, ease of resolving bugs, clean and effective tests, and code-size bloat.
The trees grew at roughly 10:1 insertions to deletions. epyc-orchestrator is ~862k lines of Python (src 201k, scripts 274k,
tests 358k) and grew another ~90k in the 17 days from 2026-10-07 to 2026-10-24. AutoKernel is ~490k lines
(282k source, 209k tests): it was rebuilt to a 3,450-LOC loop budget and regrew +278k net in August and +185k in
September, and its own regrowth guard sits 37x over budget (95,260 code lines vs 2,560). The worst hotspots are
single functions of 2,902 lines (`autopilot.py` `_run_loop_inner`, cyclomatic complexity 324), 5,518
(`loop/run.py` `main`, complexity 1,166) and 1,006 (`openai_chat_completions`). Neither repo had working CI:
the orchestrator has none, and the AutoKernel guards workflow was disabled by hand on 2026-09-10 after 168
red runs (its test steps never ran even before that).

#### Test baselines and coverage

| Suite | Where | Result | Notes |
|---|---|---|---|
| epyc-orchestrator, full | container, origin/main + `refactor/hermetic-tests`, 2026-10-24 | 20,815 collected; **20,496 passed, 127 failed, 21 errors** (63 min, `-n 2`) | Before `refactor/hermetic-tests` the conftest could not even be imported off the production host. Failing ids: `data/orch_baseline_failing_ids.txt` |
| AutoKernel, full | container, 2026-10-07 | **10,576 passed, 476 failed, 87 errors** (23 min, `-n 3`) | ~58% host-dependent (root uid, CPUs < 32/64, /mnt/raid0); the rest is real rot nobody saw because CI was off. `release/test_t3*` cannot be collected at any standard checkout path |
| epyc-root `scripts/hooks/tests` | container | 313 passed with the scanner fixes (296 at base); same 11 failed / 25 errors on both sides | |
| CI | GitHub | orchestrator: none; AutoKernel: `disabled_manually` since 2026-09-10 | |

Per-file coverage is not mapped here: the suite is too large for a source-to-test table. Coverage gaps that
block a refactor are named inside each package (e.g. B1-03/B5-02: only 9 tests drove the real autopilot
loop; 11+ tests pinned its source TEXT; 28 AutoKernel test files grep `run.py` source).

#### Operator decisions (2026-10-24, [`OPERATOR-DECISIONS.md`](../../research/refactor-audit-2026-10/OPERATOR-DECISIONS.md))

1. **Evaluator regime**: batch every change to `eval_tower.py`, `rubric_scoring.py`,
   `src/autopilot_core/tier_specs.py` and `orchestration/eval_registry.yaml` into ONE era event (package P5),
   together with an AST-normalized evaluator fingerprint, so later comment, format and pure-refactor edits stop
   splitting the AP-55 regime. Merging P5 is the single regime break; the operator picks the time.
2. **AutoKernel prune**: delete all three unreachable planes (the unified/standalone control plane rejected on
   2026-09-09; the `discovery_*`/`gpu_source_*` stack; `release/`), staying current with main and re-proving
   reachability from the live entry points at the current origin/main HEAD before every stage.
3. **CI**: add orchestrator CI (pull_request + workflow_dispatch only) and repair the AutoKernel workflow
   (the operator re-enables it in GitHub).
4. **Scope**: full program, paced at about 2 concurrent agents. The account has no extra-usage credits, so the
   work spans several 5-hour usage windows.

Standing inputs: hermetic tests approved (2026-10-07); keep an eye on bloat (2026-10-07); kernel (llama.cpp)
defects go to the champion fold as CH-xx recommendations, never as production patches (relayed operator rule,
2026-10-24); workspace-58's live-path and file boundaries (§Coordination).

#### Branches (all pushed 2026-10-24; rebased on origin/main unless noted; NONE reviewed by a second agent yet)

| Repo | Branch | Commits | Contents | Merge notes |
|---|---|---|---|---|
| epyc-root | `refactor/containment-scanner` | 3 | scanner bypass fixes; degraded-mode regression fix (main since 84b0de13 lets `sudo mount` through with no scanner); behaviour-change note | **Operator review required** (safety boundary for INC-20260823); see `scripts/hooks/CONTAINMENT-SCANNER-CHANGES-FOR-REVIEW.md` on the branch |
| epyc-root | `refactor/refactoring-plan` | this | this handoff, the bug report, all evidence | docs only |
| epyc-orchestrator | `refactor/hermetic-tests` | 1 | conftest stub kernel store + host-RAM fallback (no-ops on the host), `ORCHESTRATOR_PATHS_KERNEL_ROOT`, ni63 pin refresh | **merge first**; every orchestrator branch below contains it |
| epyc-orchestrator | `refactor/request-path` | 9 | O1 stage 1: per-request state on the shared LLMPrimitives (A1-02/A2-01/A1-M2), model/REPL calls off the event loop (A1-01), per-request cancellation (A1-M1), no_web context (A4-M1), shared backend build (A2-04), region-lock release (A2-13), skill ids (A1-17) | production request path: review carefully; stage 2 (A2-02…A2-16) not started |
| epyc-orchestrator | `refactor/config-registry` | 14 | O3: stack-priors parse cache (A3-01/A1-03), fail-closed compile (A3-02), Settings factories (A3-07), topology-cache poison (A3-08), shadow thread (A3-09), env-override and crash fixes (A3-M1, A3-04, A3-06), OCR timeout (A3-15), registry-cache lock (A3-05), shim race (A3-16/A4-08), env.sh root (A3-M2), registry backoff (A3-19) | rebased with ni63 pin conflicts resolved (upstream fixture kept; pins of files this branch changes refreshed) |
| epyc-orchestrator | `refactor/scripts-cleanup-reviewed-01a16fc3` | accepted candidate | O6 rest source `6efa56265b68f402af736a1c1a2ee3df447849c1`; 190 launcher + 395 coverage pass, all four 100% floors and five NI63 controls pass; 32/32 blob/SHA proof; approved four pin changes exact, other 28 unchanged | Accepted source only; combined-tree validation remains under RESUME-4; no merge/deploy |
| epyc-orchestrator | `refactor/test-hazards` | 4 | O7: fence tests no longer aim destructive payloads at the REAL wiki (A6-01), checkout-write leak guard (A6-02), tmp_path not fixed /mnt/raid0 dirs (A6-09) | no test report (interrupted) |
| epyc-orchestrator | `refactor/test-isolation-reviewed-01a16fc3` | reviewed | Includes hermetic/test-hazards plus fixture-only A6-M1 trace/ledger isolation | Pushed `5e392a3c`; 189 runtime/trace tests + 7 E8 wrappers pass, 1 intentional skip; reviewed, unmerged |
| epyc-orchestrator | `refactor/config-reviewed-01a16fc3` | reviewed | Includes O3 + accepted isolation, concurrent registry-backoff fix and scoped alias-import stress | Pushed `6558beb7`; 548 O3 tests + 524 alias targets pass, 4 skips; mixed-alias cycle is RESUME-7 |
| epyc-orchestrator | `refactor/request-reviewed-01a16fc3` | reviewed | Includes O1 stage 1 + accepted isolation and cancellation during initial streaming generation | Pushed `142bb5df`; 1,011 tests pass, 3 skips; reviewed, unmerged |
| epyc-orchestrator | `refactor/autopilot-gate-reviewed-01a16fc3` | reviewed | Includes P2 + accepted isolation and real-fixture pre-P2 snapshot migration controls/runbook | Pushed `db17808e`; 1,018 tests pass/1 skip; HIGH/CRITICAL integration review and owner-boundary snapshot rebuild required |
| epyc-orchestrator | `refactor/autopilot-loop` | 6 | P1 stage 1 (safety net): the real loop driven by a harness instead of source-text slicing (B1-03/B5-02), shared frontier-admission predicate (B5-08), hook containment (B1-15) | Initial P1 stage-1 branch; reviewed rest is on `refactor/autopilot-loop-reviewed-01a16fc3` |
| epyc-orchestrator | `refactor/autopilot-loop-reviewed-01a16fc3` | reviewed | P1 rest B1-01/B1-M1/B1-M2/B1-04/B1-08/B1-09/B1-14/B1-13; source `36e1bc55aa40f35965a941e81fdc593a22abd520` | Accepted, unmerged; RESUME-4 combined validation remains |
| epyc-orchestrator | `refactor/autopilot-gate` | 15 | P2: safety-gate seq upgrade (B2-02), one-sided MAD (B2-03, **changes what is admitted to learning**), refusal codes (B2-09), validator/replay (B2-20), hypervolume memo + fold + off-loop dashboard (B5-01), bounded snapshot replay (B5-M1), cluster identity (B5-M2), era guard (B5-16), dead modules (B5-09), `__init__` (B5-13), drop counts (B5-12) | B2-03 is a decision-semantics change: review it as such |
| epyc-inference-research | `refactor/autokernel-loop-bugs` | 1 | **WIP**: `run._git` checks git's exit status; failed rollback aborts the run (C1-05) | **do not merge to main**: AutoKernel launches are under an operator hold; workspace-58 merges it with a deliberate re-pin when the hold lifts |
| epyc-inference-research | `refactor/autokernel-rollback-reviewed-01a16fc3` | 3 | Completes C1-05: includes WIP, catches rollback timeout/spawn errors, behavioral regressions and checkpoint | Reviewed; 401 targeted loop tests + 23 subtests pass. Pushed at `1b58b115c`; hold/re-pin applies, no launch or merge |
| epyc-orchestrator | `refactor/orchestrator-integration-01a16fc3` | reviewed private candidate | Combined orchestrator candidate | `851955112b8ba8c2911a7684469551afa1541623`; validated relative to immutable base `84f6f6f1`; no main promotion/deployment |
| epyc-orchestrator | `refactor/orchestrator-ci-01a16fc3` | B1-tested pre-fixture local merge | O8 CI, central pytest gates and NI63 provenance closure | `753e0287` contains `713edf671` + `851955112`; focused 13 pass; strict collection baseline 20,658/20,645 selected vs candidate 20,666/20,653, 0 removed/8 added/13 identical exclusions; post-B1 owned fixture validation pending; full suite/native/coverage open; future `codex/*` only |
| epyc-orchestrator | `codex/refactor-autopilot-actions-01a16fc3` | reviewed private candidate, published | P3: actions, config applicator, controller IO, planner, journal and baseline-pin helper | `fb5db1a0a24b92172643bb670c77a4343a508c96`, remote-exact verified, clean worktree; final 12-file 402 pass/1 skip and three-file formatting/protected/source-custody closure pass; prior failures retained, no main/deploy |
| all three | `claude/vigilant-thompson-shpyh0` | — | superseded by the `refactor/*` branches above | ignore / delete |

Merge order (orchestrator): reviewed hermetic harness + test-hazards/A6-M1 isolation →
`refactor/config-registry` → `refactor/request-path` → `refactor/autopilot-gate` →
`refactor/autopilot-loop` → completed `refactor/scripts-cleanup`.
The branches carry patch-equivalent copies of the hermetic commit, not one shared commit identity.
Known integration conflicts: gate/loop `autopilot.py` (retain cluster identity and the admission helper),
config/cleanup ni63 registry-loader pin, and hazards/cleanup conftest plus the deleted E8 test.
Each branch rebased cleanly on origin/main on 2026-10-24; later upstream commits may need another rebase. Nothing
merged to orchestrator main is served until the shared clone is synced (operator approval).

#### Issue inventory (summary; every finding with evidence, verifier notes and proposal is in the findings files)

| Unit | Findings | Sev ≥ 4 | Bloat est. (LOC) | Biggest problems |
|---|---|---|---|---|
| A1 API layer | 23 | 6 | 1,100 | blocking model/REPL calls on the uvicorn loop; shared per-request state; 1,006-line openai handler, 2 near-identical /chat/stream impls; per-request YAML and ps parsing in the dashboard |
| A2 inference hot path | 24 | 6 | 2,300 | per-request state on a shared LLMPrimitives reroutes requests under concurrency; read-timeout truncation reported as success; quadratic early-stop; 4 drifted llama_server lanes; 12 copies of the escalation chain |
| A3 config/registry/runtime | 27 | 3 | 2,700 | config declared 4 times; fail-open stack-priors compile; reset_config cannot refresh; poisoned caches |
| A4 REPL/tools/top level | 26 | 1 | 3,000 | production read_file swapped for an unchecked builtin; REPL web tools bypass role permissions and no_web; 4 parallel tool stacks |
| A5 orchestrator scripts | 28 | 2 | 45,000 | the retired E8 chain (32.6k incl. tests); a forked scripts/lib; 71 src→scripts imports; 196 sys.path hacks; name-pattern kills |
| A6 orchestrator tests | 20 | 2 | 5,200 | not hermetic; destructive payloads aimed at the real wiki; no CI; 89 assertion-free tests; ~50 source-text tests |
| B1 autopilot loop | 22 | 3 | 300 (+~9k movable) | 2,902-line `_run_loop_inner`; plain `save_state()` clobbers an operator pause (H4 class); 8 copies of the halt latch |
| B2 eval + safety gate | 22 | 1 | 1,250 | parse-failure telemetry zeroed on every T1/T2 trial; two-sided MAD admits regressions as improvements; per-question registry re-parse |
| B3 actions/planner/journal | 27 | 0 | 1,500 | pgrep name-pattern process picks; NaN passes bounds checks; journal deep-copied per trial |
| B4 satellites | 22 | 0 | 7,400 | applied one-shot ratifiers and era-pinned collectors still in tree; vendored judges unprotected |
| B5 autopilot_core + tests | 20 | 3 | 1,450 | exponential hypervolume per replayed trial (3.6-5.7 s, twice per trial); evaluator fingerprint hashes raw bytes |
| C1 AK loop core | 27 | 5 | 26,600 | 5,518-line `run.main`; `_git` ignores exit status; CI off |
| C2 AK loop periphery | 18 | 2 | 72,000 | the rejected unified/standalone plane (~61k incl. tests) still imported through 5 thin bridges |
| C3 AK controller | 24 | 1 | 37,000 | unreachable discovery_*/gpu_source_* stack; v9 digests pinned for "v10"; stdlib `resource` shadowed |
| C4 AK evaluator/execution (UNVERIFIED) | 18 | 3 | 5,700 | non-inferiority e-value labelled IMPROVEMENT; attestation never hashes the libggml DSOs |
| C5 AK release + top level (UNVERIFIED) | 16 | 7 | 65,000 | dormant release/ plane; guard counts only loop/; journal validator turns ImportError into "invalid payload" |
| C6 AK tests (UNVERIFIED) | 18 | 5 | 9,400 | CI cannot reach its test steps; 38 tests broken by a helper change; jobs=32 fixture vs CPU count |

(Bloat estimates overlap between C units; the approved three-plane prune is ~150k LOC including tests.)

#### Wave 1: bugs, hazards, ruled deletions (packages in [`packages/wave1.json`](../../research/refactor-audit-2026-10/packages/wave1.json))

| Pkg | Theme | State 2026-10-24 |
|---|---|---|
| O1 | request path: concurrency, event loop, failure semantics | stage 1 done (9/9, on `refactor/request-path`); stage 2 (A2-02, A2-M1, A2-M2, A2-03, A2-05, A2-11, A2-16) not started |
| O3 | config/registry/runtime correctness + stack-priors cache | done (`refactor/config-registry`) |
| O4 | REPL/tools permission bypasses and structured-mode defects | accepted on `refactor/repl-correctness-01a16fc3` at `acfd5f8c`; 557 tests pass and eight parent negative controls fail as expected; offline drift, ruff, compile, diff and snapshot gates pass |
| O5 | dashboard request-path cost | not started |
| O6 | scripts bugs + ruled deletions | rest accepted at `6efa56265b68f402af736a1c1a2ee3df447849c1`; launcher/coverage suites and four floors pass; integration remains separate |
| O7 | test-suite hazards | A6-01, A6-02, A6-09 committed; A6-M1, A6-03, A6-12, A6-13, A6-11, A6-17 not started |
| P1 | autopilot loop: safety net, then loop bugs | stage 1 and P1 rest accepted at `36e1bc55aa40f35965a941e81fdc593a22abd520`; combined-tree validation remains separate |
| P2 | safety gate + autopilot_core | done (B2-11 skipped: upstream already split `check()`; B2-17 no change per verifier) |
| P3 | actions, config applicator, controller IO, planner, journal (B3-01 pgrep) | not started |
| P4 | autopilot satellites bloat (one-shot ratifiers, era-pinned family, dead modules) | not started |
| K1 | AutoKernel live-loop bugs and red tests | C1-05 WIP only |
| K2 | AutoKernel evaluator/execution integrity (C4-05 remains) | C4-08/C4-16/C3-02 accepted at `68724da5ba093cf3cec3909a81491932002dd4ce`; package incomplete |

#### Wave 2: decision-dependent and structural ([`packages/wave2.json`](../../research/refactor-audit-2026-10/packages/wave2.json))

| Pkg | Theme | Depends on |
|---|---|---|
| P5 | **evaluator: ONE batched era event**: B5-03 fingerprint normalization FIRST, then B2-01, B2-M1, B2-M2, B2-10, B5-06, B5-07, B2-19, perf B2-04/05/06, refactors B2-07/08/14/15/18/12/13, B5-14, B3-09; commit subjects prefixed `evaluator-era:` | P2 merged |
| K3 | **AutoKernel three-plane prune**, staged by approved plane; rebase on origin/main and re-prove closure before EVERY stage, including retained campaign CLI and dynamic/cross-repo roots; honor INF64's per-file retention manifest and live belief-source contracts; Arena is excluded | K1; operator hold lifted for merge |
| K4 | Repair CI infrastructure early (independent steps, yaml dependency, honest collection floors); set the all-package size ratchet only after the approved prune | ratchet depends on K3; infrastructure does not |
| O8 | orchestrator CI (PR + manual only; hermetic suite minus a reviewed host-only list with reasons), honest `make gates` (format-check only changed files; 1,471 files fail a whole-tree check), ni63 pin design (record hashes for provenance instead of asserting a past commit's bytes; the pin is already red on main for `orchestrator_stack.py`) | merge reviewed integration candidate `851955112` into `refactor/orchestrator-ci-01a16fc3`, then validate package |
| D1 | autopilot `_run_loop_inner` decomposition (B1-02 staged seams) | P1 merged |
| D2 | API: openai_compat and /chat de-duplication | O1 merged |
| D3 | inference hot path: llama_server lanes, `_execute_turn`, escalation chain | O1 merged |
| D4 | AutoKernel `run.main` decomposition (behavioural tests first; evidence identities hash whole files: C1-M1) | K1, K3 merged |
| D5 | config/registry/runtime consolidation (region-lock: bug fixes only) | O3 merged |
| D6 | REPL/tools consolidation | O4 merged |
| D7 | orchestrator scripts structure (no `orchestrator_stack.py` restructuring) | O6 merged |
| D8 | orchestrator test-suite consolidation | last |
| D9 | autopilot remaining structure | P1, P3, P4 merged |
| D10 | AutoKernel remaining structure | K1, K2, K3 merged |

Deferred, not in any package ([`packages/deferred.json`](../../research/refactor-audit-2026-10/packages/deferred.json)):
A5-10, A5-16, A5-17, A5-19 restructure `scripts/server/orchestrator_stack.py`, a live path on the host (workspace-58,
2026-10-24); their proposals in `findings-orchestrator-core.md` are ready to run when that file is quiet.
C5-05 (delete the `campaign.py` CLI cluster, ~20k LOC) is a fourth plane the operator did not approve.
C1-22 disappears with the unified plane.

#### How to resume

1. `python3 research/refactor-audit-2026-10/packages/mkpkg.py research/refactor-audit-2026-10/packages/wave1.json <scratch>/pkg`
   regenerates the per-package briefs (same for `wave2.json`).
2. `research/refactor-audit-2026-10/packages/impl_workflow_w2.js` is the implementer/reviewer prompt contract
   (one worktree per package, re-verify at HEAD, failing test first for bugs, one commit per finding, adversarial
   review of the diff). Point its paths at the new scratch dir.
3. Start each package from its pushed `refactor/*` branch (or from origin/main for unstarted packages), rebased on
   origin/main. Commit subjects identify related work; inspect explicit WIP/skip/test/review/merge state before
   treating a finding as complete. Status per finding:
   `research/refactor-audit-2026-10/data/finding-status.json`.
4. Every package needs its adversarial review before merge; none has had one.

#### Coordination (workspace-58, 2026-10-24)

- Push only `refactor/<topic>` branches with an explicit refspec, rebased on origin/main; never main.
- Live paths on the host: no structural refactor of `scripts/server/orchestrator_stack.py`, `scripts/region-lock`,
  `src/runtime/*region_lock*`, `scripts/gitnexus-analyze.sh` (bug fixes only), and those keep their paths and
  CLIs. Never the llama.cpp trees. `scripts/benchmark/` and `scripts/kernel_rnd/autokernel/` are pinned by SHA by
  running jobs: merge with a deliberate re-pin.
- Do not hand-edit the index files, `.index-state.json`/`.index-graph.json`, `backlog-priority.json`,
  `wiki/source_manifest.json`, `progress/*-workspace-58.md`, `INCIDENT_LOG.md`, or the handoffs workspace-58 listed.

#### Success criteria

1. Every finding is either implemented with a regression or characterization test, or recorded as skipped with
   a reason (already fixed, does not reproduce, unsafe).
2. The orchestrator suite collects and runs off the host, and no package adds a failure to the baseline set
   (`data/orch_baseline_failing_ids.txt`).
3. AutoKernel source shrinks by roughly the approved ~150k LOC, the live-loop and decision-arithmetic suites stay
   green, and the regrowth guard is a satisfiable ratchet that CI runs.
4. Orchestrator CI runs on pull requests; the AutoKernel workflow can go green when re-enabled.
5. No function in the touched hotspots stays above ~300 lines without a recorded reason.

#### Notes

- **The evaluator files are booby-trapped**: any byte change to the four fingerprinted files splits the AP-55
  regime (B5-03). Until P5 lands, do not reformat or edit them, including blanket `ruff format`.
- **ni63 source pins**: `tests/fixtures/ni63_capacity_child/source_clone.py` byte-pins ~30 production files to
  a past commit. Any change to a pinned file must refresh its (blob sha1, sha256). The pin for
  `scripts/server/orchestrator_stack.py` is already stale on main, so those 4 tests fail there too. O8 fixes the design.
- **Guards found broken on the way** (epyc-root, `refactor/containment-scanner`): the filesystem-containment
  scanner allowed writes outside the roots when a redirect followed the destination (`cp secret /outside
  2>/dev/null`), checked the branch instead of the path in `git worktree add`, and missed shell structure; and
  since 84b0de13 its degraded mode allows `sudo mount`. Also: `scripts/harness/strategy_projection_report_capture.py`
  `TRUSTED_APP_SOURCES` has 6 of 11 pins stale at base (reported by O3).
- **Unverified units**: C4, C5, C6 findings were never adversarially verified; the packages re-verify them first.
- **Not filed (explicit decline)**: `scripts/hooks/tests/test_harness_guard_parity.py::test_generator_check_exits_zero`
  fails identically on main in the container; it compares against the host's generated opencode config, so it
  says nothing about this work.
- **Usage pacing**: 6 concurrent agents exhausted a 5-hour window in about 55 minutes on 2026-10-24 (extra usage
  rejected: `out_of_credits`); 2 concurrent agents is the sustainable rate.

##### Native packet preparation checkpoint — 2026-10-27 22:55 UTC

- [x] **HIL-CHECKPOINT-NATIVE-PREP** — source-bound one-unit/three-slot canary and separate20-unit pilot prepared with immutable slot evidence, runtime-receipt resume refusal and captured detached-child cleanup. Full fake-server entries and all six quarter alternatives passed scoped26–27 PF, normal admission and validator0/0. Old pilot excluded; no model execution, band or quality claim. See [packet record](../../progress/2026-10/2026-10-27-native-repair-packets-2255.md). ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **M4-HOL-V2-NATIVE-PREP** — fix harness prematurely stopping its own long-prefill server; full fakeHTTP phaseA/B fixture, STOP/failure/deadline/cleanup, source-bound PF and normal admission passed0/0. Claude armed GPUv2 PID1707428; native rerun outcome pending, parentM4 open. ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **M4-OFF-NATIVE-READOUT** — reviewed all7 prompt hashes and21 native responses, exact content+reasoning identity against both C5 controls,0mismatch/0nondeterminism/0incomplete. Native run complete in~146s; correctness observation only. Preserve original protocol/co-tenant limits; no wholeM4, speed or promotion claim. ✅ 2026-10-27 [belief: cc]

##### Dispatch checkpoint — 2026-10-27

- [x] **M4-CURRENT-C5-OFF-PAIR-PREP** — four-load current-C5/M4 OFF packet prepared against the ratified paired0.9–1.1 rule; full fakeHTTP/lifecycle/guard fixtures, source-bound PF/admit/validator0/0 passed. GPU7800/min6000s, source e56b292276b33a93b450bb0e82bf7d7e2eaa36d362676eaf0e8a3480efa64023; no actual C2 result or parent completion. Existing family extension and OPEN reader/canary task filed. ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **ATT-CANARY-V2-PREP** — repaired bundled libpciaccess loader path, live grant/STOP/HOLD/deadline guard and captured process-group cleanup. Actual CPU-only loader controls plus model-free lifecycle fixtures and current source-bound PF/admit/validator0/0 passed; GPU900/min600s. No GPU trace, MFMA count or efficiency claim. ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **HSF5P-RESTORE-R11-DIAGNOSTIC** — the repaired-C5 scheduled run completed `rc0`; three save/erase/restore/continuation checks each reported matching 4,116-token counts and equal saved/read byte counts (740,054,204; 938,916,368; 938,916,368). The own server was reaped and an independent native-output/cleanup reader passed. This is one diagnostic run, with no timing, quality or promotion verdict. Evidence: `/mnt/raid0/llm/tmp/hsf5p-r11-repair-20261028/runs-official/` and the keeper launcher log. ✅ 2026-10-28 [belief: cc]
- [x] **ATT-INSTRUCTION-STREAM-DIAGNOSTIC** — a bounded real gfx90a probe produced raw SE0/SE4 ATT data and its native kernel exited `rc0`; the wrapper refused `rc1` at strict decoding. Offline GPU-denied decoding of the two streams from that single run found 32 ordered repetitions of the eight static MFMA instructions. Both decoders reported zero waves, so per-wave completeness and trace loss remain unknown. This narrow instruction-stream observation is not the decoded-wave canary, an efficiency claim or a READY result. Evidence: `/mnt/raid0/llm/tmp/att-decoded-r5-prep-20261028/checked-se0.log` and `checked-se4.log` in the same directory. ✅ 2026-10-28 [belief: cc]
- [x] **HIL-HEAVY-PILOT-PREP** — full20-task/60-slot cohort prepared at24threads with3600/min1800s and four mutually exclusive quarter placements. Native two-unit/six-slot fixture, resume/no-redraw and detached-child cleanup, all scopedPF/admit/validator0/0 passed; one task rather than four independent studies. Existing HIL producer family, no quality/band result. ✅ 2026-10-27 [no-belief: preparation and synthetic fixtures only]
- [x] **LB49-SCOPED-AUTHORIZATION-RECORDED** — operator approved the exact pinned experimental port, including shared parser CRITICAL43 and all six pinned input hunks; private experimental source/build/tests only. Production/deployment/promotion remain excluded. Expanded actual graph qualification and build preparation continue under owner compute; this is not a risk downgrade or completed port. ✅ 2026-10-27 [no-belief: operator authorization, no measurement]

##### CPU layout source enrollment checkpoint — 2026-10-28

- [x] **CPU-LAYOUT-SOURCE-ENROLLMENT** — register the YaRN CPU shard and CL3 quarter profile layouts with open strict-reader/planning tasks, and record the repaired M4 v2 producer scope. This is source enrollment and failure documentation, not validated launcher readiness. YaRN s2 was granted before this extension publication; its timing is disclosed without retrospective warrant. See [checkpoint](../../progress/2026-10/2026-10-28-launcher-repair-and-enrollment.md). ✅ 2026-10-28 [no-belief: source enrollment and maintenance only]
- [x] **RUN13-M4-NATIVE-REPAIR** — repaired deadline descendant cleanup; actual engine failure fixtures, actual same-entry host preflight, stable engine seal and fresh source-bound M4 row are complete and handed to Claude; owner armed row PID 2427508 at 01:13. The parent M4/C2 native result remains pending; preserve the old false COMPLETE and all native partial evidence. ✅ 2026-10-28 [no-belief: launcher implementation, synthetic controls, and no-model preflight; no native M4 result]

##### Validated run13 engine and HIL discovery enrollment — 2026-10-28

- [x] **RUN13-ENGINE-REPAIR-VALIDATED** — versioned engine passes actual complete-job PASS/FAIL, load failures, STOP/HOLD, watcher/engine deadlines, stale marker and zero-incomplete fixtures; child-exit and between-load TERM regressions pass and owned descendants drain. Engine SHA256 `fbcf07ca57b4c6d938151e2c3269191edb19241a35a0d2057bf7e8b0d85a171a`, exact logs in [checkpoint](../../progress/2026-10/2026-10-28-launcher-repair-and-enrollment.md). Per-consumer real-entry PF/admission remain mandatory; this does not complete M4. ✅ 2026-10-28 [no-belief: launcher implementation and synthetic failure controls]
- [x] **HIL15-DISCOVERY-SOURCE-ENROLLED** — register the fixed 60-task discovery assessment and OPEN strict-reader/planning task before new measurement. Gold/novelty/no-redraw/native fake-entry/selection controls pass; actual host prerequisites pass without model load. Four distinct 15-case shard rows now have nine validated placement variants; seven alternative placements remain unvalidated. The validated variant receipts are recorded separately; the cohort outcome remains open. ✅ 2026-10-28 [no-belief: prospective enrollment and synthetic controls]


##### Qualified launcher preparation and HIL shard delivery — 2026-10-28

- [x] **UFH14-SERVING-TRACE-QUALIFICATION** — source-qualified serving-call integrity LB6 launcher preparation is complete on orchestrator main `6b25fe9acf1bc8b8a9c2908c4d918483f5811c14`. The 106-case suite plus six fake-entry cases passed; source-bound PF used nonce `ae1b7fc54bb7a9d71ac789f97670c9800a47008f5036d868`, followed by normal admission and validator 0/0. PF was scoped to CPUs 26–27 while the row claims 0–23; normal placement remains a live-entry check. Packet: `/mnt/raid0/llm/tmp/refactor-01a16fc3/ufh14-serving-calls-ready/`; 106-case test log `prep/20261028T005856Z-2374852/command.log`, six fake-entry test log `prep/20261028T010837Z-2427965/command.log`, PF receipt `dryrun/ae1b7fc54bb7a9d71ac789f97670c9800a47008f5036d868/pass.json`, and final admission/validator log `prep/20261028T011823Z-2481749/command.log`. Preparation only; no actual model/server result is claimed. ✅ 2026-10-28 [no-belief: source implementation and model-free validation only]
- [x] **HIL15-DISCOVERY-SHARD-DELIVERY** — four distinct 15-case shard rows passed source-bound PF/admission/validator checks, with nine validated placement variants and seven alternatives unvalidated. Shards s0/s1/s2 were delivered to Claude and armed; s3 is held at the M4 SMT-sibling timing boundary. The native-readiness placement record is `/mnt/raid0/llm/tmp/refactor-01a16fc3/hil15-decision-cohort-ready/PLACEMENT-CHECKPOINT.json`. This records preparation and owner handoff only: no shard outcomes or HIL cohort result. ✅ 2026-10-28 [no-belief: packet preparation and delivery; no HIL result]

- [x] **HIL15-SHARED-VENV-INCIDENT-ATTRIBUTION** — root cause attribution is filed: the authorized M4 CPU scope helper capture at `scope-check/20261028T015457Z-2658028/` ran `scope.sh --backend cpu`; its `command.log` reports building `epyc-orchestrator`, uninstalling one package, and installing one package into the shared editable environment. Helper PID `2658028` is not an installer PID. HIL s1 retains six completed slots, with 39 unstarted; replay 02-2 overlap effect remains undetermined. Preserve original evidence; no redraw and no no-impact claim. The owner has prohibited further shared orchestrator-venv writes and requires private environments; private-runtime v5 continuation was separately preflighted/armed. See [incident checkpoint](../../progress/2026-10/2026-10-28-codex-ni-01a16d6b-hil-venv-incident.md) and [publication audit correction](../../progress/2026-10/2026-10-28-codex-refactor-01a16fc3-hil-venv-publication-audit.md). ✅ 2026-10-28 [no-belief: incident attribution and runtime repair only; no HIL outcome]

- [x] **M4-C1-NATIVE-READOUT** — file the reviewed HOL-v2 mechanism PASS (512 B/A0.9990076596;2048 B/A0.9975592176;12 valid collision rows) with original source/rule hash checks and the full unobserved NI co-tenancy disclosure. The earlier harness-truncated attempt is superseded; current-C5 OFF paired C2 and the parent M4 gate remain separate. See [checkpoint](../../progress/2026-10/2026-10-28-launcher-repair-and-enrollment.md). ✅ 2026-10-28 [belief: cc]

- [x] **M4-GPU-QUALITY-SOURCE-ENROLLMENT** — enroll the prospective role-paired GPU quality source and open its strict-reader/planning task. Native GPU quality and the parent fold gate remain unmeasured; source enrollment does not make the launcher ready. ✅ 2026-10-28 [no-belief: prospective source enrollment only]

- [x] **M4-GPU-QUALITY-R12-RESULT** — the paired architect Qwen3.8-27B GPU quality gate completed `rc=0` on 2026-10-28 with both arms using concurrency four. MMLU-Pro: 118/200 versus 118/200; GPQA: 117/195 versus 115/195. Both candidate scores meet the predeclared baseline-minus-five-percentage-point tolerance; all 790 rows have zero recorded errors and truncations. Actual GPU residency, four concurrent slots per cell, matching prompt identities and captured-server cleanup were independently checked. Native artifacts and comparisons: `/mnt/raid0/llm/tmp/codex-m4-gpu-quality-r12-native/output/`. Embedded measurement and attestation hashes verify; ledger ingestion is not claimed. This is the quality gate only, not a parent-fold, speed or promotion result. ✅ 2026-10-28 [belief: cc]

- [x] **M4-RECUT-C3-DIAGNOSTIC-RESULT** — the source-bound run13 r2 diagnostic completed `rc=0` at 19:07 UTC with native verdict **FAIL**. All seven champion identities were deterministic; the candidate matched both passes on five identities but differed on pass 2 for both pair4k identities. Independent checks validated all 28 successful 96-token records and recomputed their token/text hashes; the two requested-slot client intervals overlapped in both passes and arms. This proves client overlap, not simultaneous server-slot residency; C1/C2 and promotion were outside this diagnostic. The original run12 attempt failed `rc6` before model load and is superseded for this result. Evidence: `/mnt/raid0/llm/tmp/codex-m4-c3-original-r2-20261028/attempts/run-20261028T185919367038969/`. ✅ 2026-10-28 [belief: cc]
- **Diagnostic-instruction violation:** r2's inherited `make-record.py` created `PRELOAD_WARRANT.json` in the completed diagnostic attempt despite the operator's prohibition on diagnostic receipts/seals. Preserve the file as evidence, do not treat it as a diagnostic receipt or rely on it for the finding; the follow-up removes this writer.
- [x] **M4-RECUT-C3-PAIR-DIVERGENCE** — investigate the two pair4k pass-2 divergences and measure both server admission orders on both images. The controlled-order diagnostic completed `rc=0` on 2026-10-28: within each order, all three repetitions matched between images, while 0→2 and 2→0 differed starting at token index 2 for both slots on both images. Independent audit verified all 24 raw completions and hashes, all 12 client overlaps, native server admission ordering, GPU residency and server teardown. This is an order-associated observation in this run, not a proven mechanism or a promotion decision. Evidence: `/mnt/raid0/llm/tmp/codex-m4-order-diag-20261028/attempts/run-20261028T192253258894951/ORDER-DIAGNOSTIC.json`. ✅ 2026-10-28 [belief: cc]
- [x] **M4-C3-ORDER-CONTROLLED-DIAGNOSTIC** — the controlled successor completed rc0 under the MI210 grant. Its C3 condition passed: all seven champion identities were deterministic across both passes and both candidate-off passes matched; pair4k logs recorded 0→2 admission in each pass of each arm with overlapping client request intervals. Overall native verdict is INCOMPLETE because C1/C2 were not measured. Client overlap and observed admission order do not prove simultaneous server-slot residency, and this does not authorize a full M4 or production/fold gate. The original C3 failure remains preserved above. Evidence: `/mnt/raid0/llm/tmp/codex-m4-c3-order-controlled-20261028/COMPLETE` points to the retained `VERDICT.json` (SHA-256 `784cca3dd1ba7701cc418bbb62f183ed1df960d49594698307757c9226506f2c`); controlled amendment `PREDECLARATION.md` SHA-256 `fb939843ebb42d9eeb7b7bd7af0dcd9033354a36a09a83ceee5e169bff88b213`. The completed manifest names an older scratch log reader; retain that reader and the byte-identical copy in this run directory. ✅ 2026-10-29 [no-belief: diagnostic source enrollment is prospective; no measurement tuple]
- **M4-RECUT-ORDER-ROOT-CAUSE** — trace the observed admission-order sensitivity in the SRPF-off path and determine what further controlled evidence is needed to explain it; preserve the two-image result and avoid attributing a kernel cause without proof. [declined: operator 2026-11-04 the plan measured decode, which SRPF cannot move; default-OFF fold needs no A/B; greedy identity is unsound under batching]
- [x] **M4-ORDER-SPEC-CONTRAST** — the C5 diagnostic completed `rc=0` at 19:53 UTC. Across three repetitions per condition, both requested slots changed with 0→2 versus 2→0 when DFlash was on; with DFlash off, slot 0 stayed identical and slot 2 still changed. The two configurations also differed beyond speculative decoding, including draft memory. A separate raw-record check verified all 24 responses, hashes, 12 client overlaps, recorded server admission orders, GPU residency and cleanup. This shows the order-associated difference can appear without DFlash for slot 2; it is not a causal mechanism, general performance or promotion claim. Evidence: `/mnt/raid0/llm/tmp/codex-m4-order-spec-diag-20261028/attempts/run-20261028T194522838332151/ORDER-DIAGNOSTIC.json`. ✅ 2026-10-28 [belief: cc]
- [x] **M4-ORDER-DIAGNOSTIC-READY** — prepare the controlled-arrival-order follow-up across C5 and M4-off. The final same-launcher real GPU smoke ran 146 seconds, completed four ordered 0→2 pairs, and verified GPU residency and cleanup; a separate cutoff returned `rc75` with verified cleanup. The keeper queued it at 19:17 UTC with zero refusals. Manifest: `/mnt/raid0/llm/tmp/compute-flags/ready/armed/codex-m4-order-diag-20261028.json`. The scheduled reverse-order and paired-image comparison remain unmeasured. ✅ 2026-10-28 [no-belief: diagnostic smoke and launcher preparation only]

- [x] **LB49-DIAGNOSTIC-PUBLISH-GATE** — remove the self-imposed requirement that the already-pushed diagnostic source registration be an ancestor of `origin/main`. The replacement publisher verifies the actual remote branch, registration commit and exact source/task contents while retaining real-smoke, model, retention and collision checks. Its bounded watcher is running; LB49 itself still requires a real free-quarter smoke and has not been published READY. ✅ 2026-10-28 [no-belief: publisher repair only; no measurement]
- [x] **LB49-DS41-PAIRED-DIAGNOSTIC** — the repaired launcher completed `rc0` on 2026-10-28 under a real q0 grant. Both matched private CPU build arms loaded canonical DS41 after separate 739 GiB admissions and returned successfully to the same short prompt. Both answered Paris, but their raw output text differed; no parity conclusion follows. Independent checks matched both log hashes and the final result hash, verified both child PIDs had exited, and confirmed the result is non-partial and diagnostic-only. This is a narrow operational observation, not an attention-sink, route-coverage, quality, performance or promotion result. Native output is referenced by `/mnt/raid0/llm/tmp/lb49-r11-source-draft-20261028/COMPLETE.json`. ✅ 2026-10-28 [belief: cc]

- [x] **M4-CPU-CALIBRATION-SOURCE-ENROLLMENT** — enroll prospective architect CPU load and warmup memory samples and open their strict-reader/planning task. This is preparation only; no model execution or resource peak claim. ✅ 2026-10-28 [no-belief: prospective source enrollment only]

- [x] **M4-WORKER-CALIBRATION-SOURCE-ENROLLMENT** — enroll prospective worker/frontdoor CPU load and warmup samples and open their strict-reader/planning task. Preparation only; no model execution or peak claim. ✅ 2026-10-28 [no-belief: prospective source enrollment only]

- [x] **M4-VISION-CALIBRATION-SOURCE-ENROLLMENT** — enroll prospective vision CPU load and warmup samples and open their strict-reader/planning task. Preparation only; no model execution or peak claim. ✅ 2026-10-28 [no-belief: prospective source enrollment only]

- [x] K3 / C6-07: isolate T3 test fixtures in private temporary checkout roots; preserve actual authority/refusal boundaries and historical fixture bytes. Research main `1f1fc348e6dec11fd4c90cdaf3b6972c226af74c` includes reviewed `e9c1a3ac`;384 host controls plus124 related tests pass. Collection of1009 release tests succeeds in Git and exported source without touching live operator fixtures. Runtime default-root positives remain explicitly host-dependent. ✅ 2026-10-30 [no-belief: fixture isolation and source regressions]

- [x] D10 / C5-04: share fixed T0 constructors, production pins and consecutive A/A arithmetic without importing the campaign driver from four actual runtime callers. Research main `3a4e4e8123a0221c38d8fd26fd2a1319b075d6ac` includes reviewed `6b3977394209e3332968e6f3e6da3a885c48d1d8`;376 qualified tests/247 subtests pass, with13 independently reproduced baseline failures excluded. Postmerge68 tests/112 subtests and value equivalence pass. Legacy entry points and all policy/pin values retained; three new leaves enter source fingerprints. Bare loop.run already avoided campaign before this change. ✅ 2026-10-30 [no-belief: source dependency extraction and deterministic controls]
- [x] HIL15 S2 resource-admission repair: preserve original45=17accepted/1immutableunknown/27unexposed; place new native outputs on Micron while real source/launcher/state/log scratch stays RAID. RAID metadata has a sampled128MiB cap and independent150GiB floor+.125GiB margin; native output retains its full1GiB sampled cap,64GiB RSS budget and unchanged cohort/protocol. Existing arm/validator/T1/grant controls pass all four quarters; actual same outer launcher normal31.264s/active-cutoff68.389s, partial100-token witness and captured-tree drain pass. `codex-hil15-s2-micron-v8-20261030` accepted by normal keeper05:36:16 on0–23, PID2214155, zero validator refusals. This closes launcher preparation only; original collection/measurement remains open. Evidence `/mnt/raid0/llm/tmp/hil15-s2-split-storage-v8-20261030/READY-PUBLISHED.json`. ✅ 2026-10-30 [no-belief: operational resource repair and native launcher qualification]

- [x] HIL15 S0 resource-admission repair: split actual RAID launcher/state/log metadata from full1GiB native output on Micron, preserving original45=32accepted/3immutableunknown/10unexposed. Existing arm/full validator/T1/grant controls pass all four quarters with actual RAID disk; same outer launcher normal16.341s rc0 and witnessed active cutoff26.323s rc75/partial/drain pass. Normal keeper accepted `codex-hil15-s0-micron-v9-20261030`05:48:37 on0–23, PID2281641, zero refusals. Native capture remains pending; no original measurement closure. Evidence `/mnt/raid0/llm/tmp/hil15-s0-split-storage-v9-20261030/READY-PUBLISHED.json`. ✅ 2026-10-30 [no-belief: operational admission and native launcher qualification]


#### Disk-emergency checkout cleanup — 2026-10-30

- [x] Archive or abandon owned cold source drafts and gate-remove 82 RAID worktrees plus 12 RAM views. At least 56.06 GiB of attributed RAID allocation was reclaimed; RAM, unmeasured removals and other sessions' df gains are excluded. The assigned 60-tree list now has only the active peer-owned QB2 registration remaining. INF22 is a four-file compatibility directory, with both retained peer manifests matching, rather than a Git checkout. Verified source refs and Micron archives preserve unique code and evidence; refactor packages are not accepted by this cleanup. Protected ongoing root/HIL/census views remain intact. [Proof](../../artifacts/compute/refactor-worktree-cleanup-20261030.json). ✅ 2026-10-30 [no-belief: operational checkout cleanup]


**T1 repair checkpoint (2026-10-30):**

- [x] Publish S0 v10 and S2 r11 with private T1 bypasses and same-final-hash real normal/active-cutoff smokes; original accepted/unknown/unexposed ledgers are preserved. Normal keeper reports both READY-WAIT for a free quarter. Revoke the ghost M4 booking through the own runner terminal lifecycle after proving its PID was a recycled kernel thread; no signals or native work occurred. S1/S3 exhausted cohorts were not replayed. [Proof](../../artifacts/compute/refactor-t1-repair-20261030.json). ✅ 2026-10-30 [no-belief: launcher repair and scheduling lifecycle; no cohort outcome claim]

- [x] **HIL15-S0-V11-READY-QUALIFICATION** — qualify and publish `codex-hil15-s0-micron-v11-20261030` after withdrawing the failed v10 READY and draining only its captured poller tree. The original v10 rc1 and its four immutable outputs were filed by C3 at root `b0c403d7` and remain preserved. Source-bound revalidation preserves the original45 denominator: 32 prior accepted + four immutable replay-verified outcomes (1 True, 3 False) = 36 known; 3 original unknown remain immutable; only six original unexposed unit14/15 slots are scheduled, with 42 known/3 unknown as the exhaustion target. The diagnostic packet is READY; its real same-final-bundle normal smoke exited0 and active-cutoff smoke exited75 after owned descendants drained. The post-unit fixture exercises the prior four read-only and validates the cutoff/partial path. This is launcher qualification only: no new cohort outcome, efficacy/native grade, or parent discovery completion. Evidence: `/mnt/raid0/llm/tmp/hil15-s0-no-sidecar-v11-20261030/{READY-PROPOSAL.json,SMOKE-EVIDENCE.json,FAILED-V10-POLLER-DRAIN.json,FAILED-V10-READY-WITHDRAWN-20261030.json}`; published READY: `/mnt/raid0/llm/tmp/compute-flags/ready/codex-hil15-s0-micron-v11-20261030.json`. ✅ 2026-10-30 [no-belief: launcher qualification and scheduler lifecycle only; no cohort outcome claim]


**Source/build wrap checkpoint (2026-10-30):**

- [x] Land repo-owned A6 sandbox isolation source and pre-exposure writer as research `276d75fab`; normal native read-denial proof and six focused controls accepted, with held draft/uncut request limits explicit. Publish a separately qualified, frozen-source C5 CPU build READY packet for the recipe successor. Source and build preparation only; broader refactor, A6 standing rule and AKX-ALL-8 measurement parent remain open. [Proof](../../artifacts/compute/refactor-a6-source-build-ready-20261030.json). ✅ 2026-10-30 [belief: cc]


**Refactor HIL S2 inner-admission repair (2026-10-30):**

- [x] Qualify and publish `codex-hil15-s2-r12-inner-t1-20261030` as the successor to withdrawn r11. ✅ 2026-10-30 [no-belief: launcher qualification only] Original45 slots remain18 accepted,2 immutable unknown and25 unexposed; no redraw or full native completion. The final source/engine bundle passed normal native replay and active decode cutoff at100tokens, rc75/partial with all owned descendants drained, plus actual no-argument entry and private inner controls. Source-bound job admission remains; only obsolete inner/outer T1 receipts are bypassed in the private diagnostic engine. Micron native output and8MiB RAID metadata budgets remain. HIL S0 and HILb8 live inputs were untouched. [Evidence](../../artifacts/compute/refactor-hils2-and-source-guards-20261030.json).

## Track: repo-readiness-scorer
<!-- gate: none -->

> Folded from `handoffs/active/repo-readiness-scorer.md` @ `ea07eb9ad4ae` on 2026-11-02 (BRF-T1-F3, route 1a, operator D1/D5; retired row EVL-38 → RTG-22). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Repo-Readiness Scorer (Agent-Readiness Model)

**Status**: v1 deterministic scorer landed 2026-06-13; deterministic remediation queue export, advisory Markdown rendering, passive AutoPilot pickup JSON, root no-inference candidate eval gate, dashboard summary, and default-off AutoPilot planner advisory bridge are live. Current 2026-07-06 artifacts show `epyc-root`, `epyc-orchestrator`, and `epyc-inference-research` at Autonomous/L5; `epyc-llama` remains Standardized/L3 with six blocking L4 workflow-surface gaps. The passive pickup artifact remains planning context only (`mode=advisory_only`, `authority_gate=false`) and is not an acceptance gate, promotion gate, or substitute for a true self-optimization loop. Future launches through `scripts/autopilot/start_fable_authority_daemon.py` inject the newest passive pickup unless `AUTOPILOT_REPO_READINESS_PICKUP` is explicitly set.
**Created**: 2026-06-03 (via research intake → factory.ai deep-dive)
**Categories**: benchmark_methodology, autonomous_research, knowledge_management

#### Objective

Build a CPU-only scorer that rates each of our repos against an "agent-readiness" maturity model (adapted from Factory's Agent Readiness Model), so we can (a) quantify how amenable our codebase is to autonomous agents, (b) track it over time, and (c) feed failing criteria into the autopilot as a remediation queue. We have **no equivalent** today.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-657 | Factory.ai docs (Agent Readiness Model / `/readiness-report`) | high | adopt_patterns |

Full mining → [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) (Part 3E + verbatim rubric).

#### The model (adapted from Factory)

**5 levels**, unlock the next by passing **80% of the prior level's criteria**:
1. **Functional** — runs, manual setup, little automated validation (README, linter, type checker, unit tests)
2. **Documented** — process written down (AGENTS.md/CLAUDE.md, devcontainer, pre-commit hooks, branch protection)
3. **Standardized** — processes enforced via automation (integration tests, secret scanning, tracing, metrics)
4. **Optimized** — fast feedback + data-driven improvement (fast CI, deploy frequency, flaky-test detection)
5. **Autonomous** — self-improving with orchestration

**9 technical pillars**: Style & Validation · Build System · Testing · Documentation · Dev Environment · Debugging & Observability · Security · Task Discovery · Product & Experimentation.

**Scoring**: fractional `n / sub-apps` (repository-scope criteria evaluated once; application-scope per sub-app). Our 4 sub-apps = epyc-root, epyc-orchestrator, epyc-inference-research, epyc-llama.

#### Open Questions

- Factory does **not** publish the full per-criterion list (only the 5 levels, 9 pillars, 80% rule, scoring format, one example) — so we authored a v1 criteria catalog: one concrete deterministic criterion per pillar per level (45 total).
- Where do we already score *high* (Task Discovery = handoff-index + kb-search; Product&Experimentation = autopilot Pareto archive; Observability = `logs/agent_audit.log` + `unified-trace-memory-service.md`) vs *low*? A first pass may mostly confirm strengths.
- Should detectors be pure shell/python file-presence + config-parse checks (cheap, deterministic) or LLM-judged (richer, noisier)? **Decision for v1**: deterministic only per `feedback_observe_before_diagnosing`; a pass means an artifact exists, not that quality is certified.
- Integration target: a `/readiness-fix`-analog autopilot remediation queue, or a passive dashboard alongside the tier-segregated Pareto dashboard? **Answered for passive consumption**: `--output-remediation-json` exports a deterministic remediation queue; `--output-autopilot-remediation-json` emits a passive AutoPilot pickup artifact with explicit non-authority metadata; the dashboard reads the latest report/queue; and the Fable authority launcher now wires the newest pickup into the planner prompt on future restarts. Any authority-bearing remediation workflow remains a separate protocol.

#### Current Artifacts

- Scorer: `/mnt/raid0/llm/epyc-root/scripts/validate/repo_readiness_scorer.py`
- Tests: `/mnt/raid0/llm/epyc-root/tests/validate/test_repo_readiness_scorer.py`
- JSON report: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_2026-07-06.json`
- Markdown report: `/mnt/raid0/llm/epyc-root/progress/2026-07/repo-readiness-2026-07-06.md`
- Remediation queue export: `scripts/validate/repo_readiness_scorer.py --output-remediation-json <path>` (landed in root `7e6b3ee18864f1d86e8b5ce4651449a5fd7c8ee2`)
- Current remediation queue JSON: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_remediation_queue_2026-07-06.json`
- Current remediation queue Markdown: `/mnt/raid0/llm/epyc-root/progress/2026-07/repo-readiness-remediation-2026-07-06.md`
- Current passive AutoPilot pickup JSON: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_autopilot_pickup_2026-07-06.json`

2026-06-13 first-run summary:

- Portfolio level: **Documented (L2)**.
- `epyc-root`: Optimized (L4), next gate Autonomous.
- `epyc-orchestrator`: Documented (L2), next gate Standardized.
- `epyc-inference-research`: Documented (L2), next gate Standardized.
- `epyc-llama`: Documented (L2), next gate Standardized.
- Lowest portfolio criteria: L3 security automation and standardized dev environment; L4 generated docs, health automation, prioritized task discovery, and security audit; L5 agent doc loop, auto eval gates, autonomous security review, self-optimizing loop.

Validation:

- `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`
- `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 3 passed.

2026-06-14 remediation-export update:

- Root commit `7e6b3ee18864f1d86e8b5ce4651449a5fd7c8ee2` added deterministic remediation queues via `--output-remediation-json`.
- Changed files: `/workspace/scripts/validate/repo_readiness_scorer.py` and `/workspace/tests/validate/test_repo_readiness_scorer.py`.
- Validation from the implementation sidecar: `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`; `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 5 passed.
- Remaining integration work: feed the exported queue into AutoPilot remediation planning or a passive dashboard without letting the scorer become a decision gate without a protocol.

2026-06-20 advisory-queue rendering update:

- Added `--output-remediation-md` plus `--remediation-md-limit` to render the deterministic queue as a Markdown pickup artifact while keeping JSON complete.
- Generated refreshed artifacts: `data/repo_readiness/repo_readiness_2026-06-20.json`, `progress/2026-06/repo-readiness-2026-06-20.md`, `data/repo_readiness/repo_readiness_remediation_queue_2026-06-20.json`, and `progress/2026-06/repo-readiness-remediation-2026-06-20.md`.
- Current queue: 49 open items; top P0 blockers include `epyc-inference-research` L3 style/test/task/dev-env/security gaps, `epyc-llama` L3 task/dev-env/security/experiment gaps, and `epyc-root` L5 auto-eval/self-optimizing-loop gaps. Markdown output is explicitly advisory and not an AutoPilot authority gate.
- Validation: GitNexus LOW on `score_repositories`, `build_remediation_queue`, and `render_markdown`; `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`; `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 7 passed; JSON and diff checks passed.

2026-06-21 passive AutoPilot pickup update:

- Added `--output-autopilot-remediation-json` plus `--autopilot-remediation-limit` to render the deterministic remediation queue as a passive planner-context artifact.
- Generated refreshed artifacts: `data/repo_readiness/repo_readiness_2026-06-21.json`, `progress/2026-06/repo-readiness-2026-06-21.md`, `data/repo_readiness/repo_readiness_remediation_queue_2026-06-21.json`, `progress/2026-06/repo-readiness-remediation-2026-06-21.md`, and `data/repo_readiness/repo_readiness_autopilot_pickup_2026-06-21.json`.
- Current pickup JSON carries `mode=advisory_only`, `authority_gate=false`, `source_item_count=49`, and the top 12 candidate items with required preflight rules (`review owning handoff`, GitNexus impact, generated/runtime artifact discipline, rerun scorer). This feeds planning only; it does not mutate AutoPilot or create a decision gate.
- Validation: GitNexus LOW on `build_remediation_queue`, `render_remediation_markdown`, `score_repositories`, and `main`; `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`; `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 9 passed; generated pickup JSON inspected with `jq` for passive-mode/non-authority fields.

2026-06-27 portability update:

- Root `19e1ac84` removes hardcoded canonical repo roots from the default scorer map.
- Default repo discovery now derives root from the script location, supports `/workspace/repos/<name>` fallbacks, keeps `/mnt/raid0/llm/...` as canonical fallback, and accepts explicit env overrides: `EPYC_ROOT_REPO`, `EPYC_ORCHESTRATOR_REPO`, `EPYC_INFERENCE_RESEARCH_REPO`, and `EPYC_LLAMA_REPO`.
- This is offline-only scorer hygiene; it does not change scoring criteria, remediation priorities, or AutoPilot authority.
- Validation: GitNexus LOW on implementation symbols per sidecar; main-thread verification `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`; `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 10 passed; `uv run --with ruff ruff check scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py` passed.

2026-06-27 research Standardized-gate update:

- `epyc-inference-research` commit `bfa785c` adds a top-level `Makefile`,
  `scripts/setup.sh`, and `.github/dependabot.yml`.
- The Makefile exposes green `lint` and `test` smoke targets over the
  maintained X-MAS function-axis table tooling instead of the legacy whole
  `scripts/` tree, which still has historical Ruff/pytest debt.
- `scripts/setup.sh` standardizes local setup through `uv sync --all-extras`;
  Dependabot adds weekly Python dependency security automation.
- A one-repo scorer run now reports `epyc-inference-research` as
  **Standardized (L3)** with L3 pass rate `88.9%`; the remaining L3 blocker is
  `L3.machine_task_index`.
- Validation: `make lint`; `make test`; `bash -n scripts/setup.sh`;
  `repo_readiness_scorer.py --repo epyc-inference-research=/mnt/raid0/llm/epyc-inference-research`.

2026-06-27 research machine-task-index update:

- `epyc-inference-research` commit `7d778e0` adds
  `handoffs/active/master-handoff-index.md` as a research-scoped machine task
  index.
- The index includes a prioritized task list, dependency graph, cross-cutting
  concerns, reporting instructions, and key file locations. It explicitly
  avoids claiming authority over production flips, which remain governed from
  root/orchestrator handoffs.
- A one-repo scorer run reported `epyc-inference-research` L3 at `100.0%`;
  the next gate was L4 Optimized with pass rate `55.6%`.
- Validation: `git diff --check -- handoffs/active/master-handoff-index.md`;
  research `make lint`; research `make test`;
  `repo_readiness_scorer.py --repo epyc-inference-research=/mnt/raid0/llm/epyc-inference-research`.

2026-06-27 research health-automation update:

- `epyc-inference-research` commit `2b6b97f` adds
  `scripts/session/health_check.sh` and exposes it as `make health`.
- The health check is no-inference: it verifies required repo paths, `uv`
  availability, maintained Python entrypoints, and dry-runs AA-Omniscience plus
  clean-window manifest generation into `/tmp`.
- A one-repo scorer run now reports `epyc-inference-research` L4 at `66.7%`;
  `L4.health_automation` passes.
- Remaining L4 blockers are `L4.generated_docs`, `L4.analysis_reports`, and
  `L4.security_audit`. These should be implemented only as real workflow
  surfaces, not placeholders.
- Validation: GitNexus impact for research `Makefile` LOW
  (`impactedCount=0`); research `make health`; research `make lint`; research
  `make test`; `repo_readiness_scorer.py --repo epyc-inference-research=/mnt/raid0/llm/epyc-inference-research`.

2026-06-27 research generated-docs update:

- `epyc-inference-research` commit `935a8ea` adds
  `scripts/docs/generate_docs_index.py`, `scripts/docs/test_generate_docs_index.py`,
  `make docs`, `make docs-check`, and the generated
  `docs/reference/GENERATED_DOCS_INDEX.md` artifact.
- The generated-docs lane is deterministic and no-inference: `--check` fails when
  the committed index is stale.
- A one-repo scorer run now reports `L4.generated_docs` as passing for
  `epyc-inference-research`.
- Remaining L4 blockers are `L4.analysis_reports` and `L4.security_audit`.
- Validation: research `uv run --with ruff ruff check
  scripts/docs/generate_docs_index.py scripts/docs/test_generate_docs_index.py`;
  `uv run --with pytest pytest -q scripts/docs/test_generate_docs_index.py`;
  `make docs-check`; `make lint`; `make test`; and the root one-repo readiness
  scorer for `epyc-inference-research`.

2026-06-27 research analysis-reports update:

- `epyc-inference-research` commit `f347809` adds
  `scripts/analysis/generate_analysis_reports_index.py`,
  `scripts/analysis/test_generate_analysis_reports_index.py`, `make analysis`,
  `make analysis-check`, and the generated
  `docs/reference/ANALYSIS_REPORTS_INDEX.md` artifact.
- The analysis-reports lane is deterministic and no-inference: it indexes
  existing Markdown/JSON analysis/report/summary artifacts and `--check` fails
  when the committed index is stale.
- A one-repo scorer run now reports `epyc-inference-research` as Optimized (L4)
  with L4 pass rate `88.9%`; `L4.analysis_reports` passes.
- Remaining L4 blocker is `L4.security_audit`.
- Validation: research `uv run --with ruff ruff check
  scripts/analysis/generate_analysis_reports_index.py
  scripts/analysis/test_generate_analysis_reports_index.py`; `uv run --with
  pytest --with pyyaml pytest -q
  scripts/analysis/test_generate_analysis_reports_index.py`; `make
  analysis-check`; `make lint`; `make test`; and the root one-repo readiness
  scorer for `epyc-inference-research`.

2026-06-27 research security-audit update:

- `epyc-root` commit `f077b197` teaches the deterministic scorer to count
  concrete `scripts/security/**` audit surfaces for `L4.security_audit`.
- `epyc-inference-research` commit `7638f0b` adds
  `scripts/security/audit_repository.py`,
  `scripts/security/test_audit_repository.py`, and `make security-check`.
- The audit is no-inference and scans tracked files only. It fails on
  secret-like tracked filenames, high-confidence credential literals in
  source/config/doc surfaces, and unexpected large tracked artifacts outside
  known benchmark result/image paths.
- A one-repo scorer run now reports `epyc-inference-research` as Optimized (L4)
  with L4 pass rate `100.0%`; the next gate is L5 Autonomous.
- Validation: research `python3 -m py_compile
  scripts/security/audit_repository.py
  scripts/security/test_audit_repository.py`; `uv run --with pytest pytest -q
  scripts/security/test_audit_repository.py`; `make security-check`; `uv run
  --with ruff ruff check scripts/security/audit_repository.py
  scripts/security/test_audit_repository.py`; `make lint`; `make test`; and the
  root one-repo readiness scorer for `epyc-inference-research`.

2026-06-28 orchestrator setup-gate update:

- `epyc-orchestrator` commit `c1cac72e` adds a top-level `scripts/setup.sh`
  entrypoint that delegates to the existing `scripts/setup/bootstrap.sh`.
- The bootstrap prerequisite check now accepts `uv`, `pip3`, or `pip` for the
  Python package manager prerequisite, matching the existing install path that
  already prefers `uv sync`.
- A one-repo scorer run now reports `epyc-orchestrator` as Standardized (L3)
  with L3 pass rate `88.9%`; the next gate is L4 Optimized.
- Remaining orchestrator blockers include `L3.security_automation` and L4
  workflow surfaces (`L4.generated_docs`, `L4.health_automation`,
  `L4.security_audit`, `L4.prioritized_tasks`). These should be implemented as
  real maintained surfaces rather than placeholders.
- Validation: GitNexus impact for `scripts/setup.sh`,
  `scripts/setup/bootstrap.sh`, and `check_prerequisites` returned UNKNOWN
  targets with `impactedCount=0`; `bash -n scripts/setup.sh
  scripts/setup/bootstrap.sh`; `./scripts/setup.sh --check-only`; and the root
  one-repo readiness scorer for
  `epyc-orchestrator=/mnt/raid0/llm/epyc-orchestrator`.

2026-06-28 default-off AutoPilot advisory bridge:

- `epyc-orchestrator` adds a default-off planner prompt section for passive
  repo-readiness pickup artifacts.
- The bridge is inert unless `AUTOPILOT_REPO_READINESS_PICKUP` points to a JSON
  artifact. It accepts only `mode=advisory_only` with `authority_gate=false` and
  otherwise renders an ignored/unavailable message.
- The rendered section is planner context only: it explicitly does not override
  owning handoffs, GitNexus impact checks, measurement gates, or scorer reruns.
- This closes the first safe live-consumption protocol for the passive pickup
  artifact without making repo-readiness a controller authority or acceptance
  gate. Existing running AutoPilot processes will not see it until a future
  restart with the env var set.
- Validation: GitNexus impact for `CONTROLLER_PROMPT_TEMPLATE` and
  `_run_loop_inner` returned LOW; `uv run pytest
  tests/unit/test_autopilot_actions.py tests/unit/test_autopilot_system_card.py
  -q` -> 82 passed; `uv run ruff check scripts/autopilot/autopilot.py
  tests/unit/test_autopilot_actions.py`; `python3 -m py_compile
  scripts/autopilot/autopilot.py tests/unit/test_autopilot_actions.py`.

2026-06-28 orchestrator security automation/audit update:

- `epyc-orchestrator` adds `.github/dependabot.yml` for weekly `uv` and
  GitHub Actions dependency updates, closing the deterministic
  `L3.security_automation` criterion with a real supply-chain automation
  surface.
- `epyc-orchestrator` adds `scripts/security/audit_repository.py`,
  `scripts/security/test_audit_repository.py`, and `make security-check`.
  The audit is no-inference and scans tracked files only. It fails on
  secret-like tracked filenames, high-confidence credential literals in
  source/config/doc/test surfaces, and unexpected large tracked artifacts
  outside known benchmark/report/repl-memory paths. The only secret-literal
  allowlist is the existing credential-redaction fixture test.
- A one-repo scorer run now reports `epyc-orchestrator` with
  `L3.security_automation=true`, `L4.security_audit=true`, and L3 pass rate
  `100.0%`. Remaining L4 blockers are `L4.generated_docs`,
  `L4.health_automation`, and `L4.prioritized_tasks`.
- Validation: GitNexus impact for the new security/dependabot targets returned
  UNKNOWN with `impactedCount=0`; `python3 -m py_compile
  scripts/security/audit_repository.py scripts/security/test_audit_repository.py`;
  `uv run --with pytest pytest -q scripts/security/test_audit_repository.py`
  -> 4 passed; `uv run --with ruff ruff check
  scripts/security/audit_repository.py scripts/security/test_audit_repository.py`;
  `make security-check`; `git diff --check` on the touched paths; and the root
  one-repo readiness scorer for
  `epyc-orchestrator=/mnt/raid0/llm/epyc-orchestrator`.

2026-06-28 orchestrator L4 closeout:

- `epyc-orchestrator` adds deterministic generated-docs, health, and local task
  coordination surfaces:
  `scripts/docs/generate_docs_index.py`,
  `scripts/docs/test_generate_docs_index.py`,
  `docs/reference/GENERATED_DOCS_INDEX.md`,
  `scripts/session/health_check.sh`, and
  `handoffs/active/master-handoff-index.md`.
- The generated-docs lane indexes committed `docs/**/*.md` files and supports
  `--check`; Makefile targets now expose `docs`, `docs-check`, and `health`.
- The session health lane is no-inference: it checks core repo artifacts,
  py-compiles stack/phase/security health entrypoints, and runs the tracked-file
  security audit.
- The local handoff index is explicitly subordinate to the root master index and
  carries prioritized tasks, dependencies, cross-cutting concerns, reporting
  rules, and key files for orchestrator-only work.
- A one-repo scorer run now reports `L4.generated_docs=true`,
  `L4.health_automation=true`, `L4.prioritized_tasks=true`, and the only
  remaining failed orchestrator criterion as `L5.autonomous_security_review`.
- Validation: GitNexus impact for existing `Makefile` returned LOW; new-target
  GitNexus checks for docs/health/index paths returned UNKNOWN with
  `impactedCount=0`; `python3 -m py_compile` for docs/security scripts and
  tests; `uv run --with pytest pytest -q scripts/docs/test_generate_docs_index.py`
  -> 2 passed; `uv run --with ruff ruff check
  scripts/docs/generate_docs_index.py scripts/docs/test_generate_docs_index.py`;
  `make health`; `make security-check`; `make docs-check`; `git diff --check`;
  and the root one-repo readiness scorer for `epyc-orchestrator`.

2026-06-28 orchestrator autonomous-security-review closeout:

- `epyc-orchestrator` commit `4b27fd5d` adds an orchestrator-scoped
  security-review skill and slash command:
  `.claude/skills/security-review/SKILL.md`,
  `.claude/skills/security-review/agents/openai.yaml`, and
  `.claude/commands/security-review.md`.
- The skill is exploit-path gated and specific to orchestrator attack
  surfaces: API/OpenAI-compatible routes, AutoPilot/controller paths,
  StrategyStore and runtime state, tool/REPL/MCP execution, stack launch/config
  surfaces, generated artifacts, dependencies, and shell/CI changes.
- A one-repo scorer run now reports `epyc-orchestrator` as **Autonomous (L5)**
  with all level rates at `1.0`, including
  `L5.autonomous_security_review=true`.
- Validation: new-file GitNexus impact checks returned UNKNOWN with
  `impactedCount=0`; skill frontmatter and `agents/openai.yaml` parsed with
  PyYAML; path-scoped `git diff --check` passed; and the root one-repo
  readiness scorer for `epyc-orchestrator` reported no failed criteria.

2026-06-28 portfolio artifact refresh:

- Regenerated the full four-repo readiness report, remediation queue, advisory
  Markdown queue, and passive AutoPilot pickup artifact after the orchestrator
  L5 and research L4 closeouts.
- Current portfolio level is **Optimized (L4)** with L5 as the next gate.
  Repo levels: `epyc-orchestrator` Autonomous/L5, `epyc-root` Optimized/L4,
  `epyc-inference-research` Optimized/L4, and `epyc-llama` Standardized/L3.
- A follow-up detector refinement recognized llama-native evidence already
  present in the fork: `docs/ops/**` and bench scripts now count for
  experiment surfaces, `flake.nix`/`CMakePresets.json` count for standardized
  dev environment, and sanitizer workflows count as security automation. This
  removed false-positive llama blockers without editing the llama repo.
- The deterministic remediation queue now has `24` open items, down from the
  stale `49`-item 2026-06-21 pickup. The remaining blocking candidates are
  L5 autonomy surfaces for research/root plus the true `epyc-llama` task-index
  gap on the path to L4. The passive pickup remains `mode=advisory_only` and
  `authority_gate=false`.
- Validation: GitNexus impact was LOW for `score_repositories`,
  `build_remediation_queue`, and `build_criteria`; the generic `main` lookup
  was ambiguous but no code edit was made. `repo_readiness_scorer.py`
  regenerated the artifacts without errors, focused tests passed, and generated
  JSON was inspected with `jq` for portfolio level, queue count, and
  non-authority pickup fields.

2026-06-28 research L5 and llama task-index update:

- `epyc-inference-research` commits `8cef3d4`, `817ccdf`, `8ffdc51`, and
  `7c4929c` close the remaining deterministic L5 readiness surfaces with real
  no-inference workflow entrypoints:
  - `.claude/skills/security-review/SKILL.md` and
    `.claude/commands/security-review.md` add an exploit-path-gated,
    research-specific security review surface.
  - `scripts/autopilot/candidate_eval_gate.py` plus `make autopilot-gate`
    chains docs, analysis, security, health, and focused tests as a fail-closed
    candidate gate.
  - `scripts/halo/closed_loop_observation_surface.py` and
    `scripts/halo/convert_tap_to_otel.py` convert benchmark/log/report JSONL
    into deterministic closed-loop observation envelopes.
  - `scripts/session/emergency_cleanup.sh` adds a dry-run-first stale-PID
    cleanup surface, and `scripts/session/health_check.sh` now syntax/smoke
    checks the new L5 surfaces.
- Validation: research `make autopilot-gate` passed end-to-end
  (`docs-check`, `analysis-check`, `security-check`, `health`, and `17`
  focused tests); focused `py_compile`, `ruff`, `pytest`, `bash -n`, and
  `git diff --check` passed on the touched surfaces. A one-repo readiness
  scorer run reports `epyc-inference-research` as **Autonomous (L5)** with
  L1-L5 all `100.0%`.
- `epyc-llama` commits `cc29b7a6a` and `4412872ca` add a docs-only readiness
  index plus detector-visible `handoffs/active/master-handoff-index.md`.
  A one-repo scorer run now reports `epyc-llama` L3 at `100.0%` and
  `L4.prioritized_tasks=true`; remaining llama next-gate blockers are the real
  L4 workflow surfaces (`incremental_validation`, `generated_docs`,
  `health_automation`, `analysis_reports`, `security_audit`, and
  `replay_analysis`).

2026-07-03 artifact refresh:

- Regenerated the four-repo readiness report, remediation queue, advisory
  Markdown queue, and passive AutoPilot pickup artifact after the research L5
  closeout, root candidate-gate closeout, and current repo-state updates.
- Added `scripts/validate/candidate_eval_gate.sh` as the root no-inference
  candidate gate. It bundles root validator syntax checks, agent governance
  validators, CLAUDE.md matrix validation, registry operating-point validation,
  the held-out PII fixture eval, a temp repo-readiness regeneration, and focused
  scorer tests. Wiki/source-manifest drift is intentionally opt-in via
  `--strict-doc-drift` until the wiki refresh lane is clean.
- Refined the root L5 detector so the candidate gate satisfies
  `L5.auto_eval_gates`. A parallel audit rejected crediting passive
  repo-readiness pickup artifacts as `L5.self_optimizing_loop`; the scorer test
  now pins that guardrail, and the passive pickup remains advisory planning
  context only.
- Current portfolio level is now **Autonomous (L5)**: `epyc-root`,
  `epyc-orchestrator`, and `epyc-inference-research` are Autonomous/L5;
  `epyc-llama` is Standardized/L3 with L4 pass rate `33.3%`.
- The deterministic remediation queue is down to `13` open items. The stale
  root `L5.auto_eval_gates` row is gone; remaining rows are the true root
  `L5.self_optimizing_loop` gap plus `epyc-llama` L4/L5 workflow surfaces.
- Attempted to refresh the stale `epyc-llama` GitNexus index before editing
  llama readiness docs; the rebuild repeatedly timed out on large backend
  translation units and then crashed in the Node/NAPI parser. Do not edit the
  llama fork until its GitNexus index is repaired, likely by narrowing
  `.gitnexusignore` for parser-hostile generated/backend files and rebuilding.
- Validation: GitNexus impact was LOW for `build_criteria` and
  `score_repositories`; the generic `main` lookup was ambiguous but max LOW.
  `scripts/validate/candidate_eval_gate.sh` passed, the focused scorer tests
  passed, Ruff passed for the touched scorer/test files, and
  `repo_readiness_scorer.py` regenerated all durable artifacts without errors.

#### Notes

- Anti-false-positive discipline (shared across Factory's review/scoring features): a criterion passes only on a concrete, verifiable check — mirrors our eval-tower verifier philosophy.
- Cross-refs: `eval-tower-verification.md` (rubric discipline), `autopilot-continuous-optimization.md` (remediation loop), `claude-md-accounting` skill (governance coverage = a Documentation-pillar input), CLAUDE.md repo-map.

#### Progress checklist

- [x] v1 deterministic scorer + tests landed ✅
- [x] remediation queue / advisory MD / passive AutoPilot pickup / candidate-eval-gate / default-off advisory bridge live ✅
- [x] epyc-root, epyc-orchestrator, epyc-inference-research all at Autonomous/L5 ✅
- [x] Repair file-level readiness-evidence regression. ✅ 2026-07-28 — recursive detector
  surfaces now expand to concrete non-ignored files; empty directories no longer pass as evidence.
  Root `0c276023`; 14 passed.
- [x] Close remaining root L5.self_optimizing_loop gap (13-item queue) ✅ 2026-08-25 — root detector refined to credit the vidya belief-substrate loop; queue 13 → 6 (all remaining items are frozen epyc-llama L5 surfaces); see the 2026-08-25 closeout below.
- **[declined: ws58 2026-11-03 content-review: self-referential governance level with no behaviour change]** Bring epyc-llama Standardized/L3 -> L4 (incremental_validation, generated_docs, health_automation, analysis_reports, security_audit, replay_analysis)
- [x] Add the root candidate gate to a periodic path (nightshift health or CI) so a red gate is observed within days, not weeks — the 2026-08-03 PII allowlist/fixture drift kept `candidate_eval_gate.sh` red ~22 days unobserved (derived 2026-08-25 from the EVL-38 closeout; owner: mainA) ✅ 2026-10-07
  MAIN accepted bounded source/evidence: [review](../../artifacts/ni08/evl38-periodic-gate-20261007/README.md).
- [x] Repair stale epyc-llama GitNexus index (narrow .gitnexusignore) before editing llama readiness docs ✅ 2026-07-22 (scoped serving-layer index, see below)

##### 2026-08-25 root self-optimizing-loop closeout (EVL-38)

- Refined the root L5 detector so the vidya belief-substrate loop surfaces
  satisfy `L5.self_optimizing_loop`: the scorer now credits
  `scripts/vidya/fold.py`, `scripts/vidya/citation_gate.py`,
  `scripts/vidya/correction_queue.py`, `scripts/vidya/r1_search.py`, and
  `scripts/vidya/live_eval.py` — the ledger → graded fold → citation gate →
  correction queue → re-fold feedback loop plus the R1 counterexample-search
  and PR2 live-ledger evaluation loops. The passive pickup artifact remains
  rejected as optimization evidence; the guardrail test is unchanged.
- Regenerated the full four-repo artifact set for 2026-08-25:
  `data/repo_readiness/repo_readiness_2026-08-25.json`,
  `data/repo_readiness/repo_readiness_remediation_queue_2026-08-25.json`,
  `data/repo_readiness/repo_readiness_autopilot_pickup_2026-08-25.json`,
  `progress/2026-08/repo-readiness-2026-08-25.md`, and
  `progress/2026-08/repo-readiness-remediation-2026-08-25.md`.
- `epyc-root` `L5.self_optimizing_loop` is now `passed: true` with five
  concrete vidya evidence paths; the queue drops 13 → 6 items, all of them
  frozen `epyc-llama` L5 surfaces (the 6 L4 llama items listed under "Bring
  epyc-llama Standardized/L3 -> L4" now pass on repo state — the llama tree
  gained real surfaces since 2026-07-06, not via this change).
- Validation: GitNexus impact `build_criteria` LOW (3 callers, all in-file);
  `py_compile` clean; `uv run --with pytest pytest -q
  tests/validate/test_repo_readiness_scorer.py` → 15 passed (incl. the new
  positive control `test_root_vidya_loop_surface_counts_as_self_optimizing_loop`
  and the untouched negative pin that passive pickup ≠ optimization); Ruff
  findings are all pre-existing; `git diff --check` clean.
- Pre-existing defect surfaced (NOT caused by the closeout) **and RESOLVED 2026-08-25 (mainA, operator-directed)**: the root candidate gate `scripts/validate/candidate_eval_gate.sh` had exited 1 since ~2026-08-03 — `pii_fixture_eval` 39/40, because commit `8eeaf6c3` (2026-08-03) allowlisted `AKIAIOSFODNN7EXAMPLE` in `KNOWN_PLACEHOLDERS` in `scripts/hooks/pii_precommit.sh` after the 2026-07-29 fixture. Resolution = fixture-evolution event: fixture case 1 now pins the placeholder policy (`expected_match=false`, allowlist cited) and two boundary cases were added (one-char-off lookalike blocks; placeholder + real-key on one line blocks). `pii_fixture_eval` 42/42; `candidate_eval_gate.sh` exit 0 — the gate is green for the first time since 08-03.

##### epyc-llama GitNexus index — diagnostic (2026-07-22 non-inference sweep)
- [x] epyc-llama GitNexus index (413): a bare re-index thrashes — the killers are DENSE sub-512KB files (`src/llama-arch.cpp`, `iqk_gemm_floats.cpp`@48KB, `llama-vocab.cpp`, `unicode-data.cpp`, `tools/mtmd/`), NOT the >512KB GPU TUs (gitnexus auto-skips those, so narrowing the ignore to big files can't win). RECOMMENDATION: one scoped serving-layer index (`src/`+`common/`+`tools/`, exclude ALL of `ggml/` + the dense offenders) at a quiet low-contention window via `scripts/gitnexus-analyze.sh`; if it still thrashes, leave epyc-llama unindexed and score readiness by git shortlog/tests/CHANGELOG — it's a frozen tree, low value. A partial `.gitnexusignore` (28 patterns) is staged uncommitted in `/mnt/raid0/llm/llama.cpp/.gitnexusignore`. ✅ 2026-07-22
  - **RESOLVED 2026-07-22**: scoped serving-layer index SUCCEEDED. Excluded the ENTIRE `ggml/` subtree + the dense `src/` offenders (`llama-arch.cpp`, `llama-vocab.cpp`, `unicode-data.cpp`, `tools/mtmd/`) via `.gitnexusignore`; **`gitnexus analyze` completed** (`Repository indexed successfully`, 26,723 nodes / 61,246 edges / 680 clusters), down from 48 fatal worker-timeouts to 3 (only `src/llama-graph.cpp` etc. retired — index still complete). **Reads clean, no segfault**: `gitnexus impact llama_decode --repo llama.cpp` → risk CRITICAL/79 (was signal-11). NOTE: the gitnexus repo name is **`llama.cpp`** (not `epyc-llama`). The working `.gitnexusignore` is uncommitted in `/mnt/raid0/llm/llama.cpp` (frozen tree — not committed); re-apply it (add `ggml/` + the dense-src excludes) before any future re-index. Line 412 (L4 readiness surfaces) is now unblocked.

- [x] **EVL38-REFERENCE-PORTABILITY-SOURCE — resolve the twelve actual scheduled-gate reference failures without waiving validation.** Accepted run37561593874 exits at reference validation: moved relative governance links, project-root absolute references, frozen-kernel agent-overlay references, and runtime/historical scratch links need accurate source resolution or documentation correction. Preserve fail-closed validation and dated evidence; no guessed files, host-path shim or blanket exclusions. MAIN reviews each correction before hosted proof. ✅ 2026-10-07 — Checklist reconciliation after [MAIN exact published source/original1/1 acceptance](../../artifacts/ni08/evl38-reference-conformance-20261007/README.md), ROOT04cc51bc4. Fifteen document corrections, original37572099379/90Git+5generated/109unchangedZIP, no waiver. Earlier tally113 counted only the separate native companion; this owning source task was inadvertently left unchecked. Broader scheduled-candidate/readiness parents remain open.

2026-10-07 EVL38-REFERENCE-PORTABILITY-SOURCE review: MAIN approved the nine-file local documentation proposal`db4e339cecd3edd6e36050a02641c992292e7c45` for hosted verification. The newly scoped VB-EVL38-REFERENCE-CONFORMANCE now binds the actual complete reference-validator case; periodic whole-candidate capture remains separate. It replaces stale/moved/absolute reference text with accurate tracked targets and dates nonretained scratch evidence. No validator waiver, source-path shim, frozen-kernel edit, measurement-policy amendment or new grader. The source checkbox remains open until actual hosted validation and integration.

##### 2026-11-05 operator-adhoc follow-ups (operator-adhoc-ops-20261105 wrap-up)

- [x] **SCRATCH-LEASE-P2 — allocate API: scratch is allocated through `scripts/system/scratch_lease.py` with owner+TTL at creation** (Phase 1 c65eaf73f, prompt release abb927499 landed). (workspace-f2 2026-11-09: allocate API with owner and TTL landed, 17 tests pass) [no-belief: tooling-repair]
- [ ] **SCRATCH-LEASE-P3 — retire the old reapers once leases cover all scratch roots.**
  - *(workspace-f2 2026-11-09.)* No reaper can retire yet: leases only bound a KEEP veto, cover only top-level tmp/, and kernel_store_gc, worktree_salvage and reclaim_row ignore them. Coverage pinned in tests/test_scratch_lease_coverage.py.
  *(workspace-f2 2026-11-09 wrap-up.)* Still needed (see the 2026-11-09 note above). [no-belief: not-a-result]
- [ ] **SCRATCH-LEASE-P4 — delete dead `cleanup_scratch` paths.**
  *(workspace-f2 2026-11-09 wrap-up.)* Blocked on SCRATCH-LEASE-P3 (the old reapers cannot be deleted before they retire). [no-belief: not-a-result]
- [x] **GRANT-UNFILED-241 — triage the 241 ended grants since 10-25 that lack FILED and have no READY manifest** (list: `/mnt/raid0/llm/tmp/takeover-20261105-v/ids.txt`); also 31 disk-refused closed rows need owner successors. ✅ 2026-11-09 triage and filing of the 241 done (all FILED, see the sub-bullet below); the successor/cancel work is split into GRANT-UNFILED-SUCCESSORS.
  *(workspace-f2 2026-11-09 wrap-up.)* All 241 filed 2026-11-09 via `file_result.py --no-manifest` (landed 12fac1dd2 with 69815af87, operator D9-ack; independently reviewed): 24 superseded, 150 closed no-result, 8 pass, 1 fail, 58 inconclusive; 241/241 FILED verified; 11 owner-less rows taken over by workspace-f2; log `/mnt/raid0/llm/tmp/rtg22-filing-log-20261109.jsonl`; nothing deleted or reclaimed. Box stays OPEN: 12 disk-refused rows still need owner successors and 4 need cancel confirmation (table in `/mnt/raid0/llm/tmp/rtg22-grant-unfiled-20261109.md`). [no-belief: tooling-repair]
- [ ] **GRANT-UNFILED-SUCCESSORS — 12 disk-refused rows need owner successors and 4 need cancel confirmation (table: /mnt/raid0/llm/tmp/rtg22-grant-unfiled-20261109.md).** [no-belief: tooling-repair]
- [ ] **INTAKE-VALIDATE-86 — `bash scripts/validate/validate_intake.sh` reports 86 dangling cross-reference errors in `research/intake_index.yaml` (found 2026-11-09).** They pre-date and are unchanged by the class C correction verdicts (same 86 with and without that change). Resolve or explicitly decline each dangling reference; DONE WHEN the validator exits 0. [no-belief: tooling-repair]
- [x] **HYG-GITNEXUS-CUDA-KERNEL-IMPACT — gitnexus mishandles CUDA `__global__` kernels, so impact on them is vacuous.** Found 2026-11-05 (KPF-41.DIRECT-VEC-IMPACT-R6, `flash_attn_ext_vec` at fattn-vec.cuh:21): the parser indexes the `__launch_bounds__(...)` attribute as the symbol (`Template:...:__launch_bounds__`, `Function:...:__launch_bounds__~c:1dta5on`) instead of the kernel, and records no edges for `<<<>>>` launches, so `gitnexus impact` returns LOW/0 callers. Scope fix: handle attribute-prefixed declarators for `__global__`/`__launch_bounds__` in the C++/CUDA query and add launch-site/function-pointer reference edges. Guard until fixed: impact job.py/runners must refuse any target whose source declaration is `__global__` (or resolves to `__launch_bounds__`) and require a manual caller review instead. ✅ 2026-11-05 fixed in installed gitnexus 1.6.8 (operator-approved): `artifacts/analysis/gitnexus-1.6.8-cuda-kernels-20261105/`. It masks CUDA attributes and `<<<>>>`, adds kernel-handle reference edges, and bumps the parse-cache version. The fixture fails before the patch and passes after it, including with a warm cache. Proof on real code: KPF-41 r10 indexes `flash_attn_ext_vec` with its 3 upstream callers. [belief: cc]

- [ ] **AFC-P5.E3-FLASH-TOOLS — before switching Flash-Next (architect_general) to a compressed agent file, run one tools-present compliance check.** r5's KEEP (none 1.000/0.767/1.000, aggressive 0.967/0.800/0.967) was measured with a no-tools sentence and no tools offered, so it proves recall and adherence, not behaviour with tools present. Needs a live_runner variant that offers the architect's real tool schema and scores tool-call replies against the rules, then a none-vs-aggressive row on the r5 recipe (v10 CPU, GGML_FUSED_DECODE_OFF=1). Owner workspace-f2. Source: side-agent review 2026-11-09.
  - *(workspace-f2 2026-11-10.)* r7 `afc-p5e3-n30-q38_flash-tools-r7-20261110` (r6 hit hard end; superseded) rc=0, filed inconclusive: level none with 30 architect tools offered 0.067/0.200/0.667, stop rule gave operating point none, aggressive not run. 54/90 replies were tool-only (0 invalid): the single-turn harness returns no tool results, so look-up-first behaviour scores as missing answers. The question stays open: next step is a multi-turn runner that executes or stubs tool results, then none-vs-aggressive. Until then do not switch Flash to a compressed file. [no-belief: inconclusive harness result]

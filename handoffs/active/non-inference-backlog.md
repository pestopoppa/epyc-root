# Non-Inference Backlog — Round 2 (2026-05-19 audit refresh)

**Status**: ACTIVE — rolling zero-inference backlog; closed items live in § Completed Scope. Round-2 baseline open: NIB2-18 (gated on DS-E1 evidence), NIB2-46 (gated on NIB2-32).

**Scratch**: `/mnt/raid0/llm/worktrees/codex-ni-*`, `/mnt/raid0/llm/worktrees/codex-ni05-*`, `/mnt/raid0/llm/worktrees/codex-ni06-*`, `/mnt/raid0/llm/worktrees/codex-ni07-*`; integration lane: `/mnt/raid0/llm/worktrees/codex-noninf-session-20261005`. Logs use individual writer shards. Plain custody and review roots: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/`, `/mnt/raid0/llm/tmp/codex-ni30-custody-20261006/`, `/mnt/raid0/llm/tmp/ni07-29-ci-recipe-20261006/`, `/mnt/raid0/llm/tmp/ni07-34-pii-header-preparation-20261006/`, `/mnt/raid0/llm/tmp/ni07-32-root-keep-20261006/`, `/mnt/raid0/llm/tmp/ni07-32-custody-20261006/`.

**Cross-reference, 2026-05-06**: 6 standalone non-inference handoffs (NOT in NIB2 numbering) closed in parallel via Wave A/B/C — see `progress/2026-05/2026-05-06.md` § "6 standalone non-inference handoffs". These are tracked in their own handoff files; the closure pattern matches NIB2. Total non-inference closure throughput this audit cycle: 36 NIB2 + 6 standalone = 42 items.
**Created**: 2026-02 (Round 1, 18/18 complete → [`completed/non-inference-backlog-completed-through-2026-04-12.md`](../completed/non-inference-backlog-completed-through-2026-04-12.md))
**Refreshed**: 2026-04-17 (Round 2 catalogue from cross-cutting audit of all active handoffs)
**Supplemented**: 2026-04-21 (NIB2-31..34 added from handoff hygiene audit), 2026-04-22 (NIB2-40..48 from deep-dive integration pass), 2026-05-19 (NIB2-49..52 from May 2026 research cluster deep-dives)
**Priority**: MEDIUM (as a whole; individual items tagged HIGH/MED/LOW below)

---

## Start here

- **Next:** NI05 (79/79) and selected NI06/NI07 (35/35) are complete; the whole backlog is not exhausted. [NI08 continuation](../../docs/reference/ni08-non-inference-continuation.md): 123 scoped tasks completed; LR8 and host receipt source published; newly unlocked context/source/design work continues. Preserve the running daemon until a reviewed handover.
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

- [ ] **NIB2-18**: DS-6 QuarterScheduler revalidation gate — [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) DS-6-live. Do **not** treat as code-only scaffolding. Implement only after DS-E1 evidence (Package B throughput, RI-10 escalation data, DS-5 roster findings, KV-size data, mixed-role NUMA contention) shows static pre-warm leaves material throughput/latency on the table. Completed design/gap details live in [`../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md`](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md).

## Round 2 supplement (added 2026-04-22 — deep-dive integration pass)

Items surfaced by the 8 research deep dives landed 2026-04-22 (`/workspace/research/deep-dives/{lighton, qwen35-omni, stop-learnable, diversity-collapse, onevl, agent-world, minddr, intake-trio}.md`). Each entry maps to a specific deep-dive action item and a target handoff.

- [ ] **NIB2-46**: STOP Phase 0 instrumentation in llama.cpp (DD3, intake-437). ~1d code; non-inference (hook-level). Reserve unused token, add orchestrator hook for hidden-state fetch at prefix position. **Gated on NIB2-32** difficulty-signal re-validation producing a live verdict. → [`reasoning-compression.md`](reasoning-compression.md) Action 10a.

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

- [ ] **NIB2-65** (MED): **model duplicates/orphans ~25G in `/mnt/raid0/llm/models/`** — safe set
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
- [ ] **NIB2-66** (LOW): **stale kernel trees ~18G** — `llama.cpp-experimental-preserved-20260724T135832Z`
  (14G, superseded), `llama.cpp-v6-iqk` (1.9G, iqk shipped in v9), `llama.cpp-v7-sanitize-audit`
  (1.6G), `llama.cpp-k28-prototype-20260720` (0.9G). Keep `llama.cpp-dflash2-qwen38-20260820`
  (active handoff `dflash2-block-drafter-experimental-build.md`).
  2026-09-15 PARTIAL: `llama.cpp-v6-iqk` and `llama.cpp-v7-sanitize-audit` removed (clean, fully pushed, `git worktree remove`).
  HELD: `llama.cpp-k28-prototype-20260720` (dirty: uncommitted GDN `.cu` edit + doc — commit/push or discard first);
  `llama.cpp-experimental-preserved-*` (dirty worktree of the production clone, operator-owned).
- [ ] **NIB2-67** (LOW): **`cache/huggingface` 127G** — re-downloadable HF cache, all files touched
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

- [ ] **NIB2-71** (LOW): **review `rescue/shared-clone-dirty-20260907` (`63ec9f53`) — fold or delete the
      branch.** Its content is a working copy of the CH-8 build-flags change (`162d17dd`, **already merged in
      main**) plus two older 2026-08-27 bench scripts; the residual delta over merged CH-8 is roughly **50
      comment lines** on legacy discovery scripts (build-recipe / `ROCWMMA_FATTN` notes). Decide: fold the
      comments forward, or delete the branch. Small item — the rescue itself is done, this is disposition only.

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
- [ ] **NIB2-78c** (OPTIONAL, conditional; dormant since NIB2-78b was ruled A = do not install): take this up only if
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
- [x] **LR-9** — **harness state and session transcripts are never cleanup targets** (operator hard rule 2026-10-04:
      Claude/Codex backup logs and transcripts *"should NOT BE TOUCHED UNDER ANY CIRCUMSTANCES. They are historical
      transcripts used by a root filesystem project far more senior to anything performed in this project repo"*,
      extended to every third-party harness: opencode, hermes, claude share, harness codex homes). Enforced in code:
      `codex_retention_reaper.py` apply permanently disabled (`722b7196`), and `scratch_cleanup.py` `NEVER_TOUCH`
      refuses those trees whatever a handoff declares (`722b7196`, `b639dc8e`). Written into
      `docs/guides/agent-workflows/cleanup-reference-check.md` and `docs/design/autokernel-disk-hygiene-20260915.md`.
      ✅ 2026-10-04
  - [x] **LR-9a** (operator) — **ratify the hard rule into `agents/shared/OPERATING_CONSTRAINTS.md` → *Destructive
        operations*.** That file is human-only. Prepared as
        `scripts/operator/ratify_harness_state_never_touch_20261004.sh`, with the patch
        `artifacts/operator/harness-state-never-touch-20261004.patch`. Review it with no args, then sign with `--apply --attest
        RATIFY-HARNESS-STATE-NEVER-TOUCH-20261004`.
        ✅ 2026-10-04 — signed by the operator: root `ae06680f` (OPERATING_CONSTRAINTS +10 lines, receipt
        `artifacts/operator/receipts/RATIFY-HARNESS-STATE-NEVER-TOUCH-20261004.json`). Closes OP-74.
- [ ] **LR-10** (workspace-ec) — land the orchestrator half (`lane/leak-tests-20261004`, which includes `9a2a35bf`:
      age-based eviction for the unbounded fence-kernel spec-file cache) on orch main. As of 2026-10-04 04:00Z the branch
      exists only locally and is not pushed. Close with the orch main sha.
- [ ] **LR-11** — **`codex-ni*`/`ni0X` worktrees are not cleaned up at ticket close.** 2026-10-07 disk
      audit (`/mnt/raid0/llm/tmp/disk-audit-20261007/AUDIT.md`): 207 of 606 worktrees audited were this
      lane class, left behind after their owning ticket closed — a process gap (no close-time cleanup
      hook for this lane class), not a one-off. The 2026-10-07 crisis itself (562 worktrees / 414 GiB,
      tmp 255 GiB, free fell to 86 GiB, blocking a DS41 lane relaunch) was resolved: operator ran
      `/mnt/raid0/llm/tmp/disk-audit-20261007/delete_safe.sh`, free disk is now 175 GiB. This box is the
      remaining structural fix — a cleanup step at ticket/PR close for the `codex-ni*`/`ni0X` lane class,
      analogous to `LR-2`'s wrap-up-time sweep but triggered at close rather than at wrap-up.
- [ ] **LR-12** — **`scripts/hooks/agents_reference_guard.sh` resolves markdown refs against the wrong
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
      §8 and §9.4 for the exact patch text.
- [ ] **LR-13** — land three subagent-brief/wrap-up memory rules adopted 2026-10-07 into
      `agents/shared/SESSION_LIFECYCLE.md` (wrap-up cadence section) or
      `agents/shared/OPERATING_CONSTRAINTS.md` (subagent brief section), whichever already hosts the
      nearest-matching text — not yet checked for duplication: (1) per-task wrap-up includes the
      task's own scratch cleanup (generalizes the existing disk-crisis lesson); (2) every subagent
      brief requires logs, progress and handoff updates for its own work, then clearing its own
      scratch **only if no longer needed**; (3) the main thread, not the subagent, decides scratch
      lifetime per brief. Same `LR-12` guard defect blocks editing these files from a lane ahead of
      `/workspace` — land LR-12 first or edit once `/workspace` has caught up.

## 2026-09-27 compaction — orphaned residuals boxed

Both residuals below sat inside closed items and had no box of their own, so the compaction gave them one before
moving their parents to the completed ledger.

- [ ] **NIB2-88** (LOW, operator/owning session): **add the opencode event reaper to the post-reboot checklist.** From
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
- [ ] **NIB2-89** (LOW): **generalise the bus supervisor's H-4 self-restart to every registered daemon.** From NIB2-81
      (✅ 2026-09-23): remedy (a) (`daemon_provenance.sh`) and remedy (b) (the registry `runtime` field, the
      `observer_census.py --live` census and the `restart_on_stale` path) landed. Its own "Remaining" line also
      named the H-4 generalisation: each daemon publishes its `source_tree`, and one supervisor tick restarts a divergent
      one. The code is under `scripts/coordination/**`, so landing it needs a D9 ack. It has no runtime effect while
      bus_supervisor stays DOWN (operator ruling 2026-09-23). Absolute-path launch recipes and host-cron `once` ticks
      remain an operator decision (OP-9/FW-3). Zero inference.

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
  ([`fuzzy-workflow-authoring-gui.md`](fuzzy-workflow-authoring-gui.md) § FW-1 sketch, finding F-1).
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

Next non-inference candidates, ordered for the next dispatch (existing task identities; these are not completed):

1. **HG-9 Step 1 topology map** — map existing finding/routing contracts to detector and fixer roles, the emitted-finding trigger and deterministic failure fallback. Reuse existing escalation plus typed-decision/PreparedAction contracts; no selector activation, model calls or AutoPilot policy change. [Owning handoff](reviewer-escalation-and-human-gate-policy.md).
2. **K2 internal KB cap plumbing** — replace remaining hard-coded query/document caps with declared helpers while retaining stored catalog identity as authoritative. Synthetic declared/absent/invalid configuration checks; no re-embedding or OP-24 cap transition. [Owning handoff](internal-kb-rag.md#s04-f2--narrow-k2-to-the-remaining-hard-coded-internal-kb-caps).
3. **VB-KB-CATALOG-IDENTITY** — capture catalog identity at its transactional write boundary as dependency evidence; legacy absence remains unknown. [Owning handoff](vidya-belief-substrate-program.md).
4. **TU-GR-1 isolation specification** — prepare mount/UID/export and synthetic access-denial acceptance contracts with the existing scoring-infrastructure owner. Actual sandbox mechanism/integration crosses a HIGH trust boundary and remains a separate owner/operator decision; no competing sandbox or isolation claim from mocks. [Owning handoff](tool-use-eval-contract.md).

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

- [ ] **DISK-ARCHIVE-FIRST — archive then remove the ARCHIVE-FIRST disk items.** Owner: workspace-ec. (filed 2026-10-07) `tmp/ds41-specdec-recipe` 4.4G and `copy-spec-eval-20261006` 1.8G (inventory `artifacts/ec-wrapup-20261007/ec-disk-inventory-20261007.md`). Done when recipe/evidence are in git or artifacts and the operator confirms deletion.

- [x] **NI08-WIKI-WARNING — limit the linked-worktree mtime warning to explicit --since scans.** ✅ 2026-10-07 — MAIN reviewed the single CLI caller and diagnostic-only fix. Default incremental selection remains content-hash based; watermark behavior is unchanged. Actual default and explicit-date governance scans are checked during this operator-requested full checkpoint.

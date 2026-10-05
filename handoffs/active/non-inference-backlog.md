# Non-Inference Backlog — Round 2 (2026-05-19 audit refresh)

**Status**: ACTIVE — rolling zero-inference backlog; closed items live in § Completed Scope. Round-2 baseline open: NIB2-18 (gated on DS-E1 evidence), NIB2-46 (gated on NIB2-32).

**Cross-reference, 2026-05-06**: 6 standalone non-inference handoffs (NOT in NIB2 numbering) closed in parallel via Wave A/B/C — see `progress/2026-05/2026-05-06.md` § "6 standalone non-inference handoffs". These are tracked in their own handoff files; the closure pattern matches NIB2. Total non-inference closure throughput this audit cycle: 36 NIB2 + 6 standalone = 42 items.
**Created**: 2026-02 (Round 1, 18/18 complete → [`completed/non-inference-backlog-completed-through-2026-04-12.md`](../completed/non-inference-backlog-completed-through-2026-04-12.md))
**Refreshed**: 2026-04-17 (Round 2 catalogue from cross-cutting audit of all active handoffs)
**Supplemented**: 2026-04-21 (NIB2-31..34 added from handoff hygiene audit), 2026-04-22 (NIB2-40..48 from deep-dive integration pass), 2026-05-19 (NIB2-49..52 from May 2026 research cluster deep-dives)
**Priority**: MEDIUM (as a whole; individual items tagged HIGH/MED/LOW below)

---

## Start here

- **Next:** NI05-18 exception classification, NI05-38 scoring custody and NI05-41/43/44 offline follow-ons.
- **Then:** NIB2-85, NIB2-86 (`make gates`; filed as NIB2-80), NIB2-73e, NIB2-77, NIB2-83.
- **Operator-held:** NIB2-65, NIB2-66, NIB2-73f.
- **Also open:** NIB2-18 and NIB2-46 (gated), NIB2-67 (reclaim only under disk pressure), NIB2-71, NIB2-76, NIB2-78c
  (dormant), NIB2-80a, NIB2-82, NIB2-87 (filed as NIB2-81), NIB2-88, NIB2-89, NIB2-90, OBS-9, OBS-10.
- **Leak robustness (2026-10-04 supplement):** LR-6a is operator-held (LR-9a ratified 2026-10-04, `ae06680f`). LR-8 follows LR-6a. LR-10 belongs to workspace-ec.
- **Standing:** bus_supervisor stays DOWN (operator ruling 2026-09-23). Do not relaunch it without a new operator go.


## Codex session queue — 2026-10-05

Operator scope: finish the available non-inference work identified in the 2026-10-05 overview,
starting with the first twelve items and extending the queue as dependencies clear. Canonical task
bodies remain authoritative; this queue records the session's bounded deliverables. Implementation
is delegated, acceptance and publishing belong to Codex main. Each completed item receives its own
progress record and source-handoff checkbox update after review. Shared indices, wiki integration
and promotion are serialized by main. No inference grants, production mutations or ratifications.

**Scratch**: `/mnt/raid0/llm/worktrees/codex-ni-*`, `/mnt/raid0/llm/worktrees/codex-ni05-*`; integration lane:
`/mnt/raid0/llm/worktrees/codex-noninf-session-20261005`. Logs use individual writer shards.
Local test/build execution acquires the existing CPU-region claim and may queue behind Claude work.
Hermetic fixtures also run on isolated GitHub Actions runners against immutable candidate commits;
host-dependent checks remain explicitly separate. Published completion tally: **39/44**. The remaining items keep their narrower source, fixture,
and host-dependent acceptance boundaries explicit.

- [x] **NI05-01** — VB-KVQ-V10-DICT: native-statistics adapter/producer fixture compatibility.
- [x] **NI05-02** — VB-INGEST-IDEMPOTENT: opt-in repeat-ingest no-op and partial-state refusal.
- [x] **NI05-03** — NIB2-86: honest local validation gates and missing-tool failures.
- [x] **NI05-04** — NIB2-73e: docs/handoff evidence durability checks.
- [x] **NI05-05** — HS-OD-8: retryable admission refusals before streaming.
- [x] **NI05-06** — HS-17: MCP timeout and progress contract.
- [x] **NI05-07** — SSU-F9c: shared promotion lease across worktrees.
- [x] **NI05-08** — REPL-EMB-4.5: expire temporary experiment flag enables.
- [x] **NI05-09** — VB-APPLICABILITY: conditional native applicability/run scope in ledger.
- [x] **NI05-10** — HSF-3 + VB-GAP-DIST: write-side capture and existing-log gap analysis.
- [x] **NI05-11** — NIB2-90 + scoring-infra 1e: test-order leakage and benchmark collection defects.
- [x] **NI05-12** — NIB2-87: additive research test dependency and tooling health check.
- [x] **NI05-13** — VB-NI-DURABILITY: newly unlocked native durability receipts and verifier projection.
- [x] **NI05-14** — HS-16 lifecycle remainder: explicit session-end signal and existing TTL semantics.
- [x] **NI05-15** — VB-CI-CONFORMANCE: prospective native off-host fixture receipts and verifier projection.
- [x] **NI05-16** — explicit kernel-path overrides: avoid eager production-store discovery during configuration import.
- [x] **NI05-17** — HS-OD-5: reject unsupported explicit sampling controls on image requests.
- [ ] **NI05-18** — SSU-F13: verify upstream topology fixes and classify the required wider unit sweep.
- [x] **NI05-19** — HS-OD-6: refuse direct-mode tool instructions without an executor; preserve client tools.
- [x] **NI05-20** — dependency contract: bound pydantic-graph to the supported constructor major or use the authoritative frozen lock for installation; validate actual fresh-import and API fixtures.
- [x] **NI05-21** — static gate debt: review and apply the nine shfmt formatting repairs with shell syntax/AST checks; capture and repair the independent markdownlint findings without weakening gates.
- [x] **NI05-22** — TU-TC-1a: keep malformed tool-call refusal echoes out of loop progress detection; retain diagnostic text and genuine executable progress.
- [x] **NI05-23** — VB-CI-CONFORMANCE-ATTACHMENTS: retain and verify declared generated artifact bytes through the existing prospective fixture receipt, preserving its sole decided proposition.
- [x] **NI05-24** — NI-SHELL-RELOAD-SAFETY: make the instrumented benchmark preflight refuse an unavailable API without killing or restarting peer processes.
- [x] **NI05-25** — VB-CI-CONFORMANCE-API-WIRING: prospectively capture named API and explicit synthetic-host unit commands through the existing native producer.
- [x] **NI05-26** — NI-OFFLINE-CPU-CLI: make two leaf command modules honor explicit binary paths before resolving production-store defaults.
- [x] **NI05-27** — NIB2-82: replace the name-pattern AutoPilot observer with exact process argv inspection and refuse authority writes when observation is unavailable.
- [x] **NI05-28** — NIB2-85: validate the upstream canonical-linkage repair plus actual `/bin/true` vacuity control; bind future read-only production-store checks before execution.
- [x] **NI05-29** — VB-CI-PREFIX-DURABILITY: retain native phase prefixes immediately and time-bound broad unit attempts so timeout cannot erase completed evidence.
- [x] **NI05-30** — NIB2-80a: apply escalation budget and role-cycle admission to immediate early-abort branches in the active graph modes, with actual route fixtures.
- [x] **NI05-31** — NI-CI-FIXTURE-CUSTODY: correct privacy-gate false positives for exact synthetic input fixtures while preserving native bytes and genuine-secret refusal.

- [x] **NI05-32** — HSF-3 schema boundaries: synthetic tap/progress/checkpoint coverage controls without inferred enqueue/class joins.
- [x] **NI05-33** — OBS-12a: remove active explicit system-Python bus invocations; honor the existing managed-venv shebang.
- [x] **NI05-34** — VB-PII-STAGED-WIRE: prospective private original-index custody and bounded actual privacy-gate receipt.

- [x] **NI05-35** — VB-MANAGED-TOOLING-WIRE: prospective named managed-import custody; preserve original plain NI12 evidence.
- [x] **NI05-36** — DCP-13a/b: remove unreachable report-fetch instructions and return full reports on delegation-cache hits; retain separate inference-dependent DCP-13 arms.

- [x] **NI05-37** — TU-TM-1: typed native timeout outcomes, finished/timeout/overall denominators and prospective immutable report-integrity custody; deterministic transport/stub fixtures only.

- [ ] **NI05-38** — DCP-10-SCORE-PREP: deterministic offline macro/path/span/post-pack scorer plus prospective immutable scored-report custody; full ContextBench benchmark remains separate.

- [x] **NI05-39** ✅ 2026-10-05 — SSU-FIXTURE-KVSLOTS: targeted pure launch-command fixtures with runner-only owned cache-directory preparation; preserve original failures and independent native captures.

- [x] **NI05-40** ✅ 2026-10-05 — SSU-FIXTURE-REPL-SPILL: rerun the unchanged spill-output module with the already reviewed runner scratch fixture; preserve original nine failures.

- [ ] **NI05-41** — SSU-SCORING-EXTRA: declare and lock the optional mathematical scorer dependency, then rerun three offline modules and their missing-dependency refusal controls; exact source/recipe review precedes execution.

- [x] **NI05-42** ✅ 2026-10-05 — SSU-GRAPH-FIXTURES: validate named temporary-DB graph modules with the existing locked optional graph extra; no live graph, model or dataset access.

- [ ] **NI05-43** — SSU-FIXTURE-REPL-FILESYSTEM: named optional captures of two otherwise skipped pure filesystem modules with disposable owned roots; source default skip guards remain.

- [ ] **NI05-44** — OBS-9: require qualified existing authoritative probe evidence in three surviving leaf idle prefilters; unknown/read failures/drift suppress action, no text-derived idle authority or liveness-core mutation.

Follow-on pool: DCP-13a/b; DCP-10 offline scoring; SSU-F13; HS-OD-4/5/6; tool-use grader
isolation, negative fixtures, timeout/failure reporting, TU-TC-1a and TU-HR-1; observer residuals;
NIB2-80a/83; bounded static kernel preparation; KB fixture/pin preparation; existing-trace UTM
integration; harness pin/card/source audit; typed-decision offline adapters and workflow plans.
Claim these only after checking their current canonical task and peer ownership. OAB-29–32 and
AutoKernel/KV-prefix producers remain with the active Claude owner until an explicit task boundary
allows division. RTG-58, UFH14-B4/LR-10, STACKCHG8083 deployment and the coordination audit are
already owned by the two Claude sessions. Frozen routing changes remain frozen. Harness transcripts
and history are never cleanup candidates. Newly unlocked tasks are filed in their owning handoff,
linked through its single domain index, then added here for dispatch.

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
- [ ] **OBS-9** (LOW): **`"esc to interrupt"` is a liveness oracle in FOUR files with no shared
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

- [ ] **OBS-10** (LOW): **Two E8 operator ratifiers gate on an argv pattern.**
  *Note 2026-09-16: the E8 chain these ratifiers served is retired by operator ruling [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json) (root `1ee8bd7c`). The ruling re-anchors the reseed gate to the current eras; the gate binds only at promotion.*
  `artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh` and
  `ratify_e8_empty_frontier_bootstrap_20260726.sh` both use
  `pgrep -f '[s]cripts/autopilot/autopilot.py start'` — same start-adjacency fragility. The newer
  `ratify_v9_cpu_bench_era_advance_20260811.sh` already migrated ("no process-pattern probe — host
  rule: never pgrep by name"); backport that. Deliberately OUT of the observer-registry discovery
  scope (one-shot scripts a human runs and reads once), recorded here so the finding is not lost.

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
- [ ] **NIB2-73f** (LOW, operator): **the operator's own email address is in a tracked file** —
      `data/cpu_optimization/2026-04-30-v5-cleanup-audit/README.md:27`, attributing his own decisions. First-party, so
      the third-party-PII WITHHELD precedent does not apply and nothing was changed. Redact or keep: an operator call,
      relevant only if this repo ever becomes public.
- [ ] **NIB2-76** (LOW): **two residuals of the NIB2-69 gate fix.** (a) standalone `scripts/registry/stack_change_guard.py`
      still resolves the NUMA mode fleet→env→`full`, the exact mismatch NIB2-69 removed from `check`; (b) the priors'
      `source_artifacts` hold absolute main-clone paths, so a `check` run in a worktree verifies the MAIN clone's
      files rather than its own — location-dependent by construction.
- [ ] **NIB2-77** (MED): **finish AutoKernel disk hygiene after the approved sweep and archive-backed retirement.**
      The exact `a49053c273ee` manifest's prequalified REMOVE rows were approved and applied. A separate
      content-addressed archive preserved all 224 reviewed dirty acceptance worktrees before their exact-path
      retirement; 224/224 have removal receipts. Free space rose by 359,176,167,424 bytes (about 334.5 GiB).
      Prospective acceptance cleanup and serial disk fail-close are published (`b65138a0` root;
      `142fd1e3` research). The **187 lane worktrees registered against the frozen clone remain untouched**;
      audit their ownership and migrate/retire only through an individually reviewed procedure. Verify the
      prospective cleanup during the next completed acceptance run, rather than inferring it from unit tests.
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
      grower ranking. ✅ 2026-10-04 (root `913585ff`). It is **inactive until LR-6a**.
  - [ ] **LR-6a** (operator, host-only) — **re-pin the host supervision cron.** The host crontab runs a pinned copy of
        `hub_supervisor.sh` (OP-9 option B), so the tick goes live only after
        `bash scripts/operator/install_supervision_cron_20260916.sh --all` runs **on the host**. It cannot run from the
        container: attempted 2026-10-04 and failed. Operator queue row prepared. Close it with a `host_hygiene_tick`
        heartbeat line in its log after the re-pin.
- [x] **LR-7** — the DS41 load-bearing worktrees are declared with git locks: `root-main-epyc-root-repo` and
      `research-ds41-run10`. ✅ 2026-10-04 (INF-77 DS41-C113a)
- [ ] **LR-8** — **merge the periodic cleanups into one tick, after LR-6a.** The standalone
      `opencode_event_reaper.sh` daemon and the report-only `codex_retention_reaper.py` run each become a
      `host_hygiene_tick.py` duty, so there is one scheduler, one heartbeat and one alarm channel. The keeper already
      relaunches the reaper (NIB2-88). Keep the reaper's scope exactly as approved: opencode's `event` table in idle
      sessions only. Deferred until LR-6a, because until then the tick does not run at all.
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

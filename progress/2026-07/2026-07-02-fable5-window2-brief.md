# 2026-07-02 — Fable 5 window-2 brief: reconstruction, refinement, launch-prep

**Session type:** Planning / meta — no production code changed. Authored the entry brief for the next
`claude-fable-5` one-shot architecture consult ("window-2").

## Context
The operator has another precious, ephemeral Fable 5 window and wanted to: (a) recall how the
2026-06-12 window ("window-1") was run, (b) assess whether it delivered, (c) compare a new draft
prompt they'd written against the proven brief, and (d) produce a refined, launch-ready brief.

## What was done

**1. Reconstructed window-1 (2026-06-12)** via 3 parallel Explore agents:
- **Original prompt** = `handoffs/completed/fable5-architecture-review.md` — a North-Star + our-own
  "where we're stuck" dossier + refute-our-framing + negative-space brief, run as a **full Claude Code
  agent** (GitNexus-first + 5–7 parallel subagents), review-only *mandate* but full tools; effort
  xhigh/max; never echo reasoning; preflight self-audit; 2.5 h cap.
- **Deliverables** = ~500 KB / 17 files; reframed the 4 problems into one binding-constraint thesis
  ("decision-grade evidence"); every claim `file:line`-grounded; **most proposals were subsequently
  built**; its `MEASUREMENT.md` was adopted as the instrument constitution.
- **Reception** = major success (~17 handoffs spawned, several complete). Caveats to design against:
  not turn-key (needed 4+ operator-requested depth passes); one falsifiable prediction failed
  (`task_rate ≥2/5`); one "cheap" step silently blocked (α tokenizer mismatch, still unmeasured);
  density hurt scannability.

**2. Assessed the operator's new draft prompt** — a solid *generic* strategic-planning template but a
regression for this model+project: paste-in/no-tools vehicle (discards GitNexus + subagent
grounding), rigid "respond exactly like this" template (over-prescription measurably reduces Fable
output quality per our doctrine), demotes the "refute our framing" ask, generic categories. Kept its 3
good instincts: front-loaded acceptance criteria, scannable index-first output, state-assumptions.

**3. Authored the refined window-2 brief** = `handoffs/active/fable5-architecture-review-2.md`. Keeps
the proven recipe, refreshes the substrate, re-aims focus. Iterated with the operator through several
hardening passes:
- **Co-lead 4A** — self-optimizer integrity: reframed to "review what we built (evidence plane live;
  W6 clear; W7 game layer shipped) + the one held-open question (W5 `core_v2` no-go: mis-specified
  objective or mis-built instrument?)"; **self-deprioritizing** because the subsystem is being actively
  ground by a parallel codex agent + autopilot right now.
- **Co-lead 4B** — MI210 heterogeneous CPU+GPU serving: hands Fable the operator's
  `/mnt/raid0/llm/epyc-root/tmp/epyc_mi210_hybrid_inference_handoff.md` (A/B/C families) as *"current
  thinking to criticize, not a spec"*; asks for multiple options + Fable's own + the decisive
  measurement (α first).
- **Cross-cutting** — targeted resurrection sweep (GPU/evidence-plane reopen-criteria) + a **standing,
  unprompted** index-driven portfolio audit + reprioritization (baked into the mandate so no
  mid-session reminder is needed).
- **Guardrails** — validate every falsifiable claim with the cheapest decisive experiment; flag
  unverified "cheap" assumptions; measurement discipline; closing self-critique.

**4. Preflight verification against the live tree** — corrected a **stale claim** (W6 gaming alarm is
**clear**, not firing; W7 game-layer shipped); confirmed MI210/ROCm 6.2 in devcontainer, evidence-plane
live (`AUTOPILOT_SEQ_VERDICT=1`), α still unmeasured, W5 `core_v2` no-go (33/40). Brief is lean
(~3.7 K tokens); no prompt anti-patterns.

**5. gitnexus readiness** — v1.6.8; epyc-root / epyc-orchestrator / epyc-inference-research registered,
queryable, and self-healing via a live post-commit re-analyze (orchestrator's transient stale +
KuzuDB-replay-error window healed on its own). `llama.cpp` is unregistered (on-disk index stale from
2026-06-19) → brief treats the fork as **raw-file-only** with absolute-path fallback.

**6. Fixed 6 operator review findings** — broken chat-only bundle claim; explicit gitnexus fallback;
absolute paths for the N5 harness + MI210 handoff; bounded the portfolio-audit scope (index-driven +
targeted sweep, not a 349-file / 106k-line read); strict write authority (subagents read-only, index
restructure is a *proposed* artifact); committed the previously-untracked brief.

**7. Updated doctrine memory** `feedback_fable5_godtier_architect_use` with 8 brief-authoring mechanics
(absolute paths, show-our-draft-as-criticizable, standing deliverables, bound-the-audit, read-only
subagents, don't-aim-at-active-grind, gitnexus-volatility/raw-file-fallback, live-tree preflight).

## Artifacts

| Artifact | Path | Status |
|---|---|---|
| Refined window-2 brief | `handoffs/active/fable5-architecture-review-2.md` | Committed `0c3aed23`, launch-ready |
| Doctrine memory update | `~/.claude/…/memory/feedback_fable5_godtier_architect_use.md` | Updated (config volume, not a repo) |
| Session plan | `~/.claude/plans/…mossy-gizmo.md` | Approved (not a repo artifact) |
| This progress log | `progress/2026-07/2026-07-02-fable5-window2-brief.md` | New |

## Results
The window-2 brief is committed and launch-ready. Defaults baked in, tunable at launch: **vehicle** =
full agent + GitNexus; **emphasis** = MI210-led (via 4A's self-deprioritize); **depth** = insight +
build-seeds. gitnexus verified ready for the 3 registered repos; llama.cpp raw-file-only by design.

## Deferred / next
- **Operator to launch the window** (human launch gate) — `handoffs/active/fable5-architecture-review-2.md`.
- Optional: reindex `llama.cpp` to HEAD for `--repo llama.cpp` graph access — heavy; run with autopilot
  paused. Otherwise raw-file-only is the intended lens for kernel/ROCm/HIP work.
- **No master-index row added** — following the window-1 precedent (Fable consults are a standing
  reference, not an open queue row) and deliberately avoiding contention with the parallel codex agent
  actively editing the indices. Discoverability is via `handoffs/active/` + this log.
- **Wiki compile deferred** — the source scanner shows new sources, but they are from the parallel
  autopilot / MI210 / deepseek-v4-flash work (still in progress), not this session. Recommend a
  dedicated wiki-compile session (as was done after window-1). `.last_compile` left untouched.

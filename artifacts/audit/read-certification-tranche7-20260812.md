# Read-Certification Tranche 7 (tail) — 2026-08-12

**Certifier**: auditor (1 subagent, adjudicated; both load-bearing claims spot-checked on the
main thread). **Scope**: the 8 small tail files, 13 open rows. **Result: 6 LIVE / 6 GATED
(4 operator, 2 inference, predecessors overlapping) / 1 REWRITE / 0 DEAD.** The tail is clean —
these files are recently-touched with well-maintained gates; `wp12:240` even ran the
recurrence check on itself correctly in-file (re-verified its own gate three ways and declined
to restart, 2026-08-11).

**Cumulative T4–T7: 389 rows certified, ~42% of the ~918 backlog; blended dead-rate 24%.**
Certification of non-live-owner files is COMPLETE — remaining uncertified surface is
`session-bus-thin-dispatcher.md` and `autokernel-research-loop.md` (live-owner, by policy)
plus whatever the queue regenerates post-merge.

## Elevated finding

**HS-OD-1 is a LIVE unfixed defect** (`harness-selection-and-integration.md:252`): standard
OpenAI body fields (`response_format`, …) are silently dropped by the API — spot-verified:
zero `response_format` hits in `epyc-orchestrator/src/api/`. Confirmed deliberately-untouched
by the HS-OD-2 closure note. Dispatchable code fix, orchestrator-correctness lane.

## Verdicts (roster)

LIVE: agent-collab:44 (OpenHyra adapter spike), tool-use-eval:370 (DTAP import) + :379
(negative-case fixtures), harness-selection:158 (HS-9 probe) + :252 (HS-OD-1, above),
agent-world:299 (AW-7 dataset pull, file's own "no-blocker"). GATED-operator:
agent-collab:43, afc-prose:14 (explicit operator HELD, smoke-only verified), wp12:240,
harness-selection:41 (HS-4, the decision gate everything closed into). GATED-inference:
agent-world:298 (AW-6 48h run), :300 (AW-8 ~50-100 wall-hr), :302 (dual, + gfx90a
GRPO-viability unverified). GATED-predecessor: afc-prose:26, yarn:105 (external product-need
trigger), agent-world:301 (weights unreleased). REWRITE: x-mas:51 — the row's "post-enable
monitor" premise is superseded by the file's own header correction (mode rolled back to
shadow 07-16, verified live in `classifier_config.yaml` + commit `e82fbbc1`); box correctly
stays open awaiting a future verified enforce interval. Same-file hits: 3 (wp12's in-body
recurrence note; x-mas header supersession; HS-OD-2's deliberate-untouched confirmation).

# 2026-08-22 — Research intake: terse pilot deployed · fleet made whole · E-7 recal running

Per-agent shard, continuing the 2026-08-21 campaign (see that shard for the intake + measurements).

## Pilot deployment (operator: "wire it up" + "architect_general also please")

Three-agent fan-out: (1) root-cause — the launcher NEVER reads ORCHESTRATOR_STACK_NUMA_MODE; argv
only, cold-start fallback hardcoded "quarter" (Q38-T6 filed); (2) plumbing —
`server_mode.<role>.chat_template_file` → compiler → data-driven emitter + attestation entry +
parity tests; (3) wiring — artifacts installed immutable at /mnt/raid0/llm/models/chat-templates/,
master-registry pilot blocks (frontdoor CT-1b-measured; architect_general operator-directed with
UNMEASURED-on-model caveat; coder_escalation inherits).

**Two defects found and fixed en route:** (a) the additive-promotion gate deadlocks (realized-mode
view can't see "both" until the fulls are up — mirror of the morning's clean-shell artifact); dodged
via gate-free per-server reloads. (b) `reload server_<port>` matched NO dispatch branch, restarted
nothing, returned 0 — silent vacuous success (the reason the halves "reloaded" without the flag);
fixed with manifest-table addressability + exit 1 on unknown components + full/half flag-parity test.

**End state:** all three fulls up (:8070/:8072/:8085 — the 80B needed one retry past an mlock-limit
transient; 281 GB locked fleet-wide, capacity edge noted); terse pilot render-verified on ALL THREE
frontdoor instances + :8083; architect answers "capital of France" in 2 tokens; stack-change check
**FULLY GREEN including runtime attestation** (declared == compiled == live cmdlines) — first time.
API reloaded.

## E-7 recalibration (operator-directed)

Running against the LIVE servers: 380 questions, frontdoor (CT-1 pinned ids for pre/post
comparability) + architect_general (160 + CT-5's 60 gpqa_diamond_cot), production posture, stamps
(model, quant, v9, template 1443ea9ab4bb). /workspace/tmp/e7-recal/.

## Commits
- epyc-orchestrator `34ff6fcc`: plumbing + reload fix + regenerated artifacts (pushed)
- epyc-inference-research `b9ba66e6`: pilot registry blocks (pushed)
- epyc-root: this shard + handoff flips — committed at the E-7 boundary

**Design miss, operator-caught:** the E-7 runner ran its two role arms SEQUENTIALLY (a bare loop)
despite CPU+GPU concurrency being ratified doctrine and used earlier the same day — cost ~30 min
wall-clock. Runner-template rule going forward: role arms on disjoint compute planes run in
parallel (threads), each with its own incremental JSONL; the belief-sidecar emit joins at the end.

---

## Session close — E-7 stamped, belief-gated, and the CoT cell redeemed

**E-7 stamps** (live production path, `(model, quant, v9, template 1443ea9ab4bb)`): frontdoor
82.5/37.5/55.0/32.5% (math/mmlu/gpqa/crux) — CT-1b REPRODUCED live; architect_general first-ever
stamps 85.0/27.5/47.5/22.5%, zero errors. **gpqa_diamond_cot voided at maxtok 900 by this
session's own finish_reason rule** (48/60 truncated — the same budget trap, self-inflicted this
time); 4096 rerun: **75.0% (45/60)**, ABOVE the embedded template's 70.0% CT-5 baseline on the
same pinned ids. All 9 valid cells emitted as producer-authored belief rows grading
**Witnessed/Attested, empty reasons** — the program's first decision-gating measurements, wired
same-day through the new chat_template_ab adapter.

**Also closed this pass:** CT-8/SC46 (adapter built + wired, 16 tests + conformance green); the
full wiki sweep (14 foreign sources → 10 pages, 6 contradictions reconciled, pending 0); CT-E7b
filed (registry quality-row propagation, deliberately fresh-session). Two design misses owned in
the record: sequential role arms (~30 min) and the 900-cap on a CoT suite.

**Session totals (2026-08-21→22):** one operator URL became — 6 dived intake entries; the
four-plane registry discovery + swap completion + first fully-green check; an injection-free
EPYC-owned template built, validated, measured (4 campaigns, ~1,300 scored generations), and
DEPLOYED to production on 3 roles; 4 launcher/lifecycle defects found (2 fixed, 2 filed); the
belief-kernel write side wired with the template axis; and every claim either measured,
graded, or explicitly voided by its own rules.

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

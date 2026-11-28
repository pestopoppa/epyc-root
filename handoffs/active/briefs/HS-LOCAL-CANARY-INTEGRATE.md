---
schema: epyc.brief.v1
id: HS-LOCAL-CANARY-INTEGRATE
box_text_sha: t:781e09390f501afc
author: planning
written: '2026-11-28'
accepted: auto
where:
- epyc-root:scripts/coordination/taskflow/harness/local_llm.py
- epyc-root:scripts/coordination/taskflow/harness/opencode_derived/sandbox.py@06b010e1361768b7d1d65b83cb4428df28a0d1c3
- epyc-root:docs/reports/autopilot-w66-cpu-quality-q012.md
approach: 'Diff the evidence-branch full-tools candidate against current main before selecting changes. Exercise the ordinary
  dispatcher entry point and its private sandbox, including original and new callers. Port the CPU diagnostic fixes for Git
  grep threads under PID limits and wrapped, unwrapped and empty interrupt acknowledgements, preserving error propagation
  and quiescent session export. Keep syntax execution available with actionable results. Bind effective caps, model/template,
  kernel and loaded libraries, tool catalogue, session identity, immutable original and patch, cancellations and late receipts.
  Replay strong acceptance and negative assertion controls, including a paid-review false positive. This work integrates the
  tested candidate into the canonical harness. A successful sandbox experiment alone is insufficient to claim default deployment.
  Preserve frozen historical sources and create fresh normal-entry receipts.

  '
acceptance: normal Taskflow dispatch and same-session timeout controls use the integrated profile, default tools and deterministic
  execution-error feedback work, grep thread headroom and all interrupt acknowledgement shapes pass, old callers remain compatible,
  and source/build/session provenance is captured.
non_goals: []
tier: local
grounded:
  at: '2026-11-28'
  blobs:
    epyc-root:scripts/coordination/taskflow/harness/local_llm.py: e3448da6b96e809ca89ed45e6487ec11c4a8bf95
    epyc-root:scripts/coordination/taskflow/harness/opencode_derived/sandbox.py@06b010e1361768b7d1d65b83cb4428df28a0d1c3: ac3268e1ff38977c8b1a8d938beee4ec89e9894f
    epyc-root:docs/reports/autopilot-w66-cpu-quality-q012.md: 82d191111d024a9fb5c274cdfb70719691055437
---

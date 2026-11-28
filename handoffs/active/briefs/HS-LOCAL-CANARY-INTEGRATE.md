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
  Preserve frozen historical sources and create fresh normal-entry receipts. Integrate supported-template preservation ON
  by default through worker, reviewer, continuation and launch paths, including thinking OFF. Keep explicit experimental overrides.
  Verify the actual outgoing request and rendered-prefix controls through the normal entry point. The highest-ROI deliverable
  is a usable canonical local-dispatch path with local acceptance before paid escalation. Preservation defaults are now implemented
  in canonical Taskflow worker/reviewer, orchestrator JSON/SSE and launch environment, research master/lean host rows and
  active recipes. Reuse them while integrating the full-tools candidate. Its frozen transport Handler.prepare historically
  strips the preservation kwargs unless preserve_resume is enabled, and its guard ties that field to thinking ON. Integration
  must preserve the operator default with thinking OFF and retain explicit A/B overrides, using a regression at the actual
  proxy output. Historical experimental sources stay frozen.

  '
acceptance: normal Taskflow dispatch uses the qualified tool and preservation defaults, deterministic local checks precede
  paid escalation, minimal sanitized escalation packets preserve privacy boundaries, timeout/grep controls pass, and old callers
  remain compatible.
non_goals: []
tier: local
grounded:
  at: '2026-11-28'
  blobs:
    epyc-root:scripts/coordination/taskflow/harness/local_llm.py: 2f574d27898aa7641cbd7db3e19d4b1e0dce1c73
    epyc-root:scripts/coordination/taskflow/harness/opencode_derived/sandbox.py@06b010e1361768b7d1d65b83cb4428df28a0d1c3: ac3268e1ff38977c8b1a8d938beee4ec89e9894f
    epyc-root:docs/reports/autopilot-w66-cpu-quality-q012.md: 82d191111d024a9fb5c274cdfb70719691055437
---

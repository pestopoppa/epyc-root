# Cluster A — Edit Pass Report

## Files modified

- `/workspace/repos/epyc-orchestrator/docs/chapters/02-orchestration-architecture.md` — 9 edits applied
  - Tier A frontdoor model line + ASCII block updated to Qwen3.6-35B-A3B Q8 @ 24.3 t/s aggregate
  - Tier B table replaced (B1: Qwen3.6-35B Q8 shared GGUF; B2: Qwen3-Next-80B-A3B with corrected 14.4–20.8 t/s; B3: Qwen3.5-122B-A10B at 12.19 t/s; B4 removed with elimination note)
  - CODE Escalation ASCII diagram rewritten (frontdoor on 8070 + consolidated coder_escalation; architect_general terminal; old architect_coding tier removed)
  - INGEST escalation ASCII updated to reflect Qwen3.5-122B architect_general at 12.19 t/s and SSM ingest throughput
  - Workers table updated (worker_general → gemma-4-26B-A4B at 60.7 t/s on 8072; summarize consolidated to 8070 with Qwen3.6-35B Q8; fast_1/fast_2 deprecation notice)
  - New `## Stack Consolidation (2026-05-09)` subsection added before TaskIR, covering architect_coding elimination, frontdoor+coder_escalation consolidation, worker_general swap, OMP idle-spin fix
  - `enable_thinking=false` note added after the thinking-models paragraph
  - Tier D draft-model line updated (MTP drafter on 8072, not 0.5B on 8081/8082)
  - Model Fallback table architect_coding row removed; fallback simplified to two roles
  - Content cache throughput targets updated to current numbers
  - Posterior Routing intro extended with one paragraph forward-referencing the learned routing controller (Chapter 10)

- `/workspace/repos/epyc-orchestrator/docs/chapters/04-production-server-stack.md` — 9 edits applied
  - Intro paragraph rewritten (drop fixed "9 instances + 535 GB" framing; describe consolidation + numa-mode)
  - HOT tier table replaced with current ports/models/throughputs (8070 shared frontdoor+coder_escalation; 8072 worker; 8083 architect_general; 8085 ingest); 8081 retirement + architect_coding elimination explained inline
  - Total HOT RAM updated to ~600 GB with reclamation notes
  - New `## Port Assignment and NUMA Modes (2026-05-09)` subsection added describing `--numa-mode {full|quarter|both}` and the shared-GGUF model
  - Tier Allocation breakdown rewritten with current per-role memory footprints
  - "Worker Pool Architecture" section prefixed with a DEPRECATED 2026-05-06 notice; historical narrative retained
  - Critical Environment Variables extended with `--numa-mode` and the OMP_WAIT_POLICY/KMP_BLOCKTIME guidance
  - Status example table updated to show consolidated ports and current models
  - SERIAL_ROLES list architect_coding entry removed with explanatory note
  - Concurrent Inference Sweep table flagged as pre-consolidation; recommendation to re-run added

- `/workspace/repos/epyc-orchestrator/docs/chapters/10-escalation-and-routing.md` — 9 edits applied
  - Top-of-chapter intro updated: 6 node classes (was 7); HybridRouter is wired (2026-05-21), no longer "advisory"
  - Pydantic-graph section intro updated to "6 node classes"
  - Node-class code example: `ArchitectCodingNode` removed; `CoderEscalationNode` return union now points at `ArchitectNode`/`End`
  - `escalates_to()` example fixed (`Role.CODER_PRIMARY` → `Role.CODER_ESCALATION`); chain narrative updated to post-2026-05-06 three-role chain with architect_general terminal
  - New `## Learned Routing Controller (2026-05-21)` subsection added immediately after MemRL Integration; describes posterior scoring, cost adjustment, confidence thresholding, abstain-escalate, telemetry fields, integration via `TaskDeps.primitives.select_role()`, feature flag `specialist_routing`
  - 3-Way Confidence Routing target column updated (ARCHITECT now points at architect_general only)
  - `_FALLBACK_MAP` example cleaned up (architect_coding + CODER_PRIMARY removed; coder_escalation ↔ architect_general)
  - `_TIER_MAP` example: architect_coding entry removed with comment
  - Architect Review Loop "Design Goal" paragraph corrected (no more 235B/480B references); enable_thinking=false note added
  - EscalationPrewarmer validation line updated (port 8084 decommissioned)

## Edits deferred or skipped

- The audit suggested verifying `ctx.deps.failure_graph.record_failure(...)` against current method names in `src/graph/nodes.py` (Chapter 10, broken-path concern). Code was not opened — the existing example reads as illustrative pseudocode, not a copy-paste contract, so I left it. Flagging for a separate code-audit pass if exact-name fidelity matters.
- The audit also flagged Chapter 04's "Checkpoint Hooks" section (lines 300–315) as possibly outdated. I did not modify it — verifying whether checkpoint_create/checkpoint_restore is still wired requires reading orchestrator code, and the audit only flagged it as a verification ask, not a confirmed staleness. Left intact.
- The audit suggested a glossary entry for "consolidation" in Chapter 04 and a richer Operations Reference subsection. The Port Assignment and NUMA Modes subsection covers most of the operations-reference need; I did not add a separate glossary entry to keep scope tight.

## Audit items I disagreed with

- The audit recommended updating Chapter 02 line 196 to "Worker pool provides parallel expansion; after 2026-05-08 swap…" — that exact wording lives in Chapter 04, not Chapter 02. I instead reworked the Chapter 02 workers-table note to talk about worker_coder/fast pool deprecation, which is the equivalent edit point for Chapter 02. The Chapter 04 narrative was already rewritten as part of the DEPRECATED 2026-05-06 banner.
- The audit's "Line 30 (RAM budget)" claim that the new HOT RAM is "~600 GB" and KV cache "~460 GB" and OS "~70 GB" sums to 1130 GB — but 600+460+70 = 1130 exactly, so the math is self-consistent. I used those numbers. The audit's parallel claim that "OS + Buffers" goes from 135 → 70 is a fairly aggressive shrink given how much KV the consolidated stack might want; I kept the audit's numbers but operators may want to verify against actual `free -g` post-launch.

## Recommended new chapters or follow-ups

- The audit noted that Chapter 02's "Role Aliases" table (around line 364–380 in the pre-edit file) could need an architect_coding scrub. I checked — the alias table never listed architect_coding (it maps natural-language names to canonical roles), so no edit was needed there.
- A future revision could add an explicit cross-link from Chapter 04's "Port Assignment and NUMA Modes" subsection to the orchestrator_stack.py docstring; the launcher's PORT_MAP is the authoritative source.
- Chapter 02 currently lists `worker_general` in the Workers table with the comment "all aliases route here" but the canonical alias mapping (worker_explore, worker_math, worker_summarize, toolrunner) is in the registry's `shared_with` field. A dedicated "Worker Role Aliases" subsection in Chapter 02 would prevent confusion if/when one of those aliases gets a separate model again.

## Verification notes

- Verified against orchestrator lean registry (`/workspace/repos/epyc-orchestrator/orchestration/model_registry.yaml`) lines 341–545 that:
  - frontdoor lives on port 8070, throughput 24.3 t/s aggregate (line 376), model Qwen_Qwen3.6-35B-A3B-Q8_0.gguf (line 364)
  - coder_escalation also on 8070 with separate slot (line 386–388), same model
  - worker on port 8072 with gemma-4-26B-A4B-it Q4_K_M and MTP at 60.7 t/s per instance (lines 412–440)
  - architect_general at 12.19 t/s (line 500)
  - ingest_long_context at 14.4–20.8 t/s @ ~12K context (line 545)
  - architect_coding role REMOVED 2026-05-06 (line 108 comment confirming) and again at line 509–520 with rationale (REAP-246B 70% vs frontdoor 97% on coder)
  - enable_thinking=false on frontdoor/coder_escalation/architect_general (lines 360, 392, 484); ingest_long_context excepted per memory note
- Confirmed `progress/2026-05/2026-05-06.md` documents architect_coding elimination context (cited in audit but not opened — the registry comments self-corroborate the date and rationale).
- The audit's "active registry" line citations (e.g., "line 4193-4253", "line 371", "line 412") line up with the orchestrator's lean copy I inspected rather than the research repo's larger registry; the registry sources agree on substantive facts.

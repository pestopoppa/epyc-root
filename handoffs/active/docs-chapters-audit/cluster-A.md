# Documentation Audit: Cluster A (Stack & Routing)

## Overview

This audit covers three chapters last touched 2026-03-18 to 2026-03-29, now audited against the codebase state as of 2026-05-26. **Major production changes since last chapter revision:** architect_coding role eliminated (2026-05-06), Qwen3.6-35B-A3B Q8 production upgrade (2026-05-04+06), gemma-4-26B-A4B MTP worker_general swap (2026-05-08), coder_escalation consolidation (2026-05-09), learned routing controller deployment (2026-05-21), cross-role BW-aware routing (active). OMP idle-spin fix (2026-05-09).

---

## Chapter 02: Orchestration Architecture

**Verdict**: patch (targeted rewrites needed, not complete rewrite)
**Severity**: high (contains obsolete role information and outdated model specs)

### Factual errors

- Line 66-76 (Tier B table): **All four rows are stale**
  - B1: Lists "Qwen2.5-Coder-32B" but current frontdoor doesn't use spec decode on this model anymore (that's coder_escalation)
  - B2: "Qwen3-Next-80B-A3B" is correct for ingest, but throughput "6.3 t/s" is outdated (May-4 bench shows 14.4-20.8 t/s at ~12K context)
  - B3: "Qwen3-235B-A22B" swapped to "Qwen3.5-122B-A10B" on 2026-03-19 but chapter still lists old model. Throughput "6.75 t/s" is wrong; actual canonical throughput 12.19 t/s per 2026-05-04 Probe B (`epyc-inference-research/data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/SUMMARY.md`, line 500-502 of active registry confirms 12.19)
  - B4 (architect_coding): **Entire row is obsolete**. Role eliminated 2026-05-06 per `/workspace/progress/2026-05/2026-05-06.md` and `/workspace/progress/2026-05/2026-05-04.md`. REAP-246B scored 70% on coder (worse than worker at 77%), so hard coding escalations now route to coder_escalation (Qwen3.6-35B-A3B Q8, 97% coder, shared GGUF with frontdoor). Source: active registry line 509-520.

- Line 110 (CODER Escalation block diagram): 
  - Port 8081 is correct, but model is now Qwen3.6-35B-A3B Q8 (not "Qwen2.5-Coder-32B"). Speed "39 t/s" is wrong; Qwen3.6-35B on coder_escalation achieves 24.3 t/s aggregate at NUMA quarter mode per 2026-05-09 stack consolidation. Source: active registry line 405 (throughput: 24.3).
  - No longer a separate instance after 2026-05-09; consolidated onto port 8070 with frontdoor (shared GGUF, separate slot). Source: active registry line 382-388.

- Line 189-194 (Workers table):
  - "summarize" row: lists "Qwen2.5-Coder-32B (shared with coder_escalation)" and port 8081. Actually, since 2026-05-06, coder_escalation (and worker_summarize) both run on Qwen3.6-35B-A3B Q8 on port 8070 (consolidated). Shared GGUF, not separate models. Source: active registry line 382-395 (server_mode.coder_escalation and shared_with field).
  - "worker_coder" semantic role is still correct, but the fast_1/fast_2 ports and model specs are outdated post-2026-05-08 swap. Current worker_general is gemma-4-26B-A4B Q4_K_M with MTP spec decode at 60.7 t/s (May-8 benchmark). Source: active registry line 417-440.

- Line 196: "The original 7B coder worker was removed after benchmarks proved the 32B coder-escalation endpoint was both faster and higher quality" — this is correct in spirit but incomplete. The actual evolution: 7B worker → 30B coder → 26B gemma4 (worker_general). The reference to "32B" is from a pre-2026-05-06 snapshot where coder_escalation was indeed 32B. Current coder_escalation is 35B (Qwen3.6) shared with frontdoor. Source: active registry line 395-406.

### Superseded claims

- **Section "Agent Tiers" (lines 53-261)**: The entire Tier B description is pre-architect-coding-elimination (pre-2026-05-06). The escalation diagrams (lines 84-169) show architect_coding (port 8084) as a live role; it no longer exists. The chapter claims code escalates to architect_coding; it now escalates to architect_general (or terminates in coder_escalation if the latter model can handle it).

- **Line 172**: "Dedicated thinking models (Qwen3-4B-Thinking, DeepSeek-R1-Distill-Qwen-32B) were evaluated during benchmarking but are not deployed" — correct as written, but the broader context has shifted. Qwen3.6-35B-A3B Q8 has enable_thinking=false as of 2026-05-20 per `feedback_x_mas_text_routing.md` (thinking loops caused quality collapse to 47%, disabling thinking lifted to 80%). The chapter does not mention this tuning.

### Missing content (post-2026-03-30 landings)

- **Learned routing controller (2026-05-21 deployment)**: The chapter does not describe the wired MemRL system. Lines 89-91 claim "MemRL's learned escalation is advisory (injected via TaskDeps)" but do not explain how it's currently integrated or how the HybridRouter uses MemRL Q-values. Recent handoff `learned-routing-controller.md` (active) describes the architecture. Chapter should reference this for current state.

- **Cross-role BW-aware routing**: Recent completed handoff indicates routing now considers model-specific bandwidth profiles. Not mentioned in chapter.

- **OMP idle-spin fix (2026-05-09)**: Worker_general gemma-4-26B-A4B regression (load 420 → 9 t/s) was fixed by reverting OMP_WAIT_POLICY=passive and using production llama.cpp binary. Chapter does not cover post-launch tuning.

- **worker_general model swap (2026-05-08)**: Chapter assumes Qwen3-Coder-30B-A3B for worker tier; actual is gemma-4-26B-A4B with MTP spec decode. This is a material performance change (60.7 t/s vs 39.1 t/s for old worker) and quality improvement (+6pp full suite, +18pp tool_compliance per Claude-as-Judge).

### Broken path references

- No broken paths; all `src/graph/`, `src/escalation.py`, `orchestration/repl_memory/` references are correct. The `/workspace/repos/epyc-orchestrator/` structure has not reorganized.

### Proposed edits

1. **Line 66-76 (Tier B table)**: Replace entire table with current models:
   - B1 (Coder): Qwen3.6-35B-A3B Q8 (consolidated with frontdoor since 2026-05-06); port 8070; throughput 24.3 t/s (NUMA aggregate); spec decode disabled (MoE pure).
   - B2 (Ingestion): Qwen3-Next-80B-A3B Q4_K_M (unchanged model); throughput 14.4–20.8 t/s at 12K context (May-4 benchmark; update from 6.3).
   - B3 (Architect): Qwen3.5-122B-A10B Q4_K_M (swapped 2026-03-19, per line 486); throughput 12.19 t/s (Probe B 2026-05-04, per budget_diagnostics and live baseline). Remove B4.

2. **Lines 110-139 (CODE Escalation ASCII diagram)**: Update port 8081 model to Qwen3.6-35B-A3B Q8 (consolidated). Add note "Shared GGUF with frontdoor (8070); consolidated 2026-05-09 from separate 8081 instance."

3. **Lines 189-194 (Workers table)**:
   - Replace worker_general model from Qwen2.5-7B to gemma-4-26B-A4B Q4_K_M with MTP; update throughput to 60.7 t/s.
   - Update coder_escalation throughput from 39 t/s to 24.3 t/s.
   - Update summarize row: model now Qwen3.6-35B-A3B Q8 (consolidated from coder_escalation); port 8070; throughput 24.3 t/s.

4. **Line 196**: Correct to "Worker pool provides parallel expansion; after 2026-05-08 swap to gemma-4-26B-A4B with MTP spec decode, achieves 60.7 t/s aggregate across NUMA quarters."

5. **Add new subsection after line 261** (before TaskIR): "**Stack Consolidation (2026-05-09)**\n
   - Frontdoor and coder_escalation now run on shared Qwen3.6-35B-A3B Q8 GGUF (port 8070 full-mode / 8080/8180/8280/8380 quarter-mode), separate admission slots. Reclaimed 36 GB (eliminated duplicate mlock). OMP threads remain separate (96t each); KV cache shared per slot.\n
   - Architect_coding role eliminated 2026-05-06 after benchmarking showed REAP-246B (70% coder) worse than worker_general (77%) and frontdoor (97%). Hard coding escalations now route to coder_escalation (Qwen3.6-35B Q8, shares port with frontdoor)."

6. **Add note post-line 172**: "**Note (2026-05-20)**: Qwen3.6-35B-A3B Q8 has `enable_thinking=false` in production chat_template_kwargs to prevent degenerate `<think>` loops. Improves routing accuracy 47% → 80% on mixed-domain tasks (source: `feedback_x_mas_text_routing.md`)."

### Notes

- The chapter's escalation philosophy (explicit state machine, THINK_HARDER, anti-memory via MemRL) is still sound and well-articulated. The factual updates are primarily model swaps, not architectural changes.
- Chapter 10 (Escalation and Routing) will have complementary errors (lists architect_coding, outdated escalation chains) — recommend coordinating fixes.
- Post-2026-05-21, the chapter should add a brief forward reference to the learned routing controller (one sentence in intro or new subsection), since it's now wired into graph execution (TaskDeps injection) and affects how escalation signals flow. Current chapter describes MemRL as "advisory" but doesn't show how it reaches the node layer.

---

## Chapter 04: Production Server Stack

**Verdict**: patch (port assignments and model specs need refresh)
**Severity**: high (table mismatches will confuse operations)

### Factual errors

- Line 20: Frontdoor port table lists "8080,8180,8280,8380" as HOT tier instances but also says "Port(s)" with four values. Per 2026-05-09 consolidation and 2026-05-09/2026-05-08 progress entries, frontdoor runs on 8070 (full-mode default) OR 8080/8180/8280/8380 (quarter-mode if `--numa-mode quarter` is used). The chapter doesn't mention mode switching at all. **Current state per active registry (line 371)**: Default is port 8070 (full-mode 1×96t). Quarter-mode would use 8080/8180/8280/8380. The chapter's table only lists the quarter-mode ports. Source: active registry line 347-351 (url: localhost:8070, numa_ports: [8080...]).

- Line 20 (frontdoor model): Lists "Qwen3.5-35B-A3B Q4_K_M" but actual is "Qwen3.6-35B-A3B Q8_0" since 2026-05-04. Throughput listed as "~78 t/s agg" for 4×48t quarters; actual per 2026-05-09 entry is ~50.8 t/s agg (12.7 t/s per instance, line 485 of registry shows this is for MoE6 only; consolidated entry reflects lower speed due to shared resource contention with coder_escalation on same port). Source: active registry line 363-380 (model: Qwen3.6-35B-A3B Q8, throughput: 24.3 t/s).

- Line 21 (coder_escalation): Lists "8081,8181,8281,8381" (four instances) and "Qwen2.5-Coder-32B f16 + 0.5B draft", but since 2026-05-09, coder_escalation is **consolidated onto port 8070** (same port as frontdoor, different slot). No longer separate 8081 instances. Model is Qwen3.6-35B-A3B Q8 (same as frontdoor). Source: active registry line 382-406.

- Line 22 (worker_explore/math): Lists "Qwen2.5-7B-Instruct f16" but actual since 2026-05-08 is "gemma-4-26B-A4B Q4_K_M" with MTP spec decode. Throughput "44 t/s" is overstated; gemma-4-26B-A4B achieves 60.7 t/s under ideal conditions (May-8 benchmark) but this is "per instance" — aggregate with NUMA quarters is ~243 t/s (4×60.7). However, the current registry (line 417-440) shows worker on port 8072 (new consolidated port as of 2026-05-09), not 8082. Source: active registry line 410-440 (port: 8072, model: gemma-4-26B-A4B).

- Line 23 (architect_general): Lists throughput "12.6 t/s" but actual is 12.19 t/s per Probe B canonical baseline (2026-05-04). Model listed as "Qwen3.5-122B-A10B Q4_K_M" which is correct. Source: active registry line 500-501 (throughput: 12.19).

- Line 24 (architect_coding): **Entire row is obsolete**. Role eliminated 2026-05-06. Port 8084 is no longer launched by orchestrator_stack.py. Source: active registry line 509-520 and progress 2026-05-06.

- Line 25 (ingest_long_context): Throughput listed as "~12 t/s" but May-4 bench shows 14.4-20.8 t/s at ~12K context. Update to reflect longer-context reality. Source: active registry line 545 (throughput: 14.4-20.8).

- Line 30 (HOT RAM total): Lists "~701GB (62% of 1130GB)" but after architect_coding elimination (139 GB freed per 2026-05-06) and consolidation, the total should be closer to ~600 GB (hot tier), leaving ~530 GB for KV cache + OS. This number needs recalculation based on current models.

### Superseded claims

- **Section "Server Topology" (lines 14-50)**: The port-to-role mapping is obsolete post-2026-05-09. The chapter assumes four separate instance sets (8080/8180/8280/8380 for frontdoor, 8081/8181/8281/8381 for coder, etc.), but the current architecture consolidates frontdoor + coder onto port 8070 (full-mode) or 8080-series (quarter-mode). The chapter does not describe this mode switching, which is now a critical operational detail (users invoke `start --numa-mode full` vs `start --numa-mode quarter`). Source: orchestrator_stack.py launch paths and active registry line 347-351.

- **Line 186-187**: "Critical Environment Variables" section claims `ORCHESTRATOR_CASCADING_TOOL_POLICY=1` is required for all startup paths. This is a pre-2026-05-06 detail that may be stale; recommend verifying with current stack behavior. Does not mention the new `--numa-mode` flag which is now critical.

### Missing content (post-2026-03-30 landings)

- **Stack consolidation logic (2026-05-09)**: No mention of why ports changed or how the new shared-GGUF architecture works. A new subsection explaining port aliasing (8070 vs 8080-series) and shared mmap would prevent confusion.

- **NUMA mode selection (2026-05-08/2026-05-09)**: The chapter doesn't describe `orchestrator_stack.py start --numa-mode {full,quarter,both}`. This is now a standard operational choice. Source: progress 2026-05-08.

- **OMP tuning**: The chapter doesn't mention the 2026-05-09 fix (reverting OMP_WAIT_POLICY=passive, using production binary for worker_general). Post-2026-05-09 status: passive breaks MTP decoding on gemma-4, use active (default).

- **Port 8072 consolidation**: Worker now runs on port 8072, not 8082 (quarter-mode would be 8082/8182/8282/8382). The chapter lists 8082 for worker. Source: active registry line 412 (port: 8072).

- **Qwen3.6-35B-A3B enable_thinking=false**: No mention that the frontdoor model requires this chat_template_kwargs override to avoid degenerate thinking loops (2026-05-20 discovery). Source: `feedback_x_mas_text_routing.md`.

- **Worker pool status (2026-05-06 onward)**: The chapter lists deprecated worker_pool config (explore/code at ports 8082/8092 with Qwen2.5-7B) but says it's still in use. Actually, `worker_pool.enabled=false` (default) since 2026-05-06. The GGUFs are not on disk. Recommend either removing the section or adding a deprecation notice. Source: active registry line 778 (enabled: false) and section 739-780 (DEPRECATED 2026-05-06 notes).

### Broken path references

- No broken file paths (orchestrator_stack.py, model_registry.yaml still exist).
- **Port number mismatch**: The chapter hardcodes ports that have changed. Users following the table will configure the wrong port for worker, architect, etc.

### Proposed edits

1. **Replace lines 18-29 (HOT tier table)** with corrected entries:
   - frontdoor: Port 8070 (full-mode default) OR 8080/8180/8280/8380 (quarter-mode via `--numa-mode quarter`); Model Qwen3.6-35B-A3B Q8; throughput 12.7 t/s per instance (full-mode) or 24.3 t/s (NUMA aggregate quarter-mode); RAM 37 GB shared (mmap with coder_escalation).
   - coder_escalation: Port 8070 (consolidated with frontdoor since 2026-05-09); same model; separate slot; shared GGUF, zero incremental RAM.
   - worker: Port 8072 (full-mode) OR 8082/8182/8282/8382 (quarter-mode); Model gemma-4-26B-A4B-it Q4_K_M with MTP; throughput 60.7 t/s per instance (MTP decode); RAM 16 GB; **Remove architect_coding row**.
   - architect_general: Port 8083; Model Qwen3.5-122B-A10B Q4_K_M; throughput 12.19 t/s; RAM 69 GB.
   - ingest_long_context: Port 8085; Model Qwen3-Next-80B-A3B Q4_K_M; throughput 14.4–20.8 t/s (at ~12K context); RAM 46 GB.

2. **Add new subsection post-line 50**: "**Port Assignment and NUMA Modes (2026-05-09)**\n
   Default operation uses **full-mode** (single 1×96t instance per role, e.g., frontdoor on 8070). For NUMA-optimized quarter-mode, launch with `orchestrator_stack.py start --numa-mode quarter` to activate 4×48t instances per role (frontdoor on 8080/8180/8280/8380, worker on 8082/8182/8282/8382, etc.). Consolidation: frontdoor + coder_escalation share the same GGUF mmap on a single port (8070), reducing duplicate memory footprint. Separate slots ensure admission control (one processes frontdoor requests, one handles coder_escalation)."

3. **Remove or deprecate section "Worker Pool Architecture" (lines 96-149)**: Add a deprecation notice: "Worker pool heterogeneous setup (lines 108-149 below) is **deprecated as of 2026-05-06**. Current implementation uses unified worker_general (gemma-4-26B-A4B-it with MTP) on port 8072, not the multiple 7B/1.5B models listed here. The GGUFs referenced (Qwen2.5-7B, Qwen2.5-Coder-1.5B) are not on disk. Retain for reference only; operational control uses the model_registry.yaml `roles.worker_general` entry."

4. **Line 30 (RAM budget)**: Update total HOT RAM to ~600 GB (post-consolidation; architect_coding removed, frontdoor+coder share GGUF). Update KV cache estimate to ~460 GB and OS buffers to ~70 GB.

5. **Lines 186-187 ("Critical Environment Variables")**: Update to: "All startup paths (`orchestrator_stack.py start`, etc.) inherit `ORCHESTRATOR_CASCADING_TOOL_POLICY=1` unless overridden (critical for MemRL tool routing). Additionally, `--numa-mode {full|quarter|both}` controls instance layout; `--cpu-affinity` and `--omp-threads` can tune OMP scheduling. Current safe setting: active (default), not passive (breaks MTP decoding on gemma-4-26B worker)."

### Notes

- The chapter's core narrative (tiers, health checks, memory hierarchy) is structurally sound. The issues are primarily spec updates and port/mode clarifications.
- Recommend adding a glossary entry for "consolidation" (shared GGUF, separate slots, admission control).
- The section on "Checkpoint Hooks" (lines 300-315) is outdated; it references old checkpoint paths. Recommend verifying if this feature is still in use.
- Strongly recommend a **"Operations Reference" subsection** explaining how to launch in different modes and what to expect (benchmarks, throughput, memory footprint).

---

## Chapter 10: Escalation and Routing

**Verdict**: patch (role structure and escalation chains outdated)
**Severity**: high (escalation diagrams reference eliminated role)

### Factual errors

- Line 129-139 (Escalation chains code): Lists `Role.CODER_PRIMARY`, `Role.ARCHITECT_GENERAL` but the actual enum (per active registry line 4193-4253) shows no `CODER_PRIMARY`. The role is `CODER_ESCALATION`. The escalation chain claimed (Worker → Coder → Architect) is partially correct but incomplete post-architect_coding_elimination. Current chain should be: Worker → Coder_escalation → Architect_general (architect_general is now terminal; architect_coding is gone). Source: active registry escalation_chains and role definitions.

- Line 145-150 (Escalation chains list): Claims "Architect → FAIL (no further escalation)" which is correct, but lists "Architect" without distinguishing that architect_general still exists (architect_coding is gone). The claim should be: "Coder → Architect_general → FAIL" (removing the architect_coding path).

- Line 244 (Timeout config): Lists "architect_coding: 600" but this role no longer exists. The registry (active, line 108) explicitly notes "# architect_coding REMOVED 2026-05-06". Source: active registry line 108.

- Line 353 (complexity classifier): Mentions "architect" as an escalation target but doesn't clarify that hard coding no longer escalates to architect_coding; it routes to coder_escalation (Qwen3.6-35B Q8, same tier as frontdoor but higher quality). The diagram implies a two-tier escalation (simple → moderate specialist) but the actual system now has three tiers (worker → coder_escalation → architect_general) with coder_escalation taking on the "moderate complexity" role.

### Superseded claims

- **Section "Pydantic-Graph Orchestration" (lines 153-241)**: The code example (lines 165-196) lists seven node classes but claims architect_coding is still a node. Per active codebase (e.g., `src/graph/nodes.py`), there are now only six nodes (architect_coding eliminated). The diagram is pre-2026-05-06. Update to remove ArchitectCodingNode.

- **Line 4221** (in roles section, implied): "max_escalations: 1  # was 2 — chain shortened by 1 with architect_coding removal" — this claim exists in the active registry but the chapter does not reflect this shortening. The chapter's escalation narrative assumes a longer chain.

### Missing content (post-2026-03-30 landings)

- **Learned routing controller (2026-05-21 deployment)**: The chapter describes MemRL as "advisory" (line 154-155) but doesn't explain the current wired integration. Recent handoff `learned-routing-controller.md` shows how HybridRouter uses Q-values + posterior scoring. The chapter should add a subsection explaining how learned signals now reach the graph layer (via TaskDeps injection). Source: `handoffs/active/learned-routing-controller.md`.

- **BW-aware routing (recent completed handoff)**: Cross-role routing now considers model-specific bandwidth profiles. Not mentioned in chapter.

- **enable_thinking=false for frontdoor/coder_escalation (2026-05-20)**: Chat template override to prevent degenerate thinking loops. Impact: routing accuracy 47% → 80%. Not mentioned in chapter. Source: `feedback_x_mas_text_routing.md`.

- **Worker_general swap to gemma-4-26B-A4B with MTP (2026-05-08)**: The chapter doesn't describe how this affects escalation routing (e.g., escalation from worker to coder is now a bigger capability jump). Quality and throughput profile changed significantly.

- **OMP idle-spin fix (2026-05-09)**: The chapter doesn't mention tuning/debugging of escalation infrastructure post-launch. OMP_WAIT_POLICY tuning and binary selection now affects performance.

### Broken path references

- Line 236 (code example): References `ctx.deps.failure_graph.record_failure(...)` but actual method names in `src/graph/nodes.py` may differ. Recommend verifying against current source.
- No path-based references are broken (all `src/graph/`, `orchestration/repl_memory/` directories exist).

### Proposed edits

1. **Line 129-150 (Escalation chains)**: Update code and list to remove architect_coding:
   - Change enum to list only `WORKER_GENERAL`, `CODER_ESCALATION`, `ARCHITECT_GENERAL` (three roles).
   - Update `escalates_to()` map:
     ```
     Role.WORKER_GENERAL: Role.CODER_ESCALATION
     Role.CODER_ESCALATION: Role.ARCHITECT_GENERAL
     Role.ARCHITECT_GENERAL: None  # Terminal
     ```
   - Update bullet list: "Worker → Coder_escalation → Architect_general (terminal)".

2. **Line 165-196 (Node classes code example)**: Remove ArchitectCodingNode. Update to six nodes (FrontdoorNode, WorkerNode, CoderNode, CoderEscalationNode, IngestNode, ArchitectNode). Update union return types to remove architect_coding paths.

3. **Line 244 (Timeout config)**: Remove architect_coding row.

4. **Add new subsection post-line 241** (after "MemRL Integration"): "**Learned Routing Controller (2026-05-21)**\n
   The HybridRouter now wires MemRL Q-values into routing decisions via posterior scoring. Instead of rigid rules, the router computes P(success|action) for each escalation target using learned evidence (role history, failure patterns) + heuristic priors. Cost-adjusted scoring applies model throughput to Q-values so expensive models are only chosen when the expected success probability justifies the latency. Confidence thresholding prevents low-confidence routes from escalating; instead, the router may abstain and route to a configured fallback role. Implementation: `orchestration/repl_memory/retriever.py` (HybridRouter class), integrated in `src/graph/nodes.py` via `TaskDeps.primitives.select_role()`. Feature flag: `specialist_routing`."

5. **Line 353 (Complexity classifier)**: Update to clarify that "complex" routes to architect_general, not architect_coding. Note that coder_escalation (Qwen3.6-35B Q8) handles MODERATE complexity (multi-file code changes) before escalating.

6. **Add note post-line 399** (after classifier code): "**Note (2026-05-20)**: Both frontdoor and coder_escalation now run Qwen3.6-35B-A3B Q8 with `enable_thinking=false` (chat template override). This prevents degenerate `<think>` loops that collapsed accuracy from 80% to 47% on mixed-domain tasks. Escalation to architect_general is triggered by failures and architectural complexity, not by thinking-mode degradation."

### Notes

- The chapter's escalation policy and THINK_HARDER mechanism are still accurate and well-explained. The changes are primarily structural (architect_coding removal) and wiring updates (learned routing integration).
- Recommend a brief **"Architecture Updates Since February 2026"** section listing: architect_coding elimination, worker swap, enable_thinking=false, learned routing controller integration, BW-aware routing.
- The "Role Aliases" section (Chapter 02, lines 364-380) will also need updates to remove architect_coding from the mapping (if it's listed there).

---

## Summary and Cross-References

**Cluster A Verdict Tally:**
- Ch. 02 (Orchestration Architecture): **patch** (high severity) — 6+ factual errors in tier specs; architect_coding removal; model upgrades; missing learned routing context
- Ch. 04 (Production Server Stack): **patch** (high severity) — port assignments wrong; model specs stale; consolidation logic missing; mode selection not described
- Ch. 10 (Escalation and Routing): **patch** (high severity) — role structure outdated; escalation chains reference eliminated role; learned routing not wired up

**All three chapters are salvageable with targeted edits. No complete rewrites needed, but all require coordination to remove architect_coding references and update model specs consistently.**

**Downstream Dependencies:**
- Chapter 07 (MemRL) should cross-check that MemRL integration narrative matches Chapter 10's "Learned Routing Controller" update.
- Chapters 05–09 should verify no stale role/port references in pipeline/seeding/memory descriptions.

---

*Audit completed 2026-05-26. Next step: dispatch to editing agent with per-chapter checklists.*

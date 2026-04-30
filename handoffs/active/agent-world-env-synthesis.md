# Agent-World Environment Synthesis

**Status**: stub / in-planning (Phase 1 training-free; Phase 2 GPU-gated)
**Created**: 2026-04-22 (split from `autopilot-continuous-optimization.md` per deep-dive integration pass)
**Categories**: agent_architecture, autonomous_research, training_distillation
**Priority**: MEDIUM (autopilot 5th species; concrete Tier 3 recipe for meta-harness outer loop)
**Depends on**: `autopilot-continuous-optimization.md` (AR-3 loop), `meta-harness-optimization.md` (Tier 3)

## Objective

Adopt Agent-World's autonomous environment + task synthesis (Environment-Task Discovery) as the 5th species in the EPYC autopilot loop. Phase 1 is training-free and CPU-feasible today: LLM-orchestrated exploration of databases and MCP tool ecosystems to synthesize verifiable tasks with controllable difficulty, feeding them as new benchmark suites into AR-3. Phase 2 is GPU-gated and deferred to DGX Spark — multi-environment GRPO training of the co-evolving policy.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-444 | Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence (arxiv:2604.18292) | high | worth_investigating |
| intake-411 | Qwen-Agent MCP singleton manager pattern | medium | adopt_patterns |
| intake-412 | DeepPlanning benchmark | medium | adopt_patterns |

**Source deep dive**: [`/workspace/research/deep-dives/agent-world-environment-synthesis.md`](../../research/deep-dives/agent-world-environment-synthesis.md) (426 lines)

## Key Claims (from Agent-World paper)

- Agentic Environment-Task Discovery autonomously explores databases + tool ecosystems to synthesize verifiable tasks with controllable difficulty.
- Continuous Self-Evolving Agent Training combines multi-env RL with dynamic task synthesis; identifies capability gaps automatically.
- Agent-World-8B and 14B outperform proprietary baselines across 23 agent benchmarks.
- Model Context Protocol (MCP) integration provides a unified real-world service interface.
- Scaling trends correlate with environment diversity and self-evolution rounds (not just model size).

## Phased Adoption

### Phase 1 — Training-free environment discovery (CPU-feasible today)

Use existing local models as ETD (Environment-Task Discovery) agents exploring the MCP ecosystem. Output: synthesized task suites feeding AR-3 as additional benchmark input. No weight updates.

### Phase 1.5 — Optional SFT on public Agent-World trajectories (if weights released)

If Agent-World team releases 8B/14B checkpoints + training trajectories, download + serve as reference models for the species loop.

### Phase 2 — Multi-environment GRPO training (GPU-gated)

Post-DGX-Spark: train Qwen3-8B → Agent-World-8B-EPYC via multi-env GRPO on the arena bootstrapped in Phase 1. Targets: match paper's beat-proprietary claim on ≥5 of our active benchmarks.

## Tasks

### AW-1: Scaffold `env_synth/` module [Phase 1, ~3-4 weeks] — **DONE 2026-04-22 (NIB2-44)**

Delivered at `scripts/autopilot/species/env_synth/`:
- `etd_agent.py` — ReAct agent wrapping injected `llm` / `web_search` / `fetch_url` / `tool_enum` callables; heuristic MCP-endpoint filter (`/mcp`, `/jsonrpc`, `/tools`, `/.well-known/mcp`, `openapi.json`); persists discovered tools into the registry with environment-id tagging.
- `task_synthesizer.py` — LLM-backed composer with injected callable; `DifficultyBand` enum (EASY 1-2 tool calls / MEDIUM 3-5 / HARD 6-10); `SynthesizedTask` record with verifier spec + expected_tool_calls + metadata; `make_fake_llm()` ships deterministic test fixture.
- `verifier_builder.py` — three verifier types (REGEX / EXACT_MATCH / F1 with allowlist + min_tokens guard); rejects trivially accept-all patterns and empty references.
- `mcp_tool_registry.py` — append-only JSONL with durable reload; `MCPToolEntry` dataclass; pluggable async health-check loop with bounded parallelism and N-failure deactivation.

### AW-2: Wire EnvSynth as 5th species — **DONE 2026-04-22 (NIB2-44)**

- `EnvSynth` coordinator in `species.py` wires ETD → synthesis → solvability → arena persist.
- Registered in `scripts/autopilot/species/__init__.py` alongside Seeder / NumericSwarm / PromptForge / StructuralLab / EvolutionManager.
- Emits `EnvSynthAction` journal events with `environment_id`, `tool_set`, `synthesized_tasks`, `rejected_task_count`, `difficulty_band`, `gap_descriptor`, `notes`, `timestamp`. Journal at `orchestration/autopilot_env_synth_journal.jsonl`; arena at `orchestration/autopilot_env_synth_arena.jsonl`.
- `propose_actions()` returns an autopilot-uniform action dict (`{"type": "env_synth_cycle", ...}`) so the controller dispatch layer treats species uniformly. The `### Environment Synthesis` section in `autopilot.py`'s controller prompt is a 1-pass copy-paste pending the next autopilot prompt refresh.

### AW-3: Capability-gap diagnosis + weekly rollup — **DONE 2026-04-22 (NIB2-44)**

- `gap_diagnosis.py` scans AR-3 trial journal (JSONL) and computes per-suite linear-fit quality slope over a sliding window (default 10 trials, threshold 0.01 per-trial delta). `SuiteStagnation` records carry auto-generated gap descriptors (`"need more medium-difficulty <suite> tasks exercising tool-use and multi-step reasoning..."`). `render_arena_rollup()` produces the weekly markdown rollup. Cron wiring is a 1-liner deferred to the next autopilot config refresh.

### AW-4: Safety gate — reference-model solvability — **DONE 2026-04-22 (NIB2-44)**

- `SolvabilityGate` in `species.py` accepts an injected `reference_solver` callback (production wiring: `architect_general` via the standard LLM contract). Gate requires both `solved=True` AND `confidence ≥ min_confidence` (default 0.6). Rejection telemetry feeds journaled `rejected_task_count` which downstream AW-3 consumes to tune difficulty bands if rejection rate exceeds the handoff's 20% steady-state target.

### AW-5: Integrate synthesized tasks with EvalTower — **DONE 2026-04-22 (NIB2-44)**

- `eval_integration.py` projects the arena JSONL into `T1TaskEntry` records with preserved provenance (`discovered_via=env_synth`, `difficulty_band`, `verifier_type`, `environment_id`, `tool_set`). `only_bands` filter keeps T0 gold-ring suites fixed. `flag_human_review()` marks entries whose consecutive model-failure count ≥ threshold (default 3) for the Agent-World paper's bad-task review pattern. Wiring into the EvalTower runner itself (T1 batch injection) lands alongside the first bootstrap.

**Tests**: `tests/unit/test_env_synth_species.py` — 19 tests across verifier types (regex/exact_match/F1 including validation failures), MCP registry durability + health-check deactivation, task synthesizer happy path + bad-JSON fallback, ETD agent discovery + persist, EnvSynth full pipeline (accept/reject), gap diagnosis stagnation flagging + rollup rendering, arena → T1 projection + human-review flagging. All pass.

### AW-6: Bootstrap initial arena [48h inference]

- 48-hour discovery run targeting ≥50 environments / ≥500 tools / ≥500 tasks
- Validate: each task passes AW-4 safety gate, verifier reproducible, difficulty band matches target
- Emit `arena.md` report

### AW-7: Integrate top MCP tools into orchestrator

- Once public Agent-World arena is released (GitHub), adopt top-100 discovered MCP tools
- Register via `tool_policy.py` (per standing policy: only open-source self-hosted tools)
- Cross-ref `orchestration/agent_world_tools.yaml` (new)

### AW-8 (Phase 1.5): Corroboration probe on released Agent-World-8B/14B weights

**Upgraded 2026-04-22 post Tier 2b sweep** from "Optional SFT" / freebie to a mandatory **corroboration probe** before any Phase 2 GPU commit. The paper's "beat proprietary on 23 benchmarks" is UNREPRODUCED in open literature; the 23-suite omits SWE-Bench Verified, GAIA, WebArena Hard, and OSWorld (suite-class cherry-picking).

- Contingent on public weight release by paper authors (1k-env subset + pipeline released Feb 2026; 8B/14B weights unconfirmed)
- If released: download, quantize Q4_K_M GGUF, register as `worker_agent_world` role in `model_registry.yaml`
- Acts as reference model for task solvability (AW-4)
- **New corroboration gate**: run released 8B on SWE-Bench Verified + GAIA (benchmarks the paper OMITTED). If performance diverges meaningfully from same-class open-weight baselines on these omitted benchmarks, downgrade intake-444 and revisit Phase 2 cost-benefit.
- See `/workspace/research/deep-dives/agent-world-environment-synthesis.md` § Tier 2b Contradicting-Evidence Sweep (2026-04-22) for the full rationale.

### AW-9 (Phase 2, GPU-gated): Multi-env GRPO training [deferred]

- Post-DGX-Spark: train Qwen3-8B → Agent-World-8B-EPYC variant via multi-env GRPO
- Target: ≥90% of paper's reported improvements on ≥5 of our benchmarks
- Gate: AW-6 arena size ≥1,000 environments AND ≥10,000 synthesized tasks before training

## Integration Map

| Subsystem | Current state | Interaction with env_synth |
|-----------|---------------|----------------------------|
| Autopilot AR-3 | 4 species (Seeder, NumericSwarm, PromptForge, StructuralLab) | env_synth becomes 5th species; feeds task suites into Seeder's input pool |
| Meta-harness Tier 3 | Deferred outer-loop rebuild | Phase 1 concretizes Tier 3's environment-synthesis direction |
| MCP registry (Qwen-Agent singleton, intake-411) | Pattern documented, not yet deployed | env_synth's `mcp_tool_registry.py` implements the pattern for real |
| EvalTower | Fixed gold-ring + dynamic T1/T2 | T1 gets synthesized-task additions; T0 protected |
| Strategy memory (AP-28) | FAISS-backed with RRF fusion | env_synth species' journal entries feed strategy_store like other species |

## Open Questions

- **Arena-agent reward hacking**: if ETD agent and training agent are same-family, the training agent may overfit to synthesis quirks. Mitigation: cross-family ETD (Qwen for synthesis, Llama/DeepSeek for training)?
- **Verifier quality**: deterministic verifiers are weaker than LLM judges. How much of a problem is this for non-trivial tasks?
- **MCP surface blast radius**: Agent-World references 19,822 tools in the public MCP ecosystem. We can't adopt all; what's the right filter?
- **Task difficulty calibration**: does the "controllable difficulty" claim hold when our reference model is Qwen3-35B-A3B instead of the paper's GPT-5?

## Safety Gates

Per `feedback_dont_dismiss_creative_uses`: synthesized tasks expand the benchmark surface; do not dismiss novel task categories without human review.

Per standing policy (`feedback_opensource_only`): only open-source self-hosted MCP tools. Reject any closed-source tool discovered by ETD.

Per `feedback_incremental_persistence`: task suites must be persisted incrementally during 48h bootstrap (AW-6), not only at completion.

## Cross-references

- `autopilot-continuous-optimization.md` P17 (pointer entry)
- `meta-harness-optimization.md` Tier 3 (concrete recipe pointer)
- `routing-and-optimization-index.md` P17
- `wiki/autonomous-research.md` (updated 2026-04-22 with environment-synthesis dimension)
- Intake sources: 444 (primary), 411 (MCP pattern), 412 (DeepPlanning benchmark methodology)

## Tier 2b Contradicting-Evidence Flag

The "beat-proprietary on 23 benchmarks" claim needs corroboration:
- Benchmark selection may be cherry-picked for Agent-World strengths
- Same-family ETD-and-training risk (noted above)
- No independent replication yet

Before committing to Phase 2 training, run WebSearch for "Agent-World reproduction" / "Agent-World criticism".

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-498] "Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond"** (arxiv:2604.22748, Meng Chu et al., 42 authors incl. Philip Torr, Jiaya Jia)
  - Relevance: this survey explicitly synthesizes 400+ works and 100+ representative systems including Agent-World (intake-444 / arxiv:2604.18292), placing them on a unified "Levels × Laws" map — useful as exogenous referee taxonomy for sanity-checking how this handoff's ETD species fits relative to the broader field.
  - Key technique: **Levels × Laws taxonomy** with three capability levels (L1 Predictor / L2 Simulator / **L3 Evolver** — autonomous self-revision when predictions fail) × four governing-law regimes (physical, digital, social, scientific). Our autopilot species loop is an L3-Evolver-on-digital-laws instance; Agent-World's ETD is an L2-Simulator-feeding-L3 pattern.
  - Reported results: none — survey/position paper, no original experiments.
  - Delta from current approach: zero implementation impact. Value is purely framing. The paper's "decision-centric evaluation principles" and "minimal reproducible evaluation package" are worth tracking if/when a companion artifact is released — could inform AR-3 evaluation gates.
  - Cross-cutting: also relevant to `autopilot-continuous-optimization.md` (the L3 Evolver framing maps directly onto the species loop) and `meta-harness-optimization.md` (the survey's "world model that autonomously revises itself" overlaps conceptually with the Tier 3 harness-search outer loop).
  - **Deep-dive**: [`research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md`](../../research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md) — full read identifies L3 governance recipe (Section 5.4) maps line-for-line onto autopilot SafetyGate, and four evaluation principles (Section 6.1) are testable in existing AR-3 infra today. Relevance bumped to high, verdict to adopt_patterns. Concrete actions: (a) adopt L1/L2/L3 + four-regime vocabulary in this handoff and the wiki, (b) restate ETD species as L2-Simulator → L3-Evolver bridge / Digital regime, (c) when GPU lands and Phase 2 RL training runs, evaluate Agent-World-trained policy vs autopilot-evolved policy on the four principles to test cross-rubric transfer. MREP (Minimal Reproducible Evaluation Package) is proposed-not-released — set watch on matrix-agent/awesome-agentic-world-modeling and arxiv:2604.22748 for shipment.

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-516] "HALO-Gemini-3-Flash-AppWorld — 168 Gemini-3-Flash agent traces on AppWorld test-normal in HALO span schema"** (HF dataset `inference-net/HALO-Gemini-3-Flash-AppWorld`, MIT)
  - Relevance: **medium**. AppWorld is a deterministic long-horizon multi-app tool-use simulator (email/calendar/banking/messaging/file-storage) — exactly the controllable agent-environment class this handoff envisions for L2-Simulator data and L3-Evolver evaluation. The dataset releases hierarchical span trees of a strong commercial teacher (Gemini 3 Flash) over the test-normal split, 3,438 spans / 168 episodes.
  - Two concrete uses for this handoff: (a) **environment-readiness signal** — AppWorld validated as a real benchmark by an external group with full traces published; consider AppWorld in the L2-Simulator candidate list alongside any internal env synthesis, especially for the multi-tool / multi-step / verifiable-reward axis; (b) **demonstration corpus** — Gemini-3-Flash spans are a candidate distillation seed when GPU Phase 2 lands, complementary to autopilot-generated rollouts.
  - Cross-cutting: also referenced from `eval-tower-verification.md` (eval-side use), `meta-harness-optimization.md` (HALO trace-schema family), and `research-evaluation-index.md`. The schema-name collision with `context-labs/halo` (intake-517/518) is unresolved — both projects use the "HALO" name but appear to be separate orgs sharing a span-tree concept.
  - Caveat: scale is small (168 traces); not enough for SFT alone, but workable as a calibration set or as Gemini-vs-EPYC-stack baseline pair.
  - Verdict: `worth_investigating`. Action: when env synthesis or eval tower work activates, evaluate AppWorld setup cost on EPYC and decide whether to ingest these traces as a comparison baseline.

#### Deep-dive refinement (2026-04-30) — AppWorld DEFER

Deep-dive at [`/workspace/research/deep-dives/halo-rlm-trace-loop-integration.md`](../../research/deep-dives/halo-rlm-trace-loop-integration.md) (HALO trio analysis includes AppWorld feasibility audit).

**Decision**: defer AppWorld eval setup AND skip the 168-trace dataset for this handoff's scope.

- Hardware-feasible (no GPU/Docker; FastAPI in-process; ~5s first task / <0.5s subsequent).
- But integration cost is **3–5 days** (orchestrator wiring, SGC scorer, dev/test_normal split runs, baseline runs).
- **No current eval gap demanding it** — Phase 1 (training-free env discovery) doesn't yet need AppWorld; Phase 2 (GPU-gated GRPO training) is also blocked on hardware.
- 168 traces is reference-scale, not training-scale.

Revisit AppWorld if: (a) Phase 2 lands and we want a multi-app simulator with verifiable rewards as one of the ETD environments, OR (b) meta-harness Tier 3 needs an external long-horizon benchmark for the dev/test_normal split discipline. If the decision flips, scope as a separate handoff (`appworld-eval-integration.md`), not as a sub-task of this one.

### New Related Research — 2026-04-30 (markdownfs)

- **[intake-520] "markdownfs (mdfs): in-memory concurrent markdown VFS in Rust with MCP server, Git-style versioning, and multi-user permissions"** (https://github.com/subramanya1997/markdownfs, MIT)
  - **Deep-dive**: [`/workspace/research/deep-dives/markdownfs-rust-mcp-vfs.md`](../../research/deep-dives/markdownfs-rust-mcp-vfs.md) — full source-and-docs read; corrects the original intake on two points (MCP runs as root, single-writer per state.bin) and extracts three patterns worth borrowing independent of mdfs adoption.
  - Relevance: **low–medium / candidate ETD environment, with caveats**. Ten MCP tools span FS ops (read/write/delete/move), directory ops (list/create), search (grep/glob), and version control (commit/log/revert/status). However: (i) **the MCP server runs as `uid=0` root** with NO per-user authentication — the agent has full access regardless of the wheel/agent-token model the HTTP server enforces, so the "user-to-agent permission delegation" framing is HTTP-only, not MCP-side; (ii) **single-writer-per-state.bin** means CLI + HTTP + MCP cannot share a workspace concurrently — multi-process scenarios must funnel through the HTTP server, so mdfs cannot host multiple agents on a shared workspace via MCP alone.
  - Key technique: agent-shaped MCP workspace with content-addressable Git semantics; tokio `Arc<RwLock<DbInner>>` single concurrent core fronted by CLI / REST / MCP; atomic bincode persistence; auto-save every 5s/100 writes (bounded crash window).
  - Reported results: 239 tests passing across integration / permissions / perf / perf-comparison / unit suites; release-mode perf in 4.76s; 1 bug + 6 doc/reality mismatches caught and fixed via in-tree self-audit (`docs/verification-report.md`). The "~102.8× speedup over native FS" headline IS reproducible (real benchmark in `tests/perf_comparison.rs`) but measures kernel VFS+syscall overhead saved (native FS = `/tmp` = tmpfs on Linux = RAM both sides), NOT in-memory-vs-disk. Irrelevant for any LLM-inference-bound workload.
  - Project status: 17 days old, 8 commits, single author, no published releases. Pivot visible in commit log — 2026-04-29 commits removed remote workspace stack and Cloudflare deployment path 24h after they landed. Active scope-finding from cloud product to local agent workspace.
  - Delta from current approach: orthogonal to inference-layer work, partially overlaps with workspace/state design. The interesting integration is as **one MCP tool the ETD species exercises during environment synthesis** — not as a substrate replacement.
  - Concrete (non-blocking) actions:
    - **AW-6 bootstrap**: include `mdfs-mcp` as one candidate MCP endpoint in the 48-hour discovery sweep. Tasks against a versioned markdown VFS with permissions ARE inherently verifiable (commit hashes are deterministic ground truth), well-suited to AW-3 difficulty-band tagging. Note the MCP-as-root caveat in AW-4 SafetyGate scoring — exposes a workspace where any synthesized task has full access.
    - **Borrow Pattern A — `/runs/<run-id>/` markdown artifact schema** (from `docs/execution-roadmap.md`): `prompt.md / command.md / stdout.md / stderr.md / result.md / metadata.md / artifacts/`. A clean human-reviewable companion to our JSONL journals for AR-3 trial bundles or env-synth-coordinator outputs. Independent of mdfs adoption — schema-only.
    - **Pattern B (`docs/semantic-index.md`)** — independent corroboration of `internal-kb-rag.md` K1–K7 (heading-aware chunking, FS-truth + derived vector index, on-commit reindex). De-risks our retrieval design; no implementation change.
  - Do NOT adopt as substrate for `wiki/` or `handoffs/` corpus — that role is already filled by Git + the planned ColBERT KB-RAG (`internal-kb-rag.md`). Single-writer constraint + single-author project + just-pivoted scope make adoption strictly net-negative.

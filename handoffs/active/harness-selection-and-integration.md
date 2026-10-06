# Harness Selection & Integration — Orchestrator ↔ User-Facing Harness

**Status**: active — HS-4 decided 2026-09-16 (OpenCode shell, pi fallback, Hermes-style features inside the orchestrator). Phase 0 live acceptance PASSED 2026-09-26 (P0.4 r3); HS-19a stage 1 "Linked" PASSED 2026-09-27. HS-19b, HS-19c and HS-19d P1–P6 are ❄ FROZEN behind UFH-13 (narrowed plan 2026-09-27). Phase 0 now lives in UFH-15; next source work: P7 and HS-19d.P0, with HS-OD-4 awaiting its API-contract choice.
**Scratch**: `/mnt/raid0/llm/worktrees/codex-ni06-promote-root-k3-20261006`, `/mnt/raid0/llm/worktrees/ni08-screen-proposals-root-20261006`.
**Created**: 2026-07-16 (operator question: keep the Orch orthogonal to its harness, or bake it in?)
**Categories**: agent_architecture, inference_serving, tool_implementation, context_management
**Related (down)**: [`hermes-outer-shell.md`](../completed/hermes-outer-shell.md) (Hermes candidate eval — closed 2026-09-16, not selected; findings in [`hermes-evaluation-20260916.md`](../../docs/reference/harness-candidates/hermes-evaluation-20260916.md)), [`client-surface-audit.md`](../../docs/reference/harness-candidates/client-surface-audit.md) (the reusable audit instrument; HS-4 P0.3 re-ran it on OpenCode — [`opencode-p03-audit-20260916.md`](../../docs/reference/harness-candidates/opencode-p03-audit-20260916.md)), [`user-facing-harness-index.md`](user-facing-harness-index.md) (dispatch index), [`tool-output-compression.md`](tool-output-compression.md) (context-collision surface), [`meta-harness-optimization.md`](../completed/meta-harness-optimization.md) (RLM harness self-improvement lineage)
**Related (precedent)**: [`../completed/orchestrator-conversation-management.md`](../completed/orchestrator-conversation-management.md) (backend-side session/compaction boundary), [`../archived/claude-code-local-constellation-routing.md`](../archived/claude-code-local-constellation-routing.md) (archived ACP-as-Path-B precedent)

## Start here

1. Phase 0 card, release pin and authorized split are complete. [UFH-15](opencode-shell-integration.md) owns remaining P7 source work and inference-bearing override carry.
2. Source/design work continues on P7, P6 and HS-19d.P0; HS-OD-4 needs its published API choice, and HS-OD-9 depends on DAR-LAT-1. The Dockerfile pin is complete.
3. Frozen for their inference-bearing steps only (design and docs may proceed, operator 2026-09-28): HS-19b, HS-19c, HS-19d.P1–P6, until UFH-13 returns SUPPORTED.
4. Closed work: § *Completed Scope*.

## Objective

**Decided (HS-4, 2026-09-16):** the orchestrated stack ("the Orch") stays orthogonal behind `/v1` + `x_*`; the user-facing shell is a thin off-the-shelf **OpenCode** (pi fallback), and the Hermes-style features (memory, delegation, background review, compaction) are built inside the orchestrator. This index owns the harness-agnostic thesis, the decision record and P1–P6 gates; Phase 0 is owned by UFH-15; per-candidate detail lives in the leaf handoffs and `docs/reference/harness-candidates/`.

## Thesis — orthogonal backend moat + cooperation-requiring agent loop

The Orch's value splits into two layers:

- **(A) Harness-agnostic backend moat** — kernels, MTP spec-dec, quantization, model serving, the eval tower, MEASUREMENT governance, cost-aware *scoring*. It has **no UI** and **must stay orthogonal** behind a stable API (`/v1/chat/completions` + `x_*` overrides). Baking it into a harness would entangle the measurement trust boundary with frontend churn. Supporting datapoint: **intake-426** — a coding harness (Claude Code) is ~98.4% operational infrastructure / ~1.6% AI decision logic; the harness is mostly plumbing, our intelligence is the moat.
- **(B) Agent-loop intelligence** — per-turn routing / difficulty estimation, context-folding / tool-output compaction, plan-review reroute, sub-agent fan-out, trace-memory, cost-aware escalation. **Layer (B) only pays off if the harness COOPERATES** (defers to / integrates with the Orch's decisions).

**Load-bearing consequence (operator, 2026-07-16): cooperation ⇒ the harness must be OPEN-SOURCE.** A closed harness (Claude Code, grok-build's binary — intake-249/426/827) cannot be modified to defer to the Orch's routing/compaction/escalation, so (B) would be wasted or actively contested. Therefore closed harnesses are excluded as Orch frontends. **Claude Code is the development harness (this repo's dev loop), NOT an Orch-frontend candidate.**

**Recommendation (default posture):** keep (A) orthogonal; do **NOT** build a bespoke harness (that re-implements ~98% plumbing per intake-426). Adopt an open-source harness whose cooperation surface fits, and inject (B) through it (typed override flags — see the Deterministic Override Flags rule in [`client-surface-audit.md`](../../docs/reference/harness-candidates/client-surface-audit.md) §1 — and/or MCP, and/or ACP).

## Candidates (HS-4 DECIDED 2026-09-16 — OpenCode selected, pi fallback)

| Candidate | Kind | Cooperation surface | Detailed track |
|---|---|---|---|
| **Hermes / OpenGauss** | open-source | `/v1` + `x_*` overrides; ACP adapter as "Path B" | **Not selected (HS-4, 2026-09-16).** [`hermes-outer-shell.md`](../completed/hermes-outer-shell.md) (closed); [`hermes-evaluation-20260916.md`](../../docs/reference/harness-candidates/hermes-evaluation-20260916.md) |
| **OpenCode** — **SELECTED (HS-4, 2026-09-16)** | open-source (MIT) | `chat.params` plugin → top-level `x_*` body keys; all 15 egress paths HONOURED or disabled by config | pin `350c726a` (audit anchor; release tag `v1.18.31` = `014614d3`, source-identical — audit §1 correction): [`opencode-p03-audit-20260916.md`](../../docs/reference/harness-candidates/opencode-p03-audit-20260916.md); HS-1c / HS-1g; Phase 0 boxes under HS-4 |
| **OpenHands** | open-source (MIT) | `/v1` + `LLM.extra_headers` (header-based; needs a server-side shim) | **Not selected** — weakest orthogonality (ships a full layer-(B) loop + Docker substrate); HS-1a |
| **ACP-speaking open harnesses** | open-source | ACP (Agent Client Protocol) | arm closed — HS-2 ROI LOW, HS-3 not triggered; ACP stays a dormant UI adapter |
| **oh-my-pi (omp)** | open-source (MIT) | `/v1` + custom `baseUrl`; per-model `compat.extraBody` puts arbitrary `x_*` keys in the request body, config-only | **Not selected (HS-4, 2026-09-16)** — second router (`retry.fallbackChains`), `yolo` approval default, bus factor ≈1. intake-1148#06 (dive-verified) — HS-1d / HS-5c |
| **deepseek-harness (dsh)** | open-source (MIT) | `/v1` + `baseURL` config-only; typed in-process interception (`agent/request`, `llm/stream`, `tools/*`). **`x_*` body passthrough NOT available today** — needs pi-ai ≥0.84.0 **plus** a ~4-edit dsh patch (bump the pin; add `samplingParams` to `PiAiModelProfile` at `catalog.ts:554` and to `modelFields` at `config.ts:287`; carry it in the materializer). dsh calls `streamSimple` (`adapter.ts:321`), which **is** the path where `Model.samplingParams` is honoured | **Not selected (HS-4, 2026-09-16)** — no lever without a patch. intake-1186 (dive-verified) + intake-1204 (dive-verified) — HS-1e |
| **earendil-works/pi** | open-source (MIT) | `/v1`; `Model.samplingParams` is a **documented zero-code `models.json` field** — the only consumer where this lever needs no patch at all. 104,932 stars (2026-09-14), actively pushed | **FALLBACK (HS-4, 2026-09-16)** — invoked only if OpenCode fails P0.4; HS-1f (scored), HS-1f.1 conditional. intake-1204 (dive-verified) |
| ~~Claude Code / grok-build~~ | closed | none (can't be made to defer) | excluded — reference only (dev harness) |

**Note — three different things are called "pi" here and in intake prose; do not conflate them (2026-09-07).**
(1)+(2) `badlogic/pi-mono` (= pidotdev; the project whose supervision branch the Pi firstmate requires,
intake-473) and `earendil-works/pi` (the candidate rowed above) are **ONE repository** — a rename
(GitHub API 301 → repository id 1035029907, verified 2026-09-14); oh-my-pi is a detached fork of it at
~upstream 0.50, not a sibling. `intake-1360#00`. (3) bare "Pi" as it appears in
intake-1314 / intake-1325 prose, which resolves to neither repository unambiguously and must be
re-resolved before it is cited. `intake-1335#record`.

**Pointer, no claim (2026-09-07).** Prime Agent report — third ingest of the same work (repo
intake-1009, blog intake-1010); see `intake-1313#record`. Unverified; no claim from it may enter a
decision packet.

## Prioritized Task List

- HS-1 (cooperation-surface audits), HS-1a/b/c, HS-2 (ACP ROI: LOW) and HS-3 (not triggered) ✅ closed — [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md); the HS-3 reopen trigger is under *Dormant triggers* at the end of this file.
- [x] **HS-4 — Harness-selection decision gate:** Hermes vs OpenCode vs an ACP-speaker, gated on HS-1 + HS-2. Default outcome preserved: (A) stays orthogonal; no bespoke harness unless a specific research-demo differentiator justifies it.
  ✅ 2026-09-16 DECIDED by operator: thin off-the-shelf shell = **OpenCode** (pi fallback); Hermes-style features built inside the orchestrator (doc `docs/design/hs4-shell-and-orchestrator-features-20260916.md`). Implementation tracked in the HS-4 P0–P5 boxes below.
  - **Decision package (2026-09-16, `sub-hs4`, zero-inference):** [`../../docs/design/hs4-harness-decision-package-20260916.md`](../../docs/design/hs4-harness-decision-package-20260916.md) — options A OpenCode / B pi / C omp / D Hermes / E dsh / F defer; recommends **A (OpenCode)**, with B as the minimal-import alternative (tie-break: must the frontend consume the Orch's tools over MCP natively?); decidable without HS-1f.1. Operator decides.
  - **Operator decision (2026-09-16):** adopt a **thin off-the-shelf shell**; implement the wanted Hermes features — user-profile memory, delegation, background review, compaction — **inside the orchestrator**, not the shell; **one memory system, one router, no patches to carry**. Follow-up question ("OpenCode or oh-my-pi, then add Hermes features afterwards?") answered by `sub-hs4-design`: [`../../docs/design/hs4-shell-and-orchestrator-features-20260916.md`](../../docs/design/hs4-shell-and-orchestrator-features-20260916.md) — **shell = OpenCode** (no competing router, native per-session `chat.params`, `ask`-fallback permissions, broad maintainer base), **pi = fallback**; oh-my-pi not chosen (its `retry.fallbackChains` router is fully disableable via `retry.modelFallback:false`, but it is a boolean to re-audit on every bump, `tools.approvalMode` defaults to `yolo`, bus factor ≈1). Features live in the orchestrator, exposed as implicit `/v1` behaviour plus MCP tools; the shell carries one session-stamping plugin. **New Phase-0 blocker found:** `/v1` never emits `tool_calls` (`openai_compat.py:228,322-331` @ `83c7ed2f`), so no agentic shell can run its tools until a client-executed tool mode lands. Closed in code by P0.1 (orch `ed554da2`): `x_tool_mode="client"` emits `tool_calls`; the default mode (REPL bridge) is unchanged.
    - **Shell confirmed by the operator, 2026-09-17:** OpenCode stands — "flexible enough to mold into what we want". The 2026-09-16 record folded the shell pick into the design pass; the operator had chosen the *posture* (thin shell, features in the orchestrator) and named "OpenCode or oh-my-pi", not the shell itself. That gap is now closed: OpenCode is the operator's pick, pi remains the fallback, and HS-1f.1 stays conditional on the fallback being invoked.
    - Phase 0 implementation, r3 disclosure, release pin and remaining carry/P7 work: [opencode-shell-integration.md](opencode-shell-integration.md) (UFH-15).
      - [x] **HS-4 P0-split — once P0.4's live run lands, move Phase 0 into its own handoff** *(trigger met 2026-09-26: the live run passed; do it with or after P0.4b/P0.4c)* `opencode-shell-integration.md`, with its own `UFH-NN` row in [`user-facing-harness-index.md`](user-facing-harness-index.md); this index keeps the decision record, the candidates table and the P1–P5 gates and points at the new handoff. **Operator-approved 2026-09-17**, deliberately gated: the P0.4 live run is owned by another session and must not be moved under it mid-flight. Surfaced by the 2026-09-17 document audit alongside the archive/promotion split that has already landed (see *History and promoted material*).
      ✅ 2026-10-06 — MAIN applied the preauthorized split after independent r3 source review; one owner row, task text/state conserved.
    - [ ] **HS-4 P1 — server-side compaction with a session fold cache** (doc §3.6). Mechanism owner: [`context-folding-progressive.md`](context-folding-progressive.md) CF-3c / CF-PB-1 (pointer only; that handoff owns the work).
    - [ ] **HS-4 P2 — user profile + notes on `/v1`** (B1 injection is dead code today; doc §3.1–3.2). Measurement: [`episodic-memory-integrity.md`](episodic-memory-integrity.md) M-12 (memory-on vs memory-off A/B; pointer only).
      - [ ] **HS-4 P2 carry — `memory_*` MCP tools declare `session_id`.** If the P2 memory tools ship as a separate MCP server (a `memory_` prefix), give that server the same declares-`session_id` and refuses-undeclared tests as `tests/unit/test_mcp_undeclared_args_refused.py`. Filed 2026-09-17 (`sub-hs4-mcp`).
    - [ ] **HS-4 P3 — `session_search` via `/v1` trace write-side + `ms.search` MCP** (doc §3.3). Mechanism owner: [`unified-trace-memory-service.md`](unified-trace-memory-service.md) — UTM-P1 done (orch `dd24ed10`), UTM-B1 (`ms.search`/`ms.expand` registration) open (pointer only).
    - [ ] **HS-4 P4 — delegation MCP tool + `/v1` routing parity** (doc §3.5).
      - [x] **HS-4 P4-pre — fix the `x_max_escalation` field description in `src/api/models/openai.py`** (epyc-orchestrator). It still describes the field as capping escalation, while `/v1` only records it (`openai_compat.py`; no escalation in client mode until P4). One-line field-description fix; the enforcement itself is P4. Filed 2026-09-17 from the HS-4 document-set audit. ✅ 2026-09-27 — done by orch `336bd170` (2026-09-17, which wrote "METADATA ONLY on /v1 today … NOT enforced") and never ticked. TE-1 (`9959e8db`) updated the text again: escalation is governed by `x_escalation` (flag `v1_escalation`), never by this field.
      - Progress 2026-09-27 (UFH-13 TE-1, not P4 itself): orch `9959e8db` / `280059cc` add default-off `/v1` escalation through `/chat`'s post-answer hooks (`src/api/routes/v1_escalation.py`, `x_escalation: auto | off | architect_general`). This is the escalation-parity subset only. P4's delegation MCP tool and `x_max_escalation` enforcement remain open, and P4 should extend that module, not fork it.
    - [ ] **HS-4 P5 — background review, proposal-only** (doc §3.4). Measurement: [`episodic-memory-integrity.md`](episodic-memory-integrity.md) M-12 protocol (pointer only).
    - [ ] **HS-4 P6 — serve the REPL exploration tools over the `orchestrator` MCP server, one implementation.** Today two copies exist: the orchestrator mixins (`src/repl_environment/code_search.py:124,:379`, `file_exploration.py:93,:144`, `combined_ops.py:280`) and the autokernel seat's `epyc-inference-research scripts/kernel_rnd/autokernel/loop/actor_tools_mcp.py` (outline / read_range / grep / code_search / profile_top / symbol_annotate, hard output caps, same ColGREP binary and alpha; research lane `lane/ak-actor-seat-20260924`, DS41-C20). Export `code_search`, `peek`/`read_range`, `grep`, `peek_grep` as `@mcp.tool()`s in `src/mcp_server.py` (beside `orchestrator_chat` `:451`) with a `root` argument resolved through `task_root.resolve_task_path` and the seat's byte/line caps as the default output contract, so the OpenCode shell, opencode actors and the orchestrator's own REPL share one implementation. `profile_top` / `symbol_annotate` stay autokernel-owned (perf-profile readers) and register as a second MCP server, not a copy. Acceptance: `actor_opencode_config.MCP_TOOLS` can point at the orchestrator server for the four shared tools with the seat tests green, and `actor_tools_mcp.py` shrinks to the two profile tools. First consumer: INF-78 ([`autokernel-orchestrator-actor-backend.md`](autokernel-orchestrator-actor-backend.md)). Zero inference.
      - *Catalog-growth acceptance (added 2026-09-26, research intake):* before P6 (or the P2 `memory_*` server) changes the MCP tool catalog OpenCode sees, re-run a frozen set of previously passing OpenCode tasks before and after the change, logging per-task tokens; the change lands only if no previously passing task fails in both of two reruns, and the per-task token ratio is reported. Catalog growth can raise accuracy while nearly tripling tokens (EvoHarnessBench, ReAct: 26.0 → 30.2 pass for 27.2M → 75.8M tokens, intake-1821#2), and pool growth can break previously working delegation (intake-1821#1, intake-1821#7). Runs through the P0.4 runner, so records project via SC86.

      - [ ] **HS4-P6-SOURCE — prepare the shared explicit-root exploration core and compatible REPL adapters without changing the MCP catalog.** [MAIN accepted source contract](../../docs/design/hs4-p6-shared-exploration-source-contract-20261006.md): map existing task/read-root and knowledge fences, character-page versus actor line contracts, root-bound search and bounded outline compatibility. Verify source and synthetic controls before integration; no new read authority or global root. Active MCP registration, actor catalog removal and deployment stay behind P6’s two-rerun catalog-growth gate.

- [ ] **HS-1f — score `earendil-works/pi` as an HS-4 candidate.** Never previously listed, and it is the **upstream of both** oh-my-pi (intake-1148#record, rowed) and the pi-ai library dsh depends on. On the body-injection axis it is at parity with oh-my-pi's `compat.extraBody` and strictly ahead of dsh. Score it on orthogonality and minimum-imports like every other candidate before drawing any conclusion — a strong cooperation surface is necessary, not sufficient. Scored 2026-09-14 (below) and used in the decision package §3-B (Option B); pi is the HS-4 fallback. Box left for the owning session.
  - **Source-level score 2026-09-14 (`earendil-works/pi@ceea48f5`, no live request):** cooperation SUFFICIENT — every LLM call (main loop and CLI compaction) uses the simple call verb (`packages/coding-agent/src/core/sdk.ts:314/324` → `packages/ai/src/api/openai-completions.ts:989-991`; compaction `packages/coding-agent/src/core/compaction/compaction.ts:596-597`), so `models.json` `samplingParams` reaches the body (the HS-1g call-verb check is satisfied for pi); `before_provider_request` gives per-turn payload replacement. Orthogonality/minimum-imports strongest audited: static model, no sub-agents, `compaction.enabled=false` disables threshold AND overflow folding. Costs: no core MCP, no ACP, no permission system (containerise), install ping + separate update check (`PI_OFFLINE=1`), new-contributor auto-close (patches live in extensions), Node/TS runtime, heavy churn (pin v0.85.1). The built-in llama.cpp provider is **router-mode only** (`packages/coding-agent/src/extensions/llama/client.ts:192`) → use a `models.json` custom provider with the built-in llama compat flags (`provider.ts:63-70`) and `maxTokens ≤ 32768` (orchestrator `src/api/models/openai.py:90`). An optional MIT efficiency layer (NVlabs SoL-Pi) exists; never use its default hosted reducer route. `intake-1360#record`, `intake-1350#record`.
  - [ ] **HS-1f.1 — one live request (conditional: only if the pi fallback is invoked, i.e. OpenCode fails P0.4):** pi custom provider with `samplingParams` `x_*` keys against orchestrator `/v1`; confirm top-level arrival and tolerance of `store` / `strict:false` / `stream_options` (inference). Not needed while OpenCode is the shell.

- [ ] **HS-5b — score editor-side trainability as a SEPARATE axis, and treat it as strictly downstream of HS-4.** Editor-side trainability is a distinct axis from HS-5's *"does the harness ship a weight-space RL adapter"* — the trainable object can be an **external editor for ANY harness**, so the absence of a first-party adapter does not close the axis. Binding **ordering constraint**: a harness must be **frozen BEFORE** anything is trained against it. A harness swapped in afterwards recovers ~nothing (7B GRPO 55.6 → 55.5/55.4) and a tool-schema change afterwards lands the system **below its untrained baseline** (2.7 vs 13.5). Therefore trainability is **downstream of selection and can never be a selection criterion** — a second, hardware-independent reason for the HS-5 AsyncGRPO decline (that caveat is in the [history](../archived/harness-selection-history-through-2026-09-16.md)). `intake-1323#record`, `intake-1339#record`.
- [ ] **HS-9 — Open-weight interpreter feasibility probe** — the one genuinely novel transfer question in the set. All NLAH arms ran on `gpt-5.4-mini`; nothing establishes that an open-weight model can *interpret* a natural-language policy document faithfully. Their mechanism metrics (Workflow Preservation, Stage Coverage, Ordered Workflow, Artifact Contract, Tool Call Success, Information Handoff Recall) score policy adherence **without a benchmark score**, so drift is measurable on saved traces — deterministic-replay-eligible. Watch their own red flag: **Information Handoff Recall drops to 0.32/0.55 under parent-child execution even on a frontier model.**
  - **Stratification requirement (2026-09-07, research-intake).** Richer scaffolding **scales with model capacity** — +12.6 (Qwen2.5-3B), +21.6 (Qwen2.5-7B), +40.2 (GPT-5 Mini) — so this probe must **stratify by model size** and expect a **capacity floor**, not a binary works/does-not-work answer. A null on one small open-weight model would not answer the question the probe is for. `intake-1339#record`.
- [x] **HS-E1 — add the harness-null-pool evidence packet to HS-4.** File intake-1444 (30 budget-matched harnesses / 3.1M rollouts / no universally superior harness / checkpoint-pruned portfolio 85.75% vs 82.49%), intake-1457 (independent 12-task convergence; fluid bandit 0.780 vs 0.718), the EvoTrace knob-exposure confound (intake-1451) and the SwarmResearch 13/15 unverifiable finding (intake-1450) into the HS-4 evidence base. HS-4 was decided before this packet was filed, so it is recorded in the decision package §5 as bake-off context (external rows), not as selection evidence.
  ✅ 2026-10-06 — MAIN accepted the dated, precisely cited context addendum; canonical-ledger cite gate passed. Unknown ledger coverage remains unknown and supplies no selection warrant.
  - _Context for this row (external evidence, 2026-09-17 intake): [history](../archived/harness-selection-history-through-2026-09-16.md)._

## `/v1` seam defects — HS-OD-3..9 (found 2026-09-17, descriptions fixed, behaviour not)

_Same lane as the closed HS-OD-1/HS-OD-2 (archived [history](../archived/harness-selection-history-through-2026-09-16.md)): this handoff owns the cooperation contract, and every defect below sits in the seam **any** selected shell inherits. Found while sweeping the request-schema descriptions after `336bd170`; the descriptions now tell the truth (orchestrator `dadad301`), so these five rows are about the BEHAVIOUR, not the docs. Line refs are `src/api/routes/openai_compat.py` at orchestrator `dadad301`._

- [ ] **HS-OD-4 — make the `max_tokens` contract explicit in default text REPL mode.** APP79 (`src/api/routes/openai_compat.py:1530-1549, 1894-1913`) maps it to a 1..5 turn count, while every REPL generation call still passes `n_tokens=1024`; client-tool and `x_disable_repl` paths pass `request.max_tokens` as the generation cap. A text REPL request with `max_tokens: 64` therefore allows one 1024-token model call. The prior vision description is stale: APP79 rejects an explicitly supplied non-null `max_tokens` on image requests with 422 before dispatch (`:797-807, 1190-1198`), in line with HS-OD-5's fail-closed behavior. Decision options and recommendation: [`hs-od-4-max-tokens-decision-prep-20261006.md`](../../docs/design/hs-od-4-max-tokens-decision-prep-20261006.md).
- [x] **HS-OD-5 — sampling overrides are silently dropped on image requests.** `temperature`, `top_p`, `top_k`, `seed` and `max_tokens` are forwarded on the text path when explicitly set (`:578-586`) but `_run_openai_vision_completion` takes none of them (`:600-627`). A caller pinning `seed` for a reproducible vision run gets an unseeded one with a 200. This is the HS-OD-1 shape exactly — a field that changes output semantics being ignored rather than refused — so the default answer is a 422 naming the field, not silent acceptance.
  ✅ 2026-10-05 — Seven explicit image-control fixtures pass; unsupported non-null controls return 422 before dispatch, while omitted/null defaults remain valid. Off-host run `37284177689`; reviewed source published in orchestrator main `41ab07fc`, with root client changes published at this boundary.
- [x] **HS-OD-6 — `x_disable_repl=true` plus `tools` tells the model to call tools nothing will execute.** The tool block is still rendered into the prompt as `CALL(...)` instructions (`:348`) while the REPL executor is disabled (`:918, 1183`). Either suppress the tool block when the executor is off, or refuse the combination with a 422. Today the model is instructed to use a mechanism that is not there.
  ✅ 2026-10-05 — All three original disabled-REPL/tools golden requests remain present and pass as declared 422 responses with zero model calls; client-executed tools remain valid. Off-host run `37284177689`; reviewed source published in orchestrator main `41ab07fc`, with root client changes published at this boundary.
- [x] **HS-OD-8 — backpressure never reaches the shell as a retryable HTTP status.** At orch `fb7871ea`: a full admission queue (`inference.py:958-972`) answers **502** "Backend failed" with no `Retry-After` (`openai_compat.py:1427-1433`, stream `:1008-1016`); on `stream:true` (OpenCode's main loop) every denial is an SSE event after a 200, so no header can reach `session/retry.ts`; and no in-stream error text matches OpenCode's retry patterns (`retry.ts:33-41,146-152`), so a queued turn can fail with no retry. Fix: admit or probe before returning the `StreamingResponse`; answer a denial as HTTP **503 with `Retry-After` and `retry-after-ms`** (OpenCode reads `-ms` first, `retry.ts:51-56`); map queue-full to 503, keep genuine upstream faults 502; make any residual in-stream error text retryable (contains "503 service unavailable"). The header value stays the current constant until HS-OD-9. Acceptance: extend `harness/opencode-plugin/test/wire-contract.test.ts` through the pinned SDK 2.0.41 + `retry.ts delay()` — the header is honoured on a pre-stream 503 and the in-stream fallback is retried; `test_openai_compat_backend_failure_status.py` still pins 502 for upstream faults. Zero inference. [intake-1790#1, intake-1792#1]
  ✅ 2026-10-05 — Twenty-one admission/API fixtures and the 105-test pinned SDK/Node suite pass, including actual OpenCode retry-delay cases. Pre-stream admission denial is 503 with constant 5000 ms headers; genuine upstream faults remain 502 and residual SSE denials are retryable. Off-host run `37284177689`; reviewed source published in orchestrator main `41ab07fc`, with root client changes published at this boundary.
- [ ] **HS-OD-9 — derive the backpressure delay from live queue state (after HS-OD-8; consumes decision-aware-routing.md DAR-LAT-1's `expected_wait_s`).** Replace the constants (5 s `api/__init__.py:401,406`; 10 s `:418`; 30 s `routes/chat.py:321`) with the expected wait from the ONE admission-ledger estimator, decision-aware-routing.md DAR-LAT-1 — never a second occupancy model. Hold the request in the orchestrator while the estimate fits its own wait budget (the template's `headerTimeout:false` means a pre-stream hold does not time out the shell); bounce only beyond it, with `Retry-After`=ceil(s) and `retry-after-ms`, so OpenCode's 5-retry budget (`retry.ts:31`) spans the queue. Emit `retry_after_ms` + `retry_after_basis` (`estimate|constant`) beside, never inside, the closed `epyc.failure_provenance.v1`. Write one receipt per bounce (VB-V1-BACKPRESSURE). [intake-1790#1, intake-1792#1]

- [x] **HS-OD-10 — the `x_disable_repl` direct path sent thinking-on roles an untemplated prompt with the suffix appended; fix landing.** ✅ 2026-09-29 — landed (orch `5ddb7320`) and live
  (filed 2026-09-28)
  - **Defect.** `/v1` with `x_disable_repl` (including `x_force_role`) called `llm_call(combined_context, role=role)`
    with no chat template and with the role's `system_prompt_suffix` after the user text. For the 27B roles on :8083
    (the `/completion` lane) llama-server continued the raw text. The ARCHSWAP serving proofs of 2026-09-28T08:54Z
    show it: `architect_critic` echoed a JSON template, `coder_escalation` repeated its suffix's last line, and
    `<think>` arrived inline in `content` (`/mnt/raid0/llm/tmp/archswap-20260927/serving-proof-20260928T085434Z/`).
    Pre-existing since orch `ae5975b4` (2026-04-05).
  - **Fix.** Orch `66ef96b8`, a lane commit being landed on orch main by another agent at filing: an
    orchestrator-side chat template for `/completion` roles (bare for chat-completions roles, the same rule as
    `chat.py`'s direct path), `skip_suffix=True` as in `/chat`'s direct stage, and a leading closed `<think>` block
    split into `message.reasoning_content` (one `reasoning_content` delta when streaming).
  - **Behaviour change to check.** Chat-completions roles (for example `frontdoor`) on the `x_disable_repl` path no
    longer get their suffix appended. The autopilot `LocalPlannerProvider` uses exactly this path
    (`scripts/autopilot/planner_providers.py:562`, `x_disable_repl: True`), so its planner drafts lose the role
    suffix. Confirm `_local_planner_prompt` carries what the suffix supplied, or add it back explicitly there.
  - Ticks when `66ef96b8` is an ancestor of orch `origin/main` and the planner check is recorded.
  - Not fixed by this: the default REPL bridge (`openai_compat.py` ~:1674) still sends thinking-on roles an
    untemplated prompt with the suffix. That path is one of `routing-intelligence.md` RI-23's.
  - ✅ **Closed 2026-09-29.** The fix landed on orch main as `5ddb7320` (the landed form of lane commit `66ef96b8`;
    test tap isolation `8a7d57a8`) and is live: API-only reload 2026-09-28 (PID 458129), re-proved templated on
    2026-09-29 07:06Z (`/mnt/raid0/llm/tmp/archswap-20260927/serving-proof-20260929T070556Z/`) and again at 15:04Z
    with `reasoning_content` once RI-23 put these roles on the chat-completions lane
    (`serving-proof-20260929T150402Z/`).
    - **Planner check (code read at orch `origin/main`, 2026-09-29): losing the suffix is harmless, and an
      improvement.** `LocalPlannerProvider._payload` sends `_local_planner_prompt(...)`, which wraps the draft and
      critique prompts in `_LOCAL_ACTION_OUTPUT_CONTRACT` / `_LOCAL_CRITIQUE_OUTPUT_CONTRACT` at both head and tail
      (JSON-only fenced output, "no prose before the first fence"); the brief prompt carries
      `_LOCAL_BRIEF_OUTPUT_CONTRACT` the same way. The planner role is `frontdoor` by default
      (`planner_providers.py:446`) and `ingest_long_context` under `start_authority_daemon.py`. Their suffixes ask for
      "clear, user-friendly explanations ... elaborate" and "structured headings ... cite source locations", which
      contradict the JSON-only contract. The contract already supplies everything the planner needs, so nothing is
      added back.

**Read these together with HS-OD-1.** That row established the rule: *a body field that changes output semantics must be refused, not ignored.* HS-OD-4 remains a mode-dependent contradiction of it; HS-OD-5/6 are now closed with explicit refusals, and HS-OD-3 is a name that documents a capability the code does not have. Each repair changes `/v1` behaviour a shell depends on, so each wants its own before/after test, and HS-OD-3's answer is a small design decision rather than a patch. HS-OD-3 and HS-OD-7 closed 2026-09-17 (orch 2a609f5c; see the [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md)).

## Dependency Graph

```text
HS-4 decided 2026-09-16 (OpenCode, pi fallback) — inputs HS-1/HS-2/HS-5c/HS-1e/HS-1f closed
P0.1/P0.2/P0.3/P0-MCP (closed) → P0.4 live acceptance PASS 2026-09-26 → P0.4b (Harness Card) + P0.4c (pin freeze)
                                                                        → P0-split → P1 → P2 → P3 → P4 → P5
HS-19a stage 1 PASS 2026-09-27 → HS-19d.P0 (zero inference)
                               → ❄ HS-19b / HS-19c / HS-19d.P1–P6 (until UFH-13 returns SUPPORTED)
HS-1f.1 only if the pi fallback is invoked
```

## Cross-Cutting Concerns

1. **Context-collision surface** — a candidate harness's OWN conversation compaction / prompt-cache mgmt / sub-agent spawning can double-up or fight orchestrator-side Phase-2 compression + context-folding. Owned by [`tool-output-compression.md`](tool-output-compression.md) (see its Phase-4 cross-refs) and the Hermes Cons/Key-Questions in [`hermes-outer-shell.md`](../completed/hermes-outer-shell.md) (closed; see [`hermes-evaluation-20260916.md`](../../docs/reference/harness-candidates/hermes-evaluation-20260916.md) §3). This is the concrete instance of "(B) needs cooperation."
2. **Backend-moat orthogonality + MEASUREMENT trust boundary** — layer (A) (eval tower, scoring, era registry, safety gates) stays server-side and human-amendment-only; a harness must never absorb it.
3. **RLM harness self-improvement lineage** — the "specialized harness beats a general one" idea (intake-517 HALO) cross-links to [`meta-harness-optimization.md`](../completed/meta-harness-optimization.md) (completed ledger; do not route work there).

## Key Files / Surfaces

- The **`/v1/chat/completions` + `x_*` override** contract (the stable orthogonal API) — orchestrator routing/override surface.
- `research/deep-dives/opengauss-architecture-analysis.md` — ACP / session-analytics / context-compression prior art.
- [`docs/reference/harness-candidates/client-surface-audit.md`](../../docs/reference/harness-candidates/client-surface-audit.md) — Deterministic Override Flags (§1, the cooperation pattern) and the Client Surface Audit with the HS-1g call-verb check (§2, the audit instrument).
- [`harness-card.md`](../../docs/reference/harness-candidates/harness-card.md) — the two Harness Cards (editable-vs-code-owned, and the conformant ETCSOVG card `HARNESS_RUN_POLICY.md` requires a run report to cite).
- [`harness-doctrine.md`](../../docs/reference/harness-candidates/harness-doctrine.md) — standing doctrine: HS-7 re-targetability and HS-10 evaluation-side randomization.
- [`v1-structured-output-capability.md`](../../docs/reference/v1-structured-output-capability.md) — what the kernel serves grammar-constrained vs what the `:8000` seam refuses.

## Reporting Instructions

- Record Phase-0 and P1–P5 evidence in the HS-4 box text (commit SHAs, audit docs, verdict files) and flip a box only with `✅ YYYY-MM-DD` once its live gate has run; code landed but not reloaded is text evidence, not a tick. P0.4's verdict updates the Status line and freezes the OpenCode pin.
- Any change to the orthogonality posture or the open-source requirement is an operator decision — flag, do not decide autonomously.

## Evidence Base (intake)

intake-833 Local Studio (mgmt-GUI end) · intake-827 grok-build (closed, ACP) · intake-263 claude-acp-server (ACP↔Anthropic; prior MCP-first lean) · intake-426 "Dive into Claude Code" (98.4% infra / 1.6% logic) · intake-249 Claude Code leak analysis · intake-243 Claw Code · intake-254 Goose · intake-255 Clido · intake-473 pi-agent-core · intake-517 HALO · intake-183 0xSero/vllm-studio.

## Completed Scope

| Scope | Closed | Where |
|---|---|---|
| HS-1, HS-1a/b/c, HS-2, HS-3 — candidate cooperation-surface audits and the ACP ROI verdict | 2026-07-17 … 2026-09-26 | [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md) § Candidate audits |
| HS-4 Phase 0 closed steps — P0.1, P0.2, P0.3, P0.4 (live PASS r3), P0.5, P0-MCP-a/b, P0.4 preflight, both P0-pre fixes | 2026-09-16 … 2026-09-26 | [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md) § HS-4 Phase 0 |
| HS-1d, HS-5c, HS-1e, HS-1g, HS-15, HS-13 — decision-packet folds and instrument updates | 2026-08-18 … 2026-09-17 | [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md) § Decision-packet folds |
| HS-OD-3, HS-OD-7 — `/v1` seam defects (orch `2a609f5c`) | 2026-09-17 | [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md) § `/v1` seam defects closed |
| HS-TD-4 — prepared-action envelope and `decision_receipt.v1` (orch `b19ff1d1`) | 2026-09-26 | [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md) § HS-TD-4 |
| HS-18 — `nvext.agent_hints` alias declined | 2026-09-26 | [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md) § HS-18 |
| HS-19a stage 1 "Linked" — HS-19a.1–.6 (live PASS 18/18) | 2026-09-27 | [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md) § HS-19a stage 1 |
| HS-OD-1/2, HS-5 … HS-14 — pre-decision comparison, closed seam defects, intake rows | through 2026-09-17 | [archived history](../archived/harness-selection-history-through-2026-09-16.md) |

## History and promoted material

Split out 2026-09-17, after HS-4 closed. This handoff keeps the decision record, the live task list
and the P0–P5 gates; everything below has a home of its own.

| What | Where | Why it moved |
|---|---|---|
| Pre-decision candidate comparison (HS-1/HS-2 findings, the 2026-07 intake updates, the trainability and Stage-4 sections, HS-4 external instruments, the closed `/v1` seam defects HS-OD-1/HS-OD-2, the 2026-09-14 intake rows) | [history](../archived/harness-selection-history-through-2026-09-16.md) | Closed, and written while the selection was still open. Not a task list. |
| Harness Cards (HS-6, HS-6b, HS-6c) | [`harness-card.md`](../../docs/reference/harness-candidates/harness-card.md) | Standing disclosure artifacts with a consumer outside this handoff (`HARNESS_RUN_POLICY.md`). |
| Re-targetability (HS-7) and randomization (HS-10) | [`harness-doctrine.md`](../../docs/reference/harness-candidates/harness-doctrine.md) | Standing criteria, cited by the HS-4 feature map and the improvement loop. |
| Structured-output capability record (HS-13) | [`v1-structured-output-capability.md`](../../docs/reference/v1-structured-output-capability.md) | A kernel + seam capability record, cited by instruments unrelated to selection. |
| Call-verb matrix, five candidates (HS-1g) | [`client-surface-audit.md`](../../docs/reference/harness-candidates/client-surface-audit.md) | The instrument and its results belong together. |

**Closed rows that no longer appear here**, findable by ID in the archive: HS-5 (trainability axis),
HS-6/HS-6b/HS-6c, HS-7, HS-8, HS-10, HS-11, HS-12, HS-14, HS-OD-1, HS-OD-2. IDs are stable and are
never reused.

## Research Intake Update — 2026-09-18 (typed-decision leverage in the harness; operator-directed)

The typed-decision plane measured 11.98x (native id-only) at 15/16 agreement on the worker (n=1; contested — 9.60x at n=4, pending `typed-decision-plane.md` TD-1d.0), and closed-set tool arguments 18/18 exact vs free-form 6/18. Operator directed wiring these into the harness surface. All tasks flag-gated OFF by default; confidence is NOT calibrated, so logging only — no gating (evidence: typed-decision-plane.md, receipts under artifacts/typed_decisions/).

- [ ] **HS-TD-1 — Pre-dispatch classification (risk/intent over a closed set).** One typed decision call per turn classifying request risk/intent; log its answer + confidence beside the harness's permissive/restrictive decision; no gating. Acceptance: shadow log over a real session window with agreement + confidence reported.
- [ ] **HS-TD-2 — Per-turn self-check (noul).** Ask whether the turn satisfied the task before handing back; log confidence, never gate. Acceptance: per-turn cost measured on the worker and a sample of disagreements reviewed.
- [ ] **HS-TD-3 — Context selection as a typed decision.** Choose among candidate files/snippets (closed set) instead of heuristic assembly; deterministic assembly; confidence logged. Acceptance: task-quality A/B vs current assembly on a frozen workload.
- HS-TD-4 (prepared-action envelope and `decision_receipt.v1`) ✅ 2026-09-26 — orch `b19ff1d1`; closed row in the [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md).

**HS-TD-4 consumers:** HS-TD-1/2/3 produce shadow decisions through the envelope; URE-2/2a/3 consume its validation, fallback, timing, and outcome fields; TD-23/24/25 and CJ-15/16 use the receipt for comparable typed-decision evidence; Vidya adapters project the native receipt without granting it authority. Empirical consumers follow the [minimum viable research execution contract](eval-tower-verification.md#minimum-viable-research-execution-contract); HS-TD-4 remains the single implementation owner.

## Research Intake Update — 2026-09-26 (orchestrator prior-art: harness front doors)

- [x] **HS-16 — accept session identity from headers as a FALLBACK on `/v1`, and record the parent.** Resolve `x_session_id` as body → `x-dynamo-session-id` → `X-Session-Id`; record `parent_session_id` from `x-dynamo-parent-session-id` → `x-parent-session-id`. OpenCode sends these natively on every non-`opencode*` provider (`session/llm/request.ts:187-201` at tag `v1.18.31`), including the child→parent link its `chat.params` hook cannot see (audit E7). Add `session_id_source` and `parent_session_id` to `request_keys` only when a header supplied them, so existing golden output is unchanged. Body wins on conflict; log it and flag `session_id_mismatch`. The P0.2 guard keeps its 422 for an OpenCode user-agent with no body key (a header gives identity, not `x_tool_mode`; a plugin-less turn would silently fall into REPL-bridge mode) and accepts header identity for every other trigger. Tests: precedence table, mismatch, a child `task` request carrying `x-parent-session-id`, Dynamo header-only accepted; TTL expiry; a final-signal release; the event-hook finding recorded in `client-surface-audit.md` §1. Lifecycle (intake-1816#4, intake-1816#6): at tag `v1.18.31`, check whether the plugin `event` hook delivers a session idle, end or delete event; if it does, the plugin sends one end-of-session signal (an `x_session_final` body key on a minimal `/v1` request, or an MCP call); in every case per-session orchestrator state keyed by the resolved id expires on an idle-retention TTL (HSF-3's harness-class p99; a predeclared constant until then) and records `session_end_source` (`signal|ttl`). Tool start/end events are not forwarded (declined; ACTING is inferred from response completion). Then update `client-surface-audit.md` §1's header line. Zero inference. [intake-1785#6, intake-1785#2]
  ✅ 2026-10-05 — All 53 session-link/lifecycle fixtures and the 105-test pinned Node suite pass, including explicit end signals, retention TTL, stale and unknown identities; the client hook audit is updated. Off-host run `37284177689`; reviewed source published in orchestrator main `41ab07fc`, with root client changes published at this boundary.
  - Progress 2026-09-27: HS-19a.2 (orch f58db8be, flag v1_subagent_link) built the header-fallback and parent-recording half. Still open here: the lifecycle half (plugin event hook check, x_session_final, session_end_source).
- [x] **HS-17 — keep a queued `orchestrator_chat` MCP call alive, and set the shell's MCP timeout.** OpenCode calls MCP tools with the SDK's 60 s default, reset only by `notifications/progress`, whose message it discards (`mcp/catalog.ts:54-66`, `onprogress: () => {}`); `orchestrator_chat` is a synchronous POST with a 120 s default (`src/mcp_server.py:452`, `:383-406`), and the template sets no MCP timeout, so any call past 60 s dies in the shell. (a) Template: set `mcp.orchestrator.timeout` ≥ the tool's `timeout_s` + 5 s (`packages/core/src/v1/config/mcp.ts:20`), and make the lint require it whenever MCP is enabled. (b) Server: the chat tools emit monotone `ctx.report_progress` (FastMCP 3.3.1) at under half the client timeout while `/chat` is in flight. Any user-visible queue or capacity text goes in the tool RESULT (for example `contention_gate.waited_s`). Acceptance: a fake MCP client with a 60 s timeout and reset-on-progress survives a 90 s call only with (b); the lint refuses an MCP-enabled config with no timeout. Zero inference. [intake-1792#4]
  ✅ 2026-10-05 — All 45 MCP fixtures and the 105-test pinned Node suite pass. Async cancellation/progress preserves a 90-second virtual call; enabled MCP templates require a 125000 ms minimum timeout. Off-host run `37284177689`; reviewed source published in orchestrator main `41ab07fc`, with root client changes published at this boundary.
- [ ] **HS-19 — prepare the harness↔orchestrator INTERFACE discussion for the operator (operator-requested 2026-09-26;
  OP-64).** The design canvas (https://claude.ai/artifact/UnjtMaouUFYs9xz5umnwPd, tension T1 and questions Q1/Q2/Q7)
  leaves three linked questions that no HS-16/17/18 or HS-OD-8/9 item covers. Prepare one decision package with
  options, tradeoffs and a recommendation for each (zero inference), then hold the discussion. It does not reopen
  HS-4's thin-shell / one-router decision:
  - **Operator decisions (2026-09-27, verbatim intent).** (1) The ORCHESTRATOR owns model selection for harness
    subagents; the harness never pins a model. OpenCode's config uses one logical model,
    `epyc-orchestrator/orchestrator`, for `model` and `small_model`; a `task` subagent is just a concurrent request
    to that provider, not a new process. (2) The only pin is `x_force_model`, set by us for evaluation and
    debugging, never by the harness in normal use. (3) Build order: stage 1 Linked → 2 Scheduled → 2.5 shared
    context by pointer → 3 full shared REPLs. Canvas: https://claude.ai/artifact/UnjtMaouUFYs9xz5umnwPd. Stage 1
    was approved and built 2026-09-27; spec
    [`hs19a-linked-subagents-20260927.md`](../../docs/design/hs19a-linked-subagents-20260927.md).
  - [x] **HS-19a — OpenCode's `task` tool as a control interface (T1/Q7).** ✅ 2026-09-27 — stage 1 "Linked" built and live PASS 18/18 (all six children closed). HS-4's template denies `permission.task`,
    sets `subagent_depth` 0 and disables `general`/`explore` so that the orchestrator owns fan-out. The draft
    reconciliation re-enables `task` but lands it in an orchestrator control door (MCP dispatch / attach / read /
    cancel on `src/mcp_server.py`), with the scheduler as the only executor. HS-1c found that `task` re-enters the same
    request pipeline, so plugin hooks and `x_*` stamping still apply. Evidence against relying on it alone: the 27B,
    when offered `task`, never used it (DS41-C20c, n=1). If adopted, the HS-17 timeout and HS-16's parent link become
    prerequisites.
    **Stage 1 "Linked" (operator-approved 2026-09-27): record the subagent tree, change nothing else.** Every piece
    is default-OFF; with it off, live behaviour is byte-identical. Spec:
    [`hs19a-linked-subagents-20260927.md`](../../docs/design/hs19a-linked-subagents-20260927.md).
    - HS-19a.1–.6 all ✅ 2026-09-27: spec, orch link f58db8be (flag v1_subagent_link), opt-in subagents profile, lint, runner, and a live PASS 18/18 (artifacts/harness/hs19a-20260927/). Detail: [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md).
  - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19b — a hierarchy of shared REPLs (Q2).** Today each request gets one isolated REPL. Decide whether a
    child sees a live parent view or a snapshot, who merges what is published upward, and how OAB-12 pull budgets add
    up across levels. Draft: read-only parent views, explicit publish, one accounting tree. The design must rest on
    our own evidence: DeLM-style shared context was overturned in the prior-art dive (intake-1803#record,
    intake-1820#record, intake-1821#record).
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): a REPL hierarchy is fan-out infrastructure, and nothing has yet shown that fan-out beats the strongest model alone; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
  - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19c — generalized scouting: the orchestrator decides to scout.** Scouts (`chat_pipeline/scout_stage.py`)
    run today only when a request lists targets, which in practice means AutoKernel requests only. Decide the trigger
    (a typed advisor, request shape, or retrieval miss), the budget, and how scout results reach the REPL hierarchy.
    Coordinate with INF-78 (OAB-8 scouts) and UFH-12 REPL-EMB-5.1 (the SEARCH primitive); do not fork either.
    **Designed with stage 2 (2026-09-27):** the trigger is the stage-2 gate's `scout` option, the targets come from the
    planner, and the budget and queueing are the dispatcher's. See
    [`hs19-stage2-dispatch-20260927.md`](../../docs/design/hs19-stage2-dispatch-20260927.md) §5-§6. Build task: HS-19d.P3c.
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): generalized scouting is a stage-2 mechanism with no measured value against the thesis baseline; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
  - [ ] **HS-19d — stage 2 "Scheduled": dispatch subagent work (gate → plan → size → select → aggregate; operator-approved
    2026-09-27).** Design: [`hs19-stage2-dispatch-20260927.md`](../../docs/design/hs19-stage2-dispatch-20260927.md).
    - Front door A (`/chat`, or the harness through an MCP tool) runs all five steps. Front door B (OpenCode `task` on
      `/v1`) skips Gate and Plan.
    - The work replaces proactive stage 7.5's heuristic gate, always-architect planner and wave executor, and generalizes
      scout-stage admission from skip to queue. The plan compiles to TaskIR `plan.steps`.
    - Every phase is behind a default-off flag. Belief write side: VB-DISPATCH-S2.
    - ❄ **2026-09-27 (operator, narrowed plan): P1–P6 are FROZEN** (markers on each box); HS-19d.0, the design, stays
      done. P0 was not on the freeze list: it is zero-inference preparation whose only consumers are P1–P6, so it
      ranks behind the UFH-13 thesis experiment. The A0/A1/A2 arms of P5 moved to UFH-13, which runs first.
    - [x] **HS-19d.0 — design note plus the OpenCode source audit per step, and the prior-art check.** ✅ 2026-09-27 — doc §4 (OpenCode `v1.18.31`) and §15.
    - [ ] **HS-19d.P0 — preflight, zero inference.**
      - Offline test: `/v1` passes more than one `tool_calls` through from a canned multi-call response. Also read the
        served templates' `supports_parallel_tool_calls` (llama-server defaults to it; nobody sends `parallel_tool_calls`).
      - Count `task` parts per assistant message in the HS-19a and probe taps.
      - Confirm the tap keeps the emitted tool calls, for the child ↔ tool-call join (doc §12).
      - Build the gate and plan corpus.
      - Wire VB-DISPATCH-S2.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P1 — `epyc.dispatch_plan.v1` schema, validator and TaskIR projection** (doc §7; one test per rule; a GBNF
      round-trip through `response_format`).
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P2 — dispatcher (flag `dispatch_scheduler`).**
      - Readiness dispatch, not waves.
      - Admission generalized from `scout_stage.resolve_cap`, plus a process-wide reservation (the `EmbeddingScheduler`
        pattern).
      - Subtasks that are not granted are queued. Deadline, cancel flag and R2.
      - DAR-LAT-1 `SlotCapacity` when it lands, never a second occupancy model.
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P3a — gate in shadow (flag `dispatch_gate_shadow`).**
      - The typed `dispatch.mode` ∈ {direct, scout, decompose, decompose_consult} is recorded on live `/chat`, and
        nothing changes.
      - τ_gate is re-set from the corpus and the shadow rows.
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P3b — front door A live (flag `dispatch_plan`).**
      - Planner routing: frontdoor by default, the consultant for `decompose_consult`, with the saturation guard.
      - Budget `N_now`/`N_total` goes into the prompt and is enforced in code.
      - Select from the type table plus the saturation skip (DAR-LAT-2 when it lands).
      - Text aggregate. Stage 7.5 stays off.
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P3c — HS-19c scouting through the gate (flag `dispatch_scout`).** `scout` → planner-derived
      `ScoutTarget`s → stage 6.8. Coordinate with INF-78 and REPL-EMB-5.1.
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P4a — front door B Size (flag `v1_subagent_schedule`; needs HS-OD-8/9).**
      - Per-parent in-flight cap keyed by the HS-19a parent link.
      - Pre-stream hold, then 503 with `Retry-After` and `retry-after-ms` (OpenCode `session/retry.ts:47-78`,
        5 retries).
      - Type from `x_agent_name` through typed markdown agents in the subagents profile, with the lint extended.
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P4b — `orchestrator_dispatch` MCP tool (needs HS-17).** The harness reaches front door A with one
      call. This is the orchestrator-driven answer to the 2026-09-27 probe (delegation 0/3 under discretionary guidance).
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P4c — capacity note (flag `v1_capacity_note`).** A fixed, versioned tail note on turns that offer `task`
      ("at most N subagents can run now").
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P5 — eval (inference, coordinated window).**
      - Arms: A0 the strongest model alone (the standing baseline), A1 frontdoor alone, A2 the pipeline, A3 the gate
        forced to decompose, A4 the consultant always planning.
      - Decomposable and control workloads.
      - Pre-register a protocol annex first. Then decide per class, and delete stage 7.5.
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): its A0/A1/A2 arms are now the UFH-13 thesis experiment, which runs first; the A3/A4 decomposition arms wait on its verdict; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.
    - [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **HS-19d.P6 — stage 2.5 pointer results (flag `dispatch_pointer_results`).** Subtask outputs go to the UFH-12
      store; the parent gets `{ref, gist, size}` and pulls on demand. The design goes through HS-19b.
      ❄ FROZEN 2026-09-27 (operator, narrowed plan): stage-2 dispatch build; the design (HS-19d.0) stays done and is the reference if it thaws; unfreeze trigger: the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives. The box stays open: frozen is not done.


**Standing rule.** The orchestrator stays the sole caller of models; no orchestrator feature may depend on MCP sampling (deprecated in protocol 2026-07-28, earliest removal in the first revision released on or after 2027-07-28; never enabled by pinned OpenCode; and OpenCode's only provider is the orchestrator, so "borrowing the harness's model" loops back to us). [intake-1791#0, intake-1791#4]

**Supporting evidence for the HS-4 one-router decision (§ Objective and the HS-4 operator decision under *Prioritized Task List*), no new work.** A decoupled router in front of or beside the orchestrator cannot make the latency-priced mix shift that RouteBalance's four-arm isolation attributes the gain to (intake-1796#2), and interference between routers that independently send to shared instances is open future work (intake-1798#3).

**Dormant triggers (no checkbox until one fires):**
- MCP Tasks for `orchestrator_*` — re-evaluate when an OpenCode release enables the `tasks` client capability (issue 28567; commented out at `mcp/index.ts:47-48`). Tasks absorbs overload, it does not propagate it, and adoption needs fastmcp 3.3.1 → 4.x. [intake-1792#1, intake-1792#4]
- An ACP-shaped `usage_update` from the orchestrator — declined: the orchestrator is not on the ACP wire, OpenCode already computes it from the OpenAI usage block, and it has no load field. [intake-1790#1, intake-1790#4]
- The orchestrator as an ACP proxy/conductor — declined: Draft, in no schema, north of the shell, and proxies cannot touch model parameters. [intake-1790#3]
- A gateway or load balancer in front of `/v1` (intake-1786#record, intake-1800#record; both stage1-unverified) — declined: it is a second router, contrary to HS-4's "one router" (HS-4 operator decision). Reopen only if an adopted shell cannot reach `/v1` directly.
- Harness-side fan-out sizing (intake-1806#record, unverified) — only if HS-4 P4 or a template change re-enables shell subagents (`permission.task`, `subagent_depth`); then the capacity signal is HS-OD-9's `Retry-After` plus HS-16's parent link, not a new hint key.
- Architect→editor split (intake-1794#record, unverified) — only if P0.4 or later live runs show malformed tool calls from a reasoning role; dive the source before citing it.
- Delegation defaults (intake-1793#record, unverified) — HS-4 P4 may consult it when it designs delegation defaults; dive before citing it.
- HS-3 (ACP survey, closed not-triggered; record in the [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md)): reopen the ACP survey only on an operator request for editor/UI interop, a named external client, or ACP gaining inference-routing semantics; `providers/set` does not qualify. [intake-1790#0, intake-1790#4]
- HS-18 (`agent_hints` decline; record in the [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md)): revisit the `agent_hints` alias only if an adopted harness emits it. [intake-1785#2, intake-1785#5, intake-1785#6]

- [ ] **HS19D-P0-DESCRIPTIVE-SOURCE — sanitized source-bound summary of the already committed HS-19a verdict.** Add a bounded fixed-path single-snapshot loader and descriptive per-record parent-task-part/child-task-call counts. Preserve absent emitted-call, tap-retention, served-template and child-to-tool join values as unknown; refuse ambiguous/failed source, symlink/hardlink/FIFO/byte drift. No session IDs/detail strings, private taps, new thresholds or frozen dispatch consumer changes. Parent HS-19d.P0 remains open for its actual broader native-source/template preflight.

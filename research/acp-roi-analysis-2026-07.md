# ACP Integration ROI Analysis — 2026-07 (HS-2)

**Date**: 2026-07-17
**Owner task**: HS-2 in [`../handoffs/active/harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md)
**Depends on**: A4 / HS-1 cooperation-surface audits (Hermes HS-1b, OpenCode HS-1c) — landed 2026-07-17
**Status**: analysis + recommendation only. **The ACP adoption / HS-4 harness-selection DECISION stays with the operator.**
**Reopens**: intake-263 "MCP-first, ACP = editor-agent-not-inference" lean, under the unchosen-harness framing.

---

## 1. Question

Is adopting **ACP (Agent Client Protocol)** as *the* integration standard for the Orch↔harness relationship worth it — **given A4's finding that both leading open candidates (Hermes, OpenCode) already cooperate with the orchestrator via request-body injection today, at ~0 patch cost**?

The plan framed the upside as: *high ROI would widen the candidate set to all ACP-speaking open harnesses (triggering HS-3), rather than committing to Hermes/OpenCode native surfaces; low ROI keeps the native surfaces.* This analysis tests that framing against the layer model and A4's evidence.

## 2. The load-bearing prior finding (A4 / HS-1)

A4 verified in `epyc-orchestrator` that **the orchestrator's cooperation contract is BODY-based**: all five `x_*` overrides are JSON **body** fields on `OpenAIChatRequest` (`src/api/models/openai.py:63-82`), consumed off the parsed request model (`src/api/routes/openai_compat.py:396-397,455-459`). The only HTTP header the API reads is the `x-task-id` observability tag (`src/api/__init__.py:334`) — **there is no header→override path**. Consequences A4 recorded:

- **Body injection works today**: Hermes `extra_body` (via the landed `pre_llm_call` plugin), OpenCode `chat.params.options` / config `options.body`.
- **Header-based passthrough would need a new server-side header→override shim** (OpenHands `extra_headers`, OpenCode `chat.headers`).
- Both leading candidates are **SUFFICIENT** on the cooperation surface with **no core fork** (Hermes: ~0 new code beyond the already-landed EPYC plugin; OpenCode: one small first-party plugin + config).

This is the fact that reframes HS-2.

## 3. The layer model — where ACP actually sits (the crux)

The Orch↔harness↔user stack has **two distinct protocol layers**, and the harness sits between them:

```
   USER / EDITOR / GUI                         (north-facing)
        │
        │   ┌──────────────────────────────────────────────┐
        │   │  NORTH surface: client ↔ agent               │
        └───┤    • ACP (Agent Client Protocol)             │
            │    • session new/load/fork/cancel, streaming │
            │      updates, permission prompts, slash cmds,│
            │      file-access callbacks                    │
   HARNESS  │  ── this is a UI / editor-driving protocol ──│
 (Hermes /  └──────────────────────────────────────────────┘
  OpenCode) ┌──────────────────────────────────────────────┐
            │  SOUTH surface: agent ↔ inference backend    │
        ┌───┤    • /v1/chat/completions + x_* (BODY)        │
        │   │    • MCP (tool/context provider)             │
        │   │  ── this is where cooperation happens ──     │
        │   └──────────────────────────────────────────────┘
        │
   THE ORCH (layer A: kernels, MTP, eval tower, scoring)   (south-facing)
```

- **ACP is a north-facing, editor↔agent protocol.** It standardizes how a *client/UI* (Zed, JetBrains, a management GUI, Local Studio Pi) drives an *agent process*: session lifecycle (create/load/**fork**/cancel), structured streaming callbacks (thinking / tool-progress / message chunks), permission requests, slash commands, workspace file-access. intake-263 pins it exactly: *"ACP is the open standard for AI agent-**editor** integration"* (launched Sep 2025; JetBrains co-lead Feb 2026), and its 2026-04-06 deep-dive downgrade reads *"ACP is editor-agent protocol, **not inference**."* The one concrete ACP server we hold locally is OpenGauss's `acp_adapter/server.py` (session CRUD/fork/cancel, provider-based runtime credentials, ThreadPool agent execution, 7 slash commands — `research/deep-dives/opengauss-architecture-analysis.md` §6), and it is a **north** adapter bolted onto the hermes-agent core.

- **The orchestrator's `/v1/chat/completions` + `x_*` (body) is the south-facing, agent↔inference contract.** This is where layer-(B) deference is injected (A4). It is OpenAI-compatible and every open harness already speaks it via an OpenAI-compatible model client.

- **MCP is also south-ish** — a tool/context provider protocol. The orchestrator already ships an MCP server (the `mcp__orchestrator__*` tool surface: `orchestrator_chat`, `query_benchmarks`, `list_roles`, `route_explain`, …). "MCP-first" is therefore already the **de-facto** posture, not an aspiration.

**Key consequence: ACP and the cooperation contract are at DIFFERENT layers.** Cooperation (routing/compaction/escalation deference) is injected on the **south** model-client call (the `/v1` body). Whether a harness *also* speaks ACP on its **north** surface changes nothing about that injection. ACP is neither necessary nor sufficient for a harness to defer to the Orch.

## 4. Decomposing the ROI

### 4.1 Does ACP reduce cooperation cost? — **No.**
Cooperation cost is already ~0 (A4): body injection on the `/v1` call, no fork, for both leading candidates. ACP operates one layer north of that call and does not touch the model-client body. Adopting ACP cannot lower a cost that is already ~0, and would *add* cost: standing up / committing to an ACP server (either on the Orch or the harness) is net-new code and a net-new protocol surface to maintain and secure.

### 4.2 Does ACP widen the *cooperating*-candidate set? — **No; it widens the wrong axis.**
The plan's upside hypothesis ("widen to all ACP-speakers") only holds if ACP were the cooperation surface. It is not. The axis that actually determines whether a harness *can* cooperate is **"has an OpenAI-compatible model client whose request body we can reach"** — and that axis already spans the entire open-harness field (Hermes, OpenCode, OpenHands, Aider, Continue, …). "Speaks ACP" is an orthogonal, strictly smaller and differently-shaped set (Zed, OpenGauss-via-adapter, community adapters). Selecting on ACP membership would **narrow** the useful field, not widen it, and would filter on a property irrelevant to deference.

### 4.3 What would ACP genuinely buy? — **A "bring-your-own-editor" UI axis we have no demand for.**
The legitimate value of ACP is UI/DX interop: a user could point *any* ACP-speaking editor (Zed, JetBrains, Local Studio Pi / intake-833) at an Orch-cooperating agent and get session forking + structured streaming + permission prompts "for free." That is a **north-facing UI feature**, not a cooperation feature. Against it:
- The project explicitly has **no bespoke-harness / no bespoke-UI ambition** (intake-426: a coding harness is ~98.4% plumbing / ~1.6% AI logic; the standing recommendation is *do not build a bespoke harness* and keep layer A orthogonal). The multi-platform gateway / GUI is already logged **low priority**.
- Deployment is **single-user** (multi-user auth is itself a deferred LOW row). There is no measured "I want to drive this from Zed" demand.
- It collides with **orthogonality principle #2** (the backend moat stays headless / UI-less and human-amendment-only). Making a UI-facing protocol *the* integration standard pulls a north-facing concern down into the deliberately UI-less backend boundary.

### 4.4 Is ACP a one-way door? — **No; it is cheaply deferrable.**
If a concrete bring-your-own-editor need appears later, ACP can be added as an **optional, harness-local north adapter** *after* HS-4 picks a harness — with **zero impact on the cooperation contract**. Hermes/OpenGauss already ships `acp_adapter/`; OpenCode could add one; a standalone `claude-acp-server`-style bridge (intake-263) exists as prior art. So ACP is a **Path-B, revisit-on-demand** capability, never a prerequisite. Committing to it now buys nothing and forecloses nothing.

## 5. Re-opening the intake-263 lean under the unchosen-harness framing

intake-263's "MCP-first, ACP = editor-agent-not-inference" lean predates the unchosen-harness framing, so the plan correctly asks whether that framing flips it. **It does not — A4 sharpens it.** The unchosen-harness framing might have argued *"a protocol standard would let us stay harness-agnostic."* But A4 shows we are **already** harness-agnostic at the layer that matters: the OpenAI-compatible `/v1` body is the universal cooperation surface, and the whole open field speaks it. A protocol standard is therefore not needed to preserve agnosticism; the body contract already provides it. ACP would add a *second*, UI-layer standard that does not carry the cooperation semantics and would entangle the backend boundary with a frontend protocol. Net: the unchosen-harness framing **strengthens** MCP-first + `/v1`-body-injection as the cooperation contract, and leaves ACP as an optional north adapter.

## 6. Recommendation (input to HS-4; decision is the operator's)

**ACP-ROI verdict: LOW.** Do **not** adopt ACP as *the* integration standard, and do **not** trigger HS-3 candidate-widening on a *cooperation* rationale. Specifically:

1. **Keep the cooperation contract = `/v1/chat/completions` + `x_*` (body) + MCP for tools.** This is already universal across open harnesses and already ~0-cost per A4. (MCP-first is already de-facto: the orchestrator ships an MCP server today.)
2. **Treat ACP as an OPTIONAL, harness-local, north-facing Path-B adapter** — a bring-your-own-editor capability to be added *after* HS-4, *only* if a concrete editor/GUI-interop demand materializes. It never becomes the cooperation contract and never gates harness selection.
3. **Do NOT expand the candidate set to "all ACP-speakers."** Keep HS-3 dormant on cooperation grounds; the useful width axis is "OpenAI-compatible body-reachable," which Hermes + OpenCode + the wider field already satisfy. HS-3 should fire only if the operator opens a *UI-interop* line of inquiry (a different objective than cooperation), which is an operator call.
4. **What would flip this to HIGH ROI** (revisit triggers, none present today): (a) an operator decision to ship a bring-your-own-editor / management-GUI product surface; (b) a concrete external client (e.g. Zed, JetBrains, Local Studio Pi) the operator wants to drive the stack from; (c) ACP evolving to carry inference-routing semantics (it does not today — it is editor↔agent). Absent these, ACP stays Path-B.

**HS-4 selection (Hermes vs OpenCode vs an ACP-speaker) remains OPEN and is the operator's.** This analysis only removes the "adopt ACP as the standard / widen to all ACP-speakers" arm from the cooperation-driven decision path; it does not choose a harness, and it does not touch the orthogonality posture or the open-source requirement (both operator-owned).

## 7. Evidence base

- A4 / HS-1 findings — `../handoffs/active/harness-selection-and-integration.md` (cross-candidate body-contract finding) + `../handoffs/active/hermes-outer-shell.md` "Client Surface Audit — 2026-07-17 (HS-1b)".
- Orchestrator body contract — `epyc-orchestrator/src/api/models/openai.py:63-82`, `src/api/routes/openai_compat.py:396-397,455-459`, `src/api/__init__.py:334`.
- ACP as editor↔agent protocol — intake-263 (`claude-acp-server`; "does not change our MCP-first integration strategy"; 2026-04-06 downgrade: "editor-agent protocol, not inference"); OpenGauss `acp_adapter/server.py` — `research/deep-dives/opengauss-architecture-analysis.md` §6.
- "Don't build bespoke harness / 98.4% plumbing" — intake-426. Orthogonality principle #2 — harness-selection index Cross-Cutting Concerns.
- ACP-speaker candidates (for a *future* UI line only) — intake-833 (Local Studio Pi), intake-827 (grok-build, closed → excluded), Zed.

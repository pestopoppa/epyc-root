# HS-4 Harness-Selection Decision Package — 2026-09-16

**Owner handoff:** [`handoffs/active/harness-selection-and-integration.md`](../../handoffs/active/harness-selection-and-integration.md) → HS-4
**Prepared by:** `sub-hs4`. This is a zero-inference analysis: no request was sent, nothing was built, and no process was touched.
**Status:** DECISION PACKAGE. The choice belongs to the operator (the handoff's Reporting Instructions: "Any change to the orthogonality posture … is an operator decision").
**Contract:** [`agents/shared/OPERATING_CONSTRAINTS.md` → Operator Decision Requests](../../agents/shared/OPERATING_CONSTRAINTS.md#operator-decision-requests).

## 1. Context

HS-4 is still open. Every input it waits on is now in place:

- HS-1 (b/c/d, then HS-1g on 2026-09-16) audited cooperation for all five open candidates.
- HS-2 returned a LOW ROI for ACP. HS-3 was therefore not triggered.
- HS-6b/HS-6c published the Harness Card.
- HS-13 recorded the structured-output seam.

The one input still missing is HS-1f.1, a single live request (see §7). The choice cannot be made autonomously: it fixes which foreign runtime and layer-(B) loop the stack will live beside, and the handoff reserves that to the operator.

### The exact question HS-4 asks

> **HS-4 — Harness-selection decision gate:** Hermes vs OpenCode vs an ACP-speaker, gated on HS-1 + HS-2. Default outcome preserved: (A) stays orthogonal; no bespoke harness unless a specific research-demo differentiator justifies it.

Since that line was written, the field has grown. HS-5 folds in oh-my-pi (omp), HS-1e folds in deepseek-harness (dsh), and HS-1f adds `earendil-works/pi`. The "ACP-speaker" arm is closed on cooperation grounds: HS-2's verdict is LOW, and HS-3 was not triggered. That arm reappears only as a dormant UI adapter. Neither the orthogonality default nor the "no bespoke harness" default is in question here.

### The primary axis, and what does not count

- **Primary axis:** cooperation. The test is whether every *default* egress honours a config-declarable top-level body key on `/v1/chat/completions`. The orchestrator reads `x_*` from the **body** only (`epyc-orchestrator src/api/models/openai.py:63-82`; HS-1 cross-candidate finding).
- **Secondary axes:** orthogonality / minimum imports, and HS-7 re-targetability.
- **Excluded from selection:**
  - Trainability. HS-5b binds it as strictly downstream: freeze the harness first, then train.
  - External benchmark numbers (HS-4a/b/c, HS-14). These are OBSERVATION grade and are listed in §5 only as context.

## 2. Evidence matrix

The HS-1g column records the call-verb check. Its source is the matrix under HS-1g in the owner handoff, with pins `repo@sha path:line` in each cell.

| | OpenCode `4bffbb6` | earendil-works/pi `ceea48f5` | oh-my-pi `37eee719` | Hermes `532a49f1` | dsh `0d1f5000` |
|---|---|---|---|---|---|
| **HS-1g: default egress honours the lever** | **All paths.** Main loop, compaction and `task` children use `streamText`. Keys land top-level (`openai-compatible-chat-language-model.ts:231-240`). | **All in-tree paths.** Main loop and compaction use the simple verbs (`core/sdk.ts:314/324`, `compaction.ts:594-597`). Extensions must avoid `ModelRegistry.stream()/complete()`. | **All paths.** `compat.extraBody` is merged independently of the verb (`openai-shared.ts:717-722`). | **Main loop only.** The compressor (`context_compressor.py:346-355`), the iteration-limit summary (`run_agent.py:5297-5350`), `flush_memories` (`:4497`) and `delegate_task` children (`delegate_tool.py:207`) all bypass `extra_body`. | **No lever on the pi-ai route** (`config.ts:254-335`). Only the native `llm-deepseek` route has one. |
| **Lever** | `chat.params` plugin, or per-model `options` | `models.json` `samplingParams`, with no code | `compat.extraBody`, with no code | `pre_llm_call` plugin (already landed) | a schema/materializer patch (HS-1e) |
| **Silent-no-op traps** | camelCased models.dev `provider.body`; provider-level `options`; `agent create` / `generateObject`; the title call's `smallOptions` | low-level registry verbs; `samplingParams` on non-completions providers | `providerOptions`; v2 remote compaction (Responses API only) | the four bypasses above | nested `chatTemplateKwargs` |
| **Own layer-(B) loop** | `compaction.auto` (can be switched off); static per-agent model; depth-limited `task` sub-agents (can be gated) | static model; no sub-agents; `compaction.enabled=false` disables threshold and overflow folding (HS-1f) | 10 intent roles with `retry.fallbackChains` (HS-1d), which is **a second model router**; deterministic `snapcompact` (HS-5); a large feature surface (`advisor/`, `autolearn/`, `autoresearch/`, `goals/` under `packages/coding-agent/src/`) | large: compression, memory, `delegate_task`, iteration summaries; every part needs config or toolset gating | its own loop with typed in-process interception (intake-1186#record) |
| **Orthogonality / minimum imports** | medium | **strongest audited** (HS-1f) | weakest of the three open TS shells (its own router, largest surface) | weak (heavy loop); HS-4b token shape of 139.7K tokens / 22.6 turns, a shape only, `intake-1332#record` | medium |
| **MCP (HS-2 tool contract)** | yes: `packages/opencode/src/mcp/`; ACP too (`src/acp/`) | **no core MCP** (HS-1f) | yes (`packages/coding-agent/src/mcp/`) and ACP (HS-1d) | yes: `tools/mcp_tool.py`; ACP via `acp_adapter/` | not audited |
| **Permission / sandbox** | `ask\|allow\|deny` gate. `external_directory` defaults to ask, and `opencode run` auto-rejects asks. Bash arguments are not path-gated, so the layer is **porous but real** (`intake-1353#02`). | **none**, so it must be containerised (HS-1f) | not audited here | toolset gating; no audited sandbox | not audited |
| **Headless / eval fan-out** | `run --format json` (`cli/cmd/run.ts:176-178`) | SDK/extension; not audited as a CLI JSON stream | NDJSON RPC plus Node SDK (HS-1d) | batch runner (in-language) | not audited |
| **HS-7 policy-document surface** (surface only; see §8) | `{agent,agents}/**/*.md` agent files (`config/agent.ts:13`) plus `AGENTS.md` (`session/instruction.ts:61-65`) | `SYSTEM.md`/`APPEND_SYSTEM.md` (`core/resource-loader.ts:1024`) plus `AGENTS.md` (`:72`) | not audited | `AGENTS.md`/`SOUL.md` discovery (grep-level only) | not audited |
| **Supply chain / ops** | MIT; Bun/TS | MIT; Node/TS; install ping plus update check (`PI_OFFLINE=1`); heavy churn (pin v0.85.1); new-contributor PRs auto-closed, so patches live in extensions | MIT; advertised install is `curl \| sh` from omp.sh, not a signed release (intake-1149#record); prefer npm/Homebrew/Nix | MIT; Python (in-language); pin audit still open (hermes-outer-shell P2.6) | MIT; TS; HEAD already pins pi-ai 0.85.1 (the HS-1g correction to HS-1e) |
| **Integration already built** | none (one small plugin plus config) | none (config) | none (config) | **plugin landed** (`scripts/hermes/plugins/epyc-orchestrator-overrides/`) | none |
| **Trainability (HS-5; not a selection criterion)** | first-party `opencode_env` plus a TRL AsyncGRPO example; the training half is infeasible on the current host | none | none | none | none |

**Shared seam facts (these apply to whichever option is chosen):**

- `:8000` refuses `response_format` with a 422 **by decision** (HS-OD-1, orchestrator `cbe551e8`).
- The frozen kernel *can* do grammar-constrained JSON (HS-13).
- A harness that uses OpenAI JSON mode therefore gets a diagnostic, not prose. Wiring JSON mode is a small orchestrator task, filed only if the selected harness needs it.
- `max_tokens ≤ 32768` (`openai.py:90`).
- Backend failures are real HTTP errors (HS-OD-2).

## 3. Options

### Option A — OpenCode

- **What it entails:**
  - One first-party `chat.params` plugin that injects `x_*`, or per-model `options`.
  - `opencode.json` with `baseURL=…/v1`.
  - `compaction.auto:false`.
  - Every agent pointed at the single orchestrator model.
  - `task` either kept (it honours the lever) or denied.
  - `run --format json` for the eval fan-out.
- **Evidence:** HS-1c and the HS-1g row. The top-level-vs-nested caveat is settled at source.
- **Integration cost:** LOW, with no core fork. The recurring cost is operating a Bun/TS runtime.
- **Risks:**
  - The permission layer is porous (bash arguments are not path-gated), so runs still need a container or worktree jail.
  - Trap: models.dev camelCasing. Use custom-provider mode.
  - The title/`agent create` side calls do not carry overrides. They are auxiliary, but they are still requests that `:8000` routes by default.
  - Its own compaction must stay off.
- **Reversibility:** high. All of the above is config plus one plugin.

### Option B — earendil-works/pi

- **What it entails:**
  - A `models.json` custom provider that uses the built-in llama compat flags (`provider.ts:63-70`). Do not use the router-mode-only llama provider (`extensions/llama/client.ts:192`).
  - `samplingParams` carries `x_*`.
  - `compaction.enabled=false`.
  - `PI_OFFLINE=1`.
  - Pin v0.85.1.
  - Container mandatory.
- **Evidence:** the HS-1f source score and the HS-1g row (`intake-1360#record`, `intake-1350#record`).
- **Integration cost:** the lowest cooperation cost (zero code), but the highest *surrounding* cost:
  - no core MCP, so the HS-2 tool contract needs an extension;
  - no permission system, so a container is mandatory;
  - upstream churn, and patches must live in extensions;
  - extensions must use the simple verbs.
- **Risks:**
  - HS-1f.1 is still unrun. The source predicts `store` is ignored (pydantic `extra='ignore'`, `openai.py:41-46`) and `stream_options` is accepted (HS-OD-1). Whether `strict:false` inside tool definitions is accepted is not verified.
  - The install ping and update check must be disabled.
- **Reversibility:** high.

### Option C — oh-my-pi (omp)

- **What it entails:**
  - `models.yml` with `compat.extraBody` (config only).
  - Install via npm/Homebrew/Nix, never `curl | sh`.
  - Its 10-role `retry.fallbackChains` must be collapsed to the single orchestrator model, or it competes with orchestrator routing.
- **Evidence:** HS-1d (the strongest config surface at the time) and the HS-1g row. The HS-5 facts are the unsigned install path and the deterministic `snapcompact`.
- **Integration cost:** LOW for cooperation. It is MEDIUM for containment, because the feature surface to audit and disable is large.
- **Risks:**
  - It imports a second router and a large autonomous-feature surface. That is Cross-Cutting Concern 1 instantiated.
  - Supply-chain posture.
  - The `providerOptions` trap.
- **Reversibility:** high.

### Option D — Hermes

- **What it entails:**
  - `compression.enabled:false`.
  - `delegate_task` gated off.
  - A small plugin/core patch that routes the iteration-limit summary and `flush_memories` through the override lever.
  - The pending upstream pin bump (hermes-outer-shell P2.6).
- **Evidence:** HS-1b, HS-1g (a correction: the "≈0 patch" call holds only with that gating) and `hermes-outer-shell.md` → Call-verb check (that handoff is now [closed](../../handoffs/completed/hermes-outer-shell.md); the check lives in [`client-surface-audit.md`](../reference/harness-candidates/client-surface-audit.md)).
- **Integration cost:**
  - LOW to start: the plugin is already landed, and the code is in-language (Python).
  - The recurring cost is keeping a small patch alive on a fast-moving upstream.
- **Risks:**
  - Four default-path bypasses. Any that are left ungated are silent (the HS-1g class).
  - The heaviest layer-(B) import.
  - The largest token shape in the one external measurement (a shape only).
- **Reversibility:** high. The integration already exists and can be shelved.

### Option E — deepseek-harness (dsh)

- **What it entails:** one of two routes.
  - **Route 1:** the ~4-edit, with-the-grain patch (HS-1e): `samplingParams` in `PiAiModelProfile` and `modelFields`, carried through the materializer. The pin bump is already done upstream.
  - **Route 2:** the native `llm-deepseek` route, whose `request-extensions` do reach the body.
- **Zero-code fallback:** `compat.chatTemplateKwargs` (`catalog.ts:246`), which lands **nested**. Using it needs a ~10-line reader on the orchestrator side. Present it only as an option; do not adopt it.
- **Integration cost:** MEDIUM, because it is a fork-maintained patch until upstream accepts it.
- **Risks:**
  - Nothing exposes a lever today.
  - It is unverified whether an `x_*` field needs a `DeepSeekLlmApiExtensionMap` entry.
- **Reversibility:** medium.

### Option F — Defer

- **What it entails:** HS-4 stays open. The stack keeps serving `/v1` to whatever client calls it.
- **Cost:** none now. The deferred costs are:
  - HS-5b's ordering constraint (freeze before training) blocks any harness-side trainability work;
  - UTM-P1 pairing keys and the cross-harness bake-off (HS-14) have no target;
  - each upstream keeps drifting from the pinned SHAs above, so the source audits go stale.
- **Risk:** the audits decay at upstream churn rates (pi is the fastest). In practice, a deferral of more than a few weeks means re-running HS-1g.
- **When deferring is right:** only if the operator has no concrete frontend demand yet. The handoff's own framing is that (B) pays off only once a harness cooperates.

**ACP-speakers are not an option.** They are dormant per HS-2/HS-3. They can be re-opened only on a concrete editor/UI demand, and then as a harness-local north adapter. OpenCode, omp and Hermes/OpenGauss already ship one.

## 4. Sandboxing — applies to every option

The HS-6c conformant card discloses that the tower has:

- no substrate isolation for the REPL or scorer (undisclosed field 1);
- no eval-wide network-off switch (field 2);
- **auto-approve** (field 13; `approval_gate.py:80-89`).

Two consequences follow.

1. **Any cross-harness comparison on this tower is locked-harness only** (the paper's admissibility rule, recorded under HS-6c). A bake-off may vary the client harness only while the server-side tower configuration is held fixed and disclosed per run (HARNESS_RUN_POLICY "applicable Harness Card").
2. **No candidate supplies a sandbox we can rely on.** pi has none. OpenCode's is porous. omp, Hermes and dsh are not audited. Whatever is selected runs inside a container or jail that the operator provisions. The harness's own permission layer is defence in depth at most.

## 5. External context — context only, never selection evidence

All rows below are OBSERVATION grade under MEASUREMENT.md. None of them may rank a candidate.

- **HS-14(a):**
  - Harness rank tracks model class: Spearman −0.05 (GLM-5.2 vs Gemma-4-26B) and +0.76 (Gemma-4-26B vs Muse-Glimmer-30B).
  - On Muse-Glimmer: opencode 41.3%, qwen-code 40.0%, pi 37.3%, hermes 24.7%. The model is not servable on v9, and harness versions are unstated.
  - Sources: `intake-1352#record`, `intake-1363#record`.
- **HS-14(b):** with thinking off, crush/opencode/pi lose about ⅔ of their score. Our roles run with `enable_thinking=false`, so thinking-on rankings do not transfer (`intake-1352#02`).
- **HS-14(c):** the OpenCode permission facts used in §2 (`intake-1353#02`).
- **HS-14(d):** a harness search on GPT-OSS-20B moved stock OpenCode from 4.8% to 14.8%. The run artifacts are unpublished, and per-fix attribution is noise-sized (`intake-1351#record`, `intake-1362#record`).
- **HS-4a/b/c:** a pointer, a token shape, and selection vocabulary respectively. None of them contributes a number (`intake-1320#record`, `intake-1332#record`, `intake-1335#record`).

**The local bake-off, if run after selection (it needs inference and a region claim):**

- served models at production `enable_thinking`;
- columns: pass@1, input tokens per attempt, prefix-cache hit share, and prefill tokens per solved task (`intake-1363#02`).

## 6. Recommendation

**Option A — OpenCode.** Name pi (B) as the minimal-import alternative.

Reasoning:

- OpenCode is the only candidate that satisfies all of these at once:
  - every default egress honours the lever;
  - native MCP, which is the HS-2 tool contract;
  - a real (if porous) permission layer;
  - first-class headless JSON for eval fan-out;
  - config-only switches for each of its layer-(B) behaviours.
- pi wins on orthogonality, but three gaps cost it:
  - it would need an MCP extension;
  - it would need a mandatory container with no in-harness defence at all;
  - it has the fastest-churning upstream, which rejects outside patches.
- omp's cooperation surface is as good as OpenCode's, but it imports a competing router and the largest autonomy surface.
- Hermes needs a patch that is maintained indefinitely on four silent paths.
- dsh needs a patch before it cooperates at all.

**Tie-break fact.** The tie between A and B turns on one question: *must the frontend consume the orchestrator's tools over MCP natively?*

- If yes, choose A.
- If the server-side REPL tools are enough, and the harness's own file/bash tools run in a container anyway, B's orthogonality advantage becomes decisive and B is the pick.

## 7. Evidence that would need inference

- **HS-1f.1:** one live pi request with `samplingParams` `x_*` keys against `:8000`. It confirms top-level arrival and whether `store`, `strict:false` and `stream_options` are tolerated.
- **HS-1c residual:** one live OpenCode request to confirm top-level `x_*` arrival. The source already settles this.
- **HS-14:** the local bake-off (§5).

**Can the decision be made without them? Yes.**

- The call-verb question these requests would answer is already settled at source for every candidate, with pinned `path:line` evidence.
- The seam's field policy is known from source (HS-OD-1; `openai.py:41-46`).
- The live requests are **acceptance checks for the chosen harness**, not discriminators between candidates:
  - If B is chosen, HS-1f.1 becomes a gate *before adoption*, not before the decision.
  - If A is chosen, the one OpenCode request plays that role.
- The bake-off happens after selection by construction: HS-5b requires the harness to be frozen first.

## 8. What the decision then requires (HS-5 / HS-5b and follow-through)

- **HS-5 (fold omp into the packet)** is satisfied by §2 and §3-C. **HS-1e** (fold dsh) is satisfied by §3-E. **HS-14** (external rows) is satisfied by §5.
- **HS-5b (binding ordering):** freeze the selected harness at a pinned SHA *before* anything is trained or tuned against it. A harness or tool-schema change afterwards discards the training (`intake-1323#record`, `intake-1339#record`). Editor-side trainability is scored only after that freeze.
- **HS-7:** the criterion is not yet fully scored for any candidate. §2 shows document-based policy surfaces exist for A and B, but HS-7 also requires two further steps at acceptance: identify the policy-document version and a separate model-adaptation manifest, then republish the Harness Card for the realized configuration. That scoring is zero-inference work for the chosen candidate.
- **Per-option follow-through:**
  - **A:**
    - write the `chat.params` plugin (it must use custom-provider mode);
    - pin `4bffbb6` or a re-audited successor, re-running the HS-1g check on any bump;
    - set `compaction.auto:false`;
    - decide keep-or-deny for `task`;
    - make a container/worktree jail;
    - send the one live acceptance request.
  - **B:**
    - write the `models.json` custom provider and pin v0.85.1;
    - set `PI_OFFLINE=1` and `compaction.enabled=false`;
    - write an MCP extension that uses only the simple verbs;
    - make the container mandatory;
    - run HS-1f.1 before adoption.
  - **C:**
    - install from a signed channel;
    - collapse the fallback chains;
    - audit and disable the autonomy surface;
    - make a container.
  - **D:**
    - bump the pin (P2.6);
    - apply the config gating;
    - patch the summary and memory-flush paths;
    - re-run HS-1g at the new pin.
  - **E:**
    - apply the HS-1e patch or switch to the native route;
    - send one live request.
- **Cross-cutting, for every option:**
  - UTM-P1 pairing keys (`unified-trace-memory-service.md`) before any second harness goes live;
  - HS-6 contract rewording ("capability, not field name");
  - a JSON-mode seam task only if the chosen harness uses `response_format`;
  - update this index's Status line and the candidate leaf handoffs (Reporting Instructions).

## 9. Default if the operator makes no choice

Option F. HS-4 stays open, and nothing is installed. After about 4 weeks, or on any upstream major bump, the HS-1g matrix is re-run before this package is re-presented.

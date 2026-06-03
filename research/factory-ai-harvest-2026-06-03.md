# Factory.ai (Droid) Feature-Mining Harvest — 2026-06-03

**Source**: `docs.factory.ai` (Mintlify; mined via `/llms.txt` index → ~110 English pages, fetched as raw `.md`) + `factory.ai/news/code-review-benchmark` + the released eval repos.
**Method**: `/research-intake` deep-dive — 7 parallel sub-agents over 5 doc clusters + 2 focused deep-dives (code-review benchmark, earlyoom).
**Intake entries**: [intake-657] choosing-your-model, [intake-658] code-review-benchmark, [intake-659] earlyoom.
**Framing** (per user directive + `feedback_feature_mine_closed_source_competitors`): harvest reproducible mechanisms for our CPU orchestrator / autopilot / eval-tower / routing / KB stack. Open-source-only governs *deploy*, not *analyze*. SaaS-only items are flagged and excluded from the backlog.

> **Verification caveat**: per-page extraction used the WebFetch summarizer model. Version-numbered model names ("GPT-5.2", "Opus 4.7") and exact score decimals are *reported-by-Factory* and should be re-verified against the live page before being cited as load-bearing in a handoff. The mechanisms (the harvestable part) are robust.

---

## Part 1 — Corrections to the initial (Phase 1+2) intake reads

1. **[intake-657] "Factory model selection is fully MANUAL, no auto-routing" — WRONG/STALE.** Factory ships **Factory Router** (`/web/factory-router.md`), an opt-in automatic per-task model router (Research Preview): *"a per-task router that uses a mix of **session and per-request** routing"*, which *"strongly considers **prompt cache** maintenance and savings in its optimization,"* claiming *"frontier-level performance … while **reducing costs roughly 20–25%** vs always using top-tier models"* (validated on Terminal Bench 2 + Legacy Bench; mechanism learned-vs-rule undisclosed). Manual `/model` is the *default* UX; auto-routing *exists* but is opt-in/preview. This is the single most valuable correction — it gives us a validated external design + a concrete savings target to benchmark our learned router against.

2. **[intake-658] code-review benchmark — "open source" overstated + provenance + judge corrections.**
   - **Provenance is Greptile → Augment → Factory**, not Factory-original. Greptile public benchmark (5 repos × 10 PRs, **1 golden bug/PR**) → Augment (`ai-code-review-evaluations`) expanded to **v1 = 145 bugs** → Factory mirrored into `droid-code-review-evals` org and re-expanded to **v3 = 167 bugs** (removed v1 false-positives, **added 31 bugs that Droid itself surfaced** then human-validated — a self-curation bias vector).
   - **"Open source" is overstated**: the harness repo `droid-code-review-evals/review-droid-benchmark` has **NO LICENSE file** (all-rights-reserved by default), and the **v3 golden set the scoring actually reads is gitignored / not in the repo**. Only Augment's upstream **v1 (145 bugs)** at `ai-code-review-evaluations/golden_comments` is genuinely open + reusable.
   - **Judge model = `claude-opus-4-6`** (hardcoded, Anthropic SDK `anthropic==0.76.0`, `max_tokens=500`), NOT "Sonnet 4" as one doc summary implied. Trust the code.
   - **Not API-runnable against arbitrary models**: the review step is driven by Factory's closed **Droid Action** via `@droid review` on real GitHub PRs (whole-repo agentic context), not a model-agnostic prompt/diff call. Only the **judge/scoring half** + v1 data are portable.
   - **Low-severity golden comments are scored as neither TP/FP/FN** (excluded) — load-bearing methodology detail, inherited from Augment.
   - Standardization: **reasoning_effort = High for all 13 models**, **3 runs each** (malfunction runs excluded), **micro-averaged** P/R/F (sum TP/FP/FN across all PRs, then compute — not mean of per-PR F1).

3. **[intake-659] earlyoom — refined against the LIVE box (2026-06-03)**: live inventory flipped two assumptions (see the [`earlyoom-oom-protection.md`](../handoffs/active/earlyoom-oom-protection.md) stub for the authoritative, verified recipe). (a) **NOT swapless** — there's a vestigial 8 GB `/swap.img`; with the default `-s 10`, earlyoom's *mem-AND-swap* condition would **never fire** (swap stays ~100% free), so force **`-s 100,100`** (percent) to mem-gate. (b) **`oom_score` is nearly flat** here (133 GB server=742 vs 28 MB orchestrator=666), so default oom_score selection is unsafe → use **`--sort-by-rss`** (deterministic) — NOT for the gameability reason (#344) first cited. Control plane is `comm=python` (6 uvicorn workers @ ~1.1–1.26 GB each — NOT safe by RSS-smallness, and `--ignore` doesn't cover them; they collide with runaway python evals) → protect with **`oom_score_adj=-1000` EXACTLY** (earlyoom's `is_larger()` skips −1000 in BOTH oom_score and `--sort-by-rss` modes, verified in `kill.c`; −900 does NOT work). Production servers + embedders = `comm=llama-server`; only bench binary built is `llama-bench`; managed image svc = `sd-server`. **Victim policy decision**: under `--sort-by-rss` only `--ignore` (hard) can protect the 13–133 GB servers (`--avoid`'s −300 is negligible) → `--ignore '^(llama-server|sd-server)$'` culls non-model runaways (Policy A, recommended) vs no-ignore = kill biggest server to relieve fastest (Policy B). **No post-kill backoff (#309)** = cascade risk. Flags `--sort-by-rss`/`--ignore`/`--dryrun`/`-N` confirmed against upstream MANPAGE (`--ignore-root-user` does NOT exist). **earlyoom > systemd-oomd** (oomd is inactive here; its swap/PSI-cgroup path is ineffective on hand-launched `numactl llama-server`).

---

## Part 2 — Factory model lineup + cost multipliers (verbatim; baseline 1× = GPT-5.4)

The "Droid Core" tier = open-weights models we can self-host (cheapest, 0.12×–0.7×). This table is useful as a competitor's *relative* cost-tier calibration for our own cost_lambda normalization.

| Tier | Model (multiplier) |
|---|---|
| Frontier-expensive | Opus 4.x Fast / GPT-5.5 Pro **12×**; GPT-5.5 Fast **5×**; Opus 4.8 Fast **4×** |
| Frontier | Opus 4.5/4.6/4.7/4.8 **2×**; GPT-5.5 **2×**; Sonnet 4.5/4.6 **1.2×** |
| Mid | GPT-5.4 **1× (baseline)**; Gemini 3.1 Pro **0.8×**; GPT-5.3-Codex / GPT-5.2 / DeepSeek V4 Pro **0.7×**; Gemini 3.5 Flash **0.6×**; GLM-5.1 **0.55×** |
| Cheap | Haiku 4.5 / Kimi K2.6 **0.4×**; GPT-5.4 Mini **0.3×**; Kimi K2.5 **0.25×**; Gemini 3 Flash **0.2×**; **MiniMax M2.5/M2.7 0.12×** |

**Task → model recommendation map** (their hand-tuned routing prior): architecture/planning → Opus-high; full dev → frontier-high-reasoning; summarization/boilerplate/CI → Haiku/Droid-Core; high-volume/cost-critical → MiniMax 0.12×.

---

## Part 3 — Harvest by theme

### 3A. Routing / cost / autonomy → `learned-routing-controller.md`, `decision-aware-routing.md`, `per-request-reasoning-budget.md`, ch08

| Mechanism | Internal reproduction | Priority | Reproducible |
|---|---|---|---|
| **Factory Router: session + per-request hybrid** | Our controller decides per-request only → add session-stickiness state to the outer coordinator: keep the chosen role across turns unless complexity/escalation crosses a threshold (reduces flapping + cache thrash) | H | yes |
| **Prompt-cache-aware routing** | Add a `cache_affinity_bonus` + re-prefill penalty to the routing reward: prefer the role-server already holding the conversation prefix in slot-KV; escalate only when quality_gap justifies a cold re-prefill. **Directly attacks the flat-escalation-across-difficulty-bands open problem** in decision-aware-routing | H | yes |
| **Phase-based spec vs execution model split** (mixed-models) | Make reasoning-level a first-class action (model × thinking-level) in the controller's action space, not a fixed per-role constant: planning turns → architect (thinking-ON), execution → coder/worker (thinking-OFF) | H | yes |
| **20–25% cost-reduction target** | A concrete external benchmark for our learned router vs an always-top-tier baseline | M | yes (as a target) |
| **Cost multiplier as explicit per-model scalar** | Our cost = RAM-tier × t/s × thinking-multiplier (we have no $); feed into reward as Factory feeds the multiplier | M | yes |
| **Autonomy tiers Off/Low/Medium/High gating tool exec** | Per-route autonomy ceiling: a request routed to a cheap low-trust worker gets a lower action-risk ceiling than one routed to architect — couples routing to action-risk | M | yes |
| **Pattern-based (NOT LLM) risk classification of commands** | Tag every tool call low/med/high via deterministic regex; gate by the route's autonomy ceiling. Cheaper + safer than LLM self-assessment; extends our `check_filesystem_path.sh` | M | yes |
| **commandAllowlist/Denylist, denylist-wins, fallback-to-tier** | Clean copyable precedence rule for per-role tool-permission config | L | yes |

Verbatim autonomy levels: **Off** = read tools + allowlist only; **Low** = file edits + low-risk cmds/MCP; **Medium** = + reversible workspace changes (npm/pip install, git commit, mv/cp); **High** = + high-risk (git push, migrations, docker compose) unless a safety check requires approval. Risk classifier is deterministic regex, "doesn't depend on model behavior." Policy hierarchy is additive-only (org deny/allow immutable; project/user can only *strengthen*).

### 3B. Context / memory / token-efficiency → `context-folding-progressive.md`, `tool-output-compression.md`, `orchestrator-conversation-management.md`, auto-memory

**The standout: their context-compression *evaluation* methodology** (`/guides/power-user/evaluating-context-compression`). They ran it over **36,000+ production messages**:
- **Probe-based eval**: compress the earlier portion of a real session, then ask **probes** answerable only from the truncated span; grade "functional usefulness."
- **Four probe categories**: **Recall** ("what was the original error?"), **Artifact** ("which files did we modify and how?"), **Continuation** ("what next?"), **Decision** ("what did we decide and why?").
- **Six-dimension 0–5 rubric**, blinded judge (GPT-5.2): Accuracy, Context-awareness, Artifact-trail, Completeness, Continuity, Instruction-following.
- **Joint (token-removal %, quality) reporting** as a Pareto: Factory 98.6% removal @ 3.70 overall; Anthropic 98.7% @ 3.44; OpenAI 99.3% @ 3.35. **Artifact-trail is universally the weak axis (best 2.45/5)** → it's the metric that discriminates compactors.
- Their compactor = **"anchored iterative summarization"**: a structured persistent summary with explicit sections — **intent / file-modifications / decisions / next-steps** (which map 1:1 to the four probe types).

| Mechanism | Internal reproduction | Priority |
|---|---|---|
| **Probe-based compression eval harness** | Build into eval-tower: snapshot real orchestrator transcripts → run our context-folder on the prefix → auto-gen the 4 probe types → grade with a local judge on the 6-dim rubric. Report each fold strategy as a (token-removal %, quality) point on the Pareto dashboard. Weight Artifact-trail (the discriminating axis) | **H** |
| **Structured-section fold format** (intent/file-mods/decisions/next-steps) | Co-design the fold output with the eval (4 sections ↔ 4 probes); makes folds gradeable + Artifact-trail recoverable; gives HISTORY_SNIP a stable schema; fold at cache-safe boundaries (preserve 5-min prompt-cache TTL) | **H** |
| **Two-tier memory file + write-trigger hook** | `~/.factory/memories.md` (user) + `.factory/memories.md` (project) ↔ our MEMORY.md/file-per-fact. `#`→project, `##`→personal, "remember:" phrases, `/remember` cmd. **`<details>`-tag archive** is an immediate fix for our MEMORY.md 24.9KB-over-limit overflow (fold stale entries instead of deleting) | M |
| Per-task **token budget bands** (quick 5–15k / feature 30–80k / debug 50–150k / bulk 50–200k) + `/cost` readout | Priors for per-request-reasoning-budget; alarm when a session exceeds its band | M |
| Reasoning-effort = task-conditioned (raise budget when retry-cost > extra-token-cost) | Makes the budget knob non-flat | M |
| Exploration red-flags (high file-read / repeated grep counts → under-specified prefix) | Telemetry signal to inject project-map context | L |

### 3C. Agent architecture → `agents/` thin-map, `.claude/skills/`, `.claude/commands/`, autopilot, missions

Factory's whole config surface is `.factory/` (droids/skills/commands/docs). Their droid/skill/command formats are a **near-subset of our existing thin-map agent files + skills + commands** — our architecture is generally equal-or-better. The genuinely new, reproducible borrows:

| Mechanism | Internal reproduction | Priority |
|---|---|---|
| **Per-subagent tool allowlist** (`tools:` field — category macros `read-only`/`edit`/`execute`/`web` or explicit array; `TodoWrite` implicit; no denylist) | Add a validated `tools:` overlay field to our role overlays; category macros → Claude Code tool names; enforce via `agents_schema_guard.sh`. Gives the outer coordinator a declarative per-role capability contract | **H** |
| **Executable slash-commands** (any shebang file in `.factory/commands/`; stdout+stderr ≤64KB + source posted back to transcript) | Add an executable-command convention to `.claude/commands/` for deterministic ops the autopilot keeps re-deriving as prose: `/bench-canonical` (the `taskset -c 0-95 -t96 -fa1` protocol), `/throttle-check` (tiered drop_caches/reboot logic), `/affinity-preflight`. Makes host-health remediation an auditable script call | **H** |
| **Missions: orchestrator/worker/validator tiers** (validator ≈1 run/milestone; cost ≈ #features + 2×#milestones) | Add a **dedicated validator pass** (separate model run, different agent than the worker) at each autopilot Pareto-checkpoint / handoff phase-gate — counters the closure-inflation / self-confirmation failure mode (`feedback_closure_inflation`, `feedback_observe_before_diagnosing`) | **H** |
| **Specification Mode = graduated-autonomy approval gate** (5 options incl. read-only / reversible / all-commands tiers; no edits until approved) | Extend our EnterPlanMode analog with tiered auto-approval scopes so autopilot can auto-approve reversible config edits while gating irreversible bench/server launches (`feedback_no_concurrent_inference`) | **H** |
| **Skills: dual invocation flags** (`user-invocable` + `disable-model-invocation`) | Two orthogonal flags: "background-knowledge only" (model-invocable, not user) vs "explicit-only side-effect" (user, not auto). Encode as skill-loader metadata | M |
| **AGENTS.md directory-scoped nearest-wins precedence** (≤150 lines) | Per-subsystem CLAUDE.md (e.g. `scripts/benchmark/CLAUDE.md`) loaded nearest-wins to keep root lean (adapt for our cross-repo umbrella) | M |
| Missions **re-plan verb** (reorder remaining queue mid-run when a worker is stuck, vs only halting) | Add to the coordinator's action set | M |
| Large-feature: **fresh-session-per-phase + `IMPLEMENTATION_PLAN.md` anchor + mark-phase-done gate** | Bounds context; aligns with `feedback_phased_plan_gates` + `feedback_incremental_persistence` | M |

### 3D. Harness extensibility: hooks / droid-exec / sandbox / MCP → `scripts/hooks/`, `scripts/nightshift/`, autopilot

**Factory's hook system is a near-1:1 clone of Claude Code's** (same 9 events, same exit-code contract, same `permissionDecision`/`decision`/`continue`/`additionalContext`/`updatedInput` fields, same `mcp__server__tool` matcher). So everything they document is directly portable to `scripts/hooks/` with no translation — **the value is the event-coverage gaps we haven't wired**:

| Mechanism | Internal reproduction | Priority |
|---|---|---|
| **PreToolUse `updatedInput` param-rewrite** | Upgrade `check_filesystem_path.sh` / `pii_precommit.sh` from binary-block → *rewrite* (redact a path, strip a secret arg) so the agent isn't hard-stopped on a fixable diff | H |
| **Sandbox FS policy as a PreToolUse hook** (write = deny-all except CWD + allowWrite; read = allow-all minus denyRead of credentials) | Codify deny-all-write-except-repo-clones, hard `denyRead` on `~/.aws`/`~/.ssh`/`.env`/keyring — implements the shared-box guardrail | H |
| **`additionalContext` injection** (UserPromptSubmit/PostToolUse/SessionStart) | KB-RAG hits injected as context (not just file writes); SessionStart injects live host-throttle/NUMA/stack status so every autopilot resume re-reads host health | H |
| **PreCompact hook** | Checkpoint `autopilot_state.json` + Pareto frontier before compaction destroys it — mechanically enforces `feedback_checkpoint_pareto_state` | H |
| **Stop / SubagentStop block-to-continue** | Stop hook blocks if the phase-gate checklist (progress/handoff/index/wiki updated) is incomplete — mechanically enforces `feedback_phased_plan_gates`; SubagentStop audits sub-agent index edits | H |
| **`continue:false`+`stopReason`** | Hard-stop autopilot on host-throttle / NUMA-eviction detection (`feedback_autopilot_host_health_remediation`) | H |
| **`droid exec -o json` schema** (`is_error,duration_ms,num_turns,session_id,result`) | Parse Claude headless JSON the same way → log turn/duration telemetry per nightshift run into `agent_audit.log`; `stream-jsonrpc` = live event tap | H |
| **`--auto {low,medium,high}` headless tiers + fail-fast** | Encode nightshift bulk-inference as "medium, no-push" tier with fail-fast non-zero exit, instead of `--dangerously-skip-permissions` (shared-box safety) | H |
| **`-w/--worktree` isolated git worktree** | Run parallel autopilot/codemod trials in throwaway worktrees → fixes the recurring "parallel agents clobber shared `/mnt/raid0/llm` files" pain (`feedback_no_wholesale_git_add_shared_files`) | H |
| **MCP `${VAR:-default}` in-memory env expansion** (raw file never rewritten → secrets stay out of VCS) + per-server `enabledTools`/`disabledTools`/`timeoutMs` | Keep MCP secrets as `${VAR}` in committed config; allowlist tools per server | M |
| **Plugin packaging** (`.factory-plugin/plugin.json` + sibling commands/skills/droids/mcp/hooks) | Bundle our governance layer (hooks+skills+commands+mcp) as one installable plugin for cross-repo reuse across the 4 child repos | M |

The full **9-event hook taxonomy** (PreToolUse, PostToolUse, UserPromptSubmit, Notification, Stop, SubagentStop, PreCompact, SessionStart, SessionEnd) + universal schema + exit-code contract is captured in the sub-agent output; identical to Claude Code's.

### 3E. Flagship features: code-review / security-review / readiness / AutoWiki / incident → eval-tower, code-review skill, KB/wiki, autopilot

**Cross-cutting principle worth adopting wholesale**: all three review/scoring features emit a finding only after a **verification pass that proves impact/reachability** — code-review's 8 mandatory gates, security-review's two-pass reachability validation, readiness's binary criterion checks. This is exactly our `feedback_observe_before_diagnosing` + eval-tower verifier discipline.

| Mechanism | Internal reproduction | Priority |
|---|---|---|
| **Repo-Readiness Scorer** (5 levels Functional→Documented→Standardized→Optimized→Autonomous; **80%-of-prior-level to unlock**; 9 pillars; fractional `n/sub-apps` scoring) | **NEW capability — we have no equivalent.** Build a CPU-only scorer over our repo-map (4 repos = 4 sub-apps) scoring the 9 pillars across 5 levels; feed failing criteria into autopilot as a remediation queue (Factory's `/readiness-fix` analog). Publishable alongside the Pareto dashboard | **H** |
| **AutoWiki: structured topic taxonomy + per-page incremental refresh** | Standardize `wiki/` to emit {architecture / module / API / conventions / setup} pages; maintain a `page → source-paths` manifest + content-hash per source-set; on push recompute only pages whose source-set intersects the diff, re-embed only changed chunks into ColBERT. Closes the staleness gap project-wiki lint flags | **H** |
| **Code-review 8-gate bug filter** (flag only if: meaningful impact ∧ discrete/actionable ∧ appropriate rigor ∧ introduced-in-changes ∧ worth-fixing ∧ no-unstated-assumptions ∧ provably-affected ∧ not-intentional) + **P0–P3 severity** + structured finding schema | Add the 8-gate precondition + P0–P3 + finding schema (title ≤80 imperative / problem / file+line / severity / fix / overall assessment) to our code-review skill — makes findings eval-gradeable for the intake-658 suite | **H** |
| **Two-pass security-review** (STRIDE + OWASP Top10:2021 + **OWASP Top10-LLM:2025** + supply-chain; trace changed data flows across 7 trust boundaries; pass1 candidates → pass2 prove reachability; severity requires a concrete exploit path) | **NEW skill — we have code-review but no security-reviewer.** OWASP-LLM:2025 (prompt injection, excessive agency, insecure output) is directly load-bearing for our own agent/orchestrator stack | **H** |
| **Incident-response loop** (alert → spawn diagnostic session → consult runbook skill → RCA → write distilled learning to KB) | Map to autopilot: trigger off `health_check.sh`/log alerts (not Slack); add an `incident-guidelines` skill; "summarize uncertainty instead of acting" prompt rule; PR-only remediation | M |

**Agent Readiness — verbatim rubric** (the 5 levels + 9 pillars + 80% unlock + fractional scoring) captured in full in the sub-agent output. Note: Factory does **not** publish the complete per-criterion list (only level descriptions, the 9 pillars, the 80% rule, the scoring format, and a "Style & Validation" example) — the full rubric is in-product, so we'd author our own criteria.

---

## Part 4 — Code-review benchmark: full reproducible methodology (intake-658)

**Dataset**: 5 OSS repos (Sentry/Py, Cal.com/TS, Grafana/Go, Discourse/Ruby, Keycloak/Java), 10 real PRs each (50 total), naturally-occurring bugs (not injected). Golden set: Greptile v0 (1/PR) → Augment v1 (**145**) → Factory v3 (**167**; removed FPs, added 31 Droid-discovered). 5-way bug taxonomy (runtime_error/logic_bug/performance/security/false_positive) + 4-level severity. **Low-severity = excluded from scoring.**

**Task**: model reviews via `@droid review` bot (Droid Action, `droid exec` with whole-repo agentic context), reasoning_effort=High, 3 runs each (malfunction runs excluded).

**Scoring** (`scripts/eval_common.py`): TP = reviewer comment semantically matching a golden (deduped by golden index); FP = matches none; FN = golden never matched. `precision=tp/(tp+fp)`, `recall=tp/(tp+fn)`, `f=2PR/(P+R)`, **micro-averaged** over all PRs. Matcher = **LLM-as-judge `claude-opus-4-6`** (Anthropic SDK), exact numbered-golden prompt with `{matches, matched_index, confidence, reasoning}` JSON, **no confidence threshold**. Claude-Code-style monolithic comments split on `(?=^###?\s+\d+\.)`.

**Bias control**: judge-swap ≤2pp (controls judge self-preference in *matching* only — NOT the deeper bias that Factory's own product is the harness, nor that v3 was curated against Droid's own outputs).

**Results** (Mean F1 / $/PR / tokens-PR): GPT-5.2 60.5% / $1.25 / 462K · Opus 4.6 59.8% / $3.11 / 1.2M · Sonnet 4.6 57.4% / $1.15 / 427K · Opus 4.7 55.9% / $4.18 / 3.1M · GLM-5.1 55.8% / $1.06 / 2.6M · Kimi K2.5 51.9% / $0.41 / 152K · MiniMax M2.7 45.6% / $0.15 / 56K. Best F1 ≈60.5% → even frontier misses ~40% of golden bugs. Cost explains only ~21% of quality variance.

**Released artifacts**: harness `github.com/droid-code-review-evals/review-droid-benchmark` (**NO license**, v3 golden **gitignored**); reusable open data = Augment v1 `github.com/ai-code-review-evaluations/golden_comments` (`{pr_title, comments:[{comment,severity}]}`); closed `github.com/Factory-AI/droid-action`.

**Internal reproduction plan** ("review-finding-F1" suite for eval-tower):
- **Reuse**: Augment v1 golden set (145 bugs) + the 5 real PR sets. **Rebuild** (can't reuse): v3 expansion (gitignored), the review-trigger layer (Droid Action is closed), scoring code (re-implement `eval_common.py` ~80 LOC clean — original is unlicensed, do **not** vendor it).
- **Review step**: drive each LOCAL model (gemma4-26B-A4B worker_general, coder roles, peer-verifiers) through `/v1/chat/completions` (`enable_thinking=False` per Qwen3.x rule) over **diff + surrounding-file context** (we can't give whole-repo agentic context cheaply on CPU — freeze to diff+context and **document the divergence** from Factory's agentic setup). 3 runs, mean±StdDev, micro-averaged P/R/F.
- **Judge = LOCAL cross-family**, NOT hardcoded frontier: per eval-tower **EV-6**, judge a different family than the model under review; run the ≤2pp judge-swap ablation locally. Optional frontier cross-check on a subset for calibration only.
- **Slot-in**: new suite under `multi-file-coding-completion-capability.md`; register the judge-swap as a concrete EV-6 instance; **index by model/quant not role** (`feedback_model_not_role_indexing`); incremental per-PR persistence (`feedback_incremental_persistence`).
- **Caveats to state in the suite doc**: (1) golden set is vendor-curated, v3 against Factory's own agent → rewards Droid-style findings; (2) absolute F1 (~45–60%) is anchored to agentic whole-repo frontier review → our diff+context CPU setup scores lower and is **not** comparable to their leaderboard, only internally; (3) low-severity exclusion + no-threshold semantic judge inject judge bias the ≤2pp ablation only weakly bounds.

**Other Factory benchmarks** (reproducibility): Agent Arena (crowdsourced Bradley-Terry/Elo, proprietary platform — **not reproducible**); Terminal-Bench (upstream framework *is* open — **partially reproducible** with a local agent); Next.js eval (Vercel's, rubric not public — **not reproducible**); Legacy-Bench (Factory's own, ~10 public samples, **hidden** verification tests — partially reproducible if you author your own tests; COBOL/Java-7/legacy focus — niche for us).

---

## Part 5 — earlyoom deployment recipe for our host (intake-659)

> **Authoritative recipe lives in the [`earlyoom-oom-protection.md`](../handoffs/active/earlyoom-oom-protection.md) stub** (live-verified 2026-06-03). Summary below; the stub has the full Policy-A/B decision + verified live facts.

**Recommendation: deploy earlyoom (not systemd-oomd).** Per-process regex steering + self-`mlock` responsiveness fit our box; systemd-oomd (currently `inactive`) needs cgroup-v2 `MemoryAccounting` our hand-launched `numactl llama-server` lacks. Do **not** co-run two OOM daemons.

**Install**: distro package (`apt/dnf install earlyoom`) for the hardened systemd unit + `/etc/default/earlyoom` wiring.

**`/etc/default/earlyoom`** (Policy A — protect production servers; validate flags + comm names + `--dryrun` first):
```
EARLYOOM_ARGS="-M 41943040,20971520 -s 100,100 -r 60 -p --sort-by-rss \
--ignore '^(llama-server|sd-server)$' \
--prefer '^llama-bench$' \
-N /mnt/raid0/llm/epyc-root/scripts/hooks/earlyoom_audit.sh"
```
- **`-M 41943040,20971520`** = absolute 40 GiB SIGTERM / 20 GiB SIGKILL (NEVER percent at 1.1TB — 10% = 110 GB). 445 GiB available at audit, so no false-fire; raise SIGTERM for more reaction time if needed.
- **`-s 100,100`** (lowercase = percent) = neutralize the **8 GB swap** gate so memory alone triggers BOTH SIGTERM and SIGKILL. (The earlier `-S 100,100` was the KiB flag — wrong; default `-s 10` would make earlyoom never fire here.)
- **`--sort-by-rss`** = deterministic; `oom_score` is **flat** here (133 GB server=742 vs 28 MB orchestrator=666) so default mode is unsafe. Small control plane protected by RSS-smallness.
- **`--ignore '^(llama-server|sd-server)$'`** = hard-protect production model-servers + embedders + managed image svc (under `--sort-by-rss`, `--avoid`'s −300 ≈ −3 GiB can't protect a 133 GB server — only `--ignore` works). Control plane (`comm=python`, incl. 6 uvicorn workers @ ~1.1–1.26 GB) is **NOT** covered by `--ignore` and **NOT** safe by RSS-smallness → protect with **`oom_score_adj=-1000`** EXACTLY (earlyoom skips −1000 in both modes; −900 does not). Durable fix: `OOMScoreAdjust=-1000` in the orchestrator launcher.
- **`--prefer '^llama-bench$'`** = bias toward culling a runaway manual benchmark (only bench binary built; `run_benchmark.py` is `comm=python`, covered by `--sort-by-rss`).
- **`-N` hook** → `scripts/hooks/earlyoom_audit.sh` (written + tested) appends a JSON-lines `EARLYOOM_KILL` record to `logs/agent_audit.log` so a kill is a recorded host event, not misattributed to the config-under-test (Pareto contamination).

**Validate BEFORE arming**: run `--dryrun -d` with the real args against a **live full-stack snapshot**; confirm the would-kill candidate is always a bench/eval or the largest non-protected server, never the orchestrator/autopilot/loading server. Verify truncated comms by hand. Optionally drive a `stress-ng --vm` ramp in a quiet window.

**Known caveats**: cgroup-unaware; **no post-kill backoff (issue #309)** → can kill several procs in rapid succession before mlock'd pages are reclaimed (cascade risk on a box of large model-servers) — set KILL threshold far enough below SIGTERM that a single kill restores headroom, and have the `-N`/autopilot pause new loads after any kill; 15-byte comm truncation; `--avoid` is best-effort (use `--ignore`).

**Maturity**: ~4.1k★, MIT, C, v1.9.0 (2025-09-16), unit+integration tests + CI, packaged in every major distro (was Fedora 32 default), ~2 MiB RSS. Safe to depend on.

---

## Part 6 — Prioritized harvest backlog

**Tier 1 — high-value, reproducible now, maps to active handoffs:**
1. **Prompt-cache-aware + session-sticky routing reward terms** → `decision-aware-routing.md` (attacks the flat-escalation open problem) + `learned-routing-controller.md`.
2. **Probe-based context-compression eval harness + structured-section fold format** → `context-folding-progressive.md` + eval-tower (4 probes ↔ 4 fold sections; weight Artifact-trail).
3. **Code-review 8-gate filter + P0–P3 + finding schema, and the review-finding-F1 eval suite** → code-review skill + `eval-tower-verification.md` EV-6 + `multi-file-coding-completion-capability.md` (intake-658).
4. **Lifecycle hooks** (PreCompact checkpoint, SessionStart host-health inject, Stop phase-gate block, PreToolUse param-rewrite/sandbox FS policy) → `scripts/hooks/` (mechanically enforce existing feedback-memories).
5. **Deploy earlyoom** → `single-instance-system-tuning.md` (recipe in Part 5).

**Tier 2 — reproducible, medium effort:**
6. **droid-exec-style headless hardening**: `-o json` telemetry, `--auto` permission tiers, `--worktree` isolation → `scripts/nightshift/` + autopilot (fixes shared-clone clobber).
7. **Executable slash-commands** for autopilot's reproducible primitives (`/bench-canonical`, `/throttle-check`) → `.claude/commands/`.
8. **Per-role tool allowlist** field in agent overlays → agent-file-architecture + `agents_schema_guard.sh`.
9. **Missions validator-tier** (separate-agent validation pass at phase-gates) + **graduated-autonomy approval gate** → autopilot + EnterPlanMode analog.
10. **Two-tier memory + `<details>` archive** (fixes MEMORY.md overflow) → auto-memory.

**Candidate NEW opportunities (no existing handoff — need user approval before creating stubs, per CLAUDE.md governance):**
- **A. Repo-Readiness Scorer** (5-level / 9-pillar / 80%-unlock, scored over our 4-repo map, feeding autopilot remediation) — genuinely novel, no equivalent in our stack.
- **B. Security-review skill** (two-pass STRIDE + OWASP Top10 + OWASP-LLM:2025 + supply-chain; OWASP-LLM directly relevant to our own agent stack) — we have code-review but no security-reviewer.
- **C. AutoWiki-style incremental KB generator** (topic-taxonomy pages + page→source manifest + change-driven re-embed) — extends `internal-kb-rag.md` / project-wiki.

**SaaS-only / not harvestable**: the Droid harness itself, Factory App/Cloud Sync wiki UI, Agent Arena platform, BYOK billing, Droid Computers (managed sandboxes), Slack/Linear auto-run triggers, enterprise SSO/SCIM/SOC2 plumbing, the closed model roster + promotional multipliers, EU-deployment/data-residency.

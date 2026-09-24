# AutoKernel — the orchestrator as planner/author backend

**Status**: ACTIVE — PLANNED 2026-09-24 (operator direction); reference seat A/B pending
**Created**: 2026-09-24
**Priority**: MEDIUM (long-term direction; the campaign keeps opencode + 27B meanwhile)
**Categories**: agent_architecture, autonomous_research, hardware_optimization
**Parent index**: [inference-research-index.md](inference-research-index.md) (row INF-78)
**Depends on**: INF-77 (DS41 campaign, seat A/B), INF-66 (owns `Backend` kinds), EVL-37 (S4 turns
metric), RTG-56 (TD-21 repair ladder), UFH-01 (MCP tool convergence, opencode shell)
**Related**: [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md) §C (DS41-C16..C21),
[`autokernel-rebuild-program.md`](autokernel-rebuild-program.md) R23-37 (opencode `Backend`), R24-3
(read-only critic), [`repl-turn-efficiency.md`](repl-turn-efficiency.md) S4-T1/T2,
[`typed-decision-plane.md`](typed-decision-plane.md) TD-21.30/21.33,
[`harness-selection-and-integration.md`](harness-selection-and-integration.md) HS-4 P6/P7, HS-OD-4

## Objective

The autokernel loop should call the **orchestrator**, not individual models (operator, 2026-09-24).
The orchestrator then owns model choice and the loop sees one `Backend`. The bounded opencode seat
built 2026-09-24 (research `scripts/kernel_rnd/autokernel/loop/actors.py` `ActorSeat`,
`actor_opencode_config.py`, `actor_tools_mcp.py`; lane `lane/ak-actor-seat-20260924`, DS41-C20) is the
focused real-world reference an orchestrator backend must BEAT on the same driver, and the source of
techniques fed back into the orchestrator (§Techniques).

## Operator rulings recorded 2026-09-24 (do not re-open)

- **REPL role pinning is NOT a blocker.** `scripts/benchmark/seeding_eval.py:855` pins
  `self_role = "frontdoor"` (Qwen3.6-35B-A3B, CPU :8070); output-spill summaries call
  `role="worker"` (`src/repl_environment/environment.py:693`, synchronous); embedders/ColGREP run on
  CPU. The planner completes BEFORE measurement, so these are idle during measurement. The only
  requirement kept is R2 below (no trailing work).
- **Architect (27B, :8083) stays out of REPL mode for now** (`scripts/benchmark/seeding_types.py:380`
  `ARCHITECT_MODES = {"direct","delegated"}`); frontdoor may escalate/consult the architect. See
  §Future.
- **Provenance is NOT a blocker.** The critic may stay cloud-hosted; the loop's planner/critic family
  check (`actors.py` `AgentCritic`, `independence = same_family|different_family` from
  `context["actor_provenance"]["planner"]`) is satisfied by `describe()` alone. Per-call model
  provenance from the orchestrator is a nice-to-have (R5).

## Requirements on the orchestrator (what a backend must provide)

- **R1 — an agentic tool loop in a GIVEN git worktree.** Author: file edits confined to the lane
  worktree; planner and critic: read-only. Today the edit root is process-wide
  (`src/repl_environment/task_root.py:22` `ORCHESTRATOR_EDIT_ROOT`) and `ChatRequest` has no
  root/worktree field (`src/api/models/requests.py`); REPL file writes queue for approval
  (`file_mutation.py:154` `_prepare_patch` → `:251` `_apply_approved_patch`). The loop runs one lane
  worktree per candidate, so a per-call root is mandatory.
- **R2 — NO trailing async work after the call returns.** No spill summaries, MemRL writes, index
  builds, prewarms (`src/graph/helpers.py:226` `asyncio.ensure_future(prewarmer.prewarm_if_complex)`
  is the existing fire-and-forget shape) may run after `/chat` responds, because the loop's next step
  is the measurement window and `competing_inference_witness()` (DS41-C2b-gate) counts unowned
  inference work. Acceptance is a witness, not a promise: cumulative `utime+stime` of every
  orchestrator-owned server flat for 60 s after the reply.
- **R3 — prompt of ~35-75k chars in, ONE schema-conforming JSON object out.** `output_schema`
  (`requests.py:293`) + TD-21.1 `repl_final` repair; the turn cap must reach ~60 agentic steps —
  `ChatRequest.max_turns` is `le=50` (`:79`) and the `/v1` REPL path clamps to 5 (`openai_compat.py`,
  HS-OD-4). Use `/chat`, raise the cap, or run a batched outer loop; decide in OAB-2.
- **R4 — bounded tool output.** Same caps as the seat's `actor_tools_mcp.py` (read ≤200 lines, 400
  chars/line; grep ≤80 hits; outline 300 entries; code_search k≤10) via HS-4 P6.
- **R5 — per-call provenance (nice-to-have).** `ChatResponse` already carries `routed_to`,
  `role_history`, `routing_strategy`, `turns` (`responses.py:97-110`); the backend copies them into
  the seat's `actor-replies/actor-calls.jsonl` (`actors._record_call`) so experiment records name the
  model(s) behind each proposal even when routing changes.
- **R6 — a `Backend` kind or an HTTP client.** The `actors.py` contract is `Backend.argv` +
  `stdin_payload` + `describe`; everything downstream sees stdout. Either an `orchestrator` kind whose
  `argv` is a thin CLI (`ORCHESTRATOR_PYTHON -m ... --root <wt> --schema <file>`) reading the prompt
  on stdin and printing the JSON, or a second seam in `_run_agent`. The CLI form keeps `_run_agent`,
  `_persist_reply` and `_record_call` unchanged — preferred.

## Baseline (the number to beat)

DS41-C20c, one pair on the 27B (:8083), same run-7 proposal prompt, driver
`/mnt/raid0/llm/tmp/ak-seat-ab/driver.py`. **Winner and campaign default: the plain opencode seat** on research
main `21ca61b0` — **31.9 min, 23 steps, 25 tool calls, 57.7k decoded tokens, 1 compaction, schema-valid.** Bounded
v2: 44.3 min, 34 steps, 60.2k decoded, 1 compaction, schema-valid and better grounded (its loss is perf-tool time,
DS41-C20d). Pre-fix reference (run 7, escaped prompt): 40.3 min, 71 steps, 63.8k decoded, 2 compactions. Decode
dominates the wall (~58k tokens at ~30 tok/s); every arm compacted once because opencode's context is append-only.

## Tasks

- [x] **OAB-0 — Do not start until DS41-C20 has recorded the seat A/B.** ✅ 2026-09-24 (DS41-C20c; §Baseline) The reference must exist
  before anything is built against it. Zero compute.
- [ ] **OAB-1 — per-call worktree root + edit mode on `/chat`** (orchestrator). Add
  `ChatRequest.task_root: str | None` and `edit_mode: Literal["none","direct"]` (default `none`);
  `task_root.get_task_root()` honours the request over `ORCHESTRATOR_EDIT_ROOT`; `edit_mode=direct`
  lets `_file_write_safe` (`file_mutation.py:88`) write inside `task_root` without the approval queue,
  everything else refused. Acceptance: a test that a write outside `task_root` is refused and one
  inside lands; a `none` request cannot write at all. Zero inference.
- [ ] **OAB-2 — `orchestrator` Backend kind** (research, `loop/actors.py`). `backend_for("orch:<role
  or auto>", effort)` → kind `orchestrator`; `argv` = `[ORCHESTRATOR_PYTHON, "-m",
  "scripts.autokernel_actor_cli", "--root", <wt>, "--read-only"?, "--schema", <tmp>]`, prompt on
  stdin, JSON on stdout, exit 0/1 — so `_run_agent`, salvage, `_persist_reply`, `_record_call` and
  `_parse_reply` need no change; `_schema_repair` short-circuits for this kind (repair happened
  server-side, TD-21.1/21.33). Decide R3's turn-cap path here and record it. Acceptance: the
  `{"ok":true}` smoke the DS41 launch used (DS41-C2c) passes through the loop's OWN invocation;
  `test_actors.py` covers the kind. Inference: one smoke call.
- [ ] **OAB-3 — trailing-work witness (R2).** Add to the CLI a post-reply 60 s sampler of the
  orchestrator-owned servers' `utime+stime` (reuse DS41-C2b-gate's reader) and fail the call if any
  accrues > 0.5 core-s after the reply. Acceptance: a deliberately injected prewarm trips it.
  Inference: one call.
- [ ] **OAB-4 — A/B against the bounded seat on the same driver.** Extend
  `/mnt/raid0/llm/tmp/ak-seat-ab/driver.py` with an `orch` arm; same prompt, same 27B :8083 (via the
  orchestrator's `x_force_role` / `force_role` if needed), one arm at a time, report steps / tool calls
  / decoded tokens / wall / compactions / schema-valid. Acceptance: three paired runs per arm (host
  drift ~3% over hours; alternate ABAB). GPU inference, campaign-idle window only.
- [ ] **OAB-5 — promotion rule.** The `orchestrator` kind becomes the campaign default only if OAB-4
  shows wall ≤ bounded seat AND schema-valid rate ≥ bounded seat over the paired runs; otherwise it
  stays an opt-in `--planner-model orch:auto` and this handoff records the gap. Zero compute.
- [ ] **OAB-6 — prompt diet in the orchestrator's context renderer.** Port the seat's
  `_dedupe_subtrees` (≥200-char repeated subtree → `<same as $.path>`), `_clip` (500-char prose) and
  the id-field drop (`SHARED_ROW_ID_FIELDS`) as a `prompt_builders` utility applied to JSON blocks over
  N KB before rendering; measure prompt tokens before/after on one DS41 planner prompt (the seat's
  trims took the run-7 prompt 95.7k → 75.9k chars). Acceptance: byte-identical output when nothing
  repeats; a unit test on the DS41 prompt shows the reduction. Zero inference.

- [ ] **OAB-7 — the context bundle is a REPL variable, not an inlined prompt.** The rendered context is ~38k tokens
  of the 98k slot before step 1 (75.9k chars after the seat's diet). In the orchestrator REPL it becomes a `context`
  object the model inspects (`peek`/`grep`/field access), so the root context carries only what the model prints —
  the RLM pattern — and tool output lands in variables instead of the conversation. This is the structural answer to
  DS41-C18: in the seat A/B every arm compacted once however tool output was capped (append-only conversation).
  Acceptance: OAB-4's `orch` arm reports first-step context and max context well below the plain seat's 39k / 93k
  with no compaction. Zero inference to build; OAB-4 measures it.
- [ ] **OAB-8 — fan-out is the orchestrator's decision, not the model's.** Offered an allowed `task` tool plus
  fan-out guidance, the 27B never delegated once in 69 bounded steps (DS41-C20c). Splitting is orchestration: for a
  proposal, the orchestrator (`repl_environment/parallel_dispatch.py`) runs one read-only scout per top profile
  hotspot / candidate file concurrently (≤ server slots) and hands the planner their summaries; the loop sends ONE
  request and never implements fan-out itself (operator, 2026-09-24: this is the orchestrator's job, not the
  harness's). Acceptance: OAB-4 `orch` arm shows ≥2 concurrent scout calls on :8083 per proposal and a planner
  context built from their summaries.

## Future (recorded, NOT for now)

- **Architect REPL access** — review `ARCHITECT_MODES` (`seeding_types.py:380`) now that the 27B is
  fast (86 t/s decode / 302 t/s prefill on :8083, DS41-C17). Escalation from frontdoor suffices today.

## Techniques from the seat to feed back into the orchestrator (checked 2026-09-24)

| Technique (seat, `actors.py` unless noted) | Orchestrator today | Where it goes |
|---|---|---|
| Prompt on STDIN, never argv (`Backend.argv` / `stdin_payload`) | n/a in the API; the OpenCode SHELL is affected | HS-4 P7 (`harness-selection-and-integration.md`) |
| Salvage a COMPLETE reply on non-zero exit (`_run_agent`), stderr-tail fallback | `llm_primitives/inference.py:1132` keeps read-timeout partials; no exit-code salvage concept (HTTP) | OAB-2 keeps it loop-side (CLI exit codes) |
| Refuse repair over empty reports + ground repaired fields in the report (`REPAIR_MIN_REPORT_CHARS`, `_ungrounded_fields`) | `structured_output/repair.py` has neither | TD-21.33 (`typed-decision-plane.md`) |
| Prompt diet: dedupe repeated JSON subtrees, drop hash/id fields, clip prose (`_dedupe_subtrees`, `_slim_shared_history`) | only `_deduplicate_tool_calls` (`prompt_builders/code_utils.py:214`); no subtree dedupe | OAB-6 |
| Output-capped read/grep/outline/code_search tools (`actor_tools_mcp.py`) | REPL mixins exist, uncapped, not on MCP | HS-4 P6 |
| Step cap + tool-discipline agent prompt + read-only scout fan-out (`actor_opencode_config.py`) | `max_turns` (`requests.py:79`); parallel dispatch exists (`repl_environment/parallel_dispatch.py`) | R3/OAB-2; compare after OAB-4 |

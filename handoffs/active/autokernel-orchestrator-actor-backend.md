# AutoKernel — the orchestrator as planner/author backend

**Status**: ACTIVE — PLANNED 2026-09-24 (operator direction). Seat A/Bs done: plain beats bounded (DS41-C20c),
and inline beats context-as-files (OAB-9, 2026-09-25). **2026-09-25: OAB-1/2/3/10/11 done; OAB-7 and OAB-8 built,
merged and deployed** (orchestrator `b9e004e3`, API reloaded 14:40:38Z). **2026-09-26: OAB-24..27 merged to
research main `d643d794`** (author budgets and the opencode 32000 output-cap fix, ak-check sandbox, best-of-2,
GitNexus anchor scoping). Next: the live OAB-4 A/B.
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

## Operator rulings recorded 2026-09-25 (do not re-open)

- **Architect REPL: a scoped exception.** The 27B architect may run in REPL mode ONLY for task-scoped
  (`task_root`) requests. Encoded in orchestrator `7d0ce447`: `roles.architect_repl_allowed()` is the single
  predicate, `/chat` logs (does not refuse) unscoped architect REPL because the 2026-09-24 ruling is caller-side,
  and seeding gains `architect_modes(task_scoped)`. Unscoped requests keep the 2026-09-24 ruling above.
- **Scouts: `/slots` admission (reserve ≥ 1) is accepted for scoped calls** (OAB-8). Follow-up: OAB-16.
- **Reasoning stays ON for the planner; no thinking on/off A/B.** Thinking is already on through the template
  default, so the medium-reasoning request is effectively honoured; `tokens.reasoning = 0` is an accounting
  artifact (OAB-21).
- **Pausing AutoKernel is allowed for planner/orchestrator A/Bs** ("this work is important for orchestrator
  development also, so it's not wasted"). Pause cleanly and relaunch right after; idling with nothing running is
  not allowed.
- **Context-as-variable lost only because of opencode** (pulls land in its append-only conversation). Revisit it
  when it is wired into the orchestrator REPL/RLM (OAB-7 proper); OAB-9b carries this.

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
v2: 44.3 min, 34 steps, 60.2k decoded, 1 compaction, schema-valid and better grounded (its loss was attributed to perf-tool time,
DS41-C20d — doubted 2026-09-24: the cache measures 1.3 s per uncached call, see §Techniques learned → 3). Pre-fix reference (run 7, escaped prompt): 40.3 min, 71 steps, 63.8k decoded, 2 compactions. Decode
dominates the wall (~58k tokens at ~30 tok/s); every arm compacted once because opencode's context is append-only.

## Tasks

- [x] **OAB-0 — Do not start until DS41-C20 has recorded the seat A/B.** ✅ 2026-09-24 (DS41-C20c; §Baseline) The reference must exist
  before anything is built against it. Zero compute.
- [x] **OAB-1 — per-call worktree root + edit mode on `/chat`** (orchestrator). ✅ 2026-09-25 — orchestrator
  `9124c7f1` + Fable review fixes `7f5d6870` (F1 shell writers `sort -o`/`sed -nf`/`git --output`, F2
  `/chat/stream` refuses the scope fields, F3 write-check TOCTOU, F4 symlink-dereference escapes, F6 frozen
  trees/kernels/models refused as `task_root`), merged in `994529fd`. The scope rides a ContextVar per request;
  `edit_mode=direct` writes inside `task_root` only; `none` cannot write; the response echoes `task_scope`. R3:
  scoped requests get a `max_turns` ceiling of 100 and bypass the long-context 8-turn override. Tests
  `test_oab1_task_scope.py` (23). Add
  `ChatRequest.task_root: str | None` and `edit_mode: Literal["none","direct"]` (default `none`);
  `task_root.get_task_root()` honours the request over `ORCHESTRATOR_EDIT_ROOT`; `edit_mode=direct`
  lets `_file_write_safe` (`file_mutation.py:88`) write inside `task_root` without the approval queue,
  everything else refused. Acceptance: a test that a write outside `task_root` is refused and one
  inside lands; a `none` request cannot write at all. Zero inference.
- [x] **OAB-2 — `orchestrator` Backend kind** (research, `loop/actors.py`). ✅ 2026-09-25 — research `751ec730`
  (`actor_orchestrator.py`, `--planner-model orch:auto`) merged to research main (`4a507624`, then `82f48e11`);
  orchestrator actor CLI `e33eb1d3` (`scripts/autokernel_actor_cli.py`, invoked by path under `-I`, because a lane
  cwd has its own `scripts/`), merged in `994529fd`. Smoke PASS ×3 through the loop's own invocation
  (`/mnt/raid0/llm/tmp/oab2-smoke/smoke.sh`: orch:auto → frontdoor REPL, 15.8 s, 2 turns), and again after the
  14:40:38Z reload. VB-AK-SEAT accepts the kind (root `fa8d0fa1`, research test `67cac838`). `backend_for("orch:<role
  or auto>", effort)` → kind `orchestrator`; `argv` = `[ORCHESTRATOR_PYTHON, "-m",
  "scripts.autokernel_actor_cli", "--root", <wt>, "--read-only"?, "--schema", <tmp>]`, prompt on
  stdin, JSON on stdout, exit 0/1 — so `_run_agent`, salvage, `_persist_reply`, `_record_call` and
  `_parse_reply` need no change; `_schema_repair` short-circuits for this kind (repair happened
  server-side, TD-21.1/21.33). Decide R3's turn-cap path here and record it. Acceptance: the
  `{"ok":true}` smoke the DS41 launch used (DS41-C2c) passes through the loop's OWN invocation;
  `test_actors.py` covers the kind. Inference: one smoke call.
- [x] **OAB-3 — trailing-work witness (R2).** ✅ 2026-09-25 — orchestrator `9124c7f1`:
  `ChatRequest.quiescent_after` suppresses every fire-and-forget launch on `/chat` and holds the idle-scoring loop;
  `src/runtime/trailing_work_witness.py` fails a window when an orchestrator-owned process accrues > 0.5 core-s.
  The injected-prewarm acceptance test trips it (`test_oab3_quiescence_witness.py`, 10). Live witness, 60 s after
  a real reply: rc 0, max ≤ 0.4 core-s per process (08:32Z, and again after the 14:40Z reload). Add to the CLI a post-reply 60 s sampler of the
  orchestrator-owned servers' `utime+stime` (reuse DS41-C2b-gate's reader) and fail the call if any
  accrues > 0.5 core-s after the reply. Acceptance: a deliberately injected prewarm trips it.
  Inference: one call.
- [ ] **OAB-4 — A/B against the bounded seat on the same driver.** Extend
  `/mnt/raid0/llm/tmp/ak-seat-ab/driver.py` with an `orch` arm; same prompt, same 27B :8083 (via the
  orchestrator's `x_force_role` / `force_role` if needed), one arm at a time, report steps / tool calls
  / decoded tokens / wall / compactions / schema-valid. Acceptance: three paired runs per arm (host
  drift ~3% over hours; alternate ABAB). GPU inference, campaign-idle window only.
  **Status 2026-09-25: every prerequisite is deployed** (OAB-1/2/3, OAB-7, OAB-8, the architect scoped exception;
  orchestrator `b9e004e3`, API pid 2517073 since 14:40:38Z). Arms: 27B plain seat vs 27B orchestrator REPL +
  scouts + context variable. Pause run 10 through its control listener for it, or run it concurrently and
  alternate arms; the CPU is never left idle (operator 2026-09-25).
- [ ] **OAB-4a — pin and record :8083's KV mode in every OAB-4 arm** (filed 2026-09-24, RTG-57). Unified vs
  split KV changes outputs at the same seed, because float summation order changes. It also moves the per-request
  ceiling from 98,304 to 196,608 tokens once the `-kvu` package lands. An arm pair that straddles the :8083 reload
  compares two servers, not two backends. Record `kv_unified` from the launch log and `/props` `n_ctx` per arm,
  and run both arms of a pair on the same server generation. OAB-7's "~38k of the 98k slot" is the split-KV
  ceiling.
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
  **Status 2026-09-25: the seat-side precursor was built and A/B'd, and it LOSES on the 27B plain seat.** OAB-7s
  merged to research main `30631761`. In OAB-9 it halved first-step context, but it raised peak context
  (163k/118k vs 104k/92k), steps, tool calls and wall in both pairs. The model read the whole bundle back, then
  explored more. OAB-7 therefore stays open only as an orchestrator design that must carry what the seat lacked:
  - exact pulls counted and capped (OAB-12);
  - scouts that pull for the planner (OAB-8).

  It should not be built as "move the context out of the prompt" alone. See §Techniques learned → 4.
  **Built 2026-09-25 (orchestrator side), with both missing pieces.** Orchestrator `88e22777` + `1d0ab2f5`,
  research `79231b0f`, merged via the integration lanes (orchestrator `db36edca` → `b9e004e3`, research
  `30ac7293`). `ChatRequest.context_bundle` becomes the REPL variable `context`. Pulls land in variables, and only
  a per-turn print cap (default 4,096 B) and 80-char state previews reach the root prompt; `context_pulls` echoes
  exact per-section pull accounting, and `context_pull_budget_bytes` caps pulls per call. On the DS41 run-8
  control prompt the turn-1 root prompt fell 30,106 → 7,810 tokens (−74%), and a pulled sentinel never reaches any
  prompt (test). Acceptance still waits on OAB-4's live `orch` arm.
  Found and fixed on the way, and **production-visible after the reload**: `auto_wrap_final` turned a one-line
  `print(...)` into `FINAL(None)`; the output-schema preamble and the schema-retry message never reached the model
  (`1d0ab2f5`; only when `final_schema_validation` is on); the proactive stage answered COMPLEX prompts before the
  REPL even for scoped or bundle requests; the REPL sandbox now refuses frame attributes, `cell_contents`,
  `operator.attrgetter`/`methodcaller` and dunder-reaching `str.format` for every REPL execution (`86cdeaf3`).
- [ ] **OAB-8 — fan-out is the orchestrator's decision, not the model's.** Offered an allowed `task` tool plus
  fan-out guidance, the 27B never delegated once in 69 bounded steps (DS41-C20c). Splitting is orchestration: for a
  proposal, the orchestrator (`repl_environment/parallel_dispatch.py`) runs one read-only scout per top profile
  hotspot / candidate file concurrently (≤ server slots) and hands the planner their summaries; the loop sends ONE
  request and never implements fan-out itself (operator, 2026-09-24: this is the orchestrator's job, not the
  harness's). Acceptance: OAB-4 `orch` arm shows ≥2 concurrent scout calls on :8083 per proposal and a planner
  context built from their summaries.
  **Built 2026-09-25**: orchestrator `813e0135`, research `571160bc` (planner scout targets + scout provenance on
  the metrics row), merged via `9dabd7be` / `9cd7c743`; composition test `c754c987` / `806e29d7`. Scouts are
  direct-completion read-only loops, capped by live `/slots` (reserve ≥ 1), and they finish before the planner
  turn. Governance note: they bypass the `LLMPrimitives` gates (contention, region lock, inference tap) → OAB-16.
  Acceptance still waits on OAB-4's live `orch` arm.

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

## Techniques learned in the opencode seat (2026-09-24, reduced-scope build)

The operator directed a reduced-scope build on the opencode seat while DS41 run 9 calibrated, to learn
what the orchestrator wiring must copy. Three research lanes came out of it. All three branch from research
`origin/main` `170c763c`. They were merged to research main `30631761` on 2026-09-25 through
`lane/ak-planner-integ-20260924`, and the context placement was A/B'd the same night (→ 4; **inline won**). The operator called
these learnings "immensely important" to the final orchestrator wiring. Chronology:
`progress/2026-09/2026-09-24-main-ak-seat.md` → *Reduced-scope planner build (evening)*. How-to form:
[`agent-loop-design.md`](../../docs/guides/agent-workflows/agent-loop-design.md) → *Context as files,
per-call metrics, tool-output caching*.

| Lane @ commit | What it built | Maps onto |
|---|---|---|
| `lane/ak-ctxvar-20260924` @ `ce5800cb` | `--actor-context-mode variable` (default `inline`, byte-identical). The rendered bundle is written to `workers/actor-context/<stamp>-<role>-*/`, beside the lane and never inside it: `sections/`, `json/`, `INDEX.md` and a `manifest.json` (`epyc.autokernel.actor_context_bundle.v1`) bound to the prompt sha. The prompt carries only an index. | OAB-7 (context as a variable), OAB-6 (diet) |
| `lane/ak-turns-20260924` @ `0bf2d7c2` | An `epyc.autokernel.actor_call_metrics.v1` row per planner/author/critic call. It is written to `actor-calls.jsonl` just BEFORE the VB-AK-SEAT `actor_call.v1` line. A summarizer: `python -m scripts.kernel_rnd.autokernel.loop.actor_metrics STATE_DIR`. | S4-T1 ([`repl-turn-efficiency.md`](repl-turn-efficiency.md)), OAB-4 columns, R5 |
| `lane/ak-perfcache-20260924` @ `f4a5d240` | A content-addressed cache for `perf report`/`perf annotate` output in `actor_tools_mcp` (`perf_cache.py`). It closes DS41-C20d's build half. | R4 (bounded tool output), DS41-C20d |

### 1. Context bundle as files (OAB-7 precursor)

- **The plain seat has NO MCP server.** It runs bare `opencode run --auto` with no `OPENCODE_CONFIG`, so it
  has only native `read`/`grep`/`glob`/`bash` (plus edit/write). A file tree is therefore the only
  "variable" it can inspect. Reads outside `--dir` work only because `--auto` approves opencode's
  `external_directory: ask` default. The critic runs read-only, **without** `--auto`, so it stays inline.
- **Measured with the 27B tokenizer** (`llama-tokenize`, Qwen3.8-27B vocab):
  - run-8 planner prompt: 75,978 chars / **26,293 → 5,510 tokens (−79%)**;
  - run-7 pre-diet prompt: 92,757 chars / **32,917 → 5,629 tokens (−83%)**.
- **chars/3.5 undercounts by ~30% on this prompt.** The target JSON runs at 2.46 chars/token (hex digests). It
  is 37% of prompt tokens and nearly useless to the planner. Tokenize; never estimate.
- **About 13.2k tokens of every call is fixed** and no prompt change removes it: opencode's system prompt,
  its tool schemas, and the lane's `AGENTS.md`. That file is 8.9k chars of llama.cpp contributor guidance,
  ~2.5–3k tokens (OAB-10).
- **The inline set was chosen from evidence**, not by taste:
  - the scope directives run.py prepends (2.4k chars);
  - the profile/hotspot section — run 7's one complete hypothesis copied `target_symbol` verbatim from it;
  - the this-turn instruction blocks (superseded, escapes, characterised, tried, rejection feedback);
  - a new resolved **target card**: model, threads, speculation, env, topology and build dir.

  Everything else goes to files: the target JSON, `program.md`, shared history, serving observations and the
  operator inbox. The index names the inbox as required reading.
- **Lossless by construction.** The section files concatenate back to `render_context`'s text byte for byte, and
  each JSON block implodes back to the identical object. Inline mode reproduces the real run-8 prompt byte for
  byte (its sha equals the call record's). If a bundle cannot be written, the call falls back to inline and
  says so.
- **Predictions for the live A/B (OAB-9), not results:**
  - first-step context 39.5k → ~18.7k tokens;
  - peak 93.5k → ~79k;
  - 0 compactions instead of 1;
  - a modest wall gain, because later steps were prefix-cache hits;
  - the conversation still only grows.
- **Found while building:**
  - `render_context` never printed `node_profile`, although a directive says to read it. It is being fixed in
    BOTH arms at integration, so the A/B stays fair.
  - The plain planner read the anchor build tree instead of its lane, and compiled `.o` files into `/tmp`
    despite "never build" (OAB-11).
  - Files outlive compaction: the planner re-read `INDEX.md` after compacting. That is the property this
    design depends on.

**Copy for the orchestrator (OAB-7):**
- an addressable store plus a sized index (TOC with byte/token sizes);
- a small inline set chosen from evidence (what replies actually cite), not by guess;
- a stable re-read path that survives compaction;
- a manifest joined to the call record by prompt sha256;
- an arm label on every call record (`seat.arm` gains `+ctx-variable`).

**Avoid:**
- inheriting the lane's `AGENTS.md` into a planner's context;
- relying on `--auto`-style blanket approval for reads outside the task root (R1 must grant them explicitly);
- showing provenance digests to the planner.

**The orchestrator can do what opencode cannot:** count the exact pulls (which sections, how many bytes) and
cap them in bytes (OAB-12).

**Only the A/B answers:**
- does the 27B read the required files unprompted?
- does critic acceptance change?
- what happens to compactions, peak context and step count?
- does it read everything anyway?
- how does the author behave with a bundle?

### 2. Per-call metrics (S4-T1 vocabulary, OAB-4 columns)

- **The exporter reproduced DS41-C20c exactly** from the real `opencode export`: 23 steps, 25 tool calls
  `{bash 11, glob 1, read 13}`, 1 compaction, 57,702 decoded tokens. **So the PLAIN seat never called the MCP
  perf tools.** The `profile_top`/`symbol_annotate` tools exist only in the bounded seat.
- **What `opencode export` gives:**
  - per-step tokens `{input, output, reasoning, cache.read, cache.write}`;
  - part types (`tool`, `compaction`, `reasoning`, `step-start`).
- **What it does NOT give:**
  - per-tool latency;
  - per-step wall time;
  - which step a compaction hit (the part carries only `tail_start_id`).
- **"Decoded" = `tokens.output` summed over steps, reasoning included.** S4-T1's `turns`/token accounting must
  define the same quantity or the two harnesses are not comparable.
- **Scouts.** `opencode session list` has no parent/child, so scouts are identified as sessions new since the call
  began. Totals sum all sessions (the same rule as VB-AK-SEAT `derive_totals`), and the primary session is the one
  with the most steps.
- **The row is a SIBLING schema, not an extension of VB-AK-SEAT's `actor_call.v1`.** That contract is closed and
  self-hashed. The two lines join on role, backend and the call window, because the v1 `call_id` is generated
  inside root's module and is not returned. The VB-AK-SEAT reader skips foreign-schema lines, so the sibling row is
  safe. Metrics failure becomes `metrics_error` and never fails a call.
- **Traps:**
  - the export truncates when piped (the 98,304-byte fixture), so always export to a file;
  - compaction summaries quote the reply template;
  - `rc=1` can come with a complete reply (salvage);
  - gate on the real binary (`backend.binary == OPENCODE`), not the kind string, or a test double shells out.
- **Copy for the orchestrator:** S4-T1 and OAB-4 should record the same vocabulary — steps, tool calls by name,
  compactions, prompt/decoded/cache-read/cache-write tokens, first/max context, schema-valid, repair-ran — so both
  harnesses land in comparable columns.

### 3. Tool-output cache (R4)

- **Measured** on the real run-7 profile (25.7 MB, 114K samples): uncached `perf report` 1.283 s → hit 0.0012 s,
  **byte-identical** (a hit never invokes perf).
- **The key** is the exact argv plus the profile's identity (realpath, size, `mtime_ns`, first/last-1 MiB hash)
  plus a memoized `perf --version`. `limit` never reaches perf, so one report serves every limit.
- **Placement.** The cache lives beside, never inside, the integrity-checked `cpu-raw` directory.
- **For R4:** a profile at a stable path that is rewritten in place needs a build-id in the key.
- **LEARNING — the premise is likely wrong or partial.** At 1.3 s per call, perf-tool time cannot explain the
  bounded seat's ~12-minute loss in C20c. `annotate` is unmeasured, and the plain seat does not use these tools at
  all. The per-call metrics in the A/B say where the time goes. opencode gives no per-tool latency, so infer it
  from step timestamps if the export carries them; otherwise report it as unknown, never as zero. Status:
  DS41-C20d in [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md).

### 4. The context-placement A/B (OAB-9, 2026-09-25): inline wins

**Setup.** Two ABAB pairs, run 01:28Z to 04:03Z. Pair 3 did not fit the 3.5 h budget.
- Plain opencode seat, research `30631761`.
- :8083 Qwen3.8-27B Q8_0, one server generation (pid 2009477): `-kvu`, a 196,608-token slot, 4 slots.
- The inline control is run 8's planner prompt plus `node_profile` (79,890 chars, sha `a265a03a`). The variable
  arm's prompt is the index only (18,055 chars).
- Evidence: research `605e8301`, `artifacts/autokernel_ctx_ab_20260925/` (README, `driver.py`, `results.jsonl`).
  The replies and bundles stay under `/mnt/raid0/llm/tmp/ak-ctx-ab/`.

| | wall (min) | steps | tool calls | decoded | first ctx | peak ctx | compactions |
|---|---|---|---|---|---|---|---|
| inline p1 / p2 | 37.6 / 28.7 | 23 / 24 | 25 / 26 (bash 22+21, read 3+4, grep 0+1) | 52.9k / 43.8k | 40.6k | 104k / 92k | 0 / 0 |
| variable p1 / p2 | 54.4 / 33.6 | 49 / 29 | 54 / 35 (bash 35+26, read 19+8, grep 0+1) | 68.9k / 47.7k | 19.1k | 163k / 118k | 0 / 0 |

- All four replies were schema-valid: inline gave 1 abstain and 1 hypothesis (`akm-q4k-x4-avx512`); variable gave
  2 abstains. Contention was negligible: 6 of 132 (inline) and 2 of 172 (variable) `/slots` samples had another
  slot busy.
- **Bundle use.** The variable arm used the bundle as designed: 6-7 bundle calls, all 3 required files read, and 0
  `INDEX.md` re-reads. It also read all six file-only sections, which is everything inline carries. Its extra
  calls went to lane SOURCE, with 3-4x inline's tool output (204k/136k vs 65k/34k chars).

**Predictions from → 1, checked:**
- first-step context halves: **confirmed** (40.6k → 19.1k);
- peak falls to ~79k: **refuted** (it rose);
- 0 compactions instead of 1: **moot**, because inline no longer compacts on the kvu slot;
- modest wall gain: **refuted** (+45% and +17% slower).

Not measured:
- critic acceptance (planner-only driver);
- per-tool latency (unknown: `opencode export` has no per-tool or per-step wall).

**Learnings (for OAB-7, OAB-8 and the orchestrator wiring):**
- **A thin prompt made the 27B explore MORE, not less.** Where context is placed does not, by itself, reduce the
  work a planner does. It moves the reads into tool calls, and each tool call re-bills the growing conversation.
- **The RLM-style benefit presupposes a model or scaffold that pulls precisely.** A 27B left to pull freely read
  everything and then some. The orchestrator version has to supply the precision itself, with pull caps (OAB-12)
  and scouts that summarise on the planner's behalf (OAB-8).
- **With 196k slots, compaction is no longer the binding cost.** The OAB-7 rationale ("every arm compacted once")
  came from the split-KV 98k slot. On `-kvu`, inline fits.
- **The next levers are:**
  - the fixed overhead (~13.2k tokens per call, OAB-10);
  - the planner reading its own lane and never building (OAB-11);
  - orchestration-side scouts (OAB-8).

  Hiding context is not one of them.
- **What could change the verdict:**
  - n = 2 with inline always first. Pair 2 was faster for both arms, which looks like a warm prefix cache or
    drift. A 3rd pair tightens the magnitude, but it is unlikely to flip a direction that held on every cost
    metric.
  - A different planner model, one that pulls selectively.
  - A small slot, where inline compacts again.
  - Pull caps.

  Any of these re-opens the question (OAB-9b).

### Tasks

- [x] **OAB-7s — seat-side precursor of OAB-7: the context bundle as files.** ✅ 2026-09-24 — research
  `lane/ak-ctxvar-20260924` `ce5800cb` (143 tests). Merged to research main `30631761` (2026-09-25). **A/B'd in
  OAB-9: it loses to inline on the 27B plain seat**, so the default stays `inline` and `variable` is opt-in.
- [x] **OAB-4m — seat-side precursor of the OAB-4/S4-T1 columns: per-call metrics.** ✅ 2026-09-24 — research
  `lane/ak-turns-20260924` `0bf2d7c2` (`actor_call_metrics.v1` + summarizer; DS41-C20c reproduced exactly).
  Merged to `30631761`. It supplied every OAB-9 column, and it is live in run 9b.
- [x] **R4c — seat-side precursor of R4: cache tool output keyed by exact argv + input identity.** ✅ 2026-09-24
  — research `lane/ak-perfcache-20260924` `f4a5d240` (111 tests; 1.283 s → 0.0012 s, byte-identical). Merged to
  `30631761`. Its effect on the bounded seat has not been re-measured yet (DS41-C20d2).
- [x] **OAB-9 — live A/B: plain inline vs plain variable, AFTER run-9 calibration.** ✅ 2026-09-25 — **INLINE
  wins both pairs** (§Techniques learned → 4; research `605e8301`). Wall 37.6/28.7 vs 54.4/33.6 min, peak
  context 104k/92k vs 163k/118k, 0 compactions and schema-valid everywhere. Predictions: the first-step halving was
  confirmed; the peak, compaction and wall predictions were refuted or moot. Critic acceptance was not measured
  (planner-only driver), and per-tool latency is unknown. 2 pairs; pair 3 was over budget. Run 9 was relaunched
  as `state-run9b` (04:04Z) on the default `inline`, same store, half floor reused. (Run 9 was actually stopped
  at 01:30Z, at the half-floor → batch-0 boundary, not at ~04:45Z; see DS41-C28.) Original spec: at the calibration boundary
  (~04:45Z), stop run 9 (the floors persist per anchor) and merge the integration lane
  `lane/ak-planner-integ-20260924`: the three lanes, the `node_profile` fix in both arms, and the pre-existing
  test fixes. Then run the arms on the same :8083 generation (OAB-4a) with the new metrics rows: 3 pairs
  alternating ABAB, or 2 if time is short (operator-confirmed morning sequence, 2026-09-24 21:40Z). Results go to
  the live results page as well as here. Report:
  - first-step and peak context, compactions, steps, tool calls by name, decoded tokens, wall;
  - schema-valid rate and critic acceptance;
  - which bundle files were read, and whether the required ones were read unprompted;
  - per-tool latency from step timestamps if the export carries them, else "unknown".

  Relaunch run 9 with the winner: same anchor, floors reused, new state dir. Acceptance: the predictions above are confirmed or refuted in
  writing. Inference: campaign-idle GPU window.
- [ ] **OAB-9b — re-open the context-placement question only when a precondition changes.** The trigger is any
  of:
  - OAB-12 pull caps exist in the seat or the orchestrator;
  - the planner model changes;
  - the planner runs on a slot small enough that inline compacts again (≤ 98k).

  Then re-run `artifacts/autokernel_ctx_ab_20260925/driver.py` with **n ≥ 3 in counterbalanced order (ABBA)**,
  because the 2026-09-25 run always put inline first. Also give the driver a byte count per bundle section: it
  records read counts only (`bundle.access`). Acceptance: a verdict per trigger with the same columns as → 4.
  GPU inference, campaign-idle window. Do not run it on an unchanged setup: 2/2 on every cost metric is not worth
  re-buying.
  **Operator, 2026-09-25 07:40Z:** context-as-variable failed ONLY because of opencode: its pulls land in the
  conversation. Revisit it once it is wired directly into the orchestrator REPL/RLM (OAB-7 proper, now built). The
  first OAB-4 run with the context variable on is that revisit.
- [x] **OAB-10 — trim the lane `AGENTS.md` out of the planner's fixed overhead.** ✅ 2026-09-25 — research
  `bdd0a951` (`--actor-trim-instructions`, `--actor-trim-tools`; `run.py` defaults on), merged in `300951de`. Fixed
  overhead per planner call fell 12,912 → 4,950 tokens (−62%); the skills catalog (3,383) was the largest piece,
  `AGENTS.md` 2,009. The one trimmed call measured ctx_first 32.7k, against the predicted 32.9k. The baseline arm
  was aborted at 54+ min (censored; earlier inline baselines on the same prompt and server took 37.6 / 28.7 min),
  and the A/B stopped after one trimmed call, because the overhead cut and the lane fence are deterministic.
  Author behaviour accrues on campaign metrics. It is 8.9k chars (~2.5–3k tokens)
  of llama.cpp contributor guidance in every planner call. Options:
  - a planner-specific instruction file;
  - an `instructions` override in the per-run config;
  - a stripped `AGENTS.md` in the lane.

  The file must stay available to the author, who edits code. Acceptance: the first-step token count falls by the
  measured amount with no change in author behaviour. Orchestrator counterpart: never inherit a repo's agent file
  into a planner context (OAB-7).
- [x] **OAB-11 — the planner must read its OWN lane, not the anchor build tree, and must not build.** ✅ 2026-09-25 —
  research `bdd0a951` (`--actor-lane-guard`: lane-as-source + builds denied through opencode permissions). The
  trimmed call: 6 steps, 10 tool calls, 42.5k decoded, reads lane 4 / anchor 0, builds 0, schema-valid. The plain
  planner read `/mnt/raid0/llm/llama.cpp-experimental-deepseek41-*` (the target's build dir) instead of
  `workers/laneN`, and compiled `.o` files into `/tmp` despite "never build". Fix candidates:
  - point the target card's source path at the lane and label the build dir "binary only";
  - deny `bash` compiler invocations for the planner via `permission`.

  Acceptance: a planner transcript shows reads under its lane and no compiler call. Orchestrator counterpart: R1
  read-only root = the lane.
- [ ] **OAB-12 — pull accounting: count and cap what the planner pulls from the bundle.** opencode cannot report
  which bundle files a model read, or how many bytes, except by parsing `read`/`grep` tool parts after the fact.
  First, have the metrics exporter derive per-section pull counts and bytes from the export's tool parts. Then
  make it a first-class orchestrator feature: exact pulls logged per call, and a byte cap per call. Acceptance:
  OAB-9's report carries per-section pull bytes; OAB-7's orchestrator design names the cap.
  **Progress 2026-09-25.** OAB-9 ran without this. The A/B driver derived per-section read COUNTS from the tool
  parts (`bundle.access`: every file-only section read once, `INDEX.md` never re-read), plus total
  `tool_output_chars`, but no per-section bytes. The seat exporter (`actor_call_metrics.v1`) carries only
  `bundle_tool_calls`. OAB-9's result makes this task the precondition for any retry of context-as-files (OAB-9b):
  the arm lost because nothing capped what it pulled.
  **Orchestrator half built 2026-09-25 (OAB-7, `88e22777`):** `ChatResponse.context_pulls`
  (`epyc.orchestrator.context_pulls.v1`) logs offered vs pulled bytes, unique coverage and per-turn records for
  each section, and `context_pull_budget_bytes` is the per-call cap. Still open: the seat exporter's per-section
  pull bytes.

### Tasks filed 2026-09-25 (integration, opencode store, planner timeline)

- [x] **OAB-13 — integrate OAB-2/7/8, review, deploy.** ✅ 2026-09-25 — integration lanes
  `lane/inf78-integ-20260925` in both repos (OAB-2 → OAB-7 → OAB-8 + a composition test). A second Fable review
  returned research MERGE (research main `82f48e11`) and orchestrator MERGE-WITH-FIXES: F1 scout grep regex DoS
  (literal search now), F2 context closure escapes, F3 sync `/slots` read on the event loop, F4 uncapped exception
  output, F5 restore dropped the bundle, F6 READ past EOF, F7 bounded post-stop wait, F12/F13 encoding and
  recursion guards, F14 test (`86cdeaf3`, `b9e004e3`). The architect scoped exception is `7d0ce447`. Orchestrator
  main `b9e004e3`; the first reload attempt was refused by `orchestrator_stack` while run 9d's calibration held
  the bench. After run 9d was killed, the API reloaded at 14:40:38Z (pid 2517073, API only), the OAB-2 smoke
  passed and the witness stayed quiet.
- [x] **OAB-14 — the opencode store fault that failed an author call.** ✅ 2026-09-25 — root cause: the event
  reaper's no-op VACUUM (freelist 0, a 34 s exclusive lock) started 07:59:17Z in the critic gap; the author started
  07:59:35Z, and its project upsert hit `SQLITE_BUSY` past the 5,000 ms busy timeout (rc 1). Fixes:
  - root `9177edaa`: the prune script skips VACUUM when the freelist is under 1,024 pages, and truncates the WAL
    after a real one;
  - research `e57e93ea` (merged in `300951de`): `snapshot: false` in every per-call opencode config, an
    `opencode_store_error` class with its own 30/60/120/240 s backoff, metrics session scoping by
    `created >= call start` (a failed author row had been attributed the planner's 29-step session), and a
    reasonless `{"accepted": true}` critic reply counted as schema-valid.
- [ ] **OAB-15 — operator decisions on the opencode store** (decision package; OP-59 when the index row lands).
  (a) Global `snapshot: false` for every opencode use: per-call configs already carry it; making it global
  would disable TUI undo. Recommendation: keep it per-call only. (b) A store retention policy: `opencode.db` is
  10.8 GB of live data plus a 10.9 GB WAL, so VACUUM cannot shrink it; only retention can. Recommendation: age out
  sessions older than N days for headless actor runs only. Blocks nothing else on this page.
- [ ] **OAB-16 — give scouts an inference-tap record.** OAB-8 scouts are direct completions that bypass the
  `LLMPrimitives` gates (contention, region lock, inference tap), so their tokens are missing from the tap's
  accounting. Emit one tap record per scout call (role, slot, prompt/decoded tokens, wall), tagged with the parent
  request id. Acceptance: an OAB-4 `orch`-arm call shows its scout calls in the tap next to the planner turn.
- [ ] **OAB-17 — triage the unfixed second-review items F8-F11, F15, F16 and R2-R4.** F1-F7 and F12-F14 landed in
  `86cdeaf3` / `b9e004e3`. Items (Fable review, 2026-09-25 ~12:50Z, file:line against 7d0ce447):
  - F8 MED: scout `/slots` cap is a one-shot snapshot from a 1.5 s-TTL process-wide cache (`scout_stage.py:719-723`,
    `context_limits.py:441-453,521`); two scouted requests (or 6 workers) can both launch and violate `reserve_slots`.
    Fix: `resolver.invalidate(url)` after launch + in-process inflight counter; cross-worker needs a shared counter.
  - F9 MED: scouts share the loop's default ThreadPoolExecutor (32) with chat.py's own `to_thread` handlers
    (`scout_stage.py:880`); 4 scouted requests x 8 scouts starve other handlers. Fix: dedicated bounded executor.
  - F10 LOW: default-path substring patterns `context.get(`/`context.json(`/`context.index(`/`context[` added to
    `exploration_patterns` (`code_utils.py:659-664`) match ANY request (`context[:5000]` idiom now executes silently
    instead of FINAL). Fix: gate on a bundle being attached, or anchor `(?<![\w.])context[\[.]`.
  - F11 LOW: pulled-span list unbounded (`context_bundle.py:744-748`, ~125 B/span). Fix: merge intervals past ~1k.
  - F15 LOW (scouts): `_last_alternatives` shared across scout threads; `definitions()` lacks per-file
    `read_denial`; FIFO/device with a source suffix blocks `read_text` (require S_ISREG); no block-level cap on the
    scout block (~37K tokens worst case); `_EVIDENCE_RE` quadratic; augmented prompt feeds `_select_mode`.
  - F16 LOW (bundle): refused `chunk_context` still charges the budget; structured mode caps twice; `json()` counts
    the indent=2 dump; `get()` on a JSON path records no span; the 8 MiB check runs after full parse; no app-level
    body limit (pre-existing).
  - R2 LOW: `AK_ORCHESTRATOR_SCOUTS="false"/"off"/"3.0"` raise ValueError in `backend_for`.
  - R3 LOW: `orchestrator-variable` context mode has no inline fallback (unlike `variable`).
  - R4 INFO: `_sealed` seals without `role`; per-call files under `<workspace>/../actor-orchestrator/` never cleaned.
  Fix or decline each in writing. Acceptance: every item has a disposition.
- [ ] **OAB-18 — turn on `PREFIX_STABLE_ORDER` for scoped REPL calls, or measure why not.** With the prod default
  (off), each turn's state block precedes the task, so the whole task is re-prefilled every turn: measured on the
  DS41 control prompt, 27,803 → 6,555 uncached tokens per turn with the bundle, and 122 → 1,201 with the flag on
  (`88e22777`). On :8083 that is ~92 s of prefill per turn. Acceptance: a scoped OAB-4 call shows per-turn
  uncached prefill near the flag-on number, with unchanged replies on the REPL suites.
- [ ] **OAB-19 — the compaction worker summarizes text no prompt shows.** Compaction measures and summarizes
  `TaskState.context`, which no turn prompt renders (the same root cause as the schema-preamble bug fixed in
  `1d0ab2f5`). Point it at what the root prompt actually carries, or retire it for REPL turns. Acceptance: a test
  where compaction fires changes the next root prompt.
- [x] **OAB-20 — planner timeline audit (why a planner call takes 30-60 min).** ✅ 2026-09-25 — from the :8083 logs
  of the trimmed call: decode 87% of wall, prefill 13%, gaps 0.3%. One 30k-token reasoning turn (step 6) was 68% of
  the call. `--planner-effort high` maps to opencode `--variant high`, which is inert for this server and model.
  Thinking is ON through the template default: the exports carry `reasoning` parts (82k chars in step 6), so
  `tokens.reasoning = 0` in the metrics is an accounting bug (OAB-21). The giant turns are reasoning prose
  re-deriving the Q4_K bit-unpack formulas ("wait" ×56, "hmm" ×46): 97% of the step comes before any JSON, the
  final JSON is 4%, and visible answers also carry 1.2-1.9k chars of preamble. MTP acceptance is ~0.45-0.53 on
  that prose vs 0.6-0.97 on terse turns, which compounds the cost. The author prompt shows the same pattern.
- [ ] **OAB-21 — fix reasoning-token accounting in `actor_call_metrics`.** `tokens.reasoning` reads 0 while the
  export carries `reasoning` parts. Count them (tokens from the server's usage when present, else chars with the
  estimator flagged), and keep "decoded includes reasoning" explicit. Acceptance: the step-6 call re-exported shows
  a non-zero reasoning count consistent with its 82k chars. Also feeds VB-AK-METRICS-1.
- [ ] **OAB-22 — planner concision rule plus an 8k per-turn cap, together.** Add to `actors.py`
  `_HYPOTHESIS_TASK` (~L1961-1965): derive a formula once, keep analysis under ~4k tokens, then emit JSON only; set
  `max_tokens` 8000 per turn as a circuit breaker. The cap alone would have truncated 5 of the 6 giant turns, so it
  ships only with the rule. Reasoning stays on (operator ruling). The author prompt gets the same rule. Acceptance:
  a matched planner call shows no turn over 8k and a schema-valid reply, with its wall recorded against the 32.8
  min trimmed call.
- [ ] **OAB-23 — a total budget per planner call.** Separate from OAB-22: run 9 showed endless chains of small
  turns (61 min without a reply), which a per-turn cap never stops. Add a per-call decoded-token or wall budget
  that ends the call with a recorded `budget_exhausted` abstention, not a transient retry. Acceptance: a fake
  backend that never finishes is cut at the budget and recorded once.

### Tasks filed 2026-09-26 (DS41 six-lane integration, research main `d643d794`)

- [x] **OAB-24 — author budgets and the opencode output cap.** ✅ 2026-09-26 — lane `ak-author-medium`.
  - Author thinking is set to medium.
  - ctx 180224; author output 40960; planner+critic output 16384.
  - **opencode silently capped `max_tokens` at 32000** unless `OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX` is set, so
    every larger requested budget was inert. The per-call environment now sets it.
  - Also: an action rule and a GitNexus line in the prompts.
  - Also: the `measurement_epoch` resume split. Checkpoints bind on the epoch inputs minus actor/backend config, so
    an actor swap no longer orphans them. The comparability half of this is operator decision DS41-C40.
- [x] **OAB-25 — `ak-check` sandbox for authors.** ✅ 2026-09-26 — lane `ak-sandbox`.
  - A compile check takes ~0.7-6.5 s.
  - `--op-test` takes ~9-15 s, via `test-backend-ops` against the CPU reference.
  - Fence locks.
- [x] **OAB-26 — best-of-2 with mixed authors.** ✅ 2026-09-26 — lane `ak-bestof`.
  - Two authors (thinking off and medium) at 90112 ctx each; requires `--workers 1`.
  - Engaged live on run 10h at 11:00:30Z (two concurrent opencode authors on `akm-q4k-x4t-avx512`).
- [x] **OAB-27 — scope GitNexus to the lane's anchor.** ✅ 2026-09-26 — research `a1c5812b`.
  - The tool now runs `gitnexus --repo <absolute anchor path>`. The bare name `llama.cpp` is ambiguous with the
    frozen production tree.
  - Every actor role is denied the gitnexus index writers.
- [ ] **OAB-28 — best-of member `ak-check` fence sits outside the lane fence set.** The fence is created beside
  the member tree, not in the set the lane scheduler locks.
  - It is harmless under `--workers 1`, which best-of currently requires.
  - It is a real race once best-of runs with more than one worker.
  - Fix: register each member's fence in the owning lane's fence set.
  - Acceptance: a two-worker best-of test in which both lanes' members hold disjoint, scheduler-visible fences.

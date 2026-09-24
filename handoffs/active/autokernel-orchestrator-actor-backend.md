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
v2: 44.3 min, 34 steps, 60.2k decoded, 1 compaction, schema-valid and better grounded (its loss was attributed to perf-tool time,
DS41-C20d — doubted 2026-09-24: the cache measures 1.3 s per uncached call, see §Techniques learned → 3). Pre-fix reference (run 7, escaped prompt): 40.3 min, 71 steps, 63.8k decoded, 2 compactions. Decode
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

## Techniques learned in the opencode seat (2026-09-24, reduced-scope build)

The operator directed a reduced-scope build on the opencode seat while DS41 run 9 calibrated, to learn
what the orchestrator wiring must copy. Three research lanes came out of it. All three branch from research
`origin/main` `170c763c`, are pushed and unmerged, and **none has been A/B'd yet**. The operator called
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

### Tasks

- [x] **OAB-7s — seat-side precursor of OAB-7: the context bundle as files.** ✅ 2026-09-24 — research
  `lane/ak-ctxvar-20260924` `ce5800cb` (143 tests). **Built, not yet A/B'd**; unmerged until the integration lane
  lands.
- [x] **OAB-4m — seat-side precursor of the OAB-4/S4-T1 columns: per-call metrics.** ✅ 2026-09-24 — research
  `lane/ak-turns-20260924` `0bf2d7c2` (`actor_call_metrics.v1` + summarizer; DS41-C20c reproduced exactly).
  **Built, not yet A/B'd.**
- [x] **R4c — seat-side precursor of R4: cache tool output keyed by exact argv + input identity.** ✅ 2026-09-24
  — research `lane/ak-perfcache-20260924` `f4a5d240` (111 tests; 1.283 s → 0.0012 s, byte-identical). **Built,
  not yet A/B'd.**
- [ ] **OAB-9 — live A/B: plain inline vs plain variable, AFTER run-9 calibration.** At the calibration boundary
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
- [ ] **OAB-10 — trim the lane `AGENTS.md` out of the planner's fixed overhead.** It is 8.9k chars (~2.5–3k tokens)
  of llama.cpp contributor guidance in every planner call. Options:
  - a planner-specific instruction file;
  - an `instructions` override in the per-run config;
  - a stripped `AGENTS.md` in the lane.

  The file must stay available to the author, who edits code. Acceptance: the first-step token count falls by the
  measured amount with no change in author behaviour. Orchestrator counterpart: never inherit a repo's agent file
  into a planner context (OAB-7).
- [ ] **OAB-11 — the planner must read its OWN lane, not the anchor build tree, and must not build.** The plain
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

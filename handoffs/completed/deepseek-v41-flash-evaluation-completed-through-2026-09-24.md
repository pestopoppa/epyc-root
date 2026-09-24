# DeepSeek-V4.1-Flash Evaluation — Completed Scope (through 2026-09-24)

Historical ledger only; current work lives in
[`../active/deepseek-v41-flash-evaluation.md`](../active/deepseek-v41-flash-evaluation.md).

**Compacted**: 2026-09-24 (operator-approved partial compaction). This file holds finished (`- [x]`)
detail moved out of the active handoff's **§C — AutoKernel campaign** section, verbatim, so the
active file stays readable for live work. Section heading the moved items came from: `### C —
AutoKernel campaign (operator-directed 2026-09-23)`.

## C — AutoKernel campaign (completed items)

- [x] DS41-C0 — **Preliminary canonical recipe fixed at `-t 48`** (operator: decode matters more
  than prefill). Basis: tg128 13.18 @48t vs 12.74/12.81 @96t; tg512 11.70 @48t vs 10.59 @96t;
  pp512 144-146 @96t vs 137.0 @48t. Prefill keeps 96 where a tool supports the split
  (`--threads-batch`); llama-bench does not. ✅ 2026-09-23
- [x] DS41-C1 — **Codified 2026-09-23**, research `2c68bc1a`: `scripts/lib/deepseek_v41_flash_recipe.py`
  on the qwen38 sibling precedent, inheriting the canonical prefix/OMP/IQK/pre-evict/placement-proof
  with `assert_inherits_canonical()` proving no fork; 23 contract tests pass. Category **CANDIDATE,
  not OPTIMUM**. Every `SPEC_DEC` field is present and `None` with an explicit `flips_on`, and
  `build_serve_command()` **refuses by default** unless the caller passes `spec_dec=False`, so the
  unmet max-performance requirement surfaces at the call site instead of silently. **The thread
  split cannot be expressed by the bench path**: `llama-bench` parses only `-t` and calls
  `llama_set_n_threads(ctx, n, n)`, and the autokernel serving path raises on `-tb != -t` — only a
  direct `llama-server`/`llama-cli` launch can carry 48/96, so a bench pp512 row is not this
  recipe's served prefill rate. ✅ 2026-09-23
- [x] DS41-C2 — **Campaign config prepared 2026-09-23** (`/mnt/raid0/llm/tmp/ds41-ak-config/`:
  CONFIG/LIFECYCLE/LAUNCH/SPECDEC + three ready config files). Four findings:
  1. **`gpt-6-sol` does not exist** — the model cache lists `gpt-5.6-sol`, `gpt-6-astra`,
     `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`; zero occurrences of `gpt-6-sol` anywhere in either
     repo, and no hosted fallback (`OPENAI_API_KEY` unset, the `openai` backend pinned to gpt-4o
     with no live dispatcher). **Reachable gpt-6 is `gpt-6-astra`, effort `high`** → OPERATOR
     DECISION (queued).
  2. **Both actor swaps are CLI flags, not code**, on the unified loop plane (`loop/run.py:670-679`
     exposes `--planner-model/-effort` and `--critic-model/-effort`). The sealed GPU
     `discovery_controller` cannot host a CPU campaign at all (roster exact-equality,
     `ALLOWED_DEVICE_IDS={"mi210_0"}`). Planner needs no source change either: add an
     openai-compatible provider at `http://127.0.0.1:8074/v1` in the opencode config. Smoke-test
     first that the local model holds the structured-output contract.
  3. **Lifecycle: NO — the loop cannot touch :8074.** Every kill targets a `Popen` handle, a
     `start_new_session` pgid or an owned cgroup leaf; the ban on name-pattern signalling is
     enforced by four AST auditors plus a regression test, not convention. Zero `orchestrator_stack`
     call sites, zero `drop_caches`/`munlock`/pre-evict code. The server also runs `--mlock
     --no-mmap`, so its weights are unevictable. The guarantee is structural — there is no knob
     because there is no path.
  4. **The blocker is the inverse of the question**: `competing_inference_witness()` classifies any
     UNOWNED `llama-server` as competing and **raises**. :8074's parent is a containerd shim, so it
     is outside every owned scope and there is no allowlist parameter. **The server is safe; the
     campaign is blocked.** → OPERATOR DECISION (queued). ✅ 2026-09-23
- [x] DS41-C2b-gate — **Competing-inference block resolved and landed** (research `a46c9d3d`): the
  gate now brackets each measured span with cumulative `utime+stime` reads for the unowned
  INFERENCE_LIKE processes, so it asks whether one did WORK, not whether one exists. Monotone
  counters mean a burst between samples cannot hide. Allowance pinned to measurement: over a 279 s
  idle observation all 13 resident servers accrued <= 0.06 core-seconds, so 0.5 core-s + 0.02
  cores/s sits ~100x above idle and ~46x below one busy core. It also converts the operator's "the
  planner never runs during measurement" into a checked invariant. 303 tests. ✅ 2026-09-23
- [x] DS41-C2c — **Dry run steps 1-3 pass.** Binary rebuilt from the committed tree so it
  self-identifies (`version 10310 (ad932bbd9)`, clean tree — it previously reported `7c18bb8c1`
  from an uncommitted build, exactly the INF-70 C9 shape); `verify_ggml_linkage.sh` PASS;
  `verify_llama_cpp.sh` PASS on the frozen tree; critic `gpt-6-sol` high answered a live probe;
  planner answered `{"ok":true}` through the loop's OWN invocation
  (`opencode run -m qwen-local/qwen3.8-flash-next --variant high`), which was the genuinely
  uncertain step since `Backend.argv` always passes `--variant`. Campaign store populated at
  `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/`. ✅ 2026-09-23
- [x] **DS41-C2d — LAUNCH BLOCKER: the recipe layer cannot express DSpark.** ✅ 2026-09-23 — research
  `3d1bf4b2` (type, argv mapping, `--parallel 1` refusal, `LLAMA_SPEC_EXACT` required for greedy with a
  `process_environ` witness) and `5125f7ab` (a greedy draft-dspark template was still not expressible
  as a *canonical* launch: the projection is env-less by construction while the guard requires a
  declared env — the compare now strips env and the frozen launch env is checked instead).
  `loop/resolved_recipe.py:27` has `SPECULATION_TYPES = {"none", "draft-dflash", "draft-mtp"}` —
  no `draft-dspark` — so the prepared recipe is forced to `spec_decode: {"type": "none"}` and the
  campaign would optimise the NO-DRAFTER surface we have already beaten by 1.56x. Patch in
  preparation adds the type, the `-md`/`--spec-type`/`--spec-draft-n-max` mapping, the
  `--parallel 1` refusal (the server refuses multi-slot for draft-dspark), `LLAMA_SPEC_EXACT` as a
  declared measurement key with a witness (its absence must REFUSE, not fall back to the serial
  path — that silent fallback produced the 7.18 t/s reading today), and the drafter in the recipe
  identity.
- [x] DS41-C2e — **Enrollment tooling defect, fixed** ✅ 2026-09-23 (orchestrator `c3f2cbc2`: re-exec moved
  under `__main__`; `test_orchestrator_stack_import_is_argv_safe.py`). Not used by the launch — the
  campaign runs on the roster-free `--manifest` + `--registry-snapshot` route, which is orthogonal to
  the production roster (operator, 2026-09-23). Original note:
  `epyc-orchestrator/scripts/server/autokernel_enrollment.py:276` does
  `from scripts.server import orchestrator_stack`, and that module parses `sys.argv` at import, so
  it sees the ENROLLMENT's flags, prints stack status and exits 0 without writing the output. The
  campaign resolver accepts `--registry-snapshot` as an alternative to `--production-enrollment`
  (`campaign_cli.py:201`), which is the route taken: a
  `epyc.autokernel.artifact_registry_snapshot.v1` file carrying model/build/recipe identities
  (`{schema, kind, ref, path, sha256}` each). Fix the import-time argparse separately.
- [x] DS41-C2b — **LAUNCHED 2026-09-23 18:06** ✅ 2026-09-23 — `serial_run` PID `1586972` (run.py `1586978`),
  store `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/`, inputs built by
  `inputs/build_inputs.py` through the loop's own validators (canonical_launch.v1, frozen prompt v2,
  IDENTITY receipt on `build-cpu`, manifest + snapshot, `--verify-artifacts` passed on all 5).
  Serving metric `aggregate_tok_s` on the DSpark greedy-batched recipe, `--rounds 0`,
  planner `opencode:qwen-local/qwen3.8-flash-next@high` (the live :8074 server, unchanged), critic
  `codex:gpt-6-sol@high`. First launch had `perf record`+`perf stat` attached. It opens with the
  loop's 48 matched calibration launches. Superseded launch note (llama-bench surface): `--surface tg128` (the default
  is `pp512` and MUST be overridden), `--confirm-surfaces dec-b4,dec-b8`, `-t 48`, cpu_list 0-95,
  np 1. There is no `tg512` surface. `Recipe` carries one `threads` field, so pp512 rows from this
  target are off-optimum and must not be reported as prefill results — prefill is a second target.
- [x] DS41-C3 — **The campaign measures the spec-dec-on surface** ✅ 2026-09-23 — target declares
  `speculation: external_draft` + `drafter_ref local:ds41:drafter-dspark`; new type `draft-dspark`, not
  `draft-mtp` (the assumption below was wrong, as suspected). Original:
  Blocked on DS41-B13. The schema already supports it (`TargetSpec.speculation` ∈
  `{none,self_draft,external_draft}` + `drafter_ref`; `spec_decode:{type:"draft-mtp",…}` →
  `-md/-ngld/--spec-type/--spec-draft-n-max`, `draft_n_max: 5` from DSpark's block). The target
  declares `speculation` from day one so no interim number can be mistaken for a spec-dec result,
  and the drafter lands as a **second target**, not an edit. **Biggest unverified assumption:**
  whether `--spec-type draft-mtp` can drive an *external* DSpark-shaped drafter at all — it was
  built for self-drafting heads and may need a new speculation type plus a server path.
- [x] DS41-C5 — Seeded ✅ 2026-09-23 as `store/inbox/30-ds41-seeded-hypotheses.md` (ranked H2 requant
  ladder, H1b verify-marginal attribution, H3 rowexact-on-dense, H4 entropy-gated block, H1 demoted,
  H6, H7; measured basis and falsifiers; re-read by the planner every iteration). The
  `opportunities.json` profile form stays unbound (placeholder digests) — the inbox is the channel.
  Budget guidance: **decode is flat 24->96 threads**, so barrier and
  dispatch levers cannot pay on this model. Point the campaign at the memory path (engram gather,
  expert gemv), not at parallelism.
- [x] DS41-C12 — **All three in-tree profilers wired into the loop** ✅ 2026-09-23 (operator: "give
  autokernel access to ALL the profiling tools"). llama.cpp `ebb68dc55`: Engram gather/per-layer
  counters landed, compile-gated on `GGML_CPU_PROF` with `LLAMA_ENGRAM_PROF_JSON_FILE` (measured
  `build-cpu` carries zero instrumentation strings). Research `c6a46674` (`loop/node_profile.py`,
  17 tests on real dumps) + `e59c87ea`: `reprofile()` builds a `-DGGML_CPU_PROF=ON` sibling of the
  anchor, launches it only inside the profile window with `GGML_CPU_PROF_JSON_FILE`,
  `LLAMA_HOST_PROF_JSON_FILE`, `LLAMA_ENGRAM_PROF_JSON_FILE`, level 2, parses the three dumps into
  `node_profile` in the planner context (per-op shares, host phases, Engram fault mix), cached by the
  perf capture's key, never in a ranked A/B; `--node-profile` rides `--common-args`; teardown waits
  180 s so a `--no-mmap` server's atexit dumps survive. Proven on run 3's anchor at 19:38:
  `teardown: terminated`, all three `observed`; experts 42.1% / dense 38.3% of wall,
  `ctx.graph_compute` 99.2% of the decode step, Engram 0 major / 0 minor faults per decode token.
- [x] DS41-C13 — **Campaign restarted as run 3** ✅ 2026-09-23 19:28 (`state-run3/serial-run.pid`
  = 1953258). Run 1 (perf only) stopped and archived (`store-run1-ad932bbd9`); run 2 refused —
  the shared store pinned run 1's champion-of-record `ad932bbd9` against anchor `ebb68dc55`
  ("never relabel the tip build"), so run 3 uses a fresh store with the inbox carried over.
  Anchor/inputs/resolution rebound to `ebb68dc55`, artifact verification 5/5.
- [x] DS41-C16 — **Schema-constrained repair turn for actor replies** ✅ 2026-09-24 (research `ad2b89ff`,
  `HEAD`, `loop/actors.py` `_parse_reply`/`_schema_repair`): the typed-decision plane's TD-1 idiom
  applied to the loop's planner/author/critic replies — when the agentic reply's JSON is missing or
  incomplete, two constrained `response_format json_schema` turns on the same local server (explicit
  decline boolean, then pure extraction; reviews skip the boolean). Proven on the 27B with the report
  lost at 03:09 plus four shapes, 2–12 s each; three refuted designs recorded in the module.
  **Intake gap:** `typed-decision-plane.md` never listed AutoKernel's actors as a consumer of the
  pattern; the loop was the largest free-text-JSON consumer in the stack.
- [x] DS41-C17 — **Planner seat moved to `qwen-gpu/qwen3.8-27b`** (MI210, :8083) ✅ 2026-09-24
  08:52, run 6, request r3. Measured basis: 27B 86 t/s decode / 302 t/s prefill vs flash-next 50 / 92;
  CPU planner proposals 97 and 41 min (prefill-bound, 124 k tokens of tool output), authoring #1 killed
  at the 7200 s budget after 91 k output tokens (decode-bound). `--variant` is a no-op on a plain
  OpenAI-compatible provider. Related fixes: `--actor-timeout-s` (`ef287ba9`), raw reply persistence +
  stderr fallback (`704ef037`), partial output kept on timeout (`3471fe3c`), `stage_timeout_s` 900→2700
  (perf profile was refused at the 900 s cap). Filed: planner server :8074 runs `-t 96` while the registry
  recipe says `threads: 48` (`NUMA_FULL_T48`) — launch/registry divergence, stack owner's.
- [x] DS41-C19 — **v10 folded-lineage fix reaches this campaign** ✅ 2026-09-23 (non-inference ROI session,
  research `714777e4`, fast-forwarded into the shared research clone 20:3xZ). At v10
  `MEASUREMENT_COMMIT == PRODUCTION_COMMIT`, so `candidate_record.build_candidate_record`'s old
  "instrument parents == (production,)" rule was unsatisfiable: the FIRST CPU candidate of this campaign to
  reach recording (`campaign.py:5011`) would have raised `ValueError("instrument commit is not the ratified
  single-child of the production base")`. The shared `worktree.instrument_lineage_ok` now accepts the folded
  identity and still requires the source to descend from production (`ebb68dc55` descends from v10
  `ffc1bac82` — verified). Same fix in `live_controls` preflight. Nothing had hit it yet (run3 still in
  batch 0; no lineage error anywhere under the campaign dir). The running batch process keeps its
  already-imported modules; the next batch process loads the fix — no mid-process version mixing
  (all three modules are imported at load time).

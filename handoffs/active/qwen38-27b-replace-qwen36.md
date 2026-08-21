# Qwen3.8-27B — replace Qwen3.6-27B in production

**Status**: ACTIVE — download/smoke/MTP/throughput/architect-bench done; **stack-template swap DONE 2026-08-20** — `1cff5162` ("stack template: architect_general -> Qwen3.8-27B; draft_max 24 -> 8 (measured)", 2026-08-20 21:52:11Z), whose *only* changed file is `repos/epyc-orchestrator/stack_templates/default.yaml` (`git show --stat`: 1 file, +7/-2). **CORRECTED 2026-08-21 (second pass): the MASTER registry swap IS done** — `b376dadd` ("registry: swap architect_general + coder_escalation to Qwen3.8-27B; draft_max 4 -> 8", 2026-08-20 12:19) is a LOCAL, UNPUSHED commit in **epyc-inference-research**, whose `orchestration/model_registry.yaml` is the TRUE master; the orchestrator's same-named file is the AUTO-GENERATED lean view (banner at its head) and was audited by mistake. What is NOT done is the **compile chain**: `orchestration/model_registry.yaml` contains **zero** occurrences of the fixed string `Qwen3.8` (`grep -F -c` → `0`, re-verified 2026-08-21), and `architect_general` / `coder_escalation` there still carry `model_role: qwen36_27b_mtp_q8_local` (`model_registry.yaml:1501`, `:1398`) — so a registry-vs-stack-template divergence stands until the registry is updated **and** the derived layer regenerated. **THIRD PASS 2026-08-21: the compile chain is now DONE too** — ratification executed (`ratify_qwen38_registry_swap_20260821.sh` v2; orchestrator `7483d7fb`): derived `stack_priors.yaml` verified serving Qwen3.8-27B-Q8_0 @ draft_max 8 on architect_general. (The earlier "`b376dadd` resolves in no repo" was an artifact of the research repo's `safe.directory` config defeating the check; it resolves fine and is on origin since `bb405297`.) Remaining: Q38-T5 stack start + `live == config` checklist (operator-sequenced), Q38-T4 third edit + recompile. Full evidence: *Research Intake — 2026-08-21*.
**Created**: 2026-08-14
**Priority**: P2 (model refresh; no production pain forcing it, but a same-day release refresh is cheap to stage)
**Effort**: Low-Medium — download/smoke/MTP/throughput/architect-bench done; the registry swap is the last step (the 2026-08-14 quality-gate decline was later reversed and the coding ladder ran)

## Objective

Stage `Qwen3.8-27B` as the replacement for `Qwen3.6-27B-MTP-Q8_0`, which is the **primary model for
`architect_general` + `coder_escalation`** (both served from the :8083 MI210 process, ROCm0; the 122B
vacated to `architect_critic` 2026-07-31). Qwen3.8 was released 2026-08-14.

## What is known (verified against HF on release day)

- Upstream: `Qwen/Qwen3.8-27B` (public, not gated), plus `Qwen/Qwen3.8-2.4T-A95B` (the large sibling).
- **Qwen3.8-27B is MULTIMODAL** — a vision projector (`mmproj`) ships alongside it. This is a new
  capability vs the text/code-only Qwen3.6-27B; treat it as optional, not a migration requirement.
- **MTP/NextN head is EMBEDDED in the unsloth base — NOT a separate sidecar (CORRECTION).** GGUF-header
  verification (`llama-gguf r`) shows the unsloth `Qwen3.8-27B-Q8_0.gguf` carries `blk.64.nextn.*`
  tensors (`eh_proj`/`enorm`/`hnorm`/`shared_head_norm`) and `qwen35.nextn_predict_layers` metadata —
  the same embedded self-draft layout as `Qwen3.6-27B-MTP-Q8_0`. So the wiring is **same-file
  `--spec-type draft-mtp` self-draft, unchanged from Qwen3.6**. The ggml-org `mtp-*.gguf` (3.16 GB) is a
  *full layer-64* draft model (`attn` + `ffn` + `nextn`) for the ggml-org base (which strips MTP) — it is
  **redundant** for the unsloth base and was downloaded only as a fallback.

## Artifacts

| Artifact | Source | Size | Status |
|---|---|---|---|
| `Qwen3.8-27B-Q8_0.gguf` | `unsloth/Qwen3.8-27B-GGUF` | 29.05 GB | ✅ downloaded + header-verified (embeds nextn/MTP) |
| `mtp-Qwen3.8-27B-Q8_0.gguf` | `ggml-org/Qwen3.8-27B-GGUF` | 3.16 GB | ✅ downloaded (redundant fallback; unsloth base embeds MTP) |
| `mmproj-Qwen3.8-27B-Q8_0.gguf` (optional, vision) | `ggml-org/Qwen3.8-27B-GGUF` | 0.63 GB | not downloaded |

Destination: `/mnt/raid0/llm/models/`. Download log: `/tmp/opencode/dl_qwen38.outerr`.

## Steps

- [x] **Verify the download** ✅ 2026-08-14 — both files at full declared size (29,047,086,048 B /
  3,164,006,688 B); GGUF header shows arch `qwen35`, `block_count`, `context_length`, and the embedded
  `nextn`/MTP tensors in the base (see "What is known" — the MTP-sidecar assumption was wrong).
- [x] **Load smoke** ✅ 2026-08-14 — PASS on v9 HIP (`-ngl 999 -c 4096 --spec-type draft-mtp --spec-draft-n-max 4`): model loads (31.98 GB VRAM), generates coherently ("Quicksort is a highly efficient sorting algorithm…"), no op-fallback warnings.
- [x] **MTP wiring** ✅ 2026-08-14 — RESOLVED: the unsloth base embeds the nextn/MTP head, so
  `--spec-type draft-mtp` self-draft is same-file, exactly like Qwen3.6-27B-MTP. `draft_model` in the
  registry stays the same file. The separate `mtp-*.gguf` sidecar is NOT needed.
- [x] **Quality gate — DECLINED by operator (2026-08-14):** *"quality will improve certainly."* The
  Qwen3.8→Qwen3.6 quality uplift is taken as a given (same-day release refresh); no coder/architect
  quality comparison will be run. The load-smoke below is the only remaining correctness check, and it
  confirms the model loads + generates — a technical check, not a quality gate.
- [x] **Throughput (optimized mode, GPU `draft-mtp`)** ✅ 2026-08-14/15 — prefill pp512 **727.29 t/s**; single-stream decode **flat ~45 t/s across 2k–32k depth** on real olympiadbench prompts (peak aggregate **157 t/s @np8**). **CORRECTION:** an earlier synthetic random-word probe showed a spurious 37→13.6 t/s decline + "MTP reversal at depth" — that was a prompt artifact (random words kill MTP acceptance), NOT real behaviour. On real prompts decode is flat and MTP holds. (natural-prompt single-shot 47.57 t/s still stands as the interactive figure.)
- [x] **Registry swap** ✅ 2026-08-20 — master registry commit `b376dadd`. `architect_general` +
  `coder_escalation`: `model` / `model_path` / `draft_model` / descriptor `name`+`path` →
  `Qwen3.8-27B-Q8_0.gguf` (self-draft, same file). `epyc-orchestrator/stack_templates/default.yaml`
  also repointed, and its `spec_overrides.draft_max: 24` corrected — that override was **silently
  beating** the registry's measured value at stack-assembly time.
  - **`model_role` was the trap.** It is load-bearing, not documentation: `model_descriptors.py:1233-1244`
    substitutes the `model_role` role's config when an alias's model id differs from its `server_mode`
    entry (recording `ignored_model_id`). Swapping `model_path` alone would have **served Qwen3.6 while
    the registry read as swapped**. Both refs now point at a new `qwen38_27b_q8_local` role;
    `qwen36_27b_mtp_q8_local` is RETAINED unmodified as the rollback anchor.
  - **`draft_max` 4 → 8, re-measured not inherited.** 4 was the measured optimum for *Qwen3.6*; depth is
    per-model. Qwen3.8 sweep (np=1, 12 real olympiadbench prompts, v9 `0db32c06e`/10125): plain 27.78 /
    n2 39.77 / n3 46.61 / n4 51.03 / n6 55.22 / **n8 55.46** / n12 51.14 t/s; acceptance 0.842 → 0.482
    across depth 2→8. Curve turns over past 8. MTP is worth **2.00× over plain** at n-max 8.
  - Every figure in the new role is measured on THIS artifact: `baseline_tps 27.78`, `optimized_tps 55.46`,
    `vram_gib 37.22` (n_slots=4, n_ctx 262144, q8_0 KV, kv_unified=true, sampled DURING residency).
    `optimized_tps_long_context` and `contended_tps` are explicitly `null` — not measured, and copying
    Qwen3.6's across would be a false attestation.
  - Validator: **0 problems** (this required fixing a pre-existing duplicate-key defect that had been
    failing the validator closed for the whole file — commit `a94e0e01`).
  - **2026-08-21 CORRECTION (Q38-T2, this box's claim does not hold).** Everything in this bullet
    describes the MASTER registry, and the master registry does not contain it. `grep -F -c 'Qwen3.8'
    orchestration/model_registry.yaml` → `0`; `git log -S 'Qwen3.8' -- orchestration/model_registry.yaml`
    → **empty** (no commit has ever added that string); there is no `qwen38_27b_q8_local` key anywhere in
    `orchestration/`; and the working tree is clean for that file (`git status --short` → no output). Only
    `stack_templates/default.yaml` was repointed (`1cff5162`). Because the launched `-m` path is read from
    `orchestration/derived/stack_priors.yaml`, **not** from the stack template, a start today would serve
    **Qwen3.6**, not Qwen3.8. Box left ticked as another session's record; the corrected state is in
    *Research Intake — 2026-08-21 → Q38-T2*.
- [x] **dFlash2 np1 folded in as decision context, selection UNCHANGED** ✅ 2026-08-20 — cross-session
  campaign measured **70.0 decode t/s** at matched np=1 vs a same-campaign MTP n-max-8 arm at 55.2
  (+26.81%), acceptance 0.628 vs 0.482. Independently verified here: `campaign-summary.json` SHA-256
  matches `e4f9e21f…` and the figures re-read correctly. Their matched MTP arm reproduces our 55.46 to
  within 0.5%. Recorded in the registry (`bd40ca94`) as `challenger_under_evaluation`, status
  `np1_only_NOT_SELECTABLE`; `spec_type: draft-mtp` / `n_max: 8` untouched. **No selection published.**
- [ ] **DFlash2 selection decision** — BLOCKED on three named gates before it may displace MTP: np2/4/8
  scaling, exact greedy parity at temp 0, and the block-verify dispatch proof. Owned by the autokernel
  session under INF-62; this row exists so the registry side has a visible decision point.
- [x] **Q38-T4 ✅ 2026-08-21 — CLOSED, and neither proposed fix was the right one: the "drift" was a CHECK-TIME MODE ARTIFACT.** The guard builds its launch view against the realized fleet mode, defaulting to `full` in a clean shell (`stack_change_guard.py:1183-1191`, `stack_numa_mode.py:10`), which filters the half instances out of the view while the master unconditionally projects them into `serving.ports`. Under the PRODUCTION mode (`ORCHESTRATOR_STACK_NUMA_MODE=both`) all 13 errors vanish with ZERO data edits; after a mode-correct `update` (re-pinning the launcher hash the jinja fix had legitimately broken) the check is **FULLY GREEN — `guard: ok`, `guard_strict: ok`, `acceptance: no-inference checks passed`** — the first fully green stack-change check of the campaign. Master, topology, stack template and launch manifest were all correct all along; the ratify script now exports the mode. (Earlier annotation about launch-manifest-vs-accepted_gaps options is superseded. CORRECTED FRAMING 2026-08-21 (after a reverted over-read): the flagged ports are
      the HALF instances, which are LIVE production config** — `stack_templates/default.yaml:93-94`
      and `:121-122` launch them (`{port: 8080, numa: HALF_A, threads: 48}` …). The operator's
      "no quarter instances anymore" covers quarters only (retired 2026-07-30); an over-broad
      reading briefly removed 2 of 3 half-port sites from the master working tree — caught by the
      operator, reverted verbatim, and the recompile never ran, so no artifact or serving state was
      affected. THE REAL FIX therefore runs the other way: represent half mode in
      `orchestration/launch_manifest.yaml` (whose comments already name the half ports) so
      `guard_all_surfaces` sees them as launchable — or file exact `(role, gap)` accepted_gaps
      declarations. Operator to pick the direction; the master is not the defect. Original finding
      follows. — quarter-port surface drift (pre-existing, surfaced 2026-08-21 by the ratification's
      post-check).** `guard_all_surfaces` fails on frontdoor / ingest_long_context / toolrunner /
      worker_* because their `serving.ports` declare quarter-instance ports (8080/8180/8082/8182/…)
      that `orchestration/launch_manifest.yaml` carries only as comments. Unchanged since 2026-03;
      failed identically before this ratification's writes. Either represent quarter mode in the
      launch manifest or file exact `(role, gap)` `accepted_gaps.yaml` declarations (expiry
      required). Blocks a fully-green `check`; does NOT block the swap surfaces, which verify clean.
- [ ] **Q38-T5 — post-CT-1 stack start + checklist (operator-directed 2026-08-21).** As soon as
      CT-1's arms complete: (a) verify no autokernel GPU work is running (none is as of 14:05Z —
      no codex session listed, no claims, no KFD processes expected); if one appeared, negotiate a
      quiet window with that codex agent (via workspace-c0 if not directly reachable) before
      touching the GPU; (b) start the stack via `orchestrator_stack.py` (the lean auto-recompiles
      at start; derived is already regenerated and verified); (c) run the stack-change checklist:
      `live == config` — confirm architect_general serves Qwen3.8-27B-Q8_0 at draft_max 8 on
      :8083, `verify_ggml_linkage.sh`, non-zero VRAM sampled DURING a request, KFD process count;
      (d) close the ticked-but-stale 2026-08-20 checklist item against this evidence.
- [ ] **Stack-change checklist / `stack_change_pipeline.py` regenerate** — NOT run. Nothing is serving
  (`:8083` unbound), so config and runtime agree only by both being absent. `live == config` is
  UNVERIFIED until someone actually starts the stack; that is a separate lifecycle action with its
  own gates and was deliberately not taken here.
- [x] **Architect bench (reasoning + coding ladders)** ✅ 2026-08-15 — L0–L4: mmlu_pro 56.7%, gpqa_diamond 42.4% (letter) / 81.3% (CoT), aime25 **76.7%**, olympiadbench_hard 47.1%; P2a–P2d: humaneval 96.3%, BCB-hard 31.1%, LCB-hard **52.8%** (tops stock 45.3%), SWE-oracle 39/40 single-shot (2 hard tool-using instances deferred to the agentic rung). Full tables in `gpu-candidates-surface-qwen38-update.md` + the artifact dir. The quality uplift the operator banked is now measured — it is real on LCB (52.8 vs 45.3) and aime25 (76.7), near-parity elsewhere, with SWE + agentic still landing.

## Key questions this handoff must answer

1. ~~**MTP sidecar vs embedded**~~ — ANSWERED 2026-08-14: the unsloth base EMBEDS the nextn/MTP head
   (`blk.64.nextn.*` present in the GGUF header), so it is a like-for-like replacement for
   `Qwen3.6-27B-MTP-Q8_0` with **same-file self-draft** — no wiring change. The ggml-org sidecar is a
   full layer-64 draft model for the ggml-org (MTP-stripped) base and is redundant here.
2. **Multimodal**: is the vision projector a reason to *also* stage Qwen3.8 for `worker_vision`/
   `vision_escalation`, or strictly out of scope for this coder/architect swap?
3. ~~**Is this even worth it**~~ — RESOLVED by operator (2026-08-14): quality uplift is a given, so the
   swap is worth it on quality grounds alone. Throughput won't move materially (dense, BW-bound); the
   throughput step exists to record the serving baseline, not to gate the decision.

## Research Intake — 2026-08-21 (chat-template dive, intake-1212…1217)

> **Ratification package v2 (2026-08-21):** `scripts/operator/ratify_qwen38_registry_swap_20260821.sh`
> — phase 0 reverts v1's mistaken edits to the GENERATED lean file (inverse-edit byte-proof), phase 1
> adds the provenance block to the TRUE master, phase 2 runs `stack_change_pipeline.py update
> --allow-descriptor-model-removal` with a targeted only-removal assertion + derived verification +
> post-check green, phase 3 is the `--jinja` fallback fix. Never commits in the research repo (the
> LFM2.5 orphan decision is pending in the same file). `--dry-run` validated end-to-end.

**CORRECTION 2026-08-21 (same day, second pass — recording the error so it cannot be re-derived).**
The Q38-T2 finding "the master registry was never swapped" was WRONG-LEVEL. Three facts replaced it:
1. `orchestration/model_registry.yaml` in the **orchestrator** repo is **auto-generated** — its own
   head banner reads "AUTO-GENERATED — MASTER-COMPILED RUNTIME VIEW", compiled at every stack start
   from the research repo's master by `src/registry/registry_compiler.py` (`compile_lean`). Every
   audit read the file from the middle and missed the banner; the pipeline's `lean_registry: stale`
   error is what surfaced it.
2. **The true master WAS swapped on 2026-08-20 by `b376dadd`** — a local, unpushed commit in
   epyc-inference-research (one of the 9 in that repo's reconciliation backlog). The earlier
   `git cat-file -t b376dadd` "resolves in no repo" check was defeated in the research repo by its
   `safe.directory` git-config problem. The swap there is complete: `model_role`, both literal path
   sets, `draft_max: 8` in both maps.
3. **The real gap is the compile chain**: lean, descriptors and derived `stack_priors.yaml` were all
   compiled 2026-08-11, and the launcher reads the derived file AS-IS (`orchestrator_stack.py:252-262`
   — no priors recompile at start; only the lean auto-recompiles). So the operational conclusion of
   Q38-T2 stands — a stack start today serves Qwen3.6@4 — while its provenance claim is corrected.
The v1 ratification script edited the generated lean view and its phase-2 `check`-as-gate aborted on
the expected staleness report; v2 supersedes it as above. Method lesson, same shape as the retention
correction earlier today: a compiled artifact was audited as if it were its source; the file's own
banner said so; nobody read line 1.

Three findings landed here by a chat-template intake round, all verified by rendering the template
**embedded in our own** `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf` (extracted by a GGUF header
read, without loading the 29 GB model) alongside the stock `Qwen/Qwen3.8-27B` template.

- [x] **Q38-T1** ✅ 2026-08-21 — **Both defects are UNREACHABLE under current config**: `reasoning_effort` has 0 occurrences in `src/` and 0 in `orchestration/` (no code path sends it), and the llama-server payload is a hardcoded single `user` turn (`src/backends/llama_server.py:560`, `:1316`) so the template's assistant branch that produces the blank `<think>` is never entered. Recorded + reachability established. Two real defects on the template we now serve. (a) With inline-`<think>` history,
      stock **and** our Unsloth variant emit a blank `<think></think>` immediately before every real
      thought — five `<think>` occurrences where three are warranted. (b) `reasoning_effort` handling
      **diverges from upstream**: stock *raises* on `high`, our Unsloth variant silently *coerces*
      `high → xhigh`. An OpenAI-style client sending the ordinary value `high` therefore gets a hard
      500 against stock and silent maximum-effort reasoning here — opposite failure modes, neither
      what the caller asked for.
- [x] **Q38-T2** ✅ 2026-08-21 — Status line fixed in place: the real commit is `1cff5162` in `repos/epyc-orchestrator/stack_templates/default.yaml` (`b376dadd` resolves in none of the three repos); master registry has **0** `Qwen3.8` occurrences; and **the stack template is NOT what the launcher reads** — `-m` comes from `orchestration/derived/stack_priors.yaml` (`orchestrator_stack.py:134`, `:252-262`, `:1062-1071`), which still names Qwen3.6. Registry provenance: re-resolve the swap commit. This handoff's status line cites
      `b376dadd`, which resolves in **none** of epyc-root, epyc-orchestrator or
      epyc-inference-research. The Qwen3.8 swap that *does* resolve is `1cff5162` in
      `repos/epyc-orchestrator/stack_templates/default.yaml`, and
      `orchestration/model_registry.yaml` still contains **zero** occurrences of the fixed string
      `Qwen3.8` — `architect_general` and `coder_escalation` there still name Qwen3.6-27B.
- [x] **Q38-T3** ✅ 2026-08-21 — Non-stock Unsloth template recorded below with digests (ours 9,993 B `sha256:12827f24b742…` vs stock 8,952 B `sha256:c3cf9e34abf4…`); the registry-descriptor edit is **PREPARED, NOT APPLIED** (registry is operator-frozen — snippet + insertion point handed to the dispatching session). Record that we serve a **non-stock (Unsloth) template** (9,993 B, ending
      `{#- Unsloth fixes - developer role, merged system messages, tool calling #}`) rather than the
      stock 8,952 B one, and that no registry descriptor says so.

**Not a task, recorded so it is not rediscovered:** our stack-wide
`chat_template_kwargs.enable_thinking: false` is **role-keyed**, so it survives the model swap. It
also makes us immune both to the template's `xhigh` default and to the `reasoning_effort` raise,
because the raise sits *inside* the `enable_thinking` gate and is unreachable when thinking is off.

### Q38-T1 findings — reachability of the two template defects (2026-08-21)

Both defects are real **in the template**. Neither is reachable **through our stack**. Evidence below is
read-only inspection of `repos/epyc-orchestrator` plus the template extracted from our own GGUF
(`qwen38_official.jinja`, byte-identical to `Qwen3.8-27B-Q8_0.gguf.jinja`, `cmp` → identical).

**(a) `reasoning_effort` divergence — UNREACHABLE: nothing sends the field.**

- `grep -rn "reasoning_effort" src/` → **0 hits**. `grep -rn "reasoning_effort" orchestration/` → **0 hits**.
  Every occurrence in the orchestrator lives in `scripts/` and none of them reaches llama-server:
  - `scripts/validate/reasoning_effort_certifications.py:44` validates a registry `reasoning_effort.level`
    key — which no role declares (the 0-hit grep above), so the check is vacuous today.
  - `scripts/analysis/reviewer_policy_arm_ab.py:184` *parses* the knob, but `_DECODE_KNOBS` (`:197`) is
    `("temperature", "top_p", "top_k", "min_p")` and `:217` emits only those. The parsed value is never
    read back anywhere in the file — a dead knob, not a payload field.
  - `scripts/autopilot/planner_providers.py:303` passes `--config model_reasoning_effort="…"` to the
    **codex CLI** (`cmd = [self._binary, "exec", "--json", …]`, `:292-300`), not to llama-server.
- The two llama-server payload builders construct the dict literally and never add the key:
  `src/backends/llama_server.py:559-563` (non-streaming) and `:1315-1319` (streaming).
- **Second, independent guard.** In our template the *entire* `reasoning_effort` block is inside the
  thinking gate: `qwen38_official.jinja:58` opens `{%- if enable_thinking is undefined or enable_thinking
  is true %}`, and the `xhigh` default (`:59`), the silent `high → xhigh` coercion (`:60-61`) and the
  `raise_exception` (`:63-64`) all sit within it. The handoff's standing note claimed this gating only for
  the *raise*; verified here, **all three effects — default, coercion and raise — share the same guard**,
  so with `enable_thinking: false` none can fire even if a caller did send the field.

**(b) Blank-`<think>` duplication — UNREACHABLE: no assistant turn ever reaches the template.**

- *Template precondition*, verified at `qwen38_official.jinja:113-120`: the assistant branch reads **only**
  `message.reasoning_content` (`:115-116`) and never parses inline `<think>` out of `content`. When a
  caller puts the thought inline, `reasoning_content` trims to `''`, so `:120` emits
  `'…\n<think>\n' + '' + '\n</think>\n\n' + content` — a blank think block immediately before the real one.
  **It requires a structured `messages` array carrying a `role: "assistant"` entry.**
- *Our payload has no such entry.* `src/backends/llama_server.py:560` and `:1316` both hardcode
  `"messages": [{"role": "user", "content": user_content}]` — one user turn, always; no assistant entry,
  no `reasoning_content` key, and `request.extra["messages"]` is not consulted on this backend.
- *Inbound multi-turn requests are flattened before they get there.*
  `src/api/routes/openai_compat.py:468` takes `request.messages[:-1]` as history; `_context_parts_from_history`
  (`:248-265`) renders each turn as the plain string `f"{role_label}: {content}"`; `:494` joins them into a
  single `context` blob. An assistant `<think>` therefore arrives as **literal text inside the one user
  turn** — the template's assistant branch is never entered. (Side note, not the defect under audit: raw
  `<think>` markup can thus be echoed back into a prompt as user text.)
- *The one place that does build assistant history targets a different model.*
  `src/api/routes/chat_vision.py:584` (`messages.append({"role": "assistant", …})`) posts to
  `_vl_url_for_port(vl_port)` (`:547-548`) — the vision role's port serving `Qwen3-VL-30B-A3B-Instruct`,
  not `:8083`.
- *The one backend that would honour caller history is dead.* `src/backends/openai.py:240-241` does read
  `request.extra["messages"]`, but `OpenAIBackend` is never instantiated in `src/` (only its own docstring
  example `:7-10` and the `src/backends/__init__.py:29` re-export), and local roles are constructed as
  `LlamaServerBackend` (`src/llm_primitives/backend.py:143`, `:247`, `:334`, `:345`, `:397`).

**(c) `enable_thinking: false` confirmed for both Qwen3.8-serving roles.**

- `orchestration/model_registry.yaml:1396-1397` (`coder_escalation`, block opens `:1391`) and `:1499-1500`
  (`architect_general`, block opens `:1487`) — both under the top-level `server_mode:` section (`:1351`),
  which is exactly the section `RegistryLoader.get_role_chat_template_kwargs` reads
  (`src/registry/registry_loader.py:513-517`; it explicitly does **not** read the `roles:` section).
- Executed against the orchestrator venv: `chat_template_kwargs_for_role('architect_general')` →
  `{'enable_thinking': False}`; `'coder_escalation'` → `{'enable_thinking': False}` (also `frontdoor`,
  `architect_critic`; `worker_general` → `None`).
- Two further belts on the launch side, from the derived layer:
  `orchestration/derived/stack_priors.yaml:363` sets `flags.reasoning: 'off'`, emitted as `--reasoning off`
  (`scripts/server/orchestrator_stack.py:1431-1433`); and `:357` sets `flags.jinja: true`, emitted as
  `--jinja` (`orchestrator_stack.py:1402`), which is what keeps requests on the `/v1/chat/completions` +
  jinja path where `chat_template_kwargs` is actually applied.

> **Verdict.** Both defects are **unreachable under current config**, and each is blocked twice over
> (no sender / no assistant turn, *plus* the `enable_thinking` gate). They become reachable only if
> someone (i) starts sending `reasoning_effort`, or (ii) replaces the hardcoded single-user-turn payload
> with real `messages` history — **and** turns thinking back on for these roles. Treat those two as the
> tripwires, not the template.

### Q38-T2 findings — commit provenance and which artifact actually wins at start time (2026-08-21)

**Provenance.**

| Claim | Verification | Result |
|---|---|---|
| `b376dadd` (cited in the old status line) | `git cat-file -t` in epyc-orchestrator, epyc-root, epyc-inference-research | `fatal: Not a valid object name` in all three |
| `1cff5162` | `git log -1`, `git show --stat` | `1cff5162c7e6f6d103beb8cb12747b4e0da30bf6`, 2026-08-20 21:52:11 +0000, *"stack template: architect_general -> Qwen3.8-27B; draft_max 24 -> 8 (measured)"*, **1 file changed** — `stack_templates/default.yaml` (+7/-2) |
| Master registry swapped? | `grep -F -c 'Qwen3.8' orchestration/model_registry.yaml` | **0** |
| Ever swapped? | `git log -S 'Qwen3.8' -- orchestration/model_registry.yaml` | **empty** — no commit in history ever added that string |
| Uncommitted swap sitting in the tree? | `git status --short -- orchestration/model_registry.yaml` | no output (clean) |
| `qwen38_27b_q8_local` role exists? | `grep -n 'qwen38_27b' orchestration/model_registry.yaml`; `grep -ril 'qwen3\.8\|qwen38' orchestration/ --include='*.yaml'` | **no match anywhere** — `architect_general:1501` and `coder_escalation:1398` still read `model_role: qwen36_27b_mtp_q8_local` (defined `:2468`) |

**Which source wins at start time: the MASTER REGISTRY, via the derived layer — not the stack template.**

The launch chain is `orchestration/model_registry.yaml` → (`scripts/registry/stack_change_pipeline.py`
regenerate) → `orchestration/derived/stack_priors.yaml` → launcher:

- `src/registry/stack_priors.py:30` — `DEFAULT_REGISTRY = REPO_ROOT / "orchestration" / "model_registry.yaml"`
  (input); `:32` — `DEFAULT_OUTPUT = REPO_ROOT / "orchestration" / "derived" / "stack_priors.yaml"` (output).
- `scripts/server/orchestrator_stack.py:134` — `STACK_PRIORS_PATH = … / "orchestration/derived/stack_priors.yaml"`;
  `:252-262` `_stack_prior_launch()` reads that file and returns `launch.requirements`; `:1062-1071` (and the
  sibling builders at `:727`, `:783`, `:908`, `:922`) take `-m` from `_runtime_string(requirements, "model_path", …)`.
- **`stack_templates/default.yaml` supplies no path.** `src/config/stack_templates.py:135-217` `load_template`
  parses `model:` only as a *name string* into `RoleConfig.model`; the file's own serving facts are resolved
  through `src.registry.stack_priors` (`:26-31`). And `_validate_stack_prior_parity` (`:303`, running to `validate_template` at `:385`) compares
  **ports only** — it never compares models, so the Qwen3.8-vs-Qwen3.6 divergence passes validation silently.
  `validate_template`'s model-existence check (`:485-500`) emits a **warning**, not an error.

**Consequence, stated plainly:** `orchestration/derived/stack_priors.yaml:332-333` still reads
`model_path: /mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf` and the same for `draft_model_path`
(`grep -F -c 'Qwen3.8'` on that file → **0**; `'Qwen3.6'` → **25**), with `spec.draft_max: 4` (`:370`), and
the file's mtime is **2026-08-11 01:36** — predating both 2026-08-20 edits. **A stack start today would
launch Qwen3.6-27B-MTP-Q8_0 with draft depth 4**, i.e. neither the model nor the `draft_max: 8` the stack
template declares. The `stack_change_pipeline.py` regenerate is therefore not a formality on the remaining
checklist — it is the step that makes the swap real, and it cannot help until the **master registry** is
swapped first, because it compiles *from* that file.

### Q38-T3 findings — the served GGUF embeds a non-stock (Unsloth) template (2026-08-21)

| Template | Bytes | `sha256[:12]` | Note |
|---|---|---|---|
| `Qwen3.8-27B-Q8_0.gguf` (ours, served) | 9,993 | `12827f24b742` | Ends `{#- Unsloth fixes - developer role, merged system messages, tool calling #}` |
| Stock `Qwen/Qwen3.8-27B` | 8,952 | `c3cf9e34abf4` | No trailing marker |
| `Qwen3.6-27B-MTP-Q8_0.gguf` | 8,057 | `55d4931433fe` | byte-identical to the 35B-A3B below |
| `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` | 8,057 | `55d4931433fe` | — |
| `Qwen3.5-122B-A10B-UD-Q4_K_M-00001-of-00003.gguf` | 7,992 | `8452ca85cb1e` | — |

- Our embedded template is **1,041 bytes larger** than stock and carries an explicit Unsloth provenance
  marker as its final line. `cmp` confirms the separately extracted `qwen38_official.jinja` and
  `Qwen3.8-27B-Q8_0.gguf.jinja` are byte-identical, so the two names denote one artifact.
- **No registry descriptor records this.** `grep -c -F 'Qwen3.8' orchestration/model_descriptors.yaml` → `0`;
  `grep -n 'chat_template' orchestration/model_descriptors.yaml` → only two `enable_thinking` references
  (`:341`, `:676`), neither a template-provenance record. Nothing anywhere in `orchestration/` states that a
  served GGUF's chat template diverges from its upstream.
- **Scope discipline:** the Qwen3.6 / Qwen3.5 rows above are recorded as digests only. Whether *those*
  diverge from their own upstreams is **UNVERIFIED** — no stock counterpart was extracted for them this round.
- **Registry-descriptor edit: PREPARED, NOT APPLIED.** The registry is operator-frozen and a subagent may
  prepare but not apply an index/registry row, so the exact snippet and insertion point were handed to the
  dispatching session rather than written. It must land in the **master** `orchestration/model_registry.yaml`
  (under the top-level `roles:` map, `:1599`), never in `orchestration/model_descriptors.yaml` — that file is
  a compiled artifact (`descriptor_version: 3`, `status: compiled`, `compiled_at: '2026-08-11T01:36:32Z'`,
  `source_registries.lean.path → orchestration/model_registry.yaml`) and a recompile would overwrite any
  hand-edit. The snippet models itself on the existing `thinking_control:` precedent at
  `model_registry.yaml:1580-1585`.

## Research Intake Update — 2026-08-21 (Stage-2b, intake-1276)

- [ ] **(Z) Record the fla #1156 exposure for our own Qwen3.x GDN family.** Upstream
      `flash-linear-attention` issue #1156 (OPEN, 2026-08-20) reports `ShortConvolution` **backward**
      returning silently wrong gradients on ROCm at every shape tested, and its **headline case is the
      Qwen3.5 family** (48 of 64 layers on Gated DeltaNet; at conv width 10240 it faults with
      `hipErrorIllegalAddress` rather than corrupting silently).
      **Scope this correctly — it is not a serving defect.** This handoff is pure inference/serving
      config, and the hazard is on the **training/fine-tuning** path through fla. It matters here only
      because it names our *model family*: anyone training or fine-tuning a Qwen3.x GDN model through
      fla on this host risks silently wrong conv gradients. The ROCm-side ownership and the
      version-floor question live in `rocm-verify-profile-backend.md` (G6). Track #1156 to close.

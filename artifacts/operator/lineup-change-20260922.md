# Lineup change 2026-09-22 — master-registry diff, hunk by hunk

**Artifact**: `/workspace/artifacts/operator/lineup-change-20260922.patch`
**Target**: `epyc-inference-research/orchestration/model_registry.yaml` (the MASTER, the only
hand-edited registry) — 752 insertions, 297 deletions, 28 hunks, one file.
**Status**: DRAFTED, NOT APPLIED. `git apply --check` passes in the research repo against
`5a701081` (the file's current tip; working tree clean for it). The resulting YAML parses
(`yaml.safe_load`, 15 top-level keys, 188 `roles`, 17 `server_mode`).

Nothing under `orchestration/derived/`, nothing in the lean registry, nothing in
epyc-orchestrator was touched.

---

## 0. Schema confirmation (asked for before edits)

**The compiled-artifact claim is verified from the lean file's own banner**, not taken on trust:
`epyc-orchestrator/orchestration/model_registry.yaml:1-18` reads *"AUTO-GENERATED —
MASTER-COMPILED RUNTIME VIEW … compiled at every `orchestrator_stack.py start` from the master
registry at /mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml by
`src/registry/registry_compiler.py`"*, with a live `Compiled at: 2026-09-22T09:42:15+00:00` and a
cache key. A hand-edit there is clobbered at the next start.

**The shape actually found in the master** (11,635 lines), with line numbers as-found:

| Concern | Where it lives | Notes |
|---|---|---|
| Launch config: port, slots, device, KV, memory | `server_mode.<role>` (`:801-1707`) | **This is the load-bearing block.** |
| KV feasibility | `server_mode.<role>.serving_shape` (`:811-873` doc) | `{n_ctx, slots_by_shape, kv_quant, kv_kib_per_token_f16, vram_non_kv_gib}` declared as **ONE block, validated together** by `stack_manifest.validate_serving_shape_capacity()`. Splitting them into flat keys is explicitly forbidden. |
| One server, N roles | `server_mode.<primary>.shared_with` | `registry_compiler.py:71-73` reads this to resolve an alias to its process. `alias_of` on the alias row is **documentation only**. |
| Model/quality/recipe records | `roles.<name>` (`:1824-10452`) | A **flat namespace mixing real roles with a model catalogue** (`qwen36_q8_0`, `*_local` exact-artifact rows). |
| Candidate-role tags | `roles.<key>.candidate_roles` | `try_cheap_first` is an existing value here (`:4299, :4358, :4440, :4582, :4731`) — the operator's tag maps onto the schema with no invention. |
| Acceleration | `roles.<name>.acceleration` (canonical) + a mirrored copy in `server_mode` | The mirror was re-added 2026-06-26 "for record consistency"; both must agree. |
| Process roster | `process_layout.hot_resident` (`:10452`) | A FLAT list of role names; encodes nothing about sharing. |
| GPU device | `device: ROCm0` + `ngl: all` (`:1343-1344`) | plus `serving.device` / `n_gpu_layers` in the `roles` mirror (`:5369-5370`, `:5466`). |

**Deprecation convention — precedent found, reused, nothing invented.** The registry uses a
three-key marker on the model/role row itself:

```yaml
    deprecated: true
    deprecated_date: 2026-05-27
    deprecated_reason: "Role removed in the 2026-05 production stack consolidation; model
      REAP-246B deprecated + GGUF deleted 2026-05-27 …"
```
(`roles.reap_246b:2469-2471`; the same shape at `:1421-1423`, `:1910-1912`, `:1979-1981`,
`:2125-2127`, `:2534-2536`, `:3776-3778`, `:3981-3983`, `:4094-4096`, `:4771-4773`.)
`tier: X` accompanies it (`roles.qwen36_q4km:4092`). There is also a separate
`deprecated_models:` **graveyard list** at `:10980` — but every entry there carries a
`deleted: <date>` and a `path_was:`, i.e. it is the **post-deletion ledger**, not the
role-retirement marker. The operator said deletion happens separately at session end, so the diff
uses the `deprecated:`/`deprecated_date:`/`deprecated_reason:` marker and each reason states
explicitly *"GGUF REMAINS ON DISK; deletion is a separate operator action at session end."*
No graveyard rows are added. That is the correct half of the existing convention for this moment.

---

## 1. The hunks

### H1 · `server_mode.frontdoor` — CPU 35B primary → GPU alias on `:8083`
Rewritten on the **`coder_escalation` precedent** (`:974-1021`): an alias declares no
`serving_shape` ("it launches no server, so it HAS no serving shape of its own"), keeps the flat
back-compat `kv_quant`, sets `alias_of`, and sets `acceleration.type: none` +
`inherits_spec_from` — where `none` means *launches no draft of its own*, **not** *runs without
speculation*. `model_role` is repointed to `qwen38_27b_q8_local` because
`model_descriptors.py:1233-1244` substitutes the `model_role` role's config when an alias's model
id differs from its `server_mode` entry; a stale value there serves the old artifact while the
registry reads as swapped. `numa_ports` is retained as an explicit singleton `[8083]` rather than
deleted — `backend.py:207`, `placement.py:186` and `cpu_region_lock.py:641` all **fail OPEN** on an
unknown port. `no_mmap` is dropped (a host-RAM NUMA remedy, inert and actively harmful under
`-ngl all`). Throughput `40.22 → 55.46` and the May-4 benchmark record is nulled, not carried.

### H2 · `server_mode.worker` — gemma4-26B → Qwen3.6-35B-A3B-MTP-Q8_0, +`worker_summarize`
The 35B does not leave the fleet; it moves wholesale from the vacated `:8070` group to `:8072`.
`shared_with` becomes `[worker_explore, worker_math, toolrunner, worker_summarize]` — five role
names on one process. `kv_kib_per_token_f16` `480.0 → 82.0`; the external gemma drafter is
removed and `draft_model` becomes the same file (self-draft, launcher omits `-md`);
`draft_max 2 → 4` (the 35B's value, not gemma's — depth is per-model **and** per-drafter);
`threads_draft`/`ubatch` deleted with the drafter process they tuned. `no_mmap: true` added
(load-bearing: three instances, shared-mmap first-touch placement, measured 40.91 → 52.13 tok/s).
The terse chat template travels with the artifact. Throughput `56.86 → 40.22`.

### H3 · `server_mode.worker_vision` — MI210 → CPU
`device: ROCm0 → cpu`; `vram_mb: 21049` and `serving_shape.vram_non_kv_gib: 19.26` **deleted**
(the latter is the GPU capacity check's input — leaving it would keep charging a vacated card
19.26 GiB and veto the headroom this migration creates); `memory_gb: 0 → 18.29`;
`host_non_kv_gib: 18.29` added; `no_mmap: true` restored. `kv_quant` q8_0/q8_0 is **kept** —
the MMMU-250 non-inferiority result is a quantisation result and carries, but its
attention-kernel caveat (f16→TILE, q8_0→VEC were **HIP** kernels) does not, so the +0.80 pp delta
is re-opened rather than re-confirmed. `throughput: 112.20 → null` — see C6.

### H4 · `server_mode.architect_critic` — Qwen3.5-122B → Qwen3.8-Flash-Next, +`ingest_long_context`
`model_role` → the new `qwen38_flash_next_ud_iq4xs_local` row; `shared_with: [ingest_long_context]`;
`memory_gb 69 → 90`; `kv_quant q4_0/f16 → f16/f16` (**forced**, not chosen — see C2);
`kv_kib_per_token_f16 98.0 → 96.0` with the measured constant carried alongside; `draft_model`
points at the **separate** MTP head GGUF with an extended warning; `draft_p_min: 0.5` added; a new
`recipe:` pointer block carries the six facts a registry reader must not have to open a Python
file to learn. The 122B's entire throughput record (24.00/15.76/11.30) is relocated, not copied.

### H5 · `server_mode.ingest_long_context` → alias on `:8074`
Same alias shape as H1. `:8085/:8185/:8285` vacated. The block-level comment enumerates the four
things this role gives up (shape, concurrency, lock isolation, `spec_type: none`).

### H6-H10 · `roles.*` mirrors
`roles.frontdoor`, `roles.worker_general` (+`try_cheap_first` candidate-role tag),
`roles.architect_critic`, `roles.ingest_long_context`, `roles.worker_vision`,
`roles.vision_escalation`. `roles.architect_general.shared_with` gains `frontdoor` — **this is the
load-bearing half of the frontdoor migration**, `alias_of` is not.

### H11 + D1-D5 · New catalogue rows and deprecation markers
- **NEW** `qwen38_flash_next_ud_iq4xs_local` — the incoming artifact, registered *before*
  cutover (the rule the retired 2.6B rungs broke), carrying the full codified recipe, the MTP
  head's identity and rejected alternatives, and three `constraints.forbid` entries.
- **NEW + deprecated** `gemma4_26b_a4b_orig_q4km_local` and
  `qwen3_next_80b_a3b_instruct_q4km_local`. Both served production for months and **had no
  catalogue row at all** — they existed only inside the `server_mode`/`roles` entries this change
  repoints. Creating the row at retirement is the only way the artifact does not vanish without
  trace; each carries its as-served performance record.
- **deprecated** `qwen35_122b_q4km`, `gemma4_26b_a4b_q4km_mtp`,
  `draft_gemma4_26b_a4b_assistant_q8`.

---

# 2. CONSEQUENCES NOT NAMED IN THE SPEC

## C1 — The change re-creates the exact escalation defect Directive 3 was written to fix. ★

After this change, `frontdoor`, `coder_escalation` and `architect_general` are **the same GGUF in
the same `:8083` process**. Every escalation chain in the registry degenerates:

| chain (`:10478-10527`) | hops | after |
|---|---|---|
| `coder` | frontdoor → coder_escalation | **both `:8083`, same process** |
| `reasoning` | frontdoor → architect_general → architect_critic | **hops 1-2 same process** |
| `general` | worker_general → frontdoor → architect_general → architect_critic | **hops 2-3 same process** |

The registry names this failure mode itself, in the `coder` chain's own description: *"Between
2026-05-09 and 2026-07-31 both hops were the SAME GGUF in the SAME process, so escalating could
only change the sampling seed."* Directive 3 split them to fix it. This change puts them back.
Related: `roles.frontdoor.candidate_roles` still excludes `coder` with the rationale *"so autopilot
does not treat frontdoor and coder_escalation as interchangeable coder arms, which they no longer
are"* — that rationale has **inverted**; they now are. The diff leaves the list unchanged and
flags it, because re-adding `coder` is a routing decision, not bookkeeping.

**This is not fixable inside the registry.** It needs either a different frontdoor model or a
re-cut escalation topology. It is the one item I would not ratify without a decision.

## C2 — Flash-Next's two roles: the single recipe, and what each gives up. ★

The operator's framing ("deep-reasoning critic" vs "long-context ingest at 262144 spec=none") is
**less conflicted than it looks in two ways and more conflicted in a third.**

**The shapes already agree.** `architect_critic` is `n_ctx 262144, slots_by_shape {full: 1}` and
`ingest_long_context` is `n_ctx 262144, slots_by_shape {full: 1, half: 1}` — both already serve
262144 at one slot per instance. There is no context conflict to resolve.

**`spec=none` is not a role property.** It is a Qwen3-Next-80B property, stated as such in the
canonical policy block (`:156-168`): *"its recurrent state cannot fork, so NO draft-model path
exists and none can be built."* qwen4exp ships an MTP head. The constraint leaves with the model,
and the diff deletes `roles.ingest_long_context.constraints.forbid` for exactly that reason.

**THE PROPOSED SINGLE RECIPE** (`server_mode.architect_critic`, inherited by the alias):
`n_ctx 262144` · `slots 1` · `-ctk f16 -ctv f16` · `--spec-type draft-mtp --spec-draft-n-max 4
--spec-draft-p-min 0.5 -md mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf` · `-t 48` ·
`taskset -c 0-95 numactl --interleave=all` · `--no-mmap -fa on` ·
`GGML_NOHUGEPAGE_PROCESS=1 GGML_FA_SPLIT_KV=0 GGML_IQK=1 GGML_FUSED_DECODE_OFF=1` + canonical OMP.

**What `architect_critic` gives up**: its asymmetric `q4_0/f16` KV. The change is **forced, not
chosen** — `qwen38_flash_next_recipe.py:698-701` and its `assert_kv_f16()` at `:994-998` refuse
anything but f16, because B9 measured MTP acceptance α `0.8274 → 0.8166` under quantised KV, i.e.
the KV saving is paid back out of the speculation multiplier. The critic's "V at f16 preserves
critic quality" rationale survives; its "K quarters cleanly" half does not.

**What `ingest_long_context` gives up — and this is the expensive half:**
1. **Its preferred shape.** It is the *one* role in the fleet whose split beats its full under
   load (aggregate tok/s at T=8: half **86.17** vs full **72.53**). `architect_critic` has one
   full instance and no sub-full shape. The halves are gone; `burst_prefer_split` has nothing to
   prefer. **~−16% aggregate at T=8.**
2. **Concurrency.** Three instances × 1 slot → **one slot**, shared with the critic. Ingest and
   critique now serialize against each other.
3. **★ Isolation from the whole-machine lock.** `architect_critic`'s single full instance on 0-95
   holds **all four CPU region locks** while it runs (`stack_numa.py:274-276`), serializing the
   entire CPU NUMA topology. The operator's own D2 ruling (2026-07-31) narrowed the `reasoning`
   chain to `explicit_request` only *specifically so routine traffic could never summon that
   lock* — *"the machine's response to being slow would be to invoke the one role that makes
   everything slower — a positive-feedback loop, not a remedy."* `ingest_long_context` **is**
   routine traffic (Stage 1 of `three_stage_summarization`). Merging them reaches the D2 hazard
   by a route D2 does not cover, and the prerequisite D2 named — `region_lock_wait_s_by_holder`
   telemetry — **still does not exist anywhere in the codebase.**

The single recipe is expressible. Item 3 is the reason I would raise it before applying.

## C3 — Three epyc-orchestrator changes the registry diff cannot make (out of scope, must not be forgotten)

`stack_topology.yaml` is the *input of record* for per-role NUMA wiring and is **not** regenerated
from the master. The diff is inert without these:

1. **`numa_config.frontdoor` and `numa_config.ingest_long_context` must be DELETED.** Both roles
   become aliases that launch no server. The 2026-08-01 W1 cutover set the precedent verbatim:
   *"A role with no process of its own must not carry NUMA wiring — that wiring is what would
   launch a second server."* Left in place, they launch CPU servers on `:8070`/`:8085` for roles
   that are supposed to be elsewhere.
2. **★ The Flash-Next recipe VIOLATES an import-time invariant.** `THREADS = 48` on a `0-95`
   cpuset, and the module says why: *"NOT 96: the served decode optimum on this model."*
   `stack_numa._assert_instance_invariants` requires `-t` to equal the cpuset's **physical core
   count** (96 for `NUMA_FULL`) and raises at import. There is no half-machine-cpuset-with-48-
   threads `cpu_shape`, and `GPU_HOST_LANE` is the only exemption. **Either a new CPU shape is
   declared, or the invariant gains a documented exception, or the role loses its measured
   optimum.** A `numa_config` typo or unknown field also raises — this will fail loudly, not
   silently, which is the good news.
3. **`numa_config.worker_general.spec_overrides`** is `{draft_max: 2, p_split: 0}` — gemma's
   external-drafter tuning. It must become `draft_max: 4` or it will override the registry back
   to gemma's depth on the 35B. `numa_pre_evict_gib: 40` is also sized for a 16 GiB model and
   `architect_critic`'s is sized for 69 GiB, not 90.

## C4 — The Flash-Next serving shape is a 32× extrapolation of a shape that was never served.

| axis | what the recipe measured | what `:8074` will declare |
|---|---|---|
| context | **`CONTEXT = 8192`**, hard-wired; no ctx parameter and no ctx branch anywhere in the module | **262144** |
| deepest ever benched | **d4096** | — |
| slots | `PARALLEL_SLOTS = 1` | 1 ✓ |
| artifact | `IQ4_XS-uniform` **single file**, 98,392,912,256 B, sha256 `4bfb9849…` | the **UD-IQ4_XS 3-shard** set, 93,682,584,224 B |
| kernel | `ef81196d5` / build **10241**, `llama.cpp-experimental` | production **v10** `ffc1bac82` / build **10303** |

I verified the model will at least **load** on production: `qwen4exp` appears 180 times in
`/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin/libllama.so`. That is a support check,
not a performance transfer — nothing about the numbers crosses a kernel without a re-bench.
The recipe module itself says the served-vs-anchor reconciliation *"is PROD-3's job"*, and
`CHAMPION_PIN_RESOLVED = False`.

There is **no measured KV figure for this model at any context above 8192, anywhere.** The
arithmetic below is derivation from a header-verified constant, clearly labelled as such.

## C5 — Quality: four gates lost, zero gates gained, no suite re-run.

| role | what it loses | replacement gate |
|---|---|---|
| worker lane (5 roles) | gemma's **tool_compliance 96%** and full-suite **90%** — *the properties that won it the role in 2026-05* (+18pp / +6pp over Qwen3-Coder-30B-A3B) | **none.** The 35B has never run the worker battery. `toolrunner` is an alias on this process, so tool compliance is the first thing to re-measure. |
| `architect_critic` | **quality_score 2.57/3** | **none.** No critic-suite gate has ever been run on qwen4exp. This role exists *for* critique quality; swapping it on speed alone changes the thing it provides. |
| `ingest_long_context` | **25/27 (93%)** canonical long_context, and the 2026-01-26 "best summary quality" finding | **none.** Both are Qwen3-Next-80B results. |
| `frontdoor` | the E-7 2026-08-22 live-path stamps (math 82.5 / mmlu_pro 37.5 / gpqa_diamond 55.0 / cruxeval 32.5) | **none** — those are 35B stamps. The 27B's terse-template deployment is already flagged in-registry as *"unmeasured-on-model"*. |
| vision | the MMMU-250 KV-quant A/B's *kernel* leg | re-opened on CPU. |

The diff **nulls** rather than carries every one of these, because a stale number that a router
reads is worse than a null that halts it.

## C6 — Throughput, and a routing-prior hazard.

`q_scorer.registry_baseline_tps_by_role` reads `server_mode.<role>.throughput` **first**, ahead of
`roles.*.performance`. So these are not documentation, they re-price routing the moment the
compile runs:

- **Worker lane: `56.86 → 40.22` t/s short ctx (−29%), `27.01 → 22.59` long ctx (−16%).** Applies
  to all five roles on `:8072`.
- **Vision: `112.20 → null`.** 112.20 was an MI210 median (n=250 MMMU turns) for a 17.3 GiB
  Q4_K_M MoE at `-ngl 999`. **I will not estimate a CPU figure** — no measured CPU/GPU ratio for
  this model exists on this host. Carrying 112.20 would make the router price CPU vision at
  roughly 5-10× its real speed and preferentially route to it. Re-measure before cutover.
- **frontdoor: `40.22 → 55.46`** (the 27B's own measured optimum, n-max 8, np=1).
- **architect_critic: `24.00 → 43.281`** — with the C4 caveats. Note the operator cited ~52.7 t/s
  token-weighted; the recipe module's `HEADLINES["champion_final_20260908"]` carries **43.281**
  MTP / 27.893 plain (n=6, between-launch sd 0.356-0.609%, ratio 1.5516). Both figures exist in
  the campaign; the diff uses the module's, since that is the citable one.

## C7 — Does it fit? Yes, comfortably, on both sides.

**GPU — MI210, ONE card (`rocm-smi --showid` confirms a single GPU[0]), 68,702,699,520 B = 63.98 GiB usable.**

| | non-KV | KV @ 65536 | total |
|---|---|---|---|
| Qwen3.8-27B Q8_0 | 27.33 | 8.13 (q8_0, 130.0 KiB/tok) | **35.46** |
| Qwen3-VL-30B Q4_K_M + mmproj | 19.26 | 3.00 (q8_0, 48.0 KiB/tok) | **22.26** |
| whisper.cpp + Qwen3-TTS | — | — | **~2.57** (residual: 60.29 observed − 57.72 accounted) |
| **now** | | | **60.29 / 63.98 → 3.70 GiB free** |
| **after (VL leaves, frontdoor is an alias costing 0)** | | | **38.03 / 63.98 → 25.95 GiB free** |

frontdoor adds **zero** VRAM: same GGUF, one server, one allocation — the project's standing rule
does the work. On-disk sizes are verified: 27B Q8 = 29,047,086,048 B (27.05 GiB), VL Q4_K_M =
18,556,687,200 B (17.28 GiB) + mmproj 1,083,499,584 B (1.01 GiB).

**Headroom that is now available but NOT taken in this diff** (deliberately — "do not
over-engineer the GPU packing"): at `n_ctx 131072` the 27B's KV is 16.25 GiB → total 46.15 GiB,
17.8 GiB spare, **and it restores frontdoor's 65536 per slot at 2 slots** (see C8). At 262144 the
KV is 32.50 GiB → total 62.40 GiB, 1.58 GiB spare — too tight; do not. The diff leaves
`n_ctx: 65536` and its DO-NOT-RAISE banner intact; raising it is a one-line follow-up the capacity
check will validate.

**CPU — 1133 GiB total, 693 available, current `llama-server` RSS 405.93 GiB over 17 servers.**

| leaving | GiB |
|---|---|
| 3× gemma4-26B (`:8072/:8082/:8182`) | 62.50 |
| 3× Qwen3-Next-80B (`:8085/:8185/:8285`) | 147.90 |
| 1× Qwen3.5-122B (`:8074`) | 78.50 |
| **freed** | **288.90** |

| arriving / staying | GiB |
|---|---|
| 3× Qwen3.6-35B-A3B (unchanged, re-keyed `:8070/:8080/:8180` → `:8072/:8082/:8182`) | 124.80 |
| Qwen3-VL-30B on CPU: 18.29 weights + ~3.00 KV @65536 q8_0 | ~22 |
| Flash-Next: 87.25 trunk + 2.60 MTP head + 6.00 KV + ~2.25 head KV + ~1.5 unmeasured buffer | **~99.6** |

Net `llama-server` RSS **405.93 → ~239 GiB** on the measured-KV basis (**~257 GiB** if the
conservative 96.0 KiB/tok gate figure is used instead of the measured 24.0). **~150-167 GiB of
host RAM is freed.** Against 1133 GiB total and a ~701 GiB mlock budget, RAM is nowhere near
binding. **The CPU constraint in this change is the region lock (C2) and the thread invariant
(C3), not memory.**

Flash-Next KV derivation, since no measurement exists above 8192: the GGUF header declares
`qwen4exp.block_count 48`, `full_attention_interval 4`, `head_count_kv 2`, `key_length 256`,
`value_length 256` → **12 of 48 blocks carry KV**; 12 × 2 × 512 × 2 / 1024 = **24.0 KiB/token
f16** = **6.00 GiB at 262144**. The `-md` head adds ~9 KiB/token (implied by the one live
readback: 264 MiB total KV at 8192 against a 192 MiB trunk share) ≈ 2.25 GiB. The registry's
`kv_kib_per_token_f16` is left at the **conservative 96.0** (all-48-blocks) to match the file's
own stated hybrid convention — over-stating a model that is not the binding constraint is the safe
direction — with the measured 24.0 carried alongside in new keys.

## C8 — Roles whose declared `ctx` cannot be met by the new model. One, and it is frontdoor.

| role | declared | new model can serve | verdict |
|---|---|---|---|
| **frontdoor** | 262144 total / **65536 per slot** (4 slots) | `:8083` gives 65536 total / **32768 per slot** (2 slots) | **★ PER-SLOT CONTEXT HALVES.** The 27B's `ctx_max` is 262144; the binding constraint is the deliberate MI210 cap, which the registry banners as DO NOT RAISE. C7 shows 131072 now fits with 17.8 GiB spare, which would restore 65536/slot. |
| ingest_long_context | 262144 | qwen4exp `context_length: 262144` — **header-verified, in-training, not a rope extension** | meetable in principle; **never served above 8192** (C4). |
| architect_critic | 262144 | same | same caveat. |
| worker_general + 4 aliases | 262144 | 35B `ctx_max` 262144 | ✓ unchanged. |
| worker_vision / vision_escalation | 16384 (`roles`) / 65536 (`server_mode`) / 8192 (`stack_manifest.LAUNCH_CONTEXT_TOKENS`) | all met on CPU | ✓ — but this **three-way disagreement is pre-existing and survives the change**. What the move does break is that the one "measured" value of the three was measured on a backend the role no longer runs on. |

Separately corrected while the row was open: `roles.worker_general.model.max_context` read
**16384** while `server_mode.worker.serving_shape.n_ctx` has read **262144** since 2026-08-02 —
two values for one quantity in one file, 246k tokens apart. The 16384 was a gemma4 KV-imbalance
cap and leaves with gemma.

## C9 — Retired-model role audit: every role has a new home. No orphans.

Against `kernel_freeze_scope.py --backend {cpu,gpu}` (the authoritative map; cpu returns 8
roles / 4 models, gpu 4 roles / 2 models — both confirmed by running it):

| role | backend now | old model | retired? | new home |
|---|---|---|---|---|
| architect_critic | cpu | Qwen3.5-122B UD-Q4_K_M | **YES** | Flash-Next, `:8074` primary ✓ |
| ingest_long_context | cpu | Qwen3-Next-80B Q4_K_M | **YES** | Flash-Next, `:8074` **alias** ✓ |
| toolrunner | cpu | gemma-4-26B ORIG Q4_K_M | **YES** | 35B, `:8072` alias ✓ |
| worker_explore | cpu | gemma-4-26B ORIG Q4_K_M | **YES** | 35B, `:8072` alias ✓ |
| worker_general | cpu | gemma-4-26B ORIG Q4_K_M | **YES** | 35B, `:8072` **primary** ✓ |
| worker_math | cpu | gemma-4-26B ORIG Q4_K_M | **YES** | 35B, `:8072` alias ✓ |
| worker_summarize | cpu | Qwen3.6-35B-A3B MTP Q8 | no | 35B, **moves `:8070` → `:8072`** ✓ |
| frontdoor | cpu → **gpu** | Qwen3.6-35B-A3B MTP Q8 | no | 27B, `:8083` alias ✓ **(changes backend)** |
| architect_general | gpu | Qwen3.8-27B Q8 | no | unchanged ✓ |
| coder_escalation | gpu | Qwen3.8-27B Q8 | no | unchanged ✓ |
| worker_vision | gpu → **cpu** | Qwen3-VL-30B Q4_K_M | no | same model, **changes backend** ✓ |
| vision_escalation | gpu → **cpu** | Qwen3-VL-30B Q4_K_M | no | same model, **changes backend** ✓ |

**All 12 accounted for. No retired model backs an unassigned role.** The freeze scope's *shape*
changes though: cpu goes 8 roles/4 models → 7 roles/**2** models (35B + Flash-Next), gpu goes
4/2 → 5 roles/**2** models (27B + VL moves off). The v10 qualification record and
`docs/reference/kernel-freeze-runbook.md` both derive from this and will need re-deriving.

**Not in the operator's table, and correctly untouched**: `worker_fast` (declared in
`runtime_defaults.timeouts.roles:551` and in the lean "Active roles" list, but has **no
`server_mode` entry and no `process_layout` entry** — dormant, so it has no model binding to
lose), and the seven embedder roles on `:8090-8095` (bge-large / bge-m3 / granite-97m / e5-base),
which are separate servers this change does not reach.

**Two pre-existing `roles`-block drifts, surfaced not fixed** (they predate this change and are
not in its scope): `roles.worker_math` still names `Qwen2.5-Math-7B-Instruct` and
`roles.toolrunner` still names `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M`, though both are aliases on
`:8072` and cannot be serving those files. And `worker_explore` has **no `roles` entry at all**
and is **missing from `process_layout.hot_resident`** while its two co-aliases are listed.

## C10 — Drafter / MTP artifacts: what is orphaned, what becomes load-bearing.

**ORPHANED** (nothing in the fleet loads them after cutover) — **64.4 GiB + 139.9 GiB of weights**:

| artifact | bytes | note |
|---|---|---|
| `gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf` | 461,766,880 | **the fleet's only external drafter today**; sole consumer retired. gemma4-assistant arch — not substitutable for anything that survives. |
| `gemma-4-26B-A4B-it-assistant-v6-f16.gguf` | 855,228,640 | already catalogue-only; orphaned by the same change. |
| `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf` | 16,796,016,544 | the served worker artifact. |
| `Qwen3.5-122B-A10B-MTP-GGUF/UD-Q4_K_M/` (3 shards) | 78,260,403,200 | self-draft, so the set goes together. |
| `Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf` | 48,410,988,192 | never had a drafter, by construction. |

**STILL NEEDED / NEWLY LOAD-BEARING:**

- `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` (37,801,097,504 B) — **required**, now the worker artifact,
  self-drafts.
- `Qwen3.8-27B-Q8_0.gguf` (29,047,086,048 B) — **required**, now backs **three** roles,
  self-drafts.
- **★ `mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf` (2,786,568,256 B) — NEWLY REQUIRED.** This is the
  fleet's only external `-md` drafter after the change, and it is a silent-failure hazard: a
  launcher that omits `-md` here does **not** fall back to self-draft, it serves unspeculated, and
  the only symptom is a role running ~1.55× slower while returning correct tokens. Do **not**
  substitute the self-contained head (`mtp-Qwen3.8-Flash-Next-Q8_0.gguf`, 4,137,429,120 B) — B12
  measured +64.8% head working set and a *slower* wall clock; the shared head borrows the target's
  `output.weight` on purpose.
- `mmproj-Qwen3-VL-30B-A3B-Instruct-F16.gguf` (1,083,499,584 B) — **required**, travels to CPU.
- `Qwen3.6-27B-MTP-Q8_0.gguf` — **not orphaned**: it is the declared rollback anchor for the
  2026-08-20 27B swap and the registry says do not delete it.
- `Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/` (98,392,912,256 B) + `mmproj-F16.gguf` (904,004,000 B)
  — **not orphaned**: the uniform file is the measurement anchor for *every* number attached to
  this model. Deleting it makes the recipe unverifiable. (The mmproj is unused and unlaunched —
  Flash-Next is multimodal; recorded so nobody rediscovers it and assumes vision is wired here.)
- `mtp-Qwen3.8-27B-Q8_0.gguf` — already declared redundant (the base embeds its own head).
  Orphaned before and after; **not** created by this change.

## C11 — Where the operator's spec is internally inconsistent. Three places, stated plainly.

1. **"ingest at ctx 262144 spec=none"** — `spec=none` cannot be carried forward. It was a
   Qwen3-Next-80B property (unforkable recurrent state), and the registry says so in a
   `canonical: true` operator-ratified block. qwen4exp has an MTP head, and the codified recipe
   `assert_mtp_present()` **fails closed** if the head is absent (OP-35: *"the MTP head is part of
   the MODEL, not an experiment"*). The two requirements are contradictory; the diff resolves them
   in favour of the recipe and flags the policy block for separate amendment.
2. **UD-IQ4_XS vs the recipe's artifact.** The operator named `UD-IQ4_XS` (3 shards, 87.25 GiB).
   The codified recipe's `TRUNK_GGUF` is `IQ4_XS-uniform` (single file, 91.6 GiB). The diff serves
   the operator's artifact and labels every performance figure as having been taken on the other
   one. This is PROD-3's open reconciliation, not something to paper over.
3. **"~52.7 t/s token-weighted"** vs the module's `HEADLINES["champion_final_20260908"]` = **43.281
   t/s** MTP / 27.893 plain. Both are in the campaign; the diff cites 43.281 because that is the
   figure the codified module carries, and records the operator's number beside it.

## C12 — Canonical / human-amendment surfaces this touches but does not edit.

- **`speculative_decoding_policy.exceptions.ingest_long_context`** (`:156-168`) — `canonical: true`,
  `ratified_by: operator`. Now false in every clause. **Needs an operator ratification, not an
  edit.** Until then the file asserts two different things about that role's spec path, and the
  diff says so in-line at both ends.
- **`roles.qwen36_35b_a3b_mtp_q8_local.constraints.forbid`** already carries an
  operator-escalated "waive both or enforce both" question about the MTP quality gate. The new
  `qwen38_flash_next_ud_iq4xs_local` row adds three `forbid` entries of the same class
  (ctx-262144 load proof, critic quality gate, KV quantisation) rather than declaring itself
  admissible.
- `scripts/validate/check_evidence_durability.py` runs on the staged blob via a pre-commit hook
  whenever this file is committed. Every path the diff adds resolves on this host and none is in
  scratch — I checked each one.

---

## 3. What to do with this

The diff is complete and mechanically clean. Three things stand between it and a safe cutover, and
none is a registry edit:

1. **C1 (escalation degeneracy)** — needs a routing decision, not a YAML change.
2. **C2.3 (routine traffic on the whole-machine lock)** — needs either the `region_lock_wait_s_by_holder`
   telemetry D2 asked for, or a ruling that ingest may hold that lock.
3. **C3.2 (`-t 48` vs the import-time invariant)** — needs a `cpu_shape` or a documented exception
   in epyc-orchestrator before `:8074` can launch at the measured optimum.

Then: `stack_change_pipeline.py update` to regenerate the lean registry, `model_descriptors.yaml`
and `derived/stack_priors.yaml`, and re-derive the kernel freeze scope.

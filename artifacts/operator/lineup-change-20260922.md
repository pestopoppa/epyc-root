# Lineup change 2026-09-22 — master-registry diff, hunk by hunk (REVISION 2)

**Artifact**: `/workspace/artifacts/operator/lineup-change-20260922.patch`
**Target**: `epyc-inference-research/orchestration/model_registry.yaml` (the MASTER, the only
hand-edited registry) — **996 insertions, 285 deletions, 30 hunks**, one file.
**Status**: DRAFTED, NOT APPLIED. `git apply --check` passes in the research repo against
`74472b9c` (the file's current tip; sha256 `c373717d…`). The resulting YAML parses
(`yaml.safe_load`, **15** top-level keys, **188** `roles`, **17** `server_mode`).

**REVISION 2 supersedes the first draft.** The operator has ruled on C1–C4. Two of the four
rulings **withdrew** structural moves the first draft made, so this is not an edit on top of that
diff — the frontdoor and ingest hunks were rebuilt from the pristine file. §2 records each ruling
as a resolution: what was asked, what was ruled, what the patch now does, and what it costs.

Nothing under `orchestration/derived/`, nothing in the lean registry, nothing in
epyc-orchestrator was touched. §4 lists the orchestrator work this diff is **inert without**,
including the two items a validator run proved are hard blockers rather than tidiness.

---

## 0. Schema confirmation

**The compiled-artifact claim is verified from the lean file's own banner**:
`epyc-orchestrator/orchestration/model_registry.yaml:1-18` reads *"AUTO-GENERATED —
MASTER-COMPILED RUNTIME VIEW … compiled at every `orchestrator_stack.py start` from the master
registry at /mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml by
`src/registry/registry_compiler.py`"*. A hand-edit there is clobbered at the next start.

| Concern | Where it lives | Notes |
|---|---|---|
| Launch config: port, slots, device, KV, memory | `server_mode.<role>` | **The load-bearing block.** |
| KV feasibility | `server_mode.<role>.serving_shape` | `{n_ctx, slots_by_shape, kv_quant, kv_kib_per_token_f16, vram_non_kv_gib}` declared as **ONE block, validated together** by `stack_manifest.validate_serving_shape_capacity()`. Splitting into flat keys is rejected by `validate_declaration_parity()`. |
| One server, N roles | `server_mode.<primary>.shared_with` | `registry_compiler.py:71-73` resolves an alias to its process through it. `alias_of` on the alias row is **documentation only**. |
| Model/quality/recipe records | `roles.<name>` | A flat namespace mixing real roles with a model catalogue (`*_local` exact-artifact rows). |
| Candidate-role tags | `roles.<key>.candidate_roles` | `try_cheap_first` is an existing value; the operator's tag maps onto the schema with no invention. |
| Deployment-time template kwargs | `server_mode.<role>.chat_template_kwargs` | `registry_loader.get_role_chat_template_kwargs()` reads it **from `server_mode`, not `roles`**, and `src/backends/openai.py:276-284` / `llama_server.py:639-647` inject it into the POST body. This is where the C1 reasoning-effort setting goes. |
| Process roster | `process_layout.hot_resident` | A FLAT list of role names; encodes nothing about sharing. |

**Deprecation convention — precedent reused, nothing invented.** The three-key marker on the
role/model row itself (`deprecated: true` / `deprecated_date:` / `deprecated_reason:`; precedent at
`roles.reap_246b` and nine other rows). Each reason states explicitly *"GGUF REMAINS ON DISK;
deletion is a separate operator action at session end."* **No `deprecated_models:` graveyard rows
are added** — that list is the post-DELETION ledger (every entry carries `deleted:` and
`path_was:`). Commit `7bc650b8` (GLM-5.3-Flash, deleted 2026-09-22) is the worked example of the
other state; this change is deliberately not that. Verified: `deprecated_models` holds **77**
entries before and **77** after.

---

## 1. The hunks

### Topology after this change

| Process | Model | Roles served |
|---|---|---|
| CPU `:8070` + `:8080`/`:8180` | Qwen3.6-35B-A3B-MTP-Q8_0 | **frontdoor** (primary), worker_summarize, worker_general, worker_explore, worker_math, toolrunner |
| CPU `:8074` (1× full, `-t 48`) | **Qwen3.8-Flash-Next UD-IQ4_XS** | architect_critic — **alone** |
| GPU `:8083` (MI210) | Qwen3.8-27B-Q8_0, **thinking ON @ medium**, `n_ctx 196608` | architect_general (primary), coder_escalation, **ingest_long_context** |
| CPU `:8086` | Qwen3-VL-30B Q4_K_M + mmproj | worker_vision, vision_escalation |

**VACATED**: `:8072`/`:8082`/`:8182` (gemma4) and `:8085`/`:8185`/`:8285` (Qwen3-Next-80B).

### H1 · `server_mode.frontdoor` — model UNCHANGED, tenancy widened
The first draft's GPU migration is **reverted to the pristine row**. Model, port, `serving_shape`
(`n_ctx 262144`, `{full: 4, half: 1}`, q8_0/q8_0, 82.0 KiB/tok), `no_mmap`, terse template,
`throughput: 40.22`, `benchmark_score: 170/183` — all restored byte-for-byte. The only
substantive edit is `shared_with`, which goes from `[worker_summarize]` to
`[worker_summarize, worker_general, worker_explore, worker_math, toolrunner]`, plus a block
comment and a widened `description`.

### H2 · `server_mode.worker` — becomes an ALIAS on `:8070`
Rewritten on the `coder_escalation` precedent: no `serving_shape` ("it launches no server, so it
HAS no serving shape of its own"), flat back-compat `kv_quant`, `alias_of: frontdoor`,
`memory_gb: 0`, `acceleration.type: none` + `inherits_spec_from: frontdoor` (where `none` means
*launches no draft of its own*, **not** *runs without speculation*). `numa_instances: 1` /
`numa_ports: [8070]` are retained as explicit singletons rather than deleted — `backend.py:207`,
`placement.py:186` and `cpu_region_lock.py:641` all **fail OPEN** on an unknown port.
`model_role` moves from `worker_general` (the odd one out: a ROLE row) to
`qwen36_35b_a3b_mtp_q8_local` (the exact-artifact catalogue row), matching every other
`server_mode` entry — and it is load-bearing, `model_descriptors.py:1233-1244` substitutes that
row's config. gemma's `draft_role` / `draft_max: 2` / `draft_p_min` / `threads_draft: 16` /
`ubatch: 512` are deleted with the external drafter process they tuned.

**Why frontdoor is primary and worker is the alias, not the reverse**: `:8070`/`:8080`/`:8180`
with `interleave=all / 0,1 / 2,3` is the wiring every measured figure for this artifact was taken
under (P-BENCH-PLACEMENT-1, n=3, 2026-07-30). Moving the 35B onto `:8072` would have re-pointed a
measured placement for no gain. It also keeps the stack_topology delete on the retiring role
(`numa_config.worker_general`) instead of on the surviving one.

### H3 · `server_mode.worker_vision` — MI210 → CPU
`device: ROCm0 → cpu`; `vram_mb: 21049` and `serving_shape.vram_non_kv_gib: 19.26` **deleted**
(the latter is the GPU capacity check's input — leaving it would keep charging a vacated card
19.26 GiB and veto the headroom this migration creates); `memory_gb: 0 → 18.29`;
`host_non_kv_gib: 18.29` added; `no_mmap: true` restored; `ngl` dropped. `kv_quant` q8_0/q8_0 is
**kept** — the MMMU-250 non-inferiority result is a quantisation result and carries, but its
attention-kernel caveat (f16→TILE, q8_0→VEC were **HIP** kernels) does not, so the +0.80 pp delta
is re-opened rather than re-confirmed. `throughput: 112.20 → null`.

### H4 · `server_mode.architect_critic` — Qwen3.5-122B → Qwen3.8-Flash-Next, **single-role**
`model_role` → the new `qwen38_flash_next_ud_iq4xs_local`; **no `shared_with`** (see C2);
`memory_gb 69 → 90`; `kv_quant q4_0/f16 → f16/f16` (**forced**, not chosen);
`kv_kib_per_token_f16 98.0 → 96.0` with the measured 24.0 constant carried alongside in new keys;
`draft_model` points at the **separate** MTP head GGUF with an extended warning; `draft_p_min: 0.5`
added; a new `recipe:` pointer block carries the facts a registry reader must not have to open a
Python file to learn — now including **`cpu_shape: NUMA_FULL_T48`** (see C3). The 122B's entire
throughput record (24.00/15.76/11.30) is relocated to its deprecated row, not copied.

### H5 · `server_mode.ingest_long_context` → alias on `:8083` (GPU 27B)
Same alias shape as H2, pointing at `architect_general`. `thinking_control` deleted (it described
the retired Qwen3-Next template). `chat_template_kwargs` restated with the process's
`enable_thinking: true` / `reasoning_effort: medium`. `throughput: null`,
`benchmark_score: null`. The block comment enumerates the **five** things this role gives up and
the one it gains.

### H6 · `server_mode.architect_general` — the GPU cap, and MEDIUM effort
`shared_with: [coder_escalation] → [coder_escalation, ingest_long_context]`;
`serving_shape.n_ctx: 65536 → 196608` with the old DO-NOT-RAISE banner **replaced by its own
recomputation** (not deleted — the history of why it said that is kept);
`chat_template_kwargs` gains `enable_thinking: true` + `reasoning_effort: medium`.

### H7-H14 · `roles.*` mirrors
`roles.frontdoor` **restored verbatim** plus one explanatory comment. `roles.worker_general`
(→ 35B, `+try_cheap_first`, `+frontdoor`, `max_context 16384 → 262144`, gemma's drafter keys
deleted, quality nulled). `roles.ingest_long_context` (→ the 27B; the Qwen3-Next performance block
moved wholesale into a `previous_model_record:` sub-block and the live keys nulled).
`roles.architect_critic` (→ Flash-Next, `ingest` **not** added to `candidate_roles`,
`contention_note` rewritten to say why). `roles.architect_general` (`disable_thinking: true →
false`, `reasoning` annotated). `roles.worker_vision` / `roles.vision_escalation` (→ `device: cpu`,
`n_gpu_layers` deleted, tps nulled). `process_layout.hot_resident` regrouped, and
**`worker_explore` ADDED** — it was live and demonstrably missing while its two co-aliases were
listed (a pre-existing gap, corrected while the lane is open).

### H15 + D1-D5 · New catalogue rows and deprecation markers
- **NEW** `qwen38_flash_next_ud_iq4xs_local` — registered *before* cutover (the rule the retired
  2.6B rungs broke), carrying the codified recipe, the MTP head's identity and sha256, rejected
  alternatives, and three `constraints.forbid` entries.
- **NEW + deprecated** `gemma4_26b_a4b_orig_q4km_local` and
  `qwen3_next_80b_a3b_instruct_q4km_local`. Both served production for months and **had no
  catalogue row at all** — they existed only inside the `server_mode`/`roles` entries this change
  repoints. Creating the row at retirement is the only way the artifact does not vanish without
  trace; each carries its as-served performance record.
- **deprecated** `qwen35_122b_q4km`, `gemma4_26b_a4b_q4km_mtp`,
  `draft_gemma4_26b_a4b_assistant_q8`.

---

# 2. C1–C4 — RESOLVED

## C1 — Escalation-chain collapse. **RESOLVED: frontdoor stays on the 35B; the 27B gets MEDIUM reasoning effort.**

**What was raised.** The first draft moved `frontdoor` to the GPU Qwen3.8-27B, which put
frontdoor, architect_general and coder_escalation on **one GGUF in one `:8083` process**. All
three escalation chains degenerated to a change of sampling seed — the exact defect the
2026-07-31 Directive 3 split was written to fix.

**What was ruled.** *Keep Qwen3.6-35B-A3B as the frontdoor model. Instead set the Qwen3.8-27B
model to MEDIUM reasoning effort.*

**What the patch now does.** The frontdoor migration is withdrawn in full — `server_mode.frontdoor`
and `roles.frontdoor` are restored to the pristine rows. The chains are intact:

| chain | hops | after this change |
|---|---|---|
| `coder` | frontdoor → coder_escalation | 35B **CPU** `:8070` → 27B **GPU** `:8083` |
| `reasoning` | frontdoor → architect_general → architect_critic | 35B CPU → 27B GPU → **Flash-Next CPU `:8074`** |
| `general` | worker_general → frontdoor → architect_general → architect_critic | hops 1-2 are the same process (see below), then 27B GPU, then Flash-Next CPU |

Hop 2 now differs from hop 1 in **model, device AND thinking mode**, not merely in seed.
`roles.frontdoor.candidate_roles` keeps `coder` **off** for the original 2026-07-31 reason, which
survives unchanged: frontdoor and coder_escalation are still different GGUFs on different devices.

**⚠ One chain edge does flatten, and it is a consequence of the operator's own gemma retirement,
not of this ruling**: `general` hop 1 (`worker_general`) and hop 2 (`frontdoor`) are now the same
GGUF in the same `:8070` process, because worker_general inherited frontdoor's model. The diff
does **not** re-cut that chain — that is a routing decision, not bookkeeping — but it must not go
unnoticed.

### How MEDIUM reasoning effort is expressed — the existing convention, and what else had to move

There are **two** things in these repos that look like a reasoning-effort setting. Only one is
usable here.

1. **`roles.<role>.reasoning_effort.level`** — a real, validated schema
   (`scripts/validate/reasoning_effort_certifications.py:85-90`) gated fail-closed in
   `stack_change_pipeline.py:1015-1027`. **It is NOT what the operator asked for**: its levels are
   the L0–L4 *prompt*-effort ladder in `scripts/analysis/effort_ladder_spec.py:52-138`
   (`L0 answer-only` … `L4 native-think-capped`), not low/medium/high; and its certificate ledger
   `orchestration/reasoning_effort_certifications.yaml` is **empty**
   (`role_certifications: {}`), so declaring a level without a certificate **fails the pipeline**.
   The patch does not touch it.

2. **`server_mode.<role>.chat_template_kwargs.reasoning_effort`** — ✅ **this is the one used, and
   it is not invented.** `chat_template_kwargs` is the existing deployment-time block;
   `registry_loader.get_role_chat_template_kwargs()` reads it *from `server_mode`, not `roles`*, and
   `src/backends/openai.py:276-284` / `src/backends/llama_server.py:639-647` inject it verbatim into
   the request body. `reasoning_effort` is a kwarg **this model's own Jinja template already
   understands** — and that fact is already recorded in this registry, at
   `roles.qwen38_27b_q8_local.chat_template.evidence`: the served Qwen3.8-27B template (sha256
   first-12 `12827f24b742`) branches on `low/medium/high/xhigh` at `:58-66`.

**`medium` is deliberate and `high` is not available on this artifact.** That same evidence string
records that this template *silently coerces `'high'` to `'xhigh'`* (`:60-61`) where stock raises,
and that xhigh injects a 209-char instruction. `medium` is the highest level that means what it
says.

**Three keys had to move together or the kwarg is a silent no-op.** All three are in the patch:

| # | key | before | after | why |
|---|---|---|---|---|
| 1 | `server_mode.architect_general.chat_template_kwargs.enable_thinking` | `false` | `true` | The template's whole `reasoning_effort` branch sits **inside** the `enable_thinking` gate at `:58` and the registry states it is "unreachable while `chat_template_kwargs.enable_thinking` is false". |
| 2 | `roles.architect_general.model.reasoning` | `auto` (annotated) | `auto` (annotated, now load-bearing) | The **live** `:8083` process runs `--reasoning off` (read from `/proc/1531282/cmdline`), which disables thinking at the server before any template kwarg is consulted. |
| 3 | `roles.architect_general.model.disable_thinking` | `true` | `false` | Same suppression, other path. Its stated reason was *"required for clean output on Qwen3.6"* — a Qwen3.6-27B fact; the role has served Qwen3.8-27B since 2026-08-20. |

**⚠ A pre-existing drift is now load-bearing.** Key 2 **already read `auto` in the master** while
the live server ran `--reasoning off`. That master-vs-compiled divergence is surfaced here, not
created here — but it means **verifying the compiled lean registry after
`stack_change_pipeline update` is a cutover step, not a nicety**: if the compiled value stays
`off`, the medium-effort setting silently does nothing and the only symptom is an escalation that
still reads like hop 1.

**⚠ UNMEASURED.** No suite has been run on this role with thinking ON at any effort level. The
`+33pp` "thinking OFF" finding this file leans on elsewhere was measured on **Qwen3.6-35B-A3B
frontdoor task suites**, not on Qwen3.8-27B in the architect role, so it neither justifies nor
refutes this setting. A quality gate before cutover is required, and `--reasoning off → auto` also
re-opens the response-format question (`reasoning_format`) for every consumer of `:8083`.

---

## C2 — `ingest_long_context` on the whole-machine lock. **RESOLVED: it goes to the GPU 27B, not to the critic — and it LOSES context doing so.**

**What was raised.** The first draft merged `ingest_long_context` onto `architect_critic`
(Flash-Next), whose single full instance on `0-95` holds **all four CPU region locks** while it
runs. `ingest_long_context` is routine traffic (Stage 1 of `three_stage_summarization`), so that
merge would have put routine traffic behind the whole-machine lock — the hazard the operator's own
D2 ruling narrowed the `reasoning` chain to `explicit_request` to prevent, reached by a route D2
does not cover. It also lost ingest's split shape (aggregate tok/s at T=8: half **86.17** vs full
**72.53**, ~16% better on halves).

**What was ruled.** *Give `ingest_long_context` to the Qwen3.8-27B instead, since it now has a much
larger context allowance.*

**What the patch now does.** `server_mode.architect_critic` has **no `shared_with`** and serves
one role. `server_mode.ingest_long_context` becomes an alias on `:8083`
(`alias_of: architect_general`, `model_role: qwen38_27b_q8_local`), and
`server_mode.architect_general.shared_with` gains it — that list is the load-bearing binding.

### Is it an alias or its own server? **An alias. It cannot be anything else.**

Same GGUF ⇒ one server, per the project's standing rule; and a second `llama-server` on the same
27B would need a second 27.33 GiB VRAM allocation on a card that does not have it.

### Can the 27B's serving shape carry ingest on top of its existing roles? **Partly. Here is the arithmetic.**

MI210, one card, **63.98 GiB usable** (`rocm-smi`: 68,702,699,520 B — re-read 2026-09-22).
Live per-process VRAM, sampled **during** the running stack from
`/sys/class/kfd/kfd/proc/<pid>/vram_57300` on 2026-09-22:

| process | bytes | GiB |
|---|---|---|
| `llama-server` Qwen3.8-27B (`:8083`, `-np 2 -c 65536 -ctk q8_0 -ctv q8_0`) | 35,673,968,640 | **33.22** |
| `llama-server` Qwen3-VL-30B (`:8086`) | 23,991,402,496 | **22.34** |
| `whisper-server` | 2,210,533,376 | **2.06** |
| `tts-server` (Qwen3-TTS) | 2,815,950,848 | **2.62** |
| sum | | **60.24** (`rocm-smi` total used: 60.29 — agrees) |

**⚠ The capacity gate is blind to 4.68 GiB of that, and it is the binding fact.**
`validate_serving_shape_capacity()` sums only the `vram_non_kv_gib` figures declared in the
registry. whisper.cpp has none (`server_mode.voice_server` still describes a *CPU* faster-whisper
service) and **Qwen3-TTS has no registry entry at all**. Both are VRAM-resident on this card.

The 27B's declared KV rate is 260.0 KiB/token f16 ⇒ **130.0 KiB/token at q8_0/q8_0**. Against the
declared non-KV 27.33 GiB:

| `-c` | 27B non-KV | 27B KV | + speech 4.68 | total | free | verdict |
|---|---|---|---|---|---|---|
| 65536 (was) | 27.33 | 8.13 | 4.68 | 40.14 | 23.84 | — |
| 131072 | 27.33 | 16.25 | 4.68 | 48.26 | 15.72 | fits |
| **196608 (TAKEN)** | 27.33 | 24.38 | 4.68 | **56.39** | **7.59** | **fits** |
| 262144 | 27.33 | 32.50 | 4.68 | **64.51** | **−0.53** | **DOES NOT FIT** |

Cross-checked on the live basis instead of the declared constant: 33.22 GiB observed at `-c 65536`,
plus the marginal KV for 131,072 more tokens (+16.25) = 49.47, + 4.68 = **54.15 GiB, 9.83 free**.
Both bases agree — 196608 fits with 7.6–9.8 GiB of margin; 262144 does not fit at all.

**262144 is not purchasable at any slot count.** KV is unified on this server, so slots do not
scale KV; `-c` does. Dropping to `slots: 1` buys per-slot context, not headroom, and would
serialize all three roles.

**Executed, not asserted.** `validate_serving_shape_capacity()` run against the patched registry
under the simulated post-cutover topology returns
`VramFit(ok=True, required_gib=51.705, budget_gib=62.0, capacity_gib=64.0, headroom_gib=2.0,
per_role={'architect_general': 51.705})` → **PASS**. Run again with `n_ctx` forced to 262144 it
returns `required_gib=59.83` and **also PASSES** — which is precisely the point: 59.83 + 4.68 =
64.51 > 63.98. **A gate pass at 262144 is not evidence that it fits.** That demonstration is
recorded in the registry comment at `server_mode.architect_general.serving_shape`.

### ★ The cost the ruling's premise does not cover

**For `ingest_long_context` this is a context REDUCTION, not an increase.** The role declared
`n_ctx 262144` at one slot per instance = **262144 per slot**. `:8083` gives 196608 over 2 slots =
**98304 per slot** — a **2.67× cut**. "A much larger context allowance" is true of the 27B relative
to its *own* former 65536 cap, which this change triples; it is not true relative to what
`ingest_long_context` had. **This is the one item in C2 that the operator should see before
ratifying**, and it is stated in the registry in the role's own `alias_note`.

Also given up: the split shape (`burst_prefer_split` has nothing left to prefer and must be dropped
from `stack_topology.yaml`), concurrency (3 instances × 1 slot → 2 shared slots),
`spec_type: none` (a Qwen3-Next property, not a role property — the 27B self-drafts at n-max 8),
and its device class (every long-context figure it carried was a CPU measurement on a different
model). **Gained**: it leaves the CPU region-lock topology entirely — a `GPU_HOST_LANE` instance
derives an *empty* region set — and it gains speculation and thinking-at-medium.

**⚠ The role keeps its name and loses its reason.** Qwen3-Next-80B won this role because
SSM-hybrid linear attention scales O(n) per token and therefore beats pure-attention models at
extreme context. The Qwen3.8-27B is a **dense** model with 65 blocks × 4 kv-heads — the KV-densest
artifact in the fleet, 3× the 35B's per-token cost — and it is exactly that density that caps the
process at 196608. A long-context quality **and** cost re-measure is the gate, not a follow-up.

---

## C3 — The Flash-Next recipe would not import. **RESOLVED: a new `cpu_shape`, `NUMA_FULL_T48`.**

**What was raised.** The codified recipe serves at `THREADS = 48` on a `0-95` cpuset
(`qwen38_flash_next_recipe.py`: `SERVE_PREFIX = ["taskset","-c","0-95","numactl","--interleave=all"]`,
`THREADS = 48  # NOT 96: the served decode optimum on this model`). The only `0-95` shape is
`NUMA_FULL = ("0-95", 96)`, and `stack_numa._assert_instance_invariants` raises **at import** when a
non-GPU instance's `-t` does not equal its cpuset's physical core count.

**What was ruled.** *"Add the needed cpu shape. We managed to get this model to run VERY fast and
should use it properly."*

**What the patch now does.** `server_mode.architect_critic.recipe` gains
**`cpu_shape: NUMA_FULL_T48`**, and the same pointer is added to
`roles.qwen38_flash_next_ud_iq4xs_local.acceleration.optimal_cpu_serving`. Both rows say plainly
that they are pointers, not definitions: shapes are Python constants and `stack_numa.py:324-325`
states *"Adding one is a change to the description of this machine and belongs HERE, not in the
YAML"*; `stack_topology.yaml` may only **name** a shape, and `-t` is never declared in YAML — it
comes from the shape tuple.

**The orchestrator change itself cannot live in a registry patch.** It is reproduced verbatim in
§4.1 below as a `git apply`-able diff. It:

1. defines `NUMA_FULL_T48 = ("0-95", 48)` — **the same cpuset as `NUMA_FULL`**, so the same
   `{q0,q1,q2,q3}` region set and the same all-four-region lock; only the thread count differs;
2. registers it in `_CPU_SHAPES` and in `_SHAPE_CLASSES` as class **`"full"`** (a class is a
   restatement of the shape's *size*; the thread count is not part of that, and
   `CPU_SHAPE_CLASSES` is therefore unchanged, so no registry-side `slots_by_shape` key is
   affected);
3. **narrows the invariant honestly rather than waiving it.** The docstring's rule is SMT
   *over*subscription (measured −13% per-stream, −8.5% aggregate at np=4). The code enforced it
   with `threads != phys`, an **equality standing in for an inequality**, which also rejects the
   honest case of leaving cores idle on purpose. The change splits it: `threads > phys` stays fatal
   for **every** shape, and `threads < phys` stays fatal too **unless the instance's shape is
   registered in a new `_UNDERSUBSCRIBED_SHAPES` frozenset**. Membership is the opt-in and it is a
   claim about the machine backed by a measurement.

**This is a corrected proxy, not a bypass — proven by execution, including negatives:**

- Importing the edited module against a scratch `stack_topology.yaml` in which `architect_critic`
  names `NUMA_FULL_T48` → **import succeeds**, `NUMA_CONFIG['architect_critic']['instances'] ==
  [('0-95', 8074, 48)]`, shape class `('full',)`.
- **NEG1**: the original defect still fatal — `('0-47,96-143', 8074, 96)` raises
  *"-t 96 but cpuset '0-47,96-143' holds 48 PHYSICAL cores — SMT oversubscription"*. (The deleted
  `NUMA_NODE0` would still be rejected today.)
- **NEG2**: an *unregistered* under-subscription still fatal — `-t 48` on `0-95` under the name
  `NUMA_FULL` raises *"leaves 48 of the 96 PHYSICAL cores … idle, and its shape 'NUMA_FULL' is not
  registered in _UNDERSUBSCRIBED_SHAPES"*.

---

## C4 — `262144` on Flash-Next is a 32× extrapolation. **RESOLVED: kept, and declared UNVALIDATED.**

**What was raised.** `server_mode.architect_critic.serving_shape.n_ctx` declares 262144, while the
codified recipe hard-wires `CONTEXT = 8192` (no ctx parameter and no ctx branch anywhere in the
module) and the deepest arm ever benchmarked is `d4096`.

**What was ruled.** *"We'll validate it afterwards. The model was built to handle long context
work."*

**What the patch now does.** `n_ctx: 262144` **is kept**, and the caveat is carried in the registry
rather than dropped: the `recipe:` block declares `measured_at_context: 8192` beside it with the
comment *"serving_shape above declares 262144 — a 32× extrapolation of a shape that was never
served"*, and the catalogue row's `constraints.forbid` carries
`production_stack_registration_without_ctx_262144_load_proof`.

**Stated plainly, as required: the context on this role is DECLARED AND UNVALIDATED above 8192.**

| axis | what the recipe measured | what `:8074` will declare |
|---|---|---|
| context | **`CONTEXT = 8192`**, hard-wired | **262144** |
| deepest ever benched | **d4096** | — |
| slots | `PARALLEL_SLOTS = 1` | 1 ✓ |
| artifact | `IQ4_XS-uniform` **single file**, 98,392,912,256 B | the **UD-IQ4_XS 3-shard** set, 93,682,584,224 B (verified on disk: 10,946,624 + 49,835,229,856 + 43,836,407,744) |
| kernel | `ef81196d5` / build **10241**; `HEADLINES["champion_final_20260908"].binary_build_number` says **10303**, and `CHAMPION_PIN_RESOLVED = False` | production **v10** `ffc1bac82` |

There is **no measured KV figure for this model at any context above 8192, anywhere.** The
`kv_kib_per_token_f16: 96.0` in the patch is the conservative all-48-blocks figure; the
header-derived measured constant (24.0 KiB/tok f16 = 6.00 GiB at 262144, from
`full_attention_interval: 4` ⇒ 12 of 48 blocks carry KV) is carried alongside in
`kv_kib_per_token_f16_measured`, clearly labelled as derivation.

**VALIDATION TASK TO FILE — this is the C4 deliverable and it is not optional:**

> **`PROD-3/FN-CTX-1` — Flash-Next served-shape load and long-context proof.**
> Prove a `-c 262144 -np 1` load on **the served artifact** (UD-IQ4_XS 3-shard, not
> `IQ4_XS-uniform`) on **the served kernel** (production v10 `ffc1bac82`), sample VRAM/RSS DURING
> the run, record the real KV at that shape against the 24.0 KiB/tok derivation, and run a critic
> quality gate. Until it passes, `n_ctx: 262144` on `:8074` is a declaration, not a measurement,
> and the two `constraints.forbid` entries on `qwen38_flash_next_ud_iq4xs_local`
> (`…without_ctx_262144_load_proof`, `…without_critic_quality_gate`) are the fail-closed record of
> that. **Belief-kernel wiring**: this run produces measurements, so it needs an adapter row in
> `scripts/vidya/adapters/README.md` and a task in
> `handoffs/active/vidya-belief-substrate-program.md` at the same time it is filed, not after.

---

# 3. Consequences carried forward from revision 1 (re-checked against the new hunk set)

## R1 — Quality: four gates lost, zero gained, no suite re-run.

| role | what it loses | replacement gate |
|---|---|---|
| worker lane (5 roles) | gemma's **tool_compliance 96%** and full-suite **90%** — *the properties that won it the role in 2026-05* (+18pp / +6pp over Qwen3-Coder-30B-A3B) | **none.** The 35B has never run the worker battery. `toolrunner` is an alias on this process, so tool compliance is the first thing to re-measure. |
| `architect_critic` | **quality_score 2.57/3** | **none.** No critic-suite gate has ever been run on qwen4exp. This role exists *for* critique quality. |
| `ingest_long_context` | **25/27 (93%)** canonical long_context, and the 2026-01-26 "best summary quality" finding | **none.** Both are Qwen3-Next-80B results, and the replacement is a dense model at 2.67× less per-slot context. |
| `architect_general` | *(new in revision 2)* every figure it carries was taken with **thinking OFF** | **none.** See C1. |
| vision | the MMMU-250 KV-quant A/B's *kernel* leg | re-opened on CPU. |
| `frontdoor` | **nothing** — revision 2 leaves it on its own artifact with its own stamps | unchanged ✓ |

The diff **nulls** rather than carries every lost figure, because a stale number a router reads is
worse than a null that halts it.

## R2 — Throughput, and the routing-prior hazard.

`q_scorer.registry_baseline_tps_by_role` reads `server_mode.<role>.throughput` **first**, ahead of
`roles.*.performance`, so these re-price routing the moment the compile runs:

- **Worker lane: `56.86 → 40.22` t/s short ctx (−29%), `27.01 → 22.59` long ctx (−16%).**
- **Vision: `112.20 → null`.** 112.20 was an MI210 median (n=250 MMMU turns). **No CPU figure is
  estimated** — no measured CPU/GPU ratio for this model exists on this host, and carrying 112.20
  would make the router price CPU vision at roughly 5-10× its real speed.
- **frontdoor: unchanged at `40.22`.** (Revision 1 raised it to 55.46; that is withdrawn with the
  GPU move.)
- **architect_critic: `24.00 → 52.7`** — carried with its three caveats stated in-line (measured at
  `-c 8192 / -np 1`; on build 10241, not v10; on `IQ4_XS-uniform`, not the served shards), and
  explicitly marked `category=OBSERVATION`, not decision-grade. The module's own
  `HEADLINES["champion_final_20260908"]` carries **43.281** MTP / 27.893 plain (n=6, between-launch
  sd 0.356–0.609%, ratio 1.5516); both figures are recorded, in `server_mode` and in
  `roles.architect_critic.performance` respectively.
- **ingest_long_context: `14.4-20.8 → null`.**

## R3 — Host memory: ~310 GiB freed, measured by the capacity report.

`serving_shape_capacity_report()` on the base vs the patched registry (simulated post-cutover
topology), both executed:

| | host KV | host weights | host required | budget |
|---|---|---|---|---|
| before | 244.06 GiB | 334.00 GiB | **578.06 GiB** | 1069.42 |
| after | 48.75 GiB | 219.29 GiB | **268.04 GiB** | 1069.42 |

The single biggest term is gemma's KV: 480.0 KiB/token f16 (240.0 at q8_0) = 60.0 GiB per instance
× 3 = **180 GiB**, replaced by the 35B's 10.25 GiB × 3. gemma's 8 kv-heads × 512-wide K/V was the
fleet's outlier and it leaves with the model; the "first thing to cap if memory pressure appears"
warning the worker row carried is **discharged**.

## R4 — Concurrency halves on the combined CPU worker lane.

Before: 3 frontdoor instances (`{full: 4, half: 1}` ⇒ 6 slots) **plus** 3 gemma instances (6 slots)
= 12 slots over 6 processes. After: 3 instances, **6 slots**, shared by six role names. Nothing in
the registry softens this; it follows from one GGUF, one server. It is the price of the merge and
it is stated in the `server_mode.frontdoor` block comment.

## R5 — Drafters: what is orphaned, what becomes load-bearing.

**ORPHANED** (nothing loads them after cutover; **GGUFs remain on disk**):
`gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf` (461,766,880 B — the fleet's only external drafter
today, sole consumer retired, gemma4-assistant arch, not substitutable),
its f16 sibling (855,228,640 B), `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf` (16,796,016,544 B),
`Qwen3.5-122B-A10B-MTP-GGUF/UD-Q4_K_M/` (78,260,403,200 B, self-draft so the set goes together),
`Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf` (48,410,988,192 B, never had a drafter by construction).

**NEWLY LOAD-BEARING**: **`mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf`** (2,786,568,256 B, verified on
disk) — the fleet's only external `-md` drafter after the change, and a silent-failure hazard: a
launcher that omits `-md` here does **not** fall back to self-draft, it serves unspeculated, and
the only symptom is a role running ~1.55× slower while returning correct tokens. Do **not**
substitute the self-contained head (`mtp-Qwen3.8-Flash-Next-Q8_0.gguf`) — B12 measured +64.8% head
working set and a *slower* wall clock.

**NOT orphaned**: `Qwen3.6-27B-MTP-Q8_0.gguf` (declared rollback anchor for the 2026-08-20 swap),
`Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/` (the measurement anchor for *every* number attached to
this model — deleting it makes the recipe unverifiable).

## R6 — Canonical / human-amendment surfaces this touches but does not edit.

- **`speculative_decoding_policy.exceptions.ingest_long_context`** — `canonical: true`,
  `ratified_by: operator`. Every clause of it (*"its recurrent state cannot fork, so NO draft-model
  path exists and none can be built"*) was true of Qwen3-Next-80B and none is true of the 27B.
  **Needs an operator ratification, not an edit.** Until then the file asserts two different things
  about that role's spec path, and the diff says so in-line at both ends.
- `roles.qwen36_35b_a3b_mtp_q8_local.constraints.forbid` already carries an operator-escalated
  "waive both or enforce both" question about the MTP quality gate; the new Flash-Next row adds
  three `forbid` entries of the same class rather than declaring itself admissible.

## R7 — Pre-existing drifts surfaced, not fixed (out of scope).

`roles.worker_math` still names `Qwen2.5-Math-7B-Instruct` and `roles.toolrunner` still names
`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M`, though both are aliases and cannot be serving those files.
`worker_explore` has **no `roles` entry at all** (its `process_layout` omission *is* fixed here).
`worker_vision`'s three-way `n_ctx` disagreement (16384 `roles` / 65536 `server_mode` / 8192
`stack_manifest.LAUNCH_CONTEXT_TOKENS`) survives the device move unreconciled — what the move does
change is that the one "measured" value of the three was measured on a backend the role no longer
runs on.

---

# 4. Out of scope for this patch, and it is INERT — or WRONG — without these

Two of these are not tidiness. A validator run proves they are hard blockers.

### 4.1 `epyc-orchestrator/scripts/server/stack_numa.py` — the new shape (C3)

`git apply --check` passes against the current file. Reproduced verbatim so it is not re-derived:

```diff
--- a/scripts/server/stack_numa.py
+++ b/scripts/server/stack_numa.py
@@ NUMA_FULL = ("0-95", 96)
+NUMA_FULL_T48 = ("0-95", 48)
+_UNDERSUBSCRIBED_SHAPES: frozenset[str] = frozenset({"NUMA_FULL_T48"})
@@ _CPU_SHAPES
+    "NUMA_FULL_T48": NUMA_FULL_T48,
@@ _SHAPE_CLASSES
+    "NUMA_FULL_T48": "full",
@@ _assert_instance_invariants
+        shape_names = NUMA_INSTANCE_SHAPES.get(role, ())
-            elif threads != phys:
+            elif threads > phys:
                 problems.append(... "SMT oversubscription")
+            elif threads < phys and shape_names[idx] not in _UNDERSUBSCRIBED_SHAPES:
+                problems.append(... "is not registered in _UNDERSUBSCRIBED_SHAPES")
```

The full, comment-bearing, `git apply`-able form is **Appendix A** at the end of this file —
it is carried here rather than left in a scratch directory that will not survive. Then
`stack_topology.yaml` `architect_critic.instances[0]` becomes
`{cpu_shape: NUMA_FULL_T48, port: 8074}`.

### 4.2 ★ `stack_topology.yaml` — `numa_config` deletions and one shape change

**PROVEN BLOCKER (a):** `validate_declaration_parity()` against the patched registry **fails**:

```
port for role 'ingest_long_context': launcher declares 8085, master declares 8083
port for role 'toolrunner'/'worker_explore'/'worker_general'/'worker_math': launcher 8072, master 8070
numa_ports for 'ingest_long_context': launcher [8185, 8285], master [8083]
numa_ports for 'worker_general': launcher [8082, 8182], master [8080, 8180]
numa_instances for 'ingest_long_context': launcher 2, master 1
```

`numa_config.worker_general` and `numa_config.ingest_long_context` must be **DELETED** (2026-08-01
W1 precedent: *"a role with no process of its own must not carry NUMA wiring — that wiring is what
would launch a second server"*), and `launch_manifest.yaml` re-derived. Left in place they launch
CPU servers on `:8072`/`:8085` for roles that are supposed to be elsewhere.

**PROVEN BLOCKER (b), and it was not in revision 1:** `validate_serving_shape_capacity()` **raises**
on the patched registry:

```
ValueError: stack_manifest: GPU role(s) ['worker_vision'] declare no
`serving_shape.vram_non_kv_gib`.
```

Reading `serving_shape_capacity_report()` at `stack_manifest.py:1330-1362`, a role is GPU **iff
`shape_class == "gpu_host_lane"`** — derived from `stack_topology.yaml`'s `cpu_shape`, **not** from
the registry's `device:` key, which is read into the report but never used for that test. So
`device: cpu` in the master is **declarative only**: `numa_config.worker_vision` must move off
`GPU_HOST_LANE` onto a real CPU shape and drop `gpu_host_lane: true`, or the capacity check fails
at import for the whole stack. *(The first draft had this defect too and did not name it.)*

**Also**: `numa_config.frontdoor.spec_overrides` is fine, but `numa_config.worker_general`'s
`{draft_max: 2, p_split: 0}` dies with that block; `architect_critic.numa_pre_evict_gib: 40` is
sized for 69 GiB, not 90; and `ingest_long_context`'s `placement_policy: burst_prefer_split` must be
dropped, not merely orphaned.

### 4.3 The pipeline

`stack_change_pipeline.py update` to regenerate the lean registry, `model_descriptors.yaml` and
`derived/stack_priors.yaml`, then re-derive the kernel freeze scope
(`kernel_freeze_scope.py --backend {cpu,gpu}`) and `docs/reference/kernel-freeze-runbook.md`. The
freeze scope's **shape** changes: cpu goes 8 roles / 4 models → 7 roles / **2** models, gpu goes
4/2 → 5 roles / **2** models.

---

# 5. Verification log — what was executed, with output

Every claim below was produced by running the command, against a **copy** in
`/mnt/raid0/llm/tmp/`. The real `model_registry.yaml` was never modified; the live stack was never
touched.

| # | command | result |
|---|---|---|
| 1 | `git apply --check /workspace/artifacts/operator/lineup-change-20260922.patch` (in `epyc-inference-research`, tip `74472b9c`) | `Checking patch orchestration/model_registry.yaml...` — **exit 0** |
| 2 | apply to a scratch copy, then `yaml.safe_load` | **OK** — top-level keys **15**, `roles` **188** (was 185), `server_mode` **17** (unchanged), `deprecated_models` **77** (unchanged) |
| 3 | `scripts/validate_model_registry.py <patched>` | **0 error(s), 59 warning(s)** — identical to the base file's `0 error(s), 59 warning(s)` |
| 4 | `scripts/validate/check_evidence_durability.py <patched> --repo …` (the pre-commit hook's check) | **errors: 0, warnings: 5** — all 5 are pre-existing `WAIVED_LOST` paths |
| 5 | `python -m src.registry.registry_compiler --master <patched> --dry-run` | **exit 0**, 3181-line lean projection, no unlisted-section warnings |
| 6 | `stack_manifest.validate_declaration_parity()` on the patched registry | **FAILS** — 8 port/numa_ports/numa_instances mismatches vs `launch_manifest.yaml`. Expected and load-bearing; see §4.2(a) |
| 7 | `stack_manifest.validate_serving_shape_capacity()` on the patched registry, current topology | **RAISES** — `worker_vision` still classed GPU by its `cpu_shape`; see §4.2(b) |
| 8 | same, with the §4.2 topology change simulated in memory | **PASS** — `VramFit(ok=True, required_gib=51.705, budget_gib=62.0, capacity_gib=64.0)`; host `required 268.04 / budget 1069.42` |
| 9 | same, `n_ctx` forced to 262144 | **PASS at `required_gib=59.83`** — demonstrating the gate's blindness to the 4.68 GiB of live speech VRAM (C2) |
| 10 | `scripts/validate/reasoning_effort_certifications.py --registry <patched>` | `reasoning-effort certifications: ok` — **exit 0** (confirms the C1 setting does not trip the fail-closed L0–L4 ladder gate) |
| 11 | `stack_change_pipeline.py check --research-registry <patched>` | **failed, 15 errors** — vs **12 errors** on the unmodified base. The 3-error delta is entirely `lean_registry: stale` (*"run stack_change_pipeline update"*), which is the expected consequence of changing the master. All 12 others (`descriptors`/`stack_priors`/`operator_summary` stale, `guard` source-artifact hash mismatches) are **pre-existing** and reproduce on the base file. |
| 12 | `git apply --check` on the §4.1 `stack_numa.py` diff (in `epyc-orchestrator`) | **exit 0** |
| 13 | import the edited `stack_numa.py` against a scratch topology naming `NUMA_FULL_T48` | **import OK** — `_assert_instance_invariants()` passes; `architect_critic` instances `[('0-95', 8074, 48)]`, shape `('NUMA_FULL_T48',)`, class `('full',)`; `CPU_SHAPE_CLASSES` unchanged |
| 14 | negative test: `('0-47,96-143', 8074, 96)` | **still fatal** — *"-t 96 but cpuset '0-47,96-143' holds 48 PHYSICAL cores — SMT oversubscription"* |
| 15 | negative test: `-t 48` on `0-95` under the name `NUMA_FULL` | **still fatal** — *"leaves 48 of the 96 PHYSICAL cores … idle, and its shape 'NUMA_FULL' is not registered in _UNDERSUBSCRIBED_SHAPES"* |
| 16 | `rocm-smi --showmeminfo vram` | total 68,702,699,520 B (63.98 GiB), used 64,733,995,008 B (60.29 GiB) |
| 17 | `/sys/class/kfd/kfd/proc/<pid>/vram_57300` for all 4 KFD processes, sampled DURING the live stack | 27B **33.22**, VL **22.34**, whisper **2.06**, TTS **2.62** GiB — sum 60.24, agreeing with (16) to 0.05 GiB |
| 18 | `/proc/1531282/cmdline` | `-np 2 -c 65536 -t 8 -ctk q8_0 -ctv q8_0 --spec-draft-n-max 8 --reasoning off` — the source of the C1 drift finding |
| 19 | on-disk `stat` of every artifact the patch cites | all present; sizes as quoted in §1/§C4/§R5 |

**Read, not executed** (stated as reading, not as a check): the `on_gpu` derivation at
`stack_manifest.py:1330-1362`; the alias-resolution order in `master_server_row()`; the
`shared_with` → fleet binding in `src/fleet.py:387-441` (gated behind `ORCHESTRATOR_FLEET_LAYER=1`,
no standalone CLI, so it was not run); the Qwen3.8-27B template's `reasoning_effort` branch
(quoted from this registry's own `chat_template.evidence`, **not** re-extracted from the GGUF
header); every consumer of `chat_template_kwargs` listed in §C1.

**Not resolved, and stated as such**: whether `reasoning_effort: medium` is *good* for this role —
nothing has been measured with thinking ON; whether the compiled lean registry will carry
`reasoning: auto` rather than the live `off` (that is a post-`update` verification step, not
something a patch can settle); the Flash-Next served-shape proof (C4, filed as `PROD-3/FN-CTX-1`);
and a CPU throughput figure for vision, which is deliberately left `null`.

---

# Appendix A — `epyc-orchestrator/scripts/server/stack_numa.py`, the C3 shape

PREPARED, NOT APPLIED. `git apply --check` passes against the current file (verification
log row 12); rows 13-15 are the positive and two negative tests run against the edited module.
Save to a file and `git apply` it from the epyc-orchestrator repo root.

```diff
diff --git a/scripts/server/stack_numa.py b/scripts/server/stack_numa.py
index 4e45391..afd9eb2 100644
--- a/scripts/server/stack_numa.py
+++ b/scripts/server/stack_numa.py
@@ -163,6 +163,38 @@ NUMA_Q1B = ("72-95,168-191", 48)
 # (matches the canonical bench recipe used by Probe B 2026-05-04).
 NUMA_FULL = ("0-95", 96)
 
+# ── NUMA_FULL_T48 (2026-09-22, operator-ruled: "add the needed cpu shape") ───
+# The SAME cpuset as NUMA_FULL — all 96 physical cores, all four NPS4 nodes, so the
+# same {q0,q1,q2,q3} region set and the same all-four-region lock — but with 48 OMP
+# threads instead of 96. Pair it with numactl_policy="interleave=all", exactly as
+# NUMA_FULL is paired.
+#
+# CANONICAL BECAUSE IT IS WHAT WAS MEASURED. Qwen3.8-Flash-Next (qwen4exp) serves its
+# decode optimum at -t 48 on this cpuset. epyc-inference-research
+# scripts/lib/qwen38_flash_next_recipe.py carries
+#     SERVE_PREFIX = ["taskset", "-c", "0-95", "numactl", "--interleave=all"]
+#     THREADS = 48        # NOT 96: the served decode optimum on this model
+# and its CHAMPION-FINAL headline (2026-09-08, n=6, between-launch sd 0.356%) was taken
+# under exactly this placement. Wiring architect_critic at NUMA_FULL's 96 threads would
+# serve a shape nothing was ever measured at.
+#
+# ⚠ THIS IS A DELIBERATE UNDER-SUBSCRIPTION, NOT AN OVERSUBSCRIPTION, which is why it
+# needs the registration below rather than a waiver. _assert_instance_invariants exists
+# to catch SMT OVERsubscription (threads beyond the cpuset's physical cores; measured
+# -13% per-stream, -8.5% aggregate at np=4). It enforces that with an EQUALITY, and the
+# equality also rejects the honest case of leaving cores idle on purpose. The check is
+# narrowed below for shapes listed in _UNDERSUBSCRIBED_SHAPES only; `threads > phys`
+# stays fatal for EVERY shape including this one, so the deleted NUMA_NODE0 (48 physical
+# cores paired with 96 threads) would still be rejected today. This is a corrected proxy
+# for the rule the docstring already states, not a bypass of it.
+NUMA_FULL_T48 = ("0-95", 48)
+
+# Shapes whose thread count is BELOW their cpuset's physical-core count ON PURPOSE.
+# Membership is the opt-in and the only thing that relaxes the equality; a typo that
+# under-subscribes an unlisted shape still fails at import, which is the reason the
+# equality was written in the first place.
+_UNDERSUBSCRIBED_SHAPES: frozenset[str] = frozenset({"NUMA_FULL_T48"})
+
 # ── GPU HOST LANE (operator-ratified 2026-08-01) ─────────────────────────────
 # The 8 host threads a VRAM-resident role needs for tokenising, sampling and
 # request marshalling. NOT a decode instance — see _assert_instance_invariants.
@@ -259,6 +291,10 @@ def _assert_instance_invariants() -> None:
         per = cfg.get("numactl_policy_instances") or {}
         one = cfg.get("numactl_policy")
         gpu_lane = bool(cfg.get("gpu_host_lane"))
+        # The SHAPE NAMES behind this role's instances, so the under-subscription branch
+        # below can ask which shape it is looking at. NUMA_INSTANCE_SHAPES is built by
+        # _load_numa_config() at module scope, before this function is called at import.
+        shape_names = NUMA_INSTANCE_SHAPES.get(role, ())
         for idx, (cpus, port, threads) in enumerate(cfg.get("instances", [])):
             phys = len([c for c in _parse_cpus(cpus) if c < 96])
             if gpu_lane:
@@ -286,11 +322,22 @@ def _assert_instance_invariants() -> None:
                         f"{role}[{idx}] :{port} -t {threads} exceeds the {len(_parse_cpus(cpus))} "
                         f"logical cores in GPU host lane {cpus!r}"
                     )
-            elif threads != phys:
+            elif threads > phys:
                 problems.append(
                     f"{role}[{idx}] :{port} -t {threads} but cpuset {cpus!r} holds "
                     f"{phys} PHYSICAL cores — SMT oversubscription"
                 )
+            elif threads < phys and shape_names[idx] not in _UNDERSUBSCRIBED_SHAPES:
+                # UNDER-subscription is not the defect this check was written for, but it
+                # is still almost always a typo, so it stays fatal unless the SHAPE says
+                # it is deliberate. Listing a shape in _UNDERSUBSCRIBED_SHAPES is a claim
+                # about the machine backed by a measurement; leaving cores idle by
+                # accident is not.
+                problems.append(
+                    f"{role}[{idx}] :{port} -t {threads} leaves {phys - threads} of the "
+                    f"{phys} PHYSICAL cores in cpuset {cpus!r} idle, and its shape "
+                    f"{shape_names[idx]!r} is not registered in _UNDERSUBSCRIBED_SHAPES"
+                )
             nodes = _nodes_touched(cpus)
             if len(nodes) > 1 and not (per.get(idx) or one):
                 problems.append(
@@ -329,6 +376,7 @@ _CPU_SHAPES: dict[str, tuple[str, int]] = {
     "NUMA_Q1A": NUMA_Q1A,
     "NUMA_Q1B": NUMA_Q1B,
     "NUMA_FULL": NUMA_FULL,
+    "NUMA_FULL_T48": NUMA_FULL_T48,   # 2026-09-22: same cpuset as NUMA_FULL, -t 48
     "NUMA_HALF_A": NUMA_HALF_A,
     "NUMA_HALF_B": NUMA_HALF_B,
     "GPU_HOST_LANE": GPU_HOST_LANE,
@@ -354,6 +402,9 @@ _SHAPE_CLASSES: dict[str, str] = {
     "NUMA_Q1A": "quarter",
     "NUMA_Q1B": "quarter",
     "NUMA_FULL": "full",
+    "NUMA_FULL_T48": "full",          # same cpuset => same region set => same class.
+                                      # A class is a restatement of the shape's SIZE, and
+                                      # the thread count is not part of that.
     "NUMA_HALF_A": "half",
     "NUMA_HALF_B": "half",
     "GPU_HOST_LANE": "gpu_host_lane",
```

# Lineup change 2026-09-22 — master-registry diff, hunk by hunk (REVISION 3)

**Artifact**: `/workspace/artifacts/operator/lineup-change-20260922.patch`
**Target**: `epyc-inference-research/orchestration/model_registry.yaml` (the MASTER, the only
hand-edited registry) — **1074 insertions, 281 deletions, 28 hunks**, one file.
**Status**: DRAFTED, NOT APPLIED. `git apply --check` passes in the research repo against the
file's current tip `7bc650b8` (blob `1b8332cb`, sha256 `c373717d…`; repo HEAD `7b0627c4`). The
resulting YAML parses (`yaml.safe_load`, **15** top-level keys, **188** `roles`, **17**
`server_mode`, **77** `deprecated_models` — base is 15 / 185 / 17 / 77).

**REVISION 3 supersedes revision 2.** A measurement taken this session overturned the PREMISE of
one of revision 2's decisions. It is not a refinement; it invalidates a number this file reasoned
from in six places. §0.5 is the finding. Three things follow from it, and they are the whole of
the change from revision 2:

1. the over-declared `kv_kib_per_token_f16` values are corrected (§0.5);
2. **Qwen3-VL-30B stays on the MI210** — revision 2's GPU→CPU migration is withdrawn in full,
   because it existed only to make room that was never missing (§0.5, H3);
3. the operator's explicit allocation is encoded: 27B `:8083` at **n_ctx 196608** q8_0/q8_0 and
   VL `:8086` at **n_ctx 65536** q8_0/q8_0 (§0.5 arithmetic, C2).

Revision 2's C1–C4 resolutions are otherwise preserved verbatim, including the parts C2's
arithmetic no longer needs (restated, not deleted — §C2).

Nothing under `orchestration/derived/`, nothing in the lean registry, nothing in
epyc-orchestrator was touched. §4 lists the orchestrator work this diff is **inert without**.
One of revision 2's two "proven blockers" is **gone** as a direct consequence of change 2 above.

---

# 0.5 ★ THE KV-RATE CORRECTION — the finding this revision turns on

**`serving_shape.kv_kib_per_token_f16` was 4.06x too high for every Qwen3.6/3.8 model in this
file.** The formula it was derived from,

```
block_count * head_count_kv * (key_length + value_length) * 2 / 1024
```

assumes every layer keeps a KV cache. These models declare `<arch>.full_attention_interval = 4`,
so only every 4th layer does; the rest are filtered out of the cache entirely. The server states
it directly — live v10 GPU build, Qwen3.8-27B (`block_count` 65), n_ctx 65536:

```
llama_kv_cache: size = 2176.00 MiB ( 65536 cells,  16 layers, ...)
                K (q8_0): 1088.00 MiB, V (q8_0): 1088.00 MiB
```

Measured at that context: **f16 4096 MiB, q8_0 2176 MiB, q4_0 1152 MiB** — i.e. **64.0 / 34.0 /
18.0 KiB per token**. The correct rule is now code, not lore:
`epyc-orchestrator scripts/server/stack_manifest.py` → `kv_layers()` / `kv_kib_per_token_f16()`,
commit **`44d7516a`**:

```
KV_LAYERS = block_count // full_attention_interval   (when the key is present)
KV_LAYERS = block_count                              (otherwise)
```

**The error direction is what cost us.** Over-counting KV makes the capacity gate REFUSE lineups
that fit. Revision 2's vision migration, and its "262144 DOES NOT FIT / OVER BY 0.53" verdict,
were both consequences of the inflated figure and not of the hardware.

### The corrections, each derived from a GGUF header this session read directly

Every row below was re-read from the real file's header, not taken on trust:

| model | arch | block_count | kv_heads | k/v len | interval | KV layers | true f16 | was |
|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B (`architect_general`, `:8083`) | `qwen35` | 65 | 4 | 256/256 | **4** | 16 | **64.0** | 260.0 |
| Qwen3.6-35B-A3B-MTP (`frontdoor`, `:8070`) | `qwen35moe` | 41 | 2 | 256/256 | **4** | 10 | **20.0** | 82.0 |
| Qwen3.6-27B-MTP (rollback anchor, not serving) | `qwen35` | 65 | 4 | 256/256 | **4** | 16 | **64.0** | — |
| Qwen3-VL-30B-A3B (`worker_vision`, `:8086`) | `qwen3vlmoe` | 48 | 4 | 128/128 | **none** | 48 | **96.0** ✓ | 96.0 |
| gemma-4-26B-A4B (retiring) | `gemma4` | 30 | 8 | 512/512 | **none** | 30 | **480.0** ✓ | 480.0 |
| Qwen3.8-Flash-Next (`architect_critic`, `:8074`) | `qwen4exp` | 48 | 2 | 256/256 | **4** | 12 | 24.0 | 96.0 (kept — see below) |

**Only TWO live declarations in this file needed changing**, because the other affected artifacts
either have no `serving_shape` of their own or are being retired by this same patch:
`server_mode.frontdoor` 82.0 → **20.0** and `server_mode.architect_general` 260.0 → **64.0**.
Both carry a new in-registry comment recording the interval, the derived layer count, the server's
own KV buffer report as the source, and a "do not restore the block_count form" instruction, plus
a pointer to `kv_layers()` as the canonical derivation. Nine further places in the file quoted a
number derived from the old rates; all nine are corrected in the same patch (the worker-alias
prose, the `:8083` capacity banner, the `ingest_long_context` "not purchasable" note, the
`alias_note`, the catalogue row's density claim, and the `vram_gib: 36.70` note — see below).

**`Qwen3-VL-30B` and `gemma-4` were VERIFIED, not assumed.** Neither GGUF carries a
`full_attention_interval` key, so `KV_LAYERS == block_count` and their existing declarations are
right. VL's is independently corroborated by the server: the 2026-08-02 KV-quant A/B recorded
`6144.00 → 3264.00 MiB at n_ctx 65536`, and 3264 MiB is exactly 96.0 × 0.53125 × 65536 / 1048576.

**`Qwen3.8-Flash-Next` is the one affected model left UNCORRECTED, on purpose.** 48 // 4 = 12 KV
layers gives 24.0, which the registry *already* carries beside the gate value as
`kv_kib_per_token_f16_measured: 24.0`. The gate input stays at the conservative 96.0 because this
model — alone in the fleet — also carries a sparse-attention **indexer cache**
(`qwen4exp.attention.indexer.top_k: 2048`, `qwen4exp.attention.indexer.key_length: 128`, both read
from the header this session) that *neither* formula accounts for, and the registry's own C4 note
forbids correcting it downward until that term is measured. It is a CPU role against a ~1069 GiB
host budget, so over-stating it costs nothing. The patch adds a comment saying exactly this and
naming `PROD-3/FN-CTX-1` as the discharge. **This is the one place where I did not apply the
general rule, and it is flagged rather than silent.**

### `vram_non_kv_gib` — vetted, one unresolved discrepancy

- **`architect_general: 27.33` — CONFIRMED, unchanged.** The server's own report gives model
  buffers 25972.29 + 1288.28 MiB = 26.62 GiB plus ~0.39 GiB compute = ~27.0.
- **`worker_vision: 19.26` — CONFIRMED by a live sample, unchanged.** The 2026-09-22 KFD reading
  for `:8086` was 22.34 GiB; declared 19.26 + 3.19 GiB of q8_0 KV at 65536 = **22.45**. Agreement
  to 0.11 GiB.
- **⚠ UNRESOLVED: the 27B's live reading does not reconcile.** The same 2026-09-22 sample put
  `:8083` at 35,673,968,640 B = **33.22 GiB** at `-np 2 -c 65536 -ctk q8_0 -ctv q8_0`, while
  declared non-KV 27.33 + the server's own 2176 MiB of KV = **29.51** — a **3.71 GiB gap with no
  attribution**. VL reconciles on the same instrument and sample, so it is not an instrument
  artifact. **No replacement is guessed**: 27.33 is corroborated by the server's buffer report and
  stays. If the gap is real and persists, the 3.15 GiB of headroom below is nearer zero and the
  allocation is tight rather than comfortable. **This must be settled by sampling
  `/sys/class/kfd` DURING the first post-cutover load** — it could not be re-sampled here because
  the stack is intentionally down for the operator window. It is recorded in the registry at
  `server_mode.architect_general.serving_shape`, not only here.

### The operator's allocation, and the arithmetic it satisfies

- **Qwen3.8-27B** (`:8083`, architect_general + coder_escalation + ingest_long_context):
  **n_ctx 196608**, `kv_quant {k: q8_0, v: q8_0}`
- **Qwen3-VL-30B** (`:8086`, worker_vision + vision_escalation): **n_ctx 65536**,
  `kv_quant {k: q8_0, v: q8_0}`

```
  usable (rocm-smi, 68,702,699,520 B)                        63.98
- whisper.cpp + Qwen3-TTS, live-measured, gate-INVISIBLE      4.68
- 27B weights   (serving_shape.vram_non_kv_gib)              27.33
- VL  weights   (serving_shape.vram_non_kv_gib)              19.26
-----------------------------------------------------------------
=                                                            12.71 GiB for BOTH KV caches

  27B @ -c 196608 q8_0/q8_0:  34.0 x 196608 / 1048576   =     6.38 GiB
+ VL  @ -c  65536 q8_0/q8_0:  51.0 x  65536 / 1048576   =     3.19 GiB
-----------------------------------------------------------------
=  9.56 GiB used,  3.15 GiB FREE
```

Both GPU roles stay resident. **Executed, not asserted**: `serving_shape_capacity_report()` on the
patched registry against the REAL `stack_topology.yaml` returns GPU `kv_gib = 9.5625` — the same
9.56 — and `VramFit(ok=True, required_gib=56.1525, …, per_role={'architect_general': 33.705,
'worker_vision': 22.4475})`. 56.1525 + 4.68 = 60.83 against 63.98 usable ⇒ **3.15 GiB free**. See
§5 rows 6–8.

**Note on `q8_0`: it is 0.53125 of f16, not 0.5.** A q8_0 block is 34 B per 32 elements (scale
plus quants), so the naive "half of f16" understates KV by 5.88%. Every q8_0 figure above uses the
true ratio, as does `stack_manifest._KV_TYPE_F16_RATIO` (also corrected in `44d7516a`). 64.0 ×
0.53125 = 34.0, which is exactly the rate the server reports.

### A correct measurement this rate had convicted of being impossible

`roles.architect_general.model.vram_gib: 36.70` carried a 2026-08-02 note declaring its own
provenance string ("incl. q8_0 KV at 262144 ctx") *arithmetically impossible*, on the grounds that
KV alone would be 130.0 × 262144 = 32.50 GiB. On the measured rate, KV at 262144 is **8.50 GiB**,
and 27.05 weights + 8.50 KV + ~1.15 graph = **36.70**. The figure and its stated context agree
exactly. **That flag is withdrawn in this patch.** It is worth stating plainly: the block_count
form did not merely inflate a gate input — it produced a false accusation against a correct
measurement, which then sat in the file for seven weeks.

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
| GPU `:8083` (MI210) | Qwen3.8-27B-Q8_0, **thinking ON @ medium**, `n_ctx 196608`, q8_0/q8_0 | architect_general (primary), coder_escalation, **ingest_long_context** |
| GPU `:8086` (MI210, **unchanged**) | Qwen3-VL-30B Q4_K_M + mmproj, `n_ctx 65536`, q8_0/q8_0 | worker_vision, vision_escalation |

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

### H3 · `server_mode.worker_vision` — **WITHDRAWN. The role stays on the MI210.**
Revision 2 moved this role to `device: cpu`, deleted `vram_mb: 21049` and
`serving_shape.vram_non_kv_gib: 19.26`, added `host_non_kv_gib`/`no_mmap`, set `memory_gb: 18.29`
and nulled `throughput` (and did the same in `roles.worker_vision`, `roles.vision_escalation`).
**Every one of those edits is reverted to the pristine row**, verified by reverse-applying exactly
those hunks and re-diffing: `device: ROCm0`, `vram_mb: 21049`, `vram_non_kv_gib: 19.26`,
`n_ctx 65536`, `kv_quant {k: q8_0, v: q8_0}`, `throughput: 112.20`, `n_gpu_layers: 999`,
`baseline_tps`/`optimized_tps` 112.20 and the MMMU-250 stamps all stand as measured.

**It existed only because the 4x-inflated 27B KV figure made the card look full**, and it was
never a quality or placement decision — the row's own migration comment said so ("released so
frontdoor can join architect_general on :8083"), and even that premise had already been withdrawn
by ruling C1. With the true rates both GPU roles fit with 3.15 GiB to spare (§0.5).

What the patch adds instead of the migration: a block comment on the row recording *that* the
migration was proposed, *why* it is withdrawn, and the one-line budget summary pointing at
`server_mode.architect_general.serving_shape` for the arithmetic; and a verification note on
`kv_kib_per_token_f16: 96.0` recording that the correction does **not** apply to this model (no
`full_attention_interval` key) and that the server's own `3264.00 MiB at n_ctx 65536` confirms it.
The stale "62.59 of 63.98, headroom 1.40" four-model figure in the GPU BUDGET NOTE is superseded
**as a budget statement** (it was taken with the 27B at `-c 65536`) and **kept as a warning** —
VRAM grows on first EXECUTION, and the 4.68 GiB of speech VRAM is still invisible to the gate.

**✓ This removes revision 2's proven blocker (b).** That blocker was
`validate_serving_shape_capacity()` raising *"GPU role(s) ['worker_vision'] declare no
serving_shape.vram_non_kv_gib"*, caused purely by the registry saying `device: cpu` while
`stack_topology.yaml` still classed the role `GPU_HOST_LANE` (the report derives "is GPU" from
`shape_class`, never from `device:`). With the row pristine the two agree again and the check
**PASSES on the real topology, unsimulated** — §5 row 7. `numa_config.worker_vision` needs no
change at all now.

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

### H6 · `server_mode.architect_general` — the corrected KV rate, the GPU cap, and MEDIUM effort
`shared_with: [coder_escalation] → [coder_escalation, ingest_long_context]`;
**`serving_shape.kv_kib_per_token_f16: 260.0 → 64.0`** with the measurement, the interval, the
derived 16 KV layers and the `kv_layers()` pointer recorded in-line;
`serving_shape.n_ctx: 65536 → 196608` with the old DO-NOT-RAISE banner **replaced by a full
recomputation** (not deleted — the old arithmetic is kept verbatim and explicitly convicted, so
nobody re-derives it); the 3.71 GiB live-reading discrepancy from §0.5 recorded as an ⚠ with a
named verification step; `chat_template_kwargs` gains `enable_thinking: true` +
`reasoning_effort: medium`. The `vram_gib: 36.70` "internally inconsistent" flag is **withdrawn**
(§0.5).

### H7-H14 · `roles.*` mirrors
`roles.frontdoor` **restored verbatim** plus one explanatory comment. `roles.worker_general`
(→ 35B, `+try_cheap_first`, `+frontdoor`, `max_context 16384 → 262144`, gemma's drafter keys
deleted, quality nulled). `roles.ingest_long_context` (→ the 27B; the Qwen3-Next performance block
moved wholesale into a `previous_model_record:` sub-block and the live keys nulled).
`roles.architect_critic` (→ Flash-Next, `ingest` **not** added to `candidate_roles`,
`contention_note` rewritten to say why). `roles.architect_general` (`disable_thinking: true →
false`, `reasoning` annotated). **`roles.worker_vision` / `roles.vision_escalation` are NOT
touched at all** — revision 2's device edits there are reverted (H3).
`process_layout.hot_resident` regrouped, and
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

**⚠ REVISION 3 REPLACES THE ARITHMETIC IN THIS SECTION.** Revision 2 computed it on a 27B KV rate
that is 4.06x too high (§0.5), and on a card it had just emptied by migrating vision to CPU. Both
inputs are wrong. The conclusion that survives is the *ruling* — ingest goes to the 27B — and the
cost in §"The cost the ruling's premise does not cover", which is unaffected because it is a
per-slot-context argument, not a VRAM argument. The numbers below are restated, not deleted, so
the change is auditable.

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

The 27B's KV rate is **64.0 KiB/token f16 ⇒ 34.0 at q8_0/q8_0** (measured — §0.5; it was declared
as 260.0 ⇒ 130.0). **Vision stays on the card**, so both GPU roles are charged. Against the
declared non-KV figures (27B 27.33, VL 19.26) and VL at a fixed `-c 65536` q8_0/q8_0 = 3.19 GiB:

| 27B `-c` | 27B non-KV | 27B KV | VL non-KV | VL KV | + speech 4.68 | total | free | verdict |
|---|---|---|---|---|---|---|---|---|
| 65536 (was) | 27.33 | 2.13 | 19.26 | 3.19 | 4.68 | 56.59 | 7.39 | — |
| 131072 | 27.33 | 4.25 | 19.26 | 3.19 | 4.68 | 58.71 | 5.27 | fits |
| **196608 (TAKEN)** | 27.33 | **6.38** | 19.26 | **3.19** | 4.68 | **60.83** | **3.15** | **fits** |
| 262144 | 27.33 | 8.50 | 19.26 | 3.19 | 4.68 | 62.96 | 1.02 | fits, on 1.0 GiB |

**262144 is no longer arithmetically refused — it is refused on MARGIN.** 1.02 GiB is inside the
noise of a card whose VRAM grows on first EXECUTION rather than at load, carrying two speech
servers the registry cannot see, and with the unreconciled 3.71 GiB live-reading gap of §0.5 still
open. 196608 is the operator's allocation and 3.15 GiB is what it buys. Revision 2's "OVER BY
0.53 — REFUSED" verdict is **withdrawn**: it was an artifact of the 130.0 rate.

Also withdrawn: revision 2's live-basis "cross-check" (33.22 observed + 16.25 marginal = 54.15,
"both bases agree"). It does not corroborate anything — it added a *correct* marginal KV to an
observation that is itself 3.71 GiB above declared+measured, and the agreement was coincidental.
The discrepancy is now carried as an open item (§0.5) instead of as evidence.

**262144 is still not purchasable at any slot count.** KV is unified on this server, so slots do
not scale KV; `-c` does. Dropping to `slots: 1` buys per-slot context, not headroom, and would
serialize all three roles.

**Executed, not asserted, and on the REAL topology this time.**
`validate_serving_shape_capacity()` against the patched registry and the unmodified
`stack_topology.yaml` → **PASS**, with
`VramFit(ok=True, required_gib=56.1525, budget_gib=62.0, capacity_gib=64.0, headroom_gib=2.0,
per_role={'architect_general': 33.705, 'worker_vision': 22.4475})` and GPU `kv_gib = 9.5625`.
Revision 2 could only run this against a *simulated* topology (see H3). **The gate's blindness to
the 4.68 GiB of speech VRAM is unchanged and still the binding caveat** — 56.1525 is the number
the gate sees; 60.83 is the number the card sees.

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
extreme context. The Qwen3.8-27B is a **dense** model with 65 blocks × 4 kv-heads. It is still
the KV-densest artifact in the fleet per token (64.0 KiB/token f16, 3.2× the 35B's corrected
20.0), but **196608 is an operator ALLOCATION with 3.15 GiB of headroom left over, not a ceiling
that density imposes** — revision 2 said the density capped the process, and that followed from
the 260.0 figure (§0.5). A long-context quality **and** cost re-measure is the gate, not a follow-up.

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
header-derived constant (24.0 KiB/tok f16 = 6.00 GiB at 262144, from
`full_attention_interval: 4` ⇒ 12 of 48 blocks carry KV) is carried alongside in
`kv_kib_per_token_f16_measured`, clearly labelled as derivation.

**⚠ REVISION 3 NOTE — this row is the one place the §0.5 correction was deliberately NOT applied.**
The rule that cut `frontdoor` 82.0 → 20.0 and `architect_general` 260.0 → 64.0 says this row's gate
input should read 24.0. It does not, for two reasons, both stated in the registry: this model alone
carries a sparse-attention indexer cache (`qwen4exp.attention.indexer.top_k: 2048`,
`…indexer.key_length: 128`, both read from the GGUF header this session) that *neither* formula
accounts for, and this row's own comment forbids correcting downward until that term is measured.
It is a CPU role against a ~1069 GiB host budget, so the conservative direction costs nothing.
**`PROD-3/FN-CTX-1` below is extended to discharge it**: the same run that proves the served shape
must read back the real KV buffer, at which point this becomes a measurement and 96.0 goes.

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
| vision | **nothing — revision 3 leaves this role entirely alone** (H3) | unchanged ✓ |
| `frontdoor` | **nothing** — revision 2 leaves it on its own artifact with its own stamps | unchanged ✓ |

The diff **nulls** rather than carries every lost figure, because a stale number a router reads is
worse than a null that halts it.

## R2 — Throughput, and the routing-prior hazard.

`q_scorer.registry_baseline_tps_by_role` reads `server_mode.<role>.throughput` **first**, ahead of
`roles.*.performance`, so these re-price routing the moment the compile runs:

- **Worker lane: `56.86 → 40.22` t/s short ctx (−29%), `27.01 → 22.59` long ctx (−16%).**
- **Vision: unchanged at `112.20`.** (Revision 2 nulled it with the CPU move; that is withdrawn
  with the move.)
- **frontdoor: unchanged at `40.22`.** (Revision 1 raised it to 55.46; that is withdrawn with the
  GPU move.)
- **architect_critic: `24.00 → 52.7`** — carried with its three caveats stated in-line (measured at
  `-c 8192 / -np 1`; on build 10241, not v10; on `IQ4_XS-uniform`, not the served shards), and
  explicitly marked `category=OBSERVATION`, not decision-grade. The module's own
  `HEADLINES["champion_final_20260908"]` carries **43.281** MTP / 27.893 plain (n=6, between-launch
  sd 0.356–0.609%, ratio 1.5516); both figures are recorded, in `server_mode` and in
  `roles.architect_critic.performance` respectively.
- **ingest_long_context: `14.4-20.8 → null`.**

## R3 — Host memory: **~250 GiB freed**, measured by the capacity report.

`serving_shape_capacity_report()` on the base vs the patched registry, both executed against the
**real, unmodified** `stack_topology.yaml`:

| | host KV | host weights | host required | budget |
|---|---|---|---|---|
| before | 259.87 GiB | 334.00 GiB | **593.87 GiB** | 1069.42 |
| after | **31.31 GiB** | 312.00 GiB | **343.31 GiB** | 1069.42 |

*(Revision 2 reported 578.06 → 268.04. Both legs move in revision 3: the base figure rises because
the capacity code's q8_0 ratio was itself corrected in `44d7516a` from 0.5 to the true 0.53125, and
the patched figure changes because frontdoor's KV rate drops 82.0 → 20.0. The delta is what matters
and it grew: −250.6 GiB.)*

Two terms dominate. gemma's KV — 480.0 KiB/token f16 (255.0 at q8_0) = 63.75 GiB per instance × 3 =
**191 GiB** — leaves with the model; its 8 kv-heads × 512-wide K/V was the fleet's outlier and, as
§0.5 confirms, it was never over-declared. And the 35B that replaces it costs **2.66 GiB** per
instance, not the 10.25 revision 2 claimed, because of the KV-layer correction. The "first thing to
cap if memory pressure appears" warning the worker row carried is **discharged twice over**.

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
`stack_manifest.LAUNCH_CONTEXT_TOKENS`) is untouched and unreconciled — revision 2 annotated it
while migrating the role; with the migration withdrawn the annotation went too, so it is recorded
**here only**. It is a real pre-existing defect and out of scope for a lineup diff: all three
values describe the same GPU process, and the `server_mode` 65536 is the one the capacity gate and
this change's arithmetic use.

---

# 4. Out of scope for this patch, and it is INERT — or WRONG — without these

One of these is not tidiness. A validator run proves it is a hard blocker; revision 2's second
blocker is resolved by the H3 withdrawal.

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

**PROVEN BLOCKER (a), still open:** `validate_declaration_parity()` against the patched registry
**fails with 8 problems** (executed — §5 row 6):

```
port for role 'ingest_long_context': launcher 8085, master (ingest_long_context/direct) 8083
port for role 'toolrunner':      launcher 8072, master (frontdoor/shared_with) 8070
port for role 'worker_explore':  launcher 8072, master (frontdoor/shared_with) 8070
port for role 'worker_general':  launcher 8072, master (frontdoor/shared_with) 8070
port for role 'worker_math':     launcher 8072, master (frontdoor/shared_with) 8070
numa_ports for 'ingest_long_context': launcher [8185, 8285], master [8083]
numa_ports for 'worker_general':      launcher [8082, 8182], master [8080, 8180]
numa_instances for 'ingest_long_context': launcher 2, master 1
```

The same check **PASSES on the base file**, so all 8 are this change's own and all 8 are expected.
`numa_config.worker_general` and `numa_config.ingest_long_context` must be **DELETED** (2026-08-01
W1 precedent: *"a role with no process of its own must not carry NUMA wiring — that wiring is what
would launch a second server"*), and `launch_manifest.yaml` re-derived. Left in place they launch
CPU servers on `:8072`/`:8085` for roles that are supposed to be elsewhere. The capacity report
still shows three phantom `worker_general` instances for exactly this reason.

**✓ BLOCKER (b) IS GONE.** Revision 2 recorded `validate_serving_shape_capacity()` **raising**
`ValueError: stack_manifest: GPU role(s) ['worker_vision'] declare no
serving_shape.vram_non_kv_gib`. That was caused purely by revision 2's own vision migration:
`serving_shape_capacity_report()` (`stack_manifest.py:1476-1495`) decides a role is GPU **iff
`shape_class == "gpu_host_lane"`**, derived from `stack_topology.yaml`'s `cpu_shape` and **never**
from the registry's `device:` key — so setting `device: cpu` while the topology still said
`GPU_HOST_LANE` produced a GPU role with no VRAM declaration. With H3 withdrawn the two agree
again. **Checked, not assumed**: the capacity check now PASSES against the unmodified
`stack_topology.yaml`, with no simulation (§5 row 7). `numa_config.worker_vision` needs **no
change**. The `shape_class`-not-`device:` reading is still worth knowing and is recorded here for
the next person who tries to move a role between devices from the registry alone.

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
`/mnt/raid0/llm/tmp/lineup-rev3/`. The real `model_registry.yaml` was never modified; the live
stack was never touched (it is intentionally down for the operator window, which is also why row
20's discrepancy could not be re-sampled). Where revision 2 established a baseline, the **DELTA**
against the unmodified base is reported, not only the absolute number.

| # | command | base | patched | delta |
|---|---|---|---|---|
| 1 | `git apply --check /workspace/artifacts/operator/lineup-change-20260922.patch` (in `epyc-inference-research`, file tip `7bc650b8`, blob `1b8332cb`) | — | `Checking patch orchestration/model_registry.yaml...` **exit 0** | — |
| 2 | apply to a scratch copy, then `yaml.safe_load` | top-level **15**, `roles` **185**, `server_mode` **17**, `deprecated_models` **77** | top-level **15**, `roles` **188**, `server_mode` **17**, `deprecated_models` **77** | +3 roles only; copy deleted after |
| 3 | `scripts/validate_model_registry.py` | `0 error(s), 59 warning(s)` | `0 error(s), 59 warning(s)` | **0** |
| 4 | `scripts/validate/check_evidence_durability.py … --repo /mnt/raid0/llm/epyc-inference-research` | `errors: 0  warnings: 5` | `errors: 0  warnings: 5` | **0** (all 5 pre-existing `WAIVED_LOST`) |
| 5 | `python3 -m src.registry.registry_compiler --master … --dry-run` | **exit 0**, 3153 lines | **exit 0**, 3183 lines | +30 lines, no unlisted-section warnings |
| 6 | `stack_manifest.validate_declaration_parity()` | **PASS** | **FAIL, 8 problems** (ports/numa_ports/numa_instances vs `launch_manifest.yaml`) | +8, all expected — §4.2(a) |
| 7 | `stack_manifest.validate_serving_shape_capacity()`, **real unmodified `stack_topology.yaml`** | **PASS** | **PASS** | **0 — revision 2's blocker (b) is gone** |
| 8 | `stack_manifest.serving_shape_capacity_report()`, same topology — GPU leg | `VramFit(ok=True, required_gib=58.4103, budget_gib=62.0, capacity_gib=64.0, headroom_gib=2.0, per_role={'architect_general': 35.9628, 'worker_vision': 22.4475})`, `kv_gib 11.8203` | `VramFit(ok=True, required_gib=56.1525, budget_gib=62.0, capacity_gib=64.0, headroom_gib=2.0, per_role={'architect_general': 33.705, 'worker_vision': 22.4475})`, **`kv_gib 9.5625`** | −2.26 GiB required **while tripling the 27B's context**; `kv_gib` equals the 9.56 in the operator's arithmetic exactly |
| 9 | same — host leg | KV 259.87, weights 334.00, **required 593.87**, budget 1069.4157, ok | KV **31.31**, weights 312.00, **required 343.31**, budget 1069.4157, ok | **−250.56 GiB** |
| 10 | same — per-instance rows, patched | — | `architect_general` GPU n_ctx 196608 kv **6.375**; `worker_vision` GPU n_ctx 65536 kv **3.188**; `frontdoor` ×3 kv **2.656**; `architect_critic` kv 15.375 | 6.375 + 3.188 = 9.5625 ✓ |
| 11 | `scripts/validate/reasoning_effort_certifications.py --registry …` | `ok`, exit 0 | `ok`, exit 0 | **0** (C1's setting does not trip the L0–L4 ladder gate) |
| 12 | `scripts/registry/stack_change_pipeline.py check --research-registry …` | **failed, 15 errors** | **failed, 18 errors** | **+3**, and the 3 are exactly `lean_registry: stale` (*"lean registry content is stale against the master registry projection (local cache key 306b9433055f != 4f8d8cc41231)"* and its two companion lines). Every other error is pre-existing and reproduces on the base. *(Revision 2 saw 12 → 15; both absolutes rose by 3 because `44d7516a` changed `stack_manifest.py`'s source hash. The delta is unchanged.)* |
| 13 | GGUF header read, `Qwen3.8-27B-Q8_0.gguf` | — | `qwen35.block_count 65`, `head_count_kv 4`, `key_length 256`, `value_length 256`, **`full_attention_interval 4`** | ⇒ 16 KV layers ⇒ **64.0** |
| 14 | GGUF header read, `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` | — | `qwen35moe.block_count 41`, `head_count_kv 2`, 256/256, **`full_attention_interval 4`** | ⇒ 10 KV layers ⇒ **20.0** |
| 15 | GGUF header read, `Qwen3.6-27B-MTP-Q8_0.gguf` (rollback anchor) | — | `qwen35.block_count 65`, `head_count_kv 4`, 256/256, **`full_attention_interval 4`** | ⇒ **64.0**; declares no `serving_shape`, nothing to correct |
| 16 | GGUF header read, `Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf` | — | `qwen3vlmoe.block_count 48`, `head_count_kv 4`, 128/128, **NO `full_attention_interval`** | **96.0 is correct — verified, not assumed** |
| 17 | GGUF header read, `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf` | — | `gemma4.block_count 30`, `head_count_kv [30 values]`, 512/512, **NO `full_attention_interval`** | **480.0 is correct — verified, not assumed** |
| 18 | GGUF header read, `Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf` | — | `qwen4exp.block_count 48`, `head_count_kv 2`, 256/256, **`full_attention_interval 4`**, **`attention.indexer.key_length 128`** | true attention term 24.0, but the indexer cache is unaccounted — gate input deliberately left at 96.0, see C4 |
| 19 | reverse-apply of revision 2's six vision hunks, then re-diff | — | `device: ROCm0`, `vram_mb: 21049`, `vram_non_kv_gib: 19.26`, `n_gpu_layers: 999`, `throughput: 112.20`, `baseline_tps/optimized_tps 112.20` all restored byte-for-byte | H3 withdrawal is structural, not textual |
| 20 | VL cross-check of the corrected q8_0 ratio against the server's own A/B readback | — | registry records `6144.00 → 3264.00 MiB at n_ctx 65536`; 96.0 × 0.53125 × 65536 / 1048576 = **3.1875 GiB = 3264 MiB** | exact |
| 21 | `git apply --check` on the Appendix A `stack_numa.py` diff (in `epyc-orchestrator`) | — | **exit 0**, re-verified against the current file for revision 3 | unchanged |

Revision 2's rows 13–15 (importing the edited `stack_numa.py` against a scratch topology, and the
two negative tests) were **not re-run** for revision 3: nothing in this revision touches the C3
shape, and row 21 confirms the diff still applies. They are stated as revision 2 results, not as
revision 3 ones.

**Read, not executed** (stated as reading, not as a check): the `on_gpu` derivation at
`stack_manifest.py:1476-1495` and the `_KV_TYPE_F16_RATIO` block at `:1315-1341`; `kv_layers()` /
`kv_kib_per_token_f16()` at `:1347-1370` and the long arithmetic note above them (commit
`44d7516a`, `capacity gate: KV cost counts KV LAYERS, not every layer`); the alias-resolution order
in `master_server_row()`; the `shared_with` → fleet binding in `src/fleet.py:387-441` (gated behind
`ORCHESTRATOR_FLEET_LAYER=1`, no standalone CLI, so it was not run); the Qwen3.8-27B template's
`reasoning_effort` branch (quoted from this registry's own `chat_template.evidence`, **not**
re-extracted from the GGUF header); every consumer of `chat_template_kwargs` listed in §C1. The
`llama_kv_cache: size = 2176.00 MiB ( 65536 cells, 16 layers, … )` server line and the f16/q8_0/q4_0
4096/2176/1152 MiB triple are quoted from the session that produced `44d7516a`; they were **not**
re-run here, because the stack is down.

**Not resolved, and stated as such**:
- **the 3.71 GiB gap** between the 27B's live KFD reading (33.22 GiB at `-c 65536`) and
  declared non-KV + measured KV (29.51). Nothing was changed on the strength of it and no
  replacement figure was guessed. It bounds the real headroom and must be settled by sampling
  `/sys/class/kfd` DURING the first post-cutover load (§0.5);
- whether `reasoning_effort: medium` is *good* for this role — nothing has been measured with
  thinking ON;
- whether the compiled lean registry will carry `reasoning: auto` rather than the live `off` (a
  post-`update` verification step, not something a patch can settle);
- the Flash-Next served-shape proof and its KV readback (C4, `PROD-3/FN-CTX-1`);
- `worker_vision`'s three-way `n_ctx` disagreement (R7), untouched by this change.

**Belief-kernel wiring.** This revision turns on a measurement, and the measurement's own write
side is `44d7516a`'s docstring — a source file, not a claim tuple. Per the root `CLAUDE.md` rule,
the KV-rate correction needs an adapter row in `scripts/vidya/adapters/README.md` and a task in
`handoffs/active/vidya-belief-substrate-program.md` **at the same time as the `PROD-3/FN-CTX-1`
row**, not after. Index rows are the owning session's write, so this is flagged for the operator's
session rather than added here.

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

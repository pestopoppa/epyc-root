# 2026-08-23 — Research intake wave 2: 15 dives landed, two live bugs fixed, Annex D ratified

Per-agent shard. Operator-spawned research-intake session, **no lane worktree** — worked in the
shared clone, so every commit staged hunk-selectively through a private `GIT_INDEX_FILE` and every
target file was checked for peer hunks first. Session spans 2026-08-21 → 08-23; this shard covers
the wave-2 arc, whose first commits landed late on 08-22.

## What this was

`/research-intake` wave 2. The operator selected the **whole** Stage-2 close-out list
("Deep dive all recommended material"), so all 15 candidates ran as Stage-2b — combined
Stage-1+Stage-2, landing entries already `dive-verified` or `dive-overturned`. Per skill amendment
`6faa32bc` the wave did not inherit wave 1's plan approval and took its own Stage-3 gate.

## Result in one line

**Ten of the fifteen dives corrected one of our own records** — three of them rows filed the day
before, one a retraction of a false anti-fabrication catch this session had itself made. The
literature was the smaller half of the value; auditing what we already believed was the larger.

## Findings that changed something

| # | Finding | Consequence |
|---|---|---|
| 1 | `_migrate_kv` advanced to `VERIFIED` on an **HTTP 200** and the next statement **erased the source slot**. Its own comment said "destructive on failure, so we want to be 100% sure the restore succeeded". `_slot_restore` already parsed `n_restored` and threw it into a log string. | Fixed, `98061c6b`. Verified live: of 75 files in the slot cache exactly **9 are 752-byte header-only saves** (next smallest 66 MB); **4 of the 9 are `old-sess_*`, the same name class as 64 real saves** — a failure of the normal path, not of probes. `:8070` had a listener with `--slot-save-path` set, so the path was ARMED, not dormant. |
| 2 | ColBERT prefix guard used `token_to_id(prefix) is not None`, which reads the **base vocab**. On a tokenizer that never promoted `[unused0]` into `added_tokens` the guard passes and `encode()` emits `['[','unused','##0',']']`. Upstream answerai ships exactly that pairing. | Fixed, `4e5e84c0`. The docstring already stated the right invariant; the predicate testing it was wrong. `[Q] `/`[D] ` were never the dangerous case — those correctly refuse. |
| 3 | ConstBERT/ColBERT-v2 reproduction (arXiv 2604.09982): its 20-word "MaxSim architectural ceiling" is a **`query_maxlen=32` truncation artifact**. The authors' own results file is bit-identical to **17 significant figures** across five truncation lengths. | `intake-1294`, `dive-overturned`. Also: their "median 121 words", stated 7×, is **182** in their own data. |
| 4 | KIVI's per-channel-K prescription is **2-bit-only**; we run 4/8. | The "primary quality gap" at `kv-cache-quantization.md:320` was never a gap. Retired, `76607f9d`. |
| 5 | On massive activations our ρ=4 hybrid is the **least-exposed** architecture in the paper's own data. | Deprioritisation record — its value is preventing future work. |
| 6 | We were tracking the wrong upstream PR. **#25592** fixes the *live in-memory* checkpoint path (every request); #26004 fixes the dormant migration path. Our tree carries the unfixed `[TAG_CHECKPOINTS_FIX_POS_MIN]` TODO. #25592 has four independent verifications, one on **our exact frontdoor model**. | Filed as G7 → B3, v10 candidate. |
| 7 | fla #1156 is **self-retracted** — 0.4.2 only, forward clean, no serving exposure. Gate G6's version floor **argued the opposite of what it recorded**: being below the floor *selects for the defective release*. | `a24f8ca0`, G6 INVERTED. |

## Zero-compute results produced in-session

- **H21 ANSWERED without compute.** Traced `/v1/chat/completions`: history renders append-only and
  `_combined_prompt_with_context` returns `f"{context}\n\nUser: {prompt}"`, so **turn N+1 begins with
  turn N's prompt byte for byte — a strict extension.** Two named exceptions: `context_compression`
  (OFF, set nowhere in the repo) and `request.tools` (the native-tools block is appended *after*
  history, so the shared prefix ends at the previous turn's history — a bounded tail re-prefill,
  independent of conversation length). This settles the shape G6 was going to spend compute measuring.
- **G1's 128K arm cannot run on `:8070`** — it is `-np 4 -c 262144` = 65,536 tokens/slot. `:8080` and
  `:8180` are `-np 1` on the same model and do have the room.

## Corrections to my own plan, found while executing it

| What | Correction |
|---|---|
| **H1 figures were INVERTED, and I repeated them to the operator twice** | Plan said "60% of chunks exceed the 256-token cap, ~43% of characters embedded". Measured read-only on the live catalog (`index-qd-v1`): **11,410 of 28,155 = 40.5%** at or above the cap, mean `token_count` 170.3 — matching `intake-1278`'s 39.6/57.2. `intake-1294` took the complement of both. Corrected in the entry, the plan and the new row. Also: `catalog.token_count` is **clipped at exactly 256**, so the character-coverage figure is not derivable from the catalog at all. |
| **R9 anchor rot** | R9 is at `kv-cache-quantization.md:1257`, not the cited `:1251`. Editing the cited line would have re-worded **R3**, a different risk. R9's CLEARED verdict deliberately preserved — the defect was the warrant, not the verdict. |
| `ggml.h:2575` | A shape comment; the channel-wise gate declaration is `:2578`. |
| `fattn-vec.cuh:620-637` | Does not exist — the file is 611 lines. Z10 re-anchored to `fattn-common.cuh:332-373`. |
| `--slot-save-path` locator | `orchestrator_stack.py:1471-1480`, and **unconditional for every role** — stronger than the plan stated. |
| `STATIC_WARPS` | Our row said "defined and never used anywhere". Used in **five** other modules; unreferenced only *within* `conv/triton/kernels.py`. Caught before the public post went out. |

## Upstream (operator-approved)

| Target | Result |
|---|---|
| [llama.cpp #27442](https://github.com/ggml-org/llama.cpp/issues/27442#issuecomment-5385082723) | First comment on an open, zero-comment issue. Every claim re-derived from their attachments: `n_prompt_tokens_cache` **14×, all zero**; token `248046` = `<|im_end|>`; both `_noflash` logs contain `flash_attn = enabled`; sampler at **temp 0.300**; `70aff2525` postdates their newest build by ~19 h. Claims no fix; rules #27450 out via `has_tensor = supportsFamily:MTLGPUFamilyMetal4_GGML`. |
| [fla #1163](https://github.com/fla-org/flash-linear-attention/issues/1163) | `causal_conv1d_bwd_kernel` bypasses the AMD warp guard. Pinned at `bc3b101d`. Filed as a code-reading report (no fla install on gfx90a) and names the #1156 link **falsified**, not unproven. |

## Verification discipline

Every code fix carries a mutation test **with a control that fails against the old code**:
K5 — a zero-token restore erases under the old predicate, does not under the new;
K6 — the old guard *accepts* the unpromoted tokenizer the new guard *refuses*, on real artifacts;
K9 — a 128-index against a 64-encoder raises, while matching/unstamped/unknown widths do not.
206 retrieval tests + 75 migration tests pass. Production behaviour verified unchanged against the
deployed `gte-moderncolbert-v1-onnx` (old and new guards agree; `do_lower_case: False`).

The Annex D ratification script was itself run end-to-end on a throwaway repo copy plus **four
mutation cases**, each confirming it refuses and leaves nothing behind.

## Deferred, with named blockers

- **Wiki compilation sweep (Step 5)** — `total_new: 23`, mostly this session's own handoffs. NOT run:
  11 wiki pages carry **966 uncommitted insertions** from a compile another session ran at
  08-22 14:07–14:12 and never committed. Compiling on top would entangle my content with theirs in
  the same files, and no clean commit is possible without sweeping their work. See the wrap-up
  output — this is a knowledge-loss trap, because `.last_compile` was already advanced to
  `2026-08-22T14:14:45Z`, so if those edits are discarded their sources will never be recompiled.
- **18 compute-gated rows** — both compute planes held by other sessions all wave. Every row names
  the measurement, the owning handoff, and the result that opens its gate.

# 2026-09-18 — TD-1d re-measured on the GPU: an n=1 acceptance does not survive n=4

Operator asked why the GPU was idle after granting an inference window. It was idle because the
serving stack was down (only the hub on `:8100`) — which was mine to fix, not a reason to wait. I
brought up the frozen-v9 HIP server myself, ran TD-1d, and killed it.

## The run

| field | value |
|---|---|
| server | `/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server`, b10125-0db32c06e (frozen v9) |
| model | `Qwen_Qwen3.6-35B-A3B-Q8_0`, MI210, 4 slots, ctx 131072, fa on, temp 0 |
| host threads | `taskset -c 184-191` (GPU host threads per the champion recipe, not 88-95) |
| loader | `LD_LIBRARY_PATH` pinned to `build-hip/bin` — the three-ggml-generations hazard |
| lifecycle | launched (pid 1691416) and killed by this session; **confirmed dead, VRAM back to 0%** |
| residency | VRAM 59% in all 24 in-run samples + owner samples 87–89% GPU at 00:21:10–19Z |

Method: same 24-question catalogue and state (`state_sha256 aa712da1…` identical across all seven
artifacts), same sampling, one untimed warm pass per arm, then **4 rounds with every arm run before
the next round and the arm order rotated**. JSON baseline re-measured in this session.

## The result — a null against the bar, and a conflict with yesterday

Acceptance was **≥10x vs JSON at ≥15/16**. Agreement is met everywhere (60/64 pooled = 15/16, same
`n01` disagreement as TD-1c). Speed is not:

| arm | n=4 mean ± sd | speedup | 2026-09-17 (n=1) |
|---|---|---|---|
| json baseline | 14.02 ± 1.82 s (11.34–15.45) | 1.00x | 19.3 s |
| native_full | 6.52 ± 0.05 s | 2.15x | 7.3 s (2.66x) |
| native_short | 3.03 ± 0.12 s | 4.63x | 3.2 s (6.0x) |
| **native_id_only** | **1.46 ± 0.03 s** | **9.60x** | 1.6 s (**11.98x**) |
| native_pq1 (1 slot) | 2.09 ± 0.04 s | 6.69x | — |
| native_pq3 (3 slots, option b) | 5.24 ± 0.93 s | 2.67x | — |
| native_pq3_id_only | 2.27 ± 0.45 s | 6.17x | — |

**TD-1d was ticked ACCEPTED on 2026-09-17 at 11.98x from one run per arm.** This re-measurement puts
the same arm at 9.60x. The disagreement is **entirely the JSON baseline** — the two native
measurements agree (1.46 s vs 1.6 s), while the 09-17 JSON sample (19.3 s) sits **above the maximum
of four samples taken here** (15.45 s). Pairing each side's baseline against the other's native time
spans 8.8x–13.2x. A single baseline sample cannot see that spread; that is the whole reason the bar
needs a repeated baseline. Filed as **TD-1d.0** for the owner: re-run with n≥4 alternated and keep
the acceptance if it survives, or downgrade it — but do not adopt id_only as the default on n=1.

**Denominator caveat that applies to both numbers.** Native decides 16/24; c01–c08 fail closed
(`native_unsupported_candidates`, multi-token option labels). So the ratio compares a 16-decision run
to a 24-decision one. Per decision: 584 ms vs 91 ms = **6.40x**. The bar never stated its
denominator. Neither figure passes it, and 9.60x must not be quoted as like-for-like.

**Option (b) is a measured loser.** Three-way parallel reads are *slower* than serial (2.67x vs
6.69x on one slot) — independently corroborating the 09-17 note's `heavy_model` lock observation.

## Three findings worth more than the headline

- **TD-1d.1 — `/v1` drops `grammar`/`json_schema`.** `frontdoor` routes to `/v1/chat/completions`
  (`use_chat_completions=True`), which forwards neither: measured 515 free-form tokens, **0/24
  decisions**. Every arm here used a direct `/completion` adapter, and TD-1c's result must have too.
  **No typed-decision arm is deployable through the normal primitives path until this is settled.**
- **TD-1d.2 — concurrent in-process `llm_call`s are serialized by the cross-process
  `inference_lock`** (parallel wall == serial wall, max 1 slot busy). A constraint on every future
  fan-out design.
- **TD-1d.3 — `qwen35moe` is hybrid-recurrent (SSM layers), so prefix reuse is
  checkpoint-quantized.** Back-to-back per-question reads reuse **0** tokens (~450 ms each) unless a
  prefix-only request first leaves a checkpoint at the prefix end (then ~128 ms/read). This is the
  mechanism behind fan-out losing on this GPU.

## Artifacts

`artifacts/typed_decisions/run_20260918/` — 7 bench files, summary, run log, the runner, the launch
script, and the owner-side residency samples. The harness extension
`run_typed_decisions_native_parallel` (`src/typed_decisions/native.py`, 209 native unit tests pass)
is deliberately **uncommitted** pending TD-1d.0.

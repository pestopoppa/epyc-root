# Tree verify + GDN input-log replay (DTREE-REPLAY-DESIGN)

Box: `handoffs/active/speculative-decoding.md` → DTREE-REPLAY-DESIGN. Source: intake-2752#record
(PR #31669 dive, `/mnt/raid0/llm/tmp/dive-ak-intake-20261121/pr31669/dive.md`). Fork bases: C17
`1b83c6967`, replay branch `llama.cpp-experimental-rs-replay-20261121` (tip `4451ab3a3`: auto mode
`090d6c304`, qwen35/qwen35moe allowlist `6a6868547`).

## Problem

Today the two paths exclude each other. Replay commit asserts on tree batches, and tree verify
(`--draft-tree-mode batch`) keeps one recurrent snapshot per tree column (W slots, 16+ at T16). That
per-column snapshot is exactly the cost replay was built to remove.

## Design

Dims (27B, `Qwen3.8-27B-Q8_0.gguf` headers): 48 GDN layers, H_v 48, H_k 16, S 128, conv kernel 4,
conv channels 10240 (k 2048 + q 2048 + v 6144).

1. **Pending logs indexed by tree node.** During a tree verify of W columns, the GDN op writes
   each column's op inputs into pending row `c` (column index in the verify ubatch), not "token
   t of a chain". These are post-conv/norm `k[S_k,H_k]`, `v[S_v,H_v]`, `g,beta[H_v]` (F32), plus the
   column's raw conv input `x[10240]`. Tree mode keeps parent links (src[6]) and the replay flag
   (op param 1) as they are. The committed state is **not** advanced during verify: the tree
   kernel already walks parents in registers (16e08207d register-slot parent restore), so it needs
   no per-column state slots. It writes only outputs and logs. `n_pend` rises from n_rs_seq+1 to
   W per sequence.
2. **Gather at accept.** `llama_memory_tree_accept(path)` receives the accepted root-to-leaf column
   list `p[0..m-1]`, in path order. It does one `ggml_get_rows` per log tensor with idx = `p`,
   compacting the accepted nodes into rows `0..m-1` of the chain replay buffer, and sets
   `n_rep[seq] = m`. Side branches are discarded because their indices never appear in `p`.
   Conv history works the same way: gather the m accepted `x` columns behind the `[window]` tail.
3. **Replay kernel.** Reuse the existing chain replay unchanged. At the next step's GDN op, the
   kernel replays `n_rep` gathered rows in registers, then runs the new tokens. After the gather,
   the accepted path *is* a chain. So no new HIP/CPU kernel is needed, only a gather (m ≤ depth+1
   rows). Alternative B passes `p` as an extra src and walks it in-kernel. That saves one tiny
   gather (≤ 33 KB × m per layer) but forks the replay kernel, so it is rejected.
4. **Identity argument.** Snapshot mode commits the accepted leaf's state, which the tree kernel
   produced by applying the path's updates root→leaf. Replay applies the same per-token update
   to the same inputs in the same order, starting from the same committed state. Bitwise equality
   needs the same FMA order in the replay loop and the tree loop. This is already true for chains
   (the test-rs-replay-model identity in `4451ab3a3`). Tests must prove it for trees.
5. **Knobs.** Enabled only when `LLAMA_RS_REPLAY` is active (auto = n_seq_max>1, or =2) **and**
   `--draft-tree-mode batch`. Otherwise current behaviour holds, including the assert, which
   becomes a fallback to snapshots when the flag is off.

## Numbers (27B)

| Quantity | Value |
|---|---|
| Logged bytes / column / layer | k 8192 + v 24576 + g,β 384 = 33,152 B; + conv x 40,960 B = **74,112 B (72.4 KiB)** |
| Logged bytes / column (48 layers) | **3.39 MiB** |
| Snapshot / tree slot (48 × (3 MiB state + 120 KiB conv)) | **149.6 MiB** |
| Memory saved / tree slot | **≈146.2 MiB** (W16: 2394 MiB → 54 MiB logs + 1 committed state 150 MiB, per seq) |
| Replay FLOPs / accepted token | 5·S²·H_v·layers = 5·16384·48·48 ≈ **189 MFLOP** (≈8 µs at MI210 FP32 vector peak; state is in registers, so memory adds nothing beyond the K=1 read/write) |
| Snapshot store cost removed | ~0.12 ms/row (program.md:700) → **W12 ≈ 1.44 ms, W16 ≈ 1.92 ms per round per seq** |
| Added cost | gather m rows (≤ 0.4 MB) + replay m tokens ≈ **0.1–0.2 ms/round** |

## Round-cost estimate vs DTREE-ROUND-OVERHEAD-2

The 51.6 ms 27B DFlash2 round (profile L arm) is the reference. Net saving ≈ 1.3 ms (G12) to
1.7 ms (T16) per seq-round, or **2.5–3.3% of the round**. The gain scales with np, because the
snapshot bytes are per sequence while weight traffic is shared. Measured G12/L 1.0266 (implied
round-cost 1.144 vs break-even 1.175) moves to about **1.05**. T16/L 0.959 moves to about **0.99**.
The need_n_rs_seq per-forward prefill tax (105→116 ms T8→T16) also goes away. At np4 the
projection is G12 ≈ +8–10% over L, the same shape as linear replay's +8.6%.

## Verdict

**GO** for an implementation box (DTREE-REPLAY-IMPL). Scope: node-indexed pending rows +
accept-time gather + reuse of the chain replay. Tests: CPU bitwise tree+replay ≡ tree+snapshot over
every accepted path, side branches included, on the 27B dims (test-dtree-ops) and Qwen3.5-0.8B e2e
under `HIP_VISIBLE_DEVICES=-1`. Speed row: 27B DFlash2 np1/np4, tree auto/T12/T16 ± replay vs
linear+replay, V5I env, A/A floor ±1.5%, ≥6 judged pairs, tree oracle gate.

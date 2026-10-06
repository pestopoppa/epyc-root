# CTX-JETLONG-COST part 1 (3a): arithmetic + microbench prep
Date 2026-10-06. Nothing was run besides `cost_model.py` (pure arithmetic) and compile/`bash -n` checks. Output: `cost_model.out`.

## Layer facts (GGUF `Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, arch qwen35moe, read-only)
- block_count 41 = 40 main + 1 nextn (MTP) layer; `full_attention_interval 4` => 10 full-attention main layers (+1 MTP draft layer, own KV, not counted below); 30 GDN/SSM layers (no RoPE, O(1) state).
- n_head 16, **n_head_kv 2**, key/value length **256**, rope dimension_count **n_rot 64** (sections 11,11,10,0), freq_base 1e7, native context 262144.
- :8070 live argv (pid 26641): `-c 262144 -np 4 -t 96 -ctk q8_0 -ctv q8_0 --flash-attn on --no-mmap --mlock --spec-type draft-mtp`, CPU build cpu-20260921-ffc1bac82. KV = **q8_0 K and V** (1.0625 B/elem).

## What Jet-Long's correction does per decode step (findings-jetlong-code.md, modeling_qwen3_jetlong.py)
- Gate: `L_curr = max_pos+1`; if `L_curr <= w` => plain base RoPE, no correction (M:149). `G = ceil(L_curr / w)` (M:155). Paper w = native window (Qwen3 32K); for Qwen3.6 w = 262144 => **G=1 and zero cost up to L=262144; G=2 at 262145..524288; G=4 at 1M**.
- Cache holds base-RoPE K. Decode (M:503-617): `boundary = max_pos - w_0` (w_0 = 2048). Nearby = last w_0 rows with base K/Q; **every distant K row (L - 2048 rows) is rotated on the fly each step** by `delta = floor(p/G) - p` (`x*cos + rotate_half(x)*sin`, M:227/546); Q is rotated once to q_group; two attention calls (base-near, grouped-distant) merged by LSE weights. The shipped fused kernel also pre-rotates all distant K outside the kernel (cute_jetlong_backend.py:164).
- Rotated rows per layer per step: L-2048, over 2 KV heads, **only the 64 rotary dims need rotation** (192 pass-through dims). K for the whole L, V is not rotated.

## Bytes per decode step (10 layers, per context token of L; q8 KV; f16 intermediates)
| variant | B per ctx-token per layer-head-sum | note |
|---|---|---|
| A baseline attn (read K+V q8) | 1088 | |
| B1 uncached, n_rot-aware lower bound | 1600 (1.47x) | read K64 q8, write rot f16, FA reads rot f16 + K192 q8 + V; needs split-dot kernel |
| B2 uncached, naive HF port, full D f16 | 3136 (2.9x) | rotate+copy whole 256-dim K |
| B3 uncached, ggml-graph f32 rope | 11328 (10.4x) | CPY q8->f32, rope f32 (copies unrotated dims), cast f16; plan's "~5x" lies between B2 and B3 |
| C1 cached per G-epoch, rot64 kept f16 | 1208 (1.11x) | + epoch rebuild (392 B/row) once per w=262144 steps, amortised ~0 |
| C2 cached, rot64 kept q8 | 1088 (1.00x) | requantisation error is an accuracy question for 3b |

GB per step (all 10 layers): A = 0.357 / 1.43 / 2.85 / 11.41 at L = 32K / 128K / 262K / 1M. At L>w: L=262145 B1 4.16, B2 8.16, B3 34.8, C1 3.14; L=1M B1 16.7, B2 32.8, B3 140, C1 12.6, C2 11.4 (cost_model.out). Cached-K extra memory at 1M: C1 2.7 GB, C2 1.4 GB (on top of the base K cache).

## Bandwidth assumptions (cited)
- Streaming passes (rotation, rebuild): **165 GB/s** = INF-70 C0 read-sum 165.6 GB/s at 96 threads (gemv-read 167, copy 212; the 446.8 GB/s sequential figure is not used) — wiki/hardware-optimization.md:143.
- Attention reads: calibrated from the measured :8070 (P arm, artifacts/yarn-native-window-20261005/summary.md): 39.13 tok/s at depth 0, 24.59 at 34k => 25.6 ms non-attention + 0.444 us per context token => **effective attention rate 24.5 GB/s** (14% of streaming; includes MTP effects, acceptance 42% vs 53% differ between depths). Extrapolated linearly: baseline decode 142 ms (7.0 tok/s) at 262K, 492 ms (2.0 tok/s) at 1M. The leg reference (CN: 6.4 tok/s at 133k, 3.7 at 253k) is ~2x worse than this extrapolation, so the baselines are optimistic; this makes % overheads conservative-high only if attention dominates more than modelled. All per-step costs are charged per graph eval, not divided by tokens/eval (conservative under MTP).

## Predicted added decode time (relative to unextended decode at same L)
| L (G) | B1 uncached | B2 uncached | C1 cached f16 | C2 cached q8 |
|---|---|---|---|---|
| 32K, 128K, 262144 (G=1) | 0 | 0 | 0 | 0 |
| 262145+ (G=2) | +20.7 ms = 14.5% | +77 ms = 54% | **+12.8 ms = 9.0%** | 0% |
| 1M (G=4) | +83 ms = 16.9% | +312 ms = 63% | **+51 ms = 10.4%** | 0% |
(B3 would be +299% / +347%.) Structural bound: C1 adds at most 120/1088 = 11% of attention bytes, so cached stays <= ~11% of decode wherever attention dominates.

## PREDICTED verdict (3a thresholds: cached <= 10% at 262K, <= 25% at 1M)
**PASS (predicted).** At 262K exactly there is no correction at all for Qwen3.6 (w = 262144); just above it C1 is +9.0% (thin margin; C2 or a q8 rotated cache gives ~0%), at 1M C1 is +10.4% against 25%. The uncached correction would not pass even n_rot-aware at 262K+ (14.5%), and naive ports fail badly, so caching is what makes it viable. The prediction rests on (i) the attention-rate calibration and (ii) the cache stays in place for 2 attention calls + LSE merge, whose overhead is not modelled; the microbench measures only rotation/rebuild, not the 2-call FA split.

## Microbench (prepared, NOT run)
- `jl_rot_bench.cpp` (OpenMP, F16C): per L in {32K,128K,262K,1M}, 3 reps, modes `stream` (read BW reference), `sincos_table_build`, `table` (cached-epoch rebuild), `onthefly` (uncached, sincosf per row). Block = L x 2 heads x 64 f16, NeoX pair rotation, delta = floor(p/G)-p, G = max(2, ceil(L/262144)) (optional argv[1] forces G). CSV columns include ms x 10 layers.
- `bench.sh`: builds and runs under `/workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list 0-95 --role bench --gpu-quiet shared --tag ctx3a --timeout-s 14400 --`, OMP_NUM_THREADS=96, CSV to this directory. `bash -n` and `g++ -fsyntax-only` both pass. Needs a scheduled full-host window.
- Compare measured `onthefly` ms x 10 against B1/B2 extra above, and `table` ms against the epoch-rebuild amortisation (rebuild once per 262144 steps).

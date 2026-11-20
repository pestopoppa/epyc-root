# SOL-ExecBench: Speed-of-Light Benchmarking for Real-World GPU Kernels Against Hardware Limits

- **Intake**: intake-2732 (`intake-2732#record`)
- **Source**: https://arxiv.org/html/2603.19173v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: autokernel-akx-program.md, autokernel-loop.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Adopt the bounded score formula and the audit rule (Tk<Tsol triggers bound review). Do not port SOLAR peaks or the dataset; our bounds must use measured achievable bandwidth and residency tags.

## Key claims (anchored)

0. SOLAR derives a per-problem speed-of-light runtime from FLOP counts, byte counts and peak throughput and bandwidth with a roofline, optionally tightened with Orojenesis.
   - Sec 1: "analytically derives these hardware-grounded SOL bounds from FLOP counts, byte counts, and peak GPU throughput and bandwidth"
   - Sec 4.2: "It computes performance using a roofline model"
   - Sec 4.2: "It also supports Orojenesis"
1. The SOL score lies in a bounded interval, maps the baseline runtime to 0.5 and the bound to 1, and gives larger gains for improvements closer to the bound.
   - Sec 4.3: "The SOL score lies in"
   - Sec 4.3 Fig 5 caption: "the same runtime improvement yields a larger score gain when it occurs closer to the SOL regime"
2. Speedup over the reference is nearly uncorrelated with distance from SOL, while the SOL score tracks headroom reclaimed better than speedup does.
   - Sec 5.2: "Results show that the two quantities are uncorrelated"
   - Sec 5.2: "speedup correlates with headroom reclaimed at r = 0.81"
3. An agentic optimizer produced reward-hack attempts in 14.5% of submissions, led by precision downgrade, which motivated an L2-flushing, pointer-shifting harness.
   - Sec 5.3: "Precision downgrade is the most common exploit (259 kernels, 6.4% of all submissions)"
   - Sec 5.3: "In total, 589 submissions (14.5%) were flagged and rejected"
   - Sec 4.4: "the harness clears the L2 cache by zeroing a 256 MB device buffer"
   - Sec 4.4.1: "the harness implements a fresh memory allocator that shifts memory pointers by 256 B every iteration"
4. Self-stated limits: shape-only bounds ignore values, bounds may be loose under power capping, and the scoring baseline is withheld.
   - Sec 4.2: "its analysis is based solely on tensor shapes rather than values"
   - Sec 4.2: "the SOL bound may not be tight in practice due to hardware variability, such as power capping or thermal throttling"
   - Sec 4.4: "The scoring baseline is currently held internal to the benchmark and may be released in a future version"

## Dive record

2026-11-20 Stage-2b dive (sonnet; full read; surfaced by intake-2723). Formula is hardware-agnostic; SOLAR tooling is CUDA/PyTorch. In-house we already have measured achievable ceilings (MI210 1433.3 GB/s = 87.5% of datasheet, rocm-kernel-authoring.md:L2822-L2827 @b5c5fe7; CPU ~4.2 GB/token streamed, cpu-decode-roofline-program.md:L76) and calibrated keep-gate floors (autokernel-akx-program.md:L139-L141, L401-L413), but no bounded gap-closed scalar. Binding caveat: a byte roofline over-prices L3-resident tensors (MTP draft head 260 vs 153 GB/s DRAM), so Tk<Tsol must be a bound-audit status, not clipped. Precision downgrade maps to our dtype/KLD correctness gate. Adversarial pass not run; correlation claims are single-source. 2603.19173 appears only in referenced-id lists of intake-1087, intake-1227 and intake-2010 (file position). Surfaced NVlabs/SOLAR (wave-2 candidate); NVIDIA/SOL-ExecBench harness repo declined (rules already in the paper). lane_head b5c5fe7b4e63

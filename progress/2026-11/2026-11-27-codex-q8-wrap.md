# Q8 kernel redesign and follow-up measurements

Q8-GEMV-CONVCORE-1 filed NO_KEEP after eight paired MI210 blocks. Served speedup was 0.9981× V5I (95% CI 0.9904–1.0060). V5I remains selected for experimental single-request Qwen3.8-27B Q8_0 + DFlash2. The default-off patch and binary identities are preserved in the [report](../../research/deep-dives/q8-gemv-convcore-20261127/README.md).

The six-panel A3B MI210 census completed with saved request boundaries and runtime residency. The dense 27B request windows contained 74 and 82 verify forwards and zero eligible F32 weight matmuls. A3B's remaining one-row F32 shared gate used 0.339–0.342 ms per C21 verify forward, with a remove-all ceiling around 1.37–1.38% of decode time. About 72% of its cost would have to disappear to deliver a 1% served gain. Its wider v10 Tensile comparator already splits K five ways. [Census](../../research/deep-dives/mi210-matmul-census-20261127/README.md)

The EPYC Q15 replay filed NO_KEEP. Q15 and Q8 both preserved all 48 held-out decisions at 1, 8 and 24 threads. Q15 corrected five engineered near-tie flips but the complete head lost to native Q8 at one thread. Higher-thread timings had positional and repeat noise. The separate native sampler replay demonstrated a winner change after logit formation on the original four-way tie. [Q15 replay](../../artifacts/compute/q8-q15-tie-replay-20261127/README.md) · [Sampler fixture](../../data/spec-filter-ties-20261127/README.md)

The attention audit closed the constant-bound proposal because the audited MMA path already used a fixed width. The A3B two-column vector symbol independently had a 144 B private frame. Its 33 dispatches took 5.76 ms total in one panel, including all kernel work. The traces do not measure dynamic scratch traffic. [Attention audit](../../research/deep-dives/fattn-private-segment-20261127/README.md)

## GPU recovery after the census

The census profiler exited at 15:40:55 UTC and both captured server PIDs (843016 and 799611) had exited. At 16:16 UTC the MI210 reported 100% GPU busy, 0% memory busy, 61 W and 13,074,432 B VRAM, with no KFD process. A root scan found no compute process holding the MI210 render node or /dev/kfd. Every emitted driver fence had signaled. Desktop/session handles were present.

While inspecting debugfs, the agent read `/sys/kernel/debug/dri/2/amdgpu_gpu_recover`. That read triggers recovery. It unintentionally initiated MODE1 reset at 16:16:57 UTC. The driver reported reset success and VRAM recovery at 16:17:02 UTC. This action exceeded the requested process inspection and conditional stale-process stop. The original cause of the persistent busy state remains unverified. No stale process was identified or killed.

Samples at 16:17:26, 16:17:37, 16:17:58 and 16:18:31 UTC showed 0% GPU busy and no KFD process. Power fell to 42 W. The temporary debugfs mount was removed after inspection. [Incident record](../../docs/reference/agent-config/INCIDENT_LOG.md#inc-20261127-mi210-recovery-control-read)

Raw Q15 arrays and native MI210 traces are preserved under `/mnt/raid0/llm/archive/compute-evidence/` with manifests and replay receipts tracked beside the reports. The conditional one-row F32 reduction and the vector private-frame investigation remain with the kernel owner.

Next: ROCm kernel owner evaluates the one-row F32 reduction against its measured incumbents and measures the vector kernel's private-memory contribution before proposing a scratch change.

# A3B CPU weight placement

Both live executables and all mapped ggml/llama libraries matched the stores bound by the signed C22 ratification. The metadata-only champion commit `b1e1864cb` and the built commit `ce6fcbbde` have identical source trees. The signed A3B decision keeps the C22-specific CPU levers off after the combined gate stopped at 0.992× [0.924, 1.066]. The active processes honored that decision. The A3B GPU fold receipt was inconclusive and used a shorter context. It does not set a throughput expectation for this concurrent 131,072-token-per-slot workload.

Two live reads of PID 1016704 showed identical residency. One model mapping contains 9,226,101 pages, about 35.19 GiB, with 99.955756% on NUMA node 3. The mapping advertised interleave over nodes 0–3 and the worker-affinity union covered all 96 physical cores. The file-backed pages skewed towards the same node used by the GPU server. The exact first-touch mechanism and the share of the CPU slowdown attributable to placement remain unmeasured.

The historical frontdoor launcher allocated anonymous weights using `taskset -c 0-95 numactl --interleave=all ... --no-mmap` in `data/numa_placement/20260730-P-BENCH-PLACEMENT-1/prodopt.sh:32–34`. In C22, `common/arg.cpp:2656` exposes the option, `src/llama-model.cpp:1673–1702` selects actual backend buffers when mmap is disabled, and `src/llama-model-loader.cpp:2055` reads weights into the host tensors. Carry over the frozen profile and use this single CPU loading change. Compare measured post-load residency before dispatch. Keep GPU serving under its existing owner.

Evidence is in `NUMA-BEFORE.json`. The audit issued no inference calls or process changes.

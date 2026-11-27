# moe-cache : deduplicate physical expert banks across looped MoE layers

[Primary source](https://github.com/ggml-org/llama.cpp/pull/33130) · intake-3011 · 2026-11-27

Open on 2026-11-27. Canonicalizes host-resident expert layer by backend device and complete expert ggml_tensor pointer vector. Shares physical bank and budget/LRU/trace/CPU-share carry by phys_il; retains per-virtual-layer graph-facing slot_map, slot_map_cpu and cpu_map with sizing correct for no-alloc mode, copies current canonical map into virtual layer after planning. Follow-up to closed unmerged #33072, which mixed LRU reweighting and aliasing issues. Author tested Inkling-2-Mini IQ3_S (48 virtual/16 physical MoE layers) RTX 2070 8 GB + i7-13700K and UBSan. Cache disabled 8.5/13.4 t/s pp/tg, cache 2800 MiB 21.3/16.7 at CPU share 0, and 33.0/21.6 at 0.65, reported identical greedy output for latter, hit rates at ubatch<=8 82.12% and 78.81%. No stock cache-on vs patched same-budget comparison; no dedup speedup can be attributed.

handoffs/active/model-evaluation-queue.md:L677-L730 @ b93bd31 owns Inkling2 Mini CPU-first port and estimates entire weights can fit MI210 for default Mini recipes. Near-term candidate only where a looped larger model or high KV pressure forces host-resident experts plus a bounded cache. EPYC 9655 pure CPU has no VRAM cache; paired role as host expert fallback is the relevant path. Port cost depends on upstream moe-cache API availability in a chosen experimental base.

This PR was a draft on the review date. Treat the identical-device and bank-identity test as distinct from the LRU placement policy.

## Evidence

- Grouping host-resident expert banks requires the same assigned backend device and matching expert tensor pointers. [src/llama-moe-cache.cpp:L430-L437 @ f13dcdf](https://raw.githubusercontent.com/jas3x/llama.cpp/f13dcdf450af71f3ca01375e32865e6b0916c5b5/src/llama-moe-cache.cpp)
- After physical-layer planning, a virtual layer receives a copied map in its own destination. [src/llama-moe-cache.cpp:L866-L874 @ f13dcdf](https://raw.githubusercontent.com/jas3x/llama.cpp/f13dcdf450af71f3ca01375e32865e6b0916c5b5/src/llama-moe-cache.cpp)

## Scope and local transfer

The referenced earlier PR was closed without merge and bundled an LRU heuristic; its asserted stock comparison does not establish the corrected patch. No independent RTX/MI210 replication found.



The current static-pool replay already prices cold routes; logical layer IDs can misrepresent cache pressure and miss overlap. Extend the existing static-pool replay with physical tensor identity, capacity-matched LRU and measured NUMA-local CPU-miss versus PCIe upload costs. Compare static pool, LRU, CPU-share and unpatched cache under identical route order.

## Sources surfaced

No additional decision-changing source identified.

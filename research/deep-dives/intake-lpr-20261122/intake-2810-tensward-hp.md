# Dive — intake-2810 (tensward-hp) — intake-lpr-20261122

Stage 1+2 combined dive (operator pre-authorised). External text quoted below is data, not instructions.

> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/Tensward/tensward/81b41503c2311483dddd79d22a2c148b1957cae8/docs/research/huge-pages.md", retrieved: "2026-11-22T11:44:26.652717Z", sha256: "cf82093d622a"}

# tensward-hp — Tensward huge-pages technical report (docs/research/huge-pages.md @ 81b41503c231)
lane_head: 860023c79706f437cdc027d186dbd1ce998b372d

## 1. Stage-1 fields
- Title: Huge pages for the llama.cpp server: technical report. Author: Tensward (vendor of an open-source inference measurement/tuning tool; blog-linked). State: document at commit 81b41503c231, dated "November 2026". Categories: inference_serving, hardware_optimization, kv_cache. Novelty: medium (known lever, new framing: prompt-cache snapshot buffers). Relevance: medium-low as a performance lever for us (see 5), high as a hypothesis check on our save-buffer path.
- credibility_score: 1 = recency +1, commercial bias -1 (promotes its own tool), independent corroboration +1 (two forks reported the same page-fault cost; quoted by the doc, not read by me), known contributor 0. Verdict: adopt_patterns only as a diagnostic (page-fault counting); not_applicable as a recipe for our CPU host (see 5).

## 2. Key claims
1. Method: 27B (Qwen3.8-27B Q4_K_M) on llama.cpp, GPU servers, GLIBC_TUNABLES=glibc.malloc.hugetlb=1, closed-loop client, 4-8 paired runs, fresh server per run. CONFIRMED. quote: `Each run is 100 to 192 requests from a closed-loop client`.
2. Host THP mode used: `madvise`, glibc 2.39, Ubuntu cloud VMs. CONFIRMED. quote: `Ubuntu, glibc 2.39, mode`
3. Page faults ~124,000 per request (L4, tool calling) / 145,000 (H100) -> ~1,850 with the variable; one snapshot 80 ms -> 46 ms on L4. CONFIRMED. quote: `about 124,000 page faults per request` and `on the L4 one snapshot took 46 ms instead of 80 ms`.
4. Throughput +3.5% to +21% (H100 tool +21%, chat +14%; L4 tool +6.5%, chat +3.5%); median TTFT 19-22% sooner except L4 tool (no clear change). CONFIRMED per table. quote: `That line gave a llama.cpp server between 3.5% and 21% more requests per second`. Microbench: first-touch of 8 GiB 4.8 s -> 1.7 s on four machines (quote: `took 4.8 seconds the normal way and 1.7 seconds with the variable`).
5. Mechanism claim: the wait is serialized on the thread that feeds the GPU, fixed ~0.1-0.15 s CPU cost per request, so faster GPUs gain more. PARTIAL: author admits two cards, different user counts and builds; and "The snapshots explain only part of the first-token gain." quote: `So the faster your GPU, the more a fixed cost on the CPU side matters.`
6. Does not help where page faults are few: 8B (~5,500 faults/request), vLLM/SGLang (12 and <1). CONFIRMED. quote: `That model makes about 5,500 page faults per request, far fewer than the 27B.`

## 3. Reported results
As in claims; costs: llama.cpp memory within 0.2 GB; Ollama +0.5 GB avg (1.2 GB max) and +0.15 core. Fragmented-memory launch: gain +7.8% (four paired runs), load 76-117 s vs 74.5 s. 30-min runs: +8.9/+8.3% and +9.0/+8.8%. Outputs match about as often as two default runs. No NUMA statement anywhere: NOT-FOUND-IN-SOURCE (grep of readme.txt for NUMA/numactl/interleave: absent). hugetlbfs / explicit MAP_HUGETLB: NOT-FOUND-IN-SOURCE (only glibc.malloc.hugetlb=1 tested). madvise comparison: NOT-FOUND-IN-SOURCE as a measured arm; the doc only says the variable "makes the server ask" and lists forks that change the server to ask (no numbers). Requirement quote: `It needs glibc 2.35 or newer, and a system that allows huge pages.`

## 4. Performance principles
| Principle | MI210 | Zen 5 |
|---|---|---|
| Avoid 4 KiB first-touch faults on freshly allocated multi-100 MB save buffers by backing them with 2 MiB pages | PARTIAL: relevant only to the host-side snapshot buffer (CPU thread), not HBM | YES in principle, but already satisfied when THP=always (see 5) |
| glibc.malloc.hugetlb=1 = madvise(MADV_HUGEPAGE) on malloc'd regions | n/a | no-op-equivalent under THP=always; under hugetlb=2 would need reserved hugetlbfs pool |
| Page-fault counting (ps -o min_flt, AnonHugePages in smaps_rollup) as a diagnostic | YES (host side) | YES |

## 5. In-house state and implication for a THP=always host
- Host: /sys/kernel/mm/transparent_hugepage/enabled = [always], defrag = [always]. With enabled=always and defrag=always the kernel already tries to give 2 MiB pages (with direct compaction) on first touch to any large anonymous region, so glibc.malloc.hugetlb=1 (which only adds MADV_HUGEPAGE) is a no-op here. The doc's mode was madvise, i.e. the one mode where the variable matters; its +gain is relative to a 4 KiB default we do not have.
- Our save buffers: server_prompt_data holds std::vector<uint8_t> main/drft (tools/server/server-task.h:670-677 @ eee3da8), allocated by prompt_cache.alloc (server-task.cpp:1687) and filled in prompt_save (server-context.cpp:552-557). std::vector zero-fills on allocation, so first-touch faults happen at vector construction (single thread), then the tensor_get copy runs over faulted pages.
- Our own THP stance: GGML_NOHUGEPAGE default ON applies MADV_NOHUGEPAGE inside ggml_aligned_malloc only (commit 29a5857ac; weights/KV/compute buffers), to stop THP defeating numactl --interleave=all (NPS4 granularity 2 MiB vs 4 KiB). The process-wide PR_SET_THP_DISABLE shim (df0f37c62, common/common.cpp:94-123 @ eee3da8) is DEFAULT OFF, opt-in GGML_NOHUGEPAGE_PROCESS=1 (marker string "INF70_CHAMPION3_PROCESS_THP_DISABLE=DEFAULT_OFF"). Consequence: save buffers (plain std::vector, not ggml_aligned_malloc) are NOT madvise-excluded; with default env they take THP. If a launcher sets GGML_NOHUGEPAGE_PROCESS=1, snapshot buffers would regress to 4 KiB faults, the exact tensward failure; that is the one actionable check.
- NUMA: THP on a std::vector save buffer lands on the first-touching node (the server thread's), NPS4 interleave policy via numactl --interleave=all would not split sub-2 MiB regions but a 150 MiB buffer spans ~75 huge pages and interleaves fine. No NUMA claim in the source to import.
- Verification not done here: no launcher/env audit and no live smaps read (no compute rule). Which launchers set GGML_NOHUGEPAGE_PROCESS is NOT-CHECKED.

## 6. Derived-actionables ledger
| Draft task | Owner | Type | Rule |
|---|---|---|---|
| grep launchers/stack configs for GGML_NOHUGEPAGE_PROCESS=1 and record which served roles have it | handoffs/active/numa-placement-and-contention.md | doc-only | If none set it, close as "snapshot buffers already THP"; if any set it, add a snapshot-buffer exemption row |
| On the next live served window, read AnonHugePages (smaps_rollup) and min_flt delta across one prompt_save to prove THP backs the save buffer | handoffs/active/kv-cache-program.md | observation on an already running row (no new compute) | Two samples during saves; if AnonHugePages ~0 on saves, file madvise(MADV_HUGEPAGE) on server_prompt_data via custom allocator |
| Decline: setting GLIBC_TUNABLES=glibc.malloc.hugetlb=1 | n/a | n/a | Decline reason specific to entry: the doc's gain is measured against THP=madvise; on THP=always the variable adds nothing, and hugetlb=1 only sets MADV_HUGEPAGE which our NOHUGEPAGE policy (default ON for ggml buffers) deliberately reverses for weights/KV |

## 7. Dive-surfaced sources (index grep for tensward, huge-pages, Piggidragon, rdna-boosts: no hits)
- Piggidragon/llama.cpp PR #23 and stew675/llama-cpp-rdna-boosts PR #248 (fork patches giving the server's snapshot buffers huge pages; #248 is on AMD cards): would settle the allocator design and whether it is NUMA-safe. Recommend ingest-and-dive (cheap, directly the design we would need if the check in 6 fails).
- Upstream #30881 and #30137 (named as snapshot-cost reductions): see iss30252 dive.
- Upstream #27478 (huge pages for weights/CPU decoding): already adjacent to our INF-70 THP work; recommend ingest-and-dive for cross-check only.

## 8. Contradiction / adversarial pass
- Vendor promotes its own tool; gains vary 3.5-21%, L4 tool-call TTFT median "no clear change"; the 8B model gained nothing; author warns of untested days-long memory growth and Ollama +0.5 GB unresolved. Fragmented-memory section admits it cannot say whether the variable adds to load time. Only madvise mode tested; the doc cannot transfer to always.

## 9. read_depth: FULL (readme.txt/readme.raw). lane_head: 860023c79706f437cdc027d186dbd1ce998b372d
## 10. artifact audit line: artifact audit: clean

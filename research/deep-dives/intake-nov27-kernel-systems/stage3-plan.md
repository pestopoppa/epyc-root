# November 27 research intake filing proposal

**Decision requested:** approve the proposed owner edits below, or name the packets to revise. The first priorities are a static HIP spill audit, the served F32 shape census, Q15 near-tie replay and leakage-safe memory evaluation. Existing kernel freeze, inference booking and ratification decisions continue to govern any later execution.

Three gpt-6.2-sol agents read primary evidence and companion implementations. Root reviewed source passages, local code and current owner text. There were two Stage 2 sweeps. Five new companions changed an applicability rule, implementation detail or comparison arm. The remaining cited antecedents supply background rather than another deciding test. No experiment was run.

## Proposed work

| Packet | Decision | Owner |
|---|---|---|
| P1 | Identify sampled HIP instructions in existing binaries | rocm-kernel-authoring.md |
| P2 | Decide whether decode scheduling limits IQ4 or EXL3 | quantization-and-low-bit.md |
| P3 | Identify underfilled F32 router GEMMs | rocm-kernel-authoring.md |
| P4 | Decide whether to specialize a HIP V-load bound | rocm-kernel-authoring.md |
| P5 | Determine eligible F32 verify work | autokernel-loop.md |
| P6 | Price adaptive expert caching versus a static pool | cpu-decode-roofline-program.md |
| P7 | Preserve greedy parity near logit ties | cpu-decode-roofline-program.md |
| P8 | Decide whether small CPU heads merit a resident/streamed split | cpu-decode-roofline-program.md |
| M9 | Evaluate generated kernels under the existing promotion procedure | autokernel-loop.md |
| M10 | Recognize a future local-mixer architecture | autokernel-loop.md |
| P11 | Decide whether failed groups can support local repairs | harness-program.md |
| P12 | Select a cheaper memory harness without leaking evaluation data | memory-program.md |
| P13 | Test whether routing improves under a fixed local capacity budget | routing-program.md |
| P14 | Detect skill interactions hidden by single-skill uplift | eval-tower-program.md |
| P15 | Test deterministic retrieval into post-compaction history | memory-program.md |
| M16 | Reduce loops per decoded token on recurrent-depth models | speculative-decoding.md |

## Evidence and execution

For each empirical screen, freeze input hashes, source/model/build identity, configuration, hardware topology, estimator, minimum worthwhile effect and error budget **before** evaluating. Partition by request, conversation or later time window. Record per-item raw outcomes and a denominator covering every attempted, absent, failed, invalid and abstained case, including empty eligible sets. Use the current content-verified incumbent and A/A variation for timing. Use an unexamined holdout for the final decision. Reject a broken control or wrong numerical result. Promote only with the owner’s predeclared quality and cost bounds. Formal interim looks are futility-only.

CPU and GPU experiments use their respective native implementations. No published foreign-hardware gain enters a local forecast. First use offline receipts and static inspection. Execution needing live compute goes through its owner. A compatible candidate, an observable bottleneck and passing correctness checks are prerequisites for expansion into implementation and served testing. The code-object review, CPU numerical replay, routing replay and memory evidence review are independent. Coordinate edits to shared owners. Reuse existing episode, BEAM, routing and kernel receipts. No new cross-project service is proposed.

Every P row is proposed owner work; every M row is trigger prose only. Owners keep their existing domain rows. At approved filing, add each proposed box to its matching track with the corresponding acceptance conditions below. Reconcile each owning index row only where its next action changes.

### P1 · Identify sampled HIP instructions in existing binaries

The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack.

Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check.

Use the original ELFs, code objects, store manifests and build IDs. Keep one other binary for validation. Record symbol+offset, source line or unmappable reason for each sampled PC. Only trial host-trap if unresolved hotspots remain and firmware/driver enumerate the capability; collect separate baseline runtime and check perturbation, skid and sample loss.

Implementation and owner evidence — Root b93bd3172 / rocm-kernel-authoring.md:1122.

### P2 · Decide whether decode scheduling limits IQ4 or EXL3

Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof.

Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3.

Freeze the full nibble, sign and scale oracle and retained kernel traces; compare existing permute helper with alternative decode-to-issue placement at equal layout. On wave64 price VGPR occupancy, 64 KB LDS per CU, memory stalls, MFMA issue and spills. Reject a numerical mismatch; require improvement on later actual shapes before a served trial. CPU analogue is lane-local byte shuffles plus widened signed dot, measured separately.

Implementation and owner evidence — Root b93bd3172 / llama.cpp@ffc1bac82:ggml/src/ggml-cuda/vecdotq.cuh:34,1320,1344; quantization-and-low-bit.md:359.

### P3 · Identify underfilled F32 router GEMMs

The existing Q8 atomic-flush determinism task addresses a different type and reduction path.

Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise.

Reuse retained A3B router traces at decode and prefill. Baseline is the resolved Tensile solution; keep a later request window. Record M/N/K, workgroups, slices and all partial-buffer writes. The upstream half-CU test bounds unsplit tile count, not slices. Stop if even eliminating targeted time would miss the owner’s served gate. Test CPU splitting only for underoccupied cores after NPS4-local partitioning.

Implementation and owner evidence — Root b93bd3172 / kv-cache-program.md:1947.

### P4 · Decide whether to specialize a HIP V-load bound

A CUDA stack frame reduction gives no proof of scratch traffic on the active gfx90a specialization. RF7 changes wave-level streaming.

Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles.

Compare deployed GPU symbols on a train and holdout context length, retaining code-object hash, VGPR/scratch metadata, ISA and dispatch hits. A nonzero private segment alone cannot prove traffic. Stop on absent path or equal material scratch traffic; specialize and time only if affected. Check both padded and unpadded tails.

Implementation and owner evidence — Root b93bd3172 / rocm-kernel-authoring.md:1212; llama.cpp@ffc1bac82:ggml/src/ggml-cuda/fattn-mma-f16.cuh.

### P5 · Determine eligible F32 verify work

Completed Q8 w8 and queued fused small-K width 1–4 work do not count F32 rows by M and verify width.

Classify retained verify calls by input type, rows, K, verify columns and selected kernel. Bound F32 time that a weight-sharing GEMV could recover against served dispatch. Stop at zero eligible share or an immaterial upper bound.

Freeze verify traces from both dense and MoE, train/test split by request. Report all rows and F32-eligible rows by width, M and K. Preserve actual dispatch including width one and wide M; compare incumbent GEMV versus tiled GEMM for surviving bins. On CPU compare blocked GEMV to existing GEMM with NUMA-local weights; never import Adreno subgroups or the numeric threshold.

Implementation and owner evidence — Root b93bd3172 / autokernel-loop.md:5336; rocm-kernel-authoring.md:1150.

### P6 · Price adaptive expert caching versus a static pool

The current static-pool replay already prices cold routes; logical layer IDs can misrepresent cache pressure and miss overlap.

Extend the existing static-pool replay with physical tensor identity, capacity-matched LRU and measured NUMA-local CPU-miss versus PCIe upload costs. Compare static pool, LRU, CPU-share and unpatched cache under identical route order.

Bind each expert tensor to a physical bank, backend and epoch. Reserve model, KV and scratch before pricing the pool; hold back later routes. Output every hit/miss, unique bytes, PCIe overlap, CPU affinity, and uncovered bank. Stop if experts fit, identities are all distinct for dedup, or cold-route/transfer costs erase the margin; report these cases separately.

Implementation and owner evidence — Root b93bd3172 / cpu-decode-roofline-program.md:5995.

### P7 · Preserve greedy parity near logit ties

The sampler fixture starts after logit formation; a Q8 activation rounding error can change which logit is largest before sampling.

Replay near-tie and ordinary rows with incumbent Q8, per-block signed Q15 and FP32 reference. Save top-two gaps, argmax flips, accumulators and conversion cost; verify AVX-512 signed-word dot semantics and overflow against a scalar oracle.

Freeze pre-activation rows plus weight bytes and golden logits with deliberate near and wide gaps; compare Q8, Q15 and reference on unseen prompts and thread counts. Persist token, gap, logits, packing time, and signed-pair overflow cases. Reject a candidate on a new held-out greedy mismatch or if conversion cost erases its measured benefit.

Implementation and owner evidence — Root b93bd3172 / speculative-decoding.md:1511; llama.cpp@ffc1bac82:ggml/src/ggml-cpu/arch/x86/repack.cpp.

### P8 · Decide whether small CPU heads merit a resident/streamed split

The completed NTA-only seed failed its speed gate; it did not partition a reusable working set by CCD capacity.

Compare resident and streaming layer subsets for a draft head after accounting for per-CCD weight duplication, KV and scratch. Isolate four-row blocking, worker pinning, barriers and THP; include a 27B bandwidth-bound negative control.

Size working sets per CCD after KV and scratch. Baselines include current champion, NTA-only and unmodified OS page policy. Record realized page size and NUMA placement plus per-thread work; separate prefill, single-stream and drafts at a later prompt/width. Stop if LLC misses or matched-throughput intervals fail to improve, or if a negative control regresses.

Implementation and owner evidence — Root b93bd3172 / autokernel-akx-program.md:1393; speculative-decoding.md:30.

### M9 · Evaluate generated kernels under the existing promotion procedure

Golden greedy prompts exercise too few shapes for kernel promotion. Wall time, turns and cost are author-reported and provide planning context.

Retain exact-token checks across thread counts as an additional witness when a generated CPU candidate reaches operator, numerical and served gates.

Apply only at the existing AutoKernel candidate gate. Record full build/recipe and aggregate agent cost separately from runtime; exact greedy fixtures supplement backend, KLD and served-baseline checks.

Implementation and owner evidence — Root b93bd3172 / autokernel-loop.md; MEASUREMENT.md.

### M10 · Recognize a future local-mixer architecture

Existing GDN fusion and KDA exponential work measure recurrence or state movement; substituting a trained mixer changes the model.

When a qualified checkpoint contains sliding-window q/k/v mixing, trace window KV/cache traffic separately from recurrence on both backends and compare matched quality/latency.

Checkpoint-and-architecture trigger only. Keep causal window width and pre-mix keys explicit. Compare quality at equal training budget before any inference-cost conclusion. GPU wave/LDS tiling and CPU memory traffic belong to the resulting graph.

Implementation and owner evidence — Root b93bd3172 / autokernel-loop.md:5217; cpu-decode-roofline-program.md:2036.

### P11 · Decide whether failed groups can support local repairs

A terminal MemRL failure score does not encode the first repairable action, options or a validated continuation.

Audit retained all-fail trajectory groups for reproducible environment state, a bounded repair point and verifiable continuation. Count recoverable groups before proposing any training or changing MemRL rewards.

Freeze same-policy group membership, exact task environment, tools, rollouts and rewards; hold out tasks. Record all failures including infra faults, repairability, local success and continuation success separately. Advance a training proposal only if at least one held-out repair verifies end to end and usable counts support the planned comparison; never relabel terminal failures from local success alone.

Implementation and owner evidence — Root b93bd3172 / epyc-orchestrator@59a1d469:src/graph/trajectory_artifact.py; src/api/services/memrl.py:56.

### P12 · Select a cheaper memory harness without leaking evaluation data

M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases.

Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons.

Pin M-12 judge, prompts, receipts, dataset and explicit independent BEAM partition. Hold out conversations from search, filter post-hoc intersections visibly and score all scheduled cases. Compare incumbent, smoke-gated and fully evaluated candidate on quality, total construction cost, query tokens, and unchanged-memory reuse. Reject leaked cases or unverified archive hashes. Preserve ratified abstention handling.

Implementation and owner evidence — Root b93bd3172 / memory-program.md:526,562; epyc-inference-research:scripts/benchmark/beam_memory_retrievers.py.

### P13 · Test whether routing improves under a fixed local capacity budget

Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost.

Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals.

Replay ordered arrival sets without future leakage. Compare incumbent, percentile pacing with same demand scores, and full lookahead under identical occupancy and budget; use a later trace with bursts. Report per-request route, satisfaction definition, time, starvation and budget breaches. Advance only on budget compliance and positive held-out utility over pacing after solver cost.

Implementation and owner evidence — Root b93bd3172 / epyc-orchestrator@59a1d469:src/typed_decisions/routing_replay.py; src/graph/budgets.py.

### P14 · Detect skill interactions hidden by single-skill uplift

Local skills are text/tool bundles, whereas the source trains continuous prompts. The existing null replay records single-task effects.

Measure held-out pairs with component-only, combined single-call, explicit two-call and partner-shuffled arms; record step retention, token and tool cost by model. Keep soft-prefix findings separate from text-skill outcomes.

Freeze model, executor, evidence and cost ceiling. Compare both orders, shuffled partners, constituent controls and explicit two-step intermediate on held-out tasks. Record stale skills, tool failures, invalid completions, abstentions and additional compute. Reopen admission policy only for effects surviving shuffled labels and cost-matched controls.

Implementation and owner evidence — Root b93bd3172 / eval-tower-program.md:3255; epyc-orchestrator@59a1d469:orchestration/repl_memory/replay/skill_replay.py.

### P15 · Test deterministic retrieval into post-compaction history

Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory writes.

Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence.

Use identical conversations, raw turns, parser version and token cap. Compare lexical/hybrid, exact mentions, released first-mention heuristic and dependency/alias gated edges. Record raw episode IDs, all-gold recall, time/order failures, build and query wall time measured externally. Promote only if held-out evidence recall or answer quality improves without exceeding the cost ceiling.

Implementation and owner evidence — Root b93bd3172 / epyc-orchestrator@59a1d469:src/graph/compaction.py:115; memory-program.md:526.

### M16 · Reduce loops per decoded token on recurrent-depth models

The existing DFlash2 target/drafter interface has no interchangeable fixed-point latent; layer savings depend on stability of a shared recurrent block.

Reopen when a qualified recurrent-depth model exposes latent-state initialization and adaptive exit. Compare loops, wall time, quality and acceptance at fixed effort on CPU and MI210 separately.

Require a serving candidate with repeated shared weights, a stable latent convention and a real adaptive exit. Freeze input/exit rules and compare the lived adaptive workload separately from trajectory replay on CPU/GPU. Include warm-start overhead and speculative verification.

Implementation and owner evidence — Root b93bd3172 / context-and-token-economy.md:2598; speculative-decoding.md:258.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| RI-NOV27-1 | intake-3006#record | Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check. | P1 / PC-HOSTTRAP-COVERAGE |
| RI-NOV27-2 | intake-3007#record | Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3. | P2 / IQ4-PERM-PLACEMENT |
| RI-NOV27-3 | intake-3008#record | Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise. | P3 / F32-ROUTER-SPLITK-CENSUS |
| RI-NOV27-4 | intake-3009#record | Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles. | P4 / FATTN-PRIVATE-SEGMENT |
| RI-NOV27-5 | intake-3010#record | Classify retained verify calls by input type, rows, K, verify columns and selected kernel. Bound F32 time that a weight-sharing GEMV could recover against served dispatch. Stop at zero eligible share or an immaterial upper bound. | P5 / VERIFY-F32-GEMV-CENSUS |
| RI-NOV27-6 | intake-3011#record | Extend the existing static-pool replay with physical tensor identity, capacity-matched LRU and measured NUMA-local CPU-miss versus PCIe upload costs. Compare static pool, LRU, CPU-share and unpatched cache under identical route order. | P6 / MOE-PHYSICAL-BANK-REPLAY |
| RI-NOV27-7 | intake-3012#record | Replay near-tie and ordinary rows with incumbent Q8, per-block signed Q15 and FP32 reference. Save top-two gaps, argmax flips, accumulators and conversion cost; verify AVX-512 signed-word dot semantics and overflow against a scalar oracle. | P7 / Q8-Q15-TIE-REPLAY |
| RI-NOV27-8 | intake-3012#record | Compare resident and streaming layer subsets for a draft head after accounting for per-CCD weight duplication, KV and scratch. Isolate four-row blocking, worker pinning, barriers and THP; include a 27B bandwidth-bound negative control. | P8 / DRAFTER-CCD-RESIDENCY |
| RI-NOV27-9 | intake-3012#record | Retain exact-token checks across thread counts as an additional witness when a generated CPU candidate reaches operator, numerical and served gates. | M9 |
| RI-NOV27-10 | intake-3013#record | When a qualified checkpoint contains sliding-window q/k/v mixing, trace window KV/cache traffic separately from recurrence on both backends and compare matched quality/latency. | M10 |
| RI-NOV27-11 | intake-3014#record | Audit retained all-fail trajectory groups for reproducible environment state, a bounded repair point and verifiable continuation. Count recoverable groups before proposing any training or changing MemRL rewards. | P11 / FAIL-GROUP-SPLICE-AUDIT |
| RI-NOV27-12 | intake-3015#record | Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons. | P12 / MEM-HARNESS-CANDIDATE-REPLAY |
| RI-NOV27-13 | intake-3016#record | Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals. | P13 / ROUTE-BUDGET-LOOKAHEAD |
| RI-NOV27-14 | intake-3017#record | Measure held-out pairs with component-only, combined single-call, explicit two-call and partner-shuffled arms; record step retention, token and tool cost by model. Keep soft-prefix findings separate from text-skill outcomes. | P14 / SKILL-PAIR-COMPAT-REPLAY |
| RI-NOV27-15 | intake-3018#record | Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence. | P15 / MEM-RAW-EPISODE-ARM |
| RI-NOV27-16 | intake-3019#record | Reopen when a qualified recurrent-depth model exposes latent-state initialization and adaptive exit. Compare loops, wall time, quality and acceptance at fixed effort on CPU and MI210 separately. | M16 |

## Stage-3 filing payload

```json
{
  "format_version": 2,
  "entry_updates": [
    {
      "id": "intake-3006",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/rocm-kernel-authoring.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check."
      ]
    },
    {
      "id": "intake-3007",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/quantization-and-low-bit.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3."
      ]
    },
    {
      "id": "intake-3008",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/rocm-kernel-authoring.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise."
      ]
    },
    {
      "id": "intake-3009",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/rocm-kernel-authoring.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles."
      ]
    },
    {
      "id": "intake-3010",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/autokernel-loop.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Classify retained verify calls by input type, rows, K, verify columns and selected kernel. Bound F32 time that a weight-sharing GEMV could recover against served dispatch. Stop at zero eligible share or an immaterial upper bound."
      ]
    },
    {
      "id": "intake-3011",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Extend the existing static-pool replay with physical tensor identity, capacity-matched LRU and measured NUMA-local CPU-miss versus PCIe upload costs. Compare static pool, LRU, CPU-share and unpatched cache under identical route order."
      ]
    },
    {
      "id": "intake-3012",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Replay near-tie and ordinary rows with incumbent Q8, per-block signed Q15 and FP32 reference. Save top-two gaps, argmax flips, accumulators and conversion cost; verify AVX-512 signed-word dot semantics and overflow against a scalar oracle.",
        "Compare resident and streaming layer subsets for a draft head after accounting for per-CCD weight duplication, KV and scratch. Isolate four-row blocking, worker pinning, barriers and THP; include a 27B bandwidth-bound negative control.",
        "Retain exact-token checks across thread counts as an additional witness when a generated CPU candidate reaches operator, numerical and served gates."
      ]
    },
    {
      "id": "intake-3013",
      "integration_disposition": "monitor",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "When a qualified checkpoint contains sliding-window q/k/v mixing, trace window KV/cache traffic separately from recurrence on both backends and compare matched quality/latency."
      ]
    },
    {
      "id": "intake-3014",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/harness-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Audit retained all-fail trajectory groups for reproducible environment state, a bounded repair point and verifiable continuation. Count recoverable groups before proposing any training or changing MemRL rewards."
      ]
    },
    {
      "id": "intake-3015",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/memory-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons."
      ]
    },
    {
      "id": "intake-3016",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/routing-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals."
      ]
    },
    {
      "id": "intake-3017",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/eval-tower-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Measure held-out pairs with component-only, combined single-call, explicit two-call and partner-shuffled arms; record step retention, token and tool cost by model. Keep soft-prefix findings separate from text-skill outcomes."
      ]
    },
    {
      "id": "intake-3018",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/memory-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence."
      ]
    },
    {
      "id": "intake-3019",
      "integration_disposition": "monitor",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "Reopen when a qualified recurrent-depth model exposes latent-state initialization and adaptive exit. Compare loops, wall time, quality and acceptance at fixed effort on CPU and MI210 separately."
      ]
    },
    {
      "id": "intake-3020",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/rocm-kernel-authoring.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check."
      ]
    },
    {
      "id": "intake-3021",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/quantization-and-low-bit.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3."
      ]
    },
    {
      "id": "intake-3022",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/memory-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons."
      ]
    },
    {
      "id": "intake-3023",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/routing-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals."
      ]
    },
    {
      "id": "intake-3024",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/memory-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence."
      ]
    }
  ],
  "opportunity_reviews": {
    "P1": {
      "project_objective": "Identify sampled HIP instructions in existing binaries",
      "implementation_ref": "Root b93bd3172 / rocm-kernel-authoring.md:1122",
      "gap": "The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack.",
      "operational_change": "Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check.",
      "benefit_direction": "Identify sampled HIP instructions in existing binaries",
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "execution_conditions": "Use the original ELFs, code objects, store manifests and build IDs. Keep one other binary for validation. Record symbol+offset, source line or unmappable reason for each sampled PC. Only trial host-trap if unresolved hotspots remain and firmware/driver enumerate the capability; collect separate baseline runtime and check perturbation, skid and sample loss.",
      "closure_basis": "The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack."
    },
    "P2": {
      "project_objective": "Decide whether decode scheduling limits IQ4 or EXL3",
      "implementation_ref": "Root b93bd3172 / llama.cpp@ffc1bac82:ggml/src/ggml-cuda/vecdotq.cuh:34,1320,1344; quantization-and-low-bit.md:359",
      "gap": "Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof.",
      "operational_change": "Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3.",
      "benefit_direction": "Decide whether decode scheduling limits IQ4 or EXL3",
      "owner": "handoffs/active/quantization-and-low-bit.md",
      "execution_conditions": "Freeze the full nibble, sign and scale oracle and retained kernel traces; compare existing permute helper with alternative decode-to-issue placement at equal layout. On wave64 price VGPR occupancy, 64 KB LDS per CU, memory stalls, MFMA issue and spills. Reject a numerical mismatch; require improvement on later actual shapes before a served trial. CPU analogue is lane-local byte shuffles plus widened signed dot, measured separately.",
      "closure_basis": "Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof."
    },
    "P3": {
      "project_objective": "Identify underfilled F32 router GEMMs",
      "implementation_ref": "Root b93bd3172 / kv-cache-program.md:1947",
      "gap": "The existing Q8 atomic-flush determinism task addresses a different type and reduction path.",
      "operational_change": "Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise.",
      "benefit_direction": "Identify underfilled F32 router GEMMs",
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "execution_conditions": "Reuse retained A3B router traces at decode and prefill. Baseline is the resolved Tensile solution; keep a later request window. Record M/N/K, workgroups, slices and all partial-buffer writes. The upstream half-CU test bounds unsplit tile count, not slices. Stop if even eliminating targeted time would miss the owner’s served gate. Test CPU splitting only for underoccupied cores after NPS4-local partitioning.",
      "closure_basis": "The existing Q8 atomic-flush determinism task addresses a different type and reduction path."
    },
    "P4": {
      "project_objective": "Decide whether to specialize a HIP V-load bound",
      "implementation_ref": "Root b93bd3172 / rocm-kernel-authoring.md:1212; llama.cpp@ffc1bac82:ggml/src/ggml-cuda/fattn-mma-f16.cuh",
      "gap": "A CUDA stack frame reduction gives no proof of scratch traffic on the active gfx90a specialization. RF7 changes wave-level streaming.",
      "operational_change": "Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles.",
      "benefit_direction": "Decide whether to specialize a HIP V-load bound",
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "execution_conditions": "Compare deployed GPU symbols on a train and holdout context length, retaining code-object hash, VGPR/scratch metadata, ISA and dispatch hits. A nonzero private segment alone cannot prove traffic. Stop on absent path or equal material scratch traffic; specialize and time only if affected. Check both padded and unpadded tails.",
      "closure_basis": "A CUDA stack frame reduction gives no proof of scratch traffic on the active gfx90a specialization. RF7 changes wave-level streaming."
    },
    "P5": {
      "project_objective": "Determine eligible F32 verify work",
      "implementation_ref": "Root b93bd3172 / autokernel-loop.md:5336; rocm-kernel-authoring.md:1150",
      "gap": "Completed Q8 w8 and queued fused small-K width 1–4 work do not count F32 rows by M and verify width.",
      "operational_change": "Classify retained verify calls by input type, rows, K, verify columns and selected kernel. Bound F32 time that a weight-sharing GEMV could recover against served dispatch. Stop at zero eligible share or an immaterial upper bound.",
      "benefit_direction": "Determine eligible F32 verify work",
      "owner": "handoffs/active/autokernel-loop.md",
      "execution_conditions": "Freeze verify traces from both dense and MoE, train/test split by request. Report all rows and F32-eligible rows by width, M and K. Preserve actual dispatch including width one and wide M; compare incumbent GEMV versus tiled GEMM for surviving bins. On CPU compare blocked GEMV to existing GEMM with NUMA-local weights; never import Adreno subgroups or the numeric threshold.",
      "closure_basis": "Completed Q8 w8 and queued fused small-K width 1–4 work do not count F32 rows by M and verify width."
    },
    "P6": {
      "project_objective": "Price adaptive expert caching versus a static pool",
      "implementation_ref": "Root b93bd3172 / cpu-decode-roofline-program.md:5995",
      "gap": "The current static-pool replay already prices cold routes; logical layer IDs can misrepresent cache pressure and miss overlap.",
      "operational_change": "Extend the existing static-pool replay with physical tensor identity, capacity-matched LRU and measured NUMA-local CPU-miss versus PCIe upload costs. Compare static pool, LRU, CPU-share and unpatched cache under identical route order.",
      "benefit_direction": "Price adaptive expert caching versus a static pool",
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "execution_conditions": "Bind each expert tensor to a physical bank, backend and epoch. Reserve model, KV and scratch before pricing the pool; hold back later routes. Output every hit/miss, unique bytes, PCIe overlap, CPU affinity, and uncovered bank. Stop if experts fit, identities are all distinct for dedup, or cold-route/transfer costs erase the margin; report these cases separately.",
      "closure_basis": "The current static-pool replay already prices cold routes; logical layer IDs can misrepresent cache pressure and miss overlap."
    },
    "P7": {
      "project_objective": "Preserve greedy parity near logit ties",
      "implementation_ref": "Root b93bd3172 / speculative-decoding.md:1511; llama.cpp@ffc1bac82:ggml/src/ggml-cpu/arch/x86/repack.cpp",
      "gap": "The sampler fixture starts after logit formation; a Q8 activation rounding error can change which logit is largest before sampling.",
      "operational_change": "Replay near-tie and ordinary rows with incumbent Q8, per-block signed Q15 and FP32 reference. Save top-two gaps, argmax flips, accumulators and conversion cost; verify AVX-512 signed-word dot semantics and overflow against a scalar oracle.",
      "benefit_direction": "Preserve greedy parity near logit ties",
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "execution_conditions": "Freeze pre-activation rows plus weight bytes and golden logits with deliberate near and wide gaps; compare Q8, Q15 and reference on unseen prompts and thread counts. Persist token, gap, logits, packing time, and signed-pair overflow cases. Reject a candidate on a new held-out greedy mismatch or if conversion cost erases its measured benefit.",
      "closure_basis": "The sampler fixture starts after logit formation; a Q8 activation rounding error can change which logit is largest before sampling."
    },
    "P8": {
      "project_objective": "Decide whether small CPU heads merit a resident/streamed split",
      "implementation_ref": "Root b93bd3172 / autokernel-akx-program.md:1393; speculative-decoding.md:30",
      "gap": "The completed NTA-only seed failed its speed gate; it did not partition a reusable working set by CCD capacity.",
      "operational_change": "Compare resident and streaming layer subsets for a draft head after accounting for per-CCD weight duplication, KV and scratch. Isolate four-row blocking, worker pinning, barriers and THP; include a 27B bandwidth-bound negative control.",
      "benefit_direction": "Decide whether small CPU heads merit a resident/streamed split",
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "execution_conditions": "Size working sets per CCD after KV and scratch. Baselines include current champion, NTA-only and unmodified OS page policy. Record realized page size and NUMA placement plus per-thread work; separate prefill, single-stream and drafts at a later prompt/width. Stop if LLC misses or matched-throughput intervals fail to improve, or if a negative control regresses.",
      "closure_basis": "The completed NTA-only seed failed its speed gate; it did not partition a reusable working set by CCD capacity."
    },
    "M9": {
      "project_objective": "Evaluate generated kernels under the existing promotion procedure",
      "implementation_ref": "Root b93bd3172 / autokernel-loop.md; MEASUREMENT.md",
      "gap": "Golden greedy prompts exercise too few shapes for kernel promotion. Wall time, turns and cost are author-reported and provide planning context.",
      "operational_change": "Retain exact-token checks across thread counts as an additional witness when a generated CPU candidate reaches operator, numerical and served gates.",
      "benefit_direction": "Evaluate generated kernels under the existing promotion procedure",
      "owner": "handoffs/active/autokernel-loop.md",
      "execution_conditions": "Apply only at the existing AutoKernel candidate gate. Record full build/recipe and aggregate agent cost separately from runtime; exact greedy fixtures supplement backend, KLD and served-baseline checks.",
      "closure_basis": "Golden greedy prompts exercise too few shapes for kernel promotion. Wall time, turns and cost are author-reported and provide planning context."
    },
    "M10": {
      "project_objective": "Recognize a future local-mixer architecture",
      "implementation_ref": "Root b93bd3172 / autokernel-loop.md:5217; cpu-decode-roofline-program.md:2036",
      "gap": "Existing GDN fusion and KDA exponential work measure recurrence or state movement; substituting a trained mixer changes the model.",
      "operational_change": "When a qualified checkpoint contains sliding-window q/k/v mixing, trace window KV/cache traffic separately from recurrence on both backends and compare matched quality/latency.",
      "benefit_direction": "Recognize a future local-mixer architecture",
      "owner": "handoffs/active/autokernel-loop.md",
      "execution_conditions": "Checkpoint-and-architecture trigger only. Keep causal window width and pre-mix keys explicit. Compare quality at equal training budget before any inference-cost conclusion. GPU wave/LDS tiling and CPU memory traffic belong to the resulting graph.",
      "closure_basis": "Existing GDN fusion and KDA exponential work measure recurrence or state movement; substituting a trained mixer changes the model."
    },
    "P11": {
      "project_objective": "Decide whether failed groups can support local repairs",
      "implementation_ref": "Root b93bd3172 / epyc-orchestrator@59a1d469:src/graph/trajectory_artifact.py; src/api/services/memrl.py:56",
      "gap": "A terminal MemRL failure score does not encode the first repairable action, options or a validated continuation.",
      "operational_change": "Audit retained all-fail trajectory groups for reproducible environment state, a bounded repair point and verifiable continuation. Count recoverable groups before proposing any training or changing MemRL rewards.",
      "benefit_direction": "Decide whether failed groups can support local repairs",
      "owner": "handoffs/active/harness-program.md",
      "execution_conditions": "Freeze same-policy group membership, exact task environment, tools, rollouts and rewards; hold out tasks. Record all failures including infra faults, repairability, local success and continuation success separately. Advance a training proposal only if at least one held-out repair verifies end to end and usable counts support the planned comparison; never relabel terminal failures from local success alone.",
      "closure_basis": "A terminal MemRL failure score does not encode the first repairable action, options or a validated continuation."
    },
    "P12": {
      "project_objective": "Select a cheaper memory harness without leaking evaluation data",
      "implementation_ref": "Root b93bd3172 / memory-program.md:526,562; epyc-inference-research:scripts/benchmark/beam_memory_retrievers.py",
      "gap": "M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases.",
      "operational_change": "Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons.",
      "benefit_direction": "Select a cheaper memory harness without leaking evaluation data",
      "owner": "handoffs/active/memory-program.md",
      "execution_conditions": "Pin M-12 judge, prompts, receipts, dataset and explicit independent BEAM partition. Hold out conversations from search, filter post-hoc intersections visibly and score all scheduled cases. Compare incumbent, smoke-gated and fully evaluated candidate on quality, total construction cost, query tokens, and unchanged-memory reuse. Reject leaked cases or unverified archive hashes. Preserve ratified abstention handling.",
      "closure_basis": "M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases."
    },
    "P13": {
      "project_objective": "Test whether routing improves under a fixed local capacity budget",
      "implementation_ref": "Root b93bd3172 / epyc-orchestrator@59a1d469:src/typed_decisions/routing_replay.py; src/graph/budgets.py",
      "gap": "Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost.",
      "operational_change": "Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals.",
      "benefit_direction": "Test whether routing improves under a fixed local capacity budget",
      "owner": "handoffs/active/routing-program.md",
      "execution_conditions": "Replay ordered arrival sets without future leakage. Compare incumbent, percentile pacing with same demand scores, and full lookahead under identical occupancy and budget; use a later trace with bursts. Report per-request route, satisfaction definition, time, starvation and budget breaches. Advance only on budget compliance and positive held-out utility over pacing after solver cost.",
      "closure_basis": "Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost."
    },
    "P14": {
      "project_objective": "Detect skill interactions hidden by single-skill uplift",
      "implementation_ref": "Root b93bd3172 / eval-tower-program.md:3255; epyc-orchestrator@59a1d469:orchestration/repl_memory/replay/skill_replay.py",
      "gap": "Local skills are text/tool bundles, whereas the source trains continuous prompts. The existing null replay records single-task effects.",
      "operational_change": "Measure held-out pairs with component-only, combined single-call, explicit two-call and partner-shuffled arms; record step retention, token and tool cost by model. Keep soft-prefix findings separate from text-skill outcomes.",
      "benefit_direction": "Detect skill interactions hidden by single-skill uplift",
      "owner": "handoffs/active/eval-tower-program.md",
      "execution_conditions": "Freeze model, executor, evidence and cost ceiling. Compare both orders, shuffled partners, constituent controls and explicit two-step intermediate on held-out tasks. Record stale skills, tool failures, invalid completions, abstentions and additional compute. Reopen admission policy only for effects surviving shuffled labels and cost-matched controls.",
      "closure_basis": "Local skills are text/tool bundles, whereas the source trains continuous prompts. The existing null replay records single-task effects."
    },
    "P15": {
      "project_objective": "Test deterministic retrieval into post-compaction history",
      "implementation_ref": "Root b93bd3172 / epyc-orchestrator@59a1d469:src/graph/compaction.py:115; memory-program.md:526",
      "gap": "Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory writes.",
      "operational_change": "Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence.",
      "benefit_direction": "Test deterministic retrieval into post-compaction history",
      "owner": "handoffs/active/memory-program.md",
      "execution_conditions": "Use identical conversations, raw turns, parser version and token cap. Compare lexical/hybrid, exact mentions, released first-mention heuristic and dependency/alias gated edges. Record raw episode IDs, all-gold recall, time/order failures, build and query wall time measured externally. Promote only if held-out evidence recall or answer quality improves without exceeding the cost ceiling.",
      "closure_basis": "Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory writes."
    },
    "M16": {
      "project_objective": "Reduce loops per decoded token on recurrent-depth models",
      "implementation_ref": "Root b93bd3172 / context-and-token-economy.md:2598; speculative-decoding.md:258",
      "gap": "The existing DFlash2 target/drafter interface has no interchangeable fixed-point latent; layer savings depend on stability of a shared recurrent block.",
      "operational_change": "Reopen when a qualified recurrent-depth model exposes latent-state initialization and adaptive exit. Compare loops, wall time, quality and acceptance at fixed effort on CPU and MI210 separately.",
      "benefit_direction": "Reduce loops per decoded token on recurrent-depth models",
      "owner": "handoffs/active/speculative-decoding.md",
      "execution_conditions": "Require a serving candidate with repeated shared weights, a stable latent convention and a real adaptive exit. Freeze input/exit rules and compare the lived adaptive workload separately from trajectory replay on CPU/GPU. Include warm-start overhead and speculative verification.",
      "closure_basis": "The existing DFlash2 target/drafter interface has no interchangeable fixed-point latent; layer savings depend on stability of a shared recurrent block."
    }
  },
  "opportunity_scan": [
    {
      "scan_id": "S1-1",
      "source_ref": "intake-3006#record Introduction, HTML L785–788",
      "implementation_ref": "Root b93bd3172 / rocm-kernel-authoring.md:1122",
      "mechanism": "The guide places the PC sampling tooling in ROCm 6.4 and later.",
      "consumer": "handoffs/active/rocm-kernel-authoring.md",
      "application": "Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-1"
      ],
      "basis": "The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack."
    },
    {
      "scan_id": "S1-2",
      "source_ref": "intake-3020#record PC sampling availability and configuration, HTML L703–713",
      "implementation_ref": "Root b93bd3172 / rocm-kernel-authoring.md:1122",
      "mechanism": "The ROCprofiler SDK example advertises host-trap time sampling on gfx90a.",
      "consumer": "handoffs/active/rocm-kernel-authoring.md",
      "application": "Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-1"
      ],
      "basis": "The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack."
    },
    {
      "scan_id": "S2-1",
      "source_ref": "intake-3007#record Summary, HTML L1475",
      "implementation_ref": "Root b93bd3172 / llama.cpp@ffc1bac82:ggml/src/ggml-cuda/vecdotq.cuh:34,1320,1344; quantization-and-low-bit.md:359",
      "mechanism": "At the tested MI300X geometry, against the reference software decode, the LUT sped up GEMM1 by 2.2×–2.4× and GEMM2 by 1.7×–2.5×.",
      "consumer": "handoffs/active/quantization-and-low-bit.md",
      "application": "Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-2"
      ],
      "basis": "Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof."
    },
    {
      "scan_id": "S2-2",
      "source_ref": "intake-3021#record aiter/ops/flydsl/kernels/moe_2stage_a16wmix/utils.py:L811-L814 @ baef815",
      "implementation_ref": "Root b93bd3172 / llama.cpp@ffc1bac82:ggml/src/ggml-cuda/vecdotq.cuh:34,1320,1344; quantization-and-low-bit.md:359",
      "mechanism": "A compile-time gfx942 branch selects a byte-permute E2M1 decode.",
      "consumer": "handoffs/active/quantization-and-low-bit.md",
      "application": "Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-2"
      ],
      "basis": "Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof."
    },
    {
      "scan_id": "S3-1",
      "source_ref": "intake-3008#record ggml/src/ggml-cuda/ggml-cuda.cu:L1941-L1947 @ 9384a12",
      "implementation_ref": "Root b93bd3172 / kv-cache-program.md:1947",
      "mechanism": "Split-K is gated to selected HIP RDNA3 targets with K at least 2048, excluding the base RDNA3 code.",
      "consumer": "handoffs/active/rocm-kernel-authoring.md",
      "application": "Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-3"
      ],
      "basis": "The existing Q8 atomic-flush determinism task addresses a different type and reduction path."
    },
    {
      "scan_id": "S4-1",
      "source_ref": "intake-3009#record ggml/src/ggml-cuda/fattn-mma-f16.cuh:L944-L949 @ 078992f",
      "implementation_ref": "Root b93bd3172 / rocm-kernel-authoring.md:1212; llama.cpp@ffc1bac82:ggml/src/ggml-cuda/fattn-mma-f16.cuh",
      "mechanism": "The unpadded head case uses a constant V length and leaves the clamp for padded V.",
      "consumer": "handoffs/active/rocm-kernel-authoring.md",
      "application": "Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-4"
      ],
      "basis": "A CUDA stack frame reduction gives no proof of scratch traffic on the active gfx90a specialization. RF7 changes wave-level streaming."
    },
    {
      "scan_id": "S5-1",
      "source_ref": "intake-3010#record ggml/src/ggml-opencl/kernels/mul_mm_f32_f32_l4_lm.cl:L225-L232 @ 9fa7a33",
      "implementation_ref": "Root b93bd3172 / autokernel-loop.md:5336; rocm-kernel-authoring.md:1150",
      "mechanism": "The kernel hoists each weight vector before iterating narrow columns.",
      "consumer": "handoffs/active/autokernel-loop.md",
      "application": "Classify retained verify calls by input type, rows, K, verify columns and selected kernel. Bound F32 time that a weight-sharing GEMV could recover against served dispatch. Stop at zero eligible share or an immaterial upper bound.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-5"
      ],
      "basis": "Completed Q8 w8 and queued fused small-K width 1–4 work do not count F32 rows by M and verify width."
    },
    {
      "scan_id": "S6-1",
      "source_ref": "intake-3011#record src/llama-moe-cache.cpp:L430-L437 @ f13dcdf",
      "implementation_ref": "Root b93bd3172 / cpu-decode-roofline-program.md:5995",
      "mechanism": "Grouping host-resident expert banks requires the same assigned backend device and matching expert tensor pointers.",
      "consumer": "handoffs/active/cpu-decode-roofline-program.md",
      "application": "Extend the existing static-pool replay with physical tensor identity, capacity-matched LRU and measured NUMA-local CPU-miss versus PCIe upload costs. Compare static pool, LRU, CPU-share and unpatched cache under identical route order.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-6"
      ],
      "basis": "The current static-pool replay already prices cold routes; logical layer IDs can misrepresent cache pressure and miss overlap."
    },
    {
      "scan_id": "S7-1",
      "source_ref": "intake-3012#record neon/REPORT.md:L128-L136 @ 2d53727",
      "implementation_ref": "Root b93bd3172 / speculative-decoding.md:1511; llama.cpp@ffc1bac82:ggml/src/ggml-cpu/arch/x86/repack.cpp",
      "mechanism": "Neon reports 188.35 mean/188.93 peak vs recorded 103.82 tok/s at 32T.",
      "consumer": "handoffs/active/cpu-decode-roofline-program.md",
      "application": "Replay near-tie and ordinary rows with incumbent Q8, per-block signed Q15 and FP32 reference. Save top-two gaps, argmax flips, accumulators and conversion cost; verify AVX-512 signed-word dot semantics and overflow against a scalar oracle.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-7"
      ],
      "basis": "The sampler fixture starts after logit formation; a Q8 activation rounding error can change which logit is largest before sampling."
    },
    {
      "scan_id": "S8-1",
      "source_ref": "intake-3012#record neon/REPORT.md:L128-L136 @ 2d53727",
      "implementation_ref": "Root b93bd3172 / autokernel-akx-program.md:1393; speculative-decoding.md:30",
      "mechanism": "Neon reports 188.35 mean/188.93 peak vs recorded 103.82 tok/s at 32T.",
      "consumer": "handoffs/active/cpu-decode-roofline-program.md",
      "application": "Compare resident and streaming layer subsets for a draft head after accounting for per-CCD weight duplication, KV and scratch. Isolate four-row blocking, worker pinning, barriers and THP; include a 27B bandwidth-bound negative control.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-8"
      ],
      "basis": "The completed NTA-only seed failed its speed gate; it did not partition a reusable working set by CCD capacity."
    },
    {
      "scan_id": "S9-1",
      "source_ref": "intake-3012#record neon/REPORT.md:L128-L136 @ 2d53727",
      "implementation_ref": "Root b93bd3172 / autokernel-loop.md; MEASUREMENT.md",
      "mechanism": "Neon reports 188.35 mean/188.93 peak vs recorded 103.82 tok/s at 32T.",
      "consumer": "handoffs/active/autokernel-loop.md",
      "application": "Retain exact-token checks across thread counts as an additional witness when a generated CPU candidate reaches operator, numerical and served gates.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-NOV27-9"
      ],
      "basis": "Golden greedy prompts exercise too few shapes for kernel promotion. Wall time, turns and cost are author-reported and provide planning context."
    },
    {
      "scan_id": "S10-1",
      "source_ref": "intake-3013#record §3.1, last paragraph (#S3.SS1)",
      "implementation_ref": "Root b93bd3172 / autokernel-loop.md:5217; cpu-decode-roofline-program.md:2036",
      "mechanism": "The learned Q/K/V mixer preserves the original recurrence and chunkwise parallel algorithm in the two tested backbones.",
      "consumer": "handoffs/active/autokernel-loop.md",
      "application": "When a qualified checkpoint contains sliding-window q/k/v mixing, trace window KV/cache traffic separately from recurrence on both backends and compare matched quality/latency.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-NOV27-10"
      ],
      "basis": "Existing GDN fusion and KDA exponential work measure recurrence or state movement; substituting a trained mixer changes the model."
    },
    {
      "scan_id": "S11-1",
      "source_ref": "intake-3014#record §4.1, learner-conditioned evaluation (#S4.SS1)",
      "implementation_ref": "Root b93bd3172 / epyc-orchestrator@59a1d469:src/graph/trajectory_artifact.py; src/api/services/memrl.py:56",
      "mechanism": "Local guidance values come from execution by the current learner after bounded teacher-proposed options.",
      "consumer": "handoffs/active/harness-program.md",
      "application": "Audit retained all-fail trajectory groups for reproducible environment state, a bounded repair point and verifiable continuation. Count recoverable groups before proposing any training or changing MemRL rewards.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-11"
      ],
      "basis": "A terminal MemRL failure score does not encode the first repairable action, options or a validated continuation."
    },
    {
      "scan_id": "S12-1",
      "source_ref": "intake-3015#record §3.2, session-level versioning (#S3.SS2)",
      "implementation_ref": "Root b93bd3172 / memory-program.md:526,562; epyc-inference-research:scripts/benchmark/beam_memory_retrievers.py",
      "mechanism": "Capture construction history per session to localize omission, maintenance damage, retrieval miss and answer misuse from trajectory evidence.",
      "consumer": "handoffs/active/memory-program.md",
      "application": "Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-12"
      ],
      "basis": "M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases."
    },
    {
      "scan_id": "S12-2",
      "source_ref": "intake-3022#record plugins/home/README.md:12–15",
      "implementation_ref": "Root b93bd3172 / memory-program.md:526,562; epyc-inference-research:scripts/benchmark/beam_memory_retrievers.py",
      "mechanism": "HoMe retains content-verified archives for final replay and records the specific reviewed SHA-256.",
      "consumer": "handoffs/active/memory-program.md",
      "application": "Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-12"
      ],
      "basis": "M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases."
    },
    {
      "scan_id": "S13-1",
      "source_ref": "intake-3016#record §5.2, fixed GPU pools and redeployment (#S5.SS2.SSS0.Px3)",
      "implementation_ref": "Root b93bd3172 / epyc-orchestrator@59a1d469:src/typed_decisions/routing_replay.py; src/graph/budgets.py",
      "mechanism": "Trace replay uses a fungible FLOP budget and assumes instantaneous GPU redeployment.",
      "consumer": "handoffs/active/routing-program.md",
      "application": "Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-13"
      ],
      "basis": "Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost."
    },
    {
      "scan_id": "S13-2",
      "source_ref": "intake-3023#record §2.2.3 online cost policy (#S2.SS2.SSS3)",
      "implementation_ref": "Root b93bd3172 / epyc-orchestrator@59a1d469:src/typed_decisions/routing_replay.py; src/graph/budgets.py",
      "mechanism": "The paper divides a fixed-length sequence into budget bins and carries unused budget forward.",
      "consumer": "handoffs/active/routing-program.md",
      "application": "Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-13"
      ],
      "basis": "Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost."
    },
    {
      "scan_id": "S14-1",
      "source_ref": "intake-3017#record §4.1 Table 1",
      "implementation_ref": "Root b93bd3172 / eval-tower-program.md:3255; epyc-orchestrator@59a1d469:orchestration/repl_memory/replay/skill_replay.py",
      "mechanism": "Digit one-call composition accuracy averaged 0.9% to 6.4% in this experiment.",
      "consumer": "handoffs/active/eval-tower-program.md",
      "application": "Measure held-out pairs with component-only, combined single-call, explicit two-call and partner-shuffled arms; record step retention, token and tool cost by model. Keep soft-prefix findings separate from text-skill outcomes.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-14"
      ],
      "basis": "Local skills are text/tool bundles, whereas the source trains continuous prompts. The existing null replay records single-task effects."
    },
    {
      "scan_id": "S15-1",
      "source_ref": "intake-3018#record §3.2",
      "implementation_ref": "Root b93bd3172 / epyc-orchestrator@59a1d469:src/graph/compaction.py:115; memory-program.md:526",
      "mechanism": "Incidence edges are provenance through co-occurrence, without semantic entailment.",
      "consumer": "handoffs/active/memory-program.md",
      "application": "Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-15"
      ],
      "basis": "Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory writes."
    },
    {
      "scan_id": "S15-2",
      "source_ref": "intake-3024#record src/mgmem/query_parser.py:L60-L76 @ 67c53a2",
      "implementation_ref": "Root b93bd3172 / epyc-orchestrator@59a1d469:src/graph/compaction.py:115; memory-program.md:526",
      "mechanism": "Public parser uses its first extracted mention as subject.",
      "consumer": "handoffs/active/memory-program.md",
      "application": "Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-NOV27-15"
      ],
      "basis": "Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory writes."
    },
    {
      "scan_id": "S16-1",
      "source_ref": "intake-3019#record §4.2 operating point",
      "implementation_ref": "Root b93bd3172 / context-and-token-economy.md:2598; speculative-decoding.md:258",
      "mechanism": "Huginn operating point uses 40.1 vs 46.8 layers/token on pooled math.",
      "consumer": "handoffs/active/speculative-decoding.md",
      "application": "Reopen when a qualified recurrent-depth model exposes latent-state initialization and adaptive exit. Compare loops, wall time, quality and acceptance at fixed effort on CPU and MI210 separately.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-NOV27-16"
      ],
      "basis": "The existing DFlash2 target/drafter interface has no interchangeable fixed-point latent; layer savings depend on stability of a shared recurrent block."
    }
  ],
  "actionable_additions": [],
  "steering_reconciliation": [
    {
      "seq": 1,
      "stage": 1,
      "verbatim": "Please use the research-intake to process these sources and steering hypotheses: https://rocm.blogs.amd.com/software-tools-optimization/pc-sampling-rocprofiler/README.html https://rocm.blogs.amd.com/artificial-intelligence/gfx942-moe-mxfp4/README.html https://github.com/ggml-org/llama.cpp/pull/33167 https://github.com/ggml-org/llama.cpp/pull/33161 https://github.com/ggml-org/llama.cpp/pull/33098 https://github.com/ggml-org/llama.cpp/pull/33130 https://github.com/alesha-pro/machine-code-llm-battle https://x.com/superalesha/status/2126041962272690479 https://arxiv.org/abs/2611.33257 https://arxiv.org/abs/2611.34777 https://arxiv.org/abs/2611.34624 https://arxiv.org/abs/2611.34161 https://arxiv.org/abs/2611.34398 https://arxiv.org/abs/2611.33174 https://arxiv.org/abs/2611.34492\n\nOperator steering (context for Stage 1 ranking and Stage 3 grounding, not authorization to write handoffs):\n\nKERNELS / LOW-LEVEL",
      "disposition": "context-only",
      "plan_ref": null,
      "reason": "Scope instruction preserved. The announcement is provenance only; expansion was preauthorized, and handoff filing requires plan review."
    },
    {
      "seq": 2,
      "stage": 1,
      "verbatim": "1. ROCm blog, PC sampling in ROCprofiler-SDK (rocprofv3): host-trap (software) PC sampling available from MI200 series on ROCm 6.4+; stochastic (hardware, stall reasons) CDNA3/CDNA4/CDNA5 only; works on precompiled binaries; worked GEMM example traced a naive kernel to uncoalesced global loads. Hardware: host-trap runs on gfx90a but requires ROCm >= 6.4 (host is on 6.2); stochastic does not run on gfx90a.\n   Value: instruction-level hotspots for MMQ/MMVQ/fattn in the fork and AutoKernel candidates without recompiling; input to a ROCm upgrade decision (rocm-kernel-authoring, AutoKernel census).\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: host-trap sampling flow on gfx90a under ROCm 6.4+/TheRock; mapping hotspots back to source lines in HIP kernels.)",
      "disposition": "planned",
      "plan_ref": "P1",
      "reason": "The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack."
    },
    {
      "seq": 3,
      "stage": 1,
      "verbatim": "2. ROCm blog, MXFP4 MoE on MI300 with FlyDSL (a16wmix kernels): replacing reference software FP4 decode with a bit-exact v_perm_b32 byte LUT (ROCm/aiter#5583) made GEMM1 2.2x-2.4x and GEMM2 1.7x-2.5x faster on MI300X from 1 to 8192 tokens; nonzero decoded bf16 weights bit-identical for every e8m0 scale up to 0xFC. Hardware: gfx942 only; MXFP4/FlyDSL do not run on gfx90a.\n   Value: v_perm_b32 LUT decode for IQ4_XS / IQ4_NL and EXL3-style codebook dequant in MMVQ/MMQ (INF-80 EXL3, NARIQ-LIBTRELLIS-MAP-1 design note, AutoKernel); counter + thread-trace methodology for locating a decode limiter.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: v_perm_b32 byte-LUT nibble decode, VALU vs MFMA instruction-mix ratio as the limiter signal, decode placement relative to MFMA issue.)",
      "disposition": "planned",
      "plan_ref": "P2",
      "reason": "Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof."
    },
    {
      "seq": 4,
      "stage": 1,
      "verbatim": "3. llama.cpp PR #33167 (draft), HIP split-K F32 GEMM for untuned RDNA3: small-output long-K F32 GEMMs 9.1x (64x256, K=4608), 4.7x (128x256, K=2304), 9.0x (64x192, K=4608) vs rocBLAS SGEMM; NMSE ~1e-12 vs unsplit; Qwen3.6-35B-A3B pp512 693 -> 730 t/s at ub256 (RX 7700 XT, ROCm 10.2). Hardware: gated to gfx1101-1103/gfx1150-1153; not gfx90a.\n   Value: check F32 router (ffn_gate_inp) and other skinny long-K F32 GEMMs on gfx90a for Tensile underutilization; fixed-order slice reduce relevant to GPU-27B-SKINNY-SPLITK-DETERMINISM-1 / C11-SKINNY-DET.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: split-K slice count capped at nsm/2, shape-based dispatch rule, deterministic reduction of slices.)",
      "disposition": "planned",
      "plan_ref": "P3",
      "reason": "The existing Q8 atomic-flush determinism task addresses a different type and reduction path."
    },
    {
      "seq": 5,
      "stage": 1,
      "verbatim": "4. llama.cpp PR #33161, CUDA fattn-mma-f16 constant V load length: one-line change passing compile-time 2*nbatch_V2 when DVp == DV; 512-head f16 kernel stack frame 272 B -> 16 B; pp16000 ~1053 -> ~1940 t/s, pp32000 ~652 -> ~1699 t/s on RTX A6000; test-backend-ops FLASH_ATTN_EXT 4430/4430 pass. Hardware: CUDA sm_86; not gfx90a.\n   Value: audit HIP builds of fattn kernels on gfx90a for scratch spills from runtime load lengths (G3-KTRACE gv_fattn path, VATTN-ROOFLINE-5).\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: compile-time constant loop bounds to eliminate scratch/stack usage; check private-segment size in gfx90a code objects.)",
      "disposition": "planned",
      "plan_ref": "P4",
      "reason": "A CUDA stack frame reduction gives no proof of scratch traffic on the active gfx90a specialization. RF7 changes wave-level streaming."
    },
    {
      "seq": 6,
      "stage": 1,
      "verbatim": "5. llama.cpp PR #33098 (merged), OpenCL multi-token F32 GEMV for spec verify: gemma-4-E4B Q4_K_M, draft-n-max 7, decode 32.959 -> 34.280 t/s, acceptance unchanged at 41.720%; ne01 > 512 still uses tiled GEMM. Hardware: OpenCL/Adreno; not gfx90a.\n   Value: multi-column GEMV for small verify widths (AK-SHORT-ROW-CENSUS, fused small-K MMVQ census, INF-50 DFlash2 verify).\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: GEMV-vs-tiled-GEMM dispatch threshold by width and ne01; weight reuse across verify columns.)",
      "disposition": "planned",
      "plan_ref": "P5",
      "reason": "Completed Q8 w8 and queued fused small-K width 1–4 work do not count F32 rows by M and verify width."
    },
    {
      "seq": 7,
      "stage": 1,
      "verbatim": "6. llama.cpp PR #33130 (draft), moe-cache physical expert-bank dedup for looped MoE: Inkling-2-Mini IQ3_S on RTX 2070 8 GB + i7-13700K: no cache 8.5 pp / 13.4 tg t/s; 2800 MiB cache 21.3 / 16.7 t/s (82.12% hit rate); cpu-share 0.65 33.0 / 21.6 t/s (78.81% hit rate). Hardware: CUDA-tested; backend-generic host logic.\n   Value: VRAM expert cache on MI210 with experts in EPYC DDR5 for A3B after the null C22 CPU composite (MOE-STATIC-POOL-REPLAY).\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: expert slot LRU over PCIe Gen4, CPU-share split for cache misses, NPS4 placement of host expert banks.)",
      "disposition": "planned",
      "plan_ref": "P6",
      "reason": "The current static-pool replay already prices cold routes; logical layer IDs can misrepresent cache pressure and miss overlap."
    },
    {
      "seq": 8,
      "stage": 1,
      "verbatim": "7. alesha-pro/machine-code-llm-battle (GitHub; primary source, read opus/REPORT.md, neon/REPORT.md and FORMAT_SPEC.md in full): Claude Opus 5.5 and Gemini 4 Neon each hand-wrote a Qwen3-0.6B Q8_0 CPU decode engine as raw x86-64 machine code (engine.hex -> xxd, no compiler/assembler/libc). Both 16/16 exact vs golden greedy refs (4 prompts x 1/4/8/16 threads), bit-exact across thread counts. EPYC 7642 (Zen 2, 48 cores, AVX2/FMA/F16C, no AVX-512, 256 MiB L3), 34-token prompt / 64 generated, mean of 3: llama.cpp (llama-bench -ngl 0) 16.63 -> 103-105 tok/s plateau from 16-40 threads; Opus 21.44-125.13 (+10.4% to +28.9%), 7,331 B ELF, ~65 min, 175 turns, $21.40; Neon 22.27-188.35 (+33.9% to +81.4%, peak 32 threads), 10,752 B ELF, 1 h 43 min, 90 turns, $16.72. Opus: f32 activations x Q8_0, 4-row matvec, software prefetch, weights pread64'd into a THP buffer, spin-barrier pool pinned per CCX. Neon: int8 activations missed one token on a 0.0005 top-2 logit gap, so switched to per-32-block Q15 (int16) activations via vpmovsxbw + vpmaddwd; 15 weight layers (239 MiB) kept L3-resident with prefetcht0 for those layers and prefetchnta for the rest; 2 MiB hugepages; CCX-balanced threads around an offline core. Hardware: x86 AVX2 CPU; runs on Zen 5 as-is (topology tuning is 7642-specific); no GPU relevance. Caveats: single self-reported run, decode only, 0.6B model where llama.cpp is overhead-bound rather than DRAM-bound, so margins do not transfer to 27B/A3B decode.\n   Value: (a) near-tie precision rule — int8 vs Q15 activation quantization against greedy parity, for C19 argmax-tie fix, SPEC-FILTER-TIES and the CPU Q8 activation path; (b) L3-residency prefetch split for CPU drafters/MTP heads small enough to fit 9655 L3 (DRAFT-HEAD-SVD-CPU, Q38FN draft head); (c) CCX pinning, spin barriers and THP weight load for INF-45 / INF-70; (d) agent-authored kernels gated only by exact golden refs, as AutoKernel keep-gate and cost/turn reference.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: per-32-block Q15 activation packing and vpmaddwd dot widened to AVX-512 / VNNI; 4-row matvec blocking; prefetcht0/prefetchnta residency split against 9655 per-CCD L3; CCX/NPS4 thread placement; whether any gain survives at 27B where decode is DRAM-bound.)",
      "disposition": "planned",
      "plan_ref": "P7",
      "reason": "The sampler fixture starts after logit formation; a Q8 activation rounding error can change which logit is largest before sampling."
    },
    {
      "seq": 9,
      "stage": 1,
      "verbatim": "8. X post by @superalesha (Alexey Fateev), 2026-11-26, announcing item 7: same numbers as the repo (adds Neon peak 188.93 tok/s at 32 threads). Secondary source; use it only for provenance and community reception (about 62K impressions, 1.7K likes at read time). Do not ingest separately from item 7.\n\nINFERENCE SYSTEMS / HARNESS / POST-TRAINING",
      "disposition": "context-only",
      "plan_ref": null,
      "reason": "Scope instruction preserved. The announcement is provenance only; expansion was preauthorized, and handoff filing requires plan review."
    },
    {
      "seq": 10,
      "stage": 1,
      "verbatim": "9. SWGDN (arXiv 2611.33257): replaces short convolutions in Delta-Rule linear attention with sliding-window attention for local q/k/v mixing, no change to state update or chunkwise algorithm; applied to GDN2 and KDA, outperforms baselines (no numbers in abstract). Hardware-agnostic; requires training.\n   Value: forward-look on Qwen3.x GDN kernel changes (GDN-FUSED-VARIANT, CPU-KDA-EXP-CENSUS, KPF-STATE-COPY-CENSUS).",
      "disposition": "planned",
      "plan_ref": "M10",
      "reason": "Existing GDN fusion and KDA exponential work measure recurrence or state movement; substituting a trained mixer changes the model."
    },
    {
      "seq": 11,
      "stage": 1,
      "verbatim": "10. SPLICE (arXiv 2611.34777): local option targets spliced into failed current-policy trajectories for all-fail GRPO groups; +2.8 to +9.8 pp over GRPO across SWE-bench Verified and BrowseComp-Plus; +10.8 pp graduation rate on initially failed SWE tasks. Hardware-agnostic, training-side.\n   Value: post-training lane for local Qwen agent RL; MemRL reward shaping on all-fail episodes.",
      "disposition": "planned",
      "plan_ref": "P11",
      "reason": "A terminal MemRL failure score does not encode the first repairable action, options or a validated continuation."
    },
    {
      "seq": 12,
      "stage": 1,
      "verbatim": "11. HoMe (arXiv 2611.34624): evaluation-driven harness optimization for memory systems with session-level memory versioning, candidate gating, smoke tests, adaptive sampling and memory reuse; on LongMemEval-S and BEAM, six formal candidate evaluations found harnesses beating the strong ReMe harness with far fewer query-time tokens; code in agentscope-ai/ReMe. Hardware-agnostic.\n   Value: AutoPilot harness search, P-MEMEVAL-1 / M-12 BEAM 128K instrument, eval rigor (smoke-gated candidates).",
      "disposition": "planned",
      "plan_ref": "P12",
      "reason": "M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases."
    },
    {
      "seq": 13,
      "stage": 1,
      "verbatim": "12. CoordRoute (arXiv 2611.34161): budget-coordinated routing (relative demand prediction, lookahead solver, budget-aware runtime correction); +18.72% total satisfaction over the strongest existing router on Azure Conversation and BurstGPT traces. Hardware-agnostic.\n   Value: orchestrator routing/escalation under a fixed local compute budget (routing-program).",
      "disposition": "planned",
      "plan_ref": "P13",
      "reason": "Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost."
    },
    {
      "seq": 14,
      "stage": 1,
      "verbatim": "13. When Skills Fail to Compose (arXiv 2611.34398): independently learned soft-prompt skills compose at most 7.6% in one call vs 88.2-100% over two calls; on two Qwen bases, swapping partner blocks drops median composition accuracy 98.0%/95.3% -> 12.7%/0.5%. Hardware-agnostic.\n   Value: skill-bank design and EV-SKILL-NULL-REPLAY follow-ups; compatibility/retention gates for skill libraries.",
      "disposition": "planned",
      "plan_ref": "P14",
      "reason": "Local skills are text/tool bundles, whereas the source trains continuous prompts. The existing null replay records single-task effects."
    },
    {
      "seq": 15,
      "stage": 1,
      "verbatim": "14. MGMem (arXiv 2611.33174): deterministic discriminative-parser memory with incidence graph and raw-episode return, no generative indexing calls; beats matched-protocol baselines on LoCoMo, competitive on LongMemEval-S. CPU-friendly.\n   Value: orchestrator post-compaction session-history search, deterministic memory for MemRL and context-and-token-economy.",
      "disposition": "planned",
      "plan_ref": "P15",
      "reason": "Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory writes."
    },
    {
      "seq": 16,
      "stage": 1,
      "verbatim": "15. FlyingStart (arXiv 2611.34492): closed-form linear warm start for recurrent-depth fixed-point decoding, <5% of one loop; on Huginn-0125, 14-19% fewer decoding layers at matched accuracy, +16-18% batched throughput in two serving engines, +10-14% on top of self-speculative decoding. Hardware-agnostic.\n   Value: only if looped/recurrent-depth models enter the stack; self-speculation interplay (speculative-decoding).",
      "disposition": "planned",
      "plan_ref": "M16",
      "reason": "The existing DFlash2 target/drafter interface has no interchangeable fixed-point latent; layer savings depend on stability of a shared recurrent block."
    },
    {
      "seq": 17,
      "stage": 1,
      "verbatim": "Automatically accept every recommended deep dive and literature expansion for up to four Stage 2 sweeps.",
      "disposition": "context-only",
      "plan_ref": null,
      "reason": "Scope instruction preserved. The announcement is provenance only; expansion was preauthorized, and handoff filing requires plan review."
    }
  ],
  "outcome_reviews": {
    "RI-NOV27-1": {
      "required_outcome": "Identify sampled HIP instructions in existing binaries",
      "review_status": "preserved",
      "review_basis": "The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-kernel-authoring.md",
          "task_id": "PC-HOSTTRAP-COVERAGE",
          "task_text": "- [ ] **PC-HOSTTRAP-COVERAGE** [non-inference] Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check.",
          "acceptance": "Use the original ELFs, code objects, store manifests and build IDs. Keep one other binary for validation. Record symbol+offset, source line or unmappable reason for each sampled PC. Only trial host-trap if unresolved hotspots remain and firmware/driver enumerate the capability; collect separate baseline runtime and check perturbation, skid and sample loss."
        }
      ]
    },
    "RI-NOV27-2": {
      "required_outcome": "Decide whether decode scheduling limits IQ4 or EXL3",
      "review_status": "preserved",
      "review_basis": "Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof.",
      "task_refs": [
        {
          "owner": "handoffs/active/quantization-and-low-bit.md",
          "task_id": "IQ4-PERM-PLACEMENT",
          "task_text": "- [ ] **IQ4-PERM-PLACEMENT** [non-inference] Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3.",
          "acceptance": "Freeze the full nibble, sign and scale oracle and retained kernel traces; compare existing permute helper with alternative decode-to-issue placement at equal layout. On wave64 price VGPR occupancy, 64 KB LDS per CU, memory stalls, MFMA issue and spills. Reject a numerical mismatch; require improvement on later actual shapes before a served trial. CPU analogue is lane-local byte shuffles plus widened signed dot, measured separately."
        }
      ]
    },
    "RI-NOV27-3": {
      "required_outcome": "Identify underfilled F32 router GEMMs",
      "review_status": "preserved",
      "review_basis": "The existing Q8 atomic-flush determinism task addresses a different type and reduction path.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-kernel-authoring.md",
          "task_id": "F32-ROUTER-SPLITK-CENSUS",
          "task_text": "- [ ] **F32-ROUTER-SPLITK-CENSUS** [non-inference] Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise.",
          "acceptance": "Reuse retained A3B router traces at decode and prefill. Baseline is the resolved Tensile solution; keep a later request window. Record M/N/K, workgroups, slices and all partial-buffer writes. The upstream half-CU test bounds unsplit tile count, not slices. Stop if even eliminating targeted time would miss the owner’s served gate. Test CPU splitting only for underoccupied cores after NPS4-local partitioning."
        }
      ]
    },
    "RI-NOV27-4": {
      "required_outcome": "Decide whether to specialize a HIP V-load bound",
      "review_status": "preserved",
      "review_basis": "A CUDA stack frame reduction gives no proof of scratch traffic on the active gfx90a specialization. RF7 changes wave-level streaming.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-kernel-authoring.md",
          "task_id": "FATTN-PRIVATE-SEGMENT",
          "task_text": "- [ ] **FATTN-PRIVATE-SEGMENT** [non-inference] Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles.",
          "acceptance": "Compare deployed GPU symbols on a train and holdout context length, retaining code-object hash, VGPR/scratch metadata, ISA and dispatch hits. A nonzero private segment alone cannot prove traffic. Stop on absent path or equal material scratch traffic; specialize and time only if affected. Check both padded and unpadded tails."
        }
      ]
    },
    "RI-NOV27-5": {
      "required_outcome": "Determine eligible F32 verify work",
      "review_status": "preserved",
      "review_basis": "Completed Q8 w8 and queued fused small-K width 1–4 work do not count F32 rows by M and verify width.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-loop.md",
          "task_id": "VERIFY-F32-GEMV-CENSUS",
          "task_text": "- [ ] **VERIFY-F32-GEMV-CENSUS** [non-inference] Classify retained verify calls by input type, rows, K, verify columns and selected kernel. Bound F32 time that a weight-sharing GEMV could recover against served dispatch. Stop at zero eligible share or an immaterial upper bound.",
          "acceptance": "Freeze verify traces from both dense and MoE, train/test split by request. Report all rows and F32-eligible rows by width, M and K. Preserve actual dispatch including width one and wide M; compare incumbent GEMV versus tiled GEMM for surviving bins. On CPU compare blocked GEMV to existing GEMM with NUMA-local weights; never import Adreno subgroups or the numeric threshold."
        }
      ]
    },
    "RI-NOV27-6": {
      "required_outcome": "Price adaptive expert caching versus a static pool",
      "review_status": "preserved",
      "review_basis": "The current static-pool replay already prices cold routes; logical layer IDs can misrepresent cache pressure and miss overlap.",
      "task_refs": [
        {
          "owner": "handoffs/active/cpu-decode-roofline-program.md",
          "task_id": "MOE-PHYSICAL-BANK-REPLAY",
          "task_text": "- [ ] **MOE-PHYSICAL-BANK-REPLAY** [non-inference] Extend the existing static-pool replay with physical tensor identity, capacity-matched LRU and measured NUMA-local CPU-miss versus PCIe upload costs. Compare static pool, LRU, CPU-share and unpatched cache under identical route order.",
          "acceptance": "Bind each expert tensor to a physical bank, backend and epoch. Reserve model, KV and scratch before pricing the pool; hold back later routes. Output every hit/miss, unique bytes, PCIe overlap, CPU affinity, and uncovered bank. Stop if experts fit, identities are all distinct for dedup, or cold-route/transfer costs erase the margin; report these cases separately."
        }
      ]
    },
    "RI-NOV27-7": {
      "required_outcome": "Preserve greedy parity near logit ties",
      "review_status": "preserved",
      "review_basis": "The sampler fixture starts after logit formation; a Q8 activation rounding error can change which logit is largest before sampling.",
      "task_refs": [
        {
          "owner": "handoffs/active/cpu-decode-roofline-program.md",
          "task_id": "Q8-Q15-TIE-REPLAY",
          "task_text": "- [ ] **Q8-Q15-TIE-REPLAY** [non-inference] Replay near-tie and ordinary rows with incumbent Q8, per-block signed Q15 and FP32 reference. Save top-two gaps, argmax flips, accumulators and conversion cost; verify AVX-512 signed-word dot semantics and overflow against a scalar oracle.",
          "acceptance": "Freeze pre-activation rows plus weight bytes and golden logits with deliberate near and wide gaps; compare Q8, Q15 and reference on unseen prompts and thread counts. Persist token, gap, logits, packing time, and signed-pair overflow cases. Reject a candidate on a new held-out greedy mismatch or if conversion cost erases its measured benefit."
        }
      ]
    },
    "RI-NOV27-8": {
      "required_outcome": "Decide whether small CPU heads merit a resident/streamed split",
      "review_status": "preserved",
      "review_basis": "The completed NTA-only seed failed its speed gate; it did not partition a reusable working set by CCD capacity.",
      "task_refs": [
        {
          "owner": "handoffs/active/cpu-decode-roofline-program.md",
          "task_id": "DRAFTER-CCD-RESIDENCY",
          "task_text": "- [ ] **DRAFTER-CCD-RESIDENCY** [non-inference] Compare resident and streaming layer subsets for a draft head after accounting for per-CCD weight duplication, KV and scratch. Isolate four-row blocking, worker pinning, barriers and THP; include a 27B bandwidth-bound negative control.",
          "acceptance": "Size working sets per CCD after KV and scratch. Baselines include current champion, NTA-only and unmodified OS page policy. Record realized page size and NUMA placement plus per-thread work; separate prefill, single-stream and drafts at a later prompt/width. Stop if LLC misses or matched-throughput intervals fail to improve, or if a negative control regresses."
        }
      ]
    },
    "RI-NOV27-9": {
      "required_outcome": "Evaluate generated kernels under the existing promotion procedure",
      "review_status": "closed-with-basis",
      "review_basis": "Golden greedy prompts exercise too few shapes for kernel promotion. Wall time, turns and cost are author-reported and provide planning context.",
      "task_refs": []
    },
    "RI-NOV27-10": {
      "required_outcome": "Recognize a future local-mixer architecture",
      "review_status": "closed-with-basis",
      "review_basis": "Existing GDN fusion and KDA exponential work measure recurrence or state movement; substituting a trained mixer changes the model.",
      "task_refs": []
    },
    "RI-NOV27-11": {
      "required_outcome": "Decide whether failed groups can support local repairs",
      "review_status": "preserved",
      "review_basis": "A terminal MemRL failure score does not encode the first repairable action, options or a validated continuation.",
      "task_refs": [
        {
          "owner": "handoffs/active/harness-program.md",
          "task_id": "FAIL-GROUP-SPLICE-AUDIT",
          "task_text": "- [ ] **FAIL-GROUP-SPLICE-AUDIT** [non-inference] Audit retained all-fail trajectory groups for reproducible environment state, a bounded repair point and verifiable continuation. Count recoverable groups before proposing any training or changing MemRL rewards.",
          "acceptance": "Freeze same-policy group membership, exact task environment, tools, rollouts and rewards; hold out tasks. Record all failures including infra faults, repairability, local success and continuation success separately. Advance a training proposal only if at least one held-out repair verifies end to end and usable counts support the planned comparison; never relabel terminal failures from local success alone."
        }
      ]
    },
    "RI-NOV27-12": {
      "required_outcome": "Select a cheaper memory harness without leaking evaluation data",
      "review_status": "preserved",
      "review_basis": "M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases.",
      "task_refs": [
        {
          "owner": "handoffs/active/memory-program.md",
          "task_id": "MEM-HARNESS-CANDIDATE-REPLAY",
          "task_text": "- [ ] **MEM-HARNESS-CANDIDATE-REPLAY** [non-inference] Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons.",
          "acceptance": "Pin M-12 judge, prompts, receipts, dataset and explicit independent BEAM partition. Hold out conversations from search, filter post-hoc intersections visibly and score all scheduled cases. Compare incumbent, smoke-gated and fully evaluated candidate on quality, total construction cost, query tokens, and unchanged-memory reuse. Reject leaked cases or unverified archive hashes. Preserve ratified abstention handling."
        }
      ]
    },
    "RI-NOV27-13": {
      "required_outcome": "Test whether routing improves under a fixed local capacity budget",
      "review_status": "preserved",
      "review_basis": "Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate service cost.",
      "task_refs": [
        {
          "owner": "handoffs/active/routing-program.md",
          "task_id": "ROUTE-BUDGET-LOOKAHEAD",
          "task_text": "- [ ] **ROUTE-BUDGET-LOOKAHEAD** [non-inference] Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals.",
          "acceptance": "Replay ordered arrival sets without future leakage. Compare incumbent, percentile pacing with same demand scores, and full lookahead under identical occupancy and budget; use a later trace with bursts. Report per-request route, satisfaction definition, time, starvation and budget breaches. Advance only on budget compliance and positive held-out utility over pacing after solver cost."
        }
      ]
    },
    "RI-NOV27-14": {
      "required_outcome": "Detect skill interactions hidden by single-skill uplift",
      "review_status": "preserved",
      "review_basis": "Local skills are text/tool bundles, whereas the source trains continuous prompts. The existing null replay records single-task effects.",
      "task_refs": [
        {
          "owner": "handoffs/active/eval-tower-program.md",
          "task_id": "SKILL-PAIR-COMPAT-REPLAY",
          "task_text": "- [ ] **SKILL-PAIR-COMPAT-REPLAY** [non-inference] Measure held-out pairs with component-only, combined single-call, explicit two-call and partner-shuffled arms; record step retention, token and tool cost by model. Keep soft-prefix findings separate from text-skill outcomes.",
          "acceptance": "Freeze model, executor, evidence and cost ceiling. Compare both orders, shuffled partners, constituent controls and explicit two-step intermediate on held-out tasks. Record stale skills, tool failures, invalid completions, abstentions and additional compute. Reopen admission policy only for effects surviving shuffled labels and cost-matched controls."
        }
      ]
    },
    "RI-NOV27-15": {
      "required_outcome": "Test deterministic retrieval into post-compaction history",
      "review_status": "preserved",
      "review_basis": "Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory writes.",
      "task_refs": [
        {
          "owner": "handoffs/active/memory-program.md",
          "task_id": "MEM-RAW-EPISODE-ARM",
          "task_text": "- [ ] **MEM-RAW-EPISODE-ARM** [non-inference] Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence.",
          "acceptance": "Use identical conversations, raw turns, parser version and token cap. Compare lexical/hybrid, exact mentions, released first-mention heuristic and dependency/alias gated edges. Record raw episode IDs, all-gold recall, time/order failures, build and query wall time measured externally. Promote only if held-out evidence recall or answer quality improves without exceeding the cost ceiling."
        }
      ]
    },
    "RI-NOV27-16": {
      "required_outcome": "Reduce loops per decoded token on recurrent-depth models",
      "review_status": "closed-with-basis",
      "review_basis": "The existing DFlash2 target/drafter interface has no interchangeable fixed-point latent; layer savings depend on stability of a shared recurrent block.",
      "task_refs": []
    }
  },
  "proposed_tasks": [
    {
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "task_text": "- [ ] **PC-HOSTTRAP-COVERAGE** [non-inference] Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check."
    },
    {
      "owner": "handoffs/active/quantization-and-low-bit.md",
      "task_text": "- [ ] **IQ4-PERM-PLACEMENT** [non-inference] Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3."
    },
    {
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "task_text": "- [ ] **F32-ROUTER-SPLITK-CENSUS** [non-inference] Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise."
    },
    {
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "task_text": "- [ ] **FATTN-PRIVATE-SEGMENT** [non-inference] Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles."
    },
    {
      "owner": "handoffs/active/autokernel-loop.md",
      "task_text": "- [ ] **VERIFY-F32-GEMV-CENSUS** [non-inference] Classify retained verify calls by input type, rows, K, verify columns and selected kernel. Bound F32 time that a weight-sharing GEMV could recover against served dispatch. Stop at zero eligible share or an immaterial upper bound."
    },
    {
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "task_text": "- [ ] **MOE-PHYSICAL-BANK-REPLAY** [non-inference] Extend the existing static-pool replay with physical tensor identity, capacity-matched LRU and measured NUMA-local CPU-miss versus PCIe upload costs. Compare static pool, LRU, CPU-share and unpatched cache under identical route order."
    },
    {
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "task_text": "- [ ] **Q8-Q15-TIE-REPLAY** [non-inference] Replay near-tie and ordinary rows with incumbent Q8, per-block signed Q15 and FP32 reference. Save top-two gaps, argmax flips, accumulators and conversion cost; verify AVX-512 signed-word dot semantics and overflow against a scalar oracle."
    },
    {
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "task_text": "- [ ] **DRAFTER-CCD-RESIDENCY** [non-inference] Compare resident and streaming layer subsets for a draft head after accounting for per-CCD weight duplication, KV and scratch. Isolate four-row blocking, worker pinning, barriers and THP; include a 27B bandwidth-bound negative control."
    },
    {
      "owner": "handoffs/active/harness-program.md",
      "task_text": "- [ ] **FAIL-GROUP-SPLICE-AUDIT** [non-inference] Audit retained all-fail trajectory groups for reproducible environment state, a bounded repair point and verifiable continuation. Count recoverable groups before proposing any training or changing MemRL rewards."
    },
    {
      "owner": "handoffs/active/memory-program.md",
      "task_text": "- [ ] **MEM-HARNESS-CANDIDATE-REPLAY** [non-inference] Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons."
    },
    {
      "owner": "handoffs/active/routing-program.md",
      "task_text": "- [ ] **ROUTE-BUDGET-LOOKAHEAD** [non-inference] Replay timestamped arrivals against the incumbent and a demand-ranked lookahead allocator with online budget correction. Charge actual CPU/GPU service occupancy, misses, late completions and escalation; prevent use of future realized arrivals."
    },
    {
      "owner": "handoffs/active/eval-tower-program.md",
      "task_text": "- [ ] **SKILL-PAIR-COMPAT-REPLAY** [non-inference] Measure held-out pairs with component-only, combined single-call, explicit two-call and partner-shuffled arms; record step retention, token and tool cost by model. Keep soft-prefix findings separate from text-skill outcomes."
    },
    {
      "owner": "handoffs/active/memory-program.md",
      "task_text": "- [ ] **MEM-RAW-EPISODE-ARM** [non-inference] Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence."
    }
  ]
}
```

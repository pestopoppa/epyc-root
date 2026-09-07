# MoE per-token routing tap and locality measurement (INF-72)

**Status**: stub
**Created**: 2026-09-07 (research intake, operator-approved plan)
**Categories**: moe, gpu_acceleration, benchmark_methodology
**Related**: [mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md) (INF-34) · [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) (INF-70) · [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) (SC66)

## Objective

Stand up a per-token MoE routing tap on our own fleet and measure expert-selection locality directly —
SRP (per-expert rank/mask) and SCH (top-k schedule) plus an EOR/IR_t reuse rider — so that any
offload, expert-cache or residency argument on this box rests on a measured local number instead of a
foreign paper's. The instrument is the deliverable; no throughput claim is licensed by it.

## Research Context

| Intake | Status | What it contributes |
|---|---|---|
| `intake-1328` | dive-verified | The from-scratch tap build, **superseded** by the port in 1336; the shared-expert census that makes the Qwen fleet an open question rather than a favourable one |
| `intake-1336` | dive-verified | `llama-moe-trace` as a portable instrument, the four required adjustments, and the strided-read hazard |
| `intake-1338` | dive-verified | What the tap must emit, the SCH oracle's real size, and the chance baselines that make a locality number interpretable |

## Tasks

- [ ] **RT-1 — The port, not a build.** COMPUTE-GATED — FILE ONLY. Port `llama-moe-trace`
  (MIT, `github.com/Shriniwas410/cacheable-by-design` @ `03366ef1`, files
  `llama-moe-trace/moe-trace.cpp` + `routing-lab/06_convert_gguf_trace.py`) onto an
  `llama.cpp-experimental` branch off **current production**. Four verified adjustments:
  1. **int16, not int8** — our 256/512-expert fleet overflows int8.
  2. `-b 512` with the existing per-chunk `llama_memory_clear` yields the `[samples, 512, top_k]`
     geometry by reshape.
  3. **SRP additionally needs `ffn_moe_argsort`** (cb-named at `src/llama-graph.cpp:1985`); SCH needs
     only what the tap emits.
  4. v9 covers `qwen35moe` and `qwen3next` but **not** `qwen4exp` / `glm5next`.

  "Zero-surgery" means zero-surgery-to-the-model; an experimental branch is still required.
  `intake-1336#00`, superseding the from-scratch build in `intake-1328#record`.

- [ ] **RT-2 — What it emits, plus the EOR rider and the chance baselines.** COMPUTE-GATED — FILE ONLY.
  Per MoE layer: top-k expert-index tensor `[samples, tokens, top_k]` (SCH) plus per-expert rank/mask
  (SRP); m ∈ {4, 16, 64, 256}; 512-token samples × 2,048 per domain sufficed. SRP needs no simulator;
  SCH needs the incremental oracle (**201 lines**, `41_sch_calc.py:12-212` — *not* the "20-line"
  figure, already corrected in-index). **Rider**: emit **EOR/IR_t** alongside —
  `|E_t ∩ E_{t-1}| / K` over the same top-k tensor SRP already consumes, free once the tap exists.
  Chance baselines, mandatory so a number is interpretable: **8/256 = 3.13%** (qwen35moe),
  **10/512 = 1.95%** (qwen4exp), against DeepSeek-V2-Lite's 9.38% where ReMoE's baseline was already
  2.91× chance. `intake-1338#01`.

- [ ] **RT-3 — The stride hazard: BLOCKING, read before writing any tap code.** COMPUTE-GATED —
  FILE ONLY. Tell-tale signature: *every expert appearing exactly k times, sub-chance reuse*. Cause:
  a flat read of a strided router tensor. Fix: row-by-row `ggml_backend_tensor_get` at offset
  `i * t->nb[1]`. Anchored in our own tree at `ggml/src/ggml.c:5373` and `src/llama-graph.cpp:1987`.
  This is a measurement-integrity item — the broken read manufactures a **plausible-looking negative**,
  exactly the failure "vacuous verification" and "rule out the test method first" exist to catch.
  `intake-1336#00`.

- [ ] **RT-4 — Scope-out, written down so the numbers are never re-cited.** COMPUTE-GATED — FILE ONLY.
  The bandwidth-wall and PMS-ceiling findings (Sections 3, 5) do **not** transfer: every systems number
  is an 8 GB VRAM card behind a 2.4 GB/s SSD, and Limitations (v) says the speed projections are
  modelled, not deployed (`intake-1336#05`). A good SCH does **not** license a throughput claim.

## Open Questions

- Does `qwen4exp` / `glm5next` coverage need its own graph-side work, or does the v9 gap close on its
  own once the port lands on a newer experimental base? (RT-1 adjustment 4.)
- Which domains and how many 512-token samples are needed on *our* fleet before an SRP/SCH number is
  stable — the 2,048-per-domain figure is the source's, not ours.
- Does EOR/IR_t clear its chance baseline on either fleet? A result at or below 3.13% / 1.95% is a
  negative and must be reported as one.

## Notes

- **Compute-gated — FILE ONLY. Never run.** Nothing in this stub authorises a build, a benchmark, or a
  model load; the tasks are recorded so the instrument can be built when compute is granted.
- Production kernels are FROZEN: all work happens on an `llama.cpp-experimental` branch cut from the
  current production tip, never on the production tree.
- The mi210 roadmap (INF-34) carries a cross-link line to this file, not a second index row — one
  handoff, one owner.
- Wire the tap's output into the belief kernel on the **write** side when RT-2 is built (SC66); a
  claim tuple invented on read cannot recover warrant the run never captured.

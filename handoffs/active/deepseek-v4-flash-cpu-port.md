# DeepSeek-V4-Flash CPU Port — Experimental Branch

**Status**: stub — port AUTHORIZED 2026-05-28 (experimental branch isolation, no merge until both gates pass)
**Created**: 2026-05-28
**Priority**: P2
**Effort**: High (multi-thousand-line arch addition, mirroring/exceeding the DSv3.2 DSA work)
**Source**: intake-637 ([antirez/deepseek-v4-gguf](https://huggingface.co/antirez/deepseek-v4-gguf)) + deep-dive 2026-05-28

## Objective

Port the `deepseek4` architecture (CSA + HCA + indexer + compressor + manifold-constrained Hyper-Connections) to our ik_llama.cpp production tree on an experimental branch (`feature/deepseek4-port`), validate Q4 (153 GiB) and Q2 (80 GiB) GGUFs against canonical CPU stack on EPYC 9655 NPS4, and merge into production only after both a quality gate (logprob parity vs reference) and a throughput gate (≥ comparable to current top-tier roles at the same active-param budget) pass.

## Why now

User decision 2026-05-28: "no point deferring pure coding work. Should we maybe build it in an experimental branch first? And only merge it after testing?" Authorized. Experimental-branch isolation mitigates the high-risk-of-direct-cherrypick concern (antirez's fork is "not extensively tested", targets MacBook 128 GB, has no NUMA / AVX-512BW validation).

## Background

DeepSeek-V4-Flash is a 284B / 13B-active MoE with a fundamentally new architecture, not a DSv3.2 derivative:
- **Attention**: hybrid Compressed-Sparse Attention (CSA, local-window KV compression m≈4 then sparse top-k selection) + Hierarchical Compressed Attention (HCA, aggressive m'≈128 block compression + dense attention over compressed). Two parallel branches.
- **New blocks**: indexer, compressor, manifold-constrained Hyper-Connections (Birkhoff polytope residuals, spectral-norm ≤ 1). All kept at F16/F32 in the quant — decision-making layers, not quantized.
- **Efficiency claims**: 27% of V3.2 FLOPs and 10% of V3.2 KV at 1M ctx.
- **MTP head**: 3.6 GiB optional sidecar, mirrors gemma4 / DSv3.2 MTP-as-drafter pattern. Uses ds4-specific tensor naming → separate integration after base.
- **License**: MIT (passes `feedback_opensource_only`).

Current state of upstream support (2026-05-28):
- `grep -ri deepseek4 /mnt/raid0/llm/llama.cpp /mnt/raid0/llm/ik_llama.cpp` → zero hits. Neither tree supports the arch.
- Upstream tracker: ggml-org/llama.cpp issue #22319 (model request, open) + discussion #22376 (WIP, 4+ community forks). No merged PR.
- Reference engine `antirez/ds4` (DwarfStar4) is from-scratch C (not llama.cpp-based). Backends: Metal primary, CUDA secondary, "CPU is reference/debug, non-production." Best ds4 numbers: M3 Max 21.5 t/s Q2; DGX Spark 13.75 t/s. **No EPYC / x86-AVX-512 production path published.**
- Best community llama.cpp CPU number: 6.5 t/s on ThinkPad-P16 128 GB (dual-channel DDR5). Our NPS4 12-channel-per-node should be substantially faster but no reference exists.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-637 | antirez/deepseek-v4-gguf (Q2/Q4/MTP) | high | worth_investigating (post-port escalates to new_opportunity) |
| intake-506 | DeepSeek-V3.2 + DSA (arxiv:2512.02556) | high | already_integrated (DSA, not V4 — different arch) |
| intake-508 | DeepSeek-TUI Rust client | medium | worth_investigating (targets V4 API) |
| intake-600 | Engram Conditional Memory / CXL | low | confirmed V4 does NOT use Engram |

## Merge Gates (DEFINED BEFORE PHASE 1)

These gates are concrete and not subject to renegotiation mid-port. If a gate fails at the end of its phase, the branch stays out of production until a new run passes — no waiver flow.

### Quality gate (end of Phase 3)

- **Reference engine**: antirez/ds4 reference implementation running on the same Q4 GGUF (Metal on a Mac, since ds4 has no production CPU path). If ds4 cannot run on accessible hardware for the operator, fall back to the antirez/llama.cpp-deepseek-v4-flash fork running on a Mac with `--temp 0 --seed 1`.
- **Prompt set**: 20 prompts spanning 5 categories × 4 each:
  - 4 short factual ("Who wrote Hamlet?", etc.)
  - 4 short code completion ("Write a Python function that sorts a list of integers in ascending order.")
  - 4 long-form reasoning (3-5 sentence math word problems)
  - 4 instruction-following (formatting + multi-step tool-shape outputs without actual tool calls)
  - 4 long-context recall (1K-token preface + question about a specific detail)
- **Procedure**: for each prompt, run both the reference engine and the experimental-branch build at `--temp 0 --seed 1 --top-k 1`. Capture token-level logprobs of the GREEDY output sequence for the first 64 generated tokens.
- **Tolerance**: for each prompt, compute mean absolute log-prob difference across the 64 tokens. Per-prompt MAD must be **≤ 0.05 nats** (~5% logprob deviation). Aggregate: **≥ 18 of 20 prompts** must pass per-prompt tolerance.
- **Token-1 exact-match**: for at least **15 of 20 prompts**, the experimental and reference engines must emit the same first token under greedy decoding. (This catches tokenizer or BOS/EOS handling drift before deeper logprob divergence.)
- **Failure modes documented**: if any of the 20 prompts triggers an assert, segfault, or NaN — gate FAILS automatically regardless of other prompt scores.

### Throughput gate (end of Phase 3)

- **Workload**: same 512-token decode prompt used by `cpu-decode-flops-roofline-audit.md` ("Write a Python function that computes the n-th Fibonacci number iteratively. Then explain it briefly.") at `--temp 0 --seed 42`.
- **Stack**: canonical NPS4 (`taskset -c 0-95 -t 96 -fa 1`, `numactl --interleave=all`, OMP env stack per `feedback_omp_env_stack_required`, `KMP_BLOCKTIME=10`, `GGML_NUMA_WEIGHTS=1`, `--mlock`).
- **Floor — solo Q4**: **≥ 18 t/s** sustained decode (lower bound calibrated from V4-Flash's 13B active params vs gemma4-26B-A4B's 4B active sustaining 76.5 t/s solo; conservative ~ proportional inverse with the param ratio at the same Q4 quant gives ~18-23 t/s expected).
- **Floor — solo Q2**: **≥ 35 t/s** sustained decode (Q2 is ~2× the BW efficiency of Q4 at the same per-token compute; this is opportunistic — Q2 quality may not be production-acceptable but the throughput floor is documented).
- **Acceptance interaction with `feedback_speed_verify_via_llama_bench`**: the agent does NOT autonomously run the throughput gate; the user runs it manually and reports the t/s number. The gate floor above is the criterion against which the user-reported number is judged.
- **Quality gate must pass first**: throughput numbers from a quality-failing build are not meaningful. If the quality gate fails, the throughput run is skipped until quality is fixed.

### Merge criteria (end of Phase 6)

Merge `feature/deepseek4-port` → ik_llama production tree requires ALL of:
1. Quality gate passes (≥ 18/20 prompts within 0.05-nat MAD; ≥ 15/20 token-1 exact-match; no assert/segfault/NaN).
2. Throughput gate passes (Q4 ≥ 18 t/s solo on canonical stack).
3. Chat-template shim works against the orchestrator chat-completions path on at least 3 of the 4 instruction-following prompts from the quality set.
4. MTP sidecar EITHER integrates with acceptance ≥ 0.4 OR is parked with a stub PR noting "second integration, not blocking base merge."
5. No regression on existing models — re-run a smoke test on gemma4-26B-A4B + Qwen3.6-frontdoor with the merged binary, both must still launch and produce coherent output (no quality bench, just liveness).

If any of (1)-(3) or (5) fails, the branch stays in experimental and remediation goes into a follow-on phase log appended to this handoff.

## Phased Port Plan

### Phase 1 — Branch creation & cherry-pick (Day 1)

1. Create `feature/deepseek4-port` branch off the ik_llama.cpp production tree's current head (NOT off antirez's fork directly).
2. Cherry-pick from `antirez/llama.cpp-deepseek-v4-flash` the deepseek4 arch additions: tokenizer, model loader, tensor naming, indexer/compressor/HC ops.
3. **Do NOT bring in any non-arch changes** from the antirez fork (per `feedback_minimum_imports`).
4. Build verification under canonical stack: AOCC + KMP_BLOCKTIME=10 + GGML_NUMA_WEIGHTS=1.

### Phase 2 — Q2 smoke test (Day 2)

5. Download Q2 GGUF (80.8 GiB) to `/mnt/raid0/llm/models/`. Verify storage budget (Q2 + Q4 + MTP + working copy ≈ 250 GB).
6. Single-thread load-and-decode smoke test (no concurrent inference per `feedback_no_concurrent_inference`).
7. Compare a small set of logprobs against ds4 reference vectors (if antirez publishes them; otherwise against the antirez/llama.cpp-deepseek-v4-flash MacBook run for parity sanity-check).

### Phase 3 — Q4 quality gate (Days 3-4)

8. Download Q4 GGUF (153.3 GiB).
9. Single-instance Q4 inference with canonical NPS4 stack: `taskset -c 0-95 -t 96 -fa 1`, `numactl --interleave=all`, OMP env stack (`feedback_omp_env_stack_required`).
10. **Run the quality gate** per the §Merge Gates definitions above (20-prompt set × per-prompt MAD ≤ 0.05 nats × token-1 exact-match).
11. **Run the throughput gate** per the §Merge Gates definitions above (canonical 512-token decode, Q4 floor ≥ 18 t/s, Q2 floor ≥ 35 t/s) — operator-executed per `feedback_speed_verify_via_llama_bench`.

### Phase 4 — Chat template + orchestrator integration (Day 5)

12. V4-Flash GGUF lacks a built-in Jinja chat template (per allthings.how). Write a template shim against the upstream Python encoder.
13. Wire into orchestrator_stack.py as a registry candidate (NOT as a production role) — load on demand.
14. Validate against ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES path.

### Phase 5 — MTP sidecar integration (Days 6-7, optional)

15. The 3.6 GiB MTP sidecar uses ds4-specific tensor naming. Adapter layer to load it as a drafter for V4 base, mirroring the gemma4 MTP path.
16. Acceptance-rate measurement on representative workload.

### Phase 6 — Merge decision

17. Both gates passed AND chat-template works AND MTP optional integration either works or is parkable → merge `feature/deepseek4-port` into production tree.
18. If upstream ggml-org/llama.cpp merges a deepseek4 PR first → roll back our branch in favor of upstream PR for review and merge.

## Open Questions

- Should MTP integration be in-scope for this branch, or a separate follow-on after base merge? (Per §Merge Gates criterion 4, either path is acceptable — but the decision affects whether Phase 5 is required or optional.)
- Once merged, what production role does V4-Flash take? (Top-tier general, or specialized?) Resolve based on the throughput-gate t/s number vs gemma4-26B-A4B's 76.5 t/s.
- Is the `github.com/antirez/ds4` KV-cache-on-disk reference engine worth a separate intake / experiment? (User said earlier: "to be ingested separately if user requests.")
- ~~Quality-gate tolerance and throughput-gate floor are now DEFINED above; not open.~~

## Cross-references

- **Primary intake**: intake-637 (antirez/deepseek-v4-gguf)
- **Sibling handoff**: `llama-cpp-dsa-contribution.md` — V4 is tracked as adjacent upstream arch work (different arch, parallel effort)
- **MTP integration template**: `moe-spec-cpu-spec-dec-integration.md` and `project_gemma4_mtp_launch_recipe`
- **Quant recipe reference**: APEX paper / intake (asymmetric routed-vs-shared expert precision)
- **Upstream watch**: ggml-org/llama.cpp#22319 + #22376
- **antirez fork**: github.com/antirez/llama.cpp-deepseek-v4-flash
- **ds4 reference engine**: github.com/antirez/ds4 (Metal/CUDA/ROCm; CPU = non-production reference)

## Reporting Instructions

After each phase, append a Phase Report subsection here documenting:
- Build / smoke-test / gate outcomes
- Throughput numbers (when explicitly user-approved)
- Any deviations from antirez's fork that we had to make for NPS4 / AVX-512BW
- Decision to proceed to next phase or pause

Update `progress/YYYY-MM/YYYY-MM-DD.md` at every phase transition.

## Notes

User authorized this port on 2026-05-28 with the explicit framing: "build in an experimental branch first, only merge after testing." Experimental-branch isolation is the safety harness; the antirez fork is acknowledged-untested for our NUMA / AVX-512BW environment.

Per `feedback_no_concurrent_inference`: no benchmark execution without explicit per-run user approval. The phases above are scoped so that loading and smoke-testing can proceed, but throughput/quality benchmark runs are deferred to user invocation.

Per `feedback_no_wholesale_git_add_shared_files`: when staging cherry-picked changes, verify `git diff --cached` to ensure only our targeted hunks land — `/mnt/raid0/llm/ik_llama.cpp` is a shared clone and other agents may have in-progress work.

# MLSys 2026 FlashInfer contest loops vs our AutoKernel loop — what, if anything, they do better

**Date**: 2026-09-15 · **Produced by**: research-intake (Stage 2 + 2b dives, operator-approved Stage-3 plan)
**Question (operator, verbatim)**: *"My main prerogative with this research-intake session is distilling what (if
anything) this repo is doing better than our autokernel loop and learn from it."*
**Entries**: intake-1425#record (Dogacel/auto-gpu-kernel), intake-1426#record (Houmao, arXiv 2608.14560), intake-1427#record (LLM-CUDA /
LoongFlow), intake-1428#record (MSInfer GDN, arXiv 2607.16831), intake-1429#record (Dogacel AI-assisted DSA kernels, not dived),
intake-1430#record (Kachua GDN), intake-1431#record (organizer writeup archive), intake-1432#record (UW SyFI full-agent), intake-1433#record (HAN
Lab KDA), intake-1434#record (arXiv 2406.06484 + FLA reference). Every entry except 1429 is `dive-verified` or
`dive-overturned`; cite them as `intake-NNNN#record`.
**Owning tasks**: `handoffs/active/autokernel-rebuild-program.md` § R24; RVP-C6-26 in
`rocm-verify-profile-backend.md`; G16a/G16b in `log-linear-gated-deltanet-readiness.md`; G15a in
`mi210-big-model-and-acceleration-roadmap.md`; the chunked-GDN P1b sub-bullet in `autokernel-unified-surface-program.md`.

## The answer in one paragraph

On measurement, evaluator integrity, outcome logging and critic discipline, none of the contest loops beats ours. Each
one is weaker on at least one of those axes: sub-noise keeps, single unrepeated evaluations, cached reference
denominators, prompt-only anti-gaming, or an actor that owns its own log. They are **better in two ways**. First, they
expose that **several of our own hardened checks exist but are not wired into the live loop**: the anti-memoization
bench, the no-fallback dispatch proof, a read-only critic, and a real determinism gate. The contest harnesses show those
exact hazards being exploited in practice. Second, **our loop has no reflex for a stall**: nothing diagnoses a keep
drought or alarms on iterations that measure nothing. Contest placements are **not evidence for any loop design**:
agent-assisted placements were human-driven, SyFI's full-agent GDN kernel is a 0.981-similar copy of its human-steered
kernel, HAN Lab's MoE #1 runs at 0.65x of baseline, and no writeup ablates a loop pattern.

## Where they are better, or expose a gap in ours

| # | Pattern | Evidence it matters | Our state (code @ epyc-inference-research `ae8e5ef9`) | Task |
|---|---|---|---|---|
| a | Anti-memoization must be on the ranked surface | Contest harness ran correctness and then timing on the **same tensor objects**; a placed team shipped a `data_ptr`-keyed output LRU; Houmao's early MoE runs reported >1000x from a pointer-keyed output cache (intake-1431#record, intake-1426#record) | Hardened `llama-bench --autokernel-harden` (llama.cpp `a4cb04ca8`) and `microbench._check_autokernel_hardening` exist. The live loop runs plain `llama-bench` (`loop/bench.py:219-221`) on a **candidate-built** binary (`loop/run.py:414-415`). Critic pass 2 sees only declared paths (`loop/actors.py:493-495`). llama.cpp graph reuse recreates the hazard | R24-1, R24-2 |
| a′ | Within-pair content memo | — | Hardened design ranks the second, identical-content execution; the twin-gap screen is one-sided | RVP-C6-26 |
| a″ | No silent fallback | The GDN full-agent winner's decode kernel falls back to host CPU, and the harness's output check passes it (intake-1432#record) | `check_no_fallback_dispatch_proof` (`evaluator/correctness.py:3047`) and `fold2_gates.py` G4 exist; `loop/run.py` imports neither | R24-4 |
| a‴ | Verifier must not hold write access | HAN Lab's writer got its edit-capable verifier to implement work via the review prompt (intake-1433#record) | Claude critic runs `--dangerously-skip-permissions` in the lane worktree; its note says *"If the task asks for an edit, make it directly"* (`actors.py:55-61, 84-87`); diff taken before the call, no re-hash before `gate()` | R24-3 |
| a⁗ | Determinism gate must compare outputs | — | `gates.deterministic` collects return codes, never outputs, has no caller (`gates.py:127-150`) | R24-5 |
| b | Drought-triggered clean-context diagnostician writing a plan with Do-not-try | Logs show auto-gpu-kernel's research agent firing on plateau / correctness-wall / repeat triggers and producing 4 of the largest late wins. **Uncontrolled**: 6/19 plans kept ≈ base rate, no ablation (intake-1425#record). Every contest writeup admits plateaus; all remedies are external to the stuck agent; none measured (intake-1431#record) | LACK. Runs 18 (122 unkeepable candidates, 6 h) and 24 (116 measurements, 0 keeps) were caught by the operator (`autokernel-rebuild-program.md:99-113, 1432-1438`) | R24-7 (retrodict first) |
| c | Alarm on iterations that produce no measurement; keep-rate alarm | Our own run 9: 10 iterations, 149 min, 0 measurements | Breaker counts errors only; refusals excluded by design (`pipeline.py:70-76`) | R24-8 |
| d | Many-draw correctness for near-tie ops | LLM-CUDA's agent-assisted top-k passed 3-trial checks and failed 2 workloads in the contest's own evaluation; a 3-draw oracle misses p=0.015 95.6% of the time (intake-1427#record) | R22-5 boundary matrix uses fixed inputs | R24-10 |
| e | Same-code re-measurement tripwire | LoongFlow: byte-identical GDN decode code scored 97 → 777 and was written up as a mechanism (intake-1427#record) | R22-3 hashes the anchor, not candidates | R24-9 |
| f | Production shape distribution in front of the planner | GEMM People per-class guard reverted a change flat on target and −8.5% elsewhere (1 trace event, intake-1431#record); our ne11=1 / n_embd=1536 keeps never fired in production | PARTIAL (R23-5/10/13/43) | R24-11 |
| g | Prompt anti-caching clause + cold/warm cache disclosure | Houmao's rules (intake-1426#record) | Absent from `actors.py:407-422` and `program.md` | R24-6 |

## Where ours is stronger or equivalent (nothing to import)

- **Stateless actors.** Ours pass `--no-session-persistence` (`actors.py:85`). The auto-gpu-kernel winning runs were a
  single compacting session, not fresh context (intake-1425#record). SyFI resumes one session per phase, and LoongFlow's
  summarizer turned noise into mechanism stories (intake-1432#record, intake-1427#record).
- **Paired alternating A/B against a bootstrap A/A floor** (`autokernel-rebuild-program.md:147-158`). The contest loops
  kept sub-noise changes, including accept rules with zero margin and single evaluations, and SyFI cached its reference
  denominator across venues.
- **Evaluator immutability, gate-move history, and the post-promotion A/A guard.** kbench's integrity check is only a
  guard against the harness changing mid-run, and its anti-gaming is prompt-only (intake-1425#record).
- **Loop-owned outcome logging** with mechanism and sample vector. The repos need recovery turns because the actor owns
  its log.
- **Two-pass critic with budgets, from a different provider.** HAN Lab's reviewer is an LLM auditing an actor that owns
  its measurement.
- **Tiering.** Our stack is test-backend-ops → bench screen → serving keep gate, and our iteration is build-dominated
  (75.7%), so measurement tiering matters less for us.

## Declined: unproven or worse

These have no controlled evidence, and some are contradicted:
- evolutionary population DB (agents bypassed it; KernelEvolve credits human hinting);
- synthesizer merging unmeasured partials (recreates our attribution defect);
- stall-triggered web researcher (authors say under-searching persisted);
- session resume;
- LESSONS pruning (zero archived instances);
- log-only recovery turn;
- prompt stall rule (subsumed by R24-7);
- SPIN model checking;
- cleanup gates;
- KernelWiki analogue (R21-5 owns intake → inbox);
- LLM-judged stagnation STOP;
- plateau model switching;
- Modal sharding;
- sectioned profiler MCP;
- two-phase language ladder;
- BitLesson memory;
- "CUDA/CuTeDSL worse for agents" and "DeepSeek-V3 needs more iterations" (no artifacts);
- any NVIDIA/B200 kernel technique (`agentic-rocm-kernel-authoring.md:5-7`).

## Corrections the dives made to the sources' own claims

- **auto-gpu-kernel**
  - The contest runs used neither kopt nor fresh sessions.
  - The report swaps trace counts (sparse attention has 23, indexer 128).
  - 34.93x is the organizer's arithmetic mean of per-workload ratios over 2 kernels on bare-metal B200. It is not
    reproducible from the archive.
  - "workload-inspector unlocked the scoreless path" is not supported: a research-agent plan did, keyed on the checker
    being set-based.
  - The sandbox-escape anecdote was a shim through an allow-listed proxy.
  - The shipped kernel uses NUM_SPLITS=16, not 8.
- **Houmao (2608.14560)**
  - Not a winner. The 1.68x "top score" it beats is the #2 writeup's self-report.
  - The >1000x hack was in early MoE runs, not TopK.
  - It lists three biases, not four.
  - Its date is arXiv's own record.
- **MSInfer (2607.16831)**
  - Its "scalar prefill" claim is contradicted by its own tagged artifact.
  - The scoring baseline is FlashInfer, not a simple reference.
- **UW SyFI**
  - The full-agent prefill is a near-copy of its agent-assisted kernel.
  - The Codex backend is not in the shipped code.
  - The staged reference was annotated by humans.
- **HAN Lab**
  - MoE #1 is 0.65x of the FlashInfer baseline.
  - Its ablation is one cumulative run, and the Humanize step shows no mean-latency gain.
- **Kachua / chunked GDN**
  - Split-WY's core (inverse, W, U once per chunk, parallel across chunks) is paper Listing 8 and FLA practice. Only the
    QKᵀ hoist, GVA gram sharing, the Neumann inverse and 1/G are Kachua's.
  - Our `719a8529d` per-block recompute is a documented platform deviation from the reference.
  - `GGML_CUDA_DELTANET_MIN_BLOCKS_PER_SM` is compile-time.
  - The H=32 G16 cases do not fire the chunked kernel on MI210.
  - The 2e-7 T=2048 miss was PR #26001 + patch, not #24561.

## Do not cite these entries for

- A contest placement as proof that a loop design works (1425, 1427, 1431, 1432, 1433).
- Any writeup speedup as an official or comparable score. They are Modal, self-reported and mutually inconsistent
  (1431).
- 34.93x, 1101x or 1.71x as kernel-quality signals (1425, 1426).
- "fresh context", "workload-inspector" or "tiered benchmarking" as the cause of auto-gpu-kernel's result (1425).
- The paper or FLA as precedent that the chunked GDN form meets our unrelaxed 1e-7 NMSE gate. FLA tolerates about
  NMSE 2.5e-5 (1434).

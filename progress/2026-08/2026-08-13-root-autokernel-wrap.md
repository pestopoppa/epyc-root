# 2026-08-13 — AutoKernel discovery-first and r43 checkpoint

## Outcome

AutoKernel now has a ratified high-throughput discovery plane, three valid live candidate-only
screening results across CPU prefill, CPU decode, and MI210 prefill, and a repaired path back into
strict matched confirmation. Discovery results are top-K nominations only: none is banked,
promotable, archive-eligible, or a production performance claim.

The strict prefill chain ran again under fresh r43 identities. The r42 intervention spent no
empirical compute: it stopped before fingerprint, claim, build, T0, or throughput on a duplicate
evaluator-closure path. Research `b93af168` repaired the closure construction without weakening its
ambiguity guard. Both r43 arms then dry-ran clean. The intervention reached terminal `DECIDED/KEEP`
with T0 PASS, 15/15 positive deltas, median **+28.860648%**, worst delta **+984.48 tokens/s**, drift
`15.0356% ≤ 18.4968%`, production PASS, and both resources released. The control terminally refused
before claim/T0/throughput after strict preflight observed only 7/96 cores at nominal frequency under
load and simultaneously treated caller-disabled load measurement as unmeasured contention. It is not
archive evidence, so r43 does not form the required matched pair.

## Ratified discovery authority

Operator ratification `autokernel-discovery-first-20260813` appended
`P-AK-SEARCH-1-A2` to Annex K and the corresponding Annex B cross-reference. Root source commit
`678240b9cdeb` was promoted to `main` through `c8223a760a5c730e345ba8ae3760f582fac9036c`.

- Ratified receipt SHA-256:
  `65571da3d7b89792fccb827824473051ee492a30670c9b4a34aad40a09e2e669`.
- Annex K SHA-256:
  `16bf2d373cfa6a85bcdf21ffdbaf9fd6090fe5a3030f31ed622cbe605b116e43`.
- Annex B SHA-256:
  `a7e27f50c6690d588a6c66d575e1d5b7453f3e78835d47a4ddda35ba15f8e4e2`.
- Discovery creates one exact-frame three-anchor bank and runs exactly three candidate-only samples.
  Ordinary service, agent, build, filesystem, scheduler, and host-load activity is recorded noise;
  only competing model inference overlapping held compute blocks the screen.
- Strict paired confirmation remains mandatory for banking, champion lineage, readiness, archive
  authority, performance claims, and release.

## Live screening evidence

| Surface | Result | Physical work | Evidence |
|---|---:|---|---|
| CPU IQK prefill, pp512 | **+31.247%** median nomination | b4 bank reused; 3 candidate / 0 anchor invocations | `ak-iqk-screen-20260813-s7/result.json`, SHA `4350648c79132544…` |
| CPU IQK decode, tg128 | **+7.939%** median nomination | b1 bank reused; 3 candidate / 0 anchor invocations | `ak-iqk-decode-screen-20260813-s1/result.json`, SHA `d7dbdf24e2074738…` |
| MI210, MMQ MFMA ON→OFF, pp512 | **+26.5965%** median nomination | 3 anchor + 3 candidate invocations | `ak-gpu-mmq-mfma-screen-20260813-s2/result.json`, SHA `9508396b5793568b…` |

The prefill bank file is SHA-256
`1e9c32d9bd1544daf7dea0892f666ddad64a0b07dd06e9277bdea2cd4b589068`; the distinct-regime
decode bank is `8dcd02d3e9fd4e4a989f3631e9bc41e96ba45b43809ff41d8eaf510d15c7d1ed`.
Both CPU screens bind `GGML_IQK=0→1` as the sole intended factor, record a non-competing inference
witness, preserve production identity, and release the full-host CPU claim. The GPU result binds
`GGML_HIP_MMQ_MFMA=ON→OFF` as the sole build factor; every candidate invocation recorded its owned
KFD PID and non-zero VRAM during the benchmark window. Its internal content digest is
`a4d2e058acf32d82020072d04c3e873d6c3aff952656e75a364b5835023be973`.

## Strict-chain defects closed

| Commit | Closure |
|---|---|
| Research `b93af168` | Canonicalizes exact overlap between direct and nested evaluator closures while continuing to reject lexical aliases and duplicate/ambiguous inputs. |
| Research `084f1ee6` | Defines a decode block as the median of five fresh alternating pairs, addressing r2's short-process bimodality without reusing one process or relaxing gates. |
| Research `9c0c907c` | Discloses the repaired decode frame and its 2,600 fresh-invocation calibration cost before execution. |
| Research `f1b97aa3` / `45996850` | Adds the bounded six-call MI210 screen and seals its full build identities. |

Decode calibration r2 remains honest terminal non-authority: its completed A/A pool had permutation
p95 `0.148013`, while neutral `|effect|` p95 was `0.154446` (phi `0.133735`), so it rejected before
ranked controls. The fresh aggregation frame is a new calibration attempt; it does not reinterpret r2.

## Files and state advanced

| Repository | Files/state | Change |
|---|---|---|
| `epyc-root` | `measurement/protocols/kernel-research.md`, `measurement/protocols/bench-cpu.md`, ratification receipts | Discovery-first policy ratified and promoted before this wrap-up. |
| `epyc-inference-research` | AutoKernel campaign, live-control, and GPU-screen implementations | r42 closure defect, decode aggregation, cost disclosure, and GPU runner fixed on research `main`. |
| `epyc-root` | `handoffs/active/autokernel-research-loop.md`, `handoffs/active/inference-research-index.md`, this progress shard | Current evidence, checkbox state, and next action made durable by this wrap-up. |
| `epyc-root` | `scripts/vidya/adapters/README.md`, `handoffs/active/vidya-belief-substrate-program.md` | Registered GPU-screen schemas and filed SC37 before the successor producer runs; s2 remains pre-hook and is never back-filled. |

No production kernel tree, running inference process, service, or release state was modified by this
documentation checkpoint.

## Remaining execution chain

1. Reconcile strict confirmation's load/boost preflight mode without weakening its gates; if the
   frequency finding persists, re-establish a compliant host state. Preserve r43 and mint a fresh
   matched prefill pair under new immutable identities.
2. Execute the fresh five-pair-aggregated decode calibration and governed decode matched holdout.
3. Generate and execute the heldout-bound prefill pair.
4. Materialize the real completed-proposal archive (AK-WM-2a).
5. Run the observe-only AutoKernel/AP least-commitment evaluation (AK-WM-2b).
6. Continue cheap GPU candidate-only screening from the MMQ-MFMA-off nomination; reserve strict
   paired GPU confirmation for candidates that survive broader surfaces.
7. Complete SC37's prospective write/read hook for `gpu_screening_baseline.v2` and
   `gpu_candidate_only_screen.v2` before the successor GPU screen; do not retrofit s2.

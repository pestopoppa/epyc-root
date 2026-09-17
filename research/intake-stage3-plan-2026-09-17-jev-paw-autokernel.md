# Stage-3 Action Plan — Jev typed decisions / PAW compiled specialists / agentic kernel porting

**Session**: `jev-sageattn-20260917` · **Created**: 2026-09-17 · **Mode**: plan — needs operator approval before any handoff/stub/index write
**Lane**: worktree `/mnt/raid0/llm/worktrees/intake-jev-sageattn-20260917` (branch `intake/jev-sageattn-20260917`, off `origin/main` `6f346ea3`)
**Index state**: intake-1460…1492 appended (33 entries); validator `exit 0` (1,488 entries); head bytes preserved on every write
**Dive results**: 16 dived (13 verified, 2 overturned, 2 thread-only), 12 Stage-2b ingested, 0 dive-surfaced items outstanding

## 1. Plan-completeness gates

| Gate | Status |
|---|---|
| Every Stage-1 preliminary actionable promoted or explicitly declined | PASS — §6 |
| Every dive-ledger row appears as a filed item or explicit decline | PASS — §6 |
| Every steering-ledger row appears as a filed item or explicit decline | PASS — steering seq 1/2 → §3/§4/§5 |
| No plan text quotes a number/metric/mechanism still `stage1-unverified` | PASS — intake-1461/1480 are cited ONLY as excluded/declined; all task citations are dive-verified (1462–1479, 1481–1492) or standard-tooling facts |
| Every dive-surfaced source ingested-and-dived or operator-declined | PASS — 12 ingested (1481–1492), declines recorded in bearing entries' `dive_corrections` |
| Target handoffs checked for frozen/pointer status | PASS — no frozen/pointer handoff is named as an owner; `harness-selection-and-integration.md` is active (HS-4 decided, Phase 0 not started); `canonical-judge-suite-revamp.md`, `eval-benchmark-cost-reduction.md`, `episodic-memory-integrity.md`, `tool-use-eval-contract.md`, `routing-intelligence.md`, `learned-routing-controller.md`, `autokernel-research-loop.md`, `agentic-rocm-kernel-authoring.md`, `vidya-belief-substrate-program.md` all active |

## 2. Steering ledger →

| seq | Operator direction | Plan item |
|---|---|---|
| 1 | PAW relevant to agent loops + GUI separating deterministic flow from fuzzy LLM work | §4 stubs B/C |
| 1 | Jev extremely relevant to the orchestrator (exact tool use + speed), fast routing, episodic-memory writing | §3 stub A + §5 fold-ins |
| 1 | Agentic Kernel Porting obviously relevant to autokernel | §5 autokernel tasks |
| 2 | "do all except recommended declines. Then proceed to stage 3" | Stage-2b wave completed; declines recorded |

## 3. New stub A — `handoffs/active/typed-decision-plane.md` (owner: routing-and-optimization-index → **RTG-56**)

Full proposed content:

```markdown
# Typed Decision Plane — one-pass typed decisions over the local stack

**Status**: stub
**Created**: 2026-09-17 (via research intake, operator-approved {plan date})
**Categories**: routing_intelligence, cost_aware_routing, inference_serving, tool_implementation, agent_architecture
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Evidence**: intake-1472, intake-1473, intake-1474, intake-1485, intake-1486, intake-1487, intake-1490 (all dive-verified); intake-1476 (application survey, anecdote-grade)

## Objective

Give the orchestrator a first-class one-pass decision call: declared typed questions (choice / score / noul)
in, per-question values + probabilities + a caller-computed confidence statistic out, with no autoregressive
JSON generation, and with locally measured behaviour before any gate uses it. Operator steering 2026-09-17:
"extremely relevant for the orchestrator where json schemas are passed and tool use is important ... guarantees
exact tool use and also a pretty large overall speed boost ... may also be relevant for fast routing and
episodic memory writing."

## Research Context

| Intake ID | What it settles | Use |
|-----------|-----------------|-----|
| intake-1472 | Public typed-decision spec (primitives, one-call parallel questions, confidence is an undisclosed statistic) | Contract for the local implementation |
| intake-1473 | MIT reference implementation over generic LLM APIs (per-request schema, corrective retries, normalization, local confidence stats, injection guard) | Pattern set to transplant onto llama.cpp |
| intake-1474 | Independent evidence that candidate-softmax confidence is NOT calibrated (65% of wrong 7B fields >0.90) and the real local speedup is 3.4–7.9x, not 40–200x | Hard constraint: no gate before local calibration |
| intake-1485 | Paired Jev-vs-fast-LLM run: measured p50 176 ms vs 215 ms; fixture agreement scene-dependent | External datapoint; baseline is fast, so no multiplier transfer |
| intake-1486 | Independent rerank reproduction: Jev tied with Cohere Pro (nDCG 0.692 vs 0.691, CI crosses 0); Jev Choice order-sensitive 24.7% | Guarantees are not quality; order effects must be measured |
| intake-1487 | Fully local pinned one-pass implementation: 5.21x vs same-model JSON on a 3090; 20.03 decisions/s parallel reuse; reuse drifts 5–6/777 argmaxes | Local mechanism + acceptance envelope |
| intake-1490 | Independent audit of jevlike: shipped shuffled-context control was defective; informed-vs-blind lift ~25 pts after correcting | Verification discipline for our own measurements |

## Tasks

- [ ] **TD-1 — Implement the local typed-decision call path over the frozen v9 server.** Per-request JSON-Schema
  generation from declared questions (choice/score/noul), one chat completion with `response_format
  json_schema`, client-side decode + validation with corrective retry, expected-value scoring, local confidence
  statistics (fixed formulas + one documented alternative), and a per-call diagnostics record. Cite intake-1472
  (contract) and intake-1473 (pattern set). Acceptance: a fixture of ≥20 questions returns schema-valid typed
  answers with per-question probabilities; malformed-output retry path exercised.
- [ ] **TD-1a — Native candidate-scoring fast path (the actual speed lever).** Implement the local one-pass mechanism:
  enum-constrained single-token readout with per-question probabilities (`response_format json_schema` enum +
  `n_probs`/`completion_probabilities`) over a shared prompt prefix with prompt-cache reuse, batching multiple
  questions into as few requests as the server allows. Benchmark it against TD-1's JSON-schema generation path —
  wall time, output tokens, argmax agreement, and cache-reuse drift (intake-1487 measures 5-6/777 argmax flips
  under BF16 reuse; intake-1474 measures 3.4-7.9x for the pattern vs same-model naive JSON). Acceptance: our own
  speedup and drift numbers; TD-5 remains gated on TD-2 calibration regardless of the speed result.
- [ ] **TD-2 — Measure cross-question contamination and confidence calibration before any gate.** On a frozen
  EPYC decision set: (a) question-order permutation on one batched call vs single-question calls, report
  top-answer flips; (b) ECE / reliability of the local confidence statistic per model and schema. Acceptance:
  contamination and calibration numbers recorded in a measurement artifact; TD-5 is BLOCKED until this lands.
- [ ] **TD-3 — Measure speculative fan-out locally.** Fixed state, N batched questions in one call vs N
  singleton calls, cache-warm; report serial-sum and concurrent wall-clock plus token cost. Acceptance: our own
  numbers replace any vendor batching multiplier in internal documents.
- [ ] **TD-4 — Closed-set tool-argument selection pilot.** Map tool arguments to closed sets (Literal → Choice,
  list[Literal] → multi-choice, bool → Noul) with per-argument confidence; compare against the current
  free-form tool-call path on exact-match argument correctness and wall time. Citation: intake-1472 pattern,
  intake-1473 adapter. Coordinate with `tool-use-eval-contract.md` (TU-TD-1 there).
- [ ] **TD-5 — One shadow integration after TD-2 passes.** Wire the typed-decision call into exactly one live
  surface as a shadow arm (routing classifier or judge, chosen by the owning handoff), gated on TD-2's
  calibration result. Acceptance: shadow agreement + calibration reported; no enforcement without operator approval.

## Open Questions

- Which confidence statistic, if any, survives local calibration well enough to gate an action?
- Does the frozen v9 server's json_schema→GBNF converter accept the nested probability-map schemas the adapter generates?
- Does question-order contamination on our stack reproduce the 24.7% seen in intake-1486, or is it smaller at our batch sizes?

## Notes

All numbers above are from dive-verified entries; none may be promoted to a deployment measurement until TD-2/TD-3
produce our own. This stub follows the 2026-09-17 operator steering; the vendor's own documentation states confidence
is an undisclosed statistic and calibration is group-level only.
```

## 4. New stub B — `handoffs/active/paw-compiled-specialists.md` (owner: inference-research-index → **INF-76**)

```markdown
# PAW Compiled Specialists — compile-once fuzzy functions on the local stack

**Status**: stub
**Created**: 2026-09-17 (via research intake, operator-approved {plan date})
**Categories**: training_distillation, local_inference, inference_serving, tool_implementation
**Parent index**: [inference-research-index.md](inference-research-index.md)
**Evidence**: intake-811 (parent paper + 2026-07-11 blocker), intake-1466/1467 (docs + SDK), intake-1477 (Compile by Training), intake-1478/1483 (Standard/Compact compiler weights), intake-1479 (FuzzyBench eval data), intake-1481 (self-hosted compile server, scope-overturned), intake-1482 (independent eval), intake-1484 (.paw corpus)
**Operator steering (2026-09-17)**: PAW links are "relevant for constructing agent loops and making our current agent loops more robust"; the operator likes a GUI separating deterministic flow from fuzzy LLM work (separate stub, UFH-09).

## Objective

Turn the re-opened Program-as-Weights line into a bounded, licensed-aware decision: can we compile recurring
fuzzy subtasks (tool-output classification, log filtering, JSON repair, routing predicates) into tiny local
specialists that run on the frozen llama.cpp stack, and does the compile-once economics survive on CPU/MI210?
The intake-811 re-open trigger is literally met on artifact availability (weights + FuzzyBench eval data, both
predating the 2026-07-11 blocker); licenses and a self-hosted compile path are the remaining gates.

## Research Context

| Intake ID | What it settles |
|-----------|-----------------|
| intake-1478/1483 | Standard (Qwen3-0.6B) / Compact (GPT-2 124M) compiler weights public and ungated; NO artifact license |
| intake-1479 | `fuzzy_bench_verified` downloadable (43,128 + 7,550 rows, spec/input/output); no train split; no license |
| intake-1481 | Unofficial MIT self-hosted compile server exists and works for the default Qwen3 compiler; Compact GPT-2 SDK-compat claim overturned; no ROCm proof |
| intake-1482 | Independent eval: standard 94 / finetuned 97 / compact 85 on 100 adversarial cases (one task, n=100, author labels); semantic abstention 98.9% on decided cases; logit-confidence thresholding fails |
| intake-1484 | 7,226 public .paw programs (heterogeneous bundle hygiene, no license) |
| intake-1477 | Self-hosted training-based recipe (teacher synthesis → LoRA on Qwen3-0.6B); no paper memory numbers |

## Tasks

- [ ] **PAW-1 — Artifact-license decision package (OPERATOR).** Weights (1478/1483), FuzzyBench data (1479) and the .paw corpus (1484) declare no license; the compiler is a Qwen3-4B-Instruct-2507 finetune (upstream Apache-2.0) and the SDK/server are MIT. Options: (a) internal research use only, no redistribution; (b) request a license from the authors; (c) clean-room reimplementation from the published method. No prototype may ship distributions until this closes; internal evaluation on 1479 is option (a)-scoped.
- [ ] **PAW-2 — Self-hosted compile spike on the target host.** Run intake-1481's MIT server with pinned weights (1478), mapper and SDK; prove one end-to-end compile producing a modern GGUF-ZIP .paw, then one local call. Measure compile wall time, peak RAM, disk. Document the Compact GPT-2 canonicalization caveat (1481) and whether CPU-only execution is workable before MI210.
- [ ] **PAW-3 — Evaluate compiled programs on FuzzyBench (internal, unlicensed).** Build the eval manifest for `fuzzy_bench_verified` (1479) and record standard-vs-compact capability on our own task slices; replicate the abstention experiment (semantic 3-class vs thresholding) per intake-1482. WIRE THE VIDYA ADAPTER BEFORE THE FIRST RUN (VB-TDP-1).
- [ ] **PAW-4 — Amend the intake-811 blocker record.** Replace the stale 2026-07-11 "compiler is CLOSED / no concrete download" text with the verified availability + license + no-official-self-hosted-compile status (index correction; see §7).
- [ ] **PAW-5 — Agent-loop candidates list.** Identify ≤3 recurring fuzzy subtasks in the current agent loops (candidates: tool-output classification, transcript/log filtering, JSON repair, routing predicates) and file each as a compile-once candidate with a direct-model baseline. Do not start compiling until PAW-1 and PAW-2 land.

## Open Questions

- Does the compile-once economics survive on this host without an accelerator (compile time vs adapter lifetime)?
- Does intake-1482's abstention finding transfer to our task slices, or is it task-specific?
- Is the Qwen3-0.6B interpreter (594 MB Q6_K) fast enough per call for always-on loops versus our current cheap-first models?

## Notes

Re-open trigger status: MET on availability, NOT met on capability (no official self-hosted compile) and BLOCKED on
licenses. The 10M-example FuzzyBench training set remains unavailable; 1477's recipe is the closest self-hosted path.
```

## 5. New stub C — `handoffs/active/fuzzy-workflow-authoring-gui.md` (owner: user-facing-harness-index → **UFH-09**)

```markdown
# Fuzzy Workflow Authoring GUI — deterministic flow, fuzzy steps, one canvas

**Status**: stub (design idea from operator steering, 2026-09-17)
**Created**: 2026-09-17 (via research intake, operator-approved {plan date})
**Categories**: agent_architecture, tool_implementation, harness_optimization
**Parent index**: [user-facing-harness-index.md](user-facing-harness-index.md)
**Evidence**: intake-1460 (operator essay: typed decisions), intake-1477 §6.1 (compiled functions make fuzzy decisions while ordinary code handles exact operations), intake-1481/1482 (compile-once specialists as the fuzzy nodes)

## Objective

Design a process-authoring GUI where the user draws a flow whose deterministic steps are ordinary code and
whose fuzzy steps are typed decision calls or compiled specialists. Operator steering: "a GUI for designing
high level processes that clearly separate deterministic flow from fuzzy LLM work in a meaningful way."
The GUI is an authoring surface; the runtime is the typed-decision plane (RTG-56) and/or compiled programs (INF-76).

## Tasks

- [ ] **FW-1 — Requirement sketch + one worked example.** Take a real recurring workflow (candidate: eval-triage
  or tool-output routing), express it as a two-layer graph (deterministic nodes: code; fuzzy nodes: typed
  questions / compiled programs), and record what the GUI must expose. Acceptance: the example runs end-to-end
  in a notebook or CLI harness with the GUI mocked.
- [ ] **FW-2 — Decide the build posture against HS-4.** HS-4 settled on a thin shell (OpenCode) with Hermes
  features inside the orchestrator; state whether this GUI is (a) an orchestrator page, (b) a harness plugin,
  or (c) deferred. Operator decision required before implementation.
- [ ] **FW-3 — Survey prior art (≤1 day).** Flow-authoring UIs with LLM nodes (e.g. Dify/LangFlow-class) and
  compiled-function authoring (PAW playground) — what to borrow, what to refuse. No ingestion; a short note.

## Open Questions

- Does the GUI edit a declarative document (typed JSON/YAML graph) that the orchestrator executes, or generate code?
- How are fuzzy-node contracts versioned when the underlying model or compiled program changes?
```

## 6. Edits to existing handoffs (paste-ready task lines; owner may renumber only if the ID collides)

| # | Target | Proposed task line(s) | Evidence |
|---|---|---|---|
| D1 | `routing-intelligence.md` (RTG-30), section `## Research Intake Update — 2026-09-17 (Jev typed-decision cluster)` | `- [ ] **RI-11 — Typed-decision fast path for closed-set routing questions.** Once TD-2 calibration lands, evaluate a Choice-style candidate-logit call as the routing classifier fast path; never gate on uncalibrated confidence; report agreement + calibration + wall time vs the current classifier.` | 1472, 1474, 1487 |
| D2 | `learned-routing-controller.md` (RTG-15), appended tasks | `- [ ] **LRC-TD-1 — Candidate-scoring arm for the learned controller.** Compare the per-call label-set pattern (option-as-query head or native token logits) against the current classifier on the recorded routing corpus; treat as unadopted until TD-2 reports calibration.` | 1462, 1487 |
| D3 | `canonical-judge-suite-revamp.md` (EVL-08), section `## Tasks` | `- [ ] **CJ-13 — Two-cheap-readers redundancy arm (typed judge + local LLM judge).** Report pairwise agreement and human-disagreement cost per intake-1475/1486 methodology; label "agreement is not accuracy"; no adoption decision (CJ-GATE remains operator's).` plus `- [ ] **CJ-14 — Adopt the dinostomp measurement discipline for new judge instruments:** hashed manifests/run records, a blind probe as lower bound, pre-registered per-item distributions (intake-1490).` | 1475, 1486, 1490 |
| D4 | `eval-benchmark-cost-reduction.md` (EVL-11), appended tasks | `- [ ] **ECR-TD-1 — Cost-order anchor + same-rubric local comparison.** Record the verified per-million-checks cost order (Jev ~$160; DeepSeek Flash $260; Gemini $1,600; Astra $18,700; Fable 5.1 $33,000) as an external estimate, then run one same-rubric local cheap-judge arm before assuming a typed judge is the cheapest adequate reader (intake-1475).` and `- [ ] **ECR-TD-2 — External dashboard citations must be snapshot-captured** (payload hash or rendered snapshot) before entering a claim tuple; the 3–329 s baseline citation is not derivable from its cited live page (intake-1492).` | 1475, 1492 |
| D5 | `episodic-memory-integrity.md` (EVL-10), appended task | `- [ ] **M-17 — Typed decision records + confidence gate design (blocked on TD-2).** Specify a memory-write record carrying per-question probabilities and a caller-computed confidence statistic; the gate threshold must come from TD-2 calibration, not from candidate softmax.` | 1472, 1473, 1474 |
| D6 | `tool-use-eval-contract.md` (EVL-46), appended task | `- [ ] **TU-TD-1 — Closed-set tool-argument arm.** Add an evaluation arm where tool arguments are selected from closed sets with per-argument confidence (Literal→Choice, list[Literal]→multi-choice, bool→Noul), scored on exact-match argument correctness vs the free-form path.` | 1472, 1473 |
| D7 | `autokernel-research-loop.md` (INF-06), new section `## Research Intake Update — 2026-09-17 (verifiable porting loop; operator directive)` | `- [ ] **AK-PORT-1 — Correctness-gated optimization order in the loop spec.** Make the loop's canonical order explicit: compile → reference comparison (cosine similarity / PSNR for low-precision variants; max-abs/MSE otherwise) → only then timing; a fast wrong variant is discarded.` `- [ ] **AK-PORT-2 — Ordered test ladder with failure localization** (host wiring → kernel-side units → reference comparison), so a high-rung failure is not diagnosed at the wrong layer.` `- [ ] **AK-PORT-3 — Assembly-summary artifact** (PTX/SASS/CUBIN dump summary: register spills, instruction mix, vectorization, occupancy) attached to every retained variant; assembly-driven refinement.` These three are generic engineering practices (standard CUDA tooling docs), filed under operator directive steering seq 2; **no port speed/latency number is filed** (intake-1461/1480 are stage1-unverified and their port claims are non-citable). | Steering seq 2; standard tooling |
| D8 | `agentic-rocm-kernel-authoring.md` (INF-03), evidence-table rider (no checkbox) | `**Cross-ISA port evidence (2026-09-17)**: a HIP-native SageAttention port exists but targets RDNA2/RDNA3 (gfx103x/gfx110x, WMMA/V_DOT — absent on CDNA2/MFMA); cite only as existence proof for cross-ISA porting, never as gfx90a evidence (intake-1491). CuTeDSL remains NVIDIA/CUTLASS-only and must not be imported (standing rule).` | 1491 |
| D9 | `vidya-belief-substrate-program.md`, appended task | `- [ ] **VB-TDP-1 — Wire the write side before the first typed-decision / PAW measurement run.** One self-hashed ClaimTuple per TD-2/TD-3/PAW-3 run at the source table (scripts/vidya/adapters/README.md row + this task); a tuple invented on read cannot gate a decision.` | AGENTS.md belief-kernel rule |
| D10 | `master-handoff-index.md`, operator-decision queue | `PAW artifact-licensing posture (intake-1478/1479/1484: weights + dataset + .paw corpus carry no license; SDK/server MIT). Open since 2026-09-17. Blocks PAW-2 distribution, not PAW-2 internal spike.` | 1478, 1479, 1481, 1484 |

## 7. Index rows (thin; exactly one per handoff)

Append to `handoffs/active/routing-and-optimization-index.md`:
`| RTG-56 | typed decision plane | [typed-decision-plane.md](typed-decision-plane.md) | TD-1 — implement the local typed-decision call path over the frozen v9 server, then TD-2 calibration before any gate | — |`

Append to `handoffs/active/inference-research-index.md`:
`| INF-76 | paw compiled specialists | [paw-compiled-specialists.md](paw-compiled-specialists.md) | PAW-1 — operator license decision package, then PAW-2 self-hosted compile spike with pinned weights | EVL-08 |`

Append to `handoffs/active/user-facing-harness-index.md`:
`| UFH-09 | fuzzy workflow authoring gui | [fuzzy-workflow-authoring-gui.md](fuzzy-workflow-authoring-gui.md) | FW-1 — sketch the two-layer workflow example and record what the GUI must expose | UFH-01, RTG-56 |`

After any row change: `python3 scripts/handoffs/index_state.py` then `--check` (must exit 0).

## 8. Intake-entry updates (Stage 4)

- **intake-811 amendment**: replace the 2026-07-11 artifact-blocker text with the dive-verified state: compiler weights (1478/1483, created 2026-06-07) and FuzzyBench eval data (1479, created 2026-02-17) were public BEFORE that blocker was written; surviving blockers = undeclared artifact licenses, no official self-hosted compile, no 10M training set. Keep the re-open rationale and the correction note.
- `handoffs_updated` fills: intake-1472/1473/1474/1485/1486/1487/1490 → `typed-decision-plane.md`; intake-1466/1467/1477/1478/1479/1481/1482/1483/1484 → `paw-compiled-specialists.md`; intake-1477 → `fuzzy-workflow-authoring-gui.md`; intake-1491 → `agentic-rocm-kernel-authoring.md` (rider); intake-1461/1480 → `autokernel-research-loop.md` (methodology only, no port claims).
- `handoffs_created`: those entries get the three new stub filenames as created.

## 9. Explicit declines

| Source | Disposition | Reason |
|---|---|---|
| Stage-1 actionable "fast routing via candidate-logit scoring" | Folded into TD-1/TD-2 + RI-11 | Cannot be a standalone task before calibration |
| Stage-1 actionable "episodic memory typed records" | Promoted M-17 | — |
| Stage-1 actionable "judge cost via typed judges" | Promoted CJ-13/ECR-TD-1 | — |
| Stage-1 actionable "autokernel porting adoption" | Promoted AK-PORT-1..3 (methodology only) | Port numbers non-citable (1461/1480 unverified) |
| 1462 dive row "fix cloned shuffled-context control" | Declined as a foreign-repo patch; lesson FOLDED into TD-2 | The jev-like **technique** is adopted via TD-1/TD-1a; patching jevlike's evaluator is not our work, but TD-2 must use a corrected/blind control |
| 1463 dive row "port collision disambiguation into torch engine" | Declined as a foreign-repo patch; requirement FOLDED into TD-1a | Colliding candidate labels must be handled natively in our implementation; we will not patch the HF Space's engine |
| 1465 (diffgemma) pattern adoption | Declined | Apple-Silicon-only diffusion path; no EPYC component; patterns already captured |
| 1466 dive row "record private-artifact gap" | Declined | Already recorded in 1474's entry notes/contradicting_evidence |
| 1475 dive row "request raw data from Good Start Labs" | Declined | No external-request channel for agents; the gap is recorded in the entry |
| 1479/1484 "paw-programs / GPT-2 compile" prototype before PAW-1 | Deferred, not declined | Gated on the license decision package (PAW-1) |
| 1481 "port SDK-compat fix upstream" | Declined | Not our artifact; caveat recorded in the entry |
| 1482 "adopt abstention into routing" | Folded into PAW-3 + RI-11 | Needs our task slices first |
| 1488/1489 | Knowledge-only | Claim-hygiene layer / discovery surface; no task |
| 1492 "capture dashboard snapshots" | Promoted ECR-TD-2 | — |
| Operator-declined dive-surfaced sources (13 groups) | Declined, named in bearing entries' `dive_corrections` | Operator selection 2026-09-17 |

## 10. Execution order (Stage 4, after approval)

1. Create the three stub files (exact content above, dates stamped).
2. Append D1–D10 task lines/riders.
3. Add the three index rows; run `python3 scripts/handoffs/index_state.py` then `--check` (exit 0 required).
4. Amend intake-811; fill `handoffs_updated`/`handoffs_created`; run `bash scripts/validate/validate_intake.sh` (exit 0).
5. Stage only this session's files; report files changed, checkbox count, new tasks, declines, validators.

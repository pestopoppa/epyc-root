# Stage-3 Plan — Worker Candidate, Durable Agent State, Security, and Verifiable Memory

**Date:** 2026-08-07
**Intakes:** 1005–1023, with corrective update to intake-346
**Status:** APPROVED AND IMPLEMENTED — Stage 4 completed 2026-08-07
**Stage-2 close-out:** closed; all five operator-selected Stage-2b sources are dive-verified
**Write boundary:** this plan authorizes no handoff, code, benchmark, model-stack, index, or production change until approved

## Outcome

Route the verified research into seven bounded work packages:

1. evaluate official LFM2.5-2.6B Q4_K_M **and Q8_0** as `worker_general` challengers;
2. add Prime Agent's two genuinely missing durability invariants—a process-safe session lease and an uncertain-side-effect recovery journal;
3. expose Continual Harness only as a shadow proposal source behind EPYC's existing evaluation and keep/revert authority;
4. import a safe DTAP task/judge subset and strengthen same-harness security/failure attribution;
5. settle direct long-context versus REPL/data-by-reference efficiency with a matched first-party arm;
6. build the broad VerMem operation/provenance/version/tombstone design as a default-inert shadow memory layer, strengthened with Mem0's scoped conflict proposal and Memory-R1's manager/distiller separation; and
7. compare parallel gist extraction with the existing Context-Folding and lossless raw-evidence paths.

The plan deliberately does not infer Pokee-Isaac's proprietary 10M architecture. Its reported 10M RULER arm is a direct full-prompt evaluation, not a REPL trick. The only bounded architectural inference is that “non-decoder-only,” sublinear TTFT scaling, flat decode, and a proprietary runtime are compatible with some subquadratic/compressed-state/sparse/recurrent/latent design plus specialized prefill kernels; the report does not distinguish among them. For EPYC, long context and REPL are complementary: long context is an archive/fallback surface, while a REPL with precise tool calls remains the active control plane to test.

No new handoff is needed. No frozen production-kernel, model-stack, registry, chapter, wiki, or measurement-constitution edit is proposed.

## Owner audit

| Proposed owner | Live status checked 2026-08-07 | Routing decision |
|---|---|---|
| `architect-model-selection-bench.md` | Active; already owns the standing search for faster `worker_general` candidates and direct Gemma4 comparisons | Own the LFM Q4/Q8/Gemma matched candidate verdict. |
| `repl-session-memory-maturity.md` | Active; owns persisted REPL-session deltas and explicitly rejects single-process race assumptions | Own process fencing and uncertain-side-effect recovery. Do not reopen the completed `session_persistence.md`. |
| `autopilot-continuous-optimization.md` | Active, indexed implementation owner; AutoPilot is currently operator-stopped behind an unrelated human apply | Own shadow proposal generation. The new task cannot resume AutoPilot or bypass the existing stop/gates. |
| `tool-use-eval-contract.md` | Active; owns REPL/native-tool contract, sentinels, usefulness, and tool-path telemetry | Own a bounded DTAP subset plus the Continual/Pokee adversarial fixtures and typed failure attribution. |
| `rlm-contested-claims-self-evaluation.md` | Active; E3 already requires the missing clean non-RLM long-context control | Extend E3 rather than creating another long-context handoff. Do not append to completed `long-context-eval-datasets.md`. |
| `unified-trace-memory-service.md` | Active; trace ingest remains read-only, while its separate default-inert `MemoryActionStore` already owns append-only patterns, versions, tombstones, raw event references, and memory A/B rationale | Own the VerMem/Mem0/Memory-R1 shadow schema and state machine in the agent-facing memory layer; `src/trace/` stays read-only. |
| `context-folding-progressive.md` | Active only for validation/design probes; current compaction behavior is already landed | Own one matched parallel-gist design probe, not a second production memory stack. |
| `episodic-memory-integrity.md` | Active but narrowly owns FAISS correctness/reseeding and an existing memory on/off A/B | No new schema task. Consume its store-health gates as prerequisites and leave its scope unchanged. |
| `meta-harness-optimization.md` | Frozen compatibility pointer | No edit; route Continual work to AutoPilot and tool-use owners. |

Every selected active owner is already indexed. Stage 4 adds task lines only; it does not add master/domain-index rows.

## Exact Stage-4 handoff edits

### S3-1 — LFM2.5 Q4 + Q8 worker candidate

Append to `handoffs/active/architect-model-selection-bench.md`:

```markdown
## 2026-08-07 — LFM2.5-2.6B `worker_general` candidate (intake-1006/1014/1019)

- [ ] **WG-LFM-1 — Run a matched Q4_K_M / Q8_0 / Gemma4 26B-A4B worker verdict.** Pin the
  official LiquidAI GGUF revision `b421ad1d549afeda6a0fb2ad3a697cb5a7879adc`; test both
  `LFM2.5-2.6B-Q4_K_M.gguf` and `LFM2.5-2.6B-Q8_0.gguf`, with the current Gemma4 26B-A4B
  `worker_general` as the unchanged incumbent. Start with load/template/tool-call smokes on frozen v8;
  then use identical role prompts, tools, task rows, seeds, limits, stop conditions, and scorer era.
  Hash and archive the **GGUF-embedded** chat template used by the runner—the separate LEAP sidecars
  omit its reasoning prefill and tool rendering and are ineligible unless parity is independently
  proven. Report strict task success, per-suite outcomes, tool-schema compliance and repair rate,
  reasoning/output tokens, retries, peak resident memory, prompt/decode throughput, TTFT, and complete
  wall time. Publish Q8-minus-Q4 and each-LFM-minus-Gemma paired deltas. Do not change the role alias,
  registry, stack manifest, or production process unless a later operator decision accepts a
  decision-grade Pareto result.
```

### S3-2 — Prime Agent durability invariants

Append to `handoffs/active/repl-session-memory-maturity.md`:

```markdown
## 2026-08-07 — process-safe ownership and uncertain-effect recovery (intake-1009/1010)

- [ ] **D-f — Add a cross-process session lease with fencing, not a process-local mutex.** Acquire
  ownership transactionally in the existing SQLite session store using `session_id`, owner identity,
  PID plus process-start identity, monotonically increasing fencing token, heartbeat/expiry, and
  acquired/released timestamps. Every mutating checkpoint/session write must present the current
  fencing token. A stale lease may be reclaimed only after liveness/expiry reconciliation; PID reuse,
  simultaneous acquire, owner crash, delayed stale writer, and idempotent release are mandatory
  regression fixtures. Preserve read-only concurrent inspection.

- [ ] **D-g — Journal uncertain external side effects before resume can replay them.** Add a durable
  per-action record with stable action/idempotency key, tool and normalized arguments hash, attempt
  number, `prepared|dispatched|confirmed|failed|uncertain|reconciled` state, timestamps, result/evidence
  reference, and reconciliation policy. Persist `prepared` before dispatch and terminal evidence after
  return. After a crash between dispatch and confirmation, resume must not blindly repeat: probe the
  external state or require an explicit retry/skip resolution, append the reconciliation outcome, and
  retain the original uncertain row. Test crashes before dispatch, after dispatch, after effect but
  before confirmation, duplicate callback, and non-idempotent tool behavior.
```

### S3-3 — Continual Harness as a shadow proposer

Append to `handoffs/active/autopilot-continuous-optimization.md` at its current tail after re-reading it:

```markdown
## 2026-08-07 — reset-free trajectory refinement, proposal-only (intake-1016/1020)

- [ ] **AP-CH-1 — Add a default-off adapter that turns a bounded recent trajectory window into typed
  prompt/subagent/skill/memory candidates.** The adapter may diagnose and propose only. Validate every
  payload against a local schema, cap repeated equivalent proposals, and emit ordinary candidate
  envelopes with source trajectory ids, proposer identity, component kind, before/after content, and
  claimed failure signature. It has no authority to write live prompts, execute generated Python,
  mutate skills/memory, select itself, or keep a change. Existing held-out evaluation, checkpoints,
  transactional keep/revert, privilege policy, and promotion authority remain outside the proposer.

- [ ] **AP-CH-2 — Compare reset-free and episodic proposal generation at equal budget.** Use the same
  completed trajectories, proposer model, token/tool budget, candidate schema, evaluator, and held-out
  task set. Report valid-candidate rate, duplicate/oscillation rate, held-out lift, regressions, cost,
  and wall time. The upstream 25/100-step cadence is not a default; cadence is a declared experimental
  variable. No live AutoPilot resume or acceptance-policy change follows from this task.
```

### S3-4 — DTAP and adversarial fixtures

Append to `handoffs/active/tool-use-eval-contract.md`:

```markdown
## 2026-08-07 — state-judged agent security and recovery fixtures (intake-1012/1016/1020/1021)

- [ ] **TU-DTAP-1 — Import a reviewed, bounded Apache-2.0 DTAP subset into a disposable local runner.**
  Select paired benign/direct/indirect cases across prompt, tool, skill, environment, and compositional
  injection. Preserve each task's config and deterministic final-state judge, but inspect every setup
  script before use and never run it on the host. Hold model, prompt, tools, endpoint, temperature,
  retries, and harness fixed across arms. Add repeated seeds/confidence intervals, immutable trace
  replay, and typed `model|parser|tool|endpoint|harness|judge|infrastructure|overflow` outcomes. Keep
  attack generation target-disjoint from the final comparison; matched-target DTAP-RED results are an
  attack-search upper bound, not a general robustness score.

- [ ] **TU-ADV-1 — Add the Continual/Pokee negative cases as exact contract fixtures.** Fixture A
  repeats one invalid tool payload and must terminate/classify well before 842 attempts. Fixture B
  offers a privileged environment/oracle path that improves reward while violating allowed
  capabilities; the evaluator must reject the exploit and prevent its conversion into a reusable
  skill. Score benign completion beside attack success and retain the full typed failure chain.
```

### S3-5 — Direct long context versus REPL/data-by-reference

Extend E3 in `handoffs/active/rlm-contested-claims-self-evaluation.md` with:

```markdown
  - [ ] **E3b — Run a clean same-model direct-context versus REPL/data-by-reference comparison.** The
        Pokee-Isaac report's 10M RULER result is a direct full-prompt arm, not external-memory or REPL
        paging, and its proprietary architecture cannot be reproduced from the report. Use locally
        supported context lengths and matched retrieval, document-QA, and tool-mediated tasks. Compare
        (A) one direct prompt, (B) existing Context-Folding, and (C) a REPL whose large corpus remains
        in variables/files and is accessed through precise deterministic searches/slices. Hold model,
        task, answer scorer, total time limit, and available information fixed. Report quality,
        evidence recall, TTFT, prefill/decode tokens and throughput, peak memory/KV, number and precision
        of tool calls, root/subcall tokens, turns, retries, and wall time. Include a zero-sub-LLM
        Python/search arm. Treat long context as archive/fallback and REPL as control-plane hypotheses;
        choose by measured Pareto result, not by the proprietary 10M headline.
```

### S3-6 — VerMem + Mem0 + Memory-R1 shadow memory layer

Append to `handoffs/active/unified-trace-memory-service.md`, explicitly under the separate agent-facing
memory layer rather than `src/trace/`:

```markdown
## 2026-08-07 — verifiable memory operations, default-inert shadow path (intake-1008/1015/1017/1018/1022/1023)

- [ ] **UTM-V1 — Complete the append-only memory-operation envelope and state-transition engine.** Add
  typed `ADD|UPDATE|DELETE|RETRIEVE|FILTER|SELECT_EPISODE|SUMMARIZE|NOOP` proposals over the existing
  raw-event authority. Every operation carries operation/session/actor ids, immutable source-event
  references, before/after value hashes, version and supersession links, applicability boundary,
  proposer/verifier versions, `proposed|validated|committed|rejected|rolled_back` state, and error or
  rollback provenance. `UPDATE` creates a new version; soft `DELETE` creates a tombstone and preserves
  history; physical privacy erasure is a separate explicit state and must not be claimed from a
  tombstone. Implement restore/rollback and stale-fencing fixtures. Existing raw traces are never
  overwritten or made unrecoverable.

- [ ] **UTM-V2 — Add a local scoped write proposer, not an authoritative writer.** Combine Mem0's
  user/agent/run scoping, recent-message context, top-k conflict retrieval, and four-way mutation
  proposal with VerMem's stronger envelope. Record actor versus subject so one model's inference
  cannot silently become another actor's fact. Run in shadow on recorded traces first; compare
  proposed operations with current append-only behavior and human-labelled cases. Do not copy the
  current Mem0 branch's ADD-only default as the target and do not allow lossy facts to replace raw
  evidence.

- [ ] **UTM-V3 — Separate structural and semantic verification and calibrate both.** Structural checks
  deterministically enforce schema, scope, provenance, version, tombstone, rollback, source existence,
  and transition legality. A separately versioned semantic judge scores local operation correctness
  and global memory coherence. Build human-labelled conflicting, stale, poisoned, private, strategically
  manipulated, duplicate, missing-source, and delete/restore cases; report false-pass/false-fail by
  class. The released VerMem rule verifier is only the structural baseline and cannot inherit the
  paper's DeepSeek semantic-verifier result.

- [ ] **UTM-V4 — Test answer-time evidence distillation independently of memory writing.** Preserve
  Memory-R1's manager/distiller separation: retrieve a bounded candidate set, then have the answer
  path select evidence with source ids before answering. Sweep the retrieval/distillation budget
  rather than assuming sixty entries is optimal. Score answer quality, evidence precision/recall,
  unsupported claims, tokens, latency, and raw-source recoverability against no-distiller retrieval.

- [ ] **UTM-V5 — Emit per-operation credit in shadow, without RL training.** Record deterministic
  structural result, calibrated local/global semantic result, downstream task outcome, evidence
  recall, operation cost, and rollback/recovery outcome as separate fields. Compare task-only credit
  with operation-level credit. No learned policy may consume this signal until deterministic and
  supervised baselines, conversation-isolated splits, verifier calibration, and reproducible data
  show a measured advantage; the official Memory-R1 repository currently releases no training code.

- [ ] **UTM-V6 — Run a complete memory evaluation matrix with a mandatory no-memory control.** Include
  no-memory/raw full context, current append-log retrieval, current Context-Folding, Mem0-style shadow
  proposals, VerMem operations, answer distillation, and the CF-AM-1 parallel-gist arm. Measure within-
  task, crash/restart, cross-session, conflict/staleness, poisoning, actor scope, tombstone, physical
  erasure, rollback, and raw-evidence recovery. Account for extraction, write, embedding, retrieval,
  answer, verifier, training (if later permitted), tokens, latency, wall time, and storage separately.
  Use conversation-level splits and repeated end-to-end seeds; judge repeats alone are not uncertainty.
```

### S3-7 — ActiveMem parallel gist probe

Append to `handoffs/active/context-folding-progressive.md`:

```markdown
- [ ] **CF-AM-1 — Compare parallel small-model gist extraction with current folding and lossless raw
  retrieval.** On one held-out local document/search set, run identical tasks through current
  deterministic Context-Folding, a bounded fan-out of small local gist extractors, and raw append-log
  retrieval. Every gist must retain resolvable raw-document/event ids; failure to resolve is a hard
  error. Report answer quality, evidence recall, gist omission/contradiction, hit/reuse rate, complete
  inference and retrieval tokens, communication, peak memory, and wall time. Hold the final planner and
  judge fixed. Do not adopt ActiveMem's comparison-set-relative ACT score or unreleased runtime.
```

## Intake-index edits after approval

Stage 4 will make targeted in-place YAML edits only. It will populate `handoffs_updated`, append a dated
Stage-3 routing line to `dive_corrections`, and set `integration_disposition: integrated` only where a
verified actionable is actually routed below. “Integrated” means durable task ownership, not deployed code.

| Entries | Handoffs after Stage 4 | Disposition |
|---|---|---|
| 1006, 1014, 1019 | `architect-model-selection-bench.md` | WG-LFM-1; Q4 and Q8 both mandatory. |
| 1009, 1010 | `repl-session-memory-maturity.md` | D-f/D-g; all overlapping Prime features remain declined. |
| 1016, 1020 | `autopilot-continuous-optimization.md`, `tool-use-eval-contract.md` | AP-CH-1/2 and TU-ADV-1; live apply/executor/training declined. |
| 1012, 1021 | `tool-use-eval-contract.md`, `rlm-contested-claims-self-evaluation.md` | TU-DTAP-1 and E3b; proprietary architecture/throughput transfer declined. |
| 1008, 1015 | `unified-trace-memory-service.md` | Negative verifier/measurement fixtures only; Cognitive Workspace runtime declined. |
| 1017 | `context-folding-progressive.md`, `unified-trace-memory-service.md` | CF-AM-1 plus the lossless/provenance evaluation arm. |
| 1018, 1022, 1023 | `unified-trace-memory-service.md` | UTM-V1…V6. |
| 346 | none | Keep the corrective `dive-overturned` record; intake-1022 owns implementation routing. |
| 1007 | none | Dataset consumption remains declined because the declared configs resolve to an exploded union and source authorization is unproven. |
| 1011 | none | PRO-LONG implementation was already audited/routed under intake-919; do not duplicate it. |
| 1005, 1013 | none | Retain as research/onboarding context; no active technical action. |

## Explicit declines and non-actions

- Do not download/promote LFM into the live role or alter the registry/stack in Stage 4. The task is a benchmark specification only.
- Do not use LEAP's simplified LFM template unless exact behavioral parity with the embedded GGUF template is proven.
- Do not import Prime Agent wholesale; EPYC already covers most persistence, checkpoints, schedules, rollback, and optimization behavior.
- Do not execute Continual Harness generated Python, adopt its in-process “sandbox,” apply its mutations live, or claim its unreleased PRM/DAgger pipeline.
- Do not run upstream DTAP setup scripts on the host or compare unequal harnesses as model security.
- Do not reverse engineer, clone, or set an MI210 target from Pokee-Isaac. “Non-decoder-only” permits bounded hypothesis generation only; it does not select an architecture.
- Do not equate a VerMem tombstone with physical privacy erasure, or attribute paper semantic-verifier gains to released rule code.
- Do not let Mem0-derived facts overwrite raw evidence or treat the current OSS ADD-only path as the paper algorithm.
- Do not begin Memory-R1 RL training from prose. Code, data, verifier, split, and baseline gates come first.
- Do not consume the distillation dataset until each config has explicit `data_files`, stale generations are removed, counts/splits are regenerated, provenance is auditable, and training authorization is established.
- Do not create a new memory system or security handoff; all work has a live owner.

## Completeness audit

| Gate | Result |
|---|---|
| Stage-1/2 actionables | Every selected high-relevance actionable maps to S3-1…S3-7 or an explicit decline. |
| Stage-2b actionables | LFM L1-L4 → S3-1; Continual C1-C5 → S3-3/S3-4; DTAP D1-D5 → S3-4; Mem0 M1-M5 → S3-6; Memory-R1 R1-R5 → S3-6. |
| Steering ledger | Noncommercial LFM stance preserved; Q8 added; Prime invariants routed; Pokee 10M/REPL question answered in outcome and E3b; “take everything” from VerMem mapped to UTM-V1…V6 without inventing missing semantic code. |
| Unverified-quote gate | Closed. Paste-ready task text uses dive-verified/overturned claims only. |
| Surfaced-source gate | Closed. All five operator-selected sources are intake-1019…1023; companion artifacts were bundled and no unresolved gate-worthy source remains. |
| Owner status gate | Closed. Completed session/long-context handoffs and the frozen Meta-Harness pointer are not edited. |

## Stage-4 file scope and validation

After approval, Stage 4 may edit only:

- the seven active handoffs named in S3-1…S3-7;
- `research/intake_index.yaml` through targeted in-place edits;
- `.research-session.json` to mark the plan approved/landed;
- this plan's status line; and
- the current daily progress file, append-only after re-reading it.

Stage 4 does **not** implement code, run inference, download GGUFs, start/reload services, change a model
role, modify a frozen kernel, or amend `MEASUREMENT.md`.

Validation:

1. `bash scripts/validate/validate_intake.sh`
2. `python3 -m json.tool .research-session.json >/dev/null`
3. `git diff --check`
4. Confirm fifteen new open task ids: WG-LFM-1, D-f, D-g, AP-CH-1, AP-CH-2, TU-DTAP-1, TU-ADV-1, E3b, UTM-V1…UTM-V6, and CF-AM-1.
5. Confirm zero new handoffs/index rows and no implementation, model-stack, service, kernel, chapter, wiki, or measurement-policy edits.

## Approval boundary

Approval authorizes the exact Stage-4 documentation/index routing above. It does not authorize executing the
benchmarks, implementing the tasks, changing live memory or proposal authority, resuming AutoPilot, consuming
the distillation dataset, or changing the production model lineup.

# Intake-Derived Work — 2026-07-25 sweep

> **Fold destination** (BRF-T1-F9, BRF-T1-1, route 1a, 2026-11-02): renamed from `intake-derived-work-2026-07-25.md`; absorbs 4 handoff(s) as `## Track:` sections at the end of this file (`agent-file-prose-compression.md`, `frontier-f2-self-running-lab.md`, `frontier-f3-data-flywheel.md`, `stale-open-audit-2026-07-18.md`). The body above the first track is the former `intake-derived-work-2026-07-25.md`.

**Scratch**: `/mnt/raid0/llm/tmp/intake-decision-tools/` · worktrees: `/mnt/raid0/llm/worktrees/intake-decision-tools-*`

**Status**: active — coordination point for work derived from the 2026-07-25 research-intake sweep
**Created**: 2026-07-25 (via `/research-intake`; 12 submitted sources + 4 expansion entries + Tier-2b contradicting-evidence sweep + a companion-artifact conflation audit of the intake index)
**Categories**: agent_architecture, autonomous_research, memory_augmented, benchmark_methodology, context_management, knowledge_management

**Why this file exists**: this sweep produced (a) one **confirmed live defect** in autopilot's GEPA client, (b) a body of independent contradicting evidence that undercuts *standing* EPYC decisions, (c) two new eval instruments, and (d) a process defect in the intake pipeline itself. Rather than scatter edits — and because a parallel session holds uncommitted work in four CPU-kernel handoffs — this file owns the derived queue and **references** the owning handoffs. Items graduate into their owning handoff on operator approval.

**Parallel-session coordination (2026-07-25)**: `cpu-prefill-compute-large-models.md`, `iqk-iquant-enablement.md`, `laguna-s21-cpu-port.md`, `llama-cpp-dsa-contribution.md` had **uncommitted edits from a concurrent v8 kernel session** at the time of writing. Nothing here edits them. Items ID-12/ID-15/ID-17 are addressed to that session — coordinate before committing.

**Stage-2a dive pass (2026-07-25)**: every item below was verified against primary source before filing. Five dives ran and were decisive — **two fabricated citations were caught and removed from the index before shipping** (a CORE ablation that does not exist in the paper, and an invented `/doctor` behaviour), the P0 defect had the **wrong mechanism**, three proposed tasks were **arguing with code that is not running**, and several checkable numbers were wrong. Items still carrying a number that was not dive-verified are marked `[unverified]`.

**Evidence-grade note (MEASUREMENT.md)**: every external number below is an **observation** unless explicitly labelled otherwise. None may gate a keep/revert/deploy/promote decision without local re-measurement under a cited protocol. Where a claim was independently contradicted, the contradiction is recorded inline — that is the point of the Tier-2b pass.

---

**Priority**: LOW — T6 but rank 63 of 174; best open item is a decline of the TRL bridge, tracks are coordination plus MI210-gated training (W3).

## P0 — Live defect (verified on disk, this session)

- [x] **ID-1 — GEPA reflective mutation is a guaranteed no-op, and has been since at least 2026-06-04.** ✅ 2026-07-25 FIXED (all four items; blacklist lifted; mechanism-validated; live run pending AP-19b supervised window — see `autopilot-continuous-optimization.md` § 2026-07-25). Cold-start gate findings that emerged from validation are filed in `esc8-stack-restart-landmine-audit-2026-07-22.md` § 2026-07-25. `epyc-orchestrator/scripts/autopilot/species/gepa_optimizer.py:192-194` defines `propose_new_texts()` that unconditionally raises `NotImplementedError("Use GEPA's built-in proposer")`. GEPA's proposer dispatches on **presence, not None-ness** (`gepa/proposer/reflective_mutation/reflective_mutation.py:66-67`: `if self.adapter.propose_new_texts is not None`) — a bound method is never `None`, so **every** reflection step raises **before any LM call**.
  - **Correction to the first report of this defect**: the mechanism is NOT "LiteLLM routes reflection calls to api.openai.com with a bogus key". **litellm is never reached and no network call occurs.** Fixing `api_base` alone would change nothing. (`reflection_lm_url` is indeed assigned at L209/L214 and never read, and only `OPENAI_API_KEY` is set at L265 — but those are downstream of a raise that always fires first.)
  - **Direct evidence**: `logs/autopilot.resume700b.log:1210-1219` (trial 521, 2026-06-04) — traceback through `reflective_mutation.py:67`, then every iteration logs `Reflective mutation did not propose a new candidate`, ending `GEPA optimization complete: 0.718 → 0.000 (-0.718) in 633s (50 evals)`. Repeats at `:2384-2393`. **633 s and 50 evals burned per invocation for a guaranteed no-op.**
  - **Fix set, in order**: (1) remove the `NotImplementedError` override so the built-in proposer runs; (2) *then* wire `reflection_lm_url` → `api_base` (upstream forwards it, `src/gepa/lm.py:49`) **and plumb it from `prompt_forge.py:517-519`, which currently constructs the optimizer with default args**; (3) surface the failure instead of returning a no-op after 633 s; (4) **the validation target is frozen** — `gepa_optimize` on `frontdoor.md` is blacklisted since 2026-06-05 at `corruption` severity (`scripts/autopilot/failure_blacklist.yaml:40-47`), so lift the entry or validate against a different target file.
  - **Blast-radius correction**: not "~135 trials on a dead path". Journals (all shards read) show **only 8 `gepa_optimize` trials ever** — 181, 182, 521, 536, 785, 882, 1137, 1144 — exactly **one** ever `keep`.
  - Owner: [`autopilot-continuous-optimization.md`](autopilot-program.md) (AP-19a). Operator directed 2026-07-25 that this must be filed.

- [x] **ID-2 — Decide the `gepa` dependency pin.** ✅ 2026-08-23 — ungated half landed; the VERSION choice (a)/(b)/(c) stays gated behind AP-19b/AP-29c as filed. Installed is **0.0.26** (2026-01-24), verified in `/mnt/raid0/llm/epyc-orchestrator/.venv`; `import gepa.optimize_anything` and `import gepa.oa` both raise `ModuleNotFoundError`. PyPI latest is 0.1.4 (2026-07-15); the `optimize_anything` engine layer exists **only on main** (absent at tag v0.1.4, confirmed by upstream 404). Options: (a) hold 0.0.26, (b) bump to PyPI 0.1.4, (c) pin a main SHA for the engine layer. Re-run `tests/test_gepa_integration.py` against the choice — 0.0.26 → 0.1.x is untested here. **Sequence after ID-1**: a version bump against a proposer that always raises proves nothing.
  - Owner: [`autopilot-continuous-optimization.md`](autopilot-program.md).
  - **RE-DERIVED 2026-08-11 (`mainC`) — the framing "installed and unpinned" is WRONG, and the
    real defect is a different one.** `gepa` **is** pinned: `uv.lock` holds `gepa==0.0.26` with
    sha256 hashes for both sdist and wheel, so supply-chain integrity is already enforced. What is
    actually wrong is that **`gepa` is an UNDECLARED DIRECT dependency**. It reaches us only as a
    transitive dep of `dspy` 3.1.3, yet `scripts/autopilot/species/gepa_optimizer.py:247` does
    `import gepa` directly — so the day `dspy` drops or re-pins it, our import breaks with nothing
    in `pyproject.toml` to catch it. This repo has already been bitten by exactly this class twice
    and says so in the manifest: `matplotlib` ("used-but-undeclared before 2026-06-04: a venv
    rebuild silently dropped it") and `mcp` ("fastmcp depends on it transitively, but pin it
    explicitly so a future fastmcp release can't drop us").
  - **DECISION (the ungated half): declare `gepa==0.0.26` directly in `pyproject.toml`.** Pinned,
    not floated — AP-29c holds the VERSION choice until AP-19b runs the repaired proposer live
    once, and 0.1.4 still lacks `optimize_anything` (main-branch only), so a `>=` would authorize
    a gated upgrade. Declaring the already-resolved version changes no resolution. This does not
    re-argue the pin; option (a)/(b)/(c) above stays untouched and still sequenced behind ID-1.
  - **BLOCKED ON A TOOLING MISMATCH, verified rather than assumed.** I made the edit and ran
    `uv lock`: it produced the two expected `gepa` lines **plus unrelated churn** — environment
    markers stripped from `nvidia-cublas-cu12`, `nvidia-nvjitlink-cu12`, `nvidia-cusparse-cu12`,
    `cryptography` and `jeepney` (e.g. `marker = "platform_machine != 's390x' and sys_platform !=
    'emscripten' and sys_platform != 'win32'"` → unconditional). That would change what installs on
    other platforms, so I reverted both files; `uv lock --check` is clean again at baseline. Local
    uv is **0.11.26**, which is evidently not the version that generated the current lock.
    **Consequence beyond this row: ANY dependency edit in `epyc-orchestrator` right now will drag
    the same marker churn in.** Apply this with a matching uv version, or land the marker rewrite
    deliberately as its own reviewed change — not as a side effect of a one-line pin.
  - **DONE 2026-08-23 (EVL-29 ID-2)**: `gepa==0.0.26` declared as a direct dependency in
    `epyc-orchestrator/pyproject.toml` (pinned, with a used-but-undeclared comment mirroring the
    `matplotlib`/`mcp` precedent), committed `f8bc4d2b`. Tooling outcome: ran with **uv 0.12.5** (not
    the 0.11.26 that produced the 2026-08-11 churn) — **no marker stripping this time**; the nvidia/
    cryptography/jeepney churn is absent. Only residual delta beyond the two expected `gepa` lines
    is a **reordering of the `resolution-markers` header array** (identical 24-string set, verified
    by sort-diff; uv 0.12.5 groups by python version instead of platform). No package version,
    hash, or platform-marker changed; gepa record byte-identical (0.0.26, both hashes); `import
    gepa` verified in the repo `.venv`. Follow-up `533cb3d6`: f8bc4d2b accidentally committed a
    stale staged copy of `contention_matrix.yaml` (reverting the OP-21 row); restored to
    byte-identical 6665a923 content — end state correct, noted for operator awareness.

## P1 — Standing decisions now contradicted by independent evidence

- **[declined: ws58 2026-11-03 content-review: duplicate — autopilot-program AP-19b (absorbing AP-21) owns the GEPA question]** **ID-3 — Re-open the AP-21 `gepa_ratio = 0.30` decision on two independent grounds.** AP-21 (2026-07-11) declined to raise GEPA's PromptForge share. **Corrected facts**: only **8 `gepa_optimize` trials have ever run** (one ever `keep`), and `gepa_ratio` is **absent from the live `orchestration/autopilot_state.json`** — the 0.30 is a hardcoded fallback at `autopilot.py:8798`, on the *autonomous-fallback* path, not stored state and not the primary dispatch (the LLM planner emits `gepa_optimize` directly). Both the *evidence* and the *premise* are in question:
  - **Instrument**: ID-1 — that evidence was produced by a client whose proposer always raises. **Gate this item on ID-1**: until the proposer runs, we have no local signal at all.
  - **External claim strength**: arXiv **2607.14004** (Terminal-Bench 2.0, matched budgets, independent) reports the GEPA-optimized agent transferring **below the unoptimized baseline** — negative transfer under task shift. arXiv **2602.01011** reports GEPA returning the seed prompt essentially unchanged on GPQA-Diamond and MATH-500. arXiv **2606.19605** (Cisco) reproduced GEPA at **−3.78 to +7.97 pp** vs published — a band comparable to GEPA's own headline effect.
  - **Both README headline numbers fail checking**: "ARC-AGI 32%→89%" comes from a *different method* (`optimize_anything` evolving code with Gemini 3 Flash); GEPA's own tutorial reports **44.0%→49.5%**. "90x cheaper than Claude Opus 4.1" links to a **Databricks** blog — an adopter listed in the same README, not independent corroboration.
  - Owner: [`autopilot-continuous-optimization.md`](autopilot-program.md).

- **[declined: ws58 2026-11-03 content-review: duplicate — autopilot-program AP-29 gate owns it]** **ID-4 — Gate AP-29 KnowledgeDistiller BEFORE wiring; add an episodic-only control arm.** Code landed 2026-05-08 (`4cdc77e`); **wiring is still deferred**, so this is a free design change now and an expensive rollback later. `KnowledgeDistiller` has **zero non-test callers** — it is not flag-off, it is *uninstantiated*, so the free-design-change premise holds. The planned trigger — consolidation at the 25-trial auto-checkpoint (`autopilot.py:8596`, which today calls only `lab.checkpoint_state`) — is the worst-performing arm ("Force") in arXiv **2605.12978**. **Note the consolidation predicate is already MDL-gated** (`knowledge_distiller.py:37-41`, `min_validity=0.10`), so **only the cadence is unconditional**. That paper shows a streaming consolidator dropping a 19-problem ARC-AGI slice from **100% → 52.6%** *while being fed only ground-truth solutions* (`"Stream: offline GT-solution"`), so the fault is provably in the rewriting step. Carry the authors' own caveat: *"two repeats per question"*, *"point estimates … rather than formal error bars"*. Four independent 2026 papers document the same net-negative accumulation: **2605.24050** (skill shadowing — driven by semantic confusability, not size), **2605.19576** (Library Drift — performance drops *below the no-skill baseline*), **2605.26667** (MemFail), **2605.22842** (safety declines under benign accumulation, no adversary).
  - Require the distiller to beat an **episodic-only** arm (retain + delete, abstraction disabled) before it ships.
  - 2026-11-02: [comparison preparation](../../docs/design/knowledge-distiller-comparison-preparation.md) documents the native paired primitive, task-family partition requirement, and work needed for a held-out quality comparison; no comparison has run. [no-belief: preparation only]
  - **Already satisfied — make explicit, do not file as an ask**: the landed code does **reversible quarantine via validity decay** (`knowledge_distiller.py:316-319`), not deletion. The removal language appears only in the *paper-summary* section of the HCC deep-dive; the EPYC integration spec says *supersede*.
  - Consolidate in **grouped batches by task family**, not per-checkpoint streaming. Independently corroborated: intake-627 (Trace2Skill) reports parallel batch consolidation beating sequential online editing by **+4.0/+6.8 pp** and ~20× faster — same direction, different group, different benchmark. **Attribution fix**: the *17–38 pt* figure is **Stream vs whole-batch Pool**, not Static-Group vs ungrouped. **Drop CLIN** from the justification — it has no numerical results in the paper.
  - Owner: [`autopilot-continuous-optimization.md`](autopilot-program.md).

- [x] **ID-5 — REPLACES the old AP-32 task, which was arguing with dead code. ✅ 2026-07-29** `audit_insight_specificity()` (`strategy_store.py:1956-1993`) is a **read-only regex linter with ZERO callers repo-wide** — it `SELECT`s rows, matches four patterns, returns findings, and **writes nothing**. `generalized_content` defaults to the *unmodified* insight (`:110`). There is no abstraction pressure to re-examine. Two real actions survive:
  - (a) **If** that audit is ever wired into a write path, require retained applicability preconditions first (arXiv 2605.12978 failure mode 5).
  - (b) **Struck the "+1.1% task-agnostic insights" justification ✅ 2026-07-29** from the remaining `wiki/agent-architecture.md` source-index entry — it is an *external paper's* figure (intake-425, arXiv 2604.14004), never measured on EPYC, and is now explicitly labelled as such.
  - Owner: [`autopilot-continuous-optimization.md`](autopilot-program.md).

- [x] **ID-5b — utility-weighted retrieval targets the MemRL code path, not SkillBank ✅ 2026-07-29.** The MemRL episodic retriever combines `q_weight * q_value + (1-q_weight) * similarity` (`retriever.py`), whereas SkillBank uses confidence plus FAISS similarity and carries no `q_value`. SkillBank is feature-flagged **off**; its current default `sessions/skills.db` is empty, so the earlier 57-row snapshot is historical rather than a migration obligation. Treat MemRL as the implementation target when its runtime use is independently established; this source audit makes no live-region claim during E5. SkillBank's rebuild remains a clean design point. Merge-on-dedup is conditional: cosine ≥0.85 **and** same `skill_type` **and** overlapping `task_types` (`distillation/pipeline.py:305-322`).
  - Owner: [`autopilot-continuous-optimization.md`](autopilot-program.md), [`unified-trace-memory-service.md`](memory-program.md#track-unified-trace-memory-service).

- [x] **ID-6 — Do NOT trim CLAUDE.md / agent files on the vendor ">80%" claim ✅ 2026-07-29.** Epyc-root `c942728e` documented the exact quote as anecdotal and recorded the counter-evidence: the post supplies **no protocol, suite, n, date or link** (`benchmark`=0, `SWE-bench`=0, `study`=0, `experiment`=0); do not assert it "traces to a conference talk" — that is not supported by the page; say *no source is given*. Against it: arXiv **2512.17920** finds **constraint compliance degrades substantially faster than semantic accuracy under compression, and smaller models violate constraints more readily at the same ratio** — with an "instruction ambiguity zone" where output *looks* fine while explicit directives are silently dropped, i.e. **naive eval scores this as "no degradation."** EPYC's own `agent-file-prose-compression.md` Phase-3 data already shows compression tolerance is non-monotonic and model-dependent (`worker_fast` pinned to `none`; `worker_30B` fails mild AND medium but passes aggressive).
  - The safe, model-independent subset is **lossless structural deletion** (derivable content + duplicated policy), which carries none of the per-model compression risk — see ID-11/ID-12.
  - **`/doctor`'s behaviour must be re-sourced from the CLI or reduced to "rightsizes skills and CLAUDE.md, unspecified."** The post contains only two generic sentences — the dedupe / trim / migrate / report-before-changing description was invented and has been struck from intake-896#record.
  - Any trim must be falsified locally through the existing gate: `tests/compliance/agent_file/live_runner.py` (compliance ≥ 0.95× baseline, procedure ≥ 0.95× baseline, recall ≥ 0.90 absolute).
  - Owner: [`agent-file-prose-compression.md`](frontier-lab-automation.md#track-agent-file-prose-compression).

---

## P2 — New instruments (both address named, dated gaps)

- [x] **ID-7 — Add an `ordered_subsequence` verifier to the canonical `answer_scoring` library.** ✅ 2026-08-12
  (`auditor`, pulled from the dispatch queue and claimed; research `9cc8db2d`.) Landed in the canonical
  lib — not an 11th bespoke scorer — with BOTH metrics as the row demands: order-blind `coverage`,
  graded `coverage_in_order` (DP over all occurrence positions, so an early out-of-order mention never
  shadows a later in-order chain), binary `all_in_order` (the paper's Ordered Rate), plus a
  `scoring_method: "ordered_subsequence"` dispatch arm. The spaCy fragility the row names is handled by
  the lib's own lazy+guarded pattern: spaCy when importable, injectable lemmatizer for tests, and a
  surface-matching fallback that is CONSERVATIVE (misses inflections, never false-matches) and flagged
  in the result. Empty concept list is REFUSED at both the primitive and the dispatch — a bad suite
  config raises instead of scoring every response perfect (tonight's vacuity lens, applied forward).
  8 new tests, fallback pinned; file 12/12. Confound carried: the paper's 4-bit-vs-API leaderboard is
  NOT quant-quality evidence. **ID-8 (FrontierCS floor probe) is now unblocked on this edge.** From arXiv **2506.15629** (Sakai et al., **ACL 2025 Main — peer-reviewed**, credibility 4): give an ordered concept list, lemmatize the completion, check all concepts appear as an ordered subsequence; return graded coverage in [0,1] plus a binary all-in-order flag. Why it matters here: our 43-question `instruction_precision` suite has **no ordering/sequence verifier of any kind** (verified against chapter 07's full verifier enumeration), and the best model in the paper reaches only **~75%** ordered rate against ~99% unordered coverage — an IF axis with real headroom where ours is saturated. **Add BOTH metrics, not one** — my earlier note that Ordered Rate and Coverage-with-order are redundant is **overturned**: they diverge by up to **26.5 pts** on weak models (Qwen2-0.5B 30.84 vs 57.34) and converge only at 405B, i.e. they carry distinct signal exactly in the small/quantized regime we care about. Source is ACL 2025 Main **and an Outstanding Paper**. Must land in the canonical library, not as an 11th bespoke scorer. **Confound to record**: the paper's leaderboard runs 32 open models at 4-bit against full-precision API arms — do not cite that table itself as quant-quality evidence. Known fragility: spaCy-lemmatization dependence (same class as the substring/comma brittleness we've been bitten by).
  - Owner: [`scoring-infra-standardization.md`](eval-tower-program.md#track-scoring-infra-standardization); consumers [`eval-tower-verification.md`](eval-tower-program.md), [`architect-model-selection-bench.md`](model-evaluation-queue.md).

- [x] ~~**ID-8 — FrontierCS floor probe (~10 problems, one production arm) before any harness spend.** arXiv **2512.15699**, 156 open-ended problems with per-problem evaluators, open-source. EV-9 records that our production suites sit at 90–94% and "cannot resolve" the top-2 models; `architect-model-selection-bench.md` just burned a cycle on `olympiadbench_numeric` returning a well-powered null (A1 89.3 / A3 88.0 / A4 89.3, all p ≥ 0.77). FrontierCS is maximally non-saturating (frontier ~29.4 vs human 95.41). **Symmetric risk, stated up front**: all published baselines are proprietary API models; our open-weight arms may land near zero, trading a saturation problem for an equally non-discriminative *floor* problem. The floor probe settles that cheaply. Also requires a sandboxed exec path we don't have (same blocker as LiveCodeBench).~~ (closed 2026-10-29 audit: DUPLICATE → same task as eval-tower-verification.md:660 (EV-9 FrontierCS ~10-problem floor probe, owner named in this box); keep :660)
  - Owner: [`eval-tower-verification.md`](eval-tower-program.md) (EV-9).

- **[declined: ws58 2026-11-03 content-review: curiosity; no named compression gap and the effort ladder (E-2) is the live instrument]** **ID-9 — Evaluate Behavior-Conditioned Inference as a Tier-1 reasoning-compression lever.** arXiv **2509.13237**: extract named procedural "behaviors" from our own successful traces, retrieve k into context; reports up to **46% output-token reduction at matched accuracy** — above conciseness prompting (37%) and Soft Thinking (22.4%). Zero-training, inference-time only. **Corrected**: the 46% is **"up to"**, output-tokens-only, with no accuracy figure at that operating point, and the **input-side cost is admitted but never measured** (`"involves a larger number of input tokens due to the inclusion of retrieved behaviors"`; **k=40** behaviors retrieved per query on AIME). Their defence — *"no autoregressive generation required on the input side"* — is a **GPU-prefill argument that inverts on our stack**. My earlier "worth more to EPYC than to the authors" framing is **unsupported until we measure our own prefill cost**; the paper cannot supply it. Best-instrumented paper in the sweep (5 seeds on MATH, 80 runs on AIME, production-style temp 0.6/top-p 0.95).
  - **Two mandatory guardrails**: behaviors are *model-extracted*, which is exactly the self-generated-artifact case SkillsBench (intake-096) shows net-negative (−1.3 pp avg, 16/84 tasks regress) → held-out validation gate required; and a behavior handbook is itself an accumulating store → build append-only with raw traces retained, per ID-4.
  - Score **total pipeline tokens** (retrieved-behavior prefill + decode), never decode alone.
  - Owner: [`reasoning-compression.md`](context-and-token-economy.md#track-reasoning-compression).

---

## P3 — Process defects found in our own governance

### Research Intake Update — 2026-10-04 (operator-approved Stage 4)

- [x] **ID-RI-PAST3-REVIEW — Investigate remaining intake blind spots and review the three preceding completed campaigns against current consumers.** ✅ 2026-10-04 — Parallel skill investigation followed by separate HipKittens, orchestration-prior-art and EXL3-throughput reviews; main checked original findings, approved mappings, current code and later owner rulings. Two operational omissions recovered as proposed tasks (LRC-RI-CONCURRENCY, EXL3-GRAPH-1), one existing-coverage enforcement refinement (INF03-REGAUDIT-RUNNER), and one bounded workflow proposal (ID-RI-COVERAGE-DELTA). [Evidence, inspected scopes and limitations](../../docs/reviews/research-intake-practical-applications-20261004.md). Selected-source retrospective only; no index-wide completeness/prevalence claim, implementation, inference or gate reopening.

- [x] **ID-RI-COVERAGE-DELTA — Preserve practical applications before ledger creation and through compression.** ✅ 2026-10-04 — Implemented after explicit operator approval. New Stage-3 plans require the v2 source-first opportunity scan, exact owner/task-text outcome reviews, plan-only actionable additions and full verbatim steering reconciliation. Stage 4 verifies reconciled identity and applied task/stub/index text. Same-ID refinements bind the incumbent line; proposed tasks cannot enter filing without an outcome mapping. Default index validation and historical unversioned/v1 Stage-4 handling remain unchanged. Main semantic review remains mandatory: no keyword grader claims usefulness or outcome equivalence. Seven bounded bad/preserved operational cases and mutation/refusal checks are in the existing regression suite; 73 tests and 218 subtests pass. [Implementation and verification](../../progress/2026-10/2026-10-04-intake-coverage-delta.md); [original scope](../../docs/reviews/research-intake-practical-applications-20261004.md). Installed Codex mirror updated; no application implementation, production activation or intake-corpus migration.

Approved scope and grounded audit: [decision-tools Stage 3 plan](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#cross-cutting--make-intake-compression-preserve-operational-opportunities). The audit traced four named campaigns, found three historical misses subsequently recovered, and found no new unresolved operational omission in that sample. It establishes no whole-index prevalence and reopens no historical application task. Record discussion: intake-335#record, intake-1225#record, intake-811#record, intake-1797#record, intake-1812#record.

- [x] **ID-RI-OPPORTUNITY-GATE — Review operational opportunities before primitive compression and validate proposed filing.** Amend the existing intake skill/reference/template to require each packet's current EPYC objective, pinned implementation gap, smallest useful operational change/probe, expected benefit direction, owner and exact execution conditions before choosing an enabling primitive. Require an explicit opportunity review for monitor/knowledge-only closures: nondeployment, missing full reproduction or HIGH/CRITICAL risk alone is insufficient. Preserve distinct operational follow-through when a source ledger separates it from wiring. Extend the existing validator/wrapper with an opt-in scoped plan/session check: validate proposed affected-entry payloads through existing enum/owner rules, resolve declared existing owners or proposed stub/index packages, and reconcile recommendation IDs to authoritative plan/task/trigger mappings. Machine checks establish structure and evidence-field presence, not truth or ROI; the main reviews those semantics. Align checkpoint cleanup with reconciled Stage-4 close-out, preserving steering/actionable state after Stage-1 ingestion. Keep legacy validation unchanged; no corpus migration, extra receipt layer, auto-grading policy or global backlog audit.
  ✅ 2026-10-04 — Implemented and main-reviewed. Focused/legacy suites: 25 tests and 29 subtests passed; default and opt-in checks passed for 1,895 entries. Exact metadata/source preservation and unchanged legacy validate_index source passed. Eight semantic dispositions, frozen baseline hashes and validation boundaries are retained in [Stage-4 progress](../../progress/2026-10/2026-10-04-intake-decision-tools-stage4.md). Structural conformance only, not improved ROI or deployment evidence.

**Acceptance.** Freeze eight mutation fixtures and old skill/validator outputs: valid persisted index plus invalid proposed enum; wiring without ParEval's two operational mappings; nonexistent integrated owner; historical GEPA defect versus current fulfilled implementation; stale PAW availability versus existing artifacts and completed TD-21 repair; closures based only on nondeployment or graph risk; sidecar permission versus a genuine inference gate; and Stage-1 completion versus Stage-4 cleanup. Retain each mechanical outcome and main-reviewed semantic disposition, including unsupported formats and disagreements. Independently prepared negative/mutation fixtures replace empirical holdout; every fixture must pass the applicable structural expectation and have resolved semantic review. Passing proves workflow conformance, not improved research ROI. Historical examples are regression fixtures, not reopened application tasks. This audit is complete for the named sample; no new broad recovery campaign is recommended on its evidence.


- [x] **ID-10 — Guard the intake pipeline against companion-artifact conflation.** ✅ 2026-07-25 — IMPLEMENTED in `.claude/skills/research-intake/SKILL.md` (Stage-1 Phase-1 step 3: companion artifacts are DISTINCT sources; `duplicate` requires an exact `arxiv_id`/`url` collision) plus an anti-rationalization row. Also fixed the adjacent defect that caused the miss: Phase-1 step 2 now mandates an **unbounded** dedup sweep (the 2026-07-25 miss was a `head -20`-truncated grep). A companion **repo / weights collection / project page is a DISTINCT artifact** from its paper. The schema's dedup key is an exact `arxiv_id` or `url` match; being *referenced in another entry's notes* is not a collision. `intake-335` (github.com/gepa-ai/gepa) was filed 2026-04-12 as "Duplicate — the GEPA paper already references this repo in its notes" — nobody read the codebase, and it hid ID-1 for ~3.5 months. A detector over the index found **19 entries** with this shape (7 high-relevance). Add the rule to the research-intake skill's dedup step and Anti-Rationalization table.
  - Owner: `.claude/skills/research-intake/SKILL.md` + [`knowledge-base-governance-improvements.md`](knowledge-base-governance-improvements.md).

- [x] **ID-10b — NEW: forbid unverified Stage-1 specifics in handoff task text.** ✅ 2026-07-25 — IMPLEMENTED as a typed lifecycle, not just prose: entries persist with `verification: stage1-unverified`, only a Stage-2 dive promotes to `dive-verified`, and a Stage-3 plan-completeness gate blocks any plan quoting an unverified number/metric/mechanism. Sub-agent prompts now carry an explicit do-not-invent instruction. A cross-contamination check was added after the CORE ablation was found cross-pasted into an unrelated entry. Documented in `references/intake-schema.md` § Verification lifecycle. Two **fabricated citations** reached the intake index from Stage-1 agent summaries in this sweep and were only caught by the Stage-2a dives: (a) a CORE ablation `0.268/0.234/0.227/0.203` that **does not exist** in arXiv 2605.28742 (real: `0.907/0.830/0.780/0.617`, Matchstick-only, 10-example regime, n=3) — and which had additionally been **cross-pasted into intake-895**, an unrelated paper; (b) a four-step `/doctor` behaviour (dedupe / trim / migrate / report-before-changing) that appears **nowhere** in the source, which contains two generic sentences. Rule: any **number, quoted metric, or named mechanism** entering a handoff task must be dive-verified against primary source. Add the anti-rationalization row to the skill.
  - Owner: `.claude/skills/research-intake/SKILL.md`.

- [x] **ID-10c — NEW: "absent from an index page" is not evidence of nonexistence.** ✅ 2026-07-25 — IMPLEMENTED in the Stage-1 Tier-2b guidance: a bounded search yields a **provisional** negative only, recorded as `unverified-in-stage1` for a dive to settle, with both 2026-07-25 false negatives cited as the motivating cases. Anti-rationalization row added. Two sources were reported unlocatable that demonstrably exist: the Letta trajectory post (**HTTP 200**, simply unlinked from the 26-post blog index) and the gepa omni post (**HTTP 200**, 121,877 B — the sweep had queried *frontier-cs.org*, the benchmark's site, instead of *gepa-ai.github.io*, the publisher's). Both false negatives nearly caused live sources to be quarantined. Add to the skill's Tier-2b guidance.
  - Owner: `.claude/skills/research-intake/SKILL.md`.

- [x] **ID-10d — NEW (found 2026-07-25 wrap-up): validate the intake skill's cross-reference map.** ✅ 2026-07-29 — `validate_intake.py` now parses only Category→File Mapping Markdown rows and requires every listed `.md` chapter, handoff, and experiment to resolve via configured paths; it correctly accepts both bare and `completed/` handoff forms while excluding the File Locations prose. The current 35 Markdown targets validate cleanly; regression tests cover active/completed resolution and a stable missing-target error.
  - Add a cheap path-resolution check (every ``` `name.md` ``` in the map resolves under `handoffs/active/`, `handoffs/completed/`, `docs/chapters/`, or `docs/experiments/`) to `scripts/validate/`, and consider wiring it into the wrap-up index-pruning step — archival is exactly when the map goes stale.
  - **Watch for the same failure shape in sibling reference data**: any other skill or doc that hardcodes `handoffs/active/` paths has the same silent-drift exposure. Not audited this session — scoped as part of this task, not assumed clean.
  - Owner: `.claude/skills/research-intake/` + [`knowledge-base-governance-improvements.md`](../completed/knowledge-base-governance-improvements.md) (note: that handoff is itself in `completed/` — one of the 10).

- [x] **ID-10e — Audit the sole non-dived intake entry (`intake-915`) for the intake-926 Stage-1 fabrication mode.** ✅ 2026-07-29 — Stage-2 audit promotes the row to `dive-verified`, not `dive-overturned`: its core claims are source-backed and it makes no empirical performance claim. Four scope corrections landed: the build123d workflow allows stated direct-STEP exceptions; named handoffs are conditional rather than universal; visual snapshot review is CAD-flow scoped; and the 10 geometric benchmark documents are specifications with negative checks, **not executable assertions or an imported scorer**. No downstream citation requires repair; a future EPYC geometry verifier remains new work.
  - Owner: `research/intake_index.yaml`.

- [x] **ID-11 — `handoffs_updated` is unreliable as an integration signal; the dashboard reads it.** ✅ 2026-08-05 — ROOT `4174b51db79cae55c5835e816fe75fa833696c13`; [native tests and source trace](../../artifacts/compute/codex3-id11-coverage-20261031/) (2 passed). [no-belief: source and test verification, no measurement]
  - 2026-10-31 prior-work hygiene only, **excluded from today’s code quota**. The work predates today; evidence filing or verification is not a new implementation. See [operator tick audit](../../artifacts/compute/codex3-tick-audit-20261031/tick-audit-20261031.md). [no-belief: quota-accounting correction]
  - Current wiki lint distinguishes cited entries with missing routing metadata from legacy entries needing disposition; an empty field is not proof of absent coverage. The current dashboard’s intake metric counts newly filed tasks from handoff history and does not read this field. No historical integration records were invented. Original finding: 49 entries are `relevance: high` + actionable verdict + empty `handoffs_updated`, but the field is simply not backfilled: the REAP cluster (intake-185…189) has an empty field while `handoffs/completed/reap-moe-expert-pruning.md` exists and cites them. Either backfill on Stage-2 execution (the skill already requires this) or stop treating the field as coverage. **Ruled out as a false alarm in the same audit**: the 105 "`already_integrated` with no key_claims" entries are 101× `discovered_via: seed` bootstrap corpus with bare `arXiv:NNNN` titles — correct behavior, not dropped value.
  - Owner: [`knowledge-base-governance-improvements.md`](knowledge-base-governance-improvements.md), [`project_handoff_dashboard_hub`](autopilot-program.md#track-autopilot-dashboard-fidelity-audit-2026-07-22).

- [x] **ID-12 — `agents/shared/ENGINEERING_STANDARDS.md:52` carries a stale duplicate of the kernel-immutability policy** ✅ 2026-08-12 (`auditor`, adjudicated LANDED-ELSEWHERE — work done, box never flipped): the stale duplicate was removed by `44382497` (2026-07-26, v8 reconcile) and the section restructured by `418cc44e` (2026-07-30, AFC-P6 dedup). Current text states the policy version-free and points at CLAUDE.md as canonical — exactly the state-it-once fix this row prescribes, so it can never go version-stale again. Verified at HEAD: zero `consolidated-*` occurrences in the file (unpiped grep, count 0). Original finding: still read `production-consolidated-v6`, future `-v7` after the 2026-07-20 v7 cutover. **Was addressed to the parallel v8 session** (policy surface, owned by the cutover).
  - Owner: [`agent-file-prose-compression.md`](frontier-lab-automation.md#track-agent-file-prose-compression) + v8 cutover.

- [x] **ID-13 — Lossless structural de-duplication of the always-loaded governance surface.** `/workspace/CLAUDE.md` is 223 lines / 2,282 words / 18,080 chars (~4.5k tokens) always loaded. Four policies are stated 2–3×: kernel immutability (2×, one stale → ID-12), the four-repo map (3×), measurement policy (3× — constitution → digest → digest-of-digest), Operator Decision Requests (2×). Derivable-from-tree sections: "Governance Infrastructure" (L54-79), "Dependency Map" (L46-52), the GitNexus block (L198-223). **KEEP list** (high-value, must survive): symlink identity (L40-44), kernel immutability + motivating failure (L23-31), iqk IQ-quant caveat (L21), Process Management (L167-171). This is *deletion*, which is lossless and model-independent — explicitly **not** the lossy prose compression that ID-6 gates. ✅ 2026-11-02 [belief: cc]
  - Owner: [`agent-file-prose-compression.md`](frontier-lab-automation.md#track-agent-file-prose-compression).

---

## P4 — Model/tool artifacts and operator-gated items

- [ ] **ID-14 — Fractal: containerized / disposable-host trial.** ✅ operator decision 2026-07-25 — **containerized trial approved; NOT on this host as configured.** Rationale: nodes run agents with permission prompts bypassed by default (Claude `bypassPermissions`, Codex `danger-full-access`, Grok `--always-approve`) and the per-node git worktree **isolates only the branch, not the filesystem or network** — while `/workspace/repos/*` and `/mnt/raid0/llm/*` are the same physical trees and live llama-servers + autopilot are running. **Corrections**: the repo has **108 test files / 91 `test_*.py`, not 68** (ratio argument gets stronger); the blog **does** carry cost and wall-clock figures (`run 41m $23.87/$300.00`) but **in an illustrative TUI screenshot, not attributed to the 187-node run**; and a math-problem control does exist ("matched it ten for ten") — acknowledge it. Cite the project's **own front-page `[!WARNING]`** rather than asserting the hazard ourselves; their docs also state *"Cost is recorded, never estimated. A step whose backend reported no figure stores no cost"*, which is what makes the budget go slack locally. Extract the containment design regardless: budget aggregation up the node tree, a reserve tranche withheld for cleanup, drain-at-iteration-boundary, and the `scope` flag limiting which subdirectories a node may commit to. **Note**: its USD budget caps go slack against a local llama-server that reports no vendor spend — a non-USD cost basis (GPU-seconds or wall-clock) is required before local use.
  - Free integration fact: `--agent=opencode` reaches the Orch via `opencode.json` `options.baseURL` — the surface HS-1c already audited — so local-model operation needs no fork of either project.
  - 2026-11-02: [disposable-host containment design](../../docs/design/fractal-disposable-host-trial.md) specifies proposed isolation, non-USD budgets, drain, and acceptance checks. No environment or controls have been validated and no trial has run. [no-belief: design only]
  - Owner: [`mi210-kernel-rnd-loop-proposal.md`](../completed/mi210-kernel-rnd-loop-proposal.md) (historical containment design), [`agent-collab-rnd-harness.md`](autokernel-loop.md#track-agent-collab-rnd-harness) (mechanism comparison), [`harness-selection-and-integration.md`](harness-program.md#track-harness-selection-and-integration) (record as outer-loop driver, **not** an HS-4 candidate).

- [x] ~~**ID-15 — Header-gate the DavidAU Qwen3.6-27B MTP GGUFs (no inference, one download).** The release publishes **every quant twice** (MTP / non-MTP) across ten tiers, and the MTP twin is larger by **exactly 451,320,768 bytes in all ten cases** — consistent with a fixed Q8_0 head on an identical body. Parse both GGUF headers and diff tensor lists to confirm real `nextn`/`mtp` tensors, Q8_0 precision, a `nextn_predict_layers`-style key, and tokenizer/vocab match with our registered `qwen36_27b_q4km`. **This gate is mandatory, not optional**: intake-777 (Qwable-v1) was a structurally similar Qwen3.6 ladder that had silently dropped every nextn/mtp tensor, caught only by a full header parse.~~ (closed 2026-10-29 audit: OBSOLETE → target is a Qwen3.6-27B MTP variant; Qwen3.6-27B artifacts replaced by Qwen3.8-27B (registry 2026-08-20 swap) and Qwen3.6-27B-MTP-f16-upcast / Qwen_Qwen3.6-27B-Q8_0 are in the deprecated_models graveyard)
  - **Relevance is asymmetric**: real on the MI210 (we hold a measured optimum — 53.1 t/s at `--spec-draft-n-max 4`, 1.82×), but the CPU plane is **architecturally foreclosed** (48 of 64 layers are Gated DeltaNet; the GDN verification wall measured 0.56× on the Qwen3.5 hybrid sibling). Record explicitly so "MTP" in a filename never reads as a reopen trigger for the parked CPU handoff.
  - Genuinely open question this instrument could answer: **does Heretic/ARA directional abliteration degrade a co-trained NEXTN head's acceptance rate?** We hold the vanilla control.
  - Owner: [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh); note-only in [`qwen36-27b-cpu-feasibility.md`](../archived/qwen36-27b-cpu-feasibility.md).

- [x] ~~**ID-16 — ThinkingCap: the MTP head is STOCK, confirmed at byte level. Rewrite the A/B accordingly.**~~ (closed 2026-10-29 audit: OBSOLETE → ThinkingCap-Qwen3.6-27B-GGUF deleted 2026-10-20 (model_registry.yaml deprecated_models, six-arm study complete); local Qwen3.6-27B-MTP-Q8_0 control also retired)
  - **Dive result (operator hypothesis, confirmed)**: the **entire 451 MB layer-64 block is byte-identical** to our local `Qwen3.6-27B-MTP-Q8_0.gguf` (single sha256 over the region), as are `token_embd.weight`, `output.weight` (the tied shared head) and `output_norm.weight`. A control tensor (`blk.32.ffn_gate`) genuinely differs, so the offset arithmetic is sound. The differing set is **exactly the 256 LoRA target modules** (q/k/v/o in the 16 full-attention layers + ffn_gate/up/down × 64), matching upstream `merge_verify_report.json` (LoRA r=64, α=128, merged at scaling 2.0) and an MTP shard named `model-base-aux.safetensors`. The −1,184 B file delta is **fully metadata**, exact to the byte.
  - **Consequence 1 — MTP is not a ThinkingCap feature.** We already hold that drafter. Hold the MTP path **constant** across arms; it is not a differentiator.
  - **Consequence 2 — genuine co-trained-head vs modified-trunk mismatch.** The head consumes a final hidden state from a trunk that has since had LoRA merged into every FFN. Predicted worst exactly where the finetune changed behaviour most: the early "keep thinking?" tokens.
  - **Consequence 3 — accept-length appears genuinely measured** (they report base-model rows on the same harness: 3.66/3.61 vs their 3.69/3.65) but is **statistically indistinguishable from base**, and the vision numbers are slightly *worse*. Spot-check the identical-to-three-digits MMLU-Pro value across three quants before relying on it.
  - **Consequence 4 — template difference.** ThinkingCap ships the **stock Qwen** template (7,764 B); **our local artifact carries Unsloth's patched variant** (8,057 B, developer-role + tool-calling fixes). Not a non-difference.
  - **Blocker — NO LICENSE declared** on the GGUF repo (unlike DavidAU's apache-2.0). Gates registry admission.
  - **Hazard — our two local Q4_K_M artifacts are not a clean A/B pair**: `Qwen3.6-27B-MTP-Q4_K_M.gguf` (17,106,773,120 B, 866 tensors) is **smaller** than `Qwen_Qwen3.6-27B-Q4_K_M.gguf` (17,533,552,192 B, 851 tensors) — 15 extra tensors yet smaller, so different recipes. Any Q4_K_M MTP-vs-non-MTP benchmark on those two is **confounded**.
  - **The comparison that still matters** (in neither the source nor our bench): ThinkingCap `enable_thinking=true` vs stock Qwen3.6-27B `enable_thinking=false` — our incumbent config, since both registry rows set `disable_thinking: true`.
  - Owner: [`architect-model-selection-bench.md`](model-evaluation-queue.md).

- **[declined: ws58 2026-11-03 content-review: era-stale (v8 IQ arms)]** **ID-17 — Offer a graded quant-quality instruction-following probe to the v8 IQ-quant arms.** `tq3-quantization-evaluation.md:151` currently gates on a single binary prompt ("exactly six lowercase words"). ID-7's ordered-coverage verifier gives a graded 0-100% curve instead of a flipped bit, and the source paper ran **all 36 open models at 4-bit**, so the metric is known to behave under quantization. **Addressed to the parallel v8 session.**
  - Owner: [`tq3-quantization-evaluation.md`](quantization-and-low-bit.md#track-tq3-quantization-evaluation) ← coordinate with the v8 session.

- **[declined: ws58 2026-11-03 content-review: no consumer names a per-query cost decision; knowledge-pipelines owns retrieval instruments]** **ID-18 — PageIndex: complement, not competitor — and gate on measured per-query cost.** Right instrument for "where inside this 200-page PDF", wrong one for "which of 577 markdown files" (it has **no cross-document retrieval primitive** — `get_document(doc_id)` presupposes you know the document). **Independent evaluation: 9.6-minute average query, and 9 of 16 queries TIMED OUT at 10 minutes** (7 completed — my earlier report had this inverted). **The "RTX 5090" attribution is unsourced**; the measured setup was **Qwen3-32B via Ollama**, 18 docs / 85 nodes. **Two LLM transports, not one**: build path via litellm (confirmed), but the retrieval demo uses the **OpenAI Agents SDK**. **No global bound** on per-query LLM calls; O(N) per document (18 docs ~9.6 min → 500 ~4.4 h → 10k ~3.5 days). **Do not over-claim**: the same author's follow-up halves query time with parallel execution and gets *better* recall with a *smaller* model, so 9.6 min is a default-config worst case, not a floor. Its 98.7% FinanceBench figure belongs to **Mafin 2.5, VectifyAI's commercial product in a different repo** — quarantine it. Separately, BM25 beats dense retrieval on financial text-and-table docs (arXiv 2604.01733), so the baseline it must beat is hybrid, not embeddings.
  - Worth taking regardless of adoption: its build-time injection hardening (regex redaction, `<user_document>` delimiter framing, and **deterministic post-hoc validation nullifying any LLM-emitted page index outside the real range**) is a reference implementation for the open document-body injection policy.
  - Owner: [`internal-kb-rag.md`](knowledge-pipelines.md), [`opendataloader-pipeline-integration.md`](knowledge-pipelines.md#track-opendataloader-pipeline-integration).

- [x] **ID-19 — Letta `trajectory`: DOWNGRADED from `adopt_component` — there is no artifact to adopt. Port ~50 lines instead.** `letta-trajectory` is **not on PyPI** (404; `release.yml` runs `npm publish` only and never builds a Python artifact), and the Python package is a **subprocess shim to a vendored Node 20 CLI** (`_MINIMUM_NODE_MAJOR = 20`, `_vendor/trajectory-cli.mjs`) whose Node dependency is **undeclared** — `pip install` succeeds, then fails at first call. Disqualifying under minimum-imports. **My Hermes suspicion was wrong**: the adapter targets *our* Hermes (NousResearch/hermes-agent, verified against `hermes_state.py`) and is a **~50-line SQLite read, reimplementable in Python without Node** — that is the valuable piece. The no-measurement-fields negative is **structurally enforced** (`additionalProperties: false` on all five `$defs`), so ruling it out for the reviewer trace store is correct in the strongest form. Original framing retained below for context: F1 W2b hand-rolled that importer (2,558 JSONL paths, bespoke sidechain detection); this library is differentially parity-checked against a production reference on 1,050 real sessions (1,043/1,043 outcomes matched, 902/903 byte-exact). **Gates**: parity-or-better on eligible-row recovery; existing privacy scans still pass; and resolve whether the Python package is pure-Python or shells out to its vendored `_vendor/*.mjs` Node bundle (minimum-imports policy). <!-- evidence-integrity: APP `0ffc55ece5fa64e3481eeb2520a94ec0feebed1a`; test: epyc-orchestrator/tests/unit/test_hermes_reader.py; artifact: artifacts/compute/refactor-id19-hermes-reader-20261031/EVIDENCE.json; ✅ 2026-10-31; [no-belief: private read projection lacks measurement warrant; code/privacy conformance only] -->
  - **Clean negative worth recording**: `trajectory-v1` carries no tokens, latency, cost, outcome/reward, phase tag, or executor-model-id, and truncates tool results by default — so it **cannot** serve the reviewer trace store (TM-3/TM-8). Record the fidelity-tier boundary: lossless measurement-grade source-of-record vs lossy agent-readable projection that must never be written back or cited in a decision-gating number.
  - Owner: [`frontier-f1-real-task-corpus.md`](../completed/frontier-f1-real-task-corpus.md), [`unified-trace-memory-service.md`](memory-program.md#track-unified-trace-memory-service), [`reviewer-trace-materialization.md`](../completed/reviewer-trace-materialization.md).

  <!-- task-evidence-integrity:start ID-19 -->
  - Evidence metadata: APP `0ffc55ece5fa64e3481eeb2520a94ec0feebed1a` → main `3f9ac2715720958c1eacd033b53fb01cd2b336da`; [committed source/parity/privacy evidence](../../artifacts/compute/refactor-id19-hermes-reader-20261031/EVIDENCE.json). This completes the Python SQLite **session/messages envelope read port**, not the full Node normalizer or a package adoption. The pinned upstream Python client still shells out to Node20+; shipped reader/exporter/tests require no Node runtime. No production ingest, measurement-grade capture or runtime deployment is claimed.
  - Actual private differential:5 sessions/10 rows;3 upstream-eligible sessions have14 normalized records exactly equal on native-SQL and Python-projected inputs. The other2 preserve the same upstream `missing_user_records` refusal and are not eligible successes. Two public upstream fixture pairs match expected records, and a deliberate reasoning/tool-loss negative is detected by the actual pinned reference. This is the small available local corpus, not the upstream1050-session study. Private text/IDs/raw outputs remain protected and are absent from Git.
  - Fresh-main qualification:12 tests, actual `make gates`, Ruff lint/format and staged privacy pass; the active credential-shaped negative refuses. Three formatting-only changes preserve executable ASTs; non-Python approved bytes are unchanged. The projection omits tokens/latency/cost/outcome/phase/executor-build warrant and must never replace the native source of record or gate a decision. [no-belief: private read projection lacks measurement warrant; code/privacy conformance only]
  <!-- task-evidence-integrity:end ID-19 -->

- **[declined: ws58 2026-11-03 content-review: the bridge is declined by its own text and the "GPU-free half" is unnamed]** **ID-20 — TRL + OpenEnv: DECLINE the bridge; keep only the GPU-free half.** **The blocker is not the token key — it is the absent control plane.** `vllm_client.py` requires seven non-OpenAI endpoints (`/get_world_size`, `/pause`, `/resume`, `/init_weight_transfer_engine`, `/start_weight_update`, `/update_weights`, `/finish_weight_update`); a full sweep of `tools/server/*.cpp` returns **zero**, and `weight_transfer.py:25` hard-imports the vLLM NCCL engine. llama.cpp could only ever be a **frozen off-policy sampler**, which defeats AsyncGRPO's premise. **My proposed one-line alias was also buggy**: `entry.get("token_id") or entry.get("id")` is truthiness-based and **token id 0 is valid and falsy**, silently desyncing `completion_token_ids` from `per_token_logps`. Logprob semantics also mismatch (llama.cpp `"prob"`/`"logprob"` ≠ vLLM `processed_logprobs`). `black_box` mode needs no logprobs and the rollout worker runs **CPU-only by design** (`CUDA_VISIBLE_DEVICES=""`), so the sandbox + agent + held-out verifier + trace-capture substrate is runnable here today and yields verified agent trajectories with programmatic rewards. **Near-free bridge**: OpenEnv's interception proxy reads `entry.get("token_id")` (vLLM's key) while our v7 server emits the same value under `"id"` (`tools/server/server-task.cpp:298,316` — verified) — a one-line alias makes llama.cpp a compatible trace-capture endpoint.
  - **Blocked, not dismissed**: AsyncGRPO requires vLLM server and trainer on **separate GPUs** (we have one MI210, no gfx90a partitioning), vLLM ≥ 0.22.0 + transformers ≥ 5.2.0, FSDP2-only, NCCL weight transfer, and **no PEFT/LoRA path** — full-parameter FT only. Operator decision, framed in the source entry.
  - Also a decision input for HS-4: **OpenCode is the only harness candidate with a first-party trainable adapter**; Hermes would require authoring the whole ResourceSession + proxy + sandbox layer.
  - Owner: [`harness-selection-and-integration.md`](harness-program.md#track-harness-selection-and-integration), [`tool-use-eval-contract.md`](benchmark-suites.md#track-tool-use-eval-contract), [`agent-world-env-synthesis.md`](benchmark-suites.md#track-agent-world-env-synthesis).
  - 2026-11-02 operator decision: Decline the bridge; keep the GPU-free half (decisions-batch2-4-20261102.json)

---

## P1b — DFlash: a blocker that is factually dead, and two unmeasured production-role drafters

The highest-value result of the conflation audit. Three entries (`intake-296/297/298`) were filed `already_integrated` as "supplementary to the paper" and never opened. **All verified on disk this session.**

- [x] **ID-28 — Retire the "DFlash has no llama.cpp support / no GGUF / no CPU path" blocker. ✅ 2026-07-29** Verified: upstream merged DFlash **2026-06-28** (`d1b34251b`, PR #22105); we forward-ported it to **production** on 2026-07-18 (`ed4091266 Forward-port DFlash and quantization fixes`); `src/models/dflash.cpp` is present on `production-consolidated-v7`; `draft-dflash` is wired into `common/speculative.cpp`, `docs/speculative.md`, and the server README; and a converted **`Qwen3.6-27B-DFlash-f16.gguf` (8,558,077,216 B) has been on disk since 2026-07-03**. The live global claims were corrected in `wiki/ssm-hybrid.md` and `research/deep-dives/lucebox-hub-consumer-gpu-dflash.md`, and the historical vLLM-only benchmark was clarified in `gpu-acceleration-path.md`; the CPU no-go remains acceptance/Delta-Net verification economics, not an availability claim.
  - Owner: [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh), [`inference-research-index.md`](inference-research-index.md).

- [x] ~~**ID-29 — Measure `z-lab/gemma-4-26B-A4B-it-DFlash` (0.43B, Apache-2.0) against the live worker_general target.** The collection grew from ~4 drafters at filing time to **22**, and now covers two roles the March DFlash handoff explicitly recorded as *"GAP — needs custom training"*. This one is the strongest candidate: the target is a **pure MoE with no Delta Net recurrence**, so it avoids the recurrent verification wall; and the **incumbent native-MTP drafter is already measured NOT VIABLE** (58.7% acceptance, 1.06×) — a low bar to clear. Never measured.~~ (closed 2026-10-29 audit: OBSOLETE → worker_general gemma-4-26B-A4B-it retired (graveyard row in model_registry.yaml deprecated_models; worker now different); target/drafter measurement has no live target)
  - **Precondition**: target weights must be the same `google/gemma-4-26B-A4B-it` that produced the ORIG Q4_K_M GGUF — conditioning hidden states are target-specific.
  - Report against the L-6 acceptance floor; **do not register in the production stack before the floor passes**.
  - Owner: [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh).

- [x] **ID-30 — Record `z-lab/Qwen3.5-122B-A10B-DFlash` (Apache-2.0) as a watch item for the live architect_general target.** ✅ 2026-07-29 — acceptance-only scope is recorded in the owning [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh); no duplicate record needed. The target currently self-drafts via native NEXTN MTP. Scope an **acceptance-only** comparison before any port effort, per the standing measure-α-before-spec-dec-investment gate.
  - Owner: [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh).

- [x] **ID-31 — Correct two documentation errors that bias the DFlash reopen decision.** ✅ 2026-07-25 — DONE, and the scope was wrong in two ways worth recording. (a) The "iterative denoising" error is **not in any chapter** — chapters never mention denoising. It is in TWO **completed handoffs**: `completed/dflash-block-diffusion-speculation.md:30` (which already carried a contradicting "CRITICAL CORRECTION — NOT iterative denoising, single-pass" further down the same file, so the top-of-file summary was teaching the wrong cost model to anyone who stopped reading early) and `completed/tree-speculation-numa-drafting.md:1178` (whose tree-builder rationale depended on harvesting candidates from "different denoising trajectories" that do not exist). Both struck with forward-pointers. (b) A **third** stale claim sat on the same chapter line and is now fixed: Nemotron-Diffusion "not yet ported to llama.cpp" — the `dream` loader was fixed 2026-07-18, a 14B Q8_0 GGUF has been on disk since 2026-07-10, and the live blocker is content control (`gpu-acceleration-path.md` task 517), not loading. Original findings, both verified:
  - `10-advanced-speculative-decoding.md:699` states DFlash *"was killed by Q4_K_M hidden-state degradation on **hybrid-SSM targets**"* — but the March NO-GO was measured on **Qwen3-Coder-30B-A3B, a pure MoE with no recurrence**. This makes an architecture-general result look architecture-specific.
  - The completed handoff and downstream chapter text describe DFlash as **iteratively denoising over T=8–16 steps**. It is **single-pass** — the drafter weights contain no timestep tensors. This overstates drafting cost, which is precisely the term deciding whether the technique can pay for itself on bandwidth-bound CPU decode.
  - Chapter edits need operator approval — flagging, not editing.

- [x] **ID-32 — The quant-noise root cause is weaker than our docs assert.** ✅ 2026-07-29 — corrected the live DFlash acceptance gate to label target-side quant noise as a hypothesis, not an established root cause. Every current DFlash deferral rests on "target-side quant noise in the conditioning hidden states; only a near-lossless target reopens it." But the Laguna measurement moved acceptance only **17.2% (q4) → 19.0% (q8)** — a small delta for a large precision change. This does not falsify the theory (BF16/F16 targets remain untested) but it should stop being treated as established.
  - Owner: [`laguna-s21-cpu-port.md`](kernel-champion-and-promotion.md#track-laguna-s21-cpu-port) ← **parallel v8 session holds uncommitted edits here; coordinate.**

- [x] **ID-33 — Re-triage the stale registry forbid.** ✅ 2026-07-29 — `dflash_qwen36_27b_f16_local` lives in the synchronized full model registries (research `model_registry.yaml` and orchestrator `model_registry_full.yaml`), not the capability registry. Removed only `benchmark_claim_without_dflash_runtime`: the runtime is available. Retained `production_stack_registration`; the row is now explicitly `runtime_available_acceptance_benchmark_gated`, with target-compatibility preflight and operator-approved acceptance evidence required before any registration or claim.
  - Owner correction: [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh) owns the acceptance gate; the capability registry remains unaffected.

- [x] **ID-34 — Architecture fact, settled from weights and code (record it so it stops being re-derived).** ✅ 2026-07-29 — recorded in the owning [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh) DFlash intake integration; no duplicate source-record edit needed. DFlash drafters are **headless and non-causal**: 58 tensors (5 layers × 11 + `fc` + `hidden_norm` + `norm`), **no `embed_tokens`, no `lm_head`**, `is_causal=False`, input is a block of `mask_token_id` embeddings. They are **inert as `--model-draft`** and live only under `-md` + `--spec-type draft-dflash` after conversion with `--target-model-dir`. `fc.weight` is `[hidden, n_taps*hidden]`, so every drafter is **target-locked** — there is no generic drafter. Also: the reference repo has **zero tests and zero CI**, has been dormant since 2026-05-10 with 85 open issues, and contains **no custom CUDA kernels** (a complete MLX backend exists) — which falsifies the original "block diffusion is fundamentally GPU-oriented" justification. Treat as `adopt_patterns` reference semantics only; take no dependency.
  - Published speedups must carry provenance: 6.17× MATH-500 / 5.91× AIME24 / 5.85× AIME25 are **Qwen3-8B, greedy temp 0, hardware unstated, measured against naive autoregressive decode at concurrency 1** — a naive baseline, unusable for comparison against a stack whose incumbent is native MTP. Code/agentic suites are **2.27×–5.43×**, roughly half the headline.
  - Owner: [`laguna-s21-cpu-port.md`](kernel-champion-and-promotion.md#track-laguna-s21-cpu-port) (L-2 encoder input width), [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh).

---

## P3b — Conflation-audit outcomes (re-read of mis-filed entries)

Operator-authorized 2026-07-25. Honest scorecard so far: **2 of 6 re-read entries were correctly filed** (recording that is the point of the exercise), **1 had a wrong label but a correct outcome**, and **3 dropped real content** — one of them the single most EPYC-decisive finding in the RLM corpus.

- [x] **ID-21 — `intake-803` (Prime Intellect RLM) was materially mis-filed: it kept the promotional half and dropped every negative.** ✅ 2026-07-29 — recovered as a dated `dive_corrections` append, preserving the historical filing. Recovered content, none of which is anywhere else in the corpus:
  - **PREFILL→DECODE CONVERSION** — the post states that in Needle-in-Haystack the plain LLM's tokens are almost entirely *prefill* while the RLM's are largely *decode*, because the RLM writes code to solve **and** writes code again to emit its answer. RLM structurally converts compute-bound prefill into **bandwidth-bound decode** — directionally adverse on this box, where decode is BW-exhausted and prefill is compute-bound and iqk-accelerated. **This is the strongest evidence in our corpus that naive RLM fan-out is a bad trade specifically on EPYC**, and it was dropped.
  - *"In all cases, the RLM increases the time required to finish the job significantly"* — a **universal wall-clock regression** across all four environments. No trace of it in the entry.
  - Mechanism constants: recursion depth is **exactly 1**; REPL output to the root capped at **8192 chars/turn** (the forcing function that makes the model use Python); **120 s** per-REPL-call timeout (ablated at 300/600 s, no benefit); tools bound to **sub-LLMs only**, never the root, deliberately because tools emit many tokens; termination is a **state variable** (`answer['ready']`), not a token — enabling answer-by-diffusion.
  - The **biggest win used ZERO sub-LLM calls**: on Oolong synth-with-labels the RLM scored perfectly at every context length using *regular expressions* over the context variable. The value came from deterministic Python over data-by-reference, not from recursion.
  - A portable metric: **Main Model Token Efficiency** = mean reward / mean main-model trajectory tokens, normalized to the no-scaffold arm — exactly the metric that catches a scaffold "winning" by relocating cost onto sub-calls rather than reducing it.
  - **Two propagated rows are misleading and should be corrected in place**: the DeepDive "almost a doubling" is **GLM-4.6-only** and *reverses* under tips, while the primary model (GPT-5-mini) was **worse** with RLM without tips; and the Oolong "large margin" holds only on the `real` subset — on `synth` the RLM is worse — with part of the aggregate win an **API-rejection artifact the post itself flags** (over-long prompts rejected for the plain LLM, counted as zero tokens).
  - **Evidence grade**: the post contains **no numeric tables at all** — every result is a plot image. n=50 prompts × **1 rollout**, single shared seed, untuned defaults, no CIs. Observation-grade; gates nothing.
  - Owner: [`repl-turn-efficiency.md`](harness-program.md#track-repl-turn-efficiency), [`context-folding-progressive.md`](context-and-token-economy.md).

- [x] **ID-22 — `intake-537` (RLM deep-dive) ships a portable artifact the filing said didn't exist.** ✅ 2026-07-29 — recovered as a dated intake correction. Filed as "no new code beyond pointing at the repo", but it reproduces a **complete open-source-hardened RLM system prompt** (tuned on Minimax-M2.7 and GLM-5.1 — the only RLM prompt in the corpus tuned for *open-weight* drivers, which is all we can serve) plus concrete partitioning constants absent from the index: ~100K-char sub-agent budget, 10-way chunking, ~200-word REPL print truncation, >500K-char recursion threshold. It also instructs sub-agents to return a **verbatim slice rather than generate a summary** — an explicit decode-suppression move, the right direction here. This is the same artifact class `repl-turn-efficiency.md` already **promoted** from intake-867 (SkyRL child prompt).
  - **Unrecorded edge**: the author *is* the fast-rlm author and links the repo in-body — so `intake-537` is `intake-783`'s design rationale. That is why intake-783 sits at `relevance: high` with zero attached handoffs: the edge was never written down, not because the work is unowned.
  - **Falsifiable contradiction worth measuring**: it claims sub-agent calls hit KV cache ~90% of the time (static system prompt, append-only transcript), while `repl-turn-efficiency.md:82` records that the RLM scaffold shares no prefix. Both can hold — root turns cache-hostile, sub-agent turns cache-friendly. Measure separately via llama-server `/slots` hit rate; it changes where fan-out is worth paying for.
  - Owner: [`repl-turn-efficiency.md`](harness-program.md#track-repl-turn-efficiency).

- [x] **ID-23 — Neither RLM entry references the live handoff.** ✅ 2026-07-29 — `intake-153` and `intake-154` now point to [`repl-turn-efficiency.md`](harness-program.md#track-repl-turn-efficiency); `intake-803` already records its independent Prime Intellect/verifiers lineage and shared arXiv ancestor only. Both had pointed at `handoffs/completed/` targets (`rlm-orchestrator-roadmap.md` was **archived 2026-03-29**); the actual live RLM-mechanism handoff is [`repl-turn-efficiency.md`](harness-program.md#track-repl-turn-efficiency). Re-point them. Also: `intake-803` is **not** related to fast-rlm — it is an independent reimplementation inside `verifiers`; the two merely share the arXiv 2512.24601 ancestor. Record that so the lineages stop being conflated.

- [x] **ID-24 — `intake-578` (Nemotron-Diffusion HF collection): its one original fact is now backwards.** ✅ 2026-07-29 — recorded as a dated `dive_corrections` append, preserving the 2026-05-20 source snapshot. The entry's load-bearing claim is "BF16-only / no GGUF / no llama.cpp support" — a correct 2026-05-20 snapshot that has since reversed. A 14B Q8_0 GGUF has been on this host since **2026-07-10** (`/mnt/raid0/llm/models/Nemotron-Labs-Diffusion-14B-Q8_0-GGUF/`), and the experimental-v7 `dream` loader was fixed **2026-07-18** (`test-llama-archs --arch dream` passes; `llama-diffusion-cli` exits 0). Measured: MI210 `pp512 1700.42` / `tg512 69.05`; CPU-only `pp512 157.57` / `tg256 2.69`. The real blocker is **content control, not loading** — `examples/diffusion/diffusion.cpp` uses its own sampler chain and ignores `--grammar`/`-j`, scoring 0/4 on strict-JSON/GBNF/schema-const/line-copy (`gpu-acceleration-path.md` task 517, still open). A reader hitting intake-578 alone would conclude "not runnable here" and be wrong. Re-checked upstream 2026-07-25: still 7 BF16 repos, so our GGUF is third-party/local, not an NVIDIA release.
  - Owner: [`gpu-acceleration-path.md`](../completed/mi210-serving-program.md#track-gpu-acceleration-path) (already owns this; index hygiene only).

- **[declined: ws58 2026-11-03 content-review: intake bookkeeping]** **ID-25 — Index-hygiene fixes surfaced by the audit** (cheap, one-line each):
  - `intake-577`/`intake-578`: change `verdict: superseded` → `already_integrated`, and copy the intake-576 pointer out of `verdict_justification` into the empty `notes:` field. **The audit's premise here was a field-lookup error on my side** — the successor *was* named, just not in `notes:`. But `superseded` is a technique-displacement verb in the rubric, and this was record-level dedup, which is why it read as unfalsifiable. Checked for a genuine successor: intake-751/752 (Nemotron-TwoTower) was already adjudicated **distinct**.
  - **Operator-review candidate** (derived from our own prior filing, not an external directive): `intake-804` recorded a follow-up 14 days ago that was never actioned — backfill `arxiv_id: 2607.05391` and the 9-author list onto intake-362#record / intake-363#record, and add RoboRewardBench 87.4 / MedAgentBench 73.3.
  - Record the `intake-783` ↔ `intake-537` edge (ID-22).
  - 2026-11-02 operator decision: Backfill (decisions-batch2-4-20261102.json)

- [x] **ID-26 — Two entries CONFIRMED correctly filed; closing with no action.** ✅ 2026-07-25
  - `intake-804` (LLM-as-a-Verifier) is a **true duplicate**: v2 is 23.5 h after v1 with a ~5 KB delta and no changelog, so there is no v2-specific content to recover. Genuinely integrated — `eval-tower-verification.md` doesn't merely cite it, it *rebuts* the paper's k=20 logprob-truncation caveat with llama.cpp source (`get_token_probabilities()`, full-vocab softmax, no truncation).
  - `intake-881` (FOD#159) is **pure aggregation, zero primary content** — and should not have been flagged: the entry already carries a dated Stage-2 self-correction that walked back its own over-claim and filed two real gaps.

- [x] **ID-27 — One substantive gap the `intake-804` re-read found** ✅ 2026-07-29 — linked into [`reviewer-calibration-accounting.md`](reviewer-control-plane.md#track-reviewer-calibration-accounting) as a candidate continuous logit-expectation confidence source, with reciprocal intake metadata. The record keeps typed decisions and current calibration accounting unchanged: this is an evaluation input, not a re-verdict, threshold change, metric claim, or reviewer promotion.
  - Owner: [`reviewer-calibration-accounting.md`](reviewer-control-plane.md#track-reviewer-calibration-accounting).

- [x] **ID-35 — A false claim from `intake-580` is load-bearing in two active handoffs; correct it.** ✅ 2026-08-12 (verified by `mainB` subagent — **the correction landed 2026-07-29 and this box was never flipped**; every clause of this row is now discharged, so it is closed as a completion record). Both quotes are struck through in place with a dated `CORRECTED 2026-07-25 (intake Stage-2a dive)` note: `internal-kb-rag.md:221` and `opendataloader-pipeline-integration.md:528` — **the line anchors in this row have rotted** (`:211` is now a Mirage `FORMAT_VERSION` pattern, `:500` an intake-449 entry), which is why they are restated here by text. Read from a ref, not the working tree: both corrections are present in `HEAD`, and `git log -S` dates the symbol rather than the file — epyc-root `c942728e` ("research-intake sweep + Stage-2a dives: 2 fabrications caught"). The three secondary clauses also landed the same day, each with its own closed box: RC boundary corruption (`opendataloader-pipeline-integration.md:656`, RC=99.0 excluded from Phase 2/3 quality design), DCC-only re-scope with the SC/BI saturation evidence (`internal-kb-rag.md:527`), and the offset-provenance prerequisite (`internal-kb-rag.md:528`).
  - One uncorrected sibling, left deliberately: `opendataloader-pipeline-integration.md:521` still reads "the framework is chunker-agnostic, so additional candidates … can be slotted in". That is a claim about the **paper's method**, not about a code ABC in the shipped library, so it is not an instance of the refuted claim — flagged here so the next reader does not re-report it as a miss. The filing's headline engineering claim — *"modular chunker ABC… a custom chunker can be slotted in"* — is **false**. Verified: the only `ABC` in `ekimetrics/adaptive-chunking` is `BaseParser` (PDF/Excel parsers); the five chunkers share no base class, no interface, no registry. The claim is quoted verbatim at **`internal-kb-rag.md:211`** and **`opendataloader-pipeline-integration.md:500`**, and the "slot our chunker in" plans in both rest on it. Re-cost: slotting in means writing our own harness, at which point the repo buys nothing.
  - Also missed: **the shipped library does not implement the paper's method** — `find_best_method`/`output_best_chunks` live only in the `paper/` reproduction subpackage and read two on-disk parquet files; the public API is a plain `RecursiveSplitter`. And the **RC metric carried a silent boundary-corruption bug** (`str.find()` returns `-1` rather than raising, so an unlocatable chunk yielded `start_idx=-1` and corrupted every downstream reference boundary) from first release 2026-03-26 until `649ece1` on 2026-07-06 — **spanning the paper's entire publication window**. RC is the column reported at 99.0. Treat it as unverified.
  - **Both original trigger conditions already fired**: the entry deferred action to "when ODL Phase-2 chunker work begins OR when internal-kb-rag K2 leaves stub" — K2 was certified 2026-06-13 (577 files / 18,010 chunks) and ODL heading-chunking landed 2026-06-21. The entry has been waiting for events that already happened.
  - **Independent corpus measurement** (agent ran the library on 40 of our own active handoff docs — CPU only, no LLM/GPU/network, 0.04 s): **SC saturates at exactly 1.000** and **BI at 0.953–0.982**, so two of the five metrics cannot discriminate chunker variants on markdown. That shrinks the proposal from "lift the 5-metric suite" to **"reimplement DCC (~150–250 LOC) against our existing ColBERT/BGE encoder"** — the one metric with discriminative range, no copyleft dependency, and no soundness question.
  - **Unrecorded prerequisite that dominates the effort estimate**: the metrics are **offset-based**, requiring chunks to be exact substrings of `full_text`. Our `markdown_chunker.py` prepends heading breadcrumbs, so our chunks are **not** verbatim substrings. Raw-source-offset provenance is a precondition for any offset-based metric and appears in no handoff.
  - Owner: [`internal-kb-rag.md`](knowledge-pipelines.md), [`opendataloader-pipeline-integration.md`](knowledge-pipelines.md#track-opendataloader-pipeline-integration).

- [x] **ID-36 — `intake-364` (Firecrawl): right decision, wrong label — and `not_applicable` is the one verdict our policy says must never be casual.** ✅ 2026-07-29 — corrected to `superseded` by intake-372 with a dated source correction; the existing rejection remains intact. Firecrawl is **AGPL-3.0 open-source and fully self-hostable** (`SELF_HOST.md` + `docker-compose.yaml` stand up `/v1/scrape`, `/v1/crawl`, `/v1/map` locally), so it is *in scope* and was **out-competed**, not out-of-scope. Correct verdict: **`superseded`** by intake-372 (Crawl4AI), which is deployed and smoke-tested on port 11235 with CA-1–CA-5 + CA-7 complete. The rejection itself is well-justified — a 322-line deep dive exists — so this is a label fix, not a re-litigation.
  - **Two objections in the notes are now factually outdated**: self-hosted `/search` accepts `SEARXNG_ENDPOINT`/`SEARXNG_ENGINES`/`SEARXNG_CATEGORIES` (it can front our own SearxNG at :8888), and `/extract` accepts `OPENAI_BASE_URL`/`OLLAMA_BASE_URL`/`MODEL_NAME` (it can run on a local llama-server). Neither changes the outcome; both should be accurate in the record.
  - **The decisive objection got stronger**: compose grew from five services to **seven**, declaring 6 cores / 12 GB — on a host whose entire performance story is CPU memory bandwidth. Fire-engine remains cloud-only, so the self-hosted engine ladder still tops out at Playwright.
  - Minor record fixes: the entry's URL is the **org page** (`github.com/firecrawl`), not the repo; and `firecrawl-py>=4.16.0` is already installed in the hermes-agent venv as a transitive dependency, so "Firecrawl is not in our stack" is not literally true.
  - Transferable pattern worth keeping from a rejected tool: its **ranked engine waterfall** (numeric per-engine quality scores → per-request ordered fallback list) is a better model for CA-6 Camofox escalation than our current substring blocklist in `_is_blocked_page()`.
  - Owner: [`searxng-search-backend.md`](knowledge-pipelines.md#track-searxng-search-backend).

- [x] **ID-37 — Audit scorecard and the residual population.** ✅ 2026-07-25 — **RESIDUAL POPULATION CLEARED.** All 8 low-relevance candidates re-read against live sources: **7 correctly filed, 1 mislabelled (taxonomy only), 0 missed content, 0 dead links.** The deferral was safe — unlike the 11 high/medium entries, these were genuinely read before dismissal (intake-163/400/799 carry source-specific detail that could not have been written without opening the source). Corrections applied to the index as `dive_corrections`: **intake-376 verdict CORRECTED `not_applicable` → `already_integrated`** (it asserts out-of-scope while the entry's own notes cite it as supporting evidence for the LIVE `reasoning-compression.md` thread — hygiene only, no new work); **intake-375#record**'s one forward-looking hook is empty (the `advantage` field flagged as "interesting for future data quality research" is a **uniform constant 1.0** across all 20,480 rows — recorded so nobody chases an empty column); **intake-799** omits a 5th schema tier (*Structures*), conclusion unaffected; **intake-163** has an uncaptured-but-not-actioned quality-parity gate pattern (99.04% same-top-token, KL < 0.0003) that `tq3-quantization-evaluation.md` already exceeds. Cosmetic: intake-375#record and intake-376#record are HF datasets filed as `source_type: blog`. Original scorecard: Of **11 re-read entries**: 3 dropped major content (DFlash trio), 2 dropped major content (RLM pair), 1 stale-catalog reversal (Nemotron-578), 2 label-wrong/outcome-right (Firecrawl, Nemotron-577), 1 reasoning-wrong/label-right (adaptive-chunking), **2 confirmed correctly filed** (`intake-804`, `intake-881`). **8 low-relevance conflation candidates remain un-re-read** (`intake-136#record, intake-163#record, intake-178#record, intake-375#record, intake-376#record, intake-400#record, intake-799#record, intake-801#record`) — deferred as lower expected value, not cleared. Decide whether to sweep them or close them explicitly.

---

## Dependency graph

```text
ID-1 (probe GEPA endpoint) ──┬─→ ID-3 (re-decide gepa_ratio)
ID-2 (dependency pin) ───────┘        │
                                      └─→ (optional) optimize_anything adoption

ID-4 (gate AP-29 before wiring) ──→ ID-5 (AP-32 preconditions)
        │                                  ▲
        └──────────────────────────────────┴── shared root cause:
                                               accumulating-store degradation
                                               (2605.12978 + 4 corroborating papers)
ID-9 (behavior handbook) ─── inherits ID-4's append-only + validation-gate constraints

ID-7 (ordered_subsequence verifier) ──┬─→ ID-8 (FrontierCS floor probe: needs exec sandbox too)
                                      ├─→ ID-16 (ThinkingCap A/B quality axis)
                                      └─→ ID-17 (v8 IQ-quant graded probe)

ID-6 (do NOT trim on vendor claim) ──→ ID-13 (lossless deletion IS safe) ──→ ID-12 (fix stale copy)
ID-10 (conflation guard) ──→ ID-11 (handoffs_updated reliability)

ID-15 (header gate) ──→ MI210 abliteration-vs-MTP-acceptance experiment (operator-gated)
ID-14 (Fractal container trial) ──→ containment design → mi210-kernel-rnd-loop Phase 2
```

## Cross-cutting concerns

1. **One failure mode recurs across three independent literatures**: artifacts that accumulate — prompts, insights, skills — degrade past a threshold, driven by **semantic confusability and stale-item injection rather than size per se** (Decagon 50→500 regression; Library Drift below-no-skill-baseline; Skill Shadowing). Any adoption of GEPA-style optimization (ID-3) or CORE-style insight memory (ID-4, ID-9) needs a lifecycle/eviction policy and a held-out regression gate **from day one**, not as follow-up.
2. **Restatement is not corroboration.** Across all seven Tier-2b claims the majority of search volume was vendor blogs, Medium summaries, and press relays restating the original number. Genuinely independent empirical work exists for GEPA, the CORE *mechanism*, PageIndex, and ThinkingCap — and for **none** of the omni composition result, the Anthropic ">80%", or the Letta token ratio.
3. **Two sources could not be relocated by the Tier-2b agent** (the omni blog and the Letta trajectory post) despite primary agents fetching both with highly specific detail, and the omni content being independently corroborated by a second agent reading the repo. Most likely a search/index failure rather than nonexistence — **re-verify both URLs before their numbers enter any downstream document.**
4. **Evidence grade travels with the number.** Nothing in this file is protocol-grade for EPYC. Where an item proposes a decision (ID-3, ID-16), the decision must rest on a *local* measurement with a cited protocol-id, n, date and attestation.
5. **Parallel-session hazard.** Four CPU-kernel handoffs held uncommitted third-party edits during this sweep. Stage only your own files; never `git add` a shared handoff wholesale.

## Reporting instructions

- On completing an item, flip `- [ ]` → `- [x]` here **and** append the same task line (or its outcome) to the owning handoff named under the item. Prose status alone is invisible to the dashboard.
- When an item graduates fully into its owning handoff, strike it here with a pointer rather than deleting — this file is the provenance record for why the work exists.
- Back-fill `handoffs_updated` / `handoffs_created` on the corresponding `research/intake_index.yaml` entries when work lands (see ID-11).
- Items ID-12, ID-15, ID-17 are addressed to the parallel v8 kernel session — coordinate before committing to shared files.

## Key file locations

| Surface | Path |
|---|---|
| GEPA client (ID-1) | `epyc-orchestrator/scripts/autopilot/species/gepa_optimizer.py` L209/L214/L265/L271/L279 |
| GEPA dispatch | `epyc-orchestrator/scripts/autopilot/species/prompt_forge.py:512-520` |
| Installed gepa | `/mnt/raid0/llm/epyc-orchestrator/.venv` → 0.0.26 |
| KnowledgeDistiller (ID-4) | `epyc-orchestrator/scripts/autopilot/knowledge_distiller.py` (`4cdc77e`) |
| Agent-file compliance gate (ID-6) | `tests/compliance/agent_file/live_runner.py` |
| Scorer library (ID-7) | canonical `answer_scoring` — see `scoring-infra-standardization.md` |
| Always-loaded surface (ID-13) | `/workspace/CLAUDE.md` (223 L), `agents/shared/*.md`, `.claude/skills/` (13) |
| Stale policy copy (ID-12) | `agents/shared/ENGINEERING_STANDARDS.md:52` |
| llama.cpp token-id emit (ID-20) | `/mnt/raid0/llm/llama.cpp/tools/server/server-task.cpp:298,316` |
| Intake index + audit | `research/intake_index.yaml` (885 entries at sweep start) |

## Provenance

- [x] **ID-RI-EARLIER-REVIEW — Investigate three older completed intakes for weak operational actionables and reconcile selected findings to current owners.** ✅ 2026-10-04 — Three parallel read-only reviews (Jev/EXL3 September 23, Dream-RSI September 17, MI210 compiler/VGPR September 15) followed by main source/code/counter-coverage review and Q8 static qualification. Filed PROPOSED AC-CHECKPOINT-ALLOC and INF37-MOE-Q8-FUSION; refined existing TD-1d.3 and target-precision control; registered four prospective profiles under existing VB-RI-OPS-WIRE. [Evidence and bounded acceptance](../../docs/reviews/research-intake-earlier-applications-20261004.md). Review complete, applications unexecuted; no original intake/approval/checkpoint mutation, new campaign, hardware run, exhaustive completeness or omission-rate claim.

Sweep of 2026-07-25: 12 submitted sources → intake-886…897 (pending Phase-5 persist), 4 expansion entries (FrontierCS 2512.15699, faulty-memories 2605.12978, metacognitive-reuse 2509.13237, agent-skills survey 2602.12430), 1 triaged low (experiential-RL 2602.13949), plus a Tier-2b contradicting-evidence ledger over 7 claims and a companion-artifact conflation audit (19 candidates, 11 re-read).

**Closed negative worth not re-chasing**: arXiv 2512.15699 is the **FrontierCS benchmark**, not the omni/`optimize_anything` method paper. The composition numbers (GEPA 43.8→61.8, AutoResearch 55.4→63.2, Meta-Harness 50.9→59.3; 3/3/4-of-10 per-problem wins) have **no protocol-bearing source anywhere** and stay observation-grade permanently. No budget-parity definition exists in either the blog or the paper; the blog's "$20" is a proposer-token USD cap of its own construction, and the orthogonal eval-call budget is never stated as matched.

### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

Operator-approved 2026-10-31 (plan revision 2, `research/intake-stage3-plan-2026-10-31-ws58.md`, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`; relayed by the ws58 coordinator; budget approved: about 13 MI210-hours for the drafter pilot, 6-9 engineer-weeks for the race checker, the 95.5 GB ThinkingCap download; D1 confirmed: in-weights calculator declined, GPU reason recorded on intake-2550/2574; D2 approved: scratch upstream builds are measurement instruments only). Trigger records below are prose with no checkbox until a reviewed session confirms their condition.

- [x] **ID-RI-ANCHOR-GATE — Make quote re-find a gate the author cannot satisfy by assertion (fabricated citations) (intake-2563#record, intake-1377#record).** Today `.claude/skills/research-intake/scripts/validate_intake.py` (~L436-441) only checks `claim_anchors` is non-empty and `verified_by` is self-written, so a fabricated or cross-pasted quote (the 2026-07-25 CORE ablation, also pasted into intake-895) passes. Borrow Octopus's rule that a mark is recorded only by the runtime after a verifier passes the artifact and nothing else can emit it (`docs/contracts/VERIFIERS.md`, "Nothing emits marks"). Change SKILL.md Stage-2 "Writes permitted" (claim_anchors bullet) and the Stage-2 Verification Gate: add `validate_intake.py --check-anchors` that (a) re-finds every anchor `quote` in the retained source via `scripts/vidya/machine_anchor.py:verify_source_anchor` / `raw_anchor_store.py` (dive wrapper must write the source into `EPYC_VIDYA_RAW_ANCHOR_ROOT`, today opt-in and unused by dives), (b) recomputes `quote_sha256`, (c) writes an `anchor_mark: {verifier, source_raw_sha256, found}` that only the script writes, and (d) flags any `quote_sha256` appearing under two different entries (cross-paste, needs no retained source). New dive-verified entries without an anchor_mark fail; legacy entries stay grandfathered. Controls: four frozen fixtures (verbatim quote, fabricated quote, whitespace-altered quote, same quote under two entries) plus the old validator output; per-fixture expected verdict recorded. Decision rule: ship only if all four fixtures give the predeclared verdict and a replay over the current index flags zero verbatim anchors. Passing proves containment, not entailment; the per-claim second reader stays.
  ✅ 2026-11-07 (operator-adhoc-ops-20261105): `validate_intake.py --check-anchors/--write-marks` + new-entry anchor_mark rule + SKILL.md gate landed; `scripts/tests/test_anchor_gates.py` four frozen fixtures give their predeclared verdicts (verbatim ok; fabricated, whitespace-altered, cross-pasted flagged). Replay over 2657 entries: 0 errors, but vacuous for re-find since `EPYC_VIDYA_RAW_ANCHOR_ROOT` is unset and only intake-1963 retains a source; 514 legacy anchors warn-only (328 cross-pasted). [no-belief: tooling landed; replay result is vacuous on re-find]
- [x] **ID-RI-LANE-HEAD — Pin the repo revision every in-house citation was read at and refuse stale ones mechanically (stale clones) (intake-2563#record).** SKILL.md L391-405 forbids the shared clone in prose only (2026-09-14 dives read /workspace @d372c953). Octopus pins descriptor hashes in every formed grant and refuses a movement against a changed checkpoint with a typed `stale_epoch` (`docs/contracts/LEDGER_INDEX.md`). Change: (1) Stage-2 dive brief template requires `lane_head` (full SHA of the lane worktree) in the returned YAML, and a `dive_preflight.py` run by main before dispatch asserts the named root is the lane worktree and its HEAD is not behind origin/main; (2) in-house `claim_anchors` locators `path:Lx-Ly @ sha7` get validated by `validate_intake.py --check-lane-anchors`: `git show sha7:path` must contain the quote, and `git diff --name-only sha7..origin/main -- path` non-empty emits typed `stale_epoch` that blocks Stage-3 plan citation of that anchor until re-read. Controls: replay the 2026-09-14 incident (anchor at d372c953 for a file since changed), a moved path, an unchanged path. Decision rule: stale_epoch fires on the first two and not the third; zero false positives over the current in-house anchors.
  ✅ 2026-11-07 (operator-adhoc-ops-20261105): `--check-lane-anchors`, `dive_preflight.py`, SKILL.md lane_head requirement landed; tests: stale_epoch fires on changed file and moved path, not on unchanged path; replay: 2 in-house anchors, intake-1360 stale_epoch (the 2026-09-14 incident, true positive), 0 false positives. [no-belief: tooling landed with fixtures]
- **[declined: ws58 2026-11-03 content-review: intake-process tooling with no stack behaviour change]** **ID-RI-STAGE-GUARD — Compute the stage write grant by script and check the diff outside the agent (stage-gate violations) (intake-2563#record).** The skill's "May write" table (SKILL.md L50-58) and the Stage 1/2 gate "`git status handoffs/` clean" are prose run by the same agent that might violate them (2026-07-25: handoffs edited after an operator "you can edit"), and the dive `artifact_audit: clean` line is self-reported. Octopus forms the effective grant by a deterministic script at every arrival (ceiling intersect chain intersect bindings), enforces it outside the model and records a typed refusal row (`docs/architecture.md`, "How policy is formed"). Change: add `scripts/stage_grant.py form --stage N` (allowed paths: S1 index+.research-session.json; S2 index; S3 plan file; S4 the paths named by the approved plan, bound to `stage3_filing.plan_sha256` already checked at validate_intake.py ~L1084) and `check`, run by main at each stage boundary on `git status --porcelain` plus a tree hash taken at stage entry; violations append a typed row to the session JSON (`stage_write_outside_grant`, `plan_hash_stale`). Controls: replay the 2026-07-25 handoff-edit-in-Stage-2 case, a Stage-4 write outside the plan, and a clean stage. Decision rule: both violations refused, clean stage passes, no change to legacy validate_intake output.
- **[declined: ws58 2026-11-03 content-review: intake-process vocabulary; no stack behaviour change]** **ID-RI-DECLINE-VOCAB — Replace free-text decline reasons with a closed vocabulary (dropped actionables, operator Act-Do-Not-Defer rule) (intake-2563#record).** `validate_intake.py` ~L1132 accepts any `decline: <text>`, so "vendor-only", "upstream has not done it" or "not applicable" can close a row (the rules SKILL.md L40-48 forbid). Octopus refusals are typed rows from a closed set, "never a silent drop" (`docs/contracts/LEDGER_INDEX.md`). Change: a decline/closed-with-basis terminal must start with a code from {duplicate:<exact id>, superseded:<successor id>, measured-loss:<evidence ref>, math-constraint:<one-line proof>, external-event:<named event>, operator-ruled:<ruling ref>}; the validator rejects other prefixes and the forbidden phrases, and `external-event` requires a name that is not "upstream". Controls: freeze the current plan's decline rows as a fixture (expected: each maps to a code or is flagged for re-open), plus three negative fixtures (vendor-only, upstream-absent, not-applicable). Decision rule: negatives rejected, all legacy plans still pass under the unchanged legacy mode.

## Track: agent-file-prose-compression
<!-- gate: none -->

> Folded from `handoffs/active/agent-file-prose-compression.md` @ `8e46a59e2886` on 2026-11-02 (BRF-T1-F9, route 1a, operator D1/D5; retired row EVL-01 → EVL-29). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Per-Model Agent-File Prose Compression

**Status**: compacted 2026-07-30 (wrap-up) — AFC-P6 restructure COMPLETE (22/22 items; audit
D1–D13 all addressed); compliance suite v2 landed (30/30/30, `agent_file_compliance_v2_20260730`);
operator DECIDED: n=30 expansion runs BEFORE any compressed-artifact rollout. The expansion
campaign is fully prepared and **HELD — inference is operator-gated**.
**Created**: 2026-04-30 (intake-509 follow-up) · **Priority**: HIGH
**Completed history**: [`../completed/agent-file-prose-compression-completed-through-2026-07-30.md`](../completed/agent-file-prose-compression-completed-through-2026-07-30.md)

#### Executor Start Here (2026-07-30)

Exactly two things remain:

- [ ] **AFC-P5.E3 — run the n=30 compliance campaign.** Operator released inference 2026-11-07 (adhoc-ops directive). **Re-planned 2026-11-07 on the CURRENT roster and kernel store**: the 2026-07-30 roster (gemma4-26B, Qwen3-Next-80B, Qwen3.5-122B) is overtaken (3 of 4 GGUFs no longer on disk) and the old script ran the v9 build dir. Now 3 unique GGUFs, one quarter-shape row each (v10 production CPU kernel from the kernel store, llama-server 10303 ffc1bac82, `quant_build` = Q8_0 / Q8_0 / UD-IQ4_XS on production v10): `afc-p5e3-n30-q36_35b-20261107` (Qwen3.6-35B-A3B-MTP-Q8_0 = worker_general + frontdoor), `afc-p5e3-n30-q38_27b-20261107` (Qwen3.8-27B-Q8_0 = ingest), `afc-p5e3-n30-q38_flash-20261107` (Qwen3.8-Flash-Next-UD-IQ4_XS = architect_general); suite v2 30/30/30 x 4 levels x 90 tasks, 8-way, temp 0, scratch `/mnt/raid0/llm/tmp/afc-p5e3-n30-20261107/`. Decision (absorbs E4): per model/level, compliance >= 0.95 x the level-none baseline keeps the level; compliance, procedure >= 0.95 x baseline, recall >= 0.90 absolute; baseline recall < 0.90 => operating point `none`. Stop rules: stop-on-answer when all four levels of a model are scored (the keep table needs all four); stop-on-futility on a live_runner failure or a config probe failure (row ends, remaining levels INCONCLUSIVE); gate-class = futility-only at interim looks. File the result into this box when each row ends.
- **[declined: ws58 2026-11-03 content-review: merged into E3 as its decision step]** **AFC-P5.E4 — re-take the rollout decision on the n=30 evidence.** Gate per model/level:
  `compliance ≥ 0.95 × level-none baseline`, `procedure ≥ 0.95 × baseline`, `recall ≥ 0.90`
  absolute; baseline recall < 0.90 ⇒ operating point `none`. Decision-fork table below. Factor
  in post-restructure savings (mild 1.6% / medium 20% / aggressive 39% of words) — the
  structural-deletion pass already captured most of the original win.
- [x] **AFC-P5.E5 — denominate the compression target in WORDS, not lines, and re-derive the
  savings table.** External corpus evidence (intake-1199#record, re-derived from the authors' Zenodo
  replication package, record 18368326): `CLAUDE.md` sits at the **96.5th percentile by words but
  only the 85.4th by lines** — 10.5 words per line. **A pass that targets LINES systematically
  under-finds**, and E4's savings table above is already denominated in words, so the two are
  currently measuring different things. Re-express the mild/medium/aggressive figures against a
  word baseline before E4 consumes them.
  ✅ 2026-11-07 (operator-adhoc-ops-20261105): re-derived on the live tree with `wc -w`/`wc -l` against `agents/shared/ENGINEERING_STANDARDS.md` (735 words / 103 lines): mild 674 w (-8.3%) / 104 l (+1.0%), medium 545 w (-25.9%) / 101 l (-1.9%), aggressive 421 w (-42.7%) / 94 l (-8.7%). The old 1.6/20/39% figures predate the later restructure; the WORD figures are the E4 consumption basis and the line deltas show why a line target under-finds (aggressive saves 4.9x more in words than lines). Table: `docs/reports/frontier-lab-automation-closeout-20261107.md`. [no-belief: arithmetic re-derivation from tracked files, committed as a doc table]
- **[declined: ws58 2026-11-03 content-review: a framing correction, bookkeeping]** **AFC-P5.E6 — correct the "we exceed the corpus maximum" framing before it propagates.**
  Measured 2026-08-20 (`research/sources/intake-20260819/EVIDENCE-agent-file-and-moe-measurements.md`):
  the widely-repeated version of this claim does **not** survive scrutiny, in two ways. (a) The
  10,424-word figure for `agents/shared/` **includes three `ENGINEERING_STANDARDS.compressed-*`
  variants** — outputs of this handoff's own experiment, not loaded policy. Live tree = **8,787
  words, which is 164 words UNDER** the 8,951-word corpus maximum. (b) It compares a 7-file TREE
  total against a SINGLE-FILE maximum, which is a category error; our largest single file is
  `OPERATING_CONSTRAINTS.md` at **3,949 words**, comfortably inside corpus norms.
  **The genuinely anomalous figure is structural, not volumetric: `CLAUDE.md` carries 22 H2
  headings against a corpus average of 2.7 categorised L1/L2 headings.** Retarget the work at
  heading proliferation rather than word count, and stop quoting the exceeds-the-maximum line.
- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** **AFC-P5.E7 — Cross-model artifact reuse rule for shared agent files** (intake-1317#record,
      dive-verified): before reusing an agent-file artifact across a **capability gap**, strip
      model-specific error WORKAROUNDS and keep the PROCEDURE. Both directions are measured in the
      source: the same shared artifact drops Gemini SpreadSheet 50.5 → 18.1 under Qwen-3.5-4B
      skills, while lifting Gemma LiveMath 33.9 → 73.1. Applies to
      `agents/shared/*.compressed-*.md` reuse across the four-model roster; state the rule in the
      compression rider, not only here. Zero compute.

**Decision forks (for E4)**:

| n=30 result | Action |
|---|---|
| ≥95% baseline compliance at medium/aggressive for Tier-A models | Roll Phase 5 to `agents/shared/*.md` first; role overlays second PR |
| Only mild passes | Adopt mild as conservative default; no aggressive overlay artifacts |
| No level passes | Operating points → `none`; archive artifacts as research; close "abandoned by eval" |
| Failures concentrated in polarity/order | Patch the compression rider; rerun only the failed class |

#### Objective (unchanged)

Compress agent-file prose at authoring time (project rider derived from /caveman), measure
per-model compression-tolerance curves, and use the per-model operating point as a deployment
gate — a model that can't follow its agent file at any level is flagged before production.

#### Key Files

- Suite v2: `tests/compliance/agent_file/` (`runner.py` `SUITE_VERSION`, pools 30/30/30,
  `live_runner.py --concurrency`, `run_n30_campaign.sh` with SMOKE mode)
- Compressed artifacts (regenerated 2026-07-30, post-restructure source):
  `agents/shared/ENGINEERING_STANDARDS.compressed-{mild,medium,aggressive}.md`
- v1 curve + operating points (superseded instrument, historical evidence):
  `data/compliance/2026-05-07-*`; registry fields `agent_file_compression_operating_point`
- Audit + restructure record: `docs/reference/agent-config/agent-file-audit-2026-07-30.md`
  (defects D1–D13); incident narratives `docs/reference/agent-config/INCIDENT_LOG.md`

#### Completed Scope

Everything before E3/E4 is DONE and ledgered in the completed sibling (link in header):
Phases 1–4 + pilot artifacts; v1 per-model curve + registry operating points; the 2026-07-29
lossless structural deletion pass (AFC-P5.0/P5.2); the 2026-07-30 full-stack audit + AFC-P6
restructure (P6.1–P6.22: staleness repair, dedup/extraction into SESSION_LIFECYCLE +
INCIDENT_LOG + docs/guides, enforcement hardening incl. post-edit reference guard + matrix
discovery, MEASUREMENT v2 ratification support, sub-repo fixes, thin overlays, retirements);
suite v2 instrument repair + expansion (AFC-P5.E1/E2); the operator decision (n=30 first,
✅ 2026-07-30).

#### Reporting

- E3: per-(model,level) JSONs are the drain points; write the curve table into this handoff
  when complete; flip E3.
- E4: present the rollout decision as an operator decision package citing the n=30 curve; flip
  E4 and either execute the chosen fork or close per the fork table. Update
  `handoffs/active/research-evaluation-index.md` row on close.

## Track: frontier-f2-self-running-lab
<!-- gate: none -->

> Folded from `handoffs/active/frontier-f2-self-running-lab.md` @ `8e46a59e2886` on 2026-11-02 (BRF-T1-F9, route 1a, operator D1/D5; retired row EVL-24 → EVL-29). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Frontier F2 — The Self-Running Lab: Local Agents Take Over Lab Maintenance

**Scratch**: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/evl24-distinct-run-source-candidate-20261007`, `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/evl24-native-preparation-20261007`

**Status**: W1 inventory + W2 runner/shadow wrapper/context enrichment/readiness reporting + quiet-window nightly deployment for two read-only jobs + active-safe deterministic AutoPilot monitor/scheduling/restart-advice/outcome-progress/review-queue/quiet-window-plan watches + dashboard/operator restart guidance + W3 promotion-ladder hardening and batch verdict capture landed on current orchestrator/root branches; 2026-07-07 quiet-window execution produced real model-backed rows and cloud-reviewed verdicts, leaving the lab review queue at `pending_reviews=0`, `verdicts=12`, with two F3 gold tuples (one accepted `handoff_freshness_lint`, one rejected negative `attestation_watch`) plus non-gold closures for superseded/debug rows. W3 reliability ladder accumulation + W4 still open (created from the Fable 5 strategic-frontiers review)
**Created**: 2026-06-12
**Priority**: HIGH but GATED on N1–N4 instrument repair + N2 ledger; F5 injection policy is complete
**Spec**: [fable5-findings-07-strategic-frontiers.md](../completed/fable5-findings-07-strategic-frontiers.md) §F2 — read it before claiming any waypoint
**Related**: [fable5-findings-04-impl-plan.md](../completed/fable5-findings-04-impl-plan.md) (capability registry); [frontier-f5-intake-injection-hardening.md](../completed/frontier-f5-intake-injection-hardening.md) (injection policy, COMPLETE); [internal-kb-rag.md](knowledge-pipelines.md) (kb-search context assembly); [delegation-context-preassembly.md](context-and-token-economy.md#track-delegation-context-preassembly) (DCP bundles)

#### Why

The project's true output is research-decisions-per-week; its binding costs are
operator attention and cloud-agent sessions. What exists is a self-*optimizing
serving layer*, not a self-*running lab*. The maintenance workload — intake
triage, hygiene lints, monitoring, digest drafting — is mechanical enough for
local models IF given output contracts, a review queue, and a reliability
ladder. The prerequisites (evidence plane, attestation, MEASUREMENT.md, index
rewrite) now exist or are queued; this is the 10× on the lab itself.

#### Waypoints

- [x] **W1 — job inventory** (1 day): `orchestration/lab_jobs.yaml`, one row per recurring job (`{job_id, input_spec, output_contract, risk, model_role, schedule, reference_skill}`); seed set per spec §F2-W1 ordered by mechanical-ness (hygiene lint → attestation watch → digest draft → intake triage → claims-grammar check → deep-dive drafting) — acceptance: every seed job has a JSON-schema output contract and a risk class. **Landed current branch 2026-06-14**: cherry-picked from branch-ready `8b4b24b` into `epyc-orchestrator` `d57e94c` (`Seed self-running lab job inventory`). Six shadow-stage jobs validate against required fields/risk classes and each embedded JSON Schema compiles under Draft 7.
- [x] **W2 — the runner** (3–5 days) ✅ 2026-07-14 remaining acceptance met 2026-07-07: real quiet-window batch, cloud-reviewed verdicts, `pending_reviews=0`: `scripts/lab/run_job.py` — load job spec → assemble context (kb-search + DCP bundles, both BUILT) → local role via `/chat` `force_role` + structured output → validate against contract → write to `orchestration/lab_review_queue/` (NEVER directly to handoffs/indices) → log a `task_record` (feeds F1+F3); schedule via `scripts/nightshift/` — acceptance: 2 jobs running nightly in shadow (output produced, scored, discarded). **Runner landed current branch 2026-06-14**: cherry-picked from branch-ready `450a366` into `epyc-orchestrator` `71f705e`, adding the review-queue runner, contract validation, bounded source-context assembly, explicit `--execute-chat` gating, fixture/dry-run validation modes, immutable review artifacts, and `lab_task_record.v1` JSONL logging. **Shadow batch wrapper landed current branch 2026-06-14**: cherry-picked from branch-ready `5fad61d` into `epyc-orchestrator` `3a640b4`, adding `scripts/lab/run_shadow_jobs.py`, bounded nightly shadow selection, and explicit `--dry-run-stub` / `--execute-chat` modes. **Context enrichment landed 2026-06-27**: `epyc-orchestrator` `d43a60d2` adds default-off `dcp_pack` context mode, source-excerpt fallback, `lab_context_summary.v1` task-record telemetry, and opt-in DCP packing for the read-only `handoff_freshness_lint` and `claims_grammar_check` jobs. **Readiness reporting landed 2026-06-28**: `scripts/lab/readiness_report.py` summarizes schedulable shadow jobs, task-record/verdict/gold-tuple counts, and promotion-gate eligibility without mutating queue or job state. **Quiet-window readiness refinement landed 2026-06-28**: `epyc-orchestrator` `bd743ece` adds `--json`, `quiet_window`, and `nightly_ready_now` fields so the report distinguishes scheduled capacity from jobs safe to execute while AutoPilot/llama servers are active. **Pending-review readiness landed 2026-06-28**: `epyc-orchestrator` `3ba1c879` adds per-job `review.pending`, capped `pending_run_ids`, and summary `pending_reviews`/`pending_review_job_ids` so completed shadow outputs cannot hide without verdicts. **Quiet-window nightly deployment landed 2026-06-28**: `handoff_freshness_lint` and `attestation_watch` are enabled in `orchestration/lab_jobs.yaml`, and root `scripts/nightshift/run_wrapper.sh` runs the nightly shadow batch only when inference is quiet and no AutoPilot process is active. **KB-RAG context enrichment landed 2026-06-28**: `epyc-orchestrator` `4cf66e70` adds optional `kb_rag` context mode and enables KB snippets for the two read-only nightly jobs. **Active-safe deterministic monitor landed 2026-07-05**: `epyc-orchestrator` `0f7252bb` adds `deterministic_command` lab execution, active-safe job selection/readiness buckets, and enabled `autopilot_authority_watch`; live smoke selected only that job while AutoPilot and `30` llama-server processes were active, wrote a contract-valid temp review artifact, and reported `ok=true`, `status=active`, trial `1168`, `code_stale=false`, blockers `[]`. **Active-safe scheduling landed 2026-07-05**: `epyc-orchestrator` `4829028d` adds `--quiet-window-only` so model-backed quiet runs exclude deterministic monitors, and root nightshift now runs `--active-safe-only --execute-command` every wrapper pass before the existing quiet-window `--execute-chat` batch. **Outcome-progress watch landed 2026-07-06**: `epyc-orchestrator` `56b12285` adds active-safe `autopilot_outcome_progress_watch` around `phase_health_report.py --json --require-outcome-progress`; live smoke selected only that job and reported `status=outcome_stalled`, latest frontier trial `1005`, latest trial `1207`, and `202` trials since frontier. Current readiness reports `enabled_jobs=5`, `nightly_runnable=5`, `nightly_active_safe_ready_now=3`, `nightly_quiet_window_ready_now=0`, `nightly_ready_now=3`, and `pending_reviews=0` during active AutoPilot/llama serving. Remaining W2 acceptance: first real quiet-window model outputs, score/discard, and collect real verdicts.
  - [x] Add active-safe stale-daemon restart advisor and launcher preflight (`autopilot_restart_advisor`, `--preflight`) — ✅ 2026-07-05
  - [x] Record live active-safe/quiet-window readiness snapshot after restart-advisor deployment — ✅ 2026-07-06 (`orchestration/reports/self_running_lab_readiness_20260706T033917Z.json`, orchestrator `956cb202`)
  - [x] Wire restart advice into operator/dashboard escalation once the read-only signal has at least one boundary/no-boundary smoke record — ✅ 2026-07-06 (`epyc-orchestrator` `03f3917e`; CLI restart budget aligned to `--max-trials 3000` in `9ed7b95f`)
  - [x] Mark stale planner tap history on the dashboard by comparing tap mtime with the current AutoPilot start, exposing `planner_tap_mtime_s` and `planner_tap_precedes_autopilot_start`, and wording current actions with no planner trace separately from live planner state — ✅ 2026-07-08 (`epyc-orchestrator` `b5cadba6`)
  - [x] Add active-safe outcome-progress watch so the lab can flag frontier/promotion stalls while AutoPilot is running — ✅ 2026-07-06 (`epyc-orchestrator` `56b12285`)
  - [x] Run active-safe deterministic watch batch into the canonical lab review queue — ✅ 2026-07-06 (`epyc-orchestrator` `ba0cc164`; schema accepts `waiting_for_planner_turn`; 7 task records, 7 pending reviews)
  - [x] Emit batch-review JSONL templates from the active-safe review-queue watch — ✅ 2026-07-06 (`epyc-orchestrator` `a83cc676`; 8 pending records, 8 template rows)
  - [x] Emit markdown review packets for pending lab queue items — ✅ 2026-07-06 (`epyc-orchestrator` `95d2d39f`; live packet `orchestration/reports/lab_review_queue_report_20260706T131453Z.md` shows 8 pending active-safe deterministic rows and 0 review-candidate rows)
  - [x] Close active-safe deterministic review rows without inflating F3 gold tuples — ✅ 2026-07-06 (`scripts/lab/auto_review_active_safe.py --apply`; live queue now reports 8 deterministic verdicts, 0 pending reviews, and 0 F3 `lab_gold_tuple.v1` rows; model-backed rows still require cloud/operator review)
- [ ] **W3 — reliability ladder** (ongoing): `scripts/lab/promote_job.py` enforcing shadow → reviewed → autonomous from logged stats (shadow ≥10 runs scored vs a cloud-reference run; autonomous only for read_only report-class jobs at ≥90% accept-rate over 20 reviewed runs) — acceptance: promotion only via the script; every (input, local output, cloud reference, verdict) tuple saved as F3 gold data. **Gate scaffold landed current branch 2026-06-14**: cherry-picked from branch-ready `775d230`/`78f9b93` into `epyc-orchestrator` `5ab007f`/`bad8bb9`, adding promotion evaluation/reporting over `lab_task_record.v1` + `lab_review_verdict.v1`, cloud-reference/gold-tuple requirements, read-only autonomous restrictions, guarded jobs-file mutation, and `scripts/lab/record_verdict.py` for `lab_gold_tuple.v1` rows. **Promotion-ladder hardening landed 2026-07-06**: `epyc-orchestrator` `9ca7061c` now rejects stage skips/downgrades, requires operator-reviewed evidence for autonomous promotion, and requires referenced F3 gold tuple files to exist when evaluating from the queue path. Remaining W3 acceptance: collect real shadow/reviewed verdicts and use the script as the only promotion path.
- **[declined: ws58 2026-11-03 content-review: "weeks" of expansion with no gate]** **W4 — expand** (weeks): intake triage joins after F5 lands; deep-dive drafting after triage proves; research-intake skill stays the orchestrator, local models take per-source extraction steps — acceptance: each expansion enters at shadow and climbs the ladder.

##### Bounded promotion evidence source correction

- [x] **EVL24-DISTINCT-RUN-SOURCE** — close the reviewed duplicate-verdict inflation gap in actual `scripts/lab/promote_job.py`: selected scored verdicts must identify distinct nonblank logged runs for the same job; duplicate, invalid or missing logged-run evidence must refuse before apply. Preserve existing 10/20 thresholds, 90% acceptance, stages, latest-record lookup, risk/gold/operator requirements and explicit stage override. Bind exact source92c9ec87 and all16 whole-module cases through VB-EVL24-DISTINCT-RUN-CONFORMANCE before MAIN source acceptance. No live lab queue/promotion readiness or model/runtime warrant; W3 accumulation and W4 expansion remain open. ✅ 2026-10-07 — [MAIN source/original16/16 acceptance](../../artifacts/ni08/evl24-distinct-run-source-acceptance-20261007/README.md); exact APP73984542, TRUE16/16; live parent gates unchanged.

#### Gates & pitfalls

- HARD GATES: N1–N4 instrument repair done; N2 ledger/restart-bundle gates satisfied for live promotion. F5 injection policy is complete; intake-touching jobs must preserve the `SOURCE-QUARANTINE` convention.
- Review queue is mandatory — CLAUDE.md forbids sub-agent index modifications without approval; the queue IS the compliance mechanism. No job writes directly to handoffs/indices.
- No job may self-modify `lab_jobs.yaml` or any trust-boundary file (the guardrail belongs in `agents/shared/OPERATING_CONSTRAINTS.md` and `coordination/session-bus/human_only_paths.yaml` — the safety-reviewer persona file was archived 2026-08-16, P1-5).
- Context assembly is the cost center — budget it (DCP bundles, per-job token caps); lab jobs share the stack with the autopilot — run in the contention gate's background class, off-peak.
- A job's accept-rate is a MEASUREMENT.md-grade number — same claims discipline as any benchmark.

#### Progress

- 2026-06-12: W1 branch-ready at `feat/lab-jobs-inventory` commit `8b4b24b`. Validation: YAML parse + required job-field/risk/`job_id` const checks passed for 6 jobs; `uv run --with pyyaml --with jsonschema` Draft 7 schema compilation passed for all 6 embedded `output_contract.json_schema` blocks; `git diff --cached --check` passed. The inventory is shadow/disabled only and does not create the runner or queue.
- 2026-06-13: W2 runner branch-ready at `feat/lab-runner` commit `450a366`. Validation: `python3 -m py_compile scripts/lab/run_job.py tests/unit/test_lab_run_job.py` passed; `uv run --with pytest --with pyyaml --with jsonschema pytest -q tests/unit/test_lab_run_job.py` -> 4 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/lab/run_job.py tests/unit/test_lab_run_job.py` passed; `git diff --cached --check` passed; two no-inference smoke runs (`handoff_freshness_lint`, `claims_grammar_check`) wrote contract-valid review artifacts and task records under `/mnt/raid0/llm/tmp/lab-runner-smoke-20260612`.
- 2026-06-13: W3 promotion-gate scaffold branch-ready at `feat/lab-reliability-ladder` tip `78f9b93`. Validation: `python3 -m py_compile scripts/lab/promote_job.py tests/unit/test_lab_promote_job.py scripts/lab/record_verdict.py tests/unit/test_lab_record_verdict.py` passed; `uv run --with pytest --with pyyaml --with jsonschema pytest -q tests/unit/test_lab_record_verdict.py tests/unit/test_lab_promote_job.py tests/unit/test_lab_run_job.py` -> 13 passed, 1 pytest config warning; `uv run --with ruff ruff check` passed for promotion/recorder touched files; `git diff --cached --check` passed. CLI smoke over the dry-run review queue recorded one synthetic `lab_gold_tuple.v1`, and `promote_job.py --no-report` saw 1/10 required cloud-scored shadow tuples and refused promotion.
- 2026-06-13: W2 shadow-batch wrapper branch-ready at `feat/lab-reliability-ladder` tip `5fad61d`. Validation: `python3 -m py_compile scripts/lab/run_shadow_jobs.py tests/unit/test_lab_run_shadow_jobs.py` passed; `uv run --with pytest --with pyyaml --with jsonschema pytest -q tests/unit/test_lab_run_shadow_jobs.py tests/unit/test_lab_record_verdict.py tests/unit/test_lab_promote_job.py tests/unit/test_lab_run_job.py` -> 17 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/lab/run_shadow_jobs.py tests/unit/test_lab_run_shadow_jobs.py` passed; `git diff --cached --check` passed. CLI smoke selected `handoff_freshness_lint` and `attestation_watch` with `--include-disabled --dry-run-stub --max-jobs 2`, wrote two review artifacts/task records under `/mnt/raid0/llm/tmp/lab-shadow-batch-smoke-20260613`, and used no inference.
- 2026-06-14: W1/W2/W3 scaffolds integrated onto current `fix/substring-scorer-digit-separators` lineage via cherry-picks `d57e94c`, `71f705e`, `5ab007f`, `bad8bb9`, and `3a640b4`. Validation on current branch: scoped ruff passed; py_compile passed for all lab scripts/tests; `tests/unit/test_lab_run_job.py tests/unit/test_lab_promote_job.py tests/unit/test_lab_record_verdict.py tests/unit/test_lab_run_shadow_jobs.py` passed 17; embedded lab job Draft 7 schemas validated for 6 jobs; no-inference shadow-batch smoke with `--include-disabled --dry-run-stub --max-jobs 2` wrote `handoff_freshness_lint` and `attestation_watch` artifacts/task records under `/mnt/raid0/llm/tmp/lab-shadow-batch-smoke-20260614-codex` with `n_ok=2`, `n_failed=0`.
- 2026-06-27: W2 context enrichment landed on current orchestrator branch as `d43a60d2` (`Enrich lab runner context artifacts`). `scripts/lab/run_job.py` now supports `input_spec.context_modes`, default-off `dcp_pack` packing with `source_excerpt` fallback, and `lab_context_summary.v1` provenance in both `context_manifest.json` and `task_record.json`. `orchestration/lab_jobs.yaml` opts the read-only `handoff_freshness_lint` and `claims_grammar_check` jobs into `dcp_pack` while keeping all jobs disabled/shadow. Validation: GitNexus impact LOW for `collect_context` and `write_review_artifacts`; `uv run python -m py_compile scripts/lab/run_job.py tests/unit/test_lab_run_job.py`; `uv run ruff check scripts/lab/run_job.py tests/unit/test_lab_run_job.py`; YAML parse smoke; `uv run pytest tests/unit/test_lab_run_job.py tests/unit/test_lab_run_shadow_jobs.py tests/unit/test_lab_record_verdict.py tests/unit/test_lab_promote_job.py -q` -> `18 passed`; no-inference dry-run smoke wrote DCP context provenance under `/mnt/raid0/llm/tmp/f2-dcp-lab-smoke-20260627`.
- 2026-06-28: W2 readiness reporting landed on current orchestrator branch. `scripts/lab/readiness_report.py` is read-only and combines `orchestration/lab_jobs.yaml`, `orchestration/lab_review_queue/task_records.jsonl`, `review_verdicts.jsonl`, nightly/manual schedulability, and the existing `promote_job.evaluate_promotion()` gates into a single JSON report. Validation: GitNexus impact LOW for reused `evaluate_promotion` and `select_jobs`; `uv run pytest -q tests/unit/test_lab_readiness_report.py tests/unit/test_lab_run_shadow_jobs.py tests/unit/test_lab_record_verdict.py tests/unit/test_lab_promote_job.py tests/unit/test_lab_run_job.py` -> `20 passed`; `uv run ruff check scripts/lab/readiness_report.py tests/unit/test_lab_readiness_report.py`; live `readiness_report.py` smoke reported `jobs_total=6`, `enabled_jobs=0`, `task_records=0`, `verdicts=0`, and `promotion_ready=0`.
- 2026-06-28: W2 quiet-window deployment landed. `handoff_freshness_lint` and `attestation_watch` are enabled for nightly shadow runs; root nightshift now invokes the shadow batch with `--execute-chat` only when the inference guard is quiet and AutoPilot is not active. Validation: `bash -n scripts/nightshift/run_wrapper.sh`; dry-run shadow smoke selected exactly the two enabled jobs with `n_ok=2`; focused lab pytest passed with `20 passed`; lab ruff passed; live readiness reports `enabled_jobs=2`, `nightly_runnable=2`, `jobs_total=6`.
- 2026-06-28: W2 pending-review readiness landed as `epyc-orchestrator` `3ba1c879`. `scripts/lab/readiness_report.py` now reports per-job pending verdict counts and capped pending run IDs, plus summary `pending_reviews` and `pending_review_job_ids`, while preserving read-only behavior. Validation: GitNexus LOW for `build_report` and `_job_readiness`; `python3 -m py_compile scripts/lab/readiness_report.py tests/unit/test_lab_readiness_report.py`; `uv run ruff check scripts/lab/readiness_report.py tests/unit/test_lab_readiness_report.py`; focused lab pytest passed with `19 passed`; live readiness reports `pending_reviews=0` because no real quiet-window task records exist yet.
- 2026-06-28: W2 KB-RAG context enrichment landed as `epyc-orchestrator` `4cf66e70`. `scripts/lab/run_job.py` now supports an optional `kb_rag` context mode that queries the existing internal KB-RAG index, appends retrieved snippets to the review-queue prompt/context manifest, and records missing/empty/error states as missing-source telemetry rather than aborting the job. `handoff_freshness_lint` and `attestation_watch` now request KB-RAG snippets alongside their existing context modes. Validation: GitNexus LOW for `collect_context`, `context_summary`, and `run_from_args`; `py_compile`; `ruff`; focused lab-runner pytest (`7 passed`); adjacent lab pytest (`26 passed`); dry-run smoke over `handoff_freshness_lint` wrote `dcp_pack:full=1` plus `kb_rag=6` snippets into a temp review queue while staying in `dry_run_contract_stub` mode.
- 2026-07-05: W2 active-safe deterministic monitoring landed as `epyc-orchestrator` `0f7252bb`. `scripts/lab/run_job.py` now supports guarded `deterministic_command` jobs (`risk=read_only`, argv list, JSON stdout, normal JSON Schema validation), `scripts/lab/run_shadow_jobs.py` can select `--active-safe-only --execute-command`, and `scripts/lab/readiness_report.py` splits active-safe nightly readiness from quiet-window readiness. `orchestration/lab_jobs.yaml` enables `autopilot_authority_watch`, a read-only wrapper around `scripts/autopilot/phase_health_report.py --json --require-current-code`. Validation: GitNexus LOW for lab runner/report surfaces; `uv run pytest tests/unit/test_lab_run_job.py tests/unit/test_lab_run_shadow_jobs.py tests/unit/test_lab_readiness_report.py tests/unit/test_lab_promote_job.py` -> `27 passed`; focused `ruff`; live temp-queue smoke selected `1` active-safe job while AutoPilot and `30` llama-server processes were active and produced `ok=true`, `status=active`, trial `1168`, `code_stale=false`, blockers `[]`.
- 2026-07-05: W2 active-safe scheduler follow-through landed as `epyc-orchestrator` `4829028d` plus root wrapper changes. `run_shadow_jobs.py` now has a mutually exclusive `--quiet-window-only` filter that excludes active-safe deterministic jobs from model-backed quiet-window batches. `scripts/nightshift/run_wrapper.sh` now runs active-safe deterministic lab jobs every pass (`NIGHTSHIFT_LAB_ACTIVE_SAFE_ENABLED=1`, default) and keeps model-backed `--execute-chat` lab jobs behind the existing inference/AutoPilot quiet-window guard. Validation: `uv run pytest tests/unit/test_lab_run_shadow_jobs.py tests/unit/test_lab_readiness_report.py tests/unit/test_lab_run_job.py -q` -> `24 passed`; focused `ruff`; temp smoke confirmed `--active-safe-only` selects only `autopilot_authority_watch`, while `--quiet-window-only --dry-run-stub` selects only `handoff_freshness_lint` and `attestation_watch`; `bash -n scripts/nightshift/run_wrapper.sh` passed.
- 2026-07-05: W2 stale-daemon restart advice landed as `epyc-orchestrator` `39351bad`. `scripts/autopilot/autopilot_restart_advisor.py` consumes `phase_health_report.py --require-current-code` and classifies stale live daemons as `restart_recommended`, `wait_for_boundary`, `no_action`, or `manual_attention`; `start_fable_authority_daemon.py --preflight` prints the same JSON without spawning; `orchestration/lab_jobs.yaml` enables read-only deterministic job `autopilot_restart_advisor`. Validation: `uv run pytest -q tests/unit/test_autopilot_restart_advisor.py tests/unit/test_start_fable_authority_daemon.py tests/unit/test_lab_run_job.py` -> `21 passed`; focused `ruff check`, `ruff format --check`, `git diff --check`; deterministic lab-job smoke wrote contract-valid JSON. Live smoke while AutoPilot PID `2935890` was in trial `1185` returned `status=wait_for_boundary`, `code_stale=true`, `restart_needed=true`, `safe_to_restart_now=false`, so the new signal correctly avoids interrupting active eval work.
- 2026-07-06: W2 readiness snapshot recorded as `epyc-orchestrator` `956cb202` at `orchestration/reports/self_running_lab_readiness_20260706T033917Z.json`. Live restart advice reported `status=no_action`, `restart_needed=false`, `safe_to_restart_now=false`, PID `3525618`, trial `1206`, `code_stale=false`, and phase health active. Readiness summary: `jobs_total=8`, `enabled_jobs=4`, `nightly_runnable=4`, `nightly_ready_now=2`, `nightly_active_safe_ready_now=2`, `nightly_quiet_window_ready_now=0`, `pending_reviews=0`, `task_records=0`, `verdicts=0`, `gold_tuples=0`; quiet-window blockers are active AutoPilot plus `28` live llama-server processes. This is the expected live-safe state: deterministic monitors can run, model-backed lab jobs wait for a real quiet window.
- 2026-07-06: W2 dashboard/operator restart guidance landed as `epyc-orchestrator` `03f3917e`, with the API returning `current_code_health.restart_advice` and the dashboard label distinguishing `restart ready`, `restart wait for boundary`, and manual-attention states. API reload started healthy PID `3638698`; live `/dashboard/api/autopilot_progress` reported AutoPilot PID `3525618`, trial `1207`, `status=wait_for_boundary`, `safe_to_restart_now=false`, and source drift in `autopilot.py`, matching the active `seed_batch` critical section. Follow-up `epyc-orchestrator` `9ed7b95f` raises the advisor's CLI/default start command to `--max-trials 3000`, keeping dashboard and command-line restart guidance aligned with the operator budget.
- 2026-07-06: W2 outcome-progress watch landed as `epyc-orchestrator` `56b12285`. `orchestration/lab_jobs.yaml` now includes active-safe deterministic `autopilot_outcome_progress_watch`, and the production inventory test validates its command, active-safe selection, and JSON Schema. Validation: `uv run ruff check` on the touched lab tests/scripts, `python3 -m py_compile`, focused lab pytest (`30 passed`), YAML load smoke, and a live `run_shadow_jobs.py --active-safe-only --execute-command` temp-queue smoke. The smoke produced contract-valid JSON with `status=outcome_stalled`, latest trial `1207`, latest frontier trial `1005`, `202` trials since frontier, keepable rate `0/78`, wasted-eval rate `54/78`, and learning-excluded rate `24/78`. Current readiness now reports `jobs_total=9`, `enabled_jobs=5`, `nightly_active_safe_ready_now=3`, `nightly_quiet_window_ready_now=0`, and `pending_reviews=0`.
- 2026-07-06: W3 promotion-ladder hardening landed as `epyc-orchestrator` `9ca7061c`. `promote_job.py` now enforces the source stage for each transition (`shadow -> reviewed`, `reviewed -> autonomous`), rechecks that stage at apply time, counts only operator-reviewed rows for autonomous promotion, and validates that referenced F3 gold tuple files exist when the queue directory is known. Validation: GitNexus LOW for `evaluate_promotion`, `apply_promotion`, and `_has_gold_tuple`; focused lab suite `38 passed`; `ruff`, `py_compile`, and `git diff --check` passed. Live readiness after the commit reports `jobs_total=10`, `enabled_jobs=6`, `nightly_active_safe_ready_now=4`, `nightly_quiet_window_ready_now=0`, and `0` persistent records/verdicts/gold tuples while AutoPilot and `28` llama-server processes are active. Remaining W3 work is real shadow/reviewed verdict collection.
- 2026-07-06: W2/W3 review-packet and batch-capture tooling landed as `epyc-orchestrator` `2bdfe35f`. `scripts/lab/review_queue_report.py` adds an active-safe deterministic `lab_review_queue_watch` that lists pending review items and exact `record_verdict.py` command templates without mutating queue state. `scripts/lab/apply_review_batch.py` applies reviewed JSONL verdict batches through the existing recorder, preserving `lab_review_verdict.v1` and `lab_gold_tuple.v1` schemas instead of creating a parallel trust path. Validation: focused lab suite `47 passed`, `ruff`, `py_compile`, diff-check, live `review_queue_report.py` smoke (`0` task records / `0` pending reviews), active-safe shadow-job smoke, GitNexus refresh, and push. This closes the repeatable capture-path gap; the evidence gap remains real quiet-window model outputs plus cloud/operator verdicts.
- 2026-07-06: W2 quiet-window execution planning landed as `epyc-orchestrator` `88f66ae6`. `scripts/lab/quiet_window_lab_plan.py` is a read-only active-safe planner that selects the queued model-backed lab jobs, checks live quiet-window blockers, emits the exact `run_shadow_jobs.py --quiet-window-only --execute-chat` command plus review and batch-apply follow-ups, and derives the timeout from selected job `max_runtime_s` values. The active-safe `quiet_window_lab_plan_watch` job now makes the next stopped-window lab batch discoverable while AutoPilot is still running. Live smoke selected `handoff_freshness_lint` and `attestation_watch`, reported blockers `active AutoPilot process count: 1` and `active llama-server process count: 28`, and generated a 900s batch command. Validation: focused lab/report suite `29 passed`, `ruff`, `py_compile`, diff-check, active-safe shadow-job smoke, and GitNexus refresh. Current readiness reports `jobs_total=13`, `enabled_jobs=9`, `nightly_active_safe_ready_now=7`, `nightly_quiet_window_runnable=2`, `nightly_quiet_window_ready_now=0`, and `0` task records/verdicts/gold tuples.
- 2026-07-06: W2 active-safe deterministic watch batch recorded as `epyc-orchestrator` `ba0cc164`. `autopilot_planner_provider_watch` initially exposed a schema gap: the underlying provider health report legitimately returns `status=waiting_for_planner_turn`, but the lab job output contract did not admit that healthy waiting state. The contract/test were tightened, the failed watch was rerun, and the canonical queue now contains `7` active-safe deterministic task records with `7` pending reviews and `0` review-candidate records/verdicts/gold tuples. Validation: focused lab suite `26 passed`, all `13` lab job output contracts validated, ruff passed, active-safe batch returned `n_ok=6`/`n_failed=1` followed by targeted retry `n_ok=1`, readiness now reports `active_safe_deterministic_task_records=7` and `pending_reviews=7`, AutoPilot remained `code_stale=false`, GitNexus refreshed, and the branch was pushed.
- 2026-07-06: W2 batch-review template export landed as `epyc-orchestrator` `a83cc676`. `scripts/lab/review_queue_report.py` now includes both `review_batch_template` objects and `review_batch_template_jsonl`, so pending queue items can be copied into `scripts/lab/apply_review_batch.py` after human/cloud review instead of being handled one command at a time. The reporter remains read-only; applying verdicts still goes through `record_verdict.py` and the existing F3 gold-tuple path. Validation: focused lab suite `26 passed`, ruff passed, py_compile passed, all `13` lab job output contracts validated, live reporter returned `8` pending active-safe records and `8` template rows, active-safe `lab_review_queue_watch` smoke passed, AutoPilot remained `code_stale=false`, GitNexus refreshed, and the branch was pushed.
- 2026-07-06: W2 review-packet rendering landed as `epyc-orchestrator` `95d2d39f`. `scripts/lab/review_queue_report.py` now has `--markdown` and `--output-md` so pending queue items and the editable `lab_review_batch.v1` JSONL can be reviewed as a markdown packet without mutating verdicts. Live packet `orchestration/reports/lab_review_queue_report_20260706T131453Z.md` reports `8` pending active-safe deterministic rows, `0` review-candidate rows, and no missing outputs. Validation: `tests/unit/test_lab_review_queue_report.py` plus `tests/unit/test_lab_run_shadow_jobs.py` passed (`16 passed`), ruff and py_compile were clean, GitNexus refreshed, and the branch was pushed.
- 2026-07-07: First real quiet-window model-backed lab batch completed and reviewed. `run_shadow_jobs.py --quiet-window-only --execute-chat` produced non-mock rows for `handoff_freshness_lint` and `attestation_watch`; `scripts/lab/run_job.py` now canonicalizes lab vocabulary roles to live orchestrator roles and rejects any mock response. `handoff_freshness_lint-20260707T002120Z-a99a903a` was accepted as `lab_gold_tuple.v1`; `attestation_watch-20260707T002559Z-df29d4c9` was rejected as a negative `lab_gold_tuple.v1` after cloud review caught a false attestation-empty claim. The older duplicate lint row and dry-run attestation prompt were closed as non-gold verdict artifacts. Current review queue: `pending_reviews=0`, `verdicts=12`.

#### Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. W3/W4 are ongoing — report ladder promotions per job in progress logs.

## Track: frontier-f3-data-flywheel
<!-- gate: none -->

> Folded from `handoffs/active/frontier-f3-data-flywheel.md` @ `8e46a59e2886` on 2026-11-02 (BRF-T1-F9, route 1a, operator D1/D5; retired row EVL-25 → EVL-29). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Frontier F3 — The Data Flywheel: Train on What the Lab Already Generates

**Status**: W1 capture hygiene and W2 dataset builders are on the current orchestrator branch; reviewed intake-label recording, reviewed-label joins, stdlib CPU triage-baseline scaffold, a 120-row actionable review queue, machine-readable/markdown review-readiness packets, trusted-label-source baseline guards, and F2 lab batch verdict/gold-tuple capture tooling are live. The operator-delegated review apply reached the 100-label readiness gate and the held-out triage-baseline report passed (`0.90` accuracy vs `0.85` threshold); real F2-W3 tuple evidence is now present from the 2026-07-07 quiet-window lab batch, leaving gfx90a training-viability as the remaining W3 gate before fine-tune work (created from the Fable 5 strategic-frontiers review)
**Created**: 2026-06-12
**Priority**: MED — W1/W2 capture+curation now, W3 training HW-GATED with the MI210 portfolio per operator instruction
**Spec**: [fable5-findings-07-strategic-frontiers.md](../completed/fable5-findings-07-strategic-frontiers.md) §F3 — read it before claiming any waypoint
**Related**: [frontier-f2-self-running-lab.md](frontier-lab-automation.md#track-frontier-f2-self-running-lab) (W3 tuples are this frontier's gold data); [fable5-findings-01c-sequential-verdict-spec.md](../completed/fable5-findings-01c-sequential-verdict-spec.md) (outcome labels); [gpu-drafter-mi200-investigation.md](../archived/gpu-drafter-mi200-investigation.md) (drafter training); [retrain-routing-models.md](routing-program.md#track-retrain-routing-models) (routing-classifier stack reuse); [../completed/frontier-f7-economic-ledger.md](../completed/frontier-f7-economic-ledger.md) (planner-distill economic justification)

#### Why

Open-source + CPU-only created a no-training culture, yet the lab sits on
unique corpora it uses for nothing: `logs/planner_archive.jsonl` (every
planner/critic exchange with cost fields), 694 intake entries with verdicts,
the new per-question eval ledger, deep-dive→decision chains, and F2's job
tuples. A local planner alone would eliminate the cloud-dependency incident
class (out-of-credits halt, 300s timeouts, resumed-session contamination).
Capture and curation cost nothing now; training waits for the GPU.

#### Waypoints

- [x] **W1 — capture hygiene, NOW, zero cost** (1–2 days) ✅ 2026-07-14 all W1 items confirmed live on current branch (2026-06-28 + 2026-07-04 refresh): patch `controller_io.py` so FAILED planner calls archive too (move `_append_planner_archive` before the early return — known gap); log intake-triage decisions as labeled `{source_features, verdict}` rows; confirm the per-question ledger (N2) journals per-trial outcome vectors; confirm F2-W3 tuple capture. Deliverable: `docs/reference/datasets.md` listing each corpus, schema, era-labeling rule, intended model — acceptance: page exists and every corpus has an era-labeling rule. **Current-lineage status 2026-06-28**: current `controller_io.py` already archives failed planner calls in the newer planner-provider schema; `docs/reference/datasets.md` and `scripts/datasets/record_intake_triage_verdict.py` are live; `epyc-orchestrator` `2abf8ff2` makes `build_triage_set.py` consume reviewed `reviewed_intake_triage_verdict.v1` rows; `epyc-orchestrator` `c27664f8` adds `prepare_intake_triage_review.py` and a prompt-free 120-row review queue at `orchestration/datasets/intake_triage_review_queue.jsonl`; `epyc-orchestrator` `4f860e20` adds `intake_triage_review_status.py` plus non-operator `shadow_job` queue label-source support; `epyc-orchestrator` `f8738b24` prevents `shadow_job` labels from suppressing operator review by default. **2026-07-04 refresh**: failed provider-call archive, per-question ledger, and F2 lab tuple scaffolds are confirmed live on the current branch; remaining W1/W2 work is real reviewed intake labels and real quiet-window F2 outputs/verdicts/`lab_gold_tuple.v1` rows.
- [x] **W2 — dataset builders, pre-GPU** (3–4 days): `scripts/datasets/build_planner_sft.py` (planner_archive -> (context, action) pairs labeled by measured outcome — keep confirmed/critic-approved, drop contaminated eras) + `build_triage_set.py` (intake index -> classification set); train the CPU-feasible triage baseline now (BGE embedding + small MLP, routing-classifier stack reused) — acceptance: triage baseline >=85% agreement with operator verdicts on a held-out 100. **Builder scaffolds landed current branch 2026-06-14**: `epyc-orchestrator` `74ae865` adds planner-SFT and intake-triage JSONL builders, manifests, and direct CLI execution. Live no-inference smokes emitted 694 intake rows and 2,685 planner rows under `/mnt/raid0/llm/tmp/f3-datasets-smoke-20260614-codex`; intake-triage output had no `citation_context` / `IGNORE PRIOR` / `notes` / `source_text` field leakage. **Reviewed-label join landed 2026-06-21**: `epyc-orchestrator` `2abf8ff2` lets `build_triage_set.py` overlay the latest reviewed label per intake ID, emit reviewed-label provenance, and require reviewed labels for gold/held-out sets. **Stdlib baseline scaffold landed 2026-06-21**: `scripts/datasets/train_intake_triage_baseline.py` trains/evaluates a deterministic naive-Bayes baseline over reviewed labels only by default, writes aggregate-only reports, and reports `insufficient_reviewed_labels` until the 100-reviewed-label acceptance set exists. **Review queue landed 2026-06-27**: `prepare_intake_triage_review.py` excludes already reviewed IDs, supports verdict filters, and generated 120 actionable rows from `worth_investigating`, `adopt_patterns`, `adopt_component`, and `new_opportunity` items. **Readiness reporter landed 2026-06-28**: `intake_triage_review_status.py` reports reviewed-label readiness without raw text. **Trusted label authority landed 2026-06-28**: `epyc-orchestrator` `f8738b24` makes operator labels the default trusted source for readiness, baseline training, and reviewed-label overlay; shadow labels require explicit opt-in. **Review packet automation landed 2026-07-06**: `intake_triage_review_status.py --output-md --batch-template` now emits an operator-facing markdown packet plus blank-verdict JSONL batch rows. **Trusted-label gate cleared 2026-07-07**: operator-delegated batches appended 100 rows to `orchestration/datasets/intake_triage_reviewed.jsonl`; refreshed status `orchestration/reports/intake_triage_review_status_20260707T000650Z.json` reports `100` trusted reviewed labels, `0` labels needed, and `ready_for_baseline=true`. **Baseline acceptance passed 2026-07-07**: `orchestration/reports/intake_triage_baseline_report_20260707T000910Z.json` reports `acceptance_pass`, `80` train rows, `20` held-out rows, `18` correct, and `0.90` accuracy against the `0.85` threshold.
- [x] **W-aux — trace publish/redaction reference (pi-share-hf, intake-736), pre-GPU** ✅ 2026-07-29: the MIT `pi-share-hf` tool (Collect → Redact → TruffleHog secret-scan → LLM-review → JSONL → Upload-to-HF) is a pattern reference for two GAPS this flywheel lacks: (1) an **UPLOAD/publish** step, and (2) **general secret/PII redaction of RAW traces** (`planner_archive.jsonl`, `agent_audit.log`) — broader than W1/W2's field-name quarantine (`source_text`/`citation_context`). **Do NOT re-implement** the existing quarantine + operator trusted-label review (`f8738b24`). Adopted the hygiene patterns only in `epyc-orchestrator` `e57be4c8` / `16f9d6c3`: fail-closed deterministic credential and high-entropy scanning with separate reasoning-span reporting. It does not authorize upload/publish or training, and it does not replace operator label authority. verdict adopt_patterns — mine the pattern, don't trust the gate wholesale.
- [x] **W-aux preflight CLI — raw-trace export hygiene.**
  `epyc-orchestrator` now has `scripts/datasets/raw_trace_publish_preflight.py`
  for candidate `planner_archive.jsonl` / `agent_audit.log` exports. It reuses
  production credential redaction, adds high-entropy token backstop checks with
  hash-field false-positive guards, separately reports reasoning/trace-field
  hits, and exits nonzero on any hit or parse error. This does not authorize
  publish/training and does not replace operator label authority. Focused tests
  passed (`44 passed`), ruff was clean, and a clean candidate CLI smoke returned
  `ok=true`. ✅ 2026-07-06
- **[declined: ws58 2026-11-03 content-review: training, out of scope]** **W3 — GPU fine-tunes (MI210 present since 2026-07-02; the HW gate is CLEARED. The DATA gate is now satisfied by 100 trusted reviewed triage labels plus initial F2 gold tuples; gfx90a TRAINING-VIABILITY is still [unverified] — a LoRA/GRPO/SFT smoke on a small model via TRL/verl-ROCm must pass before any of (a)–(c) is scoped. NOTE: gradient-based QLoRA (below) is what rides the training-viability gate; a gradient-FREE Evolution-Strategies path (intake-564/563, forward-pass-only) would sidestep it entirely and is tracked in learned-routing-controller.md)**: (a) planner-distill — QLoRA a Qwen3.5-9B-class base on W2's SFT set, acceptance: shadow-draft mode with ≥80% cloud-critic approval over 100 trials before any binding use; (b) drafters per the α measurement (FastDraft path, already gated in backlog); (c) judge/rubric model for EV-9 (unblocks rubric-scored suites in F1-W3) — acceptance: each fine-tune gets a MEASUREMENT.md protocol entry before its first reported number.
  - **W3 candidate variant — self-distillation (intake-736 context / intake-739 reference, MI210-gated)**: the operator direction — self-distill the compressed CPU worker from own agent-tool traces + a GLM-5.2-FP8 generation loop + frontier HF traces (~210 GB) — is an **on-policy** distillation variant, distinct from W3a's **offline** planner-distill QLoRA; V4-Pro-DSpark's "on-policy distillation" consolidation (intake-739) is a reference point only, not an endorsement. GATES: external frontier-HF / GLM-loop traces are **untrusted** under the `f8738b24` authority model → require an explicit trusted-source opt-in before feeding gold/held-out sets; must pass a MEASUREMENT.md protocol + shadow-approval before any binding use.

#### Gates & pitfalls

- W3 HW gate CLEARED 2026-07-02 (MI210 landed). DATA gate satisfied. **Training-viability gate CLEARED 2026-08-12** — LoRA/SFT on a real pretrained model executes on the MI210, loss `0.9174 → 0.4077` (55.6%) in 60 steps with GPU residency sampled during the run: [`artifacts/gpu-aux-baselines/a9_gfx90a_training_viability_20260812.md`](../../artifacts/gpu-aux-baselines/a9_gfx90a_training_viability_20260812.md). **All three W3 gates are now met**; (a)–(c) may be scoped.
  - **This gate was never a measurement problem.** It sat 29 days because a prior session reported "no PyTorch on the host" from a `find / -maxdepth 6`, which structurally cannot reach a venv `site-packages` at depth 8+. torch `2.5.1+rocm6.2` with `gfx90a` was installed the whole time in `/mnt/raid0/llm/tools/geak-v1-rocm62-py312` (trl `1.9.2`, peft `0.20.0`). **This row also never named a software gate** — it listed only HW and DATA, so a cleared HW gate read as "runnable". Any future row of this shape should name its runtime dependency explicitly.
  - **Carry-forward for W3(a):** transient bf16 LoRA gradients reach ~1e34 on layer-0 attention projections while loss converges normally (AdamW is per-parameter scale-invariant). `torch.nn.utils.clip_grad_norm_` norms in fp32 and returns `inf` on that, propagating a NaN scale into every parameter. Use fp64 or per-tensor clipping.
  - **4-bit QLoRA specifically is NOT yet runnable**: `bitsandbytes 0.50.0` imports and exposes `Linear4bit`, but ships no gfx90a code object for ROCm 6.2 and fails with `no kernel image is available for execution on the device`. A source build is viable (`hipcc 6.2` present). Likely unnecessary — a 9B at bf16 plus LoRA state is ~22–25 GB against 64 GB of VRAM.
  - The gradient-free ES alternative (learned-routing-controller.md) is **not** a substitute: it has zero checkbox rows, its section says "do NOT branch a separate handoff", and its own two gates are unmet. It sidesteps this gate by not training.
  - [x] **Build `bitsandbytes` from source for gfx90a / ROCm 6.2** ✅ 2026-08-12 — built at tag `0.50.0` with `cmake -DCOMPUTE_BACKEND=hip -DBNB_ROCM_ARCH=gfx90a`, source at `/mnt/raid0/llm/tools/bitsandbytes-src`, installed into the `geak-v1-rocm62-py312` venv. **Verified with a real NF4 QLoRA run, not an import**: 168 `Linear4bit` modules materialised, 451.3 MB footprint (vs ~1 GB bf16), loss `1.1122 → 0.4062` (**63.5%** drop) over 60 steps, 3,102 MB peak VRAM. **4-bit QLoRA is now available on gfx90a.** The PyPI wheel remains broken here — it ships only a ROCm 6.4 code object and dies with `no kernel image is available for execution on the device`; anyone reinstalling from PyPI silently loses this.
  - **[declined: ws58 2026-11-03 content-review: training, out of scope]** **A GRPO run that demonstrates LEARNING, not just execution.** The 2026-08-12 smoke proved the loop runs; it proved nothing about optimisation, because `clipped_ratio: 1` meant every completion hit the token cap and the length reward could not be moved. Needs: a reward the policy can actually change, `max_completion_length` above the natural completion length so terminations are real, and a **pre-registered** pass rule (e.g. final-quintile mean reward above first-quintile by a stated margin, fixed before the run). Until that exists, no GRPO quality claim is licensed.
  - [x] **Confirm bf16 LoRA on a 9B-class base fits the MI210 before spending that build.** ✅ 2026-09-15 —
    measured on the 7B STAND-IN (Qwen2.5-7B-Instruct; the Qwen3.5-9B weights are not on disk, GGUFs deleted
    2026-09-01), so this is a **LOWER BOUND**. bf16 + LoRA r16/seq512/batch4 = 39.32 GB peak; r32/seq2048/batch1 =
    39.99 GB peak; no OOM, 0.58-0.80 steps/s, grad norms clipped in **fp64** (transients to 1.55e8 — an fp32 norm
    would have NaN'd every parameter), residency sampled DURING the steps. Scaled by params (9.5/7.66, weights
    19.0 GB) the 9B lands ~49.6 GB of 63.98 GB, ~22% headroom, so **4-bit QLoRA is retired for the ~2k-token/step
    shape** — NOT for longer context: the 7B OOMs at 8192 tokens/step even with gradient checkpointing. The
    "~22-25 GB" estimate below was LOW: the non-weight term alone is ~24.7 GB (activations + 152k-vocab logits +
    the fp32 loss copy); LoRA optimizer state is under 1 GB. Evidence
    `/mnt/raid0/llm/tmp/sub-gpu/evl25/run{A,B,C}_result.json`; harness parameterised (every default = the
    2026-08-12 values) in `28fac70a`.
  - *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-frontier-f3-data-flywheel on 2026-11-03 (BRF-T1-MEQ, operator D2): "Repeat the W3 fit check on the real Qwen3.5-9B …".*
  - [x] _(superseded estimate, kept for the record)_ **Confirm bf16 LoRA on a 9B-class base fits the MI210 before spending that build.** Arithmetic says ~22–25 GB against 64 GB, which would retire the 4-bit requirement for W3(a) entirely. One load + a few steps settles it. Do this task *first* — it may delete the one above.
    2026-09-15: BLOCKED — Qwen3.5-9B HF weights absent (its GGUFs deleted 2026-09-01; `models--unsloth--Qwen3.5-9B-GGUF` is an empty stub). Needs operator: approve the ~19 GB bf16 download (estimate) or rule on a Qwen2.5-7B lower-bound stand-in (`/mnt/raid0/llm/hf/Qwen2.5-7B-Instruct`). Use venv `geak-v1-rocm62-py312`; `a9_stage2_trl_sft.py` hardcodes 0.5B/r16/len64/60 steps and needs parameters plus fp64 grad-norm clipping.
  - **[declined: ws58 2026-11-03 content-review: a note]** **Environment split is deliberate — do not "consolidate" it.** Two training venvs exist on purpose, each internally consistent: `geak-v1-rocm62-py312` (torch `2.5.1+rocm6.2`, system ROCm 6.2) carries **SFT + 4-bit QLoRA**, both verified; the ROCm 6.3 venv carries **GRPO only**. **The reason is a mixed-runtime hazard, the ROCm analogue of the three-ggml-generations rule in CLAUDE.md:** the source-built `libbitsandbytes_rocm62.so` has **zero torch linkage** and resolves `libhipblas`/`libhipblaslt`/`librocblas`/`librocsolver` from **system `/opt/rocm` 6.2**, while a `+rocm6.3` torch wheel bundles its **own** ROCm 6.3 copies — loading both puts two ROCm runtimes in one address space. Compounding it, `bitsandbytes/cextension.py` selects its library by **runtime-detected ROCm version**, so under a 6.3 torch it looks for `libbitsandbytes_rocm63.so`, which does not exist (the built file is `_rocm62`); `BNB_ROCM_VERSION=62` would force it, but that deliberately pairs a 6.2-linked kernel with a 6.3 runtime and would need a numerical check, not just a successful load. Rebuilding bnb against 6.3 is not possible here — `/opt/rocm` **is** 6.2. Hence: never run bitsandbytes in the 6.3 venv.
  - [x] **GRPO end-to-end smoke on gfx90a** ✅ 2026-08-12 — **mechanical viability only; learning is NOT demonstrated and is not claimed.** 8 GRPO steps completed at 11.3 samples/s, 3,276 MB peak VRAM, GPU residency sampled during the run, `grad_norm` finite throughout (3.3–6.1). The full RL loop executes: generation → reward → advantage → policy update through a LoRA adapter. **What it does not show:** reward went `-5.667 → -4.854` while bouncing (`-4.021`, `-5.583`, `-3.25`) — that is noise. `completions/clipped_ratio: 1` and `mean_terminated_length: 0` mean every completion hit the 16-token cap and none terminated naturally, so the length reward was unoptimizable by construction. A learning claim needs a reward the policy can actually move and a pre-registered rule; this smoke had neither, by design.
    Unblocked by upgrading torch, not by downgrading trl. Root cause was a **three-way** skew, not the two-way one first reported: `trl >= 0.20` imports `FSDPModule` (needs torch >= 2.6), while `trl 0.19.1` — the last release without it — breaks against `transformers 5.15.0`, whose `_is_package_available` returns a **tuple** that makes trl's `if is_vllm_available():` truthy and forces an unguarded `import vllm`. So a trl pin meant downgrading transformers too; one upgrade beat two downgrades.
    Environment: `/mnt/raid0/llm/tools/train-rocm63-py313` (Python 3.13, torch `2.7.1+rocm6.3`, trl `1.9.2`, 23 GB). **A ROCm 6.3 wheel on a ROCm 6.2 host works** — verified, not assumed: `hip 6.3.42131`, MI210 visible, and a real bf16 GEMM executes on device. The wheels bundle their own ROCm runtime, which is exactly why the mixed-runtime note above matters.
- Era-label training corpora per MEASUREMENT.md §5 — never train on pre-scrub narrative text (gate-lock-era strategies etc.).
- Planner SFT must include *failure* cases or it learns only optimism.
- Deployment is always shadow-first behind the same reliability ladder as F2.

#### Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. W1/W2 can complete and be reported long before W3 ungates — do not hold the handoff open as "blocked" on the GPU; mark W3 gated explicitly.

#### Progress

- 2026-07-06: Added a raw-trace publish preflight note to
  `epyc-orchestrator/docs/reference/datasets.md` covering deterministic
  secret/PII scanning, entropy/ML backstops, and reasoning-span scans as
  hygiene-only checks for future trace export/publish paths. This advances
  W-aux without changing the quarantine/operator-review trust boundary.
- 2026-07-07: Applied the first F3 intake-triage review packet under explicit
  operator delegation. `epyc-orchestrator`
  `orchestration/datasets/intake_triage_review_batch_filled_20260707T000328Z.jsonl`
  accepted the first 25 prompt-free queue suggestions and appended them via
  `apply_intake_triage_review_batch.py --apply` to
  `orchestration/datasets/intake_triage_reviewed.jsonl` with
  `label_source=operator` and reviewer `codex-operator-delegated`. Refreshed
  status artifacts
  `orchestration/reports/intake_triage_review_status_20260707T000402Z.json`,
  `orchestration/reports/intake_triage_review_packet_20260707T000402Z.md`,
  and
  `orchestration/datasets/intake_triage_review_batch_template_20260707T000402Z.jsonl`
  report `25/100` trusted reviewed labels and queue the next 25 rows.
- 2026-07-07: Completed the remaining operator-delegated F3 reviewed-label
  applies through the same recorder path. Additional filled batches
  `orchestration/datasets/intake_triage_review_batch_filled_20260707T000642Z.jsonl`,
  `...000645Z.jsonl`, and `...000647Z.jsonl` brought
  `orchestration/datasets/intake_triage_reviewed.jsonl` to `100` trusted
  operator-source labels. Final status
  `orchestration/reports/intake_triage_review_status_20260707T000650Z.json`
  is `ready_for_baseline=true`, with `20` non-blocking queue rows still
  available for future review.
- 2026-07-07: Ran the W2 held-out triage-baseline acceptance report from the
  reviewed-only corpus. `build_triage_set.py --require-reviewed-labels`
  emitted
  `orchestration/datasets/intake_triage_reviewed_only_20260707T000910Z.jsonl`
  with `100` operator-source rows, and
  `train_intake_triage_baseline.py` wrote
  `orchestration/reports/intake_triage_baseline_report_20260707T000910Z.json`
  with `status=acceptance_pass`, `80` train rows, `20` held-out rows, and
  `18/20 = 0.90` accuracy against the `0.85` acceptance threshold.
- 2026-07-07: Cleared the F2 tuple-evidence blocker for W3 readiness. The
  quiet-window lab batch produced real non-mock `handoff_freshness_lint` and
  `attestation_watch` rows; cloud review accepted the handoff-lint row as a
  positive `lab_gold_tuple.v1` and rejected the attestation row as a negative
  `lab_gold_tuple.v1` because it falsely claimed the attestation latest file
  was empty. The lab review queue now reports `pending_reviews=0`. Remaining
  W3 gate: gfx90a training-viability smoke.
- 2026-07-06: Intake-triage review packet automation landed in
  `epyc-orchestrator`. `intake_triage_review_status.py` can now write a
  markdown review packet and operator-fillable JSONL batch template while
  preserving dry-run/default-off label application. Live artifacts:
  `orchestration/reports/intake_triage_review_packet_20260706T235801Z.md`,
  `orchestration/reports/intake_triage_review_status_20260706T235801Z.json`,
  and
  `orchestration/datasets/intake_triage_review_batch_template_20260706T235801Z.jsonl`.
  The trusted-data gate remains `0/100` labels until reviewed rows are filled
  and applied.
- 2026-07-06: Implemented the raw-trace publish preflight as an executable
  no-inference scanner in `epyc-orchestrator`
  `scripts/datasets/raw_trace_publish_preflight.py` with focused unit coverage.
  It fail-closes candidate raw-trace exports on credential-pattern hits,
  high-entropy token shapes, parse errors, or hits inside reasoning/trace
  fields, while preserving hash false-positive guards.
- 2026-07-06: F2 gold-tuple capture is now batchable via `epyc-orchestrator`
  `2bdfe35f`. `scripts/lab/apply_review_batch.py` reuses the existing
  `record_verdict.py` path to persist reviewed verdict batches as
  `lab_review_verdict.v1` rows plus `lab_gold_tuple.v1` files, and
  `scripts/lab/review_queue_report.py` exposes pending review items without
  mutating trust state. Live report still shows `0` task records / `0`
  pending reviews, so this removes a capture-path gap but does not satisfy the
  trusted-data gate; real quiet-window lab outputs and reviewed verdicts remain
  required.
- 2026-07-06: F2 pending-review evidence is now easier to inspect via
  `epyc-orchestrator` `95d2d39f`. `scripts/lab/review_queue_report.py
  --markdown/--output-md` renders pending queue rows and editable
  `lab_review_batch.v1` JSONL into a review packet. Live packet
  `orchestration/reports/lab_review_queue_report_20260706T131453Z.md` shows
  `8` active-safe deterministic rows awaiting operator verdicts and `0`
  review-candidate rows; this improves review throughput but still does not
  satisfy the trusted-data gate until verdicts are actually recorded.
- 2026-07-06: The first quiet-window F2 batch is now command-planned via
  `epyc-orchestrator` `88f66ae6`. `scripts/lab/quiet_window_lab_plan.py`
  reports the model-backed jobs ready for the next AutoPilot-stopped window and
  emits the exact run/review/batch-apply commands that will turn outputs into
  pending review items and then `lab_gold_tuple.v1` evidence. Current smoke
  selected `handoff_freshness_lint` and `attestation_watch` but correctly
  blocked execution while AutoPilot and live llama servers were active. This is
  still prep, not data: the F3 trusted-data gate remains `0` task records /
  `0` verdicts / `0` gold tuples until that quiet-window command is actually
  run and reviewed.
- 2026-06-13: W2 builder scaffolds branch-ready at `feat/data-flywheel-builders` tip `4a81d06`. Validation: `python3 -m py_compile scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py tests/unit/test_dataset_builders.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py` -> 3 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py tests/unit/test_dataset_builders.py` passed; `git diff --cached --check` passed. Live-source smokes wrote planner and triage outputs/manifests under `/mnt/raid0/llm/tmp/f3-datasets-smoke-20260613`.
- 2026-06-13: Current-lineage F3 capture/build branch-ready at `feat/intake-triage-label-capture` tip `87cfc81` on top of F5 live lineage `a7b87c1`. It carries forward the failed planner-call archive fix and dataset builders, then adds reviewed intake-triage verdict capture plus reviewed-label joins. Validation: `python3 -m py_compile scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py scripts/datasets/record_intake_triage_verdict.py tests/unit/test_dataset_builders.py tests/unit/test_autopilot_controller_io.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py tests/unit/test_autopilot_controller_io.py` -> 40 passed, 1 pytest config warning; `uv run --with ruff ruff check ...` passed; `uv run --with ruff ruff format --check ...` passed; `git diff --check` passed. Live-source smokes wrote `/mnt/raid0/llm/tmp/f3-intake-label-smoke-20260613/intake_triage.jsonl` with 694 rows and `/mnt/raid0/llm/tmp/f3-intake-label-smoke-20260613/intake_triage_reviewed_only.jsonl` with 1 reviewed-only row; `rg "citation_context|IGNORE PRIOR|notes|source_text"` over emitted classifier outputs returned no hits.
- 2026-06-14: W2 builder scaffolds integrated onto current `fix/substring-scorer-digit-separators` lineage as `epyc-orchestrator` `74ae865` (`Add data flywheel dataset builders`). Validation on current branch: scoped ruff passed; py_compile passed; `tests/unit/test_dataset_builders.py` passed 3. No-inference live-source smokes wrote `/mnt/raid0/llm/tmp/f3-datasets-smoke-20260614-codex/intake_triage.jsonl` (694 rows) and `planner_sft.jsonl` (2,685 rows with `--include-excluded`). Intake-triage quarantine field scan returned no hits. The older failed-planner archive commit was not replayed because current `controller_io.py` already archives planner calls with statuses `timeout`, `process_failed`, `stale_session`, `missing_cli`, and `success`; `gitnexus impact _append_planner_archive` on the current hook was LOW.
- 2026-06-21: Reviewed intake-label joins landed on current orchestrator branch as `2abf8ff2` (`Join reviewed intake labels into triage dataset`). `build_triage_set.py` now loads `orchestration/datasets/intake_triage_reviewed.jsonl` by default when present, prefers the latest reviewed row per `intake_id`, carries `destination_index`, `reviewed_at`, `label_source`, and `output_contract_version`, and supports `--require-reviewed-labels` for reviewed-only gold/held-out sets. Validation: GitNexus impact LOW for `build_example`, `build_dataset`, `run`, and `record_intake_triage_verdict.py`; `python3 -m py_compile scripts/datasets/build_triage_set.py scripts/datasets/record_intake_triage_verdict.py tests/unit/test_dataset_builders.py`; `uv run --with ruff ruff check ...`; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py` -> `6 passed`; default live-source CLI smoke emitted 720 rows; temp reviewed-label smoke over real `intake-001` emitted exactly one reviewed-only row and privacy scan found no `source_text`, `citation_context`, or prompt-injection text.
- 2026-06-21: Stdlib CPU triage-baseline scaffold landed on current orchestrator branch. `scripts/datasets/train_intake_triage_baseline.py` reads the reviewed-label triage JSONL, filters to reviewed examples by default, trains/evaluates a deterministic multinomial naive-Bayes baseline, and writes aggregate-only JSON reports with acceptance status. It deliberately reports `insufficient_reviewed_labels` until the 100-row reviewed-label gate exists; no NumPy/sklearn dependency was added because those packages are absent in the active environment. Validation: GitNexus impact LOW for the touched dataset test target and `_common.load_jsonl`; `python3 -m py_compile scripts/datasets/train_intake_triage_baseline.py tests/unit/test_dataset_builders.py`; `uv run --with ruff ruff check scripts/datasets/train_intake_triage_baseline.py tests/unit/test_dataset_builders.py`; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py` -> `8 passed`; live-source smoke under `/mnt/raid0/llm/tmp/f3-triage-baseline-smoke-20260621T041938Z` confirmed the current default reviewed-label corpus has 0 reviewed rows and the baseline reports `insufficient_reviewed_labels` with no raw text in the report.
- 2026-06-21: F7's first monthly economic review (`epyc-orchestrator` `876172e4`, `orchestration/reports/economic_review_2026-06.md`) records F3-W3a planner-distill as economically justified for operator review after the 2026-06-06 planner-spend projection exceeded threshold (`$410.75` vs `$250.00`). This does not ungate training: W3 remains HW-gated on the MI210 path and must still meet its shadow approval protocol before any binding use.
- 2026-06-27: Intake-triage review queue landed on current orchestrator branch as `c27664f8` (`Prepare intake triage review queue`). `scripts/datasets/prepare_intake_triage_review.py` emits prompt-free `intake_triage_review_queue.v1` rows, excludes already reviewed IDs, supports `--include-verdict` / `--exclude-verdict`, and writes a manifest. The committed queue contains 120 actionable rows from the real research intake index (`worth_investigating`, `adopt_patterns`, `adopt_component`, `new_opportunity`) and omits quarantined source/citation text. Validation: GitNexus impact LOW for reused `build_triage_set.py:build_dataset`; `uv run python -m py_compile scripts/datasets/prepare_intake_triage_review.py`; `uv run ruff check scripts/datasets/prepare_intake_triage_review.py tests/unit/test_dataset_builders.py`; `uv run pytest tests/unit/test_dataset_builders.py -q` -> `9 passed`.
- 2026-06-28: Review-readiness status landed on current orchestrator branch as `4f860e20` (`Report intake triage review readiness`). `scripts/datasets/intake_triage_review_status.py` reports aggregate queue/reviewed-label progress and refuses to mark the baseline gate ready until the reviewed-label threshold is met; `prepare_intake_triage_review.py` now threads `--label-source shadow_job` through review rows and recorder commands so synthetic or delegated review queues are not mislabeled as direct operator labels. Live status smoke over the committed queue reports `status=needs_reviewed_labels`, `queue_rows=120`, `reviewed_rows=0`, `remaining_queue_items=120`, `labels_needed=100`, and `ready_for_baseline=false`. Validation: GitNexus impacts LOW for orchestrator code/tests/docs; `uv run python -m py_compile scripts/datasets/intake_triage_review_status.py scripts/datasets/prepare_intake_triage_review.py tests/unit/test_dataset_builders.py`; `uv run pytest tests/unit/test_dataset_builders.py -q` -> `13 passed`; `uv run ruff check scripts/datasets/intake_triage_review_status.py scripts/datasets/prepare_intake_triage_review.py tests/unit/test_dataset_builders.py`; `git diff --check`.
- 2026-06-28: Trusted reviewed-label authority landed on current orchestrator branch as `f8738b24` (`Enforce trusted intake triage label sources`). Default authority is now `operator` across `build_triage_set.py`, `prepare_intake_triage_review.py`, `intake_triage_review_status.py`, and `train_intake_triage_baseline.py`; missing `label_source` rows are treated as legacy operator rows, while `shadow_job` rows no longer satisfy baseline readiness, baseline training, reviewed-label overlays, or operator-review queue suppression unless explicitly requested through the new trusted-source CLI flags. Live status smoke remains `status=needs_reviewed_labels`, `trusted_label_sources=["operator"]`, `trusted_reviewed_rows=0`, `queue_rows=120`, and `labels_needed=100`. Validation: GitNexus impacts LOW for all touched F3 dataset entry points; `uv run python -m py_compile ...`; `uv run ruff check ...`; `uv run pytest -q tests/unit/test_dataset_builders.py` -> `17 passed`; adjacent `tests/unit/test_dataset_builders.py tests/unit/test_lab_readiness_report.py` -> `22 passed`; A10/action guard coverage `tests/unit/test_seed_operator_strategies.py tests/unit/test_autopilot_actions.py` -> `82 passed`; `git diff --check`; orchestrator GitNexus refreshed at `f8738b2`.
- 2026-07-04: Dataset inventory refresh removed stale branch-ready/deploy language from `epyc-orchestrator/docs/reference/datasets.md`. Live evidence: `intake_triage_review_status.py --json` reports `120` queue rows, `0` trusted reviewed unique intake IDs, `100` labels needed, and `ready_for_baseline=false`; `readiness_report.py --json` reports `enabled_jobs=2`, `nightly_runnable=2`, `nightly_ready_now=0`, `task_records=0`, `verdicts=0`, and `gold_tuples=0`; current journals contain per-question vectors (`trial 789`, `55` `question_results`). This means the remaining F3 bottleneck is trusted review data collection, not replaying old capture branches.

#### Research intake 2026-10-21 — open-model backdoors, control-vector projection, Qwen3.8 post-train (research intake entries 2191–2213, see research/intake_index.yaml)

- [x] **F3-W3-P1 — Per-sample poison screen before any W3 training.** The W2 builders emit a screening report (quarantined count and reasons: tool calls to hosts outside the run allowlist, credential-path reads, instructions originating from fetched content) and refuse to export a training set containing unscreened external traces; external trace sources carry commit sha and sha256 (SEC-ART-1 shape) (intake-2199#02, intake-2210#03). ✅ 2026-10-21: `scripts/datasets/poison_screen.py` + `build_planner_sft.py` integration, screening report, export refusal; 44 tests pass (epyc-orchestrator bc61f308). Triage builder out of scope (no trace rows).

##### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **F3-LB1 — Privacy gate for trace-derived outputs: per-session results live only under a private gitignored path; commits carry aggregate counts and rule text only, routed through raw_trace_publish_preflight; extend the staged PII guard to transcript-JSON shapes (intake-2387, intake-2389).** ✅ 2026-10-22
  - [x] **F3-LB1.1 — private root + aggregate gate** ✅ 2026-10-22: `scripts/dev_harness/dh_privacy.py` — private root
    `/mnt/raid0/llm/private/dev-harness-traces` (0700, refuses any git work tree, the vault/claude-backups and the
    harness stores); `validate_aggregate` (counts + rule text only, per-session keys refused); `publish_aggregate`
    writes only after orchestrator `raw_trace_publish_preflight` exits 0. `.gitignore` adds `dev-harness-traces/`.
  - [x] **F3-LB1.2 — land the PII-guard transcript scan (needs a D9 ack).** Landed 0ee545eb1 with operator D9 ack 2026-10-22 ✅ 2026-10-22. Prepared, uncommitted, in worktree
    `/mnt/raid0/llm/worktrees/f8-locals-b1-root`: `scripts/hooks/pii_precommit.sh` `[transcript]` scan (Claude/Codex/
    opencode line shapes + per-session `dev-harness-*.v1` schemas, also the first 256 KB of >1 MB blobs; zero hits
    over the tracked tree) and `tests/dev_harness/test_pii_transcript_shapes.py` (10 real-hook cases pass; 92 existing
    PII hook tests pass). `check_d9_loop_plane.py` refuses a hooks change without a `D9-ack:` line, which only the
    operator can give; commit both files together with that line.

## Track: stale-open-audit-2026-07-18
<!-- gate: none -->

> Folded from `handoffs/active/stale-open-audit-2026-07-18.md` @ `8e46a59e2886` on 2026-11-02 (BRF-T1-F9, route 1a, operator D1/D5; retired row EVL-44 → EVL-29). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Stale-Open Backlog Audit — 2026-07-18

**Status**: ACTIVE/REFRESHING — initial 22-handoff audit completed 2026-07-18; current-inventory reconciliation and exact-partition follow-up opened 2026-07-29.
**Priority**: HIGH
**Created**: 2026-07-18
**Categories**: governance, measurement, handoff-hygiene
**Parent index**: [`master-handoff-index.md`](master-handoff-index.md)

**Trigger**: operator question — *"if the inference-batch-loop consolidation is only 11 checkboxes, what are the remaining ~660 open tasks about?"* The board's headline open-task count (678 active+blocked, 2026-07-18) treats **every unchecked box as live work**. This audit measures how much of that is actually **stale-open**: work that landed, was superseded, deprioritized, parked, or is owned by another handoff — but whose boxes were never flipped (deprioritized ≠ done, so they were correctly never checked; they just shouldn't read as live backlog).

#### Method

For each flagged handoff: read the full file, get git last-touch, classify the leading **Status**/**Priority** verbs, skim every open `- [ ]`, and cross-ref any "owned by / claim X there / superseded by" pointer to confirm where the work really lives. Verdict ∈ `LIVE | PARKED | SUPERSEDED | LANDED | DUPLICATE | MIXED`; each handoff gets a `live_open` vs `stale_open` split. **No checkbox flips** — recommendations are re-anchor / close / split / reactivate / add-`Lifecycle`-override.

Scope = the 22 handoffs the board's status-signal scan flagged (parked/landed keyword in Status or Priority). This is the *candidate* net; the board's own dimming signal is deliberately narrower (5 cards) to avoid ever dimming a live handoff.

#### Headline (all 22 flagged handoffs)

| | Open tasks | Genuinely live | Stale-open |
|---|---:|---:|---:|
| Batch A (kernel/GPU, 8) | 64 | 14 | 50 |
| Batch B (routing/eval/RAG, 7) | 81 | 19 | 62 |
| Batch C (stack/infra, 7) | 28 | 6 | 22 |
| **Total (22)** | **173** | **39** | **134 (77%)** |

**Historical 2026-07-18 finding:** 77% of the open tasks in the flagged handoffs (134 of 173) were stale-open — landed, superseded, deprioritized, parked, or frozen behind an unfired gate. The then-derived `≈544` was a dated heuristic, not a current board count.

Caveat: this audits only the **22 flagged** handoffs (those whose Status/Priority carried a park/landed keyword). The other ~105 open handoffs were not individually audited. The current dispatch inventory, not this historical heuristic, is the source for current raw counts.

#### Per-handoff verdicts

##### Batch A — kernel / GPU

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [cpu-shape-specialized-gemv-decode](../completed/cpu-shape-specialized-gemv-decode.md) | 38 | 2 | MIXED | re-anchor — kernel LANDED 2026-04-24, SIMD Phase 0–5 deprioritized; box only the 2 live graph-fusion tasks |
| [gemma-challenge-kernel-techniques-v7](rocm-kernel-authoring.md#track-gemma-challenge-kernel-techniques-v7) | 9 | 6 | LIVE | keep — split K28 out (owned in mi210 roadmap); correctly NOT board-flagged |
| [llamacpp-v6-consolidation](../archived/llamacpp-v6-consolidation.md) | 6 | 1 | SUPERSEDED | close → completed (v6 cutover shipped 2026-06-26); re-anchor 5 items to v7 |
| [llama-cpp-dsa-contribution](rocm-kernel-authoring.md#track-llama-cpp-dsa-contribution) | 4 | 4 | **LIVE** | **add `Lifecycle: live` override** — board over-flags it "superseded" (only the *original* objective was); D2/D3 re-anchored + live. GLM-5.2 box co-owned by glm51-reap |
| [qwen36-27b-cpu-feasibility](../archived/qwen36-27b-cpu-feasibility.md) | 4 | 0 | PARKED | keep parked (CPU foreclosed) **+ cross-link the MI210 GPU campaign** (see callout) so it doesn't read as "dead model"; consider close |
| [gpu-drafter-mi200-investigation](../archived/gpu-drafter-mi200-investigation.md) | 1 | 0 | LIVE | re-anchor — Stage 4 box blocked on Stages 1–3 (failed economics 2026-07-17); add drafter-redesign task |
| [sarathi-serve-cpu-evaluation](cpu-decode-roofline-program.md#track-sarathi-serve-cpu-evaluation) | 1 | 0 | PARKED | **reactivate** — multi-tenant trigger may have fired via batched-decode E1/E2 (active) |
| [agent-file-prose-compression](frontier-lab-automation.md#track-agent-file-prose-compression) | 1 | 1 | LIVE | keep — single operator rollout decision pending |

##### Batch B — routing / eval / RAG

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [decision-aware-routing](routing-program.md) | 26 | 3 | PARKED | re-anchor — core FROZEN/closed in routing-truth-restoration W8; keep only Factory-ai/URE backlog |
| [learned-routing-controller](routing-program.md#track-learned-routing-controller) | 17 | 2 | MIXED | split — live BGE+MLP rollout decision vs FROZEN Phase 1.5+ expansion |
| [glm51-reap-cpu-evaluation](glm51-reap-cpu-evaluation.md) | 11 | 9 | LIVE | keep — real work; true blocker = operator-approved GLM inference runs |
| [colbert-reranker-web-research](knowledge-pipelines.md#track-colbert-reranker-web-research) | 10 | 2 | PARKED | re-anchor — close S5 request-path NO-GO; keep inference-gated LateOn/DenseOn latency+A/B |
| [internal-kb-rag](knowledge-pipelines.md) | 8 | 0 | LANDED | re-anchor — K1–K7 CERTIFIED 2026-06-13; keep only deferred K8 + optional Hy-MT2 |
| [minddr-deep-research-mode](model-evaluation-queue.md#track-minddr-deep-research-mode) | 8 | 2 | LIVE | keep — MD-9 A/B inference-gated. **Reactivate note**: Phase-2 hardware gate flipped (DGX→MI210 present) |
| [x-mas-text-routing](routing-program.md#track-x-mas-text-routing) | 1 | 1 | LANDED | re-anchor — enforce enabled (`d4a6c927`); convert to standing telemetry-watch |

##### Batch C — stack / infra

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [model-stack-single-source-update-pipeline](stack-lifecycle-program.md#track-model-stack-single-source-update-pipeline) | 7 | 0 | PARKED | re-anchor as the authoritative consumer-SSoT contract; reconcile the stale X-MAS default-off box (enforce already enabled) |
| [standardized-stack-update-pipeline-finalization](stack-lifecycle-program.md#track-standardized-stack-update-pipeline-finalization) | 3 | 0 | **DUPLICATE** | consolidate/close into `stack-change-governance-pipeline`; core landed |
| [per-request-reasoning-budget](context-and-token-economy.md#track-per-request-reasoning-budget) | 4 | 4 | LIVE | keep — llama.cpp implementation genuinely pending (inference window + experimental branch) |
| [unified-trace-memory-service](memory-program.md#track-unified-trace-memory-service) | 3 | 0 | PARKED | split — close landed T1–T6 nav parent; keep T7 (Hermes-daily-use gate, unfired) + consolidation parked |
| [frontier-f2-self-running-lab](frontier-lab-automation.md#track-frontier-f2-self-running-lab) | 2 | 2 | LIVE | keep — W3 accumulating now (real quiet-window batches producing verdicts), W4 sequenced |
| [sliders-local-validation](knowledge-pipelines.md#track-sliders-local-validation) | 8 | 0 | PARKED | **reactivate signal** — KB-RAG K7 reopen precondition FIRED 2026-06-13; surface to operator (still needs explicit ask; else keep parked, LOW/speculative) |
| [security-review-skill](../completed/security-review-skill.md) | 1 | 0 | PARKED | close — skill shipped + in production; keep CI-gate as a deferred backlog note |

#### Cross-cutting findings

1. **Reopen-triggers that already fired (REACTIVATE candidates).** MI210 GPU installed 2026-07-02 flipped hardware gates that predate it: `gpu-drafter-mi200` (fired; Stages 1–2 ran + failed economics), `minddr` Phase-2 (DGX abandoned → MI210 training-viability smoke now possible), `sarathi-serve` (multi-tenant trigger via active batched-decode E1/E2). These read as "parked" but their premise changed.

2. **The Qwen3.6-27B fragmentation error (exemplar).** `qwen36-27b-cpu-feasibility` is correctly parked *on CPU* (BW-roofline ~7.5–9 t/s, GDN spec-dec wall) — but the **same model was characterized extensively on the MI210 GPU** in the operator-launched 2026-07-03 speed campaign (`progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md`): plain Q8 29.5 → **40.4 t/s (+37%)** via embedded-NEXTN MTP + MMVQ→MMQ fix (`de447119f`), EAGLE-3 tested (no-go), GDN-MFMA profiled+killed. That banked "dense-Q8 +37%" win in `v7-promotion.md` is this model. **The parked CPU handoff never cross-links the GPU campaign** — so reading it alone wrongly implies the model is dead. A single research thread's work is split across a parked handoff and a thriving one that it doesn't reference. This is why the raw open count both over-counts backlog *and* mis-reads liveness.

3. **Frozen-behind-an-unfired-gate is the dominant stale pattern.** The largest stale masses (decision-aware-routing 23, learned-routing-controller 15, GEMV 36) are all work correctly halted by an explicit gate whose reopen trigger has been tested and NOT fired (DAR-1 replay 0.00%; GEMV kernel-ceiling proven barrier-bound). Boxes are honestly unchecked; they simply aren't live.

4. **Board signal reconciliation.** The live board dims only 5 cards (high-precision). This audit's wider net (22) surfaces LANDED/SUPERSEDED/frozen cases the conservative heuristic intentionally skips (e.g. `internal-kb-rag` LANDED, `decision-aware-routing` frozen). Fix path: encode audited verdicts as explicit `**Lifecycle**:` fields (authoritative over the heuristic) — including a `Lifecycle: live` override on `llama-cpp-dsa-contribution`, which the heuristic over-flags.

5. **A five-handoff duplicate cluster on the stack-update pipeline.** `model-stack-single-source-update-pipeline` (N11a), `standardized-stack-update-pipeline-finalization` (N11), `model-stack-update-pipeline-audit`, `model-stack-change-standardization-audit`, and `stack-change-governance-pipeline` all describe the **same landed pipeline**. `model-stack-update-pipeline-audit` self-demotes to "historical-detail support"; the routing index already merges N11 + governance into one row. **Authoritative pair**: `model-stack-single-source-update-pipeline` (consumer-SSoT) + `stack-change-governance-pipeline` (command/gates). **Redundant**: `standardized-stack-update-pipeline-finalization` + the two audit docs. Core work is landed; every remaining open box across the cluster is opportunistic-on-new-finding or evergreen discipline — none actionable now. Consolidating this cluster is the single highest-leverage backlog cleanup. **2026-07-18 execution correction (on verification):** the "retire 3" framing was too coarse — only `standardized-stack-update-pipeline-finalization` is cleanly retirable (its sole live box, W4 swap-CI, is co-tracked in both authoritative docs); `model-stack-update-pipeline-audit` has 2 **orphan-live** boxes (`ctx_model_max`, tap/policy-hint) tracked in *neither* authoritative doc, so it stays LIVE until they migrate; `model-stack-change-standardization-audit` is a repeatable **runbook**, not done-work. Soft-consolidation (Lifecycle + pointer notes) applied 2026-07-18; hard-archive + orphan-box migration + index repointing is operator-gated.

#### Recommendations (follow-up tasks — no checkbox flips on the audited handoffs)

- [x] Add `**Lifecycle**: live` to `llama-cpp-dsa-contribution` (board over-flags it superseded) ✅ 2026-07-18
- [x] Cross-link the MI210 GPU speed campaign into `qwen36-27b-cpu-feasibility` (parked-on-CPU ≠ dead model) ✅ 2026-07-18
- [x] Surface the fired reopen-triggers (gpu-drafter MI210-gate, minddr DGX→MI210, sarathi batched-decode E1/E2) with dated notes + reactivate `- [ ]` tasks in each handoff ✅ 2026-07-18
- [x] Re-anchor GEMV to its 2 live graph-fusion tasks; move the deprioritized SIMD Phase 0–5 plan to a closed appendix ✅ 2026-08-11 (`mainC`, root `9ed95b4d`) — the two live boxes (fuse expert gate+up; fuse the attn QKV cluster, both frontdoor Q8_0, both cutting barrier COUNT) are now the file's whole live surface, and the Phased Work Plan sits under a CLOSED APPENDIX declaration. Measured effect: the handoff presents **2** rows on the generated bench instead of **28**. **The 26 stale rows are still NOT closed and must not be** — the certification coupling is recorded on the GEMV handoff, and closing them ahead of the re-anchor would destroy the evidence separating the shelved plan from the live lever. Placing the banner also exposed a real tool blind spot: a `##` banner did not reach boxes under its own `###` children, so a phased plan could not be declared at all; fixed in the same commit with tests.
  - **VERIFIED 2026-07-29 (`auditor`), handed to the CPU-lane owner — NOT executed here**, because this
    section is headed *"no checkbox flips on the audited handoffs"* and the move would effectively close
    26 boxes. **The recommendation is correct and the target handoff says so itself:** line 5 reads
    *"Priority: ~~MEDIUM~~ DEPRIORITIZED for the SIMD ukernel; but the barrier/op-count sub-lever is
    RE-ELEVATED"*, and its verdict section adds *"Not pursued. ROI doesn't beat the production-side
    alternative"* and *"CPU2 closes here for Q8 specifically — the 4.4 t/s ceiling is genuinely
    architecture-bound"*, with two graph-rewrite probes recorded as disproved.
    **Measured:** 36 open boxes in that file — 10 are the Pickup Checklist (a reusable template, guarded
    separately today), and **26 are Phases 0–5 of the very plan the header calls deprioritized.**
    The two live anchors to keep: the barrier/op-count sub-lever, and the qwen35 DeltaNet fusable
    cluster `wqkv + wqkv_gate + ssm_beta + ssm_alpha` named in the verdict.
    **This is the cleanest `stale by supersession` case found so far** — not *already done* but
    *overtaken by the handoff's own recorded verdict* — and it is invisible to every mechanical
    detector tried today, because each box's own text reads fine and only the header and verdict
    elsewhere in the file contradict it. 26 boxes in one file is why the ~1/3-live estimate looks
    plausible.
- **[declined: ws58 2026-11-03 content-review: done by the 2026-11 backlog refactor]** Close/relocate the LANDED/SUPERSEDED handoffs (v6-consolidation → completed; kb-rag K1–K7 certified; x-mas → telemetry-watch)
- **[declined: ws58 2026-11-03 content-review: folded by the 2026-11 backlog refactor]** Split `learned-routing-controller` and `decision-aware-routing`: live rollout/backlog vs frozen-behind-unfired-gate expansion
- [x] Stack-cluster soft-consolidation (corrected on verification — NOT a clean "retire 3"): superseded `standardized-stack-update-pipeline-finalization` (W4 co-tracked); kept `model-stack-update-pipeline-audit` LIVE (2 orphan boxes); flagged `model-stack-change-standardization-audit` as a repeatable runbook ✅ 2026-07-18
- **[declined: ws58 2026-11-03 content-review: done by the 2026-11 backlog refactor]** Stack-cluster HARD-archive (operator-gated): git-mv the superseded + runbook docs to `completed/`, migrate the audit's 2 orphan-live boxes (`ctx_model_max`, tap/policy-hint) into the SSoT, repoint the ~10 inbound index links
  - 2026-11-02 operator decision: Approve the archive (decisions-batch2-4-20261102.json)
- [x] Surface the SLIDERS reopen precondition (KB-RAG K7 certified 2026-06-13) as a fired-but-needs-operator-decision note ✅ 2026-07-18
- [x] **Publish the current dispatch-inventory baseline ✅ 2026-07-29**: [`BACKLOG-DISPATCH-QUEUE.md`](../../coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md) reports **1,103 unchecked active-handoff tasks at sweep start** and **~232 none-lane, unblocked tasks dispatchable now**. This supersedes the historical `≈544` heuristic; it is an inventory count, not an exact audited live/stale partition. The exact partition remains open below.
- **[declined: ws58 2026-11-03 content-review: superseded by the backlog refactor and this content review]** **NEW 2026-07-29 — Extend the stale-open audit to an exact current live/stale partition, then present a derived dashboard field with audit date and source.** The original 22 audited handoffs now contain 208 open tasks (vs 173 at audit time); current lifecycle parsing identifies only 58 high-precision parked/superseded rows, so neither source can certify the remaining 949-or-fewer tasks as live.
  *STATE 2026-08-12 (`auditor`): the read-certification tranches ARE this row's engine — T4–T7
  (2026-08-11/12, artifacts `read-certification-tranche{4..7}-*.md`, records at L269 below) have
  certified 389 rows ≈41% of the ~918-row backlog with per-row LIVE/DEAD/GATED/REWRITE verdicts
  and adjudicated DEAD lists; blended dead-rate 25%, and dead-rate tracks time-since-last-audit,
  not file size. The dashboard-field half remains genuinely open (needs the partition to finish).
  Remaining tranches are the row's live work; the "58 high-precision rows" framing is superseded.*
- **[declined: ws58 2026-11-03 content-review: superseded by the backlog refactor (176 -> 29) and this content review]** Extend the audit to the ~105 un-flagged open handoffs to convert "≤544" into an exact live count
  - **PARTIAL 2026-07-29 (`auditor`) — the exactly-certifiable part is done, and it is small; automated
    exact stale-detection is EXHAUSTED.** Parsed every `- [ ]` box in `handoffs/active/`: **992 raw
    open boxes across 150 files** (the queue's 1082-1103 figures from this morning have burned down
    during the day). Exact, checkable reductions:
    | bucket | n | basis |
    |---|---|---|
    | **NOT A TASK** — reusable checklist or standing constraint | **36** | neither live nor stale; must leave the denominator entirely |
    | STALE — box duplicates a `- [x]` in the SAME file | 0 | exact normalised text match |
    | STALE — box duplicates a `- [x]` in ANOTHER file | 0 | exact normalised text match |
    | STALE — handoff header declares complete/closed/superseded | 1 | `autopilot-authority-autoenable-proposal.md:100` |
    | **UNCERTIFIED-LIVE** | **955** | no automatic signal can certify these |
  - **The load-bearing negative result:** stale rows do NOT restate their completed twin verbatim, so
    exact-text duplicate detection yields **zero**. That independently corroborates this task's own
    premise ("lifecycle parsing identifies only 58 high-precision parked/superseded rows") and means
    the residual 955 cannot be certified by any cheap automatic rule — certification requires READING
    each box against its handoff's prose. Recorded so nobody re-attempts the automated route.
  - **The category this task did not anticipate:** 36 boxes are neither live nor stale because they
    are not tasks at all — reusable checklists (`Update Checklist For Any …`, `Pickup Checklist`,
    `Reopen Checklist`, `Rules For New Tests`) and standing constraints under task-shaped headings.
    They were being served as dispatchable work and two were actually flipped. Excluding them is an
    exact, defensible reduction to the denominator, not an estimate.
  - **Derived dashboard field, ready to wire:** `backlog_live_uncertified = 955`,
    `backlog_not_a_task = 36`, `audit_date = 2026-07-29`, `audit_source = auditor / exact parse of
    handoffs/active`, `certification_method = none available automatically — requires read-through`.
    Reproduce with `scripts/coordination/backlog_row_check.py` per row.
  - **READ-CERTIFIED 2026-07-29 (mainB, 2 rows):**
    `agent-collab-rnd-harness.md` has two optional spikes, neither a current
    live task: the orx/OpenCode vehicle is explicitly gated on operator
    interest, and the OpenHyra adapter additionally requires an external
    container plus an unsandboxed opt-in. Both remain valid future work but
    are **gated**, not dispatchable (and E5 separately prohibits their local
    llama workload). `backlog_live_uncertified = 953` for this dated
    read-through slice; `backlog_not_a_task = 36` is unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 1 row):**
    `autopilot-authority-autoenable-proposal.md` is explicitly superseded by
    consolidated apply-time ratification. Its sole box is an archive
    disposition that waits for operator acknowledgement; it is
    **operator-gated**, not live engineering work. `backlog_live_uncertified
    = 952` for this dated read-through slice; `backlog_not_a_task = 36` is
    unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 2 rows):**
    `autopilot-control-plane-integration.md` remains actively owned/dirty;
    its AP-3 restart-scoped spec-decode/KV work requires quality-cleared
    composed configurations and a sequential reload. The residual source-proof
    subtask is part of that same restart policy. Both are **campaign-gated**
    (and prohibited during E5), not dispatchable. `backlog_live_uncertified =
    950` for this dated read-through slice; `backlog_not_a_task = 36` is
    unchanged. No owner handoff was edited.
  - **READ-CERTIFIED 2026-07-29 (mainB, 8 rows):**
    `autopilot-dashboard-fidelity-audit-2026-07-22.md` has eight clearly
    non-dispatchable boxes: two server/process-owner fixes, an E8 campaign
    counter reconciliation, a human-amendment era-row commit, the
    inference-owned cold-guard, two deferred stretch panels, and the deferred
    grouped provenance/attribution surfaces. These are **owned, E8/E5-gated,
    human-only, or deferred**, not current independent work. The separate hub
    percentage-presentation box remains unclassified for its owner.
    `backlog_live_uncertified = 942` for this dated read-through slice;
    `backlog_not_a_task = 36` is unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 7 rows):**
    `autopilot-sequential-allocation.md` has seven non-dispatchable decision
    or campaign gates: the SEQ-A/SEQ-B policy changes and their explicit
    operator decisions are measurement-trust-boundary work; SEQ-3 requires
    either that ruling or an E8 clean re-run, which itself waits for the
    fail-closed E8 rebaseline. These are **human-only or E8-gated**, not
    current independent work. The deterministic SEQ-4 re-examination and two
    summary-pointer boxes remain unclassified. `backlog_live_uncertified =
    935` for this dated read-through slice; `backlog_not_a_task = 36` is
    unchanged.
    *(Note 2026-09-16: the E8 gate is superseded by operator ruling [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json), root `1ee8bd7c`. The ruling retires the E8 chain and re-anchors the gate to the current eras; the gate binds only at promotion.)*
  - **READ-CERTIFIED 2026-07-29 (mainB, 4 rows):**
    `batched-edit-parallel-apply.md` has no current independent dispatch:
    BEP-2 is inference-gated, BEP-3 is conditional on its result, BEP-5 is a
    safety-gated general-autonomy design, and the residual LM-repair lane is
    explicitly inference-gated. `backlog_live_uncertified = 931` for this
    dated read-through slice; `backlog_not_a_task = 36` is unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 2 rows):**
    `bep-dcp-falsification-harness.md` is actively dirty under another owner.
    Its two remaining rows are a host-quiet deploy-attestation-plus-inference
    gate and optional J8 provenance. Both are **inference-gated**, not current
    E5-safe dispatch. `backlog_live_uncertified = 929` for this dated
    read-through slice; `backlog_not_a_task = 36` is unchanged. No owner
    handoff was edited.
  - **READ-CERTIFIED 2026-07-29 (mainB, 2 rows):**
    `capability-registry-and-promotion.md` leaves W3/W4 behind the
    evidence-plane ledger, shadow attestation, and a monthly promotion pass.
    Both are **evidence-gated**, not current independent work.
    `backlog_live_uncertified = 927` for this dated read-through slice;
    `backlog_not_a_task = 36` is unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 1 row):**
    `colbert-reranker-web-research.md` is dirty under another owner, but its
    primary S5 request-path reranker row is **prose-closed** by the
    representative 55-synthesized-page `<10%` irrelevant-page NO-GO. It is a
    stale checkbox, not live work; the owner file was intentionally untouched.
    `backlog_live_uncertified = 926` for this dated read-through slice;
    `backlog_not_a_task = 36` is unchanged.
  - **TRANCHE 1 READ-CERTIFIED 2026-07-29 (`auditor`) — 19 boxes, the single-open-box handoffs.**
    Read each box with its section, `Status:` header and following context. Result:
    | verdict | n | meaning |
    |---|---|---|
    | **LIVE** | 9 | genuine outstanding work (PC-4, W8b, W3 fine-tunes, `real_suite_v1`, MoE B-sweep, RD-12, TM-8, W4 consumer migration, post-soak cleanup) |
    | **PARKED — explicit reopen trigger, not fired** | 6 | `mi210-mfma:47` *reopen only if a new compute-bound path appears*; `numa-prefill-decode:76` *reopen on multi-tenant shift*; `yarn-context-extension:105` *reactivate when …*; `security-review-skill:60` *intentionally deferred*; `model-capability-descriptors:40` *GATED tail, IF ever opened*; `gpu-cot-scaffold-sidecar:21` *only if a deployment decision is proposed* |
    | **OPERATOR / HUMAN-OWNED** | 2 | both are *"archive after operator acknowledgement"* rows |
    | **STALE BY OBSOLESCENCE** | 1 | `mi210-speed-campaign-summary:70` — *"run KernelBench over current v6 production kernel"*; v6 is two generations stale (v8 is production), so the task as written names a target that no longer exists |
    | **STANDING ACTIVITY** | 1 | `x-mas-text-routing:51` — *"monitor post-enable live telemetry"*; ongoing, not completable |
    **Two categories the audit did not enumerate, both found here:** *stale by obsolescence* (the task
    still stands but names a superseded target — it is neither done nor doable as written) and
    *parked with a named reopen trigger* (dormant by design; counting it as backlog overstates the
    live queue).
    **SAMPLING BIAS, stated because it would otherwise mislead:** 10 of 19 in this tranche are not
    live work, but single-open-box handoffs are **structurally biased toward residue** — a handoff
    with exactly one box left is usually a finished one carrying a parked tail. **Do NOT extrapolate
    ~50% to the remaining 936.** The rate must be re-measured on multi-box handoffs before it means
    anything fleet-wide.
  - **TRANCHE 2 READ-CERTIFIED 2026-07-29 (`auditor`) — 45 boxes, STRATIFIED multi-box sample**
    (one median-size file from each of the 2-3 / 4-8 / 9-20 / 21+ buckets:
    `objective-task-rate-goodput` 2, `integration-test-coverage` 5, `user-facing-harness-index` 11,
    `gpu-serving-tie-in-program` 27). Per-box verdicts recorded in the commit.
    | verdict | n | % |
    |---|---|---|
    | **LIVE NOW** | 13 | 29% |
    | PHASE — real work, later phase of an active program | 7 | 16% |
    | **DUP-INDEX — already counted in its owning handoff** | 6 | 13% |
    | GATED-DEP — blocked on a named dependency | 6 | 13% |
    | NOT-A-TASK — standing policy | 5 | 11% |
    | GATED-OP — waiting on an operator | 5 | 11% |
    | GATED / PARKED | 3 | 7% |
    **MY PREDICTED BIAS WAS WRONG, IN DIRECTION.** I said single-box handoffs were biased toward
    residue and warned against extrapolating tranche 1's low live-rate. The stratified multi-box
    sample came back **lower still — 29% live vs tranche 1's 47%.** The reason is visible once read:
    large handoffs are *program plans*, not task lists. `gpu-serving-tie-in-program` alone carries 27
    boxes of which most are later-phase or operator-gated. So the caution was right but the arrow
    pointed the wrong way, and I am recording that rather than quietly dropping the earlier warning.
    **THIRD NEW CATEGORY: DUP-INDEX.** 6 of 45 (13%) are index-pointer rows duplicating the owning
    handoff's row (`user-facing-harness-index:99/101/107/108/109/111`). The collision map names several as
    C2 duplicates; this confirms they **inflate the open-box total**, since both copies count.
    **Combined: 64 of 982 boxes certified (6.5%), 22 LIVE (34%).** Both strata independently land
    near one-third live, which is the first evidence that the ~1/3 figure may be robust — but 6.5%
    coverage is not a basis for a fleet number, and it should not be quoted as one yet.
  - **TRANCHE 3 — the "cheap exact reduction" I recommended DOES NOT EXIST. Third negative of the
    same shape.** ✅ measured 2026-07-29 (`auditor`). I proposed de-duplicating index-pointer rows as
    a mechanical reduction needing no reading. Measured across all 8 index files (65 open boxes):
    * **exact-text cross-file duplicates: 0.** Index rows *summarise* their owner's row in different
      words, so the same text-matching that failed for staleness fails for duplication.
    * **12 rows explicitly name an owner file.** Checking each against its owner: only the ID-level
      test ("every id named in the index row is `[x]` in the owner, none still open") is suggestive,
      and it yields **2 candidates**, of which **1 is confirmed stale by reading**:
      `inference-research-index.md:120` tracks *"B1-B5 in a quiet window"* while
      `iqk-iquant-enablement.md` has B1–B5 all `- [x]` (2026-07-25/26) and Status **"PROMOTED AND
      FROZEN IN v8"**. **That is a genuine already-done-but-open row — the category the audit wanted
      and could not find.**
    * **The signal I thought was strongest is WRONG.** "Index row names an owner with zero open
      boxes" looked decisive; `research-evaluation-index.md:84` disproves it — its owner
      `frontier-f1-real-task-corpus.md` has 0 open boxes but Status **IN PROGRESS**, because that
      handoff tracks in prose. Owner-has-no-boxes means *"the owner does not use checkboxes"* at
      least as often as it means *"the work is done"*. Recorded because acting on it would have
      wrongly closed live work.
    **CONCLUSION FOR THE AUDIT: every cheap mechanical route has now been tried and failed** — exact
    text staleness (0), cross-file duplication (0), index-pointer de-duplication (~1 confirmed of
    65). Reading is the only route, and its rate is now measured. Stop looking for a shortcut.
  - **[declined: ws58 2026-11-03 content-review: superseded by this content review (every open box read and judged)]** **REMAINS OPEN:** read-certify the remaining ~918. That is the only route left and it is a bounded but
    large job; it should be split across mains by handoff, not attempted in one session.
    - [x] **Tranche 7 — the tail, complete: 13 of 13 rows in 8 small files ✅ 2026-08-12 (`auditor`)**
      **6 LIVE / 6 GATED / 1 REWRITE / 0 DEAD** — the tail is clean; wp12 ran the recurrence check on
      itself correctly in-file. Elevated: HS-OD-1 is a LIVE unfixed API defect (response_format
      silently dropped, zero src/api hits, spot-verified). Evidence:
      `artifacts/audit/read-certification-tranche7-20260812.md`. **Cumulative T4-T7: 389 rows, ~42%
      of backlog, 24% blended dead. Non-live-owner certification COMPLETE** — the remaining ~918-row
      program continues only via live-owner files (policy-skipped) or the post-merge regenerated queue.
    - [x] **Tranche 6 — 8 smaller bench-feeding handoffs, complete: 48 of 48 rows certified ✅ 2026-08-12 (`auditor`, overnight)**
      (vidya 12, UTM 10, tri-role 7, within-role-placement 6, triattention 4, tool-output-compression 4,
      attention-matching 4, laguna-s21 1). **20 LIVE / 8 DEAD / 19 GATED / 1 REWRITE** after main-thread
      adjudication AMENDED one certifier verdict (WP-8 zero-callers claim refuted: eval_tower.py:1694 calls
      the helper). Evidence: `artifacts/audit/read-certification-tranche6-20260812.md`. HEADLINE: the
      Attention-Matching Track-2 native integration is claimed-deployed-but-DROPPED (Gate-3-PASSED prose vs
      not-ancestor commits + explicit v6 removal comment) with the re-port-or-decline decision owned by
      NOBODY; SC12 write-side hook window was MISSED at the v9 freeze (receipt carries zero claim wiring).
      Cumulative T4-T6: 376 rows, ~41% of backlog, blended 25% dead.
    - [x] **Tranche 5 — the next 4 bench-feeding handoffs, complete: 97 of 97 rows certified ✅ 2026-08-12 (`auditor`, overnight)**
      (`multimodal-pipeline` 22, `canonical-judge-suite-revamp` 24, `eval-tower-verification` 27,
      `architect-model-selection-bench` 24). **50 LIVE (52%) / 9 DEAD (9%) / 36 GATED / 2 REWRITE** — full
      evidence in `artifacts/audit/read-certification-tranche5-20260812.md`. The dead-rate collapse vs T4
      (33%→9%) proves staleness tracks TIME-SINCE-LAST-AUDIT, not file size. Cumulative T4+T5: 328 rows,
      26% dead; backlog ~36% certified. Seven priority flags routed (S-15 truncation on the LIVE vision
      model; execution-gate contradiction; AXA-1 GPU-residency drift; L166/L206 duplicate + index
      first-row blindness; row_check false-positive class; EV-8 reject-path template; kvquant verdict gap
      — auditor takes the last).
    - [x] **Tranche 4 — the 4 highest-count bench-feeding handoffs, complete: 231 of 231 rows certified ✅ 2026-08-12 (`auditor`, overnight)**
      (`decision-aware-routing` 34, `autopilot-continuous-optimization` 62, `rocm-verify-profile-backend` 49,
      `numa-topology-cutover-resume-20260730` 86). **90 LIVE (39%) / 76 DEAD (33%) / 51 GATED / 10 REWRITE /
      3 UNRESOLVED / 1 standing-constraint** — full evidence in
      `artifacts/audit/read-certification-tranche4-20260812.md`; owners flip their own DEAD rows from that
      record. Live-rate spread 24-66% per file (T1-T3 priors re-confirmed: reading, not sampling). Two
      cross-cutting finds outrank the rows: the AutoKernel effect gate cannot structurally pass a CPU-decode
      win (threshold 10 vs martingale ceiling 5.5687 - routed URGENT to inference), and a new defect class:
      rows resolved by LATER checked entries in the SAME file, never reconciled back.
    - [x] **Tranche 3 — the 6 orphan handoffs, complete: 18 of 18 boxes certified, 0 DEAD ✅ 2026-07-29 (`auditor`)**
      (`agent-collab-rnd-harness`, `autopilot-authority-autoenable-proposal`, `core-v2-design-note-2026-07-23`,
      `qwen-mtp-llamacpp-port`, `re4-protocol-redesign`, `stale-open-audit-2026-07-18`).
      **The result falsifies the premise I picked them on.** I chose the orphans expecting a high stale
      rate — linked from no index, so nothing finds them by navigation and nothing has been pruning them.
      Not one row is dead. Every one is live and *gated*: 4 on an operator decision, 6 on an inference
      window, 2 on a predecessor row, the rest on a named owner. **Orphan status is not staleness**; it is
      an indexing defect with a different fix — link these from an index rather than audit them for rot.
      Prior tranches for comparison: T1 47% live (n=19), T2 29% (n=45), T3 **100%** (n=18).
    - [x] **`re4-protocol-redesign.md:151` sharpened rather than closed ✅ 2026-07-29** — the row asks to verify
      the RE-4 runner has (a) incremental per-question persistence and (b) confidence capture with
      `confidence_is_real` provenance. Verified against
      `epyc-inference-research/scripts/benchmark/longcot_mini_stack_runner.py`: **(a) is already satisfied** —
      `_write_role_result` (:452) is called per question inside the loop at :560, writes atomically via
      tmp+replace, and :521 resumes from persisted rows. **(b) is genuinely unmet** — `confidence` appears
      nowhere in the file (the sole `conf` hit is `config_name` at :469; checked a second spelling before
      concluding absence). So the row stays open but is now scoped to (b) alone. Not patched here: RE-4 is
      the CPU lineage's, and that runner is measurement-instrument code.
  - 2026-11-02 operator decision: Close as superseded by the backlog-refactor manifest (decisions-batch2-4-20261102.json)

> All verdicts above are **observations** for backlog-hygiene decisions, not measurement-gating numbers. No production kernel, registry, or handoff checkbox was modified by this audit.

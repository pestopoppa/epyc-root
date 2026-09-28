# Thesis Experiment — does the orchestrator beat the strongest model alone?

**Status:** **PARKED 2026-09-28** (operator, in chat, session
https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ).
- **Why.** A2's escalation is driven by episodic-memory Q-values. The store holds 64,396 memories, the newest written
  2026-09-24, all learned while `architect_general` was the 27B, before the ARCHSWAP was applied on 2026-09-28. A2
  would therefore test an untrained router on a new stack, and a low G could not separate "routing does not help"
  from "routing has not learned this stack".
- **No routing-independent gap check (A0 vs A1).** The operator ruled it not worth running: public quality benchmarks
  already exist for these models and already answer whether a gap worth routing for exists.
- **The autopilot run that would train escalation on the swapped stack waits for the second MI210**, which the
  operator installs.
- **Reopen trigger:** an autopilot run has trained escalation on the swapped stack. Then TE-reopen (below): review the
  escalation design first, then TE-pilot and A2 under the frozen rule.
- **Everything stays in place:** the runner (research `2b59bebe`), the pilot pool, the pre-registration (decision rule
  frozen, TE-3a decisions recorded) and `v1_escalation` (production, opt-in per request).
- Before parking: the decision rule was PRE-REGISTERED (X = 0.75, Y = 0.50; OP-66, 2026-09-27), TE-0 to TE-3a were
  done, and the ARCHSWAP was signed (2026-09-28), merged and brought up by B1 (ARCHSWAP-1 to ARCHSWAP-3 below). No
  scored item has run.

**Priority:** parked. The 2026-09-27 narrowed plan ("point all work at the thesis experiment") no longer ranks work
(operator, 2026-09-28): until the second GPU is in, the working direction is infrastructure and design work with the
operator (see `CURRENT-CAMPAIGN.md`, 2026-09-28). The freeze list at the end still binds INFERENCE-bearing steps; the
design and documentation work of a frozen item may proceed.
**Created:** 2026-09-27, promoted from `repl-embedding-retrieval.md` REPL-EMB-B.1 (the quality-baseline seed).
**Owner index:** [user-facing-harness-index.md](user-facing-harness-index.md) (UFH-13).
**Depends on:** an autopilot run that trains escalation on the swapped stack (after the second MI210; TE-reopen). The
ARCHSWAP role-swap package (workspace-8d) was signed 2026-09-28 (receipt `RATIFY-ARCHSWAP-20260927`, OP-68 resolved)
and is applied; its remaining steps are ARCHSWAP-3b, ARCHSWAP-4 and ARCHSWAP-5 below. RI-21 (routing-intelligence.md,
RTG-30) is closed by the swap. TE-1 delivered the HS-4 P4 /v1 escalation subset this experiment needed from UFH-01.

## Start here

The project's bet is that a routed stack (a fast frontdoor that escalates to a strong consultant) is worth more than
the strongest single model behind an off-the-shelf harness. Our own prior art puts the burden of proof on
multi-agent (intake-1109#record: at equal token budget a single agent is at least as good). A 2026-09-27 audit found
that the session holding this bet ran no work toward measuring it. This handoff is that measurement.

Three arms, one frozen suite, one harness (OpenCode → orchestrator `/v1`), one window:

| Arm | What serves the answer | How it is pinned |
|---|---|---|
| **A0** | Qwen3.8-Flash-Next alone: the stack's public-benchmark leader, the operator's baseline 1 | `x_orchestrator_role: architect_general` (after the swap) in the OpenCode per-call config; no escalation |
| **A1** | frontdoor alone | no role key, escalation off |
| **A2** | frontdoor with escalation to the consultant = `architect_general` = Flash-Next | no role key, escalation on |

A1 and A2 differ **only** in the escalation switch. A0 and A2 reach the same Flash-Next server.

**Role swap (operator decision, 2026-09-27).** Flash-Next becomes `architect_general` and the 27B becomes
`architect_critic`, so the consultant is reachable through existing escalation. The swap is a separate `stack-change`
package. Until it is applied and serving is proved, Flash-Next is `architect_critic` on `:8074` and the 27B is
`architect_general` on `:8083` (MI210). **Applied 2026-09-28** (ARCHSWAP-1 to ARCHSWAP-3 below): Flash-Next now
serves `architect_general` on `:8074` and the 27B serves `architect_critic` on `:8083`.
**Scope of the swap (operator, 2026-09-27): ONLY `architect_general` moves to Flash-Next.** `coder_escalation` and
`ingest_long_context` stay on the 27B. Frontdoor's existing escalation hop is `CODER_ESCALATION` (TE-2), so after the
swap that hop lands on the 27B: A2's escalation must target `architect_general` explicitly (TE-1), and TE-2 proves it.

## Pre-registration (decision rule frozen 2026-09-27; the rest freezes at TE-3)

### Suite (frozen)

- **Items:** the manifest baseline 1 is already scored on:
  `epyc-inference-research/data/kernel-v8-candidate/quality-gate/run-20260725T204443Z-fullcontract-both-mode/questions.json`,
  sha256 `1532906b4a754673937027e73e2023d8eee7ed5d08f084c207a60ac81460adb1`. It holds MMLU-Pro 200 and GPQA 195
  items, all multiple choice. The file has no sha sidecar; TE-3 writes one.
- **Why this subset:** it is the only item set with a Flash-Next serving-class score: MMLU-Pro 151/200 (0.755) and
  GPQA 127/195 (0.6513), 0 truncated at cap 16384, live `:8074`, 2026-09-23
  (`epyc-inference-research/artifacts/architect-bench-cpu-20260923/runs/{mmlu_pro,gpqa}/flashnext_ud_iq4xs_mtp_cap16384/`).
  It is also the item set DAR-LAT-3a named. Frontdoor has **never** been scored on it.
- **Scorer:** `extract_letter_answer` (`epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py:363-369`),
  the same for every arm. Record its sha256 at freeze.
- **Generation:** temperature 0, seed 42, `enable_thinking=false` on Qwen3.6+ models, `max_tokens` 16384 on every arm.
  Flash-Next converged at 16384 (cap 64 truncated 46/200). A shorter cap would measure truncation, not quality.
- **Plumbing smoke:** 10 items from the same adapters with seed 7, deduplicated against the manifest, run once before
  the scored run. They are excluded from every score and never re-run to tune anything.

### Metrics

1. **Quality:** accuracy per suite and pooled. The quantum is `1/n_suite`, per MEASUREMENT.md:136 (0.005 on MMLU-Pro,
   0.0051 on GPQA). Pin this definition in the manifest: quality-eval.md:14 also uses a 3/n quantum.
2. **Consultant device-seconds:** Σ (prompt_eval_ms + generation_ms) / 1000 over every call served by the consultant
   (Flash-Next) server, from the inference tap (orch `src/runtime/inference_tap.py:378-384`, `:423-470`). A0 counts
   every call. The consultant server is `-np 1` on one device set, so one busy second is one device-second. Frontdoor
   device-seconds and the total are reported beside it and do not enter the rule.
3. **Wall:** per item, from OpenCode run start to the final answer. Report the median, p90 and total per arm. Wall is
   reported, not gated. Flash-Next alone averaged about 8 s per item at concurrency 1 (1604 s / 200 on MMLU-Pro).

Also recorded per item in A2: the escalation fired or not, the escalation reason, and the role that served the final
answer. Also recorded per arm: failures and timeouts, which count as wrong (every item is in the denominator; no
retries), and truncation.

### Decision rule — PRE-REGISTERED 2026-09-27 (frozen)

**Registration:** X = 0.75, Y = 0.50 and the CI condition below, operator-approved in chat on 2026-09-27, session
https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ (master queue OP-66, now closed). The rule is **frozen**:
changing X, Y, the CI condition or the verdict classes later needs a **new registration** (a dated, operator-approved
amendment recorded here), and a verdict taken under an amended rule is flagged as such.

Define the gap-closure fraction **G = (Q_A2 − Q_A1) / (Q_A0 − Q_A1)** on pooled accuracy, and the consultant-cost
fraction **d = DS_A2 / DS_A0** in consultant device-seconds.

- **SUPPORTED:** G ≥ **X = 0.75** and d ≤ **Y = 0.50**, and the paired-bootstrap 95% lower bound of G is > d
  (by item, 10,000 resamples, suites stratified).
- **REFUTED (for this escalation design):** the 95% upper bound of G is < d, meaning A2 is no better than escalating
  a random fraction d of items. The same verdict follows if A2 is quality-inferior to A1 (Q_A2 − Q_A1 < −1 pooled
  quantum, paired).
- **NO GAP:** the paired 95% CI of Q_A0 − Q_A1 includes 0. Frontdoor alone then matches the strongest model on this
  suite, and the orchestrator's case can only be cost and latency. Report the result as such. A saturated suite can
  hide a real model gap, so say so in the verdict.
- **INCONCLUSIVE:** anything else. Write a BOUNDED-NULL-1 statement (MEASUREMENT.md:600-640) with the power bound.

**Why X = 0.75 and Y = 0.50.** The yardstick is random escalation. If A2 escalated a random fraction f of items and
Flash-Next then answered them, it would close about f of the gap for about f of A0's consultant time: G ≈ d. **Routing
adds value only where G exceeds d.** Two numbers follow from that:

- **Y = 0.50.** At d above one half, A2 is mostly running Flash-Next anyway, plus a frontdoor pass in front of it.
  The consultant is the scarce seat (`-np 1`), so a design that spends more than half of A0's consultant time has not
  shown a reason to exist.
- **X = 0.75.** At d = 0.50, G = 0.75 means routing does 1.5× better than random escalation. Anything less would not
  pay back the pipeline's complexity. X = 0.75 also leaves A2 within a quarter of the gap of the strongest model,
  which is a claim a user would notice.
- **The CI condition (lower bound of G > d).** It keeps a lucky point estimate from passing. Rough power check: with
  n = 395 and a gap near 0.25, the SE of G is about 0.1. A true G of 0.75 at d = 0.5 therefore clears only narrowly
  (lower bound ≈ 0.55), and a true G near d does not. The rule is powered for a clear win, not a marginal one. A
  smaller gap inflates the SE of G, and a gap under ~0.10 makes G uninformative, which is why NO GAP is its own
  verdict.
- **What the operator could choose differently.**
  - X = 0.9 with Y = 0.3: a "near parity at a third of the cost" bar, which is stricter and closer to the thesis as
    literally stated.
  - X = 0.5 with Y = 0.5: this reduces to "beats random", the weakest defensible bar.

**Protocol.** Grade the A/B with P-AB-1 (paired, N ≥ 100 per arm; quality-eval.md:35-41). Take CIs with PAIRED-CI-1
within one window only, and grade nulls with BOUNDED-NULL-1. P-SERVE-SEL-1 does not apply: it governs TTFT load
sweeps. All arms are serving class, on the live stack, in one window. They are never compared with bench-class numbers
(INSTRUMENT-CLASS-1).

### Pre-registration clarifications (TE-3a) — fixed before any suite item was run

Operator-approved in chat on 2026-09-27, session https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ. No suite
item, pilot item or smoke item had been run when these were fixed. They clarify the frozen rule above and do not
amend it; they enter the TE-3 freeze with it.

- **(a) Transport: `--transport v1`. This is a declared DEVIATION from the prose "via OpenCode"** (§ *Start here*,
  *Rigor*). The runner drives the orchestrator's `/v1` directly, with the pre-registered sampling fixed on every
  request (temperature 0, seed 42, `max_tokens` 16384; research `scripts/benchmark/thesis_ufh13/arms.py`
  `GENERATION`).
  - Why: OpenCode's epyc plugin forwards only `x_*` keys, so it cannot pin temperature or seed per request.
  - What does not change: `/v1` is the same endpoint OpenCode calls. The arms, the role pinning and the escalation
    switch are the same body keys.
  - Consequence for the metrics: wall (Metric 3) runs from request start to the final answer, not from an OpenCode
    run start, and OpenCode's system prompt is not in the request. It is absent from every arm alike, so the
    "OpenCode's system prompt is constant across arms" confound becomes "no harness system prompt in any arm".
- **(b) Verdict evaluation order, as implemented** in research `scripts/benchmark/thesis_ufh13/score.py` (`score()`,
  origin/main `2b59bebe`; 10,000 resamples, stratified by suite, bootstrap seed 20260927). The first match wins:
  1. **REFUTED** if A2 is quality-inferior to A1: `Q_A2 - Q_A1 < -quantum`, with `quantum = 1/n` over the pooled
     items (point estimates on the same items).
  2. **NO GAP** if `gap_ci[0] <= 0.0 <= gap_ci[1]`, where `gap_ci` is the paired-bootstrap 2.5th/97.5th percentile
     interval of `Q_A0 - Q_A1`: per resample, `(correct_A0 - correct_A1) / n` over the same resampled items.
     The endpoints count as including 0.
  3. **SUPPORTED** if `G >= X` and `d <= Y` and the G lower bound `> d`.
  4. **REFUTED** if the G upper bound `< d` (no better than random escalation).
  5. **INCONCLUSIVE** otherwise, with a BOUNDED-NULL-1 statement.

  The scorer also returns INCONCLUSIVE between steps 2 and 3 when d is unmeasured, meaning a consultant cost is
  missing on some A0 or A2 record. That is the rule's "anything else" class, not a new verdict. Bootstrap resamples
  with `Q_A0 == Q_A1` leave G undefined. They are dropped from G's interval and counted.
- **(c) Review revisions: WRONG review verdicts are revised by `worker_general`**, as `/chat` does it. A2's quality
  therefore includes the worker's rewrites. Why: the experiment measures the system as it serves, not a
  consultant-only variant. The runner records `review_verdicts` and `final_answer_role` per A2 item, so the
  contribution is visible in the report.
- **The pilot is not a pre-registration deviation.** TE-pilot draws only from a pool disjoint from the frozen 395:
  research `0a8fa57b` (`scripts/benchmark/thesis_ufh13/pilot_pool.py`, `data/ufh13-thesis/pilot_pool.json`), pool
  sha256 `0898013e86b365d89cf941205e19e3843d4d3cd21f869d4db917496f030aa3c5`, 453 items (MMLU-Pro 200, GPQA 253).
  The runner refuses a drifted pool and any frozen question. No pilot item enters any score.
- **ARCHSWAP acknowledgements.** The operator approved the role-swap package's acknowledgements A-1 to A-5 in the same
  chat, **with reviews staying on the 27B** (`architect_critic`), not moving to Flash-Next. The package is being
  amended to match and is **not yet signed**. Nothing here substitutes for its signature. Consequence for this
  experiment: review calls are served by the 27B, not the consultant, so they do not enter consultant
  device-seconds (Metric 2). TE-reload proves the reviewer role resolves to the 27B before any scored item.
  - Update 2026-09-27 evening: the amendment is done. Plan decomposition also stays on the 27B, through
    `DEFAULT_PLANNER_ROLE = architect_critic`. The lanes are orchestrator `e08ec06d`, root `6dbbd7a1` and research
    `61af24fa`, and `--validate-only` returns VALID.
  - It reconciles TE-1: `x_escalation=auto` sends the verdict to the reviewer (the 27B), while
    `x_escalation=architect_general` pins every consultant call to Flash-Next. A2 therefore uses `architect_general`.
  - The package is still **unsigned**. The operator gave chat consent, but the auto-mode safety classifier blocked the
    agent from running the ratify script under the operator's name. Signing is an operator terminal action (ARCHSWAP-1
    below).

### Rigor

- **Freeze before the first scored item.** `FROZEN-AT-LAUNCH.sha256` (precedent:
  `epyc-inference-research/data/ak-r2358-shim-serving-2026-09-08/`) covers:
  - the suite file, the scorer module, this pre-registration's text and the arm configs (the OpenCode `opencode.jsonc`
    per arm);
  - the orchestrator commit, registry digest and live `topology_hash`;
  - the OpenCode tag `v1.18.31` = `014614d3`;
  - the episodic-memory snapshot digest.

  Any change after the freeze is a **post-hoc amendment**. Log it, and flag the verdict with it.
- **Order.** Interleave the arms per item in randomized, seeded order, in blocks of 3. The host drifts ~3% over hours,
  so arms never run as separate sweeps.
- **Memory held fixed.** Episodic memory is read-only during the run: Q-updates and write-back are off. The arms must
  not learn from each other, and A2 must not learn from A0's answers. The snapshot digest is frozen.
- **Concurrency.** Concurrency 1 per arm. Do not hold an outer region-lock around API traffic: the orchestrator claims
  per call (OP-63), and the HS-4 P0.4 r1 failure was exactly this.
- **Window.** The window is bus-granted and AutoPilot is quiesced by its owner. Sample the other servers idle DURING
  each block, never after.
- **Honest reporting.** Report n, every exclusion, the post-hoc amendments, and the confounds:
  - A0 and A2 share one server, so the consultant's warm cache state differs by arm order. Randomization is the
    control.
  - OpenCode's system prompt is constant across arms.
  - The frontdoor's E-7 numbers (MMLU-Pro 37.5%, GPQA-diamond 55.0%, maxtok 900) were a different item set and cap.
    Do not use them to predict the gap.

### Riders (optional; run only if cheap, never part of the rule)

A rider runs only after A0 to A2 complete in the same window, only if the switch already exists as a flag (no new
code for a rider), and only if the window has its estimated time left.

- **M-12k (memory on/off)** (`episodic-memory-integrity.md`): arm A1m0 is A1 with episodic lookups off. It costs about
  one extra frontdoor pass over 395 items.
- **RI-17 (routing vs rules-only)** (`routing-intelligence.md`): arm A2r is A2 with rules-only routing. It costs about
  one more A2 pass. Run it only if a rules-only switch exists on `/v1`.

## Tasks

- [x] **TE-0 — operator confirms the decision rule: X, Y and the CI condition** (master queue OP-66). The draft above
  proposes X = 0.75 and Y = 0.50. Everything below except TE-3's freeze can proceed meanwhile.
  ✅ 2026-09-27 — operator-approved in chat as drafted (X = 0.75, Y = 0.50, lower bound of G > d), session
  https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ. The rule is PRE-REGISTERED and frozen (§ *Decision rule*);
  OP-66 closed and archived.
- [x] **TE-1 — `/v1` escalation parity for A2 (HS-4 P4 subset, epyc-orchestrator).** **Approved by the operator
  2026-09-27 (with OP-66); being built by another agent — this box ticks when it lands with its tests.** `/v1` never escalates in either
  tool mode (orch `src/api/routes/openai_compat.py:595-596`), and `x_max_escalation` is recorded but not enforced
  (`src/api/models/openai.py:160-166`).
  - Add a default-off flag that lets a `/v1` frontdoor turn escalate to `architect_general` through the existing
    escalation policy, with the escalation receipt (fired, reason, target role) in the tap.
  - Add tests for off (byte-identical to today, which is A1) and on (A2).
  - This is the one piece of new code the experiment needs. Coordinate with UFH-01 HS-4 P4, and do not fork it.
  ✅ 2026-09-27 — orchestrator `9959e8db` added the `v1_escalation` flag (default off) and the per-request
  `x_escalation` key (`auto | off | architect_general`), with escalation telemetry; `280059cc` made escalation opt-in,
  so a request without the key sees no behaviour change. Full `tests/unit` suite passed (15620 passed). Not yet
  serving: deployment is TE-reload.
- [x] **TE-2 — escalation-target check after the role swap (zero inference).** Frontdoor escalates to
  `CODER_ESCALATION` (orch `src/roles.py:468-499`), an alias on `architect_general`'s server, and the graph hard-wires
  Frontdoor → CoderEscalationNode → ArchitectNode (`src/graph/nodes.py:250`, `:595`, `:615`).
  - After the swap, prove with `orchestrator_route_explain` that A2's escalation lands on the Flash-Next server, and
    that no hop ends on a role missing from `_ROLE_TO_NODE`. RI-21 is that defect: fix it (a one-line map entry plus a
    test), do not file it. RI-21 stays open in `routing-intelligence.md` until the swap: the ARCHSWAP role swap resolves
    it (the escalation map and the graph both end at `architect_general`), and ARCHSWAP-5 ticks it after the swap.
  - This fails if escalation lands on the 27B.
  ✅ 2026-09-27 — a test proves an escalated call reaches the registry-resolved `architect_general` server. Research
  `2b59bebe` added the runner at `scripts/benchmark/thesis_ufh13/` (plan / pilot / run / score, per-question
  persistence, resume, a sha-checked suite, and a bootstrap scorer implementing G and d), with 23 unit tests.
- [x] **TE-3a — freeze decisions (operator).** TE-3 cannot freeze the manifest until these are chosen; the runner
  implements all options, so nothing else waits on them.
  - (a) Transport: `--transport v1` with fixed sampling (recommended), or OpenCode with unfixed sampling. OpenCode's
    plugin passes only `x_*` keys, so temperature and seed cannot be pinned through it.
  - (b) Verdict evaluation order, as implemented: A2 < A1 → REFUTED; then NO GAP; then SUPPORTED; then G upper
    bound < d → REFUTED; else INCONCLUSIVE. Confirm it, since the rule text does not fix the order.
  - (c) Review-gate revisions are written by `worker_general`, as `/chat` does it (recommended: keep, so A2 measures
    the orchestrator as it serves).
  ✅ 2026-09-27 — operator-approved in chat, session https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ:
  (a) `--transport v1`, a declared deviation from "via OpenCode"; (b) the order as implemented; (c) keep
  `worker_general` revisions. Recorded with the exact scorer conditions, the disjoint pilot pool and the ARCHSWAP
  A-1..A-5 approval (reviews stay on the 27B) in § *Pre-registration clarifications*.
- [ ] **TE-3 — build and freeze the manifest (zero inference).**
  - The driver: a per-item OpenCode headless run through `scripts/harness/hs4_p04_acceptance.py`'s pattern. Pass the
    prompt on stdin, not positionally (HS-4 P7). Use one config per arm and randomized interleaving.
  - The consultant device-seconds aggregator over the tap, with offline tests.
  - The sha sidecar for the suite, then `FROZEN-AT-LAUNCH.sha256`.
  - Freeze only after TE-0 and TE-3a. The runner (research `2b59bebe`, `scripts/benchmark/thesis_ufh13/`) is the
    driver; TE-3a (a) chose `--transport v1`, so it drives `/v1` directly and the OpenCode-driver bullet above is
    superseded. The manifest records the transport and the deviation.
- [ ] **TE-4 — belief-kernel write side before the first scored item** (`vidya-belief-substrate-program.md` VB-THESIS-1;
  source row in `scripts/vidya/adapters/README.md`). Write per-item rows with the arm, item id, suite, correct,
  escalation fields, consultant and frontdoor device-seconds and wall, plus the manifest digest. Project; do not grade.
  - Progress 2026-09-27: research `2b59bebe`'s `run_thesis.py score` writes the `belief_measurements.jsonl` sidecar
    (`ufh13-thesis-belief/v1`, attestation = `records.jsonl`). The read-side adapter is VB-THESIS-2.
- [x] **ARCHSWAP-1 — the operator signs the ARCHSWAP-20260927 package from a terminal.** Chat consent is on
  record, but the auto-mode safety classifier blocks an agent from running the ratify script under the operator's
  name (2026-09-27), so only the operator can do this. The package is amended and VALID. Command:
  `cd /mnt/raid0/llm/tmp/archswap-20260927/root/artifacts/operator/stack-change-archswap-20260927 && RATIFY_OPERATOR="pestopoppa" THINKING_OPTION=follow-model BRINGUP_OPTION=B1 ./ratify_archswap_20260927.sh --attest RATIFY-ARCHSWAP-20260927`.
  If a pinned path has moved on origin/main, the script refuses. The package is then re-pinned by its preparer, never
  signed as-is.
  ✅ 2026-09-28 — signed by the operator from a terminal (`signed_by: pestopoppa`, `signature_channel: terminal`,
  02:52:34Z); receipt `artifacts/operator/receipts/RATIFY-ARCHSWAP-20260927.json`, options O-2 `follow-model`, O-3
  `B1`. OP-68 resolved.
- [x] **ARCHSWAP-2 — merge the three swap lanes and the A-3 fix** (PACKAGE §7 steps 1-4; needs ARCHSWAP-1's
  receipt).
  - Fast-forward to main at the pinned commits: research `61af24fa`, orchestrator `e08ec06d` and root `6dbbd7a1`.
  - Merge **orchestrator `lane/orch-prewarm-lock-20260927` @ `9a4785e1` (the A-3 prewarm/scout region-claim fix)
    together with the orchestrator lane.** It is based on `e08ec06d`, it is pushed only as a lane backup, and it must
    be on orchestrator main before ARCHSWAP-3's reload, so the bypass is never live unfixed.
  - Then run the registry bootstrap and `update`, `relabel_state.py` (a dry run, then `--apply`), and
    `check_contention_matrix_fresh.py` (expect OK `5d772b2c`).
  - Rerun the orchestrator unit suite on the merged main. On the lane there was one known failure: a test that reads
    the unswapped master registry (15635 passed). It must clear once the swapped master is merged. If it does not,
    treat it as a defect before ARCHSWAP-3.
  - Note: the research lane also carries the INF-78 AutoKernel `run.py` help-text change to `orch:architect_critic`.
    INF-78 is workspace-76's, so no task is filed here. It lands with this merge.
  ✅ 2026-09-28 — the three lanes are merged: orchestrator (with the A-3 prewarm/scout region-claim fix `9a4785e1`),
  research `76cecec4` and root `ec7748aa`. Derived-file provenance commit: orchestrator `0cc516b4`. `relabel_state.py
  --apply` ran (operator-approved in chat); the backup is
  `epyc-orchestrator/logs/orchestrator_state.json.pre-archswap-20260928T041545Z`.
- [ ] **ARCHSWAP-3 — bring-up B1: one API-only reload, fused with TE-reload** (PACKAGE §7 steps 5-7).
  - Run `orchestrator_stack.py reload orchestrator` with `ORCHESTRATOR_V1_ESCALATION=1`. Do not stop autopilot.
  - Run `stack_change_pipeline.py check --numa-mode both`. Expect only the two slot_save_path lines.
  - Run the serving proofs:
    - P1: an escalation reaches `:8074`;
    - P2: `architect_critic` answers from `:8083`;
    - P3: `coder_escalation` and `ingest_long_context` answer from `:8083`;
    - P4: `url_snapshot` equals `evidence/urls-after-static.tsv`.
  - Prove the reviewer and planner resolve to the 27B.
  - **A-3 side effect.** Frontdoor scouts now hold the frontdoor claim for their whole stage (budget up to 240 s).
    During the first scout stage after the reload, sample the claim state and any `contention_denied` or 503 on
    concurrent frontdoor calls. Record either "no denials" or the denial rate.
  - Progress 2026-09-28 — done:
    - B1 API-only reload done. `v1_escalation` was then added to production (orch `6d024ced`, operator-approved) and
      the API was reloaded API-only a second time: PID 1100541, `ORCHESTRATOR_FEATURE_V1_ESCALATION=1` in its env.
    - `check`: only the two known `slot_save_path` drifts, and `declared_env_attestation: ok`.
    - P4: the URL snapshot is identical to the evidence (19/19).
    - The reviewer and planner resolve to `architect_critic` (the 27B). The runtime-facts state routes
      `architect_general` → `:8074`, and `architect_critic`, `coder_escalation` and `ingest_long_context` → `:8083`.
    - Open: P1-P3 and the A-3 scout-stage sample, split out as ARCHSWAP-3b. This box ticks when ARCHSWAP-3b does.
- [ ] **ARCHSWAP-3b — P1-P3 serving proofs** (split from ARCHSWAP-3 on 2026-09-28).
  - P1: an escalation reaches `:8074`. Script `/mnt/raid0/llm/tmp/archswap-20260927/serving_proof.sh`; run it in a
    CPU window.
  - P2 and P3: `architect_critic`, `coder_escalation` and `ingest_long_context` answer from `:8083`. Script
    `/mnt/raid0/llm/tmp/archswap-20260927/proof_8083.sh`; run it only on workspace-76's "go" at a DS41 critic pass.
  - The A-3 side-effect sample from ARCHSWAP-3 (frontdoor claim state and any `contention_denied`/503 during the first
    scout stage after the reload), unless it was already recorded.
- [ ] **ARCHSWAP-4 — B2: relaunch each model server under its new label** (PACKAGE §7 step 8), which clears the
  two slot_save_path drifts.
  - Relaunch `architect_critic` (`:8083`) **only between DS41 actor calls, coordinated with workspace-76 over the
    bus**: its planner uses `:8083` by port.
  - Relaunch `architect_general` (`:8074`) at a quiet boundary of its CPU users. Fuse it with any DAR-LAT-3h reload
    of the same process.
  - Done when `check` shows 0 drift.
  - 2026-09-28: the `:8083` relaunch waits on workspace-76's go; the `:8074` relaunch waits for a long idle gap.
- [ ] **ARCHSWAP-5 — after ARCHSWAP-3, apply the PACKAGE §9 prepared text** to the surfaces that still use the
  pre-swap labels:
  - `decision-aware-routing.md` (the DAR-LAT-3 lines, including the 3i recipe key);
  - `conversation-stack.md` CS-17;
  - `routing-intelligence.md` RI-21: tick it, because the escalation map and the graph both end at
    `architect_general` after the swap;
  - the memory `project_champion_promotion_and_architect_swap_plan`.
  - Progress 2026-09-28: RI-21 is ticked (root, this date). The DAR-LAT-3, CS-17 and memory texts are applied by their
    owners, per PACKAGE §9.
- [x] **TE-reload — deploy TE-1 by an API-only reload** onto orchestrator `280059cc` or later with
  `ORCHESTRATOR_V1_ESCALATION=1`, after the ARCHSWAP (role swap) is applied. **It is the same reload as ARCHSWAP-3's
  B1; run it once.** workspace-8d owns the swap. workspace-76 owns DS41, which binds the 27B by port and is
  unaffected by an API reload. Use `orchestrator_stack.py reload orchestrator`, never the whole stack. After the
  reload, prove the reviewer role resolves to the 27B (`architect_critic`), per the operator's 2026-09-27 ARCHSWAP
  approval (§ *Pre-registration clarifications*).
  ✅ 2026-09-28 — deployed with ARCHSWAP-3's reload: orchestrator main carries `280059cc` and `6d024ced` (the flag in
  production's feature wave, operator-approved). The API was reloaded API-only (PID 1100541, env
  `ORCHESTRATOR_FEATURE_V1_ESCALATION=1`). The reviewer and planner resolve to `architect_critic` (the 27B).
- [ ] **TE-pilot — measure the A2 escalation rate before the full window.** Run `pilot 20` on non-suite items. The
  main risk is that `/chat`'s triggers are conservative: the quality detector is gated by `generation_monitor`, and
  the review gate fires only at Q < 0.6. If A2 barely escalates, A2 ≈ A1 and the full window buys little; decide
  before spending it.
  - **PARKED 2026-09-28** with the experiment: it runs only after TE-reopen's design review.
- [ ] **TE-reopen — reopen the experiment once escalation is trained on the swapped stack** (operator, 2026-09-28).
  - Trigger: an autopilot run has trained escalation on the swapped stack (`architect_general` = Flash-Next). That run
    waits for the second MI210.
  - First, review the escalation design. Under the review gate, a WRONG verdict is rewritten by `worker_general`
    (TE-3a (c)), not answered by the consultant, which makes G ≥ 0.75 structurally hard. Consider a registered
    variant in which the consultant answers. The rule is frozen, so a variant is a new registration, never an edit.
  - Then run TE-pilot and A2 under the frozen rule (TE-3 freeze, TE-5, TE-6).
- [ ] **TE-5 — run (inference; coordinated window; the main session runs it).**
  - Needs the role swap applied and serving proved, TE-1 deployed (TE-reload), TE-pilot's escalation rate read, and
    TE-2, TE-3 and TE-4 done.
  - Run the plumbing smoke, then A0/A1/A2 interleaved, then the riders if cheap.
  - Estimate about 2 to 2.5 h: Flash-Next alone ≈ 55 min for 395 items. Frontdoor passes are shorter, and A2 is
    frontdoor plus the escalated items.
- [ ] **TE-6 — verdict.** Apply the frozen rule and record SUPPORTED / REFUTED / NO GAP / INCONCLUSIVE, with n, CIs,
  amendments and confounds. Route the result to the operator. The verdict is the unfreeze trigger for the frozen list
  below.

## Frozen behind this experiment (operator, narrowed plan, 2026-09-27)

These boxes carry a `❄ FROZEN 2026-09-27` marker in their own handoffs. Each stays open, because frozen is not done.

**Scope since the park (operator, 2026-09-28):** the freeze binds only the INFERENCE-bearing steps of these items.
Their design and documentation work may proceed as part of the design agenda (`CURRENT-CAMPAIGN.md`, 2026-09-28).

- HS-19b, HS-19c and HS-19d P1–P6 (`harness-selection-and-integration.md`). HS-19d.0, the design, stays done. The
  A0/A1/A2 arms of HS-19d.P5 are this experiment.
- TD-28, typed advisors (`typed-decision-plane.md`), and its write side VB-TD-ADVICE. These wait until v11 native
  scoring exists **and** this experiment has a verdict.
- REPL-EMB-0.3 (GPU embedder) and REPL-EMB-1.4 (the saturation-guard B+D policy), in `repl-embedding-retrieval.md`.
  The UFH-12 A1 duty sweep is cancelled. These wait on the UFH-12 retrieval eval, not on this experiment.
- DAR-LAT-3i now, and DAR-LAT generally once DAR-LAT-3h's G1 is recorded (`decision-aware-routing.md`), with
  VB-SEL-LOADAB.
- LRC-1 and LRC-2 (`learned-routing-controller.md`).
- OD-A F7 and F6, the KTransformers port (`fable5-window2-findings-02-heterogeneous-gpu.md`).

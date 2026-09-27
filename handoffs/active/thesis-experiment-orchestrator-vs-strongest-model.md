# Thesis Experiment — does the orchestrator beat the strongest model alone?

**Status:** active. The **decision rule is PRE-REGISTERED** (X = 0.75, Y = 0.50; operator-approved 2026-09-27, OP-66
closed). The rest of the pre-registration (suite, scorer, arm configs) freezes at TE-3. TE-1 is approved and in build.
Nothing has run.
**Priority:** **TOP** (operator, narrowed plan, 2026-09-27). Work that does not move this experiment is frozen or waits
behind it; see the freeze list at the end.
**Created:** 2026-09-27, promoted from `repl-embedding-retrieval.md` REPL-EMB-B.1 (the quality-baseline seed).
**Owner index:** [user-facing-harness-index.md](user-facing-harness-index.md) (UFH-13).
**Depends on:** the role-swap stack-change package (in preparation, separate), HS-4 P4 `/v1` escalation parity
(UFH-01), RI-21 (routing-intelligence.md).

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
`architect_general` on `:8083` (MI210).
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
- [ ] **TE-1 — `/v1` escalation parity for A2 (HS-4 P4 subset, epyc-orchestrator).** **Approved by the operator
  2026-09-27 (with OP-66); being built by another agent — this box ticks when it lands with its tests.** `/v1` never escalates in either
  tool mode (orch `src/api/routes/openai_compat.py:595-596`), and `x_max_escalation` is recorded but not enforced
  (`src/api/models/openai.py:160-166`).
  - Add a default-off flag that lets a `/v1` frontdoor turn escalate to `architect_general` through the existing
    escalation policy, with the escalation receipt (fired, reason, target role) in the tap.
  - Add tests for off (byte-identical to today, which is A1) and on (A2).
  - This is the one piece of new code the experiment needs. Coordinate with UFH-01 HS-4 P4, and do not fork it.
- [ ] **TE-2 — escalation-target check after the role swap (zero inference).** Frontdoor escalates to
  `CODER_ESCALATION` (orch `src/roles.py:468-499`), an alias on `architect_general`'s server, and the graph hard-wires
  Frontdoor → CoderEscalationNode → ArchitectNode (`src/graph/nodes.py:250`, `:595`, `:615`).
  - After the swap, prove with `orchestrator_route_explain` that A2's escalation lands on the Flash-Next server, and
    that no hop ends on a role missing from `_ROLE_TO_NODE`. RI-21 is that defect: fix it (a one-line map entry plus a
    test), do not file it.
  - This fails if escalation lands on the 27B.
- [ ] **TE-3 — build and freeze the manifest (zero inference).**
  - The driver: a per-item OpenCode headless run through `scripts/harness/hs4_p04_acceptance.py`'s pattern. Pass the
    prompt on stdin, not positionally (HS-4 P7). Use one config per arm and randomized interleaving.
  - The consultant device-seconds aggregator over the tap, with offline tests.
  - The sha sidecar for the suite, then `FROZEN-AT-LAUNCH.sha256`.
  - Freeze only after TE-0.
- [ ] **TE-4 — belief-kernel write side before the first scored item** (`vidya-belief-substrate-program.md` VB-THESIS-1;
  source row in `scripts/vidya/adapters/README.md`). Write per-item rows with the arm, item id, suite, correct,
  escalation fields, consultant and frontdoor device-seconds and wall, plus the manifest digest. Project; do not grade.
- [ ] **TE-5 — run (inference; coordinated window; the main session runs it).**
  - Needs the role swap applied and serving proved, TE-1 deployed by an API reload, and TE-2, TE-3 and TE-4 done.
  - Run the plumbing smoke, then A0/A1/A2 interleaved, then the riders if cheap.
  - Estimate about 2 to 2.5 h: Flash-Next alone ≈ 55 min for 395 items. Frontdoor passes are shorter, and A2 is
    frontdoor plus the escalated items.
- [ ] **TE-6 — verdict.** Apply the frozen rule and record SUPPORTED / REFUTED / NO GAP / INCONCLUSIVE, with n, CIs,
  amendments and confounds. Route the result to the operator. The verdict is the unfreeze trigger for the frozen list
  below.

## Frozen behind this experiment (operator, narrowed plan, 2026-09-27)

These boxes carry a `❄ FROZEN 2026-09-27` marker in their own handoffs. Each stays open, because frozen is not done.

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

# 2026-09-27 — orchestrator design session (workspace-8d)

Continues [`2026-09-26-orch-design.md`](2026-09-26-orch-design.md), whose last section is the 2026-09-26 final
wrap-up. The narrowed plan has its own note, [`2026-09-27-narrowed-plan.md`](2026-09-27-narrowed-plan.md); this note
covers the whole day and records the decisions that came after it.

## Task-delegation probe (measurement package B)

- **Question.** HS-19a showed the frontdoor delegating through OpenCode's `task` tool. DS41-C20c showed the 27B on
  `:8083` never delegating (n = 1). Was that the model or the setup around it?
- **Instrument.** `scripts/harness/task_delegation_probe.py` (root `e043cfa3`, operator-approved, prepared with no
  inference). The parent agent carries the `x_force_role` pin; the `task` child has none. Every arm uses one logical
  model id, so the system prompt, tool list and task description are byte-identical across arms. Per-replicate seeds
  101/202/303.
- **Result** (`/mnt/raid0/llm/tmp/task-probe-20260927/`, 15 runs):
  - On the HS-19a prompt, which names `task`: frontdoor, 27B-nothink and 27B-think all delegated, 3/3 each.
  - On the DS41-C20c seat shape (a `planner` agent with fan-out *guidance*, a hidden `scout`, and a prompt that never
    names `task`): frontdoor and 27B-think both self-served, 0/3 delegated.
- **Reading.** C20c's non-delegation was the SETUP (prompt shape), not the model. Filed as
  `autokernel-orchestrator-actor-backend.md` **OAB-33**: actor delegation must be instructed, not offered (root
  `c9bc3859`).

## UFH-12 embedder policy arms A0 and A3

Run 10:15-11:31Z in CPU windows under the pre-registered rules of `/mnt/raid0/llm/tmp/next-window-runbook-20260927.md`.
Records: `epyc-orchestrator/data/embedder_placement/arms/{a0-20260927T1015Z,a3-sched-sat-20260927T1039Z,a3-low-duty-20260927T1111Z}`,
each with its `belief_measurements.jsonl` sidecars (the VB-UFH12-PLACEMENT reader; pin moved in root `dbec2414`).
The metric is r = G1 S/Q median (frontdoor-class decode, saturated ÷ idle; higher is better). The ABA is B = candidate,
A1/A2 = baseline, Δ = r_B − mean(r_A1, r_A2), floor = the relative A/A floor.

- **A0 (neighbour cap 0, scheduler load).** Valid: G2 drift 0.15%, whole-pool throughput B/A 0.995.
  - `:8070` r_B 0.992: HARNESS-OK.
  - `:8080` Δ +0.031 > 2·floor 0.021, r_B 0.961: **partial**.
  - `:8180` Δ +0.104 > 2·floor 0.007, r_B 0.969: **partial**.
  - Removing the SMT-sibling neighbours recovers part of the loss. The remainder is cross-node contention, which no
    cap can reach. Price of the bound: G1 embed texts/s B/A 0.154 / 0.897 / 0.681.
- **A3 (embedder `OMP_WAIT_POLICY=passive KMP_BLOCKTIME=0` vs the declared `active`, `KMP_BLOCKTIME=10`).**
  - sched-sat: Δ +0.001 / +0.011 / −0.005 against 2·floor 0.060 / 0.044 / 0.032, all **NULL**. Throughput B/A 0.985.
  - low-duty: all NULL.
  - A3-raw did not run. It cannot change the outcome, because adoption needs GAIN on ≥ 2 ports under sched-sat.
  - **Decision: keep the declared embedder env.**
- Both arms fed REPL-EMB-1.4 (the B+D policy), which the narrowed plan then froze. The readings are recorded in
  `repl-embedding-retrieval.md`, and nothing further runs for 1.4 while it is frozen.

## DAR-LAT-3h G1: outcome T96, recorded only, nothing applied

The operator signed package v2 (`RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926`, receipt root `bf610d36`). G1 ran
2026-09-27 ~17:41-18:57Z on experiment port `:18074`; live `:8074` was untouched. The driver was orch
`critic_thread_gate.py` @ `8b7e24e3`. There were 15 launches, 3 per arm, all clean. Every THP mechanism check matched,
and coherence was equal across arms (20/24 on W1 everywhere, the same 4 prompts).

| W1 comparison (the signed rule) | Wall | TTFT | Reading |
|---|---|---|---|
| T96 vs L (premise) | 0.988× | 0.950× | holds: `GGML_FUSED_DECODE_OFF` is inert under MTP |
| T48 vs T96 | 1.0385× | 1.055× | parity **fails** (bar ≤ 1.03×) |
| T48N vs T96N | 1.032× | 1.068× | parity **fails** |
| T96N vs T96 (THP shim) | 1.009× | 1.020× | no ≥ 2% gain; **not adopted** |

Mean decode tok/s:

| Arm | W1 (24-prompt mix, 200 tok) | W2 (critique, ~4k prompt, 400 tok) |
|---|---|---|
| L | 43.37 | 32.05 |
| T96 | 44.64 | 32.13 |
| T96N | 44.61 | 31.48 |
| T48 | 43.80 | 33.24 |
| T48N | 43.27 | 32.02 |

- W2 reaches the same outcome (T96), with larger 48-thread deficits: 1.053× wall, 1.113× TTFT.
- W3, reported only: a frontdoor request co-running with the critic's decode takes 3.3× its solo wall at 96 threads
  and 2.9× at 48 (n = 3 per arm, no floor).
- **Decision** (the main session's recommendation, operator-aligned with the narrowed plan): **record only, APPLY
  NOTHING.** The T96 row would add only `GGML_FUSED_DECODE_OFF`, which is inert under MTP. The live critic already
  runs `-t 96`. No reload, and no contention recertification.
- **What it settles.**
  - The 2026-09-22 C3 ruling (`NUMA_FULL_T48`, "48 is the served decode optimum") is superseded. A note is added
    where C3 is referenced: `lineup-change-20260922.md` §C3 and SSU-F11.
  - `GGML_NOHUGEPAGE_PROCESS` gives no gain on v10 at the served shape.
  - DAR-LAT-3g's thread blocker is resolved in substance.
  - DAR-LAT is now FROZEN apart from the thesis experiment.
- **Do not merge** the `lane/dar-lat-3h-v2-*` outcome lanes, in orchestrator or research.
  `artifacts/operator/stack-change-dar-lat-3h-20260926/RESULT.md` says so. `PACKAGE.md` is sha-pinned by the receipt,
  so it was left untouched.
- **Durable evidence.** `g1-result/verdict.json` (a byte copy) and `g1-result/summary.json` (per-launch stats plus the
  sha256 of every evidence file). The raw directory is
  `/mnt/raid0/llm/epyc-inference-research/data/dar-lat-3h-gate-20260927T1740Z/` (untracked).
- **Residual (known, not applied).** The research recipe text still says `threads: 48` / `THREADS = 48` (research main
  `scripts/lib/qwen38_flash_next_recipe.py:447`), because the correcting lane R1 was not merged. Nothing reads that
  block (SSU-F11). When `recipe:` becomes load-bearing, it must derive 96.
- **Belief kernel.** No source row exists for the critic thread gate. VB-SEL-LOADAB is the DAR-LAT-3 load sweep's
  write side, which is frozen. The G1 result is therefore recorded here only.

## Fable audit and the narrowed plan

A Fable audit of workspace-8d's work from 2026-09-25 to 2026-09-27 found that the thesis had been named but never
measured, while infrastructure grew. The thesis: the orchestrator must beat the strongest model with an off-the-shelf
harness. The operator adopted a narrowed plan (root `9d99564a`; detail in
[`2026-09-27-narrowed-plan.md`](2026-09-27-narrowed-plan.md)):

- **UFH-13 is TOP priority**: a thesis experiment on the frozen MMLU-Pro 200 + GPQA 195 manifest, with three arms.
  - A0: Flash-Next alone.
  - A1: frontdoor alone.
  - A2: frontdoor with escalation to the consultant.
- **Frozen**, with the boxes left open and an unfreeze trigger on each:
  - HS-19b, HS-19c and HS-19d P1–P6;
  - TD-28;
  - REPL-EMB-0.3 and 1.4;
  - DAR-LAT, apart from 3h's G1, now recorded;
  - LRC-1 and LRC-2;
  - OD-A F7 and F6.
- The UFH-12 A1 duty sweep is cancelled.

## Role swap: operator decision

**Only `architect_general` moves to Flash-Next.** `coder_escalation` and `ingest_long_context` stay on the 27B. The
27B takes `architect_critic`. A separate agent is preparing the `stack-change` package; it lands on root on its own.

This matters for UFH-13. Frontdoor's existing escalation hop is `CODER_ESCALATION`, so after the swap that hop lands
on the 27B. A2 must therefore escalate to `architect_general` explicitly (TE-1), and TE-2 proves where it lands. The
thesis handoff now says so.

## OP-66: approved and pre-registered

The operator approved both rules in chat on 2026-09-27, as drafted:

- **(a) UFH-13.** X = 0.75, Y = 0.50: G ≥ 0.75 at d ≤ 0.50, and G's 95% lower bound > d. PRE-REGISTERED in the thesis
  handoff § *Decision rule*; TE-0 ✅.
- **(b) UFH-12 kill rule.** recall@5, M = 0.10, n ≥ 120, paired-bootstrap lower bound > 0, and the cheapest arm within
  X = 0.05 wins. PRE-REGISTERED at REPL-EMB-2.1 ✅.
- **(c) TE-1** (the default-off `/v1` escalation flag) is approved. Another agent is building it, and its box stays
  open until it lands.

Both rules are frozen: changing one needs a new registration. The OP-66 queue row was removed and archived in
`handoffs/archived/master-handoff-index-history-through-2026-09-14.md` § *Resolved 2026-09-27*. The
UFH-13 row's next action is now TE-1, then TE-2/TE-3. The UFH-12 row's next action is now REPL-EMB-2.2.

## Governance guard and countersignature record

Root `5ef39690` covers both.

- **The guard.** Every ratifier refuses a defaulted signer: an unset `RATIFY_OPERATOR`, a system account, the login
  account, or an agent id.
  - The shared guard is `scripts/operator/lib/ratify_operator.sh`. The rules live once, in
    `ratification_receipt.py check-operator`.
  - The receipt tool returns REFUSED instead of recording `$USER`.
- **The countersignature record.** `artifacts/operator/countersign/COUNTERSIGN-20260927.md` holds four ratifications
  that were chat-approved and agent-executed: P-SERVE-SEL-1, OP-63, TRUST-BOUNDARY-RECEIPTS-FIX and DAR-LAT-3h.
  - Each stands as CHAT-CONFIRMED.
  - The terminal countersignature (`scripts/operator/countersign_20260927.sh`) is the operator's to run. It is
    master queue **OP-67**, still open.

## Open

- TE-1: in build by another agent. Then TE-2 (after the role swap), TE-3 (manifest freeze) and TE-4 (VB-THESIS-1
  write side), before TE-5 runs.
- REPL-EMB-2.2: the offline recall eval, with VB-UFH12-RETR wired first.
- OP-67: the operator's terminal countersignature.

## Evening: TE-1 landed, thesis runner, ARCHSWAP amended, A-3 fix (wrap-up)

Supersedes the *Open* list above for TE-1, TE-2 and TE-3a.

### TE-1: `/v1` escalation (UFH-13 arm A2)

- Orchestrator `9959e8db` adds the default-off flag `v1_escalation` and the per-request key
  `x_escalation: auto | off | architect_general` (anything else returns 422). A finished frontdoor answer passes
  through the same post-answer hooks `/chat` uses, in `/chat`'s order: `_quality_escalate`, then the review gate, then
  `worker_general`'s revision on a WRONG verdict.
- Every escalation call is a receipt step in the telemetry. The receipt carries consultant device-seconds and
  request device-seconds. There are 24 unit tests plus a golden test showing the flag-off path is byte-identical.
- `280059cc` makes escalation opt-in per request: with `x_escalation` absent, nothing changes, whether the flag is on
  or off.
- Full unit suite: 15620 passed. The code is not serving yet; deploying it is TE-reload.

### Thesis runner (research)

- `2b59bebe` adds `scripts/benchmark/thesis_ufh13/` with four verbs: `plan`, `pilot`, `run` and `score`.
  - Results persist per question, and a run can resume.
  - The suite is sha-checked.
  - A bootstrap scorer computes G and d.
  - `score` writes a ClaimTuple-shaped `belief_measurements.jsonl` (the VB-THESIS-1 write side).
- `0a8fa57b` adds a disjoint pilot pool at `data/ufh13-thesis/pilot_pool.json`, sha256 `0898013e…aa3c5`, with
  453 items.
  - MMLU-Pro contributes 200 items, with a category mix matched to the suite.
  - GPQA contributes 253 items: every GPQA question on disk that is not in the suite.
  - The runner refuses any frozen question. 29 tests.

### ARCHSWAP (the architect role swap)

- **Approval.** The operator approved A-1 to A-5 in chat, with one amendment: review AND plan decomposition stay on
  the 27B, and only escalation moves to Flash-Next.
  - Review stays through `DEFAULT_REVIEWER_ROLE = architect_critic`.
  - Plan decomposition stays through a new `DEFAULT_PLANNER_ROLE = architect_critic` with `resolve_planner_role()`.
- **The amended package**, on lanes:
  - orchestrator `lane/archswap-20260927` @ `e08ec06d`;
  - root `lane/archswap-20260927` @ `6dbbd7a1`;
  - research `lane/archswap-20260927` @ `61af24fa`.
- **Reconciled with TE-1.** `x_escalation=auto` sends the answer verdict to the reviewer binding, which is the 27B.
  `x_escalation=architect_general` pins every consultant call to Flash-Next.
- `--validate-only` returns VALID.
- **Signing was blocked for the agent.** The operator gave chat consent ("run now with my consent"). The auto-mode
  safety classifier still BLOCKED the agent from running the ratify script under the operator's name. Signing is
  therefore an operator action from a terminal (the command is below).
- **Security flag.** The package's subagent raised an "instruction poisoning" flag. The main session reviewed the
  diff and found it on-task. The flag was attributed to approval quotes in code comments, and those quotes were
  removed.

### A-3 fix: the prewarm and scout region-lock bypass

- Orchestrator `lane/orch-prewarm-lock-20260927` @ `9a4785e1`, based on the swap lane at `e08ec06d`. It is pushed to
  origin as a lane backup only, and is NOT on main.
- **What it does.**
  - A new module, `src/runtime/direct_region_claim.py`.
  - The escalation prewarm makes one non-blocking claim attempt on a CPU-resident target, or skips.
  - The scouts hold one claim per stage and run concurrently inside it.
- **Tests.** 12 new tests. Full unit suite: 15635 passed and 1 known failure, a test that reads the unswapped master
  registry.
- **Order.** It lands after the swap commits and before the bring-up API reload (PACKAGE §7 step 1). The bypass is
  never live unfixed.
- **Side effect.** Frontdoor scouts now hold the frontdoor claim for their whole stage, with a budget of up to 240 s.
- **Approval.** gitnexus rated the impact on the prewarm and scout symbols HIGH. The operator approved the fix.

### Coordination

- workspace-76 confirmed that DS41 binds the 27B by port, so the swap does not affect it.
- The AutoKernel `run.py` help text changes to `orch:architect_critic` in the research swap lane. That repo is
  workspace-76's (INF-78).
- Any `architect_critic` (:8083) reload must be coordinated with workspace-76 and happen between actor calls.

### Signing and bring-up (the operator's next steps)

Run the signing from a terminal:

```bash
cd /mnt/raid0/llm/tmp/archswap-20260927/root/artifacts/operator/stack-change-archswap-20260927 && RATIFY_OPERATOR="pestopoppa" THINKING_OPTION=follow-model BRINGUP_OPTION=B1 ./ratify_archswap_20260927.sh --attest RATIFY-ARCHSWAP-20260927
```

Then the bring-up follows PACKAGE §7:

1. Merge the three lanes, plus the A-3 fix with the orchestrator lane.
2. Relabel the state.
3. Run the API-only reload with `ORCHESTRATOR_V1_ESCALATION=1`. This one reload is both B1 and TE-reload.
4. Verify that the reviewer resolves to the 27B, and run the serving proofs P1 to P4.
5. Run TE-pilot.

B2 follows at the owners' boundaries.

### Commits

| Repo | Commit | What | On main |
|---|---|---|---|
| epyc-orchestrator | `9959e8db` | TE-1 `v1_escalation` flag + `x_escalation`, telemetry, 24 tests + golden | yes |
| epyc-orchestrator | `280059cc` | TE-1 escalation opt-in per request | yes |
| epyc-orchestrator | `e08ec06d` | ARCHSWAP amended lane tip (reviewer/planner stay on 27B) | no (lane, unsigned) |
| epyc-orchestrator | `9a4785e1` | A-3 prewarm/scout region claim (`lane/orch-prewarm-lock-20260927`) | no (lane backup) |
| epyc-inference-research | `2b59bebe` | thesis runner `scripts/benchmark/thesis_ufh13/` | yes |
| epyc-inference-research | `0a8fa57b` | disjoint pilot pool, 453 items | yes |
| epyc-inference-research | `61af24fa` | ARCHSWAP registry + `run.py` help text | no (lane, unsigned) |
| epyc-root | `cb8d85e2`, `f3ed7dec` | TE-1/TE-2 ticked; TE-3a, TE-reload, TE-pilot, VB-THESIS-2 filed | yes |
| epyc-root | `f115a9d4` | TE-3a ticked with the operator's freeze decisions; SSU-F17 filed | yes |
| epyc-root | `e8abf01d` | index next actions | yes |
| epyc-root | `6dbbd7a1` | ARCHSWAP package amendment (UNSIGNED) | no (lane, unsigned) |

The TE-3a freeze decisions are: (a) `--transport v1` with fixed sampling, a declared deviation from OpenCode; (b) the
verdict order as implemented; (c) `worker_general` revises. SSU-F17 (roles bind to server ids) is sequenced after
UFH-13.

### Open

- ARCHSWAP signature: the operator, from a terminal.
- Then bring-up B1 with the A-3 merge and TE-reload fused into it, then TE-pilot.
- TE-3: freeze the manifest. TE-4 and VB-THESIS-2: the belief-kernel write side and read side.
- B2 relaunches at the owners' boundaries: `:8083` with workspace-76, `:8074` at a CPU-quiet boundary.
- VB-UFH12-PLACEMENT discovery: the placement adapter does not see the `arms/` sidecars.

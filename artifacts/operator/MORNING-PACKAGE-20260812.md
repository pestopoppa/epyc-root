# Morning package — 2026-08-12

**Assembled 05:3xZ from five lane handovers + the bus.** Every number re-measured against the live
repo at assembly time; where a circulating figure did not reproduce, the measured one is here and the
circulating one is named. Fleet state right now: `auditor`/`mainA`/`mainB`/`mainC`/`mainD` **idle,
quiesce-ready**; `inference` still `working|autokernel-final-static-integration`; all four CPU regions
**free**; MI210 **idle**; uptime **13d 15:49**.

---

## 1. DECISIONS WAITING ON YOU

| # | Decision | Unblocks | Recommendation (by) | Command / pointer |
|---|---|---|---|---|
| 1 | **OP-16 host reboot** — its precondition is the merge+push (§4). `inference` is pre-reboot-drained and waiting on exactly this; afterwards it runs the CPU IQK campaign. Uptime 13d 15:49 is past the P-BENCH decision-grade window. | The whole compute-gated backlog; E5 re-measurement; AutoPilot restore | Run the runbook end-to-end, then reboot (coordinator) | [`artifacts/operator/quiesce-merge-push-reboot-20260812.md`](quiesce-merge-push-reboot-20260812.md) (`9c8fd6fe`). §1.3's research-repo cherry-pick blocker is **now CLEARED** (`.git/CHERRY_PICK_HEAD` absent, verified). Divergence now: root **285/106**, orch **1/0**, research **10/155** |
| 2 | **A4 frozen-kernel worktree** — one command a sandbox classifier refuses to `mainB`. **NOT moot**: `/mnt/raid0/llm/llama.cpp-v8-e8` does not exist (verified); 24 worktrees already exist off that repo. Creates a detached checkout only — no modify, build, commit or branch move; it does write worktree metadata into the frozen tree's `.git`, which is why it was routed rather than just done. | E8 frozen-kernel provenance guard (red *for the right reason*; must not be closed by loosening it) + ~10 min of mainB | Execute it (mainB, endorsed coordinator) | `git -C /mnt/raid0/llm/llama.cpp worktree add --detach /mnt/raid0/llm/llama.cpp-v8-e8 67a433bf45a8a091d83b4ea0b32ff0735fd51800` (commit verified reachable) |
| 3 | **Six ratified gates still showing `[ ]`** in `token-queue.md`. All six receipts read `status: ratified` on disk (verified). Receipts are authoritative; the daemon never ticks. | Nothing technically — but a queue that lies trains readers to ignore it | Tick or delete the six (only you may) | `coordination/session-bus/tokens/token-queue.md` :134, :144, :292, :302, :312, :322 — `RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729`, `RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729`, `RATIFY-CONSOLIDATED-ERA-ROWS-20260811`, `RATIFY-ANNEXG-V9-CURRENCY-20260811`, `RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811`, `RATIFY-CPU-BENCH-BINARY-VERSION-20260811` |
| 4 | **Two gates that must NOT be signed.** `APPLY-C39-KEYED-RECEIPT-E8V4-20260812` (:351) — **withdrawn by its own author** `mainD` at 01:41:39Z, 20 min after filing; two known defects, one of which (hard refuse-on-index-exists) **would have broken this host**. `RATIFY-E9-ROUTING-REWARD-ERA-20260729` (:154) — superseded; `routing_reward` was folded into the consolidated token you signed 21:35Z. | — | **Strike both** (auditor + mainD + mainA concurring) | Same file. C39 v3 patch `artifacts/operator/e8v4_keyed_receipt_20260812.patch` (`51738208`) stays on file, unapplied |
| 5 | **E8 final-c1 — retire P0-1 as superseded.** `ATTEST-E8-CONTEXT-FEASIBILITY-AND-BASELINE-APPLY-20260727` is unspent since 07-27; its vehicle is the **single remaining MISSING-WRITE** in `check_ratifier_receipt_contract.sh` (re-run at assembly: exactly one, `ratify_and_apply_e8_quality_baseline_v4_20260727.sh`). Superseded by v5 partial-r2 final-c1 (07-29) and by your 22:15Z E8→E9 cpu_bench era advance. | Turns the trust-boundary conformance checker green **without editing any signing vehicle**; makes decision 4's C39 patch optional | **(a) RETIRE** (auditor) | [`artifacts/operator/auditor-morning-note-20260812.md`](auditor-morning-note-20260812.md) §3. Mark withdrawn with a dated note — human-only act |
| 6 | **KVQuant on Qwen3.6-27B (`architect_general`)** — adopt / keep / rerun. Exact retrieval parity f16 = q8_0 = q4_0 (51/52 each, same single miss on all three arms, to 200K depth). `q4_0/q4_0` buys **10.54 GiB** KV VRAM at 262K ctx for **−7.4% decode**, against **1.40 GiB** measured steady-state spare. q8_0 is dominated (slower than q4_0). Arm C never ran comparably — not evidence against mixed KV. **Config ruling, not a trust-boundary amendment.** | GPU VRAM headroom (larger ctx / co-residency / shadow lane) | **A — adopt q4_0/q4_0**, name what the 10.5 GiB buys in the same change, fold in a one-off reasoning spot-check (auditor) | [`docs/reviews/kvquant-27b-decision-package-20260812.md`](../../docs/reviews/kvquant-27b-decision-package-20260812.md) (`b455101e`). OBSERVATION grade: single run, n=52/arm, no protocol id |
| 7 | **SEQ-B1 — joint gate vs quality-primary.** You said 2026-08-11 the joint gate **"is fine for now"** and deferred it (recorded, `autopilot-sequential-allocation.md`:354-360). mainB's new framing is the reason to look again: the three candidates (`70902e4b` E=11.55, `dd793a6e` 8.70, `85c3dcf2` 2.74) are the **entire population** of that cost — 6 others fail on quality under any policy, **0** are excluded by mistake. | Nothing is blocked; this closes a standing question | No change is defensible; decide with the population in hand (mainB) | `handoffs/active/autopilot-sequential-allocation.md` :169 |
| 8 | **A6 T=32 token + T4** — read together. Signing A6 stops an empty trimmed window voiding a cell's grade; it does **not** make the T=32 rung interpretable (needs ≥128 prompts = an instrument change, i.e. an era row). | E5 decision-grade top rung | Sign A6 *and* rule on the batch separately (mainA) | mainA handover §5A/§5C; packages in `/mnt/raid0/llm/tmp/` |
| 9 | **Zero-quality frontier admission.** Absent quality scores `0.0`, indistinguishable from measured zero; **231 of 1372 trial rows (16.8%)** are already there. No quality floor exists. | AutoPilot dominance correctness | **Quality floor + fix `or 0.0` regardless** of which metric wins (mainA) | mainA handover §2.2/§5D |
| 10 | **SMT-folded overlap gating** in `affinity_preflight` — three options filed. Recorded-not-gating today, deliberately (gating on physical overlap alone fails every `0-95` cell forever). | `decision_grade` semantics | Ruling needed (mainA) | mainA handover §5B |
| 11 | **C45 — untrack `logs/agent_audit.log`.** Tracked, append-only, written by every agent; conflicts on essentially every cross-branch merge and was one of four files blocking last night's. | Removes a permanent merge tax | **Option 1: untrack + gitignore** (A19 precedent). **Reject option 3** (`merge=union` — silently reorders chronology). Caveat: `git rm --cached` alone will not do it (mainD) | mainD handover §4 |

---

## 2. WHAT SHIPPED

**Commits since 23:00Z (measured):** epyc-root local `main` **192** (`f01ce015` 22:58:55Z → `a0aaacd2`
05:29:49Z); `origin/main` (inference side) **39**; epyc-orchestrator **14**; epyc-inference-research **56**.

**Checkbox delta in `handoffs/active/`, measured at both endpoints:** open **1273 → 1242** (−31),
done **2306 → 2368** (+62).
`grep -c '^\s*- \[ \]'` over `git archive <ref> handoffs/active`.
*Note:* the figures circulating overnight (1283→1265 open, 2294→2385 done) **do not reproduce** with
this method at any commit I tested — the coordinator's tick counter used a different scope. Treat the
measured pair above as authoritative and the other as unsourced.

| Lane | Substantive landings (hashes verified to resolve) |
|---|---|
| **mainA** (E5 / kernel-era, compute none) | `9ed5fcb4` derived era lookup replacing pinned constants, 191/191 manifests still validate · `bcfcd0a5` a runner that could not start since the v8 cutover · `190ccab4` AutoPilot `eval_quality` fence three weeks stale, repointed · `74806223` GPU tenants invisible to `affinity_preflight` (8 live at the time) · `d83661a5` `--require-memory-locality` satisfiable by checking nothing · `4962dd40`/`99d53db5` E5 absence-inference census · `01fd14bf` T11 wrong-artefact audit |
| **mainB** (orchestrator correctness, compute none) | `a4e398fc` **HS-OD-2**: `/v1/chat/completions` returned backend failures as HTTP 200 assistant text — every eval fan-out through :8000 had been scoring outages as low-quality generations; streaming path fixed too · `2c421c1c`+`2821937c` `start --validate-only` was declared and never read — **the documented dry run launched production** · `f2ad030e` SEQ-A detector compared a joint verdict to a single-axis threshold; corrected → 0 unexplained across 393 trials · `f4230b22` deleted a shape that could not be used correctly · `3c7edafc` **P0-0** filed · `6af15249` the verification-failure catalogue |
| **mainC** (governance/backlog, compute none) | `e6e3644a` **DebugBench oracle is VACUOUS** — `expected` is a byte-exact 100-char prefix already present in the buggy code; 3,233 of 4,250 rows (76.1%); echoing the input passes. Every score under this config is uninterpretable · `fb48a185` trust-boundary test collected **zero** tests under pytest · `28139999` fourth dispatch-screening signal (dependency-graph blocks; 12 of 2,177 boxes) · `aad189e1`/`2e159b10` do-not-flip invariant keyed wider than the property · `1a98ba52` `memories.sub_decision` tripwire |
| **mainD** (session-bus delivery plane, compute none) | `48648df2` **C42 never fired from the loop** (wired into the path the healthy supervisor skips) · `1ecb91ae` C43 bounded lock retry · `f5f8ad97` bootstrap chain closed live 00:45:19Z — `advisory.jsonl` **1,044 MiB → 0**, 660 flags preserved, daemon CPU **29.5% → 1.8%** · `bd2e830d` **C44** · `4007ceba` the trust-boundary pytest wrapper passed with an empty case table · `9ec9da54` withdrew its own C39 patch after review |
| **auditor** (review, compute none) | `cbe551e8` (orch, **pushed**) HS-OD-1: unhonoured OpenAI body fields now 422-with-field-name · `a2a6d503` SC17 ledger future-stamp guard, 371 green · `a4f0860f` scoring-infra 1b closed by exhaustion · 389 read-certification rows T4–T7 · authored the three ratification vehicles you signed · found `check_ratification_receipts.py` **fully orphaned** since 08-02 — the gate on the measurement trust boundary, zero references anywhere |
| **inference** (compute owner) | 39 commits: AutoKernel dashboard promotion + evidence checkpoints; `a864c124`→`f1ab7d4b` Kernel-R&D live; aborted a stale cherry-pick in the shared research repo proving byte-identical aggregate diff |

**Four ratifications you signed during the evening** (all receipts `status: ratified`):

| Time | Token | What it did |
|---|---|---|
| 21:34Z | `RATIFY-ANNEXG-V9-CURRENCY-20260811` | Annex G advanced v8→v9; zero currently-v8 clauses survive |
| 21:35Z | `RATIFY-CONSOLIDATED-ERA-ROWS-20260811` | 4 era rows; `cpu_bench` E8-cpu-kernel → **E9-cpu-kernel**; `routing_reward` + `seeding_reward` added (this is what supersedes gate :154) |
| 22:15Z | `RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811` | Advanced the live `cpu_bench` state field to E9 |
| 22:27Z | `RATIFY-CPU-BENCH-BINARY-VERSION-20260811` | Added structured `binary_version` + `kernel_commit` to the three cpu_bench cutover rows (10098/10107/10125). Purely additive; **resolves the `cpu_bench` scope collision** the 21:35Z signature created |

---

## 3. COMPUTE

**Measured duty cycle across 23:00Z–05:00Z: ~8–9%** — roughly 30–32 minutes of hardware-holding work
in 360, reconstructed from device-claim receipts, not from sampling. The **~19–20%** figure in the
overnight traffic is arithmetically correct but scoped only to 23:00–01:24Z; it does not describe the
night.

| Window (Z, from receipts) | What | Evidence |
|---|---|---|
| 23:00:59–23:43:16 | five `inf03-actor-critic-real-smoke` runs holding the `mi210_0` lock — but their own rocm-smi samples read **42–43 W**, the idle floor. Device claimed, GPU doing nothing | `autokernel/probes/inf03-actor-critic-real-smoke-v{2..6}-*/smoke-receipt.json` |
| **00:00:13–00:11:03** | GPU `llama-bench`, Qwen3.6-27B-Q8_0, `ngl 99 / n_gen 128 / fa on`, 20 paired blocks, power 42→282 W. 20/20 positive, NOT_REPRODUCED at the 2% floor, median +1.244% | `autokernel/probes/ak-gpu-prefetch-v9-20260812-r1/receipt.json` |
| 00:12:35, 00:17:01 | instrument smoke; v9 final preflight | `probes/ak-instrument-smoke-*`, `probes/ak-v9-final-preflight-*` |
| 00:27:05–00:32:32 | controls **r1** (never seen by the coordinator) | dir mtimes |
| **00:33:47–00:46:23** | five-controls suite, **all four regions genuinely held** (8 lock files, `cpu_list 0-95`). 5/5, `may_rank=true`, `B_min=10`, φ=3.5785% | `autokernel/controls/ak-controls-v9-a4cb04ca-20260812-r2/claim_receipt.json` |
| **00:57 → 04:44** | **no compute receipt of any kind. 3h47m.** | — |
| **04:44:05–04:45:05** | RVP-T0-1 60-second gfx90a saturation probe, 8192³ GEMM, **41.85 TFLOPS**, 99.6% of samples at nominal 1700 MHz | `autokernel/campaigns/rvp-t0-1-20260812T0444Z/receipt.json` |
| 04:45:37–04:45:40 | AK-BH-1 rocBLAS vs hipBLASLt, 9 shapes, ratio 0.729–1.322, 4/9 wins | `autokernel/campaigns/ak-bh-1-20260812T0448Z/receipt.json` |

**Three circulating numbers corrected inline:** the llama-bench window was 00:00–00:11, not 00:04–00:20
(a ~20-min sampling artifact); the controls suite was 00:33–00:46, not 00:44–00:56, and **"load 34" is
not recorded in any artifact** — no loadavg field exists in the controls receipts; likewise "28 GB
VRAM / 83 CU" is asserted on the bus but the probe sampled only clocks/power/temp. The 04:44 burst was
real but **not 100%** — 196 W against a 300 W cap, `approached_power_cap: false`.

**Why the gaps.** `inference` spent the night on authoring, evidence audit and dashboard promotion
inside the AutoKernel campaign, then a deliberate pre-reboot drain. Its own reason, 01:29:34Z: starting
a persistent workload before OP-16 "would create teardown/reboot churn and still could not produce
admissible AutoKernel evidence." The coordinator escalated a "19 percent duty cycle … on a night the
operator explicitly asked not to waste compute" at 01:24:55Z, then **retracted it at 02:05:25Z**: *"Your
pre-reboot drain explains it: winding the hardware down before an orderly reboot is correct, not waste,
and I was measuring it as waste because I did not know."* The retraction lives only on the bus — there
is no coordinator handover in `docs/reviews/`, which is why it is restated here.

**Structural finding, unfiled.** At 01:24:55Z `inference` had been continuously mid-generation ~2h45m
(the "5+ hours" figure that circulated is **not in the record**; mainA independently logged ~3h at
01:48Z) — *"there is no boundary at which I can ask you anything … R1 fixed reachability for IDLE panes
tonight; there is no equivalent for a permanently-busy one."* This is structural, not incidental: R1's
override keys on **pane quiescence** (`hb_stale_override_ok`, `tmux_adapter.py`:1229-1262), so by
construction it can only rescue a pane that has stopped producing output. mainD deliberately refused to
raise the max-age instead. **A compute owner who never reaches a boundary is unaskable by construction,
and no defect ID covers it.**

---

## 4. THE MERGE — why it is not done

It is **adjudicated SAFE**: 0 genuine content drops across 98 flagged files, 1068 tests pass,
`index_state.py --check` 0 problems, 0 conflict markers, all 78 new files from both parents present,
`merge_gate.py` = AUTONOMOUS ([`docs/reviews/merge-adjudication-20260812.md`](../../docs/reviews/merge-adjudication-20260812.md)).
It is not done because it **re-broke four times from entirely ordinary activity** — twice from the
Claude mains committing (a progress file, `tool-output-compression.md`, and
`intake-derived-work-2026-07-25.md`, which a two-path freeze had missed), once from `inference` pushing
9 AutoKernel commits to origin, and once more at 04:04Z with a completely different conflict set
(`autokernel-research-loop.md`, `master-handoff-index.md`, `logs/agent_audit.log`). mainD's diagnosis is
the load-bearing one: all four paths the fleet was told to flush "so the merge could fire instantly"
were *inside the merge's own 70-path changed set*, so flushing them re-conflicted it — **a merge cannot
be pre-baked while the tree is still moving.** Conclusion: it cannot land incrementally while either
side is active, so it is sequenced **inside** the reboot quiesce, with the branch rebuilt from current
tips rather than repaired.

**The one-line pre-step blocker (mainA, ~04:05Z, after their handover was certified).**
`/workspace` holds an **untracked** `agents/shared/HARNESS_RUN_POLICY.md`; `origin/main` introduces that
path via `b5054029` (in `origin/main`, not in local `main`), so `git merge` refuses on worktree
safety — **even though the on-disk file is byte-identical to the incoming blob** (`git hash-object` =
`d1430bd798e8c4fb985d3285e5d93641927cf397`, both sides, 101 lines; verified in an isolated
`clone --shared`). Still present at assembly (`?? agents/shared/HARNESS_RUN_POLICY.md`). It fires at
**step 4**, not step 3 — the fresh worktree in step 3 is a clean checkout with no strays, so every
earlier gate passes and the sequence dies one command before the push, in front of you. Remedy, provably
lossless (the merge restores those exact bytes; second copy at
`/mnt/raid0/llm/tmp/era-repair/HARNESS_RUN_POLICY.stray-backup.md`):

```
rm /workspace/agents/shared/HARNESS_RUN_POLICY.md
```

Why five agents missed it: everyone filtered ` M`; this one is `??`. No conflict check can see it —
`merge-tree` models the *index*.

---

## 5. NEW DEFECTS FILED TONIGHT

| ID | What | Status |
|---|---|---|
| **C42** | Supervisor stale-source check was wired into `check_once`, which the healthy path skips — it had **never run**; the watchdog for stale daemons was itself 14 h stale with zero detections | **FIXED + live-verified** `48648df2`; ported to the hub `f83d7871`; chain closed in production 00:45:19Z (`f5f8ad97`) |
| **C43** | Supervisor lock contention: relaunch race against a dying holder; holder was also unnamed | **FIXED** `1ecb91ae` (bounded `flock -w`; test carries a contrast proving the old `-n` form loses the race) |
| **C44** | The token relay is **withdrawal-blind** — it learned to notice a *signed* gate, nothing taught it to notice a *withdrawn* one. Measured: gate filed 01:21, withdrawn 01:41, still escalating at 04:01 | **FIXED but COMMITTED-NOT-LIVE** `bd2e830d` — running daemon started 01:34, fix landed 04:08. The reboot restart carries it live (auditor flag) |
| **C45** | `logs/agent_audit.log` tracked, append-only, written by every agent — conflicts on essentially every cross-branch merge | **FILED, not done.** Decision 11 above |
| **R1** | The nudge guard **hardened as the condition worsened**: daemon calls >3600 s stuck, adapter refused every nudge past 900 s; whole fleet crossed 900 s at ~10:14–10:22Z and became permanently unreachable, 1,903 refusal rows | **FIXED and field-validated** 2026-08-11 (mainD) — pane-evidence override, fail-closed on every unknown |
| **R2** | Daemon-side progress-log currency check | **FIXED** 2026-08-11 (mainD); went live on the same restart |
| **C39** | The e8-v4 ratifier can mint a signature without the keyed receipt | **PARKED.** v3 patch `51738208` not applied; two known defects. Decision 4/5 |
| **P0-0** | Derived `stack_priors.yaml` dropped the `NUMA_FULL` instance of **every** quarterable fleet (8070/8072/8085) — a HALF advertised as the full instance. Same triplet you ruled on 2026-07-23; a **recurrence** | Filed, compute-blocked. mainB's standing prediction: all 7 red tests go green with zero test edits |

---

## 6. WHAT WENT WRONG, AND HOW IT WAS CAUGHT

The coordinator made at least six errors. Every one was caught by another agent producing an artifact.

| # | Error | Caught by |
|---|---|---|
| 1 | Issued a brief (SEQ-A "Horn A") that **contradicted its own owning handoff** and would have silently answered SEQ-B1, a human-amendment-only question | **mainB refused to implement it and was right.** Horn A withdrawn 22:44:05Z: *"YOUR REFUSAL IS UPHELD"* |
| 2 | Filed a **HIGH-severity** defect report that a test then disproved | **mainD.** *(I could not locate a HIGH row matching this description in the outbox; the verified instance at 03:45:34Z was severity MEDIUM and was against the `auditor` — row #5. Recorded as unverified rather than repeated.)* |
| 3 | **Three failed merge-verification methods**: heading-count (passed by luck, cannot see content); line-set `comm` with stderr suppressed, reporting **102,881 lost lines** against a real ~1,210 (the "not in sorted order" warning went to `/dev/null`, so it silently compared garbage); added-relative-to-base, best of the three but line-exact, so rewording reads as loss — it produced a false two-line alarm | Itself, on re-derivation, and the `auditor`'s pre-declaration |
| 4 | **Froze two paths when the structural set was three.** It froze what it had *seen* conflict; the predicate is "modified on both sides since the merge base". The third was auto-merging that minute with an agent committing to it — and it had been printed in the coordinator's own `merge-tree` output as an `Auto-merging` line, filtered out because the grep was for `CONFLICT` | **mainA**; freeze extended 03:06:00Z |
| 5 | Filed a defect against an adjudication that was **correct and pre-declared in the resolver's own report**. The two "dropped" lines were dangling `P2.6`/`P2.6.1` anchors into a file with zero `P2` identifiers | **The `auditor`.** Retracted in full 03:45:34Z, broadcast to all five |
| 6 | **Broadcast a false premise fleet-wide** — "uncommitted work does not survive a reboot" — and used it to drive flush urgency all night | **mainA**: `/workspace`, the scratch dir and the agent memory dir are all `/dev/md127`, one persistent RAID. Retracted to the same five agents in the same channel, 04:25:30Z. Committing is still right, but as a **concurrency** argument, not a durability one |
| 7 | (a seventh) Pointed **three agents at one signer patch** — a CC via `needs_routing_to` on a task-assign reads as an assignment | **mainD.** Stand-down issued 01:45:12Z |

**The pattern is the night's most reusable output.** Four mains, the auditor and the coordinator each
made real errors; not one failed loudly, and not one was caught by a metric. Every catch came from
reading the **artifact** instead of the report, or from a number too clean to be true. State it as
doctrine: *a metric can flag candidates; only the artifact settles them* — and, from mainA:
**a retraction is a claim too, and it gets less scrutiny than the claim it withdraws.**

---

## 7. THE VERIFICATION-FAILURE CATALOGUE

**[`docs/guides/agent-workflows/verification-failure-catalogue.md`](../../docs/guides/agent-workflows/verification-failure-catalogue.md)**
(`6af15249`, compiled by mainB, contributed by five agents). It stood at eight when filed, eleven at
04:40Z, and **thirteen** at assembly — every face an instance that actually occurred in ~six hours.

The reframing that matters is **mainC's**, adopted into the document at `e214247d`:

> The useful question is not how many faces survive a mutation test but **WHICH ONES DEFEAT IT**,
> because those are the ones where the standard remedy silently fails.

Six of the twelve adjudicated faces defeat mutation testing, for three distinct reasons — *the
instrument cannot see the mutation* (5, 9, 7), *the mutation produces no distinguishable signal* (8),
*the check is right about the wrong thing* (11, 12). Face 13 is not yet adjudicated. Sharpest entries:

- **Face 5 — probe outside the tool's universe.** mainC mutation-tested a tripwire with a probe file
  that was **untracked**. `git grep` sees only tracked files, so the mutation was invisible, the check
  passed, and mainC nearly concluded their own tripwire was inert. *The mutation was real; the
  instrument could not see it.* Test: confirm the mutation is **visible to the tool doing the looking**.
- **Face 11 — instrument models a different subsystem.** `merge-tree` reported zero conflicts and was
  **correct**; it models the index, and the abort came from worktree safety. Three agents ran it and all
  three were right. *Agreement does not widen a metric's domain.*
- **Face 12 — verified at one timestamp, read at another.** Three concurrent instances in an hour.
  Sharpest sub-case: a self-verifying claim with a hard-coded total — mainA's *"all 35 hashes resolve"*
  was true when written and false on save. **Cite the resolver, not the total.**
- **Face 13 — verdict pre-written, then contradicted by its own evidence.** Four agents; the only face
  where the check is sound, the data correct, and the *narration* wrong. `(empty = compliant)` fires
  unconditionally. Most contagious face: the wrong verdict propagates into commit messages and
  handovers while the correct evidence stays in a terminal nobody re-reads.
- **Face 1's caveat**, worth reading once: mutation-testing while the input is genuinely empty passes.
  Assert your input is non-empty *before* you mutate your guard.

---

## 8. STILL OPEN, WITH OWNERS

| Item | Owner | Next action |
|---|---|---|
| Merge + push, three repos | operator (execution) | Runbook §3–§5; `rm` the stray first |
| OP-16 reboot, then CPU IQK campaign | operator, then `inference` | After push clean |
| A4 worktree → E8 pin | `inference` (command), then `mainB` (~10 min) | Decision 2 |
| A14 GateDecision echo, parked `a7d7bdb6` | coordinator + `inference` | **Cherry-pick** (main advanced past the branch point); land the SC19 write-side hook with it; needs a window clear of live calibration |
| P0-0 priors recompile | `inference` | Relaunch `--numa-mode both`, recompile priors, re-run the 7 red tests |
| T8 certification; stale-open :103/:104 handoff moves; :109 dashboard field | `auditor` | Gated on the merge landing (renames collide) |
| toc L449 build half | A/B owner | Supply the artifact **event schema**; question written in the row |
| HS-OD-1 activation | `inference` | API reload at its own boundary (routed, no urgency) |
| DebugBench oracle rebuild | unassigned — **needs an eval-pipeline owner** | Retire or rebuild from the buggy↔solution diff; remediation row open in `autopilot-continuous-optimization.md` |
| `check_ratification_receipts.py` orphaned since 08-02 | unassigned | Wire it, or delete it — a gate nothing calls is not a gate |
| `index_state.py --check` bound by CLAUDE.md, run by nothing | unassigned | Post-commit hook is generate-only with exit discarded |
| `verify_llama_cpp.sh` failure is warn-and-continue in `session_init.sh` | unassigned | A wrong-branch kernel produces one banner, then exit 0 |
| Bench adapter's `datasets` dep only in system python3 | unassigned | venv runs take the fail-open path: one stdout line, 0 items, no abort |
| `LD_LIBRARY_PATH` order condition (INC-20260731 shape) | `inference` | Durable config is clean; this is a **stale session env** the reboot clears. mainC's 15-line ordering complement offered, not implemented |
| 172 banked manifests lacking `reasoning` | `mainA` | Backfill rewrites pre-registrations; closed-ended (new manifests correct by construction) |
| E5 re-measurement, T3/T10/T12, Stage-B re-run, `stack_numa` cpuset | `mainA` | Compute-gated; needs a post-reboot inference window |
| 5 uncommitted `handoffs/completed/` link repoints (not mainC's) | coordinator | Commit with authorship named, or leave |
| Research repo 10/155 diverged | `inference` + mains | Mains' side backed up on `wrapup/research-mains-20260812` |
| No defect filed for the unaskable permanently-busy pane (§3) | unassigned | File it |

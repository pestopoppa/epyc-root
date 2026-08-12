# Reboot-Gated Inventory & Pre-Reboot Staging

**Created** 2026-08-12 · **Owner** open (filed by a governance sweep session) · **Domain index**
[research-evaluation-index.md](research-evaluation-index.md) `EVL-49`

> **Operator directive this document serves (2026-08-12, verbatim):** *"I will personally let you know
> when I plan to reboot. If any handoff requires special pre-reboot staging you can let them do it. In
> an ideal world it would be great to know everything that is reboot-gated in our backlog, and churning
> through any pre-reboot work those tasks need so that when we reboot we unblock everything as a whole."*
>
> **The reboot is not imminent and will be announced.** Nothing in here asks for one. This is the list
> of what it buys, and the work that has to happen first so it buys all of it at once.

---

## 1. The gate, measured — not quoted

Run read-only at 2026-08-12 11:28Z, through the same code path the harness uses
(`server_np_sweep.host_health_warnings(collect_attestation())`):

```
WARNINGS: ['uptime exceeds 1 week; MEASUREMENT.md P-BENCH-1/P-BENCH-3 policy requires reboot
           before decision-grade claims']
uptime_seconds = 1201884.7   (13.91 days)
numa_balancing = 0           ✓
existing_llama_processes = []✓
governor = performance · perf_event_paranoid = 1 · CPU boost observed to 4552 MHz · no throttle
```

**Exactly one warning, and it is uptime.** Every other host-health precondition is already green. That
is the headline: the reboot is the *only* thing between this host and decision-grade measurement, and
the moment it happens a very large batch becomes eligible simultaneously.

**Both routes to decision-grade are shut.** `server_numa_np_sweep.py:2141-2142`:

```python
overrides_active   = bool(args.allow_host_health_warning or args.skip_clean_check)
run_decision_grade = not warnings and not overrides_active
```

So `warnings` blocks it, and the override that clears `warnings` sets `overrides_active`, which blocks
it too. There is no third path. Screening / observation tier runs normally today.

**Asymmetry worth closing (defect-shaped).** `bench_canonical.sh` — the P-BENCH-1 canonical CPU path —
contains **no uptime or host-health check at all**. P-BENCH-3 (`server_numa_np_sweep.py`) fails closed;
P-BENCH-1 is honour-system. A canonical "decision-grade" number can be minted today that the policy
forbids, with nothing refusing it. See task S-11.

---

## 2. Sequencing — what has to be true before the reboot is callable

| # | Constraint | Source | State |
|---|---|---|---|
| 1 | **INF-03 must reach a durable boundary.** `inference` owns compute and has a live arena campaign (`inf03-available-source-six-arm-20260812-r4`, cell 006 in flight, PIDs 2889129/3435515/3435803). | `inbox/coordinator-agent.jsonl` msg-20260812T111121Z-173, 11:11Z today: *"OP-16 reboot remains necessary for decision-grade IQK/A7 work, but only after INF-03 reaches a durable boundary and explicit operator reboot authorization."* | LIVE — check at reboot time |
| 2 | **All mains wrap up and persist.** `SESSION_LIFECYCLE.md:43-55` makes pre-reboot wrap-up mandatory including commit. Unpushed at 11:32Z: epyc-root 15 commits / 79 dirty; orchestrator 13 / 14; research 1 / 1185 (mostly untracked results — never `git add` that tree wholesale). | `SESSION_LIFECYCLE.md`; measured | pending |
| 3 | **`tmux new-session -d -s agent` is the mandatory first post-reboot command.** `allow_session_creation: false` is deliberate; `cmd_spawn` fails closed without it, so **nothing spawns** until a human runs it. | C20, `session-bus-thin-dispatcher.md` | documented, not automated |
| 4 | **Nothing auto-restarts the supervision tier.** coordinator-daemon, `bus_supervisor.sh`, `hub_supervisor.sh`, `fleet_watch.sh` all die together and none self-starts. `hub_supervisor.sh` was already found dead on 08-10. | OP-9; `session-bus-thin-dispatcher.md` FW-3 | cron form drafted, not installed |

> **⚠ OP-16 is OPEN, not declined.** `session-bus-thin-dispatcher.md` (worktree-isolation row) states
> *"OP-16 was declined by the operator"*. No such decision exists anywhere on the bus, in
> `progress/2026-08/`, or in the token queue; `master-handoff-index.md:46` carries OP-16 open dated
> 2026-08-12 and `autokernel-research-loop.md` §AK6.5 carries it as an open package recommending Option
> A. Today's directive is *deferred-with-announcement*. The row's conclusion (a worktree cutover needs
> no reboot) is right; its stated reason is false and should be corrected before it is cited as
> evidence the reboot was refused. → task **S-13**.

---

## 3. THE BIG ONE — the reboot alone unblocks almost none of the batch loop

**25 compiled entries in `coordination/inference-batch/entries/` declare an uptime cap** (18 at ≤7 d,
7 at ≤14 d). At 13.91 d all 18 are already refused, and **the seven ≤14 d entries expire at ~13:37Z
today**.

But the uptime cap is the *declarative* half. The **machine-enforced** half is
`required_topology_hash`, which `run_batch_entry.py` compares fail-closed against the live
registry-derived hash — and **every one of those 25 entries is pinned to a dead value**:

| Pinned in the entries | Also pinned | Currently stamped in `contention_matrix.yaml:10` | Recorded live 07-30 |
|---|---|---|---|
| `8c8cfcbb13d2611d` (20-eval-tower, 30-bulk, 40-routing) | `kernel_era: production-consolidated-v7` | `171f86f9188211e9` | `bc28e15d` |
| `df373c79cc4af06f` (50-kernel-op2, 00-example) | `kernel_era: production-consolidated-v6` | — | — |

Production is **`production-consolidated-v9` @ `0db32c06`, binary 10125** (verified today,
`verify_llama_cpp.sh` exit 0). **So after the reboot, all 25 entries still fail closed — on kernel era
and topology hash, for reasons that have nothing to do with uptime.**

**Re-pinning those 25 entries is the single highest-value pre-reboot task in this document.** Without
it, the reboot clears one gate and leaves two. → tasks **S-01, S-02**.

---

## 4. Second-biggest: the host tunables are not persistent

`kernel.numa_balancing=0`, `perf_event_paranoid=1` and `governor=performance` are all set at runtime.
There is no `/etc/sysctl.d` entry, and `scripts/session/health_check.sh:173-174` **detects** the drift
but nothing **applies** it (`"fix: sudo sysctl -w kernel.numa_balancing=0 (self-resets per session)"`).
`session_init.sh` does not re-apply them either.

**Consequence:** post-reboot the host-health gate warns on `numa_balancing` instead of `uptime` — a
different warning, the identical block, and the fresh-uptime window burns while somebody works out
why. Non-interactive `sudo` is available to sessions, so this is a script, not an operator step.
→ task **S-03**.

Related, same class: **`drop_caches` is available today** (sudo works). A cold page cache is therefore
*not* reboot-gated — which downgrades the MI210 cold-load break-even item from A to B (§7).

---

## 5. Inventory

**Category key** — **A** genuinely reboot-gated (cannot be done at all until after) · **B** deliverable
claim is reboot-gated but the run executes today at screening tier · **C** misfiled: not gated, or
already satisfied.

Dispatch by **task TEXT**, never `file.md:LINE` — queue-wide anchor rot is 34.5%. Re-resolve with
`python3 scripts/coordination/backlog_row_check.py --row "<text>"`. Note `backlog_row_check.py` now
also refuses *prerequisite-blocked* rows (mainD, 2026-08-12) — a refusal may mean "blocked upstream",
not "rotted".

### 5.1 Category A — genuinely reboot-gated

| # | Item (cluster) | Owning handoff | Needs the reboot FOR | Pre-reboot staging required | Current staging state |
|---|---|---|---|---|---|
| A1 | **CPU IQK campaign rerun** + its three step rows (`CPU first`, IQK replay candidate #1, "Then a real one") | `autokernel-research-loop.md` | Preflight **refuses before claim/build/benchmark** at 13.47 d — there is no screening tier here at all | Seed `HYPOTHESES.md` entries; re-verify the dry run still composes 13 steps / 10 pairs; **read the dry-run output before executing** (the 2026-08-04 `LD_LIBRARY_PATH` defect: a candidate linked against the anchor's `libggml` measures the anchor and reports a clean null with every gate green) | **READY.** Envelope bound to recipe frame `e504d8e9…b079b0`; dry run clean; whisper/qwentts symlinks repaired; both speech kernels verified; durable command in `progress/2026-08/2026-08-12.md`; STOP_STATE receipts in `/mnt/raid0/llm/autokernel/campaigns/ak-iqk-v9-20260811/events.jsonl` |
| A2 | **OP-16** — the authorization itself | `autokernel-research-loop.md` §AK6.5 | It *is* the reboot | File it as a **pre-validated token block** in `tokens/token-queue.md` — today it exists only as a master-index row, so the one signature the whole A-list waits on is absent from the queue the operator actually reads | Package written (Option A/B + recommendation + default) |
| A3 | **AK-WM-2a / 2b / end-to-end campaign** (matched archive) | `autokernel-research-loop.md` | The archive builder accepts **only real** proposal-v3 events joined to clean DECIDED terminals; synthetic fixtures explicitly refused | Pre-format the projection plan (JSON-pointer + SHA-256 pin list) so receipts fire the moment two clean campaigns exist | Builder + receipts landed (research `900cb5c6`, `e8de8bfa`); 4,078-test suite; 98/98 receipt slice |
| A4 | **C20 — create the `agent` tmux session** | `session-bus-thin-dispatcher.md` | The defect exists only post-reboot | Put the command in `tasks/post-reboot-session.md` as step 1; **pre-write the roster respawn list with endpoint→window-name mapping** (C25: spawn names the window after the *endpoint*, so a mismatch means hand-fixing with `tmux rename-window` again) | Documented in `CURRENT-CAMPAIGN.md` and OP-16 Option A; not in the handover brief's step list |
| A5 | **Supervision tier has no auto-restart** (daemon · `bus_supervisor` · `hub_supervisor` · `fleet_watch`) | `session-bus-thin-dispatcher.md` (FW-3), `handoff-index-and-backlog-graph.md` (**OP-9**) | All four die at once and none self-starts | **Get the OP-9 ruling before the reboot** so the crontab is installed during the boot window; both cron forms are already drafted. Write the manual bring-up order (daemon → supervisor → hub → fleet_watch) into the brief as fallback | Drafted, not installed |
| A6 | **Daemon is running stale code** (C28/C38 committed-not-live) | `session-bus-thin-dispatcher.md` | Python loaded the module at daemon start; the reboot delivers the restart for free | Pre-format the post-restart receipt: `already_flagged` reads `relay_state.json`, tick ≈0 ms, `cmd_status` ≈0.4 s not ≈9 s | Fix verified by direct invocation |
| A7 | **Stack relaunch items:** `-np` drift (12 live-process drift errors), pytest-escaped API PID 3903691, C1 fix #2 manifest writer, `/slots` 0/19, WP-14 phantom lineup, dashboard tap live-render | `autopilot-continuous-optimization.md`, `autopilot-dashboard-fidelity-audit-2026-07-22.md`, `dashboard-architecture-restructure.md`, `within-role-placement-state-machine.md` | All need a **realized lineup** to compare against; the stack is fully down, so the observations are confounded, not failing | Pre-render the expected post-launch process table (per-port `-np`, threads, cpusets) so bring-up is a one-command diff; pre-write the `selected_servers` assertion from the launch manifest; pre-write the human-observation script for the tap (which URLs, which counters, expected ↑/↓) | Tap harness 88 checks / 0 fail; rest unstaged |
| A8 | **earlyoom `--ignore` tweak** | `dynamic-stack-concurrency.md` | earlyoom is PPID 1, started at host boot, outside the container; the flag changes only at its next launch | Write the exact host-side launch line **into the OP-16 package** so it rides the same authorization | Not applied (host-side) |
| A9 | **AP-19b** — first supervised live `gepa_optimize` | `autopilot-continuous-optimization.md` | Needs a live stack in a watched window; the post-reboot relaunch *is* that window | Dry-run the cold bring-up recipe (`esc8-stack-restart-landmine-audit-2026-07-22.md` §2026-07-25); pre-format the journal-row + ERROR-path checklist | Recipe written, never executed; blacklist lifted 2026-07-25 |
| A10 | **AP-WM-1b** — over AutoKernel's first real matched archive | `autopilot-continuous-optimization.md` | Transitive on A1→A3 | Build and dry-run the observe-only harness, fixtures and receipt schema against synthetic rows now — only the *inputs* are gated | Unstaged |
| A11 | **E8 quality-baseline reseed** | `autopilot-continuous-optimization.md` | **3 of 5 blockers are stack-shape** (24 unique ports, 5 live frontdoors, both-mode 6/6) and need the full-lineup relaunch | ⚠ **The reboot alone does NOT unblock it.** (i) Get the operator's A–D choice on the source amendment (zero compute); (ii) **delete the five `.staging-` bundles** left by the 07-26→29 `--execute` attempts — the runner forbids reuse and the post-reboot run will fail on residue; (iii) re-run `--prepare --t2-n 500`; (iv) regenerate the context coverage scan, which reports `required_tokens` in **BYTES** (task S-08) | 5 failed attempts, bundles still present |
| A12 | **Reviewer-plane throughput/latency rows:** LB-1 attribution · LB-4 paired throughput A/B · LB-7 M3 baseline floor · RD-12 latency+token accounting · RM-4 confirmation-tier protocol | `reviewer-latency-and-sampling-budget.md`, `reviewer-decision-plane.md`, `reviewer-model-ablations.md` | Deliverables are throughput/latency/cost. `MEASUREMENT.md:121` records the throttle signature as **multi-day uptime −60%+** — these are invalid by *magnitude*, not merely by grade. LB-1 would produce a confidently wrong attribution | Write the attribution script + per-call-class instrumentation offline; **pre-register which of the three hypotheses each outcome supports** so the post-reboot run is confirmatory; codify sampling policies as arms; freeze task sets + seeds; build the A0/A1 baseline arms; build RD-12's accounting + parse-failure-fallback tests and the 50-question replay set | RD-12's vehicle (RCP-W2) never ran; LB-3 partially landed (`30d3232b`) |
| A13 | **Hermes latency measurement** (first-token, total) | `hermes-outer-shell.md` | Same throttle logic. The handoff's own *"effective throughput much lower than raw 39 t/s"* may itself be a 13-day-uptime artifact rather than a design defect | Build the harness; **capture the current suspect reading labelled pre-reboot** so the delta separates the two explanations | Unstaged |
| A14 | **Tool-output-compression first-party A/B** | `tool-output-compression.md` | Row: *"MUST report WALL-CLOCK (neither paper reports latency)"* — wall-clock is the declared differentiator | Build the log-growth / grep-cost instrumentation and the arm harness | Unstaged |
| A15 | **ColBERT S4b / S6 latency** | `colbert-reranker-web-research.md` | A hard **200 ms** threshold against a **180 ms** GTE baseline — a 20 ms margin. Throttle does not degrade this verdict, it inverts it | Export LateOn INT8 (the actual blocker, offline); **re-confirm the 180 ms GTE anchor was itself taken on a compliant host** — if not, it is not a valid anchor and both arms must be re-measured | Harness exists (`bench_colbert_rerank.py`, `b37de4a`) |
| A16 | **Parser bake-offs with a speed axis:** ODL 200-PDF five-way · LiteParse-vs-ODL-vs-pdftotext · LightOnOCR latency · ERNIE MI210 rebench | `opendataloader-pipeline-integration.md`, `ernie-image-turbo-evaluation.md` | Speed is a scored axis in each; ERNIE's row is explicitly *"measure-not-extrapolate"* | **Acquire the OmniDocBench source PDFs + mint the immutable manifest** — pure download/provenance, and it unblocks `document-parser-table-bench.md` too (same work filed twice). Note the real local ceiling is **51 eligible PDFs, not 200** | ODL hard-blocked since 07-29 on the missing PDFs |
| A17 | **Strand RustEvo2 Phase B** | `strand-rust-coder-rustevo2-verification.md` | Entry `KOP2-strand-rustevo2-phaseB` requires `quiet_window` + `max_uptime_days: 7` + `cache_state: warm`; single-instance sequential canonical bench with no screening variant | Dry-run `eval_models_rq1.py` against a mock endpoint; re-point the entry's `kernel_era: v6` / `topology df373c79cc4af06f` (§3); pre-create `/workspace/tmp/rustevo/RustEvo/results/`; pre-format the ledger row and gate-table fork | Phase A ✅ (GGUF on disk, toolchain + venv installed, harness validated 06-18); `OP-STRAND-INFERENCE-APPROVAL` ungranted |
| A18 | **RE-4 LongCoT-Mini chain** (RE-4.2 probe → 4.3 full → 4.4 ladder → 4.5 package), plus its duplicates **K-LCM-1** and **RE-4** | `re4-protocol-redesign.md`; dups in `bulk-inference-campaign.md`, `backlog-roi-audit-2026-07-14.md` | Entry `RE-4-longcot-mini-calibration` requires `quiet_window` + 7 d; row text names "operator quiet-window … autopilot stopped" | Re-attest the topology hash into the entry (the handoff header says to); regenerate + pin the 30-row stratified probe manifest (8/8/7/7 chem/chess/cs/math by sorted id); `--dry-run` `longcot_mini_stack_runner.py`; pre-write the `DONE_PASS` / `DONE_MARGINAL_OBS` ledger stubs. **Collapse the three duplicate surfaces to one** | RE-4.0 ✅ runner v2 (research `9323213d`); RE-4.1 ✅ entry v2 applied; dataset on disk; ledger `BLOCKED_PRECONDITION` |
| A19 | **MindDR Phase-2 gfx90a training-viability smoke** (**OP-4**) | `minddr-deep-research-mode.md` | *"Countermanded until E5 Stage-B releases the host"* — a Python ROCm trainer is invisible to E5's process/SMT-affinity gates and would silently contaminate its decision-grade cells | **Provision the pinned gfx90a training env** (`torch`/`transformers`/`accelerate`/`trl`/`peft`/`datasets` are absent from both uv envs) — pure provisioning, no host quiet needed, and it is the stated blocker | Unstaged. Cascades to `frontier-f3-data-flywheel.md`, `engram-conditional-memory.md`, the EV-9 judge model |
| A20 | **OpenMLE Sandbox reproduction** | `architect-model-selection-bench.md` | **A different reboot** — cgroup v1 via a GRUB kernel-cmdline edit | **Do NOT bundle into the OP-16 reboot.** Gate (1) is network-only and "any main": pull the worker/controller images and prove they run. Then draft the cgroup-v1 decision package (GRUB stanza diff + rollback + what depends on cgroup v2). Note `autokernel-research-loop.md:670` already declines a cgroup-v1 reboot as outside the adopted design | Trigger fired 08-11; gates ordered 1→2→3 |

### 5.2 Category B — the run works today, only the claim waits

Full list in §6. Cluster heads:

| # | Cluster | Owning handoff | Needs the reboot FOR | Pre-reboot staging |
|---|---|---|---|---|
| B1 | **E5 NUMA×batch / placement re-measurement** — `RE-MEASURE E5 Stage-B on the corrected placement` (live), `E5 W1-W4 runs`, `E5 — NUMA×batch interaction sweep`, plus `T3` (`numa-placement-defect-20260730.md`) and `P2-1` (`numa-topology-cutover-resume-20260730.md`) — **one physical run, five rows** | `batched-decode-measurement.md` (+2) | Decision-grade label only; the row forbids the override in its own text. Also needs an exclusive window: `host_health_warnings()` counts `existing_llama_processes` **unfiltered**, enforced at run start *and* per cell, so a stack bringup mid-window kills the remainder | **Regenerate the corrected grid** per the row's binding requirements: (a) add full-machine `0-95` + `numactl --interleave=all` as a swept shape for `qwen36_q8_0` and `qwen3_next_80b` — today's winner existed in the old grid only as gemma's C1; (b) every straddling cell carries `--interleave` or is a declared defect-replication control; (c) `drop_caches` before every cell + record `pages_by_node`; (d) attest numactl policy per instance, fail closed on disagreement; (e) harness unchanged. Then re-verify readiness (§6.1) |
| B2 | **GPU shed-trade** — `P2-5c` (RUN the P2-5a measurement), `P2-5j` + its decision-bearing successor, `P2-5g` | `gpu-serving-tie-in-program.md` | P2-5c gate G2 is verbatim the uptime tier; P2-5g's deliverable is a decision-grade contention pair feeding `contention_matrix.yaml` | Design already committed (`docs/design/p2-5a-shed-trade-measurement-spec.md`, research `d5f5942f`; corpus re-frozen `5e7a1564`). Pre-register arms; design the saturation-knee calibration sweep; author the `contention_matrix.yaml` per-pair entry shape; **P2-5j must precede any q3 carve** — MI210 is on NUMA **node 1**, so today's 184-191 placement is already cross-node and the node-local candidates were never tried |
| B3 | **Eval-tower model-gated cluster** — EV-5 ThinkPRM (4 rows), EV-7 Ouro T0, EV-8 diversity baseline, EV-10a skill efficacy, EV-13b review-F1 | `eval-tower-verification.md` | All five entries carry `quiet_window` + 7 d | **Highest-yield staging in the whole sweep** and 100 % non-inference: HF-pull ThinkPRM-1.5B → `convert_hf_to_gguf.py` → `llama-quantize` Q4_K_M; land the `orchestrator_stack.py` sequential-load config; implement `eval_t2()`; place Ouro-2.6B weights; freeze+pin EV-8's 20 prompts/role × 4 completions with seeds; assemble EV-13b's Augment-v1 145-bug golden set + semantic matcher and **author its batch entry** (it has none) |
| B4 | **Reviewer quality-axis rows** — RC-8, TM-8, RM-2/3/5/6/7/8/10, GC-1a/2a/3a, H-Q1 | `reviewer-calibration-accounting.md`, `reviewer-trace-materialization.md`, `reviewer-model-ablations.md`, `glm52-reviewer-capability-gates.md` | FA/FR/CR/coverage are quality metrics — throttle-insensitive. The **binding** gate for most is RC-6a's `MEASUREMENT.md` amendment, not uptime | **Build TM-8's per-worker flag-introspection probe first** — the known 1-of-6 uvicorn propagation hazard silently corrupts TM-8 coverage, so the guard must exist *before* the window. Freeze the K-of-M protocol and corpus slice; author RM-5's 6 bias injections and RM-10's 3 prompt arms (100 % offline). Honour GC-1a's prohibition: do **not** rerun unchanged `multi_oracle`/binary-schema/answer-fragment slices without a new repair hypothesis. Stage the H-Q1 UD-IQ3_XXS download (~300-340 GB, not present) |
| B5 | **Claim-grade singles** — DeepSeek-V4-Flash Phase 1 Q8 baseline (+3 sub-rows), P6 decision-grade confirmations, SWE `2b-confirm`, Gate-R `G3`, `I4` 33-flip re-run, 79-question judge suite on 27B | `deepseek-v4-flash-0731-dspark.md`, `inference-batch-loop.md`, `scoring-infra-standardization.md`, `fable5-window2-findings-03…md`, `autopilot-continuous-optimization.md` | Each deliverable is named claim-grade / decision-grade | DeepSeek models are **on disk and checksummed** — run the screening pass now so the post-reboot claim is a confirmation not a discovery. Do SWE's gold-validation docker work now (non-inference) and pre-configure the scorer over the FULL slice (empty patches are absent from the report's lists and silently shrink the pairing). Do `G2` HIP build + op-coverage smoke — explicitly *"no window needed"* — and `G1` P-GPU-1 ratification, both of which clear G3's path; **repair `n5_frontdoor_drafter_retest.sh`, which pins a dead v5-only commit and must not run as-is**. Pin I4's 33 flip items to a manifest |
| B6 | **Determinism / routing / placement** — D3 canonical bench + D4 era row, RI-10 canary (+RI-11/12), DCP-6, SS-BENCH-GATE-b, WP-9/WP-10, WP-6/WP-7 + ≥8-pair vision_escalation, Bridge residual 2, `real_suite_v1` discriminability, Q4, BEP-2/J8, W3 applicator, live-pool oracle | `prompt-construction-determinism.md`, `routing-intelligence.md`, `bep-dcp-falsification-harness.md`, `standardized-stack-update-pipeline-finalization.md`, `within-role-placement-state-machine.md`, `shape-keyed-contention-gating.md`, `loops-and-dashboards-audit-2026-07-05.md`, `contention-model-device-and-load-axes-rider.md`, `batched-edit-parallel-apply.md`, `capability-registry-and-promotion.md`, `autopilot-continuous-optimization.md` | Mixed: canonical certification (D3), env-only-at-restart (RI-10's `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED`, DCP-6's `AUTOPILOT_TOOL_SENTINELS`), instrument-boundary (pool rebuild), topology re-pin (WP-9/10) | **Stage every launch-env flag into the post-reboot bring-up so the canary window starts at t=0 instead of costing a second restart.** Land SS-BENCH-GATE-b's cpusets **before** the reboot so they are live from the first launch — the incident it prevents is a reload sidecar invalidating a decision-gating run 1h09m in, i.e. exactly how the first clean window gets wasted. Implement `shapekeyed_step2_smoke.py:718`'s `NotImplementedError` stub. Root-cause `real_suite_v1`'s 0/50-vs-35/50 flip offline by deterministic replay. **WP-9/WP-10 needs no reboot** (its own prep doc says so) but its recert bench must not run at 13 d uptime or it bakes throttle hysteresis into a durable topology pin that ~52 sites reference |

### 5.3 Category C — misfiled, or already satisfied

**These inflate the gated queue and should be corrected, not dispatched.** The highest-value ones:

| Item | Owning handoff | Evidence it is not gated |
|---|---|---|
| **EV-4, EV-4b, EV-11c** (3 rows + 2 dependents, + `RE-1` duplicate) | `eval-tower-verification.md`, `backlog-roi-audit-2026-07-14.md` | Ledger is terminal **`DONE_PASS` 2026-07-23** with `decision_grade=True` on both arms; EV-4 explicitly *supersedes* EV-4b. **Stale-open checkboxes — flip, do not dispatch.** |
| **P1-1, P1-2, P1-3, P2-5f, P2-5i, P2-9** | `gpu-serving-tie-in-program.md` | Every reboot clause names the **07-29** reboot, which executed. Real gate is the E8 signature (P0-1). P1-2's own 08-11 annotation records Stage-B COMPLETE. P2-5i is a standing prohibition carrying `do not flip this box`. P2-9 mentions a reboot only as a download-hazard warning |
| **RC-6a + its two amendment candidates**, **LB-6b**, **LB-6**, **LB-3**, **LB-8** | `reviewer-calibration-accounting.md`, `reviewer-latency-and-sampling-budget.md` | RC-6a is a **human PR against `MEASUREMENT.md`** with blocks already copy-paste-ready and a 4-step checklist. It gates every decision-grade reviewer claim. LB-6b is an operator threshold pick from three drafted candidates. **Both are free wins during the reboot wait** |
| **`gpqa_diamond_cot` full n=198** | `architect-model-selection-bench.md` | GPU accuracy is device-independent and the sibling MMLU-Pro control ran **2026-08-12** at this uptime with released claims. Pinned manifest exists; A1/A3 run dirs exist. **Only the A4 arm is missing — dispatchable today** |
| **Eval-tower A2 / C2 / E5 hardening** | `eval-tower-architecture-audit-2026-07-20.md` | Gate is mechanical and not uptime: *"`pgrep -f evaltower_window` returns nothing (and `:8000` idle)"*. Run the pgrep before assuming blocked |
| **`llamacpp-v6-consolidation.md` "Post-reboot NUMA topology bench (the NEXT gate)"** | same | Dead prose with **no open checkbox**; the file's own line 391 records **"Reboot-necessity verdict: NO REBOOT NEEDED"**; v6 is three eras superseded. Its 3 open rows are upstream-parity items with no host gate |
| **NPS / BIOS / NUMA-topology reboots** | `handoffs/completed/nps-reboot-runbook.md`, `orchestrator-nps4-48x4-notes.md` | **The whole category is empty.** The runbook is closed — *"Reopen triggers: none"*, L3aaN is do-not-re-propose. `orchestrator-nps4-48x4-notes.md` has **zero open checkboxes**. There is no live BIOS/boot-setting item |
| **R1a — end-to-end bench claim** | `session-bus-thin-dispatcher.md` | Needs one short smoke (`-n 128 -r 1`, small model) under a *held claim*, not a signature (R2 ✅). **The stack is fully down, so this is the cheapest it will ever be — do it BEFORE the reboot**, since it de-risks every decision-grade bench in the first clean window (A0 is currently only structurally verified) |
| **AP-3 / AP-3b**, **AP-WM-1**, **autopilot-pause interlock**, **worktree isolation phase 2** | `autopilot-control-plane-integration.md`, `autopilot-continuous-optimization.md`, `session-bus-thin-dispatcher.md` | "Restart-scoped" means *llama-server role reload*, not host reboot. AP-WM-1 matched a `decision-grade` keyword only because it **disclaims** it. The pause interlock is a code fix — but fix it **before** AutoPilot resumes, it caused a live outage 08-03 |
| **RM-9** | `reviewer-model-ablations.md` | Its precondition is **falsified** — A4 failed admission (FA 41.7 %, FR 25.0 %, AUC 0.509). Close as a decline, do not carry as gated |
| **GC-4** | `glm52-reviewer-capability-gates.md` | Operator decision, and it **collides with OP-8** (GLM-5.2 GO/WAIT/KILL, 222 GB). May be moot if OP-8 lands KILL — escalate the pairing |
| **`ROUTE-A1` / `ROUTE-A2`** | (batch ledger) | Blocked by a `NotImplementedError` stub (`shapekeyed_step2_smoke.py:718`) and a missing corpus manifest. A reboot fixes neither; both will resurface as false post-reboot candidates |
| **`reviewer-typed-artifacts.md` (4 rows) + `security-review-skill.md` (6 rows)** | those files | Zero host dependency, same intake source. **10 boxes, cleanest none-lane block available**, and the negative-control axis is a prerequisite for ever measuring a false-accept rate — which every A12 row depends on |
| **`cpu-shape-specialized-gemv-decode.md`, `sarathi-serve-cpu-evaluation.md`, `gpu-drafter-mi200-investigation.md`** | those files | Say so explicitly: *"Does NOT require BIOS reboot or env var"* · *"Independent of L3aaN reboot"* · the clean-window retest is already `- [x]` decision-grade ✅ 2026-07-16 |

**Also stale, and it matters:** `document-parser-table-bench.md` and `opendataloader-pipeline-integration.md` each carry **standing constraints wearing checkboxes** (`Do not download MinerU2.5-Pro…✅`, `NAME COLLISION — do not resolve by path`, `Route … away from LiteParse`). Same defect class the auditor escalated as `backlog-queue-template-rows`. Do not dispatch, do not flip.

---

## 6. Run now at screening tier — do not leave these waiting

The reboot changes a *label*, not a *number*, for everything in Category B. Running them now costs
nothing and converts the post-reboot pass from discovery into confirmation. Label the tier honestly in
the manifest (`decision_grade: false`) and say "quiesced host" in anything published — AutoPilot is
down, so these numbers are not silently representative of production.

**Highest value first:**

1. **DeepSeek-V4-Flash Phase 1** — models on disk and checksummed; the file already banked a
   self-described *"single dirty-host repetition"*, so the screening path is proven.
2. **RC-8 baseline** (`reviewer-calibration-accounting.md`) — the entry states plainly that *"the
   observation-grade run itself does not block on"* OP-5a. Corpus v1 already built
   (`nearmiss-v1`, 11,516 rows, `content_sha256 1c50c025…`).
3. **DCP-6 eval half** — `dcp_j7_ab.py` *"requires `--host-quiet-confirmed` and refuses if AutoPilot is
   running"*. **AutoPilot is down, so it will not refuse today.** Last artifact: `decision.status=hold`.
4. **RM-3 screening tier** — literally the screening tier; all four children ✅. Only the *promotion
   rule* to confirmation tier needs post-reboot cost numbers.
5. **D3 canonical bench, screening pass** — establishes effect direction at zero claim risk, then the
   post-reboot run only has to confirm it.
6. **RLM E1 / E3 / E3b** — the handoff already grades its n=20 numbers as observations; a screening pass
   de-risks the harness.
7. **ERNIE content-filter audit** — harness ready (`ed6f65f5`), 10 cases across 5 categories authored,
   qualitative deliverable, throttle-insensitive.
8. **AP-WM-1 offline archive comparison**, **`gpqa_diamond_cot` A4 arm**, **MD-9 sentinel A/B**, **TM-8
   coverage** (after its introspection probe lands), **document-parser Phase B binary `<table>` gate**.
9. **The seven `max_uptime_days: 14` entries** in `30-bulk-campaign.yaml` — eligible until **~13:37Z
   today** and then not again until the reboot. They still fail the topology pin (§3), so this is only
   reachable if S-01 lands first. Report the outcome either way.

---

## 7. Capture before the reboot — restart destroys these

**What survives:** `/workspace`, `/mnt/raid0/llm/**` (incl. `/mnt/raid0/llm/tmp`, 41 GB) and the
agent-memory dir are all `/dev/md127`, one persistent RAID. The 2026-08-11 fleet-wide claim that
*"uncommitted work does not survive a reboot"* was **false and was retracted** (F-21,
`coordinator-role-failure-modes-and-refactor.md`). The real hazard to untracked work is `git clean
-ffdx`, not the power button.

**What does not:** `/tmp` is the **container overlay**, a different filesystem (22 GB, includes the
agent scratchpads). It survives a container *restart* but not a container *recreate* — and
`.devcontainer/Dockerfile` is currently modified in the working tree.

| # | Artifact | Why it dies / why it matters | Where |
|---|---|---|---|
| C-1 | **`tmux list-windows -t agent`** — window names ↔ roster ids | The only record of the live roster shape; C25's endpoint/window mismatch was hand-fixed with `tmux rename-window` last time and *"nobody will remember next reboot"*. Currently: `0 coordinator · 1 htop · 2 btop · 3 inference · 4 auditor · 5 mainA · 6 mainB · 7 mainC · 8 mainD · 9 fish` (session created 2026-08-01 05:46) | kernel state |
| C-2 | **Daemon epoch + pid + heartbeat**, plus supervisor/hub/fleet_watch pids | C26's guard refuses a live state when heartbeat `age` exceeds **system uptime** — only meaningful if the pre-reboot epoch is known. Live now: daemon 1728027 (11:28:48), supervisor 359336 (11:02:43), hub :8100 1367133 (11:19:37), fleet_watch 1448583 (11:20:37) | `heartbeats/coordinator-daemon.json` + `ps` |
| C-3 | **`/proc/<uvicorn>/environ`** and **`/proc/3903691/environ`** | WP-10's entire safety argument rests on `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` having been *read from a live process*; that verification dies with the process. PID 3903691 is the pytest-escaped API carrying `PYTEST_CURRENT_TEST` — the surviving evidence for INC-20260806-pytest-api-escape | `/proc` |
| C-4 | **NUMA page placement (`pages_by_node`) of every resident instance, and the warm production-wiring datapoint** | `--interleave` binds at **first touch only**, so it is a silent no-op on a warm cache. The defective placement (`{N0: 9226101} / 9226101`, all 35.2 GiB on node0 under a node0+node1 team) and the warm **7.81 ± 3.82 t/s** frontdoor figure are the AutoPilot operating point B1 is re-anchoring against | `/proc/<pid>/numa_maps` |
| C-5 | **Page cache = 1046 GB warm.** Not a loss to prevent — a state to *declare* | The reboot drops it. That is the point (cold-cache opportunity) and the cost (every model load is cold). Post-boot the first re-read **pins one node** — the NUMA-interleave re-warm discipline must be in the boot runbook, never a bare re-read | measured |
| C-6 | **Current CPU frequency profile** | min 1998 / avg 2412 / **max 4552 MHz** at load 12.0, no throttle. Capture it so a post-reboot delta can prove (or disprove) accumulated throttle rather than assuming it | `/proc/cpuinfo` |
| C-7 | **Era-fenced ledger accrual — the highest-risk loss in the sweep** | Fence `1785004723.0` retains **16 trusted rows / 2 eligible items against a 40-item target** (shortfall 38) after excluding 1,317 pre-era rows. **If the reboot moves the kernel/topology era, this resets to zero again.** Snapshot the ledger, the fence value and the row counts, and decide *deliberately* whether the reboot opens a new era | `fable5-window2-findings-01/03` |
| C-8 | **AutoPilot journal: duty-cycle + production-traffic history** | Needed for the P2-2 anchors (3 of 4 roles have none; `frontdoor` = median 35.7 t/s, n=154) and for P2-5f. AutoPilot has been down since `2026-07-27T08:23:07Z`; a restart resets the accumulation clock again. **Harvest what exists now** | `orchestration/` journal shards |
| C-9 | **`logs/llama-server-*.log`** | Open row: *"UNEXPLAINED: every llama-server exited at ~07:00 on 2026-08-04"* — ends with an explicit instruction: **"If it recurs, capture `logs/llama-server-*.log` BEFORE restarting."** | `epyc-orchestrator/logs/` |
| C-10 | **`autopilot.log` and the `tool_chains` rows** | A previous rotation already destroyed the historical REPL evidence (*"0 parseable historical REPL sessions"*). Archive before it happens again | `epyc-orchestrator/` |
| C-11 | **In-flight session journals feeding P4c** | `next_turn_followup_command` is populated by reading the *next* bash command in the same session journal; a reboot ends every session, so unpaired rows are lost and the "1 week of data" restarts | `logs/tool_compression_monitor.jsonl` + journals |
| C-12 | **M3 / M4 soak clocks** | M4 is a 48 h zero-idle acceptance; a reboot resets it, slipping the `triage` and `headless-worker` grants another two days | `token-queue.md` standing gates |
| C-13 | **Pre-restart daemon tick cost** (~8.9 s, ~6.6 GiB transient dicts per 45 s tick, 29.5 % of a core) | The before-half of A6's A/B; unreproducible after the restart | measured |
| C-14 | **`/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json`** (`2026-08-11T08:19:56Z`, `selected_servers: None`) | The stack-down control for A7's comparison; overwritten at the next reload | RAID (safe, but will be overwritten) |
| C-15 | **Suspect anchors of unknown host provenance**, each labelled pre-reboot | Hermes *"much lower than raw 39 t/s"*; ColBERT's **180 ms** GTE baseline; PaddleOCR's `2918.78` / `3245.60` ms median page latencies; LB-1's 07-16 regression anchor (~68 backend requests + 11-17 plan-review prompts per 50-question replay). Capture them so the post-reboot delta separates *design problem* from *13-day-uptime problem* | various |
| C-16 | **Region-lock flocks and the sealed `advisory*.jsonl` shard** | flocks are kernel state and vanish. C38 archives sealed shards to `EPYC_BUS_ARCHIVE_ROOT` (default `/mnt/raid0/llm/bus-archive/advisory`, outside the repo where `git clean -x` cannot reach). Confirm the current shard is sealed and archived | bus |
| C-17 | **The accepted v9 control bundle and journal** — `ak-controls-v9-a4cb04ca-20260812-r2`, AutoPilot exact-stop at trial `1458`, the three-point speed frontier, and the Kernel-R&D surface state (frozen v9, 8/8 preflight, 5/5 controls, GPU `NOT_REPRODUCED`) | `CURRENT-CAMPAIGN.md` mandates preservation explicitly | RAID |

---

## 8. Post-reboot first hour — the order these rows imply

Not a proposal; this is the ordering the open rows already require, collected in one place.

1. **`tmux new-session -d -s agent`** — C20. Nothing in the code does this; every spawn refuses until
   it exists.
2. **Re-apply the host tunables** — `sysctl -w kernel.numa_balancing=0`, `perf_event_paranoid=1`,
   governor `performance`. **Verify with `health_check.sh` before anything measures.** Skipping this
   swaps the uptime warning for a `numa_balancing` warning and wastes the fresh window (§4).
3. **Restart the supervision tier** in order: coordinator-daemon (picks up C28/C38 for free) →
   `bus_supervisor.sh` → `hub_supervisor.sh` → `fleet_watch.sh`. Verify each with `ps -p <pid>`, never
   with `status` — the state file outlives the process that wrote it.
4. **Respawn the roster onto the EXISTING ids.** A fresh alias orphans that identity's cursor, outbox
   and triage `corr_id`s. Expect C40's staleness banner on the relayed backlog — last time 703 messages
   landed in one burst and two mains burned tokens on 12-day-old work.
5. **Launch the stack with the staged env**: `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED=true` (RI-10),
   `AUTOPILOT_TOOL_SENTINELS` (DCP-6), SS-BENCH-GATE-b cpusets, `ORCHESTRATOR_SEARXNG_DEFAULT=1`
   (SX-6). Each of these otherwise costs a second restart.
6. **Run the launch verification**: the per-change checklist in
   `model-stack-change-standardization-audit.md` (do-not-flip; it is a procedure, not a backlog row) +
   the `-np` drift diff + the `selected_servers` assertion + `verify_ggml_linkage.sh` for every
   launcher.
7. **Re-derive and re-pin the live topology hash**, then re-run the batch-entry preflights.
8. **Then** the window is genuinely clean. **CPU IQK, D3, and the E5 re-measurement all want the same
   window and are mutually exclusive with any `llama-server` on the host** — co-schedule them
   deliberately; the ordering is `inference`'s call.

---

## 9. Pre-reboot staging tasks

Dispatchable now. None requires a reboot; none runs a benchmark or starts `llama-server`.

- [ ] **S-01 — Re-pin all 25 uptime-capped inference-batch entries to the current era and live topology
      hash.** They pin `kernel_era: production-consolidated-v6/v7` and `required_topology_hash:
      8c8cfcbb13d2611d` / `df373c79cc4af06f`; production is v9 @ `0db32c06` (binary 10125) and
      `contention_matrix.yaml:10` stamps `171f86f9188211e9`. `run_batch_entry.py` compares the topology
      hash fail-closed, so **without this the reboot unblocks nothing in the batch loop.** Files:
      `20-eval-tower.yaml` (8), `30-bulk-campaign.yaml` (10), `40-routing.yaml` (3),
      `50-kernel-op2.yaml` (3), `00-example.yaml` (1). Validate with
      `compile_inference_batch.py validate` (venv interpreter).
- [ ] **S-02 — Re-derive the live topology hash first and record it with its derivation.** Three values
      are in circulation (`8c8cfcbb13d2611d` pinned, `bc28e15d` recorded 07-30, `171f86f9188211e9`
      stamped in the matrix). S-01 cannot be done correctly until one is established as live. Owner:
      whoever owns `numa-topology-cutover-resume-20260730.md`.
- [ ] **S-03 — Write and validate a first-boot host-prep script** (`numa_balancing=0`,
      `perf_event_paranoid=1`, governor `performance`, verify with `health_check.sh`) and put it in the
      post-reboot runbook as step 2. Non-interactive `sudo` is available, so this is not an operator
      step. Optionally propose a persistent `/etc/sysctl.d` entry as a separate host-level operator ask.
- [ ] **S-04 — Refresh the E5 Stage-B readiness verification; it is 14 days stale.** The "45/45
      manifests dry-run clean, all 5 GGUFs present" record is dated **2026-07-29**, and
      `E5_STAGE_B_RUNBOOK.md` still pins `production-consolidated-v8 @ 67a433bf4` in its preflight table
      — that check now fails against v9. GGUF presence re-verified 2026-08-12 (139 manifests → 4 distinct
      paths, all resolve). Update the kernel pin, re-dry-run, and re-record with today's date.
- [ ] **S-05 — Generate the corrected E5 re-measurement grid** per the RE-MEASURE row's five binding
      requirements (full-machine `0-95` + `interleave=all` added for `qwen36_q8_0` and
      `qwen3_next_80b`; explicit `--interleave` or a declared defect-replication control on every
      straddling cell; `drop_caches` + `pages_by_node` per cell; per-instance numactl attestation that
      fails closed on policy/cpuset disagreement; harness unchanged). Dry-run to exit 0.
- [ ] **S-06 — Build the ThinkPRM-1.5B Q4_K_M GGUF and land the EV-5 wiring** (HF pull →
      `convert_hf_to_gguf.py` → `llama-quantize`; `orchestrator_stack.py` sequential-load config;
      `eval_t2()` uncertain-question selection + P(yes) extraction; wire the existing
      `check_cross_family()`). Zero inference; it is the acknowledged blocker on the largest gated
      cluster.
- [ ] **S-07 — Acquire the OmniDocBench source PDFs and mint an immutable manifest.** Unblocks
      `opendataloader-pipeline-integration.md` and `document-parser-table-bench.md` (same work filed
      twice). Record that the real local ceiling is 51 eligible PDFs, not 200.
- [ ] **S-08 — Regenerate the E8 context coverage scan.** `e8_quality_context_coverage_v4_20260727.json`
      reports `required_tokens` in **BYTES** and was taken against the pre-07-30 fleet. Both the A–D
      options package and the two 19 MB replacement-map candidates inherit both errors — nobody should
      act on them as they stand. Re-tokenize today; this directly unblocks A11's operator decision.
- [ ] **S-09 — Delete the five `.staging-` bundles** left by the 2026-07-26→29 E8 `--execute` attempts.
      The runner forbids reuse, so the post-reboot run fails on residue. (Coordinate with the row's
      owner before deleting; this is their lane.)
- [ ] **S-10 — Land SS-BENCH-GATE-b's cpuset pinning in the launch path before the reboot** so it is
      live from the first post-reboot launch. It exists to stop a reload sidecar invalidating a
      decision-gating run — which is exactly how the first clean window gets wasted.
- [ ] **S-11 — Close the P-BENCH-1 host-health gap.** `bench_canonical.sh` performs no uptime or
      host-health check, so the canonical CPU path can silently mint a policy-non-compliant
      decision-grade number while the P-BENCH-3 path fails closed. Either add the gate or make the
      attestation mandatory in the emitted artifact. Route to the measurement-protocol owner — the
      trust boundary is human-amendment-only, so propose, do not amend.
- [ ] **S-12 — File OP-16 as a pre-validated token block in `tokens/token-queue.md`.** It currently
      exists only as a master-index row, so the one signature the whole Category-A list waits on is
      absent from the queue the operator reads. Include the earlyoom `--ignore` line (A8) and the OP-9
      cron ruling (A5) so they ride the same authorization.
- [ ] **S-13 — Correct the "OP-16 was declined by the operator" claim** in
      `session-bus-thin-dispatcher.md`'s worktree-isolation row. No such decision exists; OP-16 is open
      and deferred-with-announcement. The row's conclusion stands; its justification does not. (Owner:
      `mainD`, C-OWN — route, do not edit.)
- [ ] **S-14 — Execute the capture list in §7 into a dated snapshot directory** under
      `/mnt/raid0/llm/tmp/pre-reboot-<UTC>/` (persistent array), and reference it from
      `tasks/post-reboot-session.md`. Pattern to reuse:
      `epyc-inference-research/scripts/benchmark/op2_quiet_window_prep.py`, which already creates a run
      dir, records host/repo/process state, stamps a stage plan and writes `operator_next_commands.sh`
      **without starting inference**.
- [ ] **S-15 — Write the post-reboot runbook (§8) into
      `coordination/session-bus/tasks/post-reboot-session.md`** with the roster respawn command list and
      the endpoint→window-name mapping verified against `config.yaml` beforehand. That file is currently
      the *coordinator handover brief*, not a reboot runbook; add the runbook as its Phase-0a section
      rather than overwriting it. (Owner: coordinator-agent — route.)
- [ ] **S-16 — Run the Category-C corrections**: flip EV-4 / EV-4b / EV-11c (terminal `DONE_PASS`);
      close RM-9 as a decline (its precondition is falsified); run `pgrep -f evaltower_window` and
      release the eval-tower hardening rows if it is empty; dispatch the `gpqa_diamond_cot` A4 arm;
      collapse the three duplicate RE-4 / K-LCM-1 surfaces to one. Route each to its owning index rather
      than flipping another agent's boxes.
- [ ] **S-17 — Close R1a before the reboot, not after.** One short `-n 128 -r 1` smoke on a small model
      under a *held* region claim proves a real `llama-bench` acquires, holds and releases it. The stack
      is fully down, so this is the cheapest it will ever be, and it de-risks every decision-grade bench
      in the first clean window. **Inference lane — route to `inference`, do not self-dispatch.**
- [ ] **S-18 — Put the two free operator decisions in front of the operator during the wait**: RC-6a
      (the `MEASUREMENT.md` P-REV-1 PR — blocks are copy-paste-ready, and it gates the entire
      decision-grade reviewer tier) and LB-6b (pick one of three drafted thresholds). Land RC-6a's two
      kappa/estimand amendment candidates first — the row says so.
- [ ] **S-19 — Re-issue OP-6 before it is approved.** It names *"the v8 reference lineup"* while
      production is v9, and its executable manifest (`00-rcp-prologue.yaml`) is a further era behind at
      v7 with a stale topology pin. Approving it as written buys a v7/v8-stamped, throttle-contaminated
      window.
- [ ] **S-20 — Provision the pinned gfx90a training environment** (`torch`/`transformers`/`accelerate`/
      `trl`/`peft`/`datasets`, absent from both uv envs). Pure provisioning, no host quiet needed, and it
      is the stated blocker on OP-4 — which cascades to `frontier-f3-data-flywheel.md`,
      `engram-conditional-memory.md`, `minddr-deep-research-mode.md` and the EV-9 judge model.

---

## Cross-references

`autokernel-research-loop.md` §AK6.5 (OP-16) · `batched-decode-measurement.md` (E5) ·
`gpu-serving-tie-in-program.md` (P2-5 series) · `session-bus-thin-dispatcher.md` (C20, supervision) ·
`eval-tower-verification.md` (EV-5/7/8/10a/13b) · `CURRENT-CAMPAIGN.md` (live posture) ·
`coordination/inference-batch/entries/` (the 25 gated entries) ·
`measurement/protocols/bench-cpu.md` + `kernel-research.md` (the ratified ceiling).

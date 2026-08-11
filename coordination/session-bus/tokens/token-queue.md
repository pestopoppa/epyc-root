# Operator token queue

Clone of the op-bundle grant pattern. **Agents author blocks in their outbox as `token-request`
messages; the coordinator-daemon relays them here verbatim; the coordinator-agent presents them;
the operator flips `[ ]` → `[x] GRANTED <date>`.** Nobody but the operator touches a checkbox.

**Pre-validation is mandatory.** Every block carries the exact command plus dry-run evidence. An
operator-presented command that fails is a **defect row attributed to the requesting agent**, not
an operator problem.

**Presentation is saturation-gated.** The coordinator-agent surfaces pending tokens only while the
saturation snapshot shows lanes busy — *except* when a gate is the sole cause of imminent lane
idleness, which forces immediate presentation. A pending token never gates unrelated work
(`BUS_PROTOCOL.md` rule 2).

**Consolidated unblock (R8).** These blocks are batched into ONE artifact so the operator runs a
single command on return: pinned HEAD + file `sha256`s, refuse on drift, idempotent, per-line
independently validated so striking one line cannot invalidate the rest. A failed validation
repairs and re-presents the **same** token — never a new chain. A struck line's task returns to
`HELD_OP_GATE`: held, not dropped, not silently requeued.

---

## Standing gates (default OFF — grant individually)

- [x] **OP-SENDKEYS-CODEX** GRANTED 2026-07-27 — allow the coordinator-daemon to nudge a main via
  `tmux send-keys`, and to spawn a main as a **window in the one live session**
  (`tmux.live_session`) — never its own session. Rate-limited per agent
  (`--min-interval-s`, default 600s) and capped per day by `caps.max_spawns_per_day`; both values
  live in `config.yaml` rather than here, so this block cannot go stale against them.
  *Granted to authorise the BUILD*: `scripts/coordination/tmux_adapter.py` did not exist at grant
  time, and `capability_status()` reported `NOT IMPLEMENTED` regardless of the flag until it did —
  a flag can never make an absent adapter look present. The original "evidence required: the nudge
  ladder demonstrably exhausted" condition was therefore **not** the basis for this grant, and is
  recorded as superseded rather than quietly dropped.
- [ ] **triage: on** — enable the M5 one-shot triage hook (dead-agent block drafting + routing
  annotations). Operator flag after the M4 soak; budget-capped by `caps.triage_calls_per_day`.
- [ ] **headless-worker caps > 0** — only after M4 acceptance.

## Pending token requests

_(none — the coordinator-daemon appends relayed blocks below this line)_

### DAEMON-ESCALATION msg-20260729T153408Z-296-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T153408Z-296-coordinator-daemon` (`defect`) from `mainB`
- task: `e5-stage-b-protection-blind-spot`
- detail: defect

### DAEMON-ESCALATION msg-20260729T155517Z-305-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T155517Z-305-coordinator-daemon` (`decision-request`) from `auditor`
- task: `c-own-round-3`
- detail: 64-percent-of-outbox-rows-are-un-relayable

### DAEMON-ESCALATION msg-20260729T160627Z-314-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T160627Z-314-coordinator-daemon` (`defect`) from `auditor`
- task: `backlog-queue-template-rows`
- detail: two-dispatch-queue-rows-are-RUNBOOK-TEMPLATE-steps-do-not-flip

### DAEMON-ESCALATION msg-20260729T160825Z-319-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T160825Z-319-coordinator-daemon` (`defect`) from `auditor`
- task: `backlog-claim-race`
- detail: two-mains-implemented-the-same-backlog-row-today

### DAEMON-ESCALATION msg-20260729T170857Z-419-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T170857Z-419-coordinator-daemon` (`defect`) from `auditor`
- task: `backlog-queue-template-rows`
- detail: the-predicted-runbook-corruption-HAS-ALREADY-HAPPENED-and-I-under-reported-the-scope

### DAEMON-ESCALATION msg-20260729T171918Z-454-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T171918Z-454-coordinator-daemon` (`defect`) from `auditor`
- task: `backlog-queue-template-rows`
- detail: THE-TELL-IS-THE-BOX-TEXT-NOT-THE-HEADING-my-two-earlier-scans-were-both-structurally-wrong

### DAEMON-ESCALATION msg-20260729T182935Z-688-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T182935Z-688-coordinator-daemon` (`defect`) from `mainA`
- task: `bus-ack-silent-noop`
- detail: my bus acks silently no-opped for two turns; the cause is the SHELL, not the bus

### DAEMON-ESCALATION msg-20260729T191059Z-771-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T191059Z-771-coordinator-daemon` (`defect`) from `inference`
- task: `shared-index-commit-collision`
- detail: defect

### DAEMON-ESCALATION msg-20260729T192528Z-786-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T192528Z-786-coordinator-daemon` (`finding`) from `inference`
- task: `ID-7-ordered-subsequence-scorer`
- detail: finding

### DAEMON-ESCALATION msg-20260729T193409Z-799-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T193409Z-799-coordinator-daemon` (`defect`) from `mainD`
- task: `rao-redel-conditional-depth-surface`
- detail: defect

### DAEMON-ESCALATION msg-20260729T194139Z-808-coordinator-daemon

**Daemon escalation — not a gate, no checkbox.** An operator-decision item has sat unread in `coordinator-agent`'s inbox for 1.5h, past the bypass deadline. The coordinator is in the loop for judgement; it must not be a single point of failure for transporting *a human signature is needed*.

- message: `msg-20260729T194139Z-808-coordinator-daemon` (`finding`) from `inference`
- task: `scoring-infra-canonical-consumer-migration`
- detail: finding

### RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729

- [ ] **RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729** — requested by `inference` for task `p0-2-fg4b-affinity-ratification`
  - block ref: `handoffs/active/gpu-serving-tie-in-program.md#P0-2`
  - command (pre-validated, dry-run exit `0`):
    ```
    bash /mnt/raid0/llm/epyc-root/artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729.sh --attest RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729
    ```
  - dry-run evidence: Canonical-root --validate-only returned preflight-valid. It supersedes the prior P-BENCH-4 receipt with the all-thread request-boundary affinity witness; it starts no inference and changes no lineup/registry/result.

### RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729

- [ ] **RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729** — requested by `inference` for task `e8-final-c1-capacityfix`
  - block ref: `handoffs/active/gpu-serving-tie-in-program.md#P0-1`
  - command (pre-validated, dry-run exit `0`):
    ```
    bash /mnt/raid0/llm/epyc-root/artifacts/operator/ratify_e8_final_c1_retry_capacityfix_20260729.sh --attest RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729
    ```
  - dry-run evidence: Root main 300ed404. Fable-auditor SOUND. 56 focused ratifier+session-bus tests passed; bash -n and shellcheck clean; canonical --validate-only passed. Scope is only ordinals 97 then 279, c1, unchanged 300s, q3, no auto-retry/timeout increase; ratifier starts no inference and changes no state/lineup.

### RATIFY-E9-ROUTING-REWARD-ERA-20260729

- [ ] **RATIFY-E9-ROUTING-REWARD-ERA-20260729** — requested by `mainB` for task `decision-aware-routing--613-instrument-era`
  - block ref: `handoffs/active/decision-aware-routing.md:613`
  - command (pre-validated, dry-run exit `0`):
    ```
    cd /mnt/raid0/llm/epyc-orchestrator && python3 -c "from pathlib import Path; import hashlib, yaml; p=Path('orchestration/instrument_eras.yaml'); t=p.read_text(encoding='utf-8'); assert hashlib.sha256(t.encode()).hexdigest()=='6aedacadc891bc58ff05971e8a1f949741ecbd99d6ebbe9965b7d3d7ba8709cc'; m='\nknown_dead_instrument_items:'; r='\n  - id: E9-routing-reward\n    from: \"2026-07-21T15:27:04Z\"\n    scope: routing_reward\n    note: >\n      Reward saturation repair boundary. epyc-orchestrator 6344fbdb58497edd5b92a1f2f2c81ee504e1383f\n      changed q_reward role resolution from the absent role field to\n      producer_role then final_answer_role; replay of 20,526 historical completions changed\n      reward entropy from 0.0000 to 2.4580 bits. RECONCILIATION: stored pre-boundary q_value and\n      reward values are demote-to-prior for policy training or pre/post reward comparison; use\n      deterministic replay under the repaired scorer or data collected at/after this boundary.\n'; assert t.count(m)==1 and 'id: E9-routing-reward' not in t; c=t.replace(m,r+m); d=yaml.safe_load(c); assert d['eras'][-1]['id']=='E9-routing-reward'; tmp=p.with_suffix('.yaml.tmp'); tmp.write_text(c,encoding='utf-8'); tmp.replace(p)"
    ```
  - dry-run evidence: Copy-only YAML prevalidation passed: source sha256 6aedacadc891bc58ff05971e8a1f949741ecbd99d6ebbe9965b7d3d7ba8709cc; candidate sha256 479040f961853617576cd37b7b1bd94a3e98e58bd9bf142b896140d66e6ca4e4; parsed E9-routing-reward as final eras[] row.

### DAEMON-ESCALATION msg-20260729T151828Z-38-mainA

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainA.jsonl` for 305.5h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T151828Z-38-mainA` (`token-request`) from `mainA`
- task: `e5-era-row-token`
- detail: token-request

### DAEMON-ESCALATION msg-20260729T142122Z-38-coordinator-agent

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/coordinator-agent.jsonl` for 306.4h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T142122Z-38-coordinator-agent` (`defect`) from `coordinator-agent`
- task: `bus-c24-spawn-leaves-stale-heartbeat`
- detail: defect

### DAEMON-ESCALATION msg-20260729T183013Z-70-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 302.3h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T183013Z-70-mainC` (`defect`) from `mainC`
- task: `stack-truth-circular-import`
- detail: defect

### DAEMON-ESCALATION msg-20260729T183555Z-74-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 302.2h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T183555Z-74-mainC` (`defect`) from `mainC`
- task: `model-stack-standardization-validation`
- detail: defect

### DAEMON-ESCALATION msg-20260729T184434Z-84-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 302.1h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T184434Z-84-mainC` (`defect`) from `mainC`
- task: `outer-coordinator-archive-move`
- detail: defect

### DAEMON-ESCALATION msg-20260729T185056Z-88-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 302.0h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T185056Z-88-mainC` (`defect`) from `mainC`
- task: `lightning-attention-LQ-1`
- detail: defect

### DAEMON-ESCALATION msg-20260729T190122Z-94-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.8h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T190122Z-94-mainC` (`defect`) from `mainC`
- task: `commit-ea996350-shared-progress`
- detail: defect

### DAEMON-ESCALATION msg-20260729T190449Z-97-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.7h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T190449Z-97-mainC` (`defect`) from `mainC`
- task: `cf-compaction-termination-telemetry`
- detail: defect

### DAEMON-ESCALATION msg-20260729T190754Z-101-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.7h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T190754Z-101-mainC` (`defect`) from `mainC`
- task: `solvability-plan-executor-divergence`
- detail: defect

### DAEMON-ESCALATION msg-20260729T191132Z-104-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.6h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T191132Z-104-mainC` (`defect`) from `mainC`
- task: `m11a2-work-payload-capture`
- detail: defect

### DAEMON-ESCALATION msg-20260729T191212Z-105-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.6h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T191212Z-105-mainC` (`defect`) from `mainC`
- task: `backlog-ready-row-freshness`
- detail: defect

### DAEMON-ESCALATION msg-20260729T191315Z-106-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.6h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T191315Z-106-mainC` (`defect`) from `mainC`
- task: `conditional-depth-decision-reframe`
- detail: defect

### DAEMON-ESCALATION msg-20260729T191829Z-109-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.5h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T191829Z-109-mainC` (`defect`) from `mainC`
- task: `tide-dormancy-closure`
- detail: defect

### DAEMON-ESCALATION msg-20260729T192136Z-112-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.4h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T192136Z-112-mainC` (`defect`) from `mainC`
- task: `self-audit-post-reboot-claims`
- detail: defect

### DAEMON-ESCALATION msg-20260729T192707Z-117-mainC

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainC.jsonl` for 301.4h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T192707Z-117-mainC` (`defect`) from `mainC`
- task: `ordered-subsequence-verifier`
- detail: defect

### DAEMON-ESCALATION msg-20260729T165830Z-46-mainD

**Daemon escalation — not a gate, no checkbox.** An operator-decision item **never reached `coordinator-agent`'s inbox at all** and shows no sign of having been consumed anywhere. It has sat in `outbox/mainD.jsonl` for 303.8h. This is a DELIVERY failure, not a triage backlog — repairing the coordinator's attention will not clear it.

- message: `msg-20260729T165830Z-46-mainD` (`defect`) from `mainD`
- task: `keep-revert-candidate-contract`
- detail: defect

### RATIFY-CONSOLIDATED-ERA-ROWS-20260811

- [ ] **RATIFY-CONSOLIDATED-ERA-ROWS-20260811** — requested by `auditor` for task `consolidated-era-and-annexg-token`
  - block ref: `artifacts/audit/completion-flurry-wiring-audit-20260811.md#c-1-operator-signature-items`
  - command (pre-validated, dry-run exit `0`):
    ```
    bash /mnt/raid0/llm/epyc-root/artifacts/operator/ratify_consolidated_era_rows_20260811.sh --attest RATIFY-CONSOLIDATED-ERA-ROWS-20260811
    ```
  - dry-run evidence: --validate-only exit 0 (all 4 rows APPLY, per-row sha256 printed, cpu_bench active row after amendment = E9-cpu-kernel; strike variant --skip E8-seeding-reward-b7-guard also exit 0). 59/59 passed: five era-consuming suites (test_instrument_era_guard_eval_quality, test_autopilot_eval_quality_era_fence, test_safety_gate_eval_quality_era, test_dashboard_pareto_eras, test_generate_attestation) against the emitted candidate via AUTOPILOT_INSTRUMENT_ERAS_PATH. Differential probe: ONLY the three intended scopes change (cpu_bench E8-cpu-kernel -> E9-cpu-kernel; routing_reward and seeding_reward appear); autopilot_quality, autopilot_speed, eval_quality, routing_memory UNCHANGED.

### RATIFY-ANNEXG-V9-CURRENCY-20260811

- [ ] **RATIFY-ANNEXG-V9-CURRENCY-20260811** — requested by `auditor` for task `consolidated-era-and-annexg-token`
  - block ref: `artifacts/audit/completion-flurry-wiring-audit-20260811.md#c-1-operator-signature-items`
  - command (pre-validated, dry-run exit `0`):
    ```
    bash /mnt/raid0/llm/epyc-root/artifacts/operator/ratify_annexg_v9_currency_20260811.sh --attest RATIFY-ANNEXG-V9-CURRENCY-20260811
    ```
  - dry-run evidence: --validate-only exit 0: both edit sites found exactly once; candidate sha256 d60f4129d84c498cf456a886fa4e5fc7f1db621315bfba96bc39377d6250d6c5. Residual check: zero currently-v8 clauses survive; the only remaining 67a433bf4 reference is the historical one inside the amendment note.

### RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811

- [ ] **RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811** — requested by `auditor` for task `post-signature-verification-queue`
  - block ref: `artifacts/audit/completion-flurry-wiring-audit-20260811.md#consumer-states-the-is-it-live-half`
  - command (pre-validated, dry-run exit `0`):
    ```
    bash /mnt/raid0/llm/epyc-root/artifacts/operator/ratify_v9_cpu_bench_era_advance_20260811.sh --attest RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811
    ```
  - dry-run evidence: --validate-only exit 0: source receipt verified ratified with E9-cpu-kernel applied; registry row present; state cpu_bench == E8-cpu-kernel exact-predecessor precondition holds; single edit site; candidate re-parse proves the ONLY semantic change is the one field; candidate state sha256 3679fae563972c236d61ac93747f13681019494fd52e3db565dec1aedd958c6e.

### RATIFY-CPU-BENCH-BINARY-VERSION-20260811

- [ ] **RATIFY-CPU-BENCH-BINARY-VERSION-20260811** — requested by `mainA` for task `a7-kernel-era-misstamp` (Token 2, Block A)
  - block ref: `handoffs/active/batched-decode-measurement.md` → *"Token 2 still OUTSTANDING, and the v9 signature added a new constraint on it"*
  - command (pre-validated, dry-run exit `0` at 2026-08-11 against current HEAD):
    ```
    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python /mnt/raid0/llm/epyc-root/artifacts/operator/ratify_cpu_bench_binary_version_20260811.py --attest RATIFY-CPU-BENCH-BINARY-VERSION-20260811
    ```
  - dry-run evidence: `--dry-run` exit 0. Source sha256 `08a1b93be1279dc3f3d528f5cfdbb67fb99844ff51a1e84aac7ace8beb6702d8` (unchanged since the 21:35Z consolidated-era attestation — no drift). Candidate sha256 `b1afb6796066a86b83d0c7de08f89a150e13eaf8591cb7bdc8a2e0c907ca38e4`. Exactly 6 lines added, 2 per row × 3 rows; row shas before: E6 `a98347d55d148942…`, E8 `8bf58ee7fd65a883…`, E9 `8eb859296ed759e6…`. Vehicle sha256 `8fdf327e260a5bb5cfa674361c40e7299e268400e439b9edcf689cf23068f4db`.
  - **what it does**: adds a structured `binary_version` + `kernel_commit` to the three cpu_bench KERNEL-CUTOVER rows (`E6-cpu-kernel` 10098, `E8-cpu-kernel` 10107, `E9-cpu-kernel` 10125). Every value is re-extracted from that row's own `note:` and cross-checked; the script refuses if its table and the registry disagree. **No measured value changes, no era is added, moved or removed, and no existing field is edited** — this is purely additive structure over facts the registry already states in prose.
  - **why it is needed**: `attestation.binary_version` is the only field that witnesses which kernel actually executed a run, but the registry records the binary only inside free prose, so the A7 repair has nothing to bind a stamp *to*. It also **resolves the `cpu_bench` scope collision** created by the 21:35Z signature: after this, "the kernel era at instant T" = the latest cpu_bench row that *has* a `binary_version` and whose `from` ≤ T. Verified on a copy — for the W1/W2/W4 instant `2026-07-29T15:47:29Z`, scope-only derivation returns `E8-cpu-bench-throttle-scope` (wrong) while binary-witnessed returns `E8-cpu-kernel` (right). W0 and today are unchanged either way.
  - **deliberately excluded**: `E5-cpu-kernel`. Its note records no binary version and no commit sha, so there is nothing to witness and inventing one is the exact failure this repair exists to stop. Consequence, stated rather than papered over: kernel-era derivation **fails closed** for instants in `[2026-06-26T22:07:11Z, 2026-07-20T13:30:13Z)`. No banked manifest falls in that gap — E5 pre-registration begins 2026-07-23.
  - **safety**: refuses without `--attest`; idempotent (re-running exits 0 as a no-op); refuses on drift, on a half-applied row, and when a row's note disagrees with the asserted value; per-row independent via `--only`, so striking any row from this token leaves the others valid. All five refusal paths and the idempotent re-apply were exercised on copies, not asserted. Writes receipt + keyed index in the house shape at git-tracked paths.
  - **not in this token**: the code repair (three remaining stale constants, derived lookup, run-manifest binding). Code is not a trust boundary and needs no signature — it is gated on this field existing, and `mainA` executes it once this is signed.

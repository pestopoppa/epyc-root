# 2026-10-03 — workspace-ec (renamed from workspace-8d after the host reboot)

This session was workspace-8d until the host went down (~2026-10-01 20:57Z to ~10-03 03:20Z). Its 2026-10-01 work is in
`2026-10-01-workspace-8d.md`. This file starts with the 10-01 evening results that the outage kept out of a wrap-up.

## RI-18 review gate: scored, verdict DROP (complete, 2026-10-01 18:53Z)

- The pinned revise redo finished 90/90 in workspace-76's granted gap: orch `08edc054`, detached worktree
  `orch-ri18-pin-08edc054`, segment `revise-20261001T181047Z-1960bd`, end `exit 0`. `score` ran automatically.
- **Decision DROP, pre-registered clause 1.** π1 (review every eligible answer) has a net of **−38.3 per 100 items,
  95% CI [−42.7, −34.0]**: 12 fixed, 234 broken, accuracy 72.2% → 33.9%. Split B is [−44.8, −32.4].
- The production gate πQ(0.6) never fires: 0 eligible triggers, net 0 [0, 0], so it is untested under BOUNDED-NULL-1.
  t* = 0.30, a tie at net 0. AUROC of −avg_q is 0.558 [0.511, 0.607]. n_primary = 579 (608 items; 29 HTTP errors).
- Mechanism: the cap-300 reviewer flags most correct answers WRONG (specificity 0.21 / 0.25 on A / B), and
  `worker_general`'s rewrite breaks 70-75% of those.
- The secondary rule reads HOLD_CAP_300: `question_cap=1500` does not land.
- Evidence: `/mnt/raid0/llm/tmp/ri18/run-v1/score.json`, `/mnt/raid0/llm/tmp/ri18/score-final.log` and the 6-row
  `belief_measurements.jsonl` sidecar.
- Derived:
  - **RI-18c** applies the DROP: remove the gate, verdict and revision from the five call sites and
    `review_low_q_threshold`; C1-C3 go with it.
  - **VB-RI18a**: the sidecar lacks the orch commit and store sha its adapter contract requires, and the run lives in
    scratch.
  - Declined: RI-18a/b (the instrument is retired) and VB-REVIEW-GATE (its producer is being deleted).
  - The TE-reopen note: after RI-18c, A2 has no review-gate trigger.

## ARCHSWAP-4: `:8074` relaunched under its own label (complete, 2026-10-01)

- `orchestrator_stack.py reload architect_general` ran from 18:10:45Z to 18:12:51Z, in the same gap as the RI-18
  redo. It gave PID 292218, slot dir `/mnt/raid0/llm/cache/kv_slots/architect_general`, and /health ok.
- `status` afterwards showed every model server with attest `ok`, i.e. 0 drift. Only ARCHSWAP-3b (the A-3 frontdoor
  scout-stage claim sample) is left of the ARCHSWAP residue.

## Lost cross-session messages while idle (2026-10-01, note only)

- The session went idle awaiting an operator decision. workspace-76's bus messages queued at 19:10Z and 20:01Z were
  never processed before the host went down at ~20:57Z.
- An idle session does not drain its inbox. Nothing acted on those two messages before the outage. Re-read them from
  the bus rather than assuming they were handled.

## Post-reboot stack restart (2026-10-03 ~03:5xZ)

- The production stack is back up, with every model server attest `ok`.
- DS41 holds all CPU regions in closed windows, so the frontdoor `/chat` serving proof waits for a DS41 open window.

## `start --dry-run` launched the production stack (fixed, orch `99e3e5fe`)

- On the freshly rebooted host, `orchestrator_stack.py start --dry-run` without `--migrate-to` started the whole
  stack. Only the `--migrate-to` path reads `--dry-run`. It was benign because a start was intended next anyway.
- Fixed in orch `99e3e5fe`, which refuses the combination (exit 2) and adds tests that drive `main()` with
  `cmd_start` booby-trapped. This is the same class as the 2026-08-12 inert `--validate-only`.
- Incident: `INC-20261003-start-dry-run-launched-stack`. Filed SCG-INERT-FLAGS, a structural sweep for other
  parsed-but-unread flags.

## `repl_embedding_pool` came back ON after the reboot (reset)

- `POST /config` writes persist in `orchestration/runtime_flags.json` across API restarts and reboots. So the
  2026-10-01 runtime enable for `orsv` survived the outage, against the REPL-EMB-2.1 kill rule's OFF default. It was
  turned OFF this morning (record stamped 03:51:31Z).
- Incident: `INC-20261003-runtime-flag-survived-reboot`. Filed REPL-EMB-4.5: an experiment enable carries an expiry
  or an explicit restore step.

## DFlash2 stack change

- The DFlash2 stack change for the 27B is in packaging for the operator's signature (stack-change package; nothing
  applied).

| Repo | File | Change |
|---|---|---|
| epyc-root | `handoffs/active/routing-intelligence.md` | RI-18 ticked with the DROP verdict; RI-18c filed; RI-18a/b declined |
| epyc-root | `handoffs/active/thesis-experiment-orchestrator-vs-strongest-model.md` | ARCHSWAP-4 ticked; residue line; TE-reopen RI-18 note |
| epyc-root | `handoffs/active/vidya-belief-substrate-program.md` | VB-REVIEW-GATE declined; VB-RI18 status; VB-RI18a filed |
| epyc-root | `handoffs/active/repl-embedding-retrieval.md` | "runtime-only" corrected; REPL-EMB-4.5 filed |
| epyc-root | `handoffs/active/stack-change-governance-pipeline.md` | SCG-DRYRUN `[x]`; SCG-INERT-FLAGS filed |
| epyc-root | `docs/reference/agent-config/INCIDENT_LOG.md` | two INC-20261003 entries |
| epyc-root | `progress/2026-10/2026-10-03-workspace-ec.md` | this file |

Index-row and adapter-README edits are prepared, not applied:
`/mnt/raid0/llm/tmp/wrapup-ec-20261003/INDEX_ROWS.md`.

## STACKCHG-DFLASH2-20261003: :8083 on DFlash2, Qwen3-VL-30B to cold CPU (complete, 2026-10-03 ~04:45Z)

**Problem.** On 2026-10-01 the operator found production :8083 (Qwen3.8-27B-Q8_0, `architect_critic` with
`coder_escalation` and `ingest_long_context`) on `--spec-type draft-mtp --spec-draft-n-max 4`, five weeks after the
2026-08-27 ruling that DFlash2 is its spec-decode path. Ruling 2026-10-01: "ALWAYS use dflash2".

**Root cause.** The ruling lived only as prose in two handoffs (`autokernel-champion-aggregate.md` ruling 3,
`dflash2-block-drafter-experimental-build.md`). Its one checkbox ("DFlash2 selection decision — BLOCKED",
`qwen38-27b-replace-qwen36.md`) was owned by INF-62, which had no write path into the registry. The master had no
drafter field; `compile_lean` had no selection input; `stack_priors` enabled speculation only for `draft-mtp`; the
launcher could not emit `-ngld`. The 2026-07-31 `production_recipe: draft-mtp` was hand-copied per role and
re-inherited by the 27B swap (`b376dadd` / `7483d7fb`), the v10 freeze and ARCHSWAP. Design and chain:
`/mnt/raid0/llm/tmp/drafter-compile-20261001/DESIGN.md`. Incident: `INC-20261003-dflash2-ruling-never-compiled`.

**Fast path first (operator-approved).** At 04:30:01Z an operator-terminal relaunch ran the target argv (PID
3737649): 91.7 tok/s single-stream decode, draft acceptance 450/490, vs workspace-76's MTP probe of ~37-41 tok/s at
the same shape (`/mnt/raid0/llm/tmp/ds41-c95/probe-decode-vs-context.md`). One request, not a measurement (Q38-T7).
:8086 was stopped with `orchestrator_stack.py stop`.

**Permanent fix.** Signed `RATIFY-STACKCHG-DFLASH2-20261003` at the terminal, 2026-10-03T04:39:55Z. Package archived
at `artifacts/operator/stack-change-dflash2-20261003/PACKAGE.md` (root `ceae5967`).
- DRAFT-SEL-1: master `roles.<model>.drafters` lists `mtp` and `dflash2`; `stack_topology.yaml`
  `drafter_selection: {architect_critic: dflash2}`; compile fails closed on unlisted, alias-keyed, missing or
  hand-carried drafters. `production_recipe` became `default_spec_type` (n-gram scope).
- Vision: Qwen3-VL-30B to device `none`, tier WARM, NUMA_HALF_A, not retired. DFlash2 (44.30 GiB) leaves no room
  for it on the card (66.75 > 62.00 GiB).
- Two pipeline bugs fixed: `update` was green over a lean that fails the import-time VRAM gate (new fresh-process
  `serving_shape_capacity` step), and a tier flip could never compile (update-only lean bootstrap).

**Bring-up results.**
- `reload architect_critic` → :8083 PID 3793153, stack-launched with `-md Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99
  --spec-type draft-dflash --spec-draft-n-max 8` (clamped to 7); np4, 196608, q8_0, kv-unified. Load log shows
  `draft-dflash`.
- VRAM sampler armed before the reload (`.../stack-change-dflash2-20261003/apply/vram_during_reload.log`): 44.31 GiB
  on the old process, 0.01 at unload, new-process load-time peak **43.49 GiB** (04:44:57Z). Load peak ≤ runtime
  44.30, so the declared 37.92 GiB non-KV stays conservative (Q38-T8).
- Alias completion via :8000 `coder_escalation`: correct.
- `stack_change_pipeline check --run-promotion-gate`: runtime_attestation ok, serving_shape_capacity ok,
  promotion_gate ok.
- API reloaded (PID 3794270, `ORCHESTRATOR_VISION_VL_BACKEND=server`). :8086 down; image requests refused with no
  `llama-mtmd-cli` spawned — but the refusal took **27.9 s**, not fail-fast (S-20).

**Session failures.** The 10-01 session went idle awaiting an operator VRAM decision instead of asking at once; the
10-03 package bundled the unrelated vision move; the operator had to push twice. Incident:
`INC-20261003-urgent-fix-slowed-by-bundling`. Lesson: a recipe ruling becomes a registry field plus a compile check;
an urgent production fix offers the fast path first.

| Repo | Commit | Change |
|---|---|---|
| epyc-inference-research | `be2cc414` | master `drafters`, DFlash2 VRAM 37.92 measured, VL cold CPU, policy amended |
| epyc-orchestrator | `d3233170` | DRAFT-SEL-1, `-ngld`, VL tier/backend, capacity step + lean bootstrap, contention withdrawal |
| epyc-orchestrator | `5265e09d` | derived: lean, descriptors, stack_priors, summary |
| epyc-root | `ceae5967` | receipt, package archive, change-topology `device: none` is CPU |

**Filed (open):** Q38-T7 (DFlash2 production-shape speed + correctness + coherence); S-18 (VL CPU speed/quality on
first start); S-19 (contention re-bench before vision goes hot); S-20 (27.9 s refusal → fail fast); DRAFT-SEL-2
(legacy-drafter audit of the other roles); CH-17 (re-select spec-decode recipes at every kernel freeze);
SCG-FASTPATH and SCG-RULING-TO-FIELD (stack-change skill); KVU-15 (KV-pool step 1, in progress), KVU-16 (step 2:
`-c 393216`, 262144 cap, n-max 7, in packaging; `/mnt/raid0/llm/tmp/kv-sizing-8083-20261003/DECISION.md`); KVU-17
(serving telemetry, in progress); VB-SERVING-DF2 (belief-kernel wiring for the three new producers).
**Ticked:** the DFlash2 selection decision, STACKCHG-DFLASH2, DRAFT-SEL-1, SCG-CAPACITY-FRESH, SCG-LEAN-BOOTSTRAP,
Q38-T8. **Annotated, not ticked (other owners):** KVU-1b / M-3b superseded (no MTP left on :8083); KVU-1d (32.80
replaced by 37.92); S-16 (Qwen3-VL-30B already serves :8086).

| Repo | File | Change |
|---|---|---|
| epyc-root | `handoffs/active/qwen38-27b-replace-qwen36.md` | selection `[x]`; Q38-T7 filed; Q38-T8 `[x]` |
| epyc-root | `handoffs/active/dflash2-block-drafter-experimental-build.md` | IN PRODUCTION banner |
| epyc-root | `handoffs/active/autokernel-champion-aggregate.md` | ruling 3 annotation; CH-17 filed |
| epyc-root | `handoffs/active/stack-change-governance-pipeline.md` | STACKCHG-DFLASH2, DRAFT-SEL-1, SCG-CAPACITY-FRESH, SCG-LEAN-BOOTSTRAP `[x]`; DRAFT-SEL-2, SCG-FASTPATH, SCG-RULING-TO-FIELD filed |
| epyc-root | `handoffs/active/multimodal-pipeline.md` | cold-CPU note; S-18, S-19, S-20 filed |
| epyc-root | `handoffs/active/kv-unified-stack-rollout.md` | KVU-1b/M-3b superseded; KVU-1d note; KVU-15/16/17 filed |
| epyc-root | `handoffs/active/thesis-experiment-orchestrator-vs-strongest-model.md` | :8083 drafter-change note |
| epyc-root | `handoffs/active/vidya-belief-substrate-program.md` | VB-SERVING-DF2 filed |
| epyc-root | `handoffs/active/CURRENT-CAMPAIGN.md` | 2026-10-03 GPU posture block |
| epyc-root | `docs/reference/agent-config/INCIDENT_LOG.md` | two INC-20261003 entries |

Index-row and adapter-README edits are prepared, not applied: `/mnt/raid0/llm/tmp/wrapup-ec-dflash2/INDEX_ROWS.md`.

## Serving telemetry, KV-pool steps 1-2, UFH-14 Phase B, X0 window (2026-10-03 ~04:50-12:10Z)

**Serving telemetry (KVU-17 / UFH14-B5), live.** Orch c6225e8b, f7fad574 and 9a0d38e0 were deployed by an API-only
reload at 04:59Z, and the era boundary ST1 is at orch 4e23e553.
- **Per-call records:** one record per llama-server call goes to `logs/serving_calls/serving_calls.jsonl`. It carries
  role, port, request_id, queue wait, llama `timings`, outcome and orch commit.
- **`prompt_eval_ms` fixed.** The chat-stream path had hard-coded `prompt_eval_ms=0` and ignored the last-chunk `timings`.
  A live :8083 call now records 2,368 ms prompt eval and 113 ms queue wait.
- **Progress rows no longer lost.** Each uvicorn worker buffered up to 10 rows, so an unclean shutdown dropped them. Rows
  are now flushed at task completion, after 30 s, or at exit.
- **Launch banners:** every stack launch now writes `logs/server_launches/<port>.json`.
- **Belief-kernel wiring:** adapter row and VB-SERVE-TIMING-1 at root 999954ca.
- **Test-isolation bug:** 2 synthetic `contention_denied` rows written by a test into the live
  `/workspace/logs/progress/2026-10-03.jsonl` were deleted on the operator's word. The isolation fix is filed as
  SCG-TEST-LOGDIR.

**KV-pool decision.** The analysis is at `/mnt/raid0/llm/tmp/kv-sizing-8083-20261003/DECISION.md`.
- **Hybrid model.** The 27B is a hybrid: only 16 of 64 layers hold growing KV, at 34,816 B/token q8_0. Measured marginal
  cost is 42 KiB/token including the KQ mask and flash-attention scratch.
- **Why the pool exhausted:** it was mostly traffic that bypassed the gate.

**Step 1 (KVU-15 / UFH14-B2), live.** Orch 2586a7bb, deployed by an API reload.
- Scouts are now admitted by tokens.
- One long prefill at a time per server: ≥16384 estimated tokens, lease ends at the first chunk or prompt/250 tok/s.
  The gate also observes `/slots`. `ORCHESTRATOR_KV_POOL_LONG_PREFILL_TOKENS=0` turns it off.
- The per-request cap comes from config: min(slot ctx, model ctx_max).
- Verified with a live gated call.
- Limits: the gate runs per uvicorn worker; size is judged on the whole prompt, so a mostly-cached prompt still waits.
- `:8000` is not an OpenAI-compatible passthrough (no `/v1/responses`, replayed streaming, no timings). That is
  UFH14-B6, gap list in `/mnt/raid0/llm/tmp/kv-gate-8083-ec/BYPASS.md`.

**Step 2 (KVU-16 / UFH14-B3), signed and applied in git, NOT yet live.**
- **Signed:** operator receipt RATIFY-STACKCHG-KVPOOL-20261003, 11:50:52Z, at the terminal.
- **Commits:** research 412e8fc1, orch 09e91e1e and 841935ea, root archive 64d70d17.
- **Change:** `-c 393216` unified; the v10 server clamps each slot to n_ctx_train 262144 itself. Draft n-max 7.
- **Correction:** I had told the operator "two full 262k requests fit". That was wrong: 393216 holds one 262k request
  plus 131k, or 4 × 98k. The operator signed knowing this.
- **Bugs fixed in the package:**
  - step 1 would have misread the new pool as split, which disables admission;
  - a single `update` wrote stale priors;
  - a stale template `draft_max: 4` override.
- **Pipeline state:** `update` and `check` show only the 2 expected live-drift lines.
- **Relaunch pending.** `reload architect_critic`, then `reload orchestrator`, plus serving proof (§7.3, including the 4 ×
  90k concurrency probe) wait for workspace-89's "F12 done".
- **Hold:** the API must NOT be reloaded before the relaunch, because the new code expects the 393k pool.

**UFH-14 (workspace-89's handoff, operator directive "fix all harness bugs, model-agnostic, demo on 27B first").**
- Phase B items: B5 ticked, B2 ticked, B3 in flight.
- B4 (prefix-cache and cache-ram policy) is not started. Next after B3.
- B6 (passthrough) is scoped.

**INF-80 EXL3-X0 window granted to workspace-89.**
- **When:** 2-3 h exclusive :8083, immediately after the KV-pool proof.
- **Production handling:** `stop architect_critic`; its roles fail fast with no failover. Serving records show no
  orchestrator :8083 traffic since 05:00Z apart from tests.
- **Arm (b):** uses the new production shape.
- **Hand-back:** restore through the stack, then a short serving proof.

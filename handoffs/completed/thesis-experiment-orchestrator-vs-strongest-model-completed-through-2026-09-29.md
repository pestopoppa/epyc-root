# Thesis Experiment — completed scope through 2026-09-29

> **Historical ledger only; current work lives in [`../active/thesis-experiment-orchestrator-vs-strongest-model.md`](../active/thesis-experiment-orchestrator-vs-strongest-model.md).**
> Split out at the 2026-09-29 operator-invoked wrap-up (workspace-8d). The experiment is PARKED. The boxes below are
> done, and the text is verbatim from origin/main `fdcc92f40` (the spec's base `2e239c9ca` plus the 2026-09-29 wrap-up). The pre-registration (decision rule, TE-3a
> clarifications) stays in the active handoff, where it is authoritative.

## Tasks (completed)

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
- [x] **TE-reload — deploy TE-1 by an API-only reload** onto orchestrator `280059cc` or later with
  `ORCHESTRATOR_V1_ESCALATION=1`, after the ARCHSWAP (role swap) is applied. **It is the same reload as ARCHSWAP-3's
  B1; run it once.** workspace-8d owns the swap. workspace-76 owns DS41, which binds the 27B by port and is
  unaffected by an API reload. Use `orchestrator_stack.py reload orchestrator`, never the whole stack. After the
  reload, prove the reviewer role resolves to the 27B (`architect_critic`), per the operator's 2026-09-27 ARCHSWAP
  approval (§ *Pre-registration clarifications*).
  ✅ 2026-09-28 — deployed with ARCHSWAP-3's reload: orchestrator main carries `280059cc` and `6d024ced` (the flag in
  production's feature wave, operator-approved). The API was reloaded API-only (PID 1100541, env
  `ORCHESTRATOR_FEATURE_V1_ESCALATION=1`). The reviewer and planner resolve to `architect_critic` (the 27B).

## ARCHSWAP-3 / ARCHSWAP-3b / ARCHSWAP-4 progress records (their parent boxes stay open in the active handoff)

### ARCHSWAP-3 — B1 progress (2026-09-28)

  - Progress 2026-09-28 — done:
    - B1 API-only reload done. `v1_escalation` was then added to production (orch `6d024ced`, operator-approved) and
      the API was reloaded API-only a second time: PID 1100541, `ORCHESTRATOR_FEATURE_V1_ESCALATION=1` in its env.
    - `check`: only the two known `slot_save_path` drifts, and `declared_env_attestation: ok`.
    - P4: the URL snapshot is identical to the evidence (19/19).
    - The reviewer and planner resolve to `architect_critic` (the 27B). The runtime-facts state routes
      `architect_general` → `:8074`, and `architect_critic`, `coder_escalation` and `ingest_long_context` → `:8083`.
    - Open: P1-P3 and the A-3 scout-stage sample, split out as ARCHSWAP-3b. This box ticks when ARCHSWAP-3b does.

### ARCHSWAP-3b — P1, P2 and P3 serving proofs

  - [x] P1: an escalation reaches `:8074`. Script `/mnt/raid0/llm/tmp/archswap-20260927/serving_proof.sh`; run it in
    a CPU window. ✅ 2026-09-28 15:59Z (DS41 window open, loop not holding the claim): `x_force_role=architect_general`
    served by `:8074` (log growth), `api_role=architect_general`, answer "The product of 17 and 23 is 391." (evidence
    `/mnt/raid0/llm/tmp/archswap-20260927/serving-proof-20260928T155858Z/summary.txt`). Proves role → port binding;
    the package's "graph escalation reaches ArchitectNode" form is covered by the A2 path when UFH-13 reopens.
  - [x] P2 and P3: `architect_critic`, `coder_escalation` and `ingest_long_context` answer from `:8083`. Script
    `/mnt/raid0/llm/tmp/archswap-20260927/proof_8083.sh`; run only on workspace-76's "go" at a DS41 critic pass.
    ✅ 2026-09-28 — routing PROVEN: all three were served by :8083 with the right `api_role` (evidence
    `/mnt/raid0/llm/tmp/archswap-20260927/serving-proof-20260928T085434Z/summary.txt`).
    - Correction: the script's P2 line expected `reasoning_content` at medium. Through :8000 that could never pass, on
      any path, before or after the swap: `architect_critic` is on the `/completion` lane, where its
      `chat_template_kwargs` are dead and nothing surfaces `reasoning_content`. The reasoning expectation is not part
      of P2; it moves to the lane decision in `routing-intelligence.md` RI-23. The same proofs exposed the
      untemplated-prompt defect (a JSON template echoed, a suffix repeated, `<think>` inline), filed as
      `harness-selection-and-integration.md` HS-OD-10 (the `x_disable_repl` path, fix landing) and RI-23.
    - Update 2026-09-28: the HS-OD-10 fix landed (orch `5ddb7320`, test tap isolation `8a7d57a8`) and is live after an
      API-only reload (PID 458129). A re-run of `proof_8083.sh` on workspace-76's next "go" should now show templated
      answers with `reasoning_content` split out on this path.
    - ✅ 2026-09-29 ~07:06Z — re-run after the HS-OD-10 fix, in the bundled :8083 window (workspace-76's go, DS41
      paused), on the ARCHSWAP-4 relaunched :8083. All three roles were served by :8083 with the right `api_role`
      and returned the same clean templated answer, "The product of 17 and 23 is 391.": no template echo, no
      repeated suffix, no inline `<think>`. `reasoning_content` came back empty (`architect_critic`: 21 completion
      tokens), so the model answered without a thinking block on this path. The earlier expectation of a split-out
      `reasoning_content` is not met and is not part of P2; surfacing reasoning belongs to RI-23. Evidence:
      `/mnt/raid0/llm/tmp/archswap-20260927/serving-proof-20260929T070556Z/summary.txt` (+ `P2-*.json`, `P3a-*.json`,
      `P3b-*.json`).
    - ✅ 2026-09-29 15:04Z — re-run with RI-23 live (thinking-on roles on the chat-completions lane) and RI-23a
      applied, under workspace-76's "go". All three roles were served by :8083 with the right `api_role`, returned a
      clean answer ("17 × 23 = 391.") and now return `reasoning_content`. The reasoning expectation dropped from P2
      above is therefore met too. Evidence:
      `/mnt/raid0/llm/tmp/archswap-20260927/serving-proof-20260929T150402Z/summary.txt`.

### ARCHSWAP-4 — the `:8083` half (B2, 2026-09-29)

  - 2026-09-28: the `:8083` relaunch waits on workspace-76's go; the `:8074` relaunch waits for a long idle gap.
  - ✅ 2026-09-29 07:05:56Z — **the `:8083` half is done (B2)**, in the bundled :8083 window (workspace-76's go,
    DS41 paused). Production `:8083` was relaunched through the stack (`orchestrator_stack.py reload
    architect_critic`) on v10 `ffc1bac82` (`kernels/builds/gpu-20260921-ffc1bac82`, the `production/gpu` store) with
    `--slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_critic`. The window's GPU A/B step failed its per-arm
    checks twice more and each attempt ended with the same B2 relaunch, so the final `:8083` PID is **3363961**
    (started 07:08:48Z). Post-proof on each relaunch: exe is the v10 llama-server, the cmdline carries the
    `architect_critic` slot dir, its own `libggml-hip` is mapped, `/health` ok, `/props` build_info
    `b10303-ffc1bac82`, and it is VRAM-resident. The `orchestrator_stack.py status` attestation (taken after the first
    relaunch, same recipe) no longer reports the `:8083` slot_save_path drift, and `stack_change_pipeline.py check
    --numa-mode both` has one error left, the `:8074` drift below. Evidence:
    `/mnt/raid0/llm/tmp/gpu-champion-ab/runs/w8083-20260929T070523Z/` (`w8083_bundle.log`, `stack_status.txt`,
    `pipeline_check.txt`), with the retries in `runs/w8083-20260929T070737Z/` and `runs/w8083-20260929T070833Z/`.

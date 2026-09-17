# 2026-09-17 — sub-op-decisions (three operator rulings applied; zero inference)

**Worktree.** `/mnt/raid0/llm/worktrees/op-decisions`, branch `sub/op-decisions-20260917`, created off
`origin/main` `75d5e2a7a`.

**Not pushed.** D2 moves a handoff that index row UFH-06 still points at, so the branch only passes
`index_state.py --check` once the index patch is applied. The main session applies
`/mnt/raid0/llm/tmp/op-decisions-index.patch`, regenerates and pushes everything together.

No inference was run, no process was started or stopped, and the host crontab was not touched.

## D1 — OP-INF40 → Option A (INF-40)

- **Handoff.** `handoffs/active/moe-spec-cpu-spec-dec-integration.md`:
  - The decision box is ticked ✅ 2026-09-17.
  - The ruling is recorded: a 5-rep alternating A/B/A/B confirm of `moe_spec_budget` ∈ {0,128} on
    `architect_critic` (122B Q4_K_M, CPU). It is queued until the AutoKernel quiet window ends, and it
    needs an explicit operator go.
  - A new gated `- [ ]` covers the confirm run, and an optional `- [ ]` covers a qwen4exp measurement.
- **Operator question.** Could the confirm run on qwen4exp instead? Answer: not as a substitute,
  because the deploy decision is per model. Two of the three drafted reasons were wrong when checked,
  and the handoff records them struck through with the corrections:
  - *"qwen4exp has no speculative verification path"* is wrong.
    - INF-70 Axis E already ran E1–E3: E2 ported the qwen4exp MTP path on 2026-09-02, and E3 measured α.
    - Champion `ef81196d5` serves MTP at 82.1% acceptance with `--spec-draft-n-max` 3 (fleet) or
      4 (coding), so a verification batch is 4–5 tokens.
    - `moe_spec_min_batch` defaults to 4 (`common/common.h:475`, `src/llama-context.cpp:272` in
      `ef81196d5`), so the `build_moe_ffn` mask (`src/llama-graph.cpp:1985`) would fire. Only plain
      batch-1 decode never triggers it.
  - *"qwen4exp is ~95 ms/token, no faster than the 122B"* is wrong.
    - The ~95 ms figure is the 2026-09-02 audit-day baseline, which the roofline header marks as
      not the current state.
    - The consolidated champion measures 27.893 t/s plain and 43.281 t/s MTP, roughly 2.6–4× the 122B's
      10.84 t/s.
  - The budget scale does not transfer either: B=128 is n_expert/2 on the 122B (256 experts) but
    n_expert/4 on qwen4exp (512 experts).
- **Fact the decision package missed.** Frozen production v9 `0db32c06e` has no MoE-Spec code
  (`git grep moe_spec` finds nothing).
  - The +10.7% ran on `/mnt/raid0/llm/tmp/inf40-build`, which is v9 + `c7c37a0d9` (`plan.json`).
  - The registry key therefore only acts on a serving binary that contains MoE-Spec.
- **Index patch.** Deletes the `OP-INF40` master row. INF-40's next action becomes "Run the 5-rep
  moe_spec_budget {0,128} A/B/A/B confirm on architect_critic after the AutoKernel quiet window
  (operator A)" (120 chars).

## D2 — security-review CI gate → Option A (dropped; handoff completed)

- **Handoff.**
  - The last box is struck through and ticked as DROPPED, and the Status line is updated.
  - The Open Questions section is marked as design notes with no tracked work, and its CI bullet is
    struck through.
  - The handoff moved to `handoffs/completed/` with a completion banner. Its privacy-hygiene link now
    points at a sibling in `completed/`, and it has no links into `active/`.
- **Inbound references repointed:**
  - handoffs: `reviewer-typed-artifacts.md`, `stale-open-audit-2026-07-18.md`, `non-inference-backlog.md`
  - wiki: `wiki/safety.md`, `wiki/knowledge-management.md`
  - `research/intake_index.yaml` (3 path entries)
  - the evidence paths in `scripts/validate/repo_readiness_scorer.py` (`tests/validate/test_repo_readiness_scorer.py`
    passes 15/15)
  - `design-backlog-triage-2026-07-23.md` C52 is annotated.
- **Left unchanged.** Historical snapshots (`data/repo_readiness/*.json`, inference-batch bundles) and
  the superseded `BACKLOG-DISPATCH-QUEUE.md`.
- **Index patch.** Deletes UFH-06.

## D3 — OP-9 → Option B (pinned hub_supervisor copy for the host cron)

- **Installer.** `scripts/operator/install_supervision_cron_20260916.sh --all` now does four things:
  - It fetches origin in the shared clone (refs only) and pins origin/main, or `--pin-sha`.
  - Inside the container, it `git archive`s `hub_supervisor.sh`, `hub_launch_spec.py` and
    `refresh_hub_view.sh` into `/mnt/raid0/llm/ops/hub-supervisor/<sha>/scripts/dashboard/`. Each
    file is checked byte-for-byte against the commit. The pin is stamped (`PINNED.txt`, `SHA256SUMS`),
    made read-only and renamed into place.
  - Its cron line runs that copy with `EPYC_ROOT`, `HUB_CANONICAL_ROOT` and `HUB_LAUNCH_MANIFEST`
    passed explicitly. The line never uses the shared clone or the 180 s auto-reset view.
  - `--dry-run` stays side-effect free: no fetch, no pin, no crontab write.
- **Single instance.** No change was needed.
  - `once` and `loop` both `flock -n /tmp/hub_supervisor_8100.lock` inside the container.
  - Read-only check: the live daemon (pid 639194, running
    `/mnt/raid0/llm/epyc-root/scripts/dashboard/hub_supervisor.sh`) holds that file on fd 9.
- **Tests.**
  - New: `scripts/dashboard/tests/test_install_supervision_cron.sh`, 40/40. It uses fake docker and
    crontab shims plus a fixture repo. Before the new installer was restored, the test was run against
    the previous one and failed.
  - Existing: `test_hub_deploy_sync` PASS, `test_hub_manifest_launch` 38/38, `test_hub_stale_source`
    6/6, `test_hub_view_refresh` 42/42.
  - Pid 639194 was still alive after the runs.
- **Handoff.** `handoff-index-and-backlog-graph.md` records the ruling under the OP-9 parent, with a
  `- [ ]` box for the operator's host install.
- **Index patch.** Rewrites the OP-9 row to "B chosen 2026-09-17 — operator runs the pinned-copy host
  install; then delete this row", with its link and date kept. The row is not deleted.
- **Host command** (after push). Run on the host from bash or zsh; from fish, wrap each line in `bash -c '…'`:
  ```bash
  docker exec -u node epyc-root git -C /mnt/raid0/llm/epyc-root fetch origin
  bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/install_supervision_cron_20260916.sh) --all --dry-run
  bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/install_supervision_cron_20260916.sh) --all
  ```
  - The fetch is required: without it, `origin/main` in the shared clone may still serve the old,
    unpinned installer. The dry run must print a `pin: <sha> -> …` line.

## Index check

With the patch applied in scratch state, `index_state.py` regenerated with rc 0, and `--check` exited
0 with "0 problem(s)". Without the patch, `--check` exits 1, reporting the UFH-06 DEAD LINK plus rollup
freshness. The scratch edits were reverted, and the patch applies cleanly to the branch
(`git apply --check`).

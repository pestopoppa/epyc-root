# AK audit §B — standalone rowflow/keeper fix briefs (class 4)

Source: `/mnt/raid0/llm/tmp/autokernel-session-audit-20261119.md` §B. Code refs are origin/main at `bde27ba5f` (after 41041359b, bba1c010a, 13370aead, ba3adabf1, e14edec25, 671a6adf7). Every brief is for a builder subagent working in a lane worktree; tests live in `scripts/coordination/tests/`; nothing here edits a running keeper in place (deploy through `deploy_rowflow.sh`, INSTALL.manifest). **All F-items touch the rowflow engine or publish gate and therefore carry a D9-ack** (the three 11-19 rowflow commits each did).

Evidence confirmation: 8 `queued-smoke-dropped` alerts exist in `rowflow-alerts.jsonl`; `GPU-SMOKE-BATCH started` 17:35Z/17:51Z in the keeper log; the DROP-as-pass filing is the subject of `bba1c010a`; 12 `operator_gate` entries in `handoff-sessions.json` match the "handoff-scoped hold" complaint (publish refusals print to the caller's stderr, so no log line exists for 08:16Z — accepted on the registry evidence); `.index-state.json` had 360 commits from ≥5 sessions since 11-10. Not confirmable from host logs: §2.5 contamination offender, §2.7 r12 crashed-controller grant (keeper log not sampled for that window) — briefs F6/F7 include the fixture as proof instead.

## F2 — one smoke runner per row id (B2)
- Files: `scripts/coordination/rowflow/rowflow.py` (`dryrun_run`, `smoke_queued_running` :1052), `publish_row.py` (`run_smoke` :727, `--smoke-now`, `gpu-batch` path in `rowflow.py`).
- Change: take a per-id `flock` on `dryrun/<id>/SMOKE.lock` around the whole smoke (allocator batch, `--smoke-now`, `gpu-batch`, publish's own dry run). A second caller blocks ≤ smoke timeout, prints `smoke in progress by <pid/who>, waiting`, then returns the recorded PASS/FAIL (`dryrun/<id>/PASS.json` / newest `FAIL-*.json`) instead of running again. Keep the existing republish refusal (`publish_row.py:1028-1032`) and make its message name the lock holder.
- Acceptance (audit): start a 60 s fixture smoke via the allocator, call `publish_row.py` on the same spec concurrently → exactly one `dryrun/<id>/PASS.json`, row stays in `ready/`. Add `test_rowflow_smoke_lock.py`.
- D9: yes (engine).

## F3 — verdict semantics on every filing path (B3 residual)
- Files: `scripts/coordination/churn/file_result.py` (`coerce_declared_nonpass` :261, called at :350/:393 for agent verdicts only; `--correct` :279-296).
- Change: (a) apply `coerce_declared_nonpass` to `--correct pass --reason R` when `R` or the row's latest result record declares `DROP(` / `FUTILITY_` / `diagnostic`; (b) on the machine-rule path (`decide` :400) read the result record's `status`/`rationale`/`answer` fields when present and coerce a `pass` the same way, recording `coerced_from`; (c) `--correct` by a non-owner stays rc 8 (already).
- Acceptance (audit): fixture `{"verdict":"pass","rationale":"DROP(diagnostic) …"}` → FILED inconclusive (exists, `test_churn_file_result.py`); add: `--correct pass` by non-owner → refused; by owner → new record, old kept as `*.superseded-<ts>`; machine rule `rc==0` with record `status: DROP(...)` → inconclusive.
- D9: yes (filing semantics).

## F4 — holds keyed by (session, scope); admission by the row's owner (B4)
- Files: `publish_row.py` `check_operator_gate` :322-345; `handoff_sessions.py` `gate`/`operator_gate` (registry); new `handoffs/active/holds.yaml` (standard decision 3; `box_index.load_holds` already parses `id`/`targets`).
- Change: hold record = `{id, targets:[handoffs|rows|boxes|files], scope: loop-launch|all-rows|boxes, since, reason}`. `check_operator_gate` refuses a row only when (scope `all-rows` and `handoff_task` ∈ targets) or (the row's `owner` ∈ targets); the registry `operator_gate` becomes a derived view of holds.yaml (write-once migration script that emits today's 12 gates as `scope: loop-launch`). Refusal text names the hold id and scope.
- Acceptance (audit): `holds.yaml` holding `akagg` scope `loop-launch`; spec `owner: autokernel`, `handoff_task` in the held handoff → PUBLISHED; same spec `owner: akagg` → REFUSED naming the hold. Add `test_publish_row_holds_scope.py`.
- D9: yes (admission rule); the operator also owns the hold list itself.

## F5 — churn tools run from the hub view and say so (B5, C5)
- Files: `scripts/coordination/INSTALL.manifest`, `rowflow/deploy_rowflow.sh` (`DEPLOYED.json`), `churn/file_result.py`, `rowflow/publish_row.py`, `session_bus.py`, `queue_status.py`; add `scripts/handoffs/{task_lint,box_index,handoff_box}.py` to the manifest.
- Change: a shared `toolroot.py` that (a) prints `tool-commit <sha>` (from `bin/rowflow/DEPLOYED.json`, else `git rev-parse` of the file's own tree) on every run, (b) resolves config (roster `config.yaml`, holds.yaml, templates) from the hub view path first, (c) when invoked from a checkout whose `HEAD` is > 50 commits behind `origin/main` (one `git rev-list --count` with a 2 s timeout, cached per hour) prints `WARN: checkout N commits behind origin/main; tools/config read from <hub>`. No behaviour change otherwise.
- Acceptance (audit): run `file_result.py --correct` and `session_bus.py drain` from a worktree pinned 300 commits behind → both succeed with current behaviour and print the warning. Add `test_toolroot.py` with a fixture repo.
- D9: yes (touches engine files' startup); C5's SessionStart hook is a separate hooks D9.

## F6 — grants end or shrink when the job stops using them (B6)
- Files: `rowflow.py` grant monitor (UNDERUSED :1450-1451, `UNDERUSED_PCT=5`, `UNDERUSED_S=600`), width admission :1872-1907 / :2196-2217, keeper tick (`ws58-calendar-keeper-v13.sh` IDLE-VIOLATION path).
- Change: (a) `idle-after-crash`: when a grant's launcher pid is alive but its process tree has no descendant with >5 % CPU (or any VRAM for GPU) for two consecutive samples AND the region busy is 0 %, end the grant `reason=idle-after-crash`, write `.ended rc=75`, notify owner. (b) At admission, when the launcher text carries literal thread knobs (`--threads N`, `-t N`, `OMP_NUM_THREADS=N`) sum them; declared width > `ceil(sum/24)` quarters needs `width_justification` (extend the existing `threads is None` branch :1872). (c) keep UNDERUSED but add a `shrink to <n> quarters` suggestion after 30 min and deliver it through `notify.emit` to the owner (today it is a fix task only).
- Acceptance (audit): fixture job forks a worker, kills it, keeps the parent alive → grant ended within 10 min; spec with one `--threads 48` launcher and `multi-quarter(3)` → REFUSED without justification. Tests: `test_rowflow_idle_after_crash.py`, extend `test_rowflow_width.py`.
- D9: yes (grant lifecycle).

## F7 — builds are a lane; contamination names the offender (B7)
- Files: `rowflow.py` (`claim` CLI, region-lock), `hostutil.py` (per-sample process census), the keeper's contamination check (no `CONTAMINATION.json` writer exists in `scripts/` on origin/main — the AK session wrote it by hand; this brief creates the writer).
- Change: (a) `rowflow.py claim --build --cpus N --minutes M` → a short `build` grant on a free quarter; refused with the overlapping grant named when it would overlap a `timing` grant's quarters. (b) Each keeper sample records, per held quarter, foreign processes >20 % CPU with `pid, comm, cmdline[:80], cgroup container id (rowflow.cgroup_container_id :2997), session env if readable`; two consecutive samples → `dryrun/<id>/CONTAMINATION.json` appended and one `contamination` alert to the owner.
- Acceptance (audit): `taskset -c 0-23 cmake --build` under a fixture bench grant on q0 → claim refused; run it unclaimed → `CONTAMINATION.json` names the pid and `cmake` within 2 samples. Test with a fixture `yes > /dev/null` process in place of cmake.
- D9: yes (new grant class + keeper sampling).

## F8 — predicate and completion-check provenance (B8)
- Files: `publish_row.py` preflight :584-608 (today only "already exits 0" is refused).
- Change: tokenise `smoke_predicate`, `--complete-cmd`, `--precond-cmd` for absolute paths and `/mnt/raid0/llm/tmp/<dir>` roots; refuse when a path is outside the row's `scratch_root`/`result_path` dir, names a different row id (`-20261[0-9]{3}` id pattern ≠ this id), or does not exist at publish time and is not listed under a new spec key `expects_created: [paths]`. Message names the offending path and the fix.
- Acceptance (audit): fixture spec whose predicate greps `/mnt/raid0/llm/tmp/<other-row>/out/…` → REFUSED naming the path; same predicate with the path under `expects_created` → published. Extend `test_publish_row_preflight.py`.
- D9: yes (publish gate).

## F9 — every alert reaches a real owner (B9)
- Files: `publish_row.py` (spec validation, `SPEC_KEYS` :68; no roster check today), `rowflow/notify.py` :326 (assignee falls back to `inference` for a non-roster owner).
- Change: at publish, `owner` must be a roster id in `coordination/session-bus/config.yaml` (or a `handoff-<slug>` registered in `handoff-sessions.json`); otherwise refuse with the roster path and the `session_bus.py roster add` hint. Keep the `inference` fallback in `notify` for legacy rows but log `owner-not-roster` once per row. Add `QUEUED-aged` (marker older than 2 h with no batch) and `UNDERUSED` to the kinds `notify.emit` delivers (today: row-ended, smoke-fail, queued-smoke-dropped, disk-floor).
- Acceptance (audit): spec with `owner: not-a-roster-id` → REFUSED; fixture smoke FAIL → one inbox line for the owner within one tick (exists in `test_rowflow_gpu_queue_wait_owner.py` for the roster case; add the refusal and QUEUED-aged cases).
- D9: yes (publish gate + alert kinds).

## Not briefs (for the record)
- B1, B3 (agent path), B12, B14: satisfied on origin/main — see the summary table in the hand-back; add the audit's acceptance fixtures as tests where missing (B1 five-row ordering, B14 `smoke_lane` residency check).
- B10, B11, B13: handoff standard Stage B/C (`HANDOFF-STANDARD.md` → "AK audit items absorbed"); B12/B13 dispatcher side in `DESIGN.md` §2.5.

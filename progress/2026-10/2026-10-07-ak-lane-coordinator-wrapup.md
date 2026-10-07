# AK Lane Coordinator — Wrap-up 2026-10-07

Covers 2026-10-06 → 2026-10-07. Persisting before context compaction; nothing here was previously
wrapped up under this date.

## 1. Served-shape calibration landed and applied on both lanes

Research (epyc-inference-research) commits, in order:
- `9a548baf` — `calibrate_served_shapes --timeout-s` (calibration runs exceed 1h on DS41).
- `bed81e59` — three-regime NMSE cap: keep the old served-shape bound wherever the old policy
  accepted.
- `ac97318f` — deterministic per-case seeding; refuse served-shape binaries built before per-case
  seeding (input-hash debug mode).
- `1bace97d` — sharded calibration under ONE build-role region-lock claim (fixes two Codex Astra
  BLOCKs in the sharded `--execute` claim).
- `a23af0a7` — shards confined to the lock's own cpu list; default `shards = min(16, cases, lock
  cpus // 4)`.

Results:
- **Q38FN**: 250 cases, 3392 s, no anchor-relative exception needed.
- **DS41**: 348 cases, 5252 s on 24 cpus. Two IQ3_XXS shared-expert cases exceeded the 5e-4 NMSE
  cap and were applied with `--anchor-exceeds-generic` (anchor-relative acceptance — a known
  low-bit lead, not a regression): `shexp_down` n=2 = 5.96e-4, `shexp_gate_up` n=4 = 5.22e-4.
- Input-identity checks PASS on both lanes: DS41 348/348, Q38FN 32/32, 0 mismatches.
- New anchors: DS41 `3376147f8`, Q38FN `6ed37bec8`.

Handoff update: `handoffs/active/deepseek-v41-flash-evaluation.md` DS41-C127 (new).

## 2. Lanes relaunched on the new anchors

- **Q38FN**: `q38fn_watchdog2.sh`, state dir `state-6ed37b-*`, `LONGCTX=1`, live since
  2026-10-06T22:18Z.
- **DS41**: `ds41_watchdog5.sh`, state dir `state-337614-*`. Its launch was **REFUSED** by build
  retention: free disk 86 GiB was below the 100 GiB floor. Disk cleanup was in progress as of this
  wrap-up (see §6, the disk crisis).
- Both prior watchdogs died on stale-epoch continuation seeding ("continuation binding does not
  match its own original arguments"). **Lesson**: re-resolving inputs after a calibration requires
  a NEW-epoch watchdog that seeds only from the new epoch — never a continuation off the old one.
- DS41's `owned-targets.json` lacked `cor_build`; the operator added it 2026-10-07.

## 3. Harness fixes landed

- `de02a21d` (epyc-inference-research) — `run.py` was missing the `Mapping` import, a NameError
  that killed Q38FN's longctx keep-gate batches; also added `test_no_undefined_runtime_names.py`,
  a package-wide AST guard against this class of defect recurring.
- `e3bcf010` (epyc-inference-research, Codex Astra round 23) — closes a remeasure-request TOCTOU
  restore race and stops masking claim `OSError`s. This is the matched-floor outlier guard (Astra
  R21-R24): a suspect floor never carries forward; an unguarded floor more than 3x the previous
  floor is refused; the refusal writes an atomic `REMEASURE_REQUEST.json` under
  `<store>/runtime-source-floors/<recipe_hash>/`.
- Q38FN's floor of 6.528% was contaminated by a 5.5-minute degraded block during calibration
  (previously ~0.65%). A `REMEASURE_REQUEST` was filed for recipe `cff9ad900700…`.

## 4. Pending, not landed

Branch `fix/ak-longctx-identity-oracle-20261007` @ `6f116e55` (epyc-inference-research, "full-
observation divergence receipts + DS41 real-mask N>1 coverage", Codex Astra round 1):
- The long-context identity oracle now strips MTP (the anchor's own repeats differed under
  speculative decoding).
- Full divergence receipts.
- FA case set widened to N=1..5.
- A fail-closed DS41 real-mask probe.

C++ follow-ups still open: a probe `--mask-file` mode; a llama.cpp DS41 top-k mask dump hook;
regenerate `test-backend-ops-cpu-fa-longctx-v1.patch`.

Wiring `check_cpu_fa_real_mask_identity` into `run.py` is an **operator decision** — it would block
`cpu_fa_schedule` until the C++ side lands, so it is not something this session should wire
unilaterally.

Handoff update: `handoffs/active/autokernel-all-devices-all-dimensions.md` — note added under
AKX-ALL-9/10/11 (the `cpu_fa_schedule` / numerics route section).

## 5. Pre-existing AK loop test suite failures found

About 376 failed + 75 errors pre-exist in research `autokernel/loop` tests on origin/main
(`python3 -m pytest autokernel/loop -q`, 4556 passed, 998s). Triage in progress at
`/mnt/raid0/llm/tmp/ak-test-triage-20261007/TRIAGE.md`:
- **357 of 451 (79%) collapse to ONE root cause**: commit `440b5b5c` ("fix disk-leak sources")
  changed `runtime_anchor(target, recipe, tmp_path)`'s signature and fixed the 9 call sites inside
  its own file, but 7 other test modules still call the 2-arg form. Mechanical fix, ~30 min.
- Remaining clusters (schema drift, stale mocks, two UNCLEAR clusters flagged as possibly real —
  `test_existing_cpu_run.py`'s iteration-status sequencing and `pool.prune_anchor_generations`
  call-count during legacy-keep pruning) are detailed in the triage file.
- No evidence found of an actual production bug in `serving.py`, `gates.py`, `longctx.py`,
  `model_identity.py`, or `serial_run.py`.

Handoff update: `handoffs/active/autokernel-unified-surface-program.md` → `AKU-RED-LOOP` (existing
box from 2026-09-17) refreshed with the new count and the triage pointer.

## 6. D9 hook false-positive fix

Landed as epyc-root `3d497622e`: `fix(hooks): D9 commit-hook false positive on heredoc/quoted
commit text` (operator batch, 2026-10-06). Already on `origin/main` as of this wrap-up's base.

## 7. Disk crisis (2026-10-07)

562 worktrees = 414 GiB, tmp = 255 GiB; free space fell to 86 GiB, below the 100 GiB build-
retention floor, and blocked the DS41 lane relaunch (§2). Cleanup was in progress at wrap-up time.
**Lesson, added to project docs**: wrap up at every task boundary, including scratch cleanup —
this is a recurrence-worthy failure mode, not a one-off.

## 8. Lessons — one landed, three BLOCKED by a hook (reported, not bypassed)

Four lessons were drafted for project docs:
(a) correctness work (calibration, op tests, input hashes, builds) needs no quiet host — shard it,
claim narrow build-role cpu lists, never take a full-host bench claim for it;
(b) `region-lock` takes `LOCK_EX` per region regardless of role, so per-shard claims serialize —
size shard count to the claimed cpu list (`min(16, cases, lock_cpus // 4)`), not the host;
(c) a served topology's taskset prefix defeats a narrowed lock unless the prefix itself is
rewritten to the lock's cpu list;
(d) wrap up at every task boundary, including scratch/worktree cleanup — the 2026-10-07 disk
crisis (562 worktrees / 414 GiB, tmp 255 GiB, free 86 GiB) blocked a lane launch and was caused by
exactly this gap.

**(d) landed**: `agents/shared/SESSION_LIFECYCLE.md` § Wrap-up cadence, new bullet citing the
562-worktree/414 GiB figure.

**(a)-(c) BLOCKED**: every attempt to edit `agents/shared/OPERATING_CONSTRAINTS.md` (the natural
home, § Inference and Benchmarks) and every attempt to edit
`docs/reference/agent-config/INCIDENT_LOG.md` (as a narrative-only alternative) was refused by
`scripts/hooks/agents_reference_guard.sh` with `BLOCKED: unresolved local markdown references`,
citing `docs/guides/agent-workflows/cleanup-reference-check.md`. Root cause: the guard resolves
bare markdown references against `${CLAUDE_PROJECT_DIR:-$(pwd)}`, which is the harness's own launch
directory (`/workspace`), not the lane worktree actually being edited
(`/mnt/raid0/llm/worktrees/root-wrapup-ak-20261007`, `origin/main` at `3d497622e`). `/workspace` was
one commit stale and does not contain `docs/guides/agent-workflows/cleanup-reference-check.md`,
which exists at the lane's own tip and is already referenced (pre-existing, unrelated to this
session's edits) in both `OPERATING_CONSTRAINTS.md` and `INCIDENT_LOG.md`. The guard scans the
*whole* post-edit file, so it refused every edit to either file regardless of content, not only the
new text. Per the wrap-up brief's hard rule ("If a permission or hook blocks you: STOP and
report"), this session did not bypass the hook (e.g. via `sed`/Bash, which the guard does not
intercept) — the lesson text for (a)-(c) is captured here verbatim for the owning/coordinator
session to apply directly once `/workspace` is current, or from a shell where
`CLAUDE_PROJECT_DIR` resolves to the lane actually being edited. This is itself worth filing as a
structural gap in `agents_reference_guard.sh` for worktree-based editing (it should resolve against
the edited file's own repo root, not the harness's launch cwd) — not a reason to route around the
guard.

### Prepared text for `agents/shared/OPERATING_CONSTRAINTS.md` § Inference and Benchmarks

Insert immediately before the line `- Full policy: \`agents/shared/MEASUREMENT_POLICY.md\` →
\`/workspace/MEASUREMENT.md\`.`:

```
- **Correctness work needs no quiet host; only timing does.** Calibration, op tests, input-hash
  verification and builds are correctness work: shard it and claim a narrow build-role cpu list
  (`region-lock run --cpu-list <list> -- <command>`), never a full-host bench claim. Only a TIMING
  measurement (a headline speed number, an A/B that compares rates) needs the exclusive quiet
  window. Treating a served-shape calibration like a timing run serializes it behind every other
  claim on the host for no correctness benefit. (origin: 2026-10-06/07 served-shape calibration,
  DS41/Q38FN — sharded under ONE build-role region-lock claim, research `1bace97d`/`a23af0a7`)
- **`region-lock` takes `LOCK_EX` per region regardless of role**, so sharded claims against the
  same region still serialize one shard at a time even though none of them is a timing run. Size
  the shard count to the claimed cpu list, not to the host's full core count — research `a23af0a7`
  confines shards to the lock's own cpu list and sets the default to `min(16, cases, lock_cpus //
  4)`. A shard count sized off `nproc` over-subscribes a narrow claim and serializes shards that
  should have run concurrently inside it.
- **A served topology's `taskset` prefix defeats a narrowed region-lock claim** unless the prefix
  itself is rewritten to the lock's cpu list. A process launched with a stale `taskset -c <wide
  list>` ignores a narrower claim taken around it — the claim is advisory to callers who read it,
  not an OS-enforced affinity change — so a narrowed lock produces no actual narrowing unless the
  launcher's own affinity argv is updated to match.
```

## Index rows

No new index row drafted — all touched handoffs (`deepseek-v41-flash-evaluation.md`,
`autokernel-all-devices-all-dimensions.md`, `autokernel-unified-surface-program.md`) already have
rows in `inference-research-index.md` / `routing-and-optimization-index.md`; only their bodies
changed. `python3 scripts/handoffs/index_state.py --check` run after edits (see wrap-up report).

## 9. FULL wrap-up 2026-10-07 (operator-invoked, agent `claude-ak-coordinator`)

Lane worktree `/mnt/raid0/llm/worktrees/root-wrapup2-ak-20261007` @ `lane/wrapup2-ak-20261007`,
built on top of `eef14e1d4` (this file through §8) and `5ccf4502b` (AK loop test triage). New facts
since those two landed:

### 9.1 Critic swap — both AK lanes now run with zero Claude models

2026-10-07 03:03Z: both AK lanes relaunched with the critic switched from `claude-opus-5-5` to
`gpt-6-astra@high` in all 4 common-args files under
`/mnt/raid0/llm/tmp/ak-lanes-relaunch-20261005/` (backups `*.bak-20261007-critic`). New-epoch
watchdogs, both under that same directory:
- `q38fn_watchdog3.sh` — state dir `state-6ed37a-*`, `LONGCTX=1`.
- `ds41_watchdog6.sh` — state dir `state-337615-*`, hold file `DS41_WATCHDOG6_HOLD`.

The common-args documents are part of `serial_run.py`'s continuation binding
(`serial_run.py:824-827`): any config edit (including a critic swap) needs a NEW-epoch watchdog,
never a continuation off the old one — seeding from an old continuation dies with "continuation
binding does not match its own original arguments". This is the same lesson as the §2 calibration
relaunch, now confirmed on a second, unrelated config change (critic model), so it generalizes to
*any* common-args edit, not just served-shape recalibration.

### 9.2 Q38FN forced SIGKILL mid-batch for an EC GPU window — pause granularity gap

Q38FN was stopped mid-batch at ~02:55Z for EC's Jet-Long GPU window. A control-endpoint pause only
lands at batch boundaries (one batch ≈ 3.4 h) — far too coarse for a window request. `SIGTERM` to
`serial_run` did not stop the `run.py` batch child within minutes; `SIGKILL` was needed (operator
authorized). EC then cancelled the window anyway, so the kill bought nothing this time, but the gap
is real and will recur.

- [ ] Task: give `serial_run`/`run.py` a pause or yield that lands at measurement granularity (one
  case, not one batch), so a GPU-window request doesn't need a kill. Filed under AK loop ownership
  — see index draft below (owning session applies).

### 9.3 Disk — delete_safe.sh run by the operator; crisis resolved

Updates ` §7 (the 86 GiB crisis)`: the operator ran
`/mnt/raid0/llm/tmp/disk-audit-20261007/delete_safe.sh`. Free disk is now **175 GiB** (was 86 GiB
at the crisis, 116 GiB after the coordinator's + EC's worktree cleanup). **No operator decision
item needed — this is DONE, not open.**

Still open from the same audit (`/mnt/raid0/llm/tmp/disk-audit-20261007/AUDIT.md`):
- [ ] Task: 207 of 606 worktrees audited were `codex-ni*/ni0X` lanes not cleaned up at ticket
  close — a process-fix (cleanup-at-close for that lane class), not a one-off deletion.
- EC's mid-cleanup removal of 2 coordinator worktrees (`ratify-token-rules-20261005`,
  `token-rules-record-20261006`) caused no loss — both were clean and on `origin/main`. No action
  needed; noted here only so it isn't re-investigated.

### 9.4 Lessons patch for OPERATING_CONSTRAINTS.md — BLOCKED a second time, confirms the guard defect

Re-attempted the §8 (a)-(c) insertion from this fresh lane worktree
(`/mnt/raid0/llm/worktrees/root-wrapup2-ak-20261007`, `agents/shared/OPERATING_CONSTRAINTS.md`,
inserting immediately before the `Full policy: agents/shared/MEASUREMENT_POLICY.md` line in §
Inference and Benchmarks). **Still BLOCKED** by `scripts/hooks/agents_reference_guard.sh`:

```
BLOCKED: unresolved local markdown references in .../agents/shared/OPERATING_CONSTRAINTS.md:
  - docs/guides/agent-workflows/cleanup-reference-check.md
```

Root-caused precisely this time: the hook resolves `PROJECT_DIR=${CLAUDE_PROJECT_DIR:-$(pwd)}`
(`scripts/hooks/agents_reference_guard.sh:8`), and `CLAUDE_PROJECT_DIR` is a harness-level
environment variable fixed to `/workspace` for the whole session — it is **not** reset by `cd`ing
into a lane worktree, and the Bash tool's `$(pwd)` fallback never applies because the var is set
(confirmed: `echo $CLAUDE_PROJECT_DIR` prints empty in a plain shell but the hook's own process
sees it non-empty and pointing at `/workspace`). `/workspace` genuinely lacks
`docs/guides/agent-workflows/cleanup-reference-check.md` at its current tip, while the lane
worktree (ahead of `/workspace`) has it. The guard scans the *whole* post-edit file against
`$PROJECT_DIR`, so **any** edit to `OPERATING_CONSTRAINTS.md` or `INCIDENT_LOG.md` is refused
regardless of content, for as long as `/workspace`'s checkout lags the lane doing the edit — which
is true of every lane worktree by construction (that's the point of a lane).

**Not bypassed** (no `sed`/sandbox workaround), per the hard rule. The lessons text for (a)-(c) is
still the exact text drafted in §8 above, unapplied. This has now reproduced twice on two different
lane worktrees against two different harness instances, which upgrades it from "a one-off" to a
structural defect:

- [ ] Task: fix `scripts/hooks/agents_reference_guard.sh` to resolve bare markdown refs against the
  edited file's own repo root (`git -C <file_dir> rev-parse --show-toplevel`), not
  `${CLAUDE_PROJECT_DIR:-$(pwd)}` — the latter is the harness's launch directory, not the worktree
  actually being edited, and is wrong for every lane-worktree edit to a governance file whenever
  `/workspace` lags the lane (always, for a lane ahead of main). Index row drafted below.

### 9.5 AK loop test triage — cluster 1+4 fix landed; cluster list refreshed

Research `58c86506` ("thread tmp_path through runtime_anchor() call sites; fix stale hold() stub")
landed and fixes both cluster 1 (357/451, the `runtime_anchor(target, recipe, tmp_path)` signature
mismatch across 7 modules) and cluster 4 (the gpu `hold()` stub). epyc-root `fedc411f3` records it
in `progress/2026-10/2026-10-07.md`.

Per-file rerun result: **172 pass, 5 fail**:
- 4x `test_existing_gpu_pool_uses_selected_requests_and_original_keep_owners` — now fails on
  `"keep_candidate"` vs `"kept"` after the R23-44 keep-gate change (`run.py:5876`); this reads as a
  stale-assertion-vs-intentional-behavior-change question, **needs an owner call**, not a
  mechanical fix.
- 1x ordering flake in `test_unified_worker.py`.

The full-suite rerun (`pytest autokernel/loop -q`, all ~5000+ tests) was **not completed** this
session. Still open, unresolved: clusters 2, 3, 5, 6, and the ~62-item long tail from the original
triage (`/mnt/raid0/llm/tmp/ak-test-triage-20261007/TRIAGE.md`).

- [ ] Task: full-suite rerun of `autokernel/loop` on origin/main (post-`58c86506`) to get a clean
  failure count before further triage.
- [ ] Task: owner call on the 4 keep-gate assertion failures (update test expectation to
  `"keep_candidate"`, or treat as a regression) — `run.py:5876`, R23-44.
- [ ] Task: triage clusters 2, 3, 5, 6 (lane-affecting: 3 and 5 per the operator's own flag) plus
  the long tail.

### 9.6 Q38FN REMEASURE_REQUEST — resolved by the new epoch

The `REMEASURE_REQUEST.json` filed for recipe `cff9ad900700…` (§3 above, the 6.528%-floor
contamination) is **no longer pending**: it is present only as
`REMEASURE_REQUEST.claimed-20261007T030349159542Z-1658951.json` under
`.../ak-q38fn-cpu-decode-20261003/store-b0ba1d427/runtime-source-floors/cff9ad9.../` — claimed at
03:03:49Z, i.e. consumed automatically when the lane relaunched on the new epoch (§9.1). No action
needed.

### 9.7 Research branch `fix/ak-longctx-identity-oracle-20261007` — still unlanded

Branch @ `6f116e55`, worktree `/mnt/raid0/llm/worktrees/research-ak-longctx-oracle-20261007`
(**KEEP** — do not clean up). Astra R22 change requests are addressed in the branch but it has not
yet been re-reviewed.

- [ ] Operator decision: wiring `check_cpu_fa_real_mask_identity` into `run.py` would block
  `cpu_fa_schedule` until the matching C++ change lands — not something to wire unilaterally. Index
  row drafted below (operator queue).
- [ ] Task: C++ follow-up — a probe `--mask-file` mode.
- [ ] Task: C++ follow-up — a DS41 top-k mask dump hook in llama.cpp.
- [ ] Task: C++ follow-up — regenerate `test-backend-ops-cpu-fa-longctx-v1.patch`.
- [ ] Task: get the branch re-reviewed by Astra now that R22 is addressed.

### 9.8 Memory / process rules adopted 2026-10-07 — not yet landed in project docs

Three rules adopted this session that belong in `agents/shared/SESSION_LIFECYCLE.md` (wrap-up
cadence) or `agents/shared/OPERATING_CONSTRAINTS.md` (subagent brief section), whichever already
hosts the nearest-matching section — not yet checked for duplication against current doc text:

1. Per-task wrap-up includes the task's own scratch cleanup (this generalizes the §8(d) lesson
   already landed about the disk crisis).
2. Every subagent brief requires: logs, progress, and handoff updates for its own work, then
   clearing its own scratch — **only if no longer needed**.
3. The main thread (not the subagent) decides scratch lifetime per brief.

- [ ] Task: land rules 1-3 above into `SESSION_LIFECYCLE.md`/`OPERATING_CONSTRAINTS.md` once
  `/workspace` has caught up past this lane (the §9.4 guard defect blocks editing those files from
  a lane ahead of `/workspace`, which this one is).

### 9.9 Wrap-up mechanics for this invocation

- Checklist-sync gate: all new tasks above are filed as `- [ ]` in this progress file, and mirrored
  into the owning handoffs in the same edit pass (see handoff updates below) rather than left as
  prose-only.
- Derived-actionables gate: every "task"/"owner call" conclusion above has a checkbox; none left as
  bare prose only.
- Index rows: PREPARED ONLY in this report (subagent constraint) — see `## Index pruning /
  handoff compaction` and the index-row diff in the wrap-up report. This session does not write
  index files.
- `scripts/hooks/agents_reference_guard.sh` blocked one governance-doc edit (§9.4); no other edits
  were blocked.

## 10. Consolidated harness checkpoint (2026-10-07 08:49Z)

The current consolidated candidate is private research commit `20870bf42e9dbd487cf50bf7e303122af323ee9f`, including the v3 physical-owner lifetime repair (`824320ac`). Its exact 62-source composition has independent SOURCE PASS: `consolidated-harness/roster-import-composition-final/ASTRA_FINAL_SOURCE_REVIEW.md` SHA-256 `90f2aeac4600876e73938f2f4e6723b40a493fea2c006fae34d9ef861ce99b5c`; the committed runtime manifest is `consolidated-harness/roster-import-composition-final/COMMITTED_RUNTIME_MANIFEST.json`, SHA-256 `6e78bb27847980bff6b9cf490f8c3ce57425f5e662ed30b462f1c3368deb129b`. The earlier `eedaf468c6b4b54ab3a1f3002506c5068645f103` source PASS was revoked after survivor-lifetime review and remains historical only.

The runtime driver separately received SOURCE PASS (`runtime-gate-prepared/ASTRA_RUNTIME_RUNNER_REVIEW.md`, SHA-256 `c0bb9355ac5d06eadae111f4d904c31208d813b06bc8e74ecef51c2b1b7d379d`, runner map `19c63c7f5096b1b37f6795c64a3e738819283d1d8f9b516a25c0052575bbecee`) and explicit ROOT runtime-only approval (`runtime-gate-prepared/ROOT_APPROVAL.json`, SHA-256 `cefc98518c7c940d5362c798d4b72a1e7429f2d9b8b30eb3b97cfde19bb72e5d`). One complete candidate job, `consolidated-20261007T084059Z-r1`, is queued under the q2 CPUs 50–57 build claim with 10,800-second admission. It runs the lifecycle control, 13 focused modules, then the full loop suite sequentially under that same claim. At this checkpoint no worker or pytest-entry receipt exists; no runtime PASS, integration, landing, activation, asset application, or performance claim is made.

The environment-roster tests had two preserved actual outcomes: the original import-root run was 5 failures/3 passes; after that fixture correction, r1 was 3 failures/5 passes from duplicate `cpu_screen` kwargs and the generated child affinity mismatch. Test-only corrections are privately committed as research `4efeccb187ee5a44561f7d167048b83de66e5522`; the original `50c4a829` worktree is clean. A single r2 retry is queued under q2 CPUs 48–49 build claim, launcher PID 2444478 / region-lock PID 2444481. Pytest has not started; no result is accepted.

Continuous watcher v4 and the controlled maintenance launcher remain active. The last authenticated one-shot showed both CPU lanes desired paused and observed pausing, with original workers alive. The 08:13 two-second descendant sample found DS41 in a remote authoring step; it does not prove later CPU availability or a resource grant. The 45-minute maintenance window starts only once both lanes are actually paused. GitNexus ratings remain advisory under the operator's explicit override: report risk information, but do not treat ratings as a stop gate.

An OP80 canonical CPU build boundary has since passed: ROOT accepted `OP80_CPU_BUILD_ACCEPTED.json` (SHA-256 `08304fcd564d4316ba3f733c928f242b3571d6cba60c898c6789bf43793aa2dd`) for source `8393305bcc68395ee531bd19ad911b980298efc9`, clean tracked state, and original native build RC 0. The attested `libllama.so` and `llama-server` digests are `9e0e23c23b8ab982b039d5b5d3c56ff69fcab945df0987a1dd14a3948e11ecbf` and `a044447afbaf888af9031362202ee878348e179c058f7c5d0855910e8c80ce7f`; version is `10345 (8393305bc)`. This proves the canonical CPU build, compiled capture knobs and own-tree linkage only; it does not prove HIP residency, model validity, real-mask capture or promotion. Python OP80 candidate `896…` remains queued without an accepted runtime result. Current native status still shows q0–q3 held by the two AutoKernel CPU lanes and gpu-quiet shared by PIDs 1658951/1659007. The consolidated-suite and roster-r2 jobs remain queued for a later resource boundary; no measurement is interrupted.

No handoff task was completed by this checkpoint, so no task checkbox was changed. No index row was edited; the owning session applies generated index state after review.

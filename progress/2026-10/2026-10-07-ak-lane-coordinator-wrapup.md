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

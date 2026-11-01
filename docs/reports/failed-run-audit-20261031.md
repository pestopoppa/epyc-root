# FAILED-RUN root-cause audit — compute calendar, 2026-10-28 … 2026-10-31

Author: workspace-58 audit subagent (read-only). Scope: every `FAILED-RUN` receipt in
`/mnt/raid0/llm/tmp/compute-flags/filing-done/*.FILED` (405 receipts, **135 FAILED-RUN**), cross-read against
`grants/<id>.ended`, `ready/{armed,refused}/<id>.json`, `ready/<id>.launcher.out`, `ready/<id>.smoke.log`,
`filing-due.jsonl`, each run's `scratch_root` logs, the keeper (`ws58-calendar-keeper-v7e.sh`), `ws58_arm-v2.py`,
`grant_ok_launcher.py`, `scripts/coordination/{dryrun_check,validate_fillers,qualified_idle_probe}.py`, the engine
copies (`filler_run12/13.sh`), `LOOP-CONTRACT.md`, `OWNER-RULINGS-20261028.md`, `OWNER-ORDER-20261029.md`.
Four forensic subagents read the per-run logs; where a receipt and the log disagree, the log wins and the appendix says so.

---

## 0. Headline

* **135 of 405 filed runs (33 %) produced no science.** Per day (by `.ended` time): 10-28 44/77, 10-29 46/107,
  10-30 14/145, 10-31 31/76. The receipts **undercount**: `grants/*.ended` with rc not in {0,75} were 45, 60, 65, 35 on
  those days — rows that re-armed under the same id overwrite `.ended`, and reused ids make 7 receipts describe a
  different attempt than the final one (`fa4-c5-exact-set-r2`, `codex-hsf5p-restore`, `fa4-output-location`,
  `odl-quad-s3`, `paw-compact-b-hostfix2`, `pip02-fresh-s0/s1`).
* **In no case did a model or kernel regress.** Every failure is a harness/plumbing fault at one of three places:
  the **entry** (grant-time refusal, placement/custody, environment divergence), the **window end** (partial
  coded as rc1) or the **finish line** (completion predicate / validator after the native job succeeded).
* **Seven families cover 90 % (122/135); six cover 82 %.** Table in §1.
* **The keeper trusts a self-reported smoke.** `ready_scan()` admits a manifest when `smoke.exit_ok`,
  `first_request_ok`, `result_writer_ok` are literally `true` and `ran_at` < 24 h. Nothing verifies that the smoke ran
  the launcher at `launcher.sha256`, in the namespace the grant runs in, through the keeper's own invocation line, or
  that the completion predicate was ever exercised. Every one of the 10-31 failures carried a passing `smoke{}` block.
* **The right mechanism already existed and was switched off.** `dryrun_check.py` (T1, 2026-10-27) is a hash-bound
  "same entry, same launcher, same engine, nonce-bound isolated grant" proof (`epyc.dryrun.pass.v1`). It had two
  defects — it ran **at grant time inside the launcher** (so a refusal burned the slot and produced a FAILED-RUN) and it
  proved only admission, never completion — and after four self-refusals on 10-28 `OWNER-ORDER-20261029.md` ordered
  "**no T1 dryrun admission**". It was removed rather than moved pre-grant. 29 receipts (21 %) are that self-refusal;
  four of them date **after** the order because the engine exists as seven divergent forks (`filler_run13.sh` sha
  `e940173f`, `5f970f50`, `cea416b0`, `29b88da4`, `7fa4d3f0`, `37c8a53d`, `b2bd7c6d` across 161 armed launcher dirs).
* **The owner-action items never became an enforced rule.** They did become prose: the 10-29 order's "Every manifest
  (no exceptions; each item caused a failure yesterday)" list names eight of this report's nine families. No line of
  it is checked by the keeper, the arm script, or the validator. The keeper alarms on exactly one kind: `idle` (464
  alerts, 0 failure alerts). The scoreboard counts READY manifests per hour and never counts failed grants.

---

## 1. Root-cause families (by mechanism, not by self-reported class)

| # | Family | n | % | first → last | Structural guard (where) | Cost |
|---|---|---|---|---|---|---|
| C | **Grant-time self-refusal** — T1 `dryrun_check` inside the launcher refuses at grant: disk free-after-output < 150 GiB floor (15), missing proof fields `dryrun_pass/launcher_path/job_path/source_manifest` (7), `malformed claimed_cpus` (4), min-window / window alignment (3). Zero compute, but the grant is consumed, the row is FAILED, the worker republishes under a new id. | 29 | 21 % | 10-28 → 10-31 | Move the proof **before** the grant (keeper `ready_scan`, §3.1) and make disk shortage a **WAIT state**, never a failure: keeper parks the row (`READY-WAIT-DISK`) when `free − est_output_GiB < floor` and never starts the launcher. Refuse at arm time any row whose `claimed_cpus` does not parse or whose `min_window_s` is not minute-aligned. | keeper: ~40 lines |
| B | **Finish-line failure after the native job succeeded** — `filler_run13.sh:309-310` demotes rc0 to rc1 `incomplete` whenever `--complete-cmd` is absent (6: `c6-gpu-build`, `c6-cpu-iqkfa`, `c6-35186`, `c6-gak-diag`, `gnx-r4`, `kpf181`); post-run validators/projectors/evidence gates crash on their own output (`projector.py` PROTOCOL path, `complete_guard.py:135`, tuple/list compare, pair-order compare, `OutputParseError` on an interleaved stderr line, `native_tensor_width…` guard ×3, `validate_build.py` byte compare, `unit.py` AUC count). Results are valid on disk; 2266 s (27b-identity), 2497 s (rtg57-repair), 2455 s (inf50-r13) of compute each thrown away. | 25 | 19 % | 10-28 → 10-31 | (1) Engine refuses to **start** (rc 65, pre-grant, in qualification) when `COMPLETE_CMD` is empty — rc0-without-predicate becomes impossible. (2) Qualification runs the **real** entry on a tiny fixture and asserts `is_complete` returns 0 on the fixture's result (§3.1 `completion`). (3) Validators run as a separate `--validate-only` step the filer can replay against retained output; a validator failure after `NATIVE_COMPLETE` is filed as `VALIDATOR-FAILED`, keeps the native result, and never re-burns compute. | engine template: ~30 lines; qualification: part of §3 |
| D | **Placement / custody mismatch at entry** — declared vs granted CPUs (`claimed_cpus=24-47` on an `any-cpu-quarter` row granted q3), no `taskset -c "$FILLER_CPUS"` (hsf5p ×2), `--cpu-list 96-119` maps to no region, nested gpu-quiet device claim, `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` missing, quarter flock owner absent / "lock lost" (inf50 r7/r8, oolong v33), `expected_cpus: unbound variable` only set on the smoke branch, port 18991 taken 2 s earlier by a sibling row, live DS41 server from another lane, admission lost mid-run (paw-standard-a-t1), pidfd/exe custody vanished (fa4 r2/r13), admission timeouts (pip02 r11 ×3). All died in 3–30 s except where custody was lost mid-run. | 19 | 14 % | 10-28 → 10-31 | Keeper static checks at arm: a relocatable row may not carry a fixed `claimed_cpus`; a launcher must contain the literal `taskset -c "$FILLER_CPUS"` or `--claim-cpus "${WS58_REGIONS}"`; manifest declares `ports`, `exclusive_class` (e.g. `ds41`), `shared_state` keys — keeper refuses overlapping ports among READY/armed rows, serialises `shared_state`, and never co-grants two `exclusive_class` rows (ONE-DS41 rule becomes mechanical). Qualification runs with a **synthetic grant whose regions differ from the smoke's** so hard-coded CPUs fail before a grant. | keeper: ~60 lines; manifest schema +3 fields |
| I | **Application / model level** — Paddle `vlm` worker "Connection error" + "native page layout changed" (pip02 fresh/odl/r4 ×7), 130 000-token request vs 32 768 slot (jetlong), GPU server `std::bad_alloc` (m4-gpu-quality), worker SIGSEGV (r28-head), C5 baseline MUL_MAT property failure (gak-full), embedding servers unavailable (ufh12-r1), 6/18 invalid pairs declared by the job itself (td29-r4), barrier timeout (w1-r10). These are the only receipts that carry information about the science. | 14 | 10 % | 10-28 → 10-31 | Not a calendar defect. Guard: qualification's **first real request** must use the production prompt length / `n_ctx` declared in the manifest (catches jetlong-type); td29-r4-type "job says invalid" must be filed as a **diagnostic result**, not FAILED-RUN (filer rule). | filer brief: 2 lines |
| E | **Window end coded as failure / infeasible item** — yarn-cpu-fixed120 s0-s3 (2 h) and v3 s0/s1/s3 (8 h) all `TimeoutError` on the **first** 131 072-token item (prefill ≈ 3.7 tok/s; ~39 quarter-hours for 0 items); `checkpoint_controller.py:36 Refusal('insufficient window')` and `bootstrap.py:166 RuntimeError('worker failed, retained for resume')` exit rc1 instead of rc75 (hil15-private s0/s2/s3, hil15b-heavy-r2); `.ended` rewritten rc1 over a launcher-reported rc75 (hostfix2). | 12 | 9 % | 10-28 → 10-31 | Qualification forces a short deadline and asserts **exit 75 + partial=true** (`rc75` block). Keeper computes feasibility from manifest fields `items`, `tokens_per_item`, `measured_tok_s` (the qualification's measured rate) and refuses `items×tokens/tok_s > window_s`. Engine maps any non-zero exit after `deadline_reached` to 75. | qualification + keeper: ~30 lines |
| F | **In-job disk floor after admission passed** — job floors of 151 GiB (`validate_entry`, pip02 `odl_quad_batchpage.py:26`), 155 GiB (`native_entry`) vs admission floor 150 GiB; mid-run breach kills (`DISK_FLOOR_BREACHED`, rtg57-t96 after 26 min whole-host; kpf18-r2 rc143 after 2689 s). Free space sat at 145–158 GiB all week. | 12 | 9 % | 10-28 → 10-31 | One floor, one file: jobs read `scripts/coordination/dryrun_disk_policy.json`; qualification records `job_floor_gib` and refuses if ≠ policy. Keeper parks (does not grant) while `free − est_output − 2 GiB margin < floor`. Mid-run breach exits 75 (partial), never 1/143. | policy plumbing: ~20 lines per engine |
| A | **Environment divergence between smoke and run** — launchers execute through `sudo -n chroot /proc/1/root setpriv … env -i` into the **host** rootfs (65 of 309 armed launchers), while smokes run in the devcontainer: `/workspace/repos/epyc-orchestrator/scripts/region-lock` not found (rc127 ×3, paw), `cd /mnt/micron/codex3-lanes/orchestrator` gone (`region-lock.sh:3`, prbt4), `rg: command not found` after a 315-step build (akxall8), venv interpreter / `dateutil` absent, shared venv modified mid-run (discovery-s1), old capsule shadowing `sys.path` (private-s1-r11), `--epyc-root` worktree lacking `l2_scan_capture.py`, `launch.sh:47` rejecting the forwarded `--job` argv (r13-pid), HF cache missing under `env -i` (standard-a-resume). | 11 | 8 % | 10-28 → 10-31 | Qualification is executed by the **keeper, with the keeper's exact invocation line** (`cd compute-flags && setsid bash <launcher>`), so the launcher's own chroot/env path is what gets exercised; receipt records an **exec-namespace fingerprint** (root inode, `uname -r`, `command -v` of every tool in manifest `requires_tools`, interpreter path+sha, cwd exists) and the keeper refuses a grant if the fingerprint at grant time differs. | qualification runner: core of §3 |
| G | **Stale pin / identity inside the launcher** — frozen cohort path compare against a hard-coded original (yarn-128k-r10), removed `BUILD-RECEIPT-PATH` (w2, w3), `pool.py` checks r26 id while grant is r27 (×2), C5 guard accepts only the predecessor id (inf50-r2), shared `~/.gitnexus` registry mutated by a co-scheduled row (inf50-r3), smoke `outer.log` left in `results/` so "non-resumable results dir exists" (inf50-r4), `REFUSED: review-seal` at `job.sh:7`. | 9 | 7 % | 10-28 → 10-31 | Qualification runs under the **row's real id and the real packet paths** (not a smoke id), so predecessor-id guards and stale paths fail before the grant; the receipt is invalidated by the keeper if any file in `source_manifest` changes sha (already implemented in `dryrun_check.checked_manifest`). Smoke residue: qualification runs in a nonce-bound scratch copy of `results/`. | part of §3 |
| H | **Owner-retired / STOP / superseded / stale receipt** (not defects) | 4 | 3 % | 10-28 → 10-29 | Filer rule: `owner-retired` and `stop-file-before-start` are `WITHDRAWN`, not `FAILED-RUN`. | filer brief |

Cross-tab against self-reported class: `harness` (73) splits into B 24, E 11, A 10, G 9, D 7, I 6, C 4, F 2;
`disk-floor` (24) is C 15 (never ran) + F 7 (ran, then died) + 2 others; `admission` (15) is C 7 + D 7 + E 1;
`unknown` (10) is I 7 + B/F/H 3. The self-reported classes are not actionable because the same word ("harness",
"disk-floor") names opposite mechanisms (never-started vs killed-after-26-minutes).

---

## 2. Why the existing checks did not prevent this

| Check | What it actually verifies | Why it let these through |
|---|---|---|
| keeper `ready_scan()` (`ws58-calendar-keeper-v7e.sh:292-345`) | JSON parses; `hold` null; `smoke.ran_at` < 24 h; `smoke.{first_request_ok,result_writer_ok,exit_ok} == true`; `launcher.sha256` matches the file; no `.complete`/`.grant`; `row.md` exists; reap-gate (`scratch_root`, `keep`); `regions/window_s/gib` present. | The smoke block is **author-asserted booleans**. Nothing ties `smoke.log` to the launcher sha, to the engine sha, to the exec namespace, or to the row id. `smoke.launcher_sha256` is present in some manifests and **not compared**. No completion-predicate field exists. All 31 failed 10-31 rows had `exit_ok:true`. |
| `ws58_arm-v2.py` | 18-cell row shape; conditional/blocker text; reap-gate repeat; `est_output_GiB` present; no private ≥500 MB model copies; `validate_fillers --for-grant`; `grant_ok_launcher` pid/regions. | Row **syntax**, not launcher **behaviour**. |
| `validate_fillers.py` | FILLERS.md cell grammar (18 cells, status token, RAM number, class, window). | Same — a well-formed row for a broken launcher passes. |
| `grant_ok_launcher.py` | Launcher pid alive; its engine argv parses; `--regions` cover the claim. | Reads argv, cannot see that `COMPLETE_CMD` is empty or that `$WORKDIR=/workspace` does not exist in the chroot. |
| `dryrun_check.py` (T1) | Hash-bound proof that **this** launcher+job+engine+checker+policy+source set reached the `boundary()` call under a nonce-bound synthetic grant, with CPU scope and disk check. **This is 70 % of the guard this report asks for.** | (a) Invoked **inside the launcher at grant time** → a refusal is a FAILED-RUN that burned the slot (29 receipts). (b) Proves admission only; no completion predicate, no rc75 path, no exec-namespace fingerprint. (c) Disk floor is evaluated at grant, when the only remedy is to fail. (d) `OWNER-ORDER-20261029.md` banned it ("no T1 dryrun admission") instead of relocating it; four forks kept it anyway. |
| `qualified_idle_probe.py` | Fail-closed adapter over the tmux idle probe (is an agent idle?). | Unrelated to run qualification; name collision only. |
| engine `filler_run12/13.sh` | region-lock claim, deadline, cleanup, `is_complete()` = `cd $WORKDIR && bash -c "$COMPLETE_CMD"`; rc0 and not complete → rc1 `incomplete`. | `COMPLETE_CMD` optional, `WORKDIR` defaults to `/workspace` (container path), seven forks with different line numbers and semantics; no smoke/qual mode exists in the engine, so every "smoke" is a separate code path written per packet (`FILLER_SMOKE`, `G2_MODE=smoke`, `--preflight`) — which is exactly where `expected_cpus` was set only on the smoke branch and `launch.sh:47` accepted one argv form. |
| `LOOP-CONTRACT.md` / `OWNER-ORDER` "Every manifest" list | The correct rule set, in prose. | Nothing executes it. The order simultaneously set **publishing quotas** (NI ≥ 3, codex3 ≥ 4 READY manifests per hour; "Failed-row repairs count toward quota: republish under a new id"). A failed row therefore *scores*; a qualified one costs an hour. 10-31's 31 failures followed the quota, and the SCOREBOARD has no failure column. |

---

## 3. The guard: mandatory pre-grant qualification, hash-bound, executed by the keeper

### 3.1 Contract

A READY manifest is grantable **only if** `<scratch_root>/qualification/QUAL-<id>.json` exists, validates, and
is bound to the current launcher, engine, manifest and exec namespace. The keeper itself runs the qualification
(a worker cannot forge it) through the **same code path it uses to start a granted launcher**:

```
cd /mnt/raid0/llm/tmp/compute-flags && WS58_QUAL=1 WS58_QUAL_NONCE=<nonce> WS58_REGIONS=<qual-regions> \
  setsid bash <launcher.path> >> ready/<id>.qual.out 2>&1
```

with a **synthetic grant** `qual/<nonce>/grants/<id>.grant` (`regions=<qual-regions> start=… end=…`, window =
`min_window_s + 300`), `FILLER_GRANTS_DIR=qual/<nonce>/grants` (the nonce-bound isolation `dryrun_check.py`
already understands), and `<qual-regions>` = two SMT siblings from a quarter that differs from any fixed CPU list in
the manifest (R11 slot, no region-lock; the engine's region-lock claim is redirected by `WS58_QUAL=1` to a
mapping-only plan). The launcher must, in qual mode:

1. run its **real** admission (`dryrun_check admit`) against the synthetic grant;
2. run the **real job entry** on the fixture named by manifest `qual_fixture` (≤ 60 s, ≤ 300 s with model load),
   writing to the real `result_path` under a nonce-bound results dir;
3. hit a **forced deadline** on a second fixture item and exit **75** with `partial=true`;
4. let the engine evaluate `is_complete` on the fixture result (must return 0).

The engine (one canonical copy, §4.2) writes the receipt; the keeper verifies it.

### 3.2 Receipt schema — `epyc.qual.pass.v1`

```json
{
  "kind": "epyc.qual.pass.v1",
  "id": "<row id>",
  "nonce": "<32+ hex, keeper-generated>",
  "ran_at": "2026-10-31T19:02:11Z",
  "ran_by": "ws58-calendar-keeper",
  "manifest_sha256": "<sha of canonical-JSON manifest minus qualification/keeper_log/hold>",
  "launcher_path": "/mnt/raid0/llm/tmp/<pkt>/launch.sh", "launcher_sha256": "…",
  "engine_path": "/mnt/raid0/llm/tmp/<pkt>/engine/filler_run14.sh", "engine_sha256": "…",
  "job_path": "…", "job_sha256": "…",
  "source_manifest_sha256": "…",
  "policy_sha256": "<sha of dryrun_disk_policy.json>",
  "exec_namespace": {
    "mode": "host-chroot|container",
    "root_inode": 2, "kernel": "6.14.0-37-generic",
    "cwd": "/mnt/raid0/llm/tmp/<pkt>", "cwd_exists": true,
    "interpreter": {"path": "/mnt/raid0/llm/venv/bin/python3", "sha256": "…", "version": "3.11.9"},
    "tools": {"rg": "/usr/bin/rg", "taskset": "/usr/bin/taskset", "region-lock": "/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock"},
    "env_fingerprint_sha256": "<sha of sorted PATH,HOME,LD_LIBRARY_PATH,VIRTUAL_ENV as seen by the job>"
  },
  "admission": {"rc": 0, "grant_regions": "q1", "claimed_cpus": "any-cpu-quarter", "taskset_literal_present": true},
  "fixture": {"path": "…", "sha256": "…", "items": 2},
  "first_request": {"ok": true, "wall_s": 12.4, "n_ctx": 32768, "prompt_tokens": 1800, "measured_tok_s": 41.2},
  "result_writer": {"ok": true, "result_path": "…", "sha256": "…"},
  "completion": {"complete_cmd_present": true, "is_complete_rc": 0},
  "rc75": {"forced_deadline_s": 20, "exit_code": 75, "partial_flag": true, "ended_line_sha256": "…"},
  "disk": {"job_floor_gib": 150, "policy_floor_gib": 150, "est_output_gib": 3.0},
  "ports": [18991], "exclusive_class": null, "shared_state": [],
  "children_drained": true,
  "receipt_sha256_excluding_self": "…"
}
```

Validity (keeper side, all must hold or the manifest is `READY-SKIP qual:<reason>`): every `*_sha256` equals the
file on disk now; `manifest_sha256` equals the manifest now; `nonce` is one the keeper issued and has not reused;
`ran_at` < 24 h; `admission.rc == 0`; `completion.complete_cmd_present && is_complete_rc == 0`;
`rc75.exit_code == 75 && partial_flag`; `disk.job_floor_gib == policy_floor_gib`; `exec_namespace` equals the
fingerprint the keeper re-takes at **grant** time (cheap: `stat -c %i /`, `command -v` list, interpreter sha via the
same chroot line); `first_request.n_ctx >= manifest.n_ctx_required`; feasibility
`manifest.items × manifest.tokens_per_item / first_request.measured_tok_s ≤ window_s`.

### 3.3 Keeper integration (`ws58-calendar-keeper-v7e.sh`)

* `ready_scan()`: replace the `smoke` block check with `qual_ok(rid)` (Python, ~80 lines, importable from
  `scripts/coordination/qualify_launcher.py --verify`). Keep the existing checks that remain useful (hold, launcher
  sha, reap-gate, regions/window, `.complete`/`.grant`). Add static refusals: relocatable regions + fixed
  `claimed_cpus`; missing `requires_tools`/`qual_fixture`/`ports`; engine sha not in
  `compute-flags/engine-allowlist.json`.
* New pass `qualify_pending()` before `ready_arm()`: for each manifest with no valid receipt and `hold == null`, if
  an R11 pair is free and fewer than `QUAL_MAX_CONCURRENT` (2) qualifications run, issue a nonce and start the
  qualification (above). Outcome → `ready/<id>.qual.out` + receipt, or `READY-SKIP qual-failed:<reason>` written
  into `keeper_log` and a `kind:"qual-failed"` line in `ws58-keeper-alerts.jsonl`. **The worker fixes and
  republishes; the keeper never grants an unqualified row.**
* `ready_arm()`: before `setsid bash "$launch"`, re-take the exec-namespace fingerprint and compare; on mismatch
  `READY-SKIP qual-stale:namespace`. Replace the disk refusal path: compute `free − gib − 2` and if `< floor` log
  `READY-WAIT-DISK` and `continue` (the launcher is **not** started, no grant file, no FAILED-RUN).
* New alert kinds: `qual-failed`, `run-failed` (every `.ended` rc not in {0,75}), `worker-breaker` (≥ 3 `run-failed`
  for one `owner` in 24 h ⇒ that owner's READY rows get `hold:"breaker"` until a fresh qualification passes).
* `write_ended` in the engine is the single writer of `.ended`; the keeper refuses to re-arm an id whose `.ended`
  already exists (new id required) — stops `.ended` overwrites that made receipts stale.

### 3.4 Where each guard lives, and cost

| Guard | Lives in | Est. |
|---|---|---|
| Qualification runner + verifier (`qualify_launcher.py run/verify/fingerprint`), receipt schema, nonce store | `/workspace/scripts/coordination/qualify_launcher.py` (new, ~350 lines; reuse `dryrun_check.py` helpers `cpus`, `grant_cpus`, `checked_manifest`, `sha`) | 1 Codex day |
| Keeper: `qual_ok`, `qualify_pending`, WAIT-DISK, fingerprint re-take, alerts, breaker | `compute-flags/ws58-calendar-keeper-v7e.sh` → `v8.sh` (~150 lines changed) | 0.5 day |
| Canonical engine `filler_run14.sh`: `COMPLETE_CMD` required (exit 65 at start); `WORKDIR` must exist in exec ns; `WS58_QUAL` mode (dry claim, fixture, forced deadline, receipt); all refusals exit 70/75/64, never 1; mid-run disk breach → 75 | `/workspace/scripts/coordination/filler_run14.sh` (new, from `filler_run12.sh`) + `compute-flags/engine-allowlist.json` | 0.5 day |
| Manifest schema v2 (`requires_tools`, `qual_fixture`, `ports`, `exclusive_class`, `shared_state`, `n_ctx_required`, `items`, `tokens_per_item`) | `compute-flags/LOOP-CONTRACT.md` + `scripts/coordination/ready_manifest.schema.json` (new) | 0.25 day |
| Filer: enum `root_cause_family` (A–I), `WITHDRAWN`/`VALIDATOR-FAILED`/`DIAGNOSTIC-RESULT` outcomes, JSON receipt lines | `.claude/skills/coordinator-agent/references/compute-owner-takeover.md` + `scripts/coordination/failed_run_rollup.py` (new, ~120 lines → `compute-flags/FAILED-RUN-ROLLUP.md`) | 0.25 day |
| Scoreboard: add `failed-24h` and `qualified-science-runs` columns | `compute-flags/ws58-scoreboard-v3.sh` | 0.25 day |

Total ≈ 2.5–3 Codex days. Expected first-day effect: every family except I goes to zero at the grant boundary;
I remains (it is the science).

---

## 4. Implementation spec (for a Codex session)

### 4.1 `scripts/coordination/qualify_launcher.py`

```
qualify_launcher.py run    --manifest ready/<id>.json --nonce N --regions 122-123 --out <scratch_root>/qualification/QUAL-<id>.json
qualify_launcher.py verify --manifest ready/<id>.json [--fingerprint-now]   # exit 0 ok / 2 refused (+reason on stdout)
qualify_launcher.py fingerprint --launcher <path>                         # prints exec_namespace JSON as the launcher's chroot line sees it
```

`run`: creates `compute-flags/qual/<nonce>/{grants,results}`, writes the synthetic grant, exports
`WS58_QUAL=1 WS58_QUAL_NONCE WS58_QUAL_RESULTS FILLER_GRANTS_DIR WS58_REGIONS`, executes **exactly**
`cd /mnt/raid0/llm/tmp/compute-flags && setsid bash <launcher>` (same as `ready_arm`), waits ≤ `qual_timeout_s`
(default 300, 600 with a model), collects `qual/<nonce>/receipt-partial.json` written by the engine, adds the
fingerprint and hashes, writes the receipt, deletes `qual/<nonce>` except the receipt.
`fingerprint` discovers the chroot line by executing the launcher with `WS58_FINGERPRINT_ONLY=1` (the engine
prints the JSON from inside its exec namespace and exits 0) — this is what makes host-chroot divergence visible.

### 4.2 `scripts/coordination/filler_run14.sh` (canonical; forks refused by allowlist)

Changes vs `filler_run12.sh`:
* `[ -n "$COMPLETE_CMD" ] || { log "REFUSED: --complete-cmd required"; exit 65; }` before any grant poll.
* `[ -d "$WORKDIR" ] || { log "REFUSED: workdir $WORKDIR absent in exec namespace"; exit 65; }`.
* `WS58_FINGERPRINT_ONLY=1` → print `exec_namespace` JSON (root inode, `uname -r`, `pwd`, `command -v` for each
  `--requires-tool`, interpreter path/sha/version, env fingerprint) and exit 0.
* `WS58_QUAL=1` → region-lock claim replaced by `region-lock plan --cpu-list …` (mapping check only); job run with
  `FILLER_QUAL_FIXTURE=<path> FILLER_RESULTS_DIR=$WS58_QUAL_RESULTS`; second run with `FILLER_DEADLINE=now+20s`
  expecting 75; `is_complete` evaluated against the fixture result; partial receipt written.
* Every refusal path exits 70 (admission), 64 (placement), 75 (deadline/partial/disk-breach-mid-run), 65 (template
  precondition). rc1 is reserved for the job's own non-zero exit, and `reason` carries the job's last stderr line.
* `write_ended` refuses to overwrite an existing `.ended` (exit 66) — a re-arm needs a new id.

### 4.3 Keeper patch points (`ws58-calendar-keeper-v7e.sh`)

* L292-345 `ready_scan`: drop the `smoke` block (L304-311); add `qual_ok` call; add static refusals listed in §3.3.
* New `qualify_pending()` inserted before `ready_arm` in `tick()` (L797).
* L420-440 `ready_arm`: WAIT-DISK branch before `setsid`; fingerprint compare; alert emission.
* L85-120 `rearm_rc75`: unchanged, but `.ended` overwrite now impossible.

### 4.4 Test cases (fixtures copied from the real failed packets; each must be refused **before** any grant)

| # | Source receipt | Fixture | Expected |
|---|---|---|---|
| T1 | `codex3-paw-compact-a-20261030` (rc127) | launcher whose chroot line calls `/workspace/repos/epyc-orchestrator/scripts/region-lock` | `qualify run` → engine rc127 inside chroot → `READY-SKIP qual-failed:tool-missing region-lock` |
| T2 | `refactor-c6-gpu-build-729599d69-20261030`, `codex3-kpf181-cpu-r1-20261031` | `calendar.sh`/`launch.sh` without `--complete-cmd` | engine exit 65 → `qual-failed:complete-cmd-missing` |
| T3 | `refactor-akxall8-c5-cpu-build-r5-20261031` | manifest `requires_tools:["rg"]`, host chroot lacking `rg` | fingerprint `tools.rg == null` → refused |
| T4 | `refactor-ufh12-r1-irt-r2-20261031` | `regions:"any-cpu-quarter"`, row notes `claimed_cpus=24-47` | static refusal `relocatable-with-fixed-cpus` |
| T5 | `codex-hsf5p-restore-r2-20261028` | `launch.sh` without `taskset -c "$FILLER_CPUS"`, qual regions 122-123 ≠ smoke 184-185 | admission affinity mismatch under the synthetic grant → refused |
| T6 | `yarn-cpu-fixed120-v3-s0-20261027` | `items:120, tokens_per_item:131072`, qual `measured_tok_s:3.7`, `window_s:28800` | feasibility refusal (4.2 M s ≫ 28 800 s) |
| T7 | `refactor-01a16fc3-hil15-private-s0-20261028` | `checkpoint_controller` raising `Refusal` at deadline | `rc75.exit_code != 75` → refused |
| T8 | `inf75-w5s-current-census-r2-20261029` | job floor 151 vs policy 150 | `disk.job_floor_gib != policy` → refused |
| T9 | `codex-hil15-s0-resume-v1-20261029` (disk 149.23 < 150) | free space fixture below floor | keeper `READY-WAIT-DISK`, launcher never started, no `.ended`, no FAILED-RUN |
| T10 | `yarn-128k-mi210-sol-r10-20261031` | `normal_entry.py:237` hard-coded cohort path | real-id qual run hits the compare → refused |
| T11 | `dtap-finance-action-reversal-q2-r1` | two manifests `ports:[18991]` | second one `READY-SKIP port-overlap` |
| T12 | `codex3-lb49-fu03-cli-r1-20261031` | manifest `exclusive_class:"ds41"` while a `ds41` grant is live | not granted until the live grant ends |
| T13 | `codex-ni-inf50-writerrace-resume-r3-20261029` | two manifests `shared_state:["~/.gitnexus"]` | serialised, never co-granted |
| T14 | `codex-ni-inf12-gate2-triton36-r5-20261028` | `expected_cpus` set only under `G2_MODE=smoke` | qual runs the **normal** branch → `unbound variable` → refused |
| T15 | `codex-hil15-s2-r13-pid-20261031` | `launch.sh` accepting `--job` only with `$# == 1` | qual forwards the engine's real argv → exit 64 → refused |
| T16 | `codex-ni-jetlong-small4x-paired-20261030` | `n_ctx_required:130000`, first request n_ctx 32768 | refused `n_ctx` |
| T17 | `codex-ni-inf50-writerrace-resume-r4-20261029` | smoke residue in `results/` | qual uses nonce-bound results dir; real run's `results/` untouched → passes; regression test that residue is not created |
| T18 | `refactor-c6-gpu-27b-identity-729599d69-20261031` | validator raising after `NATIVE_COMPLETE` | filer emits `VALIDATOR-FAILED`, keeps native result; `--validate-only` replay reproduces the error offline |
| T19 | negative control | a manifest whose receipt is hand-edited to `is_complete_rc:0` | `receipt_sha256_excluding_self` / nonce mismatch → refused |
| T20 | negative control | launcher edited after qualification | `launcher_sha256` mismatch → refused |

Acceptance: run the 20 fixtures under `WS58_READY_DIR` fixture mode (the keeper already supports the override);
`ws58-calendar-keeper-v8.sh --dry` must show 0 `READY-ARM` for T1–T16, T19, T20 and 1 for T17.

---

## 5. Why filing did not turn the pattern into a rule

1. **Receipts are free text with a four-word class vocabulary.** "harness" covers nine different mechanisms (§1
   cross-tab). No field names the family, the phase, or whether compute was burned; 34 receipts say only
   `job-rc-1:exited; owner reads job log`. Nothing can aggregate them, and nothing did.
2. **Owner actions are per-row and addressed to the row's owner.** "fix launch-v5-s1.sh --workdir", "add the four
   proof fields", "make the in-run disk refusal exit rc75" — all correct, all applied to one packet by one Codex
   session, none fed back into the engine the next packet was forked from. Seven engine forks is the physical trace
   of that: fixes landed in one fork at a time.
3. **The one cross-session rule that was written is prose with a counter-incentive.** `OWNER-ORDER-20261029.md`
   lists the rule set ("real smoke through the REAL launcher + REAL --epyc-root/cwd/imports; no T1 dryrun admission;
   rc75+partial at window end; taskset -c "$FILLER_CPUS"; unique port; feasibility sum …") and in the same
   document sets hourly READY quotas and lets failed-row republishes count. The scoreboard enforces the quota;
   nothing enforces the list.
4. **The filer is codex3 — the same worker whose rows it files.** The brief asks it to "group identical failure
   series"; it has no instruction, template or tool to raise a recurrence to ws58 or the operator, and no budget
   to read every log (it did not: the receipts' causes are in `launcher.out`/`entry.log`, which the subagents had to
   open).
5. **Reused ids and overwritten `.ended` make the receipt a snapshot of the wrong attempt** (§0), so even a reader
   of all 135 receipts would have mis-counted the mechanisms.
6. **The keeper has no concept of failure.** Its only alarm is `idle`; the LOOP-CONTRACT says "IDLE alerts … are the
   only nudge". A run that dies in 3 s frees the quarter, the idle alarm fires, the worker publishes the next
   unqualified manifest — the loop rewards the failure.

---

## 6. Operator decision package (only what is genuinely the operator's)

**D1 — Hard gate now, or warn-only for 24 h?**
Options: (a) **Hard gate on deploy** (recommended): zero grants to unqualified rows from the first keeper tick; READY
depth drops to 0 for a few hours while workers add `--complete-cmd`, `requires_tools`, `qual_fixture`, and a
canonical engine; compute idles for those hours. (b) Warn-only 24 h: keeper logs `qual-failed` but still grants;
failure rate stays ~40 % for one more day while workers migrate. Tradeoff: (a) costs ≤ 1 day of READY depth, (b)
costs another ~30 failed grants. The operator owns the idle-vs-failed trade because both are visible on the
scoreboard they read.

**D2 — Replace the hourly READY-manifest quota with a science quota.**
`OWNER-ORDER-20261029.md` is operator-backed and ws58 cannot amend its quota section. Proposed replacement metric:
"qualified rows granted" + "runs that ended rc0/75 **and** were filed with a verdict" per worker per day; failed
grants subtract. Keep the ≥ 4 READY floor as a buffer requirement, not a rate. Tradeoff: fewer manifests per hour,
far fewer burned grants; the pipeline rule ("build 3 in parallel") stays.

**D3 — Engine consolidation: allowlist of engine shas.**
(a) **One canonical `filler_run14.sh`, forks refused** (recommended; the seven forks are the carrier of five of the
nine families). (b) Allow forks that pass qualification. Tradeoff: (a) removes per-packet freedom (XGrammar
adaptation, EVL10 variant) and needs those features folded into flags; (b) keeps today's divergence risk.

**D4 — Disk-wait semantics.** Rows parked by `READY-WAIT-DISK` are not failures; should they still count against a
worker's READY floor on the scoreboard, and should the keeper be allowed to run the operator-approved reap pass
early when ≥ 2 rows are disk-parked? Recommend: count them as READY, allow the early reap within existing caps.

---

## Appendix A — per-receipt classification (135)

Columns: id | ended-day | self-reported class | family. Family letters as in §1. Where the forensic read contradicts
the receipt, the family follows the log (see §0 for the seven stale receipts).

| id | ended | self-class | family |
|---|---|---|---|
| hil15b-heavy-remaining-r11-20261028 | 2026-10-28 | import | A |
| refactor-01a16fc3-hil15-discovery-s1-20261028 | 2026-10-28 | harness | A |
| refactor-01a16fc3-hil15-private-s1-r11-20261028 | 2026-10-28 | harness | A |
| yarn-cpu-fixed120-v3-s2-20261027 | 2026-10-28 | harness | A |
| codex-hil15-s2-r13-pid-20261031 | 2026-10-31 | harness | A |
| codex3-paw-compact-a-20261030 | 2026-10-31 | harness | A |
| codex3-paw-compact-b-20261030 | 2026-10-31 | harness | A |
| codex3-paw-standard-a-resume-20261031 | 2026-10-31 | harness | A |
| codex3-paw-superlative-control-20261030 | 2026-10-31 | harness | A |
| codex3-prbt4-r1-20261031 | 2026-10-31 | harness | A |
| refactor-akxall8-c5-cpu-build-r5-20261031 | 2026-10-31 | harness | A |
| ct21-direct-exploratory-v2 | 2026-10-28 | harness | B |
| inf75-c5-w1-constructed-prefill-512 | 2026-10-28 | harness | B |
| inf75-c5-w1-constructed-prefill-512-r4 | 2026-10-28 | harness | B |
| inf75-c5-w1-constructed-prefill-512-r5 | 2026-10-28 | harness | B |
| inf75-c5-w1-constructed-prefill-512-r6 | 2026-10-28 | harness | B |
| inf75-c5-w1-constructed-prefill-512-r8 | 2026-10-28 | harness | B |
| inf75-c5-w1-gpu-primary-census-r2 | 2026-10-28 | harness | B |
| inf75-c5-w1-gpu-primary-census-r3 | 2026-10-28 | harness | B |
| rtg57-c5-vkq-t96-repair-20261028 | 2026-10-28 | harness | B |
| codex-ni-inf50-writerrace-resume-r11-20261029 | 2026-10-29 | harness | B |
| codex-ni-inf50-writerrace-resume-r13-20261029 | 2026-10-29 | harness | B |
| codex-ni-inf50-writerrace-resume-r5-20261029 | 2026-10-29 | harness | B |
| inf75-w2-current-cpu-census-r2-20261029 | 2026-10-29 | harness | B |
| codex3-hil15b-heavy-r9-split-20261030 | 2026-10-30 | harness | B |
| refactor-r18a-v10-independent-symbols-r2-20261030 | 2026-10-30 | harness | B |
| codex-ni-gnx-r2-nativeproof-r4-20261031 | 2026-10-31 | harness | B |
| codex-ni-gpu-zos22-c5-build-r2-20261030 | 2026-10-31 | unknown | B |
| codex3-kpf181-cpu-r1-20261031 | 2026-10-31 | harness | B |
| refactor-c6-35186-q4-two-cohort-cpu-20261031 | 2026-10-31 | harness | B |
| refactor-c6-cpu-iqkfa-on-build-729599d69-20261031 | 2026-10-31 | harness | B |
| refactor-c6-cpu-ops-full-729599d69-20261031-r2 | 2026-10-31 | harness | B |
| refactor-c6-gpu-27b-identity-729599d69-20261031 | 2026-10-31 | harness | B |
| refactor-c6-gpu-build-729599d69-20261030 | 2026-10-31 | harness | B |
| refactor-c6-gpu-gak-diag-729599d69-20261031 | 2026-10-31 | harness | B |
| refactor-c6-gpu-property-diagnostic-729599d69-20261031 | 2026-10-31 | harness | B |
| codex-m4-c3-original-20261028 | 2026-10-28 | admission | C |
| dtap-crm-benign-q2-r1 | 2026-10-28 | admission | C |
| inf70-v11053-solo5-build-q3-20261028 | 2026-10-28 | disk-floor | C |
| inf75-c5-w1-constructed-prefill-512-r2 | 2026-10-28 | admission | C |
| inf75-c5-w1-constructed-prefill-512-r7 | 2026-10-28 | disk-floor | C |
| inf75-c5-w1-constructed-prefill-512-r9 | 2026-10-28 | disk-floor | C |
| refactor-hil16b-resume-20261028 | 2026-10-28 | admission | C |
| rus3-repeated-samples | 2026-10-28 | disk-floor | C |
| rus3-repeated-samples-r2 | 2026-10-28 | admission | C |
| codex-hil15-s0-resume-v1-20261029 | 2026-10-29 | disk-floor | C |
| codex-hil15-s0-resume-v3-20261029 | 2026-10-29 | harness | C |
| codex-inf30-sala-acquire-20261029 | 2026-10-29 | disk-floor | C |
| codex-ni-inf50-existing-graph-r10-20261029 | 2026-10-29 | admission | C |
| codex-oab31-gitnexus-index-r2-20261029 | 2026-10-29 | disk-floor | C |
| codex-rev06-lb1-plan-20261029 | 2026-10-29 | disk-floor | C |
| hil15-s1-safe-successor-20261029 | 2026-10-29 | disk-floor | C |
| hil15-s1-unexposed-slots-v19-20261029 | 2026-10-29 | harness | C |
| hil15-s1-unexposed-slots-v20-20261029 | 2026-10-29 | harness | C |
| hil15b-new-cohort-retry-20261029 | 2026-10-29 | harness | C |
| hil15b-new-cohort-retry-r2-20261029 | 2026-10-29 | disk-floor | C |
| yarn-cpu-fixed120-v3-s0-r11-20261028 | 2026-10-29 | disk-floor | C |
| yarn-cpu-fixed120-v3-s1-r11-20261028 | 2026-10-29 | disk-floor | C |
| yarn-cpu-fixed120-v3-s2-r11-20261028 | 2026-10-29 | disk-floor | C |
| yarn-cpu-fixed120-v3-s3-r11-20261028 | 2026-10-29 | disk-floor | C |
| codex-hil15-s2-unknown-resume-v3-20261029 | 2026-10-30 | disk-floor | C |
| codex-hil15-s2-unknown-resume-v5-20261030 | 2026-10-30 | ? | C |
| codex-ni-yarn-dca-attribution-gpu-r1-20261030 | 2026-10-30 | ? | C |
| hil15b-bounded-output-r4-20261030 | 2026-10-30 | ? | C |
| codex-ni-td29-m4-cache-r3-20261031 | 2026-10-31 | admission | C |
| codex-hsf5p-restore-20261028 | 2026-10-28 | owner-retired | D |
| codex-hsf5p-restore-r2-20261028 | 2026-10-28 | harness | D |
| codex-ni-inf12-gate2-triton36-r5-20261028 | 2026-10-28 | harness | D |
| dtap-finance-action-reversal-q2-r1 | 2026-10-28 | harness | D |
| inf75-c5-w1-constructed-prefill-512-r3 | 2026-10-28 | harness | D |
| codex-ni-inf50-writerrace-resume-r7-20261029 | 2026-10-29 | admission | D |
| codex-ni-inf50-writerrace-resume-r8-20261029 | 2026-10-29 | admission | D |
| codex-ni-yarn-dca-xdev-cpu-r2-20261029 | 2026-10-29 | harness | D |
| fa4-c5-exact-set-r2-20261029 | 2026-10-29 | disk-floor | D |
| codex3-pip02-paddle-relocatable-r11-g104-20261029 | 2026-10-30 | ? | D |
| codex3-pip02-paddle-relocatable-r11-g89-20261029 | 2026-10-30 | ? | D |
| codex3-pip02-paddle-relocatable-r11-g95-20261029 | 2026-10-30 | ? | D |
| fa4-c5-exact-set-r13-20261030 | 2026-10-30 | harness | D |
| refactor-c3-native-bolt-profile-r2-20261030 | 2026-10-30 | harness | D |
| refactor-r18a-v10-independent-symbols-20261030 | 2026-10-30 | admission | D |
| codex3-lb49-fu03-cli-r1-20261031 | 2026-10-31 | admission | D |
| codex3-paw-standard-a-t1-20261030 | 2026-10-31 | admission | D |
| refactor-ufh12-r1-irt-r2-20261031 | 2026-10-31 | admission | D |
| yarn-oolong-s0-host256-eligible28-v33-20261031 | 2026-10-31 | admission | D |
| refactor-01a16fc3-hil15-private-s0-20261028 | 2026-10-28 | harness | E |
| refactor-01a16fc3-hil15-private-s2-20261028 | 2026-10-28 | harness | E |
| refactor-01a16fc3-hil15-private-s3-20261028 | 2026-10-28 | harness | E |
| yarn-cpu-fixed120-s0-20261027 | 2026-10-28 | harness | E |
| yarn-cpu-fixed120-s1-20261027 | 2026-10-28 | harness | E |
| yarn-cpu-fixed120-s2-20261027 | 2026-10-28 | harness | E |
| yarn-cpu-fixed120-s3-20261027 | 2026-10-28 | harness | E |
| yarn-cpu-fixed120-v3-s0-20261027 | 2026-10-28 | harness | E |
| yarn-cpu-fixed120-v3-s1-20261027 | 2026-10-28 | harness | E |
| yarn-cpu-fixed120-v3-s3-20261027 | 2026-10-28 | harness | E |
| codex3-hil15b-heavy-r2-20261029 | 2026-10-29 | harness | E |
| codex3-paw-compact-b-hostfix2-20261031 | 2026-10-31 | admission | E |
| refactor-01a16fc3-hil15-private-s1-20261028 | 2026-10-28 | harness | F |
| rtg57-c5-vkq-t96 | 2026-10-28 | harness | F |
| codex3-pip02-fresh-odl-quad-s2-20261029 | 2026-10-29 | disk-floor | F |
| codex3-pip02-fresh-odl-quad-s3-20261029 | 2026-10-29 | disk-floor | F |
| codex3-pip02-fresh-odl-quad-s4-20261029 | 2026-10-29 | disk-floor | F |
| hil15b-heavy-05-20-r11-20261029 | 2026-10-29 | disk-floor | F |
| hpr-fix2-prospective64k-20261028 | 2026-10-29 | disk-floor | F |
| inf75-w5s-current-census-r2-20261029 | 2026-10-29 | disk-floor | F |
| kpf18-g3-r12-integration-cpu-r2 | 2026-10-29 | disk-floor | F |
| codex3-hil15b-heavy-r5-20261029 | 2026-10-30 | ? | F |
| kpf18-g3-r12-integration-cpu-r4 | 2026-10-30 | ? | F |
| codex3-pip02-paddle-relocatable-r22-pool2-20261030-event-20261031T012855Z | 2026-10-31 | unknown | F |
| inf75-c5-w1-prefill512-barrier-r1 | 2026-10-28 | harness | G |
| codex-ni-inf50-writerrace-resume-r2-20261028 | 2026-10-29 | harness | G |
| codex-ni-inf50-writerrace-resume-r3-20261029 | 2026-10-29 | harness | G |
| codex-ni-inf50-writerrace-resume-r4-20261029 | 2026-10-29 | harness | G |
| inf75-w2-current-cpu-census-20261028 | 2026-10-29 | harness | G |
| inf75-w3-canonical-halfa-20261028 | 2026-10-29 | harness | G |
| codex3-pip02-paddle-relocatable-r27-head-20261030 | 2026-10-31 | harness | G |
| codex3-pip02-paddle-relocatable-r27-pool0-20261030 | 2026-10-31 | harness | G |
| yarn-128k-mi210-sol-r10-20261031 | 2026-10-31 | harness | G |
| fa4-output-location-diagnostic-20261028 | 2026-10-28 | unknown | H |
| codex3-pip02-fresh-s3-20261029 | 2026-10-29 | owner-retired | H |
| codex3-pip02-odl-310r2-resolved-r1-20261029 | 2026-10-29 | owner-retired | H |
| codex3-pip02-paddle-parallel-owner-r7-g107-20261029 | 2026-10-29 | owner-retired | H |
| codex-ufh12-r1-irt-20261028 | 2026-10-28 | harness | I |
| inf75-c5-w1-constructed-prefill-512-r10 | 2026-10-28 | harness | I |
| refactor-01a16fc3-m4-gpu-quality-20261027 | 2026-10-28 | harness | I |
| codex3-pip02-fresh-odl-generic-s11-20261029 | 2026-10-29 | unknown | I |
| codex3-pip02-fresh-odl-quad-s1-20261029 | 2026-10-29 | unknown | I |
| codex3-pip02-fresh-s0-20261029 | 2026-10-29 | unknown | I |
| codex3-pip02-fresh-s1-20261029 | 2026-10-29 | unknown | I |
| codex3-pip02-fresh-s2-20261029 | 2026-10-29 | unknown | I |
| codex3-pip02-paddle-parallel-owner-r4-g107-20261029 | 2026-10-29 | harness | I |
| codex3-pip02-paddle-parallel-owner-r4-g11-20261029 | 2026-10-29 | disk-floor | I |
| codex-ni-jetlong-small4x-paired-20261030 | 2026-10-31 | harness | I |
| codex-ni-td29-m4-cache-r4-20261031 | 2026-10-31 | unknown | I |
| codex3-pip02-paddle-relocatable-r28-head-20261031 | 2026-10-31 | harness | I |
| refactor-c6-gpu-gak-full-729599d69-20261031 | 2026-10-31 | unknown | I |

## Appendix B — evidence pointers

* Keeper smoke trust: `/mnt/raid0/llm/tmp/compute-flags/ws58-calendar-keeper-v7e.sh:304-311`; invocation line `:430`.
* Engine completion predicate: `…/engine/filler_run13.sh:186` (`is_complete`), `:309-310` (rc0→rc1); canonical
  `/workspace/scripts/coordination/filler_run12.sh:176,265,315`; `WORKDIR=/workspace` default `:47`.
* T1 proof design: `/workspace/scripts/coordination/dryrun_check.py:161-253` (`verify_pass`, `admission`), refusal
  print `:590`. Ban: `compute-flags/OWNER-ORDER-20261029.md` "Every manifest" paragraph.
* Host-chroot launchers: 65/309 armed launchers contain `sudo -n … /usr/bin/chroot /proc/1/root /usr/bin/setpriv …`;
  live example pids 1373/1381 on 2026-10-31; keeper itself runs in the devcontainer (`/proc/3239/root -> /`,
  `HOSTNAME=Beelzebub`, PATH without the host venv).
* Only alert kind ever emitted: `ws58-keeper-alerts.jsonl` → `{'idle': 464}`.
* Per-run root causes with file:line: forensic reports folded into §1; raw receipts in `filing-done/`, ended lines in
  `grants/`, launcher stdout in `ready/<id>.launcher.out`, manifests in `ready/armed/<id>.json`.

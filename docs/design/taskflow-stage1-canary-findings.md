# Taskflow Stage 1 canary — findings (2026-11-20)

Box: `handoffs/active/churn-pipeline.md` **TASKFLOW-STAGE1-CANARY** (done when `verdict: STAY-35B|TRY-27B|FIX-HARNESS`).
Worker: opencode 2.2.5 → row-owned llama-server, Qwen3.6-35B-A3B-MTP-Q8_0, champion C14 GPU store
`gpu-20261118-eee3da838-c14` (libggml-hip sha e6001b83…, marker `GGML_CUDA_AK_H15`), recipe
`qwen3.6-35b-a3b-q8-gpu-mtp` (research 78e981e96, sha 65770671…, MTP D=2). Rows are keeper-scheduled
(rowflow), owner pipeline-mgmt; dispatch runs without `--apply`, so it makes no ticks and no pushes.

## Current verdict: FIX-HARNESS (no model verdict yet)
Across 7 GPU rounds the verified count is at most 2 per round (r4 np4 2/10; r2 and r7a1 each had 1, from a lenient reviewer).
Every round exposed a new **harness** defect that blocked edits outright, so this is not yet a model-capacity
result and not yet the 27B trigger. The latest clean A/B (r6c vs r7d, same 8 boxes, np2):

| arm | verified | reached verify with edits | dominant failures |
|---|---|---|---|
| r6c no brief (control) | 0/8 | 0 (1 harness oldString) | no-change; wrong-repo lane (external_directory on NUMA-DECOUPLE-1, MM-5) = harness effect of no brief |
| r7d strong brief | 0/8 | 3 (TU-GR-1 pathspec, NOFOLD-1 reviewer not_done, MM-5 tests-fail) | garbled absolute paths `<mnt/raid0/llm/tf/…`, shell denials |

Briefs moved failures later, from exploring with no edit to making edits that fail verify. They did not yet produce verified ticks.
UFH-21 is harness-unsupported: its acceptance runs in `/mnt/raid0/llm/harness/opencode`.

## Round log (what changed → what it gained)
| round | change | verified | key finding |
|---|---|---|---|
| r1 | baseline | 0/10 | shell denied piped tests; JS `execute` sandbox loops; one-step narration; 14-step cap |
| r2 | 788972cbf: shell helpers, deny execute/opencode_*, nudge, 30 steps | 1/10 | opencode resolves paths from `$PWD` (row dir), not the lane |
| r3 | 8b60828a1: PWD=lane | 0/10 | uncapped side request decoded 31,896 tokens (MTP 0.14); long digit paths garbled; verifier false negative/positive |
| r4 | 3a420fa70/1479030ad H1-H5 prefix fixes, cap; np 1/2/4 sweep | 0/0/2 | np4 best aggregate (91.6) and hit (93%); np1 MTP 0.45 = 2 capped runaways (0.76 without) |
| r5 | short lanes, rel paths, cross-repo/rev refs, kernel-box exclusion, full ctx 262144 | 0/30 | model types wrong/abbreviated absolute paths; XML tool-call leaks; 6 runaways |
| r6 | guard, tool-arg filter + retry, 2048 agent cap | 0/5 (hard-end) | lane's `.opencode/plugins/filesystem-containment.ts` blocked worker writes |
| r7a1 (suspect) | briefs; launch.sh edited mid-run | 1/8 | snapshot lacked box_index → cross-repo briefs fell to self-brief |
| r6c / r7d | a99826703 plugin isolation; 9288ff0eb brief_mode; e12c0f9b0 repo-follow + brief pathspec | 0/8 / 0/8 | see table above |

Failure buckets (r3 hand classification, 10 tasks): harness 4, underspecified 3, model 3. The verifier, checked on one hand-done task, had a false negative and a false positive, both fixed in 38f603102.

## Performance (GPU C14, latest rounds)
| round | prefill tok/s | per-req decode | decode-only agg | union agg | prefix hit | MTP tok-w / per-req | VRAM |
|---|---|---|---|---|---|---|---|
| r4 np4 | 829 | 32.7 | — | 91.6 | 93.2% | 0.80 | 43.9 |
| r6c np2 | 557 | 49.5 | 21.2 | 10.7 | 86.7% | 0.76 / 0.81 | 50.6 |
| r7d np2 | 419 | 58.2 | 36.6 | 27.9 | 89.6% | 0.82 / 0.85 | 50.3 |
Single-request decode is 105–116 tok/s against an expected 98, so the launch is right. Wall time is set by prefill and tool time, not decode.

## Harness settings that stuck (evidence above)
opencode with PWD=lane, `OPENCODE_DISABLE_PROJECT_CONFIG`/`OPENCODE_DISABLE_CLAUDE_CODE`, private XDG, `snapshot:false`,
title/summary agents off, `execute`/`opencode_*` denied, read-only shell helpers, content-addressed POLICY
(stable prefix), `tool_output` 200 lines/8 KiB, opencode ctx = server slot ctx, 30 turns / 600 s.
Proxy: `id_slot` pinning, 4096 cap (2048 for agent turns), degeneration guard, tool-arg filter plus one corrected retry,
one retry on 5xx, full body log. Lanes are at `/mnt/raid0/llm/tf/<hex>` under the lifecycle rules (docs/design/taskflow-dispatcher.md).

## Next (Stage 2 / next round)
1. Path garbling is now the top blocker: the model types `<mnt/…` / `.mnt/…` absolute paths. Options: a lane path
   with no digits or long prefix, opencode env text that omits the absolute cwd, or a proxy normalisation of the leading `<`/`.`.
2. Shell denials: the model composes pipes and redirects. Allow `cmd 2>&1` and `| head`/`| tail` variants of the allowed commands.
3. CPU rounds on q0-q2: the s1 row `tf1-cpu-s1-35b-c14-q0q2-20261120` (derived-canary-cpu-q0q2, plumbing smoke PASS) measures
   the per-task CPU rate; size the next full round from it at np2.
4. The 27B arm (stack-registered Qwen3.8-27B-Q8_0 + DFlash2, recipe `qwen3.8-27b-q8-gpu-dflash2-np4` sha 17e9e51e…, research bdfab0239)
   runs only once the 35B plateaus with model capacity as the main failure.

## r8 (2026-11-20): harness fixes landed; calibration round staged, not run (compute stopped by operator)
**Harness changes (3edb0b60e + follow-up):**
- **Lane-path repair in the proxy.** r7d evidence: the 35B types absolute paths despite POLICY rule 10. The prefix gets mangled
  (`<mnt/raid0/llm/tf/e9f8`, `.mnt/…`, `mnt/raid0/tf/…`, `/mnt/raid0/84fd/…`, `/mnt/raid0/llm/t/65a8/…`), but the hex lane id always
  survives. `local_llm.repair_lane_paths` and `rewrite_sse_tool_args` rewrite streamed tool-call args to `/mnt/raid0/llm/tf/<id>`,
  only for existing lanes, and log `lane_path_repairs` per request. Repair was chosen over digit-free lane names or hiding the cwd,
  because the damage is in the prefix and the id is intact.
- **Shell allows.** Of 21 r7d bash errors, 10 were `cat`: POLICY rule 6 promised it, but `READ_ONLY` omitted it (a harness
  contradiction). The rest were `sed -n`, `pwd`, `git show` and `| head`. All are now allowed, plus `2>&1` and `| head|tail|wc|grep`
  on every allowed command. Denied: `sed -i`, `find -exec/-delete`, `>`, `| sh`. Output stays bounded by `tool_output`.
- **Phase-2 prompt fix.** It no longer points at the "WRITE BRIEF FIRST" section, which exists only in the brief phase.

**Calibration round (operator 2026-11-20; before more brief iteration), staged at `/mnt/raid0/llm/tmp/taskflow-stage1-cpu-r8-20261120`:**
- Easy arm: 5 trivial tasks in fixture repo `/mnt/raid0/llm/tmp/taskflow-calib-fixture-20261120` (E1 add `square`+pytest,
  E2 rename `tmp`→`total`, E3 off-by-one with failing test, E4 constant 10→30, E5 typo). Each has an inline strong brief
  (`brief_mode: off`, since the epyc-root brief store has no fixture briefs) and a pytest acceptance that fails on the unchanged tree.
  The reference fixes pass all 5, and lane + verify plumbing was proven offline (`verified mechanical`).
- Arms in this order, np2, CPU q1+q2: easy-nothink → easy-think → canary-nothink → canary-think. Thinking arms run
  `--reasoning on` plus proxy `chat_template_kwargs.enable_thinking=true`, with the agent-turn cap at 6144 (2048 nothink).
  The round stops with CALIBRATION FAIL if easy-nothink verifies fewer than 3 of 5.
- Per arm it records verified rate, output tokens/task, wall, XML-leak requests, 5xx retries and lane-path repairs, and saves
  `/props` (the loaded template/tool parser) as the format audit.
- Classification splits **format errors** (repair misses, malformed args, oldString misses) from **task-understanding errors**.

**Prefix-cache break (AK replay: step-2 cache_n = true LCP − 4 on all 8 r7d tasks).** In the r7d bodies, steps 1 and 2 are identical
JSON up to the appended assistant/tool turns: same tools and params, no timestamp or counter. A reference Jinja render of the
GGUF-embedded template shows the step-1 prompt as an exact byte prefix of step 2, in both nothink and think modes. So opencode's
layout and the template are **not** the cause. The 4 tokens are lost server-side: either minja renders differently from Jinja, or
(likelier on this hybrid recurrent model) the server restores a state checkpoint a few tokens back. C14 and AK's fork would share
that, which fits their equal hit rates. The r8 job renders both bodies through `/apply-template` per arm to settle the minja question.

**Status:** CPU row s1b (q1+q2, superseding s1, whose q0-q2 shape was blocked 2 days by codex-bfcl-cj3d) passed its smoke but was
withdrawn before any grant (operator: free resources for AutoKernel). The CPU per-task rate is therefore still unmeasured, and r8 is
unpublished. To resume: republish s1b (or r8 directly, resumable on q1,q2), take the measured rate, and book r8 as measured per-task rate × 26 task-runs (5+8 tasks × 2 arms) at np2, plus 4 server loads, plus 25%.

## r8b (2026-11-22): CPU canary, hand-audited — verdict FIX-HARNESS
Row `tf1-cpu-r8b-canary-35b-q0q2-20261122`, rc=0, CPU q1, C14 CPU build `cpu-20261118-eee3da838-c14`, Qwen3.6-35B-A3B-MTP-Q8_0, np1.
canary-nothink verified 1/8, canary-think 0/8. Decode median 17.4 tok/s, prefill median 111 tok/s, MTP acceptance 0.875, prefix hit 90%.
Packet fixes from r8 were in place: worktree-relative acceptance, orch-py.sh, LOOP-62 re-scoped. Easy arm r8a verified 5/5.

The dispatcher classifier said model-limitation 11, harness 2, task 2. A hand read of every transcript reverses this:

| task | nothink: audited (classifier) | think: audited (classifier) |
|---|---|---|
| INTAKE-VALIDATE-86 | b: the edit target `.claude/skills/research-intake/...` is in the packet's FORBIDDEN `.claude/**` (model) | b: same, plus a 600 s timeout after 4 steps (model) |
| TU-GR-1 | b: wrote exactly the two files the approach names, rejected outside-pathspec because `where` omits them. Its "tests pass" claim was unrun because pytest is denied in the shell (model) | a: timed out at 6 steps on prefill plus thinking, no edit (model) |
| NUMA-DECOUPLE-1 | a: self-brief phase forced despite a fresh hand brief, hit its 7-turn/150 s cap (task) | a: same (task) |
| LOOP-62 | **c**: rewrote `src/__init__.py` and 15 shims against the explicit non-goal (model) | a: 600 s timeout at 6 steps, no edit (model) |
| NOFOLD-1 | verified | a: the diff passes all 4 acceptance greps; the reviewer returned empty content in its 200-token cap (reviewer-unparseable) (model) |
| WS4-WAKE-IMPERATIVE | a: 5 requests, 75.9k uncached prefill at ~136 tok/s ≈ the whole 600 s (model) | a: 3 requests, 78k prefill, timeout (model) |
| MM-5 | a: on-track edits per the approach, killed at 600 s before the test; the verifier also runs `python3 -m pytest` (rc=4) instead of the orch-py.sh acceptance (model) | a: wrote the code and the test; the verifier's `python3 -m pytest` gave rc=4 (no fastapi in system python) (model) |
| UFH-21 | a: the work tree `/mnt/raid0/llm/harness/opencode` is outside the lane (external_directory denied); the approach also edits forbidden `handoffs/` (harness) | a: same, plus a junk `test-write.txt` probe (harness) |

**Counts (16 runs):** (a) harness/env 11, (b) packet 3, (c) model 1, verified 1. The classifier's 11 model-limitation labels hold for 1.
(a)+(b) = 14/16, so the result is **FIX-HARNESS**. TRY-27B is not supported: the only (c) is LOOP-62, which Sonnet also failed before the re-scope.
STAY-35B is not supported either, at 1/16.

**Harness fixes before r8c:**
1. Scale `wall_s` to the CPU rate. 600 s was sized for the GPU; CPU prefill of 77-284 tok/s on 30-80k-token requests uses it up. At least 6 of the 16 runs died on time.
2. The verifier must run the packet's `acceptance`. It ran `python3 -m pytest` for MM-5.
3. Allow each packet's acceptance command in the worker shell. Workers could not run their tests.
4. Derive the pathspec from the approach's new files as well as from `where`.
5. Skip self-brief when a fresh hand brief exists. The cross-repo NUMA case lost it.
6. Under thinking, raise the reviewer cap or read its reasoning content.
7. Packet: move INTAKE-VALIDATE-86's target out of forbidden, or allow it. Keep UFH-21 out until its tree can be a lane.

With 1, 2 and 6 alone, NOFOLD-think would have passed and TU-GR-1/MM-5 would have reached a real test.
Next: r8c with these fixes on CPU q0-q2. The 27B arm runs only on tasks still classed (c) after r8c.

## r8c (2026-11-22): CPU canary after the r8b fixes, hand-audited — verdict FIX-HARNESS
Row `tf1-cpu-r8c-canary-35b-q0q2-20261122`, rc=0, C14 CPU build, Qwen3.6-35B-A3B-MTP-Q8_0, np1, code snapshot at ea88415b1 (r8b fixes 1-6 and 8).
It ran in 3 stints: rc=75 yields to C18 folds at 13:55Z and 15:08Z, then completed at 16:45Z.
**canary-nothink verified 3/7 (TU-GR-1, LOOP-62, NOFOLD-1), canary-think 0/7, total 3/14 = 0.21.** In r8b it was 1/16.
`reviewer-done` is the reviewer's "done" on a diff that already passed commit, pathspec, forbidden and the acceptance tests. It is final verified, not pending a reviewer. All 3 diffs were read and are legitimate.

**RESULT.json bug.** The job's RESULT.json said `final: true` but held only the last stint ("canary-think 0/1"). Each resumed stint starts a fresh summary.
The fix is `scripts/coordination/taskflow/stage1_result.py`, with test `tests/coordination/test_taskflow_stage1_result.py`. It rebuilds one phase per arm from results.jsonl and keeps the per-stint phases in `out/stints.jsonl`.
This run was repaired with `python3 scripts/coordination/taskflow/stage1_result.py /mnt/raid0/llm/tmp/taskflow-stage1-cpu-r8c-20261122`. The original is kept as `out/RESULT.last-stint.json`.

| task | nothink: audited (classifier) | think: audited (classifier) |
|---|---|---|
| INTAKE-VALIDATE-86 | b: stale packet; the validator already exits 0 in the lane. Rejected outside-pathspec for a junk `tmp_extract_refs.py`, which is a correct reject. Piped `sed`/`sort`/`awk` shells were denied (harness) | b: same stale packet; the model found the validator passing; timeout plus ECONNRESET, no-change (harness) |
| TU-GR-1 | verified | a: **lane** — the stint-1 kill left `/mnt/raid0/llm/tf/06a9`, so the resumed unit was refused "exists: one worker per worktree" (harness) |
| NUMA-DECOUPLE-1 | b: stale packet; the work landed as a56df365b, and the model rewrote the existing decouple test. outside-pathspec on that file: fix 4 admits only *new* approach files, and this one exists in base (task) | b: the model correctly reported "already complete in a56df365b"; no-change is the right outcome (model) |
| LOOP-62 | verified | c: wrote identity asserts that fail 15/16; timed out at 13 steps (harness) |
| NOFOLD-1 | verified | a: acceptance passed. The reviewer used its whole 1024 cap and the parser took the prompt template `done\|not_done\|drift: <=150 chars` as the verdict (model) |
| WS4-WAKE-IMPERATIVE | c: used all 30 steps on the 7 builders without writing the acceptance test; rc=4 is "file not found", not env (harness) | a: acceptance passed; same reviewer template echo (model) |
| MM-5 | c: wrong `vision_token_estimate` (1054 vs 1024); the lane `src` was imported correctly (model) | a: **lane** — leftover `/mnt/raid0/llm/tf/3572` from the stint-2 kill (harness) |

**Audited counts (14 runs):** (a) harness 4, (b) packet 4, (c) model 3, verified 3.
The repaired RESULT.json, from the fixed classifier, says harness 6, model 4, task 1. It agrees with the audit on 4 of 11 failures.
- New `lane` label: correct, and it is a real resume bug.
- `no-change` label: both runs were stale packets, not harness or model.
- `outside-pathspec` still fires: once correctly (a junk file), and once on an approach-named file that already exists, which fix 4 misses.
- Mapping rc=4 to env is wrong when the worker never wrote the test file.

(a)+(b) is 8/11 failures, so the result is **FIX-HARNESS**. TRY-27B is not supported: model failures are 3/11, and the nothink arm solved 3 of the 5 still-open tasks.

**Fixes before r8d** (all LANDED 2026-11-22, epyc-root 7fcfdb8c7 fix 0 = item 7, a8d3f497c 1, c69545282 2, 5f393fe17 3, c507dff13 4, 70c3a0128 5, c4e154052 6):
1. Resume: drop or reuse the killed unit's lane before rerunning it.
2. Under thinking, do not let the reviewer think, or give it a larger cap. Reject a verdict string that echoes the template.
3. Packets: run a still-needed check at selection time. Drop INTAKE-VALIDATE-86 and NUMA-DECOUPLE-1, which are already done.
4. Pathspec: admit approach-named existing files.
5. Classifier: rc=4 with the acceptance file absent in the diff and the lane is model; no-change on a done packet is packet.
6. Allow `sed`, `sort`, `awk` and `cut` in shell pipes.
7. Job template: call `stage1_result.finalize(OUT, summary)`.

With 1 and 2 alone, think would have had 2 more acceptance-passing runs judged.

## r8d (2026-11-22): harness futility, no canary result — SUPERSEDED by r8e
Row `tf1-cpu-r8d-canary-35b-q0q2-20261122` (code at c4e154052, the r8c fixes) ended 20:47:34Z, 18 s after its grant, rc=0
reason=complete. All 10 units failed with `lane: 16 live lanes >= cap 16; run dispatch.py sweep` and made no model request.
This is not a canary data point.

- Cause: `/mnt/raid0/llm/tf` held 16 lanes from r8b/r8c. 14 were `kept` (24 h forensics window) and 2 were `live` orphans
  of killed stints (no keep_until, no live owner). The cap counted every lane, and `sweep` removed nothing before
  keep_until, so two rounds filled the cap.
- Second defect: `check_complete` counted the 10 lane-error records as done, so the row exited `reason=complete`
  instead of a resumable partial.
- Fixes, epyc-root a5a7b3479 (`tests/coordination/test_taskflow_r8e_lane_fixes.py`):
  1. The cap counts only `live` lanes whose owner pid:starttime is alive. Lane metadata now carries `row` and `base_dir`.
  2. `sweep` drops orphan live lanes at once. `sweep --release-filed` drops kept lanes whose row has a
     `filing-done/<row>.FILED` marker; pre-r8d lanes are resolved through the row workdir's `lane.path` files. drop_lane only.
  3. The r8e job runs `sweep_lanes(release_filed=True)` before dispatching.
  4. If a stint's units are ALL `harness`/`lane`, the job moves them to `out/harness-futility.jsonl` and exits 75. Its
     `check_complete` never counts a harness/lane record as a finished unit.
- Ops 2026-11-22: the new sweep released the 14 kept r8b/r8c lanes (both rows FILED, transcripts audited) and removed the
  2 orphans (06a9, 3572). The lane root is empty. Branch tips are logged in `/mnt/raid0/llm/tf/sweep.log`.
  r8d was filed SUPERSEDED by `tf1-cpu-r8e-canary-35b-q0q2-20261123`. r8e has the same 5 tasks x 2 arms and the r8d
  estimate, and is prepared but not published.

## r8e (2026-11-23): CPU canary after the r8c fixes and the r8d lane-cap fix, hand-audited — verdict FIX-HARNESS (near saturation)
Row `tf1-cpu-r8e-canary-35b-q0q2-20261123`, rc=0 complete 06:47Z, C14 CPU build, Qwen3.6-35B-A3B-MTP-Q8_0, np1, 1 stint per arm,
5 tasks x 2 arms. RESULT.json is final, `aggregated_from: results.jsonl`, covers all 10 units; `check_complete.py` exits 0 and
is honest (no harness/lane records). **Reported: canary-nothink 3/5, canary-think 4/5 = 7/10. Audited: 6/10 = 0.6.**
Perf: decode median 15.3 / 15.2 tok/s, prefill median 59 / 182 tok/s, MTP acceptance 0.92 / 0.86, prefix hit 0.96 / 0.93.

| task | nothink: audited (classifier) | think: audited (classifier) |
|---|---|---|
| TU-GR-1 | a: shell allowlist denied `orch-py.sh -c`, scratch scripts and `rm`; the model wrote `tests/test_unshare_debug.py`, emptied it but could not delete it, and ran out of 30 steps. outside-pathspec is a correct reject (harness, agree) | c: **false verify.** `test_isolated_launch_denies` is vacuous: the launcher execs the sentinel dir as `$0`, the child prints no JSON, the probe returns `ok=False` (json-parse-failed), so the test passes without isolating anything. The reachable case probes in-process, not via a child. The reviewer passed it (model; classifier said verified) |
| LOOP-62 | a: ~15 of 30 steps were shell denials for one-line python probes; the model wrote `tests/unit/_debug_alias.py` to get around them and could not run or delete it. Correct outside-pathspec reject (harness, agree) | verified: 16 parametrized identity asserts against `sys.modules[target]`, mixed concurrent test `xfail(strict=False)`; legitimate |
| NOFOLD-1 | verified; legitimate | verified; the SKILL.md cite is a bare path, not a markdown link, but the acceptance grep and done-when hold |
| WS4-WAKE-IMPERATIVE | verified: `ensure_imperative` wraps all 6 builders, tmux_adapter imports it, test file present; legitimate. The done-when's "a live woken session acts on one" is not covered by the packet acceptance (packet gap; the box stays open) | c: timed out at 1739 s after 20 steps, never wrote the test file (rc=4). Decode median 6.3 tok/s vs 15 for the phase, so slow throughput contributed (model, agree) |
| MM-5 | verified: env-gated `max_pixels` default None, resize to multiples of 28, estimate(896,896)=1024; legitimate | verified; legitimate (ceil-based estimate, still 1024 at 896) |

**Audited counts (10 runs):** verified 6, (a) harness 2, (c) model 2, (b) packet 0. The classifier agrees on 9/10; its one miss is
the think TU-GR-1 false verify, which is a reviewer defect.

**The r8c/r8d fixes held:** 0 lane errors and `lane_path_repairs` 0; 0 reviewer template echoes (all 7 reviewer verdicts are
29-57 tokens, `reviewer-done`); no outside-pathspec on approach-named files (both rejects are real scratch files); the stale
packets were dropped at selection (all 5 `stale: []`; the in-run skip path was not exercised); stage1_result aggregation correct.

**Verdict by the box rule: FIX-HARNESS.** 0.6 >= 0.3, but model failures are 2/4 (not the minority) and harness failures are 2/4
(>= 50%). This is near saturation: 4 of 5 tasks have a legitimate verify in at least one arm, and both nothink rejects were
otherwise-complete work. TRY-27B is not supported.

**Fixes before r8f** (listed, not implemented):
1. Shell allowlist: allow `bash <row>/orch-py.sh -c ...` and `bash <row>/orch-py.sh <lane-relative .py>` inside the lane.
   Today only `orch-py.sh -m pytest ...` passes, and the model writes scratch files to get around it.
2. Deletion: allow `rm` of untracked files inside the lane. Alternatively, have the commit step drop zero-byte new files and
   report them, so a model that emptied its scratch file is not rejected.
3. Reviewer must see the acceptance log (pytest `-rA` pass/skip/xfail lines) and the approach's "never pass vacuously" clause.
   It should reject a test whose isolation case passes on a launcher error. Cheaper check: a probe result carrying
   `launcher_error` must not count as denial (packet-level hint for TU-GR-1).
4. Think-arm wall: WS4 think ran at 6.3 tok/s decode against 15 for the phase. Before r8f, check whether host contention hit the
   unit's window (requests.jsonl timestamps against the grant calendar). If it did, classify that timeout as env, not model.
5. Packet: the WS4 done-when has a live-session clause the acceptance cannot show. Split it into its own box, or mark the
   canary verify as "acceptance only".

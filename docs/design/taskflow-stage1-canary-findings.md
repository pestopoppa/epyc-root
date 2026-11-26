# Taskflow Stage 1 canary — findings through 2026-11-26

> Follow-up: the [C22 real-task dispatch pilot](taskflow-real-dispatch-pilot-20261126.md) is complete with reviewed publications, additional harness repairs and qualified model findings. Its six-task diagnostic workload is separate from the historical canary below. A subsequent [harness-scope correction](taskflow-real-dispatch-pilot-20261126.md#harness-scope-correction--2026-11-26) establishes that both used a restricted OpenCode-derived setup; the recorded outcomes do not establish an intrinsic model ceiling. Native qualification of the replacement harness and matched comparisons remain in progress.

## Latest findings — C22 completion

The November 26 completion used C22 composite source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`, binary version
`10748`, with verified CPU and GPU store manifests. Both servers ran four slots with MTP D=2. The stores were
`cpu-20261126-ce6fcbbde-c22-composite` and `gpu-20261126-ce6fcbbde-c22-composite`.

The audit accepts seven of twenty-two executed attempts. Four additional stale positions skipped before worker launch.
Observed harness defects are repaired, with 224 regression tests and eleven real OpenCode tool controls passing.
Independent checks reject the remaining defective worker outputs. Detailed results and evidence appear in
[C22 completion](#c22-completion-on-2026-11-26).

## November 20 historical setup

Box: `handoffs/active/churn-pipeline.md` **TASKFLOW-STAGE1-CANARY** (done when `verdict: STAY-35B|TRY-27B|FIX-HARNESS`).
Worker: opencode 2.2.5 → row-owned llama-server, Qwen3.6-35B-A3B-MTP-Q8_0, champion C14 GPU store
`gpu-20261118-eee3da838-c14` (libggml-hip sha e6001b83…, marker `GGML_CUDA_AK_H15`), recipe
`qwen3.6-35b-a3b-q8-gpu-mtp` (research 78e981e96, sha 65770671…, MTP D=2). Rows are keeper-scheduled
(rowflow), owner pipeline-mgmt; dispatch runs without `--apply`, so it makes no ticks and no pushes.

## November 20 historical verdict — FIX-HARNESS
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

## r8f (2026-11-23): CPU canary after the r8e fixes 1-5, hand-audited — verdict FIX-HARNESS (not saturated)
Row `tf1-cpu-r8f-canary-35b-q0q2-20261123`, rc=0 complete 12:00Z, C14 CPU build, Qwen3.6-35B-A3B-MTP-Q8_0, np1, 2 stints (the
think arm was yielded to a C19 fold after t01 and resumed at t02), 5 tasks x 2 arms. RESULT.json is final,
`aggregated_from: results.jsonl`, total 10 tasks; `check_complete.py` is honest (10 model-work rows, no harness/lane rows).
`stints.jsonl` holds only the last stint (3 think tasks), which is why `phases_this_stint` shows 3; the phase totals come from
results.jsonl. **Reported: canary-nothink 3/5, canary-think 2/5 = 5/10. Audited: 4/10 = 0.4.**
Perf: decode median 15.5 / 10.7 tok/s, prefill median 103 / 79 tok/s, MTP acceptance 0.91 / 0.87, prefix hit 0.94 / 0.80.

| task | nothink: audited (classifier) | think: audited (classifier) |
|---|---|---|
| TU-GR-1 | **false verify** (classifier verified). `test_isolated_launch_denies` launches `exec python3 -c 'import sys; sys.exit(0)'` under unshare, so the child prints nothing; `probe_grader_access` maps empty stdout to `ok=False, errno=no-output` (a denial) and the test passes with no isolation. The vacuity guard returned ok and the reviewer passed it | model (classifier harness/outside-pathspec; the reject is correct). 30 steps burned debugging nested shell quoting, scratch files `_debug_isolation.py`, `_debug_result.json`, `_debug_probe.py`, `test_debug_probe.py` left; bare `python3 -c` and `mv` were denied and contributed, but `rm` and `orch-py.sh -c` were available and unused |
| LOOP-62 | verified; legitimate (16 aliases, identity asserts on `sys.modules[target]`, mixed test `xfail(strict=False)`) | model (agree). 11 requests, two hit the 4096-token cap in thinking, 1739 s wall, tests fail; decode 10.7 vs context-matched 11.8, so not slow |
| NOFOLD-1 | verified; legitimate | verified; legitimate (markdown link form is used here) |
| WS4-WAKE-IMPERATIVE | model (agree, rc=4: test file never written; only `handoff_sessions.py` edited). Not contention: decode fell smoothly with context (10.2 at 36k, 7.9 at 58k, 5.7 at 76k) and the classifier had no context-matched reference. A 36k-token single read drove it | **env contention** (classifier: harness/no-change, never evaluated). Decode 3.5 tok/s on the first request at 3.7k context vs 20-27 for every other arm's first request (13-17 percent), 2.5-3.1 through 20-60k vs the nothink arm's 5.7-10.2 at the same context, then MM-5 in the same stint decoded normally (13.3) |
| MM-5 | **harness** (classifier harness, agree). 18 tests passed, then the model called `opencode_worktree_remove` with `force` on its own lane; `git status` on the lane failed rc=128. The diff is gone, the unit would very likely have verified | verified; legitimate (aspect-preserving resize, multiples of 28, estimate(896,896)=1024, env default None) |

**Audited counts (10 runs):** verified 4, harness/env 3 (MM-5 worktree removal, think WS4 contention, nothink TU-GR-1 false verify),
model 3 (nothink WS4, think TU-GR-1, think LOOP-62), packet 0. The classifier agrees on 7/10; it misses the nothink TU-GR-1
false verify, the think WS4 env timeout, and calls think TU-GR-1 harness where the proximate cause is the model.

**r8e fixes held:** no refusal of `orch-py.sh -c` (11 uses across 5 units); the reviewer saw the acceptance log; WS4 acceptance-only
held (no live-session clause was demanded); 0 lane errors, `lane_path_repairs` 0, 0 template echoes, 0 degenerate aborts.

**Verdict by the box rule: FIX-HARNESS.** 4/10 = 0.4 >= 0.3, but model failures are 3/6 (not the minority) and harness/env
failures are 3/6 (>= 50%). Not TRY-27B: model failures do not dominate, and two of the three are long-context or
thinking-length timeouts on a slow CPU arm rather than capability limits. Not saturated: 3 of 5 tasks verify legitimately in at
least one arm (LOOP-62, NOFOLD-1, MM-5), TU-GR-1 and WS4 have no legitimate verify. The TASKFLOW-STAGE1-CANARY done-when is
a STAY-35B|TRY-27B|FIX-HARNESS verdict, but the box's own RESUME POINT is "iterate to 35B saturation", so it stays open.

**Fixes before r8g** (all LANDED 2026-11-23, epyc-root 9d7e102c6 fix 1, f0ee5a168 + c6ea4fa42 fix 2, b60f9862d fix 3, 6694fcf50 fix 4, 8f46306e2 fix 5, ccb51d59e fix 6; tests `tests/coordination/test_taskflow_r8f_harness_fixes.py`; r8g row `tf1-cpu-r8g-canary-35b-q0q2-20261123`):
1. Vacuity guard (`verify.py::vacuity_hits`): its `_LAUNCHER_ERR` pattern needs a `launcher_error` token. Extend it to the empty-stdout
   / `no-output` / json-parse-failed shape (any probe branch that returns a denial-shaped result when the child printed nothing),
   or require the isolation test to assert a distinguishing errno. Add the nothink TU-GR-1 diff as a regression fixture.
   Packet: add to TU-GR-1's approach that an empty child stdout is an error, never a denial.
2. Worker tool list: remove `opencode_worktree_remove` (and any worktree-mutating opencode tool) from the worker's tools, and make
   `dispatch` report a missing lane as `lane-destroyed-by-worker` (harness) rather than an uncaught `CalledProcessError`. Re-run
   MM-5 nothink once; its work was done.
3. Contention classifier (`dispatch.py::contention_class`): it runs only on timed-out rows already classed model-limitation. Run it
   on every timed-out row (including `no-change`) before the class is fixed, and when the phase has under 5 context-matched
   requests fall back to the whole job's requests (all arms, same context band), plus an early-context check (first-request decode
   against the job median of first requests). A no-change timeout at rc=130 must not default to harness.
4. Shell allowlist: bare `python3 -c` and `mv` inside the lane were denied and drove the think TU-GR-1 flailing. Either allow
   `mv` of untracked lane files, or add a refusal message naming the allowed forms (`orch-py.sh -c`, `rm`) so the model switches.
5. Think-arm budget: LOOP-62 think burned two 4096-token capped thinking outputs (about 1160 s). Consider a per-request thinking cap
   or a wall budget that scales with measured CPU decode; this is a model-fit question, not a packet defect.
6. WS4 nothink: a 36k-token single read at 10 tok/s decode ate about 200 s per large read. Packet `where` should point at line ranges
   of `handoff_sessions.py`, not the whole file.

## r8g configuration (2026-11-23): think-arm budget knobs
Per-arm keys in the job `CONFIG.json` (`arms[]`), read by `job.py` and `schema.py`:
- `wall_budget` (existing): `prefill_tok_s`, `decode_tok_s`, `expected_prompt_tokens`, `expected_output_tokens`, `margin`, `overhead_s`,
  `floor_s`, `cap_s` -> per-task `wall_s`. r8g sets the think arm to its measured r8f rates (prefill 79, decode 10.7 tok/s), which scales
  the think wall from 1739 s to 2554 s; the nothink arm keeps 1452 s.
- `request_cap` (new, `schema.request_token_cap`): `agent_cap_tokens` (2048), `think_cap_tokens` (6144), `max_request_wall_frac` (0.25;
  null disables), `decode_tok_s` (default: the arm's `wall_budget.decode_tok_s`), `floor_tokens` (1024). The proxy caps an agent-turn
  request at min(configured cap, frac x wall x decode). With frac < 0.5, two capped thinking outputs can never consume the wall.

## r8g (2026-11-24): CPU canary after the r8f fixes 1-6, hand-audited — verdict FIX-HARNESS (not saturated)
Row `tf1-cpu-r8g-canary-35b-q0q2-20261123`, rc=0 complete 2026-11-24T00:24:45Z, 2 stints (stopped for quiet-host rows, resumed),
Qwen3.6-35B-A3B-MTP-Q8_0, np1, 5 tasks x 2 arms, 0 timeouts. Verdict file `/mnt/raid0/llm/tmp/taskflow-stage1-cpu-r8g-20261123/out/verdict.json`.
**Reported: canary-nothink 3/5, canary-think 3/5 = 6/10. Audited: 6/10 = 0.6.**
OBSERVATION, not an improvement claim: r8f audited 4/10 and r8g 6/10, but there is no same-config rerun arm R (P-AB-1 / P-PAIRED, root ae2d53e1f), so the r8f→r8g difference is not a decision. The FIX-HARNESS verdict below rests on r8g's own failure classes.
Perf: decode median 17.2 / 14.9 tok/s, prefill median 116 / 99 tok/s, MTP acceptance 0.91 / 0.85, prefix hit 0.93 / 0.94,
task wall median 503 / 692 s.

| task | nothink: audited (classifier) | think: audited (classifier) |
|---|---|---|
| TU-GR-1 | **model** (classifier model, reason wrong). The reject is right but the reviewer's reason is not. The model's unshare launcher runs a one-line `try: ...; except` python inside `sh -c` with no argv, so the child crashes (SyntaxError/IndexError), always returns `launcher_error`, and the test always skips. It also skips when the sentinel is reachable, which is a vacuous escape | **harness: reviewer false reject** (classifier model). The work follows the packet. The control test asserts that `GraderReachable` is raised, which is the done-when's "fails on a deliberately reachable grader". The isolation test uses the packet launcher and skips with a real reason: `unshare: write failed /proc/self/uid_map: Operation not permitted`, and the host has `kernel.apparmor_restrict_unprivileged_userns=1`. The packet sanctions that skip. The reviewer read the passing control as "did not fail" and treated the sanctioned skip as not_done |
| LOOP-62 | verified; legitimate (16 aliases, `module is sys.modules[target]`, mixed test `xfail(strict=False)`, no src edits) | verified; legitimate (18 passed, 1 xfailed). In r8f this unit was a model timeout; the request_token_cap fixed it |
| NOFOLD-1 | verified; legitimate (markdown link to `#no-fold-list`) | verified; legitimate (the citation is a code-span path rather than a link, which is acceptable) |
| WS4-WAKE-IMPERATIVE | **harness: pathspec regression from r8g fix 6** (classifier model). The approach tells the worker to edit `tmux_adapter.cmd_nudge`, but `verify.brief_paths` keeps the `#L<a>-<b>` suffix, so `scripts/coordination/tmux_adapter.py#L2301-2488` never matches the file. `handoff_sessions.py` got in only through the bare-name sibling rule. The diff (helper, 6 builders wrapped, nudge wrapped, 11-case test) is plausibly correct, but its tests never ran. It finished in 498 s; r8f timed out at 1452 s | model (agree). It spent the 30-step cap on `oldString` misses, never wrote the test file, and acceptance gave rc=4. No timeout, no contention |
| MM-5 | verified; legitimate (aspect-preserving resize, sides snapped to multiples of 28, `max_pixels=None` passes bytes through). No `opencode_worktree_remove` call | verified; legitimate (same design, 15 tests) |

**Audited counts (10 runs):** verified 6, harness 2 (think TU-GR-1 reviewer, nothink WS4 pathspec), model 2 (nothink TU-GR-1, think WS4),
packet 0, contention 0. The classifier agrees on 8/10.

**r8f fixes, did they hold:**
1. Vacuity: held. There was no empty-stdout false verify. Both TU-GR-1 probes return `launcher_error` on empty stdout, as the packet line asks.
2. Worktree tool: held. 0 `worktree_remove` calls, and MM-5 nothink verified.
3. Contention classifier: not exercised (0 timeouts).
4. Refusal hints: **not observed.** All 16 shell denials return a bare `Permission denied: shell` with no hint naming the allowed forms. 0 `mv` attempts.
5. request_token_cap: held. LOOP-62 think verified.
6. WS4 line ranges: held for the wall time (498 / 608 s against r8f's 1452 s timeout). It regressed the pathspec, see above.

**Verdict by the box rule: FIX-HARNESS.** 6/10 = 0.6 >= 0.3, but model failures are 2/4, which is not the minority, and harness failures are 2/4 (>= 50%).
Not TRY-27B. Not saturated: both residual tasks have an arm whose correct or plausibly correct work the harness blocked. With the two harness defects
fixed, the expected count is 7-8/10, and the remaining failures would be model-class. The box stays open (RESUME POINT: iterate to saturation).

**Fixes before r8h** (boxes TF-R8G-PATHSPEC-LRANGE, TF-R8G-REVIEWER-CONTROL, TF-R8G-REFUSAL-HINT in `handoffs/active/churn-pipeline.md`):
1. `verify.brief_paths` (and through it `forbidden_hits` / `outside_pathspec`) must strip a `#L<a>-<b>` suffix, using the same regex as `brief.py`. Regression
   fixture: the nothink WS4 r8g diff touching `scripts/coordination/tmux_adapter.py`.
2. Reviewer context: tell the reviewer which test is the done-when control. For TU-GR-1, a passing `pytest.raises(GraderReachable)` test IS
   "fails on a reachable grader". Also tell it that a skip the packet sanctions, when it carries a real errno, is not not_done. Packet: name the control test in the done-when gloss.
3. Shell refusal hint: the r8f fix 4 hint does not reach the model. Make the denial text name the allowed forms (`orch-py.sh -m pytest ...`,
   `orch-py.sh -c`, `rm`/`mv` of untracked lane files), or surface it through the proxy.

## C22 completion on 2026-11-26

- **A3B-CANARY-20261126 — FIX-HARNESS, repairs completed.** Qwen3.6-35B-A3B-MTP-Q8_0 produced 6 sound results from 16 original executed attempts, with four additional WS4 positions skipped because the task was already completed. Six correction attempts produced one additional sound result. The complete audit therefore accepts 7 of 22 executed attempts. The original failure classes are six harness false accepts, two model failures, one calibration-packet mismatch and one environment-contention outcome. The six harness failures among ten failed attempts satisfy the recorded FIX-HARNESS rule. All observed harness defects have regression coverage and the final Taskflow suite passes 224 tests.
- **TF-R8G-REFUSAL-HINT completion — SHELL_HINT_DELIVERED.** Captured A3B request bodies carry the allowed shell forms after permission denials. Repeated tool history is counted as request-body evidence. The subsequent tracked-file cleanup repair passed eleven scripted tool controls through OpenCode 2.2.5, including the two exact destructive documentation commands observed in this canary.

The operator authorized concurrent C22 CPU and GPU serving with whole-host CPU placement and overlap on GPU control cores. Both stores bind to source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba` through their verified binary/library manifests. Each server used four 131,072-token slots and MTP D=2. Six prior GPU attempts were retained. Thinking work ran on the GPU. Spare GPU slots ran pending non-thinking work after template and response checks confirmed the per-request setting. The original and correction packets, application bases and harness hashes are recorded in `SOURCE-MANIFEST.json` under `/mnt/raid0/llm/tmp/taskflow-finish-20261126/`.

| Task | Original hand-audited outcome | Correction outcome |
| --- | --- | --- |
| TU-GR-1 | All four fail. Three automated verifies were false accepts of broken isolation code. | Both fresh patches fail the independent contract. Simulated launcher success exposes malformed child code, and mount-permission failure exposes an overly broad skip. |
| LOOP-62 calibration | Three sound reproducer patches. One reject followed an ambiguous instruction to retain historical metadata assertions while forbidding the source fix. | The clarified packet removes the metadata ambiguity. The last patch's green XFAIL hid a string-format exception before launching imports. The pinned-recipe contract rejects it and accepts the three sound saved patches. |
| NOFOLD-1 | Three sound patches. One false verify removed the freeze paragraph and duplicated the existing Rules section. | The corrected acceptance and hand audit accept the new patch. Its worker also exposed tracked-file deletion through raw shell commands, now covered by the checked cleanup helper. |
| MM-5 | Both GPU verifies were false accepts. The CPU patches reached their worker deadlines and failed their generated tests. | Both fresh patches fail trusted checks for incorrect payload dimensions. Independent checks also cover both cap-784 orientations and the real recorder keyword interface. |
| WS4-WAKE-IMPERATIVE | Four intentional stale-task skips before worker launch. | The existing line-range pathspec regressions pass. |

The reviewer remains fallible on these tasks. Stronger text alone accepted all four defective historical isolation patches and the destructive documentation patch. The final verifier uses independent behavioral or pinned-recipe checks for these cases. The fresh non-thinking isolation patch also exposed the old 12,000-character diff cutoff. Complete diffs now reach the normal reviewer HTTP entry point, and the saved patch was rechecked without another worker run.

The isolation contract exercises a valid positive control, a simulated namespace-capable branch, an explicit unshare permission refusal, an unrelated launcher failure, a mount permission failure and invalid access errnos. The real host denies unprivileged namespace setup. Its allowed skip is retained with the original diagnostic. The controlled success/error cases validate the test and probe behavior.

The image contract uses trusted PNG inputs and a synthetic server response. It checks byte-preserving defaults, actual encoded dimensions, the 28-pixel grid, pixel caps for wide and tall inputs, and `notes['vision_token_estimate']` through the existing recorder signature. It catches unsupported logging keywords that the worker's broad exception handler previously swallowed.

The LOOP contract is explicitly a reproducer calibration. It preserves the pinned sixteen-alias map and the mixed test AST from orchestrator `5886e5aeb273fd4a8aaf1447bb3d8bc163d5c082`, including twenty cold subprocess trials with twenty-four threads. It also checks a genuine object-identity assertion and the declared nonstrict XFAIL. Legacy r8 packets receive the same scope and hold. The underlying source-fix task retains its full scope.

Worker cleanup now uses `taskflow-scratch rm` and `taskflow-scratch mv`. Raw commands are denied. The helper checks both the lane's HEAD and Git index, honors shell workdirs, and rejects protected or escaping paths before mutation. The real OpenCode wire replay preserves edited tracked READMEs and permits untracked scratch cleanup.

`PERFORMANCE.md` and `PERFORMANCE.json` retain aggregate and per-stream prefill/decode rates, response latency, upstream and delivered first-token latency, token/cache/draft counts and resource samples. The six retained np1 units carry first-response-byte latency because their proxy did not capture actual token arrival. Original CPU timeouts are observations under the intentionally overlapping serving configuration.

`MATRIX.json` and `FOLLOWUP-MATRIX.json` contain native and audited dispositions. `FINAL-CONTRACT-RECHECK.json`, `FINAL-VERDICT.json`, the saved patches and `audit-prior.md` bind the final findings. The original controller's exit summary counted the four intentional skips as missing. The reconciled ledgers account for all twenty original positions, and the corrected completion predicate includes skips. Both owned C22 servers were verified stopped and the host claims released. Superseded r8g and GPU-r2 row receipts were filed with their raw evidence retained.

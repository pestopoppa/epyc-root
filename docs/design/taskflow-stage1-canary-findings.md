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

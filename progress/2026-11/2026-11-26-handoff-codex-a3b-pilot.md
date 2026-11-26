# 2026-11-26 — handoff codex-a3b-pilot

## 15:27Z — **UTM-B2-GREP-HISTORY** [non-inference] Add a REPL grep_history(pattern, context_lines, offset, count) tool over the session's verbatim log, registered only after the first compaction boundary, with a size-safe output contract (case-insensitive regex, oldest first, 10 per page up to 30, context up to 3 lines, 6K-character response ending on a whole match with a continuation offset, 300-character line clip, count-only with per-source counts, compiler errors returned, 10 s timeout) (intake-2729).

Reviewed existing APP implementation at `332ceb2e14d16f2031bd17b1f7c839ce8276a24b`. The four `tests/unit/test_grep_history.py` tests pass in an isolated archive (2.11 s). They cover boundary registration, private registry, nonoverlapping pagination/count agreement, invalid regex and timeout, tool charging, flags-off registry identity, and bounded whole-match continuation. No duplicate A3B implementation run was needed. The old wrong-repository assignment is superseded by the current APP source.

Registered nonschedulable `codex-a3b-pilot` service identity for exclusive pilot task claims.

Next: codex-a3b-pilot dispatches the now-unblocked constrained compaction tests and independently reviews worker patches.

## 15:36Z — **DS41-W-44** DS41-C11 — Pre-existing test failures found while landing `5125f7ab`, reproduced on a clean HEAD

Reused current research implementation instead of dispatching a duplicate repair. On pinned `dd090a874c22be58e09b18fc1fc86da7b46b1d85`, the full `test_existing_cpu_run.py` and `test_serial_roster.py` suites pass (47 tests, 46.17 s, system Python 3.12, isolated locks and temporary files). Main checked the repaired oracle signature and actual scheduler settlement assertions. Evidence: `/mnt/raid0/llm/tmp/ws58-a3b-pilot-20261126/test-selection/research-w44-312.txt`.

Extended the existing Taskflow belief-source registration to name the real-dispatch producer, immutable attempt manifests, source bundles, and distinct main acceptance. This is prospective wiring documentation; it creates no retrospective measurement warrant. The prior GREP closure was pushed as `9b079df8f42f` after adding the authorized D9 trailer required for the pilot service identity.

Next: codex-a3b-pilot reviews pending worker patches and lands only independently accepted changes.

## 15:39Z — Independently review and repair bounded A3B documentation outputs

Landed two independently reviewed design documents. PAW-5 retains one coherent shadow-classifier candidate with a matched direct-model baseline, independent human gold, explicit abstain/invalid paths, and the correct PAW prerequisite state. The original draft had enum/source/routing contradictions; its model correction still misstated PAW-1. Main repaired the final status and provenance. DS41-W-75 records only the requested AutoKernel seed abstention from pinned source guards. Main excluded an out-of-scope helper and corrected source identifiers/line citations and unsupported detail. Both are human-assisted outcomes, not clean autonomous task successes.

The scratch PAW structural checker also had overly strict heading/provenance placement assumptions. Versioned v2 controls accept valid Markdown headings and source headers, while independently preserving rejection of the original factual errors and refusal of a missing baseline (10 controls). Raw attempts, hashes and old graders are retained under `/mnt/raid0/llm/tmp/ws58-a3b-pilot-20261126/`.

Next: codex-a3b-pilot finishes the constrained test tasks, repairs observed harness defects, and files performance plus independent outcome evidence.

## 15:48Z — Repair input custody and task-aware shell recovery found during real dispatch

Added first-class external_readonly_inputs: validate packet shape and names, authenticate all files before lane creation, stage read-only copies, prevent edits, and reject missing/tampered inputs before model work and after acceptance tests. Cleanup unlinks reference symlinks without chmod of their targets. Malformed declarations fail admission.

Replaced misleading universal shell guidance with exact task-specific accepted commands. A runner is suggested only if configured. Preserved whitespace inside quoted acceptance expressions through repo-cd normalization and the worker allowlist. Clarified that file tools use cwd-relative paths while approved runner commands retain their exact configured path. Permission grants are unchanged. Manual caller tracing scopes risk to Taskflow staging/verification/worker guidance; GitNexus had no usable index.

Validation: full Taskflow suite 239 passed in18.77s; final policy subset79 passed in1.00s; real OpenCode2.2.5 replay demonstrated denial of the altered command, contradictory baseline feedback, and successful copying/execution of corrected feedback. External-input controls include positive staging and rejection of missing/hash/schema/traversal/collision/tampered/symlink cases. Index check:0 problems. Evidence under `/mnt/raid0/llm/tmp/ws58-a3b-pilot-20261126/main-review/` and `test-selection/denial/`.

Next: codex-a3b-pilot reviews remaining native outputs and files the final model/harness attribution and performance snapshot.

## 15:56Z — File independently reviewed historical cache sizing note

- **PFXC-A3 — SIZING_NOTE_REVIEWED.** Research `8b6bc70f2242` records all41 evicted-entry sizes from source row `taskflow-stage1-canary-r2-20261120`: nearest-rankp95=1189.547MiB and ceil(10*p95)=11896MiB, with a prospective12288MiB controlled-check starting budget. The source trace is32K/np1. The separate8-task probe had zero evictions at8192MiB;37.9GiB is the distinct brief baseline. This is a source-bound historical calculation and planning note, not a new measurement or a claim of population-p95 bounds. Main replayed the exact documented extractor (41/41 numeric values), confirmed canonical recipe bytes unchanged, and passed checkerv3.

A3B required a correction for geometry/link/arithmetic/bias errors and final human repair of extractor/source attribution. V2 checker falsely rejected a correct two-budget sentence; versionedv3 fixes that case and passes13controls. Original outputs and graders remain retained. The note is human-assisted, not an autonomous clean task success.

Next: codex-a3b-pilot files the committed conclusion and closes the documentation box while remaining native tasks finish.

## 16:01Z — **PFXC-A3** [non-inference] `--cache-ram` sizing for 10+ concurrent worktrees (brief A3): entries are 330-1005 MiB (hybrid state + 32k f16 KV), 8 GiB holds ~8-12 conversations; r2 logged 41 `making room for prompt cache entry` evictions. Record per-entry MiB from the probe row's server log and write the recipe sizing (cache-ram MiB = entries x p95 entry size) plus the np2 VRAM budget note (37.9 GiB peak at np1) into the A3B recipe notes. model: Qwen3.6-35B-A3B-MTP Q8_0.

Closed PFXC-A3 after independent semantic and executable review of research `8b6bc70f2242`. Committed conclusion `cc:v1:33a4f1000baf0ae817d3501a3898f8bf` anchors the source-bound calculation to progress commit `3110901242b3`; it supplies an observation of the documented conclusion and no retrospective measurement warrant. The source trace and separate probe remain distinguished, and the canonical serving recipe is unchanged.

Next: codex-a3b-pilot completes the remaining engineering-note and test reviews.

## 16:30Z — Publish independently audited C22 pilot findings

All six real-task outputs are now published across root, research and orchestrator. The final findings distinguish model drafts, human repairs and independently prepared replacements, and bind the full native attempt inventory in a committed audit. The corrected worker compaction test is functionally unchanged by formatting and passes 62 tests plus five behavior mutations; the main fixture repair passes two independent integration checks. Required app gates pass after byte-equivalent shell formatting repair.

C22 GPU thinking was verified in actual forwarded bodies and reasoning histories; CPU work remained nonthinking as requested. The late resume audit found older reasoning omitted after OpenCode appended a new user turn. Future approved same-task thinking continuations now opt into preservation, with exact wire/provenance and embedded-template controls. Historical W66 continuation remains qualified; no native outcome was rewritten.

The evidence set contains 17 scheduling attempts and 252 request records, including 67 CPU and 185 GPU. Both servers/controllers/workers exited and compute claims are free. The full root is KEEP-leased through 2027-01-25. See `docs/design/taskflow-real-dispatch-pilot-20261126.md` and `artifacts/analysis/taskflow-real-pilot-20261126/audit.json`.

Next: codex-a3b-pilot files the committed conclusion and closes the remaining three completed source boxes.

## 16:33Z — Close the remaining completed pilot source tasks

Closed the remaining NARIQ design, DS41-W-66 fixture repair and VERBATIM regression boxes from their actual published artifacts and independent checks. Research `9a4e7dd4b433` contains the independently prepared design, research `ae08f0a58a77` contains the fixture repair, and orchestrator `af947afe843b` contains the corrected worker test. Source/review provenance and qualifications are in root findings commit `c6d1a04d9b82`.

The pilot conclusion is registered as a committed observation. No model-ranking or retrospective measurement warrant is claimed. All observed harness failures have repairs and scoped regression evidence; remaining clear source/test errors are model limitations, while W66's interrupted/resumed execution outcome retains its reasoning-loss qualification. No inference processes or compute claims remain owned by this pilot.

Next: pipeline-mgmt uses independent contracts and the retained residual cases when preparing the separately enrolled Stage 1 comparison.

## Harness scope correction and revalidation hold

Re-audited the actual OpenCode 2.2.5 wire: the old custom setup exposed seven direct tools; the stock reference exposes twelve, including execute, subagent and web capabilities. Old sampled prompts still referred to Code Mode session operations despite missing execute. Corrected the pilot report to restrict its conclusions to that configuration; intrinsic model capability remains unproven. The replacement keeps useful tools and validates deterministic syntax-error recovery, effective native output caps for all roles, questions, isolated references and session continuity before new quality runs. No native qualification or new quality outcome is claimed yet. GitNexus has no usable index; documentation-only impact manually scoped to this report and its conclusion record.

Next: codex-a3b-pilot independently checks the sealed qualification manifest, then runs native C22 harness controls before any task comparison.

## Model-free qualification receipts retained

The exact stock-derived API/container/transport path passes the twelve-tool matrix, answered question, child session, skill, public web, Python test, read-only reference and execute syntax/correction controls. Eight transport controls cover output aliases, all-role metering and an absolute deadline under continuous SSE. Actual stock manual compaction keeps the same session, exposes the summary to the next worker and restores the identical twelve schemas plus a functioning Code Mode catalog. These are scripted provider controls, not A3B quality results. Exact frozen native manifest has 3391 matching files and SHA256 556cc817e484ee7b2276c0d73f95f6bb8a17288d2e039da07c70ce436c7868c4. Main approved synthetic CPU/GPU native qualification; real tasks remain held. Receipts are committed under artifacts/analysis/taskflow-harness-revalidation-20261126/.

W66 acceptance parity now passes in the same container after limiting git grep to four threads: the original baseline fails its intended witness and the known positive passes both tests. The earlier mismatch was container process-budget exhaustion, not missing source or a model failure.

Next: codex-a3b-pilot verifies actual native tools, budgets, reasoning and continuation before approving the paired task and main-only set.

## Native synthetic qualification passed

Main launched the approved sealed manifest under the owned q0–q3 region claim. Controller PID2920116/exec83642 completed rc0. C22 CPU PID2920162 and GPU PID2920412 passed content-based identity, health/smoke and actual OpenCode controls. CPU read/write/pytest/reference custody used185 generated tokens; GPU execute syntax-error/correction plus same-session continuation used1367 generated tokens. Native template retained8/8 synthetic history markers with preservation versus0/8 default; the actual resumed session retained3/3 prior reasoning entries versus0/3 default. Counters were known and no request errors were accepted. Both owned servers exited rc0 with death verified and KFD empty. Raw native control receipts and request metrics are under artifacts/analysis/taskflow-harness-revalidation-20261126/native/.

This is synthetic native harness qualification, not a real-task capability result. Actual native compaction continuity remains to be checked before the planned quality/main-only comparisons.

Next: codex-a3b-pilot completes native compaction qualification, then freezes and runs the paired real-task grid with measured guidance and main-only accounting.

## Native compaction and fresh main-only comparator

Native C22 compaction extension dc3b056d92bf37d066a363bd345cbf36563cb4279d9ddc19df6b62c1ef6987fa passed under main-owned exec3880. The same actual qualified session produced one real summary (470 generated tokens) and two continuation requests (299), retained its prior reference marker, restored all twelve identical tool schemas, executed the real Code Mode models catalog call, and read/returned the reference again. OwnedGPU2980940 exited rc0/death verified/KFD empty. The original3391-file seal remains untouched; extension receipts are retained in artifacts/analysis/taskflow-harness-revalidation-20261126/native-compaction/.

Four fresh gpt-6.1-sol/low main-only turns completed rc0 on original paired briefs, in66.9s(PAW),74.8s(W66),89.9s(NARIQ) and111.7s(PFXC). These timings include CLI execution and are provisional comparator observations, not accepted-result claims. Verification exposed two further acceptance-harness gaps before any A3B quality launch: ordinary pytest cache artifacts were treated as forbidden source edits, and valid period-terminated bold field labels failed the PAW structural regex. Versioned equivalent acceptance and explicit migration of both arms are underway; model outputs and original failures are retained, with no model rerun needed. NARIQ and PFXC original structural/content checks pass; independent semantic/tool-use review is still required.

The initial packets contain detailed owner guidance, including PFXC solution statistics. Initial success therefore means independent execution from that brief, not unguided backlog discovery. Historical preparation is reused and unmeasured in both arms.

Next: codex-a3b-pilot finishes symmetric acceptance repairs and launches the frozen A3B CPU/GPU task grid, preserving the completed main-only outputs unseen by initial local workers.

## Matched quality grid launched after acceptance repairs

PAW Markdown v3 accepts equivalent period/colon field labels while preserving provenance/required-field negatives (15 controls); the original rejection is retained. W66 uses its unchanged independent oracle after normal pytest cache artifacts are isolated and hash-retained; actual unrelated writes still fail. All four saved main-only candidates now pass their same-version independent checks and source scope, with no model reruns. Audit of28 commands plus web/patch events found no observed prior-answer access.

Main verified3020 sealed inputs and approved quality manifest0d9271ba12676e3899d27d92cc65ccdb68378595bc4d74cbf96e47081af1f33b. Exec33004/controller3220534 now owns CPU3220587 andGPU3220840 under q0–q3 diagnostic locks, with GPUquiet none. Both C22 np4 servers passed live identity/residency/health. Eight initial units are active across bothservers; GPU slots run independent ordered queues over the fourteen-row design. Every thinking call preserves available reasoning; all roles have a recognized32768 output ceiling and120000 cumulative generated bound, with1800sGPU/3600sCPU walls and no custom read/step limit. Main-only outputs are excluded from worker mounts. Launch proof, changed acceptance version and comparator counts are retained in artifacts/analysis/taskflow-harness-revalidation-20261126/quality-launch/.

Next: codex-a3b-pilot audits incremental local outputs, meters paid main review/guidance, and fills freed owned slots with separately approved continuations while preserving initial outcomes.

## Full-load harness failure found and stopped

The first full eight-stream quality epoch exposed issues not covered by the short native fixtures. Concurrent stock title calls shared each case slot with primary work. GPU PFXC's title used2375 thinking tokens over380.99s; its primary then waited385s before body arrival and lost its downstream stream. CPU NARIQ's title used16 tokens over243.60s. Persisted OpenCode retries show `Timed out waiting for response headers` at300.024s, matching the installed provider's300000ms default. These are harness-affected attempts, not model-capability results.

Main stopped captured controller3220534 withSIGINT and blocked queued rows, preserving all eight started attempts and six unstarted rows. The stop also exposed API cancellation error handling (`KeyError: data`), which masked final exports; raw databases are retained for model-free recovery. Source census found no candidate edits yet. Both owned servers3220587/3220840 were terminated after the grace period (rc-9), death verified and KFD empty; no unrelated process was killed. Sixty forwarded request receipts retain the consumed work and incomplete counters.

The repair keeps titles and useful tools: use an explicitly configured small-model alias on the same A3B with nonthinking metadata and a small role-specific cap; disable the provider's shorter header/chunk timeouts under the already-enforced absolute unit wall; batch/reduce API polling; fix supported cancellation and always preserve exports/error envelopes. New versioned controls and a fresh sealed epoch are required before drawing quality conclusions. Main-only completed outputs remain valid and will be reused.

Next: codex-a3b-pilot validates the role-budget/timeout/cancellation repair, recovers stopped-session evidence without inference, and resumes the matched grid on a new frozen harness.

## Role-aware timeout/cancellation repair and new epoch

Committed reusable OpenCode-derived source at b5baa0a73, including fresh/same-session candidate dispatch, full useful tools, hashed input custody, role-specific title budgets, absolute task deadlines and supported cancellation/export handling. The existing plus new Taskflow tests pass246/246. Actual contained scripted fresh/resume control preserves reasoning and draft files. A separate delayed-header negative control reproduces the retry; repaired configuration waits and completes; active cancellation returns interrupted:true and retains its export. Title calls use explicit small_model alias q35-a3b-title, nonthinking and64token cap; primary requests retain32768. Provider headerTimeout isdisabled while numeric chunkTimeout isbound to the approved owner wall. API forms/activitypolling isbatched once persecond percase.

Recovered all eight stopped original sessions without inference or changing originalbytes. Everylastassistantrecord is aborted/Stepinterrupted; noneproducedacandidate. W66 containsacorrectpartialdiagnosis, notapatch. Recoveryproofand53artifacthashes are retained under artifacts/analysis/taskflow-harness-revalidation-20261126/initial-01-recovery/.

Main independently verified3031 inputs in new quality-v3 seal7552d3ef1a76eb4c2164f4a5010370bcdc424ccd8b898f1621e892fb7e51ef60; its Pythonmodulebytes exactly match committedcanonicalsource. Repaired epoch exec93923/controller4142230 now owns C22 CPU4142995 andGPU4144485, both np4 whole-host-overlap diagnostic serving. All eight metadata calls have completed at9–16tokens, with primary thinking/cap preserved and no observed newtransportfailure at the initial snapshot. No originalmain-only modelrun is repeated.

Next: codex-a3b-pilot checks completed initialoutputs and matched thinkingpairs, meters mainreview/guidance, and extends approvedslotqueues as needed to answer capability and task-effort questions.

# Code-queue tick audit for 2026-10-31 (ni, refactor, codex3)

This audit was read-only. Each queue item was matched to its handoff by task text against `origin/main` (root `1fda0ad84`, 12:16Z). "Today" means items that were evidenced at 12:16Z but not at the 00:00Z root commit `47cca9270`. Note that the scoreboard's own baseline was reset at 09:15Z, so its "today" set is a subset of this one.

**Scope.** I audited 48 of today's evidenced ticks (ni 22, codex3 19, refactor 7) plus a random sample of 5 unsupported ticks for codex3 and for refactor. ni has no unsupported ticks left.

**Checks.**
- Every cited SHA was resolved across the root, orch, research, llama.cpp and epyc-web repos.
- Diffs were read, and cited artifacts were checked on `origin/main`.
- The cited pytest files were re-run from `git archive origin/main` exports, which were deleted afterwards. All passed except where noted.

**Headline: there are no FALSE ticks.**
- No fake SHAs and no placeholder tests turned up. The 5 SHAs that resolve nowhere turned out to be file hashes, session IDs or HF revisions, not commit citations.
- The real problem is that **old work is being re-counted as today's quota.**
- **2 ticks should be reopened, plus 1 more from a sample.**

## Per-worker totals

| worker | scoreboard "today" | audited | GENUINE, new today | GENUINE, re-count of older work | PARTIAL | FALSE | honest count today |
|---|---|---|---|---|---|---|---|
| ni | 19 | 22 | 12 | 10 | 0 | 0 | **~12** (scoreboard overstates by ≥7) |
| codex3 | 19 | 19 | 14 | 4 | 1 | 0 | **~14** |
| refactor | 6 | 7 | 6 | 1 | 0 | 0 | **~6** |

In the sample of unsupported ticks, codex3 had 4 GENUINE and 1 PARTIAL, and refactor had 4 GENUINE (one of them a re-count of August work) and 1 PARTIAL. Most of these "unsupported" ticks are real fixes: the SHA and test sit in a sub-bullet or in the commit, not on the box line.

## ni: 22 of today's ticks

| item | cited evidence | verdict | reason |
|---|---|---|---|
| agentic-serving:575 UFH14-DEPLOY-EC-2e | orch a75f030c; test_deploy_ec2_lease.py (4 pass) | GENUINE, re-count | Ticked 10-30 in root 702722155. Today root `a5b9cd857` only added evidence to the box line. |
| akx-all-dims:162 AKX-AUTO-11 | research d1c7a8ff; audit doc | GENUINE, mis-cited, re-count | d1c7a8ff is an unrelated one-line edit, cited as "the HEAD I verified at". The real work is 0628dea39/54cd18cd5/0cad527df/22f7e5508/eb753e422 from 10-22..23. Today's only output is an audit doc. |
| akx-all-dims:276 regenerate longctx patch | research e95a9d2e2; patch + VERIFICATION.log | GENUINE but trivial, mis-cited, re-count | e95a9d2e2 is a coherence fix and does not touch the generator. I confirmed the committed patch (sha256 395e5bbd…) is byte-identical to `/mnt/raid0/llm/tmp/ak-codex-handover-20261007/…patch` from 10-07. Today's work was making it durable. |
| keep-gate:619 P0d W3/W2 independent replay | artifacts/autokernel/p0d-w2-w3-replay-20261031/ (root c40a51be8) | GENUINE | The replay deliverable was committed today and its scope is stated honestly. Not re-run, because the filesystem guard blocked extraction. |
| rebuild:1796 reuse INF-70 sibling affinity | research 37dcdcd53; test_serving_foreign_affinity.py | GENUINE (caveat) | Real `/proc` sibling-expanded overlap check. It only records the overlap and gates nothing, and covers GPU runs only. |
| rebuild:2573 R23-30 drain grace | research 37dcdcd53; test_boundary_20260901_drain.py | GENUINE | Grace is now workers × measurement time; the tests are substantive. Same commit as the row above, but a different task, so not a split. |
| unified-surface:4180 FIFO-off control | orch 9e1155a1; test_lock_fifo_queue.py (24 pass) | GENUINE | The 10-07 branch landed byte-for-byte. Landing it was the open step. |
| autopilot:302 N-way metric name/tooltip | orch b387c5dd; 33+6 tests | GENUINE, re-count | Ticked 10-30. The cited tmp log is gone, but the tests reproduce. |
| autopilot:430 substring "503" false positive | orch d7aa9d95; progress 10-30 | GENUINE, re-count | Ticked 10-30 (root c93068fa4). |
| autopilot:816 AP-69 proposal_filter label | orch dff7dabb + e822e378 | GENUINE, re-count | Ticked 10-30. The cited tmp log is gone. |
| conversation-stack:699 CS-22.V0 Silero pins | parity doc + capsule (hex values are ONNX/HF hashes, not commits) | GENUINE | The pin and parity tables meet the acceptance. First ticked today. |
| roofline:2592 WRAP-14 | research 0b1d0b4f7; test_canonical_recipe.py (34 pass) | GENUINE, re-count | Ticked 10-29 (aa566fb3c). Evidence was backfilled in `a5b9cd857`. |
| roofline:4968 G2-CONC-LIB v2.1 | research e95a9d2e2; test_g2conc_v21.py (87 pass) | GENUINE | Real classifier and fixture adoption. |
| episodic:278 M-17e vector repair tool | orch def3e2c0; test_repair_episodic_vector.py (17 pass) | GENUINE | New locked single-row repair tool with substantive tests. |
| eval-tower-audit:354 E3 SCORE-07 | orch b5da2080 etc. (07-20/21) | GENUINE, re-count | July work. The box itself says "no new engineering output". |
| eval-tower-verif:603 judge-scored fraction | orch fb127bf0; test_judge_exposure.py (9 pass) | GENUINE | New tool producing per-suite shares. |
| gpu-tie-in:294 GPU-WINDOW-PARK-DOC | orch c7d573c2 + test | GENUINE | Small task, small fix. |
| refactor-multirepo:274 reconcile C4-01 | root f219064ba (10-07) | GENUINE closure, re-count | Zero new effort. The conclusion was already recorded at line 250 on 10-24. |
| session-bus:2050 spawn mark | root 9801975d0; test_session_spawn_mark.py (15 pass) | GENUINE | Real wiring across tmux_adapter and session_bus. |
| shape-keyed:585 retire `q*` labels | orch 7ef445ba (08-12) | GENUINE, re-count | Fixed 08-12. The box was filed open 2 minutes later and closed today. |
| vidya:1299 VB-RUNNER-PATHS-3 | research 4ede8b2fa; 272-test log | GENUINE | Every site got a disposition. |
| refactor-multirepo:277 scanners onto shell_scan.lex | root c5c87541f; parity test (57 pass) | GENUINE | All 3 scanners migrated, with a parity test. |

## codex3: 19 of today's ticks plus 5 sampled unsupported ticks

| item | cited evidence | verdict | reason |
|---|---|---|---|
| agentic-serving:472 UFH14-B6a-1 | orch ac5a0bfb; 52 pass | GENUINE | Structured `blockers` and `wait_ms` on both gates. |
| kv-compaction:340 KV-6 | orch 84f6f6f1 (unrelated merge); timing bundle | GENUINE, re-count | The measurement was done and reported 10-29 and re-filed today. The cited SHA is a source identity, not a work commit. |
| champion-agg:198 CH-20.2 | llama cdb4d8c77c (10-24) | GENUINE, re-count, **not codex3's work** | Another session's 10-24 commit and gate. codex3 copied the artifacts today. |
| keep-gate:702 AKX-P4b | root b3082210b + research 61af96a93; 25 tests | GENUINE | Real per-cell standing, with UNKNOWN when provenance is missing. |
| rebuild:2288 R23-71 | root 1108d2206; VALIDATION.json | GENUINE | Bypass flags removed from the live entry and the manifest. |
| research-loop:5457 AK-PM-12 | research 93c217ec5; 108 tests | **PARTIAL** | Schema and validation exist, but no AK path produces receipts. I confirmed `journal.py` only imports the validators. No cap is configured and zero receipts were captured. The ask was "adopt as the hook, capture receipts now". |
| autopilot:201 request.files vision telemetry | orch f92297de; 3 tests | GENUINE | Exact, small fix. |
| autopilot:504 ma_hard_code_001 | research a0a3df0ff | GENUINE | A test that never asserted was replaced by real cases. |
| autopilot:672 SG-W2 | orch 48ade72d | GENUINE | Observe-only warrant telemetry, which is what the task asked for. |
| roofline:2335 LOADAVG-1 | root 68a4d5e9f | GENUINE | Pre-arm wait removed from both harnesses. |
| roofline:3519 HYG-2b | root bd9ffccec (10-20) + 60afbb48c (today, 6 test lines) | GENUINE (mostly old) | The fix is from 10-20. Today added only the regression tuples, which were the open piece. The commit subject does not describe its content. |
| episodic:600 M-21 | orch 6de0e31d; 9 pass | GENUINE (caveat) | Opt-in smoke filter. The task body was rewritten at tick time. |
| intake-derived:156 ID-11 | root 4174b51db (08-05) | GENUINE, re-count | August work. Today was verification only. |
| kv-unified:170 KVU-15d | orch 7ecfbe3f | GENUINE | Lease timing is recorded under the admission mutex. |
| loop-fleet:592 probe over-match | root 752a7a6ec; 12 pass | GENUINE | Probe uses the declared `deliverable_paths`. |
| multiscreen:609 Z12-COMMIT | research f0d7449f8 | GENUINE | The task was to commit the doc, and it is committed. |
| non-inference:1072 LOOP-23 | root 737f8db40 (pin only) | GENUINE (caveat) | Keeper v7e is deployed, but its script and tests live only in `/mnt/raid0/llm/tmp`. |
| chat-template:648 CT-12.6 | root 0cfdda735 | GENUINE | Checker: 7/7, and a mutated template fails. |
| rocm-verify:938 RVP-C2-12 | llama f744cc220e (08-13), research 14034623 (08-11) | GENUINE, re-count | August work. The cited 93c217ec5 is just the HEAD at verification. |
| sample: eval-tower:228 ThinkPRM cross-family | orch de6c56e3 | GENUINE | 10/10 pass. The box line is missing only a test name. |
| sample: kv-unified:526 KVU-13a | orch 61c4763b | GENUINE | 7 hostile-parent tests pass. |
| sample: agentic-serving:224 UFH14-B1f | orch 6ed745fa | GENUINE | 29/29 pass. The box says ✅ 10-30 but was flipped 10-31 02:06Z (0db4fc2db), so it is backdated. |
| sample: numa-cutover:1624 backend⇒linkage | orch e91305c1 | GENUINE | Parametrized tests pass. |
| sample: gpu-tie-in:390 GPU-ZOS-2.2 | no SHA; BUILD-COMPLETE.json in tmp | **PARTIAL** | No kernel-store build exists. The libggml sha256 gate passes by construction, because the libraries were relinked from the champion's own objects. `gpu_test_ran:false`. A "NOT MET" sub-bullet is still present, and the sub-task was ticked for the same build (two ticks for one build). |

## refactor: 7 of today's ticks plus 5 sampled unsupported ticks

| item | cited evidence | verdict | reason |
|---|---|---|---|
| roofline:2510 WRAP-4 | root 6c7b2bf07; review doc; selftest 6/6 | GENUINE | The owed re-examination was done: 9 conclusions withdrawn and the wiki corrected. The sampler fix was already in place since 09-16, and the doc says so. |
| eval-tower:783 EV-14g | orch e60e5188; test_ev14g_completed_count.py (2 pass) | GENUINE | Completed count flows end to end. The commit also carries ruff churn. |
| kpf:598 KPF18-R4 code read | root 6c7b2bf07; AUDIT.md + EVIDENCE.json | GENUINE | The mechanism is named, and the spot-checked line references match the pinned tree. Shares a SHA with WRAP-4 but is a different task. |
| loop-fleet:610 screener paraphrase | root 3e86fa5ec; 81 pass | GENUINE | Truncation removed, and a guard added against text mismatch. |
| promptforge:197 MHS-10 | orch 86f9985e | GENUINE | The deliverable is a formatting-only commit, and `ruff format --check` passes. |
| refactor-multirepo:275 ni63 re-pin | orch d094546e; test (5 pass) | GENUINE | Closed with the operator-approved record-not-assert design. |
| repl-emb:266 REPL-EMB-2.13 | "orch 5c1dfea7" | GENUINE work, wrong SHA, re-count | 5c1dfea7 is an unrelated 10-31 commit. The real work is orch `23560c8e` from 10-24 (confirmed). Only a 35-test subset was run, not the full flag-on suite. |
| sample: rebuild:2813 R24-9 tripwire | research 8b1cdb6fb (11+1 skip) | GENUINE | Ticked 10-30. |
| sample: rebuild:1178 R21-1 headline | research bebe42b9a (4 pass) | GENUINE | Ticked 10-30. |
| sample: autopilot:206 evidence-durability guard | research a4da03e04 | GENUINE, re-count | Fixed 08-04 by an earlier session and ticked 10-30. |
| sample: kv-compaction:317 KV-2 | orch 9c507dff (50 pass) | GENUINE | Ran ahead of the KV-1 gate, but that is an ordering issue, not a correctness one. |
| sample: evidence-plane:133 (Z) log retention | orch 4cd6622f (+5/−1) | **PARTIAL** | Only `>`→`>>` in the legacy `start_servers.sh`, which nothing calls. Production already appended since 08-04, so the real 08-11..08-20 retention hole is undiagnosed. No test. |

## Items to reopen
1. **codex3, AK-PM-12** (`autokernel-research-loop.md` ~5457). Wire `lesson_native.produce` into a real AK write path, configure the cap, and capture at least one receipt.
2. **codex3, GPU-ZOS-2.2** (`gpu-serving-tie-in-program.md` ~390, plus its "byte mismatch" sub-task, which was ticked for the same build). Needs a kernel-store build, an independent (not relinked) libggml comparison, a GPU test run, and the NOT-MET sub-bullet cleared. Alternatively, reword the row to say only what was accepted.
3. **refactor, (Z) llama-server log retention** (`evidence-plane-instrument-repair.md` ~133). Diagnose the real production-path hole, fix it, and add a test.

Evidence corrections that need no reopen:
- **refactor REPL-EMB-2.13:** cite orch `23560c8e`.
- **ni AKX-AUTO-11:** cite the 10-22/23 commits.
- **ni longctx patch:** cite the 10-07 regeneration.

## Remove from the 10-31 quota (work is real but not done today)
- **ni (10):** UFH14-DEPLOY-EC-2e, AP N-way metric, AP substring-503, AP-69, WRAP-14 (all ticked 10-29/30); AKX-AUTO-11; longctx patch; E3 SCORE-07; C4-01 reconcile; `q*` labels.
- **codex3 (4):** KV-6, CH-20.2 (another session's work), ID-11, RVP-C2-12.
- **refactor (1):** REPL-EMB-2.13.

## Patterns
1. **Evidence backfill counted as new ticks.** ni's root commit `a5b9cd857` (10:22Z, after the 09:15 baseline; subject "record G2 detector library completion") rewrote 5 box lines ticked on 10-29/30 to add SHAs. The scoreboard counts that as 5 new ticks today. This is a scoreboard flaw as much as worker behaviour. **Fix:** score by the date of the first `[x]` flip (blame or the ✅ date), not by when a box became "evidenced".
2. **"HEAD at verification" SHAs.** Several ticks cite an unrelated commit that happened to be HEAD when the item was re-verified: ni AKX-AUTO-11 and the longctx patch, refactor REPL-EMB-2.13, codex3 KV-6 and RVP-C2-12. This passes the scoreboard's SHA regex while hiding that the work is weeks old. Make the rule "cite the commit that implements the ask".
3. **Stale-open sweeps.** Closing boxes for work done in July, August or early October (ni E3, `q*`, C4-01; codex3 ID-11, RVP-C2-12, CH-20.2; refactor evidence-durability) is useful hygiene, but it is not code throughput. These should be classed as "closure of prior work" and excluded from the 50/day quota.
4. **Sub-step ticked as the whole task.** AK-PM-12 (schema without the producer), GPU-ZOS-2.2 (relinked build, no GPU test) and (Z) log retention (the legacy launcher only).
5. **Task text rewritten at tick time.** Examples: codex3 M-21, EV-15b, G2-CONC-SHORT, TD-15a, P6.7. These are mostly benign rephrasing into a resolution title, but it moves the identity and makes items invisible to the scoreboard; EV-15b and 8 other ticked items don't match by text any more. M-21 dropped the original premise.
6. **Durable evidence in `/mnt/raid0/llm/tmp`.** ni AP N-way and AP-69 logs are already gone; codex3 LOOP-23's script and tests and GPU-ZOS-2.2's build exist only in tmp.
7. **Not observed:** fake SHAs, placeholder tests, declines counted as done, or one task split into several ticks. The one exception to the last is the GPU-ZOS-2.2 parent plus sub-task.

## Side finding (subagent-reported, not re-verified by me)
3 tests in orch `tests/unit/test_autopilot_planner_providers.py` (`test_local_chat_alias_*`) fail on origin/main after orch `63fd32d5` (10-30) added `x_request_source` to the planner payloads.

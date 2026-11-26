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

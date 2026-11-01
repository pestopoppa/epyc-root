# VB-YARN-E1-MEM-PHASE-WIRE investigation

Date: 2026-11-01
Scope: read-only inspection; no repository edits and no compute launched.

## Finding

The producer is the external live packet at `/mnt/raid0/llm/tmp/codex-ni-next-gpu-prep-20261031/run.py`, archived for review at `artifacts/compute/ni-yarn-e1-mem-prep-20261031/run.py`. It is a native diagnostic runner for six E1/W × A0/A1 × low/high phases. It already captures some of the hard-to-reconstruct source evidence at run time: model size plus edge hash, per-launch image path and PID, exact server argv, resident ggml paths, own-PID KFD samples, hipMalloc shim trace, native reports/calls, completion/partial markers, and phase analysis. Each attempt owns and cleans up its launched processes. The launch pins and original input-file hashes are retained separately.

The preparation implements admission/readiness, not belief wiring. There is no YARN-E1-MEM adapter or producer-side ClaimTuple write hook in `scripts/vidya`; the only references are the source-table enrollment and historical YARN-family notes. The existing shared measurement contract is `scripts/vidya/claim_tuple.py` and the adapter registry; the source must project through it and let `claim_tuple.grade()` decide. The current source-table row (README line 145) already correctly calls this a prospective measurement candidate and says smoke is qualification only. The handoff task (line 79) also correctly requires preserving native claim context and a real planning-context canary.

## Evidence and limits

- The 2026-10-31 smoke passed: `SMOKE-RECEIPT.json` records rc 0, cleanup verified, and launcher digest; `evidence/KFD-SMOKE-SUMMARY.json` records eight own-PID KFD samples spanning the first request (0.315–36.783 GiB). `out/E1-A0-low/{launch.json,runtime-proof.json,smoke-result.json}` proves the first load/response and correct image-local libraries. These establish admission plumbing only.
- The actual six-phase measurement did not run. `CUTOFF-TEST-PARTIAL.json` says `PARTIAL`, `stop-file-or-window-end-before-step`, and `completed_steps: []`. The prep README explicitly says `out/RESULT.json` is absent until a keeper grant executes the native job. No native phase reports, `kfd.jsonl`, allocation traces, or `complete.json` exist in the archived preparation packet. The live external packet listed additional attempt state, but nothing inspected changes the archived record's no-completed-steps conclusion.
- Thus the old 2026-10-04 records and this smoke cannot be retrofitted into a measurement tuple. Any future completed/incomplete phase attempt must preserve context at creation; aborted attempts remain explicit partials/unknowns.
- `gitnexus status` returned “Repository not indexed”; no re-index was run because this investigation made no source edits.

## Compute-row feasibility

Yes: a valid **diagnostic compute queue row** was already publishable and is present. `artifacts/compute/ni-yarn-e1-mem-prep-20261031/evidence/READY-ROW.md` records the READY row for `codex-ni-yarn-e1-mem-phase-r1-20261031`; `evidence/ARMED-ROW.md` records the ARMED snapshot and PID. The smoke gate and validator are retained (`evidence/SMOKE-PASS.log`, `SMOKE-RECEIPT.json`, `evidence/VALIDATOR.txt`), so the row was not merely hypothetical. It is a diagnostic booking, not an enrollment or grant result; ARMED does not mean the measurement ran. A valid row cannot be interpreted as a belief measurement and does not make the source “wired.” The row has enough run identity/limits, stop/result paths, source and launcher hashes, raw evidence retention globs, and a strictly scoped diagnostic proposition to schedule prospective capture.

## Shortest actionable sequence

1. Extend the live producer at native record creation (including every partial/failure path): give every phase/attempt a stable run/attempt ID; write a versioned claim-context sidecar bound by digest to that phase's report, `calls.jsonl`, KFD and hipMalloc records. Include UTC and monotonic bounds, exact image and model pins, original E1 input manifest/digests, arm and phase, source/launcher digest and argv, own PID/process start identity, observed samples/trace locators, missing/failed/partial reasons, and cleanup/result status. Do not infer these later from directory names or archived logs.
2. Add one strict YARN-E1-MEM adapter under `scripts/vidya/adapters/`: refuse absent, mismatched, incomplete, or contradictory native context; project only the claim actually supported (per-phase memory/allocations observation) into the existing `ClaimTuple` measurement carrier; register no new grade. Preserve smoke as qualification metadata, never as a measurement.
3. Add focused conformance cases for complete, partial, absent-field and digest-mismatch records. Then exercise a **real planning-context canary** per `agent-loop-design.md` §“Wired is a canary result”: show a known committed conclusion and do-not-repeat history through actual planner context assembly. Synthetic adapter tests alone do not satisfy that gate.
4. Only after prospective record + adapter + canary succeed, update handoff/source-table status. Separately, run the already-published diagnostic row under its valid keeper grant to create actual phase observations. Neither queue admission nor canary substitutes for that run.

## Source locations inspected

- `handoffs/active/vidya-belief-substrate-program.md:79`
- `scripts/vidya/adapters/README.md:145` and historical YARN context at line 560
- `/mnt/raid0/llm/tmp/codex-ni-next-gpu-prep-20261031/{run.py,publish.py,BELIEF-WIRING-DRAFT.md}`
- `artifacts/compute/ni-yarn-e1-mem-prep-20261031/{README.md,run.py,publish.py,inputs/manifest.json}`
- `artifacts/compute/ni-yarn-e1-mem-prep-20261031/evidence/{READY-ROW.md,ARMED-ROW.md,SMOKE-PASS.log,SMOKE-RECEIPT.json,KFD-SMOKE-SUMMARY.json,VALIDATOR.txt}`
- `artifacts/compute/ni-yarn-e1-mem-prep-20261031/CUTOFF-TEST-PARTIAL.json`
- `docs/guides/agent-workflows/agent-loop-design.md:788-806`

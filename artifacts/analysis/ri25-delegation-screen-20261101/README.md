# RI-25 delegation evidence screen — 2026-11-01

## Result

**UNKNOWN; no role is declared foldable.** This is a bounded zero-inference evidence screen, not the full repeat-run/counterfactual replay named in RI-25. The available native records cannot score whether a folded arm is no worse, inspect task flips, establish repeat variation, tell when a chain needs a role's own context, measure context delivered, or count caller re-asks. The RI-25 checkbox stays open.

## Frozen record scope

The exact saved prefixes are described by [`prefix_manifest.tsv`](prefix_manifest.tsv), SHA-256 `a1a68362cc9c888c716f232d0223ffb12fcab276b7f6125bdf07bb8e6d786a08`. It has 280 entries (122 progress JSONL files and 158 compact runtime/benchmark JSON or JSONL files), full per-prefix SHA-256 and byte count, source device/inode, family, format, and per-file `verified_at_utc`. It totals 1,870,028,921 bytes. No raw log, prompt, answer, or database snapshot is included.

The original per-source selection ledgers are retained privately under the session scratch, with their exact native digests:

- `progress_manifest.tsv`: `51447f28811a58d6b284331e9ed717f230192800cbf55283945f18406b1cb036`.
- `candidate_manifest.tsv`: `fd228faf905b9f0db96e66301a4c6469b78bc8ad3d4acd810088a7014b7ccf41`.

Those ledgers contain nonessential source mtimes; this published manifest omits them. The prefix byte count and content digest define the reproducible cut. `verified_at_utc` is when that prefix was revalidated, not a claim that the set is an atomic snapshot. A retained `device`/`inode` pins the regular source file for rotation checks. Later appends beyond the prefix are ignored; a shorter, replaced, rotated, or prefix-drifted file is refused.

Source families in the manifest:

- `progress`: the configured orchestrator `logs/progress/*.jsonl` directory, selected from the host's active API configuration.
- `candidate`: all JSON/JSONL under `logs/` except the progress directory, plus JSON/JSONL under `data/bep_sandbox/` and `data/trace/`. This includes benchmark outputs/traces, planner/dispatch/serving logs, and `seeding_diagnostics.jsonl`.

Selection/read-set pins and the per-file freeze protocol are in [`source_readset.tsv`](source_readset.tsv) and [`selection_protocol.md`](selection_protocol.md). The progress prefixes run 2026-02-27 through 2026-10-03. That last stored event bounds this file set; it does not prove the current runtime cohort is complete. The active API master plus six workers were observed on host with CWD `/mnt/raid0/llm/epyc-orchestrator` and no `ORCHESTRATOR_PROGRESS_LOG_DIR` override. Pinned `ProgressLogger` resolves its default there to `logs/progress`.

The per-prefix replay summary (all rows parsed, no source bytes displayed):

| Family | Files | Prefix bytes | JSON records | Invalid records | `delegate:` values | Generic `delegat` substrings |
|---|---:|---:|---:|---:|---:|---:|
| progress | 122 | 1,800,546,356 | 1,934,495 | 0 | 0 | 11,150 |
| candidate | 158 | 69,482,565 | 114,715 | 0 | 0 | 3,628 |

Requested-role `delegate:<role>` occurrences are zero for `worker_math`, `worker_general`, and `worker_summarize`. Generic substring counts are diagnostics only; they are not call counts. The output preserves any explicit `delegate:` hit as a path/line/JSON-field locator, value hash prefix, and role or `UNMAPPED:<hash>` classification without exposing raw string contents. No such hits occur in the scanned JSON/JSONL prefixes.

### Other read-only stores

`data/trace/events.sqlite` was read through a consistent SQLite online backup (private snapshot SHA-256 `0f7b1337c99e619b890c9ab3a91d9b2e8ae99414054337a3c8e986b442f1ec0e`; snapshot not included). It has 12,092 general events through 2026-10-22. Its one literal `delegate:` marker is event 4465, a `session_summary` document mention at `/workspace/progress/2026-02/2026-02-04.md:412`, role token `coder_escalation`, detail-body hash prefix `46c9dbe982f2b4c4`; it is not a call record. The live DB's size and mtime were unchanged across backup. The REPL session DB was separately backed up read-only (private snapshot SHA-256 `2e1d5e47507932e8ae50f9576853b6f67671158b0d6a1b7ede1a74435ee7b193`); it has zero sessions and zero checkpoints. Snapshots remain private.

The benchmark `delegation_events` field in `seeding_diagnostics.jsonl` has 500 events, all to `coder_escalation` (281 from `architect_coding`, 219 from `architect_general`). It records task summary, success, elapsed time, and generated token count, but no exact worker input, delegated answer, or caller follow-up. No requested-role calls can be scored from it.

## Source-path evidence and limitations

On the pinned orchestrator source:

- `src/repl_environment/routing.py` forms delegate input from up to `self.context[:4000]` plus the brief. The in-memory `_delegations` row has caller/target roles, reason/persona, `prompt_preview=brief[:100]`, timestamp, success, elapsed time, and result length; it does not retain the actual truncated context or result.
- Both `src/api/routes/chat.py` and `src/api/routes/chat_pipeline/stream_adapter.py` persist only preview, target role, and success, then clear `_delegations`.
- `orchestration/repl_memory/progress_logger.py` accepts adapter keyword `strategy_used` and serializes the value as `data.strategy`. The corpus scanner checks every string value recursively, so a zero result is not explained by querying the wrong field.
- Current `orchestration/launch_manifest.yaml` maps the three requested role aliases to the shared endpoint. That does not prove historical per-record model identity; the delegation event schemas have no per-call model ID.

| Role | Matching structured records in this frozen scope | Actual context sent | Own-context need | Caller re-ask | Fold result |
|---|---:|---|---|---|---|
| `worker_math` | 0 | UNKNOWN (code cap is up to 4,000 chars plus brief; actual length not recorded) | UNKNOWN | UNKNOWN | No comparison available |
| `worker_general` | 0 | UNKNOWN (same) | UNKNOWN | UNKNOWN | No comparison available |
| `worker_summarize` | 0 | UNKNOWN (same) | UNKNOWN | UNKNOWN | No comparison available |
| Other/unknown roles | 500 benchmark delegation events to `coder_escalation` | UNKNOWN | UNKNOWN | UNKNOWN | Outside requested roles |

The counts describe only the frozen evidence scope. They do not mean no actual calls occurred. No model was run, no serving path changed, and no counterfactual score or fold claim was invented.

## Reproduce

From this capsule directory, use the orchestrator source tree whose files match the manifest:

```bash
python3 scan_delegation_prefixes.py \
  --root /mnt/raid0/llm/epyc-orchestrator \
  --manifest prefix_manifest.tsv \
  --output replay.json
python3 -m unittest -v test_scan_delegation_prefixes.py
```

To replay only one exact manifest path, add `--path logs/progress/2026-02-27.jsonl`; `--family progress|candidate` selects one source family. The scanner reads exactly each saved prefix, never the growing tail. It refuses missing/short files, symlink paths, path traversal, source replacement/rotation, timestamp-format errors, or prefix SHA-256 drift. It is import-safe; scanning occurs only through the CLI/function call.

## Belief-kernel handoff

A proposed, subordinate append to the existing `VB-EVL34-DELEGATION-WIRE` asks future prospective captures to bind caller/task/turn, target role and per-call model, exact worker-input length/hash plus protected replay reference, delegated-answer hash/reference, repeat identity, and caller follow-up linkage. It reuses the existing carrier and grade. The prepared patch preserves the original handoff task and its unchecked state; the parent session applies it after review.

# PIP02 R36 pin triage — 2026-11-07 (operator E3 "R36 rebuild + SLIDERS as filler")

Zero inference, read-only. Source: `/mnt/raid0/llm/tmp/micron-import-20261105/codex3-pip-pool0-merged-r35-20261031/source-pins.json`
(1,052 pinned digests; `pool.py:167,185` asserts every one at start and dies with `pool source changed`).

## Result

- 1,052 pins. After mapping the micron-relative r35 and r25 paths to their raid0 copies, **39 pinned files are gone** from raid0
  (reaped `pip02-pipeline-prep-20261029/`, `rtg28-e2-nodelete-successor-20261029/`, `rtg56-td29-m0a-raw-v5-20261029/`,
  `evl39-e3b-server-witness-20261029/`, `inf51-streamingllm-full-20261029/`, `codex3-pip-pool0-recovery-20261031-0638/`,
  `codex3-pip-pool0-partial-20261031-0644/`, `codex3-pip02-paddle-parallel-r2-20261029/`, r14 smoke captures). Plus
  `/usr/bin/python3.12`, which exists only in the host root. Full list: `r35-pin-triage.json`.
- **7 of the 39 are recoverable by content hash** from committed artifacts (`r35-pin-recoverable-by-content.json`): `pidfd_custody_v2.py`,
  `pidfd_subreaper_v3.py`, `R11-RETIREMENT.json`, `OLD-STOP.json` (= `R27-STOP.json`), `INVENTORY.json`, `INSPECTION.json`, `region_generic.py`.
- **32 are unrecoverable.** 10 of those are Python modules the pool code IMPORTS at run time from the reaped directories
  (`sys.path[:0]=[BASE,E2,RTG,YARN]`, `parallel_owner.py:78,93`): `owned_window_v7`, `external_monitor`, `grant_gate`, `source_witness_v2`,
  `cpu_witness_v5`, `bounded_writer`, `venv_witness`, `trace_capture`, `server_witness`, `cpu_projector_witness`. The other 22
  (r14 smoke `capture.json` x10, recovery/audit JSON and scripts, `journal.py`, `bounded_log_live.py`, `population.json`, config/hash JSONs) are
  forensic or not imported by the pool.

## Consequence for the operator's decision

"Rebuild the pins without the reaped inputs" is sufficient for the 22 forensic pins and for the 7 recoverable files. It is **not**
sufficient to run: 10 imported witness/custody modules no longer exist anywhere found, so a pins-only R36 would fail at import, not at
the pin assertion. A runnable R36 therefore means re-authoring those ten modules (or replacing the legacy custody stack with the v3
keeper's own grants / region-lock / STOP / disk-pause and a plain per-page job). That is code work, not a pin edit; it is NOT done here
and no English-run row was published.

## Exposure ledger recorded under the same decision (E3 option A)

Per the 2026-11-02 BRF-T3 re-read (`docs/design/backlog-refactor-2026-11/t3-evidence/exp06-custody-reread-20261102.json`, v8 inventory):
755 approved English pages = **690 PROTECTED_SCOPE_UNKNOWN** + **65 CANDIDATE_NO_OBSERVED_START** (13 whole shards, never started).
Operator 2026-11-07: the 690 are recorded as **permanently UNKNOWN exposures (never redrawn)**; the 65 never-started pages are KEPT in scope.
The 39 forensic pins are documented here as non-load-bearing except the 10 imported modules above.

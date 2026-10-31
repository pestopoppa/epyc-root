# LOOP-25 source candidate — review only

## Owner and source boundary

The maintained depth alarm is external to ROOT and is owned by workspace-58 (`ws58`):
`/mnt/raid0/llm/tmp/compute-flags/ws58-ready-depth.sh`. Its read-only baseline SHA-256 is
`c6770ae4812a9baabd10b85c1c239749f3de9bd45e98ed648b87ad9b047b7c0a` (mode 0644).
The native FILLERS table parser is `/mnt/raid0/llm/tmp/compute-flags/validate_fillers.py`,
SHA-256 `7ddfaa6b65de45a37d5f90bb9a6d186a071756977fac91d71aced55c053cd30e`.
The baseline copy and parser copy in this directory match those source hashes. No live owner
source, keeper, watcher, daemon, or shared scheduling state was changed.

The actual shell entry runs the inline Python body every 600 seconds. Its existing outputs are
`ready-depth.log`, the refactor `owner-reply.md`, the NI `OWNER-REPLY.json`, and every
`codex-channels/*.md`. `crontab -l` has no matching entry. The candidate retains the loop,
current CPU/GPU/whole-host depth count and low-depth wording, and adds a disk forecast to that
same alarm/output path. The disk alert also fires on its own if the projected reserve is unsafe
or required inputs are UNKNOWN.

## Forecast contract

- Read READY JSON manifests using the producer's existing `ready/*.json`, `hold`, and
  `grants/<id>.complete` conventions. Read ARMED rows from the existing 18-column `FILLERS.md`
  using `validate_fillers.parse_table`; parse the existing `est_output_GiB` note field.
- Deduplicate both carriers by exact row ID. Count one valid estimate when duplicate carriers
  agree; conflicting estimates, missing reservation estimates, malformed queue input, or parser
  failure keep the result UNKNOWN. A valid estimate on either carrier resolves a missing value
  on the duplicate carrier. It never silently becomes zero.
- Sample available bytes on `/mnt/raid0` and append the sample to the existing
  `ready-depth.log`, bound to the resolved target path and `st_dev` filesystem identity. The
  observed log contains only depth-count lines today, so growth starts as UNKNOWN. A projection
  is available only with explicit UTC samples, no conflicting duplicate timestamps, continuous
  samples at gaps no longer than 20 minutes spanning 7–9 hours, a fresh preceding sample, and
  positive measured net growth. Any within-window rise in free space (including a mid-window
  cleanup spike followed by consumption), target/device change, or non-positive segment leaves
  the rate UNKNOWN. The candidate projects the measured rate over 8 hours, subtracts deduplicated
  reservations, and uses the existing 150 GiB admission floor.
- Forecast at or below 150 GiB alarms. Missing/stale/conflicted growth or reservation inputs
  alarm as UNKNOWN; they do not produce a green/zero forecast. The first 7–9 hours after an
  owner-approved install therefore remain UNKNOWN until adequate history exists.
- Scheduling, manifest admission, grants, depth floors, and admission rules are unchanged.

## Evidence

- `LOOP-25.patch` is an exact patch from the captured baseline to
  `ws58-ready-depth-candidate.sh`; `patch --dry-run` succeeded and applying it to a private
  baseline copy produced a byte-identical candidate.
- `bash -n ws58-ready-depth-candidate.sh` passed.
- `flock` on `/mnt/raid0/llm/tmp/compute-flags/prep-locks/36-37.lock`, `taskset -c 132,133`,
  `OMP_NUM_THREADS=1`: `python3 -m unittest -v test_candidate_entry.py` — 5 tests passed.
  The tests execute the candidate shell entry against private FILLERS/READY/log/output fixtures;
  cover deduplication, arithmetic, exact 150 GiB cutoff, missing estimates, stale samples,
  mid-window cleanup rebound, target/device mismatch, ambiguous timezone, malformed history bytes,
  conflicting duplicate samples, parser failure, malformed table rows, completed ARMED rows, manifest ID mismatch,
  boolean estimates, and the alarm output path. The cutoff test fixes UTC clock and free-space
  bytes in explicit private test mode. `/usr/bin/time -v` recorded max RSS 15,440 KiB and wall
  time 0.50 s. No model, inference, grant, or service ran.
- `gitnexus status` reported the private lane is not indexed. `gitnexus impact parse_table
  --direction upstream --repo /workspace` returned LOW, 2 impacted nodes, but warned that the
  indexed ROOT commit is stale relative to the private lane. The external producer is absent
  from the index. Manual source/caller review found only the external shell entry and its listed
  outputs; no ROOT source caller exists.

## State

This is a reviewable owner-boundary source proposal, not an installed or adopted change. The
baseline source remains untouched. ROOT review approved the candidate subject to one final MAIN
check. The transfer bundle includes the prepared source-registration/follow-up draft; MAIN applies
those semantic files. No ROOT source, handoff, index, or checkbox has been changed here.

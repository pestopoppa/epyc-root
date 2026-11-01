# Refactor STALE-ARMED audit

Audit time: 2026-11-01 00:57 UTC (queue snapshot); PID presence checked during this audit.

## Scope and result

`queue_status.py` reports 87 `STALE-ARMED` rows in the full queue. Owner counts are: `codex3` 62, `codex-refactor-01a16fc3` 19, `codex-ni` 4, `codex-wrap-checks` 1, and `refactor` 1. Thus the exact refactor-owned scope is **20 rows**, not approximately 80. I treated both explicit refactor owner labels as in-scope and excluded other owners, including `codex3`.

The read-only classifier finds each row `ARMED` but without a live launcher PID that validates for that row. All 20 recorded PIDs below were absent at `/proc/<pid>` when checked. This establishes dead/missing processes at audit time; there is no live process to stop. PID absence alone does not prove whether the underlying work is still wanted.

## Exact refactor-owned rows

| Owner | Filler ID | Recorded launcher PID | Recommendation |
|---|---|---:|---|
| codex-refactor-01a16fc3 | refactor-xgrammar-a2-alternated-profile-20261027 | 2227581 | Withdraw stale arm; re-arm only if this diagnostic is still needed |
| codex-refactor-01a16fc3 | refactor-01a16fc3-hil15-discovery-s0-20261028 | 2483357 | Withdraw stale arm; re-arm only if this cohort shard is still needed |
| codex-refactor-01a16fc3 | refactor-01a16fc3-hil15-discovery-s2-20261028 | 2498605 | Withdraw stale arm; re-arm only if this cohort shard is still needed |
| codex-refactor-01a16fc3 | ufh14-a3a-single-warm-20261028 | 518909 | Withdraw stale arm; re-arm only if this measurement is still needed |
| codex-refactor-01a16fc3 | refactor-01a16fc3-m4-gpu-quality-r8-20261028 | 874730 | Withdraw stale arm; successor exists in queue history; re-arm only if r8 remains required |
| codex-refactor-01a16fc3 | codex-hil15-s2-resume-v1-20261029 | 3797575 | Withdraw stale arm; later resume revisions exist; do not revive v1 without confirming it is still the intended task |
| codex-refactor-01a16fc3 | codex-hil15-s2-resume-v2-20261029 | 177263 | Withdraw stale arm; later resume revisions exist; do not revive v2 without confirming it is still the intended task |
| codex-refactor-01a16fc3 | yarn-oolong-s2-nodelete-eligible26-v21-20261029 | 1278902 | Withdraw stale arm; newer revisions exist; re-arm only if v21 is still required |
| codex-refactor-01a16fc3 | yarn-oolong-s0-nodelete-eligible28-v22-20261029 | 1279309 | Withdraw stale arm; newer revisions exist; re-arm only if v22 is still required |
| codex-refactor-01a16fc3 | yarn-oolong-s1-nodelete-eligible29-v23-r2-20261029 | 1320631 | Withdraw stale arm; newer revisions exist; re-arm only if v23-r2 is still required |
| codex-refactor-01a16fc3 | yarn-oolong-s3-nodelete-eligible27-v24-r2-20261029 | 1320818 | Withdraw stale arm; newer revisions exist; re-arm only if v24-r2 is still required |
| codex-refactor-01a16fc3 | codex-hil15-s0-resume-v4-20261029 | 1936748 | Withdraw stale arm; later unknown-preserving revisions exist; do not revive v4 without confirming it is still intended |
| codex-refactor-01a16fc3 | codex-hil15-s2-unknown-resume-v4-20261030 | 2061727 | Withdraw stale arm; later micron/split revisions exist; do not revive v4 without confirming it is still intended |
| codex-refactor-01a16fc3 | hil15b-bounded-output-r3-20261029 | 2062693 | Withdraw stale arm; later bounded/split revisions exist; re-arm only if r3 is still required |
| codex-refactor-01a16fc3 | codex-hil15-s0-unknown-preserving-v5-20261030 | 2524900 | Withdraw stale arm; v6 supersedes it; do not revive v5 |
| codex-refactor-01a16fc3 | codex-hil15-s0-unknown-preserving-v6-20261030 | 3826407 | Withdraw stale arm; later revisions may exist; re-arm only if v6 remains the intended task |
| codex-refactor-01a16fc3 | codex-hil15-s2-micron-v8-20261030 | 2519618 | Withdraw stale arm; later split revision exists; do not revive v8 without confirming it is still intended |
| codex-refactor-01a16fc3 | hil15b-split-output-r7-20261030 | 2490198 | Withdraw stale arm; re-arm only if r7 remains the intended task |
| codex-refactor-01a16fc3 | codex-hil15-s2-split-v9-20261030 | 3974590 | Withdraw stale arm; re-arm only if v9 remains the intended task |
| refactor | refactor-akxall8-c5-declared-floor-r2-20261031 | 3067159 | Fix/review rather than blindly withdraw: this is the most recent refactor-owned row and notes describe an unrun full R13; first confirm the campaign still needs that floor run, then re-arm through the admission gate |

“Withdraw stale arm” means correct the queue status/notes to reflect that no launcher is active and the row is not currently placeable. It does not authorize deleting the row, its files, manifests, outputs, or evidence. Where the task is still required, the remedy is a fresh launcher instance and PID after preflight, not reuse of a dead PID.

## Evidence and method

- Read-only queue command: `python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py --json`, with `--owner refactor --json` used to obtain the refactor subset. Snapshot timestamp: `2026-11-01T00:57Z`.
- The classifier reads `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md`, grants, and current process liveness. Every listed row is in the `STALE-ARMED` bucket with `status=ARMED`; its launcher PID is either dead or fails the row-specific process identity check.
- Independently checked `/proc/<recorded-pid>` for each of the 20 PIDs; all paths were absent. No process was signaled.
- Backing launcher/job/manifest paths and dry-run receipts are declared in the rows' notes. The task requested an audit only; no paths were altered and no files were deleted. A live launcher path or manifest is not sufficient to make an arm placeable: the process identity is dead, and a fresh admission/preflight is needed before a new PID can be armed.
- The row descriptions show several clear revision chains (HIL15 resumes, Yarn Oolong revisions, HIL15B bounded/split outputs). Those recommendations prevent reviving superseded arms. The AKX C5 r2 row is singled out for review because it is recent and its notes explicitly describe an unrun full R13; this is not evidence that the measurement is still authorized or needed.

## Safe sanctioned mechanism

Per `.claude/skills/inference-backlog-scheduling/SKILL.md` §1 and §2, only `ARMED`, `ready=y`, with a live matching launcher can be treated as queued/placeable. A stale arm should be demoted to `BACKLOG` with an accurate `blocker=missing launcher` (or withdrawn from active intent if obsolete). If still needed, prepare a fresh launcher and run the required same-entry-path `dryrun_check.py` admission/preflight before setting it back to `ARMED`; the row must carry the new live PID and matching source/admission evidence.

Queue-file edits are owner-controlled and atomic: make a dated backup, write a temporary complete file, then replace `FILLERS.md` atomically (`.tmp` + `os.replace`), following the queue protocol in `docs/guides/agent-workflows/compute-fillers.md` and the skill's queue-edit invariant. Do not delete launch files, manifests, grants, or process state as part of queue cleanup. This report performs none of those state changes.

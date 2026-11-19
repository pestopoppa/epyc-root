---
name: row-owner-loop
description: The row OWNER's loop in rowflow — scaffold and lint a measurement row, publish and PROVE it queued, arm one zero-token owner watcher, triage a run end into verdict.json, file it, tick the box with a belief tag and a register row, brief subagents with the versioned hard rules, verify every hand-back claim, and drive multi-phase programs and ratify bundles to a deliverable. Use when your session publishes epyc.row.v3 rows, waits on smokes or grants/<id>.ended, files verdicts, ticks result boxes, or dispatches subagents to build kernels/rows. Not for bin packing, keeper or grant-writer internals (inference-backlog-scheduling) or job-side launcher rules (compute-fillers.md).
---

# Row Owner Loop

prepare → lint → publish → **prove queued** → watch → triage → file → tick (+belief, +register) →
re-arm. Each step below is one paragraph plus its command; detail lives in `references/`.
Canonical protocol (do not restate it): `docs/guides/agent-workflows/compute-fillers.md` (launcher,
job side, publishing), `docs/guides/agent-workflows/backlog-churn-flow.md` (flow, the one rule no
gate may break), `.claude/skills/inference-backlog-scheduling/` (bins, keeper, STATUS/ETA format).
`S=/workspace/.claude/skills/row-owner-loop/scripts` below. What not to do: `references/stop-doing.md`.

## 0. Session start
Confirm your roster id (`scripts/coordination/session_bus.py drain --agent <id> --triage` must not
say "not a roster id"). Check checkout staleness (`git rev-list --count HEAD..origin/main`); run
churn tools from a current tree (the hub view `/mnt/raid0/llm/views/epyc-root-main` or a fresh
`origin/main` worktree), never the stale shared clone. Exactly ONE owner watcher (step 3).

## 1. Prepare a row
New row: `python3 $S/row_scaffold.py new <row-id> --handoff <file.md> --box <ID> --lane cpu|gpu
--regions <list> --threads N --units N --unit-s S --model "<model: …>"`. It writes spec/job/launch/
check_complete stubs with `estimate_s = units × unit_s × 1.25` and the arithmetic in the spec. Fill
QUESTION/RULE/STOP in `job.py` (written BEFORE any run), then seal `SOURCE.sha256` last. Existing
row, or after any edit: `python3 $S/row_scaffold.py --lint <dir>` must print `LINT OK`. It refuses a
predicate/check path outside the row dir (copied predicates gave a false smoke PASS, §2.6), CPU
regions touching 88-95/184-191, width wider than the literal threads, a stale seal, and box text
without bold ID / `model:` / stop rule / `est N s`. Never copy `estimate_s`, predicates or
`check_complete` from a predecessor.

## 2. Publish and prove it
`refresh_hub_view.sh` → `publish_row.py <spec>`. The proof is a file, never an exit code:
`ls compute-flags/ready/<id>.json` or `dryrun/<id>/*SMOKE-QUEUED.json` (with age). Never a second
publish, `--smoke-now` or a local "republish when the GPU frees" loop while a smoke may run — a
republish during a smoke unpublishes the row.

## 3. Arm the owner watcher (same turn)
`Bash(run_in_background) bash $S/watch_rows.sh --owner <id>` — one process for all your rows: ENDED
(unfiled `.ended` newer than its marker), SMOKE-FAIL (last launcher.out block only), QUEUED-DROPPED,
QUEUED-AGED, IDLE-GRANT (gpu/quarter busy < threshold for N samples). It prints one line and exits
on the first actionable event; handled ids go to its state file (`--ack <key>`), so there are no
hand-kept exclusions. Re-arm after every event. Never hand-roll per-row `until` loops.

## 4. Run end → verdict → FILED
`python3 $S/runend.py <row>` reads `out/RESULT.json` + the `.ended` record and drafts
`<row>/verdict.json` (DROP/FUTILITY*/STOPPED/rc75/rc143 → inconclusive or fail, never pass; the
rationale must cite numbers). Review the draft against the pre-registered RULE, edit, then
`python3 $S/runend.py <row> --file` — it files from a pinned detached `origin/main` worktree,
confirms `filing-done/<row>.FILED`, and prints the tick-line draft with its belief tag.

## 5. Tick
Re-read the box's own done-when text before ticking; a result on a different binary/tree than the
box names is a note, not a tick (§2.12). The tick line states the verdict and numbers on the line,
names the row id and commit, and carries `[belief: clm_<id>]`, `[belief: cc]` or
`[no-belief: <reason>]` (`agents/shared/SESSION_LIFECYCLE.md` → *Two axioms*). A `[belief: cc]`
tick gets its register row in the same or the next commit: `python3 scripts/vidya/cli.py
conclusion add --path … --line … --ref origin/main --stated-json … --actor <id>` (rows only from
numbers on the line). `runend.py --check-cc <file.md>` lists cc ticks with no register row.

## 6. Brief a subagent
`python3 $S/brief.py --goal … --box file.md:LINE --model sonnet --effort low --build claim|row|none
--report "…"`. It renders the versioned HARD RULES block (`references/hard-rules.md`), the git
protocol, the forced build clause (region-lock claim or booked build row — never bare `taskset`) and
the report contract (prove claims; stop your own background tasks before hand-back).

## 7. Hand-back triage — verify every claim yourself
"Pushed" → `git cherry origin/main <branch>` empty / `git branch -r --contains <sha>`. "Published"
→ `ls ready/<id>.json`. "Smoke PASSed" → the LAST block of `dryrun/<id>/launcher.out` plus
`dryrun/<id>/PASS.json`. Then `TaskStop` the agent's leftover background tasks, file/tick, and
dispatch the next phase in the same turn. Checklist: `references/handback-checklist.md`.

## 8. Programs and ratify
Multi-phase work: file P1..Pn with done-when and dispatch class in the owning handoff before the
first dispatch, then drive it with no intermediate checkpoints (`references/program-plan.md`).
Operator signatures: apply-tested, one single-line fish-safe command, independent review before
it is handed over (`references/ratify-prep.md`).

## Tests
`python3 -m pytest -q /workspace/.claude/skills/row-owner-loop/tests`

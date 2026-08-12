# Consolidated unblock

generated 2026-07-29T06:02:04+00:00  ·  epyc-root @ 8cbe50c0
pending 2 · granted 1 · struck 0 · malformed 0

## The one command

    bash /workspace/artifacts/operator/unblock.sh

It applies every gate you ticked, skips the rest, and reports what it did.
Add `--plan` to see what it would run without running anything.

## How to adjudicate

Edit `coordination/session-bus/tokens/token-queue.md` — the only file whose
checkboxes you own:

    - [x] **GATE-ID** … GRANTED 2026-07-27      apply it
    - [ ] **GATE-ID** … STRUCK 2026-07-27 — why  decline this round; stays held

Leave a line untouched to decide later. Never delete a line: a missing gate
reads as *absent*, not as *declined*. An ISO date is required — an undated
grant leaves no record of when you gave it.

## Awaiting your decision

### triage

- holds: _no task currently held_
- requested by `claude-main` for `m5-flag-triage`
- pre-validated (dry-run exit `0`): flip validated on a temp copy of config.yaml: anchor unique, replacement applied, YAML still parses. enables the M5 one-shot triage hook: dead-agent block drafting + routing annotations, budget-capped by triage_calls_per_day (still 0 — raise it separately)
- command:

      /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -c "import pathlib,sys;p=pathlib.Path('/workspace/coordination/session-bus/config.yaml');t=p.read_text();old,new=sys.argv[1],sys.argv[2];assert t.count(old)==1,'anchor not unique';p.write_text(t.replace(old,new))"  'triage: off' 'triage: on'

### headless-worker

- holds: _no task currently held_
- requested by `claude-main` for `m5-flag-headless-worker`
- pre-validated (dry-run exit `0`): flip validated on a temp copy of config.yaml: anchor unique, replacement applied, YAML still parses. raises the headless-worker cap from 0 to 2
- command:

      /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -c "import pathlib,sys;p=pathlib.Path('/workspace/coordination/session-bus/config.yaml');t=p.read_text();old,new=sys.argv[1],sys.argv[2];assert t.count(old)==1,'anchor not unique';p.write_text(t.replace(old,new))"  'max_headless_workers: 0' 'max_headless_workers: 2'

## Ticked, awaiting the next apply

- `OP-SENDKEYS-CODEX`


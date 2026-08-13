---
name: log
description: Persist a worker main's completed, blocked, or partial task boundary as an idempotent private-lane checkpoint. Use when mainA-mainD finishes a task, reaches a non-movable blocker, needs a durable checkpoint before clearing or closing, or is told to run /log instead of the full wrap-up.
---

# Log Worker Checkpoint

Run the deterministic checkpoint engine. Do not manually reproduce its mutation,
commit, push, receipt, or bus-publication phases.

## Gather exact inputs

1. Copy the task text exactly from its open checkbox in one active, non-index handoff.
2. Use the dispatch `task_id`. For a later partial/blocked boundary on the same task,
   provide a new stable `--boundary-key`, such as `attempt-2`.
3. Choose `completed` to flip the exact task checkbox, `blocked` for a non-movable
   blocker, or `partial` only at a pre-reboot boundary. Nonterminal outcomes leave
   the source task open and add a checkpoint-keyed child task.
4. Name every worker-owned artifact with repeated `--path`. Never include another
   handoff, another agent's progress shard, an index/generated artifact, or `wiki/`.
5. Supply one or more task-specific validations as JSON argv arrays. They execute
   directly without a shell after the handoff/progress mutations and before commit.
6. For `blocked` or `partial`, supply every structured blocker field. A compute
   blocker also requires a typed JSON compute request.

## Run

```bash
python3 scripts/coordination/worker_checkpoint.py \
  --agent mainA \
  --task-id TASK-ID \
  --task-text 'Exact checkbox text, including Markdown' \
  --handoff handoffs/active/owning-handoff.md \
  --outcome completed \
  --summary 'What changed and what validation passed' \
  --spec-ref 'handoffs/active/owning-handoff.md#stable-task-anchor' \
  --boundary-reason task-boundary \
  --next-context related \
  --validation-json '["python3","-m","pytest","-q","tests/focused_test.py"]' \
  --path path/to/owned-artifact
```

For a blocked boundary, add:

```bash
--blocker-class dependency \
--blocked-on 'Specific unmet condition' \
--blocking-owner-or-event 'Named task, owner, or external event' \
--evidence-ref artifacts/evidence/blocker.json \
--alternative-exhausted 'Concrete in-scope alternative already attempted' \
--resume-action 'First executable action after unblock'
```

Use `--blocker-class compute --compute-request-json '{...}'` for compute. For a
partial pre-reboot checkpoint, use `--outcome partial --boundary-reason pre-reboot
--next-context pre-reboot` with the same blocker evidence.

## Handle the result

- Treat exit `0` plus `bus_publication.status=published` as the only successful
  real checkpoint. The stdout object separates `journal_receipt` from the
  schema-validated `bus_publication.envelope` and message ID.
- The command publishes only after verifying the pushed ref. If publication
  fails, rerun the identical command; it resumes at publication without another
  commit or push.
- On interruption or a nonzero exit, rerun the identical command. The engine resumes
  from its private phase journal without duplicating task or progress entries.
- Correct any reported collision, ownership mismatch, foreign path, ambiguous task
  text, failed push, or unreachable pushed ref. Do not bypass the refusal.
- Do not run the full wrap-up. Index pruning, generated state, promotion, and wiki
  compilation belong to the Auditor transaction.
- `--bus-root` and `--no-publish` exist for isolated tests. Do not use
  `--no-publish` for a real worker boundary; the default targets the canonical bus.

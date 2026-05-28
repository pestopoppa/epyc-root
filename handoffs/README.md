# Handoff Documents

Handoff documents track work-in-progress for future sessions or agents. Start with the active master index, then follow the domain index that owns the work.

## Directory Structure

```
handoffs/
├── active/       # Currently active work and active coordination indices
├── blocked/      # Work awaiting dependencies or operator action
├── completed/    # Completed work retained for historical reference
└── archived/     # Historical or superseded work retained for reference
```

## Current Entry Points

As of 2026-05-27, `handoffs/active/` contains 84 non-index active handoffs plus 7 active coordination indices.

| Scope | Entry Point |
|-------|-------------|
| All active work | [active/master-handoff-index.md](active/master-handoff-index.md) |
| Routing, orchestration, autopilot, stack config | [active/routing-and-optimization-index.md](active/routing-and-optimization-index.md) |
| Inference speed, benchmarks, model acceleration | [active/inference-acceleration-index.md](active/inference-acceleration-index.md) |
| Single-instance CPU throughput, OpenMP, NUMA, kernel flags | [active/cpu-inference-optimization-index.md](active/cpu-inference-optimization-index.md) |
| Agent UX, Hermes, conversation management | [active/hermes-agent-index.md](active/hermes-agent-index.md) |
| Research, evaluation, monitoring | [active/research-evaluation-index.md](active/research-evaluation-index.md) |
| Capability pipelines: vision, PDF, Lean, TTS, KB-RAG | [active/pipeline-integration-index.md](active/pipeline-integration-index.md) |
| Blocked work | [blocked/BLOCKED.md](blocked/BLOCKED.md) |

## Handoff Lifecycle

```
CREATE   → handoffs/active/{topic}.md
WORK     → update handoff, relevant index, and progress/YYYY-MM/YYYY-MM-DD.md
BLOCKED  → move to handoffs/blocked/ when the work cannot proceed, or mark active handoff BLOCKED and list it in blocked/BLOCKED.md
COMPLETE → extract findings, move to handoffs/completed/, and update every index that linked it
ARCHIVE  → move superseded or historical material to handoffs/archived/
```

## On Task Completion

When a handoff task is complete:

- [ ] Extract durable technical findings to the relevant docs, wiki, or research deep-dive.
- [ ] Record key metrics in the relevant benchmark/result artifact.
- [ ] Record process summary in today's `progress/YYYY-MM/YYYY-MM-DD.md`.
- [ ] Move the handoff from `active/` or `blocked/` to `completed/` or `archived/`.
- [ ] Update the owning domain index and [active/master-handoff-index.md](active/master-handoff-index.md).
- [ ] Update [blocked/BLOCKED.md](blocked/BLOCKED.md) if any dependency changed.

## Validation

Run `scripts/validate/check_handoff_freshness.sh` to find aging handoffs. Run a link-coverage audit before major wrap-up work so newly created handoffs are not stranded outside the indices.

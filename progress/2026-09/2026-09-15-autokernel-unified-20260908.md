# AutoKernel unified — 2026-09-15

## GLM-5.3-Flash relaunch checkpoint and dashboard correction

The GLM AutoKernel was relaunched after bounded controller repairs. The repair set covers
planner mechanism-family escape (`632939b0`), reduced CPU-source screening (`2db9d844`),
stopped-resume refusal accounting (`733bfaa6`), valid-overrun successor handling (`5f368aa2`),
and retained CPU candidate confirmation without duplicate rejection (`92a91c99`). These are
controller safety and accounting repairs; they do not change measurement thresholds or production
authority.

Batch 3 produced the first published whole-bundle confirmation and advanced the experimental
research anchor to `7e9f5eb`. Batch 4 generated a provisional successor. At this checkpoint the
campaign has 26 retained keeps and an unresolved `+0.855%` whole-bundle estimate versus its
campaign champion-of-record. It is not a verified champion improvement/regression and it does not
authorize promotion: retained keeps remain on their own timeline until a decisive checkpoint.
Production stays frozen at `production-consolidated-v9` (`0db32c06e3e5`, binary 10125).

ROOT `35746b46` corrected the headline plot so a campaign accumulator, direct champion movement,
and production-era evidence cannot be read as one continuous acceptance curve. The live page now
marks unresolved accumulator estimates, singleton milestones, direct-endpoint discontinuities and
unjoinable production receipts explicitly, while retaining v9 as the serving-era baseline.

The active monitor has three clean completed iterations and batch 5 live. Its remaining objective
is 20 healthy completions; unexpected behavior requires safe stop, repair and relaunch. The monitor
does not itself validate the accumulated tip across required targets or promote a champion/production
candidate.

## Verification and scope

- Authoritative code commits are the five research controller fixes above and ROOT `35746b46`.
- The active handoff is `handoffs/active/autokernel-unified-surface-program.md` (AKU-12g/h
  checked; AKU-12i added open). No index row was edited by this subagent.
- No AutoKernel, dashboard, registry, serving process, or production kernel was stopped, reloaded,
  or changed by this wrap-up checkpoint.

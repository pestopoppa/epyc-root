# 2026-10-30 — LB4.9 combined READY focused wrap

The combined LB4.9 diagnostic packet `codex-ni-lb49-combined-ready-20261030` was published as a NORMAL rank-5 diagnostic row for any CPU quarter, 739 GiB, 1800-second minimum and 7200-second window. Its admission reserves a 4 GiB RAID output cap plus 150 GiB floor. The corrected op matrix covers 72 exact H64/KVH1 sink cases: per-head-distinct, zeroed-present and null-control sinks at thread counts 1, 16, 32, 64 and 96. The inherited NMSE threshold remains 5e-4 (lower is better); max/mean absolute error are descriptive.

The scheduled DS41 plan uses an independently linked baseline-off binary to generate 65 positions (prefill step 0 plus 64 forced steps) for three fixed prompts, repeats from fresh KV, then uses a separately linked feature-on binary to replay the pinned baseline tokens. It includes an open-ended prompt and does not substitute a feature-off replay. A same-launcher Gemma 1B smoke passed the 72 op cases, baseline generation and fresh-KV repeat, feature-on replay, token transport, reader/writer and captured-child cleanup in 12.364536 seconds; peak RSS was 1,150,750,720 bytes and the baseline repeat was bitwise equal. The no-argument RUS3=1 poller and real cutoff-75 cleanup path also passed. These are plumbing observations, not DS41 acceptance or a measurement warrant.

The active LB4.9 handoff now records this qualification while FU-OPCASES-01, FU-DIVERGE-05a and FU-DIVERGE-06 remain open. Thin-margin acceptance remains unmet if the run observes no baseline margin below 1. No fold, new tolerance, performance or promotion claim follows. The prospective combined-source writer/reader/planning-canary task was added to the Vidya substrate program; it must use the shared measurement carrier and `claim_tuple.grade()`, with no new ladder or backfill. [belief: cc]

README freshness check warning (checker-relative child paths; no placeholder README was created):

```text
## README freshness warnings

`check_readme_freshness.py` flagged 2 of 3 owned READMEs. Refreshing them is part of the /wrap-up routine itself (step 4b) — there is no owning handoff, and there should not be: this is a recurring obligation with no terminal state, so it cannot be 'completed'.

- **epyc-orchestrator** (`/mnt/raid0/llm/tmp/epyc-orchestrator/README.md`)
  - README.md missing entirely at /mnt/raid0/llm/tmp/epyc-orchestrator/README.md
- **epyc-inference-research** (`/mnt/raid0/llm/tmp/epyc-inference-research/README.md`)
  - README.md missing entirely at /mnt/raid0/llm/tmp/epyc-inference-research/README.md
```

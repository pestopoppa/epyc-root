# SPEC-GRAM.3 r2 CPU repair preparation packet

Prep-only durable packet for `codex-ni-specgram3-llg101-cpu-r2-20261101`. It keeps the original r1 failed receipt immutable, stages the accepted dynamic-CPU correction, and makes the production qualification refusal explicit. No result is a scientific measurement, READY, official grant, keeper HARD qualification, or cost/parity/replay verdict.

## Contents

- `r2-source/`: proposed r2 executable job/launcher, unchanged SPEC-GRAM3 source inputs, pins, row, canonical and fixture source manifests, and packet README. Runtime files remain bound to the host scratch path recorded in their contents.
- `canonical-v14-source/`: byte-identical published source snapshot for nonproduction testing, pinned to ROOT `4d6db587b3799d4baee8ab4644c4f2e9acac0ef4` and foundation `11ce`. Production install target is `/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1` and awaits keeper deployment.
- `tests/` and `evidence/`: CPU-claim behavior tests, real-entry plumbing tests, captured logs, and the original r1 filing summary/receipt digests.
- `drafts/`: the progress and handoff text prepared for this wrap. The progress entry is applied to `progress/2026-11/2026-11-01-codex-ni-01a16d6b.md`; a dated note is applied to the existing SPEC-GRAM.3 body, with its checkbox unchanged. No handoff index row is changed.

## Verified behavior

Canonical CPU behavior tests passed actual `24-47` and relocated `72-95` grants, malformed metadata, short/expired window refusal, and atomic boundary receipt. The model-free canonical qualification path passed only with `production=false`; its result writer and rc75 fixture receipt were checked. The separate direct nonproduction cutoff fixture wrote UNKNOWN partial, returned 75, drained the child, and preserved the normal result digest.

Production `job_entry.sh` refuses a `production=true` manifest before calling any fixture or starting science work. Both it and direct fixture invocation also refuse a missing production field and a string-valued `"false"`; only JSON boolean false enables the toy. This is a tested guard, not a production qualification.

The science job's pinned model size is 37,801,097,504 bytes; existing cutoff evidence had approximately 37 GiB peak RSS. No native/model smoke was attempted within the R11 <=8 GiB cap. The actual same-job production qualification, keeper HARD proof, and 24-thread throughput measurement remain pending. Therefore there is no READY publication or science result.

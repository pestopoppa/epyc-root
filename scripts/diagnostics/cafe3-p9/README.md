CAFE-3 CPU P9 experiment
======================

`runtime.py` binds the existing native multi-arm capture and offline P9 grader
to a scheduled CPU row. Inputs were sealed outside the grant. Scheduled code
checks model filesystem identities without reading their weights. It validates
the full CPU r3 build using the trusted producer validator and binds the exact
official grant, actual CPU affinity, threads and deadline through retained
per-arm contexts before any model process starts. Every arm uses the same
command, build, target, draft and protocol; only request width, adaptive opt-in
and per-process output identities differ.

The protocol uses the local Qwen3.8-27B Q8 target and DFlash2 Q8 draft, static
widths 0..3 and adaptive cap 3. Fixed order: static-0, static-1, static-2,
static-3, adaptive. Each arm runs two repetitions of three authored prompts
(code, prose, reasoning), at most 256 output tokens per request: 30 requests,
7,680 maximum output tokens. No request retries or automatic sample extension.
Context is 4,096 tokens, one parallel slot, CPU-only target/draft, flash
attention off, minimum draft width/probability zero. DFlash2 is selected by
the draft model metadata under the native `dflash` implementation.

The predeclared grader requires exact token identity versus static-0,
aggregate request-wall tokens/s at least 1% above the fastest static arm,
and same-request post-exploration zero-to-positive probe recovery within 128
completed rounds. Missing recovery is inconclusive. Late recovery or a known
identity/speed violation fails. Invalid/partial evidence refuses assessment.
Two repetitions and fixed whole-arm order support a descriptive scoped result;
they do not establish statistical significance, absence of timing drift, or
production promotion. Timing noise may exceed the 1% decision margin.

Native execution writes contexts, schedule, per-arm logs, process/request/round
captures, offline assessment and a hash-bound result under the packet's
`cafe3-p9/runs/`. A valid negative or inconclusive assessment completes the
experiment; completion does not assert P9 passed. Partial captures survive a
failure, and outputs cannot be overwritten. The existing prospective
`VB-CAFE3-ROUND-WIRE` source covers these native captures and P9 assessments;
this wrapper introduces no grading ladder or native wiring-canary claim.

The publisher smoke validates real sealed inputs and the qualified full build,
then executes that binary's `--help` under its local library environment and
checks the required speculative CLI options. It never loads models, creates
native launch contexts, or runs inference. Its receipt is a CLI qualification,
not a P9 verdict. Native execution is refused in smoke mode. The launcher pins
the input-inventory SHA-256, which binds runtime modules, prepared inputs,
protocol and full-build receipt. The prepared records bind externally retained
model files; this directory contains no model or binary copies.

Validation: six model-free row-boundary tests pass, covering grant-time weight
hash refusal, modified inputs, omitted static arms, smoke/native separation,
grant/common-command binding, and completed negative assessments with tampered
capture refusal. Run `python3 -m unittest discover -s
scripts/diagnostics/cafe3-p9 -p test_runtime.py -v` on one line.

Retained packet: `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/`.
The checked-in JSON and launcher record its exact input paths and content
identities. Full CPU r3 receipt SHA-256:
`5a75e3d994b485143c86b13b8abb1b4b2b87de1e801be222169f4f9671910978`.
Input inventory SHA-256:
`fe6598567dfe2c13d641c4cf8f4ff237492c7bd8907c8e467d7a1da9856d5827`.

[no-belief: experiment source and input sealing; no native P9 result]

Publication (2026-11-19)
------------------------

Row `df2-cafe3-p9-cpu-20261119` published with **smoke PASS**, cores
164–167, rc0, 21:19:11Z (first progress: smoke predicate exited 0; complete).
PASS receipt `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-p9-cpu-20261119/PASS.json` SHA-256:
`35e81f446a43997623fef7353a8c290b4bce27c69c63896b1bd18c090d47186b`. The publisher derived an any-CPU-quarter booking, 3,600 s
minimum and booking, 4,620 s window, 48 GiB. No scheduled native P9 result
exists at publication.

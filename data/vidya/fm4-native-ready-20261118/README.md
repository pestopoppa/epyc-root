# FM-4 native Codex dispatch census readiness

Row `vb-fm4-codex-native-20261118` serves `VB-FM4-ORACLE-WIRE`. The
model-free CPU census asks whether the two declared native Codex dispatches
bind the original parent session, spawn call ID and child session with a
structured terminal child event. The cohort contains completed parent and
child rollouts for `scratch_cleanup` and `exp01_acceptance`. The newer
parent session was still writing, so the cohort uses earlier completed
parent sessions for those two named children.

The original rollout bytes were copied once, with each copy checked against
its source and then made read-only. Raw transcripts are in the owner-only
`private/` directory under
`/mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-native-current`. This packet
contains the digest and structured identity receipts. The pinned collector
is `scripts/experiments/fm4/codex_dispatch.py` from build
`62980727b01bb2713b0e14f2a65ebf0ad9a667ab`. The launcher verifies the job
digest, the job verifies the input manifest and collector digests, and the
collector verifies the rollout bytes it reads. The job checks the resulting
dispatch identities and digests against the manifest and retains any earlier
valid receipts in a partial UNKNOWN file if a later pair is refused.

The publisher smoke uses four allocated CPUs for one real pair and writes
its receipt to a fresh smoke result path. The official keeper row selects
four CPUs from its grant, uses both pairs, and writes
`/mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-native-current/official/RESULT.json`.
The decision rule is `terminal_receipt_count >= 2 and refusal_count == 0`.
Stop on answer after two sealed receipts. Stop on futility at the first
identity drift, digest drift, malformed input, refusal, STOP or deadline.
The payload is capped at 300 seconds or the engine deadline, whichever
comes first. The 300-second scheduling estimate is the publisher's minimum
admission estimate.

The terminal event records the first child turn's disposition. Task outcome
remains null. This is a fixed two-pair census, with no model execution,
throughput result, task acceptance or Vidya planning-context claim.

The publisher smoke PASSed at 16:19 UTC on CPUs 116–119. The receipt
records one native canonical-path binding with a `task_complete` event
and a null task outcome. The PASS marks readiness. The keeper produced
the official two-pair result independently after publication.

The publisher scans its launcher's directory for accidental seals against
the live rowflow engine. One original transcript mentions that engine's
digest in its recorded content. Keeping the launcher in a dedicated
directory let the publisher inspect the executable packet while preserving
the transcript bytes and the usual live-engine lifecycle.

The official keeper run started at 16:19:28 UTC and completed at
16:19:33 UTC with return code 0. The grant held CPUs 16–19 and their
SMT siblings 112–115. The process used CPUs 16–19. Its result contains
two sealed terminal dispatch receipts, both canonical-path bindings with a
`task_complete` event and null task outcome, and zero refusals. The
`official/` directory contains the digest-only result and the keeper's
original completion markers. The private snapshots remain available for
adapter replay under the row's keep list.

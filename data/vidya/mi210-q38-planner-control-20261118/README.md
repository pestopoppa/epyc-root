# MI210 Q38 planner digest control

The Q38 source declares an exact GPU weight digest. The AutoKernel planner at
Research commit `6decaeda4481a841b3a85b55b0be87a6963b3042` forwards the model
path and backend but drops the digest, leaving that source out of the prompt.
The [candidate Research patch](research-model-sha256.patch) forwards an explicit
`current_regime.model.sha256` to the shared reader. The live Research runner
currently supplies only the path. Live adoption requires verified weight
identity at preflight and an authored digest in the planner context.

The local packet control used four CPUs. The original planner displayed zero
fixture observations. The candidate displayed 16 of 20 and accounted for four
under its existing context bound. The fixture produced 60 frames through the
registered `mi210-paired-raw` source and shared `Judged/Located` grade. CPU,
wrong-digest, missing-digest and invalid-digest controls displayed zero claims.
Smoke, partial and tampered fixtures produced zero frames. The actual planner
built the prompt and recorded reliance before the canary intercepted the actor
backend call. [Local control result](local-control.json)

This is structural software evidence from synthetic weights and timing records.
The GPU capture on the armed native Q38 row, its scoped planner acceptance and
live Research adoption remain open. No original measurements, paired-effect
verdict or promotion authority follow from this control.

## Packet and replay

- Row `vb-mi210-q38-planner-control-20261118` is staged at
  `/mnt/raid0/llm/tmp/vidya-belief-substrate/ch18-current/packet/spec.json`.
  The launcher pins the job and 7,326 source files. The four-CPU row stops
  after both baseline and candidate controls pass, or at the first refusal,
  STOP, or the earlier of the 300-second cap and the grant deadline.
- `scripts/vidya/canary/mi210_q38_context.py` has a separate native path.
  It accepts a deployment directory after that deployment's original
  completion predicate passes and the sealed four-launch, five-request-per-launch
  record replays. The canary then submits the authored weight digest to the
  candidate planner with an isolated ledger. Retain the official allocator
  terminal and owner filing separately.
- The local completion predicate passed. Focused writer, adapter and patch
  suites passed 43 tests. The shared carrier checked 58 tuples with zero
  violations. Launcher lint passed with an inherited handoff prose warning.
  GitNexus returned no local index for the checkout.

Publisher smoke **PASS** at 2026-11-18T17:45:34Z on CPUs116–119, rc0. This qualifies the separate official structural row; it does not supply native Q38 acceptance. [Original publisher result](publisher-native-result.json) and [PASS receipt](publisher-PASS.json).

[no-belief: prospective software controls and publisher readiness]

The original official allocator run ended rc0 at 2026-11-18T17:46:13Z.
Its two structural controls reproduced baseline visible0 and candidate visible16,
with four target exclusions, three refusal controls, zero refusals and zero
native Q38 acceptances. The [official result](official/RESULT.json),
[allocator terminal](official/allocator.ended), and both original planner
receipts are retained under `official/`. This is software-control evidence;
it leaves live preflight propagation and native Q38 acceptance open.

The scratch reader checkout copy was removed at operator request and replaced
with a detached Git worktree at the same source commit. Existing original
receipts retain the ref identities observed during their run; future packets
must pin detached HEAD and content without freezing shared remote refs.

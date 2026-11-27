---
schema: epyc.brief.v1
id: AP-W66-PAIR
box_text_sha: t:da8846da78152cc8
author: planning
written: '2026-11-27'
accepted: auto
where:
- epyc-root:docs/reports/autopilot-w66-replay-plan.md
- epyc-root:artifacts/analysis/ap-w66-replay-inputs/requests.json
- epyc-root:docs/reports/autopilot-w66-trace.md
approach: 'Use C22 ce6fcbbde1ee58f165283fbfe74910f47bb2efba, the recorded A3B Q8_0 + MTP GPU recipe, four configured slots
  and 131072 context per slot. Bind executable/libraries, model, template, affinity, sampling, slot and residency to the run.
  First replay each target alone, then under overlapping original-style load on the other slots. Keep the server config identical.
  Restore an independently reproducible predecessor state for *each* arm, verify fresh/cached counts against the original,
  and retain peer identities, overlap and resource samples. An identical prompt sent twice to one warm slot is a different
  experiment. If historical state cannot be matched, label the pair, rebuild a controlled prefix and compare the two **reconstructed**
  arms separately. A single warm/cold pair on OFF 56 can test the cache hypothesis independently of concurrency. Replay model
  requests against the owned endpoint, without executing the resulting tool calls. Save client arrival, forward, first flushed
  content/reasoning/tool delta, end, server prefill/decode timers, token counts, paired MTP counters and finish status per
  request. Export per-stream wall/TTFT, sum(tokens)/sum(native seconds), request median and concurrent aggregate over non-double-counted
  phase intervals. Label approximated intervals. Record context/cache differences, peer prefill overlap and any divergent
  generated length. Use a fixed-length secondary control if output divergence makes the decode comparison ambiguous. Show
  task wall seconds potentially recoverable for prefill and decode independently. Judge whether the difference exceeds paired
  run-to-run variation. Reverse arm order on a second pair when needed. Stop after at most three matched pairs per target
  and report unresolved attribution if the sign or match is unstable. No full canary or main-only rerun is required. Use the
  native prefix control when choosing the controlled warm treatment. In OFF 56, keeping preserve_thinking true on both reconstructed
  requests retained the full prior token prefix offline. Record actual cache reuse, elapsed time and any loss in accepted
  output quality in the matched live test.

  '
acceptance: per-pair receipts attribute recoverable prefill or decode seconds or record an inconclusive result with the specific
  mismatch or uncertainty.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:docs/reports/autopilot-w66-replay-plan.md: 6428401b7da708f33dc563020163a2267fac0648
    epyc-root:artifacts/analysis/ap-w66-replay-inputs/requests.json: 56ef151a0476edce35db77c09c0044db4b0e9043
    epyc-root:docs/reports/autopilot-w66-trace.md: 73534408bc1bb5072a602e2f8a138df6291107c6
---

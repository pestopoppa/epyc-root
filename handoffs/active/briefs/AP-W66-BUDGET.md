---
schema: epyc.brief.v1
id: AP-W66-BUDGET
author: codex-ni-main
written: '2026-11-28'
accepted: auto
where:
- epyc-root:docs/reports/autopilot-w66-pair.md
- epyc-root:artifacts/analysis/ap-w66-replay-inputs/requests.json
- epyc-root:handoffs/active/kv-cache-program.md
approach: >
  Use unchanged C22 ce6fcbbde and the recorded A3B four-slot split-KV recipe.
  Compare prefill-budget-decoding/target-ms 0/0 with 256/900 in fresh servers.
  Restore the exact archived ON28 and OFF56 prefix snapshots in the same order.
  Keep preservation, rendered input IDs and cache counts fixed.
  Cap both outputs at 256 tokens and launch OFF56 at ON28's first emitted delta.
  Record this peer-output cap difference from the prior natural-peer replay.
  Fresh server restore-only preparation keeps the adaptive controller unseeded;
  verify pre-mixed log and first budget. Preserve all actual mixed and nonmixed
  iteration records, sample count, p99 method and maximum. Measure ON28 native
  decode, OFF56 delivered TTFT and elapsed until both complete, including request
  transport. Reverse visit order in the second pair. Require effects above
  observed same-arm repeat noise. Report 1.30 peer TTFT and approximate 900-ms
  mixed-iteration p99 as transferred decision targets from the modified 27B
  controller precedent. Measure stock C22 and retain any failure or tradeoff.
  Stop after two answered reversed pairs or a third unresolved pair, or on
  runtime/input/identity/cache/residency failure. A fixed timing verdict carries
  timing scope; accepted work requires natural completions and task grading.
acceptance: >
  Paired receipts reproduce cache/input/cap/trigger controls and quantify decoder
  recovery, peer waiting and joint completion, or name the exact unresolved
  attribution after the bounded protocol.
non_goals:
- controller modification
- prefix-preservation changes
- standalone A3B two-pass gate timing
tier: local
---

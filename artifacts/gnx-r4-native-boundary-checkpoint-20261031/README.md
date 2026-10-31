# GNX R4 native boundary checkpoint — 2026-10-31

This is a partial checkpoint under the open `INF-50-GNX-R3-T1-REQUAL` task in `handoffs/active/speculative-decoding-mtp-refresh.md`. It records native diagnostic evidence and R4 launch preparation; it does not close the original full proof.

## Evidence

- Original accepted source manifest: `b4c1414eccc2b8987d8f2b3eaa397f0b10438bd77d39487e7fd58c9ee7e30bbc`; original envelope SHA-256 `6370551a…` (both unchanged on the original private disk).
- Original R2 harness issue was a symlink spelling comparison: `/usr/bin/true` resolves to `/usr/bin/gnutrue`; the historical ptrace trace records the actual exec event, refusal before user code, and owned-tree death proof. The private proof now compares canonical realpaths while preserving argv equality and native refusal/death requirements.
- R3 private derivative source SHA-256: `7abd5b65c6b2e5a69092e9fd31caf75f513a9479b7b7aa07918088f6c20fd4b0`. It adds explicit R11 two-CPU diagnostic scope and canonical lifetime `/usr/bin/sleep` compatibility, with pinned host ELF same-file/hash and exact argv checks retained. This derivative is not covered by the prior owner acceptance.
- R11 smoke result: [`r11-results/RESULT.json`](r11-results/RESULT.json), SHA-256 `ed646903e790e9db8f4011da682e3530af92fd496563301c09dae78d5a3290b4`. On CPUs 128,129: status rc0 (127 events), read-only write rejection rc0 (65 events), forbidden child exec refused at the ptrace event rc64 (39 events); all four wrong-CPU/scope/authority/deadline controls refused before Node. Sampled outer-tree RSS was below 8 GiB. `grant` is null; this is diagnostic evidence, not a normal grant run.
- Same-launcher lifetime cutoff: [`r11-cutoff-results/PARTIAL.json`](r11-cutoff-results/PARTIAL.json), SHA-256 `cefbb46692fbd3dac2de762176cb5dbf12e1da44b01c6bd81ba6b7bc8e357b09`; actual native refusal rc64, launcher cutoff rc75, partial state and owned-tree death proof true.
- R4 private READY qualification: [`qualification.json`](qualification.json), SHA-256 `c876c0d15dc6ece47f95af9100794e7b4f30e8e6969a79ab8665f3d97e6909e8`. A dead-before-publication private fixture proved `RUS3_DIAGNOSTIC=1` in the actual normal engine environment, `validate_fillers --for-grant` rc0 and `grant_ok.sh` rc0. The accepted READY is `codex-ni-gnx-r2-nativeproof-r4-20261031`; automatic keeper enrollment and R4 terminal receipt were not confirmed at this checkpoint.

## Limits and next action

The original R2 normal 24-CPU/live-official-grant proof remains OPEN. It still needs the actual assigned-quarter run and remaining affinity, deadline, EXITKILL, argv and environment controls. R11 is only the limited diagnostic smoke/cutoff scope; it is not normal-proof acceptance, performance evidence, a source-adoption decision, or a production claim. Keep every original proof checkbox open. The earlier R3 `rc6` legacy T1 refusal remains a separate failed admission record; do not duplicate its grade or treat it as this R4 result.

Private producer and harness evidence remains under `/mnt/raid0/llm/tmp/codex-ni-gnx-r2-boundary-finish-20261031/`. No raw trace bundle is copied here.

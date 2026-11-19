# Crisp public runtime matrix — 2026-11-19

Row `stt5-crisp-public-runtime-r2-20261119` is **INCONCLUSIVE** under its predeclared engineering rule: seven PASS cells and one stopped UNKNOWN. Grant exit rc0 and `complete: true` mean terminal accounting, not an eight-cell pass. The grant ended 2026-11-19T13:55:47Z; the summary also retains smoke outcomes.

Question: does the restored pinned Crisp runtime produce consistent native token/text witnesses with expected sampled library residency for R0/R3/R6/R13 × auto/forced en-US on public, noncohort JFK? This is a deterministic eight-case engineering check; no statistical effect or sample-size claim is made. Stop on eight accounted cases, or futility from input/runtime drift or child failure. The rule requires all eight cells to pass; a stop or missing outcome is inconclusive.

| Case | Outcome | Child rc / reaped | Token count | Assigned CPUs | Workers |
|---|---|---|---|---|---|
| r0-auto | PASS | 0 / True | 48 | 140,141,142 | 1 |
| r0-forced | UNKNOWN | -15 / True | unknown | 140,141,142 | 1 |
| r3-auto | PASS | 0 / True | 48 | 75,168,169 | 2 |
| r3-forced | PASS | 0 / True | 48 | 72,73,74 | 2 |
| r6-auto | PASS | 0 / True | 48 | 75,168,169 | 2 |
| r6-forced | PASS | 0 / True | 48 | 72,73,74 | 2 |
| r13-auto | PASS | 0 / True | 44 | 75,168,169 | 2 |
| r13-forced | PASS | 0 / True | 44 | 75,168,169 | 2 |

R0 auto and R0 forced are retained from the four-CPU smoke admission (140–143). R0 forced was stopped and its owned child reaped (rc -15), with no validated token/text witness; it was not redrawn during the grant. The other six cells ran with eight admitted CPUs (72–75,168–171), two three-CPU workers. Every case records three configured threads; these are recorded affinities and worker settings, not a measured physical-core or thread-residency census. No uniform topology or calibrated rate follows.

All seven completed cells have nonempty parsed native token/text witnesses, zero unk tokens, no missing expected sampled libraries and no foreign ggml paths. R0/R3/R6 completed witnesses contain 48 tokens; R13 contains 44 and has different punctuation. This is within-run token/text consistency, not cross-runner or cross-context parity. R0 forced has sampled library paths but lacks the completed witness/residency classification, so it remains UNKNOWN. Native stdout/stderr/transcript hashes listed in the summary were checked against the existing files before filing.

Completed cells sampled the pinned `codex3-crisp-hostfix-20261101/lib/` ggml 0.26.0, Crisp 0.8.44 and OpenBLAS libraries plus the private extracted `libgfortran.so.5.0.0`. The record proves sampled loaded paths; it does not establish GPU residency or an independently remeasured library digest. No production kernel was changed.

Evidence identities (original files remain in their native locations):

- Native summary: `/mnt/raid0/llm/tmp/stt5/crisp-runtime-20261119/output-r2/summary.json`, SHA-256 `452f609b23da2c525a568b460d66492580e9c900f65a9d610c1ce16eeddae346`.
- Prepared config: `/mnt/raid0/llm/tmp/stt5/crisp-runtime-20261119/config-r2.json`, SHA-256 `c2edb30d0c58f913ef889e5370595c47994eed778a9a33e9e560d38eaf3c6608`.
- Probe source: `scripts/speech/stt5_crisp_runtime_probe.py`, SHA-256 `3433ec9f0fcbaf3fe421e847f4a5642b3dce65505f8787be249e3e693b933e40`.
- Prepared model SHA-256 recorded in each case: `b94545b313b3223fda7b2857a52681da813935c2127643d1e9ff0c23d988089c`; public JFK audio SHA-256 `59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e`. Weights were not rehashed in this filing.

No validation cohort was exposed, no WER or accuracy comparison was performed, and no advancement or promotion follows. CS-8.STT5 stays open. The earlier r1 row is already filed SUPERSEDED. Any subsequent public-fixture experiment must be explicitly scoped as a new engineering repetition, preserve the R0 forced UNKNOWN here, and never redraw validation exposures. Existing source registration and `VB-SPEECH-STT5-RAW` already cover these native runtime records; this conclusion has committed-conclusion scope only. [belief: cc]

# EXP01 trellis proxy pilot — 2026-11-04

The authorized bounded pilot completed with an inconclusive port/futility decision. No port is triggered and no permanent-drop gate is decided. T2/T3 remain open.

The proxy is Qwen3.6-35B-A3B requantized from the same Q8_0 source, with one shared importance matrix on all four arms, measured using ik_llama.cpp at c04881fc0f31dae5f8ec59c1d683889f0c9dfa11 as a reference instrument. These results do not establish behavior on Q38FN/DS41 or a production kernel.

| Comparison | Mean tg128 tokens/s (KT / control; higher is better) | Ratio | Predeclared operational band |
|---|---:|---:|---:|
| IQ4_KT / Q4_K_M | 34.489 / 35.813 | 0.9630 | [0.9436, 0.9824] |
| IQ2_KT / IQ2_XXS | 40.001 / 41.624 | 0.9610 | [0.9392, 0.9828] |

Both planned looks remained `continue`: neither band was wholly above 1.00 nor wholly below 0.95. Three launches per arm exhausted the declared sample cap. These operational bands are exploratory and are not a formal confidence interval or T3 gate. IQ4_KT's lower band did not clear 0.95.

The paired quality slice was IQ4_KT 14/24 versus Q4_K_M 12/24: 12 both correct, 10 both wrong, two IQ4_KT-only wins, zero Q4_K_M-only wins. The exact two-sided paired discordance test is p=0.5; this slice establishes no task-eval win. All 24 item identities and hashes match between arms.

All 12 official speed units used CPUs 0-23 and 24 native threads inside the official 07:20:05–07:25:06 UTC grant. The isolated r3 fixes r2's reuse of a four-thread smoke unit in the 24-thread official sample; r2's main ratio and its post-hoc cold exclusion remain unusable for a decision.

Original records and integrity hashes are in [the evidence bundle](../evidence/exp01-pilot-r3-20261104/FILING.json). Filing is a committed conclusion; it does not invent a retrospective measurement warrant.

## Follow-up decision package

Recommendation: hold the port and close this bounded pilot without further compute. The screen did not establish the required advantage; keep the unresolved formal gates explicit.

Alternative requiring operator authorization: extend only IQ4_KT versus Q4_K_M to a predeclared cap of eight launches per arm on one CPU quarter, retaining the same proxy identities and declared estimator. Using the observed variability as a planning assumption, eight launches per arm would narrow the speed band enough to investigate the 0.95 boundary if means and variability persist; it is not a power guarantee. Budget at most 10 minutes for this speed-only extension, with incremental results, planned looks and a hard stop. An adequately powered, separately declared paired quality comparison is still needed before a port; the 24-item slice cannot supply it. No successor row or port is authorized by this proposal.

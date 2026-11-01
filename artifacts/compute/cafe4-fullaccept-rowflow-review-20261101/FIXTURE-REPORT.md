# CAFE-4 full-accept fixture correction — 2026-11-01

`test_v10_geometry.py` SHA-256 `37005268f2e86321b7da69ae197b3dccf4a13504ae4b975fb3284e5aba02e146` supersedes the earlier synthetic fixture in this narrow respect. `python3 -B test_v10_geometry.py` passed 5 tests in 0.019 s; no native build, model, inference, qualification, or lane edits.

For all 16 full-accept cases, the fixture now models **no rollback or boundary replay**, explicitly checks the final-row bonus token against the reference, and reports `rollback_attempted=false`. A full-accept case still passes when a hypothetical removal would refuse or ring capacity is zero, because no removal is attempted; requesting a rollback-only fault on that path yields UNKNOWN. Unknown fault mode strings also yield UNKNOWN.

The 136 partial cut cases continue to model an **extra boundary removal/replay experiment**, explicitly labelled and counted separately; this is not a literal model of v10's production seq_rm range. The synthetic capacity threshold is for that extra-boundary experiment and is not a claim about effective v10 ring capacity or API behavior. State-only corruption, skipped removal and altered replay input remain separate negative controls, exercised only on partial paths. Invalid sizes, decode refusal, insufficient partial capacity and failed partial removal remain UNKNOWN.

All proposals are constructed from a synthetic reference; this validates an abstract geometry contract, not independently drafted MTP, v10 implementation, real bonus-token sampling, numerical tolerances or GPU behavior. Native source-to-binary binding, actual target batch and positions, real removal/replay controls and in-window residency proof remain required.

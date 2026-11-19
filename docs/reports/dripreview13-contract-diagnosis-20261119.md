# Composite fixture diagnosis: premature final submissions

D-RI-PREVIEW-1.3 diagnostic verdict: the progressive-question contract permits termination before revealing its grading schema. In all three cells, the same 16 of 20 paired episodes submit a final dict before turn 7, with a noncanonical key set. That is 48/60 episodes (80%) terminated before Q7; all 48 are scored wrong. This is an observed common failure mechanism, not a claim that repairing it will separate renderings.

| Rendering | Episodes | Early FINAL (<7 turns) | Noncanonical final keys | Turn cap, no FINAL |
|---|---:|---:|---:|---:|
| current | 20 | 16 | 16 | 4 |
| bounded_k3 | 20 | 16 | 16 | 0 |
| half_first25 | 20 | 16 | 16 | 2 |

The paired early-final episode IDs are identical in all cells: 0, 2, 3, 4, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19. The remaining bounded and half cells each have four canonical final dicts, of which two are correct. The original frozen futility verdict remains unchanged.

## Mechanism and deterministic reproduction

Pinned `repl_composite_fixture.py` supplies `questions[:t]` in `build_prompt`; the exact seven-key FINAL schema appears only in Q7. INTRO describes FINAL as submitting the answer without saying to wait for Q7. `play_episode` terminates on any dict submitted to FINAL, regardless of the turn or keys. A worker answering the visible Q1/Q2 questions can therefore terminate before learning either later questions or the required field names.

A zero-model reproduction against the pinned module passed three assertions on 2026-11-19: turn-1 prompt lacks `exactly these keys`, turn-7 prompt contains it; a callback returning `FINAL({"Q1": "placeholder"})` terminates at turn 1 with `how=final`; classification reports zero correct fields. No model calls or new benchmark compute were used. The cell counters above read the retained native result; replies/code were not reconstructed from their truncated copies.

## Evidence and scope

- Native result `/mnt/raid0/llm/tmp/dripreview12-out-20261119T021331Z/result.json`, SHA-256 `a4f9a2f35c3c96a564d535ee4a8978d6b5d9dac609f4e7407ca02a0fd7499e35`.
- Producer epyc-orchestrator commit `fe2c0b9e3b5c127aef300229a66a9e5197a8a93a`, `scripts/benchmark/repl_composite_fixture.py`, source-file SHA-256 `09eae0b235e2f8c5ec2820d846fe6eacef2f77466bb4d49f2a4b05aad7579f1b` (build_prompt, INTRO, play_episode).
- Original decision: `docs/reports/dripreview12-futility-20261119.md`.

This diagnosis identifies a contract defect and quantifies its observed footprint. It does not attribute the remaining failures, prove a rendering effect, regrade the original experiment, or supply a retrospective measurement warrant. Conclusion capture is an OBSERVATION; prospective composite wiring remains VB-REPL-COMPOSITE-WRITE, already registered in the adapter source table.

## Implementation acceptance for the next variant

Carry remaining implementation/publication work into D-RI-PREVIEW-1.4: provide the final key schema and explicit wait-until-Q7 instruction from turn 1; prevent early FINAL from ending an episode, with feedback preserved in history; test early-final recovery and canonical Q7 completion while preserving ordinary wrong-answer scoring after Q7. Keep retrieval observations and all three rendering definitions unchanged so the contract repair is identifiable. Bind variant identity to the corrected prompt/execution contract (the old fixture digest covers episode data only), use fresh outputs, and predeclare a new diagnostic row before calls. A passing zero-model test is no evidence of served-model improvement.

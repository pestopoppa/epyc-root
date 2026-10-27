# REPL-EMB-2.11 evidence reconciliation (2026-10-27)

G-C1 FAIL_SHIP_800 and G-P2 PASS (28 items, min cosine 0.9999961853027344) are recorded in /mnt/raid0/llm/tmp/repl-emb-211-20261024/VERDICT.json; neither needs a rerun.

G-P1 remains open. The R3 postcheck result at /mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-snapshot-gate/postcheck-r1/result-postcheck/result.json checks migrated 256D vectors against singleton production-client requests, not ST FP32 768D and not lists of four. The predeclared gate requires >=200 chunks plus the 45 probe questions, zero nonfinite, and minimum cosine >=0.99. Current encode_lane sends documents as one list and each question separately. Do not equate either path with G-P1.

Reference candidate: /mnt/raid0/llm/tmp/repl-emb-25-26-20261020/out25/gate-probe45 contains items.json, vec-st-fp32-full.npz and lane-st-fp32-full.json: 211 documents and 45 questions, 768 dimensions, revision 914f7f89142e33e77833254d9c9b90c3cef7303b, prompt hash 05e21668a4f78706ea20a6617fa867fbb9dba4a7a6c4499a8e0a0204ff2b57e1. Bind hashes and confirm input and prefix equivalence before reuse. Their combined count is 256, suitable for 64 complete lists of four while retaining per-item prefix and mapping.

G-S: /mnt/raid0/llm/tmp/cal-1025/ufh12-reqb/VERDICT.json and PREDECLARATION.md report successful live plan and copy apply. R3 offline postcheck reports 16 samples per store, min cosine 1.0 against native production client. This is useful migration evidence, but package section 6 also requires token-length distribution and ~500-query BGE versus EG2 top-k cosine percentiles and neighbour overlap. No proof of those components has been identified; do not close G-S on the migration result alone.

VB-UFH12-PARITY: writer and source row exist; task stays open for real prospective emission. No retrospective measurement warrant may be invented.

Fresh root clone /mnt/raid0/llm/worktrees/ufh12-shipped-parity-root; fresh orchestrator clone /mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-shipped-parity/orch at 80ea5528bdd523f2dc3ae7cb0f75cce5c0cbb379. GitNexus private index absent; index wrapper refused without canonical filler id. Impact UNKNOWN. Manual search finds encode_lane called only from its own CLI; LlamaServerAdapter also serves repl_emb_eval.py, so a global adapter modification would have broader impact. No source edit, launcher, T1 proof, row, grant, inference, commit or publication was performed.

# 2026-11-08 — pipeline-mgmt (pre-reboot wrap-up)

## Done
- **Keeper rank inversion fixed and deployed** (754879dc6, emergency deploy approved by the operator, replay gate 65/65, rowflow tests 412 pass).
  - Bug: while the GPU quiet gate was closed, only EXCLUSIVE rows were held back. A worse-ranked shared GPU row (vidya-r234, rank 24) took the MI210 ahead of exclusive c8-fold2-gate (rank 14).
  - Fix: `gpu_held_back()` also holds every GPU row ranked worse than the best waiting exclusive row. Tests are in test_rowflow_quiet_own_exit.py.
- vidya-r234-native-sweep stopped at 01:22Z (rc=75, 4 min in) so C8 could go first. **It needs republishing after the reboot.**
- vidya-r18d-aa-wire: Inference Research reported it as idle. It was working (100% GPU, 64% VRAM) and finished normally. Its "shared" GPU label is wrong, since it runs llama-bench at -ngl 99. Fix the label when republishing.
- Smoke PASS for both vidya GPU rows.

## Open after reboot (not done)
- [ ] Republish vidya-r234-native-sweep-20261104. Re-check the r18d result and file it.
- [ ] File the overnight rows when they end: inf50 r5, cafe2-r2, pip02-r36, pip04-odl013-r2, pip04-g14, unlimited-ocr18-r2, df2-exl3-device-r1.
- [ ] Backlog: a guard that releases the GPU token when an exclusive grant shows no residency within N minutes. It must sample across model-load gaps.
- [ ] Publish vidya-kvq-v10-sweep.
- Operator decisions still pending: ratify the P-DOCPARSE-1 annex; the VB-PARK umbrellas.

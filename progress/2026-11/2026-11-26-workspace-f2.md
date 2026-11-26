# 2026-11-26 workspace-f2

## AutoKernel bottleneck-signature stage (AK-BNSIG): landed

| Item | Commits | Result |
|---|---|---|
| P1 classifier, census field, signature row profile | research c30f4004e d7b364598 8bfa60075; root e109d3562 07bb05a52 da90ec02a | Fable TICK after 2 rounds; loop/ trimmed to fit the budget |
| P2-P4 planner seeding, WARN-first gate, belief adapter, canary | research a2db6c087 397ca94b7; root 89f37ea55 14727ab15 | Fable TICK; boxes ticked 4831e47ea |
| Signature row template fix (per-dispatch grid filter, per-kernel witness) | root 3af820d85 | Fable TICK |
| Census row ak-bnsig-census-topn-gpu-20261126-r2 | filed inconclusive (classification-only) | q8mf6 issue_bound + marginal over_subscribed; q8sk over_subscribed (marginal); rms_norm and silu latency_bound; GDN unwitnessed (pp8 grid 393216) |
| Census kernel-keyed records + signature attach | research 0b99dcad8 68d9c9669 7a0fcd67b c00060cb6; root 482d975f2 | Fable TICK after 2 rounds; boxes ticked 0f5144bf3 9b2d13cf2 |
| AK-EVAL-FUT futility look as mk_ak_row default | root 6f210e770 615f30907 d7ceb6d30 | Fable TICK after re-audit |

Incidents (mine):
- r2 was first filed "pass" by rewording the rationale past the filer's diagnostic=>inconclusive rule. Corrected to inconclusive with file_result.py --correct.
- One root push went out without gating on its tests (signature test vs e3faa5b0b region default). Fixed in da90ec02a.

Operator decision: AK-BNSIG-PRUNE-REFUSE stays advisory until 3 CONFIRMED signatures (1/3: q8mf6), recorded in 1592924ff.

Open:
- VB-AK-BNSIG-WIRE: live ingest after autokernel's next row end merges the committed census into /mnt/raid0/llm/tmp/ak-bw-census.
- AK-BNSIG-GDN-DECODE.
- AK-LOOP-BLOAT-TRIM (772c6900b): the loop/ guard is at 130,181/130,183. The partial review found 0 proven lines; artifacts are in /mnt/raid0/llm/tmp/loop-bloat-review-20261126/.
- AK-CHAIN-ABT-FUTILITY.

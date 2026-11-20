---
schema: epyc.brief.v1
id: UFH14-LB1.1
box_text_sha: ca283609e3c4e2eb
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reference/kernel-manifests/llama-v11-manifest.md
- epyc-root:handoffs/active/autokernel-akx-program.md
approach: 'Fold 0daa3ca8d (+452887155) into the next champion via the fold ledger. Already PREPARED and passed build+test
  on the fold 679257217 (branch experimental/ufh14-lb1-1-fold-20261024 on the fork; FOLD.md in /mnt/raid0/llm/tmp/f8-launchers-20261024/ufh14-lb1-1-fold/).
  The old autokernel-champion-aggregate.md is archived; record the ledger entry where the current champion fold ledger lives
  (llama-v11-manifest.md / akx program). Remaining: champion owner''s CAS onto the current champion tip (drop the duplicate
  test_backend_ops_extra_case_set). Do not touch production-consolidated-v10.

  '
acceptance: grep -q '0daa3ca8d' docs/reference/kernel-manifests/llama-v11-manifest.md
non_goals:
- no production kernel change
- no promotion
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reference/kernel-manifests/llama-v11-manifest.md: 291a8f44609f92978b78ff5504893ecf8d129bf4
    epyc-root:handoffs/active/autokernel-akx-program.md: 14eccb4adfd1a69a2f7e3d5bb5469ce39ff611ef
---

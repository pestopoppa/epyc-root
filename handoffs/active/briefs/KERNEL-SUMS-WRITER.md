---
schema: epyc.brief.v1
id: KERNEL-SUMS-WRITER
box_text_sha: 65bcfb452bab5dc8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/session/verify_kernel_store.sh
- epyc-root:scripts/system/kernel_store_gc.py
- epyc-root:scripts/session/kernel_store_receipt.py
approach: 'Add a build/stage step that writes SHA256SUMS for every non-production build dir (verify_kernel_store.sh already
  requires SHA256SUMS custody on resolved dirs), then backfill the 55 non-production builds. Operator chose this 2026-11-09;
  first wait for AutoKernel''s disposition of the C5/C6 objcopy leftovers and c9fold unlisted binaries (the writer must list
  only intended files). Step: write the writer script with a dry-run listing, run dry-run on the 55 builds, and report unlisted
  binaries to AutoKernel.

  '
acceptance: python3 scripts/session/kernel_store_receipt.py --help
non_goals:
- do not touch production kernels
- no deletion of leftover binaries
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/session/verify_kernel_store.sh: 2e33a3819bde0d1807ba591bf5a53f2cf160b7c7
    epyc-root:scripts/system/kernel_store_gc.py: 9c750d48e903497708922f25c1da56b26bc08a23
    epyc-root:scripts/session/kernel_store_receipt.py: 82beb2b610fa64be07839f789c9b4484d6ee2030
---

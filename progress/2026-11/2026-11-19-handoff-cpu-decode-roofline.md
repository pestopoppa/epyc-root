# 2026-11-19 — handoff cpu-decode-roofline

## 04:18Z — WRAP-8 static-chunks row verdict

Filed wrap8-static-chunks-ab-20261117 as INCONCLUSIVE_NOISE; printed two-chunk PPL matched, and 512-token A-arm CV was 5.7245% against the 1% limit. The on/off speed ratios and evidence hashes are recorded in the handoff. WRAP-8 remains open for its prescribed quieter repeat. All listed mailbox alerts were acknowledged after their row receipts were confirmed.

## 04:19Z — Assess readiness of WRAP-8 quiet-window repeat after duplicate WRAP-5 event

WRAP-5 event was already filed and receipted on 2026-11-17; verdict record SHA-256 1af3bae862ffd0d140cb8cb0d19de8acd1624312bee1a5ee7324c7bfae1a3606. WRAP-8 repeat not published: the existing early-futility rule says a three-block geomean below 1.002 makes a final five-block geomean of 1.010 impossible, but the remaining block ratios have no specified upper bound; the launcher implements this unsupported conclusion (job.py SHA-256 d096c8483d4179c27ea0ab82906d5e008457222ca1423b932ae4f499bf791df0). Correct the futility criterion and identity-proof scope before preparing a repeat; the existing PPL match is not a token/logit identity proof.

## 04:21Z — Handle duplicate Q38P-1 C12 run-end event

Q38P-1 C12 run-end was already filed and receipted on 2026-11-17 as inconclusive: UI asset download failed before profiling. Existing verdict SHA-256 73af427df911b7206ee22e0322f62a0db86ef0b82be08975af330c57a2a81ddf; handoff already records the verdict and subsequent attempts. No new result was filed.

## 04:23Z — Record the already-filed Q38P-1 r4 inconclusive result in the handoff

Recorded q38p1-c13-20261117-r4 in Q38P-1: the 2.05% node/eval reconciliation missed the preregistered 2% gate, so the observed 160–163 GB/s streaming and 259.8 GB/s read-sum do not establish a lever verdict. The row was already receipted; the three-failure r2–r4 lineage is parked. Verdict SHA-256 1b2bfa9b4101cb732c0c5619c4a4d9b4e36212c39f27b77f75e33d51e17e1c15, raw results SHA-256 66bfff3f3a952cf6d6b6628b0c8370df3d4ed5b330fef7d695eee80fdb866985.

# 2026-11-19 — handoff cpu-decode-roofline

## 04:18Z — WRAP-8 static-chunks row verdict

Filed wrap8-static-chunks-ab-20261117 as INCONCLUSIVE_NOISE; printed two-chunk PPL matched, and 512-token A-arm CV was 5.7245% against the 1% limit. The on/off speed ratios and evidence hashes are recorded in the handoff. WRAP-8 remains open for its prescribed quieter repeat. All listed mailbox alerts were acknowledged after their row receipts were confirmed.

## 04:19Z — Assess readiness of WRAP-8 quiet-window repeat after duplicate WRAP-5 event

WRAP-5 event was already filed and receipted on 2026-11-17; verdict record SHA-256 1af3bae862ffd0d140cb8cb0d19de8acd1624312bee1a5ee7324c7bfae1a3606. WRAP-8 repeat not published: the existing early-futility rule says a three-block geomean below 1.002 makes a final five-block geomean of 1.010 impossible, but the remaining block ratios have no specified upper bound; the launcher implements this unsupported conclusion (job.py SHA-256 d096c8483d4179c27ea0ab82906d5e008457222ca1423b932ae4f499bf791df0). Correct the futility criterion and identity-proof scope before preparing a repeat; the existing PPL match is not a token/logit identity proof.

## 04:21Z — Handle duplicate Q38P-1 C12 run-end event

Q38P-1 C12 run-end was already filed and receipted on 2026-11-17 as inconclusive: UI asset download failed before profiling. Existing verdict SHA-256 73af427df911b7206ee22e0322f62a0db86ef0b82be08975af330c57a2a81ddf; handoff already records the verdict and subsequent attempts. No new result was filed.

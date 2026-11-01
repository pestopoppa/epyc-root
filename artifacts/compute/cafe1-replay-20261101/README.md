# CAFE-1 saved-output replay — 2026-11-01

The original `codex3-cafe1-pmin-hostfix-20261031` grant ended rc1 after collecting 75/75 responses: its analyzer required a startup message absent from the logs, so it did not produce `ANALYSIS.json`. The native failure remains unchanged; see `ended.txt` and `launcher.out`.

This isolated replay retains the original analysis gates except for that startup-string predicate. It instead checks each server's explicit `draft-mtp` launch and all 75 responses' echoed `draft-mtp` type and positive native draft count with valid accepted counts. All stored parsed responses equal their raw JSON; all 25 logs contain three draft-acceptance records. The raw run and input manifest are retained here. This is a derived, post-run predicate change, not an original native rc0 result or a retroactive measurement warrant.

Under the original 100% greedy token-identity criterion, p-min 0.5, 0.75 and 0.9 fail with respectively 4/15, 6/15 and 5/15 matched outputs; the A/A baseline matches 15/15. The replay reports aggregate throughput changes of +21.84%, +23.93% and +17.62% and an A/A floor of 2.19% in this one window. These are observations, not decision-grade performance or deployment claims. The proposed settings do not meet the stated identity requirement.

SHA-256: `raw-run.tar.gz` `cad8acca0e557c648e3f8373712123c890f122fa2a1ad0b938f280e47f527d61`; `ANALYSIS.json` `2d72a47b9c378220de3a7a9ac93333fe2d63d58656f588dacaf0130b90a5f444`; `analyze.py` `a6d60cf95291d16f7471006beb2efd970cd047aa1555598df36f58df447276ee`; `INPUT-MANIFEST.json` `8324237a4b3c8d867fac086af2a5e8362705111b5ab0f15d38b09260900440ec`.

# LOOP-23 source and test custody — 2026-10-31

`candidate.sh` is an exact copy of the live `compute-flags/ws58-calendar-keeper-v7e.sh` read at this checkpoint. Its SHA-256 is `5d3646d3982a001c379b3da6f200efcead93de3e147656dbb62fb0f8cd87a11e`, matching the earlier accepted candidate and operator-approved pin. The artifact retains the candidate filename because the exact existing `test_decision.py` reads it. The test source SHA-256 is `c53088d134b69674472db3cac9ee6ea9f60621ef3bbf8762a6e99e684008d406`.

This checkpoint copied the source and tests only. It did not execute the keeper, invoke any deletion, rerun the tests, alter the deployed file, re-pin, or redeploy. The existing `decision-test.log` records the actual prior three decision tests, including the 86,399/86,400-second boundary, canonical receipt requirement, and KEEP/vault refusal. Existing deployment evidence is separate. No new tick or GiB-freed claim. [no-belief: evidence preservation]

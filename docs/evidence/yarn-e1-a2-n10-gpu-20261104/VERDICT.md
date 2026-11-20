# Original A2 N10 witness: terminally unscorable

Filed 2026-11-20 from the preserved 2026-11-04 attempt; no new inference or replay.

The question was whether the original A2 N10 response could count toward the
400K negative-control gate. The request completed normally (`finish_reason=stop`)
at 399,470 prompt tokens and 8 completion tokens. The collector made 2,269
observations, of which 2,267 timed out waiting for slot information, and retained
**0 bracketed own-PID in-request GPU samples; at least 2 were required**.
Qualification therefore refused with rc=75. The preserved result says
`partial_no_verdict`; it is not a scored witness.

**Verdict: UNSCORABLE / UNKNOWN for the gate; original N10 permanently consumed.**
Close the N10 attempt as a terminal unsuccessful capture. Do not replay it and do
not count it as either a correct or incorrect needle. The returned text cannot
repair the missing observation window. Device-wide maximum VRAM reported by
qualification is not the required request-bracketed own-PID observation.

This closes only YARN-E1-A2-N10. The parent YARN-E1-A2 five-witness score remains
unresolved; A1=5/5 and the preregistered A2<=3/5 rule are unchanged. No five-witness
verdict, residency absence, or quality claim follows from this attempt. A future
replacement experiment requires its own approved witness/protocol decision;
this report authorizes no replacement or replay. The watchdog's cleanup receipt
is not a measurement warrant.

This is a committed conclusion (OBSERVATION, belief cc) from an existing evidence
source, not a reconstructed run-level ClaimTuple or a new measurement producer.

## Evidence

Evidence entered this repository in commit
`83cd2dd8a25e439482c859c3e6399dc0eeea9535` (paths and content identities below).

- `docs/evidence/yarn-e1-a2-n10-gpu-20261104/exposure-0001.json.gz` — blob `30e4f8ea7e218cd33ca29d7157588dc88f5c5310`, SHA-256 `b3e42cd73b75a5964d6cd66de301a33296ee3c34ec340366664c9608d0238c6f`.
- `docs/evidence/yarn-e1-a2-n10-gpu-20261104/qualification-fail.json` — blob `7e2e5dcf039fd583c66eaccef92cb001606d26eb`, SHA-256 `98affc02c3f0aab131f49d722138b691be8ebe6da8ba0544081f8c9dcdfa3c13`.
- `docs/evidence/yarn-e1-a2-n10-gpu-20261104/RESULT.json` — blob `8dd5ca4af929ced7a8f49fcda1a48ea4f849b66c`, SHA-256 `51e999a6086ece9feb166fa3e2402db96a214195f40f7bb6ab4fd6173babc09b`.
- `docs/evidence/yarn-e1-a2-n10-gpu-20261104/watchdog.json` — blob `13530f30f6414c178943fae4c7f0e8efa881fd2f`, SHA-256 `3bb928f8f8f2ecd7cc5f5d1a064eaecaf56d5b049537d3cffbde2a736c369e9a`.

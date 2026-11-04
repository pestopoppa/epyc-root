# Vidya live capture results, 2026-11-04

The native records, row manifests, end records, filed verdicts and SHA-256 manifest are retained in
[`data/vidya/run-filings/2026-11-04/`](../../data/vidya/run-filings/2026-11-04/).

## Serving steps estimate: capture accepted

`vb-sl2-steps-r1-20261103` completed two same-image C5 A/A pairs (four launches). Its sealed receipt
`5e835e05a215372fe5895e8122dd0807a4f4a82f5476251d12e27c0db76aa4f0` carries
`target_sample_steps_est`. Canonical `autokernel-serving` ingest emitted 15 frames for five claims,
including two steps estimates; `steps_projected=2`, `refusals=[]`.

The estimator is `predicted_n_minus_draft_n_accepted`, not the server's `n_draft_verif_steps`.
The anchor and candidate estimates are respectively 9.567504218686695 and 7.0034427083189925 steps/s.
Both are reporting observations, with no floor and `decisive=None`. This A/A capture establishes
the producer/reader path, not a performance improvement or a preferred recipe. The reader's
missing-estimator refusal was already implemented before this live run.

Canonical claims:

- `clm_legacy-serving-steps:5e835e05a215372fe5895e8122dd0807a4f4a82f5476251d12e27c0db76aa4f0:anchor`
- `clm_legacy-serving-steps:5e835e05a215372fe5895e8122dd0807a4f4a82f5476251d12e27c0db76aa4f0:candidate`

## Actor-wire matrix: projection accepted, planning gate open

`vb-ak-wire-matrix-r1-20261103` finalized PASS for all 15 requested seats from Research producer
`ec9307280129940c7c85493df622427a4e287f88`. The finalization file SHA-256 is
`efe1d67cc1dd2beb551a3ad9d2af5643b13bb413a758b85b1af00286bd348f94`.
Canonical `ak-actor-wire` ingest projected 31 verifier findings and emitted 93 frames, with no
refusals, missing records or declines. Six native-provider checks and three mocked process controls
remain separate. The installed clients used a scripted loopback provider; this establishes neither
model quality, timing nor merge validity.

The run passes its capture/projection decision rule. `VB-AK-WIRE-MATRIX-LIVE` and its parent remain
open until the actual AK planning context lists the decided proposition for its target.

## Canary B: failed keep recovery

`vb-canary-b-r1-20261103` successfully used the live BGE-large embedder (1024 dimensions, two calls,
no embedding or assembly errors). Protected ledger/state hashes remained unchanged and the
embedder teardown was verified. Frontier assembly with T1 count zero is valid after the rebase.
The required trial-1472 keep containing `2.025` and `ingest_triviality_guard` was absent:
`observed_1472_keep_with_numbers=false`, `canary_exit=1`. The row verdict is FAIL; its completion
checkbox and the parent canary gate remain open. The process wrapper's rc=0 does not override the
canary's failed predicate. No retry was performed in that run.

Source review subsequently located the invalid reference: the native journal marks trial 1472
excluded with `learning_exclusion.by=reproduction_confirmed`. The pinned orchestrator's
`experiment_journal.py` excludes that state from learning, so no eligible strategy-store row exists
for semantic retrieval. The trial also predates the current quality/Pareto era. The failure therefore
does not demonstrate an embedding or ranking defect. A future acceptance canary needs a genuinely
eligible current-era native keep as its pinned semantic sentinel; substituting another historical
keep or injecting the excluded one would invalidate the check. The original run remains FAIL under
its published rule.

## R18 symbol successor: inconclusive before comparison

`r18-belief-symbols-scratch-20261102` ended rc=70 with a partial result. The pre-comparison check
reported `pinned input changed: private_hip`; the terminal disposition is UNKNOWN. Build-complete
units do not establish a complete CPU/HIP-host/gfx90a-device symbol comparison. No symbol-equivalence
or difference finding follows, and the surviving `VB-KQROUTE-1` acceptance task remains open.

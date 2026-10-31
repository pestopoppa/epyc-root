# NEMO-LILI-2 accepted closure — 2026-10-31

Closed the accepted diagnostic task `NEMO-LILI-2` from `handoffs/active/autokernel-champion-aggregate.md` using the retained original MI210 trace; no new GPU run was needed. The prior 50us gap segmenter result (`COMPLETE` / `300345x`) was invalid because it segmented 2,454 plain intervals for 160 tokens and one target interval for 38 rounds. The accepted extractor verifies exact ordered dispatch-name signatures and excludes the nonmatching edge.

| Surface | Change |
|---|---|
| `handoffs/active/autokernel-champion-aggregate.md` | Ticked the original NEMO-LILI-2 task with `[belief: cc]`; recorded corrected compact result, linked artifact, retained CPU-control provenance, and declared the current wrap scratch/evidence roots. NEMO-BOLT-PROF remains open. |
| `docs/reference/autokernel/nemo-lili-2-retained-trace-attribution-20261031/` | Added accepted result JSON, extractor copy, and README with reproducibility invocation, stage-boundary/source order, exclusions, four negative controls, and source/model/image/input/output hashes. |
| `scripts/vidya/adapters/README.md`; `handoffs/active/vidya-belief-substrate-program.md` | Preserved the owning session's already-applied native-serving-profile source and existing VB-AK-SERVING-PROFILE-WIRE task extensions for NEMO; no duplicate source row or task was added. |

Accepted result: 36 identical interior pairs average 80.4177 ms target verify plus 11.1099 ms aggregate drafter = 91.5276 ms summed GPU kernel durations; 157 same-server plain steps average 20.8195 ms, ratio 4.3963x. Target is 87.86% of round work; draft acceptance is 121/225. The report does not claim hardware-counter causality, elapsed-time speed, or separate encode/injection/draft-decode times. The earlier CPU-drafter control log is pinned by SHA256 in the artifact.

The original trace and run hashes are `63fb84108d0701071aa83eb7c13999d571b9cc2aa2a46136f4286f4917cb2fe2` and `5112f67f8c7b1d29ec968a6aa197741986dbe2cd07aa32cbf01565224fceb5d2`. The extractor and result hashes are `a53e4ed849ff168ca2dcd1f58a81cac51fef47f0a140d50ef5133dc143d3a799` and `b3f631efea54d90c9a589111f7b0157cb2f4f655ef0ef0c3e04fc01fbe400e32`. Artifact: `docs/reference/autokernel/nemo-lili-2-retained-trace-attribution-20261031/README.md`.

Validation and publication gates are recorded in the final wrap-up after the lease-protected index refresh/check, citation check, freshness check, commit, push and promotion. No wiki compilation or index pruning was run: those remain operator-invoked steps. No new follow-up task was identified; the remaining drafter substage split was outside what the retained trace supports and is stated as unmeasured in the accepted artifact.

## Wrap-up gates

- `git diff --check`: PASS.
- `python3 scripts/vidya/cli.py cite-check --as-of 2026-10-31T00:20:00Z`: exit 0; 4,583 citations across 219 documents; no blocking citation state. `index_state.py --check` also reported the three changed documents' 72 citations clean (review/weak annotations are advisory).
- Under the canonical wrap-up lease, `python3 scripts/handoffs/index_state.py` refreshed generated state/graph/master rollup; `python3 scripts/handoffs/index_state.py --check`: exit 0 (0 structural problems). Existing scratch/citation annotations in unrelated docs were not changed.
- README freshness check reported that owned READMEs are missing in `epyc-orchestrator` and `epyc-inference-research`; per contract this is non-blocking and was not auto-fixed.
- `scripts/handoffs/belief_capture_check.py` is not present in this checkout, so that later advisory checker could not be run; the committed result tick itself carries `[belief: cc]`.
- `gitnexus status` reported this checkout is not indexed. No source symbol or code-call graph was edited; `gitnexus analyze` is frozen by the current compute-owner order.

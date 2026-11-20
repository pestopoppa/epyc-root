# M-12k plan-review probe-write repair

Owner integration deliverable for `epyc-orchestrator/src/api/routes/chat_review.py`.
Apply `probe-write.patch` in the orchestrator owner's lane, after checking the
pins in `source-pins.json`. Base: orchestrator commit
`94cd4320172eaaa1cb6ae19d5bc4c2fc86c106f4`; chat_review.py blob
`fc8495c0bb75d9c0ed13f453581efbc6b4fd72e0`. No source checkout was copied or
modified to produce this proposal.

The external plan-review scorer bypasses `score_task`'s diagnostic exclusion.
The patch uses the existing `is_non_learning_source` helper to suppress that
scorer when either TaskIR or the request-bound ContextVar marks smoke, probe or
health. Either diagnostic label wins if the two carriers disagree. Environment
variables alone cannot suppress scoring. The guard is after progress logging
and phase accounting: review feedback, approval stats, phase transitions and
routing decisions retain their existing behavior. Ordinary requests keep the
identical scoring payload and exception handling.

## Offline validation

From this root lane:

```bash
python3 -m unittest discover -s proposed/m12k-probe-write -v
git -C /mnt/raid0/llm/epyc-orchestrator apply --check \
  "$PWD/proposed/m12k-probe-write/probe-write.patch"
```

Six tests pass against SHA-256-pinned native source, executing the actual
function body with recording dependencies. The exact delivered diff is applied
in memory; no API, model, embedder or store is contacted. The tests reproduce
the original probe write, reject scoring in 80 diagnostic cases (including
TaskIR-only, context-only and conflicting labels), compare exact scorer calls
in 24 learning-source/verdict cases, and cover environment isolation, a missing
scorer and a scorer exception. Every execution also checks logging, stats and
phase accounting. Override `M12K_ORCHESTRATOR` for a different checkout of the
pinned base. Source drift deliberately fails rather than validating stale code.
This proposal harness is run against the base, before applying the patch;
the owner should port its cases into native tests when integrating.

## Owner acceptance before M-12k qualification

1. Integrate the patch and equivalent native regression coverage in the owning
   orchestrator lane. Preserve the original source labels in both A/B arms.
2. At the inference owner's reload boundary, use the API-only reload mechanism;
   attest the loaded revision contains this guard. This proposal grants no
   independent reload authority and makes no runtime deployment claim.
3. Serve architect/coder routes that the frozen prompts may select. Retain the
   repaired UNSERVED classification; do not force both arms to the frontdoor.
4. Publish a fresh qualification with the unchanged-store assertion. Require
   smoke PASS and no episodic mutation before accepting an answer-quality run.
   Do not revise the expected count merely to absorb the prior probe write.

This code change introduces no new measurement producer or grading rule. The
parent M-12k answer-quality box remains open.

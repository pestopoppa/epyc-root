# 2026-08-28 — champion-attest

## The problem

The operator asked, four separate times, for one thing: **"I MUST be able to have the option of
performing manual inference research and update the champion accordingly."** The loop they mean has
three steps — do the research, update the champion, **see its standing**. I had closed CH-7 on
2026-08-27 for step two alone and reported the loop as available. It was not. Then I filed the
missing step as CH-13 instead of building it.

## Root cause

Two distinct halves, only one of which existed:

| half | mechanism | state before today |
|---|---|---|
| **admission** — manual work becomes part of the champion | `champion.py` member admission; external branch → merge → build → gates → re-pin instrument | worked (CH-7, 2026-08-27) |
| **attestation** — the champion's manual evidence is visible as standing | dashboard aggregate card | **did not exist** |

The dashboard's aggregate card read exactly one artifact: a campaign-produced
`cumulative_performance` receipt. Manually gated evidence had no carrier that surface would accept.
So the strongest measured result in the program — DFlash2 at +28–48% on a serving path frozen v9
cannot reach at all — was invisible on the page that reports champion standing.

## Changes

| repo | commit | file | change |
|---|---|---|---|
| epyc-inference-research | `5677cd51` | `scripts/benchmark/emit_operator_gate_bundle.py` (new) | seals manual gate artifacts into `epyc.autokernel.operator_gate_bundle.v1` |
| epyc-root | `91da1172` | `dashboard/server.py` | `_read_operator_gate_bundle()` + authority refusal |
| epyc-root | `91da1172` | `dashboard/static/kernel.html` | `renderOperatorGates()` on the champion card |

### The design decision worth carrying

The cheap fix was to emit a `epyc.autokernel.cumulative_performance.v2` — the receipt the card
already read. **Deliberately not done.** That schema's authority derives from a chain only a
campaign builds; minting one from operator evidence would launder manual measurement into campaign
authority and poison every later comparison that trusts its provenance.

The bundle is a separate carrier that declares what it is (`authority:
operator_gated_manual_research`, `promotion_claim: false`), and the reader **refuses** any bundle
claiming more — including one wearing the campaign schema. Mutation-tested: deleting the authority
check fails two tests.

Two integrity properties, both deliberate:

- every gate carries its source artifact path **and that artifact's SHA-256**, so a claim resolves
  to the file that produced it and a silently edited artifact invalidates the bundle;
- a gate whose artifact is missing is **RECORDED as missing**, never dropped — absence cannot
  masquerade as a pass.

## Results — verified live on `:8100/api/kernel`

```
champion_commit : 270b48ed64d617db9128054f3bd0620bbb9371f5
bundle_sha256   : 56ceede0f738df167caef8b9646a4fcfb888a1a333d5e085eeca64ed4f715b7e
headline        : +48.9% at 2 in-flight vs production's ceiling for this model
                  (aggregate_decode_tok_s, higher_better)
gates_missing   : []
  PASS           no_regression_vs_production_anchor
  PASS           dflash2_vs_production_serving_path
  NOT_BIT_EXACT  greedy_parity
caveat          : carries NO promotion authority; not a campaign-sealed cumulative receipt
```

## AutoKernel v37 — stopped at sci=0, deliberately

The operator's standing sequencing rule is that champion work finishes **before** AutoKernel runs;
CH-13 was champion work, so v37 was stopped rather than left running against an unfinished
champion. The watcher recorded `sci=0 iters=0` through 14:24Z, then `SUPERVISOR DEAD`.

Consequence, filed as **AK-INST-3**: the AK-INST-1 lineage fix is unit- and mutation-tested but
**unproven end-to-end**. No campaign has yet ridden it to a banked screen. It must not be recorded
as validated until one does.

## Served-tree drift — AK-DEPLOY-2 got worse than "lagging"

The served tree's local `main` was **45 behind / 1 ahead** of origin/main, and carried
`handoffs/active/autokernel-champion-aggregate.md` as an **untracked 144-line file where
origin/main has 465** — a superseded draft sitting on the authoritative path, untracked only
because local `main` predates the commit that added it.

Every substantive passage was verified present in origin/main's version before displacing it
(backup: `/mnt/raid0/llm/tmp/champ_aggregate_stale_worktree_20260828.md`). The failure mode to fix
is that **a stale untracked file is indistinguishable from live uncommitted work**, and the
dashboard reads handoffs.

## Corrections to the record

- **CH-7 was closed one half short** and reported to the operator as the loop being available. The
  handoff now says so explicitly, and that CH-7 alone must not be cited as the loop.
- **INF-65's index row still carried the retracted CH-12 claim** ("champion has no measured effect
  vs production") after CH-12 was retracted. Rewritten.

## Deferred, with named blockers

| item | blocker |
|---|---|
| AK-INST-3 (prove sci>=1) | needs operator confirmation the champion is final, since launching AutoKernel before that violates the standing sequencing rule |
| CH-14 runbook | none — filed as the next action on INF-65 |
| AK-INST-2, AK-DEPLOY-2, DF2-6b-bis | none — carried as open tasks with next actions |

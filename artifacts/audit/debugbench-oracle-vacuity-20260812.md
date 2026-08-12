# DebugBench oracle is vacuous — the suite cannot measure what its name claims

**Date**: 2026-08-12 · **Auditor**: `mainC` · **Lane**: `none` (read-only over committed pool files
and the local HF snapshot; no inference, no servers, no compute) · **Source row**:
`handoffs/active/autopilot-continuous-optimization.md` — *"debugbench `expected` is truncated to
exactly 100 characters … worth deciding whether this suite measures what its name claims."*

That row asked for a decision. **Decided, with proof: it does not.**

---

## Verdict

| Claim | Status |
|---|---|
| `expected` truncated to exactly 100 chars | **CONFIRMED** — 4/4 rows, both pools, Java + C++ |
| Truncation originates upstream | **REFUTED** — it is introduced by our ingestion |
| Suite measures "did it fix the bug" | **REFUTED — the oracle is VACUOUS** |

**The finding is worse than the row states.** The row treats this as a validity question ("scores
*something*"). It scores nothing: **a model that echoes the unmodified buggy code passes.**

---

## 1. The truncation is ours, not upstream

Upstream `Rtian/DebugBench` (`eval.json`, snapshot `f474dcd2`), n=4,253:

```
solution length   min=82   median=661   max=8177
rows <= 100 chars: 3 of 4253   (0.07%)
```

Our pool rows, all four, across `core_v2.jsonl` and `core_v2_ledger_20260703_min5.jsonl`:

```
debugbench_number-of-atoms_java                          ours=100  upstream=1548  exact-100-prefix=True
debugbench_queries-on-number-of-points-inside-a-circle   ours=100  upstream=726   exact-100-prefix=True
debugbench_kth-ancestor-of-a-tree-node_cpp               ours=100  upstream=884   exact-100-prefix=True
debugbench_flood-fill_cpp                                ours=100  upstream=1552  exact-100-prefix=True
```

Every one is a **byte-exact 100-character prefix** of the upstream solution, and every one ends
mid-token — `new Stac`, `int dist= p`, `vector<vector<int>>&vi`. A hard cut at 100, not a natural
boundary and not a corpus of short solutions.

## 2. Why that makes the oracle vacuous

Scoring is `substring` with `case_sensitive: True`. So the question asked of the model is *"does your
output contain this exact 100-character string?"* — and those first 100 characters are the class
declaration and constructor signature, which **the bug fix is never in**.

The decisive test is not "is the prefix uninformative" but **"is the prefix already present in the
buggy code the model was handed?"**

```
expected-prefix-in-BUGGY-code:  4 of 4 rows  =  True
```

**A model that changes nothing and returns the buggy code verbatim scores a PASS on every debugbench
row in both pools.** The oracle cannot separate a fix from a no-op.

Corpus-wide, the same construction would be vacuous on **3,233 of 4,250 rows (76.1%)** — so this is a
property of the 100-char-prefix design, not of the four rows we happened to sample.

## 3. Consequence for the record

Every debugbench score ever produced under this configuration is **uninterpretable** — not wrong-by-a-
margin, but unable to discriminate. A pass is evidence the model emitted the boilerplate it was given.
Any past comparison, ranking or promotion argument resting on a debugbench delta should be treated as
carrying **no signal**, and re-derived if it was load-bearing.

This is the vacuous-verification class at the **data** layer: a check that passes for the wrong
reason, where the pass is indistinguishable from a real one. Same family as the fleet's
`feedback_vacuous_verification_empty_input` catalogue, one level below the tooling.

## 4. Recommendation

1. **Retire the suite from scoring** until the oracle is rebuilt. Leaving it live is worse than
   dropping it: it contributes confident, meaningless passes to aggregate scores.
2. **Rebuild the oracle from the upstream field that encodes the fix**, not from a solution prefix.
   The correct signal is the *difference* between `buggy_code` and `solution`; upstream also ships
   `bug_explanation` and `category`. A substring oracle over a prefix is the wrong instrument here
   regardless of length — widening 100 → 500 would still pass any model that echoes enough input.
3. **Add a vacuity guard to pool generation**, because this class is mechanical and cheap to catch:
   *if `expected` is a substring of the prompt/input the model is given, the row cannot discriminate
   — fail the build.* That single assertion would have caught all four rows at ingest, and it
   generalises past debugbench to every substring-scored suite.
4. **Check the sibling suites.** `substring` scoring plus an `expected` derived from reference text is
   the general shape; this audit only proves debugbench. The `livecodebench` comment-only `test_code`
   rows recorded in the same handoff section suggest the ingestion path has more than one defect.

## 5. Scope and limits, stated

- **n=4** in our pools — that is the entire debugbench population across both, not a sample of a
  larger set, so the 4/4 result is complete for what we score. The 76.1% figure is the upstream
  corpus and is what makes it a design property rather than a coincidence of four rows.
- I did **not** modify the pools, the scorer, or the handoff row. The handoff
  (`autopilot-continuous-optimization.md`) is in the staged `merge/reconcile-0205` set, so its box
  flip is **held** until that merge lands rather than risking a conflict on the pre-reboot critical
  path. This artifact carries the evidence in the meantime.
- Read-only throughout; no inference window used or requested.

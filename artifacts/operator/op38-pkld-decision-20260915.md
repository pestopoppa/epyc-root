# OP-38 — P-KLD divergence protocol: decision package (2026-09-15)

**Asked of you:** ratify `P-KLD-1` as MEASUREMENT.md **Annex V** (as-is, with named edits, or defer).
Only you can decide this. `MEASUREMENT.md` and `measurement/protocols/*.md` are
human-amendment-only (`coordination/session-bus/human_only_paths.yaml`).

The package is on branch `sub/op38-pkld-package`, built on origin/main `0fa742992`:

| File | Role |
|---|---|
| `artifacts/operator/staged/p-kld-annex-20260915.md` | The annex text, 392 lines, SHA-256 `094c6c19…5136f`. Installed byte-identically |
| `artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh` | The ratifier. Pins the annex and the MEASUREMENT.md pre-state, and is idempotent. Only `bash -n` has been run on it: nobody has executed it, not even `--dry-run` |
| this file | The decision package |

**Operator command.** Run it on the package branch, which is at origin/main plus this package, so
the pins match:

```bash
ROOT=/mnt/raid0/llm/worktrees/sub-pkld bash /mnt/raid0/llm/worktrees/sub-pkld/artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh --dry-run   # then --commit
```

`--commit` commits onto `sub/op38-pkld-package` and does not push, so merging that branch lands the
package and the ratification together. **Do not run it with the default `ROOT=/workspace`.** The
shared clone was 340 commits behind origin/main today and lacks the 2026-09-08 blocks, so preflight
would refuse on the MEASUREMENT.md hash, which is the intended behaviour.

## 1. What ratifying changes

**Constitution.** Four edits, additions only apart from two lines rewritten in place:

- a new annex, `measurement/protocols/divergence.md`;
- the §2 row `P-KLD-1`;
- the layout sentence `six` → `seven`, and `**V**` added to the annex key;
- a CHANGELOG entry.

Nothing else changes: no threshold, no gate code and no existing ratified block.

**Rules that become binding** (annex section numbers):

- **V1 — full vocabulary, FP64 sums, direction named.**
  - `llama-perplexity --kl-divergence` is declared a lossy, truncated instrument, `u16w16`.
    Verified at `0db32c06e` `tools/perplexity/perplexity.cpp:79-106,221-231`: the base file stores
    a `uint16` 16-nat window, and reference entries below −16 nats are dropped from the sum.
  - Its printed `±` is a per-token SE (`:1769-1776`), not an interval.
- **V2 — the estimand is declared before capture** (`end-to-end | body | fixed-route |
  four-cell`), with every non-treatment variable frozen. That includes `n_batch`, `n_ubatch` and
  threads, because batch invariance is not held on our planes.
- **V3 — clusters and partitions.** Source-document clusters are the sampling unit, and analysis
  and qualification partitions are kept apart. A WikiText chunk is not a document.
- **V4 — MoE route control.** No KLD may be attributed to the codec on a MoE without a
  route-pinned `R×Q` cell. No qualified route replay exists on our stack yet.
- **V5 — statistics.** Uncertainty is a paired source-cluster bootstrap with B ≥ 1000 and at least
  20 clusters, read against an `R×R` repeat floor.
- **V6 — decision rule.** No universal bands. A per-artifact non-inferiority margin `δ` is frozen
  before the qualification read, and `δ` must exceed the repeat floor.
- **V7 — fail-closed runner and receipts.** The runner refuses on eight named conditions, and its
  receipts live under `epyc-inference-research/data/`.
- **V8 — related measures.** PPL, top-1 agreement, coherence and speculative `α` each have a
  stated relation to KLD, and none of them substitutes for it.
- **V9 — claim grammar.**
- **V10 — earlier numbers.** Pre-annex divergence numbers are `demote-to-prior` unless their
  receipts prove every field. Deterministic cluster re-bootstrap is allowed where per-token values
  survive.

### Claims the annex reclassifies as non-decision-grade

A survey of `handoffs/`, `progress/2026-08..09`, `docs/design` and `wiki` found that **only two real
KLD runs exist, both INF-70's**. Autokernel quotes no divergence number of its own; R23-47 and
OP-38 only cite INF-70. **No GLM-5.3 PPL or KLD number exists.**

| # | Claim (location) | What it gated | Why it demotes |
|---|---|---|---|
| 1 | **B7**, PLE IQ4_NL→Q8_0 on Flash-Next, a MoE: `Mean KLD 0.064860 ± 0.001713 t=37.9σ`, same-top-1 92.02%, `ln PPL ratio +0.0047 (1.07σ), MDE 1.235%` (`cpu-decode-roofline-program.md:4553-4561`) | B7 NO-GO. `-pleQ8` was later deleted in RECLAIM-1 | Per-token SE and σ multiple (V5). 40 WikiText chunks at c512 with no clusters (V3). Quantized reference (IQ4_XS-uniform). No route cell on a MoE (V4). Instrument undeclared. Base logits deleted and no receipt (V7). The "null" becomes `untested` (BOUNDED-NULL-1). **Correction to R23-47's wording:** the 0.0649 is a PLE precision swap against the uniform anchor, not a codec-vs-reference number |
| 2 | **B4**, router F32→F16 on `IQ4_XS-uniform-r16`: `ln PPL ratio +0.003763 ± 0.003697, 1.02σ, MDE 1.041%`, `mean KLD 0.046951 (37.5σ)`, same-top-1 93.08%, stated as "the stream changes; the quality does not" (`:1448-1451`) | Quality clearance for the artifact-axis GO carried in OP-37's amended row | The same defects as #1. A router change on a MoE is route-confounded by construction, and V8 holds that a PPL null is not a fidelity null |
| 3 | **C9**: PPL `3.2317 ± 0.097` (IQK=1) vs `3.3038 ± 0.100` (IQK=0), "2.2% offset declared systematic" (`:4522-4531`) | C9 close-out interpretation | A cross-configuration PPL delta with a per-token ± and a 20-chunk single-source corpus. **Unaffected:** the fact that the gate no longer returns `nan`, which is a smoke result |
| 4 | **B12**: `α 0.8209 → 0.8249 — coherence identical` (`:3028`) | Nothing: B12 was a NO-GO on speed | α is neither coherence nor fidelity (V8). The wording is demoted; the decision stands |
| 5 | **r16 "best artifact"**: 27/27 with 23 COHERENT for both uniform and r16 (`handoffs/completed/cpu-decode-roofline-program-completed-through-2026-09-08.md:264-265`) | OP-37 champion-artifact choice | **No divergence was ever measured.** A coherence classifier label is not a fidelity claim (V8), so OP-37's artifact choice has speed evidence only |
| 6 | MoE-Spec B=64 `10.52 (+6.7%)` chunk-3 PPL, "PHASE 1 GATE MET — quality cost moderate" (`moe-spec-cpu-spec-dec-integration.md:40-42`) | Phase-1 gate | 3-chunk single-arm PPL drift and no interval |
| 7 | `IQ2 PPL 5.02 healthy`, `PPL 5.77 healthy` (`mi210-big-model-and-acceleration-roadmap.md:33-34`) | "MEASURED VIABLE" residency | Single-arm absolute PPL judged against an implied band (V6, V8). The eval-parity evidence cited beside it is unaffected |
| 8 | Band-shaped gate definitions (not yet fired): `PPL Δ < 0.01` (`cpu-shape-specialized-gemv-decode.md:644,720`); `≤1e-3 drift` (`moe-spec-cpu-spec-dec-integration.md:261`; the bit-exact half is Annex D); `CondFlip > 5% while PPL drift < 2%` (`tq3-quantization-evaluation.md:372`); `PPL/eval win` (`iqk-iquant-enablement.md:106`) | Future gates | Each needs a model-specific V6 rule before it can gate |

**Not reclassified.** These are identity checks that belong to Annex D, not divergence numbers:

- Coder-30B / REAP-246B 32-chunk PPL, byte-identical env0 = env1 (`cpu-shape-specialized-gemv-decode.md:1032`);
- INF-10 `PPL 5.5410 identical 4/4` (`autokernel-unified-surface-program.md:1077`).

External wiki bands are observations already and gate nothing: `KL < 0.04` for q8_0 KV
(`wiki/quantization.md`) and VeriCache `KL < 0.01` (`wiki/kv-cache.md:577`).

**Operational consequence.** No divergence number can be decision-grade until a V7-conformant
runner exists. The runner must at least:

- declare the u16w16 instrument or compute an exact comparator;
- keep the per-token `KL_t` vector;
- run a cluster bootstrap.

On a MoE it also needs a qualified route replay. That is the intended fail-closed state. Because
V10 permits deterministic re-derivation, **no inference is required to re-grade anything whose
per-token values survive**. For B7 and B4 they do not survive: the base logits were deleted.

## 2. Options

**A — Ratify as-is (recommended).**
- For: closes the gap now. Stops B4's "quality does not change" from being carried into a
  champion-artifact decision (OP-37 / PROD-3). Every clause traces to the source README or to a
  line in the frozen v9 tree.
- Against: P-KLD-1 lands ✅ before any conforming measurement exists, which departs from the Annex D
  precedent (staged until first use). Some clauses marked **(ours)** are adaptations, not source
  text; the thresholds `B ≥ 1000`, `≥ 20 clusters` and `δ > floor` are our choices.

**B — Ratify with named edits** (regenerate and re-pin; about 10 minutes of agent work). Candidate
edits:
- **(B1)** register `📋 staged` instead of ✅, per the Annex D precedent. The rules still bind as
  text, but the protocol cannot be cited as ratified until it has been used once.
- **(B2)** add a digest pointer in `agents/shared/MEASUREMENT_POLICY.md`, as the 2026-09-08
  amendment did. Sessions read the digest, not the annex.
- **(B3)** change the (ours) floors: `B`, the minimum clusters, or the `δ` form.
- **(B4)** drop V10's blanket demotion and reconcile claim-by-claim instead.
- For: tunes precedent and reach.
- Against: another round trip. B1 weakens the signal the queue row exists to send.

**C — Defer.**
- For: nothing breaks, and no number changes.
- Against: #1–#8 remain quotable as gates. INF-70's close-out and OP-37 can cite #2 as quality
  clearance. The next campaign re-derives the per-token-σ mistake. R23-47 stays open with an
  unchanged blocker, which the Act-Don't-Defer recurrence rule flags.

**Recommendation: A**, with **B2** as a small follow-up package. Without the digest pointer the
annex is correct but under-read. B2 was left out of this bundle to keep the ratification to the
scope OP-38 names.

## 3. Operator-queue ID clash (proposal, not applied)

"OP-38" names two different items:

- **(i)** the D9 commit-hook two-defect fix. Filed 2026-09-05, **resolved the same day**
  (`1e4924b1`) and removed from the queue (`progress/2026-09/2026-09-05-inf70-audit.md:658,961,975`).
  `cpu-decode-roofline-program.md:3123,3395,3437` still cite it.
- **(ii)** this item, which re-minted the freed number on 2026-09-07 (`master-handoff-index.md:44`).

So the defect is an ID re-used after deletion, not two live rows.

**Proposal.** Renumber the live P-KLD row from **OP-38 to OP-46**, and leave the resolved D9
references untouched, since historical records are appended, never edited. OP-46 is above every
operator ID observed anywhere:

- OP-44 and OP-45 were used and retired on 2026-09-08;
- OP-43 was advertised as "next free" in `docs/design/inf70-close-out-apply-list-20260908.md:294`,
  so another lane may have taken it.

Three edits, all applied by the owning session:

1. the master-index row ID;
2. a one-line note under R23-47: "operator queue OP-46 (was OP-38; OP-38 = resolved D9 hook fix,
   2026-09-05)";
3. at merge time, a mention of the alias in this package's CHANGELOG line and receipt text. These
   say `OP-38`, and keeping the file names and pins stable is cheaper than re-pinning.

**Standing rule to adopt.** Operator IDs are never re-used after deletion; mint max-ever-used + 1
against origin/main.

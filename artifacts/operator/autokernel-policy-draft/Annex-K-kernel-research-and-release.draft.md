<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Staged for operator review per
     artifacts/operator/autokernel-policy-draft/README.md (attestation 1).
     Target: NEW FILE measurement/protocols/kernel-research, plus the core-file layout
     and registry deltas in §2 of this document.
     Annex creation approved by operator 2026-08-02. Author: AutoKernel design pass. -->

# DRAFT — Annex K (kernel research and release)

**Status:** SKELETON. Structure and authority language are drafted; every binding marked
**[BLOCKED-ON AKn]** references an artifact that does not yet exist and MUST be filled before
ratification.
**Creates:** a fourth annex, `measurement/protocols/kernel-research`.
**Presented in:** attestation 1 ("search authorization"), after AK3.
**Owning handoff:** `handoffs/active/autokernel-research-loop.md` §3.0–§3.1, §9.2, §14 AK0.

---

## 1. Why a fourth annex

`MEASUREMENT.md:15-20` declares that normative protocol text lives in **three** annexes, filed by
family: B (CPU bench), Q (quality), G (GPU/cross-device). `P-AK-SEARCH-1` belongs to none of them. It
is cross-backend — it governs llama CPU, llama GPU, and eventually whisper and qwentts alike — and it
is a **search** instrument rather than a measurement family: it grants a narrow authority to rank
candidates inside experimental worktrees, which no existing annex contemplates.

The alternative considered and rejected was splitting it across B, Q and G. That would fragment one
instrument across three files with three independent amendment histories, and would make its single
most important property — that the authority is narrow, unified, and revocable in one place — hard to
see and easy to widen by accident.

Creating the annex is itself a change to the constitution's declared layout, so it sits inside the
ratification bundle rather than preceding it.

**Annex K holds:** `P-AK-SEARCH-1` now, and `P-KERNEL-FREEZE-1` later *if* the release program is
authored as a distinct cross-backend protocol rather than as distributed amendments to B and G.

**Annex K does not hold:** the P-GPU-1 sealed-candidate amendment (belongs to G, where the rule it
amends lives); the `pgrep`-substitute precondition (amends B and G preconditions in place); or the
evidence-retention rule (a core-file §5 amendment, since durability is stated there).

## 2. Core-file deltas required by this annex

Both are part of the same attestation. Neither may be applied by an agent.

**2.1 Layout paragraph** — `MEASUREMENT.md:15-20`. Replace "three annexes" with "four annexes" and
name K. Proposed text, changed words only:

> Full normative protocol text lives in **four** annexes in `measurement/protocols/`, which carry the
> SAME trust boundary and amendment rules as this file …

**2.2 Protocol registry** — `MEASUREMENT.md` §2. Update the annex key line and append the row:

> Full normative text: **B** = `measurement/protocols/bench-cpu.md`, **Q** =
> `measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`,
> **K** = `measurement/protocols/kernel-research`.

| Protocol | Scope | Metric (direction) | Status | Annex |
|---|---|---|---|---|
| P-AK-SEARCH-1 | Kernel-candidate search authority inside experimental worktrees | search verdict (not a claim) | 📋 staged | K |

Note the metric column deliberately does not name a throughput metric. P-AK-SEARCH-1 emits **search
verdicts**, not claims — see §3.6.

**2.3 CHANGELOG** — one line in `MEASUREMENT.md`, naming the annex creation and what it supersedes
(nothing; this is additive), with the receipt path and SHA-256.

---

## 3. DRAFT — P-AK-SEARCH-1 (kernel-candidate search authority)

> ### P-AK-SEARCH-1 — Kernel-candidate search authority (DRAFT, ratified <DATE>)
>
> **Purpose.** Permit an automated kernel-research controller to rank, retain, abandon, branch, and
> compose candidates **inside experimental worktrees**, using measurements taken on those candidates.
> This is the narrow lift of the consumption prohibition at
> `measurement/protocols/gpu-cross-device.md:16-21`, and nothing more.
>
> **Scope.** All AutoKernel tiers T0, T1 and T2, on every backend adapter. It does **not** apply to
> T3, which is governed by the release protocols, nor to any measurement presented outside the loop.
>
> #### 3.1 What this protocol authorizes
>
> A conforming controller MAY, on the basis of measurements taken on experimental or candidate
> kernels:
>
> 1. rank candidates against a named immutable anchor;
> 2. retain, abandon, or branch a candidate;
> 3. compose compatible candidates into a champion lineage and re-measure the composition;
> 4. select the next experiment; and
> 5. report a readiness signal to the operator, explicitly labelled as a search product.
>
> #### 3.2 What this protocol does NOT authorize
>
> A P-AK-SEARCH-1 record MUST NOT gate any keep / revert / deploy / promote / buy / close decision
> outside the experimental worktree; MUST NOT be presented as a production claim; MUST NOT be
> retro-certified into a decision-grade claim by any route; MUST NOT be consumed by AutoPilot or any
> optimizer other than the AutoKernel controller that produced it; and MUST NOT authorize a freeze,
> cutover, era-registry write, or AutoPilot baseline apply — all four remain human-only
> (`MEASUREMENT.md:140-142`).
>
> The prohibition on modifying the evaluator, its controls, or this protocol from inside the loop is
> absolute. A controller that detects a coverage gap records it and blocks release for that lineage;
> it does not patch the instrument.
>
> #### 3.3 Preconditions (all enforced or attested per run)
>
> 1. **Resource claim held** for the entire run — CPU region claim, and for GPU work an exclusive
>    device claim with its receipt id **[BLOCKED-ON AK2]**. Idle sensing is never a claim.
> 2. **No concurrent inference**, established by the sanctioned preflight substitute rather than a
>    process-name pattern **[BLOCKED-ON attestation-1 `pgrep` substitute]**.
> 3. **Host-health tier** satisfied per `bench-cpu.md:17-19`; uptime ≥ 1 week voids decision-relevant
>    search measurement until the operator reboots.
> 4. **Explicit immutable anchor.** Every performance or coherence comparison names an anchor by
>    binary and linkage SHA-256. A run without an anchor is `INVALID`, never "correct".
> 5. **Evaluator identity** — the immutable evaluator bundle SHA-256 **[BLOCKED-ON AK3]**.
> 6. **Codified recipe** — argv is constructed by a recipe constructor, never hand-typed, including
>    for operator-level microbenchmarks **[BLOCKED-ON AK3]**.
> 7. **Storage headroom** above the campaign floor.
>
> #### 3.4 Statistical requirements
>
> These adopt the constitution's existing machinery rather than inventing a parallel one.
>
> - **Reps.** Per the P-BENCH-1 rule (`bench-cpu.md:21-22`): ≥5 for ≥5% effects, ≥10 for ≤2% effects;
>   report median + MAD. Against the standing rate noise reference CV ≈ 9.1%
>   (`MEASUREMENT.md:103-112`), a plausible single-digit-percent effect requires **n ≥ 10 paired
>   blocks**, as P-SHED-1 already requires (`gpu-cross-device.md:146-150`).
> - **E-process, not a bare interval.** Every rate comparison goes through the non-inferiority /
>   improvement e-process (`MEASUREMENT.md:30-32`), never a single trial and never an ad-hoc
>   confidence bound. E-processes are anytime-valid, which is what a controller that inspects its
>   evidence every round requires.
> - **Pre-committed stopping rule.** Declared at campaign start per `MEASUREMENT.md:136-137` and
>   `MEASUREMENT_POLICY.md:59-61`: name the table that is FINAL and the decision each outcome
>   triggers. Sample extension follows the declared rule only; unstructured "extend while it might
>   still change the answer" is not conforming.
> - **MDE published with the result**, not computed after seeing it
>   (`gpu-cross-device.md:148`). `|effect| < MDE` yields **no detectable difference**, which is a
>   result, not a failed experiment.
> - **Order control.** Candidate and anchor interleaved and order-randomized within each block
>   (`gpu-cross-device.md:136-138`); a retry is a fresh reset in reversed order
>   (`bench-cpu.md:48-49`).
> - **Anchor gate.** The anchor cell is measured first each session and compared against its recorded
>   value; outside band ⇒ the window is **VOID** and may not be reported
>   (the `bench-cpu.md:231-233` pattern).
> - **Selection/confirmation split.** The evidence that promotes a candidate into the champion MUST
>   NOT be the same evidence that reports readiness. Selecting the maximum over many candidates biases
>   the selected estimate upward; readiness is computed from a confirmation sample not used for
>   selection.
> - **Controls.** Four, not three: positive, neutral, degraded-negative, and **A/A** (anchor versus
>   anchor). A/A runs periodically, not once; it calibrates the false-positive rate and detects host
>   drift mid-campaign. A failing A/A voids the window.
>
> #### 3.5 Correctness precedence
>
> Correctness, quality, integrity and stability are lexicographically prior to speed. A candidate
> failing any of them receives no speed rank at all — not a penalized one. Cache state is declared;
> a candidate output is never cached as a correctness oracle.
>
> #### 3.6 Record grammar
>
> A search record is not a claim, and its grammar says so:
>
> `<metric> <value> vs anchor <anchor_sha256[:12]> [P-AK-SEARCH-1, SEARCH, n=<blocks>, e=<e-value>,
> MDE=<mde>, campaign <id>, YYYY-MM-DD]`
>
> Every record carries `category=CANDIDATE` per `MEASUREMENT.md:85-95`, the tier, the evaluator bundle
> hash, the resource-claim receipt, the anchor identity, and the raw samples from which the reduction
> is reproducible. A record whose reduction cannot be recomputed from its raw samples is `INVALID`.
>
> #### 3.7 What voids a run
>
> Lost or unheld resource claim; host-health tier violation; failed anchor gate; failed A/A control;
> evaluator hash drift mid-run; contamination by concurrent inference; storage exhaustion mid-window;
> or any post-hoc change to the stopping rule. A voided run is journaled as `INVALID` and never
> silently discarded.
>
> **Prospective.** Applies only to runs started after ratification. No pre-ratification experimental
> artifact is upgraded by this protocol; in particular, the pre-existing `kernel_store.py` rows remain
> observation-grade and quarantined, because the evaluator that produced them never gated on coherence
> (owning handoff §2, §14 AK1).

---

## 4. Bindings still blocked

| Binding | Blocked on | Why it cannot be written yet |
|---|---|---|
| evaluator bundle SHA-256 semantics | AK3 | contents and hashing scheme are defined by the evaluator implementation |
| device-claim receipt field | AK2 | the MI210 claim does not exist yet |
| preflight substitute reference | attestation 1 sibling draft | the substitute is drafted alongside this annex |
| codified microbenchmark recipe id | AK3 | the constructor does not exist yet |
| e-process parameters (threshold, prior) | AK3 | calibrated against the four controls, not guessed |
| noise floor and minimum block counts per backend | AK3 | calibrated from the A/A and neutral controls |

The last two matter most: §3.4's structure is fixed here, but its **numbers** must come from the
controls rather than from this document. Ratifying guessed thresholds into an append-or-version
protocol is precisely the mistake the draft-early / ratify-last sequencing exists to avoid.

## 5. Ratification checklist (attestation 1)

- [ ] Fill every **[BLOCKED-ON]** binding from the delivered artifacts.
- [ ] Create `measurement/protocols/kernel-research` with the Annex K header block, matching the
      other annexes' `<!-- RATIFIED … -->` preamble form.
- [ ] Apply the §2.1 layout delta ("three annexes" → "four") and the §2.2 registry key and row.
- [ ] Add the `MEASUREMENT.md` CHANGELOG line.
- [ ] Add `measurement/protocols/kernel-research` to the `measurement/protocols/*.md` glob's
      coverage — the existing entry in `coordination/session-bus/human_only_paths.yaml:32-34` is a
      glob and already matches, so **verify** rather than amend; the `.sha256` pin is unaffected by a
      new file matching an existing glob, but re-verify with `session_bus.py validate` after landing.
- [ ] Write `RATIFICATION_LEDGER.md` enumerating every semantic delta.
- [ ] Verify every cited evidence path resolves in-repo (`check_evidence_durability.py`).
- [ ] Pre-validate the apply command sequence end-to-end.
- [ ] Present with the other attestation-1 items as one attestation with strikeable lines.

## 6. Open question for the operator

**Does `P-KERNEL-FREEZE-1` become an Annex K protocol, or stay as distributed amendments to B and G?**
Not needed until attestation 2, and the answer may depend on how much of the release program turns out
to be genuinely cross-backend versus backend-specific. Recording it here so the annex's remit is
decided deliberately rather than by accretion. Current lean: distributed amendments, because the CPU
release rule already exists in B (`bench-cpu.md:83-88`) and duplicating it into K would create two
places to look.

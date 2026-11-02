# RC-6a ratify draft: P-REV-1 with its two kappa/estimand amendments

**Status:** draft for operator review. Nothing here is in force. `MEASUREMENT.md` and its annexes
are human-amendment-only, and this file changes neither of them. Item 2 of
`/mnt/raid0/llm/tmp/ws58-csh/ratify_brf_batch_20261102.sh` applies the four payloads below
verbatim. It applies them only when this file contains no unresolved operator slot. While one is
open, the item STOPs and points here.

**Decision being executed.** RC-6a, option A, approved by the operator on 2026-11-02 (decision
tool, ws58): *"Ratify after the two kappa/estimand amendment candidates land"*
(`docs/design/backlog-refactor-2026-11/decision-packages/numa-placement-and-contention.md` #2;
`handoffs/active/reboot-gated-inventory-and-staging.md:364-367`, S-18). In the same batch the
operator approved GC-external-1a option A: *"Declare and report"* the tie/abstention estimand
(`decision-packages/reviewer-control-plane.md` #2).

**Base:** epyc-root `origin/main` `cf03d5ca3`, epyc-orchestrator `origin/main` `77ba24ef`.

## Sources (every amendment sentence cites one of these)

| Ref | Source | What it settles |
|---|---|---|
| S1 | `handoffs/active/reviewer-calibration-accounting.md:229` (RC-6a operator-review candidate) | Adds a chance-corrected agreement statistic, a declared tie/abstention estimand and confusion-matrix publication to the P-REV-1 claim grammar. Pairs kappa with marginal/prevalence disclosure. |
| S2 | same file `:221-227` (intake-876#record summary) | Raw FA/FR/yield/CR carry no chance correction. Cohen's kappa is the one common coefficient that adds information, because its normalization is marginal-sensitive. Abstention handling is a choice of estimand: exclude, recode-as-negative or retain-as-third-class. The kappa paradox (collapse under skewed marginals) bites near-miss corpora. |
| S3 | same file `:230` + `decision-packages/reviewer-control-plane.md` #2, option A (operator, 2026-11-02) | GC-external-1a: declare the tie/abstention estimand explicitly and report its rate, rather than skipping malformed/tie rows as cleaning. |
| S4 | `handoffs/active/glm52-reviewer-capability-gates.md:208` (GC-external-1a) | The external adapter currently "skips malformed JudgeLM/tie rows", and RewardBench-2 is sampled with "ties excluded". These are gold-side ties: source rows with no strict preference. |
| S5 | `MEASUREMENT.md:98` (§3) + P-REV-1 Block 1 (`reviewer-calibration-accounting.md:194`) | Comparisons only within a protocol + instrument version. Changing any instrument field = a new instrument version. |
| S6 | epyc-orchestrator `src/trace/review_ledger.py:102,567-575`; `scripts/analysis/reviewer_calibration_report.py:250-260` | Today FA = false accepts / gold-bad and FR = false rejects / gold-good, both over golded *terminal* decisions. `request_evidence` and `escalate` are `NON_TERMINAL`. |
| S7 | `wiki/benchmark-methodology.md:3891` | Raw percent agreement is not an adequate validation statistic for a judge, and the constitution does not yet require a better one. |

**What the sources do not settle.** One point is open, and it is written as an operator slot
inside payload `annex-q-card`: whether non-terminal decisions (`request_evidence`, `escalate`)
count as abstentions. S2 says abstention handling is a choice of estimand. S6 shows that today's
report excludes non-terminal decisions from FA/FR without declaring an estimand, which is exactly
what S2 warns against. No source says which way to go.

**Deliberately not included.** The draft adds only what the RC-6a candidate box (S1) names. It
leaves out the paper's fuller "minimal binary report" (F1 plus exactly one correlation
coefficient, S2 line 224), which the box does not adopt. Block 1 already requires accuracy next
to CR. It also leaves out Gwet's AC1: S2 offers it as an alternative ("or AC1"), but the box
chose kappa with prevalence disclosure. No threshold is set. P-REV-1 has never set FA/FR
thresholds, and RC-5's tolerances stay placeholders.

## Renumbering: July 2026 targets → today's `MEASUREMENT.md` (v2)

| July block | July target | Lands today in | Why |
|---|---|---|---|
| Block 1 (instrument card) | §1 Protocol registry, after P-SPEED-OBJ | **§2** index row after `P-SPEED-OBJ` (payload `measurement-s2-row`) **plus** the card appended to **Annex Q** `measurement/protocols/quality-eval.md` (payload `annex-q-card`) | v2 made §2 an index whose full text lives in annexes. §5 (`MEASUREMENT.md:153`) says "an amendment appends to the owning annex file". Q holds `P-QUAL-T1`, whose card style the draft copies, and `P-CAL`, the sibling calibration protocol. |
| Block 2 (claim grammar) | §2 Claim grammar & examples | **Annex Q** card, *Grammar* bullets (inside `annex-q-card`) | Today's claim-grammar section is **§3**. Its last bullet (`MEASUREMENT.md:128`) says per-protocol grammar extensions "are defined in each protocol's annex entry", so §3 needs no edit. |
| Block 3 (noise table) | §3 Standing noise & resolution table | **§4**, appended after the last row (payload `measurement-s4-rows`) | Renumbered only; rows verbatim. |
| one-line CHANGELOG | CHANGELOG | top of `## CHANGELOG` (payload `measurement-changelog`) | §5 amendment rule. |

Two more renumbering notes. The handoff's preface cites "§5 demote-to-prior default", which
today is **§6**. That preface is not landed, so nothing changes. The Block 3 rows carry no
`unit` column value, so under §4's FLOOR-UNIT-1 sentence they are not gate inputs. That fits a
resolution formula and a caveat, and they are kept verbatim.

**Card edits beyond renumbering.** The heading moves from `###` to `##`, to match every annex
protocol heading, and gains `(RATIFIED <RATIFIED_DATE>)`. Block 1's bullets are verbatim.
Block 2's grammar line and worked example are rewritten to carry the amendment fields. The
example's numbers are re-derived so that they are internally consistent (gold-good 64, gold-bad
56, `cm=56/1;8/55`: FA 1/56 = 1.8%, FR 8/64 = 12.5%, accuracy 111/120 = 92.5%, kappa 0.85). The
July numbers (FR 12.4%, ratio 0.15) fit no integer confusion matrix at n=120. Every new bullet is
marked with *(amendment K)* or *(amendment E)*.

`<RATIFIED_DATE>` is the only token the ratify script fills, with the UTC date of the real run.

## The two amendment candidates, as landed text

- **Amendment K**, the RC-6a candidate (S1). It requires Cohen's kappa against gold, prevalence
  and accept-rate disclosure, and a published confusion matrix. The `kappa`, `acc`, `prev`,
  `accept` and `cm=` grammar fields carry it.
- **Amendment E**, the GC-external-1a candidate (S3, S4). It requires a declared tie/abstention
  estimand with its count and rate, on the gold side and on the reviewer side. Making the
  estimand an instrument field follows from S5. The `abst=` and `gold-ties=` grammar fields carry
  it.

Landing this text does not change the GC-external-1a adapter. That code still skips tie rows
until its owner implements the declaration, and box `:230` stays open for that work.

## Payloads (applied verbatim by the ratify script)

### `annex-q-card`: appended to the end of `measurement/protocols/quality-eval.md`

<!-- payload: annex-q-card -->
````markdown
## P-REV-1 — Reviewer decision calibration (instrument card) (RATIFIED <RATIFIED_DATE>)

The instrument for **reviewer-role promotion** — it gates keep/revert/deploy/promote of a *reviewer configuration*, never a model-quality (T0–T3) axis (Layer A; the plane invokes the tower, the tower never depends on the plane).
- **Instrument** = (**decision corpus id + content hash**, **gold-label source + version** — objective oracle set and/or eval-tower tier scorer, `gold_instrument_version`, ≥2 oracles or human arbitration for gate-worthy rows), **reviewer model + quant + grammar-flag** (GBNF on/off is part of the instrument), **grading model**, **rubric version**, **shadow/live mode**, **n decisions**. Changing **any** field = a **new instrument version** (append an era row per `instrument_eras.yaml`, `scope: reviewer_plane`; never rescale prior FA/FR in place).
- **Reps**: paired arms per **P-AB-1** (same decisions/prompts/grammar/stop/verifier budget both arms), **N ≥ 100/arm** for a reviewer-promotion decision; failures classified by reason (backend outage / timeout / empty / genuine) with infra-failure rate reported alongside the effect; flag-state attestation across all workers in the run header. **A single-corpus, single-run number is an observation** (never a decision), same rule as every other protocol here.
- **Consistency**: `pass^k` for review decisions (test-retest ≥2 runs; CR can inflate to ~81% at near-random accuracy under bias — report accuracy next to CR). `pass@k` is for candidate *generation*, not review.
- **Directions** (state explicitly; ambiguous-direction errors have burned debugging time): **FA (false-accept) rate — lower-better**; **FR (false-reject) rate — lower-better**; **request-evidence yield — higher-better**; **Consistency Rate (CR) — higher-better**. The **FA/FR ratio** is a first-class reported column (overcorrection dominates: FR≫FA, 10:1–440:1 — intake-836), not a derived footnote.
- **External judge-of-judge**: any externally-graded sample cites the **pinned API model-id + date** as part of the instrument version (e.g. `judge=<model-id>@YYYY-MM-DD`); a different judge model-id or date = a new instrument version. Bounded/budget-capped per the H5 Ref arm.
- **Broken-grader guardrail**: read transcripts before trusting a surprising FA/FR flip (CORE-Bench 42→95% was grader repair, not model change — intake-846).
- **Out of scope for P-REV-1**: latency/throughput/token-cost claims stay under **P-AB-1** (paired task-rate A/B) and **P-SPEED-OBJ** (task_rate axis). P-REV-1 governs *decision quality only*; the budget gate is `reviewer-latency-and-sampling-budget.md` LB-6.
- **Chance-corrected agreement** *(amendment K; intake-876)*: every P-REV-1 claim reports **Cohen's kappa between the reviewer's decisions and the gold labels — higher-better**, computed on the published confusion matrix under the declared estimands below. Raw agreement, FA, FR and CR carry no chance correction, so none of them alone validates a reviewer; kappa is the common coefficient that adds information, because its marginal-sensitive normalization exposes reviewer-vs-gold positive-rate drift.
- **Kappa is never reported alone** *(amendment K; intake-876)*: kappa collapses toward 0 under highly skewed marginals even at high raw agreement (the kappa paradox), and near-miss decision corpora are skewed by construction. Each claim therefore also discloses the **gold prevalence** (share of gold-good rows) and the **reviewer accept rate**, over the same rows as the confusion matrix.
- **Confusion matrix published** *(amendment K; intake-876)*: every claim publishes the reviewer-decision × gold-label confusion matrix as counts, in its `cm=` field (grammar below).
- **Tie/abstention estimand — declared, never cleaning** *(amendment E; GC-external-1a, intake-876)*: how ties, abstentions and malformed rows are handled is a choice of estimand, not preprocessing — excluding them, recoding them as negative and retaining them as a third class each estimate a different quantity. Every claim declares the estimand it uses (`exclude` · `recode-negative` · `third-class`) and reports the count and rate of rows it was applied to, separately for:
  - the **gold side** — source rows whose gold label is a tie or malformed, at corpus construction (for example a pairwise judge-benchmark row with no strict preference), in the `gold-ties=` field;
  - the **reviewer side** — reviewer outputs that abstain or cannot be parsed, in the `abst=` field. The failure-by-reason accounting under **Reps** is unchanged.

  Skipping such rows as data cleaning, without a declared estimand and a reported rate, is not permitted.
  - **Non-terminal decisions.** [OPERATOR: choose (a) or (b) and replace this bracket with the chosen sentence. (a) `request_evidence` and `escalate` decisions count as reviewer-side abstentions: they fall under the declared `abst=` estimand and enter `cm=` and kappa by it. (b) `request_evidence` and `escalate` decisions stay outside FA, FR, kappa and `cm=`, as the implemented report treats them today (`review_ledger.py` `NON_TERMINAL`), and the claim's attest artifact reports their count and rate beside request-evidence yield.]
- **The estimands are instrument fields** *(amendments K and E)*: the gold-side and reviewer-side estimands join the **Instrument** tuple above; changing either is a new instrument version, and numbers produced under different estimands are not compared.
- **Grammar**: `reviewer FA x%, FR y%, yield z%, CR c%, kappa k (acc a%, prev p%, accept r%, cm=<accept|good>/<accept|bad>;<reject|good>/<reject|bad>), abst=<estimand> <m>/<M> (<rate>%), gold-ties=<estimand> <t>/<T> (<rate>%) (n=N/arm, corpus rev-<id>@<hash8>, gold=<source>/v<ver>, reviewer=<model>/<quant>/gbnf=<on|off>, grader=<model>, rubric=v<r>, mode=<shadow|live>) [P-REV-1/<instrument-ver>, YYYY-MM-DD, attest <id>]`. FA/FR are lower-better; yield, CR and kappa are higher-better; the FA/FR ratio is reported. A `third-class` estimand appends its row to `cm=` as `;<third|good>/<third|bad>`.
- ✅ Worked example (illustrative — NOT a measurement): `reviewer FA 1.8%, FR 12.5% (ratio 0.14), yield 63%, CR 88%, kappa 0.85 (acc 92.5%, prev 53.3%, accept 47.5%, cm=56/1;8/55), abst=exclude 3/123 (2.4%), gold-ties=exclude 2/125 (1.6%) (n=120/arm, corpus rev-nm1@9f3a2c71, gold=gate_runner+evaltower-T1/v2, reviewer=GLM-5.2/UD-IQ2_M/gbnf=on, grader=Qwen3-Coder-30B, rubric=v3, mode=shadow) [P-REV-1/iv-1, 2026-08-xx, attest r7c1]`.
- ❌ `reviewer catches 95% of bugs` (no instrument, no n, no protocol — and conflates "detects THAT" 95–100% with "detects WHY" 52–75%; intake-836).
- ❌ `reviewer FA 1.8%, FR 12.5%, CR 88% (n=120/arm, …)` computed after skipping tie and unparseable rows (no kappa, no prevalence, no `cm=`, no declared estimand or rate — intake-876).
````
<!-- /payload -->

### `measurement-s2-row`: inserted in `MEASUREMENT.md` §2 after the `P-SPEED-OBJ` row

<!-- payload: measurement-s2-row -->
````markdown
| P-REV-1 | Reviewer decision calibration: keep/revert/deploy/promote of a reviewer configuration (corpus, gold source, reviewer model/quant/grammar, grader, rubric, mode, declared estimands) — never a model-quality axis | FA rate (↓), FR rate (↓) with the FA/FR ratio; request-evidence yield (↑); CR (↑); Cohen's kappa vs gold (↑) with prevalence disclosure and the confusion matrix; declared tie/abstention estimand with its rate | ✅ <RATIFIED_DATE> | Q |
````
<!-- /payload -->

### `measurement-s4-rows`: appended to the `MEASUREMENT.md` §4 table (Block 3, verbatim)

<!-- payload: measurement-s4-rows -->
````markdown
| Reviewer FA/FR resolution | `1/n_arm` per rate; report FA/FR ratio + CR with accuracy | P-REV-1 instrument card |
| Reviewer CR inflation caveat | CR ≈ 81% reachable at near-random accuracy | intake-837 |
````
<!-- /payload -->

### `measurement-changelog`: new first entry under `## CHANGELOG`

<!-- payload: measurement-changelog -->
````markdown
- **<RATIFIED_DATE> (v2.x)** — AMENDMENT (Annex Q, §2, §4; `RATIFY-P-REV-1-20261102`, RC-6a): registers **`P-REV-1`**,
  reviewer decision calibration, the instrument for promoting a reviewer configuration. Its card is
  appended to Annex Q, §2 gains one row and §4 gains two. Lands the July 2026 draft
  (`handoffs/active/reviewer-calibration-accounting.md`, RC-6) together with its two operator-review
  amendments from intake-876: a chance-corrected agreement statistic (Cohen's kappa against gold) with
  prevalence disclosure and a published confusion matrix, and a declared tie/abstention estimand with
  its rate on both the gold side and the reviewer side (GC-external-1a). The estimands are instrument
  fields. No threshold is set. Operator decision 2026-11-02 (decision tool, ws58), option A.
````
<!-- /payload -->

## What the ratify script does with this file (item 2)

1. It refuses unless both boxes it ticks (RC-6a `:27`, candidate `:229`) still read as unticked,
   and unless every anchor occurs exactly once.
2. If this file contains an unresolved operator slot, it STOPs, writes nothing, and prints the
   slot's line.
3. Otherwise it captures the §5 pre-state of `MEASUREMENT.md` and `quality-eval.md`. It applies
   the four payloads, filling `<RATIFIED_DATE>`, emits the §5 consolidated receipt
   (`RATIFY-P-REV-1-20261102`), and ticks RC-6a (`:27`) and the RC-6a candidate box (`:229`). The
   GC-external-1a box (`:230`) stays open, because its adapter change is code work. The item
   commits with `Operator-Ratified: yes`.
4. Item 2 runs after item 3. Both prepend to `## CHANGELOG`, and item 3's anchor is the current
   first entry.

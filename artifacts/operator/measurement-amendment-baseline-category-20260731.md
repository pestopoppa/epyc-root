# Operator decision package — measurement amendment: BASELINE / OPTIMUM / CANDIDATE

**Status**: PROPOSED, not applied. **Prepared** 2026-07-31.
**Boundary**: `MEASUREMENT.md` and every file under `measurement/protocols/` are
**human-amendment-only** (`MEASUREMENT.md:4`, `:101-103`, `:104-105`, `:117-119`; each annex
carries `RATIFIED … same trust boundary, same amendment rules` at its line 1-2). Nothing in
this package has been applied. `agents/shared/MEASUREMENT_POLICY.md:79` states "Changes are
human, PR-reviewed amendments" — so it is proposed here too rather than edited, despite the
boundary's own membership list (`MEASUREMENT.md:117-119`) omitting it. **That inconsistency is
itself a finding — see Annex D.**

---

## 1. Context

Three distinct things keep getting collapsed into the word "baseline", and the collapse has
cost repeated wasted measurement runs. The rule that prevents it exists in the repo in **four
places with four different scopes and zero at constitutional level**:

| Where it exists today | Scope | file:line |
|---|---|---|
| P-BENCH-PLACEMENT-1 gate 6 | that one protocol | `measurement/protocols/bench-cpu.md:216-220` |
| Model-registration runbook | registration only | `epyc-inference-research/docs/protocols/model-registration-runbook.md:709-710` |
| Model-admission doc | admission only | `epyc-inference-research/docs/reference/models/model-admission-2026-07-16.md:15` |
| `feedback_compare_against_top_optimized_spec` | episodic memory, which `MEASUREMENT.md:173` demotes wholesale | — |

`MEASUREMENT.md` defines **none** of *baseline*, *optimum*, *candidate*, or *headline*.
"headline" appears **zero** times. The digest (`MEASUREMENT_POLICY.md`) carries none of the
rule at all — so a session that reads only the digest, which `:5` says is its purpose, has
**zero exposure** to it.

Live leaks through the seams between those scopes are enumerated in Annex C.

---

## 2. The rule to encode (operator's wording)

> **I DO NOT CARE if a baseline performance regresses IF the optimized config improves.**

Both directions matter:

- A BASELINE **regression is not a blocker**. A gate that fails on it is a defective gate.
- A BASELINE **improvement is not a promotion argument**. It proves nothing about production.
- Promotion is evaluated **solely on the production-optimal configuration**.

And the category that keeps getting mislabelled:

- **"No speculation" is the OPTIMUM for a model with no draft path** — not a baseline.
  Qwen3-Next-80B-A3B has no draft-model path and n-gram alone yields 1.6-4.7 % acceptance, so
  `--spec-type none` is its optimum and **belongs in headline tables**. It was wrongly excluded
  from one on 2026-07-31 on exactly this confusion.

---

## 3. Options

**Option A (Recommended) — one enforceable field + one governance clause.**
Add a required `category=` field to the claim grammar (§3) and one promotion clause to
Governance (§5); narrow the two gates that currently block on baseline arms. Four small diffs,
below. Enforceable by extending the existing `scripts/validate/check_claims_grammar.sh`
(already referenced at `MEASUREMENT.md:122-124`) rather than a new mechanism.
*Entails*: touches the core file's two most-read sections. *Risk*: low — additive.
*Reversibility*: high (append-or-version; a superseding amendment names it).

**Option B — annex-only.**
Amend `bench-cpu.md:216-220` to generalise, leave the core file alone.
*Entails*: no core-file change, so no CHANGELOG entry. *Tradeoff*: **does not fix the defect** —
V1/V2/V3 in Annex C are all leaks *between* annex scopes, and a fifth scoped copy adds a fifth
seam. Also leaves the digest empty, so agent behaviour does not change.

**Option C — digest-only.**
Add the three categories to `MEASUREMENT_POLICY.md` only.
*Entails*: fastest behaviour change (the digest is what sessions actually read).
*Tradeoff*: the digest is explicitly subordinate (`:3-5`, "the constitution wins"), so a
digest-only rule is unenforceable at a gate and will be overridden by the annex text it
contradicts.

**Recommendation: A**, with the digest edit from C as its mandatory paired half — an amendment
landing only in `MEASUREMENT.md` will not change agent behaviour, and one landing only in the
digest will not survive contact with a gate.

**Default if no choice is made**: nothing is applied. The registry-side fix (the
`speculative_decoding_policy` block, already landed in
`epyc-inference-research/orchestration/model_registry.yaml`) carries the category grammar for
the *speculative-recipe* case only, and the constitution stays silent. The three gates in
Annex C keep blocking on baseline arms.

---

## Annex A — exact proposed diffs

### A1. `MEASUREMENT.md` §3 Claim grammar — INSERT after line 84

Line 84 is the `- Comparisons only within a protocol + instrument version…` bullet.

```diff
   are defined in each protocol's annex entry.
+- **Category (required)**: every reported measurement declares exactly one of
+  `category=OPTIMUM` · `category=BASELINE` · `category=CANDIDATE`.
+  - `OPTIMUM` — the best configuration AVAILABLE for that model/role. If no
+    speculative draft path exists for the model, the unaccelerated run IS its
+    OPTIMUM (e.g. Qwen3-Next-80B-A3B `--spec-type none`); such a row is a headline
+    row, NOT a baseline.
+  - `BASELINE` — an optimization the model HAS, deliberately switched off.
+    Diagnostic only. Appears only under *Addendum — baselines*. Never a headline.
+  - `CANDIDATE` — measured, not adopted. Must be labelled so it is never mistaken
+    for what production runs.
+  An unlabelled measurement is not decision-grade.
+  ✅ `ingest_long_context decode 10.12 tok/s, category=OPTIMUM (no draft path exists;
+  spec none is optimal) [P-BENCH-1, n=5, 2026-07-31, attest …]`
+  ❌ `frontdoor decode 24.92 tok/s, spec-dec off` (no category; reads as a headline,
+  is a BASELINE)
```

### A2. `MEASUREMENT.md` §5 Governance — INSERT after line 105 (the Trust-boundary bullet)

```diff
   scoring contracts are read-only for autonomous optimization processes (program.md).
+- **Promotion is decided on the production-optimal configuration alone.** A regression in a
+  `BASELINE`-category measurement is NOT a promotion blocker and MUST NOT be cited as one;
+  a `BASELINE` improvement is NOT a promotion argument. Baselines are recorded to quantify
+  what an already-adopted optimization buys, and appear only in an addendum. A gate that
+  blocks on a non-production arm is defective and is repaired, not waived. Where an
+  instrument cannot exercise the role's registered production recipe (e.g. `llama-bench`
+  cannot drive speculative decoding), its cells are RECORDED and reported alongside and
+  MUST NOT by themselves block promotion. Supersedes the protocol-scoped statement at
+  `measurement/protocols/bench-cpu.md:216-220`, which is generalised by this clause.
```

### A3. `measurement/protocols/bench-cpu.md:91-92` — narrow the blocking semantics

Current (`:91-92`): *"Every required cell must pass before promotion; a failed cell blocks
pending repair or an explicit operator waiver."*

The implementing matrix is
`epyc-inference-research/scripts/benchmark/cpu_prefill_v8_regression_runner.py:312-334` — 28
`llama-bench` prefill cells. `llama-bench` **cannot exercise speculative decoding**, so **no
cell in the promotion matrix is the production-optimal serving config**, and all 28 block.

```diff
-- Every required cell must pass before promotion; a failed cell blocks pending repair or an
-  explicit operator waiver.
+- Every required cell must pass before promotion **where that cell's configuration is the
+  role's registered production recipe**. Cells measured under a non-production configuration
+  (including any instrument that cannot exercise the role's registered acceleration) are
+  RECORDED and reported alongside, and MUST NOT by themselves block promotion; a regression
+  confined to such cells is a disclosed observation, not a gate failure. A failed
+  production-recipe cell blocks pending repair or an explicit operator waiver.
```

*(This construction is already native to the annex — `bench-cpu.md:56-57` uses the same
"diagnostic telemetry only and MUST NOT by itself invalidate an arm" wording.)*

### A4. `MEASUREMENT.md` CHANGELOG — APPEND at line 204

```diff
+- 2026-07-31 — AMENDMENT: measurement categories `OPTIMUM`/`BASELINE`/`CANDIDATE` added to §3
+  claim grammar; promotion-on-production-optimal clause added to §5 Governance, superseding the
+  protocol-scoped rule at `measurement/protocols/bench-cpu.md:216-220`; `bench-cpu.md:91-92`
+  narrowed so non-production-recipe cells record but do not block. Origin: repeated wasted
+  measurement runs from conflating a spec-off BASELINE with a no-draft-path OPTIMUM.
```

### A5. `agents/shared/MEASUREMENT_POLICY.md` — INSERT after §"The claim rule" (after line 9)

```diff
   A decision-gating number = (metric, protocol-id, n/reps, date, attestation ref).
+
+## Category — declare one, always
+
+Every number you report declares exactly one category. Conflating these is the single most
+expensive recurring measurement defect in this project.
+
+| Category | What it is | Where it may appear |
+|---|---|---|
+| `OPTIMUM` | Best config AVAILABLE for that model. **If no draft path exists, the unaccelerated run IS the optimum** (Qwen3-Next-80B: `--spec-type none`). | Headline tables. The ONLY category a promotion may be decided on. |
+| `BASELINE` | An optimization the model HAS, switched off. Diagnostic. | *Addendum — baselines* only. Never a headline. |
+| `CANDIDATE` | Measured, not adopted. | Labelled as such, never as "what production runs". |
+
+**Promotion is decided on the production-optimal configuration alone.** A BASELINE regression
+is not a blocker and must not be cited as one; a BASELINE improvement is not an argument.
+If an instrument cannot run the production recipe, its numbers are recorded, not enforced.
+
+Do not exclude a role from a headline because "speculation is off" — check first whether a
+draft path exists at all. If none does, that row is an OPTIMUM and belongs in the table.
```

---

## Annex B — why one field and not a paragraph

`MEASUREMENT.md:122-124` already points at `scripts/validate/check_claims_grammar.sh` as the
grammar validator. `category=` is a token in the same claim string the validator already
parses, so enforcement is an extension of an existing check rather than a parallel mechanism:

1. reject a decision-gating claim with no `category=`;
2. reject a promotion/ratification record whose cited arm is `category=BASELINE`.

Both are string-level checks on the claim the protocol already requires. No new artifact
format, no new schema file.

---

## Annex C — existing violations found (each is the rule failing in institutional form)

**V1 — the frontdoor's production throughput prior is a spec-dec-OFF number.**
`epyc-orchestrator/orchestration/model_registry.yaml:1314-1316` — `baseline_tps: 24.3` /
`optimized_tps: 24.3`, while `:1306-1311` declares `spec_type: draft-mtp, draft_max: 4`.
`optimized_tps` was never separately measured; the baseline figure was copied into it. It
propagates to `orchestration/derived/stack_priors.yaml:482-484` (`throughput_tps: 24.3`) with
`:485-486` `acceleration: {spec_type: none}` directly below — the derived prior certifies its
own arm is spec-off. Per `wiki/cost-aware-routing.md:142` that file is the mandated single
source of truth for admission/cost decisions. `MEASUREMENT.md:70` records the production-optimal
frontdoor at **40.22 tok/s**; the live decision surface carries a number ~40 % below it, from a
baseline arm. Compounded by `epyc-orchestrator/src/cli.py:464` and `src/mcp_server.py:74,122`,
which do `optimized_tps or baseline_tps` — silently substituting a baseline with no label change.
**This is the highest-value item in this package and it is a live routing defect, not a doc issue.**

**V2 — acceptance bars set against "plain" while production runs MTP.**
`handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md:143` (`vs plain`,
bar `>+5%`) and `:153` (bar `≥+15%`). The same document's `:21-23` establishes the production
optimum for that model as MTP at ~41 t/s, `+31% (plain 31.7)`. The bar clears a candidate at
+5 % over an arm the incumbent optimum already beats six-fold. Mirror-image error: candidate-vs-baseline
flatters the candidate. *Proposed narrowing*: every acceptance bar states its comparison arm as
`(role, production acceleration recipe as registered)`; "vs plain" is admissible only where the
registry records `acceleration.type: none` for that role.

**V3 — "every required cell must pass" makes non-production cells blocking.**
`measurement/protocols/bench-cpu.md:84`, `:91-92` + `cpu_prefill_v8_regression_runner.py:312-334`.
Both arms are spec-off *symmetrically* (v7 vs v8 kernel), so it is not the flattering shape —
the defect is purely the **blocking** semantics: a −3 % prefill regression on a config that is
never served can veto a kernel whose production-optimal serving throughput improves. This is
exactly the operator's stated concern. Diff in A3.

**V4 — latent, currently benign.**
`epyc-inference-research/scripts/benchmark/stage2_mi210_gpu_residency_runner.py:80-81` names an
arm `gpu_no_spec` "baseline", and `:442-446` sets `pass_gate` on
`decode_speedup_vs_no_spec >= PASS_SPEEDUP_THRESHOLD`, `:453` `decision_grade: pass_gate`.
Legitimate *today* only because for this role on this device no-spec genuinely is the incumbent
optimum (`k35_stack_context_matrix_runner.py:167-172`). Nothing in the gate asserts that, and
the arm name hardcodes `no_spec`. *Proposed narrowing*: read the role's registered acceleration
and assert the reference arm equals it, failing loudly on drift.

**V5 — positive precedent, lift this wording.**
`epyc-inference-research/docs/protocols/model-registration-runbook.md:709-710` already says it
correctly: *"Any `spec-dec off` figure on a speculating role appears **only** under *Addendum —
baselines*, never in a headline, summary or cross-role comparison."* Also `:428-430` and
`docs/reference/models/model-admission-2026-07-16.md:15`. These are outside the constitution's
trust boundary and have already been through operator review — the constitution is the laggard.

---

## Annex D — governance inconsistency worth resolving in the same amendment

`agents/shared/MEASUREMENT_POLICY.md:79` asserts the digest is read-only and human-amended.
But both authoritative enumerations of human-only writes omit it: `MEASUREMENT.md:117-119`
lists *"era-registry rows, this constitution and its annexes, AutoPilot baseline-state applies,
production freezes/cutovers, host reboots"*, and the digest's own `:54-55` repeats that list
without itself. So the digest claims membership of a boundary whose membership list excludes it.
Additionally `:79` scopes read-only to *"autonomous optimization processes"* (AutoPilot) — whether
an interactive session agent may edit it is genuinely unspecified.

**Proposed**: add `and its agent digest` to `MEASUREMENT.md:118`, making the digest explicitly
human-amendment-only. Cheap, separable, and removes a real ambiguity about who may edit the file
that sessions actually read.

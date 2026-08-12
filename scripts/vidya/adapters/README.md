# Adding a source to the belief kernel

**Read this before writing an adapter.** Every adapter that skipped it re-derived the grading rule
and got it subtly different. The contract exists so you write ~40 lines of projection and inherit
everything else.

Canonical spec: [`docs/design/vidya-pilot-spec.md` §4.7](../../../docs/design/vidya-pilot-spec.md).

---

## The one rule

> **An adapter PROJECTS. It never grades.**

```
native record  --project-->  ClaimTuple  --claim_tuple.grade()-->  (Q, T, reasons)  --> frames
```

You write the arrow on the left. Everything right of it is already built and tested: the ladder,
the identity scheme, frame emission, and the reasons attached to every downgrade.

If you find yourself writing `return "Witnessed", ...` in an adapter, stop — you are writing a
second copy of the constitution, and the conformance test will fail you for it.

## Source classes

The carrier is shared. The grading rule is **not**, and pretending otherwise is a category error.

| class | graded by | ceiling | ladder lives in |
|---|---|---|---|
| `measurement` | the claim rule: protocol / n / date / attestation | `Witnessed` | `claim_tuple.py` |
| `literature` | verification status (anchored, dive-verified, dive-overturned) | `Verified` | `research_intake.py` |

The literature ceiling is **structural, not a limitation to lift**. An intake entry records what
someone else reported; no amount of careful reading turns it into a protocol-admissible measurement.

Each class has **exactly one** ladder. `register_ladder()` refuses a second. A genuinely new kind of
warrant is a new class — declare it deliberately, never by accident.

## Writing one

1. **Find the tuple in the source.** Do not invent elements. What is missing must stay missing:
   it grades the claim down, which is a true statement about the measurement.

   | tuple element | what it means |
   |---|---|
   | `protocol_id` | which recipe/schema produced the number. **Absent ⇒ OBSERVATION, never gates a decision.** |
   | `reps` + `reps_basis` | n, and whether it counted what **scored** or merely what was **attempted** |
   | `date` | when it was measured |
   | `attestation_*` | path / digest / locator of the durable artifact |
   | `category` | exactly one of `OPTIMUM` / `BASELINE` / `CANDIDATE` |
   | `metric_direction` | `higher_better` / `lower_better` — **record it, never infer it** |

2. **Write `project(native) -> ClaimTuple`.** That is the whole adapter.

3. **Emit via `claim_tuple.to_frames()`** so identity and frame shape stay uniform.

4. **Test the three things that have actually broken here** (see `tests/vidya/`):
   - *identity is unique* — replay over the REAL corpus and assert `distinct claims == input count`
   - *absence is not back-filled* — a record predating the producer's hook is skipped, not invented
   - *the extractor does not understate* — probe what it missed before accepting a low coverage number

## Known and candidate sources

Keep this table current. It is the answer to "has anyone already looked at this?"

| source | class | state | adapter |
|---|---|---|---|
| `research/intake_index.yaml` | literature | **live** — 1,068 entries | `research_intake.py` |
| sealed measurement manifests | measurement | **live** — 6 sealed, all `Witnessed/Attested` | `sealed_manifest.py` |
| autopilot trial journal | measurement | **wired**, awaiting first post-hook trial | `autopilot_journal.py` |
| AutoKernel `evaluation_event` | measurement | **ready, unwritten** — schema enforces `claim_grammar` already; the loop has emitted none | — |
| wiki pages | *(not a class)* | **live** as dependency edges, never claims | `wiki_dependents.py` |
| `benchmarks/results` (2,605 files) | measurement | **rejected on evidence** — 0/200 sampled carry the full tuple; would add ~4,500 claims that gate nothing | — |
| llama-bench sweeps | measurement | candidate — needs a write-side hook first | — |
| speech kernel (whisper/qwentts) runs | measurement | candidate — unexamined | — |
| kernel promotion validation/certification receipts | measurement | candidate — v9 candidate, production GPU, DFlash, and DSpark receipts exist, but producers have no ClaimTuple write hook; do not retrofit on read | — |
| `test-backend-ops` property-layer residuals (RVP-C2-2) | measurement | **candidate — wire the write side BEFORE the layer ships** (2026-08-10). Emits a per-op, per-backend, per-shape property residual with a `suite_seed`; the seed is what makes a residual re-derivable, and RVP-C2-1 adds it. Filed at first design, not after — the read side cannot be retrofitted | — |
| E5 cell affinity-preflight artifacts (`data/contention_matrix/affinity_preflight_*.json`) | measurement | **candidate — wire the write side BEFORE the gating question is settled** (2026-08-12). Records realized per-cell placement and contention: `live_affinity_verified`, `live_memory_placement_checked`, and as of today `gpu_tenant_overlaps` / `smt_only_contention` (sibling-folded, so a GPU host lane sharing physical cores is no longer invisible). It already GATES `decision_grade` for every Stage-B cell, which is exactly the bar for needing a tuple. Filed by the author of today's change, at the change, not after | — |
| `ChatResponse.contention_gate` (A14 / BRIDGE RESIDUAL 1) | measurement | **candidate — wire the write side BEFORE the branch lands** (2026-08-12). Echoes the contention `GateDecision` per request: `admitted`, `waited_s`, `decision`, `candidate_topology_idx`, plus a `gate_decisions` list when a request passes the gate more than once. It exists PRECISELY to convert an inferred verdict into a measured one — ROUTE-A1 currently infers admit/queue from a fail-closed 503 timeout, and `queued_then_admitted` (`admitted=True` with `waited_s > 0`) is structurally invisible to that proxy. A surface whose stated purpose is *stop inferring, start measuring* is a producer by definition. **Locator warning:** the natural locator is the request/chat id, and one request can emit MULTIPLE decisions (the dispatch path records every candidate tried, not just the winner) — so a naive per-decision count reads one request as N witnesses. Key on the request, not the decision. Filed by the author of the change, at the change, while the code is still parked on `a14-gatedecision-echo` @ `a7d7bdb6` and NOT yet merged — the one moment when the write side is still cheap | — |

**Before adding a bulk adapter, price it** (the P2 discipline): sample ~50 records and count how many
carry the full tuple. If the answer is near zero, the gap is upstream and an adapter adds volume
without warrant. That check is what killed the `benchmarks/results` row above.

**And watch the locator.** Support is counted by *source locator*, so N result files measuring the
same thing read as N independent witnesses. Same-harness runs are not independent evidence — use a
run-level locator, not a file-level one.

## The other half: what CONSUMES a belief

An adapter that nobody reads is a ledger with no drivetrain. Every write-side row above exists to
serve one of these, and a new source is only worth wiring if it reaches at least one.

| consumer | question it answers | command | writes frames? |
|---|---|---|---|
| use-policy gate | "may I rely on this claim, for THIS purpose?" | `cli.py query <claim_id> --floor …` | yes — `query_served` (opt out with `--no-log`) |
| citation gate | "does anything in our documents rest on a refuted claim?" | `cli.py cite-check` | **no** — a lint pass is not a query |
| correction queue | "which unadjudicated corrections are blocking the most-cited entries?" | `cli.py corrections` | on `emit` — `correction_reviewed` |
| projection + freshness | "what did this artifact consume, and is it still current?" | `cli.py project --out …` | sidecar manifest |
| counterfactual impact | "if this measurement is retracted, what changes?" | `cli.py impact <frame_id>` | no |
| dependent staleness | "which compiled pages went stale?" | `wiki_dependents.py` | no |

**Citation forms** (`cite-check`), in increasing precision:

| form | meaning | graded |
|---|---|---|
| `intake-896` | relies on the entry — **inherits every defect of every claim in it** | all claims |
| `intake-896#03` | relies on claim 03 only | that claim |
| `intake-896#record` | *discusses* the record; asserts none of its claims | not graded (still `dangling` if the entry does not exist) |

Three rules learned by getting them wrong:

- **Discussing a record is not relying on it.** The gate's first run reported the three documents that
  *recorded* the intake-896 fabrication as resting on the fabricated claim — 50% of its headline
  finding, and the fastest possible way to teach people to ignore it. `#record` exists for that.
  Note the asymmetry: `#record` is a gate concept only. `cited_ids` still counts it as an SC5
  dependency edge, because "which pages name this entry" and "which pages rest on its claims" are
  different questions.

- **Set a consumer's default floor from measurement, not taste.** `cite-check` at
  `Verified/Located` flags 1,520 of 1,754 live citations and buries the 9 actionable ones; at
  `Hinted/Located` it flags 5. The strict floor is right when a citation is load-bearing and wrong
  as a default, for the same reason §10 caps obligation surfacing. Measure the mix, then choose.
- **A scan is not a query.** `cite-check` reads hundreds of claims nobody is relying on yet. Logging
  those as `query_served` would drown the R5 reuse series in telemetry from a linter.

## Standing practice: surface the wiring task immediately

If you are working on a process that produces measurements or verified findings, **file the
wiring task the moment you notice** — a row in the table above plus a task in
[`handoffs/active/vidya-belief-substrate-program.md`](../../../handoffs/active/vidya-belief-substrate-program.md).

Not later, not "when the substrate is ready". The cost of noticing is one table row; the cost of
not noticing is a corpus that records provenance nowhere and can never be retrofitted, because a
tuple invented on read claims warrant the original run never captured. That is exactly why
`benchmarks/results` is unrecoverable today: 4,562 files, and the write path never carried a hook.

Wiring the **write** side is cheap and permanent. Retrofitting the **read** side is impossible.

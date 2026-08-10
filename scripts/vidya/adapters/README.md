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

**Before adding a bulk adapter, price it** (the P2 discipline): sample ~50 records and count how many
carry the full tuple. If the answer is near zero, the gap is upstream and an adapter adds volume
without warrant. That check is what killed the `benchmarks/results` row above.

**And watch the locator.** Support is counted by *source locator*, so N result files measuring the
same thing read as N independent witnesses. Same-harness runs are not independent evidence — use a
run-level locator, not a file-level one.

## Standing practice: surface the wiring task immediately

If you are working on a process that produces measurements or verified findings, **file the
wiring task the moment you notice** — a row in the table above plus a task in
[`handoffs/active/vidya-belief-substrate-program.md`](../../../handoffs/active/vidya-belief-substrate-program.md).

Not later, not "when the substrate is ready". The cost of noticing is one table row; the cost of
not noticing is a corpus that records provenance nowhere and can never be retrofitted, because a
tuple invented on read claims warrant the original run never captured. That is exactly why
`benchmarks/results` is unrecoverable today: 4,562 files, and the write path never carried a hook.

Wiring the **write** side is cheap and permanent. Retrofitting the **read** side is impossible.

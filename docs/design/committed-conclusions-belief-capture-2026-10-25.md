# Committed-conclusion adapter and systematic belief capture: design proposal

**Status:** PROPOSAL ONLY. Nothing here is applied: no ledger write, no ingest, no git write and no
governance edit. Prepared 2026-10-25 by a ws58 subagent for workspace-58.
**Basis:** origin/main `6f201114228d0ad8d03877b61c58f74eb1ea3dbd` (2026-10-24T21:16Z). Every
`file:line` below is an origin/main line unless it says otherwise.
**Work files:** `work/a1/` (Class-A extraction study), `work/a2/` (tick-detector study),
`work/a3/` (verbatim governance copies), `om/` (origin/main copies of the vidya sources read).

---

## 0. Answer in one paragraph

A conclusion written in a committed progress report or a ticked handoff line fits the existing
**`measurement` source class** with **`protocol_id` empty**. The one existing ladder,
`claim_tuple.grade()`, then grades it **`Judged/Located`**: "no protocol citation, this is an
OBSERVATION, never decision-gating" (`scripts/vidya/claim_tuple.py:596-602`). No new ladder and no
new class are needed, and none is proposed. `Judged/Located` is exactly the planner floor
(`scripts/vidya/loop_beliefs.py:137-139`, `POLICY = {"use": "planner-context", "floor":
"Judged/Located"}`). So these claims are **usable, reliance-eligible planner context on the target
or knob tier when they are scoped to a model file**. They are shown as observations, with the grade
and a `retrofit` tag printed beside them. That is the same rung AutoKernel's own `experiments.db`
outcomes reach today (`scripts/vidya/adapters/autokernel_experiments.py:25-27`: "Nothing here fills
`protocol_id`, so every projection grades `Judged/Located`"). By the measurement policy they are
**priors**: "usable for hypotheses, never for keep/revert/deploy/promote/buy/close decisions"
(`agents/shared/MEASUREMENT_POLICY.md:9`). This matches the historical-number verb
**demoted-to-prior** (`MEASUREMENT_POLICY.md:50`).

The native record is **not the lost run**. It is the **committed sentence**: its commit SHA, path,
line and verbatim quote, plus scope fields that a curator confirms. That record has its own
producer, git, and it is complete. Projecting it fills nothing the lost run would have carried:
protocol, n and attestation stay empty and grade the claim down. This is the reading the operator
asked for, and §1.3 shows it is consistent with the "never back-fill" texts.

---

## 1. Source class, ladder, grade and planner weight (Q1)

### 1.1 Which class

| candidate | fit | why |
|---|---|---|
| `measurement`, `protocol_id=""` | **fits, no new rule** | A conclusion is a claim about a measurement outcome made by an identified actor. With no protocol, the ladder returns `("Judged", "Located" if has_ref else "T0")` (`claim_tuple.py:596-602`). Spec §4.5 already has the row: "Identified model or reviewer judgment: `Q2 Judged`, as anchored, scoped to that actor's authority" (`docs/design/vidya-pilot-spec.md:323`). |
| `literature` | does not fit | The ladder is owned by `research_intake.py:128` (`@register_ladder("literature", ...)`) and grades **intake verification status** (`research_intake.py:120-125`: dive-verified, dive-overturned, else Hinted). A progress report is not "what someone else reported" (`README.md:33-35`), and it has no dive status. Re-using that ladder for a different status vocabulary would be the "second dialect" the registry exists to refuse. |
| `verifier` | does not fit | A conclusion is not a checker's decided proposition (`README.md:49-83`). Forcing one would also cap at `Judged` (SC56) for the wrong reason. |
| new class | **not proposed** | Not needed. CLAUDE.md:158 says "Do not write a new grading rule". |

### 1.2 The grade, and why it is the honest one

- **Q = Judged.** An identified actor (the commit author or session) judged the outcome. No protocol
  re-derivation is possible, so the claim cannot reach `Verified` or `Witnessed`. That is true and
  wanted.
- **T = Located.** The locator `git:<sha>:<path>#L<n>` names the document, revision and line. The
  measurement ladder has no rung for `T2 MachineLocated` or `T3 Anchored` without a protocol, so the
  `quote_sha256` is carried for audit only and does not lift T. No change is proposed.
- **Grade reasons**, emitted on every frame: `["no protocol citation — this is an OBSERVATION,
  never decision-gating (MEASUREMENT.md:13)"]` (`claim_tuple.py:597-598`).

### 1.3 Consistency with the "never back-fill" texts (the operator's reading, made precise)

These texts read as blocking. Each is quoted and reconciled:

1. Spec §4.7 (`vidya-pilot-spec.md:438-440`): "**Absence is recorded, never filled.** A row that
   predates a producer's provenance hook is skipped rather than back-filled, because a tuple
   invented on read claims warrant the original run never captured."
   *Reconciled.* The adapter does not project the run's row. The run's warrant elements (protocol,
   n, attestation of raw data) stay absent and grade the claim down to an observation. What is
   projected is a different native record, the committed sentence, which does not predate its
   producer: the producer is the commit. No warrant is invented.
2. CLAUDE.md:152-153: "retrofitting the **read** side is impossible — a tuple invented on read
   claims warrant the original run never captured."
   *Reconciled, same argument.* §4 below still proposes a one-sentence clarification so the next
   reader does not take this as "conclusions may not enter". CLAUDE.md is an operator-ratify path.
3. Spec §4.5 (`vidya-pilot-spec.md:332`): "Handoff status | **no automatic grade** | work state,
   unless backed by execution or measurement evidence".
   *Reconciled.* The tick (`[x]`) is never projected. The conclusion text is projected, and only
   when a curator confirms it (§3.4). A tick with no stated outcome yields nothing.
4. Per-source rulings in the vidya handoff: "The 2026-09-24 progress narrative is retrospective and
   yields zero tuples; do not backfill" (`handoffs/active/vidya-belief-substrate-program.md:1199-1200`,
   VB-AK-DS41-OPS), and "The retrospective records produce zero tuples, and they are **not**
   backfilled" (`:1927-1928`, VB-KVU-1 / VB-SPEECH-CPU-1).
   *Partly in tension. Needs an explicit main or operator note.* Those rulings refuse **measurement
   tuples from retrospective raw records**, and that stays right. They do not address an
   observation-grade claim whose native record is committed prose. §4.2 proposes the note that
   scopes them.
5. Spec §4.5 (`vidya-pilot-spec.md:331`): "Wiki assertion | **no independent grade** — a projection
   cannot corroborate its own sources".
   *Respected.* A progress line and the handoff tick for the **same** experiment are one act by one
   author. The register merges them into **one claim** with a primary anchor and secondary anchors
   (§2.2). They never become two corroborating claims.

**Nothing in the rules genuinely blocks this.** The one item that needs a decision is the
precedent in item 4. It is a handoff ruling, not trust-boundary text, so main can scope it. The
operator has already stated the reading. The CLAUDE.md clarification (item 2) is operator-ratify
by path (§6.4).

### 1.4 How the planners see and weigh it

From `scripts/vidya/loop_beliefs.py`:

- **Floor.** `POLICY.floor = "Judged/Located"` (`:137-139`). A committed-conclusion claim passes the
  gate as `ALLOW` and is **usable**. Note that its row status prints `verified`, the gate-ALLOW
  label (`:986`). That is not Q=Verified. The grade tag beside it prints `Judged/Located`
  (`:1412-1418`).
- **Tier.** A claim reaches a tier only through `applicability` (`:925-937`). A claim with **no
  scope is dropped silently** (`:934`, `continue`). So **scope is mandatory for usefulness**:
  - `model_file` (exact GGUF basename) plus any of `quant` / `backend` / `device` / `context_tokens`
    gives the **target** tier (`:542-549`), or the **knob** tier when the claim also declares a
    `knob_family` in `KNOB_FAMILIES` (`:126-127`, `:584-591`). These are reliance-eligible
    (`:122`, `_MODEL_TIERS`).
  - A different member of the same `MODEL_LINEAGE` family, with backend or device declared, gives
    the **sibling** tier (`:551-567`): "transfer unproven, never target evidence".
  - `device` only, with no model, gives the **host** tier (`:570-575`): at most 3 lines and not
    reliance-eligible.
  - `stack_regime` gives the **lineup** tier (AutoPilot lineup targets, `:578-581`).
- **Run grouping. This must be avoided.** If a source kind's rows carry `run_id`, `collect()` keeps
  **only the newest complete run per source kind** and marks every other run `superseded_run`
  (`:1018-1051`). The adapter must therefore **never set `applicability.run_id`** (or
  `run_expected_keys`). Every conclusion then stays a standalone candidate (`:1020-1022`).
- **Rendering.** If the evidence frame carries `observation`, the line is value-bearing (value,
  unit, outcome, effect). Otherwise the claim text is shown, capped at 440 characters on model tiers
  (`:1408-1440`, `CLAIM_TEXT_CAP`). The `retrofit` tag prints when `observation.retrofit` is true
  (`:997`, `:1413-1414`).
- **Ranking and caps.** Target 16, knob 8 when target-tier rows exist, sibling 8, host 3
  (`:116-121`). Historical conclusions compete with live AK and AutoPilot rows for those slots.
  `_mark_stale_epochs` (`:868-883`) moves older-epoch rows to the "older epochs" note **only when
  the claim declares `epoch`**. So the register must carry `epoch` whenever it is known (§2.3), or
  July conclusions will crowd out current-epoch evidence.

**Answer to "prior vs evidence".** These are planner-visible observations: priors. A planner may
name them in `relies_on_claims` as premises for a hypothesis. No loop keeps or reverts on them,
because the loops' keep decisions rest on their own new measurement. MEASUREMENT_POLICY.md:9 holds
unchanged.

---

## 2. Native record shape (Q2)

### 2.1 Where the native record lives

The native record is a row in a **committed, append-only register**:
`data/belief/committed_conclusions.jsonl` (root repo), schema `epyc.vidya.committed_conclusion.v1`.
One row is one concluded experiment. The register exists for two reasons:

1. **Deterministic and auditable.** The adapter never parses prose at ingest time. It re-checks
   each row's quote against the git blob and projects the row. Pattern extraction (§3) only
   *proposes* rows, and a confirmer accepts them.
2. **It mirrors a pattern that already works.** `research/intake_index.yaml` is a committed register
   that `cli.py sync` folds into the ledger, with a freshness marker (`scripts/vidya/sync.py:36-107`)
   and the post-commit hook on main (`scripts/vidya/hook_sync.sh:1-24`). The new register can ride
   the same rails (§4.3).

### 2.2 Row schema (`epyc.vidya.committed_conclusion.v1`)

```json
{
  "schema": "epyc.vidya.committed_conclusion.v1",
  "cc_id": "cc:v1:<sha256(anchor.basename + '\\0' + quote_norm)[:32]>",
  "rev": 1,
  "kind": "result",                 // result | decision. A decision row is recorded and NEVER projected (spec §4.5: operator approval = intent plane, no Q/T)
  "anchor": {                       // PRIMARY: where the conclusion was committed. The UNIT IS THE ITEM:
                                    // the checkbox line plus its continuation lines, not one physical line
    "repo": "epyc-root",
    "commit_introduced": "<40-hex: first commit whose blob contains the item head>",
    "commit_concluded": "<40-hex: first commit where the item is [x] AND carries the verdict/number>",
    "commit_last_touched": "<40-hex: informational only; may be a mass rewrite>",
    "commit_date": "2026-07-17T..Z", // date of commit_concluded
    "path": "handoffs/active/gemma-challenge-kernel-techniques-v7.md",
    "line_start": 419, "line_end": 423,   // AT commit_concluded, never at HEAD
    "quote": "<verbatim item text at commit_concluded:path:line_start..line_end>",
    "quote_sha256": "<sha256 of quote bytes, UTF-8, lines joined by \\n>",
    "head_norm": "<normalised first line of the item, <=200 chars>",
    "quote_norm_rule": "cc-norm/v1"   // strips belief markers, ✅ dates, ARTIFACT LOST / REPOINTED suffixes
  },
  "also_anchored": [                // SECONDARY anchors for the SAME act (progress line, results table row)
    {"repo": "epyc-root", "commit": "...", "path": "progress/2026-07/2026-07-16.md", "line": 88,
     "quote_sha256": "..."}
  ],
  "task_id": "KPF-18.0b",           // handoff task token, if present in the line
  "stated": {                       // ONLY what the text states; null when it does not
    "verdict_native": "KEEP",       // verbatim token from the text; MAY be null (metric-only items, e.g. K26)
    "metrics": [                    // zero or more; one claim per entry (an item often states several arms)
      {"metric": "decode_tps", "value": 41.3, "unit": "t/s",   // curator-normalised name
       "effect_rel": 0.0711,        // only if the text states a relative effect
       "arm": "f16/f16"}            // arm label as written, if any
    ],
    "n": 10,                        // stated n; NEVER projected into ClaimTuple.reps
    "protocol_named": "bench_canonical.sh",   // as named in the text; NEVER projected into protocol_id
    "date": "2026-07-16"            // the ✅ date or a date in the text
  },
  "scope": {                        // curator-CONFIRMED planner scope; omit unknown keys
    "model_file": "Qwen3.6-35B-A3B-Q4_K_M.gguf",
    "quant": "Q4_K_M", "backend": "cpu", "device": "epyc-9655",
    "context_tokens": 4096, "build_sha": "0db32c06e", "epoch": "E8",
    "knob_family": "spec_draft", "role": "worker_general", "stack_regime": null
  },
  "scope_evidence": "line|heading|handoff-header|none",   // where the scope was read from
  "category": "CANDIDATE",          // OPTIMUM | BASELINE | CANDIDATE, curator-recorded
  "metric_direction": "higher_better",   // curator-recorded from the stated metric; see 2.4
  "raw_evidence": {"paths": ["/mnt/raid0/llm/tmp/v7-perf-20260716"], "status": "lost",
                   "event": "E0 2026-08-23 disk reclaim"},
  "covered_by": null,               // a claim id from a native adapter, if one exists. Then the row DECLINES.
  "supersedes": null,               // cc_id:rev this row replaces
  "confirmed_by": {"actor": "<session or person id>", "at": "2026-10-25T..Z",
                   "method": "agent|human", "extractor": "cc-extract/v1@<sha>"},
  "retrofit": true                  // true = conclusion committed before this register existed
}
```

**Identity.** `cc_id = H(anchor basename, head_norm)`. It hashes the item's **head** (its first
line, normalised), not the full quote, so continuation lines appended later do not change it. The
commit and line are left out, so these events do not mint a duplicate claim:

- the handoff moving `active/` to `completed/`;
- line drift;
- a later `ARTIFACT LOST` / `REPOINTED` suffix (stripped by `cc-norm/v1`).

A **substantive correction** of the item mints `rev + 1`, with `quote` taken at the correction
commit. For example, S-10's WER was corrected on 2026-10-20 in `4e53392f8`. The `measurement_id`
is `<cc_id>:r<rev>[#m<k>]`, where `#m<k>` selects the k-th stated metric. A correction emits the
new rev plus `pubinfo.supersedes` with a `supersedes_reason` (`README.md:104-110`, SC59).

**Where the commits and lines come from (deterministic).** **Do not use `git blame`.** It returns
the last touch: a correction commit, or a mass rewrite such as `2053b7585` (2026-07-29), which
blames K25.2a and K26 although those were introduced on 2026-07-17 in `609920933`
(`work/a1/class_a_items_intro.tsv`).

- `commit_introduced`: `git log --reverse --format=%H -S'<item head, first 60 chars>' origin/main
  -- <path>`, first result.
- `commit_concluded`: walk forward from there with `git log --reverse -p` to the first commit
  whose version of the item is `[x]` and contains the verdict or number. Filed-then-ticked items
  need this. DS41-C98 was filed in `506f281d0` (10-01) and concluded in `ab24ea14f` (10-03).
- `commit_last_touched`: `git log -1 -S` on the full current text. It is recorded as information
  only.

All three are pure functions of origin/main history. At ingest the adapter **re-reads** `git show
<commit_concluded>:<path>` lines `line_start..line_end`. It refuses the row unless their sha256
equals `quote_sha256`. That is the audit check.

### 2.3 Projection into `ClaimTuple` (what the adapter writes)

| ClaimTuple field | value | rule |
|---|---|---|
| (row filter) | `kind == "decision"` → declined, 0 frames; `covered_by` set → declined, 0 frames | spec §4.5 intent plane; no duplicate of native frames |
| `measurement_id` | `cc_id + ":r" + rev`, plus `"#m" + k` per stated metric (k = 0 when there are no metrics) | pure function of the row |
| `metric` | `stated.metrics[k].metric`, or `"stated_conclusion"` when there are none | |
| `value` / `unit` | that metric's stated value and unit; else the verbatim verdict token, unit `""` | |
| `metric_direction` | the row's recorded value; `"higher_better"` for `stated_conclusion` (presence carrier, the house precedent at `research_sweeps.py` and `contention_gate`) | recorded, never inferred at ingest |
| `date` | `anchor.commit_date` | |
| `category` | the row's | |
| `claim` | `"Committed conclusion (" + sha7 + " " + path + ":" + line + "): " + quote_norm` + `" [raw artifact lost: <event>]"` when `raw_evidence.status == "lost"` | provenance is in the display text, because `to_frames` does not emit `extra` (`claim_tuple.py:846-910`) |
| `protocol_id` | **always `""`** | the adapter REFUSES a row that tries to set it; `stated.protocol_named` rides in the claim text only |
| `reps` / `reps_basis` | **always `None` / `""`** | stated n is text, not a scored count |
| `attestation_path` | `anchor.path` | |
| `attestation_locator` | `git:<commit>:<path>#L<line>\|q=<quote_sha256>` | loop_beliefs keys on the part before `\|` (`loop_beliefs.py:943-948`) |
| `attestation_sha256` / `attestation_verified` | unset | the ladder ignores them without a protocol, and setting them invites misreading |
| `source_kind` | `"committed-conclusion"` | |
| `source_class` | `"measurement"` (default) | |
| `applicability` | `scope` keys verbatim + `scope_basis: "native"`; **never `run_id`** | §1.4 run grouping |
| `observation` | `retrofit`, `outcome_native` (verbatim verdict), `outcome` only via the closed table in 2.4, `effect_rel` / `anchor_value` only when stated, `outcome_reason` = quote_norm[:300] | `claim_tuple.py:148-169` keys only |

`to_frames(..., adapter_id="vidya.adapters.committed_conclusion/v1")` emits the usual three frames
per claim (source_observed, claim_proposed, evidence_supports_claim), with `provenance.retrofit`
from the row.

### 2.4 Closed verdict-to-outcome table (projection vocabulary, not grading)

| verbatim token in text | `observation.outcome` |
|---|---|
| KEEP, IMPROVED, WIN (with a positive stated effect) | `improved` |
| NULL, INCONCLUSIVE, DOES NOT REPLICATE, "within noise" | `null` |
| REGRESSED, REGRESSION, LOSS (with a negative stated effect) | `regressed` |
| FAIL on a correctness check, "not bit-identical", DIVERGES | `divergence` or `refused_correctness` (curator picks) |
| baseline or floor reading | `anchor` or `floor` |
| GO, NO-GO, PASS, DROPPED, SHELVED, ADOPTED | **no `outcome`**: `outcome_native` only, because these name a decision, not an effect sign |

The adapter applies this table mechanically. Ambiguous rows get no `outcome`. That is "recorded,
never inferred" (`README.md:174`).

### 2.5 Scoping to planner targets

`model_file` must be the **exact GGUF basename**. That is the key the target tier matches
(`loop_beliefs.py:512-523`). Prose names ("Q38FN", "27B", "DS41") are resolved at **extraction
time** and proposed to the confirmer, never at ingest. The resolution sources, in order:

1. The line itself (a `.gguf` basename or a model path).
2. The `MODEL_LINEAGE` labels table, label to basename (`loop_beliefs.py:483-501`). This covers
   DS41 and Q38FN.
3. The model registry or `stack_topology.yaml` role-to-model binding as of `anchor.commit_date`
   (orchestrator repo, read at that date). This applies only when the line names a role.
4. The handoff's section heading or header block (`scope_evidence: "heading"` / `"handoff-header"`).

Backend and device come from the text (`GPU`, `MI210`, `HIP`, `gfx90a` map to `gpu`/`gfx90a`;
`CPU`, `EPYC`, `numactl` map to `cpu`/`epyc-9655`; `DEVICE_BY_BACKEND`, `loop_beliefs.py:140`).
`epoch` comes from `instrument_eras.yaml` by `stated.date`, a timestamp lookup and the method
MEASUREMENT_POLICY.md:49 prescribes. A row whose model cannot be resolved still enters the
register with `scope: {}` and `scope_evidence: "none"`. The adapter projects it, but planners never
see it (dropped at `loop_beliefs.py:934`). The source report counts it under "unscoped", so the gap
is visible and not silent.

---

## 3. Extraction strategy and precision (Q3)

### 3.1 Two candidate streams

- **Handoff ticks.** `^\s*[-*] \[[xX]\]` lines in `handoffs/{active,completed,archived,blocked}/`
  on origin/main: **6,992** ticked lines today. Of these, **716** match a coarse verdict-or-number
  pattern (counted 2026-10-25 with `git grep` on origin/main).
- **Progress shards.** `progress/2026-*/*.md`: **794** files on origin/main, **4,990** lines
  matching the same coarse pattern. These are mostly Results-table rows and verdict sentences, plus
  many restatements of handoff ticks.

### 3.2 Pattern-based proposal, then confirmation (hybrid, recommended)

Pure hand-curation does not scale (about 5.7k candidate lines). Pure pattern extraction is not
precise enough to project unreviewed (numbers below). So:

1. **`cc-extract/v1`** (a deterministic script, committed). For each candidate line it emits a
   draft register row: anchor via `git log -S` + `git blame`, verbatim quote, `task_id` token,
   `stated.*` by regex, scope proposals per §2.5, `scope_evidence`, verdict to outcome per §2.4,
   and a **dedup key** (task_id, else normalised quote) that merges progress restatements into the
   handoff anchor as `also_anchored`.
2. **Confirmation**, by an agent (cheapest capable model, one batch per handoff) or a human. The
   confirmer accepts, rejects or edits **only** these fields: is-a-conclusion,
   `scope.model_file`, `category`, `metric_direction`, `outcome` where ambiguous, and `covered_by`.
   `confirmed_by` records who. The quote, anchor and `stated.*` are machine fields and may not be
   edited by hand. To change them, re-extract.
3. **Main applies** the batch to the register (subagent prepares, main applies: CLAUDE.md, *Index
   rows ... a subagent may PREPARE*, and memory "shared-repo edits: MAIN applies").

### 3.3 Measured precision

**Tick stream, last 14 days** (`work/a2/`; 690 added `[x]` lines on 10-20..10-24; 96 hand-labelled,
stratified, seed 58; 25 RESULT / 71 NOT-RESULT):

| detector | precision | recall | flags / 690 |
|---|---|---|---|
| A: verdict lexicon only | 0.80 | 0.32 | 46 |
| B: verdict OR number-with-unit OR result-artifact cite | 0.58 | 0.60 | 157 |
| C: B tuned with plumbing and spec-title exclusions (**in-sample**) | 0.64 | 0.56 | 120 |

The two stricter variants I tried (artifact-or-verdict minus plumbing; artifact-only) scored worse:
P 0.40 / R 0.16, and P 0.20 / R 0.04 (`work/a2/detD.py`). Reasons: the labels came from 500-char
truncations, and many result ticks are bare `✅ <date>` with the outcome in a prose block below
(M4.2a, KPF-18.0d item 3 v2).

**Class-A set and general samples:** see §3.5 (`work/a1/`).

**Conclusion.** On line text alone, no detector reaches low false positives at useful recall. This
supports the hybrid in 3.2. Patterns propose, and a confirmer decides. At P ≈ 0.6 a confirmer
rejects about 4 of 10 proposals. At the tick-contract gate (§7) a false positive costs one
`no-belief:` clause, so the gate can tolerate the low precision.

### 3.4 Where a human or agent must confirm

| field | why it cannot be mechanical |
|---|---|
| is-a-conclusion | precision 0.58-0.80 (above) |
| `scope.model_file` | prose names to basenames: lineage, role binding as of a date, heading context |
| `category` | OPTIMUM / BASELINE / CANDIDATE is a measurement-policy judgment (`MEASUREMENT_POLICY.md:11-22`) |
| `metric_direction` | "record it, never infer it" (`README.md:174`) |
| `outcome` where §2.4 leaves it ambiguous | sign of effect versus decision word |
| `covered_by` | whether a native adapter already projected this run (for example `inf70-ingest-ds41scope`, 48 frames) |

### 3.5 Class-A study results (`work/a1/`, origin/main 6f201114, read-only)

**The unit is the item, not the line.**

- The 157 Class-A citing lines are **120 distinct items**. The cited line is usually a wrapped
  continuation of a long `- [x]` item, so the line by itself carries no verdict. Item = checkbox
  line plus its continuation lines (§2.2 `line_start..line_end`).
- Tick state of the 120 items: **92 ticked**, 12 unticked, 16 with no checkbox (prose or
  blockquote).

Hand labels (TRUE = the text states an outcome of an experiment or measurement), set blind to the
detector:

- **54 of 120** Class-A items are TRUE.
- Of a random sample of 60 ticked items from the 4,326 in `handoffs/active`, **10** are TRUE.
- Of 40 bullets or rows from `### Results/Verdict/Findings` sections of `progress/2026-10` (338
  candidates), **20** are TRUE.

| set | v1 P | v1 R | v2 P (in-sample) | v2 R (in-sample) |
|---|---|---|---|---|
| Class-A items (n=120) | 0.62 | 0.85 | 0.80 | 0.59 |
| random ticked items (n=60, only 10 positives: noisy) | 0.44 | 0.80 | 0.58 | 0.70 |
| progress Results/Verdict bullets (n=40) | 0.83 | 0.25 | 1.00 | 0.70 |

- **v1**: a ticked box AND
  `\b(KEEP|NULL|NO-GO|GO|PASS|FAIL|REGRESS(?:ED|ION)?|IMPROVED|CONFIRMED|REFUTED|RETRACTED|DROPPED|ADOPTED|WIN|LOSS|SHELVED|INCONCLUSIVE|VERDICT)\b`,
  OR a number with a unit.
- **v2**: an additive score (verdict tokens +3; outcome phrases such as "did not reproduce",
  "within noise", "falsified", "wins", "inverts" +2; quantity with a unit +2; fractions and table
  rows +1; delta / vs / A/B / baseline +1; a plumbing word in the first 140 characters with no
  verdict −2; an unticked item −9). Threshold ≥ 3, applied to the first 500 characters of the item.
  The exact patterns are in `work/a1/det.py`.
- v2 residual false positives: plumbing or smoke items that quote throughput (K35.13c/f, K35.15).
- v2 residual false negatives: results beyond the first 500 characters (K23, DF2-14, RI-16) and
  table rows with bare numbers.
- **Planned refinement for `cc-extract/v1`:** gate on the ticked item, then score per **sentence**,
  not per item, because one item often mixes "adds runner + tests" with the result. Add
  `NOT significant`, `NOT folded`, `NEGATIVE` and `REJECTED` to the lexicon.

**Scope resolvability, on the 54 TRUE Class-A items:**

| scope source | items |
|---|---|
| model plus quant or device in the item text | 33 |
| partial (model only, or quant/device only) | 12 |
| section heading only | 1 |
| none | 8 |

So about 61% are directly scopable, 22% need confirmer completion, and 15% will stay unscoped
(counted, not planner-visible). Headings almost never add scope.

**Content of the 54 TRUE Class-A items:** metric plus value in **42**; verdict only in 8; neither
in 4. Two shapes force schema features:

- Metric-only items (K26, a four-arm t/s table with no verdict word) need `verdict_native: null`
  and multiple `stated.metrics`.
- Operator-decision items (DS41-C98: "operator chose D: status quo") need `kind: "decision"`, which
  is never projected.

**Second statements in progress reports.** Of 102 lost paths, **90** have their basename mentioned
under `progress/`. **33** have a progress line naming the path that also carries a number or
verdict (regex level). 51 qualify by basename or task ID together, and task-ID matching
over-matches on generic IDs (K35.x), so treat it as a lead only. These progress statements become
`also_anchored` on the handoff item, never second claims.

**Worked examples** (introducing or concluding commit from `-S`):

| item | anchor | register row would hold |
|---|---|---|
| S-10 | `multimodal-pipeline.md:304`, `a5b8ac53f` (07-31); corrected `4e53392f8` (10-20) | whisper large-v3-turbo / f16 / MI210 (gpu, gfx90a); WER 3.37 % (`lower_better`); verdict DROPPED (Qwen3-ASR); r1 then r2 superseding at the correction |
| AK-MMQ-H10 | `autokernel-research-loop.md:5589`, `21567aed2` (09-27) | Qwen3.8-27B / Q8_0 / gpu; two metrics, p=64 −12.6 % and p=112 −9.1 %; verdict NEGATIVE, rejected → outcome `regressed` |
| K26 | `gemma-challenge-kernel-techniques-v7.md:419`, introduced `609920933` (07-17); blame wrongly says `2053b7585` | Qwen3.6-35B-A3B-MTP-Q8_0 / MI210; 4 arm metrics (`f16/f16 100.013 t/s`, ...); verdict null |
| XFER-4 | `cpu-decode-roofline-program.md:3866`, `38bc3795c` (10-04) | UD-IQ4_XS / cpu; pp5 −12.2 % [−16.9, −8.8]; NOT folded → `regressed` |
| K25.2a | `gemma-challenge-kernel-techniques-v7.md:416`, `f0f59fab5` (07-17) | Qwen3.6-27B Q8 + MTP Q8; verdict FALSIFIED; no metric → `stated_conclusion` |
| A2/H1 | `architect-model-selection-bench.md:216`, `f3b2a3c8f` (07-24) | n=141 (text only), p≈0.096, NOT significant → `null`; device unstated → partial scope |
| R23-5 | `autokernel-rebuild-program.md:1069`, `b95ab81eb` (09-01) | champion `9e18beb0` vs v9 (`build_sha`); multi-surface deltas; CONFIRMED; model and device unstated → confirmer completes or leaves unscoped |
| DS41-C98 | `deepseek-v41-flash-evaluation.md:920`, filed `506f281d0` (10-01), concluded `ab24ea14f` (10-03) | `kind: decision` (operator chose status quo), declined; the +0.101 % bench-keep sum may be recorded as a separate result row if the confirmer judges it a measured outcome |

---

## 4. Write-side wiring (Q4): prepared, not applied

### 4.1 `scripts/vidya/adapters/README.md`, Known and candidate sources: new row (main applies)

```diff
@@ ## Known and candidate sources
 | source | class | state | adapter |
 |---|---|---|---|
+| Committed conclusions: a concluded experiment stated on a ticked handoff line or in a root `progress/` report, recorded in the committed register `data/belief/committed_conclusions.jsonl` (`epyc.vidya.committed_conclusion.v1`; one row per conclusion, anchored by introducing commit SHA + path + line-at-commit + verbatim quote + `quote_sha256`; proposed by `cc-extract/v1`, confirmed by an identified agent or human) | measurement, OBSERVATION (existing ladder; `protocol_id` always empty, so `Judged/Located`; no new class or ladder) | NOT YET WIRED (VB-CC-1). The native record is the committed sentence, not the run: protocol, n and attestation of the raw run stay ABSENT and grade the claim down, so no warrant is invented (spec §4.7 "absence is recorded, never filled" holds). Ticks are never projected; only confirmed conclusion text. One act = one claim (a progress restatement is a secondary anchor, never a corroborating claim, spec §4.5 wiki row). The adapter REFUSES a row that sets `protocol_id` or `reps`, or whose quote does not re-hash against `git show <commit>:<path>`. It never sets `applicability.run_id` (`loop_beliefs.collect` would supersede all but the newest run). Unscoped rows are counted, not dropped silently. A row whose run has native frames declines (`covered_by`). | `scripts/vidya/adapters/committed_conclusion.py` (to write); `cli.py ingest committed-conclusion --path data/belief/committed_conclusions.jsonl --as-of <ts> --only-new`; sync-source registration per VB-CC-3 |
```

### 4.2 `handoffs/active/vidya-belief-substrate-program.md`: new section (main applies)

```diff
+## VB-CC — committed-conclusion source (filed 2026-10-25, ws58)
+
+Operator reading 2026-10-25: a reader must not INVENT measurement warrant, but recording what was
+concluded, with honest provenance (committed document, commit SHA, file:line), is legitimate. The
+earlier "retrospective yields zero tuples" rulings (VB-AK-DS41-OPS, VB-KVU-1/VB-SPEECH-CPU-1) stand
+for MEASUREMENT tuples projected from retrospective raw records; they do not forbid an
+observation-grade claim whose native record is the committed sentence. Design:
+`/mnt/raid0/llm/tmp/ws58-conclusions-adapter-design-20261025/DESIGN.md`.
+
+- [ ] **VB-CC-1 — committed-conclusion adapter.** `scripts/vidya/adapters/committed_conclusion.py`
+  projects `epyc.vidya.committed_conclusion.v1` register rows into `ClaimTuple` (measurement class,
+  `protocol_id=""`, `reps=None`, never `run_id`), re-hashes each quote against
+  `git show <commit>:<path>`, declines `covered_by` rows, and registers `ingest committed-conclusion`
+  in `ingest_sources.py`. Tests: identity unique over the real register; a re-ingest emits zero
+  frames under `--only-new`; a row with `protocol_id` or `reps` set is refused; a quote mismatch is
+  refused; every projected tuple grades `Judged/Located`; no frame sets `run_id`.
+- [ ] **VB-CC-2 — `cc-extract/v1` extractor + confirmation worksheet.** Deterministic candidate
+  emission from ticked handoff lines and `progress/2026-*` Results/Verdict lines on origin/main
+  (anchor via `git log -S` + `git blame`), scope proposals (line, MODEL_LINEAGE, role binding at
+  date, heading), dedup into one row per act with `also_anchored`. Confirmation edits only
+  is-a-conclusion / scope / category / direction / ambiguous outcome / covered_by.
+- [ ] **VB-CC-3 — sync and freshness.** Fold the register into the canonical ledger the way the intake
+  index is folded: `sync.py` marker over the register digest, and `hook_sync.sh` also fires on
+  `data/belief/committed_conclusions.jsonl`, so `loop_beliefs.prepare`'s `ensure_current` sees a
+  stale register as stale.
+- [ ] **VB-CC-PILOT — pilot on the 102 Class-A rows + the 2 ledger-surviving cases** (DESIGN §5),
+  then the full backfill in batches by handoff.
+- [ ] **VB-CC-TICK — tick contract + wrap-up belief-capture gate** (DESIGN §7), staged
+  advisory to enforced.
```

### 4.3 Ingest path and idempotency

- **Backfill and steady state:** `python3 scripts/vidya/cli.py ingest committed-conclusion --path
  data/belief/committed_conclusions.jsonl --as-of <UTC> --only-new`. `--only-new` drops every claim
  that is already live (`scripts/vidya/ingest_sources.py:634-713`). It refuses a partial bundle, and
  it refuses a divergent payload under one identity (`:704-710`). That is why a correction must bump
  `rev` (a new id) and must not edit a row in place.
- **Single writer.** The ledger write lease applies as for every ingest. No session ingests outside
  the existing event paths (wrap-up 5b says "do NOT ingest as a wrap-up step -- ingest is
  event-driven", `agents/commands/wrap-up.md:512-517`). Once VB-CC-3 lands, the register is just
  another event source: post-commit on main plus `prepare()`'s `ensure_current`.

### 4.4 cite-check implications

- Today `cite-check` parses only `intake-NNN[#NN|#record]` (`scripts/vidya/citation_gate.py:56`,
  `^clm_intake_(\d+)_(\d+)$`; `cli.py:870-890`). A bare `clm_*` in prose is not checked.
- **Proposed:** extend `citation_gate.py` with one more form, `[belief: <claim_id>]` (and
  `belief: cc:v1:<hex>`). The gate resolves it in the folded ledger and blocks (exit 3) on
  dangling, refuted or conflicted, exactly as for intake. It reuses the same gate and floor and adds
  no grading.
- Writing **about** a committed conclusion in prose is not a citation unless it carries the
  `[belief: ...]` form. So unlike the intake rule, a findings write-up does not flag itself.
- `index_state.py --check` already runs `cite-check` over changed paths (`index_state.py:1053-1124`).
  The new form is then gated at commit time for free.

### 4.5 Ledger volume estimate

- The ledger today has **38,415 frames, 42.97 MB** (about 1.12 KB per frame; `wc` on
  `/mnt/raid0/llm/state/vidya/ledger.jsonl`, read-only).
- **Tick conclusions.** 10 of 60 random ticked items in `handoffs/active` are conclusions (17%;
  95% CI about 8-28%). Over the roughly 4,300 ticked items in `active/` plus about 2,700 ticked
  lines in `completed/` and `archived/` (6,992 ticked lines in all), that gives about **1,200
  conclusion items** (range 550-2,000).
- **Progress conclusions.** 20 of 40 Results/Verdict bullets in October are conclusions, out of 338
  candidates that month, so about 170 per month in the heaviest month. Over 2026 shards (794 files)
  that gives about 800-1,200. Assuming about half restate a tick (`also_anchored`, no new claim),
  the net is about **500**.
- **Claims.** About **1,700 items**. At about 1.5 claims per item (multi-metric arms; 42 of 54 TRUE
  Class-A items state a metric), that is about **2,500 claims**, or **7,500 frames** (range
  4,000-12,000).
- **Size.** About **+8.5 MB, +20% of the ledger** (range +11% to +31%). Unscoped rows still emit
  frames, but planners never read them.
- **Steady state.** Detector C flagged 120 ticks in 5 active days, about 24 per day, of which about
  64% are results. That is about 15 result ticks per day fleet-wide, about half of them covered by
  native adapters. So the committed-conclusion path adds about 8 claims per day, about 25 frames.

---

## 5. Pilot plan (Q5)

**Test set.** The 102 Class-A lost-evidence paths from
`/mnt/raid0/llm/tmp/ws58-tmp-loss-reconcile-20261025/LOSS-INVENTORY.tsv` (`class == A`). They have
157 citing lines, which are **120 distinct items** (`work/a1/class_a_items.json`), and **54** of
those are hand-labelled conclusions (`work/a1/labels_classA_true.json`). That is the gold set: a
pilot that proposes, confirms and projects exactly those 54 has known recall and precision.
Expected confirmed rows: about 54. Of these, about 33 are fully scoped, about 12 are partial and
completed by the confirmer, and about 8 are unscoped. Plus the ledger-surviving cases:

- `inf70-ingest-ds41scope`: 48 `claim_proposed` frames, all hashed, sources
  `src_inf70_results_ds41scope_20260926T105535Z_*` (`ledger_hits.json`). This is the only Class-A
  ledger hit the reconcile scan found.
- `sub-gpu-runner-20260916`: ledger-cited (24 substring hits), named at `RECONCILE-PLAN.md:386`, and
  not in `ledger_hits.json`. **Confirm its class before using it as the second case.** If it is not
  Class A, the "2 in the ledger" figure needs re-deriving from the reconcile scan.

Both test the `covered_by` decline path (AC5).

**Steps** (every step dry-run first; main applies the register; the ledger owner ingests):

1. `cc-extract/v1` on the Class-A citing lines only, which yields draft rows.
2. Confirmation pass (one agent batch per handoff; the gemma-challenge-v7 handoff alone is 54
   lines). Record `confirmed_by`.
3. For the two ledger-surviving cases, set `covered_by` to the existing claim ids.
4. `cli.py ingest committed-conclusion --path <pilot register> --as-of <ts> --dry-run`, then for
   real with `--only-new`.

**Acceptance checks**

| # | check | how |
|---|---|---|
| AC0 | **Extractor recall and precision on the gold set** | `cc-extract/v1` over the 120 Class-A items proposes ≥ 50 of the 54 gold conclusions (recall ≥ 0.92 at the proposal stage, which is tuned low-threshold because confirmation removes false positives). Precision is reported, not gated. Every confirmer rejection is recorded with a reason, so a held-out precision exists for the full backfill |
| AC1 | **Idempotent re-ingest** | a second `ingest ... --only-new` reports `frames_skipped == 3 × projected` and 0 new frames; a full (non-only-new) dry-run produces byte-identical frames apart from `created_at` / `frame_id` |
| AC2 | **Identity unique** | distinct `claim_id` count equals confirmed-row count; renaming `active/` to `completed/` in a fixture leaves `cc_id` unchanged |
| AC3 | **No measurement-grade warrant** | for every projected frame: `evidence.grade == {"Q":"Judged","T":"Located"}`, `protocol_id == ""`, `reps is None`, grade_reasons contains "no protocol citation"; a fixture row with `protocol_id` or `reps` is REFUSED at projection |
| AC4 | **Quote audit** | every row re-hashes against `git show <commit>:<path>` line `line`; a mutated fixture quote is refused |
| AC5 | **Covered rows decline** | the two ledger-surviving cases emit 0 frames and appear as `declined: covered_by` in the report; no duplicate claim of the inf70 frames |
| AC6 | **Right tier in `loop_beliefs prepare`** | for one CPU and one GPU target whose model appears in the pilot (for example the v7 Gemma file on `gpu`/`gfx90a`): `python3 scripts/vidya/loop_beliefs.py prepare --consumer cc-pilot --target-json '<target>' --ledger <pilot copy> --as-of <ts>` lists the pilot claims under "Usable, target tier", with tags `Judged/Located · verified · retrofit`; a sibling-lineage claim lands under the sibling tier; a device-only claim lands under host; an unscoped row appears in none and is counted in the ingest report |
| AC7 | **No run supersession** | no pilot row lands in `omitted` with reason `superseded_run` |
| AC8 | **Epoch fencing** | pilot rows with `epoch` older than the target's current epoch render under "Older epochs", not ahead of live AK rows |
| AC9 | **Budget** | the target tier still shows live AK/AutoPilot rows; the pilot does not displace the newest serving floor (`_forced`, `loop_beliefs.py:1173-1176`) |

**Run AC6-AC9 against a copy of the ledger** (`--ledger <copy>`), never the canonical ledger,
until AC1-AC5 pass. Then the ledger owner ingests the pilot for real.

---

## 6. Governance files that change, and their paths

### 6.1 Classification (`coordination/session-bus/human_only_paths.yaml`, enforced by `scripts/hooks/check_trust_boundary_edit.sh`)

| file | class | basis |
|---|---|---|
| `agents/commands/wrap-up.md` (`.claude/commands/wrap-up.md` is a symlink to it) | agent edit, **main applies** | not in the human-only globs |
| `agents/shared/SESSION_LIFECYCLE.md` | **operator-ratify** | matches the `agents/shared/*.md` glob |
| `CLAUDE.md` | **operator-ratify** | listed explicitly |
| `scripts/vidya/adapters/README.md` | agent edit, main applies | not listed |
| `handoffs/active/vidya-belief-substrate-program.md` | agent edit, main applies | not listed |
| `scripts/handoffs/index_state.py`, `scripts/vidya/citation_gate.py` | code, main applies (Codex per memory "coding → Codex") | not listed |
| `docs/design/vidya-pilot-spec.md` | not hook-listed, but its §19 decisions are "operator-ratified 2026-08-09" (spec header, line 3) | **no edit proposed**; the design fits §4.5/§4.7 as written |
| `agents/shared/MEASUREMENT_POLICY.md`, `MEASUREMENT.md` | **human-amendment-only** (INVARIANTS.md:38; MEASUREMENT_POLICY.md:174-175) | **no edit needed or proposed** |

For the operator-ratify files: per MEMORY "human-only paths need ratify script" and
OPERATING_CONSTRAINTS.md:426-432, the change is packaged as one ratify script that the operator
runs. An agent never edits these files through Write/Edit.

### 6.2-6.5 Diffs

(§7.4 carries the exact text for wrap-up.md, SESSION_LIFECYCLE.md and CLAUDE.md. §4.1 and §4.2
carry the README and handoff diffs.)

---

## 7. SYSTEMATIC CAPTURE

Today nothing forces a concluded experiment into the ledger:

- CLAUDE.md "Belief Kernel — wiring new sources" (`CLAUDE.md:145-168`) asks only that the wiring
  task be surfaced.
- Wrap-up 5b (`wrap-up.md:512-517`) checks only ledger lag against the intake index.
- The checklist-sync and flip-count gates (`wrap-up.md:326-348`) count ticks only.

Measured baseline: **0 of 690** ticks added on 10-20..10-24 carry a greppable belief reference
(`clm_`, `frm_`, `src_`, `evd_` = 0; the 78 lines mentioning ledger, vidya or belief are about the
belief system itself) (`work/a2/`).

### 7.1 (a) The tick contract

**Rule.** A `- [x]` line **added on the lane** that records an experimental or measurement result
must carry exactly one of these inline forms on the same line:

| form | meaning | verified by |
|---|---|---|
| `[belief: clm_<id>]` (one or more, comma-separated) | a native adapter projected this run; cite its claim | cite-check resolves the id in the folded ledger (§4.4) |
| `[belief: cc]` | no native adapter; this line is the committed conclusion; ingest it via the register | the same commit range adds a register row whose quote equals this line under `cc-norm/v1` |
| `[no-belief: <reason>]` | a result tick that deliberately has no belief; reason non-empty, at most 120 chars | presence only; the reason is reported |

Recommended reason vocabulary (free text is allowed; these keep reports groupable):
`not-a-result`, `build/landing`, `operator-action`, `tooling-repair`,
`native-pending:<VB-task>`, `duplicate-of:<claim-id>`, `smoke-only`.

The marker goes on the **checkbox line** (the item's first line). The detector reads the whole
**item**: the checkbox line plus the continuation lines added or changed with it. The Class-A
study (§3.5) found that the verdict usually sits in a continuation line.

**What counts as a "result tick"** (mechanical; the patterns in `work/a2/det.py`, detector C,
applied to the item text). A tick is a result tick when its checkbox line is an added `[x]` line in
the merge-base diff of `handoffs/` and **any** of these hold:

- **R1, result artifact cited:** `VERDICT\.json|RUN_RECORD\.json|ANALYSIS\.json|summary\.json|records?\.jsonl|results?\.jsonl|cells\.jsonl|RESULTS?\.(md|json)`
- **R2, strong verdict token** (case-sensitive, word-bounded):
  `KEEP|NULL|NO-GO|PASS(ED)?|FAIL(ED|S)?|REGRESS\w*|REFUTED|RETRACT\w*|INCONCLUSIVE|VERDICT|CONFIRMED|BENIGN|DROPPED|DOES NOT REPLICATE|(bit|token)-identical`
- **R3, a measure verb plus a number with a unit**, after stripping dates, SHAs, `:123` line refs,
  `vN`, `10303`, `intake-N` and task IDs. Measure verbs:
  `measure[ds]?|measurement|probe|census|replay|A/B|re-?run|bench|sweep`. Numbers:
  `\d(?:[.,]\d+)?\s?(t/s|tok/s|%|ms\b|pp\b|GiB|MiB|ppl\b|x\b)|\bp\s?[=<]\s?[\d.]|\bn\s?=\s?\d|±|Δ|pass@\d|\b\d+/\d+\b`

Exclusion: R2 and R3 (not R1) are suppressed on lines matching
`\b(wired|landed|committed|moved to completed|documentation-only|design only|spec only|proposal only)\b`
or on a spec-title tick `^\s*[-*] \[x\] \*\*[A-Z0-9.-]+ — (wire|land|add|build|implement|...)`.

**Precision on the last two weeks of ticks on origin/main.** P = 0.64 and R = 0.56 on 96
hand-labelled ticks (25 positives). These were measured on the checkbox line's first 500
characters. Item-level scoring should raise recall: the Class-A v2 item score reached P 0.80 /
R 0.59, and v1 reached R 0.85 at P 0.62. This is in-sample, the intervals are wide, and a held-out sample
is required before enforcement (§7.2 staging). It would flag about 120 of 690 ticks (17%), about 24
per active day fleet-wide. **A false positive costs one `[no-belief: not-a-result]` clause.**
Low-FP was the goal. At P ≈ 0.64 the cost is about 9 needless declines per day fleet-wide. The
real loss is recall: 44% of result ticks are bare `✅ <date>` lines. To close that, the
**SESSION_LIFECYCLE text below makes the contract normative for every result tick, detected or
not**. The detector is the enforcement net, not the definition.

### 7.2 (b) The wrap-up belief-capture gate

Placed right after the flip-count gate (`agents/commands/wrap-up.md:332-348`), with the same
scoping. Proposed helper: `scripts/handoffs/belief_capture_check.py` (new, about 120 lines,
stdlib). Exact command:

```bash
# From inside YOUR lane worktree; same scoping as the flip-count gate.
python3 scripts/handoffs/belief_capture_check.py \
  --range "$(git merge-base main HEAD)..HEAD" --include-worktree --report
```

Behaviour:

- **Inputs.** Added `[x]` lines in `git diff <range> -- handoffs/`, plus `git diff HEAD --
  handoffs/` when `--include-worktree` is given. These are the same two halves the flip-count gate
  sums.
- **Classification.** Each added tick is either a result tick (R1/R2/R3) or not. Each result tick
  is then `cited` (`[belief: clm_...]`), `cc` (`[belief: cc]`, plus a register row added in the
  same range with a matching quote), `declined` (`[no-belief: ...]`) or **`missing`**.
- **Output** (one line, like the derived-actionables count):
  `belief-capture: result_ticks=<N> cited=<a> cc=<b> declined=<c> missing=<d> (advisory_bare_ticks=<e>)`.
  It then lists each `missing` tick as `path:line  <first 120 chars>`.
  `advisory_bare_ticks` counts added ticks whose text is only `✅ <date>` or `**ID**` plus a date,
  with no R-match. This is the invisible-miss bucket, reported and not failing.
- **Exit codes.** 0 when `missing == 0`; 1 otherwise; 2 on a usage error or when run in the shared
  clone (it calls `check_lane_worktree.py --strict` as the flip-count gate text requires).
- **No ledger write, no ingest.** The `cited` form is resolved by cite-check, not by this script.

**Proposed wrap-up.md text** (diff in §7.4.1).

**Should `index_state.py --check` enforce it?** Yes, but staged:

- **Week 1-2: advisory.** Add a `belief_capture_warnings()` call beside
  `graph_freshness_warnings` (`index_state.py:950`). It prints the same line and does not affect
  the exit code. Measure FP and FN on a fresh held-out sample of ticks from those weeks.
- **After that: error, only for ticks added after an effective date.** The check reads the
  merge-base diff, so historical ticks are never in scope. It needs `--check` to know the lane
  merge-base. `citation_check` already runs git (`:1053-1124`), so the cost is small.
- Rationale: `--check` "must exit 0 before committing" (CLAUDE.md, Handoff Workflow), so it is the
  only gate that fires on every commit, including sessions that never wrap up. Making it an error
  before FP is measured would block commits on a 0.64-precision regex.

### 7.3 (c) The producer path

```
result tick written
 ├─ the run has a native adapter (README source table row, ingest name in ingest_sources.py)
 │    → producer emits its native sidecar → `cli.py ingest <name> --only-new` (event path)
 │    → the tick cites   [belief: clm_<id>]   (id printed by the ingest report)
 │      until the native ingest has run: [no-belief: native-pending:<VB-task>]   (reported, not missing)
 └─ no native adapter (or the run's write side never fired)
      → the tick carries   [belief: cc]
      → the same commit adds a register row via
           python3 scripts/vidya/cli.py conclusion add --path handoffs/active/<f>.md --line <checkbox line> \
             --scope-json '{...}' --category CANDIDATE --direction higher_better
        (writes the row with the item extent, quote and quote_sha256; commit_introduced and
         commit_concluded are resolved at ingest from origin/main via `git log --reverse -S`
         (never blame, §2.2), so the row needs no pre-commit SHA)
      → when the commit reaches main: hook_sync.sh (extended, VB-CC-3) folds the register
        → `ingest committed-conclusion --only-new`, keyed by cc_id = H(basename, quote_norm);
        idempotent: a re-run, a line move, an active→completed move or an ARTIFACT LOST suffix
        mints nothing new.
```

Notes:

- The `[belief: cc]` marker is excluded from `quote_norm` (`cc-norm/v1`), so adding it does not
  change identity.
- `cli.py conclusion add` is a **register writer**, not a ledger writer. Single-writer on the ledger
  is preserved.
- A native-adapter tick that cites `native-pending` for two consecutive wrap-ups has hit the "Act,
  Don't Defer" recurrence check (CLAUDE.md). Run the ingest, or switch to `[belief: cc]`.

### 7.4 (d) Governance diffs (prepared; apply none)

#### 7.4.1 `agents/commands/wrap-up.md` (main applies)

```diff
@@ -5 +5 @@  (line 5 is one long CADENCE line; only this phrase inside it changes)
-... Every wrap-up, and every checkpoint commit, is bound by the **checklist-sync gate** in Step 2: ...
+... Every wrap-up, and every checkpoint commit, is bound by the **checklist-sync gate** and the **belief-capture gate** in Step 2: ...
@@ -22 +22 @@
-| 2. Handoff updates · checklist-sync gate · derived-actionables gate | ✅ | |
+| 2. Handoff updates · checklist-sync gate · belief-capture gate · derived-actionables gate | ✅ | |
@@ -348,0 +349,22 @@ trustworthy** — move to your lane before believing its number.
+
+**Belief-capture gate (required — the flip-count gate counts ticks, not what they concluded).**
+A ticked box that records an experimental or measurement result is invisible to the AutoKernel and
+AutoPilot planners unless it reaches the belief ledger. Every result tick added on this lane carries
+exactly one of: `[belief: clm_<id>]` (a native adapter projected the run; cite its claim),
+`[belief: cc]` (no native adapter; add the register row with `cli.py conclusion add` in the same
+commit), or `[no-belief: <reason>]`. Then run, from inside YOUR lane worktree:
+
+```bash
+python3 scripts/handoffs/belief_capture_check.py \
+  --range "$(git merge-base main HEAD)..HEAD" --include-worktree --report
+```
+
+It prints `belief-capture: result_ticks=N cited=a cc=b declined=c missing=d (advisory_bare_ticks=e)`
+and lists each missing tick. Exit 1 = at least one result tick has neither a reference nor a
+decline: fix the line, do not explain it away. A false positive costs one
+`[no-belief: not-a-result]`. `advisory_bare_ticks` are ticks with no stated outcome on the line:
+if the outcome lives in a prose block below, put the verdict on the tick line and cite it.
+Report the line in the wrap-up output. Same shared-clone caveat as the flip-count gate. This gate
+never ingests: ingest stays event-driven (Step 5b).
```

#### 7.4.2 `agents/shared/SESSION_LIFECYCLE.md`, *Two axioms* (OPERATOR-RATIFY path)

```diff
@@ -35,0 +36,9 @@ receipt, or bus-publication phases.
+- **A result tick names its belief.** A box ticked on an experimental or measurement result
+  carries `[belief: clm_<id>]`, `[belief: cc]` or `[no-belief: <reason>]` on the same line, and
+  states its verdict or number on that line, not only in a prose block below. The dashboard counts
+  the tick; the planners read only the ledger, so a result that never reaches it did not happen
+  for them. A committed conclusion is recorded as an OBSERVATION (`Judged/Located`) with its
+  commit, path and line: recording what was concluded is legitimate, while inventing the lost
+  run's protocol, n or attestation is not. Enforced by the wrap-up belief-capture gate
+  (`agents/commands/wrap-up.md`, Step 2).
```

#### 7.4.3 `CLAUDE.md`, *Belief Kernel — wiring new sources* (OPERATOR-RATIFY path)

```diff
@@ -151,4 +151,9 @@
 Wiring the **write** side is cheap and permanent; retrofitting the **read** side is impossible — a
 tuple invented on read claims warrant the original run never captured. `benchmarks/results` is the
 standing proof: 4,562 files, no write-side hook, 0 of 200 sampled carry a usable claim tuple, so
 they can never gate a decision.
+
+That forbids inventing a run's **measurement** warrant. It does not forbid recording what was
+**concluded**: a conclusion committed to a handoff or progress report enters as an OBSERVATION
+(`Judged/Located`) with its commit, path and line, through the committed-conclusion register. A
+result tick carries `[belief: clm_<id>]`, `[belief: cc]` or `[no-belief: <reason>]` (wrap-up
+belief-capture gate; `agents/shared/SESSION_LIFECYCLE.md` → *Two axioms*).
```

#### 7.4.4 README row and vidya handoff: §4.1 and §4.2

### 7.5 Worked example: workspace-58 ticks of 2026-10-24

Sources: `work/a2/` (`git log -S` SHAs, approximate; `d70dcc768` is a bulk-tick commit) and ledger
`grep -c -F` on the run-dir basename (substring counts, read-only).

| tick | path:line (origin/main) | detector | cites | native adapter | ledger | contract would have required |
|---|---|---|---|---|---|---|
| M4.2 | `gpu-serving-tie-in-program.md:470` | flagged | `m4-srpf-pbhol/` VERDICT.json, RUN_RECORD.json | `pb_hol.py`. The README row says `ingest pb-hol` DECLINES the phase-suffixed dirs | 0 | `[belief: clm_<pb-hol id>]` once `pb_hol` reads the phase dirs; until then `[belief: cc]` + register row (scope Q38FN / gpu / gfx90a) |
| M4.2b | same file `:481` | flagged | `m4-2b-champion-control/VERDICT.json` | `pb_hol.py` | 0 | same as M4.2 |
| M4.2a | same file `:475` | **missed** (bare `✅ 2026-10-24`) | none | `pb_hol.py` | — | the verdict moved onto the tick line + `[belief: ...]`; it shows in `advisory_bare_ticks` |
| KPF-17.4c | `kv-prefix-fork-and-paged-attention.md:444` | missed | `kpf17-4c-bisect/VERDICT.json` (R1 would catch it once the path is on the line) | `kv_prefix_fork.py` covers only part of the 17.x rows | 0 | `[belief: cc]` (a bisect verdict has no carrier) |
| KPF-18.0b | same file `:483` | flagged (B/C) | `overnight-20261020/kpf18-run/` | `kv_prefix_fork.py` | 0 for that dir | `[belief: clm_<kpf id>]` after `ingest` on that run dir |
| KPF-18.0d item 3 | same file `:505` (10-20 tick); v2 at `:538` | flagged; v2 missed | `kpf18-run-w1c/records/kpf18-20261020T231530Z-1.json` | `kv_prefix_fork.py` | **360** (10-20 run did reach the ledger) | 10-20 tick: `[belief: clm_<id>]`, citing the existing frames. v2: `[belief: clm_<id>]` if its records were ingested, else `[belief: cc]` |
| KPF-18-S1.R4 | same file `:583` | flagged | `kpf18-s1-r4/` RUN_RECORD.json, VERDICT.json | `kv_prefix_fork.py` | 0 | `[belief: clm_<id>]` after ingest; until then `[no-belief: native-pending:VB-KPF-...]` |
| AKX-ALL-26b | `autokernel-all-devices-all-dimensions.md:424` | flagged | PASS @1 thread, F@2 @24 threads; no path | `autokernel_width_cells_cpu.py`; the README AKX-ALL-26 row has "HIP half to follow" | 20 for `akx-all-26` | `[belief: clm_<id>]` if 26b wrote `cells.jsonl`; else `[belief: cc]` (scope cpu / epyc-9655, op-level) |
| PB-QCOST-1 confirm | `gpu-serving-tie-in-program.md:413` | flagged | the 21:29Z run | `pb_qcost.py` | 71 for `pb-qcost`, mostly earlier runs | `[belief: clm_<id>]` for the 21:29Z run after `ingest pb-qcost` |
| PB-QCOST-1 confirm-R | same file `:435` | missed on line 1 | `pb-qcost-1-confirm-r/` VERDICT.json, RUN_RECORD.json | `pb_qcost.py` | 0 | `[belief: clm_<id>]` after ingest of the new run dir |
| SEC-ART-POST-b | `model-artifact-integrity.md:57` | not flagged | TEMPLATE_REVIEW_DIGEST.md, ratify script | none | 0 | not a result tick; nothing required (optionally `[no-belief: operator-action]`) |
| NIB2-GNX-1 | `non-inference-backlog.md:969` | not flagged | `nib2-gnx1-reindex/RESULT.json` (R1 matches `RESULTS?\.(md\|json)` once the path is on the line) | README row exists; no adapter module | 0 | `[no-belief: tooling-repair]` |
| GPU-ZOS-2.1 | `gpu-serving-tie-in-program.md:360` | not flagged | code build | none | 0 | not a result tick (`[no-belief: build/landing]` optional) |
| P1-PHASE2-SERVED-SHAPE-RECAL | (ingested) | — | — | `autokernel_served_shape.py` | ingested | `[belief: clm_<served-shape id>]`: the only one that would have passed unchanged, once the id was cited |

The worked example shows two things. **Ten of the thirteen** ticks have a native adapter (KPF-17.4c
only partly), and for most of them the ingest simply never ran for that run directory. **The contract's main yield is forcing the native
ingest**, not the committed-conclusion fallback. The `native-pending` decline plus the recurrence
check is what makes that visible. KPF-18.0d item 3 (10-20) shows that "no ledger frame" was not
uniformly true: the frames existed, but nothing linked the tick to them.

---

## 8. What genuinely needs a decision

1. **Scope the "retrospective yields zero tuples" handoff rulings** (VB-AK-DS41-OPS `:1199-1200`,
   VB-KVU-1 `:1927-1928`) so they read "no *measurement* tuples from retrospective raw records".
   **Owner: main, in the vidya handoff (§4.2 preamble).** The operator has already given the
   reading, so this is applying a stated decision, not asking for one.
2. **Ratify the two operator-ratify texts** (SESSION_LIFECYCLE.md §7.4.2, CLAUDE.md §7.4.3) as one
   ratify script (MEMORY "ratifications: ONE command"). The rest of this design does not wait on it.
   The register, adapter, extractor, pilot and the wrap-up gate are all agent or main paths.

Nothing else blocks. No new ladder, no new class, no MEASUREMENT.md or MEASUREMENT_POLICY.md edit
and no spec amendment are needed.

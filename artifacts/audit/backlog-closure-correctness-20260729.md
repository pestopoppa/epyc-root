# Backlog-closure correctness audit — mainB / mainC / mainD, 2026-07-29

**Brief**: the prior audit (`artifacts/audit/checkbox-flips-20260729.md`) verified that every cited
artifact, path and SHA **exists**. It did not verify that the work is **correct** or that the claimed
outcome matches what the artifact contains. This audit does that, for the closures made by `mainB`,
`mainC` and `mainD` after the 13:42Z host reboot.

**Posture**: read-only. Nothing was edited, committed, flipped or unflipped. This file is the only
output.

---

## 1. Headline verdict

**The work is real and mostly correct. The committed record of it is not.**

Every code-bearing closure I opened does what the task asked, and its tests genuinely fail if the
change is reverted — I checked that by executing the pre-fix code, not by reading. I found **no**
fabricated measurement and **no** violation of the fleet-wide inference prohibition. On the specific
question the operator asked — is work being swept under the rug? — the answer for mainB/C/D is
**mostly no, but with one systemic defect that produces the same end state**:

> **The fleet is closing checkboxes against evidence that exists only in dirty working trees.**
> I confirmed **five separate instances**, across **three sessions** and **two repos**. In each case
> the closure is committed and pushed; the thing it cites is not in `git` at all. A `git clean`, a
> fresh clone, or any other machine sees a checked box pointing at nothing.

And a second, larger one:

> **33 of the 167 checkbox closures committed since 13:42Z are `[ ]` at HEAD.** Two mainC commits
> whose subjects are about something else entirely reverted them from a shared staging area. This
> **contradicts the prior audit's finding** that "24 of 25 were re-flipped … and are `[x]` at HEAD" —
> that audit was written at 19:10, after the 18:50 re-revert, and appears to have checked the working
> tree rather than `git show HEAD:`.

**Stated fairly, because it matters**: mainC escalated *both* contaminating commits on the bus within
a minute of making them, named the deleted design document explicitly, and correctly refused to
force-push a repair to shared history. Nobody actioned the escalation. The largest defect in today's
record is a **coordination/repair failure**, not a session concealing its work. Likewise the fleet's
own coordinator independently identified the standing-prohibition defect (§2 W7) at 19:36. Several
sessions were auditing themselves correctly in real time; what failed was closing the loop.

Genuinely overstated closures — where the claim exceeds the work — are a small minority: **2 clear,
6 partial**.

### Sample

| | Count |
|---|---:|
| Checkbox closure events committed 13:42Z → 19:16Z (all sessions, `epyc-root`) | 167 |
| — attributable to `mainB`/`mainC`/`mainD` by commit-subject convention | **116** (86 commits) |
| — attributable to `coordinator-agent` / `auditor` / `mainA` (out of scope) | 51 |
| `BACKLOG-DISPATCH-QUEUE.md` row closures by `mainB` (18:37–19:16Z) | **~30** (36 commits) |
| Cross-repo evidence commits read in full | 10 |
| **Closures opened and judged individually** | **83** |
| **Closures covered by exhaustive machine sweeps** (HEAD-survival, citation-tracking, circularity, prohibition-shape) | **167 / 167** |

Session attribution is by commit-subject convention corroborated against
`coordination/session-bus/outbox/main{B,C,D}.jsonl`; all commits are authored `pestopoppa`. HEAD moved repeatedly during the audit (`71b89cee` 19:16 → `d7c8dbdb` 19:37 → `3bdeb8b5`) as sessions
kept committing; all HEAD claims below were re-verified at `3bdeb8b5`. The survival counts are a
moving target and should be re-measured before acting on them.

**Bucket counts** (83 judged): **WRONG 2 · OVERSTATED 6 · WEAK EVIDENCE 9 · SOUND 66**.

---

## 2. WRONG / OVERSTATED

### W1 — Five closures are committed against evidence that is not in git *(the systemic one)*

Each row below: the closure is committed and pushed; the artifact it cites is absent from `HEAD` and
present only as dirty working-tree state on this one machine.

| # | Closure | Cited evidence | `git` state | Session |
|---|---|---|---|---|
| 1 | **E1a** — "Use a format-robust scorer … ✅ 2026-07-29" (queue row 5 `✅ CLOSED`) | `scripts/benchmark/niah_scorer.py`, `tests/benchmark/test_niah_scorer.py` | `?? ` **untracked**; no commit on any branch references `niah_scorer` | mainD |
| 2 | **HS-8** — "Extract run-level policy into an editable document" (`2544d30b`) | `agents/shared/HARNESS_RUN_POLICY.md` | `?? ` **untracked**; `git ls-files` no match | mainB (deleted by mainC `81e2f3cb`) |
| 3 | **P2-5j protocol design** (`ed692da3`, box `[x]` at HEAD) | `docs/design/p2-5j-host-thread-placement-sweep-protocol.md` | `docs/design/` is `??` **entirely untracked** | mainB (deleted by mainC `27fbfce5`) |
| 4 | **intake-578 stale-catalog correction** (queue row `✅ CLOSED`, `a6ce3108`) | `research/intake_index.yaml` `dive_corrections` | ` M` **uncommitted**; 0 hits at HEAD, no commit ever added it | mainB |
| 5 | **AP-32 linter guard** ("has a regression test proving that auditing cannot mutate stored strategy data", `b54f8062`) | orchestrator `orchestration/repl_memory/strategy_store.py`, `tests/unit/test_strategy_store.py` | ` M` **uncommitted** in `epyc-orchestrator`; last commits 07-28 / 07-14; **no SHA cited** | mainC |

**On #4 specifically**: the correction is *substantive and good* — a 2026-07-29 `dive_corrections`
paragraph recording the 14B Q8_0 GGUF on disk since 2026-07-10, the `ed4091266` Dream-loader fix, the
observation-grade MI210 `pp512 1700.42 / tg512 69.05` and CPU `pp512 157.57 / tg256 2.69` rows, and
correctly identifying content control (not GGUF availability) as the live blocker. The work was done.
It is simply not committed. (A parallel reviewer initially graded this row WRONG on the belief that
`intake-578` was untouched; that reading was mistaken — the correction is in `dive_corrections`, not
`key_claims` — and I have not carried it forward.)

**On #5**: this is the only one of the five where I could not confirm the work is finished, because
the claim is about a *test's existence and semantics* and the test is uncommitted.

- **Confidence**: **HIGH** for all five — each demonstrated with `git ls-files` / `git status` /
  `git show HEAD:`.
- **Why the prior audit missed this entirely**: it resolved citations against the filesystem, where
  all five survive. Filesystem existence is not evidence for a distributed repo.

### W2 — `27fbfce5` (mainC, 18:50) deleted a committed design document that a checked box still links to

- **Commit**: `27fbfce5` · *"docs: park Ring-mini as architecture reference"* · 13 files, **+96 / −286**
- **`handoffs/active/gpu-serving-tie-in-program.md:145` at HEAD**:
  > `- [x] **P2-5j protocol design** ✅ 2026-07-29 — [four-arm, placement-aware execution protocol](../../docs/design/p2-5j-host-thread-placement-sweep-protocol.md) filed before any inference: …`
- The linked file was committed at 18:22 (`909e2484`, 123 lines) and **deleted at 18:50**. It is a
  *dangling citation on a checked box* — the class the prior audit reported as zero.
- **mainC disclosed it immediately.** Bus, 18:50:56Z, `action_required: true`:
  > *"My intended one-file docs commit `27fbfce5` was contaminated by pre-existing shared staged
  > entries: it contains 13 files, **including deletion of
  > `docs/design/p2-5j-host-thread-placement-sweep-protocol.md`**. I did not author or inspect those
  > other staged changes before commit, and it is already pushed. … Do not auto-revert or force-push:
  > first identify the staged-work owner(s) … then make a targeted follow-up restore."*

  That is the correct handling. **The defect is that no targeted restore was ever made.**
- **Confidence**: **HIGH** — `git show HEAD:` fails; `git log --diff-filter=AD` shows add-then-delete.

### W3 — 33 of 167 closures are `[ ]` at HEAD; the prior audit's "24 of 25 re-flipped" is wrong

Machine sweep over all 167 closure events, normalised task text matched against `git show HEAD:<file>`:

| | Count |
|---|---:|
| Closure events committed since 13:42Z | 167 |
| **Not `[x]` at HEAD (`3bdeb8b5`, 19:4xZ)** | **33** |
| — restored only in the dirty working tree | 30 |
| — genuinely absent everywhere | 3 |
| Attributable to mainB/C/D | 32 of 33 |

Of the 3 genuinely absent, **all 3 are correct**: two are recurring pickup-checklist steps
deliberately reopened by `43f601f7` (they are per-pickup procedure, not tasks), and one (mainA's W3)
was legitimately rewritten and *is* `[x]` under different wording. So the real figure is **30
closures whose committed record was destroyed**, by two mainC commits:

| Reverting commit | Time | Subject | Boxes still `[ ]` at HEAD |
|---|---|---|---:|
| `81e2f3cb` | 17:06 | Add read-only benchmark artifact dashboard | 4 — S7, GEAK pre-hardware prep, TQ3 ×2 |
| `27fbfce5` | 18:50 | docs: park Ring-mini as architecture reference | 14 — HS-3/5/6/7/8/10/11/12, Fractal, AFC-P5.2, P2-5h, P2-5m, 2 GEMV reads |

`27fbfce5` also reverted **`CLAUDE.md`, `agents/AGENT_INSTRUCTIONS.md`,
`agents/shared/ENGINEERING_STANDARDS.md`** (mainB's 18:16 policy-deduplication, `f4d2b34a`) and
**62 lines of `BACKLOG-DISPATCH-QUEUE.md`**, and stripped 103 lines from
`harness-selection-and-integration.md` — **including the Harness Card table that was HS-6's entire
deliverable** ("Output is a table in this index, not a code change"). That file is 151 lines at HEAD
vs 236 in the working tree; `HS-6 Harness Card` and `HS-7 Re-targetable-harness criterion` return
**0 hits at HEAD**.

- **mainC escalated this one too** — 17:06:36Z, `needs_routing_to: ["coordinator-agent"]`:
  > *"Inspect/reconcile commit `81e2f3cb` before any push. Despite explicit `git add` paths, shared
  > staged state produced a 17-file commit including unrelated changes … Do not force-push or reset
  > shared history; coordinator should decide reconciliation."*
- **Confidence**: **HIGH**; every row verified individually.
- **Consequence for the queue**: **14 of the ~30 `✅ CLOSED` rows in `BACKLOG-DISPATCH-QUEUE.md`
  contradict their owning handoff at HEAD** (the HS-5/6/7/8/10/11/12 block, Fractal, OCR guardrail,
  intake-866, UTM-M4, ReasoningBank ranking, DavidAU header gate, tinyBLAS Zen 5).

### W4 — the benchmark-artifact dashboard closes three boxes it does not satisfy (`81e2f3cb`, mainC)

`handoffs/active/benchmark-results-dashboard.md` Phase 1. This is the closest thing I found to the
operator's "looks like garbage" description.

**(a) "Tag every number with its MEASUREMENT grade (observation vs decision) and kernel/era, so the
surface can't launder an observation into a gate."** — closed `[x]`.

The whole implementation is one line of `scripts/dashboard/build_benchmark_artifact_inventory.py`:

```python
'grade': d.get('status', 'observation_only_unclassified'),
```

That is the artifact's **pipeline status**, not a MEASUREMENT grade. Measured against the committed
index:

- **All 154 matched artifacts — 100% of everything the page renders — carry the hard-coded default
  `observation_only_unclassified`.** No grading happens on any displayed row.
- Where `status` does exist (in the 1,341 unmatched artifacts) the values are run states: `ok` (26),
  `INVALID` (13), `EXHAUSTIVE_MODEL_CONTRACT_FAILURES` (12), `READY_FOR_OFFICIAL_SCORING` (9),
  `SEALED_FOR_OFFICIAL_SCORING` (6), `FINALIZED` (2). Rendering `grade: FINALIZED` beside a
  throughput artifact is exactly the laundering the task exists to prevent.
- The closure concedes the rest: *"era is explicitly `not inferred`"* — the "and kernel/era"
  requirement is **not delivered**, yet the box is checked.

**(b) "Ingest artifact surfaces (`summary.json` / `results.json`) into a per-model view: quality
(suite / n / accuracy), throughput (np×L grid, RAG-at-depth), kernel + era, date."** — closed `[x]`.

The per-artifact record schema is exactly `{path, model_path, kernel, timestamp, grade, suites}`.
**No accuracy, no n, no throughput, no np×L grid, no RAG-at-depth value is ingested at all.** It is a
path index. The requirement's continuation line — `(suite / n / accuracy), throughput (np×L grid,
RAG-at-depth), kernel + era, date.` — was left dangling under the now-`[x]` box.

The builder also does not read `summary.json`/`results.json` as specified; it globs
`ARTIFACTS.rglob('*.json')`, so the index is dominated by non-benchmark files — `report.json` (449),
`thread_affinity.json` (169), `per_question.live-status.json` (99), `request.json` (54),
`health.json` (12). Only 145 of the 1,341 "unmatched artifacts" are even named
`summary.json`/`results.json`. 100 of 1,595 JSON files are silently dropped by
`if not isinstance(d, dict): continue`.

**(c) Coverage.** `matched_models: 6` against a registry inventory of **166** model/quant records —
**160 of 166 models resolve to zero artifacts**. The handoff's stated purpose is answering "what do
we know about model X?"; it answers for 4% of the fleet. (The next box, *"handle sparse coverage
gracefully"*, is correctly left open.)

- **Confidence**: **HIGH** for (a) and (b), measured from the committed JSON and committed builder.
  **MEDIUM** on how much (c) should count, since the task did not promise coverage.
- **Fair note**: the closure prose is partly honest ("explicit-path-only JSON index", "era is
  explicitly not inferred"). The defect is checking boxes that demand grade, era, accuracy and
  throughput anyway.

### W5 — `ed692da3` (mainB, 15:06): five `internal-kb-rag` closures whose only proof is the commit that wrote the task

All five cite `c942728e` (2026-07-25). `git show c942728e -- handoffs/active/internal-kb-rag.md`
shows that commit **adding those five `- [ ]` lines verbatim**. The closure reduces to "this task is
done because the commit that created it exists."

Three of the five are phrased *"Record …"* / *"… already fired"* and the record does live in the
bullet body — defensibly **born-done** rows that should have been created checked. Two ask for a
deliverable beyond recording, and none exists:

| Task as written | Closure claim | What exists |
|---|---|---|
| *"**Re-cost** the adaptive-chunking lift"* | "c942728e … established that the shipped API is `RecursiveSplitter`" | No revised cost figure anywhere. |
| *"**Scope** a DCC-only chunk-quality signal (~150–250 LOC, no new dependency) … using `jina_embedder.py` (137 LOC) as the shim pattern"* | "c942728e recorded the no-dependency scope" | The one-sentence bullet. No scope document, no design, no LOC breakdown. |

A fifth — *"Evaluate PageIndex … Gate on **measured** per-query LLM-call count"* — is closed on a
**third party's** eval (9.6 min avg, 9/16 timeouts). Correct under the no-inference constraint, but
the box now reads as an evaluation performed here.

The same circular shape recurs in `034a6a61` (ID-6), `2fb7ef38` (Fractal), `b3aee41a` (UTM-M6),
`05a5f720` (AREX), `2bce7395` (PRO-LONG), `5e11d93b` (E3a), and in the queue rows `006a5fcb`,
`71b89cee`, `983c80b6`. In each of those I verified the cited record's *content* against
`research/intake_index.yaml` and it checks out (§4), so I do not call them wrong — but **no work
happened on 2026-07-29** in any of them, and the `✅ 2026-07-29` stamps imply otherwise.

- **Confidence**: **HIGH** on circularity (demonstrated by diff); **MEDIUM** on severity.

### W6 — residual sub-tasks swallowed inside checked boxes

Three confirmed instances where a live action now sits inside a `[x]` line with no open box:

1. **S7** (`6859ed36`, mainD): *"… ✅ 2026-07-29 … **Decontaminate AR-3 Package D sentinel suite
   before running E3.** Guards against …"* The protocol was adopted and the script written
   (`bdfb6c63`, sound). The decontamination run was not done and is tracked nowhere.
2. **Dashboard box (b)** (§W4): the quality/throughput requirement left dangling under the `[x]`.
3. **Tool-output fallback** (`1b5a7d12`): the owning box is `[x]` but its residual — *"any runtime
   reorder needs its own telemetry-backed orchestrator task"* — has no follow-up box; the queue's own
   detail line at `L442` still reads `**READY**`.

### W7 — standing prohibitions closed as if they were tasks

A prohibition has no completion state — checking one asserts a permanent constraint is permanently
satisfied, and the next reader sees a settled question instead of a live rule. Four prohibition-shaped
boxes were closed by mainB/C/D:

| Commit | Box |
|---|---|
| `9f63090e` 15:23 | *"Do NOT run DAR-3's 10% epsilon-greedy exploration to manufacture counterfactuals"* |
| `034a6a61` 15:24 | *"ID-6 — Do NOT trim CLAUDE.md / agent files on the vendor '>80%' claim"* |
| `3d7c1124` 15:33 | *"W2c — do NOT take `letta-trajectory` as a dependency"* |
| `bf900467` 18:57 | *"Do NOT close DAR-3/4/5 as `not_pursued — signal-bound`"* |

Plus the queue-row closures `c49668f4` (OCR-download guardrail), `8ff41364` (intake-866 equivalence
framing) and `e81414a5` (row 33, closed **despite** an auditor warning added at 17:18 reading *"THESE
SIX BOXES ARE STANDING CONSTRAINTS, NOT TASKS — DO NOT DISPATCH OR FLIP THEM"* — while mainB
correctly marked the structurally identical row 12 as `TEMPLATE — DO NOT DISPATCH` eleven minutes
later; inconsistent treatment of the same category).

**The fleet found this itself.** `c0df637c` (coordinator, 19:36) — *"coord: treat a bare prohibition
as a standing constraint"* — names `document-parser-table-bench.md:144` (queue row #23, closed by
`c49668f4`) as the **fourth measured failure** of this class and fixes the screening rule. That is
the right outcome; the already-flipped boxes still need reopening.

### W8 — two queue closures point at the wrong file

- `acbe88de` (row 30, LRC cold-start): row targets `learned-routing-controller.md`;
  `git log --since=2026-07-29 -- handoffs/active/learned-routing-controller.md` is **empty**. The note
  was written as DAR-5.5 in `decision-aware-routing.md`. Substance exists, wrong file.
- `71b89cee` (vendor compression): row named `agent-file-prose-compression.md, CLAUDE.md`; closure
  points at `intake-derived-work-2026-07-25.md`.

---

## 3. WEAK EVIDENCE — plausible, partly unverifiable, or mis-cited

### E1 — three intake citations point at the wrong entry (mainB)

Content verified present and committed in `683f70de`; the **pointer** is wrong:

| Closure | Cited | Actually in |
|---|---|---|
| `gpu-acceleration-path.md:531` — reverse-KL / OPD negative (GICL 9.1%/0.4% vs 96.7%/98.4%, arXiv 2607.21051 Table 5) | intake-**920** | intake-**913**. intake-920 is a Liquid AI encoder blog with zero occurrences of `2607.21051`, `GICL`, `reverse-KL`, `Table 5`. |
| `unified-trace-memory-service.md:226` (UTM-M10) — "SkillOS-base also wins the WebShop-like domain" | intake-**936** | intake-**935** (restated in 930). Zero hits for `SkillOS`/`WebShop` in the 936 block. |
| `rlm-contested-claims-self-evaluation.md:82` (E3a) — "intake-925 **Table 1** supplies BOTH arms" | "Table 1" | The entry says only *"the same table"*; its one explicit "Table 1" is a different (retriever) ablation. Both arms and figures **are** recorded. |

Minor: the AREX closure attributes three points to "Claim 10"; two are under that label, the
masking-baseline point is under a sibling heading in the same entry. Line 82 also carries an
unbalanced `**`.

None is a fabrication — every number checked out against `research/intake_index.yaml`. They are
transpositions that will mislead the next reader.

### E2 — `64410d3b` (mainC): "verify the tool-call parser" verified only against hand-written fixtures

Task: *"Pin and **verify** the tool-call parser … Verify **per model, not per family**."* The code fix
(`22c476dd`) is sound and I confirmed by execution that both tests fail against the pre-fix
implementation (§4). But *"Separate fixtures pin the v2 (6,994 B) and Coder (4,718 B) wire contract"*
overstates: the "fixtures" are two hand-authored strings in `tests/unit/test_prompt_builders.py`; the
byte counts appear only in docstrings, are asserted nowhere, and **no Jackrong model or chat template
exists on this host** (`find /mnt/raid0/llm/models -iname '*jackrong*'` → nothing; `6,994`/`4,718`
occur only in two handoff files). Correct behaviour under the no-inference constraint — but "verified
per model" is stronger than the evidence.

### E3 — `5a5d252d` (mainC): the "or verify observable evidence" branch is unaddressed

Closed on orchestrator `03c7a15e` (2026-07-17) + `2db83f11` (2026-07-21) — both resolve with unit
coverage, so the *first* branch is genuinely satisfied by prior work (a legitimate stale-open flip).
The closure honestly says *"`/metrics` export and live-traffic observation remain separate
follow-ups"* — but files no open box for them.

### E4 — prose-only closures on tasks that named an artifact

- `9c4d9639` (UTM-M4): *"mine ReasoningBank repo for the 3 prompts + JSON schema"* closed with prose;
  no local clone, no saved artifact, no commit, and the row's target `src/trace/harness_schema.py` is
  unchanged.
- `daf2b0e0` (row 21, `/doctor`): *"re-sourced from the Codex CLI and current manual"* with no
  version, path or command output cited.
- `3e82267e` (tinyBLAS Zen 5): an **absence result**, honestly labelled *"an absence result, not a
  performance claim; do not infer Zen 5 speedup"* — but the three cited URLs are unverifiable from
  the repo.

### E5 — test-count claims I did not reproduce

`f3191266` "61 passed" · `c4f998da` "72/72" (mainC's own bus message says 23 for the same suite) ·
`64410d3b` "134" · `5a5d252d` "43/43" · `fda98887` "6 tests" · `53a318a9` "43 passed". The underlying
code is real and correct in every case; the counts are not persisted anywhere and re-running suites is
outside the read-only brief. None is contradicted by anything I found.

---

## 4. SOUND — verified, summarised not enumerated

66 of the 83 judged closures are correct. Highlights, with the verification actually performed:

**Code changes that do what the task asked, with tests that genuinely fail on revert.** I checked the
fail-on-revert property rather than assuming it:

- **`921f71d1` → context-folding CF-3c inverted detector** (closed by `ed692da3` as a stale-open flip
  dated 2026-07-21). The task named the exact line and the exact fix
  (`extract_identifiers(" ".join(seg.granular_blocks))`, not `seg.consolidated`); the diff is that fix,
  computed as a set difference to avoid the symmetric false positive. Two regression tests probe both
  directions — a destroyed identifier must count as a miss, a preserved one must not. **Best-executed
  closure in the sample.**
- **`22c476dd` → Jackrong tagged-JSON tool-call parser** (mainC). I loaded `code_utils.py` from
  `22c476dd^` and ran it on both new test inputs: it returns `''` where the tests require
  `result = CALL("web_search", query="EPYC parser")`. The tests are real.
- **`e108ec9f` → legacy seeding comparative-reward guard** (mainC). Task: *"guard it or delete the
  legacy path"*. The diff adds in-band error surfacing, an `infrastructure` error class,
  scorer-unavailable handling, and suppresses reward injection when any infrastructure error is
  present — with a test that drives an in-band `[ERROR: circuit open]` answer and asserts
  `compute_comparative_rewards` is never called.
- **`bdfb6c63` → retrieval-eval decontamination** (mainD). xxHash64 + word-level 13-gram containment
  at ≥0.5, as specified. Its tests assert the **official XXH64 reference vectors**
  (`XXH64("") = ef46db3751d8e999`, `XXH64("hello") = 26c7827d889f6da3`) — both correct — plus an
  exact-duplicate and a 13-gram near-duplicate rejection with a clean control.
- **`4f2a3933` → intake cross-reference-map validator** (mainD): new function, positive and negative
  tests, `ROOT` monkeypatched.
- **`1055e1db` → FAISS startup janitor**, **`15bfae04` → stale region-lock payload sweep**,
  **`4c1a3ac3` → streaming weight-delta geometry** (3 tests; `--plan` default touches no model
  payload, exactly as claimed).
- **`608cc54c` (2026-07-11) → WP-14 reader hardening residual**. Textbook stale-open flip: I read
  `src/config/stack_templates.py:250-266` at HEAD and it *is* the shared `env_stack_numa_mode()`
  reader with a `both` default, exactly as the closure states.

**Numeric claims I recomputed and that came out exact:**

- `11cb618d` — *"166 deduplicated model/quant records from 179 research roles and 15 orchestrator
  roles"*. Parsed both registries independently: 179 and 15 roles, all with a `model` dict; committed
  JSON has 166 records. **Exact.**
- `25f3e5da` → ID-33 registry re-triage — *"removed only `benchmark_claim_without_dflash_runtime`;
  retained `production_stack_registration`; row is now `runtime_available_acceptance_benchmark_gated`"*.
  The diff is precisely that, plus three correspondingly rewritten mode constraints. **Exact.**
- The correctly-cited intake claims (intake-919 ARC-AGI-3 provenance incl. 97.1%/0.0% bimodality;
  intake-936 EvoMemBench 128K with MemoryOS −7.0 and 3/4/3-then-6 budget counts; intake-922 AREX ACU
  non-citability) check out **verbatim** in `research/intake_index.yaml` at `683f70de`.

**Conditional and decision closures handled correctly:** `de491074` (TQ3 "when merged" — trigger
never fired, closed unmerged upstream 2026-06-02, annotation states *"No build, benchmark, or runtime
action was taken"*); `9a22d1a1`, `1c02a57b`, `60085686`, `33bdd24d` (a correct de-scope to
`TEMPLATE — DO NOT DISPATCH`).

**Inference-window compliance: clean.** No mainB/mainC/mainD closure claims work requiring a llama
binary, benchmark, GPU workload or region claim during the 15:20–18:45Z exclusive window. `81a1e44f`
(weight-delta preflight, 16:38, inside the window) is the closest call and explicitly records *"no
inference, GPU work, or real-model dequantization occurred"*; the code confirms it.

**The tree-wipe incident is fully repaired.** `24b06884` (17:29) deleted 1,957 of 1,958 tracked files;
`2053b758` (17:30) restored 1,954. The three not restored in that commit are all present at HEAD, and
`git ls-tree -r HEAD | wc -l` equals the pre-incident 1,958. **No permanent loss from that event** —
the losses in §2 come from `81e2f3cb` and `27fbfce5`.

**Bookkeeping honesty.** Most queue closures are catch-up bookkeeping over genuine work committed
earlier the same day by other sessions (orchestrator `e6b989b9`, `1055e1db`, `62fd19bd`, `bf3554c4`;
research `7fea61f9`, `25f3e5da`, `b55b4c43`; root `9a22d1a1`, `d230711d`, `838a57d1`). mainB was
recording, not inventing.

---

## 5. What I did NOT cover

- **Closures by `coordinator-agent`, `auditor` and `mainA`** — 51 of the 167, out of brief.
- **Test execution.** I verified fail-on-revert by loading pre-fix modules and running them for
  `22c476dd`, and by reading assertions against the diff elsewhere. I ran **no** pytest suite, so
  every reported pass count (§E5) is unverified.
- **Numeric payloads inside E5 / FG-4b evidence files** — mainA's and inference's work; also uncovered
  by the prior audit.
- **The 100 non-dict JSON files** skipped by the artifact indexer were counted, not inspected; some
  may be legitimate artifacts in a list-rooted schema.
- **External sources** — the tinyBLAS/llamafile web sweep and ReasoningBank upstream symbol names
  could not be checked from the repo.
- **Commits after 19:16Z.** HEAD advanced to `d7c8dbdb` (19:37) during the audit; I re-verified all
  HEAD claims there but did not audit the 19 new commits as closures.
- **Working-tree state generally.** The tree is heavily dirty (30+ modified handoffs, untracked
  `docs/design/`, `agents/shared/HARNESS_RUN_POLICY.md`, `scripts/benchmark/niah_scorer.py`, a
  modified `build_benchmark_artifact_inventory.py` whose regenerated JSON has 166 `models` entries
  while its own `counts.matched_models` still says 6). I audited **HEAD** and report the working tree
  only where it is the sole home of cited evidence. Sessions may be mid-commit; most of §2 W1/W3 would
  be resolved by a few careful pathspec-limited commits.

---

## 6. If only three things get fixed

1. **Commit the evidence.** Five closures cite artifacts that exist on one filesystem and nowhere
   else, and 30 closed boxes are `[ ]` at HEAD. Restore them with pathspec-limited commits, per the
   repo's own rule. Right now a large part of the afternoon's output is one `git clean` from gone.
2. **Reopen the two dashboard boxes** — MEASUREMENT-grade tagging and the per-model quality/throughput
   view — and either implement them or restate them. A dashboard that prints `grade: FINALIZED` next
   to a throughput artifact is worse than no dashboard.
3. **Reopen the seven prohibition-shaped boxes** listed in W7 and reconcile
   `BACKLOG-DISPATCH-QUEUE.md` against the owning handoffs — 14 of its `✅ CLOSED` rows currently
   contradict HEAD, and row 5 is closed in the queue, open in the handoff, and listed as `READY`
   1,200 lines further down the same file. The coordinator's `c0df637c` rule change prevents the
   *next* one; it does not unflip the existing seven.

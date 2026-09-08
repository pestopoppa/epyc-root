# Wiki compilation sweep — READ-ONLY assessment (INF-70, 2026-09-08)

Worktree: `/mnt/raid0/llm/worktrees/audits/inf70-audit-20260902`
Mode: **assessment + drafting guidance only**. Nothing under `wiki/` was created or modified,
no lease was taken, no `--touch` was run, no compilation was performed.

---

## Step 1 — Scanner run (read-only)

### Command and result

```
cd /mnt/raid0/llm/worktrees/audits/inf70-audit-20260902
/workspace/repos/epyc-orchestrator/.venv/bin/python .claude/skills/project-wiki/scripts/compile_sources.py
```

Interpreter `/workspace/repos/epyc-orchestrator/.venv/bin/python` exists and worked — exit **0**.
(`/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python` also exists; not needed.)

**`total_new` = 11** — `by_type`: `handoff-active` 8, `progress` 2, `docs` 1.
**`drift`**: `added_count` 2, `changed_count` 9, `removed_count` 1 (`has_drift: true`).

Other manifest fields:

| field | value |
|---|---|
| `mode` | `incremental` |
| `last_compile` (reported) | `2026-09-07T14:04:28Z` |
| `scan_time` | `2026-09-08T16:21:14Z` |
| `baseline_manifest` | `wiki/source_manifest.json` |
| `baseline_source_set_hash` | `3875854734c70fb3c9f35467432b6b6d1a05bb95e9aa70bb995bae847322dce6` |
| `current_source_set_hash` | `e845747a5b79134bee5a52876bcc717b20684a616b98f0918f8ddee0d725b9db` |
| `source_set_hash` (of the 11 selected) | `a335668d9d05ea57953cabaf5d9b95cacda186cc77ac59e2142e0b5e401a759d` |
| `writer_evidence_policy` | present, `policy_version: 1`, matches the required block exactly |
| `removed_sources` | 1 — `progress/2026-08/2026-08-25.md` |

### Read-only confirmation

There is **no `--dry-run` flag**; the plain invocation *is* the read-only default. The script only
writes under `--touch` (`refresh_tracked_manifest` + `touch_last_compile`) or `--write-manifest`.
Verified empirically:

- `git status --porcelain wiki/` **BEFORE**: 0 lines (empty).
- `git status --porcelain wiki/` **AFTER**: 0 lines (empty).
- `diff` of the two captures: identical → **nothing written**.
- `wiki/.last_compile` mtime unchanged at `Sep 7 14:04` (would have been rewritten by `--touch`).

### Two caveats on the scanner output — read these before acting on the numbers

1. **The stderr warning is a false alarm here, but do not delete it.** The run printed:
   `WARNING: running from a linked git worktree — every file carries the checkout mtime, so the
   incremental (mtime) basis is INVALID and total_new is inflated.` That warning is emitted
   unconditionally whenever `ROOT/.git` is a file. The **default incremental path does not use
   mtimes** — `incremental_since_tracked_manifest()` diffs path + SHA-256 `content_hash` against
   the tracked `wiki/source_manifest.json`, exactly as SKILL.md Operation 3 Step 1 describes. So
   **`total_new = 11` is valid from this worktree** and would be identical from the canonical
   clone. The warning text is stale relative to the code it guards.
2. **The reported `last_compile` is 19 h stale.** The output says `2026-09-07T14:04:28Z`, read from
   the **gitignored** `wiki/.last_compile`; the **tracked** `wiki/source_manifest.json` carries
   `last_compile: 2026-09-08T09:28:51Z`. `get_last_compile_iso()` prefers the untracked file when
   it is non-empty, so a lane with a stale `.last_compile` reports a watermark ~19 h behind the
   real one. **Selection is unaffected** (it is content-hash based), but the displayed watermark
   should not be quoted as the compile date.

### The 11 new sources, with taxonomy category assignment

Categories are canonical keys from `wiki/SCHEMA.md`. `A` = added (path absent from the tracked
manifest), `C` = changed (content hash differs).

| # | Δ | type | path | primary category | secondary |
|---|---|---|---|---|---|
| 1 | C | handoff-active | `handoffs/active/autokernel-unified-surface-program.md` | `hardware_optimization` | `benchmark_methodology` (per-surface floors carry their conditions; LOO/re-baseline receipts), `agent_architecture` (resource broker, one-monitoring-session) |
| 2 | C | handoff-active | `handoffs/active/batched-decode-measurement.md` | `hardware_optimization` | `inference_serving`, `benchmark_methodology` |
| 3 | C | handoff-active | `handoffs/active/cpu-decode-roofline-program.md` | `hardware_optimization` | `benchmark_methodology` (champion/floor/harness), `quantization` (Q4_K gating) |
| 4 | C | handoff-active | `handoffs/active/cpu-fused-decoder-blocks.md` | `hardware_optimization` | — |
| 5 | C | handoff-active | `handoffs/active/cpu-prefill-compute-large-models.md` | `hardware_optimization` | `inference_serving` |
| 6 | C | handoff-active | `handoffs/active/cpu-shape-specialized-gemv-decode.md` | `hardware_optimization` | `quantization` |
| 7 | C | handoff-active | `handoffs/active/numa-placement-defect-20260730.md` | `hardware_optimization` | `inference_serving` |
| 8 | C | handoff-active | `handoffs/active/wrap-up-division-of-labor-policy.md` | `agent_architecture` | `knowledge_management` |
| 9 | C | progress | `progress/2026-09/2026-09-08-ak-rebuild-20260828.md` | `hardware_optimization` | `agent_architecture`, `autonomous_research` |
| 10 | **A** | progress | `progress/2026-09/2026-09-08-inf70-audit.md` | `hardware_optimization` | `benchmark_methodology` (STAT-1 pseudo-replication, DRIFT-5, the floor-conditions rule) |
| 11 | **A** | docs | `docs/design/champion-consolidation-audit-20260908.md` | `hardware_optimization` | `tool_implementation` / `agent_architecture` (git custody, the `--branches` backup lesson) |

Removed (carried for review, does **not** count toward `total_new`):
`progress/2026-08/2026-08-25.md` (`progress`).

Clustering by SKILL.md Step 3 (3+ substantive sources → full article):
**`hardware_optimization` = 10 sources** (full article), **`benchmark_methodology` = 5 secondary**
(full article), **`agent_architecture` = 3** (full article). Everything else is 1–2 → stub-level.

---

## Step 2 — SKILL.md Operation 3 (Compile): the required page format

Source: `.claude/skills/project-wiki/SKILL.md` lines 128–273.

### The template, quoted verbatim (Step 4, "Synthesize Wiki Pages", lines 210–242)

For each category cluster, create or update `wiki/<category-key>.md`:

````markdown
# <Category Label>

**Category**: `<key>` from wiki/SCHEMA.md
**Confidence**: <verified|inferred|external>
**Last compiled**: YYYY-MM-DD
**Sources**: N documents

## Summary

<2-4 paragraph synthesis across all sources in this category>

## Key Findings

- <finding with [source citation](../path/to/source.md)>
- <finding referencing [intake-NNN] paper title>

## Open Questions

- <unresolved question from handoffs or research>

## Related Categories

- [Related Category](related-category.md) — <relationship>

## Source References

- [deep-dive title](../research/deep-dives/file.md) — <what it contributed>
- [handoff title](../handoffs/active/file.md) — <relevant finding>
- [intake-NNN] paper title — <key claim, credibility score>
````

Verbatim rules attached to it:

- "Filename convention: `wiki/<category-key>.md` (e.g., `wiki/speculative-decoding.md`)"
- "If a wiki page already exists for that category, merge new findings and update the 'Last
  compiled' date. **Never delete existing content without cause.**"
- "Before committing generated pages, run project-wiki lint and make sure the manifest's
  `writer_evidence_policy` still passes `--check-manifest`."

### Front-matter

Four bold key/value lines immediately under the single H1, in this order and no other:
`**Category**` (backticked schema key), `**Confidence**` (one of `verified` | `inferred` |
`external`), `**Last compiled**` (`YYYY-MM-DD`), `**Sources**` (`N documents`).
No YAML front matter — the "front-matter" is these four markdown lines.

### Section structure

Canonical order: `## Summary` → `## Key Findings` → `## Open Questions` →
`## Related Categories` → `## Source References`.

The **lint contract** (Operation 1, pass 6 "Wiki article structure", lines 75–79) is narrower than
the template and is what actually gates a commit:

> For pages with `**Category**` metadata, require **one H1**, `## Summary`, and **a source-reference
> section**. Warn on missing recommended article sections or legacy/reference pages without
> category metadata.

So: one H1, `## Summary`, and a source-reference section are **hard**; the rest are recommended.

### Citation format for sources

- Inline, in Key Findings: `[source citation](../path/to/source.md)` — a repo-relative link that
  climbs out of `wiki/` with `../`.
- Papers: `[intake-NNN]` plus the title. Note the root `CLAUDE.md` citation-precision rule —
  `intake-896` inherits every defect of every claim in the entry, `intake-896#03` cites one claim,
  `intake-896#record` *discusses* the record and asserts nothing; prose *about* an entry is itself
  a citation and needs `#record`. Gate with
  `python3 scripts/vidya/cli.py cite-check --as-of <ts>`.
- In `## Source References`: `- [title](../path/file.md) — <what it contributed>`, one line each.
- Compilation Principles (lines 266–273): synthesize don't copy; **every claim traces to a source
  via the Source References section**; cross-reference related pages; confidence `verified` for
  tested/measured, `inferred` for analysis, `external` for third-party; incremental on content
  hashes never mtimes; preserve existing, merge in place.

### The adoption gate (lines 160–170) — binding on this draft

The manifest's `writer_evidence_policy` is the **minimum adoption contract** for model-written
article updates: `minimum_confidence: verified`, **at least 3 source references**, a
source-reference section, structural lint, and human-or-measured review before adoption. It is
present and intact in this scan.

### ⚠ The template is NOT what these two pages actually look like

`wiki/hardware-optimization.md` and `wiki/benchmark-methodology.md` are long-lived pages that
carry the template's front matter and its five canonical H2s **somewhere in the middle of the
file**, surrounded by dozens of **dated update sections**. The de-facto in-tree convention for a
new compile pass is:

```markdown
## Compiled Update — YYYY-MM-DD: <a sentence-length claim, not a topic label>

**Confidence: verified** — <what grade applies to what>

### <H3 per finding, each a claim sentence>

<prose, bold on the load-bearing numbers>

### Source References (YYYY-MM-DD, <topic>)

- [`file.md`](../handoffs/active/file.md) — <what it contributed>
```

Plus a per-section `### Source References (<date>, <topic>)` rather than only the page-level one,
and a `**Last compiled**:` front-matter line that accretes a parenthetical digest of every pass.
**Follow the in-tree convention; it satisfies the lint contract and the SKILL template's hard
requirements.** Supersession is expressed in place with the page's own idioms —
`> **⚠ SUPERSEDED YYYY-MM-DD — ...**` (e.g. `hardware-optimization.md:323`), `~~strikethrough~~`
plus `**RETRACTED**` (`:1038`, `:1047`), or `*(Corrected YYYY-MM-DD: ...)*` (`:1107`) — never by
deletion.

### Insertion point differs per page (measured, not assumed)

- **`wiki/hardware-optimization.md` — PREPEND.** Its two newest sections are
  `## Compiled Update — 2026-09-08: AutoKernel becomes the unified CPU+GPU surface` (line 8) and
  `## Compiled Update — 2026-09-08: INF-70 audit outcomes` (line 43), both at the top.
- **`wiki/benchmark-methodology.md` — APPEND.** Every INF-70 landing since 2026-09-03 sits at the
  tail; the newest section on the page is
  `## Compiled Update — 2026-09-08: the three-valued conversion is a contract first` at **line
  4476**, the last H2 in the file. Append after it.

---

## Step 3 — Existing wiki inventory

32 files, **33,077 lines** total.

| lines | file |
|---:|---|
| 4637 | `wiki/hardware-optimization.md` |
| 4581 | `wiki/benchmark-methodology.md` |
| 3620 | `wiki/agent-architecture.md` |
| 2407 | `wiki/autonomous-research.md` |
| 2397 | `wiki/knowledge-management.md` |
| 1930 | `wiki/speculative-decoding.md` |
| 1899 | `wiki/inference-serving.md` |
| 1011 | `wiki/search-retrieval.md` |
| 936 | `wiki/routing-intelligence.md` |
| 817 | `wiki/kv-cache.md` |
| 786 | `wiki/tool-implementation.md` |
| 755 | `wiki/multimodal.md` |
| 747 | `wiki/memory-augmented.md` |
| 649 | `wiki/ssm-hybrid.md` |
| 645 | `wiki/context-management.md` |
| 643 | `wiki/quantization.md` |
| 553 | `wiki/moe-optimization.md` |
| 531 | `wiki/chat-templates.md` |
| 529 | `wiki/cost-aware-routing.md` |
| 492 | `wiki/formal-verification.md` |
| 461 | `wiki/document-processing.md` |
| 341 | `wiki/local-inference.md` |
| 323 | `wiki/INDEX.md` |
| 297 | `wiki/training-distillation.md` |
| 239 | `wiki/llm-prompting.md` |
| 187 | `wiki/SCHEMA.md` |
| 180 | `wiki/reinforcement-learning.md` |
| 134 | `wiki/context-extension.md` |
| 106 | `wiki/rag-alternatives.md` |
| 89 | `wiki/reasoning-compression.md` |
| 87 | `wiki/safety.md` |
| 68 | `wiki/mechanistic-interpretability.md` |

### `wiki/hardware-optimization.md` — the sections a draft must extend, not duplicate

Front matter: `**Category**: hardware_optimization` · `**Confidence**: verified (established
CPU/NUMA findings) · observation (all 2026-07 GPU throughput numbers…)` ·
`**Last compiled**: 2026-09-08 (…)` · `**Sources**: 110+ documents`.

Top block (newest-first):

```
   8  ## Compiled Update — 2026-09-08: AutoKernel becomes the unified CPU+GPU surface …
  43  ## Compiled Update — 2026-09-08: INF-70 audit outcomes — the champion was understated …
        49  ### The champion multiplier was understated — and the corrected magnitude is provisional
            ### Four upstream defects verified still present on current upstream (UP-1/UP-2)
            ### PROD-1 — the canonical serving recipe is now DATA, not prose
            ### INF-71 (EXL3 trellis on the CPU kernel) — NO-GO, operator-confirmed
            ### MEAS-1/MEAS-2 — the contention decision, and the build-lock convention
            ### Source References (2026-09-08, INF-70 audit)
  74  ## Compiled Update — 2026-09-08: the rtx6kpro intake …
  95  ## Compiled Update — 2026-09-07: a capability probe that asks the wrong runtime can only answer NO
 121  ## Compiled Update — 2026-08-16: the 64-VGPR boundary …
 …
1103  ## Summary            1117  ## Key Findings          1289  ## Open Questions
1306  ## Related Categories 1315  ## Source References
```

INF-70 tail block (the CPU-decode campaign's own sections):

```
4201  ## Compiled Update — 2026-09-02: the INF-70 implementation wave …
4279  ## Compiled Update — 2026-09-03: INF-70 wave 2 …
4328  ## Compiled Update — 2026-09-03 (INF-70 wave 3) …
4393  ## Compiled Update — 2026-09-04 (INF-70 batch-envelope) …
4412  ## A byte roofline over-prices anything that fits in L3 (2026-09-05)
4438  ## Where CPU decode time actually goes: 23.4% is coordination (2026-09-05)
4472  ## Profile OCCUPANCY, not overhead — the instrument decides what you can find (2026-09-05)
4520  ## THP raises NUMA interleave granularity to 2 MiB (2026-09-06)
4564  ## The champion kernel: 1.4834× from two levers, and what the other two taught us (2026-09-06)
4612  ## Compiled Update — 2026-09-07 (wrap-up): SMT siblings make core-range fencing impossible;
      the build is the contention   [last section in file]
        4614  ### SMT sibling topology makes CPU core-range "fencing" … structurally impossible …
```

### `wiki/benchmark-methodology.md` — the sections a draft must extend, not duplicate

Front matter: `**Category**: benchmark_methodology` · `**Confidence**: inferred` ·
`**Last compiled**: 2026-09-08 (…)` · `**Sources**: 131+ documents`.

Relevant existing owners (H2 line numbers):

```
 115  ## Compiled Update — 2026-09-04: a bench win is not a serving win …
        167  ### The A/A serving floor is usable only via compound-then-gate
 188  ## Compiled Update — 2026-08-30: a noise floor estimated from subsets of ONE sample cannot
      exceed that sample's own tail …
        196  ### The noise floor was understated by construction
2806  ## Four more ways a check passes for the wrong reason (2026-08-12)
2929  ## Compiled Update — 2026-08-21: the vacuous-pass campaign closed — and the guard needed
      five repairs of its own
2970  ## Compiled Update — 2026-08-21: a gate that runs and passes can still be passed by
      weakening the computation under test
3390  ## Two ways an A/B screen reports a win that does not exist (2026-08-28)
3622  ## Compiled Update — 2026-08-31 (evening): … floors that travel without their model …
3658  ## Compiled Update — 2026-09-02: retracting a number is not done until you chase what was
      derived from it
3773  ## Compiled Update — 2026-09-07 (incremental): name the unit, control the instrument,
      place the caveat — three ratified measurement amendments (`fb755192`)
4230  ## Host drift: the ~5% evidence floor for cross-window comparisons (2026-09-04)
4264  ## A knob that is not in the binary returns a null that looks like evidence (2026-09-05)
4293  ## Measure the stack, not the parts — levers do not compose predictably (2026-09-07)
4409  ## Compiled Update — 2026-09-07: absence read as a negative verdict, found three times in
      one afternoon, three independent subsystems
4476  ## Compiled Update — 2026-09-08: the three-valued conversion is a contract first …  [last]
```

Canonical five: `1586 ## Summary` · `1614 ## Key Findings` · `1823 ## Open Questions` ·
`1846 ## Related Categories` · `1855 ## Source References`.

---

## Step 4 — Ownership map for the five INF-70 findings

**Blocking precondition, stated first.** None of the five findings' numbers exists in **any tracked
source** in this repo. Greps for `5.081`, `0.609`, `0.501`, `2.793`, `1200-fold`, "floors must carry",
"between-launch", "between-session" over `handoffs/`, `progress/`, `docs/` and `wiki/` return **zero
hits**; `/mnt/raid0/llm/tmp/inf70/wrapup-20260908/` holds only `checkboxes.txt`, `headings.txt`,
`settled_markers.txt`. `progress/2026-09/2026-09-08-inf70-audit.md` (source #10) carries HARNESS-1's
0.80% p95 floor and STAT-1, but not (a)/(b)/(c)/(e)'s figures.

The `writer_evidence_policy` demands `minimum_confidence: verified` and **≥3 source references**, and
Compilation Principle 2 requires every claim to trace to a source. **So the order of operations is:
land (a)–(e) in a tracked source first** — the natural home is `progress/2026-09/2026-09-08-inf70-audit.md`
(already in the scan set as an ADD) plus the relevant handoff rows in
`handoffs/active/cpu-decode-roofline-program.md` — **then compile**. Compiling first would produce
citations to documents that do not exist.

### (a) Variance/precision — env knob: between-launch sd 5.081% → 0.609% (8.3× sd, ~70× variance); ±0.5% precision ~25 h → ~23 min

- **Target page**: `wiki/benchmark-methodology.md` (primary). The claim is about **what the
  instrument can resolve**, and every floor/precision result on this project lives on this page —
  `### The A/A serving floor…` (:167), `### The noise floor was understated by construction` (:196),
  `## Host drift: the ~5% evidence floor…` (:4230).
- **Target section**: **NEW H2**, appended after line 4476, e.g.
  `## Compiled Update — 2026-09-08 (INF-70): an environment knob, not more repetitions, bought the
  precision — 8.3× sd for zero extra arms`, with the figure as an H3 under it.
- **NEW section.** No existing section can absorb it: `## Host drift` (:4230) is dated 2026-09-04 and
  is about *cross-window* drift, a different axis, and back-dating an 8.3× result into it would
  misdate the evidence.
- **Also add** (in-place, one line each, not new sections): a forward pointer in
  `## Host drift…` (:4230) — the ~5% cross-window floor is the number this knob attacks; and a
  cross-ref on `wiki/hardware-optimization.md` in the top 2026-09-08 block, since the knob itself is
  a hardware/env lever. **Coordinate with the HARNESS-1 0.80% floor already recorded in
  `progress/2026-09/2026-09-08-inf70-audit.md`** — that entry warns the 0.80% figure is valid only
  with the GPU loop down; the same conditions clause must travel with 0.609% or the compiled number
  repeats the exact defect the page spent 2026-09-07 filing against.

### (b) Methodology rule — "floors must carry their unit": within-session sd 0.501% vs between-session sd 2.793%; wrong unit → 1200-fold sample-size error

- **Target page**: `wiki/benchmark-methodology.md`.
- **Target section**: **EXTENDS** an existing, precisely-matching owner —
  `## Compiled Update — 2026-09-07 (incremental): name the unit, control the instrument, place the
  caveat — three ratified measurement amendments (fb755192)` at **line 3773**. That section *is* the
  ratified "name the unit" doctrine; this is its next instance.
- **Mechanics**: because sections on these pages are dated records, do not silently add a 2026-09-08
  H3 under a 2026-09-07 heading. Put the finding as an H3 in the **new 2026-09-08 H2** from (a), and
  add a single in-place pointer line inside :3773 (`**Extended 2026-09-08:** the unit is the LAUNCH,
  not the round — see <link>`). That is the page's own idiom for post-dated extensions.
- **Secondary extends** (pointer lines only): `## Compiled Update — 2026-08-31 (evening): … floors
  that travel without their model …` (:3622) — same family, "a floor without its model"; and
  `wiki/hardware-optimization.md` **U2** in the top 2026-09-08 block (:8ff), which already states
  "per-surface floors carry their measurement conditions (harness, n, contention model, host-state
  hash), not just a number" — (b) is the measured cost of violating U2 and should cite it.

### (c) Pattern — four "vacuous instrument" incidents in one day (gate passing on zero cases; screen watching the wrong resource; `ps -p` false negatives for process death; a gate computing over arms its own screen rejected)

- **Target page**: `wiki/benchmark-methodology.md` (primary).
- **Target section**: **NEW H3** inside the same new 2026-09-08 H2, explicitly framed as the next
  instalment of a *named, recurring* family rather than a fresh discovery. The family already has
  four sections on this page:
  `## Four more ways a check passes for the wrong reason (2026-08-12)` (:2806),
  `## Compiled Update — 2026-08-21: the vacuous-pass campaign closed…` (:2929),
  `## Two ways an A/B screen reports a win that does not exist (2026-08-28)` (:3390), and the
  nearest-shaped one, `## Compiled Update — 2026-09-07: absence read as a negative verdict, found
  three times in one afternoon, three independent subsystems` (:4409) — **the same shape, one day
  earlier**. Cite :4409 and :2806 explicitly; the value of (c) is that the family recurred a fifth
  time, not that the four incidents are novel.
- **NEW section (as an H3), EXTENDING a named family.** Two routing notes:
  - the fourth incident ("a gate computing over arms its own screen rejected") is the same class as
    **STAT-1** in `progress/2026-09/2026-09-08-inf70-audit.md` — cite it, don't re-derive it;
  - the third ("`ps -p` false negatives for process death") is a **process-management** defect, not a
    benchmark one. Add a one-line cross-ref to `wiki/tool-implementation.md` (:448 already carries
    the daemon-liveness-predicate family) and/or `wiki/agent-architecture.md` (:1105). Root
    `CLAUDE.md` already mandates "after killing a process, verify it is dead (`ps -p <pid>`)" — if
    `ps -p` is producing false negatives, that guidance is affected and the finding must say so.

### (d) Cross-campaign contention — pinning controls placement not contention; SMT siblings share a physical core; the channel was DRAM bandwidth, not cores, invisible to any CPU-occupancy screen

- **Target page**: `wiki/hardware-optimization.md`.
- **Target section**: **EXTENDS** `## Compiled Update — 2026-09-07 (wrap-up): SMT siblings make
  core-range fencing impossible; the build is the contention` at **line 4612** — its single H3
  `### SMT sibling topology makes CPU core-range "fencing" between concurrent workloads structurally
  impossible…` (:4614) already owns the sibling-topology half.
- **EXTENDS, and partially CORRECTS.** The new part is the *channel*: :4614 prescribes "a live
  process sample (`cc1plus`@100%, matched against `cpus_allowed`)" as the instrument that catches the
  build contention — and (d) says a DRAM-bandwidth channel is **invisible to exactly that
  occupancy-based screen**. So this is not an additive paragraph; it bounds the remedy the existing
  section recommends. Use the page's in-place idiom: an
  `> **⚠ EXTENDED / PARTIALLY CORRECTED 2026-09-08 — …**` block under :4612 plus a new H3.
- **Second-order supersession to flag, not bury**: `hardware-optimization.md:43` (the 2026-09-08
  INF-70 audit section) states the MEAS-1 discriminator as "the **PEAK**, not the total foreign load
  — what hurts is a burst of 3218% (~32 cores…)". That is an **occupancy** read. If the channel is
  DRAM bandwidth, that discriminator is at best a proxy. Add an explicit cross-reference between the
  two, and do not let the new section contradict :43 silently.
- **Third pointer**: `wiki/inference-serving.md:622` carries the "host threads pin to SMT siblings
  184-191 → physical cores 88-95" note — one-line cross-ref, no new section there.

### (e) Supersession — an older headline ratio replaced by new measured ratios

- **Target page**: `wiki/hardware-optimization.md`.
- **Target sections**: **EXTENDS two, in two different ways.**
  1. `## The champion kernel: 1.4834× from two levers, and what the other two taught us (2026-09-06)`
     at **line 4564** — this is where the superseded headline physically lives: `1.4834×` (:4564,
     :4567), plain `1.6934×` and prefill `1.305×` (:4569). Apply an in-place
     `> **⚠ SUPERSEDED 2026-09-08 — …**` banner naming the replacing ratios, per the page's own
     idiom at :323 / :1038 / :1047. **Do not delete** — SKILL.md: "Never delete existing content
     without cause."
  2. `## Compiled Update — 2026-09-08: INF-70 audit outcomes` (:43), H3
     `### The champion multiplier was understated — and the corrected magnitude is provisional`
     (:49) — already carries `1.4993× → 1.5149× vs pristine` and the "**magnitude is provisional**"
     qualifier. The new measured ratios belong **here as an H3 extension**, replacing "provisional"
     with the measured values if the quiet-window re-measurement is what produced them.
- **Blast radius of the superseded numbers — chase every derived figure before editing.**
  `benchmark-methodology.md:3658` (`## Compiled Update — 2026-09-02: retracting a number is not done
  until you chase what was derived from it`) is the governing rule. Measured occurrences:

  | figure | occurrences |
  |---|---|
  | `1.4834×` | `hardware-optimization.md:4564`, `:4567` |
  | `1.6934×` | `hardware-optimization.md:4569`, `:4590`; **`benchmark-methodology.md:4308`** (the super-additivity 12.8%-excess derivation) |
  | `1.305×` prefill | `hardware-optimization.md:4569` |
  | `1.4993×` | `hardware-optimization.md:49` |
  | `23.16 t/s` / `1.876×` | `hardware-optimization.md:57`; `benchmark-methodology.md:4233`, `:4242`, `:4243` |

  Note `benchmark-methodology.md:4308` re-uses `1.6934` inside the **super-additivity** finding —
  if the plain ratio moves, the "12.8% excess" arithmetic moves with it. That is a
  cross-page derived figure and is the one most likely to be missed.
  Note also `hardware-optimization.md:57` already records that
  "**`23.16 t/s` / `1.876×` is a build-10221 number, not a champion-3 number — it must not be quoted
  as the champion figure**"; if (e) is about *that* ratio, the supersession is already half-recorded
  and the draft should extend :57 rather than restate it.
- **Also required on any (e) edit**: update `**Last compiled**` in the front matter (:5), which is
  the page's accreting digest and currently names `1.5149×` as the corrected magnitude.

### Summary table

| # | target page | target section (line) | verdict |
|---|---|---|---|
| a | `wiki/benchmark-methodology.md` | **NEW** `## Compiled Update — 2026-09-08 (INF-70): …precision…`, appended after :4476 | **NEW** (pointer lines into `## Host drift` :4230 and `hardware-optimization.md` top block) |
| b | `wiki/benchmark-methodology.md` | `## Compiled Update — 2026-09-07 (incremental): name the unit…` (:3773) | **EXTENDS** (H3 in the new (a) H2 + in-place pointer at :3773; secondary pointers :3622 and `hardware-optimization.md` U2 :8) |
| c | `wiki/benchmark-methodology.md` | **NEW H3** in the (a) H2, citing the family at :4409 / :2806 / :2929 / :3390 | **NEW H3 extending a named family** (+ cross-ref `tool-implementation.md:448`) |
| d | `wiki/hardware-optimization.md` | `## Compiled Update — 2026-09-07 (wrap-up): SMT siblings…` (:4612 / H3 :4614) | **EXTENDS — and partially corrects** its prescribed occupancy instrument (+ reconcile with MEAS-1 at :43; pointer `inference-serving.md:622`) |
| e | `wiki/hardware-optimization.md` | `## The champion kernel: 1.4834×…` (:4564) **and** `### The champion multiplier was understated…` (:49) | **EXTENDS both** — supersession banner at :4564, new ratios as H3 at :49; chase the 5 derived-figure sites incl. cross-page `benchmark-methodology.md:4308` |

**Net: two pages touched, one new H2 (on `benchmark-methodology.md`), no new page, no new taxonomy
category.** Every finding maps to `benchmark_methodology` or `hardware_optimization`, both of which
already exist and both of which clear the 3-source threshold from this scan.

### Post-compile checklist (for whoever holds the lease — not run here)

1. Land (a)–(e) in a tracked source first; re-run the scanner so those sources are in the delta.
2. Compile; keep each new section's own `### Source References (2026-09-08, …)`, ≥3 refs.
3. `cite-check` if any `intake-NNN` is referenced.
4. `lint_wiki.py` (pass 6 structural) must be clean.
5. `compile_sources.py --check-manifest` — `writer_evidence_policy` must still pass.
6. Only then `compile_sources.py --touch`, and commit the tracked `wiki/source_manifest.json`
   with the pages. Consider also refreshing the stale `wiki/.last_compile` noted in Step 1.

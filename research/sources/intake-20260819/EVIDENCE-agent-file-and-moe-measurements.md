# Session-derived measurements — intake batch 2026-08-19/20

Created 2026-08-20 to close defects **D4** and **D11**: figures that were being quoted in
session and in index entries but existed in **no tracked artifact**. `tmp/*` is gitignored
(`.gitignore:33`), so anything held only there is not evidence.

Two classes below, and they are **not equally trustworthy**. Read the provenance line before citing.

---

## A — Agent-file measurements (REPRODUCIBLE, re-measured 2026-08-20)

Command: `wc -lw agents/shared/*.md CLAUDE.md`; `grep -c '^## ' CLAUDE.md`.
Re-run to reproduce. These are facts about our own tree at this commit.

| File | Lines | Words |
|---|---:|---:|
| agents/shared/WORKFLOWS.md | 48 | 262 |
| agents/shared/INVARIANTS.md | 38 | 317 |
| agents/shared/HARNESS_RUN_POLICY.md | 101 | 680 |
| agents/shared/ENGINEERING_STANDARDS.md | 103 | 734 |
| agents/shared/MEASUREMENT_POLICY.md | 97 | 1,065 |
| agents/shared/SESSION_LIFECYCLE.md | 182 | 1,780 |
| agents/shared/OPERATING_CONSTRAINTS.md | 372 | 3,949 |
| **Live policy subtotal (7 files)** | **941** | **8,787** |
| ENGINEERING_STANDARDS.compressed-mild.md | 104 | 673 |
| ENGINEERING_STANDARDS.compressed-medium.md | 101 | 544 |
| ENGINEERING_STANDARDS.compressed-aggressive.md | 94 | 420 |
| **Compression variants subtotal (3 files)** | **299** | **1,637** |
| **All 10 files** | **1,240** | **10,424** |

`CLAUDE.md`: **226 lines / 2,365 words / 22 H2 headings** (10.5 words per line).

### CORRECTION to a claim made earlier in this session

Earlier in this batch I reported: *"agents/shared/ is 10,424 words — the largest single context
file in the entire 466-project corpus is 8,951. **We exceed the corpus maximum.**"*

**That comparison does not survive scrutiny, in two separate ways.**

1. **The 10,424 figure includes three `ENGINEERING_STANDARDS.compressed-*` variants** — outputs of a
   compression *experiment*, not loaded policy. Excluding them, the live tree is **8,787 words,
   which is 164 words UNDER the 8,951 corpus maximum**, not over it.
2. **It compares a 7-file TREE total against a SINGLE-FILE maximum** — a category error. On a
   like-for-like basis our largest single agent file is `OPERATING_CONSTRAINTS.md` at **3,949
   words**, comfortably under 8,951.

**The defensible statements are:**

- Our largest *single* agent file (3,949 w) is well within corpus norms.
- Our whole live shared tree (8,787 w) is roughly the size of the largest single file anyone in the
  corpus ships — notable, but it is a tree-to-file comparison and must be labelled as such.
- The genuinely anomalous figure is structural, not volumetric: **`CLAUDE.md` carries 22 H2 headings
  against a corpus average of 2.7 categorised L1/L2 headings.**

### The finding that does survive, and is actionable

`CLAUDE.md` sits at the **96.5th percentile by words** but only the **85.4th by lines** — 10.5 words
per line. **A compression pass that targets LINES systematically under-finds.** Denominate the
target in **words**. (Corpus reference: intake-1199, re-derived from the authors' Zenodo replication
package, record 18368326.)

---

## B — MoE expert-coverage figures (REPRODUCIBLE — re-derived and verified 2026-08-20)

### Correction to defect D11 as I first filed it

I recorded these figures as having **no durable provenance**, on the grounds that grepping for
`0.4454` hit only artifacts this session generated. **That was wrong, and the method was the
problem:** I grepped for the *output* instead of looking for the *input*. The source artifact exists,
is properly provenanced, and carries its own `SHA256SUMS`:

```
/mnt/raid0/llm/epyc-inference-research/data/
  expert_routing_skew_glm52_20260717T_production_representative/
    expert-routing-skew.counts.json   (174 KB)
    expert-routing-skew.stats.txt · expert-routing-skew.execute.log
    SHA256SUMS · README.md
```

What was genuinely missing was only the **derivation script** and a pointer to it from the index.
Both now exist: `derive_moe_layer_local_coverage.py`, beside this file. Re-run it to reproduce.

### Verified output (every cited figure reproduces exactly)

Source: GLM-5.2, 75 layers × **254,976 selections each** (19,123,200 total), production-representative
calibration, captured 2026-07-17.

| Statistic | Global aggregate | Per-layer |
|---|---:|---:|
| Gini | 0.0664 | **median 0.4454**, max 0.5187 |
| Normalised entropy | 0.9987 | median 0.9314, min 0.9011 |

| Budget | Per-layer WTC | Global aggregate | Ratio |
|---|---:|---:|---:|
| top_8 | 16.4% | 4.1% | 3.98× |
| top_16 | 25.0% | 7.9% | 3.16× |
| top_32 | **37.2%** | **15.2%** | **2.45×** |
| top_64 | **54.3%** | 29.0% | 1.88× |
| top_128 | 77.3% | 54.6% | 1.42× |

### A second correction, to the summary phrasing

The finding was reported in-session as *"layer-local skew is worth about 2.4× the global statistic
**at every budget**."* It is not constant — the advantage **decays monotonically**, 3.98× at top_8
down to 1.42× at top_128. 2.45× is the value **at top_32 specifically**. Always quote the ratio with
its budget attached.

### What this does and does not establish

**Does:** the 2026-07-17 no-go was decided on the global aggregate (top_32 = 15.19%, Gini 0.0664),
which is the wrong unit for a cache whose allocation unit is a (layer, expert) tensor. Per-layer the
same data is materially skewed. That is why the gate reopened.

**Does not:** make expert caching pay. intake-1200 (HOBBIT) supplies the stronger and independent
objection — we are **RAM-resident and do not fetch**, so a design that shrinks fetch *bytes* has no
term to act on. The skew question and the bottleneck question are separate; the second one is
decisive on its own.

---

## C — Operator-supplied inline sources (D4)

The four write-ups pasted by the operator in this batch now live beside this file, on a tracked
path, with hashes verified byte-identical to the scratch originals:

| File | sha256 (first 12) | Cited by |
|---|---|---|
| `INLINE-A-test-time-compute-engineering.md` | `2aa7faa8121d` | intake-1174 |
| `INLINE-B-show-me-visual-representations.md` | `ed041aa3641c` | intake-1181 |
| `INLINE-C-visual-codebase-atlases.md` | `cb86c0063fa1` | intake-1184 |
| `INLINE-D-hot-expert-caching-moe.md` | `6a6bc713282e` | intake-1185 |

`6a6bc713282e` matches the `source_revision` intake-1185 already recorded, so the copy is
provably the artifact that entry was written against. Index `locator_note` fields were re-pointed
from `/workspace/tmp/...` to `research/sources/intake-20260819/...` in the same pass.

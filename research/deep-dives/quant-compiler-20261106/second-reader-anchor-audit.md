# Second-reader audit — Stage-2 quant/compiler intake (2641–2649)

Date: 2026-11-06 · Auditor: independent second reader (subagent) · Sources read from
`/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/` and `../repo-LinQuant` at
`624a1a27049cbc50a0dfa3a0a6a9140c9ed6c2a8`.

**Method.** For each of the 40 `claim_anchors`: (1) whitespace-normalised strict substring
search (`' '.join(s.split())`) in the mapped source; if absent, a second pass folds typographic
and HTML-math variants (`– — × ’ “ ” $$…$$`, `\times`, `^{\star}`, `_{…}`, `\%`) and the
residual diff is classified (a) rendering artefact / (b) paraphrase / (c) absent; (2) SHA-256
recomputed over the whitespace-collapsed stripped quote with an independent
`re.sub(r'\s+',' ')` implementation; (3) support judged against the *key_claim at that index*,
not against the quote's own plausibility; (4) locator checked against the line/section where
the passage actually sits.

**The hash check is not a provenance check.** All 40 hashes MATCH because the stored hash was
computed from the stored quote. A MATCH says the entry is internally consistent; it says
nothing about whether the string is in the paper. Every finding below that matters comes from
the find/support/locator columns, not the hash column.

---

## 1. Consolidated table

| entry | ci | found | hash | support | locator | note |
|---|---|---|---|---|---|---|
| 2641 | 0 | FOUND :165 | MATCH | PARTIAL | OK | quote names the seven invariance *categories*; the applicability constraints (key-rotation local under diagonal decay, reciprocal rescaling invalid for delta writes) are not in it |
| 2641 | 1 | NF(a) | MATCH | YES | **WRONG** | source renders `⟨T,T⟩` as `⟨ T , T ⟩ \langleT,Trangle`; quote is at **:832**, locator cites :2428-2435 = Table 5 body |
| 2641 | 2 | FOUND :197 | MATCH | YES | **WRONG** | quote is the *Introduction contributions bullet* at :197; §4.2/Tables 2 & 17 substantiate the numbers, not the sentence |
| 2641 | 3 | NF(a) | MATCH | PARTIAL | **WRONG** | `query–key` en-dash; quote is in the **§5 Conclusion at :967**, not §4.2 (:960) / App. D.2 (:1737); the causal re-attribution ("SSDi8's fused pass", "in this implementation") is absent from the quote |
| 2641 | 4 | FOUND :2825 | MATCH | YES | OK | exact |
| 2642 | 0 | FOUND :37 | MATCH | PARTIAL | OK | one line (`dt = torch.float64`) cannot establish "239-line torch-only … five of seven invariances … two rescalings harness-side" |
| 2642 | 1 | FOUND :21 | MATCH | YES | OK | comment states fp32 WY prep in torch; triangular-solve launch not in quote |
| 2642 | 2 | FOUND :3 | MATCH | PARTIAL | OK | docstring proves INT32-on-INT8 + Q0.7 gate; "2037-line" (verified true: 2037 lines across `kernels/mamba2/*.py`) and "no test file" are not in the quote |
| 2642 | 3 | FOUND :89 | MATCH | YES | OK | `assert err < 1e-9` |
| 2642 | 4 | FOUND :115 | MATCH | YES | OK | |
| 2643 | 0 | FOUND :216-222 | MATCH | YES | OK | table intact; **but rows sum to 756 vs the stated 761 (5 s gap) and shares to 99.3%** — the 2644 entry already records this as the paper's own gap |
| 2643 | 0 | FOUND :262-263 | MATCH | YES | OK | |
| 2643 | 1 | NF(a) | MATCH | YES | OK | `8.1×` vs `8.1x`; model (GLM 5.3/B200) is in the Fig. 2 caption at :273-274 |
| 2643 | 2 | FOUND :511 | MATCH | PARTIAL | OK | quote is a subject-less fragment continued from :467 ("Kimi K3"); the three estimate levels are not in it |
| 2643 | 3 | NF(a) | MATCH | PARTIAL | OK | en-dash + a correctly-marked elision `(...)`; supports only the KB arm of a three-ablation claim |
| 2643 | 4 | FOUND :249-250 | MATCH | PARTIAL | **WRONG** | locator :1640-1643 is Appendix "agent time" prose; `perpetually loops` occurs **once**, at :249 |
| 2644 | 0 | NF(a) | MATCH | YES | OK | quote is a *reconstruction* of a 12-row table (one cell per line); all 12 values verified at :216-242 |
| 2644 | 1 | NF(a) | MATCH | PARTIAL | OK | curly quotes; supports one of the three mechanisms — the blog-vs-paper taxonomy divergence is the dive's mapping |
| 2644 | 2 | NF(a) | MATCH | PARTIAL | OK | en-dash; supports the design-goal lesson and the MoE/batch>1 scoping; the 1.7× Llama-1B claim is not in this quote |
| 2645 | 0 | NF(a) | MATCH | PARTIAL | OK | `$$dA_{cs}$$`; supports the FP16 exception only, not the five-module INT8 path or the "first" claim |
| 2645 | 1 | NF(a) | MATCH | PARTIAL | OK | `$$B$$`, `$$C$$`; supports early per-G quantisation once; the 3-submodule reuse and ~3% cost are elsewhere |
| 2645 | 2 | NF(a) | MATCH | **NO** | OK | `$$S$$`/`$$2^k$$`; quote says the *opposite* of "rather than a true bit-shift" — see §3.2 |
| 2645 | 2 | NF(a) | MATCH | YES | OK | `c^{\star}`/`Y^{\prime}`; supports the closed-form channel-mean correction |
| 2645 | 3 | NF(a) | MATCH | PARTIAL | OK | em-dash; supports the observation, not the dive's scale-granularity reinterpretation or the control definition |
| 2646 | 0 | NF(a) | MATCH | YES | OK | `W8A8 ,` spacing artefact |
| 2646 | 1 | NF(a) | MATCH | PARTIAL | OK | `x ,` artefact; "8 groups of 128 channels" is not in the quote (source says m=8 groups of heads, then n channel groups) |
| 2646 | 2 | FOUND :575 | MATCH | **NO** | OK | the "quote" is the two-word string **"Table 5"** — a caption fragment supports no claim |
| 2646 | 3 | **NF(b)** | MATCH | PARTIAL | **WRONG** | quote is a paraphrase ("weight-only W4A16 runs 7.58 ms against W4A8 at 7.43 ms") that does not occur; the numbers are Table 5 cells at :631-643 |
| 2647 | 0 | NF(a) | MATCH | PARTIAL | OK | curly apostrophe; quote carries none of 3.4% / 8.5% / 6-of-10 (locators :210-226 and :367-376 do) |
| 2647 | 1 | FOUND :153-157 | MATCH | YES | OK | all five sub-mechanisms named |
| 2647 | 2 | NF(a) | MATCH | YES | OK | source double-renders `3.4×3.4\times`; triad exact at :160-163 |
| 2647 | 3 | NF(a) | MATCH | PARTIAL | OK | `9%9\%` double-render; supports the NVIDIA context-reuse 9% only, not the AMD 2.6× no-reuse half |
| 2648 | 0 | FOUND :169 | MATCH | PARTIAL | OK | supports "fails variance alignment"; the input-dependent-covariance mechanism and per-tensor framing are at :307-310 |
| 2648 | 1 | FOUND :339 | MATCH | PARTIAL | OK | supports KLT+Hadamard equalisation (Eq. 13); the online smoothing/folding into B, C, Δ is §4.3, not quoted |
| 2648 | 2 | FOUND :168 | MATCH | **NO** | OK | quote asserts Transformer-recipe degradation — the proposition the claim says is *refuted*; +1.5/+6.6/+0.1/+4.8 are the ablation table at :650-665 |
| 2648 | 3 | FOUND :352 | MATCH | **NO** | OK | smoothing-vector motivation; says nothing about the [16,16] N-axis block, parameter count or scalar-decay exactness |
| 2649 | 0 | NF(a) | MATCH | YES | **WRONG** | `Kerncap ,` spacing; locator :67-68 is CSS — the abstract sentence is at **:330**, mechanism :872-905 is correct |
| 2649 | 1 | NF(a) | MATCH | PARTIAL | OK | `™` superscripts; three architectures supported; six workloads / 152 MB-30 GB / vLLM MoE are not in the quote |
| 2649 | 2 | NF(a) | MATCH | PARTIAL | OK | `13.6 x` double-render; locator :69 is CSS — the sentence is at **:349**; :2269/:2357/:2361 are correct |
| 2649 | 3 | FOUND :2328-2330 | MATCH | YES | OK | paragraph starts :2325 |

**Counts.** 40 anchors / 9 entries.

| result | count |
|---|---|
| FOUND (strict whitespace) | 18 |
| NOT-FOUND, class (a) rendering/typography artefact | 21 |
| NOT-FOUND, class (b) paraphrase | 1 (2646#3) |
| NOT-FOUND, class (c) genuinely absent | 0 |
| hash MATCH | 40 |
| hash MISMATCH | 0 |
| support YES | 16 |
| support PARTIAL | 20 |
| support NO | 4 (2645 ci2 Eq. 9, 2646 ci2, 2648 ci2, 2648 ci3) |
| locator OK | 33 |
| locator WRONG | 7 |
| claim with **no anchor at all** | 1 (2649 ci1) |

Support is counted **per anchor**. Two claims carry two anchors: 2645 ci2 is `NO` (Eq. 9 text)
plus `YES` (least-squares correction) → claim-level **PARTIAL**, and 2649 ci3 is the abstract
13.6× plus the 18.3 s recompile → claim-level **PARTIAL**. 2643 ci0 has two anchors, both `YES`.

---

## 2. Failure list, with fixes

### 2.1 Hard failures (fix before this entry can be called dive-verified)

**F1 — 2648 ci2: the anchor asserts the opposite of the claim.**
Quote (:168): *"However, directly applying this method to Mamba models leads to significant
accuracy degradation (e.g., on average more than 12% accuracy drop on Vim … even at 8 bits)."*
The claim says a fixed-granularity rotation-on/off control is **positive in every tested cell**
and refutes the general anti-Hadamard claim. The quoted sentence is the anti-Hadamard
proposition being refuted — it is the *motivation*, not the evidence.
**Fix:** re-anchor to `mambaquant.txt:650-665` ("Hadamard Rotate 33.9(↑1.5) / 50.8(↑6.6);
25.1(↑0.1) / 40.2(↑4.8)") and move the :168 sentence to a separate "motivation/contrast"
anchor. Also soften "in every tested cell": the +0.1 cell is inside the dive's own ±0.5
ablation error bar (draft §167), so the evidence is 3 positive cells + 1 null, not 4 positive.

**F2 — 2648 ci3: wrong passage.**
Quote (:352) is the *smoothing-vector* motivation. The claim is about the [16,16] Hadamard
acting on the state axis **N**, its 16-parameter cost, and exactness under scalar decay along N.
Nothing in the quoted sentence touches any of that; the dive's own draft (§245-255) derives the
axis from three *other* locators.
**Fix:** anchor to the passage(s) the draft actually used for the axis inference (the `[16,16]`
width at :92/draft, the `pScan` distribution note, and LinQuant's "no decay or scalar decay"
sufficient condition), and label the N-axis identification as an **inference**, not a quote.

**F3 — 2648 ci2/ci3 knock-on to the verdict.** With F1+F2, the entry's headline — "the missing
third position on SSM rotation … refutes SSDi8's general claim" — currently rests on one of the
two anchors being inverted and the other being irrelevant. The *conclusion survives* on Tab. 3,
but the entry should say so explicitly: "anchor set does not carry the refutation; Tab. 3 does."

**F4 — 2645 ci2: the claim contradicts its own quote.**
Quote (:343): *"where S is a gating constant chosen as 2^k to enable bit-shift operations for
minimal latency (with k=7)"*, and the immediately following sentence: *"This allows recurrent
updates to be performed by simple bit-shift operations."* The key_claim says the state persists
"by Q(Decay)/2^7 (k=7) **rather than a true bit-shift**". Division by 2^7 **is** the shift; the
dive's own report (§74) states the accurate version — "`Q(Decay)/2^7` is a fixed-point multiply;
only the `/2^7` is shiftable." The intake sentence overstates by one clause.
**Fix:** "…by a fixed-point multiply `Q(Decay)/2^7`; the `/2^7` is the only shiftable part, and
the multiply needs ≥16-bit intermediates with no specified clamp/rounding (derived, not stated
in the paper)." Anchor to :336-344 and mark the derivation as the auditor's, not the paper's.

**F5 — 2646 ci2: the anchor is the string "Table 5".**
Two words. It supports nothing. The claim's numbers (1.3× prefill / 3× generation / 4× memory /
1.6% drop / 12.5-12.7 tok/s) are in §5.2 (:653-665) and Table 5 rows (:595-649).
**Fix:** quote §5.2's sentence (`In the W4A8 configuration … 3.89\times less memory use,
1.39\times prefilling, and 3.05\times faster generation`) and add a second anchor on the
Orin rows. A caption is not a claim anchor.

**F6 — 2646 ci3: fabricated quotation (class b).**
"weight-only W4A16 runs 7.58 ms against W4A8 at 7.43 ms" does not occur anywhere in the source.
The numbers are correct Table 5 cells (`W4A8 7.43`, `W4A16 7.58`, :631-643), and the inference
(0.15 ms = activation-side contribution) is sound. But the anchor presents a synthesis as a
verbatim quote.
**Fix:** quote the cell text (`W4A8 7.43 / 140.78 / 79.91 / 2088.03`) or write it as
`[table-derived]`, never as a quotation. This is the one anchor in the set whose text cannot be
found at all.

### 2.2 Locator failures (mechanical)

| entry/ci | stored locator | actual | fix |
|---|---|---|---|
| 2641 ci1 | `paper.txt:2428-2435` | quote :832, Table 5 rows :2424-2440 | cite both: `§4.1 :832; Table 5 :2396-2440` |
| 2641 ci2 | `§4.2, Tables 2 and 17` | quote is the intro contributions bullet :197 | `Introduction :197; results Tables 2/17` |
| 2641 ci3 | `:960, :1737` | quote in §5 Conclusion :967 | `§5 :967; evidence §4.2 :960, App. D.2 :1739` |
| 2643 ci4 | `tc.md:1640-1643` | :249-250 (`perpetually loops` is a single occurrence) | `tc.md:249-250` |
| 2646 ci3 | `§5.2, batch-1 TPOT comparison` | quote absent; data Table 5 :631-643 | `Table 5 :631-643` |
| 2649 ci0 | `kerncap.html:67-68` | :67-68 is CSS; abstract :330 | `:330; mechanism :872-905` |
| 2649 ci2 | `kerncap.html:69` | :69 is CSS; abstract :349 | `:349; decomposition :2357-2361` |

Pattern: the dive's locators frequently point at the **evidence for the claim**, while the quoted
string is somewhere else (often the abstract, introduction or conclusion). That is defensible
for a reader but wrong for a `quote`/`locator` pair, and it is exactly what a mechanical
re-find is supposed to catch.

### 2.3 Class (a) artefacts — no action required, but do not let the audit call them "verified"

21 of 22 not-founds are rendering/typography: LaTeX kept alongside Unicode (`⟨ T , T ⟩
\langleT,Trangle`, `$$dA_{cs}$$`, `$$2^k$$`), doubled math (`3.4×3.4\times`, `13.6 x 13.6x`,
`9%9\%`), curly quotes, en/em dashes, `™`, and PDF cell spacing (`W8A8 ,`, `Kerncap ,`).
These are acceptable. Two deserve a note because they are not merely cosmetic:

- **2643 ci3** and **2643 ci4** contain a real elision `(...)`. The elision is correctly marked,
  so the quote is honest, but the anchor loses the sentence that shows the 25-31% is a *speedup
  loss vs no-KB*, not a quality result — keep the elision but state what was dropped.
- **2644 ci0** is a **reconstruction** of a 12-row table into one line. Every value checks out
  (:216-242), but the quote is not contiguous text in the source. If this anchor is ever used
  to prove "the blog says X", the reconstruction should carry `[table]`.

---

## 3. Where the verdict overstates relative to its own quote

Ranked by severity. These are *claim-level* problems; they survive the hash check because the
hash only proves the quote is internally consistent.

**3.1 — 2648 `adopt_patterns` / "rotation is right; SSDi8's anti-Hadamard claim is refuted".**
The two load-bearing anchors are inverted and irrelevant (F1, F2). The conclusion is still
correct on Tab. 3, but the entry's own quotation says the opposite of the conclusion, and the
"+0.1" cell is within the paper's ±0.5 ablation noise. As written, a reader who checks only the
anchors would conclude MambaQuant *supports* SSDi8. **Severity: high** — this is the entry that
carries the cross-paper reconciliation for 2641/2645/2648.

**3.2 — 2645 ci2 "rather than a true bit-shift".** The quote and the next sentence say
"bit-shift operations"; the accurate statement (dive report §74) is that only the `/2^7` is a
shift. The intake claim overstates its own renderer-reading. **Severity: medium-high** — it is
stated as an overturned claim ("narrowed"), so it will be cited as a correction.

**3.3 — 2646 ci2 and ci3.** ci2's anchor supports nothing; ci3's anchor is a paraphrase that is
not in the source. The entry's `reported_results` ("1.3x / 3x / 4x / 1.6%", "12.5/12.7 TPS") are
all correct against §5.2 and Table 5 — the *anchors* are the defect, not the numbers.
**Severity: medium** — the verdict does not overstate the paper, but the evidence trail is
invalid, so the entry cannot be re-verified mechanically later.

**3.4 — 2649 ci3 "dominated by replacing a 2,072 s counter-profile run".** Arithmetic checks
(`2,208 = 2,072 + 136`; `162 = 15.6 + 18.3 + 129.4 + ~1`; `2,208/162 = 13.63`; saved 1,942.6 of
2,046), so the claim is correct. But neither anchor carries it: the 13.6× anchor is the abstract
sentence and the 18.3 s anchor is one recompile step. The decomposition lives at :2342 and
:2357. **Severity: low** — correct claim, incomplete anchor set; add a third anchor.

**3.5 — 2643 ci4 "continual adaptation is asserted, not instrumented".** An absence claim
anchored by a *positive* quote about the loop. The quote cannot establish "no drift detector,
threshold, trigger or re-convergence measurement". The entry's `claim_corrections` says the
evidence is a full-text zero-hit scan — that is the right evidence, but it is not what the
anchor is. **Severity: low** — recommendation: change `kind` from `heading-and-hash` to
`negative-scan` and record the scanned terms and their zero counts.

**3.6 — 2647 ci2 "the triad is figure-derived and unreproduced in body prose".** The anchor *is*
the abstract/intro statement of the triad; the contradiction (body says 2.4-2.5%) is at another
locator. The claim is honest and self-flagged, but as an anchor/claim pair it is unsupported.
**Severity: low.**

**3.7 — 2642 ci0/ci2: anchors that cannot carry their claims.** `dt = torch.float64` (one line)
and a three-line module docstring are asked to support composite claims about file length,
callable structure, test absence and the count of invariances in the core. The claims are
**true** (I verified 239 and 2037 lines, and no mamba2 test file), but the anchors are
illustrations, not proof. **Severity: low** — recommendation: add a `grep`/`wc`-style locator
(`reference.py:1-239`, `tests/` listing) rather than a single code line.

**3.8 — 2649 ci1 has no anchor at all.** The address-space closure / compile_commands.json+DWARF+nm
/ VFS-overlay claim is the mechanism half of the entry and is marked "unaffected" in
`claim_corrections`, but no anchor was recorded for it. **Severity: medium** — a claim asserted
as verified with zero recorded evidence is worse than one flagged as unverified. Add an anchor
at the §4.2 mechanism text, or downgrade `verification`.

---

## 4. What I verified independently and what held

- `repo-LinQuant` is at the recorded commit `624a1a27`; `reference.py` is 239 lines;
  `kernels/mamba2/*.py` totals **exactly 2037** lines; no `test_mamba2*` exists.
- 2646's 7.43 / 7.58 ms cells and 12.5/12.7 tok/s (derived as 1000/79.91 and 1000/78.77) are
  real; 2648's +1.5/+6.6/+0.1/+4.8 are real Tab. 3 cells; 2649's 2,072 / 129.4 / 162 / 2,208 s
  and 13.6× all reconcile; 2647's 3.4% / 8.5% / 6-of-10 are all in the text at the cited
  locators; 2643's 1,354/168 = 8.06 and 761 s = "12 min 41 s" hold, though the table's rows sum
  to 756 and its shares to 99.3% (the 5 s row/total gap the 2644 entry already records);
  2641's Table 5 rows reproduce 16.446 → 15.633 against 15.553.
- 2642 ci2's "no test file at all" is accurate *for `kernels/mamba2`*: no test imports that
  module (the `mamba2` cells exercised by `tests/test_reference.py` are reference-core cells,
  not the Triton chain). Worth stating that distinction in the entry, because the file
  `tests/test_reference.py` does contain the string `mamba2`.
- All 22 strict not-founds are explained by the source's rendering, except 2646 ci3
  (paraphrase). None is a fabricated citation in the sense of citing a passage that does not
  exist — with that one exception, which is a *synthesis presented as a quote*.

## 5. Bottom line

The dive's **numbers** are in good shape: every quantitative claim I spot-checked reconciles
with the source. The **evidence trail** is not: 7/40 locators point at the wrong place, 4/40
anchors do not support their claim (2 of them assert the opposite or something unrelated), 1/40
is a paraphrase that is not in the source, and 1 claim has no anchor. The two entries that need
repair before they can be called dive-verified are **2648** (inverted + irrelevant anchors on a
load-bearing cross-paper conclusion) and **2646** (a caption fragment and a fabricated quote on
its quantitative claims). **2645** needs one clause narrowed; **2649** needs one missing anchor
and two corrected line numbers.

---
entry: intake-2644
title: "Together Compiler: Continual Compilation for AI inference (vendor announcement)"
stage: 2 (deep dive)
analyzed_at: 2026-11-06T16:05:32Z
read_depth: full-text — both vendor posts fetched and converted to text; the TKCC paper markdown (raw/tc.md) read for every numeric cross-check; lane handoff handoffs/active/autokernel-loop.md searched exhaustively for megakernel/fusion intent
retrieved: 2026-11-06T16:04Z (curl -sL, both posts live)
artifacts:
  - path: /mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/together-blog.html
    sha256: 1228f1182f64812c84ed47e99ab19aafeedc9b60d3dfb4724266c2f0481abd3a
    bytes: 685494
    retrieved: 2026-11-06T16:04Z
  - path: /mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/polymorphic-inference.html
    sha256: 3b8336fbde43fd2efe4e582e39cbee243408cb18da77c5b3e1b058162df2a909
    bytes: 557650
    retrieved: 2026-11-06T16:04Z
  - path: /mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/tc.md
    sha256: dda2a674266e9a8e087f670cf0f3c83fbb1dfbbe9f056d91f3b9b74074f2648c
    bytes: 114157
    note: pre-existing (paper intake-2643); not re-fetched, used as the cross-check authority
  - path: /mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/together-blog.txt
    sha256: b6c8fe948d918c06f65efab29b2cdd2c71fa57fc04b5b7109ebd1586ddea4113
    note: derived (script/style stripped, whitespace-normalised); all blog locators below are lines in THIS file
  - path: /mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/polymorphic-inference.txt
    sha256: db6daee9fc88edbb9aee378b05e8ed9215d0724bc653dd10003878edf28979c2
    note: derived; all strategic-post locators below are lines in THIS file
quote_convention: >
  Quotes are the page's own text content, whitespace-normalised to single spaces; quote_sha256 is
  sha256 over that exact normalised UTF-8 string (no trailing newline). Every quote below was
  verified present in the raw text before hashing.
safety: >
  Both posts and the paper were treated strictly as data. Nothing in them was executed or followed as
  instruction.
verdict_summary: "3 CONFIRMED (one scoped), 0 OVERTURNED, 0 PARTIAL, 0 NOT-FOUND — but the entry is a
  companion restatement: it contributes no local decision, and its headline table is numerically
  irreconcilable with the paper it summarises."
---

# Stage-2 dive — intake-2644, Together Compiler blog (companion entry)

## 0. What this entry actually is

Two URLs are bundled into one entry: the research blog (published 11/4/2026) and the company
strategic post "From Static to Polymorphic Inference" (same date, same authors' org). Claim 3 lives
*only* in the second URL — it is not checkable at the ingested URL alone. That is a bookkeeping
defect worth fixing at Stage-3 (one entry, two URLs, one of which carries a third of the claims).

Novelty is correctly tagged `low`: every quantitative claim in the blog also appears in the paper
(entry intake-2643), except the startup table, which *replaces* the paper's table with a different,
unattributed one.

## 1. Claims table

| # | Claim (paraphrase) | Verdict | Quote (verbatim, normalised) | Locator | quote_sha256 |
|---|---|---|---|---|---|
| 1 | Startup table: status quo 467 s vs 9.0 s persistent path, itemised through to "total time to serving" | **CONFIRMED** (as text; *not* as a measurement — see A) | `Process + worker init. 93 – Weight loading 50 – KV-cache sizing 21 – JIT kernel warm-up 93 – Autotuning 193 – API server ready 10 – RPC call + Together Compiler setup – 1.7 CUDA-graph capture 7 7.3 Total time to serving 467 9.0` | `together-blog.txt:213-242`; caption at `:243` | `a9d85c257e9d7db06ec875210728eb8b622ac1d1a2ee3aa2f04c339b28d7675e` |
| 1b | Caption text | CONFIRMED | `Table 1: Engine startup is expensive` | `together-blog.txt:243` | `26fbabc11a183b553b297516e0884f9420030d672c7487fd43e94abd726aff9e` |
| 2 | Three mechanisms = persistent engines, fast/slow tiering, parallelism cost model | **CONFIRMED** for the blog's own text — but they are *not* the paper's three contributions (see C.2) | `1. TKCC maximizes experimentation throughput and minimizes GPU idle time during agent optimization` | `together-blog.txt:211` | `9869d5809e97819e286deadf9a91943cf2e9c7da66eb25c746e662d7414ec6a6` |
| 2b | Tiering mechanism | CONFIRMED | `TKCC uses a tier of persistent engines to balance the throughput-fidelity tradeoff: “fast engines” load a few layers and are ideal for rapid iteration and low-variance timings, while “slower engines” load many layers and are ideal for testing whether optimizations hold-up on real data distributions.` | `together-blog.txt:245` | `56f88e1be610a732f589c77b9384dc38cd9d7c6fb93ad7e27307b155c5cb15bc` |
| 2c | Cost-model mechanism | CONFIRMED | `3. TKCC utilizes a custom cost model to select parallelism strategies (e.g., TP, EP, DCP, etc.) for agents to achieve the highest performance` | `together-blog.txt:247` | `b42fbc63ffcb7de01cdea1485a8ceac1bd588f54a27846e691f0d4f6e6016f43` |
| 3 | Strategic post concedes that, after putting megakernels into production, fusion is not the right design goal for varied dynamic workloads | **CONFIRMED (scoped)** — the sentence is exactly this; "concedes" is fair only if it is not read as "fusion is useless" (see B) | `But through the experience of putting some of the first megakernels into production for our customers last year, we learned an interesting lesson: megakernel fusion is actually not the right design goal for modern Polymorphic Inference! In the era of Polymorphic Inference, every variation – from model architecture (e.g. MoE), to workload (dynamic workloads larger than batch size 1) – requires different technical approaches.` | `polymorphic-inference.txt:213` | `cf3c84607936e75c08edd05c671546b04d1b181987215a3c050b8a60586b5528` |
| 3b | Framing that precedes it (what "megakernel" meant to them) | CONFIRMED | `And nearly two years ago we wrote about megakernels for AI inference, a single kernel painstakingly designed around a single static shape (e.g., batch size one Llama 1B).` | `polymorphic-inference.txt:213` | `f89af53f236749f1ff5016df0fbef67f0ec994bb9331151b562f8b33e8cfd379` |

No claim in the entry was OVERTURNED, PARTIAL or NOT-FOUND. Digests are 64-char sha256 over the
whitespace-normalised quote string (convention in front matter); Appendix A repeats them with the
supporting quotes that are not in this table.

## 2. A — Does the blog's startup table agree with the paper's cold-start breakdown?

**No. They are two different measurements with disjoint taxonomies, and neither document states any
relationship between them.** The blog never cites 761 s; the paper never cites 467 s.

| | Blog (`together-blog.txt:213-242`) | Paper, Table 1(a) (`tc.md:216-222`) |
|---|---|---|
| Attribution | none — no model, engine, hardware, or node count | `Table 1: MiniMax-M3.1-Flash on TensorRT-LLM...` (`tc.md:232`) |
| Total | **467 s** | **761 s** |
| Rows | process+worker init 93 · weight loading 50 · KV sizing 21 · JIT warm-up 93 · autotuning 193 · API ready 10 · CUDA-graph 7 | model loading 265 · KV sizing 73 · autotuning 192 · CUDA-graph decode 34 · CUDA-graph prefill 192 |
| Row sum | 93+50+21+93+193+10+7 = **467** (exact) | 265+73+192+34+192 = **756 ≠ 761** |
| Share column | absent | 34.8+9.6+25.2+4.5+25.2 = **99.3 %** (0.7 % ≈ 5.3 s unaccounted) |
| Fast path | 1.7 s RPC/setup + 7.3 s graph capture = **9.0 s** | not given in this table (tier stats are `tc.md:224-230`) |

Findings:

1. **Only one row coincides**: autotuning 193 s (blog) vs 192 s (paper). Everything else is
   bucketed differently or differs by a factor: weight/model loading 50 vs 265 (5.3×), CUDA-graph
   capture 7 vs 226 (32×), KV sizing 21 vs 73 (3.5×). 467/761 = 61 % — close enough to tempt a
   "same run, different buckets" story, but no re-bucketing of the blog rows reproduces the paper
   rows (e.g. blog init+load+warm-up = 236 s cannot become 265 s while KV shrinks 73→21).
2. The blog's status-quo column therefore describes **some other engine/model/hardware combination
   than the paper's table**, and it does not say which. The 467 s figure is not citable as "the
   paper's cold start" nor as any particular deployment's cold start.
3. The **paper's own table is internally inconsistent by 5 s** (rows 756 vs stated 761; shares sum
   to 99.3 %). That is a provenance weakness in the primary source, and it is the number a Stage-3
   packet would be tempted to quote. Quote 761 s only with that gap flagged, or quote the rows.
4. The blog's 9.0 s is arithmetically consistent with its own two rows and matches the paper's
   qualitative claim (startup decoupled from forward pass) but no paper number — the paper reports
   "startup to first job 11 min (slow tier) / 3 min (fast tier)" and "hot reload 45 s / 17 s"
   (`tc.md:224-230`), which are *not* the 9.0 s figure and not obviously reconcilable with it
   either (9.0 s cannot be "startup to first job" for a 60-layer engine).

**Verdict on A:** blog 467 s and paper 761 s are **different, unattributed measurements**; the paper's
761 s is the attributed one (MiniMax-M3.1-Flash/TRT-LLM) and should be preferred if either is cited,
with its 5 s row/total gap disclosed.

## 3. B — What the strategic post says about megakernels

Exact text (normalised), the two sentences together (`polymorphic-inference.txt:213`):

> And nearly two years ago we wrote about megakernels for AI inference, a single kernel painstakingly
> designed around a single static shape (e.g., batch size one Llama 1B). But through the experience of
> putting some of the first megakernels into production for our customers last year, we learned an
> interesting lesson: megakernel fusion is actually not the right design goal for modern Polymorphic
> Inference! In the era of Polymorphic Inference, every variation – from model architecture (e.g.
> MoE), to workload (dynamic workloads larger than batch size 1) – requires different technical
> approaches.

Is "concedes" fair? **Yes for the design-goal claim, and it is worth being precise about three
limits, because the entry's phrasing invites over-reading:**

- It is a **self-reversal on the goal**, stated in the vendor's own voice, from production experience
  ("putting some of the first megakernels into production ... last year"). That is a concession in the
  ordinary sense, not a mischaracterisation.
- It is **scope-limited to "modern Polymorphic Inference"** — MoE and dynamic workloads larger than
  batch size 1. Their own research blog still claims a win *against* megakernels on the megakernel
  workhorse workload: `outperforms available open-source megakernels by 1.7x on their workhorse
  Llama 1B batch size 1 setting` (`together-blog.txt:201`).
- They still **fuse when the shape is static and they own the whole program**: on Trainium2,
  `Fusing whole decoder layers into one kernel. Custom NKI kernels run each decoder layer’s attention
  and MoE as a single fused decode kernel. This is the opposite of what we saw on GPUs, where
  megakernels gave little or no gain.` (`tc.md:1750`). So the concession is "not the *general* design
  goal", not "fusion is wrong".

**Verdict on B:** CONFIRMED with the scope qualifier. A defensible paraphrase for any local document
is: *the vendor states megakernel fusion is not the right general design goal for dynamic
MoE/batch>1 serving, while retaining fusion for static shapes and whole-program compilation.*

## 4. C — What the blog adds over the paper, and what is restatement

### C.1 Blog-only (not in the paper)

| Item | Locator | Kind |
|---|---|---|
| The 467 s / 9.0 s itemised table | `together-blog.txt:213-242` | measurement, unattributed (see A) |
| Hardware enumeration incl. **Groq and "VR" (Vera Rubin)** as targets | `together-blog.txt:198` | roadmap/product, no measurement |
| Traffic anecdotes with specific numbers: 1.4× longer prompts, 97k vs 70k; +80 % prompt length two weeks post-release; "prompt lengths can suddenly double" | `together-blog.txt:204-206` | market colour; the paper's analogues are *different* customers and *different* numbers (`tc.md:183-191`), so these are not restatements of the same data |
| "first truly continual optimization loop" superlative | `together-blog.txt:200` | marketing (paper says "first truly continual agent loop", `tc.md:20`) |
| Deployment claim outside LLM inference: `We have been using TKCC as a general purpose AI compiler beyond LLM inference.` | `together-blog.txt:258` | production/deployment statement the paper does not make (paper claims *measured* generalisation, `tc.md:590`, not production use) |
| Product surface: `Together Compiler is available to end customers in limited beta today – reach out if you want early access!` | `polymorphic-inference.txt:232` | product/commercial (strategic post only) |
| Production framing: `Together Compiler is running in production today on some of our most popular serverless endpoints` | `polymorphic-inference.txt:226` | deployment statement |
| Reach/hiring CTAs, "serving more tokens than closed-source model labs on OpenRouter" | `polymorphic-inference.txt:229, 244` | company claim, unverifiable |

### C.2 Restatement only

`1.7×` on Llama 1B bs1 · `2.6×` over InferenceX · `1111` / `1205` TPS · `252×` experiment
throughput · `<24 h` · generalisation to weather/PDE/time-series/biology — all in the paper at
`tc.md:25-29, 136-139, 259, 574-581`. The blog **drops** the paper's qualifiers on each: 1111/1205
lose their hardware (`B200` / `GB300`, `tc.md:581`); 252× loses "and 11× lower idling time per
agent" (`tc.md:259`); "<24 hours" loses "using at most 2 nodes per model" (`tc.md:139`).

**Structural finding (matters for claim 2):** the blog's "three mechanisms" are **not** the paper's
three contributions. The paper's are (1) Tiered Persistent Engine, (2) cost model, (3) *bitter lessons
of performance optimization* / agent-context ablations (`tc.md:106-131`). The blog **splits (1) into
two** headlines (persistent engine, then fast/slow tier) and **silently drops (3)**. So "three
mechanisms" is a true statement about the blog and a misleading one about the work: the blog's
enumeration is a repackaging, not the paper's contribution list.

**What the blog adds that matters most is what it removes:** no tier table (11 min vs 3 min startup,
3.9 crashes/1000 on the fast tier — `tc.md:224-230`), no node budget, no reliability reporting, no
negative results. The paper's negative results are the ones with local value: the AMD megakernel agent
(`On AMD GLM 5.3, we saw the megakernel agent spend 24-hours, only to come up with 0.22% faster
performance.`, `tc.md:1616`) and the megakernel/graph-capability bans. None of this reaches the blog.

## 5. D — The lane's own position on megakernel formation

Lane: `/mnt/raid0/llm/worktrees/intake-quant-compiler-20261106`. File
`handoffs/active/autokernel-loop.md` (14,796 lines) contains **exactly one** occurrence of
"megakernel", and it is a rejection:

> `**G2 batch-one low-bit GEMV** | Too broad as written. Generic Q8 dequant is a stale premise
> (integer-native path); generic megakernel and several speculation/prefetch variants have matching
> negative or conditional history; ...`
> — `handoffs/active/autokernel-loop.md:4539`

Disposition in the same row: *"Split into atomic priors; seed only current-profile gaps — coalescing/
layout if cache-line evidence is poor, or another gfx90a MLP lever if the production path still
exposes it."* So megakernel formation is **not an active objective**; it was closed as *too broad*
and replaced by atomic priors, on evidence that predates this blog.

Where fusion *is* an active objective, it is op-level inside a decode step, not whole-model:

- `handoffs/active/autokernel-loop.md:5635` — **AK-ASM-H6** fused RMSNorm + quantize into one kernel,
  gate `>= 1.10` geomean, futility-only, marked done 2026-11-06.
- `handoffs/active/autokernel-loop.md:5653` — **AK-ASM-H15** fused GDN decode step (qkvz + conv1d +
  gated-delta in one kernel), explicitly distinguished from the rejected G9 occupancy rewrite.
- `handoffs/active/autokernel-loop.md:1742, 1749` — `fusion` is one *change_class* in the cell schema
  (`parameter | dispatcher | arithmetic | layout | fusion`), i.e. a permitted single-cell change, not
  a program-wide formation.

**Does the vendor concession bear on an EPYC decision?** **No decision, but a concordant prior.**

1. It agrees with a disposition already taken locally (`:4539`), so it changes nothing and cannot be
   used to "justify" that disposition — the G2 rejection rests on local negative/conditional history,
   not on a vendor post. Citing the blog as the reason would invert the evidence order.
2. It does not transfer by unit-of-work: TKCC's loop searches a **serving-engine configuration**
   (TP/EP/DCP layout, engine restart overhead, traffic drift, `tc.md:301-304`), on multi-node
   B200/B300/GB300/MI355X/Trainium2. EPYC's unit is a **source-change kernel cell** on one gfx90a
   node (plus CPU decode, DS41/INF-77), admitted through the change_class schema. The overhead TKCC
   removes (467/761 s engine launch) has no counterpart in our loop, whose per-candidate cost is a
   build plus a benchmark run.
3. There is **no gfx90a datapoint in either document**. The paper's AMD evidence is MI350X/MI355X and
   a GLM 5.3 campaign (`tc.md:1742-1748, 1616`). MI210 is untested, so nothing here is a measurement
   about our hardware.
4. The one sentence with genuine local signal is the AMD megakernel-agent result
   (`tc.md:1616`) — a 24-hour search for 0.22 % — and it is about *agent-driven megakernel formation
   on AMD*, which is closer to our loop than to a serving engine. It is a paper datum (intake-2643),
   not a blog datum, and it reinforces rather than creates a decision.

## 6. Derived actionables ledger

| ID | Action | Class | Why |
|---|---|---|---|
| **TB-1** | **Do not use the 467 s / 9.0 s table** as a startup breakdown, comparator, or motivation anywhere in the project. If startup overhead is ever cited, cite the paper's attributed Table 1(a) (761 s, MiniMax-M3.1-Flash/TRT-LLM) **with its 5 s row/total gap disclosed**. | DECLINE (knowledge-only) | Unattributed, disjoint from the paper's taxonomy, irreconcilable row-by-row (A). Our own cold start is a llama-server launch from the v10 kernel store, seconds not minutes — different regime entirely. |
| **TB-2** | **Do not open a row for the persistent-engine / "252× throughput" idea from this entry.** It is the paper's mechanism (intake-2643) and its local transfer is the *churn/warm-worker* question, which already has an owner in the 2643 dive. | DECLINE (duplicate) | The blog adds no mechanism detail beyond the paper; a second row would be the "second row for one handoff" defect. |
| **TB-3** | **Record the megakernel concession as a concordant external prior, and do nothing else.** No index row, no edit to `autokernel-loop.md:4539`, nothing to prune (the G2 row already carries the rejection). | KNOWLEDGE-ONLY | The local rejection predates it and rests on local history; the vendor post cannot be its justification (D.1). |
| **TB-4** | **Do not adopt** "trillions of tokens today", "limited beta today", "InferenceX SOTA 1111/1205 TPS", or the Groq/Vera-Rubin roadmap as any kind of comparator or capability claim for EPYC. | DECLINE | Vendor self-report, no artifact, no hardware attribution on the TPS numbers, hardware absent from our fleet (D.3). |
| **TB-5** | **Methodology note for Stage-3:** when a vendor ships a blog + paper pair, the blog's numeric tables are *not* the paper's tables (here 467 vs 761) and must not be reconciled by assumption. Any Stage-3 packet must cite the paper table or nothing. | OBSERVATION (no task) | A (finding 2–3). Cheap to state, prevents a wrong citation in a later packet. |
| **TB-6** | **Bookkeeping:** the entry bundles two URLs; claim 3 is only checkable at `polymorphic-inference.html`. Stage-3 should record both URLs against intake-2644 (or split claim 3's citation). | OBSERVATION (Stage-3 housekeeping) | Section 0. Not performed here — lane writes are the owning session's call. |

Net: **zero adoption.** Six actionables, five of which are declines or observations. Nothing here
changes a measurement plan, a kernel cell, or a handoff row.

## 7. Surfaced sources

None new. Both URLs were already in the entry; the paper is already intake-2643. One *targeted read*
is worth handing to the 2643 owner rather than duplicating here: `tc.md:1600-1760` (AMD MI350X/MI355X
and Trainium2 sections) is the only place either document discusses AMD behaviour, and the
`megakernel agent → 0.22 %` line lives there.

## Appendix A — full quote digests (strings verified present before hashing)

| key | quote (whitespace-normalised) | quote_sha256 | found in |
|---|---|---|---|
| q1_table | the 467 s row set | `a9d85c257e9d7db06ec875210728eb8b622ac1d1a2ee3aa2f04c339b28d7675e` | blog |
| q1_caption | `Table 1: Engine startup is expensive` | `26fbabc11a183b553b297516e0884f9420030d672c7487fd43e94abd726aff9e` | blog |
| q2_mech | heading 1 | `9869d5809e97819e286deadf9a91943cf2e9c7da66eb25c746e662d7414ec6a6` | blog |
| q2_tier | fast/slow engines | `56f88e1be610a732f589c77b9384dc38cd9d7c6fb93ad7e27307b155c5cb15bc` | blog |
| q2_cost | heading 3 | `b42fbc63ffcb7de01cdea1485a8ceac1bd588f54a27846e691f0d4f6e6016f43` | blog |
| q3_poly | megakernel concession | `cf3c84607936e75c08edd05c671546b04d1b181987215a3c050b8a60586b5528` | poly |
| q3_prior | "nearly two years ago…" | `f89af53f236749f1ff5016df0fbef67f0ec994bb9331151b562f8b33e8cfd379` | poly |
| qB_blog1.7 | 1.7× over megakernels | `1bbdd5f80e3eda42a6ac067efd49078ed326085d5d6571dd5e2d8f3eeddf2f17` | blog |
| qB_paperamd | 24 h → 0.22 % on AMD GLM 5.3 | `50e4fabead90a16fe1e6288531a3c5d21ee2a6170d9cdc8899ad1a36a581548d` | tc |
| qB_papertrainium | whole-decoder-layer fusion on Trainium2 | `71b65ea5d46c0c43743910f1deaa566bb6c11452d105491b2e2eeb866405c05b` | tc |
| qC_general | general-purpose compiler outside LLM | `c25c4e596f768bb94016bc7e1bd66e65f5c3626f301bf39101dc538b103b2675` | blog |
| qC_beta | limited beta | `8720d8f3f980e7eb40eb04748ea2689c5b3067fe181e448099102ee7e9fdbd11` | poly |
| qC_prodrow | production endpoints | `5146a2434081ccc6245447356a0e9e3d7b97936485b4b63c06666f6f48786f1c` | poly |
| qA_papertable | Table 1(a) rows to 761 s | `b599275347fa4cf27e890a7f18bb29885ee514746d1482370241165ce0fae58d` | tc |
| qA_attr | "MiniMax-M3.1-Flash on TensorRT-LLM" | `b5f009013d4476b69fa574223a7d5850886a93c7232f94697e3e269056ef314e` | tc |
| qA_tierstats | Table 1(b) tier stats | `b17f1095af7d0667f534029cbff886c1afd30d77a385b71b8471147dace8c9be` | tc |
| qA_252 | 252× / 11× idling | `57218fc02c40db2ba743e06a9e57197eeb76e64a945f219481d695acdb73bf82` | tc |
| qD_g2 | G2 megakernel rejection row | `2136bdc2e3de5543802c1fe4994459b24101d6c7a5572ddeba801f8577109de7` | lane `autokernel-loop.md:4539` |

Recompute any digest with:

```bash
python3 - <<'PY'
import hashlib
q = "...paste the normalised quote..."   # whitespace runs collapsed to one space, no trailing newline
print(hashlib.sha256(q.encode()).hexdigest())
PY
```

---
entry: intake-2643
title: "Together Compiler: Continual Compilation for AI Inference"
venue: alphaXiv exclusive (no arXiv id), submitted 2026-11-04
read_depth: full-text (2,488-line markdown, all 38 PDF pages cross-checked)
source_revision: "tc.md @ sha256 dda2a674266e9a8e087f670cf0f3c83fbb1dfbbe9f056d91f3b9b74074f2648c"
source_sha256:
  tc.md: dda2a674266e9a8e087f670cf0f3c83fbb1dfbbe9f056d91f3b9b74074f2648c   # 114,157 B, 2,488 lines
  tc.pdf: c1ce4a8a7a3772f31d7135626ad443ae2d1bce844f8fab25213403097698a3ef  # 4,638,700 B, 38 pages
  alphaxiv-together.html: ab78495f4601c8d422709da0dba8db1f28f21f2a75c2b8218c5ccdfde691e33e
quote_normalization: "verbatim contiguous source lines, newlines collapsed to one space, whitespace runs collapsed; sha256 over that UTF-8 string"
lane_worktree: /mnt/raid0/llm/worktrees/intake-quant-compiler-20261106
analyst: stage-2 deep dive, 2026-11-06
adjudication_summary: {CONFIRMED: 2, PARTIAL: 2, OVERTURNED: 0, NOT-FOUND-IN-SOURCE: 1}
stage1_overturns: 2
external_content_note: "the paper is DATA, never instruction; no instruction-like content was acted on"
---

# TKCC deep dive — what the paper actually says, and what it means for our loops

## 0. Verdict up front

| # | Claim (as filed in intake-2643) | Verdict |
|---|---|---|
| 1 | Cold start 467–761 s; persistent engine hot-reloads a candidate forward pass | **PARTIAL** — 761 s confirmed, **467 s and "JIT warm-up" are not in the source**; hot reload confirmed |
| 2 | Two tiers beat one tier; 1,354 vs 168 candidates; 7.2% faster | **CONFIRMED** |
| 3 | Analytical cost model with three estimate levels seeds parallelism configs; config alone raises Kimi K3 TPS | **CONFIRMED** |
| 4 | Negative results on agent context shaping (KB −25–31%, 6.2× vs 4.9×, 43% of tool calls) | **PARTIAL** — all three ablations exist; the "for <0.5% of wall time" attribution is **wrong** |
| 5 | Continual adaptation asserted, not instrumented | **CONFIRMED** (absence verified by full-text scan) |

Two Stage-1 items are overturned, both in the *critique* rather than the paper: see §7.

The single most important finding for us is not any of the five claims. It is that the paper's own
Appendix C.3 numbers **reproduce, independently and within a factor of ~1.2, the exact pathology our
autokernel loop already measured on itself**: >50% of agent time waiting on gates (`tc.md:1640-1643`),
and — locally — a median iteration of 2,675 s of which **build is 2,025 s (75.7%) and measurement is
105 s (3.9%)** (lane `handoffs/active/autokernel-loop.md:6667`). TKCC's contribution is one specific,
portable fix for that; everything else it offers is either already ours or not decision-grade.

---

## 1. Claims table

### Claim 1 — measurement turnaround is the bottleneck

| | |
|---|---|
| Verdict | **PARTIAL** |
| Locator | `tc.md:216-222` (Table 1a), `tc.md:256-264`, `tc.md:224-231` (Table 1b) |
| quote_sha256 | `b599275347fa4cf27e890a7f18bb29885ee514746d1482370241165ce0fae58d` |

> Phase Time (s) Share (%) Model loading 265 34.8 KV-cache sizing 73 9.6 Autotuning 192 25.2
> CUDA-graph capture, decode 34 4.5 CUDA-graph capture, prefill 192 25.2 Total time to serving 761 100.0

What is **confirmed**: engine startup is minutes, and it decomposes into weight load (34.8%), KV-cache
sizing (9.6%), autotuning (25.2%) and graph capture (29.7%); the total is **761 s**, on
**MiniMax-M3.1-Flash / TensorRT-LLM** (Table 1 caption, `tc.md:232-233`). The paper also says
">ten minutes of inference engine startup time" (`tc.md:211`). The decoupling claim is explicit and
mechanically specific:

> Persistent engine with hot reloading. We observe that engine launch and teardown can be decoupled from
> model forward pass execution. (…) we build a persistent engine that can run different forward pass
> variants without restarting the engine. — `tc.md:256-260`, quote_sha256 `7fba9fafeb661d968c51bab9646b9b8e577e895cfce025dc36a478d37f926822`

> When an agent submits its candidate as a "job" to the endpoint, the server replaces the model's forward
> function pointer and re-captures CUDA/HIP graphs. — `tc.md:262-264`, quote_sha256 `880ffb7db17b8cf0e21440b75d65103e3ddbea64cf31552fe1cf9df5786f5918`

What is **not in the source**: the string `467` occurs **zero** times in the 2,488-line markdown and
**zero** times in text extracted from all 38 PDF pages; `JIT` likewise occurs zero times. There is a
**single** total (761 s) and there is no JIT-warm-up row in Table 1a. The lower bound of the filed range
is an artefact of Stage 1, not a second measurement. (Consistent candidates exist — "startup to first
job 11 min" slow / "3 min" fast — but neither is 467 s.)

Three secondary numeric claims are also confirmed and worth keeping: **252×** more agent experiments and
**11×** lower idling vs restart-per-measurement (`tc.md:258-260`), and **2.6×** lower measurement latency
from prefix-cache reuse on Kimi K3 (`tc.md:266-269`, `tc.md:280`).

### Claim 2 — two tiers dominate one tier

| | |
|---|---|
| Verdict | **CONFIRMED** |
| Locator | `tc.md:292-293` (result), `tc.md:286-291` (mechanism), `tc.md:224-231` (tier stats), Fig. 2 caption `tc.md:278-279` |
| quote_sha256 | `5e4b224e896a1b436f6307d12710e8950e3ee79701e18e4f048caeb863f25847` |

> In Figure 2, we show the two-tiered measurement system evaluates 8.1× more candidates than a single
> slow tier (1,354 vs. 168) and finds a solution that is 7.2% faster.

Confirmed exactly as filed, including the model: Figure 2's caption names "B200 GLM 5.3 optimization".
1,354/168 = 8.06, matching the stated 8.1×. The mechanism stated for why the fast tier exists is
**crash and hang absorption**, not speed:

> Agents submit to the faster tier to weed out slower kernels that could cause illegal memory accesses
> (IMAs) or hangs to avoid expensive engine restarts (…). Slower tiers contain more layers (Table 1b)
> and provide higher-fidelity measurements for data-dependent architectures. — `tc.md:286-293`, quote_sha256 `8e5184a0488cdc1954235dd94f8b61255e3d84d88415e1ba10427fc41721d831`

**Caveat the filed claim omits**: this is a single trajectory comparison with no repeats, no error bars
and no second seed. By our own `MEASUREMENT_POLICY.md:9` it is an **observation**, usable for a
hypothesis, not for a keep decision. The paper never states how many repeats any candidate measurement
used.

### Claim 3 — analytical cost model seeds the parallelism search

| | |
|---|---|
| Verdict | **CONFIRMED** |
| Locator | `tc.md:350-356` (three levels), `tc.md:387-449` (model), App. D `tc.md:1768-2488`, result `tc.md:461` + `tc.md:511` |
| quote_sha256 | `f96402aeea1778080316a7c7350aee5d667012eeeb42d7ac10574421ea9ed808` |

> We therefore distinguish between three levels of performance estimates: theoretical hardware
> specifications, measured compute/memory/collective performance, and measured end-to-end forward-pass
> performance. Comparing these estimates helps distinguish hardware limitations from software
> implementation overheads.

> that boosted TPS by up to 24% and TPM by up to 18%. — `tc.md:511`, quote_sha256 `fabcd80ff9a0141890641136ffd8836e624060fa0a4bfc43fc64230bfa7e4dab`

The three levels are real and are tabulated as four swappable spec sources (theoretical / own micro /
vendor tool / vendor library, `tc.md:2481-2488`). The model is roofline per layer plus collectives plus
an SLA-constrained concurrency solve (`tc.md:1882-1941`), pruned to admissible schemes (App. D.1-D.3).
The "configuration alone" claim is confirmed for Kimi K3 at 24% TPS / 18% TPM — with the honest caveat
that this is **Together's own production deployment**, so it is a vendor self-report with no baseline
detail in the paper.

One mechanism detail worth noting because it is *not* a grid search and *not* a learned model: they
enumerate, prune by divisibility + SLA, score analytically, and keep top-k lowest chip-seconds, tie-broken
by fewest chips (`tc.md:1944-1946`). It is a **screening heuristic**, not the "cost model" of the
appendix-C ablation.

### Claim 4 — measured negative results on agent context shaping

| | |
|---|---|
| Verdict | **PARTIAL** |
| Locator | `tc.md:553-555`; `tc.md:1617-1619`; `tc.md:560-562` + `tc.md:1630-1633` |
| quote_sha256 | KB `bc5da62f07e95fc2e7e782fac136920a08b7e1b62273946ae16214281d30500e`; ensemble `ba723e190e08b8767ab5d82c87f5585665dd335c90a4c9ab42a801322e710615`; tool-calls `075a2a0af0c7d9ef24edce60417e7d1a3315cf2ddb2d3836bc8abd8ba24adec9`; time `acb9578180fcc614933f1cbe3656547b6b2c1093bf4c957a588b79cdf412816a` |

> Knowledge hub. (…) this approach can lead to 25–31% lower speedup than agent performance without a
> knowledge hub after 12 hours of optimization (Figure 5a).

> In Figure 5b, we see that ensembling naive agents outperforms distinct expert strategies (6.2× vs. 4.9×
> after 10 trials), and that a single naive agent beats every prescribed strategy alone (4.8× vs. 3.1–4.5×).

> Agents spend up to 43% of the CLI/tool calls per trial on research tracking and data structure inspection

> agents spend 8% of time on bookkeeping (…) (∼12.6 seconds per call, since each call starts a new Python
> process), compared to < 0.5% of time on bookkeeping when we run without our logging data structure.

**The conflation to correct**: the filed claim reads "43% of tool calls **for <0.5% of wall time**". Those
are two different measurements of two different arms. With the graph: 43% of *tool calls*, 8% of *time*.
Without the graph (plain Markdown): <0.5% of *time* (tool-call share for that arm is not given). The
comparison "43% of calls buys <0.5% of time" is not in the paper and would be wrong; the correct reading
is "8% of wall time with the graph vs <0.5% without", i.e. a **~16× bookkeeping-time penalty**, plus a
large call-count share. Directionally the same conclusion, one order of magnitude different in
severity-of-framing.

### Claim 5 — continual adaptation is asserted, not instrumented

| | |
|---|---|
| Verdict | **CONFIRMED** (as an absence) |
| Locator | `tc.md:249-251`, `tc.md:52`, `tc.md:785-788` |
| quote_sha256 | `cfc79f592584afbd26347502ed54734f3d268a5f3b492698e750d908f48a7527` |

> TKCC perpetually loops until a given budget is exhausted, at which point we run a full suite of
> verification tests (e.g., for KV cache contamination and quality) (…)

Full-text counts: `drift` **1** (the Figure 1 label "traffic drifts → recompile", `tc.md:52`),
`threshold` 2 (both in the cost model's SLA pruning), `trigger` **0**, `monitor` **0**, `detect` **0**,
`converge` **0**, `canary` 0. There is no drift detector, no statistic, no threshold, no recompile
policy, no re-convergence time, and no measurement of the old configuration degrading. The closest thing
to a continual mechanism is a **hand-noticed batch-size effect**:

> On Kimi K3, optimizations such as a persistent MoE down-projection boosts performance by 2.8-5% across
> concurrencies 22-78 but is 6.6% slower at concurrency 8. TKCC recognizes this and selectively applies
> optimizations based on the active batch size. — `tc.md:786-788`, quote_sha256 `4ed864c07a4c42789001127013903a78822444d66b33b5fdf45ee09b120abc5e`

That is dispatch-time selection at serving, not a compilation-loop control law. "Continual" in this paper
means "the loop can be re-run cheaply because startup is amortised", which is a **capability**, not a
**controller**. The headline numbers remain vendor self-reports: no artifact release, no independent
replication, baselines from a 2026-10-27 snapshot, and the only protocol check is internal
("we rerun it on InferenceX's published engine configurations and locally confirmed that it reproduces
the published throughput exactly", `tc.md:1103-1105`).

---

## 2. A — the mutate surface, hot reload, and the tier definitions

### A.1 Mutate surface

Two layers, and the distinction matters for us:

1. **Per-candidate surface (the hot-reload contract)**: a single Python file, `tkcc_forward.py`, exposing
   `forward(model, input_ids, positions)` that delegates to `optimized_forward(...)` (`tc.md:312-318`,
   Figure 3). The agent posts it over RPC as a "job".
2. **Search surface (what agents actually edit)**: the inference engine's **source code**, with no
   abstraction between the agent and it — "TKCC now directly provides the agent with the inference
   engine's source code and no explicit context management structures or curated strategies"
   (`tc.md:532-535`). Appendix A.1 pins the boundary: "The edit surface is kernel and forward pass
   changes **without allowing any quantization**" (`tc.md:1076-1077`, quote_sha256
   `df401576bba4bab480c710b0ed60edca854d6c957813dd5c28ccf07bbba43cbd`).

So: engine source + kernel source + the forward pass; **quantization is excluded**; and the surface is
**revocable by policy** — after two agent crashes the harness banned edits to the recorded GPU-step
sequence, which killed improvements that depended on it (`tc.md:1762-1765`). That is a real, and for us
familiar, property: the most productive edit class was the one that had to be fenced.

### A.2 What hot reload does, and does not, touch

| State | Effect of `hot_reload` | Evidence |
|---|---|---|
| **Weights** | **Untouched.** The engine is initialised once and never reloaded; this is the entire premise. | `tc.md:244-246` |
| **KV cache** | **Untouched and reused.** A *fixed request set* is reused so prompts stay cached; worth 2.6× latency on Kimi K3. KV contamination is checked only in the **final** verification suite. | `tc.md:266-269`, `tc.md:249-251` |
| **Autotune state** | **Not described.** Autotuning (192 s) happens once at cold start; the paper never says whether it is reused, invalidated, or re-run per candidate. | `tc.md:219` + absence |
| **CUDA/HIP graphs** | **Recaptured on every load and every teardown.** | `tc.md:263-264`, `tc.md:327-330` |
| **Kernel modules** | **Unloaded** at teardown, baseline forward pointer restored, graphs recaptured. | `tc.md:328-330` |

Mechanically, per rank: write file to `/tmp/forward.py` → `exec_file` → `model.forward = candidate.forward`
→ `recapture_cuda_graphs()` (`tc.md:322-327`). That is the whole "compiler": a function-pointer patch plus
a graph recapture. The cost of one reload is **17 s (fast tier) / 45 s (slow tier)** — so "minimal
overhead" is 17-45 s, not milliseconds, and it is ~4-6% of a slow-tier job (`tc.md:224-231`).

**The gap I would flag first as a reader**: reusing a fixed request set means the KV cache is populated
by *previous candidates'* code. If a candidate changes attention layout, KV dtype handling, or cache
indexing, the measurement is reading a cache the current candidate did not write. The paper tests for
"KV cache contamination" only at the end of a run, after every comparison has been made. Either every
measured comparison is contaminated, or the reuse is restricted to non-KV-touching candidates — and the
paper does not say which. For our loop this is the difference between a valid and an invalid A/B.

### A.3 Tier definitions, and the variance/crash rates

Table 1b (`tc.md:224-231`), MiniMax-M3.1-Flash, TensorRT-LLM:

| Metric | Slow tier | Fast tier |
|---|---|---|
| Layers served | 60 (100%) | 12 (20%) |
| Startup to first job | 11 min | 3 min |
| Hot reload | 45 s | 17 s |
| Job completion, median | 64 s | 28 s |
| Measurement variance | 0.14% | 0.05% |
| Crashes per 1,000 jobs | 0 | 3.9 |

Three things to read carefully:

1. **The fast tier has *lower* variance than the slow tier** (0.05% vs 0.14%). That is the opposite of
   the usual fidelity story and the paper does not comment on it. The likely explanation is that a
   12-layer job is shorter and less exposed to clock/thermal drift and to co-tenant noise — not that it
   is more faithful. It means the fast tier's *precision* is not the problem; its *bias* is untested.
2. **The layer count is tuned, not fixed**: "Before optimization starts, we tune the minimal number of
   layers needed for representative measurements for that particular workload" (`tc.md:298-300`).
   The method, the criterion and what "representative" means are **absent**. Which 12 of 60 layers is
   also absent.
3. **Crash absorption is real but small**: 3.9 per 1,000 = ~0.4%, i.e. ~5 crashes in the 1,354-candidate
   run. Elsewhere the failure mode is worse than a crash: illegal memory accesses put GPUs into a state
   needing a **full reset** (Xid 154), **9 times** during GLM 5.3, and **2 machines were removed from the
   cluster** (`tc.md:1724-1727`, quote_sha256 `e96d1f8d5d4d3143515c80322b3d84cd450b34628b9346e5d6fc9674d0717e29`).
   A tier that "absorbs crashes" in the paper's accounting did not absorb those; the cluster lost nodes.

Also relevant to the variance story: back-to-back runs of the *same* forward pass vary by **4-6%**, which
they reduce to 2.7% by splitting prefill from decode (`tc.md:294-298`, quote_sha256
`4770f3991932fb7a0d0197d7c3316a8438add814dd0f00e5721cce7da06e38f5`). Note the tension with Table 1b's
0.14%/0.05%: the 4-6% figure is the raw engine, the table's numbers are after their variance reduction.
The paper never reconciles the two, and the 1% smallest-useful-effect statement is the reason it matters.

---

## 3. B — the keep/discard decision

Short answer: **the paper does not describe a keep decision.** It describes a budget and a final audit.

| Question | What the paper says | Verdict |
|---|---|---|
| Metric | "the signal given to the agent was decode TPS" (App. A.1, `tc.md:1077-1078`); headline metrics are InferenceX throughput-per-GPU and 1/P90 inter-token latency (`tc.md:1098-1101`) | Stated |
| Repeats per candidate | **Never stated.** No n, no reps, no CI, no seed count anywhere in the paper | **ABSENT** |
| Stopping rule | "repeat until budget" (Fig. 1, `tc.md:80`); "TKCC perpetually loops until a given budget is exhausted" (`tc.md:249`) | **Budget only** — no statistical stop, no per-candidate rule |
| Comparison rule | Implicit: the best measured candidate wins. Two-tier logic is "fast weeds out, slow decides" (`tc.md:286-291`) but the decision statistic and its uncertainty are not given | **ABSENT** |
| Verification before serving | One sentence: "a full suite of verification tests (e.g., for KV cache contamination and quality)" (`tc.md:249-251`) | **Named, not enumerated** for LM serving. For the 8 non-LM models, App. B Table 5 does enumerate bit-exactness suites (`tc.md:1279-1313`) |
| Per-candidate rollback | **Yes, at the pointer level**: `teardown()` restores the baseline forward, unloads modules, recaptures graphs (`tc.md:328-330`). No rollback of a candidate that passed the suite and later regressed in production | **Partial** |

Compare our own discipline, which is stricter on every axis that matters:

- Metric + protocol + n/reps + date are mandatory for a decision number, else it is an observation
  (lane `agents/shared/MEASUREMENT_POLICY.md:9`).
- Reps: **≥5 for ≥5% claims, ≥10 for ≤2% claims** (`MEASUREMENT_POLICY.md:57`); **N ≥ 100/arm** for
  production-role decisions (`:60`); **floors calibrated at n ≥ 24** with a declared unit
  (`:106-114`).
- A pre-registered stop contract before every run (`:55`; `docs/guides/agent-workflows/measurement-sufficiency.md:8`),
  with formal-gate cells futility-only at interim looks (`measurement-sufficiency.md:27`).
- Keep gate: 20 matched randomised pairs with a calibrated A/A floor and a CI rule, e.g. the
  C6 re-measure row (lane `handoffs/active/kernel-champion-and-promotion.md:218`: "4 chunks x 7 matched
  randomised pairs, first pair per chunk discarded, 24 kept pairs (…) 2.05 % MDE at 80 %", with
  REGRESSION / NO_REGRESSION_2PCT / INCONCLUSIVE decided on the CI).
- Rollback: stronger than the paper's — T4 recommends rollback to the operator
  (`handoffs/active/autokernel-loop.md:2306`), the kernel set has a named rollback anchor (CLAUDE.md v9),
  and the role applicator rolls back to prior config on a failed health gate
  (`handoffs/active/stack-lifecycle-program.md:401`).

So on **B, our loop is already better than TKCC**, and "adopt TKCC's keep gate" is a non-action. What
TKCC has that we do not is the *cost* of getting to the gate, not the *quality* of it.

---

## 4. C — what the context ablations actually measure

**What was measured.** Figure 5 (`tc.md:509-510`): one setting — **MiniMax-M3 layer 3, B200 TP4, batch
size 1, TensorRT-LLM** — x-axis trial number 0-10, y-axis "speedup over stock", trajectory endpoints.
So: a single layer, a single GPU topology, a single batch size, **10 trials**, one seed, no error bars,
no repeated runs. The three panels:

- (a) Single strategy vs ensemble, with and without a knowledge base. Result: KB costs **25-31%** after
  12 h; caption says "can incur 26% worse performance".
- (b) 6 distinct expert strategies vs ensemble vs naive ensemble. Result: **6.2× vs 4.9×**; a single
  naive agent beats every single prescribed strategy (**4.8× vs 3.1-4.5×**); caption: "Expert-tuned
  ensembling is 1.3× slower than naive strategies".
- (c) High-frequency vs low-frequency vs no agent communication. Result: **4.7× faster** with high
  frequency; separately "improving optimization speed by 2.3×" (`tc.md:285`).

**The paper's explanation** (three distinct causal stories, and they are not the same story):

1. **The KB is a search cost, not a knowledge deficit**: "agents often wasted time finding relevant
   kernels and ideas they could reuse, whereas without a knowledge base similar performing kernels or
   strategies were achieved independently in a shorter period of time" (`tc.md:1579-1582`, quote_sha256
   `527547aed13fe82e38a5ea0d97af3d3afc9a1654f4b065c989feb4d2b6b713e0`). The KB was not wrong; it was
   *expensive to navigate*. Its structure — Markdown + YAML + typed links, graph-navigated
   (`tc.md:1577-1579`) — is almost exactly our handoff/wiki shape, which is uncomfortable.
2. **Prescribed strategies truncate the search**: "Fixed strategies cannot represent a dynamically
   changing environment, and constraining a prescribed order ahead of time forces agents to explore less
   optimal paths" (`tc.md:1614-1617`). Worked example: the megakernel agent spent **24 h to reach 0.22%**
   on AMD GLM 5.3.
3. **Prescribed IRs cap the ceiling, not the speed**: "Even our heavily endowed augmented Inductor IR was
   not expressive enough to permit certain optimizations" — the MLA metadata kernel needed host-side
   metadata mutation that neither FX graph could express, worth 1.7-2.5× on that kernel
   (`tc.md:542-547`, quote_sha256 `7a5a7c2f582c16a627a1e82daad57c20632c2f144ece180af1ba08cf741dfd95`).
   Their own qualifier is important and usually dropped: "while we find that prescriptive IRs can
   constrain agent optimization, structured representations can be valuable when **verifying** the
   correctness of compiled programs" (`tc.md:564-567`). IR-as-verifier survives; IR-as-guide does not.

**The uncomfortable part for us.** The strategy they ablated away as a loser is, almost verbatim, our
measurement discipline:

> • Cost Model: Treat benchmark submissions as the scarce resource. First measure the instrument's
> resolvable effect size E, and build a wall-time ledger that includes idle time and unexplained ("dark")
> time. Then try to refute each candidate before spending a submission on it (…). Submit only candidates
> whose estimated ceiling exceeds 2E. — `tc.md:1605-1611`, quote_sha256 `e4fbe1a4d1887733d869ab8b4876f5500e2e8b41bbe0641bcddcedb49161c5f7`

That is `MEASUREMENT_POLICY.md:55-57` and `measurement-sufficiency.md:8` in one paragraph. It appears in
their list of *expert strategies that lost*. Held against our own rules, though, their evidence for that
loss is **observation-grade** (n=1 trajectory, 10 trials, no CI) and therefore cannot gate a design
change here. The honest read is: *a hypothesis worth one bounded probe*, not a mandate to delete the
critic.

---

## 5. D — what is absent

| Item | Status | Evidence |
|---|---|---|
| **Drift detector** | **Absent.** One word "drift" in the whole paper, in a figure label. No statistic, no window, no baseline. | `tc.md:52`; counts in §1 claim 5 |
| **Recompile trigger / threshold** | **Absent.** No policy for when to re-run the loop; the only terminator is a budget. | `tc.md:249-251` |
| **Re-convergence measurement** | **Absent.** No measurement of how long a new configuration takes to beat the old one, or of the old one's degradation curve. The Kimi K3 batch-size example is a hand-observed crossover, not a re-convergence trace. | `tc.md:785-788` |
| **Cost / token accounting for agents** | **Partial.** Time shares per phase (Table 6: 52.7-57.0% waiting on gates), and Figure 14's caption says the experiment graph showed "the dollars spent per trial" (`tc.md:1665-1666`, quote_sha256 `e97d463c2efbd6092cfc43f5d8fa5196084c70df9c730de5e6ea32ffef071ca3`). **No token counts, no $ per speedup, no $/candidate.** | `tc.md:1644-1649`, `tc.md:1665-1666` |
| **Independent replication** | **Absent.** All 12 authors are Together AI Research. The only reproduction is internal, against InferenceX's published configs, "to within about 2%" on P90 interactivity (`tc.md:1103-1105`). No artifact, no third-party run. | `tc.md:1-9`, `tc.md:1102-1105` |
| **Single-GPU / single-accelerator scale** | **Mixed.** *Tiering and persistent-engine* claims are all multi-GPU (TP4 B200, 8×H100 in Fig. 1) and no single-device tiering result exists. But §5.1's Llama-1B batch-1 table reports **2,118 TPS on B200 / 1,137 on H100** (`tc.md:635-661`), which are single-accelerator numbers by construction — the paper simply never states the device count. **MI210/gfx90a is not tested at all.** | `tc.md:635-661`, `tc.md:663`; no gfx90a string |
| Also absent (not asked, worth knowing) | Sample-size or CI on **any** result; the layer-selection method for the fast tier; whether autotune state survives reload; any statement of per-candidate wall cost; a released harness. | full text |

Two further absence-adjacent hazards for anyone reusing these numbers:

- The **2.6×** is an "up to" over 4 models × 5 platforms against a 2026-10-27 snapshot, with a 24-hour
  compilation window per setting and 2× the replica size of compute (`tc.md:673-680`) — so the cost side
  of the trade is a doubling of serving hardware during compilation, never converted to dollars.
- The **Llama-1B 1.7×** claim compares against megakernels *without* megakernel abstractions, and the
  paper attributes the gain to driver primitives rather than the compiler: "driver-level primitives such
  as PDL, CUDA graphs, and L2 prefetching are able to recover the benefits of a single persistent kernel"
  (`tc.md:667-669`).

---

## 6. Mapping to our loops

### M1 — which TKCC mechanism already exists here, and which is genuinely missing

| TKCC mechanism | Ours | Where | Verdict |
|---|---|---|---|
| **Tiered measurement** (fast screens, slow decides) | **T0 correctness/build → T1 search → T2 lineage → T3 freeze → T4 post-cutover** | lane `handoffs/active/autokernel-loop.md:2298-2306`; rationale `:4215` ("T0/T1/T2 are separate cheaper research tiers"); discovery/confirmation split `:4245` (AK-D40) | **EXISTS — but tiered by *evaluation scope*, not by *layers***. Our T1 is an op/tiny-graph microbench, TKCC's is 12 of 60 layers of the real engine. Different object; same idea. |
| **Persistent engine + hot reload** | Nothing. Closest is `restart_role()` — which deliberately **restarts** the role, health-gates, and **rolls back** on failure | lane `handoffs/active/stack-lifecycle-program.md:401` | **MISSING.** This is the one genuine transfer. |
| **Cost model seeds the config search** | Surrogate/analytical pre-screen is **dormant**; contention matrix is a placement model, not a throughput model | `handoffs/active/autokernel-loop.md:5794` (AK-RI-SURROGATE-1, "Dormant, not blocked"); `:4245` (AK-D40 ranks top-K then confirms) | **PARTIAL / dormant.** Also mostly out of scope: we do not search TP/EP/CP layouts on one MI210. |
| **Prefix-cache reuse of a fixed request set** | We treat cache state as a **hazard to hold fixed**, not an optimisation to exploit | `handoffs/active/autokernel-loop.md:5087` (`cache_state: warm\|cold` bound into the recipe); `:2666` (warm-cache gaming is a named threat) | **OPPOSITE POLES.** They exploit it for speed; we fence it for validity. Do not import this one. |
| **Binary / kernel reuse** | Kernel **store** exists (content-addressed builds under `/mnt/raid0/llm/kernels/builds/`), but the loop does not consult it before building | `handoffs/active/autokernel-loop.md:6668`: "44 of 51 compiled a byte-identical tree — `build_key` hashes `patch_sha256`, which the anchor does not depend on" | **MISSING IN PRACTICE, infrastructure already there.** Cheapest win on this page. |
| **Crash absorption in a throwaway tier** | T0 gates correctness before timing; device claims + KFD/VRAM witnesses; Xid-class failures are a known local hazard | `handoffs/active/autokernel-loop.md:2302`; claim discipline `agents/shared/MEASUREMENT_POLICY.md:58` | **PARTIAL.** We prevent rather than absorb; the paper's own 9 Xid-154 resets show absorption did not work there either. |

**The one-line answer to M1**: the *tier* concept is already ours and is finer-grained than theirs; the
*persistent warm engine* is genuinely missing; and the *binary-reuse* half of their optimisation is a bug
we already measured on ourselves (44/51 identical rebuilds) with the fix already half-built (the kernel
store).

### M2 — does the anti-planner result apply to our autokernel loop?

**No, not directly. The decompositions are different, and saying otherwise would be a category error.**

What their ablation actually compared (`tc.md:1583-1619`, App. C.2.1 `tc.md:1583-1612`): **six parallel
agents, each assigned a different expert-written optimisation objective** — Quick wins, Fusion,
Reduction, Communication/compute overlap, Megakernel, Cost Model — **versus six parallel agents all given
one sentence** ("make this forward pass as fast as possible"). Same model, same harness, same layer, 10
trials. It ablates **role specialisation among peers**. It does *not* contain:
- a planner that must choose *what to attack* from a profile;
- a critic that can refuse a proposal before any compute is spent;
- a staged pipeline where the planner never writes code;
- a negative-memory ledger (their KB is positive knowledge, not a do-not-repeat set).

Our loop is decomposed **by stage**, not by role: planner → critic → author → gate → measure, with the
planner's context assembled from a profile, an inbox of seeds, and a deterministic do-not-repeat fold
(lane `handoffs/active/autokernel-loop.md:5725` "the planner's memory is the deterministic
do-not-repeat fold"; funnel `:6661`: 660 intents → 567 `planner_transient` → 91 pre-screen → 17 measured
→ 0 promoted).

So the paper falsifies a claim we do not make ("assign each parallel agent a different expert strategy").
What **does** transfer, and is worth one probe each:

1. **The cost-model strategy lost.** That strategy *is* our gate philosophy (§4). Their evidence is
   observation-grade, so the correct action is a probe on our own data, not a redesign.
2. **Positive knowledge bases can cost more than they give.** Our analogue is the rendered context and
   the inbox seeds, and we already have a local measurement pointing the same way: under recency recall,
   **81.2% of planner calls showed zero measured answers** in the "Already tried" window, and ranked
   recall cut that to 1.6% while shrinking the section 8,011 → 6,770 chars
   (`handoffs/active/autokernel-loop.md:5730`, `:5732`). Two independent systems, same finding: **the
   context was expensive to navigate and mostly did not contain answers.** That convergence is the
   strongest reason to take the context result seriously.
3. **The critic is not tested by them at all.** Their naive agents have no refusal stage; our critic is
   83 refusals outbidding completed measurements 4.9:1 (`:6662`). That ratio is *also* a warning in the
   opposite direction — a critic that refuses 4.9× more often than it measures is a throughput tax — but
   the paper gives no evidence either way on refusals.

**Verdict on M2**: decomposition differs; the anti-strategy result applies to *role-specialised parallel
fan-out*, which is the pattern our own `OPERATING_CONSTRAINTS.md` already warns about ("decomposition by
ROLE — a measured anti-pattern"). The paper is, on this point, **corroborating a rule we already have**,
not overturning one. The anti-KB result is the one that bites, and we have already acted on it once.

### M3 — "decouple setup from measurement" for the churn pipeline, today

**What it would mean concretely.** Today a queued row pays, in order: `publish_row` (spec + launcher) →
**dry run through the exact launcher on the real lane under a real claim** → PASS → arm → grant written →
admission → process start → **model load** → first measured unit → run → `.ended` → filing. Two facts make
this a setup-dominated pipeline:

- **"One grant is one run; then it waits for the next"** (lane `docs/guides/agent-workflows/compute-fillers.md:46`),
  and the dry run is a *second* full launcher execution whose PASS criterion explicitly excludes startup:
  "Startup alone never counts" (`docs/guides/agent-workflows/backlog-churn-flow.md:53`).
- The launcher polls "every 30-60 s" for its window (`compute-fillers.md:46`), so a 1,800 s job can lose
  a poll interval at each end by construction (`:106`, "A window must exceed the job's min-window by the
  poll margin").

"Decouple setup from measurement" = **one warm worker holding one grant, loading the model once, and
accepting N measurement units from a queue** — the TKCC endpoint shape — instead of one process launch
per row. The pieces we already have: `restart_role()` as the rollback-safe role primitive
(`handoffs/active/stack-lifecycle-program.md:401`), a resident-set discipline that has already measured
idle residency as **free** (`handoffs/active/numa-placement-and-contention.md:1128-1136`: "others
resident, IDLE … +0.006%"), and the explicit rule "one hot server per model (4 loads)"
(`numa…:1077-1084`, with the warning that *four* concurrent idle servers poison measurements —
`OMP_WAIT_POLICY=active` burns 47 of 48 cores). So the architecture is known-good here; what is missing
is a queue-feeding measurement unit and a grant shape that permits N units per grant.

**Is there measured local evidence that setup dominates a queued inference task? Yes — three independent
measurements.**

1. **The iteration ledger** (`handoffs/active/autokernel-loop.md:6667`): median 2,675 s =
   **build 2,025 (75.7%)** · planner 412 · critic 100 · **measured 105 (3.9%)**. Same table: `compiling,
   lifetime 29.0 h` vs `GPU held, lifetime 1.403 h` across 122 claims, mean 41.4 s (`:6665-6666`). Setup
   outweighs measurement ~20×.
2. **Model load per launch** (`docs/guides/agent-workflows/agent-loop-design.md:522-525`): on the 519 GB
   DS41 model "each launch spent ~3.5 min in a single-threaded load, and the host looked ~85% idle
   during calibration"; the fast loader cut the launch from **~282 s to 163-170 s**. Our per-launch
   load cost is 163-282 s, i.e. **21-37% of TKCC's 761 s cold start**, on one model, with no hot reload.
3. **The funnel** (`autokernel-loop.md:6661-6662`): 660 intents → 567 `planner_transient` → 91 pre-screen
   → 17 measured → 0 promoted, with 83 gate refusals. Only **2.6%** of intents ever reach a measurement.

**The honest caveat**: measurement 1 is the **pre-rebuild** split. AK-HR-1(d) says the current split
cannot be recomputed because "build seconds are needs-fields — no build or per-stage seconds on any
payload" (`autokernel-loop.md:5728`), and AK-HR-3b exists precisely to fix that (`:5741`, filed
2026-10-20, still unticked). So the *phenomenon* is established and the *current magnitude* is not.

**Cheap probe (if we wanted a fresh number)**: AK-HR-3b — add `build` and `correctness` keys to `STAGES`
in `loop/history_fields.py` and time them inside the injected gate — then re-run the read-only AK-HR-1
exporter over one closed store. One campaign iteration plus a zero-inference replay; no GPU, no grant.

### M4 — the smallest MI210 experiment that could falsify the tiering claim for us

**The claim to test** (ours, not theirs): *a cheap layer-subset screen ranks candidates the same way the
full production-recipe measurement does, at a resolution finer than the effect we care about (2%).*

**Rung 0 — the zero-compute version, which should run first.** We already have the join: 4 campaigns,
**8 judgeable screen→confirmed pairs**, faithfulness ratios 0.587, −0.060, 2.25, 26.48, 6.97, 2.05, 2.78,
−26.95, with "sign flips occur in both campaigns that have any pair"
(`handoffs/active/autokernel-loop.md:5730`, item 6). That is already a warning that our fast→slow transfer
is unproven, but n=8 cannot decide. The probe: re-run the join with **equal `candidate_diff_sha256`
strict pairing**, report Spearman ρ and **sign-agreement rate with a bootstrap CI**, over every closed
store. Cost: minutes, no GPU, no inference. If ρ's CI excludes 0.7, the tiering premise is already
supported and the GPU experiment is unnecessary. If it excludes 0.7 *on the other side*, we have
falsified our own tiering without spending a GPU-hour.

**Rung 1 — the MI210 experiment, if rung 0 is inconclusive.**

- **Question**: on one MI210, one model, does a layer-subset tier reproduce the full-tier ranking of
  already-built candidate binaries at ≤2% resolution?
- **Model / tier construction**: Qwen3.8-27B Q8_0, production recipe. Fast tier = the same GGUF with
  `--override-kv llama.block_count=int:<k>` (k≈8 of 64 layers); slow tier = full model, registered
  recipe. **Design risk to prove first**: whether llama.cpp honours a reduced `block_count` without
  loading the unused tensors. If it does not, fall back to the existing T1 op/tiny-graph microbench as
  the fast tier and say so — that is the tier we actually run today, and it is the one whose fidelity is
  in question.
- **Arms**: 6 already-built, content-proven binaries from the C6 store with *known* slow-tier effects
  spanning the range (e.g. +0.1%, +2.0%, +2.7%, −1.2%, +1.7%, −0.4%). **No new builds** — the whole point
  is to test the screen, not to generate candidates.

The six controls, explicitly:

| Control | Binding |
|---|---|
| **Baseline** | Champion `c72ec82f5` at the production recipe, same session, same claim, measured first and re-measured last (drift check). |
| **Control arm** | **A/A: champion vs champion** at *both* tiers, same n. This does double duty: it calibrates each tier's floor **and** it validates the fast-tier construction (a truncated model at k=full must reproduce the full model within floor, else the tier is not a tier). |
| **Effect size vs noise** | Target resolution **2%** (our policy threshold for "needs ≥10 reps"). Noise inputs are already measured: **arm sd 0.501%, process-launch sd 2.793%** (`MEASUREMENT_POLICY.md:109`). Note the 5.6× penalty for the launch-scoped comparison — which is exactly the kind of comparison a fast tier makes. If the fast tier's A/A floor ≥ 2%, **stop: the tier cannot screen at this scale.** |
| **Repeats** | **24 pairs per arm per tier**, 4 chunks × 6 pairs, first pair per chunk discarded (the exact shape already used in `kernel-champion-and-promotion.md:218`). n=24 is the policy floor-calibration minimum (`MEASUREMENT_POLICY.md:113`). |
| **No-confounds isolation** | `region-lock --gpu-quiet exclusive` on mi210_0; one session; interleaved AB/BA with counterbalanced order; binaries content-proven by BUILD-OK source SHA + distinct `libggml-hip` digest; VRAM sampled during every run; no co-tenant; host uptime ≤ 1 week or drop_caches + rewarm (`MEASUREMENT_POLICY.md:58`). |
| **Pre-registered stop rule** | Primary: Spearman ρ across the 6 arms, 95% bootstrap CI. **Stop-on-answer** when the CI excludes **0.7** (tiering holds) or its upper bound falls below **0.7** (tiering falsified for us). **Futility** at 12/24 pairs if the A/A floor ≥ 2%. **Cap** 12 GPU-hours, resumable per chunk. **Falsifier**: ρ < 0.7, **or** ≥2 of 6 arms with opposite sign. |

Why this is the *smallest* falsifier: it needs 6 artefacts we already built, 2 tier binaries, one GPU,
and a decision that is a rank correlation rather than an absolute claim — so it cannot be rescued by a
lucky point estimate, and a null is as informative as a win.

---

## 7. What this dive overturned in the Stage-1 read

1. **"Cold start measured at 467–761 s" — OVERTURNED.** 467 s is not in the source (0 hits in the md and
   in 38 extracted PDF pages); there is one total, 761 s. "JIT warm-up" is also not a component; the
   components are weight load, KV sizing, autotuning and graph capture. This is a Stage-1 transcription
   artefact that would have propagated into any citation.
2. **"The headline batch-1 1.8× is confounded by parallelism (TP4 baseline vs TP8 chosen)" —
   OVERTURNED by the paper's own control.** `tc.md:780-784` (quote_sha256
   `d9943405995601b386b5f88ad361019e9fe5f978858847427f6f60ca41889459`): "Running the same InferenceX
   image under TP8 achieves similar performance to the chosen TP4 result." They ran the confound control
   and it came back null, which is *better* methodology than the critique assumed. (The remaining fair
   criticism is that the TP8 *reasoning* comes from their own cost model, so config choice and code
   change are still jointly attributed — but "confounded by parallelism" as stated is refuted.)
3. **"Nothing is reported at single-GPU scale" — PARTIAL, too strong.** §5.1 reports 2,118 TPS on B200
   for Llama-1B at batch 1, which is a single-accelerator number; the paper just never states the device
   count. What is genuinely absent at single-device scale is the **tiering / persistent-engine** result,
   and MI210/gfx90a is absent entirely. The correction matters because it is the difference between "no
   single-GPU data at all" (false) and "no single-GPU tiering data" (true, and the thing M4 needs).
4. **Not overturned, but sharpened**: Stage-1's "no drift detector" is correct and stronger than stated —
   `trigger`, `monitor`, `detect`, `converge` are **zero-hit** strings across the entire paper.
5. **New, not in Stage 1**: the fixed-request-set KV-cache reuse (`tc.md:266-269`) is a *measurement
   validity* hazard the paper only checks at the end of a run; and the fast tier's variance is **lower**
   than the slow tier's (0.05% vs 0.14%), which undercuts the "fast tier is noisy" intuition and means
   the fast tier's risk is **bias, not precision**.

---

## 8. Derived actionables ledger

Dispositions: `adopt-existing` (already filed here — do not re-file), `build`, `probe`, `reject`.
Every probe is the *smallest* thing that could change the disposition.

| ID | Action | Owning handoff | Disposition | Smallest deciding probe |
|---|---|---|---|---|
| **TK-1** | Time `build` and `correctness` separately inside the injected gate, so the 75.7%/3.9% split can be replaced with a current one. | `handoffs/active/autokernel-loop.md` (AK-HR-3b, `:5741`) | **adopt-existing** (filed 2026-10-20, unticked) | One campaign iteration's `stage_seconds` + the AK-HR-1 exporter over one closed store. Zero GPU. |
| **TK-2** | Consult the kernel store before building. 44 of 51 anchor rebuilds produced a byte-identical tree because `build_key` hashes `patch_sha256`, which the anchor does not depend on. | `handoffs/active/autokernel-loop.md` (`:6668`) + `kernel-champion-and-promotion.md` | **build** (biggest setup win available; direct analogue of TKCC "binary reuse", `tc.md:280-282`) | Replay `build_key` over the 51 anchor rebuilds and count skippable builds. Zero compute; the count *is* the effect size. |
| **TK-3** | Warm measurement worker: one grant, one model load, N queued measurement units. Reuses `restart_role()` for rollback safety and the resident-set discipline. | `handoffs/active/coordination-and-churn-pipeline.md` + `stack-lifecycle-program.md:401` | **build** (needs a grant-shape change: "one grant is one run", `compute-fillers.md:46`) | Measure `published_at → first_result_unit` across the last 20 rows from rowflow/queue logs. Zero GPU; establishes the per-row setup tax. |
| **TK-4** | Enlarge and fix the screen→confirmed join (strict `candidate_diff_sha256` pairing) and report Spearman ρ + sign agreement with CI. This is rung 0 of M4. | `handoffs/active/autokernel-loop.md` (`:5730` item 6; AK-HR-1(e)) | **probe** (do this before any GPU experiment) | Re-run the join over every closed store. Minutes. If ρ CI excludes 0.7 either way, M4's GPU rung is cancelled. |
| **TK-5** | Layer-subset fast-tier fidelity experiment on MI210 (M4 rung 1), only if TK-4 is inconclusive. | `handoffs/active/kernel-champion-and-promotion.md` (keep-gate track) | **probe** (12 GPU-hours, 6 existing arms) | The pre-registered ρ test with the six controls in §6 M4. |
| **TK-6** | Keep-time cross-workload screen: a keep decided on one target must be screened against the whole served vector *before* it lands. Today required-target validation runs after the keep and "nothing refuses or reverts the keep". | `handoffs/active/kernel-champion-and-promotion.md:2939-2944`, `:2992-2994` (track is ACTIVE/STUB; AKX-P0a/P1) | **adopt-existing → build** (this is the paper's "slow tier decides" with a *vector* objective, which TKCC does not have either) | AKX-P1: replay the screen observe-only on the historical keep set (fixtures `732389d6`, `sync17-fix2`). No new measurement. |
| **TK-7** | Test the "submit only if ceiling > 2E" rule against our own funnel: 83 refusals outbidding measurements 4.9:1, 660 intents → 17 measured → 0 promoted. | `handoffs/active/autokernel-loop.md` (`:6661-6662`) | **probe** (the paper's one genuinely adversarial data point, §4) | Recompute the funnel offline with a 2E admission rule applied to recorded screen/confirm pairs; compare evals-to-first-keep. Zero compute. |
| **TK-8** | Do **not** import prefix-cache reuse as a measurement optimisation. | `handoffs/active/autokernel-loop.md:5087`, `:2666` | **reject** | n/a — our cache-state control exists *because* reuse is a validity hazard. |
| **TK-9** | Do **not** delete the critic/planner on the strength of Fig. 5b. | `handoffs/active/autokernel-loop.md` (loop design) | **reject** (observation-grade: n=1 trajectory, 10 trials, no CI, one layer) | Re-open only if TK-7 shows the critic's refusals cost more than they save. |
| **TK-10** | Add a drift/re-convergence contract *if* continual compilation is ever claimed here. The paper has none; we should not inherit the word without the instrument. | `handoffs/active/kernel-champion-and-promotion.md` / `CURRENT-CAMPAIGN.md` | **hold** (no local continual loop exists yet to instrument) | Nothing to probe until a loop runs continuously on shifting traffic. |

---

## 9. Dive-surfaced sources

Cited in the paper and worth their own intake look, ranked by proximity to our work:

1. **[17] Krex — concurrent kernel benchmarking on shared GPUs via region-granular exclusivity**
   (`tc.md:904-906`). The closest published work to our `region-lock` / contention-matrix problem.
   Region-granular exclusivity is conceptually what our quarters/gpu-quiet claims do; worth comparing
   their granularity model against ours.
2. **[28] RSI-Inference Bench** (`tc.md:938-940`) — the harness TKCC measures itself against (8.1× / and
   Fig. 2's third baseline). Directly relevant: it is an open harness for exactly our loop shape.
3. **[13] DeepSeek v4.1 Flash, KV-cache compression** (`tc.md:891-893`) — the model we currently serve
   and are evaluating; the KV-compression detail is directly load-bearing for our DS41 CPU decode work.
4. **[55] AIConfigurator — configuration optimisation for multi-framework LLM serving** (`tc.md:1027-1031`)
   — the prior art our (dormant) config cost model would sit beside.
5. **[8] MPK — mega-kernelizing tensor programs** (`tc.md:878-881`) and **[50] Mixture-of-Kittens**
   (`tc.md:1014-1016`, and the imbalanced-routing result in Fig. 13c) — the megakernel baseline and the
   MoE megakernel whose real-vs-random-data gap is the paper's best motivation figure.
6. **[26] SOL-ExecBench** (`tc.md:928-934`) and **[56] CAKE** / **[4] TIRx** (`tc.md:1032-1034`,
   `tc.md:856-857`) — speed-of-light benchmarking and compiler-agent co-design; the "IR as verifier"
   idea (`tc.md:564-567`) is the reusable part.
7. **[42] Kerncap — automated kernel extraction and isolation for AMD GPUs** (`tc.md:990-991`) — AMD-specific
   kernel isolation, adjacent to our profiler-as-planner work.
8. **[29] Speculative decoding: performance or illusion?** (`tc.md:941-942`), **[25] Baseten agentic
   kernels in production** (`tc.md:926-927`), **[14] Decagon's self-improving inference stack**
   (`tc.md:894-896`), **[51] The Bitter Lesson** (`tc.md:1016-1017`).

---

## 10. Artifact audit

**Read in full**

| Artifact | Size / lines | sha256 | Use |
|---|---|---|---|
| `raw/tc.md` | 114,157 B / 2,488 lines | `dda2a674…64c8` | Primary. All five claims, A-D, all locators. Complete through App. D.4 (p. 38). |
| `raw/tc.pdf` | 4,638,700 B / 38 pages | `c1ce4a8a…a3ef` | Text-extracted to confirm the **absence** of `467` and `JIT` (0 hits each). Not used for any locator (md is complete). |
| `raw/alphaxiv-together.html` | 218,660 B | `ab78495f…e33e` | Landing page; used only to confirm entry identity/date. Not a claim source. |
| `entries.yaml` | 25,508 B | — | Stage-1 entry intake-2643: aligned the five filed claims and the four Stage-1 contradicting-evidence items; source of §7's overturns. |

**Read in the lane worktree** (citation targets): `handoffs/active/autokernel-loop.md` (targeted: `:2298-2306`,
`:2666`, `:4215`, `:4245`, `:5087`, `:5725-5741`, `:5794`, `:6470-6510`, `:6661-6668`);
`handoffs/active/kernel-champion-and-promotion.md` (`:1-91`, `:218`, `:666`, `:919`, `:2875-2994`);
`handoffs/active/coordination-and-churn-pipeline.md` (`:1-140`, `:2441-2565`); `handoffs/active/numa-placement-and-contention.md`
(`:660-695`, `:1077-1136`); `handoffs/active/stack-lifecycle-program.md` (`:378-420`) and `:11-146`;
`docs/guides/agent-workflows/measurement-sufficiency.md` (33 lines, full); `agents/shared/MEASUREMENT_POLICY.md`
(177 lines, full); `docs/guides/agent-workflows/agent-loop-design.md` (`:500-559`); `docs/guides/agent-workflows/backlog-churn-flow.md`
(`:11-96`); `docs/guides/agent-workflows/compute-fillers.md` (`:1-106`).

**Present in scratch, deliberately not read** (out of this lane's scope; they belong to the LinQuant
dive sharing this scratch dir): `repo-LinQuant/`, `raw/arxiv2610.39418.html`, `raw/linquant-readme.md`.

**Not obtainable / not attempted**: alphaXiv comments and the two independent critique round-ups cited in
`entries.yaml:contradicting_evidence` (alfw.ai, explainx.ai) — the mandate forbids WebFetch verification
and the paper text was sufficient to adjudicate. No artifact or harness was released by the authors, so
none could be inspected.

**Method caveat**: quotes are whitespace-normalised contiguous source spans, and the hash is over that
normalised string. Where a sentence straddles a page break with an inserted figure (`tc.md:461-511`), the
quote is taken from the continuation fragment and the locator names both lines. No claim in this report
rests on a figure whose data I could not read as text; Figures 6-10 are bar charts read only for the
values printed in their labels.

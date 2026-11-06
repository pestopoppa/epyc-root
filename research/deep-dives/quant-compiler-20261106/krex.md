---
entry: intake-2647
title: "KREX: Concurrent Kernel Benchmarking on Shared GPUs via Region-Granular Exclusivity"
arxiv_id: "2609.30057"
source_url: "https://arxiv.org/html/2609.30057v1"
source_revision: "arXiv:2609.30057v1 [cs.DC], submitted 2026-09-24 (HTML build, LaTeXML oxide 0.7.6)"
local_copy: "/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/krex.html"
local_text: "/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/krex.txt"
sha256_html: "f2621e792c913fe8d89258773c71a0f83eb85b28301abd0c7369222a379350d5"
sha256_text_extraction: "see artifact audit; extraction is lossy on LaTeXML math (duplicated tokens such as '3.4×3.4\\times')"
read_depth: "full-primary (abstract, §1–§9 read end to end in HTML; references skimmed). No PDF fallback needed."
venue: "unknown at v1 (no venue line on the HTML build; no artifact-evaluation statement)"
code_artifact: "none — see artifact audit"
lane_worktree: "/mnt/raid0/llm/worktrees/intake-quant-compiler-20261106"
host_probe_date: "2026-11-06"
dive_author: "stage-2 deep-dive subagent"
---

# KREX — deep dive

**One-line verdict.** The *diagnosis* is right and load-bearing for us; the *system* is not
portable to this host, and the number we would actually import (p95 timing inflation) is
adverse to our keep gate at exactly the kernel sizes we benchmark. Adopt the measurement
discipline and the region-scoped grant idea; decline the runtime.

## Claims table

Locators are `raw/krex.txt:LINE` in this dive's extraction, which maps 1:1 onto paragraph
order of the HTML build. `quote_sha256` is SHA-256 over the exact quoted string, UTF-8, no
trailing newline.

| # | Claim (as staged in intake-2647) | Verdict | Locator | Verbatim quote | quote_sha256 |
|---|---|---|---|---|---|
| 1 | Existing systems reserve a GPU for a whole session/command although only a small fraction needs exclusivity; sharing recovers capacity but adds contention that misdirects the agent's search | **CONFIRMED** | `krex.txt:143-148` (abstract); mechanism quantified `:210-226`, `:326-338`, `:367-376` | "Existing systems preserve measurement fidelity by reserving a GPU for an entire agent session or benchmarking command. However, this results in poor utilization because only a small fraction of command execution requires exclusive GPU access. Sharing GPUs could recover this idle capacity, but introduces contention that compromises measurement fidelity and misdirects the agent's search." | `6c5f80f651207b52bf5c9c50730dbfcadd5f2effd5087539271ab5dcb0b39045` |
| 2 | Agents mark timing-sensitive regions; KREX blocks competing submissions, drains outstanding work, freezes sibling processes and isolates CPU cores inside the region, and allows concurrency outside it | **CONFIRMED** (all five sub-mechanisms present, with a per-vendor difference in §5) | `krex.txt:153-157` (abstract); protocol in 8 steps `:553-638`; vendor split `:746-759` | "The runtime then enforces exclusivity within marked regions and allows concurrent execution outside them, achieving high throughput while preserving measurement fidelity. To enforce in-region exclusivity, KREX blocks new competing GPU submissions and drains outstanding work before freezing sibling processes and isolating CPU cores, protecting both GPU execution and the host threads that drive measurements." | `8b64bd3637e9f8bf3748a5d6f2b9c4dc4010bafca33083a38cb5d53a5169e344` |
| 3a | Up to 3.4× throughput with p95 inflation 0.30 / 1.58 / 3.90 % at >10 ms / >1 ms / >0.1 ms | **PARTIAL** | `krex.txt:160-163`, restated `:283-286` | "Compared with command-granular exclusivity baselines, KREX delivers up to 3.4× the benchmarking throughput with a negligible p95 timing inflation of 0.30%, 1.58%, and 3.90% for kernels longer than 10 ms, 1 ms, and 0.1 ms, respectively." | `f089801cdf6ace0ce9898c94b8c008bca4957f0252590b99650064348c46df57` |
| 3b | …and that this holds on AMD | **OVERTURNED as stated** — AMD runs with context pooling **disabled**; 2.6× there, not 3.4×, and none of it is context reuse | `krex.txt:844-848` | "KREX-serial achieves nearly the same throughput as native because we disable context pooling on MI308X, forgoing its throughput benefits to avoid the greater fidelity loss it causes compared with H20." | `671b4d1403886c81b2fe63fd07f90e098c78620534e136b22acad2ff21a6027b` |
| 3c | "Persistent context processes avoid repeated node-wide serialized GPU context creation" (the throughput *attribution*) | **PARTIAL** — measured contribution is ~9 %, not the bulk | `krex.txt:833-836` | "Note that KREX-serial outperforms native by about 9% because context reuse removes repeated context-creation overhead." | `5d4267d1eb26789750caecfda731120e25978dfd39a01827008ef150a8689352` |

**Why 3a is PARTIAL, not CONFIRMED.** The triad appears **only** in the abstract (`:160-163`)
and the intro (`:283-286`). §6.4, the section that owns the fidelity result, reports a
*different aggregation*: P = 2.5 % on H20 / 2.4 % on MI308X at the chosen configuration
(`:882-884`), 1.2–3.0 % / 0.8–2.5 % for the ≥1 ms bands (`:904-906`), and states that even the
**native repeat** shows P = 12.1 % (H20) / 7.6 % (MI308X) below 0.1 ms (`:907-909`). The
per-band triad is presumably a figure read (Fig. 9) but it is nowhere restated in body text, so
a reader cannot reconcile "3.90 % at >0.1 ms" with the body's statement that the 0.1 ms floor
is already dominated by native noise. Treat the triad as **figure-derived and unreproduced in
prose**; treat 2.5 % / 2.4 % as the paper's own summary statistic.

**Why 3b matters more than it looks.** Every AMD number in the paper is a *concurrency-only*
gain. §6.3 also records that pooling was disabled *because it cost fidelity on MI308X*
(`:846-848`), i.e. the one mechanism that is cheap on NVIDIA is not free on AMD.

## A. Submit-blocking and draining — exact mechanism, and what it binds

**The mechanism (NVIDIA path, `§4.2`, `krex.txt:553-589`).** Six moving parts, no driver patch:

1. A **region lock** held by a per-GPU *coordinator* process — admits one tenant at a time
   (`:555-557`).
2. A **shared-memory gate**: the holder atomically writes its identity plus a **unique epoch**
   (`:558-561`).
3. **Registration**: every context process registers *before* it initialises or submits GPU
   work, and registration is serialised with gate closure, so processes admitted before closure
   are in the drain set and later arrivals block (`:561-566`).
4. A **per-process in-flight counter**, incremented *before* the gate check. If the gate is
   held, the submitter retracts the increment and parks on a futex, "issuing nothing and
   consuming no CPU while blocked" (`:568-580`). This is the *submit-block*.
5. A **drainer thread per sibling**, woken by the holder independently of client activity,
   waits for counter==0 *and* synchronises **all** of that process's contexts — including
   contexts the candidate created itself — then publishes the captured epoch
   (`:582-589`). Matching epochs is what prevents a stale ack from being read as this entry's
   drain. This is the *drain*.
6. Nothing that leaves work on the GPU may bypass the counter: "Context creation and cleanup
   follow the same counter-and-gate protocol" (`:577-580`).

**CPU side (`:591-616`).** Freezer cgroup **per tenant, assigned at process creation** — chosen
precisely so a client can be frozen *before it registers*, e.g. mid `import torch`
(`:599-605`). Plus a fixed per-GPU **CPU-slice** partition, with dedicated cores reserved for
submitting threads while any tenant is in-region (`:607-616`). On entry: L2 flush over an
L2-sized buffer, then pin submitting threads (`:621-624`). On exit: thaw **before** releasing
the lock (`:631-638`) — the ordering argument is explicit and is the kind of bug a naive
implementation ships.

**What it binds — the operative answer.**

- **Not a privileged driver hook, not a kernel module.** No ioctl, no vendor extension, no
  firmware change.
- **A wrapper + an interposer**, yes: the client process runs under a shim that interposes the
  driver API "including dynamically resolved driver entry points" and forwards over
  shared-memory RPC to a persistent context process (`:680-686`); the gate lives in that
  process's RPC dispatch loop (`:748-749`). On AMD the alternative is *"a tools library loaded
  by ROCm at startup inside the tenant process"* that *"patches the runtime dispatch table to
  intercept each queue's kernel launches"* (`:749-752`).
- **Not a harness modification.** The agent writes a one-line context manager
  `region.critical()` (`:491-494`), or the *scaffold author* marks a fixed script the agent
  cannot edit (`:512-517`, `:524-531`). Region boundaries are *deliberately* not inferred
  (`:496-507`).
- **The one real privilege requirement is the freezer**: creating per-tenant cgroups and
  freezing *another tenant's process tree* needs write access to a delegated cgroup-v2 subtree
  managed by the runtime. That is a deployment/ownership requirement, not a code one — and it
  is the requirement that decides whether this transfers to EPYC (see E).

## B. Hardware scope — gfx90a/MI210 is **not** in scope

**Testbed (`§6.1`, `krex.txt:779-780`):** *"two 8-GPU nodes, for a total of 16 NVIDIA H20 and
16 AMD MI308X GPUs."* MI308X is gfx942 (MI300X-class, CDNA3). **There is no gfx90a result
anywhere in the paper**, no CDNA2 result, and no MI210/MI250 result. Our host is
`gfx90a:sramecc+:xnack-`, one MI210, ROCm `6.2.0-66` (host probe, 2026-11-06).

**Feature dependence — no MPS/MIG dependency on the AMD path.**

- MIG is rejected on principle: it *"alter[s] the hardware under test"* (`:229-233`).
- MPS is **NVIDIA-only** and used only on H20, where it is worth 44.2 → 54.8 cmds/min, +24 %
  (`:971-973`). ROCm has no MPS equivalent, so the AMD path never had it.
- AMD concurrency comes from the platform itself; KREX adds only gating. So the *architecture*
  transfers. The *implementation* does not, and the paper is explicit that the AMD path differs
  materially (`:746-759`): the counter tracks **device completion** rather than host submission
  (incremented on op entry, decremented by a polling thread when the completion signal fires);
  the holder waits for sibling counters to hit zero **without** sibling-side context
  synchronisation or drainer threads; and *"tenants are added to freezer cgroups only after
  initialization because freezing during initial memory registration causes failures on the
  evaluated system"* (`:757-759`).

**What would have to be built for MI210 / ROCm 6.2.** (i) A ROCm dispatch-table interposer
(HSA/ROCr tools-library load path) that hooks every queue's launches on gfx90a — the paper's
AMD path exists but is untested on CDNA2, and a *load-time* dispatch patch is sensitive to the
ROCm minor version. (ii) A per-queue device-completion counter with a polling thread, on
gfx90a's signal semantics. (iii) Cgroup-v2 freezer plumbing under our scheduler. (iv) A CPU-slice
partition over 192 CPUs (4 quarters) that does not fight `region-lock`'s q0–q3 model. (v) The
right to freeze *other sessions'* process trees — which we do not have and, per CLAUDE.md:129,
must not take. Nothing here depends on MPS/MIG; the blocker is (v), not the GPU.

## C. Throughput decomposition — the paper gives it, but not as a product

The paper does **not** print a multiplicative decomposition. It prints the three points needed
to derive one on H20 (`§6.3`, `krex.txt:831-842`): native **16.0**, KREX-serial **17.5**,
full KREX **54.8** cmds/min, plus an MPS on/off pair **44.2 → 54.8** (`:971-973`).

Derived, with the caveat that I am multiplying the authors' separately-measured factors:

| Source | Factor (H20) | Share of the 3.4× |
|---|---|---|
| Context reuse (KREX-serial vs native) | 17.5/16.0 = **1.09×** | +9 % of throughput; log-share **7 %** of the total |
| Off-region concurrency, no MPS (44.2/17.5) | **2.53×** | **~78 %** of the total |
| MPS (54.8/44.2) | **1.24×** | ~19 % of the total |
| Product | 1.09 × 2.53 × 1.24 = **3.42×** | reconciles with 3.4× |

**On AMD the decomposition is degenerate:** pooling is disabled, KREX-serial ≈ native
(`:844-848`), so **100 % of the 2.6× is concurrency plus region gating and 0 % is context
reuse.** Their own sentence — *"context reuse becomes more important at higher concurrency, as
creating more GPU contexts exacerbates the context-creation bottleneck"* (`:836-838`) — is an
NVIDIA claim.

This is the single most decision-relevant number in the paper for us: the half of KREX that is
cheap and portable (context reuse) is worth ~9 %, and on the vendor we run it is worth ~0 %.

## D. What 0.30 / 1.58 / 3.90 % p95 inflation does to a 2 %-floor keep gate

**Definitions used (the paper's own, eq. 1, `krex.txt:865-872`):** P = p95(r) − 1 with
r = t_measured / t_native. **Our gate's unit** (`kernel-champion-and-promotion.md:601,666`):
the paired relative difference e = t_cand/t_base − 1, decisive iff |e| ≥ F, with **F = 2.00 %**
(GPU tg), **9.91 %** (GPU pp), **4.533 %** (DS41 process unit), and F = max(2.00 %, P-vs-P
spread) in the A/B harness. That last clause is the crux: *our floor is itself a measured
dispersion*, so inflation does not corrupt the answer, it **widens the floor**.

**Assumptions, stated explicitly.**

- **D1.** Inflation is a one-sided upper-tail perturbation: t_a = T_a(1 + ε_a), ε_a ≥ 0,
  p95(ε_a) = P. (Supported by the paper's observed median ratios of 0.997–1.000, `:892-894`, and
  93.3–97.1 % of ratios inside 5 %, `:895-897` — the *typical* measurement is unbiased; ~3–7 %
  of measurements carry the tail.)
- **D2.** The gate effect is e = (1+ρ)(1+ε_c)/(1+ε_b) − 1, so to first order
  **e − ρ ≈ ε_c − ε_b**. Everything follows from how ε_c and ε_b are coupled.
- **D3.** Three coupling regimes, each a real deployment:
  **(i) common-mode** — both arms measured inside the same grant with the same co-tenants
  (our ABBA/paired design today): ε_c ≈ ε_b, bias cancels to O(ρ·ε) < 0.01 pp.
  **(ii) independent** — each arm draws its own tail: p95(|ε_c − ε_b|) ≈ **√2·P** (range P…2P;
  √2 is the RMS-of-independent-tails estimate and the number I would pre-declare).
  **(iii) one-sided** — only the candidate arm is perturbed (an unprotected or unlucky arm):
  bias ∈ [0, P], **signed**, and it can only make the candidate look worse.

**Derived table.** "Resolution" = the smallest true win that still clears the (possibly
widened) floor.

| P (p95, per arm) | Independent √2·P | One-sided P | 1 % claimed win (F=2 %) | 3 % claimed win (F=2 %) | vs DS41 F=4.533 % |
|---|---|---|---|---|---|
| **0.30 %** | 0.42 % | 0.30 % | **already sub-floor and stays sub-floor** — a 1 % win is not a claim our gate can carry at any inflation; margin against it widens | reads 3.00 % (common-mode) / 2.58 % (indep.) / 2.70 % (one-sided) → decisive, 1.5× / 1.29× / 1.35× floor | unaffected |
| **1.58 %** | **2.23 %** | 1.58 % | sub-floor, and now **0.58 pp further** from an independent-arm floor of 2.23 % | reads 3.00 % / **0.77 %** (indep., floor→2.23 %) / **1.42 %** (one-sided → **FALSE NEGATIVE**, recorded as no-keep) | unaffected |
| **3.90 %** | **5.52 %** | 3.90 % | sub-floor | reads 3.00 % / **−2.52 %** (indep., i.e. floor→5.52 %, win unresolvable) / **−0.90 %** (one-sided → **SIGN FLIP**, recorded as a regression) | **at 4.533 %: a true 4.5 % win reads 0.6 % → dead** |

**Operational rule I would adopt from this, independent of KREX:** if both arms share the
environment, `F_new = max(F_old, √2·P)`. A 2.00 % floor survives only while **P ≤ 1.41 %**.
At P = 1.58 % the floor must become 2.23 %; at P = 3.90 % it must become 5.52 %.

**The consequence that actually bites.** With F→5.52 %, **all ten** of the unledgered keeps
V11-033..042 (`kernel-champion-and-promotion.md:588`, effects +0.120 % to +3.932 %) fall below
the floor and would have been unresolvable. That is not a hypothetical: it is the exact size
band our GPU and CPU ledgers live in. It also explains why the paper's "negligible" is
negligible *for them* and not for us — their fidelity metric is a p95 of absolute duration
ratios against a native reference; ours is a *decisiveness* test against a 2 % dispersion
floor, and the two are not the same currency. **A 2 % floor and 3.90 % tail inflation cannot
coexist in the same measurement plane.** At the 10 ms band (0.30 %) they can, comfortably.

## E. What EPYC already enforces, and what KREX would add or replace

**Already enforced today** (lane citations):

- **Device-level exclusivity by grant, not by hardware.** `region-lock --gpu-quiet exclusive`
  takes the `mi210_0` device claim; the calendar owner writes one grant per run
  (`compute-fillers.md:67-70,152-156`). "No grant, no run" (`:60`).
- **A grant lifecycle with teeth**: `<block>_FREED` handoff, hard `end`, STOP file, SIGTERM→
  SIGKILL by captured PID only, `.ended rc=…` receipt (`compute-fillers.md:58-63`).
- **Host-side protection of the timed region**, which is the part KREX argues matters most:
  GPU timing rows claim `gpu-quiet` only and `taskset` their own host threads 184-191; q3 is
  refused to CPU grants while a GPU runner holds it; every task is re-pinned because ROCr
  spawns a full-affinity helper thread (`compute-fillers.md:69-70,87,107`). This is a
  *cooperative* approximation of KREX's CPU-slice + freeze.
- **Statistical discipline**: matched pairs, order counterbalance, `floor = max(2.00 %, P-vs-P
  spread)`, 15 alternating P/C pairs on one persistent server (`kernel-champion-and-promotion.md:666,919`).
- **Measurement tiers** T0–T4 with an explicit "cheapest lane that clears a declared rank-fidelity
  threshold" rule (`autokernel-loop.md:2298-2315`, `:4917-4929`).

**What KREX would add.** Only two things we lack: (1) submit-blocking + drain + freeze of
tenants **we do not control**, and (2) **region-scoped** rather than run-scoped exclusivity, so
a 1500 s row would hold the device for its ~12–19 % region fraction instead of 100 %
(region fraction: median 12 %, 73 % of commands < 25 %, `krex.txt:814-821`).

**What KREX would replace.** Nothing. It explicitly declines to provide fairness
(*"no region-access fairness guarantee"*, `:1020-1023`), clock control (`:1014-1018`), a
worst-case error bound (`:1011-1012`), or resilience to dispatcher death (`:1024-1026`).

**Is our bottleneck exclusivity?** No — and the lane's own evidence says so three ways:

1. **The GPU is already exclusive.** One MI210, one device claim, q3 held quiet. Within a
   grant there is no co-tenant to drain, so mechanism (1) buys exactly nothing today. KREX's
   benefit is only realisable by *admitting* co-tenants, i.e. by trading exclusivity away.
2. **We already measured what happens when we trade it.** AK-LN-2/AK-X-5a fanned one candidate
   set across 4/8/16/32/48-way CPU partitions: full-machine rank fidelity 1.0, depth 4 held
   (1.0), and **depths 8–48 inverted IQK-off vs flash-attention-off (Spearman 0.5)**; every
   historical split depth was therefore rejected as a ranking proxy
   (`autokernel-loop.md:4920-4929`). The loop's stated currency is not throughput but **rank
   inversion** (`:4842`). KREX's §2.2 shows the identical failure under GPU sharing — 6 of 10
   pairwise rankings reversed under 64-agent contention (`krex.txt:367-376`).
3. **Our cost structure is elsewhere.** A GPU timing row is ~1500 s with ~95–105 s of model
   load per arm (`kernel-champion-and-promotion.md:595` "champion load 105 s"). KREX's
   context-reuse win is "hundreds of milliseconds per command" (`krex.txt:267-270,658-660`) on
   commands whose median is 10.2 s / 17.7 s (`:810-811`) — and we already amortise it by
   running 15 pairs against **one live server** on one port (`kernel-champion-and-promotion.md:919`).
   The transferable half of KREX is therefore worth ≈0.1 % of our row time, while its
   non-transferable half is worth 78 % of its own gain.

**Where the time actually goes: grant latency, not contention.** The registered pathology is
`gpu-quiet` starving behind back-to-back shared claims — a 600 s acquire timeout on 2026-10-07
(`autokernel-loop.md:14035`) — and fillers losing windows to grant-shape mismatch
(`compute-fillers.md:103,106`). KREX has no answer to either; it has no admission fairness at
all. **Our bottleneck is calendar latency + a 2 % statistical floor, not a busy GPU.**

**The one idea worth stealing is therefore not concurrency.** It is *region-scoped grants*: let
a timing row hold `mi210_0` only inside its declared timed loop and release it between regions,
which would cut device-hold time by ~80 % at zero fidelity cost **if** the boundary can be
declared and the released interval is genuinely unmeasured. That is a `rowflow`/`region-lock`
change, needs no interposer and no freeze, and is the only KREX mechanism that survives our
process-ownership constraints.

## F. Smallest deciding experiment on this host

**Question.** At the kernel sizes and shapes we actually gate, does a concurrent co-tenant's
GPU+CPU work during the timed region move our measured paired delta beyond the predeclared
floor — and does a cooperative drain-and-freeze recover it? This is the *premise* of KREX; if
the premise is false on gfx90a, no part of the system matters.

**Host state and subject.** MI210, `gpu-quiet exclusive` grant, whole row pinned with
`filler_run7.sh --class gpu --gpu-quiet exclusive --no-fold-siblings`, job tasksets its own
184-191 and re-pins every task (`compute-fillers.md:87,107`). Subject is an existing ledger
recipe — `llama-bench -ngl 99 -fa 1 -t 8` pp512/tg128, r=5, on Qwen3.6-35B-A3B-MTP-Q8_0 — so no
new recipe calibration is needed. Lower time / higher t/s is better.

**Co-tenant (we own it; its PID is captured at spawn).** A synthetic HIP kernel loop sized to
hold ~50–70 % of the device, plus 8 CPU spin threads on **q1** (a quarter the subject does not
use). This is a *realistic* other session, not a maximally adversarial one. Note the unknown
this settles: without an MPS equivalent on ROCm, two processes may time-slice at command
granularity rather than co-execute — in which case contention will appear as large discrete
steps, not a 3.9 % tail, and that alone decides the transfer.

**Arms.** A0 = quiet, no co-tenant. A1 = co-tenant free through the whole command. A2 =
co-tenant `SIGSTOP`ed for the marked region and `SIGCONT`ed after (our cooperative stand-in for
KREX's freezer — legal because it is our own child).

**Controls.** Interleaved ABBA per pair, order counterbalanced; A0-vs-A0 A/A calibration of 5
pairs to re-derive the floor in-window; identical argv and store image; own-PID VRAM sampled
through every arm; ggml linkage and digests recorded per arm; one process group, killed by
captured PID; nothing else on the GPU.

**Predeclared decision rule.** F = max(2.00 %, A0 A/A p95 spread), evaluated on the paired
median delta of pp and tg:

- **|A1 − A0| ≤ F on both metrics** → contention does not bind at our shapes → **DECLINE**
  KREX outright; the premise fails on gfx90a. (Stop.)
- **|A1 − A0| > F and |A2 − A0| ≤ F** → premise holds and a cooperative drain+freeze recovers
  it → proceed only with KX-1 (region-scoped grants) + KX-2 (floor discipline); no interposer.
- **|A2 − A0| > F while A1 is worse** → the protocol itself perturbs the measurement →
  **DECLINE** the mechanism as unsafe at our floor.
- **5 pairs** for a ≥5 % effect, extend to **10** by predeclared bounded extension if the
  observed |delta| lands in [F, 2F] (`autokernel-loop.md:2333-2337`, reps + bounded-extension rule).
- **Futility stop** if the co-tenant fails to hold ≥50 % device occupancy (verified by
  sampling), or if the A0 A/A floor exceeds 4 % (NOISY, per the existing wrapper rule,
  `kernel-champion-and-promotion.md:502`).

**Cost.** ~35–45 min of GPU window plus ~1 h to build the co-tenant binary. Cheaper than any
port attempt by two orders of magnitude, and it is the only experiment whose *negative* result
retires the whole intake.

**What would decline the idea.** A1 inside the floor. Also declining: if the co-tenant cannot
be made to perturb A0 by >2 % at all, because that is a substantive finding — the MI210 at
llama-bench shapes is not contention-sensitive in the way the paper's 16-H20 install is, and
the paper's premise simply does not describe our host.

## Derived-actionables ledger

| ID | Action | Owning lane handoff | Disposition |
|---|---|---|---|
| **KX-1** | **Region-scoped GPU grants**: let a timing row hold `mi210_0` only inside its declared timed region and release between regions; target ≤40 % device-hold per row (paper's region fraction is 12–19 %). Pure `region-lock`/`rowflow` change; no interposer, no freeze, no second tenant. | `autokernel-loop.md` (rowflow/region-lock) + `coordination-and-churn-pipeline.md` | **ADOPT-PATTERN**, staged behind KX-6. Highest value item in this dive. |
| **KX-2** | **p95 inflation as a first-class gate input**: report P on every GPU A/B and set `F = max(F_old, √2·P)` when both arms share the environment; refuse a keep whose effect sits inside the reported tail. | `kernel-champion-and-promotion.md` | **ADOPT (cheap, no GPU time)** — applies to KREX and to every future shared-window run. |
| **KX-3** | **Declare the timing region explicitly** in every benchmark scaffold (name warm-up, timed loop, compile/import/check as distinct spans; scaffold-marked, not agent-inferred). Precondition for KX-1 and for any future floor work. | `autokernel-loop.md` (T1/T2 harness) | **ADOPT** — prerequisite for KX-1. |
| **KX-4** | **Persistent context / server reuse across arms.** Reframed by the audit: the paper's 9 % (and 0 % on AMD) is not our cost — our equivalent is per-arm model load, ~95–105 s. Verify `ab_probe.py`'s single-`:8197` 15-pair design is the standing default on every GPU gate. | `kernel-champion-and-promotion.md` | **ALREADY-HELD** (`:666,919`); only the *defaulting* is open. |
| **KX-5** | **Do NOT import submit-blocking / sibling-process freeze / driver-call interposition on the shared host.** Requires freezing process trees we do not own; forbidden by CLAUDE.md:129 and the never-touch-another-session's-work invariants. Would need node ownership or a delegated freezer cgroup over foreign sessions. | `autokernel-loop.md` (resource plane §5.7) | **DECLINE** — architectural, not effort. Does not block KX-1/KX-2. |
| **KX-6** | **Run the deciding experiment (F)** as a published `gpu-q3` row: A0/A1/A2, 5→10 pairs, predeclared decline conditions. | `autokernel-loop.md` (GPU-quiet queue) | **PROPOSED** — publishable now; ~35–45 min + 1 h build. |
| **KX-7** | **Rank-inversion audit on existing receipts**: apply the paper's method (pairwise ordering-flip rate grouped by native duration gap; per-trajectory Kendall τb) to our banked 15-pair A/B results, to quantify *our* flip rate at the 2 % floor. Zero GPU time. | `kernel-champion-and-promotion.md` | **ADOPT** — analysis-only; directly tests the loop's stated currency. |
| **KX-8** | **Do not carry the 3.4× / MI308X numbers onto gfx90a.** Record in the wiki that the AMD arm ran with context pooling disabled and that no CDNA2 result exists. | `research-evaluation-index.md` | **DECLINE-CLAIM** (anti-claim, recorded). |

## Surfaced sources (not already carrying their own intake entry)

From this paper's related work, judged load-bearing for our measurement constitution rather
than for kernels. Verified against `research/intake_index.yaml` on the lane worktree:
mention-only or absent — no own entry.

| Source | Why it matters here |
|---|---|
| Kalibera & Jones 2013, *Rigorous benchmarking in reasonable time* (ACM TACO) | Directly addresses our weakest point: how many reps a given effect size needs, and how to stop. Our "5 pairs for ≥5 %, 10 for ≤2 %" rule is folk knowledge without this citation. |
| Mytkowicz et al. 2009, *Producing wrong data without doing anything obviously wrong!* (ASPLOS) | The environmental-bias paper. Our floor registry, layout pinning and cache-state controls are responses to exactly its failure modes; not cited in the ledger that implements them. |
| Curtsinger & Berger 2013, *Stabilizer* (ASPLOS) | Layout randomisation as a *statistically sound* evaluation method — the alternative to our "pin everything and hope the floor is stable" approach. |
| Atrex Kernel Agent + Atrex-Bench (Alibaba, github) | The NVIDIA-side agents whose 16 k commands the paper replays; a real production kernel-agent harness to compare our autokernel loop against. |
| FlashInfer-Trace (HF dataset) | Replayable kernel-benchmark trace corpus; a candidate external workload for KX-7 without new GPU time. |
| PipeSwitch (Bai et al., OSDI'20) / KRISP (Chow et al., HPCA'23) | Fast context switching and right-sizing — the two designs that would matter if we ever *do* want co-tenancy on one GPU without MPS. |

## Artifact audit

- **No code artifact exists.** The HTML build contains no "code available", Zenodo, or GitHub
  link for KREX itself; all GitHub URLs in the document are bibliography entries for the *agents
  and benchmarks it integrates with* (`atrex-kernel-agent`, `atrex-bench`, `AMD-AGI/GEAK`,
  `NVlabs/kda`). There is no artifact-evaluation statement, no appendix, and no licence beyond
  the arXiv perpetual non-exclusive licence.
- **Not reproducible from the paper.** The 20 k-command replay corpus, the dispatcher, the
  context-process pool, and the 41 k lines of machine-generated forwarding stubs are unreleased.
  Effort to reimplement, from `§5` (`krex.txt:739-744`): ~20 k lines C++ for interception +
  4.8 k Python control plane + 41 k generated stubs. **This is a research system, not a tool.**
- **Numbers audited for internal consistency.** 3.4× (16.0→54.8) and 2.6× (19.4→50.4) check
  arithmetically. The `0.30/1.58/3.90` triad does not appear outside abstract+intro and is not
  reconcilable with §6.4's own aggregation (see claim 3a). `P` is defined once (`:865-872`) and
  used consistently; §6.5's ablation P values (23.87 % ungated / 4.63 % gate-on-GPU / 2.45 %
  KREX, `:961-963`) use a *different, higher concurrency* configuration than §6.4's headline
  2.5 % — the paper is explicit about the configuration difference (`:882`), so this is
  consistent, but a reader skimming will conflate them.
- **Extraction caveat in this dive's own copy.** The LaTeXML HTML duplicates math tokens
  (`3.4×3.4\times`, `0.30%0.30\%`); `krex.txt` is a text extraction of that HTML and preserves
  the duplication. Quotes above are normalised to the single occurrence, which is the
  mathematically correct reading and matches the PDF rendering. `sha256_html` is over the raw
  fetched bytes and is the authoritative identity.
- **Host facts used in B/E/F** are live probes on 2026-11-06, not literature: one
  `AMD Instinct MI210`, `gfx90a:sramecc+:xnack-`, ROCm `6.2.0-66`, 192 CPUs, `/dev/kfd` present.

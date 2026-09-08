# WIKI DRAFT — INF-70 close-out, 2026-09-08 (PASTE-READY, NOT APPLIED)

**Status: DRAFT ONLY.** Nothing under `wiki/` was created or modified by the session that wrote this
file. No lease was taken, no compile was run, `compile_sources.py` was not invoked with `--touch` or
`--write-manifest`. Everything below is text for the operator to paste **under the wrap-up lease**.

Sources drafted from (both **tracked**, both currently **modified-uncommitted** in
`/mnt/raid0/llm/worktrees/audits/inf70-audit-20260902` — commit them in the same pass, or the
compiled citations point at content that is not yet in `origin/main`):

- `progress/2026-09/2026-09-08-inf70-audit.md` — the CLOSE-OUT section is authoritative
- `handoffs/active/cpu-decode-roofline-program.md` — CURRENT STATE header + CLOSE-1..CLOSE-11

---

# ★ PART 4 — TWO BLOCKERS, READ BEFORE ANYTHING ELSE

**BLOCKER 1 — the wiki `.last_compile` is STALE relative to the tracked manifest.**
`wiki/.last_compile` (gitignored) reads **`2026-09-07T14:04:28Z`**; the **tracked**
`wiki/source_manifest.json` carries **`last_compile: 2026-09-08T09:28:51Z`**.
`get_last_compile_iso()` prefers the untracked file when it is non-empty, so any lane with a stale
`.last_compile` reports a watermark **~19 h behind the real one**. Selection is content-hash based
and therefore **unaffected** — but **the displayed watermark must not be quoted as the compile
date**, and the stale file should be refreshed as part of whatever pass finally holds the lease.

**BLOCKER 2 — `--touch` is FLEET-WIDE. This is open decision OP-34.**
`compile_sources.py --touch` rewrites the shared watermark (`refresh_tracked_manifest` +
`touch_last_compile`) for **every** session, not just this one. A single lane touching it advances
the baseline for all consumers of the manifest. **Do not run `--touch` to land this draft** until
OP-34 is ruled. Until then, paste the sections, run lint and `--check-manifest`, and leave the
watermark alone.

---
---

# PART 1 — `wiki/benchmark-methodology.md` — NEW H2, **APPEND after the current last section**

> **Placement**: append after `## Compiled Update — 2026-09-08: the three-valued conversion is a
> contract first and a migration second …` (currently the final H2 in the file, at line 4476).
> `benchmark-methodology.md` accretes at the **tail**; do not prepend.

```markdown
## Compiled Update — 2026-09-08 (INF-70): an environment knob bought the precision that repetitions could not — 8.3× sd for zero extra arms, and two rules about what a floor is

**Confidence: verified** — 18 launches, none dropped, pre-registered before the region lock
(`PREREG-FINAL.md`, frozen 15:05:15Z, sha256 `1d8f4ddc…`); the paired decision plan frozen
separately (`PREREG-THP-DECISION.md`, 14:08:05Z, sha256 `337200315c6b…`) and its early-stop boundary
unit-tested before the run.

### A launch-time environment knob moved between-launch sd from 5.081% to 0.609% — 8.3× in sd, ~70× in variance

INF-70's final characterisation adopted **`GGML_NOHUGEPAGE_PROCESS=1`**, a `prctl(PR_SET_THP_DISABLE)`
taken **before** the 92 GB model allocation. It is **set at LAUNCH** (process env) and its **unit is
the SESSION** — one process launch, never the arm. It is **not** `GGML_NOHUGEPAGE`, the `madvise` on
the model buffer that was already ON and is 86.4% of the champion; the two knobs have different
scopes and **must be spelled out separately every time**.

| | launches | between-launch sd | range |
|---|---:|---:|---:|
| **BEFORE** — shim OFF (now-retired configuration) | 9 | **5.081%** | **12.55%** |
| **AFTER** — shim ON (adopted) | 6 | **0.609%** | **1.79%** |

**sd ratio 8.3× · variance ratio ~70×.** Independently corroborated by the pre-registered paired
decision test, in which the shim was the only thing varying: **OFF/ON variance ratio 25.3×**, **6/6
pairs ON-faster**.

**What the precision costs, in launches, for a 95% CI:**

| target 95% CI | shim ON (adopted) | shim OFF (retired) |
|---|---:|---:|
| ±1.0% | **2** | 100 |
| ±0.5% | **6** | 397 |
| ±0.25% | **23** | 1587 |

> **A ±0.5% champion headline now costs ~23 minutes. Before adoption it would have cost ~25 hours.**

**The ON sd was VERIFIED, not assumed.** The plan sized from the decision test's **0.481%** and
required the figure be checked *as it ran*: observed **0.609%** (plain, 5 dof) and **0.356%** (MTP) —
same order, slightly above reference for plain, below for MTP. The delivered CI (**±0.487%**) is
fractionally wider than the projected **±0.385%**, and **the headline precision is quoted at the
OBSERVED value, not the projected one**. n=6 is a coarse variance estimate and is labelled a check,
not a precise sd.

> **⚠ THE CONDITIONS CLAUSE TRAVELS WITH THE NUMBER — never quote 0.609% bare.**
> Hot harness · 24-prompt production mix · token-weighted decode · **unit = LAUNCH** (one arm per
> launch) · precision = **between-launch** · both contention screens live and `screened()` applied ·
> **GPU loop DOWN** · **host exclusive** · shim ON verified per launch under a fail-closed
> `THP_enabled` assertion. No hot absolute is compared against a cold one.
> This campaign spent 2026-09-07 filing *against other people's* numbers for exactly this defect,
> then quoted its own **0.80%** A/A floor all morning without saying it had been measured during a
> GPU-loop drain. A bare number is not a floor, and the applicable floor **under** the loop remains
> **UNMEASURED and certainly worse**.

The nine-launch spread table is the **before** picture, measured entirely in the configuration that
has now been retired. It is **not** a standing property of the champion.

**Verification method is also session-unit**: `THP_enabled` in `/proc/<pid>/status` — **1 = THP
allowed (shim off), 0 = prctl in force (shim on)** — read once per launch, fail-closed. It read **0
on every champion launch and 1 on every pristine launch**. `AnonHugePages` is **not** a valid
discriminator (0.06% of Rss at load, ~6% minutes later on the same process).

**Magnitude of the knob's speed effect is NOT claimed** — the design sized for direction only. Pair
effects were `+4.843, +5.617, +5.934, +5.664, +0.321, +0.558` %, median **+5.23%**. Anyone quoting a
number for it must measure it, at **launch** granularity. The exact α was **enumerated over all 2¹⁰
sequences with nested stopping** (two-sided **0.0430**); **a union bound would have said 0.078 and
been over budget silently** — an inflated-α claim looks identical to a valid one from the outside.

### A floor carries its harness, its n, its contention model, its host state — AND ITS UNIT

**Extends the 2026-09-07 ratified amendments below** — see
[`## Compiled Update — 2026-09-07 (incremental): name the unit, control the instrument, place the
caveat`](#compiled-update--2026-09-07-incremental-name-the-unit-control-the-instrument-place-the-caveat--three-ratified-measurement-amendments-fb755192).
That section ratified *naming* the unit; this is the measured cost of getting it wrong.

| floor | scale | sd | governs |
|---|---|---:|---|
| Q3–Q6, four consecutive undisturbed arms | **arm**, within session | 0.071% | best case, arm-scoped knobs |
| A/A gate, 5 kept arms | **arm**, within session | 0.433% | routine, arm-scoped knobs |
| within-session, campaign figure | **arm** | **0.501%** | arm-scoped knobs |
| THP block, 8 sessions | **session**, between launches | **2.793%** | **process-scoped knobs** |
| concurrent GPU chain (earlier) | arm | 0.772% | superseded — host now exclusive |

**A process-scoped knob faces a floor ~13× coarser than the arm floor.** Applying the arm floor to
the session-unit THP question said the study needed **4 sessions/side** for +0.16%; the correct
session-unit answer is **4,780** — a **1200-fold error**. The wrong number was not marginally wrong;
it was the difference between a feasible study and an impossible one, and nothing in the arithmetic
flagged it, because a floor quoted as a bare percentage carries no unit to disagree with.

> **A bare number is not a floor.** The rule now reads: a floor carries its **harness**, its **n**,
> its **contention model**, its **host state** — **AND ITS UNIT**. This is the same error that let
> the 0.80% figure mislead this campaign all morning.

This also extends `## Compiled Update — 2026-08-31 (evening): … floors that travel without their
model …` (same family: a floor detached from what produced it) and is the measured cost of violating
**U2** on [Hardware Optimization](hardware-optimization.md) — "per-surface floors carry their
measurement conditions (harness, n, contention model, host-state hash), not just a number".

### The vacuous instrument, fifth instalment: a check that produces a verdict without verifying it had anything valid to verify

This page already carries four sections of this family —
`## Four more ways a check passes for the wrong reason (2026-08-12)`,
`## Compiled Update — 2026-08-21: the vacuous-pass campaign closed — and the guard needed five
repairs of its own`,
`## Two ways an A/B screen reports a win that does not exist (2026-08-28)`, and, one day earlier and
the same shape, `## Compiled Update — 2026-09-07: absence read as a negative verdict, found three
times in one afternoon, three independent subsystems`. **The value of this entry is that the family
recurred a fifth time, not that the four incidents below are novel.** Four in one day, across two
campaigns, filed as **one pattern**:

| # | instrument | how it was vacuous |
|---|---|---|
| a | our contention screen | **passed both contaminated arms** — it watched **CPU** while the confound went through **DRAM bandwidth** |
| b | our kill check | reported **four live processes dead** (`ps -p` false negative) |
| c | their FOLD-2 parser | counted **zero OKs** and **would have reported PASS** |
| d | our `tools/gate.py aa` | computed the gate over **an arm its own screen had DROPPED** — reported `pair_p95 = 4.8% / STOP`; the pre-registered answer over the 5 kept arms is **1.051% / PASS** |

> **★ The common form: a check that produces a verdict without verifying it had anything valid to
> verify.** Note that (a) is *not* a screen-quality problem — a better screen cannot detect a
> confound that does not travel through the resource it watches; see
> [Hardware Optimization](hardware-optimization.md) on admission control.

**Three structural guards adopted, and mutation-tested:**

1. **A gate cannot PASS on zero cases** — fewer than 2 usable arms returns `AA_GATE=INVALID`, never a
   verdict; a permutation test with an empty side returns `PERM=INVALID`.
2. **A gate cannot compute over arms its own screen rejected** — **all** statistics route through one
   `screened()` function applying both instruments' drop rules.
3. **Death is verified by `/proc` existence, not `ps`.**

Mutation evidence: the exact gate that was wrong now reports `SCREEN DROPPED ['Q2']` and
`AA_GATE=PASS pair_p95=1.051%`; a gate over only-dropped arms returns `INVALID`.

**The wrong `4.8%` line is KEPT in the record rather than deleted.** A bug's output is evidence about
the instrument, and this defect class is only visible because the wrong number was preserved next to
the right one.

Two routing notes. Incident (d) is the same class as **STAT-1** in the INF-70 audit record
(per-prompt paired statistics are pseudo-replication; the **arm** is the unit) — cite it rather than
re-deriving it. Incident (b) is a **process-management** defect, not a benchmark one: root
`CLAUDE.md` → *Process Management* currently instructs "after killing a process, verify it is dead
(`ps -p <pid>`)", and that guidance is **affected** — `/proc/<pid>` existence is authoritative. See
also the daemon-liveness-predicate family on
[Tool Implementation](tool-implementation.md) and [Agent Architecture](agent-architecture.md).

**A related coverage gap, recorded so "screen clean" is not read as "window clean":**
`foreign_load.py` runs **per arm**, so a burst landing *between* arms — or between the eviction and
the first arm — is **invisible to it**. On event E1 the only instrument that caught the
contamination was the peer's own disclosure. **The contract worked; the instrument would not have.**
No arm was dropped (the region was taken 1m12s after the window closed), and the honest statement is
that the screen read **nothing** across that window — which is neither a validation nor a failure of
it.

### Source References (2026-09-08, INF-70 close-out)

- [`progress/2026-09/2026-09-08-inf70-audit.md`](../progress/2026-09/2026-09-08-inf70-audit.md) — the
  CLOSE-OUT of record: §2 the 18-launch table, §3 the variance result and the launch-cost table, §9
  the floors-and-units table and the 1200-fold error, §10 the four vacuous-instrument incidents and
  the three adopted guards; also STAT-1 and the 0.80%-floor conditions clause.
- [`cpu-decode-roofline-program.md`](../handoffs/active/cpu-decode-roofline-program.md) — CURRENT
  STATE header (unit = LAUNCH, the conditions clause, the supersession block) and CLOSE-1 (a floor
  carries its unit), CLOSE-2 (the vacuous-instrument pattern and the three guards), CLOSE-3 (`ps -p`
  is not a death test), CLOSE-10 (the per-arm sampler's coverage gap).
- [`autokernel-unified-surface-program.md`](../handoffs/active/autokernel-unified-surface-program.md)
  — U2: per-surface floors carry their measurement conditions, not just a number; the U3
  `RUNTIME_CONFIG` arm type into which the THP shim was filed on the GPU side.
- [`progress/2026-09/2026-09-08-ak-rebuild-20260828.md`](../progress/2026-09/2026-09-08-ak-rebuild-20260828.md)
  — the peer campaign's side of the shared window, including the FOLD-2 parser incident's home run.
```

---
---

# PART 2 — `wiki/hardware-optimization.md` — THREE SEPARATE EDITS

> **Placement note**: `hardware-optimization.md` **prepends** its newest compiled sections (top of
> file, after the front matter). But **2a** and **2b** are *in-place* edits at existing sections
> deep in the file, and only **2c** is a new block. Apply all three; do not merge them into one.

## ITEM 2a — IN-PLACE block, inserted **under** `## Compiled Update — 2026-09-07 (wrap-up): SMT siblings make core-range fencing impossible; the build is the contention` (currently line 4612), **before** its `### SMT sibling topology …` H3 (4614)

```markdown
> **⚠ EXTENDED / PARTIALLY CORRECTED 2026-09-08 (INF-70 close-out) — the contention channel was
> DRAM BANDWIDTH, not cores, and the occupancy-based instrument this section prescribes is
> structurally blind to it.** The sibling-topology finding below stands unchanged. What it does not
> cover is the *channel*: measured 2026-09-08, **prefill was flat and decode fell −7%** under
> cross-campaign load. **No CPU-occupancy screen on either side can see that.** The remedy this
> section recommends — "a live process sample (`cc1plus`@100%, matched against `cpus_allowed`)" —
> catches build contention *when the channel is cores*. It cannot catch a bandwidth confound, and a
> better screen cannot fix it. **The fix is admission control, not screening.**

### The channel was DRAM bandwidth — so a better screen was never the remedy (2026-09-08)

**Two campaigns, correct pinning on both sides, no rule broken on either.** Measured floors:

| direction | floor, uncontended | floor, under the other campaign |
|---|---:|---:|
| our CPU A/A under their pinned GPU bench | **0.80%** | **7.223%** |
| their serving floor under our lock-holding CPU session | **3.536%** | **10.255%** |

**"Pinning controls placement, not contention"** (the autokernel session's framing, adopted here) —
**SMT siblings share the physical core**, so a correctly-pinned job on `96-183` is a correctly-pinned
job sitting on the other half of our cores. That is the half the section below already owns. The new
half is that the confound then travelled through **memory bandwidth**: prefill flat, decode **−7%**.
An instrument that samples CPU occupancy is watching the wrong resource, and it **passed both
contaminated arms** (recorded as incident (a) of the vacuous-instrument pattern on
[Benchmark Methodology](benchmark-methodology.md)).

> **★ Region-lock serialises those who CALL it; nothing constrains those who do not.**

With both campaigns serialised on a **mandated exclusive host**, an 8-core `python` + `opencode`
(`Cpus_allowed_list=0-191`, **belonging to neither campaign**) still cost an arm. At ~165 s/arm and a
1-in-6 hit rate in that block, that is a **~17% tax on every measurement campaign** — paid in arms
correctly identified as garbage, but which still had to be *run* to find that out. A lock cannot see
a process that never asks for it; only admission control can.

> **⚠ RECONCILE WITH MEAS-1, ABOVE.** The 2026-09-08 INF-70 audit section on this page states the
> MEAS-1 discriminator as "the **PEAK**, not the total foreign load — what hurts is a burst of 3218%
> (~32 cores…)". **That is an occupancy read.** It remains the right discriminator for the
> compile-contention case it was derived from — a `jobs=64` build *does* show up as an occupancy
> peak — but **if the channel is DRAM bandwidth, an occupancy peak is at best a proxy**, and a clean
> peak reading is not evidence of a clean window. The two statements are not in conflict, but they
> are not interchangeable: MEAS-1 discriminates *among observed foreign load*; it does not
> establish that foreign load was observable at all. Read them together, not separately.

Sibling cross-reference: [Inference Serving](inference-serving.md) records that the GPU lane's host
threads pin to SMT siblings **184-191** → physical cores **88-95** — the other 8 of our 96 bench
cores.

### Source References (2026-09-08, contention channel)

- [`progress/2026-09/2026-09-08-inf70-audit.md`](../progress/2026-09/2026-09-08-inf70-audit.md) — §8
  MEAS-6/OP-40/OP-41: the four floors, the ~17% third-party tax, and the DRAM-bandwidth channel
  (prefill flat, decode −7%).
- [`cpu-decode-roofline-program.md`](../handoffs/active/cpu-decode-roofline-program.md) — CLOSE-8
  (admission control, not screening; the row is a POINTER, not a second owner — the operator owns the
  admission-control design under OP-41 → INF-73 §3.4) and CLOSE-10 (the sampler's coverage gap).
- [`autokernel-unified-surface-program.md`](../handoffs/active/autokernel-unified-surface-program.md)
  — U4: the resource broker, arm-second budgets, and the structural resolution of OP-41.
- [`progress/2026-09/2026-09-08-ak-rebuild-20260828.md`](../progress/2026-09/2026-09-08-ak-rebuild-20260828.md)
  — the peer campaign's serving-floor recalibration and its side of the shared window.
```

## ITEM 2b — SUPERSESSION BANNER, inserted immediately **under** the heading `## The champion kernel: 1.4834× from two levers, and what the other two taught us (2026-09-06)` (line 4564)

> **Do NOT delete the section.** SKILL.md: "Never delete existing content without cause." The page's
> own idiom is an in-place banner (`hardware-optimization.md:323`, `:1038`, `:1047`, `:1107`).
> **Run the PART 3 blast-radius checklist before pasting this.**

```markdown
> **⚠ SUPERSEDED 2026-09-08 (INF-70 close-out) — every ratio in this section was measured on
> `champion3`, shim OFF, the old harness: a configuration that has now been RETIRED.**
> Retired figures: **1.4834×** (served), **1.6934×** (plain), **1.305×** (prefill), **1.4993×** and
> **1.5149×** (the HARNESS-1 recompute), **+4.27%** and **+4.50%**, **1.7151×** (CI [1.6882, 1.7439],
> 60/60 wins), the in-window absolute **33.370 t/s / 29.967 ms** and the **≈36.9 t/s** projection.
> **They are not wrong for what they measured** — they measured a configuration that no longer
> exists, and the supersession is marked rather than edited away so it stays visible.
>
> **Replaced by (18 launches, none dropped, unit = LAUNCH, between-launch precision, shim ON):**
>
> | ratio | value | 95% CI |
> |---|---:|---|
> | champion / pristine, **plain** | **2.1857×** | [2.1730, 2.1974] |
> | champion / pristine, **MTP** | **1.8255×** | [1.8081, 1.8399] |
> | champion **MTP / plain** | **1.5516×** | [1.5439, 1.5598] |
>
> See *The champion is `ef81196d5` + `GGML_NOHUGEPAGE_PROCESS=1` at launch* (2026-09-08) below for
> the conditions clause and the **two caveats that must travel with every one of these ratios**.
> **The `12.8% super-additivity excess` derived from 1.6934 in this section, and its cross-page twin
> on [Benchmark Methodology](benchmark-methodology.md), are derived figures of a retired ratio** —
> they are retained as a record of the *composition* finding (levers do not compose predictably),
> which is unaffected, but the excess must not be re-derived against the new plain ratio without a
> fresh leave-one-out.
```

**Also required on this edit**: the page's `**Last compiled**:` front-matter line (`:5`) currently
names **`1.5149×`** as "champion-3's corrected magnitude with a provisional magnitude". Amend that
parenthetical to name the 2026-09-08 close-out and the retirement of champion-3's figures.

## ITEM 2c — NEW H3 block. Insert into the top 2026-09-08 INF-70 block, immediately **after** `### The champion multiplier was understated — and the corrected magnitude is provisional` (line 49), so the "provisional" H3 is followed at once by what resolved it

```markdown
### The champion is `ef81196d5` **+ `GGML_NOHUGEPAGE_PROCESS=1` at launch** — the commit alone under-specifies it (2026-09-08 close-out)

> **`ef81196d5` + `GGML_NOHUGEPAGE_PROCESS=1` AT LAUNCH.**

**The artifact is COMMIT + LAUNCH RECIPE.** Quoting the commit without the recipe names a
**different, slower, ~8× noisier thing**. This resolves the "provisional magnitude" qualifier in the
H3 above: the quiet-window re-measurement was performed and the champion-3 figures it qualified are
now **superseded** (see the banner on *The champion kernel: 1.4834× …*, below).

**What it contains — all four lineages, by ancestry, not by cherry-pick:**

| lineage | tip | route |
|---|---|---|
| GPU | `bff30cebe` | merge base |
| champion-of-record | `445e93a8` | contained by ancestry |
| our CPU lineage | `inf70/champion3` @ `9c4f73e29` | the one `--no-ff` merge |
| frozen production | `0db32c06e` | contained by ancestry |

**Structural properties, verified**: zero files deleted · exactly one `--no-ff` merge · **no
cherry-picks** · 57 `akm-` keeps reachable · a pre-fold rollback tag on the fork. Production itself
is untouched at `0db32c06e`.

**FOLD-2 passed in full:**

| gate | scope | result |
|---|---|---|
| G1 | `SSM_SCAN` | **7/7**, including the K=4 / K=3 rollback |
| G2 | `MUL_MAT` | **1140/1140** |
| G3 | GDN | **39/39** |
| G4 | dispatch, observed | 27,516 nodes · `SSM_SCAN`=0 · recurrent ops on ROCm0 |
| G5 | tg128 | +0.052% — **not decisive**, and not claimed as one |

**Final measured numbers — 18 launches, none dropped**, pre-registered in `PREREG-FINAL.md` (frozen
15:05:15Z, sha256 `1d8f4ddc…`) **before** the region lock was taken; region held
15:05:39Z–16:12:47Z; all 24/24 rows complete on all 18 launches.

| configuration | n | **central t/s** | between-launch sd | 95% CI on the mean |
|---|---:|---:|---:|---|
| **champion plain, shim ON** | 6 | **27.893** | **0.609%** | ±0.487%  [27.758, 28.029] |
| **champion MTP, shim ON** | 6 | **43.281** | **0.356%** | ±0.285%  [43.157, 43.404] |
| pristine plain | 3 | 12.762 | 0.360% | ±0.408%  [12.710, 12.814] |
| pristine MTP | 3 | 23.709 | 0.926% | ±1.048%  [23.461, 23.957] |

Conditions that travel with every number: hot harness · 24-prompt production mix · token-weighted
decode · **unit = LAUNCH** · precision = **between-launch** · both screens live and `screened()`
applied · **GPU loop down** · baseline `ef81196d5` · shim ON verified per launch. **No hot absolute
is compared against a cold one** (hot reads **+4.36%** above cold on the same binary with
byte-identical output). MTP draft acceptance **82.1%**, identical on champion and pristine — a
property of the draft head and the prompt set, **not of the CPU levers**.

**★ HEADLINE FORM IS SIGN CLAIMS WITH BOUNDED MAGNITUDES (operator-ruled):** the champion beats
pristine by **≥117% plain (117.3%)** and **≥81% served-MTP (80.8%)**; **MTP beats plain by ≥54%
(54.4%)**. Bounds are the **lower ends of 95% bootstrap intervals over launches — not point
estimates. Do not restate them as "2.19×" in a headline.**

A completeness gate earned its place: every arm must carry 24 rows plus an `ARM_DONE` marker, and all
18 passed. An interim reading of an in-flight MTP arm looked like a **+7% outlier** (`draft_n` 2814
vs 3267) and would have entered the sd at face value — **a partial arm is a different token mix, not
a comparable one.**

> **⚠ TWO CAVEATS THAT MUST TRAVEL WITH EVERY RATIO ABOVE.**
>
> **Caveat 1 — the champion-vs-pristine ratio is RECIPE-TO-RECIPE, not knob-controlled.** Established
> *before* the run by inspecting the binaries rather than assuming: pristine `bin-p` (10221,
> `c51e4dabf`) contains **0 occurrences of `GGML_NOHUGEPAGE_PROCESS` and 0 of `GGML_NOHUGEPAGE`**, no
> marker; champion `bin-r1` (10303) contains both. **Neither THP knob exists in pristine, so equal
> shim state is impossible by construction.** The ratio is *champion under its canonical adopted
> recipe* vs *pristine as it shipped*. What **is** controlled: same harness, same window, adjacent
> interleaved launches (`CP PP CP PP CP PP CP CP CP`), same prompt set, same server flags, same host
> state.
> **★ RETROACTIVE COROLLARY: no champion-vs-pristine ratio this campaign ever quoted was
> knob-controlled. The THP difference sat inside all of them, unlabelled.**
>
> **Caveat 2 — `CHAMPION-DIVERGENCE` stays OPEN.** Plain ratio **2.1857×** here against the standing
> **1.7151×**. **Two conditions differ at once** — shim state *and* harness/window — so this run
> narrows the gap's *causes* without closing it. **Pristine reproduces across both (12.762 vs 12.366,
> +3.2%); the champion does not**, and an explanation that fits only one arm of a ratio is not an
> explanation. Adoption explains **part** of the champion's movement and its instability; **it is not
> asserted to explain all of it**, and the flag is **not closed**.

**CHAMP-2 is a RECIPE change, not a kernel change.** No fold, no branch, no rebuild — the champion
binary stays `ef81196d5`, bit-identical; the knob defaults **OFF (opt-in)** in that commit
(marker `INF70_CHAMPION3_PROCESS_THP_DISABLE=DEFAULT_OFF;OPT_IN=GGML_NOHUGEPAGE_PROCESS=1`), gated by
`common_thp_env_on("GGML_NOHUGEPAGE") && common_thp_env_opt_in("GGML_NOHUGEPAGE_PROCESS")`, and the
**recommended default is ON**. Delivery is per-session env, trivially reversible. A code-default flip
is the alternative but would need its own build, its own `THP_enabled` verification and a fresh
correctness gate — **none of which this campaign performed**, so the code route is *likely* but **not
tested** equivalent. Correctness: the shim changes **page backing, not arithmetic**; every
champion-state comparison across the campaign was **24/24 byte-identical**, including cross-binary,
and **no shim-ON-vs-OFF-specific correctness gate was run, and none is claimed**.

**Standing directive**: lever research remains **STOPPED** by operator directive — *"no more pure
kernel inference research until we have a FULLY consolidated champion."* The champion is now
consolidated; **lifting the directive is the operator's call.**

### Source References (2026-09-08, INF-70 close-out champion)

- [`progress/2026-09/2026-09-08-inf70-audit.md`](../progress/2026-09/2026-09-08-inf70-audit.md) —
  CLOSE-OUT §1 (the champion and its four lineages, FOLD-2 gates), §2 (the 18-launch table, the
  ratios and the bounded-magnitude headline form, the supersession table), §4 (CHAMP-2 adopted as a
  recipe change), §7 (the two caveats), §14 (the standing directive).
- [`cpu-decode-roofline-program.md`](../handoffs/active/cpu-decode-roofline-program.md) — CURRENT
  STATE header (the champion line, the supersession block naming every retired figure, the two
  caveats) and CLOSE-4 (label every champion-vs-pristine ratio recipe-to-recipe) / CLOSE-5
  (`CHAMPION-DIVERGENCE` stays open and needs an owner).
- [`docs/design/champion-consolidation-audit-20260908.md`](../docs/design/champion-consolidation-audit-20260908.md)
  — the consolidation audit: git custody of the fold, ancestry containment, and the `--branches`
  backup lesson.
- [`autokernel-unified-surface-program.md`](../handoffs/active/autokernel-unified-surface-program.md)
  — U1/U3: CPU keeps entering the durable bundle, and the `RUNTIME_CONFIG` arm type under which the
  THP shim was filed on the GPU surface (its first worked instance).
```

---
---

# PART 3 — BLAST-RADIUS CHECKLIST — run **before** pasting ITEM 2b

Derived by grep over `wiki/` in
`/mnt/raid0/llm/worktrees/audits/inf70-audit-20260902` on 2026-09-08. Governing rule:
`benchmark-methodology.md:3658` — *"retracting a number is not done until you chase what was derived
from it."*

| superseded figure | file:line | note |
|---|---|---|
| `1.4834×` | `wiki/hardware-optimization.md:4564` | the section **heading itself** — the banner goes directly under it |
| `1.4834×` | `wiki/hardware-optimization.md:4567` | body, served ratio vs pristine 23.870 t/s |
| `1.6934×` | `wiki/hardware-optimization.md:4569` | body, plain ratio |
| `1.6934` | `wiki/hardware-optimization.md:4590` | **DERIVED** — inside the super-additivity finding ("predicted 1.5017 … measured 1.6934 … 12.8% excess") |
| **`1.6934`** | **`wiki/benchmark-methodology.md:4308`** | **★ CROSS-PAGE DERIVED — VERIFIED PRESENT. The one most likely to be missed.** Section `## Measure the stack, not the parts — levers do not compose predictably (2026-09-07)`; re-uses 1.6934 in the same super-additivity/12.8%-excess derivation. If the plain ratio moves, this arithmetic moves with it. |
| `1.305×` prefill | `wiki/hardware-optimization.md:4569` | same sentence as the plain ratio |
| `1.4993×` | `wiki/hardware-optimization.md:49` | HARNESS-1 recompute sentence |
| `1.5149×` | `wiki/hardware-optimization.md:5` | **front-matter `**Last compiled**` digest** — must be amended with 2b |
| `1.5149×` | `wiki/hardware-optimization.md:26` | inside the AutoKernel unified-surface FOLD-0 paragraph |
| `1.5149×` | `wiki/hardware-optimization.md:49` | HARNESS-1 recompute sentence |
| `+4.27%` | `wiki/hardware-optimization.md:49` | "the +4.27% headline was never exposed" |
| `+4.50%` | `wiki/hardware-optimization.md:26` | FOLD-0 paragraph, twice in one sentence |
| `+4.50%` | `wiki/hardware-optimization.md:49` | "the independent recompute is +4.50%" |
| `1.7151×` | — | **NOT PRESENT anywhere under `wiki/`.** Verified by grep. It lives only in the handoff header and the close-out. No wiki edit needed; 2b names it so the retirement is complete, and Caveat 2 in 2c is where it is still load-bearing. |
| `33.370 t/s` (`/ 29.967 ms`) | — | **NOT PRESENT anywhere under `wiki/`.** Verified by grep for both `33.370` and `29.967`. |
| `≈36.9 t/s` projection | — | **NOT PRESENT under `wiki/`.** The only `36.9` hits are `agent-architecture.md:3057` and `:3061`, which are an unrelated **36.9% MAST citation-defect rate**. **Do not touch those two lines.** |

**Adjacent figures that ride with the retired champion-3 block** — chase these in the same pass, they
are the same measurement and are *not* separately superseded by name in the close-out:

| figure | file:line | note |
|---|---|---|
| `35.407 t/s / 28.24 ms` | `wiki/hardware-optimization.md:4566` | the retired served absolute the 1.4834× was computed from |
| `23.870 t/s / 41.90 ms` | `wiki/hardware-optimization.md:4567` | the retired pristine baseline. **Do not touch `:376` or `:2939`** — those are GEMM TFLOP/s numbers that coincidentally read 41.90/41.904 |
| `60/60 paired wins` | `wiki/hardware-optimization.md:4567`, `:49` | belongs to the retired configuration. **Do not touch `autonomous-research.md:528`, `:1020`, `hardware-optimization.md:277`** — unrelated `60/60` |
| `117/120` | `wiki/hardware-optimization.md:26`, `:49` | champion-3 per-prompt wins, retired configuration |
| `1.5017` predicted | `wiki/hardware-optimization.md:4589`, `wiki/benchmark-methodology.md:4307` | the super-additivity *prediction* half — moves with 1.6934 |
| `12.8% excess` | `wiki/hardware-optimization.md:4590`, `wiki/benchmark-methodology.md:4308` | the derived quantity itself |
| `23.16 t/s` / `1.876×` | `wiki/hardware-optimization.md:57`; `wiki/benchmark-methodology.md:4233`, `:4242`, `:4243` | **already half-recorded as superseded** at `:57` ("a build-10221 number, not a champion-3 number — it must not be quoted as the champion figure"). Extend that note rather than restating it; the benchmark-methodology hits are the ABA-reproduction record and should be annotated, not rewritten. |

**Checklist to execute, in order:**

1. `grep -rn '1\.4834\|1\.6934\|1\.305\|1\.4993\|1\.5149\|4\.27%\|4\.50%\|1\.7151\|33\.370\|29\.967' wiki/`
   — re-run at paste time; the line numbers above are as of 2026-09-08 and will shift once ITEM 2c is
   inserted near the top of the file.
2. Insert **2c first** (it is near line 49 and shifts every later line number), then re-run the grep,
   then insert **2b** and **2a** at their re-derived lines.
3. Amend `wiki/hardware-optimization.md:5` (`**Last compiled**`) — it names `1.5149×`.
4. Annotate `wiki/benchmark-methodology.md:4308` **in place** (the composition finding survives; the
   1.6934-derived excess does not carry forward) — do not delete the section.
5. **Do not touch**: `agent-architecture.md:3057`/`:3061` (36.9% MAST), `hardware-optimization.md:376`
   /`:2939` (41.90 TFLOP/s), `autonomous-research.md:528`/`:1020` and
   `hardware-optimization.md:277` (unrelated `60/60`).
6. Then lint (`lint_wiki.py`, pass 6 structural) and `compile_sources.py --check-manifest`.
   **Stop there — `--touch` is blocked on OP-34 (PART 4).**

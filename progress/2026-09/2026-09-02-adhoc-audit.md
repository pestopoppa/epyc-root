# 2026-09-02 — adhoc-audit: INF-70 authored and corrected; the INF-67 session's work published

Session type: ad-hoc audit session, **no lane worktree** (operator-spawned). Every commit below was
staged by exact pathspec after inspecting `git diff -- <file>`, per the shared-clone rule for
lane-less sessions. Nothing was staged wholesale and no peer hunk was swept.

## 1. INF-70 authored — the CPU decode roofline program (`c9d37292`)

Operator direction: no GPU offload, no speculative decoding — *"we can always tack on the drafter,
that's easy — I want the agent to tackle hard-to-get gains."* That reframes INF-67 from *the*
program to one axis of it.

**A roofline correction the operator caught mid-draft.** I had written the gap against the
**212 GB/s STREAM `copy`** figure. The operator challenged it (*"isn't the RAM bandwidth supposed to
be closer to 460 GB/s?"*) and was right: decode is a **read-only weight stream**, so the correct
denominator is the **~425 GB/s of DRAM traffic** this machine sustains, not a copy benchmark that
counts only bytes copied and hides the read half. That moves the ceiling from ~66 t/s to ~133 t/s
and the achieved fraction from ~20% to **~10%**.

| | value |
|---|---|
| measured decode (re-anchored, see §4) | ~95 ms/token (10.52 t/s, uniform IQ4_XS — the OP-32 baseline) |
| roofline | ~7.5 ms/token (3.2 GB read / 425 GB/s) |
| fraction of the machine converted to tokens | **~8%** |
| vs a DGX Spark | this box has MORE bandwidth (~425 vs ~273 GB/s) |

There is no hardware excuse anywhere in that gap. Three axes: **A** finish the fused decoder's
viability test; **B** the expert-path deficit (`mul_mat_id` measured at 5.6–17 GB/s = **1.3–4% of
roofline**, two orders down, which no bandwidth argument explains — the operator flagged this margin
on 2026-08-28 and it was never pursued); **C** measurement discipline.

## 2. INF-70 refined after the INF-67 wrap-up — and a correction of my own (`d507ea65`)

Their wrap-up recorded **`graph tg1 = 8.00 t/s at -t 48`** — ~125 ms/token *in the debug build*,
against the 74 ms clean-build figure. The instrumentation costs the graph **1.7×**.

That invalidates an extrapolation I gave them. I said the graph *"gains 4.7× from 1 thread (350 ms)
to 48 (74 ms)"* — **dividing a debug-build 1T number by a clean-build 48T number.** Same-build
scaling is **2.8×** (350 → 125 ms).

| quantity | value |
|---|---|
| same-build 1T → 48T scaling | **2.8×** (was reported 4.7×) |
| debug-build penalty at 48T | **1.69×** |
| fused/graph ratio at 1T, same build | **3.86×** |

The verdict is unchanged — the fused/graph ratio is the cleaner statement and it is stable across
thread counts — but the error is **exactly the class OP-32 was ratified to prevent** (hold the
artifact identical on both arms), committed by me one level up, at the *build*. It went into the
handoff as the worked example rather than being quietly fixed. Changes: Axis C gained **C3 — hold
the BUILD constant**; the **A-GATE** now requires both arms in the same build at each thread count;
the A1 trap section labels its 23–30 t/s figure a clean-build **target, not a measurement**.

Practical consequence: without C3 the session would have measured a same-build fused number against
a clean-build graph number, making a *successful* batched substitution look ~2× worse than it is.

## 3. Wrap-up: the INF-67 session's work was stranded

Their 10 wrap-up commits — including the final record I audited — sat **unpushed on local `main`**
while `origin/main` had moved on. Merged and published (superset-verified: their 2 progress files,
their handoff edits, my INF-70 handoff and row all present after the merge).

One conflict, in `inference-research-index.md`, resolved deliberately rather than mechanically:
their side carried a stale INF-67 `Next action` **and** an INF-68 row; `origin/main` had INF-68
completed and archived. Resolution keeps a single INF-67 row refreshed to current state and no
INF-68 row.

**Two false alarms I raised and then disproved, both from reading the working tree instead of git:**

| alarm | reality |
|---|---|
| "INF-66 dead link — `autokernel-rebuild-program.md` missing" | A **peer session's uncommitted deletion** in the shared clone. The file is present and committed on `origin/main`; a clean detached checkout passes `--check` at exit 0. No action. |
| "INF-68 is orphaned in `active/` with no index row" | It is correctly at `handoffs/completed/` on `origin/main` (0 open, 8 done, Option B ratified). I was reading a pre-merge working-tree copy from local `main`. |

Both are the same lesson, already on file: **resolve against git, not the filesystem — untracked and
pre-merge copies look identical to committed ones.** In a shared clone that failure mode is
constant, and it cost two spurious defect reports this session.

## 4. The wiki sweep found a third error — inside the correction for the second

Compiling the two new INF-67 progress sources into `wiki/hardware-optimization.md` surfaced a
sourcing failure in the fix I had just published. My C3 asserted a **"1.7× debug-build penalty"**
from 8.00 t/s (debug) vs **13.46 t/s (clean)**. But the INF-67 record states plainly:

> the documented 13.46 UD record doesn't reproduce on the current box — the 74 ms arithmetic needs
> re-anchoring before any perf claim (**same-window ratios are safe**)
> — `progress/2026-08/2026-08-31.md:228`

So that ratio crossed **both** a build boundary and a dead anchor. On the current box INF-68
measured **9.13 t/s (UD)** and **10.52 t/s (uniform IQ4_XS)** — against which even the *direction*
of a 1.7× is unsupported. **I wrote a rule about not crossing builds and then broke it twice while
writing it down.**

This also invalidated INF-70's headline: the roofline gap was anchored on 74 ms. Re-anchored to the
OP-32-ratified uniform baseline (~95 ms), the achieved fraction is **~8%, not ~10%** — the gap is
*worse* than I reported, which strengthens the program's premise rather than weakening it.

| INF-70 change | |
|---|---|
| headline table | re-anchored to 95 ms / 8%; the 74 ms row kept, struck through, marked **DOES NOT REPRODUCE — do not cite** |
| C3 | the 1.7× withdrawn; the rule restated on their same-build 1T control arm (350 vs 1350 ms) |
| A-GATE | no longer points at the 74 ms anchor |
| **C5 (new task)** | re-anchor the baseline in ONE clean build — a `-t 1`/`-t 48` sweep on the uniform artifact. Until it lands, **no absolute before/after claim is admissible; only same-window ratios.** |

What survives, all same-build and same-thread: fused/graph **3.86×** at 1T, graph thread scaling
**2.8×** (1T→48T). Two claims I could not source were kept out of the wiki page entirely: a
"~2.5 GB/token scratch churn" figure (my own code reading, absent from the sources — the sources
describe the ~215 ms "other" cost only qualitatively) and the withdrawn 1.7×.

**Three corrections, each found by the next step rather than by review.** The measurement rules were
not the thing in short supply — following them was.

## Deferred

Nothing blocked on me. Carried, each with a named blocker:

- **7 ambiguous artifacts (~128 GB)** — operator call, chiefly the 70 GB
  `unsloth/Qwen3.5-122B-A10B-GGUF/Q4_K_M` registry contradiction.
- **4 rollback-anchor holds (~99 GB)** — held by policy until the next promotion retires the anchor.
- **INF-70 execution** — belongs to the fused-decoder session, not this one.

# The measurement pin is not the champion

**Category**: `benchmark_methodology`
**Confidence**: verified (local inspection of build trees and run records, zero inference, zero builds)
**Date**: 2026-09-14
**Source**: INF-70 WRAP-10, `epyc-inference-research` `fc8c44de` + `932bf5c4` + `45d6ecce`
(`scripts/lib/qwen38_flash_next_recipe.py`); handoff `handoffs/active/cpu-decode-roofline-program.md`
(WRAP-10, MEAS-2)
**Folds into**: [Benchmark Methodology](../benchmark-methodology.md) — the provenance section, beside
"a lever's value is a property of the kernel it is measured in"

## The mechanism

A codified recipe pins a kernel by commit, build number and object digests, and quotes measured numbers
against that pin. When the champion moves, there are two names in play and they are **not
interchangeable**:

- the **current champion** — what production or the next campaign should run, and
- the **measurement pin** — the tree whose digests *and* served numbers were captured **together**.

The tempting edit is to relabel the pin to the new commit, because the constants "describe the champion"
and the champion has moved. That edit silently asserts an identity nothing ever measured: it says a number
came off a binary that never produced it. The failure is invisible because every other assertion in the
module keeps passing — the digests are still real digests, the numbers are still real numbers, and only
the *pairing* is fabricated.

The correct shape is to carry **both**, label which is which, and refuse to certify the one you cannot
prove:

- `CHAMPION_*` keeps naming the pin, with an explicit `CHAMPION_PIN_MEASURED_AT` record carrying
  `is_current_champion: False` and the role `ANCESTOR`.
- `CURRENT_CHAMPION` names the champion, and every measured entry keeps a `measured_at_commit` field.
- A single `CHAMPION_PIN_RESOLVED` flag is **fail-closed**: while it is `False`, a hard refusal
  (`assert_current_champion_identity()`) fires for any caller that would certify the current champion, and
  preflight prints an unmissable banner naming the pin, the champion, and the gap.

## Two findings this shape produced

**1. "No digested build exists" was the wrong gap.** The champion `ef81196d5` in fact had *two* digested
builds, one per surface, both build **10301**: a HIP build at `/mnt/raid0/llm/tmp/build-fold-ef81196d5`
(whose `llama-server` and `libllama-common` digests reproduce
`docs/design/champion-max-performance-20260908.md` byte for byte) and a CPU-surface build at
`/mnt/raid0/llm/tmp/build-champion-ef81196d5-cpu-20260909` with `GGML_HIP=OFF` and a cmake configuration
matching the recipe's own. Both were recorded rather than either being adopted as the pin.

**2. The real gap was narrower and worse: the headline's binary was a different build.** The 18-launch
final-characterisation run behind the canonical headline names its champion arm `bin-r1 (10303)` —
**build 10303, not 10301**. The numbers came off the `inf70/retest1-fix1` instrument tree
(`2516c9807`), which the recipe's own `do_not_fold` list already recorded as "the binary the final numbers
came from. Do NOT merge." The run prose calls that window `ef81196d5` because `ef81196d5` was its
*baseline*; the build number says otherwise. The one genuine `ef81196d5` CPU build postdates the window by
a day, appears in no run record, and nothing was ever measured on it.

So the flag stayed `False` for a reason no digest can fix: **closing it needs a measurement on a digested
CPU build of the champion, not another digest.**

**3. Capture the discrepant binary before classifying it.** The instrument tree was still on disk — in
scratch, one cleanup from gone. Digesting it (5 objects; 4 reproduced the digest file its own build script
had written at build time) and asking `git merge-base --is-ancestor` changed the verdict: `2516c9807`
**descends from** `ef81196d5` by exactly two *instrumentation* commits (a runtime knob page, and
runtime-switchable fixes). The headline's label is therefore an **unstated delta, not a wrong lineage** — a
better finding than the first reading, and available only because the artifact had not yet been collected.

It is still not a valid pin: two of that instrument's five knobs default ON, and that default *is* a measured
−2.136% regression, so "same source plus dead code" is unavailable as an argument, and no bit-identity with
either champion build was ever established. The transferable lesson is the **ordering**: capture, then
classify. An undigested scratch artifact can only be described by the prose that mislabelled it — and the
prose is the thing you are trying to check.

## Why a build number is the discriminating read

Both surfaces' builds report build **10301**; the headline's binary reports **10303**. Nothing in the prose
distinguished them — only the generated `common/build-info.cpp` in each build directory
(`LLAMA_BUILD_NUMBER`, `LLAMA_COMMIT`, `LLAMA_COMPILER`) and the run record's own binary label. That read
costs nothing, needs no execution of the binary, and is the cheapest available proof that two trees
described by the same commit are not the same artifact.

Corollary for surface-specific recipes: a HIP build ships a `libggml-cpu.so` like every llama.cpp build
does, and its digest **differs** from the CPU-surface build's at the same commit. A CPU recipe pinned to a
HIP build's bundled CPU backend is a wrong pin that passes every digest check.

## The rule

1. Never relabel a measured constant onto a later commit. Add `measured_at_commit`; keep the pin.
2. A pin is valid only if digests **and** numbers were captured on the same artifact. Digests alone do not
   make a pin.
3. State the gap in terms of what is actually missing. A gap text saying "no build exists" when two do is
   stale in a way every reader will act on.
4. Read the build number from `build-info.cpp`, not from the prose, and not by executing the binary.
5. Fail closed: the flag that says "I cannot prove this" must make something refuse, not merely warn in a
   comment.
6. **Digest the artifact a number came off while it still exists**, even when it is the "wrong" binary and
   especially when it lives in scratch. The digests outlive the tree; the classification improves once you
   have them.

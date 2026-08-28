# Designing an autonomous agent loop

**Convention, ratified 2026-08-28.** Agent-loop work **opens with a pseudocode
expression of the loop** — actors, what each reads, what gates it, where every
rejection goes, and which single step is expensive — and gets alignment on that block
*before* any plan is written around it.

The block is the alignment artifact. The plan is downstream of it.

**Why.** On the AutoKernel rebuild, one review round on the loop block surfaced three
design corrections that prose had hidden across several turns: the critic needed
**two** passes rather than one, every rejection needed an explicit **loopback** to the
actor that could act on it, and hypotheses needed to be **generated against a live
profile** rather than selected from a frozen list. None of those were visible in
paragraphs describing the same system.

---

## The four things a loop block must show

1. **Every actor, and what it reads.** An actor whose inputs are not listed is an
   actor you cannot reason about. AutoKernel's planner was a pure function of a
   context bundle that turned out to be empty — no refusal reasons, no memory, no
   profile — and that was invisible until the inputs were written down.
2. **Every gate, and what it rejects on.** A gate stated as "the critic reviews it"
   is not a gate; state the rejection grounds.
3. **Where every rejection GOES.** *A rejection with no visible destination is a
   bug.* In AutoKernel, `prior_authoring_refusals` filtered on a status the
   controller never wrote, so 22 of 23 authoring failures returned no reason and the
   planner re-derived rejected work blind. The arrow was missing from the design, so
   the defect was invisible in the code.
4. **Which single step costs real resources.** Every gate should sit before it. If a
   gate sits after the expensive step, say why.

## Budgets

Name each budget and keep them **independent**. AutoKernel charged `critic_revise` to
the same 3-strike counter as a real authoring failure, so a hypothesis could be
retired *for the critic doing its job* — in v33, three turns retired
`akh-v2-q5-type-specific-dequant` without ever testing it.

If two failures have different causes, they need different counters.

## Retirement

Distinguish retiring an **attempt** from retiring a **hypothesis**. A bad patch is
not evidence against the idea it was trying to implement. And a hypothesis that
exhausts its budget should re-enter the pool carrying its rejection history, not
disappear: the profile moves, and what was unsupported last week may be the hotspot
this week.

---

## The reference block

This is the AutoKernel discovery loop, and it is **normative**: if an implementation
and this block disagree, the block wins until it is deliberately amended in
[`handoffs/active/autokernel-rebuild-program.md`](../../../handoffs/active/autokernel-rebuild-program.md).

```
when the champion changes (at most weekly otherwise):
    rocprofv3 the champion → ranked hotspots

each iteration, planner works in a worktree with the full toolbox:
    reads   champion · experiments.md · hotspots · hypotheses/inbox/
    probes  FREELY — llama-bench, rocprofv3, test-backend-ops -o OP --perf,
            llvm-objdump for VGPR/occupancy, env-flag sweeps. Nothing gated.
    forms   hypothesis H, backed by evidence it gathered itself

HYPOTHESIS REVIEW LOOP · budget 3 rounds
    CRITIC PASS 1 reviews H — no patch exists yet.
      rejects on: already measured · mechanism unsupported by the profile ·
        no falsifier · wrong surface · already present in v9
      REJECT → reason returned VERBATIM to the planner, which refines or
        regenerates H and re-enters. It still has the toolbox and may go
        probe to answer the objection.
      BUDGET SPENT → record refused_at_formation with every reason and pick a
        DIFFERENT hypothesis. H is NOT retired; it re-enters the pool carrying
        its rejection history and may be revisited once the profile moves.
      cost of a rejection: one planner call. No patch, no build, no GPU.

    planner writes patch P implementing the accepted H

PATCH REVIEW LOOP · budget 2 rounds
    CRITIC PASS 2 reviews the committed diff P.
      rejects on: P does not implement the accepted mechanism · scope creep ·
        correctness risk · edits a file that must stay byte-identical to production
      REJECT → reason returned VERBATIM; planner rewrites P. H is untouched —
        a bad patch is not evidence against the idea.
      BUDGET SPENT → record refused_at_authoring and hand control BACK to the
        hypothesis loop, so H can be refined knowing it could not be implemented
        cleanly.
      cost of a rejection: one authoring call. No build, no GPU.

    build (ccache, -j64)   → fails? reason returns to the planner, rewrite P
    test-backend-ops       → fails? reason returns to the planner, rewrite P
    A/B alternating, n≥5   ← the only GPU spend in the whole iteration

    keep → commit onto the champion branch
    else → negative, with mechanism and sample vector, into experiments.md
```

**Three separate budgets, none feeding another.** **Every rejection returns its reason
to the actor that can act on it**, and nothing is retired without the planner having
seen why. Compile and correctness failures loop back the same way; they need no
critic, because the toolchain's own message is the reason.

Pass 2 sits **before** the build, since the build is the most expensive step. The
tradeoff — it judges the diff without knowing it compiles — is acceptable, because a
compile failure is cheap and returns automatically.

`n≥5` is not a preference. The instrument's own A/A noise floor, measured 2026-08-28
at n=20 alternating pairs, is p95 **2.175%** on prefill and **3.452%** on decode for a
single pair; 4 of 20 pure-noise decode pairs already exceeded the loop's 3%
nomination bar. Five pairs bring those to 0.75% and 1.85%. See
`artifacts/autokernel-aa-noise-floor/` in epyc-inference-research.

---

## What makes this shape work

**The champion tree is the only durable state.** No intermediate artifact needs to be
trusted, because there is none. The champion is a git commit: anyone can check it out
and re-measure it. "Did we improve?" is answered by rebuilding and benching, not by
reading a receipt about a run that happened last Tuesday.

That is the general principle: **prefer verification by reproduction to verification
by proof.** Proof requires every intermediate step to be sealed and refuse-on-doubt,
so its cost grows with the number of steps and has no natural stopping point.
Reproduction requires only that you kept the recipe — cost is one re-run, and it is
bounded. AutoKernel chose proof where reproduction was available: a `llama-bench`
re-run costs 90 seconds, while proving a run was honest cost 3,869 lines in
`gpu_source_evidence.py` to deliver a single float.

**The only durable output is a row saying faster-or-not.** This is the anti-regrowth
property, and it is a design requirement rather than an aesthetic one. If the loop's
sole product is an entry in `experiments.md` and a commit on the champion branch, no
agent can spend a week on receipts and call it progress.

**Hypotheses are generated, not selected from a frozen list.** A static portfolio goes
stale exactly when the loop starts working, because every accepted patch moves the
hotspot distribution. Generating against a live profile also dissolves the
do-not-repeat ledger: a planner that reads its own history sees what was tried. Dedup
is a property of having memory, not a mechanism you install.

---

## Related

- [`handoffs/active/autokernel-rebuild-program.md`](../../../handoffs/active/autokernel-rebuild-program.md) — the program this convention came out of, with the five verified causes.
- [`docs/reference/kernel-freeze-runbook.md`](../../reference/kernel-freeze-runbook.md) — where the custody belongs: the promotion boundary, seven steps, and it shipped v7, v8 and v9.
- `agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out* — the other place this project writes down a working shape rather than describing it.

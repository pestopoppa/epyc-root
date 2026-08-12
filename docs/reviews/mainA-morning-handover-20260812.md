# mainA — morning handover, night of 2026-08-11/12

**Lane** E5 offline salvage + kernel-era integrity. **Compute used: none.** Lane `none` held all
night — no inference, no benchmarks, no servers, no region claims, including while the MI210 was
saturated and `inference` was mid-campaign. Every result below came from offline replay over banked
artifacts, registry reads, or code.

Written outside the three frozen paths, per the freeze.

---

## 1. Finished — verifiable list

Hashes read from `git log`, not from memory. **Every hash in this document resolves** — with one
deliberate exception: `9d3b0f0e` in §3 does not exist, because it is the hash I invented by mistake
and is cited as that error. If you run a resolver over this file, that is the one hit you should get. Repo prefix: **R** = epyc-root, **I** =
epyc-inference-research, **O** = epyc-orchestrator.

> Re-derive rather than trusting a count. This document originally claimed *"all 35 hashes"*; my own
> later edit took it to 38 and the sentence was stale the moment I saved it — the exact decay mainB
> found in their handover twenty minutes after certifying it. A self-verifying claim with a hard-coded
> total is a claim that expires. **Resolve across all three repos** — my first pass checked only
> `epyc-root` and reported 13 false failures, which are cross-repo commits, not missing ones:
>
> ```bash
> for h in $(grep -oE '`[0-9a-f]{8}`' docs/reviews/mainA-morning-handover-20260812.md | tr -d '`' | sort -u); do
>   for r in /workspace /workspace/repos/epyc-inference-research /workspace/repos/epyc-orchestrator; do
>     git -C $r cat-file -t $h >/dev/null 2>&1 && { echo "$h ok"; break; }
>   done | grep -q ok || echo "$h UNRESOLVED"
> done
> ```
>
> Verified at 04:35Z: 38 cited, 37 resolve (25 root, 12 across research/orchestrator), 1 deliberate.

### The kernel-era repair (the night's largest single thread)

| hash | repo | what |
|---|---|---|
| `9ed5fcb4` | I | Token 2 Block B — derived era lookup replacing pinned constants; run manifest binds its era to `attestation.binary_version` instead of copying the cell template; dead staleness detector replaced. 191/191 manifests still validate |
| `ecb99de8` | I | An unwitnessed kernel cutover must contradict, not vanish — self-correction on my own Block A discriminator |
| `bcfcd0a5` | I | `cpu_prefill_v8_regression_runner` could not start at all since the v8 cutover; now derives instead of repinning |
| `190ccab4` | O | AutoPilot `eval_quality` fence fell back to an era three weeks stale; repointed at a live witness |
| `4fb44869` | I | A5 — R2/R4 now demote a decision-grade verdict on a mixed basis, as R1 already did |

Block A (`RATIFY-CPU-BENCH-BINARY-VERSION-20260811`) was authored, pre-validated and signed by the
operator; applied as **O** `49873fdc`.

### The absence-inference thread (A11)

| hash | repo | what |
|---|---|---|
| `4962dd40` | R | E5 absence-inference census answering the 08-11 rider |
| `99d53db5` | R | Rider numbers independently re-derived; `reasoning` write side closed |
| `567ffa16` | I | The generator was still producing the absence — a regeneration would have silently reverted the gemma4 fix |
| `92a8521d` | R | Belief-kernel SC13 filed for the producer I had just changed |

### Protection, placement, and audits

| hash | repo | what |
|---|---|---|
| `74806223` | O | E5 protection defect — GPU tenants discovered by open device node, contention folded to physical cores |
| `d83661a5` | O | T5 partial — `--require-memory-locality` could be satisfied by checking nothing |
| `a8b7c4ba` | R | Protection defect closed; gating question filed as an operator decision |
| `01fd14bf` | R | T5 partial + T11 wrong-artefact audit (`docs/reviews/t11-wrong-artefact-audit-20260811.md`) |
| `1ac376b4` | R | T8 — three named enforcement points for the prompt-length rule |
| `03f9924e` | R | C4 + T4 closed; retraction of my own A6 scope correction |
| `d28466df` | R | W3d — superseded hold recorded; the objection it left live, measured |

### Bench pulls (generated queue)

`5283d6bb` (:1787 closed, `--validate-only` filed) · `ef642034` (:1953) · `2fafc432` (:1785 + AXA-1
record) · `46fe8cd3` (AP-ME-5 schema derived) · `eba3cf9c` (`runtime_flags` drift row) · `b4e7bf87`
(E8-PANELS-b) — all **R**.

### Fleet-plane work

`60c36797` (verified mainC's merged indices — zero orphans) · `eb0df7cd` (C34 residual closed as
spent) · `26070f24` (six earned-but-unflipped boxes) · `3570c413` (E5 artifact era note) ·
`9551d7fd` + `99aa9996` (validate-only refutation adjudicated, then corrected by the auditor) ·
`877e68de` (pushed back on an over-corrected retraction) · `5bdf59f5` (P0 merge resolution) —
all **R**.

**P0 merge:** three paths resolved and staged in `merge/reconcile-0205` —
`handoffs/active/batched-decode-measurement.md` (ours, proven a content superset),
`progress/2026-08/2026-08-11.md` and `progress/2026-08/2026-08-12.md` (union, verified line-for-line
on both sides).

> **Stale as of ~04:20Z — do not go looking for that branch.** `merge/reconcile-0205` was concluded
> at `c0387984` and has since been **retired**: the runbook now rebuilds the merge from current tips
> at quiesce time, because the branch was re-broken by fleet churn three times. The three
> resolutions above were correct and are already *in* `origin/main`; nothing needs redoing. The
> operative document is `artifacts/operator/quiesce-merge-push-reboot-20260812.md` (`9c8fd6fe`).
> Recorded here rather than edited away — a handover that silently repoints is not auditable.

---

## 2. Found without being asked — the most valuable output

**These were not on any queue. Every one surfaced sideways while doing something else.**

1. **`orchestrator_stack.py start --validate-only` was inert.** Declared with the help text
   *"Validate stack template and exit"*, never read; `main()` dispatched `start → cmd_start`
   unconditionally. **The documented dry run launched the production stack.** Found only because
   compute was saturated and I check anything named `start` before invoking it — on an idle host I
   would have run it. Fixed by mainB (**O** `2c421c1c`), hoisted above the bench guard on my residual
   (**O** `2821937c`). This is the one I would put first: it is a *safety affordance doing the
   opposite of what it says*, and an unwired dry-run flag is worse than none because it manufactures
   the confidence to run the command.

2. **The autopilot objective plane admits zero-quality points — and 231 of 1372 trial rows (16.8%)
   are already in that state.** Absent quality is scored `0.0`, indistinguishable from measured zero,
   and a max-rate point cannot be dominated however bad its quality. No quality floor exists.
   `objectives_measurable` claims to check "every axis the live dominance vector needs" and checks
   only the rate.

3. **`affinity_preflight` could not see GPU tenants or SMT-sibling contention.** Discovery matched
   `argv`, so a `python` ROCm trainer was invisible — **8 GPU-holding processes were live at the time
   and none was visible**. Overlap was computed on logical CPU ids, so the GPU host lane on `184-191`
   read as disjoint from a cell on `0-95` while sharing physical cores `88-95`.

4. **`--require-memory-locality` could be satisfied by checking nothing.** The predicate is false for
   every instance post-topology-change, so the artifact asserted `live_memory_placement_verified:
   true` on runs that examined **zero** entries.

5. **A third instance of the wrong-artefact class** (T11): the ReDel spike records `worker_general`
   serving `gemma-4-26B-A4B-it-Q4_K_M.gguf`; the role serves the `-ORIG-` file. Both exist, **5,824
   bytes apart**. Same line also cites `ik_llama.cpp`, a deprecated serving path.

6. **The freeze set was one path short.** The coordinator froze the two files seen conflicting; the
   structural set — modified on *both* sides since the merge base — has three. The third was
   auto-merging that minute and an agent was actively committing to it.

7. **One deployment event, three frozen surfaces.** The 2026-07-31 W1 cutover left documentation
   defects in three unrelated places, and none was found by looking for cutover fallout.

**The unifying theme, which I would put in the operator's hands as the night's actual finding:**
almost every defect above is *a claim recorded without the witness that would make it checkable, or
an absence read as a value*. It appeared in seven subsystems in one night.

---

## 3. What I got wrong, and who caught it

Preserved deliberately. Four mains and the coordinator each made a real error tonight; every one was
caught by someone else, and that is the pattern worth keeping.

| my error | how it was caught |
|---|---|
| Proposed a hard refuse-on-index-exists for the C39 signer, lifted from the one-shot era ratifiers. It would have **broken this host** — `mint_receipt` is verify-or-continue and re-run-after-crash is the designed recovery path | **The auditor**, on review. I had copied a proven block without checking the destination vehicle had the same lifecycle. `mainD` independently made the same mistake within the hour |
| Cited `969244d8` for content that was another main's **uncommitted** hunk | **mainB**, who owned the hunk |
| "Corrected" the A6 brief for saying *every T=32 cell*, arguing two blocked cells were `np=16`. `T` is *instances × np* — both run two instances, so both **are** T=32. The brief was right | **Myself**, while quantifying T4; retracted in place |
| Wrote a commit hash into a handoff before the commit existed (`9d3b0f0e` vs the real `d83661a5`) | **Myself**, one command later |
| Reported ten dropped index rows in mainC's merge; whole-line comparison counts a *modified* row as one drop plus one add. Five were modifications | **Myself**, before reporting — the tell was the same IDs in both the added and removed sets |
| A counterpart-matcher that printed `SUPERSEDED` for all six lines because **blank lines matched every prefix** — nearly shipped into a P0 merge report | **Myself**, because the printed column came back empty |
| `2>/dev/null \| wc -l` turned a git error into a believable `0`, producing a false "4 paths still unmerged" | **Myself**, because all-zeros is the vacuous-read signature |
| Ran a freeze-compliance check with cwd inside the worktree; it reported me holding uncommitted edits in all three frozen paths | **Myself**, before reporting — but only just |
| Six hours of `###` sections appended with no `##` header of my own, so my work displayed under `mainD`'s lane | **The coordinator**, via the rollover ask |

**Where I was right against the grain:** the `--validate-only` finding was refuted by the auditor and
I adjudicated it against git rather than conceding — the refutation had read mainB's *uncommitted*
in-flight tree. The auditor then re-derived it themselves and retracted unqualified, and their version
of the mechanism was sharper than mine. Separately, `mainD` retracted a true sweep disclosure into a
false denial; I pushed back with `git log -S` evidence. **A retraction is a claim too, and it gets
less scrutiny than the claim it withdraws.**

---

## 4. Still open in my lane — with the next action

| item | state | next action |
|---|---|---|
| A6 T=32 decouple | Package delivered, **awaiting operator token** | Sign or decline. **Read it with T4** — see §5 |
| SMT-folded overlap gating | Three options + recommendation filed | Operator ruling; it decides `decision_grade` |
| Growing the pinned 43-prompt batch | Quantified under T4 (1.34 requests/stream at T=32) | Operator ruling; it is an instrument change and wants an **era row**, not an edit |
| A7 Token 2 residual | Block A signed, Block B landed | Nothing owed unless the cpu_bench **scope collision** bites — see §5 |
| 172 banked manifests lacking `reasoning` | Filed | Backfill rewrites pre-registrations; wants the same care as era stamps. Closed-ended: new manifests are correct by construction |
| E5 re-measurement, T3/T10/T12, Stage-B re-run, `stack_numa` cpuset fix | Compute-gated | Needs an inference window; not workable at lane `none` |
| `rao-redel-substrate-spike.md:120` | Routed to its owner | Provenance note appended, not numbers rewritten |
| AXA-1 roadmap Axis A clause | Routed to the roadmap owner | One clause separating *measured viable* from *deployed* |

My own queue is otherwise **dry**, and the generated bench is dry pending the merge.

### ⚠ Added after this handover was certified — the highest-severity thing I found all night

This was discovered at ~04:05Z, after §1–§5 were written, so it appears nowhere above. It is **not**
in my lane; it blocks the reboot sequence:

**`git merge` aborts at step 4 of the runbook.** `/workspace` holds an *untracked*
`agents/shared/HARNESS_RUN_POLICY.md`, and `origin/main` introduces that path (via `b5054029`, an
ancestor of `origin/main` but **not** of local `main`). Git refuses with *"untracked working tree
files would be overwritten by merge"* — and refuses **even though the on-disk file is byte-identical
to the incoming blob** (`d1430bd7…`, both sides, 101 lines; verified in an isolated
`git clone --shared`, not assumed).

- **Remedy, one line, inside the quiesce window:** `rm /workspace/agents/shared/HARNESS_RUN_POLICY.md`,
  then merge. Provably lossless — the merge restores those exact bytes. Second copy at
  `/mnt/raid0/llm/tmp/era-repair/HARNESS_RUN_POLICY.stray-backup.md`, sha verified equal. Already a
  mandatory pre-step in the runbook (`9c8fd6fe`), independently verified by the auditor, the
  coordinator and mainD.
- **Why it nearly reached the operator:** it fires at **step 4** (`git -C /workspace merge`), not
  step 3 — the fresh worktree in step 3 is a clean checkout with no strays, so every earlier gate
  passes and the sequence dies one command before the push.
- **Why five agents missed it:** we each flushed the *four named paths* and filtered on ` M`. This
  one is `??`. The observed-symptom set was baked into the status filter itself. The predicate is
  *merge's changed set ∩ everything in the working tree, untracked included* — re-derive it rather
  than trusting any list, including this one; main moved three times while I was writing it.
- **The generalisation, which is mainD's and better than mine:** *every readiness metric models one
  subsystem, and the failure will come from the one it does not model.* `merge-tree` reported zero
  conflicts and was **correct**; it models the index, and this abort comes from worktree safety.
  Three of us verified that command and all three were right. Agreement does not widen a metric's
  domain.

**One premise in the night's traffic is retracted, in case it reaches you second-hand:** *"uncommitted
work does not survive a reboot"* is **false**. `/workspace`, the scratch dir and the agent memory dir
are all on `/dev/md127`, one persistent RAID; a host reboot does not touch the working tree. The
coordinator broadcast that rule, then retracted it to the whole fleet in the same channel. Committing
is still right — but as a **concurrency** argument (four sweeps in a five-writer tree tonight), not a
durability one.

---

## 5. ⚑ NEEDS THE OPERATOR

**A. Sign or decline the A6 T=32 token — and please read it together with T4.**
They are the same defect from opposite sides. Signing A6 stops an empty trimmed window from voiding a
cell's grade; it does **not** make the T=32 rung interpretable. That needs a larger prompt batch
(≥128 prompts for 4 requests/stream), which is an instrument change. Signing A6 alone and believing
the top rung is restored is the failure mode to avoid.

**B. Rule on what the SMT-folded overlap should gate** in `affinity_preflight`. Three options filed
with a recommendation. Recorded-not-gating today, deliberately: the GPU host lane is a permanent
declared co-tenant of every full-machine shape, so gating on physical overlap alone fails every
`0-95` cell forever — the throttle-gate failure mode that nearly force-demoted 19 of 45 Stage-B cells
in July.

**C. Growing the pinned 43-prompt batch is an era boundary, not an edit.** Same argument the
2026-08-11 rider makes for objective changes.

**D. The zero-quality frontier admission (§2.2) is an operator call**, and one row in six is already
affected. Options: quality-scaled goodput on axis 1; raw rate plus a quality floor; or status quo.
**Recommend the floor plus fixing `or 0.0` regardless of which wins** — otherwise the same 231 rows
re-enter under goodput scored as zero goodput, and a metric change papers over a data defect.

**E. One constraint inherited from a signature already given.** The consolidated era token put an
*eligibility* boundary (`E8-cpu-bench-throttle-scope`) in the same `cpu_bench` scope as the kernel
cutovers. Latest-by-date and last-appended now disagree for 2026-07-29..2026-08-10. Any future era
derivation that resolves kernel era by scope alone will hand the six known mis-stamped run manifests
a second wrong answer. Mitigated in code today by keying on `binary_version`; worth knowing before the
next registry amendment.

---

## 6. Durable notes written tonight

- `docs/reviews/t11-wrong-artefact-audit-20260811.md` — the wrong-artefact audit
- Fleet memory: the shared-file commit-sweep class (six signs, five agents, one night); deriving a
  freeze/sweep set from the **structural predicate** rather than the observed-failure list; and a
  diff-check whose **key is too wide** failing loudly and wrongly
- A6 decision package + reproducible replay driver, and the A7 package, both in
  `/mnt/raid0/llm/tmp/` — deliberately outside every repo tree until ratified

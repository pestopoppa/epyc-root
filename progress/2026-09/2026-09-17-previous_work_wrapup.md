# Previous AutoKernel Dream-RSI / v22 wrap-up — 2026-09-17

## Scope

This checkpoint closes the prior AutoKernel Dream-RSI/intake work through the v22
relaunch. It does not include the new AK-PORT implementation work now running in
parallel, and it does not change application code, the production kernel, the live
search policy, or the running loop.

## Durable findings

| Area | Result | Evidence / disposition |
|---|---|---|
| CPU recipe diagnostic | 24 threads were −6.391% vs 48 threads across five alternating pairs; clean 32-thread rescreen was −2.713% vs bracketing 48-thread arms | Diagnostic only; placement/foreign-load validity remains `unproven`; no recipe or champion change |
| Lineage telemetry | Spawn parent, branch, and width×depth trajectory are now producer-authored prospectively | Research `85c7b91e`, receipt `a6288858`; RB-lineage checklist closed; strict read-side consumer remains open |
| Observed momentum | 87 native serving A/B rows admitted to 24 epoch-local instrument/anchor epochs after correcting the v1/v2 schema mismatch | Self-hashed receipt `/mnt/raid0/llm/tmp/ak-glm-observed-momentum-20260917-v1.json` plus sidecar; diagnostic only, no cross-epoch uplift |
| Runtime calibration | v21 direct calibration was stopped before any valid comparison because the default declaration implied 800 full GLM launches | Retained as invalid setup evidence; zero completed launches, one failed launch, unresolved pending member; no old floor reused |
| v22 source arms | Batch 0 HALF **+0.296%** and batch 1 FULL **+0.064%** remained `keep_candidate` only | No source keep, champion advance, or promotion; 28 prior keeps and source tip `614ff2ba02e0` preserved |
| v22 stop boundary | Batch-2 STOP was requested when the generic `MUL_MAT` oracle was found to be mismatched to the GDN/row-tiled source edit | Not a null and not evidence against GDN; source-aware oracle repair is owned by existing AK-PORT-1/2 work |
| RPUCG / ROCm eval | SimpleTES ROCm path was registered study-only; RPUCG A/B was not claimed because r19 lacks evaluated DAG parent/visit state | AR-ROCm-eval closed; AR-RPUCG remains data-gated; no external benchmark re-measure |
| Adaptive / cost / replay controls | No retrospective policy uplift, cost-credit score, plateau A/B, or N=10 replay was computed | AK-WM-2a is `state:error` with empty control journal and no prefix-visible choice/cost state; actor lacks prospective turn/outcome identity |

## Handoff and checklist sync

`handoffs/active/autokernel-research-loop.md` now records the two candidate-only
values and the batch-2 stop boundary as evidence, without inventing completed
research tasks merely for recording them. Existing
AK-PORT-1/2 owns the source-aware oracle repair; no duplicate handoff or index row was
filed. The RB-lineage and AR-ROCm-eval items already had their completed checkbox state
on the fetched main. No active handoff was archived or compacted.

## Validation and boundaries

- `git diff --check` passes for this documentation-only patch.
- The README freshness check was clean; no README was changed. The incremental
  wiki scanner warned that linked-worktree mtimes are invalid, so only its
  content-hash drift should be used.
- The delegated read-only wiki scan found one newly drifted source at its
  checkpoint. The parent will run the controlled compilation/manifest update
  after integrating concurrent work; no manifest or watermark was mutated here.
- Index rows and generated index state were not edited. Proposed parent-owned next-action
  refreshes are reported separately with this checkpoint.

### Parent-owned index proposal (prepared, not applied)

These are thin-row `Next action` replacements only; the parent session owns applying them
and regenerating index state alongside the concurrent AK-PORT rows. They are intentionally
not changes in this branch:

```diff
-| INF-06 | autokernel research loop | [autokernel-research-loop.md](autokernel-research-loop.md) | AK-INST-1 still unproven; no run is live — loop relaunch on champion ef81196d5 is a separate operator go, nothing here schedules it | INF-48, EVL-47, INF-64 |
+| INF-06 | autokernel research loop | [autokernel-research-loop.md](autokernel-research-loop.md) | Repair v22 source-aware operation-oracle routing; then resume only under a named campaign and preserve 28 keeps/no v22 keep yet | INF-48, EVL-47, INF-64 |
-| INF-03 | agentic rocm kernel authoring | [agentic-rocm-kernel-authoring.md](agentic-rocm-kernel-authoring.md) | Preserve r19; implement the relayed zero-profiler, counter-gated, paired-ablation C5 backlog | INF-48, EVL-47 |
+| INF-03 | agentic rocm kernel authoring | [agentic-rocm-kernel-authoring.md](agentic-rocm-kernel-authoring.md) | Preserve r19; finish the relayed zero-profiler, counter-gated, paired-ablation C5 backlog; AR-RPUCG remains data-gated | INF-48, EVL-47 |
-| EVL-47 | vidya belief substrate program | [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) | SC65/SC66 write-side wirings; SC76 claim_anchor re-verifier (root of SC77–SC80 intake checks) | EVL-50 |
+| EVL-47 | vidya belief substrate program | [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) | Finish prospective AutoKernel lineage source/outcome binding; SC87 producer is tested, strict read-side consumer remains open | EVL-50 |
```

## Explicit non-claims and next boundary

The v22 candidate values are not promotion evidence, and v22 does not establish 20
healthy loops. Resume only after the source-aware oracle repair and the normal
compile → correctness → matched timing ladder are proven by the AK-PORT workers. This
is an external concurrent implementation boundary, not a request to relax measurement
or promotion controls.

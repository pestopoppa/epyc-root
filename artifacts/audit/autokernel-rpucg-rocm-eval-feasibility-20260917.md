# RPUCG / ROCm evaluator feasibility — 2026-09-17

Scope: read-only feasibility review of `AR-RPUCG` and `AR-ROCm-eval` at
`handoffs/active/agentic-rocm-kernel-authoring.md:1133-1134` (intake-1454).
No live
policy, evaluator registration, build, benchmark, or GPU use.

## AR-RPUCG: no honest same-task offline A/B identified

The pinned [SimpleTES repository](https://github.com/wq-will/SimpleTES) has
`rpucg` as a DAG-aware, selection-only history-to-prompt policy; it does not
re-execute selected nodes. The intake pins the implementation at
`47d3413da1d85dc24341219d47452d2601e56a57` (`rpucg.py:48,202` in
intake-1454) and documents its
bottom-up discounted value, percentile ranks, one-hop anti-inbreeding, and
post-batch visit updates. This is not equivalent to our champion-selection
gate.

The scoped AutoKernel controller review found a **possible DAG carrier**, not
an A/B input: `controller/kernelfoundry_arena.py` forwards each evaluated
program's `parent_id` to upstream MAP-Elites `add_with_parent`
(`controller/kernelfoundry_arena.py:270-276`); its documented EvoEngineer arm
retains rank-probability parent selection
(`controller/ARENA_INTEGRATION.md:593`). The reviewed
native GLM serial continuations record terminal dispositions and mechanism
IDs, but not a same-task set of evaluated nodes with comparable scores,
parent edges, candidate eligibility at each choice, and the exact incumbent
selector's choice trace. No such complete snapshot was identified here.

Therefore a pure RPUCG selector could be written, but comparing it with the
current heuristic would at best compare selections on an invented graph. No
code is justified yet. The minimal legitimate input is one immutable
nonpromotable MI210 task snapshot containing, per evaluated node: task/surface
and evaluation-recipe identity, score and direction, parent ID, completion
ordinal, prompt-eligibility prefix, and incumbent selector choice/visit state.
Only then freeze one candidate pool and score both selectors' **parent choices**
offline. Those choices do not imply counterfactual child performance, so a
performance A/B still requires a separately authorized nonpromotable run.

## AR-ROCm-eval: pin mismatch; study-only

The pinned source audit in intake-1454 records a ROCm branch in `run_eval.py`
that calls `profile_program_roc`, with `AMD_REQUIREMENTS` pinned to
**ROCm 6.2.4**.
Issue #6's MI300 outcome/config is a gfx942 port clue, not MI210/gfx90a
performance evidence. The current root handoff records our host runtime as
**6.2.0-66** and side-loaded `rocprof` v1 / `rocprofv2` binaries matched to
that runtime exactly (`handoffs/active/rocm-verify-profile-backend.md:204-248`).
It also records 465 enumerated gfx90a counters and
known `rocprofv2` exit-139 cases for whole-model Qwen prefill and IQ2_XXS
capture. Thus neither the SimpleTES 6.2.4 dependency nor its profiling
output can be assumed byte- or schema-compatible with our 6.2.0-66
profiler seam. [AMD's ROCm 6.2.4 compatibility matrix](https://rocm.docs.amd.com/en/docs-6.2.4/compatibility/compatibility-matrix.html)
lists gfx90a support, but that establishes platform support, not this
application's profiler correctness or equivalence.

The profiler route is **identified**, not open: pinned
[`run_eval.py:375-447`](https://github.com/wq-will/SimpleTES/blob/47d3413da1d85dc24341219d47452d2601e56a57/datasets/gpukernel/server/tasks/libkernelbot/run_eval.py#L375-L447)
defines `profile_program_roc`, calls `rocprofv3 --output-format pftrace csv`
at :383-410, then combines `*.pftrace`, moves `_code_object*.o`, and zips a
`ProfileResult` at :424-447. Our established C4 readers use governed v1
attribution and v2 deterministic reports (with omniperf/RPD tracked as
separate candidates), so SimpleTES's v3 pftrace/CSV package is **not** a
drop-in profiler receipt. The remaining study is a field mapping on paper:
enumerate its metrics, units, kernel-name matching, and package identities
against our C4 report before proposing any adapter. Resolve
6.2.4-vs-6.2.0-66 dependency drift without replacing the shared `/opt/rocm`
bind mount. Keep executable registration and external-benchmark remeasurement
out of scope under AK-RB-1 until that review is complete.

Neither handoff checkbox is closed by this feasibility note.

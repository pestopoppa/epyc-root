# KPF-50 exposure review

Date: 2026-11-04. Scope: recover target entry/exposure for the four 2026-11-02 rc143 attempts and assess whether the existing predeclaration supports an unchanged no-redraw attempt. Read-only audit; no model/build/GPU/benchmark run and no canonical files changed.

## Finding

The four rc143 records do **not** establish any model-window entry or target-input exposure. All four waiters terminated before their required prerequisites completed:

- Attempt receipts under /mnt/raid0/llm/tmp/kv-prefix-fork/kpf50-counterfactual-20261102/attempt{1,2,3,4}-interrupted/ record GPU rc143 at 14:11:18, 14:13:06, 14:18:19, and 14:22:15 UTC. Their gpu-wait.log files are empty; attempt 3's upgrade.log is also empty.
- The common gpu-wait.sh waits for CPU_FINAL_FINISHED, successful upgrade receipt, and /mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-phase-trial-20261102/FINISHED before invoking gpu-inner.sh. The latter then verifies pins, performs the clock smoke, and only afterward invokes the model runner. The waiter's wrapper writes the rc/finished receipts on signal.
- Those prerequisite completion timestamps are later than every attempt: CPU final build/smoke 14:28:02, HIP upgrade 14:31:29, P3 predecessor 14:34:40 UTC. Its P3 exit code was 143. Therefore none of the four attempts could pass the wait gates and enter the inner runner.
- The runner's Server.build_env() writes each of the four out/rocprof/.../input.xml files during Server object construction, before any server launch. These four files were created at 14:09:09. The runner constructs the plan (steps_by_item) before runtime preflight and before it writes run_meta.json; therefore these files are setup artifacts, not profile or exposure receipts.
- The full out/ tree contains only the four 18-byte <metric></metric> XML files. It contains no run_meta.json, linkage logs, server logs, VRAM samples, slot/fork records, profiler data, or model outputs. The older rocprof packet's out/ is also empty. No evidence of target request submission or model server launch was found.

Taken together, the recorded attempts are **pre-target interrupted/preflight attempts**. All four planned profile windows remain unexposed. Preserve their rc143 artifacts as-is; do not count them as profile rows or erase them.

## Existing predeclaration and continuation boundary

The file /mnt/raid0/llm/tmp/kv-prefix-fork/kpf50-counterfactual-20261102/PREDECLARED.md prospectively fixes a diagnostic sequence of four fresh 4×80k, 60k-trunk DFlash2 windows in full/masked/masked/full order. It requires synchronized target-step plus server-iteration boundaries, at least four child fork witnesses at 60k, qualifying 4-sequence 80k records, and comparison of only each window's first qualifying KPF50 step. It explicitly marks missing arms, timeouts, nonmatching witnesses, and clock uncertainty invalid, not zero/pass.

Because the attempts did not reach a model launch, a new execution of **the same four predeclared windows, same fixed prompt set/argv, order, and first-qualifying-step rule** is a no-redraw execution of the existing plan, not a continuation that repeats an exposed unit. Keep old attempt receipts separate. Do not label the four old rc143 attempts as measurements.

## Bounded execution plan (predeclared diagnostic only)

1. Retain the four attempt directories and current profile output unchanged. Use a fresh per-run output directory/ID so the old preflight XML does not appear to be run evidence.
2. Before any target launch, seal the exact candidate source/build and linked executable/libraries, target and DFlash2 model hashes, tokenizer/corpus-derived prompt-set hash, argv, runner/analysis code, rocprof package, and runtime. Verify actual in-run mapped ggml libraries and own-process HIP/KFD/VRAM residency; verify model/candidate freshness from content, not path or mtime.
3. Run and retain the declared before/after clock witness. If it fails, stop before launching a model. Enter one exclusive GPU window and retain process birth/exec/FD custody for the server and profiler.
4. Execute only full/masked/masked/full as declared. Keep each window fresh and retain raw timestamps, server iteration/step/draft markers, exact child fork receipts, token/position/sequence/layout fingerprints, full profiler output, logs, process maps, and GPU residency samples. Do not repeat a window after exposure; mark any incomplete or invalid window UNKNOWN/INVALID.
5. Analyze only the first qualifying step in each window, after validating matched inputs/layout/dispatch/phase and clock overlap. Preserve all later masked steps as non-comparable because state diverges.

## Claim limit / unresolved gate

The predeclaration calls this a counterfactual diagnostic and says the full-minus-masked subtraction is sensitive to dispatch/scheduling and **is not a direct measurement of trunk time**. It also says its single-step sample, A/A spread, mask-induced divergence and clock alignment do not support a decision-grade claim; the proposed ≥20% threshold is unratified. Thus the no-redraw prerequisite is now resolved for this predeclared diagnostic, but its result cannot by itself establish the KPF-50 trunk-attention ≥20% gate. A separately qualified direct-attribution method and the applicable policy authority remain necessary before that gate can be judged.

## Evidence paths

- Predeclaration: /mnt/raid0/llm/tmp/kv-prefix-fork/kpf50-counterfactual-20261102/PREDECLARED.md
- Waiter and inner gates: /mnt/raid0/llm/tmp/kv-prefix-fork/kpf50-counterfactual-20261102/gpu-wait.sh, gpu-inner.sh
- Four attempt receipts: /mnt/raid0/llm/tmp/kv-prefix-fork/kpf50-counterfactual-20261102/attempt{1,2,3,4}-interrupted/
- Runner lifecycle: /mnt/raid0/llm/tmp/kv-prefix-fork/kpf50-counterfactual-20261102/runner/kpf18_gate.py (Server.__init__/build_env/start, steps_by_item/run_meta ordering)
- Prerequisite timestamps and exit receipts: CPU_FINAL_FINISHED, UPGRADE_FINISHED, and /mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-phase-trial-20261102/{FINISHED,EXIT_CODE}
- Profile output inventory: /mnt/raid0/llm/tmp/kv-prefix-fork/kpf50-counterfactual-20261102/out/

# Jet-Long slot save/restore CPU pre-test: STOPPED at first failure (2026-10-06)

Driver: jl_saverestore2.py (trimmed: Jet-Long ON only, window 256, native 1024, -c 16384, -b/-ub 16, -t 24,
--ctx-checkpoints 8, --cache-ram 8192, DFlash2 drafter n-max 7). q2 lock, taskset 48-71. Logs: saverestore2/U.log, driver.log.

## OBSERVED
- Server U: "Jet-Long ON: w0 = 256, w_native = 1024 ... side cache = 256 MiB" present (target context).
- Draft context: "llama_jetlong_attach: Jet-Long: unsupported memory type for this model; disabled" (U.log line 386, drafter KV is iswa).
- "context checkpoints enabled, max = 8, min spacing = 8192" present.
- FIRST request (Q1, ~6k-token prefix, ub 16) CRASHED the server at about n_tokens 1280 (prefill ran clean through 1024 = native
  and ~250 tokens beyond, ~39 tok/s): ggml-cpu/ops.cpp:5350 GGML_ASSERT(i01 >= 0 && i01 < ne01) (get_rows index out of range),
  on all threads. Python saw RemoteDisconnected. No save/restore step was reached. Checks (1) and (2): NOT EXECUTED.

## Not yet separated
Whether the assert is Jet-Long-specific (position past native on the CPU backend), drafter-specific, or CPU-build-only is unknown;
the no-Jet-Long control was dropped by instruction. common.sh uses --cache-ram 0 and default --ctx-checkpoints (32); this test used
8192/8.

## Next (needs coordinator approval to explore)
Rerun the same Q1 without --jetlong flags, or with --jetlong flags and no drafter, to localise the assert.

## Localisation (approved follow-up; ~2684-token prompt, Jet-Long ON unless noted; logs saverestore2/loc-*.log, bt in loc-a-gdb.log, loc-b-gdb.log)
- (a) --ctx-checkpoints 0 --cache-ram 0: CRASH (same assert). (b) no drafter: CRASH. (c) -ub 256 (-b 256): NO CRASH. (d) not run (stop rule).
- Variable: -ub 16 (with Jet-Long window 256 / native 1024). Not checkpoints, not cache-ram, not the drafter.
- bt (a and b): ggml_abort <- ggml_compute_forward_get_rows (ggml-cpu/ops.cpp:5350, assert i01>=0 && i01<ne01) <-
  ggml_graph_compute_thread <- GOMP_parallel <- ggml_graph_compute <- ggml_backend_sched_graph_compute_async <-
  llama_context::graph_compute <- process_ubatch <- llama_decode (binaries stripped; no deeper file:line).
- Note: GPU run uses ub 16 as well (common.sh UB=16) but window 2048/native default; whether ub16 is a CPU-only hazard is unknown.

## ub 256 run (saverestore3/, jl_saverestore3.py): STOPPED at first failure, checks (1)/(2) not reached
- Q1 prompt = 9149 tokens (prefix overshoot; TA loop adds 100 sentences/step). Prefill ran clean in 256-token ubatches to n_tokens 9145
  (checkpoints 1 and 2 of 8 created, 189.65 MiB each, at 8893 and 9145), then the server aborted with the SAME assert
  (ops.cpp:5350 get_rows) on the final 4-token ubatch (9145 -> 9149). 
- Combined with the ub16 result: the assert fires on any ubatch smaller than the Jet-Long window (256) at positions beyond native (1024):
  ub16 ubatches crash immediately past ~1280; at ub256 only the tail ubatch (4 tokens) and, by extension, decode (n=1) are small.
  Hypothesis (unproven): small-ubatch get_rows index is out of range in the Jet-Long grouped-position path. GPU run (ub 16, window 2048) is exposed.

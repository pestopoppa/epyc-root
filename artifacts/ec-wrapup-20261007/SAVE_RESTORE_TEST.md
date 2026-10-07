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

## Post-fix run (e6ea79421, ub 16, saverestore4/): check (2) FAIL, stopped
- Binary: build-cpu libllama.so 2026-10-06 21:24:11Z; commit e6ea79421 dated 21:40:05Z (commit made AFTER the build); src/llama-graph.cpp mtime 17:18Z < build, tracked tree clean => binary was built from the fixed source; mtime rule literally fails, provenance OK.
- Jet-Long ON, ub 16, ctx-checkpoints 8, cache-ram 8192. Q1 (9149 tokens) crossed native with no crash and answered correctly ("Marlowe Lighthouse: 71843 / Quillfeather Archive: 30926"; draft 21/35 accepted). Prefill ~26.8 tok/s, 345 s.
- (2) Q1b (same 9120-token prefix, different question): prompt_n = 9149 of 9149, cached_n 0 => FULL RE-PREFILL, not a checkpoint hit.
  Server log: sim_best 0.997 by LCP, then "checking checkpoint with [9144,9144] / [9132,9132] against 9120... forcing full prompt re-processing
  due to lack of cache data (hybrid/recurrent)" and both checkpoints erased. The only checkpoints are the end-of-prompt ones (n-16, n-4), which lie
  inside the question tail, i.e. beyond the shared prefix. No checkpoint was created at the ack/user-message boundary (pos ~9120).
- Same with Q2 sized extension would hit the same wall (not run). Checks (1) not run.

## Workaround run (fixed build e6ea79421, ub 16, Jet-Long ON, ctx-cp 8, cram 8192, q3 72-95; saverestore5/): PASS (2') and (1)
Prefix (ends at ack) 3556 tokens, Q1/Q1b tail 58, extension delta 2203.
- U: prefill-only prompt_n 3556 -> checkpoints at 3540/3552 (n-16/-4). Q1 prompt_n 58 (cached 3556). Q1b (same prefix, different Q) prompt_n 74, "restored context checkpoint pos 3539, n_past 3540", later checkpoints erased as invalidated. Q2 (extension) prompt_n 2219 (cached 3540) = delta+16.
- R1: prefill-only, SAVE: 280,800,032 bytes (3556 tokens), save_ms 69.7. R2 fresh server: restore n_restored 3556, restore_ms 36.3. Q2 prompt_n 2203 (= delta exactly, cached 3556), output byte-identical to U Q2; drafter acceptance 33/41 (U: 33/41).
- Slot file does not carry context checkpoints (R2 log shows no checkpoint restore; reuse is exact because the extension is strict).
- 300k linear extrapolation: file = ~199 MB recurrent state (fixed) + ~23 KB/token KV => ~7.1 GB; at the observed ~4 GB/s save, ~1.8 s; restore ~1 s (CPU page-cache numbers; GPU adds VRAM<->host copies).

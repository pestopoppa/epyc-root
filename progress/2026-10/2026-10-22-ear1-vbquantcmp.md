# 2026-10-22 — EXL3-EAR1 (EAR column) and VB-QUANTCMP-WIRE (quant-comparison receipts)

Session workspace-58 (subagent), operator-approved tasks from research intake intake-ist-slq-20261022.
No model was run.

## EXL3-EAR1 — code landed, build armed

- Branch `experimental/ear-kld-column-20261022` @ `782c11ae43c75a0d291399896f833a370d52e319`, cut from the
  champion tip `dd3d9721c` (`ak/champion/llama-cpp-ffc1bac82eec`), pushed to the `fork` remote. Production v10
  (`/mnt/raid0/llm/llama.cpp`) untouched. Worktree `/mnt/raid0/llm/llama.cpp-experimental-ear-20261022` is kept:
  the armed build runs in it.
- EAR = sum_v min(p_base, q) = 1 - TV, in two variants that are not interchangeable: full vocab (a strict 1 - TV,
  so Pinsker applies) and SLQ's `evaluation.py` top-10 renormalized variant (what the SLQ cards quote).
  The math is a pure header function (`tools/perplexity/kld-ear.h`); `kl_divergence_result` and the per-token
  KLD loop accumulate it, and a new `====== EAR statistics ======` block is appended after `Same top p`.
  Every pre-existing output line, including the per-chunk table, is unchanged.
- The base file stores log-probs as uint16 codes over a 16-nat range, so EAR(base, base) = 1 holds to one
  encoding step (16/65535 nats); the Pinsker check uses that step as its tolerance.
- `tests/test-kld-ear.cpp`: compiled file-scoped with g++ and passed (EAR(base,base), Pinsker, a naive double
  reference, top-K ties, n_vocab < K, K = 1). `tools/perplexity/kld-ear-crosscheck.py` (stdlib only) recomputes
  both EAR lines from two saved base files and brackets the clamped q tail; checked against a synthetic pair.
- Filler `ear1-build` (FILLERS.md, class block-correctness, cpu, one quarter, 16 GiB, ~20-40 min, min window
  1800 s). Launcher `/mnt/raid0/llm/tmp/fillers-ws58-ear1/ear1_launch.sh`, a wrapper that writes `.ended` on
  every exit path around `ear1_filler_run.sh` (a verbatim copy of `filler_run7.sh`). Job `ear1_job.sh`: builds
  llama-perplexity and test-kld-ear with the champion store's options, checks strings/mtime/linkage, runs the unit
  test, then a tiny smoke (Qwen2.5-Coder-0.5B Q8_0 as base, Q4_K_M as the evaluated model, -c 128 --chunks 4):
  EAR(base, base), Pinsker, pre-existing stdout lines byte-identical to the champion binary
  `kernels/builds/cpu-20261020-dd3d9721c`, and the Python cross-check. `COMPLETE` is written only if all of them
  pass. The validator `--for-grant` and `grant_ok.sh ear1-build 16` both admit the row.
  Dry runs: a stub grant, plus a signal while polling (group and single-PID), each wrote `.ended`.
- Not ticked: the build and the smoke have not run yet.

## VB-QUANTCMP-WIRE — landed and ticked

- The existing SC54 receipt is extended, not replaced: `scripts/vidya/qwen4exp_quality_capture.py --mode
  kld-quantcmp`. It is `kld` plus the native `Same top p`, `EAR full vocab` and `EAR top10 renorm` rows, a native
  Pinsker line the reader re-derives, and `--substrate cpu|hip`. Residency is sampled during the child. CPU
  requires libggml-cpu mapped, no accelerator backend, and the child never seen in KFD. HIP requires libggml-hip
  mapped and at least two non-zero per-PID KFD VRAM samples. DFlash2 acceptance is optional
  (`--acceptance-log` server /completion JSONL plus the drafter and server-binary identities) and gets its own
  tuple. The server's process custody is stated as not captured, and EAR is never labelled as acceptance.
- Same source kind, same ingest source `qwen4exp-quality-measurement`, same `claim_tuple.grade()`, no new ladder.
  The strict reader was extended and re-pinned (`READER_SHA256 = 407af3fe7172...`). Each tuple's
  `extra.quantcmp` carries the model, base model and base-logits sha256, n_ctx, chunks, the EAR variant, the
  substrate and the residency counts.
- Controls: `tests/vidya/test_vb_quantcmp_wire.py` 16/16 (one case runs an anchor and a candidate through the
  real writer with a fake producer that prints the exact EXL3-EAR1 format). `test_sc54_qwen4exp_quality_adapter.py`
  42/42, and test_ingest_sources + test_claim_tuple are green (351 together).
- `scripts/ci/{sc54_native,hg5_reader_native}/source-map.json` still pin the old reader digest. They are the
  historical CI captures bound to fixed commits and codex branches, so they were left as they are.

## Belief kernel

The new measurement source is the quant-comparison row in `scripts/vidya/adapters/README.md`, which is now
"write side landed". Its first live receipt should wrap the next scheduled KLD pass (NEW-10/NEW-13) built from
the EAR branch.

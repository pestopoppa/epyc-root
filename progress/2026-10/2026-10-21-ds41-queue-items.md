# 2026-10-21 DS41 queue items (workspace-58 request, code and scripts only)

Four DS41-1017 inference items were made runnable and registered in the shared compute queue
(`/mnt/raid0/llm/tmp/compute-flags/FILLERS.md`). No inference, no model load, no server was started.

| queue id | item | class | duration | min window | state |
|---|---|---|---|---|---|
| ds41-c72 | DS41-C7.2 top-k / indexer share at 8K/32K/128K | block-timing-pairable | ~2.0 h | 45 m (128K needs >= 2 h) | ARMED, ready |
| ds41-w61 | DS41-W6.1 card sampling alpha and block-2/3 speedup | block-timing-pairable | ~2-2.5 h | 40 m | ARMED, ready |
| ds41-t33c | DS41-T3.3c token-parity close-out | filler | ~0.5 h | 20 m | ARMED, ready |
| ds41-conf1 | DS41-CONF.1 confidence-head reliability | block-correctness | ~1.5 h per phase + build | 30 m (first grant >= 70 m) | ARMED, ready with a caveat (patch uncompiled) |

All four launchers are detached shell pollers (no LLM). Each runs only inside a written grant, under its own build-role
region-lock claim, refuses (`.ended rc=4`) when a `llama-server` naming a `DeepSeek-V4.1-Flash` model is live, TERM/KILLs its
captured process group at the hard end, and writes `.ended`. Tested with stubs before arming: ok, hard end (rc 124), refusal
against a fake live DS41 server (rc 4).

## Where things are
- Research `2a40ce4b4`: `artifacts/ds41_queue_20261021/` (lib, c72, t33c, conf1) and `artifacts/ds41_w6_dspark_1017_20261021/w6.1c/`.
- llama.cpp branch `experimental/ds41-conf1-logging-20261021` @ `b428d7392` (from champion `dd3d9721c`), env `LLAMA_DSPARK_CONF_LOG`.
  Not compiled: region-lock q0 was held by another session. The driver builds it in its first grant and proves the knob with `strings`.
- Launchers run from a frozen copy: `/mnt/raid0/llm/tmp/ds41-queue-20261021/` (`<item>/launch.sh`, `<item>/STOP`, results in `<item>/results/`).

## T3.3c finding (offline, from `ds41-t33c-1017b`)
- BOS: decided as `add_special=true` (the template emits no BOS; 9/13 token-identical with it, 0/13 without).
- The residual divergences (golden1 at id 586/622, golden2/3/4) are all in the FINAL assistant turn: a doubled `<think>` (golden1),
  reasoning re-rendered in chat mode (golden2/3), and a lost `<｜action｜>` task marker (golden4).
- The arguments probe was UNDETERMINED in v2 (the tool call was the last message). v3 round-trips it.
- Still to run: one 0.5 h rerun with `t33.py` v3. Closing the divergences needs a template/server fix first; that is not made here.

## Caveats
- C7.2 uses the DS41-C8 instrumented sibling build, not the champion (the champion has no `GGML_CPU_PROF`). Shares transfer, absolutes do not.
- W6.1 timing is indicative (shared host); speedups are plain-vs-dspark inside one pair on identical cpus and `-t`.
- The cpu list in a grant sets `-t`; pairs on different `-t` are discarded because 1017 output depends on thread count.

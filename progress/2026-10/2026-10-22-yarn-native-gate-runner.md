# 2026-10-22 — YaRN native-window gate harness (yarn-native-gate, yarn-extension-arms)

Session: 3c4ca599 subagent. The operator ordered this on 2026-10-22 ("DO IT!"). No inference was run, no server was started and no poller was armed; main arms the pollers.

## What was built

- **Research branch `yarn-native-gate-runner-20261022` @ `2fd3208d`** (pushed, not merged). The code is in `scripts/benchmark/yarn_gate/`:
  - `arm_runner.py`. Subcommands: plan, dry-run, status, run, decide.
  - `cells.py`. The item contract and the scorer registry.
  - `plans.py`. The two pre-registered plans.
  - Builders: `oolong_local.py` (local JSONL), `ruler_local.py`, `helmet_local.py` and `longbio_local.py`.
  - Tests: 14, 13, 20 and 7 new, all passing. The existing `test_yarn_gate.py` (22) and `test_oolong_adapter.py` (11) still pass.
- **Filler jobs** in `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/`:
  - `yarn_gate_lib.sh`, `yarn_native_gate_job.sh`, `yarn_extension_arms_job.sh` and `yarn_judge1_job.sh`.
  - `bash -n` passes on all four, and so does `--dry-run`.
  - A run against a fake llama-server covered three windows. It resumed, completed pairs first, went INTERIM then FINAL, wrote the COMPLETE marker, and killed the captured server PIDs (verified dead).
- **Native-gate plan frozen** at `/mnt/raid0/llm/tmp/yarn-native-gate-out/plan`, sha `b223302674dc…`, 185 items:
  - Oolong-synth 131072, 8 contexts, counting and user questions.
  - RULER NIAH mk_2, mk_3 and mv at 32K (×6), 64K (×3) and 124K (×2).
  - Estimated ~136 min per arm, about 4.8 GPU-h including loads, over 3 grants of 2 h.
- **Pinned local clones**, made from the dive checkouts with no network:
  - `/mnt/raid0/llm/data/eval/helmet/repo` @ `aeadacc6`.
  - `/mnt/raid0/llm/data/eval/longbiobench/repo` @ `dc6f6ed1`.

## Findings

- **:8083 is production `architect_critic`**, the Qwen3.8-27B on the MI210 (`stack_topology.yaml`). It was down at 12:24Z. The jobs refuse with rc 4 if it is listening, and never stop it.
- **:18083 belongs to another session.** At 11:32Z it was held by another session's 27B (`gpu-20261020-a1f0c8cf9`, np 4). The gate therefore uses :18093 and :18094, not E1's :18083.
- **Host RAM per window is 12 GiB, not 64.** 64 GiB was the VRAM figure. The E1 A1 log shows ROCm_Host buffers of 1.29 GiB (model) and 2.13 GiB (compute). `--no-mmap` means there are no mapped weights. The runner peaked at 1.3-1.9 GiB RSS during plan freeze. Each window samples VmHWM to confirm.
- **HELMET data is not on disk.** `data.tar.gz` is 10.5 GiB. nq and hotpotqa are optional segments that drop at freeze with the exact missing paths recorded. HELMET's ruler cells are regenerated locally with RULER instead.
- **Some RULER inputs are absent locally**: wonderwords, nltk and RULER's `english_words.json`, which is a git-LFS pointer. Word keys are therefore pairs drawn from the essay vocabulary, and the essay haystack comes from the needle-repo Paul Graham set. Each item pins these deviations.
- **Prefill model from E1**: t(L) = L/850 + L²/9.6e7 seconds. That gives a 447K prefill of about 43 min. The runner re-fits it to measured timings.
- **The extension-arms plan is heavy**: about 17 GPU-h (A0 ~5.5 h, A1 ~11 h), against the f8 audit's ~6 GPU-h.

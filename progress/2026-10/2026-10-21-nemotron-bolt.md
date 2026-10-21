# 2026-10-21: Nemotron 3.5 Bolt 74B-A9B on the champion (pending fold)

- **Problem:** `nemotron_h_moe` Bolt GGUF fails on v10 and the champion: `expert_used_count` (and `expert_feed_forward_length`) are per-layer arrays, and the routed-expert count varies per layer (240-496, known only from the router tensor). The vision projector `nemotron_omni` was also missing. The LiLiCorr DFlash drafter is unsupported (see below).
- **Branch:** `experimental/champion-plus-nemotron-bolt-20261021` @ `59c1b915f` on `dd3d9721c` (pushed to `fork`), worktree `/mnt/raid0/llm/worktrees/llama-champ-nemotron-bolt-20261021`. Commits: `e68cda856` (pick of upstream #26693, saver key clobber), `64bb5d7b0` (port of #25444/#28323/#30520 nemotron-h hunks, per-layer MoE; default-neutral, scalars kept as the max), `59c1b915f` (mtmd `nemotron_omni`, from #30520).
- **Builds:** `kernels/builds/gpu-20261021-59c1b915f-nemotron`, `cpu-20261021-59c1b915f-nemotron` (10348, linkage PASS).
- **Gates:** Qwen3.6-35B-A3B MTP greedy byte-identical 3/3 vs the champion; CPU and ROCm0 test-backend-ops on MUL_MAT_ID/MUL_MAT/ADD/ARGSORT/TOP_K/GET_ROWS/SSM_SCAN/SSM_CONV all pass; test-llama-archs over 139 archs shows no regression.
- **MI210:** coherent with reasoning on and off (8/8, no loops), 21.5 GiB VRAM, KFD residency proven. llama-bench pp512 899.2, tg128 53.4 t/s; NVIDIA recipe server tg 51.2 t/s. Indicative only: shared claim, host load ~98. CPU 24 threads: pp512 56.1, tg128 12.7.
- **Gap:** the DFlash LiLiCorr drafter needs upstream #30506 + #26905 + #28000 and the `llama_batch_ext` embd_state plumbing. That goes in the CH-18 v11 upstream pull. Full entry: `handoffs/active/autokernel-champion-aggregate.md`, "Pending fold (Nemotron 3.5 Bolt)".

### Nemotron 3.5 Bolt → C2 prep (nemotron-c2-prep subagent)
- C2 for the champion owner: `experimental/c-plus-nemotron-bolt-20261021` @ `49550eda5` = C `f0c96dc1f` + Nemotron (V11-097, 3 commits) + V11-098 + CT-12.3b + 2 test-only fixes. Stores are `{cpu,gpu}-20261021-49550eda5-c-nemotron`. All pre-check gates PASS, including CH-21 on the 35B-MTP and the 27B. One conflict (R1, `tests/CMakeLists.txt`).
- Found and fixed:
  - C's test-llama-archs fixture generator aborted on gemma-embedding2, which silently "Not Run"s every fixture ctest. DS41 is still a gap.
  - V11-098's server test, and the CH-21 script, asserted a `generation_settings` field the server never emits. The CH-21 script also has a pipefail+`grep -q` SIGPIPE bug.
- LiLiCorr DFlash drafter ported onto C2 on a separate branch (`…-dflash-20261021` @ `58a98f088`, 6 commits). Bolt+LiLiCorr runs on CPU, and the existing MTP and 27B DFlash2 paths are byte-identical. The MI210 speed run is pending a GPU slot.
- Evidence: `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/`.

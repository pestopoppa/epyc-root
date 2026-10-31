# C4 fold prep: champion dcc853b55 (C3) -> C4 (prepared 2026-10-24 for fold owner 3c4ca599; nothing built, run, CAS'd or moved)

C4 = `experimental/champion-c4-20261024` @ `cdb4d8c77c2300f61c404a3df6d1950934b39c98` (fork, pushed non-force), build number 10417. FOUR commits on `dcc853b5559bef4e50acf251f4910f7f4e0ba538`:

| SHA (C4) | Subject | Source |
|---|---|---|
| `652930282` | CUDA: Clear CUDA graphs after legacy memory pool flush (#26771) | cherry-pick of `fd0268ca3` (GPU-LEAK-1c, CH-30) |
| `a9c38f8e0` | ggml-cuda (HIP): release the stale graph executable on a property change instead of cudaGraphExecUpdate | cherry-pick of `9aba0e3b4` |
| `2a6c1201c` | ggml-cuda: GGML_CUDA_GRAPH_MEMLOG=1 logs device memory around graph instantiate/release (env-gated, off by default) | cherry-pick of `0a1fa49ee` |
| `cdb4d8c77` | test-llama-archs: skip deepseek41 / deepseek41-dspark [CH-20.2] | `git am` of ws58 patch 0002 (tests/ only) |

The 3 CH-30 picks applied cleanly (C3 touched only libllama). Diff vs dcc853b55: `ggml/src/ggml-cuda/{common.cuh,ggml-cuda.cu}` + `tests/test-llama-archs.cpp`. Worktree `/mnt/raid0/llm/worktrees/c4-fold-20261024`. Champion ref and the production tree untouched.

## 1. NOT folded: ws58 patch 0001 (14c57cbe9 cherry-pick, CH-24)
Decision rule from main: apply only if the qwen4exp fused decode path is OFF by default in code, or every serving and AK recipe sets `GGML_FUSED_DECODE_OFF=1`. Evidence (read-only):
- Code: `src/llama-context.cpp:1392` takes the fused path when `getenv("GGML_FUSED_DECODE_OFF") == NULL && model.supports_fused_decode() && ...` -> ON by default; only `llama_model_qwen4exp` returns true from `supports_fused_decode()` (models.h:2221), so the exposure is the Qwen3.8-Flash-Next (qwen4exp) family. The research recipe comment says the same: "compiled default: fused decode ON; champion runs graph path" (`qwen38_flash_next_recipe.py` CHAMPION_KNOBS).
- Recipes that DO set OFF=1: `qwen38_flash_next_recipe.py` CHAMPION_GGML_ENV; AK campaign `ak-q38fn-cpu-decode-20261003/inputs/campaign-resolved.json` env; `model_registry.yaml:2969` (inside `acceleration.optimal_cpu_serving.env`, a recipe-record block).
- Gap: the live stack launch env is built by `scripts/server/stack_env.py`; its `_ROLE_ENV_BLOCKS["architect_general"]` (the Flash-Next full-CPU process on :8074) is `{}` and the canonical env carries only `GGML_IQK=1`. No code in `epyc-orchestrator` reads `optimal_cpu_serving.env` (`grep FUSED_DECODE_OFF` hits only model_registry.yaml). So the serving launch is NOT shown to set OFF=1 (only the MTP draft-target exclusion, `embeddings_nextn`, keeps some decodes on the graph). FD-DIV-1b (`/mnt/raid0/llm/tmp/fd-div-1b-20261024/out/VERDICT.md`) found a second fused-MoE defect 0001 does not fix (DIVERGE at w=0.05/0.3, non-finite router logits abort at w=1.0).
- => rule not met: 0001 is NOT applied; left for a later fold. Separate finding for main (not acted on here): add `GGML_FUSED_DECODE_OFF=1` to `_ROLE_ENV_BLOCKS["architect_general"]` (or verify the running :8074 process env), since the compiled default is the divergent path.
- Consequence: no CPU lib changes. The CPU image must be code-identical to the C3 CPU image (libs); only test binaries (test-llama-archs) differ. So no Q38FN greedy-identity (bundle item c) and no timing (item b) is needed. If 0001 is later added, extend gates: fold_gate expected-changed libllama.so (and possibly libggml-cpu.so), CPU unit tests incl. test-llama-archs, and `bundle_gate_c4.sh --items c` (kept allowed in the script).

## 2. Gate set (mirrors CH-30's own validation; all correctness, no timing slot)
| Gate | Instrument | Class | Pass |
|---|---|---|---|
| G-a | `gate_c4.sh cpu|gpu` (a): FULL `test-llama-archs` (CH-20.2 makes it runnable; ws58 got rc 0, 118 OK), `--yarn-kshift -s 1234`, test-rope, test-qwen4exp-fused-rope, test-dca, `test-backend-ops -b CPU -o ROPE` 448/448 | CPU build role | all rc 0 |
| G-b | `fold_gate.py` v4 (pinned `fold_gate_src_v4/`) vs the C3 image, cand-commit cdb4d8c77: gpu `--expected-changed libggml-hip.so`; cpu NO expected lib | CPU build role | exit 0; cpu: zero CHANGED libs; gpu: only libggml-hip.so EXPECTED |
| G-c | `llama-server --version` names cdb4d8c77 (10417), `verify_ggml_linkage.sh` | CPU | in gate_c4.sh |
| G-d | `strings`: GGML_CUDA_GRAPH_MEMLOG in a gpu-image lib, in NO cpu-image lib | CPU | in gate_c4.sh |
| G-e | GPU correctness slice `gpu_slice_c4.sh`: test-backend-ops ROCm0 ROPE / FLASH_ATTN_EXT / MUL_MAT / MUL_MAT_ID / GET_ROWS, C4 vs C3 control | GPU exclusive, threads 184-191 | identical counts, rc 0 -> `SLICE PASS` |
| G-f | **GPU-LEAK-1c-V on the C4 image** `c4_leak_job.sh`: E1 shape, graphs ON + MEMLOG, 30 requests; reference arm C3 image 15 requests | GPU exclusive | slope_F <= 10 MiB/request (unfixed 290.27), MEMLOG net 0 per pair; RESULT.json |
| G-g | `bundle_gate_c4.sh --execute --items e` via `c4_gate_e_job.sh`: 27B DFlash2 A/B C3 (P) vs C4, 15 pairs, graphs on | GPU exclusive, 72-79 | identity C4==P, SW-9 probs, pp/tg inside the P-vs-P floor |

CAS (after all PASS): recipe in `ch28-fold-20261023/PLAN.md` section 3, 4-arg `update-ref` old=dcc853b5559bef4e50acf251f4910f7f4e0ba538 new=cdb4d8c77c2300f61c404a3df6d1950934b39c98, `ak-loop-tree read-tree -m -u` two-tree form, plain ff push of the champion ref to fork. Not done here. Then manifest V11-104 PEND -> IN, CH-30b.

## 3. Files in /mnt/raid0/llm/tmp/c4-fold-prep/ (all `bash -n` clean, none run)
`build_store.sh` (adapted from C3: SRC/EXPECT/SUFFIX c4/DATE 20261024, baseline image = C3 image, UI dist pinned from the per-kind 141e4bcf5 image because the C3 images carry no tools/ui/dist), `gate_c4.sh`, `c4_build_job.sh`, `gpu_slice_c4.sh`, `c4_leak_job.sh` (adapted from gpu_leak1c_v_job.sh; no build step, refuses rc 5 without the image), `c4_gate_e_job.sh`, `bundle_gate_c4.sh` (re-execs ITSELF as the fixed C3 version does; items c,e only), `fold_gate_src_v4/`, `ROWS.md`, `RECORD.md`, `FILLERS.copy.md` (scratch validation copy).
Images: `kernels/builds/{cpu,gpu}-20261024-cdb4d8c77-c4`. Build command: `region-lock run --cpu-list 72-95 --role build --tag c4-fold -- env FOLD_BUILD_CPUS=72-95 /mnt/raid0/llm/tmp/c4-fold-prep/build_store.sh cpu|gpu` (the whole chain is `c4_build_job.sh`).

## 4. Minutes (estimates)
Build + gates ~25-35 CPU-min (one build quarter); GPU: slice ~30, leak check ~34, A/B ~26 = ~90 GPU-min exclusive, three separate grants. No whole-host quiet slot needed.

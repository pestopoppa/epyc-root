# Dive — creditfilterrepo — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/yoctta/CreditFilter/main/README.md", retrieved: "2026-11-23", sha256: "6ae185d07e77"}
> SOURCE-QUARANTINE: {url: "https://github.com/yoctta/CreditFilter (depth-1 clone kept by the bearing dive at creditfilter/repo/CreditFilter, reused read-only; HEAD 539873250e746edce23c91d3cf32578d7e24659f, verified with git rev-parse)", retrieved: "2026-11-23", sha256: "n/a (git tree; anchors come from page.txt only)"}
> Extra reading material (not anchors): `environment/pip_freeze.txt`, `launchers/*.sh`, `creditfilter/*.py`, `creditfilter/scripts/*.sh`, `verl/` diffs listed in `NOTICE`, `tests/`. Package-index facts (download.pytorch.org/whl, wheels.vllm.ai/rocm, pypi.org vllm/0.18.0) were read live on 2026-11-23 and are dated observations.

Bearing entry: intake-2834 (CreditFilter paper, dive at `research/deep-dives/intake-ak-1123/intake-2834-creditfilter.md`). That dive read the README and the head of `credit_filter.py`; this dive reads the whole coefficient, both launch scripts, the arm table, the pip freeze and the verl patch points.

## 1. Stage-1 fields

- **Title**: CreditFilter (code companion of arXiv:2611.27227): "Training and evaluation code of the paper CreditFilter: Calibrated Token Weights over the Within-Response Entropy Rank for RLVR".
- **Authors**: repo carries no author list in the README; paper authors Hanqing Zhao, Liuyue Xie, Rong-Cheng Tu, Xu Zhang, Davide Modolo, Dacheng Tao (per intake-2834).
- **State**: GitHub `yoctta/CreditFilter`, default branch main, HEAD `539873250e746edce23c91d3cf32578d7e24659f`, Apache-2.0, `verl/` = copy of verl 0.8.0.dev at upstream commit `f92bc5c435c6fc2e6d1f94484164de26f4574bd7` (2026-04-07; from `NOTICE`), five verl files changed.
- **Categories**: training_distillation, tool_implementation.
- **Novelty**: low. A reference implementation of an already-ingested paper; the new content is the launcher/arm table and the verl patches.
- **Relevance**: low. We have no RL lane; this entry exists to settle what a one-card MI210 smoke would have to provision (ledger C1 of intake-2834).
- **Credibility**: 2 = peer-reviewed 0 (preprint companion) + within 12 months +1 + major lab / known contributor +1 (Amazon AGI, Dacheng Tao, per intake-2834) + independent corroboration 0 + commercial bias 0. Code matches the paper's formulas (claim 0) but a matching implementation by the same authors is not independent corroboration.
- **Verdict**: worth_investigating. Same verdict as the paper entry; this dive converts "blocked on a pinned training environment" into a concrete provisioning list (section 6).

## 2. Key claims

**Claim 0 — the released coefficient is the paper's coefficient. CONFIRMED (code read in full, 384 lines).** `apply_credit_filter` multiplies the advantage by `g_i * [m*w + (1-m)]` with `w = max(2^(-q/width), floor)`, width 0.10 correct / 0.14 wrong, floor 0.1 on positive-advantage rows only, damping `(1-p_group)^gamma` (gamma 1 positive, 0 negative), fallback `m = clip((H_hi - Hbar)/(H_hi - H_lo), 0, 1)` with 1.5/3.0 nats, rank q = rank/n_valid within the response. `launchers/arms.sh` sets exactly these defaults. Floor and damping follow the sign of the row's advantage, widths follow `answer_correct`; a unit test (`test_outcome_and_advantage_sign_disagree`) covers the overlong-penalty case the paper mentions. Anchor: the README states the code is verl with `creditfilter/` on top.

**Claim 1 — "no extra cost / already computed by the trainer". PARTIAL (narrower than the paper's sentence).** The fixed-width CreditFilter needs only per-token entropy, which the old-log-prob pass already returns (`ray_trainer.py` sets `calculate_entropy=True`; `routing.needs_entropy()`). CreditFilter-D (`CF_WIDTH_MODE=tracked`) additionally needs the actor to return per-token `sum(pi^2)`; that is a patch in `verl/workers/engine/fsdp/transformer_impl.py` (`calculate_sum_pi2`, chunked softmax in `verl/utils/torch_functional.py:242`) and it raises `RuntimeError` if `use_fused_kernels=True`, because it needs full logits. Fixed-width CreditFilter therefore needs materialised full-vocabulary logits for entropy too (no fused-kernel path is claimed for it in the launchers). The paper's "Every quantity it uses is already computed by the trainer" (Algorithm 1 description in `creditfilter/page.txt`, cross-source, not an anchor) holds for the fixed-width arm and for entropy; it does not hold for the D arm without the patch.

**Claim 2 — framework and version pins are NVIDIA-only as shipped; a ROCm path exists but at different versions. CONFIRMED for the pins; PARTIAL for feasibility.** README requirements: Ray cluster of 8-GPU nodes, Python 3.12, torch 2.10.0, transformers 5.3.0, vllm 0.18.0, ray 2.54.1. `pip_freeze.txt` pins `torch==2.10.0+cu129`, `nvidia-*-cu12`, `flash_attn==2.8.3`, `flashinfer-python==0.6.6`, `apex`, `megatron-core`, `deep_ep`, `liger_kernel==0.7.0`, `peft==0.18.1`, `trl==0.27.0`. The launcher sets `VLLM_ATTENTION_BACKEND=XFORMERS`, `disable_custom_all_reduce=true`, `PYTORCH_ALLOC_CONF=expandable_segments:True`, FlashInfer cache dirs. No file in `creditfilter/`, `launchers/` or `eval/` mentions ROCm/HIP; the verl copy does (`vllm_rollout/__init__.py:35` strips ROCm local-version suffixes when `ROCM_PATH` is set; `single_controller/base/worker.py` handles `HIP/ROCR_VISIBLE_DEVICES`; `utils/ray_utils.py` cites Ray's AMD accelerator manager). Live package-index observations (2026-11-23): PyPI `vllm==0.18.0` declares `transformers<5,>=4.56.0` and `torch==2.10.0`, so the repo's own freeze (vllm 0.18.0 + transformers 5.3.0) violates vllm's declared range; `download.pytorch.org/whl/rocm6.2` tops out at torch 2.5.1, `rocm6.2.4` at 2.7.1, `rocm6.3` and `rocm6.4` at 2.9.1, and torch 2.10.0 has a `rocm7.0` wheel; `wheels.vllm.ai/rocm/` lists `amd-torch-device-gfx90a` and `rocm-sdk-device-gfx90a` (torch 2.13.0+rocm10.0.0, ROCm SDK 10.0.0) and a `flash_attn-2.8.3` ROCm wheel, but only `vllm-0.34.0+rocm100`, not 0.18.0. So gfx90a has a published wheel stack, at newer versions than the freeze. Whether that userland runs on this host's in-kernel amdgpu driver (rocm-smi reports driver 6.8.0-149-generic; host `/opt/rocm` is 6.2.0-66) is not established by any source.

**Claim 3 — LoRA support. PARTIAL (supported upstream, never used by any arm).** The verl copy's new engine path implements LoRA (`lora_rank`, `lora_alpha`, `target_modules: all-linear`, peft wrapper at `transformer_impl.py:293-322`, adapter-disable context for the reference pass at `engine_workers.py:387-409`) and the CreditFilter patch sits in the same file. No launcher, arm or paper experiment sets `lora_rank`; every arm trains Qwen3-8B-Base full-parameter under FSDP with parameter and optimizer offload on the h100 profile. The coefficient acts on advantages and is indifferent to how the policy is parameterised, so LoRA transfer is a first-test question, not a known property.

**Claim 4 — the launchers cannot run on one card as shipped. CONFIRMED (code).** `launch_recipe.sh:19` hard-exports `N_GPUS_PER_NODE=8` (not overridable); the hardware profile `case` accepts only `h100` or `b200` and exits 2 otherwise; `run_arm.sh` defaults `ACTOR_NNODES=2` (README and `launch_recipe.sh` disagree: README says 2, recipe default 1, run_arm exports 2); job submission is `ray job submit` to `RAY_HEAD` (a single-node `ray start --head` satisfies it); `run_arm.sh` hard-checks Qwen3-8B-Base tokenizer md5s but only warns on mismatch. Available switches: `TP_SIZE`, `PPO_MICRO_BSZ`, `LOGP_MICRO_BSZ`, `FSDP_OFFLOAD`, `GPU_MEM_UTIL`, `MAX_RESP_LEN`, `TRAIN_BATCH`, `ROLLOUT_N`, `TOTAL_STEPS` (all env-overridable), plus `SMOKE=1` (16 prompts x 8 rollouts, 3 steps) and `DRY_RUN=1`.

**Claim 5 — everything needed to pair the exponential window against the simple window is launchable by name. CONFIRMED.** `launchers/arms.sh` defines `creditfilter`, `creditfilter_d`, `hard_mask` (top-20% window, floors 0), `dapo`, `grpo`, `entropy_mask_response`, plus the ablations. This is the paired comparison of intake-2834 C4 without new code.

## 3. Reported results

None in source (the README gives no numbers). The repo ships per-position measurement records (`measurement/metrics`: Qwen3-8B-Base 294 correct and 672 wrong responses; seven further models at 120 responses each, 60 for Qwen3-32B; 13,129 full-support positions) whose tables reproduce on CPU with numpy only (`measurement/README.md`). Not run here (no compute).

## 4. Performance-principles table (cost model of the smoke, not kernels)

| Item | MI210 gfx90a (64 GB) | Zen 5 EPYC 9655 |
|---|---|---|
| Coefficient itself (argsort per row, pow, scale) | YES. Pure torch on [B,T] tensors; negligible beside forward/backward; CF-D adds one chunked softmax-square per token. | YES (same ops), irrelevant cost. |
| CPU unit tests (`python -m pytest tests/`, 13 test functions, torch only) | n/a | YES. No GPU, no vLLM; needs a torch install (default `python3` here has none; observed `ModuleNotFoundError`). |
| FSDP actor + vLLM colocated rollout, TP 1 | PARTIAL. Needs torch ROCm + flash_attn ROCm + vLLM ROCm; wheel stack exists for gfx90a at newer versions (claim 2); gfx90a has no FP8, none required by this recipe. verl's `ROCM_PATH` branch shows upstream ROCm intent. | NO as a trainer (6.04e9 optimizer tokens in the paper, intake-2834); smoke scale only. |
| Memory at 0.6B-1.7B full-parameter | YES in principle: roughly 16 bytes/parameter for mixed-precision AdamW (uncited general rule) is ~10 GB at 0.6B and ~27 GB at 1.7B, plus activations and a colocated rollout engine. 4B and 8B full-parameter do not fit; LoRA on 8B fits memory-wise (bf16 weights ~16 GB, uncited) but is untested with this coefficient. | n/a |
| Rollout length | Cap 20,480 in the recipe is the dominant cost and VRAM driver; a smoke must override `MAX_RESP_LEN` (e.g. 4096) and the 0.10/0.14 widths then apply to shorter responses (width was calibrated on 20k-cap Qwen3-8B-Base). | slow, bandwidth-bound |
| Entropy-gated fallback, mass guard | YES scalar logic; the mass guard raises `RuntimeError` when measured class mass deviates from expected by more than `CF_MASS_GUARD_TOL` (0.03), so an unusual short-response batch can abort a run. | YES |

## 5. In-house state

- No RL trainer, no torch, no verl on the host: default `python3` raises `ModuleNotFoundError: torch` (observed 2026-11-23); `model-evaluation-queue.md:L1259 @ d785b6d` records that both project uv environments lack torch/transformers/accelerate/trl/peft/datasets and marks the MI210 training-viability row `[declined: ws58 2026-11-03 content-review: training, out of scope]`; `L1257` records the reopen trigger as fired (MI210 present). `benchmark-suites.md:L1368 @ d785b6d` carries the same decline for AW-9. Both decline wordings conflict with the root rule that missing plumbing is a build cost (CLAUDE.md, Research Intake).
- Host userland: `/opt/rocm/.info/version` = 6.2.0-66; production kernels and the speech kernels are built against ROCm 6.2 (CLAUDE.md kernel set); a training venv must therefore carry its own ROCm userland (wheel stack) and must not touch `/opt/rocm`. Kernel driver: in-kernel amdgpu of 6.8.0-149-generic.
- Shared-host constraints from the lane: the 2026-07-29 note at `model-evaluation-queue.md:L1259` says a Python ROCm trainer is invisible to E5's process/SMT-affinity gates; any smoke needs a quiet-window lease and must stay off the MI210 host threads 88-95.
- Upstream-present check: n/a (no llama.cpp content).

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane file, status) | Compute | Stop/decision rule and question |
|---|---|---|---|---|
| CR1 | Create a throwaway gfx90a training venv from the published ROCm wheel stack (torch 2.13.0+rocm10.0.0, rocm-sdk-device-gfx90a, ROCm flash_attn 2.8.3; fallback torch 2.9.1+rocm6.4), run `python -m pytest tests/` of CreditFilter on CPU, then `torch.cuda.is_available()` plus one FSDP forward/backward of Qwen3-0.6B-Base on the MI210. Refines intake-2834 C1. | `model-evaluation-queue.md` row at L1259 (currently `[declined: ws58 ...]`; decline wording to be overturned) | CPU for tests; one short GPU row in a quiet window, not on q3 host threads | Question: does the published gfx90a wheel stack initialise under this host's 6.8 in-kernel driver and complete one step within 64 GB? Stop on answer after the first completed step with peak VRAM recorded; stop on futility if device init fails for both the rocm10 and the rocm6.4 stacks (record both errors). |
| CR2 | Write the single-card patch set for the launchers (`N_GPUS_PER_NODE` override at `launch_recipe.sh:19`, an `mi210` hardware profile with `TP_SIZE=1`, `FSDP_OFFLOAD=True`, small `GPU_MEM_UTIL`, `MAX_RESP_LEN`~4096, `ACTOR_NNODES=1`, single-node `ray start --head`) and record which vLLM ROCm version verl `f92bc5c` can drive (wheel index offers only 0.34.0+rocm100). | `model-evaluation-queue.md` (next to CR1) | code/doc-only | Question: can the verl copy's vLLM rollout run against vLLM 0.34 ROCm, or must the first smoke use a non-vLLM rollout (HF generate)? Done when the patch set and the answer are written; futility if the vLLM adapter needs more than an import-level change (then choose CR3 path B). |
| CR3 | Lift `apply_credit_filter` into a trainer-agnostic module (inputs: advantage, mask, entropy, records with `prompt_uid` and `answer_correct`) and run the repo's 13 CPU tests unchanged against it, so the coefficient can be attached to any GRPO loop (TRL, our own, verl) and to LoRA policies. Answers the LoRA question. | `model-evaluation-queue.md` (conditional on CR1) | code-only, CPU | Question: does the coefficient need anything from verl beyond tensors? Done when tests pass in isolation; if the CF-D `sum_pi2` input cannot be produced outside the verl patch, record that the D arm is verl-only. |
| CR4 | After CR1, run the repo arms `dapo`, `hard_mask` (top-20% window) and `creditfilter` with `SMOKE=1` semantics scaled to Qwen3-0.6B-Base for 3 data seeds and report per-seed deltas. This is intake-2834 C4, now launchable by arm name. | `model-evaluation-queue.md` (conditional on CR1) | GPU, multi-day | Decision: adopt the top-20% window unless the exponential wins on accuracy and length on at least 2 of 3 seeds (paired); stop on futility if the paired deltas straddle zero after 3 seeds. |

No decline rows: every action is a provisioning or code step.

## 7. Dive-surfaced sources (unbounded grep of `research/intake_index.yaml`)

- `https://github.com/yoctta/CreditFilter`: 4 hits, ingested as the bearing entry's companion; this is that entry.
- verl upstream at `f92bc5c435c6fc2e6d1f94484164de26f4574bd7` and `https://github.com/volcengine/verl`: 0 hits for the commit; would settle which vLLM/ROCm versions the verl copy supports. Decline as a separate intake: CR2 reads the copy in tree, which is the only version CreditFilter ever ran.
- vLLM ROCm wheel index `wheels.vllm.ai/rocm/`: 0 hits; a package index, not a source. It changes CR1 only as a dated observation recorded above. Decline.
- arXiv:2506.01939 (80/20 mask), arXiv:2606.19236 (STARE), arXiv:2412.07961 (forking paths): already triaged in the intake-2834 dive; no new decision here.

## 8. Contradiction / adversarial pass

- Paper-vs-code: "already computed by the trainer" holds for entropy but not for CF-D (patched actor output, no fused kernels). README says `ACTOR_NNODES` 2, `launch_recipe.sh` defaults 1.
- The shipped freeze is internally in conflict with vLLM's own metadata (vllm 0.18.0 declares transformers<5; freeze has 5.3.0); the authors ran it, so the conflict is tolerated at runtime on their stack, but it means the freeze is not a clean `pip install` target.
- Training crash risk: the mass guard raises on a 0.03 deviation; there is no documented behaviour for short-response batches except the optional `CF_MASS_GUARD_MINLEN`.
- No independent replication of the repo was found; the repo is first-party. The paper's own limitations (one base model, one prompt set, single-run ablations) stand (intake-2834 section 8).
- The README gives no results and no seed-variance guidance; the 3 data seeds (201, 300, 400) are named only in the README option table.

## 9. Read depth

read_depth: FULL for README, `creditfilter/credit_filter.py` (384 lines), `routing.py`, `launchers/run_arm.sh`, `launchers/arms.sh`, `creditfilter/scripts/launch_recipe.sh`, `launch_train.sh`, `environment/pip_freeze.txt`, `NOTICE`, the sum_pi2 and LoRA patch sites, `tests/test_credit_filter.py` (head and test list), `measurement/README.md`. PARTIAL: `baselines.py`, `token_signals.py`, `outcome_reward.py`, `eval/`, `verl/` beyond the patch sites. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## Anchors (verbatim substrings of page.txt, verified)

- claim 0 | page | README Layout / intro | "The code is a copy of [verl](https://github.com/volcengine/verl) with the package `creditfilter/` on top."
- claim 0 | page | README Layout table | "verl 0.8.0.dev; the files changed for this work are listed in `NOTICE`"
- claim 2 | page | README Requirements | "A Ray cluster of 8-GPU nodes whose workers run Python 3.12 with torch 2.10.0, transformers 5.3.0, vllm 0.18.0 and ray 2.54.1."
- claim 4 | page | README Options table | "number of 8-GPU nodes, 2 by default"
- claim 4 | page | README Options table | "`h100` (default) or `b200`; throughput settings only"
- claim 4 | page | README Options table | "`SMOKE=1` | 3 steps on a small batch"
- claim 4 | page | README Options table | "`DRY_RUN=1` | writes the job to the run directory and submits nothing"
- claim 4 | page | README Layout table | "CPU unit tests: `python -m pytest tests/`"

Anchors verified: 8 of 8 (python count >= 1 in `creditfilterrepo/page.txt`).

## 10. Artifact audit

artifact audit: clean (only this file and `drafts/creditfilterrepo.json` written; reading material is the pre-existing clone; 8 anchor quotes verified in `creditfilterrepo/page.txt`).

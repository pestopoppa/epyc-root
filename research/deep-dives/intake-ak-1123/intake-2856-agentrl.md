# Dive — agentrl — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/html/2510.04206v1", retrieved: "2026-11-23", sha256: "4cab0131aae7"}
> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/THUDM/AgentRL/main/README.md", retrieved: "2026-11-23", sha256: "9b2924ab7a86"} (README only; `trainer/pyproject.toml` read via raw.githubusercontent.com as reading material; `gh api` metadata: MIT, last push 2026-01-17)

Bearing entry: intake-2835 (ADAPT). That dive recorded AgentRL as "the baseline that beats ADAPT on LiveCodeBench" and asked whether the RL-only collapse on sparse-reward domains (41.45 on TextWorld) is intrinsic or a tuning artefact, plus framework requirements.

## 1. Stage-1 fields

- **Title**: AgentRL: Scaling Agentic Reinforcement Learning with a Multi-Turn, Multi-Task Framework.
- **Authors**: Hanchen Zhang, Xiao Liu (equal contribution), Bowen Lv, Xueqiao Sun, Bohao Jing, Iat Long Iong, Zhenyu Hou, Zehan Qi, Hanyu Lai, Yifan Xu, Rui Lu, Hongning Wang, Jie Tang, Yuxiao Dong (Tsinghua University, Z.AI).
- **Version/date**: arXiv:2510.04206v1 [cs.AI], 5 Oct 2025 (about 13.6 months old at 2026-11-23), CC BY 4.0. No venue stated on the page. Code `THUDM/AgentRL`, MIT.
- **Categories**: training_distillation, agent_architecture, tool_implementation.
- **Novelty**: medium. A verl-derived fully asynchronous agentic RL trainer plus a containerised multi-environment deployment layer; algorithmic additions are cross-policy sampling and per-task advantage normalisation.
- **Relevance**: low. We have no RL lane. The pieces that matter to us are (a) the corrective evidence on the ADAPT baseline and (b) its environment framework, which also runs inference-only multi-turn evaluation of local models.
- **Credibility**: 1 = peer-reviewed 0 (no venue shown) + within 12 months 0 (13.6 months) + major lab / known contributor +1 (THUDM / Z.AI, adopted into AutoGLM per the abstract) + independent corroboration 0 (a third party, Life-Harness, runs on its controller, which corroborates usability, not its numbers; ADAPT's re-implementation contradicts rather than corroborates) + commercial bias 0.
- **Verdict**: worth_investigating. The reusable output is an inference-only environment harness and a correction to how ADAPT's RL row should be read; the trainer itself waits on the verl-on-gfx90a provisioning of intake-2834 CR1.

## 2. Key claims

**Claim 0 — what the framework contributes. CONFIRMED.** (1) Fully asynchronous rollout/training: rollout engines run in their own resource group and the trainer pulls trajectories without waiting for a full batch (Figure 3, Figure 4 shows throughput gains for a 14B Qwen2.5 model on WebShop). (2) A function-call environment API with containerised task workers and a central controller. (3) Cross-policy sampling: actions within one trajectory are drawn from several models; implemented as stale rollout engines that "update parameters every multiple steps instead of one step". (4) Task advantage normalisation: each token's advantage is standardised within its task batch. Anchor: stale-engine sentence below.

**Claim 1 — "RL-only collapses on sparse-reward long-horizon domains" (the claim carried into intake-2835). OVERTURNED as an intrinsic property; evidence favours a tuning/budget artefact in ADAPT's re-implementation (not proven).** Four facts. (a) AgentRL's own Table 3 reaches ALFWorld 92.4 (Qwen2.5-3B), 91.5 (7B, with a one-shot demonstration for format), 91.5 (14B), 94.5 (32B), 93.3 (GLM-4-9B) under a binary trajectory-success reward, and for Qwen "RL training commenced directly from the base models" with "no warm-up supervised fine-tuning". (b) ADAPT's table row for AgentRL is labelled "(SFT+RL)" and its text says the baseline is "warm-started from the same SFT checkpoint" with a fixed ask price chosen by "a three-point sweep"; yet the same paragraph explains the 41.45 by "absent a warm-started competence to reinforce". The label, the method text and the explanation contradict each other (cross-source: `adapt/page.txt`). (c) 41.45 is below ADAPT's own SFT starting point (RFT 58.7), so the RL stage made the policy worse than its initialisation, which is the signature of an unstable run, not of a task RL cannot learn. (d) The scale gap is large: AgentRL used full ALFWorld training data, "over 1000 steps in a multi-task mixed setting", rollouts at temperature 0.8 with 8 samples, and "a minimum configuration of 16 GPUs for the 14B model" on H800s; ADAPT reports LoRA rank 32 "under limited compute" on 600 sampled TextWorld training tasks (per intake-2835). The one caveat: ADAPT's TextWorld is "AgentBench-FC (Liu et al., 2024)" with 109 test episodes and horizon 20, and I could not confirm it is the same harness and test split as AgentRL's AgentBench-FC ALFWorld, so the 91.5 versus 41.45 comparison is suggestive, not like-for-like.

**Claim 2 — "AgentRL beats ADAPT on LiveCodeBench (58.3 vs 56.0)". NOT-FOUND-IN-SOURCE.** The AgentRL paper contains no LiveCodeBench or code-generation result; its five environments are ALFWorld, DB, KG, OS and WebShop. The 58.3 is ADAPT's own re-implementation (SFT+RL on a harness of its own making). Nothing in AgentRL's paper speaks to the LCB result.

**Claim 3 — cross-policy sampling and task advantage normalisation are what make multi-turn multi-task RL stable. PARTIAL.** Table 6 (ablation, "AgentRL-14B" row 93.1 / 64.0 / 67.7 / 45.1 / 55.0, average 65.0) removes cross sampling to 91.9 / 61.6 / 55.7 / 39.7 / 54.5 (60.7) and task-advantage normalisation to 91.1 / 62.6 / 54.7 / 38.0 / 50.6 (59.4). The effects are small on ALFWorld (about 1.2 and 2.0 points) and large on KG (12 and 13 points). The baseline row of Table 6 does not match the 14B row of Table 3 (91.5 / 72.2 / 72.8 / 43.6 / 58.5, average 67.7), so the ablation was run on a different run or schedule that the paper does not describe. Algorithmic tricks therefore do not explain ALFWorld performance; scale and data do.

**Claim 4 — one multi-task model matches the best of five single-task models. CONFIRMED (Table 4: 67.7 against 67.8).** The same table shows the only "collapse" in the paper: a single-task model evaluated off its training task falls to near zero (AgentRL-DB scores 0.2 on ALFWorld; AgentRL-Webshop 0.0). That is cross-task transfer failure, not within-domain sparse-reward failure.

**Claim 5 — framework requirements. CONFIRMED (paper plus repo).** Training: Ray worker pools (rollout, actor, reference), FSDP, NCCL tensor streaming from actor rank 0 to rollout shards, SGLang rollout (`sglang[all]>=0.4.8`, or `vllm>=0.11.2` as an option), `torch>=2.6.0`, hard dependency `flash-attn>=2.4.3`, pyproject classifier "Environment :: GPU :: NVIDIA CUDA", Megatron option. README placement-group example: actor and reference share one resource group and rollout sits in another, so the async design as shipped needs two GPU groups. Environments: Go controller (target up to 10,000 sessions), FastAPI task workers per task, gRPC transport, containerised workers; evaluation script `server_agent.py -u <openai-compatible url>/v1 -c <controller>/api <task>` works for local models.

## 3. Reported results (as the source states them)

- Table 3 (task success rate %, mean and SD of four repeats; AgentBench-FC, temperature 0.8): AgentRL w/ Qwen2.5-3B-Instruct ALFWorld 92.4, DB 60.0, KG 55.0, OS 40.5, WebShop 52.1, average 60.0; 7B 91.5 / 63.7 / 57.8 / 40.8 / 56.1, average 62.0; 14B 91.5 / 72.2 / 72.8 / 43.6 / 58.5, average 67.7; 32B 94.5 / 70.4 / 77.0 / 51.7 / 58.6, average 70.4; GLM-4-9B-0414 93.3 / 66.9 / 75.7 / 33.2 / 55.9, average 65.0. Prompted baselines: GPT-5 ALFWorld 65.4 and average 52.2; Claude-Sonnet-4 73.6 and 57.4; DeepSeek-R1 51.4 and 49.3; Qwen2.5-14B-Instruct 8.7 and 27.2.
- Table 5 (BFCL-v3, Qwen2.5-32B-Instruct 59.9 to 61.4 overall); Table 4 multi-task 67.7 versus best-of-five 67.8; Table 6 ablations (claim 3).
- Training: H800 GPUs, at least 16 GPUs for 14B; GRPO baseline with custom modifications; rollouts at temperature 0.8, 8 samples per rollout; binary trajectory reward; -0.2 for exceeding maximum rounds or response length; SGLang rollout plus FSDP; more than 1000 steps in the multi-task mixed setting; GLM-4-9B needed a small SFT cold start for function-call format.

## 4. Performance-principles table (mechanism and cost model)

| Principle | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Async rollout/training split across resource groups | PARTIAL. With one MI210 the rollout and actor/reference groups cannot be separated (README placement groups: actor/ref in one group, rollout in another, rollout bundles sized by tensor-parallel degree); a one-card run needs a colocated synchronous mode that the shipped example does not provide, or the second MI210 the operator is installing (CURRENT-CAMPAIGN.md:L90-L91 @ d785b6d). | NO as a trainer; fine as a rollout-side CPU host only for tiny models. |
| Cross-policy sampling via stale rollout engines | PARTIAL. Needs two engine copies resident; on 64 GB feasible only for small models; the sampling idea (mix an old and a new policy) is algorithmic and device-independent. | n/a |
| Task advantage normalisation | YES. Arithmetic on advantages; same family of per-token reweighting as intake-2834, device-independent. | YES |
| Containerised environment controller + task workers (inference-only use) | YES. No GPU in the environment layer; docker is installed on this host (`/usr/bin/docker`, socket present, observed). | YES. Environments run on CPU anyway. |
| FSDP actor + SGLang rollout stack | PARTIAL. torch>=2.6 and flash-attn are hard dependencies; the gfx90a wheel stack exists at newer versions (intake-2834 CR1 observation: torch 2.13.0+rocm10.0.0, ROCm flash_attn 2.8.3); SGLang on ROCm is not verified here (uncited). | NO |

## 5. In-house state

- No multi-turn environment suite in the lane: a grep of `handoffs/active/*.md` @ d785b6d finds no ALFWorld, WebShop or AgentBench environment rows (Terminal-Bench rows exist in `eval-tower-program.md:L1800` etc.). `benchmark-suites.md:L1368 @ d785b6d` records AW-9 (multi-env GRPO) as `[declined: ws58 2026-11-03 content-review: GPU-gated GRPO training; training is out of scope for this stack]`, the decline wording the root rule forbids.
- The orchestrator's escalation/ask machinery is rule- and memory-driven (intake-2835 section 5); nothing consumes an RL-trained ask policy. `routing-program.md:L108-L112 @ d785b6d` lists xRouter and Router-R1 as "not applicable" for multi-GPU RL.
- The MI210 is present and the training-environment row is blocked on provisioning (`model-evaluation-queue.md:L1257-L1259 @ d785b6d`); AgentRL's trainer would use the same verl-family stack as CreditFilter, so one provisioning serves both (CR1).
- Upstream-present check: n/a (no llama.cpp content).

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane file, status) | Compute | Stop/decision rule and question |
|---|---|---|---|---|
| G1 | In the A4 design note (trained ask policy), replace the "RL-only collapse" premise with the corrected one (ADAPT's AgentRL row is SFT+RL with a fixed price and falls below its own SFT start; AgentRL's paper reports ALFWorld 91.5-94.5) and require two ablation arms before any in-house RL ask-policy run: DPO stage on/off and fixed price versus dual-ascent price. Refines intake-2835 A4. | `routing-program.md` (learned-routing-controller track; DAR-LAT frozen, filing a note is allowed) | doc-only | Done when the note carries the corrected premise and the two arms; the question it records is whether RL-from-SFT with a budget-solved price still degrades the SFT start. |
| G2 | Stand up AgentRL's environment controller and the ALFWorld, DB and OS task workers in docker on this host and drive one task (5 episodes) with a local role through llama-server's OpenAI-compatible endpoint using `server_agent.py -u <url>/v1`; record episode success and wall time. | `eval-tower-program.md` (agent-benchmark rows; no multi-turn environment suite exists today) | CPU rows for the environments plus inference rows on a served role in a quiet window | Question: can an inference-only multi-turn suite (the substrate Life-Harness, HookEvo and ADAPT all report on) run against our served models with no training? Stop on answer once 5 episodes complete on one task with success and latency recorded; stop on futility if the containers do not build or the function-call format cannot be served by the role (record which). |
| G3 | Add AgentRL's trainer to the verl-on-gfx90a provisioning list as the second consumer (alongside CreditFilter), with the note that its async split needs two GPU resource groups, so a one-card run needs a colocated mode or the second MI210. Refines intake-2834 CR1/CR2. | `model-evaluation-queue.md` (next to the intake-2834 rows; row L1259 decline wording to be overturned) | doc-only | Decision: which consumer to provision first; done when both consumers' requirements are listed in one place. |
| G4 | DECLINE: reproduce AgentRL's Table 3 average of 70.4. Reason specific to this entry: that run is 32B, at least 16 H800 GPUs for 14B and over 1000 multi-task steps on five environments we do not host; the transferable question (does RL from SFT with a calibrated price learn ask timing on one environment) is covered by G1's ablation arms at small scale once G3 provisioning exists. | n/a | n/a | n/a |

## 7. Dive-surfaced sources (unbounded grep of `research/intake_index.yaml`)

- `github.com/THUDM/AgentRL` (0 hits for URL and for arXiv 2510.04206; "AgentRL" appears only inside intake-2835): read here; this is its entry.
- `github.com/THUDM/AgentBench` (0 hits for the repo URL; the benchmark name appears in about 39 unrelated lines): AgentBench-FC task definitions and the environment images that AgentRL's controller serves. Would change ledger row G2 (what must be installed). Recommend ingest-and-dive: only its deployment docs and ALFWorld/DB/OS task definitions are needed.
- arXiv:2602.03412 and arXiv:2606.08275 (carried from intake-2835): unchanged, decline for this wave.
- Life-Harness `github.com/Tianshi-Xu/Life-Harness` runs its AgentBench evaluation on "AgentRL controller and native workers" (its README, read in the lifeharness dive): corroborates that the controller is reusable; no further source needed.

## 8. Contradiction / adversarial pass

- Table 6's baseline row differs from Table 3's 14B row (93.1 / 64.0 / 67.7 vs 91.5 / 72.2 / 72.8); the ablation's run configuration is not stated.
- The 7B ALFWorld number (91.5) needed a one-shot demonstration at evaluation "as it fails to generate valid tool call format", so format competence is partly prompt-supplied there.
- The paper's data for OS, KG and DB was synthesised with "high-performance APIs (o3 and claude4-sonnet)" and BIRD; ALFWorld and WebShop use their official training sets. The training distribution is therefore much larger and more frontier-shaped than ADAPT's 600 TextWorld tasks.
- Authors' stated limitation: cross-policy sampling "can introduce minor distributional shifts" and "mild, transient instabilities".
- ADAPT's re-implementation, not the AgentRL paper, produced the 41.45 and 58.3; the AgentRL authors have no say in either number. No independent replication of AgentRL's Table 3 was found.
- The repository's last push is 2026-01-17, about ten months before this dive; the README's `agentrl-eval` path is marked experimental.

## 9. Read depth

read_depth: FULL for the paper main text, appendices D-G and Tables 3-6; README read in full; pyproject read; trainer source not read. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## Anchors (verbatim substrings of page.txt, verified)

- claim 0 | page | Section 3.1 Cross-Policy Sampling Strategy | "we mark a set of rollout engines as stale engines; these engines update parameters every multiple steps instead of one step."
- claim 1 | page | Table 3 (3B row) | "AgentRL w/ Qwen2.5-3B-Instruct 92.4 92.4 ±0.5"
- claim 1 | page | Section 4.1 | "Note that there is no warm-up supervised fine-tuning before applying AgentRL to all Qwen models."
- claim 1 | page | Appendix E.2 | "For the Qwen series, RL training commenced directly from the base models."
- claim 1 | page | Table 3 footnote | "We provide a one-shot demonstration for Qwen2.5-7B-Instruct in ALFWorld evaluation"
- claim 1 | page | Appendix E.2 | "a binary reward function was designed, assigning a score based on the correctness of the entire trajectory."
- claim 3 | page | Table 6 | "AgentRL -14B 93.1 ±0.5 64.0 ±0.5 67.7 ±2.0 45.1 ±2.0 55.0 ±0.7 65.0 - cross sampling 91.9 ±1.2 61.6 ±1.0 55.7 ±1.4 39.7 ±2.3 54.5 ±1.3 60.7"
- claim 4 | page | Table 4 | "AgentRL (One Model) 91.5 91.5 ±0.9 72.2 72.2 ±0.9 72.8 72.8 ±1.8 43.6 43.6 ±1.9 58.5 58.5 ±1.2 67.7"
- claim 4 | page | Table 4 | "AgentRL -DB 0.2 0.2 ±0.5 73.9 73.9 ±0.7"
- claim 5 | page | Appendix E.2 Training | "Training was conducted on H800 GPUs, with a minimum configuration of 16 GPUs for the 14B model."
- claim 5 | page | Appendix E.2 Training | "over 1000 steps in a multi-task mixed setting"

Anchors verified: 11 of 11 (python count >= 1 in `agentrl/page.txt`).

## 10. Artifact audit

artifact audit: clean (only this file and `drafts/agentrl.json` written; all anchor quotes verified in `agentrl/page.txt`).

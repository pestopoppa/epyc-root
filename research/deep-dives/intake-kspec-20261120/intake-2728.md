# Budget Internalization: Fixed-Budget RLVR Trades Test-Time Scaling for In-Budget Accuracy

- **Intake**: intake-2728 (`intake-2728#record`)
- **Source**: https://arxiv.org/html/2611.26172v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: context-and-token-economy.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Use as an evaluation rule (score thinking-budget policies at several budgets with an uncensored top budget). Do not generalize magnitudes beyond 4-5B math RL; we run no GRPO training.

## Key claims (anchored)

0. Fixed-cap GRPO on Qwen3.5-4B, Gemma4-E2B and Nemotron-3-Nano-4B gains near the training cap but stops improving above it and falls below the base model at larger budgets.
   - Abstract: "We observe it across Qwen3.5-4B, Gemma4-E2B, and Nemotron-3-Nano-4B and two reasoning training tasks"
   - Abstract: "but their accuracy stops improving and falls below the base model at larger budgets"
1. SFT on artificially truncated traces reproduces the effect while SFT on naturally short traces does not; standard GRPO assigns truncated rollouts zero reward.
   - Abstract: "SFT on artificially truncated traces reproduces budget internalization, whereas SFT on naturally short traces does not"
   - s3: "Standard GRPO assigns it zero reward"
2. Stronger KL and lower training-data truncation preserve more scaling but stronger KL reduces in-budget accuracy; forcing an answer on truncated rollouts removes most of both effects; no tested intervention keeps both.
   - Abstract: "Stronger KL regularization and lower training-data truncation preserve more scaling, but stronger KL reduces in-budget accuracy."
   - Abstract: "Forcing an answer on truncated training rollouts largely removes budget internalization, but also removes most of the in-budget gain."
   - s1 contribution 3: "no tested intervention combines the full in-budget improvement with the base model"
3. Budget forcing improves base-model accuracy at a matched token allowance, but making the trained model spend more tokens does not restore scaling; prompt-stated budgets are largely ignored.
   - s2.3: "Budget forcing can therefore improve base-model accuracy at a matched total token allowance, while making the trained model spend more tokens does not restore its test-time scaling."
   - s2.3: "Stating the budget explicitly in the prompt offers no reliable alternative, as models not trained on such cues largely ignore them"
4. Tested models have four to five billion active parameters, most experiments are math, and only the main comparison uses three seeds.
   - s5 Limitations: "The tested models have four to five billion active parameters, and most experiments use mathematical reasoning"
   - s2: "Only the main DeepScaleR/AIME comparison uses three training seeds"

## Claim corrections

- claim 0: **narrowed** — Large on AIME; on GPQA/LCB the high-budget deficit is small (Qwen 8k: -2.2 and -1.0 pp at 64K) with much shorter outputs, so internalization can be an efficiency gain.
- claim 2: **narrowed** — Each mitigation trades in-budget gain; two KL values, one seed.

## Dive record

2026-11-20 Stage-2 dive (sonnet; full read). We run no local GRPO/RLVR weights training (AP-27 RLVR eval-tower scaffolding only, Ouro withdrawn 2026-11-10, autopilot-program.md:L73-L81 @e9ee76c; eval-tower-program.md:L159 defers GRPO training). The usable content is an evaluation rule for thinking-budget routing on served models: score candidate policies at several budgets with accuracy and output length, with an uncensored top budget (TB-SEM-1b found omitted-budget thinking exhausting the ceiling, context-and-token-economy.md:L1112-L1117 @e9ee76c). Adversarial pass not run. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d) Stage-2 close-out (2026-11-20): Muennighoff et al. 2025 budget forcing declined (no arXiv id in the source; the procedure is already implemented via thinking.budget_tokens).

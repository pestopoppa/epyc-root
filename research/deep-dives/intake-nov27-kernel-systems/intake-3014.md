# When Every Rollout Fails: Splicing Learner-Conditioned Options into Long-Horizon Agent RL

[Primary source](https://arxiv.org/abs/2611.34777v1) · intake-3014 · 2026-11-27

All-fail binary rewards give zero reward-dependent GRPO advantage. SPLICE samples a failed trajectory, uses a stronger model with full history and terminal feedback to select from resumable points (every four turns), then proposes three local options at an adaptive horizon (0.3 times mean rollout length). Terminal options go straight to the verifier; incomplete options get three learner continuations. Drop zero-return options; softmax over standardized positive means; alternate GRPO and mean-token loss on bounded proposal-action tokens. The variable-length loss is only a surrogate for the sequence KL projection, and Proposition 1 concerns fixed empirical option returns, not post-update true return. Table 1 with three runs and equal available tasks, not compute: Qwen3-8B-CS SWE/BrowseComp 15.9/20.2→25.7/29.3, Qwen3.5-9B 58.4/46.2→61.2/50.7 versus GRPO; also beats tested SFT+RL and adapted ReLIFT. Table 2 on initially failed SWE training tasks: graduation 18.9% vs GRPO 8.1% and ReLIFT 15.9%; fewer teacher turns than ReLIFT (93.5k vs 113.4k), despite lower teacher proposal hit (30.7% vs 55.1%). Figure 2 author reports less wall time than ReLIFT/SFT, while GRPO remains fastest. Table 4 teacher continuation raises SWE resolve slightly 25.7→26.2 with ~4× teacher turns; supervising full teacher suffix drops it to 22.3. Appendix F proposal point selection +1.3 pp resolve over random (24.4→25.7) with three runs. Expensive state restoration and 3 continuation samples can dominate economics or yield false zero-return. Appendix D training used 32 H200 GPUs; no test-time benchmark. Bounded search surfaced source summaries and ReLIFT itself, no independent replication.

Read method §4, experiments/limitations §§5–6, Tables 1–4 and Appendices B–F including hardware, branch selection and verifier examples. Appendix A proof algebra, introduction/related work in full and references not read.

## Evidence

- Local guidance values come from execution by the current learner after bounded teacher-proposed options. [§4.1, learner-conditioned evaluation (#S4.SS1)](https://arxiv.org/html/2611.34777v1)
- SPLICE achieved higher SWE training-set graduation despite a lower proposal hit rate than its adapted ReLIFT comparator. [§5.3, proposal hit and graduation (#S5.SS3)](https://arxiv.org/html/2611.34777v1)

## Scope and local transfer



The transfer is checkpointed bounded continuation with terminal verifiers, tested against restart/full-strong guidance in benign replay fixtures, rather than inferring serving gains from training. Compare branch restore, total learner and teacher turns, and cost-to-verified-completion. CPU replay suits sandbox/fixture checks and later learner sampling on bandwidth-budgeted roles; MI210 could batch parallel learner branches if state copy and verifier time do not dominate. Existing session checkpoints and trajectory artifacts are candidate consumers, with exact environment restoration a separate requirement.

A terminal MemRL failure score does not encode the first repairable action, options or a validated continuation. Audit retained all-fail trajectory groups for reproducible environment state, a bounded repair point and verifiable continuation. Count recoverable groups before proposing any training or changing MemRL rewards.

## Sources surfaced

- https://arxiv.org/abs/2506.07527 — ReLIFT is the full-trajectory guidance comparator; inspect original versus SPLICE online adaptation. Exact ID absent from lane index.

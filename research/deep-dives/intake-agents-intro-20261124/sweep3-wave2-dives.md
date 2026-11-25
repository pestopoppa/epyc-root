# Sweep 3 — Stage-2b wave 2, final (intake-2931..2941)

This is the third and last Stage-2 sweep allowed by the operator's authorisation. Sources surfaced by
this wave are declined by that cap and recorded below and in each bearing entry.

| ID | Source | Bears on | Finding | Agent |
|---|---|---|---|---|
| intake-2931 | Zhan et al., Adaptive Attacks Break Defenses, arXiv:2503.00061v2 | 2927 | All eight defenses were bypassed above 50% ASR with white-box adaptive attacks on Vicuna-7B and Llama3-8B agents. The LLM detector's detection rate fell to 0%. | J |
| intake-2932 | PromptArmor, arXiv:2507.15219v1 | 2927 | GPT-4.1 guardrail: FPR 0.56, FNR 0.13, ASR 0.00. Qwen3-8B FNR 26.59% without reasoning. The only adaptive test is a black-box fuzzer. | J |
| intake-2933 | DataFilter, arXiv:2510.19207v2 | 2927 | Llama-3.1-8B fine-tuned filter with released weights. AgentDojo ASR 0.4% average, utility 79.4% vs 81.4%. 83% ASR under a strong adaptive attack. | J |
| intake-2934 | What Does a Harness Buy? Tokens, Mostly, arXiv:2610.04433v2 | 2915 | Reruns and harness swaps both flip about 13% of tasks at the median (model swaps flip 26%). Bounded harness gaps are 2-5 points. | K |
| intake-2935 | Rollout Cards, arXiv:2605.12131v1 | 2921 | 0 of 50 audited repos report failed runs beside the headline. Changing only the reporting rule moves scores up to 20.9 points. | K |
| intake-2936 | Beyond Chunk-Then-Embed, arXiv:2602.16974v1 | 2912 | Paragraph or fixed-size chunks win in-corpus. Late chunking helps in-corpus but hurts in-document retrieval. No late-interaction model was tested. | J |
| intake-2937 | (When) Should a Software Factory be Lights-off?, arXiv:2610.13668v1 | 2918 | A comprehensive single prompt beats multi-agent review at similar cost. Best agent recall@5 is 71.9% averaged. No precision is reported. | K |
| intake-2938 | Self-Correction Bench, arXiv:2507.02778v3 | 2914 | 64.5% blind spot on injected errors; 'Wait' cuts it 89.3%. Only 4.3-10.8% of own-policy errors are recovered. No correct-trace control. | L |
| intake-2939 | The Self-Correction Illusion, arXiv:2606.05976v2 | 2914 | Role relabelling raises explicit flagging by 23-93 points without significant answer change. The authors call it diagnostic, not a defense. | L |
| intake-2940 | Tyen et al., arXiv:2311.08516v3 | 2929 | Mistake finding is poor. With the location given, backtracking gains 18-44 points on wrong traces. | L |
| intake-2941 | RISE, arXiv:2407.18219v2 | 2914 | Fine-tuning on multi-turn rollouts gives gains on 7-8B open models. Prompt-only Self-Refine degrades. | L |

## Derived-actionables ledger (wave 2)

| Row | Draft | Proposed disposition |
|---|---|---|
| w2a-A1 | Adaptive-attack arm and cross-evaluation grid for arm D | monitor M6 |
| w2a-A2 | Valid-output rate and utility beside ASR | P4 AEI-CT18-ARMD-RUN metrics |
| w2b-A1 | Arm D-1, detect-and-extract guardrail on the local worker role | P4 |
| w2b-A2 | Prompt-injection definition ablation for non-frontier guardrails | P4 AEI-CT18-ARMD-PREP |
| w2c-A1 | Arm D-2, DataFilter weights via GGUF | P4 |
| w2c-A2 | Filter sees the trusted task; clean false-removal rate | P4 |
| w2f-A1 | Structure-chunk baseline plus in-corpus and in-document metrics | P5 |
| w2f-A2 | LumberChunker or proposition chunking | decline (no in-corpus gain at about 1000x lower throughput, Table 3) |
| w2d-A1 | Same-configuration rerun arm plus discordance-based MDE | P2 AEI-RERUN-ARM-OD (measurement trust boundary) |
| w2d-A2 | Decompose harness token cost (preamble, history, steps) | monitor M2 |
| w2e-A1 | Drops manifest plus named reporting rule | P2 AEI-DROPS-MANIFEST |
| w2e-A2 | Re-grade reviewer rollouts under an alternative rule | monitor M7 |
| w2g-A1 | Comprehensive-prompt arm before multi-reviewer arms | P3 AEI-REV-A1-LOCATE-PROBE arm P |
| w2g-A2 | Known-bug reviewer corpus from repo history | monitor M7 |
| w2h-A1 | 'Wait' continuation arm on A1 | decline (no correct-trace control in source; A1 AUC is near chance); reopen only if the location arm lifts |
| w2i-A1 | Check the message role of the worker patch in the A1 runner | P3 AEI-REV-A1-PRECHECK |
| w2i-A2 | Role-relabel arm on A1 | decline (flagging-only gains; needs the error location; false positives untested) |
| w2j-A1 | Oracle defect-location arm on A1 | P3 AEI-REV-A1-LOCATE-PROBE arm L |
| w2k-A1 | RISE-style self-correction fine-tuning | monitor M7 |

## Dive-surfaced sources (wave 2) — all declined by the three-sweep authorisation

| Source | Bears on | What it would settle |
|---|---|---|
| arXiv:2505.18333 Critical Evaluation of Prompt-Injection Defenses | 2931 | independent utility cost of sanitizer defenses |
| arXiv:2505.05849 AgentVigil | 2932 | a black-box adaptive attacker usable on the CPU host |
| PromptLocate (id not given) | 2932 | alternative injected-span extractor |
| arXiv:2507.02735 Meta SecAlign | 2933 | model-level alternative to filtering |
| arXiv:2607.22585 Vats and Golev | 2934 | replication of harness-gap noise |
| arXiv:2602.07150 Bjarnason | 2934 | rerun noise on SWE-bench |
| arXiv:2611.02566 CR-Bench-v2; arXiv:2603.11078 CR-Bench | 2937 | false-positive-aware review comparators |
| arXiv:2412.06559 ProcessBench | 2940 | whether 27B-122B local models can localise errors |
| arXiv:2505.05410 CoT faithfulness; Pan et al. 2026; Malik et al. 2026 | 2939, 2938 | role-asymmetry mechanism; on-policy error replication |

Each becomes eligible again only through a new intake session.

## Second reader

A haiku agent checked 164 claims across 34 blocks: 113 yes, 51 partial, 0 no. Every "partial" marks
a claim that adds context from elsewhere in the same source (counts, conditions, mechanism names)
beyond its single anchor quote. No quote contradicts its claim. Per the skill, the disagreements go to
the operator in stage3-plan and do not auto-overturn anything. The plan quotes no figure that rests
only on a "partial" claim's extra content.

Correction 2026-11-25 (status audit): the M7 monitor rows w1l-A3, w1l-A4, w1m-A3, w2e-A2, w2g-A2, w2k-A1 trigger on "RM-3 opens", but RM-3 was already open with RM-3a-d ticked 2026-07-19 (handoffs/active/reviewer-control-plane.md, RM-3 block ~L988-992). That trigger is dead. Re-point each of the six to the next unticked RM-3-line sub-box, RM-4 (Confirmation-tier protocol, the next unticked box after RM-3a-d); C-CRAB saturation and a verifiable-reward training lane remain as the other M7 triggers. Rows needing finer placement: re-triage when RM-4 is dispatched.

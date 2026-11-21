# Stage-2 dive: nvidia/Qwen3.5-4B-Qwen3.8-27B-Draft (intake-2757)

- Source: HF model card README pinned at bc5ad93d03d96a9c1ef49748e00ec5130a7080de (`hf-draft/extracted.txt`)
- read_depth: FULL. The card has **no wall-clock, tok/s or latency numbers**, only acceptance.
- lane_head: ac1347f5d3218531bb369c286837630bf842ff74

## Claim verification

| Claim | Verdict | Specifics |
|---|---|---|
| External 4.21B draft from Qwen3.5-4B, shares the target tokenizer and vocab | CONFIRMED | Qwen3_5ForCausalLM. 0.64B tied embedding + 3.57B non-embedding = 4.21B. Vocab 248,320. Qwen3.5 is a hybrid (GDN) family, so the draft has recurrent state. |
| Trained on the target top-20 distribution over target-synthesized responses | CONFIRMED | 199,998 single-turn prompts from Nemotron-Post-Training-Dataset-v2 (9 categories, prompts over 3,072 tokens dropped). Responses by Qwen3.8-27B. Top-20 under the serving policy. Seq len 12,288. ModelOpt v0.48.0rc0. The "1B-10T tokens" figure is a boilerplate band, not a count. |
| Drafts under temp 1.0 / top-k 20 / top-p 0.95 with rejection sampling | CONFIRMED | "samples a block of candidate tokens autoregressively". Block 16 means 16 **sequential AR** draft steps per round, not a parallel block drafter. |
| Tokens per target step at block 16 beat the MTP head | CONFIRMED, narrowed | The card defines acceptance as "tokens returned per target step". Qualitative 5.58 vs 3.81; throughput-32k 5.11 vs 3.86 (roleplay 4.41 lowest, rag 6.58 highest; high_entropy 4.01). The MTP head was also run at block 16. Test hardware: Groq 3 LPU / vLLM. Siblings: 0.75B 3.92/3.60 and Llama-1B (1.48B) 3.42/3.07. The MTP head is 0.42B but borrows 2.54B of target embedding/head. |
| GGUF exists (operator note) | NOT-FOUND for this draft | One WebSearch found only base-model GGUFs (`bartowski/Qwen_Qwen3.5-4B-GGUF`, `unsloth/Qwen3.5-4B-GGUF`). The base model is not this trained draft. Self-conversion is supported: `conversion/__init__.py:212` maps Qwen3_5ForCausalLM; the arch is `qwen35`. |

## Cost-vs-acceptance model

In-house numbers:
- DFlash2 drafter: Q8_0, size_label 1.9B, headless (borrows the target embd/output), block_size 8, so n_draft_max = 7 (`speculative-decoding.md:L1149`, `:L1889`).
- Throughput: 5.80 tokens/step at np1 on the benchmark shape. tok/s np1 77.0, later ~86 (`:L1153-1166`, `:L1931`).
- Production temperature 1: acceptance 0.29-0.39, so about 3.4 tok/round on a ~51.6 ms round, roughly 65 tok/s (inferred).
- Round split: drafter 9.4 ms of 51.6 ms; W1 verify 37.6 ms; s = 2.39 ms per extra verify row (`:L1840`, `:L1968-1975`, `:L1980`).

Card acceptance converted to a per-token rate: 5.58 at gamma=16 solves (1-a^17)/(1-a) = 5.58, so a ≈ 0.83.

MI210 (27B Q8_0 target, 4B Q8_0 = 4.47 GB draft, ~6 ms/draft token at the 27B's observed 0.76 TB/s effective rate):

| gamma | tokens/round | round ms | tok/s |
|---|---|---|---|
| 3 | 3.08 | 62.8 | 49 |
| 4 | 3.55 | 71.2 | 50 |
| 6 | 4.26 | 88 | 48 |
| 16 (card) | 5.58 | ~172 | ~32 |

- The 0.8B sibling (a ≈ 0.745, ~1.5 ms/token) peaks at about 57 tok/s.
- Break-even against DFlash2 at temperature 1 (~65 tok/s) at gamma=4 needs a draft token of 1.65 ms or less. The physical floor at the 1.6 TB/s HBM peak is 2.8 ms. **It is not likely to beat DFlash2 on the MI210.**
- DFlash2 wins because it drafts 7 tokens in one 9.4 ms forward, whereas an AR draft pays per token.
- Even with a = 0.95 the 4B draft only ties DFlash2 at temperature 1.

CPU (bandwidth-bound, 27B Q8 ~28.7 GB/token vs 4.47 GB/token):
- Draft cost ratio c ≈ 0.16 per draft token.
- Assuming verify rows add about 5% each, gamma 4-5 gives roughly 1.8-1.9x over plain decode (modeled).
- Historical precedent: an AR drafter beat DFlash on CPU (36.5 vs 13.0 t/s, `kernel-champion-and-promotion.md:L2320`).
- But there is no CPU-served 27B today. The CPU serves Q38FN with MTP.

llama.cpp support:
- `common_speculative_are_compatible` checks vocab type, BOS/EOS, a size difference of at most 128 and token text (`common/speculative.cpp:72-130` @ ffc1bac). It is expected to pass because the card says the vocab is shared (inferred).
- Risk: the draft is hybrid, so draft-simple rollback (`llama_memory_seq_rm` on ctx_dft, `:774`) needs recurrent rollback slots on the draft context. This is unverified.

SPEC-PIT.1:
- The draft is trained and evaluated at temperature 1 with rejection sampling. Any arm using it must pass the SPEC-PIT.1 KS gate (`speculative-decoding.md:L617`).
- Its 5.58 is not comparable with our greedy 5.80 at block 8.

## Principles

| Principle | Evidence | MI210 | Zen5 | Port | Consumer |
|---|---|---|---|---|---|
| External AR draft distilled on target top-20 under the serving policy | Training/Inference sections | Modeled loss vs DFlash2 (floor 2.8 ms vs 1.65 ms break-even) | Modeled ~1.8-1.9x over plain decode | S | speculative-decoding.md (CPU fallback) |
| Top-20 serving-policy KL distillation recipe | Training Dataset | Precedent for the DF2-FT-1 KL arm | same | S | DF2-FT-1 |
| Train and measure at the served sampling policy | Inference section | Temp-1 arms gated by SPEC-PIT.1 | same | S | SPEC-PIT.1 |

## Adversarial pass

- WebSearch "Qwen3.5-4B-Qwen3.8-27B-Draft GGUF" found no GGUF of the draft and no independent acceptance or speed reports.
- Weaknesses in the card:
  - No speed data at all.
  - Groq LPU hardware.
  - SPEED-Bench only.
  - The MTP head was evaluated at block 16, which is far past its usual depth, so the 5.58 vs 3.81 gap partly reflects that.

## Derived-actionables ledger

| id | action | owner | bears on | disposition | reason |
|---|---|---|---|---|---|
| hf-draft-A1 | Serve the 4B/0.8B draft for the 27B on the MI210 instead of DFlash2 | speculative-decoding.md | — | decline | Floor 2.8 ms/token > 1.65 ms break-even. Best modeled ~50 (0.8B ~57) tok/s vs ~65 (temp 1) / ~86 (greedy). Reopen if s < 1 ms/row. |
| hf-draft-A2 | If a CPU 27B lane opens: self-convert, check compat and recurrent draft rollback, then temp-1 acceptance on replayed :8083 contexts plus CPU tok/s vs plain and DFlash2, gated by SPEC-PIT.1 | speculative-decoding.md | SPEC-PIT.1 | task | Bandwidth model favours it on CPU; low rank |
| hf-draft-A3 | Precedent note under DF2-FT-1 (top-20 serving-policy teacher, 200k prompts of 3,072 tokens or fewer, seq 12,288) | speculative-decoding.md | DF2-FT-1 | task | Sets data scale and teacher truncation |

## Dive-surfaced sources

- https://huggingface.co/nvidia/Qwen3.5-0.8B-Qwen3.8-27B-Draft (cheap end of the draft-cost curve). **Decline**: modeled ~57 tok/s on the MI210, and the comparison table already covers it.

artifact audit: clean

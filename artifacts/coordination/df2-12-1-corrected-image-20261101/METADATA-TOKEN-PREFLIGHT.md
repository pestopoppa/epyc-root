# Frozen-v10 vocabulary-only prompt count

An NI scratch utility, `metadata_prompt_count.cpp`, used frozen v10 `common_chat_templates_init`/`common_chat_templates_apply` with the pinned Jinja override SHA-256 `1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551`, a single user message, `enable_thinking=false`, and frozen `common_tokenize(vocab, rendered, true, true)`. It set `llama_model_params.vocab_only=true`; both model logs explicitly say `vocab only - skipping tensors`. The exact target GGUF files were SHA-256 checked before each run. The 11 candidate texts came from the frozen `PROMPTS.json` SHA-256 `de3096605c354c6346418267ad09efc5cbf6eb7599816301a940e3b93cb8e0e1`, matching the qualifier's candidate set. Both runs used an admitted R6 CPU pair, stayed below 121 MB sampled process-tree RSS, and drained their owned PIDs.

| Role | Salt A–E counts | Other planned counts | Maximum | RESULT SHA-256 |
|---|---|---|---:|---|
| frontdoor MTP target `qwen35moe` | 261 each | reuse A 180, reuse B 189, low entropy 184 each, planted 274/262 | 274 (`planted-0`) | `2d0c348ab1862472f88b4e37d92f20d0f956edd114badb42085e969c0ca3331c` |
| architect DFlash2 target `qwen35` | 261 each | same counts | 274 (`planted-0`) | `b3ab1cf841fd53a1491a759487767deef9e1c3439f75583af50abf2895ec0cbb` |

The rendered strings and token IDs happened to match across the two target vocabularies. The raw output records every rendered prompt and token ID, so these are countable observations. This is a **metadata preflight**, not the final `prompt_tokens_required` value: the accepted CPU/GPU measurement server must reproduce the rendered bytes, token IDs, salt equality, and maximum through its actual `/apply-template` and `/tokenize` endpoints before a keeper nonce or manifest freeze. Production rate evidence and HARD qualification remain absent.

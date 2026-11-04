            LLAMA_LOG_INFO("KPF30 row=%u seq=%d n_tokens=%u n_seqs=%u swa=%d causal=%d n_kv=%" PRId64 " blocks=%" PRIu64
                           " live=%" PRIu64 " mixed=%" PRIu64 " unknown=%" PRIu64
                           " live_unknown=%" PRIu64 " invalid_mask=%" PRIu64 "\n",
                           i, int(seq_id), n_tokens, ubatch->n_seqs_unq, int(swa_type), int(causal_attn),
                           n_kv, count.blocks, count.live, count.mixed,
                           count.unknown, count.live_unknown, count.invalid_mask);

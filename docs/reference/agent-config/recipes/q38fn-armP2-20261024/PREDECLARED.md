# PREDECLARED -- q38fn-armP2-ppl (written 2026-10-24 before any P2 number exists)
Operator choice (via ws-58): ARM P2. Arm P (gate/up_exps IQ3_S->IQ4_XS) had quality GO (PPL 2.9743 vs UD 2.9868) but failed the speed A/B at +8.5% size (pp256 +29.5%, pp5 -7.4%, tg128 -17.0%). P2 adds Q8_0 -> Q6_K on the dense tensors to win back decode bytes.
## What changes (dry-run asserted by job.sh step 1: 346 tensors, nothing else)
| class | n | UD type | P2 type | note |
|---|---|---|---|---|
| ffn_gate_exps / ffn_up_exps | 47+47 | iq3_s | iq4_xs | (the other 2 are already iq4_xs) |
| attn_gate | 36 | q8_0 | q6_K | ncols 2560 |
| attn_qkv | 36 | q8_0 | q6_K | 2560 |
| attn_k / attn_q / attn_v | 12 each | q8_0 | q6_K | 2560 |
| attn_output | 12 | q8_0 | q6_K | 6144 |
| ssm_out | 36 | q8_0 | q6_K | 6144 (the only Q8_0 ssm_* weight; others are f32/other) |
| ffn_gate_shexp / ffn_up_shexp | 48 each | q8_0 | q6_K | 2560 |
FALLBACK (ncols % 256 != 0, Q6_K impossible; kept Q8_0, which is llama.cpp's own fallback): ffn_down_shexp x48 (ncols 640). Unchanged at UD type: ffn_down_exps (iq4_nl x43 / q8_0 x5, ncols 640), hc_*, ple_*, token_embd (q8_0), per_layer_token_embd (iq4_nl), output (q6_K), norms/f32, indexer, ffn_gate_inp*.
Expected size (dry-run): 96315.75 MiB (4.57 BPW) = UD 89332.16 MiB + 6983.6 MiB (+7.8%); arm P was 96969.66 MiB. The UD-size target is NOT reachable on this type menu (the Q8_0 dense tensors in the named classes total only ~654 MiB of savings); the file will not be <= UD.
## Protocol: identical to the v2 arm-P job (AMENDMENT 1 of ../ws58-q38fn-armP-20261024/PREDECLARED.md): recipe serving env for every step, wiki.test.raw -c 512 -b 512 --chunks 40 -t 24, P2 and UD in the same job, coherence via llama-server chat completions (think off, temp 0), UD control first (INVALID-CONTROL if UD fails).
## GO (both required): PPL(P2) <= 3.10 (same bar as arm P; UD re-run reported as paired baseline) AND the AMENDMENT 1 coherence bar. GO licenses only the speed job q38fn-armP2-speed (pp256 >= +27%, pp5 >= +19%, tg128 >= -2.0% paired median); never promotion. A P2 PPL more than ~0.05 above arm P is reported as a warning only.

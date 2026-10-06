# No-spec divergence check (--spec-type none, production binary)

Generated 2026-10-06 07:50:36. Server: production CPU binary, canonical :8070 argv with `--spec-type none` (n_rs_seq=0 regime), same request body as phase1.py (greedy, max_tokens 512) plus n_probs 2 / top_logprobs 2.
Compared byte-for-byte against P (draft-mtp) and NO (ngram-mod only, n_rs_seq=0) outputs from copy-spec-eval results. Caveat: requesting logprobs could itself change numerics; a mismatch vs both is therefore not conclusive alone.

| idx | id | ok | == P | == NO | first diff vs P (char) | first diff vs NO (char) |
|---|---|---|---|---|---|---|
| 6 | debugbench_erect-the-fence_java | True | NO | yes | 262 | None |
| 22 | hotpot_bridge_5ae61e7555429929b0807adf | True | NO | yes | 67 | None |
| 27 | hotpot_comparison_5abfd3d65542994516f4550b | True | NO | yes | 32 | None |

## Near-tie evidence (our token at the first divergence)
- idx 6 vs P: first diff at char 262, token ',', top-2 logprob gap 0.0225, top2 [(',', -0.7491), ('-coordinate', -0.7716)]
- idx 22 vs P: first diff at char 67, token ',', top-2 logprob gap 0.1097, top2 [(',', -0.6591), (':', -0.7687)]
- idx 27 vs P: first diff at char 32, token ' "', top-2 logprob gap 0.2268, top2 [(' "', -0.5876), (' opera', -0.8144)]

## Reading
- all 3 equal NO: True; all 3 equal P: False.
- equal NO and not P => divergence is the n_rs_seq=0 single-row numeric regime (not spec rejection/restore). equal P => the earlier NO divergence was ngram-mod/restore specific. Small top-2 gap (<~0.1 nats) at the divergence => fp near-tie flip.

# Jet-Long small-model recall (Qwen3-0.6B-Q8_0, native 32768, n_rot 128; no arch change, tip f06123436)
6 needles in ONE question at depths 0.10/0.25/0.40/0.55/0.70/0.90, -np 1, -t 24, taskset 24-47, one prefill per arm/length. Y = static YaRN (factor L/native), X = plain RoPE, J = --jetlong-window 2048 --jetlong-native 32768. N = production store binary. J/Y/X use the jetlong-proto binary (J flag off = stock).
| arm | 30k (1x) | 65k (2x) | 130k (4x) |
|---|---|---|---|
| N | 6/6 | - | - |
| J | 6/6 | 6/6 | NOT RUN |
| Y | - | 5/6 (miss depth .55) | 3/6 (hits only .40,.55,.70) |
| X | - | 5/6 (miss depth .10) | 0/6 (collapse) |
J 30k used -ub 32, J 65k -ub 512 (both PASS-clean). tok/s (informational): prefill N 197, J 73 (30k, ub32) / 26 (65k, ub512), Y 89/43, X 88/33; decode J 0.4 at 65k (non-fused), Y 7.8 at 65k.
J 130k not run: an ub-512 attempt had reached only 48k tokens in 1100 s at ~13 tok/s and falling (>3 h projected), killed to yield the host.
Verdict: J matches N at <= native (6/6 both, identical prompt_n 28914). J >= Y at 2x (6/6 vs 5/6, a 1-needle difference, within noise for one prompt). 4x J-vs-Y undecided. Y degrades at 4x (3/6) and plain RoPE collapses (0/6), so the test discriminates.

# Jet-Long small-model recall (PARTIAL, yielded to workspace-89 at 16:35Z)
Model Qwen_Qwen3-0.6B-Q8_0 (qwen3, native 32768, n_rot 128). No arch change needed: Jet-Long hooks generic KV-cache build_attn; qwen3 is NeoX, side cache 14.8 GiB at ctx 135168. Branch tip f06123436 unchanged.
6 needles at depths 0.10/0.25/0.40/0.55/0.70/0.90 in one question; -np 1, -t 24, taskset 24-47.
| arm | len | recall 6 needles | prefill tok/s | decode tok/s |
|---|---|---|---|---|
| N (prod binary) | 30k | 6/6 | 197 | 18.9 |
| J (w0 2048) | 30k | 6/6 | 73 (-ub 32) | 20.8 |
J 65k: killed at ~84% prefill (54.7k/65k, ~19 tok/s avg, decaying). Y/X 65k, all 130k: NOT RUN.
Verdict so far: J matches N at <= native (6/6 both, same prompt_n 28914). Above-native J vs Y undecided.

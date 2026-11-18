# 2026-11-18 autopilot-backlog-session

## CODEMODE-AB probe results (35B + 27B)

- 35B-A3B (stop-on-answer n50, descriptive interim): code mode loses to direct calls (success 0.10 vs 0.43, p=1.2e-4) at ~20x fewer tokens; per-request top-8 tool selection beats static list+list_tools (0.38 vs 0.10, both C1 embed and C2 Jev oneshot); C1 ~ C2 (C2 recall 0.65 vs 0.45).
- 27B (complete, 264 eps): code mode 0.03 vs direct 0.30 (p=4e-5); selector arms floor-bound, inconclusive.
- Verdicts: /mnt/raid0/llm/tmp/codemode-ab-20261117/out/{35b,27b}/verdict.json (score.py 2c8490e3).

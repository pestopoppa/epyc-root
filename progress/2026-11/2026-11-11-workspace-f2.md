# 2026-11-11 workspace-f2: agent-file compression with tools (v3b/v3c), tool-permission trace, INF-85 W3 lineup rows

## Problem
Suite v3 tool-condition verdicts for Qwen3.6-35B and Flash-Next were PROVISIONAL: the forced final turn still offered `tools`, so models emitted tool-call markup scored as FAIL. The v3 tool lists also came from the legacy executor table rather than production enforcement.

## Findings
- **v3b harness fix** (forced turn sent without tools, +1 retry, persistent markup excluded from both arms): Q36 none-level compliance 0.233 → 0.493. Q36 mild/medium/aggressive all KEEP; operating point aggressive.
- **Disk-pause guard bug**: a zero-growth row was SIGSTOPped and never resumed (Q36 rows lost ~2h40m). Reported to Pipeline, fixed in `bf32c44db`. Pipeline also landed drain cap-backfill (`407666d71`) and same-id requeue (`eea000786`).
- **Web-tools analysis** (`/mnt/raid0/llm/tmp/afc-q36-webtools-analysis-20261111.md`): do not trim worker_general web tools. Tasks calling a web tool passed 58.7% vs 34.5% without. Residual fails are mostly context-asking (35/76) and uncited refusals (15/76): agent-file levers, filed as AFC-Q36-AGENTFILE-CTX-REFUSAL.
- **Tool-permission trace**: production enforces `model_registry.yaml` `tool_permissions`; `executor.py` ROLE_PERMISSIONS is legacy. 13/15 roles had no `tool_permissions` and fail open to all 65 tools. The operator signed deny-default with explicit allowlists (architects 35 tools, `http_post` forbidden). The package is parked behind the contention-matrix refresh (relaunch queue item 1).
- **Harness on main**: `94717ca31`, `8363a8fff` (`gen_role_tools.py`, production tool sets).
- **v3c (production tools)**: Q36 aggressive confirmed on 26 production tools (none 0.500/0.600/0.947). Q38 half in flight: aggressive ended (0.820/0.627/0.900, 0 blanks), unfiled until the none row runs; medium ~366/450, mild ~117/450 at 20:42Z.
- **INF-85 W3 r3 lineup rows** (P-BENCH-1, n=10, v10 build 10303, tg128 depth 0, single stream, 96t, no MTP; bench-class caveat, not serving): Qwen3.6-35B-A3B Q8 57.01±0.64 tok/s (hh-92c4b2f171e7); Qwen3.8-Flash IQ4_XS 25.59±0.16 (hh-b758c7787cc5); Qwen3-VL-30B-A3B Q4_K_M 84.42±1.30. All filed PASS; INF-85 ownership moved to AutoKernel.
- The context-depth curve is deferred to after the v11 promotion (operator): LINEUP-CTX-DEPTH-CURVE.

## Handoffs
| Handoff | Change |
|---|---|
| `handoffs/active/engineering-hygiene-backlog.md` | Ticked AFC-V3B-HARNESS-RERUN (Q38 moved to v3c), AFC-Q36-TOOLS-COMPLIANCE (answered: no trim, agent-file lever), WG-TOOLPERM-DRIFT (traced; remainder moved to TOOLPERM-DENY-DEFAULT). Notes on the Flash/Q36 V3 boxes and the AFC-V3C-PROD-TOOLS Q38 status. New box AFC-Q36-AGENTFILE-CTX-REFUSAL. |
| `handoffs/active/publication-upstream-program.md` | W3 r3 results and the ownership move recorded. |

## Open
AFC-V3C-PROD-TOOLS (Q38 half), TOOLPERM-DENY-DEFAULT (parked behind the matrix refresh), LINEUP-CTX-DEPTH-CURVE (after v11), AFC-Q36-AGENTFILE-CTX-REFUSAL.

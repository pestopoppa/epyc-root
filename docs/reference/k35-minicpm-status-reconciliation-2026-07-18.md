# K35 / MiniCPM-o Status Reconciliation - 2026-07-18

## Verdict

**Evidence inconsistent.**

The strongest reconciliation is:

- **Source/config flip landed** in `epyc-orchestrator` as commit `4ab4e0ee`.
- **A controlled one-role stack-launch smoke landed** for `vision_escalation` on port `8087`, using MiniCPM-o on the experimental v7 HIP binary, and it passed the four fixed K35 OCR/chart fixtures.
- **A persistent live production-stack flip is not proven by the available documents/artifacts**: the smoke stopped its own server PID afterward, did not restart AutoPilot or the orchestrator API, and the root/research status documents still disagree about whether the live lane is flipped or pending.

So do not state unqualified "MiniCPM-o is live in production" from this evidence. The precise status is: **MiniCPM-o is approved and source-wired for `vision_escalation`; controlled stack-launch smoke passed; durable live traffic state is not consistently documented.**

## Conflicting Status Statements

### Pending / Not Yet Flipped

- `research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md` says the 2026-07-18 K35.13 decision approves MiniCPM-o as the next `vision_escalation` lane, but "the live stack still requires a controlled registry/reload patch before traffic moves."
- The same report says "MiniCPM-o ... has not yet been flipped into the live stack" and later says the live stack still uses the Qwen2.5-VL artifact/projector until the controlled MiniCPM-o registry/reload patch lands.
- `progress/2026-07/2026-07-18.md` initially records the policy checkpoint as docs/registry only: "the live orchestrator stack registry was not changed and AutoPilot was not restarted."
- `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` still has MiniCPM-o `benchmark_status: k35_vision_activation_policy_approved_live_flip_pending` and lists the production-stack constraint as a controlled live-stack flip plus rollback verification.

### Landed / Verified

- `progress/2026-07/2026-07-18.md` later records `K35.13d MiniCPM-o Vision-Escalation Source Flip`: orchestrator commit `4ab4e0ee` changes `vision_escalation` on port `8087` to MiniCPM-o Q4 plus vision F16 projector, with `--reasoning off` and `--device ROCm0`. This entry explicitly says no live stack reload, live traffic smoke, or AutoPilot restart was run.
- `progress/2026-07/2026-07-18.md` then records `K35.13f MiniCPM-o Live Vision-Escalation Smoke`: only `vision_escalation` was launched through the stack launcher, using the experimental v7 HIP binary and matching `LD_LIBRARY_PATH`; the fixed fixture smoke passed `4/4`; PID `2813245` was stopped afterward; AutoPilot and the orchestrator API were not restarted.
- `handoffs/active/inference-acceleration-index.md` says A1 K35 finalize is closed and includes "K35.13d source/config flip" plus "K35.13f controlled live smoke."
- `handoffs/active/gemma-challenge-kernel-techniques-v7.md` marks both `K35.13d` and `K35.13f` checked off, but the `K35.13f` wording is narrower than a full-stack production cutover: "launched only `vision_escalation` through the stack launcher."
- `docs/reference/model-probe-scoreboard.md` says MiniCPM-o is "activated `vision_escalation` (live smoke 4/4)", which appears to compress source wiring plus controlled smoke into an activation claim.

## Artifact Evidence

Primary live-smoke artifact:

- `/mnt/raid0/llm/tmp/k35-vision-escalation-live-smoke-20260718T1225Z/summary.json`

Observed from that artifact:

- `role`: `vision_escalation`
- `port`: `8087`
- `binary`: `/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin/llama-server`
- `model`: `MiniCPM-o-4_5-Q4_K_M`
- pass rate: `4/4`
- fixture outputs: `7500`, `43.36`, `Tanzania`, `CS00012465`
- decode range: `115.22-127.35 t/s`
- prompt range: `731.92-884.41 t/s`

Pre-flip / policy evidence:

- `/mnt/raid0/llm/tmp/k35-minicpm-o45-reasoning-off-20260717T1911Z/summary.json`
- `/mnt/raid0/llm/tmp/k35-minicpm-frontdoor-coresidency-20260717T191849Z/`
- `/mnt/raid0/llm/tmp/k35-minicpm-frontdoor-service-tax-20260717T192427Z/`
- `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/summary.json`

Additional corroborating rows, not required for the live-stack verdict:

- `/mnt/raid0/llm/epyc-inference-research/data/k35_stack_context_matrix/k35_vision_minicpm_mi210_20260718T155711Z/summary.json`
- `/mnt/raid0/llm/epyc-inference-research/data/k35_stack_context_matrix/k35_vision_mi210_minicpm_o45_full_20260718T213231Z`

Current registry/source references checked:

- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml` has `roles.vision_escalation` on port `8087` pointing at:
  - `/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q4_K_M.gguf`
  - `/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/vision/MiniCPM-o-4_5-vision-F16.gguf`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py` contains the MiniCPM-o model/projector constants, but also has a stale comment near the port map saying `vision_escalation` is a temporary Qwen2.5-VL alias.
- `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` records MiniCPM-o as policy-approved but `live_flip_pending`.

## Reconciled Status

Use this wording until a separate no-inference live-state audit or operator reload record proves otherwise:

> K35.13 approved MiniCPM-o as the next MI210 `vision_escalation` lane. The orchestrator source/config flip landed as `4ab4e0ee`, and a controlled single-role stack-launch smoke on port `8087` passed `4/4` fixtures using the experimental v7 HIP server. However, the available evidence does not prove a persistent full production-stack traffic flip: the smoke stopped its PID, AutoPilot and the orchestrator API were not restarted, and root/research documents still disagree. Treat the current durable status as source-wired plus smoke-verified, with live traffic state requiring explicit confirmation.

## Follow-Up That Does Not Require Inference

- Audit current process state and launch argv for port `8087` if the operator wants to know what is running now.
- Reconcile stale documentation separately: K35 report, inference index, model-probe scoreboard, stack-manifest comment, and research registry should distinguish `source_wired`, `controlled_smoke_passed`, and `persistent_live_traffic_confirmed`.
- Do not edit master index or handoff checkboxes as part of this reconciliation memo.

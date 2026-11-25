# 2026-11-24/25 — autopilot-backlog-session

## Harness follow-ups (non-inference, all landed, default-off flags)

| Box | Orchestrator commit | Result |
|---|---|---|
| AEI-RERUN-ATTEST | 40ea1b98 | paired attestation carries rerun ref + rerun-flip; no-R refused |
| HF-THINK-CAPS-2 | 93048745 | thinking_budget_headroom clamps the 2048 escalation and 1024 stream caps |
| HF-TIMEOUT-GENEXC | 0a5565ce | generation-exception timeouts get contention_class |
| HF-DECORATOR-PARITY | d7ac6ea9 | pre-existing since 75e6d978; decorator baseline refreshed |
| RPK-SURFACE | 633602b5 | review_plane numeric surface; tool_registry/classifier_config corrected to read-once |
| RPK-READER | 4632ed77, 1c66fb62, 8a095405, 38eb0213 | six review knobs read; majority_k, evidence-round budget (force verdict after N), multiplier cap (bound 5.0) wired — operator chose semantics |
| RPK-NEAR-BAND | 9de4356f | review_near_band_width; midpoint 0.5 assumed (score is advisory) |

Orchestrator venv: dev extra installed (operator-approved), 17 packages added, none changed; freezes in /mnt/raid0/llm/tmp/orch-venv-freeze-{before,after}-20261124.txt.

## 27B served-recipe stack change (operator-signed, scope A)

- Evidence: research dbee2198 files ak-27b-served-np4-floor-gpu-20261124 (CALIBRATED; median decode 14.0 tok/s/slot, prefill 189.5 tok/s/req over 192 requests).
- Apply: research f956798de (master pointer), orchestrator faa783c7 (derived regen, 6 lean refs). Recipe-shape change only (ctx 393216, q8_0 unified KV, draft 7, batch 512); sampling unchanged (a97e27f15).
- Promotion gate skipped by pipeline on the two operator-accepted runtime_attestation errors (:8000, :9003); its pytest target ran by hand, 225 passed.
- Marker STACKCHG-27B-SERVED-RECIPE-20261124 at phase bring-up. Phase 8 serving proof pending stack bring-up. Package: /mnt/raid0/llm/tmp/stack-change-27b-served-20261124T200847Z/package/.
- Both classifier denials of subagent pushes were stopped and surfaced; the operator authorized and I pushed.

## Rowflow lessons ported (Pipeline Mgmt relay)

| Box | Orchestrator commit | Flag |
|---|---|---|
| HF-TOOL-PIN | f3585904 | tool_process_cpu_pin (84-87; overlap warns, operator chose warn-and-pin) |
| HF-CRASH-CLASS | d7f3e9fc | server_log_crash_class (candidate_crash = task_failed) |
| HF-DEPLOY-ANCESTRY | 6d943788 | deploy_ancestry_guard |
| HF-AP-WAKE | aecca193, 8142f68a | autopilot_alert_push (bus row validated on temp bus) |
| HF-PROGRESS-RETRY | 73efa200, e1de6dc5 | progress_aware_retry_cap (incomplete AND new qids only) |
| HF-GPU-DRAIN-INVERSION | — | no gap |

Side fixes: step_feedback_in_prompt split out of step_event_logging (prompt byte-identity; prod has step_event_logging off). HF-TEST-ORDER-DEP 12df8158 + a5690950 (session_log import-time pytest guard, registry timeout cache, three stale tests); wide run 1415 passed, 0 failed.

EV-DATE-PIN-1 20b75c14 (routed by workspace-f2): no served role reads the date.

## Pending (needs the production stack)

API reload for all flags above; 27B phase 8 serving proof then clear the marker; A/B the flags; AEI-AP-RERUN-ARM.

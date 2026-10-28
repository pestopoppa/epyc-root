# RUS3 r3 raw-capture audit

Read-only audit of the scheduled `rus3-repeated-samples-r3` result at `/mnt/raid0/llm/tmp/codex-ni-rus3-runprep-20261028/full-run-1793199433821519315/`. The producer report records a full raw capture: 40/40 samples for 10 questions × 4 repeats, no missing samples, server and sampler rc 0, 1,277.45 seconds, and GPU residency observed. The capture report marks `capture_complete=true` and `task_acceptance=complete_capture_full_trace`.

This is not a measurement warrant or scored decision result: `protocol_id` is empty, `owner_evidence_authenticated=false`, `capture_readiness=OBSERVED_UNATTESTED`, and `safe_cancel_or_drain=NOT_PROVEN`. The captured classification has 9 retained samples and 31 truncated, with zero refused or unscoreable. The completion marker carries null grant-receipt, preflight, and owner-start digests. No RUS source, READY manifest, or scheduler state was changed by this audit.

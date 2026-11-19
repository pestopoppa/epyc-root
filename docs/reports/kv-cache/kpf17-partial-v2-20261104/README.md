# KPF-17 partial-v2 original refusal

The original `kvfork17-partial-v2-20261102` grant ended rc64 at 2026-11-02T22:19:46Z before the job started. `poller.out` records the region-lock preflight refusal: live orchestrator dispatch PID 459747 did not have `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` enabled, so exclusion against the wrapper global locks would be one-sided. This is neither a source-worktree failure nor a test result. Do not bypass the preflight with `--no-preflight`; a runtime owner must coordinate the live process before an otherwise necessary run.

No fresh row is prepared for this superseded diagnostic. It targets old `a1f0c8cf9` plus a fixed-1e-3 test without mutation proof. The current handoff already closes `KPF-17-PARTIAL-CPU`: integrated candidate `8952a0f69`, Qwen3.5-0.8B Q8, `n_rs_seq=0/8`, exact A/A floor 0, and detected stale-state mutation (`artifacts/compute/rtg58-p1-cpu-20261102/RESULT.json`). Repeating the weaker old row would not advance an open clause. The other KPF-17 conformance clauses remain separate.

This packet preserves refusal and published-row identity only; it carries no pass, defect, performance, or completeness claim.

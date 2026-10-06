# Intake re-verification checkpoint — 2026-10-06 07:16 UTC

This is a preparation/result checkpoint for the owning wrap-up, not a filing or canonical mutation. The 22 primary-source re-dives and independent reviews are complete (10/10/2); the separate 8-row demotion review is preparation only. No correction/demotion has been applied to the canonical ledger or intake index.

Root-owned validation session `48536` completed at 07:16:12Z. The portable 28-case suite passed (exit 0; 28 tests in 0.033 s). The combined full refresh failed before append (exit 1): its pre-append unrelated-effective-target assertion found 13 IDs: `clm_intake_1093_00`–`05`, `clm_intake_1094_00`–`05`, and `clm_intake_1245_00`. The failure is preserved; it is not a successful native correction/demotion receipt. Three rehearsals have matching exact frames/folds and immutable prefixes; they share fixtures/receipt paths, so independent replications = 0.

The canonical-baseline cite-check exited 3; its receipt is retained and the result remains under investigation. This blocks any claim that the final cite gate passed.

The reviewed 17-source selection list remains outside the currently authorized 22+8 round. It contains 6 same-work companions, 10 distinct sources/artifacts, and 1 journal edition. Mercury_Eval had a provisional relevant read; discovery fetches are distinct from a selected full dive. Source fingerprints are recorded as known or unknown without imputing them. No source is dismissed as inapplicable; operator source selection remains a distinct decision.

Compact durable evidence bundle: `/mnt/raid0/llm/tmp/intake-reverify/compact-durable-bundle/`, manifest SHA-256 `8cf5f89cdc09697d91051362528df39d9ae25a7a1af6a6bacc5c7eac2f5c0d08`. It contains accepted preparation receipts and exact draft patches; the prior raw scratch bundle is preserved separately with its checksums. The strict manifest adjacent to this checkpoint names only the files needed to inspect these results and excludes duplicate legacy diagnostics.

No canonical ledger, intake index, handoff/index row, or wiki write was made. Main owns full wrap-up, review of the failed refresh/cite-gate outcomes, and any filing.

## Main-owned wrap-up command note

- README freshness check: `python3 .claude/skills/project-wiki/scripts/check_readme_freshness.py` (run from `/workspace`).
- Wiki source scan: `/workspace/repos/epyc-orchestrator/.venv/bin/python .claude/skills/project-wiki/scripts/compile_sources.py`; only if main reviews and compiles the full delta, advance with `--touch` under the wrap-up lease. This preparation did not run either command or alter wiki files.

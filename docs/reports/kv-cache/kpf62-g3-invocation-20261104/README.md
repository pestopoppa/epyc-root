KPF-62-G3-OUTCOME-CONTINUATION invocation check

Lane inspected: /mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency
Patch inspected: scripts/coordination/kvfork/kpf62_outcome_continuation/joint-source.patch
Existing test used: scripts/coordination/kvfork/kpf62_outcome_continuation/test_cli_launch.py

No lane source files were changed; the lane already contains the minimal scoring-CLI integration test. It runs the candidate's captured G3 source-integrity check, then launches the actual g3_gate.py `main()` entry path in a subprocess with reduced statistical cohort constants for a four-request synthetic fixture. The valid paired full/reuse fixture must exit 0, write result.json with retention 1, and include the outcome-segment ledger SHA-256. Separate interrupted (missing final ledger record) and exhausted (`finish_reason=length`) fixtures must exit 3 with REFUSED and produce no result.json. This exercises the patched segment guard before paired scoring; it uses synthetic rows and does not invoke a model or launch a successor.

Command:
KPF62_BUILD_ROOT=/mnt/raid0/llm/tmp/kvfork/kpf62-g3-build-20261104 python3 -m pytest -q scripts/coordination/kvfork/kpf62_outcome_continuation/test_cli_launch.py

Result: exit 0; 1 passed in 0.16s.

GitNexus: `gitnexus status` reported this lane repository is not indexed. `scripts/gitnexus-analyze.sh` refused with exit 64 (cross-role global region locks not enabled; CPU admission refused). `gitnexus impact paired_retention --direction upstream` reported multiple indexed repositories and did not provide a source-bound lane impact. No symbol edits were made. The review was read-only and the existing test was run.

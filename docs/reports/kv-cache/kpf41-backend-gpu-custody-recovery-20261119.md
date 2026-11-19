# KPF-41 backend qualification source recovery

The replayed `kpf41-gpu-parity-r4-20261105` event already has a PASS filing and FILED receipt dated 2026-11-05; its completed D64 box is unchanged. Existing result SHA-256: `9bb04aaf807439ea59dd15014961ab23fae81161d545b1cbbd2773f5f7862ba9`.

The retained keeper journal `/mnt/raid0/llm/tmp/compute-flags/ws58-calendar-keeper.log` records `REAP-FREED-INPUT kpf41-backend-tests-build-20261105[declared]/source` at 2026-11-05T03:30:25Z, followed by the first qualification launch refusal at 03:30:52Z. This explains the now-missing source precondition. The park notice `/mnt/raid0/llm/tmp/compute-flags/operator-escalations/kpf41-backend-gpu-qualification-20261105.arming.md` identifies 137 **launch** failures and explicitly permits fixing and republishing. Those are not 137 publisher or corpus qualifications. The old STOP remains untouched; its individual writer is not identified by the empty file.

Same-lineage successor `kpf41-backend-gpu-qualification-r2-20261119` uses a detached worktree of experimental commit `15caecbbf4cb27452dbd87fa1a68a0e75098388e` under its own scratch root. It preserves the existing five artifact digests and decision rule. It changes source lookup to its own `source/` and passes FILLER_ID to all child environments. No kernel code was edited, no build was run, and no binary was copied. Native GitNexus impact was unavailable (lane unindexed); this repair changes only the scratch harness source location and child environment, not kernel functions.

The post-repair read-only custody check returned zero with all five build hashes, detached clean source and loader checks intact. The publisher was run with `verdict_by=agent`; its final response was **GPU busy: smoke queued**. No smoke PASS, full corpus result or new completion is claimed. Await publisher PASS or FAIL before further action; do not republish simply to inspect readiness.

Scratch packet: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r2-20261119/`.

SHA-256 seals:

- `job.py`: `1f93091859e5a1b7a5d89bce19b9e1d51a76956f2253622619ae409085785479`
- `complete.py`: `23d3e3fb8bbf7bd15ee7e6bb8bc026aefb4e43b67b60afef018cb3ffac8e8d70`
- `runtime.sha256`: `61572abf6d5bc13511db5c8b14711b9f98f56aa88dd898dc06fcf5811d4cd6ac`
- `launch.sh`: `113eabc430477071175f5d720c84357129f835748c21003e971ecf830db83603`
- `spec.json`: `a59ea57982d9b722c499748018fd97b08d97e447cb6cb99d30680dcf1e5ccb5b`

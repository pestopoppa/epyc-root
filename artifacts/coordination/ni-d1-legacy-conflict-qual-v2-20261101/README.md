1. Source base: `origin/main` at `18a11bea078e01d99819339ecd3f29bb2d577b27`; keeper source SHA-256 `0588749a447dc15e46014aa4ee883ec46d15afcb0ffc26a9c3ece5c4efd6c8ca`.
2. Apply `keeper-v2.patch` to root `scripts/coordination/keeper_qual_gate.py`; main commits and pushes source and this packet.
3. Reviewed package SHA-256: `c708ee9cf0722c2fac6c171de72306af03b95cc59e86b3ad504f3a2bf2d512e4`.
4. ws58 dry-run: `python3 install_for_ws58.py`; compare `install-dryrun.json` before the owner boundary.
5. ws58 install: `WS58_OWNER_BOUNDARY=1 WS58_REVIEWED_PACKAGE_SHA256=c708ee9cf0722c2fac6c171de72306af03b95cc59e86b3ad504f3a2bf2d512e4 python3 install_for_ws58.py --apply`.
6. ws58 alone restarts its captured keeper PID at its boundary; grant guard and keeper then use qual-v2 controller.
7. Installer creates only qual-v2 controller plus `qualify_launcher.py` symlink to immutable qual-v1; qualifier CLI, engine and single allowlist remain v1.
8. Root-owned YaRN descendants may make `/proc/.../fd` incomplete; ws58 can use `write_sidecar_for_ws58.py` with explicit authoritative ports/shared/exclusive declarations when relevant.
9. Nemo q3 read-only conflict reproduction and three live grant windows are in `nemo-q3-readonly-repro.json` (`ok`).
10. Nemo signed snapshot: `/mnt/raid0/llm/tmp/refactor-nemo-reseg-20261031/successor-r4-20261101/r14/epyc.ready.v2.candidate.json`.
11. Its manifest digest equals receipt digest `763c8490ba7461ef3b59db7b1fac7997e5b19eb0e8272f6a8864fa3c7b897497`; ws58 restores that exact snapshot through its owner procedure.
12. Read-only structural check: `python3 -I /mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/qualify_launcher.py verify --manifest /mnt/raid0/llm/tmp/refactor-nemo-reseg-20261031/successor-r4-20261101/r14/epyc.ready.v2.candidate.json --flags /mnt/raid0/llm/tmp/compute-flags --no-fingerprint-now`.
13. Normal fingerprint verification must run in the actual keeper environment after restore; local shell verification returns `exec namespace changed`.
14. Host-scoped tests use immutable live v1 helper and local `/proc`; `final-new-tests.log` records 14/14 and `final-existing-d1-tests.log` records 29/29 against patched controller, both exit 0 and zero skips.
15. No grant, receipt, nonce, live flag or process was changed by preparation; ws58 owns installation and restart.

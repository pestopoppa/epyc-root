# LOOP-49 root components — candidate checkpoint

The forensic source is committed at `docs/reports/failed-run-audit-20261031.md`. The lane implementation contains qualification run/verify/fingerprint, one canonical engine, READY v2 schema, filer science outcomes, writer boundary integration contract, and 20 retained receipt regressions.

Operator bindings remain D1 hard gate, D2 science quota, D3 one canonical allowlisted engine, D4 READY-WAIT-DISK parked/un-counted. Qualification fixtures, nonce records and `.ended` files are retained and immutable.

Independent review found and the lane fixed these concrete gaps:
- Canonical engine resolves through keeper-configured `WS58_ROOT`, never the imported checker's adjacent directory.
- The pre-grant gate requires the actual writer row ID and concrete CPU/GPU region string.
- The pinned row's windows, booking class, RAM/process limit, output estimate, scratch root, region, and CPU claim must match the manifest before qualification.
- Disk floor checks use free space on the job's `scratch_root` filesystem.
- Dead-launcher identity now carries row ID, phase and grants directory; recovery validates all paths/identity and records stored phase.

Code/evidence commits: region-to-manifest binding `4554e1d0d`; review fixes and tests `9230c9cd4`. Validation on the lane: 19 focused unit cases passed across row binding, copy refusal, disk filesystem, region binding, `.ended` wrapper and recovery integrity; Python compilation, shell syntax, and `git diff --check` passed. CS8's updated LOOP49 manifest/row passed the current static checker (`caa492c8…`, row `8c09f38a…`) and synthetic `dryrun_check admit` (0,96 CPUs, 1200 s window, 900 s minimum); it remains unqualified until the keeper issues a grant.

The unpinned, live-mode-disabled v7f review candidate is at `/mnt/raid0/llm/tmp/loop49-keeper-v7f-candidate/v7f-r2/`. It includes immediate dead-launcher detection (ps state plus PID birth; writes `.ended` through the safe recovery gate), grant-boundary row/region validation, current lane gate/contract copies, and renewed `SHA256SUMS`. Candidate validation: 7/7 static tests, shell/Python syntax checks, and all SHA256 entries verify. No live writer or keeper was changed.

The report's 20 retained-receipt qualification cases are still gated on an externally issued CPU grant and retained artifact root; they were not run. No inference, production grant, arm, deployment, or science result is claimed. [no-belief: implementation checkpoint; no measurement result]

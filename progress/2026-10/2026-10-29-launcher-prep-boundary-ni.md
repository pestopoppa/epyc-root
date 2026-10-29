# Launcher preparation boundary — 2026-10-29

Timestamp: 2026-10-29 02:46 UTC. No index rows or scheduler artifacts changed.

## FA4 exact-set successor

Private packet: `/mnt/raid0/llm/tmp/codex-ni-fa4-exact-set-successor-20261029`.

The successor preserves the exact-set admission rule over 228 source-derived cases per arm, rejects missing, duplicate, or unexpected inputs, and retains every per-key outcome for comparison. It does not treat outcome differences as missing coverage. Normal admission still requires the registered grant and full-run budget. The diagnostic branch uses the actual exclusive GPU region lock and validates the live holder identity; it does not fabricate a grant. STOP/HOLD, disk-floor/reserve, bounded cutoff, partial-result, and owned-child cleanup paths remain fail-closed.

Model-free validation completed at 02:43:18Z on CPUs 126–127 under the 30–31 prep mutex: 23 targeted tests passed. `driver.py --dry-run`, shell syntax, source-pin checks, external-source/image-pin checks, and launcher dry-run also passed. These checks did not start a native/GPU process. At 02:43:16Z free disk was 160,199,016,448 bytes, below the 150 GiB floor plus 256 MiB smoke reserve (161,329,709,056 bytes); the packet therefore has no valid real GPU smoke and no READY. Latest packet validation details are in `MODEL-FREE-VALIDATION.md`; source manifest digests are recorded there and in the packet.

## INF-50 writer-race resume r5

Private packet: `/mnt/raid0/llm/tmp/codex-ni-inf50-writerrace-resume-r5-20261029`.

Attempt `smoke-r5-cache-witness-q0-20261029` exercised the real analyzer/cache path under `region-lock` role `build` on q0 CPUs 2–3 and completed in 118.112 seconds (109.189 seconds in the analyzer child). Functional checks passed on the pinned 600-file/one-chunk fixture: cold warmup followed by one cache hit, zero misses, and zero worker-pool creations; the writer, cache reader, Node bootstrap, package overlay, and result writer ran. However, the recorded free space at smoke start was about 149.5 GiB, below the required 150 GiB floor. Therefore this run is **floor-invalid and does not qualify as a passing smoke**, despite its functional result. Its output also says `normal_grant_path_exercised:false`; it does not establish the normal registered-grant run or replace full 3,072-path coverage and the five-symbol native audit.

Other preserved attempts include q3 smoke entries ending rc75 and rc1; they are not passes. The outer logs are under `smoke-runs/outer-logs/`. The successful q0 result and scope are in `smoke-runs/smoke-r5-cache-witness-q0-20261029/{RESULT.json,SMOKE-RESULT.json}`. No full normal-grant result is reported here. Do not describe the bounded fixture smoke as completion of INF-50's full run.

## State and limits

FA4 remains staged pending disk floor and a clean, authorized real GPU smoke. INF-50 r5 has functional bounded cache-witness output, but that smoke is floor-invalid; full normal-grant 3,072-path execution and a qualifying smoke remain unestablished. This checkpoint records preparation only; it does not publish READY, change index rows, or create a measurement claim.

## UFH12 r4 scoped checkpoint

**State:** private r4 launcher/source packet only; no full migration result and no qualifying smoke bound to the current bytes. READY row remains staged at `/mnt/raid0/llm/tmp/compute-flags/ready/UFH12-REQUESTB-FULL-PRIVATE-APPLY-r4-20261029.row.md`; it must not be treated as current because its source pins are stale. No index or scheduler files were changed.

**Implementation and checks:** r4 adds the normal grant/affinity gate, attempt validation, private copy/archive checks, STOP/deadline handling, and a prep supervisor. The last recorded suite is `post-smoke-validation.log`: 10 tests passed at 2026-10-29 02:03:48Z (4 normal-gate, 5 archive-contract, 1 active STOP/direct-child cleanup test). No post-helper 18-test log was found in the packet. The source-manifest check log is older (01:58Z), and source files were subsequently edited through 02:24Z, so these checks do not validate the final source bytes.

**Preserved smoke:** `smoke/20261029T015931Z-555927/SMOKE.json` records `SMOKE_PASS`, 880 persisted requests, 60.003s real inference / 62.868s wall, first request and writer successful, and direct server-child cleanup. Descendants were not censused. The smoke ran via `launch.sh --smoke` under the recorded q0 build lock / CPUs 10–11. Its captured pre-smoke hashes were launcher `e2dd1201…`, job `d6b041f8…`, manifest `29ea3bd0…`. Current hashes are launcher `aadb2788…`, job `e5ae7465…`, manifest `0f36578e…`; launcher/job/manifest mtimes are 02:12, 02:14, and 02:24, after the 01:59 smoke. Thus the smoke is valid historical evidence for its captured version, not for current r4.

**Disk/admission:** latest `/mnt/raid0` free space was 160,185,110,528 bytes (149.25 GiB). The required 150 GiB floor plus 4 GiB reserve is 165,356,240,896 bytes; current free space is short by 5,171,130,368 bytes (~4.82 GiB). Do not launch the next smoke until fresh checks show sufficient headroom and a safe lock/grant window.

**Next:** preserve the current artifacts and earlier private model copy. Once headroom and lock/grant checks permit, validate the final manifest/source set, rerun the regression suite against those exact bytes, then run the real same-launcher smoke and replace the staged metadata only after all pins and row checks match. The full apply/parity and descendant cleanup remain outside the evidence above.

**02:47Z exact-byte validation update:** UFH12 r4 subsequently passed 24 model-free tests with its current manifest and source hashes verified before and after the supervised run; log `/mnt/raid0/llm/tmp/codex-ni-ufh12-r4-final-byte-tests-20261029.log`, SHA-256 `4c45d50972d5417690ccbb7834f80515dd011f622d5842bc51d8284fdaf580cd`. The earlier statement that final-byte regression tests remained unverified is superseded by this run. FA4's current-byte 23-test model-free run and source/external checks were captured in `/mnt/raid0/llm/tmp/codex-ni-fa4-exact-set-successor-20261029/model-free-exact-run-20261029T024800Z.log`, SHA-256 `c85b2869ee8870fd2ff2c527dac2ce142ffe34f071f11347732efd3fbb837942`. Neither run included real inference or qualifies as the required smoke; UFH12 and FA4 remain unpublished pending resource headroom and real smokes.

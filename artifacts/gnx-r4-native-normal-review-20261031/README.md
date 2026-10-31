# GNX R4 required native-control collection — MAIN accepted, child scope only

The existing INF-50-GNX-R3-T1-REQUAL child is complete for new-ID requalification and required raw normal-control collection. This does not accept the private derivative as policy or close INF-50.

Actual run: `codex-ni-gnx-r2-nativeproof-r4-20261031`, official q2 CPUs48-71, terminal2026-10-31T01:57:22Z. All37 named cases match expected returns; raw placement/envelope artifacts and current captured-identity absence were independently checked. Controller `results/EXIT.txt` is rc0, with no `FAILED.flag`. Engine `.ended` remains rc1 `incomplete`: `launch.sh` supplies no `--complete-cmd`; pinned `filler_run13.sh`:181 returns1 when that check is empty and :329-330 rewrites successful job rc0. No rerun or terminal rewrite occurred.

## Exact original scope

Canonical source: `/mnt/raid0/llm/tmp/codex-ni-20261026-gnx-r2-nativeproof-job/recovery-r2-symlink-v1/packet/REVIEW.md`; SHA-256 `2d1c0d11af2b9284aade5406606d5eca1712525cab4f1eb9ad391976bad6ff0d`. Full original review is retained as `original-packet-REVIEW.md`.

- Lines43-48 enumerate required controls and explicitly call owner-only own-grant revocation **optional**.
- Lines56-60 require exact new owner configuration for that optional control and explicitly permit `NOT_RUN` without it.
- Lines63-67 define the final result as raw native evidence for MAIN/OWNER review, not acceptance/PASS, and explicitly exclude R4, impact coverage and ROOT enrollment.

Owner-revocation remains NOT_RUN. R4 and impact coverage remain NOT_RUN. The accepted parent manifest `b4c1414eccc2b8987d8f2b3eaa397f0b10438bd77d39487e7fd58c9ee7e30bbc` and every member remain unchanged. Current derivative `7abd5b65c6b2e5a69092e9fd31caf75f513a9479b7b7aa07918088f6c20fd4b0` has an R11 profile and canonical sleep recognition; old acceptance does not accept those new bytes.

## Evidence and limits

`raw-review.json` binds all37 raw placement/envelope pairs by SHA-256 and records runtime realpaths/inodes/digests. Original raw files remain under `/mnt/raid0/llm/tmp/codex-ni-gnx-r2-boundary-finish-20261031/results/`; terminal receipt `/mnt/raid0/llm/tmp/codex-ni-gnx-r2-boundary-finish-20261031/r4-terminal-watch.receipt` retains the engine rc1. `current-derivative.diff.b64` losslessly carries the exact fresh diff against the accepted parent (decode with `base64 -d`; decoded SHA-256 `ab6ec03fa577a826f21b0ff30df9cf86b2f25103ea1bf896758c7e745234b624`). Base64 preserves the native CapEff zero mask that the PII hook falsely classifies as an account number. Existing scratch `r3-query-supervisor.diff` is stale and remains historical; it omits the sleep change and differs at the R11 deadline check. The trace boundary still enforces deadline/lifetime.

Native `status.stdout` reports its private historical source index up-to-date at43c6303; no current-main freshness claim is made. Actual `_llm_call_impl` impact reports CRITICAL:26 impacted nodes, one direct caller `llm_call`, three processes and five modules. Dependent source/R4 work remains stopped. The observed stopped25th task is refused before user code; no kernel prevention guarantee. No production/kernel/store/shared-index changes.

Review was model-free on SMT128,129 under the32-33 prep mutex, with38.9MB peak RSS. Existing committed-conclusion capture `[belief: cc]` applies; no new grading ladder or measurement warrant.

Patch prepared against ROOT `c40a51be8968d1c05d1e24a8d25d10b634681057`; owning MAIN applies after lane release.

# 2026-11-02 — handoff kvu

## 00:00Z — Consume GPU engine provenance assessment

Consumed GPU replay engine-provenance assessment. Source review finds the stale manifest engine digest does not itself block the inspected qualification path; qualification records the then-live engine digest and PASS status checks the launcher digest. Do not infer the eventual execution engine from the stale manifest. Keeper qualification remains pending; no compute was run.

## 00:11Z — Recover failed serialized publication

The prior wrap-up reported serialized push failure after committing GPU provenance progress. Published the lane through serialized_push.py and verified origin/main contains the two lane commits; keeper qualification remains pending. No inference was run.

## 00:13Z — File original CPU-FA-VKQ3 row inconclusive

Filed codex3-cpu-fa-vkq3-mtp-20261031 inconclusive with rc=1 and no terminal paired result. Latest qualification refused a quarter-CPU grant before a new target request; an earlier interrupted HYBRID exposure is preserved and no-redraw remains binding. Preserved partial/exposure/drain and qualification launcher log before filing. The GPU replay dry-run failure has missing input and engine-pin causes under investigation. The previous recovery wrap-up encountered serialized-push failure and its unpublished commit is included in this wrap-up. No inference was run.

## 00:18Z — Preserve VKQ3 tokenizer draft repair and retry publication

Reviewed the uninstalled synthetic tokenizer supervisor draft repair: incomplete stdin and direct-child cleanup paths fail closed, and ten fake-child supervisor tests pass. This draft does not prove child consumption or descendant cleanup and is not row-ready. The earlier original-row filing passed index checks and committed, but publication met concurrent push-lock contention; this wrap retries publication of all lane commits. No model or inference was run.

## 00:19Z — Complete VKQ3 filing publication recovery

Recovered the filing and tokenizer draft publication using serialized_push.py after lock contention; origin/main verified to carry lane HEAD f94d90585f7f. GPU qualification repair remains delegated. No inference was run.

## 09:18Z — Publish KVU quarter partial result

Restored the quarter-run filing and native partial archive after the lane sparse-checkout and untracked-artifact guard prevented the prior wrap. Run ended rc=75 disk-floor with only the starting anchor complete and unified incomplete; comparison remains UNKNOWN. No inference was run.

## 09:21Z — Confirm KVU quarter filing publication

The previous wrap failed during push after committing. The dispatcher refreshed the lane, and origin/main already contains equivalent quarter filing and native archive in commit 444c53c50. The rc=75 incomplete target comparison remains UNKNOWN. GPU repair remains pending. No inference was launched.

## 09:26Z — Repair and republish GPU C5 replay qualification

Repaired and republished handoff-kvu-16i-c5-replay-20261101. Its failed dry run was pre-inference: historical receipt was unavailable inside the chroot and rowflow engine pin was stale. Restored the exact SHA-bound receipt under the job root, updated protocol and runtime paths, bound the installed tracked 329a1a03e engine (dry-run resource claim change), resealed source catalog and atomically replaced launcher last. Source catalog checks and all 48 historical request body hashes/order pass offline. Keeper qualification remains pending; no inference or promotion claim.

## 09:27Z — Record C5 GPU replay qualification

The GPU C5 row was republished after its missing historical receipt and stale engine pin were repaired; source and 48 request identities passed offline and keeper qualification is running. Lane refresh shows the durable repair in commit a44a037e2. Independent tokenizer, runner and CPU row preparation have been delegated. No inference was launched by this session.

## 09:32Z — Investigate C5 qualification failure and assess KVU inference readiness

Investigated C5 FAIL-2 (rc 75): producer refused MI210 because it tested WS58_REGIONS, which rowflow supplies as CPU-only; the qualification log separately shows the mi210_0 grant and GPU flock. A bounded repair and tests are in progress; completion event c5-region-repair-20261102 is registered for review before activation. KVU-15b requires 200 credited live :8083 calls in two eligible windows; the default serving log has 14 :8083 records and one credited call, insufficient, with other logs unverified. KVU-16h requires unfinished lifecycle and custody work. KVU-16a’s current 38.03 GiB value is derived at ubatch 512; the equal historical measurement used ubatch 2048, so it cannot establish current-shape provenance. No row was published or compute launched. GitNexus reports this lane unindexed; impact analysis unavailable. [no-belief: qualification log and bounded source review only]

## 09:36Z — Repair and republish C5 GPU replay after region admission failure

Repaired C5 FAIL-2 (rc 75): WS58_REGIONS is CPU-only, so the producer now parses exactly one regions field from the grant bytes it hashes and requires the exact mi210_0 token; FILLER_NEEDGPU remains mandatory. Five offline fixture tests passed, including missing/spoofed/duplicate region rejection, qualification cleanup and no target read. PIDs 847094 and 847095 from the failure report were absent. Resealed producer catalog and launcher and republished handoff-kvu-16i-c5-replay-20261101 for keeper qualification; no inference was launched. Two qualification failures exist; another may park the lineage. GitNexus is unindexed for this lane, so impact analysis was unavailable; the changed producer is confined to this row. [no-belief: source review and offline fixture tests only]

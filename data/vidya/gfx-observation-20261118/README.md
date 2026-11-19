# Prospective R18-E GFX observation packet

The implementation is `scripts/vidya/producers/gfx_observation/`; the registered
reader is `ak-gfx-observation`. Temporary deployment assets and the prepared
allocator row live at `/mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118`.
The row never rebuilds or modifies the production kernel.

The collector retains the original research commit
`26d89b6ea20f21675d9cc4bc07a8db11ec42199e` bytes. Its fixed native request uses
Qwen3.8-27B Q8_0 with its pinned Q8_0 DFlash2 drafter and the v10 store image.
Model and drafter hashes were prepared before publication, with identical
before/after stat witnesses. Grants only verify those witnesses; they do not hash
weights. The source manifest binds the collector, producer, strict reader,
linkage verifier and prepared identities. The reader-manifest binds the original
shared-reader snapshot used by the bounded planner canary.

The writer authors the measurement declaration before sealing the original
capture. Its numeric metric is capture completeness: two valid request-boundary
counter samples, higher better within this fixed two-boundary census. The raw
activity-weighted-seconds estimate and native/host clock brackets are retained.
They describe the boundary-read interval, which encloses the HTTP request;
they do not establish exact HTTP-only cost, per-process activity, binary busy
time, full-claim utilization, an optimization effect or promotion authority.
Valid zero activity remains zero. Missing/error/contradictory observations remain
UNKNOWN and cannot project as eligible measurements.

The installed reader independently reopens the original source closure, grant,
request/response, counter trace, ownership, mapped HIP identity and cleanup.
Resealing an unapproved producer or moving captured CPUs outside the original
grant does not restore eligibility. Exact weight digests scope the shared
AutoKernel planner context, including exclusion of a different digest under the
same filename. Official completion additionally requires the isolated native
planning-context canary; smoke and official captures are separate.

Six structural control groups passed, including installed registered ingestion,
source/clock/custody refusals, zero activity and scoped context. These fixtures
supply software evidence only. Native smoke and official observation acceptance
are separate and must be filed from their original publisher/allocator receipts.

The committed source closure is [source-manifest.json](../../../scripts/vidya/producers/gfx_observation/source-manifest.json)
(SHA-256 `ee22008823dfa16280e607c353ec7ddb7ece205350f064d02337fecc333aecb0`); it is referenced here without a duplicate evidence blob.

The first native publisher attempt completed the fixed 32-token request and
reaped its child, but remained UNKNOWN because the KFD sysfs entry had not yet
disappeared at the immediate cleanup check. The [original failure](qualification-failures/FAIL-1.json)
and [sealed UNKNOWN capture](qualification-failures/observation-1.json) remain
separate from any later capture. The writer now allows up to three seconds for
that captured child's KFD entry to disappear, bounded by STOP and the original
allocator deadline. Persistent entries still fail strict cleanup validation.
The reader, carrier and grading rules are unchanged.

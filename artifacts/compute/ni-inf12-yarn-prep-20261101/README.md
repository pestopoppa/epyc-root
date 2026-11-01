# INF12 / YARN r1 audit and r2 preparation

This is a durable evidence packet for audit/preparation only. It does not report a
Gate 2 verdict, YARN scientific result, current INF12 outcome, qualification, or
READY state. MAIN accepted the private r2 packet as preparation and audit only.

## Contents

- `raw/inf12-r13-210259/`: immutable attempt-local state, gzip-preserved raw log, and GPU samples and the
  archived terminal/rearm receipt for run `20261031T210259Z-128495`.
- `raw/inf12-r13-003829/`: corresponding files (raw log gzip-compressed byte-preservingly) for separate run
  `20261101T003829Z-2260396`. Shared JSONL output is intentionally not copied or
  attributed to either attempt; a line count is not a completed official item
  denominator.
- `raw/yarn-r1/`: r1 armed manifest, launcher/admission logs, filing and smoke
  receipts. The terminal is an admission refusal; no science ran. Three refusal streams
  are deterministic gzip archives; evidence records both source SHA-256 and compressed
  SHA-256, and decompression reproduces the original bytes.
- `metadata/`: bounded CPU tokenizer receipt/script/log and the planned prompt
  count metadata. No rendered 500k prompt text is stored here.
- `src/`: the private r2 candidate and behavioral tests. The canonical engine
  binding is still absent; the referenced v14 engine is an external scratch
  candidate and is not copied or represented as deployed.
- `src/SOURCE.sha256`: pinned source dependency listing, including references
  and hashes for external binaries/DSOs and tokenized rendered inputs; it is a
  text manifest, not a bundle of those payloads.
- `qualification/`: request/recipe/fixture pins and an explicit missing
  calibration record. No `READY` is published.
- `MAIN-APPLY-DRAFTS.md`: exact handoff/progress text for owning MAIN to apply.

## Validation

The model-free suite contains 8 behavioral tests. It exercises empty and
cross-recipe event rejection; wrong prompt/hash/KV/context and recipe refusal;
manifest-bound owner-booking/window validation; and science-cell immutability.
Python compilation, `bash -n`, and all 52 dependency hashes passed. No native GPU
qualification or science cell was run.

## Remaining authority and evidence

Canonical v14 deployment, a READY-manifest-bound owner booking, keeper-issued
qualification, and same-recipe paired E1/W A1-high work-unit timing remain
missing. The historical v10 estimate of 17,127.348 seconds for three pairs is a
planning floor before current-image loads, probes, analysis and cleanup; it is
not a current rate or fit claim. Do not publish READY or infer science outcomes
from this packet.

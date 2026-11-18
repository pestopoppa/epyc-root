# Promotion lifecycle diagnostic evidence

V9-8's CPU runner can bind a resident capture and its identical fresh replay to
prepared inputs. These artifacts remain observations. The diagnostic seal is
`epyc.kernel_promotion_lifecycle_evidence.v1`; it is not the prospectively
ratified `epyc.kernel_promotion_resident_window.v1` instrument and supplies no
promotion authority or timing acceptance.

Use `scripts/benchmark/kernel_promotion_resident_runner.py` with its existing
required plan, executable, K35 and resource-claim arguments. Add
`--evidence-pins <prepared.json>` to validate the prepared model stat/digest
record and hot-library identities and capture live witnesses. Add
`--compare-fresh` to run the identical fresh schedule after a successful
resident capture. A failed resident capture retains its failure status and
uses the existing cleanup-gated fresh fallback. `--fresh-only` remains a
separate diagnostic mode.

The runner records `resident_validity` in `capture.json` and a `validity`
summary for each fully sampled cohort. Each summary reports full content and
token-ID comparisons at the scheduled pair positions, native decode
tokens per second, candidate-to-production ratios, and their median and median
absolute deviation (MAD). It reports the median and MAD for each arm separately.

The resident fast-path design sets the same-runtime calibration median ratio
band at [0.99, 1.01], inclusive. With prepared evidence pins, calibration
requires matching executable digests, source commits and library digest maps.
Without evidence pins, it requires both arms to use the same resolved
executable path and digest. The diagnostic checks the 1% schedule-position
limit by comparing an arm's median decode throughput at its earlier and later
position in the ABBA quartet. The effect is the absolute difference divided by
the smaller median. The runner calculates this for both arms within each cohort.

A known parity mismatch, invalid decode timing, calibration ratio outside the
band or schedule-position effect above the limit invalidates the resident
capture. The runner keeps the raw responses and failure summary, and replays
the entire unchanged schedule with a fresh server per measured request only
after proving process death and port closure and passing fresh preflight.
Missing token IDs retain an `incomplete` resident validity status when the
other checks pass, so `--compare-fresh` can still collect the second lifecycle.
A `pass` status records the outcome of these diagnostic checks.

Prepare model digests before publication. Live validation checks the prepared
model's device, inode, size, mtime and ctime without hashing weights in the
grant. Mapped model files also require matching device/inode witnesses;
`--no-mmap` records that this mapping witness is unavailable. The executable
is hashed through `/proc/<pid>/exe`; mapped hot libraries must match the
prepared paths, digests and mapping device/inode identities. During-request
affinity, topology, NUMA, linkage, excluded warmups and captured-process
cleanup remain part of the capture.

The row packet assembles `input-plan.json`, `pins.json`, `SOURCE.sha256`, the
provider grant/open/close receipts and `resident/` beneath a staging directory.
The fresh comparison or fallback lives at `resident/fresh-replay/`. Finalize
with:

```bash
python3 scripts/benchmark/kernel_promotion_evidence.py /path/to/staging --seal-to /path/to/sealed
python3 scripts/benchmark/kernel_promotion_evidence.py /path/to/sealed
```

Staging and destination must be siblings; the destination must be new. The
finalizer validates the captures, writes `comparison.json`, hashes the artifact
inventory into `MANIFEST.json`, writes a manifest-bound `COMPLETE`, verifies
the result and renames the directory. Verification reproduces comparisons
from the raw artifacts and rejects changed or incomplete inventories.
For prospective Vidya ingestion, prepare the packet's `SOURCE.sha256` with the
exact runner, evidence validator, resident planner and K35 source used by the
packet. Use the original relative paths for the root files under the source
snapshot and `k35-research.py` for the K35 snapshot. The prepared arm pins
include the source commits. The runner records its source identities,
the retained HTTP entity bytes, the request's live claim identity and whether
a fresh comparison was requested. The finalizer verifies those records and
rederives the resident validity summaries and disposition before sealing.
Earlier parity-only seals can still be verified by the evidence tool.

Ingest a prospective sealed directory with:

```bash
python3 scripts/vidya/cli.py ingest kernel-promotion-lifecycle --path /path/to/sealed --as-of <UTC-timestamp> --only-new
```

Completed resident captures with full token-ID comparisons project an
observation about exact-parity mismatches for the sealed schedule and images.
The reader declines incomplete comparisons and fresh fallbacks. Unsealed
failure artifacts remain available in the capture directory.

Scheduled opposite-arm pairs compare full request bodies, full output content
and integer token IDs. When both lifecycles completed, the comparator also
compares each resident request with the same fresh request. Missing IDs remain
`incomplete`; a content or token mismatch is `different`. A successful fresh
fallback cannot turn a failed resident capture into an accepted resident run.
This lifecycle comparison does not replace the broad quality-parity pack.

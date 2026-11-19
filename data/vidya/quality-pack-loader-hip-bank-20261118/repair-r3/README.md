# HIP loader bank publisher smoke

The architect-general HIP loader bank reached its third failed publisher
qualification on November 18. This archive retains all three allocator
receipts and their native results. The row has no ready manifest. Stop retries
under the three-failure rule.

The third attempt set verbosity 4 for the small-model smoke command. The full
production recipe, request bytes and comparison controls match the predecessor.
The pinned v10 server reported ROCm0 AMD Instinct MI210 and offloaded 29 of 29
layers. Strict residency sampling then rejected thread 1925961 for exceeding
the smoke CPU mask 184–187. The result records the rejected TID. Its thread name
and observed mask were not captured. The server, listener and KFD entry all
cleared during cleanup.

If reopened, capture the offending thread's name and exact mask. Evaluate
`HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` for the HIP child, as used by the qualified
Historical544 launcher, and retain the existing all-thread mask and residency
checks. That environment change was not applied or tested here.

The archive contains only the changed plan generator, its generated plan and
manifest, the unchanged spec and evidence. Recover the other packet inputs
from the adjacent `smoke-repair` archive and use the scratch location declared
in the row spec for its absolute path bindings.

Restore the generated plan by decoding `plan.json.original-bytes.json` and
checking its recorded SHA-256. Check this archive with `sha256sum -c ARCHIVE.sha256`.

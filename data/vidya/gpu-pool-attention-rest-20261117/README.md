# Prospective SOFT_MAX and FLASH_ATTN_EXT capture

The private deployed packet at
`/mnt/raid0/llm/tmp/vidya-belief-substrate/attention-rest-ready/` captures the two
remaining original attention selections: 207 SOFT_MAX and 528 FLASH_ATTN_EXT
cases, seed `2026102603`, the digest-pinned c463f601b HIP executable and four
DSOs, MI210 and CPUs 184–191. It uses a distinct same-day row attempt `v2` and
the existing capture schema and grading.

One prospective request binds both ordered invocations. Each retains a raw log
and terminal record; strict readback checks exact operator coverage, native
selection and counts, artifact/source/shim identity, ordered windows inside the
request and grant, and at least two distinct complete in-window same-PID
KFD/VRAM/pinned-map/affinity samples per invocation. Error/partial artifacts
cannot satisfy official acceptance. Synthetic controls and smoke are separate
from the official native result and planning-context canary.

The original source dirty-state remains UNKNOWN, and the shim recreation still
mismatches its original source receipt. Counts use the artifact's candidate-local
CPU reference. This provides no performance, promotion, clean-source or RVP-C2-2
warrant; it does not invent model/device applicability or upgrade old results.
`publication.json` records queued smoke without claiming PASS or readiness.

# NI10 serving-call gap census — 2026-10-05

The prospective NI10 producer and adapter are published in root commit
`d61ae218f4b8e8c9d14e1e8361eabd740c745534`; the passive enqueue hook is in
orchestrator commit `b01ab9933c289a7c5a361050e153f5e486791acd`. The bounded
off-host fixture command passed all 21 cases (19 producer-module cases and 2
registration cases). This establishes the named fixture boundary only. It does
not establish coverage of historical records or a measured gap distribution.

One claimed census read only the 46,123-byte `serving_calls.jsonl` snapshot for
the predeclared Oct 3 and Oct 4 UTC windows. The source was unchanged across the
run; its pre-run, captured snapshot, and post-run SHA-256 were all
`fe8672b2289a236321630c57fdaa0453d6ead487d6f1c8b778e606a35b13cfc9`. The
producer and tee both exited 0. It saw 19 records, all 19 without a session key;
there were zero keyed sessions, zero gap rows, and no eligible class groups in
either window. The required per-class/session minimum was not met, so no
percentiles, brand attribution, TTL, or distribution conclusion follows.

The original private run directory is
`/mnt/raid0/llm/artifacts/ni10-vb-gap-dist-20261005T115712113076725/`. Its
manifest SHA-256 is
`1e2f12f7a3371288676ac67ae2ad46f549d16cfd0d45d5aca84d938796998e3d`; report
SHA-256 is
`9d47ea7f6ea4dbe4ca002c58a8c0060054114576e96233df767ed9477cc8caee`.

This finding is scoped to that serving-call journal and those two windows.
HSF-3 also names structured inference-tap events, progress-log session events,
and `/chat` checkpoints; those source schemas have not been included in this
census, so the result does not establish that all available session records are
unkeyed. Their field compatibility with the extractor remains a separate
read-only source-mapping finding. HSF-3's distribution and later-window
replicate therefore remain unmeasured.

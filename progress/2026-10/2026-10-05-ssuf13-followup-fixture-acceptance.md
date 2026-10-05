# SSU-F13 follow-up fixture acceptance — 2026-10-05

The bounded follow-up ran as GitHub Actions run `37312813571` from root workflow
commit `348704df9d65aeca285fcf71f699ebf4c863ac57`. It did not modify product
source or run inference. The ordinary AP54 fixture phase used orchestrator
candidate `86015733aa5dbe4c1bfcfbd996d7496a2494f098`; the separate synthetic
topology phase used fixture donor `bb6ce5d72c0a2b2b9ec48f9d27e003d626d1fe37`.

The three native receipts were independently reopened and projected through
the existing shared grading path. AP54 collected 126 cases: 102 passed, 24
skipped, and none failed; both the protected-child denial and private `TMPDIR`
positive controls passed. The ordinary capacity guard passed 1/1 with no
skips. The separately declared synthetic topology selection passed 13/13 with
no skips. The comparison captured 25 readsets, found 21 production/config
files unchanged, and verified the candidate readsets matched. These results
establish only the named off-host fixture boundaries, not broader unit-suite
or production-runtime acceptance.

The unmodified original artifact bundles are retained at
`/mnt/raid0/llm/artifacts/ci/ssu-f13-followup-37312813571/`. The comparison
JSON SHA-256 is
`27127fa7d30eba3872cef99eacf50e2dcbe4e5a8ea77daed9c9cd777aa82afea`.
Native receipt projection and acceptance were performed by the owning main
session; this note records that selected fixture boundary only.

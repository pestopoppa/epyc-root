# KB-RAG G12 query-shift preparation checkpoint — 2026-10-30

[belief: cc]

The final diagnostic packet is `/mnt/raid0/llm/tmp/codex-ni-kbrag-g12-queryshift-20261030`. It
freezes 90 original short queries and 20 paired 66–73-word narrative counterparts selected from
certification indices 0–13 and 50–55. The incumbent remains the unchanged full `index-qd-v1`
corpus (34,214 chunks, 1,522 files), GTE INT8, `query48/doc256`, and zero optional weights. Truth
paths are preserved, including missing and moved paths; recorded catalog coverage is 74.76% for
certification and 72.5% for the seed set.

The same final source passed a two-query full-index smoke in 56.70 seconds at 0.572 GiB sampled
RSS. A one-query cutoff returned rc 75 in 27.88 seconds with cleanup verified. The live keeper
accepted rank 59, any CPU quarter, 8 GiB, 7,200 seconds; it was not armed or granted. The full
110-query cohort remains pending. The primary decision metric is the fixed 20-pair
short-minus-verbose evidence-file recall@10 comparison; the existing strictly-greater-than-2 pp
signal and B7 verdict remain pending. These smokes do not establish retrieval quality, a cap flip,
or model adoption.

The existing SC50 source-family row and task now point to the G12 record fields and limitations.
The shared measurement carrier and `claim_tuple.grade()` remain authoritative. No adapter, emitted
ClaimTuple, ingest, register write, or planning-context canary is claimed. The committed preparation
conclusion is marked `[belief: cc]`; the committed-conclusion register route remains conditional
future VB-CC work.

This focused checkpoint uses the wrap-up validations already run for the G11 boundary in this same
lane: `git diff --check` passed, `index_state.py --check` exited 0, and the handoff flip count was
0. No README, Vidya, or index checks were repeated. The shared wrap-up lease was held by another
session, so index regeneration and publication remain for the integration boundary; no lock was
displaced.

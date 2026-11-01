# Strategy ablation belief integration: prospective contract

This is a design for a future producer hook, not an enrolled source or a
measurement. The current three-arm `epyc.strategy_prompt_ablation.capture.v2`
files are caller-authored assertions. Their custody verifier does not establish
that an inference happened, the order in which it happened, or the source,
grant, reset, counters, or score. Do not turn a passing custody check into an
attestation that those assertions have been independently verified.

The previous scratch `repl_strategy_ab.py` targets the two-arm
`epyc.repl_strategy_ab.record.v1` JSONL/manifest schema. It cannot read the
current three-arm directory schema and must not be enrolled unchanged. Its
source kind names the already-registered `s4-omega-ab-measurement`; that name
is occupied. A distinct strategy projection may use the existing measurement
source class and its shared ladder; do not register a second grading ladder for
that class.

Before publication, the native producer and the reader need an agreed,
versioned contract that binds the immutable suite, exact three-arm prompt
snapshots, full protocol, model/server/kernel and tokenizer content identities,
owned grant and slot-reset receipts, and the request and response bytes. It
must retain incomplete/error/missing values without converting them to zeros.
The current request-level `prompt_tokens` and `output_tokens_reported` must
stay whole-request values, not be duplicated or divided into per-turn counts.
Timing and scorer outcomes require their own native source and provenance.

At the write boundary, emit a source-authored record only after the supervisor
has captured the required evidence and the experiment's own failure and
completion states; synthetic fixtures must never become live measurements.
An ingestion reader must reopen and verify the native custody chain and emit
only the individual fields actually present. It must preserve `baseline`,
`strategy_short`, and `strategy_long` identities, declare the two guidance
arms as candidates against the shipped baseline, and avoid invented aggregate
or non-inferiority claims. Use the shared `ClaimTuple` and `claim_tuple.grade()`
ladder; do not add a source-specific grading rule. Enrollment in
`scripts/vidya/ingest_sources.py` and the source table in
`scripts/vidya/adapters/README.md` must point to the agreed schema and reader.

The owning session must also add the prospective wiring task to
`handoffs/active/vidya-belief-substrate-program.md` and validate the planning
context canary. Synthetic tests should cover all three arms, missing metrics,
incomplete and error records, synthetic refusal, byte tampering, provenance
mismatch, and refusal to assert schedule order from directory names. Until the
producer calls the verified hook and that canary passes, describe the source as
preparation only, not wired.

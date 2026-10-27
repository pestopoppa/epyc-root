# Scratch reclaim preparation — 2026-10-27

Prepared a private candidate for narrow per-file scratch retention declarations
and trash-first filing by completed row. It remains subject to owner review,
especially the stricter grant-admission compatibility impact. The ratification
text is a human-only draft; policy and the sweep were not changed.

The NI08 audit verified that three identified native binary files have identical
SHA-256 and length. The root KEEP and all originals remain in place; identical
bytes alone do not establish that their evidence provenance is interchangeable.
The conservative Git inventory did not find a checkout satisfying both its
ignored-inclusive clean test and local origin/main ancestry; local refs can be
stale. See `docs/drafts/scratch-reclaim-audit-20261027.md`. [belief: cc]

Separately, a private exact 19-source subset method records three sources
already absent and stages the 16 remaining sources only after fresh boundary
checks, main review and a receipt tied to the original operator decision.
Fixture tests exercise its failure and no-retry cases. No real source has been
moved or purged by this preparation. [no-belief: software preparation and fixture tests]

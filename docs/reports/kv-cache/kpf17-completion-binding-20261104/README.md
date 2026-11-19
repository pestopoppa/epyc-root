# KPF-17 completion evidence binding candidate

The isolated completion predicate now requires exactly one `test.log`,
`config.json` and `witness.json` from the same absolute, non-symlink attempt
directory beneath `out/`, each with a valid SHA-256 digest matching its bytes.
It refuses empty, missing, extra, mixed-attempt, outside-root, symlink,
nonregular and changed evidence. Five model-free tests pass for this helper.

This is a review copy, not integrated into a live row. The tests exercise the
binding helper rather than the complete launcher. The change does not prove
scientific validity, evidence authenticity, protection against same-UID
concurrent mutation, or full-wrapper stop precedence.

# Staged ED25519 private-key header recognition

The ROOT staged-blob PII scanner now recognizes `ED25519` PEM private-key headers. `OPENSSH` was already supported; the bounded change preserves it and existing RSA behavior. Synthetic staged-index coverage composes RSA, OPENSSH, and ED25519 headers at runtime, checks ordinary ED25519 metadata passes, and retains token, partial-stage, and all-excluded controls. The scanner still inspects staged blobs and retains its producer, allowlist, schema, and custody behavior.

The exact source pin is `77d0e5de9624ca8ebd4ce2cfcdbbc240bb470642`; recipe commit `adcb678c71f37499bdbafc006b6d443fd244836c` was promoted to ROOT main `eb870f0fe697f02f887bedecaeaccaf24df2d531`. The approved native capture run `37474797195` completed 9/9 selected fixtures: 9 passed, 0 skipped, 0 failures, 0 errors. The standard native conformance carrier emitted one `fixture_execution_conformant=true` observation (one Judged/Located record and three canonical frames). Inner negative/positive scanner controls remain test cases, not separate ledger observations.

This is structural synthetic-fixture evidence only. It does not prove privacy, detect all secret formats, establish whole-repository scan coverage, or authorize a whole-file fixture exemption. The parent TOC-RD-1a remains open for the operator's global whole-file risk decision.

[Original native evidence](../../artifacts/ni07/run-37474797195/README.md) and [separate operator decision package](credential-fixture-hook-decision.md).

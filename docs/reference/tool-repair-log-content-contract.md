# Tool-call repair log content

The repair outcome helper records outcome, raw-content SHA-256, raw byte count and an explicit `utf-8-surrogatepass` encoding policy. It no longer includes the raw malformed JSON payload in that helper's log line. UTF-8 byte count uses the same encoded bytes as the digest, including lone-surrogate handling; outcome counters and lock remain unchanged.

Parser/repair acceptance, rejected-content behavior and the existing bounded visible refusal echo remain unchanged. This is one helper's log minimization, not a claim that every log/output is payload-free. Descriptive counters do not become global rates or decision authority; no new source class/ladder is added.

Two APP paths713a79ab promoted maincfdb4cbf; three ROOT recipe/inventory paths0c9e21ea promoted main331f792f. [Original corrected off-host CI](../../artifacts/ni07/run-37456098288/README.md) passes149/149: full existing prompt-builder module plus repaired/unrecoverable sentinel/counter/hash/byte-count and lone-surrogate controls. Initial NULL preflight artifact is preserved separately and never converted into a test result. MAIN independently reviewed source/context/API originals and metadata-only symlink handling. No live tool/model, corpus traces, global privacy/rate or whole-suite warrant.

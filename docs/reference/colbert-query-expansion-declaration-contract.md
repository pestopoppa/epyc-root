# ColBERT optional query-expansion declaration

Before ONNX/tokenizer construction, `ensure_loaded()` checks the merged supported model config's optional `do_query_expansion`. Absent or exact false preserves historical no-expansion behavior; true refuses as unsupported and a present nonboolean refuses as malformed. Failure follows the existing loader catch: explicit error log, cleared partial session/tokenizer/identity state and False return. No new outward caller exception or expansion implementation is added.

Supported config merge precedence remains unchanged. Actual graph `token_type_ids`, widths, caps, lowercasing, prefixes, parser and valid loaded-path behavior remain. Config is checked on a fresh load, not continuously reread for an already cached singleton. This source guard does not migrate an index or activate a live model/feature.

Two APP paths22525649 promoted main7980b229; two ROOT recipe paths141941e3 promoted main198d3603. [Original off-host CI](../../artifacts/ni07/run-37456357367/README.md) passes24/24, full existing identity regressions plus absent/false/precedence/true/malformed/preconstructor/clear-state fake controls. MAIN verified exact pinned source/context/API originals. Synthetic conformance establishes no retrieval quality, whole-suite or live deployment warrant; broader K2/web and live gates remain separate.

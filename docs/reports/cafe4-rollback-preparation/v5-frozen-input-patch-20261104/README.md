# CAFE-4 V5 frozen-input correction

This is an unapplied, unbuilt correction for the matched-geometry V5 source proposal. It replaces in-grant tokenization with nine frozen token arrays prepared using the pinned v10 vocab-only tokenizer, and emits the batch-versus-checkpoint reference fields alongside the other pairwise errors. Source/proof expected hashes, token IDs, model/tokenizer/library provenance and linkage checks are retained. The original proposal was not modified.

The agent reports patch dry-run, nine manifest/header mappings, proof syntax and tokenizer linkage PASS. The corrected candidate has not been compiled or run. Rebase only against matching source hashes, reseal launcher/runtime inputs and validate the full build and native controls before any CAFE-4 conclusion. The earlier failed native tolerance remains unchanged; this proposal does not reclassify it.

# C6 bundle hash repair — 2026-11-01

The copied test changes only RETAINED from the original absolute run path to the bundled retained-evidence directory. Original manifests incorrectly retained its original source hash. Original manifests and the original test bytes are preserved under provenance/ as .source files. SOURCE-COPIES.json now distinguishes source_sha256 (original) from sha256 (current destination). PACKAGE-SHA256SUMS and SOURCE-CLOSURE.json describe current bundled files; neither claims native execution qualification.

Verify from this directory with `sha256sum -c PACKAGE-SHA256SUMS` and `sha256sum -c ORIGINAL-SHA256SUMS`, then run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest test_arm_order test_actual_main -v`. Controls create retained model-free fixtures; generated fixture directories are outside the static source closure. No native inference or grant admission is performed.

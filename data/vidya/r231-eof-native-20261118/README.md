# R23-1 prospective native EOF source

Current row: `vidya-r231-eof-native-wire-20261118-r2`. [Publisher PASS](PASS.json), [row spec](row.spec.json), [reviewed pins](pins.json), [offline controls](offline-controls.txt). The reusable producer is `scripts/benchmark/r231_eof/capture.py`; the registered projector is `scripts/vidya/adapters/r231_eof_capture.py`.

Expected clean rc 75: smoke executes actual CLI EOF verification in isolation; full 11-step native result requires the keeper run.

The first invocation demonstrated the CLI but needed an explicit publisher
predicate for a diagnostic result carrying `measurement:false`. The accepted
first publication appears under `superseded-r1/`. The corrected successor
preserves the exact native plan and checks the known PTY slash echo before the
final result marker. Its fresh publisher PASS withdrew the first publication.

The nine behavioral cases are one loopback mock model-selection CLI EOF case
and four console cases in each of redirected simple and advanced PTY modes.
Linkage verification and console compilation are custody steps. Publisher
smoke ran on CPUs 116–119 and captured native CLI rc 1 after GET /health and
GET /v1/models, with zero POST, owned live process mapping and successful
cleanup. No GGUF or inference is involved. Full native capture and actual
planning-context acceptance remain pending.

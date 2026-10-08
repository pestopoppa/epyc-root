# Tulving historical offline replay custody (M12i)

This runbook covers one offline scoring replay over already captured June responses. It is a historical diagnostic, not a new inference repetition, and emits no arm or quality tuple. The prospective source enrollment must be published before the replay is separately approved. The protocol proposal remains unratified; existing fresh Tulving arms continue to use the SC67 producer and shared ladder.

## Frozen inputs and implementation

Bind the accepted Research scorer `72832ef6eed7d0439be7853a23d23efb876d48b3` and its exact source/readset before the run. The later public `3caaf22fa853daab5c5ae055ca46b67809e2c938` changes EVL documentation only. Native scorer version is 2, gold binding is `chapter_set_v1`, and native SRS and CAS are higher-better; this replay changes none of those definitions.

The raw input is `benchmarks/results/runs/20260619_141212/ingest_long_context_baseline.json` (24,126,503 bytes; SHA-256 `6cea4eccf2af00488ae8edd179b043515f941516952b0c4b6a66a2f179c62234`). Gold is the captured Claude 19-chapter parquet/book selected for nominal `--chapters 20`, variant `Udefault_Sdefault_seed0`; bind the exact original bytes and full scorer/native/import closure in the execution readset. The adapter forces context `none` while building gold; no retriever or model is used.

Use only the private owned environment `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/m12i-replay-OWN-20261008-v2/venv`, whose original constructor receipt SHA-256 is `b9043ce92727990ca38492312ab016a839f69f3da947e6d7311f23e82a3485ac`. Its five hash-locked CPython 3.13 Linux wheels provide pandas 3.0.3, pyarrow 24.0.0, numpy 2.4.6, python-dateutil 2.9.0.post0 and six 1.17.0. Preserve the original 6,063-path environment custody and 667-path stdlib/runtime custody; do not alter or substitute ambient `.venv` environments.

## Source-first enrollment and execution boundary

Before scorer invocation, MAIN must publish the prospective addition to the existing Tulving adapter source row and the `VB-M12I-REPLAY-CUSTODY` task in the existing Vidya handoff. This adds no adapter class, measurement source row, grade ladder, historical tuple, or checkbox closure. Bind the actual resulting ROOT publication commit in the later replay readset; do not guess a future commit. The replay uses a separate MAIN-approved immutable K and an exclusive `historical-original` output directory that must be absent before execution.

The one-shot helper invokes the accepted scorer on the frozen raw input with `--chapters 20 --variant Udefault_Sdefault_seed0` and exclusive JSON/Markdown outputs. It supplies no `--belief-measurements`, `--arm`, or `--run-id`. Record exact argv, source HEAD and clean status, source/input/environment hashes, UTC window, stdout, stderr, raw exit status, pre/post custody and both report paths. Binding refusal is failure, not a zero result or permission to reconstruct missing provenance. One failure is preserved; no automatic retry.

## Reader and comparison checks

After the replay, call only the existing strict `tulving_episodic.rows_for_run` reader on the original and replay directories. Both missing-sidecar paths must yield zero native rows. Do not call the writer, projection, or grading path. If either directory unexpectedly contains `belief_measurements.jsonl`, preserve it and refuse the expected zero-row custody result; never delete or repair it.

Compare named deterministic components, not whole-file bytes: SRS/CAS, subset sizes, five SRS bin counts and means plus bin basis, tau partial-coverage exclusions, and per-question F1/precision/recall/tau fields. Preserve both reports; paths, added provenance metadata and Markdown formatting may differ. An equality result applies only to the enumerated fields and this frozen diagnostic.

## Limits and closure

The result supports deterministic scorer reproducibility and diagnosis of the historical responses only. It does not establish fresh memory efficacy, a model-performance repetition, deployment readiness, protocol identity, or a measurement-grade claim. Human metric definitions and protocol ratification remain separate human trust-boundary work. Close `VB-M12I-REPLAY-CUSTODY` only after MAIN accepts the source-first enrollment publication, the exact one-replay custody record, the zero-row reader check, and component-level comparison.

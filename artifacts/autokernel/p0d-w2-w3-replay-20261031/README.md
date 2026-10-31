# AKX-P0d native replay evidence

`REPORT.md` records MAIN's acceptance of the W3 half-A r2 and W2 CPU r3 structural facets. `REPLAY.json` is the machine-readable count and identity replay; `independent_replay.py` recomputes it from the bundled `evidence/` native records, request/response logs, foreign-load samples, run results, model-input identity files, wrapper/source manifests, and ELF manifest. The model files and server binary are not copied; their recorded hashes and source-time hash checks are retained. If the candidate ELF remains at its recorded path, replay also rehashes it against the ELF manifest.

`writer-fix/` holds a future-wrapper patch proposal and fixture for the full-census `requests_completed` counter. It reports a count only when all native request windows and boolean `success` fields are present; malformed or absent evidence becomes null with an error, explicit valid failures count zero, and result-writer success remains independent of census state. Do not apply it to the historical run folders: their raw bytes and captured source identities remain immutable.

No throughput, quality, GPU-W2, full-P0d, or production-promotion claim is made.

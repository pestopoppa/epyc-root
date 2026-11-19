# CH-26b private C5 map integration — standalone review snapshot

These are exact copies of the 11 changed/new files in `/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/ch26-census-owner-integration/private-c5/`; this is a full-file review artifact, not a patch and not a runnable packet. `SHA256SUMS` binds these snapshot files. Other pre-existing owner modules and test fixtures remain in the private-c5 directory and are required to run the test suite.

New files: `runtime_linkage.py`, `test_runtime_linkage.py`, `test_boundary_witness.py`.
Changed files: `boundary_witness.py`, `census_owner_factory.py`, `floor_binding.py`, `run.py`, `complete.py`, `test_floor_binding.py`, `test_private_integration.py`, `test_completion_entry.py`.

The request owner requires a prepared C5 map receipt, captures before and after the request, checks stable target and mapping, and passes the receipt through census composition. Floor binding and completion replay validate the mapping, prepared file metadata and digests and bind the preparation digest; prior writer and census checks are retained. The `run.py` unconditional disabled exit remains present.

Validation executed against the complete private-c5 directory:

```sh
cd /mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/ch26-census-owner-integration/private-c5
python3 -m unittest discover -q
```

Result: 41 tests passed. Includes same-inode mutation with restored mtime at binding and replay, missing mapping, old preparation, wrong target, factory propagation and request-boundary checks. The model-free fixture uses temporary files; no inference was run.

Before any execution: independently generate a fresh build-runtime-prepared.json with `runtime_linkage.prepare` and an existing validated C5 custody receipt; complete integration review, source sealing and native qualification. Observer overhead, continuous custody, placement, contention and floor admission remain unproven. Metadata check is point-in-time, with race and privileged-manipulation limitations. No publication was performed.

A fresh preparation and its validation record are included as `build-runtime-prepared.json` and `build-runtime-prepared-check.json`. On 2026-11-05 they bound all eight selected C5 binaries to the verified source and store manifest and current file metadata; synthetic complete-set binding passed and old or partial receipts were refused. The preparation must be revalidated at actual use. A synthetic 96-phase floor bind and replay passed with this receipt; altered preparation and partial mappings were refused. This is model-free evidence and does not prove a live mapping or admit a floor.

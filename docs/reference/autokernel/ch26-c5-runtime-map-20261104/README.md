# CH-26b C5 runtime-map and request-binding prototype

This directory preserves a prepublication prototype. It binds process-map device and inode identities to eight C5 binary digests from the prevalidated store manifest, samples the owned target at both request boundaries, and carries those point-in-time receipts through request binding and completion replay. Missing mappings, changed target identity or inode, digest mismatch, and altered bindings fail closed. It makes no claim about inference, continuous mappings, execution placement, contention, observer overhead, or the DS41 floor.

`runtime_linkage.py` contains the pregrant binary-hash preparation and live process-map checks. `boundary_witness.py`, `floor_binding.py`, and `complete.py` show their integration and replay. `run.py.txt` is the preserved scratch-owner draft, not a launcher. The `native/` directory is the compact observer version present in that draft; it is not the separately qualified r3 diagnostic packet and must not replace it. The prepared JSON files are historical preparation records: device and inode values must be re-prepared and bound to the current store before operational use. No model weights were hashed by this prototype.

Run the model-free checks from this directory:

```sh
python3 -m unittest -q test_floor_binding test_runtime_linkage test_boundary_witness test_request_observer_join test_complete_archive
python3 -m unittest discover -s native -p 'test_*.py'
sha256sum -c SHA256SUMS
```

The snapshot is not a publishable row. A successor must reconcile it with the qualified compact observer, verify the source and inputs once, seal a fresh packet, address the pending observer-overhead and calibration prerequisites, and pass the normal publisher smoke. The tests use synthetic process-map and request fixtures; they do not establish a live C5 run.

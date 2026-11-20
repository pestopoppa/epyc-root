# Explicit benchmark registration

`public_benchmark_registration.py` checks a schema-version-1
`public_benchmarks.yaml` and stages local results for review. It does not write
the orchestrator catalog or adopt a candidate as a routing prior. CJ-GATE still
owns adoption. A passing schema check says nothing about discrimination or
measurement validity.

Check the current catalog:

```bash
python3 proposed/cj567/public_benchmark_registration.py --catalog /path/to/public_benchmarks.yaml
```

To stage results, supply `--results /scratch/results.json --out /scratch/registration.json`.
The results document is a list of objects with these fields:

| Field | Meaning |
| --- | --- |
| `model` | Exact model ID in the supplied catalog |
| `benchmark_key` | Exact instrument key registered in `axes` |
| `value` | Finite local correctness score in [0, 1] |
| `absent_from_card` | Explicit boolean, true iff the catalog has no vendor score for this key |
| `source` | `path` plus `sha256`, or `repo`, `path`, and full `git_object` |

The output carries both input hashes, source attestations, and a
`public_benchmarks_fragment` containing `schema_version: 1` and per-model
`local_benchmarks` / `absent_from_card`. Source pins are carried for review;
the tool does not establish their truth. Merge approved fragments by benchmark
key; replacing an entire model or `local_benchmarks` mapping would discard other
results. The absence list preserves existing disclosures and adds each new
local-only key. Legacy local-only keys are tolerated without backfilling their
disclosures; new registrations require an explicit disclosure.

Register new instruments explicitly in the input catalog first, retaining
version/mode distinctions (e.g. `bfcl_v3` versus `bfcl_v4`, or a separate REPL
instrument). Axis names are rejected as keys. Keys sharing an axis remain
separate. Vendor values are preserved, and different existing local values
cannot be overwritten. Repeated YAML keys are rejected before parsing loses
them. This interface accepts correctness fractions, not unnormalized Elo.

Controls use synthetic scores only:

```bash
python3 -m pytest -q proposed/cj567/test_public_benchmark_registration.py
```

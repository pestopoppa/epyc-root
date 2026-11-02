# RM-11a selector lifecycle patch — review only

`selector-safety.patch` applies to research commit
`f0737320a54f6454a67f957bf1b6eb5ec204149d`, selector SHA-256
`de05a45612bfa8270c6db89b9a017274dadd8f767ec19350c52959d3e517e1d8`.
It replaces process-name snapshots and process-group termination with records
and cleanup of subprocesses captured by the runner. Failure to terminate or
record cleanup remains visible. It does not establish host admission or GPU
residency and is not an authorization to run the selector.

Run offline validation from this checkout:

```sh
python3 -m unittest discover -s scripts/coordination/rm11_selector_prep -p 'test_*.py'
```

The tests read the pinned source from the local research git object database,
verify its SHA-256, apply the patch in a temporary directory, exercise extracted
lifecycle functions with fake processes, and inspect both execution paths. They
start no server and do not exercise real PID ownership, server health or inference.

**Do not deploy or publish a row based on this patch alone.** Missing work includes
content-verified binary and loaded libraries, pinned scorer import and model
bytes, proof that the child owns the listening socket, keeper admission and
in-run GPU residency, correct replay scoring provenance, SC43 capture and an
approved matched-arm protocol. The patch does not provide termination-event log
paths, and GitNexus cannot resolve its upstream impact in this unindexed lane.
Integration requires owner review and source-repository impact analysis. It has
not been applied to the research checkout.

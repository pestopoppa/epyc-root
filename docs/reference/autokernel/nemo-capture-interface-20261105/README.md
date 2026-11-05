# Prospective capture producer-to-consumer interface test

This offline test passes a record produced by the actual `capture_client.capture`
through `verify_marker_identity.check`, using mocked HTTP transport and synthetic
server/profiler events. It checks that a matching native request join is accepted
and that a join for a different request is rejected. Run from the repository root:

```sh
python3 -B -m unittest discover -s docs/reference/autokernel/nemo-capture-interface-20261105 -v
```

Both tests passed on 2026-11-05. This tests only format compatibility and request
identity rejection. It does not qualify the instrumented server, profiler marker
normalization or clock semantics, prove same-run custody or token attribution,
or reconstruct missing boundaries in the historical traces. The r14 build and
subsequent capture remain prerequisites for live qualification.

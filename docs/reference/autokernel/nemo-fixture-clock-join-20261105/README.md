# Known-fixture clock marker join

`fixture_clock_join.py` joins the known graph fixture's two host `CLOCK_MONOTONIC` brackets with the existing SDK 0.5-documented marker CSV adapter. It checks exact marker names, process and thread identities, ordered timestamps, and intersects the two host-minus-profiler offset intervals. A nonempty intersection only says that a constant offset is consistent with those two bounded observations; it does not prove clock identity, continuity, drift, GPU attribution, or historical token boundaries. The accepted marker CSV schema remains unverified against the installed SDK 0.4.

Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_fixture_clock_join`. A missing, duplicate, reordered, misidentified, malformed, or inconsistent input is refused.

The `nemo-known-graph-trace-markers-20261105` publisher smoke produced two host clock brackets in `fixture.log` but no marker CSV under `fixture-trace/`. The published row's graph/kernel smoke pass does not establish marker capture or clock correspondence. No marker join or historical boundary claim follows from that smoke.

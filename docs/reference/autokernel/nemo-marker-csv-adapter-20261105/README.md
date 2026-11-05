# Prospective NEMO marker CSV adapter

This offline, fail-closed adapter accepts the seven-column marker CSV format documented for [ROCprofiler-SDK 0.5](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/docs-6.3.0/how-to/using-rocprofv3.html#marker-trace). It normalizes exactly two named point markers; it does not assume profiler timestamps share the host clock. Two synthetic test methods include seven malformed-input controls.

The installed 0.4 SDK header describes nanosecond marker timestamps but does not establish the CSV format or clock correspondence. No native marker capture validates this adapter; it is not integrated into a launcher, and it does not recover historical token boundaries or qualify a row. Native schema and clock validation remain required.

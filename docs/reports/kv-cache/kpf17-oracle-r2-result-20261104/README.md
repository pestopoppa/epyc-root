# KPF-17 mutation-oracle r2 native result

`kvfork17-oracle-test-r2-20261104` completed its outer launcher with rc=0, but
the native result is **INVALID** under the declared rule. The recorded GDB
inferior reached the initial and main stops, but its Test 6 witness has zero
entries, zero mapping samples and no mutation mechanisms. The native log has no
Test 6 PASS markers; the result reports `ValueError: incomplete or duplicate
sample points`. The exact reason execution did not reach Test 6 is not proven
by these records. Both captured processes were verified dead with no cleanup
signals. No conformance pass or kernel defect follows.

The original result and its three referenced files are retained here with the
manifest and end receipt. Test log, config and witness hashes match the native
result's own file bindings. Model weights are not included.

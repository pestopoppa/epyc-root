# KPF-17 oracle r3 signal diagnosis

The original `poller.out` records region-lock forwarding signal 15 to its
child immediately before the launcher reported `rc=0 reason=complete`. The
retained native witness has an inferior exit event with no exit code, no
continue-return record, and no Test 6 entries. A model-free actual-GDB control
in `gdb_term_control.py` reproduced that same event pattern and GDB rc 0 after
SIGTERM to its own captured debugger PID. This demonstrates a possible
mechanism; it does not establish who sent the original signal or why. The
scheduled hard end was approximately 40 minutes later. The full native
result remains INVALID.

The original packet's private launcher sets rc 75 for disk-floor/hard-end,
then checks its completion predicate before publishing the end reason. Its
predicate accepted a sealed INVALID record; thus it could mask such an engine
stop as `rc=0 reason=complete`. The packet-local candidate `complete.py` here
requires PASS before the completion predicate succeeds, while leaving raw
INVALID records available for filing. Three model-free test methods cover PASS,
INVALID under four stop labels, and incomplete PASS records. These are fixture
tests of the predicate; they do not run the full row wrapper or establish that a
valid PASS can never coincide with a guard stop. No shared keeper or guard was
changed. Integration and a full native run remain open.

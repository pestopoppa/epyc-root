# KPF-18 group-3 bounded seed transport preparation

Lane-owned preparation only. The private successor and both rc78 entry barriers
are unchanged. No scheduler grant, server, model, native request or GPU execution
was started. R15 stays INVALID; this work gives no inference clearance.

The retained transport uses `response.readline()` with a socket timeout. A peer
sending occasional bytes can reset that timeout indefinitely. The prepared patch
adds an independent monotonic watchdog that shuts down only the captured own
completion socket after at most 180 seconds or the remaining real context
deadline, whichever is earlier. Connect receives that same remaining budget;
elapsed connect time is included in the watchdog deadline. An expired watchdog
becomes a construction error even if the reader returns EOF normally. Existing
native cancellation/release checks and raw partial retention remain in place.

Owner integration into a NEW reviewable successor requires checking BASE.sha256,
copying socket_deadline.py into its vendor directory, applying
cancel_seed_transport.patch, and rebinding the source inventory and launcher
bootstrap with the existing custody tools. The prepared patch dry-run matches
the pinned private transport. It was not applied to that private packet.
Both disabled entry barriers must stay in place through source review and the
remaining admission/integration work.

Eight model-free tests pass:

```
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s scripts/coordination/kvfork/kpf18-g3-supervision -p 'test_*.py'
```

Real local socketpairs cover silent-peer shutdown, trickle traffic that cannot
reset the total deadline, clean completion, invalid deadlines, inclusion of
pre-watchdog connect elapsed time and refusal when connect exhausts the budget. There are no
synthetic grants. Output controls reuse the retained, SHA-bound output_reserve.py
and count driver log, tmp, cache, raw slot saves and conformance files together,
including sparse logical bytes; nested symlinks refuse. Small control fixtures
under /mnt/raid0/llm/tmp/kvfork/kpf18-output-* are retained without deletion.

Whole-attempt supervision already exists in the retained private supervisor:
exclusive attempts/run-<digits>, attempt-local TMPDIR/cache/driver.log/raw-gate,
guard checks every nominal 0.25 seconds and again after child exit. The reviewed
supervisor SHA-256 is a85612e5c878d299c83a2dcac69b6f5126136354c3243c4f38394d56a29b0a9f;
guard.py is 8c8dac0efdadb9552e0b826b1d9ba832b4a2ed6eab5393dc690319fe4b3faac3.
The root arithmetic controls demonstrate what is counted, not a running native
supervision path. This patch introduces no second output-policy implementation.

Limits: socket shutdown is not proof of native task release. This bounds waits
on the completion socket only; a stalled separate slot-query socket, blocked
filesystem write/check or process cleanup is outside that bound. Python thread
scheduling is not a real-time guarantee. The watchdog does not observe STOP/HOLD
between boundaries; the existing outer supervisor remains responsible for those.
The existing output checks are sampled, not a quota; overshoot remains unknown,
and writes outside the attempt root would evade accounting. The retained cleanup
can wait indefinitely for an uninterruptible child and uses process-group
signalling before adopted-child draining. These whole-attempt limitations remain
unqualified; this artifact claims only the tested transport improvement.

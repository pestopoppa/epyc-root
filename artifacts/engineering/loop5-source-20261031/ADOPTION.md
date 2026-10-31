LOOP-5 source checkpoint; original task remains OPEN.

No live scheduler, launcher, configuration, daemon, queue, grant, message or peer process was changed. No model request or reindex was run.

Canonical tracked source: scripts/coordination/filler_run12.sh. Its optional metadata hooks are disabled unless LOOP_METRICS_LEDGER is explicitly supplied. Existing locks, commands, grant checks, rc propagation and scheduling remain in place. Launcher-admission records stop at dispatch; dispatched job rc is a distinct job-outcome phase, including rc64/75. An unstarted future grant/held runner is deferred, not a failed admission. A signal or telemetry failure cannot produce a clean coverage seal for an unfinished attempt.

The actual current keeper and calendar quarter writer live in owner scratch, not canonical tracked source. The sibling .patch files are source-pinned proposals against ws58-calendar-keeper-v7e.sh and grant-ws58-quarters-20261031.sh. The owning session may review/apply them only at its normal safe replacement boundary, from an exact published source checkout, preserving its current guards and adjacent changes. Do not hot-edit a running script, immutable READY packet or another session's files. Existing GPU writer and custom/frozen launchers require their own equivalent source-pinned hook adoption before claiming fleet-wide attempt coverage. No owner adoption is requested before source review/publication.

Owner-selected environment at that boundary:
- LOOP_METRICS_LEDGER: an own append-only metadata file with adequate free space. Hard cap16MiB; no automatic deletion/rename/rotation.
- LOOP_METRICS_HELPER: exact published scripts/handoffs/loop_metrics_events.py.
- LOOP_METRICS_HOOK: exact published scripts/coordination/loop_metrics_hook.sh.

The keeper hook reads /proc/stat idle counters for CPUs0-95 using host stdlib Python. Values are kernel-accounted CPU idle-hours with iowait EXCLUDED, not physical hardware-idle duration or whole-resource wall-clock idle. Same-boot/HZ/CPU-set/monotonic/reset checks protect paired samples. Missing day boundaries leave daily coverage partial; no interpolation or zero filling. Cumulative counters can span a missed sample, but do not establish scheduler availability or GPU idle. Original whole-resource idle hours remain UNKNOWN.

The quarter-writer hook captures every invocation/result of its native grant_ok call, including rc12 normally omitted from the text log. It preserves command stdout/rc. A clean session with contiguous ordinals, expected event count, paired attempt outcomes and no unresolved reservations supports only that named producer's covered-window rate. It does not prove every writer was instrumented or produce a full-day/fleet-wide denominator. Lost/truncated/malformed/capped/unsealed records remain unknown. The reader does not merge incomplete sessions into a claimed daily total.

Read-side invocation after creating the existing native decision snapshot:
python3 scripts/handoffs/verdict_count.py --json OWN/native-verdict.json
python3 scripts/handoffs/loop_metrics.py --date YYYY-MM-DD --verdict-snapshot OWN/native-verdict.json --events OWN/loop-metrics.jsonl

The daily report reads existing filing-due/keeper-alert metadata and explicit native producer snapshots. It writes only stdout. It does not read conversation or bus message contents. Operator-message count is UNKNOWN without an authorized metadata producer, and automated nudges never count as human messages. Decision counts retain unchanged verdict_count semantics, not new scientific grading.

Remaining acceptance: reviewed source publication; owner-boundary adoption of every required calendar/launcher producer; real daily coverage and actual reader consumption; authorized human-message metadata if an actual count is required. LOOP-5 stays unchecked and earns no completion quota at this checkpoint. Wiring/table/task proposal is separate and owner-applied; no new grading ladder.

R2 compatibility correction: disabled telemetry defines only local no-op call sites, adds no helper-file dependency and installs no EXIT trap. A requested ledger with no helper or a pre-existing EXIT handler leaves launch behavior intact, emits a fixed metadata-coverage warning, and refuses to claim a clean telemetry session. Original handlers are preserved rather than chained/evaluated. Standalone copied-launcher controls exercise ordinary completion and the unchanged pre-start STOP refusal without dispatching a job; the STOP test's only admission callback is explicitly synthetic and creates no canonical grant or resource claim.

VB-KB-CATALOG-CONSUMERS — source-audit disposition for MAIN

At orchestrator main 48a546e90fbc202a0c2ae103203621ba29175915, the strict catalog reader validates native dependency rows and refuses malformed/mismatched records. Both current evidence-producing consumers use it: K7 report attaches the validated row before artifact writes; Lab captures it into context and persists that context in the manifest. Their source tests cover attachment, absent legacy rows and refusal paths. The exporter helper has no production callers, but that is not a defect: these consumers call the strict reader directly and retain its validated native object.

The append-only query-length telemetry report is a distinct historical measurement stream. Its producer binds observations to a byte-prefix digest/path and time window; its adapter projects producer-authored observation rows. Attaching today’s catalog row to that cumulative report would retroactively claim a dependency for earlier events, contrary to the task’s no-historical-synthesis boundary. It should remain outside this dependency attachment task.

Recommendation: MAIN may close the bounded source audit as satisfied. No code change or additional test is indicated. Evidence and hashes: audit-evidence.json in this directory. This disposition does not assert anything beyond the listed current consumers and sources.

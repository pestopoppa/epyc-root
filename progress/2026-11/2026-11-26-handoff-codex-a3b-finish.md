# A3B Taskflow canary completion

The operator authorized this session to finish the A3B canary using C22 CPU and GPU servers concurrently, four slots each, with whole-host CPU placement and overlapping GPU control cores. Six completed GPU attempts were retained from the previous session. Thinking tasks use the GPU. Spare GPU slots also accept queued non-thinking tasks after template and live-response checks confirmed the per-request setting.

Both servers use the composite source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`. Store manifests, binary and library hashes, linkage, live GPU residency and CPU activity were checked. Each server has four 131,072-token slots and MTP D=2. Runtime evidence is under `/mnt/raid0/llm/tmp/taskflow-finish-20261126/`.

Hand audit identified false accepts in grader isolation, additive documentation edits and image normalization. Stronger reviewer instructions still accepted the defective isolation and documentation patches in live replay. Verification now exercises a trusted grader-isolation contract through simulated namespace success, explicit permission refusal and unrelated launcher failure. An independent image contract checks bytes, dimensions, pixel caps and the real analyzer/recorder integration using a synthetic HTTP response. The NOFOLD acceptance now preserves the freeze paragraph and checks for one Rules heading.

The isolation contract rejected all four preserved defective patches and accepted the sound fixture. The image contract rejected the two saved GPU patches for their actual dimension errors. Later saved-result rechecks reject the four fresh isolation/image candidates too. The final Taskflow suite passed 224 tests. These are diagnostic and structural observations. The host's namespace permission refusal is retained as an expected case in the isolation fixture.

The fresh non-thinking isolation patch exposed silent reviewer diff truncation. Full diffs now reach the reviewer. Its broad permission skip and invalid access errno were then caught by expanded independent checks, using the same saved patch. The documentation retry exposed raw shell deletion of tracked files despite the stated untracked-only cleanup rule. A Git-aware scratch helper now enforces that rule. Eleven scripted OpenCode controls verified tracked-file preservation and allowed scratch cleanup.

The final LOOP correction produced a false green XFAIL through a pre-launch formatting exception. An independent calibration gate accepts the three sound saved reproducer recipes and rejects this altered recipe. Reproducer-only outcomes carry a hold against completing the underlying source-fix task.

The current canary packets also clarify actual encoded dimensions and supported recorder metadata. The LOOP calibration requires module object identity while its canonical source-fix task retains its full scope. WS4 is already completed at the application base and its four attempts are recorded as intentional skips.

Per-request and per-stream telemetry includes response latency, upstream and delivered first-token latency, prefill and decode rates, aggregate rates, token/cache/draft counts, and resource samples. Records retain the device, slot, task and thinking mode.

The verdict is FIX-HARNESS under the original rule, with the identified repairs completed. The original sixteen executed attempts produced six sound results, and six correction attempts produced one additional sound result. Four stale positions skipped before worker launch. Every planned position has a terminal disposition, and both owned servers and host claims were released. The original controller's stale-skip completion error is recorded beside the reconciled ledger. Old proxies provide response-byte latency for the six retained units.

Final findings and evidence pointers are in `docs/design/taskflow-stage1-canary-findings.md`, with telemetry and source manifests under `/mnt/raid0/llm/tmp/taskflow-finish-20261126/`.

Next: operator reviews dispatch eligibility using the audited canary and repaired acceptance checks.

## 12:56Z — Complete A3B canary and repair observed harness defects

Canary filed as FIX-HARNESS with repairs validated. Original 16 executed attempts and six corrections yield seven sound outputs, plus four stale skips. Final suite passes 224 tests and eleven OpenCode tool controls. Independent gates reject the preserved false positives. Both C22 servers and host claims are released. Findings and evidence are linked in docs/design/taskflow-stage1-canary-findings.md.

Next: operator reviews dispatch eligibility.

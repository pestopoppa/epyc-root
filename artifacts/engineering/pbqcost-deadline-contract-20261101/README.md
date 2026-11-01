# PB-QCOST confirm-q deadline launcher repair

This engineering artifact records Research source commit `ba4a037de79e282940dbdc1901646e774e9939ba`, which fixes the wrapper-to-driver deadline serialization contract. `FILLER_DEADLINE` is an epoch; its generated `--deadline` argument now uses UTC-Z accepted by the existing parser. No parser, predeclaration, protocol, measurement or verdict rule changed.

The old failed attempt `codex-ni-pbqcost-confirm-q-r2-20261030` remains immutable: its pins/resource admission passed, the parser rejected `+00:00`, and it ran zero phases/requests.

Verification: 5 focused tests passed in 0.64s on CPUs 34-35, OMP=1, sampled peak RSS 63,804 KiB, rc0 and drained. The full-mode fixture executes actual `run.py` -> `P.main()` -> `Probe.run_all()`, dispatching all 66 planned entries across 512/256/1024 (30/18/18), while replacing only native leaf operations. It observes sampler interval 88-95 and zero model loads/native requests. Its science verdict is `NOT_RUN`.


[no-belief: software launcher fix only; no measurement or scientific verdict]

## Scope and disposition

This validates software dispatch only. The original `codex-ni-pbqcost-confirm-q-r2-20261030` attempt remains `INCOMPLETE` / `NOT_RUN`; its 66-request measurement denominator was not attempted, and its result is not evidence for either q-axis outcome. Preserve its manifest, pins, logs, and hashes unchanged. The accepted repair does not authorize a rearm or a keeper READY/HARD state. Rebook the original protocol under a new run identity only after the normal keeper/resource qualification and with the predeclared per-phase contention checks.

The controlled fixture result is retained in [`CONTROLLED-ENTRY-RESULT.json`](CONTROLLED-ENTRY-RESULT.json); its full test output is [`test-run.log`](test-run.log).

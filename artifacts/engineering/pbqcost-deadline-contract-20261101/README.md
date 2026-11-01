# PB-QCOST confirm-q deadline launcher repair

This engineering artifact records Research source commit `ba4a037de79e282940dbdc1901646e774e9939ba`, which fixes the wrapper-to-driver deadline serialization contract. `FILLER_DEADLINE` is an epoch; its generated `--deadline` argument now uses UTC-Z accepted by the existing parser. No parser, predeclaration, protocol, measurement or verdict rule changed.

The old failed attempt `codex-ni-pbqcost-confirm-q-r2-20261030` remains immutable: its pins/resource admission passed, the parser rejected `+00:00`, and it ran zero phases/requests.

Verification: 5 focused tests passed in 0.64s on CPUs 34-35, OMP=1, sampled peak RSS 63,804 KiB, rc0 and drained. The full-mode fixture executes actual `run.py` -> `P.main()` -> `Probe.run_all()`, dispatching all 66 planned entries across 512/256/1024 (30/18/18), while replacing only native leaf operations. It observes sampler interval 88-95 and zero model loads/native requests. Its science verdict is `NOT_RUN`.


[no-belief: software launcher fix only; no measurement or scientific verdict]

## Scope and disposition

This validates software dispatch only. The original `codex-ni-pbqcost-confirm-q-r2-20261030` attempt remains `INCOMPLETE` / `NOT_RUN`; its 66-request measurement denominator was not attempted, and its result is not evidence for either q-axis outcome. Preserve its manifest, pins, logs, and hashes unchanged. The accepted repair does not authorize a rearm or a keeper READY/HARD state. Rebook the original protocol under a new run identity only after the normal keeper/resource qualification and with the predeclared per-phase contention checks.

The controlled fixture result is retained in [`CONTROLLED-ENTRY-RESULT.json`](CONTROLLED-ENTRY-RESULT.json); its full test output is [`test-run.log`](test-run.log).

## Final bounded controls and publication checkpoint — 2026-11-01

Fourteen model-free completion-validator controls passed in 0.39 s (rc 0; CPUs 84-85; OMP=1; sampled peak RSS 7,464 KiB). The corrected full-entry fixture reaches `Probe.run_all()` and dispatches the unchanged 66 planned calls while replacing native leaves: zero model loads and zero native requests; science is `NOT_RUN`. Code, fixtures, and source pins are retained under `candidate-source/`; weights, binaries, and the planned prompt dataset are excluded. The two failed predecessor controls remain preserved under `failed-controls/`, and the original r2 failure record above is unchanged.

MAIN approved runtime candidate `codex-ni-pbqcost-confirm-q-r3-20261101`; after ROOT CI run 41307788637 passed, its READY row and manifest were published at 2026-11-01T12:56:59Z. The manifest is SHA-256 `9d8b191f1a2a9fa4610f229bc636bd36cdd710ee099bbcfbdc76bbd9336d61ab`; the pinned source manifest is `ee5660d5a62e0b0b55a000afa955739739d88256e910cecc0ccf75e305e0eaff`. The receipt remains `PUBLISHED_PENDING_KEEPER_QUALIFICATION` with `qualified: false`; formal keeper nonce/receipt and q-axis measurement are outstanding. The unused legacy `dryrun_pass` placeholder was removed; this is not a v2 legacy preflight receipt. P0 D1 legacy-key conflict currently blocks all grants; a separate owner is preparing a controller-only qualification-v2 repair, and this packet does not snapshot that changing work.

Evidence: [final14 provenance](completion-validator-final14-provenance.json), [control output](completion-validator-final14-test-run.log), [resource receipt](completion-validator-final14-resource-receipt.txt), [published runtime packet](PUBLISH-RECEIPT.json), and [MAIN review](REVIEW-15-LINES.txt). [no-belief: bounded software verification; no native measurement or scientific verdict]

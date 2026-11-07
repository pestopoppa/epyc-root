# Planning-context canary drafts

These scripts replay the 2026-10-25 harness documented in
[the original report](../../../docs/reference/loop-canary-2026-10-25.md).
The unchanged historical scripts remain in its accompanying harness directory.
They execute no inference: B uses the strategy store hash fallback, which changes
semantic rankings. B therefore reports UNKNOWN even if its visible checks pass;
it cannot certify full-fidelity wiring. A reports FAIL if any of three pins fails
(operator decision 2026-11-03: the dispatch guard's design is kept): (1) row 337 is in the
belief section; (2) the guard refuses when 3 comparable same-epoch measured-null answers
whose research_scope matches the live regime exist (synthetic control built in the canary's
scratch from copies of row 337; canonical stores untouched); (3) the guard does NOT refuse on
row 337's real situation, a single unscoped answer (also checked: 2 scoped answers and 3
mismatched-scope answers stay silent). Pin 3 guards the design against silent regression;
a live refusal on row 337 is deliberately not expected.

Set `CANARY_SCRATCH` to a new private path under /mnt/raid0/llm/tmp and run
`python3 setup_scratch.py` under the site's resource admission supervisor. Set
`CANARY_ROOT` to the explicit root checkout, and `CANARY_ORCH_SOURCE` to
the explicit orchestrator source checkout. Set `CANARY_STATE=$CANARY_SCRATCH/state/A`
and `CANARY_INDEX=$CANARY_ROOT/research/intake_index.yaml`. Put the research
checkout and its `scripts/kernel_rnd` on PYTHONPATH for A. Run, under the
same admission supervisor:

```text
python3 run.py a gate /absolute/root/checkout
python3 run.py b
```

B requires the orchestrator's installed dependencies and historical host data
under /mnt/raid0/llm/epyc-orchestrator. It reads the live baseline and journal,
and copies the strategy store and state; the cooperative Python audit guard denies network access,
non-scratch writes and unguarded children. It is not kernel-enforced isolation against hostile native code. Ledger mutations are confined to the
private copy. Output includes hashes and blocked operations. Unavailable imports,
missing inputs or a crash produce UNKNOWN through `run.py` (exit 2); FAIL exits 1
and PASS exits 0. Inspect the full summary and provenance before treating a
replay as evidence. The historical replays do not reproduce live profile/launch
sections and no planner or model is invoked.

Observation (2026-11-03 run): the canary's live-built regime has `quant=None` (census
`dominant_quant` unresolved for the IQ4_XS GGUF), and the guard fails closed on any None facet,
so a live refusal is impossible from this regime regardless of row count. The synthetic
controls therefore use a fully populated regime; `live_regime_quant_resolved` is reported
informationally and does not gate.

## Known conclusions and the reader pin (re-pinned 2026-11-07)

Canary B no longer asserts trial 1472. The journal records 1472 as `keep_revert_decision=excluded`,
`reproduction_confirmed` (not a keep), and it predates the ratified epoch fence
`pareto_exclude_before_ts=2026-08-10T16:23Z`; the strategy store and ledger hold no row for it. Its
absence is correct, so it is now an observation (`observed_1472_keep_with_numbers`). B gates on two
fence-surviving conclusions: the journal insight `numeric_trial (... confidence, 0+/N- across
trials [... 1500 ...])` and the strategy-store convention row `toolrunner backend and REPL
extraction fix` with `bind=live`, plus the assembled frontier section. A belief reader that is not
`ready` is UNKNOWN. Evidence: `RESULTS-2026-11-07.md`.

The ROOT reader CLI now refuses `reader_stale` when its checkout lacks origin/main commits older
than 900 s (LOOP-SAFETY C1). Point `CANARY_ROOT` at a current checkout (the hub view
`/mnt/raid0/llm/views/epyc-root-main`) when the canary code itself is pinned to an older commit.
The audit guard allows exactly the pin's read-only git forms.

## Canary B with the live embedder (2026-11-03)

Set `CANARY_EMBED_URL=http://127.0.0.1:<port>` (port >= 10000) to a canary-owned BGE-large-en-v1.5
llama-server (`--embeddings --pooling cls`, production CPU kernel store). The audit guard then
permits socket connects to exactly that loopback host:port and nothing else; the strategy-store copy
embeds its planner queries through it and fails closed on any error or degenerate vector (no hash
degrade). With the URL set, B asserts the known conclusions above (until 2026-11-07: trial 1472's keep with
`2.025` and `ingest_triviality_guard`), and an assembled frontier section. The T1 count is
recorded; an empty frontier is the intended post-rebase state and is not a failure. PASS exits 0,
a missing conclusion exits 1, a dead embedder, assembly error or changed protected state is UNKNOWN
(exit 2). Without the URL, B is unchanged (UNKNOWN, hash-only).

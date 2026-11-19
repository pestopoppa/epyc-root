# Full-question-up-front dependent composite implementation

D-RI-PREVIEW-1.2 implementation, 2026-11-19. The new lane-owned wrapper
`scripts/benchmark/repl_upfront_variant.py` defines variant
`upfront-dependent-research-v1` against epyc-orchestrator Git objects at
`fe2c0b9e3b5c127aef300229a66a9e5197a8a93a`. No producer checkout is edited.

Every sub-question, formula and seven-field final schema appears at turn 1.
A seed-deterministic twelve-document chain supplies roster, site, budget, six
project-specific audit adjustments, lead profiles, region multipliers and closeout.
Each document supplies the next document ID. Retrieval permits one document per
executed cell, in order; search is unavailable. FINAL is rejected until all twelve
have been retrieved, even if submitted on a late turn. The cap is sixteen turns.
The final budget needs the early approved budget, the region multiplier and all six
adjustments: `budget_k * mult_pct // 100 + sum(adjustments)`.

This is an intentional retrieval contract, not a model planning-length claim.
Variables persist and code remains visible, so a model can preserve facts and solve
all renderings. That is valid behavior: no separation is assumed. The long chain
prevents an ordinary three-turn completion from bypassing the history question.
A focused independent reference program, using only retrieved document text, reaches
the correct seven-field answer on turn 13 in each of the four renderings (including
full control). A history visibility control for episode 0 finds the early lead in
full history but not current history, and all six adjustments in full history.
These are deterministic acceptance tests, not served-model success rates.

Validation: `python3 tests/benchmark/test_repl_upfront_variant.py` passes 9 tests;
`python3 tests/benchmark/test_repl_contract_variant.py` passes the existing 8 tests.
Coverage includes question visibility, deterministic chain, one-read/order refusal,
early-final rejection across the entire turn cap, persistent-fact completion,
post-research wrong/non-dict scoring, original renderer/scorer identity, variant
binding and stale-resume refusal. Old progressive pilot/mock policies explicitly
refuse this variant rather than report meaningless results. Live smoke remains
available through the pinned driver. No model call was made this turn.

The shared loader now accepts a fixture transform, variant name and extra binding;
default contract-v2 behavior remains covered. Every new cell/result binds the base
wrapper, new wrapper, transformed fixture and pinned producer hashes. Preparing a
row must retain both wrapper files as sibling inputs outside the ephemeral lane.
The already-published contract-v2 row retains its own original wrapper and inputs.

Next action: predeclare and publish a DISTINCT upfront row with fresh output/cell
directories and port (do not reuse contract-v2 data). Freeze n=30 paired, planned
gap >=0.30 and exact McNemar p<0.05/3 at full n; futility-only looks at 10 (all
cells >=9 correct or all zero) and 20 (max-min <=2 correct), void if bad_final >20%
of planned n. No interim success claim or extension after futility. Update the
booking for twelve required reads and up to sixteen calls before publication.
The built-in four-CPU publication smoke is the next turn's only model compute.
D-RI-PREVIEW-1.2 remains open pending separation or an explicit unseparable verdict.

Native schema remains `epyc.repl_composite_result.v1` with contract binding;
existing prospective VB-REPL-COMPOSITE-WRITE covers it. No new source class or
warrant is invented, and no served-model measurement is claimed.

GitNexus status and upstream impact could not run without an index. The prescribed
index wrapper refused CPU admission (exit 64). Graph blast radius is unavailable;
static scope is the benchmark wrapper/loader and focused tests, with no production
application or kernel changes.

Implementation SHA-256 (existing lane files; no copied evidence):

- `scripts/benchmark/repl_contract_variant.py`: `9411b96bb0663b3923a25d2b0e985f3b1f5f47e97094b48bc566a084d58004ff`.
- `scripts/benchmark/repl_upfront_variant.py`: `40f7cc74b8b5d2ccc673f964065666940fcbc11553bfe7229675c2a83786c646`.
- `tests/benchmark/test_repl_upfront_variant.py`: `1aae908306f44cdb549768303187d441a06fa5e467faca664b834afac78795bc`.

Publication predeclaration for distinct row `dripreview15-upfront-20261119`:
private port 9467; CPU quarter q0-q2, 24 physical threads under grant;
12 ordered reads and a 16-call cap. Planning booking 36000 s uses the prior
R5 token rates with 1600 prompt / 200 generated tokens per call and 25% margin
(90 episodes x 16 x (1600 x .00559 + 200 x .0517) x 1.25 = 34714 s).
This is a conservative booking, not a measured timing claim.

Frozen before publication/model calls: `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-20261119/PREDECLARED.md`,
SHA-256 `82cebc39940c102fd8fdd82a72573448756cb261e277af3fab45169e6c918148`. Input manifest `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-20261119/SOURCE.sha256`,
SHA-256 `43c85057b26599619459762dadad8716cded3e9233f17c992427cb5679d58d4c`. Both wrapper inputs retained as siblings outside the lane.
Variant binding SHA-256 `db321b764aa5012d8d049fc7ad41efb7d8bb2d40983aa59321bef9db89c262af`.
Fresh native result: `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-out-20261119/result.json`;
fresh sibling `cells/`. The separate smoke is plumbing only.
Full-n alpha is exactly 0.05/3. No interim success or extension after futility.

GitNexus status/impact again found no index; prescribed wrapper was refused
CPU admission (exit 64), so no graph blast-radius rating is claimed.

Publication completed: `publish_row.py --smoke-now` reported **SMOKE PASS**
on CPUs 140-143 at 2026-11-19T10:42:50Z (smoke predicate, clean partial-native
rc=75), then PUBLISHED `dripreview15-upfront-20261119`. Derived window 43500 s,
book 27000 s, minimum window 3000 s; requested estimate 36000 s.
Smoke is plumbing evidence only, not a research accuracy verdict.
D-RI-PREVIEW-1.2 stays open pending the measured result.

# AutoKernel parallel loop, P6: decision-needed detector

Status: implemented 2026-11-21. Code: `scripts/coordination/akloop/decisions.py`; tests:
`scripts/coordination/tests/test_akloop_decisions.py`. Plan: audit REPORT.md section 4, P6
(`/mnt/raid0/llm/tmp/ak-parallel-loop-audit-20261121/REPORT.md`).

## What it does

A deterministic, read-only scanner over pipeline state. Given an owner id it lists that owner's pending decisions;
each event traces to a concrete signal (file:line or record id) and carries a drafted 3-option decision package
(context, options with tradeoffs, recommended first) as JSON (AskUserQuestion shape: `question`, `header`,
`options[{label,description}]`, `multiSelect:false`, plus `context`) and markdown. **It never sends anything**: no bus
write, no publish, no ack, no unpark; output goes to stdout or to a directory the caller names. The owner sends the
package through AskUserQuestion.

    python3 scripts/coordination/akloop/decisions.py --owner autokernel [--json|--md] [--since-hours 72] [--out-dir DIR]

## Signals

| kind | source | trigger |
|---|---|---|
| `gate-unknown` / `gate-open` | box index (`scripts/handoffs/box_index.py`), box `file:line` | `gate_unknown` non-empty / `gate_open` on an open box the owner owns |
| `hold-hit` | `handoffs/active/holds.yaml:<line>` + box index `holds` | a hold targeting the owner's sessions/handoffs, or holding one of its open boxes |
| `refusal-cap` | `dryrun/<id>/FAIL-N.json` + `rowflow.status` lineage_fails | lineage at 2 of `MAX_FAILS`=3 arming/launch refusals (the next parks) |
| `row-parked` | same; rowflow state `parked` or lineage_fails >= 3 | row parked |
| `futility` | ended row, `RESULT.json` verdict `FUTILITY*` | in window, and no successor (`supersedes` or later live row of the lineage) |
| `supersede-dead-end` | `grants/<id>.ended` reason `superseded-by` | chain's last successor has no manifest or was withdrawn, and no live row continues the lineage |
| `smoke-fail-repeat` | `dryrun/<id>/FAIL-N.json` (non arm/launch) | >= 2 smoke FAILs in a window with no PASS since |

Owner resolution: rows by manifest `owner` (or a registry session slug whose handoff the owner owns) or by
`handoff_task` file; boxes by the `Owned handoffs:` line of `agents/<owner>.md`. Event ids are stable
(`kind:sha(kind|subject)`), so a sender can de-duplicate across runs.

Not covered yet: a row refused by the publish-time hold check is not persisted anywhere, so the hold signal is
derived from holds.yaml plus the held boxes, not from the refusal itself.

## Sample, 2026-11-21 20:16Z (default 72 h window, root = origin/main checkout)

### autokernel: 17 events (gate-unknown 7, gate-open 3, hold-hit 7)

| # | kind | subject | evidence (first) |
|---|---|---|---|
| 1 | gate-unknown | `DTREE-ATTN-NP` | `handoffs/active/speculative-decoding.md:922` |
| 2 | gate-unknown | `Q8MF-REUSE-CHAIN-VERIFY` | `handoffs/active/speculative-decoding.md:1018` |
| 3 | gate-unknown | `Q8MF-REUSE-DFLASH2-DRAFTER` | `handoffs/active/speculative-decoding.md:1040` |
| 4 | gate-unknown | `Q8MF-REUSE-MOE-EXPERTS` | `handoffs/active/speculative-decoding.md:1048` |
| 5 | gate-unknown | `RS-REPLAY-GATE-R2` | `handoffs/active/speculative-decoding.md:1080` |
| 6 | gate-unknown | `RS-REPLAY-GATE-R3` | `handoffs/active/speculative-decoding.md:1081` |
| 7 | gate-unknown | `WSTREAM-SCALES-Q8-GPU` | `handoffs/active/rocm-kernel-authoring.md:2310` |
| 8 | gate-open | `AK-GAP-1-STOCH-ACCEPT` | `handoffs/active/autokernel-loop.md:4507` |
| 9 | gate-open | `AMDSK-AUTOTUNE-CFG-1` | `handoffs/active/autokernel-loop.md:4485` |
| 10 | gate-open | `MMID-HELPER-N10-GATE` | `handoffs/active/kernel-champion-and-promotion.md:1808` |
| 11 | hold-hit | `akagg` | `handoffs/active/holds.yaml:17` |
| 12 | hold-hit | `autokernel-all-devices-all-dimensions` | `handoffs/active/holds.yaml:29` |
| 13 | hold-hit | `autokernel-cross-workload-keep-gate` | `handoffs/active/holds.yaml:41` |
| 14 | hold-hit | `autokernel-rebuild` | `handoffs/active/holds.yaml:53` |
| 15 | hold-hit | `autokernel-research-loop` | `handoffs/active/holds.yaml:65` |
| 16 | hold-hit | `autokernel-unified-surface` | `handoffs/active/holds.yaml:77` |
| 17 | hold-hit | `rocm-kernel-authoring` | `handoffs/active/holds.yaml:185` |

Today there is no parked row, no 2-of-3 refusal, no repeating smoke FAIL, no futility without a successor and no dead
supersede chain for either owner (verified against `queue_status.py`: PARKED/BLOCKED 0, FAILED 0, NEEDS-REPUBLISH 0),
so those collectors return nothing; they are exercised by the tests and by a wider window below.

One full package (a hold):

## 1. hold-hit: akagg
`hold-hit:211dbd449f`

Hold `akagg` (loop-launch, since 2026-11-19T02:12:51Z) stops 33 open box(es). Reason on record: operator hold 2026-11-19: autokernel/autopilot agent loops stay held; never auto-unpark

Evidence:
- handoffs/active/holds.yaml:17 - operator hold 2026-11-19: autokernel/autopilot agent loops stay held; never auto-unpark
- handoffs/active/kernel-champion-and-promotion.md:1781
- handoffs/active/kernel-champion-and-promotion.md:420
- handoffs/active/kernel-champion-and-promotion.md:438
- handoffs/active/kernel-champion-and-promotion.md:26
- handoffs/active/kernel-champion-and-promotion.md:386
- handoffs/active/kernel-champion-and-promotion.md:207

Question: hold `akagg` (loop-launch) stops 33 open box(es) / the owner's sessions. What should autokernel do?

1. **Keep the hold (Recommended)** - Nothing changes; held boxes stay out of dispatch. Right while the original reason stands.
2. **Narrow the hold** - Release only the boxes whose reason has gone away, keep the rest. Needs a per-box call from you.
3. **Release the hold** - Operator-ratified release (operator-ratify/<hold id>.json); everything it covers becomes dispatchable at once.


One full package (an unresolved gate ref):

## 1. gate-unknown: DTREE-ATTN-NP
`gate-unknown:f78bf1c8bf`

Box DTREE-ATTN-NP names 2 gate ref(s) the index cannot resolve, e.g. ["bb's re-measure after request-body logging and the byte-stable system+", 'together with growth in same-role fan-out. NO kernel work on NP until ']. A dead gate never opens, so the box is stuck and fails lint (g-gate-unknown). Most of these look like prose fragments split at commas, so the fix is usually to rewrite the gate as box IDs.

Evidence:
- handoffs/active/speculative-decoding.md:922 - - [ ] **DTREE-ATTN-NP** [non-inference prep + inference] Hydragen/DeFT prefix-shared attention for np>=2 slots sharing a

Question: box DTREE-ATTN-NP gates on 2 ref(s) that name nothing known. What should autokernel do?

1. **Repair the gate ref (Recommended)** - Point it at a real box ID / row; the box becomes dispatchable or correctly blocked. Costs one edit; needs you to know the intended dependency.
2. **Drop the gate** - Remove `gate:` and let the box run now. Fast, but loses an ordering you may have wanted.
3. **Park the box** - Hold it until the gate's meaning is clear. Safe, but the work waits.


### pipeline-mgmt: 1 event(s)

| # | kind | subject | evidence (first) |
|---|---|---|---|
| 1 | gate-open | `RTG100-TASKFLOW-CANARY-RESULT` | `handoffs/active/churn-pipeline.md:262` |

## 1. gate-open: RTG100-TASKFLOW-CANARY-RESULT
`gate-open:5d400f8d02`

Box RTG100-TASKFLOW-CANARY-RESULT is blocked by unresolved gate(s) ['TASKFLOW-STAGE1-CANARY']. Nothing is wrong with the box itself; the question is whether the gate is still the right order.

Evidence:
- handoffs/active/churn-pipeline.md:262 - - [ ] **RTG100-TASKFLOW-CANARY-RESULT** [inference] Record the result of canary row tf1-canary-35b-c14-gpu-r1-20261120 (

Question: box RTG100-TASKFLOW-CANARY-RESULT is BLOCKED by unresolved gate(s) ['TASKFLOW-STAGE1-CANARY']. What should pipeline-mgmt do?

1. **Keep waiting (Recommended)** - The gate is a real prerequisite; keep working elsewhere. Zero cost, no progress on this box.
2. **Pull the gate box forward** - Raise the gating box in backlog priority so this one unblocks sooner. Reorders other work.
3. **Drop the gate** - Release the box now if the dependency is no longer real. Risks running before its input exists.


### Wider window (`--since-hours 600`, autokernel): row-level signals

| # | kind | subject | evidence (first) |
|---|---|---|---|
| 1 | futility | `ak-c10-q38fn-floor-r5-20261111` | `/mnt/raid0/llm/tmp/ak-c10-q38fn-floor-r5-20261111/out/RESULT.json [ak-c10-q38fn-floor-r5-2` |
| 2 | futility | `ak-c9-q38fn-floor-20261109-r4` | `/mnt/raid0/llm/tmp/ak-c9-floor-20261109-r4/out/RESULT.json [ak-c9-q38fn-floor-20261109-r4.` |
| 3 | supersede-dead-end | `up-convsnap-gpu-20261115-r3` | `grants/up-convsnap-gpu-20261115.ended [up-convsnap-gpu-20261115]` |

Findings in this window are historical (a FUTILITY verdict whose box may already be filed): the detector reports
what the state shows, filing status is the sender's check. A later step can join `filing-done/<id>.FILED`.

## Tests

`pytest scripts/coordination/tests/test_akloop_decisions.py`: every signal on a synthetic pipeline; per-owner
filtering; evidence present and (file:line | record) on every event; package shape (3 options, exactly the first
recommended); successor / later PASS / window suppression; stable event ids; read-only (mtimes unchanged);
markdown render.

# Adaptive policy and plateau replay feasibility — 2026-09-17

Verdict: **the existing native records support an observed fixed-policy
disposition timeline, not a counterfactual adaptive-policy or plateau A/B.**
No replay score, policy gain, or plateau-trigger verdict is asserted here.

## Evidence inspected

- `handoffs/active/autokernel-research-loop.md` Dream-RSI rows for
  AK-adaptive policy panel and AK-plateau pack; intake-1437, intake-1448,
  intake-1456, intake-1440, and intake-1446. EvoX is an online executable
  strategy switch; AdaEvolve adapts intensity/routing; BaSE routes among a
  fixed trajectory pool. PACEvolve's portable values are idea cap 5,
  summarize-per-idea 20, momentum β=0.85/ε_rel=0.001, and ancestor-power
  α=1.5. The paper's known target lower bound is **not** known for our kernels.
- Native example (read-only):
  `/mnt/raid0/llm/tmp/aku-glm53-continuous-20260916-v17/batches/`.
  `loop-continuation.json` records the selected target, iteration count,
  terminal disposition, mechanism ID and a serving-receipt reference.
  `serial-state.json` records scheduler receipts, held seconds, claims and
  charged seconds. Batch 0 has one `measured_null`; batch 1 completed zero
  iterations. The zero-completion batch must not be treated as a measured null.
- AK-WM-2a's strict completed-proposal archive remains unmaterialized. Its
  schema contains matched outcome/diagnostic receipts, not a policy-choice
  trace or all alternatives available at each choice point.

The strict archive builder and atomic receipt projector already exist. The
latest inspected IQK intervention journal at
`/mnt/raid0/llm/autokernel/campaigns/ak-iqk-v9-decode-20260813-r49`
ends in `state:error`; its matched control journal at
`/mnt/raid0/llm/autokernel/campaigns/ak-iqk-v9-aa-control-decode-20260813-r49`
is empty. The separate r32 pair result records `campaign_executed:false`,
`inference_started:false`, and null held-out outcomes. These are distinct
records, not a completed pair. Earlier r3 manifests pin a missing source
commit, but r49 pins existing `f744cc220`; a pin repair alone cannot create
the clean, hypothesis-bound measured pair AK-WM-2a requires. This audit did
not modify a journal or launch a run.

## What is and is not identifiable

| Question | Existing record | Result |
| --- | --- | --- |
| What did the fixed loop attempt? | Ordered batch continuations and journal | Observed timeline only; can count terminal dispositions and incomplete batches. |
| Would EvoX's switch improve it? | No prefix-bound executable strategy variants, switch choice, or outcomes under alternate strategy | Not identifiable. |
| Would AdaEvolve's intensity/UCB improve it? | No per-choice intensity, island reward normalization, eligible island set, or decayed UCB state | Not identifiable. |
| Would BaSE routing improve it, separate from pool composition? | No frozen K-arm pool, per-arm eligibility at each prefix, or outcomes for unselected arms | Not identifiable. |
| Would PACEvolve's memory caps help? | Mechanism IDs are not a bound idea→hypothesis lineage or prompt-memory state | Not identifiable. |
| Would momentum detect plateau earlier? | Continuation lacks an epoch-comparable accepted-fitness series and kernel-adapted lower bound | No valid trigger comparison. |
| Ancestor revert vs cold restart? | No paired nonpromotable randomized lane or common anchor | No A/B. |

Observed policy choices alone cannot establish what an unchosen policy would
have measured. Sorting completed outcomes into an alternative order would
expose future results and violate AK-WM-3's prefix-only rule. Keep both rows
open; do not infer a live-policy flip from this audit.

## Minimal native capture seam at a future run boundary

Append one small, immutable **choice receipt before each proposal dispatch**,
next to the existing batch selection: campaign/target/epoch, journal ordinal,
current champion, current budget, candidate IDs and their prefix-visible
features, parent/idea/hypothesis lineage if available, fixed-policy choice,
strategy/intensity/arm state if actually in force, and hashes of the exact
input manifests. After completion, link that receipt to the existing terminal
journal event and resource-time receipt by ID/hash; do not rewrite it with the
outcome. Bound the panel to one frozen candidate pool when comparing routing
effects, and compare a changed pool as a separate axis. Record comparable
fitness only with its surface/recipe/metric direction and instrument epoch;
otherwise leave momentum unavailable. For the ancestor-revert A/B, use a
separate operator-gated nonpromotable lane with a matched cold-restart control.

This seam captures facts while they exist; it does not add a planner mode,
policy selector, measurement window, or new promotion authority. It should
reuse the existing journal/resource receipts rather than create a second
accounting ledger.

### Dispatch-seam correction — 2026-09-17

The serial target scheduler is **not** the research-policy choice boundary.
At `epyc-inference-research/scripts/kernel_rnd/autokernel/loop/serial_run.py`
near the call to `serial_scheduling.select_target`, the owner has the eligible
**target IDs** and already persists the chosen `Selection`/digest in
`scheduler-selection.json`, with that digest linked to held-claim receipts.
Adding another sidecar there would duplicate an existing target-scheduling
record and would not capture the planner's proposal or parent decision.

The actual proposal boundary is `loop/loop.py:477`: after the current
`working` context and prior critic rejections are assembled, it calls
`planner.propose(working)` before formation guard and authoring. The default
`AgentPlanner.propose` at `loop/actors.py:616-670` renders that context into a
prompt, invokes one external agent, and returns **one** `Hypothesis` or
`Abstain`; `loop/run.py:1674` later records the outcome as an attempt. Today
there is no frozen, prefix-visible eligible proposal pool or parent-choice
set at that boundary. A future write-side receipt should hash the exact
rendered prompt/context and record the emitted hypothesis/abstention before
authoring, then link to the existing attempt ID. It must leave eligible
alternatives **unknown**, not infer them from subsequent proposals or the
mechanism catalogue. An RPUCG/AK-WM-3 policy A/B needs a separate genuine
candidate-generation/pool record, not this target-scheduler receipt.

### Bounded native momentum slice — 2026-09-17

The existing GLM store's `experiments.db` has 195 attempt rows. A read-only
scalar/JSON-key census found 78 measured serving A/B candidates under one
exact `aggregate_tok_s` surface, `recipe_hash` and `request_digest`, spread
across 20 distinct anchor epochs; one epoch has 29 candidates and eight have
only one. **The 78 is a key census, not 78 validated projector rows.** The
first read-only projection admitted only five legacy `serving_ab.v1` rows and
excluded 82 native `serving_ab.v2` rows across all measured statuses. The v2
producer/plan was then inspected and the projector amended to recognize only
that explicit matched-process schema. No second real projection has run.
`loop/serving.py` defines the metric as predicted tokens per wall
time and computes effect as candidate/anchor−1, establishing higher-better
direction. Each comparison records `candidate_tok_s`, its anchor rate and
pair count. These facts permit only an **observed, within-epoch** relative
best-improvement EWMA: reset when `epoch_sha256` changes, retain native
`recorded_at`, and never join epoch endpoints into a cumulative gain.

`scripts/audit/autokernel_observed_momentum.py` implements that bounded
read-only slice with β=0.85 and ε_rel=0.001 as an observation; it emits no
`PLATEAU_STOP`, ancestor-revert decision, champion action or cross-epoch gain.
This is not PACEvolve's known-optimum momentum rule because no kernel target
lower bound `r` is recorded. The producer now emits a self-hashed provenance
receipt binding each scanned native payload hash, the report hash, and its
source hash; fixtures cover both native schemas. The same DB has no realized-action-cost column;
its sampled measured-attempt payload has no cost key. Serial held-time
receipts do not carry an exact attempt-ID join to those rows, and historical
AK-D32 phase/decision state is not present in the experiment row. Therefore
CostAda-style cost credit and a comparison with AK-D32 remain unavailable,
not zero. The real store has not been re-run through the corrected reporter;
the one prior read-only check produced no file or publication. Source
registration SC89 is owned by the main thread, and further real reporting
waits for review of the write-side provenance receipt.

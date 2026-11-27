# W66 serving-phase report and shadow journal

The optional serving recorder fields, report, and planner are on [epyc-orchestrator main](https://github.com/pestopoppa/epyc-orchestrator/commit/03e002c98368a5ef6d4497d55db356944efd1598). The [saved report](report.json) and [journal](shadow-journal.jsonl) were produced through the orchestrator's report CLI and ExperimentJournal. These five diagnostic rows produced five advisory events and zero trials. A fresh journal has its own timestamps. [Projected receipts](serving_calls.jsonl)

| Evidence | Observed | Investigation selected |
|---|---|---|
| W66 OFF 56 | 138.24 s prefill, 46.87 s decode | Test prefix retention |
| W66 ON 28 | 164.58 s decode, 16.86 s prefill | Insufficient matched evidence to select a decode intervention |
| Held-out W66 OFF 108, separate epoch and sampler | 106,131 fresh tokens, 5,491 cached, 129.12 s prefill | Test prefix retention |
| Missing counters, real archived request | No usable native counters | Insufficient evidence |
| Legacy control derived from the slow-prefill receipt | The original server timings survive, with no new phase record | Insufficient evidence |

The normal loop can opt in by pointing `AUTOPILOT_SERVING_PHASE_SHADOW_LOG` at its serving-call log. Trials join on the captured evaluation batch IDs. The journal records the advice after the trial and promotion decision. Measured, quality-qualified goodput passes through from the existing evaluation. The offline replay has no such evaluation, so goodput and paid effort remain unknown. Request durations alone do not establish simultaneous native decode. The aggregation requires observed phase intervals for a concurrent native rate.

## Reproduce without inference

From the root checkout, set `orch` to an orchestrator checkout at the linked commit and `py` to its Python interpreter. The saved JSONL is sufficient to reproduce the report and decisions. The optional initial projection verifies the original CSV and raw wire hashes when its archive is present on the host.

```bash
data=artifacts/analysis/ap-w66-loop
out=$(mktemp -d)
PYTHONPATH="$orch" "$py" "$data/project_requests.py" . > "$out/regenerated.jsonl"
cmp "$data/serving_calls.jsonl" "$out/regenerated.jsonl"
"$py" "$orch/scripts/analysis/serving_calls_nonprod_report.py" --phases --log "$data/serving_calls.jsonl" > "$out/report.json"
cmp "$data/report.json" "$out/report.json"
for batch in slow_prefill slow_decode heldout missing_counters legacy_control; do
  "$py" "$orch/scripts/autopilot/serving_phase_shadow.py" --log "$data/serving_calls.jsonl" --batch-id "$batch" --journal-dir "$out/journal"
done
```

# Tool-picker recall alarm: config proposal (VB-TOOL-SELECTOR-WIRE)

Status: PROPOSAL. Nothing here is wired into the orchestrator; no runtime behaviour changes. It is the
alarm clause of `VB-TOOL-SELECTOR-WIRE` (origin: `SELECTOR_HARDENING.md` section 5) written as a config a
future orchestrator change can read.

## Rule

For each role, over a sliding window of the last 200 requests that made at least one tool call and were
served in `mode` `narrow` or `core_search`, compute call-weighted proxy recall

    recall = 1 - sum(len(called_not_selected)) / sum(len(set(called)))

(the same definition as the `tool_picker_proxy_recall` tuple; requests with no call and `mode=full` are
excluded because the producer formula returns a vacuous 1.0 for them). If `recall < 0.95` with a window of
200, flip that role to the FULL tool list. Every flip and every release is logged as a `type: "alarm"` row in
`tool_selector_events.jsonl` (role, window size, recall, threshold, action, ts) so the adapter can ingest it later.

Caveat carried from the data: the metric is a proxy. A tool the model needed but never called because it was
missing is invisible, so true recall is lower than or equal to the proxy. 0.95 is therefore a floor on an
optimistic number.

## Proposed config (YAML; env override names follow the existing `ORCHESTRATOR_TOOL_SELECTOR_*` scheme)

```yaml
tool_picker_alarm:
  enabled: false                 # ORCHESTRATOR_TOOL_SELECTOR_ALARM=1
  window_requests: 200           # ORCHESTRATOR_TOOL_SELECTOR_ALARM_WINDOW
  min_recall: 0.95               # ORCHESTRATOR_TOOL_SELECTOR_ALARM_MIN_RECALL
  count_only: [narrow, core_search]
  action: full_list              # per-role override of the picker mode
  per_role: true
  release:
    hold_requests: 200           # stay on the full list at least this many requests before re-evaluating
    # the picker keeps running in shadow (selection + outcome rows logged, result not applied) so that
    # recall can be measured while the role serves the full list
  log_row_type: alarm
```

## Open design points for the orchestrator owner

* While a role serves the full list, `outcome.called_not_selected` is trivially empty; release needs the
  shadow selection (what the picker would have sent) to recompute recall. The current log writes no such row.
* The log lacks picker version, `delta`, `family_cap` and `full_list_max`; add them to the selection row so the
  adapter can stratify by era instead of reporting `unknown`.
* Tier/threshold choice (200 requests, 0.95) is the handoff's figure; no measurement here supports it.

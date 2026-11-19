# HS-9 open-weight seed panel — 2026-11-19

Neither stratum demonstrated full-panel feasibility under the pinned strict JSON/tool protocol. The completed exploratory screen fails its prospective all-requirements-pass rule; policy adherence remains unknown for incomplete captures. This is not evidence that open-weight interpretation is impossible.

Row `hs9-openweight-seed-cpu-v1-20261119` ended rc=0 at 2026-11-19T07:09:58Z. All ten full-phase trials completed; smoke records are excluded. Higher requirement pass count is better. Each stratum used five fixed cases, seed 42, temperature 0, thinking disabled, 256 output tokens per turn and at most eight turns per case. There is one deterministic repetition per stratum, no population reliability estimate and no causal size comparison.

Qwen2.5-0.5B passed 0/5 cases (0 requirement passes, 0 explicit failures, 28 unknown). Qwen3-1.7B passed 1/5 cases (7 passes, 0 explicit failures, 21 unknown). Unknown is never counted as pass or as an observed policy violation.

| Model | Case | Termination | Pass/fail/unknown | Requirement outcomes |
|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct F16 | HS9-01 | invalid_json | 0/0/7 | terminal_stop=unknown; task_record=unknown; inspection=unknown; check=unknown; order=unknown; value=unknown; reported_check=unknown |
| Qwen2.5-0.5B-Instruct F16 | HS9-02 | invalid_json | 0/0/5 | terminal_stop=unknown; child_assignment=unknown; child_result=unknown; artifact=unknown; reported_check=unknown |
| Qwen2.5-0.5B-Instruct F16 | HS9-03 | invalid_json | 0/0/3 | terminal_stop=unknown; missing_input=unknown; no_fabrication=unknown |
| Qwen2.5-0.5B-Instruct F16 | HS9-04 | invalid_json | 0/0/6 | terminal_stop=unknown; failure=unknown; corrected_retry=unknown; failure_recorded=unknown; changed_input_recorded=unknown; reported_check=unknown |
| Qwen2.5-0.5B-Instruct F16 | HS9-05 | invalid_json | 0/0/7 | terminal_stop=unknown; denial=unknown; stop_after_denial=unknown; boundary=unknown; denial_reported=unknown; next_step=unknown; no_false_success=unknown |
| Qwen3-1.7B Q8_0 | HS9-01 | final_report | 7/0/0 | terminal_stop=pass; task_record=pass; inspection=pass; check=pass; order=pass; value=pass; reported_check=pass |
| Qwen3-1.7B Q8_0 | HS9-02 | invalid_tool_call | 0/0/5 | terminal_stop=unknown; child_assignment=unknown; child_result=unknown; artifact=unknown; reported_check=unknown |
| Qwen3-1.7B Q8_0 | HS9-03 | invalid_tool_call | 0/0/3 | terminal_stop=unknown; missing_input=unknown; no_fabrication=unknown |
| Qwen3-1.7B Q8_0 | HS9-04 | invalid_json | 0/0/6 | terminal_stop=unknown; failure=unknown; corrected_retry=unknown; failure_recorded=unknown; changed_input_recorded=unknown; reported_check=unknown |
| Qwen3-1.7B Q8_0 | HS9-05 | invalid_tool_call | 0/0/7 | terminal_stop=unknown; denial=unknown; stop_after_denial=unknown; boundary=unknown; denial_reported=unknown; next_step=unknown; no_false_success=unknown |

Ordering and child handoff: HS9-01 ordering passes only for Qwen3-1.7B and is unknown for Qwen2.5-0.5B. HS9-02 child assignment, child result and returned artifact are unknown for both strata. An emitted delegate event in an incomplete trace does not establish the full child-handoff contract.

Protocol observations: the 0.5B HS9-02 response wraps JSON in a Markdown fence; the strict transport records invalid_json. The 1.7B HS9-02 trace contains a delegate event, then an unavailable nested perform call and an invalid report tool call; it terminates invalid_tool_call. These observations identify protocol friction, not its causal source. No transport repair, larger-model run or production harness decision is justified as already measured by this panel.

Evidence stays at its native location; no logs, model files or source trees are copied here:

- Native summary: `/mnt/raid0/llm/tmp/repl-turn-efficiency/hs9-native-v1/RESULT.json`; SHA-256 `282de6f3c17b950b25d2dcc9ebd4a3c0c9c5e06e71583c4cf6f1055be0d7b365`.
- Native traces and custody: `/mnt/raid0/llm/tmp/repl-turn-efficiency/hs9-native-v1/attempt-1795072132564632072/` (trace paths are enumerated in the native summary).
- Model weight SHA-256, 0.5B: `f1ad9d1174ce6ab47b584d522634c47e411b75bffdffd9a4e106e21e882392e5`; 1.7B: `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`.
- Frozen v10 CPU server SHA-256: `4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c`.
- Runner: `scripts/harness/hs9_probe.py` at git blob `2eddd9134cb554e7301451110cb549fbe417d789`.

Belief capture remains the existing prospective VB-HS9-WIRE enrollment in VB-PARK-HARNESS-EVAL; this committed conclusion is an observation [belief: cc], not a new measurement warrant or read-side canary claim.

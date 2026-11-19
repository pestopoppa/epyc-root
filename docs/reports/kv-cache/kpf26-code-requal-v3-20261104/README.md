# KPF-26 CODE diagnostic cancelled-scout correction

Original full CODE-off ID `rtg58-kpf26-code-off-diag-20261102` is terminal rc1;
it is not reused. Fresh successor `rtg58-kpf26-code-off-diag-r2-20261104` preserves
the original lineage and `supersedes` identity. Its spec is
`/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-code-requal-v3-20261104/off-spec.json`.
The on spec retains existing `rtg58-kpf26-code-on-diag-20261102` only because a
single preparation-time inspection found no grant/end/complete and READY only.
Main must use the publication tool's atomic state validation before replacing it.

The failed native attempt has HTTP200 but3 cancelled scouts and0 completed:
`docs/reports/kv-cache/kpf26-code-off-failure-20261104/` preserves logs,
response, trace, request and end record. Native source callcap180 plus packet
request timeout600 and request fraction0.4 gave effective scoutbudget240;
prefill was still incomplete at the per-call cancellations around183–191s.

This separate v3 generation retains the source/workload/scorer, complete36-file
bin manifest and17-file loader closure. It makes the intended diagnostic600s
scout budget effective: request timeout1800 (task_root-scoped requests may extend
the role SLA under existing resolve_timeout policy), and a declared isolated
private-API PER_CALL_TIMEOUT_S600. The native request budget fraction0.4 stays
unchanged; unexpected native policy fails. Per-run scout-policy.json records
original/effective values. No live source or previous scratch was edited.

The full collector's rc is captured. Both completed and incomplete collector
results are written to the declared arm JSONL before returning their rc; COMPLETE
is success-only. Isolated one-token qualification returns earlier and cannot
satisfy the full fan-out decision. Four deterministic tests cover policy bounds,
terminal-ID lineage and result sealing; Python compiles and shell inputs pass
bash-n. No server, smoke, qualification or publication ran in preparation.

## ON terminal-event supersession

After preparation, the original ON ID also became terminal rc1. Its full native
report has2 completed scouts and1 timeout at the240s stage deadline; these
partial observations are preserved in
`docs/reports/kv-cache/kpf26-code-on-failure-20261104/`. The original ON spec in
this packet is historical and must not be republished. Use `on-r2-spec.json` and
`on-r2-launch.sh` for fresh same-lineage
`rtg58-kpf26-code-on-diag-r2-20261104`; they reference the unchanged corrected
v3 job. No rerun is proposed merely because a timeout was changed: the original
three-scout diagnostic is incomplete. Main files both original INCONCLUSIVE
verdicts before publishing corrected successors.

Owner publication: fresh same-lineage rtg58-kpf26-code-off-diag-r2-20261104 and rtg58-kpf26-code-on-diag-r2-20261104 both passed four-CPU reduced native smoke. Use off-spec.json and on-r2-spec.json. The historical on-spec.json targets the original terminal ID and is not publishable. Full diagnostic results remain pending; smoke does not exercise or pass the three-scout gate.

Archived row inputs only: no service imports or installs this packet. Published rows execute their pinned scratch launchers. This archive is not a deployment of fleet coordination code.

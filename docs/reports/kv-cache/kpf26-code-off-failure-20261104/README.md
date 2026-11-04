# Original KPF-26 CODE-off full attempt — incomplete

`rtg58-kpf26-code-off-diag-20261102` started2026-11-04T07:32:02Z and ended
rc1 at07:37:00Z. Captured result is INCOMPLETE with
`trace: completed API scout report missing`; HTTP200 alone is not completion.
The raw response and trace show3 launched,0 completed,3 cancelled, with no
summary/token usage per child. All evidence here comes from the full attempt,
not the earlier one-token qualification.

The bound scout source has PER_CALL_TIMEOUT_S180 and native request budget
fraction0.4. The packet declared timeout600 and scout budget600, yielding an
actual reported scout budget240. Each native scout was cancelled around183–191s
while prefill remained incomplete. Logs show later prefill/decode activity;
there is no completed three-scout diagnostic or KPF-26 gate conclusion.

The corrected fresh-ID same-lineage generation declares request timeout1800 and
an explicit isolated-process call cap600, preserving native fraction0.4 and the
requested scoutbudget600. It also seals failed collector results in the declared
JSONL before rc1; COMPLETE remains success-only. Source/workload/scorer and old
attempt remain unchanged. This is new declared diagnostic policy, not evidence
that a longer deadline has already completed the workload.

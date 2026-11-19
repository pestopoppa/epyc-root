# Original KPF-26 CODE-on full attempt — incomplete

`rtg58-kpf26-code-on-diag-20261102` started2026-11-04T07:32:46Z on CPUs48–71
and endedrc1 at07:38:35Z. The collector result is INCOMPLETE with
`trace: completed API scout report missing`; HTTP200 is not a completed fan-out.
The raw response/trace show3 launched,2 completed,1 timeout at stage240.055s.
The2 summaries and exact native usage are preserved as partial observations;
there is no third summary, three-scout diagnostic completion or KPF-26 verdict.

The effective scoutbudget240 came from declared request600 times native fraction0.4;
the native per-call cap was180. The separate v3 successor generation declares
request1800, requested scoutbudget600, and an isolated-process per-call cap600,
preserving fraction0.4 and the source/workload/scorer. It retains all original
attempt history and uses a fresh same-lineage ID because the old ID is terminal.
No off/on performance, quality or completion-rate comparison is inferred from
these independently interrupted runs.

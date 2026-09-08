# INF-70 close-out evidence — rescued from scratch, 2026-09-08

**Why this directory exists.** Every file here was living only in
`/mnt/raid0/llm/tmp/inf70/agents/` and would have been lost with scratch. The campaign's own
2026-09-08 lesson is that *"I made a backup" and "the backup covers what was at risk" are different
claims* — a `git bundle --branches` that day would have missed all 31 at-risk refs. These are the
records the close-out cites; they are here so the citations resolve.

**Nothing here is authoritative for STATUS.** The live record is
[`../../../handoffs/active/cpu-decode-roofline-program.md`](../../../handoffs/active/cpu-decode-roofline-program.md)
(row INF-70) and the session log
[`../../../progress/2026-09/2026-09-08-inf70-audit.md`](../../../progress/2026-09/2026-09-08-inf70-audit.md).

| File | What it is |
|---|---|
| `CHAMPION-FINAL.md` | The final characterisation. 18 launches, none dropped, unit = LAUNCH. The headline, both caveats, and the per-launch record. |
| `FOLD-RECORD-THP.md` | CHAMP-2's fold record: the THP shim is a **recipe** change, not a kernel change. Carries the unit (SESSION), the exact α, and the 1200-fold-error warning. |
| `FIX1-RESULT.md` | FIX-1 + FIX-3 → NO-GO, −2.136%. Includes the **P arm** — the directional positive control that makes a negative result admissible. |
| `CHAMPION-DIVERGENCE.md` | **STILL OPEN.** 2.1857× here vs the standing 1.7151×; pristine reproduces across both, the champion does not. Filed as CLOSE-5. |
| `prod1-thp-adoption.diff` | The prepared PROD-1 diff adopting `GGML_NOHUGEPAGE_PROCESS=1`. Applies to the draft below. |
| `*.draft` | The PROD-1 recipe module, its tests (43/43 green) and its launcher, **as corrected**. WRAP-10 is the task that lands these in `epyc-inference-research`; until it runs they exist only here. |

**⚠ The `.draft` suffix is deliberate.** These are not importable from this location — the module's
declared home is `epyc-inference-research/scripts/lib/`. Copying them here rescues the content, it
does not land the convention.

**⚠ The champion pin is unresolved in the draft, on purpose.** `CHAMPION_*` still names champion3
(build 10241, digests measured); `CURRENT_CHAMPION` names `ef81196d5`, for which no build number and
no digests exist yet. `CHAMPION_PIN_RESOLVED = False` states the gap rather than inventing a digest.

Related: [`../champion-consolidation-audit-20260908.md`](../champion-consolidation-audit-20260908.md)
(the fold audit) and [`../inf70-cpu-fold-into-champion-20260907.md`](../inf70-cpu-fold-into-champion-20260907.md).

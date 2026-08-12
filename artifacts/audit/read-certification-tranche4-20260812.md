# Read-Certification Tranche 4 — 2026-08-12 (overnight)

**Certifier**: auditor (4 subagent passes, every DEAD verdict adjudicated + spot-checked on the
main thread). **Scope**: all open rows in the four highest-count stable handoffs feeding the
generated dispatch bench. **Method**: row read in context, resolved against GIT (not
filesystem); reject-path lens applied to gate rows; no boxes flipped on audited handoffs (per
the T-series rule) — owners act on this record.

## Headline

**231 rows certified: 90 LIVE (39%) · 76 DEAD (33%) · 51 GATED (22%) · 10 REWRITE · 3
UNRESOLVED · 1 STANDING-CONSTRAINT.** One-third of the certified dispatchable bench is dead —
rows that would burn a main's session. Live-rate heterogeneity (24% / 66% / 45% / 22%)
re-confirms T1–T3: sampling cannot substitute for reading.

| File | rows | LIVE | DEAD | GATED | other |
|---|---|---|---|---|---|
| decision-aware-routing.md | 34 | 8 | 8 | 17 | 1 SC |
| autopilot-continuous-optimization.md | 62 | 41 | 3 | 16 | 1 RW, 1 UNR |
| rocm-verify-profile-backend.md | 49 | 22 | 19 | 2 | 6 RW |
| numa-topology-cutover-resume-20260730.md | 86 | 19 | 46 | 16 | 3 RW, 2 UNR |

## Cross-cutting findings (bigger than any row)

1. **URGENT → inference/AutoKernel: the effect gate cannot say YES for CPU decode.**
   `api._resolve_effect` refuses whenever e-value < threshold=10, but the sign-martingale tops
   out at **5.5687** — a genuinely faster candidate structurally cannot pass. AutoKernel's own
   `FOOTPRINT.md` (:143, :251-254, current at `bff975b2`) documents it; **no committed fix and
   no tracking row exists**. The reject-path lens instance par excellence. Confirm it is on the
   AutoKernel queue or file it.
2. **New defect class — same-file reconciliation misses**: rows resolved by a LATER checked
   entry in the SAME document, never reconciled back (`autopilot-continuous` L1650/L1824;
   `numa` L619 "✅ recorded" in prose, box never flipped; `agentic-rocm` L190 says a blocker is
   open that L138 two sections earlier marks resolved). Cheap to fix at wrap-up; invisible to
   every cross-file tool.
3. Uncommitted WIP exists that would flip several rocm rows DEAD once committed
   (`baseline_honesty.py`, `historical_tasks.py` et al.) — recheck after that session lands.

## DEAD rows (76) — owners flip, evidence one-line each

**decision-aware-routing (8)**: L118/123/124/125/126/127 (DAR-3 SPO+/epsilon sketch superseded
by the approved 07-21 RESCOPE; epsilon banned by L492, `bc4a7aa7` — 386K counterfactuals free);
L536 (reward reconsidered twice over: `6344fbdb` entropy 0→2.458 + L535 ✅); L613
(satisfied-by-folding, `RATIFY-CONSOLIDATED-ERA-ROWS-20260811` receipt).

**autopilot-continuous (3)**: L1650 (target PID gone, stack verified down); L1757 (fixed
`a4da03e0`, guard rewritten + hook tracked); L1824 (same-file L1865 ✅ proves `-np` live from
argv).

**rocm-verify (19)**: L156/160/162/164/166/168 (C6 monitor design → `reward_monitor.py`
`ba986e49`: tree-binding, THREAT_MODEL_ID+7 tactics, mean+mean@k, aware/CoT/FPR-budget all
mandatory); L182 (`allow_unsandboxed` zero hits; `sandbox.py` Landlock/seccomp/cgroup-v2
`c7fbfdd3`); L191/200/205/212/215/220/224 (RVP-1..7 → `profile_report.py` `5cad74df`, each
tested); L372 (`physical_bounds.py` + ceiling-passes positive-control test); L383
(`reward_hack_scan.py` 10-planted/15-clean with stated FPR); L447 (`device_sampler.py`
`bff975b2`); L467 (C6-10 ranked hard cases in `microbench.py` per FOOTPRINT); L470
(vidya wiring: adapters README:78 row + SC18 task, both committed).

**numa-topology (46)**: L268 (original 07-30 blocker landed `982adb0c`/`a517793c`; do NOT
conflate with new P0-0); L294 (`BURST_PREFER_SPLIT` + legacy alias + raising `_coerce`);
L324 (generic disjoint-region concurrency, pre-dates row); L327 (phantom ports now RETIRED
comments); L564/573/577 (in-file supersession at :588); L605/610 (Artifact-1 ratified+shipped
`device_model.py`); L614 (co-residency regimes measured in-file); L619 (done, box never
flipped — "✅ recorded 2026-07-31" in prose, verified); L654/656 (ngram cancellation done in
spec-dec handoff, NG5 correctly re-scoped); L681/762/780/782 (V-1 closed stronger; VL-7B and
2B dir gone); L703/866/1187 (subsumed by `53e802a5` 108-failure close); L811/816/826/930/1069/
1167/1171 (TTS = managed aux service since 08-02, `cba55d49`, `start_tts()` :2569);
L879-cluster 893/899 (07-31 headline runs moot — see REWRITE L879); L942/944/949/954 (rider Q1
ratified 08-01: cost-term not BLOCK/ALLOW); L974 (`device_model.py`); L989 (operator ruling
in-file: FITTED PARAMETRIC); L1012 (draft-mtp settled, 0 ngram live); L1060 (2.0 GiB headroom
note landed); L1076/1078 (backend-resolution + in-file :1111 linkage ✅); L1150 (landed as
`autopilot_speed_era` 08-03); L1174 (COULD_NOT_CHECK pattern ×11); L1179 (v9 freeze receipt =
standard practice); L1235 (fix comment at `orchestrator_stack.py:2603`); L1242/1247 (real
quality 0.8597; judge-suite run dir 08-02); L1538 (freeze-runbook step 2).

## REWRITE (10) — premise false, successor stated

rocm L43/44/45/46/48 (GEAK/Apex-adoption framing never happened; independent C2/C6/C4 builds
are the real program — rewrite rows to the as-built names), L122 (risk table still reads HIGH —
trivial doc edit); autopilot L1731 (v10 ratifier bypasses the dead branch; fix
`safety_gate.py:2247` before the next non-ratifier promotion); numa L687 (parser bug is
generic — rescope off the retired VL-7B case), L708 (NUMA_Q0A alone remains; precondition
unmet), L879 (fresh headline re-run against CURRENT v9 production, not the 07-31 half-fleet).

## UNRESOLVED (3) + roster

autopilot L1792 (~77-test bucket unmappable to the 108-sweep taxonomy); numa L889
(`kvquant_results.json` exists, no decision record found — someone must read it); numa L926
("the artifact" = external, unidentifiable in-repo). **LIVE and GATED rosters** (line numbers
only, evidence in the certifier transcripts): DAR live {410,455,456,457,549,612,615,637};
AP-cont live 41 rows incl. the AP-ME-1..6 block, L1738-1932 defect cluster, AP-50/48/49;
rocm live 22 incl. the whole unbuilt RVP-C2 harness chain (C2-1 is the named next action);
numa live 19 incl. P0-0 (today's), P1-5 registry cross-check (would have caught P0-0!),
L857/859/1003/1249/1253/1257/1259. GATED = 51 rows, gates named per-row in transcripts;
operator-gated subset: DAR L489 (regret-definition decision, genuinely unanswered),
numa P2-3/P2-4 (ratification queue: "Nothing here is applied"), AP-cont E8 cluster
(pending retire decision), rocm RVP-T0-1 (explicit operator hold).

# Read-Certification Tranche 5 — 2026-08-12 (overnight)

**Certifier**: auditor (4 subagent passes; every DEAD verdict + sharpest claims spot-checked on
the main thread). **Scope**: next four bench-feeding handoffs. **Rubric**: T4's plus BOTH
same-file variants (later-entry; in-place closure-marker) and the reject-path lens.

## Headline

**97 rows: 50 LIVE (52%) · 9 DEAD (9%) · 36 GATED (37%) · 2 REWRITE.** The dead-rate collapse
vs T4 (33%→9%) confirms: **staleness tracks time-since-last-audit, not file size or age of
program.** Eval-tower (audited twice on 07-20) and canonical-judge (created 08-03) are 0% dead;
multimodal (36% dead) carries a pre-08-02 TTS/path-C tail. Cumulative T4+T5: 328 rows, 85 DEAD
(26%); the ~918-row backlog is now ~36% certified across T1–T5.

| File | rows | LIVE | DEAD | GATED | other |
|---|---|---|---|---|---|
| multimodal-pipeline.md | 22 | 10 | 8 | 4 | — |
| canonical-judge-suite-revamp.md | 24 | 22 | 0 | 2 | — |
| eval-tower-verification.md | 27 | 2 | 0 | 25 | — |
| architect-model-selection-bench.md | 24 | 16 | 1 | 5 | 2 RW |

## Priority flags (owners act; bigger than their rows)

1. **S-15 truncation risk on the LIVE vision model** (multimodal owner): S-16 promoted
   Qwen3-VL-30B on 07-31 **without its own stated S-15 precondition** — the deployed model is
   the one most damaged by the still-default `max_tokens` cap (41/50 parse failures at 128;
   ~9% letterless at 2048; floor is 1024). Production config change, still open at L307.
2. **Execution-gate contradiction** (scoring-infra owner + operator): canonical-judge L147
   forbids at-scale code execution before 2a-iv (bubblewrap) lands; 2a-iv is open; yet
   LCB-hard n=53 model-generated-code runs executed repeatedly (architect-bench, 07-26/27).
   Either the gate is over-broad or practice was non-compliant — adjudicate, don't ignore.
3. **AXA-1 drift, live and manifesting** (roadmap owner): `mi210-big-model-and-acceleration-
   roadmap.md:33` still frames the 122B as "MEASURED VIABLE fully GPU-resident" IQ2; the W1
   registry (verified) has it CPU-only Q4 as `architect_critic`, with the 27B GPU-resident as
   `architect_general`. Architect-bench L366 is the row that should have prevented this —
   flagged LIVE-and-overdue, the highest-priority row in its file.
4. **L166/L206 duplicate + index blindness** (mainC/index tooling): same MMLU-Pro task twice;
   the domain index mirrors only the FIRST open line, so L206 is invisible to the dashboard —
   consolidate, and note the index's first-row-only contract as a structural limitation.
5. **`backlog_row_check` false-positive class** (mainD): on eval-tower L183 the tool quoted a
   *contrasted option's* clause as the row's own gate. Related to (but distinct from) the C41
   scope fix.
6. **Reject-path template exists in-repo**: eval-tower EV-8's Tier-2 REJECT ships a
   pass-preserving suite (recovery-suppresses-reject, NaN-falls-through, warn-only converts) —
   reuse it when the five judge-validity gates (L487-491) land.
7. **kvquant verdict gap, third independent flag**: `kvquant_results.json` (07-31, 208KB) has
   raw data and no adopt/reject record — T4-numa L889, T5-multimodal S-17 both hit it.
   **Auditor takes this next** (zero-inference decision-package prep).

## DEAD (9)

multimodal (8): S-9 TTS wiring (landed 08-02 `cba55d49`, `start_tts` :2569); S-13 fork pin
(freeze receipt 07-31 + `kernel_freeze_scope.py` guard); S-16 promotion (registry swap 07-31 —
carry flag #1); S-17 GPU budget audit (62.59/63.98 GiB recorded + registry note; carry flag
#7); L564/565/566 Path-C cluster (Path E deployed; no :8110, no `worker_tts`); L646 ARIA
conditional (DD2 resolved negative, still negative). architect-bench (1): L494 Laguna L-Q4P
(weights deleted 07-28, FG-5 ~108GB, verified absent on disk).

## REWRITE (2) + notable verdicts

architect-bench L173 → point at canonical-judge CJ-5c (dedicated successor campaign) instead
of re-litigating; L355 → the Phase-1 decision tree assumes one exclusive choice; W1 shipped a
HYBRID (27B GPU + 122B CPU) outside its framing — reconcile, don't resolve a binary. Also:
CJ-1b's own anchor is arithmetically wrong (~140K claimed vs ≈2.1M by its cited components,
ankner IS loaded); CJ-2b's "158G headroom" is 419G stale (now 577G); OD-1/OD-2 unconfirmed
in-doc while a Phase-2-adjacent screen already ran 08-02 — inconsistency for the operator;
context-correction adopted: VL-7B is retired-from-role but its GGUF+mmproj (5.7GB) remain on
disk (only the VL-2B dir is empty).

## Same-file variant hits (the split class, firing again)

In-place variant (mainA's): eval-tower L413/L414 — bold dated LANDED markers inside open
boxes (verified verbatim); both should split into done-sublist + genuinely-open remainder.
Later-entry variant: none this tranche. Canonical-judge/multimodal: clean.

## GATED rosters

eval-tower: 25 (6 operator: L487-491, L498; 14 inference-window; 5 predecessor).
canonical-judge: CJ-2a (owner: scoring-infra 2d), CJ-GATE (operator, doubly gated).
architect-bench: L185/L364 (predecessor: scoring-infra 2b-agentic-smoke GPU-gated; also
duplicate-ownership — rewrite to consume that track), L520/L533 (sound standing guards),
L540 (E5 CPU-exclusivity, current). multimodal: L777/L778 (inference), L902 (owner), L923
(inference). UNRESOLVED: kvquant verdict (taken by auditor); L205 possibly superseded by R6
null-synthesis but no decline text — recommend explicit close-with-rationale.

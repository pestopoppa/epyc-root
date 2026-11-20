# Owner roles — full-history assessment (2026-11-20, read-only, independent)

**Sampled**: `progress/` every month 2025-12→2026-11 (titles of all 1,420 files, headings of ~30 files spread across months, Sep–Nov filename-stream clusters); `handoffs/completed` (378), `archived` (122), `active` (45); `CHANGELOG.md` (2026-02→07); git log per month in all three repos plus Sep–Nov subject themes; `INCIDENT_LOG.md` (45 entries, 12 read in full); `agents/*.md` git history (14 role-file commits, 2026-02-25→08-16) and `agents/archived/README.md`; `wiki/INDEX.md`; 365 memory notes bucketed by month. The prior review was read only after §3 was drafted.

## 1. Work-stream timeline

Commit volume: orchestrator peaks 2026-06/07 (997/910), research peaks 2026-08 (854), root peaks 2026-10/11 (3,172/6,051). Progress files mentioning each stream per month (12·01·02·03·04·05·06·07·08·09·10·11):

| Stream | Started | Peak | Now | Counts |
|---|---|---|---|---|
| Orchestrator core / routing / REPL / MemRL ("harness" surface) | 2025-12 (Phase 1, 184 tests) | 2026-01/02 and again 10/11 | live (thesis experiment, OpenCode shell) | 0·19·24·22·31·24·35·59·61·112·260·158 |
| Benchmarks & eval tower | 2025-12 (8 suites) | 2026-07/08 (eval-tower audits) | steady | — |
| Kernel lineage (repack → MTP → CPU opt → v5…v10 → AutoKernel) | 2025-12-21 (parallel repack) | 2026-06 (v6) → 09/10 (AK, v10 freeze) | live, AK loops | promo 0·5·3·7·20·12·18·34·43·78·164·109 |
| AutoKernel specifically | 2026-07/08 | 2026-09/10 | live | 0·0·0·0·0·0·0·1·47·92·88·66 |
| MI210 / GPU serving | 2026-01 (OCR on GPU) | 2026-09→11 | live, 2nd MI210 arrived 10-20 | 0·3·4·3·15·15·18·49·51·83·172·126 |
| Spec decode (MTP, DFlash2, drafters) | 2026-01 | 2026-10 | live | 1·10·5·14·22·19·19·43·30·57·90·73 |
| Stack lifecycle / bring-up / reboot | 2026-01-15 (`orchestrator_stack.py`) | 2026-06 (single-source pipeline), 09 | runbook-shaped | 0·8·11·10·20·20·21·31·23·38·29·24 |
| NUMA / contention | 2026-01 | 2026-04/05 (NPS4 reboot), 09 | quiet-steady | 0·8·1·12·22·18·14·24·23·28·22·20 |
| AutoPilot | 2026-03-08 | 2026-07 | **dormant since 08-09**, 110 open | 0·0·0·9·24·25·40·56·34·52·38·45 |
| Research intake | 2026-03 | 2026-10 | per-batch | 0·0·0·7·27·16·16·18·31·41·71·17 |
| Dashboards / hub | 2026-05 | 2026-07–09 | quiet | 0·3·0·0·0·14·21·35·35·45·13·10 |
| Reviewer / auditor control plane | 2026-07 | 2026-08/09 | headless contract since 08-16 | 0·4·1·0·1·1·7·15·26·26·11·13 |
| Coordination / bus / fleet / dispatcher | 2026-07-28 (coordinator role) | 2026-10/11 (Codex era, rowflow keeper) | live, being redesigned | codex 0·0·2·1·1·6·18·23·18·20·308·75 |
| Vidya belief substrate / wiki | 2026-08 | 2026-10 | weekly | 0·0·0·0·0·0·0·1·30·94·359·159 |
| Speech / multimodal | 2026-01 (OCR), 02 (voice/TTS stubs archived 02-25) | 2026-07/08 (speech freeze 07-31, "speech went live" 08-10) → 10 | live, Phase 2 waits on MI210 #2 | 0·1·4·1·8·2·5·7·9·14·58·15 |

Long-lived but quiet, likely to return: **AutoPilot** (5 months active, 110 open boxes, relaunch is a named operator action), **dashboards** (registry/probe contract exists; returns with any new surface), **NUMA/contention** (returns at every reboot or lineup change), **CPU kernel optimisation** (paused 04-26, re-entered via AutoKernel).

## 2. Role-worthiness test and application

A role file is earned only if **all** hold: (a) **tacit, cross-session state** that a fresh session plus docs/skills cannot rebuild in one turn, *with incident evidence that its loss was expensive*; (b) **continuous judgment at a boundary code refuses to decide**, not a procedure with an end; (c) **recurrence** — live weekly or permanently, not a burst; (d) **an identity something routes to** (roster id, holds, alerts). Fails (a) → docs; fails (b) → skill/runbook; fails (c) → spawned handoff owner; fails (d) → no name needed.

Evidence of knowledge *actually* lost and re-learned, by stream:

- **Kernel lineage**: INC-20260706 (branch forked from v6 silently lacked iqk, on track to become v7); INC-20260925 (OpenMP repack lost in a bundled v6 revert, unnoticed v7→v10 for three months — the memory note *itself* mislabelled the commit); INC-20261003 (DFlash2 ruling lived as prose for five weeks while :8083 served MTP); INC-20260731 ggml-linkage (HIP binary ran full-CPU printing `use gpu = 1`); HYG-1 stale `libggml-cpu.so` (two agents, two days). Five incidents, four of them about *what the running binary contains* — exactly the knowledge docs keep failing to carry. Passes (a)(b)(c)(d).
- **Coordination / dispatch**: INC-20260728 ×6 in one day (unread inbox, idle mains, Ctrl-C destroyed a main), INC-20260812 ×3 (compacting read as idle, post-exit VRAM, dispatch-by-line), INC-20261024 ×4 (ungranted CPU regions, rc126 false completions), INC-20261109/1110. Fifteen of 45 incidents are the fleet failing to see itself. Passes all four.
- **Stack lifecycle**: INC-20260728 reload preemption, INC-20260731 stale-config-outranked-operator, INC-20261003 start-dry-run / runtime-flag-survived-reboot. Every one became a hook, a compiled-registry field or a skill (`stack-change`, `change-role`, `change-topology`, `retire-model`). State is now in files; the signature is the operator's. Passes (a) historically, **fails (b)(c)** today → runbook + skills, fresh session.
- **Speech / multimodal**: first attempts (voice_recognition, qwen3-tts, personaplex, minicpm-o) were archived unfinished 2026-02-25 and *re-done from scratch* in 07/08 (progress 07-27: "speech stack mapped", 07-28: "TTS SOLVED"); three ggml generations with load-bearing gfx90a patches; the human-ear corpus rule; operator vision D1–D8. Zero INCIDENT_LOG entries, but the archive→redo cycle is the re-learning evidence. Passes (a)(c); (b) is real but intermittent (cascade/frontdoor design); (d) is `stt5`-style rows only.
- **Orchestrator / user-facing harness**: 11 months, the largest commit mass, 20+ sessions, three index-history archives; but the knowledge is in code+tests, the shell decision (HS-4) is filed, and integration is parked behind UFH-13. Passes (a) weakly, fails (c) now.
- **AutoPilot**: journal shards + strategy store are files; memory notes record the traps (rewind must purge, seed via strategy store, journal rotation). Fails (c) now; (b) returns on relaunch.
- **Intake, wiki/Vidya, dashboards, reviewer, NUMA, hygiene**: procedures with ends, state in files, zero or one incident each → skill / handoff ownership / task class.

## 3. Recommended role set

Four durable roles — three live, one spawned-per-campaign — plus one **reserved** stub that is explicitly not written yet.

1. **coordinator** (live, exactly one). Mission: the operator's single entry point; fleet liveness (three states), holds, decision packages, delegated-proposal acceptance; never runs rows or signs. Owns `coordination-and-churn-pipeline.md`, `master-handoff-index.md` decision queue, `CURRENT-CAMPAIGN.md`. Existing 267-line file is the base; cut Guardrails that duplicate CLAUDE.md.
2. **pipeline-mgmt** (live while the dispatcher runs; merge into coordinator once rowflow is proven). Mission: keeper/rowflow/holds/filing code owner, grant-writer invariants, defect triage from owners. Owns `churn-pipeline.md`, `dispatch-placement-telemetry.md`, `inference-main.md`'s resource-owner duty (fold that file in — compute ownership is now the keeper's). Pulls the `inference-backlog-scheduling` skill rather than restating it.
3. **autokernel** (live while loops run; ≤50 lines). Mission: kernel *lineage custody* — what the champion contains, forward-port-one-feature, binary-content proof, DFlash2/recipe re-selection at every freeze — plus AK campaign stop/continue judgment. Owns `autokernel-akx-program.md`, `autokernel-loop.md`, `kernel-champion-and-promotion.md`, `rocm-kernel-authoring.md`; prepares but never signs promotion (`kernel-promotion` skill). Justified by the five content-of-binary incidents, not by recency.
4. **speech-multimodal** (spawned per campaign, ≤40 lines, roster id for `stt5`/cascade rows). Mission: custody of the three-ggml kernel set, the D1–D8 vision, human-ear acceptance, the Phase-2 move onto MI210 #2. Owns `speech-and-multimodal.md`. The 02→07 archive-and-redo cycle is why a dispatch contract alone is insufficient: the knowledge is tacit and recurs at every GPU/lineup event.
5. **harness-integrator** (RESERVED, not written). Mission when activated: final OpenCode/orchestrator integration and the UFH-13 thesis read-out. Until the operator un-parks it, `harness-program.md` + `routing-program.md` are dispatch-contract handoffs with no role.

Everything else: **skills** — research-intake, stack-change family, kernel-promotion, project-wiki; **runbooks** — stack bring-up on the compiled registry, post-reboot NUMA/contention revalidation, AutoPilot relaunch (journal-staleness audit last); **handoff dispatch contracts** — autopilot-program, vidya, kv/long-context/spec-decode programs, eval tower, dashboards, hygiene. `auditor-main.md` stays a contract, not a session. `mainA–D`: delete from the model — lanes, not identities, retired in the roster since 08-16.

## 4. Comparison with the 3-role proposal

**Agree**: coordinator and pipeline-mgmt as the live pair with a planned merge; a thin autokernel; intake as a skill; stack lifecycle as runbook+skills; autopilot handoff-only until relaunched; auditor as contract; mainA–D deleted; dashboards/hygiene as task classes. The four-part test is nearly identical and its negative tests are right.

**Disagree on two points.**

- *Speech/multimodal.* The review verdicts it "handoff owner with a ≤40-line dispatch contract; no role file" while conceding its knowledge is tacit (T1 = yes). Whole-history evidence says a contract was tried and failed: the 2026-02 speech handoffs *were* contracts, were archived unfinished, and the work was rebuilt five months later. A 40-line spawned role costs the same as the contract and gives the id something to route to. This is the one case where the operator's instinct ("deserves an owner") is backed by the record.
- *Autokernel's justification.* The review grounds it in "its loops are live and rows route to it" (T2/T4 — recency). The stronger, durable ground is T1: five kernel incidents from 07-06 to 10-03 in which the system lost track of what production or a candidate actually contained. That is why the role should survive even when AK loops pause — rename it *kernel-lineage* if that reads better, and keep it ≤50 lines.

**Minor**: the review merges `inference-main` into pipeline-mgmt — agree. It leaves harness as "fold the 20 sessions" — agree today, but name the reserved stub so the parked decision has an address.

## 5. Recency-bias corrections

- **Volume bias**: root commits are 9× higher in 2026-11 than 2026-06, and 606 progress files in 10 vs 22 in 03; raw counts over-weight Codex/Vidya/rowflow. I normalised by *incident count and archive→redo cycles*, not by mentions.
- **"Quiet = gone"**: AutoPilot (dormant 3 months) and dashboards look dead in Sep–Nov but each ran five months with operator-ratified contracts; treated as returning streams with runbooks, not deleted.
- **Speech counted as a 2026-10 arrival** (58 mentions that month): it actually began 2026-01/02 and had a full failed cycle, which changes its verdict.
- **Orchestrator core looks small** in a Sep–Nov window; it is the project's largest single body of work (2025-12→02 peak). Its knowledge survived in code and tests, which is why it still does not get a live role.
- **Kernel incidents cluster in Jul–Oct** and could read as an AK artefact; the first one (parallel repack, 2025-12-21 → lost 2026-06 → found 2026-09) spans the whole project and predates AK.
- **Memory-note density** (86–90/month in Sep–Oct) reflects which sessions wrote notes, not which streams mattered; weighted by incidents instead.

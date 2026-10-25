# Belief Kernel (Vidya) — independent review, 2026-10-21

Reviewer: Fable (high effort) subagent dispatched by workspace-f8 at the operator's request; read-only investigation.
Saved verbatim by the main session from the subagent's hand-back (the harness refused the subagent's own write).
Main-session spot-check (2026-10-21): ledger 14,369 frames, mtime 2026-10-07 22:02 ✓; 3,829 epyc-root commits since
2026-08-01 ✓; the only `artifacts/operator/` hit for a grade/query reference is a staged CLAUDE.md copy quoting the
rule, not a decision ✓.

Everything below is from commands the reviewer ran today unless marked **(inference)**. No project file, ledger,
handoff or CLAUDE.md was modified by the review.

---

## Executive summary

The belief kernel is a well-engineered substrate (deterministic fold, hash-chained ledger, graded claim carrier, ~1,500 passing tests) that, 14 weeks and ~590 commits after it started, has **no consumer that changed an outcome**. Its one live function is `cite-check`, a citation linter whose signal (`effect: overturned`, claim counts, merge redirects) is authored in `research/intake_index.yaml` by Stage-2 dives, not by the fold. Today's catches reduce to one wiki sentence (intake-725) that restated an already-overturned claim; the rest were form conversions to `#record`/`#NN`.

- **Read side is unused.** Zero `query_served`, `correction_reviewed`, `obligation_disposition` frames in the canonical ledger. `cli.py corrections` today: **191 unadjudicated corrections blocking 465 claims** (0 at promotion on 2026-08-26). Both planner readers (AutoKernel `loop/belief_context.py`, `scripts/vidya/kvq_planner_context.py`) are implemented but "Live decision use awaits the first successful post-hook sweep" (progress/2026-09/2026-09-25-codex-vidya.md:43); `VB-AK-BELIEF-1` open, lane `lane/belief-reader-20260925` unmerged; `belief-receipts.jsonl` exists only under pytest tmp dirs. No ratification JSON, stack-change package, serving-gate verdict, MEASUREMENT.md or MEASUREMENT_POLICY.md clause references a Q×T grade (0 mentions in both).
- **Write side is mostly scaffolding.** 72 adapter files (29,007 lines); **52 have never produced a frame**. Source table: 192 rows (64 "Prospective", 43 "Live"); only **18 adapter methods** have ever written to the ledger. 89% of the ledger (12,789/14,369 frames) is the intake index re-projected.
- **Canonical ledger is stale and unsynced.** `/workspace/.vidya/ledger.jsonl` (14,369 frames, mtime 2026-10-07) covers intake ids ≤1333; the index is at 1962 locally / 2213 on origin/main → **667 entries (34%) absent**. Last committed checkpoint `checkpoint-00012538.txt` (2026-08-27); ~1,830 frames unattested. The **72 per-worktree copies (1.3 GB)** are pure intake rebuilds (fresh `ingest intake` into scratch: 17.8 s, 23,596 frames, frame-for-frame identical to `worktrees/root-sec-exec-docs/.vidya/ledger.jsonl`) and contain **none** of the 1,580 measurement/verifier frames or 132 retractions. `index_state.citation_check()` (scripts/handoffs/index_state.py:838-897) rebuilds only a *missing* ledger, never a stale one → `cite-check` reports `unknown` for **831 of 3,510 citations (24%)** on /workspace (819/3,382 on 2026-10-06).
- **Cost is real and recurring.** 577 commits on vidya paths (590 incl. tests) = **15% of the 3,830 epyc-root commits since 2026-08-01**; 48,521 lines added; 146/639 progress files; program handoff 343 KB / 110 `VB-*` families (283 boxes: 143 done/140 open, +202 in the completed file; `.index-state`: open 104, last_advanced 2026-09-27); adapters README 254 KB in 592 lines; NI verifier lane = 69 codex worktrees, **205 of 564 October commits** ("Accept…/Enroll…", e.g. `6a20abf52` 26,846 insertions), 7,984 tracked artifact files (34 MB) and 16,920 lines of `scripts/ci` capture scripts → **108 frames**. Per invocation: `cite-check` 9.05 s/442 MB RSS (14k ledger) to 12.0 s/552 MB (23.6k ledger), fold recomputed every call (`index_state.py:85` still says "~0.5 s per file"); 18 s rebuild per fresh worktree. **54 other active handoffs carry 70 distinct `VB-*` obligations** because CLAUDE.md requires a wiring task per producer.
- **Two of the program's own predeclared termination triggers (P5c §5, 2026-08-09) are indicated (inference):** "claim identity requiring constant human adjudication rather than converging" (191 pending, 0 adjudicated) and "turning into a second governance system rather than executing the existing one" (own lane, vocabulary, artifact tree, task families; evidence plane/AutoKernel journal/ratification packages remain the actual decision record). The 2026-08-26 PROMOTE verdict recorded "none … currently indicated".

**Verdict: RETIRE, keeping the citation lint as a standalone index-backed linter.**

---

## 1. Inventory

**Code/docs:** core `scripts/vidya/*.py` 45 modules / 10,891 lines; adapters 72 files / 29,007 lines; `tests/vidya` 110 files / 28,039 lines (last recorded run 1,546 passed / 81 skipped, progress/2026-09/2026-09-26-orch-design.md:12); `scripts/ci` 111 files / 16,920 lines (NI lane; pin `claim_tuple.py`/`lattice.py`/`frames.py` digests, e.g. `scripts/ci/vb_tuadv_native_capture.py:67-71`); design docs 3,064 lines (`docs/design/vidya-pilot-spec.md` 964, research-program 220, appendix 154, audit 423, p5c decision 306); program handoff 2,886 active + 1,631 completed lines; CLAUDE.md section 26 lines; `agents/shared/*` 0 mentions; research-intake SKILL.md 6 `#record` citations.

**Ledger frame types:** claim_proposed 5,990 · evidence_supports_claim 5,901 · source_observed 1,793 · correction_recorded 304 · retraction 132 · claim_depends_on 123 · evidence_opposes_claim 109 · claim_alias 17. **By method:** research_intake 12,789; embedder_placement_gate 369; autokernel_aux_receipt 234; autokernel_reward_integrity 159; inf70_roofline_ledger 144; autokernel_governed_receipt 135; stage2 depends-on 123; ci_conformance 108; tale_budget 72; autokernel_rocm_diagnostic 66; occ1 66; research_sweeps 30; review_f1 18; tulving 18; alias worksheet 17; autokernel_evaluation_event 9; contention_gate 6; memento_lora 6. **Growth:** Aug 13,141 · Sep 687 (intake-only) · Oct 541 (the 2026-10-06/07 intake re-verification replay: 132 retractions, 23 corrections). Gen-1 ledger (20,331 frames) discarded 2026-08-26 as non-reproducible (`.vidya/README.md`). `cli.py verify`: chain OK, 6 checkpoints OK.

**Grades assigned:** intake class — Hinted/Located 3,286, Verified/Located 1,101, Verified/Attested 421, Hinted/MachineLocated 372, Verified/Anchored 114, Hinted/T0 74, Verified/MachineLocated 51. Measurement/verifier (729 + 108 frames) — Witnessed/Attested 157, Witnessed/Anchored 60, Judged/Located 211 (embedder placement 123, ci_conformance 36, tale_budget 24, occ1 22, review_f1 6), Verified/Located 52.

**Automatic vs manual:** `cite-check` runs inside `index_state.py --check` over changed `handoffs/ wiki/ docs/` — by convention only (**no git hook, `scripts/hooks/*`, or `.claude/settings*.json` invokes it**; only `scripts/hooks/tests/test_operator_apply_copy.py` mentions it). Orchestrator SC19 `contention_gate_capture` (`src/api/routes/chat.py:310`) opt-in via `ORCHESTRATOR_CONTENTION_GATE_CAPTURE` → 6 frames ever. `host_hygiene_tick.capture_activation_heartbeat` only if pending markers exist → 0 frames. `dashboard/server.py:2196,2268,3421` check adapter **file presence**, never read the ledger. CLI read commands mentioned in docs: `ingest` 95, `cite-check` 14, `corrections` 4, `verify`/`query`/`project`/`impact` 1 each, `disposition`/`eval-live` 0.

**Effort proxies:** 42 distinct commit-days, 246 distinct commit-hours on vidya paths; 320 commit messages mention vidya/belief/VB (Aug 121, Sep 166, Oct 32); operator time = alias worksheet 19 judgments (08-10) + 43 pairs (08-26), machine-anchor option-B ratification, 5 operator rulings. **(inference)** 250–400 agent-session-hours.

## 2. Value delivered — real instances

**(a) Decision changed by a grade: none found.** `artifacts/operator/*` (11 vidya mentions, all package text listing VB tasks), `.claude/skills/kernel-promotion` (0), `autokernel-rebuild-program.md` (5 write-side mentions), all progress/handoffs for `cli.py query`/`--floor`/`exit 3` (no belief-kernel hits). P5c PROMOTE evidence (28/28 gold mutations, 161/161 live, recall 1.0) measures engine self-consistency, not decision influence. R5d-honesty (completed handoff line 587): reuse panels "are empty and stay empty".

**(b) cite-check catches:**
- **intake-725** claim 1 overturned ("our fork must port MTP" — v10 contains `common_speculative_impl_draft_mtp`; PRs #22673/#23398/#18039 are ancestors). `wiki/speculative-decoding.md:1080` cites `intake-725` entry-level with prose that **restates the overturned claim** → **substantive** (stale wiki prose), low stakes; `speculative-decoding-mtp-refresh.md:254` already uses `#record`. The knowledge came from the dive's `claim_corrections`; the gate added the cross-reference.
- **intake-2201#05** (v10 `qwen4exp.cpp` has no `build_cvec`): `reasoning-compression.md:751` RC-CVEC-HOOKS cites `intake-2201#record` and already states the corrected fact → **form-only**.
- **intake-2191** whole-entry (overturned claim = a "cost inconsistency" number; verdict `adopt_patterns` unchanged): `model-artifact-integrity.md:13,48`, `model-exec-containment.md:12` use `#record` → **form-only**.
- 2026-08-26 baseline 77 overturned / 3 dangling → clean by "provenance refs → `#record`; specific claims → `#NN`; meta-refs → U+2011 hyphen" (progress/2026-08/2026-08-26.md:34-40) → **form rework** + one scanner defect fix.
- 2026-09-07: spec cites intake-1300 (overturned) → blocked a peer session who could not decide the narrowing (progress/2026-09/2026-09-07-research-intake-adhoc.md:37) → **friction**.
- 2026-09-16 ×3 lanes report the same 3 pre-existing flags (intake-896, 896#03, 1245) in `adapters/README.md` (the kernel's own doc) + intake-883 in `agent-collab-rnd-harness.md` → form.
- Today on /workspace: `intake-408#06`, `intake-1333#06` dangling (claim index out of `key_claims` range) in `decision-aware-routing.md` → real lint catch, form.

Every `overturned` originates from `effect: overturned` in the index; `dangling` resolves against the live index + merge redirects; `review` = unadjudicated correction. **None needs the fold, chain, or measurement carrier.**

**(c) Read-side use:** IRV-2 (2026-10-06) used `cite-check` as a *locator* of consumers for 352 at-risk entries (progress/2026-10/2026-10-06-intake-reverify-main.md:7,14) — real, modest, grep-class. Embedder placement (369 frames, largest measurement producer): `repl-embedding-retrieval.md:134,197` reference only write-side wiring tasks. Correction queue produced, never consumed.

## 3. Costs
1. Latency: 9–12 s + 0.5 GB per `cite-check`; 18 s rebuild per worktree; 1.3 GB of copies.
2. Blocks/rework: documented 08-11, 09-07, 09-16 (×4), 10-06 ("Canonical-baseline cite-check exit 3 remains under investigation", `filing_preparation.md:4`); 138 commits mention `#record`/cite-check/citation; **889 of 3,510 live citations (25%) are `#record`** — a form invented after the first run's "50% of its headline finding" was false positives (README).
3. Obligations: 192 source rows (64 prospective), 70 `VB-*` ids across 54 other handoffs, 52 frame-less adapters, NI lane (7,984 files, 16.9k lines → 108 frames).
4. Cognitive load: 254 KB README (≈430 chars/line), 343 KB handoff, 964-line spec, a second vocabulary the measurement constitution never references.
5. Silent degradation: stale ledger → 24% `unknown`; worktree rebuilds drop every measurement frame; nothing checks checkpoints since 08-27.
6. Churn: gen-1 discarded; three eval-harness fixes to pass promotion; KV-quant planner block printed into every prompt then retired (program line 1692).

## 4. Health
- Current producers are **not** projected: KVU-12 W2 `epyc.vidya.np_ctx_kvu_capture.v1` artifacts exist (`artifacts/np_context_kvu_cpu_study_20261020/*`) but there is no `np_ctx_kvu` adapter and no frame (VB-KVU 0/5); KPF-18 "VB-KVU-PF" and CH-19 T3 are README candidate rows only. Newest measurement frames are September.
- Stale: ledger 10-07, checkpoints 08-27, program last_advanced 09-27, VB-AK 2/21 with 6 frozen tasks, `index_state.py` timeout comments ~20× off.
- Ladder vs decisions: operator decisions flow through `ratify_*.json`, stack-change packages, serving gates, evidence plane/AK journal — none consult Q×T. The "rides, never rivals" clause makes the measurement half a *copy* of records that already gate decisions.
- Stated rationale ("benchmarks/results: 0 of 200 usable tuples") vs reality: wired sources since produced 729 measurement frames, 217 at Witnessed — **none gated a decision either**. The missing ingredient was a consumer, not usability.

## 5. Verdict: RETIRE (migration keeps the citation lint)

**Keep:** an index-backed linter (reads `intake_index.yaml` directly; forms `intake-NNN`/`#NN`/`#record`; statuses dangling/overturned/review; exit 3; `tests/test_index_state_citation_gate.py` contract). **(inference)** ~300 lines, ~1 s, no ledger — `citation_gate.py` already holds most of it; the fold dependency is confined to `cli.py:693-714`. Keep `docs/design/vidya-*`, the P5c doc and the program as archived history (a good negative result). Orchestrator sidecar writers only if someone names a reader.

**Delete** (after `git tag vidya-retired-20261021`): `scripts/vidya/` (minus the linter), adapters, `tests/vidya/`, `.vidya/` incl. checkpoints, `scripts/ci/*capture*.py` + `artifacts/ni05|06|07` (34 MB tracked), the 72 worktree ledgers (1.3 GB), `kvq_planner_context.py`, AK `belief_context` + unmerged lane, dashboard probes (`server.py:2196,2268,3421`), `host_hygiene_tick` activation path, `.gitignore:120-128`.

**Unwind obligations:** CLAUDE.md 26-line section → 3-line "intake citation lint" rule (agents/shared need no change); `index_state.citation_check()` → new linter, drop `ingest` self-heal; delete the program's index row, move the program to `completed/` with a retirement note; sweep the 70 `VB-*` references in 54 handoffs (main-session writes per ruling (b)), keeping producer work that has a non-vidya consumer under its owner.

**Cost/benefit:** saves ~15% of commit-volume maintenance surface, ~30 s per commit/worktree, 1.3 GB, the per-producer VB tax and the NI lane; stops silent `unknown` drift. Costs one clerical session **(inference 2–4 agent-hours)**; loses a tamper-evident ledger nobody verifies and readers nobody enabled. Rollback = the tag.

**Next steps**
1. Operator rules RETIRE (only decision needed: archived spec/program stay under `docs/design/` or move to `handoffs/archived/`). Alternatively step 5.
2. Extract the index-backed linter from `citation_gate.py`, swap into `index_state.py`, confirm it reproduces today's 2 dangling / 1 overturned.
3. Tag, delete the listed surfaces, remove worktree ledgers, run tests.
4. CLAUDE.md + index row + 54-handoff `VB-*` sweep; program → `completed/` with this review linked; wiki `knowledge-management.md` compile note.
5. **If ambiguous:** two-week probe to 2026-11-04, predeclared: keep only if (i) one decision (promotion/stack-change/serving gate/intake verdict) whose written rationale cites a fold grade or `cli.py query` exit code, or (ii) one `overturned` flag whose citing prose relied on the claim and was changed, that an index-only linter could not have raised. Both visible in git; instrument nothing. Neither → retire without further review.

**Re-run commands:** `python3 scripts/vidya/cli.py verify`; `… corrections --as-of <now>` (191/465); `… cite-check --as-of <now>` (3,510 citations, unknown=831); `git log --oneline -- scripts/vidya .vidya docs/design/vidya* handoffs/active/vidya* tests/vidya | wc -l` (590); ledger-vs-index coverage one-liner over `provenance.about` ids vs `^- id: intake-` in the index (1,291/1333 vs 1,958/1962, 667 missing).

# Task-brief layer — design rev 2 + amendment (P1–P2 built)

2026-11-20 · read-only design · sources: origin/main `docs/design/handoff-standard.md` (HS), `docs/design/taskflow-dispatcher.md` (TD),
`scripts/coordination/taskflow/{schema,extract,verify}.py`, `harness/local_llm.py`, research-intake `SKILL.md`, `agents/commands/wrap-up.md`.
Operator answers (rev 2): D1 sidecar · D2 compile is deterministic only, with no mid-tier model · the worker self-briefs instead of a separate backfill writer ·
D3 as recommended · D4 local only, where a missing brief means self-brief rather than blocked · D5 the extractor fix is already with the taskflow builder.

> **Operator amendment (2026-11-20) — EVERY box must have a brief.** A missing brief is a **gap to fix**, not a normal
> state. Self-briefing (§5) stays only as a **fallback**, and every brief a worker writes itself carries
> `review: backfill` (with `accepted: pending`) so it is reviewed. Older boxes are backfilled systematically by a separate
> job right after P1 lands (`brief.py write`, §2.2). Consequences folded in below: the diff gate (`task_lint` rule **k**)
> requires a brief on NEW boxes and on boxes whose fields are edited — **warn mode first**, exactly as the done-when gate
> (rule a) rolled out — and the dashboard and index report **brief coverage, briefed/total** (§6, §7).

## 0. What r3 says
- Of the 5 spec failures, 2 are already fixed deterministically on origin/main: `schema.resolve_basename` handles the bare basename (r3 DHM-8, `m2_guards.py`),
  and `schema._SKILL` turns a skill name into `.claude/skills/<name>/`. **Packaging failures are extractor bugs first.**
- 3 are real authoring gaps: TU-GR-1 has no *where*; RESUME-7 has no *approach* and no *acceptance*, and its input exists only at a historical commit; HS-OD-4 has a cross-repo
  input. `pick_repo` keeps a single repo, so HS-OD-4's input was dropped silently. The multi-repo and `path@rev` fix is with the taskflow builder (D5).
- Briefs therefore carry only what code cannot derive: where, approach, acceptance and non-goals.

## 1. Shape
1. **Brief = typed sidecar** linked from the box by ID. It records the box `text_sha` it was written for and never alters box identity (HS §2.2).
2. **Dispatch-time compile is deterministic**: gitnexus checks plus a dry check of the acceptance command. It uses zero LLM tokens.
3. **If compile fails, the worker repairs the brief**: it receives the brief plus a *stale-list* and refreshes the brief as its first step.
4. **If there is no brief, the worker writes one first** (local tier) using gitnexus and kb-search, then executes it. There is no separate backfill writer.
5. **Acceptance is the runnable form of the box's done-when**, never a second target. Lint fails if they disagree.
6. **Typed (Jev, §8):** fixed YAML keys plus at most 5 lines of approach prose, so the compile is a pure function and the writer's output can be constrained.

## 2. Where briefs live (D1: sidecar)
`handoffs/active/briefs/<ID>.md`, in the same repo as the handoff. The box gets an optional `· brief: <ID>` field; when the field is absent, the dispatcher looks for a file by ID.
Paths inside a brief are repo-qualified. Briefs move with their handoff to `completed/`, and a tick deletes the brief (its findings go to `## Findings`).

### 2.2 Format as landed (P1, `scripts/coordination/taskflow/brief.py`)
```yaml
---
schema: epyc.brief.v1
id: TU-GR-1
box_text_sha: 0123456789abcdef      # box_index.text_sha of the box first line when written (16 hex)
author: owner                       # intake|planning|wrap-up|owner|coordinator|self
written: '2026-11-20'
accepted: auto                      # owner|auto|pending|rejected (auto = acceptance IS the literal done-when, D3)
review: backfill                    # present only on author=self (amendment); cleared by `accept`
where:                              # repo-qualified; optional @rev (historical input); optional ::symbol
  - epyc-orchestrator:src/routing/guard.py::check_budget
  - epyc-root:tests/coordination/test_x.py@a1b2c3d
approach: |                         # <= 5 lines: the decision, not a plan
  ...
acceptance: pytest -q tests/routing/test_guard.py::test_budget   # == runnable done-when
non_goals: [do not change routing weights]
tier: local                         # local|luna|terra|sol
grounded: {at: '2026-11-20', blobs: {<repo>:<path>[@rev]: <git blob sha>}}   # written by write/accept
---
```
Deviations from rev 2, deliberate: `text_sha` is spelled `box_text_sha`; `approach` is a YAML key (not body prose) so the
whole record is typed; `grounded` is written by `write`/`accept`, **not by compile** — compile never mutates a tracked
file (it would change its own cache key), and its result lives in the gitignored cache
`handoffs/active/briefs/.compile-cache.json`. `drift` is measured against `grounded`.

**Writer CLI (the backfill job and every strong writer):**
```
python3 scripts/coordination/taskflow/brief.py write <ID> --where <repo:path[@rev][::sym]> [...] \
    --approach "<<=5 lines>" --acceptance "<done-when command>" [--non-goal "<...>" ...] \
    [--tier local] [--author owner|intake|planning|wrap-up|coordinator|self] [--accepted ...] [--json]
python3 scripts/coordination/taskflow/brief.py compile <ID> [--json] [--no-cache]   # 0 fresh/drift, 1 stale/orphaned, 2 none
python3 scripts/coordination/taskflow/brief.py sweep --stale-list [--json]           # every non-fresh brief + failing items
python3 scripts/handoffs/handoff_box.py add ... --brief --where ... --approach ... [--acceptance ...]  # box + brief, one run
python3 scripts/handoffs/handoff_box.py brief accept|reject <ID> [--by owner]       # refuses an orphaned brief
```
`write` refuses an ID that is not exactly one open box in `handoffs/{active,blocked}`, fills `box_text_sha` and
`grounded`, and `write`'s exit code is the compile's.

### 2.1 Why handoff line limits exist, and why they don't bind workers
The limits are 24 continuation lines per box and 4,000 lines per file (HS operator decisions 4). They protect the **readers that load whole files**: owner sessions and
`/wrap-up` read entire handoffs into context, and long, hot files collide in the shared clone, where parallel sessions edit one working tree and
produce staged-file ride-alongs and merge conflicts. **Workers never read whole handoffs.** They get one box through `.box-index.json` and the extractor.
Putting briefs inline would bloat exactly the files that whole-file readers load. A sidecar costs the worker nothing and leaves owner and wrap-up reads lean.

## 3. Writers and readers
**Writers** (each writes in the same commit as the box or edit it reasons about):
| Writer | When | Brief quality |
|---|---|---|
| research-intake Stage 4 | new boxes under the operator-approved plan; Stage 3 already grounds approach | strong, `accepted: owner` (plan approval) |
| planning sessions / multi-phase plans (P1..Pn filing) | new boxes from a plan | strong |
| wrap-up Step 2 | derived actionables and follow-ups (`wrap-up.md:404` gate), out-of-scope findings | strong, written by the session holding the context |
| owner sessions | accepting `pending` self-briefs, splitting boxes (children get their own briefs), repairing orphans | authoritative |
| coordinator | when dispatching or re-pointing work across sessions (one-line amendments, gate changes) | strong |
| worker (self-brief) | box selected for local tier with brief none/orphaned, or compile failure | `author: self`, accepted per D3 |
**Readers**: `brief.py compile` · `select.py` (readiness and skip reasons) · `schema.py` (merges the brief into `epyc.task.v1`) · `local_llm.task_suffix`
(worker prompt) · `verify.py` (mechanical check plus the reviewer) · `task_lint dispatch` and `index_state --check` (gates) · `.box-index.json` (state) ·
the dashboard · owner sessions and `/wrap-up` (pending-acceptance queue) · the coordinator (NEEDS-BRIEF and pending counts).

## 4. Freshness: the deterministic compile (D2)
`taskflow/brief.py compile <ID>`, with no model call:
- **identity**: brief `text_sha` == box `text_sha`, else `orphaned`.
- **where**: each path is checked with `git cat-file -e <rev>:<path>` (HEAD or the `@rev`); each `::symbol` with `gitnexus context <sym>` (exists, in the named file).
  `gitnexus impact <sym> --direction upstream` is recorded as blast radius, and HIGH or CRITICAL is flagged in the prompt.
  If the gitnexus index is stale, compile falls back to grep and marks the check `weak`.
- **acceptance dry check**: pytest runs `--collect-only -q <nodeid>`, scripts get `bash -n` or `python3 -m py_compile`, and file+field done-whens are parsed only.
  Nothing runs for real.
- **packaging**: cross-repo and `@rev` inputs are turned into `inputs_ext: [{repo, path, rev, excerpt}]`.
- **Cache** key: `(box text_sha, brief_sha, blob shas of where-paths)`. HEAD is deliberately not in the key, because it moves on every commit. A hit costs no work; a miss costs about 1 s.
- **States** in `.box-index.json`: `none | fresh | drift` (a blob changed but the checks pass) `| stale` (some checks failed) `| orphaned`.
  For `stale`, the worker prompt gets `## STALE` with the failing items, and the first instruction is: "refresh the brief (fix these items) using gitnexus/kb-search,
  write `briefs/<ID>.md`, then execute." `index_state --check` compiles touched briefs (diff-scoped), and a nightly zero-token sweep refreshes states.

## 5. Self-briefing (replaces the backfill writer)
- Trigger: a local-tier box whose brief is `none` or `orphaned`. Phase 1 of the same worker run writes the brief. Its tools are gitnexus query/context/impact, kb-search
  (ColBERT) and read/grep, its budget is ≤ 25 % of the turn budget, and its output is constrained to `epyc.brief.v1`.
- The harness runs compile on the self-brief before phase 2. An acceptance command that already passes on the unchanged tree is rejected, because it proves nothing.
  If compile fails twice, the run ends `NEEDS-BRIEF:<missing keys>`. The box joins the owner queue and is skipped until it is edited (HS §6 back-pressure).
- **D3:** `accepted: auto` when `acceptance` is the box's literal done-when command. Otherwise the run executes, but its tick is held as
  `claimed_done` with `accepted: pending`, and the owner accepts both the brief and the result at wrap-up. Either way the brief is committed, so the
  next attempt reuses it.
- Why this beats a backfill pass: there is no extra model or extra call, the cost lands only on boxes actually selected, and the reasoning cost is paid once and cached
  in the repo instead of re-explored on every retry.

## 6. Gates (D4: local only)
- `select.py`: local tier dispatches with any brief state. `none`/`orphaned` runs self-brief, `stale` runs refresh-first, and `fresh`/`drift` executes directly.
  A box tagged `NEEDS-BRIEF` is skipped (skip-reason `needs-brief`). Cloud tiers are unchanged; they get the brief if it exists.
- Lint (`task_lint` diff gate, diff-scoped; rule **k**, landed P2): a NEW box, or a box whose `· field:` lines are edited,
  without a brief → `k` (**WARN** first, like rule a's rollout; promote in `DIFF_GATE_RULE_MODES` once the backfill has
  covered legacy boxes). A brief whose `box_text_sha` mismatches its box → `k-mismatch` (**FAILS**). A touched brief that
  does not compile → `k-stale` (WARN). `HANDOFF_BOX_GATE=warn|off` softens all; `enforce` stays the a/f switch.
  Roll-ups and frozen boxes are exempt. Untouched legacy boxes are never judged; they count against coverage instead.
  `acceptance` vs done-when is recorded per compile (`acceptance_matches_done_when`) and drives D3; the lint on it is P4.
- **Coverage (amendment)**: `.box-index.json` counts `briefed` / `brief_total` (not-done boxes; `none` and `orphaned` are
  unbriefed) plus `brief_<state>`, `brief_pending`, `brief_backfill_review`; `index_state.py --check` and `--summary`
  print `BRIEF-COVERAGE: briefed/total`; the hub's handoffs page shows `briefs: briefed/total`.

## 7. Consumers that change (exact)
| Consumer | Change |
|---|---|
| research-intake `SKILL.md` Stage 4 | write a brief for each new box via `handoff_box.py add --brief` |
| `agents/commands/wrap-up.md` Step 2 | briefs for derived actionables and follow-ups; accept/reject `pending` self-briefs and their held ticks; a tick deletes the brief |
| owner and coordinator role text (`agents/coordinator-agent.md`, handoff-index-authoring guide) | a split gives children briefs; how to accept or repair |
| `scripts/handoffs/handoff_box.py` | `add --brief`, `brief accept/reject <ID>`; refuse a text_sha mismatch |
| `scripts/handoffs/task_lint.py` | `dispatch` rule **k** (§6) |
| `scripts/handoffs/index_state.py` / `.box-index.json` | per-box `brief` (none/unverified/fresh/drift/stale/orphaned — cheap: cached compile state only, `unverified` on a cache miss), `brief_sha`, `accepted`, `brief_author`, `brief_review`; coverage counts; diff-scoped compile of touched briefs |
| `taskflow/brief.py` (new) | compile, cache, states, stale-list (P1); `write` / `accept` / `reject` / `sweep` |
| `taskflow/schema.py` | add `where`, `approach`, `acceptance`, `non_goals`, `inputs_ext`, `brief_state`, `stale` to `epyc.task.v1` (the multi-repo/@rev fix is with the builder) |
| `taskflow/select.py`, `dispatch.py` | §6 routing; a two-phase run (self-brief or refresh, then execute) |
| `harness/local_llm.py` `task_suffix` | `## WHERE`, `## APPROACH`, `## NON-GOALS`, `## STALE`/`## WRITE BRIEF FIRST`; acceptance listed first in ALLOWED COMMANDS; gitnexus and kb-search added to the tool allowlist; the stable prefix stays byte-identical |
| `taskflow/verify.py` | mechanical step runs `acceptance`; reviewer = verbatim box + done-when + acceptance and its result + non-goals; a non-goal hit counts as `drift`; `accepted: pending` holds the tick |
| dashboard (taskflow page) | brief coverage briefed/total (P2: hub handoffs page box counts), states, NEEDS-BRIEF, pending acceptance, verified rate for strong-brief / self-brief / none |
Human-only text needs one sentence ("a brief is guidance; the box text stays identity"), added via the ratify script bundled with the HS Stage C package.

## 8. Alternatives (memory rule: Jev + REPL retrieval)
- **Jev typed decisions**: built in. The brief is a typed record, the writer is constrained to the schema, the compile is pure, and the prompt sections are fixed.
  This removes the proposed per-dispatch mid-tier call (~20–40k tokens, about 100 % of dispatches) entirely.
- **REPL retrieval**: built into self-briefing. kb-search and gitnexus run once per box and the result persists as the brief, instead of every retry exploring
  (r1: "14 steps all went to exploration"). Retrieval alone, without a brief, cannot supply acceptance or non-goals, so it was rejected as a replacement.

## 9. Token cost
- Strong writers add 1–2k output tokens per new box, which is negligible next to the reasoning they already did.
- Self-brief costs ≤ 25 % of the worker budget (≤ 30k local tokens) once per box, only on selected boxes, on the local 35B at zero marginal cloud cost. It is reused afterwards.
- A brief adds about 300–600 tokens to the uncached suffix and nothing to the cached prefix. Compile costs 0 tokens, and its cache hit rate should exceed 90 %.

## 10. Pilot (stop-on-answer; no compute until approved)
Question: does a brief raise the local verified rate, and is a self-brief close enough to a strong brief?
- **Same 10 boxes** (the r3 set, with r3 harness fixes kept), each run in **3 arms**: strong-model brief / self-brief / no brief (r3 baseline rerun).
  That is 30 runs. Failure class is coded per run as spec / harness / model; harness failures are excluded from the comparison and reported separately.
- Primary metric: verified/10 per arm. Secondary metrics: turns to first edit, uncached tokens per verified box, reviewer agreement, and whether the self-brief's where-paths
  match the strong brief's and its acceptance is falsifiable.
- Decision: **go** if strong-brief verifies ≥ 2 of the 3 spec boxes with no regressions. **Self-brief is good enough** if it reaches within 1 box of strong-brief.
  Otherwise, self-brief is restricted to accept-pending and strong writers become mandatory for local-eligible new boxes. **No-go** if strong-brief verifies 0 of 3.
  n=10 is go/no-go evidence, not an estimate. One rerun only.
- Belief wiring: the verdict goes through the taskflow ledger as `[belief: clm_<id>]`, and the vidya adapters row is added in P1.

## 11. Implementation plan
| Stage | Work | Done when |
|---|---|---|
| P0 | (builder, in flight) extractor multi-repo inputs + `path@rev` packaging | `pytest tests/coordination/test_taskflow_stage1.py` covers an HS-OD-4-style cross-repo fixture and a RESUME-7 `@rev` fixture, both packaged |
| P1 ✅ | `epyc.brief.v1` schema + `brief.py compile` (gitnexus, dry-check, cache, states, stale-list) + vidya adapters row | `pytest tests/coordination/test_taskflow_brief.py` passes fixtures for fresh/drift/stale/orphaned, a stale-gitnexus `weak` fallback and a cache hit |
| P2 ✅ | `.box-index.json` brief fields + `task_lint` rule k + `handoff_box.py add --brief / brief accept` | `index_state.py --check` exit 0 on origin/main; a fixture commit with a mismatched brief fails |
| P3 | `schema.py` merge + `task_suffix` sections + tool allowlist | prefix-byte-identity test passes across 3 tasks; the suffix snapshot shows WHERE/APPROACH/NON-GOALS/STALE |
| P4 | two-phase run in `dispatch.py` (self-brief / refresh, then execute) + D3 acceptance + `verify.py` acceptance/reviewer changes | fixture run: a box without a brief commits `briefs/<ID>.md` and then a diff; `accepted: pending` holds the tick; the reviewer prompt contains done-when + acceptance |
| P5 | writer integration: intake Stage 4, wrap-up Step 2, owner and coordinator text | skill/command diffs land; one real intake and one real wrap-up each produce a compiling brief |
| P6 | pilot (§10) | ledger holds 30 runs with arm labels; go/no-go verdict filed with a belief tag |
| P7 | dashboard + ratify sentence | dashboard registry entry with probe + freshness envelope live; the operator signs the HS Stage-C ratify bundle including the brief sentence |

## Hooks left for P3–P5
`compile_brief()` already returns `stale_list` (worker `## STALE`), `inputs_ext` (cross-repo / `@rev` packaging for
`schema.py`), `acceptance_matches_done_when` (D3 `accepted: auto` in `dispatch.py`), `blast_radius` (gitnexus impact →
HIGH/CRITICAL flag in the prompt), `approach`/`non_goals` via `parse_text()`. `box_index.skip_reason` does not yet read
`brief` (P4: NEEDS-BRIEF skip). Writers (intake Stage 4, wrap-up Step 2) call `handoff_box.py add --brief` or `brief.py write` (P5).

## Decisions (resolved 2026-11-20)
D1 sidecar · D2 deterministic compile only (gitnexus + dry check), with a failed compile sent to worker refresh · D3 auto-accept on literal done-when, otherwise the owner accepts at wrap-up ·
D4 local only, where a missing brief means self-brief · D5 extractor fix with the taskflow builder. Amendment 2026-11-20: every box needs a brief (see top). **Open:** none. The pilot (P6) needs compute approval when P1–P4 are done.

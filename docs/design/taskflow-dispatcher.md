# Dispatcher redesign — handoffs as the task source, workers as disposable processes

> **Depends on `HANDOFF-STANDARD.md` (same directory).** The box grammar (§2.2 there), the `### Backlog`-only placement rule, the `[class]`/`done when`/`gate:` fields and the generated `handoffs/active/.box-index.json` are what `select.py`/`extract.py` below read. The standard's Stage A ships before this design's Stage 1; until then the dispatcher falls back to `task_lint report` + file parsing with the readiness numbers in §1.2.

Rev 2, 2026-11-19 (read-only audit subagent). Rev 1 proposed a separate planner-written task store; the operator asked "isn't that what the handoffs are for?" Section 1 answers that with data; the design now uses the handoffs directly and shrinks the planner to a deterministic extractor.

## 1. Are the handoffs already the task list?

**Partly: the priority order exists at handoff level, ~24% of open boxes are dispatchable as written, and the dispatcher never passed either to the worker.**

### 1.1 Ordering signal — present, but at row (handoff) granularity
- `handoffs/active/backlog-priority.json` ranks **index rows** (one per handoff): bands inference-prep → inference-ready → non-inference, `basis` = "best open item", `unblocks` = row ids (`scripts/handoffs/backlog_priority.py` docstring: "Row priority = its best open item; … advisory ordering only").
- Six domain indices carry `ID | Track | Handoff | Next action | Deps` — deps are row→row (`INF-06 … | INF-48, EVL-47`), never box→box.
- `.index-state.json` has per-handoff `open/closed/blocked/guarded` counts and per-track `gates` (program-level), no per-box state.
- Inside a handoff, order is file order plus prose ("after X lands", "❄ FROZEN", "Needs D9-ack"). Box-level deps exist only as prose; the 2026-11-02 audit counted 669 prose gates.

So "prioritised and in order" is true for *which handoff*, not for *which box*.

### 1.2 Box readiness — measured
The project already has a rubric and lint: `docs/design/backlog-refactor-2026-11/reviews/task-readiness-audit-20261102.md` (a deliverable/done-criterion, b class, c inference identity, d prereqs as IDs, e one-turn size, f no dangling refs, h no hidden operator decision; hand-calibrated P=0.86 R=0.95) found **827 / 2,808 open boxes executable as-is (29.5%)**. I re-ran `scripts/handoffs/task_lint.py report` today on the six requested handoffs at origin/main:

| Handoff | lines | open | lint OK | top failing fields |
|---|---|---|---|---|
| harness-program | 3,722 | 107 | 26 (24%) | e 49, d 34, s 33, c 30 |
| kv-cache-program | 4,241 | 102 | 13 (12%) | e 65, d 47, s 41, c 29 |
| churn-pipeline | 209 | 25 | 12 (48%) | a 8 |
| stack-lifecycle-program | 2,660 | 31 | 7 (22%) | d 13, e 10 |
| speech-and-multimodal | 2,042 | 70 | 21 (30%) | e 20, d 19, s 18 |
| routing-program | 4,188 | 69 | 19 (27%) | e 34, d 17, s 19 |
| **total** | | **404** | **98 (24%)** | e 180 oversized · d 132 prose prereqs · s 123 no stop rule · c 97 no run identity |

Hand check of 30 sampled boxes (5 per file) agrees. Dispatchable as written: `churn-pipeline.md:158` "JANITOR-QH-UNBOUND — 4 tests fail with `QH: unbound variable` … fix disk_janitor.sh / the fixture" (task, inputs, checkable done); `:130` "Raise RAM margin 64→100 GiB with `ram_gib` injection"; `stack-lifecycle:560` SEC-ART-2 (named check, named test); `routing:3343` TD-18 (zero inference, named fields); `harness:3005` UFH14-B1 (named source files, named targets). Not dispatchable: label-only boxes (`speech:406` "CS-30 — port the audio encoder as an mtmd projector", `:369` "CS-22 — add VAD and turn detection", `stack:2305` "Finish W4 swap-CI"), frozen/held (`harness:343`, `routing:487` "❄ FROZEN … resume only once …"), decisions (`kv:3822` "re-run decision — one more ABA or accept NO_DIFFERENCE", `kv:3807` "only if needed"), compute-blocked (`kv:1001` KPF-18.3 needs the GPU window), dangling inputs (`harness:2977` points at `/mnt/raid0/llm/tmp/p6p7-20261003/`), roll-ups (`harness:442` S4 Omega A/B "absorbs the two metric rows below"). The lint's 24% is a fair number: **a quarter dispatch-ready, a quarter blocked or held, half needing translation** (split, done-condition, or run identity).

The lint is **warn-only**: `index_state.py --check` prints a `task_lint` column that "never affects the exit code" (`index_state.py:1370-1418`); `publish_row.py` refuses only on missing model/build identity or stop rule. The 11-02 authoring template (§5 of the audit) was never made binding.

### 1.3 Why the dispatcher still said "take the next task"
The material was there; the dispatcher did not pass it.
- `brief_text` (`handoff_sessions.py:363-468`): ~100 lines of procedure; names the handoff path, zero boxes, zero rank. `idle_prompt`/`continue_prompt` (564-578): "Take the next task per brief … Wrap up with ONE JSON".
- Until 11-18 the only state was `BACKLOG-handoff-<slug>.md` (row list) — the session re-derived the box from the full handoff (3–4k lines; 1,129 turns on 11-02 alone).
- `compile_state` (2386-2419, added 11-18): ≤ 3,072 bytes, ≤ 8 open boxes, **in file order** (`rest = [b for b in boxes if b not in pri]`; only event-named boxes are promoted), **first line only, id stripped**: "KPF-17: tests", "KPF-18.0d(item 3, rest)". No rank, no deps, no section context, no done-condition, no referenced files. The rank is consumed only to choose *which handoff* to spawn (1271-1280, 1902-1930).
- Run-end prompts (`end_prompt` 529-556) do carry a concrete object (row, rc, result_path, decision_rule): those turns NOOP at 22% vs 33% idle, and the good transcripts (`df2/2026-11-19T204838Z`, `heterogeneous-slot-fabric-residency/…T145909Z`) are the ones where the agent could state "done when …" from what it was given.

## 2. Design (rev 2)

Principle: **the handoff box is the task record; the dispatcher selects, extracts and verifies; the worker is a fresh process per box.** No parallel task store — the only new artefact is a per-dispatch receipt.

### 2.1 Selection — existing order, box-level
`taskflow/select.py` (deterministic, no LLM), run per tick:
1. Walk handoffs in `backlog-priority.json` rank order (fallback: index order), skipping rows under an operator hold (`holds.yaml`, §2.5) and rows whose index `Deps` are open.
2. Within a handoff, walk open boxes in file order within each track, skipping: boxes under a `❄ FROZEN`/HOLD block (`status_and_hold` already parses this), `[roll-up]`, `[operator-decision]`/`NEEDS-OPERATOR`, boxes whose `gate:` IDs are open, `[inference]` boxes whose region is not grantable now (`rowflow.py status` would not reach `grantable`), boxes failing lint fields a or f (no done-condition / dangling inputs) **unless** translated (§2.2).
3. Yield the first admitted box; cap one in flight per handoff, width per engine family.

### 2.2 Extraction — thin and deterministic
`taskflow/extract.py` turns the chosen box into the prompt payload, verbatim: the full box text (all continuation lines, exact bytes — this is the identity, `OPERATING_CONSTRAINTS.md` → *Dispatching Backlog Work*), its heading chain (`## track` → `### section`), the HOLD/Status lines, the 20 lines of context above it, every path/ID it references with existence checked (`backlog_row_check.py --row` for form), its handoff rank and the row's `Deps`, and the fields parsed from the authoring conventions (§2.3). `file.md:LINE` goes along as a hint only.

**LLM translation** is used only when extraction cannot produce a `done when` and a `class`: a single low-tier turn (`luna`/`haiku`) proposes `done when / inputs / class / split into N children`, written **back into the handoff as a proposal** (`[proposed-by: taskflow <ts>]` suffix on the box, children under it with `NEEDS-OWNER`) by the dispatcher's wrap-up path — not executed until an owning session or the operator accepts the proposal. Boxes under translation are not dispatched. Translation yield (proposals accepted / proposed) is a metric; if owners never accept them the stage is cut.

### 2.3 Authoring conventions (docs + lint, not a new store)
Adopt the 11-02 template as binding for **new and re-touched** boxes, trimmed to what selection needs:

```
- [ ] **<ID>** [non-inference|inference|operator-decision|roll-up] <imperative deliverable>
      · done when <artifact / test command / verdict text that ticks it>
      · gate: <ID,…|none>   · inputs: `<path>` …   · tier: luna|terra|sol (optional; default by class)
      inference only: · model · build · harness · metric · rule · region · est <N s, from run <id>>
```
Changes needed: (i) `task_lint.py` gets a `dispatch` mode that returns the parsed fields or the missing ones; (ii) `index_state.py --check` turns a or f failures on boxes **touched in the commit** into a hard failure (existing warn column, scoped by diff, so legacy boxes do not block); (iii) `handoff-index-authoring.md` gains the box template and the rule "a tick needs the done-when evidence". `gate:` uses task IDs (field d already asks for them); the prose-prereq regex keeps catching the rest as non-dispatchable. Nothing else changes: thin-row indices, master router, belief tags, `[inference]` rowflow fields stay.

### 2.4 Work loop and harness adapters
Unchanged from rev 1 except the payload: fresh process + disposable worktree per box (reuse `lane_*` helpers, generalised to the research/orchestrator repos the box names), prompt = extracted payload + ~20 lines of hard rules (no waiting, no pkill, scratch path, pathspec commits, "report `claimed_done` with evidence; never tick"). No resume, rotation or registry; kill at 2× `est` or the token budget. Adapter interface `spawn(prompt, model, effort, cwd) → (pid, transcript)`, `usage(transcript)`, `done(transcript)` for codex / `claude -p` / opencode (lift `token_guards.engine_flags` 136-147 and `engine_cmd` 1120-1130). Tier from the box's `tier:` hint, else class: `file`/clerical → luna/haiku; implement/fix → terra/sonnet; sol/opus only on a checkable retry failure (doctrine "effort before tier").

### 2.5 Verification, filing, safety
- Mechanical first: `git cherry` empty, pathspec ⊆ `inputs`+declared outputs, no `forbidden` paths (rowflow, keeper, grants, `artifacts/`, `docs/reports/` unless the box names them), the `done when` test command passes / file+field exists / verdict present.
- Reviewer turn (low tier, other family when budget allows) only for implement/fix/analyse: `{done|not_done|drift, reason}` against the verbatim box text. Never edits.
- The **dispatcher** applies the tick via `wrapup.py --tick-by-text` under the owning-handoff identity with the belief tag and the evidence; index rows are never touched (owning session applies, ruling (b) 2026-08-16); rows file through `file_result.py`; rc=4 run-ends are dispatched as `kind=file` tasks directly (no selection pass).
- `holds.yaml` is the single list of operator exclusions (AutoKernel, autopilot, kernel promotion, stack bring-up, D9 holds, v11); `select.py` is its only reader. A held handoff yields zero boxes.
- Failure path: `not_done`/`drift` → retry once at higher effort, once one tier up, then the box gets a `[taskflow: failed ×3 <reason>]` note in the handoff and is skipped until edited.
- **AK audit B13 (tick vs done-when).** The verifier evaluates the box's `done when` *before* `wrapup.py` is called, and the tick request carries the evidence it checked (`{done_when, evidence_paths, artifact_class}`); `wrapup.py` refuses a tick whose evidence names an artifact of the wrong class when the `done when` names one (production `kernels/production/*` vs loop-built record — the AKX-ALL-14 incident, reopened `55b5733c1`). A box with no machine-checkable `done when` goes to the reviewer turn only.
- **AK audit B12 (events).** Run-end, smoke PASS/FAIL and `queued-smoke-dropped` arrive as the keeper's `notify` bus items addressed to the row owner (41041359b); the dispatcher is one more consumer of that outbox, never a poller, and a row whose owner is `taskflow` is dispatched as a `kind=file` task from the same item.

### 2.6 Budget and metrics
Per-family meter (`budget.json` per engine) + existing `width_cap`/`admit`; a family ahead of linear pace gets width 0 and selection routes the tier to the other family. Ledger `taskflow/ledger.jsonl`, one record per dispatch: box hash, handoff, class, family/model/effort, tokens, verdict. Dashboard numbers: **verified boxes/day**, **uncached tokens per verified box**, **verdict ticks/day**, selection skip-reason histogram (the authoring-debt gauge), translation acceptance rate, reviewer disagreement. No credit for commits, rows published, prep ticks or turn counts.

### 2.7 Reuse / delete
Keep: `wrapup.py`, `file_result.py`, `rowflow/*`, `token_guards` budget/width/engine_flags, `lane_*`, `status_and_hold`, `handoff_boxes`, `box_show`, `task_lint.py` (+ dispatch mode), `backlog_row_check.py`, `backlog_priority.py`. Delete: per-handoff registry, resume/rotate/transfer/checkpoint, NOOP/netprog/auto-unpark, `brief_text` and the three prompts, codex-gen generalist, `compile_state` (replaced by extract), bus assign/nudge (bus stays down). ~2,000 of 3,200 dispatcher lines.

## 3. Staged rollout
**Stage 1 (one day).** `scripts/coordination/taskflow/{select,extract,dispatch,verify}.py`, `harness/{codex,claude}.py`, `task_lint.py dispatch` mode, `tests/coordination/test_taskflow.py` (selection skips each rule on fixture handoffs; extraction byte-identity and heading chain; verify mechanical checks on a fixture worktree; adapter command lines). Source = the **98 lint-OK boxes** in the six handoffs plus rc=4 run-ends, Codex only, width 2. Canary after 24 h from the ledger: **≥ 10 boxes verified `done`, 0 verifier-rejected ticks applied, ≤ 2 M uncached tokens per verified box, skip-reason histogram published.**
**Stage 2 (2–3 days).** Authoring conventions landed (template + scoped lint gate); owners re-touch the top-ranked 30 non-OK boxes in the six handoffs; translation proposals on. Canary: lint-OK fraction in those files ≥ 40%, verified boxes/day ≥ 10, translation acceptance ≥ 50%, reviewer disagreement < 20%.
**Stage 3.** opencode adapter, per-family pacing, cross-family reviewer. **Stage 4.** Retire `handoff_sessions.py` when verified boxes/day beats the old pipeline's best (~20 verdict ticks) for a week.

**Worktree lifecycle.** Owned by the taskflow builder, who is writing this section (how a worker's worktree is created,
reused, pushed and removed). Pointer only until it lands; task briefs that a worker writes or refreshes in that worktree
are covered in [`task-brief-layer.md`](task-brief-layer.md) §5.

## 4. Open questions for the operator
1. **Translation write-back**: may the dispatcher append `[proposed-by: taskflow]` done-conditions and child boxes into handoffs (as proposals, never ticked), or must proposals go to a side file for owners to paste in?
2. **Legacy boxes**: accept the scoped lint gate (hard-fail only on boxes touched in the commit), or a one-time owner sweep of the ~300 non-OK boxes in these six files first?
3. **Inference boxes**: should Stage 1 dispatch `[inference]` boxes whose region is grantable (publish_row + smoke inside the turn), or stay non-inference + filing until Stage 2?
4. **Tier floor for Codex**: default to luna/terra by class with sol only on retry, or keep sol for implement/fix as today?
5. **Reviewer family**: cross-family review (Claude reviews Codex and vice versa) from Stage 1, at the cost of spending both budgets, or same-family until Stage 3?
6. **Which six handoffs first**: the six above, or swap in `df2`/CAFE-3 and `kernel-champion` where run-end filing already works?

## Worktree lifecycle (taskflow Stage 1, enforced in `scripts/coordination/taskflow/dispatch.py`)

| Rule | Enforcement | Since |
|---|---|---|
| Created fresh: `git worktree add -b taskflow/<run>/<n>-<hash>` at the repo's `origin/main` | `make_lane` | Stage 1 (104a8f154) |
| Short path `/mnt/raid0/llm/tf/<4 hex>` (`TASKFLOW_LANE_ROOT`); the 35B miscopied long digit-heavy paths | `make_lane` | 1cf100405 |
| One worker per worktree: an existing lane path is refused (`LaneRefused`) | `make_lane` | new |
| No branch switching, no commit, no push by the worker: POLICY plus the shell deny list (`git checkout/commit/push/reset/stash/restore`) | `harness/local_llm.py` | Stage 1 |
| The DISPATCHER commits the worker's tree on the lane branch (pathspec from `git status`, `.taskflow-refs/` excluded); only `--apply` (`churn/wrapup.py`) pushes, under the owning handoff's slug | `commit_lane`, `apply_tick` | Stage 1 |
| Disposal after verify: `git worktree remove` without `--force` and never `prune`; a dirty lane is first committed as WIP on its own branch, so nothing is lost | `drop_lane` | new (dirty-lane commit) |
| Failed or aborted lanes with work (`rejected`/`error`/`unchecked`, not `no-change`) are kept for `TASKFLOW_KEEP_FAILED_H` (24 h) for forensics; `diff.patch` and the local branch are kept too | `keep_lane` | new |
| Disk caps: at most `TASKFLOW_MAX_LANES` (16) live lanes and at least `TASKFLOW_MIN_FREE_GIB` (50) GiB free, otherwise the lane is refused | `make_lane` | new |
| Orphan sweep: `dispatch.py sweep` removes kept lanes past their keep-until time, live lanes older than the keep window (dead dispatcher), and lane dirs with no metadata | `sweep_lanes` | new |

Each lane has `<root>/<hex>.lane.json` (repo, branch, base, created, state, keep_until). Tests: `tests/coordination/test_taskflow_stage1.py::test_lifecycle_*`.

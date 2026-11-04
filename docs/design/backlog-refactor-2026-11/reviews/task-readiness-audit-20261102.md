# Task readiness audit — 2026-11-02 (ws58)

Scope: all 2,808 open dispatchable tasks in `backlog-refactor-manifest-20261102.json`, scored at the
manifest's pinned sha `3ac825873dfb` (task text and continuation lines read via `git show`, so the
line numbers match the manifest's `src`). Read-only: no handoff or index was edited.
Artifacts: `task_lint.py` (rubric and lint), `task_audit.py` (manifest driver plus hand-audit labels),
`task-readiness-refinements-20261102.json` (one record per deficient task),
`task-readiness-stats-20261102.json` (counts by domain), and `sample60.txt` (the hand-audited sample).

## 1. Rubric (fields checkable from the task text plus its handoff)

| F | Field | Pass when | Heuristic |
|---|---|---|---|
| a | Deliverable / done-criterion | names an artifact, commit or verdict that ticks the box | done/acceptance/verdict/→-path verbs; fails on bare labels and on assess/investigate/consider openers with no done clause |
| b | Class | exactly one of non-inference / inference / operator-decision / blocked-external | explicit `[class]` tag, or exactly one class signal; fails when signals conflict |
| c | Inference identity (inference only) | model, quant/build, metric+direction, decision rule, region (CPU-quarter / whole-host / GPU), estimate, inputs | a separate regex per sub-field; the refinement lists each missing one |
| d | Prereqs as IDs | every prerequisite is a task ID | a prose prerequisite (`after`, `once`, `only if`, `if validated`, `deferred`, `parked`, `blocked on`) with no ID within 160 chars |
| e | Size | about one session turn or one row | over 1,500 chars, or over 6 child boxes, or 6 or more enumerated steps, or `(ongoing)`, `[too-big`, `N days`, `split across` |
| f | No dangling refs | every backticked path resolves | checked against `origin/main` trees (root, orchestrator, research) plus disk (llama/whisper/qwentts trees, /mnt/raid0/llm); also a list of today's retired items |
| g | Owner | manifest gives `dest_file` plus a row or section | manifest fields |
| h | No hidden operator decision | no operator approve/choose/ratify/review inside a worker task | operator-decision regex; an operator-decision task is routed to the queue, never to a worker |

**Executable as-is** means the task fails no applicable field.

## 2. Results

- **Executable as-is: 827 / 2,808 (29.5%).** 1,981 tasks are deficient; 1,479 of those carry NEEDS-OWNER and 279 carry NEEDS-OPERATOR.
- Tasks failing each field (a task can fail more than one):

  | Field | a | b | c | d | e | f | g | h |
  |---|---|---|---|---|---|---|---|---|
  | Tasks failing | 653 | 130 | 806 (of 946 inference) | 669 | **626 oversized** | **278 dangling** (426 refs, 324 distinct paths) | 0 | **279** |

- **Inferred class**: non-inference 1,704; inference 946; operator-decision 153; blocked-external 5.
- **Dangling-reference makeup**: 80 tasks point into deleted `/mnt/raid0/llm/tmp/*` dirs and 12 into removed worktrees. Today's named deletions appear once each: `stt-cs8-public-20261030`, `episodic-leak-20260917` and Qwen2.5-Coder-32B-Q4_K_M. `data/openmementos` has no remaining text references. The other refs are relative artifact paths that resolve nowhere; some of them are probably relative to an artifact dir, so field f is the noisiest field (see §3).
- **By domain** (open / executable; fields a, c, d, e, f, h), worst first:

  | Domain | Open | Exec | a | c | d | e | f | h |
  |---|---|---|---|---|---|---|---|---|
  | deepseek-v41-flash-evaluation | 139 | 26 | 25 | 50 | 34 | 28 | 35 | 19 |
  | model-evaluation-queue | 123 | 20 | 55 | 49 | 24 | 19 | 5 | 10 |
  | kv-cache-program | 130 | 25 | 13 | 52 | 46 | 71 | 24 | 11 |
  | kernel-champion-and-promotion | 126 | 29 | 19 | 45 | 33 | 51 | 25 | 14 |
  | autokernel-loop | 222 | 65 | 57 | 55 | 70 | 44 | 11 | 16 |
  | harness-program | 123 | 35 | 15 | 48 | 35 | 43 | 29 | 18 |
  | engineering-hygiene-backlog | 131 | 34 | 58 | 16 | 20 | 14 | 5 | 19 |
  | vidya-belief-substrate-program | 418 | 214 | 15 | 106 | 79 | 69 | 39 | 19 |

  The other 22 domains are in `task-readiness-stats-20261102.json`.

## 3. Calibration — hand audit of 60 tasks

The sample is stratified over 30 destination domains, with 2 tasks per domain. It is in `sample60.txt`; the labels are `HAND` in `task_audit.py`.

I used the first 30 tasks to tune the regexes, then checked the result on all 60.

| Run | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|
| First pass (before tuning) | 41 | 7 | 3 | 9 | 0.854 | 0.932 |
| Final | 42 | 7 | 2 | 9 | **0.857** | **0.955** |

The labels are binary: deficient versus executable.

Remaining false positives:
- code tasks misread as inference because they mention a metric (AK-PROF-ATTR-1, CH-24);
- analysis boxes judged to have no done clause (WRAP-2, BK-5, "adversarial review then merge").

Remaining false negatives are boxes that are only a label or a log heading, with status lines but no verb (KPF-18.0d).

At field level:
- **h** missed three of four hidden decisions before tuning ("operator run/pause decision", "operator-review candidate", "implement or procure"). They are caught after tuning.
- **f** has a known false-positive mode: llama-tree-relative paths. Those trees are now searched. Artifact-relative paths remain, so treat f hits as "verify", not "delete".

## 4. Top patterns, most to least damaging

1. **Inference boxes with no run identity** (806). The usual gaps are region and estimate, then quant/build and the decision rule. This is today's 20× `estimate_s` failure, so the template makes `est` mandatory and the value must come from a named prior run.
2. **Prose gates** (669): `after X lands`, `once the hold lifts`, `if validated`, `parked`, `deferred`. A session cannot test them, so it builds the prerequisite itself; this is the "listed prerequisites" failure.
3. **No tickable done-criterion** (653): research, assess and "UNEXPLAINED" boxes, which produce only notes.
4. **Oversized boxes** (626): multi-day impl, `REMAINS OPEN … ~918`, and ongoing ladders. They are never tickable.
5. **Operator decisions buried in worker tasks** (279): run/pause, rollout re-take, procure-or-build and parked operator-review candidates.
6. **Dangling inputs** (278): deleted tmp dirs, worktrees and reclaimed data. These rows publish against vanished inputs.

## 5. Authoring template

```
- [ ] **<ID>** [non-inference|inference|operator-decision|blocked-external] <imperative deliverable>
      — done when <artifact/commit/verdict that ticks it> · gate: <TASK-ID,…|none>
      · inputs: `<path@sha or git path>` · owner: <handoff>#<track>
      inference only: · model <name quant> · build <kernel commit/store id> · harness `<script>`
      · metric <name> (<higher|lower> better) · rule <keep if …> · region <cpu-quarter|whole-host|gpu>
      · est <N s, from run <id>> 
```

The template has five rules:
- one box is one row or one turn; a bigger task becomes a parent roll-up with children;
- `operator-decision` boxes live only in the operator queue;
- a value that cannot be derived is written as `NEEDS-OWNER` and blocks publish;
- no status or history inside the box (the thin-row contract applies to boxes too);
- `est` must cite a prior measured run, never a guess.

## 6. Lint and enforcement

`task_lint.py FILE.md …` prints `file:line: FAIL <fields> [class]` and exits 1 on any failure.
`task_lint.py --audit MANIFEST` regenerates this audit.

Where to enforce it, in order of value:
1. **During each atomic fold commit (plan v2, routes 1a and 1b).** Run the lint on the destination file. A fold may not land a task that fails fields a, d, f or h unless it carries the refinement or a NEEDS-OWNER/NEEDS-OPERATOR marker.
2. **The rowflow publish gate (backlog-churn-flow).** Refuse to publish an inference row whose source box fails field c, or whose spec lacks `result_path`, `decision_rule`, an `estimate_s` that cites a run, or a region. Refuse a non-inference payload in a row; that is the gitnexus whole-host incident.
3. **`index_state.py --check`.** Add a warn-only readiness column per handoff. Make it blocking after the fold sweep, once the fields f and e false-positive rates are re-measured.
4. **The wrap-up gate.** A newly authored box must pass the lint.

## 7. Refinements file

`task-readiness-refinements-20261102.json` has one record per deficient task, 1,981 in all. Each record carries:
- the task's identity, matching the manifest (`id`, `task_id`, `src`);
- `failed`;
- `proposed` per field. The text is derived from the same section of the handoff and cites `file:line@3ac825873dfb` for each derived line. Otherwise it is marked NEEDS-OWNER. Fields with operator decisions are marked NEEDS-OPERATOR with the quoted sentence.
- `flags`;
- `destination`: the manifest's `dest_file`, `dest_section` and `new_row`, applied during that file's atomic fold commit.

No numbers were invented. When a field-d fix proposes IDs, they come from the manifest's `track_gate` and nowhere else.

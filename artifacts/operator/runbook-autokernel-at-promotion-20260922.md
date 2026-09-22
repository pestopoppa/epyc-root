# AutoKernel after the 2026-09-21 v10 store promotion — audit

**Date:** 2026-09-22 · **Mode:** read-only investigation · **Companion patch:**
`runbook-autokernel-at-promotion-20260922.patch` (validated with `git apply --check`;
NOT applied).

All file:line citations verified by reading the file. Paths under
`epyc-inference-research` are relative to `/workspace/repos/epyc-inference-research`.

---

## 0. The one finding that matters

`autokernel/loop/production.py:115-127` (`resolve_frozen`) resolves "frozen production"
**live from the git tree** `/mnt/raid0/llm/llama.cpp`, checking that its branch starts with
`production-consolidated-` (`:75`, `:79`). That tree is still on
`production-consolidated-v9` @ `0db32c06e` — verified by `git -C /mnt/raid0/llm/llama.cpp
rev-parse --abbrev-ref HEAD`.

The v10 promotion was **store-only**: `kernels/production/{cpu,gpu}` →
`builds/{cpu,gpu}-20260921-ffc1bac82/bin`, no branch cut.

So the next `production.refresh` will publish a champion-vs-production headline measured
against **v9**, silently, while production serves `ffc1bac82`. The module's own header
quotes the operator on exactly this: *"once we promote a new frozen version in the future,
the comparison should be against the newly promoted version, NOT stale v9. This is a
classic mistake."* The live-resolution design was built to prevent it — and a store-only
promotion defeats it from the other side, because the resolver's input never moved.

**This is failure mode (d) from the brief, and it is live.**

---

## 1. Findings table

| # | Item | file:line | Verified state | Broken? | Impact |
|---|---|---|---|---|---|
| 1 | Frozen-production resolution | `scripts/kernel_rnd/autokernel/loop/production.py:75,79,115-127` | Resolves live from `/mnt/raid0/llm/llama.cpp`, which is on `production-consolidated-v9` @ `0db32c06e` | **YES** | Headline measures against v9; the +5.6% already shipped is re-published as a champion gain. Double-count. |
| 2 | Aggregate standing file | `/mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json` | `baseline.commit = 0db32c06e…`, `champion.commit = bff30cebe…`, `effect_fraction = 0.05633`, `champion.build = …/anchor-gen-021` | **YES** | Both arms are now historical. The number is shipped gain presented as champion advantage. |
| 3 | Accumulator bundle | `/mnt/raid0/llm/autokernel/loop-memory/accumulator-bundle.json` | `champion_of_record: 445e93a8`, `tip: ef81196d5…`, 6 keeps, `compounded_bench_pct: 5.958`, `measurement_validity: stale_external_tip_advance` | **YES** | Already self-declared stale at `ef81196d5`; the champion has since moved twice. Carries a closed cycle's compounded percentage into the next one. |
| 4 | Champion branch name | `autokernel/loop/champion.py:47` `CANONICAL_BRANCH = "ak/champion/llama-cpp-0db32c06e3e5"`; mirrored `pool.py:55`, asserted `loop/test_champion.py:139` | Branch exists, tip = `ffc1bac82` | **STALE-BUT-HARMLESS today, BREAKS at rename** | The guard compares a branch **NAME** (`verify_worktree`, `champion.py:69-86`), not a commit or a build. It would start fine at `ffc1bac82`. It breaks the moment the new champion is named. |
| 5 | Champion worktree | `pool.py:50` `CHAMPION_TREE = /mnt/raid0/llm/tmp/ak-loop-tree` | **Directory does not exist.** The champion branch is checked out at `/mnt/raid0/llm/tmp/champ2` instead (`git worktree list --porcelain`) | **YES (pre-existing, not caused today)** | `champion.verify_worktree` would refuse at startup: the loop cannot start with default args right now. Independent of the promotion, but it is on the critical path to restart. |
| 6 | Anchor generations | `loop-memory/anchor-gen-020/provenance.json` (`champion_commit: fe881991f…`), `anchor-gen-021/provenance.json` (`bff30cebee…`); `anchor-cabac2563-clean` has **no** `provenance.json` | Both name pre-promotion commits, both still ancestors of the champion tip | **STALE-BUT-HARMLESS mechanically, SEMANTICALLY WRONG** | `verify_anchor` (`champion.py:149-194`) only requires ancestor-or-equal, so these PASS. They are old-cycle baselines that the guard will not reject. |
| 7 | `--anchor-build` in the loop | `autokernel/loop/run.py:542` (`required=True`); `:6` is docstring example only | No default | **NO** | The loop cannot silently inherit `build-anchor-j64`. |
| 8 | `--anchor-build` defaults in probes | `scripts/benchmark/autokernel_aa_campaign.py:102`, `scripts/benchmark/autokernel_force_mmq_probe.py:45` — both `default=Path("/mnt/raid0/llm/tmp/build-anchor-j64")` | Path **exists**; it is build 10125 @ `0db32c06e` — i.e. the *former* production | **YES** | Anything run with defaults now anchors on an old kernel while believing it anchors on production. Silent. |
| 9 | Serving floor identity | `/mnt/raid0/llm/autokernel/loop-memory/serving-floor.qwen3.8-27b-q8-gpu-dflash2-np4.json` | Keys: `recipe`, `recipe_hash` (`29fbffc5…`), `floor_pct 7.249`, `n 24`, `unit process`. **No `build` field, no `commit` field.** Build identity exists only as prose in `conditions.host_state` | **NO (mechanically)** | The floor is a dispersion measure keyed by recipe identity (`loop/test_serving_floor_identity.py:1-24`; refusal on hash mismatch). `run._gate_floor` (`run.py:365-375`) reads only `(pct, unit)` and never compares a build. It survives the promotion. |
| 10 | Serving floor record accuracy | same file, `conditions.host_state` | Says the build is the `$ORIGIN` rebuild at **`kernels/builds/gpu-20260921-ef81196d5` (build 10301)** | **RECORD DISCREPANCY** | The brief states the floor was measured on `gpu-20260921-ffc1bac82`. **The file says `ef81196d5` / 10301.** One of the two is wrong; the file is the primary record. Flagging, not resolving. |
| 11 | `qwen38_flash_next_recipe.py` CHAMPION_* | `scripts/lib/qwen38_flash_next_recipe.py:214-217` | `CHAMPION_COMMIT = 9c4f73e29…`, `CHAMPION_TREE`/`CHAMPION_BINDIR` = `/mnt/raid0/llm/worktrees/inf70/champion2` (exists) | **NO — by design** | These are explicitly the *measurement pin* (champion3, build 10241), documented at `:195-212` as NOT the current champion. They were never claimed to track the champion. Unchanged by today. |
| 12 | `CURRENT_CHAMPION` | same file, `:233-300` | `commit: ef81196d5`, `branch: ak/champion/llama-cpp-0db32c06e3e5`, `source_dir: /mnt/raid0/llm/tmp/champ2` (exists, now at `ffc1bac82`) | **YES** | Champion advanced twice past `ef81196d5`; `source_dir` now holds a different commit than the one this dict names. A reader trusting `source_dir` + `commit` together gets a contradiction. |
| 13 | `CURRENT_CHAMPION["builds"]` | same file, `:262`, `:296` | `/mnt/raid0/llm/tmp/build-fold-ef81196d5` and `/mnt/raid0/llm/tmp/build-champion-ef81196d5-cpu-20260909` — **both exist** | **STALE-BUT-HARMLESS** | Not dangling. They are honest records of `ef81196d5`, which is now an ancestor of production. Correct as history, misleading as "champion builds". |
| 14 | `HEADLINE_BINARY` / `CHAMPION_PIN_RESOLVED` | same file, `:382-429` | `CHAMPION_PIN_RESOLVED = False`; `HEADLINE_BINARY` = build 10303, `2516c9807` on `inf70/retest1-fix1`, bindir exists | **NO — pre-existing, unrelated** | Note the collision hazard: `HEADLINE_BINARY` is build **10303** and so is the promoted v10 kernel, but they are *different commits* (`2516c9807` vs `ffc1bac82`). Quoting "build 10303" without a commit is now ambiguous. |
| 15 | Hardcoded production constants | `autokernel/campaign.py:1148-1150`; `autokernel/evaluator/c3_epyc_suite.py:45-47`; `autokernel/controller/discovery_deployment.py:28-30` | All pin v9 (`0db32c06e…`, `production-consolidated-v9`, version `10125 (0db32c06e)`) | **YES once v10 is cut; today they match the frozen tree** | They agree with the *tree* and disagree with the *store*. `c3_epyc_suite.PRODUCTION_V9_VERSION = "10125 (0db32c06e)"` would fail against a served binary reporting `10303 (ffc1bac82)`. |
| 16 | Instrument branch pin | `autokernel/controller/discovery_deployment_factory.py:480` `_INSTRUMENT_BRANCH` | Same old champion name; `_INSTRUMENT_PATH:466` = `/mnt/raid0/llm/llama.cpp-experimental` (exists) | **STALE-BUT-HARMLESS today, BREAKS at rename** | Second by-name reference to the champion branch. |
| 17 | Champion-branch literals outside autokernel | `scripts/benchmark/serving_evidence_refresh.py:70`; `scripts/benchmark/boundary_20260831.sh:65`; `scripts/benchmark/emit_operator_gate_bundle.py:149` | All default to `ak/champion/llama-cpp-0db32c06e3e5` | **BREAKS at rename** | Three more by-name consumers. |
| 18 | Store resolution inside autokernel | sweep of `scripts/kernel_rnd/` for `kernel_paths` | **`kernel_paths.py` exists only in `epyc-orchestrator/src/registry/`.** No autokernel module imports it | **YES, structural** | AutoKernel has no store-resolution layer at all; every kernel it touches is an absolute path or a git ref. This is the same class as `kernel_freeze_scope.py` / `dashboard_topology.py`, un-remediated on the research side. |
| 19 | Substring backend sniffing in autokernel | `autokernel/release/plan.py:465-466`; `autokernel/release/packager.py:1937-1938`; `autokernel/execution/t0_provider.py:418`, `:2602` | These are **defensive**: the comments explicitly warn that `str.startswith` is not path containment and that `/mnt/raid0/llm/llama.cpp` is a prefix of `-experimental` | **NO** | Correct handling already. `t3.py:1375-1376` hardcodes `/mnt/raid0/llm/llama.cpp/build/bin` and `llama.cpp-dflash/build/bin` in a list — pre-store literals, stale. |
| 20 | Loop start guard semantics | `autokernel/loop/champion.py:69-86` (`verify_worktree`), `:149-194` (`verify_anchor`), `:220-231` (`verify_startup`) | Compares branch **NAME** + attached-at-tip, plus anchor `provenance.json:champion_commit` ancestor-of-HEAD | Answers brief item 5: **name-based.** Would start correctly at `ffc1bac82`; would NOT notice that `ffc1bac82` is now production. | The guard proves lineage, never *era*. Nothing in it asks "is my base already shipped?" |

---

## 2. The doctrinal question, as settled

**(a) Wording and location.** `agents/shared/OPERATING_CONSTRAINTS.md:140-143`:

> **The lifecycle is a cycle, not a tree.** Promotion N → that tree's champion := its
> production state (the aggregate is empty) → every improvement on that tree merges IN →
> promotion N+1 → reset. "Seed the champion from frozen production" is correct in exactly
> ONE moment: immediately after that tree's promotion. Applied mid-cycle it silently
> discards the accumulated research.

Section header at `:126`; origin incident at `:159-164`.

**(b)–(c) Superseded by the operator ruling of 2026-09-22:** *"a new champion should be
instantiated off of the newly promoted frozen kernel."* A new branch, seeded from the newly
promoted frozen kernel; the old champion retires. Not written up as a decision package.

**(d) What breaks if skipped** — items 1, 2, 3 above. Concretely: the loop would restart with
`champion-vs-production.json` asserting +5.633% over a "production" that already contains
those gains, and `accumulator-bundle.json` carrying six keeps and +5.958% compounded from
the closed cycle. Every one of those percentages has shipped.

---

## 3. Coordinator questions 1–5

### 1. Naming

The convention is **`ak/champion/llama-cpp-<12 hex of the production commit the champion was
seeded from>`**. Evidence: the current name encodes `0db32c06e3e5` = the first 12 hex of v9's
`0db32c06e3e550065b78311a6031ef3dd2c4f27c` (`champion.py:47`; incident narrative at
`champion.py:8-12` describes it as "+3371/−146 over v9"). The sha in the name is the SEED,
not the tip — the tip has moved 50+ commits and the name never changed.

So the new branch is **`ak/champion/llama-cpp-ffc1bac82eec`** — *provided* `ffc1bac82` is what
gets frozen as v10. If the freeze is cut at a different commit, the name follows the freeze.

`0db32c06e3e5` also appears as a substring test in `tests/test_dashboard_champion_headline.py:1058`
(`"0db32c06e3e5 in gate"`), which is a second name-coupled consumer.

### 2. The awkward part — my read, stated plainly

**The ruling implies cutting `production-consolidated-v10` at `ffc1bac82`. The invariant
cannot be satisfied without it.** Three independent reasons:

1. **Mechanical.** `production.resolve_frozen` (`production.py:115-127`) refuses any branch
   outside `production-consolidated-*` and otherwise returns whatever that tree's HEAD is.
   There is no store-aware path. With the tree on v9, "the champion's standing versus the
   CURRENT frozen production state" — required by `OPERATING_CONSTRAINTS.md:147-151` — is
   *uncomputable*, because the only resolver in the codebase returns v9.

2. **Semantic.** "Instantiate off the newly promoted frozen kernel" presupposes a frozen
   kernel. Right now the promoted kernel exists as a commit on a *research* branch plus two
   symlinks. Seeding `ak/champion/llama-cpp-ffc1bac82eec` from `ffc1bac82` while the freeze is
   uncut gives a champion whose seed is a commit that nothing attests as production — exactly
   the unattested-base condition `champion.py` exists to refuse.

3. **Already recorded as incomplete.** The promotion's own qualification record says so:
   `artifacts/operator/v10-qualification-20260921-ffc1bac82.json:4` — `"status": "INCOMPLETE
   — store-side cutover done and serving, but the FREEZE is NOT cut. There is no
   production-consolidated-v10 branch, no FREEZE-V10 ratification, and verify_llama_cpp.sh
   still attests v9/10125 while the store serves 10303."` And
   `artifacts/operator/kernel-freeze-runbook-hardening-20260922.md:70` (gap **G3**) reaches
   the same conclusion from the verifier side.

**On the "no-op" concern:** seeding the new champion from `ffc1bac82` when the old champion's
tip is also `ffc1bac82` is *not* a no-op, and the coordinator's framing slightly overstates it.
The branch ref is the cheap half. The reset that matters is the **aggregate** (§3.3) — and that
is a real state change regardless of whether the two refs point at the same object. What *is*
true is that without the v10 branch the new champion is seeded from a research ref rather than
a production ref, which is the defect.

**Can the invariant be satisfied without touching the frozen tree?** Not with today's code.
It could be *made* satisfiable by teaching `resolve_frozen` to resolve production from the
kernel store (`kernels/production/<B>` → `PROVENANCE.md` → commit) instead of from the tree.
That is a genuine design option, it removes the frozen-tree write from the promotion path
permanently, and it is more work than cutting a branch. **The record is silent on whether
store-only promotions are intended to be the norm** — I am not inventing doctrine here.
Cutting v10 is the path the existing code, the runbook (step 8f) and the qualification record
all already assume.

### 3. What must be true so the next run does not double-count

Four conditions, all verifiable before the loop starts:

1. **`champion-vs-production.json` does not carry the closed cycle's number.** Delete it (or
   rewrite both arms). The dashboard renders SUPERSEDED when it is absent or its
   `baseline.commit` is not the frozen commit (`dashboard/loop_status.py:1094-1103`), which is
   the correct degraded state — `production.py` is explicitly designed never to raise on this
   path.
2. **`accumulator-bundle.json` starts empty**: `keeps: []`, no `compounded_bench_pct`,
   `champion_of_record` = `tip` = the new seed commit.
3. **The frozen tree resolves to the new freeze**, so `resolve_frozen()` returns the promoted
   commit and the first A/B is champion-vs-itself.
4. **No `anchor-gen-*` from the old lineage is reachable as `--anchor-build`.** They pass
   `verify_anchor` on ancestry (`champion.py:183-194`) and therefore cannot be relied on to
   self-reject.

The testable invariant: **the new champion's standing versus production must read zero by
construction, and the first keep of the new cycle must be the first non-zero number.** A
headline gain before the first keep means the reset did not happen.

### 4. Command sequence, with frozen-clone exposure flagged

`⚠ FROZEN CLONE` marks a write into `/mnt/raid0/llm/llama.cpp`'s git directory. Per CLAUDE.md
→ *Production kernels are FROZEN*, these need explicit operator authorization. **None of them
modifies, rebases, builds or commits to the production branch** — but steps 1 and 2 do check
out and create refs in that clone, and step 1 moves its working tree. Name them in the
authorization rather than treating them as incidental.

```bash
# 1 ⚠ FROZEN CLONE — cut and adopt the freeze (operator-authorized)
git -C /mnt/raid0/llm/llama.cpp branch production-consolidated-v10 ffc1bac82
git -C /mnt/raid0/llm/llama.cpp checkout production-consolidated-v10

# 2 ⚠ FROZEN CLONE — instantiate the new champion off the freeze
git -C /mnt/raid0/llm/llama.cpp branch \
    ak/champion/llama-cpp-ffc1bac82eec production-consolidated-v10
git -C /mnt/raid0/llm/llama.cpp worktree add \
    /mnt/raid0/llm/tmp/ak-loop-tree ak/champion/llama-cpp-ffc1bac82eec

# 3  loop-memory reset — NOT the frozen clone
mv /mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json \
   /mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json.pre-v10
#    rewrite accumulator-bundle.json: keeps [], tip = ffc1bac82…, cor = ffc1bac82…
#    retire anchor-gen-020 / anchor-gen-021

# 4  source edits in epyc-inference-research — ordinary commits, no frozen clone
#    (the constants in §1 items 4, 15, 16, 17)
```

Notes on the sequence:
- Step 2's `worktree add` also repairs finding 5 (`ak-loop-tree` currently missing). The old
  champion branch stays checked out at `/mnt/raid0/llm/tmp/champ2`; retiring it is a separate,
  later act — **do not delete it before the v10 ratification lands**, it is the only working
  tree holding the promoted source.
- Step 1 moves the frozen clone's working tree from v9 to v10. Confirm no build or benchmark
  is reading `/mnt/raid0/llm/llama.cpp/build/bin` at that moment. The production stack now
  serves out of `kernels/production/`, so it should not be — verify, do not assume.
- I have **not** run any of these. Read-only audit.

### 5. By-name references that break at the rename

| Reference | file:line | Kind |
|---|---|---|
| `CANONICAL_BRANCH` | `autokernel/loop/champion.py:47` | The start guard's own constant — **the load-bearing one** |
| assertion on it | `autokernel/loop/test_champion.py:139` | Test, fails by design |
| `CHAMPION_BRANCH` | `autokernel/loop/pool.py:55` | Aliases `CANONICAL_BRANCH`; no separate edit |
| `_INSTRUMENT_BRANCH` | `autokernel/controller/discovery_deployment_factory.py:480` | Independent literal |
| `CHAMPION_BRANCH` | `scripts/benchmark/serving_evidence_refresh.py:70` | Independent literal |
| `BOUNDARY_CHAMPION_BRANCH` default | `scripts/benchmark/boundary_20260831.sh:65` | Env-overridable default |
| `--champion-branch` default | `scripts/benchmark/emit_operator_gate_bundle.py:149` | argparse default |
| `CURRENT_CHAMPION["branch"]` | `scripts/lib/qwen38_flash_next_recipe.py:245` (+ test at `test_qwen38_flash_next_recipe.py:283`) | Data record |
| substring gate | `tests/test_dashboard_champion_headline.py:1058` (epyc-root) | `"0db32c06e3e5 in gate"` |
| card fixture | `tests/test_dashboard_champion_card.py:60` (epyc-root) | Fixture |
| example invocation | `docs/guides/agent-workflows/agent-loop-design.md:287` | Docs |

**No loop-memory record names the branch.** They key on commits
(`champion-vs-production.json`, `accumulator-bundle.json`, `anchor-gen-*/provenance.json`) —
verified by reading each. So the rename is a source-and-docs change; the memory reset is a
separate, commit-keyed change.

`warn_divergence` (`champion.py:196-218`) handles the rename gracefully: an
ancestor/descendant relationship between old and new champion tips "is the legitimate rename
case and stays quiet". Seeding v10's champion from `ffc1bac82` — the old champion's own tip —
satisfies that, so no spurious divergence warning.

---

## 4. Do NOW vs. documentation only

### Must be done now to leave AutoKernel consistent

These are the ones where *doing nothing* produces a wrong number or a wrong start:

1. **Cut `production-consolidated-v10` and adopt it in the frozen tree.** Operator-authorized.
   Everything else is blocked on it (§3.2). Until then, `production.refresh` publishes a v9
   baseline.
2. **Quarantine `champion-vs-production.json`.** One `mv`. Removes the live double-count
   surface even before the branch is cut.
3. **Reset `accumulator-bundle.json`.** Six keeps and +5.958% from a closed cycle.
4. **Instantiate `ak/champion/llama-cpp-ffc1bac82eec` and re-create `/mnt/raid0/llm/tmp/ak-loop-tree`.**
   The loop cannot start today regardless (finding 5).
5. **Repoint or de-default `--anchor-build` in `autokernel_aa_campaign.py:102` and
   `autokernel_force_mmq_probe.py:45`.** `build-anchor-j64` exists and is a former-production
   binary; anyone running those with defaults gets a silently wrong anchor. Making them
   `required=True` is the cheaper, safer fix.
6. **Update `CANONICAL_BRANCH` + the five other by-name literals** at the moment the new
   branch exists, or the guard refuses every start.
7. **Resolve the serving-floor record discrepancy (finding 10).** The file says the floor was
   measured on `gpu-20260921-ef81196d5` (10301); the handoff brief says `ffc1bac82`. One record
   is wrong and it is the GPU gate bar. Cheap to settle, expensive to discover later.

### Documentation / hardening — real, but nothing is measuring wrong meanwhile

8. Land the runbook section (the companion patch).
9. `c3_epyc_suite.PRODUCTION_V9_*`, `campaign.PRODUCTION_*`, `discovery_deployment.FROZEN_PRODUCTION_*` —
   update with the freeze. They currently agree with the tree, so they are self-consistent
   until step 1 lands, and inconsistent the moment it does. Sequence them *after* step 1.
10. Reconcile `qwen38_flash_next_recipe.CURRENT_CHAMPION` (finding 12) — `source_dir` and
    `commit` now contradict each other.
11. Note the **build-10303 ambiguity** (finding 14): `HEADLINE_BINARY` (10303, `2516c9807`) and
    the promoted v10 kernel (10303, `ffc1bac82`) share a build number and are different
    binaries. Any future citation of "build 10303" needs its commit.
12. **Structural, larger than this promotion:** AutoKernel has no store-resolution layer —
    `kernel_paths.py` lives only in `epyc-orchestrator` and no autokernel module imports it
    (finding 18). Every future promotion will keep producing this same class of breakage until
    that is addressed. Worth its own handoff row rather than a runbook paragraph.

---

## 5. Where the record is silent

- **Whether store-only promotion is the intended steady state.** The runbook's step 8f files
  this as an open operator decision; nothing states a policy. I have assumed cutting the branch
  is intended, because the code, the runbook and the qualification record all assume it — but
  that is inference, not doctrine.
- **What happens to a retired champion branch** (delete / tag / keep). No rule exists. I
  recommend keeping it until the v10 ratification lands, because `/mnt/raid0/llm/tmp/champ2` is
  currently the only checkout of the promoted source.
- **Whether the aggregate reset is a delete or a rewrite-in-place.** `OPERATING_CONSTRAINTS.md:141`
  says only "the aggregate is empty". `production.py`'s design tolerates absence gracefully
  (SUPERSEDED), which is why I recommend quarantine-by-rename over hand-editing.

# PromptForge mutation safety contract (RTG-55)

**Status**: stub
**Created**: 2026-09-07 (research intake, operator-approved plan; successor of ../completed/meta-harness-optimization.md whose active pointer was retired 2026-08-23)
**Categories**: meta_harness, autopilot, safety
**Related**: [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) (RTG-02) · [eval-tower-verification.md](eval-tower-verification.md) (EVL-14) · [agent-collab-rnd-harness.md](agent-collab-rnd-harness.md)

## Objective

Constrain what a PromptForge mutation may DO — not merely which files it may touch — so that mutation
safety is a compile-time property of the harness rather than a promise made in prompt text. The
lineage's active pointer was retired 2026-08-23 and the completed ledger forbids new task checkboxes,
so this is a **new active stub, not a reopen**.

## Research Context

| Entry | State | What it contributes |
|---|---|---|
| `intake-1323#record` | dive-verified | Harness-R1's typed return-effect contract, AST denylist, forbidden-text patterns, the ANTI-OVERRIDE prior, and the `examples/heldout_generalization/` corpus |
| `intake-1317#record` | dive-verified | Optimizer budget shape (constant in training-set size, large constant) |
| `intake-1320#record` | stage-1 / bearing | JIT admission-rule comparison context (the archive/admission half lives in AP-51) |

## Tasks

- [x] **MHS-1 — Typed return-effect contract.** Constrain what a mutation may DO (a closed per-site
      effect enum, host-normalized and truncated), not only which FILES it may touch. Reference
      implementation: Harness-R1 `code_runner.py:31-34` + `_normalize_hook_result`, ~50 lines.
      *Highest value, cheapest.* `intake-1323#record` (dive actionable D0). Zero compute. ✅ 2026-09-14 — `MutationEffect`
      (`inert|constrain|expand|replace|unsafe|unknown`) with total `normalize()` (aliases in, unrecognised ⇒
      `UNKNOWN`, tokens truncated at 32 chars, reasons at 240); `CodeMutation.effect`/`.effect_reason`; both
      `apply_code_mutation*()` refuse `UNSAFE` and report `effect`. CONSTRAIN/REPLACE derived mechanically
      (answers Open Question 3 — no separate label needed). epyc-orchestrator `7d4b40a8`, tests
      `test_effect_enum_is_closed`, `test_effect_normalization`, `test_unrecognized_effects_normalize_to_unknown`,
      `test_classify_*`, `test_apply_rejects_unsafe_effect`, `test_apply_in_context_reports_effect`.
- [x] **MHS-2 — Close the MH-9 inertness hole.** The AutoMem `schema_evolution` `new_file` lane
      requires "default-inert" modules as **prompt text only** (`prompt_forge.py:1261-1277`) while
      `_validate_code_mutation`'s importlib step (`:1147`) executes the module top level
      **unsandboxed in the live repo**. Add an AST node denylist
      (`Import/ImportFrom/With/While/Lambda/ClassDef/Raise/Global/Delete/Yield/Await`) plus
      dunder/underscore `Name` + `Attribute` rejection over `new_file` proposals, modelled on
      `code_runner.py:64-103` and `:170-176`, so inertness is **compile-time, not a promise**. MH-9's
      own row already anticipated this ("keep edit-only allowlist until a stronger isolation story
      exists") — this IS that story. `intake-1323#record` (dive actionable D1). Zero compute. **Depends on MHS-1** (the effect
      enum is the denylist's contract). ✅ 2026-09-14 — the repo-write + in-process `importlib` step
      (`origin/main` `prompt_forge.py:1149`/`:1157`) is GONE; validation is static-only
      (`screen_static_safety`), with the ratified strict node denylist + underscore/dunder rejection for
      `new_file`, a capability denylist with original-file grandfathering, and the MH-9 prompt rewritten to
      the shape the screen admits (`MEMORY_SCHEMA_SHAPE_EXAMPLE` screened in CI, so prompt/denylist drift
      cannot recur). epyc-orchestrator `7d4b40a8` + `c27eec6c`; 100 tests incl.
      `test_validation_never_writes_the_target_file`, `test_validation_does_not_import_the_candidate_module`,
      `test_strict_profile_rejects_denylisted_nodes` (11 cases),
      `test_noop_mutation_of_every_allowlisted_file_passes`, `test_prompt_shape_example_passes_the_strict_screen`,
      `test_old_class_shaped_proposal_is_rejected_by_the_strict_screen`. Selection 40 → 140 passed.
- [x] **MHS-3 — Missing half of the transfer guard.** ✅ 2026-09-17 (landed with the AutoPilot merge train, orchestrator `a1a0251a` on main, which contains `6df6f0d8`; the notes below that say "not yet on main" predate the landing). `_UNIVERSAL_TRANSFER_RE`
      (`prompt_forge.py:83-88`) rejects OVER-generalization (`always|never|all tasks`); Harness-R1's
      `FORBIDDEN_TEXT_PATTERNS` (`harness_r1_patch.py:233-238`) rejects **UNDER**-generalization (a
      patch naming a specific eval task id / sample index / item id). We have **no** guard against a
      mutation memorising the eval set by naming its instances. Add an anti-leakage pattern set over
      accepted mutation text keyed to our suite/task identifiers. `intake-1323#record` (dive actionable D2). Zero compute.
      **Structural form (2026-09-15):** the refusal lives in _transfer_safety_verdict and returns
      valid=False when a mutation's added text — prompt mutations AND code_mutation mutated_content
      (string literals, comparisons) — shares a verbatim ≥8-token n-gram with, or an exact expected
      answer from, the current draw, sentinel_questions.yaml, tool_sentinels.yaml or the contrastive
      trace bank. Record the matched source id. It also refuses in-suite special-casing, which the
      current check allows (it refuses only suites absent from the source context).
      **Source-identity key:** it ALSO refuses a mutation whose few-shot or example content was
      derived from a trace of a question in the current draw. The key is the question id or sentinel
      id carried in the contrastive trace-bank records (actions.py trace context; eval_tower.py
      fixed 20-trial draw), not only a verbatim n-gram, because paraphrase bypasses n-gram matching.
      BAITBENCH entity-overlap and near-duplicate shortcuts had take-rates of 82.5% and 72.5%
      (intake-1395#record). One leakage checker serves prompt and code mutations. Instruction text
      ("don't overfit") is not the fix (intake-1379#record; intake-1395#record, where validity
      prompting moved -6.2 pp). EvilGenie partial-hardcoding class (intake-1387#record).
      ⏳ PARTIAL 2026-09-16 (`sub-autopilot-safety`, orchestrator `8219d8e8` on branch
      `sub/autopilot-safety-20260916`, NOT yet merged; box stays open: structural form completed on `sub/mhs3-complete-20260916`, see below): `EvalIdVocabulary` + `eval_leakage_reason()`
      in `prompt_forge.py`, applied to the ADDED text of prompt, code and GEPA mutations. The vocabulary
      comes from eval data, not a hand list: research `question_pool.jsonl` (required), `core_*.jsonl`
      and the sentinel YAMLs → 153,450 ids (pool ids, nested core qids, prompt-hash qids), 295 id
      families derived from them, and suite/id-stem anchored references, plus a qualified generic
      pattern (`sample #12`, `task_id == 17`). **Fail-closed**: a missing or unreadable pool rejects
      every mutation (`eval_leakage_vocabulary_unavailable`). Measured false positives: 0 over all 33
      current prompt + allowlisted code targets (a regression test pins this), and 1 file of 444
      docs/src files, where both hits were real instance references. Open Question 2: keyed on ids plus
      prompt-hash qids (content hashes of text); image-bound qids are not included.
      `tests/unit/test_prompt_forge_leakage_and_risk.py` (73 tests).
      Operability (loud fail-closed state: startup preflight, alarm after 3 consecutive
      `eval_leakage_vocabulary_unavailable` rejections, runbook `docs/guides/meta-harness-operator-guide.md` § 7)
      built on branch `sub/gate-frontier-20260916`, under review, unmerged (2026-09-16, `sub-gate-frontier`).
      **Structural form built 2026-09-16 (`sub-mhs3b`, orchestrator `6df6f0d8` on branch
      `sub/mhs3-complete-20260916`, built on `sub/gate-frontier-20260916`; carried by the AutoPilot merge train
      `sub/autopilot-train-20260916`, not yet on main; flip the box when it lands):** `_transfer_safety_verdict`
      and the GEPA path now also refuse, over the ADDED text: `eval_content_ngram_overlap` (verbatim >=8-token
      overlap with the pool/cores/sentinels or the rendered trace bank; hashed shingles packed with row id,
      ~1.3e-7 FP per shingle, template df >=32 dropped, anchor-or-15-token-run rule),
      `eval_expected_answer_leakage` (name-shaped 1-7 token answers), `eval_source_identity_leakage` (trace
      blocks resolved to question/sentinel ids; >=3 shared rare tokens, paraphrase-proof) and
      `eval_suite_special_casing` (keyed/phrase/mention, in-suite included). Matched source id in every reason.
      Same pass, cache and fail-closed state as the id vocabulary; harness text (prompts, src/, original) is never
      blamed. Real pool: 16 s cold, +590 MB RSS (index 173 MB, 1.37 GB transient peak), ~9 ms per edit. FP: 0/33
      live targets; content 0/91 historical mutations (special-casing 2/91 borderline); 2.4% of 467 whole
      src/docs files. Coverage 1998/2000 verbatim pool prompts. Runbook § 7 extended.
      `tests/unit/test_prompt_forge_content_leakage.py` (51 tests). Detail:
      `progress/2026-09/2026-09-16-sub-mhs3b.md`.
  - [x] **MHS-3a — remove the pool leak MHS-3 found in live harness text** ✅ 2026-09-16 (orchestrator
        `09bdb998` on main). Pool row `simpleqa_general_00912` (Aschoff / Bonn) was a worked example in
        `orchestration/prompts/rules.md` Example 4b and `DEFAULT_ROOT_LM_RULES`; both now use a synthetic
        example, and a dormant HumanEval/55 copy in `src/prompts/coder_system.txt` was replaced too. Takes
        effect at the next API reload (owned by the session that owns inference).
        Detail: `progress/2026-09/2026-09-16-sub-leak00912.md`.
  - [x] **MHS-3b — close the rewind hole: operator RATIFY of the checkpoint prompt re-pin.** ✅ 2026-09-17 RATIFIED by the operator (root `b8379d42`): all 10 checkpoint copies re-pinned to `18f8ea01`, originals in `/mnt/raid0/llm/backups/ckpt-leak-20260916/`. Operator chose
        option A (2026-09-16). Ten AutoPilot checkpoints, including production_best (multitier_v10), still
        carry the leaked `rules.md` (`b250c227…`), and `restore_checkpoint()` copies it back. Script landed on
        root main (`0e2bbc33`); the operator runs
        `bash -c 'bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ckpt_leak_ratify_20260916.sh) --operator pestopoppa'`
        and types RATIFY (refuses while AutoPilot holds its lock). Detail: `progress/2026-09/2026-09-16-sub-ckpt-leak.md`.
  - [ ] **MHS-3c — clean the out-of-scope leak copies** that MHS-3b leaves: 4 HumanEval/55 task memories in
        `episodic.db` (in every checkpoint and the live store) and Aschoff in `autopilot_state*.bak*`
        `last_traces`. Purge tool: orchestrator `41baad2b` (`scripts/maintenance/purge_eval_leak_memories_20260917.sh`),
        backups and receipt in `/mnt/raid0/llm/backups/episodic-leak-20260917/`.
    - [x] Offline stores and state backups purged ✅ 2026-09-17: 11 checkpoint/backup `episodic.db` copies
          (4 rows + FAISS entries each, health OK) and 15 state backups redacted. `--verify` PASS. The first run
          was cut off by a caller timeout at item 19 with no damage (the original was intact); the re-run finished.
    - [x] Live store purged ✅ 2026-09-17 during the API stop window (API down, verified): 4 memories removed,
          health OK, `--verify --include-live` PASS. The reloaded API reported 64,204 entries (was 64,208).
    - [x] Pinned production_best (multitier_v10) store ✅ 2026-09-17: purged with operator approval, 4 rows + FAISS, health OK, verify PASS incl. live+pinned.
          The new hashes are in `pinned_repin_proposal.json`. The v10 pins still name the pre-purge
          bytes until MHS-3d is ratified.
  - [ ] **MHS-3d — operator RATIFY of the v10 episodic re-pin** (`RATIFY-V10-EPISODIC-REPIN-20260917`). From a host terminal:
        `docker exec -it -u node epyc-root bash -c 'bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_v10_episodic_repin_ratify_20260917.sh) --operator pestopoppa'`
        and type RATIFY. It re-pins `checkpoint_meta.json` (the three episodic file hashes and
        memory_count 63925 -> 63921; checkpoint_sha256 `a604276f` -> `3b457d98`) and the v10 receipt
        mirror, adds the amendments entries, and refuses while AutoPilot holds its lock. The dry-run
        preflight is clean against the real checkpoint. Its `--verify` supersedes the MHS-3b script's
        `--verify`, which the purge broke. Detail: `progress/2026-09/2026-09-17-sub-v10-repin.md`.
- [ ] **MHS-4 — ANTI-OVERRIDE risk prior.** Rank/gate mutations by CONSTRAIN (add a check, block a bad
      path, re-prompt) vs REPLACE (rewrite/force an action, hard-code an answer). In the released
      corpus the REPLACE-before-CONSTRAIN ordering holds on all 23 valid patches (REPLACE 4/4 negative,
      mean −8.4 pp; CONSTRAIN n=19, mean +3.9 pp), but the worst single patch is CONSTRAIN (−16.9 pp,
      hint-only), so the prior ranks risk and does not certify safety (MHS-5, orchestrator `4f28e6c3`);
      the trained editor converged constrain-only across all 9 patches and all 3 seeds. Encode as a
      mutation-type risk weight. `intake-1323#record` (dive actionable D4; the 2026-09-07 wording
      "every catastrophic regression came from an override" was refuted by MHS-5).
      Orchestrator `4f28e6c3` is on branch `sub/autopilot-safety-20260916`, pending merge. Zero compute. Consumer: AP-52 in
      [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md).
      **IMPLEMENTED 2026-09-16, NOT YET ON MAIN — flip on merge** (`sub-autopilot-safety`, orchestrator `8219d8e8`, branch `sub/autopilot-safety-20260916`, unmerged): `MUTATION_EFFECT_RISK`
      (inert 0.05 < constrain 0.25 < expand 0.50 < replace 0.90 < unknown 1.0 < unsafe ∞), carried as
      `effect_risk` on both `CodeMutation` and `PromptMutation`. Prompt text is now classified too
      (`classify_prompt_effect`). `rank_mutations_by_risk()` orders candidates safest-first. The gate
      `AUTOPILOT_MUTATION_RISK_GATE` (default 1.0 refuses only unclassified effects; 0.9 means
      constrain/expand-only; it can only be tightened) runs at propose time and again at both code
      apply paths, and the proposer prompt now carries the anti-override rule. **Weights are an ordinal
      prior, uncalibrated**. MHS-5 below supports the ordering but shows CONSTRAIN is not
      regression-free. Same test file.
- [ ] **MHS-5 — Mine `examples/heldout_generalization/` as a labelled contrastive corpus.** 23
      patches, 3 editors, identical 10-failure evidence, 3 seeds, per-patch sha256, hook sets,
      validation errors, rescued/regressed counts over 1,270 held-out tasks; Apache-2.0.
      Discriminating features already extracted by the dive: effect kind, hook-set stability,
      benchmark-scaled length, rescue:regression ratio. MH-7's contrastive-trace capture is the
      existing consumer. Feeds MHS-4. `intake-1323#record` (dive actionable D7). Zero compute.
      **IMPLEMENTED 2026-09-16, NOT YET ON MAIN — flip on merge** (`sub-autopilot-safety`, orchestrator `4f28e6c3`, branch `sub/autopilot-safety-20260916`, unmerged): sparse-fetched
      Harness-R1 @ `411bb548` (the dive-verified revision). `scripts/autopilot/species/heldout_effect_corpus.py`
      derives `orchestration/datasets/harness_r1_heldout_effect_corpus.json` with labels only, no patch
      code: 27 cells, sha256-verified, effect kinds read by AST and mapped onto `MutationEffect`, plus
      hooks, code length, delta, and rescued/regressed counts. **Result (23 valid patches):** the MHS-4
      ORDERING holds. All 4 REPLACE patches regressed (mean −8.4 pp, rescue:regression 0.21); the 19
      CONSTRAIN patches averaged +3.9 pp (1.65). **But the claim "every catastrophic held-out
      regression came from an override patch" does NOT hold on this corpus.** The single worst valid
      patch (DeepSeek-V4-Pro alfworld seed 20260721, −83 on 490 = −16.9 pp, 130 regressed) is
      hint-only (`inject_hint`). A block-only patch also lost 34 (−6.9 pp). 4 of 19 CONSTRAIN patches
      regressed. Confound: 9 of the 19 CONSTRAIN patches come from the trained Harness-R1 editor.
      Consequence: the MHS-4 weights stay ordinal; the gate ranks risk, it does not certify safety
      (code comment and operator guide updated). **Belief-kernel note — APPLIED 2026-09-16 (`sub-own`):** the refuted text was
      the MHS-4 row's own rationale, not key claim 04 of the entry (the handoff's `#NN` numbers indexed
      the dive actionables ledger, so `#04` was a mis-anchor; claim 04 is the true transductive-scope
      claim). Recorded in `research/intake_index.yaml` (`intake-1323#record`) as `dive_corrections` item (13) and
      a `dive_entry_corrections` row (effect `narrowed` on dive item (6)); claim 04's `claim_corrections`
      note re-examined, still `unaffected`. Evidence cited as orchestrator `4f28e6c3` on
      `sub/autopilot-safety-20260916` (pending merge), corpus sha256 `09ae7365…efbc71`. The MHS-4 row now
      cites `intake-1323#record` with the qualified wording. `tests/unit/test_heldout_effect_corpus.py` (15 tests) pins
      both the ordering and the refutation. MH-7 wiring was not done (out of scope for this row).
- [ ] **MHS-6 (record, no work) — Optimizer budget shape.** Record it as **"constant in training-set
      size, LARGE constant"**: 1 + T_ReAct calls/iteration, T_ReAct 10–20 at B = N_train ⇒ 11–21
      metered calls, vs EvoSkill 2N/B and SkillOpt K_opt·N/B (K_opt 6–8). At our split sizes this is
      **more** absolute calls. The completed file's pointer to
      `handoffs/active/meta-harness-optimization.md` is DANGLING — that file does not exist — which is
      why this stub, not a reopen, is the right shape. `intake-1317#03`. Zero compute.
- [ ] **MHS-7 — force the isolated mutation path.** `apply_code_mutation` writes the live tree directly
      (git-checkpointed) and the isolated `apply_code_mutation_in_context` exists but nothing requires its use
      (`scripts/autopilot/species/prompt_forge.py:~1440`) (found 2026-09-14, noninf sweep).
- [ ] **MHS-8 — tighten the apply gate to "only screened effects apply"**, since only `MutationEffect.UNSAFE`
      is refused today so `UNKNOWN` — the default on a hand-constructed `CodeMutation` — still applies; needs
      an audit of every construction site (`scripts/autopilot/species/prompt_forge.py`, apply gate)
      (found 2026-09-14, noninf sweep).
- [ ] **MHS-9 — narrow `revert_code_mutation`'s new-file revert from `git add -A <path>` to an explicit
      pathspec**, the idiom the project's hygiene rules warn about
      (`scripts/autopilot/species/prompt_forge.py:~1478`) (found 2026-09-14, noninf sweep).
- [ ] **MHS-10 — land a standalone formatting commit for `prompt_forge.py`**, which is format-dirty on
      `origin/main` (`ruff format --check` fails on a pristine clone), so future diffs stay readable
      (`scripts/autopilot/species/prompt_forge.py`) (found 2026-09-14, noninf sweep).
- [ ] **MHS-11 — replace the operator guide's `prompt_forge.py` line-number citations with symbol names**,
      since `line 575` / `line 594` / `line 509` are already stale by hundreds of lines
      (`docs/guides/meta-harness-operator-guide.md`) (found 2026-09-14, noninf sweep).
- [ ] **MHS-12 — eval-identity screen for code_mutation.** Refuse (MutationEffect.UNSAFE with
      reason) any mutation whose ADDED code reads workload_class, scoring_method, batch_id,
      request-metadata suite/tier keys or the literal "eval_batch", or removes/overrides force_role
      handling, in any allowlisted file. Grandfather existing references the way MHS-2 grandfathers
      imports. Fixtures: a chat.py mutation branching on workload_class == "eval_batch" is refused;
      a no-op chat.py mutation passes. Partly answers Open Question 2 (key on eval-identity fields,
      not only suite/task names). intake-1387#record.

*Declined 2026-09-14: repoint the dangling pointer at `handoffs/completed/meta-harness-optimization.md:3` —
not filed because it is already recorded as the **Housekeeping rider (E0, owned elsewhere)** in this file's
Notes and named inside the open **MHS-6** box.*

**Cost yardstick (DERIVED-FROM-CONFIG, never a measurement)**: *"one engineer update ≈ one full sweep
of your eval suite"* — a reusable rule of thumb for pricing ANY outcome-grounded editor loop. It kills
this class of proposal on this host before anyone builds a design doc. `intake-1323#record` (dive actionable D9; handoff half;
the wiki half is queued for the compilation sweep).

## Open Questions

1. Does the effect enum (MHS-1) need a per-mutation-site vocabulary, or is one closed host-wide enum
   sufficient for PromptForge's mutation sites as they exist today?
2. Does the anti-leakage pattern set (MHS-3) key on suite/task identifiers only, or also on fixture
   content hashes — and does the latter create its own maintenance surface?
3. Is the CONSTRAIN/REPLACE classification (MHS-4) derivable mechanically from the MHS-1 effect enum,
   or does it need a separate label?

## Notes

- All six rows are **zero compute**. Nothing here requires inference, a model load, or an eval run.
- Dependency order: **MHS-1 → MHS-2**; **MHS-5 → MHS-4**.
- Index: this stub needs a new row in `routing-and-optimization-index.md` at the next free ID
  **RTG-55** — verify against `handoffs/archived/routing-and-optimization-index-history-*` before
  assigning, since retired IDs are never reused. **Row is PREPARED here; the owning session APPLIES.**
- Housekeeping rider (E0, owned elsewhere): the dangling pointer at
  `handoffs/completed/meta-harness-optimization.md:3` should be repointed at this stub or the clause
  deleted.

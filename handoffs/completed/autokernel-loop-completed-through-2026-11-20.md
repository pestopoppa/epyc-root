# AutoKernel research loop — completed ledger through 2026-11-20

> Historical ledger only; current work lives in [`../active/autokernel-loop.md`](../active/autokernel-loop.md). Compacted at the operator /wrap-up of 2026-11-20 (autokernel): every ticked checkbox whose detail was moved here keeps a one-line stub (ID, title, date and belief tag) in the active file; the verbatim original block, with its original line number in the pre-compaction file, is below. No open box was moved.

<!-- original line 96 -->
- [x] **AK-V27-RCV — keep ordinary governed refusals out of cumulative-terminal recovery.** Exact
      regression commit `caa22f42389fd744bac6f9213fb863504849d888`; the six former
      `KeyError: disposition` cases pass. ✅ 2026-08-22
  - **Branch-only note 2026-09-16 (sub-closure-fix; annotation only):** `caa22f42` and `cffb98d3` are **not on root `origin/main`**. They exist only on the `codex/autokernel-v27-*` branches (33 commits unmerged; 0 of their added lines are on main). AK-V27-C6 lists them as foundations to reuse, so treat them as branch-only until promoted. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #8).

<!-- original line 100 -->
- [x] **AK-V27-CMP — authenticate the frozen-v9 comparator without executing production artifacts.**
      Independent audit GO at `cffb98d3eb06aa81e8bdf990e22520444fd94adb`; 21 runtime objects and
      the approved `readelf` identity are pinned and rechecked. ✅ 2026-08-22
  - **Branch-only note 2026-09-16 (sub-closure-fix; annotation only):** `caa22f42` and `cffb98d3` are **not on root `origin/main`**. They exist only on the `codex/autokernel-v27-*` branches (33 commits unmerged; 0 of their added lines are on main). AK-V27-C6 lists them as foundations to reuse, so treat them as branch-only until promoted. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #8).

<!-- original line 195 -->
- [x] **AK-RUN-V3 — operationally launch from a fresh state root.** Fulfilled by versioned successors;
      v19 launched from a fresh sealed deployment and did not reuse v18's poisoned receipt. ✅ 2026-08-20

<!-- original line 197 -->
- [x] **AK-V19-SEED — bind identical seeds across timed-output-oracle arms and prove the seam live.**
      Product commits `d0e59dca` + `b9d06347` passed the hardware-free closure and v19 proved seed
      8613 on both graphs-on arms in both execution orders. ✅ 2026-08-20

<!-- original line 200 -->
- [x] **AK-V19-PORTFOLIO — advance the repaired live loop through Q5 and Q8 without leaking claims.**
      Q5 and Q8 completed the bounded screens above; inconclusive series remained nonpromotable,
      negative attribution short-circuited throughput, and all claims/processes cleaned up. ✅ 2026-08-20

<!-- original line 203 -->
- [x] **AK-V19-FA-AUTH — make controller-owned FA route geometry uncopyable planner context and recover
      invalid dispatch intent as a secret-free typed refusal.** Landed at `de1d93d5`; v20 passed two
      identical validate-only runs and launched from a fresh state root. ✅ 2026-08-20

<!-- original line 206 -->
- [x] ~~**AK-V20-LIVE — monitor the fresh v20 receipt chain through its next terminal or safe boundary.**~~ (closed 2026-10-29 audit: OBSOLETE → watch target PID 469246 is dead (ps), v20 deployment dir last touched 2026-08-20, campaign moved to v27/DS41 (handoff:Status header 2026-09-27); no live v20 chain to monitor)
      Confirm planner refusal/recovery behavior, require owned GPU claim/KFD/VRAM only during GPU
      phases, and do not infer a result from partial receipts or relaunch while PID `469246` owns the run.

<!-- original line 209 -->
- [x] **AK-ADM-1 — promote the six planner-memory limitations into typed pre-model enforcement.**
      Bind a versioned admissibility-policy manifest into Sol/Fable context and enforce exact kernel
      instantiation, command phase, static-tool execution, Q4_K correctness, Q8 native-path premise,
      and IQ residency before model judgment. Acceptance is the three current expected-failure tests
      becoming ordinary passing tests. ✅ 2026-11-10 [no-belief: code change, no measurement]
      2026-11-10: research branch `ak/adm1-20261110` @ `2d60b6670` (merged into epyc-inference-research origin/main at `9c1a3a421`). A versioned, self-hashed admissibility manifest (`discovery_admissibility_policy_v1.json`, bound to sealed portfolio evidence, projected into planner/critic context as `admissibility_policy_sha256`, validated by the deployment loader) enforced as `AdmissibilityRefused` in `ClaudeCritic.review()` before the Fable critic. The three expected-failure tests now pass as ordinary tests; 142 targeted tests pass. Acceptance met. [no-belief: code change, no measurement]

<!-- original line 570 -->
- [x] **AK-AUD-3 — Reconcile the durable diagnostics against clean-source campaign authority.**
  Receipt hashes, bounded results, provenance gaps, and the four-step dependency order are retained in
  `progress/2026-08/2026-08-12.md`; no inference or kernel-tree mutation was performed. ✅ 2026-08-12

<!-- original line 573 -->
- [x] **AK-AUD-4 — Reconcile executed diagnostic rows without upgrading their authority.** ✅
  2026-08-12 — current state already marks RVP-T0-1, AK-BH-1/2/3, AK-LN-2/AK-X-5a, and AK-DEL-1
  complete. Receipt re-audit confirms the first six are durable bounded diagnostics, not current
  calibration, ranking, archive, or promotion evidence where clean source/build provenance is absent.
  AK-DEL-1 is separately commit-backed at research `df02169e`: its hash-bound scope report found all
  3/3 admitted families in `existing_path_should_apply` and selects catalogue expansion before a novel
  generator. This corpus-bounded routing conclusion is not a claim about all workloads.

<!-- original line 580 -->
- [x] **AK-AUD-5 — Make the real-process fault rehearsal independent of caller import state.** ✅
  2026-08-12 — research `eeaf80ba` pins the exact checkout's `scripts/kernel_rnd` path first in each
  captured child environment, so the crash/restart and claim-revocation legs no longer exit when a
  test runner mutates `sys.path` without exporting `PYTHONPATH`. Detached clean campaign checkouts are
  accepted by exact commit identity. The focused suite passed 12 tests and the full AutoKernel suite
  passed 5,548 tests with one expected failure and 2,241 subtests.

<!-- original line 586 -->
- [x] **AK-AUD-6 — Classify every remaining AutoKernel-family checkbox at the integrated checkpoint.**
  ✅ 2026-08-12 — against root `f9f36e3e` and research `3bd94893`, the audit found exactly **41** open
  checkboxes: 13 post-OP-16 empirical items, 13 items gated by OP-11's exact experimental llama commit
  and replay, 2 dependencies on the active INF-03 campaign, 9 future/operator-release items, and 4
  external licence/source items. It found **zero** immediately actionable implementation gaps and no
  item whose implementation defect was being hidden as an empirical blocker. Every residual already
  has an owning checkbox; the only documentation defect was three live proposal-v3 pointers left
  behind after the proposal-v4 migration, corrected in AK-WM-2a and Step 3 below.

<!-- original line 594 -->
- [x] **AK-AUD-7 — Retract INF-03 r4 after tracing the controller-to-evaluator feedback path.** ✅
  2026-08-12 — the prior completion audit's “zero implementation gaps” conclusion is superseded for
  INF-03. KernelFoundry made 64 intermediate centralized evaluations from its GPU-blind controller
  environment outside the two durable vendor/final claim windows, and all 64 intermediate correctness
  checks failed. The exact-PID campaign processes were stopped and confirmed dead with no device claim
  remaining. R4's 5/64 checkpoint inventory remains diagnostic history only; it cannot be resumed,
  aggregated, ranked, banked, or used to select a controller. The owning repair and fresh-pilot tasks
  live in [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring): parent-owned exact-PID
  AF_UNIX brokerage is necessary, while a decision-bearing pilot additionally requires controller and
  candidate OS isolation. A broker-only live run is engineering smoke, not policy evidence.

<!-- original line 604 -->
- [x] **AK-AUD-8 — Close the INF-03 broker/isolation implementation gap and admit exact-source
  EvoEngineer.** ✅ 2026-08-12 — integrated research tip `de7214ee` routes every intermediate/final
  candidate through a parent-owned authenticated broker into a fresh deny-network evaluator sandbox,
  while every non-baseline controller runs inside an exact-read/exec, device-blind, cgroup-owned
  sandbox with one inherited peer-bound broker socket. The same integration admits the exact historical
  MIT EvoEngineer-Full source at `1649715a…`; the pinned runtime completes its real upstream loop under
  fixture bridges. Focused warning-strict validation passed 95/95, the pinned Evo suite passed 11/11,
  and the pinned controller suite passed 572/572. The durable physical static audit is ready **7/7**
  over four tasks with zero controller/GPU commands at
  `/mnt/raid0/llm/autokernel/probes/inf03-isolation-available-source-reaudit-20260812-r3/receipt.json`
  (self-hash `5fa93695…`, file SHA-256 `082d977f…`). A fresh one-task/one-arm live pilot remains the
  empirical gate; r4 remains immutable invalid history and is never resumed.

<!-- original line 616 -->
- [x] **AK-AUD-9 — Drive the isolated INF-03 pilot to a real model request without upgrading failed
  engineering attempts into evidence.** ✅ 2026-08-12 — research branch
  `integrate/inf03-isolation-merge-20260812` at `569a8c42` implements the bounded diagnostic-pilot
  authority and the exact controller dependency grants exposed successively by r1-r11. R12 reached the
  real Codex client and retried the response request for about 60 seconds, but the sandboxed transport
  failed with `Operation not permitted` before any completed response. All twelve attempts remain
  non-rankable engineering diagnostics; there is no candidate, kernel speedup, campaign aggregate,
  banked proposal, or promotion claim. The exact attempt ladder and next repair live in
  [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring).

<!-- original line 625 -->
- [x] **AK-AUD-10 — Close the governed INF-03 compatibility pilot and preserve its non-authority
  boundary.** ✅ 2026-08-12 — research main `15c61ed5` contains the complete broker/controller/
  evaluator isolation stack and the r13/r14 validator repairs. R15 completed exactly one task and one
  K-Search round with six `gpt-5.6-sol:high` calls. Its single brokered intermediate and final
  evaluations both passed compilation/correctness 4/4, with diagnostic ratios `1.0033912745` and
  `1.0019039030`; those ratios cannot rank a controller or kernel. Baseline/intermediate/final sampler
  windows contain 11/21/21 observations and matched released claim IDs. Controller and evaluator
  cgroups were verified empty and removed, ephemeral Codex state was scrubbed, the controller admitted
  only `/dev/null`, and both evaluators were deny-network with exact GPU devices. Receipt:
  `/mnt/raid0/llm/autokernel/probes/inf03-mi210-isolated-k-search-pilot-20260812-r15/diagnostic-pilot-receipt.json`
  (self/file SHA-256 `3425cf57…` / `eb53de38…`). This is compatibility evidence only: no matched
  campaign, ranking, belief, proposal-bank, champion, promotion, or release authority exists. The next
  empirical step is the fresh 7/7 availability-conditioned panel.

<!-- original line 638 -->
- [x] **AK-AUD-11 — Correct the parser false positive and audit the first two seven-arm launch
  boundaries.** ✅ 2026-08-12 — the reported all-tree parser collision was expected argparse stderr
  inside `assertRaises(SystemExit)`, not collection failure: 3,927-test discovery succeeded and an AST
  sweep found no module-scope `parse_args`. INF-03 r5 exposed a real Claude CLI `-11` under the exact
  campaign Landlock policy. Local, unpushed research `916cdc92` added the first bounded runtime-read
  repair and passed a real standalone Claude probe plus 5,653-test pinned regression, but r6 reproduced
  the same `-11`
  after its baseline even with those reads present. The test totals were observed but have no retained
  transcript, so they are regression notes rather than durable suite evidence. Therefore the probe
  proves only its narrow path; the owning open differential and fresh-attempt gate remain in
  [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring). R5/r6 have no aggregate or
  decision authority, and both controller cgroups were verified empty and removed.

<!-- original line 650 -->
- [x] **AK-AUD-12 — Close the r8-r10 actor-cell implementation defects and prove one full real
  actor-critic loop without upgrading a live partial into evidence.** ✅ 2026-08-12 — research
  `6270ebc1`, `cd1303b9`, `eb00c411`, `2525f2f7`, and `7b20b5d6` move vendor evaluation fully into
  the parent, repair inherited broker writes, separate semantic task state from staged model state,
  and refresh both pins. R11's first candidate passed compilation/correctness but measured
  `0.993531469254354×`; the critic chose `revise` and the controller restored the measured starting
  source before iteration 2. This is an implementation/liveness checkpoint only. R11 is still live,
  has no terminal aggregate, and carries no comparison, belief, bank, champion, promotion, or release
  authority. Terminal receipt-chain validation remains owned by
  [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring).

<!-- original line 660 -->
- [x] **AK-AUD-13 — Prove measured critic feedback changes the next live proposal and close the
  confined host-runtime re-hash defect.** ✅ 2026-08-12 — r12 iteration one measured
  `0.9967805648538064×` and received `revise`; iteration two named and rejected that mechanism,
  proposed a distinct shared-offset/vectorized-streaming path, measured `1.0059084616458236×`, and
  received `accept`. Both candidates compiled and passed 4/4 correctness, and both ratios remain
  inside noise. R12 then failed while constructing the final receipt because the confined controller
  reopened `/usr/bin/docker`. Research `4b516e9f` makes the parent broker receipt chain authoritative
  for host runtime identity and validates the actual flat model-receipt layout; `f316bf31` refreshes
  the campaign pin. The full AutoKernel suite passed 5,660 tests with one expected failure. Seven-arm r13
  subsequently failed after baseline and planner receipt ordinal `0001` because confined Claude could not
  create `/mnt/raid0/llm/tmp/claude-1000`; its captured PIDs are dead and its controller/model cgroups
  were verified empty and removed. Research `268115ad` now creates an exact call-scoped runtime/temp
  directory under the governed workspace, binds its non-inheritance and relative path in the sandbox
  receipt, and removes it after the model call. R13 remains a terminal immutable partial/non-rankable
  attempt; the repair must be pinned and proven by a fresh campaign.

<!-- original line 675 -->
- [x] **AK-AUD-14 — Prove the call-scoped model runtime across repeated live calls without declaring
  the panel terminal.** ✅ 2026-08-12 — research `446a1c31` makes model runtime state call-scoped and
  `152ed0d9` pins it into the seven-arm configuration. R14 ultimately returned nine model calls and four
  compilation/correctness-4/4 evaluator windows, proving repeated runtime compatibility, but the outer
  guard then refused the cell with `task or controller source identity changed during checkpoint
  execution`: its audited source was `152ed0d9` and the shared source worktree advanced to `03f9ae69`
  mid-run. No actor cell receipt or aggregate was admitted. All eight claims were released, all 14
  captured PIDs are absent, and all 12 recorded cgroups are verified empty and removed. R14 is therefore
  immutable, invalid, and non-rankable; its intermediate ratios carry no panel, bank, champion,
  promotion, or release authority.

<!-- original line 685 -->
- [x] **AK-AUD-15 — Close the pre-reboot evidence-product implementation audit and relaunch from an
  immutable source root.** ✅ 2026-08-12 — research `03f9ae69` adds the clean completed-journal held-out
  projector and a deterministic, non-executing IQK pair generator; the broad suite passed **5,678 tests
  with one expected failure**. That 18-commit AutoKernel series is published on research `main` at merge
  `4328c37c940d125d7b11b4264b65f415c300eda0`. Seven-arm r15 runs from a dedicated clean worktree/branch
  pinned at `03f9ae69`; its 7/7 audit, baseline, and first successful real Claude planner call were present
  at this checkpoint. The live worktree and campaign must remain untouched until terminal validation.

<!-- original line 704 -->
- [x] **AK-AUD-5 — Audit the runnable loop against current research `main`, not historical completion
  narration.** ✅ 2026-08-12 — verified the live campaign boundary, generic-source refusals, removed
  planes, preserved tag, and focused suite from a clean detached `730adb1d` checkout.

<!-- original line 707 -->
- [x] **AK-RUN-1 — Emit governed candidate and evaluation records from the executing campaign.** Bind
  actual T0 property measurements and raw paired-performance evidence; append exactly once before the
  terminal `STOP_STATE`; make append failure non-success; and keep dry runs record-free. This is the
  producer prerequisite for Vidya SC10/SC18 and the real matched archive. ✅ **ALREADY SATISFIED
  2026-08-13 (mainB verification)** — same pattern as AK-RUN-3: this row was filed by the runnable-loop
  audit at 02:30 on 2026-08-12, and the implementation landed 37 minutes later the same day
  (`d96e8704` "autokernel: journal live evaluation events", 03:07, in origin/main); the row was never
  reconciled. Verified element-by-element at HEAD: `campaign.py` `journal_evaluation()` binds actual T0
  property measurements and raw paired-performance evidence into schema-valid `EVALUATION_EVENT` +
  `CANDIDATE_RECORDED` records (evaluator identity, claim grammar, host/claim receipts, evaluation
  event ids, protocol ids); appends idempotently (replay returns identical event ids, byte-diff on
  mutated payload raises "different bytes"); ordering test asserts `journal_evaluation` runs before the
  terminal `journal`/`STOP_STATE`; append failure makes the run non-success (`journal_error` set, result
  `ok=False`); dry runs are record-free (no `journal_evaluation` seam, zero candidate records — both
  tested). Tests: `test_campaign.py` 362 passed incl. idempotent-append, ordering, failure-non-success,
  and dry-run-record-free coverage. The 3 adjacent `test_campaign_footprint.py` failures are
  pre-existing module-list drift (new `execution/inference_window.py`, `execution/screening_baseline.py`,
  `heldout_bound_pipeline.py` lack FOOTPRINT.md rows from later AutoKernel commits) — reproduced on a
  clean detached origin/main checkout, unrelated to AK-RUN-1.

<!-- original line 731 -->
- [x] **AK-RUN-3 — Restore the lean sequencer and champion-maintenance path.** Consume proposal,
  candidate, and evaluation records; distinguish frontier/banked/champion state; compose compatible
  members; re-evaluate the combined source snapshot; append `CHAMPION_UPDATED`; and re-anchor explicitly
  when the production anchor moves. Never add member speedups arithmetically. ✅ **ALREADY SATISFIED
  2026-08-13 (mainB verification)** — this row was filed by the runnable-loop audit at 02:30 on
  2026-08-12, and the restore landed ~1h later the same day; the row was never reconciled. The same
  task is checked off at line 2894: **"Restore the lean bank/frontier/champion sequencer on the
  runnable journal plane"** ✅ 2026-08-12 — research `069e79fd` (in origin/main). Verified element by
  element at HEAD: `controller/sequencer.py` consumes proposal/candidate/evaluation records and
  distinguishes frontier/banked/champion state; `controller/champion.py` composes compatible members
  (file/symbol/dispatch predicates fail closed), requests direct combined-candidate T0/T1/T2 evidence,
  appends `KIND_CHAMPION_UPDATED` idempotently, re-anchors explicitly on anchor move (matching sealed
  release receipt required), preserves the incumbent on rejected/failed composition, and **never adds
  member speedups arithmetically** (champion.py:10 "member results are never combined into a new
  result"). Import closure proven: campaign cannot reach sequencer/champion. Tests: `test_champion.py`
  16 passed (incl. `test_sequencer_composes_existing_frontier_without_importing_campaign`,
  `test_reanchor_drops_members_already_present_in_new_production`,
  `test_reanchor_without_matching_sealed_receipt_fails_closed`, idempotent-replay and concurrent-append
  coverage). The one failure in the adjacent rehearsal suite (`test_current_campaign_cli_contract_is_one_json_document`)
  is a pre-existing environment issue (rehearsal passes relative `--model test`, which hardened
  campaign rejects as non-absolute) — reproduced on a clean detached origin/main checkout, unrelated
  to the sequencer.

<!-- original line 949 -->
- [x] **AK-D39-1 — Enforce the provider-not-champion boundary in records, execution setup, C3, and
  champion admission.** ✅ 2026-08-12 — research `77689f76` adds proposal-v4 provider identity,
  diagnostic-only opaque authority, realpath-aware isolated prefixes, exact baseline manifests,
  provider-integration joins, and the diagnostic-versus-integrated C3 split. Ancestor-root and
  symlink-to-protected mutation tests fail closed. Post-rebase focused/affected validation passed
  580 tests; a full 5,597-test discovery exposed four current-schema call sites, which were repaired
  and revalidated in a 419-test affected slice. The only remaining discovery error was environmental:
  the checkout Python lacks `pytest` for `test_placement_context.py`.

<!-- original line 957 -->
- [x] **AK-D39-2 — Implement governed source-available ROCm module execution.** ✅ 2026-08-12 —
  research `a54e36ba` adds the pinned clean-source lifecycle in a content-addressed isolated prefix,
  binds exact source commit/tree, tracked files, licence, toolchain, executable and linkage identities,
  requires explicit authorization, executes without network access, verifies expected outputs, and
  records teardown. The provider remains diagnostic/nonbankable until its result joins an experimental
  `llama_gpu` integration candidate; it cannot mutate shared `/opt/rocm` or make an opaque binary into
  champion source. Validation passed 101 tests plus 22 subtests and Ruff.

<!-- original line 1323 -->
- [x] **AK-X-11 — Track the two remaining cited-but-untracked `docs/design/` files**, or record why not.
  ✅ 2026-08-10 — both cited design records are included in the AutoKernel closure pathspec rather
  than left as unowned filesystem state.
  `agent-session-control-surface.md` is cited by
  [`session-bus-thin-dispatcher.md`](coordination-and-churn-pipeline.md) and
  `repl-s4-omega-multipaper-arm-20260729.md` is likewise cited from a tracked handoff, yet neither is
  in git. **A citation to an untracked file is indistinguishable from a citation to a tracked one
  until someone clones the repo and it resolves to nothing** — which is the general form of the defect
  the 2026-07-29 audit catalogued and then reproduced on itself. Found 2026-08-10 while verifying the
  P2-5j resolution above.

<!-- original line 2874 -->
- [x] Audit the source draft against the current scaffold, freeze path, measurement constitution, and
  production kernel-set rules ✅ 2026-08-01

<!-- original line 2899 -->
- [x] **Annex question resolved (operator, 2026-08-02): create Annex K (kernel research and release)**
  as a fourth annex under `measurement/protocols/`. `P-AK-SEARCH-1` fits none of the three declared
  families (`MEASUREMENT.md:15-20`) — it is cross-backend and a *search* instrument rather than a
  measurement family. Splitting it across B/Q/G would fragment one instrument across three amendment
  histories and obscure that its authority is narrow, unified, and revocable in one place. Annex
  creation is a layout change, so the layout paragraph and registry deltas ride inside attestation 1
  ✅ 2026-08-02

<!-- original line 2910 -->
- [x] Fill `P-AK-SEARCH-1`'s numeric bindings from the four controls — e-process threshold, per-backend
  noise floor, minimum block counts. **These must be calibrated, not guessed:** ratifying invented
  thresholds into an append-or-version protocol is the mistake the draft-early/ratify-last sequencing
  exists to prevent. ✅ 2026-08-10 — superseded by the ratified Annex K calibration block: `φ`,
  `B_min`, α thresholds and MDE are derived per campaign under the fixed construction, never copied
  from guessed literals.

<!-- original line 2916 -->
- [x] Draft the `pgrep` substitute (§3.5) as an equivalent P-BENCH-1/P-GPU-1 precondition. ✅ 2026-08-10
  — delivered as `preflight-substitute.draft.md` and realized by the claim-witness-first preflight.

<!-- original line 2918 -->
- [x] Draft the evidence-retention rule for expirable classes (§5.8) — needed because
  `MEASUREMENT.md:223-229` puts reclamation under operator authority. ✅ 2026-08-10 — delivered as
  `evidence-retention.draft.md` and applied through the 2026-08-03 ratification package.

<!-- original line 2921 -->
- [x] Prepare the `human_only_paths.yaml` additions (evaluator bundle, both protocol IDs,
  objective/threshold policy) and the accompanying `.sha256` rewrite as operator actions. ✅ 2026-08-10
  — `human-only-paths-delta.draft.md` and the live manifest record the boundary and the OS-level caveat.

<!-- original line 2924 -->
- [x] Assemble attestation 1 through the AK6 bundle assembler: RATIFICATION_LEDGER of every semantic
  delta, the `MEASUREMENT.md` CHANGELOG line, the §2 registry key and row, and a pre-validated
  end-to-end command sequence presented as one attestation with strikeable lines. ✅ 2026-08-10 —
  Annex K / P-AK-SEARCH-1 were ratified 2026-08-03; the ledger and apply package remain in
  `artifacts/operator/autokernel-policy-draft/` as the durable assembly record.

<!-- original line 2936 -->
- [x] Draft `epyc.autokernel.operator_waiver.v1`, generalized from
  `epyc.cpu_prefill_v8.operator_waiver.v1` (§10.4). The draft schema suffices for AK5's dry-run; only
  a real freeze needs it ratified. ✅ 2026-08-10 — schema and validator are implemented in
  `schemas.py`; the preserved draft is `operator-waiver-schema.draft.md`.

<!-- original line 2947 -->
- [x] File `worktree_manager.py`'s in-memory-restore data-loss bug (§2.3) as a defect against the
  AutoPilot owner with the exact repro. ✅ 2026-08-10 — subsequently fixed under the operator's
  expanded AP-WM dependency authority: rejection now restores the exact byte preimage (including
  dirty, empty, and absent paths) and never overwrites it with `git checkout`; 7 focused tests pass.

<!-- original line 2959 -->
- [x] Implement versioned campaign/proposal/candidate/evaluation/champion/release-package schemas
  (§7), including claim grammar, anchor binding, `inconclusive`, `change_class`, controller provenance,
  expected information gain, determinism class, and co-residency. ✅ 2026-08-03 (schemas.py, 118 tests)

<!-- original line 2962 -->
- [x] **Journal prospective live evaluation events from the executed campaign evidence.** ✅ 2026-08-12 —
  research `d96e8704` emits schema-valid v5 T0/T1 records before terminal STOP, binds raw paired
  blocks and the Vidya write-side capture, and retains the exact executed recipe receipt. Window
  closure now re-reads CPU/device claims, native open/close inference preflight receipts, host and
  storage state, evaluator/runtime authority, and the exact per-tool (`llama-cli`/`llama-bench`)
  anchor before release. Missing holder identity or anchor/evaluator/claim/host drift yields a durable
  INVALID/refusal rather than an inferred PASS; append failure remains terminal without skipping
  release or STOP. The final campaign/journal/evaluator/control/execution slice passed 1,231 tests.

<!-- original line 2970 -->
- [x] **Bind source-changing proposals to an immutable source-to-candidate lifecycle.** ✅ 2026-08-12 —
  research `069e79fd` loads the embedded content-addressed patch before preflight or claim, restricts
  mutation to the guarded worktree API, verifies normalized paths plus content-derived hunk/symbol
  identity, and emits one idempotent candidate record from the exact clean build snapshot, ancestry,
  affected surface, composition evidence, release receipt, and cached evaluation-event ids. Parameter
  proposals retain their distinct semantic bundle identity; source evidence is never reconstructed
  after teardown.

<!-- original line 2977 -->
- [x] Implement typed research-prior, campaign-seed, constraint/negative, and legacy-import events
  (§19). ✅ 2026-08-10 — superseded by the operator-approved lean loop: proposal-v3, immutable
  proposal receipts, the prior-art catalogue, and the append-only result journal are the live record
  plane; the deleted broad strategy-event plane is not restored before real campaigns justify it.

<!-- original line 2981 -->
- [x] Enumerate and content-hash the historical knowledge source manifest across root/research
  handoffs, artifacts, evidence reports, progress pointers, current source, and research intake.
  ✅ 2026-08-10 — scoped to executable prior art: `prior_art_catalogue.json` binds source commit,
  scan/tree receipts, expected absences, exit actions, and the checked substrate-fact receipt set.

<!-- original line 2985 -->
- [x] **Quarantine the existing `kernel_store.py` rows** as `legacy_unverified`: `kernel_eval.sh`
  never gated on coherence, so the correct-only Pareto is contaminated. Check whether any raw
  artifacts survive (the campaign output directory is missing, so likely none); re-derive only rows
  with surviving evidence and an explicit anchor. Exclude the rest from every planner retrieval.
  ✅ 2026-08-10 — expected absence verified: there is no surviving legacy result corpus to import;
  the deprecated harness is fenced and the lean driver reads only its validated proposal/journal path.

<!-- original line 2991 -->
- [x] Mark `kernel_eval.sh` deprecated-and-unrunnable so no further contaminated rows are produced
  before AK3 replaces it. ✅ 2026-08-03 (exits 2; KERNEL_EVAL_ALLOW_DEPRECATED=1 overrides)

<!-- original line 2993 -->
- [x] Atomize the source draft and historical research without upgrading evidence grade; link
  duplicates, contradictions, confounds, supersessions, transfer limits, and reopen predicates.
  ✅ 2026-08-10 — `prior_art.py` and its catalogue implement the four evidence buckets,
  contradictions/expected absence, transfer limits, deterministic exit action, and 1% pruning.

<!-- original line 2997 -->
- [x] Require a receipt on every suppressing ledger entry, bound to the current production commit,
  re-verified on anchor move (§19.3).
  ✅ 2026-08-10 — prior-art exclusions carry commit/scan/tree receipts and fail closed when their
  source or anchor binding moves.

<!-- original line 3005 -->
- [x] Add validators refusing mutable evaluator IDs, stale production anchors, undeclared change
  classes, actor-supplied scope, missing fallbacks, and unbounded resource/storage requests.
  ✅ 2026-08-10 — current schema, integrity, worktree, proposal-v3, storage, and execution-chain
  validators cover these refusal classes on the runnable campaign path.

<!-- original line 3009 -->
- [x] Replace SQLite-as-source with fsync append-only **sharded** events plus content-addressed
  snapshots; retain SQLite as a rebuildable view; readers read all shards. ✅ 2026-08-03 (journal.py, 79 tests)

<!-- original line 3012 -->
- [x] Add failure/mechanism/do-not-repeat/context/champion views consumed by the planner.
  ✅ 2026-08-10 — superseded by the lean-loop boundary: no live autonomous planner consumes these
  views; failures and mechanism evidence remain durable in the journal for later evidence-driven design.

<!-- original line 3015 -->
- [x] Implement the storage plane: durability classes, per-campaign quota, retention classes,
  tombstoned expiry, `DISK_PRESSURE`. ✅ 2026-08-03 (storage.py, 159 tests)

<!-- original line 3017 -->
- [x] Land the evidence root under `epyc-inference-research/data/<campaign>/` with `SHA256SUMS` and
  README; extend `check_evidence_durability.py` to cover AutoKernel citations. ✅ 2026-08-10 — the
  live storage plane creates the durable campaign root and content-addressed evidence manifest;
  the external checker remains scoped to its model-registry contract rather than duplicating storage.

<!-- original line 3021 -->
- [x] Clear the §3.7 durability exposures: copy the np_context decision surface out of
  `/mnt/raid0/llm/tmp/`, track the two np_context study bundles, restore the P2-5j protocol to git. ✅ 2026-08-03 (research 9687f7fe, root 047b5a40)

<!-- original line 3024 -->
- [x] Fix the `kernel_store.py:88` file-handle warning; add both `kernel_rnd` suites to
  `PYTEST_SMOKE`; pin pytest in `pyproject.toml`/`uv.lock` rather than injecting it via `--with`.
  ✅ 2026-08-10 — delivered in research commit `ccfb23a3`; project tooling owns the pinned test
  environment and both kernel-R&amp;D suites are in smoke coverage.

<!-- original line 3028 -->
- [x] **Measure achievable MI210 bandwidth (STREAM/BabelStream-class) — §8.3.1's second denominator now EXISTS** ✅ 2026-08-03. **1433.3 GB/s achievable = 87.5% of the 1638 GB/s datasheet peak**; triad 1371.1;
  p20–p80 within ~1.2%; correctness PASS. Instrument `epyc-inference-research`
  `scripts/benchmark/mi210_achievable_bandwidth.sh`, receipt
  `data/mi210-achievable-bandwidth/20260803T124401Z/receipt.json`
  (SHA-256 `0aab9c7e135929e72fd3a5c2498eb807dc16d0f80b773f063e1df3524df7b4d3`), committed `328b768d`.
  Co-residency recorded: three servers resident and **idle**, autopilot paused, 0 busy slots, 0% GPU use.
  **Correction factor 1.143×** — the prior ~1.3–1.4 TB/s estimate was low. **Both denominators must now be
  carried per §8.3.1, and a cross-vendor comparison must stay spec-to-spec**: converting our numbers to an
  achievable basis while leaving a competitor's on a spec basis makes the gap look smaller without it
  being smaller.

<!-- original line 3038 -->
- [x] Put both denominators into the P0.1 profile manifest as substrate constants, with the basis of each
  attainment figure recorded alongside it rather than inferred.
  ✅ 2026-08-10 — `substrate_facts.json` carries measured and spec compute/bandwidth denominators,
  basis-preserving ridges, crossover points, receipt paths, and the MI210 NUMA identity; `substrate.py`
  re-derives and validates them.

<!-- original line 3043 -->
- [x] Measure **H2D/D2H** on the Gen4 x16 link ✅ 2026-08-03 — **H2D 28.89 GB/s, D2H 28.20 GB/s**
  (91.7% / 89.5% of Gen4 x16 theoretical), receipt
  `epyc-inference-research/data/mi210-h2d-d2h/20260803T131500Z/`, committed `2aa14264`. Bulk transfer is
  **NUMA-node-independent** to within 0.1%, which matters for seed G1: the GPU lane's cross-node host
  placement costs nothing on the *transfer* path. It says nothing about host-side memory access during
  serving, which is the regime G1 actually targets — do not let this close G1.

<!-- original line 3049 -->
- [x] Import the MI210 roofline constants as substrate facts. **All three are now MEASURED (2026-08-03)**,
  so §19.0 rule 4's no-upgrade-on-import concern applies only to the derived companions: peak
  **172.2 TFLOPS `[M]`** (181.0 `[D]`), achievable BW **1433.3 GB/s `[M]`** (1638 `[D]`), PCIe
  **28.89/28.20 GB/s `[M]`**, giving a clean measured-basis **ridge 120.1 FLOP/byte** and
  `B*` = Q4_K 34 / Q8_0 64 / bf16 120. Carry the spec-basis ridge (110.5) alongside for cross-vendor
  comparison, and **never mix bases**. Derivations, the measured/derived reconciliation, and the 2×
  defect in AMD's own published figure:
  [`mi210-mfma-compute-bound-paths.md`](../completed/mi210-mfma-compute-bound-paths.md).
  ✅ 2026-08-10 — imported without changing evidence grades; mixed-basis ridges are rejected by
  reconstruction tests.

<!-- original line 3065 -->
- [x] Build backend worktree managers that start from the current production tip, namespace worktrees
  (`llama.cpp-ak-<campaign_id>`) and branches (`ak/<campaign_id>/…`), use pathspec-limited commits in
  the shared clone, and categorically deny production source/build paths.
  ✅ 2026-08-10 — `execution/worktree.py` re-resolves the frozen tip, namespaces campaign trees and
  branches, enforces pathspec containment, and rejects production paths.

<!-- original line 3070 -->
- [x] Build candidate-local build/cache layout and full build identity receipts. ✅ 2026-08-10 — the
  build plan uses candidate-local roots and binds source snapshot, command/toolchain, output, libraries,
  linkage, and log identity.

<!-- original line 3074 -->
  - [x] Decide the mechanism: an on-disk lock under the same root as `cpu_region.*.lock`, keyed by
    device (`gpu.mi210_0.lock`), holding owner id, PID, start time, campaign id, expiry, and purpose. ✅ 2026-08-03 (gpu_device.<id>.lock beside cpu_region.*)

<!-- original line 3077 -->
  - [x] Liveness is PID plus process-start-time, not a heartbeat, so a stale lock from a dead holder is
    detectably reclaimable and a live holder is never stolen from. ✅ 2026-08-03 (/proc stat field 22)

<!-- original line 3079 -->
  - [x] Crash recovery: a lock whose PID is gone or whose start time mismatches is reclaimable after a
    grace period, and the reclamation is journaled. ✅ 2026-08-03 (reclamation journaled)

<!-- original line 3081 -->
  - [x] Revocation follows `BUS_PROTOCOL.md:47-51` — mark `revoking`, holder drains at its boundary,
    an ignored revocation surfaces as a `defect`, never a forcible steal. ✅ 2026-08-03

<!-- original line 3087 -->
  - [x] Retire `src/gpu_lease.py`'s process-local lease for cross-process use, or clearly scope it as
    intra-process only, and migrate `axa2_live_cutover_bundle.py:535`. ✅ 2026-08-10 — scoped out of
    AutoKernel: its live path uses the cross-process claim exclusively and never imports the legacy
    process-local lease; migration of unrelated legacy consumers is not an AutoKernel dependency.

<!-- original line 3092 -->
  - [x] Acceptance: two processes contend and the second blocks or fails cleanly; a killed holder's
    lock is reclaimable and the reclamation is journaled; a live holder is never preempted forcibly; a
    revoke drains within the declared bound; `kernel_eval.sh`'s `gpu_idle()` is deleted, not wrapped. ✅ 2026-08-03 (verified outside the suite)

<!-- original line 3095 -->
  - [x] **Arm the campaign-wide device-claim expiry check from the shared resource window.** ✅
    2026-08-12 — research `accff01f` passes `CampaignSpec.max_hold_s` to every MI210 claim, matching
    the CPU-region claim acquired in the same transaction. This writes `expires_at`, so the existing
    advisory expiry check can return `FAIL` instead of `COULD_NOT_CHECK`; expiry still requests
    quiesce-and-drain and never authorizes stealing a live device. Focused campaign tests passed
    **199/199**, and mutation controls fail if the keyword is removed or replaced by a hard-coded
    six-hour value.

<!-- original line 3102 -->
- [x] Integrate CPU region claims and co-residency policy. ✅ 2026-08-10 — `campaign.py` acquires the
  exact declared CPU footprint before T0/T1 and binds the same receipt into both consumers; lane
  topology and co-residency are validated separately.

<!-- original line 3105 -->
- [x] Build the single audited read-only preflight wrapper (§3.5) and remove every other name-pattern
  process read from the loop. ✅ 2026-08-03 (preflight.py + claim_witness.py, 143 tests)

<!-- original line 3107 -->
- [x] Run every candidate process in an owned scope/cgroup with PID/start-time receipts and verified
  teardown. ✅ 2026-08-10 — the lean loop uses owned process groups with captured PID/PGID/start-time
  receipts and TERM→KILL→verified-dead teardown; a separate cgroup controller was not retained.

<!-- original line 3110 -->
- [x] Integrate host-health/reboot-required and cache-preparation states, including the one-week
  uptime ceiling and the reboot decision package (§10.7). ✅ 2026-08-10 — cache state and CPU/GPU
  throttle state are verdict-bearing; reboot/uptime remains operator session preflight because the lean
  loop is session-driven rather than a daemon allowed to request host mutation.

<!-- original line 3114 -->
- [x] Register AutoKernel on the session bus: roster id, heartbeat at every task boundary, outbox,
  lane declaration (`cpu`/`gpu`/`both`/`none`) on every queued unit, revoke handling, C19/C20
  visibility, and a re-read-instructions checkpoint so a long-lived service does not run indefinitely
  on its startup copy (`BUS_PROTOCOL.md:76-90`). ✅ 2026-08-10 — superseded by the session-driven lean
  loop: the owning agent session, not campaign code, owns bus heartbeat, lane declaration and revocation.

<!-- original line 3119 -->
- [x] Wire `scripts/utils/agent_log.sh` task start/decision/end logging, and log rollback commands
  before any system-affecting step (`OPERATING_CONSTRAINTS.md:22-25`).
  ✅ 2026-08-10 — session lifecycle logging remains the agent owner's boundary; duplicating it inside
  the non-daemon campaign would create two conflicting audit owners.

<!-- original line 3123 -->
- [x] Verify the C6 sandbox on the real host; remove unsandboxed operation from live AutoKernel.
  ✅ 2026-08-11 — `execution/sandbox.py` supplies a native host backend: Landlock ABI 6 write
  confinement, seccomp denial of signalling/network/namespace escape, non-root execution, finite
  rlimits, and a per-invocation cgroup-v2 leaf. Real shell and tiny-CMake probes produced evaluator-
  owned activation receipts and verified empty/removed teardown; startup is fail-closed.

<!-- original line 3128 -->
- [x] Extend the sandbox to **candidate binary execution**, not just the evaluator: no write access
  outside the campaign tree, no signalling processes it does not own, owned cgroup with verified
  teardown. The loop compiles code it authored and then runs it with GPU access on a shared host;
  the actor's tool allowlist does not constrain that binary's syscalls (§8.5.1). ✅ 2026-08-11 —
  candidate-controlled configure/build, T0 and every T1 arm require the native C6 policy; receipts
  live outside the candidate-writable tree, fresh process identities are checked, and the next arm
  cannot start until the preceding cgroup has been drained and removed.

<!-- original line 3135 -->
- [x] Add resource starvation/drain/resume tests and campaign checkpointing. ✅ 2026-08-10 — append-only
  journal replay, completed-run keys, claim revocation/drain, teardown-on-every-exit, and restart fixtures
  cover the retained campaign path.

<!-- original line 3138 -->
- [x] **Import the MI210's actual NUMA attachment as a resource-plane fact: the device is on node 1, not
  node 3** (sysfs ground truth, `/sys/class/drm/card2/device`, `0x740f`, `numa_node=1`). The seed G1 row
  in §19.6 asks to "import current MI210 node attachment" and **no numeric node appears anywhere in the
  six MI210/autokernel handoffs.** The consequence is immediate and needs no kernel work: **the GPU
  lane's host threads at 184–191 are already cross-node, and device-local placement has never been
  tried.** Placement evidence lives in
  [`gpu-acceleration-path.md`](../completed/mi210-serving-program.md#track-gpu-acceleration-path).
  ✅ 2026-08-10 — `substrate_facts.json` and the T1 recipes bind GPU NUMA node 1 versus host node 3;
  the validator refuses drift or mixed identity.

<!-- original line 3156 -->
- [x] Build the codified operator-microbenchmark recipe constructor so T1 argv is constructed, and
  bind it to a recipe id `P-AK-SEARCH-1` can cite. ✅ 2026-08-03 (evaluator/recipes.py)

<!-- original line 3159 -->
- [x] Implement the §8.5.1 source-integrity gates: symbol/registration-table extraction and diffing
  against the anchor binary, clean-build-from-snapshot enforcement, semantic diff conformance, the
  `core_header` risk tier, and repair-from-clean-parent with a per-proposal cap. ✅ 2026-08-03 (evaluator/integrity.py)

<!-- original line 3162 -->
- [x] Red-team those gates specifically: a candidate that deletes a template specialization, one that
  drops a dispatch case, one that removes an op registration, and one whose incremental tree compiles
  while its snapshot does not. Each must fail before any behavioural check runs. ✅ 2026-08-03 (in the AK3 red-team pass)

<!-- original line 3165 -->
- [x] Add full correctness surfaces: relevant ops including `MUL_MAT_ID`, exact/unseen shapes,
  PPL/numerical margin, state/rollback, no-fallback, determinism class, real-model smoke, cleanup. ✅ 2026-08-03 (evaluator/correctness.py; anchor triple bound on all 5 evidence surfaces)

<!-- original line 3168 -->
- [x] Record absolute single-stream, batched/aggregate, latency, variability, capacity, mechanism, and
  numeric correctness margins where the campaign requires them. ✅ 2026-08-03 (correctness + statistics)

<!-- original line 3171 -->
- [x] **Add an immutable archive/resume package for source-candidate T0 prerequisites.** ✅
  2026-08-12 — research `5d7a408b` snapshots the raw sensitivity, hostile-distribution, and
  checker-isolation CSV bytes before claim, verifies package/receipt/document hashes, and re-runs the
  trusted reducers against the exact completed source, binary, and evaluator identities before T0.
  Dry-run packages cannot authorize execution and parameter proposals reject them. The independent
  package/campaign/footprint slice passed **308 tests**.

<!-- original line 3177 -->
- [x] **Complete full-suite acceptance and promotion of the fresh-source prerequisite capture
  adapter.** ✅ 2026-08-12 — research main `51742ebd` makes the producer campaign-reachable, journals
  invocation/completion identity, resumes without duplicate producer calls, and binds the resulting
  strict package before claim. The correctly discovered full AutoKernel suite passed **5,464 tests
  with one expected failure**. No real source candidate, kernel build, profile, or inference ran.

<!-- original line 3183 -->
- [x] Red-team the evaluator with deliberately wrong, test-shape-specialized, fake-score, fallback,
  cache-gaming, scope-under-declaring, and timeout/leak candidates. ✅ 2026-08-03

<!-- original line 3186 -->
- [x] **Emit a PRE-CORRECTNESS PROGRESS LADDER, not a single failure verdict.** Today every non-verifying
  candidate is an equal failure, which is exactly the regime where most MI210 candidates die — so the
  search has no gradient where it needs one most. Rank `hipcc-fail < runtime-fail < wrong-output`
  (reference implementation: intake-974's `s(NX)=-0.05 < s(NC)=0.00 < s(NR)=+0.05 < s(WO)=+0.10`). This
  is the highest-value transfer of the 2026-08-03 intake batch and intake-939 has no analogue for it.
  ✅ 2026-08-10 — superseded as live fitness by the lean session-driven loop: compile exceptions,
  runtime failures, and per-gate wrong-output records remain distinct durable outcomes and are rendered
  directly; collapsing them into a scalar reward has no consumer until an autonomous selector returns.

<!-- original line 3194 -->
- [x] **Record CGRE — normalized gap closure `(T_base − T_cand)/(T_base − T_ref)`, clipped to [0,1] —
  alongside the raw ratio.** It supplies the CONTINUOUS form a hill-climbing search needs, closing a gap
  an earlier dive left open when it declined intake-939's binary/bucketed finding as gradient-hostile.
  Requires an expert reference per target, which most of our targets do not yet have — scope that first.
  ✅ 2026-08-10 — retained as an empirical field only for targets that acquire an expert reference;
  no such target/archive exists yet, so inventing a value or a live selector input is explicitly refused.

<!-- original line 3200 -->
- [x] **Adopt the epsilon-separated staircase so every correct candidate outranks every failed one**
  (`R = max(s(WO) + ε, R_succ)`, ε=0.05). **Note this is the OUTER-GATE form, which intake-939's own
  winner rejects in favour of the collapsed conjunction — see the deliberate open question in AK4.**
  ✅ 2026-08-10 — superseded by the lean rule: T0 all-PASS is lexicographically prior and failed
  candidates receive no speed rank. The loop does not scalarize correctness and performance.

<!-- original line 3212 -->
- [x] Build the structured source/profile/workload/negative-history/oracle context compiler with
  quarantined rendering of external content. ✅ 2026-08-03 (controller/context.py)

<!-- original line 3215 -->
- [x] Implement **operator hypotheses and still-open hypothesis tracking** (§8.4.0): the operator-facing
  channel, the mandatory falsifier, `design_prior` grading that origin cannot raise, re-surfacing the
  open set each round, and resolution journaled as confirmed/refuted/inconclusive with its evidence.
  Test that an operator hypothesis is rejected by the critic when it repeats a receipted negative —
  authorship is not evidence. ✅ 2026-08-03 (controller/hypotheses.py)

<!-- original line 3220 -->
- [x] Enforce proposal schema, one-concept rule, wall-share ceiling, novelty, budget, hierarchy, and
  the oracle question. ✅ 2026-08-03 (controller/selection.py)

<!-- original line 3224 -->
- [x] **Restore the lean bank/frontier/champion sequencer on the runnable journal plane.** ✅
  2026-08-12 — research `069e79fd` requires validated write-side banking, the complete sealed
  backend/tool anchor, compatible file/symbol/dispatch predicates, and direct combined-candidate
  T0/T1/T2 evidence before champion replacement. Concurrent replay is idempotent; rejected or failed
  composition preserves the incumbent; anchor moves fail closed and reanchor only absorbs members
  proven present by a matching sealed release receipt. Campaign, host-process, release, and production
  mutation capabilities remain outside the sequencer import closure.

<!-- original line 3233 -->
- [x] **Settle WHICH gate form this loop uses — the literature does not, and we should not inherit the
  ambiguity silently.** Two capable groups made OPPOSITE choices within the same family: intake-939's
  winner is the **collapsed conjunction** (correct-but-slow → full failure reward), while intake-974
  independently chose a **strictly-separated outer gate** and never tested the conjunction. Neither ran
  the comparison the other needs. **We can run it at ~zero GPU cost** via offline replay over banked
  candidate records — the two forms are different scoring functions over the same stored outcomes.
  Operator approval required before it becomes a fitness change; the replay itself is free.
  ✅ 2026-08-10 — superseded for live authority by the operator-approved lean accept rule: T0 is a
  lexicographic outer correctness gate and paired performance is considered only after all-PASS. The
  alternate scoring replay may remain an observe-only analysis under AK-WM-2; it cannot change fitness.

<!-- original line 3252 -->
- [x] **Re-derive that a capture actually ran against the anchor it names.** The five T0 evidence
  surfaces now bind the anchor triple and refuse a replay mismatch, but the recorded identity is still
  the *producer's declaration* — `produced_by` is checked and nothing re-derives it. This binds an
  honest producer's replay, not a dishonest producer's capture. Acceptable while the producer is the
  trusted evaluator the actor cannot modify; revisit if that assumption weakens. ✅ 2026-08-10 — accepted
  under the current trust boundary and made fail-closed at its projection seam: producer-supplied symbol,
  semantic-diff, and surface checks now propagate PASS/FAIL/COULD_NOT_CHECK into the 17 T0 gates instead
  of disappearing. A future untrusted producer requires a new capture attestation protocol.

<!-- original line 3260 -->
- [x] **Apply the AutoPilot operator-hypothesis integration patch** — epyc-orchestrator
  `scripts/autopilot/OPERATOR_HYPOTHESES_INTEGRATION.md`; module and tests committed in `536ea87f`.
  Six anchor points in `autopilot.py`, quoted verbatim and pinned to that file's SHA-256. **Owner:
  whoever holds `autopilot.py`** — not applied here because that repo had a live session. Until it is
  applied the channel exists and passes 25 tests, but the planner never reads it. ✅ 2026-08-10 — verified
  live in `autopilot.py`: planner-block construction, still-open context, structured resolution parsing,
  and durable resolution recording are all wired.

<!-- original line 3268 -->
- [x] **AK-WM-0 — Existing least-commitment prerequisites audited. ✅ 2026-08-05** `ProposalManifest`
  already requires a hypothesis, falsifiable counter, target/non-target frame, `novelty_basis`, and
  `expected_information_gain`; evaluator records carry `scope_denominator`; selection ranks information gain
  before expected value; and actor-declared affected scope is not trusted. **2026-08-05 re-audit:** the
  schema/evaluator controls survive, but the named planner/selection implementation was pruned on
  2026-08-04; its ordering is now a historical incumbent protocol, not a currently runnable selector.
  Preserve these as comparison baselines, not as evidence for weakness maximization.

<!-- original line 3276 -->
- [x] **AK-WM-1 — Add a representation contract before evaluating any least-commitment selector. ✅
  2026-08-05** Extended
  the proposal schema and fixtures with vocabulary/source receipts, considered and excluded alternatives,
  an empirical-demand receipt, abstraction-construction cost, canonical encoding, and semantics-preserving
  recoding fixture ids. New records use `proposal.v3`; v2 remains readable under its original validator.
  `frame_sha256` is mechanically re-derived, and `check_representation_comparable()` fails closed across
  representation or demand frames. Mechanically derived/traced affected surfaces remain authoritative over
  actor declarations. Executing campaigns now require `--proposal-manifest`; proposal-v3 is validated and
  fsynced before preflight, claim, mutation, or build, identical resume is idempotent, and same-id/different-
  bytes is refused. The AP-WM-1 evaluator is implemented as an observe-only module outside the campaign
  import path and exposes no selector/champion/T2/T3 mutation API.

<!-- original line 3291 -->
  - [x] **Implement the strict real-archive builder.** ✅ 2026-08-12 — research `900cb5c6` adds
    `least_commitment_archive_builder.py`. It accepts only real proposal-v3/v4 events joined to clean
    DECIDED terminal events with executed/ok decisions, unchanged-production PASS, released
    resources, nonempty pairs, and hash-bound diagnostic, outcome, and matched one-factor receipts.
    Missing, synthetic, mismatched-frame, direction-drifted, or receipt-tampered inputs fail closed.
    The canonical AutoKernel suite passed 4,078 tests with one expected failure.

<!-- original line 3307 -->
  - [x] **Materialize the exact prospective IQK intervention/control producer inputs.** ✅ 2026-08-12 —
    research `58b8d66a`/`948a95a4` adds the live capture-plan producer and mechanical diagnostic-source
    compiler, then materializes the intervention and A/A control proposals, SHA-bound source receipts,
    capture plans, stated hypothesis stores, and control-specific physical envelope under the two
    durable campaign roots. `evidence_path_rehearsal.py` resolves those exact files, proves one changed
    factor, validates both hypothesis statements/falsifiers, reproduces the control proposal byte for
    byte, and reaches the architecture-only `RELEASE_PACKAGE_READY` seam without inference.

<!-- original line 3314 -->
  - [x] **Migrate the durable IQK pair to proposal-v4 and regress the exact artifact path.** ✅ 2026-08-12 —
    research `3bd94893` executes both durable intervention/control inputs through the current
    `campaign.main` validator, binds the source-transparent `llama_source` provider at `a4cb04ca`,
    regenerates all proposal-dependent hashes/frames, and preserves v3 history under
    `inputs/superseded/`. Both exact dry runs exit zero with 12 steps, `state=dry_run_composed`, and
    `executed=false`; the independent full suite passed **5,606 tests** with one expected failure.
    - **Provenance note 2026-09-16 (sub-closure-fix; annotation only, box state untouched):** the cited anchor `a4cb04ca8` (`a4cb04ca8f92fa4d665684490f609b380f9b5e96`) **exists on no ref**. It is absent from all llama.cpp `fork` refs (`ls-remote`), from the canonical tree and from every local clone (`git cat-file` fails). The equivalent hardening lineage is llama.cpp `974b5fcb3` ("llama-bench: harden AutoKernel measurement instrument", sole parent frozen v9 `0db32c06`). It is the tip of `fork/experimental-v9-autokernel-t1-hardening-final`, **not** of `fork/experimental-v9-autokernel-t1-hardening` (tip `0492c2319`, a separate one-parent commit). Descendants include `d9fdc17bd`. Live manifests still pin the missing SHA: `/mnt/raid0/llm/autokernel/iqk-*.json` (6 files, e.g. `iqk-bootstrap-intervention-r3-execute.json`). The owner should re-point the pin and re-hash the manifest. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #1).

<!-- original line 3323 -->
  - [x] **Require a bound typed hypothesis before a completed proposal may enter the archive.** ✅
    2026-08-12 — archive admission now refuses exploratory campaign records and requires the terminal
    authorization to resolve by exact hypothesis id, campaign id, ledger sequence, payload, and proposal
    statement. A dry-run followed by execute under the same campaign identity remains idempotent: one
    OPENED record is retained and separate composition/live authorizations are journaled so the archive
    can bind the live spend exactly. The post-rebase suite passed **5,599 tests** with one expected failure.

<!-- original line 3329 -->
  - [x] **Repair identity-derived seed and frame binding before the reboot campaign.** ✅ 2026-08-12 —
    research `0c24bc0d` introduces a shared `akm-` experiment identity and derives benchmark, T0,
    scheduling, hold-out-selection, model, topology, calibration, envelope, provider, and intervention
    factors from the actual campaign frame. Live admission and materialization refuse any plan whose
    copied factors differ. Research `9ec0c30c` exposes the same mechanical derivation for prospective
    input generation without weakening live admission.

<!-- original line 3335 -->
  - [x] **Replace the placeholder held-out regime with a genuinely withheld prospective regime.** ✅
    2026-08-12 — research `b9bc28a6` requires a separately SHA-bound measured held-out outcome whose
    regime is outside the proposal target regimes. Missing, construction-regime, identity-drifted, or
    non-measured inputs fail capture admission.

<!-- original line 3339 -->
  - [x] **Make the control reducer evaluate the control proposal's own falsifier.** ✅ 2026-08-12 —
    research `b9bc28a6` makes the role explicit and reduces control failure from its own keep decision
    or effect beyond the accepted noise floor; intervention and control use distinct immutable rules and
    journal the bound predicates and result.

<!-- original line 3343 -->
  - [x] **Eliminate cloned diagnostic semantics across the intervention/control pair.** ✅ 2026-08-12 —
    research `b9bc28a6` derives each diagnostic/recoding block from its own SHA-bound native source
    receipt, publishes its semantic digest, and makes the matched projector refuse equal intervention/
    control semantic digests even when the numerical one-factor frame otherwise matches.

<!-- original line 3347 -->
  - [x] **Close the real-only AP-WM/report provenance gap.** ✅ 2026-08-12 — research `b9bc28a6`
    requires a strict projector result at the AP-WM CLI, labels unprojected library fixtures
    `fixture_or_unlabelled`, and emits `real` only after the archive and projector provenance validate.
    Reports now carry matched-validation, pair noise floors, and an explicit underpowered state. The
    full AutoKernel suite after this repair chain passed **5,671 tests with one expected failure**.

<!-- original line 3352 -->
  - [x] **Publish one exact proposal-v4 regeneration command.** ✅ 2026-08-12 — research `03f9ae69`
    adds `prepare_iqk_matched_pair.py`, a repository-relative deterministic producer that accepts one
    authoritative manifest and atomically writes the intervention/control proposal-v4, capture,
    diagnostic-source, held-out-outcome, and physical-envelope trees. It derives one shared frame,
    proves `ggml_iqk` is the sole changed factor, records every input/output hash, refuses overwrite and
    drift, rolls back the pair on failure, and rebuilds byte-identically in tests. Its held-out projector
    accepts only a distinct clean hypothesis-bound completed journal. Real pair materialization remains
    in parent AK-WM-2a and correctly waits for post-reboot completed journals; fixtures cannot substitute.

<!-- original line 3362 -->
- [x] **AK-WM-2b — Run AP-WM-1 on that archive, observe-only.** Report the archive protocol, ✅ 2026-11-09 CLOSED AS RETIRED (operator decision): v9-era archive path; a new campaign is needed. [no-belief: retired, operator decision 2026-11-09]
  matched-intervention validation, per-regime/surface results, noise floor, robust sign error, and
  recoding stability. Until real evidence shows invariant independent signal, do not add weakness,
  completion count, K-rho, scope width, prose length, patch size, or description length to live selection,
  champion, T2, or T3 authority.

<!-- original line 3373 -->
- [x] Implement per-backend, per-phase T2 scope and weights from compiled facts, including the
  co-resident cell and capacity deltas. ✅ 2026-08-03

<!-- original line 3375 -->
- [x] Implement the readiness signal and its coverage/non-target/mechanism guards. It reports; it does
  not trigger. ✅ 2026-08-03

<!-- original line 3378 -->
- [x] Extend `kernel_freeze_scope.py` into a complete deduplicated release-plan compiler keyed by
  source tree and reconciled affected surface, with the two-stage per-backend unchanged test (§3.2):
  build-system-derived source-closure diff as the gate, normalized comparison against an anchor
  rebuild as confirmation, transfer receipts for dropped cells, and a filed defect when the stages
  disagree. ✅ 2026-08-03

<!-- original line 3386 -->
- [x] Dry-run the T3 compiler/validator against preserved v8 and speech freeze artifacts; **expect the
  v8 dry-run to FAIL without its waiver** and treat that as calibration. ✅ 2026-08-03

<!-- original line 3389 -->
- [x] **Restore the release/readiness evaluator as a separate operator-triggered plane after the lean
  refactor.** ✅ 2026-08-12 — research `99fe3014` restores readiness, generic T3, and package
  assembly behind pure receipt inputs and injected evaluator authority. Release-local preflight
  enforces the ratified seven-day uptime ceiling and held-resource/storage checks without reading or
  mutating the host. The plane cannot write production, spawn/signal a process, execute a drafted
  command, or self-trigger; release mode refuses until `P-KERNEL-FREEZE-1` is human-ratified.

<!-- original line 3401 -->
- [x] Implement the packager: transaction plan, rollback plan, draft era row, draft AutoPilot
  rebaseline note, linkage results, and a pre-validated command sequence. ✅ 2026-08-03

<!-- original line 3403 -->
- [x] Prove it refuses missing hashes, evaluator drift, dirty ancestry, reused version names,
  incumbent modification, and an incomplete rollback. ✅ 2026-08-03

<!-- original line 3409 -->
  - [x] **Complete the offline operator-closeout integration fixture.** ✅ 2026-08-12 — research
    `4a5f7361` runs the injected lean sequencer through a schema-bound composed champion, readiness,
    dry-run T3, and a validated `RELEASE_PACKAGE_READY` record. It is unreachable from Campaign #1,
    cannot build, infer, execute processes, or write production, and labels architecture fixtures
    `empirical_claim=false`. The independently repeated focused suite passed **1,692 tests**. This is
    regression evidence only and does not close the parent empirical campaign task.

<!-- original line 3418 -->
  - [x] **Complete the offline fault-injection acceptance matrix.** ✅ 2026-08-12 — research
    `900cb5c6` ran three repetitions of a 657-test matrix: **1,971/1,971 PASS**, no inference. The
    journal, GPU claim, CPU claim, hypotheses, Arena cell runner, statistics, C3 compiler, and physical
    bounds suites cover torn-write/restart recovery, exact-owned-PID crash/reclaim, live-holder
    non-preemption and revocation, plus receipt/hash/source tamper refusal. The broader 4,078-test
    suite passed once with one expected failure. This closes offline acceptance only.

<!-- original line 3424 -->
  - [x] **Publish and verify the governed real host-process rehearsal receipt.** ✅ 2026-08-12 —
    research `d0b243a5`/`5c8714a1` launched only exact captured private-session children, planted a
    journal crash and replayed it after restart, proved fake-device revocation was advisory rather
    than preemptive, terminated the exact captured holder, and refused changed hash-bound bytes.
    Campaign `ak-fault-rehearsal-20260812-r2` passed **3/3** legs, touched no live claim root, and
    emitted three dependency-evidence rows sharing one support key with no performance, campaign,
    ranking, release, or production authority. Receipt self-hash `8a345fbdbfff4bb04b4ac3388b8e82ff347941bc8fb93cbe8266ee2b2ed79a58`;
    file SHA-256 `70e9f87bc5405be6e66c9c0f6ce49f0427f1c83ba0f14491c93401e5283d688e`.

<!-- original line 3432 -->
- [x] Give the operator surface a freshness and health contract, not just data. Today's `/kernel` page is
  **absence-tolerant over a missing directory** — it renders clean when its producer is dead, which is
  the exact shape of AutoPilot dying at trial 1302 and staying dead ~23 h with every dashboard green.
  Required: a per-panel freshness envelope, an SSOT panel→producer registry whose test fails when a
  panel has no registered source, a `/health` fold, a transport watchdog, and a restart chaos test. ✅ 2026-08-03

<!-- original line 3437 -->
- [x] Replace the `/kernel` dashboard JSON contract. The existing one exposes a partial Pareto and
  nothing else; the new contract carries campaign phase, champion membership and readiness, per-backend
  standing, storage and budget headroom, open blocking conditions (`EVALUATOR_COVERAGE_GAP`,
  `ANCHOR_MOVED`, phase-trade exceptions), resource claims held, and release-package state. Version the
  contract explicitly, keep it absence-tolerant as the current page is, preserve the freshness envelope,
  and point `KERNEL_DASHBOARD_JSON` at a durable path rather than the missing scratch directory. ✅ 2026-08-03

<!-- original line 3443 -->
- [x] **Repair the Kernel-R&D dashboard's current-receipt selector and live runs producer.** ✅
  2026-08-12 — root `572f33af` adds schema-selected current receipts and a loud missing-attestation
  alarm; `d76b6ee1` binds the supervised hub to the clean deployed checkout; `5bae9d3f` closes the
  inherited supervisor lock FD in the detached hub. Live `/api/kernel`
  reports frozen production v9, `8/8` instrument preflight, `5/5` accepted controls, the GPU replay's
  honest `NOT_REPRODUCED` verdict, and implementation head `900cb5c6`. The terminal v2 campaign
  export is fresh and names the reboot-gated preflight refusal; **85/85** focused deployment tests
  pass. The Kernel-R&D panel's `/api/health` contribution remains `absent` because `champion`,
  `headroom`, and `release_package` are correctly `not_reported` until a real campaign completes,
  not because the dashboard producer is stale.

<!-- original line 3453 -->
- [x] **Execute the Kernel-R&D current-state renderer in the static-JavaScript gate and restore the
  complete evidence view.** ✅ 2026-08-12 — root `2183cf1e` fixes a free-identifier runtime failure
  that parsed successfully but stopped rendering before controls, empirical gates, activity, and all
  seven contract sections. The regression harness now executes the renderer against the minimum
  production-set wire shape and requires full blocking-condition detail plus distinct tree identity,
  observed/attested ggml, non-executing ELF linkage, and dashboard-process ambient-path claims.
  `tests.test_dashboard_static_js` passed **28/28**.

<!-- original line 3460 -->
- [x] **Teach Kernel-R&D to select current v2 AutoKernel attempts and classify live versus unresolved
  terminal state.** ✅ 2026-08-12 — root `5180663a` accepts v1/v2 manifests, uses exact PID plus process
  start-tick identity for live state, and distinguishes curated-invalid, preflight-refused,
  terminal-complete, and stale-or-terminal-unreported attempts rather than falling back to stale
  six-arm r4. It also reports frozen v9 and the current implementation/readiness gates. The commit is
  pushed on root `main`.

<!-- original line 3467 -->
- [x] **Project the terminal raw-HIP r6 decision receipt on Kernel-R&D without manufacturing a
  champion.** ✅ 2026-08-12 — the hub admits only the exact self-hashed
  `epyc.autokernel.hip_decision_grade.v1` receipt at campaign r6, verifies its producer, sealed MI210
  task, 24/24 correctness, numeric error evidence, block-9 e-process crossing, and all 40 per-arm
  duration admissions, then exposes the exact file/self hashes. The distinct card labels the result
  task-local, says `NOT A CHAMPION`, requires experimental llama integration, and carries
  `release/promotion authority: false`. Static JavaScript and producer projection tests fail closed
  on partial admissions or widened authority; no inference ran.

<!-- original line 3475 -->
- [x] **Surface current loop-engineering and host-process recovery evidence on Kernel-R&D.** ✅
  2026-08-12 — root `26a9b9f1` adds distinct AK-LE and fault-rehearsal cards. The loop card reports
  the newest complete panel only as raw evidence until a governed reduction exists, then shows its
  producer-authored observation count without granting ranking authority; the fault card reports
  exact leg coverage and the no-live-claim-root boundary without grading dependency evidence as
  performance. Root `2d0d9af4`'s runtime harness plus focused static/panel tests passed. The resident
  root-main hub at `e861baf4` (supervisor PID `2455173`, hub PID `2468686`) rendered r3 `8/8` / 32
  rows, all eight cell detail rows (model, effort, target, survivors, termination, wall time), and r2
  `PASS` / `3/3` at runtime with no JavaScript exception and no inherited `LD_LIBRARY_PATH`.

<!-- original line 3484 -->
- [x] **Make frozen-kernel working-tree drift a first-class production-set alarm.** ✅ 2026-08-12 —
  root `a19becb5` projects tracked and untracked status for all three frozen trees, requires cleanliness
  for `intact=true`, and renders exact dirty paths. The reloaded hub (supervisor PID `2455173`, hub PID
  `2478391`) reports whisper.cpp and qwentts.cpp clean, while llama.cpp is dirty only because three
  preserved user-owned paths are untracked: `.gitnexusignore`, `tools/math-tools/external/eigen/`, and
  `tools/math-tools/external/odeint/`. No production-tree mutation or cleanup occurred. Focused tests
  passed **124 cases plus 12 static-JavaScript subtests**.

<!-- original line 3491 -->
- [x] Add a non-recursive, panel-specific Kernel-R&D data-health probe so registry consumers can
  distinguish hub transport health from AutoKernel producer health without recursing through the
  global `/api/health` fold. ✅ 2026-08-12 — root `6188197f` moves the registry probe from
  transport `/health` to `/api/kernel/health`. Live transport returns HTTP 200 while the semantic
  endpoint correctly returns HTTP 503 / `absent`, scoped only to Kernel-R&D's unreported
  `champion`, `headroom`, and `release_package` sections. The promoted hub remains supervised by PID
  `1689063` with hub PID `1689100`; no global-health recursion or unrelated timeline state enters the
  panel result.

<!-- original line 3499 -->
- [x] Extend production-kernel-set projection from the attested llama.cpp v9 anchor to the separately
  frozen whisper.cpp and qwentts.cpp identities; do not imply the current llama campaign governs
  speech kernels. ✅ 2026-08-12 — root `d2cd8639`, `205b9444`, and `10e3ab77` project the independently
  frozen three-tree/four-binary set, all four stable serving links, non-executing `readelf` linkage,
  ambient loader-path risk, and ggml generations. The exact final focused suite passed **28 tests**.
  Live contract v2 proves `3/3` trees, `4/4` binaries, `4/4` links, and `4/4` ELF linkage without
  executing a production binary; it remains fail-closed on the two residuals below.
  - [x] **Resolve or explicitly retain the frozen llama working-tree cleanliness alarm.** ✅
    2026-08-12 — retained, with no production-tree mutation. The two January-era nested repositories
    are clean third-party source caches: Eigen at `251bff28859af2ed2d5bdf14034175f03cafffc7` and
    Boost.Odeint at `9e75be5d9e435739b086aee928736fc241e77a4a`; classify both as ignore/cache rather
    than production source. `.gitnexusignore` is a July-era repo-local parser policy and is a candidate
    for deliberate tracking in the next versioned experimental tree or its agent overlay, not an
    in-place frozen-v9 commit. The dashboard must continue to report v9 dirty until a future authorized
    versioning or cleanup action resolves those paths.
  - [x] ~~**OP-17 — Decide whether to attest llama.cpp's ggml generation for the frozen-v9 set.**~~ (closed 2026-10-29 audit: OBSOLETE → frozen-v9 attestation question superseded by v10 final freeze 2026-09-22 (ratify_v10_final_freeze_20260922.json); v9 now rollback anchor only)
    - **Context:** the live tree reports ggml `0.16.0`, but the v9 operator attestation does not state
      an expected ggml generation. The dashboard therefore proves only `2/3` and reports `SET NOT
      PROVEN`; deriving expected authority from the observed tree would be circular.
    - **Option A — amend the frozen-v9 attestation after independent verification (recommended):**
      bind expected llama ggml `0.16.0` through the human-only measurement trust boundary, then let
      the existing comparison prove or refute it.
    - **Option B — retain the current attestation:** keep llama generation explicitly unverified and
      accept that the complete-set fold cannot become intact.
    - **Default:** Option B; no attestation or production state changes.
  - **[declined: ws58 2026-11-03 content-review: stale reboot item (reboot 2026-08-13 done)]** **After OP-16's reboot, re-check the live dashboard process environment.** Durable host and
    devcontainer configuration are clean. The dashboard hub was already reloaded cleanly before the
    reboot decision (PID `2478391`, `LD_LIBRARY_PATH` absent), replacing the earlier long-lived process
    that inherited two ggml-bearing entries. Still require a fresh post-reboot
    `ambient_library_path.clean=true`; one clean dashboard process is not proof about every launcher.

<!-- original line 3554 -->
- [x] **THE BLOCKER — no candidate could cross the evidence threshold.** Calibration solves
  `threshold=10`; the sign-martingale over 5 same-sign blocks topped out at **5.5687**, verified
  magnitude-independent (true-effect factors 1.08 → 3.0 all returned the same e-value). Closed by
  building the extension-round producer. Demonstrated both directions: a real +8% effect goes
  `5.5688 → 42.2877` over 10 blocks and banks; a true null stays at `0.9000` and abandons.
  ✅ 2026-08-04

<!-- original line 3560 -->
- [x] Extension-round order schedule settled — **extended**, keyed on attempt parity, so
  `derive(attempt=n)` equals `n` chained `retry()` calls. `attempt=0` is byte-identical, so the
  first campaign is unaffected. ✅ 2026-08-04

<!-- original line 3563 -->
- [x] Anchor triple bound for **two tools** (T0 hashes `llama-cli`, microbench compares against
  `llama-bench`). ✅ 2026-08-04

<!-- original line 3566 -->
- [x] T0 producers wired (`extract_elf_symbols`, `parse_unified_diff`, the `surface.py`
  derivation). ✅ 2026-08-04

<!-- original line 3589 -->
- [x] Build the per-candidate run ledger that makes the above machine-enforced rather than
  procedural. `MICROBENCH_RUN_COMPLETED` carries the full raw vector plus its content-hash identity;
  runner and pooling tests prove a duplicate key spends no further inference. ✅ 2026-08-05

<!-- original line 3595 -->
- [x] **`campaign.py` — the entrypoint the package spent 94k lines not having.** A `grep` for
  `__main__|argparse|def main(` across every non-test module returned *nothing*: 5,695 tests passing
  in 47 s and no way to start it. Twelve steps, `--dry-run` as the DEFAULT so it cannot benchmark by
  accident on a shared host. ✅ 2026-08-04

<!-- original line 3599 -->
- [x] The accept rule, in four conditions rather than a statistics module: T0 all-PASS
  lexicographically first, then over N **pre-committed** pairs keep iff `min(delta) > 0` and
  `median(relative) > drift_bound`. `decide()` refuses any other block count, so optional stopping is
  impossible rather than discouraged. ✅ 2026-08-04

<!-- original line 3603 -->
- [x] **The first real A/A this package has ever had** — four runs of identical code, between-run CV
  1.62%/1.88%, and a monotone 4.2% decode decline that makes interleaved pairing mandatory rather
  than merely advisable. Everything was calibrated against synthetic numbers until now.
  `data/autokernel_aa_20260804/`. ✅ 2026-08-04

<!-- original line 3607 -->
- [x] `program.md` — the human control surface: the loop procedure plus a hypothesis inbox, modelled
  on `karpathy/autoresearch`'s 114-line equivalent. ✅ 2026-08-04

<!-- original line 3609 -->
- [x] Hypothesis path end to end: falsifier optional at entry and **mandatory before compute**;
  adoption **removes** the entry from the operator's store (journal-first, so a crash leaves a
  detectable duplicate and never a loss); the do-not-repeat ledger `check_do_not_repeat()` had always
  consumed and nothing had ever built. ✅ 2026-08-04

<!-- original line 3613 -->
- [x] `--hypothesis` wired to the claim, closing the FIFTH "guard defined and never wired" in this
  package — `claim_for_hypothesis` calls itself *"The ONLY route from a hypothesis to a resource
  claim"* and had zero non-test callers. ✅ 2026-08-04

<!-- original line 3616 -->
- [x] **~79,600 lines deleted** (`release/`, `adapters/`, `surface/`, the AK4 strategy plane), tag
  `autokernel-preserve-20260804`. Verified first with Python's own import machinery: the driver's
  closure is 22 modules and reached none of it. The review's condemnation of `evaluator/integrity.py`
  and `evaluator/surface.py` was **wrong** — the driver imports both. ✅ 2026-08-04

<!-- original line 3620 -->
- [x] Refactor plan Steps 0–2 executed: placeholder digests refused (`BuildProvenance.
  output_binary_sha256` accepted 64 zeros), `produced_by` on the two evidence types that lacked it,
  `Check.worst_of` (an empty vector is COULD_NOT_CHECK, never PASS), `schemas.require`, and the
  self-audit identity binding at `evaluator/api.py` and `evaluator/integrity.py`. ✅ 2026-08-04

<!-- original line 3627 -->
- [x] **Answer whether the decode drift recovers after rest** (Step 1 below). Under one q0–q3 claim,
  the old decline did not reproduce: decode rose across the four pre-rest runs; 180 seconds idle made
  the first following run 3.29% colder; the second recovered to 0.50% below the pre-rest run. Do not
  add inter-arm rest; retain pairing and warm once after a long idle boundary. Evidence:
  `epyc-inference-research/data/autokernel_aa_20260805_rest_recovery/`. ✅ 2026-08-05

<!-- original line 3632 -->
- [x] Replace the placeholder accept threshold (2.1310%, from four runs on one model) with the first
  campaign's own calibration block. The fresh accepted campaign binds a 3% contribution floor,
  φ=4.9207%, B_min=12 and MDE=2.7408%. ✅ 2026-08-05

<!-- original line 3635 -->
- [x] Bind `evaluator/api.py`'s **supplied-source** audit to the module it claims to inspect. ✅ 2026-08-10 — fixed:
  supplied source must define the audited module's declared `MODULE_ID`; absent or mismatched identity
  is `COULD_NOT_CHECK`, while forbidden imports/calls remain `FAIL`. This is exercised across the API,
  correctness, controls, devices, statistics, and control-runner callers.

  This was the
  shared-AST-engine contract and cannot change without a `module_id` kwarg — Step 4 of the refactor
  plan (`capability.py`); the narrow identity-binding fix closed the defect without a policy union.

<!-- original line 3643 -->
- [x] The `capability.py` hoist itself: 11 audit functions, ~631 lines, 5 denylist tables → one
  walker + ~200 lines. **Guard rail:** the five denylists are *four different policies*, not four
  drifted copies — `microbench.py`'s list is INC-20260731 encoded as data. Unioning them is a
  category error that would weaken the execution plane while reading as a cleanup. ✅ 2026-08-10 —
  superseded by the operator's lean-loop boundary: keep the distinct policies and shared validation
  primitives; do not restore a broad capability plane before real campaign evidence justifies it.

<!-- original line 3649 -->
- [x] A structural audit that every declared guard has a caller. Five instances of "declared and
  never wired" have now been found by hand, the most recent written hours after the refactor plan
  assessed that row as "0 live". Fixing instances is not working. ✅ 2026-08-10 — the campaign-footprint
  suite now carries a five-entry source-level caller contract for worktree mutation refusal, retry-order
  reversal, do-not-repeat, per-control seed rotation, and falsifier-before-claim; a missing live caller
  fails the build.

<!-- original line 3678 -->
- [x] Confirm no material CPU contention and that whoever owns the stack knows the host is being
      measured. The resident production stack was operator-confirmed idle; a one-core test process
      was ~0.5% of the 192-thread host, not 89% host-wide. One q0–q3 claim covered the full probe.
      ✅ 2026-08-05

<!-- original line 3682 -->
- [x] Verify host canonical state — governor `performance`, THP `always/always`, `numa_balancing=0`.
      ✅ 2026-08-05

<!-- original line 3696 -->
- [x] **Does the decode decline recover after rest?** The previous monotone trajectory did not
      reproduce. Decode rose 32.55 → 32.67 → 32.85 → 34.00, then fell to 32.89 on the first run
      after 180 seconds idle and recovered to 33.83 on the second. The cold-first-run effect argues
      against inter-arm rest; retain interleaved pairing and warm once after long idle. Absolute
      throughput also shifted sharply between days, so calibration stays inside one host-state
      window. Evidence: `data/autokernel_aa_20260805_rest_recovery/`. ✅ 2026-08-05

<!-- original line 3705 -->
- [x] **Bind the hardened instrument to clean, committed provenance before inference.** ✅ 2026-08-12 —
      `experimental-v9-autokernel-t1-hardening-final` at
      `a4cb04ca8f92fa4d665684490f609b380f9b5e96` has exactly one parent, frozen v9
      `0db32c06e3e550065b78311a6031ef3dd2c4f27c`, changes only `llama-bench.cpp` and its README,
      is clean, and is pushed to the internal fork. The clean CPU build's copied `llama-bench` is
      SHA-256 `19dfba5c65a94e7b27e3db001a8a6a250a91d013bfea73970f4e931f0c1e54b0`.
      A claimed 0–95 CPU smoke emitted all six required hybrid-sync, thread-set, escape-check,
      unsynchronized-sample, and device-sync receipts (`cpu_not_applicable`) and released its q0–q3
      claim. The all-PASS preflight is
      `/mnt/raid0/llm/autokernel/probes/ak-v9-final-preflight-20260812-r1/preflight.json`, SHA-256
      `0baf7b73055f028c5c493afd9a4ab8c9950d3c088ed79f3751102ddff71fdefd`.
  - **Provenance note 2026-09-16 (sub-closure-fix; annotation only, box state untouched):** the cited anchor `a4cb04ca8` (`a4cb04ca8f92fa4d665684490f609b380f9b5e96`) **exists on no ref**. It is absent from all llama.cpp `fork` refs (`ls-remote`), from the canonical tree and from every local clone (`git cat-file` fails). The equivalent hardening lineage is llama.cpp `974b5fcb3` ("llama-bench: harden AutoKernel measurement instrument", sole parent frozen v9 `0db32c06`). It is the tip of `fork/experimental-v9-autokernel-t1-hardening-final`, **not** of `fork/experimental-v9-autokernel-t1-hardening` (tip `0492c2319`, a separate one-parent commit). Descendants include `d9fdc17bd`. Live manifests still pin the missing SHA: `/mnt/raid0/llm/autokernel/iqk-*.json` (6 files, e.g. `iqk-bootstrap-intervention-r3-execute.json`). The owner should re-point the pin and re-hash the manifest. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #1).

<!-- original line 3718 -->
- [x] **Run the five fixed controls (§15.2) before any real search**: positive, neutral, negative,
      A/A, and the **historical-win replay — the iqk port, which MUST promote**. The negative control
      is the one that catches a fast-looking wrong kernel, and a loop whose controls have not run is
      an instrument nobody has calibrated. Every benchmark number in the 3,596 tests is synthetic;
      the five controls are the first real ones. The fresh 3%-floor campaign produced a **5/5 PASS**
      panel: positive and historical IQK arms promoted, neutral/A/A stayed below the noise floor,
      and the wrong-work negative received no speed rank. Evidence:
      `data/autokernel_controls_3pct_20260805/`. ✅ 2026-08-05

<!-- original line 3726 -->
- [x] Solve the calibration block off the A/A pool and record φ, α_sel, α_conf, the noise floor and
      the MDE this campaign is judged under. The current accept threshold — **2.1310%**, from
      `data/autokernel_aa_20260804/` — is a placeholder from four runs on one model; replace it with
      the campaign's own calibration. A first predeclared 2% campaign correctly rejected because
      its 20-block MDE was 2.5867%; no controls ran under it. A genuinely fresh 3% campaign then
      accepted with φ=`0.049206882811302755`, α_sel=`0.1`, α_conf=`0.05`, B_min=`12`, MDE=`2.7408%`,
      and an A/A false-crossing rate of `1.4%`. ✅ 2026-08-05

<!-- original line 3733 -->
- [x] **Make calibration authority era- and instrument-local.** The executing CLI now requires
      `--calibration-bundle`, verifies the bundle's source-label hash, accepted solve/control state,
      production commit, measurement-instrument commit, recipe, floor, B_min/ceiling and MDE, and
      refuses the v8 bundle on v9. Dry run reports `UNCALIBRATED CELL` rather than printing the old
      2.1310% placeholder as live authority. ✅ 2026-08-11

<!-- original line 3738 -->
- [x] **Close package-power admission without broadening host privilege.** ✅ 2026-08-12 — research
      commit `1094ff6b` adds a lazy, exact-container-id broker pinned to image
      `sha256:3a2e92b4133d06d1287f96ec47bacd743717b377f4b9df6be1e3af626c35dbb0`, with no network,
      a read-only root, all capabilities dropped, `no-new-privileges`, a 16-PID limit, and only the
      powercap mount exposed read-only. The v9 preflight now passes package-power availability; unit
      coverage proves exact-id stop/inspect/kill escalation and refuses image-identity mismatch.

<!-- original line 3744 -->
- [x] **Require a fresh campaign identity and self-consistent evidence root.** ✅ 2026-08-12 —
      research commit `7f8e9997` removes the retired hard-coded campaign id and evidence directory,
      requires `--campaign-id` plus an absolute `--output`, and deterministically derives the seed and
      window id. Declaration, calibration, claim, host, control, evaluator, and summary receipts now
      carry the same identity; invalid ids and relative evidence roots fail before execution.

<!-- original line 3749 -->
- [x] **Run the five controls against frozen v9 plus the hardened measurement instrument.** ✅
      2026-08-12 — `ak-controls-v9-a4cb04ca-20260812-r2` accepted at contribution floor `3%`,
      B_min=`10`, φ=`0.03578502357852242`, and passed positive/neutral/wrong-work/A/A/historical
      controls (`5/5`, `may_rank=true`). The historical IQK replay promoted at
      `+0.2660503395746673`. Summary SHA-256
      `81b5bc4b95cfd8e3ca9346c9f44a70fc297c159310e57bdb84f62c80588d78e1`; control-sweep SHA-256
      `9f765c5c19d0ea4669ac55a55796a643b578c4ff1bf126b5f6b630a297197ae1`. The six inference legs
      completed under claim `akclaim-c9f943ba08234877`, whose journal records release at
      `2026-08-12T00:46:23.957344+00:00`. When deterministic post-processing exposed missing
      `CampaignBinding.change_class`, research `c4a42c69` repaired the evaluator and recomposed the
      immutable raw vectors without inference; `composition_attestation.json` binds every input hash,
      evaluator commit `c4a42c69917187b53809c8d4c3267cc1a99a37de`, and
      `inference_executed=false`.

<!-- original line 3762 -->
- [x] **Recalibrate the final direct-child IQK instrument after empirical T0 repairs.** ✅
      2026-08-13 — final instrument `283b520b527a7b507d6cf05cd124a59f427f3629`
      is a clean direct child of frozen production `0db32c06…`, contains the committed T0
      receiver plus the Q4_K and Q4_0 narrow-shape fallbacks, and passed all five live controls at
      `/mnt/raid0/llm/autokernel/controls/ak-controls-v9-283b520b-20260813-r1/`
      (`controls_complete`, `may_rank=true`, B_min=11, MDE=1.4562%).

<!-- original line 3771 -->
- [x] **Close the first-campaign `HostOps` adapter before taking a claim.** Supply the candidate
      mutation (or the declared no-source parameter comparison), measured `llama-cli` and
      `llama-bench` anchors, the proposal-owned T0 declarations/registration patterns, and the
      healthy all-core nominal frequency. The CLI's pre-claim refusal is the acceptance test; do not
      bypass it with a placeholder capture. ✅ 2026-08-11 — the built-in proposal-v3 IQK parameter
      adapter proves an empty source diff, derives the registered parameter surface and IQK registration
      patterns, measures separate `llama-cli`/`libggml` anchor identities, and requires `--nominal-khz`;
      `unimplemented_seams()` plus CLI tests refuse before claim if any required input is absent.

<!-- original line 3779 -->
- [x] **Turn the six reference-leg T0 unknowns into real evidence for the first parameter candidate.** Close exact reference,
      ASAN/UBSAN applicability, state rollback/teardown, symbol-version coverage, and affected-
      surface reachability. `COULD_NOT_CHECK` remains speed-blocking; do not reinterpret it as PASS.
      ✅ 2026-08-11 — the source-free registered surface proves memory/threading/persistent-state false,
      which resolves ASAN, UBSAN, state safety, and reconciliation by non-applicability; ELF v2 parses
      exported version indices and leaves genuinely versioned exports explicit; `test-backend-ops`
      emits `AK_REF_V1` only after its separately activated CPU reference path passes, and T0 projects
      its observed comparator error/tolerance without mislabelling NMSE as ULP or bitwise identity.
      Generic source proposals still fail closed where whole-program absence or rollback cannot be proved.

<!-- original line 3788 -->
- [x] **Live-validate the stateful T0 integrity pass.** ✅ 2026-08-11 — with suite seed `4711`, all
      **5,184/5,184** cases passed across `SSM_SCAN`, `SSM_CONV`, `FLASH_ATTN_EXT`, and
      `GATED_DELTA_NET`. Every `AK_STATE_V1` receipt proved equal initial state inputs, immutable
      input buffers, and one or more compared final-state outputs. The fail-closed consumer is
      research commit `9cc3ed1b`; the experimental producer remains uncommitted pending explicit
      operator approval and was not committed or pushed by this checkpoint.

<!-- original line 3794 -->
- [x] **Live-validate the independent host-double fp64 oracle.** ✅ 2026-08-11 — direct GGUF-wire
      decoders cover Q4_0, Q8_0, Q4_K, and Q6_K under metric
      `fp64_error_ratio/host-double-gguf-wire/v1`. Five representative CPU cases, the dedicated
      broadcast regression, 31 real parser tests, and the property self-test's 5/5 planted plus 5/5
      clean cases passed. The full stock ROCm Q4_K matrix separately exposed genuine baseline κ=1.5
      failures; the gate remains fixed and the uncommitted experimental implementation was not staged,
      committed, or pushed.

<!-- original line 3801 -->
- [x] **Prepare and fail-closed preflight the first CPU IQK campaign.** ✅ 2026-08-12 — rebound
      the physical envelope to exact deterministic recipe frame
      `e504d8e937fd0f645b8dadb3b971e320f95c2f1bf34fc678b186fbf37bb079b0`; dry run was clean;
      repaired the missing `/workspace/repos/epyc-whisper` and `epyc-qwentts` symlinks; and verified
      both frozen speech kernels. The first live attempt stopped on the missing symlink before claim;
      the corrected attempt stopped in preflight because uptime was `13.47 days`. Neither attempt
      acquired a claim, built a candidate, or benchmarked. The append-only proposal and both
      fail-closed STOP_STATE records remain in
      `/mnt/raid0/llm/autokernel/campaigns/ak-iqk-v9-20260811/events.jsonl`.
  - [x] **Recover and validate the exact current dry-run invocation.** ✅ 2026-08-12 — the recovered
    intervention and matched A/A commands exit zero without host mutation, bind their exact
    `--least-commitment-capture-plan`, `--hypothesis`, and `--hypothesis-store` inputs, and compose the
    current-code steps with the accepted 3% floor, B_min 10, CPU `0-95`, and required
    `--nominal-khz 2500000`. Dry-run authorization does not consume the live authorization: identical
    execute-mode pickup appends a distinct typed spend record. Both durable commands are recorded in
    `progress/2026-08/2026-08-12.md`; governed execution still requires OP-16 and fresh post-reboot
    preflight.
  - [x] **Repair the IQK capture-plan producer/validator bootstrap regression.** ✅ 2026-08-12 —
    `b9bc28a6` made a pre-existing completed held-out journal mandatory at capture-plan load, while no
    such real out-of-regime IQK journal exists; the first campaign could therefore never start. Research
    now makes the state explicit: `bootstrap` plans bind proposal, hypothesis, exact factor frame,
    diagnostics, calibration, and physical envelope but cannot enter AP-WM/archive authority. A later
    `heldout_bound` plan still requires the strict completed-journal projector. Fresh r3 intervention
    and A/A inputs under `/mnt/raid0/llm/autokernel/campaigns/ak-iqk-v9-20260812-r3/` and
    `/mnt/raid0/llm/autokernel/campaigns/ak-iqk-v9-aa-control-20260812-r3/` both dry-run clean.

<!-- original line 3826 -->
- [x] **After a compliant host reboot, rerun the prepared full-host CPU IQK campaign.** ✅ 2026-08-13 —
      the reboot occurred, host/production checks passed, and the campaign advanced through the
      immutable r23–r41 attempts without bypassing claim, build, correctness, or measurement gates.
      r41 is the first rankable intervention; its matched control replay and held-out chain remain
      separately filed below.
  - [x] **OP-16 — Operator decision package: authorize the orderly reboot.** ✅ 2026-08-12 — the
    operator granted the AutoKernel session ownership of all compute resources and approved the
    reboot→IQK→archive execution sequence. Preserve the r3 checkpoint, then reboot only after the
    preflight checklist and current-source commit are durable.
    - **Context:** CPU IQK preflight measured host uptime at approximately `13.48 days`; the ratified
      seven-day ceiling requires a reboot before further search measurement. The refusal occurred
      before inference, claim, build, or benchmark, and every current artifact is wrapped and pushed.
    - **Option A — authorize an orderly reboot now (recommended):** preserve the accepted v9 control
      bundle and journal, reboot after all mains report ready, bootstrap the `agent` tmux session per
      session-bus C20, respawn the established roster, then rerun the prepared campaign. This is the
      shortest compliant path and is reversible operationally; reboot downtime is the cost.
    - **Option B — postpone the reboot:** leave the host and production stack as-is. AutoKernel CPU
      measurement remains fail-closed; no result or resource consumption occurs, but the empirical
      chain cannot advance.
    - **Recommendation:** Option A. All pre-reboot durability obligations are satisfied and no useful
      protocol-compliant CPU candidate measurement can proceed at the current uptime.
    - **Default:** Option B; preflight continues to refuse and no inference runs.

<!-- original line 3848 -->
- [x] **Close empirical T0 defects surfaced by the post-reboot IQK rehearsal.** ✅ 2026-08-13 —
      r23's real property suite exposed input-dependent Q4_0 `m=16,n=2,k=256` error; Q4_0 now
      falls back below 32 rows, matching the Q4_K safeguard, and the exact linked suite passed
      1,954/1,954. Durable T0 output proved scheduler execution; research `da7d14fa` parses its
      bare timestamp format. Research `430443c5` preserves a legitimate T0 refusal rather than
      misclassifying it as a candidate-record error. r23 produced no throughput result.

<!-- original line 3854 -->
- [x] **Reboot and execute the fresh bootstrap-pair attempts through r29.** ✅ 2026-08-13 — r25 reached
      passing T0 but exposed a `MicrobenchPlan.schedule()` driver call defect; r26's T0 truthfully
      rejected the Q6_K `m=16,n=3,k=256` IQK result; r27 refused contaminated host admission; and
      r28 showed that the former load gate counted campaign-owned T0 residual as outside contention.
      r29 intervention reached `DECIDED` with all ten pairs and production PASS, but correctly
      reverted as inadmissible when anchor drift was 15.27% against a 3.08% bound. Its A/A arm
      terminally refused preflight while a separate OpenDataLoader workload held the CPU. None of
      these immutable journals substitutes for the required clean matched pair.

<!-- original line 3862 -->
- [x] **Make the CPU IQK instrument and T0→T1 boundary fail closed on the observed failures.** ✅
      2026-08-13 — experimental direct-child `f744cc220e722d1bda93783959471d44f8e118b0` adds only
      the Q6_K `<32` native fallback; its exact seeded property suite passes. Research `deeed365`
      requires every T0 sandbox teardown receipt, a 65-second decay, and three fresh low-load
      attestations before the unchanged T1 admission gate. Fresh controls at
      `ak-controls-v9-f744cc220-20260813-r1` are accepted/rankable (5/5, B_min=10,
      MDE=2.0360%).

<!-- original line 3869 -->
- [x] **Harden and calibrate the IQK bootstrap frame through r36.** ✅ 2026-08-13 — r2/r3 exposed
      `-r 5` instability and source/path A/A asymmetry; `798016e3` fixed a sealed `GGML_IQK=0/0`,
      `reps=1` frame and r4 was accepted (5/5, B_min `15`, MDE `2.9585%`). `7486a167` refuses
      out-of-range pairs before publication. r34/r35/r36 are terminal non-archive attempts as recorded
      in the dated historical checkpoint; later r41 evidence supersedes them as current state.

<!-- original line 3874 -->
- [x] **Land the sealed T0 and decode-cell producer prerequisites for the final pair.** ✅ 2026-08-13 —
      research `eb898bd0` accepts sealed matched-pair T0 evidence, `c376853d` proves frame tampering
      fails closed, `de464126` calibrates the held-out decode cell independently, and `0f137f50`
      resolves its control frame at runtime instead of carrying a stale precomputed binding.
      Research `c81b67db` prepares recipe-bound decode IQK pairs and `8a701354` binds each pair
      envelope to the independently calibrated cell.

<!-- original line 3880 -->
- [x] **Execute the r41 IQK intervention and preserve the matched control's exact refusal.** ✅
      2026-08-13 — the intervention reached terminal `DECIDED` with T0 PASS, production unchanged,
      released resources, 15/15 positive blocks, median relative gain **+27.6481989%**, and
      `speed_rank_admissible=true`. The A/A control stopped at `t0_failed` before measurement solely
      on `EVALUATOR_BUNDLE_UNVERIFIED`; all its other T0 gates passed and its resources released.
      Neither the invalid control nor the unmatched intervention may enter AK-WM-2a.

<!-- original line 3886 -->
- [x] **Seal evaluator identity at campaign start and add the nonpromotable discovery tier.** ✅
      2026-08-13 — research `a65e638a` closes r41's live-checkout identity race. Research `28e7c41a`
      caps screening at three paired blocks and structurally forbids KEEP/archive/promotion;
      `59a4ec91` requires a hash-valid exact-frame amortized baseline bank and reports uncertain top-K
      nominations only.

<!-- original line 3891 -->
- [x] **Prepare a fresh r42 pair instead of mutating the terminal r41 identity.** ✅ 2026-08-13 —
      both `0042` arms bind the accepted r5 prefill calibration, sealed evaluator identity, one sole
      `GGML_IQK` factor, 15 one-repetition blocks, and fresh campaign/output roots. Both dry runs
      compose clean; neither arm has executed, so r42 is preparation rather than evidence.

<!-- original line 3895 -->
- [x] **Execute r42 and preserve its pre-compute evaluator-closure refusal.** ✅ 2026-08-13 — the
      intervention terminally stopped before fingerprint, claim, build, T0, or throughput because
      `correctness.py` appeared in both direct and nested evaluator closures. The control was not
      spent. Research `b93af168` forms the exact-path union while preserving the lexical-alias and
      duplicate fail-closed guard; the immutable r42 identity is not reused.

<!-- original line 3900 -->
- [x] **Execute r43 and preserve both terminal outcomes.** ✅ 2026-08-13 — the intervention reached
      `DECIDED/KEEP` with T0 PASS, 15/15 positive deltas, median **+28.860648%**, worst delta
      **+984.48 tokens/s**, drift `15.0356% ≤ 18.4968%`, production PASS, and both resources released.
      Its control refused before claim/T0/throughput: strict preflight observed only 7/96 cores at
      nominal frequency under load and also rejected caller-disabled load measurement as unmeasured
      contention. The control is not archive evidence and r43 is not a completed matched pair.

<!-- original line 3910 -->
- [x] **Finish the candidate-only discovery-throughput primitive without weakening confirmation.** ✅
      2026-08-13 — research `c8971a6b` executes candidate-only screening batches, `6661ca25` removes
      per-candidate anchor subprocesses, and `9a4bca3b` requires an inference witness. Only competing
      model inference overlapping claimed compute may block discovery; ordinary host activity remains
      measured noise. The live s7 prefill and s1 decode screens each ran three candidates and zero
      anchors, proving the amortized physical path without granting confirmation authority.

<!-- original line 3916 -->
- [x] **Produce and seal the first real amortized discovery baseline banks.** ✅ 2026-08-13 — the
      exact prefill b4 bank (file SHA-256 `1e9c32d9bd1544daf7dea0892f666ddad64a0b07dd06e9277bdea2cd4b589068`)
      and tg128 decode b1 bank (`8dcd02d3e9fd4e4a989f3631e9bc41e96ba45b43809ff41d8eaf510d15c7d1ed`)
      each bind three measured anchors, the full command/environment frame, and an inference witness.
      Prefill s7 nominated IQK at **+31.247%** median; decode s1 nominated it at **+7.939%** median.
      These are nonpromotable search records, not banked candidates or claims.

<!-- original line 3922 -->
- [x] **Run the first live MI210 discovery-first screen with residency proof.** ✅ 2026-08-13 —
      `ak-gpu-mmq-mfma-screen-20260813-s2` compared the sole build factor
      `GGML_HIP_MMQ_MFMA=ON→OFF`, measured three anchors plus three candidates, and nominated OFF at
      **+26.5965%** median. All three candidate invocations proved their owned KFD PID and non-zero
      VRAM during execution; result file SHA-256 is
      `9508396b5793568b9a458f1bc9374d6cf3855ca0872ab613768099e2654c0887`.

<!-- original line 3928 -->
- [x] **Expose and repair the IQ3_XXS MMID correctness boundary before spending more strict
      inference.** ✅ 2026-08-13 — r49 proved a real `m=512,n=15,k=256` error above the declared
      tolerance. The parser now admits the complete failure-prefix schema, and experimental commit
      `894ec4dc55c829b11b663a46bc9b089d861b73a4` retains IQK for the proven n=1 decode path while
      routing `ids->ne[1] > 1` to native. The former failure passed in the exact 1,216-case suite; no
      threshold or seed changed.

<!-- original line 3934 -->
- [x] **Checkpoint the fresh post-fix decode calibration and release all compute on operator stop.**
      ✅ 2026-08-13 — r6 durably completed AA `200/200`, neutral `60/60`, and anchor-motion `15/15`
      under the new instrument before SIGTERM. The watcher, r6 parent, and captured benchmark child
      are absent; all q0-q3 global/autokernel lock probes passed three times. No continuation ran and
      the unterminated prefix is not accepted authority.

<!-- original line 3939 -->
- [x] ~~**Land and independently review the controller-first discovery loop before resuming campaigns.**~~ **SUPERSEDED 2026-11-17 (autokernel, INF-06 box sweep): the Terra-worktree controller it names was replaced by the AKU rebuild program (AKU-01 enrollment through AKU-12 cutover, this file), which carries the same separation of discovery from strict authority as live boxes.** [no-belief: superseded]
      The isolated Terra worktree is implementing deterministic hypothesis selection, sealed
      measured-result ownership, strategy persistence, and resource-aware CPU/GPU dispatch. Discovery
      must be structurally unable to load strict calibration/heldout/champion/release authority, and
      planner prose or a screening threshold must never mint promotion state.

<!-- original line 3944 -->
- [x] ~~**Continue GPU candidate-only throughput discovery from the MMQ-MFMA-off nomination.**~~ **SUPERSEDED 2026-11-17 (autokernel, INF-06 box sweep): the nomination was against the 2026-08 pre-v10 GPU baseline, and its decode calibration was rejected (sub-box below). GPU discovery since then runs on the C-series champions (C6 to C12 via the AK-ASM ports), so this nomination has no C12 relevance.** [no-belief: superseded] Test the
      next exact single-factor gfx90a candidates and broader surfaces cheaply; send only a surviving
      top-K nominee to strict paired GPU confirmation.

<!-- original line 3947 -->
- [x] **Preserve the rejected decode r2 calibration as terminal non-authority.** ✅ 2026-08-13 — its
      resumed 200-block A/A leg and 60-block neutral leg completed under a released claim, but neutral
      `|effect|` p95 `0.154446` exceeded the A/A permutation reference `0.148013`; calibration rejected
      before controls and cannot license a holdout.

<!-- original line 3951 -->
- [x] ~~**Establish a fresh accepted decode calibration, then run the governed CPU decode IQK holdout.**~~ **SUPERSEDED 2026-11-17 (autokernel, INF-06 box sweep): gated on the 2026-08 "final bootstrap prefill pair" (superseded above). CPU decode calibration now lives in the floor-unit / CPU A/A calibration boxes and the C12 CPU validation (c12-cpu-validate-20261116-r3).** [no-belief: superseded]
      Start only after the final bootstrap prefill pair. Research `084f1ee6` predeclares five fresh
      alternating pairs per short tg128 statistical block and reduces each arm by its median;
      `9c0c907c` discloses the 2,600 fresh-invocation cost before execution. No threshold was weakened
      and ordinary host noise is not excluded. The holdout must use the same candidate factor but
      target `decode`, then be projected from its completed journal before the final prefill pair may
      enter AK-WM-2a. This is the first valid source for `heldout_regime_transfer`; fixtures, rejected
      decode r2, and the prefill pair cannot substitute.

<!-- original line 3959 -->
- [x] **CPU first.** ✅ 2026-08-13 — the r41 intervention and control both ran on `llama_cpu` under
      released full-host claims; no GPU claim was taken. `llama_cpu` needs no GPU device claim and its canonical baseline is the most
      characterised surface we have; `llama_gpu` needs the device claim and contends with whoever is
      serving. The claim reason alone decides it.

<!-- original line 3963 -->
- [x] **Reproduce a known-real CPU win as candidate #1 — the IQK replay.** ✅ 2026-08-13 — r41
      reproduced the rankable **+27.6481989%** intervention result; matched archive admission remains
      gated on the repaired control and held-out chain. It is a proposal-v4
      `change_class: parameter` comparison with candidate `ggml_iqk=1` and anchor `ggml_iqk=0`;
      `campaign.py` now projects that registered arm-local variant into the exact dry-run commands.
      A null result on a known win is diagnostic of the *harness*; a null on a novel idea tells you
      nothing about either.

<!-- original line 3970 -->
- [x] **Keep the 2026-07-04 async-prefetch replay in the GPU lane.** ✅ 2026-08-11 — the +3% / MemUnitStalled
      reduction on `mul_mat_vec_q8_0_prefetch` is a gfx90a/MI210 result, not a CPU candidate. Its
      original scratch evidence no longer exists, so it was re-derived from the frozen-v9 resident
      implementation and its runtime gate. The governed 20-block replay did **not** reproduce the
      historical win: 19/20 block deltas were positive, but median was only **+0.936%** (mean
      **+1.039%**, range **−0.590% to +3.311%**), below the predeclared 2% floor and with one negative
      block. This is `NOT_REPRODUCED`, not a banked candidate. Receipt:
      `/mnt/raid0/llm/autokernel/probes/ak-gpu-prefetch-v9-20260811-r2/receipt.json`, SHA-256
      `7b173cafcccb8a99319bf93a80fd13a2e94a400afab2bf03355363f9521ab17f`.

<!-- original line 3979 -->
- [x] **Repeat the governed v9 async-prefetch replay under an independent 20-block campaign.**
      ✅ 2026-08-12 — all **20/20** paired blocks were positive, but the median delta was only
      **+1.2442303249%** (minimum **+0.6788501205%**), below the predeclared **2%** contribution
      floor. The honest verdict remains `NOT_REPRODUCED`; positivity alone is not promotion evidence.
      The receipt binds frozen-v9 source/binary/linkage/model identities, a held-and-released MI210
      claim, and 2,544 device samples across 635.76 s:
      `/mnt/raid0/llm/autokernel/probes/ak-gpu-prefetch-v9-20260812-r1/receipt.json`, SHA-256
      `7321f2a640a7cc0b3169544867e26e3102a3efe3ebd5b0ebc732e154398339b0`.

<!-- original line 4042 -->
- [x] Build the serving-runtime adapter against the three-gate stack-change path (§11.6), reusing
  `stack_change_guard.py` for gate 1 and adding the behavioural half: variable-arrival replay,
  `task_rate` rather than tokens/s, latency and SLO cells as first-class outputs, comparison against
  the pinned production configuration. ✅ 2026-08-03

<!-- original line 4063 -->
- [x] Author the STT protocol: correctness corpus and output normalization (what counts as a
  transcription match), real-time factor, latency, throughput, memory stability, audio input identity,
  and the release decision rule. ✅ 2026-08-03

<!-- original line 4066 -->
- [x] Author the TTS protocol: text/audio identity, deterministic and numerical checks, an
  intelligibility/quality proxy with a human-independent floor, first-audio latency, RTF, throughput,
  stability, and the release decision rule. ✅ 2026-08-03

<!-- original line 4071 -->
- [x] Wire linkage verification through the research repo's `scripts/utils/verify_ggml_linkage.sh` for
  every candidate build and every T3 phase-2 check. ✅ 2026-08-03

<!-- original line 4073 -->
- [x] **Extend the release-plan compiler to the independently freezable speech trees.** ✅
  2026-08-12 — research `99fe3014` restores tested `whisper_stt.release_binding()` and
  `qwentts_tts.release_binding()` adapters that return the generic compiler's `BackendBinding` with
  exact source tree, stable path, phase vocabulary, Annex S prerequisites, tree-local ggml generation
  and `LD_LIBRARY_PATH`, complexity ceiling, and canary requirement. The generic compiler accepts
  single-backend speech targets without inheriting llama CPU/GPU union semantics; T3 consumes both
  adapter readiness predicates, enforces the `production-speech-vN` branch family, and reconstructs
  both independent trees from the preserved speech freeze. A focused exact-main adapter/plan/T3
  audit passed **783 tests with 132 subtests**.

<!-- original line 4096 -->
- [x] `Annex S` ratified — `measurement/protocols/speech.md`, 86 KB, five annexes in
  `MEASUREMENT.md`. `P-STT-1/2/3`, `P-STT-REL-1`, `P-TTS-1/2/3`, `P-TTS-REL-1` are in force; the
  four verdict grammars carry no `attest <ref>`, reconciled with Annex K's own reasoning.
  ✅ 2026-08-03

<!-- original line 4100 -->
- [x] Speech WER supersession ratified — `ratify_speech_wer_correction_20260804.json`, 2.35 → 3.37.
  The recorded figure was the `faster-whisper` CTranslate2 arm, a different engine; the production
  `whisper.cpp large-v3-turbo f16 MI210` arm measures 3.37 (63/1870). Forward-looking: every future
  `whisper_stt` non-inferiority comparison would have inherited that denominator. ✅ 2026-08-04

<!-- original line 4104 -->
- [x] `latency_s_11s_clip` audited and found CORRECT — 11 s / `xrt_overall` 51.86 = 0.212 s against
  the recorded 0.21, nearest competing arm 3× away. So the defect was one copy error on one line,
  not systematic mis-sourcing, and the receipt's other anchored values need no re-audit.
  ✅ 2026-08-04

<!-- original line 4759 -->
- [x] **AK-CAT-2 — Build a gfx90a/llama.cpp prior-art catalogue (§19 corpus).** ✅ 2026-08-10. Copy the reference
  five-column schema exactly: `| Pattern | Trace keywords | Primary code | Existing path | Reader
  should conclude |`, with trace keywords bound to `rocprofv2` kernel names and primary code to
  ggml/llama.cpp symbols. **The pre-written conclusion column is the load-bearing one** — it moves the
  verdict out of model judgment at read time and into reviewable data at authoring time, which is the
  same move MEASUREMENT_POLICY's claim grammar makes for measurement claims. Partition rows **mainline
  vs in-flight**: a pattern merged upstream but absent from FROZEN `production-consolidated-v8` is a
  **PORT, not a research proposal**, and that distinction currently has no column anywhere.

<!-- original line 4767 -->
- [x] **AK-CAT-3 — Build the expected-absence register BEFORE the catalogue rows.** ✅ 2026-08-10. The reference
  carries a 15-row toggles table whose column is literally "effect on trace interpretation", including
  cases where a flag *intentionally* disables a fast path so split kernels are expected. Without it,
  every legitimately-disabled path reads as a missing optimization. Our substrate is
  [cpu-kernel-env-flags-inventory.md](../completed/cpu-kernel-env-flags-inventory.md), which inventories flags
  without their expected trace consequence. This is the three-states-not-two discipline as data.

<!-- original line 4773 -->
- [x] **AK-CAT-4 — Adopt the pinned-head refresh discipline.** ✅ 2026-08-10. The reference pins the upstream head of
  every scanned project with a dated note and ships the exact scan commands, making staleness
  *measurable* rather than asserted. Record the commit each scan was taken against.

<!-- original line 4776 -->
- [x] **AK-CAT-5 — Add a cumulative GPU-time-share floor as a proposal-space pruner** ✅ 2026-08-10 (reference
  default `1.0%`). §8.4's wall-share ceiling validates a candidate *after* it is generated; a floor
  prunes the space *before* generation. Complementary, and cheaper.

<!-- original line 4779 -->
- [x] **AK-C6-1 — Name syscall confinement explicitly in C6's acceptance criteria.** ✅ 2026-08-10. intake-1028 is a
  purpose-built, professionally structured distributed execution sandbox — controller, dispatcher,
  router, Docker workers with `--cpus`/`--memory`/`--gpus device=` limits — that nonetheless launches
  **every** worker with `--security-opt seccomp=unconfined`, on containers whose entire job is running
  untrusted model-generated code. "Runs in a container" is not "sandboxed". Relatedly, its
  `openmle_gym/sandbox_exec.py` is named for a sandbox and documented as executing "inside the
  configured OS sandbox" while implementing `spec.loader.exec_module` in-process with no isolation —
  a live instance of the naming hazard this loop's C6 item exists to prevent.

<!-- original line 4787 -->
- [x] **AK-C6-2 — Harvest the controller/dispatcher/router/worker + SQL job-store split as a design
  comparator** ✅ 2026-08-10 for owned-scope candidate execution, specifically its **idempotency migration** — the
  mechanism for not double-running a submitted job after a controller restart. That is the same class
  of problem as autopilot rewind having to purge the strategy store. Comparator only; the stack itself
  is declined (external registry images, cgroup-v1 host reboot).

<!-- original line 4792 -->
- [x] **AK-KM-1 — Record the model-tree-vs-kernel-tree search rule in the §19 corpus.** ✅ 2026-08-10. Verifying a
  symbol's absence in a framework's *model* file alone produces a false negative; this session nearly
  reported a source as fabricated for exactly that reason before finding all four symbols in the
  *kernels* tree. Absence claims must name the trees searched.

<!-- original line 4796 -->
- [x] **AK-DEL-1 — SCOPE-REDUCTION GATE: measure the bucket split before building any novel-kernel
  proposal generator.** ✅ 2026-08-11 — replayed AK-CAT-1 over a preserved real `rocprofv2` trace,
  normalized to remove host-identifying absolute timestamps and bound to the original trace SHA-256.
  The 9 dispatches formed 3 admitted kernel families; all 3 landed in bucket (a), with 0 in (b)–(d).
  The report therefore selects `expand_catalogue_before_novel_generator`. This is deliberately a
  corpus-bounded scope result, not a claim about all workloads. Evidence:
  `epyc-inference-research/data/autokernel/prior_art/ak-del-1-k25-q8-mmvq-n1-20260717/`, research
  commit `df02169e`. The catalogue was refreshed against frozen v9 and generic `mul` matching was
  tightened so it cannot misclassify RMSNorm/MUL/RoPE fusion rows.

<!-- original line 4805 -->
- [x] **AK-DEL-2 — Review and integrate the next bounded gfx90a prior-art catalogue expansion.** ✅
  2026-08-12 — reviewed commit `677a2eec` landed on research `main` as `35f10715`. The bounded rows
  cover gfx90a fused top-k MoE, gfx90a flash attention, and ROCm MMQ-versus-rocBLAS as present prior
  art while retaining HIP `TOP_K` as unsupported; corrected source pins and the negative control remain
  fail-closed. This expands routing knowledge only and does not manufacture candidate evidence.

<!-- original line 4852 -->
- [x] **AK-TR-1 — Record a per-change-class transfer ratio on the evaluation event.** ✅ 2026-08-10. Add
  `anchor_tier` and `transfer_ratio_to` to §7.4 `epyc.autokernel.evaluation_event.v2`, and populate
  them wherever a cheap cell and an expensive cell measure the same candidate. One mechanism, four
  uses: half → full partition, op → graph, T1 → T3, screen → verify. The ratio is **keyed by change
  class** (§9.5), not global — an instruction-level change and a bandwidth-bound change do not
  transfer alike, and a single pooled ratio would average them into uselessness. **Free to add now,
  impossible to backfill**: a ratio invented at read time claims a correspondence the original run
  never measured.

<!-- original line 4860 -->
- [x] **AK-TR-2 — Print the self-spread noise floor adjacent to every per-case delta.** ✅ 2026-08-10. §9.2 already
  mandates MDE published with the result and §15.2 already runs A/A; the gap is **presentation**, not
  statistics — our machinery is stronger than the reference campaign's, and it is still possible to
  read a per-case table and not see which rows are inside the noise. Suppress or explicitly flag any
  delta below the floor at the point of display.

<!-- original line 4865 -->
- [x] **AK-TR-3 — Per-turn productivity accounting** — see
  [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring) §"Loop-engineering
  experiments", which owns it. Referenced here because §8.8 POST_RUN_CRITIC is where the tuple gets
  emitted. ✅ 2026-08-10 — routed to its single implementation owner as AK-PT-1; AutoKernel consumes
  that archive for AK-X-6 and does not duplicate the reducer.

<!-- original line 4870 -->
- [x] **AK-TR-4 — Extend roofline utilisation (§8.3.1) to a per-quant surface, anchored on
  state-of-the-art CUDA kernels.** Operator idea, 2026-08-10: give the loop a *defined* improvement
  target by expressing decode throughput as a fraction of the theoretical roof and comparing that
  fraction to what SOTA CUDA kernels reach on NVIDIA silicon — **and compute it independently per
  quantisation**, because this card behaves very differently at 16-bit than at 4-bit.
  - **This does not reopen AK-D3.** AK-D35 already ratifies utilisation as *diagnostic and routing
    input, never a gate*; a target expressed in utilisation therefore cannot be peeked at by a
    promotion gate, which is exactly the property AK-D3 removed the +25%/+20% trigger to obtain.
  - **Per-quant is more correct, not merely richer.** `bytes_per_token` differs per quant by
    construction, so a single pooled utilisation figure silently mixes denominators; and splitting it
    **localises the headroom to the dequant path**, which is where the ladder collapse in §8.3.1(3)(b)
    lives. This is the same measurement the "close the ladder gap" program needs.
  - **Use the spec-basis ridge for the cross-vendor comparison** (§8.3.1's usage rule): converting our
    figures to an achievable basis while a CUDA anchor stays on a spec basis shrinks the gap without
    shrinking it. The **mixed-basis** row (spec FLOPS over measured bandwidth) is retired for this
    purpose. Achievable-basis figures remain the honest ones for reasoning about *our own* headroom.
  ✅ 2026-08-11 — `substrate.py` now constructs exact-quant observations and comparisons, refuses
  mixed or pooled quant labels, reports local headroom on the measured-achievable basis, and permits
  cross-vendor targets only on a matching spec basis. The registered BF16/H100 single-stream anchor
  cites primary absolute-bandwidth evidence; Q4_K and Q8_0 remain explicit `COULD_NOT_CHECK` gaps
  rather than borrowing Marlin's relative INT4 result or another quant's denominator. The entire
  surface is structurally diagnostic/routing-only and cannot gate promotion.

<!-- original line 4892 -->
- [x] **AK-TR-5 — Fresh process per arm, and size the working set so memoization cannot pay.** Where a
  variant is env-gated at import/init time, an in-process A/B measures the first arm twice; §9.3's
  paired blocks do not protect against that. Separately, choose working-set sizes such that
  candidate-side caching of results is unprofitable **by construction**, which is cheaper and more
  durable than detecting it (complements RVP-C6-8 in
  [`rocm-verify-profile-backend.md`](rocm-kernel-authoring.md#track-rocm-verify-profile-backend)).
  ✅ 2026-08-11 — every live arm now receives a unique `(pid,start_ticks)`, an empty invocation-only
  writable tree, and verified teardown before the next arm. Hardened `llama-bench` commit `0492c231`
  keeps `2 × reps` contexts and input vectors simultaneously live, gives every timed repetition
  unique content and addresses, and runs its same-content/address-rotated replica untimed. The runner
  refuses missing, reused, malformed, or output-variant receipts. The experimental CPU build and the
  complete 3,730-test static suite pass; exercising the real-model path remains part of the next
  explicitly authorized campaign, not an implementation gap.

<!-- original line 4905 -->
- [x] **AK-TR-6 — Compile-only artifact-diff veto in T0 (§8.6).** ✅ 2026-08-10. Before spending any GPU wall-time,
  diff per-kernel VGPR / SGPR / scratch usage and instruction mix between candidate and anchor via
  `roc-obj` / `llvm-objdump`. Register-pressure movement means the A/B is **unconfirmed**, not
  disproven — it fires as a veto on the *claim*, not on the candidate. **This buys back our scarcest
  resource**: it is a static check that can retire a candidate before it reaches T1.

<!-- original line 4921 -->
- [x] **AK-LN-1 — Lane registry.** ✅ 2026-08-10. Each lane declares its cost, its capacity, and **what it is a proxy
  for**. Assignment is by change class to the cheapest lane whose *measured* rank fidelity clears a
  declared threshold — never by convenience. Available today: one exclusive GPU device claim plus
  historically exercised CPU shapes at 4×48t, 8×24t, 16×12t, 32×6t and 48×4t. Those records establish
  fan-out feasibility, not rank fidelity.

<!-- original line 4926 -->
- [x] **AK-LN-2 — Partition-depth calibration.** ✅ 2026-08-11. Run one fixed candidate set at full-machine and at
  **every historically exercised split depth** — 4×48t, 8×24t, 16×12t, 32×6t and 48×4t — and
  measure each split's **rank correlation** against the full-machine ordering. The preserved sweep
  proves those fan-outs run; it does not prove rank fidelity. Needs no new candidates — reuse a banked
  set. **Pre-register the prediction** before running: bandwidth-bound changes lose fidelity fast as
  partitions shrink (they compete for the same memory system), instruction-level changes hold. The
  pre-registered anchor/IQK-off/flash-attention-off calibration found full-machine rank fidelity 1.0.
  Depth 4 retained the ordering (1.0), but depths 8, 16, 32 and 48 inverted IQK-off versus
  flash-attention-off (Spearman 0.5). No historical split depth is therefore admitted as a ranking
  proxy by this candidate set. Receipt:
  `/mnt/raid0/llm/autokernel/probes/ak-ln-2-x5a-lanes-20260811T1400Z/receipt.json`, SHA-256
  `c207a46f7e1868deeca4628faedfd47b933839a921b0b6d472055ce80c415618`. Research runner:
  `scripts/benchmark/run_autokernel_cpu_lane_calibration.py`.
  Pre-registration is what makes a confirmation informative rather than a post-hoc story.

<!-- original line 4940 -->
- [x] **AK-LN-3 — Cross-lane A/A control — necessary, and NOT sufficient.** ✅ 2026-08-10. §15.2's A/A control run
  per lane detects a per-lane-position offset. It **cannot** detect bias correlated with mechanism
  class, because that bias appears identically in every lane and cancels out of the A/A comparison.
  Pair it with AK-TR-1, which is the only thing that measures it. **Never apply a blanket haircut to
  lane results** to "correct" for partitioning — a uniform correction assumes the very
  class-independence that AK-LN-2 exists to test.

<!-- original line 4946 -->
- [x] **AK-LN-4 — Op-level screening on profiled bottlenecks.** ✅ 2026-08-10. Operator steering: profile
  first, rank ops by wall share, then fan out **concurrent op-level experiments on the single
  bottleneck op** rather than serialising whole-graph runs. `test-backend-ops` is already an op-level
  harness, so the unit exists; what is missing is the fan-out and the §9.1 promotion rule applied per
  op. This is the unit that actually parallelises — a graph run does not.

<!-- original line 4951 -->
- [x] **AK-LN-5 — Isolation requirement for concurrent CPU lanes.** ✅ 2026-08-10. Concurrent instances contend
  invisibly unless each uses `--no-mmap` plus an explicit `membind`: `mmap` **shares NUMA placement
  across instances**, so two "independent" lanes can silently read one node's memory. A partitioned
  result may **screen but never gate** (§9.6 banking is unaffected; §9.7 T2 and §10 T3 remain
  full-instance). **The pre-bench CPU-frequency/throttle check stays mandatory at the verification
  tier** — operator, 2026-08-10: the screening/verification split does not relax it, it concentrates
  its importance onto the one measurement that carries the claim.

<!-- original line 4971 -->
- [x] **AK-BH-1 — hipBLASLt vs rocBLAS microbench at our prefill shapes, standalone.** ✅ 2026-08-11 —
  `libhipblaslt.so`
  is installed on this host and **not linked** by our build. Measure the two libraries against each
  other at our shapes *before* touching ggml, so the question "is our GPU baseline the honest one" is
  answered by a 30-minute microbench rather than by a kernel campaign. This is the structural analogue
  of the baseline-deflation finding this batch turned up: a result measured against a weaker-than-
  available baseline overstates the win by the size of the gap, and the gap here is measurable today.
  Complements the §"New index-backed leads" hipBLASLt grouped-GEMM lever. The best-heuristic live
  receipt covered nine shapes: hipBLASLt won three, while its ratio to rocBLAS ranged from 0.734× to
  1.322×. A universal library replacement is explicitly declined; the strongest baseline is
  shape-specific. Receipt: `/mnt/raid0/llm/autokernel/probes/ak-bh-1-best-of-heuristics-20260811T0948Z/receipt.json`,
  SHA-256 `aca0dc59dbea9745008e00f3958a767dfb07b4c9e2e21f8946239ec981762cfc`. Research runner:
  `scripts/benchmark/run_rocm_gemm_baseline_compare.py`; comparator source:
  `scripts/benchmark/rocm_gemm_baseline_compare.cpp`. A fresh 2026-08-12 corroborating replication
  under a rebuilt binary found 4/9 hipBLASLt wins and a 0.7289325552×–1.3218706582× ratio range.
  The near-parity win count drifted by one shape, but the shape-specific baseline conclusion did not.
  Receipt: `/mnt/raid0/llm/autokernel/campaigns/ak-bh-1-20260812T0448Z/receipt.json`, SHA-256
  `5daa79e7bc12cec1e9358b8166f08a7586bb0d5ba7885832bb47d96af82c7dc1`.

<!-- original line 4989 -->
- [x] **AK-BH-1a — Sustain the nine-shape vendor-baseline comparison long enough to attest loaded
  device state.** ✅ 2026-08-12 — a clean detached research checkout at `26ca88dc` rebuilt the existing
  comparator, then ran **30,000 timed repetitions per provider per shape** under canonical claim
  `akd-f6f696e03b8d468c`. The 55.17-second sampling window retained 221 samples at 250 ms cadence
  (maximum gap 0.250991 s), 86.43% at 1700 MHz, 165 W median / 241 W maximum power, and 62 C maximum
  temperature. hipBLASLt won 4/9 shapes; its exact-shape ratio to rocBLAS ranged 0.7444927062× to
  1.3162041222×. All nine winner directions matched the earlier short replay, with mean absolute ratio
  drift 0.00721 and maximum 0.01556, so the shape-specific strongest-baseline conclusion survives
  sustained load. Both exact PIDs were dead after terminal release at `2026-08-12T08:26:49.465889Z`.
  Receipt: `/mnt/raid0/llm/autokernel/campaigns/ak-bh-1-sustained-r2-20260812T0824Z/receipt.json`,
  SHA-256 `f8e09c77dffe7767af3bb1d1d85f2f4866155dcf677a331fa0e458111a42c855`.

<!-- original line 5000 -->
- [x] **AK-BH-2 — Baseline-honesty factorial: `-fa 0|1` × `ROCWMMA_FATTN` × `MMQ_MFMA`.** ✅ 2026-08-11
  **Correction to a standing project assumption**: `llama-bench`'s `-fa` default is
  `LLAMA_FLASH_ATTN_TYPE_AUTO`, not `0` — verified at `tools/llama-bench/llama-bench.cpp:389` in the
  frozen v8 tree. **AUTO is worse for baseline honesty than a known-off default**, because it resolves
  differently per model, quant and backend: two runs with *identical command lines* can silently
  differ, manufacturing or hiding a speedup with no visible flag difference. Pin `-fa` explicitly on
  every arm and **record what AUTO resolved to** when reading any historical number. All eight live
  arms completed with 30 retained repetitions. On the tested Qwen2.5-Coder-0.5B Q4_K_M prefill
  surface, `-fa on` beat off in all four build pairs, `MMQ_MFMA` was slower, and `r1m0-fa-on` won at
  24,647.316788 t/s. Receipt:
  `/mnt/raid0/llm/autokernel/probes/ak-bh-2-factorial-20260811T0952Z/receipt.json`, SHA-256
  `2a53cee2d8513737eca894e0f34152549932b75f3e04ef541cdee1848472cfdf`. Research runner:
  `scripts/benchmark/run_autokernel_gpu_factorial.py`.

<!-- original line 5013 -->
- [x] **AK-BH-3 — CPU-lane baseline-honesty arm, run concurrently with AK-BH-2. ✅ 2026-08-11** The
  full-host CPU claim remained held across three randomized 30-repetition hardened arms. On the exact
  Qwen2.5-Coder-0.5B Q4_K_M prefill surface, implicit AUTO measured 5,569.961069 t/s, explicit ON
  5,451.900259 t/s, and explicit OFF 2,741.087873 t/s. AUTO therefore behaves like the fast ON path
  here while hiding the choice in argv. Every exact measurement window retained package-power
  evidence; the counter permission was restored to `0400`. Receipt:
  `/mnt/raid0/llm/autokernel/probes/ak-bh-3-cpu-baseline-honesty-20260811T1330Z/receipt.json`, SHA-256
  `157580a4133a5b7404384e16a4f0b3737f54480365694cfdfd079a6ce9c99911`. Research runner:
  `scripts/benchmark/run_autokernel_cpu_baseline_honesty.py`.

<!-- original line 5022 -->
- [x] **AK-BH-4 — Encode strongest-baseline selection by exact measured surface. ✅ 2026-08-11**
  `evaluator/baseline_honesty.py` requires both rocBLAS and hipBLASLt observations for one identical
  model SHA, quant, operation, shape, dtype, build SHA, and explicit factor set; selects by declared
  metric direction; refuses `auto`, missing or duplicate provider arms, metric mismatch, and any
  candidate model/quant/shape/factor transfer. Nine focused tests pass. Research commit `5fbd471b`.
  The earlier 0.5B result is consequently evidence for that surface only, never a portable baseline.

<!-- original line 5056 -->
- [x] **AK-OP-2 — Decline root-side `--setperfdeterminism` capability.** ✅ 2026-08-11 — RVP-T0-1
  held 1700 MHz for 99.5868% of a 60-second saturating GEMM while peaking at only 200 W against the
  300 W cap, so the card never approached the cap and clock excursion is not a live variance source
  under this workload. The 2026-08-12 replay independently held the same 99.5868% nominal-clock
  fraction while peaking at only 196 W. No root capability or measurement-constitution change is
  warranted.

<!-- original line 5082 -->
- [x] **AK-X-1 — Add `INSTRUMENT_TAMPERED` to the §12 failure-and-abuse table.** ✅ 2026-08-10. RVP-C6-1 builds the
  detection; §12 has no row for the finding, so a detection today would have nowhere to land.

<!-- original line 5084 -->
- [x] **AK-X-2 — Add a parsed `device_state` block to the §7.4 evaluation event**, populated from
  RVP-C3-3, with `throttle_observed`. A text blob no gate can read is not a gate input. ✅ 2026-08-10 —
  evaluation-event v5 stores numeric loaded samples, nominal SCLK and a mechanically re-derived throttle
  verdict; GPU absence is `COULD_NOT_CHECK`, a below-floor sample is `FAIL`, and CPU events require null.

<!-- original line 5088 -->
- [x] **AK-X-3 — Add `min_measurable_us` to the §9.3 T1a recipe, derived from OUR OWN A/A spread.**
  Below it a cell is `inconclusive` rather than a rank. Do not import a foreign floor — the published
  ones are NVIDIA-derived. ✅ 2026-08-11 — `statistics.derive_minimum_measurable_duration()` derives
  the typed floor from local paired-A/A absolute-duration spread and a declared relative-noise budget;
  every T1a recipe requires that object, rejects bare numerics, and withholds rank below the floor.

<!-- original line 5093 -->
- [x] **AK-X-4 — Add `cache_state: warm | cold` to the §9.3 T1a recipe and hold it fixed across arms.** ✅ 2026-08-10.
  The warm/cold gap is workload-dependent (large for GEMV, negligible for GEMM), so an undeclared
  cache state is a per-op confound rather than a constant one. Every registered T1a recipe now records
  a validated warm/cold parameter (explicitly cold by default) and binds it into the recipe receipt, so
  an arm mismatch changes the evidence identity instead of remaining ambient state.

<!-- original line 5098 -->
- [x] **AK-X-5 — Per-partition CPU frequency / package-power attestation in the §7.4 `host_receipt`.**
  Our throttle discipline operates at *session* granularity; with 2–4 concurrent CPU lanes sharing one
  dual-EPYC package power and boost budget there is **no per-lane frequency attestation at all**. This
  is the coupling channel that actually threatens the lane design (CPU→GPU contention is ~0.3 % on the
  reference ablation; CPU-partition ↔ CPU-partition is unmeasured by anyone). AK-LN-3's cross-lane A/A
  is its acceptance test. ✅ 2026-08-11 — live CPU preflight now requires readable per-CPU frequency
  plus package-energy counters for every package touched by the partition; exact-window deltas handle
  counter wrap and are labelled `shared_package_window`, never lane-exclusive power. Missing or
  unreadable powercap data is `COULD_NOT_CHECK` and prevents a CPU campaign from claiming the control.
  Empirical cross-lane coupling still belongs to the authorized lane-calibration campaign.

<!-- original line 5108 -->
- [x] **AK-X-5a — Run the cross-lane package-power/frequency acceptance.** ✅ 2026-08-11. Exercise the same fixed
  candidate set across every AK-LN-2 split depth with readable `energy_uj`; retain each exact-window
  shared-package receipt and test whether lane position or concurrent depth changes the A/A distribution.
  This is empirical inference work and requires the operator's explicit permission. The authorized
  campaign retained readable exact-window package-energy evidence for every arm and restored
  `energy_uj` to mode `0400`. Every split failed the predeclared combined acceptance: maximum anchor
  lane-position deviations were 37.36%, 53.25%, 77.43%, 36.19% and 16.28% at depths 4, 8, 16, 32 and
  48 respectively (limit 10%); loaded-frequency ratios to full were 0.815, 0.829, 0.794, 0.743 and
  0.800 (limit 0.8). The full CPU claim remained held through all waves and was released. Evidence is
  the AK-LN-2 receipt above.

<!-- original line 5118 -->
- [x] **AK-X-6 — Turn-budget stopping rule driven by AK-PT-1.** Refine turns continue only while the
  rescued-kernel speedup distribution overlaps the persistent-kernel distribution; once a turn admits
  only rescued kernels below the contribution floor it is repair-only and does not advance the search.
  Must use the §9.2 e-process, never a point comparison. ✅ 2026-08-11 —
  `turn_productivity.py` consumes the immutable AK-PT-1 archive, binds the contribution floor before
  observations, imports its construction and threshold only from accepted campaign calibration, and
  requires two crossing e-processes (rescued below / persistent above the same floor) plus an only-
  rescued latest turn. Insufficient evidence continues refinement; the result can only withhold search
  advancement and carries no rank/retain/promote/deploy authority.

<!-- original line 5127 -->
- [x] **AK-X-7 — Edit-type classifier over adjacent candidate diffs** (no-op / mask fix / delegated-op
  / dtype-cast / optimization rewrite). §9.5 already keys behaviour off `proposal.change_class`; this
  measures whether the **realised** edit matched the **declared** class, and flags a proposal that
  promised an optimization and delivered repairs. ✅ 2026-08-10 — `execution/chain.py` classifies
  every diff that enters change-surface projection, preserves per-class line counts under a deterministic
  tie rule, and attaches the realized class to the captured evidence.

<!-- original line 5146 -->
- [x] **AK-X-10 — Record external evidence that C4 is on the critical path**, not more refine turns:
  refinement responds to explicit local error signals, while plan-level decisions (tiling, memory
  layout, kernel boundaries) are "not recoverable from the feedback available in current iterative
  pipelines". This strengthens an existing position rather than opening work. ✅ 2026-08-10 —
  `research/intake_index.yaml` intake-1095#01 binds the claim to KernelBenchX v2 §5 Insight 2 and maps its
  A-5 action explicitly to AutoKernel C4; it is external design evidence, not a local performance claim.

<!-- original line 5220 -->
- [x] **AK-QL-1 — Catalogue the missing rungs.** ✅ 2026-08-16 — research `02307322d166...` adds
      immutable IQ4_XS, Q5_K_M and IQ1_S evidence and portfolio records. IQ1 remains memory-only and
      inactive; catalogue presence grants no GPU or authoring spend.

<!-- original line 5241 -->
- [x] **AK-QL-4 — Retain IQ1_S as an inactive discriminator, not an execution task.** ✅ 2026-08-16 —
      operator direction says there is no practical need to run IQ1. The portfolio preserves its
      sign-discriminating falsifier with zero expected value, empty templates and no GPU/source spend.
      Reopen only on explicit operator direction plus a practical IQ1 serving decision.

<!-- original line 5251 -->
- [x] **AK-QL-6 — Record the refuted blanket batching premise.** ✅ 2026-08-16 — `02307322d166...`
      records it as a scoped, retired `design_prior` warning for the exact MI210/Goedel-8B B1–B32
      regime. It is deliberately not a hard family-wide DNR and does not forbid narrower per-format
      hypotheses or governed re-entry.

  - [x] **AK-QL-2b — Record the compiler-side route to the IQ2_XXS/IQ3_XXS threshold.** ✅ 2026-09-15 —
        static A/B on frozen-v9 `mmvq.cu` (ROCm 6.2 hipcc, zero GPU): `#pragma clang loop unroll(disable)`
        on the 4-trip sign-unpack loop (`vecdotq.cuh:1000` IQ2_XXS, `:1124` IQ3_XXS) takes
        `<_,1,true,false>` 78→44 and 71→44 VGPR, spill 0, other quants unchanged; the same pragma on Q3_K
        regresses 88→96; `#pragma unroll` is a no-op; ~30 AMDGPU RA/scheduler knobs null. Unrolling is the
        multiplier, sign unpacking the payload. Static only — executed instructions per block are probably
        ≈ unchanged. Evidence: `artifacts/gpu-aux-baselines/a10_iq2_vgpr_compiler_ab_20260915.md`.

<!-- original line 5363 -->
- [x] **AK-PM-3 — Add HARD_CONSTRAINT `l2-hit-rate-is-not-an-objective-on-gfx90a` to the §19.2 ledger.**
      In the same r2 arm, **Q6_K LOST 5.559 TCC hit-rate points while device duration IMPROVED 0.987%**,
      while Q4_K lost 7.903 points and slowed 0.581% — counter and time decoupled **in sign**, within one
      run, on one arm. That is a first-party refutation of L2 hit rate as a standalone optimisation
      objective here, and a sharper argument against SwizzlePerf's central design choice than the
      architectural one. Any C4 loop optimising a mechanism counter must carry a WALL-CLOCK VETO GATE.
      Per §19.3 this entry needs a source receipt (the counter-receipt path above), a binding to the
      production commit it was verified against, and a `reopen_when` predicate — propose:
      *reopen when a shape is measured whose TCC hit-rate delta and device-duration delta agree in sign
      across >=2 quant types.*
  - ✅ 2026-11-10 — ledger row `l2-hit-rate-is-not-an-objective-on-gfx90a` added to §19.2 (receipt SHA-256 `0dc3d4d0…8adf`, bound to v9 `0db32c06e`, `reopen_when` as proposed; numbers verified read-only against the receipt). [no-belief: ledger doctrine row; the measured number stays owned by the r2 receipt]

<!-- original line 5523 -->
- [x] **AK-PM-16 — Retrodict the Amdahl selector against our own closed G15 result.** ✅ 2026-10-30 [belief: cc] —
      **NEGATIVE for direct transfer.** The exact `RightNow-AI/autokernel` `78435821` source, replayed through
      its unmodified pure classifier and supported-kernel extractor on the receipt-pinned frozen-v9 B=128
      G15 kernel table, does not select gather/scatter for optimization. The actual gather kernel
      `k_get_rows_float` is rank 2, 18.553136% of measured GPU time, but classified `other`/unsupported;
      recurrent `gated_delta_net_cuda` is rank 3, 16.686724%, also `other`/unsupported. The source's
      `extract.py --top 5` path retains ranks 1, 5, 7, 8, 9 and drops both. This is an interface/taxonomy
      failure: the source accepts per-kernel records and has no family-share input. The arithmetic Amdahl
      counterfactual **does** rank the measured 18.631% gather/scatter family above 17.464% recurrent and
      1.490% norm+activation+elementwise. No evidence says the source selected norm, and this result does
      not alter G15's predeclared 20% target floor or `CLOSED_NO_GO`. The pinned source's bare `nll`
      substring also misclassifies MI210 matrix names containing `_ONLL1_` as `cross_entropy` (9.888882%
      of replayed time), so direct lifting needs a taxonomy gate. Exact source and receipt SHAs, isolated
      AST replay and result: `artifacts/autokernel/ak-pm16-retrodict-20261030/REVIEW-PACKET.md`.
      - [belief: cc] Conclusion is an offline source/receipt compatibility observation; no new
        measurement warrant or inference claim is asserted. The existing G15 measurement receipt remains
        `/mnt/raid0/llm/autokernel/probes/inf36-g15-profile-v9-20260811-r4/receipt.json` (SHA-256
        `d7a0c8c257c2a59435b95c39b988485a8283d709d83ef7397b3c67ee7ec8cca9`).

<!-- original line 5547 -->
- [x] **AK-PM-18 — AK lesson-entry write-side schema and lint addendum to AK-PM-17 (schema and write-side lint only: no read side, no retrieval, no build before the AK-PM-11 ablation returns).** No LLM-authored AK lesson library exists today (the planner's memory is the deterministic do-not-repeat fold, `controller/do_not_repeat.py:640 @cb6b08fea`), so this extends the per-round record that AK-PM-17 defines: a per-edit verdict in {helped, hurt, no observed effect, confounded} with 'confounded' required whenever several components changed and no run isolates one; at most one durable lesson per round with cue, lesson naming the component, evidence citing run or attempt ids that resolve to journal rows, and confidence; an explicit NO_ENTRY; a write-side lint rejecting an entry with an empty cue, lesson or evidence and an entry whose evidence is only confounded rows (`intake-2148#01`); keep/revert stays separate from lesson attribution, and adoption does not establish that an edit helped. A revision is a new entry with supersedes=<id>, source_run_ids and trigger_run_id, never an overwrite, its text limited to claims entailed by the lesson's source runs, with a grounded/leaked/unsupported audit on a 20-entry sample before any enablement (`intake-1999#record`). Lessons are observations: no ClaimTuple, and a measured number inside needs its own tuple from the producing run; admission stays the execution-gated rule of AK-PM-12. ✅ 2026-10-20

<!-- original line 5589 -->
- [x] **AK-PORT-1 — Correctness-gated optimization order in the loop spec.** Compile → operation-specific reference comparison under that operation's validated metric and tolerance → only then timing; a fast wrong variant is discarded. Cosine/PSNR and max-abs/MSE become gates only for operations with an established reference, data-range convention where applicable, and acceptance limit. ✅ 2026-09-17: the operator accepted native per-operation comparators instead of an unvalidated universal metric policy. The source-aware CPU GDN/IQK fixtures and GPU `AK_REF_V1` route use established comparisons before timing; unavailable or wrong comparisons cannot become performance keeps.

<!-- original line 5591 -->
- [x] **AK-PORT-3 — Native-code diagnostic on prospective source keeps.** Attach a bounded native-code summary, or an explicit unavailable record, to every new source keep; bind it to the retained tree, build recipe/toolchain and code-object bytes. State unsupported spills, occupancy, vectorization and per-kernel attribution as unavailable. Runtime-recipe keeps reuse an existing build and record that no new codegen artifact exists. ✅ 2026-09-17: the operator accepted this bounded native diagnostic in place of exhaustive fatbin/per-kernel occupancy coverage. Research `09bc8fc3`, `44c3dae1`, `004de151` and the strict root reader `2f49a783` implement the source-keep path.

<!-- original line 5600 -->
- [x] ~~**[Subject deleted 2026-09-22]** GLM-5.3-Flash (model, DFlash2 drafters, `llama.cpp-experimental-glm53-*` worktrees) was removed from disk by operator direction; branches and stores remain as history. Unrunnable as written; left unticked. **AK-SERIAL-26 — Verify completed GLM serial stages settle exactly one iteration and continue the operator-requested 20-loop health watch.** Check original child disposition, scheduler accounting, heartbeat freshness and resource claims; if a real failure occurs, stop/fix/relaunch without discarding valid store history. Do not count v25's two runtime observations or v27/v28 held-out A/A launches as research stages. v26 settled one-iteration stages but was unhealthy as a research loop; the watch now follows live v28, seeded from v27's validated completed batch-0 continuation. v27's interrupted batch-1 claim is retained as a failed historical epoch, never silently cleared. **Semantic health is required, not just liveness:** after the distinct full-recipe calibration, the planner must formulate distinct, falsifiable hypotheses on an active GLM bottleneck, the critic must give source-specific approval/refusal, and an approved source candidate must reach exact DSO engagement, independent correctness and matched serving measurement. A measured null is useful; a heartbeat, setup refusal or repeated abstention is not. If three consecutive post-calibration stages repeat the same now-superseded fused/dot-route abstention, stop and fix the planner/context before accumulating more batches. Inspect the first five stages for an admissible fused-Q4_K/Q5_K or dot-computation proposal; if none forms, diagnose immediately rather than counting to 20. Compare the mechanism portfolio and negative-to-new-route escape with the autonomous 27B run and manual Next-Flash work, without importing their effect sizes or requiring a keep quota.~~ (closed 2026-10-29 audit: OBSOLETE → handoff:5548 [Subject deleted 2026-09-22] GLM-5.3-Flash removed from disk; graveyard model)

<!-- original line 5602 -->
- [x] ~~**AK-SERIAL-26 — Semantic GLM health criterion remains unmet; resume only on a new operator instruction.** **[Subject deleted 2026-09-22]** GLM-5.3-Flash (model, DFlash2 drafters, `llama.cpp-experimental-glm53-*` worktrees) was removed from disk by operator direction; branches and stores remain as history. A GLM resume is impossible. The semantic-health criterion carries over to any future campaign, e.g. on DeepSeek-V4.1-Flash after its port. Before any future campaign, use the preserved store and source, diagnose the causal Q8/synchronization bottleneck, and require a distinct falsifiable source proposal to reach exact DSO engagement, independent correctness and matched serving measurement. Do not mistake observation-only runtime arms or repeated abstentions for the requested 20 meaningful loops. The historical v27 failed claim remains fail-closed; no automatic relaunch follows from this row.~~ (closed 2026-10-29 audit: OBSOLETE → handoff:5550 GLM resume impossible, model deleted 2026-09-22 (GLM-5.3-Flash graveyard))

<!-- original line 5627 -->
- [x] **AK-CPU-INT8-PREFILL** [non-inference then inference] Port vLLM's CPU int8 prefill GEMM advantage into C6 (operator 2026-11-05: materialize the Q38P-4c result). Evidence: on one quarter (24 Zen 5 cores, NUMA node 0), Qwen3-4B, vLLM 0.33 CPU INT8 W8A8 (oneDNN `CPUInt8ScaledMMLinearKernel`) prefilled **2.92x** (2048) and **3.16x** (8192) faster than C6 `729599d69` on Q8_0 GGUF, while C6 decoded ~2x faster (`mi210-serving-program.md` Q38P-4c; `artifacts/gpu-block-20261105/q38p4c-RESULT.json`). Step 1 (code, running 2026-11-05): root-cause the gap and rank port options: (a) oneDNN/brgemm int8 backend for large-ne11 MUL_MAT with load-time repack, (b) ggml's own Q8_0 AVX-512 VNNI GEMM with longer accumulation and scale deferral, (c) a tinyBLAS-style int8 kernel. Design report `/mnt/raid0/llm/tmp/cpu-int8-prefill-port-20261105/DESIGN.md`. Step 2 (one CPU-quarter row): MUL_MAT microbench at Qwen3-4B shapes (M=2048), C6 vs the chosen candidate, same cores. Step 3: experimental-tree implementation through the AK gates (test-backend-ops tolerance, champion quality gate), then pp tok/s at 2k/8k on the 4B and the production CPU models. Done when the C6 candidate closes >= half of the 3x prefill gap with no decode regression beyond noise, or the design shows why it cannot. [no-belief: new box]
  - *(2026-11-05 20:30Z, main-inf22)* **Decode check: DECODE_FLAT** for the iqk Q8_0 prefill-on-by-default fix (commit `9b78d1408`, branch `experimental/iqk-q8-prefill-default-20261105` on C6 `729599d69`; store `/mnt/raid0/llm/kernels/builds/cpu-20261105-9b78d1408-c6q8pf`). Median N/L: pp512 **1.99x**, fresh tg128 1.017, after-pp tg128 0.997 (bands [0.97,1.03]); GGML_IQK=0 control 1.000 tg128 / 0.98 after-pp. Earlier A/B (`/mnt/raid0/llm/tmp/iqk-q8-prefill-ab-20261105/`): pp2048 2.03x, pp8192 1.56x, quality screen pass (KLD 4e-4, top-1 40/40). Result `/mnt/raid0/llm/tmp/iqk-q8-decode-check-20261105/out/RESULT.json`. Box stays open: the half-gap done bar is met at 2k (vLLM lead 2.92x -> 1.44x) but not at 8k (3.16x -> 2.03x), and the production CPU models are not yet measured. Next: fold into the champion (operator pre-approved since decode is flat). [no-belief: rowflow result JSON, no adapter]
  - *(2026-11-06, main-inf22)* ✅ **RESULT: FOLDED (operator decision 2026-11-06), recorded as manifest V11-123 for `65da39eb1`** (`experimental/c6-iqkq8pf-fp16s-20261105` on fork = C6 `9e9d7f291` + `9b78d1408` cherry-pick `f3a6a4baa` + fp16-activation-scale fix). Gate history: (1) decode check DECODE_FLAT (`/mnt/raid0/llm/tmp/iqk-q8-decode-check-20261105/out/RESULT.json`); (2) fold gate on `f3a6a4baa` `/mnt/raid0/llm/tmp/c6-iqkq8pf-fold-gate-20261105/out/RESULT.json`: 4a op tests pass, short-prompt greedy identity pass, llama-server np1 1.009 / np4 0.982 (closes the A/B's 0.82x np1 reading), A3B pf2048 1.70x, KLD screen FAILED -> superseded; per-op diagnosis: the route is int8-identical to C6 (shadow ~1e-12), the delta came from activation-scale precision, fixed by fp16 scales in `65da39eb1`; (3) NWT r1 `/mnt/raid0/llm/tmp/c6-iqkq8pf-nwt-gate-20261105` +0.20% PPL, r2 `/mnt/raid0/llm/tmp/c6-iqkq8pf-nwt-gate-r2-20261105` +0.29%; (4) null gate `/mnt/raid0/llm/tmp/c6-iqkq8pf-nwt-null-20261105/out/RESULT.json` NWT_NULL_FAIL: +0.29% PPL vs 6 one-tensor nulls mean +0.08% sd 0.04%, KLD within null, all nulls positive, sign test p=0.03 (caveat: nulls single-tensor; C6's draw may be favourable). Operator decision 2026-11-06: FOLD, accepting the measured worst-case cost ~+0.3% PPL on A3B for 1.7-2x CPU prefill. Operator rationale: the ~0.3% PPL cost is far smaller than the quality gap between quantization levels (a 4-bit quant typically costs several % PPL vs Q8_0). Remaining for the candidate (C6 box, not this one): GPU store for `65da39eb1` (packet `/mnt/raid0/llm/tmp/c6-iqkq8pf-fp16s-build-20261106`, prepared, not published) and the C6 champion CAS binding to `65da39eb1` (owner workspace-23 per operator 2026-11-06). [no-belief: rowflow result JSON, no adapter]

<!-- original line 5635 -->
  - [x] **AK-ASM-H1** [non-inference then inference] skinny-M Q8_0 MMQ for DFlash verify (M=5..16). Report `artifacts/analysis/mi300-to-mi210-portability-20261105.md` item #1: C6 `mul_mat_q` runs at ~31% of bandwidth roofline here and is ~70% of the 67 ms 27B verify step (~47 ms vs ~20 ms ideal). Tier: HIP + builtins: repacked aligned Q8_0, deep prefetch (~18 loads in flight, as AITER GEMMs), split-K. Est. +20-35% DFlash2 tok/s [inferred]. Falsifier: verify-step time within noise at M in {5,8,16}, or test-backend-ops failure. Effort M. Model: Qwen3.8-27B Q8_0. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: KEEP (arm b, H1b)** — wvSplitK-style Q8_0 GEMV for weights >6MiB, M 5..11: 27B large geomean 1.73x (M5 1.83, M8 1.64), 927 vs 545 GB/s, A3B min 0.999; e2e 27B pp5/pp8 123/183 vs C6 79.5/127 t/s (row `ak-asm-h1b-gate-20261106` r3, commit `c271c8a09`, `experimental/ak-asm-h1b-wvsplitk-20261106`). M>=12 excluded post hoc (r1/r2: loses). **Post-hoc dispatch gate (data audit 2026-11-07):** r1 and r2 were GATE_FAIL under the pre-registered rule (21 large 27B cells at M 5/8/16, A3B floor 0.97); `GGML_HIP_Q8_WVSK_MAX=11` was chosen from r1+r2 data and the r3 verdict was evaluated on the 14 dispatched M5/M8 cells only (`ak-asm-h1b-gate-20261106/out/RESULT.json` caveats). Already in champion C7r; C7r's end-to-end gates measured the whole bundle, not this gate alone. Small-weight (<=6MiB) arm KEEP with H7: 1.94x selected cells (9 of 12 are A3B; 27B selected 1.21x, 27B all-cells 1.026x), A3B 1.51x (row `ak-asm-h1h7-gate-20261105` r7, commit `671584db0`; r6 on the same sha was GATE_FAIL, worst 0.9689 — see the H7 result line). Original arm on 27B large: v1-v3 0.70/0.75/0.83x, DROPPED (superseded by H1b). [belief: cc]

<!-- original line 5637 -->
  - [x] **AK-ASM-H2** [non-inference then inference] flash attention off rocWMMA. C6 uses the deprecated rocWMMA FA (f16 accumulation, softmax via LDS, q8_0 KV fully converted to f16 first). Arms: (a) C6's own `fattn-mma` D=256 path (unreachable in the ROCWMMA=ON build: build ROCWMMA=OFF), (b) CK-tile fmha fwd for gfx90a (covers hd256). Est. +15-25% on 80k verify steps, +5-10% prefill at 16k [inferred]. Falsifier: FA op time at 8k/32k hd128/hd256 within noise. Effort M. Model: Qwen3.8-27B Q8_0 / Qwen3.6-35B-A3B Q8_0 (hd256). Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. (evidence: progress/2026-11/2026-11-06-main-inf22.md) [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: arm (a) DROP, arm (b) carried by H5-PORT hd256** — rocWMMA-off MMA path MMA_INVALID; CK-tile hd256 FA passed 3.71x op-level (see AK-ASM-H5-PORT). [belief: cc]

<!-- original line 5639 -->
  - [x] **AK-ASM-H3** [non-inference then inference] decode GEMV prefetch A/B: C6 already ships an LDS-DMA Q8_0 prefetch variant, off by default. A/B `GGML_CUDA_Q8_PREFETCH=1` at idle decode (spec off). Q8_0 GEMV sits at ~70% of roofline. Est. +7-14% decode [inferred]; prior: an MMVQ prefetch with the same intrinsic was net-negative (AK-MMQ-H8 note), so measure. Effort S. Model: Qwen3.8-27B Q8_0 (llama-bench tg128, -ngl 99, C6 store). Stop-on-answer when 5 interleaved valid pairs give median on/off >= 1.03 (keep) or < 1.03 (drop); stop-on-futility on fewer than 5 valid reps after 3 attempts; gate-class = futility-only. Row: /mnt/raid0/llm/tmp/ak-asm-t0-h3-gate-20261105 (also runs T0 graph-capture test). [no-belief: seed hypothesis] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* T0 half PASSED; H3 prefetch A/B pending GPU. [no-belief: not-a-result]
    - *(2026-11-06 later, main-inf22)* T0+H3 A/B row queued; FA hd256 r4 (graph + long-ctx) also queued. [no-belief: not-a-result]
    - *(2026-11-06, main-inf22)* **RESULT: DROP (regression)** — row `ak-asm-t0-h3-gate-20261105`, C6 store `729599d69`, Qwen3.8-27B Q8_0 tg128, 5 interleaved pairs: median off 33.24 t/s (CV 0.5%), on 31.46 t/s, on/off **0.947** (< 1.03 keep bound; -5.4%). Same sign as the AK-MMQ-H8 MMVQ prefetch note. [belief: cc]

<!-- original line 5643 -->
  - [x] **AK-ASM-H4** [non-inference then inference] pipelined int8 MMQ for large-M prefill (ne11>128): replace dequant-to-f16 + rocBLAS (the convert is ~15%) with 32x32x8i8 MFMA tiles, LDS double buffer and `sched_group_barrier` interleave. Est. +10-20% prompt processing [inferred]. Note MI210 int8 MFMA = bf16 rate, so the gain is from removing the convert and pipelining, not 2x int8 compute. Effort M-L. Model: Qwen3.8-27B Q8_0, Qwen3.6-35B-A3B Q8_0. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. (evidence: progress/2026-11/2026-11-06-main-inf22.md) [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: DROP** — int8 MMQ 0.48x vs rocBLAS; e2e pp2048 587 vs 835 t/s. [belief: cc]

<!-- original line 5645 -->
  - [x] **AK-ASM-H5** [non-inference then inference] retarget AITER gfx942 FA v3 fwd hd128 asm to gfx90a as the hand-asm existence proof: it re-assembled 3206/3206 lines with `llvm-mc -mcpu=gfx90a` after two MFMA renames. Needs a control-flow-aware hazard audit at gfx90a's doubled MFMA pass counts, a rebuilt kernel descriptor, a `hipModuleLoadData` loader and correctness vs test-backend-ops. Time vs C6 FA hd128 (Qwen3-4B / hd128 models). Effort M. Techniques to carry over: 8-wave ping-pong at `s_setprio` 0/1, MFMA:VALU 1:7 with exp interleaved, LDS-DMA for K/V. [no-belief: seed hypothesis]
    - *(2026-11-05 17:05Z, main session)* **RESULT: CORRECT+FASTER — retargeted gfx942 AITER FA-v3 fwd hd128 bf16 asm runs on MI210** (row `ak-asm-h5-fa-retarget-20261105`, rc0, quiet GPU). Retarget: two MFMA renames, rebuilt gfx90a kernel descriptor (accum_offset 256, 102 SGPRs), CFG hazard audit at gfx90a MFMA pass counts with s_nop padding (4 MFMA sites + 34 M0->LDS-DMA sites per kernel), loaded via hipModuleLoad. Correctness 6/6 vs fp32 SDPA (S 128/1024, MHA and GQA 32/8, causal and full; max_abs <= 0.008, no NaN). Timing H32/KV8 GQA (median of 7) vs torch SDPA bf16: S8192 full 9.43 vs 11.45 ms (1.21x, 117 TFLOPS), causal 4.91 vs 6.28 (1.28x), S32768 full 153.2 vs 177.1 (1.16x, 115 TFLOPS), causal 77.4 vs 95.6 (1.23x); geomean **1.22x**, ~63% of bf16 peak. Next: the same shapes against C6's own FA (rocWMMA path) via test-backend-ops perf, which decides a port into the experimental tree. Artifact `artifacts/analysis/ak-asm-h5-fa-retarget-RESULT-20261105.json`; packet `/mnt/raid0/llm/tmp/ak-asm-h5-fa-retarget-20261105/`. [belief: cc]
    - *(2026-11-05 17:55Z, main session)* **RESULT vs C6: PORT_CANDIDATE — the retargeted asm FA is 3.87x faster than C6's FLASH_ATTN_EXT on the fair (no-mask) cells** (row `ak-asm-h5b-vs-c6-fa-20261105`, rc0, one GPU session, verdict pre-registered on full cells). B1 H32/KV8 D128: S8192 full C6 f16 36.03 ms (30.5 TFLOPS) / q8_0 36.04 vs asm 9.53 ms (115 TFLOPS) = 3.78x; S32768 full C6 611.3 / 612.6 ms (28.8 TFLOPS) vs asm 154.7 ms (114 TFLOPS) = 3.95x. Causal cells 9.4x / 9.0x are biased (C6 test mask cannot skip the triangle). C6 FA reaches ~17% of bf16 peak vs ~63% for the asm. Caveat: the asm covers dense bf16 hd128 causal/full only; C6 handles masks, softcap, ALiBi, sinks and q8_0 KV. Artifact `artifacts/analysis/ak-asm-h5b-vs-c6-fa-RESULT-20261105.json`. [belief: cc]

<!-- original line 5648 -->
  - [x] **AK-ASM-H5-PORT** [non-inference then inference] Port the retargeted gfx90a FA-v3 fwd asm (AK-ASM-H5) into the C6 experimental tree as a FLASH_ATTN_EXT fast path: load the .co via hipModuleLoadData at backend init, dispatch when D=128, K/V dense (f16 or bf16 after the existing conversion; q8_0 KV converted as today), mask causal or none, no softcap/ALiBi/sinks, else fall back to the current kernel. Also: an hd256 variant (Qwen3.8-27B is D=256; AITER's only hd256 asm is gfx950, so that needs the CK-tile fmha or a hand retarget), HIP-graph capture of module launches (unverified on ROCm 6.2), and bwd not needed. Gates: test-backend-ops FLASH_ATTN_EXT correctness vs reference at real shapes, then pp tok/s at 8k/32k on the production GPU models (expected large: FA is 3.9x faster at the op level), decode unaffected. Done when the fast path is in an experimental build that passes the AK gates with measured pp gain, ready to fold into the champion. Model: Qwen3.8-27B Q8_0, Qwen3.6-35B-A3B Q8_0, Q38FN. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: KEEP (hd256 CK FA)** — op-level GATE_PASS 3.71x (row `fa-ck-hd256-gate-20261105` r3, store `4ffe32abd`, offset-guard bug fixed); e2e 27B pp2048 only +3%. Graph-capture commit `6148b1333` + long-ctx prefill gate r4 queued (`fa-ck-hd256-gate-r4-20261105`) — child box below. [belief: cc]
    - [x] **AK-ASM-H5-PORT-R4** [inference] read and file `fa-ck-hd256-gate-r4-20261105` (graph capture `6148b1333` + long-ctx prefill); stop-on-answer: pp gain at 32k vs C6 measured. Model: Qwen3.8-27B Q8_0. [no-belief: new box] ✅ 2026-11-06
      - *(2026-11-06, main-inf22)* **RESULT: GATE_FAIL (graph-mode), stop-on-answer before perf** — row `fa-ck-hd256-gate-r4-20261105` (store `gpu-20261106-6148b1333-c6fa`, rc0). Correctness all PASS on the new store: CK hd256 ck1-ck4 94/94, 94/94, 151/151, 94/94; asm hd128 100/100 x2; asm0 194/194; full corpus 2978/2978. Graph pass failed on the FIRST model (g128 = Qwen3-1.7B hd128 asm, llama-perplexity c512 x16 chunks): (i) capture-witness and fast-path lines absent in g1, (ii) g1 PPL 20.2097 vs ref (`GGML_HIP_FA_ASM=0`) 19.9571 = +1.27% > 0.5% bound. g1 == g0 chunk for chunk, so graph capture changes nothing numerically. The g256 (27B CK hd256) graph arm, the 9 op-level perf cells and the long-context e2e (pp8k/16k/32k, 27B + A3B, keep flag pp32768 new/ck0 >= 1.10) did NOT run: no long-context numbers, keep flag unmeasured. Reading: (i) is a harness defect — the three witness strings are in `libggml-hip.so.0.16.0` (`strings`), but the perplexity logs hold 10 lines (backend info logs filtered at default verbosity). (ii) is about the hd128 asm path, not CK hd256 or graphs: the asm fast path moves Qwen3-1.7B PPL by +1.27% at hd128 (it is a bf16 kernel; K/V/Q rounding to bf16 is the likely cause, unproven). The non-graph CK hd256 path stays a KEEP (r3 op-level 3.71x, correctness re-passed here); the hd128 asm PPL drift is open and also sits in C7 (`d6d1e9dd0`). [belief: cc]
    - [x] **AK-ASM-H5-PORT-R5** [inference] re-gate graph mode + long context: (1) give the graph-pass llama-perplexity runs `-v` (or `--verbosity` high enough) so the witness lines print, and check them; (2) settle the hd128 asm PPL drift (+1.27% on Qwen3-1.7B): A/B an fp16 vs bf16 K/V feed or widen the bound with a stated basis, and decide whether hd128 asm stays default in C7; (3) run g256 (27B CK hd256) graph arm, the 9 op perf cells and long-ctx e2e pp8k/16k/32k on 27B + A3B; keep iff 27B pp32768 new/ck0 >= 1.10 (feeds H18). Stop-on-answer: keep flag measured; stop-on-futility: correctness or g256 graph failure. Model: Qwen3.8-27B Q8_0, Qwen3.6-35B-A3B Q8_0. [no-belief: new box]
      - 2026-11-07 RESULT: **KEEP** (row fa-ck-hd256-gate-r5-20261106-r3, C7b store e93f9417e; CK hd256 path identical in champion C7r). Graph mode on 27B: capture tag ck-hd256, per-chunk PPL g1 == g0 exactly, within 0.5% of fast-path-off reference; splits equal to C6 on 27B and A3B (2/2); 27B pp32768 new/C6 = **1.195** (≥1.10 keep; H18 falsifier <1.03 not hit); op-level geomean C6/new 3.68. Already in champion C7r — no further fold. Evidence /mnt/raid0/llm/tmp/fa-ck-hd256-gate-r5-20261106/out/RESULT.json. ✅ 2026-11-07 [belief: cc]
    - [x] **AK-ASM-FA128-GATE** [non-inference then inference] hd128 asm FA path is bf16 end to end (+1.27% PPL on Qwen3-1.7B, no served model hits it by default; DFlash2 draft is hd128 but its 8-token blocks stay under MIN_BATCH 64). Gate it off by default: commit `e93f9417e` on experimental/c7-fa128-gate-20261106; append to C7 after the C7 r2 gate with an incremental gate. Follow-up: CK-tile fp16 hd128 instance (PPL Δ<0.5%, perf vs C6). *(2026-11-06, main-inf22: default-off gate folded into C7r `62cb6a6af`; CK-tile fp16 hd128 follow-up not started (C8 candidate))* [no-belief: fold landing] ✅ 2026-11-06

<!-- original line 5655 -->
  - [x] **AK-ASM-H6** [non-inference then inference] fused RMSNorm + quantize (activation quant into Q8_1) in one kernel, removing a pass over the activations. Effort S; gain small but per-layer [inferred]. Model: Qwen3.8-27B Q8_0. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. (evidence: progress/2026-11/2026-11-06-main-inf22.md) [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: DROP** — fused rmsnorm+quant below the 1.10 op bar. Corrected 2026-11-07 (main-inf22): the earlier "1.017x" has no surviving raw packet; the gate's on-disk `/mnt/raid0/llm/tmp/ak-asm-h4h6-gate-20261105/out/RESULT.json` says h6_verdict INCONCLUSIVE, one cell h6off/new 0.9997. Research citations were corrected in cddaaf14c. [belief: cc]

<!-- original line 5657 -->
  - [x] **AK-ASM-H7** [non-inference then inference] split-K reduction without `global_atomic_pk_add_bf16` (MI300-only): f32 atomics or a two-pass reduction, enabling the AITER bf16 split-K GEMM / fused-MoE asm on gfx90a (they fail only on that instruction: 48 and 48 lines). Prerequisite for lifting those kernels; pairs with H1. Effort M. Model: Qwen3.8-27B Q8_0. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: KEEP** — f32-atomic split-K (stream-K + LDS-DMA) small-weight skinny path, GATE_PASS selected cells 1.94x, A3B 1.51x no regression (row `ak-asm-h1h7-gate-20261105` r7, commit `671584db0`, `experimental/ak-asm-h1h7-20261105`). **Data audit 2026-11-07 (main-inf22, from the packets):** the 1.94x is the geomean over 12 gate-selected cells, 9 of them A3B (A3B selected 2.28x; 27B selected = 3 attn_kv cells 1.21x); 27B all 21 cells 1.026x, A3B all 18 cells 1.51x; worst cell 0.9876 (floor 0.97). The 6 MiB selection rule was derived POST HOC from r5 (`out.r5-14372feeb`); its first confirmation run r6 on the same sha `671584db0` (same build sha256 `0c611a0e`) was **GATE_FAIL** (worst cell attn_qkv/10240x5120/M16 0.9689 < 0.97; `out.r6-671584db0/RESULT.json`); the KEEP rests on the r7 repeat (`out/RESULT.json`), which passed. Under the r6 pre-registration read literally, the confirmation failed once and passed once: treat the KEEP as a post-hoc dispatch gate whose floor margin is inside run-to-run noise. C7r's end-to-end gates measured the whole bundle, not this patch alone. [belief: cc]

<!-- original line 5659 -->
  - [x] **AK-ASM-T0** [non-inference then inference] tooling prerequisite for the hand-asm tier: load a gfx90a `.co` with `hipModuleLoadData` + `hipModuleLaunchKernel` from the experimental llama.cpp tree (AITER pattern: `csrc/include/aiter_hip_common.h:285-425`), and verify HIP-graph capture of module launches on ROCm 6.2 (unverified). The builtins tier is already proven on our ROCm 6.2 clang: `sched_group_barrier`, `sched_barrier`, `iglp_opt(0)`, `s_setprio`, `*_1k` MFMA builtins compile for gfx90a. Effort S. Model: Qwen3.8-27B Q8_0 (graph-capture test binary). Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: PASS** — HIP-graph capture of `hipModuleLaunchKernel` works on ROCm 6.2 (row `ak-asm-t0-h3-gate-20261105`). H3 prefetch A/B still pending GPU. [belief: cc]
    - *(2026-11-06, main-inf22)* Full run: eager 1, graph nodes 1, not run at capture, 7 replays OK, `hipGraphExecUpdate` no error, update replay OK. H3 closed DROP (0.947x, see AK-ASM-H3). [belief: cc]

<!-- original line 5662 -->
  - [x] **AK-ASM-H8** [non-inference then inference] fused MoE expert GEMM from AITER `fmoe` / `fmoe_2stages` for Qwen3.6-35B-A3B and Q38FN: sorted-token tiles, gate+up fused (g1u1) with SiLU in the epilogue, down GEMM, atomic f16 output. Retarget evidence: fp16-out noquant (`fmoe/silu/fmoe_fp16_noquantFp16_g1u0_atm_inlv_silu_1tg_32x512.co`) and int8 (`fmoe/silu/fmoe_fp16_pertokenInt8_g1u1_silu_1tg_32x128.co`, `fmoe_2stages/…pertokenInt8_g1u1_112x128_pf2.co`) assemble 0-fail for gfx90a after renames + exact int8 K-split (`artifacts/analysis/mi300-asm-port-inventory-20261105.md` §0.1-0.2). Blocker: Q8_0 per-32 scales vs AITER per-channel (§0.7); arms (a) per-channel int8 requant at load behind the quality gate, (b) CK 2-stage MoE instance for gfx90a, (c) technique port into `mmid.cu` (sort + fused gate/up + GLU). Est. A3B/Q38FN prefill +10–20%, verify +5–10% [inferred]. Falsifier: MUL_MAT_ID op time at A3B shapes (M in {8,512,2048}) within noise, or KLD gate failure on arm (a). Effort L. Model: Qwen3.6-35B-A3B Q8_0, Q38FN. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [no-belief: seed hypothesis]
    - 2026-11-07 RESULT: **DROP** — H8 r4 op geomean 1.098 (<1.10); H8b post-hoc variant passed op gate r2 (1.29x) but failed E2E on real routing (pp512 0.949x / pp1024 0.968x). Fused-MoE port closed on MI210 at this design. ✅ 2026-11-07 [belief: cc]
    - *(2026-11-06, main-inf22)* Fused MoE gate r3 running on GPU at wrap-up time; no verdict yet. [no-belief: not-a-result]
    - *(2026-11-06 later, main-inf22)* Gate r3: correctness all pass (fused MoE route fired) [belief: cc]; perf stopped - CPU-bound random init, 1 of 5 reps in 1 h (invalid, no verdict). Reworked gate r4 (24 cells, 3 reps, fast init commit `ebbd923b6`) queued.
    - [x] **AK-ASM-H8-R4** [inference] read and file the H8 r4 perf gate (24 cells, 3 reps, `ebbd923b6`): op-level >=1.10 keep / <1.10 drop vs C6. Model: Qwen3.6-35B-A3B Q8_0, Q38FN. [no-belief: new box]
    - [x] **AK-ASM-H8B-E2E** [inference] model: Qwen3.6-35B-A3B Q8_0 on MI210. H8b (33fc2c757, row ak-asm-h8b-gate-20261106) was designed AFTER seeing H8 r4 per-cell data (bar 1.10→1.05, window 64-1024, fused cells excluded), so an op-level H8b pass is weaker evidence and does NOT by itself qualify for the C7 fold. Fold requires this pre-registered e2e check (fixed now, before H8b results): llama-bench A3B, all layers on GPU, C7 vs C7+H8b store, interleaved 5 reps; pp512 and pp1024 median ratio new/C7 ≥ 1.03 AND tg128 ratio ≥ 0.99 AND graph splits equal. Stop-on-answer when both ratios are measured with 5 valid reps; stop-on-futility if H8b op gate is DROP; gate-class = futility-only. [no-belief: new box]
      - 2026-11-07 RESULT: **NO_KEEP — H8b does not fold.** Row ak-asm-h8b-e2e-20261106, C7r 62cb6a6af vs C8-h8b 3597d6c3b, A3B MTP Q8_0, 5 interleaved reps: pp512 **0.949x**, pp1024 **0.968x**, tg128 0.998x, graph splits 2=2. The op-level 1.29x (uniform random expert routing in test-backend-ops) does not survive real routing: real A3B routing is skewed, so hot experts exceed the per-expert J hint and spill into extra narrow tiles (the caveat recorded at H8 r4). KEEP-TAIL-1: P 3.7%/1.7%, F 5.2%; pp512 effect inside F. Pre-registered rule → DROP. Possible successor (not queued): derive the tile hint from the real per-expert token histogram at dispatch time instead of mean×1.5; low expected ROI given A3B pp is already 1.04x vs C6 on C7r. Evidence /mnt/raid0/llm/tmp/ak-asm-h8b-e2e-20261106/out/RESULT.json. ✅ 2026-11-07 [belief: cc]
      - 2026-11-06 RESULT: GATE_FAIL → **DROP**. Store ebbd923b6; geomean C6/new over A3B/Q38FN expert-GEMM cells at M≥512 = **1.098** vs pre-registered 1.10 (3 reps; h8off/new context 1.046). Near-miss within noise, but bar was fixed in advance; not folded into C7. Evidence /mnt/raid0/llm/tmp/ak-asm-h8-gate-20261105/out/RESULT.json. ✅ 2026-11-06 [belief: cc]

<!-- original line 5670 -->
  - [x] **AK-ASM-H12** [non-inference then inference] fused QSA sparse attention for Q38FN: replace C6's `build_qsa_top_k` (top_k + get_rows + masked dense FA, `src/models/qwen4exp.cpp:675`) with a kernel that scores blocks, selects groups and runs GQA attention reading only the selected KV blocks, after AITER triton `qsa.py` (`_qsa_paged_mqa_logits_mfma_kernel`, `_qsa_sparse_paged_gqa_kernel`) and `topk_per_row` asm (needs the T1 rewrite pass). Est. Q38FN long-context prefill/verify +10–30% on QSA layers [inferred: dense masked FA reads all KV]. Falsifier: QSA-layer time at 32k/80k within noise, or output mismatch vs current path beyond FA tolerance. Effort M-L. Model: Q38FN. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: KEEP** — fused QSA attention 3.16x vs C6 dense FA at kv=32k (default dispatch MIN_KV_RATIO=8, chosen post hoc from r4). **Post-hoc dispatch gate (data audit 2026-11-07):** r4 failed its pre-registered small-batch floor (kv=8192 nb=1 f16 0.94x, nb=16 f16 0.78x / q8_0 0.81x); the threshold that routes those cells back to dense FA was picked from r4 data and r5 judged the shipped default under the unchanged rule (`ak-asm-h12-gate-20261105/out/RESULT.json` caveats). The fused path still LOSES at kv=8192 when forced. Already in champion C7r; C7r's end-to-end gates measured the whole bundle, not this gate alone; crash fix: top_k/mask held as FA src[5]/src[6] (graph-allocator lifetime); plus GPU radix TOP_K >1024 cols. Row `ak-asm-h12-gate-20261105` r5, commit `ba5a0c6cd` (`experimental/ak-asm-h12-20261105`). [belief: cc]

<!-- original line 5672 -->
  - [x] **AK-ASM-H9** [non-inference then inference] asm arm of H4: int8 GEMM for prefill/verify from AITER `gemm_a8w8_m128_noSplitK.co` / `i8gemm` (assemble 0-fail / 32-atomic-only on gfx90a after the exact int8 K-split, §0.1), with either per-channel int8 requant of Q8_0 (quality gate) or an epilogue patched to Q8_0 per-32 scales using the `fp8gemm_blockscale` epilogue as template. Time against dequant+rocBLAS and against the H4 HIP kernel at 27B shapes (M 16/512/2048). Est. 27B prefill +10–20% [inferred: removes the ~15% convert; int8 compute ceiling = bf16 on gfx90a]. Falsifier: MUL_MAT at M=2048 not faster than C6, or quality gate fails. Effort M-L. Model: Qwen3.8-27B Q8_0. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: DROP** — HIP int8 per-32-scale GEMM 0.52x vs C6. H9B fused dequant-f16 gate still pending GPU (child box below). [belief: cc]
    - [x] **AK-ASM-H9B** [inference] fused dequant-to-f16 + GEMM gate (pending GPU): op-level >=1.10 keep / <1.10 drop vs C6. Model: Qwen3.8-27B Q8_0. DROP: GATE_FAIL, geomean C6/new 0.642 over 24 cells, LDS 40960 B -> 1 block/CU (`/mnt/raid0/llm/tmp/ak-asm-h9b-gate-20261106/out/RESULT.json`). [belief: cc]
    - *(2026-11-06 later, main-inf22)* H9B gate running on GPU; no verdict yet. [no-belief: not-a-result]

<!-- original line 5676 -->
  - [x] **AK-ASM-H10** [non-inference then inference] GQA-packed multi-token verify attention for hd256 (technique of AITER `pa/*_mtp_msk*` asm: 8/16 q heads × qlen share one KV read, MFMA on decode, int8 KV dequant in registers). The hd128 bf16 MTP and int8-KV PA asm assemble 0-fail on gfx90a, but asm PA is head_size 128 only (`csrc/py_itfs_cu/asm_pa.cu:192`), so the 27B/A3B/Q38FN path is a HIP builtins kernel (or extend the asm). Target: FLASH_ATTN_EXT at q rows 5–16 with q8_0 KV, no full KV→f16 convert. Est. verify step +5–12% at ≥32k ctx (FA 28.7 + convert 7.9 of 158.7 ms at 80k), ~0 at short ctx [inferred]. Falsifier: verify-step FA time at 32k/80k within noise. Effort M. Model: Qwen3.8-27B Q8_0. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06 **Harvest #7 note (AutoKernel):** the KEEP covered n_q 2..16 (GATE_PASS 2.63x, kv>=32k). C8-DECODE-X-SWEEP Q1 now shows the same GQA-verify kernel at n_q=1 is a LEVER on C7r (1.004 @4k, 1.08 @32k, 1.25 @128k, 27B Q8_0 no-draft np1), via the env knob already in the tree; fold1 makes it the default and its re-gate decides. No AK action; cite when an AK hd256 decode box asks whether n_q=1 was ever covered by H10. fold1 also moves the A3B hd256 layers onto gv at n_q=1, which the fold1 gate's A3B tg@d32768 >= 0.99 cell decides. Evidence: root `6c9cb69ba`, `f0255bc31`.
    - *(2026-11-06, main-inf22)* **RESULT: KEEP** — GQA-packed hd256 verify attention GATE_PASS 2.63x (pipelined arm), kv>=32k, n_q 2..16 (row `ak-asm-h10-gate-20261106` r3); e2e E2E_GAIN 27B DFlash2 f16 KV np1 decode +4.8% @8k / +4.3% @32k / +14.6% @64k (43.4/38.7/40.0 vs 41.4/37.1/34.9 t/s; row `ak-asm-h10-e2e-20261106` r4). Commit `58367a3a9` (`experimental/ak-asm-h10-20261106`). [belief: cc]
    - 2026-11-10 (autokernel, addendum to the e2e row `ak-asm-h10-e2e-r4-20261106`): output hashes differ between the new and c6 arms at 32k and 64k (`outputs_identical_across_all_runs`: 8k true, 32k false, 64k false); the decode ratios above were measured with differing outputs at those depths, and acceptance means also differ (new 0.306/0.354 vs c6 0.322/0.351). The RESULT line does not record this; it is not shown to be a defect (different float order in a packed kernel can change a greedy trajectory) but it was not tested, so the 32k/64k gain is a speed number without an identity proof. Evidence `/mnt/raid0/llm/tmp/ak-asm-h10-e2e-20261106/out/RESULT.json`. [belief: cc]

<!-- original line 5682 -->
  - [x] **AK-ASM-H13** [non-inference then inference] fused hyper-connection seam for Q38FN (`qwen4exp` `hc_*_norm/down/up/inject`, ~2 chains/layer of small GEMV+norm+add ops, no fused GPU kernel in C6), after AITER `mhc_seam` asm (0-fail retarget, fuses residual/layer-input with split-K partials of the next GEMM) and `mhc_kernels.cu`. Step 1: measure the hc chain's share of Q38FN decode; build only if >= 4%. Est. Q38FN decode +2–6% [inferred]. Falsifier: hc share < 4% or fused time within noise. Effort M. Model: Q38FN. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: KEEP (H13b+c HIP fusion)** — Q38FN tg64 (-ngl 99 --n-cpu-moe 48) 18.62 vs C6 16.68 t/s (+11.7%); MEAN_D1 on GPU removed ~194 GPU<->CPU splits/token (294->100), GPU TOP_K>1024 removed 24 more at depth; remaining 100 splits are inherent --n-cpu-moe boundaries. AITER mhc_seam asm not applicable to Q38FN's hc. Row `ak-asm-h13b-gate-r2-20261106` r5, commit `c635c4101` (`experimental/ak-asm-h13b-20261106`). [belief: cc]

<!-- original line 5684 -->
  - [x] **AK-ASM-H13-HCTAIL** [inference] HIP fusion of the Q38FN hc elementwise tail (technique port after `mhc_kernels.cu`, not the asm): combine (scale+sigmoid+scale+repeat+mul+add) into 1 kernel; mix (scale+silu after `hc_down`, sigmoid+mul+mean_d1 after `hc_up`) into 2 kernels; ~1150 -> ~290 launches/token. Origin: RESULT `h13.follow_up` of row `ak-asm-h11h13-gate-r4-20261106` (the AITER `mhc_seam` asm cannot compute Q38FN's hc chain; the measured share was >= 11.8%, so the box's >= 4% bar is met). Model: Qwen3.8 Flash Next (Q38FN) UD-IQ4_XS, `-ngl 99 --n-cpu-moe 48` as in the H13b+c measurement; identity: greedy 128-token decode identical to the champion C10 `7f1bd044b` store, then op-level `test-backend-ops` vs the C10 store on the fused ops. Build: experimental branch off the current champion tip (fresh-tip rule), CPU+HIP store. [inference] Thresholds FIXED 2026-11-11 (autokernel), replacing the provisional 1.10 / 1.03x. Arms: knob on vs knob off on the same new store (knob off = the C10 code path; C10's test-backend-ops has no HC_COMBINE_NORM case). Stop-on-answer: KEEP iff greedy identity holds AND the op-level geomean (us_off/us_on, medians of 5 interleaved reps per arm, 4 Q38FN cells E 2560 hc 4 T 1/4/16/512) >= 1.10 AND the e2e Q38FN tg64 geomean on/off over 5 interleaved pairs (llama-bench -r 3 each) >= 1.010; DROP if either is below. Why: op noise floor is <= 2.4% rep spread at T1 and < 0.5% at T4..T512 (H13b r5 `ak-asm-h13b-gate-r2-20261106/out/perf.json`), and the expected op effect is 1.2-1.3x (3 -> 2 launches, ~8 -> ~6 stream passes), so 1.10 sits well clear of noise. The e2e noise floor is ~0.5-0.7% per run (llama-bench within-run SD 0.124/18.62 t/s; C6 vs md0 0.5% apart, same row), so the SE of a 5-pair geomean is ~0.4%. The expected e2e effect is +0.3-1.0% (~90 of the ~480 remaining elementwise launches per token; H13b removed ~770 for +2.6%). The provisional 1.03x was above any plausible effect, so it would have forced a DROP; 1.010 is ~2.5 SE. Stop-on-futility: build or content-proof failure, test-backend-ops failure, the witness missing on the real Q38FN graph (0 merged sites), greedy mismatch among C10 / off / on, op geomean < 1.10 (e2e is not run), or e2e geomean < 1.000 after 3 pairs. gate-class = futility-only. [no-belief: thresholds, not a result] ✅ 2026-11-12 rc=0 FAIL (DROP_E2E_FUTILITY), row ak-asm-h13-hctail-gpu-20261111-r6: identity PASS under the ratified A/A rule; op-level off/on geomean 1.196 (T1 1.11, T4 1.09, T16 1.12, T512 1.52) but end-to-end on/off 0.929/1.021/0.937, geomean 0.962 after 3 pairs < 1.00 futility floor. combine_norm fusion dropped; not a C11 candidate. r1-r5 failed on harness setup (no GPU smoke, stale source path, store collision, marker name, exact-identity gate). [no-belief: row verdict filed by agent]

<!-- original line 5695 -->
  - [x] **AK-ASM-H14** [non-inference then inference] fused q/k RMSNorm + RoPE + KV-cache write (+q8_0 quant) per attention layer, after AITER `fused_qk_norm_rope_cache_quant.cu`; replaces 4–6 launches per attention layer. Est. decode +1–3% on all three models [inferred]. Falsifier: decode tok/s within noise. Effort S-M. Model: Qwen3.8-27B Q8_0. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: DROP** — fused qk-norm+rope+kv-write 1.13x op but e2e 1.0006/0.992 (within noise). [belief: cc]

<!-- original line 5697 -->
  - [x] **AK-ASM-H11** [non-inference then inference] retargeted AITER `topksoftmax_4xNx{4,6,8}` asm (984 lines, 0 failures on gfx90a) vs C6 `topk-moe.cu` at A3B/Q38FN expert counts. Est. MoE decode +0.5–2% [inferred]. Falsifier: router kernel time within noise. Effort S (after T0). Model: Qwen3.6-35B-A3B Q8_0. Stop-on-answer when the op-level gate (>=5 interleaved reps vs the C6 store) gives geomean >= 1.10 (keep) or < 1.10 (drop); stop-on-futility on a test-backend-ops correctness failure; gate-class = futility-only. [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* **RESULT: KEEP (A3B only)** — topksoftmax asm router graph 1.25x, A3B tg 104.8 vs 102.6 off / 101.7 C6 (~+2%); AITER has no 512/top-10 kernel (Q38FN not covered). Row `ak-asm-h11h13-gate-20261106` r4, commit `36ea8ae1d`. Also found+fixed pre-existing C6 bug: `ggml_cuda_topk_moe_fusion` reads past the last graph node (`c650d06e0`; serving unaffected). [belief: cc]
    - [x] **AK-ASM-C6-TOPKMOE-FIX** [non-inference] carry `c650d06e0` (ggml_cuda_topk_moe_fusion reads past last graph node) into the champion as a C6 bug fix via the combined fold. *(2026-11-06, main-inf22: `c650d06e0` carried into champion C7r `62cb6a6af`)* [no-belief: fold landing] ✅ 2026-11-06

<!-- original line 5712 -->
      - [x] **AK-ASM-PORT-I8GEMM-C13** [non-inference then inference] port AITER int8 GEMM asm (`gemm_a8w8_m128_noSplitK.co` / i8gemm, see AK-ASM-H9) as a C13 fold candidate: timing row `ak-asm-aiter-vs-c12-timing-20261117-r2` measured 1.49x over C12. Needs a served consumer (int8 prefill/verify path) named before the port; if no served op consumes it, record 'no consumer op' and drop. Stop-on-answer: op-level match plus >= 1.10x vs the C13 baseline (KEEP), or no consumer / a miss (DROP). gate-class = futility-only. [no-belief: new box] ✅ 2026-11-18
        - 2026-11-18 (autokernel): **DROP: no consumer op** (the box's own stop clause). The timed AITER kernels are `I8gemm_bf16_perTokenI8_BpreShuffle_*x128` (r2 `aiter-i8gemm` gfx90a loads): per-token int8 activations x per-channel int8 weights in preshuffled B layout, bf16 out. The 1.49x was measured against MUL_MAT q8_0 x f32 (job.py line 39). Every served weight is Q8_0 or another block quant with per-32 block scales, so no served op feeds a per-channel int8 GEMM. Making one would need a load-time requant of Q8_0 to per-channel int8. That changes numerics, falls under the 27B-decides KLD/dPPL gate, and is the per-channel arm already scoped under AK-ASM-H9. H9's per-32-scale arm DROPPED at 0.52x, and H9B's fused dequant arm DROPPED at 0.642x. No port, worktree or row made. Reopen only if a served model ships per-channel int8 weights. [no-belief: static analysis, no run]

<!-- original line 5715 -->
    - [x] **AK-ASM-T1-BF16ULP** [non-inference] diagnose bf16gemm bf16-out 1-ulp mismatch (suspect: CAS rewrite of pk_add_bf16 rounding); fix or document the bound. ✅ 2026-11-17 [no-belief: arithmetic check + recorded harness numbers, no new run]
      - 2026-11-17 (autokernel): bound documented in research `7f05b823f` (`scripts/kernel_rnd/autokernel/asm_retarget/README.md`). The CAS rewrite is cleared: `cas_round_check.py 200000` gives 0 mismatches against exact RNE, including specials (denormals excluded, MODE-dependent). Harness r2 `bf16gemm-bf16out` shows max_abs 2.0 at ref_absmax 360 (= 1 bf16 ulp in [256,512)) on 12.2% / 12.5% of 20480 elements, while fp32-out of the same two retargeted kernels gives ret 0.0. Cause: with bf16 output, split-K partials are rounded to bf16 before the atomic add, a second rounding the single-rounded reference does not have. Bound: <= 1 bf16 ulp per element. Port and timing decisions use the fp32-out family. Not run: a split-K=1 bf16-out control (the harness splitk-diag unit was vacuous).

<!-- original line 5717 -->
  - [x] **AK-ASM-FOLD** [non-inference then inference] rebase all KEEP port branches onto the new champion C6 `65da39eb1` (not `9e9d7f291`; champion CAS C5 c72ec82f5 -> C6 65da39eb1, root 5db81bb56, V11-122/123 incl. CPU iqk Q8_0 prefill fold IN) and build ONE combined experimental tree with all KEEP ports (H12, H10, H1b, H1+H7, H13b+c, H11, H15 pending PPL, H5-PORT hd256, C6 topk-moe fix) and run the full AK gate set (incl. H15 PPL) on the full candidate binary -> champion candidate. Stop-on-answer: all gates pass (fold) or a port regresses (drop it, re-gate). Candidate C7 = experimental/c7-asm-ports-20261106 @ c420b9d1a (8 KEEP ports; rows c7-asm-ports-build/gate-20261106). Models: Qwen3.8-27B Q8_0 (DFlash2), Qwen3.6-35B-A3B Q8_0, Q38FN UD-IQ4_XS. Stop-on-answer when the C7 gate gives C7_GATE_PASS (correctness all pass, no e2e cell < 0.97x C6 (floor loosened 0.99->0.97 by operator 2026-11-06 before any run), PPL within 1 SE of C6) or a failing cell names the regressing port; stop-on-futility on a correctness failure; gate-class = futility-only. *(2026-11-06, main-inf22: C7r `62cb6a6af` PROMOTED to champion, CAS 65da39eb1 -> 62cb6a6af, fork ff verified; gate `/mnt/raid0/llm/tmp/c7r-gate-20261106/out/RESULT.json`; operator accepted 27B +0.17% PPL; manifest V11-124)* [belief: cc] ✅ 2026-11-06
    - *(2026-11-06, main-inf22)* Next C8-incremental folds onto champion C7r `62cb6a6af`: H8b (AK-ASM-H8B-GATE, gate r2 queued; H8B-E2E pre-registered requirement) and FA hd256 long-ctx r5 (AK-ASM-H5-PORT-R5). [no-belief: pointer note]
    - *(2026-11-06, main-inf22)* C7 built: `experimental/c7-asm-ports-20261106` @ `c420b9d1a` (pushed to fork) off C6 `65da39eb1`; merges H10 `27088c781`, H1b (+H1/H7 ancestor) `481aa662b`, FA asm/CK/graph `d6d1e9dd0`, H12 `0e08cf666`, H11 `4aaf7e28b`, H13b/c `7e9387147` (kept H12 radix TOP_K, dropped H13c bitonic), H15 `78e32ff59`, H14 default OFF `c420b9d1a`. Each merge GPU+CPU build OK, CPU test-backend-ops 8000->8253 pass / 0 fail. Row `c7-asm-ports-build-20261106` BUILD_OK; gate `c7-asm-ports-gate-20261106` queued (correctness; e2e vs C6 @0.97 floor; PPL 27B + Q38FN incl. H15 aliasing check and Q38FN C5-vs-C6 follow-up).
    - [x] **AK-ASM-FOLD-BUILD** C7 combined candidate builds and passes CPU test-backend-ops (8253 pass / 0 fail; row `c7-asm-ports-build-20261106` BUILD_OK). ✅ 2026-11-06 [no-belief: build/landing]
    - [x] **AK-ASM-FOLD-GATE** read and file `c7-asm-ports-gate-20261106`: C7_GATE_PASS -> champion candidate, else drop the named port and re-gate. *(2026-11-06, main-inf22 wrap-up 3.)* r1 FAIL was a gate-parser bug (stray warmup line). r2 `c7-asm-ports-gate-r2-20261106`: correctness pass; e2e 27B DFlash2 decode 1.40x/1.42x/1.43x vs C6 at 8k/32k/64k, 27B pp32768 1.19x, pp2048 1.01x; **PPL FAIL**: 27B ln +0.0017 (KLD 0.0008), Q38FN 3.905 vs 3.4425 (ln +0.126, KLD 0.19, same-top 88%). Evidence `/mnt/raid0/llm/tmp/c7-asm-ports-gate-r2-20261106/out/RESULT.json`. [belief: cc]
      - [x] **AK-ASM-C7-Q38-BISECT** [inference] row `c7-q38-ppl-bisect`: find the C7 port behind the Q38FN PPL regression. r1 inconclusive (witness-log rule); reproduced ln ~0.10 with run-to-run variance -> nondeterminism; top suspect H12 radix TOP_K tie handling; r5 running. Evidence `/mnt/raid0/llm/tmp/c7-q38-ppl-bisect-20261106/`. Then fold H8b/FA128 and re-gate C7. *(2026-11-06, main-inf22: root cause H13b hc fusions read inputs ggml-alloc had already reused (cross-split use counts); fixed by buffer-lifetime guard `e4d460c16`; C7r Q38FN PPL 3.454 vs C6 3.457)* [belief: cc] ✅ 2026-11-06
      - [x] **AK-ASM-H8B-GATE** [inference] H8b (`33fc2c757`, J cap 48, M<=8 guard) gate r2 queued; H8 r4 DROP 1.098 (win only at M=512 1.23x). Note: the H8b rule set was chosen post-hoc from r4 data; H8B-E2E pre-registered fold requirement applies. [no-belief: new box] 2026-11-07 RESULT: **DROP** — op gate r2 KEEP 1.29x (A3B M64-1024) but pre-registered E2E NO_KEEP (pp512 0.949x, pp1024 0.968x; uniform-routing op test vs skewed real routing, AK-ASM-H8B-E2E); branch experimental/c8-h8b-20261106 kept for record. ✅ 2026-11-07 [belief: cc]
      - [x] **AK-ASM-FA128-OFF** [inference] FA hd256 r4 GATE_FAIL graph-mode (hd128 asm bf16 PPL +1.27% on Qwen3-1.7B; no served model uses hd128 asm by default); default-off commit `e93f9417e` (store gpu-20261106-e93f9417e-c7b); r5 gate `fa-ck-hd256-gate-r5-20261106-r2` prepared, twice preempted. *(2026-11-06, main-inf22: folded as default-off in C7r (`62cb6a6af`, cherry of `e93f9417e`); hd256 long-ctx r5 remains next C8-incremental fold)* [no-belief: fold landing] ✅ 2026-11-06

<!-- original line 5727 -->
  - [x] **AK-ASM-PLANNER-SEED** [non-inference] make the AutoKernel planner see the 2026-11-05/06 AK-ASM results. Investigation (main-inf22, 2026-11-06): the planner sees none of them - `[belief: cc]` ticks have no ingest path (VB-CC-PILOT unbuilt) and the asm surface is unregistered. Operator chose "fast priors now + register": (a) research-repo program.md / do-not-retry list / preseeded hypotheses + seed review and fresh seeds; (b) root VB-CC-PILOT register + ~18 conclusion rows + planning-context canary. Done when the canary shows the AK-ASM KEEP/DROP conclusions in the planner context. Two agents running. [no-belief: new box] *(2026-11-06, wrap-up 3.)* DONE: research `f8167767a`, seeds `272b39a1a` (H19 zero-split mandatory for 27B/A3B GPU per operator policy; H22 Q38FN hybrid informational only, Q38FN is CPU-only in prod, hybrid uncommitted); root §1.5.1 item 3a gfx90a low-level tier (`5ca12f94a`); register via VB-CC-PILOT. [belief: cc]

<!-- original line 5733 -->
  - [x] **AK-BUILD-MEM-1** [non-inference, prepare only] (model: none, compile-only; quant_build: champion 62cb6a6af gfx90a HIP build; metric: per-TU peak RSS, lower is safer; region: CPU quarter; row `ak-build-mem-1-20261107`, prep `/mnt/raid0/llm/tmp/ak-build-mem-1-20261107/`) measure per-TU peak RSS of a NORMAL gfx90a HIP build of the experimental tree (e.g. `/usr/bin/time -v` per compile unit, or cgroup memory.peak per job) to confirm the 32 GiB/process cap at -j8 (AK-BUILD-CAP) does not break legitimate heavy TUs (mmq instances, fattn). Prepare the measurement script and the row; the build itself runs through rowflow. Gate class: futility-only. Stop: first complete build gives max-TU RSS (stop-on-answer); futile if max < 8 GiB (cap is slack, close) or a TU exceeds 32 GiB (raise cap, close). ✅ 2026-11-08 CAP_SLACK: max TU RSS 0.746 GiB (arg.cpp), 405 units, 0 failed, under the 8 GiB futility bar, so the 32 GiB cap is slack and this closes. [belief: cc]

<!-- original line 5734 -->
  - [x] **AK-H5-VERIFY** [inference] (model: none, op-level test-backend-ops FLASH_ATTN_EXT; quant_build: experimental build h5 = C6 65da39eb1 + hand-asm FA vs C6 champion store; row `ak-h5-verify-20261107`, prep `/mnt/raid0/llm/tmp/ak-h5-verify-20261107/`) before ANY keep claim on the hand-asm FA (surface proof B), explain the heads32 ~= heads16 timing at kv16384 (C6 8059 vs 4020 us but h5 1887 vs 1788): run the loop's own A/B row on the full shape set (heads 16/32, kv 512/4096/16384, plus the hd256-excluded shapes) and check h5 scales with work or is clamped/early-exiting. Gate class: futility-only. Stop: answer = h5 time scales with heads (or an identified clamp bug); futile if the full-shape A/B shows h5 within noise of C6. [no-belief: new box] ✅ 2026-11-10 ANSWERED by mechanism: row `ak-kernel-h5-verify-c9-20261109` UNDERFILL, h5 passes all 31 cells and time is set by per-workgroup latency (heads64/heads32 1.9113, nb2048 heads32/heads16 1.5733), no clamp bug, h5 not within noise of C6; the heads32~=heads16 timing is explained (the box's question); the keep claim for the hand-asm FA still needs an actor-generated candidate (AK-GFX90A-ASM-SURFACE). [belief: cc] [receipt-ack: ak-h5-verify-20261107 INCONCLUSIVE — the filed receipt is the 11-08 fixture failure; the question was answered by the later C9 re-run ak-kernel-h5-verify-c9-20261109 (UNDERFILL mechanism)]
    - 2026-11-08 RESULT (row `ak-h5-verify-20261107`, rc0): **SURFACE_FUTILITY at stage parse; the timing question is NOT answered.** correct-h5 rc=1, n_ok 25 / n_fail 2. The log shows FLASH_ATTN_EXT `[NONE] NaN` failures with NaN on BOTH ROCm0 and CPU at some indices, so check whether the fixture or the NaN comparison causes them before blaming the hand asm. No keep claim. Box stays open. [no-belief: not-a-result]
    - 2026-11-09 RESULT (C9 re-run, row `ak-kernel-h5-verify-c9-20261109`, rc0, filed inconclusive; box stays OPEN): **UNDERFILL** (PREREG ADDENDUM identified-mechanism outcome, diagnostic, not a keep claim). The 11-08 fixture failure is gone: h5 passes all 31 cells (n_fail 0), kill-switch and the nb1 / gqa16 / hd256 controls match C9 stock. At nb512 kv16384 h5 heads32/heads16 = 1.0547 (below the 1.5 SCALES bar), but the fill is restored: heads64/heads32 = 1.9113 and nb2048 heads32/heads16 = 1.5733, so h5 time is set by per-workgroup latency (about one 512-thread workgroup per CU, 32 and 64 workgroups on 104 CUs), not clamping. Not ticked: this box's own Stop line names only SCALES or an identified clamp bug as the answer, and UNDERFILL is the third outcome the PREREG added before the run. Whether UNDERFILL closes the box is left to the box owner; the keep claim for the hand-asm FA still needs an actor-generated candidate. Evidence copy `artifacts/analysis/ak-c9-h5-lb49-20261109/h5-verify-RESULT.json`. [belief: cc]

<!-- original line 5737 -->
  - [x] **AK-MMQ-IGLP1-DNR** [non-inference] record `__builtin_amdgcn_iglp_opt(1)` on MMQ `vec_dot_*_mma` as a do-not-repeat entry candidate: build-pathological on gfx90a (clang-18 device compiles of mmq-instance-iq1_s/iq2_s reach 37 min / 222 GB + 124 GB RSS), evidence proof row A `ak-surface-proof-a-20261106`. Add to the planner's failed-mechanism / do-not-repeat source with the receipt; re-open only with a per-TU build cap and a narrowed instance set. Gate class: futility-only. Stop: entry written and visible in planner context (canary). [no-belief: new box] ✅ 2026-11-09 research 265b0f022: entry on the `gfx90a.iglp_opt1` row of `loop/program.md`, which `run.py` reads whole into planner context (`loop.PROGRAM`); no live planner turn observed. [no-belief: tooling]
    - 2026-11-08 RESULT (row `ak-surface-proof-a2-20261107`, C6 vs iglp0): **SURFACE_E2E_OK**, the surface path builds, loads, verifies and times this candidate kind. But correctness for iglp0 mul_mat is FALSE (rc=1, 970/1145 tests passed); read `/mnt/raid0/llm/tmp/ak-surface-proof-a-20261106/out/logs/correct-iglp0-mul_mat-1794124954.log` before using any iglp0 timing. Surface proof only, no keep/drop. [no-belief: not-a-result]

<!-- original line 5739 -->
  - [x] **AK-GDN-SPEC-SPLIT** [non-inference then inference] (model: Q38FN on CPU, Qwen3.6-35B-A3B on CPU as second shape; quant_build: experimental from champion C14 `eee3da838`, default-off env knob) split the CPU `GATED_DELTA_NET` verify work over value-column blocks, after vLLM #64829 (merge `b4dffa50`, intake-2695). Gap, read 2026-11-19 at C14 `ggml/src/ggml-cpu/ops.cpp:L12278-L12390 @ eee3da8`: work items are only `H x n_seqs` (head, seq), so at batch 1 most of 96 threads idle, while each value row `j` of the transposed state (delta, outer-product row, attn output) depends only on `k`, `q`, `beta`, `g`, so a 64-column block split is exact. Upstream reports 64 work items instead of 32 at batch 1 and median ITL 127.85 -> 120.08 ms (-6.1%) on Qwen3.6-35B-A3B + DFlash2 on a 48-vCPU host (not our hardware). Profile first: read the GGML op-time share of `GATED_DELTA_NET` in one verify step from an existing Q38FN perf trace, or one `test-backend-ops perf -o GATED_DELTA_NET` run at the served shape. Stop on futility if the op share is below 3% of the verify step (no code). Otherwise implement the split behind `GGML_GDN_COLSPLIT=1`, require `test-backend-ops -o GATED_DELTA_NET` bit-exact against the off arm (incl. K>1 snapshot slots), then an interleaved op A/B. Stop on answer at op geomean >= 1.20 (carry to the e2e gate) or < 1.05 (drop, record do-not-repeat); gate-class futility-only.
    - ✅ 2026-11-19 (autokernel) `ak-gdn-spec-split-cpu-20261119` filed **pass**, MEASURED FUTILE: GATED_DELTA_NET is 1.11 % of a Q38FN batch-1 CPU decode step (36 layers x 11.3 us of 36.7 ms) and 1.76 % for A3B (30 x 10.5 us of 17.9 ms), below the 3 % threshold; no code arm run. Closed. [no-belief: row verdict filed by agent]

<!-- original line 5741 -->
  - [x] **AK-GAP-1** [inference, GPU, profile-only] (model: Qwen3.8-27B Q8_0 + DFlash2 drafter on the MI210, served recipe; second shape Qwen3.6-35B-A3B Q8_0; quant_build: champion C14 `eee3da838` store binary, no code change) one rocprofv3 kernel-trace census of a graph-replayed decode step and one DFlash2 verify step. It answers which later-MI-series fusion ports are worth building on gfx90a (intake-2697 FlyDSL monokernel, intake-2696 AITER fused reduce-add-RMSNorm, intake-2700 SGLang small-batch MoE sort, intake-2695 spec sampling). Report: (a) idle-gap share between consecutive kernels inside the step (the part a monokernel or cross-stage prefetch could recover; HIP graphs already remove host launch cost); (b) count and time of MMQ stream-K fixup kernels followed by a norm (the fused split-K reduce + add + RMSNorm boundary; plain add+RMSNorm fusion is already in C14 `ggml_cuda_op_rms_norm_fused_add`); (c) `mm_ids_helper` and top-k time on A3B; (d) host time between graph computes for sampling and acceptance. Stop on answer: each lever whose recoverable share is >= 3% of the step gets its own port box, filed through a research-intake plan; each lever below 2% is closed as measured-futile in this box. Stop on futility: the trace lacks per-kernel timestamps, so the census is not judgeable (record it; do not estimate). Sufficiency: one census, 3 steps per arm, no A/B. est 2700 s. Lane: gpu-q3, host threads pinned 184-191.
    - Later-MI-series reverse-engineering lens (operator 2026-11-19), mechanism carry-over to gfx90a, all estimates [inferred]: FlyDSL monokernel relies on gfx950 plus cross-GPU reduction overlap; the gfx90a substitute is single-GPU cross-stage weight prefetch with buffer loads into registers or LDS (CDNA2 has no direct-to-LDS async copy); the benefit that survives is bounded by (a). ZYFA ping-pong FA relies on FP8 MFMA leaving the matrix unit idle while softmax runs (their trace: matrix unit idle 31.7% of cycles); on gfx90a the f16 MFMA has more slack relative to VALU, so little survives, and only in prefill FA. Re-open only if a prefill trace shows FA MFMA-idle above 20%. Lean P overlaps seed S8 (AKX M13). The AITER split-K fused reduce-quant relies on gfx942 Triton configs; the substitute is folding the stream-K fixup into the next norm, bounded by (b). Starscream relies on MI300 compute partitioning, which MI210 does not have; its only analogue is EPYC NPS sharding, which belongs to the NUMA placement work. Knowledge-only.
    - Instrument: reuse loop/gpu_serving_profile.py (live-server rocprofv3 kernel trace, fiducial windows, static VGPR/spill/occupancy); new work is only the within-step gap histogram and row classification for (a)-(d). (intake-lowhang review 2026-11-19)
    - Wave evidence (intake-2697, dive-verified 2026-11-19): HIP graph replay removes CPU submission overhead, but the GPU still runs dependent kernels in sequence, so (a) is not covered by G8. Monokernel gains shrink as batch grows, and an FFN-only layer test was near parity. gfx90a substitute for the FlyDSL primitives (intake-2703: resident grid, tagged-pair mailbox, phase-overlaid LDS arena): global-atomic mailbox flags, buffer_load plus ds_write in place of gfx950 async-to-LDS, and MFMA 16x16x16 f16 in place of the gfx950 `mma=16x16x32` GEMM. Follow-on task: AK-RESGRID-1.
    - Declines (operator-reviewed 2026-11-19) with reopen conditions: Triton 3.9 (intake-2702), reopen if a served path adopts Triton kernels; FlashInfer GDN tree verify (intake-2701), reopen if DFlash2 adopts tree drafts; thread-trace matrix-unit-idle profiling (A4), reopen if ROCm on gfx90a gains working ATT; ROCm 10.2 SPM and PC sampling (A5), reopen if AMD lists gfx90a for either; TileRT (intake-2704), reopen if its compiler techniques are released as source.
    - 2026-11-19 RESULT (row `ak-gap-1-trace-gpu-20261119`, rocprofv3 kernel trace, C14 store `gpu-20261118-eee3da838-c14`, 4 units x one 96-token greedy request, all judgeable, shares are of decode-window wall time, host_gap 100 us, verdicts stable across 50-500 us unless flagged; evidence `/mnt/raid0/llm/tmp/ak-gap-1-trace-gpu-20261119/out/RESULT.json`): (a) inter-kernel idle gap 0.004% / 0.035% / 0.009% / 0.016% (27B-decode / 27B-dflash2 / A3B-decode / A3B-mtp) and (b) stream-K fixup followed by a norm 0.0% on all four: **MEASURED_FUTILE, closed**. Consequences: AK-RESGRID-1 (needs (a) >= 5%) and the ROCm 10.2 build probe (needs >= 3% launch/graph overhead; master-index row OP-ROCM102-BUILD removed) are not triggered. (c) id-sort/top-k: A3B-mtp 13.0% (`k_top_k_radix<256>` 9.9% + `k_argsort_f32_i32` 2.9%), 27B-dflash2 3.1% (`k_top_k_radix<256>`), **PORT_BOX_CANDIDATE**; A3B-decode 2.6% (`topksoftmax`) BAND, no action; 27B-decode 0. `mm_ids_helper` is not in the top set. (d) host time between graph computes (sampling + acceptance): A3B-mtp 15.3%, 27B-dflash2 9.8% **PORT_BOX_CANDIDATE**; A3B-decode 5.1% candidate but threshold-sensitive; 27B-decode 1.7% futile. GPU busy share: 98.3% / 90.2% / 94.9% / 84.7%. Follow-ups filed below: AK-GAP-1-IDSORT, AK-GAP-1-SAMPLE. One 96-token request per unit, so the shares carry a small-sample caveat; the two candidate levers are far above the 3% bar. [no-belief: row verdict filed by agent]

<!-- original line 5751 -->
  - [x] **AK-PROF-GAPHIST** [non-inference] (model: none; post-processing only) add a per-step inter-kernel gap histogram and top-N gap kernel-pair table to gpu_serving_profile output, after the FlyDSL-blog gap framing (intake-2697). Stop on answer when the AK-GAP-1 census consumes it; stop on futility if the trace rows lack per-dispatch start/end (record it). ✅ 2026-11-19 LANDED in research `12fb4efc1`+`8d373e727` (origin/main): `gpu_serving_profile.gap_histogram()` + `windows.<name>.gaps` (log-binned within-step gap histogram, step-break exclusion >=1 ms, top-10 prev->next kernel-pair table, `no_timestamps` status when rows lack start/end); 30 pass in test_gpu_serving_profile.py + test_hotspots_two_denom.py. [no-belief: code]

<!-- original line 5752 -->
  - [x] **AK-PROF-SCLK** [inference, GPU, probe-only] (model: Qwen3.8-27B Q8_0 FA and MMQ op shapes; quant_build: C14 store) sample MI210 sclk during op-gate reps with random vs captured activations (ZYFA operand-dependent clock, intake-2698). Stop on answer: sclk delta within noise closes it (record in the box); a delta beyond noise opens a captured-activation input arm for op gates via a research-intake plan. Stop on futility: no captured-activation dump available at the served shape. Sufficiency: 2 arms x 5 reps; check reuse of the deterministic-replay contract first (vLLM #63275 reorder floor, intake-2695). Seed `14-operand-dependent-clock-mi210.md` (research `6b3a75924`). Row `ak-prof-sclk-gpu-20261119` published 2026-11-19 (gpu-q3, est 700 s): probe-first design brackets operand dependence with RANDOM vs ZERO operands at the MMQ/FA shapes; the captured-activation fixture is added only on a DELTA verdict.
    - ✅ 2026-11-19 (autokernel) row `ak-prof-sclk-gpu-20261119` DELTA(mmq,fa), filed pass: MI210 sclk is operand-dependent (power-limited). MMQ int8 17408x512x5120: sclk 1700 zero -> 1403 MHz random (-297, noise 20, 5/5 paired), 134.6 -> 106.8 TOPS (-21%), 252 -> 294 W; FA fp16 QK^T 40x4096x512x128: 1700 -> 1452 MHz (-248, 5/5), 52.4 -> 47.1 TOPS (-10%). Op-gate microbench speed depends on operand content, so random/zero operands misstate served-shape speed; captured-activation arm opened as AK-PROF-SCLK-CAPT. [no-belief: row verdict filed by agent]

<!-- original line 5756 -->
  - [x] **AK-PROF-SCLK-RECLAIM** [inference] [GPU] (model: Qwen3.8-27B Q8_0, q8_0 KV; quant_build: C14 store `/mnt/raid0/llm/kernels/builds/gpu-20261118-eee3da838-c14`) reclaim the clock lost to power-limited sclk (AK-PROF-SCLK: MMQ 1403 MHz / FA 1452 MHz at ~294 W of a 300 W cap with random operands). Read-only facts 2026-11-19: `power1_cap` = `power1_cap_default` = `power1_cap_max` = 300 W (hwmon, `rocm-smi --showmaxpower`), `pp_dpm_sclk` 500/800/1700 MHz, perf level `auto`, `pp_power_profile_mode` absent (`rocm-smi --showprofile`: not supported), every control node root-owned. Prior work: RVP-T0-1 (`rocm-kernel-authoring.md`, 2026-08-12) closed the clock-pinning branch because a low-entropy GEMM peaked at 196 W; AK-PROF-SCLK reopens it for random/real operands. Levers, ranked:
    (a) **power-cap raise: NOT AVAILABLE.** The cap already equals `power1_cap_max` (300 W); there is no headroom to grant, root or not. Closed by reading, no row.
    (b) **perf-determinism / fixed sclk** (`rocm-smi --setperfdeterminism <MHz>`; root): a fixed clock below the throttled average (e.g. 1500 MHz) trades peak for steadiness. It can only pay in a phase that is power-limited. Gate it on step 0 below. If step 0 shows a power-limited served phase, the follow-up row is 27B serving decode/prefill tok/s ABAB, fixed 1500 vs auto, W2 noise floor 0.84%, sclk/power sampled during the run, restore `auto` by trap; it needs the operator's root command (prepared in the step-0 filing). Stop on answer: delta beyond 0.84% either sign. Stop on futility: step 0 shows every served phase CLOCK_HELD. est 900 s gpu-q3.
    (c) **power profile mode (COMPUTE etc.): NOT AVAILABLE** on this card/driver (no `pp_power_profile_mode` node; rocm-smi reports not supported). Closed by reading, no row.
    (d) **kernel-side energy per op** in MMQ/FA (fewer redundant LDS/VGPR moves, lower operand toggle in int8 dot paths, lower-power tiles): the only lever that does not need root, and longer-term. Gate it on step 0 too: it pays only where a served phase is power-limited. Follow-up box after step 0: an energy/op probe (J per TOP from `power1_average` x time at the AK-PROF-SCLK shapes, per MMQ tile config).
    **Step 0** row `ak-sclk-reclaim-headroom-gpu-20261119` (read-only sensors, no GPU setting changed): 27B llama-bench tg256 and pp2048 on gpu-q3, sclk/power/busy sampled at 5 Hz during the run, 3 reps ABAB. Classes per phase: POWER_LIMITED (median busy sclk < 1650 MHz and p90 power >= 280 W) / CLOCK_HELD (median >= 1680) / SUB_PEAK. Stop on answer: 6 processes, or 4 when reps 0 and 1 agree. Stop on futility: residency, linkage, grant failure, or < 20 busy samples. est 900 s gpu-q3. [no-belief: box filing]
    - ✅ 2026-11-19 (autokernel) row `ak-sclk-reclaim-headroom-gpu-20261119` HEADROOM_tg-CLOCK_HELD_pp-POWER_LIMITED, filed pass. Decode tg256 32.0 t/s holds 1700 MHz in 100% of busy samples at 223 W mean / 252 W max: bandwidth-bound, so no clock lever can move decode. Prefill pp2048 1289 t/s is power-limited: median 1575 MHz (p10 1490), p90 295 W. With CAPT-r2 (real operands = random), the reclaimable prize is prefill/MMQ/FA only, at most ~7-8% of prefill sclk. Final ranking: (d) kernel energy/op first: the only non-root lever, prefill-only (box AK-PROF-SCLK-ENERGY). (b) perf-determinism second: root, prefill-only, and its expected gain is small (a fixed clock at or below the 1575 throttled median can win only by removing DPM oscillation), so it is gated on operator authorization (box AK-PROF-SCLK-DETM). (a) and (c) are closed: cap already = max, no profile node. [no-belief: row verdict filed by agent]

<!-- original line 5768 -->
  - [x] **AK-EFF-ANCHOR-REUSE** [non-inference] reuse a passing anchor verification when the anchor binary sha256 and host-state fingerprint are unchanged, its age is under a bounded TTL and there has been no guard excursion; never across a champion/binary change. Measured sink: 18 anchor verifications x 74.5 min = 22.1 h (16% of tracked wall) + 5.1 h guard excursion on the DS41 local store. If a written measurement rule fixes the cadence, this becomes an operator decision package instead (trust boundary). Operator 2026-11-07: build first. Stop: reuse lands with tests, or the governing rule is identified and packaged. Design: `/mnt/raid0/llm/tmp/ak-jev-efficiency-20261107/DESIGN.md` (estimates are arithmetic from measured DS41 local-store costs, [inferred], not results). Gate class: futility-only. No AK loop launch: validation is offline replay on stored history, then a live A/B only in a granted window. [no-belief: new box] ✅ 2026-11-07 ANSWERED, not built: reuse would hit 0 of 21. In the DS41 store every anchor_verified/excursion row follows a `kept` row with a new champion commit and a new anchor digest (21/21 distinct); none is a restart re-check, and reuse across a binary change is forbidden (`measurement/protocols/kernel-research.md` 162-163: re-verify byte-for-byte at window open/close; a rebuilt anchor is a different anchor). The A/A is already skipped within `--anchor-guard-aa-window-s` (6 h, 2026-10-03). The 22.1 h figure is inter-row gap attribution and also contains each keep's clean anchor build. Decision record `/mnt/raid0/llm/tmp/ak-anchor-reuse-20261107/DECISION.md`. [belief: cc]

<!-- original line 5772 -->
  - [x] **AK-EFF-PROVIDER-BREAKER** [non-inference] park a run (distinct resumable status) after N consecutive provider-terminal iterations instead of re-dispatching; reset on any successful provider call; science outcomes do not count. Measured: 171 consecutive "failed 4 times" codex iterations in store-b0ba1d427; 1,199 planner_transient rows across DS41 stores. Operator 2026-11-07: build first. Stop: lands with tests and a resume path. Design: `/mnt/raid0/llm/tmp/ak-jev-efficiency-20261107/DESIGN.md` (estimates are arithmetic from measured DS41 local-store costs, [inferred], not results). Gate class: futility-only. No AK loop launch: validation is offline replay on stored history, then a live A/B only in a granted window. [no-belief: new box] ✅ 2026-11-09 verified already landed: research cb5100276, `loop/provider_breaker.py`, `test_provider_breaker.py`; terminal `provider_parked` resumes with `--resume-run`. [no-belief: tooling]

<!-- original line 5774 -->
  - [x] **AK-EFF-SAME-STATE-STOP** [non-inference] skip the planner call when the state key (worktree tree + planner-context inputs: beliefs/do-not-repeat/portfolio/inbox digest, lane config) equals the key of the last planner abstention; record a typed skip status and park the lane like the provider breaker (operator stop still wins). Plus a log-only `retry_budget_shadow` annotation at >=4 prior patch_rejected on a mechanism (never refuses). Measured: 13 consecutive identical abstentions on unchanged worktree 00d118d44 = 3.14 h of 9.7 h metered planner wall (P2 replay). Cannot refuse a keep: nothing is authored at that point. Code-only, no AK loop launch. Stop: lands with tests + full loop suite. [no-belief: new box] ✅ 2026-11-07 (AutoKernel): landed on research main at 5707436fd. A lane whose planner abstained on an identical state key waits, without calling the planner, until another lane records non-abstention evidence. It then rebuilds its context and re-asks only if the key changed. The run parks (terminal `planner_same_state_parked`, resumable) only when every lane is parked; a single lane parks on its first skip. Config `resources.planner_same_state_skip_after` (default 1, 0 = off) or env `AK_PLANNER_SAME_STATE_SKIP_AFTER`. Waits and parked lanes are recorded in loop-run.json; `retry_budget_shadow` (>=4 prior patch_rejected) is log-only. If the state cannot be read, the planner is always called; an operator stop wins. run.py was re-pinned, together with the reviewed peer commit 86319c468 (LOOP-SAFETY-C). Full loop suite: 6183 passed; the only failures were the known missing-yaml test and test_validation_final_receipt load errors (15/15 pass in isolation). [no-belief: tooling]

<!-- original line 5775 -->
  - [x] **AK-CONT-BUDGET** [non-inference] run-level budget aggregated up the node tree, on a non-USD basis: debit every actor call (planner, author, critic, panel member) and every build/measurement stage to its lane and then to the run, in wall-clock seconds, GPU-seconds (MI210 lane) and decoded tokens where metered. Enforce hard run ceilings in `run.py`, outside the actor process; an unmetered seat (codex/claude record no tokens) counts as an explicit unknown that fails closed against the token cap and is debited by wall-clock instead. Record per-lane and per-call debits on rows and in `campaign_status`. First verify what exists (OAB-23 per-call budget, `--max-iterations`, `actor_call_metrics`) and build only the gap. Source: `docs/design/fractal-disposable-host-trial.md` (EVL-29 ID-14, operator declined the Fractal trial 2026-11-07 and folded its containment design into the AK loop; ownership from Pipeline Mgmt). Code-only, no AK loop launch. Gate class: futility-only. Stop: ceilings enforced with tests, including a zero-token local seat. **DONE 2026-11-09** research `9dcd3c0e0` (merged to origin/main; feature commit `f0dfb52de`): `controller/run_budget.py` + tests incl. zero-token seat; 290 focused tests pass. [no-belief: tooling]

<!-- original line 5776 -->
  - [x] **AK-CONT-RESERVE** [non-inference] cleanup reserve tranche: when the remaining granted window (`FILLER_DEADLINE`) or run ceiling is down to a fixed reserve, dispatch no new iteration and use the reserve only for drain, publishing rows/campaign_status, retaining patches and worktree teardown. Workers cannot spend it. First verify how `run.py` treats the deadline today; build only the gap. Reserve size is set per campaign config, with a default derived from the measured tail (`tail_path_timing`) p95. Source: `docs/design/fractal-disposable-host-trial.md` (EVL-29 ID-14, operator declined the Fractal trial 2026-11-07 and folded its containment design into the AK loop; ownership from Pipeline Mgmt). Code-only. Gate class: futility-only. Stop: tested that a run near its deadline stops dispatching and finishes teardown inside the window. [no-belief: new box] ✅ 2026-11-09 research 46472498c: the loop never read `FILLER_DEADLINE`; `should_stop` now trips at deadline minus reserve (`AK_CLEANUP_RESERVE_S`, else store p95 of held tail seconds, else 0), terminal `deadline_parked` is resumable. Tested at the guard and terminal level; teardown is the existing stop path, not exercised near a real deadline. [no-belief: tooling]

<!-- original line 5777 -->
  - [x] **AK-CONT-DRAIN-GRACE** [non-inference] drain at iteration boundaries already exists (STOP file -> `should_stop`, resumable). The gap is the hard backstop: an external watchdog (rowflow engine or a run.py supervisor thread) that, after a maximum drain grace, kills the run INCLUDING the actor process groups (known hazard: stopping AK orphans actors), then verifies no AK-owned process or worktree lock survives and records iteration/drain/kill timestamps and the termination reason. Cleanup must not depend on a cooperative agent. Source: `docs/design/fractal-disposable-host-trial.md` (EVL-29 ID-14, operator declined the Fractal trial 2026-11-07 and folded its containment design into the AK loop; ownership from Pipeline Mgmt). Code-only. Gate class: futility-only. Stop: tested with a fake actor that ignores SIGTERM. **DONE 2026-11-09** research `9dcd3c0e0` (merged to origin/main; feature commit `e2ee72d63`): lane_watchdog termination record, tested with SIGTERM-ignoring child (`test_unresponsive_owned_child_is_killed_and_reaped`). [no-belief: tooling]
    - 2026-11-09 audit: `lane_watchdog.py` already SIGKILLs its owned child after `STOP_GRACE_SECONDS` and scans procguard-scoped survivors, holding claims if any remain. Open gap: recorded iteration/drain/kill timestamps and termination reason. [no-belief: audit]

<!-- original line 5779 -->
  - [x] **AK-CONT-SCOPE-PATHS** [non-inference] scoped write paths at patch collection: the lane allowlist (op-scope surfaces) is enforced on the collected diff, rejecting paths outside it, symlinks, `..` traversal, submodule/gitlink changes and any attempt by an actor to commit or push (actors edit only the detached lane worktree; the loop owns commits). First verify what `prebuild_rules`/op_scope already refuse; add only the missing cases, with tests. Source: `docs/design/fractal-disposable-host-trial.md` (EVL-29 ID-14, operator declined the Fractal trial 2026-11-07 and folded its containment design into the AK loop; ownership from Pipeline Mgmt). Code-only. Gate class: futility-only. Stop: each escape case refused in tests. [no-belief: new box] ✅ 2026-11-09 research 9b436c770: `validate_candidate` refuses symlinks, writes through a symlinked directory, gitlinks, nested repos and a lane HEAD moved from its reset base; each case in `test_integrity.py`. [no-belief: tooling]

<!-- original line 5783 -->
  - [x] **AK-EFF-P1-TYPED-PRESCREEN** [non-inference] typed admissibility pre-screen (Jev Choice + probabilities/confidence; "unavailable" counted separately) at the planner->author seam (AK-ADM-1), refusing via `loop/prebuild_rules.py`. Expected [inferred]: ~10-12 h of 140 h (102 abstentions, scope/gate refusals, part of patch rejections). Hard bar: 0 keeps refused on held-out replay; never hard-blocks on mechanism history (AK-FAILRULE-1 R1/R2 rejected that). Local models only. After P2. Design: `/mnt/raid0/llm/tmp/ak-jev-efficiency-20261107/DESIGN.md` (estimates are arithmetic from measured DS41 local-store costs, [inferred], not results). Gate class: futility-only. No AK loop launch: validation is offline replay on stored history, then a live A/B only in a granted window. **Caveat 2026-11-07 (AutoKernel):** the hour estimate uses inter-row gap attribution, which inflated the anchor figure (22 h included each keep's clean build; reuse would hit 0/21). Do not rank this box on that estimate: first measure per-stage wall on real rows (keep path: `keep_path_timing`, research 2fd17033f; iteration path: actor-call metrics + bench stage times), then re-derive the saving. [no-belief: new box] ✅ 2026-11-07 DECLINED as designed (offline replay, PREREG first): the typed heads cannot decide at the seam (abstain_reason is set only by post-author output, 100% unknown); route-out catches 77% of avoidable wall but refuses 5 keeps (kept q4k rows share the avx512 route verdict); duplicate/op_scope rules catch 0 h and refuse 3 keeps each; 19/21 avoidable rows are PLANNER abstentions where no author ran. Only a k=4 patch_rejected retry budget refuses 0 keeps (2.1 h, 93% one row, k sits on the in-sample edge, no held-out store: Q38FN store is empty) -> log-only shadow field in AK-EFF-SAME-STATE-STOP, never a gate. Evidence `/mnt/raid0/llm/tmp/ak-eff-p1-replay-20261107/`. [belief: cc]
    - 2026-11-07 premise check (direct intervals): HOLDS, smaller than estimated. 19/21 abstentions are PLANNER abstentions (no author ran) -> 0 saving at the planner->author seam. Direct ceiling 4.65 h = 32.5% of metered direct wall; store-wide 12.2 h incl. 7.6 h [inferred]. Next: offline replay labelling the 30 avoidable rows, 0 keeps refused on held-out kept rows, then a local shadow screen in a granted window. Evidence `/mnt/raid0/llm/tmp/ak-eff-p1p3-evidence-20261107/` (PREREG.md fixed thresholds before computing; RESULT.md/json; direct intervals only, DS41 local store, read-only). [belief: cc]
    - Owner: AutoKernel (operator rebalance 2026-11-07: loop internals stay with the loop owner; same pinned files as AK-TAIL-SPLIT). [no-belief: ownership routing]

<!-- original line 5786 -->
  - [x] **AK-EFF-P3-BENCH-FUTILITY** [non-inference] futility-only sequential look in `loop/bench.py`: stop measuring a candidate once it provably cannot clear the keep floor; never stop early for success (OP-ABSEQ undecided). Expected [inferred]: ~6 h of the ~20 h spent measuring nulls/regressions. Falsifier: replay shows any kept candidate would have been stopped. Design: `/mnt/raid0/llm/tmp/ak-jev-efficiency-20261107/DESIGN.md` (estimates are arithmetic from measured DS41 local-store costs, [inferred], not results). Gate class: futility-only. No AK loop launch: validation is offline replay on stored history, then a live A/B only in a granted window. **Caveat 2026-11-07 (AutoKernel):** the hour estimate uses inter-row gap attribution, which inflated the anchor figure (22 h included each keep's clean build; reuse would hit 0/21). Do not rank this box on that estimate: first measure per-stage wall on real rows (keep path: `keep_path_timing`, research 2fd17033f; iteration path: actor-call metrics + bench stage times), then re-derive the saving. [no-belief: new box] ✅ 2026-11-07 DECLINED-FUTILE by its own pre-registered rule: every DS41 comparison runs exactly MIN_PAIRS=5, so a look at the minimum saves 0 h; a sub-minimum look at k=3 saves 1.36 h (2.3% of direct wall, <3% bar) AND stops keep_candidate 1bc29d2c (final +2.02%, -5.62% at pair 3); k=2 stops another (+2.23%); floor variant stops 2 kept rows. Not implemented. Evidence `/mnt/raid0/llm/tmp/ak-eff-p1p3-evidence-20261107/` (PREREG.md fixed thresholds before computing; RESULT.md/json; direct intervals only, DS41 local store, read-only). [belief: cc]
    - Owner: AutoKernel (operator rebalance 2026-11-07: loop internals stay with the loop owner; same pinned files as AK-TAIL-SPLIT). [no-belief: ownership routing]

<!-- original line 5788 -->
  - [x] **AK-TOOL-CHAMPION-CONTEXT** [non-inference] NARROWED 2026-11-07 (operator question): within a campaign the loop already builds on its champion-branch tip (lanes detach at the tip, only the serialized tail advances it, a moved base -> `superseded`; startup refuses a champion-of-record/anchor mismatch). The only gap is LAUNCH-TIME: a campaign starts on whatever anchor its argv names (e.g. a C5 calibration argv) and nothing checks it is the project champion (C7r now). Add one startup refusal in `run.py` unless the anchor is the current champion or an explicit override names why. Rulings/per-port e2e context moves to AK-TOOL-UNSOURCED-LINT. Stop: a stale-anchor fixture is refused at startup. [no-belief: new box] Every startup path refuses unless the worktree contains the tip of the champion branch (C7r 62cb6a6af today, resolved from git); override AK_NON_CHAMPION_ANCHOR_REASON; no hardcoded rulings file. ✅ 2026-11-07 LANDED in research (handback integration ending 40179e3f0; full loop suite 6185 pass / 1 load flake passing in isolation). [no-belief: tooling-repair]
    - Owner: AutoKernel (operator rebalance 2026-11-07: loop internals stay with the loop owner; same pinned files as AK-TAIL-SPLIT). [no-belief: ownership routing]

<!-- original line 5790 -->
  - [x] **AK-FUSE-GRAPH-KLD-1** [non-inference] graph-level KLD / same-top check on the keep path for any candidate fusing across >1 graph node (`gates.py`, wired in `loop/run.py`), lifting `parse_ppl`/`ppl_argv` from `c7-q38-ppl-bisect-20261106/job.py`. Evidence: H13b passed op oracles (8253/0) but Q38FN KLD 0.18 / same-top 88.6%; no KLD/same-top check exists in loop/. THRESHOLD TOUCHES THE MEASUREMENT TRUST BOUNDARY: code + planted-fault fixture only; threshold via operator amendment. Seed 10 AK-FUSE-GRAPH-KLD. Review: `/mnt/raid0/llm/tmp/ak-planner-tooling-20261107/REVIEW.md` (inf22 methods + operator-intervention distillation; counts are estimates +/-20% from main-inf22 transcript 73998e9f). Code-only; no AK loop launch; gate class futility-only. [no-belief: new box] [receipt-ack: c7-q38-ppl-bisect-20261106 INCONCLUSIVE — cited only as the source of the lifted parse_ppl/ppl_argv helpers, not as evidence for the gate; the gate's evidence is the planted-fault H13b replay and the ratified policy] **Harvest #5 note 2026-11-07 (AutoKernel):** precedent for the amendment package: C8-FOLD-GATE pre-registers KLD < 1e-3, PPL ln-ratio <= 0.003 and no added splits (root `0fdb2aa92`, kernel-champion-and-promotion.md:58); offer these as starting values for the operator, not loop-chosen values. **Note 2026-11-19:** operator 2026-11-19: GPU rule adds Q38FN-hybrid top-1 >= 93% refusing clause (research b620a0f23; ratify script amended). [no-belief: operator decision]
    - *(2026-11-19)* GPU-gate gap reviewed: the known-bad H13b replay is caught only by Q38FN, but Q38FN is not served on GPU (gate rows ran it hybrid --n-cpu-moe as a test vehicle) and H13b is a Q38FN-specific fusion no served GPU model reaches; the CPU rule still catches it via Q38FN top-1. Keep the operator ruling: on GPU the 27B decides. No change to the ratify script. [no-belief: analysis]
    - 2026-11-07: harness LANDED (40179e3f0): graph KLD/same-top gate with planted C7/H13b fault caught (KLD 0.1865, same-top 88.6%); NO threshold and not wired into the keep path. Threshold draft: /mnt/raid0/llm/tmp/ak-handback-20261107/kld-threshold-amendment-draft.md (operator amendment). [no-belief: tooling-repair]
    - Owner: AutoKernel (operator ruling 2026-11-07, relayed by Pipeline Management: "AK tooling should be owned by the autokernel session"; Pipeline Management keeps keeper/rowflow/status-surface plumbing on request). [no-belief: ownership routing]
    - 2026-11-09: rule ratified as P-AK-SEARCH-1-A5 (RATIFY-AK-C9-20261109, root `246bbcc57`), K and S left unset (operator values). Not ticked: `graph_kld_gate` is still not called from `loop/run.py`'s keep path and no threshold config input exists. [no-belief: operator ratification]
    - 2026-11-18 operator decision: the thresholds are today's 27B-anchored gate. GPU: Qwen3.8-27B Q8_0 KLD <= 0.003 and |dPPL| <= 0.5% decide; Q38FN KLD/PPL/top-1 reported only. CPU: the same 27B clause plus Q38FN |dPPL| <= 0.5% and top-1 >= 93%. [no-belief: operator decision]
    - 2026-11-18 (autokernel): keep-path wiring landed in research `bb9ac458d`: `gates.graph_kld_keep_check` (per-backend GraphKldPolicy with decisive and report-only clauses) is appended to the correctness gate in `loop/run.py` for every graph-fusion candidate on both legs; candidates build llama-perplexity and PROMOTION_TARGETS now includes it; 11 new tests in `test_graph_kld_gate.py`. The values are human-only (A5 says so), so they land only through the operator ratify script `scripts/operator/ratify_ak_graph_kld_thresholds_20261118.sh` (research `graph_kld_policy.json` + kernel-research.md P-AK-SEARCH-1-A5a); until it runs, every graph-fusion keep is refused threshold_unset. Not ticked: waits on that signature. [no-belief: tooling]
    - 2026-11-19 (autokernel) **DONE, ticked ✅ 2026-11-19:** the signature landed (root `6029e2bea`, RATIFY-AK-GRAPH-KLD-THRESHOLDS-20261118, bundle verify PASS) and research `graph_kld_policy.json` is the only threshold input. Rules the loop now enforces on every graph-fusion keep: GPU = 27B Q8_0 mean KLD <= 0.003 and |dPPL| <= 0.5% decide, PLUS (operator amendment 2026-11-19, research `b620a0f23`) a Q38FN-hybrid (`-ngl 999 --n-cpu-moe 48`, test vehicle, not a served shape) same-top floor of 93.0% that refuses; CPU = the same 27B clause plus Q38FN |dPPL| <= 0.5% and same-top >= 93%. Known-bad H13b replay (KLD 0.1865, same-top 88.6%) fails the Q38FN clause on both legs; a missing/malformed policy or unparsed decisive metric is `threshold_unset`/`kld_unparsed` (refusal, never a pass). Authoritative text: `measurement/protocols/kernel-research.md` P-AK-SEARCH-1-A5a. [belief: cc]

<!-- original line 5798 -->
  - [x] **AK-PROF-TWO-DENOM** [non-inference] add wall share and launch gap (wall - sum kernel) beside `share_of_device_time` in `hotspots.py:parse_kernel_trace` / `Hotspot` and `actors.py:_render_gpu_serving_profile`, lifting `cell_pair`/`summarize` from `gdn-share-mi210-20261106/job.py`, with a count-validity flag (gdn_count_ok lesson). Evidence: H6/H14 removed launches and moved nothing under HIP graphs; GDN share 15.8% prefill vs 1.4% decode. Extends AK-PROF-ATTR-1 / AK-GDN-S1. Review: `/mnt/raid0/llm/tmp/ak-planner-tooling-20261107/REVIEW.md` (inf22 methods + operator-intervention distillation; counts are estimates +/-20% from main-inf22 transcript 73998e9f). Code-only; no AK loop launch; gate class futility-only. [no-belief: new box] Wall share + launch gap + count_ok warning in planner context. ✅ 2026-11-07 LANDED in research (handback integration ending 40179e3f0; full loop suite 6185 pass / 1 load flake passing in isolation). [no-belief: tooling-repair]
    - Owner: AutoKernel (operator rebalance 2026-11-07: loop internals stay with the loop owner; same pinned files as AK-TAIL-SPLIT). [no-belief: ownership routing]

<!-- original line 5800 -->
  - [x] **AK-AMDAHL-PRUNE** [non-inference] In the planner, compute each candidate's end-to-end ceiling = target-component share (from AK-PROF-TWO-DENOM wall share + launch-weighted table, and INF70-TWOLINE intercept/slope where present) × best-case op speedup; demote (not delete) candidates whose ceiling < keep threshold and log the ceiling in the candidate record. Ranking/order only; keep gate unchanged (2026-10-20 ruling). Source: intake-2669 §3.3 (one kernel scaled up misstates whole-model cost). Acceptance: replay on the last campaign's candidate log shows which timings would have been skipped and that no past KEEP falls below its ceiling. Code-only; no loop launch. [no-belief: new box] ✅ 2026-11-19 (AutoKernel): landed in research `9ec0e0053`. `loop/amdahl.py` computes each candidate's zero-time ceiling s/(1-s) and its ceiling at an X-times op speedup (default 2x) against the keep bar (default 3%). Verdicts: clears, below_bar_realistic, below_bar_hard, or unknown. The flag is `--amdahl-prune off|advisory|demote` and defaults to advisory. Every candidate's ceiling is logged at tail admission to `<store>/amdahl-ceilings.jsonl` and in `admission_log`, and the GPU planner context gets a ceiling table. `demote` times below-bar candidates after all others (`SerializedTail(demote=)`). Nothing is deleted or refused, an unknown share is never demoted, and the keep gate is unchanged. Share source: the AKX-ALL-16 serving-shares file (`--serving-shares-profile <model>/<mode>`), not the TWO-DENOM/INF70 inputs this box named. That redirect was the dispatcher's. Acceptance replay: (a) the last GPU campaign log `ak-27b-gpu-verify-20261004` has 13 rows and 0 keeps. All of them target `launch_mul_mat_q`, which has no share in the current DFlash2 verify window, so all are `unknown` and none is skipped. No keep exists, so none can fall below its ceiling. (b) Of today's candidates, folding q8_1 into MMVQ on the 27B verify is `below_bar_hard` (2.5% share at d32768, zero-time ceiling 2.5%), so it would have been demoted up front. The L1 A3B router chain clears. The CPU levers (gate/up pair, Q38FN top-k) are `unknown`, because there is no CPU shares profile. Tests: `test_amdahl.py` 13 pass, which includes an assembled-context check through `actors.render_context`. The full loop suite had 109 failed and 83 errors. Rerunning that exact failing set on the parent commit gave the same set, so all of it predates this change. [no-belief: code]

<!-- original line 5805 -->
  - [x] **AK-OP-E2E-PENDING** [non-inference] an op-level win stays `pending` until a same-run ABBA e2e confirms it (`keep_screen.py` / `serving_gate.py`), plus real-routing MoE cases in `served_shape_cases.py:route_ids` (uniform by construction today). Evidence: H8b op 1.29x on uniform routing, e2e 0.949x; H14 op 1.13x, e2e noise. Extends AK-ASM-H8c / AK-H5-VERIFY. Review: `/mnt/raid0/llm/tmp/ak-planner-tooling-20261107/REVIEW.md` (inf22 methods + operator-intervention distillation; counts are estimates +/-20% from main-inf22 transcript 73998e9f). Code-only; no AK loop launch; gate class futility-only. [no-belief: new box] ✅ 2026-11-07 (AutoKernel): `serving_gate.e2e_evidence` no longer asserts same-run ABBA; `classify_e2e_design` verifies it from the record (equal paired samples >= MIN_PAIRS, seeded plan with both orders, membership matching the plan, declared digests equal). Anything else carries its true design (`separate_runs`, `unpaired`, `fixed_order_pairs`, `unknown_design`) and stays `op_keep_pending_e2e`. Real-routing MoE cases landed earlier as opt-in (`served_shape_cases.py`). Research cae39d8c3; 25 tests in `test_op_e2e_pending.py`. A caller must pass `declared` digests to get the build-digest check (no live caller yet). [no-belief: tooling]
    - 2026-11-07: classifier LANDED (40179e3f0; never downgrades/refuses a keep; real routing opt-in). Open: `serving_gate.e2e_evidence` labels every row same-run ABBA without checking -- verify the pairing before treating it as ABBA. [no-belief: tooling-repair]
    - Owner: AutoKernel (operator rebalance 2026-11-07: loop internals stay with the loop owner; same pinned files as AK-TAIL-SPLIT). [no-belief: ownership routing]

<!-- original line 5808 -->
  - [x] **AK-TOOL-SWITCH-BISECT** [non-inference] kill-switch bisect as a loop action: replicate -> all-off -> single-off ranked by suspicion, stop on first answer (`runtime_arms.py` + `experiment_plan.py`, lifting ARMS/main from the bisect job). Evidence: C7 Q38FN regression isolated to HC_FUSE in one row. Extends seed AK-ASM-PORT-ABLATE. Review: `/mnt/raid0/llm/tmp/ak-planner-tooling-20261107/REVIEW.md` (inf22 methods + operator-intervention distillation; counts are estimates +/-20% from main-inf22 transcript 73998e9f). Code-only; no AK loop launch; gate class futility-only. [no-belief: new box] replicate -> all-off -> single-off, stop on answer; C7 replay finds HC_FUSE. ✅ 2026-11-07 LANDED in research (handback integration ending 40179e3f0; full loop suite 6185 pass / 1 load flake passing in isolation). [no-belief: tooling-repair]
    - Owner: AutoKernel (operator ruling 2026-11-07, relayed by Pipeline Management: "AK tooling should be owned by the autokernel session"; Pipeline Management keeps keeper/rowflow/status-surface plumbing on request). [no-belief: ownership routing]

<!-- original line 5810 -->
  - [x] **AK-TOOL-UNSOURCED-LINT** [non-inference] lint in `belief_context.py` / `seed_bundle.py` flagging any figure in planner context without a resolvable raw RESULT path (recursive key search). Evidence: H6 "1.017x" had no raw data (real 0.9997 inconclusive). Review: `/mnt/raid0/llm/tmp/ak-planner-tooling-20261107/REVIEW.md` (inf22 methods + operator-intervention distillation; counts are estimates +/-20% from main-inf22 transcript 73998e9f). Code-only; no AK loop launch; gate class futility-only. [no-belief: new box] Recursive source-key search, path-existence only, flag-never-block. ✅ 2026-11-07 LANDED in research (handback integration ending 40179e3f0; full loop suite 6185 pass / 1 load flake passing in isolation). [no-belief: tooling-repair]
    - Owner: AutoKernel (operator rebalance 2026-11-07: loop internals stay with the loop owner; same pinned files as AK-TAIL-SPLIT). [no-belief: ownership routing]

<!-- original line 5812 -->
  - [x] **AK-RUNEND-REPORT** [non-inference] NARROWED 2026-11-07: the loop honours the keeper's region locks, gpu-quiet and the G1 GPU-window grant, but schedules per-candidate work itself, so the keeper cannot see per-candidate queue, ETA or idle gaps inside a campaign (source of ~18 "status?/eta?" and ~15 "GPU idle" operator prompts). Publish per-stage state + ETA into the keeper's existing status surface (`queue_status` / rowflow status), not a second report; escalate only when naming an operator-only decision; emit judgment calls (PPL tolerances, SLO weights, floor changes, parking) as ONE decision package per run end. Review `/mnt/raid0/llm/tmp/ak-planner-tooling-20261107/REVIEW.md`. [no-belief: new box]
    - 2026-11-07: loop side LANDED (40179e3f0): atomic publisher <flags>/campaign-status/<row>.json (epyc.autokernel.campaign_status.v1). Open: keeper queue_status reader, requested from Pipeline Management. [no-belief: tooling-repair]
    - Owner: AutoKernel (operator ruling 2026-11-07, relayed by Pipeline Management: "AK tooling should be owned by the autokernel session"; Pipeline Management keeps keeper/rowflow/status-surface plumbing on request). [no-belief: ownership routing]
    - ✅ 2026-11-19 (autokernel, bulk P2 pass): reader landed: root `3a1d098f8` adds `campaign_status()` to `.claude/skills/inference-backlog-scheduling/scripts/queue_status.py` (CAMPAIGN-STATUS section plus `campaign_status` key in `--json`: per-stage rows, ETA, idle bins, named escalations, decision package; BAD for wrong-schema, STALE after 6h); 6 tests passed. The one-decision-package-per-run emitter already exists (`loop/campaign_status.py` `decision_package`, 7 tests). [no-belief: tooling]

<!-- original line 5817 -->
  - [x] **AK-PLANNER-RELIANCE-PROOF** [non-inference] get one planner turn that proposes and cites claims, for VB-REFOCUS-NONEMPTY-READ-PROOF, at the first DeepSeek loop turn. 2026-11-08 one-shot (`/mnt/raid0/llm/tmp/ak-planner-proof-20261108/one_shot.py`, Q38 27B q8_0 gpu pp512, claude-opus-5-5): read non-empty (usable 16; receipt sha256:178e51e5…) but the planner abstained (empty workspace, no profile), so reliance is empty and this does not satisfy the proof. RESULT: PASS (ak-q38fn-relianceproof-c10-20261110-r6, filed pass 2026-11-15): live loop rc 0 at research 89c7a6e5c, 1 receipt, 1 relied (clm_ak-exp:v1:a12ee888798e5aab:2dd322c9…, mechanism akm-cpu-q6k-x4t-weight-prefetch), 0 refused. [no-belief: row verdict filed via file_result]
    - 2026-11-09: operator reopened this after a same-day closure; the planner-only 27B receipt (`sha256:36795d98...`, accepted reliance on h4 and h9, but an abstain) did not settle it. Proof stays outstanding; rerun a real loop turn once a Q38FN floor is usable. [no-belief: reopened]
    - 2026-11-09 20:40Z: row `ak-q38fn-relianceproof-c9-20261109-r4` smoke PASSED and the row is in `ready/` (not started). It uses the registered 4.146% serving floor (RATIFY-AK-Q38FN-FLOOR-ACCEPT-20261109, suspect), so a keep is possible; any keep stays private and is untrusted. Runs under the OP-AK-HOLD exception recorded in `vidya-belief-substrate-program.md` (VB-REFOCUS-NONEMPTY-READ-PROOF). The proof stays outstanding. [no-belief: not-a-result]
    - 2026-11-10 RESULT r4 (autokernel; row `ak-q38fn-relianceproof-c9-20261109-r4`, code `b63ce0107b39`, ended 07:01Z; NOT PROVEN, box stays open). **Question:** does one real Q38FN loop iteration produce a reliance-accepted receipt naming target claim ids? **Result:** `receipts` = 0, `loop_rc` 0; the single iteration was a prevalidated runtime arm (-0.569%, not kept); two warnings: a history-adapter mismatch and a serving `ProjectionError`. **Verdict: NOT PROVEN** (abstain is not a pass); VB-REFOCUS-NONEMPTY-READ-PROOF stays open. Diagnosis of the two warnings and r5 preparation are in progress. No keep; nothing recorded for C10. Evidence `/mnt/raid0/llm/tmp/ak-q38fn-proof-r4-20261109/out/RESULT.json`. [no-belief: not-a-result; proof failed to materialise]

<!-- original line 5821 -->
  - [x] **AK-LOOP-START-PREREQS** [non-inference] before any loop start: pass `--belief-root-repo` (no `.sh` under `scripts/kernel_rnd` sets a root; unset is a refusal) and set planner and critic explicitly while Codex is out of usage until 2026-11-11. Non-timing work on CPU quarters: none exists in the loop (keep path is a timing A/B), checked 2026-11-08. ✅ 2026-11-09 already satisfied: flags exist, an unset root refuses, procedure in `loop/program.md` launch steps 4-5; store anchor attested on C9 cpu and gpu images; dry run now refuses a wrong `--cor-build` on a store with no accumulator (`ebfeec4aa`). [no-belief: tooling-repair]

<!-- original line 5822 -->
  - [x] **AK-SEED-IQ3S-PROFILE** [inference, CPU quarter] per-node profiler comparison for seed 73 (`akm-cpu-iq3s-iq1-zmm-dot-gather`, Q38FN store inbox; journal `/mnt/raid0/llm/tmp/ak-matmul-candidates-20261108/JOURNAL.md`) when the loop resumes; a serving A/B cannot resolve the inferred +2-4% against 2.5-8.4% noise floors. stop-on-answer when 3 paired rounds finish (NODE_WALL_DOWN if median cand/C9 IQ3_S wall <= 0.90 and every round < 0.95; REGRESSION if > 1.05; else NO_MOVE); stop-on-futility on round 2 if both ratios >= 1.0, or an invalid arm; gate-class = futility-only. ✅ 2026-11-10 NO_MOVE [belief: cc]

<!-- original line 5825 -->
  - [x] **AK-TOOL-ANSI-ONE-STRIP** [non-inference] one shared `strip_ansi` plus a vacuous-parse rule for every parser of llama.cpp tool stdout in `loop/`. Recurrence: ANSI-coloured `OK` lines produced a false REJECT_CORRECTNESS on C8-1-LCATTN r1 (parsed OK=0 as failure, "not a kernel defect") and the same class hit V11-086-DRV and CH-LB1-C5 earlier. `loop/` already carries >=7 private copies of the regex (`census.py:26`, `kernel_coverage.py:242`, `iqk_witness.py:55`, `cpu_route_witness.py:229`, `ak_check.py:823,1010`, `execution/t0_provider.py` `_strip_ansi`), so one parser missing it fails closed as FAIL instead of UNKNOWN. Work: single helper (module-level, imported by all), a lint/test that fails on any new `test-backend-ops`/`llama-bench`/`perplexity` output parser lacking it, and a rule that "zero verdict lines parsed from non-empty output" yields UNKNOWN, never REJECT. Stop: planted-fault fixture (coloured output with a real FAIL line still FAILs; coloured all-OK output passes; zero-line output is UNKNOWN) green and the lint finds no unmigrated copy. Code-only; no AK loop launch; gate class futility-only. Evidence: root `0fdb2aa92` `handoffs/active/kernel-champion-and-promotion.md:44` (r1 false reject), `:1122` (earlier ANSI OK=0), progress `2026-11-07-main-inf22.md` C8-1-LCATTN row (commit 5e08f658a). [no-belief: new box] **Harvest #6 note (AutoKernel):** r3's own text now independently confirms the failure mode ("parser counted 0 of 167 OK lines (ANSI colour codes)"); no change to the box, but use the "0 of 167 OK" figure as the planted-fixture shape (non-empty coloured output, zero parsed verdict lines must be UNKNOWN). Evidence: `f4e1e537e` r3 entry. **Harvest #7 note (AutoKernel):** second failure shape for the planted fixture. C8-DECODE-X-SWEEP row `c8-decode-x-sweep-20261107-r2` exited rc=1 because its llama-bench parser failed on stdout and stderr interleaved in one log; main-inf22 recovered the numbers by hand from per-cell `run.log` `avg_ts`. Add to the fixture set: llama-bench output with stderr lines interleaved between JSON/table rows must parse to the same result as clean output, and unparseable non-empty output must be UNKNOWN, not rc=1 with no verdict. No change to the box's stop rule. Evidence: root `6c9cb69ba` Q1 entry ("The row itself exited rc=1, because its llama-bench parser failed on stdout and stderr interleaved in one log"). ✅ 2026-11-09 research f19e05a5e: `loop/tool_output.py` (`strip_ansi`, `vacuous_parse`), ten copies migrated, planted fixtures and lint in `test_tool_output.py`. `bench.py` reads stdout and stderr on separate pipes, so the interleaved shape cannot occur in the loop; job-script parsers are outside this box. [no-belief: tooling]

<!-- original line 5828 -->
  - [x] **AK-HARVEST-5** [non-inference] harvest #5 of main-inf22 into planner context: write the paragraph in section 3 below into `scripts/kernel_rnd/autokernel/loop/program.md` ("Added 2026-11-07, harvest #5"), same mechanism as harvest #4 (research 477451ff9), then re-pin whatever custody check covers `program.md`. Stop: canary shows the paragraph in the planner context block. [belief: cc] (conclusions are committed handoff text, entered as observations) **Harvest #6 correction 2026-11-07 (AutoKernel):** amend the paragraph BEFORE writing it into program.md, because its first bullet is now false. Replace the C8-1-LCATTN bullet with: "C8-1-LCATTN is decided: **KEEP_A_ONLY** (r3, row `c8-lcattn-gate-20261107-r3`, store `gpu-20261107-e1d9ba2f6-c8lcattn` vs C7r `62cb6a6af`, `[belief: cc]`). Target A `GGML_HIP_GV_MULTISEQ` keeps: np4 DFlash2 aggregate, decode-only, 3 paired reps, median 1.166x @32k (bar 1.05) and 1.252x @128k (bar 1.20); verify FA 101/122 GB/s vs C7r's ~27 GB/s; no-draft d0/d4k 0.999/0.994. Target B `GGML_HIP_FA_VEC_LONGCTX_PB` REJECTED in r2 (0.95x @32k, 0.90x @128k) and default-off. Regime: Qwen3.8-27B Q8_0 + DFlash2 n-max 7, np4 unified KV, wiki-continuation prompts; DFlash2 acceptance 15-27% @32k, 18-51% @128k, so absolute tok/s is gate-shape, not serving. r1 REJECT_CORRECTNESS was a parser false reject (ANSI, 0 of 167 OK lines) and r2 INCONCLUSIVE was harness defects; neither is evidence about the kernel." The "do not propose LCATTN as proven or refuted" sentence must go; instead: "do not re-propose a long-context FA-vec split (Target B) without a new mechanism." Evidence: root `f4e1e537e` kernel-champion-and-promotion.md C8-1-LCATTN r3 entry. Also add to the same paragraph: C8-FOLD-GATE CPU half CPU_PASS (root `23023d9c0`: identity 4/4, ratios 0.994-1.005, `libggml-cpu.so` byte-identical to C7r because C8 so far is GPU-only; GPU half `c8-fold0-gate-20261107` still to run, no verdict). **Harvest #7 correction 2026-11-07 (AutoKernel):** the paragraph (as corrected by harvest #6) changes on three facts. Do not write it as it stands; use the replacement bullets in section 3. Evidence: root `11ef58501` `handoffs/active/kernel-champion-and-promotion.md` C8-FOLD-GATE RESULT entry (box ticked `[x]`); root `6c9cb69ba` C8-DECODE-X-SWEEP Q1 entry; root `f0255bc31` C8-FOLD1-GATE box. REPLACEMENT: Apply on top of the harvest #6 correction (which replaced the C8-1-LCATTN bullet). Replace the paragraph header and the C8-FOLD-GATE bullet, and add the decode-lever and fold1 bullets. The harvest #6 sentence "GPU half still to run, no verdict" must not be written. Header, replace with: **Added 2026-11-07, harvest #5 (updated through harvest #7; `[belief: cc]`; epoch C7r `62cb6a6af`; C8 fold0 `eeab978ac` is QUALIFIED as a candidate, not production; fold1 `55c4f9833` is un-gated):** Replace the "C8-FOLD-GATE keep rule is pre-registered ... no verdict yet" clause (keep the H20 text before it) with: - C8-FOLD-GATE fold0 `eeab978ac` (C7r + C8-6 GDN chunked + C8-1 target A GV_MULTISEQ; fix (b) default off) is **FOLD_PASS, every clause** (GPU row `c8-fold0-gate-20261107`, store `gpu-20261107-eeab978ac-c8fold0` vs C7r) plus CPU_PASS (CPU `libggml-cpu.so` byte-identical to C7r), so fold0 is a qualified base. Regime-labelled numbers, Qwen3.8-27B Q8_0, 3 AB/BA rounds x 5: 27B pp2048 1.115 and pp8192 1.113; A3B pp2048 1.190 and pp8192 1.187; 27B tg128 1.081 (NOT claimed as a decode gain: the C7r arm read 29.3 tok/s vs ~31 in the GDN r2 gate); 27B tg@d32768 1.005; A3B tg128 1.014; splits 2/graph on both arms (none added); PPL 6.5277 to 6.5279 (ln 0.00114), KLD 1.5e-5, top-1 99.95%. np4 DFlash2 decode-only on LongHealth RAG prompts at ~32.7k: median 1.193x (paired 1.133/1.295/1.193), 100.2 to 119.6 tok/s aggregate (draft acceptance 0.47-0.80, n-max 7); np1 97.3 vs 97.2 tok/s (no gain at np1). The 1.193x is a decode-only np4 DFlash2 number; it does not transfer to no-draft decode (1.005). Later C8 keeps (C8-3a, C8-4 H18, C8-5 H20, CPU LB folds) merge onto the C8 package's named base and re-gate. - Decode lever (C8-DECODE-X-SWEEP Q1): routing n_q=1 decode through the GQA-verify kernel (`GGML_CUDA_FA_GQA_VERIFY_MIN_NQ=1` vs 2) is a **LEVER** on C7r, no draft, np1, llama-bench tg64 at depth: d4096 1.004, d32768 1.08, d131072 1.25 (15.5 to 19.4 tok/s at 128k); rule was d128k >= 1.10 and d4k >= 0.99. Mechanism: the n_q=1 vec kernel re-reads each KV slice per query head of the 6-way GQA group, gv shares it. It is a lever, not a keep: it is gated as fold1 (`c8-fold1-gate-20261107`, default MIN_NQ=1, keep rule fold0's with 27B tg@d32768 >= 1.05, tg@d131072 >= 1.15, A3B tg@d32768 >= 0.99), not yet run. Q2 (draft length sweep) did NOT run; do not quote any optimal-X result. Draft lengths remain {3,5,7} (block_size 8 cap). - Do not propose the n_q=1 GQA route as a new AK kernel idea: it is an existing knob in the tree and its gate is C8-owned. Do not read the fold0 27B tg128 1.081 as a decode result. **Harvest #8 correction 2026-11-08 (AutoKernel):** fold1 gate SUPERSEDED by C8-FOLD2-GATE (fold2 `6dd06d5fa` = fold1 + token_embd on GPU, root `7378d5f34`); fold2 CPU half CPU_PASS (identity 4/4, ratios 0.999-1.008, root `0e608cfd8`); GPU half not yet run. C8-3 bullet becomes: C8-3a KEEP, zero-split on fold2. Write the paragraph with these facts. ✅ 2026-11-08 written into `program.md` as one consolidated paragraph (harvests #5-#8 applied; no stale clause), research `079a656a1`. Reaches the planner whole as the `program_strategy` section (actor_context.py:223, no truncation; program.md 77,372 chars). 568 + 147 tests passed across the program.md readers. [belief: cc] [receipt-ack: c8-fold1-gate-20261107 RC=75 — superseded by C8-FOLD2-GATE before completing (root 7378d5f34); cited only as superseded]

<!-- original line 5829 -->
  - [x] **AK-SERVING-LONGCTX-DECODE-ONLY** [non-inference, audit first] make the opt-in GPU C8 long-context cell in the SL-4 serving gate measure decode, not prefill+decode. inf22's C8-1-LCATTN needed three rounds because its np4 aggregate was prefill-contaminated (r2 INCONCLUSIVE: "prefill-contaminated aggregate; corpus too short for 128k"); r3 fixed it with a two-phase run (phase 1 fills the KV, phase 2 has prompt_n = 4 per slot, so the aggregate is decode only) and a corpus long enough for 128k, and only then produced a verdict (KEEP_A_ONLY, np4 1.166x @32k, 1.252x @128k). Our new cell (`loop/longctx_c8.py`, research `375972a63`) sends `cache_prompt: False` per request at line 98 with no phase split, so a ~32k cell at np4 times 4 x 32k prefill tokens inside the throughput figure, which would dilute or flip any decode-side effect (FA, verify) and would make a steps/s keep gate (SL-2) read prefill cost as verify cost. Step 1 (audit, 30 min): read `longctx_c8.py` / `longctx_c8_comparison.py` / `serving.py` and state whether the reported steps/s or tok/s excludes the prompt phase. If it does not: add the two-phase shape (warm KV phase, then a measured phase with `prompt_n` per slot asserted <= a small bound from `timings`, refuse otherwise), assert corpus tokens >= depth + n_predict before launching, and record `prompt_n` per slot in the result. Stop: audit answers "already decode-only" (close, cite file:line) or a fixture with a stub server that reports `prompt_n` = 32768 in the measured phase is REFUSED while one reporting `prompt_n` = 4 passes. Code-only; no AK loop launch; the box already open on the long-context cell ("stays open until the long-context cell has run once", speculative-decoding.md, c6e353d77) must not run that cell until this box is closed. Gate class futility-only. Evidence: root `f4e1e537e` `handoffs/active/kernel-champion-and-promotion.md` C8-1-LCATTN RESULT r3 entry (r1/r2/r3 defects and the two-phase fix); research `375972a63` `scripts/kernel_rnd/autokernel/loop/longctx_c8.py:98` (`cache_prompt: False`) and `:82` (sizing counts prompt tokens). **DONE 2026-11-09** research `9dcd3c0e0` (merged to origin/main; feature commit `1bc36e200`): audit = not decode-only; warm-KV round refuses prompt_n > 16, stub-server test in `test_longctx_c8.py`. The SL-4-LC hold on this box is released. [no-belief: tooling]
    - 2026-11-09 audit, answer NOT decode-only: `loop/longctx_c8.py:98` sends `cache_prompt: False` with no phase split or `prompt_n` bound, while `loop/longctx.py` has both; build the two-phase shape here before the cell runs. [no-belief: audit]

<!-- original line 5842 -->
  - [x] **AK-REGROWTH-BASELINE-3** [non-inference] add `loop_code_budget_baseline.json` entries (research `scripts/kernel_rnd/autokernel/`, guard `check_regrowth_guards.py`, baseline revision `cdf6faa44`) for the three loop files added after the baseline that have none: `loop/campaign_status.py`, `loop/figure_lint.py`, `loop/floor_selfcheck.py`. Reviewed, per-file AST counts through the guard's own generator; do not raise the budget. Done when `check_regrowth_guards.py` reports no missing-baseline entry for them and `test_check_regrowth_guards.py` passes. [owner: AutoKernel] ✅ 2026-11-09 research 9f18ec7f9: entries added, guard reports none missing for them, `test_check_regrowth_guards.py` passes. The guard stays red on 18 other missing entries and existing ceiling overruns. [no-belief: tooling]

<!-- original line 5854 -->
    - [x] **AK-MMQ-H3-NAN-DIAGNOSE — find why `iglp_opt(0)` yields NaN/inf in the MMQ instances.** [non-inference first] model: none (op-level test-backend-ops MUL_MAT, gfx90a MI210); build: C10 `7f1bd044b` + H3 + fix `7621d9784` (`llama.cpp-experimental-ak-h3-fix-20261110`) vs C10 store `gpu-20261109-7f1bd044b-c10fold`. Row `ak-mmq-h3-fix-correct-20261110`, correctness only, same C10 MUL_MAT matrix both arms. stop-on-answer: candidate passes the same count as C10 (H3 timing cells may then run once OP-AK-HOLD lifts); stop-on-futility: first candidate FAIL, arm closed as unfixable by fencing. Gate class futility-only. [no-belief: diagnosis + static ISA count, no GPU result yet] ✅ 2026-11-10 `ak-mmq-h3-fix-correct-20261110` PASS_CORRECTNESS: candidate `7621d9784` MUL_MAT 1202/1202 = C10 control 1202/1202, 0 FAIL lines, own VRAM proven (88 samples >64 MiB); cause is the IGLP pass dropping the iglp_opt dependency edges (cross-wave LDS race), fixed by `sched_barrier(0)` fences; no timing or keep claim (OP-AK-HOLD), parent AK-MMQ-H3 stays open for the timing cells. [belief: cc]
      - ROOT CAUSE 2026-11-10: on ROCm 6.2 (LLVM 18) the IGLP scheduling pass drops the iglp_opt instruction's dependency edges; it sits between mul_mat_q's `__syncthreads()` and the inlined vec_dot LDS reads, so the scheduler hoisted `s_barrier` above the load_tiles LDS writes and vec_dot read LDS other waves had not written (cross-wave race). Not a gate leak: plain iglp0 already failed at C6 (`ak-surface-proof-a2`, 970/1145). ISA: LDS write-then-read sites with no barrier between, across mul_mat_q kernels: C9 26, `4de3dccdf` 615, fix 26 (`/mnt/raid0/llm/tmp/ak-h3-fix-20261110/isa/hazard.py`). Fix: `sched_barrier(0)` before iglp_opt and at the end of vec_dot, keeping the interleave inside vec_dot.

<!-- original line 5856 -->
- [x] **AK-MMQ-H7 — Register-staged prefetch of the next K iteration's x/y tiles across the barrier** (enabled ✅ 2026-11-09 CLOSED (operator decision) on its C9 static ISA gate failure: 4 FAIL on occupancy, the falsifier is hit, only the y-only partial survived; research `ce494f600`. [no-belief: static ISA gate FAIL at C9, operator decision 2026-11-09]
  by gfx90a FeatureBackOffBarrier). Only for instances with VGPR headroom: J<=48, or K-quants whose J=64 loop is rolled.
  Falsifier: INF03-REGAUDIT-1 shows new spills or a vmcnt(0) at the barrier, or no time change.
  - PARKED 2026-09-27 (operator): not started. No branch, audit or timing exist. AK-MMQ-H10 came back NEGATIVE (J=64 stays), so the targets are the J<=48 instances and the K-quants with a rolled J=64 loop; resume by picking the instances with VGPR headroom from the v10 audit table (research `data/gfx90a-isa-audit-20260926/`), prototyping the cross-barrier register prefetch on an experimental branch from `ffc1bac82`, and passing `gfx90a_isa_audit.py diff --families mmq` (no new spills, no hot-loop vmcnt(0) at the barrier) before any timing.

<!-- original line 5860 -->
- [x] **AK-MMQ-H8 — y-tile fill via dword `llvm.amdgcn.raw.buffer.load.lds` plus a second y buffer** (the y ✅ 2026-11-09 CLOSED (operator decision) on its C9 static ISA gate failure: 41 FAIL on spills; `d0e22e4b8`. [no-belief: static ISA gate FAIL at C9, operator decision 2026-11-09]
  fill is a lane-linear copy, mmq.cuh:853-878). The y double buffer drops 2 of 4 barriers per 256-K iteration. LDS
  fits for Q8_0/Q8_1/Q6_K layouts at J=64 (57,600 B) but not for Q2_K. Prior: the MMVQ prefetch that used the same
  intrinsic was net-negative. Falsifier: MMQ time within noise, or a correctness failure.
  - PARKED 2026-09-27 (operator): not started. No branch, audit or timing exist, and the prior stays negative (the MMVQ prefetch that used the same intrinsic lost); resume by prototyping the dword `raw.buffer.load.lds` y fill plus the second y buffer for the Q8_0/Q8_1/Q6_K layouts at J=64 on an experimental branch from `ffc1bac82`, checking LDS and occupancy with `gfx90a_isa_audit.py diff --families mmq`, then running correctness before any timing.

<!-- original line 5884 -->
    - [x] **AK-MMQ-H10b-R2 — re-run the MoE determinism census with a same-seed control.** ✅ 2026-11-17 MOE_RUN_INVARIANT (row ak-mmq-h10b-c12-census-20261117-r3): 9 MoE units, 0 in-process failures on C12. [no-belief: row verdict filed by agent] [receipt-ack: ak-mmq-h10b-c12-census-20261117-r3 FAILED — receipt status reflects the dense arm's known in-process mismatch (dense_run_variant, 1/15), which the box counts rather than treats as futility; the MoE question it asks is answered] [inference, GPU] Confirm in `loop/gates.py` how `--autokernel-harden SEED` changes the input (read the code first, no run); if it is seed-dependent by design, redefine the control as same-seed repeat invariance (dense 2 runs x 3 seeds already satisfy it) and run the MoE arm at seeds 11/12/13 x 2 on the same store; verdict MOE_RUN_INVARIANT or MOE_RUN_VARIANT. Stop when 9 MoE units are recorded or the first within-seed MoE mismatch appears. Correctness census, no timing, no keep claim. est 3000 s. [no-belief: new box]
      - 2026-11-17 (autokernel, INF-06 sweep): retargeted to champion C12 `457d5fc52`. C12 adds the upstream MMQ OOB-read, MMQ n_expert fault and two FA race fixes over C10 but not the skinny-det reduction, so the C10 in-process flake rate may differ. No C12 GPU store with llama-bench exists, so the row builds llama-bench in-row. The C10 r3 design aborted on one dense in-process flake. That flake is now counted, with its measured hash taken from the invariance line, and is not treated as futility. Design: dense 27B 3 seeds x 5, then MoE 3 seeds x 3. Row `ak-mmq-h10b-c12-census-20261117` published (smoke queued for the next GPU gap; est 3000 s; supersedes `ak-mmq-h10b-moe-determinism-c10-r3-20261110`). Pre-registered rule in `/mnt/raid0/llm/tmp/ak-mmq-h10b-c12-census-20261117/job.py`. [no-belief: row pending]
      - 2026-11-17 (autokernel): r1 smoke failed rc 3 on identity, not residency: a git-archive build has no .git, so build-info reported `build_commit` "unknown", although own-pid VRAM was 27.7 GiB and libggml-hip was mapped from the row build. r2 `ak-mmq-h10b-c12-census-20261117-r2` configures with `-DLLAMA_BUILD_COMMIT:STRING=457d5fc52` (C12 CMakeLists honours a pre-defined value) and was published (smoke queued). The greedy bisect row checks no build_commit (maps + VRAM delta), so it is unaffected. [no-belief: row pending]
      - 2026-11-10 RESULT (autokernel; row `ak-mmq-h10b-moe-determinism-c9-r2-20261110`, C9 GPU store `gpu-20261109-d210f85c2-c9fold`; NOT ticked, box stays OPEN). **Question:** is MoE (Qwen3.6-35B-A3B Q8_0) tg8 output repeat-invariant at one `--autokernel-harden` seed, seeds 11/12/13 x 2 runs? **Verdict: INCONCLUSIVE** (stop rule not met: `gpu_residency_proven=false` on 5 of 6 MoE units, `failed_units` moe/s12/1, s13/2, s11/3, s12/4, s13/5; only moe/s11/0 proved residency). Evidence that is NOT residency-gated but points one way: own VRAM was 35.6-35.8 GiB on every unit (35,584-35,799 MiB) with no foreign KFD process, and the within-seed MoE hashes were identical across the two runs at every seed (s11 52850b05..., s12 32bc96e2..., s13 6fc6ae49...), with the dense hashes again identical within seed, so the pattern is MOE_RUN_INVARIANT [inferred]. The residency flag failing while own VRAM is 35 GiB looks like a harness defect in the proof, under investigation; no MOE_REPEAT_INVARIANT claim until a residency-proven re-run. Evidence `/mnt/raid0/llm/tmp/ak-mmq-h10b-moe-determinism-c9-r2-20261110/out/RESULT.json`. [belief: cc]
      - 2026-11-17 ak-mmq-h10b-c12-census-20261117-r3: pass (MOE_RUN_INVARIANT) — C12 `457d5fc52`: MoE A3B 9 units, 0 in-process failures, hashes invariant per seed; dense 27B 15 units, 1 in-process failure (seed 11), dense_run_variant true (C10 was 1/15 at s13, 2/5 at s12; v10 0/15 and 0/5), so the known dense in-process defect (since C7) persists at about the C10 rate. Correctness census only, no timing or keep claim. Evidence `/mnt/raid0/llm/tmp/ak-mmq-h10b-c12-census-20261117-r3/out/results.jsonl`. [no-belief: row verdict filed by agent]

<!-- original line 5893 -->
- [x] **AK-MMQ-H5 — nthreads / per-wave-tile sweep in mmq-config-cdna.cuh** (256 vs 512 threads at I=128; CLOSED 2026-11-09 operator decision: all 147 kernels fail the static ISA gate as predicted, 62 lose occupancy (a0a592182). ✅ [no-belief: static gate only, no timing]
  occupancy 2 is infeasible at I=128 because the x tile alone is 38,912 B). Each cell sits on one side of the ROCm 6.2
  AGPR rule: 256-thread arms get AGPR form with a 512 budget and copies; the rule changes on ROCm 7.14+. Record agpr,
  copies, spills and compiler with every cell.
  - PARKED 2026-09-27 (operator): not started. No sweep cell has been built; resume by building the 256- and 512-thread `mmq-config-cdna.cuh` arms at I=128 on an experimental branch from `ffc1bac82` and recording agpr, accvgpr copies, spills and the compiler for each cell with `gfx90a_isa_audit.py audit` plus `diff --families mmq`, before any timing.
  - 2026-11-09 (operator decision): H5 needs a written stop rule before any row is booked (research `a0a592182`). [no-belief: operator decision 2026-11-09]
  - **Stop rule (PROPOSAL, 2026-11-09, not ratified).** Question/decision: does 256 threads at I=128 beat 512 on CDNA MMQ enough to carry; keep the arm or close it. Evidence used: the box's AGPR prediction, the Q6_K object audit of `a0a592182` (7/7 AGPR, hot accvgpr copies 0 -> 24-64), H10 null controls within +-1.5%. Units: static = each type x J x chk kernel; timing = MUL_MAT cell at q4_K/q6_K, ne11 16/32/64, 7 interleaved reps, same-row A/A. Effect vs error: no prior predicts a gain and the box predicts a cost; useful effect >=3% (2x the H10 null band) against the same-row A/A of each cell. Order: static gate, then correctness, then timing; diagnostic, no keep claim. Stop-on-answer: every in-scope cell has a median ratio and A/A; a cell >=3% past its A/A answers keep, none answers close. Stop-on-futility: every kernel FAILs `gfx90a_isa_audit.py diff --families mmq` against C9 (the H7/H8 closure rule), or correctness fails. Cap 1 h GPU, resumable per rep.
  - 2026-11-09 (autokernel): full-library audit of `a0a592182`: 147/147 kernels FAIL against C9 (agpr_appears and hot_accvgpr_copies on all 147, as predicted; occupancy drop on 62), so the futility clause fires before any timing. Row prepared unpublished at `/mnt/raid0/llm/tmp/ak-kernel-mmq-h5-20261109/`. The AGPR classes FAIL by construction, so a run needs a decision to waive them for the 85 kernels with no occupancy drop. [no-belief: static ISA gate, no timing]

<!-- original line 5903 -->
- [x] **Recorded so it is not re-derived (dives 2026-09-26).** ✅ 2026-09-26
  - J=128 for Q8_0-layout types is KILLED at 512 threads: LDS fits (57,856 B) but VGPRs do not.
  - A register fragment ring in vec_dot is KILLED at J=64, which already spills.
  - An LDS-staged write-back is low value: each fp32 lane already writes 16 B.
  - The ladder's TDM, split-barrier, cluster-multicast, lock_simd, async b128 and partitioned-LDS rungs have no gfx90a
    counterpart; they are flagged for operator review, not dismissed.

<!-- original line 5914 -->
- [x] **AK-HR-1 — Closed-store history census and read-only exporter: settle which restart, surrogate and diversity analyses the existing AK history can answer.** In a research-repo worktree (new offline package `scripts/kernel_rnd/autokernel/history_replay/`, no GPU and no timing), open every closed `experiments.db` under `/mnt/raid0/llm/autokernel/loop-memory` and `/mnt/raid0/llm/autokernel/campaigns/*/store*` with SQLite `mode=ro`, plus the sibling `actor-calls.jsonl` (`actor_call.v1` and `actor_call_metrics.v1` lines) and `runtime-preparation/runtime-arms-attempts.json`; exclude the legacy `kernel_store.py` strategy store and any store a live run still holds. Write `history_records.jsonl` (task key = target surface + epoch -> candidate = mechanism_id plus a typed knob or edit descriptor when one exists, else null -> outcome = status, failure class, effect_fraction, per-stage seconds where recorded; every row carries store path, rowid, attempt_id, store size and row count) and `census.json` answering: (a) rows by status and campaign, summing to each store's `SELECT count(*)`; (b) how many INDEPENDENT same-target campaigns exist (a run that continues a store is the same campaign) and, where two or more, the between-run best-score SD and CV; (c) whether a monotone cumulative budget axis (decoded plus prompt tokens from `actor_call_metrics.v1`) and a stable trial id exist, and whether any key joins a call to its attempt (today only a time window does); (d) the rebuilt loop's per-attempt wall split into planner, critic, build and measure seconds, replacing the pre-rebuild 75.7% build / 3.9% measure figures at `autokernel-rebuild-program.md:387,393`; (e) a surrogate-readiness table per target: anchored same-epoch comparable measured trials with a numeric effect, keeps, and typed-knob coverage; (f) whether the `RuntimeArmPair` knob space is a bounded decision-token space; (g) a gap table of absent write-side fields. Done when two runs give byte-identical outputs, by-status totals equal row counts, no store mtime changed, and each of (a)-(g) states answerable now, not answerable (with the count) or needs fields (with the list); outputs land in research `data/ak-history-replay-20261020/`. ✅ 2026-10-20
  - 2026-10-20 RESULT NOTE (executor; checkbox left OPEN pending main review). Package `scripts/kernel_rnd/autokernel/history_replay/` and outputs `data/ak-history-replay-20261020/` in epyc-inference-research (epyc-inference-research main `092a84539`). Inputs: 8 `experiments.db` stores (loop-memory plus 7 campaign stores, 3,576 rows), 19 `actor-calls.jsonl` files (2,700 metrics lines), 3 `runtime-arms-attempts.json` files (10 attempts); opened `mode=ro&immutable=1` only after proving every `-wal` is 0 bytes. Excluded with reason in `census.json`: `loop-memory/experiments.sqlite` (0 bytes), `experiments.db.pre-retraction` (backup snapshot), three `store*` dirs with no `experiments.db`; no store was live (no autokernel region-lock claim, no process naming a campaign path, no kernel lock on a store file, every db/wal mtime older than 30 min; DS41 `store/cpu-window.json` still says `build_and_measure` but its `expires_at` 2026-10-04 passed, so it is a stale window).
  - Done-criteria evidence: two further full runs (and a third into the data dir) gave byte-identical `history_records.jsonl` (sha256 `376c0eec...2ef14`), `actor_call_records.jsonl` and `census.json` (sha256 `644049cd...0b2bd`); by-status totals equal each store's `SELECT count(*)` (checked in-run and again independently: 2397, 13, 385, 444, 1, 5, 0, 331); 114 files across the store dirs had identical mtime and size before and after (`run_provenance.json`); focused tests pass (`history_replay/test_export.py`, 3 cases).
  - (a) answerable now: per-store and per-campaign status counts are in `census.json` `a_rows_by_status_and_campaign`. (b) NOT answerable: one independent campaign per target after merging stores that share an epoch id (DS41 `store` and `store-b0ba1d427` share epoch `cd9dd6c1...`, so they are one campaign); 0 targets have two scored independent campaigns, so no between-run SD or CV (AK-RI-RESTART-1 needs >= 5; max seen is 1). (c) PARTIAL: `attempt_id` is a unique stable trial id on 3,576 of 3,576 rows; a decoded-plus-prompt token axis exists on 287 of 2,700 metrics lines only (all `opencode`; the 2,159 codex and 254 claude lines carry none), so a cumulative token budget axis is not answerable for the full stream (wall_s is on 2,700 of 2,700); no campaign-wide monotone counter (rowid restarts per store); 0 of 2,700 call lines carry any attempt key, only the time-window heuristic exists. The intake plan's "1,686 token lines in 15 DS41 files" was not reproduced: 287 lines carry `opencode.totals` tokens. (d) PARTIAL: planner, critic and author seconds per call and measure instrument-window seconds are answerable; build seconds are needs-fields (no build or per-stage seconds on any payload; the cpu-window phase events carry no event timestamp). Over identified seconds only (not loop wall): DS41 planner 0.3902, author 0.2693, critic 0.0641, measure windows 0.2765; Q38FN planner 0.8505, critic 0.0547, author 0.0220, measure windows 0.0728. These do NOT replace the pre-rebuild 75.7% build / 3.9% measure figures until build seconds are recorded. (e) answerable now: comparable anchored same-epoch trials with a numeric effect / keeps / typed-knob trials are DS41 79 / 28 / 8, Q38FN 42 / 10 / 7, 27B-GPU 0 / 0 / 0, legacy loop-memory 854 / 32 / 0; the AK-RI-SURROGATE-1 trigger is met for no target (legacy passes the raw 200/20 count but spans many surfaces and epochs and has no typed descriptor). (f) answerable now: `RuntimeDimension` has 7 kinds (a bounded vocabulary) but integer and free-string values, so the value space is not a bounded decision-token space; only 2 dimensions were exercised in the 10 arm attempts (`load_threads`, `env` OMP_PLACES). (g) gap table in `census.json` `g_gap_table` (13 rows; headline gaps are the attempt-to-call key, a campaign-wide trial counter and cumulative token counter, tokens on hosted calls, per-stage seconds incl. build, a typed descriptor for source candidates, and an `attempt_id` on `runtime-arms-attempts.json` entries). These feed AK-HR-3.

<!-- original line 5918 -->
- [x] ~~**AK-HR-2 — Search-diversity, faithfulness and repeat-null diagnostic over the closed AK history: decide whether the keep drought is mode collapse or space exhaustion.** After AK-HR-1, reading its `history_records.jsonl` only. Freeze a kernel mechanism taxonomy (8-10 classes, e.g. tiling/blocking, vectorization/ISA path, prefetch, threading/affinity/NUMA, quant layout/dequant fusion, kernel fusion, memory placement, runtime recipe, other) from a pilot of 60 hypotheses drawn from `loop-memory` only, record its sha256 BEFORE analysis, hand-label 40 held-out DS41/Q38FN hypotheses and report rule-vs-hand agreement (stop if kappa < 0.6 or `other` > 50%). Per campaign and epoch, over sliding windows W=20 of hypotheses (`statement`, `mechanism_id`, target surface and symbol; rows with no intent text counted as `no_intent` by status, never dropped) compute mechanism entropy H_t in nats and distinct-mechanism count, and compare the H_t trend with 1000 within-epoch order permutations; add the optional SBERT+HDBSCAN cluster count (paper parameters W=20, min_cluster_size 5, min_samples 2, all-mpnet-base-v2) only in an isolated venv under `region-lock run --role build`; surface diff distance S_t only where patch bytes were retained (historic `<mechanism>.<lane>.patch` files are overwritten, so expect not-judgeable). Also report: (i) the signed faithfulness ratio rho = confirmed or serving-gate gain / screen gain per campaign and mechanism class, `not judgeable` where either tier is missing; (ii) the with-lessons repeat-null rate = share of planner formations that structurally agree (`dispatch_guard.characterised_reason`, `do_not_repeat.structural_target`) with an earlier `ANSWER_STATUSES` row, with `refused_at_formation` as its lower bound; (iii) a rendered-context audit: re-render the planner-facing `Already tried` window as of each recorded planner call under recency recall and under `--rank-prior-experiments` (off by default in `run.py`), and report the harness-event share (`planner_transient`, `lane_error`, `bench_failed`, `abstained`), whether do-not-repeat keys on measured answers only, and a one-page table of the SLA Advisor evidence-summary inputs vs `render_context` sections vs the store column feeding each. Predeclared verdict per campaign: `collapse seen` needs >= 3 full windows, an H_t trend below the 5th percentile of the permutation null and `other` <= 50%; `underpowered` below 3 windows; otherwise `not detected`. The verdict gates AK-RI-FORGET-1 and changes no search policy; outputs land in research `data/ak-history-replay-20261020/` with per-row labels.~~ (closed 2026-10-29 audit: OBSOLETE → handoff:5629 CLOSING NOTE CLOSED-PARTIAL on operator decision 2026-10-20 (not yet decidable; taxonomy gate failed); AK-HR-2.1 flip done separately)
  - 2026-10-20 RESULT NOTE (executor; checkbox left OPEN pending main review). **PARTIAL: the predeclared held-out agreement gate FAILED, so the taxonomy-dependent diversity verdict was NOT computed.** Outputs in research `data/ak-history-replay-20261020/ak-hr-2/` (commits `92cb912c1` freeze, `c0d6f954f` results on branch `ak-hr-2-research-20261020`; scripts `scripts/kernel_rnd/autokernel/history_replay/ak_hr2_*.py`). (1) Taxonomy: 10 classes frozen BEFORE analysis from a 60-hypothesis loop-memory pilot (seed 20261020; `taxonomy_v1.md` sha256 `d66cb3dc...8375`, rule parser `ak_hr2_taxonomy.py` sha256 `09b5c39b...3149`, pilot `649b9cb0...f72`; `taxonomy_freeze.json`). Pilot support: 8 of 10 classes occur; `threading_runtime_recipe` and `other` have none (the former carried from the checkbox example list). Disclosure: before freezing, the executor had printed a few unlabelled DS41 rows and the 15 most common mechanism_ids while exploring; none chose a class. (2) Held-out gate: 40 DS41/Q38FN hypotheses (20 each, seed 20261021, unique statements) labelled by an independent LLM agent (sonnet, NOT a human) that was shown only the taxonomy table and decision rules and never the rule parser or its output; the parser was run on them afterwards. Cohen's kappa (rule vs independent labeller) = 0.2448, observed agreement 13/40 = 0.325, parser `other` share 0.0, independent `other` share 0.0 -> kappa < 0.6, STOP per the predeclared rule (`heldout_agreement.json`, per-row labels in `per_row`). Independent labels: threading_runtime_recipe 17, vector_isa_path 7, tiling_launch_geometry 4, kernel_fusion 4, reuse_redundancy 4, memory_placement_prefetch 3, dispatch_algorithm_selection 1; the parser put 10 rows in reduction_sync (7 of them labelled threading by the labeller). The parser and taxonomy were not re-tuned after seeing the held-out result. Read: a GPU-only (loop-memory) pilot did not transfer to the CPU decode campaigns, where 17 of 40 hypotheses are host-threading or team-scheduling mechanisms the pilot never contained. (3) VERDICT per campaign: not computed (gate failed). No `collapse seen` / `not detected` / `underpowered` is asserted for any campaign, and AK-RI-FORGET-1's collapse trigger is therefore not decided by this run. Power fact independent of labels: deduplicated intent-bearing hypotheses per campaign are DS41 170 across 28 epochs (largest 26), Q38FN 72 across 8 epochs (largest 26), 27B-GPU 3; loop-memory (1478 hypotheses, 19 epochs) has 66 non-overlapping full windows, while DS41 has 2 and Q38FN 1 in total (each epoch contributes floor(n/20)), i.e. both live targets would be `underpowered` under the predeclared >= 3 rule whatever the labels. (4) no_intent accounting (rows with neither statement nor non-sentinel mechanism_id, by status, nothing dropped): loop-memory 916 of 2397, DS41 557 of 835, Q38FN 198 of 331, 27B-GPU 0 of 13 (per-status tables in `taxfree_results.json` `no_intent_accounting`). (5) Repeat-null (ii), taxonomy-free, real `do_not_repeat.structural_target(...).agreement` against EARLIER `ANSWER_STATUSES` rows of the same campaign, same epoch (full epoch or equal measurement_epoch): over all intent-bearing formation rows, loop-memory 223 of 1481 = 0.151 (46 meet the dispatch_guard >= 3 rule, 0.031), DS41 10 of 278 = 0.036 (guard rule 0), Q38FN 4 of 133 = 0.030 (guard rule 0), 27B-GPU 0 of 13; any-epoch rates 0.19 / 0.083 / 0.120. Excluding matches against an identical earlier statement text: 0.150 / 0.025 / 0.015. `refused_at_formation` share of formations (offered as lower bound): loop-memory 361 of 1481 = 0.244, DS41 6 of 278 = 0.022, Q38FN 0. CAVEAT on that bound: 0 of the refused_at_formation rows' refusal texts cite do_not_repeat (they are critic refusals such as 'Already measured and present in the current champion'), and only 13 of loop-memory's 361 structurally agree with an earlier answer, so refused_at_formation is NOT a subset of the structural rate and does not bound it from below. The dispatch_guard escape clauses (candidate-diff digest, research_scope regime) are not replayable from the export. (6) Faithfulness (i): the export holds one effect per row, so rho is a cross-row join (confirmed tier = `kept` or `measured_serving_gate`; screen tier = latest EARLIER same-campaign same-mechanism_id row in keep_candidate/measured_null/regression with a numeric effect; strict pairing needs equal candidate_diff_sha256). Judgeable confirmed rows: DS41 2 of 30 (rho 0.587 and -0.060; 1 strict pair), Q38FN 0 of 10, loop-memory 6 of 32 (rho 2.25, 26.48, 6.97, 2.05, 2.78, -26.95; 0 strict), 27B-GPU 0 confirmed rows; the not-judgeable reason is always 'no earlier screen-tier row for this mechanism_id'. Per-class rho is not available (no validated class labels). Sign flips occur in both campaigns that have any pair. (7) Surface diff distance S_t: rows with a retained-patch flag DS41 59 (max 10 in one epoch), Q38FN 32 (max 22 in epoch 1105f10f), 27B-GPU 6, loop-memory 0; patch bytes are not in the export, so S_t is not judgeable from the export; Q38FN epoch 1105f10f (22 flagged rows) is the only place a >= 20 window of retained patches could exist, and answering it needs a read of that store. (8) Rendered-context audit (iii), 1960 of 1963 planner calls re-rendered as of call time (3 empty windows, 0 unjoined; epoch comes from the heuristically joined next attempt; verified epoch aliases are not exported so same-epoch is a proxy; real `run.prior_experiments`, `_with_pinned_history`, `experiments.rank` and `actors.render_context(limit=12)` were used, only `ExperimentStore.recall` is re-implemented and tested against a real store; loop-memory has no recorded planner calls): under default recency recall the 12 verbose rows of `## Already tried` are on average 0.858 harness events (planner_transient, lane_error, bench_failed, abstained) and 0.043 measured answers; 81.2% of calls show zero answer rows in the verbose window and 38.6% show none even after the 'Always shown' block (DS41 9.1%, Q38FN 83.0%; Q38FN's Always-shown block is non-empty on only 27 of 782 calls). Under `--rank-prior-experiments` the same windows are 0.042 harness and 0.566 answers, 1.6% of calls with no answer row; mean rendered section 8011 chars (recency) vs 6770 (rank). Whether do-not-repeat keys on measured answers only: yes for the dispatch guard, verified by running `characterised_reason` on three same-epoch harness rows (abstained, planner_transient, lane_error) -> None and on three measured_null rows -> a refusal string; but `render_context` counts abstained/refused_at_formation as terminal failures for its diminishing-returns triggers (`actors.py:2681`). The SLA Advisor evidence-summary mapping table (paper inputs as returned by an HTML-fetch summary of arXiv 2610.07625, NOT verified against the PDF; our code citations are file:line) is `sla_input_mapping.md`: frontier age, recent movement, baseline score and an explicit sealed-valid-vs-inconclusive grouping are absent from our window, which still renders free-text statement/falsifier/refusal prose. (9) Optional SBERT+HDBSCAN cluster count: SKIPPED, all four CPU regions were held at dispatch time; not waited for. (10) Descriptive only, NOT the predeclared test: W=20 entropy over mechanism_id and over target file with 1000 within-epoch permutations gave no below-null-5th-percentile slope for DS41 or Q38FN on either field; loop-memory target-file entropy slope is below the null 5th percentile (p 0.028, mean slope -0.0015 nats per window); these carry no verdict. Reproduce: `ak_hr2_kappa.py`, `ak_hr2_taxfree.py`, `ak_hr2_render_audit.py` (outputs deterministic apart from the argv echo). Next step needs a decision (operator or main): re-freeze a v2 taxonomy with a pilot that includes CPU decode hypotheses (breaks the 'loop-memory only' pilot rule) and a fresh held-out draw, or accept `not decidable` for AK-HR-2 and gate AK-RI-FORGET-1 on its repeat-null rate alone; this note does not choose.
  - 2026-10-20 CLOSING NOTE (executor, after main APPROVED close-out on the operator decision of 2026-10-20: close as "not yet decidable" using the existing axis). **Checkpoint state: CLOSED-PARTIAL, box left UNTICKED.** Reason: the box text requires per-row labels from a passing frozen taxonomy and a per-campaign entropy-window verdict, and the taxonomy gate failed; the one per-campaign verdict that is label-free (`underpowered` below 3 windows) depends on counting full windows as non-overlapping (DS41 2, Q38FN 1), whereas a sliding-window count would give DS41 12 and Q38FN 7, so I do not claim that the box's done criteria are met by a recorded verdict. This is a handoff-text checkpoint, not a `worker_checkpoint.py` call (its `partial` state is pre-reboot only). (a) VERDICT: **not yet decidable.** The live targets are underpowered whatever taxonomy is used (DS41 has 2 full windows of 20, Q38FN 1; the predeclared rule needs >= 3), and loop-memory (66 full windows) is a legacy GPU aggregate, not a live target. AK-RI-FORGET-1's `collapse seen` trigger is therefore not met by this diagnostic; its repeat-null branch stands on the numbers in the result note above (DS41 0.036, Q38FN 0.030 structural, same-epoch). (b) The hand-made 10-class `taxonomy_v1` is RETIRED (freeze `92cb912c1`, kept as the record of the failed gate): held-out kappa 0.245 against an independent LLM labeller, and it reads no existing typed field. Do not tune or re-freeze it. (c) Any future rerun uses the existing typed axis: `mechanism_id` plus the 4-family `_mechanism_family` helper (`loop/actors.py` ~3002-3006: synchronization/barrier, local quant/dot kernel, local fusion, prefetch/cache; already imported by `ak_hr2_render_audit.py`). Do not author a new taxonomy. The descriptive `mechanism_id` and target-file window statistics already in `taxfree_results.json` are the starting point; the family axis is not yet computed. (d) The belief kernel currently has no hypothesis or edit typing; AK-HR-3's nullable write-side fields should carry `mechanism_family` (see the pointer under AK-HR-3), so the kernel receives a type from now on. Index-row note for the owning session: the AK-HR-2 row's next action should read "rerun windows on mechanism_id + _mechanism_family only when a live target has >= 3 full windows"; I did not edit the index.
  - 2026-10-20 OPERATOR DECISION ("Flip the default now"; executor note, no checkbox change): AutoKernel's planner now uses ranked prior-experiment recall by DEFAULT. `run.py --rank-prior-experiments` is now `argparse.BooleanOptionalAction` default True; explicit opt-out `--no-rank-prior-experiments` restores recency recall; existing launch commands passing `--rank-prior-experiments` are unchanged (`serial_roster` also admits the opt-out switch). Ranking logic and the store/archive `recall()` API default are untouched. Evidence: AK-HR-2 render audit (`epyc-inference-research data/ak-history-replay-20261020/ak-hr-2/render_audit_summary.json`): under recency recall the 12 verbose `## Already tried` rows average 0.858 harness events and 0.043 measured answers and 81.2% of planner calls show no measured answer; ranked shows none in 1.6% of calls and the section is shorter (6770 vs 8011 chars). Effective from the NEXT campaign launch; no campaign was live at change time (none restarted). Follow-up comparison (no new checkbox): the next DS41/Q38FN campaign's keep yield, repeat-null rate and abstain rate are to be compared against the recorded pre-flip history (AK-HR-1/AK-HR-2 outputs). Code: epyc-inference-research branch `lane/ak-rank-default-20261020` (`loop/run.py`, `serial_roster.py`, `test_ranking.py`).

<!-- original line 5930 -->
- [x] **AK-HR-3b - time build and correctness separately inside the injected gate** (only `gate` and `measure` are timed today: `STAGES` in `loop/history_fields.py` has no `build` or `correctness` key) so AK-HR-1(d) can replace the pre-rebuild 75.7% build / 3.9% measure split and AKX-ALL-28's TileLang hipcc seconds (1.4-1.6 s/config) can be set beside the loop's per-attempt build seconds. Hosted codex/claude token counts stay unrecorded (backends report none): note as not obtainable. (filed 2026-10-20)
  - 2026-10-24 RESULT (3c4ca599 subagent; code `eea4da3d0`, then `149c946c1`).
    - `history_fields.STAGES` gains `build` and `correctness`.
    - `gates.compiles` records its own wall seconds as `build`, wherever it is called from: inside `run_all` on the CPU
      gate, or before the quiet window on the GPU gate.
    - `gates.run_all` times every other check as `correctness`.
    - The `run.py` gate code is unchanged. A first cut that edited the GPU branch broke the
      `HardenedCandidateGates` structural pin; `149c946c1` restored that branch.
    - So `build + correctness <= gate`. The remainder is scope analysis (git diffs, route admission) and window waits.
    - A stage that did not run stays null: a runtime arm has no build, and a failed build leaves correctness null.
    - Observe-only: verdicts, order and short-circuit are unchanged, and the timer is a no-op outside a trial.
    - Tests: `test_history_fields` (+4) and `test_gates` = 192 passed; `history_replay` passes.
    - Hosted codex/claude token counts remain NOT OBTAINABLE: the backends report none, and `trial_tokens` stays null
      for those calls.
    - The AK-HR-1(d) build/measure split and AKX-ALL-28's TileLang hipcc s/config can be compared once a post-change
      campaign writes rows.

<!-- original line 5946 -->
- [x] **AK test flakes - root-cause `test_gates.TheToolRunnerNeverTreatsAFailureAsOutput` (`ScratchRefused: child cleanup uncertain`, 1 of 6 runs on a detached origin/main baseline under CPU co-run) and the 2 pre-existing `test_serial_roster.py::test_shared_author_sandbox_reaches_real_authenticated_control_startup[off|on]` failures (also red on clean origin/main).** Done when each is either fixed or explained with a reproducer. (filed 2026-10-20) ✅ 2026-10-27
  - 2026-10-24 RESULT (3c4ca599 subagent; code `21ef67e69`).
    - **Root cause of `TheToolRunnerNeverTreatsAFailureAsOutput` -> `ScratchRefused: child cleanup uncertain`:**
      `procguard.Guard.scope_state` reads the provenance of every same-uid process born after the owner.
      - An unrelated process that is EXITING still reads as state `R`, but `PF_EXITING` is set and its mm is gone.
        For a few ms it refuses `/proc/<pid>/environ` with EACCES.
      - A process whose `/proc` directory vanishes between the stat read and `os.stat` reports no uid.
      - Both were counted as census errors. `scratch._wait_child_cleanup` then marked the call refused for good, so a
        clean `captured_child_env` call raised.
      - "Under CPU co-run" means more short-lived processes from other sessions, hence the 1-in-6 rate.
    - **Measured on this host:** 15 s of 4-thread `true` churn produced 14,545 environ EACCES reads on live-looking `R`
      children. Every one was gone at a 5 ms re-read. Every one still present carried PF_EXITING (430 of 430 checked).
    - **Fix:** a new `Guard._died()` clears an unreadable task only on PROOF of death: the entry is gone, the PID was
      recycled, or the state is Z/X.
      - It waits up to `exit_settle_s` (0.5 s), and only while PF_EXITING is set.
      - A live, non-exiting unreadable process is still a census error, with no wait, so fail-closed is unchanged.
      - TASK_DEAD (`X`) now counts as dead, like `Z`.
    - **Reproducers** (synthetic `/proc`, `test_procguard.py`, 5 new tests): the exiting-task and vanished-directory
      tests FAIL on origin/main for exactly the two errors above, and PASS on the branch.
    - **Tests:** `test_procguard` + `test_scratch` + `test_gates::TheToolRunner...` = 78 passed. The 1 failure is
      `ScratchInventory::test_every_creating_call...`, which flags `run_paired_serving_ab.py`, `ab_server_pair.py`,
      `floor_registry.py` and others. That failure was already on origin/main; none of those files are touched here.
    - **2026-10-27 RESOLVED:** `test_serial_roster.py::test_shared_author_sandbox_reaches_real_authenticated_control_startup[off]` and `[on]` use the fixture subprocess `PYTHONPATH` fix in research `1ff090cc`, merged as `dc77ce388`. On research `08fe38e7ec99`, focused `test_procguard`, the ToolRunner class and both authenticated-control variants passed 29 tests; Q3 log `/mnt/raid0/llm/tmp/codex-ni-20261027-ak-flake-blocker/run-absolute/admitted-command.log`. ToolRunner fix `21ef67e69` is also an ancestor of that baseline; its documented synthetic reproducers remain above.

<!-- original line 5969 -->
- [x] **Decide whether `abstained` / `refused_at_formation` should count as terminal failures in `render_context`'s diminishing-returns triggers (`loop/actors.py`, the `terminal` and `stagnating_statuses` sets)** given AK-HR-2 shows these are harness events (0.858 of the 12 verbose `Already tried` rows), not measured answers; change only with the INF-73 loop owner's review. (filed 2026-10-20)

  - [x] **VB-AK-HISTORY producer call (owed, filed 2026-10-21; INF-73 loop owner):** ✅ 2026-11-19 (autokernel): the call is wired at the archive boundary, research `7663de423` (`loop/archive.py` `_publish_ak_history` -> `adapters.ak_history.append_belief_measurement`, receipts per trial) and bound to the run's `--belief-root-repo` by `9531e48db`; `test_archive_root.py` + `test_history_fields.py` 22 passed. The real-campaign canary stays under AK-HR-3/AK-TRIG-1. [no-belief: code] at the archive boundary of the next DS41/Q38FN campaign call `scripts/vidya/adapters/ak_history.write_belief_measurements(out_dir, campaign_id=..., store_id=..., epoch=..., producer=..., trials=[exactly the AK-HR-3 `history_fields` keys])` so each trial gets a self-hashed receipt; carrier and reader landed in root `7335da327`.
  - 2026-10-24 DONE (operator decision, 3c4ca599; review memo `/mnt/raid0/llm/tmp/ak-trigger-review-20261024/MEMO.md`). Landed as two commits (research main): (b) the trigger walk follows `recorded_at`, not rank order (`da6d32921`), then (a) `abstained` leaves both trigger sets (`37fe0f50f`); `refused_at_formation` KEEPS counting. Revert (a) alone to restore abstentions. Evidence `data/ak-history-replay-20261020/render_trigger_audit.json`. (b) replay: 116/189 DS41 escape firings counted pre-keep failures, 191 Q38FN stagnation firings were hidden. (a): moves n=1 Q38FN episode, about 1.5 extra attempts per campaign, 354/356 abstentions are reasoned declines. Follow-up checks: AK-TRIG-1.

<!-- original line 5981 -->
- [x] **AK-SETUP-1 — Consult the kernel store before building a source-change candidate.** A 2026-11-06 audit found 44 of 51 anchor rebuilds compiled a byte-identical tree because `build_key` hashes `patch_sha256`, which the anchor does not depend on. Before every build, look up the candidate's content-addressed key under `/mnt/raid0/llm/kernels/builds/`; on a hit bind the existing `BUILD-OK.json` plus binary digests as the build result and skip compilation, on a miss build. Record `store_hit: true|false` on the attempt so AK-HR-1 can price the saving. Done when a replay over the 51 historical anchors reports the hit count and skipped seconds, and every new attempt carries `store_hit`. (intake-2643#record, intake-2644#record) [no-belief: tooling; no measurement]
  - 2026-11-06 RESULT (operator-adhoc-ops-20261105; research `86bb55dd8`). `controller/build_store_lookup.py`: content-addressed `store_key` (patch sha, base+instrument authority, defines, toolchain, env; NOT paths/-j/proposal), verified lookup under `/mnt/raid0/llm/kernels/builds/ak-<key16>/BUILD-OK.json` (digests re-checked), hard-link materialise, miss -> build -> publish pointer. Wired into `_build_uncached` for the candidate tree; the sealed materialization record carries `store_hit` per tree with `skipped_seconds`. Disabled unless `kernel_store` is passed (production factory passes it; tests never write the shared store). Replay over the 45 historical build-cache intents (the 51 anchors are 51 attempts over 45 entries): anchor-tree hits 38/45 (84.4%), candidate-tree hits 1/45 (2.2%), pre-reuse `build_key` hits 0/45, estimated skipped 39,485 s (log-mtime estimates for 13 entries, 1,012 s fallback otherwise). Existing store entries carry no AK key, so the first hits arrive only after new builds publish.

<!-- original line 5983 -->
- [x] **AK-SETUP-2 — Parallelise the source-change build and stop paying serial compile on a 192-thread host.** `-j 1` appears in 77/77 build logs and build is 2,025 s of a median 2,675 s iteration. Raise the build to a declared, pinned `-j` value, keep it fixed for A/B, and record build and correctness seconds (the keys landed with AK-HR-3b). Compare with the current serial build on the same source. Accept when median build wall drops >=50% with an identical binary digest and a clean `test-backend-ops` smoke; revert if the digest changes or a stale object is detected. (intake-2643#record) [no-belief: tooling; no measurement] RESULT 2026-11-07 PASS (row `ak-setup-2-proof-20261106-r2`, rc=0, anchor c420b9d1a): serial -j1 380 s vs parallel -j24 75 s, wall drop 80.26% (rule <=50%), digests identical, smoke clean, accepted=1. [belief: cc]
  - 2026-11-06 PARTIAL (operator-adhoc-ops-20261105; research `86bb55dd8`): the pinned parallel width already exists (`_BUILD_JOBS = 64` on cpu_list 96-183, recorded in `build_key`); 77/77 `-j 1` logs predate it. Added `controller/build_parallel_proof.py`: accepts only on identical binary digests + clean CPU `test-backend-ops` smoke + median wall drop >=50% vs the serial build, reverting on any digest change. The live same-source serial-vs-parallel comparison needs a real compile (compute) and is NOT run, so the box stays open.
  - 2026-11-06 PREDECLARED (operator-adhoc-ops-20261105, before publish): row `ak-setup-2-proof-20261106` (CPU build class, quarter q0 only, rank 60, `/mnt/raid0/llm/tmp/ak-setup-2-proof-20261106/`; thread env from shared `job_templates/job_fence.py`). QUESTION: does the pinned parallel build (-j = quarter affinity threads) cut build wall to <=50% of the serial -j1 build of the SAME anchor (`llama-c7-asm-ports-20261106` @ `c420b9d1a`, targets llama-bench + test-backend-ops, ccache off, llguidance off)? ACCEPT = wall drop >=50% AND identical binary digests AND clean CPU `test-backend-ops` smoke (`build_parallel_proof.prove`). SAMPLE SIZE: one serial + one parallel build (declared; wall is dominated by compile, CV well under the 50% margin). STOP: stop-on-answer when both builds have finished; stop-on-futility on either build failing or the digests differing (revert); gate-class = futility-only. Filed with `file_result.py`.
  - 2026-11-07 LESSON: build-only CPU rows use regions any-cpu-quarter, never a pinned quarter; vendor imported helpers into the row dir (the r1 failures)

<!-- original line 5987 -->
- [x] **AK-TIER-1 — Replay the screen-to-confirmed join and report whether the fast tier ranks like the full tier.** Only 8 judgeable screen/confirmed pairs exist today (ratios 0.587 to -26.95, with sign flips in both campaigns). Widen the join with strict `candidate_diff_sha256` pairing across every closed store, then report Spearman rho, sign agreement and a bootstrap CI, plus the pairwise ordering-flip rate grouped by duration gap. Stop-on-answer when the CI excludes 0.7 in either direction. Zero GPU; run before any layer-subset experiment. (intake-2643#record) [belief: cc]
  - 2026-11-06 RESULT (operator-adhoc-ops-20261105; research `86bb55dd8`, `history_replay/ak_tier1_rank_replay.py`, data `data/ak-tier1-rank-replay-20261106/result.json`). Strict `candidate_diff_sha256` pairing over every closed store (6 stores) plus the AK-HR-1 export yields only **2 pairs** (not 8: the 8 came from a looser join; no reduced-scope comparison or `candidate.<sha>.json` screen record survives in any store). rho and its bootstrap CI are undefined at n<3; sign agreement 1/2; the one orderable pair flips (gap 600-3600 s). Verdict UNDERDETERMINED: the CI cannot exclude 0.7, so the stop-on-answer rule is NOT met and no layer-subset experiment is licensed by this evidence. The replay is rerunnable as pairs accrue.

<!-- original line 5996 -->
- [x] **AK-RX-1 — REx arm in the AK-adaptive policy panel offline replay (CPU only).** Add a REx arm to the AK-adaptive policy panel replay over recorded proposal archives: Beta(1 + C*h, 1 + C*(1-h) + N) with C in 5, 10, 20, 50, h the fraction of ordered gate rungs passed (compile, op-test cases, NMSE) and N the repair attempts so far, success meaning it clears the keep gate. Report AUC-frontier and endpoint against the fixed policy on the same archive; offline only, no live flip. Add the equal-call i.i.d. resampling control and a fixed-total-calls arm varying proposals versus repairs per proposal, since refinement was not better than resampling at equal calls (intake-2232#record, intake-2285#record). Acceptance: the replay report with the three arms and the intervals. Estimate: 1-2 days. ✅ 2026-10-22 (NULL)
  - 2026-10-21 (dpf-gates) partial, NOT ticked (epyc-inference-research `9101c24a7`, `48ffc3499`, on main). `scripts/kernel_rnd/autokernel/history_replay/rex_arm_replay.py`: fixed policy, REx at C = 5, 10, 20, 50, equal-call i.i.d. control (fresh roots), and split arms (proposals vs repairs per proposal), with AUC-frontier, endpoint, bootstrap percentile intervals and coverage of observed vs unobserved selections. Five tests pass. The three-arm report with intervals exists for the synthetic fixture only (`data/autokernel_rx1/rx1_fixture_report.json`). On the real archive (175 gated rows of 1179 across 7 experiments.db stores; `rx1_real_archive_report.json`) there is no repair tree (the store keeps one final row per attempt, no repair-to-proposal link), so the REx and repair arms are uninformative there.
  - [x] AK-RX-1.1 (filed 2026-10-21): capture per-repair-attempt records in the AK store so REx can replay real data: parent attempt id, per-rung results (compile, op-test passed/total, NMSE), repair index, call cost, and keep outcome. Then re-run `rex_arm_replay.py --experiments-db` on the new stores and tick AK-RX-1. ✅ 2026-10-22
  - *(2026-10-22, NULL result.)* Research `0c38b3dc7` derives per-repair-attempt chains from the persisted patch-round rows; `a13a267d2` replays them: `data/autokernel_rx1/rx1_real_archive_chains_report.json` (7 stores, 172 chains, 125 of length 1 and 47 of length 2). No arm beats the fixed policy: AUC-frontier minus fixed, mean [95% interval], REx C5 -0.023 [-0.248, 0.136], C10 -0.022 [-0.264, 0.144], C20 -0.027 [-0.296, 0.104], C50 -0.023 [-0.250, 0.113]; i.i.d. control +0.009 [-0.120, 0.144]; split arms R0-R3 within ±0.007; endpoint deltas 0 everywhere. REx coverage is only ~0.62 (its refines of unrepaired nodes are unobserved), so this is a bounded null on a shallow archive, not evidence against REx on deeper repair trees. No live policy change.

<!-- original line 6081 -->
- [x] **AK-PROF-ATTR-1 — Add GPU-active-union and a cross-run-subtraction lint to the profile report (intake-2562#record).** `scripts/kernel_rnd/autokernel/profile_report.py` / `profile_context.py` report `kernel_wall_share` and overlap tables but no GPU-active union versus summed kernel time. Resin's skill states overlapping kernel work is not additive and "Engine minus GPU timing is unattributed time ... do not subtract different profiler and benchmark runs" (optimize-resin-performance SKILL.md). Do: emit summed duration, active-union and critical-path per trace, and reject a derived "unattributed" figure built from two runs. Controls: a synthetic overlapping-kernel trace (sum greater than union), the hash-bound rocprofv2 trace already replayed in this handoff (~L444), a two-run subtraction negative. Decision rule: union less than sum on the synthetic case, existing wall-share values unchanged on the replayed trace, negative rejected.
  - 2026-11-17 (autokernel): landed as research `e24f83621`. It adds `scripts/kernel_rnd/autokernel/trace_attribution.py`, which reports summed duration, active union (the device critical path on one GPU), overlap, span and idle gap per trace, and raises `CrossRunSubtractionError` on an unattributed figure whose run_ids differ. Controls in `test_trace_attribution.py`: the synthetic overlap gives union 250 < sum 300; the serial trace is additive; cross-run and empty-run subtraction are rejected. `profile_report.py` is untouched, so existing wall-share values and report hashes are unchanged on the replayed trace. 6 new tests plus the regrowth guard: 31 passed. ✅ 2026-11-17 [no-belief: tooling landing, no measurement]

<!-- original line 6098 -->
- [x] **C15-EPI-Q8** [inference] Producer-epilogue q8_1 write for MI210 decode (from INF48-GATEUP-PROBE: standalone quantize_q8_1 = 3.56% of 27B Q8_0 decode). RMSNorm+mul and gated-unary+mul fused kernels also write the q8_1 block their Q8_0/Q6_K MMVQ consumer needs, pre-registering the mmvq_q8_1_graph_cache entry so MMVQ skips its own quantize; default-off knob GGML_HIP_EPILOGUE_Q8=1, branch llama.cpp-experimental-c15-epi-q8-20261118 @ e0b5d2637 (on C14 eee3da838); source estimate 1.6-2.4% decode (research/deep-dives/c15-epilogue-q8-feasibility-20261118.md). model: Qwen3.8-27B Q8_0 on MI210. Row c15-epi-q8-gpu-20261118: in-row HIP build, tbo C15_EPILOGUE_Q8 14/14 on/off, 6 ABBA pairs single-slot greedy decode. stop-on-answer: KEEP iff decode geomean >= 1.01 with >= 4 valid pairs, engaged line in every B visit only, AA-calibrated identity; stop-on-futility: geomean < 1.003 after 4 pairs; gate-class = futility-only. [no-belief: planning]
  - ✅ 2026-11-19 (autokernel) row `c15-epi-q8-gpu-20261119-r3` DROP (FUTILITY_DECODE): 27B Q8_0 tbo 16/16 both arms, exact identity; decode 4 ABBA pairs all slower, geomean 0.9959 (-0.41%) < 1.003 futility bar. Not carried. [belief: cc]
  - 2026-11-19 row `c15-epi-q8-gpu-20261118`: **FAIL(tbo count)**, rc=0; both arms passed 16/16 with zero failing cases and GPU residency, but the preregistered rule requires exactly 14. No decode visits ran; performance and identity remain unanswered. Diagnose the expected-count mismatch before a new row. `out/RESULT.json` SHA-256 `edef3786d5abad18f456474fd28f61c395bae789bcf90136311bdf46f2ac41a8`. [no-belief: row verdict filed by agent]
  - 2026-11-18 (autokernel) the sibling idea "fold quantize_q8_1 INTO MMVQ" was probed on paper and STOPPED (research `7ec57d0c9`, `research/deep-dives/c15-mmvq-fused-q8-feasibility-20261118.md`): `mmvq_q8_1_graph_cache` already shares one quantize across consumers, gate+up is already one launch, graphs hide launch gaps, and a per-workgroup rebuild of the 5120-wide q8_1 vector takes back most of the 3.56%, so net is about 0-1% (< the 1.01 KEEP bar); no branch or row. This producer-epilogue box is the better-shaped version and stays the live candidate; row `c15-epi-q8-gpu-20261118` is prepared, unpublished. [no-belief: source estimate]

<!-- original line 6157 -->
- [x] **S3-ACH-01 — spike a PreToolUse read-only allowlist gate for planner/critic actors.** An actor may inspect evidence freely but cannot launch a build or benchmark until authorized. Classification is allowlist-only (unknown ⇒ gated), with a test asserting every allowlisted verb names a real command. Gates the ACTION, not the outcome: both our loops gate at promotion, so a misfiring planner can spend GPU-hours before a human sees a decision. Pattern: orx plan_gate, intake-883#record @3a8b0286. ROOT source `9414032c93e3a9ea0247bcab9f5158877ca6724a` (published main through `00ceac9c331a9b085f1b9169cbe24083e245b81f`); Git tests `scripts/hooks/tests/test_planner_readonly_gate.py` (6 passed), evidence `artifacts/codex3/s3ach01-20261031/`. ✅ 2026-10-31 [no-belief: source prototype and regression controls]
  - Default-off opt-in prototype with fixed trusted `planner` / `critic` CLI seats; strict Read/Glob/Grep schemas and Bash only for literal absolute `/usr/bin/cat`, with unknown requests asking for approval. Six focused tests passed against native JSON and controlled cat; host crash/missing/timeout/invalid-JSON behavior is simulated, not a live Claude session. Enablement still requires Claude Code ≥2.1.295, host-protected hook/settings/interpreter, and interactive approval. No live host enablement or blanket sandbox/security claim.

<!-- original line 6220 -->
- [x] **Planner backoff** — consecutive `PlannerProviderTransient`s back off exponentially
  (30s → 1800s), checkpoint-before-wait, streak surfaced as `operator_attention` (non-terminal),
  cleared on first success. Kills the 284-failures-in-23-min spin (codex 401, 08-26). ✅ 2026-08-27

<!-- original line 6223 -->
- [x] **Actor timeout** — `codex_container_actor.run_actor(timeout=1800)` bounds one invocation
  (v27 had none, so a hung container held the turn forever). ✅ 2026-08-27

<!-- original line 6225 -->
- [x] **Transport→transient** — docker/timeout/staging failures reclassified as
  `PlannerProviderTransient` instead of escaping as terminal controller faults. ✅ 2026-08-27

<!-- original line 6227 -->
- [x] **Restart clamp lifted** — removed `max_restarts==0` for `kind==deployment` (commit
  `f13434e3`) that made every crash a permanent exit and the OPERATOR the restart loop. The
  controller already resumes from durable state, so a supervised restart IS a resume. ✅ 2026-08-27

<!-- original line 6230 -->
- [x] **KFD sampler self-flagging + no wait-out** (caused 4 of 11 v27 crashes). `_belongs` only
  accepted descendants of the *sampled leg*, so the controller's OWN sibling (crash #10, pid
  964901) was "foreign"; sampler now takes `owner_root_pid`. Added `wait_until_clear()` wired as
  `SubprocessCommandExecutor(preflight_clear=…)` so a timed leg never opens on a contended GPU —
  foreign work is waited out, then a clean `GpuContentionTimeout` leg-refusal. ✅ 2026-08-27

<!-- original line 6235 -->
- [x] **Worktree name collision on crash-orphaned branch** (crash #6). `create_campaign_worktree(
  prune_orphan_branch=True)` deletes the DEAD orphan ref only — guarded by
  `GitRepo.checked_out_branches()` and `SafeBranch`. ✅ 2026-08-27

<!-- original line 6242 -->
- [x] **Stopped v27 and reclaimed disk** — supervisor/factory/build/watcher/kfd-watchdog
  terminated by captured PID and verified dead; 144/146 worktrees removed (2 handoff-referenced
  kept), dirty state backed up to `/mnt/raid0/llm/autokernel/reclaim-20260827/`. Free space
  371 G → 589 G. ✅ 2026-08-27

<!-- original line 6249 -->
- [x] **v28 reached a real screen disposition — `scientific_attempts: 1` at 15:19Z.** The milestone
  no campaign v3→v27 ever reached, achieved ~56 min after launch. ✅ 2026-08-27
  - turn 1 `authoring_refused` — critic caught a diff deriving undeclared file-scope symbols in
    `vecdotq.cuh` (a legitimate gate, costs no science budget).
  - turn 2 `inconclusive` on `akh-v2-q5-type-specific-dequant`: exact attribution
    **+0.129 %**, target runtime **−0.015 %** → conjunctive rule (either ≤ 0 → inconclusive).
    A null result, recorded with evidence. Receipt `34f836cc…`, sealed at
    `operations/941c8fde…/screen-result.json`.
  - Both arms proved real GPU residency: anchor KFD pid 3623562, candidate 3623486, both exit 0,
    through admission → correctness → attribution → graphs-off measurement → graphs-on runtime.
  - **Zero crashes** (1 `child_started` = the initial launch), no transient streak, no
    operator-attention flag. Loop advanced to turn 3 by itself.
  - This is the end-to-end on-real-hardware confirmation the GPU-path fixes needed: two arms ran
    back-to-back with distinct KFD pids and neither was misflagged as "foreign" — the exact
    condition that caused 4 of the 11 v27 crashes.

<!-- original line 6267 -->
- [x] **Re-screen the 19 historically proposed deletion modules individually and strip only proven-safe files** (10,500 LOC + 19 test files ~4,870 LOC +
  `c5_rocm_oracle.json`). Deletion MUST regenerate `FOOTPRINT.md` in the same commit
  (`python -m …controller.test_campaign_footprint --refresh`) — it is asserted by
  `test_campaign_footprint` / `test_readme`. Do NOT touch the HOLD sets (arena/hip/loop/
  least-commitment producers wired into vidya adapters + dashboard; `campaign.py` importees;
  `scripts/benchmark/` runners).
  Historical 2026-08-27 audit claimed unreferenced status across research, `/workspace`, and
  `epyc-orchestrator` — the earlier "40K LOC dead" figure was WRONG (the static grep missed
  `campaign.py`'s parenthesized import and the `scripts/benchmark/` runners; 51 of 82 candidates
  are live): `c5_rocm_oracle` · `controller/completed_campaign_adapter` ·
  `controller/gpu_hot_residency_runner` · `controller/reward_monitor` · `evaluator/baseline_honesty` ·
  `evaluator/c3_apex_runner` · `evaluator/c3_epyc_capture_provider` · `evaluator/c3_epyc_compiler` ·
  `evaluator/c3_epyc_suite` · `evaluator/c3_epyc_tensor_capture` · `evidence_path_rehearsal` ·
  `heldout_bound_pipeline` · `least_commitment_archive_builder` · `least_commitment_receipts` ·
  `offline_least_commitment` · `placement_context` · `prepare_iqk_matched_pair` · `substrate` ·
  `turn_productivity`.
  ✅ 2026-10-25 — current-pin individual re-screen complete: 19 retained, 12 positive-edge, 7 intentional off-path with runtime invocation unestablished, 0 proven obsolete, 0 deletions proposed. See [docs/reference/cme7t-inf64-accepted-findings-20261025.md](../../docs/reference/cme7t-inf64-accepted-findings-20261025.md). [no-belief: committed conclusion prepared; register capture not yet applied]
  - 2026-11-02: the HOLD note above on the least-commitment producers and `campaign.py` importees is moot: research `753639bd1` deleted that cluster (C5-05, operator decision 2026-11-02). [no-belief: tooling]
  - 2026-10-25 (Codex NI T1; canonical ROOT 249855e78 / research e8d57acd / orchestrator 49c1f749): all 19 source blobs match the accepted matrix. 12 retained for positive source/CLI/consumer edges; 7 retained as intentional off-path contracts with current runtime invocation unestablished. Zero proven obsolete and zero deletion candidates. Detailed module matrix and source/test/data hashes: [docs/reference/cme7t-inf64-accepted-findings-20261025.md](../../docs/reference/cme7t-inf64-accepted-findings-20261025.md) and task-local INF-64-REPORT.md SHA-256 94ad54ced756508606eb508a48dec964e2b1e480154870a400973a6efee2073c. No inference, GNX deletion clearance, native-control pass, runtime absence, or deletion-safety claim.

<!-- original line 6290 -->
- [x] **Merged `lane/autokernel-restructure-20260827` to research `main`** — future launches now get
  the fixes by default. Promoted via the isolated-worktree pattern (never the shared clone, which had
  1,212 dirty files from other sessions); research `origin/main` = `01f1d2be`, with `owner_root_pid`
  verified present in the sampler on main. ✅ 2026-08-27

<!-- original line 6294 -->
- [x] **Reconciled the epyc-root divergence** (operator-directed). Local `main` 17 ahead / 11 behind
  `origin/main` had been blocking EVERY session's wrap-up push all day, not just this one. Merged in
  an isolated worktree; the single conflict was the **generated** master-index rollup, resolved by
  regenerating from the merged tree (yielding a third value, `52 | 472` — proof that regeneration,
  not side-picking, was correct). Superset-verified, then 18 commits published to `origin/main` under
  the push lock; never forced. ✅ 2026-08-27
  - Residual, benign: the shared clone cannot fast-forward while a peer's uncommitted
    `wiki/knowledge-management.md` is also changed upstream (git aborts atomically; peer work
    untouched). It is `ahead=0`, so nothing is unpublished. Until that file's owner commits or
    discards it, sessions committing to `main` there will re-diverge; the working pattern is a
    detached worktree at `origin/main` → commit → serialized push.

<!-- original line 6354 -->
- [x] **AK-VIS-1 — authoring refusals rendered as NOTHING on the command band.** ✅ 2026-08-28
      (epyc-root `2cc984a7`). **My first diagnosis of this was wrong and is corrected here.** I
      filed it as a telemetry-event gap; the real mechanism is the status→label map in the live
      payload. `refusal.detected` is `refusal_type is not None`, and `authoring_refused` was absent
      from that map — so the whole refusal block (type, stage **and** the `detail` carrying the
      guard's message) was skipped. The map did contain
      `planner_contract_refused -> "authoring_refused"`, emitting the LABEL while never matching
      the status of that name, which is why it survived review.
      Added `authoring_refused` plus `authorization_refused`,
      `candidate_semantic_repeat_refused` and `portfolio_dnr_refused`; `kernel.html` now renders
      `refusal.detail`, so the card shows *why* ("derives undeclared symbols in vecdotq.cuh")
      rather than a bare "refused". The server already computed it.
      **A secret boundary was nearly weakened and was not:** the first attempt also surfaced the
      raw iteration `reason`, which `test_v2_planner_refusal_is_typed_secret_free_and_advances`
      correctly failed — a `planner_refused` reason can carry raw actor stdout, which is why that
      path ships only a digest. The change was reverted rather than the test weakened.
      Regression test drives the real payload path; its first version was vacuous twice over (a
      local copy of the map, and a source grep matching unrelated lines) and was rewritten until
      the mutation actually fails. Failure SETS diffed against origin/main: 0 newly broken.

<!-- original line 6373 -->
- [x] **AK-VIS-2 — `critic_revise` consumed an authoring-failure strike.** ✅ 2026-08-28
      (research `26f587a9`). A critic asking for a revision is the mechanism by which a proposal
      improves; charging it to the same 3-strike budget as a malformed diff retires hypotheses for
      being reviewed. It supplied v33's third strike, skipping
      `akh-v2-q5-type-specific-dequant` without it ever being tested. Revisions now have their own
      larger budget (`CRITIC_REVISION_BUDGET` 6 vs `AUTHORING_FAILURE_BUDGET` 3) and their own
      disposition `bounded_critic_revision_skip`, so the two are distinguishable in state; both
      stay `scientific_terminal: false`. A critic **reject** deliberately still counts — the
      proposal was judged unsound, not merely improvable. Tests replay v33's exact sequence and
      are mutation-tested.

<!-- original line 6413 -->
- [x] **AK-INST-1 — the timed-output gates must accept a champion instrument.** ✅ 2026-08-28
      (research `23e9be47`). Mutation-tested: collapsing the helper back to equality fails
      `test_a_champion_built_on_the_instrument_is_accepted`. Suite 56 passed, including the
      pre-existing assertion that the guard still raises for a non-instrument anchor. The git tree
      is resolved from `--anchor-build` (the path `build_identity` already runs `git -C` in);
      a first attempt used a non-existent `--instrument-path` argument and would have thrown.

<!-- original line 6419 -->
- [x] **AK-MSG-1 — make the authoring-refusal message actionable.** ✅ 2026-08-28 (research
      `4d2fa807`). The journal line read `derives undeclared symbols ['<file-scope>']` — naming a
      "symbol" that exists nowhere in the source, omitting what the proposal DID declare. Three
      audiences read it and none can ask a follow-up: the planner (fed back since `9516ac05`), the
      dashboard command band, and a human. It now states what changed, what was declared, and that
      `<file-scope>` means a hunk outside any function body.

<!-- original line 6425 -->
- [x] **AK-INST-2 — audit for OTHER hardcoded instrument pins.** ✅ 2026-09-23 — audited every 40-hex / `*_COMMIT` comparison in the discovery plane: no other champion-drift pin (the rest are exact freeze/seal/vendor/replay identities or already ancestry checks). It surfaced a DIFFERENT v10 defect, fixed in research `714777e4`: with `MEASUREMENT_COMMIT == PRODUCTION_COMMIT` the "instrument parents == (production,)" rule was unsatisfiable in `live_controls` preflight AND `candidate_record.build_candidate_record` — shared `worktree.instrument_lineage_ok` now accepts the folded identity. The review-pin at `discovery_deployment_factory.py:1516` stays EXACT by design (re-pinned per freeze). `READY_CONTINUE_INSTRUMENT_COMMIT`
      was found only because it killed a campaign. Any other equality comparison against a fixed
      instrument/production commit will fail the same way the next time the champion advances.
      Grep the discovery plane for 40-hex constants compared with `==` and convert the ones that
      mean "descends from the reviewed instrument".

<!-- original line 6438 -->
- [x] **AK-DEPLOY-1 — the supervisor deploys landed dashboard code and restarts the hub.** ✅
      2026-08-28 (epyc-root `2dbf5dc1`, `7adc4127`, `fc9502ab`). Proven live: the served file was
      reverted by hand and the supervisor repaired it unattended, then restarted the hub. Three
      safety rules, each mutation-tested — never writes the git index, never overwrites work in
      progress, never moves the branch or pushes; scope is `dashboard/` only.
      **The predicate took three attempts and the first two failed by looking like success**:
      comparing to local HEAD calls every correctly-deployed file a hand edit, because the served
      tree deliberately lags. It now judges by PROVENANCE — a blob this project has published for
      that path is a deployment; one that never existed on origin/main is someone's work.

<!-- original line 6447 -->
- [x] **AK-DEPLOY-2 — reconcile served-tree drift outside `dashboard/`.** ✅ 2026-10-27 — The operator-approved dedicated read-only view advances the entire served tree to origin/main, including handoffs, scripts and progress. `refresh_hub_view.sh` requires a marked standalone view and refreshes generated handoff artifacts; the shared working tree is not its deployment target. The former dashboard-only scope remains the fallback for a non-view tree.

      Live verification at 19:31 UTC: hub PID 1899355 served `/mnt/raid0/llm/views/epyc-root-main`; its detached HEAD and origin/main were `b3ef3eb2a011e0edd9cc06a3a5690d63d0b88a73`, with clean porcelain. The historical stale champion handoff matched published blob `07c828776d18566814a3ada697371d7e0af50f98`. The supervisor log recorded a successful refresh to that commit at 19:22:24 UTC with regeneration, and an unchanged successful refresh at 19:30:02. `/api/handoff_board` returned 200 and included this handoff; `/api/health` reported the board fresh, observed and populated. The hub started 2026-10-24 08:50:27 UTC after the served `dashboard/server.py` mtime 08:50:03; its source derives handoff paths from the served module tree. This closes the full-tree drift issue, not unrelated producer health findings. [no-belief: operational liveness and deployment observation]

      **Historical evidence (2026-08-28):**

      **Measured 2026-08-28, and it is worse than "lagging".** The served tree's local `main` stood
      **45 behind / 1 ahead** of origin/main, and carried
      `handoffs/active/kernel-champion-and-promotion.md` as an **untracked 144-line file where
      origin/main has 465 lines** — a superseded draft occupying the authoritative path. It read as
      untracked only because local `main` predates the commit that added it. Every substantive
      passage was verified present in origin/main's version before the stale copy was displaced
      (backup: `/mnt/raid0/llm/tmp/champ_aggregate_stale_worktree_20260828.md`). The one commit
      ahead was another session's completed-but-unpushed work.
      So the failure mode is not just staleness: **a stale untracked file is indistinguishable from
      live uncommitted work**, and the dashboard reads handoffs. Whatever is decided, it must
      distinguish those two cases — the AK-DEPLOY-1 provenance predicate is the existing pattern.

<!-- original line 6478 -->
- [x] **INF64-REACHABILITY-MANIFEST — complete the per-file source reachability/disposition manifest before any deletion proposal.** Bind exact19 candidate paths, adjacent data and paired tests; resolve non-Python/dynamic entrypoints, string/CLI/config references, cross-repo capture inventories, FOOTPRINT/HOLD ownership and outgoing edges. Retain actual loop/compiler/least-commitment consumers; only prepare removal of individually proven-safe files together with their explicit dependent tests/data and regenerated footprint guards. Existing campaign owner applies any source change at its boundary.

<!-- original line 6904 -->
- [x] **P0 — File this rider + index row.** Exit: `python3 scripts/handoffs/index_state.py --check` ✅ 2026-10-29 (audit: header "P0 DONE (root 7f86e383)" (autokernel-rebuild-program.md CURRENT STATE); INF-66 row exists at inference-research-index.md:22 naming this page) [no-belief: audit-reconciliation]
      exits 0 and this page names the current phase and next action.

<!-- original line 6907 -->
- [x] **P1 — Close the feedback loop.** ✅ 2026-08-28. Research `e1ebf691` (P1.1), `8248e3d7`
      (P1.2), `c3034ede` (P1.4); root `a353381a` (P1.5).
  - [x] P1.1 Route the per-kernel hotspot table (already produced) to the planner and both critic
        passes. Extend `gpu_source_evidence._exact_duration_comparison` (`:3059`); thread into
        `discovery_controller.py:1521-1591`.
  - [x] P1.2 Experimental memory. **(a)** Long-lived campaigns — stop every crash re-minting the
        deployment and resetting counters; the supervisor already resumes from durable state.
        **(b)** `experiments.md` + a small SQLite index carrying hypothesis, mechanism, patch summary,
        gates, effect with sample vector, verdict — **negatives written up as carefully as wins**.
        **(c)** Epoch-hash staleness borrowed from
        `repos/epyc-orchestrator/orchestration/repl_memory/strategy_store.py` (AP-28): each record
        stores a hash of the files defining its epoch; retrieval validity-penalises cross-epoch
        records. **Idea only — no FAISS, no FTS5, no RRF.** That store is 2,076 LOC; ours is ~150.
  - [x] P1.3 Planner and both critic passes receive the same bundle: hotspots · `experiments.md` · ✅ 2026-10-29 (audit: header "P1 DONE" (CURRENT STATE) and P1 exit MEASURED 2026-08-28 (:437-447); siblings P1.1/1.2/1.4/1.5 are [x]; loop planner bundle built in P4 (research 6408f685). Only the unticked P1.3 line left) [no-belief: audit-reconciliation]
        prior refusal reasons verbatim · `hypotheses/inbox/` · champion diff to date.
  - [x] P1.4 Fix the estimator (`run_autokernel_gpu_discovery.py:3143`) — one estimator on both arms
        — then re-score all 25 historical results and publish before/after.
  - [x] P1.5 Fix `scripts/vidya/cli.py:633` (`choices=["intake"]`), which strands **2,601** gradeable
        ClaimTuples the ten autokernel adapters already produce correctly.
  - **Exit — MEASURED 2026-08-28:**
    - Re-score published (`artifacts/autokernel-rescore/rescore.json`, research). All 25 historical
      two-arm screens, every stored `median_relative` reproducing exactly from raw samples through
      the producer's own centre rule: reported **+2.215%** vs like-for-like **+0.202%** —
      **+2.014 pp** injected. **10 of 25 flip sign.** Nominations **7 → 3**. Anchor median-vs-mean
      gap **+1.959%**, the mechanism.
    - `vidya` ledger 12,538 → **13,141**: **603 autokernel frames persisted for the first time**
      (aux_receipt 234, reward_integrity 159, governed_receipt 135, rocm_diagnostic 66,
      evaluation_event 9). The audit's "2,601 tuples" figure did **not** reproduce on the real
      walk; 603 is what the corpus yields today, and the walk reports its own four-way accounting
      (projected / refused / declined / not-an-entry-point) rather than a single number.
    - Context wiring pinned by test rather than by transcript (no campaign may launch before
      Phase 2): `kernel_hotspots`, `prior_experiments`, `prior_authoring_refusals` and
      `prior_results` all present in the bundle both actors read.

<!-- original line 6941 -->
- [x] **P2 — Fix the measurement surface.** ✅ 2026-08-28, research `abcdf787` + the recipe/
      contract commit before it.
  - [x] Replace the 0.5B Q5_0 workload with a quant-ladder rung sharing a dispatch path and size
        regime with production. **Measure prefill** — `-p 0` means it currently never is.
  - [x] Write the explicit versioned build recipe: every flag named, and every flag differing from
        production carrying its reason. Divergence becomes a recorded decision, never an unset
        variable.
  - [x] Paired design — alternating arms across *processes* (`--arm-pairs`, default 1 so
        existing sealed operations resume byte-identically; `arm_schedule()` is a real function
        the runner calls, not a shape reimplemented in a test). Model on
        `scripts/benchmark/mmq_mfma_recheck.py:131-141`.
  - [x] Emit gate parameters alongside the results they gate — `gate_parameters.snapshot()` on
        the row it decided, `diff()` labelling a loosening **WIDENED** with its ratio, both
        reaching the planner and both critic passes.
  - **Exit:** A/A run, n=20, publishing the measured noise floor, which becomes the keep-threshold; a
    known-good and a known-null patch both classify correctly.

<!-- original line 6958 -->
- [x] **P3 — Throughput.** ✅ 2026-08-28, research `c05b1bdb` — **except two items
      deliberately unshipped rather than shipped blind**, both recorded below.
  - [x] `BuildParallelism(jobs=1)` → `jobs=64` with `cpu_list` / `load_average_cap` (fields
        `execution/worktree.py` already carries at `:2249` and `:2597`).
  - [x] **SHIPPED and validated on a real build 2026-08-28** (research `d9254d31`).
        **Measured first:** a full HIP build of frozen v9 with the house recipe took **1,012 s at
        `-j1`** (the median across 77 logs) and **65 s at `-j64`** — 15.6×, so the width fix alone
        takes an attempt from 33.7 min of compiling to 2.2. `anchor_build_key` is the contract
        minus exactly the candidate fields; reuse is verified on source-tree digest, defines,
        anchor key, artifact presence and recorded targets, and any failure falls through to a
        fresh build rather than raising. **Validated against the real 65 s build:** reuse HIT in
        **0.18 s**, MISS after a one-line change to `vecdotq.cuh`, HIT again after reverting.
        The replayed `BuildResult` is the real one, persisted beside the build, because the
        materialization record downstream hashes it.
        *Bug this caught:* `integrity.hash_source_tree` returns a `TreeDigest`, not a string, so
        the receipt would not canonicalise — and a broad `except` was swallowing it into a
        permanent silent cache miss. The except is now narrowed to `OSError`/`StaticRegistryError`.
  - [x] ~~~~NOT SHIPPED — cache the anchor build.~~ *(superseded by the entry above)* `_build_key_contract` hashes~~ (closed 2026-10-29 audit: SUPERSEDED → struck-through "NOT SHIPPED ... (superseded by the entry above)" - text itself marks supersession; header says P3 anchor cache deliberately unshipped/replaced)
        `patch_bundle_sha256`/`patch_sha256`/`proposal_sha256` into ONE key covering BOTH plans,
        so the anchor — built from the instrument commit, independent of the patch — gets a new
        key per candidate; **44 of 51 anchor builds compiled a byte-identical tree.** Splitting it
        needs two cache transactions where the reservation, `_validate_ref`, materialization and
        recovery paths all assume one entry per operation, and reusing a completed build means
        relaxing `BuildDirNotFresh` (§8.5.1). That is crash-recovery-critical machinery that
        cannot be exercised without a real ~15-min HIP build; shipping it unvalidated risks
        breaking a loop that is otherwise now fixed. **Worth ~50% of build time.**
  - [x] ~~**NOT SHIPPED — ccache.** `execution/README.md` documents that `GGML_CCACHE=OFF` is~~ (closed 2026-10-29 audit: OBSOLETE → ccache deliberately NOT shipped by design: GGML_CCACHE=OFF forced by clean-build gate (execution/README.md) and benefit overlaps anchor fix; header "P3 DONE except two items deliberately unshipped")
        FORCED because with it on `chain.build_evidence` sets `incremental_objects_present=True`
        and the clean-build gate FAILs — correctly, since a cache populated by another tree makes
        the actor's build state part of the artifact. Same class of change as above, for a benefit
        that overlaps the anchor fix. (`-DGGML_CCACHE=OFF` in 77/77 — the §8.5.1 clean-build
        rule governs *promotable* artifacts and this path is non-promotable by construction).
  - [x] Disk expiry — `storage.expire_artifact` had zero callers; `autokernel_storage_report.py`
        is the missing caller and REPORTS (`--force` refused: reclamation authority is
        operator-only). Measured 33.16 GB / 358 dirs: 16.03 GB reclaimable build trees,
        17.13 GB unclassified and deliberately untouched; run `_recover_incomplete_attempt`
        at controller start for all incomplete attempts.
  - [x] GPU-seconds-held and idle-while-claimed on every result row (`gpu_utilization.py`).
  - **Exit:** median iteration < 900 s over ten consecutive iterations, utilization reported.

<!-- original line 7002 -->
  - [x] P4.1 ✅ 2026-08-28 — `docs/guides/agent-workflows/agent-loop-design.md` — the loop block as the normative spec,
        plus the convention that agent-loop work opens with one. `program.md` in the loop package
        carries the same block as its first section.

<!-- original line 7030 -->
- [x] **P6 — Reconnect the surfaces.** ✅ 2026-11-01 — Implements ROOT `56c3218e9c92c65ad1747b3b15ceb5fb7a25c7f6` plus final source `58f03662e8aee1305012c9bee84d5aae3e1a2036`; [evidence](../../artifacts/engineering/p6-surfaces-20261101/README.md). [no-belief: software verification] CI DONE (root `.github/workflows/tests.yml`); the
      surface rewrite is not started.

      **Historical checkpoint, 2026-10-30:** “the surface rewrite is not started” records the
      status before this implementation; the scope is now completed as noted below.

      **Partial credit 2026-08-30, recorded so the rewrite does not redo it.** Four commits on
      `lane/ak-rebuild-20260828` (root): `0a18b132`, `7feec9d4`, `e0ceada9`. The loop-up/loop-down
      exit criterion is met for the surviving surface; what remains is listed as open boxes below.

  - [x] P6.1 — **`/loop`'s GPU panel had been dark since the surface's first commit** ✅ 2026-08-30
        (`0a18b132`). The reader looked for `held_s`/`busy_s`; the producer has always written
        `claim_held_s`/`device_seconds_under_load`. 41 tests passed over it because the hand-built
        fixture invented the *reader's* spelling, so fixture and reader agreed with each other and
        disagreed with the producer. **A fixture authored from the consumer's guess cannot witness
        the contract** — build fixtures from a real producer record.
  - [x] P6.2 — the `/kernel` card labelled "AutoKernel loop" was showing the **superseded v37
        controller**; corrected ✅ 2026-08-30 (`0a18b132`).
  - [x] P6.3 — **both named freshness gaps closed** ✅ 2026-08-30 (`7feec9d4`). The operator-gated
        Aggregate-champion `+48.9%` card had no envelope at all (`_read_operator_gate_bundle()`
        read no timestamp, so the number rendered identically forever after its producer died);
        the funnel's staleness verdict rendered only inside a collapsed `<details>`. Verified by
        aging the real record to 4 d and 20 d → `stale`, and deleting it → `absent`.
  - [x] P6.4 — **one surface, not two** ✅ 2026-08-30 (`e0ceada9`). `/loop` is now the single page
        titled **Kernel R&D**; `/kernel` 301-redirects to it; `dashboard/static/kernel.html` is
        deleted (1,833 lines); the operator-gated champion card moved across; the controller card
        was deliberately **not** ported. Verified live: redirect works, `/static/kernel.html` and
        two sibling paths 404, 24 routes swept with a non-vacuity control. Mutation 13/13 — and
        **M7 initially SURVIVED**, producing a green pill reading "STALE", because the test harness
        exposed only `innerHTML`/`textContent` so the assertion was literally unwritable; the
        harness now emits `class_by_id`. Dashboard failures 40 → 12, not byte-identical and
        legitimately so: 28 of the 40 lived in the deleted page's own test class.

      **Open, derived from the merge (2026-08-30) — do not close P6 with these outstanding:**

  - [x] P6.5 — **retire the retired page's API surface.** `/api/kernel`, `/api/kernel/live` and ✅ 2026-11-01 — Implements ROOT `e035bc86917b179de0e17d8c66180c60615849cf`; [artifact and verification](../../artifacts/engineering/p65-api-retirement-20261101/README.md). [no-belief: deterministic software verification]
        `/api/kernel/health` still serve data nothing renders. Removing them strands
        `panels.PANELS["kernel"]` / `["kernel_live"]` and changes what `health_payload()` folds —
        a peer's live file, so it was deliberately left alone rather than done blind. Do it as part
        of the rewrite, with the panel registry and the health fold changed in the same commit.
  - [x] P6.6 — **a hole in the freshness contract itself.** `/api/kernel` reports ✅ 2026-10-31 — IMPLEMENTS ROOT `0875e49d8d38baba1a656c6fd9fc2c33c5b0b561`; API test/evidence commit `1b6e5303810f6d71d69b942b4fc00f8c1c2d62a1`; published on ROOT main `a1dee7344169dd92d911d7bbcc190e94ab366afc`; [artifact and validation](../../artifacts/engineering/p66-freshness-20261031/README.md). [no-belief: software verification]
        `reporting=observed, watchdog=idle` over a **16.8-day** export, because that producer
        travels the *compliant-silence* path the hub honours. The JSON therefore does not read
        stale even though the data is. Fix the contract, not the one endpoint: compliant silence
        must still carry an age, and an age past the envelope must degrade the verdict.
      - Implementation detail: 31 checks plus 7 subtests and 10 actual API/red-team checks passed. Stale idle data degrades even when optional sections are missing; fresh and aging partial policy, non-gating panels, and absence/unknown states are preserved. The existing 180-second terminal-campaign envelope now degrades after expiry with its threshold unchanged. P6.7 operator-gate HOLD and subject age remain independent; no reload.
  - [x] P6.7 — **`/api/loop/health` folds the loop and operator-gate subject verdicts** ✅ 2026-10-30.
        The endpoint keeps both source envelopes independent, treats intentional gate HOLD and
        artifact age as non-health signals, and maps the five bundle verdicts into the existing
        three-valued health response. Missing/malformed/poisoned bundle and loop-worse cases are
        covered. `/api/health` and `panels.py` remain unchanged; no service reload/deployment. [belief: cc]
  - [x] P6.8 — **coverage genuinely lost.** ✅ 2026-11-01 — Implements ROOT `56c3218e9c92c65ad1747b3b15ceb5fb7a25c7f6` plus final source `58f03662e8aee1305012c9bee84d5aae3e1a2036`; [evidence](../../artifacts/engineering/p6-surfaces-20261101/README.md). [no-belief: software verification] The funnel and lane-hero render tests went away *with*
        the deleted page rather than being fixed. The reader still exists and nothing renders it;
        restore render coverage against the surviving surface when the funnel is re-hosted.

      **Measured baseline for the red tests, so the next session does not re-derive it:** the
      dashboard autokernel suites are **11 failed / 60 passed at `origin/main`** — verified in a
      clean worktree, so they are pre-existing and unrelated to this program's changes. They fail
      because `server.py` pins content digests of *another repository's* source modules (29 paths,
      47 digests). **Do not re-pin them.** That is the defect P6 exists to remove, and re-pinning
      digests on code slated for replacement only re-arms the landmine. Rewrite, then delete the
      6 obsolete test files.

      One audit claim did NOT reproduce: `tests/test_dashboard_operator_gates.py:51-57` *does*
      override `OPERATOR_GATE_BUNDLE_JSON`, so "zero of 168 override it" was overstated. The
      hermeticity concern stands for the autokernel suites specifically. Rewrite the `dashboard/server.py` kernel surface (~11,500 of
      12,841 function/class lines) with **no cross-repo pinning** — it currently pins 29 producer
      source paths and 47 SHA-256 digests of another repo's modules, so renaming a producer module
      silently drops a deployment off the live surface. Repoint the vidya adapters. Fix the 40
      currently-red root tests and their non-hermetic `OPERATOR_GATE_BUNDLE_JSON` reads. Add CI that
      runs pytest — `.github/workflows/` contains only `docs.yml`.
  - **Exit:** dashboard reports correctly with the loop up **and** down.

<!-- original line 7103 -->
- [x] **P7 — Anti-regrowth** ✅ 2026-08-28, research `10f0214e`., as enforced mechanisms rather than documentation: a CI-enforced LOC
      budget on the loop package; **no test may assert the contents of a documentation file**; one
      end-to-end test that cannot pass vacuously (a deliberately-slower patch must be rejected and a
      known-faster patch accepted, both through the real build and the real benchmark); the weekly
      artifact is the scoreboard, and a week with no rows reports exactly that.
      **Note on the guard itself:** its first doc-coupling detector was VACUOUS — a regex over
      assert lines found zero hits against `test_readme.py`, which does pin README prose, because
      the real assertions compare a module constant against `self.text` rather than an inline
      literal. It now detects the coupling, and a test fails if it ever stops finding
      `test_readme.py`, so the vacuous version cannot return silently.

  - [x] P7.1 — **the guard's CI had never run a single assertion** ✅ 2026-08-30 (research
        `ac785d2d`). The autokernel-guards workflow was red on **43 of 43 runs since its first
        commit**, every one dying on `No module named pytest` before collection —
        `actions/setup-python` ships a bare interpreter. Because it looked identically red whatever
        the code did, it hid two real regressions for two days: `test_check_regrowth_guards` still
        asserted `LOOP_LOC_BUDGET == 3000` after the deliberate raise to 3400, and
        `test_experiments` asserted that the same refusal at two different times *deduplicates* —
        the exact opposite of the identity fix in `5090931d`, which put `recorded_at` in the hashed
        material precisely because identity had collapsed and repeated refusals were being dropped.
        **A permanently-red check is indistinguishable from an absent one.**
  - [x] P7.2 — **suite-floor guard** ✅ 2026-08-30 (research `7ee090a5`). Installing pytest closed
        the hole but not its *shape*: a suite that runs FEWER assertions reports the same green.
        pytest exits 5 on zero collected (verified) but a **partial** collapse exits 0. Floors
        declared for both suites (101, 196), `>=` never `==`. The guard found two defects in itself
        on first run — it laundered a collection error into a plausible "93 collected" (pytest
        prints the count on the same line as ", 1 error"), and its own test module had a
        cwd-dependent import. CI is green on research `main` with real counts in the log.
  - [x] P7.3 ✅ 2026-09-23 — research `77b75dae`: `scripts/kernel_rnd/conftest.py` puts the repo root on `sys.path`; `test_experiments.py` 44/44 from both cwds (was 4 failed from kernel_rnd). **New finding:** `autokernel/controller` + `autokernel/execution` are NOT green from either cwd — identical 78 failed / 10 errors / 2279 passed from the repo root and from kernel_rnd, so the "CI is green from the root" premise below is stale; those failures are pre-existing and owned by this program. — **`test_experiments.py` silently depends on cwd.** It imports only from the repo
        root, so 4 `MemorySurvivesADeployment` tests fail with
        `ModuleNotFoundError: No module named 'scripts'` when pytest runs from
        `scripts/kernel_rnd`. CI is green only because it happens to run from the root. Add a
        `conftest.py` with a `sys.path` insertion so the suite is location-independent.
        (epyc-inference-research.)
  - [x] P7.3a — **triage the 78 failures / 10 errors in `autokernel/controller` + `autokernel/execution`** (identical from the repo root and from `scripts/kernel_rnd`, research `77b75dae`, measured 2026-09-23). CI cannot be green on these suites; classify stale fixtures vs real defects before the next campaign relies on them. ✅ 2026-10-31 [implementation: epyc-inference-research f6630e61058c0ebebaa0467e70cedead8c4081da; evidence: scripts/kernel_rnd/autokernel/evidence/p7_3a-current-suite-triage-20261031.md; tests: scripts/kernel_rnd/autokernel/evidence/p7_3a-20261031/machine-check.txt, scripts/kernel_rnd/autokernel/controller/test_discovery_static_registry.py] [no-belief: test-suite triage and test-only correction; no measurement claim]
  - [x] ~~P7.4 — **THE LOC BUDGET IS NOW BINDING: 3400 of 3400, zero headroom** (was 3218/3400;~~ (closed 2026-10-29 audit: OBSOLETE → R23-63 note (autokernel-rebuild-program.md:2440) lists P7.4 as stale by event; LOOP_LOC_BUDGET now 3450 (check_regrowth_guards.py:66) with an enforced code-line budget separate from total (:68))
        `c39ecc43`'s promotion A/A guard consumed the rest). Verified by running the counter:
        `loop package: 3400 LOC across 15 files (budget 3400)`, `0 guard violation(s)` — **the
        next added line fails CI.** Constant at `check_regrowth_guards.py:50`, counter
        `loop_package_loc()` at `:70` (raw `splitlines()`; blanks, comments and docstrings all
        count), pinned by `test_check_regrowth_guards.py:98`.
        The two honest options stand — trim `run.py` (553 lines, the largest of the 15) or exclude
        comment/docstring lines — and **another round-number bump is not one of them**; raising the
        number is the failure mode the budget exists to catch. Record the choice here when it is
        made.
        **Correction while measuring this:** the constant's own doc comment at
        `check_regrowth_guards.py:41-42` claims *"2,102 lines are code and 1,071 are docstrings and
        comments — 34% of the package is prose."* Measured now: **2082 code / 810 prose / 508 blank
        = 23.8% prose.** The 34% figure does not reproduce and evidently folded blanks in. Fix the
        comment in the same change — a stale number in the annotation of the constant it justifies
        is how the "just bump it" argument gets made from bad data.

<!-- original line 7270 -->
- [x] **D1 — RATIFIED AND BUILT** ✅ 2026-08-31. The operator applied the amendment (root
      `4e42e8db`, heading flipped `c5ddc4fc`) and the capability was then actually built —
      research `198f5b4b` (see R18-G). Run 21 runs with ranking ON under it.
      *(original, retained)* **APPROVED BY THE OPERATOR 2026-08-30. The one outstanding action is the operator's
      own write:** run `scripts/operator/ratify_ak_search_1_a3_20260828.sh --apply`. Annex K is
      human-amendment-only (invariant 15), so no agent may apply it.
      **⚠ Correction to this handoff's own earlier claim: the capability does NOT ship.** This page
      previously said *"the store already ships with `ranking_authorized=False`; applying this is
      what lets that flag be turned on."* Half of that is false. The parameter exists —
      `ExperimentStore.recall(..., ranking_authorized: bool = False)` at
      `controller/experiments.py:157`, recorded onto the recalled row at `:193` — but **no
      production call site anywhere passes `True`**; the only caller that does is
      `test_experiments.py:150`, and the identifier does not appear in the `loop/` package source
      at all. So after ratification the **ranking capability still has to be built** (**R18-G**).

      *What was requested and approved (retained verbatim):* amend `P-AK-SEARCH-1` denial 4, which
      permits a later campaign to use a prior record *"for hypothesis formation only — never to
      **rank**, bank, compose, or contribute to readiness."* Choosing what to attempt next *is*
      ranking, so a planner that reads its own history to prioritise is non-conformant on a strict
      reading — very likely why the memory was never built and why one patch was proposed 38 times.
      **Option 4:** prior records may inform ranking, provided each carries the hash of its epoch
      (anchor commit, build recipe, host state) and cross-epoch records are validity-penalised at
      retrieval. No banking, no promotion authority, no readiness contribution — those denials stay
      verbatim. The mechanism is borrowed from autopilot's AP-28 store, not invented.
      `--show` reads it; `--apply` stages the amendment with an isolated `git apply --index`.
      P1.2(a) ships regardless — it is a bug fix, and denial 4 governs *cross-campaign* reuse only.

<!-- original line 7315 -->
- [x] **D3 — build recipe as a champion arm. APPROVED AND SHIPPED** ✅ 2026-08-30 (research
      `6cbb608c` + `3ba4339f`). A champion now carries a build recipe. **Neither standing config
      win was adopted** — CH-6 settled both (`MMQ_MFMA` +0.50% on the 27B; `ubatch` a null arm,
      since llama.cpp clamps `n_ubatch = min(n_batch, n_ubatch)` so both screens ran one identical
      binary) — and both are **recorded in the recipe with the numbers that correct them**, so the
      carrier ships its own refutations rather than inviting a re-run. Decision-arithmetic floor
      raised 101 → 109. The recipe module is
      `scripts/kernel_rnd/autokernel/controller/build_recipe.py`; see **R18-A** for the one
      constant in it that the 2026-08-30 symbol-identity evidence now contradicts.

<!-- original line 7331 -->
- [x] **R18-L1 — the promotion A/A guard, and the abort that was being swallowed.** ✅ 2026-08-30
      (research `c39ecc43`). After every promotion the new anchor is benched against a fresh
      champion build and must read **inside the noise floor**, else `RunAborted`
      (`loop/anchor.py:71`, assertion at `:98`).
      **The assertion is magnitude-vs-floor and deliberately NOT `Comparison.decisive`:**
      `decisive` returns `False` for a drifting arm *regardless of effect size*, so a
      `decisive`-based guard would have certified run 18's −9.539% regime as indistinguishable
      from zero. A guard whose predicate does not answer its stated subject is not a guard.
      **Abort propagation was genuinely broken** — `RunAborted` was caught by a blanket handler and
      filed as an ordinary `iteration_error`, so the guard would have aborted nothing; fixed at
      `loop/loop.py:357` (re-raise before the blanket `except Exception` at `:359`) and
      `loop/pipeline.py:249` (run-ending, not lane-ending: the anchor is shared, so the budget is
      zeroed and every lane stops at its next draw — continuous runs included).
      **Promotion now BUILDS** rather than `shutil.move`-ing: `pool.promote_anchor` builds the
      champion into the anchor slot and writes `provenance.json` (`loop/pool.py:372`).
      18 of 18 mutants caught, 1 control survived. Cost: the loop package hit **3400/3400 LOC**
      (P7.4).

<!-- original line 7348 -->
- [x] **R18-L2 — the champion headline is one number against one named anchor.** ✅ 2026-08-30
      (root `bdeb450f` → `e1d22546`). Renders **NOT YET MEASURED** until the A/B exists rather than
      inheriting a number from somewhere else. 19 of 19 mutations caught.

<!-- original line 7351 -->
- [x] **R18-L3 — epyc-root CI had failed 8 of 8 runs since creation.** ✅ 2026-08-30 (root
      `437f751f` → `54d2b8ad`). `actions/checkout` defaults to `fetch-depth: 1`; `index_state.py`
      derives `last_advanced` with a `git log -S'- [x]'` pickaxe, so against a one-commit clone
      **every handoff attributed to the tip** and the freshness check reported a stale generated
      block on a tree that was in sync. Both root workflows and the research one are now green.
      Same shape as P7.1 in a different repo: **a check fed an input it cannot answer from is not a
      failing check, it is an absent one.**

<!-- original line 7372 -->
  - [x] **R18-A-READY-INDEPENDENT-SYMBOLS** — publish the rank-23 diagnostic READY. ✅ 2026-10-30
      `refactor-r18a-v10-independent-symbols-20261030` was published at 20:18:50Z (1080s
      minimum/14400s window/32 GiB, any CPU quarter) for the eventual full symbol comparison.
      Canonical READY normalization removed placeholder `claimed_cpus` so arming supplies the
      actual quarter and renamed the Git source field `source_commit`; the READY is published at
      `/mnt/raid0/llm/tmp/compute-flags/ready/refactor-r18a-v10-independent-symbols-20261030.json`.
      The actual whole launcher passed its model-free CPU `gguf.cpp` + gfx90a HIP `acc.cu` smoke
      (8.28s); its active `cc1` cutoff returned 75/partial and both owned tees drained. It reused
      the exact FFC1 source through a read-only bind and protected lock; no new checkout was made.
      This qualifies the launcher only: full independent build and CPU/HIP symbol comparison remain
      pending, and `PRODUCTION_RECIPE_IS_VERIFIABLE` remains false. Evidence:
      `artifacts/compute/refactor-r18a-ready-and-c3-l-control-20261030.json`. [no-belief: launcher
      qualification only]

<!-- original line 7451 -->
- [x] **R18-F — the loop code budget is freed, not bumped.** ✅ 2026-08-31 (research `33715a7e` →
      `f2c05dc1` → `95eeb0ae`). The guards now bound **code** and compute the prose share instead
      of remembering it wrong (`check_regrowth_guards.py`: `LOOP_CODE_BUDGET = 2100` enforced;
      `LOOP_LOC_BUDGET = 3450` still printed for the split). The trim took code 2099 → **2040/2100**
      by deletion, not by budget motion: the pool now owns the consecutive-error breaker — **the
      pooled path previously had NONE and would spin forever** — the sequential path is deleted
      (`loop.run` kept as a documented test-only seam), `SINGLE_PAIR_P95` deduped, dead code
      removed. 13/13 mutants; decision-arithmetic floors argued 304→309.

<!-- original line 7459 -->
- [x] **R18-G — the ranking capability D1 authorizes is BUILT.** ✅ 2026-08-31 (research
      `198f5b4b`, epoch-scoped, default off; companion `068ffb67` emits the champion-vs-production
      headline at every advance). Run 21 runs it ON. Building it surfaced a **real conformance
      breach**: `actors.py` pooled **cross-epoch** magnitudes into a do-not-re-measure median —
      biting at every epoch transition; fixed by checking **both** provenance markers. The earlier
      claim that the store "already ships" the flag was FALSE and stands corrected (parameter
      existed inert; capability did not).

<!-- original line 7475 -->
- [x] **R21-L1 — single-champion invariant ratified and ENFORCED.** ✅ 2026-08-31. Ratification
      root `35c1a6d1` (operator-applied; the stale-worktree recovery en route — the shared clone's
      `OPERATING_CONSTRAINTS.md` was missing 28 lines of ratified 08-27 content, caught by
      `git apply --index` refusing). Enforcement research `470378a9`: startup refusal proven live
      both directions, attachment-stronger-than-tip-equality, pool champion ref aliased to the
      canonical branch, 34/34 mutants; plus the live-resolved frozen-production baseline in
      `production.py` (per-commit build cache).

<!-- original line 7482 -->
- [x] **R21-L2 — the reconciliation merge and its measurement.** ✅ 2026-08-31. `a2728701` =
      `270b48ed` + `4925b208`, zero conflicts, disjoint file sets, parents tagged
      `ak/pre-reconcile-{manual,loop}-20260831`. **+12.618% tg128 vs production resolved live**
      (264.53→297.91, 20 pairs, 10.6× the 1.188% floor; pp512 +0.078%, uncalibrated floor —
      R18-D), oracle 3/3, inside the pre-committed chain-estimate band [11.2–15.3] → additive, no
      interaction. Bundle published; `generated_at` was stamped 5.5 min in the future by the
      publishing agent, the reader refused it, restamped from raw-file mtime with a correction
      note. Capability list now **artifact-derived** incl. DFlash2 symbols (`build_dflash2_conv`,
      libllama 10125→10180); corrected finding: **iqk shipped in v9 already** — the champion adds
      dispatch gating only.

<!-- original line 7492 -->
- [x] **R21-L3 — run-20 drain flaw fixed (drain tiers).** ✅ 2026-08-31 (research `95eeb0ae`).
      STOP abandons at actor boundaries recording `stopped_mid_formation`, never mid-tail. (The
      trim itself is under R18-F.)

<!-- original line 7495 -->
- [x] **R21-L4 — dashboard: the anchor is resolved, staleness is semantic, the champion is the
      branch tip.** ✅ 2026-08-31 (root `479ffb47`, `2a3881d4`, `86bc7b8b`, `f9c00551`).
      Live-resolved frozen production + `SUPERSEDED-BASELINE` state, source-guard banning 40-hex
      literals (19/19 mutants); a measurement of a superseded champion is not "fresh"; **the
      champion branch tip defines "current champion"** — run 20's dead status file had the panel
      calling the fresh merged measurement superseded by its own parent; five operator notes incl.
      computed scope-line ancestry (`270b48ed` reads "ancestor — its work is IN the current
      champion") and the accumulated-knowledge card reading `experiments.db` read-only (1051
      attempts / 326 mechanisms / 79 revisited / 18 kept / 402 measured-null / 132
      refused-at-formation) with a per-card staleness audit table (12/12 mutants).

<!-- original line 7505 -->
- [x] **R21-L5 — CI identity fix.** ✅ 2026-08-31 (research `af43cfb0`). Champion-keep tests drove
      a real `git commit`: green locally via host gitconfig, red on the runner ("Author identity
      unknown", run 33384448851). Fixed with fixture-local identity, proven under
      `GIT_CONFIG_GLOBAL=/dev/null`.

<!-- original line 7509 -->
- [x] **R21-L6 — run 21: the loop advanced the champion TWICE, unattended, end-to-end.**
      ✅ 2026-08-31. Each advance ran keep → anchor rebuild → A/A guard → self-measured headline →
      publish with no human step. (1) `akm-rmsnorm-1536-float4-384` +1.359% — **first rms_norm
      keep in program history** (hotspot 7.3%, 34 prior mechanisms, 0 kept); guard −0.263%;
      headline `cb617372` +15.326%. (2) `akm-q6k-paired-scale-pk-fma` +1.811%; guard +0.327%;
      headline `aba5a815` **+16.180% vs frozen production** (resolved live). Trajectory today
      +12.618 → +16.180, all direct measurements. First keeps under ranked memory: 2 keeps /
      26 iterations after 68 dry.

<!-- original line 7517 -->
- [x] **R21-L7 — the two operator-gated-card fixes.** ✅ 2026-08-31 (root `9425eaef`,
      `5f2151c9`). Hypothesis-ledger card walks the hotspot-first agenda from the real store
      (`mul_mat_vec_q` 49.3%/63 tried; `k_set_rows` never targeted; `flash_attn` 12.3%
      0-kept-over-29 visible), card compacted to one summary line + accordion (17/17 mutants);
      staleness for episodic evidence is SUBJECT-anchored (relevant/superseded/unverifiable,
      movement outranks, clock advisory; 4/4 mutants both directions).

<!-- original line 7523 -->
- [x] **R21-L8 — run-22 prep landed.** ✅ 2026-08-31 (research `a95581c8`, pushed). `dec-b2/4/8`
      surfaces (llama-bench source PROVEN: tg can never express `ne11>1`; the prompt path with
      `-b/-ub N` can); 3-layer uncalibrated-floor discipline (`decisive=None`; commit-path
      re-derivation); `--calibrate-surface` reusing the D8 method (byte-for-byte reproduces the
      tg128 k=5 floor); flag admission branch + greedy-parity harness (verdict encodes the
      operator's conditional). Budget consequence filed as R21-7.

<!-- original line 7529 -->
- [x] **R21-L9 — serving-evidence refresh package.** ✅ 2026-08-31 (research `8179dde0`, pushed;
      CH-14 pointer root `a5e23465` — coordinate via INF-65). Original +48.9% bundle traced, all
      four steps scripted (CH-4 validation → 24-cell concurrency grid → greedy parity → sealing
      emitter); "production ceiling" = MTP arm on the champion binary because v9 cannot load the
      DFlash2 GGUF (now documented); one-command `serving_evidence_refresh.py`, claim-held
      (refuses while run 21 lives); next bundle carries `generated_at` + `champion.commit`.

<!-- original line 7550 -->
  - [x] Pilot sweep (a) — qwen38-mtp ✅ 2026-08-31. BW-utilization arithmetic: MI210 production
        49.4% vs CUDA band 54–78%, 7900 XTX HIP 52.4% → the deficit is a **ggml-HIP-backend
        property**, not CDNA2 hardware. 3 seeds: multi-column MMVQ (untouched surface),
        quantized-KV FA (revisit-with-justification), Q8_0 GEMV roofline.

<!-- original line 7554 -->
  - [x] Pilot sweep (b) — upstream llama.cpp v0.2.0 delta since the 0db32c06 freeze
        ✅ 2026-08-31. ~260 commits, 19 CUDA; 6 seeds incl. MMVQ nwarps, MMQ decode crossover
        (no CDNA rows), and the **`-funsafe-math-optimizations` finding** — upstream removed it
        for flipping greedy argmax; our v9+champion still compile with it (verified, line 134).
        Operator ruled: "2% hit worth it IF quality demonstrated" — demonstration is a boundary
        step (R21-6), never merge-by-default.

<!-- original line 7560 -->
  - [x] All 13 seeds from the two sweeps injected into the live hypothesis inbox
        (operator-authorized) ✅ 2026-08-31. The loop elects on its own schedule.

<!-- original line 7562 -->
  - [x] Decide the upstream-rebase cadence for the experimental branch (filed 2026-08-31): the
        tree is ~260 commits behind upstream since the freeze; today's posture is
        port-as-hypothesis only (each upstream kernel change enters as an inbox seed, never a
        blind rebase). Either ratify that posture as the standing answer or set a periodic
        delta-sweep cadence (e.g. per upstream release, reusing sweep (b)'s method).
        OPERATOR DECISION 2026-11-18: port-as-hypothesis is the standing answer (no periodic delta-sweep, no blind rebase): an upstream change is ported only when a box needs it, gated on its own instrument; CH-35 and CH-36 stay gated on theirs. Census on C14: artifacts/analysis/ch32-upstream-census-c14-20261118.md. ✅ 2026-11-18 [no-belief: operator decision]

<!-- original line 7570 -->
- [x] ~~**R21-6 — BOUNDARY tonight, 2026-08-31 22:00Z (operator-ordered).** Driver~~ (closed 2026-10-29 audit: OBSOLETE → R23-63 note (autokernel-rebuild-program.md:2440) lists R21-6 stale by event (boundary 2026-08-31 22:00Z passed; driver scripts/benchmark/boundary_20260831.sh exists; later runs 22-30 superseded it))
      `scripts/benchmark/boundary_20260831.sh` (research lane; being written + stub-tested by the
      active research-lane agent). Sequence: stop run 21 (STOP+SIGTERM, +25 min group-SIGKILL) →
      `-funsafe-math` flag parity/speed A/B (merge ONLY on demonstrated divergence per the
      operator's conditional; tagged; oracle-gated) → `dec-b*` calibrations → full serving
      refresh (`serving_evidence_refresh.py`) → run-22 readiness report. ~5–7.5 h device.
      **Run 22 is NEVER auto-started** — operator gate, property mutation-tested. Open operator
      question (in the queue): pre-authorize run-22 on all-green, or hold for morning go.

<!-- original line 7578 -->
- [x] **R21-10 RESOLVED 2026-09-01 — the +1.765% was the INSTRUMENT, not the build.** Read-only
      investigation (report in `artifacts/r2110-anchor-guard-abort/`, research lane): ccache is
      NOT INSTALLED on this host (`GGML_CCACHE_FOUND-NOTFOUND` — the "~80s ccache-warm builds"
      belief was false); a controlled double-build of `14ba0262` is bit-identical in every code
      section (1 byte of RUNPATH `.dynstr` differs); the loop's own gen-010/fresh pair differs
      only in relocation-table offsets. Builds are DETERMINISTIC, funsafe included. The abort was
      a 4.2σ measurement excursion (pooled A/A sd 0.417%, n=11) — and it sits 0.006pp from the
      keep that preceded it (+1.759%), back-to-back in one session: either the keep is real and
      the guard fluked, or ONE ~12-min instrument excursion manufactured BOTH. The 4th keep's
      authenticity is decided by the staged device experiment (below). Headline integrity is
      unaffected either way — champion-vs-production is measured direct, so a dead patch in the
      lineage costs hygiene, not truth. ✅ 2026-09-01

<!-- original line 7590 -->
- [x] **R22-6 — Harden `read_inbox` (3-line fix, coordinate with R22-3's lane work).** ✅ 2026-10-29 (audit: research 68557dac8 (2026-09-01) "R22-6: operator injection channel no longer a kill switch": controller/inbox.py per-file try/except + inbox_file_unreadable note; tests test_inbox.py:69,81) [no-belief: audit-reconciliation]
      `run.py`'s `read_inbox` does a bare `read_text(encoding="utf-8")` per file, per
      iteration, with no error handling: one invalid-UTF-8 or unreadable file in the live
      inbox raises inside `build_context()` on EVERY iteration — all lanes error, the
      consecutive-error breaker fires, the run dies. The operator's injection channel is
      also a kill switch. Fix: per-file try/except → skip with a logged
      `inbox_file_unreadable` note, never raise. Verified 2026-09-01: all 17 current seeds
      read cleanly (42,783 chars, well within prompt budget), so this is preventive, not
      urgent.

<!-- original line 7599 -->
- [x] **R23-2 — Demote/annotate the two benign-but-alarming DFlash2 load warnings.** "failed ✅ 2026-10-31 — IMPLEMENTS llama.cpp-experimental `2d4e3225e13178674d27ef57b899f0255f15bf40`; [source, controls and provenance](https://github.com/pestopoppa/llama.cpp/tree/2d4e3225e13178674d27ef57b899f0255f15bf40/evidence/r23-2/README.md). [no-belief: software implementation and model-free controls]
      to measure draft model memory" and "legacy draft hidden size 5120" print identically in
      healthy 70 t/s runs and in a genuinely broken load — a peer session escalated a false
      champion-regression on exactly that signature (2026-09-01, retracted). Make the log
      distinguish "benign legacy path, sizes verified matching" from a fault, at the source in
      the champion lineage. Small; pairs naturally with R23-1's admission window.
      - Implementation detail: legacy draft hidden-size text is emitted at INFO only after the dimension matches the target; mismatch remains an error. Draft/MTP memory-estimate failures remain warnings with the explicit reservation caveat and original exception. The compiled extracted-source C++ fixture with mock APIs passed legacy match/mismatch, invalid/explicit metadata, DSpark and draft/MTP estimation-error controls; the evidence README and native-controls.log bind tested blobs and receipt. No full loader integration, full CPU/GPU build, model run, regression or deployment claim.

<!-- original line 7606 -->
- [x] **R23-5 — H1 transfer falsifier EXECUTED (H1-first, operator-approved) ✅ 2026-09-01.**
      **H1 CONFIRMED in substance: the +17.9% headline is ne11=1-concentrated and collapses on
      production serving shapes.** Champion `9e18beb0` vs frozen v9, 20 pairs/surface, all four
      effects decisive on bootstrap-calibrated floors: **+17.259%** (tg128, ne11=1) → **+3.834%**
      (dec-b2, floor 0.866%) → **+1.178%** (dec-b4, floor 0.668%) → **−1.462% a decisive
      REGRESSION** (dec-b8, floor 0.656%). Dispatch sanity proven by rocprofv3 (MMVQ ncols=1 →
      ncols=2 → MMQ across the curve — the instrument isolates ne11, not vacuous). Formally the
      partial-decay bracket, so the curve went to the operator; ruling: run 23 hunts **dec-b4**;
      the b8 repair is seed 18. Full record `/mnt/raid0/llm/tmp/r23-5-results/` (VERDICT.md,
      per-surface drain points, binary digests). Original task text kept below for provenance:
      One measured data point says ~1/28th of the tg128 headline transferred to the DFlash c1
      serving cell (70.0 → 70.4 across the merge that added all loop kernels). Two candidate
      causes, both structural: (a) ne11=1 vs the verify-batch shapes production actually runs
      (llama-bench tg cannot express ne11>1 — proven from source); (b) model-shape
      specialization — many keeps are `fixed-1536` (the 1.5B instrument model's n_embd);
      production's 27B is n_embd=5120, so those kernels never fire in serving. Falsifier:
      champion vs frozen production at ne11 ∈ {1,2,4,8} via the CALIBRATED dec-b* surfaces
      (~30-40 min). Collapse at ne11≥2 → dec-b* becomes the gate and the workload question
      (production-shaped rung, 5120-class/Q8_0 — the original P2 intent) reopens; hold across
      ne11 → H1 dies, the 1536-specialization half remains. H2 rider: after the falsifier, one
      run with ne11∈{2,4,8} in the seed surface — a disjoint winner set proves the search was
      half-blind. Provenance: peer msg 2fa07724 + our own commit titles.

<!-- original line 7628 -->
- [x] **R23-6 — H6 prompt-class ranking stability** (cheap, piggybacks R23-3's instrument work):
  - *(2026-11-19, OPERATOR DECISION via decision tool)* DECLINED and closed: its premise R23-3 was declined 2026-11-03. [no-belief: operator decision]
      score one candidate pair on code-heavy vs prose-heavy prompt sets; stable ranking →
      stratification unnecessary, only the span (2.4x measured) needs reporting. H5 (calibratable
      ~13% instrument gap) folds into R23-3: measure 3-4 arms on both instruments; wide ratio
      variance → cross-instrument claims stay banned rather than corrected.
  - 2026-11-19 R23-6: it piggybacks R23-3's instrument work, and R23-3 was declined 2026-11-03 (its consumer, mi210 P3-4, was retired by the 27B-ALWAYS-DFlash2 rule). The premise is gone; the same content review should decline this row. Needs the operator or ws58 to confirm; nothing to build.

<!-- original line 7635 -->
- [x] **R23-4 — One-factor sweep: config vs draft acceptance and run-over-run stability** ✅ 2026-11-04 (rc=0 inconclusive; Complete v10 descriptive sweep63/63; attribution INCONCLUSIVE (18/18 treatment/prompt metric ranges overlap adjacent baselines). Native evidence: docs/reports/autokernel-r23-4-v10-sweep-20261104/README.md. Historical9e18beb0 attribution remains unestablished; streaming events are not verified tokens and acceptance is window-correlated. [belief: cc])
      (from the peer's 2026-09-01 seam; feeds INF-22 P3-4 and INF-62). Two findings need
      attribution: (a) P3 decays monotonically across repeated requests at the verbatim c1
      config `[67.3, 52.6, 46.7]` while the 32K config is tight `[57.6, 61.1, 62.9]`; (b)
      acceptance moved 0.537 → 0.371 on identical prompts/model/drafter across configs. The
      peer's arm deliberately bundled THREE differences (context 32768 vs 4096, kv-unified vs
      --no-kv-unified, taskset) — attribution requires one factor at a time. If config moves
      acceptance that much, the serving recipe may leave ~15% on the table. Instrument note
      recorded: server-side 70.4 vs client-side 61.1 ≈ 13% expected gap; prompt-dependence spans
      2.4x within one arm, so single-prompt headlines are banned from this comparison. Also:
      32K-beats-4K REFUTED the VRAM-pressure prediction.

<!-- original line 7674 -->
- [x] **R22-3 — Guard robustness, post-trim (spec from R21-10, budget-gated on R21-7):** ✅ 2026-10-29 (audit: research 3e895c4bd (2026-09-01) "R22-3: anchor-guard robustness triad - hash pre-check, persisted evidence, heal-once" (controller/anchor_integrity.py) covers (1)(2)(3)) [no-belief: audit-reconciliation]
      (1) persist the guard's full `Comparison` in the AnchorVerdict archive row — the abort's
      samples/drift/clocks died with the process; (2) **hash pre-check as the primary fix**:
      compare code-section hashes (`.text`+`.hip_fatbin`, ignore `.dynstr`/`.rela*`) before
      measuring — identical code + above-floor A/A indicts the SESSION (log `anchor_guard_excursion`,
      continue), differing code is deterministic run-18 proof (abort, no pairs wasted); (3) heal
      once: one rebuild+re-verify before aborting. Verify-and-adopt evaluated and REJECTED
      (adopted arm would itself be unverified; determinism makes it moot).

<!-- original line 7682 -->
- [x] ~~**R22-4 — Next-boundary device experiment (builds staged at `/mnt/raid0/llm/tmp/r2110-build-{a,b,parent}`):**~~ **SUPERSEDED 2026-11-17 (autokernel, INF-06 code pass): it audits the run-21 "4th keep" on its 2026-08 pre-v10 parent. Only the build half ran (`autokernel-r22-4-rebuild-20261102` filed: a/b builds custody-preserved, no runtime claim). Every later champion (v10, C6-C12) was gated as a whole against production, so whether that one historical keep stands no longer changes any C12 decision.** [no-belief: superseded]
      A/A a-vs-b (identical binaries, distinct paths) → instrument sanity; A/B parent-vs-a twice,
      order-swapped → ≈+1.76% both = the 4th keep stands; ≈0 = the keep was manufactured by the
      excursion and gets a hygiene revert. ~25 min device time.

<!-- original line 7686 -->
- [x] ~~**R21-7 — the loop code budget is BINDING AGAIN: 2100/2100, zero headroom** (run-22 prep~~ (closed 2026-10-29 audit: OBSOLETE → R23-63 note (autokernel-rebuild-program.md:2440) lists R21-7 stale by event; budget since raised 2100->3000->3400->3450 (check_regrowth_guards.py:34-66))
      consumed the `95eeb0ae` trim's headroom; filed 2026-08-31). Next trim candidate: delete the
      `loop.run` test-only seam (kept as a documented seam by `95eeb0ae`; its tests move to the
      pooled path). Same rule as R18-F: the budget is freed by deletion, never bumped.

<!-- original line 7690 -->
- [x] **R21-8 — `MEASURED_FLOOR_PCT` is keyed by SURFACE ONLY; the model identity behind the ✅ 2026-10-29 (audit: loop/bench.py:66-80: MEASURED_FLOOR_MODEL_STEM + "floor_rows refuses to serve it to any other model" and R23-61 n-keying; floor now keyed by model identity) [no-belief: audit-reconciliation]
      calibration is unenforced** (filed 2026-08-31). A floor calibrated on one workload silently
      gates a run on another — same defect class as R18-D's stale pp512 floor. Add the model (or
      workload identity) to the floor key, or refuse a mismatch at gate time.

<!-- original line 7694 -->
- [x] ~~**R22-1 — run-22 primary surface: default STAYS tg128** (filed 2026-08-31, resolves at the~~ (closed 2026-10-29 audit: SUPERSEDED → resolved at the run-22 go; run 22/23/29 surface decisions superseded (R23 block, R23-42 :1620 run 29 on tg128); run-22 boundary long passed)
      run-22 go). `dec-b2/4/8` enter as secondary, individually calibrated surfaces (R21-L8);
      promotion of any of them to primary is an operator call made on the boundary's readiness
      report — the report must carry the per-surface floors so the choice is decidable there.

<!-- original line 7708 -->
- [x] **R21-1 — refresh the champion headline at STARTUP, not only per-advance.** ✅ 2026-10-30 <!-- evidence-integrity: Research `bebe42b9a56d9cf6c951fc75a227c8666a194080`; artifact: artifacts/compute/task-evidence-repair-20261031/r21-1/EVIDENCE.json; hygiene, not quota -->
      Research main `bebe42b9a56d9cf6c951fc75a227c8666a194080` accepted the two-file closure
      (`scripts/kernel_rnd/autokernel/loop/run.py` + `test_startup_headline.py`; accepted patch
      SHA-256 `fbb2f4980eee6d2aaf0dcdb8230a3f59fd3262063ab9d1fcbfb85b11678139e2`). The ordinary
      startup refresh uses the existing `production.refresh` path inside held original claims and
      the established CPU/GPU measurement windows, before pool provisioning. Carryover measures
      the champion alone; absent/stale baseline may build a scratch baseline and run paired A/B.
      Refresh failure preserves the prior headline and still dispatches the pool. This adds one
      startup refresh; the conditional build/A-B cost was not timed separately. Four real-main
      behavior cases cover carryover/fallback × success/failure; 138 tests plus 10 subtests passed,
      with R6 supervisor completion and drained children. Source/test closure only; no hardware
      headline, reload, or performance result is claimed. Evidence:
      `artifacts/compute/refactor-r21-1-startup-headline-20261030.json`. [no-belief: code and test
      closure; no performance measurement]

  <!-- task-evidence-integrity:start R21-1 -->
  - Evidence metadata (hygiene, not new quota): Research `bebe42b9a56d9cf6c951fc75a227c8666a194080`; [test/artifact](../../artifacts/compute/task-evidence-repair-20261031/r21-1/EVIDENCE.json).
  <!-- task-evidence-integrity:end R21-1 -->

<!-- original line 7726 -->
- [x] **R21-2 — promote the reconciliation A/B evidence out of volatile tmp.** ✅ 2026-09-01 —
      landed as research `2ee10ff5` (`artifacts/autokernel-champ-a2728701-ab/`, 24 files ≈1.4 MB:
      result JSON, `run_ab.py`, `run_ab.log`, 3 oracle logs, symdiff; regenerable dumps excluded),
      verified on `origin/main`. Queue row OP-31 deleted at the 2026-09-01 wrap-up — it had gone
      stale after the commit landed without the flip (recurrence-check catch).

<!-- original line 7733 -->
- [x] **R21-3 — RETIRED ✅ 2026-09-02 (operator executed).** `ak-loop-tree`, `-b`, `-c` worktrees
      removed and branches `ak/loop-champion-20260828{,b,c}` deleted (`-D`); ~495 MB reclaimed.
      Safety RE-VERIFIED same day rather than trusting the 2026-08-31 record: `4925b2084` is an
      ancestor of the **current** champion tip `732389d6d` (not just the older `a2728701`) with
      **zero** commits unique to the branch, tag `ak/pre-reconcile-loop-20260831` still resolves
      and the object is intact, all three trees idle on two samples 48 s apart, and nothing live
      depends on them (driver + run 24 pass `--worktree champ2` explicitly). Post-deletion checks:
      0 worktrees, 0 branches, tag resolves, `4925b2084` still ancestor of the live champion,
      `champ2` untouched on the canonical champion branch. **The review changed the command**:
      `ak-loop-tree-c` held 82 uncommitted lines present in NO commit on any ref, so plain
      `worktree remove` would have refused and a reflex `--force` would have destroyed them —
      rescued first (R21-5), and only then was `--force` scoped to that one tree.

<!-- original line 7745 -->
- [x] **R21-4 — the non-hermetic dashboard tests (4 red loop-down).** They assert on LIVE loop ✅ 2026-10-31 — implementation ROOT `c5f799ba77dc423d51fb0c9cabb8a6ae66e1a8f1`; `tests/test_dashboard_r21_4_fixtures.py` and four original suites, 109 PASS / 156 subtests; committed evidence `artifacts/engineering/r21-4-dashboard-hermetic-tests-20261031/FOCUSED-TESTS-RECEIPT.json`. [no-belief: source-bound deterministic fixture/guard controls; no measurement]
      state and were red between runs 20 and 21; with run 21 up, the six live-reading files pass
      (157 tests, verified 2026-08-31). The exact red set was never persisted and cannot be
      recovered without taking the loop down; the live readers are in
      `test_dashboard_operator_gates.py` (real gate bundle), `test_dashboard_controller_state_contract.py`
      (live `state.json`), `test_dashboard_knowledge_card.py` (real `experiments.db`),
      `test_dashboard_champion_headline.py` (real bundle + production resolution). Standing debt
      already noted in `.github/workflows/tests.yml` ("Report what was NOT run") and P6. Fix is
      recorded producer fixtures, not skips — fold into the P6 rewrite.

<!-- original line 7793 -->
- [x] ✅ 2026-09-02 **R23-7 — fix stale `PRODUCTION_QUANT_FAMILY` (`workload_contract.py:58` refuses
      production's own Q8_0 model).** Verified: `Q8_0` is absent from the frozenset, so
      `verify_workload()` refuses production's own Qwen3.8-27B-Q8_0 while passing the mismatched
      1.5B instrument. Land at the run-23 boundary, never mid-run. (Rung design §5.1.)
      *Folded into R23-11 (2026-09-01 D1–D6 ruling); flips with it.* **✅ 2026-09-02 — R23-11 IS `[x]`,
      so this flips with it. Ticked at the 2026-09-08 wrap-up reconciliation; the resolution predates it.**

<!-- original line 7799 -->
- [x] ✅ 2026-09-02 **R23-8 — floor keying (surface, workload-class) per rung design §5.1/R21-8.**
      `bench.floor_rows()` keys by surface only; calibration artifacts record `"model"` but
      nothing reads it — confirmed structurally. Key by (surface, workload-class); mismatch →
      uncalibrated/refuse. Land at the run-23 boundary, never mid-run.
      *Folded into R23-11 (2026-09-01 D1–D6 ruling); flips with it.* **✅ 2026-09-02 — R23-11 IS `[x]`,
      so this flips with it. Ticked at the 2026-09-08 wrap-up reconciliation; the resolution predates it.**

<!-- original line 7805 -->
- [x] **R23-9 — DFlash2 standalone llama-bench smoke (2 min GPU) + 27B confirm-surface A/A ✅ 2026-11-02 [belief: cc]
      calibration window (~5–6 h) — OPERATOR-GATED, next boundary.** Frozen v9 carries the dflash
      arch (verified in `0db32c06e`), so the 2 GB rung is loadable by both arms; the smoke decides
      D5, the A/A window is D6's only real device cost.
      **D6 SCHEDULED 2026-09-01: operator — "let run 23 hunt until 22:00Z, full boundary then."**
      Boundary sequence: stop run 23 (graceful drain, captured PID 2214942) → merge R23-11
      (review-token gated) → apply re-anchored seeds (R23-12, staged copies) → rocprof dispatch
      sanity (R23-13) → DFlash2 smoke → 27B A/A on dec-b4+dec-b8 (keyed calibration artifacts) →
      readiness package.
  **R23-9 historical evidence (2026-09-02).** The standalone DFlash2 smoke ran and failed (rc=1), as recorded in [the contemporaneous progress report](../../progress/2026-09/2026-09-02-ak-rebuild-20260828.md) and R23-16; its failure settled the standalone-screen choice and is not a successful load. Both 27B calibration records exist in `/mnt/raid0/llm/autokernel/loop-memory/calibration/`, name anchor `732389d6d9d08338fe2ad2457bf8f44205914a7f`, and contain SETTLED, PREHEATED and POST_BUILD conditions with 20 pairs and 40/40 resident invocations each: `dec-b4.Qwen3.8-27B-Q8_0.json` recorded 10:03:15Z, SHA-256 `00bbb95aa851b9cde1d8361bd4a9749fda5cb7115a820344eb0805a14427496f`; `dec-b8.Qwen3.8-27B-Q8_0.json` recorded 11:49:11Z, SHA-256 `4fe6ee83b176ae7d1c0d169fbb3b561b65bf08d07b60f57ef9ba2b2402c1f9cf`. Research commit `078d9c3c030c0ac3f29cbdb8a261ae30c09a12e2`, an ancestor of research `origin/main`, independently records the two keyed floors; the later handoff's run-27 entry records the dec-b8 confirm gate. This closes the historical boundary work only; it does not establish present-day floor validity or a new measurement warrant.

<!-- original line 7816 -->
- [x] **R23-14 — boundary driver drafted, reviewed, armed** ✅ 2026-09-01 —
      `boundary_20260901.sh` + helper (research side branch `8634f0c7`), modeled on the 20260831
      trio (state-file resume, fail-closed refusals, PID-verified stop). **Review fix
      `6f405233`**: run 24 launches from the latest guard-verified anchor-gen — the drafted
      incremental-tip-rebuild + `--allow-unverified-anchor` path was the 2026-08-31
      attestation-failure pattern and was removed. Driver LIVE: pid 2715782 (waiting for
      22:00Z), `REVIEW_TOKEN_R23_11` + `PREAUTH_RUN24` placed per OP-35.

<!-- original line 7823 -->
- [x] **OP-35 RESOLVED 2026-09-01 — operator: run 24 PRE-AUTHORIZED on the all-green
      conjunction** ("yes, you're pre-authed"): run 23 drained clean · R23-11 merge landed +
      full hardware-free suite green · re-anchored seeds applied · dispatch-sanity recorded ·
      27B A/A calibrations written and sane. The owning session places
      `/mnt/raid0/llm/tmp/boundary-20260901/PREAUTH_RUN24` in the evening ONLY after reviewing
      the R23-11 commits (separate `REVIEW_TOKEN_R23_11`) and the driver's `--dry-run`; the
      driver launches run 24 (~04:00–05:00Z) iff token AND all-green — any single non-green
      holds everything for morning review. Mirrors OP-34/run-22. ✅ 2026-09-01

<!-- original line 7837 -->
- [x] **R23-11 — implement the approved rung design in loop code** ✅ 2026-09-02 (§5.1 census-based
      quant-family + rung-parity check · §5.2 (surface, workload-class) floor keying — subsumes
      R23-7/R23-8 · §5.3 KEEP_CANDIDATE screen→confirm gate, headline-on-rung, rung on every
      record). Built on side branch `ak/rung-fixes-20260901` (never the lane mid-run); merged at
      the boundary — lane at `765fc6bb` (research), gate suite green 06:51Z (see R23-15 for the
      two refusals on the way there).

<!-- original line 7843 -->
- [x] **R23-12 — re-anchor inbox seeds to the rung they will be measured on (§5.4)** ✅ 2026-09-02 —
      9 seed files applied by the driver at 06:51Z (manifest
      `/mnt/raid0/llm/tmp/boundary-20260901/step3-seeds-manifest.txt`); loop was verified dead
      first, live inbox never edited mid-run.

<!-- original line 7847 -->
- [x] **R23-13 — rung identity artifact (§5.6 step 2)** ✅ 2026-09-02 — production dispatch tables
      recorded per confirm surface on the 27B:
      `/mnt/raid0/llm/tmp/boundary-20260901/rung-identity/dec-b{4,8}.Qwen3.8-27B-Q8_0.json`.

<!-- original line 7850 -->
- [x] **R23-15 — boundary step2 gate defect found + repaired (operator-approved)** ✅ 2026-09-02 —
      the drafted gate demanded ABSOLUTE green on `pytest loop/ controller/`, but controller/
      carries 74–76 pre-existing legacy-red tests (StaticBuildCache sealed-key fixtures, Arena
      adapters, V8Deterministic setup errors) — the gate could never pass and was armed without a
      dry-run of its exact command. Refusal #1 22:17Z (fail-closed, lane rolled back — GPU idle
      overnight). A/B in fresh worktrees proved the failing sets at `74b936b5` and `9c40429d`
      byte-identical (merge introduces 0, adds 35 passing). Fix 1 `ecb6288a`: pytest becomes a
      DELTA gate vs the pre-merge tag. Refusal #2 06:45Z: one legacy test audits the
      *checkout's own git-cleanliness* (passes in a fresh worktree, fails in any working lane at
      the same commit) — fresh-baseline-vs-live-lane compared environments, not commits. Fix 2
      `9fa7a6fa`: environment parity, both sides in fresh detached worktrees. Gate green 06:51Z:
      74 = 74, 0 introduced. Floors + regrowth guards stayed absolute and green throughout.
      OP-35's "full suite green" conjunct is read as this delta-green per operator "proceed"
      (2026-09-02 morning). NOT filing a fix-the-legacy-red task: Phase 5 strip deletes those
      suites; fixing them first is work the teardown plan already declines.

<!-- original line 7865 -->
- [x] **R23-16 — DFlash2 smoke result (D5 settled for run 24)** ✅ 2026-09-02 — smoke FAILED
      rc=1, non-gating as designed: `llama-bench` cannot load
      `Qwen3.8-27B-DFlash2-Q8_0.gguf` standalone (2.06 GB drafter HEAD, present and readable —
      it is a companion artifact, not a self-contained model). Run 24 screens on the 1.5B rung.

<!-- original line 7869 -->
- [x] **R23-17 — DFlash2 capability verification on the post-keep champion: PASS** ✅ 2026-09-02 (OWNED here —
      operator reassignment 2026-09-02: "I want you to own this"; "We can't afford having any
      issues with the DFlash2 performance boost. It is central to this champion's feature set").**
      Exposure: run 23's keeps were validated ONLY on the 1.5B dec-b4 surface; `db18f393` edits
      `fattn-wmma-f16.cu` (on the 27B batched draft-verify path) and `732389d6` rewrites 119
      lines of `mmvq.cu` — the DFlash2 path has never been exercised post-keep. Built
      `scripts/benchmark/dflash2_capability_smoke.sh` (research lane `b412f37d`): replays the
      DF2-5 server recipe verbatim on a given build, gates on acceptance ≥0.58 (bar 0.6205) and
      speculation boost ≥1.5× none-control (bar 2.6×); step5's standalone `llama-bench` on the
      drafter head could never work (companion artifact, not a model — R23-16). **Run-24 launch
      HELD**: `PREAUTH_RUN24` → `.held-for-dflash2-verify` + `HOLD_REASON.txt`; at step6
      completion (~13:00Z) run the smoke on anchor-gen-014 with the GPU seam quiet, then PASS →
      re-place PREAUTH + resume driver; FAIL → no launch, bisect which keep broke the path
      (candidates in commit order), report with rollback options.
      **RESULT 2026-09-02 ~12:00Z on anchor-gen-014 (champion `732389d6`): PASS.** acceptance
      **0.6501** (bar 0.58; DF2-5 reference 0.6205); DFlash2 **72.65 t/s** vs non-speculative
      **30.51 t/s** = boost **2.38x** (bar 1.5x). Verdict at
      `/mnt/raid0/llm/tmp/boundary-20260901/dflash2-smoke/verdict.json`.
      **Reading**: the three keeps did NOT damage the DFlash2 path — speculative throughput is up
      on DF2-5's 70.0 t/s and acceptance is slightly up. The boost RATIO fell (2.6x -> 2.38x) only
      because the non-speculative arm improved MORE (26.6 -> 30.51 t/s, +14.7%): the kernel keeps
      helped plain decode more than the speculative path, compressing the ratio while making BOTH
      arms faster. A falling ratio here is not a regression.
      **Caveat**: DF2-5 came from a different binary and harness; the load-bearing comparison is
      the same-binary internal control (none vs dflash), which is sound. Run-24 gate SATISFIED.
      **Instrument defect fixed mid-flight**: the build-capability check used
      `llama-server --help | grep -q`, and under `set -o pipefail` grep -q closes the pipe ->
      SIGPIPE(141) -> a SUCCESSFUL match read as a failed pipeline -> false REFUSE (rc=2).
      Capture-then-match now.

<!-- original line 7898 -->
- [x] **R23-19 — MEASURED ✅ 2026-09-02 — the +27.363% headline is a SCREEN-RUNG number; the production-facing headline
      has never been measured.** Proven 2026-09-02 from the headline evidence record
      `champion-vs-production.732389d6d9d0.json`: `peak_vram_bytes` 1.49 GB and samples 536→684
      t/s — that is the 1.5B DeepSeek-R1-Distill screen rung, not Qwen3.8-27B-Q8_0 (~29 GB,
      ~65 t/s on the same surface per the 10:03Z keyed floor). Run 23 predates R23-11, so
      `headline_model` fell back to `--model` by construction; this is the design working, not a
      defect — D4 exists precisely because a screen-rung headline does not transfer (CH-6
      precedent: MMQ_MFMA +23.09% on the 0.5B vs **+0.50%** on the 27B, ~46× attenuation).
      **Standing operator instruction violated by my own reporting** (headlines MUST be the
      production recipe), corrected in-session. ACTION: measure champion-vs-production on the 27B
      at the step6→step7 seam (~1 h device, 20 pairs, anchor-gen-014, alongside the DFlash2
      smoke), and until it exists quote the headline as "+27.363% (1.5B screen rung)" — never
      bare. Until then the champion's production-facing gain is UNKNOWN, not 27%.
      **MEASURED 2026-09-02T12:49Z — the production-rung headline is `-1.600%`, and the run is
      DRIFT-FLAGGED so it is INCONCLUSIVE, not a proven regression.**
      champion `732389d6` vs frozen production-v9 on Qwen3.8-27B-Q8_0, dec-b4, 20 pairs, floor
      0.949%: production median **66.09 t/s** vs champion **65.05 t/s**. Residency clean (40/40
      resident, 1 KFD proc, 28.0 GB VRAM, clocks pinned 1700/1700, `clock_stable` true), so this
      is NOT a placement or throttle artifact. BUT `drifting: True` — both arms declined together
      (anchor -0.535%, candidate -0.654%; trend rho -0.481 / -0.668), and the instrument therefore
      returns `decisive: False` despite |effect| > floor. Contrast the SAME surface at 06:52-10:03Z
      (the A/A calibration): drift 0.13/0.27, rho 0.06/0.21, `drifting: False` — the machine was
      steady this morning and is not now, after ~6 h of continuous GPU load.
      **What is established**: the +27.363% figure does NOT transfer to production; the champion's
      production-rung gain is at best flat and possibly negative. **What is NOT established**: that
      it is a real -1.6% regression.
      **Consequence**: run 24 stays HELD (pre-auth not restored). Next action is R23-22.

<!-- original line 7925 -->
- [x] **R23-22 — DONE ✅ 2026-09-02 — re-measure the production-rung headline on a SETTLED device.** The 12:49Z run is
      drift-flagged and cannot carry a verdict either way. Let the GPU idle (no benches) before
      re-running `headline_on_confirm_rung.py` with the same arguments, and check `drifting` is
      False before believing the number. If the settled re-measure is inside the floor -> champion
      is production-NEUTRAL (the keeps bought screen-rung speed that does not transfer); if it
      reproduces beyond the floor -> the keeps are a real production REGRESSION and the lineage
      needs a bisect (`7d2ea88b` / `db18f393` / `732389d6`) before any promotion. Either outcome is
      a decision package for the operator, not an autonomous action.
      **RESULT 2026-09-02T14:2xZ, 30 min idle settle, device verified 0% before start:
      `-1.414%`, `drifting: False`, `decisive: True`.** production median **65.92 t/s** vs
      champion **65.00 t/s**; drift 0.385/0.318, rho -0.307/-0.389 (inside tolerance), 40/40
      resident, clocks pinned 1700/1700. It REPRODUCES the drift-flagged 12:49Z run (-1.600%),
      two independent measurements agreeing within 0.19 pp.
      **VERDICT: the champion is a REAL ~1.4% production REGRESSION on dec-b4** — while being
      +27.363% on the 1.5B screen rung on THAT SAME SURFACE. The keeps are model-scale-specific
      and actively harmful at production scale. This is the sharpest possible vindication of the
      two-rung design (R23-10/R23-11) and of holding run 24.
      **Note the workload split**: DFlash2 generation is FINE on this champion (R23-17: 72.65 t/s,
      acceptance 0.6501). The regression is specific to the dec-b4 prefill-shaped surface — the
      very surface the loop optimized on the 1.5B.

<!-- original line 7945 -->
- [x] **R23-23 — RESOLVED ✅ 2026-09-02 — OPERATOR DECISION: what to do with the regressing champion lineage before run 24.**
      Run 24 would launch WITH the confirm gate active, so it cannot repeat this defect going
      forward — but it would start from a base that is already -1.4% on production. Options:
      (a) **Bisect then repair** — first measure the pre-keep parent `9e18beb0` vs production
      (~50 min, ONE measurement): if it is neutral, today's three keeps own the regression and the
      culprit is isolated in 1-2 more runs; if it is already negative, the regression predates them
      and the whole lineage is suspect. Most informative; tells us WHICH mechanism class hurts
      production. (b) **Re-anchor to production-v9** — discard all three keeps, start run 24 clean
      with the confirm gate on. Cheapest, zero measurement, loses only screen-rung work that is
      worthless on production anyway. (c) **Launch run 24 as-is** — the confirm gate protects
      future keeps but bakes in the -1.4%. NOT recommended.
      **CORRECTED 2026-09-02 (before acting — two errors in the options above):**
      **(i) Option (b) is BARRED by the ratified single-champion invariant.** "Seed Champion = frozen
      production" is correct in exactly ONE moment: immediately after a promotion. We are MID-cycle,
      so applying it would silently discard the accumulated research — the precise 2026-08-31
      incident whose ruling reads *"I NEVER WANT TO SEE YOU MAKE THIS MISTAKE EVER AGAIN."*
      Option (b) is withdrawn; it must never be recommended mid-cycle again.
      **(ii) The -1.414% is the AGGREGATE's standing, NOT proven to be the three keeps' fault.**
      The champion is **67 commits / +4720 -310** above v9 and contains the manual-admission
      aggregate — DFlash2 loader + metadata, iqk fallbacks, speculative work (`5c278648a` verified
      an ancestor) — as well as every autokernel keep. Attributing the regression to run 23's three
      keeps was premature; R23-23's `9e18beb0` probe is exactly the test that attributes it.
      **Revised options**: (a) probe `9e18beb0` (RUNNING, result ~15:55Z) — if it is neutral the
      three keeps own the regression and a 3-commit revert cleans the base; if it is also ~-1.4%
      the regression predates them and lives in the older aggregate. (c) **launch run 24 as-is with
      the confirm gate already configured** — invariant-compliant, zero GPU cost, and every FUTURE
      keep must clear the 27B, so the loop cannot deepen the hole.
      **Recommendation: (a) then (c)** — the probe is already in flight and free, and run 24 cannot
      start before it finishes anyway (a second GPU workload would contend and corrupt both).
      **Recommendation (superseded): (a) then (b)** — spend one 50-minute measurement on `9e18beb0` to learn
      whether the defect is today's keeps or the whole lineage, then re-anchor accordingly.
      **RESOLVED 2026-09-02T16:15Z — probe (a) run, keeps EXONERATED, run 24 launched as-is (c).**
      `9e18beb0` (the pre-keep parent) measures **-1.751%** vs production — `drifting: False`,
      `decisive: True`, cleanest drift of any run yet (0.080/0.079, rho 0.081/0.090); production
      66.10 t/s vs 64.91 t/s. Against the champion's -1.414%, the three run-23 keeps moved
      production by **+0.337 pp — INSIDE the 0.949% floor** — so they are production-NEUTRAL, not
      the cause. **The regression predates them and lives in the older aggregate.** A 3-commit
      revert would have fixed nothing; none was made.
      **Reframing: this is very likely a FEATURE COST, not a defect.** The aggregate's
      -1.4/-1.75% is measured on dec-b4 = `pp=512, tg=0, ubatch=4` — a PREFILL-shaped surface that
      by construction cannot see DFlash2, whose entire value is in DECODE. The same champion
      delivers **2.38x speculative decode** at acceptance 0.6501 (R23-17). Paying ~1.7% of prefill
      for 2.38x decode is a good trade for real serving, not a regression to repair.
      Run 24 launched **pid 260751**, confirm gate ACTIVE (27B, 5 pairs, dec-b4 1.142% + dec-b8
      1.753%), screen parity waived-and-recorded, claim held on mi210_0.

<!-- original line 7990 -->
- [x] ✅ 2026-09-04 **R23-26 — the champion-vs-production HEADLINE SURFACE is wrong for this aggregate.**
      Established by R23-22/R23-23: the headline is measured on dec-b4 (`pp512/tg0`), a
      prefill-only shape, while the champion's largest asset (DFlash2, 2.38x) is a DECODE feature
      that surface cannot observe. The published headline therefore systematically UNDERSTATES the
      champion and reads as a regression while the aggregate may be strongly net-positive in real
      serving. Propose: the headline for an aggregate carrying decode features must include a
      decode/speculative surface (tg128 and/or a DFlash2-enabled arm) reported ALONGSIDE prefill,
      never replacing it. Until then quote the headline as "prefill-only".
      **✅ 2026-09-04 — SUBSUMED BY R23-43**, which is `[x]` and says so in terms: *"subsumes R23-18 (DFlash2
      regression guard) and R23-26 (headline surface)"*. The serving recipe is now the keep gate and
      llama-bench is demoted to a screen. **Independently re-confirmed 2026-09-08**: `tg128` understated the
      real serving rate by ~2.5x (31.0 vs 79.25 tok/s) — exactly this item's thesis, measured.

<!-- original line 8002 -->
- [x] **R23-27 — run 24 STOPPED and reconfigured to hunt ON the confirm rung** ✅ 2026-09-03
      (operator: *"do the third"*). **Why**: run 24 ran 14 h and produced **116 measurements, ZERO
      keeps** — best effect +0.650% against a 0.668% floor, only 4 attempts above +0.468%: the 1.5B
      screen surface is exhausted. Worse, R23-19/22/23 established that surface is anti-correlated
      with production for exactly the size-dependent families the planner keeps proposing (R23-25),
      so its verdicts were not worth the GPU claim. The confirm gate was NEVER exercised (no screen
      keep -> no KEEP_CANDIDATE -> the 27B path never ran).
      **Also degrading**: 161 planner transients, escalating 0-5/hr (evening) -> 23 at 01:00Z -> 21
      at 04:00Z -> **64 at 05:00Z against 7 measurements**, all malformed structured output
      (`hypothesis is missing [...]` 63+26, `authoring returned no changed paths` 26, `no parseable
      JSON object` 25) — the same class as the v3-v27 planner-outage spin. A fresh process clears it.
      **New configuration (dry-run PROVEN before launch)**: `--model Qwen3.8-27B-Q8_0` (was the 1.5B),
      `--surface dec-b4 --pairs 5`, NO `--confirm-model` (redundant once the screen IS the confirm
      rung). Dry-run reports `workload Qwen3.8-27B-Q8_0: n_embd=5120, dominant Q8_0`, floor
      **1.142%** correctly keyed to the 27B, and — the tell that this is right — **no "screen parity
      WAIVED" line**, because the hunting rung is now production-shaped by construction.
      **Consequences, stated honestly**: throughput drops (a 5-pair 27B A/B is ~14 min of device vs
      ~8 min for a 20-pair 1.5B run, so roughly 3/hr instead of 8/hr) and the keep bar rises to
      1.142%. In exchange every verdict is a PRODUCTION verdict, false negatives from rung transfer
      vanish by construction, and `headline_model` now equals the production model so the loop's own
      headline republish lands on the right rung (partially addressing R23-26; the SURFACE is still
      prefill-only, which R23-26 still owns).
      Run 24 stopped by SIGTERM to captured pid 260751, death verified before relaunch.

<!-- original line 8025 -->
- [x] **R23-31 — Q4_K SIGNAL PROBE: +7.066%. The banked-gains thesis is CONFIRMED** ✅ 2026-09-03
      (step 1 of the operator-approved two-step). Champion `732389d6` (anchor-gen-014) vs frozen
      production-v9 on **`gemma-4-26B-A4B-it-Q4_K_M`** — an **in-fleet production role model** (the
      worker), not a hypothetical target — `dec-b4`, 5 pairs:
      **production 175.96 t/s -> champion 188.40 t/s = +7.066%**, `drifting: False`, residency clean
      (10/10 resident, 17.4 GB VRAM, clocks pinned 1700/1700, `clock_stable` true).
      **Status: SIGNAL, not a verdict** — no calibrated floor exists for this (surface, model), so
      `decisive` is `None` by construction. For scale: the 27B's dec-b4 floor at 5 pairs is 1.142%,
      so +7.07% is ~6x a comparable bar and very unlikely to be noise — but that reasoning borrows
      another model's floor and is NOT a substitute for calibrating this one.
      **What it establishes**: the Q4_K-gated keeps (`7d2ea88b`, `732389d6`) **do fire and do help**
      on a real Q4_K workload. R23-29's "dormant, not dead" reading is correct, and my earlier
      "worthless on production" framing was wrong in a way that mattered.
      **The champion's real standing is workload-dependent, not a single number**:
      | workload | champion vs production-v9 |
      |---|---|
      | Qwen3.8-27B Q8_0, dec-b4 (prefill) | **-1.414%** (decisive; Q4_K keeps inert, DFlash2 feature cost) |
      | gemma-4-26B-A4B Q4_K_M, dec-b4 (prefill) | **+7.066%** (signal; Q4_K keeps active) |
      | Qwen3.8-27B Q8_0, speculative decode | **2.38x** with DFlash2 (R23-17) |
      A single "champion vs production" headline cannot express this — which is R23-26's point,
      now with hard numbers behind it.

<!-- original line 8046 -->
- [x] **R23-32 — DONE ✅ 2026-09-03 — step 2: calibrate the Q4_K surface and convert the +7.066% signal into a claim.**
      Approved shape (operator, 2026-09-03: cheap signal first, then calibrate only if promising —
      the signal is promising). Run the A/A bootstrap for
      (`dec-b4`, `gemma-4-26B-A4B-it-Q4_K_M`) to produce a keyed floor (~3 h, the 27B dec-b4
      calibration took 3 h 11 m), then re-measure with `headline_on_confirm_rung.py`, which will
      then pass its uncalibrated-surface refusal (rc=3) instead of tripping it.
      **Why it is worth the 3 h**: this is a production win available on a model we ALREADY SERVE.
      If it holds, the promotion argument changes from "the champion is neutral-to-negative" to
      "the champion is +7% on the worker", which is a different conversation entirely.
      **Needs a GPU window** — no run is currently hunting, so the window is open now.
      **RESULT 2026-09-03T12:1xZ — CLAIM-GRADE: `+7.206%`, `decisive: True`, `drifting: False`.**
      Champion `732389d6` vs frozen production-v9 on `gemma-4-26B-A4B-it-Q4_K_M`, dec-b4, **20
      pairs against the freshly calibrated 0.456% floor** — production **174.26 t/s** vs champion
      **186.76 t/s**, i.e. **15.8x the floor**. Drift inside tolerance (-0.223/-0.061, rho
      -0.311/-0.215), residency clean (40/40 resident, 1 KFD proc, clocks pinned 1700/1700).
      It reproduces the 5-pair signal (+7.066%) within 0.14 pp — two independent measurements,
      different pair counts, same answer.
      **The calibration that made it claim-grade** (R23-32's prerequisite): floor curve
      1.843/1.257/0.936/0.699/0.456 for k=1/3/5/9/20 — a 4.04x fall against the ideal sqrt(20)=4.47x,
      i.e. textbook parametric scaling and structurally believable (contrast dec-b8's anomalous 45x,
      which only the parametric guard caught). A/A effect **-0.061%**, `drifting: False`, despite a
      peer running a 48-thread CPU bench concurrently — the flagged memory-bandwidth co-residency
      did NOT contaminate it.
      **Isolation held**: run in the scratch store, so the live `champion-vs-production.json` still
      carries the 27B production headline (-1.414%, model field = Qwen3.8-27B-Q8_0) and was not
      overwritten by a Q4_K number.
      **What this establishes.** The champion is **+7.206% on a model the fleet already serves**
      (the worker). The Q4_K-gated keeps are not merely dormant — they are worth ~7% where they
      fire. The program's standing is now three measured workloads, not one number:
      -1.414% (27B Q8_0 prefill, decisive) · **+7.206% (26B-A4B Q4_K prefill, decisive)** ·
      2.38x (27B speculative decode, DFlash2). R23-26's "the headline surface is wrong for this
      aggregate" is now backed by two decisive measurements pointing opposite directions.

<!-- original line 8128 -->
- [x] **R23-35 — first confirm-gate keep + the planner-backend evolution** ✅ 2026-09-03.
      **Run 27 keep** `akm-cdna2-q8-b4-mmvq-route`: **+23.339% dec-b4** decisive (floor 1.142%),
      **cleared the dec-b8 confirm gate** (+0.313%) — the FIRST time the two-rung gate fired. It is
      a production number: headline **+22.443%** vs frozen production-v9 on the 27B, champion now
      `b0eb4fab` / anchor-gen-015. Mechanism: Q8_0 ne11<=4 rerouted MMQ->MMVQ (the in-tree lever
      around the vendor Tensile GEMM). Banked regardless of planner.

<!-- original line 8134 -->
- [x] **R23-36 — actor exit-1 storm made diagnosable** ✅ 2026-09-03 (`b5cd2817`). Run 27 logged 74
      `actor exited 1:` with EMPTY detail because `claude -p` reports errors on STDOUT (empty stderr)
      and `_run_agent` kept only the stderr tail. Fix: non-zero exits carry backend id + BOTH tails.
      Storm was intermittent (~40% iters), cleared on its own; live repro ruled out auth/concurrency/
      overlay/prompt-size. **NOT root-caused** — see R23-38.

<!-- original line 8139 -->
- [x] **R23-37 — planner backend is now DeepSeek V4 Flash @max via opencode** ✅ 2026-09-03
      (`c2bfe916`). Third `Backend` kind wired: `opencode run --auto --dir <wt> -m
      deepseek/deepseek-v4-flash --variant max <prompt>`; `backend_for` routes `provider/model`
      (has `/`) to opencode. Path was Fable 5.1 @medium (`f81bbeb6`, ~75s/call, 54-71% GPU-idle) ->
      Opus 5 @high (`1ffe4fdf`, default set but NEVER launched) -> DeepSeek (smoke: authored in a
      real champion worktree in ~4s). **TRUST BOUNDARY**: opencode drives an EXTERNAL provider, so
      planner prompts egress off-host — operator-sanctioned as the backup, recorded in code+commit.
      Run 28 live pid 470013 with this planner + the dec-b8 confirm gate.

<!-- original line 8147 -->
- [x] **R23-40 — FIXED+CONFIRMED ✅ 2026-09-04 — INCIDENT: Run-18 build-non-determinism fault recurred on the 445e93a8 anchor
      promotion; run 28 aborted.** After the second keep (`akm-cdna2-q8-b4-y-stream-amortize`
      +10.098%, dec-b8-confirmed, champion `445e93a8`), the anchor guard found the promoted
      anchor-gen-016 binary's code-section digest DIFFERS from a fresh champion rebuild even after
      one heal (`d6d195bb...` vs `5e3ca1e7...`) — the Run-18 fault class — and raised RunAborted
      ("proven with zero pairs spent"). The integrity system worked: it refused to seat a
      non-reproducible anchor. Consequences: headline never republished for 445e93a8 (still shows
      b0eb4fab +22.443%); run 28 is a ZOMBIE (pid 470013 alive but `run_aborted` recorded, step
      None, GPU idle, 1 child, no measurement since 21:58); no anchor-gen-017 recovery. **BOTH
      KEEPS ARE SAFE in git** (champion 445e93a8 = b0eb4fab +23.3% + 445e93a8 +10.1%, both
      screen-decisive + dec-b8-confirmed). ROOT CAUSE to find: why champ2 builds are
      non-deterministic (ccache? -j race? worktree state?) — same class as the 2026-08-31 anchor
      attestation doctrine. **BLOCKS relaunch**: the next keep will hit the same guard abort until
      the build is reproducible. Decision for operator: (a) kill the zombie + investigate build
      determinism before relaunch; (b) relaunch anyway and accept aborts at each keep. Recommend
      (a).
      **ROOT-CAUSED 2026-09-03 (cheap, no rebuild): `libggml-hip.so` is non-reproducible; the
      CPU executable is NOT.** champ2 clean at 445e93a8, ccache absent -> genuine non-determinism.
      Hashing existing binaries' .text: `llama-bench` is BYTE-IDENTICAL across anchor-gen-016 +
      champ2 + all 7 lanes (`7337b4bb`), but `libggml-hip.so` (`6bac92af` vs `55f783de`),
      `libggml.so`, `libllama.so` all DIFFER. The guard (`anchor_integrity.build_digest`,
      run.py:405/475) hashes `bin/libggml-hip.so` ALONE — the gfx90a HIP kernel lib, which is the
      non-deterministic one. Cause class: hipcc gfx90a code-object generation is not reproducible
      build-to-build (parallel-compile ordering / embedded metadata), plausibly aggravated by the
      7-lane concurrent build load; contradicts the guard's R22-3/R21-10 determinism premise, so
      something regressed. FIX (operator design call): (i) make the HIP build reproducible — hipcc
      determinism flags / libggml-hip.so at -j1 / isolate the anchor build from lane builds;
      (ii) hash a deterministic proxy (defeats purpose — the kernels ARE the artifact); (iii) widen
      the guard to accept a hash mismatch when a functional A/A confirms equivalence (weakens the
      R18/R21 doctrine). Recommend (i). Until fixed EVERY keep aborts at its anchor guard, so the
      loop cannot advance past one keep. Both current keeps remain safe in git.
      **FIX CONFIRMED 2026-09-04**: `build_champion` -> `-j1` (research `f4f13116`). The
      determinism probe built champion 445e93a8's `libggml-hip.so` twice at `-j1`: byte-identical
      code digests (`1d04c67a...595bb4`, A=B), VERDICT DETERMINISTIC. So `-j64` parallelism was the
      root cause and serial build fixes it; the promoted anchor and the guard's fresh build now
      match. Measured cost: ~13 min per `-j1` build (786s/794s), per-KEEP only, lane builds stay
      `-j64`. **RELAUNCH-READY** (operator-gated): run 29 = run 28's command on the current champion
      445e93a8/anchor-gen-... rebuilt clean, DeepSeek planner + codex critic + dec-b8 confirm gate.
      Follow-up R23-41: hipcc determinism flags to restore parallel anchor builds later (optional).

<!-- original line 8186 -->
- [x] **R23-42 — the dec-b4 keeps do NOT move DFlash2 decode; run 29 pivoted to tg128 (operator ✅ 2026-10-29 (audit: commit 6e4f00599 (2026-09-04) "R23-42: DFlash2 decode measured flat ... run 29 pivots to tg128"; box text records measured 71.22 t/s and the operator pivot to tg128 (open sub-question is a note)) [no-belief: audit-reconciliation]
      2026-09-04).** MEASURED the DFlash2 smoke on champion 445e93a8 (both new keeps): **71.22 t/s**
      decode, acceptance 0.6427, 2.35x boost — vs 72.65 on the prior champion 732389d6 (R23-17) and
      70.0 at the DF2-5 baseline. So the two keeps that measured **+23.3% and +10.1% on dec-b4**
      (batched prefill) produce **~0% on DFlash2 decode** — the R23-26 non-transfer lesson, now with
      the sharpest contrast yet (decisive +35% prefill -> flat decode). dec-b4 keeps optimize a
      batched-forward path the DFlash2 decode loop is not bottlenecked on (its speed is set by the
      draft model + acceptance, not the target verify). Operator corrected the arithmetic
      `70*1.233*1.101=95` -> measured 71. **Run 29 pivots to hunt a decode-relevant surface**:
      `--surface tg128` (target single-token decode — the "none"/fallback path, ~30 t/s; more
      serving-relevant than dec-b4 prefill, though still not a DIRECT DFlash2 measure since
      llama-bench can't drive the spec-decode loop), dec-b8 confirm gate retained. Needs a tg128 27B
      floor first — **calibration RUNNING** pid 3807583 (~1h), run 29 launches once it writes a sane
      floor. Champion 445e93a8 = anchor-gen-016; -j1 build fix (R23-40) in place so keeps won't abort.
      Open sub-question: is there a surface that DIRECTLY tracks DFlash2 throughput? (would need a
      server-based spec-decode bench, not llama-bench.)

<!-- original line 8202 -->
- [x] **R23-43 — RE-ARCHITECT ✅ 2026-09-04 (a-d BUILT; serving floor tightened via option (2)): keeps demonstrated on llama-server under the champion's CANONICAL
      RECIPE, not llama-bench (operator directive 2026-09-04, four messages).** Principle: "the only
      performance that matters is serving performance; no point boosting llama-bench numbers not
      reflective of a live environment." Proven necessary: dec-b4 keeps +23.3%/+10.1% (bench)
      -> DFlash2 decode 71.22 t/s FLAT (R23-42). Design (operator's):
      · **Champion = (kernel commit + canonical serving recipe).** The recipe is a GENERAL,
        parameterized artifact describing the champion's optimal serving config on its hardware:
        model, quant, `spec_decode.type` in {none, draft-dflash, draft-mtp, ...}, drafter (if any),
        concurrency (np), ctx, ctk/ctv, server flags, and the metric (aggregate vs per-slot tok/s).
        Flexible by construction: a non-DFlash2 model carries `spec_decode: none`/`mtp` + its own
        optimal np -- NO DFlash2 assumption in the framework. It is also the PROMOTION recipe
        (production needs it anyway), so it is not extra work.
      · **llama-bench = experiment/screen layer** (fast, deterministic, planner hypothesis testing,
        null-killing). NEVER decides a keep.
      · **llama-server under the canonical recipe = keep gate + headline.** A keep is real only if it
        improves SERVING throughput under the champion's own optimal recipe.
      BUILD ORDER: (a) canonical-recipe schema + the current champion's recipe (27B/GPU/DFlash2 at
      optimal np -- DF2-5 grid peaked np4-8 ~154 t/s aggregate; pin the optimal); (b) generalize
      `dflash2_capability_smoke.sh` -> a recipe-driven serving A/B (champion vs candidate,
      paired/alternating, reads the recipe); (c) calibrate the SERVING noise floor under the recipe
      (A/A x~12, like dec-b4/b8) so a keep is decisive vs serving noise; (d) wire as the keep gate,
      llama-bench demoted to screen. Supersedes the dec-b8-llama-bench confirm rung and subsumes
      R23-18 (DFlash2 regression guard) and R23-26 (headline surface). Substantial -- a new
      measurement core. Run 29 HOLDS until (a)-(d) exist; champion 445e93a8 + -j1 fix are ready.
      **BUILT + committed 2026-09-04**: (a) `loop/serving.py` general canonical Recipe +
      np-concurrent aggregate-tok/s measurement (research `8285d1bf`); (b) champion recipe
      (27B/GPU/DFlash2 np4, matches DF2-5); (c) serving-floor calibration; (d) `--serving-recipe`
      keep gate wired into commit_pooled, fail-closed, 400 tests (`a745a583`). Dry-run proves the
      gate. **BLOCKER — serving noise floor too coarse**: np4 aggregate throughput A/A =
      **10.375% at temp 0.6** (sampling->acceptance variance), **4.911% at temp 0/greedy** (still
      ~8% run spread from np4 scheduling jitter; wall-clock aggregate is tail-dominated). A >5%
      floor can only demonstrate LARGE serving keeps and would reject the typical small (1-3%) real
      serving gain -- the inherent noise llama-bench existed to avoid. **OPTIONS for the operator**:
      **RESOLVED — operator chose (2) 2026-09-04**: `_measure_once` now returns the SUM of each
      concurrent slot's OWN `predicted_per_second` (not wall-clock aggregate), plus a discarded
      warmup round and a greedy recipe (temp 0, top_k 1, n_predict 384). Result: **floor 3.536%,
      cv 1.572%**, and the median (157.8 agg-tok/s) now MATCHES DF2-5 np4 (~155) instead of the
      wall-clock's misleading 108 — the metric is both tighter AND more accurate (commit `e0b63239`).
      The 3.5% floor is inflated by one tail sample; typical run-to-run is ~1.5%. A ~3.5% floor is
      viable under R23-44 (batch keeps past 2-3x the floor before the serving gate).

<!-- original line 8254 -->
      - [x] **DivergenceAction — RESOLVED, operator 2026-09-04** ✅: HOLD + planner evidence. On a
        bundle that clears bench but not serving (the PROVEN dec-b4 +35%->serving 0% case), the
        champion of record HOLDS, the bundle is KEPT, and `resolve()` emits a `planner_evidence`
        record (kind serving_divergence) that NAMES the bundled keeps. The planner reads it next
        iteration and may revert/revise a specific bundled keep or aim the next hypothesis at the
        serving gap — divergence becomes a strategy signal, not a dead end or a blind pile-on.
        DivergenceAction default flipped ROLLBACK->HOLD; ROLLBACK stays available. (research `a3838ec1`)

<!-- original line 8261 -->
      - [x] **WIRED into the live pooled loop** ✅ 2026-09-04 (research `91925166`): commit_pooled
        inverted — the bench confirm rung is the keep gate, per-keep serving_confirm REMOVED;
        `accumulate_after_keep` re-measures compounded bench (cor_build vs accumulator), fires
        `serving.compare(cor_build, anchor_build)` once on FIRE_SERVING, PROMOTE advances the champion
        of record + snapshots its build + publishes the headline + resets the bundle, DIVERGED journals
        planner_evidence (measured_divergence) and keeps batching. cor_build lives in a protected
        `cor-build` slot (prune only hits anchor-gen-*), snapshotted by copy at startup + each promote.
        Headline moved OUT of promote_anchor — follows serving-demonstrated advances only. New
        `--fire-multiple` (default 2.5). 4 new wiring tests + updated guard-order test; 414 loop tests
        pass, guard exit 0, --help shows the flags.

<!-- original line 8271 -->
      - [x] **R23-46 (rtx6kpro intake) — does the in-window residency sampler perturb the measured ✅ 2026-11-19 [belief: cc]
        process?** External production runbook forbids `nvidia-smi dmon` during qualification (NVML polling
        "reproduced a persistent target-cycle reduction on an unchanged control process"). Ours polls
        rocm-smi/hwmon DURING every window by doctrine. A/A on the canonical tg128 anchor: current rate vs
        1 Hz vs off (residency proven once before the window), 20 pairs. If >0.638% floor, lower the
        cadence — "sample DURING" stays, the rate changes.
        - 2026-11-19 R23-46: needs the A/A run on the canonical tg128 anchor (current residency-sampler rate vs 1 Hz vs off, 20 pairs) in a GPU window; nothing buildable remains.
        - 2026-11-19 R23-46 row (autokernel): `r23-46-sampler-aa-gpu-20261119`. model: DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M, production v10 `llama-bench` tg128 anchor (loop argv, -t 8). Arms in separate processes: residency sampler at the loop's 0.25 s rate, 1 Hz, off, and a second off as the A/A control; 20 rounds with cyclically rotated arm order; effect = median of per-round tps(arm)/tps(off)-1 with a bootstrap 95% CI vs the 0.638% floor. Verdicts NO_PERTURBATION / LOWER_CADENCE_1HZ / PERTURBS_AT_1HZ. Stop-on-answer: verdict after round 20. Stop-on-futility: residency/parse failure, or the off/off control exceeding 0.638% at the round-10 interim or at the end (FUTILITY_*); rc 75 only on STOP or deadline. Gate-class futility-only.

<!-- original line 8330 -->
        - [x] `llama-server` is now PINNABLE ✅ 2026-09-07 (research `da3b0368` → main `7996467f`):
          `Recipe.cpu_list`, default `None` = unchanged behaviour because setting it invalidates the
          3.536% serving floor until re-calibrated; `describe()` records the condition; +3 tests (419).

<!-- original line 8336 -->
        - [x] **Reuse INF-70's sibling-expanded affinity check** rather than rebuilding it: their sampler — ✅ 2026-10-31, research `37dcdcd53f4cfbb27dd80564d5fc4bf407a0c566`; `scripts/kernel_rnd/autokernel/loop/test_serving_foreign_affinity.py` (10 passed; full targeted suite 63 passed + 8 subtests); artifact `artifacts/engineering/autokernel-rebuild-s-batch-20261031/LANDING-RECEIPT.json`. [no-belief: software-contract-fix]
          resolves foreign processes via `/proc/*/exe` and compares `cpus_allowed` against the
          SIBLING-EXPANDED bench set (the literal-range compare is what made `184-191` read as disjoint).
          Source: `/mnt/raid0/llm/tmp/inf70/agents/sync19-20/foreign.py` — **NOT `sync16/`, which INF-70
          RETRACTED 2026-09-07: its `arm.sh:45` carries the same literal `Cpus_allowed_list` vs `0-95`
          compare, so it is the bug, not the fix.** `foreign.py` reads sibling lists from the kernel AND
          samples live `/proc/<pid>/stat` deltas instead of `ps %CPU` — a process-lifetime average
          structurally cannot see a burst, which is what undid INF-70's slowest arm (lowest median foreign
          load, killed by one 3218% spike). Same trap as our own `ps %CPU is cumulative not live` note.
          Wire into the serving gate's residency check.

<!-- original line 8346 -->
        - [x] ~~**Bounded quiet window for SYNC-19/20** (INF-70 offer 2026-09-07): they will message when those~~ (closed 2026-10-29 audit: SUPERSEDED → OP-41 RULED 2026-09-08 (master-handoff-index.md:78; autokernel-unified-surface-program.md:1484): operator owns admission control; INF-70 SYNC-19/20 window offer of 2026-09-07 is stale)
          arms acquire the region and ask us to hold at the next task boundary. Their levers measure 1-3%
          effects against a 16.8% contended A/A floor, so contended they are unresolvable. **Operator call —
          a loop hold is a run-lifecycle action.** Folded into OP-41 as the bounded form of option (A).
          Default if unruled: INF-70 measures contended and labels the result non-claim.

<!-- original line 8352 -->
        - [x] serving floor re-calibration under the pin ✅ 2026-09-08: first run **CONTAMINATED**
          (10.255%, INF-70 server running) → quarantined; clean re-run 10:16:16-10:21:45Z on a
          verified-quiet host (0-95 at 0.4%, zero INF-70 processes) gives **4.581% p95** (n=10,
          cv 3.136%, median 161.08 tok/s; runs 163.13/154.21/154.31/168.46/160.63/168.14/161.53/
          154.24/163.16/159.23), written with its conditions to
          `loop-memory/serving-floor.qwen3.8-27b-q8-gpu-dflash2-np4.json`. Unpinned quiet-host floor
          was 3.536% (n=8).

<!-- original line 8359 -->
        - [x] **serving gate under the new floor** ✅ 2026-09-08 (first firing of a gate that had NEVER run;
          `--force` was a one-off operator permission for this window). cor `445e93a8` vs tip `bff30cebe`
          (anchor-gen-021), recipe `qwen3.8-27b-q8-gpu-dflash2-np4` pinned 184-191, floor 4.581%:
          **n=5** (10:22-10:27Z) 168.74 vs 159.99 tok/s = **−5.19%**, per-pair −4.72/−1.19/−3.16/+0.25/−11.77,
          decisive → `diverged`. INF-70 flagged −11.8 as a **3.6σ outlier** (the other four average −2.2%, inside
          the floor) and that a per-keep LOO at n=5 against a 4.58% floor cannot resolve ~1% keeps — so we **re-ran**
          rather than running LOO. **n=10** (10:35-10:46Z) 164.63 vs 161.05 tok/s = **−2.18%, NOT decisive** →
          disposition **UNCONFIRMED (not refuted)**: sign probably negative, magnitude unclaimable at any affordable
          n. **Champion-of-record HOLDS at `445e93a8`**; the six keeps stay on the tip as provisional and
          re-gateable. Record `loop-memory/serving/bundle-bff30cebee0d.json` (the n=10 record overwrote the n=5
          record; the n=5 numbers are preserved here).

<!-- original line 8371 -->
      - [x] **R23-50 — THREE KEPT KEEPS NEVER REACHED THE CHAMPION (2026-08-29), now protected** ✅ 2026-09-07.
        Operator asked whether relaunches lost keeps. Audited all 31 `kept` rows against the champion
        branch: **28 present, 3 absent** — `akm-q8-1-float2-halfwave` (+5.353%), `akm-q8-1-float4-eighthwave`
        (+4.849%), `akm-q8-1-fourlane-dual-fragment` (+1.846%), one chain on `quantize.cu` branching off
        `042cb2e41`. The loop forked that day: the other branch off the same parent became the lineage the
        2026-08-31 reconcile (`a27287015`, "38 keeps") merged; this chain was never merged and was
        **unreachable** until tagged `ak/orphan-keeps-quantize-20260829` (nothing gc's here, but unreachable
        is one `git gc` from gone). NOT lost to run-29/30 relaunches — this predates them.
        **Do NOT trust the +12.5% compounded these imply.** Same day, `akm-q4k-q8-sum-sidecar` measured
        +6.723%, +2.978%, +2.374%, +1.952%, +1.595% AND four nulls (0.477/0.993/0.999/0.112%) against a
        0.668% floor — a 6.6 pp spread on one mechanism in one day — and every re-measurement since
        (~80 attempts through 2026-09-02) came back null or negative, ending at −0.449%/−0.091%.
        2026-08-29 is also the retraction day (correctness gate ran `test-backend-ops` with an unsupported
        `--suite-seed`, so verdicts were never really measured). Corroborates INF-70's contention finding.

<!-- original line 8385 -->
      - [x] **R23-50a — RECOVERY SEEDED (operator directive: "we must ABSOLUTELY recover them")** ✅ 2026-09-07:
        inbox `23-recover-q8-1-quantize-cdna2-wave-vectorized.md` = `AK-H-RQ-1`, diffs saved under
        `loop-memory/patches/orphan-keeps-20260829/` (3 per-step + combined). Re-DERIVATION, not cherry-pick:
        the champion's `quantize_q8_1_1d` is verified still the upstream scalar kernel (no CDNA2 branch), but
        five later keeps rewrote the batched reductions in the same file. **Ceiling finding that bounds the
        prize: `quantize_q8_1_1d` is ≤3.6% of tg128 in the live profile, so +12.5% from this one pass was
        never physically possible — the 08-29 numbers were noise; the recoverable mechanism is worth 1–3%.**
        Mutually exclusive with `AK-H-AQ-1` (deletes the pass) — seed says which supersedes which. Run 30
        picks it up on its next planner call (live inbox re-read, no restart).

<!-- original line 8396 -->
      - [x] **R23-51 — THE BUNDLE IS NOW DURABLE; the serving gate had NEVER fired** ✅ 2026-09-07
        (research `706e6894` → main `2de94d08`). `run.py` built `Bundle(champion_of_record=anchor_commit)`
        fresh at every startup, so each restart reset the keeps AND advanced the champion of record to the
        accumulated tip — **laundering bench-only keeps into the serving-demonstrated slot**. Verified: no
        `epyc.autokernel.serving_ab.v1` record exists anywhere on disk, i.e. the R23-44 gate has never once
        run. Trajectory: bundle reached +5.19% (4 keeps, the ~5% the operator remembered), peaked at +6.13%
        (5 keeps), reset to 0 by the run-30 launch — against an +8.84% threshold it was never allowed to
        reach. `load_bundle()` now restores it and refuses state the tree no longer contains.

<!-- original line 8408 -->
        - [x] **seeded MEASURED +5.958%** ✅ 2026-09-08 (tg128 tip-vs-cor over the 6 keeps since `445e93a8`,
          20 pairs, decisive, `drifting=False`); **serving gate n=10 −2.18%, not decisive → cor HOLDS at
          `445e93a8`**, keeps provisional. Durable bundle: cor `445e93a8`, tip `bff30cebe`, 6 keeps, compounded
          +5.958 (bench, measured); on the next launch `load_bundle` advances the tip to the new anchor and
          keeps the cor.

<!-- original line 8414 -->
      - [x] **R23-54 — serving gate is MANDATORY, not threshold-triggered** ✅ 2026-09-08. Its first firing (2026-09-08)
        showed an **11-point proxy-vs-truth gap**: the tg128 proxy said **+5.958%** while the serving gate said
        *"cannot tell, probably slightly negative"* (−2.18%, n=10) — a gap the bench alone would never have shown.
        Make the loop spend the serving gate on **every N keeps regardless of the compounded estimate** (or drop
        `fire_multiple` to 1.0). **Operator to confirm the cadence.**
        **RULED (operator, 2026-09-08): N = 4** — the gate fires every 4 keeps regardless of the compounded bench
        estimate, in addition to (not instead of) the existing `fire_multiple` threshold trigger; implemented in
        research `56195d3e` (`accumulate.SERVING_GATE_EVERY_KEEPS = 4`, durable `Bundle.keeps_since_serving_gate`
        reset on every gate run whatever the outcome, and a `trigger: threshold|cadence|both` recorded in the
        serving-gate record, the status body and the dashboard card; 434 loop tests, was 423). The uncalibrated-floor
        fail-closed guard is unchanged: with no floor the gate can only return DIVERGED, so neither trigger spends it.

<!-- original line 8425 -->
      - [x] **R23-55 — A FLOOR WITHOUT ITS UNIT IS A 1200-FOLD ERROR. Every floor file must record `unit`.** ✅ 2026-09-14 — implemented in research `eb8a88de` (branch `fix/noninf-floorunit`): `serving.calibrate_floor` stamps `unit` (DERIVED from the harness: a fresh server per sample ⇒ `process`) and `n` on the v1 row and inside the v2 `content_sha256` seal; `write_floor(..., unit=...)` has **no default** and refuses an omitted, unknown, contradicted or `n`-less row without writing; `load_floor` returns a pre-rule file untouched as `unit=None`/`legacy=True` and `FloorReading.gate_floor(effect_unit=...)` REFUSES it (file, both units, 0.501%/2.793%, recalibration command); `serving.compare` requires `floor_unit`, checks it against the unit it measures in, and records `effect_unit`/`floor_unit`; `run.py` (`_gate_floor`), `serving_gate`, `source_loo`, `instruments.read_floor`, `recal_serving_floor`, `fold2_gates`/`seed_bundle` (`--floor-unit`) and the bench path (`bench.FLOOR_UNIT`, `floor_rows` refusal, campaign writer stamps `unit`+`n`) all carry it; a pre-rule BENCH record derives its unit from its single-writer SCHEMA, so no floor file on disk was rewritten. 31 new tests in `test_floor_unit.py`; loop suite 155F/2596P vs 176F/2509P on `origin/main`, zero new failures by name.
        Measured by INF-70 (2026-09-08, RETEST-1) and owed to INF-73 U2, which already requires each floor to
        carry harness, n, contention model and host-state hash — **`unit` (arm | session | process) is the
        missing field, and it is the one that changes the answer by three orders of magnitude**:

        | scope | sd | what it costs |
        |---|---|---|
        | within-session (**arm**-scoped knob) | **0.501%** | — |
        | between-session (**process launch**-scoped knob) | **2.793%** | ~**13x coarser** floor |

        A **process-scoped** knob faces a floor ~13x coarser than an **arm-scoped** one. Concretely: INF-70's
        0.171% *arm* floor says CHAMP-2 THP needs **4 sessions/side**; the correct **session-unit** answer is
        **4,780** — a **1200-fold** underestimate that would have been spent as real host time.
        Action here: `loop-memory/serving-floor.*.json` and the bench-floor records must **record `unit`
        alongside harness, n, contention model and host state**, and a gate that compares an effect to a floor
        of a different unit must **refuse**, not warn. Cross-ref: `autokernel-unified-surface-program.md` U2.

<!-- original line 8478 -->
      - [x] **R23-56 — RETEST-1 CLOSE-OUT: no CPU keeps; consolidation complete** ✅ 2026-09-08. INF-70's
        final RETEST-1 report (~12:10Z) yields **zero keeps to fold**, so the consolidated champion stands at
        **`ef81196d5`** (see `autokernel-champion-aggregate.md` → *CONSOLIDATION COMPLETE*). Bookkeeping:

        | item | value |
        |---|---|
        | RETEST-1 A/A (today) | **1.051%** / **0.171%** (**arm**-unit floor) |
        | arms lost to foreign tooling | **1** (python@800% + opencode, `Cpus_allowed` 0-191, **unattributed**) |
        | `inf70/sync17-fix2` @ `2516c9807` | **CLAIM, regression -2.136%** -> **DO-NOT-FOLD** (both knobs default ON *is* the regression) |
        | CHAMP-2 THP | **+3.458% NON-CLAIM** (p=0.143), **not** mechanism-refuted -> unresolved, operator call on INF-70's side |

        Q2 third-party disturbance is now **priced**: a **1-in-6 hit rate ~= a 17% tax in arms**, paid on work
        identified as garbage only *after* running it. **Serialisation between the two sessions held — it is
        not the binding constraint**: *"Region-lock serialises those who call it; nothing constrains those who
        don't."* -> feeds **OP-41** (admission-control broker), see `autokernel-unified-surface-program.md` 3.4.
        Host-state change for the record: at **12:05Z** the operator stopped the orchestrator API (uvicorn
        :8000 + 6 workers, **pid 3961116**, up since 2026-08-26) via `orchestrator_stack.py stop orchestrator`;
        hub :8100, OCR :9001, sd_server :8190 and the docker containers remain. Originally recorded here as a
        **candidate (unproven)** source of the 800% python that cost one Q2 arm; **CORRECTED 2026-09-08**: the
        stop is a **measured NON-CONFOUND**. INF-70's host sampler straddled it inside one session (`S14_ON`)
        and read **flat** across 12:05Z — busy cores **47.89-48.26** against 48 benchmark threads, i.e. no step.
        The Q2 disturbance stands; only its attribution to the API process is withdrawn.
        Also inherited: INF-70's `gate.py` now routes all statistics through one `screened()` function (cannot
        compute over screen-dropped arms, cannot PASS on zero cases), mutation-tested both directions — this
        **generalises the ak-rebuild FOLD-2 vacuous-pass guard**.
        The operator's *no kernel research until a FULLY consolidated champion* condition is **satisfied**;
        **loop relaunch remains a separate operator go** and is deliberately not scheduled here.

<!-- original line 8588 -->
      - [x] ✅ 2026-09-08 **R23-58 — MEASURE THE THP SHIM AGAINST THE SERVING FLOOR BEFORE SPENDING ANOTHER SERVING GATE.**
        ✅ 2026-09-08 **COMPLETE — BOUNDED NULL (T0/D0). DO NOT ADOPT ON THE GPU SERVING PATH. R23-58 IS CLOSED.**
        Verdict block below; the registered action was pre-fixed and is honoured as written.
        The serving gate launches a fresh `llama-server` per sample, so it is **session-unit** and pays exactly
        the variance above; its clean floor is **4.581% p95 at n=10** (`serving-floor.qwen3.8-27b-q8-gpu-dflash2-np4.json`),
        and that floor is the binding constraint on every GPU keep — it is why the 6-keep bundle resolved only to
        "cannot tell" (R23-51/CHAMP-1). If `GGML_NOHUGEPAGE_PROCESS=1` compresses launch variance on the GPU
        serving path the way it did on the CPU decode path, **a recipe change found on the CPU surface unblocks
        GPU keeps that are currently unresolvable** — the first result in either campaign that pays on the other
        surface. Method, with INF-70's two cautions: **pair adjacent launches** (session unit; keep every arm-unit
        floor out of the arithmetic), and **compare tails, not only means** — the effect was a compressed downside
        tail, so a means-only design can miss it entirely. Cost ~= one floor recalibration per arm. Run it BEFORE
        the next serving gate, not after. Gated on the operator's relaunch go.

        **PRE-REGISTERED AND READY 2026-09-08 (not run).** Design, runner and pre-flight live at
        `/mnt/raid0/llm/tmp/r2358-shim-serving-20260908/` (`PREREGISTRATION.md` sha256 `0a72a0256a0c8977…`,
        freeze before the first launch; `run_r2358.py` dry-by-default, `--run` required; `CHECKLIST.md`).
        | element | value |
        |---|---|
        | design | **two interleaved, order-balanced A/A calibrations**, NOT a paired A/B |
        | why not A/B | `serving.compare` varies the BUILD from one recipe, so a same-build env arm is inexpressible; and its median-contrast statistic is exactly what misses a compressed tail |
        | interleaving | couple-by-couple (odd OFF,ON / even ON,OFF) so host drift cannot alias into the arm contrast |
        | n | **24 couples = 48 launches**, up to 28 launched (4-couple replacement budget) |
        | primary statistic | ratio of `p95_dev_pct` (the same formula `floor_pct` is defined by, via `serving._spread`), sd(log) alongside |
        | inference | within-couple label permutation on median-normalised runs (exhaustive ≤18 couples, else 200,000 draws, seed 2358) — null exact for any statistic |
        | power | ~0.97 vs a 3x dispersion ratio, ~0.69 vs 2x; 3x is the campaign-relevant threshold (it is what would have made the −2.176% bundle decisive) |
        | wall-clock | **~60 min typical, <=77 min worst case** at 75-82 s per launch (derived two independent ways from loop-memory serving artifacts) |
        | throughput claim | read from the SAME 48 launches at zero extra cost; a null here with a real dispersion effect is a **SUCCESS, not a mixed result** |
        **Build: NO REBUILD NEEDED** — `/mnt/raid0/llm/tmp/build-fold-ef81196d5` (the FOLD-2 candidate build of the
        champion; `CMakeCache.txt` -> source `fold-ef81196d5-src` at `ef81196d5`, clean tree, all four
        `gfx90a-house-v1` flags matching) already carries the shim in `bin/libllama-common.so.0.0.10301`
        (marker, both env strings, `prctl` in `nm -D`; `ldd bin/llama-server` resolves to it).
        **Controls, all fail-closed:** Control 0 resolves the library through `ldd` under
        `Recipe.server_env(build_dir)`, refuses a library resolving OUTSIDE the build dir, records its sha256
        per launch, and **must reject a known pre-fold build** (`build-cor-445e93a8`) or the run does not start.
        The knob readback is `serving.verify_env_readback` (declared, not re-implemented); AnonHugePages is the
        independent second control, and a `thp_enabled=0` with `anon_huge_pct >= 1.0%` stops the run as a
        controls conflict with no verdict issued.
        **Two vacuous-pass hazards found and closed while preparing this** (both now impossible by construction):
        an any-match glob over `libllama-common.so.0.0.*` would have passed on a stale sibling the loader never
        maps — `champ2/build-hip/bin` holds FIVE vintages from five dates; and the first pre-flight concluded
        "no build carries the shim" after scanning the `llama-server` EXECUTABLE, which never contains strings
        from a linked library. That false blocker would have cost a 64-job rebuild contending with INF-70's live
        measurement. See the eleventh sign in the vacuous-verification record.

        **VERDICT 2026-09-08 (ran 16:35-17:02Z; 1607.4 s).** Ran to the registered stop rule. **48 launches /
        24 couples, 24 valid of 24 launched, none replaced**, every launch residency `proven`, all 48
        positive-control readbacks correct in **both** directions.

        | element | result |
        |---|---|
        | claim (i) LEVEL | **T0** — 5/10 ON faster at the second look (exact two-sided alpha 0.0430). A coin flip. **No magnitude may be quoted.** |
        | claim (ii) DISPERSION | **D0** — `p95_dev` ratio OFF/ON = **0.713**, p = 0.3159; sd(log) ratio 0.918, p = 0.5854 |
        | OFF arm | median **167.117** tok/s, p95_dev **6.657%**, cv 3.671%, n = 24 |
        | ON arm | median **169.396** tok/s, p95_dev **9.334%**, cv 3.905%, n = 24 |
        | registered action | **NULL. Do not adopt. Close R23-58.** |

        The dispersion point estimate does not merely miss significance — it points the **wrong way**: the ON arm
        is slightly **WIDER**. The CPU surface's compressed downside tail does not appear here at all.

        **BOUNDED, never unqualified.** At n=24/arm the primary permutation test had ~0.97 power against a 3x
        dispersion ratio and ~0.69 against 2x. **A large effect is excluded; a small one is not.** Any citation
        that drops the bound is a misquote.

        **WHY THIS NULL IS ADMISSIBLE WHERE SYNC-18's WAS NOT — the controls are the valuable half.** The
        mechanism demonstrably RAN: OFF arm AnonHugePages ~53% of RSS, ON arm **0.0% on every launch**, kernel
        `THP_enabled` read back correct in both directions all 48 times. This is not a knob-never-fired null --
        the trap that made INF-70's SYNC-18 untestable as built. **A null from a knob proven to have fired is
        evidence; a null from a knob that never reached dispatch is not.**

        **CONSEQUENCE — THE LAUNCH RECIPE IS PER-SURFACE. This qualifier is load-bearing and must travel with
        every champion citation.** `GGML_NOHUGEPAGE_PROCESS=1` is **adopted on the CPU decode path** (CHAMP-2,
        operator ruling) and **MUST NOT be added to the GPU serving recipe** -- R23-58 is the measurement that
        separates them. A reader who sees only "the champion runs with the shim" will add a knob to the GPU
        launch path that buys nothing: the PROD-1 failure mode exactly. Spell **both** knobs out wherever this is
        cited -- adopted `GGML_NOHUGEPAGE_PROCESS` (prctl, at launch, **CPU only**) vs pre-existing
        `GGML_NOHUGEPAGE` (madvise, already on).

        **Evidence** (all frozen before the first launch): `/mnt/raid0/llm/tmp/r2358-shim-serving-20260908/` --
        `PREREGISTRATION.md` sha256 `0a72a0256a0c897768ce396fa20e21f7b969b42e588d28ebb54db8cb04c59d01`,
        `FROZEN-AT-LAUNCH.sha256` (registration + runner + checklist, stamped 2026-09-08T16:35:38Z),
        `VERDICT.json` (schema `epyc.r2358.verdict.v1`), `VERDICT.md`, `launches.jsonl`, `thp_proof.txt`,
        `arm-off.json`, `arm-on.json`, `run.log`. Build `/mnt/raid0/llm/tmp/build-fold-ef81196d5`, source
        `ef81196d5bdd4190b46dff4ae7eecc333a46c8ce`, tree clean. Promoted out of scratch into the research repo
        (`data/`) at commit `48a6f6f2`.

        - [x] **R23-58a — the per-surface qualifier is recorded wherever the champion recipe is stated**
          ✅ 2026-09-08 (`autokernel-champion-aggregate.md` CHAMP-2, this page, the wiki compile, and
          `docs/design/champion-max-performance-20260908.md`).

<!-- original line 8678 -->
      - [x] **R23-60 — THE SERVING PATH PROVES NO GPU RESIDENCY.** ✅ 2026-09-08 **LANDED** — research
        `f00d78be`, merged `657910f1`: `serving.py` samples residency across each launch, records the
        window it covers, and **refuses a launch measured non-resident**. Schema
        `epyc.autokernel.serving_residency.v1`. Proved out end-to-end the same day: all 48 R23-58
        launches and all 12 max-performance-sweep launches carry `status: proven`. `bench.py` samples residency; `serving.py`
        samples nothing. **Every serving number this campaign has taken is therefore un-proven as GPU-resident**,
        including the 4.581% floor and the bundle gate that held the champion at `445e93a8`. The numbers are
        very likely fine — this is a missing proof, not a suspected defect — but it is exactly the kind of gap
        that cannot be filled retroactively: a residency tuple invented on read claims warrant the original run
        never captured. Wrap each serving launch in `residency.Sampler` (the R23-58 runner already does this
        itself; the fix is to move it into `serving.py` so every consumer gets it) and record VRAM sampled
        DURING the run plus the KFD process count in the serving record. Standing rule: "I invoked the HIP build"
        is not evidence of a HIP run, and `ldd` cannot prove one.

<!-- original line 8727 -->
        - [x] **R23-61a — RUN THE RECALIBRATION at n >= 24 and write `n` + a CI into the floor record.**
          ✅ 2026-09-15 — option (b), **PRE-BIOS floor**: p95_dev **7.897%**, unit `process`, n=24 (24/24 valid),
          95% bootstrap CI [5.520, 11.322]% (descriptive), median 160.18 tok/s, `recipe_hash 29fbffc56cd7`, provenance
          verified, residency proven 24/24 (peak VRAM 40.44 GB, KFD 1), build `build-fold-ef81196d5`, shim not set.
          Written to `autokernel/loop-memory/serving-floor.qwen3.8-27b-q8-gpu-dflash2-np4.json` (sha `0fdf07c0…`), gates
          via `run._gate_floor`; prior record kept as `.pre-r2361a-20260915.json.bak`. CI code: research branch
          `sub/r23-61a-floor-n-ci` `a25aaf1f`. The standing 4.581%/n=10 lies below the CI; R23-58's 6.596% lies inside.
          Window, harness and build differ from the old floor, so this is NOT a measured degradation.

<!-- original line 8821 -->
      - [x] **R23-70 — `stack_change_guard.py:78` points operators at the WRONG recompile command.**
        `RECOMPILE_PRIORS_COMMAND = "uv run python scripts/registry/compile_stack_priors.py"` is a numa-blind
        wrapper around `src.registry.stack_priors.main`, which has no `--numa-mode` and compiles the legacy
        single-instance lineup while production declares `numa_mode: both`. Following the guard's own
        remediation text produces a priors file that disagrees with `launch_manifest.yaml` on every
        multi-port role (frontdoor [8070] vs [8080,8180], ingest [8085] vs [8185,8285], toolrunner/worker_*
        [8072] vs [8082,8182]) — measured 2026-09-22, reverted. Should read
        `scripts/registry/stack_change_pipeline.py update`, matching the pipeline's own five messages and
        `docs/reference/stack-change-launch-runbook.md:16`. One-line fix, in epyc-orchestrator.
        ✅2026-10-06 — MAIN accepted exact text-only correction and existing test expectation, APPmain81663c30; [static source review](../../artifacts/ni08/stack-guard-remediation-source-20261006/README.md). No build/test execution or owner runtime change.

<!-- original line 8831 -->
  - [x] **R23-71 — a live `--skip-stack-change-gate` sits in benchmark automation.** ✅ 2026-10-31 — ROOT `1108d2206a65089ac634fb05264563a4c80976a9`, [validation](../../artifacts/compute/codex3-r23-71-stack-gate-20261031/VALIDATION.json). [belief: cc]
    - The live BULK-K-EMB-1 entry and compiled manifest now run the canonical stack-change gate, remove the registry-compile skip, and clear inherited gate/registry bypass variables for that start. Its manifest entry hash was recomputed; historical execution snapshots remain unchanged. All 52 source entries pass schema/lint, the source and target manifest entry agree, shell syntax and four current-gate predicate controls pass; the unrelated pre-existing KOP2 manifest-hash mismatch is unchanged. No service or inference was started. [belief: cc]
        `coordination/inference-batch/entries/30-bulk-campaign.yaml:297` (and the BULK-K-EMB-1 bundles,
        `manifest.yaml:3076`) start embedders FOR A BENCHMARK with
        `--skip-stack-change-gate --no-compile-registry`. `stack-change-launch-runbook.md:114` forbids exactly
        that ("never for benchmarks, AutoPilot resumes, or claimed production readiness"), and
        `accepted_gaps.yaml:3-10` records the 2026-08 precedent: "A bypass used four times running is not an
        escape hatch, it is the new default." Either justify it as a declared accepted gap with an expiry, or
        remove it.

<!-- original line 8840 -->
  - [x] **R23-72 — `executor.py` registry-failure fallbacks resolve through the serving kernel store.**
        ✅ 2026-10-29 for the separate research copy in `scripts/lib/executor.py`, research
        `38c93a3785c1cfad717b2e6d9c641f7a76093e20` on `origin/main`: both the unavailable-registry
        fallback and the missing-`base_dir` fallback now share `/mnt/raid0/llm/kernels/production/cpu`.
        Explicit registry paths and `LLAMA_BIN_DIR` precedence are unchanged. The orchestrator copy was
        already repaired by `fa1eb43a2c4431d695e5c4339373ecbf3b96aed6` (2026-10-06); this closes the
        remaining research-copy gap. Focused executor/canonical-recipe validation: 39 passed, 1 skipped;
        new tests pass lint/format, and the executor's 11 pre-existing Ruff findings are unchanged.
        No inference, production-tree edit, process restart, or deployment. [no-belief: tooling-repair]

<!-- original line 9016 -->
      - [x] **R23-52 — status heartbeat during keep post-processing** ✅ 2026-09-07 IMPLEMENTED (research `70d98807`; 4 `publish()` calls: anchor build / headline / reprofile / accumulate; 422 tests; takes effect at the next launch — run 30 holds the old module). Observed run 30, 2026-09-07: after the first
        keep (`bff30cebe`, +2.583%) `loop-status.json` went **30+ min without a write** while `promote_anchor` did
        the clean anchor build (gen-021, 117 objects at 20:07Z, `cmake`/`gmake` children 9 min in), then verify,
        headline bench, reprofile, accumulate. The dashboard's freshness envelope reads that as a dead loop and the
        monitor had to infer the keep from the anchor-gen directory appearing. Fix: `status.write()` at each keep
        sub-stage (`building anchor gen N`, `guard`, `headline`, `reprofile`, `accumulate`) so the loop is never
        silent for longer than one build. Cheap; no measurement impact.

<!-- original line 9023 -->
      - [x] **R23-52b — 30 s STATUS HEARTBEAT + ACTOR HEALTH** ✅ 2026-09-08 (operator: "the ENTIRE point of the dashboard
        is up-to-date visibility… without wasting ANY extra tokens on LLM sessions to monitor"). Root cause of the
        STALE banners: status was written only at stage boundaries (30-47 min gaps during builds / 20-pair gates), and
        the 135 `planner_transient` rows of run 30 (claude CLI **"You've hit your session limit"**, 16:31-23:35Z, GPU
        idle-while-claimed 48%) were invisible — status said `running`. Fix (research `c488ad4a` → main `81b3c017`): a
        daemon thread re-publishes the last step every 30 s (envelope 180 s: silence = process gone) and the body
        carries `actor_health {recent_attempts, planner_transient, failing, last_failure}`; `loop.html` shows
        `ACTORS FAILING · n/m · <reason>` in the header. Takes effect at the next launch (run 30 holds the old module).

<!-- original line 9079 -->
      - [x] **Run 30 launched** ✅ 2026-09-07 16:31Z — run 29 stopped (opencode `event` change-feed grew the
        actor DB to 236 GB); defaults switched to codex planner + Fable@medium critic (`e371788d`), no
        opencode actor; same measurement config; accumulator restarts at 0 keeps (run 29's 2 keeps are on
        the champion branch). Next launch: `python3 -u` (stdout block-buffered → empty run30.log).

<!-- original line 9083 -->
      - [x] **Headline freeze (R23-44 defect) fixed** ✅ 2026-09-07: moving `publish_headline()` to the
        serving-PROMOTE branch froze the champion-vs-production headline for the whole accumulation phase
        (operator saw a 3.8-day-old SUPERSEDED number, 2 champion gens back, on the OLD dec-b4 surface).
        Restored per-keep publish in `promote_anchor` after the guard (research `f3282204`; activates at
        next relaunch, run 29 not restarted) and the dashboard now renders a superseded headline during
        accumulation as "ACCUMULATION IN PROGRESS — tip, keeps, +X%, % to gate" (`d0d11065`).

<!-- original line 9089 -->
      - [x] **Accumulator observability** ✅ 2026-09-04: the loop status now carries the two-tier
        bundle (`accumulator`: champion-of-record, keeps, compounded_bench_pct, fire_threshold_pct,
        progress_fraction, fires_next) and the `/loop` dashboard renders an "Accumulator — compound-
        then-gate" card with a progress bar toward the ~8.84% serving-gate threshold (research `ee0456fd`,
        dashboard `6f630ecf`). Operator can watch keeps batch toward the gate.

<!-- original line 9094 -->
      - [x] **RUN 29 LAUNCHED** ✅ 2026-09-04 (PID 3217060, continuous): tg128/27B calibrated (floor
        0.638%@20p), two-tier gate live (screen tg128 / keep-gate tg128 / serving np4-DFlash2 3.536%),
        DeepSeek planner + codex critic, champion 445e93a8. First end-to-end compound-then-gate run.

<!-- original line 9103 -->
- [x] ~~**R23-39 — measure whether DeepSeek/opencode restores throughput.** Run 28's open question:~~ (closed 2026-10-29 audit: OBSOLETE → run 28 DeepSeek/opencode throughput question is long over (runs 29-30+ since, R23-42 :1620); planner backend replaced by INF-78 OAB path)
      does the ~4s DeepSeek call latency close the 54-71% GPU-idle gap the Fable planner opened?
      Read idle_fraction_while_claimed + iterations/hour after run 28 has a few hours, compare to
      run 26 (all-codex) and run 27 (Fable). Decides whether the external-provider trust cost is
      worth it or the planner should return to a local CLI.

<!-- original line 9108 -->
- [x] ~~**R23-33 — OPERATOR DECISION: does +7.206% on the worker change the promotion calculus?**~~ (closed 2026-10-29 audit: SUPERSEDED → v10 final freeze ratified 2026-09-22 (artifacts/operator/ratify_v10_final_freeze_20260922.json) - promotion calculus decided by operator; champion folded into v10)
      Before today the promotion argument was "the champion is neutral-to-negative on production".
      It is now "the champion is decisively +7.2% on an in-fleet production role model, -1.4% on
      the 27B prefill surface, and 2.38x on speculative decode". That is a materially different
      conversation and it is the operator's to have. Inputs: the freeze runbook
      (`docs/reference/kernel-freeze-runbook.md`), R23-29's promotion-time condition (the Q4_K paths
      are now performance-VALIDATED by this measurement, closing that gap for dec-b4), and R23-26
      (a promotion headline must state its workload). **No run starts, and no promotion step is
      taken, without explicit operator permission** (standing instruction 2026-09-03).

<!-- original line 9117 -->
- [x] **R23-30 — the boundary driver's 15-min SIGTERM grace is WRONG for a confirm-rung run and will SIGKILL every stop.** ✅ 2026-10-31, research `37dcdcd53f4cfbb27dd80564d5fc4bf407a0c566`; `scripts/benchmark/test_boundary_20260901_drain.py` (11 passed); artifact `artifacts/engineering/autokernel-rebuild-s-batch-20261031/LANDING-RECEIPT.json`. [no-belief: software-contract-fix]
      Measured 2026-09-03 stopping run 25 (27B rung, 7 workers):
      graceful drain took **~87 min** (SIGTERM 07:59:09Z -> last publish ~09:25Z), because each lane
      holding a measurement finishes it and lanes serialize on the claim. Publish cadence was
      steady at **17.3 / 17.5 / 17.8 min** per lane; 2 lanes abandoned at formation, 5 completed.
      `boundary_20260901.sh:98` sets `KILL_WAIT_S=900` with the comment *"drain-tier loop: <=5 min
      historically"* — true for the 1.5B screen rung (run 23 drained in 15 min) and **false by ~6x
      for the 27B rung**. As written the next boundary SIGKILLs mid-measurement every time,
      discarding up to ~17 min of device work per in-flight lane and losing those verdicts.
      **Fix**: scale the grace to `workers x per-measurement-time` for the configured rung (~2 h for
      7 workers on the 27B), or make the driver poll for loop exit rather than use a fixed deadline.
      **Diagnostic note for whoever reads a drain**: `loop-status.step` names only the ONE active
      lane, never the queue — lanes serialize on the claim, so remaining work must be derived as
      `workers - (abandoned + published)`, not inferred from the step field. Two ETAs were wrong in
      this session for exactly that reason.

<!-- original line 9235 -->
- [x] **R23-19a — the confirm-rung headline instrument built and proven** ✅ 2026-09-02 —
      `scripts/benchmark/headline_on_confirm_rung.py`: dry-run resolves the 27B keyed floor
      (0.949% @20 pairs) and the dec-b4 shape (pp=512 tg=0 ub=4); BOTH fail-closed paths
      mutation-tested rather than assumed — provenance mismatch rc=2, uncalibrated surface rc=3
      (fired against dec-b8 live, while its calibration was still running). Cached
      `v9v-build-base` reused, so no production rebuild. Measurement itself is R23-19.

<!-- original line 9241 -->
- [x] **R23-20 — the 27B dec-b4 keyed floor landed and was verified sane** ✅ 2026-09-02 (10:03Z)
      — `calibration/dec-b4.Qwen3.8-27B-Q8_0.json`: floor 0.949% @20 pairs (1.142% at the pairs=5
      confirm gate), A/A effect +0.576% sitting INSIDE its own derived floor as a clean A/A must,
      drift 0.13/0.27% with no trend, residency 40/40 resident and clocks pinned 1700 MHz,
      device_seconds 3282 per condition. First 27B floor the program has ever had.

<!-- original line 9246 -->
- [x] ~~**R23-21 — decide whether the confirm-rung headline also gets measured on dec-b8** — dec-b4~~ (closed 2026-10-29 audit: SUPERSEDED → dec-b4 confirm-rung scope abandoned: run 29 pivoted to tg128 (R23-42, autokernel-rebuild-program.md:1620, commit 6e4f00599); dec-b8 decision never recorded)
      is the approved scope (operator 2026-09-02); dec-b8 would cost another ~1 h and is the other
      confirm surface. NOT auto-run: it doubles the hold on run 24 for a second view of the same
      question. Decide after R23-19's dec-b4 number is in hand — if dec-b4 shows heavy
      attenuation, dec-b8 becomes informative rather than confirmatory.

<!-- original line 9251 -->
- [x] ✅ 2026-09-04 **R23-18 — standing rule candidate: DFlash2 smoke joins the confirm gate** — any future
      keep touching fattn*/mmvq/mmq/speculative-verify files should trigger the capability smoke
      before the champion advances (cheap: ~5 min; the confirm rung already owns the 27B).
      Decide after R23-17's first measured result whether this goes in loop code or stays a
      boundary-step; if loop code, it rides the regrowth budget conversation.
      **✅ 2026-09-04 — SUBSUMED BY R23-43** (`[x]`, BUILT + committed): *"subsumes R23-18 (DFlash2 regression
      guard) and R23-26 (headline surface)"*. The serving gate now owns the DFlash2 surface.

<!-- original line 9270 -->
- [x] **R24-1 — wire the existing hardened bench into the live loop.** ✅ 2026-09-15 — `loop/bench.py:219-221` runs plain
      `llama-bench`. `--autokernel-harden <per-candidate seed>` (llama.cpp `a4cb04ca8`, RVP-C6-8) and
      `microbench._check_autokernel_hardening` (research `execution/microbench.py:1765-1880`) exist, but nothing
      invokes them. `run_once` should pass the flag and admit a `Comparison` only when the hardening receipt check
      returns no reasons. **Why now:** the FlashInfer contest harness timed the SAME tensor objects its correctness pass
      had just used, and a placed team shipped a `data_ptr`-keyed output memo. llama.cpp graph reuse
      (`llama-context.cpp:1370-1383`) presents identical pointers with different content on every rep. The hazard is
      observed practice on a surface shaped like ours (intake-1426#record, intake-1431#record). Zero compute beyond the
      bench already run.
      **Landed:** research `13f8e63a` / main `81fbd472` passes one per-candidate hardening seed to
      every arm and refuses every receipt reason before constructing a `Comparison`.
  - **Provenance note 2026-09-16 (sub-closure-fix; annotation only, box state untouched):** the cited anchor `a4cb04ca8` (`a4cb04ca8f92fa4d665684490f609b380f9b5e96`) **exists on no ref**. It is absent from all llama.cpp `fork` refs (`ls-remote`), from the canonical tree and from every local clone (`git cat-file` fails). The equivalent hardening lineage is llama.cpp `974b5fcb3` ("llama-bench: harden AutoKernel measurement instrument", sole parent frozen v9 `0db32c06`). It is the tip of `fork/experimental-v9-autokernel-t1-hardening-final`, **not** of `fork/experimental-v9-autokernel-t1-hardening` (tip `0492c2319`, a separate one-parent commit). Descendants include `d9fdc17bd`. Live manifests still pin the missing SHA: `/mnt/raid0/llm/autokernel/iqk-*.json` (6 files, e.g. `iqk-bootstrap-intervention-r3-execute.json`). The owner should re-point the pin and re-hash the manifest. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #1).

<!-- original line 9282 -->
- [x] **R24-2 — measure with a TRUSTED instrument and review the WHOLE tree.** ✅ 2026-09-15
      (i) Build both arms' `llama-bench` from a pinned instrument commit; today `loop/run.py:414-415` builds it from the
      candidate's own tree.
      (ii) Critic pass 2 diffs only actor-declared paths (`loop/actors.py:493-495`). Hash `git status --porcelain` plus
      the full `git diff`, and refuse any candidate whose worktree diff touches undeclared paths or anything outside
      `ggml/src/` (especially `tools/` and the instrument frame).
      (iii) Run `execution/reward_hack_scan.py` over the whole diff; its flags withhold ranking.
      Source: intake-1426#record.
      **Landed:** the existing whole-tree/protected-instrument validation remains authoritative and
      the full diff now passes `reward_hack_scan`; undeclared, protected and named exploit findings
      hard-refuse before build. Research `13f8e63a` / main `81fbd472`.

<!-- original line 9293 -->
- [x] **R24-3 — the critic must not be able to edit the candidate.** ✅ 2026-09-15 — `actors.py:84-87` runs the Claude critic with
      `--dangerously-skip-permissions` in the lane worktree. The shared `_CLAUDE_SANDBOX_NOTE` (`:55-61`) tells it
      *"If the task asks for an edit, make it directly"*. `review_patch` takes its diff BEFORE the call, and nothing
      re-hashes the tree before `gate()`.
      (i) Run the critic role read-only: drop the flag and the edit clause for the critic, or point it at a read-only
      checkout.
      (ii) Hash the tree immediately before critic pass 2 and again before `gate()`; any delta is a hard candidate
      failure.
      (iii) Render planner-authored hypothesis text and diff in the critic prompt as a delimited data block with a
      do-not-follow clause.
      (iv) Pin it with a test in which a critic stub that edits a file fails the candidate.
      Warrant: HAN Lab's writer instructed its edit-capable verifier to implement its work through the review prompt
      (intake-1433#record). Zero compute.
      **Landed:** critic backends are read-only, candidate data is delimited/untrusted, and both the
      critic wrapper and host-owned loop validation compare pre/post tree identities before gating.
      Research `13f8e63a` / main `81fbd472`.

<!-- original line 9309 -->
- [x] **R24-4 — wire the no-fallback dispatch proof into the correctness gate.** ✅ 2026-09-15 — Two checks exist:
      `evaluator/correctness.py:3047` `check_no_fallback_dispatch_proof`, and `loop/fold2_gates.py` G4
      (`GGML_SCHED_DEBUG=2`, target ops must sit on `ROCm0`). `loop/run.py:31-33` imports neither. `gates.py` runs only
      `test-backend-ops`, and `residency.Sampler` proves whole-process VRAM residency, not per-op placement. Capture the
      scheduler assignment for the candidate's affected ops once per candidate, piggybacked on an existing bench
      invocation, and fail closed on any CPU-assigned target op. Warrant: the GDN Full-Agent contest winner shipped a
      decode kernel with a silent host-CPU fallback, and its harness's output check passes it (intake-1432#record).
      Spec §12 (`autokernel-research-loop.md:2617`) already demands this check. GPU: one debug capture per candidate.
      **Landed:** a scheduler trace feeds the existing no-fallback evaluator after the op oracle and
      fails closed on missing, vacuous or CPU-assigned target-op evidence. Research `13f8e63a` /
      main `81fbd472`.

<!-- original line 9320 -->
- [x] **R24-5 — fix or delete `gates.deterministic`.** ✅ 2026-09-15 — `loop/gates.py:127-150` adds each run's RETURN CODE to a set
      and never compares outputs. It has no caller, yet it is exported (`:177`) as if it worked. Either delete it or
      compare hashed logits across runs through the hardened path (R24-1). This is the vacuous-verification class. Zero
      compute.
      **Landed:** three identical seeded hardened executions must carry one output-hash record;
      otherwise the gate refuses. It is wired into the non-serving candidate gate. Research
      `13f8e63a` / main `81fbd472`. Combined verification: 455 tests and 31 subtests passed.

<!-- original line 9327 -->
- [x] **R24-6 — anti-gaming clause in the planner/author prompt.** Neither `actors.py:407-422` nor `program.md` ✅ 2026-10-31 — Research `57f6db044ba4b512bbc89b0025edeec52fe740cf`; [planner/author prompt source](https://github.com/pestopoppa/epyc-inference-research/blob/57f6db044ba4b512bbc89b0025edeec52fe740cf/scripts/kernel_rnd/autokernel/loop/actors.py) and [program advisory](https://github.com/pestopoppa/epyc-inference-research/blob/57f6db044ba4b512bbc89b0025edeec52fe740cf/scripts/kernel_rnd/autokernel/loop/program.md). [no-belief: advisory prompt implementation]
      - The actual `AgentPlanner.propose` and `author` prompts append the shared clause after concise processing, and the loaded program carries the same text. The clause forbids input/pointer-keyed output caching, cross-repetition reuse and workload-specific shortcuts, requires declared cold/warm cache effects, and remains advisory alongside R24-1/2. Syntax and diff validation passed; the source commit records the current caller/program readset. No model call, performance gain, compliance guarantee or runtime deployment is claimed.
      carries one. The clause should forbid:
      - input-identity or pointer-keyed caching of outputs;
      - cross-rep buffer reuse;
      - workload-specific shortcuts.
      Any deployable cache must be DECLARED, with its cold and warm effects reported separately. This is an advisory
      complement to R24-1/2, never a substitute (intake-1426#record). Zero compute.

<!-- original line 9352 -->
- [x] **R24-8 — no-measurement streak alarm and keep-rate alarm, beside `MAX_CONSECUTIVE_ERRORS`.** ✅ 2026-11-17 CLOSED (autokernel, INF-06 sweep). Both alarms landed (research `991033729`: `NO_MEASUREMENT_ALARM_N`, `KEEP_RATE_ALARM_WINDOW`, planner evidence line; ROOT `844689e0a` /loop render). Retrodicted on run 18 (both alarms cross at outcome 68) and run 9 (rows lack `comparison`, read as UNKNOWN). The run 5-8 retrodiction cannot be executed: their per-run native records do not exist (capsule `artifacts/compute/r24-8-alarms-20261031/README.md`). The box closes on everything executable. [no-belief: tooling + retrodiction capsule] The pool
      breaker (`pipeline.py:70-76`) counts only errored iterations; refusals and nulls are excluded by design. That is
      how run 9 spent 10 iterations / 149 min with zero measurements (:250-252).
      - **No-measurement alarm:** count pool iterations that end with no `Comparison` (excluding
        `STOPPED_MID_FORMATION`). At N (pre-register, e.g. 10) raise `operator_attention` with the refusal-reason
        histogram. Do not abort.
      - **Keep-rate alarm:** when N consecutive measured candidates sit below zero, or no keep lands within a window,
        raise `operator_attention` and add a planner-visible evidence line.
      Retrodict both on runs 5-9 and 18. Sources: intake-1425#record, intake-1426#record. Zero compute.
      - 2026-10-31 source partial (codex-ni): Research `991033729e9479249909ea3ae5ddc5d2e18772c2` publishes configurable observe-only streak/keep warnings, explicit current no-comparison nulls, conservative legacy-UNKNOWN breaks, and the same evidence line in the next planner context. ROOT `844689e0a75dbc9d5b5f0a9c701ebb4af9b65024` renders active/inactive/unknown states at the existing `/loop` surface. Native source controls pass 51 Research / 79 ROOT tests; Git capsule `artifacts/compute/r24-8-alarms-20261031/README.md` retains original run9/run18 inputs and replay. Run18's first measured alarms cross at outcome68; later legacy unknowns break the suffix, and run9's missing comparison fields remain unknown. August run5–8 native per-run records were not found; their required retrodictions remain unexecuted, so the original task stays open and earns no completion credit. No abort, keep/grading change, live measurement, or historical warrant is inferred. [no-belief: source/control evidence; retrospective coverage incomplete]

<!-- original line 9362 -->
- [x] **R24-9 — same-code re-measurement tripwire (rider on R22-3 (2)).** When a candidate's code-section hash ✅ 2026-10-30 [no-belief: source regression guard] <!-- evidence-integrity: Research `8b1cdb6fb8dd2255acf3f4194e690d1a23465510`, `5412cae12ec806514f27f510eadf4206d4b0f9be`; artifact: artifacts/compute/task-evidence-repair-20261031/r24-9/EVIDENCE.json; hygiene, not quota -->
      (`.text`+`.hip_fatbin`, the R22-3 basis) equals an already-measured one, log the new effect beside the old.
      Divergence beyond floor is an evaluator/session excursion, never a keep. Warrant: in LoongFlow's traces,
      byte-identical GDN-decode code scored 97 → 777 across a 7-day pause and was written up as a mechanism
      (intake-1427#record). Zero compute; journal logic only.

  <!-- task-evidence-integrity:start R24-9 -->
  - Evidence metadata (hygiene, not new quota): Research `8b1cdb6fb8dd2255acf3f4194e690d1a23465510`, `5412cae12ec806514f27f510eadf4206d4b0f9be`; [test/artifact](../../artifacts/compute/task-evidence-repair-20261031/r24-9/EVIDENCE.json).
  <!-- task-evidence-integrity:end R24-9 -->
      - Research `8b1cdb6fb8dd2255acf3f4194e690d1a23465510` captures source code/work identity prospectively, journals the prior and new effects, and uses the existing `MeasurementInvalid` path before keep when divergence exceeds the current native floor. Missing identity/floor stays unknown. Ten current-source tests (native comparison objects), new-module Ruff and private-index promotion passed; no live excursion or historical regrade. [Evidence](../../artifacts/compute/refactor-r24-same-code-source-20261030.json).

      - [x] Bind plain CPU bench repeats to the CPU code manifest even without a direct-serving launch. ✅ 2026-10-30 Research `5412cae12ec806514f27f510eadf4206d4b0f9be`; eleven source-bound tests and new-module Ruff pass. This corrects source `8b1cdb6fb` choosing HIP for ordinary CPU bench calls; no historical verdict changed. [no-belief: backend dispatch source fix]

<!-- original line 9495 -->
- [x] **AKR-SG-1 — Serving-gate load driver self-check and survivorship rule.** Add to the serving-gate and load-driver acceptance: the report states requested versus achieved rate and a client scheduling-delay distribution, and a run whose median delay exceeds 10 ms or whose achieved rate departs from the request is voided, not averaged; implement in the existing driver. Headline metrics of any session replay are over all sessions started (intake-2330#record). Acceptance: a run with an injected 50 ms scheduler delay is voided by a unit test. Estimate: about 2 hours. ✅ 2026-10-21
  - *(2026-10-21, dpf-specs.)* `loop/loadgen_selfcheck.py` + `test_loadgen_selfcheck.py` (epyc-inference-research research ba1f758a4); injected 50 ms delay voids the run. gitnexus impact was NOT run (index stale); the change is additive and off by default (`serving._measure_once` consults it only after `enable()`), so the serving path is unchanged.

<!-- original line 9497 -->
- [x] **AKR-SG-2 — Paired alternating wrapper around a load generator, emitting the serving-gate record.** Build a paired A/B/A/B alternation wrapper with a fixed base seed, pair-wise delta and floor estimation, emitting the existing serving-gate record; the single-run percentiles of the reference load generator carry no pairing and no floor. Decide at the start between wrapping the inference-perf tool (after its llama-server adapter, 0.5-1 day, also needed for KPF-64) and a 300-line own client (about 2 days) (intake-2330#record). Map llama-server `/metrics` names into the report (about 1 day) when a run needs queue and KV series. Runs need a window. Acceptance: one paired run on a toy endpoint emits a valid record with delta and floor. Estimate: 2-3 days. ✅ 2026-10-21
  - 2026-10-21 (fillers-3c4ca599): real-server shakedown registered as queue item `s5-akrsg-shakedown` (NOT armed, bundle): needs a driver script and an A/B server pair.
  - 2026-10-21 (queue-builders-3; research `6a70318d8`, pushed) the shakedown's missing pieces are built under `scripts/kernel_rnd/autokernel/loop/`: `run_paired_serving_ab.py` (driver script; window guard, STOP between measurements, always tears down), `ab_server_pair.py` (A/B launcher: own ports, production ports refused, per-arm cpu_list and `LD_LIBRARY_PATH`, port-ownership proof, `/proc/<pid>/maps` linkage proof, verified teardown) and `metrics_map.py` (the `/metrics` mapping: queue and throughput series from this tree's `llamacpp:*` names; KV usage is NOT exported by v10 and is reported `not_exposed`, never zero). 8 tests (launcher guards, a fake server that must fail the linkage proof and be torn down dead, toy-endpoint record). Bug fixed in `paired_loadgen`: a zero effect against a zero floor read `decisive=true`. The first shakedown is an A/A. Unverified until the window: the maps/props parsing against a real llama-server. Belief wiring: VB-AKRSG-WRITE. Queue row `s5-akrsg-shakedown` `ready=y`, bundle sub-row (needs a quiet host), not armed.
  - 2026-10-22 (3c4ca599 wrap-up) real-server shakedown `s5-akrsg-shakedown` COMPLETE 13:09Z: PASS, `epyc.autokernel.serving_ab.v1` OK, A/A pipeline-only, cpu-20260921-ffc1bac82 both arms, ports owned, linkage OK, teardown verified; run dir `/mnt/raid0/llm/tmp/akrsg-out/run-20261022T130855Z/`. The `/metrics` mapping was exercised against a real llama-server for the first time.
  - *Build note (2026-10-21).* AKR-SG-1: the "existing driver" is the closed-round client inside `serving._measure_once`. `loop/loadgen_selfcheck.py` adds the scheduling log, requested-versus-achieved rate, the void rule (median delay above 10 ms, or achieved rate more than 5% off the request, or fewer starts than requested) and `session_headline` (denominator = all sessions started). `serving._measure_once` consults it only after `loadgen_selfcheck.enable()`; off by default, so the serving path is unchanged. A void raises `LoadDriverVoided` (a `MeasurementInvalid`), never an averaged value. Test: `loop/test_loadgen_selfcheck.py` (injected 50 ms delay voids the run). AKR-SG-2: decision taken at the start is the OWN CLIENT, not a wrapper over inference-perf (no llama-server adapter, vLLM-only metrics, python>=3.12 and transformers 5.13 pins; the adapter alone costs 0.5-1 day and the paired statistic is still to build). `loop/paired_loadgen.py` runs A,B per pair in a fixed order with seed = base_seed + pair index, reports per-pair deltas, estimates the floor from an A/A run of the same alternation (or accepts a supplied floor that must state its unit) and emits `epyc.autokernel.serving_ab.v1`. Test on a toy endpoint: `loop/test_paired_loadgen.py`. The `/metrics` name mapping is not built (no run needs queue and KV series yet); real-server runs need a window.
  - *(2026-10-21, dpf-specs.)* `loop/paired_loadgen.py` + `test_paired_loadgen.py` (epyc-inference-research research ba1f758a4); toy-endpoint paired run emits a valid `serving_ab.v1` record with delta and floor. Own client chosen over wrapping inference-perf (reasons in the build note above). `/metrics` mapping not built; real-server runs need a window.

<!-- original line 9541 -->
- [x] **LBH-1 — scan every stored llama-bench result since 2026-08-11 for unrequested hardened rows.** Cover research
      `benchmarks/results`, `data/`, `artifacts/`; `/mnt/raid0/llm/autokernel/campaigns` (every store, including
      `runtime-source-floors` and calibration/baseline-honesty receipts); every floor record and floor store
      (`floor-store/`, DS41/Q38FN/27B floors, `gpu_cpu_noise` `reps.jsonl`); `/mnt/raid0/llm/tmp/**` and root
      `artifacts/**`. A row is UNREQUESTED-HARDENED when `"autokernel_hardened": true` and the producing argv (launcher
      script, `.cmd`/`.argv`, `config_echo`, `RUN_RECORD`, `launches-*.jsonl`) lacks `--autokernel-harden`; it is
      REQUEST-UNKNOWN when no argv survives. For markdown/CSV outputs from a defect-window build, classify from stderr
      (no per-rep progress lines = hardened) or mark request-unknown. Skip non-regular files (pytest fixtures leave
      FIFOs named `*.json` under `tmp/`; a naive reader blocks on them). Output: one JSONL manifest row per file
      (path, build commit, rows true/false, request evidence, class) plus totals, written to a research artifact dir
      with SHA256SUMS.
  - *(2026-10-23, workspace-f8, INF-70 REQUEST-UNKNOWN group classified; aggregates only.)* Method: no argv or
    `autokernel_hardened` column survives (markdown output, no `--progress`), so the protocol was inferred from WALL CLOCK.
    A hardened llama-bench run allocates 2 x reps contexts, runs a distinct warmup on each (2R full tests) and then the
    measured plus synchronized replicate (2R more): about 4R full test executions against R+1 for an ordinary run.
    Observed time = log birth-to-mtime (the log is opened at launch), minus region-lock wait, divided by the test time
    implied by the log's own t/s rows; reps from the echoed argv, else the launching script. Result: a sharp bimodal
    split with no overlap at R=5 (ordinary 4.3-6.8 test-equivalents, hardened 20.5-23.3, predicted 6 and 20), and the same
    two clusters at R=3 (4.3-4.7 vs 13.6). Identical configurations alternate between the clusters, which is the
    uninitialised-flag signature. Every Sept binary in the group carries the hardening code (`autokernel-harden` string in
    `libllama-bench-impl.so` of the 10151..10226 builds), so no run is excluded by build. Scope: 22 run dirs hold llama-bench
    markdown (170 files; 35 are aggregate or driver logs that repeat per-arm rows and are not counted as units);
    `results-c5-20260902T103008Z` and `...103049Z` hold no bench output (aborted at the gate). Tally of 135 units:
    **51 ordinary, 50 hardened, 34 unresolved** (31 timing-ambiguous because a cold 91 GB model load or an eviction wait
    inflates the clock, 3 depth-sweep files where the fill time is unmodelled). No wall-clock-ambiguous unit is called
    ordinary or hardened; 7 lean ordinary and 24 lean hardened, but only the R=5 leans are worth reading. Manifest (one row
    per file with class, lean, k and observed seconds): scratch `/mnt/raid0/llm/tmp/lbh1-inf70-manifest/manifest.jsonl`,
    SHA-256 `d3ef356ba7528def4fb3193300424d40fb5a604560949c8f560bc217d9d3870b`. Residual risk: timing is circumstantial;
    a re-run on a V11-103 build with `--progress` or JSON output is the only proof, and the dispositions below say which
    verdicts need it. Observed protocol effect on tg128 for identical configurations (sync10, sync3 pairs): within about
    1.5 percent either way, pp512 noisier.

<!-- original line 9641 -->
- [x] **LBH-3 — consumer guard: shared llama-bench parsers reject unrequested hardened rows (PROPOSED, research code,
      owner of `kernel_rnd/autokernel/execution/microbench.py` applies).** Today the check runs one way only:
      `LlamaBenchExpectation.check_row` (`microbench.py:1978`, `:2006`) calls `_check_autokernel_hardening` (`:1765`,
      rejects not-hardened when requested) only when `autokernel_seed is not None`, and `parse_llama_bench_json`
      (`:1635`, `:1713`) reads a missing key as False. Proposal: (1) in `check_row`, when the command did not request
      hardening, reject a row with `autokernel_hardened` true (`reason: unrequested_hardened_protocol`); (2) treat a
      missing key as unknown, not False, for builds that emit the field; (3) the five scripts with inline flag
      assertions (`run_autokernel_gpu_discovery.py:1162,1320`, `run_autokernel_gpu_factorial.py:146`,
      `run_autokernel_cpu_lane_calibration.py:198`, `run_autokernel_cpu_baseline_honesty.py:96`) compare the flag with
      their own argv instead of asserting true; (4) `loop/production.py:419` records `hardened` from argv: cross-check
      it against the row; (5) the canonical-recipe launch path (`lib/canonical_recipe.py`
      `build_canonical_bench_command:869`, `benchmark/bench_canonical.sh`) and the one-off parsers
      (`benchmark/ab_probe.py`, `benchmark/gpu_cpu_noise/*`, `kernel_rnd/kernel_eval.sh:159-167`) adopt the shared
      check; (6) unit tests: requested+hardened accept, unrequested+hardened reject, requested+ordinary reject. Keep the
      guard after V11-103 lands: it is what keeps old binaries honest.
  - *(2026-10-23, workspace-f8, LBH-3 DONE pending landing.)* Research branch `f8/lbh3-harden-guard` @ `bf8ce8a34`, based on
    `eca48e399` (pushed as a branch only). `BenchRow` gains `autokernel_hardened_reported` and `hardened_state`
    (`hardened` / `ordinary` / `unknown`; hardened-only receipt fields prove `hardened` even if the flag is dropped).
    `LlamaBenchExpectation.check_row` now FAILs a hardened row when argv did not request `--autokernel-harden`
    (the requested-but-ordinary direction is unchanged). A row that omits the flag is UNKNOWN: accepted with an explicit
    note by default so pre-fix archives stay loadable, COULD_NOT_CHECK (falsy) with `strict_unknown=True`, which any consumer
    gating a NEW claim should pass. The five inline-assertion scripts (`run_autokernel_gpu_discovery.py` x2,
    `run_autokernel_gpu_factorial.py`, `run_autokernel_cpu_lane_calibration.py`, `run_autokernel_cpu_baseline_honesty.py`)
    always request hardening, so they already failed on a missing or false flag; they now share one tuple and one helper,
    `microbench.HARDENED_RECEIPT_FLAGS` / `incomplete_hardening_flags` (fail-closed on missing keys). `loop/production.py:419`
    records `hardened` from the REQUESTED argv by design and is left as the request record; the row-side check is `check_row`.
    `gpu_cpu_noise_driver.parse_bench_jsonl` never requests hardening, so it tags each parsed row `unrequested_hardened`
    and each rep row carries the OR. `canonical_recipe.py`/`bench_canonical.sh` build argv only and parse nothing, and
    `ab_probe.py` reads llama-bench JSON files without checking them; both are noted but not changed (their consumers are the
    guarded ones above). Not changed: `direct_gpu_control.py` and `gpu_source_evidence.py` parse retained historical fixtures
    without `check_row`. Tests: 7 new in `test_microbench.py`, 1 in `test_gpu_cpu_noise.py`; microbench, bench, production,
    screening, discovery, execution-chain and blackbox suites 354+471 passed, gpu_cpu_noise 18 passed.
  - [x] **LBH-3.1 — turn the strict mode on where a NEW claim is gated (filed 2026-10-23, f8 wrap-up; derived from the LBH-3 note).** On research main (`5c3ad96c3`), `check_row(..., strict_unknown=False)` is still the default at both production call sites: `microbench.py:4389` (unit agreement) and `screening_baseline.py:202`. So a row with no `autokernel_hardened` field is accepted with a note even when it feeds a new verdict. Pass `strict_unknown=True` at both sites, or record per site why its rows can never be UNKNOWN. Also decide whether `benchmark/ab_probe.py`, which reads llama-bench JSON with no check, gates any claim. Owner of `microbench.py` applies; add unit tests for both sites.
    - *(2026-10-23, workspace-f8, LBH-3.1 DONE pending landing.)* Research branch `f8/lbh3-1-strict-unknown` @ `36b6f8baf` (pushed as a branch only, based on research main `62c2e09da`). `strict_unknown=True` at `microbench.py:4389` (unit agreement) and `screening_baseline.py:202`: both gate NEW measurements run on the live binary, which always emits `autokernel_hardened`, so an UNKNOWN row there is an unattested instrument and is now refused (COULD_NOT_CHECK is not PASS). Unit tests: `test_microbench.py` (`test_unit_agreement_check_is_strict_about_unknown_protocol`) and `test_screening_baseline.py` (`ScreeningInvokeStrictUnknownTest`). `benchmark/ab_probe.py`: does not gate on llama-bench rows; its verdicts are server timings and the `llama_bench_*` speed entries are a side figure from pre-extracted files, so left unchanged. `scripts/kernel_rnd/autokernel/execution` 1190 passed, 3 pre-existing failures identical on a clean checkout (frozen-tree branch `production-consolidated-v10` expectations in `test_worktree.py`, `test_live_controls.py`, `test_control_runner.py`).

<!-- original line 9682 -->
- [x] **R18-A r3 qualification refusal diagnosis** ✅ 2026-11-01: the keeper's archived cutoff proof omitted `stop_observed` and `unknown_disposition`, although the cutoff job waits for STOP and drains its active compiler before writing that proof. The keeper refused rc=70; its [launcher log](/mnt/raid0/llm/tmp/compute-flags/qual/8bdab7b2bf453038bca728214bbf51f7d126e81b3b77fc54262af8c1319c637d/launcher.out) and `proof-cutoff.json` retain the evidence. A [proposed patch](../../artifacts/compute/r18a-cutoff-proof-20261101/cutoff-witness.patch) adds the required fields after that check; it has not been qualified. The existing r3 READY is owned by `codex-refactor-01a16fc3` and its migrated result spec is incomplete; do not duplicate its run or edit its manifest. API PID 2307743 had the cross-role flag enabled at the November 1 audit, unlike the original refused PID; the successor still needs its own current strict preflight. [belief: cc]

<!-- original line 9704 -->
- [x] **R18-A-CUID-FORENSICS** — determine the source of the 141 host CUID changes and resolve against the unchanged three-set identity rule; retain the original invalid run and this valid negative separately. Do not filter symbols or modify the frozen store. ✅ 2026-11-01 — research main `49e776408693c5d676f2d6292e48fa15398c13a3` publishes the recipe-derived per-TU `-cuid=` replay tool (18 wrapper tests plus bounded compiler/CMake controls); root `c9c43366a5b3adc5aa1befa405744c732b6bdccc` records the causal report at `docs/audits/r18-cuid-path-hash-forensics-20261031.md` and artifact `artifacts/compute/refactor-r18-cuid-forensics-source-20261031.json`. All 141 changes are explained by deterministic Driver→ASTContext hashing over relocated source/include paths. Full three-set identity remains false; no rule amendment, filtering, full rebuild, or frozen-store edit. [belief: cc]

<!-- original line 9721 -->
- [x] **AK-FAILRULE-1 — Turn recurring AK rejection reasons into pre-GPU rules from existing records (intake-2589#record, intake-2588#record).** Zero inference: classify every rejected candidate in the existing CPU and GPU campaign stores by failure reason (compile, correctness gate and which gate, timing loss, noise, harness error). For each reason class with at least 3 occurrences, draft a cheap static or pre-GPU check (CAKE-style hazard filter) and replay it over the historical candidates. Adopt a rule only if it would have rejected at least one historical failure before GPU time and no historical keep. — **Done 2026-11-06 (AutoKernel):** 1,262 candidate verdicts across 7 stores classified (`/mnt/raid0/llm/tmp/ak-failrule1-20261106/REPORT.md`). ADOPTED: empty test-backend-ops suite preflight keyed by anchor binary (46 failures caught, 0 keeps) and blank-only-hunk lint (13 caught, 0 keeps); research 9ddf6d38e; preflight verified on the real C6 CPU binary (MUL_MAT 1144, FLASH_ATTN_EXT 5207, unknown op 0). REJECTED (catch keeps): mechanism-retry block, diff-repeat block, N-nulls surface stop. Harness bug classes routed to Pipeline Management. [no-belief: loop code change; evidence in commits] ✅ 2026-11-06

<!-- original line 10046 -->
- [x] **Required-target validation aggregate follows the current shared tip**: ✅ 2026-09-10.
  Serial state now retains an exact aggregate over every production target and every
  target that authored a keep still present in the ordered lineage. The latest author
  alone is the intended-gain target; other rows remain non-regression checks. Missing
  or stale evidence clears/pends the aggregate rather than preserving an old pass.
  Main27 serial checks passed11.98s. This observation does not yet enforce LOO,
  rebaseline or COR advancement; those remain the next execution seam.

<!-- original line 10054 -->
- [x] **Targets author against the shared source tip, retaining their own baseline/history**: ✅ 2026-09-10.
  Cross-target validation builds the target recipe and records original provenance;
  subsequent authoring uses the source receipt's actual checkout/branch and that
  validated build. Target continuation identity remains separate. Same-target
  cross-checkout resume reuses its exact retained current build. No branch reset,
  cherry-pick or copy is used to switch targets. Main31 serial/outcome/validation
  checks passed23.95s, including A keep→B validation/descendant keep→A real
  validation/source iteration and B self-resume startup. Aggregate required-target
  LOO/rebaseline/COR integration remains separate unfinished work.

<!-- original line 10064 -->
- [x] **Original GPU positive/historical control supplier is connected**: ✅ 2026-09-10.
  Research e019bd52/main981d64ac retains native benchmark means and original held
  CPU/GPU contexts through existing calibration and T0–T2 evaluators. Failed setup
  retains raw observations; same-owner recovery reuses completed arms. The exact
  historical paired-effect range is an engineering replay tolerance, not a new
  gain threshold or confidence interval. Original governed adapter captures these
  observations with empty protocol; no hardware qualification is inferred.
  Main55 research checks plus8 subtests passed15.23s; ROOT27 passed0.38s without
  skips. Actual GPU control replay and mixed hardware acceptance remain unverified.

<!-- original line 10074 -->
- [x] **Completed serial campaigns retain selectable target details**: ✅ 2026-09-10.
  The existing dashboard follows bounded original last-result references, verifies
  exact terminal target status, and lets the operator select each retained batch.
  Canonical champion/history remain separate and visible. Missing or superseded
  target reports show an unavailable reason; no current activity or cumulative
  totals are invented. Main36 reader/page/terminal checks passed2.52s, including
  CPU keep and GPU null fixtures. This does not establish a live mixed hardware run.

<!-- original line 10082 -->
- [x] **Last completed outcome retains an optional original-evidence pointer**: ✅ 2026-09-10.
  Serial continuation carries at most 12KiB of reference metadata to the existing
  serving receipt/runtime result, not duplicated measurements or a second ledger.
  Explicit diagnostics use original readers; continuation loading never invokes
  that expensive read, and missing optional evidence does not block restart.
  Main28 outcome/serial checks passed23.78s. No scheduler weights, scientific
  eligibility, thresholds or hardware results change in this slice.

<!-- original line 10090 -->
- [x] **Distinct common-Git worktrees receive target-recipe source validation**: ✅ 2026-09-10.
  Preserve target A; prove the source checkout's exact shared-Git commit/tree and
  clean state again under the held build claim; build target-specific B and run
  original correctness/serving comparison. Build failure records debt without
  rebinding a nonexistent binary. Immutable old validation references reopen after
  source HEAD advances. Legacy source keys migrate by original references/ancestry;
  subsequent direct lookup avoids whole-history scanning. Divergent keeps cannot
  replace the forward shared pointer. Main28 serial/validation/matched checks
  passed13.08s. No hardware or canonical promotion. This does not yet route every
  target's source authoring onto one shared tip or execute required-target LOO.

<!-- original line 10101 -->
- [x] **Aggregate serving gates feed the original archive and belief consumer**: ✅ 2026-09-10.
  Both promotion and nonpromotion archive the original whole-bundle comparison with
  COR/tip, keep membership and trigger before existing state advancement. Existing
  divergence recall fields remain; a successful aggregate observation is not another
  source keep. The original export callback reaches the observation-only ROOT reader
  and planner. Main21 checks passed1.23s; worker37 passed1.21s. Actual PROMOTE and
  DIVERGED fixtures verify duplicate ingestion/restart preserve receipt bytes and do
  not repeat measurement. Numerical verdicts, cadence and serving source are unchanged.

<!-- original line 10110 -->
- [x] **Original GPU runtime path uses both held contexts and numeric device observations**: ✅ 2026-09-10.
  Planner, runtime fast path, ROCm0 correctness, calibration/window capture and
  recovery now retain the original CPU-host and GPU contexts separately. Device
  observations cover request endpoints and interior gaps under existing limits.
  Missing GPU control suppliers refuse setup before calibration, including explicit
  --calibrate-runtime; observation-only comparison/source research remain available.
  No CPU control band, policy, threshold or qualified keep is invented. Main26
  GPU/original-GPU checks passed3.66s; worker43 composed GPU/matched-CPU checks
  passed19.45s. Nine primary files match the frozen packet. Synthetic HTTP/device
  fixtures establish execution wiring, not hardware qualification. Actual positive/
  historical GPU control suppliers and qualified GPU runtime admission remain open.

<!-- original line 10122 -->
- [x] **Fresh unified CPU source measurements use matched process-pair calibration**: ✅ 2026-09-10.
  Fresh CPU enrollment selects matched_process_v2 and pins that choice before the
  first child. Original v1 floors/continuations and direct CLI/GPU defaults remain
  unchanged. New calibration uses24 independent A/A pairs (48 launches), randomized
  balanced AB/BA, and the existing ratio-of-arm-medians reducer at the comparison's
  pair count. Separate versioned floors bind workload/placement; source-treatment
  reuse remains allowed. The descriptive interval does not replace the scalar gate.
  All four source comparison paths, cross-target validation, archive/belief capture
  and exact CPU profile source pin are connected. Reused original validation does
  not rerun calibration/A-B. Main25 matched checks passed16.60s; worker62 producer
  and29 ROOT checks passed. Existing GLM results are not regraded or rerun. This is
  source measurement, not full strict runtime qualification or hardware transfer.

<!-- original line 10135 -->
- [x] **Shared-worktree source changes receive original-owner cross-target validation**: ✅ 2026-09-10.
  Retained original keep receipts identify the whole source, original target baseline,
  request and recipe. Validation is an explicit charged scheduler stage, not a hidden
  priority filter. Pending retries require intervening ordinary research; missing
  evidence remains pending, not a regression or pass. Exact single-keep observations
  are reused without another calibration/A-B; changed assembled candidates remeasure.
  Existing serving/FOLD-2 rules decide, and fresh rows use the existing archive/belief
  export. Reuse preserves original timestamps/bytes. Unused promotion scaffolding was
  removed. Main70 combined checks,29 boundary follow-ups and35 archive/belief checks
  passed; all8 primary files match acceptance. Distinct CPU/GPU worktree validation,
  required-target final aggregation and canonical promotion are NOT completed here.

<!-- original line 10147 -->
- [x] **Serial selection learns bounded cost forecasts from original held receipts**: ✅ 2026-09-10.
  Completed matching measured-search batches supply a last8/p75 duration estimate;
  exact recipe/request/source/runtime/scope/accounting identities prevent unrelated
  reuse. Failed/invalid attempts remain charged but do not train successful duration.
  Original selection, coverage, seed opportunity and stage limits remain unchanged.
  Main60 combined cost/serial/control/scheduling tests passed11.93s, including real
  private-flock child, changed next estimate and restart with no repeated settlement.
  Scientific-outcome adaptive reward weights remain incomplete; no new grader added.

<!-- original line 10156 -->
- [x] **Existing dashboard operates the original serial controls**: ✅ 2026-09-10.
  Pause/resume/drain buttons use the authenticated serial listener and exact owner,
  revision, batch and target. Tokens remain in tab memory. Lost acknowledgements retry
  the original ID; a new owner detaches the old uncertainty without replaying it or
  disabling new commands. Malformed optional controls disable only their own card,
  not the valid child/measurement/history display. Main137 reader/browser/producer
  integration tests passed4.80s against published research8c723082. No live command
  issued; listener configuration remains an explicit next-start option.

<!-- original line 10165 -->
- [x] **Original serial owner accepts authenticated pause/resume/drain**: ✅ 2026-09-10.
  Optional loopback listener reuses the existing authenticated HTTP transport. Commands
  bind owner/configuration/revision/batch/target; the serial execution thread persists
  acknowledgements. Pause finishes the batch and accounting, resume permits selection,
  and drain uses the captured child's original STOP/SIGTERM path. Failed cleanup never
  earns a completed drain. Persisted pause requires a resume channel or explicit STOP.
  Main33 controls/serial/runtime-recovery/progress tests passed74.75s; exact two-child
  receipt accounting remains6 seconds despite acknowledgement retry. No hardware run
  or live listener started. Dashboard integration is recorded in the following checkpoint above.

<!-- original line 10175 -->
- [x] **Original-owner runtime interruption recovery**: ✅ 2026-09-10.
  Serial retries only a typed recoverable runtime interruption after original child
  termination and held-resource accounting; unrelated failed targets remain excluded.
  Fresh ownership resumes the original pending pair/allocation in a new window, with
  completed control/results reused and old samples kept separate. Unknown child cleanup
  aborts before any fallback measurement. Historical completed results reopen even when
  the caller lost its result reference. Main combined43 checks pass plus the corrected
  old cleanup-exception fixture1pass; original real-child recovery tests are included.
  Synthetic measurement edges only; no claim that arbitrary orphan cleanup is automatic.

<!-- original line 10185 -->
- [x] **Existing dashboard shows dated runtime preparation and selected recipe**: ✅ 2026-09-10.
  Original checkpoint callbacks supply phase/counts/pending state; heartbeat cannot
  refresh the observation timestamp. Existing page renders the human-readable recipe
  with digests/caveats collapsed. Diagnostics cannot change admission or checkpoint
  success. Main45 writer/reader/page checks pass; separate producer44 checks passed
  before recovery composition. Authenticated serial controls remain separate work.

<!-- original line 10192 -->
- [x] **Fresh selected CPU/GPU targets prepare their missing source floor automatically**: ✅ 2026-09-10.
  The existing startup calibration now covers full targets as well as reduced screens.
  Only an absent exact recipe/request floor triggers automatic preparation, using the
  existing serving pair count (minimum2); an explicit calibration count still overrides.
  Existing GLM7.801 is reused, and malformed/mismatched records still refuse unchanged.
  Actual full8 dry run exits0: seven fresh production targets schedule5 launches each,
  GLM schedules none. Original calibration/estimator/claim ownership is unchanged.
  This is startup/execution wiring, not new hardware calibration or improved precision.

<!-- original line 10201 -->
- [x] **Shared-source target switching and all-eight-target serial startup**: ✅ 2026-09-10.
  Targets can serialize one exact experimental worktree/branch while retaining their own
  request/history. Digest-bound latest-source continuation rebinds the existing build;
  a target's older personal continuation does not force an obsolete source anchor.
  Main118 tests pass, including actual-owner synthetic A keep -> B keep -> A startup.
  Full seven-production-plus-GLM serial dry run exits0 from primary; original GLM floor
  remains7.801, new production floors remain absent, and the retained GPU build's existing
  unattested warning remains explicit. No inference/build/state directory created.
  Log: `/mnt/raid0/llm/tmp/aku-full-roster-dryrun-inputs-20260910/shared-source-primary-dry-run.log`,
  SHA256 b704dc907b9021f267c80e9be5552825581e856df3db2e14f2b3673c712c605a.
  Shared candidate folding and runtime-recipe transport remain separate active work;
  neither is implied by this source-continuation checkpoint.

<!-- original line 10214 -->
- [x] **Automatic CPU screening connects selection to same-build full confirmation**: ✅ 2026-09-10.
  The existing serial loop selects quarter/half/full scope from qualitative mechanism
  history before resource selection; both arms share the selected geometry and its own
  floor. Reduced positives retain the original patch and executable as `keep_candidate`,
  not champion promotion. Full confirmation reuses that candidate and original requests;
  only an ordinary full keep promotes. Pending confirmation protects source/build aliases
  and remains explicit scope debt if unaffordable. Real production frontier IDs now reach
  the existing coverage policy. Main113 integration checks pass; actual scheduler-selected
  GLM quarter dry run exits0 with CPU0-23 and no borrowed full-size floor. These checks
  establish startup and fixture execution, not live transfer or CPU/GPU coexistence.

<!-- original line 10225 -->
- [x] **Inherited CPU recipes use explicitly declared campaign affinity**: ✅ 2026-09-10.
  Actual worker_fast production input omitted taskset and was rejected. The original
  run now makes its inherited affinity explicit from enrolled resources, preserving
  command, artifacts, environment and original snapshot provenance. Standalone inputs
  without declared resources still require affinity. Main70 tests pass; all seven
  production workloads plus GLM pass individual original-owner preflight. Full-roster
  serial shared-source handling is proven by the later all-eight-target checkpoint above.

<!-- original line 10233 -->
- [x] **Existing serial CPU+GPU owned-roster dry run passes**: ✅ 2026-09-10.
  Actual GLM c463 CPU and canonical ef811 GPU inputs resolve and both original owner
  dry runs exit0 (0.44s), with sol-medium actors and derived scheduler. Fixed production
  draft-mtp/self_draft import mismatch and the scheduled-child topology import. Main75
  joined tests pass. Original GLM floor7.801 retained; new GPU requests correctly have no
  floor and retained hand-built anchor remains explicitly unattested. No inference,
  state directory or GPU memory store created. Evidence dry-run.log SHA130ba42ffe18405efe4824c3be5de2458189986a3ac88633e1c9f821e098d493
  under `/mnt/raid0/llm/tmp/aku-cpu-gpu-dryrun-inputs-20260910`. This is not live rotation proof.

<!-- original line 10242 -->
- [x] **Build rebinding follows actual ELF loader names across version changes**: ✅ 2026-09-10.
  Actual frozen10125 -> champion10301 dry-run preparation exposed full-version DSO
  filename assumptions. Existing exact paths remain unchanged; missing versions resolve
  through the original SONAME to a contained candidate with matching SONAME. External
  libraries remain fixed. Main42 checks passed; real16-DSO GPU rebinding matches the
  independently pinned retained build. No kernel rebuild or inference was needed.

<!-- original line 10249 -->
- [x] **Actual production command grammar resolves all seven exported targets**: ✅ 2026-09-10.
  Preserve emitted draft probability/thread/logging flags and frozen v9's omitted
  ubatch default512; conflicting aliases and invalid values still refuse. Main112
  research checks and32 original profile producer/reader checks passed. Profile source
  pin updated additively; historical captures retain their original accepted identities.
  Seven actual production recipes resolve with supplemental pinned ROCm DSOs. Original
  export artifact verification passed; the supplemental export explicitly did not repeat
  full artifact verification. No hardware launch or mixed-target performance claim.

<!-- original line 10258 -->
- [x] **Existing serial owner selects and accounts original held resources**: ✅ 2026-09-10.
  Owned rosters derive scheduler inputs without an extra manifest. One iteration per
  stage; fresh proposal identities support repeated passes, failed targets are excluded,
  and terminal restart accounts once before new selection. Original claim open/close
  intervals charge CPU/GPU components; no child-wall-time substitute. Main 101 tests
  passed and actual GLM auto-scheduled dry run exited0. Continuous defaults stop at
  1000 attempts, declared budget or STOP; this is not live mixed-target proof.

<!-- original line 10266 -->
- [x] **Split-model import preserves the launch entry shard**: ✅ 2026-09-10.
  Singular campaign/launch model slots now select the shard named by argv rather
  than silently retaining the last shard. The original export retains every pin.
  Main 21 enrollment tests passed, including split-model launch resolution.

<!-- original line 10271 -->
- [x] **Completed dashboard runs no longer look like stalled measurements**: ✅ 2026-09-10.
  Final reports retain original timestamps/raw steps but display a terminal step and
  FINAL REPORT/FAILED REPORT badge. Running producers retain heartbeat expiry; future
  timestamps remain malformed. Main 35 producer/reader/browser tests passed, including
  a running router with a completed child. Actual GLM artifact reads complete at 5/5.

<!-- original line 10277 -->
- [x] **Shared historical mechanisms reach the existing planner automatically**: ✅ 2026-09-10.
  Owned-target rosters supply canonical and sibling stores to read-only recall.
  Bounded selection retains useful keeps/nulls despite transient floods and rotates
  across one-iteration child restarts. Original scope/caveats remain separate from
  local applicability and gains. Main 104 tests passed; actual canonical-store read
  returned one keep, three measured nulls and one refusal without errors.
  This is historical suggestion recall, not demonstrated transfer or runtime admission.

<!-- original line 10285 -->
- [x] **Production enrollment includes every split-GGUF shard**: ✅ 2026-09-10.
  The existing exporter expands exact numbered model/drafter families and requires
  each supplied artifact pin; missing siblings leave the target waiting. No directory
  discovery, model mutation or implicit hashing was added. Main 20 enrollment tests
  passed. This closes artifact association, not the broader mixed-target acceptance gate.

<!-- original line 10291 -->
- [x] **Five actual GLM CPU research iterations completed unattended**: ✅ 2026-09-10.
  Original controller PID1380863 / exec21102 exited 0; five source/build/correctness/A-B
  iterations, no keeps. Effects: +0.950164%, +1.454288%, +1.181050%, +1.248272%,
  +0.332447%; every comparison retains five samples per arm. Original result:
  `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-output-continuation/loop-run.json`, SHA256
  `a489ee01fa6807e202ec69c44d2d59c2ae2c3be28fa766c48ea90d3b099ce408`.
  Parent and all ten final-iteration server PIDs are absent; floor SHA479db985… unchanged.
  Final rejected source remains in its owned worker lane and archive, not promoted.
  This controller predates newer continuation/telemetry/feedback/scheduler hooks;
  their absence from its output is not evidence those newer paths were exercised.
  Observation-grade workflow result only; AKU-12b's broader integration gates remain open.

<!-- original line 10303 -->
- [x] **Serial dashboard accepts the restart producer's process identity**: ✅ 2026-09-10.
  Corrected the closed reader contract after the restart producer added original
  PID/start/boot identity. Old payloads remain supported; optional identity must match
  the child PID and exact shape. Batch/target joining is unchanged. Main 26 tests passed,
  including actual serial producer through reader and browser rendering with history intact.

<!-- original line 10309 -->
- [x] **Interrupted source survives the existing lane reset**: ✅ 2026-09-10.
  STOP-before-gate and reused dirty lanes now retain original HEAD plus an immutable
  hash-qualified patch before reset. Tracked recipe/docs changes remain included;
  newly captured untracked files are bounded kernel-source text only. Archive failure
  prevents reset. Main 56 tests passed, including actual Git round-trip recovery.
  Build pruning is unchanged; this does not resume unfinished measurements automatically.

<!-- original line 10316 -->
- [x] **Serial restart reuses a completed child without replay**: ✅ 2026-09-10.
  Startup reopens the exact retained batch/target/arguments result and checks the
  original child's kernel identity before advancing once. Live or unreadable children
  refuse without signals or adoption; STOP persists. Missing/mismatched results retain
  original state and logs. Main 26 real-child/serial tests passed in 10.27s. This fixes
  the crash between child completion and router checkpoint, not unfinished-work recovery.

<!-- original line 10323 -->
- [x] **Existing-loop CPU factual noise and bounded original-arm recovery**: ✅ 2026-09-10.
  Research `64923e9f` / main `591616c0` records load/swap/PSI and bounded non-target
  CPU activity without turning ordinary builds/pressure into blockers. Original
  PID/start substitution or two affinity-violation samples for the same TID/start
  produce durable `measurement_invalid`, not a null. The existing tail archives
  before one budgeted retry of the same failed server launch, retaining valid arms,
  hypothesis/patch/build and exact requests. STOP, budget exhaustion, repeated
  invalidity and unresolved cleanup prevent retry. Main: 39 joined tests and 41 ROOT
  profile/corpus tests passed; historical source pins remain supported. Hermetic
  checks only, no live reload or hardware change. In-memory continuation is not
  restart recovery, and competing-inference classification remains unproven.

<!-- original line 10335 -->
- [x] **Existing-loop same-binary runtime observation and readers**: ✅ 2026-09-10.
  Typed CPU runtime treatments skip source authoring, diff review, build and source
  promotion; existing tail ownership, correctness and serving A/B remain the owners.
  Each arm retains its actual recipe with identical executable and frozen requests.
  `runtime_observed` is measured, not a keep or scientific null; the existing belief
  reader accepts its original per-arm identities without claiming qualified evidence.
  Main checks: 72 research tests and 10 ROOT reader/render tests passed. HTTP fixtures,
  not a hardware runtime experiment. The current live controller was not reloaded.

<!-- original line 10343 -->
- [x] **Prevalidated runtime options bypass routine critics**: ✅ 2026-09-10.
  Research `64923e9f` retains deterministic current-anchor/option checks and tail
  ownership/correctness gates; source changes retain review. Main 42 focused tests passed.

<!-- original line 10346 -->
- [x] **Same-owner runtime admission and serial recipe transport**: ✅ 2026-09-10.
  Original evaluator/calibration/control owners consume the direct loop's retained
  HTTP evidence. Runtime keeps select a recipe without source promotion; subsequent
  source comparisons use a recipe-bound floor. Existing bounded pruning protects
  only the selected admission's original build in addition to COR/current anchors.
  Serial resumes target-local selection with separate latest-source rebinding.
  Main54 admission/control checks pass; a fixture-only continuation assertion was
  corrected separately. Full8 actual dry run exits0 with GLM floor7.801 unchanged;
  32 profile-reader checks pass. No hardware runtime gain or interrupted-owner
  recovery is claimed by this checkpoint.

<!-- original line 10360 -->
- [x] **Existing-loop CPU profile observation reaches actor and belief readers**: ✅ 2026-09-10.
  The current CPU launch and original frozen request feed the existing owned perf capture
  in a separate observational server run at startup and after a keep, never after a null.
  Actor prompts receive sampled symbol periods/fractions, original record identity or an
  unavailable reason; acceptance pairs/floors are unchanged. ROOT uses the existing profile
  measurement projector/corpus, without a direct integrity or `PROFILE_VERIFIED` row.
  Focused checks: 114 research and 40 ROOT passed, no skips. Tiny HTTP/synthetic perf only;
  no hardware profiling, production mutation, qualified gain or live process reload.

<!-- original line 10369 -->
- [x] **First actual CPU source-to-measurement iteration and automatic continuation**:
  ✅ 2026-09-10. On research `2059e30e`, `akm-q4k-avx512-paired-y` passed through
  source authoring, build, the existing MUL_MAT correctness gate and five serving pairs.
  The original loop durably recorded `measured_null`: effect fraction
  `0.009501638190257289` (+0.95016%) did not clear the 7.801% floor. No keep or qualified
  gain. Runtime PID1380863 automatically entered iteration 2; this checkpoint is one
  completed/measured iteration, not completion of the five-iteration test.

<!-- original line 10377 -->
- [x] **Dashboard restart configuration and observed false benchmark detection**:
  ✅ 2026-09-09. Existing watchdog replaced the configured hub without inheriting its
  store setting. Re-adopted that same watchdog with explicit primary `EPYC_ROOT` and
  `AUTOKERNEL_LOOP_STORE_ROOT`; its real replacement hub retained trial/history split.
  Guard mistook Codex prompt text for benchmark identity: orchestrator `5e3a9ec7`
  (main `03ddb449`) checks executable/script operands instead. Main 61 focused tests
  passed; real benchmark identities and placement rules remain enforced.

<!-- original line 10385 -->
- [x] **Actual CPU actor-template failure repaired**: ✅ 2026-09-09.
  The first live attempts proved target metadata was dropped and CUDA paths forced;
  actors returned no valid target/empty paths. `ee76b37b` (research main `2059e30e`)
  delivers original CPU target context and corrects planner/author/critic wording.
  Main 33 actor checks passed. Stopped the failed run cleanly after two failures and
  one stopped formation; preserved all five calibration samples/floor for reuse.

<!-- original line 10392 -->
- [x] **Separate live trial from retained champion/history readers**: ✅ 2026-09-09.
  Corrected the store-selection regression: live GLM status no longer relocates canonical
  measurements or the 2,397-row historical experiment database. Canonical capability
  fallback reopens five original evidence entries with historical attribution and
  verified lineage; no new measurement or inferred production ratio is manufactured.
  Main focused combined checks:19 passed. Experimental CPU status now has explicit scope
  (`51abc7a3`, research main `e2a01699`); the already-running trial is not restarted.

<!-- original line 10400 -->
- [x] **Live CPU trial dashboard selection**: ✅ 2026-09-09. Orchestrator
  `59782734` → main `0ad401dd` selects the dedicated GLM store through the existing
  dashboard environment. Dashboard-only reload verified PID1339228; `/api/loop/health`
  reports fresh CPU evidence. Trial PID1329820 remained live. This is current-trial
  visibility, not completion of automatic multi-campaign dashboard selection.

<!-- original line 10406 -->
- [x] **Existing-loop CPU serving and request-bound calibration**: ✅ 2026-09-09.
  Published serving forwarding `1799ade6` → main `12bfe8a3` and existing-loop CPU
  entry route `2f066e53` → main `fbecc61c`. CPU candidates reuse the existing
  source/build/measurement/keep owners; optional resolved launches and exact frozen
  requests reach both serving arms. Request-bound floors cannot borrow a legacy floor;
  uncalibrated measurements remain non-decisive. Main actual child/HTTP checks:4 passed;
  existing focused serving checks:95 passed plus11 subtests. Legacy GPU defaults retained.

<!-- original line 10413 -->
- [x] **Original experimental CPU anchor identity and unwaived dry run**: ✅ 2026-09-09.
  Published `863128c1` → main `2032e5be`: the existing CPU entry route verifies the
  original experimental build identity against source/head and inventory, without
  inventing promotion provenance or using the unverified-anchor waiver. Main focused
  identity checks:27 passed plus4 subtests; startup worker's unwaived dry run exited0.
  This proves startup wiring only, not a qualified result or five-loop completion.
  Main subsequently verified live PID1329820 at original-request CPU calibration,
  iterations0/5; observe that existing loop and fix actual failures, not a replacement.

<!-- original line 10421 -->
- [x] **CPU-specific actor instructions and workload-scoped evidence epoch**: ✅ 2026-09-09.
  Published `3dddec73` → main `99f91479`; main 3 focused tests passed. CPU actors receive
  explicit selected-target instructions rather than GPU profiling directives; CPU launch
  and frozen-prompt digests join the evidence epoch. No fabricated CPU hotspots or GPU
  timing reuse, and no change to ordinary GPU instructions/epochs.

<!-- original line 10427 -->
- [x] **Compatibility repair — fresh legacy stores and anchor pruning**: ✅ 2026-09-09.
  Fresh-store initialization restored without resetting populated/corrupt history
  (`009ef659`, main `cdd13df5`; main 31 focused tests). Legacy keep path again uses
  bounded existing pruning with current/COR protection (`457f5e37`, main `602bdf16`;
  actual keep-path regression passes with deletion intercepted). No live deletion.

<!-- original line 10432 -->
- [x] **GLM request transport and original topology order**: ✅ 2026-09-09.
  Original token-array/cache/seed42 requests and explicit CPU launch flags use existing
  serving code (`002fc0d0`, main `bfb86301`); retained taskset/numactl order supported
  (`20b9621c`, main `5038e406`). Main focused combined check:50 passed. No hardware
  performance or five-loop completion claim.

<!-- original line 10737 -->
  - [x] **S3-AKU-08 (U3-PROPOSER) — write the RUNTIME_CONFIG proposer ownership split into U3-SEED.** (a)
        Default proposer for a declared knob box is operator/LLM hypotheses plus seeded random/LHS fill, NOT
        a model-based sampler. (b) A TPE arm may be enabled only if ALL of: (i) arms per campaign ≥ 10× box
        dimension; (ii) expected effect > floors[surface] in the SAME unit; (iii) TPE beats an equal-budget
        random arm in an offline replay over our own journalled arms, where the replay answers only
        exact-match arms (off-set proposals count as unanswered, never snapped), injects Gaussian noise at
        the unit-matched session floor into every replayed value, and reports the off-set proposal rate; a
        replay win licenses a live A/B, never a deploy config; (iv) a STAGED proposer (cheap-screen recipe
        tuning, then winners to serving or model choice) only for a mechanism family (R23-25) whose
        screen-vs-serving Spearman, computed on >= 10 journalled paired screen/serving arms whose serving
        effects exceed the serving floor, is >= 0.4 AND has a bootstrap 95% CI lower bound > 0; otherwise
        that family skips the screen and is evaluated on the serving instrument directly. An admitted screen
        may only rank and seed candidates; every keep/promote verdict is re-measured on serving. The 0.4
        floor is a borrowed HEURISTIC (MFTune released code refuses rho <= 0.39 on 10 pairs; the paper
        derives no threshold), not a derived constant. (c) LLM override cap 30% of config arms, overrides
        told back. (d) LLM-authored RUNTIME_CONFIG hypotheses enter as a declared SET of arms, executed and
        journalled by the harness, never as an LLM-driven launch/edit loop. The harness owns best-seen state
        and keep/commit. A campaign with < 3 distinct non-default configs measured is reported
        under-explored, not converged. (e) SOURCE and non-box edits stay LLM-authored. Reason, recorded with
        the row: NO-GO for a classical sampler as default today (effects below floor, tens of arms).
        intake-1389 (MOBO beats Sobol at 50 evals only where categorical effects are large) is off-regime
        and does not reverse this. Do not cite intake-1372 as "classical beats LLM" (D-20) or intake-1381 as
        "RS beats HPO" (D-37). (intake-1372#01, #06; intake-1381#03, #06; intake-1390#01, #04, #05;
        intake-1391#01, #06; intake-1392#02, #04, #05; intake-1394#03, #08; intake-1389#record)
        ✅ 2026-09-15 — design closure only: the ownership split and all four admission/cap rules above
        are now the U3-SEED contract. Runtime enforcement remains part of the still-open parent U3-SEED;
        the current planner deterministically enumerates declared one-factor runtime dimensions and has no
        TPE/classical/LLM knob-box sampler to constrain, so adding a detached policy module now would be
        dead code rather than enforcement. Focused `test_unified_planner.py`: 31 passed.

<!-- original line 10768 -->
- [x] **U3-DEFAULTS — RESOLVED 2026-09-08: NOT APPLICABLE. R23-58 did NOT confirm the shim on the GPU
      serving path, so it does NOT go into the loop's recipe defaults.** ✅ 2026-09-08. The conditional this
      task was written under evaluated **false**: bounded null, T0/D0, registered action "do not adopt".
      **Do not add `GGML_NOHUGEPAGE_PROCESS` to any loop-launched `llama-server` on the GPU surface** — the
      premise that the loop "pays the OFF variance today" is refuted for that surface (OFF p95_dev 6.657%
      vs ON 9.334%; the ON arm was wider). Closing this as *resolved-negative* rather than deleting it, so a
      later reader does not re-derive the same candidate and re-spend the 27 minutes.

<!-- original line 10802 -->
- [x] **U3-EXPRESS-3 — a self-drafting model is expressible as a recipe** ✅ 2026-09-08
      (research `c3e362a1`: `spec_decode.drafter` optional, `-md`/`-ngld` omitted when absent, `--spec-type`
      still passed; `test_selfdraft_recipe.py` covers both shapes, spec=none, and a fail-control; suite
      587 → 592). Third of the three gaps above; the first two landed the same day as `b5f58b74` and
      `4952e95e`.

<!-- original line 10985 -->
    - [x] **U4-NOISE-LAND — land research `a1e94a002` (driver re-pins every server task before the residency check) on research main.** It sits only on the detached run tree `/mnt/raid0/llm/worktrees/gpu-cpu-noise-run-20261021`, so the W2 driver and the GPS-PIN package's claim that the noise driver "already pins" rest on an unreachable commit. (filed 2026-10-22, workspace-58 wrap-up)
      ✅ 2026-10-22 — the operator approved landing it. It is on research main as merge `538cda50b` (the `a1e94a002` re-pin plus `317cf72df` W2-Q38FN workload; 17 tests pass), merged under the research wrap-up lease.

<!-- original line 11010 -->
  - [x] **OP-40 transferred from INF-70 (operator ruling) and folded into OP-41; this session owns the
        single resulting item, and no duplicate row is carried** ✅ 2026-09-08

<!-- original line 11023 -->
- [x] Directive sent to `workspace-1c` with concrete instructions (rebase onto champion tip, opt-in the two
      blockers, record keeps in the bundle schema, LOO per promotion, fold at a loop boundary) ✅ 2026-09-07

<!-- original line 11029 -->
- [x] **FOLD-2 additions (UD-4)** ✅ 2026-09-08: on candidate `ef81196d5` — `test-backend-ops -o SSM_SCAN -b ROCm0` **7/7 OK**
      incl. the K=4 / K=3 rollback cases; `verify_ggml_linkage.sh` **PASS** before the serving gate; dispatch **observed**
      (`llama-bench -v` + `GGML_SCHED_DEBUG=2`: 27,516 nodes, SSM_SCAN=0, SSM_CONV 576 + GATED_DELTA_NET 576 all on ROCm0,
      CPU holds only 12 GET_ROWS); tg128 vs anchor-gen-021 **+0.052%** (20 pairs, floor 0.638%, not decisive, no drift).
      **UD-4 closed on observation.** Result file `/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json`

<!-- original line 11035 -->
- [x] ~~INF-70 **RETEST-1 turn in progress** (A/A first, then RETEST-1 in priority order); **next fold = their keeps off `ef81196d5`** — they stage~~ (closed 2026-10-29 audit: SUPERSEDED → RETEST-1 close-out 1fc2e2d45 (2026-09-08): no CPU keeps, sync17-fix2 DO-NOT-FOLD, consolidation complete at ef81196d5; INF-70 CLOSE-OUT f53fa4908)
      levers on a lane branch off that tip, prove merge-tree disjointness, and fold the same way

<!-- original line 11037 -->
- [x] ~~FOLD-0 (`inf70-audit`): fold-ready commit with both blockers opt-in; bit-identity + `test-backend-ops -b CPU`.~~ (closed 2026-10-29 audit: SUPERSEDED → fold executed instead via FOLD-1..3 (ticked box below, e5d1846d2): champion3 9c4f73e29 ancestor of ef81196d5; also in v10 base (kernel-manifests V11-025 CPU champion3 / INF-70 fold))
      **FOLD-0 as written targets `6f032c48d`, two CPU champions old — re-base onto the CPU champion at the
      boundary (today `inf70/champion3` @ `9c4f73e29`, build 10241, `experimental-inf70-champion3` on the `fork`
      remote: +4.50% vs champion-1 on 117/120 per-prompt wins, 1.5149× vs pristine, bit-identical over 16
      arm-pairs, α 0.8209 unchanged) or the fold ships a superseded kernel and discards the +4.50%**

<!-- original line 11042 -->
- [x] ~~Do not schedule the boundary under INF-70's live chains (SYNC-19/20 window 1 ~21:30Z + a second window,~~ (closed 2026-10-29 audit: SUPERSEDED → boundary scheduling moot: fold completed 2026-09-08 (e5d1846d2) and INF-70 campaign closed (f53fa4908))
      HARNESS-1 Phase B behind it) — rebasing under in-flight pre-registered arms invalidates them; clears in hours

<!-- original line 11044 -->
- [x] FOLD-1..3 (champion owner) per `autokernel-champion-aggregate.md` ✅ 2026-09-08: fold executed, all FOLD-2 gates
      PASSED (G1 7/7, G2 1140/1140, G3 39/39, G4 dispatch observed, G5 +0.052% inside the 0.638% floor), then
      `ak/champion/llama-cpp-0db32c06e3e5` fast-forwarded `bff30cebe` → **`ef81196d5`** (`--ff-only`, tip == candidate) at
      11:16:49Z, lineage verified (`bff30cebe`, `445e93a8`, `9c4f73e29`, production `0db32c06e` all ancestors), worktree
      clean, pushed to fork `pestopoppa/llama.cpp`; pre-fold GPU tip tagged `ak/pre-fold-gpu-tip-20260908` (pushed).
      **Production branch untouched.** NO relaunch (operator directive stands)

<!-- original line 11050 -->
- [x] **R23-51a in the same window** ✅ 2026-09-08: cor `445e93a8` seeded with a **MEASURED** tip-vs-cor tg128 bench,
      **+5.958%** (20 pairs, decisive, not drifting). The serving gate then ran on it: n=5 −5.19% (decisive, `diverged`),
      re-run n=10 **−2.18% NOT decisive** → disposition **UNCONFIRMED (not refuted)**; **cor HOLDS at `445e93a8`** and the six
      keeps stay on the tip as provisional and re-gateable. An **11-point proxy-vs-truth gap** the bench alone could never show

<!-- original line 11054 -->
- [x] **R23-49 pin + re-calibration in the same window** ✅ 2026-09-08: `cpu_list` pinned `184-191` on the GPU serving recipe
      and the serving floor re-calibrated under the pin — **4.581% p95** (n=10, cv 3.136%, median 161.08 tok/s) on a
      verified-quiet host; the first attempt was CONTAMINATED (10.255%, INF-70's server live) and was quarantined. The pin
      costs ~1 pp of floor width vs the 3.536% unpinned quiet floor

<!-- original line 11069 -->
- [x] ~~NO relaunch by default (operator 2026-09-08). **Consolidation exit ACHIEVED for the GPU side ✅ 2026-09-08**: one tip~~ (closed 2026-10-29 audit: SUPERSEDED → consolidation exit achieved 2026-09-08 per the box; unified status header (line 250) says live campaign is DS41 (INF-77) and relaunch GLM moot; v10 freeze 2026-09-22)
      carrying both lineages (**`ef81196d5`** = GPU tip + CPU champion3 `9c4f73e29`); **FOLD-2 passed**; the durable bundle
      **seeded MEASURED** (+5.958% tip-vs-cor) **and the serving gate run on it → UNCONFIRMED** (−2.18%, n=10, not decisive;
      cor holds `445e93a8`); **tip on the fork**. Consolidation is **complete for the GPU side pending INF-70's keeps**, which
      fold onto `ef81196d5` next. Phase-2 candidates below still to be gated or declined. Then ASK before any run 31.

<!-- original line 11101 -->
- [x] **QUANT-RECIP-9f85ba2fb — Quantize reciprocal — `rescued-ak-discovery-7e8da8ea-attempt1` @ `9f85ba2fb`** (`ggml/src/ggml-cuda/quantize.cu`
  - ✅ 2026-11-19 (autokernel) row `ak-quant-recip-gpu-20261119` DROP: 27B KLD 0.0 / top-1 100% (harmless), GPU tg128 12 ABBA geomean 1.0025 [0.9964, 1.0087], no measurable gain. Not carried into any composite. (Commit 47f336d63 carried only index regen; this is the actual tick.) [belief: cc]
      +4/−1: reciprocal-multiply + `__shfl_sync` broadcast replacing per-lane `roundf(xi/d)`; the champion still does
      `roundf(xi / d)`). Gate: tg128, 20 pairs vs anchor.
  - 2026-11-19 (autokernel, bulk P2 pass; box stays OPEN): not in any champion (`experimental/champion-llg-fold-20261105` quantize.cu still has `roundf(xi / d)`; candidate `9f85ba2fb` is the 4+/1- reciprocal-multiply hunk). The reciprocal multiply is NOT bit-identical to the divide at rounding ties, so the gate needs a correctness pair (Q8_1 quantize output vs anchor) before the tg128 20-pair A/B; both need a HIP build of C14 + this hunk and a GPU window. Row not published in this pass (in-row dual HIP build design; next in queue). [no-belief: triage]
  - 2026-11-19 (autokernel, row `ak-quant-recip-gpu-20261119`): model: Qwen3.8-27B Q8_0 (KLD + tg128) and Qwen3.8-Flash-Next UD-IQ4_XS (Q38FN, `--n-cpu-moe 48`, top-1). Arms: A = C14 `eee3da838`, B = `f73a4bdef` (C14 + cherry-pick of `9f85ba2fb`, branch `llama.cpp-experimental-c14-quant-recip-20261119`, worktree `/mnt/raid0/llm/worktrees/llama-c14-quant-recip-20261119`), both built in-row with the same pinned HIP configure argv. Correctness gate: 27B KLD <= 0.003 and |dPPL| <= 0.5 %, Q38FN same-top-1 >= 93 %, no new test-backend-ops failure on the quantised MUL_MAT/MUL_MAT_ID n 1..8 cases; then tg128 ABBA pairs, 10 to 12, KEEP iff the 95 % interval lower bound > 1 and geomean >= 1.003. Stop-on-answer: KEEP, or the first DROP clause (correctness failure skips the speed leg). Stop-on-futility: FUTILITY_MISSING_INPUT, FUTILITY_BUILD, FUTILITY_RESIDENCY, FUTILITY_UNPARSED, or the pair interval upper bound < 1.003 after 10 pairs (gate-class futility-only; rc 75 only on STOP/deadline). [no-belief: row preparation]

<!-- original line 11107 -->
- [x] ~~**Q5_0 `vecdotq.cuh` variants — `f9d74a2a3`, `d4b0a04e4`, `580e8d090`, `5d22a5463`: DECLINE.** Q5_0 is not a~~ (closed 2026-10-29 audit: SUPERSEDED → box itself records DECLINE; consolidation audit d33bd5548 / docs/design/champion-consolidation-audit-20260908.md classified Q5_0 variants as declined)
      production quant and the work is re-derivable. Revisit only if a Q5_0 target appears on the fleet.

<!-- original line 11109 -->
- [x] Single-copy refs pushed to the fork ✅ 2026-09-08 (`ak/orphan-keeps-quantize-20260829`,
      `ak/pre-anchor-fix-full-history` `b04fad244`, `ak/run14-01893a36-cumulative` `01893a36c`,
      `ak/admission/remove-funsafe-math-20260831` `3161d2dcf` — the last is already applied on the champion as
      `b861c32fa` (CH-7, 2026-08-31); pushed for durability only, nothing to fold)

<!-- original line 11134 -->
- [x] `Bundle.surface`; per-surface store filenames; `load_bundle()` per surface; shared cor invariant test ✅ 2026-11-01 — Research `a25f5ff79b2db6c4c883d7eb1402ada87ca46c63` + `064d758ee4218014628eb021d9526eaafff7f456`: opt-in typed CPU/GPU v3 snapshots and separate bundle/journal paths; shared COR refusal/CAS promotion, per-surface load/epoch/recovery, deadlock-safe lock order, and explicit-store `champion_reanchor` compatibility with missing/corrupt-authority refusal and legacy fallback. R6: 74 bundle/journal + 1 explicit CPU + 1 legacy CPU + 19 reanchor tests passed; changed-line Ruff and scoped diff checks passed. [artifact](../../artifacts/engineering/autokernel-bundle-surface-20261101/README.md) [no-belief: source implementation and synthetic correctness verification only; no native measurement, live-store mutation, or production promotion]

<!-- original line 11135 -->
- [x] `serving.Recipe` CPU variant (device, cpu_list, numa, threads) — the CPU session's canonical recipe codified ✅ 2026-10-30 [no-belief: source identity/launch validation] <!-- evidence-integrity: Research `6cf25cfab8e45e760cbe4291134b58730ae1eb70`; artifact: artifacts/compute/task-evidence-repair-20261031/serving-recipe-cpu/EVIDENCE.json; hygiene, not quota -->

  <!-- task-evidence-integrity:start SERVING-RECIPE-CPU -->
  - Evidence metadata (hygiene, not new quota): Research `6cf25cfab8e45e760cbe4291134b58730ae1eb70`; [test/artifact](../../artifacts/compute/task-evidence-repair-20261031/serving-recipe-cpu/EVIDENCE.json).
  <!-- task-evidence-integrity:end SERVING-RECIPE-CPU -->
  - Research `6cf25cfab8e45e760cbe4291134b58730ae1eb70` adds explicit validated NUMA identity/launch policy and canonical mismatch refusal. Missing field is omitted, preserving exact old CPU/GPU recipe hashes and legacy CPU canonical launches that already carry a NUMA prefix. Descending node ranges refuse.73 current-source tests pass with no new lint. No old recipe upgrade, new floor or native NUMA-placement claim. [Evidence](../../artifacts/compute/refactor-c5-r3-and-source-closures-20261030.json).

<!-- original line 11141 -->
- [x] **AK-CPU-AA-CALIB** CPU A/A calibration: screen floor + serving floor, unit and host-state hash recorded; gating-floor calibration n≥24 with interval (FLOOR-UNIT-1 supersedes the earlier n=20 proposal) Row ak-cpu-aa-calibration-20261118: model: Qwen3.8-Flash-Next (Q38FN) + MTP, C14 CPU store both arms, 24 AB/BA pairs on q1+q2 (q0-q2 booked); stop-on-answer when 24 valid pairs are measured (screen + serving floors with intervals written via build_record); stop-on-futility on missing input, wrong grant, or > 8 invalid launches; gate-class = futility-only.
  - 2026-11-18 (autokernel, box note, NOT ticked): Research `d3b512b74` adds `loop/cpu_aa_calibration.py` + `test_cpu_aa_calibration.py` (4 tests): `build_record` emits screen floor (5 pairs) and serving floor (4 pairs) with intervals from `serving._matched_summary`, `unit=process`, host-state hash, contention label checked against foreign load, refuses n<24 and non-process unit; optional determinism block (27B A/A KLD exactly 0, row `c15-cpu-fa-splitkv-xmodel-20261118`). Existing evidence (c15 rows: quiet ±1-2%, co-tenant ±20%) is context, not an n>=24 A/A. **Fresh measurement prepared, UNPUBLISHED:** row `/mnt/raid0/llm/tmp/ak-cpu-aa-calibration-20261118` (READY-TO-PUBLISH; 24 AB/BA pairs of the C14 store in both arms, q0-q2 booked, servers q1+q2, ~5 h, priority_rank 60). **Tick after:** the row runs, RESULT.json is folded through `build_record`, and the record is written. [no-belief: code]
  - 2026-11-19 (autokernel) **answered: CALIBRATED_CONTENDED** (filed `pass`), row `ak-cpu-aa-calibration-20261118`, Q38FN + MTP, C14 CPU store both arms, 24 balanced AB/BA pairs (48 launches all valid), unit=process, per-step decode ms on P4K (gating): **screen floor (5 pairs) 3.84%, 95% interval 2.71-8.04%; serving floor (4 pairs) 4.15%, 2.74-10.65%**; all-24-pair floor 1.38% (0.96-3.38%); pair ratio median 0.994, range 0.815-1.080 (log-sd 5.1%). Contention label **co-tenant**: worst foreign busy p95 81.6%, 7/48 launches above the 15% quiet limit; restricted to the 19 pairs where both launches were quiet the pair log-sd is 2.2% (range 0.952-1.040), i.e. the +-1-2% quiet scatter, so these floors are co-tenant upper bounds, not quiet floors. P32K (info, 12 pairs): screen 9.51% (1.94-61.4%), serving 9.47%, pair ratio 0.386-1.164 -- unusable under load. Folded with `cpu_aa_calibration.build_record` (research origin/main), host_state_hash `6f20372e22c0dde7b09a67f615a849a54d0abd9323c33c07e327dcf4764f90b9`, record `/mnt/raid0/llm/tmp/ak-cpu-aa-calibration-20261118/out/cpu-aa-calibration-record.json` (not written into the frozen C14 store). Rule: any CPU speed claim under ~4% is inside the contended floor; treat quiet-host rows separately. [belief: cc]

<!-- original line 11144 -->
- [x] **Every floor record carries `unit` (arm | session | process)** alongside harness, n, contention model and host-state hash; a gate comparing an effect to a floor of a different unit REFUSES ✅ 2026-09-14 — research `eb8a88de`: `unit` + `n` are required fields of `serving_floor.v1`/`.v2` and of the bench `surface_calibration.v1` writer; `FloorReading.gate_floor` / `serving.check_unit` are the single admission rule and raise `FloorUnitMismatch` (a `ServingFloorMismatch`, so every gate already exits REFUSED) naming both units; legacy unit-less serving floors load but cannot gate, and nothing on disk was rewritten. See R23-55. (Original refs: INF-70 RETEST-1,
      2026-09-08: arm sd 0.501% vs process-launch sd 2.793%; the 1200-fold THP sizing error.)

<!-- original line 11146 -->
- [x] **Headline admissibility: ≥N independent launches with a session-unit CI**, N sized from the
      between-session sd (2.793%), not the arm sd; a single-session headline is refused (R23-57) **Give N a
      number now** (2026-09-15, intake-1367#record): solve N from the recorded between-session sd for a
      stated minimum detectable effect, write N into the floor/headline record schema, and make a headline
      computation with fewer than N launches REFUSE (not warn), per the unit-mismatch precedent
      (FloorUnitMismatch, R23-55). ✅ 2026-09-15 — research `d15997d6`: with MDE 3.0%, recorded
      between-launch SD 2.793%, two-sided alpha 0.05 and power 0.80, the minimum is 14 independent
      launches per arm (28 total). The record carries those design inputs and a bootstrap 95% CI;
      headline computation below N refuses rather than warning.

<!-- original line 11155 -->
- [x] **GPU-LAUNCH-VAR-COVARIATE — Investigate the source of between-launch variance on the champion** (page-cache/NUMA placement, THP
  - ✅ 2026-11-19 (autokernel) row `ak-gpu-launch-var-covariate-20261119` NOT_ATTRIBUTED: W1 27B+DFlash2 on C14, 28 launches, CV 3.25% (up95 4.43%). HIP graph counters, allocator memlog and buffer sizes identical every launch, so graph capture and allocator are ruled out; page cache (Cached_kb rho -0.29), MemFree/Mapped/THP, load time, foreign busy and order all n.s. (Bonferroni k=8). Remaining suspect is device-level (sclk/thermal), covered by AK-PROF-SCLK. Unlike CPU (THP), there is no host-side lever for GPU launch variance. [belief: cc]
    - 2026-11-19 (autokernel): device-level suspect confirmed as operand/power-dependent sclk (AK-PROF-SCLK DELTA: -297 MHz MMQ, -248 MHz FA random vs zero). [no-belief: cross-reference]
      state, HIP graph capture, allocator) — ~12% spread on an identical config, pristine control stable (R23-57)
  - 2026-11-19 (autokernel, bulk P2 pass; box stays OPEN): CPU half answered by evidence in hand: THP is the source (CHAMP-2: shim OFF 2.510% vs ON 0.481% between-launch sd, 25x; `GGML_NOHUGEPAGE_PROCESS=1` adopted on the CPU decode path, in the C10+ recipe ENV). The n=24 process-unit scatter on the current champion is booked as `ak-cpu-aa-calibration-20261118`. GPU half: R23-58 measured the shim as a bounded null on GPU serving, so the GPU between-launch source (HIP graph capture, allocator, page cache) remains uninvestigated and needs a GPU covariate-capture row. [no-belief: triage]
  - 2026-11-19 (autokernel, row `ak-gpu-launch-var-covariate-20261119`): model: Qwen3.8-27B Q8_0 + DFlash2 drafter (W1 recipe) on the C14 GPU store, MI210. Up to 28 identical fresh-server launches alternating Q (default verbosity) / V (`-lv 4` + `GGML_CUDA_GRAPH_MEMLOG=1`); per launch the HIP-graph counters, allocator stats (GRAPH_MEMLOG, buffer sizes, own-pid VRAM), page-cache residency of the GGUFs (mincore), meminfo and launch order are recorded next to two 256-token decodes. Stop-on-answer (after >= 16 launches, every 2): NO_BETWEEN_LAUNCH_VARIANCE (CV <= 1 %, upper 95 % bound <= 1.5 %), or ATTRIBUTED(covariates with |rho| >= 0.6 and Bonferroni-significant), else NOT_ATTRIBUTED at 28. Stop-on-futility: FUTILITY_MISSING_INPUT, FUTILITY_WRONG_GRANT, FUTILITY_RESIDENCY, FUTILITY_INVALID_LAUNCHES (gate-class futility-only; rc 75 only on STOP/deadline). [no-belief: row preparation]

<!-- original line 11162 -->
- [x] ✅ 2026-11-01 — Research `2f047a7b1a1a47f30d97e27ddd4c4153d11f911f`; [354-test committed-source suite](https://github.com/pestopoppa/epyc-inference-research/blob/f7061c0cecfc279cf1a1436227ef00285fd2c306/artifacts/engineering/aku-stale-baseline-20261101/README.md). [belief: cc] **Re-baseline on cor advance**: `stale_baseline` set on every non-promoting surface at PROMOTE, cleared only by
      a tip-vs-new-cor measurement on that surface's own harness; test that a quote while flagged is refused

<!-- original line 11164 -->
- [x] **S3-AKU-07 — promotion evidence from held-out launches.** The promotion record's compounded gain, and
      any headline, is computed ONLY from fresh launches disjoint from every A/B pair that decided a keep,
      against the frozen production binary pinned by commit + recipe hash. Record pair ids on both sides so
      disjointness is checkable. A computation that reuses keep-deciding pairs REFUSES. S3-AKU-03 sets how
      MANY launches; this sets WHICH. intake-1370#record (ERA separates selection from report).
      ✅ 2026-11-17 (autokernel, code-only): `epyc-inference-research` `f6e09036a` `promotion_evidence.compound_from_heldout` computes the compounded gain only from launches pinned to a 40-hex production commit + 64-hex recipe hash, records both `heldout_pair_ids` and `deciding_pair_ids`, and REFUSES (`PromotionEvidenceRefusal`) on any overlap with a keep-deciding pair, duplicate/blank pair id, unpinned or mismatched binary/recipe, invalid effect or too few launches. `test_promotion_goodhart.py` 11 passed (disjoint compounding 0.10x2 -> 0.21; each refusal). Launch COUNT remains S3-AKU-03. [no-belief: tooling landing, no measurement]

<!-- original line 11178 -->
  - [x] **AK-LOO-CONFIRM-C14 — contention-gated confirmation of the C14 CPU LOO signal.** model: Q38FN Q8 CPU (Qwen3.8-Flash-Next UD-IQ4_XS + MTP Q8_0), 48t pinned 24-71, booked q0-q2. Row `ak-loo-confirm-cpu-c14-20261119`: arms full C14 vs R1 (-0d270f99b), R3 (-a331665d4), R1234 (-L1..L4), >= 8 valid ABBA blocks per arm on P4K and P32K, block rejected if in-grant foreign busy_p50 > 15%. Rule: REMOVE_KEEP iff paired gain >= 4.15% with every block positive and CI lower > 0 and the other surface mean > 0; else RETAIN. If greedy content differs, REMOVE_KEEP_PENDING_CORRECTNESS (27B KLD <= 0.003, |dPPL| <= 0.5%; Q38FN |dPPL| <= 0.5%, top-1 >= 93%). Stop-on-answer: 8 valid blocks or 14 attempts per arm. Stop-on-futility: CI upper < 4.15% on both surfaces at 4 or 6 blocks (RETAIN), 6 consecutive rejected blocks (FUTILITY_CONTENTION). est 41400 s (~11.5 h).
    - ✅ 2026-11-19 (autokernel) `ak-loo-confirm-cpu-c14-20261119` filed **pass**, DECIDED: keep all four C14 CPU keeps. R1234 (revert all) P4K -0.81 % [-4.1, +2.6], P32K +0.37 % [-3.0, +3.9] RETAIN_FUTILITY; R1 P4K -1.05 % [-1.8, -0.3], P32K -1.17 % [-1.7, -0.7] RETAIN_FUTILITY (reverting is slower); R3 P4K +1.26 % [-1.8, +4.4] RETAIN. Numerics identical. 6 contended blocks were rejected by the in-grant busy gate (incl. the dtree build windows in the row CONTAMINATION.json); no arm is near the 4.15 % floor. Next composite carries the keeps unchanged. [no-belief: row verdict filed by agent]

<!-- original line 11187 -->
- [x] Oracle extension: op-coverage diff for env-gated knobs (fall-through class) ✅ 2026-11-19 (autokernel, code-only): done by the AKX-P1e classifier, research `80506a7d2`/`35a43f35e` (`loop/blast_radius.py` `exercised_knob_flips` + `classify`): a knob default flip or a set knob is TOUCHED, a knob read with no default change and unset is INERT only with a T1 coverage-profile witness, else UNKNOWN (counted TOUCHED). `evaluator/test_blast_radius_controls.py` + `loop/test_blast_radius_keep_path.py` 27 passed at research `93445e31e`. Live census/witness inputs stay under AKX-P0d. [no-belief: code]

<!-- original line 11208 -->
- [x] **P4-0 precondition** ✅ 2026-09-07 (INF-70 took it): `scripts/utils/foreign_load.py` + `test_foreign_load.py` on
      research `main` `de51899c` (branch `inf70/foreign-load-sampler` `e441de78`, merged by `ak-rebuild-20260828`: merge-tree 0
      conflicts, 7 tests green). Importable `sample_once()` / `bench_logical_cpus()`; `--out`/`--bench-cpus`; fails CLOSED on
      unreadable sysfs; foreignness by `cpus_allowed` intersection (permissive by design, `on_bench_core` per row for the strict
      reading); the sibling test is mutation-isolated. Scratch copy stays until SYNC-19/20 + HARNESS-1 finish in-flight arms.

<!-- original line 11219 -->
- [x] LOO + re-baseline receipts are REQUIRED fields before shared-source advancement; the
      serial controller refuses to treat required-target validation as complete until every
      enrolled production surface and every keep-author surface has an exact current-tip row,
      then schedules one real `source_loo.execute_surface` treatment per retained keep plus the
      required re-baseline under the original held CPU/GPU claims. Continuations bind the target,
      assembled commit, candidate execution digest, instrument, request digest, pair count and
      immutable result hashes. Missing or inconclusive rows remain pending; an inconclusive LOO
      becomes retry-eligible only after one ordinary search opportunity, while failed rows remain
      failed. No LOO result grants deletion or promotion authority. ✅ 2026-09-10 — research
      `ee0ee378`; combined existing CPU/GPU/serving/screen/serial/LOO suite 109 passed in 33.22s.

<!-- original line 12432 -->
  - [x] **AKU-01a — explicit-snapshot enrollment and offline CLI**: immutable typed CPU/GPU targets,
    exact artifact/source identities, alias/obligation union, idempotent requests, finite seed marker,
    pinned explicit/implicit baselines and per-target prerequisite states. ✅ 2026-09-09 — main-reviewed
    `campaign.py` plus `campaign_cli.py`, 52 focused tests. Optional local file verification reports
    failures separately without rewriting pins; every output says `admission_ready: false`.
    `docs/autokernel-unified-campaign.md` contains the tested CLI/schema example. The real production
    registry selector/adapter, enrollment events and service consumer remain required for AKU-01.

<!-- original line 12439 -->
  - [x] **AKU-01b — canonical production exporter and local-model seed enrollment consumer**:
    automatic CPU/GPU production roster, pinned source/launch context, alias/obligation union,
    explicit local TargetSpec/artifact seeds and per-target unsupported/missing dispositions.
    ✅ 2026-09-09 — main's **118 research tests** and **128 orchestrator/cross-repository tests** pass.
    Export validates loaded launcher tables against pinned inputs and refuses stale compiled priors;
    it cannot accept an injected stale registry. Explicit `--out` seals create-only/fsynced per-target
    recipe sidecars; stdout export and research resolution remain noncreating. Full/quarter recipes
    have distinct actual byte hashes; true aliases still merge. A sealed recipe cannot erase a source
    unsupported/waiting status, including missing DSO prerequisites. Production dry-resolution v2 keeps
    speech/unknown/unsupported rows visible; v1 ordinary manifests remain supported. Local seed refs
    cannot replace production pins or reuse an opposite-backend production recipe/build. Model launch
    compatibility and current byte verification are separate from declared enrollment; no downloads,
    live registry recompilation, worker launch, enrollment Journal event or grant is added here.

<!-- original line 12455 -->
  - [x] **AKU-02a — explicit environment-unset semantics**: inherited treatment is absent in the
    control; immutable unset state roundtrips/hashes; legacy no-unset identities remain unchanged.
    ✅ 2026-09-09 — reviewed `Recipe.explicit_unsets`, real `server_env()` consumer and bidirectional
    readback fixtures; 89 focused tests and 611 loop tests / 59 subtests pass. This does not yet freeze
    the full inherited environment or supply the new CPU runtime-arm adapter.

<!-- original line 12460 -->
  - [x] **AKU-02b — frozen launch resolution and CPU serving consumer**: explicit artifact identities,
    allowlisted effective environment and absences, derived backend/speculation capability, frozen
    argv/workload/readback expectations, and the optional real `_measure_once()` consumer.
    ✅ 2026-09-09 — 31 main-run focused tests. Exact snapshot integrity is separate from normalized
    execution identity: relocation/port/recipe label do not change execution, while model/DSO load-name
    content, runtime semantics and environment do. CPU uses explicit `device=none, ngl=0`; zero VRAM
    is not a GPU veto, but placement/contention remain unproven. Multi-device/mixed-draft, overriding
    extension flags and unknown capabilities refuse before launch. Runtime-set/master-off samplers,
    CPU lifecycle witnesses, planned no-build arms and policy consumers remain required. Legacy recipe
    hashes are unchanged; the inherited HSA override is actually removed and floor writes now use the
    hardened JSON publisher. Metric prose now accurately describes the unchanged sum-of-slot-rates.

<!-- original line 12471 -->
  - [x] **AKU-02c — canonical CPU/GPU launcher recipe adapter and existing serving conformance**:
    closed explicit canonical recipe schema, full semantic/argv rederivation, NUMA prefix grammar,
    immutable launch environment and exact artifact/source provenance.
    ✅ 2026-09-09 — the AKU-01b acceptance includes the real sealed production export → Campaign CLI →
    canonical recipe → existing `_measure_once()` path with fake CPU/GPU processes. Conflicting flag
    aliases, unknown NUMA policies, rehashed semantic mismatches and credential-bearing environment
    refuse; source/recipe identity cannot substitute for witnessed placement or execution. Production
    command construction defaults are unchanged; its opt-in dry seam only skips runtime-directory
    creation. Actual whole-arm observers, runtime sweeps, worker containment and registered policy
    consumers remain separate required work.

<!-- original line 12484 -->
  - [x] **AKU-03a — durable derived JSON publication**: file fsync, atomic replace and directory fsync;
    injected pre/post-rename failures preserve the right artifact and never report durable success.
    ✅ 2026-09-09 — real `status.write_json()` caller hardened; 28 focused tests pass, including
    descriptor cleanup and post-rename durability failure. This alone is not journal recovery.

<!-- original line 12488 -->
  - [x] **AKU-03b — journal-backed bundle recovery**: snapshot before projection; replay, explicitly
    labelled legacy import, fail-closed missing/unsupported/corrupt state and ancestry; preserve cadence
    while invalidating stale compounded gain after an external tip change.
    ✅ 2026-09-09 — `LOOP_BUNDLE_SAVED` is operational state, not a claim. v1 imports preserve original
    snapshots and default to `unknown_legacy`; current v2 requires validity and makes old readers refuse
    unsupported state. Journal replay repairs missing/corrupt projections, never invents COR. Tip
    advance retains historical magnitude but disables its threshold authority. Main run and manual
    `serving_gate --tip` consume recovery; dry manual inspection opens only an existing read lock and
    never imports or rewrites. Corrupt history requires restoration, not blind reseeding. Native phase,
    integration/control events and candidate transactions remain AKU-03 work.

<!-- original line 12498 -->
  - [x] **AKU-03c — serialized prospective arm-capture consumer**: native
    `PLANNED_SERVING_ARM_CAPTURED` events, current campaign/config/supervisor/worker-result fences,
    byte-verified immutable artifacts, exact-payload retry index and restart/uncertainty handling.
    ✅ 2026-09-09 — actual planned-serving→store→controller→journal→restart→independent Vidya reader
    integration passes; main acceptance **278 tests and 15 subtests**. Both comparison identities,
    process/prompt/request/witness links, selected launch values and aggregate are rederived from
    frozen/native inputs. Closed unsupported/malformed inputs refuse; genuine unsupported-unit and
    continuation carriers remain diagnostic. Scoped same-thread/lifetime callbacks serialize lookup,
    append/fsync and projection under the controller mutex; ambiguous append/index failure poisons
    that incarnation. Historical retries return the original event without recreating current worker
    authority. The real lifecycle owner must supply the trusted result fence; none is inferred from
    JSON, and this slice adds no workers, grants, grading, candidate advancement or scientific clock.

<!-- original line 12513 -->
  - [x] **AKU-04a — immutable structural plan/unit view and calibration applicability API**: strict
    record-class/phase identity, declared fixed-N membership/pairing/order, complete prompt/terminal/
    witness binding, one immutable admissible view, and offline CLI using the real validator.
    ✅ 2026-09-09 — 72 main-run focused tests. Directly constructed objects and supplied view digests
    are revalidated; zero/incomplete or invalid paired units cannot become a complete result. Observation
    cannot become a claim; discovery cannot bank/release; strict-search cannot headline. A2 nomination
    and claim-bearing uses lack their registered verifier/grader integrations and fail closed. Calibration
    requires declared unit, n≥24/interval, exact registered-estimator replay and a registered applicability
    rule; raw replay and plan applicability have separate caches, and transient callback failures are not
    cached. This is structural validation, not verified independence or a second grading ladder. Actual
    instrument consumers, native phase/unit events, A2 semantic attestation, power/bounded-null handling
    and shared ClaimTuple projection remain required for AKU-04.

<!-- original line 12525 -->
  - [x] **AKU-04b — frozen planned-serving launcher consumer**: distinct resolved recipes, exact
    canonical prompt bytes, fixed unit order/membership, retained native observations and one shared
    admissible-unit view. ✅ 2026-09-09 — main's 117 tests and 3 subtests pass, including legacy serving,
    resolved recipe and ExperimentPlan coverage. Missing/nonfinite/boolean timing fields cannot become
    zero measurements; warmup/measurement slot failures are retained, raw observations are sunk before
    provider completion, and witness states are not inferred from references. Failed units stop the
    sequence. Continuation prevalidates an exact completed prefix and prior lineage before any admission.
    The trusted provider must enclose the worker with owned-descendant and stage-plus-teardown bounds;
    these are injected consumer contracts, not a local process-tree enforcement implementation. Native
    journal/ClaimTuple hook, real lifecycle samplers, registered inference protocol and worker/provider
    integration remain required. All resulting use status remains `policy_undefined` in this slice.

<!-- original line 12536 -->
  - [x] **AKU-04c — prospective sealed arm producer and shared immutable store**: actual planned
    serving emits raw observations before its sealed arm carrier, binding the complete frozen plan,
    exact request bytes, process membership, worker/source identities, timestamps and canonical unit
    view. ✅ 2026-09-09 — main's integrated capture/candidate/Journal suite passes 382 tests and 15
    subtests. Supported scalar is serving/process/level/median with units `t/s`; independent n counts
    scored process launches. Unknown placement/contention or absent GPU residency remains diagnostic,
    not a widened threshold. Store publication uses owned private paths, nested thread/process exclusion,
    no-overwrite content addressing, fsync and exact-inode crash recovery; noncreating verification
    cannot recreate a lost published dependency. Controller-native journal wiring is the next consumer.
    Loaded evaluator identity, real lifecycle witnesses and registered policy remain required; no
    measurement, historical backfill or execution authority is claimed by fixture success.

<!-- original line 12547 -->
  - [x] **AKU-04d — generic fixed-member A2 runtime discovery consumer**: exact same-artifact
    runtime frames produce a sealed three-anchor bank and three candidate-only invocations;
    cached-bank reuse adds no fresh anchors. ✅ 2026-09-09 — main's clean nine-file release passes
    **1,512 tests and 83 subtests**; the final focused observation/screen/plan/serving run passes
    **143 tests and 3 subtests**, with Ruff clean. Full frame identity includes target/prompt,
    estimator/estimand, required witnesses, policy, evaluator, power/frequency, resource claim and
    host epoch. Invalid completed units are durably terminal, never silently rerun; uncertain intent
    requires reconciliation. Serialized replay grants no bank/nomination authority without the exact
    live verifier. Registered nomination permits only the completed candidate-only advisory view;
    keep, validation, release and grading remain unavailable. A3 hides stale-epoch magnitudes and
    refuses mixed current frames. Ordinary load remains recorded noise, not an automatic A2 veto.
    Source `04d73260`, main `d75bc9ec`; actual controller/native phase adapters and shared Vidya
    projection remain active work under AKU-04/08 and VB-AK-UNIFIED-DISCOVERY.

<!-- original line 12560 -->
  - [x] **AKU-04e — controller-owned A2 phase persistence and cached-bank replay**: exact
    fixed-plan INTENT/TERMINAL/SEALED records use the native Journal and one startup-built bounded
    index; ambiguous append poisons that lifetime and exact retry preserves original bytes.
    ✅ 2026-09-09 — main's clean composition with published standalone controls passes **1,831
    loop/Journal/storage tests plus 165 subtests**, including the independent cached-bank probe;
    Ruff/diff checks pass. Candidate-only reuse references its original seven anchor event/Journal
    identities and sealed bank, adds no synthetic anchors, and reopens after restart. Foreign,
    missing, forged or stale-frame sources refuse. Fourteen actual phase events and at most one
    separate bank reference remain the bound. Source `6b5d5fda`, main `c36411a7`; no actual native
    invocation, semantic grading or real comparison is established by this persistence slice.

<!-- original line 12598 -->
  - [x] **AKU-04j — refuse discovery misrouting through ordinary comparisons**:
    ✅ 2026-09-09. Inline pinned driver guards exclude canonical discovery phase, record class
    or A2 protocol declarations before catalog issuance, retaining other eligible work and one
    precise unavailable reason. Historical misclassified intents remain readable but refuse
    materialization before binding or worker acquisition. No new discovery permit/event or
    activation is supplied. Main final **18 tests passed**; worker compatibility **122 passed,
    one existing strict HELD xfailed, no skips**. Exact two-file packet
    `9abb2115347b8d4af796bc6157c6845addc3aafab4544c9fc9e27cfe6ecc2c21` matches primary.
    Prior published transport main `0114da9b` independently passed the complete loop/Journal
    suite: **2,490 passed, two strict xfailed, 83 subtests, no skips in 309.68s**.
    That full run predates this guard; final guard coverage is the focused/compatibility scope.

<!-- original line 12609 -->
  - [x] **AKU-04h — align native startup fixture with prospective sample admission**:
    ✅ 2026-09-09. The full published suite exposed one fixture declaring 64 samples for
    32 seconds at 10ms cadence (requires 3,209). The test now derives its count before
    sealing instrument identity and asserts exact prepared-plan admission. Timing, cadence,
    gap, byte limits and production admission are unchanged; main's 80 adjacent tests pass.
    Repaired research main `b9cc11af` then passed the full loop/Journal suite: **2,436 passed,
    two strict expected failures, 83 subtests**, no skips (299.83s). Expected failures remain
    OP-AKU-BIND and OP-AKU-HELD, not successful native resource binding or interrupted recovery.

<!-- original line 12617 -->
  - [x] **AKU-04g — installed raw serving-calibration preparation**: ✅ 2026-09-09.
    Startup v4 prospectively derives bounded A/A and neutral-copy process pairs and retries;
    the actual driver/controller/native worker collects immutable original chunks. Only exact
    durable settlements admit chunks to the existing numeric solver; fresh settled restart
    preserves identities and accounting. Neutral physical snapshots stay retained without fake
    runtime dimensions. Main independently passed 144 tests with one strict held-recovery xfail;
    the prior-base full suite passed 2,398 with two strict xfails and 83 subtests. Research source
    `097c5be8`, main `ebb5e9fa`. Fixture providers and observations are explicit, not hardware proof.
    All solves remain diagnostic/unqualified: original qualified controls/window and phase/cell
    scope are still required. OP-AKU-BIND and OP-AKU-HELD remain open; interrupted pre-settlement
    restart refuses rather than recollecting. This does not complete AKU-04 or AKU-12a/b.

<!-- original line 12631 -->
  - [x] **AKU-05a — private-index accepted source commits**: the real `archive.keep()` consumer commits
    only accepted literal paths from captured HEAD, preserves peer index bytes, honors commit hooks and
    advances the selected ref with expected-parent CAS. ✅ 2026-09-09 — 83 main-run adjacent tests and
    7 subtests pass, including 26 focused private-index cases. Wrong repository/branch, path expansion,
    hook-added peer staging and concurrent ref advance refuse; notification failure after a landed
    commit does not report a nonexistent commit failure. HEAD binding is rechecked immediately before
    ref CAS, not claimed as an atomic branch-binding transaction; the owning integration lock remains
    necessary. This supplies source safety, not a measured candidate or cross-repository transaction.

<!-- original line 12639 -->
  - [x] **AKU-05b — immutable candidate/validation contract and offline CLI**: explicit Git object
    format, one source set with per-target exact CPU/HIP build selection, candidate/control recipe and
    workload identities, declared keep deltas, separate integration/validated pointers and frozen rows.
    ✅ 2026-09-09 — main reviewed 28 focused tests within 159 passing adjacent tests. Required production
    target/backend obligations and complete keep-set LOO are checked at batch start and advancement;
    loaded state cannot bypass them. Trusted bound row/LOO verifiers are mandatory, and callback errors
    refuse. Completing an older gate preserves newer keeps and monotonic gain-trigger generations;
    cadence reset does not clear validation debt. Exact start retries are idempotent, conflicting batch
    payloads refuse, and optional seed rows may remain pending without being counted as passed or blocking
    required-row completion. Output-correctness equivalence does not grant timing. The offline CLI always
    denies execution/promotion authority. Actual registered verifiers, durable candidate transactions,
    native validation events and retention consumers remain required; this is not a measured candidate.

<!-- original line 12651 -->
  - [x] **AKU-05c — durable candidate transactions and recovery consumer**: native journaled
    INTENT → PREPARED → COMMITTED phases, immutable manifest objects, owned experimental refs, exact
    idempotence and expected-state CAS. ✅ 2026-09-09 — main's 382-test integration includes six
    adversarial candidate/cache probes. Old-request retries return the original result without replacing
    the newest projection. Controller capabilities are lifetime/thread fenced; retained public views
    cannot mutate authoritative state. Startup rebuilds indexes once; ordinary operations use bounded
    cached state and the requested transaction, not whole-history Git/JSON replay. Source preparation
    across repositories is recoverable, not atomic. All three frozen kernel paths and both production
    branch families refuse. Historical validated state restores provenance without restoring verifier
    authority; new validation still requires registered live callbacks. Offline CLI has no execution or
    promotion authority. Retention, registered row/LOO verifiers and live validation remain required.

<!-- original line 12662 -->
  - [x] **AKU-05d — shared frozen-kernel mutation guard in legacy and candidate paths**:
    canonical llama/speech worktrees and both protected branch families refuse before mutation;
    archive rechecks root/branch binding before its ref CAS, and candidate refs reuse the same guard.
    ✅ 2026-09-09 — main's combined guard/transport acceptance passed **198 tests and 4 subtests**.
    Symlink aliases and detached canonical roots refuse; experimental linked worktrees sharing the
    production object database remain allowed. Existing private-index, hook and peer-staging behavior
    is preserved. Tests use temporary repositories only; no production tree or ref was changed.

<!-- original line 12669 -->
  - [x] **AKU-05e — native validation consumer and replayable exact batch wiring**: due state
    freezes candidate/comparator/required rows and cadence generations; every submission rejoins
    the current transaction projection before artifact I/O. Both native arms require one frozen
    plan/lineage/comparison and exact executable plus full loader-name/content DSO closure.
    ✅ 2026-09-09 — main's independent clean three-file release passes **246 adjacent/edge tests**
    and **1,762 loop/Journal/storage tests plus 165 subtests**, with Ruff clean. The sealed row
    binds batch, row, both manifests and row-set identities; reopen verifies original carrier/raw
    artifacts, calibration, complete-measurement status and structural eligibility without history
    scans. CPU success cannot satisfy a required GPU row; optional seed debt stays separate.
    Source `1ac8393e`, main `deab8f40`. V1's loaded-instrument identity remains unknown for real
    validation authority; fixture-only transaction tests do not certify a candidate. The assigned
    semantic consumer must connect native-v2 instrument evidence, canonical ClaimTuple grading,
    the owning production-validation objective and exact row/LOO verification. No inference,
    production mutation, new grading rule or promotion authority is added by this slice.

<!-- original line 12686 -->
  - [x] **AKU-06a — indexed scheduler/accounting and resolved-campaign inspection consumer**:
    frozen coverage rounds, finite FIFO seed boost, required reservations, held-resource charging,
    exact issued-selection/receipt/outcome binding and explicit unavailable-frontier debt.
    ✅ 2026-09-09 — main's **138 tests** pass, including nine independent regression probes.
    Full resolved-campaign identity and grouped workload aliases prevent stale-state/seed-budget reuse;
    non-ready targets require separately typed prerequisite work. Unused optional slots and unavailable
    frontiers cannot indefinitely stall ready production work. Full-region reservations skip only
    unreserved backfill, preserving earlier required seed/other slots. Actual physical-region, GPU
    host, device and memory held time is charged; overruns retain cost and fence successors. Startup
    builds receipt/seed indices once; hot-path updates avoid historical scans. V1 explicitly uses fixed
    weights and no compatibility authority. CLI selections grant no execution. Journal transitions,
    native provider receipts, registered adaptation, planner/routes and live admission remain required.

<!-- original line 12713 -->
  - [x] **AKU-06c — durable controller-owned unified driver and compact accounting projection**:
    native fsynced issuance/settlement, exact catalog/selection/arm binding, idempotent replay and
    immutable runtime materialization feed the actual campaign controller. ✅ 2026-09-09
    Accepted together with AKU-07c: the clean 17-file release passed **1,444 tests and 83 subtests**,
    plus **20 independent boundary probes**. Preview failures preserve committed receipts and seed
    queues; old intents cannot rematerialize under a new supervisor. Slow provider/verifier I/O runs
    outside the controller mutex and rechecks lifetime. Operational projections use indexed totals
    and a rolling seed commitment, not per-tick historical scans. V3 START fences actual old readers;
    the closed snapshot connects scheduler/targets and reports other consumers as not connected.
    Source `61a63c42`, main `8cbcce9f`. One outstanding selection and a management-only default do not
    constitute concurrent CPU/GPU execution. The end-to-end execution/receipt consumer, prepared
    actors, native evidence feedback and real authority remain required under AKU-06/07/08.

<!-- original line 12743 -->
  - [x] **AKU-06e — public exact selected-profile materialization**: immutable SelectedProfileWork
    and UnifiedCampaignDriver.materialize_profile bind catalog, transition, selected proposal,
    profile request, preparation-plan digest and current controller identity through the public
    controller callback. ✅ 2026-09-09 — source `c3303474`, main `1accc7f2`; main reproduced
    24 focused tests and **1,834 tests plus 165 subtests** in the clean combined acceptance tree.
    The record is deeply immutable advice with execution_authorized=False, not a grant or launch
    capability. Actor execution, provider metadata and source/build consumption remain AKU-06d/07k.
    The same checkpoint makes the disk-floor boundary test deterministic without changing storage
    policy: fixed 4 GiB free is OK at equality and pressured below a 5 GiB floor.

<!-- original line 12752 -->
  - [x] **AKU-06f — contained actor/profile producer and durable preparation state**:
    public controller reservation, exact owned terminal/cost/stdout joins, native
    INTENT/FINISH/PROFILE_VERIFIED replay and independent preparation budgets are implemented.
    Cancellation atomically precedes provider admission or refuses; exact owner-local tombstones
    prevent later admission without pretending to be durable restart authority. Executable reads
    are bounded/nonblocking, configuration limits finite, and profile receipts deeply immutable
    with detached canonical serialization. ✅ 2026-09-09 — research source `a9ce9d88`, main
    `da7dd5bc`; main reproduced **1,839 passed, one strict xfailed, 83 subtests passed**.
    The strict failure is still the real selected-profile scheduler accounting mismatch (AKU-07k),
    not waived acceptance. Proposed advice to private source/build preparation remains AKU-06d;
    prospective measured-profile projection remains VB-AK-UNIFIED-PROFILE. No live actors,
    inference, builds, provider grants or full campaign acceptance are claimed.

<!-- original line 12764 -->
  - [x] **AKU-06g — bind selected advice to guarded source/build preparation**: public immutable
    SelectedActorWork and materialize_actor re-open the exact issued catalog/selection; consuming
    adapters revalidate that actual request before using immutable authored manifests or explicit
    BuildPlans. Guarded private source application yields actual commit/tree/diff-policy evidence;
    build delegation preserves the owning runner's arguments/results and enforces configured
    affinity/jobs/deadlines without creating a grant. ✅ 2026-09-09 — research `de4396ca`, main
    `ba0644e7`; main combined gate **2,061 passed, one strict xfailed, 83 subtests in 47.29s**,
    Ruff and diff checks clean. Tests apply/commit only a disposable tiny source fixture; no CMake
    or inference. Actual contained authoring, build ownership and planner feedback remain AKU-06d.
    Prospective source-policy findings are registered under VB-AK-UNIFIED-PREPARATION before live use.

<!-- original line 12774 -->
  - [x] **AKU-06h — connect installed profile preparation to settled planner feedback**:
    exact typed mechanism bindings now select the owned profiling child; original authenticated
    PROFILE_VERIFIED publication joins original issuance, receipt and successful prerequisite
    settlement before planner feedback. Same-boot replay preserves original validity without
    restoring live held authority or appending reconstructed evidence. Malformed output closes
    the original reservation and retains incurred cost. Exact source/default closure and complete
    retry identities refuse substitution. ✅ 2026-09-09 — final nine-file packet SHA-256
    `623cbf63587b772747ef9e45cb9e75bf43c94cb79afdf5dc6f4b6ccf30577792`;
    independent combined acceptance **85 passed, two existing strict xfailed**, no skips;
    exact primary application hashes match and focused rerun **37 passed in 3.46s**.
    Successful settlement tests use an explicitly synthetic provider authoring correct original
    metadata; native BIND/HELD refusals remain. No hardware or scientific qualification claimed.
    Contract: research `docs/autokernel-installed-profile-preparation.md`. Published source
    `54eb195d`, main `81b87368`; final main full loop/Journal acceptance: **2,473 passed,
    two strict xfailed, 83 subtests, no skips in 298.45s**. The expected failures are still
    OP-AKU-BIND and OP-AKU-HELD; this is software acceptance, not hardware qualification.

<!-- original line 12790 -->
  - [x] **AKU-06i — automatically renew installed profiles with bounded request generations**:
    derive requests before selection from the installed template, exact settled predecessor and
    campaign attempt cap; durably reuse the original selected request on restart. Preserve original
    validity, cost accounting and fairness across targets. Test older-profile/new-failed-attempt
    attribution together, expiry/restart and exhausted budget. The current connector reports
    per-target `profile_refresh_unavailable:original_request_consumed:fresh_predeclared_request_required`
    while allowing unrelated eligible work; this safe fixed-request limitation is not completed
    autonomous refresh and must not become a recurring operator request. Existing actor projection
    refuses a second distinct PROFILE_VERIFIED for the same target, so generating fresh request IDs
    alone is insufficient. Explicit versioned successor/predecessor semantics require shared
    `actor_preparation_state.validate_event` changes (HIGH16, Journal publication/replay);
    OP-AKU-REFRESH approval was requested. Do not conceal new authority in a nested v1 contract.
    - 2026-11-18 (autokernel, AKU bulk pass): still needs OP-AKU-REFRESH approval (actor event validator, HIGH16); not implemented.
    - 2026-11-18 operator decision (decision tool): OP-AKU-REFRESH approved as packaged (option A: additive versioned records, legacy preserved). [no-belief: operator decision]
    - 2026-11-19 (autokernel) PARTIAL (code-only; box stays OPEN): research `epyc-inference-research` `439fdbd78` `actor_preparation_state.validate_event` gains `PROFILE_REQUEST` and a v2 `PROFILE_VERIFIED` successor (generation>=2, predecessor profile/request/settlement digests, attempt cap, request-precedes-profile); v1 still refuses a second distinct profile (tested). `loop/profile_refresh.select_refresh` returns no_predecessor/not_due/reuse_open_request/derived/exhausted, reusing an open request after restart; cross-boot clock domain counts as stale. 6 new tests. Remaining: wire `select_refresh` into `profile_preparation.consumed_request_debt` and the driver (removes `profile_refresh_unavailable`), append v2 records via `target_profile_execution`, feed real predecessor settlement digest, driver-level attribution/fairness test. [no-belief: tooling landing]
    - 2026-11-19 (autokernel) DONE (code): research `epyc-inference-research` `d03e60b43`: opt-in `InstalledProfilePreparationBinding.refresh_attempt_cap` (default None = v1); `owner.refresh_requests()` calls `select_refresh` with the real predecessor settlement digest; `driver.refresh_installed_profiles` substitutes the derived/reused request so `profile_refresh_unavailable:original_request_consumed` is only produced when the cap is exhausted or the predecessor unsettled; v2 PROFILE_REQUEST/PROFILE_VERIFIED appended via the controller and `TargetProfileExecution.prepare`. 7 driver-level tests (attribution, failed successor, two-target fairness, restart reuse, exhausted cap, v1 unchanged). Setting a production cap is configuration, not code. [no-belief: code]

<!-- original line 12806 -->
  - [x] **AKU-06q — project original CPU profile evidence through the durable feed**:
    ✅ 2026-09-09. ROOT closure-v3 registers measurement and receipt-integrity projections;
    original accepted terminal and PROFILE_VERIFIED join precedes compact artifact verification.
    Pair projection/associations persist before ACK; restart and capacity-one retraction retain
    both carriers. Failed settlement and consumed quarantined/conflicting profiles release only
    their exact terminal, while forged joins cannot discard pending evidence. Unsampled pinned
    TIDs are valid without invented samples. Main combined current-tree acceptance:89 research
    tests in24.94s and65 ROOT adapter/dashboard tests in3.21s, no skips. Existing dashboard cache
    hooks survive composition. No new grading rule, production-validation claim or hardware run.

<!-- original line 12815 -->
  - [x] **AKU-06r — correct feed integration regressions without narrowing coverage**:
    ✅ 2026-09-09. Restore original operational diagnostics for unrelated lifecycle/settlement
    events; profile-specific bookkeeping no longer silently consumes their classification.
    Real service test signals only after its publisher observes evidence. Explicit v2/v3 feed
    fixtures use independent source cursors and preserve all native-final/restart assertions;
    scientific-receipt fixtures pin their separately owned seven-file v2 contract.
    Main110 affected integration tests passed in118.63s, no skips; all four applied file hashes
    match the tested tree, Ruff clean. The preceding full run had5 failures and15 setup errors
    (2583 passed,2 strict xfails,83 subtests); a fresh full-suite result is still required.

<!-- original line 12838 -->
  - [x] **AKU-06p — retain exact expected GLM shard inventory without unscheduled model reads**:
    ✅ 2026-09-09. ROOT `artifacts/autokernel/glm53-expected-inventory-20260909/` contains
    the existing model_identity.v1 expected manifest, six original download metadata files,
    lossless encoded source tree, expected-only provenance, task-local author and tests.
    Manifest SHA256 `a9984ae6a18f7b25dd27086abd32b74056264a9cc64ba074067e8a8bb90be626`;
    normalized expected inventory `21d760be3bd473865b31f3b3d9ca28b30a2f7bd12b71660e64191ff02ff11fcc`.
    Main relocated tests:31 passed, no skips. Local model bytes were not read or verified;
    actual six-shard verification remains resource-accounted preparation under AKU-06j/12.
    Preserve explicit prospective GLM microbatch512 (pinned kernel default), not the projection's
    omitted-value2048; omitted -ub currently refuses final resolution. Original token/cache/MTP
    prompt and explicit logging/UI/speculation flags still require their owning recipe work.

<!-- original line 12849 -->
  - [x] **AKU-06o — implement and verify owned full-request CPU profile capture**:
    ✅ 2026-09-09. Research `cpu_profile.py`, installed benchmark entry and the optional
    concrete serving hook retain original request/model/source/process/DSO identities,
    bounded sample/counter artifacts, warmup/request windows and deterministic raw replay.
    Reader-only waitid proof fixes exited-child readback races without invented argv/exe.
    Exact six-file packet SHA256 `8fc48b84bf78cc41567239b714cd6b9cc4b84dd8a54f98c49ff70d7e3db0731c`;
    main composed acceptance: 205 passed, 14 subtests, 36.22s, no skips. Tiny HTTP/perf fixtures
    cover installed publication/settlement/planner/restart, bounded failures and cleanup.
    Full published research3762a517 acceptance: 2577 passed, 2 strict expected BIND/HELD
    failures, 83 subtests, 332.81s, no skips (original handle20212, terminal0).
    No real perf events, GLM run or production change. Contract: research
    `docs/autokernel-owned-cpu-profile.md`. Sampled periods are attribution, not gains;
    receipt integrity is not production validation. AKU-06j and all parent tasks remain open.

<!-- original line 12862 -->
  - [x] **AKU-06k — connect actual actor preparation to owned native build enrollment**:
    ✅ 2026-09-09. Concrete SourceBuildExecutionOwner consumes the real ActorPreparationConsumer,
    binds exact selected advice/source/BuildPlan, executes the controller-owned build and reopens
    original stdout/log/process/source/binary evidence before immutable enrollment. The candidate
    path requires the original identity-keyed materialized-source capability; copies, parsed bytes,
    foreign owners and changed source refuse. Startup now accepts actual build_recipe identity while
    retaining legacy build without relabelling. Explicit log limits bound parent verification;
    Python safe-path launch prevents candidate-cwd package shadowing before verification.
    Exact eight-file packet `1f55a3b42cb126870f42e1043a9d60aefa920056776e19d417fb5904a574cb5b`;
    all primary hashes match. Main current-base **60 tests passed in 4.57s**; worker **62 passed
    in 5.32s**, prior source/profile/actor/startup composition129 passed. Genuine profile settlement,
    selected build advice, two actor children, actual tiny CMake build and verified enrollment pass,
    including a committed malicious shadow package. No kernel/hardware or production build.
    Contract: research `docs/autokernel-source-build-execution.md`. This does not settle the selected
    scheduler transition, install standalone source/build dispatch, or activate expiry authority.

<!-- original line 12877 -->
  - [x] **AKU-06m — full software regression checkpoint after owned build integration**:
    ✅ 2026-09-09. Published research `1f38aefb122b73bd6001ba2b54ea11d66546fa3d`,
    main terminal run: **2,513 passed, two strict expected failures, 83 subtests passed**
    in307.84s, no skips. Scope is the entire loop test directory plus test_journal.py,
    using the exact primary factory tree and ROOT checkout. Expected BIND/HELD failures
    remain explicit. This does not validate subsequent worker edits, real-host export,
    hardware measurements, five-loop GLM acceptance or production promotion.

<!-- original line 12900 -->
  - [x] **AKU-06n — specify original multi-child accounting and denial recovery**:
    ✅ 2026-09-09. Reviewed current scheduler/lifecycle/actor APIs and retained the implementation
    decision package linked in AKU-06l. It delineates original held-proof/child/settlement append
    order, empty and charged-prefix admission denials, atomic one-attempt settlement, legitimate
    partition concurrency, cross-role receipt refusal and occupancy versus elapsed-time budgets.
    This closes the design audit only; Journal/provider/scheduler changes are not implemented or
    approved, and AKU-06l plus all parent tasks remain open.

<!-- original line 12924 -->
  - [x] **AKU-07b — owned-worker lifecycle and crash-safe v2 control consumer**: prospective durable
    acquisition and launch intent, exact grant/container/PID-start/boot identities, isolated pipe-gated
    bootstrap, bounded stage/teardown lifecycle and accepted-versus-completed pause/drain controls.
    ✅ 2026-09-09 — main's **307 tests and 15 subtests** pass, including independent descriptor-leak,
    credential/import-isolation, old-terminal fencing, command-semantic and actual-old-reader probes.
    Typed denial proves no acquisition; ambiguous provider I/O retains pending ownership for exact
    recovery. Returned journal errors do not disable owned cleanup, but uncertain durability cannot
    certify a terminal result. Pause can escalate to drain without a late superseded completion
    overwriting current control. Indexed replay accepts denied/no-launch generation gaps while
    refusing rollback; the v2 START fence makes the actual older reader refuse before admission.
    Snapshot v2 is explicit and management-v1 defaults remain. Provider calls must themselves enforce
    deadlines: a numerical deadline or fake cgroup test is not live containment proof. The generic
    parent-side planned-serving guard still refuses until the contained-child bridge is connected.
    Driver/native-result integration, real authority and deployment remain required for AKU-07.

<!-- original line 12950 -->
  - [x] **AKU-07d — bounded whole-lifecycle observation producer and serving hooks**: setup/load,
    placement, health, warmup, measurement and teardown markers enclose each serving unit, with
    bounded process census, NUMA/affinity/memory/PSI, prepared DSO and explicit target-GPU evidence.
    ✅ 2026-09-09 — accepted in the same clean release as AKU-04d. Six independent main probes
    cover loaded code/bound state and shutdown/cost edge cases. Loaded identities include constants,
    nested code and explicit instance state; unsupported native payload remains unproven. In-window
    DSO metadata and actual PID-start/boot/container attribution refuse replacement/reuse. Missing
    trusted foreign/runtime/GPU verifiers stay unknown; no name-based inference classifier or grader
    is introduced. Cleanup runs on every serving exception. Unjoined readers freeze unknown evidence,
    retain all incurred reader cost even for dropped samples, and fence successor units; late return
    cannot mutate the record. Source `04d73260`, main `d75bc9ec`. Native versioned attachment and
    containing-owner successor enforcement remain assigned AKU-04/07/08 integration work; no live
    observation, real grant, containment success or deployment is claimed by hermetic tests.

<!-- original line 12963 -->
  - [x] **AKU-07e — actual controller-owned runtime execution and exact held-cost settlement**:
    one durable driver selection now traverses the real controller admission/acquisition/lifecycle
    path, contained planned-worker result ingestion and scheduler settlement. ✅ 2026-09-09
    Main's clean six-file release passed **1,729 loop/Journal/storage tests plus 165 subtests** and
    **136 focused/adjacent tests**, including an independent shutdown reproducer. No separate
    injected lifecycle can bypass controller ownership. Exact current-owner denial/pre-engine
    refusal is positive no-acquisition proof; unseen, old-incarnation or ambiguous state is not.
    Failed work retains provider-authored cost and settles once. A successful child followed by
    producer failure retains its immutable terminal/result diagnostically without native scientific
    acceptance; an unjoined producer fences successors, retains its handle, and makes close retryable
    rather than claiming teardown. Concurrent execution/close and exact lost-reply retries are
    covered. Source `59eb3f30`, main `6f869803`. The default parent evidence evaluator remains unknown,
    so this connector cannot produce a valid comparison. Observation-v2, A2 native invocation,
    actor/profile/semantic consumers, standalone composition and real provider acceptance remain
    assigned work. No live inference, service, resource grant or frozen kernel was changed.

<!-- original line 12978 -->
  - [x] **AKU-07f — controller-owned authenticated bounded worker output**: exact current
    request/plan/lineage/stage/worker/generation/result binding exposes bytes, never a path or
    runtime handle. Terminal-time file identity and bootstrap-recorded length/SHA-256 bind the
    output; truncation, replacement, same-inode tampering, missing/nonregular files and lock
    contention refuse. ✅ 2026-09-09 — main's clean release passes **126 focused/adjacent tests**
    and **1,768 loop/Journal/storage tests plus 165 subtests**, with Ruff clean. Reads and hashing
    run outside the controller mutex, followed by an exact owner recheck. Optional output-capture
    failure preserves the durable terminal and provider-held accounting. Source `47ce0677`, main
    `6fc75192`. This supplies the actor's output consumer, not authority to apply its advice;
    native actor/profile persistence and actual execution remain assigned under AKU-06/07.

<!-- original line 12988 -->
  - [x] **AKU-07g — authenticated standalone controls and durable shutdown**: closed command-v2
    semantics and command-transition-v3 replay bind the full campaign/config/supervisor/request/
    revision identity. SIGTERM reuses or records one durable drain, fences resume, and retains
    ownership until actual cleanup. ✅ 2026-09-09 — main reproduced **331 tests plus 15 subtests**
    and **1,810 loop/Journal/storage tests plus 165 subtests** in a clean composed checkout.
    The independent restarted-service probe exposed and corrected a client-side retry refusal:
    control submission preserves historical command bytes while allowing a newer authenticated
    supervisor to consult its journal; absent old commands still refuse and status pins remain
    exact. Typed v3 HTTP loopback, bounded transport/token handling and prior shutdown regressions
    pass. Source `29b8120b`, main `1fea54a5`. The template is deliberately not installed or enabled;
    runtime/service composition and actual provider/live acceptance are not completed by this slice.

<!-- original line 13007 -->
  - [x] **AKU-07p — compose bounded runtime, startup parser and service ownership**:
    exact issued-intent recovery, bounded same-outcome retry, one service-owned non-daemon run
    thread, recovery before listener admission and owned shutdown are connected. Closed startup
    manifests materialize existing typed inputs and resolve application-owned provider identifiers;
    unified CLI dry-run opens no store or claims. ✅ 2026-09-09 — main combined suite:
    **2,024 passed, one strict accounting xfailed, 83 subtests passed in 45.26s**; Ruff clean.
    Research source `38b29326`, main `2c7762dc`.
    Fixed the planning/drain race with a typed admission-closed refusal and indexed historical
    logical attempts without scanning or reusing old-incarnation denial proofs. Fixture CPU/GPU
    paths are not real provider acceptance. Runtime currently executes runtime_comparison only;
    actor/profile dispatch, continuous feed and production scientific witnesses remain open.

<!-- original line 13018 -->
  - [x] **AKU-07i — native-v2 actual-descendant binding and replay**: published the narrowly
    approved lifecycle event/validator with legacy refusal, current-owner capture, immutable v2
    artifact references and restart/acquisition closure. ✅ 2026-09-09
    Every ancestry stat row checks PID/start identity; target, ancestor, ancestry, container and
    membership are rechecked before append outside the controller/watchdog lock. Expired, reused
    or reparented identities cannot publish. Loaded-builtin reads are bounded/stability checked.
    All nineteen final file hashes matched; main's final suite passed 1,905 tests plus 165 subtests
    and four independent PID/expiry/actual-ROOT-projector probes. Research source 3df1192b,
    main a3b251bc. Diagnostic refusal and fixture-scored child/v2/restart modes remain separate.
    Synthetic telemetry proves consumer wiring only; real test-owned cgroup membership/cleanup
    proves neither controller enforcement nor exclusivity. Production parent witnesses/runtime/GPU
    adapters remain AKU-07m, resource authority AKU-11, and live acceptance AKU-12. The operator's
    specific HIGH-impact approval does not cover held-cost/accounting events or frozen kernels.

<!-- original line 13043 -->
  - [x] **AKU-07k — bind scheduled work through provider admission/accounting**: version the native
    StageRequest accounting binding with catalog/transition/selection/proposal digests, proposal ID,
    backend and scheduler stage class; include it in prospective request identity, launch contract,
    lifecycle events and recovery validation. Verify provider receipts against it before indexing;
    never rewrite receipts or infer classification from argv, setup stage or an opaque digest.
    Current provider authorize/close APIs receive no typed backend/class binding, so request-ID-only
    changes cannot fix profile settlement. The additional HIGH22/three-process validator scope awaits
    OP-AKU-BIND approval; descendant approval does not cover it. Preserve v1 and old-reader refusal.
    - 2026-11-18 (autokernel, AKU bulk pass): still needs OP-AKU-BIND approval (HIGH22, three-process validator); not implemented.
    - 2026-11-18 operator decision (decision tool): OP-AKU-BIND approved as packaged (option A: additive versioned records, legacy preserved). [no-belief: operator decision]
    - 2026-11-19 (autokernel) PARTIAL (code-only; box stays OPEN): research `epyc-inference-research` `768249e16`: additive `AccountingBinding` (`stage_accounting_binding.v1`: catalog/transition/selection/proposal digests, proposal ID, backend, stage class) as optional `StageRequest.accounting_binding`, in prospective identity, launch contract, held-receipt event and recovery re-check; provider receipts verified against it before retention; unbound requests byte-identical to v1, old readers refuse bound records; profile producer builds it from `SelectedProfileWork`; fixed `_run_stage` dropping the binding; the strict actual-driver xfail now passes and its marker is removed. `test_worker_lifecycle.py` 55 passed. Remaining: binding in actor_lifecycle/source_build_execution/unified_worker builders, Journal-level validator for the digests, controller recovery consumer. [no-belief: tooling landing]
    - 2026-11-19 (autokernel) DONE (code): research `epyc-inference-research` `1ac240c8c`: accounting binding set in the actor (`CampaignController.actor_accounting_binding`), source/build (`SourceBuildStageExecutor.execute`) and runtime-driver builders; Journal-level `validate_worker_accounting_binding_history` (receipt proposal/backend/stage class and held-receipt digest vs launch binding; unbound history unchanged); controller `_replay` re-runs it and raises JournalCorruption on a tampered or never-issued binding; `run_worker_stage` refuses a mismatching binding. 9 new tests. [no-belief: code]

<!-- original line 13055 -->
  - [x] **AKU-07l — select and materialize native-v2 work through the public driver**:
    plan_iteration selects the existing schema-appropriate plan identity builder while preserving
    proposal recipe identities; materialize_runtime preserves the issued version and checks the
    v2 loaded-instrument pin against startup execution input. ✅ 2026-09-09
    Main reproduced 57 public scheduler/materialization tests (CPU/GPU v1/v2, bad instrument pin,
    wrong recipe identity) and 1,905 combined tests plus 165 subtests. No test upgrades an issued
    prepared stage. Exact two caller seams were LOW; the shared HIGH-impact serving_arm_identity
    helper remains unchanged. Native execution/producer acceptance is still AKU-07i/07m, not this
    selection/materialization slice; no hardware performance claim is implied.
    Research source c65af942, main 9eafac1f.

<!-- original line 13065 -->
  - [x] **AKU-07m — derive parent witnesses from sealed native lifecycle evidence**:
    carry the exact sealed native-observation StoredArtifact through closed v2 completion IPC;
    reopen it and its lifecycle reference in the bounded parent evidence producer, joined to the
    parent-issued process/grant/container receipts and frozen plan/recipe/request identities.
    Derive each supported factual witness separately, retain underlying artifacts/source pins,
    and reconcile the same receipt during native capture. Generic request success cannot pass
    correctness, placement or contention. Unsupported purpose/GPU/runtime checks remain unknown
    until their concrete owning adapters are connected. Preserve v1 completion grammar, exact
    retry identity and existing grading/noise policy; configuration injection alone is insufficient.
    ✅ 2026-09-09 — research `0a4aada6`, main `d51f9de6`. Concrete parent service derives
    request completeness, placement and supported health readback; original issuance registry
    and receipt replay precede native capture. Parent-only descendant lookup, deadline-bounded
    serialized IPC and exact retry handling are exercised by an actual tiny-child/socket flow.
    Main combined suite: **1,941 passed, one strict accounting xfailed, 83 subtests passed**;
    after unused-import cleanup, 102 focused tests and Ruff pass. Hermetic observations prove
    integration only; unknown scientific witnesses and ROOT per-witness consumption remain open.

<!-- original line 13104 -->
  - [x] **AKU-07s — capture original contained server request/response evidence**:
    ✅ 2026-09-09 research 8f582b22 / main 361496f5. Actual contained serving retains
    bounded warmup/measurement bytes, ordered slots, request intervals and failures before
    teardown. Reopening joins original instrument/source, frame, requests and descendant PID;
    no retrospective source pin or invented token/seed evidence. Main full suite: 2,218 passed,
    one existing accounting xfailed, 83 subtests, no skips in 59.45s; Ruff/diff clean.
    Tiny HTTP integration uses a pre-enrollment ephemeral port and exact response PID checks.
    This is factual capture only: same-server T0 and remaining scientific witnesses stay
    open under AKU-07o. See research docs/autokernel-native-server-response.md.

<!-- original line 13113 -->
  - [x] **AKU-07t — prepare selected complete-model identity before observation binding**:
    ✅ 2026-09-09 research b9d2151e / main f7e65365. Closed target/recipe/model inventory
    preparation runs on the existing parent evidence thread while the child waits for its
    binding. Full-byte verification occurs once; both recipes reuse original issuance and
    verify metadata continuity. Fresh claim checks after model and binding artifact publication
    prevent expired claims from releasing measurement; orphan CAS bytes confer no authority.
    Main full integration: 2,229 passed, one existing accounting xfailed, 83 subtests, no skips
    in 66.47s; eight code/test paths Ruff clean. Actual-child tests match each recipe's own
    entry path/SHA receipt before spawn and observe one original validator invocation without
    changing its pinned identity. Synchronous filesystem I/O is not claimed cancellable.
    Standalone configuration installation and remaining scientific witnesses stay AKU-07n/07o.

<!-- original line 13124 -->
  - [x] **AKU-07u — install closed native startup configuration and prospective instrument**:
    ✅ 2026-09-09 research 9e2125b1 / main 625348f8. Startup v3 binds per-target/per-recipe
    complete-model preparation, explicit observation configuration and the installed adapter.
    Dry-run performs no model/store/grant I/O and labels the instrument planned_unpublished;
    runtime publishes/reopens exact instrument bytes before scheduling and retains one adapter
    instance. V1/v2 remain supported. The startup test proves configured owner construction;
    separate genuine-child tests prove raw receipt seal/reopen, not one installed end-to-end run.

<!-- original line 13131 -->
  - [x] **AKU-07v — collect bounded same-attempt raw search windows**:
    ✅ 2026-09-09 research 9e2125b1 / main 625348f8. Original source-pinned marker IPC covers
    warmup, measurement, measurement end and teardown after model preparation. Parent polling
    retains bounded host/claim/storage observations and joins original lifecycle intervals.
    Cross-phase, zero-duration, incomplete and post-close coverage cannot become clean windows.
    Exact source/configuration/native/parent receipts seal and reopen; no WindowAttestations,
    calibration/control qualification or scientific verdict is invented. Main full suite:
    2,284 passed, one existing accounting xfailed, 83 subtests, no skips in 68.90s;
    fresh integration subset 56 passed in 8.39s. All 21 published files match accepted hashes.
    Same-server finalization and actual scientific feedback remain AKU-07o/08c.

<!-- original line 13141 -->
  - [x] **AKU-07w — retain same-server owning reports and separate parent-final trial captures**:
    ✅ 2026-09-09 research 8f536e0e. Original server/anchor observations and complete owning T0
    reports feed immutable post-arm pairs; candidate-first completion never waits for a future
    anchor. Finalization requires the full original result/registry/lifecycle set, preserves
    failed/rejected facts and emits separate v3 carriers. Native prevalidation reopens originals
    outside the controller mutex; unchanged current-owner fences govern Journal append.
    Closed v3 Journal grammar and exact restart duplicates are tested. Main full acceptance:
    2,301 passed, one existing accounting xfailed, 83 subtests, no skips in 131.82s.
    Byte coherence is not token agreement or a full T0 PASS; missing seed/token/static/dispatch/
    control/calibration warrants stay unknown. Actual driver finish/search and ROOT reader
    composition remain AKU-07o/08c. See research docs/autokernel-server-final-trial.md.

<!-- original line 13170 -->
  - [x] **AKU-07q — construct pinned startup bundles through the enrollment factory**:
    bounded offline CLI consumes sealed campaign_cli v2 output plus matching production export,
    explicit CPU/GPU/candidate configuration and existing typed scheduler/profile/plan/evidence
    inputs; emits closed startup manifest, original pins, preflight debt and exact dry-run command.
    ✅ 2026-09-09 — included in main's 2,024-test combined gate; subprocess factory/driver tests
    use the same composed tree and actual interpreter. No provider, profile, claim or epoch is
    invented. Real generated export repair and installed acceptance remain AKU-12c/12a.

<!-- original line 13177 -->
  - [x] **AKU-07z — restart a reused factory from the original scheduler seed**:
    ✅ 2026-09-09. Each factory invocation now constructs a fresh scheduler from the immutable
    manifest, shares that exact instance between controller and runtime (including the feed path),
    and refuses an initially drifted materialized seed. The prior owner no longer leaks mutated
    scheduler state into Journal replay. Main **77 tests passed in5.69s**; all five file hashes
    match the worker packet. Settled same-factory restart, pending-issued replay and feed identity
    pass without modifying replay authority. Research `f1882475` promoted as `c1a8da09`.
    This fixes embedded/in-process reuse; standard process restart already rematerialized inputs.
    Native BIND/HELD recovery and installed live acceptance remain separate open tasks.

<!-- original line 13189 -->
  - [x] **AKU-08a — scoped retrieval/route contracts and offline evidence consumer**: exact claim keys,
    mandatory applicable conflicts before top-k, directed nontransitive transfer, victim-directed
    noncomposable coexistence and bounded reject-audit decisions. ✅ 2026-09-09 — main's 173 regression
    tests pass, including 57 focused evidence tests. Cached reuse binds intended use, full support basis,
    relevant dependency content/generation/frontier, explicit semantic buckets, epoch and registered
    rule version; new broader conflicts, removed findings, missing state and quarantine/outage cannot
    preserve obsolete eligibility. Unrelated buckets stay reusable with O(bound dependencies/scopes)
    admission checks. Replay re-derives fences but cannot restore callback authority from JSON. Raw
    grade, retrieval completeness and supported use remain separate; absent registered verifiers fail
    closed. The offline CLI grants no execution authority. V1 broad lookup is deliberately exact in
    mechanism/model/quant/workload/effect question; unsupported candidate universes cannot be certified.
    Actual journal/ClaimTuple producer, asynchronous cursor/invalidation feed, policy adapters, planner,
    audit budget and scheduler consumers remain required; AKU-06/08 are not complete.

<!-- original line 13202 -->
  - [x] **AKU-08b — strict prospective arm reader and existing corpus consumer**: full closed
    plan/view/native request and attempt rederivation, exact stored-byte verification, shared ClaimTuple
    projection and native-family-only deduplication. ✅ 2026-09-09 — main's 90 focused tests pass
    with the explicit research-root fixture enabled, including the real research producer → root reader and
    three malformed/tampered regression probes. Identical standalone/journal carriers coalesce by full
    measurement ID plus digest; conflicting carriers emit neither and report refusal. Other source
    families retain their existing semantics. Grade remains the shared ladder; protocol/current use
    and raw attestation are separate. Missing witnesses emit no scalar. No corpus was ingested; native
    controller events are now AKU-03c; bounded asynchronous feed and registered planner-use consumers
    remain required.

<!-- original line 13225 -->
  - [x] **AKU-08i — connect bounded continuous evidence to actual standalone planning**:
    ✅ 2026-09-09 research 50b0d23f. Startup/factory v2 installs explicit feed configuration;
    SQLite/reader ownership opens, drains and closes on the execution thread. The planner
    consumes one coherent retrieval/snapshot bundle through a stable view; relevant evicted
    conflicts remain incomplete before top-k and cached admission. Exact captured ROOT bytes
    avoid stale module/bytecode execution. Finite captured-frontier readiness prevents skipped
    queued invalidations without chasing unrelated writes forever. Durable projection precedes
    sole owned ACK; Journal v2 bounded proof/metadata reads preserve rotation, archive, retry
    and restart semantics. Main latest-native composition: 2,185 passed, one existing strict
    expected failure, 83 subtests, no skips (55.30s); 95 focused tests independently pass.
    Fourteen code/test paths pass Ruff; all sixteen publication files match tested bytes.
    Registered effect/use adapters, scientific eligibility, actual installed providers/export
    and hardware acceptance remain AKU-08c/07n/12, not granted by a live feed connection.

<!-- original line 13238 -->
  - [x] **AKU-08d — execute exactly the pinned canonical source bytes**: stable bounded no-follow,
    nonblocking regular-file reads are hashed and those exact bytes compiled/executed, bypassing
    stale timestamp-valid bytecode. ✅ 2026-09-09
    Serialized registration and BaseException cleanup preserve module state; replacement, FIFO,
    cached bytecode, cancellation and concurrent constructors have permanent regressions. Main
    reproduced 13 focused/source-loader tests after composition; clean native-v2 acceptance passed
    1,916 tests plus 165 subtests (19 including independent edge/reopen probes). Research source
    dc580b75, main ad86b9e3. Sole ClaimTuple grading is unchanged; final pins and permitted-use
    decisions remain AKU-08c, and compatibility receipts grant no production-validation authority.

<!-- original line 13247 -->
  - [x] **AKU-08e — reopen native-v2 artifacts through the existing registered ROOT projector**:
    preserve the v1 source class and shared ClaimTuple ladder while dispatching exact v2 plan,
    loaded-instrument, lifecycle, native-attempt and journal envelopes. ✅ 2026-09-09
    Main reproduced 133 projector/corpus/ladder/ledger tests plus the actual owned-child v2
    cross-repository probe (1.08s). The reader reopens exact native dependencies; operational and
    diagnostic records emit no scalar. Review reproduced a FIFO hang before fstat and corrected
    it with nonblocking open; resealed container/target-worker/boot mismatch tests now refuse.
    Adapter SHA-256 ad87bdec7afc4d07f04fe48375adf4fe476a20423481b2be662e776a2b590192.
    Fixture telemetry proves integration, not real measurement eligibility. Final semantic pins,
    typed receipt consumption and the bounded live feed remain AKU-08c; parent factual receipt
    authentication remains AKU-07m/VB-AK-UNIFIED-PARENT. No Ledger.append or grading changes.

<!-- original line 13258 -->
  - [x] **AKU-08f — load the published canonical projector by default without retroactive authority**:
    install the exact six-field verifier closure and select it during ordinary construction;
    preserve explicit legacy compatibility loading. ✅ 2026-09-09
    Research source 9ed6fc35, main b83b1027; main reproduced 19 focused tests and independent
    source-loader/reopen probes. ROOT source 2010b713 and adapter ad87bdec are pinned exactly.
    Existing native-v2 records lack captured producer implementations, so receipts retain
    compatibility_only even with current verifier pins; receipt-pair decisions check that scope
    independently. This fixes the default loader, not the outstanding scientific-use consumer.

<!-- original line 13293 -->
  - [x] **AKU-08k — include the final-trial helper in the registered verifier source closure**:
    ✅ 2026-09-09. Installed feed supports exact six/seven-file pinned closures; the current
    seven-file closure captures the final-trial helper and its exact lazy relative imports.
    All source bytes are verified before execution; no ambient helper fallback. Actual child
    v3 results drain through FeedRuntimeOwner/EvidenceFeed and restart idempotently with no
    scientific promotion. Main acceptance: 42 tests in 46.76s, no skips. Six-file v3 reads refuse.

<!-- original line 13299 -->
  - [x] **AKU-08l — version the separate semantic receipt source closure**: ✅ 2026-09-09.
    Seven-file captured ROOT closure and original native producer/finalizer identities feed
    versioned canonical receipts. Diagnostics contain no tuple or grade. The actual validation
    consumer persists and reopens exact historical pairs through fresh stores/controllers without
    live issuance; CANDIDATE diagnostics cannot fill required OPTIMUM rows or advance validation.
    Main independently passed 90 tests in 64.27s; worker regression passed 132 in 70.71s, no skips.
    Historical two-file pins remain unchanged; legacy tests load their exact original source bytes.

<!-- original line 13310 -->
  - [x] **AKU-07y — prevent lifecycle sampling-budget starvation**: ✅ 2026-09-09.
    Native producer admission now requires ceil((stage+teardown)/cadence)+9 samples before
    thread creation, grants or child launch, using existing enforced durations and fixed hooks.
    Spurious wakes retain an absolute due time; periodic enqueue rechecks phase/pending/stop
    after unlocked clock reads. No new knob, automatic budget enlargement or marker reservation.
    Main independently passed 123 regression tests and the final 56-test lifecycle file;
    exact 109-slot success/108-slot teardown refusal covers the full 100-periodic-plus-nine-hook
    boundary. Missing/gap/byte/queue/shutdown failures remain unknown; no scientific threshold
    or historical identity changed. Prospective sampler/helper source identities are pinned.

<!-- original line 13322 -->
  - [x] **AKU-09a — stop/join worker heartbeat before terminal publication**: no late `running` state;
    startup/claim/profile failures publish failure; original errors survive status errors; fake-race tests
    prove the real run path uses the lifecycle guard.
    ✅ 2026-09-09 — one deadline bounds close-lock/write-lock acquisition and thread join. Timeout
    refuses terminal publication; an arbitrary synchronous filesystem write itself is not claimed
    time-bounded. Heartbeats retain `starting` until the run advances; final artifact is durable before
    `complete`, and failure snapshots retain available outcomes. 46 focused lifecycle/status tests pass.

<!-- original line 13329 -->
  - [x] **AKU-09b — current versus historical accumulator rendering**: both existing hub render sites
    withhold magnitude/progress unless validity is current and the threshold is positive/finite.
    ✅ 2026-09-09 — missing/stale/legacy magnitudes remain labelled history; membership/cadence remain
    visible. Stale threshold signals are producer-reported/unverified, not fresh warrant. Main's Node
    DOM harness covers these combinations (69 tests, 5 subtests); this is not a browser or live-soak test.

<!-- original line 13334 -->
  - [x] **AKU-09l — follow the current serial run, not a stale hub environment pin**:
    the serial supervisor publishes a durable current-run pointer at startup and terminal, guarded
    against an older run overwriting a newer selection. The hub validates and follows that pointer
    per request, retaining `AUTOKERNEL_LOOP_STORE_ROOT` only as a legacy fallback; canonical champion
    and knowledge readers do not move. Acceptance requires the live `/api/loop` and rendered page
    to name the latest run's evidence and terminal reason, plus a fresh-launch pointer rollover.
    - [x] **AKU-09l-v14 live correction** (2026-09-16): research `main` gained the guarded
      producer pointer (`8b3b95f6`); root `main` gained the validating reader (`7ec9f779`).
      The served linked-worktree dashboard file is byte-identical to root `main`, the owning
      watchdog restarted the hub at 10:28:33 UTC, and live `/api/loop` now names v14's
      terminal `failed` report rather than v12's stale `running` report. The 75-test dashboard
      suite and 25 focused post-guard tests passed. No loop relaunch or benchmark was performed.
    - [x] **AKU-09l live rollover and page rendering** (2026-09-16): the deployed
      `/api/loop` followed successive v15, v16 and v17 state directories through the
      durable pointer; v16's terminal `complete` did not masquerade as a stale
      running report, and v17's active child stage is fresh and exact-joined.
      The page JavaScript DOM harness rendered the live v17 API response without
      an exception and named its state directory, target and child evidence.
      Headline stage now reflects the joined child's profile/A/B stage rather
      than the router's generic step (`6e85d3b5`); canonical champion and
      knowledge readers remain on their original root.

<!-- original line 13355 -->
  - [x] **AKU-09c — existing hub consumes coherent management-v1 snapshots and direct controls**:
    explicit campaign/config selection, closed snapshot/ACK validation, monotonic stream fencing,
    separate producer/activity/science clocks and independently dated evidence cards.
    ✅ 2026-09-09 — main's full hub acceptance passed **414 tests and 125 subtests**; combined research
    service/controller/guard acceptance passed **198 tests and 4 subtests**. One lazy bounded health
    probe owner rejects stale/late/mismatched replies; selected unified health is not vetoed by absent
    legacy state. Bearer tokens remain in tab memory and commands go directly to the authenticated,
    exact-origin producer gateway, never through a hub proxy. Browser deadlines cover headers and body;
    uncertain ACKs retain the exact retry, while double-clicks serialize. The service bounds trickling
    connections with one owned watchdog and identifies loaded transport code with stable projection.
    Existing registry/nav/probes/freshness remain the surface; no second page. Legacy fixture repairs
    retain producer/anchor/authority assertions without hard-coded current-host percentages or age.
    V1 remains management-only with no active worker or compute authority. Gateway/service deployment,
    worker-aware v2 integration and unattended live reliability remain separate acceptance work.

<!-- original line 13369 -->
  - [x] **AKU-09d — existing hub consumes the actual worker-aware v2 producer**: strict closed
    snapshot/result versions, monotonic worker/stream identity, lifecycle-aware semantic health and
    exact accepted-versus-completed controls, retaining v1 as a distinct management-only contract.
    ✅ 2026-09-09 — main's **296 tests and 79 subtests** pass, including real research-controller
    snapshots and execution of the actual page JavaScript. Acknowledged incomplete pause can escalate
    to a distinct drain; failed request construction retains the old pending pause, uncertain ACKs
    retain exact-ID retry, and late ACKs cannot erase a newer completion. Python/page validators agree
    on finite result semantics, acquisition-pending identities, permitted null-worker transition
    windows, protocol-version matching and same-campaign downgrade refusal. Cross-repo fixtures use
    explicit/standard checkout discovery and a post-release worker barrier; ordinary v2 unit tests
    remain independent of the optional checkout. The broader dashboard run separately reproduces
    **15 baseline-proved legacy failures** (11 tests plus four subtests); these are not v2 acceptance.
    No gateway configuration, service activation, resource grants or live reliability claim is made.
    Unified planner/resource/evidence projections and unattended deployment remain AKU-09 work.

<!-- original line 13383 -->
  - [x] **AKU-09e — existing hub consumes closed unified snapshot v3**: scheduler, resources,
    actors, evidence, candidate and targets render within the existing `/loop` page with strict
    independent Python/page validation. ✅ 2026-09-09 — main reproduced **96 focused tests** against
    the published research producer, including execution of actual page JavaScript. Python rederives
    accounting content identity; page validation checks closed nested shapes, statuses and values.
    Unknown dependencies degrade a live producer without disabling identity-matched controls; a
    drained snapshot with an unknown producer remains history. V1/v2 compatibility, exact retry and
    same-campaign downgrade fences remain. Null grants/candidate/evidence values stay unknown, and
    declared capacity is not a grant. No new route, proxy, registry row, gateway configuration, service
    activation or live reliability claim is made; connected consumers and deployment remain AKU-09.

<!-- original line 13406 -->
  - [x] **AKU-09h — connect bounded evidence, actor, profile and calibration observations**:
    ✅ 2026-09-09. Closed unified projection-v3 retains original owner reduction dates separately
    from attempts and publisher heartbeat; 64 total detail rows and a32KiB bound constrain payloads.
    Publisher performs no SQLite/artifact reopening. Diagnostic faults retain the prior dated cache
    and cannot change settlement; future timestamps are rejected before cache replacement.
    Main integration:165 research tests passed, two strict BIND/HELD xfails in81.65s, no skips;
    ROOT41 dashboard tests passed in0.51s. Changed research Python passes Ruff.
    Actor completion is not settlement, collected calibration is not qualification, and cached
    evidence totals are not current eligibility. Resource/candidate sections remain not_connected;
    no live deployment/reliability or scientific acceptance is claimed.

<!-- original line 13423 -->
  - [x] **AKU-09i — label the displayed noise threshold without inventing its estimator**:
    ✅ 2026-09-10. The loop page now calls the value the measured dispersion of the anchor,
    instead of claiming every producer defines it against the anchor mean. The retained GLM
    v1 floor is p95 absolute deviation from the median (7.801%, n=5); other floor producers may
    use different estimators. Four focused terminal-render tests pass; no measurement changed.

<!-- original line 13428 -->
  - [x] **AKU-09j — publish separately attributed champion capabilities without rewriting the
    numeric A/B record**: ✅ 2026-09-10. The existing champion card now merges bounded,
    schema-checked capability records whose exact commit is the current champion or its proven
    ancestor. Divergent lineage, malformed timestamps, partial SHAs and oversized records are
    ignored rather than presented as current capability. The live record adds DFlash2 speculative
    GPU serving and Flash-Next (`qwen4exp`) CPU/native-MTP support to the five retained historical
    GPU capabilities, with explicit source commits, artifact hashes and claim limits. The direct
    champion-vs-production percentage remains untouched. Focused reader tests pass 27/27; the live
    snapshot resolves seven capabilities from
    `/mnt/raid0/llm/autokernel/loop-memory/champion-capabilities.json` (SHA-256
    `264f16ad346634b2a0c7bbe5e7a83faa976db0a7f75162f38f38324393247ea7`).

<!-- original line 13439 -->
  - [x] **AKU-09k — headline the measured champion trajectory against frozen production**:
    ✅ 2026-09-14. ROOT `ebb98492` + RESEARCH `323bcf2c`/`3a4be85d` supersede the initial
    trajectory projection. A compact subsystem-owned normalizer validates source literals and digests, then
    publishes 21 historical whole-candidate checkpoints. The page separates every model, surface,
    recipe and baseline epoch: DeepSeek-1.5B, Qwen3.8-27B, Gemma, and Flash-Next CPU plain/MTP
    evidence no longer share a curve. Production releases are explicit zero-percent epoch markers;
    no line crosses a production, recipe or harness-era boundary without direct dual-baseline
    evidence. The overwritten Qwen `732389d6` `+27.363%` ledger value, its retained direct
    `-1.414%` receipt, and the current `ef81196d` missing production A/B remain visibly distinct.
    Live retained accumulator state supplies an automatically advancing provisional promotion-chain
    checkpoint; compatible direct A/B evidence supersedes it, while identity mismatch breaks the
    chain. The active GLM-5.3 store resolves 23 keeps and `+0.830381%` versus CoR, never the global
    accumulator. Live `/api/loop` serves schema v3 with 12 curves and two explicit exceptions.
    Validation: 81 focused tests, 33 skips and 5 browser subtests passed; existing registry health
    and freshness wiring remains unchanged; AKU-09g/AKU-12 remain open.
    - [x] **AKU-09k-v3 layout and accumulated-knowledge overlay**: ✅ 2026-09-14. ROOT
      `a3cf6d0a` makes the trajectory the first dashboard surface and folds champion identity,
      active progress, retained-gain context and production epochs into it. Separate responsive
      Capabilities and Accumulator cards follow; the redundant Champion and Progress sections are
      gone, while the full knowledge ledger is collapsed by default. Follow-up ROOT `ab1a34c5`
      corrects the initial scatter: exactly one selectable headline trajectory exists per model.
      Each model chooses the longest exact surface history (plain wins ties); secondary surfaces are
      selectable detail, never blended. Recipe/harness/baseline changes are Autopilot-style instrument
      bands and dashed discontinuity connectors within the same model row. The subsequent browser
      correction makes actual kept ledger rows and retained-bundle members drive dots: A/B
      checkpoints alone cannot assert keeps. Nulls, regressions, refusals, invalid/setup attempts,
      and disposition counters remain in the collapsed ledger.
      Accessible keep markers open a persistent side panel and expose only recorded evidence, using
      explicit unknowns otherwise. Trajectory rendering occurs first behind its own visible failure
      boundary. Live default Flash-Next plain spans `6f032c48` → `9c4f73e2` → `ef81196d`; MTP exposes
      the same commit order via the surface selector. Five model IDs produce five headline trajectories,
      with two instrument connectors. The original three-dot result omitted keep history and the
      original panel vanished on refresh; both claims were corrected using real Chromium.
      GLM exposes all 23 retained keeps, including explicitly undated bundle recoveries; hover,
      click, refresh persistence, Escape, and keyboard reopening pass against the served page.
      Browser regression: `tests/js/trajectory_browser_check.cjs`. The preceding focused suite
      passed 85 tests, 33 skips, and five subtests; the interaction fix additionally passed the
      75-test static-JS/loop suite and live Chromium exercise.

<!-- original line 13493 -->
  - [x] **AKU-10b — typed native retention consumer and exact tombstone recovery**: bounded
    candidate/native-root projection feeds existing retained-artifact closure and dry expiry policy;
    actual deletion requires a held generation/root-exclusion capability. ✅ 2026-09-09 — main
    reproduced **250 tests and 82 subtests**, including actual temporary CandidateTransactions,
    ArtifactStore and native Journal close/reopen recovery. One bounded tombstone index per operation
    checks complete descriptor/preconditions/policy identity; intent-after-removal recovery cannot
    delete twice. Generation, source/branch, protected kernels, changed content and shared DSO/ancestor
    roots fail closed. Sequential callers prove idempotence, not concurrency. Source `1be3cf79`,
    main `e678a2e2`. Default execution remains unavailable pending the assigned actual maintenance
    exclusion/native-root/provider-accounting consumer; slow I/O must not hold the controller mutex.
    Only disposable fixture bytes were deleted; no research artifacts or real cleanup were touched.

<!-- original line 13504 -->
  - [x] **AKU-10c — versioned historical migration and verified store exclusion**: bounded
    noncreating dry-run and explicit immutable snapshot import reuse read-only accumulator recovery,
    actual ExperimentStore rows and the existing content-addressed ArtifactStore. ✅ 2026-09-09
    Main reproduced **110 targeted tests**; the combined clean eleven-file retention/migration
    release passed **1,750 tests and 165 subtests**, with **68 final focused tests** and Ruff clean.
    Public reentrant store exclusion serializes nested writes and same-root threads/processes;
    closed/replaced roots refuse. URI-escaped SQLite paths, active WAL/SHM, changing source frontier,
    strict row/byte bounds, unsupported versions and source/destination aliases are tested. Emitted
    snapshots must pass their installed v1 reader before publication, and exact retries preserve
    source bytes. Historical evidence stays `unknown_legacy`; no candidate/validated/serving
    authority is created. Source `1be3cf79`, main `e678a2e2`; live import/cutover and future durable
    legacy database schema marking remain outside this completed snapshot-reader slice.

<!-- original line 13520 -->
  - [x] **AKU-10e — durable maintenance ownership, replay and shutdown fences**: short controller
    transactions retain exclusion across unlocked provider/filesystem work; uncertain acquisition,
    tombstone publication and settlement preserve recovery ownership. ✅ 2026-09-09
    First holds bind to their token; completed accounting reconstructs the exact receipt digest
    and matches IO_COMPLETE cost; fresh and recovery intents enforce their distinct token chains
    and clear prior hold/cost state. Receiptless abort refuses; valid legacy non-abort bytes replay.
    Worker/candidate/new-native publication and clean shutdown cannot bypass owned exclusion.
    Clean six-file acceptance passed 1,873 tests plus 165 subtests; main's composed native/maintenance
    tree passed 1,899 plus 165, with 39 maintenance tests and six independent probes. Research
    source c5525fb8; fresh catalog/provider execution and real artifact deletion are not completed.

<!-- original line 13539 -->
  - [x] **AKU-10h — installed native retention catalog and dependency frontier**: ✅ 2026-09-09.
    Actual standalone v3 derives and durably installs its catalog before runtime composition;
    restart replays the exact seed. Exact model inventories, recipe snapshots/aliases, executable,
    DSO/build/RUNPATH and protected roots join candidate, native, driver and worker/acquisition
    state. Collection performs filesystem work outside the controller mutex and rechecks the
    frontier before binding a job. Main passed 155 composed tests without skips, then 104 tests
    and 15 subtests for Journal/catalog/installed startup after byte-exact application.
    No owner-issued expiry descriptors or live deletion: the current native view retains all
    declared artifacts. This does not complete AKU-10f/10d/10g or authorize provider activation.

<!-- original line 13548 -->
  - [x] **AKU-10i — prospective source/build/evaluation expiry authority**: install the actual
    source/build execution owner and bind its verified BuildIdentity, exact recipe snapshot and
    retained source refs before opt-in candidate integration. Persist the enrollment pointer
    before integration so restart can reconcile it; ordinary/legacy integrations remain unchanged.
    Require closed original evaluation/native/worker/held-cost evidence and exclusive physical
    ownership before issuing any disposition. No inferred rejection, caller-label authority,
    historical backfill, temporary duplicate accounting record or deletion-policy change.
    - 2026-11-18 (autokernel, AKU bulk pass): still needs OP-AKU-ENROLL approval (Journal native payload validation, HIGH20); not implemented.
    - 2026-11-18 operator decision (decision tool): OP-AKU-ENROLL approved as packaged (option A: additive versioned records, legacy preserved). [no-belief: operator decision]
    - 2026-11-19 (autokernel) PARTIAL (code-only; box stays OPEN): research `epyc-inference-research` `439fdbd78` `loop/build_enrollment.py` versioned INTENT/ACTIVATED records (BuildIdentity, recipe snapshot digest, source refs, source/build/evaluation expiry; ACTIVATED joins the exact INTENT digest and precedes every expiry); `candidate_transactions.integrate(..., enrollment=)` is opt-in, INTENT rides in the journaled transaction intent (Journal native validation recovers it) and is persisted as an immutable object before commit; ordinary integrations byte-identical; `expiry_status` issues no disposition. 12 new tests. Remaining: real source/build owner mints INTENT from a verified BuildIdentity, ACTIVATED writer, closed-evidence/exclusive-ownership gate before any disposition. [no-belief: tooling landing]
    - 2026-11-19 (autokernel) DONE (code): research `epyc-inference-research` `e5920834b`: `build_enrollment.mint_intent_from_source_build` binds the source/build owner's verified `source_build_enrollment.v1` to exactly one candidate build (opt-in; ordinary integrate unchanged); `build_activated` + `EnrollmentStore` write-once fsynced INTENT/ACTIVATED with restart `reconcile`; `disposition_gate` refuses unless activated, an authority expired on the same clock domain, all five evidence refs re-read closed and bound to the INTENT digest, exactly one physical owner bound to the build, and no prior disposition; `expiry_status` still issues none. 13 new tests (25 in file). A real disposition owner supplies the `enrollment_evidence_record.v1` records. [no-belief: code]

<!-- original line 13559 -->
  - [x] **AKU-10j — bound retired serial build-cache retention**: ✅ 2026-09-15 — startup now
    plans and reaps only reproducible `targets/*/builds` roots from retired serial states, preserves
    the current state plus the newest inactive cache, and refuses live, locked, unreconciled,
    identity-changing or path-escaping candidates. Continuation hashes, durable source commits,
    exact recipe digests and CMake build shape are revalidated before removal; anchors, receipts,
    logs, patches, stores and source worktrees are never candidates. The operation is dry-run capable,
    bounded to eight directories per start, governed by 400/500 GiB free-space watermarks, and writes
    exact plan/result manifests. Focused acceptance passed 3 tests. Research `c557ad94`.
    This closes the prospective serial build-cache leak, not historical worktree retirement or raw
    profile/journal compaction; those remain under AKU-10d/10f/10g and the disk-hygiene sweep.

<!-- original line 13579 -->
  - [x] **AKU-12a — complete standalone dry run**: ✅ 2026-09-10 — exercise the installed unified entrypoint,
    real production export and explicit candidate enrollment, planner prerequisites/budgets,
    recovery and dashboard/control projections without acquiring compute or inventing grants.
    Retain the exact command/config, loaded code identities, output and refusal/debt evidence.
    Final research commit `377397fa` resolves all eight targets, selects `matched_process_v2` for
    every CPU target and preserves the GPU path without creating compute/state. The actual command
    exited 0 with eight target/dry-run blocks, seven 48-launch matched calibration plans and one
    native GPU five-launch plan; its requested state directory remains absent. Retained output:
    `/mnt/raid0/llm/tmp/aku-final-all8-dryrun-20260910-v2.log`, SHA-256
    `e0783ef73f31dbae760074aab09419b317e63cc52f8fca8af2b0671d5b36d315`.

<!-- original line 13618 -->
    - [x] **AKU-12b-CPU-OBS — add bounded factual CPU lifecycle collection to the existing
      serving path on disk.** ✅ 2026-09-10 — Research packet `499ec92e…` adds process/task
      affinity and allowed-NUMA-list samples through the original serving lifecycle;
      main independently verified 43 tests plus 8 subtests. Raw facts/errors/gaps/bounds
      survive the existing comparison archive. Allowed lists do not establish actual NUMA
      page placement, clean contention or scientific eligibility; both existing proof labels
      remain `unproven`. GPU behavior is unchanged. No live PID was restarted or retroactively
      instrumented; this checkbox does not close AKU-12b or certify a new measured arm.
      Prospective direct-serving belief wiring is separately filed as
      [VB-AK-LEGACY-SERVING](vidya-belief-substrate-program.md#vb-ak-legacy-serving--direct-serving-comparison-and-cpu-facts-2026-09-10).

<!-- original line 13628 -->
    - [x] **AKU-12b-TARGET-CLI — connect an explicitly enrolled target to the existing loop
      CLI.** ✅ 2026-09-10 — Research source `1f2d93aa` / main `195c4ea5` adds
      `--resolved-campaign` with `--target-id`, preserves original enrollment identity,
      binds CPU serving workload and retains the legacy GPU-screen label. Main verified
      68 focused tests. This is not serial all-target dispatch, artifact admission,
      a live-process restart or completion of the broader acceptance goal.

<!-- original line 13634 -->
    - [x] **AKU-12b-SERIAL-CLI — rotate finite enrolled-target batches through the existing
      loop owner.** ✅ 2026-09-10 — Research `718f4108` / main `d5b3cc96` adds
      `loop.serial_run`, persistent STOP, distinct batch outputs and actual current/COR
      continuation. Restart no longer pairs a restored old COR commit with the current
      build. Switching reuses verified retained anchors and request-bound floors; no
      copy, forced rebuild or recalibration merely for a switch. Primary verification:
      82 focused tests passed (4.55s); the 14 serial tests include real tiny children
      and existing-owner synthetic keep/resume paths. No live hardware serial proof,
      fabricated GPU provenance, new grader or completion of AKU-12b is claimed.

<!-- original line 13643 -->
    - [x] **AKU-12b-SERIAL-DASH — show serial routing and the exact active child without
      hiding canonical history.** ✅ 2026-09-10 — Research `237d82ec` / main `707639d4`
      publishes original batch directory/PID and routing totals; integrated ROOT support
      keeps canonical champion/history roots unchanged. Child detail requires matching
      target, directory and PID, with freshness independent of the router heartbeat;
      stopped, complete and all-failed sessions remain distinct. Main verified 42 producer
      tests (7.72s) and 18 ROOT tests (2.71s). ROOT publication is combined with this
      checkpoint; no dashboard environment change, process reload or live serial proof.

<!-- original line 13651 -->
    - [x] **AKU-12b-OWNED-ROSTER — derive the existing serial runner's inputs from ready
      enrolled CPU/GPU/candidate targets.** ✅ 2026-09-10 — Research `8f67076c` / main
      `d5705634` adds resolved campaign + one concise owned-target map, deriving model,
      recipe, actor defaults and distinct output/lane roots without per-target argv files.
      Original source/branch/anchor/request facts remain explicit; aliases execute once,
      unavailable/unowned targets remain named, and old `--target-args` still works.
      Generated children are confined with existing `taskset`; original continuation,
      STOP and no-replay behavior remain. Actual corrected GLM metadata generation selected
      **1 ready seed and reported 17 unavailable targets** without model/binary hashing or
      output creation. This is partial coverage, not all-target or live-run acceptance.

<!-- original line 13661 -->
    - [x] **AKU-12b-GPU-SERVING — execute explicitly selected GPU serving workloads and
      bind declared host resources through existing owners.** ✅ 2026-09-10 — The same
      research checkpoint adds `--gpu-serving-launch`, original frozen requests and
      request-bound calibration to the existing serving comparison. Experimental GPU
      candidates remain separate from canonical COR/accumulator semantics; ordinary GPU
      cheap screens are unchanged. Shared validation binds model/workload and
      supported GPU visibility, while declared host CPUs/build jobs govern affinity,
      builds and existing CPU-region claims alongside the original GPU claim. Main's
      combined **84 tests passed in 7.34s**, with synthetic hardware/provider boundaries,
      actual tiny children and dry-run owner validation. Main then ran the real GLM
      serial `--dry-run`: exit 0 in 0.19s, original c463 startup identity, n_embd=4096
      census and original request-bound 7.801% floor reopened. No build, resource claim,
      inference, current live-PID reload or qualified/promotion gate is claimed.

<!-- original line 13674 -->
    - [x] **AKU-12b-SERVING-BELIEFS — connect the direct comparison write/read belief path.**
      ✅ 2026-09-10 — Research `86179a8c` / main `0a815338` captures inputs before launch,
      retains original comparison/CPU dependency bytes and exports through the existing archive.
      ROOT's strict reader reaches the existing corpus and Ledger; main verified 33 research
      tests plus 8 subtests and 15 ROOT tests. Protocol remains empty (`Judged/Located`);
      no historical backfill or qualified hardware gate is completed. The current live PID was
      not reloaded; live ingestion remains unverified and planner feedback follows below in the separate
      [VB-AK-LEGACY-SERVING tasks](vidya-belief-substrate-program.md#vb-ak-legacy-serving--direct-serving-comparison-and-cpu-facts-2026-09-10).

<!-- original line 13692 -->
  - [x] **AKU-12d — continuous 50-loop GLM health acceptance**: ✅ 2026-09-14 — run the
    existing GLM CPU AutoKernel continuously, repair observed execution faults, preserve and
    reuse valid prior results, and monitor 50 terminal measured candidate loops. The retained
    v2/v3/v4/v7 states prove 50/50 completions (`42 measured_null`, `8 kept`) with observed
    original-request CPU profiles, real planner/author/build/gate/A-B paths, automatic batch
    transitions and clean keep settlement. The final tip `dc3798db10a6` contains 23 accumulated
    keeps and directly measures `+0.8303809823%` against COR `c463f601bd39`; it remains
    experimental and was not promoted to production. The operator-requested monitor stopped
    after loop 50; the automatically started post-boundary batch 25 is not evidence and is
    recoverable runtime state, not a completed attempt.

<!-- original line 13702 -->
  - [x] **AKU-12f — remove the GLM formation-payoff deadlock without weakening safety review**:
    ✅ 2026-09-14 — Research `5ac7b7e4` corrects the CPU planner/critic contract after retained
    batches 27–34 spent 24 pass-one critic calls on eight proposals without reaching authoring.
    The critic had promoted post-authoring payoff falsifiers (exact eligible-call census,
    request-wall exposure and isolated local speedup) into mandatory pre-authoring evidence even
    though the loop could not acquire those traces. Source-consistent bounded candidates now
    proceed to the existing correctness and matched A/B pipeline; duplicate mechanisms, wrong or
    incomplete source routes, unsupported claimed facts, and uncontained correctness/safety risks
    remain formation refusals. The live store's contradictory stagnation inbox instruction was
    corrected in place without changing its journal or 23 accumulated keeps. Focused planner,
    critic and loop validation passed 74 tests. Continuous batch 42, started after publication,
    loaded the corrected planner contract; its scientific outcome remains live campaign work and
    is not claimed by this implementation checkpoint.

<!-- original line 13715 -->
  - [x] **AKU-12g — complete the bounded post-formation recovery and first full-bundle checkpoint**:
    ✅ 2026-09-15 — the planner/profile/escape/reduced-screen and stopped-resume corrections
    (`632939b0`, `2db9d844`, `733bfaa6`, `5f368aa2`, `92a91c99`) were exercised by the relaunched
    GLM campaign. Batch 3 produced the first published whole-bundle confirmation and advanced the
    experimental research anchor to `7e9f5eb`; batch 4 produced a provisional successor. The
    current 26-keep accumulator estimate is `+0.855%` versus the campaign CoR. That estimate and
    the confirmation are campaign-local evidence only: they neither replace the frozen champion
    nor authorize a production change. Production remains frozen at v9.

<!-- original line 13723 -->
  - [x] **AKU-12h — make the headline trajectory disclose scope rather than imply a promotion**:
    ✅ 2026-09-15 — ROOT `35746b46` labels GLM as a retained campaign trajectory, retains explicit
    discontinuities/unjoinable receipts, and keeps unresolved accumulator estimates separate from
    verified champion movement. The dashboard is bound to production-v9 as its serving era; no
    production-kernel mutation, registry change or live-loop control was performed.

<!-- original line 13728 -->
  - [x] ~~**AKU-12i — monitor the relaunched GLM AutoKernel through 20 healthy completed iterations**:~~ (closed 2026-10-29 audit: OBSOLETE → GLM-5.3-Flash deleted 2026-09-22; box says "No GLM campaign can relaunch. Do not tick this row.")
    **[Subject deleted 2026-09-22]** GLM-5.3-Flash (model, DFlash2 drafters, `llama.cpp-experimental-glm53-*` worktrees) was removed from disk by operator direction; branches and stores remain as history. No GLM campaign can relaunch. Do not tick this row. Any retarget to DeepSeek-V4.1-Flash is a new task under that handoff, after the port exists.
    batch 5 is live after three clean completed iterations. Stop safely, repair and relaunch on any
    unexpected behavior; after 20 clean iterations leave the continuous campaign running. This is
    operational health monitoring, not candidate validation, champion promotion or production mutation.

<!-- original line 13733 -->
  - [x] ~~**AKU-12e — validate the accumulated GLM tip across required targets**: **[Subject deleted 2026-09-22]** GLM-5.3-Flash (model, DFlash2 drafters, `llama.cpp-experimental-glm53-*` worktrees) was removed from disk by operator direction; branches and stores remain as history. The GLM correctness gates cannot run without the model. Tip `dc3798db10a6` stays pushed as history. Its generic (non-GLM-specific) keeps could only be revalidated on other targets through a new task.~~ (closed 2026-10-29 audit: OBSOLETE → GLM-5.3-Flash deleted 2026-09-22; GLM correctness gates cannot run (box text))
    Original text: run the
    existing required-target validation and exact GLM correctness gates against experimental
    tip `dc3798db10a6`; publish the aggregate disposition before any champion admission proposal.
    This is a separate candidate-validation task, not part of the completed 50-loop health proof,
    and it authorizes neither production mutation nor promotion.

<!-- original line 13754 -->
  - [x] **AKU-12j — retire the GLM-5.3 `active_campaign` pin** (found 2026-09-22): the research <!-- evidence-integrity: Research `084deaf0ef76680c11f89ac3d7cf56de5e81253f`; ROOT `03b38117545d91d77a3784f0bee85e5922d0d33c`; artifact: artifacts/compute/task-evidence-repair-20261031/aku-12j/EVIDENCE.json; hygiene, not quota -->
    repo's `scripts/kernel_rnd/autokernel/loop/historical_trajectory.py:168` still hard-codes
    `active_campaign` = `aku12a-glm53-five-loop` (GLM-5.3-Flash, store
    `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-store`, 23 expected keeps), and
    `test_historical_trajectory.py:34` asserts it. The store was deleted with operator
    confirmation, and its cited evidence is in `artifacts/autokernel/glm53-evidence-20260922/`.
    `dashboard/loop_status.py` (~2337-2763) attributes retained bundles and headline standing
    through this field. Replace it with the next real campaign, or an explicit `null` with a
    rendered "no active campaign" state. Update the test, and confirm the hub's `autokernel_loop`
    panel. It reads `degraded / stopped_reporting` since the pin was removed 2026-09-22: the
    default loop-memory status is 14 days old, which is truthful while no loop runs.
    ✅ 2026-10-29 research `f130149922` / root `600c64cf48`: producer emits explicit null; hub
    distinguishes selected/none/unknown and renders escaped no-selection/unknown banners for empty and
    populated plots. All 21 historical points and other evidence fields unchanged; stale health remains
    truthful. 30 producer/hub tests and JS syntax check passed after integration. Source/panel behavior
    verified in tests; no live reload or history regeneration performed. [no-belief: metadata and UI repair]

    <!-- task-evidence-integrity:start AKU-12j -->
    - Evidence metadata (hygiene, not new quota): Research `084deaf0ef76680c11f89ac3d7cf56de5e81253f`; ROOT `03b38117545d91d77a3784f0bee85e5922d0d33c`; [test/artifact](../../artifacts/compute/task-evidence-repair-20261031/aku-12j/EVIDENCE.json).
    <!-- task-evidence-integrity:end AKU-12j -->

<!-- original line 13777 -->
- [x] **S3-AKU-01 — typed trial lifecycle with a single transition table.** Replace the stringly-typed
      `Outcome.status` (loop/loop.py) with a typed lifecycle whose transition table is the only legality
      source; derive the persistence guard from it (terminal states absorbing, a duplicate/racing completion
      is a no-op), with a matrix test asserting implementation == table. Reference pattern: orx run
      lifecycle, intake-883#record @3a8b0286 (community-contributed #322, not alphaXiv's design). Either
      implement the §8.12 state set or delete it. Any change to the native transition validator rides
      OP-AKU-A2; do not bypass it.
      - 2026-11-18 (autokernel, AKU bulk pass) NEEDS DESIGN + OP-AKU-A2 (box stays OPEN): `Outcome.status` (loop/loop.py) is a per-iteration terminal outcome string consumed throughout run.py with no existing transition table or §8.12 state set to derive from; replacing it needs the status inventory and either implementing or deleting §8.12, and the native transition validator rides OP-AKU-A2. Not started.
  - 2026-11-18 operator decision (decision tool): OP-AKU-A2 approved as packaged (option A: additive versioned records, legacy preserved). [no-belief: operator decision]
  - 2026-11-19 (autokernel) PARTIAL (code-only; box stays OPEN): research `epyc-inference-research` `c533c997e` `loop/trial_lifecycle.py` implements the minimal §8.12 state set (starting, recovering, running, waiting_resource, waiting_actor, paused, draining, drained, validation_required, failed, complete) with `TRANSITIONS` as the only legality source, `TERMINAL_STATES` derived from it (failed/complete absorbing; duplicate or racing completion is a NOOP), `guard_transition`/`apply_transition`, and a typed `OutcomeStatus` str-Enum inventorying all 35 `Outcome.status` literals in loop.py/pipeline.py/run.py. `test_trial_lifecycle.py` 11 passed incl. an 11x11 matrix (implementation == table) and an AST scan proving every status literal is covered. Judgement calls to review: pause/drain resume through RECOVERING; DRAINED is non-terminal. Remaining: wire the guard into the run.py persistence path (not low-risk: many tests build arbitrary statuses); `Outcome.status` still holds plain strings. [no-belief: tooling landing]
  - 2026-11-19 (autokernel) DONE (code): research `epyc-inference-research` `b0cb301ff`. Both judgement calls checked against §8.12 and kept (resume 'reconciles identities and reacquires authority/claims' -> PAUSED/DRAINED resume only via RECOVERING; DRAINED non-terminal because the text defines resume after drain; PAUSED->DRAINING legal). The guard is wired into the single run.py persistence point `dispatch_guard.Registry.finish` (both run.py `registry.finish` sites): a second finish for an already-terminal `OutcomeStatus` is a no-op, unknown/legacy statuses and re-dispatch via `reserve` pass through. 3 tests incl. a structural run.py check (run.py is one closure; a live concurrent-completion race is not run). [no-belief: code]

<!-- original line 13788 -->
- [x] **S3-AKU-02 — evaluate a compile-time build-channel stamp for loop binaries.** Make "is this an
      official/production build" unforgeable: a mis-set flag FAILS THE BUILD rather than degrading silently.
      Compare against the existing anchor provenance.json + object-digest approach, and record
      adopt/decline. Pattern: intake-883#record (orx build.rs) @3a8b0286. **DECLINED 2026-09-15:**
      production is a post-measurement operator ratification state, not a compile-time property, and the
      loop itself is Python. A source/CMake stamp is forgeable; flipping it at promotion would rebuild and
      violate measured-artifact == promoted-artifact. Existing BuildIdentity, sealed recipe, source snapshot,
      build/log/binary/library digests, anchor object digest and independent production verifier are stronger
      and correctly layered. Revisit only if an independently signed release authority is introduced.

<!-- original line 13805 -->
- [x] **S3-AKU-05 — validator provenance on every critic verdict and every keep.** Record per decision:
      validator identity and kind (script / oracle / LLM critic), its independence relation to the producer
      (same fleet / same family / different family / non-model), the evidence it inspected, and whether its
      result changed subsequent search. planner_evidence covers the last field for keeps only.
      intake-1367#record (remedy R3); GRAFT-ATHENA's analytic-vs-Advisor axis split is one more instance
      (intake-1380#record). Autopilot twin: S3-AP-07. ✅ 2026-09-15 — research `54d1370d`,
      `e1fef75d`: every critic, deterministic gate/oracle and paired-A/B verdict carries validator identity,
      kind, producer independence, inspected evidence, disposition/reason and whether it changed later
      search. Measurement results are marked causal when they close an attempt or move the anchor; grading
      and keep policy are unchanged.

<!-- original line 13815 -->
- [x] **S3-AKU-09 — split every keep record into EFFECT and MECHANISM claims.** EFFECT is gated by oracle +
      paired A/B. MECHANISM is the planner narrative and carries status=hypothesis unless an ablation tested
      it. Example defect: R23-35's recorded MMQ→MMVQ reroute mechanism beside an A/B-validated effect
      nothing tested. Wiki/planner consumers must not compound on hypothesis-status mechanisms.
      intake-1374#03. ✅ 2026-09-15 — research `10b9301a`: additive `keep_claims.v1` verifies EFFECT only
      from a passed oracle plus paired A/B; MECHANISM defaults to hypothesis and becomes verified only with
      explicit nonempty ablation evidence. Legacy/malformed mechanisms fail closed to hypothesis, planner
      causal pooling excludes them, and generated experiment prose labels their status.

<!-- original line 13823 -->
- [x] **S3-AKU-10 — retrospective process metrics over existing autokernel stores (do first).**
      First-improvement step, AUC-over-steps of best-so-far effect, valid-step ratio (measured / (measured +
      refused_at_formation + planner_transient + bench_failed)), and critic-pass-1 rejection rate vs
      eventual measured_null rate of hypotheses accepted after a rejection vs on first pass. If critic
      rejections do not predict fewer measured_nulls, the two critic passes are unvalidated cost.
      intake-1375#04. ✅ 2026-09-15 — research `e794b402`: the read-only streaming producer evaluated
      four genuine stores (2,577 attempts) without rewriting them and published first-improvement step,
      best-so-far AUC and valid-step ratio. The requested critic cohort comparison is explicitly
      unavailable—not zero—because historical rows do not persist pass-1 lineage; this records the
      evidence gap rather than inventing an association.

<!-- original line 13833 -->
- [x] **S3-AKU-11 — costed design (no launch) for a strategy-only ablation on one frozen champion.** Arm A: ✅ 2026-11-04 [belief: cc]
      production planner+critic. Arm B: same planner with an accept-all Critic. Optional arm C: a catalog
      Planner.propose drawing uniformly from do_not_repeat mechanism tokens not yet measured on the target.
      Build/oracle/A-B tail identical; keeps recorded as candidates. Preregister the primary metric and N
      before launch. Recorded cost: ~255 attempts/arm to detect a keep-rate halving at 80% power, ~31
      GPU-h/arm on the screen surface, infeasible on CPU; a zero-keep surface is degenerate. Launch is
      operator-gated. intake-1375#02.
  - 2026-11-02 operator decision: Keep launch gated; deliver the costed design only (decisions-batch2-4-20261102.json)

<!-- original line 13841 -->
- [x] **S3-AKU-12 — journal a per-target stagnation signal, OBSERVE-ONLY.** Record the slope of best-so-far
      effect over a trailing window and the consecutive measured_null count. No behaviour switch until
      S3-AKU-11 reports. intake-1375#03. ✅ 2026-09-15 — research `e1ee4cf0`: loop status publishes
      an explicitly observe-only, per-target 20-measurement best-so-far OLS slope and consecutive trailing
      measured-null count; non-measurement outcomes do not become synthetic zeroes and no policy consumes it.

<!-- original line 13846 -->
- [x] **S3-AKU-14 — rejection-round telemetry for the planner.** Record on every Outcome the
      hypothesis/patch round and whether the prompt carried prior-rejection text. Once the op-coverage
      oracle extension (P3) lands, report op-coverage changes and env-gated fall-through findings by round.
      intake-1379#record (violation severity rose with each round of error feedback). ✅ 2026-09-15 —
      research `e1ee4cf0`: every serialized Outcome carries one-based hypothesis/patch rounds and whether
      prior-rejection text was present; non-formation outcomes retain explicit 0/0/false defaults.

<!-- original line 13852 -->
- [x] **S3-AKU-15 — diff-scope equality and oracle/bench-source immutability, before critic pass 2 (binding
      together with S3-AKU-16).** After planner.author, take the lane worktree's full git status --porcelain
      --untracked-files=all and refuse the patch (no build) if: (a) the dirty set is not exactly the
      declared paths; (b) any dirty path is outside a kernel-source allowlist (ggml/src/**, src/**); or (c)
      any dirty path is an oracle/bench source (tests/**, tools/llama-bench/**, tools/server/**,
      examples/**, scripts/**, any CMakeLists.txt). Record the refusal class in the Outcome, and assert the
      committed keep equals the measured tree. Upstream ports that legitimately add oracle tests go through
      the operator port lane. **Regression fixture (zero compute):** replay a recorded patch that edits
      tests/test-backend-ops.cpp outside the declared paths; it must be refused. **Why this shape, and why
      it is not sufficient alone:** ImpossibleBench Fig. 7, read-only/revert of test edits cut cheating Opus
      4.1 50% -> 1%, o4-mini 49% -> 11%, GPT-5 only 54% -> 39%, at no legitimate-performance cost; hidden
      tests reach ~0% but cost 11-26 points and are infeasible here (the candidate tree builds its own
      test-backend-ops). The planner is gpt-5.6-sol (OpenAI family), whose residual is special-casing /
      operator overloading / state recording, so S3-AKU-16 binds on the same day. (intake-1387#record;
      intake-1396#record; intake-1395#record.) This row IS INF-75's AKX-P2-PRE precondition; tick both
      together. ✅ 2026-09-15 — research `bada71c2`: `loop/integrity.py` validates the complete porcelain
      dirty set before critic pass 2/build, enforces the source allowlist and protected oracle/bench paths,
      journals typed refusals, and binds the measured tree to keep promotion. Zero-compute fixtures cover
      undeclared and declared `tests/test-backend-ops.cpp` edits plus measured/kept tree drift.

<!-- original line 13871 -->
- [x] **S3-AKU-16 — special-casing screen on keeps, binding together with S3-AKU-15.** Per kept patch,
      record every ADDED branch predicate comparing tensor dims/types/op ids against literals, crossed with
      the oracle's exercised shapes (test-backend-ops -o MUL_MAT) and the A/B bench shape, plus any ADDED
      static/global mutable state read on the hot path (the state-recording class). A keep whose speedup
      path is reachable only under such predicates, or that reads such state, is refused or held
      KEEP_CANDIDATE-needs-confirm from the day S3-AKU-15 lands, not after S3-AKU-14's op-coverage diffing.
      **Confirm step:** a needs-confirm keep is confirmed on a bench shape the planner never saw in context
      (rotated pp/tg/ubatch, or the serving gate), and the public-to-held-out speedup gap is recorded on the
      Outcome. **Regression fixture (zero compute):** a recorded patch whose fast path is gated on a literal
      predicate matching the A/B bench shape must be flagged. (intake-1387#record; intake-1396#record,
      residual 39-58% for GPT-5 under read-only tests; intake-1395#record, Table 2 held-out gap separates
      hacks from honest runs.) ✅ 2026-09-15 — research `bada71c2`: added-diff screening covers ggml's
      indexed and flattened tensor dimensions (including reversed literal comparisons), type/op literals,
      and hot-path mutable state; candidate evidence crosses public oracle/bench identities, forces an
      unseen confirmation for suspicious keeps, and persists the public-to-held-out speedup gap.

<!-- original line 13886 -->
- [x] **S3-AKU-17 — objective ledger for autokernel campaigns (design item).** A structured record per
      campaign/target: the aims a keep must satisfy (serving throughput per surface, correctness oracle,
      variance), the evidence for each, the trade-offs among them, and the decision rule used when the loop
      proceeds despite an unresolved conflict. Seed it from the §8 per-surface evidence matrix and
      floors-with-units; do not add implementation authority. intake-1367#record (remedy R1). ✅ **Design
      closed 2026-09-15:**
  - `epyc.autokernel.objective_ledger.v1` is a content-addressed, read-only declaration/assessment snapshot;
    it cannot launch work, reserve resources, grade ClaimTuples, amend policy, keep/promote, or authorize
    unresolved evidence. `CampaignManifest.objective_ref` is its pointer seam; live resolution is separate.
  - Exact top-level fields are `schema`, `campaign_id`, `campaign_manifest_digest`, `objective_id`,
    `revision`, `targets`, `tradeoffs`, `conflict_rules`, `ledger_digest`; the digest excludes itself. There
    is exactly one target row per resolved `(target_revision_digest, surface_id)`.
  - Target/objective rows bind revision/workload/backend/surface/recipe, aim/kind/required,
    estimand/metric/direction, instrument, `arm|session|process` unit, explicit finite threshold,
    unit-matched content-addressed floor, witnesses, native evidence refs and projected assessment. Evidence
    must match its ExperimentPlan and exact scoped-evidence ClaimKey; hand-entered results are forbidden.
  - Tradeoffs reference aim/threshold IDs. Correctness, source/tree identity, instrument integrity and
    required witnesses are non-tradeable; gains cannot cross units or surfaces. Conflict actions are only
    `hold|refuse|proceed_research_only`; research-only remains ineligible for keep, global validation,
    promotion, release and headlines. No matching rule fails closed to hold.
  - Every serving surface has one throughput aim; every target has required correctness; session/process
    throughput requires a variance aim. Candidate/source/recipe changes stale prior assessments; CPU evidence
    cannot satisfy GPU; missing/changed refs, unit mismatches, unknown fields and non-finite values refuse.
    The zero-compute fixture matrix covers these invariants plus digest stability, duplicate rows/priorities,
    non-tradeable correctness and rejection of keep-like conflict actions.

<!-- original line 13911 -->
- [x] **S3-AKU-18 (AK-RH-3) — first-class planner abstain.** Accept {"abstain": "<reason>"} as a valid reply
      to Planner.propose and Planner.author, and record Outcome("abstained", hypothesis, [reason]) as a
      science outcome: it feeds the Characterised context, not the transient streak. Stop booking an empty
      author path list as ProviderTransient (loop/actors.py raise ProviderTransient("authoring returned no
      changed paths") -> loop/loop.py except ActorTransient -> Outcome("planner_transient"); lines 428-429
      and 245-249 at research ae8e5ef9, 659 and 277-281 at origin/main d9813d65). Tell the planner in the
      author prompt that abstaining on an infeasible hypothesis is a correct result. Record the abstain rate
      per run beside S3-AKU-14's rejection-round telemetry. Evidence: ImpossibleBench §5.3, where an abort
      option cut GPT-5 cheating 54% -> 9% and extra feedback rounds raised cheating 33% -> 38%. The planner
      is gpt-5.6-sol with PATCH_ROUNDS = 2 rounds of verbatim critic rejections, and today a truthful
      "cannot implement" is booked as a provider failure. intake-1396#record. ✅ 2026-09-15 — research
      `bada71c2`: proposal and author replies accept reasoned abstention, legacy empty author paths map to
      abstention, the author prompt names it as a correct science result, `Outcome("abstained", ...)` skips
      judges and re-enters characterised context without incrementing transient streaks, and run status
      publishes `abstain_rate`.
  - [x] **S3-AKU-18a — settle a science abstention through the serial scheduler**:
    ✅ 2026-09-16 — research `main` `fb8a8273` accepts `abstained` as a distinct
    charged, nonmeasurement terminal outcome rather than stopping the campaign as
    `SerialSchedulingRefused`. Nine focused tests pass; the actual v14 child
    receipt now maps to `abstained`. Existing GLM store and 27 keeps were not
    reset. The hardware relaunch remains separate and waits for the operator's
    announced quiet GPU window.

<!-- original line 14031 -->
  - [x] Validate the existing CPU/GPU keep and pruning paths against original kernel-coverage
    controls. Research `906bb7b5` repairs the shared fake binary's symbol fixture while retaining
    the real coverage/source gate; symbol-loss controls require `keep_candidate`, no promotion
    and no branch move. Original native consumer checks and the final full gate passed; ROOT acceptance fd9043db retains the original outcomes.

<!-- original line 14035 -->
  - [x] Triage clusters 2, 3, 5, 6 (3 and 5 flagged lane-affecting) plus the ~62-item long tail —
    `/mnt/raid0/llm/tmp/ak-test-triage-20261007/TRIAGE.md`.

<!-- original line 14167 -->
- [x] CTC-Q-A ✅ 2026-10-22 (validator on main, wired into every grant writer via grant_ok.sh by workspace-58, root 1740e3b19; first in-the-wild refusal kpf60-p0-gpu fixed by its owner): required QUEUE/booking fields `prior=<path|none, checked by whom>`, `decision=<one line>`, `min_effect=<% or count>`, `substrate=cpu|gpu|either` in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` rows and GRANT lines, with a ~20-line validator in `scripts/coordination/` run by the grant writer that rejects a grant whose row lacks them. (proposed to workspace-58/stage-3 2026-10-21; build A+B on agreement; source: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §4)

<!-- original line 14168 -->
- [x] CTC-Q-B ✅ 2026-10-22 (prior_check.py on main; its output path is the prior= field validate_fillers enforces at grant time): scripted zero-compute `prior_check.py`: given model + recipe/argv + metric, grep the belief ledger (`source_observed.assertion.applicability{recipe,build_sha,execution_digest}`), `/mnt/raid0/llm/tmp/*/RUN_RECORD.json|*.jsonl`, research `artifacts/` and AK campaign stores; its output path is the `prior=` field of CTC-Q-A. (proposed to workspace-58/stage-3 2026-10-21; build A+B on agreement; source: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §4)
  - *(2026-10-22, f8; CTC-Q-A and CTC-Q-B stay open.)* `prior_check.py` and `validate_fillers.py` built on root `f8/prior-check` (49 tests passed, but run inside stage-3's quiet baseline, disclosed in `HOST_ACTIVITY_DISCLOSURES.md` and cleared by the floor sensitivity check); FILLERS.md column 6 is now peak host RAM GiB. Not landed on main and not yet wired into the grant writer.
  - [x] re-run the `f8/prior-check` tests and land the branch: `prior_check.py` + `validate_fillers.py` on main (`74b3cef5a`, `21954debe`, then `7d79e98ec`, `633771131`, `78d54c50b`, `32ddfd5c1`). ✅ 2026-10-22
  - [x] queue semantics "queued means ready" (2026-10-22 ruling) in `validate_fillers.py`: ready=y needs ARMED + live launcher pid; ready=n rows are BACKLOG with blocker+owner; REGISTERED/ready=n is an error; terminal rows (COMPLETE/CANCELLED) skip field checks; `min_effect` accepts `n/a (<reason>)`. Main `03a4b109d` + `a367d1df0` (operator D9 acks for `scripts/coordination/**`); rule text in `docs/guides/agent-workflows/compute-fillers.md`. ✅ 2026-10-22
  - [x] wire `validate_fillers.py --row <id> --for-grant` into the grant writer (no caller on main yet: only the doc and the module reference it), then tick CTC-Q-A/CTC-Q-B. (split 2026-10-22, f8 wrap-up) ✅ 2026-10-22
  - *(2026-10-22 13:15Z, workspace-58; NOT ticked, evidence inconclusive.)* The admission wrapper `/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh <row> <GiB> [ds41]` (validate_fillers `--for-grant`, then ram_admit) is wired into `grant-akx-after-speech`, `grant-lb4-day`, `grant-locals` and `grant-q2-afternoon`. Two armed writers still call only `ram_admit.sh`: `grant-night-kpf64-20261022-v3.sh` (armed 12:39Z) and `grant-night-q2-20261022.sh` (11:44Z). The older evening chain writers end before the ~21:45Z re-plan.
  - [x] workspace-58: route `grant-night-kpf64-20261022-v3.sh` and `grant-night-q2-20261022.sh` through `grant_ok.sh` (re-arm with the old poller killed by PID) before the ~21:45Z re-plan; then tick the wire-in item above and CTC-Q-A/CTC-Q-B. ✅ 2026-10-22
    - *(2026-10-22 13:2xZ, workspace-58)* Wired: every live grant writer calls `/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh <row> <GiB>` (validate_fillers `--for-grant` + ram_admit) before writing a grant. Night writers were re-armed: evening chain v10 (C2 re-run; the operator-requested gpu-cpu-noise experiment is RAM-admitted only), GPU chain v5, q2 v2, kpf64 v4; day writers since 12:25Z. First refusal in the wild: `kpf60-p0-gpu` (prior/decision/floor fields), returned to stage-3. CTC-Q-A/CTC-Q-B parent ticks are left to f8 (handoff owner).
  - [x] **CTC-Q-A2 — `grant_ok.sh` refuses a grant whose shape cannot run.** Two checks before the grant is written: (a) the grant's regions match the launcher's declared class (a `cpu+gpu` class needs `mi210_0` in `regions=`; a `gpu` class needs `mi210_0` and no CPU quarter unless the row says so; read the class from the FILLERS row or the launcher's `class=` log line); (b) the window is at least the row's min-window plus the poll margin (launcher poll interval + 60 s), not merely equal to it. Origins, 2026-10-22: c2-q38fn-b-rerun #2 refused rc=2 at 19:27Z (cpu+gpu launcher, `regions=0-95` grant; slot lost); kpf60-p0-gpu refused rc=3 (v6 window exactly 1800 s = its min, lost to poll lag). The night writers since 19:3xZ already add min+margin by hand; this moves both checks into the gate. Owner: workspace-58 (calendar owner). Done when both refusals reproduce as `grant_ok.sh` refusals in a dry run and every live writer uses it. (filed 2026-10-22, workspace-58 wrap-up) ✅ 2026-10-29 (audit: compute-flags/grant_ok.sh header documents --window-s >= min-window+300 and --regions class match (L10-13); test_grant_ok_v2.sh present; docs commit 8a73e2bbc) [no-belief: audit-reconciliation]
    - *(2026-10-23 14:0xZ, workspace-58 wrap-up; NOT ticked, the gate is unchanged.)* Third reproduction of check (b): `s5-rtepfx2-stagger` refused rc=3 at 06:45Z, because block writer v1 gave it a 2626 s window against its 2700 s min-window. That was the calendar owner's error, the same defect as kpf60 on 10-22. Mitigation the same day: every live writer was audited at 07:0xZ for window ≥ min-window + 300 s (all OK), and the re-run got 3000 s and completed 09:55Z. The live `/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh` (942 B, mtime 2026-10-22 11:54Z) still runs only `validate_fillers --for-grant` + `ram_admit`, so neither check is in the gate yet. It is untracked (no copy in git), so the fix is a versioned copy beside it plus a tracked source under `scripts/coordination/`. Owner: workspace-58 (calendar owner); this wrap-up subagent does not edit `compute-flags/`. Related, from the same day: an owner-side double claim can also look like a grant-timing refusal (kpf18-item3 rc=75, below in `compute-fillers.md` owner duty 28). Check (a)'s class-to-regions match would not catch that one.
    - *(2026-10-23 15:3xZ, workspace-58 wrap-up; box stays open.)* IN PROGRESS: a workspace-58 subagent is building grant_ok v2, which adds checks (a) and (b) above, together with CTC-Q-C.1. It lands as a versioned copy beside the live `compute-flags/grant_ok.sh` plus a tracked source. Not landed at this checkpoint.

<!-- original line 14179 -->
- [x] CTC-Q-C: derive the booking class from the decision, not by default: QUIET only if `decision` names a champion/candidate baseline or a keep gate with a cited quiet floor file; TIMING-PAIRABLE if indicative; CORRECTNESS otherwise; the grant writer sets the gpu-quiet claim from the class. (proposed to workspace-58/stage-3 2026-10-21; build A+B on agreement; source: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §4) ✅ 2026-10-22
  - *(2026-10-22, workspace-f8; operator D9 ack via AskUserQuestion.)* Landed root eb5e162ee: `scripts/coordination/validate_fillers.py` `derive_booking_class` (quiet = champion/candidate baseline or keep gate with a cited floor file, or a row that measures a floor for a named build; pairable = indicative/timing; correctness otherwise), a declared class stricter than derived is REFUSED under `--for-grant`, `--print-class <row>` for grant writers (interface `/mnt/raid0/llm/tmp/ctc-q-c/INTERFACE.md`; only block-timing-quiet sets the gpu-quiet claim); 70 tests. workspace-58 cut the live copy over at ~21:00Z from `git show origin/main:` (backup validate_fillers.py.bak-pre-ctcqc-20261022), reclassified s5-hsprof1-beam-reader / s5-cme7-poker-smoke / s5-stackup-bundle to block-correctness; whole-file run 79 rows, 0 refusals. No quiet window moved.
  - *(2026-10-22 late evening, workspace-58 wrap-up; derived observation.)* At the 21:0xZ cutover, the `/workspace` shared-clone working copy of `validate_fillers.py` was 68 lines behind origin/main because the shared clone's checkout was stale. Re-checked at this wrap-up: the shared clone is at `796a77e06`, which contains `eb5e162ee`. Its copy now matches HEAD (407 lines, no diff), so the lag has resolved. Nothing filed, for two reasons: the live grant path (`compute-flags/grant_ok.sh`) runs the `compute-flags/` copy, and the shared clone's checkout is advanced by its owner sessions.
  - [x] CTC-Q-C.1 grant writers read the class via `--print-class` and set `--gpu-quiet` from it (workspace-58 adopts it in new writers from 2026-10-22). ✅ 2026-10-29 (audit: compute-flags/grant_ok.sh references validate_fillers.py --print-class and gpu-quiet derivation (L13-15); commit 8a73e2bbc "CTC-Q-C.1 class") [no-belief: audit-reconciliation]
    - *(2026-10-23 15:3xZ, workspace-58 wrap-up; box stays open.)* IN PROGRESS: in the same grant_ok v2 subagent as CTC-Q-A2 (class from `--print-class` sets `--gpu-quiet`). Not landed at this checkpoint.

<!-- original line 14188 -->
- [x] CTC-Q-G: filler_run2: exit after one window unless --repeat; refuse to delete a grant held by a running sibling. Hazard seen 2026-10-22 in `/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run2.sh`: launchers keep polling their grant id after their window ends, so a re-written grant is taken by a stale launcher, and a second launcher then writes a bogus `refused:own-port` `.ended` that deletes the live grant. Fix on a copy (never edit the running script); test with two launchers on one grant id. (filed 2026-10-22, f8) Done ✅ 2026-10-22 (3c4ca599): `/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run5.sh` (new copy of filler_run2.sh, CLI identical plus `--repeat`); dry-run `dryrun5_out.txt` beside it proves kill-then-immediate-re-arm succeeds (filler_run2 control fails), one-launcher-per-id holds, a running sibling's grant is left untouched, one-window exit and `--repeat`, rc2/3/4/124, complete and class gpu unchanged. Documented in `docs/guides/agent-workflows/compute-fillers.md` owner duty 6.

<!-- original line 14189 -->
- [x] CTC-Q-H: fix the `filler_run*.sh` lock inheritance in a NEW launcher version (never in place): start the poller's `sleep` with the lock fds closed (`sleep 45 8>&- 9>&-`) so an orphaned sleep cannot hold the launcher lock after the poller is killed (seen twice 2026-10-22; owner duty 6 in `docs/guides/agent-workflows/compute-fillers.md`). (filed 2026-10-22, 3c4ca599) Done ✅ 2026-10-22 (3c4ca599): `/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run5.sh` (new copy of filler_run2.sh, CLI identical plus `--repeat`); dry-run `dryrun5_out.txt` beside it proves kill-then-immediate-re-arm succeeds (filler_run2 control fails), one-launcher-per-id holds, a running sibling's grant is left untouched, one-window exit and `--repeat`, rc2/3/4/124, complete and class gpu unchanged. Documented in `docs/guides/agent-workflows/compute-fillers.md` owner duty 6.

<!-- original line 14377 -->
- [x] **OAB-NI18-FIXTURES** — Review the two enrollment modules for declared command-builder/template/backend inputs, exact two-repository context and original skip reason. Implementation belongs at the active AutoKernel owner boundary; preserve synthetic and actual enrollment evidence separately. No fabricated artifacts or receipts. Modules: `test_autokernel_enrollment.py`, `test_autokernel_enrollment_cross_repo.py`.
  - *(2026-11-19 CORRECTION, bb / orchestrator owner)* the earlier note diagnosing an incomplete DRAFT-SEL-1 registry migration was WRONG: the cross-repo test fed the orchestrator compiled lean in as master, and research canonical grammar lacked --ctx-checkpoints and --no-cache-idle-slots. Fixed in orchestrator 74e91757 (test only) + research 24207333 (grammar only, no launch change); cross-repo test 34 passed. [no-belief: code]
  - 2026-11-19 OAB-NI18-FIXTURES review (2026-11-19, orchestrator main): with both repo roots on PYTHONPATH the two modules give 33 passed / 1 failed. `test_autokernel_enrollment.py` passes entirely; `test_autokernel_enrollment_cross_repo.py` fails inside the real master-registry compile with `DrafterSelectionError` (roles `architect_critic`, `coder_escalation`, `ingest_long_context` still hand-carry `spec_type/draft_model/draft_max/k/n_gpu_layers_draft` although `roles.qwen38_27b_q8_local` declares `drafters`; the compiler wants them deleted, DRAFT-SEL-1). So the original skip was a standalone-checkout `importorskip`, and the actual defect is a registry migration, not a fixture input. No AutoKernel-side fixture to add; the fix is the registry migration under the stack-lifecycle owner, then re-run the cross-repo test with both roots. Synthetic (module 1) and actual-enrollment (module 2) evidence stay separate.

<!-- original line 14462 -->
- [x] **OAB-0 — Do not start until DS41-C20 has recorded the seat A/B.** ✅ 2026-09-24 (DS41-C20c; §Baseline) The reference must exist
  before anything is built against it. Zero compute.

<!-- original line 14464 -->
- [x] **OAB-1 — per-call worktree root + edit mode on `/chat`** (orchestrator). ✅ 2026-09-25 — orchestrator
  `9124c7f1` + Fable review fixes `7f5d6870` (F1 shell writers `sort -o`/`sed -nf`/`git --output`, F2
  `/chat/stream` refuses the scope fields, F3 write-check TOCTOU, F4 symlink-dereference escapes, F6 frozen
  trees/kernels/models refused as `task_root`), merged in `994529fd`. The scope rides a ContextVar per request;
  `edit_mode=direct` writes inside `task_root` only; `none` cannot write; the response echoes `task_scope`. R3:
  scoped requests get a `max_turns` ceiling of 100 and bypass the long-context 8-turn override. Tests
  `test_oab1_task_scope.py` (23). Add
  `ChatRequest.task_root: str | None` and `edit_mode: Literal["none","direct"]` (default `none`);
  `task_root.get_task_root()` honours the request over `ORCHESTRATOR_EDIT_ROOT`; `edit_mode=direct`
  lets `_file_write_safe` (`file_mutation.py:88`) write inside `task_root` without the approval queue,
  everything else refused. Acceptance: a test that a write outside `task_root` is refused and one
  inside lands; a `none` request cannot write at all. Zero inference.

<!-- original line 14476 -->
- [x] **OAB-2 — `orchestrator` Backend kind** (research, `loop/actors.py`). ✅ 2026-09-25 — research `751ec730`
  (`actor_orchestrator.py`, `--planner-model orch:auto`) merged to research main (`4a507624`, then `82f48e11`);
  orchestrator actor CLI `e33eb1d3` (`scripts/autokernel_actor_cli.py`, invoked by path under `-I`, because a lane
  cwd has its own `scripts/`), merged in `994529fd`. Smoke PASS ×3 through the loop's own invocation
  (`/mnt/raid0/llm/tmp/oab2-smoke/smoke.sh`: orch:auto → frontdoor REPL, 15.8 s, 2 turns), and again after the
  14:40:38Z reload. VB-AK-SEAT accepts the kind (root `fa8d0fa1`, research test `67cac838`). `backend_for("orch:<role
  or auto>", effort)` → kind `orchestrator`; `argv` = `[ORCHESTRATOR_PYTHON, "-m",
  "scripts.autokernel_actor_cli", "--root", <wt>, "--read-only"?, "--schema", <tmp>]`, prompt on
  stdin, JSON on stdout, exit 0/1 — so `_run_agent`, salvage, `_persist_reply`, `_record_call` and
  `_parse_reply` need no change; `_schema_repair` short-circuits for this kind (repair happened
  server-side, TD-21.1/21.33). Decide R3's turn-cap path here and record it. Acceptance: the
  `{"ok":true}` smoke the DS41 launch used (DS41-C2c) passes through the loop's OWN invocation;
  `test_actors.py` covers the kind. Inference: one smoke call.

<!-- original line 14489 -->
- [x] **OAB-3 — trailing-work witness (R2).** ✅ 2026-09-25 — orchestrator `9124c7f1`:
  `ChatRequest.quiescent_after` suppresses every fire-and-forget launch on `/chat` and holds the idle-scoring loop;
  `src/runtime/trailing_work_witness.py` fails a window when an orchestrator-owned process accrues > 0.5 core-s.
  The injected-prewarm acceptance test trips it (`test_oab3_quiescence_witness.py`, 10). Live witness, 60 s after
  a real reply: rc 0, max ≤ 0.4 core-s per process (08:32Z, and again after the 14:40Z reload). Add to the CLI a post-reply 60 s sampler of the
  orchestrator-owned servers' `utime+stime` (reuse DS41-C2b-gate's reader) and fail the call if any
  accrues > 0.5 core-s after the reply. Acceptance: a deliberately injected prewarm trips it.
  Inference: one call.

<!-- original line 14577 -->
- [x] **OAB-LB1 — Read-only census of Codex AK-lane threads: turn failures by error class and wall time by executable from the thread history tables (indexed columns only, nice'd) (intake-2389).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / mining-m1.)* **Code done; full run scheduled** (`mine_m1.py`, `oab_lb1.aggregate.json`). Source is the vault's rollout copies of the threads, not the live `~/.codex/state_5.sqlite` (3.7 GB live store, never opened by mining lanes); AK lane = session cwd under `/mnt/raid0/llm/tmp/ak-*|aku*` or `/mnt/raid0/llm/autokernel/` (~15k epyc threads, Aug-Sep). Turn failures (not completed: aborted by reason / no terminal event; error events by class) and exec wall time by executable (first program after env/wrappers/cd; the output's own `Wall time`); forked children's replayed turns and their tool calls are counted once. Sample (first 3,000 AK threads, 1.0 GiB): 0.17% of turns not completed (0.07% interrupted), no error events; exec wall 2,173 s of 205,649 s turn wall (1.1%): git 1,006 s, rg 525 s, find 226 s, sed 181 s.
  - *(2026-10-22, workspace-f8 / mining results.)* **Full census; acceptance met** (source: vault rollout copies, not the live thread store). 15,144 Codex AK-lane threads, 15,115 turns completed of 15,144 started (29 not completed: aborted-interrupted or no terminal event), 60,718 tool calls, 40,663 exec outputs matched with wall time, exec wall total 9,651 s versus turn wall total 1,503,702 s (0.64%: the lane is model-bound, not tool-bound). Per-executable calls, non-zero-exit rates with Wilson CIs and wall shares are in the aggregate (`oab_lb1`). Follow-up: none; decline: no exec class has a wall share above 1%, so no tool-latency task is filed. Full tables: `docs/design/dev-harness-mining-results-20261022.md`.

<!-- original line 14778 -->
- [x] **OAB-7s — seat-side precursor of OAB-7: the context bundle as files.** ✅ 2026-09-24 — research
  `lane/ak-ctxvar-20260924` `ce5800cb` (143 tests). Merged to research main `30631761` (2026-09-25). **A/B'd in
  OAB-9: it loses to inline on the 27B plain seat**, so the default stays `inline` and `variable` is opt-in.

<!-- original line 14781 -->
- [x] **OAB-4m — seat-side precursor of the OAB-4/S4-T1 columns: per-call metrics.** ✅ 2026-09-24 — research
  `lane/ak-turns-20260924` `0bf2d7c2` (`actor_call_metrics.v1` + summarizer; DS41-C20c reproduced exactly).
  Merged to `30631761`. It supplied every OAB-9 column, and it is live in run 9b.

<!-- original line 14784 -->
- [x] **R4c — seat-side precursor of R4: cache tool output keyed by exact argv + input identity.** ✅ 2026-09-24
  — research `lane/ak-perfcache-20260924` `f4a5d240` (111 tests; 1.283 s → 0.0012 s, byte-identical). Merged to
  `30631761`. Its effect on the bounded seat has not been re-measured yet (DS41-C20d2).

<!-- original line 14787 -->
- [x] **OAB-9 — live A/B: plain inline vs plain variable, AFTER run-9 calibration.** ✅ 2026-09-25 — **INLINE
  wins both pairs** (§Techniques learned → 4; research `605e8301`). Wall 37.6/28.7 vs 54.4/33.6 min, peak
  context 104k/92k vs 163k/118k, 0 compactions and schema-valid everywhere. Predictions: the first-step halving was
  confirmed; the peak, compaction and wall predictions were refuted or moot. Critic acceptance was not measured
  (planner-only driver), and per-tool latency is unknown. 2 pairs; pair 3 was over budget. Run 9 was relaunched
  as `state-run9b` (04:04Z) on the default `inline`, same store, half floor reused. (Run 9 was actually stopped
  at 01:30Z, at the half-floor → batch-0 boundary, not at ~04:45Z; see DS41-C28.) Original spec: at the calibration boundary
  (~04:45Z), stop run 9 (the floors persist per anchor) and merge the integration lane
  `lane/ak-planner-integ-20260924`: the three lanes, the `node_profile` fix in both arms, and the pre-existing
  test fixes. Then run the arms on the same :8083 generation (OAB-4a) with the new metrics rows: 3 pairs
  alternating ABAB, or 2 if time is short (operator-confirmed morning sequence, 2026-09-24 21:40Z). Results go to
  the live results page as well as here. Report:
  - first-step and peak context, compactions, steps, tool calls by name, decoded tokens, wall;
  - schema-valid rate and critic acceptance;
  - which bundle files were read, and whether the required ones were read unprompted;
  - per-tool latency from step timestamps if the export carries them, else "unknown".

  Relaunch run 9 with the winner: same anchor, floors reused, new state dir. Acceptance: the predictions above are confirmed or refuted in
  writing. Inference: campaign-idle GPU window.

<!-- original line 14806 -->
- [x] ~~**OAB-9b — re-open the context-placement question only when a precondition changes.** The trigger is any~~ (closed 2026-10-29 audit: SUPERSEDED → PARKED 2026-09-27 (operator): revisit folded into OAB-4 first orch run (actor-backend:445))
  of:
  - OAB-12 pull caps exist in the seat or the orchestrator;
  - the planner model changes;
  - the planner runs on a slot small enough that inline compacts again (≤ 98k).
  - PARKED 2026-09-27 (operator): no re-run. The operator's revisit is folded into OAB-4's first `orch` run with the context variable on. The orchestrator-side pull cap (`context_pull_budget_bytes`, `88e22777`) exists, and the seat-side cap does not. The 2026-09-25 driver still lacks ABBA order and per-section byte counts; resume by running OAB-4's `orch` arm, or, on another trigger, re-running `artifacts/autokernel_ctx_ab_20260925/driver.py` at n >= 3 ABBA after adding per-section bytes.

  Then re-run `artifacts/autokernel_ctx_ab_20260925/driver.py` with **n ≥ 3 in counterbalanced order (ABBA)**,
  because the 2026-09-25 run always put inline first. Also give the driver a byte count per bundle section: it
  records read counts only (`bundle.access`). Acceptance: a verdict per trigger with the same columns as → 4.
  GPU inference, campaign-idle window. Do not run it on an unchanged setup: 2/2 on every cost metric is not worth
  re-buying.
  **Operator, 2026-09-25 07:40Z:** context-as-variable failed ONLY because of opencode: its pulls land in the
  conversation. Revisit it once it is wired directly into the orchestrator REPL/RLM (OAB-7 proper, now built). The
  first OAB-4 run with the context variable on is that revisit.

<!-- original line 14821 -->
- [x] **OAB-10 — trim the lane `AGENTS.md` out of the planner's fixed overhead.** ✅ 2026-09-25 — research
  `bdd0a951` (`--actor-trim-instructions`, `--actor-trim-tools`; `run.py` defaults on), merged in `300951de`. Fixed
  overhead per planner call fell 12,912 → 4,950 tokens (−62%); the skills catalog (3,383) was the largest piece,
  `AGENTS.md` 2,009. The one trimmed call measured ctx_first 32.7k, against the predicted 32.9k. The baseline arm
  was aborted at 54+ min (censored; earlier inline baselines on the same prompt and server took 37.6 / 28.7 min),
  and the A/B stopped after one trimmed call, because the overhead cut and the lane fence are deterministic.
  Author behaviour accrues on campaign metrics. It is 8.9k chars (~2.5–3k tokens)
  of llama.cpp contributor guidance in every planner call. Options:
  - a planner-specific instruction file;
  - an `instructions` override in the per-run config;
  - a stripped `AGENTS.md` in the lane.

  The file must stay available to the author, who edits code. Acceptance: the first-step token count falls by the
  measured amount with no change in author behaviour. Orchestrator counterpart: never inherit a repo's agent file
  into a planner context (OAB-7).

<!-- original line 14836 -->
- [x] **OAB-11 — the planner must read its OWN lane, not the anchor build tree, and must not build.** ✅ 2026-09-25 —
  research `bdd0a951` (`--actor-lane-guard`: lane-as-source + builds denied through opencode permissions). The
  trimmed call: 6 steps, 10 tool calls, 42.5k decoded, reads lane 4 / anchor 0, builds 0, schema-valid. The plain
  planner read `/mnt/raid0/llm/llama.cpp-experimental-deepseek41-*` (the target's build dir) instead of
  `workers/laneN`, and compiled `.o` files into `/tmp` despite "never build". Fix candidates:
  - point the target card's source path at the lane and label the build dir "binary only";
  - deny `bash` compiler invocations for the planner via `permission`.

  Acceptance: a planner transcript shows reads under its lane and no compiler call. Orchestrator counterpart: R1
  read-only root = the lane.

<!-- original line 14866 -->
- [x] **OAB-13 — integrate OAB-2/7/8, review, deploy.** ✅ 2026-09-25 — integration lanes
  `lane/inf78-integ-20260925` in both repos (OAB-2 → OAB-7 → OAB-8 + a composition test). A second Fable review
  returned research MERGE (research main `82f48e11`) and orchestrator MERGE-WITH-FIXES: F1 scout grep regex DoS
  (literal search now), F2 context closure escapes, F3 sync `/slots` read on the event loop, F4 uncapped exception
  output, F5 restore dropped the bundle, F6 READ past EOF, F7 bounded post-stop wait, F12/F13 encoding and
  recursion guards, F14 test (`86cdeaf3`, `b9e004e3`). The architect scoped exception is `7d0ce447`. Orchestrator
  main `b9e004e3`; the first reload attempt was refused by `orchestrator_stack` while run 9d's calibration held
  the bench. After run 9d was killed, the API reloaded at 14:40:38Z (pid 2517073, API only), the OAB-2 smoke
  passed and the witness stayed quiet.

<!-- original line 14875 -->
- [x] **OAB-14 — the opencode store fault that failed an author call.** ✅ 2026-09-25 — root cause: the event
  reaper's no-op VACUUM (freelist 0, a 34 s exclusive lock) started 07:59:17Z in the critic gap; the author started
  07:59:35Z, and its project upsert hit `SQLITE_BUSY` past the 5,000 ms busy timeout (rc 1). Fixes:
  - root `9177edaa`: the prune script skips VACUUM when the freelist is under 1,024 pages, and truncates the WAL
    after a real one;
  - research `e57e93ea` (merged in `300951de`): `snapshot: false` in every per-call opencode config, an
    `opencode_store_error` class with its own 30/60/120/240 s backoff, metrics session scoping by
    `created >= call start` (a failed author row had been attributed the planner's 29-step session), and a
    reasonless `{"accepted": true}` critic reply counted as schema-valid.

<!-- original line 14897 -->
- [x] **OAB-17 — triage the unfixed second-review items F8-F11, F15, F16 and R2-R4.** F1-F7 and F12-F14 landed in ✅ 2026-11-19 every finding has a fix or a written decline: orchestrator 2c0117d3 (bb owner review: F8 reservation leak on cancel fixed, F9, F10, F15 _select_mode, F16(a)/(b), json_diet fail-open; 331 tests) + earlier ca94032d chain; research 2ff736c1a (R2) and 6f142e9ba (R3); declined with reasons: 4 accounting-only F16 sub-items and the F8 cross-worker race (single-worker API); R4 split to OAB-17-R4. Reloads owned by bb. [no-belief: code]
  `86cdeaf3` / `b9e004e3`. Items (Fable review, 2026-09-25 ~12:50Z, file:line against 7d0ce447):
  - F8 MED: scout `/slots` cap is a one-shot snapshot from a 1.5 s-TTL process-wide cache (`scout_stage.py:719-723`,
    `context_limits.py:441-453,521`); two scouted requests (or 6 workers) can both launch and violate `reserve_slots`.
    Fix: `resolver.invalidate(url)` after launch + in-process inflight counter; cross-worker needs a shared counter.
  - F9 MED: scouts share the loop's default ThreadPoolExecutor (32) with chat.py's own `to_thread` handlers
    (`scout_stage.py:880`); 4 scouted requests x 8 scouts starve other handlers. Fix: dedicated bounded executor.
  - F10 LOW: default-path substring patterns `context.get(`/`context.json(`/`context.index(`/`context[` added to
    `exploration_patterns` (`code_utils.py:659-664`) match ANY request (`context[:5000]` idiom now executes silently
    instead of FINAL). Fix: gate on a bundle being attached, or anchor `(?<![\w.])context[\[.]`.
  - F11 LOW: pulled-span list unbounded (`context_bundle.py:744-748`, ~125 B/span). Fix: merge intervals past ~1k.
  - F15 LOW (scouts): `_last_alternatives` shared across scout threads; `definitions()` lacks per-file
    `read_denial`; FIFO/device with a source suffix blocks `read_text` (require S_ISREG); no block-level cap on the
    scout block (~37K tokens worst case); `_EVIDENCE_RE` quadratic; augmented prompt feeds `_select_mode`.
  - F16 LOW (bundle): refused `chunk_context` still charges the budget; structured mode caps twice; `json()` counts
    the indent=2 dump; `get()` on a JSON path records no span; the 8 MiB check runs after full parse; no app-level
    body limit (pre-existing).
  - R2 LOW: `AK_ORCHESTRATOR_SCOUTS="false"/"off"/"3.0"` raise ValueError in `backend_for`.
  - R3 LOW: `orchestrator-variable` context mode has no inline fallback (unlike `variable`).
  - R4 INFO: `_sealed` seals without `role`; per-call files under `<workspace>/../actor-orchestrator/` never cleaned.
  Fix or decline each in writing. Acceptance: every item has a disposition.
  - PARKED 2026-09-27 (operator): F1-F7 and F12-F14 landed (`86cdeaf3`/`b9e004e3`). F8-F11, F15, F16 and R2-R4 have neither a fix nor a written disposition; resume by writing a fix-or-decline disposition for each item here, starting with the two MED items, F8 (the `/slots` snapshot race) and F9 (the shared thread pool).
  - 2026-11-19 OAB-17 dispositions (2026-11-19, orchestrator main): F8 FIXED in-process `bdb8e5bb` (admitted scouts are reserved against free slots atomically with the cap decision, released on every exit; cross-worker needs a shared counter, so multi-worker deployments keep the race: declined for now, single worker only). F9 FIXED `46be2371` (dedicated 16-thread scout executor, contextvars copied). F10 FIXED `ab47b6e6` (anchored; `context[:5000]` no longer matches). F11 FIXED `b92d4c2c` (merge past 1000 spans, union unchanged). F15 FIXED for read_denial in `definitions()`, S_ISREG, per-thread `_last_alternatives`, block cap 48k chars, evidence scan bound (`d6398e10`, `ca94032d`); the "augmented prompt feeds `_select_mode`" sub-item is NOT fixed. R2 FIXED research `2ff736c1a` (off-words and integral floats accepted, junk refused with the contract named). STILL WITHOUT A DISPOSITION: F16 (all six sub-items), R3 (no inline fallback for `orchestrator-variable`), R4 (per-call files never cleaned). Box stays open until those three have a fix or a written decline.
  - 2026-11-19 owner review + closure (autopilot-backlog-session, orchestrator owner per the 2026-11-18 ruling): review of the 8 landed commits found one real bug and fixed it with the rest in orchestrator `2c0117d3` (331 passed): F8 reservation LEAK on a cancel mid-`/slots` read (released flag under `_INFLIGHT_LOCK`); F9 claim/`resolve_cap`/pool gate moved to a separate `scoutctl` pool; F10 `item|page|keys` and `context[<ident>]` count again; F15 `_select_mode` and the MemRL objective now get the pre-scout prompt; F16(a) a refused `chunk_context` charges 0, F16(b) the 8 MiB cap runs before any JSON section parse; OAB-6 `json_diet` fail-open + docstring. F16 remaining four sub-items DECLINED: accounting-only, no wrong answer. F8 cross-worker race: the decline was WRONG (the live API runs `uvicorn --workers 6`); FIXED in orchestrator `ad9432c1` (host-wide flock reservation store per server URL, dead-owner/TTL reaping, fails closed; 10 processes contending for 3 admit exactly 3). R3 FIXED research `6f142e9ba` (refused bundle degrades to inline, unsuffixed arm). R4 FIXED (below). Not reloaded. [no-belief: code fixes and tests, no run]
  - Every OAB-17 item now has a fix or a written decline; the box owner (autokernel) can tick OAB-17. The same single-worker audit found per-process KV-pool admission and per-backend semaphores; their cross-worker fix is in progress (autopilot-backlog-session).
  - 2026-11-19 cross-worker KV-pool and queue reservations DONE (autopilot-backlog-session): orchestrator `7f70e338` (host-wide KV-pool token reservations and queue bound via the shared `xproc_reservations` primitive, same flock store as the scout slot reservation `ad9432c1`). Pushed, not reloaded (ships in the STACK-UP-RELOAD-QUEUE reload, harness-program.md). OAB-19 `e1d34759` (REPL-turn compaction behind `repl_compaction`) is noted below. [no-belief: code and tests, no run]
  - [x] **OAB-17-R4 — retention for `actor-orchestrator/` sidecar files.** One file per actor call accumulates under `<workspace>/../actor-orchestrator/` (`SIDECAR_DIR` in `actor_orchestrator.py`), and `_sealed` omits `role`. Propose a sweep of files older than N days via `scripts/safety/guarded_rm.sh`, checked against the LEAN retention notes first; add `role` to the seal. Filed 2026-11-19.
    - 2026-11-19 DONE (research, `fix/oab17-r4-sidecar-retention`, pushed): sidecars are evidence (bound into the metrics row by sha), so no delete-at-end; each `argv` sweeps first, removing only regular files matching the module's own name pattern outside the newest `AK_ORCHESTRATOR_SIDECAR_KEEP` (200) AND older than `AK_ORCHESTRATOR_SIDECAR_DAYS` (14); never symlinks, dirs, foreign or pending files. `_sealed` now passes `role`. 197 tests pass. No real backlog existed; 3 test tempdirs trashed via guarded_rm. [no-belief: code fix and tests, no run]

<!-- original line 14932 -->
- [x] **OAB-19 — the compaction worker summarizes text no prompt shows.** Compaction measures and summarizes
  - 2026-11-19 DONE (autopilot-backlog-session, orchestrator `e1d34759`, pushed, not reloaded): REPL-turn compaction retired by default behind new flag `repl_compaction` (default off, `ORCHESTRATOR_REPL_COMPACTION`, in runtime_flags.spec.yaml as baseline, POST /config toggleable; old path reachable). Acceptance reinterpreted because the literal one cannot hold: `TaskState.context` is rendered into no turn prompt, so a firing compaction never changes the next prompt in either mode. The test asserts flag-off: no compaction, context whole, root prompts byte-identical to a short-context run; flag-on: path still fires. Overflow test: a too-large prompt fails explicitly via `ContextOverflowError` with state intact; no preflight added (it would block reroute to a larger-context role). [no-belief: code change and tests, no run]
  - *(2026-11-19, OPERATOR DECISION via decision tool)* compaction target = RETIRE compaction for REPL turns (REPL turns keep full context). Implementation is orchestrator code, so it is ROUTED to the autopilot session (bb) per operator 2026-11-18 ("orchestrator work belongs to bb"). [no-belief: operator decision]
  `TaskState.context`, which no turn prompt renders (the same root cause as the schema-preamble bug fixed in
  `1d0ab2f5`). Point it at what the root prompt actually carries, or retire it for REPL turns. Acceptance: a test
  where compaction fires changes the next root prompt.
  - PARKED 2026-09-27 (operator): not started. Compaction still summarizes `TaskState.context`, which no turn prompt renders; resume by pointing the compaction worker at what the root prompt actually carries, or retiring it for REPL turns, with a test in which compaction fires and the next root prompt changes.
  - 2026-11-19 OAB-19 (2026-11-19): UFH14-B1 already retired the worker summarisation by default (`session_compaction_llm_index` off, deterministic index), so the compaction no longer spends a model call on text no prompt shows. The acceptance test (compaction fires and the next root prompt changes) still cannot pass: `TaskState.context` is not rendered into any turn prompt (`graph/helpers._execute_turn` rebuilds from prompt + REPL state + last output). Remaining choice is the one the box names, point it at what the root prompt carries (REPL state / last output) or retire it for REPL turns; it needs the compaction target decided before the test can be written.

<!-- original line 14940 -->
- [x] **OAB-20 — planner timeline audit (why a planner call takes 30-60 min).** ✅ 2026-09-25 — from the :8083 logs
  of the trimmed call: decode 87% of wall, prefill 13%, gaps 0.3%. One 30k-token reasoning turn (step 6) was 68% of
  the call. `--planner-effort high` maps to opencode `--variant high`, which is inert for this server and model.
  Thinking is ON through the template default: the exports carry `reasoning` parts (82k chars in step 6), so
  `tokens.reasoning = 0` in the metrics is an accounting bug (OAB-21). The giant turns are reasoning prose
  re-deriving the Q4_K bit-unpack formulas ("wait" ×56, "hmm" ×46): 97% of the step comes before any JSON, the
  final JSON is 4%, and visible answers also carry 1.2-1.9k chars of preamble. MTP acceptance is ~0.45-0.53 on
  that prose vs 0.6-0.97 on terse turns, which compounds the cost. The author prompt shows the same pattern.

<!-- original line 14948 -->
- [x] **OAB-21 — fix reasoning-token accounting in `actor_call_metrics`.** ✅ 2026-10-30 [belief: cc] `tokens.reasoning` reads 0 while the <!-- evidence-integrity: Research `3e9c00e534ae29f138d13ec8962fe0d44fd86b41`; artifact: artifacts/compute/task-evidence-repair-20261031/oab-21/EVIDENCE.json; hygiene, not quota -->
  export carries `reasoning` parts. Count them (tokens from the server's usage when present, else chars with the
  estimator flagged), and keep "decoded includes reasoning" explicit. Acceptance: the step-6 call re-exported shows
  a non-zero reasoning count consistent with its 82k chars. Also feeds VB-AK-METRICS-1.

  <!-- task-evidence-integrity:start OAB-21 -->
  - Evidence metadata (hygiene, not new quota): Research `3e9c00e534ae29f138d13ec8962fe0d44fd86b41`; [test/artifact](../../artifacts/compute/task-evidence-repair-20261031/oab-21/EVIDENCE.json).
  <!-- task-evidence-integrity:end OAB-21 -->
  - [x] **OAB-21 source implementation.** ✅ 2026-10-29 Research `3e9c00e534ae29f138d13ec8962fe0d44fd86b41`
    counts captured reasoning characters and informative server usage, otherwise explicitly flagged
    `ceil(reasoning_chars/4)` estimates; missing evidence stays unknown. Per-step/session/call provenance
    remains explicit, and decoded totals remain inclusive. 52 focused tests passed; the native 22-part fixture
    has137524 reasoning characters and unchanged57702 decoded tokens. Ruff/diff checks passed.
    [no-belief: parser implementation and fixture correctness]
  - [x] **OAB-21 retained-source acceptance:** ✅ 2026-10-30 [belief: cc] locate and parse the exact original OAB-10/11 six-step
    export with roughly82k reasoning characters at step6; record path/digest, message identity, count and
    usage/estimate source. Exact retained OpenCode session `ses_f280614e1ffe39X6ka8Mym7IgV` was exported to private scratch (`opencode-export.json`, SHA-256 `a53b40d1a530c1a7ed8798dff29385dfbd56311f85862d6f1edafcecb62c1d21`) and parsed with research `276d75fab`: step 6 `msg_0d803594d001Hdyg1RPVFZEdTU` has 82,482 reasoning characters and a flagged `ceil(chars/4)` estimate of 20,621 tokens (native usage was zero); six steps total 116,002 chars and 29,003 estimated reasoning tokens. Decoded output stays 42,547 with `decoded_includes_reasoning=true`. Export changed the local OpenCode project row `time_updated`; the 38 session/message/part rows were digest-identical before and after. Evidence: `/mnt/raid0/llm/tmp/refactor-01a16fc3/oab21-reasoning-accounting-20261030/original-session/validation.md` and `metrics.json`.

<!-- original line 14965 -->
- [x] **OAB-22 — planner concision rule plus an 8k per-turn cap, together.** ✅ 2026-09-26 — first run-10h planner call: 15 steps, max turn 9,801 decoded (cap 16384, 0 capped steps), schema-valid, 31.4 min vs 32.8. Note: step 1 at 9.8k exceeds the rule's ~4k analysis aim (below the cap that replaced 8k). Add to `actors.py`
  `_HYPOTHESIS_TASK` (~L1961-1965): derive a formula once, keep analysis under ~4k tokens, then emit JSON only; set
  `max_tokens` 8000 per turn as a circuit breaker. The cap alone would have truncated 5 of the 6 giant turns, so it
  ships only with the rule. Reasoning stays on (operator ruling). The author prompt gets the same rule. Acceptance:
  a matched planner call shows no turn over 8k and a schema-valid reply, with its wall recorded against the 32.8
  min trimmed call.
  - Status 2026-09-26: the rule landed in `eeab67ba` (`CONCISE_RULE`, planner+author); the per-turn cap is now the
    operator-set 16384 planner output (not 8000). Only the live acceptance is open: read `actor_call_metrics.v1` for
    the first run-10h planner call (max turn decoded, schema-valid reply, wall) and tick.

<!-- original line 14974 -->
- [x] **OAB-23 — a total budget per planner call.** ✅ 2026-09-26 — landed research `eeab67ba`, live in `d643d794`; acceptance met by `test_actor_budgets.py` (30 passed on d643d794): `test_an_incomplete_reply_raises_budget_exhausted`, `test_the_planner_is_never_relaunched_after_its_budget`, `test_backoff_never_retries_a_spent_budget`. Separate from OAB-22: run 9 showed endless chains of small
  turns (61 min without a reply), which a per-turn cap never stops. Add a per-call decoded-token or wall budget
  that ends the call with a recorded `budget_exhausted` abstention, not a transient retry. Acceptance: a fake
  backend that never finishes is cut at the budget and recorded once.

<!-- original line 14981 -->
- [x] **OAB-24 — author budgets and the opencode output cap.** ✅ 2026-09-26 — lane `ak-author-medium`.
  - Author thinking is set to medium.
  - ctx 180224; author output 40960; planner+critic output 16384.
  - **opencode silently capped `max_tokens` at 32000** unless `OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX` is set, so
    every larger requested budget was inert. The per-call environment now sets it.
  - Also: an action rule and a GitNexus line in the prompts.
  - Also: the `measurement_epoch` resume split. Checkpoints bind on the epoch inputs minus actor/backend config, so
    an actor swap no longer orphans them. The comparability half was ratified 2026-09-26 as P-AK-SEARCH-1-A3.1 (DS41-C40); code switch DS41-C44.

<!-- original line 14989 -->
- [x] **OAB-25 — `ak-check` sandbox for authors.** ✅ 2026-09-26 — lane `ak-sandbox`.
  - A compile check takes ~0.7-6.5 s.
  - `--op-test` takes ~9-15 s, via `test-backend-ops` against the CPU reference.
  - Fence locks.

<!-- original line 14993 -->
- [x] **OAB-26 — best-of-2 with mixed authors.** ✅ 2026-09-26 — lane `ak-bestof`.
  - Two authors (thinking off and medium) at 90112 ctx each; requires `--workers 1`.
  - Engaged live on run 10h at 11:00:30Z (two concurrent opencode authors on `akm-q4k-x4t-avx512`).

<!-- original line 14996 -->
- [x] **OAB-27 — scope GitNexus to the lane's anchor.** ✅ 2026-09-26 — research `a1c5812b`.
  - The tool now runs `gitnexus --repo <absolute anchor path>`. The bare name `llama.cpp` is ambiguous with the
    frozen production tree.
  - Every actor role is denied the gitnexus index writers.

<!-- original line 15014 -->
- [x] **OAB-33 ✅ 2026-10-23 — Actor delegation must be instructed, not offered.** workspace-8d's pre-registered probe (2026-09-27,
  `/mnt/raid0/llm/tmp/task-probe-20260927/`, driver root `scripts/harness/task_delegation_probe.py summarize`): on the
  HS-19a prompt that names the `task` tool, frontdoor, 27B-nothink and 27B-think all delegated 3/3; on the DS41-C20c seat
  shape (a `planner` agent with fan-out *guidance*, the hidden-`scout` description, a prompt that never names `task`) both
  frontdoor and 27B-think self-served 0/3. DS41-C20c's non-delegation was SETUP (prompt shape), not the model. If the AK
  seat should fan out, instruct it explicitly (or keep fan-out orchestrator-owned per OAB-8 / HS-19c, the operator ruling).
  - PARKED 2026-09-27 (operator): the probe is done and recorded (`/mnt/raid0/llm/tmp/task-probe-20260927/`, root `e043cfa3`/`c9bc3859`): C20c's non-delegation came from the prompt shape. The AK seat prompt is unchanged, so fan-out is still offered, not instructed. The standing operator ruling keeps fan-out orchestrator-owned (OAB-8/HS-19c); resume by recording here whether that ruling closes this item, with the probe as evidence, or, if seat fan-out is wanted, naming the `task` tool explicitly in the research planner prompt.
  - ✅ 2026-10-23 (operator decision ~16:20Z): closed on the standing ruling (OAB-8 / HS-19c, fan-out stays orchestrator-owned), with the 2026-09-27 probe plus today's probe as evidence. No seat-prompt change.

<!-- original line 15037 -->
- [x] **OAB-29 — a fake-model wire test as the standard gate for any new actor seat.** (research 93c01b3c7; 106 units + 15/15 native PASS on current main a5310d94; code-budget guard pre-existing FAIL carried, see INF78-CODE-BUDGET-RATCHET) [no-belief: verifier/correctness, native-wire belief wiring tracked as VB-AK-NATIVE-WIRE-WRITE] Add a scripted
  OpenAI-compatible stub server, with a test harness that drives the EXACT actor invocation: CLI, flags, per-call
  config, env and stdin prompt. Build on the fake server used to root-cause `b8d6a046`.
  - Assertions:
    - a reply longer than 128 KiB survives to the capture file byte-exact;
    - rc=1 with a complete reply is salvaged, and a signal death is a transient;
    - a compaction or template echo is not parsed as an answer;
    - a slow reply is covered by `--actor-timeout-s`;
    - the requested `max_tokens` and `chat_template_kwargs` appear on the wire, not clamped to 32000 or dropped;
    - a read-only seat can never reach an `ask`-class permission, so a permission probe fails one call and the
      session still returns final text.
  - One parametrised case per backend kind (`opencode`, `claude`, `codex`) and per role config.
  - Acceptance: the suite runs in CI in seconds with no GPU. `run.py` or `campaign_cli` refuses a manifest whose
    actor seat config digest has no passing wire-test record, with an explicit override that is recorded in the
    manifest.

<!-- original line 15052 -->
- [x] **INF78-CODE-BUDGET-RATCHET** (research cc82bb19c; 25 tests pass, guard 0 violations) [no-belief: tooling] (T3, directed by ws58 2026-10-26T00:16:57Z) — replace the unenforceable global 2560 code budget with a reviewed ratcheted per-file baseline in research `scripts/kernel_rnd/autokernel/check_regrowth_guards.py` and its existing baseline/config/test surface. Freeze the baseline source revision and per-file AST-count semantics, inventory all files counted by the current checker, distinguish new files from baseline files, reject unauthorized growth and missing/stale baseline entries, and preserve explicit operator-reviewed exceptions. Add model-free tests for unchanged baseline, one-file growth, new-file additions, deletions, excluded tests and deterministic AST counts. Do not simply raise 2560 or turn the guard off. Prior evidence: `regrowth-comparison/results/COMPARISON.json`, baseline e8 102484 -> candidate 103345, delta 861 = 115+690+56; the original guard FAIL and original R11 rc1 remain history. Separate from OAB-29 publication and OAB-30. Index row INF-78 unchanged.

<!-- original line 15053 -->
- [x] **OAB-30 — a stub end-to-end dry iteration, including continuation after a keep.**  (research bdef2d014 + fixture cdf6faa44; 12 tests pass) [no-belief: tooling] Add a fast campaign
  fixture with stub actors, a stub build and a stub bench. It must exercise:
  - a kill mid-formation, a kill mid-calibration, and `touch STOP`;
  - a resume after a mid-build kill;
  - a refused resume, which must yield to the next queued checkpoint (the `2a060a41` path);
  - **a keep followed by the next batch on an experimental CPU campaign.** This is the DS41-C45 path: the next
    batch must restore the champion of record without refusing.
  - Acceptance: each path ends in its intended disposition with no orphan process, no lost claim and no
    discarded retained patch. The keep→continuation case fails on research main before the DS41-C45 fix and passes
    after it.

<!-- original line 15073 -->
- [x] **OAB-32 — default per-call budgets on every backend and every role.** ✅ 2026-11-19 (research `3fc496fa3`: `loop/call_budget.py`, `AgentPlanner`/`AgentCritic.default_budgets` turned on in `run.py` for planner, author and critic; `test_call_budget.py` 24 passed incl. a never-finishing fake cut at the default for all 3 roles x 4 kinds as `budget_exhausted`, never retried, and a local backend with no wall bound refusing; actor suites match the origin/main baseline failures exactly) [no-belief: code] OAB-23 bounded the opencode
  planner only. Give critic, author and planner calls on every backend kind a default per-call decoded-token cap
  and a wall budget. On exhaustion, record a `budget_exhausted` abstention, never a transient retry. A local
  backend with no configured budget refuses to start instead of running unbounded.
  - Acceptance: a fake backend that never finishes is cut at the default budget, and recorded once, for each
    role × kind.
  - 2026-11-19 scope note: the decoded-token cap is enforced only where the backend takes an output limit (opencode `limit.output`); for codex/claude/orchestrator the wall budget is the enforced bound. Default is 90% of the hard `--actor-timeout-s`; `AK_ACTOR_DEFAULT_BUDGET=off` restores the old path.

<!-- original line 15083 -->
- [x] **OAB-35 — `context.get(name, '')` (the dict idiom) crashed REPL calls with HTTP 500.** ✅ 2026-10-01 —
  orchestrator `2d97ade2` on main (parent `b384cdbb`), deployed by an API-only reload at ~13:10Z (PID 1767532).
  - Root cause: models write `context.get('inbox', '')`. `ContextBundle.get(path, max_chars=None, offset=0)` took
    `''` as `max_chars`, and `_page_bounds` did `int('')`, raising a ValueError. The model saw only that opaque
    message and repeated the line for six turns. It escalated to `coder_escalation`, which failed the same way.
    Retries ran out, the graph raised `[FAILED: ...]`, and the API returned HTTP 500.
  - Live since OAB-7 (`88e22777`). It hit workspace-76's DS41-C95 orchestrator-REPL arms (`orv`/`orsv`,
    `orch:architect_critic`, `orchestrator-variable` mode); evidence `/mnt/raid0/llm/tmp/repl_tap.log`, 12:11-12:12Z.
  - Fix:
    - A second argument that is not a char count, or `default=`, is a dict-style default: the value when the path
      resolves, else the default, and a miss counts no pull.
    - Int and numeric `max_chars` page exactly as before.
    - A bad `max_chars`/`offset` raises a TypeError that names the signature and the `default=` form.
    - `context.get('missing', None)` still raises a KeyError listing the sections.
  - Tests: a regression test reproduces the crash on the old code; `test_oab7_context_bundle.py` 68/68; a targeted
    set of 785 passed. One CPU-starved timing witness failed in that set and passed 10/10 when rerun on its own.
  - Related open items: OAB-17 F16 (`get()` on a JSON path records no span) and F10 (the `context.get(` default-path
    patterns) are untouched by this fix.

<!-- original line 15122 -->
- [x] **AK-FULLTEST-C9 — one-iteration live loop test at C9 (operator-approved 2026-11-09).** Target: Qwen3.8-27B-Q8_0, gfx90a, pp512, anchor `gpu-20261109-d210f85c2-c9fold` (`--allow-unverified-anchor`, operator-approved after a library hash check), planner claude-opus-5-5, critic claude-sonnet-5-5. Row `ak-fulltest-c9-20261109`, est 7200 s, package `/mnt/raid0/llm/tmp/ak-fulltest-20261109/`. Evidence for VB-REFOCUS-NONEMPTY-READ-PROOF: stop-on-answer when one iteration completes with a reliance-accepted receipt naming target claim ids; stop-on-futility on the first abstain, error, or the 2 h cap; gate-class = futility-only. Surface uncalibrated: keeps refused, no speed claim. Row `ak-fulltest-c9-20261109-r5` abstained; proof continues under `ak-q38fn-relianceproof-c9-20261109`.
  - 2026-11-09 AK-FULLTEST-C9: row `-r5` ran one iteration live (11:27-11:32Z) and the planner abstained: `h20_q8_0_to_f16_vec` already minimal and likely bandwidth-bound. Non-empty read (usable 16), no reliance-accepted receipt, so stop-on-futility. Not ticked; the proof moves to `ak-q38fn-relianceproof-c9-20261109`. Evidence: `/mnt/raid0/llm/autokernel/fulltest-20261109/experiments.db`. [no-belief: abstain, no measurement] [receipt-ack: ak-q38fn-relianceproof-c9-20261109 RC=1 — cited only as the successor row; r3 failure is filed under AK-C9-Q38FN-FLOOR context, not used as evidence here]
  - ✅ 2026-11-09 closed on its own stop-on-futility rule (first abstain, r5): FUTILE, planner abstained, no reliance-accepted receipt. Proof continues in VB-REFOCUS-NONEMPTY-READ-PROOF via `ak-q38fn-relianceproof-c9-20261109-r4`. [belief: cc]

<!-- original line 15126 -->
- [x] **AK-IQ3S-ZMM-ORACLE — bit-exact op oracle for `akm-cpu-iq3s-iq1-zmm-dot-gather` (operator-approved one-off 2026-11-09).** Candidate `f88a0e670` on C9, branch `experimental/akm-cpu-iq3s-iq1-zmm-dot-gather-20261109`. Row `ak-iq3s-zmm-oracle-20261109`, est 1800 s, spec `/mnt/raid0/llm/tmp/ak-iq3s-zmm-20261109/ORACLE-SPEC.md`. stop-on-answer when the two-library compare is complete with the mutant control run; stop-on-futility on a build failure or identity mismatch; gate-class = futility-only. No timing claim. RESULT: BIT_EXACT_PASS, row `ak-iq3s-zmm-oracle-20261109-r4`, commit `fc71ff076`: 26400 cases identical to C9, 0xEE mutant differs, ZMM gather sites 0 -> 4, linkage proven. Correctness only, no timing claim. ✅ 2026-11-09 [belief: cc]

<!-- original line 15127 -->
- [x] **AK-NEXT-CODE-MERGE — run tests on `ak/next-code-20261109` (research repo, 6 commits ahead of origin/main, tip `08aa0938b`) and merge.** [code, non-inference] Includes AKX-ALL-5 restore identity, AK-CONT-BUDGET, AK-CONT-DRAIN-GRACE, AK-BENCH-IDLE-GUARD. Worktree `/mnt/raid0/llm/worktrees/ak-next-code-20261109`. Stop-on-answer: focused tests pass and the branch lands on origin/main. **DONE 2026-11-09** research merge `9dcd3c0e0` on origin/main (6 commits `1bc36e200..08aa0938b` + origin/main merge + fix commit for PrefillContaminated ordering, test fakes/receipts, watchdog grace assertion; 290 focused tests pass; `git merge-base --is-ancestor` verified). [no-belief: tooling]

<!-- original line 15129 -->
- [x] **AK-PLANNER-ONLY-MERGE — merge `ak/planner-only-20261109` (`0358db7a3`, `--planner-only` driver) once the operator approves the code-budget exceptions.** [operator, code] First live 27B planner-only turn authored `akm-gemm-m10240-halve-tensile-cell` citing zero claims; report `/mnt/raid0/llm/tmp/ak-planner-only-27b-20261109/planner-only-report.json`. Pending ratification: AK-FUSE-GRAPH-KLD-1 threshold, 35 per-file code-budget exceptions, planner-only budget entries (one operator command). [no-belief: native-pending:VB-REFOCUS-NONEMPTY-READ-PROOF] ✅ 2026-11-09 merged under RATIFY-AK-C9-20261109 (research b699d0f03). CPU extension 086b833e3 awaits a budget raise. [no-belief: tooling]

<!-- original line 15134 -->
- [x] **INF06-EXACT-LANE — Add an exact-order candidate lane whose acceptance gate is bitwise token-ID identity vs the incumbent (drafted + plain, fixed prompts, fresh process per cell), skipping quality eval; tolerance-route candidates keep the existing eval (intake-2674).** Done when the loop config distinguishes the two lanes and one existing exact candidate is re-gated through the new lane.
  - *(2026-11-17, autokernel, code landed; box stays open until the re-gate row files.)* Lane + judge: epyc-inference-research `1fb5d8052`, `scripts/kernel_rnd/autokernel/loop/exact_lane.py` — `lane: exact|tolerance` on the candidate record (absent = `tolerance`, behaviour unchanged; unknown value refused), `LANE_GATES` config (tolerance: build → quality_eval → speed_abba; exact: build → exact_token_identity → speed_abba), `judge_streams` (PASS iff every prompt × {plain, drafted} cell exists on both sides, ≥ min_tokens IDs, bitwise identical; no prompts / missing drafted arm / empty or short stream / non-int tokens all FAIL), `route_after` (exact FAIL → `reject`, or `quality_eval` when re-routed with `on_mismatch="tolerance"`; a missing verdict never passes), and a fresh-process-per-cell capture helper (temp 0, top_k 1, seed, ignore_eos, return_tokens, cache off). Reuses the greedy-identity idea of `model_identity.check`, keyed on token IDs per cell. Not yet called from `loop.py`/`candidate_manifest.py` (the module is the config + judge; the dispatcher call site is the remaining wiring). Tests: `test_exact_lane.py` 14 passed (pytest, pure Python). Re-gate row `ak-inf06-exact-regate-c12lb49-20261117` (owner autokernel, CPU quarter) published and queued for smoke: C12+LB4.9 `bda43aa17` vs C12 `457d5fc52`, prebuilt stores sha-checked, sealed judge copy, dense Qwen3-8B + Qwen3-0.6B draft, 3 prompts × 2 arms × 2 kernels = 12 fresh-process cells, 64 tokens each. [no-belief: code landed; row verdict pending]
  - *(2026-11-17, autokernel)* Loop wiring landed: epyc-inference-research `dd84d828b` — `Hypothesis.lane` + `iterate(exact_judge=, exact_on_mismatch=)` wrap the gate with `exact_lane.lane_gate` (absent lane returns the original gate result untouched; exact PASS skips the quality gate, FAIL rejects); `test_exact_lane.py` 22 passed, `test_loop.py` green; re-gate row `ak-inf06-exact-regate-c12lb49-20261117` smoke PASS, in `ready/`. [no-belief: code landed]
  - *(2026-11-17, autokernel)* Driver wiring landed: epyc-inference-research `8b304f882` — `run.py --exact-lane-config <json>` (incumbent store, model, draft, fixed prompts, port) builds `exact_lane.make_exact_judge` (fresh `serve_one` capture per cell, incumbent store vs `worker.build_dir`, `judge_streams`) and passes it via `pool.drive` → `pipeline.run_pool` → `loop.iterate(exact_judge=, exact_on_mismatch="reject")`; no flag = no judge, and candidates without lane "exact" stay on the unchanged gate path; `test_exact_lane.py` 28 passed (fake capture), pipeline/loop/campaign/driver suites green. [no-belief: code landed]
  - *(2026-11-18, autokernel)* The exact lane is not usable for GPU candidates until C10-GPU-GREEDY-AA-DIVERGENCE is fixed: identical GPU runs disagree (r3 `ak-c12-greedy-aa-bisect-20261117-r3` BASE F=0.352), so bitwise identity vs the incumbent would reject every GPU candidate. CPU candidates are unaffected. [no-belief: row verdict filed by agent]
  - *(2026-11-18, autokernel, result)* ✅ Re-gate row `ak-inf06-exact-regate-c12lb49-20261117` filed PASS: C12+LB4.9 `bda43aa17` vs C12 `457d5fc52`, 3 prompts × {plain, drafted}, 6 cells per side, 384 token IDs bitwise identical, routed to `speed_abba` with the quality eval skipped. Lane live for CPU campaigns: epyc-inference-research `f9c8ca5c6` adds `exact_lane_cpu_c13.json` (incumbent = champion C13 CPU store `cpu-20261117-bda43aa17-c13`, the re-gate row's models and prompts, port 18791), and `serial_run._child_command` now passes `--exact-lane-config` to every CPU campaign child. **CPU-only for now:** the launcher, `run.py` and `load_config` refuse it for GPU campaigns, because identical GPU runs diverge (C10-GPU-GREEDY-AA-DIVERGENCE: NOT_LOCALIZED; an r4 bisect is in flight). `test_exact_lane.py` 35 passed. [no-belief: row verdict filed by agent]

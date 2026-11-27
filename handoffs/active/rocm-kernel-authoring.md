# ROCm Verify/Profile/Benchmark Backend for MI210 Kernel Authoring

**Model**: gpt-6.1-terra
**Effort**: high

> **Fold destination** (BRF-T7-F13, BRF-T7-1, route 1b, 2026-11-03): renamed from `rocm-verify-profile-backend.md`; every former handoff of this plan target is a `## Track:` with its own gate marker: `rocm-verify-profile-backend`, `agentic-rocm-kernel-authoring`, `gemma-challenge-kernel-techniques-v7` (rows INF-03, INF-16 retired into INF-48). The former `rocm-verify-profile-backend.md` body is `## Track: rocm-verify-profile-backend`; tracks those handoffs already had are lifted verbatim after their owner.

**Status**: ACTIVE — triaged 2026-11-09 (inf48-triage): 76 open boxes -> 8 live items (INF48-LIVE-1..7 + the ATT/AITER/LSA boxes; see table)
**Row**: INF-48
**Domain**: inference-research
**Created**: 2026-06-03 · **Updated**: 2026-11-09 (INF-48 triage; evaluator carriers landed on research branch)
**Priority**: MEDIUM (the substrate for [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring))

> **NEXT ACTION (2026-11-09): PARKED under the recorded gate "GPU AutoKernel lane restart" (operator 2026-11-09, below); nothing in INF-48 is dispatchable until it lifts.**
> *Pre-park next action, kept for the restart:* port the C6 controller wiring (INF48-LIVE-1) onto research main, then schedule the two GPU rows.
> The 2026-08-22 "rejected carriers" state is stale: the repairs were made on `codex/autokernel-v27-descendant-20260823`
> (audit fixes `27602b14d`, falsified-C6 typed disposition `32d48f3da`) and the evaluator-layer subset is now landed on research
> branch `inf48-triage-20261109` (`f69569bc4`, `1525888cc`, `02b35fda0`), merged to research main through `64a287b83`; the controller half
> has 18 conflicting files (INF48-LIVE-1). Schedule `RVP-ATT-CANARY-R4` and `ROCK-AITER-GFX90A` step 2 as rowflow rows (blockers recorded
> under each box). RVP-C4-10 stays closed (PC sampling unimplemented on this ROCm).

> **RECORDED GATE: "GPU AutoKernel lane restart"** (operator 2026-11-09, decision tool: "Park under GPU-lane gate"). Waiting on it, boxes stay UNTICKED:
> INF48-LIVE-1 RVP-C6-WIRE, INF48-LIVE-2 RVP-C2-PRODUCER, INF48-LIVE-3 RVP-C4-5..9,11, INF48-LIVE-6 GPU-AK-SIGNALS. The gate lifts when the operator restarts the GPU AutoKernel lane.
> Where the C6 work stands for the restart: the C6 evaluator layer is on research main (`64a287b83`); the controller half still lives only on `codex/autokernel-v27-descendant-20260823` (18 conflicting files, see INF48-LIVE-1).
> `RVP-ATT-CANARY-R4` also sits under this gate, but its row `codex-att-r4-20261109` was queued on operator instruction on 2026-11-09, so it is NOT withdrawn; the row runs as queued. *(2026-11-11, autokernel)* r4..r4d were never published; `codex-att-r4e-20261109` ran and is filed PASS.
> Re-homed out of this file on 2026-11-09: LSA-PORT-1 -> `long-context-program.md` (D-LSA section). ROCK-AITER-GFX90A found no live MI210-serving destination (see the box) and stays here. INF48-LIVE-7 already sits in its kernel handoff (INF-03/INF-37 were folded into INF-48; there is no other kernel handoff).

| Live item | What | State |
|---|---|---|
| INF48-LIVE-1 RVP-C6-WIRE | controller half of the C6 oracle/Ghost wiring | controller port landed (2763f5910); C6-26 remainder + RVP-C6-19/21 + live proof open |
| INF48-LIVE-2 RVP-C2-PRODUCER | 16 producer-dependent C2/C3/C5 boxes | PARKED (OP-11) |
| INF48-LIVE-3 RVP-C4-5..9,11 | rocprof v1 profile(), taxonomy, telemetry | done 2026-11-16 |
| RVP-ATT-CANARY-R4 | GPU trace-launcher canary | row rvp-att-canary-r4f-20261116 published 2026-11-16 (partial+full path) |
| ROCK-AITER-GFX90A | step 2 timing vs C6 | step 2 filed 2026-11-09 PORT_CANDIDATES; AITER-PORT-1 tile step TILE_CONFIRMED; C10 prefill A/B KEEP 1.127x; quality row pending |
| INF48-LIVE-6 GPU-AK-SIGNALS | counter/ISA/race/equivalence | open |
| INF48-LIVE-7 INF03/INF37 | MMQ audit, AGPR, MoE Q8 fusion | partly operator-parked |
| LSA-PORT-1 | experimental sparse-attention port | open |

Triage counts (76 boxes): LIVE 41 (folded into the 8 items) · DONE 5 (RVP-C6-14/16/17/18/22) · SUPERSEDED 18 · DROP-CANDIDATE 0 · resolved by operator 2026-11-09: 7 DROPPED (GEAK-eval, RVP-C5-4, RVP-C5-5, Item A, K10, K30, B2), 5 RE-HOMED (K27 to quantization-and-low-bit.md iqk track; K31, W1 to the DSA track here; W2, W3 restored in the publication track here). Original box text: `git show b3bd883d3:handoffs/active/rocm-kernel-authoring.md`.

> **Historical next action (2026-08-12): implement the exact k228 and k175 model-tensor hook manifests, then run
> their governed real EPYC C3/C5 captures and matched whole-model exits.** OP-11 was
> resolved as Option B (decline for now), so C2-7/C2-8/C2-9 remain deliberately open unless the
> operator explicitly reopens the experimental producer. The research reducers/runners remain
> durable; the old oracle-integrity smoke remains non-evidence.
>
> **Evidence-authority boundary (2026-08-12):** RVP-T0-1 and its v9 replication are durable
> hardware-saturation diagnostics, and AK-BH-1/2/3 plus AK-LN-2/AK-X-5a are durable bounded
> diagnostic receipts. Their retained hashes and commands support those local findings, but the set
> does not uniformly bind a committed clean source checkout and complete build manifest. Do not use
> it as current AutoKernel calibration authority. Establish clean hardened-instrument provenance
> first, then run frozen-v9 controls, the full-host CPU IQK campaign, and the matched archive/evaluation.
>
> **Correction carried with it (operator, 2026-08-10):** the phrase *"All runs operator-approved
> (P-GPU-1)"* below is **wrong as a blanket statement**. P-GPU-1 governs the **class of claim** a GPU
> result may carry, not permission to run; the human boundary is **freeze / cutover / promotion**.
> What remains true and unchanged: profiling or benching a **live server** is owned by whoever owns
> that inference, and co-residency is theirs to schedule.

## Track: rocm-verify-profile-backend
<!-- gate: EVL-47 -->

### Backlog

- [ ] **INF48-LIVE-1 RVP-C6-WIRE - integrate the audited C6 oracle/Ghost wiring into the research-main discovery controller.** The carrier/evaluator layer landed in research branch inf48-triage-20261109 commit f69569bc4 (Hawkeye measurement, two-process Ghost Replay, sandbox, reward integrity; 153 pytest tests green across c6_mutants, c6_reward_integrity, hawkeye, sandbox). ✅ 2026-11-16 controller half on research main: 0540c6d14, e194dbf4d/737ca4061/bf94b0965/ab91897a5, 2763f5910 (last missing branch test ported: recursive sidecar-tamper refusal); test_c6_admission_integration 14/14; controller suite 1398 pass 0 fail after bc52f6d0c. [no-belief: software port] Children below are folded RVP-C6-19/21/24/26 remainders. C6-26: the twin-gap screen now also reports a materially FASTER synchronized twin, but only as a non-fatal WARNING (1525888cc, 02b35fda0): the ordinary twin runs first on a fresh cold context, so a hard FAIL could be a false positive; promote to FAIL only after its false-positive rate is measured; remaining is the planted C-style content-hash-memo kernel in `reward_hack_corpus` (changes the 9/9 corpus identity, needs its own re-pin) and, optionally, rank-first-execution in the experimental llama-bench. C6-24 done: test_wrapper_raise_mutation_separates_laundering_from_honest_kernel (research e194dbf4d) (three-run bitwise determinism part is done in c6_reward_integrity.py). [no-belief: new consolidated box] *(2026-11-11, autokernel)* Controller port DONE: bf94b0965 and ab91897a5 are ancestors of research origin/main 520395b72; admission + oracle/candidate split live in discovery_controller/deployment_factory/gpu_source_evidence; test_c6_admission_integration 13 passed. Remaining open under this box: only the folded RVP-C6-19/21/24/26 items. 2026-11-17: Codex login restored; row c6-admission-live-proof-r5 published (smoke queued) [no-belief: status note] 2026-11-19 (autokernel): the controller half is already on research main (ancestors above); what was added for the proof is the typed native-C6 refusal (`C6SplitPolicyRefusal`, research `123423abb` on branch `ak-c6-typed-refusal-20261119`, not yet on main; behaviour-neutral, only names the refusing legs) and the r9 proof-instrument pin (branch `ak-c6-r9-proof-pin-20261119`, NOT for main). No new opt-in was needed: C6 admission stays behind the sealed bundle's `--c6-admission` flag, default off. Box stays OPEN on the proof row `c6-admission-live-proof-r9`, C6-26 remainder and RVP-C6-19/21. [no-belief: status note]
  · 2026-11-21 OPERATOR DECISION (AskUserQuestion, this session): production C6 semantic judge = Claude in-context, the same pattern as the Claude-as-Judge suites. Operator chose this option, whose text stated that it "also ratifies gating on its verdict", so the C6-19 semantic tier is ratified as GATING with an in-context Claude judge, conditional on the C6-20 mutant calibration (3/3 reject + 3/3 honest accept, `87c49f249`). C6-21 differential audit: score the generation corpus with that judge. [no-belief: operator decision]
  · 2026-11-21 C6 remainders. C6-19: the Appendix-H rubric (arXiv:2510.17891v2, intake-1241#record) now exists as data: research `27072cf51` (`tritonrl_appendix_h_rubric.json`, `semantic_judge.py`, 9 tests). A blind in-context Claude calibration rejected 3/3 mutants and accepted 3/3 honest controls (`87c49f249`; non-gating, gating needs operator ratification). Open: choose the production judge (in-context Claude vs a local model) and ratify gating. [no-belief: software + non-measurement calibration]
  · 2026-11-21 C6-21: `differential_audit` helper landed (`87c49f249`, 3 tests). Open: score a generation corpus with the chosen judge. [no-belief: software]
  · 2026-11-21 C6-26: (b) is DONE and the earlier "remaining" text was stale: the planted C-style content-hash memo is already in `reward_hack_corpus` (`fb437d534`, 26 cases, r3 26/26 on 2026-11-10). (a) Promoting twin-gap to FAIL cannot be priced offline: there are 0 populated GPU twin records, and the CPU proxy shows 0/679 above 20% (max 5.3%). It needs an honest-kernel GPU hardened-bench row. [no-belief: status note]
  - [x] **INF48-C6-RESEAL-C9** Reseal the C6 instrument to C9 and create one real bundle (operator 2026-11-09; agent running in `worktrees/c6-reseal-c9-20261109`). Site model stays 1.5B, a deliberate screening model. [belief: cc] ✅ 2026-11-11 (autokernel) superseded by research a87018724 (+ tmp_gate b94792bb2), both on origin/main; C6 instrument then re-pinned to C10 (C6-C10-REPIN). [no-belief: superseded]
  - [x] **INF48-C6-LIVE-PROOF** Controller code landed (research bf94b0965, ab91897a5) but C6 admission has never run on hardware. r2 smokes failed 21:10Z: c6-native-residency-r2 on the residency check (see PIPE-EVE-RESIDENCY-FALSE-FAIL), c6-26-corpus-repin-r2 job rc=1. Republish and run. [no-belief: tooling-repair] ✅ 2026-11-11 (autokernel) C6 admission ran on hardware: c6-native-residency r3 PASS (backend-matched 1.0, NMSE 1.2e-4) and c6-26-corpus-repin r3 26/26, sens/spec 1.0 (notes below). [belief: cc]
    - 2026-11-16: blocked on the run environment, not code. C6 --validate-only fails on (a) sealed rocprofv3 interpreter /usr/bin/python3.13 missing from the image (only uv cpython 3.13.17 present, different sha), (b) claude.exe has 2 hard links so the critic actor refuses it. Row c6-admission-live-proof-r1 drafted; publishes once validate-only passes. [no-belief: environment diagnosis]
  - [ ] **INF48-C6-CONTROLLER-PROOF** [inference] ONE discovery-controller iteration with C6 admission on the MI210 (model: none; op-level q4_K MUL_MAT on production v10 GPU store; bundle /mnt/raid0/llm/tmp/c6-live-proof-validate-20261116-r2, research 043120e83, validate-only PASS 2026-11-16 graph_sha256 002ca627…). The native legs are proven (box above); the controller-level admission iteration is not. est 3600 s. stop-on-answer: both admission legs reopen sealed native C6 PASS receipts and the iteration writes or refuses with a typed disposition; stop-on-futility: any untyped/fail-closed error or validation failure, no retries. Row c6-admission-live-proof-r1. [no-belief: new box] 2026-11-17: Codex login restored; row c6-admission-live-proof-r5 published (smoke queued) [no-belief: status note] 2026-11-19 r12 (autokernel): first candidate (q5_0 MUL_MAT m32 n1 k256) reached the native C6 oracle and got typed `C6SplitPolicyRefusal(precision_equivalence)`, but the exception killed the controller (supervisor_dead, screen_ambiguous) and no C6 receipt was sealed, so the box is NOT met (auto-filer recorded row verdict 'pass' with rationale DROP(diagnostic); that label overstates it). Two defects fixed in research 33041e70a (origin/main): (a) the refusal is now sealed (correctness/c6-refusal.json) and mapped to `C6SplitPolicyCorrectnessRefusal` (a CorrectnessRefusal), so the loop records that candidate as correctness_falsified and continues; (b) the refusal was an oracle mis-specification: legs bitwise equal, NMSE 3.6e-5 (passes 5e-4) but normalized RMS 6.0e-3 vs an f32-epsilon bound 1.9e-6 against an unquantized-activation f64 reference, which every MMVQ kernel incl. production fails; quantized MUL_MAT now uses q8_block epsilon (bound 0.125 at D=256). Controller suite 1364 pass. Row c6-admission-live-proof-r13 published (bundle c6-live-proof-validate-20261119-r13, validate-only PASS graph a1c0ed6a…; smoke queued). [no-belief: status note]
      · done when: a c6-admission-live-proof row files PASS with both admission legs reopening sealed native C6 PASS receipts and the iteration writing or refusing with a typed disposition
      · 2026-11-22 (autokernel): r14 INCONCLUSIVE (harness false stop: rowflow idle-after-crash check killed it because gpu-q3 was stored as shape gpu; not a C6 result); rowflow fix epyc-root c514779d1; r15 published. Filing ledger already records r14 SUPERSEDED-BY r15 (filing.supersede, rc=75). [no-belief: status note]
    · 2026-11-21: r13 FUTILITY_CARRIER root-caused to `gpu_source_evidence.py` `_validate_c6_split_receipt_body`: empty oracle stdout was refused on sealed-receipt reopen (stdout is empty by design; the oracle writes its sidecar). Fixed in research `5d16a37ad` with a test. Row `c6-admission-live-proof-r14` (code pin 5d16a37ad, bundle c6-live-proof-validate-20261121-r14) published, smoke PASS. [no-belief: tooling-repair]
    - 2026-11-19 `c6-admission-live-proof-r13`: **inconclusive (FUTILITY_CARRIER)**. Trace and validation passed; the controller reached the C6 oracle but died on untyped `EvidenceProducerError: C6 oracle stdout must not be empty`. No admission records or sealed refusals; rc=0 is the launcher result, not proof success. Result `/mnt/raid0/llm/tmp/c6-admission-live-proof-r13/out/results.jsonl`, SHA-256 `ce10993b518a1c4104d3e87ea448d759adbcb6399294b05086d359693230ee94`. The proof box stays open; investigate the empty-stdout receipt validation before a new attempt. [belief: cc]
    - 2026-11-17 c6-admission-live-proof-r6: inconclusive, box stays OPEN — the C6 controller now runs end to end and the iteration returned, but it produced no candidate, so C6 admission itself was never exercised. [no-belief: row verdict filed by agent]
    - 2026-11-18 c6-admission-live-proof-r7: inconclusive (FUTILITY_CARRIER; untyped StaticRegistryError in the carrier iteration, code fa3faaba7), box stays OPEN. The carrier/registry needs a fix before r8. [no-belief: row verdict filed by agent]
    - 2026-11-18 `c6-admission-live-proof-r8` is published (rank 40) with the carrier fix (research `92ce851f4`); r7 stays the last verdict. Box stays OPEN until a candidate reaches C6 admission. [no-belief: row published]
    - 2026-11-18 `c6-admission-live-proof-r8`: **inconclusive (FUTILITY_CARRIER, EvidenceProducerError)**. The supervisor fix `92ce851f4` worked: a real iteration built a candidate and reached the native C6 oracle (`gpu_source_evidence.py:2434`), which refused it with an untyped error, most likely GPU run-to-run nondeterminism. Box stays OPEN: needs a typed refusal. [no-belief: row verdict filed by agent]
    - 2026-11-19 (autokernel) `c6-admission-live-proof-r9` published (rank 40, gpu-q3 under `numactl --membind=3 -- taskset -c 184-191`, `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0`; smoke queued). Two fixes behind it: (1) the native C6 split-policy refusal is now typed `C6SplitPolicyRefusal` carrying `failed_legs` (research `123423abb`, branch `ak-c6-typed-refusal-20261119`, 3 tests, test_gpu_source_evidence + test_c6_admission_integration 61 pass); (2) the champion branch `ak/champion/llama-cpp-ffc1bac82eec` advanced C10 -> C14 `eee3da838`, so `_verify_instrument` rejected every C10 bundle (the r8 bundle too), and r9 binds a ref `ak/c6-proof-instrument-c10-20261119` frozen at C10 `7f1bd044b` (research branch `ak-c6-r9-proof-pin-20261119` @ `c8ea1032d`, NOT for main; fresh bundle `c6-live-proof-validate-20261119-r9`, validate-only PASS graph `859edec9...`). One supervised iteration, `autonomous_discovery=false`, stopped by the job after the first admission record or typed stop; it is the controller proof, not the AK loop. The controller instrument re-pin to the current champion is DONE (coordinator: it executes the operator's 2026-11-10 ruling, not a new decision; the constants are not on the human-only list): research origin/main `aa7085891` (C14 `eee3da838`: commit, 283-path delta, test-backend-ops blob, fattn.cu/fattn-common.cuh/fattn-tile.cuh pins, FLASH_ATTN_EXT accumulator fragment for C14's zero-guarded `fattn_div_rowsum`; 52 + 72 tests pass; typed refusal `8e38cece1` rides along). Row `c6-admission-live-proof-r10` (rank 40, bundle `c6-live-proof-validate-20261119-r10`, validate-only PASS graph `be489822...`) published (smoke queued) and binds C14; r9 stays queued and proves the wiring on C10. Not re-pinned: the C10 MUL_MAT correctness baseline (1202 cases) and decode dispatch trace; only the live C14 run can say whether they hold. [no-belief: row published]
    - 2026-11-19 `c6-admission-live-proof-r9`: **inconclusive (FUTILITY_CARRIER, CodexContainerError "interrupted at checkpoint")**. Smoke, trace, validate and supervised start all passed. The one iteration is a planner (Codex) / critic / authoring cycle that repeats after every refusal: 8 cycles in 69 min (~8.6 min each), none reached C6 (3 authoring refusals for a diff touching `<file-scope>` outside the declared symbols, 6 critic revise on a mis-targeted `quantize_q8_1` patch, then one more file-scope refusal). The deadline-300 stop (est 3600 / min 2700) then SIGTERMed the supervisor mid planner turn and the actor raised an untyped error. Codex credentials/quota were fine (10 planner turns rc 0): not an external blocker. Fix: typed `ActorDeadline` (research `4d2eadbba` on main, `f6ed032c6` on `ak-c6-r9c-actor-deadline-20261119`), 3 h window. `c6-admission-live-proof-r9c` published (est 10800, min window 7200, fresh bundle `c6-live-proof-validate-20261119-r9c` graph cbcc00a5). Box stays OPEN until a candidate reaches C6 admission. [no-belief: row verdict filed by agent]
    - 2026-11-19 (autokernel) C14 reprofile `ak-c14-c6-dispatch-reprofile-20261119-r2` filed **PASS** (r1 was a harness futility: job.py looked up SHA256SUMS keys as `bin/<f>` but the C14 store lists `./bin/<f>`; r2 accepts both and reports FUTILITY_IDENTITY_PARSE when no file is found). C14 has zero new ROCm0 backend-ops fails vs production v10 on MUL_MAT/FLASH_ATTN_EXT/ROPE/RMS_NORM/SET_ROWS; MUL_MAT 1202/1202 with an EMPTY fail multiset (C10 baseline had one q4_K FP64-ratio fail; v10 has 66), FLASH_ATTN_EXT 3339, ROPE 428, RMS_NORM 21, SET_ROWS 159. All 17 decode tg128 anchor tuples, the 60,054 trace rows and the agent CSV are identical to C10; only the trace sha changed (`a93823a0…`). Re-pin on research main `e417749ab` (C14 trace pin, FLASH_ATTN_EXT cases 3094->3339, `C14_MUL_MAT_CORRECTNESS_BASELINE` with `C10_…` alias; controller suite green). `c6-admission-live-proof-r11` published (rank 40, gpu-q3, est 10800 s / min window 7200 s, supersedes r9c): code pin `e417749ab` (full sha in job.py), fresh bundle `c6-live-proof-validate-20261119-r11` (validate-only PASS graph `e080f7cc…`), inputs check the C14 worktree and champion branch both resolve to `eee3da838`. Box stays OPEN until a candidate reaches C6 admission. [no-belief: row verdict filed by agent]
    - 2026-11-19 `c6-admission-live-proof-r11`: **inconclusive (FUTILITY_CARRIER, but a harness mislabel)**. The controller completed cleanly (supervisor rc 0, `portfolio_exhausted` then `complete`), but job.py did not count `controller_complete` as a typed outcome. Journal: 13 planner turns, 6 critic refusals, 6 authoring refusals, 1 planner contract refusal, 0 admission records. The critic refusals were correct: the `quantize_q8_1` patches did not touch the sealed `quantize_q8_1_1d` anchors. The planner refusal was correct too: the candidate did not match its portfolio assignment. **All 6 authoring `<file-scope>` refusals were false positives, and so were r9's.** git copies only the first line of a declaration into the hunk header and cuts it at 80 bytes, so the parser never saw the function name (`rms_norm_f32(const float * x,`, `…vec_dot_q5_0_q8_1_imp`). The fix is in research main `7946e2196`. Replaying the 13 r11 patches gave 6 refusals before the fix and 0 after. `c6-admission-live-proof-r12` is published (rank 40, gpu-q3, est 10800 s / min window 7200 s, supersedes r11). It pins the code at `7946e2196` and uses a fresh bundle `c6-live-proof-validate-20261119-r12` (validate-only PASS graph `17167514…`). job.py now types a clean completion as `PORTFOLIO_EXHAUSTED_NO_ADMISSION`. The smoke is queued for the next GPU gap. [no-belief: row verdict filed by agent]
  - [ ] **INF48-FOLD-PLAN** Archive this handoff once AITER-PORT-1, ROCK-AITER, C6 wiring and the canary land, moving parked items to their program handoffs (operator 2026-11-09). [no-belief: planning] 2026-11-17: 3 of 4 preconditions landed (AITER-PORT-1 ✅, ROCK-AITER-GFX90A ✅, RVP-ATT-CANARY-R4 ✅); C6 wiring (INF48-LIVE-1 / INF48-C6-CONTROLLER-PROOF) remains. Non-pruning moves applied: LIVE-6 open children -> autokernel-akx-program.md, FA kernel bugs -> kernel-champion-and-promotion.md. Archive (file move to completed/, INF-48 index row delete) waits for LIVE-1 and the operator /wrap-up. [no-belief: hygiene] 2026-11-19 re-check (autokernel), evidence for the 3 met preconditions: AITER-PORT-1 `[x]` (l.4037, + AITER-PORT-1-QUALITY `[x]`); ROCK-AITER-GFX90A `[x]` 2026-11-10 (gemmdown KEEP 1.127x at d32768, origin/main 63d62eae3; vLLM half ROCK-AITER-GFX90A-VLLM `[x]` 2026-11-12); RVP-ATT-CANARY-R4 `[x]` (row rvp-att-canary-r4g-20261116 PARTIAL_OK + FULL_OK). Remaining precondition: C6 wiring, open on INF48-C6-CONTROLLER-PROOF (r9 published; r8 inconclusive FUTILITY_CARRIER). Left open. [no-belief: hygiene]
  *(2026-11-09, Pipeline)* Rows: `c6-26-corpus-repin-20261109` and `c6-native-residency-20261109`, pinned to unpushed research branch c6-wire-20261109 (22d82ba1e, 7d40638b5; dual path, off by default). model: none for the corpus repin, production v10 q4_K MUL_MAT for residency; quant_build: harness-level on the MI210, not a kernel candidate. stop-on-answer when one complete pass manifests all 26 corpus cases / three residency legs agree with the oracle; stop-on-futility on a compile failure, a non-manifesting case or a nonzero leg, no retries; gate-class = futility-only. C6-21 needs the judge tier; C6-19 Appendix-H rubric not found.
  - *(folded into INF48-LIVE-1; full text at b3bd883d3:1253)* **RVP-C6-19 — Add a SEMANTIC-COMPLETENESS tier to C6, and DROP the planned L3.**
  - *(2026-11-10, AutoKernel)* c6-native-residency r2 FAIL was the oracle, not the kernel. v10's ROCm q4_K MMVQ output matches an emulation of its Q8_1 float-min-sum arithmetic to 1.6e-6. The atol/rtol 0.01 gate against the CPU Q8_K reference scores 0.625 on that output and 0.69 even on a consistent-sum kernel (NMSE 1.2e-4 and 5e-5, both inside test-backend-ops' 5e-4). r3, under a rule fixed before the run (backend-matched ≥0.95 and NMSE ≤5e-4), PASSED: legs bitwise equal and resident, backend-matched 1.0, NMSE 1.2e-4 (`RESULT.json` c6178a74…). [belief: cc]
  - *(2026-11-10, AutoKernel)* c6-26-corpus-repin r3 answered: 26/26 manifested, sensitivity and specificity 1.0, under the inherited rowflow claim. r2's rc=1 came from two claim-inheritance bugs: it used the `/proc/locks` pid (the exited `flock(1)` child) as the holder, and the ancestor walk stopped at the parent. Fixed in research `a4fe7b157` and `75247c3da` (receipt 3dda28f7…). [belief: cc]
      · roll-up: children carry the work
        · class: non-inference
      · section: C6 — the sufficiency question, answered NEGATIVELY
  - [x] **C6-CTRL-MULMAT-ORACLE** — the controller's MUL_MAT numerics (`evaluate_numerics` against the CPU f32 reference at atol 0.01 / matched 0.95) fail every honest GPU q4_K candidate. For quantized MUL_MAT, gate on NMSE ≤5e-4 against the CPU reference (the test-backend-ops criterion); use `c6_backend_matched_oracle` (`min_sum="quantized"` for C9+) as a diagnostic only; keep matched-ratio for f32/f16 ops. Model: none (op-level). Stop: controller change merged with a test showing an honest q4_K candidate passes and a planted defect fails. [no-belief: new box] ✅ 2026-11-10 research d05f29c3f (NMSE ≤5e-4 PrecisionContract predicate for quantized MUL_MAT; tests test_honest_q4k_gpu_output_passes_on_nmse / test_planted_q4k_defect_is_refused_through_nmse) [no-belief: software change, finite regression controls]
  - [x] **C6-C10-REPIN** — from the results of `c10-c6-dispatch-reprofile` (being republished as -r2 with new-fail-vs-v10-baseline semantics after r1 aborted on 66 known v10 MUL_MAT failures): re-pin `families[*].cases`; re-pin the mmvq/fattn/rope/norm/set_rows anchors; re-pin cuda-quantize-q8-v1 to `^void quantize_q8_1<(true|false)>\(.*\)$` with per-instantiation counts (re-profile, not ineligible). If the v10 control differs from the factory pins, record the drift before re-pinning. Model: none (op-level + tg128 trace). Stop: pins committed from row data. ✅ 2026-11-10 — factory re-pinned to C10 from c10-c6-dispatch-reprofile-20261110-r2 (pass: C10 0 new fails vs v10; MUL_MAT 1201/1202 vs v10 1073/1139). cases MUL_MAT 1202 / FA 3094 / ROPE 428 / RMS 21 / SET_ROWS 159 (old 655 counted 496 unsupported; v10 drift). Anchors from the C10 rocprofv3 trace: decode FA = flash_attn_ext_vec (no tile dispatch, so GQA7 pair+tail ineligible), 8-arg mmvq, quantize_q8_1_1d<false|true> per instantiation, rope wg256, rms_norm_f32<…,false>. Portfolio re-sealed 936ae176; C6 capacity 20→16. Deployment gpu-discovery-c10-anchor-20261110-v1 regenerated, loads (config 12324b65); prior bundle kept as .pre-repin. Research c18811673 (5ca754303). Open: MUL_MAT correctness gate refuses the 1 shared baseline fail (C6-CTRL-MULMAT-ORACLE, in progress). [no-belief: row verdict filed by autokernel]
  - [x] **C6-RESEAL-D664 cleanup** — drop branch `c6-reseal-c9-20261109` (superseded by research `a87018724`; `tmp_gate` ported in `b94792bb2`). Optional: port its header-from-commit materialization if the C10 instrument worktree cannot be kept clean. [no-belief: new box] ✅ 2026-11-11 (autokernel) branch c6-reseal-c9-20261109 (d664dc178) deleted after its clean worktree was removed; content superseded by a87018724/b94792bb2. [no-belief: cleanup]

> Folded from the body of `handoffs/active/rocm-verify-profile-backend.md` (row INF-48), from its first `##` section on, @ `779a81fd46b0` on 2026-11-03 (BRF-T7-F13, route 1b, operator D1/D5). Headings demoted two levels; every box kept its text and ID.


- [x] **RVP-AUD-1 — Audit diagnostic receipt durability versus source/build provenance.** RVP-T0-1,
  AK-BH-1/2/3, and AK-LN-2/AK-X-5a retain their bounded findings; missing clean source/build identity
  is now explicit and blocks their use as AutoKernel campaign authority. ✅ 2026-08-12
**Categories**: hardware_optimization, benchmark_methodology, tool_implementation, inference_serving
**Hardware gate — SATISFIED 2026-07-02**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB) is racked; ROCm 6.2 bind-mounted; llama.cpp HIP build verified on gfx90a (`progress/2026-07/2026-07-02-mi210.md`). This backend is now **ACTIVE** (priority MEDIUM). Runnable first tasks: (1) install/pin `pytorch-triton-rocm` matched to ROCm 6.2 + verify gfx90a matmul (intake-760); (2) stand up `rocprof-compute` gfx90a metric subset (C4); (3) the honest-vendor-baseline candidates that are gfx90a-*reachable* — **BitBLAS/TileLang low-bit GEMM** (intake-497/tilelang-puzzles), **NOT AITER** (gfx942-only, intake-759). GPU claim grade follows P-GPU-1; profiling a live server remains the inference owner's scheduling boundary. [was: "~July 2026; nothing executes until the card racks" — stale]
**Priority**: MEDIUM (the substrate for [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring))
**Parent**: [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring) · **Parent index**: [`inference-research-index.md`](inference-research-index.md)
**Full reasoning + evidence**: [`research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md`](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md) (§5.2/§5.5/§5.6 cover this backend).

---

#### Objective
Provide the **evaluation backend** the agentic kernel-authoring loop calls: given a candidate HIP/Triton kernel + a PyTorch reference, return `(compiles?, correct?, speedup, profiler_metrics, integrity_flags)`. It is factored out from the controller (model + search) so controllers can be A/B'd without touching it. **The substrate is now mostly AMD-native MIT/Apache-2.0 code (GEAK-eval + Apex + AgentKernelArena) demonstrated on gfx90a — so this is an adopt/reproduce/harden task, not a from-scratch build.** The two genuinely net-new pieces are **C4** (gfx90a profiler-metric) and **C6** (anti-reward-hacking).

#### Component table — adopt / build / harden (post-GEAK truth)
| # | Component | Plan | Source | Risk |
|---|-----------|------|--------|------|
| **C1** | Build (hipcc/hipify/torch-ROCm) | **ADOPT** | GEAK-eval 674 / Apex 675 (already build on ROCm/gfx90a); torch-ROCm `load_inline` known-good | LOW |
| **C2** | Correctness oracle | **ADOPT then HARDEN** | adopt GEAK-eval's torch-ROCm oracle; **harden** with robust-kbench 668 (forward+backward, multi/unseen shapes, magnitude/variation, output-buffer poisoning) **+ AgentKernelArena 679 unseen-shape generator** | MED |
| **C3** | Timing / speedup reward | **ADOPT then FIX BASELINE** | adopt GEAK-eval timing + Apex/AgentKernelArena Magpie score; **gate reward on an honest vendor baseline** (rocBLAS/hipBLASLt/AITER/torch-ROCm-compile), not eager (FastKernels 671) | MED |
| **C4** | Profiler-metric feed | **BUILD — deterministic first** | Paired mapping/formal `rocprofv2` traces → deterministic kernel/overlap/fuse/architecture tables; bounded similarity/catalogue judgment only after that. Xe-Forge static gfx90a constraint-KB and CudaForge formal selection remain fallbacks. NVIDIA/NCU subsets do NOT transfer | **MED** — parser/report/counter taxonomy are closed; real paired-trace signal remains empirical |
| **C5** | Benchmark / task suite | **ADOPT (primary) + layer** | GEAK-eval 674 (TritonBench-revised + real ROCm bench, gfx90a-proven) **and** AgentKernelArena 679 (HIP/Triton/Torch2HIP suites); layer our own `fast_p` tiering; seed EPYC ops (attention/MoE-dispatch/dequant). MultiKernelBench 667 = secondary (multi-vendor abstraction only) | MED |
| **C6** | Reward-integrity / anti-hacking | **BUILD — our differentiator** | robust-kbench 668 exploit-class half (Apache-2.0, liftable) **+** AgentKernelArena 679 unseen-shape half **+** a red-team-with-cheating-kernels gate. GEAK/Apex have only loose oracles | MED |

#### Current sequence (replaces the old phase plan)
- **[declined: operator 2026-11-09 (INF-48 triage, dropped, not done): external-license gate on GEAK-eval pins (re-audited 2026-08-11: no project-level license); nothing runnable]** **Reproduce GEAK-eval's published MI250X task/result on the MI210.** — closed as dropped, not completed; original text: `git show b3bd883d3:handoffs/active/rocm-kernel-authoring.md` line 84. [no-belief: dropped by operator 2026-11-09]
- **[declined: operator 2026-08-12 PARKED (OP-11 'decline for now'); not open work, reopen only on an operator decision. Restructure 2026-11-10: checkbox removed so it stops counting; r4 replay FAIL 2026-11-09/10 and offline follow-ups done 2026-11-10, children below keep their ticks]** **INF48-LIVE-2 RVP-C2-PRODUCER (PARKED, operator OP-11 'decline for now', 2026-08-12) - C2 oracle surfaces and C3/C5 capture hooks that need the experimental producer.** Reducers/runners are durable on research main (c5fe6b51, 1a4d7dca, 000a2686, eca5dbda, 14034623); closure needs an operator-approved committed experimental producer plus fresh durable-identity replay. Do not work these until the operator reopens OP-11. NOTE: `test_c3_epyc_tensor_capture` has 12 errors on research main 645ca5b54 (pre-existing, unrelated to this triage); fix before the k228/k175 hooks. [no-belief: new consolidated box]
  - **r4 replay result (2026-11-10, AutoKernel; row `c2-producer-replay-r4-20261109`, raw `/mnt/raid0/llm/tmp/c2-producer-replay-r4-20261109/out`).**
    QUESTION: on the clean committed producer `llama.cpp-experimental-q38fn-20261004` @ `dd6c9cdbd`
    (test-backend-ops sha256 `7a95ab8b…7515`, CPU backend, reducer pinned at research `dec858bea`), do the
    AK_SENS/LAYOUT/STATE receipts satisfy the durable reducers? VERDICT: **FAIL (box stays open).**
    Sensitivity FAIL — 92,936 observations, 54,250 units, **3,894 unscoreable**: CONV_2D 3,696 (528 of 1,570
    cases; inputs change, output does not — degenerate geometry, e.g. 1x1 input with padding 5 / dilation 4, so
    the output is padding-only), CPY 69, LIGHTNING_INDEXER 32, FLASH_ATTN_EXT 24, FILL 28, TOP_K 18, other ≤8.
    70 units are `#unpaired` (11 FLASH_ATTN_EXT/LIGHTNING_INDEXER keys whose receipt is missing on some seeds).
    Layouts: 8,983 rows, **247 `supported=0`** (MUL_MAT 100, SET_ROWS 84, CPY 63), counted as hard failures.
    Stateful: 5,186/5,186 clean. The ordinal reducer fix (research `dec858bea`, merged `f4b850f9e`) was
    already in r4's pin, so it does not change this count and **no r5 is warranted on that basis**. [belief: cc]
    - [x] Classify the structurally output-invariant CONV_2D geometries (output is padding-only) as C5-2 insensitive
      cases instead of unscoreable, with a geometry test proving the exclusion, then re-reduce the r4 CSVs offline
      (no new compute). Re-check the residual CPY/FILL/TOP_K/ARGSORT units afterwards. ✅ 2026-11-10 -
      research `60d2042e0` (merged `a16499b99`): `conv2d_output_is_padding_only` (no in-range tap in either spatial
      dim), units carry `structurally_insensitive`; only flagged when the measured output really was invariant.
      Offline re-reduce of r4 (92,936 obs, 54,250 units): **3,696 CONV_2D units structurally insensitive,
      unscoreable 3,894 -> 198** (CPY 69, LIGHTNING_INDEXER 32, FILL 28, FLASH_ATTN_EXT 24, TOP_K 18, ARGSORT 8,
      SSM_SCAN_ROLLBACK 7, LOG 6, SQRT 6); outcome still FAIL. Residuals: CPY 69 = i32/quantized-src to f32 (23
      src types x 3) - the producer's value-source collector takes only F32/F16/BF16 leaf tensors, so the
      transform only perturbs the overwritten dst, a producer coverage gap; FILL 28 = output is the constant `c` by
      op semantics (input overwritten; insensitive by construction, not yet classified); TOP_K 18 / ARGSORT 8 =
      degenerate tiny shapes (ne=1 or 3) whose seed-derived inputs collide across seeds. Note: with kernel 1x1 the
      example "padding 5, dilation 4" alone is NOT padding-only; the r4 cases are (stride1=5,padding1=2). [belief: cc]
    - [x] Decide whether the 247 layout `supported=0` rows (MUL_MAT/SET_ROWS/CPY) are legitimate CPU-backend
      non-support, which the layout reducer should exclude, or a gap in the producer. Make the reducer count
      unsupported separately from hard failures. ✅ 2026-11-10 - **legitimate CPU non-support, not a producer
      gap**: `ggml-cpu.cpp` `supports_op` declines CPY/SET_ROWS to IQ1/IQ2/IQ3 dst (no `from_float`; 63+84 rows) and
      MUL_MAT whose src1 is f16 unless src0 is f16 (src0 vec_dot_type != f16; 100 rows). The producer emits
      supported=0 + hard_failure=1 by design for any probe pass. Research `60d2042e0`: `BackendOpsCase.supported`,
      `BackendOpsRun.unsupported_hard_failures_by_op()` (247) vs `hard_failures_by_op()` (0 ran-and-failed);
      fail-closed `status` deliberately unchanged (existing test), so excluding them from a gate is a consumer
      decision for a CPU-only run, not for GPU candidates where non-support would hide a missing kernel. [belief: cc]
    - [x] Producer: find why FLASH_ATTN_EXT hsk=320 and LIGHTNING_INDEXER cases emit no AK_SENS receipt on some
      seeds (sens phases rc=1). This is the source of the 70 unpaired units. ✅ 2026-11-10 - cause found, fix NOT
      applied: the f16 KQ mask from `init_tensor_kq_mask` contains `-INFINITY` blocks (when
      `0.2*N/8192 >= 1`, i.e. these larger FA/LI shapes); `autokernel_write_scaled_float` rejects non-finite results
      ("value transform produced a non-finite F16 input"), so the identity pass fails (`value_receipt completed=0`,
      error `compare failed`, supported=1, hard_failure=0) and the receipt gate
      (`transforms_completed == 4`) emits nothing. r4: LI 52/50/52 and FA 1/2/3 rows per seed 4711/6841/8117; mask
      occurrence is seed-dependent, hence unpaired. (REGLU f16, 6 rows, is separate: fails at transform 3.) A correct
      fix needs a producer decision (preserve -inf mask sentinels under scale; negate must not flip -inf to +inf)
      plus rebuild and replay, so it was not made here; stdout `VALUE TRANSFORM FAIL` text was not retained in the
      CSV, so this is source-derived, not log-confirmed. [belief: cc]
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:92)* **Harden the remaining producer-dependent C2 oracle surfaces.**
  - [x] **Bind the three reducer outputs into verdict-bearing source-candidate T0 authority.** ✅
    2026-08-12 — research `d8013a6c` requires measured, hash-bound sensitivity,
    hostile-distribution, and checker-isolation evidence tied to the exact candidate source,
    evaluator bundle, suite version, producer, and evidence object. Missing or dry-run evidence and
    source/evaluator drift yield `COULD_NOT_CHECK`; parameter candidates cannot smuggle these source
    prerequisites. This completes the consumer authority, not OP-11's producer identity or replay.
- [x] **HIP arm minimum loop closure (after the Triton loop works).** ✅ 2026-08-12 — research
  `2c214d48` `controller/hip_authoring_arm.py` admits only a true Torch2HIP task from clean Apache-2.0
  AgentKernelArena `2dbbf1d3`, hashes the task/candidate/toolchain, compiles GPU-blind for gfx90a,
  and uses separate released MI210 claim/sampler windows for the vendor baseline and centralized
  final evaluation. The r4 SiLU receipt compiled and passed 11/11 public correctness and 11/11
  timing-validity cases; root independently re-derives its two producer-authored belief rows. The
  Torch-eager ratio is observation-only and non-rankable; no production or experimental llama tree
  was touched.

#### Interface contract (the seam controllers depend on)
```
evaluate(candidate_source, torch_reference_module, inputs) -> {
    compiled: bool,
    correct:  bool,              # hardened C2 verdict (incl. unseen-shape check)
    speedup:  float,             # C3 reward vs the HONEST vendor baseline
    metrics:  dict[str, float],  # C4 gfx90a profiler signal (for a profiler-fed judge)
    diagnostics: str,            # compiler/runtime errors -> Correction-mode feedback
    integrity_flags: list[str],  # C6 exploit detections (empty = clean)
}
```
Mirrors GEAK-eval's evaluator, Apex's Magpie scorer, and CUDA Agent's `verification.py`/`profiling.py`/`compile.sh` (intake-660) — all validate this factoring. Resist widening the seam; a new controller's needs should be derivable from these fields.

#### gfx90a caveat + audit
Same `gfx90a` predicts **compile compatibility, not performance equivalence** — reproduce every AMD number on the MI210 before trusting it (GEAK-v1 carries the only gfx90a *evaluation*; GEAK-v2/HIP/AgentKernelArena publish gfx942 numbers only — but GEAK **v4** retains first-class gfx90a *knowledge*, amended 2026-08-03 in [`agentic-rocm-kernel-authoring.md`](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring)). **Run the GEAK-family freshness sweep (deep dive §9) at each audit.** All intake-674–679 AMD numbers are vendor-reported until reproduced on our own gfx90a (`feedback_classify_eval_failures_by_reason`, observe-before-diagnosing).

#### Historical C4 tooling block — resolved 2026-08-03 (research-intake Stage-2b)

The C4 row above is scored HIGH risk for "CDNA2 counter taxonomy unproven". That is only half of it:
**the profilers themselves are absent.** `rocprofv2`, `rocprof` and `omniperf` were all missing as of
2026-07-20 ([`mi210-big-model-and-acceleration-roadmap.md:205`](../completed/mi210-serving-program.md#track-mi210-big-model-and-acceleration-roadmap));
`rocprof` v1's SQ/TA counters read zero on this box and it aborts at init on graph-enabled builds;
`rocm-bandwidth-test` is not installed; and QuixiCore's timing recipe — otherwise worth copying — assumes
`rocprofv3`, also absent.

**This is a regression, not a contradiction.** Two other files record successful `rocprofv2` runs on
2026-07-04, sixteen days earlier, so something changed on the host between those dates. Recording it as a
chronology rather than as an inconsistency is the point: the earlier runs are still valid evidence, and
the fix is a host action (reinstall/re-pin), not a re-litigation of which file is right.

##### CLOSED 2026-08-03 — tooling side-loaded, and the CDNA2 counter taxonomy is PROVEN


**The container fix keeps getting reverted, and it does not matter.** `.devcontainer/Dockerfile` gained a
`libpciaccess0` line (root `e0cbad4a`); a host-side sync rewrote the whole `.devcontainer/` directory twice
on 2026-08-03 and dropped it both times, leaving a stale `Dockerfile.orig` beside it. That sync is outside
the container and cannot be reached from a session here. **Nothing depends on the line**: the provisioner
side-loads `libpciaccess0` itself when the container lacks it, which is the path actually in use today. Do
not re-litigate this — restore the line if convenient, and rely on the provisioner regardless.

**Reproducible from git, not just present on the filesystem** — `epyc-inference-research`
`scripts/benchmark/provision_rocm_profilers.sh` (idempotent, `--verify` mode, refuses if the installed
ROCm is not 6.2.x). The 19 MB of extracted binaries are deliberately not tracked; the recipe is. `env.sh`
is the tracked canonical copy at `scripts/benchmark/rocm_profilers_env.sh` and the tools-directory path is
a symlink to it, so there is one copy and it cannot drift. Counter enumeration committed at
`data/gfx90a-counters/`. Research `7926557b`.

**Installed by EXTRACTION, not by `apt install`, and the distinction is deliberate.** `/opt/rocm` is a
bind mount of the host's `/opt/rocm-6.2.0`, shared by four live GPU servers and three FROZEN kernel trees
running three different ggml generations. An apt install would write into that shared tree and could pull
dependency upgrades of ROCm runtime libraries underneath a production server — the exact silent-breakage
mode the `LD_LIBRARY_PATH` discipline exists to prevent. The packages were `dpkg -x`-extracted to
`/mnt/raid0/llm/tools/rocm-profilers-6.2` (19 MB); **nothing outside that directory was modified** and
reversal is `rm -rf`.

Two incidental findings worth keeping: `libpciaccess.so.0` was **absent from this container entirely**
(our own handoff had recorded "add `/usr/lib/x86_64-linux-gnu` to `LD_LIBRARY_PATH`" as the fix — but the
library was not there to find), and `rocprofv2` derives its ROCm root from its own `argv[0]` rather than
from `$ROCM_PATH`, so the prefix needs a mirrored `.info/version`. Both are handled in `env.sh`.

- [x] **RVP-C4-1 — Add and exercise a governed whole-model `rocprof` v1 attribution fallback.**
  ✅ 2026-08-11 — `run_autokernel_rocprofv1_attribution.py` binds clean source/binary/model/profiler
  and linkage identities, holds the MI210 claim, samples the device at 250 ms, and captures
  p2048/p8192/p32768 with graphs disabled. GDN summed-kernel shares were **15.397%, 14.649%, and
  12.180%**; optimistic 4x-op full-model ceilings were **11.548%, 10.987%, and 9.135%**. This
  reproduces the earlier ceiling instead of raising it. Receipt:
  `/mnt/raid0/llm/autokernel/probes/k28-rocprofv1-attribution-20260811-r3/receipt.json`, SHA-256
  `981306080a674f89f5ac7f9c7631feef1d31071dacd46329aa983db72e74c5a0`; research integration
  commit `48350b24`.
- [x] **RVP-C4-3 — Replace the Q4_K Omniperf multi-pass merge with a governed single-pass PMC
  transport.** ✅ 2026-08-11 — Omniperf/rocprof-v1 permuted rows across passes and blocks, so its
  apparent block-1 comparisons were withdrawn. The replacement validates the installed gfx90a
  counter catalogue, collects `SQ_WAVES`, `SQ_INSTS_VALU`, and `SQ_INSTS_VALU_INT32` in one
  rocprofv2 file-plugin pass, requires exact within/across-block invariance, and emits no normalized
  comparison on missing/zero/drifting counters. A predeclared two-attempt ceiling retries only
  transport exit/missing-artifact failures and preserves every attempt. The four-block
  representative-shape r7 matrix passed 12/12 cells and found Q4_K minus same-bit Q4_0 at
  **+112.5 VALU and +35 INT32 instructions/wave** with equal waves. Receipt SHA-256
  `1e34339c1c986413c4eeb1b56ba3202c8763d08df45aba1c0580917c888f5e47`; research
  `70374c43` / main `ac88d75a`. The result is differential-mechanism evidence only; fused unpack
  wall share remains structurally unidentifiable.
  The retained exit-139 attempts are localized to target-process finalization after complete
  correctness rows and CSV flush: an intermittent legacy ROCProfilerV2 preload-stack teardown crash
  in the side-loaded ROCm 6.2 profiler on the unsupported Ubuntu 25.10 / kernel 6.14 host mix. It is
  not a kernel-execution or counter-collection failure. Keep the fail-closed bounded retry; do not
  mask rc139 or accept its otherwise-complete CSV. If this becomes recurring infrastructure, first
  reproduce with core capture in a ROCm-6.2-supported 22.04/24.04 environment, then validate a
  rocprofiler-SDK/rocprofv3 migration on an isolated current stack.
  A later Q4_K candidate diagnostic narrowed one tempting false explanation: two runs with 32/34-byte
  workload identifiers both exhausted their two attempts, but a 13-byte identifier still produced one
  exit 139 followed by a passing retry. Identifier length is therefore not established as causal.
  The existing bounded fail-closed retry remains the correct integration contract; never accept a
  complete-looking CSV from a nonzero profiler exit. Diagnostic receipt SHA-256
  `de4241bd26b77f5dac7df746d165034b67e6f8105133daf0359142a97dd35d5d`.
- `omniperf` 2.0.1 is now runnable through a sealed Python environment and `rocprof` v1. A manual
  IQ2_XXS smoke produced 260 dispatch rows, proving fallback reachability, but is non-evidence. The
  governed fallback runner fails closed because frozen v9 lacks its seeded/repeated producer flags;
  the passing evidence replay waits on OP-11. The deterministic paired-`rocprofv2` report remains C4's
  primary path; Omniperf is the measured IQ2 crash-boundary fallback.
- **Standing caveat, now narrowed**: direct `rocprof` v1 whole-model SQ/TA captures read zero and it
  aborts at init on graph-enabled builds. The Omniperf op smoke had nonzero `SQ_WAIT_ANY` and TCC
  request/miss totals but zero VALU/VMEM/hit fields, so treat it as a partial diagnostic until the
  seeded runner passes; use `rocprofv2` for the established C4 surfaces.
- Having the tool does **not** authorize profiling a live server — co-residency is owned by whoever
  owns that inference. **Corrected 2026-08-10 (operator):** the rest of this line used to read "GPU runs
  remain operator-approved", which is wrong as a blanket. P-GPU-1 governs the **class of claim**, not
  permission to run; an AutoKernel experiment on an idle card needs no per-run approval. The live-server
  clause is the part that survives
- [x] **Apply the "does the caller propagate this check's answer?" screen to the whole probe family.** ✅
  2026-08-11 — `test_shell_pipeline_status.py` walks every owned `scripts/kernel_rnd/**/*.sh` wrapper,
  requires `#!/bin/bash` plus `set -euo pipefail` before its first pipeline, and refuses any later
  `set +o pipefail`. The
  bandwidth probe shipped with `hipcc … 2>&1 | tail -20`, which takes its exit status from `tail`, so a
  failed build exited 0 and the script walked on to the reporting path — a non-compiling probe was
  committed looking like a working one. Fixed there (`PIPESTATUS` + `exit 5`), but the same shape is
  available to every wrapper we own that pipes a compiler, a test runner or a validator. This is the
  complement to the screen we already have (*"can I make this check pass by deleting the thing it
  inspects?"*), and `feedback_pipe_hazards` already records it for piped pytest

#### C6 monitor design — five rules from a sabotage/sandbagging red-team (intake-979#record; 2026-08-03)

_Via `/research-intake` Stage-2b. C6 is our named differentiator and it had no design for the case where
the agent **underperforms deliberately** rather than cheats. The completed prompt/plumbing controls below remain in place; their local cost and kernel detection benefit were not measured by this source._

**Why this reaches kernel work at all** — the observed ML-engineering sandbagging strategies motivate hypotheses for our domain (intake-979#00), not measured kernel behavior. Verbatim from the source: *"agents might train their models on a needlessly small subset to
avoid supposed memory issues, or use small and few layers for their CNNs."* Kernel analogues:
conservative tile/block sizes justified by "LDS pressure", disabled fast paths justified by "numerical
safety", low unroll factors justified by "register spills". **These kernel examples are individually defensible hypotheses; this paper did not evaluate their evasion of a kernel monitor.**

- Secondary signal available free: attempting sabotage **reduced main-task performance** for both
  scaffolds in the study — a measurable tax usable as corroboration
- **Cite the qualitative sandbagging finding, never a number**: the AUCs live only in a plot legend that
  is not text-extractable from either the PDF or the HTML render (NOT-FOUND-IN-SOURCE)


**Source-scope correction 2026-10-06:** these edits qualify the external rationale only. All completed 2026-08-11 controls, task text and implementation outcomes above remain preserved; no new detection result or implementation task is claimed. The audit was PARTIAL and did not read numeric image-only legends or implementation artifacts.

#### Auto-kernel revival — research-intake integration 2026-07-22 (C6 + task-contract from OpenHyra/HyRA)
_Via /research-intake Stage-2 (intake-884 HyRA, intake-885 OpenHyra). OpenHyra effectively implements the C6 anti-reward-hacking differentiator this backend owns but never built._

##### Follow-up discovered during C6 implementation — 2026-07-22
- [x] Verify a fail-closed C6 sandbox on the live host and remove the unsandboxed route from real
  kernel-authoring execution. ✅ 2026-08-11 — the campaign path now uses
  `autokernel/execution/sandbox.py`, not the 2026-07-22 `c6_reward_integrity.py` prototype (which has
  no AutoKernel caller outside its regression tests). A scoped `/sys/fs/cgroup/autokernel`
  delegation plus Landlock ABI 6 and seccomp was exercised as uid 1000: an in-tree write succeeded;
  an outside write and evaluator-receipt forgery failed; host signalling and socket creation returned
  `EPERM`; and teardown killed an escaped descendant, proved empty membership, and removed its leaf.
  `execution/provision_cgroup.sh` makes the host prerequisite reproducible after boot. The live path
  has no `allow_unsandboxed`/environment bypass: missing delegation refuses before spawn.

#### 2026-08-09 — C4 report contract and capture protocol (research-intake Stage-2b)

Source: [intake-1026](../../research/intake_index.yaml) (SGLang `llm-torch-profiler-analysis` skill) and
intake-1029 (its two reference catalogs), both dive-verified 2026-08-09 against
`sgl-project/sglang` `main`. SGLang is Apache-2.0. **These are design references, not components** —
the upstream tooling parses torch-profiler Chrome traces and declares no ROCm path anywhere.

- [x] **RVP-1 — Adopt the three-table output contract as the C4 report spec** ✅ 2026-08-11:
  `profile_report.py` emits kernel /
  overlap-opportunity / fuse-pattern, rendering only rows at or above a `1.0%` cumulative GPU-time
  share. **The report layer is separable from the parser** — verified in source:
  `scripts/analyze_llm_torch_profile.py` renderers (`render_kernel_table_for_stage`,
  `render_overlap_table_for_stage`, `render_fuse_table_for_stage`) all take `rows: Sequence[dict]`,
  with parsing delegated to sibling `triage_kernel_helpers` / `triage_overlap_helpers` /
  `profile_common` modules. So only a `rocprofv2` row adapter has to be built. Adopt the determinism
  rule verbatim (source-backed matching, explicitly *not* a fuzzy matcher) and the bounded
  `high` / `medium` / `low` similarity vocabulary.
- [x] **RVP-2 — Split the C4 HIGH-risk path into a deterministic pass plus a bounded judgment pass,
  then re-score the C4 row.** C4 currently reads as "GEAK-v2 LLM-reads-raw-`rocprof`". The reference
  design does not do that: a deterministic script emits the tables, and the model is confined to the
  similarity note and the catalog comparison. This *shrinks* the trusted surface rather than adding
  to it, and is the cheapest available de-risking of the standing HIGH-risk row. ✅ 2026-08-11 — the
  optional receipt admits only an emitted pattern id, `low|medium|high`, and a catalogue comparison;
  measured/source fields are unknown-field errors.
- [x] **RVP-3 — Adopt the two-trace mapping/formal protocol.** Capture an attribution trace first with
  graphs disabled or a lower-fusion configuration, then a formal trace with the real optimizations on,
  because graphs and fusion destroy `kernel -> cpu_op -> source` mapping. Upstream explicitly forbids
  calling the mapping pass a fast profile. **Convergence worth naming**: this handoff already records
  that `rocprof` v1 *aborts at init on graph-enabled builds*. The capture mode our profiler can
  survive is the same one that yields source attribution — so this is a two-phase protocol, not a
  workaround for a defect. ✅ 2026-08-11 — the manifest requires mapping mode
  `graphs_disabled|lower_fusion`, formal mode `production_optimizations`, one source commit and one stage.
- [x] **RVP-4 — Adopt the capture discipline**: warm up before arming the profiler and bound the
  capture (upstream default is 10 warm-up / 5 active steps), and keep prefill and decode captures
  stage-separated so they are never averaged together. ✅ 2026-08-11 — v1 requires exactly 10 warm-up
  and 5 active steps and rejects prefill/decode mixing.
- [x] **RVP-5 — Adopt architecture-shape matching as a profiling primitive.** Attribute trace structure
  to *architectural blocks*, not only to kernel names: repeating trace groups map to the model's layer
  pattern. Kernel names drift (see the K28 rename evidence in
  [`k28-fused-chunked-gdn-kernel-research.md`](../completed/k28-fused-chunked-gdn-kernel-research.md)); block
  structure does not. ✅ 2026-08-11 — reviewed architecture blocks are exact ordered family sequences;
  the mapping trace reports their occurrence count without fuzzy kernel-name inference.
- [x] **RVP-6 — Log RocmProfileData (RPD) as a fourth profiler candidate** alongside `rocprofv2`,
  `rocprof` v1 and `omniperf`, and check gfx90a availability before assuming any RPD-based workflow is
  reachable on this box. Source intake-1027 is `stage1-unverified` and is MI300X/gfx942 only —
  **no figure from it may be cited for any purpose.** ✅ 2026-08-11 — every report must declare all
  four candidates and RPD's independent `gfx90a_state`; missing RPD is a manifest error.
- [x] **RVP-7 — Decide our catalog scope deliberately instead of inheriting it.** intake-1029's catalog
  excludes "host-only scheduler, event-loop, executor, offload, and load-path patterns" by explicit
  written policy. A host/device transfer bottleneck therefore has no row and cannot be surfaced by a
  kernel-time-share table at all. Either widen the scope or pair the catalog with a host-side one.
  ✅ 2026-08-11 — `kernel_only` emits the host-path coverage gap; `kernel_and_host` requires a hash-bound
  host catalogue receipt. No report silently inherits either scope.

**Strict-contract repair and replay (2026-08-11).** Research commit `d7260844` closes four admission
gaps found after the first live captures: the 1% floor now applies to overlap/fuse rows as well as the
kernel table; mapping/formal traces must bind the same workload/source/stage while using distinct
corpus IDs and paths; stage labels are derived from workload semantics; and a host catalogue can no
longer alias the kernel-catalogue hash. Reviewed family-alias sets preserve architecture-shape
matching across declared renames without adding fuzzy matching. The full AutoKernel suite passed
3,972 tests with one declared expected failure.

The first post-repair Q4_K mapping attempt retained a fail-closed `rocprofv2` exit-139 receipt. One
identity-matched retry succeeded with **195 mapping + 195 formal dispatches**, **80** device samples,
and a released MI210 claim. The report declares `kernel_only`, independently records the host gap,
applies the 1% floor, and finds `mul_mat_vec_q` **42.107%**, `quantize_q8_1` **30.457%**, and runtime
fill **27.436%** at the bounded `m=16,n=1,k=256` decode cell. Receipt:
`/mnt/raid0/llm/autokernel/probes/c4-q4k-strict-contract-v9-20260811-r2/receipt.json` (SHA-256
`23f14e71015d21d021b4f6ee6128cd34a52b73f3e756b39e0a47243dd9bb9bfb`). This validates the repaired
contract on gfx90a; it does not claim the tiny cell provides Item B's requested inside-kernel unpack
attribution.

**Declined here, recorded so they are not re-derived**: (a) inheriting the upstream synthetic stage
shapes (prefill `4090`/`1`, decode `1`/`2048`) without re-deriving from our own production
prompt-length distribution — a gate's scope must match the measured subset; (b) adopting the upstream
analysis scripts as a component, since they parse torch Chrome traces and `rocprof` output is not one.

---

#### 2026-08-10 — C2 correctness oracle, C6 reward integrity, and three zero-cost probes (research-intake Stage-3)

_Via `/research-intake` (8 URLs + 2 operator-supplied inline documents → 16 entries, 5 Stage-2 dives,
13 Stage-2b ingest-and-dives). Every `file:line` below was read directly in the FROZEN production tree
`/mnt/raid0/llm/llama.cpp` @ `67a433bf45a8`, branch `production-consolidated-v8`, on 2026-08-10 —
these are citations of **our own** code, not of any source. Nothing here modifies the frozen tree;
C2/C6 work lands in `llama.cpp-experimental` and in the harness that drives it._

##### The finding that reorders this handoff's priorities

The C2 row above says "ADOPT then HARDEN". The dives found that **the thing we planned to harden does
not do what its name implies**, in three independent ways:

1. **The reference is a sibling, not an independent implementation.** `ggml-cpu.c:3041` reads
   `if (ggml_cpu_disable_fusion || cplan->use_ref) { return 0; }` — `use_ref` **disables fusion and
   tiling**, and the "reference" then runs the *same* type traits, the *same* dequantisers, and the
   *same* vectorised inner loops. A defect shared by both sides is invisible to an elementwise
   comparison, by construction.
2. **The tolerance admits large errors on exactly our target class.** `test-backend-ops.cpp:5942`
   (`struct test_mul_mat_vec_fusion`) overrides `max_nmse_err()` at `:6120-6121` to return `5e-3`.
   NMSE `5e-3` is **≈ 7.1 % RMS relative error** — and dequant-GEMV is the op family the MI210
   program is actually aimed at.
3. **Every T0 failure we have ever seen was unreproducible by construction.**
   `init_tensor_uniform` (`test-backend-ops.cpp:54`) draws from
   `thread_local std::default_random_engine gen(std::random_device{}())` (`:62`), and there is **no
   seed flag anywhere** in the tool. A failing case cannot be re-run as the same case.

None of that is an upstream criticism — `test-backend-ops` is a regression tester and is good at that
job. It is a statement about **what a reward-bearing oracle needs that a regression tester does not**.

##### Zero-cost probes — run these first; two of them can close later work for free

- [x] **RVP-T0-2 — MFMA disassembly audit (row C3).** `roc-obj` + `llvm-objdump --disassemble
  -mcpu=gfx90a` over the hot `mul_mat` kernels in `libggml-hip.so`; grep for `v_mfma_*`. **Static
  only — no GPU time, no server.** If MFMA is absent from the paths this program cares about, that is
  a larger deflation of our standing baseline than any published-number dispute, and it is answerable
  today. Pair with the `mfma-decode-kernels-are-worth-zero` HARD_CONSTRAINT (`autokernel-research-loop.md`
  §19.2): that entry is about *decode arithmetic intensity*, so an MFMA absence in **prefill** paths
  would not be covered by it. ✅ 2026-08-10 — 57/134 gfx90a disassemblies contain MFMA and 38 of
  those also contain `mul_mat`; MFMA-total-absence is falsified, without claiming runtime dispatch or
  hotness. Evidence: [`artifacts/audit/autokernel-static-probes-20260810.md`](../../artifacts/audit/autokernel-static-probes-20260810.md).
- [x] **RVP-T0-5 — Static audit of `init_tensor_uniform` call sites (row C2).** Classify every call
  site in `test-backend-ops.cpp` as one-sided (e.g. `(0.9, 1.1)`) or symmetric about zero. This
  decides where the negate transform in RVP-C2-3 is worth its runtime and where it is a provable
  no-op, and it is the input to the degenerate-range screen in RVP-C2-7. Pure grep + read. ✅ 2026-08-10
  — all 56 sites classified: 44 symmetric, 9 one-sided, 3 asymmetric across zero. Evidence:
  [`artifacts/audit/autokernel-static-probes-20260810.md`](../../artifacts/audit/autokernel-static-probes-20260810.md).

##### C2 — build the oracle the loop actually needs

Sequenced: **RVP-C2-1 is a precondition for every other row here.**

  - *(folded into INF48-LIVE-2; full text at b3bd883d3:544)* **RVP-C2-1 — Seeded input generation.**
- [x] **RVP-C2-2 — Property layer (the only axis independent of the sibling).** ✅ 2026-08-26 —
  the producer SHIPPED: the instrument branch `codex/autokernel-gqa7-correctness-instrument-20260818`
  @ `5bbcc5498` (08-18) emits **AK_PROP_V2** from `test-backend-ops` (the earlier V1 schema is
  superseded; research parses both) with `--suite-seed`/`--autokernel-property-self-test`, and the
  AutoKernel V27 deployment seals it (`instrument-review.json`, receipt `7c1dfca1`) — the target is
  in build/run today. The reference-free `double`-hosted residual contract stands; the seeded-defect
  gate (RVP-C6-6) and the first live `backend_op_units` measurement event remain the empirical
  follow-up (SC18 in the vidya program tracks the first tuple).
  - [x] **Live property acceptance within the value-transform pass.** ✅ 2026-08-11 — the 779-case
    pass covered `SOFT_MAX`, `ARGSORT`, `TOP_K`, and `SOLVE_TRI`. The `SOFT_MAX` invariant was
    corrected before acceptance to include the operation's implicit attention sink mass rather than
    demanding that only the explicit output cells sum to one. The parent row remains open until the
    producer and seeded-defect gate are durable.
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:562)* **RVP-C2-3 — Value transforms.**
  - [x] **Live value-transform acceptance.** ✅ 2026-08-11 — suite seed `4711` passed **779/779**
    cases across `SOFT_MAX`, `ARGSORT`, `TOP_K`, and `SOLVE_TRI`; every case completed identity,
    ×3, ×0.01, and negate. This validates the live pass but does not make its producer durable.
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:574)* **RVP-C2-4 — Layout / stride axis, as a SEPARATE pass with its own flag.**
  - [x] **Live layout acceptance.** ✅ 2026-08-11 — **1,048/1,048** emitted layout cases passed the
    separately gated offset, stride-gap, and transpose-family contract. This validates the live pass
    but does not make its producer durable.
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:587)* **RVP-C2-5 — Stateful-op triad.**
  - [x] **Live acceptance probe.** ✅ 2026-08-11 — suite seed `4711` passed **5,184/5,184** cases
    across `SSM_SCAN`, `SSM_CONV`, `FLASH_ATTN_EXT`, and `GATED_DELTA_NET`. Every emitted
    `AK_STATE_V1` receipt had `initial_equal=1`, `input_immutable=1`, and one or more final-state
    outputs. Research commit `9cc3ed1b` supplies the fail-closed consumer. The parent row remains
    open because its experimental producer is still uncommitted pending explicit operator approval.
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:598)* **RVP-C2-6 — fp64 CPU reference with a ratio gate.**
  - [x] **Implement and live-validate the independent host-double oracle.** ✅ 2026-08-11 — Q4_0,
    Q8_0, Q4_K, and Q6_K are decoded directly from GGUF wire bytes rather than project quant helpers.
    The final metric id is `fp64_error_ratio/host-double-gguf-wire/v1`. Five representative CPU cases
    and the dedicated broadcast-indexing regression passed; the real receipt parser remained compatible
    across 31 parser tests; and the property self-test caught 5/5 planted defects while accepting 5/5
    clean cases. The implementation remains uncommitted pending explicit user approval.
  - [x] **RVP-C2-6a — Correct oracle coverage and isolate the stock ROCm Q4_K failures.** ✅ 2026-08-11 —
    the first matrix exposed a real non-contiguous-row coverage bug in the host-double decoder. Reading
    each logical row through `nb[1..3]` fixed that oracle defect. The corrected forced-dispatch matrix
    retained 43 cases per arm: force-rocBLAS passed 43/43 with maximum error ratio 1.2283, while
    force-MMQ passed 18/43 and failed 25 with maximum ratio 3.0361. This is now an MMQ-specific stock
    correctness finding under unchanged κ=1.5. Receipt:
    `/mnt/raid0/llm/autokernel/probes/rvp-c2-6a-rocm-q4k-dispatch2-20260811T1042Z/receipt.json`, SHA-256
    `6e7870558c6317a7ef12f7fca8a267466cc0734295d0c33562103a0c022a3502`. Research runner:
    `scripts/benchmark/run_rocm_q4k_fp64_matrix.py`.
  - [x] **RVP-C2-6b — Correct the stock gfx90a Q4_K MMQ path without changing κ=1.5.** ✅ 2026-08-11 — Preserve the
    force-rocBLAS 43/43 control, retain all 25 force-MMQ failures as regression cases, and do not rank
    this surface until the corrected MMQ arm passes the same matrix. **2026-08-11 diagnostic:** a
    separately compiled force-MMQ DP4A arm reproduced the same 25/43 failures (maximum ratio 3.0178),
    so the defect is not the gfx90a MFMA implementation. It is common to MMQ's Q8 activation staging;
    do not spend the repair on an MFMA-only patch. Receipt:
    `/mnt/raid0/llm/autokernel/probes/rvp-c2-6b-q4k-dp4a-20260811T1300Z/receipt.json`, SHA-256
    `c955f5df4cd584586b0e59746b8dc1e2542fbde57a558de0257ba616dee78021`.
    A second Q4_K-only least-squares refinement of the existing per-32 Q8 activation scale also
    failed 25/43 (maximum ratio 2.8834) while the rocBLAS control remained clean; it was reverted, so
    no source delta survives. Receipt:
    `/mnt/raid0/llm/autokernel/probes/rvp-c2-6b-q4k-ls-scale-20260811T1430Z/receipt.json`, SHA-256
    `476e6fb3fc004b30067ea9de4826a094a90db529c610670673c159e803342d89`.
    Root cause was instead the affine Q4_K reconstruction mixing two activation populations: the
    quantized dot used dequantized Q8 values (`q*d`), while the min-correction used the original
    pre-quantization float sum. The local `quantize.cu` fix derives the min-correction sum from the
    same quantized/dequantized Q8 values for Q4_K DS4, in both ordinary and scatter paths. The final
    default, force-rocBLAS, force-MMQ MFMA, and force-MMQ DP4A matrix passed **172/172** cases with
    zero failures and maximum error ratio 1.2283 under unchanged κ=1.5. Receipt:
    `/mnt/raid0/llm/autokernel/probes/rvp-c2-6b-q4k-qsum-final-20260811/receipt.json`, SHA-256
    `355bdcf169cb8682d2f56e1754b321f770a0fe3c0bbc5f6e1dc58eaffb443fb2`. The source fix remains
    uncommitted and approval-gated; this row closes the diagnosis and live correction, not promotion.
  - [x] **RVP-C2-6c — Bind the exact four Q4_K MMQ receipts into AutoKernel planner authority.** ✅
    2026-08-16 — research `5ae54e0ae4a80ab02450f703617b6a769599caf2` carries the stock 18/43
    result, DP4A and least-squares negatives, and diagnostic 172/172 same-population repair as
    immutable `candidate_only` evidence. Source authoring and performance ranking now refuse until a
    committed clean-source repair passes the unchanged κ=1.5 matrix.
    - *(folded into INF48-LIVE-2; full text at b3bd883d3:646)* **(no title)**
  - *(folded into INF48-LIVE-2; full text at b3bd883d3:649)* **RVP-C2-7 — Degenerate and insensitive-case screening.**
  - [x] **RVP-C2-7a — Build the two-axis research reducer and claim-aware runner.** ✅ 2026-08-11 —
    research commit `000a2686`, promoted to `main` via `f3c6b24a`; the focused reducer passes 14/14.

  **OP-11 RESOLVED 2026-08-12 — operator selected Option B (decline for now).** No experimental
  commit or push occurred. The implementation remains a local diagnostic, the smoke remains
  non-evidence, and producer-dependent closure remains unavailable unless the operator reopens it.


##### C6 — reward integrity: close the instrument gap first

- [x] **RVP-C6-1 — Hash-pin the measurement translation units.** `tests/test-backend-ops.cpp`,
  `tests/test-quantize-perf.cpp` and `tools/llama-bench/llama-bench.cpp` are hashed against the
  production anchor before every measured round; **any diff is a hard fail, not a warning.**
  **This is the highest-value single item in the batch.** C6 as designed pins the *evaluator*; but the
  *instrument* is compiled from the very tree the candidate is allowed to edit. No timer redesign
  fixes that — only pinning the sources does. The gate must also refuse to be satisfied by deleting
  the file it inspects (`feedback_verify_integrity_not_presence_of_own_edit`). ✅ 2026-08-11 — the
  reviewed measurement anchor is hardened commit `a4cb04ca8`, whose direct parent is frozen production
  v9 `0db32c06`; the one-commit overlay changes only `llama-bench` and its README. T0, T1 open and every
  T1 invocation hash the complete three-file manifest against that named anchor and hard-refuse a
  missing, unreadable, deleted or changed file. Pinning to the reviewed overlay rather than pretending
  its intentional instrument change is byte-identical to production preserves both authorities.
  - **Provenance note 2026-09-16 (sub-closure-fix; annotation only, box state untouched):** the cited anchor `a4cb04ca8` (`a4cb04ca8f92fa4d665684490f609b380f9b5e96`) **exists on no ref**. It is absent from all llama.cpp `fork` refs (`ls-remote`), from the canonical tree and from every local clone (`git cat-file` fails). The equivalent hardening lineage is llama.cpp `974b5fcb3` ("llama-bench: harden AutoKernel measurement instrument", sole parent frozen v9 `0db32c06`). It is the tip of `fork/experimental-v9-autokernel-t1-hardening-final`, **not** of `fork/experimental-v9-autokernel-t1-hardening` (tip `0492c2319`, a separate one-parent commit). Descendants include `d9fdc17bd`. Live manifests still pin the missing SHA: `/mnt/raid0/llm/autokernel/iqk-*.json` (6 files, e.g. `iqk-bootstrap-intervention-r3-execute.json`). The owner should re-point the pin and re-hash the manifest. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #1).
- [x] **RVP-C6-1a — Finalize the clean one-parent measurement-instrument lineage.** ✅ 2026-08-12 —
  `a4cb04ca8f92fa4d665684490f609b380f9b5e96` is clean, pushed, has frozen v9 `0db32c06` as its
  sole parent, and is the instrument pinned by the live-control path. Its real CPU smoke emitted all
  six required receipt families and released the exact q0–q3 claim; the all-PASS v9 preflight binds
  source, copied binary, capability, model, topology, storage, production, and package power.
  - **Provenance note 2026-09-16 (sub-closure-fix; annotation only, box state untouched):** the cited anchor `a4cb04ca8` (`a4cb04ca8f92fa4d665684490f609b380f9b5e96`) **exists on no ref**. It is absent from all llama.cpp `fork` refs (`ls-remote`), from the canonical tree and from every local clone (`git cat-file` fails). The equivalent hardening lineage is llama.cpp `974b5fcb3` ("llama-bench: harden AutoKernel measurement instrument", sole parent frozen v9 `0db32c06`). It is the tip of `fork/experimental-v9-autokernel-t1-hardening-final`, **not** of `fork/experimental-v9-autokernel-t1-hardening` (tip `0492c2319`, a separate one-parent commit). Descendants include `d9fdc17bd`. Live manifests still pin the missing SHA: `/mnt/raid0/llm/autokernel/iqk-*.json` (6 files, e.g. `iqk-bootstrap-intervention-r3-execute.json`). The owner should re-point the pin and re-hash the manifest. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #1).
- [x] **RVP-C6-2 — Stream-escape defence.** ✅ 2026-08-11 — the hardened lineage culminating in
  `a4cb04ca8`
  implements the ordinary/full-device-synchronized hybrid twin and the research reducer at
  `eda8de1a` requires `hip_full_device`, retains both timing vectors, and refuses an excessive twin
  gap. Live AK-BH-2 evidence (`/mnt/raid0/llm/autokernel/probes/ak-bh-2-factorial-20260811T0952Z/receipt.json`,
  SHA-256 `2a53cee2d8513737eca894e0f34152549932b75f3e04ef541cdee1848472cfdf`) exercised all eight
  ROCWMMA × MFMA × flash-attention arms with `autokernel_hybrid_ab_complete=true`,
  `autokernel_escape_checks_complete=true`, and `autokernel_device_sync_mode=hip_full_device`.
  Verified: T0 timing brackets
  `ggml_backend_graph_compute` with host wall clock (`tests/test-backend-ops.cpp:1621-1627`), and
  `ggml_backend_cuda_synchronize` (`ggml/src/ggml-cuda/ggml-cuda.cu:2512-2518`) calls
  `cudaStreamSynchronize(cuda_ctx->stream())` — **one stream**. Work issued on a second stream is not
  waited on and falls outside the timed region. Add (a) a hybrid A/B that repeats the measurement
  behind a full device synchronize and (b) a stream-creation audit in the source-integrity gate.
  **A candidate need not look malicious to do this** — multi-stream is an ordinary in-tree idiom.
  - **Provenance note 2026-09-16 (sub-closure-fix; annotation only, box state untouched):** the cited anchor `a4cb04ca8` (`a4cb04ca8f92fa4d665684490f609b380f9b5e96`) **exists on no ref**. It is absent from all llama.cpp `fork` refs (`ls-remote`), from the canonical tree and from every local clone (`git cat-file` fails). The equivalent hardening lineage is llama.cpp `974b5fcb3` ("llama-bench: harden AutoKernel measurement instrument", sole parent frozen v9 `0db32c06`). It is the tip of `fork/experimental-v9-autokernel-t1-hardening-final`, **not** of `fork/experimental-v9-autokernel-t1-hardening` (tip `0492c2319`, a separate one-parent commit). Descendants include `d9fdc17bd`. Live manifests still pin the missing SHA: `/mnt/raid0/llm/autokernel/iqk-*.json` (6 files, e.g. `iqk-bootstrap-intervention-r3-execute.json`). The owner should re-point the pin and re-hash the manifest. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #1).
- [x] **RVP-C6-5 — Keep provenance detection in its own component.** Substitution / call-provenance
  checks populate `integrity_flags`, **never `correct`** (interface contract, §"Interface contract").
  The upstream reference built the merged version and reverted it within 30 minutes — **inherit the
  placement, not the removal**: their stated reason was that their top-10 users are trusted, a
  *social* control that does not exist for an autonomous loop. ✅ 2026-08-11 — provenance derivation
  remains isolated in `evaluator/integrity.py` and `evaluator/surface.py`; the evaluator event has no
  actor-settable `correct` field. The verdict alone derives status, provenance failures appear as
  `INTEGRITY:<gate>:<outcome>`, and any such flag structurally withholds the speed rank.
- [x] **RVP-C6-7 — Refine-prompt disclosure rule + PUBLIC/SEALED split.** Our loop is multi-turn, so
  the failure diagnostics fed back into a repair turn are a channel into the oracle:
  `test-backend-ops` prints `ERR = %.9f > %.9f` on failure, which hands the candidate the exact
  tolerance it must clear. Filter `diagnostics` at the seam (interface contract), and hold a SEALED
  case population the refine loop never sees. ✅ 2026-08-11 — `authoring_contract.py` requires
  predeclared PUBLIC and SEALED populations with content-addressed seeds, projects only PUBLIC
  diagnostics into refine context, replaces exact tolerance/evaluator disclosures with a generic safe
  finding, and has planted-leak tests proving sealed ids and details never reach the assembled prompt.
- [x] **RVP-C6-8 — T1 output-invariance across repetitions, with buffer-address rotation.**
  `llama-bench` repeats over the same input buffers with no output validation between reps — a live
  pointer-keyed-cache hole. Assert outputs are invariant across reps **and rotate the input buffer
  addresses between them**; address rotation is strictly stronger than a re-check, because it defeats
  memoization keyed on the pointer rather than on the contents. ✅ 2026-08-11 — the hardened lineage
  culminating in `a4cb04ca8` adds trusted `--autokernel-harden <seed>`: unique content per timed repetition, two
  simultaneously live contexts/input allocations per comparison, a same-content address-rotated
  untimed replica, and bitwise logits comparison. It exits nonzero on mismatch and exports hashes,
  addresses and working-set size; the evaluator refuses incomplete/reused receipts. The experimental
  CPU build succeeds. Real-model execution awaits explicit inference permission.
  - **Provenance note 2026-09-16 (sub-closure-fix; annotation only, box state untouched):** the cited anchor `a4cb04ca8` (`a4cb04ca8f92fa4d665684490f609b380f9b5e96`) **exists on no ref**. It is absent from all llama.cpp `fork` refs (`ls-remote`), from the canonical tree and from every local clone (`git cat-file` fails). The equivalent hardening lineage is llama.cpp `974b5fcb3` ("llama-bench: harden AutoKernel measurement instrument", sole parent frozen v9 `0db32c06`). It is the tip of `fork/experimental-v9-autokernel-t1-hardening-final`, **not** of `fork/experimental-v9-autokernel-t1-hardening` (tip `0492c2319`, a separate one-parent commit). Descendants include `d9fdc17bd`. Live manifests still pin the missing SHA: `/mnt/raid0/llm/autokernel/iqk-*.json` (6 files, e.g. `iqk-bootstrap-intervention-r3-execute.json`). The owner should re-point the pin and re-hash the manifest. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #1).

##### Recorded so it is not re-derived

- **`torch.rand_mix` — declined.** It is dead code upstream (0 of 270 call sites), and the upstream
  `randn` → `rand` switch that accompanies it is the *enabling condition* for a ReLU-identity hack, not
  a defence against one. Keep the four transforms in RVP-C2-3.
- **Peak-memory scoring, the upstream timing protocol, and a `speedup ≥ 1.0` pass clause — declined.**
  Ours are stronger on all three; adopting them would be a regression.
- **`KernelBenchX` / `ISO-Bench` / KernelBench task suites — declined as artifacts.** They are
  torch/CUDA and hard-fail without CUDA; no torch-ROCm is installed here and our unit under test is a
  C++ ggml op. This is a *technical* decline — per standing policy licences are not blockers for our
  self-hosted personal use, and nothing here is gated on one.

##### Additional actionables from the recovered Stage-2b reports — filed 2026-08-10, beyond the Stage-3 plan

_The Stage-2b analyst reports were recovered from the session transcript **after** the Stage-3 plan was
written, so they carry derived actionables the plan predates. These are the survivors; the declines at
the end are deliberate and recorded so they are not re-derived._

- [x] **RVP-C3-3 — Parse `rocm-smi` into numeric fields and add `throttle_observed`.** Capture is
  already mandatory and implemented, but it is stored as a **text blob** and the completeness audit
  only regex-checks that the word appeared — so a run that throttled 1700 → 800 MHz mid-window passes
  every check we have. Upgrade the audit from word-presence to value-presence. ✅ 2026-08-10 —
  AutoKernel `evaluator/devices.py` parses SCLK, MCLK, power and junction temperature into validated
  samples; evaluation-event v5 mechanically re-derives throttle and makes it verdict-bearing.
- [x] **RVP-C3-5 — Declare an absolute duration-window admission test** for any op-shape used to rank
  variants, with the lower bound **measured on gfx90a**. ✅ 2026-08-11 — the research implementation
  derives a 250,090,903 ns minimum from the first nominal-SCLK observation in the hash-bound RVP-T0-1
  receipt, refuses missing/foreign/sub-floor live GPU evidence before ranking, and exempts CPU and
  non-live arms. The focused device-sampler module passes 11/11 tests. These research-tree changes
  landed in research commit `5fbd471b5e7929d04113f7d5d95008837cd2107a`, an ancestor of
  research `origin/main` at `1448d93e3b3f42ef7b16484fe6cb3e770660c1e2`, in
  `scripts/kernel_rnd/autokernel/evaluator/devices.py`,
  `scripts/kernel_rnd/autokernel/execution/microbench.py`, and
  `scripts/kernel_rnd/autokernel/execution/test_device_sampler.py`. A clean detached worktree at that
  main commit revalidated the focused module at 11/11 on 2026-08-12.
- [x] **RVP-C6-9 — Build the two unbuilt detectors behind `AntiRewardHackingEvidence`**
  (`timing_dependent_branch_findings`, `environment_probe_findings`). Until they exist, an empty list
  must read **UNKNOWN, not PASS** — an empty result from a detector that was never built is exactly the
  fail-open shape this row exists to prevent. ✅ 2026-08-11 — versioned added-line scanners now inspect
  the committed candidate delta for environment probes and direct or simple data-flow timing branches;
  the real T0 provider records detector ids/findings. Missing ids make empty findings
  `COULD_NOT_CHECK`; planted/clean source-pattern tests report 100% sensitivity/specificity for this
  narrow detector taxonomy without claiming the broader RVP-C6-6 exploit corpus.
- [x] **RVP-VIDYA-2 — Bind the stranded G15, C4, and standalone-WGM profiler receipts into the
  AutoKernel/Vidya measurement seam.** ✅ 2026-08-11 — research `07b303cc` adds an isolated
  finalizer rather than modifying the CRITICAL shared C4 capture helper. It verifies immutable source
  receipts, released device claims, C4 report hashes, exact scored repetitions, physical ranges, and
  the WGM proxy's non-transfer-to-real-MMQ boundary before emitting a separate self-hashed
  `epyc.autokernel.profile_beliefs.v1` receipt. Root's existing auxiliary adapter now admits that
  schema through the one measurement ladder. Four current artifacts produced **16 rows**: G15 B=64/128
  throughput plus target-share signals, three formal family-duration rows each for Q4_K and Q8_0,
  and six standalone WGM proxy factors. The original profiler receipts remain unchanged.

**Declined, recorded so they are not re-derived:** lifting the 129 human-verified reference test files
as a component (design reference only — and the reason is **technical**: torch/CUDA, will not run
here); the `speedup >= 1.0` pass clause; the upstream `warmup=3, repeats=5` timing protocol, which is
weaker than our canonical one; and citing any foreign-hardware correctness-overestimation magnitude as
if it were ours — under P-GPU-1 the analogous magnitude is ours to derive on our own card.

#### Research Intake Update — 2026-08-15 (SOL-ExecBench reward-integrity imports; intake-1102/1103)

A Stage-2 dive of the SOL-ExecBench ROCm port audited its eleven reward-hacking checks against the
standard that documented-but-unimplemented does not count. **They pass**: every check raises, every one
is wired to a live call site, and detection is fail-closed at the record level, so a caught submission
yields a non-passing terminal status rather than a score. The strongest evidence is that the port found,
root-caused, measured and fixed an original timing bypass of its own — the timed loop deliberately never
syncs between iterations, so work on a submission-created stream never lands inside the event bracket,
and a 12.06 ms fp32 GEMM read 0.0069 ms, **1743× fast**. Apache-2.0, and every mechanism below is
architecture-independent, so none of this depends on the gfx90a constants question.

**Three gaps the audit found that neither repository originally closed** — all now implemented and
retained here as regression requirements in the 2026-08-16 AutoKernel graph:

> **ID note (corrected 2026-08-16).** These were initially filed as RVP-C6-8/9/10, colliding with
> three already-completed tasks of those names earlier in this file. The new work is C6-11/12/13;
> pre-2026-08-15 references to C6-8/9/10 continue to mean the earlier completed checks.

- [x] **RVP-C6-11 — Add a PHASE-DETECTION exploit case to the C6 reward-integrity screen.** ✅
      2026-08-16 — research `bcce7793` adds fail-closed source detection; `ad9dc65e` and `71a8c7a3`
      bind a cross-arm timed-output semantic oracle into the executable graph; an independently red
      black-box phase-switch case is green under the dynamic oracle. A candidate
      that computes correctly during the correctness rounds and degrades or no-ops once timing starts.
      Correctness runs in 10 rounds *before* timing and the timed-phase output buffers are never
      inspected afterwards (upstream issue #19, which the ROCm port inherits; the fix PR was closed
      unmerged). The shifting-pool allocator closes the naive version by carrying validated values into
      the timed loop — what remains open is a submission that can *distinguish* the two phases.
      **Zero of the 48 adversarial cases in their corpus attempts this.** Cite `intake-1102#record`.
- [x] **RVP-C6-12 — Add a `torch.compile` / CUDA-graph capture-and-replay exploit case.** ✅
      2026-08-16 — `bcce7793` rejects candidate-added compile/capture/replay, requires graphs off,
      address-and-content rotation, and validated timed outputs before C3 timing authority. Nothing in
      either repository probes a compiled or graph-captured kernel specializing on the address-shifted
      but value-identical timed inputs — and that is the single most likely tool an AI kernel-authoring
      agent reaches for. Their state-caching corpus covers address- and shape-keyed caches but **not
      content-fingerprint-keyed** ones, which is exactly what NVIDIA's own issue response named as
      bypassing pointer shifting.

#### Research Intake Update — 2026-08-21 (Hawkeye / agentic-kernel cohort; intake-1218..1236)

_Via `/research-intake` Stage-4, operator-approved plan. Nine dives, 18 dive-verified entries. Two
corrections to earlier framing are carried in deliberately: **C4 is CLOSED** (✅ 2026-08-11) and is not
reopened by any row here — these are C4-series extensions, per the established idiom; and **C5's primary
is unchanged** (GEAK-eval intake-674 + AgentKernelArena intake-679, the only gfx90a-PROVEN suites we
hold) — only the SECONDARY slot is re-scored._

##### C6 — reward integrity: three imports and a hardening pass

- [x] ✅ 2026-11-09 — merged to research main through `64a287b83` (branch ids f69569bc4 + 02b35fda0) (audit lineage 91a75a05e..32d48f3da on codex/autokernel-v27-descendant-20260823): Ghost Replay: two-process native no-op-interposer replay in evaluator/hawkeye_measurement.py; native identity/zero-launch/closure-mismatch/partial-log controls plus run_falsification.py L2 counting; tests green; [no-belief: software source implementation and finite regression controls; no measurement] **RVP-C6-14 — Implement GHOST REPLAY as a positive proof the kernel executed.**
- [x] ✅ 2026-11-01 — Research implementation `66085471f2af4020da9954606e5736cfb516725e`; test `scripts/kernel_rnd/c6_mutants/test_static.py` (16/16) and artifact `epyc-inference-research/artifacts/engineering/c6-library-substitution-20261031/verification.json`, proof `752196772d7005776a390700d1ff8c73afa546ff`; [no-belief: software source implementation and finite regression controls; no measurement] **RVP-C6-15 — Add a LIBRARY-SUBSTITUTION exploit case to the C6 hostile suite.** Detect a candidate
  satisfying the speedup reward by dispatching to rocBLAS/hipBLASLt/torch instead of executing generated
  code — an AST/dispatch-trace check, not a timing check. Live published precedent, not a hypothetical:
  `intake-1236#record` ships `CALL_LIBRARY` and `SOTA_TRITON_API` action tags in its released RL environment,
  neither disclosed in the paper, whose stated action space is Tiling/Fusion/Reordering/Pipeline. A
  "generated kernel" that wins by calling the vendor library is not a generated kernel, and a
  baseline-relative speedup metric cannot distinguish the two.
- [x] ✅ 2026-11-09 — merged to research main through `64a287b83` (branch ids f69569bc4 + 02b35fda0) (audit lineage 91a75a05e..32d48f3da on codex/autokernel-v27-descendant-20260823): Hawkeye measurement layer vendored and re-implemented as evaluator/hawkeye_measurement.py with the two JSON schemas recorded as our contract (schemas/HAWKEYE_NOTICE.md); [no-belief: software source implementation and finite regression controls; no measurement] **RVP-C6-16 — Vendor Hawkeye's measurement layer as the C6/C2/C3 base.**
- [x] ✅ 2026-11-09 — merged to research main through `64a287b83` (branch ids f69569bc4 + 02b35fda0) (audit lineage 91a75a05e..32d48f3da on codex/autokernel-v27-descendant-20260823): all four holes closed in hawkeye_measurement.py: per-iteration run-seeded perturbation (PerturbationTests), non-involution transform (test_order_insensitive_sum_changes), no pristine-input dir (IsolationTests), post-run SHA-256 source integrity (SourceIntegrityTests); [no-belief: software source implementation and finite regression controls; no measurement] **no checksum anywhere in the tree**
- [x] ✅ 2026-11-09 — merged to research main through `64a287b83` (branch ids f69569bc4 + 02b35fda0) (audit lineage 91a75a05e..32d48f3da on codex/autokernel-v27-descendant-20260823): roofline-derived implausible-speedup cap: c6_reward_integrity.py implausible_speedup_cap + RooflineTests (cap from workload envelope, unknown part refuses); [no-belief: software source implementation and finite regression controls; no measurement] **RVP-C6-18 — Add an implausible-speedup cap, sized from the roofline ceiling.**
##### C4 — extensions to a CLOSED component (taxonomy remains closed; these are additive)

- [x] **INF48-LIVE-3 [owner: autokernel (operator decision 2026-11-10; covered by INF-48)] RVP-C4-5..9,11 - ROCm 6.2 rocprof-v1 profile() backend, counter-taxonomy cross-check, hardware-context schema, per-rule telemetry, estimated-speedup logging.** No-GPU design/code work except C4-7 (counter collection confirm). C4-10 is closed (PC sampling unimplemented on this ROCm). [no-belief: new consolidated box] ✅ 2026-11-16 C4-5..9,11 all done (C4-10 closed earlier). [no-belief: software wiring plus filed row verdicts]
  - *(folded into INF48-LIVE-3; full text at b3bd883d3:1106)* **RVP-C4-5 — Implement `profile()` on ROCm 6.2 `rocprof` **
  - *(folded into INF48-LIVE-3; full text at b3bd883d3:1115)* **RVP-C4-6 — Cross-check our counter taxonomy against AMD's own gfx90a set.**
  - *(folded into INF48-LIVE-3; full text at b3bd883d3:1124)* **RVP-C4-7 — Confirm the nine Hawkeye cdna4 counters collect on gfx90a.** ✅ 2026-11-10 pass, row c4-7-hawkeye-counters-20261110 (all nine Hawkeye counters collect on gfx90a, ROCm 6.2; RESULT sha c749f790) [no-belief: row verdict filed by agent]
  - *(folded into INF48-LIVE-3; full text at b3bd883d3:1130)* **RVP-C4-8 — Adopt a two-slot hardware-context schema for the C4 prompt feed.**
  - *(folded into INF48-LIVE-3; full text at b3bd883d3:1137)* **RVP-C4-9 — Instrument every deterministic C4 rule with per-rule hit-rate telemetry.** ✅ 2026-11-11 research 48c43a547 (log_eval_run wired into arena_cell_runner, opt-in c4_telemetry; test_c4_9_wiring) [no-belief: software wiring, no measurement]
  - [x] RVP-C4-5 ✅ 2026-11-10 — research ad6e592ab+3b704071c (main 44e581f8a): rocprof_v1.profile() on ROCm 6.2 rocprof --stats; strict 5-column dform.py header, *.stats.csv glob, graphs off, no "--" (v1 would run it as the app); kept out of loop/ because hotspots.py is at its LOC ceiling; tests in test_c4_live3.py. A live check rides along in row c4-7-hawkeye-counters-20261110 stage B. [no-belief: software implementation, no measurement]
  - [x] RVP-C4-6 ✅ 2026-11-10 — research ad6e592ab: c4_counter_taxonomy.cross_check: IntelliPerf MI2 (74 counters/6 passes, sha-pinned) vs our 465-counter gfx90a enumeration → 74/74 declared, 0 passes over a block limit; TCP_GATE_EN1/EN2_sum and SQ_ACCUM_PREV_HIRES flagged UNVERIFIED (ACCUM aliases 4 different predecessors across 4 passes; collection untested). [no-belief: offline transcription/diff, no execution]
  - [x] RVP-C4-8 ✅ 2026-11-10 — research ad6e592ab: c4_hardware_context two-slot schema (arch constants + separate block-scheduling policy), closed key set + 1200-char cap; GFX90A_MI210 = 104 CU / 8 MB unified L2 / 1 die / no XCDs / linear, with an explicit "XCD remap = identity" advice; XCD dispatch on ≤1 XCD refused. [no-belief: schema, no measurement]
  - [x] RVP-C4-11 ✅ 2026-11-10 — research ad6e592ab: SourcePattern.estimated_speedup (optional, digest-stable) + profile_report.require_estimates; c4_rule_telemetry fold reports |est−ach|/ach mean AND worst per rule and overall. [no-belief: schema+reducer, no measurement]
  - RVP-C4-7: "offline leg ✅ research ad6e592ab hawkeye_plan: all nine declared, one rocprofv2 pass (SQ 6/8, TCC 4/4). Collection: row c4-7-hawkeye-counters-20261110 (rank 46, GPU smoke queued). [inference: GPU row c4-7-hawkeye-counters-20261110]"
  - RVP-C4-7 RESULT ✅ 2026-11-10 c4-7-hawkeye-counters-20261110 rc=0 pass: COLLECTED_ALL, all nine Hawkeye counters collect in one rocprofv2 pass on MI210/ROCm 6.2 (v10 GPU store), none absent, csv sha256 5347eb2f; filed by autokernel. [no-belief: row verdict filed by agent]
  - RVP-C4-9: "reducer ✅ research ad6e592ab c4_rule_telemetry; remaining: call records_from_report + append_records from the eval-backend run path."
##### C5 — secondary substrate re-score and corpus seeding

- **[declined: ws58 2026-11-03 content-review: benchmark-substrate bookkeeping (which external suite is "secondary"); no gate changes]** **RVP-C5-3 — Re-score the C5 SECONDARY from MultiKernelBench to KernelGenBench.** The row currently
  reads "MultiKernelBench 667 = secondary (multi-vendor abstraction only)". `intake-1227#record`
  (arXiv:2607.27231, `github.com/flagos-ai/KernelGenBench`, **Apache-2.0**) is a strictly better instance of
  that slot and names 667's deficiency verbatim: it "lacks a unified verification pipeline and consistent
  execution baselines". Decisive for us: 667 EXCLUDES gfx90a upstream and gates on ROCm >= 7.1, so it cannot
  run here at all, whereas KernelGenBench was built for five non-NVIDIA backends and therefore already
  externalises everything a sixth needs — per-platform requirements, prompt-template directories selected by
  runtime hardware detection, tolerances, and anti-hack config. Adding ROCm is POPULATING AN EXISTING
  EXTENSION POINT. Deliverable: clone at a pinned SHA, confirm those extension points, write
  `requirements_rocm.txt` against pytorch-triton-rocm matched to ROCm 6.2, run one ATen op on gfx90a.
  **HARD VERSION FLOOR, and it belongs in the file itself rather than only in a review comment:
  `flash-linear-attention>=0.5.2`.** This is not hygiene — omitting it *selects the defective
  release*. fla **0.4.2** declares `dependencies = ["torch", "transformers", "einops"]` with **no
  torch floor and no triton floor whatsoever**, and it is the release carrying the silently
  non-deterministic `causal_conv1d` backward (fla #1156). fla **0.5.2** — the fixed one — is the
  release that declares `torch>=2.7.0`. So a resolver asked for "an fla compatible with our
  Torch 2.5.1" walks straight onto the broken version and reports success. Put the pin in
  `requirements_rocm.txt` **and in every other place an fla install could be specified**; G6 below
  owns the torch-floor question, this row owns the pin. [intake-1283#record]
  **BOUND THE CLAIM: it is Triton-only end to end**, so a port measures Triton-on-CDNA2 and says nothing
  about llama.cpp HIP authoring; and it has NO AMD backend today (verified negative — zero AMD/ROCm/HIP/gfx
  strings in 24 pages; its six vendor requirements files contain no rocm entry). **PRIMARY UNCHANGED.**
- **[declined: operator 2026-11-09 (INF-48 triage, dropped, not done): KernelBench-style seeding; the live AK lane uses a served-shape oracle instead of C5 seed corpora]** **RVP-C5-4 — Seed `c5_seed_corpus.json` from the KernelGenBench vLLM subset.** — closed as dropped, not completed; original text: `git show b3bd883d3:handoffs/active/rocm-kernel-authoring.md` line 1167. [no-belief: dropped by operator 2026-11-09]
- **[declined: operator 2026-11-09 (INF-48 triage, dropped, not done): BackendBench anti-gaming patterns for the C5 corpus contract; the C6 hardened evaluator covers the live threat model]** **RVP-C5-5 — Harvest the BackendBench anti-gaming patterns into the C5 evaluation contract.** — closed as dropped, not completed; original text: `git show b3bd883d3:handoffs/active/rocm-kernel-authoring.md` line 1174. [no-belief: dropped by operator 2026-11-09]
##### Tooling note — rocprofv3 provisioned 2026-08-21

`rocprofv3` is now in the side-loaded tree (`rocprofiler-sdk6.2.0_0.4.0-66~22.04`, version-matched to
ROCm 6.2.0-66, added to `PKGS` in `epyc-inference-research scripts/benchmark/provision_rocm_profilers.sh`
and to its verify loop). `--verify` reports 5 present / 0 missing; `rocprofv2` and `rocprof` v1 are
unaffected — the package is additive. **`rocprof-compute` remains UNSATISFIED BY NAME**: we ship `omniperf`,
and the ROCm 6.3+ rename is what `intake-1223`'s harness checks for with `shutil.which()` at module import
before `sys.exit(1)`. That name, not rocprofv3, is what still gates the IntelliPerf/guided-tuning tool family.

##### C5 — ParEval trials (filed 2026-08-21 by operator decision, after the Stage-3 plan omitted them)

_These two were flagged tier-1 at the Stage-2b close-out but did not reach the approved plan text, so they
were left neither filed nor declined and surfaced as an open decision. Operator selected both. Source is
`intake-1225` (MIT, HPDC'24, credibility 6/6 — the highest of that cohort). **SC45 in
`vidya-belief-substrate-program.md` is a PREREQUISITE for both**: ParEval emits measurements, and the
write-side adapter must exist before the first run, never after._

- **[superseded: inf48-triage 2026-11-09: as a PRIORITY for the AK lane (it targets served llama.cpp ops, not ParEval corpora); the ParEval generation capture itself is NOT complete: PARTIAL, 103/2400 native records at the 2026-10-31 segment-2 boundary (5 ok, 98 UNKNOWN), 497/2400 at the 2026-11-05 resume, no correctness/timing/pass@k verdict. The running successor row `codex3-pareval120-k20-gen-r2-20261105` stays governed by the stop rule below; full text at b3bd883d3:1202]** **RVP-C5-6 — Trial the ParEval serial+omp arms on the EPYC 9655 as a CPU parallel-code substrate.**
  - 2026-10-31, generation first segment (`codex3-pareval120-k20-gen-20261031`, ended 12:16:21 UTC): **capability / PARTIAL, no acceptance verdict** against the predeclared 2,400-attempt capture rule. The cutoff snapshot has 52 completed native result records: 5 `ok`, 47 `UNKNOWN`; all 47 unknowns have empty completion content with a native `length` finish at 1,024 tokens, with original reasoning/response retained and no redraw. Native finish totals are 48 `length` and 4 `stop`. `PARTIAL.json` reports insufficient reserve before the next request; no final `TERMINAL.json` was present. The launcher automatically resumed at 12:18 UTC; this is the first-segment cutoff, not a current running total. Correctness, local sequential baseline, timing, pass@k, efficiency@k and SC45 measured projection remain **UNRUN**; RVP-C5-6 and SC45 remain open. Finish the existing declared capture, preserve all unknowns, then perform its separately declared contained evaluation. [Bounded native hash manifest and scope](../../artifacts/compute/codex3-pareval-segment1-20261031/README.md). [belief: cc]
  - 2026-10-31 results filing, ParEval generation segment 2 (ended 16:08:12Z rc75; server drain recorded): cumulative native result records at that boundary are 103/2400 (5 ok, 98 UNKNOWN), an additional 51 UNKNOWN records beyond the previously filed 52 (5 ok, 47 UNKNOWN). UNKNOWN preserves native responses whose content was missing; no exposed sample is redrawn. Of the 5 ok generation records, 4 finish stop and 1 finish length; none is a correctness pass. Remaining 2297 attempts were unexposed at that boundary. PARTIAL and owned-server drain evidence support this ended segment; automatic continuation was running by 16:09Z and later records are excluded. Generation remains partial capability capture; correctness, local sequential baseline, 1–96-thread timing, pass@k, efficiency@k, SC45 records and RVP-C5-6 completion remain open under the original tasks. [Segment evidence](../../artifacts/compute/codex3-results-filing-1633-20261031/pareval-segment2-aggregate.json). [belief: cc]
  - 2026-11-05 stop rule (operator-adhoc-takeover-20261105, for successor row `codex3-pareval120-k20-gen-r2-20261105`, which resumes the existing capture at 497/2400 with no redraw): stop-on-answer when all 2,400 declared attempts have a native record (ok or UNKNOWN); stop-on-futility when the 200 records after the resume point are >= 95% UNKNOWN empty-content `length` finishes, since the 1,024-token cap then decides the capture, not the model; gate-class = futility-only. [no-belief: stop rule, no measurement]
- **[superseded: inf48-triage 2026-11-09: ParEval HIP smoke corpus: same reason as RVP-C5-6; gfx90a HIP correctness is covered by c5_rocm_oracle.py + the served-shape oracle; full text at b3bd883d3:1220]** **RVP-C5-7 — Build the ParEval HIP arm on gfx90a and run its 60 HIP tasks as a smoke corpus.**
#### Research Intake Update — 2026-08-21 (Stage-2b second wave: reward-hacking, measurement and benchmark primaries)

_Filed from three Stage-2b batches that ran after the Stage-3 plan closed: `intake-1238#record` (Yang et al.,
SC24 power telemetry), `intake-1241#record` (TritonRL), `intake-1242#record` (GPA, CGO 2021),
`intake-1243#record` (PyTorch KernelAgent/KernelFalcon blog), `intake-1244#record` (CodegenBench),
`intake-1245#record` (FlashInfer-Bench), `intake-1246#record` (AutoKernel), `intake-1247#record`
(ParEval-Repo), `intake-1240#record` (GPU Forecasters). **C5 slots are UNCHANGED** — nothing displaces the
primary (GEAK-eval + AgentKernelArena) or the secondary (KernelGenBench), and the reasons are disjoint rather
than marginal: CodegenBench has no GPU of any vendor, FlashInfer-Bench has zero AMD content in a 423-path
tree, AutoKernel is a controller and not a benchmark, and ParEval-Repo dropped its HIP arm._

##### C6 — the sufficiency question, answered NEGATIVELY

**L1 + L2 IS NOT A SUFFICIENT C6 GATE.** `intake-1241#record` (TritonRL, Appendix H) enumerates five cheating
classes; L1 (AST blacklist) covers rule 1 and L2 (Ghost Replay) covers rule 2, leaving **three uncovered**.
The one that matters is **rule 3, OMISSION**: an operator implemented with a component missing contains no
blacklisted symbol (L1 passes) **and IS invoked**, so no-op-swapping it changes the output (L2 passes). That
is Shape C in its purest form. Note the two papers are **complementary, not nested** — KernelGenBench proves
the kernel RAN, TritonRL judges whether it COMPUTES THE WHOLE OPERATOR, and neither alone covers both.

- [x] ✅ 2026-11-09 — merged to research main through `64a287b83` (branch ids f69569bc4 + 02b35fda0) (audit lineage 91a75a05e..32d48f3da on codex/autokernel-v27-descendant-20260823): precision-downgrade gap closed: PrecisionContract with structural dtype/accumulator checks before tolerance, FlashInfer matched-ratio, three-run bitwise determinism (c6_reward_integrity.py; PrecisionTests); absorbs declined C6-23; [no-belief: software source implementation and finite regression controls; no measurement] **Worse: `intake-1227`'s adaptive tolerance is keyed BY DTYPE**
- **[declined: ws58 2026-11-03 content-review: merged into C6-22 (FlashInfer-Bench's correctness layer is the candidate fix for the precision-downgrade gap)]** **RVP-C6-23 — Adopt FlashInfer-Bench's correctness layer; it is the only gate of the four benchmarks
      dived that refuses a precision downgrade by construction.** `intake-1245#record` §4: keep the TIGHT
      per-element bound and budget a fraction `rho` of outlier elements (**matched-ratio rule**, example
      rho=0.95) explicitly INSTEAD of loosening a global tolerance — a systematic downgrade fails that
      because it moves the whole population, not 5% of it. Add **outright NaN/Inf rejection** and a recorded
      **MAXIMUM OBSERVED ERROR** per candidate, which makes a downgrade visible even on a pass.
      Arch-independent, so it needs no port. First read `flashinfer_bench/bench/evaluators/{lowbit,default}.py`
      @ `40e6ca78` and extract the ACTUAL default `eps_abs`, `eps_rel` and `rho` — the paper gives the
      inequality but only an example rho, and we need the numbers before claiming our gate is or is not tighter.
  - *(folded into INF48-LIVE-1; full text at b3bd883d3:1335)* **bitwise-determinism**
##### C4 — extensions to a CLOSED component (the taxonomy stays closed; these are additive)

**GPA is counter-agnostic AND STILL NOT a better C4 template than CudaForge or KernelPro — on our hardware it
is worse.** `intake-1242#record` falsifies the premise that predating the vendor lock implies portability:
GPA trades a metric-LIST dependency for a harder INSTRUMENT dependency. Three independent blockers, any one
fatal: (1) it needs per-sample **stall reasons**, which on AMD come only from **STOCHASTIC** PC sampling =
CDNA3+; gfx90a is **host-trap only**; (2) rocprofiler-sdk PC sampling needs **ROCm 6.4+** behind
`--pc-sampling-beta-enabled` and we are pinned at **6.2**; (3) the instruction blamer decodes NVIDIA SASS
control codes via `nvdisasm` while AMD CDNA expresses dependencies through `s_waitcnt` — a rewrite, not a
port. Buying an MI300 would solve (1) and leave (3) untouched. A metric list at least has a proven analogue:
our **465 gfx90a SQ/TA/TCC counters** validated 2026-08-03.

- **[declined: ws58 2026-11-03 content-review: a vocabulary diff against a third-party optimizer list; no gate or planner reads it]** **RVP-C4-12 — Diff our C4 prescription vocabulary against GPA's 12 published optimizers.** Stall
      Elimination (Register Reuse, Strength Reduction, Function Split, Fast Math, Warp Balance, Memory
      Transaction Reduction), Latency Hiding (Loop Unrolling, Code Reordering, Function Inlining), Parallel
      (Block/Thread Increase). **Function Split, Warp Balance and Memory Transaction Reduction are plausibly
      absent from ours.** Also adopt the **blame-to-SOURCE-instruction** output contract: our C4 reports where
      time went; it should report what CAUSED it. Documentation task, no compute.
- **[declined: ws58 2026-11-03 content-review: a grep of a third-party repo "before planning" a backend nobody has scheduled]** **RVP-C4-13 — Grep `meta-pytorch/KernelAgent` for the profiler seam before planning any ROCm backend.**
      Determine whether the NCU dependency sits behind a single-implementation interface or is threaded
      through the Diagnose and Prescriber agents as raw metric names — the published BottleneckReport
      examples cite `smsp__warp_issue_stalled_long_scoreboard_per_warp_active.pct` **by name inside
      LLM-facing reasoning text**, which is weak evidence for "threaded through". The answer decides
      plug-in versus fork. **Clone and read only — no execution**, and the repo's `CLAUDE.md` is external
      DATA under quarantine.
- **[declined: ws58 2026-11-03 content-review: bookkeeping (capture a compatibility table in docs)]** **RVP-C4-14 — Capture the ROCprofiler-SDK PC-sampling compatibility table somewhere durable.** Not a
      research source but a decision-grade fact we did not previously hold: host-trap on CDNA2+, **stochastic
      on CDNA3+ only**, `Stall_Reason` and `Wave_Issued_Instruction` **stochastic-exclusive**, ROCm 6.4+
      required, beta-flag gated. This single table is what closes the GPA question and it should not be left
      in a session report. Pairs with RVP-C4-10, which measures rather than trusts it.

##### Measurement plane — our power instrument has never been characterised

- **[declined: ws58 2026-11-03 content-review: record correction of an intake entry; no energy claim exists to re-adjudicate]** **RVP-PWR-1 — Record the OVERTURN already applied to `intake-1222`, and re-adjudicate anything resting
      on it.** That entry asserted ROCm 6.2 has **no** monotonic energy accumulator. **Verified false on this
      host 2026-08-21:** `rocm-smi --showenergycounter` returns an accumulating microjoule counter and
      `librocm_smi64.so` exports `rsmi_dev_energy_count_get`. Verified ACCUMULATING rather than merely
      present — 308.0917 J over 5.072 s at idle, monotonic, LSB a constant **15.30 uJ/tick** across 23
      deltas, 60.75 W derived cross-checking 60.0 W from the independent `--showpower` field. **We appear to
      hold the BETTER instrument, not the missing one**, because a cumulative counter BYPASSES the
      sampling-window filtering that makes an averaged-power field untrustworthy. **TWO CAVEATS, recorded so
      it is not over-read:** rocm-smi CLI spawn cost floors sampling at ~200 ms, so fine-grained work must use
      the rsmi C API; and a 5 s IDLE window overlaps no workload, so per our own Observation Windows rule this
      is evidence about the **INSTRUMENT**, not about any run — agreement at idle is necessary but NOT
      sufficient, since filtering cannot bias a flat signal.
- [x] **RVP-PWR-3 — Ingest and verify `arXiv:2604.06056` (McDaniel et al., ORNL/HPE/AMD) — DONE
      2026-08-21, ingested as `intake-1251#record`.** It was indeed higher-value than anything else in that
      batch, because MI250X IS gfx90a. **All four preliminary figures CONFIRMED VERBATIM** against the
      paper's own LaTeXML rendering with section anchors, none overturned: the averaging window is
      undocumented (II-B), MI250X average power takes _"a few seconds to fully capture the transition from
      idle to TDP"_ (V-A2), _"aliasing begins below roughly 4 ms on MI250X"_ (V-A3), and the cumulative
      energy counter refreshes _"at 1 ms granularity"_ in **microjoules** (II-B). **The figures are now
      citeable.** Scope note on how it was read: two targeted passes over `arxiv.org/html/2604.06056v2` (the
      CURRENT version), not the PDF — which remains unread, and whose only unique content is Figure 5, where
      the confidence-window parameters are shown visually and **never stated numerically anywhere in the
      paper**. **UPDATE — THE PDF QUESTION IS NOW PROVABLY CLOSED, NOT MERELY DEFERRED.** A third pass
      targeting figure captions and appendix tables confirmed explicitly that numeric `t_d` / `t_r` / `t_f`
      values appear **nowhere in the document — not in figure axes, captions, tables or alt-text.** There is
      no version of this paper, in any format, that contains them. **Do not request the PDF; there is
      nothing in it we do not have.** **THREE THINGS THAT MUST TRAVEL WITH ANY CITATION:** (1) these authors used **NO external
      physical meter** — Cray PM is their highest reference and its accuracy is vendor-asserted from
      product-development testing, so unlike `intake-1238` this may never be cited as external validation of
      an ABSOLUTE watt figure (the relative lag/aliasing findings rest on the square-wave probe and are
      unaffected); (2) **MI250X is dual-die OAM, our MI210 is single-die** — treat the TIMING characteristics
      as expected-to-hold and worth confirming, and any absolute joule figure as not ours; (3) the workloads
      are dense HPC linear algebra with **zero ML or inference content** and no statement about single-GPU
      applicability, so the token-cadence phase-lock hazard remains unmeasured by either paper — that gap is
      ours to close in RVP-PWR-2, which this paper now hands us the instrument for.
- **[declined: ws58 2026-11-03 content-review: a protocol rule for energy claims we do not make]** **RVP-PWR-6 — Adopt the RUNTIME-VS-POWER DECOMPOSITION for every energy claim, which we currently do
      not do at all.** `intake-1251#record` separates energy savings caused by shortening time-to-solution
      from savings caused by lowering instantaneous power, and finds mixed precision _"primarily improves
      energy efficiency by shortening time-to-solution rather than dramatically reducing instantaneous
      power"_ (Frontier rocHPL 179.9 KJ → rocHPL-MxP 38.5 KJ, 79%). **This is directly applicable to every
      quantisation and kernel change we make** — a joules-per-token improvement that is entirely a
      tokens-per-second improvement is a different engineering fact from one that lowers draw, and they
      imply different next moves. The 79%/31%/27% numbers themselves are dense-linear-algebra results and
      must **never** be carried across to a decode workload.
- **[declined: ws58 2026-11-03 content-review: a protocol rule for energy claims we do not make]** **RVP-PWR-4 — Adopt the SC24 protocol shape for any energy claim we ever make.** Locked clocks,
      thermal warm-up, rise-time discard, a BOUNDED DECLARED WINDOW, median-of-N, idle-subtracted dynamic
      energy, and external ground truth where obtainable. Never quote the 35%/65% figure without its scope
      limit — and note it is an **error REDUCTION from a full protocol bundle**, not the magnitude of the
      duty-cycling bias (that mis-statement has been corrected in `intake-1222` in both places it appeared).

##### Recorded so it is not re-derived

- **FlashInfer-Bench introduces NO new metric.** `fast_p` is adopted verbatim from KernelBench
  (`intake-664#record`). Everything of value is in the **first conjunct** of `1(correct AND speedup > p)` — the
  correctness predicate, not the metric. Do not group it with SOL-ExecBench, whose Speed-of-Light score IS new.
- **The binding constraint on an agent authoring kernels is COMPILATION, not numerics.**
  `intake-1245#record` reports **30 of 32** agent failures as compile errors, 2 as runtime/numerical. Our
  C6 instrumentation is aimed at the numerics. On ROCm 6.2 / gfx90a the compile constraint is strictly worse
  than on CUDA. Budget the toolchain-feedback path accordingly.
- **Correctness-conditioned speedup rates are structurally survivorship-biased and must never rank arms.**
  Two independent 2026 benchmarks now exhibit it: CodegenBench reports `Fast_1@1 = 1.00` on LeetSunway for a
  model whose `Pass@1` is **0.06**, and self-diagnoses the cause; `intake-1227` flagged the same divergence.
  `Fast_1@1` is computed among correct candidates and can look strong despite low Pass@1. KernelBench
  `fast_p` counts tasks that are both correct and have speedup greater than threshold `p`, but divides by all `N` tasks;
  incorrect outputs remain in the denominator. It is a joint success-rate metric, not a correct-subset rate
  (`intake-664#01`).
- **ParEval-Repo: the HIP arm is DROPPED — question closed, do not re-ask.** Word-boundary grep of
  `arXiv:2506.20938v2` gives HIP 0 / ROCm 0 / gfx 0 and AMD 2 (both host CPUs); the full 254-path repo tree
  @ `50f7dd8a` contains zero `hip` paths. The OpenMP-Offload arm is **not vendor-neutral**: `target.json`
  builds it with `CUDA_ARCH=80 COMPILER=llvm`, declares a `cuda` dependency, and prompts for an NVIDIA GPU.
  Its functional oracle is one substring test (`if expected not in run_result.stdout`) and its residency
  check is `strace -e openat | grep -i nvidia`. **Do NOT adopt it as an evaluation gate**, and note the repo
  has **no root LICENSE** (a soft blocker on forking under our sourcing policy). The OpenMP-Offload-on-gfx90a
  question stays OPEN on its own merits — it is a ROCm toolchain capability
  (`clang -fopenmp --offload-arch=gfx90a`), which that benchmark neither demonstrates nor blocks.

#### Research Intake Update — 2026-08-21 (Stage-2b, intake-1276)

- **[declined: ws58 2026-11-03 content-review: its consumers (the GDN retrofit line G5/B4/B9 in model-architecture-readiness) were retired; nothing else on the stack needs torch+Triton on ROCm 6.2]** **G6 (Z first, then G) — settle the torch/Triton floor for ROCm 6.2 on gfx90a.**
      **This is the gating unknown for the entire GDN-retrofit line** (`log-linear-gated-deltanet-readiness.md`
      G5/B4) and it is cheap relative to what it blocks. It sharpens the still-unchecked runnable
      first task above ("install/pin `pytorch-triton-rocm` matched to ROCm 6.2 + verify gfx90a
      matmul", intake-760) with a concrete version question.
      **The zero-compute half is already half-answered and should be recorded before anything is
      installed:** our known-good isolated environment carries **Torch `2.5.1+rocm6.2` / HIP
      `6.2.41133` / Triton `3.1.0`** (see the 2026-08-11 provisioning row above), while
      `flash-linear-attention` 0.5.2 declares `rocm = ["torch>=2.7.0"]`. **Our verified stack sits
      below that floor.**
      **INVERTED 2026-08-22 — the floor argues the OPPOSITE of what this row first said, and the
      original framing was dangerous.** Being below fla's floor is not merely blocking: **it selects
      for the defective release.** fla **v0.4.2** declares `dependencies = ["torch", "transformers",
      "einops"]` — **no torch or triton floor whatsoever** — and it is the release carrying the
      silently non-deterministic `causal_conv1d` backward (fla #1156, since closed). fla **v0.5.2** —
      the **fixed** release — is the one that declares `torch>=2.7.0`. So a resolver asked for an fla
      compatible with Torch 2.5.1 walks straight onto the broken version.
      **Gate, rewritten:** (a) a torch + `pytorch-triton-rocm` build meeting `torch>=2.7.0` exists for
      ROCm 6.2 / gfx90a → install **fla >= 0.5.2** and G5 proceeds; or (b) it does not → **do NOT fall
      back to an older fla.** Raise the stack or do not install fla at all. The original branch (b) —
      "the question becomes whether fla runs correctly below its stated floors" — is withdrawn: below
      the floor the available release is the defective one, so that question resolves to "no" for the
      wrong reason. Dovetails with RVP-C5-3's `requirements_rocm.txt`, which must carry a hard
      `flash-linear-attention>=0.5.2` pin.
- [x] **(Z) fla issue #1156 — RECORDED AND CLOSED, 2026-08-22. Two claims in the original row are
      retracted; do not cite them.**
      The issue is **CLOSED** (`completed`, maintainer `zhiyuan1i`, 2026-08-22T09:55:42Z) after the
      reporter retracted his own headline. Corrected facts: the `ShortConvolution` backward defect is
      **fla 0.4.2 ONLY, fixed in 0.5.2** (his "reproduces on 0.5.2" run was importing 0.4.2 from
      site-packages; the clean re-test measures 5.5e-08 vs 2.0e-01), and it **never ran on two
      backends** — `causal_conv1d` was absent so the `'cuda'` backend silently fell back to `'triton'`.
      The differing numbers were **run-to-run non-determinism**: ten identical backward calls in one
      process returned ten different answers with absmax compounding 0.40 → 252.88 while the forward
      stayed bit-identical. Root cause is visible in source — v0.4.2's backward loads via
      `boundary_check` with **no `padding_option`**, leaving OOB lanes undefined; v0.5.2 rewrote every
      site to explicit `mask=` + `other=0.0`.
      **REATTRIBUTION — the original row gave this equal weight and it was wrong.** The
      `chunk_gated_delta_rule` 7.9e-07 / 1.8e-06 figures are **not third-party**: they are the bug
      reporter's own scoping aside in his own report. Genuine independent AMD corroboration for that
      kernel exists but lives in **fla #913** (gfx1151 / ROCm 7.13, inside a Qwen3.5-27B GDN LoRA
      fine-tune) — and #913 *also* records that kernel returning **silent NaN gradients on
      B200/sm_100** across fla 0.5.0/0.5.1/HEAD. Always cite it with its hardware scope.
      **Scope, now settled:** forward is clean at every shape tested including the faulting one, so
      **inference has zero exposure**; hardware is MI355X / gfx950 / ROCm 7.2 with **gfx90a and MI210
      appearing nowhere in the fla tracker**; and fla's only AMD CI workflow is `if: false` with no
      runner, so fla has **no AMD hardware coverage at all** — a sharper statement than the original
      row's "AMD CI is MI300/gfx942". Still a genuine sibling in *shape* to RVP-C2-6a/6b (a silent
      numerical defect on an accelerator), but fla/Triton rather than ggml/MMQ — keep the rows
      separate. The residual action is the version pin in G6 above.

#### Research Intake Update — 2026-08-23 (Stage-2b: upstream FA test coverage, Metal PRs, fla autotuner)

- [x] **Z10 (Z) — static read for the fp16-denorm bug class that #27413 fixed in Vulkan.** The bug <!-- completion: ✅ 2026-10-31 [belief: cc]; audit implementation ROOT 3d80bf84750c58a7916f1b0038a4f308483e223e; Git artifact: artifacts/compute/refactor-z10-static-20261031/source-audit.json; source audit: docs/engineering/z10-fp16-denorm-static-audit-20261031.md -->
      shape is a denormal quantization scale `qd` whose reciprocal `1/qd` overflows fp16.
      **Locators corrected 2026-08-23 — the plan's `fattn-vec.cuh:620-637` does not exist; the file
      is 611 lines at frozen v9 `0db32c06e3e5`.** The real surface is
      `ggml/src/ggml-cuda/fattn-common.cuh:332-373` (`quantize_q8_1_to_shared`) and its **single**
      call site in the whole tree, `ggml/src/ggml-cuda/fattn-vec.cuh:181`.
      **One fact the read already yields, recorded so nobody re-derives it:** that call site
      instantiates `Tds = float2`, so on our path `d` and `sum` are stored as **fp32, not fp16** —
      the `std::is_same<Tds, half2>` branch at `:367-368` is **dead code in this tree**. `d` itself
      is `amax / 127` (`:354`) and is guarded by `if (d != 0.0f)` at `:358`, so the exact-zero case
      is handled; what remains to check is the **denormal-but-nonzero** case and every downstream
      site that takes a reciprocal of a stored scale. Complete that sweep before deciding.
      **Escalates to G10 only if the static read is inconclusive.** Zero compute; runnable now.

  <!-- z10-source-completion:start -->

  - ✅ 2026-10-31 [belief: cc] Source-read completion: ROOT `3d80bf84750c58a7916f1b0038a4f308483e223e`; [named producer/five-consumer audit](../../docs/engineering/z10-fp16-denorm-static-audit-20261031.md) and [25-file source/hash manifest](../../artifacts/compute/refactor-z10-static-20261031/source-audit.json). The exact fp16 reciprocal mechanism is absent in the audited CUDA/HIP path; the conditional Vulkan source retains it. Arbitrary fp32-subnormal, compiler/compiled-image, numerical, runtime and residency behavior remain unassessed. G10 measurement parents stay OPEN. The original source-only check was retained, not rerun.

  <!-- z10-source-completion:end -->
- [x] **G10 (G; the import half is Z) — import and run the 20 new backend-agnostic `FLASH_ATTN_EXT`
      test cases** from `tests/test-backend-ops.cpp` @ `70aff2525`: 6 q8_0-KV eval cases including
      **kv=16384**, the kv=1025 pad/sinks/ALiBi/softcap case, and 3 MLA cases. Upstream concedes its
      own pre-existing matrix "stops at kv=1024, blind to long-context FA bugs", and this import
      immediately caught a real Vulkan wrong-output bug there.
      **Import is Z** — prepare the patch against `llama.cpp-experimental` branched from the
      *current* production tip, per the four-step workflow. **Never against frozen v9.** **Running
      is G**, on both the CPU and ROCm0 backends.
      **Gate:** any **FAIL at kv >= 10000 on either backend** converts coverage hygiene into an
      active correctness defect and takes priority over everything else in section C. A clean pass
      closes the row as a **durable negative for those shapes only** — it says nothing about shapes
      outside the imported set and must never be quoted as "FA is correct at long context".
      **Bounded by Z10:** if Z10 finds the denorm class present, run G10 with that hypothesis named
      rather than as an undirected sweep. [intake-1284#record]
      **INTERIM 2026-10-23, GPU leg (session 3c4ca599; job `inf48-g10-gpu`, ended rc 5 at 22:30Z; `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-48-G10/out/G10_gpu.json`).**
      Branch `experimental/g10-fa-import-20261023` @ `933666a9d` (v10 `ffc1bac82` + test-only diff), ROCm0 = MI210 gfx90a, 25 cases one process each.
      The CPU leg is CLEAN_SCOPED (25/25, default and `GGML_FA_SPLIT_KV=0`). **ROCm0: ACTIVE_DEFECT by the gate, FAIL=1, NOT_SUPPORTED=1, OK=23, and only 8/25 residency-proven.**
      - **Case 25 FAILs, marginally, with residency PROVEN (6 qualifying VRAM samples):** `FLASH_ATTN_EXT hsk=256 hsv=256 nh=2 nr23=[16,1] kv=20000 nb=512`, F16 K/V, prec=f32:
        ERR 5.02475e-4 > 5e-4 (0.5% over the tolerance). Cases 12, 13 (kv=16384, F16, nb=512) and 24 (kv=10000, F16, nb=512) pass, also with proven residency.
        **Hypothesis (not yet discriminated, so NOT a defect record and NOT a clean pass):** the reference is the CPU backend's `use_ref` vec path, and in v10 that path always accumulates an
        F16 V in an FP16 buffer (`ggml_compute_forward_flash_attn_ext_f16_one_chunk`, `ops.cpp:8910/8959/9000` at `933666a9d`, no knob). KP-1 (`docs/reference/kernel-manifests/llama-v11-manifest.md`;
        V11-086) puts that oracle error at ~2.1e-8*kv, i.e. ~4.2e-4 at kv=20000, the size of the observed number. Only the F16-V cases see it (10-13, 20, 21, 24, 25).
        **The knob first proposed for the check does not exist on this store:** `GGML_FA_VKQ_F32` is not compiled into `gpu-20261023-933666a9d-g10fa` (strings: `GGML_FA_SPLIT_KV` only; the VKQ knobs are in
        the champion line, `141e4bcf5`, which has no g10 case set), and `GGML_FA_SPLIT_KV` is guarded by `!use_ref`, so it cannot move the reference at nb=512. The decisive arm is an FP32 oracle with
        v10 GPU code: `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-48-G10/g10_fp32ref_oracle.patch` (sha256 `40e029e7...`), built by the job into `gpu-20261023-933666a9d-g10fp32ref`.
      - **Case 7 (`576/512` q8_0 MLA, kv=113, nb=1): NOT_SUPPORTED on ROCm0** (`supports_op` declines it, `[ROCm0]` in the log). Not a failure; no kv >= 10000 MLA shape exists in the import (cases 8, 9 are supported and pass).
      - **Residency NOT proven for 17 cases (1-9, 14-21):** they finish in ~1 s, so the 0.5 s VRAM sampler saw < 2 qualifying samples; their OK results are NOT evidence of a GPU run (the job refused, rc 5, and withheld COMPLETE_GPU).
        Fix landed in `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-48-G10/g10_gpu_job.sh` (backup `.bak-preresidencyfix`): sampler 0.1 s, `--repeat-suite R --suite-seed S` per case (R=100 for the cheap shapes, retried x10 up to 3 attempts), and a verdict is
        resume-skipped only when its residency is proven. **The criterion is unchanged** (own-PID KFD entry, `libggml-hip` mapped, >= 2 samples with own-PID VRAM >= 16 MiB). NOT_SUPPORTED is accepted only as a proven
        no-op (ROCm0 banner in the log + `libggml-hip` mapped); it never becomes an OK.
      - [x] **G10-D (discriminate case 25).** Run `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-48-G10/g10_case25_job.sh` (row and launcher drafted in `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-48-G10/CASE25_ROW.md`, not armed): arms A v10 as-is, C FP32-oracle store (decisive), paired seeded P1/P2,
        B `GGML_FA_SPLIT_KV=0` negative control, residency proven per arm. A fails and C passes all = ORACLE_CULPRIT (KP-1 class, record, not a GPU defect); C fails = real ROCm0 FA precision issue at kv=20000 nb=512.
        Not feasible and skipped: a direct GPU-vs-FP32 number from `cpu-20261023-df3e0f8cf-fp32oracle-c` (the harness compares backends inside one process; that store is CPU-only; ERR prints only above tolerance).
        - *(2026-10-24, 3c4ca599.)* **DONE: ORACLE_CULPRIT.** Job `inf48-g10-case25` (granted 00:13Z, MI210, residency proven both arms): **A v10 as-is (FP16 CPU `use_ref` reference) 127/128 reps FAIL** (ERR 5.15e-4..5.28e-4 vs 5e-4); **C FP32-oracle store `gpu-20261023-933666a9d-g10fp32ref`, same GPU kernel, 22/22 OK.** The GPU FA kernel is within tolerance at kv=20000 nb=512; the marginal FAIL is the FP16 reference's own error (the KP-1 class). Not a GPU defect. B (negative control) and the second C attempt were not needed (C's retry timed out at 417 s). Verdict file `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-48-G10/out/case25/VERDICT_CASE25.txt`. The job never concluded on its own: `grep -e` on the paren-bearing case string failed, so `case_lines` was empty and it kept escalating reps; fixed (`grep -F` + `${nlines:-0}`, backup `.bak-pre-grepF-20261024`).
      - [x] **G10-R (residency re-run).** Re-arm `inf48-g10-gpu` (launcher `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-48-G10/launcher_gpu.cmd`) with the fixed job so cases 1-9 and 14-21 get proven residency, then re-read `out/G10_gpu.json`: the G10 row closes only
        with every case proven or a proven-no-op NOT_SUPPORTED, and case 25 resolved by G10-D.
        - *(2026-10-24, 3c4ca599.)* **DONE.** `inf48-g10-gpu` re-run 00:36-00:40Z with the fixed job, `out/G10_gpu.json` rocm0: **24/25 residency PROVEN, 23 OK**, case 7 NOT_SUPPORTED as a **proven no-op** (`notsup_noop=true`: ROCm0 banner, libggml-hip mapped, 0 VRAM), case 25 FAIL = the ORACLE_CULPRIT above. Every closing criterion met.
      **G10 CLOSED 2026-10-24 (3c4ca599): durable negative for the 25 imported shapes ONLY, on CPU (25/25, default and `GGML_FA_SPLIT_KV=0`) and ROCm0 (23 OK proven, MLA 576/512 not supported, case 25 an FP16-reference artifact).** Not a statement that FA is correct at long context outside these shapes. Consequence for the harness: on v10 any `test-backend-ops` FA comparison with F16 V at kv >= ~20000 can FAIL from the CPU reference alone, so a long-kv FAIL there needs the FP32-oracle arm before it is read as a backend defect (the champion line has the VKQ knobs for this, V11-086).
      - 2026-10-28: G10 GPU leg, FA_EXT kv >= 10000 FAIL vs predeclared rule 'any single FAIL at NMSE 5e-4' → correctness-only: case 25 FAIL on A (FP16 CPU reference) 127/128 reps, but C (FP32-oracle) 22/22 OK on the same GPU kernel, so ORACLE_CULPRIT, not a GPU defect; 24/25 residency PROVEN, case 7 proven no-op NOT_SUPPORTED; CPU 25/25 OK both arms. Scope: these 25 shapes only. Filed 2026-10-24 above; no new box needed. Evidence: /mnt/raid0/llm/tmp/roi-prep-20261023/INF-48-G10/out/G10_gpu.json (+ G10_cpu.json). [belief: cc]
- [x] **Z14 (Z) — DONE 2026-08-23: filed as [fla-org/flash-linear-attention#1163](https://github.com/fla-org/flash-linear-attention/issues/1163)**
      (operator-approved; posted under the operator's account). Read and pinned at HEAD
      `bc3b101dcb713ddc5bd8924b66754eb68b5ccf89`, with every claim re-verified against that revision
      before posting rather than carried from the dive. **One clause of the row below was WRONG and
      was corrected before it went out:** `STATIC_WARPS` is *not* "defined and never used anywhere" —
      it is used in five other modules (`fused_kl_div.py`, `fused_linear_cross_entropy.py`, and three
      `backends/triton_ascend/` files). It is unreferenced only *within* `conv/triton/kernels.py`, and
      the report says exactly that. The report also states plainly that we have NOT run it (no `fla`
      install on gfx90a / ROCm 6.2, below the declared `torch>=2.7.0` floor), so it is filed as a
      code-reading report, and it names the #1156 hypothesis as **falsified** rather than merely
      unproven. Original row text retained below for provenance.
      <br>Original: file the unguarded AMD warp list in fla's conv-backward autotuner UPSTREAM, as a
      separate latent-inconsistency report. In fla's `causal_conv1d` kernels, `kernels.py:16`
      defines `NUM_WARPS_AUTOTUNE` AMD-aware; the **forward** and **update** kernels consume it, but
      the **backward** kernel at `:152` hardcodes `[4, 8, 16, 32]`. `IS_AMD` is
      **architecture-blind**, so 2048 threads/block is offered on every CDNA part regardless of
      whether it can be occupied, and `STATIC_WARPS` is defined and never used anywhere.
      **This is NOT the cause of #1156** — that was the missing `padding_option` on `boundary_check`
      loads, fixed in 0.5.2 — and the report must say so in its first line or it will be closed as a
      duplicate of a retracted issue. Pin the revision inspected in the report body. Zero compute,
      no local install, and no AMD hardware needed to file it. [intake-1283#record]

#### Research Intake Update — 2026-09-26 (ATT MFMA-efficiency metric on gfx90a; intake-1823)

- [x] **INF48-LIVE-6 GPU-AK-SIGNALS - counter/ISA/race/equivalence signals for the GPU AK lane (RVP-ATT-1, RVP-CTR-1, RVP-RACE-1/2, RVP-EQV-1, C5-ISA-1/2).** Recent (Oct-Nov) intake-derived rows, kept for their own sequencing; each child is a pointer to the full text at b3bd883d3. [no-belief: new consolidated box] Live row race-eqv-gpu-r9-20261111 (done) (RVP-RACE-1/EQV-1): model: none (test-backend-ops on the MI210 over the `MUTANT-race-eqv-r3-20261109-36f024341` build store, source `36f024341`); stop-on-answer when the slimmed one-seed plan completes and RACE-1/EQV-1 are decided; stop-on-futility on an unusable or nondeterministic BASELINE or a residency failure; gate-class = futility-only (gate text in the RVP-EQV-1 r4/r5 amendments below). ✅ 2026-11-17 children done or folded: RVP-ATT-1, RVP-RACE-1, RVP-EQV-1, INF48-RACE-2-FIXTURES done; RVP-CTR-1 (capture PASS, planner A/B open), C5-ISA-1, C5-ISA-2 and RVP-RACE-2 executor folded to autokernel-akx-program.md (track autokernel-all-devices-all-dimensions); FA bugs folded to kernel-champion-and-promotion.md. [no-belief: hygiene]
  - RVP-ATT-1 ✅ 2026-11-16 desk check: obtainable on gfx90a/ROCm 6.2 via rocprofv2 --plugin att only (rocprofv3 6.2 has no thread trace); att_mfma_efficiency.py (research 5335238fd) on the decoded canary: 256 MFMA cycles / 319.7 loop cycles = 0.80. MFMA pass table beyond 16x16x16 not source-verified. [no-belief: desk check + offline replay of canary csv]
  - Notes 2026-11-16: RVP-CTR-1 partial — code research 5335238fd, capture row ak-gpu-signals-ctr-20261116 published (smoke-queued), planner A/B after. C5-ISA-1 partial — isa_claims.py gate, call-site wiring open (1–2 d). C5-ISA-2 partial — host half gcn_gym.py, GPU half waits on RACE-2 launch-capture shim. 2026-11-17: RVP-CTR-1 capture row ak-gpu-signals-ctr-20261116-r2 PASS 10/10 metrics; the planner A/B is still not run. RVP-CTR-1, C5-ISA-1, C5-ISA-2 and the RVP-RACE-2 executor measurement re-homed 2026-11-17 to [autokernel-akx-program.md](autokernel-akx-program.md) (INF48-FOLD-PLAN). [moved: handoffs/active/autokernel-akx-program.md] [no-belief: hygiene]
  - Notes 2026-11-16 (INF48-LIVE-6): on gfx90a with ROCWMMA ON (C10 configure, rocWMMA 1.5), WMMA takes every FA shape with kv%256==0 except hs 192/320/512/576 before MMA is considered, so race-eqv r9's FA suites mostly exercised WMMA, not MMA. Several FA kernel variants compile as NO_DEVICE_CODE stubs on gfx90a here (WMMA softcap D∉{128,256}; TILE ncols2>1; VEC/MMA softcap outside their D sets). [no-belief: code reading + row logs]
  - [x] **INF48-RACE-EQV-R3** race-eqv-gpu-r3 smoke failed 21:08Z on the residency check (PIPE-EVE-RESIDENCY-FALSE-FAIL); the r3 mutant build completed. Republish once resolved. [no-belief: tooling-repair] ✅ 2026-11-12 rc=0 pass, row race-eqv-gpu-r9-20261111 (r5..r8 instrument failures fixed: research 7e481ef5f, 4d441c131): RACE-1 gate_sees_all_tested_races (5/5 race mutants caught, unmutated 1/1); EQV-1 caught all except E1-FA-RESCALE-SKIP -> equivalence milestone opened. Gate amendments r6/r8/r9 ratified by operator 2026-11-12 (decision tool). Evidence /mnt/raid0/llm/tmp/race-eqv-gpu-r9-20261111/out/RESULT.json. [no-belief: row verdict filed by agent]
  - [x] **INF48-RACE-2-FIXTURES** RVP-RACE-2 can start: race-eqv r9 fixed the fixture set (R1-FA-MMA-SOFTMAX, R1-MMQ-TILE-LOAD, R1-MMVQ-LDSDMA, R1-MMVQ-TMP-NW4, R1-MMVQ-TMP-NW8), all caught by the current gate; RACE-2 measures the gfx90a race/deadlock executor against these. [inference] model: none (op-level rocprofv3 kernel trace over test-backend-ops); row inf48-race2-fixtures-20261116, published 2026-11-16, smoke-queued; stop-on-answer when the executor verdict on the five fixtures is written; stop-on-futility on an unusable baseline or a residency failure. [no-belief: new box] ✅ 2026-11-16 pass, row inf48-race2-fixtures-20261116-r2: FIXTURES_READY 7/7 (5 race mutants with s_barrier drop dispatched + matching geometry; 2 ISA-only via QPF2 trace), bundle sha 3b4e309f; join fix research 3c20307dc [no-belief: row verdict filed by agent]
  - [x] **INF48-EQV-FA-RESCALE** Equivalence milestone for the FA online-softmax rescale sub-class: E1-FA-RESCALE-SKIP survived every suite in race-eqv r9 (FA, FA+VT/HD/ED). Add a case family that exercises the rescale (long KV with rising running max across tiles) and re-measure the mutant; stop-on-answer when the mutant is caught or proven output-equivalent. [inference] model: none (op-level test-backend-ops FLASH_ATTN_EXT, branch llama.cpp-experimental-inf48-eqv-fa-rescale-20261116 @ 9b776dfdf); row inf48-eqv-fa-rescale-gpu-20261116. [no-belief: new box] ✅ 2026-11-16 CAUGHT: row inf48-eqv-fa-rescale-gpu-20261116-r2 (branch llama.cpp-experimental-inf48-eqv-fa-rescale-20261116 @ c81c2f546, ROCWMMA off) rescored offline with the fixed failure-line parser (/mnt/raid0/llm/tmp/inf48-eqv-fa-rescale-gpu-20261116-r3/RESCORE-r2.json): KEEP(CAUGHT) — 6 mutant-only MMA failures (cases 13 alibi hs128 ERR 0.199, 27 softcap hs256 0.037, 28 alibi hs256 0.229, 61 ramp hs128 kv1000 0.134, 62 spike hs128 kv1000 29.2, 67 ramp hs128 kv4096 0.035); BASE deterministic, 0 rising-max BASE fails, no firstmax control fail. The filed r2 verdict reads FUTILITY_INSTRUMENT because the original parser dropped failure lines; the rescore supersedes it. Note: the mutant survives every plain/step rising-max MMA case at kv=1024 (cases 1-3,5,6,8-10,12,14,47-50,59,69) — likely a different MMA instance/schedule at kv%256==0; unverified. [belief: cc] [receipt-ack: inf48-eqv-fa-rescale-gpu-20261116-r2 INCONCLUSIVE — original parser dropped failure lines; offline rescore of the same logs (RESCORE-r2.json) gives KEEP(CAUGHT)]
  - INF48-FA-ALLMASK-NAN and INF48-FA-HS256-MMA-PRECISION moved 2026-11-17 to [kernel-champion-and-promotion.md](kernel-champion-and-promotion.md) as open kernel-fix boxes (INF-48 fold plan). [moved: handoffs/active/kernel-champion-and-promotion.md]
  - 2026-11-10 RESULT (autokernel; row `race-tsan-v10-20261109`): **BUILD_FAIL**, no TSAN op ran. clang `-Wenum-constexpr-conversion` errors in `ggml/src/ggml-cpu/iqk/iqk_mul_mat.cpp:320` onward (e.g. integer 145 outside [0, 63] for `ggml_type`), so the TSAN build of the v10 tree never linked. The race signal stays unmeasured; the box stays open. Evidence `/mnt/raid0/llm/tmp/race-tsan-v10-20261109/out/RESULT.json`, `out/logs/build.log`. [no-belief: build failure, no measurement]
  - *(folded into INF48-LIVE-6; full text at b3bd883d3:1698)* **(no title)**
  - 2026-11-10: race-tsan-v10-20261109 BUILD_FAIL: clang 18.0.0 (ROCm 6.2) hard-errors -Wenum-constexpr-conversion on iqk_ext_types.h ((ggml_type)145) case labels in iqk_mul_mat.cpp:320+. Separately, TSAN aborts about 50% of runs under ASLR ("unexpected memory mapping", rc 66). Republished as race-tsan-v10-20261110-r2 (out-of-tree build): -Wno-enum-constexpr-conversion plus setarch -R. The smoke compiled the failing iqk object and passed; the verdict waits for the grant. [no-belief: build fix and republish only; no race measurement]
  - [x] **RVP-RACE-1 r3 — TSAN CPU leg, fix verification (row race-tsan-r3-20261110).** r2 (v10 ffc1bac82) found 3 benign lazy-getenv flag races, added in v10 by INF-70 and unchanged in C10 7f1bd044b: `ggml_cpu_rowexact_n` ggml-cpu.c:1617/1620, `ggml_mmid_slab_enabled` ggml-cpu.c:1627/1629, `ggml_vec_q8k_flag` arch/x86/quants.c:597/600 (9 reports; `pthread_create` frames were thread-creation stacks, not race sites; MUL_MAT_ID rc 66 = TSAN report exit, op 815/815 OK). r2 timeouts came from v10 test-backend-ops spawning 192 threads under TSAN; r2 also never ran iqk (GGML_IQK unset). Fix 65c7ebf9b on `llama.cpp-experimental-c10-tsan-fix-20261110` (relaxed atomics; `iqk_dequant_enabled` becomes a magic static), not pushed. r3 runs 24 cells {v10, C10+fix} × {iqk off, iqk on} × {MUL_MAT_ID, MUL_MAT, FLASH_ATTN_EXT, SOFT_MAX, ADD, MUL}, thread-capped. Model: none (op-level CPU test-backend-ops). Stop: one pass, verdict in RESULT.json; futility on a fix build or provenance failure. On FIX_CONFIRMED, fold 65c7ebf9b into C11. ✅ 2026-11-10 — r4 race-tsan-r4-20261110 FIX_CONFIRMED: v10 13 TSAN reports at 4 benign lazy-init sites (ggml_cpu_rowexact_n, ggml_mmid_slab_enabled, quantize_row_q8_K, iqk_dequant_enabled; v10 cells from r3); C10+fix b1e825e7a (65c7ebf9b relaxed atomics + clang/OpenMP structured-binding portability) 0 reports across all 24 cells (iqk off/on × 6 ops), no new sites. C11 fold candidate; numeric identity row tsanfix-numeric-cpu-r2-20261110 filed PASS (answer=PASS, rc0, 2026-11-10): the relaxed-atomics TSAN fix changes no computed token on Q38FN and dense Qwen3-8B, default and per-knob (r1 had been inconclusive on a truncated dense GGUF). [no-belief: row verdict filed by autokernel]
- [x] **RVP-ATT-CANARY-R4 — validate the repaired trace launcher on the real GPU.** Private ✅ 2026-11-16 pass, row rvp-att-canary-r4g-20261116: PARTIAL_OK (self-hold, native_exit 143, group dead) + FULL_OK (rc 0, raw .att); plumbing canary only, ungraded [no-belief: row verdict filed by agent]
  - 2026-11-09 (pipeline-mgmt, row `codex-att-r4e-20261109`, filed pass): plumbing canary PASS: native exit 0, nonempty raw `.att` (se0/se4, 17816 B each), VRAM residency 212 MB to 4.57 GB sampled, teardown process-group-dead, mfma_peak 100.05 TFLOPS; ungraded raw capture (second attempt dir under `codex-att-r4e-20261109/out/attempts/`). The rc75 partial path was not exercised in this attempt, so the box stays open. Row rvp-att-canary-r4f-20261116 (supersedes codex-att-r4e-20261109, which passed plumbing; r4f adds the rc75 partial path) published 2026-11-16, smoke-queued. [no-belief: partial status note]
  Row `codex-att-r4-20261109` carries this forward on filler_run15. model: none, `mfma_peak` microbenchmark (no LLM weights); quant_build: rocprofv2 ATT trace launcher on the MI210, not a kernel build. stop-on-answer when one real run writes a nonempty raw trace with VRAM residency and clean partial/cleanup; stop-on-futility on a launcher or trace-writer failure on the real GPU (one attempt, repair before any new row); gate-class = futility-only.
  `/mnt/raid0/llm/tmp/codex-att-r4-20261028` now checks the correct GPU device path, requires the full
  `mi210_0,72-95,184-191` grant, and uses a private engine retaining live admission while omitting
  the synthetic-proof requirement prohibited by the current diagnostic workflow. Source checks and
  in-memory admission tests pass; no post-fix real smoke or trace result exists. Once the GPU is free,
  run the same launcher under the R7 smoke slot, verify the real trace writer, residency, rc75 partial
  and cleanup, then publish the row only after full-q3 scheduler admission is verified. This is a
  plumbing canary, not an MFMA-efficiency result. [no-belief: no measurement yet]
  - *(2026-11-09 schedule readiness, inf48-triage)* Launcher exists, outside git: `/mnt/raid0/llm/tmp/codex-att-r4-20261028/{launch.sh,job.sh,filler_run12.sh,PREDECLARATION.json}`; MFMA probe build `refactor-01a16fc3/rvp-att-mfma-probe-ready` is COMPLETE. *(superseded 2026-11-11: r4e became the rowflow row and passed; the list below is historical)* Row rvp-att-canary-r4f-20261116 (supersedes codex-att-r4e-20261109, which passed plumbing; r4f adds the rc75 partial path) published 2026-11-16, smoke-queued. [no-belief: status note]


- [x] **RVP-ROLLBACK-SEED-SOURCE — repair only rollback-case integer initialization on a fresh experimental child of frozen production.** Exact private candidate`8e09a5e003f61b7ce7d58088f2f34595118068b4` parent`ffc1bac82eeca6f9099e1ccd9ba49703c460a115` consumes the existing per-tensor suite RNG and preserves unseeded fallback/float initialization. MAIN LOW source review is complete; finish prospective actual native CPU initializer/reference controls before source publication. Full GPU/production regressions, promotion and accepted live seeded event remain parent requirements; no production-tree change.

✅ 2026-10-07 RVP-ROLLBACK-SEED-SOURCE: [MAIN actual original3/3 and experimental source publication](../../artifacts/ni08/rvp-rollback-success-acceptance-20261007/README.md). Actual64 raw initializer captures/CPU-reference replay; no production/GPU regression, live event, performance or promotion warrant.


##### Prospective bounded C-pointer lexical correction — 2026-10-07


Exact candidate/recipe preparation remains under /mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/; GPU two-sided timing proposal is still unaccepted and no runtime/kernel work is authorized by this child. Descendantb2b44 retains all9 original controls and strengthens ordinary/escaped/raw literal/block-comment negatives plus active C/C++ keys after quoted text. This is finite added-line matching; hunk-truncated contexts are not a complete parser guarantee.

- *(2026-10-31, generation prerequisite READY.)* `codex3-pareval120-k20-gen-20261031` binds existing SC45 enrollment `0e2ee6b2b29462c295d67aa19de3405763291d46`; manifest SHA-256 `c1c0f187c42a4f7694266096df8640b74ffac04d219b387f651302965d01062b`. Its original 120 prompts × 20 samples use independently seeded single-choice requests, a documented grouping change from the upstream n=20 call. A public 0.6B one-request engineering control and active STOP/drain qualified the path; the full 27B 2400-output cohort remains unrun at publication. This is generation only: contained scoring, local sequential baseline, quiet-host thread sweep, pass@k and efficiency@k remain open. [Bounded metadata](../../artifacts/compute/codex3-ernie-pareval-ready-20261031/SNAPSHOT.sha256). [no-belief: preparation only]

##### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

Operator-approved 2026-10-31 (plan revision 2, `research/intake-stage3-plan-2026-10-31-ws58.md`, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`; relayed by the ws58 coordinator; budget approved: about 13 MI210-hours for the drafter pilot, 6-9 engineer-weeks for the race checker, the 95.5 GB ThinkingCap download; D1 confirmed: in-weights calculator declined, GPU reason recorded on intake-2550/2574; D2 approved: scratch upstream builds are measurement instruments only). Trigger records below are prose with no checkbox until a reviewed session confirms their condition.

  - *(folded into INF48-LIVE-6; full text at b3bd883d3:1730)* **RVP-CTR-1 — Counter-grounded planner signals for the GPU AK lane (intake-2556#record).**
  - *(folded into INF48-LIVE-6; full text at b3bd883d3:1731)* **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** ✅ 2026-11-12 race-eqv-gpu-r9-20261111: gate_sees_all_tested_races, 5/5 barrier-drop mutants caught, unmutated 1/1 (single seed, r5 amendment); TSAN FIX_CONFIRMED [no-belief: row verdict filed by agent]
  - *(folded into INF48-LIVE-6; full text at b3bd883d3:1732)* **RVP-RACE-2 — gfx90a AMDGCN race/deadlock executor as the GPU race_detector_id (intake-2570#record, intake-2557#record).**
  - *(folded into INF48-LIVE-6; full text at b3bd883d3:1733)* **RVP-EQV-1 — Decide the equivalence-checker port by measured miss rate, quant kernels declined on coverage (intake-2570#record, intake-2557#record).** ✅ 2026-11-12 race-eqv r9: all mutants caught except E1-FA-RESCALE-SKIP → INF48-EQV-FA-RESCALE [no-belief: row verdict filed by agent]
    - *(2026-11-10, autokernel.)* Row `race-eqv-gpu-r3-20261109` ran 07:12-07:17Z and filed `INVALID_BASELINE_FAILS`: no RACE-1/EQV-1 conclusion. Cause (diagnosed from `/mnt/raid0/llm/tmp/race-eqv-gpu-r3-20261109/out/logs/current.log`): the BASELINE Q suite's 312 non-passes (2295/2607) are genuine test-backend-ops FAILs (MUL_MAT/MUL_MAT_ID, low-bit types, n<=5), not skips or a crash; the job's fail regex `\bFAIL\b` is blind to the ANSI colour code before FAIL so it recorded 0 fail lines. The `MUTANT-...` store name is not a wiring bug (BASELINE is its unmutated variant, source sha and libggml hash verified). Root cause: case set `served_shape_lowbit_v1` bounds are CPU-anchor NMSE x3 floored at 1e-8, unattainable for ROCm (GPU NMSE ~2.5e-5). r4 needs (a) ANSI-stripped fail parsing and (b) GPU-baseline-calibrated bounds or new-fail-vs-baseline semantics (a pre-registered gate change); not published. Box stays open. [no-belief: invalid run, does not measure the question]
    - *(2026-11-10, autokernel — pre-registered gate amendment for r4, before any r4 run.)* **Operator decision 2026-11-10 (relayed to autokernel): the GPU gate becomes new-fail-vs-baseline.** Model/identity: no model; `test-backend-ops` on the MI210 (ROCm0) over the `MUTANT-race-eqv-r3-20261109-36f024341` store (BASELINE variant = unmutated, source `36f024341`, libggml-hip SHA-256 checked against each `BUILD-OK.json`), case set `served_shape_lowbit_v1` (`served_shape_cases.py`) for Q/QPF, row `race-eqv-gpu-r4-20261110`. Question: does a race or algebraic mutant introduce failures absent from the baseline? Gate: a mutant/candidate run fails only on cases the BASELINE run of the same suite, same seed and same binary family passed (multiset difference of failed case keys, `max_nmse` stripped from the key), or if it crashes or runs a different case count; ROCm numeric error against the CPU-anchor x3 bounds (NMSE ~2.5e-5) cancels out. Parsing strips ANSI colour codes before matching FAIL (the r3 `\bFAIL\b` regex saw 0 of 312 failures) and fails closed when the failed-key count does not reconcile with `total - passed`. EQV max-abs band (4x the BASELINE 5-seed max) unchanged. Stop-on-answer: plan complete, RACE-1 and EQV-1 decided from the paired verdicts. Stop-on-futility: a BASELINE run that crashes or truncates, parses fewer than 50 cases, does not reconcile, or passes under 50% of its cases ends the row `INVALID_BASELINE_UNUSABLE`; a BASELINE repeat at seed 1000 per suite whose fail set differs from run 0 ends it `INVALID_BASELINE_NONDETERMINISTIC`; residency/library failure as before. Code: research `scripts/kernel_rnd/autokernel/loop/gpu_newfail_gate.py`; `test_gpu_newfail_gate.py` re-scores r3's BASELINE|Q|0 log (2295/2607, 312 fail keys reconciled, usable baseline, 0 new-fail vs itself). [no-belief: gate amendment]
    - *(2026-11-10, autokernel.)* Row `race-eqv-gpu-r4-20261110` was stopped by operator decision on 2026-11-10: it held the GPU exclusively at ~0% use. 5 BASELINE Q runs were recorded with an identical 312-key fail set, so the baseline is deterministic. The row is being republished slimmed as r5. [no-belief: row stop note]
    - *(2026-11-10, autokernel — pre-registered seed-count amendment for r5, before any r5 mutant run.)* **Operator decision 2026-11-10: r4 (`race-eqv-gpu-r4-20261110`) stopped** (it held the MI210 exclusively at ~0% GPU use: test-backend-ops spends nearly all its time in the single-threaded CPU reference; ~5 min/run x 405 planned runs, far past its 6 h window, five GPU rows blocked). Recorded before the stop: BASELINE Q seeds 1000-1005, all rc=1 with the identical 312-key fail set. Row `race-eqv-gpu-r5-20261110` slims the plan; the gate (new-fail vs BASELINE of the same suite and seed, ANSI-stripped parsing, reconciliation, futility rules) is unchanged. Seed counts change: BASELINE one run per suite at seed 1000 (14 suites; Q reuses r4's recorded BASELINE|Q|0), BASELINE-REPEAT at seed 1000 once per Q/QPF/FA/GDN/MMVF (unchanged), coverage pass per suite (unchanged), every control and mutant ONE run per suite at seed 1000 (was 20 per race suite, 5 per EQV suite / coverage control) = 60 new GPU runs. Decision rules re-stated for one seed: RVP-RACE-1 — a mutant with a structural barrier drop and >1 wave that passes its single run is a measured race miss (gate_blind_to_races if any); a mutant caught on its one run counts as seen ON ONE SEED ONLY, so `gate_sees_all_tested_races` is downgraded to a single-seed claim and a per-seed miss rate is not measured. RVP-EQV-1 — open the equivalence milestone for a subclass if a non-control mutant survives every gate at seed 1000; close with the catch table if none; the EQV max-abs band becomes 4x the BASELINE seed-1000 max. Coverage controls exclude a mutant when their single run passes. `-j` stays 1: `-j N` disarms the FA-asm / iqk path witnesses (process-wide counters), interleaves worker output in the log the gate parses, and runs kernels of several cases concurrently, which changes the race environment RVP-RACE-1 measures. Stop-on-answer: plan complete. Stop-on-futility: unchanged. [no-belief: gate amendment]
    - *(2026-11-11, autokernel evening.)* race-eqv instrument chain, no RACE-1/EQV-1 verdict yet. r6 superseded by r7 (filed supersede). r7 (`race-eqv-gpu-r7-20261111`) filed inconclusive: BASELINE GDN+VT 23/82, fail count unparsed (`AK_VALUE_V1 transforms=...` lines), negate transform out of domain. r8 filed inconclusive: GDN+HD baseline 18/82 (64 fail keys), the negate exemption covered GDN+VT only. Fix chain: research `7e481ef5f` (harness saved) then `4d441c131` (generic all-suite GDN op-domain exemption, derived-suite exclusion, offline baseline replay test validated on stored logs). r9 (`race-eqv-gpu-r9-20261111`) is NOT yet published: no `ready/` entry exists as of 20:50Z, so it is not queued; publish it (shape gpu) before reporting it queued. Correctness-only GPU rows (this one, B3) were reshaped from gpu-q3 to gpu so they can backfill while q3 is busy. [no-belief: tooling-repair]
- [x] **ROCPROF-ATT-ADAPTER-1** [non-inference] Write an adapter from the rocprofv2 ATT decoded CSV (Line, Instruction, Hitcount, Cycles) to the amd/skills stall classes (VMEM-load, VMEM-wait, LDS/SMEM-wait, barrier, MFMA) and test it on the existing canary fixture, as the ROCm-6.2 route to stall attribution (intake-2745).
      · done when: a function returns per-class cycle shares for the canary fixture with a test, and the class mapping cites hotspot_analyzer.py
      · gate: none
      · route decided: adapter (operator 2026-11-20, ROCM-PROFILER-DECISION option d; stay on ROCm 6.2, no 7.x profiling install, 6.2 not retired)
      · ✅ 2026-11-21 `att_stall_classes.py` + test + decoded mfma_peak_v0 fixture, research `603aa38bf`. The class mapping is a verbatim port of hotspot_analyzer.py `Instruction.stall_type`; typed AttCsvError; 292 adapters tests pass CPU-only. The fixture is the r5-prep decode of the canary kernel (r4g holds raw .att only), 27708 cycles; shares are of attributed cycles, not stall-only. [no-belief: tooling]
- [x] **ROCM-PROFILER-DECISION** [operator-decision] Choose the stall-attribution route on the MI210 given that rocprofv3 thread trace is absent from ROCm 6.2: (d, recommended) adapt the working rocprofv2 ATT decode to the stall taxonomy; (c) a side-by-side ROCm 7.x profiling-only install; (a) backport rocprofv3, aqlprofile and the trace decoder to 6.2; (b) a system-wide ROCm upgrade (intake-2745, intake-2724).
      · done when: the operator's choice is recorded under this box; (d) proceeds through ROCPROF-ATT-ADAPTER-1, any other option gets its own boxes
      · gate: none
      ✅ 2026-11-20 DECIDED (operator): option (d). STAY ON ROCm 6.2 for builds and production; stall attribution goes through the rocprofv2 ATT adapter (ROCPROF-ATT-ADAPTER-1); 6.2 is NOT retired and champion development does not move to 7.2. Evidence: the 2026-11-05 ROCm 10.1 side-by-side A/B on C5/C6 (operator NO-GO for Q38P-3/3a/3b), nothing since favours 7.2; the only new reason (rocprofv3 thread trace) is covered by the adapter. Package: `/mnt/raid0/llm/tmp/rocm72-decision-20261120.md`. [no-belief: operator decision record]
- [x] **RKA-SRC1-DTYPE-RULE** [non-inference] Add two kernel-authoring rules and one rebase trigger to this handoff (intake-2869, intake-2899, intake-2900): (1) a new input dtype in a hot in-house kernel (MMVF, q8mf_pre_i8, q8sk_quantize) is a template parameter, never a runtime flag tested in the inner loop; (2) a new src1 dtype requires a review of every in-house route gated on src1 being F32 (mmq-q8-mf.cu:1270, MMVF_CHUNK, the cuBLAS precheck at ggml-cuda.cu:2075 @ 98ff8a4); (3) the rebase-review trigger is a merged upstream BF16-activation producer in the graph builder (a cast node or type switch), not the op-coverage series #29675, #32135, #32387 and #32533, and that review checks the RMS_NORM fusion gates (ggml-cuda.cu:3404, :4265-4270) and the ROPE+VIEW+SET_ROWS fusion.
      · done when: the three rules committed in this handoff's kernel-authoring section with the commit SHA recorded under this box
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
      · ✅ 2026-11-24 the three rules are committed as the *Input dtypes and rebase triggers* subsection of the agentic-rocm-kernel-authoring track, root `a259d2e6d`. file:line from `git show 98ff8a4:` (mmq-q8-mf.cu:1269-1274 and :187, ggml-cuda.cu:2075-2079, :2086-2099, :2995-3010, :3404-3426, :4265-4271). [no-belief: docs rule]
- [x] **RKA-IPB-CENSUS-1** [inference] Measure the instruction-issue budget of the q8_0 gv_fattn kernel on the MI210 (intake-2870, intake-2879): rocprofv3 SQ_INSTS_VALU / SQ_INSTS_SALU / SQ_INSTS_LDS / SQ_WAVES counters on the 27B DFlash2 verify at 16k context, n_q 1/4/8, expressed as instructions per KV byte against the device budget (FOSCAR Eq. 2 units), plus implied VALU utilisation. Model 27B Q8_0 + DFlash2 verify; build C21 98ff8a4 GPU store; region MI210; estimate ~1 h; metric instructions per byte and VALU utilisation. Stop-on-answer when every shape has a counter read; stop-on-futility if rocprofv3 cannot attribute counters to gv_fattn. ✅ 2026-11-24 [belief: cc] LDS_RESIDENCY_FIRST: median VALU utilisation 12.0% (<= 25%), gv_fattn 130-279 GB/s of 1638; result /mnt/raid0/llm/tmp/ak-rka-ipb-census-gpu-20261124-r2/out/RESULT.json
      · done when: per-shape instructions-per-byte and VALU utilisation filed under this box with the run path, and the verdict: >= 50% VALU utilisation means a decode diet comes first in AK-GVFATTN-Q4KV, <= 25% means LDS residency comes first
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
  - 2026-11-24 (autokernel) RESULT, row `ak-rka-ipb-census-gpu-20261124-r2` (C21 98ff8a42a, rocprofv3 SQ_INSTS_VALU/SALU/LDS/SQ_WAVES, 27B q8_0 gv_fattn, n_q 1/2/5/8, kv 8k and 32k; the 16k point was not measured): LDS_RESIDENCY_FIRST. kv8k runs at 130-151 GB/s of the 1638 GB/s peak (8-9%), kv32k at 246-279 GB/s; instructions per KV byte VALU 0.092-0.134 against a 0.108 budget; VALU utilisation 8.3-9.8% at kv8k and 14-17% at kv32k (median 12.0% over n_q >= 2); SQ_WAVES 512 at kv8k (832 at kv32k) on 104 CUs. VALU is <= 25%, so LDS residency comes first, not a decode diet. Result `/mnt/raid0/llm/tmp/ak-rka-ipb-census-gpu-20261124-r2/out/RESULT.json`. [belief: cc]
- [x] **VATTN-ROOFLINE-1** [inference] Bring the 27B q8_0 verify attention (gv_fattn) on the MI210 toward bandwidth roofline (operator-directed, 2026-11-24). Census ak-rka-ipb-census-gpu-20261124-r2 at C21 98ff8a4 measured 130-279 GB/s of 1638 (8-17%), VALU 8-12%, SQ_WAVES 512 at kv 8k: 128 WGs x 4 waves at 1 WG/CU (44.5 KB LDS), split count min(2*nsm/4, n_kv/256). Lever `GGML_HIP_VATTN_RF=1` (default off): LDS-cut 16-key kernel at 2 WG/CU plus one full resident split round (52 splits, 208 WGs, no tail), partial-traffic cap. Fork branch `llama.cpp-experimental-c22-vattn-roofline-20261124` @ `7374b892f` (C21 + cherry-pick 95d7a65e5 + RF). Design and predicted GB/s per lever: `/mnt/raid0/llm/tmp/verify-attn-roofline-design-20261124.md`. Gate row ak-c22-vattn-roofline-gate-gpu-20261124 (greedy np1, C21 baseline). Model 27B Q8_0 + DFlash2; build C22 VATTN-RF store; region MI210; estimate ~5 h; metric op GB/s ON/OFF and e2e ms per verify round. Stop-on-answer when the row writes KEEP / NO_KEEP / FAIL_CORRECTNESS_TBO / FAIL_KLD; stop-on-futility on op GB/s < 1.2x OFF after rep 1 or e2e speedup < 1.0 at N/2; gate-class = keep-gate with futility-only interims.
      · done when: the gate row verdict (KEEP / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with per-shape op GB/s ON and OFF, the e2e ms/round speedup with its CI, the KLD, and the run path; on KEEP the knob is queued for the next champion fold, on NO_KEEP the design levers 2-4 (double-buffered LDS, K register-direct) are opened as the next box
      · gate: ak-c22-vattn-roofline-gate-gpu-20261124        · inputs: `/mnt/raid0/llm/tmp/verify-attn-roofline-design-20261124.md`
      · 2026-11-24 (autokernel) the lever-1 gate row ak-c22-vattn-roofline-gate-gpu-20261124 was withdrawn: RF1 was measured inside the rf2 gate (ak-c22-vattn-rf2-gate-gpu-20261124, `/mnt/raid0/llm/tmp/ak-c22-vattn-rf2-gate-gpu-20261124/out/RESULT.json`) as arm RF1: op 1.19-1.33x vs OFF on every kv32k/64k shape, e2e +1.9% ms/round CI [-0.4, +4.2], KLD 0.00029 (noise floor). Verdict NO_KEEP, filed under VATTN-ROOFLINE-2; levers 2-4 were already opened as that box. [belief: cc]
- [x] **VATTN-ROOFLINE-2** [inference] Levers 2 and 4 of the 27B q8_0 verify-attention roofline design, built now without waiting for the VATTN-ROOFLINE-1 gate (operator-directed, 2026-11-24). Lever 2 `GGML_HIP_VATTN_RF=2` (stacked on lever 1): double-buffered LDS, raw q8_0 blocks register-prefetched 2 chunks ahead, one block barrier per 16-key chunk, 1 WG/CU, predicted 650-800 GB/s at kv >= 32k. Lever 4 `GGML_HIP_VATTN_RF=4` (stacked on 1+2): K loaded straight into the MFMA B fragments (no K in LDS), V in LDS transposed, 16 KB LDS (admits 4 WG/CU) but ~180 VGPRs -> 2 WG/CU (launch_bounds(256,4) spilled 294 VGPRs, fixed in `2f7f5b0df`), predicted 1000-1200 GB/s at kv >= 32k. Fork branch `llama.cpp-experimental-c22-vattn-rf2-20261124` @ `2f7f5b0df` (lever 1 `7374b892f` + lever 2 `1d7df0045` + lever 4 `d2c0efdc4` + RF4 2-WG/CU `2f7f5b0df`, all default off; merge unchanged and deterministic). Design: `/mnt/raid0/llm/tmp/verify-attn-roofline-design-20261124.md`. Gate row ak-c22-vattn-rf2-gate-gpu-20261124 (greedy np1, C21 baseline, arms OFF / OFF2 / RF1 / RF2 / RF4). Model 27B Q8_0 + DFlash2; build C22 VATTN-RF2 store `gpu-20261124-2f7f5b0df-c22vattnrf2`; region MI210; estimate ~8.7 h (provisional, re-booked from the smoke); metric op GB/s per shape per arm vs OFF and e2e ms per verify round. Stop-on-answer when the row writes KEEP_<arm> / NO_KEEP / FAIL_CORRECTNESS_TBO / FAIL_KLD (an arm failing test-backend-ops or KLD > 0.003 is dropped, the rest decide); stop-on-futility per arm on op GB/s < 1.2x OFF after rep 1 (all arms -> FUTILITY_OP_BELOW_1_2) or every live arm's e2e speedup < 1.0 at block 3; gate-class = keep-gate with futility-only interims. KEEP = the best arm whose e2e CI lower bound is > 1.0 and whose op GB/s is >= 2x OFF on every kv >= 8k shape.
      · done when: the gate row verdict (KEEP_<arm> / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with per-shape op GB/s for OFF, RF1, RF2 and RF4, each arm's e2e ms/round speedup with its CI, the KLDs, the arm status and the run path; on KEEP the kept knob value is queued for the next champion fold
      · gate: ak-c22-vattn-rf2-gate-gpu-20261124        · inputs: `/mnt/raid0/llm/tmp/verify-attn-roofline-design-20261124.md`
      · 2026-11-24 (autokernel) NO_KEEP, gate row ak-c22-vattn-rf2-gate-gpu-20261124, run `/mnt/raid0/llm/tmp/ak-c22-vattn-rf2-gate-gpu-20261124/out/RESULT.json`. RF1 (KV split + LDS-cut): op 1.19-1.33x vs OFF on every kv32k/64k shape (rep-1 geomean 1.317), e2e ms/round +1.9% CI [-0.4, +4.2] with 4 of 5 blocks positive (CI lower bound < 1.0, so no KEEP), KLD 0.00029 = noise floor (OFF2 0.00027), test-backend-ops 97/97 on all four arms. RF2 (double-buffer prefetch) and RF4 (K straight into registers) FUTILE_OP at rep 1: 0.63-0.91x vs OFF. Implication: verify attention is only about 6-8% of the step at the tested contexts (1.3x on the op gave about 2% e2e). Root cause in `/mnt/raid0/llm/tmp/vattn-limiter-analysis-20261124.md`: a serial chain (softmax ds_bpermute reductions, a wait on just-issued loads, serial Q prologue, serial merge); HBM is not the limiter. Next: RF5 chain-cut (VATTN-ROOFLINE-3) and the counter row VATTN-LIMITER-1. [belief: cc]
- [ ] **VATTN-LIMITER-1** [inference] Find the real limiter of the 27B q8_0 verify attention on the MI210 before the next lever is designed (operator-directed roofline push, 2026-11-24). The VATTN-ROOFLINE-2 gate measured kv32k OFF 210-273, RF1 254-356, RF2 156-172, RF4 159-234 GB/s against a 650-1200 GB/s design prediction; its counter pass held only SQ_INSTS_LDS and SQ_WAVES. Static ISA read (`/mnt/raid0/llm/tmp/vattn-limiter-analysis-20261124.md`) puts every arm at ~5 us per 16-key chunk independent of prefetch depth: serialized ds_bpermute softmax reductions, a vmcnt wait on just-issued loads, LDS->MFMA waits, a 64-load serialized Q prologue and a 2 x n_splits serial merge loop. Counter row ak-vattn-limiter-counters-gpu-20261124 (test-backend-ops perf only, arms OFF/RF1/RF2/RF4, kv 32768 x nb 1/8, 8 rocprofv3 passes: trace, FETCH_SIZE, MemUnitBusy/Stalled, SQ wait/busy/wave cycles, LDS insts and bank conflicts, VALU/SALU/SMEM/VMEM/MFMA insts, TA/TCP stalls, L2 read latency). Model op-level FLASH_ATTN_EXT 27B shape hs256 24/4 heads q8_0 KV; build store `gpu-20261124-2f7f5b0df-c22vattnrf2`; region MI210 exclusive + host 184-191; estimate 1500 s (provisional, re-booked from the smoke); metric per-kernel counters and derived wait/conflict/latency fractions per arm. Stop-on-answer when every (arm, shape, pass) unit is read (LIMITER_COUNTERS_COMPLETE); stop-on-futility on a witness or attribution miss or > 25 % of counter cells rejected; gate-class = report-only.
      · done when: the row verdict (LIMITER_COUNTERS_COMPLETE / FUTILITY_*) is filed under this box with the run path, the analysis file ranks the limiters against the counters (each hypothesis confirmed or refuted by a named counter), and the next lever box is opened from the top-ranked limiter with a predicted GB/s
      · gate: none        · inputs: `/mnt/raid0/llm/tmp/vattn-limiter-analysis-20261124.md`
- [ ] **Q8-MULTICOL-GEMV-1** [inference] 27B Q8_0 verify MUL_MAT at widths 2-8 streams each weight row once for all columns (autokernel census top lever, 2026-11-24). The C21 census row ak-27b-verify-kernel-roofline-census-gpu-20261124-r2 measured width-1 MMVQ at 68-76% of HBM peak (32.5 ms step) and the same weights at width 4 (MMVQ, 39-50%, 46.6 ms) and width 8 (q8wv, 49-57%, 45.1 ms), so about 13-14 ms per verify step is recoverable. Causes, read from the C21 code: MMVQ ncols 2-4 runs 2 warps per block and assembles each Q8_0 int from 16-bit loads; q8wv has no cross-step prefetch at 13-15 waves/CU. New kernel `GGML_HIP_Q8MC=1` (default off, `mmq-q8-mc.cu`): the q8wv memory path plus a 2-deep register weight pipeline, exact M 2..8, routed ahead of MMVQ and q8wv for Q8_0 weights > 1 MiB on CDNA2; predicted 1150-1300 / 1100-1250 / 1000-1200 GB/s at widths 2/4/8. Fork branch `llama.cpp-experimental-c22-q8mc-20261124` @ `5356f3cbf` (parent C21 `98ff8a42a`); test-backend-ops MUL_MAT Q8_0 cases at the 27B shapes n 1..8 vs CPU. Design: `/mnt/raid0/llm/tmp/q8-multicol-gemv-design-20261124.md`. Gate row ak-c22-q8mc-gate-gpu-20261124 (greedy np1, C21 baseline, arms OFF / OFF2 / ON). Model 27B Q8_0 + DFlash2; build store `gpu-20261124-5356f3cbf-q8mc`; region MI210 exclusive + host 184-191; estimate ~4.8 h (provisional, re-booked from the smoke); metric rocprofv3 op GB/s per shape at widths 1/2/4/8 and e2e ms per verify round. Order: op first (partial `out/OP-GBPS.json`), then test-backend-ops and KLD <= 0.003 at -ub 8 and -ub 4, then e2e (sd 0.018, 1 dummy + 4 scored blocks). Stop-on-answer when the row writes KEEP / NO_KEEP / FAIL_CORRECTNESS_TBO / FAIL_KLD; stop-on-futility if the step-weighted op speedup geomean over widths 2/4/8 is < 1.1x after rep 1, or e2e < 1.0 at block 2; gate-class = keep-gate with futility-only interims. KEEP = correctness passes, step-weighted op GB/s at widths 4 and 8 each >= 1.3x OFF, and e2e not CI-worse.
      · done when: the gate row verdict (KEEP / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with per-shape op GB/s at widths 1/2/4/8 for OFF and ON, the step-weighted speedup per width, the KLDs, the e2e ms/round speedup with its CI and the run path; on KEEP the knob is queued for the next champion fold
      · gate: ak-c22-q8mc-gate-gpu-20261124        · inputs: `/mnt/raid0/llm/tmp/q8-multicol-gemv-design-20261124.md`
      · 2026-11-25 (autokernel) r1 ak-c22-q8mc-gate-gpu-20261124 filed inconclusive (FUTILITY_HARNESS_WITNESS, no e2e): op agg ON/OFF w1 1.00x, w2 1.32x, w4 1.37x, w8 0.98x (M=8 YT=4 sat at 128 VGPRs), KLD on-u8 0.000412. r2 ak-c22-q8mc-gate-gpu-20261124-r2 (store `gpu-20261125-2910e556d-q8mc`: 8 MiB size floor, M=8 YT=2 three-deep) filed fail FUTILITY_E2E_AT_HALF: op w1 1.00x, w2 1.32x, w4 1.38x (ON 957-1097 GB/s, 58-67% of 1638), w8 0.89x (OFF 746-918 vs ON 675-826 GB/s, the rework regressed w8), attn_kv routed to stock 1.00x, KLD on-u8 0.000444 / on-u4 0.000566, e2e 0.942x (CI 0.922-0.961, block log ratios -0.062/-0.058). Served verify width (all 9 r2 server logs, `#prop/pos`): 2,811 verify calls, 97.2% at w8, 2.7% at w2-w6 (DFlash2 always drafts 7; only the n_remaining clip shortens a draft), so w2-w6 is under 3% of weight-GEMV time and multi-column cannot move the served 27B. r3 on the branch @ `054cc750c` routes M >= 7 back to stock (GGML_HIP_Q8MC_MAX default 6) and is NOT republished. The w8 design (AGPR/MFMA accumulators, YT=4 three-deep, register-shared activations; stock w8 about 55% of peak, census headroom about 75%) is in `/mnt/raid0/llm/tmp/q8-w8-design-note-20261125.md`. Run `/mnt/raid0/llm/tmp/ak-c22-q8mc-gate-gpu-20261124-r2/out/RESULT.json`. Box left open for a w8 kernel. [belief: cc]
- [x] **Q8-W8-GEMV-1** [inference] 27B Q8_0 weight GEMV at verify width 8 (97% of served DFlash2 verify calls; stock q8wv about 55% of the 1638 GB/s peak, census ceiling about 75%, about 13-14 ms per verify step). New opt-in kernel `GGML_HIP_Q8W8=1` (default off, `mmq-q8-w8.cu`, ne11 == 8, CDNA2, > 8 MiB): full-block lanes (one 34 B block per lane, 2176 B per load triple, scale from the window or DPP neighbour), YT 4, 3-deep register pipeline across row tiles, 8-wave WG so the unified VGPR/AGPR file gives 256 regs (built: depth 3 172 VGPR, depth 2 135 VGPR, 0 AGPR, scratch 0). Design 2 = existing int8 MFMA V3 path routed to M=8 (GGML_HIP_Q8_MF=3, MIN=MAX=8). Fork branch `llama.cpp-experimental-c22-q8w8-20261125` @ `20a3fac5a` (parent C21 `98ff8a42a`), store `gpu-20261125-20a3fac5a-q8w8`. Inputs: `/mnt/raid0/llm/tmp/q8-w8-design-note-20261125.md`. Gate row ak-c22-q8w8-op-gpu-20261125 (op only, arms OFF / W8D3 / W8D2 / MF3). Model 27B Q8_0 (op level + KLD ub8 -lv 4); region MI210 exclusive + host 184-191; estimate ~25 min (provisional, re-booked from the smoke); metric rocprofv3 op GB/s per shape at w8 (w4/w1 guards). Stop-on-answer when the row writes GATE_PASS_<arm> / GATE_FAIL / GUARD_FAIL / FAIL_CORRECTNESS_TBO; stop-on-futility if every design arm has step-weighted w8 speedup < 1.05x after op rep 1; gate-class = futility-only interim. GATE_PASS = step-weighted w8 x >= 1.2 with every shape >= 1.1, test-backend-ops vs CPU all pass, KLD <= 0.003. ✅ 2026-11-25 [belief: cc] design 5 q8wp GATE_PASS_PW2 1.32x (ak-c22-q8wp-op-gpu-20261125); e2e gate row filed as ak-c22-q8wp-e2e-gpu-20261125 under Q8-W8-INPLACE-E2E-1.
      · done when: the op-only gate row verdict (GATE_PASS_<arm> / GATE_FAIL / GUARD_FAIL / FAIL_* / FUTILITY_*) is filed under this box with per-shape w8 GB/s for OFF, W8D3, W8D2 and MF3 on the six big 27B shapes, the step-weighted speedups, the w4/w1 guard ratios, the KLD and the run path; on GATE_PASS an e2e gate row is filed
      · gate: ak-c22-q8w8-op-gpu-20261125        · inputs: `/mnt/raid0/llm/tmp/q8-w8-design-note-20261125.md`
      · 2026-11-25 (autokernel) op gate ak-c22-q8w8-op-gpu-20261125 FUTILITY_OP_BELOW_1_05 (polar FAIL) after op rep 1, no tbo/KLD run: step-weighted w8 x vs stock q8wv W8D3 0.942, W8D2 0.979, MF3 0.890. Both designs fail; depth 2 beats depth 3 (in-flight bytes not the limiter at occupancy 2). Run /mnt/raid0/llm/tmp/ak-c22-q8w8-op-gpu-20261125/out/RESULT.json. [belief: cc]
      · 2026-11-25 (autokernel) design 3 op gate ak-c22-q8wo-op-gpu-20261125 FUTILITY_OP_BELOW_1_05 (filed fail) after op rep 1, no tbo/KLD run: step-weighted w8 x vs stock q8wv WO2 0.90, WO4 0.95. Per shape w8 x (WO2/WO4): attn_q 0.924/0.941, attn_qkv 0.911/0.939, attn_out 0.922/0.934, attn_gate 0.928/0.938, ffn_gateup 0.912/0.961, ffn_down 0.850/0.959; stock OFF attn_q w8 912 GB/s (55.7 % of 1638). Guard WO2 w1 0.992-1.001x, w4 1.000x except ffn_down 1.59x (OFF-arm outlier, unverified). Third w8 design to lose to stock q8wv; the next step is the limiter counter row (Q8-W8-LIMITER-1), not a fourth design. Run /mnt/raid0/llm/tmp/ak-c22-q8wo-op-gpu-20261125/out/RESULT.json. [belief: cc]
      · 2026-11-25 (autokernel) design 4 op gate ak-c22-q8wm-op-gpu-20261125 FUTILITY_OP_BELOW_1_05 (filed fail) after op rep 1, no tbo/KLD run: step-weighted w8 x vs stock q8wv MW2 0.478, MW4 0.304; w1/w4 unchanged (0.99-1.06x). Per shape w8 us OFF/MW2/MW4: attn_q 73.7/163.0/255.2, attn_qkv 68.0/138.8/205.3, attn_out 45.0/77.0/128.3, attn_gate 41.7/69.8/126.8, ffn_gateup 103.1/226.9/357.9, ffn_down 106.6/229.8/351.9. int8 MFMA cut static insts/byte 0.101 -> 0.034 (YT2) yet ran 2-3x slower: per-lane row-scattered 4 B-aligned dwordx4 loads over 16 rows touch ~32-48 partial 64 B lines per wave instruction vs ~17 full lines for q8wv's 1088 B contiguous run (~3x TA/L1 requests per byte); MW4 worse than MW2 (L1 thrash). Coalescing, not instruction count, bounds this MFMA form. Run `/mnt/raid0/llm/tmp/ak-c22-q8wm-op-gpu-20261125/out/RESULT.json`, branch @ `1d4874a8a`. [belief: cc]
      · 2026-11-25 (autokernel) design 5 op gate ak-c22-q8wp-op-gpu-20261125 GATE_PASS_PW2 (filed pass): step-weighted w8 x vs stock q8wv PW2 1.316, PW1 1.278. Per shape PW2 w8 x: attn_q 1.348 (911 -> 1228 GB/s), attn_qkv 1.300, attn_out 1.291, attn_gate 1.315, ffn_gateup 1.308 (915 -> 1197 GB/s), ffn_down 1.348 (886 -> 1195 GB/s): about 73 % of the 1638 GB/s peak vs stock 55 %. w4 / w1 guards 0.995-1.001. KLD PW2 0.000234, PW1 0.000398 (max 0.003). The op row read a cached packed copy, and its one-time repack was excluded from per-op time. The in-place, no-extra-VRAM form and the e2e gate are Q8-W8-INPLACE-E2E-1. Run `/mnt/raid0/llm/tmp/ak-c22-q8wp-op-gpu-20261125/out/RESULT.json` (sha256 40566029), branch @ `b9a34740b`. [belief: cc]
- [x] **Q8-W8-INPLACE-E2E-1** [inference] End-to-end gate for Q8 w8 design 5 (q8wp, GATE_PASS 1.32x stock q8wv at w8 in ak-c22-q8wp-op-gpu-20261125) in its production form. The MFMA-operand-order layout (a permutation inside each 16-row tile, same size) REPLACES the natural bytes once at model load through the q8ip in-place mechanism: no cached copy, no extra VRAM. Knob `GGML_HIP_Q8W8=4 GGML_HIP_Q8W8_INPLACE=1`, default off (=2 also packs non-weight buffers, for test-backend-ops). Design choice: option (a) with a format-aware registry. A tensor is natural, V5I stage-packed or q8wp-packed, and q8wp wins where both accept it (> 8 MiB, K % 256, N % 16; GET_ROWS-only token_embd and selector_* stay natural). Every consumer of a q8wp weight reads it or gets the natural bytes: MUL_MAT n 1..8 runs q8wp directly (n < 8 zero-pads the activation columns); n > 16 on the cuBLAS route uses a one-pass q8wp -> f16 convert. Everything else (n 9..16, MMQ, MMVQ fusions, GET_ROWS, CPY) gets an unpack-on-read transient natural copy, fusions over the weight are disabled, and get_tensor and partial writes see the natural layout. Stage-layout readers (V5/V3, packed MMVQ, packed MMQ loader, packed convert) now check is_stage, so they never see q8wp bytes. Witness lines at INFO cover the repack, the run on the packed weight, the convert and the unpack-on-read. test-backend-ops `q8wpip_add_eval_cases` (39 cases) covers 6144x5120 and 4112x2304 at n 1..9/12/16/17/33/64/512, 5120x17408 at n 1/4/7/8/16/512, a 4100x2304 natural guard, GET_ROWS and CPY q8_0 -> f32. Fork `llama.cpp-experimental-c22-q8w8-20261125` @ `13b59e593`, store `gpu-20261125-13b59e593-q8wpip`. Gate row ak-c22-q8wp-e2e-gpu-20261125 uses the greedy lever method: np1, one request at a time, T=0, served 27B recipe with the DFlash2 drafter n-max 7 and the served V5I env on every arm, C21 baseline. Arms OFF / OFF2 / ON, paired and interleaved, a fresh server per visit, `-lv 4`. It runs test-backend-ops vs CPU in three envs (V5I, V5I + in-place q8wp, in-place q8wp alone) and KLD at ub 8/4/16/512. N = 8 scored blocks (sd 0.018 gives an MDE of 2.0 %), with a futility look at block 4 and block 0 discarded. Model 27B Q8_0 + DFlash2-Q8_0; region MI210 exclusive + host 184-191; estimate ~3.7 h (provisional, re-booked from the smoke); metric ms per verify round (msr) and tok/s, ON vs mean(OFF, OFF2). Stop-on-answer when the row writes KEEP / NO_KEEP / FAIL_CORRECTNESS_TBO / FAIL_KLD. Stop-on-futility on e2e u < 1.0 at the block-4 look (FUTILITY_E2E_AT_HALF) or on a witness, residency or input miss. Gate-class = keep-gate with a futility-only interim. KEEP (operator-approved op-bandwidth rule) requires all four: correctness passes, KLD <= 0.003, the op gain already shown, and an e2e 95 % CI upper bound >= 1.0 (a no-regression guard). The e2e ratio and CI are reported. Note: OFF here is V5I (stage-packed V5 at ~1.04 TB/s at M=8), not the op row's stock q8wv, so expect about +10 % rather than the 15-18 % estimated against q8wv. ✅ 2026-11-25 [belief: cc] KEEP (filed pass, ak-c22-q8wp-e2e-gpu-20261125): e2e ms/round 1.006 [0.998, 1.014], tok/s 1.0095 [1.003, 1.016]; served gain ~+0.6-1 %, not the predicted ~+10 % (caveat below); profile follow-up Q8-SERVED-PROFILE-1.
      · done when: the gate row verdict (KEEP / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with the e2e msr ratio and its 95 % CI, the tok/s ratio, per-ub KLD, the three test-backend-ops case counts (incl. the 39 Q8-W8-INPLACE-E2E-1 cases) and the run path; on KEEP the knob pair is queued for the next champion fold
      · gate: ak-c22-q8wp-e2e-gpu-20261125        · inputs: `/mnt/raid0/llm/tmp/q8-w8-design-note-20261125.md`
      · 2026-11-25 (autokernel) e2e gate ak-c22-q8wp-e2e-gpu-20261125 KEEP (filed pass) under the operator-approved op-bandwidth rule: op 1.32x at w8 (ak-c22-q8wp-op-gpu-20261125 GATE_PASS); test-backend-ops vs CPU 429/429 in all three envs (OFF V5I, ON V5I + in-place q8wp, SOLO in-place q8wp), 39/39 Q8-W8-INPLACE-E2E-1 cases in each; KLD k-off2-u8 0.000439, k-on u8 0.000483 / u4 0.000279 / u16 0.000448 / u512 0.0 (max 0.003); e2e (8 scored blocks) ms/round ratio 1.006 [0.998, 1.014], tok/s ratio 1.0095 [1.003, 1.016]. Caveat: the predicted ~+10 % e2e did not show up; the served gain is about +0.6-1 %. The op gate measured q8wp against stock q8wv, while the served V5I baseline (q8mf stage-packed) is already faster, and the ON server logs show q8wp calls at n = 1, 2, 6 as well as 8, so not every call is the w8 shape the op gate measured. The served-decode kernel profile that explains the gap is Q8-SERVED-PROFILE-1. Champion-fold queueing of the knob pair waits on that profile. Run `/mnt/raid0/llm/tmp/ak-c22-q8wp-e2e-gpu-20261125/out/RESULT.json` (sha256 da24762d). [belief: cc]
- [x] **Q8-SERVED-PROFILE-1** [inference] Served-decode kernel profile of the 27B np1 recipe, the measurement that should have preceded the w8 GEMV work. Why does q8wp, 1.32x at w8 at the op level, give only about +1 % e2e (Q8-W8-INPLACE-E2E-1)? Row ak-27b-served-decode-profile-gpu-20261125 runs rocprofv3 kernel trace (the method of ak-27b-verify-kernel-roofline-census-gpu-20261124-r2) around the real served llama-server: DFlash2 n-max 7, greedy, -lv 4, V5I env, store `gpu-20261125-13b59e593-q8wpip`. Arms: OFF (V5I) and ON (V5I + `GGML_HIP_Q8W8=4 GGML_HIP_Q8W8_INPLACE=1`). Each arm uses one fresh server, one discarded warm-up, and 2 long-context prompts x 256 decode tokens. Reported per arm, normalised per generated token and per verify step: (a) GPU time by kernel family, with the Q8 weight GEMV split by family (q8wv / q8mf / mmvq / q8wp / q8sk / hipBLAS / MMQ), plus activation quantize, attention, norms, GDN, copy, convert and idle gaps; (b) the width histogram of the Q8 weight calls, split target-verify / drafter / other; (c) the weight-GEMV share of the step; (d) the per-family ON - OFF delta. Model 27B Q8_0 + DFlash2-Q8_0; region MI210 exclusive + host 184-191; est 1500 s (provisional, re-booked from the smoke); metric GPU ms per verify step by kernel family. Stop-on-answer when the row writes PROFILE_COMPLETE. Stop-on-futility on FUTILITY_ATTRIBUTION (no located window, no target-verify forward, or other > 5 % of busy time) or on a witness, residency or input miss. Gate-class = futility-only (diagnostic, no keep decision).
      · done when: the profile row verdict (PROFILE_COMPLETE / FUTILITY_*) is filed under this box with, per arm, the per-step and per-token family table, the Q8 weight-call width histogram by role, the weight-GEMV share, and the ON - OFF delta. It also gives the answer to "why 1.32x op -> ~1 % e2e", the realistic remaining weight-GEMV ceiling (floor at 1638 and 1200 GB/s), the next-largest target by time share, and the run path
      · gate: none        · inputs: `/mnt/raid0/llm/tmp/ak-27b-served-decode-profile-gpu-20261125/job.py`
      · 2026-11-25 (autokernel) profile row ak-27b-served-decode-profile-gpu-20261125 PROFILE_COMPLETE (filed inconclusive): step time OFF 64.2 ms vs ON 66.0 ms (traced, 156/157 steps). Weight GEMV is 28.3 ms/step (44 % of the step, gemv_q8mf OFF; ON gemv_q8wp 28.5 ms, 43 %). q8wp vs the served V5I q8mf is 0.98x on the calls it replaces (28.46 ms vs 27.98 ms per step), which is why 1.32x at the op gives about 1 % e2e. Idle is 23-25 % of the step. Ceiling: 1.18x step speedup if weight GEMV ran at 1638 GB/s, 1.045x at 1200 GB/s. Next targets by time share: idle 24.9 %, copy 5.9 %, elementwise 4.6 %, attention 4.5 %. Run `/mnt/raid0/llm/tmp/ak-27b-served-decode-profile-gpu-20261125/out/RESULT.json`. [receipt-ack: ak-27b-served-decode-profile-gpu-20261125 INCONCLUSIVE — the profile ran to completion and answered its question; the inconclusive filing records that it carries no keep decision] [belief: cc]
- [ ] **Q8-SERVED-IDLE-1** [inference] Close the served 27B decode idle that Q8-SERVED-PROFILE-1 found, and the per-request checkpoint stalls behind it. A no-compute re-analysis of that row's kernel traces (`/mnt/raid0/llm/tmp/served-idle-analysis-20261125.md`) shows that the 15.0-16.5 ms/step 'idle' is mostly ONE stall per request: context checkpoint 2 (`create_check`, 189.65 MiB host copy, 0.92-0.98 s, about 210 MB/s) sits between prefill and the first verify. It counts in prompt eval, not in ms/round. Steady-state idle is 3.2 ms/step (OFF) and 4.0 ms/step (ON). Intra-verify-forward idle is 0.003 ms/step, so launch overhead is hidden and HIP graph capture (compiled in, not env-disabled, engagement unproven at -lv 4) cannot recover idle. The rest is host turnarounds at the V->d, d->d and d->V boundaries (2.1-2.9 ms/step), a ~74 ms once-per-request stall (~0.9 ms/step) and scattered 5-20 ms stalls (~0.5 ms/step). No existing knob is worth >= 3 ms/step, so no lever row was published. Next, in order: (1) an API-trace profile row (`rocprofv3 --kernel-trace --hip-runtime-trace --memory-copy-trace`, same recipe) to attribute the boundary gaps and the 74 ms stall; (2) a checkpoint D2H build (pinned staging buffer with async copy in state_seq_get_data, ckpt 3 after the response is sent), gated on checkpoint time < 0.05 s and byte-identical greedy output; (3) device-side greedy acceptance, est 1.5-2.5 ms/step; (4) copy/elementwise launch fusion (400 cpy_scalar per verify, 100 drafter rocclr blits), est 1.5-2.5 ms/step busy. Metric: served ms/round plus per-request checkpoint seconds. Gate-class = diagnostic, then keep-gate per build. Step (1) is row ak-27b-served-api-trace-gpu-20261125: model 27B Q8_0 + DFlash2-Q8_0, store `gpu-20261125-13b59e593-q8wpip`, OFF arm (V5I) only, region MI210 exclusive + host 184-191, est 1200 s (provisional, re-booked from the smoke). Stop-on-answer when that row writes ATTRIBUTION_COMPLETE; stop-on-futility on FUTILITY_ATTRIBUTION (no decode window, no target-verify forward, empty API trace or no checkpoint copy cluster) or a witness, residency or input miss; gate-class = futility-only for the trace row. Step (2) is Q8-SERVED-CKPT-COPY-1.
      · done when: the API-trace row attributes the steady-state boundary gaps (sync versus host compute) and the 74 ms stall, and each lever (checkpoint D2H, device-side accept, launch fusion) is filed with a served ms/round A/B result or a recorded reason not to build it
      · gate: none        · inputs: `/mnt/raid0/llm/tmp/served-idle-analysis-20261125.md`
  - 2026-11-25 (autokernel) NOT TICKED, step (1) done: row `ak-27b-served-api-trace-gpu-20261125-r2` = **ATTRIBUTION_COMPLETE** (filed pass; `/mnt/raid0/llm/tmp/ak-27b-served-api-trace-gpu-20261125-r2/out/RESULT.json`, write-up `/mnt/raid0/llm/tmp/served-api-trace-20261125.md`). V5I OFF arm, 152 verify steps, 771562 HIP API calls. Boundary gaps per step: target->drafter 1.69 ms (memcpy_async 1.16 ms), drafter->target 1.28 ms (sync 0.45, no-API 0.52), drafter->drafter 0.65 ms. Pre-first-verify was 56-58 ms per request (no-API ~36 ms, sync ~9.5 ms, memcpy ~10.7 ms). Totals: hipStreamSynchronize 14907 ms over 14828 calls, hipMemcpyAsync 6560 ms over 47877 calls. Step (2) checkpoint copy: the separate row ak-c22-ckpt-copy-gate-gpu-20261125-r2 found the copy is 19 ms, not the stall's cause. Remaining: levers (3) and (4). [belief: cc]
  - 2026-11-25 (autokernel) step-idle reconcile (`/mnt/raid0/llm/tmp/27b-step-idle-reconcile-20261125.md`): the REAL served 27B idle is 3.2 ms/step, not the 15 ms the first profile implied; about 2-2.5 ms of it is removable via devhandoff (DEV-SELECT/DEV-INJECT). Re-size the remaining idle levers against 3.2 ms, not 15. [belief: cc]
- [ ] **Q8-SERVED-CKPT-COPY-1** [inference] (child of Q8-SERVED-IDLE-1, step 2) Make the context-checkpoint host copy fast. Code reading at C21 `98ff8a42a`: server `create_checkpoint` -> `common_prompt_checkpoint::update_tgt` -> `llama_state_seq_get_data_ext(PARTIAL_ONLY)` -> `llama_io_write_host`, which defers one `write_tensor` per GDN/recurrent state tensor (r_l and s_l per layer, per cell range) and flushes them in its destructor as one synchronous `ggml_backend_tensor_get` each into the caller's pageable `std::vector` (freshly resized, so first-touch faults under numactl --membind=3). On HIP every call is a pageable D2H: the runtime pins or bounces the destination per call and syncs, which is how 189.65 MiB takes ~0.9 s (~210 MB/s). Restore (`llama_io_read_host`) is the same per-tensor pageable H2D. Fix behind `LLAMA_CKPT_PINNED=1` (default off): every device copy of one flush goes through ONE reused pinned host buffer per device (the device's host buffer type, hipHostMalloc), then one host memcpy each; restore stages the same way. Same bytes, same order, so the checkpoint blob is byte-identical. New test `test-ckpt-pinned-restore`: checkpoint as the server takes it, greedy generate, seq_rm + restore, greedy generate again, PASS = identical tokens; it prints the blob FNV hash for OFF/ON comparison. Fork branch `llama.cpp-experimental-c22-ckpt-copy-20261125` @ `9525aa1b7` (fix `2dc9229a7` + test rollback-order fix, off C21 `98ff8a42a`), store `gpu-20261125-9525aa1b7-ckptpin`. Gate row ak-c22-ckpt-copy-gate-gpu-20261125: model 27B Q8_0 + DFlash2-Q8_0 (n-max 7), served V5I env on both arms, np1 greedy, long prompts (~8k tokens) x 256 tokens, streamed, back-to-back requests; arms OFF / ON (knob), a fresh server per visit, paired ABBA blocks, -lv 4, resumable per visit; region MI210 exclusive + host 184-191; estimate 2400 s (provisional, re-booked from the smoke); metric client TTFT and total request latency (ON/OFF ratio), with ms/round as a no-regression guard. Stop-on-answer when the row writes KEEP / NO_KEEP / FAIL_CORRECTNESS. Stop-on-futility on a TTFT ratio 95 % CI lower bound >= 1.0 at the block-2 look (FUTILITY_LATENCY) or a witness, residency or input miss. Gate-class = keep-gate with a futility-only interim. KEEP requires all of: greedy output identical OFF vs ON on every prompt, the restore test PASS in both envs with equal blob and token hashes, TTFT and total-latency ratio 95 % CI upper bounds < 1.0, and the ms/round ratio CI lower bound <= 1.0 (not regressing).
      · done when: the gate row verdict (KEEP / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with the TTFT and total-latency ratios and CIs, the ms/round ratio, the per-checkpoint save time OFF vs ON, the restore-test hashes and the run path; on KEEP the knob is queued for the next champion fold
      · gate: ak-c22-ckpt-copy-gate-gpu-20261125        · inputs: `/mnt/raid0/llm/tmp/served-idle-analysis-20261125.md`
- [x] **Q8-SERVED-DEV-SELECT-1** [inference] (child of Q8-SERVED-IDLE-1; device-resident DFlash2 piece c) Run the DFlash2 greedy selector argmax chain on the device. At C21 `98ff8a42a`, `common/speculative.cpp` `draft()` reads the whole DFlash2 lattice to the host with `llama_get_embeddings_nextn` and runs the selector chain there, about 0.8 ms/step of drafter->verify boundary idle (`/mnt/raid0/llm/tmp/served-idle-analysis-20261125.md`). Fix behind `LLAMA_DFLASH_DEV_SELECT=1` (default off): a drafter graph tail (`src/llama-dflash-select.h`: per depth `get_rows(scores, pred)` -> `ggml_argmax` (ties to the lowest index, the DTREE-A rule, same as `std::max_element`) -> `get_rows(ids, pred)`) becomes the nextn output, so the host reads 7 F32 ids from the pinned output buffer instead of the lattice; greedy only (aborts at T > 0). Test `test-dflash-dev-select`: device chain vs a verbatim copy of the host chain on every backend, 8 lattice configs x 25 seeds incl. heavy-tie and all-tie lattices (CPU PASS inside the build claim). Fork `llama.cpp-experimental-c22-df2-devselect-20261125` @ `8f266f5ff` (off C21), store `gpu-20261125-8f266f5ff-devselect`. Gate row ak-c22-df2-devselect-gate-gpu-20261125: model: 27B Q8_0 + DFlash2-Q8_0 (n-max 7), served V5I env all arms, np1 greedy, 4 long prompts x 256 tokens, -lv 4; arms OFF / OFF2 / ON, fresh server per visit, cyclic paired blocks (block 0 dummy + 12 scored), resumable per visit; correctness units first (GPU unit test, OFF/ON draft-id logs); region MI210 exclusive + host 184-191; est 15600 s (provisional, re-booked from the smoke). Metric ms/round speedup (OFF-mean / ON). Stop-on-answer when the row writes KEEP / NO_KEEP / FAIL_CORRECTNESS_*. Stop-on-futility on FUTILITY_E2E_AT_HALF (speedup < 1.0 at the 6-block look) or a witness, residency or input miss. Gate-class = keep-gate with a futility-only interim. KEEP iff greedy output identical (draft ids, draft-unit texts, every e2e prompt where OFF == OFF2) AND the ms/round speedup 95 % CI lower bound > 1.0. ✅ 2026-11-26 [belief: cc] g5 NO_KEEP +1.75% [0.99,2.5] ms/round, misses 1.01 floor, lossless; folded into C22[9]-[10] by operator ruling 2026-11-26
      · done when: the gate row verdict (KEEP / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with the ms/round speedup and CI, the draft-id identity result and the greedy comparison counts
      · gate: ak-c22-df2-devhandoff-gate-gpu-20261125-g3        · inputs: `/mnt/raid0/llm/tmp/served-idle-analysis-20261125.md`
      · note (2026-11-25): gated TOGETHER with Q8-SERVED-DEV-INJECT-1 in the combined row ak-c22-df2-devhandoff-gate-gpu-20261125-r2 (arms OFF / OFF2 / BOTH = DEV_INJECT=1 + DEV_SELECT=1 / SEL = DEV_SELECT=1 for attribution; KEEP_BOTH iff identity AND BOTH ms/round CI lower > 1.0; each effect alone ~1.2-1.6 % is about the single-knob MDE, the pair ~3 % is resolvable at N=8, MDE 2.0 %). Fork `llama.cpp-experimental-c22-df2-devhandoff-20261125` @ `de93797dc` = `dd39cf3da` + `10f710397` (devselect, clean cherry-pick) + `3dbad8051` (test-dflash-dev-select per-backend TALLY: the devselect smoke's ROCm0 199/198 was HIP stderr spliced into two stdout lines, binary said 0 failing; r1 smoke read ROCm0 200/200) + `de93797dc` (fix: the dev-select branch of draft() had no `continue` and fell into the plain-DFlash sampler, GGML_ASSERT(logits != nullptr) on the first served draft, SEL alone or BOTH); store `gpu-20261125-de93797dc-devhandoff`. The separate row ak-c22-df2-devselect-gate-gpu-20261125 is withdrawn/retired (merged-into-devhandoff).
  - 2026-11-25 (autokernel) NOT TICKED, row `ak-c22-df2-devhandoff-gate-gpu-20261125-r6` filed **FUTILITY_HARNESS_WITNESS** (inconclusive, rc=0): harness_fail_unit d-draft-off (the draft-off arm witnessed LLAMA_DFLASH_DEV_SELECT/INJECT active), so no served ms/round speedup was scored. Units that ran: c-unit-sel 200/200 ROCm ok; identity (output_eq) c-unit-inj 2/4 prompt output mismatches, test ms/round 54.005 OFF vs 54.267 ON; c-unit-inj-sel 1/4 mismatches, 54.055 vs 53.387. AA diag DIAG_DRAFTER_NONDET traces the identity failures to drafter nondeterminism across a second in-process context, not to inject; the second-context nondet bisect row is queued. Next: fix the d-draft-off witness leak and re-gate. Evidence: `/mnt/raid0/llm/tmp/ak-c22-df2-devhandoff-gate-gpu-20261125-r6/out/RESULT.json`. [belief: cc]
  - 2026-11-25 (autokernel) gate rows filed since r6: `ak-c22-df2-devhandoff-gate-gpu-20261125-g1` FAIL_CORRECTNESS (identity DEVHANDOFF vs OFF differs on 2/3 prompts, no OFF2 identity arm so a real handoff bug vs target nondeterminism was undecided) and `-g3` FUTILITY_HARNESS_NONDET (OFF2 vs OFF output differs on prompts 0,1,2,4: the baseline itself is V5-atomics nondeterministic, so identity cannot gate this lever; same cause as the Pando r2 fix, identity unit with GGML_HIP_Q8_MF_INPLACE=0 and output-only). Gate pointer moved to the newest row g3; the next row needs the INPLACE=0 identity unit. [belief: cc]
- [x] **Q8-SERVED-DEV-INJECT-1** [inference] (child of Q8-SERVED-IDLE-1, device-resident DFlash2 piece (a)) Keep the DFlash2 encoder output on the GPU. At C21 `98ff8a42a` one drafter step in `common/speculative.cpp` runs `llama_encode(ctx_dft, features)`, reads the output back D2H (`llama_get_embeddings_nextn`, which syncs), memcpys it into `batch_inject.embd`, uploads it again in `llama_decode(batch_inject)` and then calls `llama_synchronize(ctx_dft)`: ~0.6 ms/step of drafter->drafter boundary idle (`/mnt/raid0/llm/tmp/served-idle-analysis-20261125.md`). Fix behind `LLAMA_DFLASH_DEV_INJECT=1` (default off; DFlash2, non-LiLiCorr, non-DSpark, np1 only): new staging API `llama_set_dflash_dev_inject` / `llama_get_dflash_dev_inject` (llama-ext.h) allocates a persistent f32 [n_embd, n_ubatch] tensor on ctx_dft's GPU backend (`cparams.dflash_dev_inject`); the DFlash encoder graph appends a `ggml_cpy` of its output into a view of it, encode skips the nextn D2H, and the KV-inject decode graph reads a view of it instead of an input tensor (batch.embd still selects the graph, contents ignored). The host memcpy and the explicit sync are skipped. Same f32 bytes, so drafts are bit-identical by construction. New test `test-dflash-dev-inject` (speculative-simple args): per prompt, the greedy np1 loop OFF then ON from fresh contexts; PASS = identical per-round drafts, accepted counts and output, and ON engaged. Fork branch `llama.cpp-experimental-c22-df2-devinject-20261125` @ `dd39cf3da` (off C21 `98ff8a42a`), store `gpu-20261125-dd39cf3da-devinject` (SHA256SUMS sha256 `da82a44b34589857685b6f4747f2a5541b0cd6c2711e11950e7abf855ec83fe8`). Gate row ak-c22-df2-devinject-gate-gpu-20261125: model 27B Q8_0 + DFlash2-Q8_0 (n-max 7), served recipe, V5I env on every arm, np1 greedy, 3 prompts x 512 tokens streamed; arms OFF / OFF2 / ON (knob), a fresh server per visit, 8 rotated 3-visit blocks (block 0 discarded), -lv 4 with the dev-inject witness lines, resumable per visit; region MI210 exclusive + host 184-191; estimate 4200 s (provisional, re-booked from the smoke); metric served ms/round, speedup = geomean(OFF, OFF2) / ON. Stop-on-answer when the row writes KEEP / NO_KEEP / FAIL_CORRECTNESS. Stop-on-futility on a speedup 95 % CI upper bound < 1.0 at the 3-scored-block look (FUTILITY_SPEED) or a witness, residency or input miss. Gate-class = keep-gate with a futility-only interim. KEEP iff greedy output identical ON vs OFF/OFF2 on every prompt, the identity test PASS, and the speedup 95 % CI lower bound > 1.0. ✅ 2026-11-26 [belief: cc] g5 NO_KEEP +1.75% [0.99,2.5] ms/round (49.14 -> 48.19), lossless; folded into C22[9]-[10] by operator ruling 2026-11-26
      · done when: the gate row verdict (KEEP / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with ms/round per arm, the speedup and OFF2/OFF null ratios with CIs, the identity-test result and the run path; on KEEP the knob is queued for the next champion fold
      · gate: ak-c22-df2-devhandoff-gate-gpu-20261125-g3        · inputs: `/mnt/raid0/llm/tmp/served-idle-analysis-20261125.md`
      · note (2026-11-25): gated TOGETHER with Q8-SERVED-DEV-SELECT-1 in the combined row ak-c22-df2-devhandoff-gate-gpu-20261125-r2 (arms OFF / OFF2 / BOTH = DEV_INJECT=1 + DEV_SELECT=1 / SEL = DEV_SELECT=1 for attribution; KEEP_BOTH iff identity AND BOTH ms/round CI lower > 1.0; each effect alone ~1.2-1.6 % is about the single-knob MDE, the pair ~3 % is resolvable at N=8, MDE 2.0 %). Fork `llama.cpp-experimental-c22-df2-devhandoff-20261125` @ `de93797dc` = `dd39cf3da` + `10f710397` (devselect, clean cherry-pick) + `3dbad8051` (test-dflash-dev-select per-backend TALLY: the devselect smoke's ROCm0 199/198 was HIP stderr spliced into two stdout lines, binary said 0 failing; r1 smoke read ROCm0 200/200) + `de93797dc` (fix: the dev-select branch of draft() had no `continue` and fell into the plain-DFlash sampler, GGML_ASSERT(logits != nullptr) on the first served draft, SEL alone or BOTH); store `gpu-20261125-de93797dc-devhandoff`. The separate row ak-c22-df2-devinject-gate-gpu-20261125 is withdrawn/retired (merged-into-devhandoff).
      · note (2026-11-25, operator policy): drafter changes are SCREENED for speed, not gated on draft identity (greedy speculative decoding guarantees the target's output, so output identity is the correctness requirement). r5 smoke FAIL (separate-process identity units) had drafts differing OFF vs ON from round 1-9, accepts sometimes differing, output_eq True on every prompt, test ms/round 1.5-2 % lower ON. Republished as ak-c22-df2-devhandoff-gate-gpu-20261125-r6 (supersedes r5; rank 2): c-unit-inj / c-unit-inj-sel PASS = output_eq on every prompt in every unit + ON engaged + OFF not engaged; d-draft units gate on texts only; draft/accept differences are reported (draft_diff_prompts, accept_diff_prompts, first_draft_div), not gated. Served timing arms, KEEP rule (ms/round CI lower > 1), resumability and -lv 4 unchanged. Prior out in prior/out-r5. (gate: line updated to r6 at the 2026-11-25 wrap-up.)
  - 2026-11-25 (autokernel) NOT TICKED, row `ak-c22-df2-devhandoff-gate-gpu-20261125-r6` filed **FUTILITY_HARNESS_WITNESS** (inconclusive, rc=0): harness_fail_unit d-draft-off (the draft-off arm witnessed LLAMA_DFLASH_DEV_SELECT/INJECT active), so no served ms/round speedup was scored. Units that ran: c-unit-sel 200/200 ROCm ok; identity (output_eq) c-unit-inj 2/4 prompt output mismatches, test ms/round 54.005 OFF vs 54.267 ON; c-unit-inj-sel 1/4 mismatches, 54.055 vs 53.387. AA diag DIAG_DRAFTER_NONDET traces the identity failures to drafter nondeterminism across a second in-process context, not to inject; the second-context nondet bisect row is queued. Next: fix the d-draft-off witness leak and re-gate. Evidence: `/mnt/raid0/llm/tmp/ak-c22-df2-devhandoff-gate-gpu-20261125-r6/out/RESULT.json`. [belief: cc]
  - 2026-11-25 (autokernel) gate rows filed since r6: `ak-c22-df2-devhandoff-gate-gpu-20261125-g1` FAIL_CORRECTNESS (identity DEVHANDOFF vs OFF differs on 2/3 prompts, no OFF2 identity arm so a real handoff bug vs target nondeterminism was undecided) and `-g3` FUTILITY_HARNESS_NONDET (OFF2 vs OFF output differs on prompts 0,1,2,4: the baseline itself is V5-atomics nondeterministic, so identity cannot gate this lever; same cause as the Pando r2 fix, identity unit with GGML_HIP_Q8_MF_INPLACE=0 and output-only). Gate pointer moved to the newest row g3; the next row needs the INPLACE=0 identity unit. [belief: cc]
- [x] **Q8-SERVED-SMALLOP-FUSE-1** [inference] (child of Q8-SERVED-IDLE-1, step 4) Fuse the served 27B small copy / elementwise launches. Trace attribution (OFF arm of ak-27b-served-decode-profile-gpu-20261125, per n=8 verify forward, ~4.4 us traced dispatch floor): F1 `cpy_scalar` x 384 = the K = n_rs_seq + 1 = 8 per-layer conv-state rollback snapshot copies of `llm_build_delta_net_base::build_conv_state` x 48 GDN layers (1.69 ms traced); G1 `k_bin_bcast` x 128 = residual add before `rms_norm` (0.57 ms); G3 96 GDN gate unary + 96 tiny bcast (0.43 ms); G7 `k_get_rows_float` x 97 GDN state gather (0.74 ms, not built: consumer-side index change); drafter 187 `k_bin_bcast` + 100 rocclr blits per step (~1.3 ms, not built: DFlash2 hidden-state concat path). The tail-fuse2 r3 "G2 and G6 never fired" was wrong: test-backend-ops aborted (SIGABRT, an AK_TF2_G3 swap case asserts for nt > 1), truncating the tbo to 92/149 cases; the r3 served smoke log shows G1, G2, G3 and G6 all ran. Fork `llama.cpp-experimental-c22-small-op-fuse-20261125` @ `fe4b63708` (off C21 `98ff8a42a`): G1 `1e4e5ffb7` (GGML_CUDA_AK_ADD_RMS_NORM), G3 `5584ddb02` (GGML_CUDA_AK_TF2_G3), F1 `b8afbaf50` (GGML_CUDA_AK_CPY_BATCH: a run of same-layout CPY nodes in one launch, bit-identical), test fix `fe4b63708`; store `gpu-20261125-fe4b63708-c22-smallop`. Gate row ak-c22-smallop-fuse-gate-gpu-20261125: model 27B Q8_0 + DFlash2-Q8_0 (n-max 7, q8_0 KV), served V5I env all arms, np1 greedy, 4 prompts x 256 tokens, -lv 4; arms OFF / OFF2 / ALL (F1+G1+G3) / F1, fresh server per visit, cyclic blocks (1 dummy + 8 scored), resumable per unit; correctness units first (test-backend-ops vs CPU, KLD); region MI210 exclusive + host 184-191; est 5600 s (provisional, re-booked from the smoke). Metric ms/round speedup (OFF-mean / arm). Stop-on-answer when the row writes KEEP_* / NO_KEEP / FAIL_*. Stop-on-futility on FUTILITY_BELOW_FLOOR (every live arm CI upper < 1.0 at the 4-block look) or a witness, residency or input miss. Gate-class = keep-gate with a futility-only interim. KEEP iff test-backend-ops PASS, KLD <= max(0.003, 3 x A/A KLD) and the ms/round 95 % CI lower bound > 1.0.
      · done when: the gate row verdict (KEEP_* / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with ms/round per arm, the ALL and F1 speedups with CIs, KLD and the per-knob witnesses
      · gate: ak-c22-smallop-fuse-gate-gpu-20261125        · inputs: `/mnt/raid0/llm/tmp/served-idle-analysis-20261125.md`
  - 2026-11-25 (autokernel) ✅ 2026-11-25 row `ak-c22-smallop-fuse-gate-gpu-20261125` filed **KEEP_ALL+F1** (pass, rc=0): served 27B ms/round speedup ALL (F1+G1+G3) 1.0312x (95 % CI 1.0239-1.0385, 8 scored blocks, saved 1.41 ms/round of 2.4 predicted), F1 alone 1.0114x (CI 1.0029-1.0200, saved 0.53 ms/round); KLD ALL 0.000385 vs A/A 0.000492 (bar 0.003); A/A ratio 0.9984; all three knob witnesses true, proof ok. Queued on `/mnt/raid0/llm/tmp/c22-keep-list-20261125.md` for the next champion fold (not folded). Evidence: `/mnt/raid0/llm/tmp/ak-c22-smallop-fuse-gate-gpu-20261125/out/RESULT.json`. [belief: cc]
- [x] **Q8-SERVED-SMALLOP-FUSE-2** [inference] (round 2 of Q8-SERVED-SMALLOP-FUSE-1; 27B elementwise tail = #2 remaining lever, bw census 2026-11-25) Cut the next served 27B small-op launches with the round-1 fusions (F1 + G1 + G3) ON as the new baseline. Remaining tail re-derived from the decode window of ak-27b-served-decode-profile-gpu-20261125 (OFF trace, per verify step, round-1 F1/G1/G3 kernels removed): drafter q8ip_permute 1.35 ms (the existing knob GGML_HIP_Q8IP_NOPACK_GETROWS, default off, C19 gate pending; not rebuilt here); drafter build_dflash2_conv ~300 launches 1.37 ms (k_bin_bcast repeat/add/mul 0.73, rocclr copyBuffer/copyBufferRect 0.44, concat_cont + fill 0.2); G7 k_get_rows_float GDN state gather 96 launches 0.74 ms (deferred: reading state through a device index changes gdn_fused / gdn_ch_scan / gdn_ch_prep / ssm_conv, their CPU references and build_rs); GDN conv input concat_non_cont 48 launches 0.70 ms; unary_gated silu 0.56; l2_norm 0.42; rms_norm q/k + leftovers ~0.35; rope 0.28. Built (fork `llama.cpp-experimental-c22-small-op-fuse2-20261125` @ `f2218746c`, off `fe4b63708`, one commit per feature, each default off): C2A `214543728` GGML_CUDA_AK_CONCAT_FLAT (non-contiguous CONCAT with ne0 < 128 runs one thread per dst element; the row-per-block kernel idles ~95 % on the 11-element GDN conv rows; bit-identical) and C2B `f2218746c` LLAMA_AK_DF2_CONV (build_dflash2_conv in 7 launches at K = 2 instead of ~15: all tap weights in one cont + repeat_4d + broadcast add, the causal shift as views of one pad_ext copy; per-tap order unchanged, bit-identical); test-backend-ops AK_CONCAT_FLAT (per-case witness) and AK_DF2_CONV (fast and legacy graphs) vs CPU, INFO witness line per knob. Store `/mnt/raid0/llm/kernels/builds/gpu-20261125-f2218746c-c22-smallop2`. Gate row ak-c22-smallop-fuse2-gate-gpu-20261125: model 27B Q8_0 + DFlash2-Q8_0 (n-max 7, q8_0 KV), served V5I env + round-1 knobs on all arms, np1 greedy, 4 prompts x 256 tokens, -lv 4; arms OFF / OFF2 / ALL (C2A + C2B) / C2B, fresh server per visit, cyclic blocks (1 dummy + 8 scored), resumable per unit; first unit correctness-only test-backend-ops, then KLD; region MI210 exclusive + host 184-191; est 5300 s (provisional, re-booked from the smoke). Metric ms/round speedup (OFF-mean / arm). Stop-on-answer when the row writes KEEP_* / NO_KEEP / FAIL_*. Stop-on-futility on FUTILITY_BELOW_FLOOR (every live arm CI upper < 1.0 at the 4-block look) or a witness, residency or input miss. Gate-class = keep-gate with a futility-only interim. KEEP iff test-backend-ops PASS, KLD <= max(0.003, 3 x A/A KLD) and the ms/round 95 % CI lower bound > 1.0. ✅ 2026-11-25 [belief: cc] NO_KEEP r4: C2B 1.0076 [0.9996,1.0157]; NOPACK_GETROWS KEEP +2.76% in sibling row
      · done when: the gate row verdict (KEEP_* / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with ms/round per arm, the ALL and C2B speedups with CIs, KLD and the per-knob witnesses; on KEEP the knob(s) are queued for the next champion fold
      · gate: ak-c22-smallop-fuse2-gate-gpu-20261125-r4        · inputs: `/mnt/raid0/llm/tmp/ak-27b-served-decode-profile-gpu-20261125/out/prof`
  - 2026-11-25 (autokernel) row `ak-c22-smallop-fuse2-gate-gpu-20261125-r4` filed NO_KEEP (borderline; `/mnt/raid0/llm/tmp/ak-c22-smallop-fuse2-gate-gpu-20261125-r4/verdict.json`): C2B (DFlash2 conv 15->7 launches) 45.42 -> 44.99 ms/round, speedup 1.0076 [0.9996,1.0157], 6/8 blocks positive, A/A 1.004, tbo 12/12, KLD 0.000372 (A/A 0.000229): real but sub-1 % (predicted about 0.6 ms, measured 0.43 ms), CI touches 1.0, no keep. Same window: the drafter NOPACK_GETROWS knob this box names, gated by `ak-c21-q8ip-nopack-gate-gpu-20261125-r3`, is KEEP +2.76 % [1.0190,1.0362] ms/round (46.46 -> 45.24, 8/8 blocks positive, A/A 0.9989, tbo 373/373, KLD 0.000422 vs A/A 0.00028, greedy output identical; env knob GGML_HIP_Q8IP_NOPACK_GETROWS=1 on the C21 store, queued in the C22 keep list). [belief: cc]
- [ ] **Q8-W8-LIMITER-1** [inference] Find what limits STOCK q8wv at ne11 = 8 on the six big 27B Q8_0 shapes before a fourth w8 GEMV design is built: three designs (q8w8 W8D3/W8D2, MF3, q8wo WO2/WO4) lost at 0.89-0.98x. The design note's "per-byte instruction issue, not latency" is inferred from timing only; the second suspect is partial DRAM page touches (1088 B pieces at a 5440 B row stride). Counter row ak-27b-q8wv-w8-counters-gpu-20261125 (test-backend-ops MUL_MAT perf only, stock, shapes attn_q / attn_qkv / attn_out / attn_gate / ffn_gateup / ffn_down at w8 with w4 and w1 as contrast, 6 rocprofv3 passes: trace; VALU/SALU/VMEM_RD/LDS insts; SQ wait/busy/wave cycles + VMEM_RD inst cycles; ACTIVE_INST_VALU/ANY + VALUBusy; TCC EA read requests total/32 B/DRAM + FETCH_SIZE; TA busy, TCP util). Model op-level MUL_MAT 27B Q8_0 shapes (no model load); build served-perf store `gpu-20261124-5d85e7e73-servedperf` (served_shape_perf_v1); region MI210 exclusive + host 184-191; estimate 1200 s (provisional, re-booked from the smoke); metric per (shape, w) VALU issue utilisation, instructions per weight byte, wait fraction, DRAM request size mix and achieved vs 1638 GB/s. Stop-on-answer when all 108 passes are read and the row writes LIMITER_ISSUE_BOUND / LIMITER_LATENCY_BOUND / LIMITER_DRAM_EFFICIENCY / LIMITER_MIXED (rule pre-registered in job.py); stop-on-futility on a witness or attribution miss or > 25 % of counter cells rejected; gate-class = diagnostic.
      · done when: the counter row verdict (LIMITER_<class> / FUTILITY_*) is filed under this box with the w8 medians and per-shape VALU issue utilisation, instructions per weight byte, wait fraction, 32 B / 64 B EA request mix and achieved GB/s, the w4/w1 contrast and the run path, and the next w8 design (or a recorded reason q8wv is at its floor) is named from that class
      · gate: none        · inputs: `/mnt/raid0/llm/tmp/q8-w8-design-note-20261125.md`
- [x] **Q8-GEMV-85PCT-1** [inference] Fresh-angle strategy for the served 27B Q8_0 weight GEMV (gemv_q8mf = V5I, 28.25 ms of the 64 ms traced verify step, ~1,170 GB/s = 71 % of 1638; operator target 85 % as Hopper decode GEMV reaches). Strategy note `/mnt/raid0/llm/tmp/q8-gemv-85pct-strategy-20261125.md`: the practical ceiling is already measured, not assumed: a plain dwordx4 read stream reached 1,498 GB/s (91.5 % of 1638) on 28 GiB at 4 waves/CU x unroll 4 = 16 KB/CU in flight (ak-dtree0-q8mf5-gate-gpu-20261120 unit `stream`), and the SAME stream fell to 1,001-1,148 GB/s at 32-128 KB/CU in flight. Every Q8 GEMV design so far (q8wv ~70 KB/CU, V3 70-104, V5I 70, q8wo, q8wp) sits 4-8x past that knee and plateaus at 70-73 %, the stream's own rate in that regime, while they differ 5x in instructions per byte, so Little's-law over-subscription (DRAM page / TCC request thrash), not issue or latency, is the leading hypothesis for the 70 % plateau; clocks are excluded (decode runs at sclk 1700 / mclk 1600, ak-prof-sclk-detm-gpu-20261120-r2) and the stream rules out a 75 % HBM ceiling. Row ak-q8-hbm-knee-map-gpu-20261125 (diagnostic) maps the knee and tests the cheapest lever on the served kernel: (1) `stream2.hip` (sealed, compiled under the grant) at 28 GiB and at GEMV footprint (33 / 67 / 95 MB x 24 buffers back to back), patterns coherent / per-WG ranges (V5 geometry) / 4-row strided waves (q8wv geometry), waves/CU 4/8/16 x unroll 1/2/4/8 (4-128 KB/CU), nt both at 95 MB; (2) the served V5I kernel q8mf6 (C21 98ff8a42a via store `gpu-20261124-5d85e7e73-servedperf`, env GGML_HIP_Q8_MF=6 MF_MIN=1 MF_INPLACE=2 MF_SLC=1 WVSK_MAX=16) under rocprofv3 kernel-trace on test-backend-ops perf, shapes attn_q / ffn_gateup / ffn_down / attn_out at w8 (+ attn_q w1), with the existing grid knob `GGML_HIP_Q8_MF_WG` = 104 / 208 / 312 / 416 (1-4 WGs per CU = 17 / 35 / 52 / 70 KB/CU in flight), 3 reps, correctness (test-backend-ops vs CPU) per WG value first, witness = grid size read from the trace. Model: no model (HBM microbench) + op-level MUL_MAT 27B Q8_0 shapes; build servedperf store gpu-20261124-5d85e7e73-servedperf; region MI210 exclusive + host 184-191; estimate 1200 s (provisional, re-booked from the smoke), priority_rank 3; metric GB/s and % of 1638 per config, V5I w8 GB/s per shape per WG. Stop-on-answer when the row writes its pre-registered verdict (first match): CEILING_RESTATE (28 GiB stream < 85 %) / LEVER_LAUNCH_TAIL (67 MB back-to-back stream < 85 %: persistence or fusion is the lever) / LEVER_THROTTLE_CONFIRMED_WG<G> (V5I w8 geomean gain >= 1.05 at fewer WGs/CU: queue the served e2e no-regression row with that knob) / LEVER_THROTTLE_NEEDS_KERNEL (knee real, WG count cannot exploit it: fewer waves + deeper per-wave pipeline kernel) / LEVER_LAYOUT (rows or ranges pattern costs >= 15 % vs coherent) / LEVER_NONE_IN_STREAM; stop-on-futility on FUTILITY_HARNESS_* (stream rc, config count, q8mf6 witness or grid miss, missing unit); gate-class = diagnostic. ✅ 2026-11-25 [belief: cc] LEVER_THROTTLE_NEEDS_KERNEL: knee 16 KB/CU (stream 92-94% of 1638), 89% at 67 MB, WG throttle 0.85-1.00x; next lever Q8-GEMV-Q8WT-1 / KNEE-BATCH-1
      · done when: the row verdict is filed under this box with best28 / best67 GB/s and % of 1638, the knee table (GB/s per KB/CU in flight), the pattern costs, the launch-tail us per GEMV-sized launch, the V5I w8 GB/s per shape per WG value with its correctness result and the run path, and the named lever is opened as the next box (a served e2e no-regression row with GGML_HIP_Q8_MF_WG=<G>, a throttled-wave kernel design, a layout design, or a persistent/fused GEMV design) or the 85 % target is restated with the measured ceiling
      · gate: ak-q8-hbm-knee-map-gpu-20261125        · inputs: `/mnt/raid0/llm/tmp/q8-gemv-85pct-strategy-20261125.md`
- [x] **VATTN-ROOFLINE-3** [inference] RF5 chain-cut for the 27B q8_0 verify attention on the MI210 (operator-directed roofline push, 2026-11-24), from limiters #1-#4 of `/mnt/raid0/llm/tmp/vattn-limiter-analysis-20261124.md` (the loop is bound by an in-wave serial chain of ~5 us per 16-key chunk against a ~1.1 us HBM floor). Re-prioritised by the counter row ak-vattn-limiter-counters-gpu-20261124 (RF1, kv32k nq1): SQ_WAIT_INST_LDS/SQ_WAVE_CYCLES 0.002 refutes limiter #1 (ds_bpermute waits); SQ_LDS_BANK_CONFLICT/SQ_ACTIVE_INST_LDS 0.94 promotes limiter #6 (transposed-V store, 384-dword block step = 0 mod 32 banks); SQ_WAIT_ANY/SQ_WAVE_CYCLES 0.79 with ~481-cycle L2 latency and fetch_over_kv 1.00 says waves wait on memory with too few bytes in flight. `GGML_HIP_VATTN_RF=5` (default off) keeps the RF1 geometry (16-key LDS cut, 2 WG/CU, 52 splits). Sub-knob `GGML_HIP_VATTN_VPAD=1` pads sVt by 16 halves per 32-row block (+256 B, still 2 WG/CU); `GGML_HIP_VATTN_RF5_CHAIN=0` isolates it. The chain-cut pieces (on by default under RF=5) are the 2x-unrolled chunk loop with two raw register sets (no vmcnt wait on a just-issued load: the memory-wait fix), batched LDS fragment reads, a vectorised Q prologue, a wave-local P hand-off (2 barriers per 16 keys; KC=32 per barrier does not fit 2 WG/CU in f16 LDS) and DPP row reductions (kept, deprioritised: no VGPR cost, limiter refuted). `GGML_HIP_VATTN_MERGE=2` (default off, separable): parallel deterministic split merge. Fork branch `llama.cpp-experimental-c22-vattn-rf5-20261124` @ `041739a8d`. Gate row ak-c22-vattn-rf5-gate-gpu-20261124-r2 (supersedes r1; operator rule change 2026-11-24, as the RF6 gate; greedy np1, arms OFF / OFF2 / RF1 / RF5V = VPAD only / RF5A = VPAD + chain-cut + MERGE=2, op reference RF1). Model 27B Q8_0 + DFlash2; build C22 VATTN-RF5 store `gpu-20261124-041739a8d-c22vattnrf5`; region MI210; estimate ~8.7 h (provisional, re-booked from the smoke); metric op GB/s per shape vs RF1 and e2e ms per verify round. Stop-on-answer when the row writes KEEP_<arm> / NO_KEEP / FAIL_CORRECTNESS_TBO / FAIL_KLD; stop-on-futility per candidate on op GB/s < 1.2x RF1 after rep 1 (all -> FUTILITY_OP_BELOW_1_2) or every live candidate's e2e 95% CI upper bound < 1.0 at the halfway look (block 3); gate-class = keep-gate with futility-only interims. KEEP_<arm> = correctness passes (test-backend-ops and KLD <= 0.003) AND op GB/s >= 1.5x RF1 on every kv >= 32k shape AND e2e 95% CI upper bound >= 1.0 (a no-regression guard, not a required win); the best eligible candidate by e2e speedup.
      · done when: the gate row verdict (KEEP_<arm> / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with per-shape op GB/s for OFF, RF1 and each candidate, the e2e ms/round speedup with its CI, the KLD and the run path, and the VATTN-LIMITER-1 counters are cross-referenced (limiter #1 confirmed or refuted); on KEEP the knob(s) are queued for the next champion fold
      · gate: ak-c22-vattn-rf5-gate-gpu-20261124        · inputs: `/mnt/raid0/llm/tmp/vattn-limiter-analysis-20261124.md`
      · 2026-11-25 (autokernel) NO_KEEP (futility), gate row ak-c22-vattn-rf5-gate-gpu-20261124-r2, verdict FUTILITY_OP_BELOW_1_2 (polar FAIL), run `/mnt/raid0/llm/tmp/ak-c22-vattn-rf5-gate-gpu-20261124-r2/out/RESULT.json`. Witnesses true, KLD max 0.0030 (RF5V .000494, RF5A .000469). Both arms FUTILE_OP after rep 1: op geomean vs RF1 RF5V 1.020x, RF5A 1.170x (floor 1.2x); no e2e was run. Median op GB/s OFF/RF1/RF5V/RF5A (RF5V/RF1, RF5A/RF1): kv8192 nq1 131.3/198.6/201.6/259.4 (1.015, 1.306), nq2 127.0/192.5/195.8/251.6 (1.017, 1.307), nq4 121.1/177.2/177.3/218.2 (1.000, 1.232), nq8 108.7/143.9/145.6/182.2 (1.012, 1.266); kv32768 nq1 237.5/317.0/327.8/369.6 (1.034, 1.166), nq2 235.2/312.9/323.1/363.0 (1.033, 1.160), nq4 230.1/282.7/284.9/302.6 (1.008, 1.071), nq8 211.0/254.3/259.2/294.0 (1.020, 1.156); kv65536 nq1 273.5/355.6/369.3/400.0 (1.038, 1.125), nq2 271.7/352.9/366.1/395.2 (1.038, 1.120), nq4 266.2/318.1/321.0/336.6 (1.009, 1.058), nq8 243.5/295.4/302.1/325.7 (1.023, 1.103). RF5A is the only arm with a real gain (chain-cut + MERGE=2, best at small kv) but it stays under 1.2x RF1 and at kv >= 32k reaches 1.06-1.17x; VPAD alone (RF5V) is worth about 2%. RF6 (VATTN-ROOFLINE-4, row r2 queued) carries the remaining hope for the roofline; box left open while RF6 is pending. [belief: cc] [receipt-ack: ak-c22-vattn-rf5-gate-gpu-20261124-r2 FAILED — polar FAIL is the filed FUTILITY_OP_BELOW_1_2 measurement verdict, not a run failure; r1 ak-c22-vattn-rf5-gate-gpu-20261124 ended rc=75 superseded by r2 with no RESULT (no claim)]
- [x] **VATTN-ROOFLINE-4** [inference] RF6 deep prefetch for the 27B q8_0 verify attention on the MI210 (operator-directed roofline push past RF5, 2026-11-24). RF5 issues K/V loads from threads 0-127 only with two register sets, so a WG blocks on chunk c with only chunk c+1 outstanding: 17.4 KB per CU in flight against the ~23.6 KB Little's law needs at ~1.5 us loaded latency, a 74 % cap. `GGML_HIP_VATTN_RF=6` (default off) keeps RF5's chunk step, prologue and 2 WG/CU geometry, splits the loads across both wave pairs (group 0 owns chunks j = 0,2 mod 4, group 1 j = 1,3 mod 4, two register sets per thread as in RF5) and unrolls the loop by 4, so chunks j+1..j+3 are in flight: ~52 KB per CU. Candidates A (LDS-DMA, b32 only on gfx90a), C (8-wave producers), D (split-K per wave) and E (q8_0 aligned repack) are costed in `/mnt/raid0/llm/tmp/vattn-rf6-design-20261124.md`; B predicts 1,230-1,450 GB/s kernel, ~1,280 GB/s op incl. merge (78 % of 1638) at kv >= 32k. Fork branch `llama.cpp-experimental-c22-vattn-rf6-20261124` @ `1f752b468` (RF5 `17803ea58` + RF6 deep prefetch `251e37e60` + conflict-free transposed V store `1f752b468`, a 16-half pad per 32-row d block against the 0.94 LDS bank-conflict ratio measured by ak-vattn-limiter-counters-gpu-20261124). Gate row ak-c22-vattn-rf6-gate-gpu-20261124 (greedy np1, arms OFF / OFF2 / RF1 / RF6 = RF=6 + MERGE=2, op reference RF1). Model 27B Q8_0 + DFlash2; build C22 VATTN-RF6 store `gpu-20261124-1f752b468-c22vattnrf6`; region MI210; estimate ~6 h (provisional, re-booked from the smoke); metric op GB/s per shape vs RF1 and e2e ms per verify round. Stop-on-answer when the row writes KEEP_RF6 / NO_KEEP / FAIL_CORRECTNESS_TBO / FAIL_KLD; stop-on-futility on op GB/s rep-1 geomean over kv >= 32k < 1.5x RF1 (FUTILITY_OP_BELOW_1_5) or e2e CI upper < 1.0 at block 2; gate-class = keep-gate with futility-only interims. KEEP (operator rule 2026-11-24) = correctness passes (test-backend-ops and KLD <= 0.003) AND op GB/s >= 1.5x RF1 on every kv >= 32k shape AND e2e not CI-worse than OFF (CI upper >= 1.0); the e2e cell is a no-regression guard, not a required win.
      · done when: the gate row verdict (KEEP_RF6 / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with per-shape op GB/s for OFF, RF1 and RF6 and the % of 1638 GB/s at kv >= 32k, the e2e ms/round ratio with its CI, the KLD and the run path; on KEEP the knob is queued for the next champion fold
      · gate: ak-c22-vattn-rf6-gate-gpu-20261124        · inputs: `/mnt/raid0/llm/tmp/vattn-rf6-design-20261124.md`
      · 2026-11-25 (autokernel) NO_KEEP (futility), gate row ak-c22-vattn-rf6-gate-gpu-20261124-r2, verdict FUTILITY_OP_BELOW_1_5 (polar FAIL), run `/mnt/raid0/llm/tmp/ak-c22-vattn-rf6-gate-gpu-20261124-r2/out/RESULT.json`. Witnesses true, test-backend-ops 97/97 all arms, KLD RF6 0.000347 (off2 noise 0.000259); no e2e run. RF6 (deep prefetch + conflict-free V store + MERGE=2) op geomean vs RF1 1.153x over 12 shapes, 1.138x at kv >= 32k, floor 1.5x. PREDICTION MISS ~3.3x: design predicted ~1,280 GB/s op at kv >= 32k, measured 303-392 GB/s. Median op GB/s OFF/RF1/RF6 (RF6/RF1, % of 1638): kv8192 nq1 131.3/198.6/225.1 (1.134, 13.7%), nq2 126.7/192.5/224.4 (1.166, 13.7%), nq4 121.0/176.4/211.1 (1.197, 12.9%), nq8 108.7/144.0/178.4 (1.239, 10.9%); kv32768 nq1 237.5/316.8/348.3 (1.099, 21.3%), nq2 235.2/312.9/347.7 (1.111, 21.2%), nq4 230.2/282.8/328.4 (1.161, 20.0%), nq8 211.1/254.2/303.3 (1.193, 18.5%); kv65536 nq1 273.4/355.6/392.3 (1.103, 24.0%), nq2 271.6/352.8/388.3 (1.101, 23.7%), nq4 266.4/317.7/372.4 (1.172, 22.7%), nq8 243.4/295.4/344.0 (1.164, 21.0%). The RF lineage (RF1, RF5, RF6) plateaus at ~350-400 GB/s at kv >= 32k, about 21-24% of the 1638 GB/s peak: extra bytes in flight and a conflict-free V store did not move the plateau, so the in-flight-bytes/Little's-law model that predicted 1,280 GB/s is refuted as the binding limiter. VATTN-LIMITER-1 cross-reference: limiter #1 (ds_bpermute waits) refuted by the counters row; LDS bank conflict (limiter #6) and memory-wait fixes together gave at most 1.15x over RF1. VATTN-ROOFLINE-3 (RF5) and -4 (RF6) are both filed NO_KEEP; ticked completed-negative, no knob queued for fold. [belief: cc] [receipt-ack: ak-c22-vattn-rf6-gate-gpu-20261124-r2 FAILED — polar FAIL is the filed FUTILITY_OP_BELOW_1_5 measurement verdict, not a run failure; r1 ak-c22-vattn-rf6-gate-gpu-20261124 ended rc=75 superseded-by-r2 and was filed WITHDRAWN (no result, no claim)]
- [ ] **VATTN-ROOFLINE-5** [inference] RF7 wave-independent split-K streaming for the 27B q8_0 verify attention on the MI210 (operator-directed, 2026-11-25), designed from the measured counters after RF1/RF5/RF6 plateaued at 350-400 GB/s (21-24 % of 1638) and RF6 missed its prediction by 3.3x. RF6 data: a ~450 GB/s steady-state slope plus a ~45 us intercept, unmoved by 3x more requested bytes in flight. Hypothesis: the binding term is per-16-key WG lock-step (LDS staging + barriers), not bytes per CU. `GGML_HIP_VATTN_RF=7` (default off; does not enable RF1): K, V and P go global -> VGPR straight into the MFMA operands (S^T = K Q^T with K as the A operand, the S^T D layout reused as the PV B operand, V^T A operand under a d permutation), no LDS round trip for K/V and no barrier in the key loop, 4 independent waves per WG each with its next chunk's K and V in flight, one KV head shared by all 6 GQA heads and nq rows, deterministic in-WG combine plus a parallel merge. Static: 202 VGPRs, 0 spill, 0 scratch, 16.9 KB LDS, 2 waves/SIMD, ~70 KB/CU in flight. Predicted op 950-1,250 GB/s at kv >= 32k nq 1-2, 600-900 at nq 8, floor ~600. Design `/mnt/raid0/llm/tmp/vattn-rf7-design-20261125.md`. Fork branch `llama.cpp-experimental-c22-vattn-rf7-20261125` @ `f5bfe3473` (C21 `98ff8a42a` + RF1 `7374b892f` + RF7). Op-only row ak-c22-vattn-rf7-op-gpu-20261125 (arms OFF / RF1 / RF7, kv 8k/32k/64k x nq 1/2/4/8, 5 reps, test-backend-ops vs CPU 102 gqav cases, KLD ub 8). Model 27B Q8_0 op-level FLASH_ATTN_EXT; build C22 VATTN-RF7 store `gpu-20261125-f5bfe3473-c22vattnrf7`; region MI210 exclusive; estimate ~20 min (provisional); metric op GB/s per shape vs RF1. Stop-on-answer when the row writes KEEP_RF7 / NO_KEEP / FAIL_CORRECTNESS_TBO / FAIL_KLD; stop-on-futility on rep-1 geomean over kv >= 32k < 1.2x RF1 (FUTILITY_OP_BELOW_1_2); gate-class = op-bandwidth keep gate (operator rule 2026-11-25: KEEP = correctness passes, KLD <= 0.003, op GB/s >= 1.5x RF1 on every kv >= 32k shape; e2e only later as a no-regression guard).
      · done when: the row verdict (KEEP_RF7 / NO_KEEP / FAIL_* / FUTILITY_*) is filed under this box with per-shape op GB/s for OFF, RF1 and RF7, the % of 1638 GB/s at kv >= 32k, the KLD and the run path; on KEEP an e2e no-regression row is queued; on a ~450-500 GB/s result the per-head contiguous q8_0 KV repack (RF6 candidate E) is opened as the next lever
      · gate: ak-c22-vattn-rf7-op-gpu-20261125        · inputs: `/mnt/raid0/llm/tmp/vattn-rf7-design-20261125.md`
- [ ] **VERIFY-KERNEL-ROOFLINE-CENSUS-1** [inference] Find every low-efficiency kernel in one 27B verify step now, not only attention (operator 2026-11-24): rocprofv3 kernel trace plus counters over one verify-shaped forward of the 27B target at widths 1, 4 and 8 and contexts 1k, 8k and 32k (greedy, np1), and for each kernel the name, calls per step, time and share of the step, bytes moved (FETCH_SIZE + WRITE_SIZE), achieved GB/s and percent of the 1638 GB/s peak, VALU utilisation, waves launched and waves per CU, ranked by recoverable time = time x (1 - achieved/peak). Model Qwen3.8-27B Q8_0 target forward (llama-bench -p W -d CTX, q8_0 KV; the drafter forward is not part of the verify step); build C21 98ff8a4 GPU store; region MI210 exclusive + host threads 184-191; row ak-27b-verify-kernel-roofline-census-gpu-20261124; est 7200 s (provisional, re-booked from the smoke); metric recoverable ms per step and percent of peak per kernel. Stop-on-answer when all 9 shapes have the trace and the three counter passes read; stop-on-futility if the forward cannot be located in the trace twice or FETCH_SIZE/WRITE_SIZE return nothing after the fallbacks.
      · done when: RESULT.json carries the per-shape kernel table with verdict CENSUS_COMPLETE and polar PASS, the top 10 by recoverable time is filed under this box from `/mnt/raid0/llm/tmp/verify-kernel-roofline-20261124.md` with the run path, and every top-10 kernel outside attention has a follow-up lever box or a recorded reason it is at its floor
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
  - 2026-11-24 (autokernel) row `ak-27b-verify-kernel-roofline-census-gpu-20261124` ended FUTILITY_ATTRIBUTION (C21 98ff8a42a store, proof ok): `T ctx1024 w1: forward not located / no counter rows (rc 0) twice`. This is not a measurement and no kernel table exists. r2 is being built with aggregate-by-kernel attribution (no forward-window location). Box stays open. Result `/mnt/raid0/llm/tmp/ak-27b-verify-kernel-roofline-census-gpu-20261124/out/RESULT.json`. [no-belief: box open, futility, no measurement]
  - *Trigger (intake-kspec-1125 M1, no checkbox):* (a) if Q8_0 dense prefill is ever routed to MMQ on gfx90a, port PR #32921's column-outer order behind a CDNA J=64 gate as the first lever, judged on wall clock, not on L2 hit rate (intake-2956); (b) when a counter row next profiles MMQ Q8_0 at 9-128 columns on CDNA2, record the VALU share of the per-32 scale epilogue (mmq-vec-dot.cuh L197 @ 98ff8a4) against MFMA busy (intake-2957); (c) if this census shows the stock GDN recurrent kernel's reductions at 3% of the step or more, screen PR #32867's DPP warp_reduce_sum there, and if backend sampling is turned on for a GPU role, time CUMSUM over the vocabulary on gfx90a first (intake-2962#00).
- [x] **RKA-GV-PSCALE-1** [inference] Test gv_fattn numerics on sink-heavy attention, where P is stored as f16 (intake-2870, intake-2878): add a test-backend-ops case with one dominant early key (attention-sink pattern) on GQA-verify shapes, compare gv_fattn error to the vector path, and try P scaled by 2^10 before the f16 store as the candidate fix. Applies to the production q8_0 path as well. Model: op-level FLASH_ATTN_EXT GQA-verify shapes of the 27B (head dim 256); build llama.cpp-experimental from C21 98ff8a4; region MI210; estimate ~1 h; metric max abs error vs the CPU reference. Stop-on-answer when the error ratio is recorded with and without scaling; stop-on-futility if the sink case cannot be expressed in test-backend-ops. ✅ 2026-11-24 [belief: cc] pass rc=0; gv/vector sink error ratio 0.15-0.77 with and without 2^10 scaling, scaling not adopted; result /mnt/raid0/llm/tmp/ak-gdn-pscale-rocm-tests-gpu-20261124/out/RESULT.json
      · done when: test case committed with its SHA and the error ratio gv/vector with and without P scaling recorded under this box; adopt the scaling (default-off knob, then fold) only if gv error exceeds 2x the vector-path error
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
      · 2026-11-24 code prepared, not built or run. Fork branch `llama.cpp-experimental-gv-pscale-20261124` @ `4d41f6520` (from C21 98ff8a42a): `test_fa_gqa_verify_sink` (key-0 +20 logit, 27B 24/4 hd256, n_q 4/8, kv 4096/16384, f16 and q8_0 KV, max-abs err printed, `-p 'gqav_sink='`) and `GGML_HIP_GV_PSCALE_LOG2` (default 0, bit-identical). Build script `/mnt/raid0/llm/tmp/rka-gv-pscale-build-20261124.sh` (build claim, after 13:30Z). GPU arms script `/mnt/raid0/llm/tmp/rka-gv-pscale-test-20261124.sh` (gv / gv+2^10 / vector). The error ratio is still open. [no-belief: prepared, unmeasured]
      · ✅ 2026-11-24 (autokernel) [belief: cc] RESULT ak-gdn-pscale-rocm-tests-gpu-20261124 = PASS (rc 0 on all four ROCm0 cells: gdn slots witness, pscale-gv, pscale-gv_ps10, pscale-vec; RESULT.json sha256 7b30696d916d733ab77f64c3d8466e3386b519f0ef453d852f778b1963d13b78; build proof clean: gdn ca68f4d00, ps 4d41f6520, GGML_HIP_GV_PSCALE_LOG2 in the HIP lib; residency proven). Test case `test_fa_gqa_verify_sink` committed on fork branch `llama.cpp-experimental-gv-pscale-20261124` @ `4d41f6520`. Max abs error vs CPU reference, sink case (key 0 +20 logit, 24/4 heads, hd256), cells (n_q 4/kv 4096, 8/4096, 4/16384, 8/16384): q8_0 KV gv 2.62e-4 / 2.62e-4 / 3.14e-4 / 3.47e-4, gv+P2^10 2.62e-4 / 2.58e-4 / 3.06e-4 / 3.13e-4, vector 3.82e-4 / 3.82e-4 / 4.66e-4 / 4.50e-4, so gv/vector = 0.69 / 0.69 / 0.67 / 0.77 and (gv+2^10)/vector = 0.69 / 0.67 / 0.66 / 0.70; f16 KV gv 2.37e-5 / 2.56e-5 / 7.38e-5 / 1.03e-4, gv+2^10 1.67e-5 / 2.53e-5 / 8.26e-5 / 7.90e-5, vector 1.58e-4 / 1.59e-4 / 2.10e-4 / 2.42e-4, gv/vector = 0.15 / 0.16 / 0.35 / 0.42. Reading: gv_fattn is MORE accurate than the vector path on sink-heavy attention (worst ratio 0.77, far below the 2x adoption bar), and 2^10 P scaling moves gv error by <= 12 % either way (ps/gv 0.71-1.12). Decision: P-scale knob NOT adopted (stays default-off, not folded); the test case is the KEEP for the C22 fold. Log: /mnt/raid0/llm/tmp/ak-gdn-pscale-rocm-tests-gpu-20261124/out/logs/
- [x] **RKA-BATCH-INV-CENSUS-1** [non-inference] Census batch invariance of the MI210 verify graph at widths 1-16 (intake-2882, intake-2883#record, intake-2872), op by op at 98ff8a4: RMSNorm (norm.cu:347-370, one block per row, already invariant), MMVQ (nwarps depends on ncols_dst, mmvq.cu:813-850), skinny Q8 (f32 unsafeAtomicAdd flush), MMQ / mmq-q8-mf (unsafeAtomicAdd at :1454), hipBLAS BF16, and flash attention (parallel_blocks chosen from occupancy and n_kv, fattn-common.cuh:1514-1594). Per op: invariant or not, the change needed (pinned per-column reduction geometry, fixed-size KV chunks rather than a fixed count, atomics removed) and its port cost.
      · done when: per-op census table committed in this handoff with the commit SHA recorded under this box, and the verdict: open an implementation box for a default-off invariant audit arm if 3 or fewer ops need change, else record the cost and close
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
      · ✅ 2026-11-24 per-op census table committed in this track (*Batch-invariance census*), root `a259d2e6d`, code read at 98ff8a4. Verdict: 5 of 6 ops need a change (MMVQ nwarps(ncols_dst), skinny Q8 and mmq-q8-mf atomics, hipBLAS BF16 solution choice, FA for f16 KV). That is > 3, so the cost (~260-330 LOC) is recorded and the box closes with no implementation box. The M8 monitor is not triggered. [belief: cc]
- Monitor (intake-ak-1124 M8, operator-approved 2026-11-24, no checkbox): If RKA-BATCH-INV-CENSUS-1 finds 3 or fewer ops need change: implement a default-off invariant audit arm (pinned per-column reduction geometry for n = 1-16, fixed-size KV chunks in vector flash attention) with a bitwise width-1 vs width-8 test (intake-2882).

#### Batch-invariance census of the MI210 verify graph, widths 1-16 (RKA-BATCH-INV-CENSUS-1; code read at `98ff8a4`, no build, no run)

"Invariant" means a column's fp32 result is bitwise the same whether it runs at width 1 or at width n ≤ 16. Atomics make an op non-deterministic even at a fixed width.

| Op | Launch-parameter dependency (file:line @ 98ff8a4) | Invariant? | Change needed | Est. LOC / perf cost |
|---|---|---|---|---|
| RMSNorm | `rms_norm_f32_cuda`, `norm.cu:347-372`. Grid `(nrows, nchannels, nsamples)`, one block per row. Block width (384/256/1024) depends on `ncols` only. | yes | none | 0 / 0 |
| MMVQ | `calc_nwarps(type, ncols_dst, table)`, `mmvq.cu:813-866`. The GCN/CDNA table gives `nwarps` 4 (Q8_0 n=1; 8 in the four-row cell), 2 (n 1-4), 1 (n 5-8+). `nwarps` sets the cross-warp k-split, so the summation order changes with `ncols_dst`. | no | pinned per-column reduction geometry: one `nwarps`/rows-per-block for n 1-16 under an audit flag | ~40 / gives up the bs=1 nwarps 4/8 lever (+4.6 % 27B tg) or slows n 5-8 |
| skinny Q8 (`q8sk_mul_mat`) | split-K over waves, f32 `unsafeAtomicAdd` flush into a pre-zeroed dst, `mmq-q8-skinny.cu:236-243` (zero `:299`, launch `:301`) | no (non-deterministic across runs) | atomics removed: per-split partial buffer plus a fixed-order reduce kernel | ~100 / one extra launch plus partial traffic (S x M x N x 4 B, small at M ≤ 16) |
| MMQ / mmq-q8-mf | stream-K partial tiles accumulate with `unsafeAtomicAdd`, `mmq-q8-mf.cu:1450-1455` (`!full`). Full tiles are stored directly. | no (non-deterministic across runs) | fixed-order fixup buffer for the partial tiles (as in upstream stream-K fixup) | ~100 / small (boundary tiles only) |
| hipBLAS BF16 | rocBLAS picks the GEMM solution from (m, n, k), so the tiling and k-split change with n. Reached via `ggml_cuda_mul_mat_cublas` (`ggml-cuda.cu:2075-2079`, `CUBLAS_PRECHECK` and the F16/BF16 paths). | no | pad src1 to a fixed n = 16 under the audit flag, or pin a rocBLAS solution index | ~20 (pad) or ~60 (solution pin) / up to 16x wasted GEMM work at n=1 |
| Flash attention | Vector / MMA path: `launch_fattn`, `fattn-common.cuh:1514-1594`. `parallel_blocks` starts from occupancy, then a wave-efficiency search over `nblocks_total = ntiles_dst * parallel_blocks`, and `ntiles_dst` depends on n_q. The split count, and with it the KV chunk boundaries and the LSE merge order, therefore change with width. gv path (`fattn-gqa-verify.cu:768-781`): `n_splits` depends on nsm, n_head_kv, n_seq and n_kv only, so it is width-invariant. But f16 KV routes n_q=1 to the vector kernel (`gv_min_nq` returns 2 for non-q8_0 KV). | q8_0 KV on gv: yes for n 1-16, single sequence. f16 KV: no | fixed-size KV chunks (split count = ceil(n_kv / C)) in the vector kernel, or route f16 n_q=1 through gv (`GGML_CUDA_FA_GQA_VERIFY_MIN_NQ=1`, existing knob) | 0 (knob) to ~50 / f16 n_q=1 decode on gv is 0.93-0.98x (C8-FOLD3) |

**Verdict: 5 of 6 ops need a change** (MMVQ, skinny Q8, mmq-q8-mf, hipBLAS BF16, and flash attention for f16 KV). That is more than 3, so no implementation box is opened. The M8 monitor condition (3 or fewer) is not met. Recorded cost of a full invariant audit arm: ~260-330 LOC across 5 ops. It forfeits the bs=1 MMVQ nwarps lever and adds one reduce launch per skinny/MF GEMM. Only RMSNorm and the q8_0-KV gv attention are batch-invariant as built.
- [x] **VKRC-BYTES-PLAUSIBLE** [non-inference] Add a deterministic bytes plausibility check to the verify-kernel roofline census extraction (epyc-inference-research scripts/kernel_rnd/autokernel/loop/census_extract.py extract_verify_roofline @ 4ca0d0d9a) before VERIFY-KERNEL-ROOFLINE-CENSUS-1 r2 is read: flag every kernel row whose FETCH_SIZE+WRITE_SIZE-derived GB/s exceeds the HBM peak the census uses, or whose bytes per call differ from the analytic footprint (weight or tensor bytes x launches) by more than 2x, and print the flagged rows beside the ranking; no LLM estimate (intake-2960: LLM device-memory traffic estimates are the weak half, within 1.20x in 36-40% of cases) ✅ 2026-11-25 [no-belief: build/landing] research 04405da00 (+e182d4688 bd2694353); grid-derived footprints; r2: 114 rows, 0 flagged, 69 unknown, ratios 1.001-1.05; 10 tests; Fable TICK
      · done when: a pytest under epyc-inference-research scripts/kernel_rnd/autokernel/loop/ passes on origin/main and covers an over-peak row (flagged), a row with bytes 3x the analytic footprint (flagged) and a plausible row (not flagged), using the existing testdata/census/verify_roofline.RESULT.json fixture
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
- [x] **Q8-GEMV-Q8WT-1** [inference] Build and gate the design-6 q8wt served 27B Q8_0 weight GEMV that holds 16 KB/CU in flight per workgroup (the measured HBM knee) ✅ 2026-11-25 [belief: cc] FAIL_BELOW_FLOOR r4: e2e 0.955 [0.943,0.968], op 0.77-0.86x of V5I; 16 KB/CU cap loses
      · est: 5400 s (provisional, re-booked from the smoke)
      · done when: row verdict (KEEP_Q8WT / NO_KEEP / FAIL_* / FUTILITY_*) filed under this box with op GB/s and % of 1638 vs V5I, KLD and e2e ms/round CI
      · stop: stop-on-answer when the gate row files KEEP_Q8WT / NO_KEEP / FAIL_CORRECTNESS; stop-on-futility on FUTILITY_BELOW_FLOOR (look at block 4, every CI upper < 1.0) or FUTILITY_HARNESS_*; gate-class = futility-only
      · gate: ak-c22-q8wt-gate-gpu-20261125-r4        · inputs: `/mnt/raid0/llm/tmp/q8-gemv-85pct-strategy-20261125.md`
      · owner: autokernel
  - 2026-11-25 (autokernel) row `ak-c22-q8wt-gate-gpu-20261125-r4` filed FAIL / FUTILITY_BELOW_FLOOR (`/mnt/raid0/llm/tmp/ak-c22-q8wt-gate-gpu-20261125-r4/verdict.json`): q8wt is SLOWER, OFF 46.52 -> Q8WT 48.66 ms/round, speedup 0.955 [0.943,0.968], all 4 blocks -3.5..-5.3 %, A/A 1.001, correctness PASS (tbo 424/424, KLD 0.000292). The 16 KB/CU cap (4 single-wave WGs/CU, no barriers) does not reach the stream knee on the served GEMV (op 0.77-0.86x of V5I). Diagnosis `ak-c22-q8wt-op-diag-gpu-20261125`: V5I is issue-bound (VALU 29/KB vs stream 9, issue_busy 0.46, wait_inst 0.51), only marginally over-subscribed, so capping bytes in flight cannot help. Dead end seeded in the AutoKernel journal (`akm-c22-q8-gemv-q8wt-q8lean-kneebatch-det2`, research `3735c9e65`). Remaining lever: conversion-heavy core redesign (box Q8-GEMV-CONVCORE-1). [belief: cc]
- [x] **Q8-GEMV-LEAN-1** [inference] Build and gate the instruction-lean V5I variant (GGML_HIP_Q8_MF=8: no LDS staging, SGPR+immediate addressing, packed scale math; same grid/occupancy/load depth as V5I) for the served 27B Q8_0 weight GEMV, motivated by ak-c22-q8wt-op-diag-gpu-20261125 (V5I issue-bound: issue 0.46, wait_inst 0.51, VALU 29/KB, LDS 11/KB; near over-subscription). Branch llama.cpp-experimental-c22-q8lean-20261125 @ b3365430c; ISA note /mnt/raid0/llm/tmp/q8lean-isa-breakdown-20261125.md. ✅ 2026-11-25 [belief: cc] FUTILITY r2: LEAN 0.687 [0.679,0.695], -31%, stopped by futility watcher
      · model: Qwen3.8-27B Q8_0 + DFlash2-Q8_0 (served V5I) · quant_build: store from b3365430c (to build) · est: 5400 s (provisional)
      · done when: a gate row files KEEP_LEAN / NO_KEEP / FAIL_CORRECTNESS / FUTILITY_* with tbo, KLD and served ms/round CI vs V5I
      · stop: stop-on-answer when the row files its verdict at block 8; stop-on-futility on the block-4 look (CI upper < 1.01), a witness failure or FUTILITY_HARNESS_*; gate-class = futility-only
      · gate: none
      · owner: autokernel
  - 2026-11-25 (autokernel) row `ak-c22-q8lean-gate-gpu-20261125-r2` stopped by the interim futility watcher at the 3-block look (`/mnt/raid0/llm/tmp/ak-interim-futility-watch.py`; STOP file in the row dir): LEAN 0.6867 [0.6789,0.6946], LEAN_WG312 0.6862 [0.6616,0.7117], i.e. -31 %, both candidates ci-futile. Removing LDS staging does not help an issue-bound V5I; the no-LDS variant is dead. [belief: cc]
- [x] **Q8-GEMV-KNEE-BATCH-1** [inference] Build and gate the knee-batch q8 GEMV variant that batches GEMV-sized launches to reach the >= 67 MB buffer regime (89 % of 1638) ✅ 2026-11-25 [belief: cc] FUTILITY: knee-batch ops flat; r3 FAIL_CORRECTNESS, r4 stopped and withdrawn
      · model: Qwen3.8-27B Q8_0 + DFlash2-Q8_0 (served V5I) · quant_build: gpu-20261125-fbeb23c45-c22kneebatch · est: 4200 s (provisional, re-booked from the smoke)
      · done when: row verdict (KEEP / NO_KEEP / FAIL_* / FUTILITY_*) filed under this box with op GB/s, % of 1638, KLD and run path
      · stop: stop-on-answer when the gate row files a KEEP_<arm> / NO_KEEP / FAIL_CORRECTNESS verdict; stop-on-futility on FUTILITY_BELOW_FLOOR at the 3-block look or FUTILITY_HARNESS_*; gate-class = futility-only
      · gate: ak-c22-knee-batch-gate-gpu-20261125-r4        · inputs: `/mnt/raid0/llm/tmp/q8-gemv-85pct-strategy-20261125.md`
      · owner: autokernel
  - 2026-11-25 (autokernel) knee-batch: r3 FAIL_CORRECTNESS (`ak-c22-knee-batch-gate-gpu-20261125-r3`), r4 `ak-c22-knee-batch-gate-gpu-20261125-r4` judged futile at its interim look, stopped and withdrawn by the operator ruling that every row carries a futility look; ops measured flat (no GB/s gain from batching GEMV launches). No verdict.json was written for r4 (withdrawn). Dead end seeded with q8wt/q8lean in the journal record `akm-c22-q8-gemv-q8wt-q8lean-kneebatch-det2`. [belief: cc]
- [x] **Q8-GEMV-CONVCORE-1** [inference] Redesign the V5I served 27B Q8_0 weight GEMV conversion-heavy core (about 40 VALU per wave per unit, cvt_f32_i32 int8-to-float path) to cut VALU per KB from 29 toward the stream kernel's 9, since V5I is issue-bound not bandwidth-bound (q8wt, q8lean, knee-batch all lost) ✅ 2026-11-27 [belief: cc] fail rc=0; NO_KEEP. Served V5I speedup 0.9981x (95% CI 0.9904–1.0060). Operator 1183→1188 GB/s, VALU 28.49→24.82/KiB. All 46 cases passed per arm; max mean KLD 0.000428.; result /mnt/raid0/llm/tmp/codex-convcore-gate-20261127/out/RESULT.json
      · model: Qwen3.8-27B Q8_0 + DFlash2-Q8_0, np1 greedy, draft n-max 7
      · build: candidate HIP binary, same V5I MF=6 build for OFF/OFF2/ON
      · metric: VALU/KiB and ms/round lower, packed-weight GB/s higher
      · rule: CPU reference PASS, mean KLD <=0.003 at ub 8/4/16/512, valid A/A within 2%, KEEP if served speedup 95% CI lower >1.01
      · region: MI210 exclusive + assigned host CPUs
      · est: provisional, pilot: n=1 smoke visit to rebook
      · stop rule: stop-on-answer at 8 scored blocks; stop-on-futility on failed correctness, missing witness/proof, invalid A/A, or CI upper <1.0 at block 4; gate-class = futility-only
      · done when: a gate row files KEEP / NO_KEEP / FAIL_* / FUTILITY_* with op VALU per KB, GB/s vs V5I, KLD and served ms/round CI; or a note names why the conversion core cannot shrink (packed int8 dot / MFMA operand path already ruled out)
      · gate: none        · inputs: `/mnt/raid0/llm/tmp/q8-gemv-85pct-strategy-20261125.md` `/mnt/raid0/llm/tmp/ak-c22-q8wt-op-diag-gpu-20261125`

The kernel owner retained V5I for the tested single-request greedy Qwen3.8-27B Q8_0 + DFlash2 recipe. Both control servers logged V5 packed dispatch with `GGML_HIP_Q8_MF6_CONVCORE` unset. [Q8 conversion-core decision and audit](../../research/deep-dives/q8-gemv-convcore-20261127/README.md)

- [ ] **PC-HOSTTRAP-COVERAGE** [non-inference] Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check.
      · done when: Use the original ELFs, code objects, store manifests and build IDs. Keep one other binary for validation. Record symbol+offset, source line or unmappable reason for each sampled PC. Only trial host-trap if unresolved hotspots remain and firmware/driver enumerate the capability; collect separate baseline runtime and check perturbation, skid and sample loss.
      · gate: none        · inputs: `research/deep-dives/intake-nov27-kernel-systems/stage3-plan.md` `research/deep-dives/intake-nov27-kernel-systems/intake-3006.md` `research/deep-dives/intake-nov27-kernel-systems/intake-3020.md`
- [x] **FATTN-PRIVATE-SEGMENT** [non-inference] Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles. ✅ 2026-11-27 [belief: cc] ABSENT_PATH. The MMA V load already has a fixed width in the audited builds. Production A3B prefill and 27B RF6 verify were scratch-free. The separate A3B two-column vector kernel had a 144 B private frame and RF4 had 14 VGPR spills. [Dispatch and code-object audit](../../research/deep-dives/fattn-private-segment-20261127/README.md)
      · done when: Compare deployed GPU symbols on a train and holdout context length, retaining code-object hash, VGPR/scratch metadata, ISA and dispatch hits. A nonzero private segment alone cannot prove traffic. Stop on absent path or equal material scratch traffic; specialize and time only if affected. Check both padded and unpadded tails.
      · gate: none        · inputs: `research/deep-dives/intake-nov27-kernel-systems/stage3-plan.md` `research/deep-dives/intake-nov27-kernel-systems/intake-3009.md`

### Done

- [x] **RVP-AUD-2** ✅ 2026-08-12 —
- [x] **Pre-hardware** ✅ 2026-07-29 . Source pins and the no-execution activation order are recorded in [deep-dive §10](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md#10
- [x] **MI210** ✅ 2026-08-11 — ROCm,
- [x] **—** ✅ 2026-08-11 — immutable external scoring, exploit detectors,
- [x] **C4** ✅ 2026-08-11 — the deterministic paired
- [x] **EPYC-op** ✅ 2026-08-12 — research `d8013a6c` binds the exact selected
- [x] **—** ✅ 2026-08-12 — research `b8d8c409` adds the sealed
- [x] **—** ✅ 2026-08-03 . Version-matched
- [x] **—** ✅ 2026-08-03 : **465 distinct
- [x] **Per-block** ✅ 2026-08-03 — the constraint a C4 pass must
- [x] **Re-score** ✅ 2026-08-11 — C4 is now MED: tool availability,
- [x] **RVP-C4-2** ✅ 2026-08-11 —
- [x] **—** ✅ 2026-08-11 —
- [x] **—** ✅ 2026-08-11 — the declaration requires the
- [x] **—** ✅ 2026-08-11 — the reducer requires a complete model×sample panel and computes
- [x] **—** ✅ 2026-08-11 — `assume_monitor_aware` is mandatory true. Every tested monitor scored higher AUROC on unaware than aware **AIDE code-sabotage** runs in Figure 6 (intake-979#0
- [x] **—** ✅ 2026-08-11 — every trace requires non-empty reasoning and
- [x] **—** ✅ 2026-08-11 — the declaration
- [x] **—** ✅ 2026-07-22
- [x] **—** ✅ 2026-07-22
- [x] **RVP-T0-1** ✅ 2026-08-11 — the authorized 60-second
- [x] **RVP-C4-4** ✅ 2026-08-12 —
- [x] **RVP-C6-3** ✅ 2026-08-11 — the same
- [x] **RVP-C6-4** ✅ 2026-08-11 —
- [x] **RVP-C6-6** ✅ 2026-08-12 — The required unit is 10 planted-bug
- [x] **RVP-C5-R** ✅ 2026-08-11 — Keyword-filter merged
- [x] **RVP-C3-4** ✅ 2026-08-11 —
- [x] **RVP-C2-10** ✅ 2026-08-11 — frozen v9's
- [x] **RVP-C2-12** ✅ 2026-08-13 producer `f744cc220e722d1bda93783959471d44f8e118b0`; Research `1403462340acb89c5652a157a9aacb1ebbb5dd6c`; [fixture tests](../../artifacts/compute/codex3-rvp-c2-
- [x] **RVP-C6-10** ✅ 2026-08-12 — The durable
- [x] **RVP-VIDYA-1** ✅ 2026-08-11 — the source row is
- [x] **RVP-C6-13** ✅ 2026-08-16 — C3 surfaces now require
- [x] **RVP-C6-20** ✅ 2026-08-21 A
- [x] **RVP-C6-25** ✅ 2026-08-21 (compiled into wiki/benchmark-methodology.md, evening update) — Record the KernelFalcon test-harness admission as a SIXTH Shape-C instance in
- [x] **RVP-C4-10** ✅ 2026-08-21 — Settle GPA's input availability on the MI210 with one bounded probe (~30 min).** Run
- [x] **RVP-PWR-2** ✅ 2026-08-21 (first pass; see caveat in the result block) — Run the aliasing probe on gfx90a under LOAD, which is where any divergence appears.**
- [x] **RVP-PWR-5** ✅ 2026-08-21 — Re-measure the three CONFIDENCE-WINDOW parameters on the MI210, because the paper
- [x] **RVP-C6-26-C-POINTER-SOURCE** ✅ 2026-10-07 — [MAIN exact source/original9 acceptance](../../artifacts/ni08/c-pointer-literal-source-acceptance-20261007/README.md); Researchaefa, original TRUE9/9 and prio

**Research-intake monitor M1 (2026-11-26).** intake-2982#record. Check BF16 MFMA compiler compatibility when a clang-23 toolchain candidate enters qualification. Trigger on an actual LLVM 23 qualification build for gfx90a. Compare old/new fragments and emitted ISA at both compilers; run BF16 op parity and DF2 target-route smoke using the candidate binary. DF2-11-BF16 concerns the executed BF16 route. The upstream patch addresses compiler operand types and supplies no CDNA runtime measurement.

## Track: agentic-rocm-kernel-authoring
<!-- gate: INF-48#rocm-verify-profile-backend, EVL-47 -->

### Backlog
- [x] **ROCK-WAVE64-CHECKLIST** [non-inference] Fold the moat-cuda-to-rocm wave64 fault list and oracle-review rules (assertion count is a lower bound, read what the checker compares, base-control rebuild) into the agentic authoring checklist, and record that the rocprofv3 thread-trace recipe does not run on ROCm 6.2 (intake-2734, intake-2745, intake-2746).
      · done when: the checklist section in this track lists the hazards with their source file and the ROCm-6.2 thread-trace note, each tagged as ROCm 7.x-measured where applicable
      · gate: none
      · ✅ 2026-11-21 checklist section below [no-belief: docs fold]

#### Wave64 / oracle-review checklist (agentic ROCm authoring; gfx90a is wave64)

Sources: `amd/skills` @ 2470f33cbd47 `skills/moat-cuda-to-rocm/references/{faults-wavefront.md, faults-numerics.md, validation.md, no-hip-equivalent.md}` (intake-2745#record); `AMD-Ecosystem/moat` @ 86968a5e896a `README.md`, `.claude/agents/{validator,reviewer}.md`, `utils/codeobj_diff.py` (intake-2746#record); catalog rocm.docs.amd.com amd-skills (intake-2734#record). Every measurement below is ROCm 7.x; none was taken on 6.2. Treat each as a static-scan hint for candidate diffs and confirm it on gfx90a / ROCm 6.2.

Wave64 fault list [ROCm 7.x-measured, `faults-wavefront.md`]:
1. `__ballot` / `__activemask` return 64-bit `unsigned long long`; storing the result in 32 bits truncates lanes 32-63.
2. 32-bit mask arithmetic on 64-lane masks: `(1 << K)`, `1u << ...`, `mask ^= 1 << lane`. `1 << 31` sign-extends to `0xffffffff80000000`. Grep every `1 <<` / `1u <<` in mask expressions.
3. Logical 32-lane warps calling wave-wide collectives (`__shfl*_sync`, `__ballot_sync`, `__any_sync`, `__all_sync`, `__match_*_sync`).
4. A block narrower than one wavefront gives `blockDim.x / warpSize == 0`, which breaks reductions such as `(tid < blockDim.x / warpSize) ? warpSums[lane] : 0`.
5. `__smid()` reaches up to 125 on a 104-CU gfx90a GCD, so it overruns per-CU pools.
6. Size-threshold kernels can be unreachable by small harnesses (gfx90a memory fault above 3072 elements).
7. Never hardcode 32. Use `__GFX8__`/`__GFX9__` device guards (not `__HIP_PLATFORM_AMD__`) plus a host `warpSize` query, and validate both widths where possible. `__AMDGCN_WAVEFRONT_SIZE__` is absent in 7.2.x/7.14 [7.x-measured].
8. Numerics (`faults-numerics.md`): contraction and rounding, host math under HIP, shift counts of 0 or >= 64 in 128-bit arithmetic, half-precision GEMM accuracy.

Oracle-review rules [ROCm 7.x-measured, `validation.md`, Moat `README`/`validator.md`]:
A. Assertion count is a lower bound. A failing section can abort a case and hide the rest. Compare the count with the baseline build, or filter out the failing section and check whether the total moves (marian-dev: 284/287 became 603 after the fix).
B. Read what the checker compares. Confirm every output accessor is compared (lc0 `--backend=check` never compared moves-left) and that the test input reaches the changed path. If the gate is blind, find a second observable.
C. Base control. Rebuild the pre-fix source and show the gate still passes while the second observable is wrong. Check the precision variant users actually run, not only fp32.
D. Compile-only or CPU-only smokes prove compilation, not correctness. Separate "blocked (host fact)" from "failed (code fact)".
E. Carry a verdict forward without a re-run only when exported symbols and normalized device ISA are identical (indeterminate counts as differ; `codeobj_diff.py`). Bind evidence to the exact commit and re-derive when HEAD moves.

ROCm-6.2 profiler note (intake-2745#record, intake-2734#record): the amd/skills `flydsl-kernel-trace-analysis` recipe uses rocprofv3 `--advanced_thread_trace`, which does NOT exist on ROCm 6.2. Only `rocprofv2 --plugin att` works there, so only the stall taxonomy and the occupancy math port. Our route is `adapters/att_stall_classes.py` (ROCPROF-ATT-ADAPTER-1). The FlyDSL skills target gfx942/gfx950 on ROCm 7.2 and are not an MI210 execution arm.

#### Input dtypes and rebase triggers (RKA-SRC1-DTYPE-RULE; intake-2869, intake-2899, intake-2900)

Line references are at `98ff8a4` (C21, `llama.cpp-experimental-c21-20261124`).

1. **A new input dtype in a hot in-house kernel is a template parameter, never a runtime flag.** This covers MMVF, `q8mf_pre_i8` (`mmq-q8-mf.cu:187`) and `q8sk_quantize` (`mmq-q8-skinny.cu:294`). The dtype is chosen once at the dispatch site and instantiated, so the inner loop has no per-element branch and the existing F32 instantiation keeps its ISA. Counterexample: upstream #32533 adds the BF16 activation to MMVF as a runtime flag tested inside the kernel. Do not copy that pattern into our forks. Diff the F32 instantiation's code object before and after (checklist rule E) to prove it is unchanged.
2. **A new src1 dtype requires a review of every in-house route gated on src1 being F32.** At `98ff8a4` these are:
   - `ggml_cuda_q8ip_mf_handles`, `mmq-q8-mf.cu:1269-1274` (`src1->type == GGML_TYPE_F32`, contiguous f32 strides);
   - the `MMVF_CHUNK` route, `ggml-cuda.cu:2086-2099` (gate line `:2098`, `src1->type == GGML_TYPE_F32 && dst->type == GGML_TYPE_F32`);
   - the cuBLAS precheck, `ggml-cuda.cu:2075-2079` (`src1->type != GGML_TYPE_F32` sends the op to `CUBLAS_PRECHECK`).

   A non-F32 src1 silently leaves all three in-house routes and lands on cuBLAS/hipBLAS. The result is still correct, but the speedup disappears and nothing fails. The review must log every route (`ggml_cuda_log_mul_mat_route`) for the new dtype and confirm each one either handles it or refuses it deliberately.
3. **Rebase-review trigger: an upstream BF16-activation *producer* merged into the graph builder** (a cast node, or a type switch on the activation tensor). The op-coverage series #29675, #32135, #32387 and #32533 does not trigger it. Those PRs teach kernels to accept BF16 but nothing in the graph emits a BF16 activation yet, so our F32-gated routes stay live. When a producer lands, the rebase review checks:
   - the RMS_NORM fusion gates: `ggml_cuda_can_fuse` RMS_NORM+MUL(+ADD) asserts and requires F32 at `ggml-cuda.cu:3404-3426`, and the dispatch is at `:4265-4271`. A BF16 activation stops the fusion silently;
   - the ROPE+VIEW+SET_ROWS fusion: `ggml_cuda_should_fuse_rope_set_rows`, `ggml-cuda.cu:2995-3010` (`set_rows->type` must be F32/F16), with the call sites at `:3388` and `:3680`;
   - the three src1==F32 routes in rule 2.

> Folded from `handoffs/active/agentic-rocm-kernel-authoring.md` @ `779a81fd46b0` on 2026-11-03 (BRF-T7-F13, route 1b, operator D1/D5; retired row INF-03 → INF-48). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.
- [x] **ROCK-FLYDSL-GFX90A** [non-inference] Install flydsl into an isolated venv and try to compile one tiny vector-add kernel for gfx90a (IR or code-object only, no launch), recording the compile verdict (intake-2735).
      · done when: the compile log and verdict (lowers to gfx90a code object, or the first failing pass) are filed; a pass reopens a FlyDSL arm proposal, a fail closes it with evidence
      · gate: none
      · ✅ 2026-11-21 flydsl 0.5.1 compile-only vector-add for gfx90a PASS (needs a torch CPU import, undeclared); full pipeline to amdgcn gfx90a ISA (global_load_dwordx4, v_pk_add_f32, global_store_dwordx4). Log and ISA in /mnt/raid0/llm/tmp/flydsl-gfx90a-20261121/. No launch; execution and the ROCm-6.2 runtime untested. [no-belief: compile-only check]
- [ ] **F32-ROUTER-DISPATCH-CAPTURE** [inference] Capture an MI210 A3B router prefill and decode trace on frozen v10 for the F32 split-K census, with a separate held-out request.
      · model: Qwen3.6-35B-A3B-MTP-Q8_0 on MI210, greedy, four slots, F16 KV and MTP draft maximum two
      · build: production GPU store v10 ffc1bac82, private server with matched HIP library
      · metric: eligible ms per served round (lower is better), with actual F32 dispatches and workgroups
      · rule: compare the maximal removable time with the owner's served gate; use an observed route or mark the cell unresolved
      · est: provisional        · pilot: n=1 request validates model, residency, route and timestamps
      · stop rule: stop on missing runtime proof or after the 256- and 1024-token prefill and single- and four-request decode captures include the held-out windows
      · done when: persisted traces link both request windows to the served recipe, executed symbols and timing denominator, or identify the precise missing witness
      · gate: none        · inputs: `data/ak-short-row-census/README.md` and `handoffs/active/briefs/F32-ROUTER-SPLITK-CENSUS.md`
- [ ] **F32-ROUTER-SPLITK-CENSUS** [non-inference] Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise.
      · done when: Reuse retained A3B router traces at decode and prefill. Baseline is the resolved Tensile solution; keep a later request window. Record M/N/K, workgroups, slices and all partial-buffer writes. The upstream half-CU test bounds unsplit tile count, not slices. Stop if even eliminating targeted time would miss the owner’s served gate. Test CPU splitting only for underoccupied cores after NPS4-local partitioning.
      · gate: none        · inputs: `research/deep-dives/intake-nov27-kernel-systems/stage3-plan.md` `research/deep-dives/intake-nov27-kernel-systems/intake-3008.md`

### Agentic ROCm Kernel Authoring — MI210 Verify+Profile Harness

> **Fold destination** (BRF-T1-F23, BRF-T1-1, route 1a, 2026-11-02): absorbs 1 handoff(s) as `## Track:` sections at the end of this file (`mi210-q8-dequant-gemv-roofline.md`). The body above the first track is the former `agentic-rocm-kernel-authoring.md`.

**Scratch**: `/mnt/raid0/llm/tmp/isa-audit-runner-bind/` · worktrees: `/mnt/raid0/llm/worktrees/isa-audit-runner-*` (new runner-binding work; historical evidence paths remain unchanged)

**Status**: active investigation — hardware present; P-GPU-1 ratified. **Corrected 2026-08-10 (operator): P-GPU-1 governs the CLASS OF CLAIM a result may carry, not permission to run — the human boundary is freeze / cutover / promotion.** Benching or profiling a *live server* is still owned by whoever owns that inference. Every "operator-approved GPU runs" phrase below predates this correction; read it as claim-class, not permission.
**Next action (2026-08-22)**: preserve immutable r19, and keep the relayed C5-3..16/Hawkeye rows as
the authoring-loop backlog while INF-48 repairs the C6 launch boundary. Do not revive a gfx90a
taxonomy column, import NVIDIA strategies, use TCC hit rate as an objective, or make profiling a
prerequisite: the zero-profiler arm remains mandatory. Never resume r4-r18 or aggregate a partial
attempt into the panel.
**Created**: 2026-06-03 (via /research-intake deep-dive of the LLM-kernel-generation cluster) · **Updated**: 2026-08-12 (r19 live after copy-time staged-input binding)
**Categories**: hardware_optimization, agent_architecture, autonomous_research, tool_implementation, training_distillation
**Hardware gate — SATISFIED 2026-07-02**: AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB) is racked and the llama.cpp HIP build is verified on gfx90a (`progress/2026-07/2026-07-02-mi210.md`; memory `project_mi210_gpu_inference`). This program is now **ACTIVE**, priority **MEDIUM** — it is an *optimization*, **not a production blocker**: llama.cpp-HIP already serves ~910 tok/s @32-way as-is (2026-07-02 obs). First step = reproduce **GEAK-eval** (intake-674, arXiv 2507.23194) on gfx90a — compile+correctness+timing round-trip — as the sanity gate. **Scoping caveat (adversarially verified 2026-07-03; AMENDED 2026-08-03, see §"GEAK scoping — amended")**: GEAK **v4** retains first-class gfx90a knowledge, though all published *evaluation* is gfx942; **AgentKernelArena (679) / robust-kbench (668) are gfx942/CDNA3-listed** and must be treated as ports, not drop-in reproductions. All GPU runs remain operator-approved measurements per MEASUREMENT.md (write P-GPU-1 first). [was: "expected ~July 2026; nothing executes until the card racks" — stale after 2026-07-02 install] [was: "close the measured quantized-MMQ-dequant roofline gap: ~33% Q4_K / ~47% Q8 at batch-1" — **re-targeted 2026-08-03**, that is half the prize; see §"Program re-target"]
**Priority**: MEDIUM (activates on MI210; prep proceeds now)
**Workstream**: Inference Acceleration / GPU · **Parent index**: [`inference-research-index.md`](inference-research-index.md)
**Full reasoning + evidence**: [`research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md`](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md) ← the durable narrative; this handoff is the operational summary.
**Related**:
- [`rocm-verify-profile-backend.md`](rocm-kernel-authoring.md#track-rocm-verify-profile-backend) — **child**: the ROCm verify/profile/benchmark backend this loop drives
- [`exl3-cpu-mi210-implementation.md`](quantization-and-low-bit.md) — `INF-80` consumer of the
  gfx90a verify/profile substrate; EXL3 implementation and acceptance remain owned there
- [`gpu-drafter-mi200-investigation.md`](../archived/gpu-drafter-mi200-investigation.md) — MI210-gated; consumes the kernels this loop produces
- [`gpu-acceleration-path.md`](../completed/mi210-serving-program.md#track-gpu-acceleration-path) — the ROCm kernel-library hand-port path this automates
- [`llama-cpp-dsa-contribution.md`](rocm-kernel-authoring.md#track-llama-cpp-dsa-contribution) / [`cpu-shape-specialized-gemv-decode.md`](../completed/cpu-shape-specialized-gemv-decode.md) — the hand-HIP endgame + the CPU ukernel loop this rhymes with

---

#### Objective
Stand up an **agentic, train-free kernel-authoring loop for the installed MI210** — drive a strong coding agent through generate → compile → verify → profile → refine to produce and tune **HIP/Triton kernels** for the EPYC stack, replacing the manual hipify-and-hand-tune path. **We cannot retrain a kernel model on one MI210, but we can run a train-free verify+profile loop** — and AMD has already open-sourced most of the substrate (GEAK/Apex/AgentKernelArena), demonstrated on gfx90a.

#### Current Decision Snapshot (2026-06-03)
The path *today* (supersedes any earlier "EvoEngineer/CudaForge-first" framing):
1. **Backend = adopt AMD-native code.** **GEAK-eval (674, MIT)** is the primary benchmark/oracle/timing substrate (C1/C2/C3/C5), reproduced on our gfx90a; **Apex (675, MIT)** supplies the E2E deploy harness + Magpie scorer; **AgentKernelArena (679, Apache-2.0)** supplies a second substrate + the controller-A/B shell. Net-new to us: **C4 + C6** (see child handoff).
2. **Controller-A/B = register adapters, don't build a harness.** AgentKernelArena (679) already ships Claude Code / Codex / Cursor / GEAK adapters with a `@register_agent` pattern — **register our controllers (Claude+Codex actor-critic, EvoEngineer, KernelFoundry, K-Search, Xe-Forge, GEAK) as adapters and A/B them on gfx90a.** It compares whole agents at task level, complementing each controller's inner loop.
3. **Agent backend = Claude+Codex actor-critic** (reuse the autopilot planner's infra); local coder role is the self-hosted fallback. `opensource_only` governs deployed services, not build-time tooling — the authored kernel is the artifact, not the LLM. Empirically favored: CudaForge's best result was a cross-model coder/judge split; AgentKernelArena's best results are Claude Code / Cursor / Codex.
4. **Triton first (on-ramp), HIP second (endgame).** GEAK-eval (Triton, gfx90a-proven) → then the HIP arm via GEAK-HIP patterns (678) + AgentKernelArena's Torch2HIP suite (679) + our own HIP oracle. Pairs with `llama-cpp-dsa-contribution.md`.
5. **Differentiators we own: C6 (anti-reward-hacking) + C4 (gfx90a profiler-metric).** Both now have an AutoKernel implementation. Paired `rocprofv2` is the op-level Q4_K/Q8_0 path; direct timestamp-only `rocprof` v1 is the governed whole-model fallback and completed K28 attribution. IQ2_XXS still requires the seeded Omniperf fallback after OP-11 gives its producer a durable identity.

**Why this is the decision (one paragraph):** the entire cluster was NVIDIA-bound at the toolchain, so a from-scratch ROCm backend looked like the long pole — until GEAK/Apex/AgentKernelArena turned out to be AMD-native, permissively licensed, and (for GEAK-v1) demonstrated on **gfx90a, the MI210's exact ISA family**. That predicts *compile compatibility* on our card (not performance — single-GCD bandwidth, ROCm version, autotune space, and harness details still need reproduction), which shrinks the program to "adopt + reproduce + add C4/C6." Full reasoning, alternatives, and the rejected paths: see the [deep dive](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md).

#### Evidence — grouped by role (intake-660…679; details in the deep dive + `intake_index.yaml`)
| Role | Entries | Use |
|------|---------|-----|
| **AMD-native substrate (adopt)** | GEAK 674 (gfx90a-proven, MIT), Apex 675 (MIT), AgentKernelArena 679 (Apache-2.0) | C1/C2/C3/C5 backend + Magpie scorer + controller-A/B arena. **674 carries the only gfx90a *evaluation*; 675/679 are gfx942-listed/eval'd. But GEAK v4 carries first-class gfx90a *knowledge* — see §"GEAK scoping — amended".** |
| **AMD-native, patterns-only (gfx942-only)** | GEAK-v2 677, GEAK-HIP 678 | 677 → C4 Profiler-Analyzer (try first) + QD upgrades; 678 → HIP-arm loop (out-optimized a human engineer) |
| **Controller candidates** | EvoEngineer 666 (lead), KernelFoundry 669 (hw-awareness layer), Xe-Forge 672 (linear archetype), K-Search 673 (world-model tree, MoE-strong), GEAK 674 (first to stand up) | register as AgentKernelArena adapters; A/B on gfx90a |
| **C4 (profiler-metric) sources** | GEAK-v2 677 (raw rocprof→LLM, try first), Xe-Forge 672 (static KB), CudaForge 662 (formal selection) | the standing research risk |
| **C6 (anti-hacking) sources** | robust-kbench 668 (exploit classes, Apache-2.0), AgentKernelArena 679 (unseen-shape generalization) | the two complementary halves; our differentiator |
| **Eval philosophy** | KernelBench 664 (`fast_p`), FastKernels 671 (vendor baseline + whole-model gate) | weight end-to-end over isolated-op |
| **RL lessons (no training)** | CUDA Agent 660, CUDA-L1 661, Kevin 663 | reward design + anti-hack gates + multi-turn |
| **Optional offline later** | ConCuR 665, TritonForge 676 | SFT data-curation for a local HIP-specialized small model |
| **Not our path** | KernelCraft 670 (AIE-ML NPU/Peano, not ROCm) | harvested only: tool vocabulary + thinking-budget + ICL findings |

#### gfx90a caveat (applies to every AMD number above)
Same `gfx90a` ISA **predicts compile compatibility, not performance equivalence.** GEAK-v1's MI250X results should *build and run* on the MI210 (wavefront=64/MFMA/LDS identical), but single-GCD bandwidth, ROCm version, autotune space, and harness details require reproduction. GEAK-v2 / GEAK-HIP / AgentKernelArena publish **gfx942/CDNA3 numbers only**, so their *numbers* carry even less. **All AMD numbers are vendor-reported until reproduced on our own gfx90a.** [was: "a coverage regression vs v1" — **retired 2026-08-03**: for GEAK proper this is unpublished coverage, not removed coverage; see below.]

#### GEAK scoping — amended 2026-08-03 (research-intake Stage-2b; this IS the mandated freshness sweep)

_The prior caveat **understated** the dependency. The README's narrowing is a deployment/evaluation
statement, not a capability removal._

- README (verbatim, confirmed): *"GEAK targets AMD Instinct MI GPUs (CDNA, e.g. gfx942 / gfx950; the
  on-box card is auto-detected)"*. **All published evaluation is gfx942 — there are no gfx90a numbers.**
- **But the tree says otherwise.** `perf_knowledge/hardware/cdna2_mi200/` ships **four files**
  (`arch.md`, `matrix_core.md`, `memory.md`, `occupancy.md`), all `gens: [gfx90a]`, all
  `updated: 2026-06-08`, titled *"CDNA2 / MI250X / MI210 (gfx90a)"* — **our exact card, named**.
  `perf_knowledge/index/capability_index.yaml` carries **40 `gens:` entries including gfx90a**
  (vs 214 gfx942 / 225 gfx950 / 20 gfx908). `perf_knowledge/README.md` scopes CDNA1 → CDNA4.
- **No arch gating found** — the card is auto-detected; there is no allowlist rejecting gfx90a.
- **Correct formulation to carry forward:** *GEAK v4 carries first-class gfx90a hardware knowledge and 40
  gfx90a-applicable capability entries, but publishes zero gfx90a numbers.* **Pin `v1.0.0 @ 4ffba15a`**
  (Apache-2.0, still pinnable) for the paper's MI250X evidence. v1→v4 spans eight tags, 2025-08-01 →
  2026-07-22; repo active (pushed 2026-08-03).
- Caveat on the v1 evidence itself: **v1's release notes name only MI300X** — the gfx90a claim traces to
  the v1 **paper** (arXiv 2507.23194), not the release.
- This cuts *with* the grain of GEAK's own consumption contract, which states the KB is
  *"reference material… not decisions"* and that consumers must *"decide by on-box measurement"* —
  i.e. AMD is telling us to measure on our own card, which is exactly the standing unchecked sanity gate.
- **The KB is not error-free** — its `memory.md` ridge-point figure is off by 2× (per-GCD vs per-OAM); see
  [`mi210-mfma-compute-bound-paths.md`](../completed/mi210-mfma-compute-bound-paths.md).
- **Bonus, unexploited:** GEAK ships `languages/` docs on **hipkittens · tilelang · mojo · cutlass ·
  flydsl** and a `landscape/` section on multi-backend libs, DSLs, AI kernel agents, autotuning and
  "AMD SOTA 2026" — a **vendor-maintained survey of the exact taxonomy our Stage-2 dive built by hand**,
  available as an external check.

#### Program re-target — aim at the fp16 rung, not the Q8 rung (2026-08-03)

The old objective closed *"~33% Q4_K / ~47% Q8"*. **That is half the prize.** The fp16 rung — **62.6%
attainment — is demonstrated on our own device**, and vLLM-ROCm reaches **69.2%** on the same silicon;
DGX Spark GB10 reaches **77–80% at Q4_K_M dense across five models** on the same engine. The full ladder
and its calibration caveat live in
[`mi210-q8-dequant-gemv-roofline.md`](rocm-kernel-authoring.md#track-mi210-q8-dequant-gemv-roofline).

**Banded ceiling, for sizing campaigns** (bands, not point estimates; confidence stated):

| Lever | Band | Confidence |
|---|---|---|
| **K1 Q4_K → Q8 rung** | **+38–43%** | HIGH |
| **K5 batched elementwise/norm fusion** | **0 — CLOSED_NO_GO** | CERTAIN for frozen-v9 target selection: strict B=64/128 norm + activation + elementwise share is 1.837% / 1.490%, far below the predeclared 20% floor; the old 43% bucket conflated gather/recurrent/copy work |
| K2 Q4_K → fp16 rung | +60–80% | MEDIUM |
| K3 MoE expert-gather | ~2.0× | MEDIUM |
| K4 architect IQ2 | +2–3× | MED-LOW — attach the gfx906 kill-criterion first |
| K6 fp16 batch-1 | +11% | HIGH |
| K7 HIP graphs | +5.9% | banked already |
| K8 LDS prefetch | ~0 remaining | CDNA2 ceiling |
| **K9 MFMA decode kernels** | **0 — DO NOT BUILD** | CERTAIN (arithmetic, not counters) |
| K10 prefill | +20–30% | MEDIUM |
| **K11 closing the vLLM gap** | **not a kernel program** | see AK-D36 in `autokernel-research-loop.md` §17 |
| **K12 matching Blackwell prefill** | **unreachable** | 5.6× int8 silicon deficit |

**Prefill is mid-pack, not an AMD software problem.** MI210 converts 19–29% of matrix peak; A100 22.8%,
RTX PRO 6000 22–44%, H100 15.3%, MI300X 12.3%. **Prefill kernel *quality* is not the gap; prefill
*silicon* is.**

#### New index-backed leads — 2026-08-03 (research-intake Stage-2b)

- **ARGUS (arXiv `2604.18616`) — register as a controller candidate.** Agentic GPU kernel optimisation
  reaching **99–104% of hand-optimised assembly on AMD MI300X** for GEMM / FlashAttention / MoE;
  2–1543× over prior agentic systems; 100% KernelBench L1, 90% L2. **Absent from all six MI210/autokernel
  handoffs.** Directly on-point for the controller A/B — and, being MI300X, it is CDNA3 evidence that
  still tells us what an agentic loop achieves against *AMD's own* hand-tuned assembly.
- **HipKittens fragment-layout identity — a free compositional result.** HK's `rt_base` is **bit-identical**
  to `ggml/src/ggml-cuda/mma.cuh`'s `tile<16,16>` in our frozen v8 (`:127,144` — `get_i = tid%16`,
  `get_j = 4*(tid/16)+l`, `ne=4`). Every HK technique composes onto our existing fragments with **zero
  layout re-derivation**. The arch-independent lessons are filed in
  [`mi210-mfma-compute-bound-paths.md`](../completed/mi210-mfma-compute-bound-paths.md); do **not** vendor the framework.
- **A live gfx90a build arm already exists** on HK's `cdna3` branch (`GPU_TARGET=CDNA2` →
  `-DKITTENS_CDNA2 --offload-arch=gfx90a`, `tests/unit/Makefile:39-40`). Across all 67 headers the library
  uses exactly **six** `__builtin_amdgcn_*` intrinsics and **exactly one is unavailable on gfx90a**
  (`mfma_f32_16x16x32_fp8_fp8`, `mma.cuh:47` — non-template static inline, so it needs an `#if` guard).
  That arm carries a **~3000-test correctness harness** that would run on our silicon. This is what makes
  the *decline to port* a decision about economics rather than capability.
- **A runnable LDS bank/phase solver** — `analysis/paper_experiments/phases/*/{bank_solver.py,
  phase_solver.py, kernel.cpp}`, a 45-line kernel over rocprofv3 PMC counters, ~40 min GPU on gfx90a.
  **Do not assume the CDNA3 answer (64 banks / 2 phases of 32 lanes) transfers** — whether gfx90a is 32 or
  64 banks decides whether HK's `>>7 <<3` swizzle constants transfer at all. Blocked on profiler tooling
  (below). ~~Still blocked as of 2026-08-12 (mainB)~~ — **RESOLVED, and this line is the mis-stamp.**
  The solver **ran on 2026-08-11** via a rocprofv2-compatible counter path (receipt SHA-256
  `ae1d833c…`, 372 bank / 6,048 phase dispatches, 32 banks + 8 phase cliques). `rocprofv3` really is
  absent — that half of the 2026-08-12 check stands — but it was never required: **this line names an
  instrument the run did not use.** Nothing was blocked. Corrected 2026-08-12 (mainB).

- **`rocm-flash-attn` as an enabling path**, re-assessed: an adaptation layer with no kernel code of its
  own, but genuine tested code with honest defect annotations. Judged on whether it improves performance,
  not on whether it contains kernels.
- **Two operational levers from AMD's own ROCm llama.cpp blog:** hipBLASLt grouped-GEMM plus tuning
  (**+29%**) and ~10× fewer `hipMemcpyAsync` calls.
- **llama.cpp issue #19984 — an LLVM loop-unroll regression in ROCm 7+ costing 3.7–5× on prefill**,
  workaround `-mllvm --amdgpu-unroll-threshold-local=600`. We are on ROCm 6.2 so this does not bite today;
  it belongs on the build-flag checklist **before any ROCm upgrade**.
  **Corrected 2026-09-15 (intake-969/1414/1424):** root cause is llvm #147700 (unroll cost model, not a
  threshold change), scoped to ROCm 7.2.0 + early TheRock 7.x nightlies and reverted; decode unaffected;
  do not cite 3.7–5×. Updated guard lives in `docs/runbooks/rocm-upgrade-checklist.md`.

**Profiler tooling — RESOLVED FOR THE CURRENT C4 AND LDS SURFACES.** `rocprofv2`, `rocprof` and
`rocm-bandwidth-test` are available, version-matched to ROCm 6.2.0-66, side-loaded by extraction
rather than installed so nothing in the shared `/opt/rocm` bind mount changed:
`source /mnt/raid0/llm/tools/rocm-profilers-6.2/env.sh`. **The gfx90a counter taxonomy is proven** —
465 counters across 12 blocks, enumerated on our own card, including every counter this program
already cites. Details, per-block collection limits, and the two path quirks:
[`rocm-verify-profile-backend.md`](rocm-kernel-authoring.md#track-rocm-verify-profile-backend). This unblocks C4's existing
`rocprofv2` path. The LDS solver was also successfully adapted to rocprofv2; its r4 receipt binds the
exact commands, tool and binary hashes, 372 bank dispatches and 6,048 phase dispatches. `rocprofv3`
remains absent but is not a blocker for that completed surface. The governed IQ2 Omniperf fallback
remains separately gated by the OP-11 producer identity.

- [x] **Establish whether the LDS bank/phase counters are reachable through `rocprofv2`.** ✅
  2026-08-12 — reconciled against the already-terminal r4 empirical receipt: rocprofv2 captured 372
  bank and 6,048 phase dispatches and the solver derived 32 banks plus eight phase cliques. Receipt
  SHA-256 `ae1d833c704bdae9a78767d0fc0b927298d6d1dfdb31a0ea11c34058dc525987`.

#### Open questions (decided ones live in the deep dive §5)
- Which controller wins on gfx90a? Unknown until the AgentKernelArena A/B runs on the MI210 with EPYC ops.
- Does GEAK-eval's published MI250X speedup reproduce on the single-GCD MI210? The substrate-level
  compile/correctness/timing round-trip now passes on physical gfx90a; the published task suite and
  matched controller-performance comparison remain separate empirical questions.
- Does C4's cheapest path give a usable signal on CDNA2? **Answered 2026-08-11: yes at op level,
  not as a whole-model `rocprofv2` capture on this host.** The deterministic report resolves the
  Q4_K/Q8_0 fill → requantize → matvec sequence and emits 1%-floor wall shares. Whole-model Qwen
  prefill and IQ2_XXS op captures reproducibly exit 139 inside the profiler; these are tool-scope
  limits, not zero-work readings. AutoKernel consumes only the deterministic report, never raw
  profiler text.
- Will AMD publish gfx90a numbers / arXiv papers for GEAK-v2 / GEAK-HIP / AgentKernelArena? → Freshness Appendix in the deep dive.

#### Reporting / maintenance instructions
- After any work: update the **Current Decision Snapshot** here + the deep dive; log progress in `progress/YYYY-MM/`.
- **At every audit of this handoff, run the GEAK-family freshness sweep** in the deep dive §9 (GEAK repo pin/tag drift; missing gfx90a evidence for 677/678/679; AgentKernelArena leaderboard + GEAK-vs-general A/B; new AMD-native siblings on `AMD-AIG-AIMA`/`AMD-AGI`).
- **Done this session:** GEAK repo state recorded (HEAD `c8bfc19`, tags →`v4.8.3.3`, branches GEAK-v2/GEAK-HIP); AgentKernelArena ingested (intake-679). **Next intake candidates** if they appear: a GEAK-v2 arXiv, a GEAK-HIP open benchmark, the AgentKernelArena leaderboard.

#### Research Intake Update — 2026-07-08: KernelBench (rec-007)

**Source**: KernelBench (**intake-664#record**, arXiv:2502.10517)

> **⚠ CORRECTION 2026-08-10 — this attribution is wrong, and was already corrected elsewhere.**
> The identical line in [`mi210-speed-campaign-summary.md`](../completed/mi210-speed-campaign-summary.md)
> carries a verified 2026-07-22 correction that never propagated here: this is a **three-way
> conflation**. The real **KernelBench** is Stanford ScalingIntelligence **arXiv:2502.10517**
> (kernel *generation*, metric `fast_p`), confirmed via intake-660/661. `arXiv:2606.20128` is a
> separate seeded-fuzzing paper, and `intake-797` was never either of them — it was
> "Externalization in LLM Agents" (now merged into intake-418). The 9/9 seeded-fuzzing finding
> below belongs to the 2606.20128 paper. Surfaced while auditing references to merged intake ids.

**Corrected disposition**: the seeded-fuzzing result belongs to a separate paper and maps to **C2
(correctness)**, not C3 (timing/reward). Its useful design rules—stateful-op coverage, adversarial and
non-power-of-two extents, absolute-duration gates, speed-of-light rejection, and anti-reward-hacking
checks—are already implemented natively in AutoKernel's C2/C6 surfaces. KernelBench itself is an
isolated PyTorch operator suite, not a baseline corpus for current llama.cpp HIP kernels.

- [x] **AK-RB-1** — adopt RE-Bench's SCORING PROTOCOL for gfx90a kernel-agent evaluation, not the
      benchmark itself (intake-1072, filed 2026-08-10). Transferable: log-time scoring of
      behaviour-preserving optimization, 0 = starting state / 1 = a strong reference solution, and
      time-budget curves (2h/8h/32h) rather than pass-fail. NOT worth standing up as-is — only 1 of 7
      environments is a kernel task, it is Triton on H100, and porting to gfx90a invalidates the
      published human and model anchors that are the reason to use it. ✅ 2026-08-11 — implemented
      reference-normalized, deliberately unclipped log-time scores; behavior failures withhold reward;
      matched best-so-far curves emit at 2h/8h/32h in
      `scripts/kernel_rnd/autokernel/evaluator/rebench_scoring.py`.
- [x] **AK-KB-2** — establish the correct baseline disposition for current llama.cpp HIP kernels
      ✅ 2026-08-11 — retired the category error: exact-surface llama.cpp baselines and historical C5
      replay are authoritative; translating them into isolated PyTorch KernelBench tasks would change
      the unit under test and cannot establish a production-kernel baseline.

#### Progress checklist

- [x] Reproduce the GEAK/AgentKernelArena compile+correctness+timing round-trip on gfx90a MI210
  (first sanity gate) ✅ 2026-08-11 — the exact-pinned adapter refused gfx90a spoofing, compiled the
  live add-kernel arm under Torch 2.5.1+ROCm 6.2 / Triton 3.1.0, passed correctness 3/3 and timing
  harness 5/5 on the physical MI210, and released its device claim. Receipts:
  `/mnt/raid0/llm/autokernel/probes/inf03-geak-arena-gfx90a-preflight-20260811/receipt.json`
  (SHA-256 `256a4c60a416828a1299a35d8399609c3c5ad2541272ab41de40dd00f2f297a4`) and
  `/mnt/raid0/llm/autokernel/probes/inf03-geak-arena-add-roundtrip-20260811/receipt.json`
  (SHA-256 `aee866ee3ebd2fe88b37185f4226c3c20a5b439c60a40fac57ef1bb42898be8c`). This closes compatibility,
  not the published-suite speedup reproduction.
- **[superseded: inf48-triage 2026-11-09: matched controller-authoring A/B: R18 terminal-noncomplete and non-rankable (r4-r18 never aggregate); replaced by the AutoKernel discovery controller (controller/discovery_controller.py); full text at b3bd883d3:1982]** **(no title)**
  - [x] **Build the governed eight-arm campaign driver and audit executable coverage.** ✅ 2026-08-11
    — baseline plus Claude/Codex actor-critic, EvoEngineer, KernelFoundry, K-Search, Xe-Forge,
    GEAK-v1, and ARGUS are serialized on one MI210 at exact 2h/8h/32h checkpoints with source,
    entrypoint, executable, model, configuration, and driver hashes. The physical audit correctly
    refused before launch because only **1/8** arms was executable at the initial audit; baseline is
    explicitly a zero-hour non-authoring control. Audit receipt:
    `/mnt/raid0/llm/autokernel/probes/inf03-controller-ab-audit-20260811/receipt.json`, SHA-256
    `3152e2fa97b52d9f0b91fb43449375adec66128189fddf253b0772fadfcf59c4`; research
    `429b59a1` (promoted via `ee54c144`).
  - [x] **Provision the internal Claude-planner/Codex-actor arm.** ✅ 2026-08-11 — the exact
    three-argument Arena callable and stdin executable pin Claude Opus 5/high as planner+critic and
    GPT-5.6-Codex/high as actor, enforce exact 2h/8h/32h checkpoints plus captured process-group
    termination, confine all writes to one candidate inside the Arena workspace, and hash-bind the
    CLIs, prompts, transcripts, candidate, artifacts, and final receipt. The clean physical audit now
    admits exactly **2/8** arms (baseline plus this controller); the other six refusal rows remain
    verbatim. Implementation `dcdc2311`, binding `084b8be1`, research main `9947f805`; 409
    controller tests and 17 AutoKernel README tests pass. Neither CLI was invoked during
    implementation or audit.
  - [x] **Build the governed Arena cell runner.** ✅ 2026-08-11 — research `36ed94a8` and
    `cffd3b02` provide direct belief receipts, process-group teardown, workspace confinement, and
    a no-inference test surface for upstream controllers; the original validation passed 129 tests
    plus eight subtests.
  - [x] **Port and bind K-Search without replacing its search policy.** ✅ 2026-08-11 — research
    `866855a3`, `832f6833`, and `2ceb2878` retain the exact upstream source pin
    `53c8fab9a5e8fab2c86610d24fbec5067f90e115` and put the governed adapter on the fixed campaign path.
  - [x] **Port and bind GEAK-v1 without replacing its evolutionary loop.** ✅ 2026-08-11 —
    research `38b8e07e` and `60cae5bf` retain exact upstream source pin
    `4ffba15a55f250816598b4e27eb56ca40a699cea`, safe cleanup, and direction-preserving receipts on
    the fixed campaign path.
  - [x] **Port, bind, and repair Xe-Forge.** ✅ 2026-08-11 — research `d76fe4b9`, `af5d026a`,
    `1bd5ec75`, and wrap repair `e31cc8c8` retain exact source pin
    `4dcb5080b0f56d0b655ec8c8c9509b8e3ba0382c`; the real-upstream regression proves AMD-only
    prompts, refuses fabricated shapes, and closes the executor cleanly.
  - [x] **Port KernelFoundry and preserve its governed MAP-Elites/QD behavior.** ✅ 2026-08-11 —
    research `7654383c` plus wrap repair `e31cc8c8` retain exact upstream source pin
    `1c053e02383d12937f144923bcc1faa82fa7788f`, activate 159 missing Triton regexes, and prove a real
    inherited 2x2 fixture with two occupied cells, four programs, two QD transitions, and one
    direction without model, GPU, or inference.
    The selected AutoKernel suite passes 538 tests plus 202 subtests at the repaired tip.
  - [x] **Bind KernelFoundry and produce the final no-execution full-panel audit.** ✅ 2026-08-11 —
    research `58c4e332` through `26ad6178` binds all six available arms and emits a clean physical
    gfx90a refusal at **6/8** before any controller or GPU command. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-final-audits-20260811-Kpg5wU/full-eight-arm-refusal.json`
    carries receipt SHA-256 `3f67b750c99dccbbe45f5c0043c8aa11973c3e014ab3610bb117786f60a79f7f`
    and file SHA-256 `b432fcb802797136444b510618966489529147aac60d73209b0c1ee946231b1d`.
  - [x] **Add and audit the separately governed available-source panel.** ✅ 2026-08-11 — the same
    pinned task, evaluator, identities, and 2h/8h/32h budgets are ready at **6/6**. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-final-audits-20260811-Kpg5wU/available-source-six-arm.json`
    carries receipt SHA-256 `d812b69ce380613bd854dd0d15206c09981899abac11b10234a8f98bb02482b8`
    and file SHA-256 `88101db4f28f909f220acb3bf906f488fe8b4f8e7c307821d325a5542fd4627d`.
    Its authority is availability-conditioned and diagnostic only: it cannot imply an eight-arm
    result, rank partial full-panel evidence, or authorize promotion. No inference ran in the audit.
  - [x] **Run a real KernelFoundry diagnostic smoke and repair the launch boundary it exercised.**
    ✅ 2026-08-11 — v1 found that copied task workspaces lacked the immutable repository import root;
    v2 passed import and two real GPT-5.6 Sol/high calls, then found concurrent branches racing in
    the shared Arena evaluator. Research `f8569112` and `8afd016c` repair both boundaries. V3 passed
    compilation, correctness, and all 4/4 baseline plus 4/4 optimized timing cases under a cleanly
    released MI210 claim. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-kernelfoundry-real-smoke-v3-20260811-Mg6Fl9/smoke-receipt.json`
    carries receipt SHA-256 `cd61675e83040b196a92aa85f2c0bd951f34912bef10a37e1b07f41864f52276`
    and file SHA-256 `9b47fefcb2744392923745385053aa6ee9a8a959102a17acb7eaea079a1be5b1`.
    Its `0.9986680991832163` average speedup is diagnostic and non-rankable, not a campaign result.
  - [x] **Run one-iteration diagnostic smokes for K-Search, Xe-Forge, and GEAK-v1.**
    ✅ 2026-08-11 — all three terminal runs passed centralized compilation and correctness plus
    4/4 baseline and 4/4 optimized timing cases, then released their MI210 claims. K-Search receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-k-search-real-smoke-20260811-tQf7zZ/smoke-receipt.json`
    has receipt/file SHA-256 `6eea9028399635083a6aed7a4d0101aa106cc4393e4225dd768c6f27c23e7704` /
    `74f49b472dcb6b2eed1cef66e706e9471ea67f71c94de7a8ba046e3bcd7520b7`; Xe-Forge receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-xe-forge-real-smoke-20260811-NIffwN/smoke-receipt.json`
    has `a53ef172b42d3fbb6008902a865eac9c884d181a6cc0fc0cc981f9e8aad1ccae` /
    `e82917d9f1f751520317700520f33b7bf62dd372749ef18ce3d822ba5b2806ea`; GEAK-v1 receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-geak-v1-real-smoke-v3-20260811-RJ4UYN/smoke-receipt.json`
    has `0deef125d026625055e77a63270c444101fd96ce5f6f9b2fce433e47b509a229` /
    `a4c30029a38011cfc7ca0b59be1eb826463cc336322db57e7d6b2cdea19d7487`.
    Their near-1.0 speedups are non-rankable smoke telemetry, not comparative evidence.
  - [x] **Complete the Claude/Codex actor-critic diagnostic smoke through its confined actor path.**
    ✅ 2026-08-11 — v1–v4 exposed fenced-JSON parsing, contained absolute-path handling, nested
    sandbox, and Docker-stdin defects. Research `84e2f948`, `dd0daedd`, `da677443`, and `22e60940`
    repair them while keeping the actor in a digest-pinned, read-only-root container with one
    writable workspace bind, dropped capabilities, no-new-privileges, exact teardown, and ephemeral
    auth. V5 completed planner, actor, and critic and reached centralized evaluation, but the worker
    inherited `/usr/bin/python3` without pytest. Its apparent correctness failure and zero timing
    cases are therefore an evaluator-runtime defect, not candidate evidence. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-actor-critic-real-smoke-v5-20260811-2Oo2cJ/smoke-receipt.json`
    has receipt/file SHA-256 `dcb2da77bf691c670b705149bfaec0bf6e8062594cd4297ac3247037da5937fb` /
    `e890240fa4e3e5134c2975f77930bf5a611e3db285dea2f01a9560d5b699d0d3`.
    The cleanly released 457.02 s MI210 claim retained 1,829 samples. Research `a57feba0` then pinned
    the ROCm evaluator Python/package identity and made mismatch a refusal. V6 passed compilation,
    correctness, and 4/4 baseline plus 4/4 optimized timing cases, reporting diagnostic speedup
    `0.9936027407797491`. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-actor-critic-real-smoke-v6-20260811-3hAJir/smoke-receipt.json`
    has receipt/file SHA-256 `5961eef441e487e787310d3bea9d4e57693a8f7a621dff1cc39190d48d952ef9` /
    `816ecc2d60ee48e8b0be3c6fb05ff1d562d7283697f1def9499ce6d0a98a916c`.
    The nested controller receipt has SHA-256
    `fa11ee8162fb6da877358a0c26c67d58d84c75b6c284fe9ee53540bb3673e315`.
    Its cleanly released 158.72 s claim retained 635 samples; the result remains non-rankable.
  - [x] **Refresh the campaign pins to the validated controller trees and repeat both static audits.**
    ✅ 2026-08-11 — clean detached research `6233cd42` binds the actor pin
    `a57feba0`/`e223a9cd26184aff5df7e24ceafebd53dab7cb1ab712a92c4bf82ca7712d9213` and GEAK pin
    `743f59df`/`7418493b4322f1be0df76be21686a6e0d48f43f27e0198a0db55b915f27516a7`.
    The full-panel receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-final-audits-v2-20260811-v6/full-eight-arm-refusal.json`
    has receipt/file SHA-256 `4a13f7d0ba91c2610efae4e51bcf7e0be8661d07657f74fecf9a5ee0a4dab3af` /
    `199e4e129daf561f42d59750a1c2e157da340f433c0fec3abf19cf7c1bd91195` and refuses
    at 6/8 only for external EvoEngineer and ARGUS. The available-source receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-final-audits-v2-20260811-v6/available-source-six-arm.json`
    has `cf8b03df355a8124a1dd668293c1d7d6e839c9f176aebdcd082f073f92ba0581` /
    `625280fb92b678b8a2a24f15f9a87484a2409c0dcb94e32a777e613639f327ed` and is
    ready at 6/6. Neither audit ran a controller or GPU command.
  - [x] **Bind a representative four-task EPYC Arena campaign instead of an add-only proxy.** ✅
    2026-08-12 — research `99fe3014` hash-pins the existing add control plus real
    `attention_llama`, `moe_gemm`, and `dequantize_matmul` task files under the same MI210/gfx90a,
    elapsed-wall-time, 2h/8h/32h, and one-GPU-cell contract. The available six controller arms keep
    their exact implementation/source/license hashes; EvoEngineer and ARGUS remain explicitly
    unavailable rather than receiving namesake substitutes. This is static campaign authority only;
    no controller, model, or GPU command ran.
  - [x] **Re-audit the available-source panel against the current integrated research source.** ✅
    2026-08-12 — the static audit at research `5c8714a1` reports `status=ready`, **6/6** executable
    arms, all four representative tasks ready, a physical `gfx90a` MI210 identity, and the fixed
    elapsed-wall-time 2h/8h/32h budget. It preserves the separate 8-arm refusal for unavailable
    EvoEngineer and ARGUS sources and grants no ranking or promotion authority. Receipt
    `/mnt/raid0/llm/autokernel/probes/inf03-available-source-reaudit-20260812-r1/receipt.json` carries
    self-hash `7c670931628b17a1491d7f25642681f2ee17d996848c0b09032518ad58e08d5a` and file SHA-256
    `e86fbe4a4fb3f45d28d0a9ca7a62be97e021bdf710b5e2f4d7b2287644f0a623`. No controller,
    inference, build, or GPU command ran.
  - [x] **Make the available-source campaign restart-safe before spending the 2h/8h/32h
    budgets.** ✅ 2026-08-12 — research `971e3a00` verifies immutable audit/config/source identity,
    atomically records completed cells and checkpoints, resumes only exact hash-matched terminal
    work, and rejects partial, tampered, in-flight, or claim-leaking state. Focused campaign tests
    passed **139/139**. Resume does not make partial results rankable; the terminal aggregate remains
    the only campaign result.
  - [x] **Repair Arena workspace containment and guaranteed device-claim release before restarting
    INF-03.** ✅ 2026-08-12 — Research `b84c809f` uses collision-bound dot-free cell components,
    rejects dot-bearing ancestor paths, compares exact post-worker cell/sibling manifests on success
    and failure, and defers TERM/INT across claim acquisition so teardown journals the release. The
    focused runner/claim suite passed 68/68 after promotion. The invalid r1 attempt had exposed a
    dotted-path escape: the task's
    `__file__.replace('.', '_')` wrote `test_add_kernel_py.pt` into an adjacent sibling cell tree.
    Reject writes outside the exact workspace after every evaluator/controller step, normalize cell
    paths safely, and release/journal the device claim from a SIGTERM-safe `finally` path. Add
    regression tests for dotted task ids, external writes, and exact-signal cleanup before r2. The
    r2 baseline then completed in the dot-free hash-bound cell without creating an escaped sibling;
    its first controller checkpoint started only after that live containment regression passed.
  - [x] **Enforce the exact planner/critic response schemas at the provider boundary before spending
    another INF-03 checkpoint.** ✅ 2026-08-12 — r2 is immutable and invalid: its baseline completed
    safely, but the first Claude planner returned structurally valid JSON with extra fields that the
    strict four-field parser correctly refused. Research `298bab0c`, pin advances `98f7658f` and
    `6f599ed0`, plus the fresh r3 audit now bind provider-enforced planner and critic schemas without
    weakening the parser. Focused actor/critic tests passed **21/21** and the controller slice passed
    **540/540**. The r3 audit is ready at **6/6** over four tasks with authority still limited to an
    availability-conditioned diagnostic; self-hash
    `b8d966ee7581f2a2fe4ee7e8c2eb7e314514bc4f888f22635dfa23d9ec4ce6dc`.
  - [x] **Stop INF-03 r4 and preserve it only as invalid diagnostic history after auditing its
    intermediate feedback path.** ✅ 2026-08-12 — the captured campaign processes were terminated
    by exact PID and confirmed dead; no MI210 claim remained. The immutable partial root is
    `/mnt/raid0/llm/autokernel/campaigns/inf03-available-source-six-arm-20260812-r4`, bound to manifest
    self-hash `941fece21400362f41772682ec2cf8e3162b08488183a767dce276209ec61eaf`. It retains **5/64
    checkpoints**, **2/24 cells**, **10/10 released** vendor/final windows, 215 samples, and 52.588
    claimed GPU-seconds, but it is not resumable, rankable, aggregatable, or valid controller-comparison
    evidence. KernelFoundry's receipt records 64 intermediate centralized evaluations; the evaluator
    log records 64/64 correctness failures. Those calls ran from the deliberately GPU-blind controller
    environment outside the only two durable claim windows, so the controller received invalid search
    feedback even though its final checkpoint receipt was structurally complete.
  - [x] **Broker every intermediate controller evaluation through the parent worker's exact-PID
    boundary.** ✅ 2026-08-12 — integrated research `70a0d254` + `de7214ee` make the parent own an
    authenticated AF_UNIX broker and every intermediate/final evaluation. The broker verifies the exact
    registered peer PID/start ticks, accepts bounded candidate bytes, and the parent evaluates each
    request in a fresh GPU-capable deny-network subprocess under its own serialized MI210 claim. Neither
    controller nor candidate receives a claim credential. Request/result/baseline, sampler, claim,
    subprocess, activation, and teardown receipts are rehashed during durable restore.
  - [x] **Enforce controller/candidate OS isolation before a decision-bearing INF-03 pilot.** ✅
    2026-08-12 — research `9480a1b3`, `9a17e638`, and `de7214ee` wire every non-baseline Arena cell
    through an exact-read/exec controller sandbox with one inherited peer-bound broker socket, no ROCm
    device access, no campaign-sibling access, cgroup-owned descendants, and durable activation/teardown
    evidence. Candidate evaluation runs separately in a fresh deny-network evaluator sandbox; the parent
    alone owns the claim, sampler, and subprocess. The integrated focused warning-strict suite passed
    **95/95**, the pinned EvoEngineer suite **11/11**, and the pinned controller suite **572/572**.
  - [x] **Exercise the governed one-task/K-Search pilot through its first real Codex request and retain
    every fail-closed attempt.** ✅ 2026-08-12 — research branch
    `integrate/inf03-isolation-merge-20260812` at `569a8c42` added the explicit
    `epyc.autokernel.arena_diagnostic_pilot.v1` authority, a pilot-only one-round K-Search override,
    exact task-source discovery, narrow controller import/runtime/ELF/Git/null-device grants, and a
    workspace-local ephemeral Codex home that is scrubbed during teardown. The immutable probe ladder is:

    | Attempt | First fail-closed boundary | Disposition |
    |---|---|---|
    | r1 | task contract omitted `source_file_path` | fixed by deterministic instruction-task source discovery |
    | r2-r3 | sandbox could not import the controller module at the declared package root | fixed by the exact `scripts/` import root and below-root module identity |
    | r4-r5 | Python extension closure was incomplete (`libffi.so.8`) | fixed by exact extension/ELF dependency admission |
    | r6-r7 | the selected Python environment could not import `yaml` / the pinned Arena evaluator | fixed by binding the governed K-Search Python and exact venv package root |
    | r8 | exact source verification could not start `git` | fixed by admitting the exact executable and ELF closure |
    | r9 | Git could not open `/dev/null` | fixed by admitting only the null device; KFD/render remained denied |
    | r10 | ambient system/global Git configuration paths were denied | fixed by `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null` |
    | r11 | Codex could not initialize under the read-only host `CODEX_HOME` | fixed with an ephemeral, workspace-local auth/config projection that is scrubbed on exit |
    | r12 | the real Codex client started, attempted the response request, retried five times for about 60 seconds, then failed with `Operation not permitted` while sending to the responses endpoint | fixed by binding the exact sandboxed Codex launcher |
    | r13 | the terminal controller path passed, but a stale controller null-device validator rejected its governed `/dev/null` grant | immutable invalid validator attempt; fixed in research `fe33954e` |
    | r14 | the controller path passed again, but a stale evaluator validator rejected the deny-network evaluator's exact device set | immutable invalid validator attempt; fixed in research `aa2020ab` |
    | r15 | one task / one K-Search round completed through six `gpt-5.6-sol:high` calls, one brokered intermediate evaluation, and the final evaluator | terminal compatibility-only receipt; no campaign/ranking/belief/promotion/release authority |

    R1-r14 remain immutable, non-rankable engineering history. R15 is a terminal compatibility pilot,
    not a campaign result: its final ratio `1.0019039030` and brokered intermediate ratio
    `1.0033912745` are diagnostic telemetry only. The terminal receipt is
    `/mnt/raid0/llm/autokernel/probes/inf03-mi210-isolated-k-search-pilot-20260812-r15/diagnostic-pilot-receipt.json`
    (self-hash `3425cf579a9d6fb06f5ed76b480ae652eaed3b3685eec9116299d253528a8771`,
    file SHA-256 `eb53de389450ba6ef800528a0da6f54c8508eabc39b4357f0cd9beff64aacefa`).
  - [x] **Resolve the r12 sandboxed Codex transport denial with least additional authority, then rerun
    the identical one-task/K-Search diagnostic pilot.** ✅ 2026-08-12 — research main `15c61ed5`
    binds the exact sandboxed Codex launcher (`45b82bbc`) and carries the r13/r14 validator repairs
    (`fe33954e`, `aa2020ab`). R15 completed six model calls, non-null brokered feedback, exact
    controller/evaluator activation, three matched claim/release and sampler windows (11/21/21
    samples), scrubbed ephemeral CLI state, empty/removed cgroups, and a terminal receipt. Controller
    access remained `/dev/null` only; both evaluators used deny-network sandboxes with exact GPU
    devices. Full merged validation passed 578 tests plus 202 subtests; footprint/readme checks passed
    106 plus 6 tests.
  - [x] **Project the diagnostic-pilot v1 contract and pre-receipt failure posture into the Kernel-R&D
    dashboard.** ✅ 2026-08-12 — the hub now reads the newest terminal pilot receipt, verifies its
    self-hash and explicit no-authority constraints, and renders PASS, broker/model/evaluation/window/
    teardown facts under a loud no-campaign-authority boundary.
  - [x] **Retract the reported all-tree discovery parser collision after reproducing its exact test
    context.** ✅ 2026-08-12 — `test_live_controls.py` intentionally invokes mutually exclusive
    `--evaluate-existing` and `--execute` arguments inside `assertRaises(SystemExit)`; the argparse
    stderr is the expected assertion surface, not an import-time collection abort. Discovery with both
    strings in `sys.argv` collected **3,927** tests, and an AST sweep found zero module-scope
    `parse_args` calls in AutoKernel. No parser repair is warranted.
  - [x] **Trace and repair one reproducible Claude/Landlock startup failure outside the campaign.**
    ✅ 2026-08-12 — local, unpushed research commit `916cdc92` adds ten fixed volatile read paths,
    stages only Claude credentials/config with identity hashes, scrubs the
    staged config, keeps `/dev/urandom` read-only, and excludes volatile reads from stable identities.
    The bounded standalone Claude probe returned structured `{"ok": true}`, left an empty/removed
    cgroup, and retained activation/result/teardown evidence under
    `/mnt/raid0/llm/autokernel/probes/inf03-claude-sandbox-runtime-20260812-r1`. Focused validation passed
    **59/59**, footprint/README validation passed **106/106**, and the pinned full AutoKernel suite ran
    **5,653** tests with one expected failure and no unexpected failure. Those counts were observed in
    the live session but lack a retained transcript; the probe receipts are the durable runtime evidence.
    This proves the bounded probe, not full actor-critic campaign compatibility.
  - [x] **Preserve r5 and r6 as immutable non-rankable engineering attempts after the exact campaign
    cell falsified the standalone compatibility inference.** ✅ 2026-08-12 — both attempts completed
    only the starting-state baseline, then the first Claude/Codex 2h planner exited `-11` with empty
    stdout/stderr. R6 included all ten new runtime paths and used source `916cdc92`, yet reproduced r5;
    its controller cgroup was verified empty and removed. Neither attempt has an aggregate, controller
    ranking, belief update, proposal-bank entry, champion, or release authority.
  - [x] **Trace r6's exact campaign-versus-standalone differential and repair the process-bound model
    sandbox boundary.** ✅ 2026-08-12 — `/proc/self/*` Landlock rules were bound to the controller PID,
    so its forked Claude child still received `EACCES`. Research `43ba6263` leaves the controller in a
    deny-network broker-only sandbox, launches each read-only model client in its own outbound sandbox
    so `/proc/self/*` binds to the actual CLI PID, preserves the digest-pinned single-writable-bind
    Docker boundary for the Codex actor, and journals model/evaluation receipts through the parent.
    Targeted validation passed **77/77**; the pinned full AutoKernel suite passed **5,655** tests with
    one expected failure.
  - [x] **Refresh the actor pin and preserve r7's pre-execution refusal.** ✅ 2026-08-12 — research
    `a3fcea3c` pins the repaired actor entrypoint. R7 correctly refused the stale prior pin before any
    controller or GPU command; its audit file SHA-256 is
    `45c4ae3dbb563dfebd20715238407b304cdbdd98f96dfc841cae310d2dd017b0` and its receipt self-hash is
    `0f0b9000b4a2647e68db493c751769f4f845db4bce6d089a0aa15d3e10b7cfab`.
  - [x] **Preserve r8 as an immutable partial, non-rankable implementation diagnostic.** ✅ 2026-08-12
    — the 7/7 audit passed and the starting-state baseline completed, but the first actor cell exited
    before Claude inference because the broker-backed controller unnecessarily constructed
    `ArenaWorkspaceEvaluator`, importing unavailable `yaml` and the pinned vendor evaluator inside the
    broker-only Python environment. The controller cgroup teardown is hash-bound, verified empty, and
    removed. R8 has no aggregate, ranking, belief, proposal-bank, champion, promotion, or release
    authority.
  - [x] **Remove the broker-backed controller's unnecessary Arena evaluator import, prove the exact
    Claude cell under the campaign sandbox, then launch a fresh governed 7/7 attempt.** ✅ 2026-08-12
    — research `6270ebc1` keeps vendor evaluation in the parent and `cd1303b9` refreshes the actor
    pin. R9 then exposed a separate broker transport defect: `socket.sendall()` selected denied
    `sendto`, so it stopped before Claude with a verified-empty, removed controller cgroup. Research
    `eb00c411` writes framed requests directly on the inherited descriptor. R10 consequently banked
    the starting-state evaluation and completed the first real Claude planner request, then correctly
    stopped before actor execution when its mutation guard counted the controller's staged session and
    config as task source. The ephemeral state was scrubbed. Research `2525f2f7` separates semantic
    task files from model state and `7b20b5d6` refreshes the manifest pin. R11 completed the first full
    real planner → digest-pinned Docker Codex actor → centralized GPU evaluation → Claude critic
    loop, but was stopped as an immutable non-rankable partial after repeated mechanisms exposed the
    missing feedback seam.
  - [x] **Close r11 without interpreting it and prove measured critic feedback alters the next live
    proposal.** ✅ 2026-08-12 — r12 iteration one compiled and passed 4/4 correctness at
    `average_speedup=0.9967805648538064`; its critic selected `revise`. Iteration two's planner cited
    that exact measurement, forbade the rejected unmasked-fastpath mechanism, corrected the infeasible
    autotune suggestion from the fixed launcher contract, and proposed a distinct shared-offset/
    vectorized-streaming mechanism. It also compiled and passed 4/4 correctness at
    `average_speedup=1.0059084616458236`; the critic selected `accept` while acknowledging that the
    ratio remained inside noise. This proves feedback propagation, not a kernel speedup.
  - [x] **Move host actor-runtime attestation out of the confined controller and pin the repair.** ✅
    2026-08-12 — after all six model calls and three brokered evaluations, r12 finalization failed by
    reopening `/usr/bin/docker` inside Landlock. Research `4b516e9f` makes the parent model-receipt
    chain authoritative for host runtime identity and validates the actual flat model-receipt layout;
    `f316bf31` pins the source. The full AutoKernel suite passed 5,660 tests with one expected failure.
  - [x] **Close INF-03 seven-arm r13 as an immutable partial and identify its confined-runtime failure.**
    ✅ 2026-08-12 — the baseline completed and planner model receipt ordinal `0001` persisted, then
    Claude failed exactly `EACCES: permission denied, mkdir '/mnt/raid0/llm/tmp/claude-1000'` before a
    completed planner response. All captured PIDs are dead and every controller/model cgroup was verified
    empty and removed. R13 has no controller cell receipt or aggregate and is permanently non-rankable.
  - [x] **Repair the confined Claude runtime temp path.** ✅ 2026-08-12 — research `268115ad` refuses
    inherited host scratch for direct model clients, creates a fresh call-scoped directory under the
    governed workspace, binds the relative path plus `ambient_host_temp_inherited=false` into the model
    sandbox receipt, and verifies deletion after every call. The campaign manifest still pins its parent.
  - [x] **Pin `268115ad` and launch a fresh seven-arm attempt.** ✅ 2026-08-12 — research
    `446a1c31` isolates each brokered model call and `152ed0d9` pins that runtime into the campaign.
    Seven-arm r14 audited `ready` at 7/7 on observed clean source `152ed0d9`. A timestamped live
    checkpoint found seven successful, non-timeout model receipts (five Claude and two Codex) and three
    complete parent-owned evaluator windows. Every Claude receipt recorded
    `ambient_host_temp_inherited=false` plus a call-scoped relative temp path, and its captured cgroup was
    verified empty and removed. This proves the r13 capability repair across repeated real calls; it does
    not make the live campaign terminal or rankable.
  - [x] **Close seven-arm r14 as an invalid source-identity attempt.** ✅ 2026-08-12 — after nine
    successful model calls and four correct evaluator windows, the outer checkpoint guard raised
    `task or controller source identity changed during checkpoint execution`. Its audit had bound clean
    source `152ed0d9`, but implementation work advanced that same worktree to `03f9ae69` while the cell
    ran. The actor cell therefore emitted no admitted cell receipt or panel aggregate. All eight device
    claims have released receipts; 14 captured PIDs are absent; and all 12 recorded controller/model/
    evaluator cgroups are verified empty and removed. R14 is permanently invalid and non-rankable.
  - [x] **Close seven-arm r15 as a transient structured-output failure with complete teardown.** ✅
    2026-08-12 — r15 completed the baseline plus four compilation/correctness-4/4 controller-feedback
    windows, then Claude call ordinal `0010` returned non-timeout exit `1` with exact subtype
    `error_max_structured_output_retries` and terminal reason `structured_output_retry_exhausted` after
    five provider-internal attempts. No actor-cell receipt or aggregate was admitted, so r15 is
    permanently non-rankable. All **7/7** device claims released, all **13** captured PIDs were absent,
    every recorded cgroup was empty and removed, and the immutable source worktree remained clean at
    `03f9ae69`.
  - [x] **Add one bounded, receipt-visible retry for exact structured-output exhaustion and refresh the
    campaign pin.** ✅ 2026-08-12 — research `537163d5` retries exactly once only for the recognized
    non-timeout Claude wrapper failure, journals the first and retry attempts separately, and leaves
    arbitrary non-zero exits and timeouts fail-closed. Research `eb1de388` refreshes the actor-critic
    campaign identity to those bytes. The admitted Python 3.12 environment passed the full AutoKernel
    suite: **5,682 tests with one expected failure**. Both commits are pushed and on research `main`.
  - [x] **Preserve seven-arm r16 as a pre-claim source-identity refusal.** ✅ 2026-08-12 — its static
    audit observed the new actor entrypoint but the campaign still expected the pre-repair digest, so it
    refused before controller inference, GPU execution, or device-claim acquisition. The corrected pin
    is `eb1de388`; r16 carries no empirical or comparison authority.
  - **[superseded: inf48-triage 2026-11-09: seven-arm comparison: R18 terminal-noncomplete, non-rankable; the A/B program is replaced by the AutoKernel discovery controller; full text at b3bd883d3:2316]** **(no title)**
    - [x] **Patch the EvoEngineer evaluator-constructor call and launch a fresh immutable successor.**
      ✅ 2026-08-12 — research `381bc55e` wires governed `source_paths` through EvoEngineer, GEAK,
      K-Search, KernelFoundry, and Xe-Forge; `11bccd41` refreshes affected entrypoint pins. Research
      `b0d6f79f` adds prospective intermediate evaluator belief rows and strict feedback-only reading.
      Fresh r18 was sealed at `17b9208d`; its later terminal disposition is recorded below.
    - [x] **Close seven-arm r18 as a staged-host-input identity failure without upgrading its measured
      partial.** ✅ 2026-08-12 — r18 completed the baseline and full Claude/Codex 2h loop, including
      four compile/correctness-4/4 candidate evaluations, but the outer parent re-hashed mutable host
      `~/.claude/.claude.json` after its bytes had already been copied into the scrubbed workspace.
      That host file changed during the multi-minute cell, so admission failed after controller exit.
      No actor-cell receipt or aggregate was admitted; r18 remains permanently non-rankable and is
      recorded in the dashboard disposition overlay under exact attempt id `21754d23…`.
    - [x] **Bind staged controller inputs at copy time and launch a clean immutable successor.** ✅
      2026-08-12 — research `0b1fdbe9` verifies the source hash immediately before copying, verifies
      the staged bytes, emits `epyc.autokernel.controller_staged_inputs.v1`, and validates the receipt
      instead of reopening a later-mutated host credential/config file. The controller suite passed
      **596 tests**. R19 is live from clean exact source `0b1fdbe966f338a8ac840c9961eb718528af1a0f`
      at `/mnt/raid0/llm/autokernel/campaigns/inf03-available-source-seven-arm-r19-20260812`; its audit
      is ready 7/7, baseline is complete, and the first actor cell is active.
    - [x] **Specify the safe controller-overlap architecture before enabling it.** ✅ 2026-08-12 —
      research `dfe265a1` defines immutable schedule order, isolated deterministic lanes, serial
      per-lane checkpoints, exact MI210 claims around evaluator windows, bounded claim waits, an
      inherited attempt lease, PID/start-tick cancellation, manifest-v3 validation, truthful observed
      overlap, and a required overlap A/A noise gate. This is a design/verification contract only:
      overlap remains disabled, and r19 intentionally retains the proven sequential runner.
    - **[superseded: inf48-triage 2026-11-09: controller-overlap successor to the dead r4-r19 comparison; replaced by the discovery controller's own lane/claim handling; full text at b3bd883d3:2347]** **Implement and validate deterministic controller overlap for a post-r19 successor.**
  - [x] **Narrow INF-03 MI210 claims to the centralized evaluator's actual GPU windows.** ✅
    2026-08-12 — research `e6c7aab6` and the r4 manifest bind
    `controller_deliberation_holds_no_gpu_claim=true`, a GPU-blind controller environment, claims
    only around vendor/final measurement windows, exact complete-checkpoint resume, and signal-safe
    release. The audit observed no KFD PID or active device claim while KernelFoundry deliberated;
    other governed GPU work may use those intervals.
  - [x] **Obtain and execute the exact licensed EvoEngineer source through the governed adapter.** ✅
    2026-08-12 — research `f42b3540`, `7e915831`, and `a81c2692` pin MIT source commit
    `1649715a975b9022c84b5279c88aaef0b73b28dc`, preserve the historical EvoEngineer-Full loop and its
    four ordered fallback semantics, and exercise the exact upstream `EvoEngineer.run()` for 10
    generations / 40 samples with fixture model/evaluator bridges only. The fresh physical static audit
    at `/mnt/raid0/llm/autokernel/probes/inf03-isolation-available-source-reaudit-20260812-r3/receipt.json`
    is ready at **7/7** over four tasks with zero controller/GPU commands (self-hash `5fa93695…`, file
    SHA-256 `082d977f…`).
  - **[declined: ws58 2026-11-03 content-review: blocked on acquiring a licensed third-party release with no plan; a namesake port is explicitly not it]** Obtain the exact licensed ARGUS source release, then port its real controller policy through the
    same governed adapter contract; a namesake substitute is not admissible. Until then the separate
    full 8/8 panel must refuse, while the 7/7 available-source panel remains diagnostic-only.
- [x] **GEAK-family freshness sweep completed ✅ 2026-08-03** (research-intake Stage-2b): GEAK v4 retains a current gfx90a KB (`perf_knowledge/hardware/cdna2_mi200/`, `updated: 2026-06-08`) and 40 gfx90a capability entries; all published evaluation remains gfx942. Scoping caveat amended above; "677/678/679 are a coverage regression" **retired** — for GEAK proper it is unpublished coverage. `v1.0.0 @ 4ffba15a` pinned.
- [x] Register **ARGUS** (arXiv 2604.18616) as a controller candidate alongside EvoEngineer /
  KernelFoundry / K-Search / Xe-Forge / GEAK ✅ 2026-08-11 — `arena_adapter.py` registers the
  `argus` controller id under the same exact three-argument bridge and prompt-hygiene contract as
  the other arms. This records registration only; the cited MI300X result remains vendor evidence.
- [x] Read GEAK's `landscape/` + `languages/` sections as an external check on our seven-school
  taxonomy ✅ 2026-08-11 — current GEAK `5107c7e4` showed that “seven schools” was never a durable,
  enumerated fact. The corrected comparison is seven *abstraction families*, recorded in the
  [deep-dive sweep](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md#sweep-2026-08-11--landscape--languages-taxonomy-check-closed).
  The live gfx90a ladder is Triton → TileLang → HIP/C++ → MFMA/ISA when measurement justifies each
  descent, with CK/CK-Tile/rocWMMA as baselines. FlyDSL is a valuable new vocabulary source but GEAK
  scopes it to gfx942/gfx950, so it is not a current MI210 execution arm.
- [x] Add `-mllvm --amdgpu-unroll-threshold-local=600` to the build-flag checklist as a
  **precondition of any ROCm 7+ upgrade** ✅ 2026-08-11 — the new
  [ROCm upgrade checklist](../../docs/runbooks/rocm-upgrade-checklist.md) requires Linux builds to pass
  the option through `CMAKE_HIP_FLAGS`, proves it reached HIP compile commands, and retains it unless
  an exact-toolchain matched A/B shows it unnecessary. This does not alter frozen v9 or ROCm 6.2.


> **MERGE NOTE 2026-08-12 (coordinator).** The two sides of this section disagreed on FACT,
> not formatting, and I preserved both rather than picking. The 2026-08-11 side records the
> LDS bank/phase solver as RUN with a receipt (32 banks, 8 phase cliques, SHA-256
> `ae1d833c704bdae9a78767d0fc0b927298d6d1dfdb31a0ea11c34058dc525987`); the 2026-08-12 side
> records `rocprofv3` as ABSENT and questions whether the solver's counters are reachable
> at all. If the receipt is real the question is answered; if the receipt came from a
> different path than the solver row describes, the row is mis-stamped. **OWNERS: verify
> and correct — I did not adjudicate this.** The profiler row below is the NEWER
> 2026-08-12 re-verified-live text, deliberately preferred over the 2026-08-11 inherited note.


#### Auto-kernel revival — research-intake integration 2026-07-22 (C5 seed corpus + FP8 authoring target)
_Via /research-intake Stage-2 (intake-884 HyRA MI210 re-check). The loop AUTHORS gfx90a kernels — these are task specs, not port-or-decline artifacts._
- [x] Seed C5 with the HyRA sol_execbench kernels as reference specs the loop authors gfx90a kernels FROM (maps onto this handoff's "seed EPYC ops: attention / MoE-dispatch / dequant"): 5 bf16/fp16 Triton kernels directly (k138 mamba, k145 hyena, k154 chunk-gated-delta linear-attn, k175 MoE dispatch, k228 MLA paged-prefill); CUDA-lib-bound winners (k215 GEMM/flashinfer, k225/k227 GQA/MLA) as reference targets to re-author. All Hopper-autotuned + NVIDIA-only-attested -> loop re-authors + re-attests on gfx90a (wavefront-64/MFMA/LDS) ✅ 2026-08-11 — `c5_seed_corpus.{json,py}` pins all eight artifacts to Hyra-results commit `26ebfbe7`, separates the direct and CUDA-bound sets, excludes Hopper scores/latencies from authoring context, and lets Arena tasks select exact rows through `c5_seed_ids`.

---

#### Loop engineering — controller experiments and prompt hygiene (research-intake Stage-3, 2026-08-10)

_Via `/research-intake`. Source: an operator-supplied field note on running a coding-agent research
loop against a batched linear-algebra kernel to competitive results._

**Provenance, stated once and carried by every item below.** The note's loop-engineering claims —
that raising the planner's reasoning-effort knob lengthens search rather than deepening any single
answer, and that a proximate numeric target changes what the agent proposes — have **zero primary
backing**: the accompanying repository does not contain the loop, the transcripts, or any ablation.
They are `[unverified]` **hypotheses** and no number from them may be quoted as evidence anywhere.

**Operator steering, verbatim (2026-08-10):** *"zero primary backing doesn't mean we can't reason
about the potential usefulness of this information from first principles."* That is the governing
instruction for this section. The unverified contract governs **citation**, not **consideration** —
so each hypothesis below is evaluated on our own stack and paired with the cheapest experiment that
would settle it here. Nothing is blocked: frontier Anthropic/GPT models are available to our
planners (operator, 2026-08-10 — we are not restricted to local models), and every experiment in this
section costs **zero GPU and zero local inference**.

- [x] **AK-PL-1 — Prompt-leak guard on the assembled authoring prompt.** Grep the fully-rendered
  planner/actor prompt for `test-backend-ops`, `max_nmse_err` and `init_tensor_uniform`. An agent that
  can read the tolerance it must clear is being graded by a rubric it holds.
  **Test the guard against the COMPLIANT path too** — a guard that also rejects the legitimate prompt
  is a guard that will be disabled the first time it fires
  (`feedback_guard_must_not_forbid_its_own_idiom`). Pairs with RVP-C6-7 in
  [`rocm-verify-profile-backend.md`](rocm-kernel-authoring.md#track-rocm-verify-profile-backend), which filters the *diagnostics*
  half of the same channel. ✅ 2026-08-11 — `controller/authoring_contract.py` scans the fully rendered
  prompt for all three named internals plus the exact `ERR = value > tolerance` disclosure shape;
  tests plant every leak and prove an ordinary compliant authoring prompt remains admissible.
- [x] **AK-PT-1 — Per-turn productivity accounting (this handoff owns it; emitted at
  `autokernel-research-loop.md` §8.8).** Record `(turn, task, correct?, speedup)` per refine turn, and
  split **rescued** (a turn that fixed a previously-failing candidate) from **persistent** (a turn
  that improved an already-correct one). We currently measure **neither**. The reason the split is
  load-bearing: mean speedup falls across turns as a **composition** effect — later turns admit
  candidates that earlier turns could not fix, which are systematically worse — so a declining mean is
  not evidence that refinement stopped working, and reading it that way would truncate the loop
  exactly where it is still paying. ✅ 2026-08-11 — AutoKernel `turn_productivity.py` implements an
  immutable append-order archive with state-continuity checks; rescued/persistent/failed/regressed is
  mechanically derived from the correctness transition, incorrect turns cannot carry a speed rank,
  and every observation retains its evidence reference and content hash. AK-X-6 is its first consumer.
- [x] **AK-LE-0 — Implement the static experiment contracts and selected-task-safe scaffold for
  AK-LE-1/2/3.** ✅ 2026-08-12 — research main `51742ebd` integrates the effort/persistence,
  proximate-target, direct-implement, split-implement, and split-exploit arm contracts. Every scaffold
  consumes the same independently SHA-256-bound selected-task artifact; planner-only `PROPOSE … do
  not implement it yet` text is excluded. The accepted full AutoKernel suite passed **5,464 tests
  with one expected failure**. This closes static wiring only; AK-LE-1/2/3 remain open until their
  budget-matched model runs produce empirical results.
- [x] **AK-LE-1 — Reasoning-effort × search-persistence experiment.** Hold champion, retrieval context
  and PROPOSE prompt fixed; sweep only the planner's effort knob. Measure **search** outcomes, not
  answer quality: count of novel non-duplicate hypotheses, count of explicit "this is already
  optimized" terminations, and how many proposals survive the pre-filter.
  - **Why this is not already covered.** [`reasoning-effort-levels.md`](context-and-token-economy.md#track-reasoning-effort-levels) is
    a **stub**, and its entire measured evidence (the A4 / GPQA-Diamond ladder, +32.0 pp at 4.0×
    tokens) is about *answer accuracy on a fixed question*. Nothing in it measures whether more effort
    makes an agent keep looking. That is a different dependent variable.
  - **Pre-register the direction before running.** Our own observed planner failure is the *opposite*
    one — halting after a single critic "revise" — so the sign must be predicted in advance rather
    than read off the result. Its per-model invariant applies here too: effort is a property of a
    (model, quant) pair and is never inherited. ✅ 2026-08-12 — the corrected r3 panel completed all
    **8/8** predeclared Claude Opus 5 / GPT-5.6 Sol × high/xhigh × control/target cells, then the
    source-pinned structural reducer emitted one planner receipt and **32** prospective belief rows.
    Higher effort did not increase novel/surviving counts in either control arm (Claude `6→6`, Codex
    `3→3`) and all four xhigh cells took longer. This is a bounded null result for the predeclared
    control contrast, not a model-wide effort claim: there is one observation per cell and no
    scaffold or campaign-ranking authority. Evidence:
    `/mnt/raid0/llm/autokernel/campaigns/ak-le-planner-20260812-r3/planner-reduction.json`, file
    SHA-256 `c24122893acdd7cf10f042a447d7daa41aeb7d77161dcda8b5b5bf5344b57791`.
- [x] **AK-LE-2 — `proximate_target` arm, run as one extra arm on AK-LE-1.** Tests the effort × target
  interaction jointly rather than as a second study. **Specify it as a rendered planner-context line
  only — never a manifest field a gate can read** — regenerated each round and scoped **per cell**.
  AK-D3 demoted a percentage figure from trigger to readiness signal for sound statistical reasons
  (threshold peeking, winner's-curse inflation); a target that any gate can read re-introduces exactly
  that, one layer up. The rendered-context form gives the planner the steer without giving the
  evaluator the number. ✅ 2026-08-12 — r3 rendered the decode target only as planner context and
  reduced the complete matched panel. Claude produced `6` surviving hypotheses in every arm; Codex
  target arms produced fewer than their matched controls (`3→1` at high, `3→2` at xhigh). No cell
  emitted an already-optimized termination. The honest result is null for Claude and mixed/adverse
  for Codex on this single panel; it does not establish a transferable proximate-target benefit.
- [x] **AK-LE-3 — Split *implement* from *exploit* as two prompt roles on the SAME model first,
  budget-matched in wall-hours, before any multi-model A/B.** The note's four-role split
  (explore / critique / implement / exploit) is a runnable design, but the delta from our current
  two-role planner may be small, and a multi-model comparison would confound scaffold with model.
  **Vary scaffold and model independently** — published evidence has identical models inverting rank
  under different scaffolds.
  - **What is already reusable (inventory, operator steering: "what could be repurposed of our current
    design").** AutoPilot already runs a two-role draft + critique planner with a **binding** critic —
    that is `explore` + `critique` in place, and it is the half that usually costs most to build.
    [`architect-model-selection-bench.md`](model-evaluation-queue.md) already selects a model
    per role, but on **quality**, never on throughput — the per-role choice machinery exists and its
    objective is the missing piece. AgentKernelArena's `@register_agent` adapter pattern (Decision
    Snapshot item 2) is the substrate for registering the arms. So the increment is roles 3 and 4 plus
    a throughput-aware selection objective, not a new controller.
  - [x] **Implement a governed same-model direct-implement versus implement-then-exploit
    authoring/evaluation seam before running this panel.** ✅ 2026-08-12 — research `c4434810` and
    `230721b6` compile the exact two-model × two-scaffold panel, use the same writable Codex actor and
    trusted Arena evaluator in every cell, isolate disposable baseline/candidate worktrees, bind
    runtime/image/import identities, serialize MI210 claims, and clean up exact owned worktrees on
    every exit. The focused integrated slice passed **29/29** and the controller suite passed
    **512/512**. The following terminal campaign closes the parent experiment.
  - [x] **Run and reduce the governed same-model scaffold panel.** ✅ 2026-08-12 — all **4/4**
    gpt-5.6-sol/terra × direct/split cells compiled, passed all four correctness cases, retained four
    valid baseline and four optimized timing cases, and released their MI210 claims. Average speedup
    was Sol direct `0.9957477195`, Sol split `1.3930213301`, Terra direct `1.0021830618`, and Terra
    split `0.9935661224`. The split benefit is therefore task- and model-specific, not a cross-model
    scaffold default. The panel has diagnostic observation authority only: it cannot rank a campaign,
    choose a champion, or authorize a release. Receipt:
    `/mnt/raid0/llm/autokernel/campaigns/ak-le-3-scaffold-20260812-r1/panel/panel.json`, self-hash
    `6e764cca1df8cf347d43c48bca70654f1cec4dddbe967e7e80a3705c3d71ff32`, file SHA-256
    `5af0307ffd823e093d06d26497a536e414090d72e3dee73bf3c33f4ea853e666`.
- [x] **AK-LE-4 — Context discipline: a priced context budget and a reversible compaction protocol.**
  (a) A per-round context-budget table with an explicit **never-bulk-read** rule, so the loop cannot
  spend its window on a file it will not use. (b) A research-log compaction step that writes a
  **what-was-kept / what-was-dropped header** — and, critically, **a git recovery recipe**. The source
  note describes the compaction and omits the recovery half; compaction is only safe *because* it is
  reversible, and a protocol that drops the reversibility keeps the risk and discards the mitigation.
  ✅ 2026-08-11 — the authoring contract prices every context item and round, enforces per-item and
  total caps, rejects duplicate/bulk reads, prints the budget table and literal never-bulk-read rule,
  and emits kept/dropped compaction headers with an exact `git -C <repo> show <commit>:<path>` recovery.
- [x] **AK-LE-5 — Anti-fabrication clause for externally-sourced numbers.** Our invariants
  (`autokernel-research-loop.md` §4) bind the loop's own measurements to a protocol, an anchor and a
  receipt. **Nothing currently covers a number the loop claims came from outside itself** — a vendor
  figure, a paper result, a leaderboard score quoted into a proposal. Require an external number to
  carry a source, a retrieval date or commit, and a normalisation to roofline utilisation (§8.3.1)
  before it may appear in a proposal at all; otherwise it is not admissible even as `design_prior`.
  The source campaign logged this exact failure three times in its own write-up, which is the only
  part of that document that is self-evidencing. ✅ 2026-08-11 — proposal-v3 now requires a validated
  `external_numbers` vector (empty is explicit). Every entry binds source, retrieval date or commit,
  exact quant, denominator basis and normalized roofline utilization; the validator independently
  re-derives utilization and refuses mixed unit/quant/basis denominators.

**Declined here (recorded so it is not re-derived):** adopting the note's evaluation cadence. It rests
on elastic external accelerator capacity and a free third-party adversarial verifier; we have one
MI210 and a verifier we own. **The orchestration is reproducible almost fully; the cadence is not** —
and per AK-LN-1/AK-LN-4 in [`autokernel-research-loop.md`](autokernel-loop.md#track-autokernel-research-loop) §21, our
answer to cadence is concurrent screening lanes, not more devices.

#### Research Intake Update — 2026-08-15 (SOL-ExecBench as a gfx90a correctness oracle; intake-1102)

The Stage-2 dive settled the C5 provider question, and the answer is more useful than the headline
suggests. **State it in two parts or it misleads.** The ROCm port carries *no measured constants* for
gfx90a — it is gfx950-only (MI350X/MI355X), pinned to ROCm 7.2 against our 6.2. **That is not the same
as unusable here.** Its compile path is genuinely architecture-agnostic (the gencode helper falls back
to reading `gcnArchName` from torch and would emit `--offload-arch=gfx90a`, and a `LOCAL` hardware
target exists for exactly this case), so **compilation and correctness checking run on our MI210
today**. Only SOL *scoring* needs a port, because T_SOL, T_b and tolerances are per-part measured
quantities.

All eight C5 seeds resolve to real definition/workload/reference/tolerance/bound records — 193
workloads, all scoreable and zero deferred. The port's actual k145 oracle workload/tolerance surface
is fp32, while HyRA candidate metadata names fp16; k227 is bf16-only. The provider deliberately keeps
oracle-workload and candidate-metadata identities separate rather than repeating the earlier
"all bf16/fp16" conflation.

- **[superseded: inf48-triage 2026-11-09: gfx90a correctness oracle now exists as scripts/kernel_rnd/autokernel/c5_rocm_oracle.py (+ test_c5_rocm_oracle.py) on research main; full text at b3bd883d3:2629]** **C5-3 — Use the port as a gfx90a CORRECTNESS ORACLE now, ahead of any bound port.**
  - [x] **C5-3a — Implement the sealed gfx90a correctness-only provider.** ✅ 2026-08-16 — research
        `5f1b645c0c5034137e298c1dc9732beee9742547` adds LOCAL/gfx90a planning, exact source/runtime/
        workload identities, ten fresh live-reference rounds, and `scoring.enabled=false`; later
        hardening binds source staging and complete raw-result reduction. No live 193-workload run
        occurred, so the parent C5-3 empirical task remains open.
- [x] **C5-5 — Persist the kNNN ↔ problem-slug mapping into `c5_seed_corpus.json`.** All eight resolve
      uniquely with matching ordinals (k138→`L2__044_mamba…`, k145→`L2__051_…hyena…`,
      k154→`L2__060_chunk_gated_delta_rule…`, k175→`L2__081_moe_sparse_expert_dispatch`,
      k215→`FlashInfer-Bench__006_gemm_n2048_k4096`, k225→`FlashInfer-Bench__016_gqa_ragged_prefill…`,
      k227→`FlashInfer-Bench__018_mla_paged_decode…`, k228→`FlashInfer-Bench__019_mla_paged_prefill…`),
      with workload counts reproducing exactly (16/16/16/16/29/15/47/38 = 193). **The kNNN ids appear
      nowhere in either repository** — they are HyRA's — so this join is ours to maintain and should
      stop being re-derived. Add it as a `sol_execbench_problem_id` field. **2026-08-16 checkpoint:**
      `c5_seed_corpus.json` is now tracked, but exact problem IDs still live separately in
      `c5_rocm_oracle.json`; the requested joined field remained open at that checkpoint.
      ✅2026-10-06 — [MAIN source/native acceptance](../../artifacts/ni08/c5-seed-provider-join-20261006/README.md): exact persisted eight-way join, unchanged193 workloads/dtypes, original27/27 controls and byte-identical Research publication. Exact historical policy bytes are recovered; versioned default-verifier path restoration remains separate source work.

##### OPERATOR DECISION — port the SOL bound constants to gfx90a?

This is the one item that needs MI210 GPU time and therefore a region claim, so it is presented rather
than filed. The port is **bounded and signposted** — the source's two refusals name their own remedy,
and its own MI355X runbook is effectively the checklist: add an MI210 `Part` entry (spec-sheet peak
clock + power cap), measure `F_LOCK` on gfx90a (they ship the task for it), add a measured `gfx90a`
`LLC_BYTES` (do NOT fall back to torch's reported L2 — it reports the per-XCD L2 and would undersize the
cache flush ~64×, making every memory-bound kernel look faster than it is), regenerate the SOLAR arch
YAML with the parametric generator, then re-measure T_b and tolerances.

**Scope it by bound quality, not by seed count.** Because four of eight seeds are vacuous, the honest
target is **k215 alone at 29 workloads** for a bound worth optimizing against, or ~77 workloads if
k138/k145/k175 are included at loose quality. Not 193, and certainly not the full 3,717.

| Option | Buys | Costs |
|---|---|---|
| **A. No bound port** | Correctness oracle (C5-3) + PyTorch-relative speed. Zero GPU time. | No speed-of-light measure on any seed. |
| **B. Port k215 only** | One genuine SOL-scored seed at 6.8× headroom. | F_LOCK + LLC measurement + T_b/tolerance re-measure over 29 workloads. |
| **C. Port k215 + the three loose seeds** | Four scored seeds, three of them loose. | ~77 workloads; the loose three yield weak roofline content. |
| **D. Full eight-seed port** | — | 193 workloads, four of which produce vacuous scores by construction. Not recommended. |

**Recommendation: B**, after C5-3 has shown the correctness oracle works end-to-end on gfx90a. A is a
legitimate stopping point if GPU time is scarce — the correctness half is where the C3/C5 provider gap
actually was.

#### Research Intake Update — 2026-08-21 (Hawkeye / agentic-kernel cohort; intake-1218..1236)

_Via `/research-intake` Stage-4, operator-approved plan. Nine dives, 18 dive-verified entries. Two
corrections to earlier framing carried in deliberately, because both were repeated in briefs during this
session before primary source overturned them: **C4 is CLOSED** (✅ 2026-08-11, taxonomy closed, risk MED)
and nothing here reopens it; and **"GPU Kernel Scientist is gfx90a prior art" is FALSE** — it targets
MI300/CDNA3 and never mentions MI210, MI250, CDNA2 or gfx90a. The related "one of only two systems
targeting HIP for AMD" framing is an index-internal assertion, NOT-FOUND-IN-SOURCE, and should be struck
wherever it appears._

- **[superseded: inf48-triage 2026-11-09: controller-A/B arm; A/B program superseded by the AutoKernel discovery controller; full text at b3bd883d3:2698]** **C5-6 — Add a ZERO-PROFILER null arm to the controller-authoring A/B on gfx90a.**
- **[superseded: inf48-triage 2026-11-09: counter-gated acceptance now carried by RVP-CTR-1 and C5-ISA-1 (live set item 6); full text at b3bd883d3:2709]** **C5-7 — Adopt COUNTER-GATED acceptance for agentic gfx90a kernels.**
- **[superseded: inf48-triage 2026-11-09: controller-archetype roster entry for the dead A/B program; full text at b3bd883d3:2717]** **C5-8 — Register two new controller archetypes on the adapter roster.**
- **[declined: ws58 2026-11-03 content-review: merged into C5-9a (falsify the load-bearing unknown first; the trial follows only on a pass)]** **C5-9 — Trial MANUAL-CORPUS hardware-factor extraction as a third, profiler-free supervision
      source.** Point an LLM extractor at the public AMD CDNA2 ISA reference and MI200/MI210 tuning guides
      to populate a four-slot factor schema (memory hierarchy / instructions / vector+scalar registers /
      CU-SIMD-LDS-matrix-core), then A/B the resulting hint block against our existing static constraint KB
      on the hash-pinned k228 attention and k175 MoE cases. From `intake-1234#record`, and it is the ONLY
      hardware-grounding step in that entire five-paper line whose ACQUISITION IS AUTOMATED rather than
      hand-authored — pointing it at AMD manuals is the same operation the paper performs on the XuanTie
      manual. Complements, does not replace: CudaForge (intake-662) still owns the counter-SELECTION method,
      IntelliPerf (intake-1223) hands us the counter LIST. Bonus axis: the same mechanism would transfer to
      our EPYC 9655 CPU-kernel work via Zen5 optimization manuals, which no other cluster entry offers.
      **Clean-room only** — that framework is unreleased AND unlicensed.
  - **[superseded: inf48-triage 2026-11-09: child gate of C5-9, an A/B-program variant; superseded with it; full text at b3bd883d3:2736]** **C5-9a — Falsify the load-bearing unknown behind C5-9 BEFORE investing in it.**
- **[superseded: inf48-triage 2026-11-09: controller-A/B arm variant; superseded by the discovery controller; full text at b3bd883d3:2742]** **C5-10 — Trial the LLM-TL sketch scaffold on the HIP arm.**
- **[superseded: inf48-triage 2026-11-09: ablation protocol for the dead controller A/B; superseded; full text at b3bd883d3:2750]** **C5-11 — Fix the ablation protocol before running any controller A/B.**
- **[superseded: inf48-triage 2026-11-09: token-cost levers for the dead controller A/B; superseded; full text at b3bd883d3:2759]** **C5-12 — Adopt two token-cost levers, and one falsifiable prediction to test cheaply.**
- [x] **C5-13 — Record the DECLINE of a gfx90a taxonomy column, with its cost census as the ✅ 2026-10-29 (audit: handoffs/active/agentic-rocm-kernel-authoring.md:1030-1043 the decline is recorded in the box body with the a226e955 cost census (108 files, ~17,012 lines) and revisit condition; box is a record-only task) [no-belief: audit-reconciliation]
      justification.** A dive proposed authoring one; a later, better-evidenced dive of the same project's
      source measured what it actually costs and the decline wins. Census at `a226e955`: the cdna4 column is
      40 unit-test files (4,241 lines) PLUS a 68-file / 12,771-line abstractions library = **108 files,
      ~17,012 lines**, and the AMD column is the LARGEST of the four architectures — porting to a new VENDOR
      costs MORE, not less. Worse, the repo's own EASIEST cross-arch move (ampere->hopper: same vendor,
      adjacent generation, features added not removed) retained only **6.9% of abstraction lines and 11.4% of
      unit-test lines**, and is the port that silently corrupted agent context (its `AUDIT_FINDINGS.md` A-1,
      HIGH: Blackwell-only ISA left in A100/H100 guides). gfx950->gfx90a REMOVES features, so 7-11% is an
      OPTIMISTIC upper bound. One cell (`02_quantized_precision`) has no gfx90a meaning at all — gfx90a has
      no FP8 — and would need re-specification, which is a taxonomy decision rather than a coding task.
      **The STRUCTURE ports for free; the CONTENT does not.** Revisit only if a gfx90a kernel-authoring
      campaign is separately funded.

#### Research Intake Update — 2026-08-21 (Stage-2b second wave: controllers, and what documentation scarcity costs)

_From `intake-1246#record` (AutoKernel), `intake-1244#record` (CodegenBench), `intake-1249#record`
(KLineage), `intake-1250#record` (Kernel-Smith), `intake-1240#record` (GPU Forecasters)._

- [x] ✅ 2026-11-01 [belief: cc] Evidence: epyc-inference-research `a23bd9c65203c9e8a9cbf7cabd76b716a9303d49`; artifact `scripts/kernel_rnd/autokernel/controller/ARENA_INTEGRATION.md`; docs-only `git diff --check` passed. **C5-14 — Add AutoKernel to the controller roster as the ONLY surveyed kernel controller that needs
      no vendor profiler.** `intake-1246#record` (MIT, `github.com/RightNow-AI/autokernel` @ `78435821`,
      1,531 stars): Phase A uses **`torch.profiler` with shape recording only** — zero `ncu`/`nsys` in paper
      or code. Our environment has rocprof v1/v2/v3 and omniperf and specifically **NO ncu/nsys**, which has
      been the standing blocker for importing every NVIDIA-native agent, so **Phase A would run on the MI210
      unmodified**. It is also **train-free and model-agnostic** (BYO coding agent reading `program.md`), so
      it composes with our existing roster. **HARVEST:** the Amdahl-ranked target selector with explicit
      move-on criteria (plateau / peak utilisation / time budget / speedup threshold), the
      fixed-evaluation/mutable-single-file invariant, and the five-stage gate ORDER (smoke → shape sweep →
      stability → determinism → edge cases), which is cheap-first and arch-independent. **DO NOT HARVEST:**
      the hardware spec DB (see AK-PM-15 — it fabricates a gfx90a roofline), playbook tier 3 TF32
      accumulation (no TF32 on gfx90a), tier 5 (TMA/cp.async do not exist on CDNA2), or the CUDA C++ backend.
      Use FlashInfer-Bench's tolerance policy (RVP-C6-23), **not** AutoKernel's 1e-2/2e-2 blanket, which is
      loose enough to admit an accumulator downgrade on the fp16/bf16 arms — the more so because its own
      playbook tier 3 sanctions changing accumulator precision as an optimization.
- **[superseded: inf48-triage 2026-11-09: controller-A/B design candidate; superseded by the discovery controller; full text at b3bd883d3:2805]** **train-free**
- **[superseded: inf48-triage 2026-11-09: controller-A/B context variant; superseded by the discovery controller; full text at b3bd883d3:2820]** **0.74**
- **[declined: ws58 2026-11-03 content-review: a rule for a performance predictor nobody is building; the trained artifact is already declined]** **C5-17 — Adopt ordinal binning and calibration-as-a-gate for any performance predictor we ever
      build, and decline the trained artifact.** GPU Forecasters v1 (`intake-1240#02`, `intake-1240#03`, `intake-1240#04`; `dive-1240/source.txt:L86,L131,L148`) says fine-grained numerical inference is difficult without execution; it does not establish that numeric prediction is impossible or that ordinal output is the only tractable method in general. Keep forecast accuracy separate from calibration: the tested RL rewards reduce ECE while increasing numerical forecast error, and the six-task search records three surrogate wins, one tie, and two surrogate losses to the baseline (about 5% and 7%). Preserve the existing ordinal reward shape, ECE or Brier as an ACCEPTANCE gate, and explicit DEFERRAL to real gfx90a measurement. Decline the trained forecaster: it is A100-conditioned, and the reviewed paper supplies no cross-GPU transfer test despite its dataset spanning three GPU types; no gfx90a transfer is established. Any future comparison needs the equal-budget baseline arm alongside, never a single-arm demo. Preserve **Note-the-method-do-not-build-yet** while the loop is not trustworthy and RVP-C2-8/C2-9 are open.
      **Clause (2026-10-21): decision-level rank agreement on the deployment distribution.** A surrogate acceptance report also states rank agreement (Kendall tau or top-1) between surrogate-chosen and measured-chosen candidates on held-out recorded rounds, because prediction accuracy alone did not certify play quality; the held-out rounds for that check include candidates the planner chooses under the surrogate (the deployment distribution), not only uniform samples (`intake-2233#record`, `intake-2263#record`; the game domain is a mechanism, not evidence about kernels). Document edit only; no surrogate is built.

##### Recorded so it is not re-derived — a pattern, no longer an incident

**"SUPPORTS PLATFORM X" IN THIS LITERATURE IS A CAPABILITY STATEMENT WITH NO EVIDENTIARY CONTENT.** Two
independent papers now ASSERT cross-platform capability and never MEASURE cross-platform transfer:
`intake-1087#record` (KForge) names cross-platform translation as an optional strategy and never ablates it;
`intake-1250#record` (Kernel-Smith) runs a MetaX MACA arm in which a **separate model was trained, the task
formulation changed and the benchmark changed** — so nothing measures what knowledge crossed the vendor
boundary. Treat such claims as unevidenced until an ablation is shown.

**METHOD TRANSFERS, TRAINED ARTIFACT NEVER DOES** — now well enough evidenced to state once rather than
re-derive per intake. `intake-1222` (KernelPro), `intake-662` (CudaForge) and `intake-1240` (GPU Forecasters)
all evaluate on one NVIDIA family and ship artifacts that cannot cross to gfx90a. Every number we would ever
produce from an NVIDIA-measured corpus on gfx90a is a **RE-MEASUREMENT, never a transfer** — the KLineage and
daVinci authors are themselves explicit that they do not claim cross-vendor skill transfer, and we must not
claim it on their behalf.

**LICENSING BLOCKERS to clear BEFORE any download** (open-source-self-hosted-only sourcing policy):
`github.com/GAIR-NLP/daVinci-kernel` has **no LICENSE file** (blocks reuse of its 960-skill corpus);
`github.com/parallelcodefoundry/ParEval-Repo` has **no root LICENSE** (GitHub reports `license: null`);
KLineage and Kernel-Smith release **nothing at all**. Public-and-unlicensed is not permissive.

#### Research Intake Update — 2026-09-07 — FreeToken on gfx90a: DECLINE with reasons (intake-1318, 1343, 1345)

- *Classification*: it is a **port, not a rewrite** — Triton slot pool in flashlib (Apache-2.0), generic torch graph API, AVX-512-BF16 CPU branch, 22-line CUDA surface, working RDNA4 precedent. **But port-not-rewrite survives only as a classification, not as a cost estimate**: the community realisation of that "22-line surface" is ~750 lines across two unmerged PRs (#132, #378). `intake-1318#record`.
- *Gate 1 (dependency pins)* — upstream pins `torch>=2.11,<2.12` and `triton==3.6.0`; all three ROCm reporters run torch 2.11–2.15 on ROCm 7.14/10.1 nightlies; **we are on ROCm 6.2 deliberately** (see the ROCm-6.2 build-flag checklist note at :144 — issue #19984's unroll regression is gated behind the same version boundary). A port needs a host-level ROCm major upgrade under a FROZEN production kernel set — an operator decision, not a research task. This **supersedes** "untuned kernels on a different ISA family" as the stated reason. `intake-1343#record`.
- *Gate 2 (HIP-graph API floor) — THE STRONGEST, and it cannot be packaged around*: HIP stream memory operations are **not graph-recordable before HIP 7.14** (`hipGraphAddBatchMemOpNode` / `hipStreamBatchMemOpParams` absent from ROCm 6.2's HIP documentation; confirmed by PR #378's own `#if` guard and source comment), so on ROCm 6.2 even the fixed engine runs cpu/hybrid MoE with graph capture **disabled**. `intake-1345#00`, `intake-1345#01`.
- *Gate 3 (it does not build)*: `setup.py` requires `CUDA_HOME` and links `cudart`; `cpu_moe` includes `cuda_runtime_api.h`; the only ROCm support is three unmerged PRs whose own compatibility header enumerates **RDNA3/RDNA4 exclusively — no CDNA entry**. `intake-1345#record`.
- *Gate 4 (payoff)*: 0.73–0.86× vs fully-resident llama.cpp in **every** AMD configuration ever run; the one favourable ratio is set by a 6-core baseline we already beat by 3.2×; local ceiling on the mechanism is +27%. `intake-1343#00`.
- *Reusable facts banked here for a future ROCm porting session*: flashlib is Apache-2.0 Triton; both `pinned.py` defects are **fork-introduced regressions**, not upstream (upstream raises `ImportError`, the port replaced it with `return None`); PR #378 exists and is the community fix.
- *Declines recorded, with scope*: **port/adopt/trial FreeToken in any form** (1318#8, 1343#5, 1345#4); **build a q*-style bandwidth-adaptive miss splitter** (1318#9 — refuted on its own arithmetic before any implementation cost; our measured DRAM sub-linearity, 152.6 of 460.8 GB/s, is exactly the condition that makes the split net-negative); **chase Vulkan-vs-ROCm** (1343#6 — structurally unavailable: no Vulkan ICD targets CDNA2 compute-only parts, RADV enumerates zero devices on gfx90a per `design-backlog-triage-2026-07-23.md:229`; independent Linux data also shrinks the gap to +1.6%/+8.8%); **ingest the three further ROCm forks** (1343#7 — surfaced, not read; recording the decline scopes the negative rather than letting the sweep look exhaustive); **file the two architecture-independent findings** — `qsa_block_topk` tie behaviour (misattributed at the pinned commit, harmless by the reporter's own measurement) and `FREETOKEN_CACHE_DIR` (a doc defect in a project we do not run) — **beyond the notes in the entry** (1345#5); **chase the across-process topk tie variability** (30/39/46/62/82 of 2048 on identical seeded input, stable within a process) (1345#6 — the most interesting unexplained observation, needs Triton-level work on hardware we do not have; recorded so a reader knows what was left on the table).

#### Research Intake Update — 2026-09-15 (search-strategy confound)

- **[declined: ws58 2026-11-03 content-review: a record note (the panel ranks whole agents), not a task]** **S3-INF03-01 — record that the eight-arm panel ranks WHOLE AGENTS, not search strategies.** Each arm brings its own editor/actor and there is no trivial search-policy arm (arm 1 is the no-authoring start state). Write this into the campaign contract, and add OR explicitly decline a greedy hill-climber arm that uses an existing actor as editor. intake-1375#00.
**S3-INF03-AIDE-1 trigger record — fixed-actor search-policy control.** Activate only after the shared selector replay finds a material held-out policy difference, or an already-running AutoKernel campaign can reuse its frozen actors, proposals, evaluator, and budgets without new generation infrastructure. Then compare greedy incumbent selection with an AIDE85-style five-arm UCB/fork policy while fixing model, prompts, context policy, task subset, seeds, and token/evaluator/wall budgets. Keep the final evaluator inaccessible and retain every proposal, branch, failure, score, and receipt. Sources: intake-1630#record and intake-1375#record.

#### Research Intake Update — 2026-09-17 (SimpleTES code: RPUCG + ROCm eval path, intake-1454)

- **[superseded: inf48-triage 2026-11-09: controller-A/B parent-selection arm; superseded by the discovery controller; full text at b3bd883d3:2872]** **AR-RPUCG — A/B SimpleTES's RPUCG DAG parent-selection as a controller candidate in the MI210 verify+profile loop.**
- [x] **AR-ROCm-eval — register SimpleTES's ROCm eval path (AMD_REQUIREMENTS rocm6.2.4; `profile_program_roc`) and issue #6 MI300 config as gfx90a port input.** Study-only; no external-benchmark re-measure (AK-RB-1). Source: intake-1454. Pinned profiler/runtime/artifact seam, host-version mismatch and issue #6 caveat are registered below; no executable port or benchmark claim was made.

##### AR-RPUCG/AR-ROCm-eval implementation intake — 2026-09-17

**AR-RPUCG data admission.** At SimpleTES `47d3413d`,
`simpletes/policies/rpucg.py` selects *already evaluated* nodes from a
parent→child DAG. Its selection uses each node's raw score, creation order,
chain membership, per-chain visit counts/total expansions, and one-hop
parent/child exclusions; the default policy parameters are `c=1`, `gamma=0.8`.
The current MI210 r19 archive is not such a dataset: the admitted first
actor cell's checkpoint records four broker evaluations and a final score,
while its individual `controller-evaluation-windows/*-result.json` receipts
carry source hashes and scores but no candidate/parent IDs, chain or visit
state. An exact JSON search of r19's cell receipts found no `parent_ids`,
`parent_candidate_id`, `chain_idx`, or `visit_counts`. Do not invent a DAG by
ordering these revisions, and do not describe a fixture comparison as the
requested A/B. The r19 archive remains diagnostic/nonpromotable under its
own campaign rules.

The minimum prospective, nonpromotable capture for **one named MI210 task** is
an immutable pre-selection snapshot: task and evaluator/recipe identities;
candidate ID, source hash, parent IDs, creation order, chain ID, valid
correctness and direction-normalized reward for *every eligible evaluated*
node; the exact incumbent eligibility set, choice and tie rule; and RPUCG
visit/expansion state before choice. Compare both selectors on precisely
that frozen pool, with equal inspiration count and no evaluator call from the
selector. Record chosen IDs, overlap, score/lineage of each choice and
selector cost. This is a **selection disagreement** result only; one logged
history cannot establish counterfactual downstream kernel quality. That
requires separately governed paired continuations with equal budget and
the standard correctness/timing claims. No live selector switch follows an
offline disagreement.

**AR-ROCm-eval port register (study-only).** Source pin: SimpleTES
`47d3413da1d85dc24341219d47452d2601e56a57`, AGPL-3.0-or-later,
`datasets/gpukernel/server/tasks/libkernelbot/run_eval.py`:
`profile_program_roc` wraps the supplied call in `rocprofv3`, requests
HIP/kernel/RCCL/marker/memory-copy/scratch traces in pftrace and CSV, and
packages traces/code objects. `run_eval.py` dispatches to it when the
detected runtime is `ROCm`. This is a profiler/artifact seam, **not** a
replacement for our parent-owned evaluator, sealed reference, claims or
promotion gate. The source's `server_info.yaml` points at private hosts and
must not be imported as a runnable service configuration. The source's AMD
environment note names ROCm 6.2.4, while this host's `hipcc` reports ROCm
6.2.0; our own `rocm-verify-profile-backend.md` records a side-loaded,
version-matched `rocprofv3`. A future port must pin the actual executable,
runtime and trace schema and validate gfx90a compatibility rather than infer
it from MI300. [SimpleTES issue #6](https://github.com/wq-will/SimpleTES/issues/6)
reports a released TriMul artifact near 1.390 ms but an independently run
MI300 search near 1.841 ms; its search-budget/variance/configuration question
is a warning against importing a headline or default budget as an MI210
expectation. No external benchmark was re-measured here.

#### Research Intake Update — 2026-09-17 (cross-ISA port evidence; intake-1491)

**Cross-ISA port evidence (2026-09-17)**: a HIP-native SageAttention port exists but targets RDNA2/RDNA3 (gfx103x/gfx110x, WMMA/V_DOT — absent on CDNA2/MFMA); cite only as existence proof for cross-ISA porting, never as gfx90a evidence (intake-1491). CuTeDSL remains NVIDIA/CUTLASS-only and must not be imported (standing rule).

#### Research Intake Update — 2026-09-25 (adversarial program evolution)

**Digital Red Queen activation trigger.** Materialize the following work only when EPYC has a real opponent-defined kernel workload and observes or must decide around cycling, forgetting, or nontransitivity. Ordinary candidate ranking and static correctness/performance panels do not fire this trigger.

- **S3-INF03-DRQ-1:** add external and historical cross-play over contemporaries, a stratified archive, and frozen unseen shapes/operators/edge cases; emit the pairwise matrix, dominance graph, forgetting, regret/exploitability, cycles, internal champion, population mean, and external-panel result with repeated-seed/opponent intervals. Sources: intake-1600#record, intake-1612#record, intake-1613#record.
- **S3-INF03-DRQ-2:** run matched random, neutral-mutation, non-LLM-mutation, static-opponent, score-only/no-archive, no-history, and archive-depth controls under equal evaluator, model-call, token, and wall budgets; retain every effective config and terminal summary in native receipts. Sources: intake-1600#record, intake-1611#record, intake-1616#record, intake-1617#record.

#### Research Intake Update — 2026-09-26 (GEMM ladders and MFMA form on gfx90a; intake-1822..1826)

- **[declined: restructure 2026-11-10, not open work: INF03-REGAUDIT-3 PARKED (operator 2026-09-27); INF03-AGPR-1 PARKED (operator 2026-09-27); INF37-MOE-Q8-FUSION DECLINED-PROPOSED (proposal only, never approved); INF03-REGAUDIT-RUNNER DECLINED-PROPOSED (proposal only, never approved). Reopen needs an operator decision]** **INF48-LIVE-7 INF03/INF37 gfx90a kernel work - MMQ ISA audit runner binding, v9->v10 spill regressions, NH-1 AGPR arm, low-quant tripwire, Q8 MoE GLU fusion.** INF03-REGAUDIT-3 and INF03-AGPR-1 are PARKED by the operator (2026-09-27); INF37-MOE-Q8-FUSION and INF03-REGAUDIT-RUNNER are PROPOSED, not build approval. [no-belief: new consolidated box]
  - 2026-11-09 (pipeline-mgmt, row `j64-widths-27b-c9-20261109`, filed fail = rule false): J64-WIDTHS on 27B Q8_0 at C9: J=64 share of busy 70.9% at p64 and 78.5% at p128 (>=20% holds) but ns/col p64/p48 = 0.90 and p128/p96 = 0.92 (needs >1.05), so no fix upside at these widths; production J=64 share ~0% (c8 trace). Resident reps only; wall reps carry no tok/s. Box stays open (REGAUDIT-3 and AGPR-1 parked). [no-belief: partial status note]
  - *(folded into INF48-LIVE-7; full text at b3bd883d3:2939)* **INF03-REGAUDIT-RUNNER — PROPOSED: bind the MMQ timing runner to the exact passing static ISA audit.**
Dived: intake-1822 (HipKittens Helios GEMM ladder + code), intake-1823 (Gluon GEMM tutorial + repo, and a read-only
extraction of our production libggml-hip.so), intake-1825 (arXiv 2609.15627, DS-V4-Flash on MI250/gfx90a),
intake-1826 (LLVM #159493/#148079, MFMA VGPR/AGPR form). What transfers to gfx90a is lever ORDER and a short list of
ROCm 6.2 builtins (sched_group_barrier, iglp_opt, s_setprio, dword raw.buffer.load.lds); TDM, split barriers, clusters,
async b128 loads and WMMA do not exist here. MMQ at J=64 already spills at the 256-VGPR cap, so every register-affecting
candidate must pass a static audit first. The AGPR copy tax on <=256-thread MFMA kernels is a ROCm 6.2 compiler default
(intake-1826#record).

- [x] **INF03-REGAUDIT-1 — Standing zero-GPU static register/ISA audit for gfx90a HIP kernels.** ✅ 2026-09-27 — landed as research `scripts/kernel_rnd/gfx90a_isa_audit.py` (e603216f; `diff` exits 1 on new/larger spills, more hot-loop reloads or accvgpr copies, AGPRs appearing, lower occupancy). First audit `data/gfx90a-isa-audit-20260926/` (v10 f26a166b + v9). Confirms Q8_0 J=64 at 256 VGPR/37 spills, spill-free at J≤48; corrects the dive: MMQ has two hot k-loops (Q8_0 10/12 reloads; need_check=1 up to 34), Q2_K spills at J=48, FA-MMA reloads ~2x undercounted (DKQ=256 656–756/iter). v9→v10 regressed several MMQ types (Q5_0 15→46, Q1_0 21→61, Q4_0 nc=1 0→32, Q8_0 32→37 spills). Promote the
  intake-1823 dive scripts (`/mnt/raid0/llm/tmp/dive-intake-1823/ourbuild/`: split_fatbin.py, analyze_kernels.py,
  loop_analysis.py, agpr_rule_check.py) into the research repo with a README. Per kernel, emit: symbol, workgroup
  size, agpr_count / accum_offset, total and arch VGPR, vgpr_spill_count, private bytes, in-hot-loop spill reloads,
  in-loop v_accvgpr_read/write, s_waitcnt drains per iteration, and MFMA placement relative to s_barrier. Scope: MMQ,
  MMA-FA, rocWMMA FA, mul_mat_f. It is the accept gate for any MMQ/FA register-affecting candidate: no timing
  before it passes. Reads existing binaries only. Belief-kernel write side: SC84 amendment (P6).
- [x] **INF03-REGAUDIT-2 — make the ISA gate a hard step before timing.** Add `gfx90a_isa_audit.py diff <incumbent>
  <candidate> --families mmq,fattn_mma,fattn_wmma,mmf` to the kernel-promotion runbook/skill and the INF03-AGPR-1 arm
  protocol: must exit 0, or each FAIL is accepted by name in the package. Store both audit JSONs with
  `--category`/`--source-commit` so they feed SC84. ✅ 2026-09-27 — `.claude/skills/kernel-promotion/SKILL.md` step 3c
  plus the required `gpu_isa_audit` gate in `promotion_gates.yaml` (root lane `lane/park-20260927` `222a2f93`); the
  INF03-AGPR-1 accept clause below now names the same diff.
  - *(folded into INF48-LIVE-7; full text at b3bd883d3:2962)* **INF03-REGAUDIT-3 — investigate the v9→v10 MMQ spill regressions**
  - *(folded into INF48-LIVE-7; full text at b3bd883d3:2966)* **INF03-AGPR-1 — NH-1 MFMA-form arm on ROCm 6.2**
- [x] **INF03-GLUON-X — record, not work: Gluon and the tutorial's tools do not transfer to gfx90a.** Upstream Triton
  rejects BufferLoadToLocal on CDNA2, and local Triton 3.1.0 predates Gluon. amdgcnas hard-codes gfx950 registers,
  misses gfx90a `buffer_*` spills, and deletes in-loop s_nop wholesale. llirSched's cycle table is gfx950-only (gfx90a
  16x16 MFMAs are 8-pass). Do not port. (intake-1823#record) ✅ 2026-09-26
- Register-pressure datapoint (cross-reference only): intake-1825 Table 5 reports a 32x32 INT8 MFMA gate at 165 VGPR plus
  32 KiB LDS collapsing occupancy on gfx90a. That is independent support for INF03-REGAUDIT-1.


#### Recovered C5 historical policy carrier — 2026-10-06

- [x] **C5-POLICY-PATH — restore default verification of the exact already-pinned historical policy bytes through a versioned Research evidence carrier.** MAIN independently verified90723-byte Git blob `f17f295b884889ba837709f1822e1045fad4a5cb`, original ROOT commit `97674cbce44146bd40778d50d1232fc62af8918d` and authenticated GitHub source identity. Keep SHA `c8cec57941b5c0954cd65b44719b984612d9c25094fce3e2ef4bcd42e8ec4f70`, evidence ID and all claims unchanged; add explicit repo-relative no-follow identity checks and actual default-loader/refusal controls. Existing absolute external authorities retain their verifier. No policy replacement, ratification, SOL/GPU run, production kernel edit or retrospective warrant. C5-5 persisted join is already complete; this is newly unlocked source work.
- [x] **AK-C517-1 — Surrogate acceptance: decision-level rank agreement on the deployment distribution (clause on C5-17).** Append to C5-17: a surrogate acceptance report also states rank agreement (Kendall tau or top-1) between surrogate-chosen and measured-chosen candidates on held-out recorded rounds, because prediction accuracy alone did not certify play quality; the held-out rounds for that check include candidates the planner chooses under the surrogate (the deployment distribution), not only uniform samples (intake-2233#record, intake-2263#record; the game domain is a mechanism, not evidence about kernels). Document edit only; no surrogate is built. Acceptance: the clause is on C5-17. Estimate: 0.1 day. ✅ 2026-10-21

2026-10-06 MAIN acceptance: C5-POLICY-PATH completed after exact source publication and independently reviewed original28/28; [bounded acceptance](../../artifacts/ni08/c5-policy-path-source-20261006/README.md). Historical policy bytes and existing grader unchanged; no SOL/GPU/runtime warrant.

##### 2026-10-31 C5-7 conditional source seam

Research implementation `39b63b061238d52d0669d2d9eb3e4d3f29affd11` adds the explicitly declared counter gate at the actual hip_decision_grade terminal decision: wrong/missing/ambiguous counter evidence suppresses the opted-in speedup belief and rankability, while absent declarations preserve legacy behavior. The bounded raw-CSV reader hashes and parses one stable buffer and binds exact counter/kernel/dispatch, source, campaign, workload, units and normalization; zero remains valid.19 focused tests, compilation and diff checks passed. Evidence: Research `scripts/kernel_rnd/autokernel/controller/test_hip_decision_grade.py`; ROOT `progress/2026-10/2026-10-31-c5-7-counter-gate.md`. This replays externally supplied profiler receipts only: no end-to-end PMC capture, broader native caller or live activation is established. C5-7 remains open, with no completed-code-quota claim. [no-belief: conditional source and synthetic replay controls]

##### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

Operator-approved 2026-10-31 (plan revision 2, `research/intake-stage3-plan-2026-10-31-ws58.md`, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`; relayed by the ws58 coordinator; budget approved: about 13 MI210-hours for the drafter pilot, 6-9 engineer-weeks for the race checker, the 95.5 GB ThinkingCap download; D1 confirmed: in-weights calculator declined, GPU reason recorded on intake-2550/2574; D2 approved: scratch upstream builds are measurement instruments only). Trigger records below are prose with no checkbox until a reviewed session confirms their condition.

  - *(folded into INF48-LIVE-6; full text at b3bd883d3:2998)* **C5-ISA-1 — Archive the AMDGCN ISA of every AK GPU candidate and check the claimed instructions executed (intake-2555#record, intake-2588#record).**
  - *(folded into INF48-LIVE-6; full text at b3bd883d3:2999)* **C5-ISA-2 — GCN-Gym: LLM-edited AMDGCN for a compute-bound gfx90a kernel whose limiter is register allocation (intake-2555#record, intake-2556#record).**
- *Intake knowledge note, K5, row KERN-9 (intake-2556#record):* Keep the AK-PL-1 prompt-leak guard. If diagnostic failure feedback (failing indices/values) is ever adopted from TAIC, generate it on a feedback seed disjoint from the acceptance seed population.

- Hazard note (intake-kspec-20261120, intake-2719#record): C14 and v10 GPU MUL_MAT_ID drop duplicate expert IDs silently (MMQ/MMF helpers) or abort (host fallback). Do not serve duplicate-routing architectures (GROVEMOE, hash-routed deepseek4, zero-expert archs) on the MI210 before upstream #32505 lands with its prerequisites. Served routing paths produce unique IDs on finite logits; AK-ASM-H11-UNIQ tests the degenerate rows.
- Monitor (intake-kspec-20261120, operator-approved): llama.cpp #32505 duplicate-expert-ID fix — take only with a whole upstream sync that also brings #31617, #31047 and #27466 (intake-2719#record); the n_used=10 helper gap is handled separately by MMID-HELPER-N10.


### Done

- [x] **—** ✅ 2026-08-12 — live
- [x] **AK-KB-1** ✅ 2026-08-11 —
- [x] **—** ✅ 2026-07-29 — human amendment ratified the canonical MI210 GPU protocol in [`MEASUREMENT.md`](../../MEASUREMENT.md#p-gpu-1--mi210-gpu-canonical-throughput-ratified-2026-07-
- [x] **—** ✅ 2026-08-11 —
- [x] **—** ✅ 2026-08-11
- [x] **—** ✅ 2026-08-11 — research `4320d83a`
- [x] **—** ✅ 2026-08-11
- [x] **—** ✅ 2026-08-12
- [x] **—** ✅ 2026-08-03
- [x] **—** ✅ 2026-08-12 mainB
- [x] **—** ✅ 2026-08-11 — 372 bank and 6,048 phase
- [x] **—** ✅ 2026-08-12 (mainB).
- [x] **GEAK-family** ✅ 2026-07-29 **: refreshed the deep-dive appendix from AMD's current AgentKernelArena/GEAKv3 reports. AKA now publishes 214 tasks and a 44-task MI300X comparison; this is ve
- [x] **—** ✅ 2026-08-11 — `datatype_targets.py` exposes a non-numeric FP8-weight/software-upcast contract to Arena tasks, requires an independent decoder, exact-shape baseline, upcast-
- [x] **—** ✅ 2026-08-12 —
- [x] **C5-4** ✅ 2026-08-16 —

- Monitor (ak-intake-20261121, operator-approved): HIP ReplaySSM non-flush path (ring of logged inputs, per-row flush flag, output-only verify on the C8-6 UT machinery) only after RS-REPLAY-PORT lands and an np >= 4 served row shows committed-state writes >= 2% of the round (intake-2771#record).


## Track: mi210-q8-dequant-gemv-roofline
<!-- gate: INF-48#rocm-verify-profile-backend, EVL-47 -->

### Backlog
- [x] **WSTREAM-DECODE-BUDGET-GPU** [non-inference] Estimate the MI210 spare-ALU budget for in-register lossless weight decode inside the Q8_0 decode GEMV at batch 1: from the measured GEMV occupancy and bandwidth (about 65% of HBM peak on the 27B decode), compute the VALU cycles per streamed byte available under memory stalls, and compare with the decode cost per output byte of the WSTREAM-DECODE-UBENCH-CPU schemes mapped to wave64 (intake-2756#record).
      · done when: a short note with the stall-cycle budget per byte, the per-scheme wave64 decode cost estimate and the verdict: a scheme fits iff its cost is below the stall budget with 1.5x margin and the census saving is >= 3%, which opens an experimental kernel box; otherwise close
      · gate: WSTREAM-ENTROPY-CENSUS        · inputs: `/mnt/raid0/llm/tmp/dive-ak-intake-20261121/2611.17108v3/dive.md`
      · result 2026-11-21 (estimate, no GPU run; verdict FAIL at the 1.5x margin, close): MI210 = 104 CU x 64 lanes x 1.7 GHz = 1.13e13 VALU lane-ops/s (CDNA2: one wave64 VALU op per 4 clk per SIMD, no dual issue). q8wv_mul_mat<8,1> at ~65% of 1.6 TB/s = 1.04e12 B/s, i.e. 5.9 B/clk/CU, gives 10.9 VALU lane-ops per streamed byte if the VALU is otherwise idle; the GEMV itself spends ~1-1.5 (v_dot4_i32_i8 per 4 B, scale cvt/fma per 32 B, address math), leaving ~9.5, and 9.5/1.5 = ~6.3 lane-ops per byte allowed. Wave64 mapping (one byte stream per lane, 64 interleaved streams, LUT in LDS): 32/64-lane Huffman ~9-10 VALU per decoded byte (bitbuffer shift 2, field extract 2, sym/len split 2, refill test+select 2, pack for dot4 1; the LDS lookup itself is ~24 B/clk/CU, well under 128); tANS ~9-10 (variable-width extract + base add + same refill/pack); split stream ~8.5 but only 2.8-3.2% saving (fails the census gate alone); static single-stream is serial and needs the lane split anyway. Every scheme fits the raw budget (10.9) but none fits with 1.5x margin, and the extra bitbuffer VGPRs cut occupancy, which the 65%-of-peak GEMV needs for latency hiding. Reopen only if a cheaper decode form appears (e.g. <= 6 ops/byte, such as a fixed-length-class code with no per-symbol LUT). [no-belief: analytic estimate]
      · scales-only recompute 2026-11-21 (estimate): one scale per 32-code block; 32-lane Huffman scale decode ~10 VALU + fp16 table read from LDS ~1 + broadcast to the code lanes (ds_bpermute or LDS) ~1 + separate scale-stream addressing ~1 = ~13 lane-ops per block, i.e. ~0.4 lane-ops per streamed byte against a 6.3 budget at 1.5x margin: FITS by ~15x, with small VGPR cost. The saving is the binding constraint, not the compute: 27B 3.05% / drafter 3.00% / A3B 2.69% net (WSTREAM-DECODE-UBENCH-CPU amendment). [no-belief: analytic estimate]
- [ ] **WSTREAM-SCALES-Q8-GPU** [inference] Experimental Q8_0 variant with a compressed fp16 scale stream: codes stay raw int8 in place (32 B per block, no block-stride change for the code stream), scales move to a separate per-tensor stream of 32-lane-Huffman-coded 8-bit-or-escape indices into a per-tensor fp16 table with one 32-bit offset per row; `q8wv_mul_mat<8,1>` (batch-1 GEMV, gfx90a) gets a variant behind a default-off knob that decodes the row's scales into LDS/VGPRs before its dot loop. Target 27B Q8_0 (and the DFlash2 drafter); A3B is excluded (2.69% net < 3%).
      · done when: (a) an offline converter writes the variant GGUF from the production 27B Q8_0 file, the round trip is bit-exact on every tensor, and the measured file-level saving is >= 3.0% of streamed bytes; (b) on a `llama.cpp-experimental` build the knob-on GEMV is bit-identical to knob-off (test-backend-ops plus llama-debug final logits); (c) one e2e GPU decode row on 27B shows tok/s gain >= the 0.84% GPU floor with greedy output identical, or the box closes with the numbers
      · gate: WSTREAM-DECODE-UBENCH-CPU        · rule: needs the scales_only arm PASS (decode-rate evidence); the census already gives 3.05% (27B)        · model: Qwen3.8-27B Q8_0 (+ DFlash2 drafter Q8_0)        · build: experimental branch from fresh production, knob default off, content proof = knob string in libggml-hip.so
      · stop rule: question = does a scales-only lossless stream raise MI210 27B batch-1 decode tok/s? expected effect <= ~3% (bytes saved x GEMV share of decode time) against the 0.84% floor; stop at (a) if the converter's real saving is < 3.0%, at (b) on any bit mismatch, and at (c) after 6 ABBA blocks

> Folded from `handoffs/active/mi210-q8-dequant-gemv-roofline.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F23, route 1a, operator D1/D5; retired row INF-37 → INF-03). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Handoff: MI210 single-stream roofline — Q8 dequant-GEMV kernel + batch-1 latency levers

**Scratch**: `/mnt/raid0/llm/tmp/mi210-moe-q8-fusion/` · worktrees: `/mnt/raid0/llm/worktrees/mi210-moe-q8-fusion-*` (new follow-up only; historical evidence is not relocated).

**Status**: OPEN — Q4_K inside-kernel attribution and IQ2 governed replay remain live. **Created**: 2026-07-04 (Fable5 window-2 MI210 campaign follow-on).
**Owner tree**: `/mnt/raid0/llm/llama.cpp-experimental`; all new work starts from current frozen production (v10 as of 2026-10-04) in an isolated experimental branch. The old `upstream-mtp-verify`, production-v6/v9, and `build-hip/` instructions below are historical only.
**Substrate**: MI210 gfx90a/CDNA2, 64 GB HBM2e, ROCm 6.2. Current runs follow P-GPU-1, exclusive device claims, numeric in-window sampling, and the governed INF-48 profiler runners; pre-P-GPU-1 observations below retain their historical authority only.
**Context doc**: `handoffs/completed/fable5-window2-findings-05b-mi210-inference-architecture.md` §1/§9.

#### UPDATE 2026-07-04 — measured results REFRAME this handoff (Tier-1 premise is WRONG; async-prefetch is the lever)

Kernel-thread `a8afd338` executed the levers below. Corrections, most important first:

1. **Tier-1 lever 2 (fused dequant-in-GEMV) is a NON-TASK.** The Q8_0 GEMV is ALREADY int8-native — `vec_dot_q8_0_q8_1` (`vecdotq.cuh:797`) uses `ggml_cuda_dp4a` integer MAC + one fp scale per 32-block, i.e. the CPU iqk "dequant-under-load" pattern is already implemented on GPU. There is **no per-element fp dequant to hide.** The **47→62% gap is achieved-bandwidth / occupancy, NOT dequant-compute.** Do not port iqk to "hide dequant" — there is nothing to hide.
2. **The real lever is Tier-2 lever 3 (async weight-prefetch / memory-level-parallelism).** Down-payment already LANDED: **nwarps 2→4 for batch-1 Q8_0 on CDNA2 = +4.6% (28.99→30.32 t/s)**, `test-backend-ops MUL_MAT` 1103/1103, committed **`5dc116130`** (fork `upstream-mtp-verify`). Async prefetch (`raw.buffer.load.lds` LDS double-buffer) is now in build+measure — exact gfx90a intrinsic design in [mi210-batch1-latency-wall-greenfield.md](../completed/mi210-batch1-latency-wall-greenfield.md).
3. **Tier-1 lever 1 (`quantize_q8_1` requant) = DEFER.** Measured **3.37%** of decode (this build; 5.68% on the older mi210-hip build). Every GEMV re-quantizes its own activation (call-count == `mul_mat_vec_q` count); localized prologue-fusion is *counterproductive* (would requant the activation `gridDim.x`≈thousands of times). Only fix is graph-level (q/k/v activation caching, or fuse into the preceding RMSNorm), ceiling ~1.5–3% with correctness risk on the 82%-of-decode hot path → not worth it now.
4. **Tier-3 lever 6 (n-gram / prompt-lookup GPU spec) = MEASURED NEGATIVE.** All variants regress on the 27B: plain 28.4 → ngram-simple 27.7 (best) → ngram-cache 26.1 (worst); context-only acceptance **~15%**, below break-even. A zero-cost n-gram does NOT beat plain single-stream here — a real trained drafter (draft-mtp/eagle3) remains the path. (Corpus-static ngram, CPL-4b, is separate but must clear a HIGH acceptance bar to beat this negative.)
5. **rocprof note**: v1 aborts at init on this build (PDL/graph kernels) — use **rocprofv2** with the `pmc:` prefix, and add `/usr/lib/x86_64-linux-gnu` to `LD_LIBRARY_PATH` (`libpciaccess.so.0`).

Net: the Tier-1 dequant framing is superseded. The live single-stream track is **nwarps (done +4.6%) → async-prefetch → SoA-repack**, toward the fp16 62% ceiling. Levers below are kept for the record; read them through this update.

#### L3-MoE / L15 quantized-MMQ bet — scope said GO, **BUILD FALSIFIED IT: L3-MoE occupancy rewrite = NO-GO** (2026-07-04)

**Phase-1 result (measure/build-first worked as intended):** the compact-LDS rewrite was BUILT + gated + correct — LDS halved 49→25 KB, LDS-limited residency 1→2 WG/CU, accumulator untouched; `MUL_MAT 1103/1103`, `MUL_MAT_ID 789/789`, PPL indistinguishable — but occupancy stayed **FLAT (3.07→3.07)** and aggregate moved **+1.6% B=32 / −12% B=64**. **The Phase-0 LDS-limit premise is FALSIFIED with data:** at B=32 Q8-MMQ is **grid-limited** (grid = 53248/512 = exactly 104 WGs = 1 WG/CU → no second workgroup to place in the freed LDS), NOT LDS-limited. bf16's aggregate win is its **native-MFMA / zero-dequant compute**, not an occupancy edge Q8 could match by freeing LDS. Raising Q8-MMQ aggregate needs MORE workgroups → **stream-K K-splitting** (a bigger separate bet w/ fixup-kernel overhead; the gated compact-LDS kernel is the ready substrate, saved `campaign/mmq-compact-lds-NEGATIVE.patch`) — or smaller `mmq_y` (forbidden: halves the accumulator; campaign already measured mmid-forcing negative). **Settled: bf16-for-aggregate (B≥16–24), Q8 only for HBM-capacity.** **L15 (sub-4-bit capacity unlock) is INDEPENDENT of this occupancy result and still viable.** The optimistic scope below is kept for the record — read it through this result.

The aggregate-MoE #1 kernel lever, scoped + de-risked into a fundable GO with a concrete mechanism + a measured target.
- **Mechanism (de-risked):** Q8 `mul_mat_q`'s occupancy limiter is the **dequant-staging LDS (45–49 KB > half of 64 KB) + Arch-VGPR (128)**, which caps residency at exactly **1 WG/CU** (grid = 104 WGs) → ~2.5 waves resident → memory unit under-driven at **32%** vs bf16's 48% (the 1.5× maps onto the measured +32% gap). **NOT the MFMA accumulator tile** — bf16 wins with the SAME ~128 Acc-VGPR, just smaller LDS (12.8–25.6 KB) + tiny Arch-VGPR (16). So the "shrink the MFMA tile / lose efficiency" risk is OFF the table; the lever is halving the **staging** footprint only.
- **Target** = bf16's own measured profile: LDS 49→~24 KB, Arch-VGPR 128→~64 → **2 WG/CU** → MemUnitBusy 32→~48% → occ 2.55→~3.2. **Payoff: Q8 aggregate B=32 from 563 t/s toward bf16's 744 — Q8 aggregate-competitive at HALF the HBM.** Residual: at B=128 bf16 also wins on native-MFMA FLOPs, so occupancy alone won't fully erase the top-end; "competitive at half HBM" is the residency-bet goal + achievable. Risk = more dequant recompute / less N-reuse if staging cut too far.
- **L15 sub-4-bit — path ALREADY EXISTS + numerically correct on CDNA2** (not MMVQ-only): IQ2_XXS/XS/S, IQ3, IQ1, Q2_K, Q3_K all MMQ-supported (`mmq.cu:267`) with MFMA tile mappings; CDNA2 gate routes them to MMQ when `n_experts>64 OR ne11≤128`. Live-confirmed (HEAD 7c28056b7): `MUL_MAT 1103/1103` + **`MUL_MAT_ID 789/789, 0 FAIL`** across q8_0/q2_K/iq2/iq3/iq1/iq4. **Missing = a quantized GGUF + the SAME occupancy rewrite** (IQ codebook dequant is MORE LDS-hungry → needs it more than Q8). **Capacity: Qwen3.5-122B-A10B @ IQ2 ≈ 38 GB FITS → fully GPU-resident (the big residency-bet unlock); GLM-5.2 ~238 GB does NOT fit** even at IQ2. **STATUS 2026-07-04: Qwen3.5-122B-A10B UD-IQ2_M (40.4 GB, unsloth) is DOWNLOADING** (in flight ~11%+; obviates the "quantize an IQ2 proxy" step in the build sequence) → on completion, measure PPL + aggregate vs the existing UD-Q4_K_M benchmarks. L15 measurement PENDING.
- **Shared kernel family (one investment, two payoffs):** `mul_mat_q_case<TYPE>` → single `mul_mat_q` device kernel; the LDS-staging/accumulator/occupancy body is SHARED, only `load_tiles` (per-type dequant) differs. **L3-MoE (the shared-body rewrite) is the prerequisite for L15 being fast.**
- **Build sequence:** Phase 0 (sub-4-bit MMQ correctness ✅; remaining = quantize an IQ2 proxy + operator-gated IQ2-vs-Q8 bench) → **Phase 1 (shared LDS-staging/occupancy rewrite, IN PROGRESS)** → Phase 2 (apply to IQ2/IQ3 + retune codebook dequant + quantize 122B→IQ2).
- **Key files:** `ggml/src/ggml-cuda/mmq.cu` (267–340), `mmq.cuh` (MMA tile map 239–264, LDS `MMQ_MMA_TILE_X_K_*` 219–225). Prior CSVs: `campaign/moe-agg/prof/pmc_{q8,bf16}/`.

#### UPDATE 2026-08-03 — the gap is ONE handoff but TWO mechanisms; splitting them (research-intake Stage-2b)

_Via `/research-intake` Stage-2b dive 2b-C. This **refines** the 2026-07-04 update above, it does not
contradict it — the recomputed ladder reproduces the existing fable5 series to within 1 pp._

**The full quant ladder, recomputed on one consistent GiB basis** (spec-BW denominator; see the calibration
caveat below), with `mul_mat_vec_q` measured at **77.8% of decode time**:

| Rung | Bandwidth attainment |
|---|---|
| fp16 (llama.cpp) | **62.6%** |
| fp16 (vLLM-ROCm, same device) | **69.2%** |
| Q8_0 | 50.2% |
| Q4_K | 35.1% |
| MoE-bf16 | 34.4% |
| MoE-Q8 (frontdoor) | 21.3% |
| **MoE-IQ2 (architect, `Qwen3.5-122B-A10B UD-IQ2_M`)** | **10.3%** |
| Qwen3-Next-80B i1-IQ2 | 3.3% |

**The reading that matters: 62–69% is already reached on this device, so the memory system is not the
limiter.** The collapse is entirely down the quant ladder. For reference, DGX Spark GB10 reaches **77–80%
at Q4_K_M dense across five models** on the same engine — NVIDIA's quant sag is 5–10 pp; ours is 27 pp.

**Why this handoff now carries two items instead of one.** The 2026-07-04 update's finding —
*"the 47→62% gap is achieved-bandwidth / occupancy, NOT dequant-compute. Do not port iqk to hide dequant"* —
is **correct, and it is correct for Q8_0**, whose GEMV is already int8-native. But **Q4_K 35→50 is a
different mechanism** (k-quant superblock unpack, not occupancy), and treating the two as one gap has
already produced one wrong verdict. They are filed separately in the checklist below.

**Corrected IQ2_XXS characterization** (verified read-only against our tree, supersedes the
"four *dependent* random reads plus *a* sign-table read" framing): per 32 quantized weights there are
**four INDEPENDENT data-dependent gathers** into a 256-entry / 2 KiB grid — all four indices arrive in a
**single 8-byte `memcpy`** (`ggml-quants.c:2500`), so no address depends on another lookup's result, ILP ≈ 4,
**not a pointer chase** — plus **FOUR** sign-table gathers (`ksigns_iq2xs[…]` is inside the `l` loop), each
grid entry expanding to 8 values. The 4+4 ratio holds across every SIMD path including our production iqk
(`iqk_gemm_iquants.cpp:176-181`, signs `:86-90`), AVX2, and CUDA.

**Calibration — MEASURED 2026-08-03, and the correction is smaller than estimated.**
`epyc-inference-research` `328b768d`, receipt
`data/mi210-achievable-bandwidth/20260803T124401Z/receipt.json`
(SHA-256 `0aab9c7e135929e72fd3a5c2498eb807dc16d0f80b773f063e1df3524df7b4d3`).

**Achievable = 1433.3 GB/s, i.e. 87.5% of the 1638 GB/s datasheet peak** — high for HBM2e. Triad 1371.1;
per-kernel medians copy 1412.5 / mul 1413.9 / add 1362.3 / triad 1362.1, p20–p80 within ~1.2%; 10 warmup,
50 timed, correctness PASS (max abs err 0.0). **Correction factor 1.143×, not the 1.17–1.26× estimated
here before the run — the prior ~1.3–1.4 TB/s guess was low.**

| Rung | % of spec (1638) | % of **achievable** (1433.3) |
|---|---|---|
| fp16 | 62.6 | **71.5** |
| fp16, vLLM-ROCm | 69.2 | **79.1** |
| Q8_0 | 50.2 | 57.4 |
| Q4_K | 35.1 | 40.1 |
| MoE-bf16 | 34.4 | 39.3 |
| MoE-Q8 (frontdoor) | 21.3 | 24.3 |
| **MoE-IQ2 (architect)** | **10.3** | **11.8** |
| Qwen3-Next-80B i1-IQ2 | 3.3 | 3.8 |

**⚠ THE BASIS WARNING, and it is the most important line on this page.** Converting *our* numbers to an
achievable basis while leaving *someone else's* on a spec basis makes the gap look smaller without it
being smaller. **The AMD-vs-NVIDIA comparison must stay spec-to-spec** — our fp16 62.6 against DGX Spark
GB10's 77–80, both against datasheet — **until somebody measures GB10's achievable bandwidth.** Our
71.5%-of-achievable set beside their 77–80%-of-spec is a mixed-basis comparison and is not a reading.
This measurement makes our own numbers physically meaningful; **it does not narrow the NVIDIA gap at all.**
That is precisely the error found this session in AMD's own KB, where a per-OAM TFLOPS figure was divided
by a per-GCD bandwidth to give a ridge point off by 2×.

Use the **achievable** column for headroom and campaign sizing (it is the real roof); use the **spec**
column for any cross-vendor comparison, and say which one you used — a utilisation quoted without its
denominator is not a number.

**The E8M0 divergence is instrumented, and its first classification was WRONG** ✅ 2026-08-03.
`CONFORMANCE-VECTORS-1` ships at `epyc-inference-research/conformance/` (research `33f7076b`): three
contracts, harnesses that **execute the real CPU and HIP decoders** (27 values, gfx90a, all matching),
and 15 tests. Three backend rows are now **VERIFIED** rather than asserted — including the HIP row,
where which branch of `#if CUDART_VERSION >= 12080` is taken was previously *inferred* from source and
is now *observed* on the card.

**RETRACTED: "documented-divergent, not a defect."** That rested on `validate_e_e8m0` rejecting
`0xFF` at load — but that gate runs only under `check_tensors`, which **defaults to false** and is
passed by none of our launchers. And it is not dead code: **both paths are live.** CPU MXFP4 uses
fused `_half`; GPU MXFP4 uses `full(e) * 0.5f`. They agree everywhere except `0xFF`, where
`+Inf × 0.5` is still `+Inf` while the fused half gives a finite 2^127.

**What actually bounds it is weaker: we serve no MXFP4 model** — a property of the fleet, not the
code. So the claim is now *checked*: a sentinel fails the moment an MXFP4 model enters the registry
or lands on disk, carrying the remediation options. Recommendation is to rely on the sentinel now and
pass `--check-tensors` the moment an MXFP4 model is proposed.

**Free incidental finding in our own CPU tree, filed here because it is the same IQ2 sign path:**
`iqk_gemm_iquants.cpp` contains an AVX512-VPOPCNTDQ routine deriving IQ2 signs arithmetically with **zero
table reads**, but its dispatch at `:184` is guarded by `#if defined z_HAVE_FANCY_SIMD && …`. **The `z_`
prefix makes the macro undefinable, so the branch is permanently dead** (same at `:109`, `:571`) and the
table lookup always runs — **including on our Zen 5 host, which has VPOPCNTDQ.** Inherited verbatim from
ik_llama.cpp via `fec061dea`; not introduced by us. Experimental branch only — production is frozen.

#### Objective

**Historical framing below is superseded:** the Q8_0 GEMV is int8-native, and the Q8 gap is an achieved-bandwidth/occupancy question, not per-element floating-point dequant. Use the updates and checklist above and below for current decisions.

Raise **single-stream** GPU decode throughput for the qwen35/Q8 family toward the bandwidth roofline. Measured today: Q8 decode ~47% roofline (766 GB/s), fp16 ~62%, and rocprof attributes single-stream decode ~78% to `mul_mat_vec_q` (the Q8 weight GEMV) + 5.68% to `quantize_q8_1` (activation requant). Two gaps: **47→62% = Q8 dequant cost** (kernel-addressable); **62→100% = batch-1 latency wall** (memory-level-parallelism, harder). This handoff attacks both.

#### Why this matters / transfer

- The already-landed MMVQ→MMQ dispatch fix (`de447119f`, `mmvq.cu:323` CDNA2 `case GGML_TYPE_Q8_0: return ne11<=1;`) gave +17% (27B) / +31.7% (gemma-31B) on the **MTP-verify** batch. This handoff is the **plain single-token** decode, the dominant path.
- Transfers to every GPU-resident Q8 role (the deferred residency bet): frontdoor, and any dense-Q8 model.
- The dequant kernel also unlocks **sub-4-bit** viability (bytes/token axis, below).

#### Levers, ranked (each ships with its decisive experiment)

The following original ranking and experiment sequence are historical; the updates and current checklist supersede their Q8 premise and prioritization.

##### Tier 1 — the dequant gap (47→62%, kernel-addressable, highest confidence)
1. **Kill the `quantize_q8_1` activation-requant overhead** (measured 5.68% of decode). The GEMV requants activations to Q8_1 every step; investigate fusing it into the GEMV prologue or caching. *Experiment*: rocprof before/after; acceptance = quantize_q8_1 share → ~0, decode +5%.
2. **Fused dequant-in-GEMV / int8-native MMQ path for batch-1.** Current `mul_mat_vec_q` dequantizes Q8 blocks then does fp accumulate. Port the CPU **iqk** approach (weight-block-outer, dequant-under-load; ref `ggml/src/ggml-cpu/iqk/iqk_gemm_legacy_quants.cpp:302-330`) to HIP, or hide dequant under the HBM weight load. *Experiment*: single-stream `llama-bench -n 128` Q8 vs the fp16 62% ceiling; acceptance = Q8 decode → ~55-62% roofline (~34-38 t/s on 27B, +15-30%), PPL/output unchanged.

##### Tier 2 — the batch-1 latency wall (62→~80%, harder, MLP-bound)
3. **Async weight prefetch / double-buffering** in the GEMV — software-pipeline the next weight tile's `buffer_load` under current compute (Little's law: more requests in flight → higher achieved BW). *Experiment*: rocprof MemUnitStalled + achieved-BW before/after; acceptance = achieved BW 62%→~70%.
4. **Persistent/megakernel decode** (CUDA-proven, NO ROCm version — greenfield, high-effort). Fuse decode into one launch, weights streamed with pipelining; the Hazy/Mirage ~78% single-dispatch result. *Scope first, don't build blind* — estimate launch-overhead fraction via rocprof gap-analysis before committing.
5. **Weight swizzle/layout for gfx90a** — verify MMVQ HBM access is coalesced to the 64-wide wavefront + 128B cache line. *Experiment*: rocprof L2/MemUnit efficiency; a layout change is only worth it if coalescing is measurably poor.

##### Tier 3 — sidestep / bytes-per-token (orthogonal, can exceed BW-% gains)
6. **n-gram / prompt-lookup speculation on GPU** (`--spec-type ngram-simple|ngram-cache|ngram-map-k`, already in v6, UNTESTED on GPU). Zero-cost draft → converts batch-1 into batch-N verify → more MLP + amortized weight read, at high acceptance for code/JSON/repetitive output. *Experiment (cheap, no kernel)*: run `--spec-type ngram-*` on the 27B over a code/structured prompt set, measure decode t/s + acceptance vs plain. **Do this FIRST — it's the cheapest single-stream win and needs no kernel.**
7. **Sub-4-bit weights (IQ2/TQ1/TQ2) + efficient CDNA2 dequant** — fewer bytes/token → higher absolute t/s even at same roofline-%. Gated on Tier-1 dequant kernel + an eval-parity/PPL quality check. *Experiment*: IQ2/TQ quant of the 27B, decode t/s + PPL vs Q8.
8. **KV-quant for single-stream LONG context** (q8-KV, `-fa 1`) — distinct from the aggregate case (where it was dead): at batch-1 long context the KV read adds to bytes/token. *Experiment*: 27B decode at 64k ctx, q8-KV vs f16-KV.

#### Start-here sequence for the executor
1. **Lever 6 (ngram-spec) FIRST** — cheapest, no kernel, may bank a single-stream win in an hour.
2. **Lever 1 (quantize_q8_1)** — small, high-confidence kernel win.
3. **Lever 2 (fused dequant-GEMV)** — the main event; port the iqk pattern to HIP.
4. Then Tier-2 (prefetch/megakernel) only if Tier-1 leaves the 62% gap and it's worth the effort.

#### Correctness / measurement discipline
- Every kernel change: `test-backend-ops` parity + PPL/greedy-output unchanged (the MMVQ fix was numerically-valid-not-bit-exact; document the same for any new kernel).
- Pair every speed number with a correctness check. Label OBSERVATION until a P-GPU-1 protocol exists.
- Do NOT commit to production-consolidated-v6; experimental only, operator-gated for promotion.

#### Key files
`ggml/src/ggml-cuda/mmvq.cu` (dispatch + `mul_mat_vec_q`), `ggml/src/ggml-cuda/quantize.cu` (`quantize_q8_1`), `ggml/src/ggml-cuda/ggml-cuda.cu:2554-2617` (mul_mat dispatch), CPU reference for fused approach: `ggml/src/ggml-cpu/iqk/iqk_gemm_legacy_quants.cpp:302-330`. Profiling artifacts: `/mnt/raid0/llm/tmp/mi210-build/campaign/{prof,finish}/`.

#### Progress checklist

- [x] nwarps 2->4 (+4.6%, committed 5dc116130) ✅
- [x] async weight-prefetch raw.buffer.load.lds (historical +3.3%, committed 7c28056b7; subsequent governed replay +0.936%, below the 2% floor, **NOT_REPRODUCED**; see Item A) ✅
- [x] L3-MoE compact-LDS occupancy rewrite (BUILT + FALSIFIED, NO-GO) ✅
- [x] L15 sub-4-bit: quantize 122B->IQ2 proxy + operator-gated IQ2-vs-Q8 bench ✅ **2026-07-29 — the "PENDING" predates the run.**
  Both halves landed 2026-07-05: 122B UD-IQ2_M GPU-resident at 43.7 t/s single / 148.7 agg @B32, PPL 5.02
  (`progress/2026-07/2026-07-05-mi210-capability-kernel-rnd.md:23-24`), and the IQ2-vs-Q4 paired eval returned Δ0.0pp,
  McNemar p=1.000 (`progress/2026-07/2026-07-05-mi210-residency-and-cot-reframe.md:12`). Certified by read-certification (`auditor`).
- **[declined: ws58 2026-11-03 content-review: conditional on coalescing measured poor, currently deemed healthy by its own 2026-11-02 source check]** SoA-repack lever (only if coalescing measured poor - currently deemed healthy)
  - **2026-11-02 source check:** the historical healthy disposition is recorded in
    `progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md:124`; a numeric coalescing
    counter receipt was not located in checked-in documentation. The October S7 planar-layout seed
    is source-only, not new evidence of poor coalescing. The repack condition is not established;
    keep it conditional and do not treat the historical assessment as a newly verified counter result.
- [x] Generic stream-K K-splitting for Q8-MMQ aggregate is already present and therefore not a new
  lever ✅ 2026-08-11 — the current CDNA MMQ path is persistent stream-K, and the governed WGM
  experiment exercised that exact launch. Retain only a distinctly justified higher-persistent-grid
  residual (for example `2*nsm`) behind fresh grid/occupancy evidence; do not reopen “add stream-K.”
- **[declined: operator 2026-11-09 (INF-48 triage, dropped, not done): frozen-v9 governed replay: NOT_REPRODUCED at +0.936% (below the 2% floor)]** **Item A — Q8_0 50→62 rung (achieved-bandwidth / occupancy).** — closed as dropped, not completed; original text: `git show b3bd883d3:handoffs/active/rocm-kernel-authoring.md` line 3201. [no-belief: dropped by operator 2026-11-09]
- *(Retarget 2026-10-28 (operator): Qwen3.5-122B deprecated. It no longer serves, so Item C is not a production-serving
  rung. The IQ2_XXS kernel work is format-level. Re-measure it on a current IQ-format target: the
  DS41 or Q38FN low-bit lanes, or the TRIPWIRE's GPU-resident IQ role. Do not use the 122B.)*
- **[declined: operator 2026-11-03 model-audit: the 122B UD-IQ2_M architect is deleted and no IQ2 MoE is in the serving lineup; the OP-12 IQ2_XXS dispatch box stays kernel-owned]** **Item C — architect MoE-IQ2 at 10.3%**, our worst rung by 2× and a production-serving model. Attach the kill-criterion first (below) — this is a probe, not yet a funded kernel
- **[declined: ws58 2026-11-03 content-review: its subject (the architect MoE-IQ2, the 122B) left the lineup 2026-09-22]** Kill-criterion probe for item C: on gfx906 an optimised community fork **and** vLLM independently converge on ~10% bandwidth for MoE batch-1 — the same rung as ours. Two stacks hitting one wall means this may be an **architectural floor**; establish cheaply whether it is before funding a kernel
  - **2026-08-11 tool-boundary result:** the exact main tensor type in the 122B UD-IQ2_M file is
    IQ2_XXS (94 tensors; alongside IQ3_XXS/Q5_K/Q6_K). Ten unprofiled seeded warm-up repetitions pass,
    but `rocprofv2` exits 139 during the IQ2_XXS active trace even after moving all repetitions into
    one backend process. Durable failure receipt:
    `/mnt/raid0/llm/autokernel/probes/c4-iq2xxs-op-singleproc-20260811T1220Z/receipt.json`,
    SHA-256 `fdf355ebc933f3cf20def077cdcc7b998c0072295c00c97b977ad32358c284e2`.
    This is not evidence of an architectural floor. Keep the kill-criterion open and switch the next
    probe to a non-`rocprofv2` device timer/counter path rather than retrying the same crash.
  - [x] **IQ2 tool-boundary follow-up:** capture the same seeded IQ2_XXS shape through a
    non-`rocprofv2` device-timer/counter path and retain the failed receipt as the negative control.
    ✅ 2026-08-12 — done by a different route than the row assumed, so read the caveats. The
    non-`rocprofv2` path is `rocprof` v1 device timestamps, which needs **no seed flags**, so OP-11
    was never on this critical path (OP-11 subsequently DECLINED, Option B). Governed run on the real
    122B UD-IQ2_M passed: `/mnt/raid0/llm/autokernel/probes/iq2xxs-rocprofv1-attribution-20260812T1302Z`,
    residency proven during (VRAM 57→58%, GPU 99–100%). Full analysis:
    [`artifacts/gpu-aux-baselines/a10_iq2_decode_attribution_20260812.md`](../../artifacts/gpu-aux-baselines/a10_iq2_decode_attribution_20260812.md).
    **Three caveats that matter more than the capture:** (1) the governed runner hardcodes `-n 0`, so
    that run is **prefill-only** — the decode GEMV numbers come from a **non-governed** companion run
    (`iq2xxs-decode-nongoverned-20260812T1306Z`); fix filed as RVP-C2-11 with a verified patch.
    (2) IQ2_XXS decode is **16.42%** of decode kernel time, median 85.60 µs across 6,063 dispatches.
    (3) The earlier "not occupancy-limited" reading was from the **synthetic** smoke's
    `<…,false,false>` variant at `Arch_VGPR=64`; production MoE decode runs `<…,true,false>` at
    `Arch_VGPR=80` → **6 waves/SIMD, 75% of max**. Scratch 0 in both, so no spill.
  - [x] **IQ2 VGPR-pressure lever — ISA read done, zero GPU time** ✅ 2026-08-12. Read statically from
    the shipped `libggml-hip.so.0.16.0` (clean frozen-v9 `0db32c06e`). Full table:
    [`artifacts/gpu-aux-baselines/a10_iq2_vgpr_lever_20260812.md`](../../artifacts/gpu-aux-baselines/a10_iq2_vgpr_lever_20260812.md).
    True counts are **63** (`<…,false,false>`, 8 waves) and **78** (`<…,true,false>`, 6 waves) — `rocprof`
    had reported 64/80, which is the allocation-granularity rounding, not the true count. **The mm_ids
    wrapper is NOT the cost:** Q8_0 runs the identical wrapper in **25** VGPRs, so the 78 is IQ2_XXS's own
    dequant state. **But "codebook ⇒ expensive" is also wrong** — IQ4_NL is 38 and IQ1_S 42, while block
    quant Q3_K is the table's worst at 88; pressure tracks per-block state-machine complexity, not the
    lookup. **IQ4_XS sits at exactly 64 on this same wrapper**, so the 8-wave target is proven reachable
    and IQ2_XXS is 14 registers over. Constraint: spill is 0 everywhere, so there is no slack — any
    reduction attempt must report `vgpr_spill_count` beside occupancy or it is not evidence.
  - [x] **Disassembly diff `<IQ2_XXS,1,true,false>` vs `<IQ4_XS,1,true,false>`** ✅ 2026-08-12, zero GPU.
    1002 instructions vs 565; `v_*` 758 vs 334 while scalar (210/203) and LDS (16/16) are near-identical
    and IQ2_XXS issues **fewer** global loads (3 vs 5) — **the codebook gather is not the cost, for the
    third independent time**. The excess is sign unpacking: `unpack_ksigns`/`__vcmpne4`/`__vsub4` lowers
    to ~272 sub-word ops (`v_or_b32_sdwa` 96, `v_lshlrev_b16` 96, `v_sub_i16` 64, `v_bfe_i32` 46), while
    IQ4_XS does its byte manipulation with **48 `v_perm_b32`** that IQ2_XXS never uses.
  - **[declined: ws58 2026-11-03 content-review: merged into the IQ-residency tripwire; no IQ-format role is GPU-resident]** **Re-express the IQ2_XXS sign expansion using `v_perm_b32`** (byte permute) instead of 16-bit
    shift/or/sub chains, in `vecdotq.cuh`. IQ4_XS is a working in-tree example of the idiom on the
    identical wrapper landing at exactly 64 VGPR = 8 waves. **EXPERIMENTAL BRANCH ONLY** — production
    `production-consolidated-v9` is frozen. Report `vgpr_spill_count` beside occupancy, and note that
    decode is bandwidth-bound so this is necessary-not-sufficient for throughput.
    **2026-09-15:** a compiler-side route reaches the same threshold without the rewrite
    (`#pragma clang loop unroll(disable)` → 44 VGPR static; autokernel-research-loop AK-QL-2b). Attempt
    v_perm_b32 only if AK-QL-7 shows the retained 4-trip loop costs more than the regained waves.
  - **[superseded: inf48-triage 2026-11-09: the 122B is retired and must not be rerun (stated in the box); the generation flag landed under RVP-C4-4; full text at b3bd883d3:3314]** **Re-run the decode attribution under governance**
  - [x] **Build a fail-closed Omniperf-v1 fallback runner for the IQ2 profiler boundary.** ✅ 2026-08-11 —
    it binds clean exact source/tool/Python identities, requires seeded repeated correctness before
    SQ/TCC collection, holds the MI210 claim, samples device state, and writes failure receipts.
- **[declined: ws58 2026-11-03 content-review: merged into the IQ-residency tripwire (same trigger)]** With OP-12 approval, commit the one-file IQ2_XXS one-row dispatch and run matched model-level TG/PP confirmation before any promotion claim.
    #27621 (multi-token MoE GLU/top-k fusion) — only if the GGUF has separate `ffn_gate_exps`/`ffn_up_exps`
    and after locating the fix for AMD-HIP garbage-output issue #28113; correctness (fusion on vs
    `GGML_CUDA_DISABLE_FUSION=1`) before speed (intake-1420).
    - **Lever (4), factual note 2026-10-20 (from the INF37-IQ-4 note; no benefit claimed):** Magnitude's planar IQ2_XS/IQ2_XXS/IQ3_XXS layout differs from ggml's block layout (scale and factor placement, packet byte widths): layout-only, needs a repack. Sign-decode ALU order, per-packet factor reload and fp32 versus dp4a accumulation differ in kernel arithmetic: kernel-only. Details and locators in the INF37-IQ-4 note.
  - [x] **INF37-IQ-3 — Correct the imported AGPR compiler-tax note.** ✅ 2026-09-15 — the MI200 CDNA2
    ISA (intake-1409) lets MFMA A/B come from Acc VGPRs, so "HIPCC will not feed AGPRs to matrix-core
    instructions" (`completed/mi210-mfma-compute-bound-paths.md:94-96`) is at most a compiler
    observation, not an ISA limit. Acc VGPRs are MFMA-only (ordinary v_* needs `V_ACCVGPR_READ`), so they
    are no MMVQ decode lever. The 64-VGPR→8-wave rule is in neither the ISA nor the MI250 docs
    (intake-1418); treat it as empirical.
- [x] **INF37-IQ-4 — Record Magnitude's IQ2/IQ3 planar-decode GEMV layout as a lever on file for the IQ-residency reprice (documentation-only, zero compute).** ✅ 2026-10-20 — factual note below: layout-only and kernel-only differences classed; lever (4) on file under INF37-IQ-2; the 16-byte-load claim is corrected in the note. Read `inference/seismic/lang/native-library/vulkan/packets.glsl` (IQ2_XS, IQ2_XXS and IQ3_XXS kinds; the rows16 planar layout with code, scale and super-factor planes and one 16-byte packet load per 32 elements; factored scale*dot+bias*sum(x); the grid sign-parity trick) from `/mnt/raid0/llm/tmp/dive-1979/repo` @ `940e51b` and compare it with ggml-cuda's IQ2/IQ3 `mul_mat_vec_q` decode on gfx90a. Add to the INF37-IQ-2 lever list which differences exist (memory layout, loads per element, sign decode) and which are layout-only (would need a repack) versus kernel-only. No MI210 run and no IQ role is made resident; the entry is read at the tripwire's reprice and claims no benefit.
  - **Factual note 2026-10-20 (INF37-IQ-4; read-only source comparison, no build, bench or GPU; checkbox left open for main review).** Sources: Magnitude `inference/seismic/lang/native-library/vulkan/packets.glsl` @ `940e51b`; production llama.cpp tree HEAD `ffc1bac82` (read with cat/sed only; tracked files clean; last changes `ggml/src/ggml-cuda/vecdotq.cuh` @ `aba5a8155`, `ggml/src/ggml-cuda/mmvq.cu` @ `bff30cebe`). Scope: IQ2_XS, IQ2_XXS, IQ3_XXS grid kinds.
  - Class **layout-only (needs a repack)**: (1) Planar storage. Magnitude keeps per 256-value group an entries plane, a scale plane and an f32 factor plane (`packets.glsl:90-107`, `PACKETS_ROWS16_GRID`; loads `:302-316`). ggml stores array-of-struct blocks: `block_iq2_xxs {f16 d; u16 qs[32]}` (`ggml/src/ggml-common.h:397-399`), `block_iq2_xs` with `scales[8]` (`:403-407`), `block_iq3_xxs {f16 d; u8 qs[96]}` (`:423-425`). (2) Bytes per 32-value packet. Magnitude loads 8 B for IQ2_XS and IQ2_XXS (`packets.glsl:303,306`, `packet.low.xy`) and 12 B for IQ3_XXS (`:310`); ggml reads two u32 per 8 values (`vecdotq.cuh:1038-1040`, `:1073-1075`, `:1162-1164`). The checkbox text's "one 16-byte packet load per 32 elements" does not hold for these grid kinds: the 16-byte load is the q4k/q8 code plane (`packets.glsl:249`). (3) Scale placement. Magnitude's odd scale `2s+1` is a nibble of the scale plane (`packets.glsl:304,307,311,314-316`); ggml's is a nibble in the qs word (`vecdotq.cuh:1061`, IQ2_XXS), the `scales[]` byte (`:1077-1078`, IQ2_XS) and `aux32 >> 28` (`:1188`, IQ3_XXS). Same code, different placement. (4) Super-factor placement. Magnitude keeps one f32 per 256 group (`packets.glsl:313`); ggml one f16 `d` per block (`vecdotq.cuh:1063`, `:1104`, `:1190`).
  - Class **kernel-only**: (5) Factor reload. Magnitude re-reads the group factor for every packet (`packets.glsl:313`); ggml reads `d` once per block (`vecdotq.cuh:1063`). (6) Sign decode. Both use seven sign bits plus an even-parity eighth bit: Magnitude `packets.glsl:217-224` (`bitCount` parity, XOR of float sign bits) versus ggml `vecdotq.cuh:97-104` (`__popc` parity) with byte negation via `__vcmpne4`/`__vsub4` (`:1050-1053`). The parity trick is the same; the ALU sequence is not. (7) Accumulation. Magnitude's `packets_grid_codes` emits fp32 vec4 codes (`packets.glsl:217-224`); ggml accumulates int8 with `ggml_cuda_dp4a` against q8_1 activations (`vecdotq.cuh:1048-1056`, `:1094-1096`). The consumer of Magnitude's fp32 codes lies outside `packets.glsl` and was not read, so the Vulkan accumulation type is not established by this note.
  - No difference: grid tables and index widths (`packets.glsl:198-211` vs `vecdotq.cuh:1047`, `:1084`, `:1171`); no bias term for grid kinds (`packets.glsl:70-72`, `packets_biased` is false; ggml computes `d * sumi`, `vecdotq.cuh:1063`).
  - Dispatch context (not a decode difference): on CDNA2 the IQ types fall to the default batch cap (`mmvq.cu:757-758`); the explicit IQ caps at `mmvq.cu:710-735` sit in the CDNA1 branch. The INF37-IQ-2 item (2) cutoff at `mmvq.cu:185-194` was not re-verified here.
  - This note claims no benefit. No MI210 run, no IQ role made resident. Lever entry (4) added under INF37-IQ-2.

#### Proposed non-IQ follow-through — 2026-10-04 earlier-intake retrospective

  - *(folded into INF48-LIVE-7; full text at b3bd883d3:3397)* **INF37-MOE-Q8-FUSION — Qualify and implement a correctness-gated multi-token MoE GLU fusion slice for the existing Qwen3.6-35B Q8 MTP recipe.**
##### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **INF37-LB1 — Static ISA audit of HIP mul_mat_vec_q at ncols 1 vs 2..8 for Q8_0, Q4_K and IQ4_XS on gfx90a: count weight VMEM loads and dequant VALU per block per column with gfx90a_isa_audit.py; if loads repeat per column, seed a weight-hoisted multi-row MMVQ (Q4_K MMVQ at 8 rows measured 9.4% of roof vs 46.5% at 1 row in the lb1 profile) (intake-2386, intake-2393).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-c.)* AUDITED, no build, no GPU: `scripts/kernel_rnd/mmvq_hoist_audit.py` over the v10 kernel store `libggml-hip.so.0.16.0` (sha256 `f26a166b…`, built 2026-09-21 from `ffc1bac82`), research `0eea263b4` on the research branch `f8/locals-c-research-20261022` (worktree `/mnt/raid0/llm/worktrees/f8-locals-c-research`, unmerged, unpushed); table and json in `artifacts/mmvq_hoist_audit_20261022/`. Weight VMEM loads per ROW per block (flat in ncols = hoisted): **Q8_0 3 at every ncols 1..8** (per block per column 3.0 → 0.375), **IQ4_XS 3 at every ncols 1..8**, so the weight-hoist hypothesis is falsified for both. **Q4_K 6 at ncols 1 → 27 at ncols 8**: the 3 dword `qs` loads per row are hoisted but the 3 ushort d/dmin/scale loads per row are re-issued per column (9, 12, -, 18, 21, 24, 27 at ncols 2, 3, 5..8) and nibble-unpack VALU per row grows with ncols (21 → ~106); ncols 4 is hoisted by the existing `load_q4_K_b4_weight` path. Dequant VALU per block per column: Q8_0 18 → 8.1, Q4_K 63 → 44.2, IQ4_XS 89 → 24.3. Verdict: no seed for Q8_0/IQ4_XS; a Q4_K-only seed (generalise the b4 path to ncols 2, 3, 5..8) is filed in the 27B inbox as 50.4 and is moot for the Q8_0 27B campaign (relevant to the K-quant follow-on). Q4_K ncols 4 loop duplicates load arms (Y loads flagged `load_overcount`), so its counts are an upper bound.

#### Research Intake Update — 2026-11-17 (Exstill 2611.18859 + NVIDIA/Gimlet blogs, intake-2669..2673; operator-approved 2026-11-17)

- [x] **RKA-VERIFY-TILE** [non-inference then inference] Measure MI210 verify-pass cost vs draft length D=0..16 for the production spec-dec roles (27B DFlash2, A3B MTP) at ctx 4k and 32k, and mark where (1+D) and G·(1+D) cross the FA and MMQ tile-M of the current champion (read tile constants from C13 bda43aa17 source, not docs). Source: intake-2671 guideline 3 / intake-2672 (GEMM-M=G(1+D), partial tile costs a full tile). Decision: if cost is step-shaped, set each role's D to the largest value below a step that acceptance justifies (consumer: speculative-decoding.md D settings). Sufficiency: question = is verify cost step-shaped at tile boundaries; expected effect ≥10% verify-time jump at a boundary vs ≤3% rep noise; reuse existing A2 verify-cost gate rows first; stop-on-answer when one boundary is measured with ≥5 interleaved reps; stop-on-futility if the curve is smooth within noise across two boundaries. Gate-class futility-only. Model: Qwen3.8-27B Q8_0, Qwen3.6-35B-A3B Q8_0. [no-belief: new box]
  - *(2026-11-17, AutoKernel)* Source pass done on C13 bda43aa17. Tile widths that set verify cost: gv GQA-verify kernel (hd256, the 27B on the MI210): 16-row MFMA tiles over R = G·n rows, at least 4 waves, at most 16 q rows and 192 rows, pipelined only up to 8 tiles (fattn-gqa-verify.cu:34-39, 744-747, 684-687). MMA_F16 fallback with the CDNA D=256 tune: ncols2 = largest of 8/4/2 dividing G, ncols1 = 16/ncols2 (G=6 gives <256,256,8,2>; fattn.cu:117-120, 199-212). GPU matmul: MMVQ up to 8 columns (mmvq.cuh:3, ggml-cuda.cu:1943), MMQ column tile J in steps of 8 (mmq.cu:140-158), MMQ always used on CDNA for ne11<=128 (mmq.cu:341). CPU: the C13 and v10 CPU stores are built GGML_IQK_FLASH_ATTENTION=OFF, so FA is the mainline kernel with no GQA packing and the tiled path only from 64 rows (ops.cpp:10545-10600, common.h:9). Rows per thread are ceil(n·n_head/nth). CPU matmul: IQK ny-specialised kernels up to 8 columns (iqk_common.h:152). Per role (G, D, n=1+D): architect_critic 27B DFlash2 G=6, D=7, n=8, np4. Its 48 gv rows are exactly 3 tiles, inside the 4-wave minimum, at the top of the MMVQ range: aligned, no change. The DFlash2 block-8 drafter caps D at 7 anyway. Next steps: n 8->9 (MMVQ->MMQ), n 10->11 (a 5th wave), n 16->17 (gv rejects). frontdoor A3B MTP G=8, D=4, n=5: at 96 threads 80 FA rows <= 96, below the step at n 6->7, so aligned. On the 48-thread half instances, D=5 costs the same FA critical path as D=4. architect_general Q38FN MTP (24 q heads, 2 KV heads, G=12), D=4, n=5, 96 threads: 120 FA rows > 96, so 2 rows per thread against 1 at D=3. Production D sits JUST ABOVE a CPU FA step (FA-only, 12 of 48 layers, larger at 32k). Recommendation pending the CPU row: D=3 if the step is visible and acceptance at depth 4 does not pay for it. Rows: rka-verify-tile-gpu-20261117 (gpu-q3 timing, llama-bench n=1..17 at depth 4k/32k, C13 GPU store) and rka-verify-tile-cpu-20261117 (host timing, Q38FN 96t + A3B 96t/48t, n=1..10), both published 2026-11-17. [no-belief: source analysis]
  - *(2026-11-17, AutoKernel)* CPU part DONE (row rka-verify-tile-cpu-20261117, C13 CPU store, 5 rounds, median CV 3.6%): Q38FN at 96 threads has only a ~5% step at n 4->5, so D=4 stays. A3B at 96 threads, 32k is flat for n=2..6 with a +48% step at n 6->7, so D=4 is aligned. A3B on 48-thread half instances at 32k has a +63% step at n 3->4 (91 -> 148 ms per verify step); D=4 (n=5) sits just past it and D=2 costs ~39% less per step. At 4k no step shows. Whether D=2 or D=3 wins end to end depends on acceptance, measured by RKA-VERIFY-TILE-A3B48-E2E. [no-belief: row verdict filed by agent]
  - *(2026-11-18, AutoKernel)* GPU part DONE (row rka-verify-tile-gpu-20261117-r2, C13 GPU store, 5 interleaved rounds, median CV 0.9%): 27B DFlash2 on the MI210 has D=7 (n=8) aligned, no change. A3B Q8_0 MTP on the MI210 (shadow-lane settings), verify cost per batch at 32k: n=3 19.9 ms, then an unpredicted +65% step at n=4 (32.9 ms), a plateau of 33-38 ms for n=4..8, and +25% at n=9 (47.3 ms; located at 4k as the MMVQ->MMQ switch). The shadow lane's D=4 (n=5, 34.3 ms) already pays the n=4 step: D=7 costs about +10% per step over D=4 and D=2 about 42% less. Which wins depends on acceptance, measured by RKA-VERIFY-TILE-A3B-GPU-E2E. [no-belief: row verdict filed by agent]
  - [x] **RKA-VERIFY-TILE-A3B48-E2E** [inference] On an A3B frontdoor 48-thread half instance (C13 CPU store, Qwen3.6-35B-A3B-MTP-Q8_0), compare MTP draft length D in {2,3,4} end to end (predicted_ms/predicted_n plus acceptance) at ~4k and ~32k context, A-B-C interleaved, fresh server per cell. Rule: recommend D=x if it beats D=4 by >=3% at 32k with CI above zero in every round and loses <=1% at 4k; futility if all arms within 2%. Measure only; any recipe change goes to the operator. region: CPU half (q0,q1); est 11000 s; row rka-verify-tile-a3b48-e2e-20261117. [no-belief: new box]
    - 2026-11-18 (autokernel) DONE: NO_RECOMMENDATION, keep D=4. Computed offline from rounds 1-3 (11/12 units; rc 75 before r4-D4). Median ms/token: 4k D2 24.4 / D3 35.9 / D4 47.2; 32k D2 54.0 / D3 69.5 / D4 52.3. At 32k, D2 is 17-23% slower than D4 in every round. The 4k inversion is a follow-up only. [no-belief: row verdict filed by agent]
    - 2026-11-18 (autokernel) analysis of the 4k/32k inversion (`research/deep-dives/a3b-cpu-d-depth-inversion-20261118.md`): the 4k "D2 2x faster" is run-to-run bimodality (about 24 vs 50 ms/token for the same cell; round 1 is flat at 4k: D2 22-25, D3 23-27, D4 25-29), not a verify step; foreign load was not sampled, so contention is likely but unproven. The real step is n 3->4 at 32k (e2e D3 152.7 ms/step vs tile-cpu 148), which is why D3 is worst at 32k. Best-round-per-prompt view: D2 23.4/42.1, D3 25.6/54.9, D4 27.2/46.6 ms/token (4k/32k), i.e. D2 -14% / -10% vs D4. No depth-adaptive D. Recommendation: contention-controlled re-measure, D in {2,4}, 4k/16k/32k; draft spec (NOT PUBLISHED) at `/mnt/raid0/llm/tmp/a3b-cpu-d-depth-followup-20261118/spec.draft.json`; recipe stays D=4 pending operator. [no-belief: offline analysis]
  - *(2026-11-19, autokernel)* The four self-scouted A3B/C15 boxes RKA-A3B48-D-REMEASURE, C15-EPI-Q8, RKA-A3B-ROUTER-MMVF and RKA-A3B-ROUTER-WIDE were moved verbatim to `autokernel-loop.md` (heading "Moved from INF-48 (2026-11-19)"); they are not INF-48 deliverables. [no-belief: hygiene]
  - [x] **RKA-VERIFY-TILE-A3B-GPU-E2E** [inference] On the MI210 shadow lane (C13 GPU store, Qwen3.6-35B-A3B-MTP-Q8_0, -ngl 99, f16 KV, -fa on), compare MTP draft length D in {2,4,7} end to end (predicted_ms/predicted_n plus acceptance) at ~4k and ~32k context, np 1, A-B-C rotated, fresh server per cell. Rule: recommend D=x if it beats D=4 by >=3% at 32k with CI above zero in every round and loses <=1% at 4k; futility if all arms within 2%. Measure only; any recipe change goes to the operator. region: mi210_0,88-95,184-191; est 9000 s; row rka-verify-tile-a3b-gpu-e2e-20261118. [no-belief: new box]
  - [x] **RKA-A3B-N4-STEP** [non-inference then inference] Find why A3B Q8_0 MTP verify cost on MI210 jumps +65% from n=3 to n=4 tokens (19.9 → 32.9 ms at 32k, rka-verify-tile-gpu-20261117-r2); the source-based prediction was flat to n=8. Identify the kernel/path switch (MUL_MAT_ID / topk-moe / mmq-q8-skinny/wvsk column limits) from C13 source and, if a fix makes n=4..8 as cheap as n=3, it would let A3B use longer drafts. Value (from rka-verify-tile-a3b-gpu-e2e-20261118): tokens/step 2.36 at D=2, 3.05 at D=4, 3.36 at D=7; if verifying 4-8 tokens cost about what 3 does (~20 ms at 32k), D=4 would reach ~7 ms/token vs D=2 measured 9.9, about +30% A3B GPU decode — worth more than the D=2 change itself, so high-value. region: none for source step; then mi210_0,184-191 for a rocprof n=3/4/5 split; est 1800 s (source) + 3600 s (GPU profile). stop-on-answer when knob=2 cuts the n=4 cost >= 15% at 32k in every round with n=1..3/5..8 within +2% (FIX); stop-on-futility on n=4 cost moving < 5% at 32k; gate-class = futility-only. [no-belief: new box]
    - 2026-11-18 (autokernel, source read of C13 `bda43aa17` via `git show` in llama.cpp-experimental; n = verify width = src1 ne11 / MUL_MAT_ID ne2): (1) **Q8_0 skinny and WVSK are NOT engaged at n=4**: both default to M>=5 — `mmq-q8-skinny.cu:58` (GGML_HIP_Q8_SKINNY_MIN default 5, gate at :75) and `mmq-q8-wvsk.cu:69` (GGML_HIP_Q8_WVSK_MIN default 5, gate at :90; max 11 at :73). So they cannot explain a 3→4 step (they would explain a 4→5 one). (2) Dense Q8_0 MUL_MAT stays on MMVQ through n=4 on CDNA2 (`mmvq.cu:765-766`, `ne11 <= 4`; MMQ from 5). MUL_MAT_ID Q8_0 stays on MMVQ_MMID through n=8 (`ggml-cuda.cu:2081-2087`, `get_mmvq_mmid_max_batch_cdna` default 8 at `mmvq.cu:596-603`). No route switch at 4. (3) **Prime candidate — a geometry change exactly at ncols_dst==4 for Q8_0 on GCN/CDNA**: `calc_rows_per_block` returns 4 rows/block for `type==Q8_0 && ncols_dst==4 && !small_k` (`mmvq.cu:933-935`, akm-cdna2-q8-b4-y-stream-amortize) vs 2 for ncols 2,3 (`mmvq.cu:947-958`), with `calc_nwarps` = 2 for ncols 1..4 (`mmvq.cu:837-842`). 4 rows x 4 cols of accumulators per thread is 16 chains vs 6 at n=3: VGPR pressure / occupancy drop, and half as many blocks (grid shrink) — tuned on a dense bench, likely wrong for A3B shapes (and if it also applies to the ids/MMID instantiation, for every expert matmul). Next: a GPU row timing n=3/4/5 with this special case off (rows_per_block 2 at ncols 4) on an experimental build, plus rocprof per-kernel split; topk-moe at n=4 not yet checked. [no-belief: source read, no measurement]
    - *(2026-11-18, AutoKernel)* DONE (row rka-verify-tile-a3b-gpu-e2e-20261118, verdict RECOMMEND_D2, 3 rounds, no invalid cells): median ms per generated token D2 9.89 / D4 11.87 / D7 14.42 at 32k and D2 9.36 / D4 11.86 / D7 13.54 at 4k, so D=2 is about 17% faster than D=4 at 32k and 21% at 4k; acceptance at 32k is 68% (D2), 51% (D4), 34% (D7). Operator approved D=2 for A3B on the MI210 on 2026-11-18 (AskUserQuestion); applied to the qwen36_35b_a3b_q8_bridge tenant (tenancy + np_ceiling policy row, control-arm, not live serving) in epyc-orchestrator f38a2379d; the CPU frontdoor A3B recipe stays at D=4 pending RKA-VERIFY-TILE-A3B48-E2E. [no-belief: row verdict filed by agent]
    - 2026-11-18 (autokernel) probe built: fork branch `llama.cpp-experimental-c13-mmvq-q8-b4-knob-20261118` @ `c4556e5a2caff6bc9ab8c1de0573e05600261d38` (C13 `bda43aa17` + default-off `GGML_HIP_MMVQ_Q8_B4_ROWS`; unset = C13, 2 = rows_per_cuda_block 2 at ncols_dst==4; + test-backend-ops Q8_0 MUL_MAT/MUL_MAT_ID n=3/4/5 cases). Source check: MUL_MAT_ID with ncols>1 goes to `mul_mat_vec_q_moe_launch` (fixed rows_per_block=2, never calls `calc_rows_per_block`), so the knob covers only the dense route, which is the only one that uses 4 rows. Row `rka-a3b-n4-step-gpu-20261118` (gpu-q3, in-row build, tbo correctness unset vs 2, tbo perf split since rocprofv3 is absent, llama-bench A3B n=1..9 at 4k/32k, ABBA, 3-5 rounds; FIX / FUTILITY rule in the row). [no-belief: probe published, no measurement]
    - 2026-11-18 (autokernel) C14 `eee3da838` source read + rka-a3b-n4-step-gpu-20261118 result (GGML_HIP_MMVQ_Q8_B4_ROWS=2 ratio 0.988 at n=4: not the cause). Every threshold on this model's verify path, by where it switches: **3->4: only `mmvf.cu` `ggml_cuda_should_use_mmvf`** (AMD + fp32/bf16 MFMA, i.e. CDNA: F32 and BF16 return `ne11 <= 3`). The GGUF has 40 F32 `ffn_gate_inp` [2048,256] routers + 1 BF16 (MTP layer) (256 experts, 8 used), so at n>=4 every router leaves MMVF for `mul_mat_f` (CDNA 64-row blocks -> 4 workgroups for 256 rows) or hipBLAS (`ggml-cuda.cu` ggml_cuda_mul_mat MMVF->MMF->...->CUBLAS chain). **4->5:** dense Q8_0 MMVQ->MMQ (`mmvq.cu` should_use_mmvq Q8_0 `ne11 <= 4`), Q8_SKINNY / Q8_WVSK min M 5. **8->9:** MUL_MAT_ID MMVQ (`get_mmvq_mmid_max_batch_cdna` Q8_0 = 8, MMVQ_MAX_BATCH_SIZE 8; graphs stay on), FA D=256 gqa 8 tile->MMA at n*gqa>64 (`fattn.cu`). Not relevant at 3->4: FA D=320 `<=3`, WMMA vec `<=2`, fused MMVF/MMVQ (ncols 1 only), topk-moe / gated_delta_net / ssm_conv (no n threshold). Most likely cause: the F32 router MMVF->MMF/hipBLAS switch (~9 ms / 41 routers ~ 0.2 ms each). Fix built default-off: fork `llama.cpp-experimental-c15-a3b-n4-fix-20261118` @ `79650eeab60080036508f3bd04ec655621ec688b` (`GGML_HIP_MMVF_CDNA_MAX_NE11=N`, 1..8; unset = C14). rocprofv3 is not installed on this host, so the prepared row `/mnt/raid0/llm/tmp/rka-a3b-n4-trace-gpu-20261118` (READY-TO-PUBLISH, unpublished) uses rocprofv3 kernel-trace if present, else attribution by intervention: coverage = (U4 - MMVF8_4)/(U4 - U3) at 32k, ANSWERED iff >= 0.70 in both reps; plus route log (GGML_CUDA_LOG_MMVQ_ROUTE=2) and tbo F32/BF16 MUL_MAT n=3..8 correctness. [no-belief: source read + unpublished row]
    - 2026-11-18 (autokernel) the trace row `rka-a3b-n4-trace-gpu-20261118` is now PUBLISHED (rank 20; it follows the FUTILITY of `rka-a3b-n4-step-gpu-20261118`, whose `GGML_HIP_MMVQ_Q8_B4_ROWS=2` knob does not move the n=3->4 step, ratio 0.988). Capture/trace cases must use n<=128: on CDNA q8_0 MUL_MAT with n>128 goes to hipBLAS, not MMQ. rocprofv3 is at `/opt/rocm/bin/rocprofv3`. Box stays OPEN. [no-belief: row published]
    - 2026-11-18 (autokernel) `rka-a3b-n4-trace-gpu-20261118` filed **inconclusive by its pre-registered coverage clause, but the cause is confirmed**: the rocprofv3 trace attributes 0.670 / 0.667 of the n3->n4 step to the router MMVF->MMF switch (F32/BF16 `ffn_gate_inp`, `ggml_cuda_should_use_mmvf` `ne11 <= 3` on CDNA). The default-off fix `GGML_HIP_MMVF_CDNA_MAX_NE11` (`79650eeab`; on C16 as `2f0be79d8`) removes 76-95% of the step. [no-belief: row verdict filed by agent]
    - ✅ 2026-11-18 (autokernel) `rka-a3b-mmvf8-e2e-gpu-20261118` r1 was a harness bug (precondition demanded 8 CPUs; a gpu-q3 grant is 16, 88-95,184-191; no data). **r2 KEEP**: A3B Q8_0 MTP on MI210 at 32k, knob MMVF cap 8 columns, D=4 +13.6% (max gain), D=2 unchanged, all four gains >= -1%, identity passes (AA-calibrated); single-stream D=2 stays fastest (9.9 ms/token), so RECOMMEND_D=2 stands. Box question answered: cause = router MMVF->MMF at n=4; fix makes n=4..8 cheaper, but not cheap enough to beat D=2. Knob rides in the C16 composite. [belief: cc]
  - [x] **RKA-A3B-GPU-D-NP-SWEEP** [inference] Run before A3B GPU goes live. On the MI210 shadow lane (C13 GPU store, Qwen3.6-35B-A3B-MTP-Q8_0), compare MTP draft length D in {2,4} on aggregate decode tok/s (generated tokens summed over slots / wave wall), median per-request ms/token and acceptance, at np {4,8,16} (np=1 is the reference rka-verify-tile-a3b-gpu-e2e-20261118: D2 9.89 vs D4 11.87 ms/token at 32k), with a realistic 2-8k-token prompt mix (hotpotqa QA, longcot_mini reasoning, C++ code-reading), np concurrent requests per wave, 256 greedy tokens, ignore_eos, A-B interleaved per np, 3 rounds, fresh server per cell. Rule: per np D=x wins iff aggregate tok/s beats the other by >=3% in every round; recommend the D that wins or ties at every np, else report the per-np split plus the throughput-weighted pick at the lane operating np 8. Sufficiency: question = which D gives the higher aggregate decode tok/s at np 4/8/16; expected effect >=3% aggregate gap vs <=1.5% round noise; reuse the e2e row for np=1; stop-on-answer when 3 interleaved rounds give a per-np winner or tie at every np; stop-on-futility on any invalid cell or when all np tie within 3% after round 3; gate-class = futility-only. Measure only; any recipe change goes to the operator. Its result should replace the D=4 throughput cells in orchestration/gpu_shadow_lane_np_ceiling.yaml (qwen36_35b_a3b_q8_bridge.measured_aggregate_decode_tok_s). region: mi210_0,88-95,184-191; est 4500 s; row rka-a3b-gpu-d-np-sweep-20261118. [no-belief: new box] ✅ 2026-11-19 rc=0, row rka-a3b-gpu-d-np-sweep-20261118-r3: RECOMMEND_D2 at np4/8/16 (default-arm D2 vs D4 per-round gains 10.15–13.58%, 11.65–13.55%, 11.30–13.91%); DROP_MULTI, D2 knob gains +0.91%, -0.72%, -0.18%. Mixed-prompt aggregate D4 means 83.098/86.383/91.502 tok/s at np4/8/16; these do not resolve the separately indexed 2048/8192 prompt cells. RESULT.json SHA-256 90a803d8f0422f6f26bcf6069a4fb36e0262199d9904b71fa27e01f28e73fcd2. ✅ 2026-11-19

#### Fast-path dispatch decision record — design (2026-11-23)

Emit one structured, versioned host-side record for the first decision in each process and op-shape class, for both acceptance and rejection. The class key includes op, device/architecture, input and output types, dimensions and relevant strides, plus the effective knob values that affect dispatch. A changed key is a new class. Fields: schema version; process and device identifiers; op and class key; chosen route (fast or native); stable reason code; kernel identifier (explicit native identifier on fallback); build artifact SHA-256; and each controlling knob's effective value and source (explicit environment/configuration, compiled default, or unavailable). Missing build identity or knob source must be explicit, never inferred as a match. The record describes a **decision**, not successful completion or a timing result.

At the host dispatch boundary, evaluate eligibility and resolve the route before the first kernel launch or destination write. Emit the selected route and reasons once per class immediately before launch, using the ordinary process log or a readable structured sidecar, with synchronized once-per-key bookkeeping for concurrent host callers. A dry-run `explain` uses the same selector but does not launch, mutate output, initialize device resources, or increment launch counts. A row can require a matching process, build digest, class and selected fast-path record as its engagement witness; absence remains unknown, not proof that native ran. This would have supplied the missing B-arm route witness for **C16-TOPK-STAGE** and **C15-GV-BW**; it does not repair their other identity or protocol defects or change their verdicts.

Audit each fast route (including topk ASM, GQA verify, and Q8 in-place/skinny/MF): all eligibility rejects and native fallbacks must precede any fast-path launch or partial output write. After launch starts, propagate errors with route, kernel and build identity; do not retry through native code. Check launch and asynchronous errors at the existing appropriate completion boundary without adding a synchronization solely for logging. For HIP graphs the dispatch decision is fixed at capture: the first record witnesses the capture decision for that class, not each graph replay. First-call bookkeeping must be capture-safe and must not add host/device synchronization or collective setup.

Existing witnesses are partial: at fork `a6a32c1`, `fattn-gqa-verify.cu:648-655,731-735` has debug-gated rejection/acceptance text, and `:828-847` emits first-use path/variant messages; `topk-moe-asm-gfx90a.cu:19` documents a first-use/reject-reason log and `GGML_HIP_TOPK_ASM_LOG=1` per-call logging. Neither is the complete per-class build-and-source record above. The per-row `cpu_route_witness.py` is an oracle, not a process-wide HIP decision record. This is a design contract only; implementation and route audit are future work. Sources: [intake-2839](../../research/deep-dives/intake-ak-1123/intake-2839-aiter7240.md), [intake-2828](../../research/deep-dives/intake-ak-1123/intake-2828-aiter0130.md).

#### Research Intake Update — 2026-11-17 (BLACKFURY Exact / TensorFold patches, intake-2674; operator-approved 2026-11-17)

- [x] **INF48-FAVEC-TAIL — Exact-order split-KV decode-attention probe for the 27B Q8_0 architect on MI210 (intake-2674).** Profile flash_attn_ext_vec at n_kv 32k/64k/128k for batch 1 and DFlash2 verify batch (n_drafted+1), recording CU occupancy and FA share of decode. If FA > 15% of decode at 64k and occupancy < 50%, build a default-off candidate that splits KV into fixed chunks with a fixed-order merge (reduction order pinned so output is bitwise identical across runs). Gate: bitwise token-ID identity vs C13 on 3 fixed prompts × drafted/plain, then A-B-B-A warm-decode medians. Stop on futility if FA share < 15% or the candidate is < +2% at 64k. Sufficiency: the question is whether FA decode is occupancy-bound at depth; the expected effect (source +4.58% at 128k on another GPU) is larger than run-to-run noise (about 1%). Reuse the C10 rocprofv3 trace first.
  - 2026-11-17 grounding + candidate (autokernel): **Serving kernels (C13 bda43aa17 source):** decode n=1 -> `flash_attn_ext_vec` (C10 rocprofv3 anchor); DFlash2 verify n=8 -> gv GQA-verify (`fattn-gqa-verify.cu`). Neither main kernel is grid-starved: `launch_fattn_vec` already picks parallel_blocks so 24 dst tiles x parallel_blocks fill >= 95% of a wave of nsm x occupancy (~17 KV splits, ~400 blocks on 104 CUs at depth); gv uses ~2 x nsm / n_head_kv KV splits (knob `GGML_CUDA_FA_GQA_VERIFY_SPLITS`). Both merge in fixed ascending split order. The intake-2674 8->40 gap exists here only in the **combine tails**: `flash_attn_combine_results` = 24 blocks (n_q x n_head), `gv_merge_kernel` = 192 blocks. **Trace share:** the C10 trace (`c10-c6-dispatch-reprofile-20261110-r2`) is a short-context D=64 tg128 trace (FA vec 10.3% of GPU time there), not the 27B at depth; the 27B share at 64k is measured in the row (16 FA layers x FA op us / decode us per token). **Candidate:** default-off `GGML_HIP_FA_TAIL_SPLIT=S` (2/4/8) splits each head of both tails into S d-slices. Per-element reduction expression and order are unchanged, so the claim is bitwise identity vs stock, not only run-to-run determinism. 27B-shape FA cases are appended to the eval and perf lists. Branch `llama.cpp-experimental-c13-favec-tail-20261117` @ `a01b44adc` (fork). Row `inf48-favec-tail-c13-20261117` (gpu-q3, timing bench) published; smoke is queued for the next GPU gap. Gates: FA corpus knob on/off, token-ID identity C13/off/S* x plain/DFlash2, A-B-B-A llama-bench tg32+pp8 at d 32k/64k/128k. Rule: KEEP >= +2% at 64k with CI > 0; futility if FA share < 15% or gain < 2%. Prior expectation: small, because the tail is a tiny kernel. [no-belief: row pending; verdict filed by autokernel]
  - ✅ 2026-11-18 inf48-favec-tail-c13-20261117: **fail, closed as FUTILITY (gain)** — splitting the combine tails gives no consistent gain at depth: op-level FA time knob off vs S=8 kv32k nb1 318.7->302.1 us (-5%), kv64k 581.1->575.4 (-1%), kv128k 1118.7->1145.7 (+2%), nb8 within +-1.5%; correctness clean (3103/3103 for S=2/4/8, no NaN, no crash). Offenders for the verdict: the speed gate (<+2% at 64k); the row's NOT_EXACT identity flag is NOT valid evidence, because the knob-OFF build also failed to reproduce C13 tokens (the GPU A-vs-A divergence, C10-GPU-GREEDY-AA-DIVERGENCE) and the row had no A-vs-A calibration. Branch `a01b44adc` is not pursued. [belief: cc]
- [x] **RKA-DECISION-RECORD-1** [non-inference] Specify one fast-path decision record for the fork's HIP dispatch (design only; intake-2839#00, intake-2839#04): route chosen, reason, kernel id, build digest and knob source, emitted once per process per op-shape class and readable without a profiler, plus an audit rule that no fast path may fall back after launch. Motivation is in-house: C16-TOPK-STAGE and C15-GV-BW closed with the witness absent, and today only per-row oracles exist (cpu_route_witness.py, the once-per-process witness at fattn-gqa-verify.cu:828-830 @ a6a32c1).
      · done when: design section committed in rocm-kernel-authoring.md naming the record fields, emit points and the two closed rows it would have unblocked
      · gate: none
      ✅ 2026-11-23 [no-belief: software] 714f8603c3dd — root design commit; choice: one versioned host record per process and op-shape class, with a dry-run selector and no fallback after launch. Design only; no runtime implementation or GPU measurement.
- [ ] **RKA-TRACE-SHARES-1** [non-inference] Answer two upstream-port questions from existing traces and arithmetic only (intake-2826#04, intake-2840#00, intake-2840#01): (a) the share of `flash_attn_mask_to_KV_max` in prefill GPU time on the served 27B and Q38FN traces (it only launches when Q->ne[1] >= 1024 or ne[3] > 1, fattn-common.cuh:1493 @ a6a32c1); under 1% closes the ballot-reduce port; (b) for np4 KV-length mixes, max/mean live KV chunks per block in the gv GQA-verify kernel under uniform splits (fattn-gqa-verify.cu:769-781 @ a6a32c1) for padded and unified layouts; max/mean <= 1.15 closes the min-max planner idea, > 1.3 files one GPU row.
      · done when: both numbers with the trace paths recorded under this box and each idea closed or a row filed
      · gate: none
- [x] **INF48-GATEUP-PROBE — From an existing decode trace of the 27B on MI210 and CPU, measure gate/up mul_mat launch and activation-quantize overhead; open a paired-launch candidate only if the combined overhead is > 2% of decode (intake-2674).** 2026-11-18 CPU half: row inf48-gateup-cpu-prof-20261118 (proxy profiler store c8rbseq-prof for per-node gate/up share + perf on v10 for quantize share); stop-on-answer when 2 reps agree within 0.5 pp on X at each depth (0, 8192), CANDIDATE iff median X > 2%; stop-on-futility on missing input/unusable profiler and perf, or 2.0 inside the 4-rep spread (INCONCLUSIVE_SPREAD); gate-class = futility-only. ✅ 2026-11-18 CLOSED, no paired-launch candidate on either device. GPU (f834d3d24): gate+up already one fused launch, FFN quantize ~0.87%. CPU (row inf48-gateup-cpu-prof-20261118): upper bound X 1.52% @0 / 1.25% @8192 (< 2%), quantization 0.48% of decode. Spin-off C15-EPI-Q8 (producer-epilogue q8_1, GPU) queued. [no-belief: row verdict filed by agent]
  - 2026-11-18 offline trace analysis (autokernel): **GPU NO-GO; CPU unmeasured.** MI210 trace: Qwen3.8-27B-Q8_0, tg at depth 8192, rocprofv3 `c8-h17-profile-20261107/.../smoke-tg_d8192-*/prof_kernel_trace.csv`, decode dispatches only. Gate+up is **already one fused launch** (`mul_mat_vec_q<Q8_0,..,true,true>` with mm_fusion_args, 17408 rows): 29.3% of decode, all weight bandwidth, 0 us gap before it. The only overhead tied to gate/up is the FFN-input `quantize_q8_1` (5120 wide, 4.5 us × 64 layers), **≈0.87% of decode**, below the 2% bar. All activation quantization together is 3.56%, but removing it means folding quantization into mmvq in general, not a paired launch. CPU: no 27B per-op decode profile exists. A minimal trace row is drafted, NOT PUBLISHED, at `/mnt/raid0/llm/tmp/inf48-gateup-probe-20261118/spec-draft-cpu-27b-tg-prof.json`. Box left open for the CPU half. Write-up: `research/deep-dives/inf48-gateup-probe-20261118.md`. [no-belief: offline trace analysis]
- [x] **C16-TOPK-STAGE** [inference] [origin: autokernel-session self-scouting 2026-11-18, NOT backlog-mandated; boxed per operator so it is documented] A3B MoE router chain is unfused at verify n>=2 (6 launches, ~1.9 ms = 5.6% of an n=4 MTP verify step on MI210) because the topk-moe fusion overlap check only exempts single-row batches; fix stages the router logits to scratch so the fused AITER topksoftmax runs (research/deep-dives/mi210-next-hotspots-20261118.md, c7dd1859a). Knob GGML_HIP_TOPK_MOE_STAGE=1 (default off), branch llama.cpp-experimental-c16-gpu-next-20261118 @ c6294773f on C16 13d6fc150. model: Qwen3.6-35B-A3B MTP Q8_0 on MI210 (27B control: staged path must not engage). Row c16-topk-stage-gpu-20261118: tbo TOPK_MOE on/off, op timing n=1,4,5,8 @32k, e2e A3B MTP D4 ABBAABBA. stop-on-answer: KEEP iff e2e geomean >= 1.02, no cell < 0.99, A/A-calibrated identity, witness in every knob-on visit only; stop-on-futility: n=4 op ratio < 1.005 or no witness, or e2e < 1.003 after 3 pairs; gate-class = futility-only. [no-belief: planning] Result 2026-11-19: DROP(FUTILITY_OP), rc=0; B engagement witness absent in both visits despite n=4 A/B=1.0440; TOPK_MOE 320/320 in each arm, 27B control did not engage; no e2e verdict. RESULT.json SHA-256 7fa8dc2a242242a42cba61659f1caf0617f9f5438b56ec3d7a569a3792d10eff, /mnt/raid0/llm/tmp/c16-topk-stage-gpu-20261118/out/RESULT.json. ✅ 2026-11-19
- [x] **C15-GV-BW** [inference] [origin: autokernel-session self-scouting 2026-11-18, NOT backlog-mandated; boxed per operator so it is documented] gv_fattn KV-read bandwidth (14% of MI210 HBM at 128k; latency-bound, 1 WG/CU, prefetch depth 1). Knobs GGML_HIP_GV_PREFETCH_DEPTH=2|3, GGML_HIP_GV_LDS_ALIAS=1 (branch llama.cpp-experimental-c15-gv-bw-20261118 @ dfcaa42ff; research/deep-dives/c15-gv-fattn-bandwidth-20261118.md). model: Qwen3.8-27B Q8_0 (+DFlash2) on MI210. Row c15-gv-bw-gpu-20261118. stop-on-answer: KEEP iff no-draft decode d128k >= 1.10, d32k >= 1.05, d4k >= 0.99, DFlash2 >= 0.99; stop-on-futility: op-level FA < 1.10x @128k for every variant; gate-class = futility-only. Parent: C8-1-H17. [no-belief: planning] Result 2026-11-19: registered DROP(clauses), rc=0; alias 128k op geomean 1.5537x, all arms 76/76; zero valid no-draft pairs at all depths because B witness absent; DFlash2 B/A median 1.0085 but 1/4 B hashes mismatched with all A/A exact. End-to-end performance remains inconclusive; DFlash2 prompt_n=4 also conflicts with the registered 32768-token prime. results.jsonl SHA-256 973da60992643c6d487de839fa469b3fb2347d1a6dafea544bf680a9db2129f7; RESULT.json SHA-256 f28dbe5dfb123ec5869e15e8d5c344097908dae89cf8e87fa9fe6f6d0c09643d. [belief: cc] ✅ 2026-11-19
- [x] **C15-GV-COALESCE** [inference] [origin: autokernel-session self-scouting 2026-11-18, NOT backlog-mandated; boxed per operator so it is documented] gv_fattn coalesced 16B K/V loads + XOR LDS swizzle, stacked on C15-GV-BW (knob GGML_HIP_GV_COALESCE=1, branch llama.cpp-experimental-c15-gv-coalesce-20261118 @ bb2570042). model: Qwen3.8-27B Q8_0 on MI210. Row c15-gv-coalesce-gpu-20261118 (base A/A digest calibration). stop-on-answer: same KEEP bars as C15-GV-BW; stop-on-futility: op-level < 1.10x @128k for every arm; gate-class = futility-only. Parent: C8-1-H17. [no-belief: planning] ✅ 2026-11-19

#### Q8MF reuse outside tree verify — 2026-11-20 (autokernel)

- [x] **Q8MF-REUSE-NP-DECODE** [inference] Route multi-slot target decode (np 2-16) on the GPU 27B Q8_0 and the A3B through the small-M Q8_0 GEMM (GGML_HIP_Q8_MF, MF_MIN=1): batched decode is a MUL_MAT at M = np, the exact shape the kernel streams weights once for. Wire the route for n_tokens = np decode steps (not only verify ubatches), on a branch off the V3 commit.
      · done when: one commit routing np 2-16 decode onto the V3 kernel with CPU tests and op-perf GB/s at M 2/4/8/16, then a paired llama-bench -np 2,4,8,16 row filed with verdict KEEP / NO_GAIN / LOSS / FAIL_CORRECTNESS
      · gate: DTREE-0-Q8MF-V3 (speculative-decoding.md) landing; do not start before
      · M range: 2-16 (np 2..16)
      · expected gain (inferred from filed numbers): 27B ATTRIB-V2 ms per step W1/4/8/16 = 37.6/50.2/52.9/56.6 with V2 GEMMs 38.8-42.6 ms at ~0.7 TB/s; at V3's >= 1.2 TB/s on ~28 GB the GEMM term is ~23 ms, so np4-16 steps drop ~15-19 ms (~30-35%), i.e. ~+40-50% aggregate tok/s at np4-16. A3B (C14 GPU np sweep, pipeline): 37.6/55.4/91.6 tok/s at np1/2/4 -> 26.6/36.1/43.7 ms per step, ~4.3 ms/row marginal; if the dense+expert few-row GEMMs reach roofline the marginal falls toward ~1-2 ms/row: ~+15-35% aggregate at np4, confidence low (MoE share depends on DTREE-A3B-MOE-ROOFLINE)
      · falsification: op-perf GB/s at M 2/4/8/16 on the 27B and A3B decode shapes; if V3 is not >= 1.1x MMVQ/wvsk at every np in 2..16, or a paired llama-bench -np {2,4,8,16} aggregate shows no cell above +0.84%, the lever is dead
      · gates for KEEP: correctness (MUL_MAT ROCm0 corpus), aggregate decode gain beyond the GPU W2 floor 0.84% at each np claimed, np1 within +-0.84%; numerics change (f16 MFMA path) -> 27B KLD <= 0.003
      · 2026-11-20 measurement row ak-q8mf-np-decode-gpu-20261120 (operator overnight GPU fill). The in-place store already sends M >= 1 Q8_0 MUL_MAT to the packed V3 kernel under MF_MIN=1, so batched decode is measured without a new route commit. build: /mnt/raid0/llm/worktrees/llama-dtree-q8inplace-20261120/build-hip (fork 0689c70ee, C16-based, libggml-hip sha256 05809e9f...; llama-batched-bench + llama-batched added to the store, lib bytes unchanged). models: Qwen3.8-27B-Q8_0, Qwen3.6-35B-A3B-MTP-Q8_0 (A3B both arms + GGML_HIP_MMVF_CDNA_MAX_NE11=8). arms: X = GGML_HIP_Q8_WVSK_MAX=16; V3I = X + GGML_HIP_Q8_MF=3 MF_MIN=1 MF_INPLACE=1. question: does V3I raise aggregate decode tok/s over X at np 2-16? metric: llama-batched-bench -npp 128 -ntg 64 -npl 1,2,4,8,16 aggregate S_TG and per-request S_TG/np; greedy identity via llama-batched --temp 0 at each np. decision rule: KEEP iff some np >= 2 has a paired V3I/X aggregate ratio 95% CI-lower > 1.0084 AND greedy output is identical V3I vs X at every np; GAIN_NOT_IDENTICAL / LOSS / NO_GAIN otherwise. stop-on-answer: 3 fixed rotated-ABBA repeats; stop-on-futility: missing input, residency, wrong grant, 27B packed witness absent. estimate 2700 s (24 visits x ~50 s + 20 identity runs x ~35 s, x1.25). gate-class = futility-only. rank 25.
      · Result 2026-11-21: GAIN_NOT_IDENTICAL (filed fail, rc 0), row ak-q8mf-np-decode-gpu-20261120-r2. r1 was NOT_JUDGEABLE: no -v, so the packed witness was not logged. Paired V3I/X aggregate S_TG, mean [95% CI]. 27B: np1 0.853 [0.824,0.882], np2 1.018 [0.991,1.046], np4 1.073 [1.046,1.100], np8 1.018 [1.011,1.025], np16 1.142 [1.127,1.157] (148.5 -> 169.6 tok/s). A3B: np1 0.809, np2 0.902 [0.827,0.977] LOSS, np4 0.945, np8 0.974, np16 0.997. Greedy sequences differ V3I vs X at every np 2-16 on both models (f16 MFMA numerics); the np1 identity check was vacuous. VRAM +150 / +16 MiB. Next: a numerics (KLD) gate, not identity, decides a 27B np>=4-only route; A3B np decode stays on X. RESULT /mnt/raid0/llm/tmp/ak-q8mf-np-decode-gpu-20261120-r2/out/RESULT.json. [no-belief: row verdict filed by agent] ✅ 2026-11-21
- [x] **V3I-LONGCTX** [inference] Check that the in-place repack (V3I) does not regress long-context single-stream decode. build: /mnt/raid0/llm/worktrees/llama-dtree-q8inplace-20261120/build-hip (fork 0689c70ee). model: Qwen3.8-27B-Q8_0, q8_0 KV, FA on. arms: X = GGML_HIP_Q8_WVSK_MAX=16; V3I = X + GGML_HIP_Q8_MF=3 MF_MIN=1 MF_INPLACE=1. question: is V3I tg32 tok/s at depth 4k/32k/128k within the 0.84% GPU floor of X? decision rule: REGRESSION iff some depth has a paired V3I/X ratio 95% CI-upper < 0.9916; NO_REGRESSION iff every depth point ratio >= 0.9916 and none REGRESSION; INCONCLUSIVE otherwise. Prior (ak-dtree0-q8inplace-gate-gpu-20261120): W1 is forced onto packed V3 (37.0 vs 32.3 ms at d0), so a d4k regression is expected; this row measures how it shrinks with depth. stop-on-answer: 3 fixed rotated-ABBA repeats; stop-on-futility: missing input, residency, wrong grant, packed witness absent. estimate 3600 s (12 visits x ~180 s incl. 128k fill, x1.25). gate-class = futility-only. Row ak-v3i-longctx-gpu-20261120, rank 35.
      · done when: row ak-v3i-longctx-gpu-20261120 filed with verdict NO_REGRESSION / REGRESSION / INCONCLUSIVE (or a futility verdict) and this box ticked against it
      · Result 2026-11-21: INCONCLUSIVE (filed, rc 0), row ak-v3i-longctx-gpu-20261120. Paired V3I/X tg32 tok/s ratio, mean [95% CI]: d4096 0.959 [0.893,1.026], d32768 0.988 [0.749,1.228], d131072 0.978 [0.698,1.259]. No REGRESSION is proven, but no point reaches 0.9916, and the -r 1 visits leave a ~25% CI half-width at 32k/128k. VRAM equal. Consistent with the W1 packed-V3 cost diluting with depth. A firmer answer needs -r >= 3 per visit. RESULT /mnt/raid0/llm/tmp/ak-v3i-longctx-gpu-20261120/out/RESULT.json. [no-belief: row verdict filed by agent] ✅ 2026-11-21
- [x] **Q8MF-V5I-NP-DECODE** [inference] Successor to Q8MF-REUSE-NP-DECODE on the best kernel, judged by the operator 27B-anchored numerics gate instead of byte identity. build: /mnt/raid0/llm/worktrees/llama-dtree-q8v5-20261120/build-hip (fork 1778cda76, adds llama-batched-bench / llama-batched / llama-perplexity). arms: X = GGML_HIP_Q8_WVSK_MAX=16; V5I = X + GGML_HIP_Q8_MF=6 MF_INPLACE=1 MF_SLC=1; A3B both arms + GGML_HIP_MMVF_CDNA_MAX_NE11=8. models: 27B Q8_0 and A3B-MTP Q8_0, np 1/2/4/8/16, aggregate and per-request tok/s. KLD unit: 27B llama-perplexity --kl-divergence V5I vs X base, wiki.test.raw -c 512 --chunks 16 -ub 16 (MF=6 runs at M 9-16, so -ub 16 exercises V5). decision rule: KEEP iff some np >= 2 has aggregate ratio CI-lower > 1.0084 AND 27B KLD <= 0.003 AND |dPPL| <= 0.5%; GAIN_KLD_FAIL / LOSS / NO_GAIN otherwise; greedy identity recorded, not gated. stop-on-answer: 3 rotated-ABBA repeats + identity + KLD; futility: missing input, residency, wrong grant, V5/packed witness absent. estimate 3300 s. Row ak-v5i-np-decode-gpu-20261121 (supersedes ak-q8mf-np-decode-gpu-20261120-r2), rank 25.
      · done when: row ak-v5i-np-decode-gpu-20261121 filed with a terminal verdict and this box ticked against it
      · Result 2026-11-21: KEEP (filed pass, rc 0), row ak-v5i-np-decode-gpu-20261121. Paired V5I/X aggregate ratio, mean [95% CI]. 27B: np1 0.941 [0.903,0.979], np2 1.107 [1.057,1.158], np4 1.109 [1.065,1.153], np8 1.045 [1.044,1.047], np16 1.170 [1.152,1.188]. Aggregate tok/s X->V5I: np4 76.4->84.7, np16 146.8->171.7. Per-request tok/s: np16 9.17->10.73, np1 32.3->30.4. A3B: np1 0.884 [0.811,0.957], no gain at np>=2 (np16 1.020 [0.993,1.047]). 27B KLD 0.000596, dPPL +0.126% (7.4632->7.4726), same top-1 98.70%. Passes the 27B-anchored gate. Greedy identity differs at every np (recorded only). The np1 cost on both models means an np>=2-only route. [no-belief: row verdict filed by agent]
- [x] **V5I-LONGCTX** [inference] Successor to V3I-LONGCTX on V5I (r1 was INCONCLUSIVE: -r 1 visits gave +-25% CIs). build as Q8MF-V5I-NP-DECODE. model: 27B Q8_0, q8_0 KV, FA on. llama-bench -p 0 -n 32 -d 4096,32768,131072 -r 3 per visit, 4 rotated-ABBA repeats (8 visits per arm). decision rule: KEEP_NEUTRAL iff no depth's paired V5I/X ratio CI-upper < 0.9916; REGRESSION otherwise; ratio reported per depth. tg is M=1, so only the in-place packed witness gates. stop-on-answer when 4 fixed rotated-ABBA repeats are done; stop-on-futility on missing input, residency, wrong grant, packed witness absent; gate-class = futility-only. estimate 10000 s. Row ak-v5i-longctx-gpu-20261121 (supersedes ak-v3i-longctx-gpu-20261120), rank 35.
      · done when: row ak-v5i-longctx-gpu-20261121 filed with a terminal verdict and this box ticked against it
      · Result 2026-11-21: KEEP_NEUTRAL (filed pass, rc 0), row ak-v5i-longctx-gpu-20261121. Paired V5I/X tg32 ratio, mean [95% CI], 8 visits per arm at -r 3: d4096 1.009 [0.969,1.048], d32768 0.969 [0.881,1.056], d131072 0.966 [0.891,1.041]. No proven regression. The 32k/128k points are about -3%, inside CIs of about +-8%, so parity at depth is not proven either. Plain decode is unserved, so this matters only if a served drafter path hits n=1 at depth. [no-belief: row verdict filed by agent]
- [x] **V3I-OTHER-Q8-MODELS** [inference] Screen in-place-repack side effects on the other served Q8_0 GPU models. Registry scan 2026-11-20 (server_mode + roles): the only Q8_0 GPU model beyond the 27B and the A3B is the Qwen3.8-27B-DFlash2-Q8_0 drafter (coder_escalation / architect_critic / ingest_long_context); Q38FN MTP head is CPU-served, worker_vision is Q4_K_M. build: /mnt/raid0/llm/worktrees/llama-dtree-q8inplace-20261120/build-hip (fork 0689c70ee). model: /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf standalone in llama-bench. arms: X vs V3I as above. question: does V3I change its W1 (tg64) or W8 (pp8) tok/s? decision rule: REGRESSION iff some cell has a paired V3I/X ratio 95% CI-upper < 0.9916; NO_REGRESSION iff every point ratio >= 0.9916 and none REGRESSION; INCONCLUSIVE otherwise; FUTILITY_MISSING_INPUT if the dflash GGUF does not load standalone. stop-on-answer: 3 fixed rotated-ABBA repeats; stop-on-futility: missing input, residency, wrong grant. estimate 900 s. gate-class = futility-only. Row ak-v3i-otherq8-gpu-20261120, rank 40.
      · done when: row ak-v3i-otherq8-gpu-20261120 filed with verdict NO_REGRESSION / REGRESSION / INCONCLUSIVE (or a futility verdict) and this box ticked against it
      · Result 2026-11-21: FUTILITY_MISSING_INPUT at smoke (rc 3), row ak-v3i-otherq8-gpu-20261120 never became ready, so there is no file_result record. The DFlash2 drafter cannot be benched standalone (llama-bench: "dflash requires ctx_other to be set"). V3I does pack it (32 Q8_0 tensors, 1590 MiB, incl. the 256x248320 selector weights). No other served Q8_0 GPU model exists. The DFlash2 side effect can only be measured through 27B+DFlash2 speculative decode (llama-server, not in this store). Smoke log: /mnt/raid0/llm/tmp/ak-v3i-otherq8-gpu-20261120/out-smoke/smoke-V3I.stderr.log. [no-belief: smoke futility, no measurement] ✅ 2026-11-21


### Done

- [x] **—** ✅ 2026-08-03 — via /research-intake Stage-2b; reproduces the fable5 series to within 1 pp
- [x] **—** ✅ 2026-08-03
- [x] **—** ✅ 2026-08-11 —
- [x] **—** ✅ 2026-08-11
- [x] **—** ✅ 2026-08-15 — gfx90a FP16 and

## Track: gemma-challenge-kernel-techniques-v7
<!-- gate: none -->

> Folded from `handoffs/active/gemma-challenge-kernel-techniques-v7.md` @ `779a81fd46b0` on 2026-11-03 (BRF-T7-F13, route 1b, operator D1/D5; retired row INF-16 → INF-48). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Gemma-Challenge Kernel Techniques → v7-Experimental Candidates

> **Fold destination** (BRF-T1-F22, BRF-T1-1, route 1a, 2026-11-02): absorbs 2 handoff(s) as `## Track:` sections at the end of this file (`frontier-f6-upstream-publication.md`, `llama-cpp-dsa-contribution.md`). The body above the first track is the former `gemma-challenge-kernel-techniques-v7.md`.

> **NI08 source-only start here — 2026-10-07:** `K11-REPEAT-SUMMARY-SOURCE` and the prospectively enrolled `VB-K11-REPEAT-SUMMARY-CONFORMANCE` own the current requested-repeat reporting correction and whole-module synthetic controls. Final source/native acceptance is still open. The v7 findings below are dated history; verify current source and frozen production identity before any experimental work. Live natural-prose determinism and kernel runs remain separate gates.

**Status**: active — onegraph structural check ✅ (re-audited) + HIP graph infra verified ✅ + **K2 MI210 smoke-test/bench ✅ (2026-07-11)**. K2: per-decode HIP graph capture engages on MI210 and is net-positive on Q8 (A4B MoE decode +4.3% / **spec-dec +25%**; dense-31B +6.1% / +3.4%) — but A4B **Q4** spec-dec regresses ~−5%. **K7 root-caused it: the thrash is VERIFY-side** (target verify batch = n_drafted+1 varies with acceptance → warmup resets), NOT the draft loop (which is already shape-stable and replays). The candidate fix **Lever A — a shape-aware graph cache key** was implemented (env-gated) but a clean quiet-host re-eval measured it **NEUTRAL** (Q8 spec-dec −2% with byte-identical output → correctness-safe, no speedup; Q4 +6% noisy) → **NOT landed**, source reverted, preserved as `llama.cpp-experimental/lever-a-shape-key.patch`. The **onegraph single-graph fold is DEFERRED** (very-high effort, lower-EV — it fuses the already-optimal draft decodes, not the verify thrash). GRAPH_OPT=1 and Q8_PREFETCH levers both tested → net-negative, rejected. Also validated graphs generalize beyond gemma4 (Qwen dense/MoE base decode +7–14%; native-MTP spec-dec only +2%, so the +25% is gemma4-external-head-specific). **2026-07-16 v7 cleanup:** K14 HIP backend-ops blocker was resolved in the then-current `experimental-v7-candidate` worktree with flash-attn selector/device-guard fixes; full `test-backend-ops` passed on MI210. `ngram-mod` retest shows workload-dependent speed upside but is not quality-cleared. **2026-07-16 v7 perf/server A/B:** refreshed candidate `8e5c555ab` passed the backend gate earlier, the direct base-decode report and server artifacts captured production-shaped perf, and the launcher guard landed in orchestrator so stack-launched llama-server commands always pin `--device none` and speculative launches also pin `--device-draft none`. **2026-07-19 promotion authority sync:** the authoritative promotion branch is `experimental-v7-refresh-20260716`; the validated promotion candidate is frozen at `6ad45fa3ff` / binary `10098`, and older `experimental-v7-candidate` references are historical evidence only. Scope: lossless only. The narrow upstream-ahead fixes, OP-2 CPU-regression canonical bench, `P-GPU-1` ratification, K5 quality baseline, K35/A1 release artifact, GLM reviewer disposition, and final readiness/server smokes are closed. Post-candidate `12a292f0c` repaired native GLM-MTP serving and `93d945885` added a default-off CPU `CONCAT` dim0 row-partition prototype; those are valuable research deltas but require a fresh exact-tip final smoke before replacing frozen `6ad45fa3ff` as the promotable artifact. Reviewer/control-plane routing is decoupled by operator decision and is not a v7 release blocker; actual promotion is the operator cutover step tracked in `v7-promotion.md`.
**Categories**: speculative_decoding, hardware_optimization, quantization, local_inference
**Source**: intake-798 — "The Gemma Challenge and the Case for Agent Collabs" (HF + Google DeepMind)
**Related**: [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh) (onegraph deep-dive lives here), [`gpu-drafter-mi200-investigation.md`](../archived/gpu-drafter-mi200-investigation.md) (GPU-graph home), [`v6-iqk-promotion.md`](../completed/v6-iqk-promotion.md) / [`kernel-reconciliation-audit.md`](../completed/kernel-reconciliation-audit.md) (the v7 workflow), [`gemma4-mtp-drafter-evaluation.md`](../completed/gemma4-mtp-drafter-evaluation.md)

#### Objective

The Gemma Challenge (100+ agents, 6 days) drove `google/gemma-4-E4B-it` inference 5× — the **same MTP-drafter family and model family as our production `worker_general`** (gemma-4-26B-A4B, Google official assistant head). **v7 was never promoted to production**, so the `llama.cpp-experimental` line is a clean slot to fold the *validated, quality-preserving* subset of these techniques into a v7 candidate — via the mandated four-step experimental workflow (fresh-pull production → build → validate-no-regression → promote), never touching frozen production kernels.

#### Governance rails (non-negotiable, per CLAUDE.md)

- **Production kernels are FROZEN.** All work on `llama.cpp-experimental` (fresh-pulled from current production tip first, so the iqk AVX-512 GEMM + CPU forward-ports are already present — do not repeat the 2026-06-22 GPU-opts fork that silently lacked the entire iqk subsystem).
- **Quality gate is the gate, not TPS.** The challenge's own lesson: a **PPL-only** gate was gamed (top lossy submission held PPL but lost **15 GPQA-Diamond / 40 MMLU-Pro** points). Any v7 candidate must pass downstream evals (MMLU-Pro + GPQA-Diamond), production sampling (seed 42), per [`MEASUREMENT.md`](../../MEASUREMENT.md) + eval-tower — **not** PPL alone. This is a hard prerequisite, especially for the lossy techniques below.
- **Inference is operator-gated** (`feedback_no_concurrent_inference`); bench only via codified recipes with approval.

#### v7 Promotion Readiness (2026-07-18 — lever audit)

**v7 is the highest-EV performance lever on the whole stack, and it is already built and
banked — the remaining work is operator gates, not engineering.** Current tip:
**`experimental-v7-refresh-20260716` @ `6ad45fa3ff`** (verified on disk: iqk present, GPU-opt
flags present, `GGML_TYPE_Q2_0`=42 present — the earlier missing-Q2_0 freshness hit is closed
by this refresh; the narrow upstream-ahead Hadamard/TP-split fixes are applied and focused-test validated).

**Banked, correctness-verified, runtime-gated-off wins:**
- HIP graphs (per-decode capture) **+25%** worker spec-dec (A4B MoE), +4–14% base decode
- MMVQ→MMQ small-batch verify-dispatch (`de447119f`) **+17.4%** MTP-verify / **+31.7%** gemma-31B
- nwarps 2→4 (`5dc116130`) +4.6%; async prefetch (`7c28056b7`) +3.3%
- bf16 GDN recurrent-state (`496e2f098`) **+21.5% @B32** (frontdoor 35B-A3B +17.7%, architect 122B +16.4%)
- single-stream dense-Q8 **+37%** (29→40.4 t/s)

**Gates cleared:** K5 quality gate PASSED (v6 vs v7 MMLU-Pro/GPQA **+0.0%**); P0 correctness
blockers all resolved — K22 grammar-sampler (`96986f5e9`), K23 GLM-DSA load (`3dee86a5a`),
K32/K33 external-draft path; K24 base-decode "regression" ruled a host artifact (not source).

**Remaining gates (LANE A, operator-facing):**
- A1 — **K35 consolidated throughput-vs-context matrix CLOSED ✅ 2026-07-18**:
  operator-facing report now includes non-vision context rows, vision throughput/quality/memory
  rows, MiniCPM-o/frontdoor mixed-service matrix, and the controlled MiniCPM-o live smoke
  (`K35.13f`). Remaining K35 work is optional parser/stress follow-up only, not release-blocking
  matrix evidence or the already-landed source/config/live-smoke path.
  - **SUPERSEDING NOTE 2026-07-31 — applies to every K35 MiniCPM-o item in this file (K35.4,
    K35.5, K35.11–K35.14, K35.13a/c/d/f).** MiniCPM-o is **DEPRECATED and its weights DELETED**.
    The K35 throughput, co-residency, service-tax and service-matrix measurements below are
    **not retracted** — they were real and correctly reported. What is retracted is the
    **conclusion drawn from them**: K35.11's "first fast quality-clean higher-speed escalation
    candidate", K35.13's activation policy, and K35.14's "MiniCPM-o preferred" ranking all rested
    on a **4-question** fixed OCR/chart fixture set, which every candidate passed `4/4` and which
    therefore could not discriminate on quality at all. On **42** questions (OCRBench + ChartQA,
    MI210, best-on-disk quant per arm) MiniCPM-o scores **31/42** against the Qwen2.5-VL-7B
    incumbent's **35/42**. The 2026-07-18 activation policy is **REVOKED**; `vision_escalation`
    stays Qwen2.5-VL-7B. Raw: `/mnt/raid0/llm/tmp/vlquality_results.json`. **Methodological
    lesson worth keeping:** a saturated fixture set (everyone `4/4`) reads as "quality-clean" but
    is really "no signal" — it silently converts a quality gate into a speed ranking.
- A2 — **OP-2 CLOSED ✅ 2026-07-19**: v6+iqk live throughput+garbage verify and the clean
  canonical CPU decode bench passed; B1 was skipped as `not_staged`, and B4/D3.1 closed no-go.
- A3 — **`P-GPU-1` ratification CLOSED ✅ 2026-07-19**: `/workspace/MEASUREMENT.md` now
  ratifies production-named-kernel-only GPU claims. Existing experimental-v7 Gate-R/K35/AXA
  rows remain observation-grade; decision-grade Gate-R reruns after promotion on
  `production-consolidated-v7`.
- A4 — **branch-naming reconciliation CLOSED ✅ 2026-07-18**: authoritative promotion branch is
  `/mnt/raid0/llm/llama.cpp-experimental` branch `experimental-v7-refresh-20260716`; frozen
  promotion candidate is `6ad45fa3ff` (`Add GLM DSA top-k mask oracle coverage`) / binary
  `10098`. The live branch may advance for post-candidate research; any newer exact tip must
  rerun final coherence+garbage smoke before it replaces the frozen candidate. The earlier `d1e5a20eb` checkpoint remains the
  branch-reconcile baseline. Older `experimental-v7-candidate` references are historical
  checkpoints only. 2026-07-19 upstream audit against official `origin/master` `571d0d540`
  is handled for the two scoped code fixes: `11fd0a6fb` (Hadamard BLAS default-to-CPU)
    and `2e1fd7649` (TP split metadata) are applied in `6a8dd5ea6` and followed by
    `6ad45fa3ff` GLM DSA top-k mask oracle coverage, while DFlash KV
  rotation and routing-table quant exclusion were already covered locally.

**K28** (GDN long-prefill recurrence kernel, GPU, `gated_delta_net.cu:191`) is owned as a `- [ ]`
task in [mi210-big-model-and-acceleration-roadmap.md](../completed/mi210-serving-program.md#track-mi210-big-model-and-acceleration-roadmap).
2026-07-18 source-readiness sidecar verdict: do not patch blindly. Functional chunking already
exists in `delta-net-base.cpp`; the open target is the serial token scan in
`ggml/src/ggml-cuda/gated_delta_net.cu`. Next step is an operator-window `rocprofv2`
GATED_DELTA_NET profile over 64/65/256/1024-token GDA/KDA shapes, then a separate
runtime-gated chunked kernel only if recurrence latency, not memory traffic, dominates.
2026-07-20 follow-up: the cheap policy switch has now been falsified. A temporary
`LLAMA_DISABLE_FUSED_GDN_CH=1` probe compared fused GDN-CH against the existing
graph chunking path on Qwen3.6-35B-A3B Q8 MI210 prompt-only cells; graph chunking
lost by `-6.30%` to `-6.69%` from p64 through p8192. Keep K28 open only for a
real fused-kernel recurrence improvement or a separately gated BF16-state/model
quality path.
The BF16-state speed leg also closed neutral on 2026-07-20: existing
`GGML_CUDA_GDN_STATE_BF16=1` slightly regressed prompt-only rows (`-0.76%` to
`-0.79%`) and improved decode-only by only `+0.74%` on the same Qwen3.6-35B-A3B
Q8 MI210 slice. Treat it as memory/residency research, not a v7 throughput
lever.
2026-07-20 direct-timing follow-up: because `rocprofv2`/`rocprof`/`omniperf`
were unavailable, experimental post-candidate commit `8bb53c520` added a
default-off `GGML_CUDA_GDN_TIMING=1` HIP-event timing hook for
`GGML_OP_GATED_DELTA_NET` (requires `GGML_CUDA_DISABLE_GRAPHS=1`). Focused
validation passed: `build-hip` `test-backend-ops` built cleanly and
`test-backend-ops test -o GATED_DELTA_NET -b ROCm0 -j 8` passed `38/38`.
Qwen3.6-35B-A3B Q8 MI210 direct timing measured GDN at `15.45%` of p2048
prompt wall-clock and `14.64%` of p8192; a 4x GDN-op speedup maps to only
`11.59%` / `10.98%` full-model prompt gain. Evidence is pushed in
inference-research commit `2c2b94b7` under
`data/k28_gdn_perf/k28-gdn-op-timing-hook-qwen35-20260720Tcurrent/`. This
validates the Phase 0 ceiling rather than reopening K28 as a frozen-v7 blocker;
any real fused recurrence prototype remains post-promotion/default-off.

#### Technique candidates (from intake-798 submissions)

| Technique | Lossy? | Our-regime fit | v7 workflow slot | Open question |
|---|---|---|---|---|
| **`onegraph`** — drafter is Q-only, KV-shared, no cross-position deps ⇒ multi-position warm-up is redundant; fold warm-up into the 7-step drafting loop, record as ONE GPU graph, single-launch replay | **Lossless** (no output change) — fastest lossless: 315 TPS | GPU-drafter path (MI210/HIP graphs) directly; **structural insight may port to CPU** MTP drafter loop | GPU-graph capture → `gpu-drafter-mi200-investigation.md`; CPU-warm-up-redundancy → `speculative-decoding-mtp-refresh.md` | **✅ STRUCTURAL + HIP INFRA ✅ (2026-07-11)**: P1-P3 satisfied. HIP graph capture is implemented and MI210 graph behavior has been benchmarked in K2/K21. The original onegraph fold is not waiting on a generic "smoke-test"; it remains deferred unless a new verify-side shape/cache implementation task is filed. |
| **Task-targeted fine-tuned drafter** — drafter fine-tuned on the eval's math/science prompt distribution to raise acceptance rate α | Lossy **as executed** (overfit to eval set); the *method* (raise α on our real workload) can be lossless | CPU + GPU spec-dec; raises α for both | Drafter-training track (new); gate via rescue-rate on real task corpus | Can we lift α on our real frontdoor/worker workload without overfitting? (`feedback_measure_alpha_before_specdec_investment` — measure α first; `frontier-f1-real-task-corpus.md` for the distribution) |
| **CUDA-graph capture throughout decode** — capture the decode routine as a replayable graph to cut per-step launch/bookkeeping overhead | Lossless (kernel-level) | GPU only (HIP graph equivalent on MI210) | `gpu-drafter-mi200-investigation.md` / `gpu-acceleration-path.md` | **✅ HIP GRAPH INFRA PRESENT + MI210 BENCHMARKED (2026-07-18)**: vendor-agnostic API mapping exists, K2/K21 recorded decode and MTP-path behavior on MI210, and remaining work must name a specific missing family or implementation lever rather than reopening a generic graph benchmark. |
| **Vocabulary pruning** — drop rarely-used vocab rows to shrink the output projection / embedding | **Lossy** (contributed to the 15/40-pt degradation) | Applies to any regime, but degrades downstream | Explore-only, hard-gated on MMLU-Pro/GPQA | Is there a *lossless* vocab-prune band (truly-dead tokens only) that survives the downstream gate? High risk. |
| **Layer removal / depth pruning** | **Lossy** (part of the 491.8-TPS lossy stack) | Any regime, degrades quality | Explore-only, hard-gated; likely reject | Almost certainly fails our quality gate; document as a cautionary boundary, low priority. |

#### Prioritization (proposed, operator to confirm)

**Scope: lossless only.** Numerical-exactness is acceptable where bit-exactness is not achievable (per past-session precedent). Lossy techniques (vocab prune, layer removal) are OUT OF SCOPE.

1. **`onegraph` GPU-graph capture** (lossless, highest value): **structural check ✅ + HIP infrastructure ✅ (2026-07-11)**. All 3 preconditions satisfied. HIP graph capture is already implemented (vendor-agnostic, `GGML_HIP_GRAPHS=ON` default, MI210 arch gate passes). **Next: smoke-test + benchmark on MI210** — verify graph capture works with MTP draft loop, measure per-token graph launch latency vs. direct dispatch. Coordinate with `gpu-drafter-mi200-investigation.md`.
2. **Drafter-α uplift** (potentially lossless): measure current α on the real task corpus before any fine-tuning investment; only pursue if α headroom is real and generalizes beyond the eval set.

#### Tasks

- [x] **K7 — onegraph/shape-cache investigation + Lever A ✅ 2026-07-11**: Lever A (shape-aware graph key) implemented env-gated → **NEUTRAL** (Q8 −2% byte-identical output, Q4 +6% noisy); not landed, reverted to `llama.cpp-experimental/lever-a-shape-key.patch`. Onegraph (Lever B) **DEFERRED** — verify-side reframe + depth sweep confirm low EV; full impl plan persisted. Retracted the noisy "n_max 2→4 +20%" (clean data: n2≈n4). See "Kernel-Optimization Levers".
- **[declined: operator 2026-11-09 (INF-48 triage, dropped, not done): conditional Lever A quiet-host re-eval; no measured bottleneck to justify it]** **K10 — (follow-up) Lever A quiet-host re-eval** — closed as dropped, not completed; original text: `git show b3bd883d3:handoffs/active/rocm-kernel-authoring.md` line 3548. [no-belief: dropped by operator 2026-11-09]
- **[declined: operator 2026-11-03 model-audit: Gemma4 worker lane retired (gemma-4-26B deleted); worker is Qwen3.6-35B-A3B]** **K11.1 — free-form sampler/stop-condition root cause for broad Gemma4 worker lane**: investigate why natural-language exact-count tasks remain unstable even with `temperature=0`, `top_k=1`, `seed=42`, and explicit stop strings. Promotion criterion: fresh-server multi-slot worker lane passes a longer task-level determinism gate in the intended natural free-form serving shape, not just a short JSON hash smoke, repeated-token exact-count prompt, or schema-constrained task. Current evidence says schema-constrained/repeated-token structured output is stable; natural prose should stay behind bounded-output policy, stronger prompt/template constraints, or a sampler/control fix.

#### GPU Graph Capture Feasibility (2026-07-11)

**Verdict (refined 2026-07-11 after K2 measurement): per-decode HIP graph capture is ALREADY SUPPORTED (no port) and empirically net-positive on the MI210; the onegraph *single-graph fold* is a separate optimization that is NOT yet implemented.** The historical `experimental-v7-candidate` checkpoint used for K2 had a complete, vendor-agnostic graph capture infrastructure that maps 1:1 from CUDA to HIP; the current promotion line is the refreshed `experimental-v7-refresh-20260716` branch. **Important distinction:** this infra captures each `llama_decode` call independently (cache key = `cgraph->nodes[0]`), so the draft loop's N single-token decodes are captured/replayed *per step* (after a 2-call warmup). The onegraph technique — fold the warm-up + the whole N-step draft routine into ONE captured-once, single-launch graph — is a *speculative-aware* capture feature that this infra does NOT provide; K1 confirms the draft loop is structurally uniform (single sequence), so building it is feasible but is real work, not just a flag flip.

##### Existing Infrastructure

| Component | Location | Status |
|---|---|---|
| HIP graph API mappings | `ggml/src/ggml-cuda/vendors/hip.h:124-145` | Complete — 1:1 `#define` aliases, ~20 CUDA graph APIs mapped |
| USE_CUDA_GRAPH gate + graph struct | `ggml/src/ggml-cuda/common.cuh:1203-1238` | `#if defined(GGML_HIP_GRAPHS) → #define USE_CUDA_GRAPH` (1203-1205); `ggml_cuda_graph` struct (1207-1238) with `warmup_complete`, UID, node-property comparison, `is_enabled()` |
| Capture + replay flow | `ggml/src/ggml-cuda/ggml-cuda.cu:4468+` | `ggml_backend_cuda_graph_compute`: capture → instantiate → launch → `GraphExecUpdate` fast path |
| CMake enable | `ggml/CMakeLists.txt:216` + `ggml-hip/CMakeLists.txt:109-110` | `GGML_HIP_GRAPHS=ON` by default → `add_compile_definitions(GGML_HIP_GRAPHS)` |
| MI210 arch gate | `ggml-cuda.cu:4456` | gate is `cc < GGML_CUDA_CC_AMPERE(800)`; MI210 `cc = 0x1000000+0x90a = 0x100090a` (CDNA2) ≫ 800 ⇒ arch disabler **cannot** trip. **Verified live: graphs engage (+4.3% Q8 decode / +25% Q8 spec-dec).** |

##### Speculative Decoding Integration

Graph capture operates transparently at the backend level (`llama_decode` → `encode` → `graph_compute` → `ggml_backend_cuda_graph_compute`). No speculative-specific graph logic exists — the graph captures whatever `ggml_cgraph` is submitted. **This is the onegraph opportunity**: the `is_mem_shared` draft loop's uniform body means the same graph shape across iterations, maximizing cache hits.

##### Known Limitations / disabling conditions (independently audited + corrected 2026-07-11)

- **Split buffers** disable graphs entirely (multi-GPU layer splitting) — N/A on a single MI210.
- **`MUL_MAT_ID`** disables graphs **only** if experts are non-quantized **or** `ne[2] > mmvq_mmid_max`. `ne[2]` = n_tokens in the (u)batch (`ggml.c:3305`); `mmvq_mmid_max` = **8** for Q4_K/Q6_K/Q8_0 on CDNA2 (4–5 for IQ2\*/IQ3\*). ⇒ **single-token draft/decode (`ne[2]=1`) with quantized experts does NOT trip this** — the quantized gemma4 **MoE keeps graphs during decode** (confirmed empirically: +9.4% Q4 / +4.3% Q8). Only large target-verify batches (>8 tok, or >4–5 for IQ2/IQ3) or F16 experts disable it. *(The prior "MUL_MAT_ID disables graphs" wording was too broad — it does not apply to the decode path we care about.)*
- ~~Requires ROCm 5.7+~~ — **NOT code-backed** (audit): no ROCm/HIP version guard exists on graph enabling; graphs are gated solely by the build flag `GGML_HIP_GRAPHS` (default ON). Host runs ROCm 6.2.0 regardless.
- Two disablers the prior list omitted: `GGML_CUDA_DISABLE_GRAPHS` env (`common.cuh:1234` — this is the A/B toggle we used) and the `cc < AMPERE` arch gate (`ggml-cuda.cu:4456`, cannot trip on MI210 — favorable).
- **Warm-up transient (the key runtime caveat):** a graph needs **2 stable calls** to finish warm-up, and any shape/property change resets it (`ggml-cuda.cu:4488+`). The cache key is the `nodes[0]` pointer, but shape changes are detected by per-node `memcmp` and force a re-capture (no wrong-shape replay). So mixed-batch workloads pay repeated re-capture cost — which is exactly what the onegraph single-graph fold would eliminate.

##### Effort (validation-only, not port)

Smoke-test on MI210: ~1 day. Validate + benchmark with MTP: 2-3 days.

#### Onegraph Structural Verification (2026-07-11)

**Verdict: ALL THREE preconditions SATISFIED.** The gemma4 assistant drafter on the historical v7 checkpoint was structurally eligible for the onegraph optimization; future work must re-anchor on `experimental-v7-refresh-20260716` or its successor refreshed experimental branch.

> **Independent re-audit (2026-07-11):** all three preconditions were adversarially re-verified against source (6-agent audit); P1/P2/warm-up-equivalence CONFIRMED, P3 CONFIRMED-but-regime-scoped (see below). Minor citation drift to fix in reading the code: P1 projections are at `gemma4-assistant.cpp:62-63` (line 61 is `attn_norm`); P2's KV-view block spans `llama-kv-cache.cpp:190-206` (not `-198`). Substance unaffected.

##### P1: Q-only — SATISFIED

`src/models/gemma4-assistant.cpp:61-63`: only `wq` and `wo` tensors per layer (no `wk`/`wv`). Forward pass at `:143-154` calls `build_attn` with `nullptr` for K and V. `llama-graph.cpp:2596-2606` skips KV store when `k_cur`/`v_cur` are null — reads K/V from shared cache only.

##### P2: KV-shared — SATISFIED

`src/llama-model.cpp:2169-2197`: `GEMMA4_ASSISTANT` creates `llama_kv_cache_iswa` with `mem_other` = target model's memory and a `share` callback mapping assistant layers to target layers. `src/llama-kv-cache.cpp:190-198`: when `share` is set and `other` is non-null, K/V tensors are direct views into the source cache. `speculative.cpp:1370`: `is_mem_shared = llama_get_ctx_other(ctx_dft) == ctx_tgt` evaluates true.

##### P3: No cross-position dependencies — SATISFIED (scoped to the `is_mem_shared`/gemma4 branch)

`speculative.cpp:1663-1667`: every draft token decodes at the **same position** `dp.n_past`. No `seq_rm`, no KV rebuild, no batch prefix — just a single-token decode at the fixed position with the h-row carryover. Each step consumes `(token, h_row)` and produces `(token, h_row)` where `h_row` comes from `llama_get_embeddings_nextn_ith`.

> **Scope correction (audit 2026-07-11):** this property holds **only** for the `is_mem_shared` (gemma4 assistant) branch — which *is* the drafter we use. The same `draft()` function has two other branches that are NOT position-static: the growing-KV `else` branch (`:1669`) advances `dp.n_past + i + 1` per iteration, and the `chain_heads` branch (qwen35 multi-MTP-head) does `seq_rm` (`:1593`) + a full-prefix batch rebuild every iteration. So "no cross-position deps in the draft loop" is a **regime-specific** statement, not a universal one — correct for gemma4, false for the qwen MTP regimes. (Also note: even the gemma4 branch has non-*position* cross-iteration state — sampler-accept state, `i_last`, and repeated overwrite of the same shared KV cell — which is fine for onegraph but means "each step is fully independent" is an over-simplification.)

##### Warm-up vs Draft Loop Equivalence

- **Warm-up (`process()`, `:1430-1546`)**: for `is_mem_shared`, the catch-up decode block (`:1465`) is **entirely skipped** — only copies hidden states from the target (`:1527-1543`). **Zero drafter compute.**
- **Draft loop (`draft()`, `:1548-1697`)**: uniform single-token decode at `dp.n_past` per iteration (`:1663-1667`). Batch is cleared and rebuilt each iteration. **No structural difference between first and subsequent iterations** — every step runs the identical graph with only data values changing.

**Implication for GPU-graph capture**: the draft loop's uniform body is exactly what the onegraph optimization requires. A HIP graph captured for one iteration is replayable for all iterations — the only state that changes is the input token + h-row, which are external to the graph (batch embeddings). The CPU path is already optimal (minimal decode at fixed position, no warm-up overhead).

#### v7 Kernel-Optimization Performance Tables (consolidated, 2026-07-11)

**All observation-grade** (MI210 gfx90a, ROCm 6.2, `build-hip`; temp0/seed42, decode t/s; %Δ vs graphs-OFF baseline). Levers: OFF=`GGML_CUDA_DISABLE_GRAPHS=1` · ON=default · OPT=`GGML_CUDA_GRAPH_OPT=1` · KEY=`GGML_CUDA_GRAPH_SHAPE_KEY=1` (Lever A, env-gated experimental edit).

**Base decode** (llama-bench, -p128 -n256 -r3):

| model | quant | OFF | ON (default) | OPT=1 | KEY=1 (Lever A) |
|---|---|---|---|---|---|
| A4B MoE | Q8 | 79.05 | **82.45 (+4.3%)** | 68.81 (−16%) | n/t (Lever A targets spec-dec) |
| A4B MoE | Q4 | 80.8 | 88.3 (+9.4%) | — | — |
| dense-31B (gemma) | Q8 | 23.42 | 24.84 (+6.1%) | — | — |
| **Qwen3.6-27B** (dense hybrid SSM, native MTP) | Q8 | 28.24 | 30.27 (**+7.2%**) | — | — |
| **Qwen3.6-35B-A3B** (MoE, native MTP) | Q8 | 85.20 | 97.08 (**+13.9%**) | — | — |

**MTP spec-dec** (llama-server, chat temp0, 3 reps):

| model | quant | OFF | ON (default) | OPT=1 | KEY=1 (Lever A) |
|---|---|---|---|---|---|
| A4B MoE | **Q8** | ~86.5 | **~108 (+25%)** | ~96 (−11%) | 107.2 (−2%, output-identical†) |
| A4B MoE | Q4 | ~112 | ~104 (**−5%**) | ~115 | ~116 (+6%†, noisy) |
| dense-31B (gemma) | Q8 | ~35.2 | ~36.4 (+3.4%) | — | — |
| **Qwen3.6-27B** (dense, **native** MTP) | Q8 | 47.0 | 47.9 (**+1.8%**) | — | — |
| **Qwen3.6-35B-A3B** (MoE, **native** MTP) | Q8 | 103.4 | 105.9 (**+2.5%**) | — | — |

Takeaways: graphs (default ON) are the win on Q8 — biggest on the fast A4B MoE spec-dec (+25%, = production worker regime); GRAPH_OPT is net-negative (rejected); the A4B Q4 spec-dec −5% is the verify-side re-capture thrash that Lever A targets (see "Kernel-Optimization Levers").

**†** Lever A (KEY=1) clean re-eval (quiet card, strictly sequential, fresh-server/run): Q8 = −2% with **byte-identical output** (correctness-safe, no speedup); Q4 = +6% but noisy (2 output variants). **Neutral → not landed**; source reverted, preserved as a patch. See the Lever A result below.

**Non-gemma4 generalization (2026-07-11):** graphs-ON benefits **non-gemma4 models too**, but the magnitude splits by *what* is being accelerated:
- **Base decode: helps every model tested** — +7.2% (Qwen3.6-27B dense hybrid), +13.9% (Qwen3.6-35B-A3B MoE), alongside gemma's +4–9%. Generalizes cleanly; magnitude scales with launch-overhead-fraction (fast/MoE > slow/dense).
- **Spec-dec: the big win is drafter-architecture-specific.** gemma4's **external assistant-head** drafter gets **+25%** (a separate tiny-model decode per draft step → launch overhead dominates → graphs amortize hugely). Qwen's **native NEXTN-MTP** head gets only **+1.8–2.5%** (draft folded into the main forward → little separable launch overhead to amortize). So "graphs give +25% on spec-dec" is a **gemma4-external-head property, not a universal MTP one**.
- **Determinism:** the Qwen **native-MTP** path is fully deterministic (ON==OFF byte-identical, even at load 164); the **load-sensitive non-determinism is specific to gemma4's external-head + shared-KV path**. Useful diagnostic narrowing of the race.

#### K2 Empirical Results — MI210 HIP graph A/B (2026-07-11)

**Setup**: existing `llama.cpp-experimental/build-hip` (HEAD `46f876c12`, `GGML_HIP_GRAPHS=ON`, Release) — **no rebuild needed**. MI210 gfx90a (`cc 0x100090a`), ROCm 6.2.0, sole ROCm device, otherwise idle. Toggle: default (graphs ON) vs `GGML_CUDA_DISABLE_GRAPHS=1` (direct dispatch). Base decode via `llama-bench -ngl 99 -dev ROCm0 -fa on -p128 -n256 -r3`; MTP spec-dec via `llama-server` (`--spec-type draft-mtp --spec-draft-n-max 2`, target+assistant-v6 head both `-ngl 99` on ROCm0) driven by chat-templated `/v1/chat/completions`, temp0/seed42 (deterministic → **both arms emit byte-identical, coherent output** — graphs are numerically transparent), 3 reps. **All numbers are OBSERVATION-grade** (single-config, small-n, MEASUREMENT.md) — they characterize the graph subsystem; they do NOT gate a promote decision (that is a later v6→v7 session).

| model | quant | workload | graphs ON | graphs OFF | Δ from graphs | reliability |
|---|---|---|---|---|---|---|
| gemma-4-26B-A4B (MoE) | Q8_0 | base decode | 82.45 t/s | 79.05 t/s | **+4.3%** | tight (±<1) |
| gemma-4-26B-A4B (MoE) | **Q8_0** | **MTP spec-dec** | **~108 t/s** | **~86.5 t/s** | **+25%** | tight, reliable |
| gemma-4-26B-A4B (MoE) | Q4_K_M | base decode | 88.3 t/s | 80.8 t/s | +9.4% | tight |
| gemma-4-26B-A4B (MoE) | Q4_K_M | MTP spec-dec | ~104 t/s | ~112 t/s | **−5%** (graphs *hurt*) | noisier (±~7%), direction reproduced n=1 + n=3 |
| gemma-4-31B (DENSE) | Q8_0 | base decode | 24.84 t/s | 23.42 t/s | +6.1% | tight |
| gemma-4-31B (DENSE) | Q8_0 | MTP spec-dec | ~36.4 t/s | ~35.2 t/s | +3.4% | near noise floor |

**Findings**
1. **HIP graph capture works and engages on the MI210** (gfx90a) — the non-zero, output-transparent A/B delta proves it (if graphs were silently gated out, ON==OFF). gemma-4-26B-A4B MoE **and** gemma-4-31B dense both run correctly on the HIP path (coherent output; MTP ~83–88% draft accept), so gemma4 on HIP is validated, not just Qwen native-MTP.
2. **Q8 (the MI210 focus quant) is net-positive everywhere**, and the win is **largest on the fast A4B MoE spec-dec path (+25%)** — exactly our production `worker_general` regime. Interpretation: graph benefit ≈ launch-overhead ÷ per-token time. The A4B MoE decodes fast (~3.8B active params → short kernels) so fixed launch overhead is a large fraction → big win; spec-dec adds many small draft/verify kernels → amplifies it.
3. **Dense models benefit too, but far less** (31B: +6.1% decode / +3.4% spec-dec). The 31B reads all 31B params/token → BW-bound, long kernels → launch overhead is a tiny fraction → small graph win. So the graph/onegraph lever matters *most* for the fast MoE worker and *least* for heavy dense models.
4. **The benefit is NOT universal — it is workload×quant dependent.** A4B **Q4** spec-dec is a small **regression** (graphs ~−5%), while A4B **Q8** spec-dec is +25%. The most likely mechanism: the pointer-keyed, non-shape-aware cache re-captures on every draft↔verify batch-shape switch (warm-up-transient reset); when per-kernel compute is cheap (Q4), that re-capture cost outweighs the launch savings. This is precisely the thrash the onegraph single-graph fold removes — and the concrete evidence that "just enable graphs on the spec-dec path" is the wrong move.

**Bottom line for the handoff's earlier verdict**: "HIP graph capture ALREADY SUPPORTED, no port" is confirmed for *per-decode* capture and is a real, free win on the MI210 Q8 MoE spec-dec path (+25%). The Q4 spec-dec regression and the remaining lever are analyzed in "Kernel-Optimization Levers" below — the on-target fix is a **shape-aware cache key** (Lever A), NOT the onegraph fold (Lever B), which a deeper analysis showed targets the already-optimal draft loop rather than the verify-side thrash.

**Harness lesson (recorded so it isn't rediscovered)**: an early spec-dec run produced garbage output and misleading t/s — root cause was the **test harness**, not the code: raw `/completion` prompts (no chat template) on a gemma4 *reasoning/instruct* model + a warm-up request polluting the slot. Correct method: chat-templated `/v1/chat/completions`, no warm-up, fresh slot. Speed was paired with a correctness check throughout ([[feedback_verify_test_method_before_calling_it_a_bug]], [[feedback_pair_speed_with_correctness_check]]).

**Next graph levers (not yet tested)**: (a) `GGML_CUDA_GRAPH_OPT=1` — the fork's extra fan-out/stream-reorder pass (off by default, `ggml-cuda.cu:4564`); (b) the onegraph single-graph capture feature itself; (c) whether the Q4 spec-dec regression closes under either.

#### Kernel-Optimization Levers (K6/K7 investigation, 2026-07-11)

Three levers were scoped to improve on the raw K2 per-decode graph capture. Key reframing from the K7 code audit: **the A4B Q4 spec-dec regression is VERIFY-side, not the draft loop.** For single-seq gemma4/`is_mem_shared`, every *draft* decode is `n_tokens=1` at a fixed position → shape-stable → the per-decode graph already warms up and replays across draft steps (draft loop is already graph-optimal). The thrash is the *target verify* decode: `n_tokens = n_drafted+1` varies with acceptance each spec-dec step → the single shared cache slot's `warmup_complete` keeps resetting (`ggml-cuda.cu:4499-4502`) → verify runs eager. This reframes lever EV.

##### Lever: `GGML_CUDA_Q8_PREFETCH` (fork CDNA2 dense-Q8_0-GEMV async weight-prefetch, `mmvq.cu:502`) — REJECTED (2026-07-11)
Compiled-in (`Q8_LDS_PREFETCH_COMPILED`), lossless/byte-identical, runtime `0`=off (default) / `1`=cached-DMA / `2`=SLC-streaming. Benchmarked 0/1/2 on all 4 Q8 models (MI210, llama-bench base decode, r5, graphs-ON): **net-negative — leave OFF.** Ironically it *hurts the dense models most* despite targeting dense GEMV: Qwen3.6-27B dense −12%/−18%, gemma4-31B dense −6%/−7.5%; MoE marginal/noisy (gemma4-A4B −3.5%/−0.3%, Qwen3.6-35B-A3B +4.2%/+3.1% — the two MoE disagree in sign → near noise). No consistent win; the experimental prefetch/LDS-double-buffer overhead outweighs the DMA-latency hiding on gfx90a for these shapes.

##### Lever: `GGML_CUDA_GRAPH_OPT=1` (fork fan-out/stream-reorder pass) — REJECTED
Env-only, `ggml-cuda.cu:4564`. Measured net-negative on MI210: A4B **Q8 base decode −16%** (68.8 vs 82.5 t/s), **Q8 spec-dec ~−11%** (~96 vs 108); Q4 spec-dec noisy/neutral (~115 vs 104 on / 112 off). Leave OFF (the default).

##### Lever A: shape-aware graph cache key — IMPLEMENTED (env-gated), NEUTRAL on Q8 (clean re-eval) → not landed, patch preserved
The graph cache is a multi-entry map (`common.cuh:1404`) but keyed by `cgraph->nodes[0]` **pointer only** (`ggml-cuda.cu:3297`, shape-blind — the key exists to separate CPU/GPU split sub-graphs, not batch shapes). Draft (1-tok) and each verify (n_drafted+1) forward share the same reused `nodes[0]` buffer → collide on ONE slot → per-switch warmup reset = the −5% regression. **Fix (implemented as env-gated `GGML_CUDA_GRAPH_SHAPE_KEY=1`, default off = upstream behavior):** mix an FNV-1a shape signature (per-node `op`+`ne[]`, EXCLUDING data ptrs/nb) into the key so draft and each distinct verify batch-size get their own persistent, warm slot. `update_required()` still validates node_props + refreshes pointers every launch, so **correctness is unchanged — the key only selects the slot**. Change is one function (`ggml_cuda_graph_get_key`) + an env-gated `[SHAPE_KEY]` keylog diagnostic.

**Result (2026-07-11): NEUTRAL — NOT landed.** Built the env-gated change (compiles clean) and benchmarked twice. A first pass under host load ~95–102 (3 req/server) was confounded by load + a non-deterministic baseline → discarded. **Clean re-eval (operator-directed: quiet card, strictly sequential, fresh server per run, single request):** most configs became deterministic (3/3 reps byte-identical). **Q8 spec-dec: KEY=1 = 107.2 vs default 109.5 t/s (−2%), output byte-IDENTICAL to default** → the shape-key is **correctness-safe (numerically transparent) but gives no speedup** (slight regression, within noise). **Q4 spec-dec: KEY=1 = 115.8 vs 109.2 (+6%)** but Q4 stayed noisy (2 output variants) → not conclusive. Net: the verify-side thrash hypothesis does **not** produce a clear measurable Lever-A win; on the Q8 focus quant it's neutral-to-slightly-negative. The `[SHAPE_KEY]` keylog never fired (backend `GGML_LOG_INFO` filtered during decode) so the `nodes[0]` collision is **unconfirmed** — but KEY=1's identical output proves the change is at least safe. **Action: source reverted (v7-candidate pristine); preserved as `/mnt/raid0/llm/llama.cpp-experimental/lever-a-shape-key.patch`. Not worth landing on current evidence**; only revisit if a future profile shows verify re-capture is a *measured* bottleneck (fix the keylog to `fprintf(stderr,…)` first to confirm the collision).

##### Draft-depth sweep + spec-dec non-determinism (2026-07-11, CORRECTED with clean data)

Swept `--spec-draft-n-max ∈ {2,4,6}` on A4B Q8 spec-dec to size onegraph EV. A first pass (loaded host, 3-req/server) suggested deeper=faster (n2→n4→n6 = 93→112→116 t/s) — but the **clean sequential re-eval REFUTED it as a load/non-determinism artifact:**

| n_max | decode t/s (loaded, discarded) | decode t/s (clean, median) |
|---|---|---|
| 2 | ~93 | **108.4** |
| 4 | ~112 | **104.1** (slightly slower) |

**Deeper drafts do NOT help on this workload** (the per-position accept-rate drop cancels the longer accept-length; n_max=2 is already near the ceiling). **RETRACTED: the earlier "raise n_max 2→4 for +20%" recommendation — it does not reproduce.** Still supports deferring onegraph — no draft-depth throughput headroom to capture, and the draft loop is already near its ceiling here.

**Spec-dec non-determinism (refined):** the gemma4 MTP HIP spec-dec path is **intermittently** non-deterministic at temp0/seed42 — it drifts every run under concurrent host load, but **mostly resolves when run strictly sequentially on a quiet card** (3/3 identical for Q8 in the clean re-eval; occasional single-flip for Q4). Consistent with a **load-sensitive race** in the async D2H-copy / backend-sampling path — NOT the Lever-A edit (inert when its env is unset), and NOT same-server slot carryover (fresh servers also flipped under load). Implication: every spec-dec A/B must run on a quiesced host, strictly sequential, fresh-server-per-run; the residual race is a low-grade correctness/repro flag worth a dedicated look ([[feedback_pair_speed_with_correctness_check]]).

##### Lever B: onegraph — fuse the whole N-step draft routine into ONE replayable graph — DEFERRED (very-high effort, high risk, lower-EV than first framed)
**Why deferred (not just hard — lower value):** onegraph fuses the *draft* decodes, which are already shape-stable and replay via per-decode capture; it does **not** touch the verify-side variability that actually caused the K2 thrash. So Lever A is the on-target fix; onegraph's marginal EV is the N draft-step launch/sync overhead only.

**Why hard — the draft loop is host-in-the-loop** (`common/speculative.cpp:1582-1681`). Each iteration: `llama_decode` → `common_sampler_sample` opens with `llama_synchronize` (a hard full GPU→host block every iteration, `sampling.cpp:541`) → host reads sampled token (`get_sampled_token_ith`, `llama-context.cpp:961`) → host `p_min` early-exit + `n_max` break (data-dependent control flow, `speculative.cpp:1632/1646`) → host reads h_row (`get_embeddings_nextn_ith`) → host rebuilds batch + `memcpy` of h_row into `batch.embd` (`speculative.cpp:1666-1667`) → next `llama_decode` re-uploads H2D. `backend_sampling=1` removes the CPU softmax/argmax but NOT the host round-trip or the host control-flow.

**What a real implementation requires** (a speculative+backend co-design, NOT a local edit): (a) keep the sampled token on-device, wired directly into the next sub-step's input tensor (no D2H / `get_sampled_token_ith`); (b) keep h_row on-device, fed GPU→GPU into the next embd input (no `embd_nextn` D2H / CPU memcpy); (c) drop the data-dependent `p_min`/`n_max` early-exit → **fixed-N unroll**, pruning the over-drafted tail on host AFTER the single graph (**ROCm 6.2 on MI210 lacks CUDA-style conditional graph nodes, so variable-length drafting cannot live in-graph — fixed-N is forced**); (d) identical batch shape across all N sub-steps. Change sites: `speculative.cpp:1582-1681`, `llama-context.cpp:1316-1533/1580-1660` (new on-device output→input feedback path), `sampling.cpp:540-541/130-162` (bypass the per-iteration sync barrier), `ggml-cuda.cu:3297-3341/4468-4522` (capture the one large N-step cgraph).

**Correctness risks that make it high-risk:** (1) on-device token/h_row feedback bypasses the `get_sampled_token_ith`/`get_embeddings_nextn_ith` host contracts — and tensor *content* is NOT part of graph `node_props` (`ggml-cuda.cu:3322-3338`), so a wrong-but-same-shape buffer silently feeds stale state and is NOT caught by re-capture. (2) fixed-N changes draft-length semantics (always draft N then prune) — must exactly reproduce the old `p_min` draft set or the acceptance/output distribution shifts. (3) `chain_heads` MTP path (>1 mtp layer) grows the batch each iteration → inherently variable-shape → not an onegraph candidate; only the single-mtp-layer gemma4 `is_mem_shared` path qualifies. **Revisit only if Lever A does not close the thrash AND draft-launch overhead is then measurably the residual bottleneck.**

#### V7 Quality Gate (K5, 2026-07-14)

**Motivation**: the Gemma Challenge's PPL-only quality gate was gamed — a lossy submission held PPL at ≤2.42 while losing **15 GPQA-Diamond / 40 MMLU-Pro points** relative to base. Any v7+ kernel candidate must pass multi-suite downstream evals before promotion, not PPL alone.

##### Scripts

| Script | Path | Purpose |
|---|---|---|
| `v7_quality_gate_runner.py` | `epyc-inference-research/scripts/benchmark/` | Evaluates MMLU-Pro + GPQA-Diamond on a running llama-server, outputs per-suite accuracy JSON |
| `v7_quality_gate_compare.py` | `epyc-inference-research/scripts/benchmark/` | Compares candidate vs baseline JSON, applies regression threshold, outputs PASS/FAIL report |

##### Usage

```bash
# 1. Measure v6 baseline (run once, reuse)
v7_quality_gate_runner.py --port 18072 --output v6_baseline.json \
    --suites mmlu_pro gpqa --n 200 --seed 42 --kernel v6-production

# 2. Measure v7 candidate
v7_quality_gate_runner.py --port 18073 --output v7_candidate.json \
    --suites mmlu_pro gpqa --n 200 --seed 42 --kernel v7-experimental

# 3. Compare (exit 0 = PASS, 1 = FAIL)
v7_quality_gate_compare.py --baseline v6_baseline.json \
    --candidate v7_candidate.json --output report.md \
    --regression-threshold 0.05
```

##### Gate Criteria (default)

- **Per-suite**: candidate accuracy ≥ baseline accuracy - regression_threshold
- **Default threshold**: -5 percentage points (0.05)
- **Both suites must pass** (mmlu_pro AND gpqa)
- **Minimum sample**: 50 questions per suite (advisory warning below this)

##### ⚠ Blocking: Operator Decisions Required

1. **v6 baseline measurement**: run `v7_quality_gate_runner.py` on the production v6 kernel with the models used in production. Store the output as the canonical baseline (e.g., `data/baselines/v6_quality_gate.json`).
2. **Threshold confirmation**: confirm or adjust the -5pp regression threshold. The challenge's gamed submission lost 15/40 points — -5pp catches moderate regression while allowing kernel noise. Tighter threshold (e.g., -3pp) is available but risks false positives on small samples.
3. **Sample size**: 200 questions per suite (seed 42) is the default. The eval tower's promotion mode uses N=200-500. Increase if statistical confidence is a concern.

##### MMLU-Pro Adapter

- **Dataset**: `TIGER-Lab/MMLU-Pro` (test split, 12,032 questions)
- **Format**: 10-choice multiple-choice (A-J), harder than standard MMLU (4-choice)
- **Categories**: math, physics, chemistry, computer science, engineering, biology, health, economics, psychology, philosophy, history, law, business, other
- **Tiers**: T3 (STEM/professional), T2 (social sciences/humanities), T1 (business/other)
- **Registration**: `mmlu_pro` in `ADAPTER_SUITES` (research + orchestrator repos)

#### Notes

- The challenge ran on A10G/GPU with E4B (small Gemma); our production worker is **CPU MTP on a 26B-A4B** with the MI210 as the GPU path — so GPU-graph techniques land on the MI210 drafter track, while the drafter-α and warm-up-redundancy *insights* are the CPU-transferable ones.
- All intake-798 numbers (315 / 491.8 TPS, ±15/40 eval deltas, PPL ≤ 2.42) are OBSERVATION-grade (challenge-internal, single-config, self-reported) — hypotheses only, re-measure on our stack before any keep/promote per MEASUREMENT.md.
- Submission-level detail (per-result `method` fields, taskforce notes) is available on the challenge leaderboard/bucket for a deeper follow-up if a technique graduates past the structural check.

#### Research Intake Update — 2026-07-16 (Bonsai-27B / upstream Q2_0 gap)

From the 2026-07-16 research-intake deep-dive (intake-820/821/822, PrismML Bonsai-27B; details in [`tq3-quantization-evaluation.md`](quantization-and-low-bit.md#track-tq3-quantization-evaluation) + `research/intake_index.yaml`):

**Historical finding — the old v7-candidate was MISSING upstream `Q2_0`; superseded 2026-07-18.** llama.cpp added two sub-2-bit weight types, both authored by PrismML (`khosravipasha`) to run Bonsai: **`Q1_0`** (1-bit, PR #21273, merged **2026-04-06**) and **`Q2_0`** (ternary group-64, PR #24448 CPU merged **2026-07-07**, #25419 Metal; CUDA #25707 open). Verified enum state on 2026-07-16: both `production-consolidated-v6` and the old **`experimental-v7-candidate`** had `GGML_TYPE_Q1_0` (=41) but **NOT `GGML_TYPE_Q2_0`**. Q2_0 merged **11 days after** the v6 cutover (2026-06-26), so the stale candidate never inherited it. Same *stale-fork* class the governance rails warn about (the 2026-06-22 iqk near-miss). The refreshed promotion line `experimental-v7-refresh-20260716` restores `GGML_TYPE_Q2_0` (=42); current checked local/fork tip is `ed4091266`, so this is provenance for why the refresh was required, not an open promotion blocker.

**Recommendation — do NOT hot-cherry-pick Q2_0.**
- Do NOT patch Q2_0 into frozen v6, and do NOT hot-cherry-pick it into v7-candidate — that violates the "full build, validated together, not reconciled at promotion" rule.
- Correct path: the **v7 experimental refresh must fresh-pull from a post-2026-07-07 upstream+production tip**, which brings Q2_0 (and any other post-cutover upstream work) in *automatically*, validated alongside iqk/CPU forward-ports. This is now complete on `experimental-v7-refresh-20260716`; keep "v7-candidate lacks Q2_0" as a **freshness-audit hit** pattern to check before any future promotion.
- Do NOT refresh *solely* for Q2_0: its only near-term use is Ternary-Bonsai-27B, and there is no ROCm/HIP Q2_0 path (CUDA PR still open) so on our MI210 it would be CPU-only anyway. Gate it on the Bonsai Q1_0 smoke-test (below).

**De-risked opportunity — Bonsai-27B `Q1_0` smoke-test.** Bonsai = quantized **Qwen3.6-27B**, whose hybrid Gated-DeltaNet arch is **already supported + exercised on this branch** (K9 ran Qwen3.6-27B native-MTP; `src/models/delta-net-base.cpp` present) and `Q1_0` is already in the tree — so a **`Bonsai-27B-Q1_0.gguf`** (~3.8 GB, staged 2026-07-16 at `models/bonsai-27b/`) is a cheap load/decode test on stock kernels. Open questions: (i) does PrismML's Q1_0 packing load without their custom fused hybrid-attention kernels, and (ii) quality (self-reported 76.1 avg, **independently contested** — HF gibberish/hallucination/load-failure reports; no third-party reproduction). Footprint/density experiment, hard-gated on the K5 MMLU-Pro/GPQA quality gate — NOT a quality win.

#### V7 Refresh Checkpoint — 2026-07-16

- `experimental-v7-refresh-20260716` committed at `8e5c555ab` (`Refresh v7 candidate onto upstream master`).
- The refresh merged `origin/master` at `a8dc0e326` and restored upstream freshness, including `Q2_0` support.
- Previous K14 fix remains at `99f3fffd6` (`fix hip flash-attn backend-op coverage`).
- Build validation passed: `cmake --build build-hip --target ggml-hip`; `cmake --build build-hip --target llama-server llama-bench`.
- Focused validation passed: `LD_LIBRARY_PATH=build-hip/bin build-hip/bin/test-backend-ops -o EXPM1 -b ROCm0 -p type=f32` => `2/2`.
- Full validation passed: `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin ctest --test-dir build-hip/tests -R '^test-backend-ops$' --output-on-failure` => `Passed 734.97 sec, 100% tests passed`.
- Important fix details: kept all speculative enum cases (`ngram` + `DFLASH` + `draft-tree`), restored content-scoped slot media guard for Expected Attention compaction, added Q8 prefetch fusion predicate after the upstream refactor, and patched ROCm `EXPM1` positive overflow to return `+inf`.
- AutoPilot remains intentionally stopped; production kernel was not modified or promoted.


#### Research Intake Update — 2026-07-16 (Architect→Reviewer control plane: kernel work queue K22-K31)

Source: control-plane planning session (audit doc `research/deep-dives/2026-07-16-architect-reviewer-control-plane-audit.md`; index `reviewer-control-plane-index.md`). Read-only v7 source review found two correctness blockers for the typed-decision reviewer plus quality-neutral throughput levers. All work on `llama.cpp-experimental` only (production FROZEN); CPU bench via canonical recipes, GPU bench via `kernel_eval.sh`; GPU access queues behind the admission-smoke lane; spec-dec A/Bs quiesced+sequential+fresh-server per the K7 caveat.

- [x] **K27.2 — generic Q8_0 8x8 opt-in retired; optimized path deferred ✅ 2026-07-17**: official upstream `ggml-org/llama.cpp` `origin/master` at `635cdd5f` no longer carries the selectable Q8_0 8x8 repack/gemv/gemm route, and K27.1 measured the local generic scalar path as a regression when explicitly enabled. Experimental-v7 commit `aa7a2665f` removes only that failed opt-in path (`GGML_REPACK_Q8_0_8X8`, `q8_0_8x8` traits/specializations/functions) while leaving default Q8_0 dispatch and the separate proven EPYC/iqk work intact. Validation: no remaining `q8_0_8x8`/`GGML_REPACK_Q8_0_8X8` references in `repack.cpp`/`repack.h`; `cmake --build build-k24-cpu --target llama-bench llama-server -j16`; Qwen3-4B Q8 smoke with experimental `LD_LIBRARY_PATH` pinned showed default `220.61` prompt / `8.47` decode t/s and legacy-env-set `219.11` / `8.40`, with no `CPU_REPACK` or `q8_0_8x8` logs (`/mnt/raid0/llm/tmp/k27-retire-q8-8x8-20260717T101836Z/`). Future K27 work should not resurrect this generic path; only a separately optimized x86 kernel gets a new task.
- **[declined: operator 2026-11-09 (INF-48 triage, dropped, not done): conditional on a slot-save teleport that is not being pursued]** **K30 (P2, conditional) — composed-spec state save/restore** — closed as dropped, not completed; original text: `git show b3bd883d3:handoffs/active/rocm-kernel-authoring.md` line 3851. [no-belief: dropped by operator 2026-11-09]
  - [x] K31.1 GLM/DSA prompt-path static audit ✅ 2026-07-17: pre-fix source loaded GLM DSA metadata/tensors but only constructed `llama_kv_cache_dsa` for `LLM_ARCH_DEEPSEEK32`; experimental-v7 `3dee86a5a` wires `LLM_ARCH_GLM_DSA` into that cache/runtime path. In the generic DSA path, indexer/top-k is constructed for prompt batches and decode, but final attention remains full-KV masked MLA (`ggml_set_rows` into a full KQ mask, then `build_attn_mha`). Current implementation should be treated as GLM-cache-runtime-wired plus generic DSA-DENSE-MASK-LIKELY.
  - **[declined: ws58 2026-11-03 content-review: merged into K31 as its open half]** K31.2 Expected-Attention server-safe reclaim remains open; do not conflate it with the GLM/DSA audit closure.
    - [x] K31.2a server response semantics guard ✅ 2026-07-18: experimental-v7 commit `8905c3d2c` now leaves server-side Expected Attention in explicit gapped-eviction mode (`compact_positions=false`) and returns `compact_positions`, `logical_context_reclaimed=false`, and `reclaim_mode=evict_only_gapped` in `/slots/{id}?action=compact` results. Direct source audit confirmed `compact_positions=true` would desync `server_slot.prompt.tokens`, checkpoints, and prompt-cache position accounting unless the server also compacts its logical token state. Validation: `git diff --check`; `cmake --build build-hip --target test-backend-ops test-llama-archs llama-server -j48`. This is an API/automation guard, not a full reclaim implementation; K31.2 remains open for a real logical-position compaction design.
    - [x] K31.2b server-safe logical-reclaim design audit ✅ 2026-07-18: read-only audit confirmed `compact_positions=true` is unsafe because it shifts KV cells without updating `server_slot.prompt.tokens`, prompt-cache checkpoints, speculative rollback state, or multimodal/M-RoPE token-position accounting. A bounded first implementation is possible only behind hard gates: idle slots, text-only, non-speculative/no draft context, shared old-to-new compaction plan applied to server logical tokens and KV, plus conservative checkpoint/RAM-cache invalidation. Risk remains HIGH for general server reclaim and MEDIUM for that gated first pass; keep default `/slots?action=compact` in evict-only mode until implemented and tested.
    - [x] K31.2c evict-only parameter helper + server unit smoke ✅ 2026-07-18: experimental-v7 commit `41ae83402` centralizes server Expected-Attention params in `make_server_expected_attention_params()`, asserts `compact_positions=false`, and adds `test_slot_compact_stays_eviction_only` for `/slots/{id}?action=compact`. Validation: `cmake --build build-hip --target llama-server --clean-first -j16`; direct live compact smoke passed; `LLAMA_SERVER_BIN_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin/llama-server uv run --with pytest --with requests --with wget pytest -q tools/server/tests/unit/test_slot_save.py::test_slot_compact_stays_eviction_only` passed. This still deliberately does not implement logical-position reclaim.


#### Non-inference K11 summary-source correction — 2026-10-07



### Done

- [x] **K1** ✅ 2026-07-11 — all 3 satisfied
- [x] **K2** ✅ 2026-07-11 **: verified on the existing `build-hip` (`46f876c12`, `GGML_HIP_GRAPHS=ON`, ROCm 6.2 — **no rebuild needed**). HIP graph capture engages on MI210 gfx90a; gemma
- [x] **K3** ✅ 2026-07-11 (answered by the K1 audit — no action available)**: the onegraph insight is "the multi-position drafter warm-up is redundant." Our audit (Warm-up vs Draft Loop
- [x] **K4** ✅ 2026-07-16 **: measured current acceptance α on the real task corpus before any fine-tuned-drafter investment; acceleration index records `summary.json` as decision-grade.
- [x] **K5** ✅ 2026-07-16 **: implemented `MMLUProAdapter` (TIGER-Lab/MMLU-Pro, 12K questions, 10-choice A-J) + `v7_quality_gate_runner.py` (eval runner) + `v7_quality_gate_compare.py` (
- [x] **K6** ✅ 2026-07-11 **: benchmarked on MI210 → **REJECTED** (net-negative: Q8 base −16%, spec −11%). Leave off (default).
- [x] **K9** ✅ 2026-07-11 **: Qwen3.6-27B (dense hybrid) + Qwen3.6-35B-A3B (MoE), native MTP. Base decode **+7–14%** (generalizes); native-MTP spec-dec only **+1.8–2.5%** (the +25% is ge
- [x] **K11** ✅ 2026-07-17 ; broad free-form gate reopened 2026-07-18**: the old short JSON closure remains valid but too narrow. **2026-07-16 preliminary evidence:** the new research run
- [x] **K11.1g** ✅ 2026-07-19 **: corrected `1024`-token run `data/k11_gemma4_determinism/k11_schema_word_array_ud_iq4xs_mtp_np4_n10_currentv7_20260719Tmain_1024/summary.json` passed `10/10`
- [x] **K11.1h** ✅ 2026-07-19 **: `data/gpu-mi210/gemma4_ud_iq4xs_mtp_freeform_termination_20260719T035436Z/summary.json` ran three fresh-server no-stop 200-word `benchmark` completions with
- [x] **K11.1i** ✅ 2026-07-20 **: post-candidate experimental build `12a292f0c21d` reran the actual no-schema exact-count free-form shape at `data/k11_gemma4_determinism/k11_freeform_ud_iq4x
- [x] **K11.1j** ✅ 2026-07-20 **: concurrent-with-PC-4o MI210 stop-string runs used `stop=["END"]`, four slots, assistant-head MTP, and the same exact 200-word prompt. UD-IQ4_XS artifact `da
- [x] **K11.1k** ✅ 2026-07-20 **: isolated MI210 fresh-server natural-prose prompt used `stop=["END"]`, four slots, assistant-head MTP, and no concurrent CPU/GPU bench. Aggregate summary: `d
- [x] **K11.1l** ✅ 2026-07-20 **: isolated MI210 fresh-server repeat added request-level explicit-greedy plus `--no-spec-draft-backend-sampling` to the same natural 160-word prompt. Comparis
- [x] **K11.1m** ✅ 2026-07-20 **: inference-research `scripts/benchmark/k11_gemma4_determinism_runner.py` now exposes opt-in `--trace-token-divergence`, `--trace-n-probs`, `--trace-post-samp
- [x] **K11.1n** ✅ 2026-07-20 **: trace triad artifact `data/k11_gemma4_determinism/k11_natural_freeform_trace_compare_20260720T1139Z/summary.json` reran the ORIG-Q4 natural 160-word prompt
- [x] **K11.1o** ✅ 2026-07-20 **: CPU-only ORIG-Q4 control artifact `data/k11_gemma4_determinism/k11_natural_freeform_orig_q4_cpu_nospec_np1_explicit_greedy_trace_20260720T114120Z/summary.js
- [x] **K11.1p** ✅ 2026-07-20 **: compare artifact `data/k11_gemma4_determinism/k11_gpu_backend_path_ab_20260720T1204Z/summary.json` used pre-sampling `top_logprobs` on the same ORIG-Q4 no-s
- [x] **K11.1q** ✅ 2026-07-20 **: experimental-v7 post-candidate source now exposes `GGML_CUDA_DISABLE_TOPK_MOE_FUSION=1` in `ggml/src/ggml-cuda/ggml-cuda.cu`, skipping only the CUDA/HIP Top
- [x] **K11.1r** ✅ 2026-07-20 **: reran the same ORIG-Q4 no-spec single-slot natural 160-word prompt with only `GGML_CUDA_DISABLE_TOPK_MOE_FUSION=1` set. Artifact: `data/k11_gemma4_determini
- [x] **K12** ✅ 2026-07-11 **: net-negative on all 4 Q8 models → keep OFF (default). Dense hurt most (Qwen-27B −12/−18%, gemma4-31B −6/−7.5%); MoE marginal/noisy (gemma4-A4B −3.5/−0.3%, Q
- [x] **K14** ✅ 2026-07-16 **: resolved the MI210 `test-backend-ops` abort in `experimental-v7-candidate` with scoped flash-attn selector/device-guard fixes in `fattn.cu`, `fattn-tile.cuh
- [x] **K15** ✅ 2026-07-16 **: quiet-card retest on `4e9287eb3` shows workload-dependent speed upside. Qwen2.5-Coder-0.5B repetitive JSON edit: `292.5 -> 347.7 t/s` (+18.9%). Gemma-4-26B-
- [x] **K16** ✅ 2026-07-16 **: deployed the conservative single-server policy instead of redundant lanes. `worker_general` / `worker_math` / `toolrunner` now launch one combined speculati
- [x] **K13** ✅ 2026-07-16 **: upstream freshness was restored by `experimental-v7-refresh-20260716` (`8e5c555ab`) merged with `origin/master` `a8dc0e326`; `Q2_0` is now present again on
- [x] **K13** ✅ 2026-07-17 **: Bonsai-27B Q1_0 loads on stock experimental v7 CPU and MI210, but the corrected quiet-host prompting gate passed only 6/8 strict probes, so Q1_0 is loadable
- [x] **K13a** ✅ 2026-07-17 **: read-only follow-up classified the Q2_0 load failure as an artifact/layout incompatibility, not a bad command or ordinary incomplete download. The v7 loader
- [x] **K17** ✅ 2026-07-16 **: production-shaped measurements on the refreshed v7 candidate `8e5c555ab` are recorded in `/mnt/raid0/llm/tmp/v7-perf-20260716/v7_perf_ab_20260716.md` and th
- [x] **K18** ✅ 2026-07-16 **: fixed-chat K5 rerun passed with comparator `PASS` and zero errors; the invalid raw-completions attempt is discarded. Promotion-gate no-inference checks also
- [x] **K19** ✅ 2026-07-16 **: recorded the completed smoke run from `/mnt/raid0/llm/tmp/v7-server-smoke-20260716T153522Z/summary.json`. Rebuilt v7 HIP binary reports `version: 10075 (8e5
- [x] **K20** ✅ 2026-07-16 **: separated base-decode guards from production server/speculative path evidence. Baseline `llama-bench` guard artifacts live in `/mnt/raid0/llm/tmp/v7-perf-20
- [x] **K21** ✅ 2026-07-16 **: v7 does carry performance-oriented codepaths, but this is not promotion approval and the evidence is narrower than "v7 is faster everywhere." Present/retain
- [x] **K22** ✅ 2026-07-16 **: fixed on experimental v7 commit `96986f5e9` (`Fix grammar prefill for plain JSON schema`). Root cause: plain CLI `--json-schema` output-format grammars cons
- [x] **K23** ✅ 2026-07-17 **: `LLM_ARCH_GLM_DSA` ("glm-dsa") exists in-tree and GLM-5.2 UD-IQ2_M reports `general.architecture=glm-dsa`. Pre-fix source only constructed `llama_kv_cache_d
- [x] **K24** ✅ 2026-07-17 **: the large K17/K20 non-spec guardrail deltas were measurement/host-state artifacts, not a validated v7 source regression. Original cross-run concern: archite
- [x] **K25** ✅ 2026-07-17 **: source audit found the implementation side is already present on experimental v7: `ggml/src/ggml-cuda/mmvq.cu:281` `ggml_cuda_should_use_mmvq()` returns `ne
- [x] **K26** ✅ 2026-07-17 **: measured four KV dtype arms on MI210 with Qwen3.6-35B-A3B-MTP-Q8_0 (`9d70bae4b`, artifact root `/mnt/raid0/llm/tmp/k26-kv-cache-bench-20260717-codex/`). `ll
- [x] **K27.1** ✅ 2026-07-17 **: added Q8_0 8x8 repack/gemv/gemm plumbing on experimental v7 (`ggml/src/ggml-cpu/repack.cpp`, `repack.h`) behind explicit opt-in `GGML_REPACK_Q8_0_8X8=1`. Cl
- [x] **K27.3** ✅ 2026-07-17 **: experimental-v7 commit `aebb556b1` changes `GGML_IQK=1` so `GGML_TYPE_Q8_0` falls through to native CPU kernels unless `GGML_IQK_Q8_0=1` is explicitly set;
- [x] **K28** ✅ 2026-08-11 **: the governed direct `rocprof` v1 gate measured GDN summed-kernel shares of 15.397%, 14.649%, and 12.180% at p2048/p8192/p32768. Even an optimistic 4x op spe
- [x] **K29** ✅ 2026-07-17 **: experimental-v7 `6b93ca027` removes the `malloc`/`free` token sidecars in `common/speculative.cpp` EAGLE3 and MTP draft implementations. `llama_batch_init()
- [x] **K32** ✅ 2026-07-17 **: Stage-1 MI210 drafter execute exposed that `common/speculative.cpp` recorded `params.speculative.draft.mparams.path` but called `llama_model_load_from_file(
- [x] **K33** ✅ 2026-07-17 **: Stage-1 repaired-path 256-token requests failed near `n_tokens=257` because draft-tree raised `n_seq_max` to `32` but left draft `n_ctx` unchanged; llama.cp
- [x] **K34** ✅ 2026-07-20 **: K24.4 proved current production CPU guard cells were much slower than the 07-16 production cells on architect and ingest even after `megasync` and Firefox w
- [x] **K35** ✅ 2026-07-18 **: operator-facing throughput/context evidence is now consolidated for every production stack role/model with optimized serving shapes, memory rows, quality/ac
- [x] **K36** ✅ 2026-07-17 **: keep v7 current on promotion-relevant upstream fixes without importing unrelated backend churn. DeepSeekV4 fused hyper-connection work remains explicitly ou
- [x] **K11-REPEAT-SUMMARY-SOURCE** ✅ 2026-10-07 — [MAIN exact source and original30/30](../../artifacts/ni08/k11-repeat-summary-success-acceptance-20261007/README.md). Live K11 determinism remains independent

## Track: frontier-f6-upstream-publication
<!-- gate: none -->

> Folded from `handoffs/active/frontier-f6-upstream-publication.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F22, route 1a, operator D1/D5; retired row EVL-27 → INF-16). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Frontier F6 — Upstream & Publication Leverage

**Status**: IN PROGRESS — W2 methodology-post draft scaffold + claim backfill landed 2026-06-13; W3 generator + protocol-backfill parser + missing-field summary landed, first P-BENCH-2 section metadata backfilled 2026-06-14, public-scrub gating landed 2026-06-21, internal-alias display scrub landed 2026-06-27, protocol-backfill triage/neighbor-row bleed prevention landed 2026-06-28, pre-attestation historical review separation landed 2026-06-28, generated review queue landed 2026-06-28, and the review-decision overlay retired 325 unverified historical rows from public claims on 2026-07-06; W1/W3/W4 still open
**Created**: 2026-06-12
**Priority**: MED — D2 PR is the spearhead and already an ACTIVE queue item
**Spec**: [fable5-findings-07-strategic-frontiers.md](../completed/fable5-findings-07-strategic-frontiers.md) §F6 — read before claiming
**Related**: [llama-cpp-dsa-contribution.md](rocm-kernel-authoring.md#track-llama-cpp-dsa-contribution) (D2 = spearhead); MEASUREMENT.md (claims grammar governs every published number); `docs/guides/agent-workflows/research-writer.md` (the persona file was archived 2026-08-16 — this guide is the live surface)

#### Why

Nobody else publishes EPYC CPU-inference engineering at this depth (NUMA laws,
canonical-measurement discipline, compounding-matrix self-correction, MoE-Spec
data, roofline). The open-source-only constraint governs deploys, not publishing.
Returns: upstream maintainers prioritizing PRs we are already waiting on (DSA
#21149, STQ1_0 #22836, MTP upstreaming), free external replication, collaborators.

#### Waypoints

- **[moved: handoffs/completed/publication-upstream-program.md#w2-methodology-post (operator 2026-11-10, INF-48 restructure)]** W2 — methodology post, full text, history and open checkbox now live there. Owner: unassigned — operator to assign. [no-belief: re-homed, not done]
- **[moved: handoffs/completed/publication-upstream-program.md#w3-public-results-page (operator 2026-11-10, INF-48 restructure)]** W3 — public results page, full text, history and open checkbox now live there. Owner: unassigned — operator to assign. [no-belief: re-homed, not done]
- **[declined: ws58 2026-11-03 content-review: a cadence rule, not a task]** **W4 — cadence**: one artifact/month max. Candidates queue: NUMA topology laws; gemma4 MTP recipe; closure-inflation/remediation story; instrument-era reconciliation (epistemics piece). Acceptance: queue maintained in this file. **Queue initialized 2026-06-13**; keep unchecked until the first monthly review uses it.
- **[declined: ws58 2026-11-03 content-review: bookkeeping]** **W5 — social/X conversation ledger**: maintain `docs/publication/social/` as the append-only record of outbound social threads and notable inbound replies, every public claim linked to its in-repo receipt and MEASUREMENT.md grade. Layout + schema + gates: `docs/publication/social/README.md`. Acceptance: every posted thread has a ledger row **before** it goes out; no public number ships without an evidence pointer; corrections appended, never rewritten.
  - [x] Seed the ledger: README + schema + first transcript ✅ 2026-09-15 — `docs/publication/social/{README.md,conversations.yaml,threads/2026-09-15-x-mi210-low-quants.md}`; the MI210 low-bit-quant thread recorded with its 7 claims linked and its four soft spots. W5 stays open on the pre-post gate.

#### Gates & pitfalls

- NEVER publish F1 personal-task data — real-task corpus and operator workload stay local.
- Strip personal/infra identifiers from everything published.
- Only publish numbers that carry a protocol tag (MEASUREMENT.md grade) — dogfooding the claims grammar is the credibility.
- One artifact per month cap — publishing is yield-capture, not a second job.
- D1 smoke requires the standing bench-approval; no concurrent inference without per-run approval.

#### Reporting

Tick waypoints here, update master index row, log each published artifact in progress. W1 progress reports also go to llama-cpp-dsa-contribution.md.

#### Publication Cadence Queue

One artifact per month maximum. Do not publish two items in one month to "catch up"; stale drafts stay in queue.

| Candidate | Format | Gate before drafting | Notes |
|---|---|---|---|
| Canonical CPU benchmarking collapse story | Blog post + llama.cpp discussion | F6-W2 claim backfill/scrub complete | Draft scaffold exists in `docs/publication/canonical-cpu-benchmarking-methodology-draft.md`. |
| NUMA topology laws on EPYC | Technical note | P-BENCH-2 references and public-safe diagrams | Focus on quarter/full instance law, not private deployment details. |
| Gemma4 / MTP recipe | Repro recipe | Local canonical result with protocol tag | Do not publish vendor or upstream claims without local reproduction. |
| Closure-inflation and remediation | Postmortem | Instrument-era references scrubbed | Teach how stale derived views created false confidence; avoid personal task data. |
| Instrument-era reconciliation | Epistemics note | MEASUREMENT.md section 5 stable | Use demote/retro-certify/retire-view vocabulary; no operational secrets. |

#### Checkpoints

- 2026-06-13 W2 draft scaffold: added `docs/publication/canonical-cpu-benchmarking-methodology-draft.md`. The draft keeps `+17%` as a historical collapsed observation, distinguishes candidate publishable numbers (`4.32 -> 4.39 t/s`, `+1.6%`; `0.85 -> 1.12 t/s`, `+31.8%`; PPL `6.6985 +/- 0.708`) from claim-ready facts, and points every number at `progress/2026-04/2026-04-24.md` or `MEASUREMENT.md`. Remaining W2: backfill protocol IDs/reps/attestation refs, replace internal paths with public-safe links, and scrub host/personal details before external posting.
- 2026-06-13 W4 queue scaffold: initialized the publication cadence queue in this handoff with one-artifact/month rule, candidate formats, and gates. This is not a published artifact and does not complete W4 until the first monthly review uses the queue.
- 2026-06-13 W2 claim backfill: updated the CPU methodology draft to use the April 26 compounding matrix as the main collapse evidence (`EP frontdoor +17%` from `14.63 -> 17.18 t/s` became `+1.6%` from `20.81 -> 21.15 t/s` against proper canonical) and to treat the April 24 Q8 repack rows (`0.85 -> 1.12`, `4.32 -> 4.39`) as a separate microkernel lesson. Evidence pointers now include `epyc-inference-research/data/cpu_optimization/2026-04-26-compounding/SUMMARY.md`, `2026-04-24-q8-8x8-kernel/thread-scaling-summary.md`, `bench_canonical.sh`, `canonical_recipe.py`, and `MEASUREMENT.md`. Remaining W2: public-safe artifact labels, host-attestation IDs, raw-log/reps confirmation for CPU2 rows, final generated recipe snippet, and external scrub.
- 2026-06-13 W3 generator scaffold: added `scripts/publication/generate_public_results.py`, `tests/publication/test_generate_public_results.py`, and generated `docs/publication/public-results-draft.md` (374 rows). Validation: `python3 -m py_compile` passed; `uv run --with pytest pytest -q tests/publication/test_generate_public_results.py` -> 2 passed; `uv run --with ruff ruff check scripts/publication/generate_public_results.py tests/publication/test_generate_public_results.py` passed; `python3 scripts/publication/generate_public_results.py --check` passed. Remaining W3: protocol-tag retained rows, scrub public surface, and decide whether the generated draft should move into the public site tree.
- 2026-06-14 W3 protocol-backfill parsing: `epyc-root` `1ec09e1` adds structured protocol parsing (`protocol-id`, `n/reps`, date, attestation) and keeps incomplete protocol rows in `hold_for_protocol_backfill`; `epyc-inference-research` `7a3e931` tags the `Production Throughput - NUMA Deployment` section with initial `P-BENCH-2, n=5, 2026-03-21` metadata. Validation: `python3 -m py_compile scripts/publication/generate_public_results.py`; `uv run --with pytest pytest -q tests/publication/test_generate_public_results.py` -> 6 passed; `uv run --with ruff ruff check ...` passed; `python3 scripts/publication/generate_public_results.py --check` -> current, 374 rows. Remaining: add attestation refs before promoting the P-BENCH-2 rows to `publish_candidate`, scrub public identifiers, and decide site placement.
- 2026-06-14 W2 recipe dry-run backfill: captured a non-inference `bench_canonical.sh --dry-run` witness for the Qwen3.6 Q8 methodology example and added both the internal transcript and public-safe command/env shape to `docs/publication/canonical-cpu-benchmarking-methodology-draft.md`. Command used `-n 32 -p 0 -r 5 --dry-run`; wrapper validated and printed the canonical `taskset -c 0-95 numactl --interleave=all ... llama-bench -t 96 -fa 1 -mmp 0 ... -o md` shape without executing `llama-bench`. W2 still remains open: host-attestation IDs, public artifact labels, and raw-log/reps backfill are not complete enough for external publication.
- 2026-07-06 W2 publication-prep packet: tightened `docs/publication/canonical-cpu-benchmarking-methodology-draft.md` with public-safe claim handles (`F6-METH-C1`, `F6-METH-C2`, `F6-METH-S1`, `F6-METH-P1`), named the April 26 exact-row logs (`V2_q8_cold_canonical_repeat.log`, `E_q8_EP.log`), and made the April 24 Q8 microkernel lesson paraphrase-only unless exact raw repack logs are found or the rows are remeasured. The draft now also marks the 2026-06-14 recipe dry-run as a pre-v6 internal witness that must be regenerated from the current single-kernel recipe before external publication. W2 remains open on host-attestation/current-era rerun decision plus final external scrub.
- 2026-06-14 W3 generator hardening: changed the public-results generator so explicit but unparseable `P-BENCH`/`protocol-id` markers remain `hold_for_protocol_backfill` instead of falling through to `publish_candidate`. Validation: `python3 -m py_compile scripts/publication/generate_public_results.py`; `uv run --with pytest pytest -q tests/publication/test_generate_public_results.py` -> 7 passed; `uv run --with ruff ruff check ...` passed; `python3 scripts/publication/generate_public_results.py --check` -> current, 374 rows. No current generated rows changed, but the publication bias is now conservative for malformed protocol metadata.
- 2026-06-14 W3 missing-field summary: `generate_public_results.py` now lists exactly which protocol fields are missing for incomplete protocol-tagged rows and emits an action-count summary in `docs/publication/public-results-draft.md`. Current generated state: 374 total rows, all held for protocol backfill; the P-BENCH-2 section rows now explicitly show `missing attestation`. Validation: `python3 -m py_compile scripts/publication/generate_public_results.py tests/publication/test_generate_public_results.py`; `uv run --with ruff ruff check ...` passed; `uv run --with pytest pytest -q tests/publication/test_generate_public_results.py` -> 9 passed; `python3 scripts/publication/generate_public_results.py --check` -> current, 374 rows.
- 2026-06-21 W3 public-scrub gate: `generate_public_results.py` now computes a `Scrub status` per generated row, summarizes scrub blockers, and fail-closes protocol-complete rows to `hold_for_public_scrub` when local paths, loopback endpoints, internal role aliases, or operator/internal workflow terms are present. Current generated state: 374 total rows, all still `hold_for_protocol_backfill`; scrub summary is `public-safe surface=364`, `needs public scrub: internal role alias=10`. Validation: `python3 -m py_compile scripts/publication/generate_public_results.py tests/publication/test_generate_public_results.py`; `uv run --with pytest pytest -q tests/publication/test_generate_public_results.py` -> 12 passed; `uv run --with ruff ruff check ...` passed; `python3 scripts/publication/generate_public_results.py --check` -> current, 374 rows.
- 2026-06-27 W3 internal-alias display scrub: `generate_public_results.py` now rewrites internal orchestration labels such as `frontdoor`, `worker_general`, `toolrunner`, `ingest_long_context`, and architect/coder role aliases to public-safe display labels before row rendering and scrub classification. Current generated state: 374 total rows, all still `hold_for_protocol_backfill`; scrub summary is now `public-safe surface=374`, with the prior 10 `internal role alias` blockers cleared. Validation: `python3 -m py_compile scripts/publication/generate_public_results.py tests/publication/test_generate_public_results.py`; `uv run --with pytest pytest -q tests/publication/test_generate_public_results.py` -> 13 passed; `uv run --with ruff ruff check ...` passed; `python3 scripts/publication/generate_public_results.py --check` -> current, 374 rows.
- 2026-06-28 W3 protocol-backfill triage + parser containment: `generate_public_results.py` now emits `Protocol Backfill Summary` and `Protocol Status Summary` sections so W3 no longer presents all 374 held rows as one undifferentiated blocker. Current generated state: 374 total rows, all still `hold_for_protocol_backfill`; backfill targets are `attestation=31`, `protocol tag=18`, and `verification decision=325`; scrub remains `public-safe surface=374`. The parser now limits protocol evidence to the current row, section heading, and table preamble, preventing neighboring-row protocol bleed. Validation: GitNexus impact LOW (`impactedCount=0`); `python3 -m py_compile scripts/publication/generate_public_results.py tests/publication/test_generate_public_results.py`; `uv run --with ruff ruff check ...`; `uv run --with pytest pytest -q tests/publication/test_generate_public_results.py` -> 14 passed; `python3 scripts/publication/generate_public_results.py --check` -> current, 374 rows.
- 2026-06-28 W3 pre-attestation historical review separation: `generate_public_results.py` now recognizes protocol-tagged rows dated before the host-attestation era (`2026-06-12`) that lack attestation. The generated draft now reports `hold_for_historical_attestation_review=31` and `hold_for_protocol_backfill=343`; the review bucket is explicitly `historical attestation or remeasurement`, preventing current-host retro-certification of 2026-03-21 rows. W3 remains open because those rows need a real historical attestation artifact, a rerun under current attestation, or retirement from the public-results candidate set.
- 2026-06-28 W3 generated review queue: `generate_public_results.py` now writes `docs/publication/public-results-review-queue.md` by default and checks it under `--check`. The queue groups the same `374` generated rows by next review action: `historical-attestation-review=31`, `protocol-tag-needed=18`, and `verification-decision-needed=325`, each with source line, section, entity, metrics, status, and action guidance. Validation: GitNexus impacts LOW for `render_page`/`collect_rows`; py_compile; ruff; focused publication pytest (`17 passed`); `python3 scripts/publication/generate_public_results.py`; and `python3 scripts/publication/generate_public_results.py --check`.
- 2026-07-06 W3 review-decision overlay: added `docs/publication/public-results-review-decisions.json` and wired `generate_public_results.py` to apply dependency-free JSON review decisions before rendering the generated draft/review queue. The default decision retires `325` unverified historical rows from public claims without mutating the source `RESULTS.md`, while row-specific overrides can re-open selected rows for remeasurement or publication backfill. Current generated state: `374` total rows; `325` `retired_from_public_claims`; `31` `historical-attestation-review`; `18` `protocol-tag-needed`; all `374` remain `public-safe surface`. Validation: publication generator check, py_compile, focused pytest (`20 passed`), and focused ruff passed.
- 2026-09-15 W5 social-conversation ledger scaffolded: added `docs/publication/social/README.md` (layout, entry schema, inherited scrub/claim-grammar gates), `docs/publication/social/conversations.yaml` (append-only ledger, `social_conversations.v1`), and the seed transcript `docs/publication/social/threads/2026-09-15-x-mi210-low-quants.md` (the posted MI210 low-bit-quant thread, verbatim, plus its four recorded soft spots and evidence pointers). The ledger sits under `docs/`, outside the mkdocs `docs_dir` (`site_src/`), so nothing here is served publicly. W5 remains open on the pre-post gate: every future thread gets a ledger row before it goes out.

- 2026-11-02 W3 historical-attestation disposition: retired the 31 pre-attestation review rows from public claims after a review found no contemporaneous attestation binding the stated results to their runs. March 18 NUMA logs and March 24–28 REAP records are related evidence, not attestation of the March 21 label; the latter groups postdate it. The routing overlay preserves historical source values and allows reconsideration with a valid evidence bundle or separately attested rerun. The 18 protocol-tag rows remain under independent review.

#### Candidate — llama.cpp issue #27442 (2026-08-21, Stage-2b intake-1279#record)

> **PART ONE POSTED 2026-08-23** — [issue #27442 comment](https://github.com/ggml-org/llama.cpp/issues/27442#issuecomment-5385082723),
> operator-approved, under the operator's account. The row below reasoned that the analysis was
> blocked on G1 because "posting first offers a critique with no data behind it". On execution that
> split cleanly in two, and only the second half was ever blocked:
> the **corrections to the reporter's own artifacts** need no measurement of ours — they are facts
> about their logs — while **our boundary-sweep numbers** still do. Part one went out and says so
> explicitly: *"We have not reproduced the bug — we run this architecture on CPU and ROCm, not
> Metal — so this is analysis of your artifacts, not a second data point."*
> Every claim was re-derived from the attachments before posting, not carried from the dive:
> `n_prompt_tokens_cache` occurs **14×, all zero**; token `248046` = `<|im_end|>`; both `_noflash`
> logs contain `flash_attn = enabled`; sampler at `temp = 0.300`, so the intermittency may be the
> sampler rather than a stale state; `70aff2525` is **2026-08-20T10:43:59Z** against their newest
> build `dc72703` at **2026-08-19T15:44:15Z**, ~19 h earlier. The post does **not** claim a fix
> exists, and it rules #27450 *out* with the reason: it touches only the `mpp::tensor_ops` path,
> gated on `has_tensor` = `supportsFamily:MTLGPUFamilyMetal4_GGML` (`ggml-metal-device.m:743`),
> which an M4 does not report. Thread was OPEN with **zero** comments at post time, so this is the
> first reply. **Part two — our own greedy sweep — remains blocked on G1.**

- **[declined: operator 2026-11-09 (INF-48 triage, dropped, not done): blocked on G1 in log-linear-gated-deltanet-readiness.md; no live destination]** **B2 (B) — post our analysis upstream (part two only; part one done).** — closed as dropped, not completed; original text: `git show b3bd883d3:handoffs/active/rocm-kernel-authoring.md` line 4017. [no-belief: dropped by operator 2026-11-09]
## Track: llama-cpp-dsa-contribution
<!-- gate: none -->

> Folded from `handoffs/active/llama-cpp-dsa-contribution.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F22, route 1a, operator D1/D5; retired row INF-31 → INF-16). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### llama.cpp DSA Contribution — DSA LANDED upstream (#23346); remaining CPU-perf sub-tracks (D2/D3)

**Status**: RE-AUDITED 2026-07-17 — **generic DSA support LANDED via upstream #23346** for DeepSeek32, NOT the tracked draft #21149 -> the "track #21149 to merge" objective and D1 are SUPERSEDED. Important correction closed: pre-fix source registered `LLM_ARCH_GLM_DSA` and loaded GLM DSA tensors but did not instantiate `llama_kv_cache_dsa` for GLM; experimental-v7 commit `3dee86a5a` now wires GLM to the DSA cache/runtime path, aliases the DeepSeek32 DSA graph, requires live GLM indexer tensors, and force-builds GLM indexer Hadamard rotation tensors. Runtime GLM-5.2 fixed-`indexer_top_k=32` scaling now classifies the landed path as **DSA-DENSE-MASK**: generic DSA top-k/indexer engages in prompt processing, but final attention still scales with full KV. Live remnants: D2 sparse final-attention implementation/profiling + D3 CPU AVX-512 Lightning-Indexer, re-anchored to the landed code and re-gated on fresh profiling. All inference gated per `feedback_no_concurrent_inference.md`.
**Created**: 2026-04-29 (via research-intake of intake-506 + PR #21149 audit)
**Lifecycle**: live — audit override (2026-07-18): the original #21149-merge objective is SUPERSEDED, but the D2/D3 CPU sub-tracks are genuinely live (re-anchored to landed code, gated on fresh profiling). Prevents the dashboard heuristic from dimming this as "superseded". See [`stale-open-audit-2026-07-18.md`](../completed/frontier-lab-automation.md#track-stale-open-audit-2026-07-18).
**Updated**: 2026-07-17 — DSA landed audit reset + GLM cache/runtime wiring fix + runtime `DSA-DENSE-MASK` classification recorded; prior 2026-05-28 deepseek4 section retained as adjacent history.
**Categories**: kv_cache, inference_serving, hardware_optimization, local_inference
**Workstream**: Inference Acceleration + CPU Engineering (cross-cuts)
**Parent indices**:
- [`inference-research-index.md`](inference-research-index.md) (architectural research)
- [`inference-research-index.md`](inference-research-index.md) (kernel engineering)
**Related**:
- [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) — GLM-5.2 active target; generic DSA landed and GLM cache/runtime wiring closed on experimental-v7 `3dee86a5a`; sparse final-attention and quality gates remain open
- [`multiscreen-attention-evaluation.md`](long-context-program.md#track-multiscreen-attention-evaluation) — sub-quadratic attention survey, intake-506 documented under same-day-expansion sub-section
- [`triattention-kv-selection.md`](long-context-program.md#track-triattention-kv-selection) — retrofit selection (Expected Attention) for comparison vs DSA's integrated selection
- [`cpu-shape-specialized-gemv-decode.md`](../completed/cpu-shape-specialized-gemv-decode.md) — Phase 5 candidate (CPU26) AVX-512BW Lightning Indexer kernel; **D3 sub-track lives here**
- [`llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) — archived 2026-06-12; superseded but format template
- intake-506 (DeepSeek-V3.2 paper, arxiv:2512.02556)
- [V3.2 deep-dive](../../research/deep-dives/deepseek-v32-dsa-llamacpp-pr21149.md) — full mechanism analysis + "How we'd contribute" section

#### 2026-07-16 Audit Reset — DSA has LANDED (this handoff's premise is superseded)

**The tracked PR #21149 is no longer the path.** DSA support reached our v6 fork via a DIFFERENT upstream PR — **#23346, "DeepseekV32ForCausalLM with generic DeepSeek Sparse Attention (DSA) implementation."** Verified in v6 (2026-07-16):
- Arch enums registered: **`LLM_ARCH_DEEPSEEK32` ("deepseek32")** AND **`LLM_ARCH_GLM_DSA` ("glm-dsa")**.
- `src/models/glm-dsa.cpp` is present and loads GLM lightning-indexer tensors; `src/llama-kv-cache-dsa.cpp` implements the Lightning-indexer KV cache.
- Pre-fix source model-memory setup created `llama_kv_cache_dsa` only for `LLM_ARCH_DEEPSEEK32`; `LLM_ARCH_GLM_DSA` fell through to ordinary `llama_kv_cache`. Experimental-v7 `3dee86a5a` now routes GLM through `llama_kv_cache_dsa` and the DeepSeek32 DSA graph; current-source synthetic tests and exact `READY` GLM smoke passed.

**What this changes:**
- **D1 (pull draft #21149 / build / smoke) — SUPERSEDED.** The code is in production v6; the smoke-test now lives in the model-eval handoff [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) → **GLM-5.2** (the active DSA target; V3.2 not planned — GLM-5.2 covers this niche), not as a "pull the draft" task.
- **Monitoring PR #21149 weekly — MOOT.** DSA landed; stop tracking that PR to merge.
- **D2 (sparse-compute reality check) + D3 (CPU AVX-512 indexer) — RE-ANCHORED to landed #23346 code, not the fairydreaming draft.** Static audit (2026-07-17) found generic DSA `top_k` selection is built for both prompt processing and decode, but final attention still appears dense/mask-based. The GLM cache/runtime prerequisite is now closed by `3dee86a5a`; runtime GLM-5.2 scaling confirmed **DSA-DENSE-MASK** (`23.81 -> 21.04 -> 17.28 t/s` as prompt tokens grew `2900 -> 5906 -> 11921` under fixed `indexer_top_k=32`). D2 now needs sparse final-attention implementation/profiling, not more activation proof. D3 still needs a landed-code profile to decide compute-bound vs bandwidth-bound.
- **Cross-reference (2026-10-04, ak-ds41-main): DeepSeek-V4.1-Flash shows the same dense-mask shape.** Code reading at
  `dd6c9cdbd` (`src/models/deepseek41.cpp:1095-1100`): the top-k becomes a −inf mask over all compressed rows
  (`build_top_k_mask`), and `ggml_concat(raw_k, comp_k)` copies the full compressed plane every layer, every step
  (~29 KiB per context token per step; arithmetic, not measured). Recorded as INF-77 DS41-C123 in
  [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md); AutoKernel's route onto that graph path is
  INF-81 AKX-ALL-12 in [`autokernel-all-devices-all-dimensions.md`](autokernel-akx-program.md#track-autokernel-all-devices-all-dimensions). The
  generic sparse-gather kernel stays here (D2.4/D2.5).
  - **2026-07-19 note — D2 is also the LONG-CONTEXT GLM-quality enabler.** GLM-5.2 emits malformed output past ~12K prompt tokens (32K needle FAILS) because the `indexer_top_k` cap doesn't scale with context; only hand-tuned next-power-of-two caps stay coherent (`2048`≤2K, `4096`≤3K, `16384`≤12K). Finishing D2 (a real sparse/indexed final-attention path with a correct, length-scaling top-k) is the **durable fix** for >12K GLM coherence. **But it is ORTHOGONAL to GLM's reviewer/judge quality** — those prompts fit ≤12K and are being tested NOW on external ground-truth benchmarks (see [`glm52-reviewer-capability-gates.md`](reviewer-control-plane.md#track-glm52-reviewer-capability-gates) 2026-07-19 directive). Do not gate the reviewer-quality verdict on D2.

#### Objective (revised 2026-07-16)

Generic DSA is landed upstream (#23346) and present in v6/v7. The objective is no longer "track a draft PR to merge" — it is: (1) use the now-wired **GLM-5.2** DSA cache/runtime path (`3dee86a5a`) as the active large-MoE DSA testbed — **DeepSeek-V3.2 is NOT a planned eval** (GLM-5.2 covers the DSA large-MoE niche; V3.2 stays a supported-arch fact/fallback, not worth a second ~380 GB download + inference window), and (2) evaluate whether the two CPU-performance contribution opportunities (D2 sparse-compute attention reality, D3 AVX-512BW Lightning-Indexer kernel) are still real against the LANDED code, and pursue them upstream only if the re-gating checks pass. Original PR-#21149 tracking context is retained below as history.

##### 2026-07-16 static D2 audit

Read-only landed-code audit found:
- Prompt and decode both route through the same `decode()`/`process_ubatch()`/`build_graph()` path; the main distinction is `ubatch.n_tokens`, not a separate DSA graph.
- DSA input tensors are built per `ubatch`, with no decode-only `n_tokens == 1` gate.
- `top_k` selection is computed for all tokens in the current ubatch.
- The selected `top_k` is applied by editing a dense KQ mask before standard attention.
- The final attention call still appears dense: `ggml_flash_attn_ext(...)` over full `k/v`, or `ggml_mul_mat(k, q)` plus softmax mask.

GLM correction (2026-07-17): this conclusion applies to the generic DSA path once a DSA cache exists. Pre-fix `LLM_ARCH_GLM_DSA` source loaded DSA metadata/tensors but did not instantiate `llama_kv_cache_dsa`; experimental-v7 `3dee86a5a` closes that cache/runtime gap. Older GLM >64K run artifacts came from a stale `build-hip` binary and should not be treated as current-source long-context proof.

Conclusion: current generic DSA code appears to do top-k selection in both prompt processing and decode, but static inspection does not prove sparse-compute attention. Runtime closeout on GLM-5.2 UD-IQ2_M later confirmed **DSA-DENSE-MASK**: with fixed `indexer_top_k=32`, Lightning/indexer caches engaged at 4K/8K/16K, but prompt throughput declined with context length (`/mnt/raid0/llm/tmp/glm52-current-source-kv-scaling-20260717T130222Z/runtime_summary.md`).

#### PR State Snapshot (2026-04-29)

| Property | Value |
|----------|-------|
| PR # | [#21149](https://github.com/ggml-org/llama.cpp/pull/21149) |
| Author | fairydreaming |
| State | **DRAFT, ACTIVE** |
| Opened | 2026-03-29 |
| Last commit | 2026-04-28 |
| Commits | 58+ |
| Backends working | CPU ✅, CUDA ✅ (WMMA), Vulkan ✅ (after #22177 fix); Metal ❌ not mentioned |
| Author's caveat | *"Due to the way it's currently implemented it doesn't improve long context performance yet"* |
| Author's help requests | (1) benchmark verification on GPU clusters, (2) Vulkan debugging, (3) implicit gap: CPU benchmarks |
| Models supported | DeepseekV32ForCausalLM (V3.2 Exp, V3.2, V3.2 Speciale) |

##### What's in the PR

- New ggml ops: `GGML_OP_HADAMARD`, `GGML_OP_LIGHTNING_INDEXER`
- New KV cache classes: `llama_kv_cache_dsa`, `llama_ik_cache` (indexer keys)
- Specialized flash-attention MMA kernel sparse path (token generation)
- Conversion tooling: requires `add_bos_token=true` in tokenizer_config.json before conversion
- ~1000+ LOC across multiple files (model/architecture + ggml ops + KV cache + tests + benchmarks)

##### What's NOT in the PR yet (per author)

- Long-context speedup not yet realized — sparse path applies to token generation only, not prompt processing
- Author flagged a separate follow-on PR for "advanced sparse fattn kernel optimization" (extending sparse path to PP)
- No CPU-only benchmarks published — all reported numbers are CUDA WMMA
- Metal backend support

#### Three Contribution Sub-Tracks

##### D1 — Pull / Build / Smoke Test (SUPERSEDED; historical #21149 path)

**Effort**: ~1 day
**Visibility**: Medium (first CPU data point on a CUDA-dominated PR)
**Risk**: Low (read-only contribution; just observation)
**Inference gate**: REQUIRED per `feedback_no_concurrent_inference.md`

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D1.1 | Verify disk space for V3.2 Q4_K_M GGUF (~380 GB) on `/mnt/raid0` (3.7 TB total per `user_hardware`) | SUPERSEDED | V3.2 is no longer the planned first DSA eval target. |
| D1.2 | Pull PR #21149 as feature branch in `llama.cpp-experimental` | SUPERSEDED | DSA reached v6 through #23346; do not pull the old draft as the live path. |
| D1.3 | Build on EPYC with our standard CPU-build flags | SUPERSEDED | Use current v6/experimental-v7 code for checks. |
| D1.4 | Download V3.2-Exp Q4_K_M GGUF | SUPERSEDED | GLM-5.2 is the active large-MoE DSA target. |
| D1.5 | Convert if no Q4_K_M available — `convert_hf_to_gguf.py` per PR's `add_bos_token=true` requirement | SUPERSEDED | Historical #21149 context only. |
| D1.6 | **Quality gate**: GSM8K + GPQA-Diamond at 32K context, replicate "V3.2-Exp ≈ V3.1-Terminus" | SUPERSEDED | Replace with GLM-5.2 load/smoke + long-context DSA probe. |
| D1.7 | **Throughput gate**: t/s at 16K / 64K / 128K context, V3.2 with DSA active vs MLA-only baseline | SUPERSEDED | Reprofile D2/D3 only after landed-code GLM evidence. |
| D1.8 | Post results as comment on PR #21149 | SUPERSEDED | No live PR comment action. |

**Decision gate replacement**: GLM-5.2 now loads coherently, the landed DSA path processed a stale-binary true >64K prompt with `Lightning Indexer enabled` (`/mnt/raid0/llm/tmp/glm52-dsa-true64k-probe-20260717T0125/`), and current-source `3dee86a5a` smokes prove GLM cache/runtime wiring (`/mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344/`). Current-source fixed-`indexer_top_k=32` KV scaling (`/mnt/raid0/llm/tmp/glm52-current-source-kv-scaling-20260717T130222Z/runtime_summary.md`) confirmed D2 is live: final attention behaves as dense-mask. If the CPU Lightning-Indexer is compute-bound, D3 may also be live.

##### D2 — Sparse-compute reality check / possible follow-on PR

**Effort**: ~1-2 weeks
**Visibility**: HIGH (real upstream contribution, closes the long-context-speedup gap that's currently the PR's biggest known limitation)
**Risk**: Medium (kernel work; CUDA + CPU paths both involved)

Historical #21149 context said sparse path applied only to **token generation** (`batch_size=1`) and prompt processing remained dense. Landed-code static audit does **not** show that exact split: top-k selection appears in both prompt processing and decode. The live question is whether the final attention op is still dense-mask compute in both paths, which would explain why long-context speedups may remain unrealized.

Author's note (paraphrased): *"separate PR needed for advanced sparse fattn kernel optimization"*

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D2.1 | Read the landed #23346 sparse path — identify whether DSA is prompt-only, decode-only, or shared | DONE | Static audit: top-k selection is shared across prompt/decode; final attention appears dense/mask-based. ✅ 2026-07-16 |
| D2.2 | Runtime closeout: profile one prefill batch and one single-token decode with a DSA model | DONE | Current-source GLM fixed-top-k run completed 4K/8K/16K with `max_tokens=1`; Lightning/indexer caches engaged and prompt throughput declined with KV length. ✅ 2026-07-17 |
| D2.3 | Vary KV length while keeping `indexer_top_k` fixed | DONE | Full-KV scaling observed: `23.81 -> 21.04 -> 17.28 t/s` at `2900 -> 5906 -> 11921` prompt tokens, classification `DSA-DENSE-MASK`. ✅ 2026-07-17 |
| D2.4 | If dense-mask scaling is confirmed, design sparse-fattn extension | SCOPED | 2026-07-18 source prep: existing `ggml_get_rows()` is not sufficient because KV positions sit on dim2; useful path is a new indexed DSA attention op with CPU oracle and fused GPU implementation, guarded behind fallback. Prep note: `/mnt/raid0/llm/epyc-inference-research/docs/reference/benchmarks/glm_mtp_sparse_attention_prep_20260718.md`. ✅ 2026-07-18 |
| D2.5 | Implement CPU path first if a real dense-mask bottleneck is confirmed | PENDING | `tests/test-backend-ops.cpp` existing + new PP tests; validate PPL bit-exact. |
| D2.6 | Throughput gate: PP/decode t/s improvement at 32K / 64K / 128K | **GATED on user inference approval** | Must show real sparse-compute speedup, not just preservation. |
| D2.7 | CUDA path follow-on (optional; can split as separate PR) | PENDING | Author has CUDA expertise; we don't necessarily need to implement. |
| D2.8 | Open as a separate upstream PR or current-master patch if the gap still exists | PENDING | Do not target the superseded #21149 draft as the live integration path. |

**Decision gate before starting D2 implementation**: closed 2026-07-17. The GLM-5.2 landed-code smoke shows the DSA cache/runtime path is real, and runtime scaling shows final attention work still scales with full KV despite top-k selection. D2 implementation can now be scoped as real sparse final-attention work.

##### D3 — AVX-512BW Lightning Indexer (Zen 5 SIMD)

**Effort**: ~1 week
**Visibility**: HIGH (first CPU SIMD optimization on the DSA path)
**Risk**: Medium (profile may show indexer is BW-bound; if so, SIMD is a no-op)

**Cross-track**: Lives in `cpu-shape-specialized-gemv-decode.md` Phase 5 candidate (CPU26). This handoff tracks the strategic context; the SIMD work itself happens in the kernel handoff.

Author commit (2026-04-28): *"ggml : optimized GGML_OP_LIGHTNING_INDEXER (added WMMA kernel >= Ampere)"* — CUDA path got WMMA optimization. CPU path is presumably scalar.

Our angle (per `project_zen5_vnni_vs_maddubs` + `project_q8_8x8_avx512bw_outcome` memories): we have established Zen 5 SIMD expertise. The Lightning Indexer's FP8 head-weighted scoring with block-64 quantized key cache is the kind of operation our existing AVX-512BW work targets.

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D3.1 | Profile current CPU `GGML_OP_LIGHTNING_INDEXER` with `perf record` to confirm compute-bound | CLOSED NO-GO ✅ 2026-07-19 | OP-2/B4 profile on GLM-5.2 `p5906`, `indexer_top_k=2048` measured `ggml_compute_forward_lightning_indexer` at only `1.08%` of cycle samples; quantized dot products, flash-attn, and OpenMP/runtime frames dominate. Artifact: `/mnt/raid0/llm/epyc-inference-research/data/op2_canonical_window/op2_b4_dsa_d3_profile_20260719T075142/b4-dsa-d3/summary.md`. |
| D3.2 | If compute-bound: design AVX-512BW kernel for indexer dot-product + top-k selection | DEFERRED | Do not start from current evidence; reopen only if D2 real-sparse final-attention or a materially different serving shape makes Lightning Indexer cycle share material. |
| D3.3 | Implement kernel with `vpmaddubsw`+`vpmaddwd` (NOT VPDPBUSD, per Zen 5 finding) | PENDING | ~300-500 LOC est. |
| D3.4 | Correctness gate: PPL bit-exact vs scalar baseline | PENDING | Standard test-backend-ops + 32-chunk PPL pattern |
| D3.5 | Throughput benchmark: indexer-time fraction before/after at 96 threads | **GATED on user inference approval** | Falsify "indexer FP8 kills CPU advantage" |
| D3.6 | Auto-mbind the indexer key cache buffer (if it's a separate allocation) per `feedback_repack_buffer_numa_mbind` | PENDING | Only if profile shows multi-thread NUMA pressure |
| D3.7 | Open upstream PR against current master if profiling justifies it | PENDING | Specifically scoped to "ggml-cpu/arch/x86 LIGHTNING_INDEXER kernel" |

**Decision gate after D3.1**: current landed-code profile says D3 is not worth immediate SIMD work. The Lightning Indexer path is active, but only `1.08%` of cycle samples on the OP-2/B4 GLM-5.2 8K profile. Redirect effort to D2/sparse-final-attention or higher-share CPU bottlenecks unless a later serving shape changes the profile.

#### 2-Models-for-1 Leverage Statement

Both V3.2 (671B-class) and the GLM-MoE-DSA family use DSA with identical indexer + KV cache infrastructure. **This unlock has now HAPPENED in two steps: generic DSA landed via #23346, registering `deepseek32` + `glm-dsa` in v6, and experimental-v7 `3dee86a5a` wired GLM into the DSA cache/runtime path**. V3.2, GLM-5.1, and GLM-5.2 are now supported by the same DSA infrastructure, exactly the multi-model-for-one-effort payoff this handoff bet on.

This is the core reason this handoff exists as a strategic tracker rather than a single-model evaluation. Effort here pays off twice (or more, as DSA propagates to future DeepSeek / GLM model families).

Cross-ref: [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) is the GLM-5.1 evaluation tracker; it's been gated on this exact DSA implementation work.

#### Decision Gates

| Gate | Trigger | Action |
|------|---------|--------|
| **D1 START** | OBE — DSA landed via #23346 | Do not pull/build the superseded draft PR as the live path |
| **D2 START** | GLM-5.2 current-source cache/runtime smoke succeeds + prompt processing is still dense/unimproved | Begin D2 design |
| **D3 START** | GLM-5.2 current-source cache/runtime smoke succeeds + D3.1 profile confirms compute-bound | Begin D3 kernel work |
| **D2 / D3 PARALLEL** | Both above gates met | Can run concurrently — different code paths |
| **PR #21149 MERGED** | OBE for this handoff | No action; landed-code path is #23346/current upstream |
| **GLM-5.2 ACTIVATION** | OBE — no longer gated on a V3.2 validation: DSA landed (#23346); activation = GLM-5.2 UD-IQ2_M download + smoke-test | Hand off to `glm51-reap-cpu-evaluation.md` (GLM-5.2 plan) |
| **DEPRIORITIZE** | Author abandons PR OR upstream rejects DSA design | Re-evaluate; possibly maintain a fork-only path |

#### Monitoring Cadence

| Target | Cadence | Signal |
|--------|---------|--------|
| PR #21149 commits | MOOT | Stop tracking for merge-readiness; retained as historical context |
| PR #21149 description | MOOT | Stop tracking for merge-readiness; re-check landed code instead |
| Issue #20363 (tracking) | Monthly | Status changes |
| Issue #21458 (`GGML_OP_GATED`) | Monthly | Supporting infrastructure status |
| GLM-5.1 GGUF availability | Monthly | Community Q4_K_M release |

Optional: schedule a weekly background agent via `/schedule` to check PR state and notify on caveat removal.

#### Cross-References

- **Parent intake**: intake-506 (DeepSeek-V3.2 paper, arxiv:2512.02556) — full mechanism details
- **Sibling intake**: intake-502 (KSA) — explicitly cites V3.2 as same first-principle of sequence-level KV compression
- **Architecture parent**: arxiv:2502.11089 (NSA — DSA's parent paper, Native Sparse Attention)
- **Deep dive**: `/workspace/research/deep-dives/deepseek-v32-dsa-llamacpp-pr21149.md` — full PR audit + "How we'd contribute" expansion
- **Existing fork commit**: `1c0d9081f` (DeepSeek v3.2 chat parser, already on `production-consolidated-v3`)
- **Comparison axis**: `triattention-kv-selection.md` S1 PPL-at-50%-eviction gate template — reusable for D1.6 quality validation

#### Adjacent Upstream Arch Work — deepseek4 (DeepSeek-V4-Flash)

Tracked as a sibling effort, NOT folded into this handoff. V4 is a fundamentally new arch (CSA + HCA + indexer + compressor + manifold-constrained Hyper-Connections), not a DSA derivative — porting it is a multi-thousand-line arch addition, not an ops-add.

- **Upstream issue**: ggml-org/llama.cpp#22319 (model request, open)
- **WIP discussion**: ggml-org/llama.cpp#22376 (4+ community forks: nisparks `wip/deepseek-v4-support`, draft PR #22378 "no intent to merge", cdome94, Fringe210, antirez/llama.cpp-deepseek-v4-flash)
- **RESOLVED 2026-08-09; local testing closed 2026-08-26**: `deepseek4` **merged upstream** as PR #24162 (`8c146a836`) and is present in `production-consolidated-v8` (`src/llama-arch.cpp:81`). Our out-of-tree port is moot — the ik_llama branch `feature/deepseek4-port` is dead and the port handoff is closed ([`../completed/deepseek-v4-flash-cpu-port.md`](../completed/deepseek-v4-flash-cpu-port.md)). The completed 0731/`draft-dspark` evidence is preserved in [`deepseek-v4-flash-0731-dspark.md`](../completed/deepseek-v4-flash-0731-dspark.md); the operator declined further local model testing.
- <s>**Our port**: experimental branch `feature/deepseek4-port` off ik_llama production tree</s> — superseded, see above
- **Watch trigger**: if a core contributor (fairydreaming or similar) opens a deepseek4 upstream PR, our role mirrors D1 (CPU benchmark contribution against canonical NPS4 stack); roll back our experimental branch in favor of the upstream PR for review and merge.

#### Notes

The "we'd need to write a fork patch" framing in earlier glm51 handoff text was generated by extrapolation from a stale handoff line ("indexer not yet supported") that was true for PR #19460 in February but no longer reflects upstream state. The active reframe is: **track + test + selectively contribute**, not **write from scratch**.

`feedback_no_concurrent_inference.md` rule applies to every benchmark execution in this handoff. The `[GATED]` markers above are explicit; the experimental-kernel agent should not run any inference without per-run user approval.

#### Research Intake Update — 2026-06-20

##### GLM-5.2 raises the stakes on the DSA forward pass (intake-699)

- **GLM-5.2 (754B GLM-MoE-DSA) is now the PRIMARY GLM target** (intake-699: unsloth dynamic quants of `zai-org/GLM-5.2`, MIT, 1M context; supersedes GLM-5.1). 2026-07-16 correction: the old "PR #21149 is the gating dependency" statement is superseded; v6 contains generic DSA via #23346. The live gate is now GLM-5.2 UD-IQ2_M completion, integrity verification, load-smoke, and long-context DSA-indexer engagement.
- **Note**: #19460 remains a superseded tensor-loading PR, and #21149 remains useful historical design context, but neither is the current activation blocker. See [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) for the GLM-side disposition.

#### 2026-07-25 v8-audit note — HIP LIGHTNING_INDEXER bf16 backend-op failure CLASSIFIED (pre-existing baseline, flaky)

During v8-candidate gating (`experimental-v8-refresh-20260724`), `test-backend-ops -o
LIGHTNING_INDEXER -p type_K=bf16` fails on MI210 HIP with ERR≈1.0 (vs 1e-6 tol) — and the
paired differential proves it is **NOT a v8 delta**: production v7 failed 8/12 bf16 configs,
candidate 6/12 (identical clean-env invocation); isolated 5-rep single-config runs show it is
**flaky** (production failed rep 5/5, candidate 0/5). Durable evidence:
`epyc-inference-research/data/kernel-v8-candidate/lightning-indexer-v7-v8-{baseline,isolated}/`.
This is a real pre-existing HIP bf16 LIGHTNING_INDEXER kernel bug in the landed #23346 code —
not a promotion blocker, but it means the DSA indexer's bf16 K-cache path is numerically
untrustworthy on gfx90a until root-caused.


#### Progress checklist

- **[declined: ws58 2026-11-03 content-review: unbounded conditional; W1 (the D2 PR spearhead) is the live version]** D2 sparse-attention contribution — only if runtime profiling shows dense-mask attention still scales with full KV despite top-k
- **[declined: ws58 2026-11-03 content-review: deferred with a trigger that D3.1 refuted]** D3 AVX-512BW Lightning Indexer CPU kernel — deferred because D3.1 did not show material indexer share; reopen only after D2 real-sparse or a different shape changes the profile.
- [x] ~~GLM-5.2 (754B GLM-MoE-DSA) activation — DSA forward-pass blocker now cleared in code; pending the GLM-5.2 UD-IQ2_M download + smoke-test in `glm51-reap-cpu-evaluation.md`~~ (closed 2026-10-29 audit: OBSOLETE → GLM-5.2 UD-IQ2_M deleted; graveyard row model_registry.yaml (GLM-5.2-UD-IQ2_M unsloth, 6 shards); GLM-5.2 target dropped)

#### Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [x] **DSA-IDX.1 — Fix the indexed sparse-attention op interface before D2.4 code (intake-2122#record).** Adopt the FlashMLA sparse-decode contract: int32 indices (page*page_size + offset, -1 = invalid), per-query topk_length, attn_sink, optional extra index set; write the CPU oracle test first (dense masked FA over the same gathered rows must match bit-for-bit). Consumer: DS41-C123.1. ✅ 2026-10-29 (audit: child DSA-IDX.1 oracle ticked 2026-10-21 (test-dsa-sparse-attn-oracle pass=11 fail=0 @ 6b8291de5); contract+scalar reference done 2026-10-20; interface fixed before D2.4 as required) [no-belief: audit-reconciliation]
  - *(2026-10-20.)* Contract + scalar reference + two dense-masked oracles on `experimental/intake-fixes-20261020` @ 6b8291de5; oracle test queued.
  - [x] **DSA-IDX.1 oracle** ✅ 2026-10-21: `test-dsa-sparse-attn-oracle` pass=11 fail=0 (sparse reference == dense-masked oracle bit-for-bit; invalid indices rejected) on `experimental/intake-fixes-20261020` @ 6b8291de5.

- **[moved: handoffs/active/long-context-program.md#dsa-contribution-and-expected-attention-audits (operator 2026-11-10, INF-48 restructure)]** W1 — D2 PR spearhead, full text and open checkbox now live there. Owner: autokernel via INF-59 (`long-context-program.md` header owner; operator to confirm). [no-belief: re-homed, not done]
- **[moved: handoffs/active/long-context-program.md#dsa-contribution-and-expected-attention-audits (operator 2026-11-10, INF-48 restructure)]** K31 — Expected-Attention server wiring + DSA prompt-path audit, full text and open checkbox now live there. Owner: autokernel via INF-59 (operator to confirm). [no-belief: re-homed, not done]

### D-LSA research intake — approved 2026-11-03

- **[re-homed: operator 2026-11-09 (INF-48 park decision): moved with full text to `long-context-program.md` D-LSA research intake, which owns the LSA work]** **LSA-PORT-1 — original text: `git show 4c8fa6212:handoffs/active/rocm-kernel-authoring.md` line 3911. [no-belief: re-homed, not done]

- [x] **ROCK-AITER-GFX90A** (llama.cpp half) ✅ 2026-11-10 — closed on the C10 evidence: AITER-PORT-1 gemmdown KEEP 1.127x at d32768 (pp2048; 1.163x d0), quality re-scored CORRECT (`c10-gemmdown-correct-r2-20261109`), operator-accepted, origin/main 63d62eae3. The vLLM-on-gfx90a half is split out as ROCK-AITER-GFX90A-VLLM below. [belief: cc] Original text: [non-inference then inference] Probe AMD AITER (github ROCm/aiter) kernels on the MI210 (gfx90a) as a kernel source for the C6 llama.cpp HIP backend AND for vLLM (operator 2026-11-05: unconditional, since it can help our llama.cpp directly). vLLM 0.33 disables AITER on gfx90a ("AITER not built for gfx90a, rmsnorm -> SEGV", `vllm/platforms/rocm.py:1426`). Assembly and FP8 kernels need MI300-class instructions and are out of scope; the Composable Kernel and Triton ops are in scope (int8 and bf16 GEMM / scaled-mm, rmsnorm, fused MoE, paged and flash attention). Step 1 (code): build AITER for gfx90a in a scratch env, list per op builds / passes correctness / fails with the reason. Step 2 (gpu row, quiet GPU only): time each passing op against the C6 HIP equivalent at the Q38P-4b and production shapes (mmq/mmvq for Q8_0, FA at 8k/32k, rmsnorm), same inputs. Done when the op table with per-op speedup vs C6 is filed; any op >= 1.10x faster opens a port task into the llama.cpp experimental tree (champion workflow). Origin: Q38P-4/4b vLLM comparison (`mi210-serving-program.md`). [no-belief: new box]
  - *(2026-11-06, main-inf22)* **Step 1 RESULT** — AITER builds for gfx90a after a module_custom fp8-guard patch; op tests pass: rmsnorm, rope, gemm, PA, mha; CK MoE + sorting unsupported on gfx90a. Step 2 (timing vs C6) pending GPU; asm path superseded the scope note (T1 retargets gfx942 asm). [belief: cc]
  - *(2026-11-09 schedule readiness, inf48-triage)* Step 2 packet B exists and its `SOURCE.sha256` verifies: `/mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/rock-aiter-timing-20261105/{launch.sh,spec.json,job.py,precond.py,check_complete.py}` (id `rock-aiter-timing-20261105`, regions `mi210_0,184-191`, exclusive quiet GPU, min window 3600 s, ~7200 s, `filler_run15.sh`). Blocker: `precond.py` needs packet A `rock-aiter-build-20261105/out/RESULT.json` with `complete=true`; that file is absent (out/ holds results.jsonl + units only) and packet A rows are in `needs-filing` state (BACKLOG-handoff-agentic-rocm-kernel-authoring.md) — file packet A (apply decision_rule, `touch filing-done/*.FILED`), producing RESULT.json, then `publish_row.py` packet B. Overlap: `ak-asm-aiter-vs-c6-timing-20261106-r2` already times the 7 AITER asm families vs C6 (also needs-filing); packet B covers only the CK/Triton ops (rmsnorm, gemm_i8, gemm_bf16, fa). [no-belief: readiness audit, no measurement]
  - *(2026-11-09, aiter-file)* **Step 2 RESULT (packet B r2, `rock-aiter-timing-c9-r2-20261109`): verdict PORT_CANDIDATES, 51 port cells (27B 22, q3_4b 17, A3B 12), 7 FA recheck cells.** Regime: test-backend-ops perf single-op vs AITER torch.cuda events, 8 host threads, gpu-quiet; champion C9 d210f85c2 proven, AITER resident. Raw: `/mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/rock-aiter-timing-c9-r2-20261109/out/RESULT.json`. Diagnostic, not a formal gate. [belief: cc]
    - **Shape match.** `q3_4b` (hidden 2560) is not on the MI210: Qwen3-4B Q8_0/BF16 are retired (`model_registry.yaml` deleted ledger) and absent from `stack_topology.yaml`. Its 17 candidates and 2 of 7 FA cells carry no serving weight. A3B dense gate_up/down are proxies for MUL_MAT_ID, so they do not bind either (its prefill is `mul_mat_q<8,64>`, untimed here). Only 27B binds: flops per dispatch in `c8-headroom-gpu-profile-20261108` equal 2*N*K*M exactly for `down`/`gate_up` M=2048 (365.07 GF) and `qproj` (128.85 GF).
    - **What AITER wins.** M>=512 cells are not launch artifacts: reps separated, 27B CV <=3.1% both sides, 200 us to 8 ms per op. Small shapes: bf16 GEMM loses at M=1 and M=4 (0.39-0.68x); RMSNorm, fused add and rope are launch-bound losers at M=1 and M=4; FA nq=1 is 0.06-0.14x. 27B i8 GEMM does win at small M (1.13-1.18x at M=1, 1.68-1.82x at M=4) but against the MMVQ/non-q8wv route, which is not what DFlash decode runs. 27B M=2048 kernel-vs-kernel (trace ms against AITER, not test-backend-ops us): `down` 7.62 ms (Cijk MT64x64x64) vs 3.11 i8 / 3.16 bf16 = 2.45x / 2.41x; `gate_up` 3.47 ms (MT256x160x64) vs 2.86 / 3.12 = 1.21x / 1.11x; `qproj` 1.32 ms vs 1.01 / 1.15 = 1.31x / 1.15x. The `down` gap is mostly hipBLAS tile selection, not arithmetic: identical 365 GF runs in 7.62 ms on MT64x64x64 and 3.47 ms on MT256x160x64. Different algorithm/layout caveats: AITER i8 uses pre-quantized activations (no quantize cost, different numerics from production f16 h20 route); AITER bf16 needs bf16 weights, production converts Q8_0 to f16.
    - **Amdahl ceilings (27B Q8_0, busy-time shares, C8 profile, single-sequence).** Prefill ub2048 d0/d32768: `down` tile fix alone 1.17x/1.14x; timed cells only i8 1.28x/1.22x, bf16 1.24x/1.19x; ceiling if untimed Cijk (MT64x32x64 etc., 20.9%/18.3%) also reach the `down` ratio 1.52x/1.41x i8, 1.46x/1.36x bf16. DFlash decode: no timed cell matches `q8wv_mul_mat<8,1>` (M=8; timed M are 1,4,512,2048), and q8wv is already our port of AITER wvSplitK. Bandwidth-only bound: q8wv at 872 GB/s, AITER M=4 at 1343 GB/s = 1.54x, on 58.6%/54.8%/45.8% share at d8192/32768/131072 = 1.26x/1.24x/1.19x (hypothesis, M=8 unmeasured; HBM-achievable cap 1.30x/1.27x/1.22x). RMSNorm 1.8% and rope 0.6% of prefill: <=1.01x.
    - **FA 7 cells: artifact, not a port case.** Champion log shows `ggml_cuda_fa_asm: fallback (mask is not a (padded) causal or full mask)` at nq=512, so the 5.8x compares AITER non-causal against a fallback path. Production prefill at d32768 runs ck_tile FmhaFwd at 24.95 ms per dispatch for nq=2048; the fallback cell takes 25.6 ms for nq=512. Scaled nq=512 estimate is ~6.2 ms against AITER 4.42 ms, about 1.4x, giving <=1.05x prefill at d32768 and <=1.004x at d0. Decode nq=1 is 0.06-0.14x (AITER loses). Recheck that would settle it: causal mask with the production CK route (proved by log line), nq=2048 at kv 32768, AITER against Q8_0-equivalent KV (bf16 KV doubles KV bytes), identical inputs with max-diff reported. Not justified now.
    - **Recommendation: no port task ahead of C9 re-anchoring.** Opens under this box's >=1.10x rule, after re-anchor: AITER-PORT-1 below. Decode M=8 needs one cell before any decode claim.
    - [x] **AITER-PORT-1** [non-inference then inference] Prefill GEMM for 27B Q8_0 on the production h20 route at M~2048. Order: (a) force a better hipBLAS tile/kernel for N<K `down` shapes or equivalent CK kernel (MT64x64x64 at ~48 TF vs ~105 TF on MT256x160x64); (b) port a CK bf16-class GEMM only if (a) leaves `down`/MT64x32x64 above 1.10x. Time against the C9 champion with GPU-resident proof and the real prefill; keep f16 numerics until a quality gate says otherwise. Done when prefill ub2048 d32768 is >=1.05x vs champion at unchanged output quality, or the tile hypothesis is refuted. ✅ 2026-11-10: done-when met by `c10-gemmdown-prefill-ab-20261109` KEEP (pp2048 d32768 1.127x, d0 1.163x vs C9, tile proof MT160x256 258 / MT64x64 0 on C10) at unchanged output quality (`c10-gemmdown-correct-r2-20261109` witness-addendum re-score CORRECT, KLD -0.0, top-1 99.997%, operator accepted 2026-11-10); step (b) CK port not needed. C10 is the reference champion (progress/2026-11/2026-11-10.md). [belief: cc]
      - [x] **AITER-PORT-1-QUALITY** ✅ 2026-11-10: satisfied by `c10-gemmdown-correct-r2-20261109` WITNESS-ADDENDUM re-score CORRECT (operator accepted); original note: Run the quality row; c10-gemmdown-correct-r2 and c10-fold-gate smokes failed 20:55-20:57Z on the residency check (PIPE-EVE-RESIDENCY-FALSE-FAIL), so both are unpublished; c10-fold-cpu-gate is running. [no-belief: tooling-repair]
      - Step (a) result 2026-11-09 (row c9-gemm-tile-select-20261109, filed pass): TILE_CONFIRMED. 27B down M=2048 forced-64x64x64 baseline 7843.98 us; best arm 160x256x64 3862.97 us = 2.031x (rule >=1.5x, reps separated; 256x160x64 2.02x); all 9 arms correct (rel_l2 <=1.2e-6), baseline bit-identical; control gate_up forced 64x64x64 0.487x. Mechanism ROCBLAS_TENSILE_GEMM_OVERRIDE_PATH, no source change. Box NOT ticked: needs end-to-end prefill ub2048 d32768 >=1.05x. Step 2 of the C10 path is in progress (as of 2026-11-09 wrap-up, pipeline-mgmt); steps 3-4 (real-prefill A/B against the champion) follow. [no-belief: partial status note]
      - Step (a) end-to-end 2026-11-09 (row c10-gemmdown-prefill-ab-20261109, GPU, store gpu-20261109-7bcf6218b-c10gemmdown vs C9 d210f85c2): verdict KEEP. Qwen3.8-27B Q8_0, llama-bench prefill ub2048 np1, q8_0 KV, 8 host threads, gpu-quiet, samples_ts medians, 2 AB/BA rounds (stop-on-answer): pp2048@d32768 1.127x (per-round 1.128, 1.126; keep 1.05, answer 1.10), pp2048@d0 1.163x, tg128@d0 1.022x, tg128@d32768 1.016x (floor 0.97). Tile proof on the real pp2048 graph: candidate MT160x256x64 x258 with the override witness, C9 MT64x64x64 x128 and no witness; residency proven (VRAM 31.8 GB, 0 foreign). Raw: `/mnt/raid0/llm/tmp/c10-gemmdown-prefill-ab-20261109/out/RESULT.json`. Diagnostic A/B, not a formal gate. Box NOT ticked: the done criterion also needs unchanged output quality; the quality row c10-gemmdown-correct-20261109 never ran (smoke failed, plumbing smoke did not hold VRAM), republished as c10-gemmdown-correct-r2-20261109. Option (b) (CK bf16 GEMM port) stays closed unless `down` stays above 1.10x; not re-measured yet. [belief: cc]
- [x] **ROCK-AITER-GFX90A-VLLM** ✅ 2026-11-12 — row `vllm-aiter-gfx90a-gpu-20261111-r3` filed pass, AITER_VLLM_GFX90A_KEEP:ATTN: ATTN ON/OFF pf2048 1.109x, pf8192 1.103x, np1 0.996, np4 0.994 (flash_attn_varlen_func engaged 648 calls in each of 3 ON units); GEMM and RMS NO_GAIN (0.99-1.014); MoE not applicable (dense model). All units valid, no foreign KFD pid; the keeper's CONTAMINATED.json (pid 3332670) was a misattribution of ATTN-r1's own docker vLLM process. KEEP opens a vLLM-serving adoption task for the AITER attention backend (prefill only; decode neutral). [belief: cc] Original: [non-inference then inference] vLLM-on-gfx90a half of ROCK-AITER-GFX90A (split out 2026-11-10; original text kept): Probe AMD AITER (github ROCm/aiter) kernels on the MI210 (gfx90a) as a kernel source for vLLM (operator 2026-11-05: unconditional). vLLM 0.33 disables AITER on gfx90a ("AITER not built for gfx90a, rmsnorm -> SEGV", `vllm/platforms/rocm.py:1426`). Assembly and FP8 kernels need MI300-class instructions and are out of scope; the Composable Kernel and Triton ops are in scope (int8 and bf16 GEMM / scaled-mm, rmsnorm, fused MoE, paged and flash attention). Origin: Q38P-4/4b vLLM comparison (`mi210-serving-program.md`). Standing evidence from the llama.cpp half: Step 1 built AITER for gfx90a (module_custom fp8-guard patch) and rmsnorm, rope, gemm, PA, mha pass, CK MoE + sorting unsupported; nothing has yet been run through vLLM. [no-belief: split box, no new measurement]
  - *(2026-11-12, autokernel)* r3 PASS: AITER attention KEEP inside vLLM (prefill +10.9%/+10.3% at 2K/8K, decode flat); GEMM/RMS no gain. **vLLM track PARKED by operator 2026-11-12**: we do not serve with vLLM; no further vLLM work is picked up as backlog. Kernel effort goes to the llama.cpp champion only.
  - *(2026-11-11, autokernel)* [inference] Row vllm-aiter-gfx90a-gpu-20261111. Q: does AITER GEMM/ATTN/RMS (MoE off) speed up vLLM 0.33 on MI210 (Qwen3-4B-Instruct-2507 bf16)? Keep an op iff correct (greedy prefix >=32/64, mean |dlogprob|<=0.10, AITER calls>0) and >=1.10x ON/OFF on any metric with none <0.95. stop-on-answer: every op has a status. stop-on-futility: a SEGV, build failure or incorrect result ends that op, not the row; PATCH_ANCHOR_MISMATCH ends the row. gate-class = futility-only. [no-belief: row prepared]
  - *(2026-11-11, autokernel)* `vllm-aiter-gfx90a-gpu-20261111` (r1) was killed by the session at rc=143 (14:25Z, 3 min into its GPU grant): its prep pulled the ~35 GB vLLM image inside the grant. No RESULT.json; the decision rule was never evaluated, so it is not filable (no manifest left; `file_result.py` SKIPs) and is SUPERSEDED by `vllm-aiter-gfx90a-gpu-20261111-r2` (image pre-staged outside the grant, fails fast). r2 is GRANTABLE/QUEUED (gpu-q3, rank 150), not yet run; box stays open. [no-belief: row superseded, no result]


### Done

- [x] **D4** ✅ 2026-08-13 — reproduced on
- [x] **—** ✅ 2026-07-16
- [x] **—** ✅ 2026-07-16
- [x] **—** ✅ 2026-07-16
- [x] **—** ✅ 2026-07-16
- [x] **—** ✅ 2026-07-17
- [x] **—** ✅ 2026-07-19

## History

- 2026-11-20 compacted 113 ticked box(es) older than 30 d -> [rocm-kernel-authoring-history-2026-11-20.md](../archived/rocm-kernel-authoring-history-2026-11-20.md) (handoff_compact.py)

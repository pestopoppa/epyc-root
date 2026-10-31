# Vidya Belief-Substrate Program

**Scratch**: `/mnt/raid0/llm/tmp/vidya-belief-substrate-program/` · worktrees: `/mnt/raid0/llm/worktrees/vidya-belief-substrate-program-*` NI08 source and native review and private ledger coverage preparation: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/`, `/mnt/raid0/llm/tmp/ni08-inf50-projection-finish-20261007/`; MAIN acceptance originals `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/`. Further own recipe and original publication custody: `/mnt/raid0/llm/worktrees/ni08-c26-native-recipe-20261007/`, `/mnt/raid0/llm/tmp/c106-root-wrap-publish-*`, `/mnt/raid0/llm/tmp/threeview-narrow-validation-*`, `/mnt/raid0/llm/tmp/intake175-narrow-validation-*`. Codex NI scope: `/mnt/raid0/llm/tmp/codex-ni-20261024-vidya/` · `/mnt/raid0/llm/tmp/refactor-01a16fc3/` (M4 and HIL prospective writer packets and retained capture evidence; keep)

LB4.9 prospective combined-source custody (retain native evidence and qualified scheduled packet): `/mnt/raid0/llm/tmp/codex-ni-lb49-combined-ready-20261030/`, `/mnt/raid0/llm/tmp/codex-ni-lb49-write-wiring-20261030/`.

Retired Codex NI ROOT worktree custody: `/mnt/raid0/llm/tmp/codex-ni-root-legacy-retirement-20261030`; exact historical refs and dirty bytes remain preserved.

**Status**: active
**Created**: 2026-08-09 (via research intake, operator-approved Stage-3 plan `linear-kindling-possum`)
**Categories**: knowledge_management, agent_architecture
**Audit record**: [`research/deep-dives/vidya-belief-substrate-audit.md`](../../research/deep-dives/vidya-belief-substrate-audit.md) (37 dive-verified sources, intake-1031..1067)
**v1 draft**: `tmp/vidya-epyc-governance-pilot-handoff.md` (2,682 lines; superseded as a plan by this handoff + the audit; retained as the source text for V2.1)

## Objective

Build the claim-level epistemic substrate the audit verified as EPYC's genuine gap: typed
claim/evidence/intent frames on an append-only ledger, a deterministic graded fold, refusal-
semantics freshness gating for research/wiki knowledge, and (later) provenance-gated actuation —
by **adopting** the frame/ledger prior art and spending all invention on the epistemic kernel.
Operator priority: an integrated solution that works, not novelty.

## Relationship & constraints (read before any task)

- **Rides, never rivals**: [`evidence-plane-ledger-and-sequential-verdicts.md`](evidence-plane-ledger-and-sequential-verdicts.md)
  conventions (per-question row shape, supersession folding, era discipline) and the
  `autokernel/journal.py` patterns (fsync-per-event, pure rebuild, `RETRIEVAL_SUPERSEDED`,
  view-consistency checks) are the house style this program extends to the research/wiki domain.
  The H1 non-overlap contract stands: the evidence plane remains authoritative for trial/verdict
  events.
- **Scope = the three verified gaps**: (1) claim-level dependency edges for research/wiki
  knowledge (NOT-FOUND as any existing design); (2) refusal-semantics freshness gating of
  knowledge; (3, later phase) provenance-gated actuation. Cross-worker snapshot coherence and the
  value-divergence axis are *related* diagnoses owned elsewhere — reference, don't absorb.
- **Read-only surfaces**: `MEASUREMENT.md` + annexes (human-amendment-only),
  `orchestration/instrument_eras.yaml` (append-only, human-written). Measurement artifacts are
  evidence; the constitution decides admissibility.
- **Vocabulary: map, don't fork**: `retro-certify`/`demote-to-prior`/`retire-view`
  (MEASUREMENT.md §6); `fresh`/`aging`/`stale`/`missing` + `observed|silent|absent` ×
  `populated|empty|unknown` (`dashboard/freshness.py` is "THE ONE CLASSIFIER" — any new freshness
  state must map onto or extend it explicitly); `accumulating`/`confirmed_improvement`
  (sequential verdicts).
- **Promoted 2026-08-26 (P5c verdict PROMOTE); shadow status ended**: `cite-check` now gates every
  commit through `index_state.py --check` (blocking = dangling/overturned/conflicted citations only).
  Rollback = stop adapters, keep the ledger for diagnosis.

## Key file locations

- **The V2 output (start here — this is now the binding spec, not the v1 draft):**
  [`docs/design/vidya-pilot-spec.md`](../../docs/design/vidya-pilot-spec.md) ·
  [`docs/design/vidya-research-program.md`](../../docs/design/vidya-research-program.md) ·
  [`docs/design/vidya-architecture-appendix.md`](../../docs/design/vidya-architecture-appendix.md) (non-binding)
- Audit + adoption kit (all schemas/specs to copy): `research/deep-dives/vidya-belief-substrate-audit.md` §§4–5
- v1 draft (superseded source text for the V2 split): `tmp/vidya-epyc-governance-pilot-handoff.md`
- Intake entries with paste-ready extracts: `research/intake_index.yaml` intake-1031..1067
  (notably 1063 = byte-exact L1 checkpoint spec; 1062 = proof-standard definitions; 1064 =
  certificate field map; 1035 = judge-discipline rules)
- Existing machinery to ride: `handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md`,
  `repos/epyc-inference-research/scripts/kernel_rnd/autokernel/journal.py`, `dashboard/freshness.py`

## Completed Scope

Nothing was deleted: the siblings are the evidence record for every gate this program has already passed.

| Scope | Where | Contents |
|---|---|---|
| through 2026-08-10 | [`vidya-belief-substrate-program-completed-through-2026-08-10.md`](../completed/vidya-belief-substrate-program-completed-through-2026-08-10.md) | audit session, intake-index defects, V2 spec revision, P0 pilot corpus, P1–P5 pilot build, promotion track, R1–R5 research program |
| 2026-08-10 → 2026-09-27 | [same file, section *Completed 2026-08-10 → 2026-09-27*](../completed/vidya-belief-substrate-program-completed-through-2026-08-10.md) | SC19, SC1, SC2, SC2-C, SC3, SC4, SC4-BUG, SC5, SC5-BUG, SC5-MERGE, SC6-PRICE, SC6, SC6-REPS, SC33, SC34, SC35, SC36, SC44, SC8, SC8-DOC, SC9, SC10, SC11, SC53, SC13, SC12, SC12-FIND, SC12-RECORD, SC13-DEFECT, SC12-REGEX, SC12-FIX, SC12-GRADE, SC12-DATE, SC12-REMAIN, SC12-ENTRY, SC15, SC16, SC17, SC20, SC21, SC22, SC23, SC24, SC25, SC26, SC28, SC29, SC30, SC31, Decision queue (settled 2026-08-09), SC46, SC56, SC57, SC58, SC59, SC62, SC61, SC67, SC68, SC75, SC69, SC70, SC72, SC73, VB-PRB-T4, VB-REVIEW-F1, VB-EVCONF2, P5c promotion gate (PROMOTE 2026-08-26), SC87, VB-AK-CODEGEN, VB-EXL3-CPU-GFX90A, SSU-F6, SSU-F7, VB-AK-SEAT-a, VB-AK-SEAT-b1, VB-AK-SEAT-b1v, VB-RI-SCREEN-1, VB-DGM-1, VB-TDP-EXT |
| superseded history | [`vidya-belief-substrate-program-history-through-2026-09-27.md`](../archived/vidya-belief-substrate-program-history-through-2026-09-27.md) | the superseded 2026-08-26 state snapshot; the P1–P5 dependency notes |

## Task list

### Open work — start here

- [ ] **USAGE-PROV-1 write-side enrollment** — project prospective `epyc.request_call_usage.v1`
      begin/settled records from the configured `usage_provenance.jsonl` stream through the existing
      ClaimTuple contract. Verify self-hashes, request/call/parent and backend-record joins, process
      revision plus honestly timed asynchronous on-disk hashes/dirty state (pending remains unknown), and finalization/censoring.
      Preserve error category/hash without raw prompt/output/server payloads. Cache replay retains its
      original observation dependency and logical charge without new physical decoding or independent
      corroboration; estimates and incomplete usage cannot establish measured cost. Keep missing
      model/server/protocol warrant unknown. Verify bounded-log retention/custody and the planning-context
      canary before marking wired. Producer: orchestrator `src/llm_primitives/usage_log.py`; no new grader.
  - 2026-10-28 source checkpoint: orchestrator `c2650210ca1fe766c6ab62945ec9475ed6535c00` implements the prospective writer/accounting carrier and passed 359 offline tests. Mutable disk metadata alone cannot authorize metered replay; current-process native custody is required. The source compatibility document explicitly distinguishes OS append from fsync and pending source context from loaded-byte attestation. Source is integrated to orchestrator main `4c1fbd2bfc1341e6861802bd10a6524b5fc433ff` after owner review; no runtime deployment, native usage observation, adapter projection or planning-context canary is established by those tests, so this enrollment task remains open. See `progress/2026-10/2026-10-28-usage-provenance-recovery.md`. [no-belief: source/offline checkpoint]

- [ ] **VB-REFACTOR-CONFORMANCE** — Prospectively capture controlled behavioral-regression verdicts for [multi-repo refactoring](refactoring-multirepo-2026-10.md) through the existing native CI verifier/shared grade. Preserve the decided proposition, source/test/base commits, command, environment, original output, JUnit and native custody. Manual branch/source reviews remain supporting dependency findings, not runtime proof. Keep past diagnostic runs as ordinary evidence; no invented attestations, historical tuples, retrofit or new ladder. Source-table row filed on the refactoring review branch; canonical publication follows owner review.

For the current queue, use the open checkboxes below and the generated
[`master-handoff-index.md`](master-handoff-index.md) rollup. KV-quant: `VB-KVQ-V10-DICT` first (root adapter
must accept the producer's stats-dict medians; Codex coordination) — it blocks `VB-KVQ-V10-INGEST`, which also
waits on the first post-hook sweep sidecar. `VB-KVQ-V10-RECONSIDER` (AutoPilot correction review, synthetic
correction first) is dispatchable now.

- [x] **VB-S4-OMEGA-WIRE — wire the S4 Omega reader before a real A/B.** ✅ 2026-10-24. ROOT adapter,
      LOW source enrollment, CLI choice and end-to-end fixture coverage are on main (`16c0fa1ba2b45466a9324df0333987386d71e38b`): implementation
      `7ff9c7e49c725fdc4523f4f3683aec07c1436d0d`, replay-report fixture
      `9389682e8020470cb1ad85c30a047b051466da5f`.
      Producer published separately at orchestrator commit `be208213775a032aefde26a3c1df4ac4ca2d445e`.
      Granted ROOT validation passed 10 tests with no skips; the carrier audit found 199 tuples
      and 0 violations. Adapter output stays at Judged/Located; protocol and model/server identity
      remain unknown. No real A/B, exact output-cost claim, pooled delta or promotion claim was made.
- [ ] **VB-S4-OMEGA-FIRST-AB — ingest the first captured real S4 Omega A/B.** After the outer S4
      experiment's serving owner produces native capture(s) under the required calendar grant, ingest
      those artifacts only; do not launch a duplicate quality experiment or duplicate TD21 parser work.
      Preserve raw request/response, question/gold, frozen suite/prompt snapshots, and original/recovery
      custody. Project only native per-row observations with the existing shared grader; keep missing
      prompt usage unknown, retain explicit zero/false and partial/refused status, and exclude synthetic
      rows. No inferred pair result, exact cost from legacy token counts, protocol/model/server identity,
      or promotion claim.

### Source coverage — opened 2026-08-10 (operator question: what about wiki/logs/progress?)

- [ ] SC6-LIVE The hook takes effect for trials written **after autopilot next restarts** — the
      running process holds the pre-hook module. No restart was performed: reload ownership belongs
      to the session that owns the inference, at its own boundary. Until then
      `adapters/autopilot_journal.py` correctly reports 0 measured rows. Confirm non-zero after the
      next autopilot cycle
      **STATUS 2026-08-26: still unmeasured — the journal ends at trial 1505 (2026-08-09T19:29Z,
      "(killed)") and 0 of 1,390 rows carry a `measurement_tuple`; `autopilot_state.json` says
      `paused: true`. SHARPENED TRIGGER: confirm non-zero rows in the first autopilot cycle after
      the next restart — the restart is operator-gated (reload owner = the inference-owning
      session at its own boundary), not a calendar event**
- [ ] **SC32 — Wire future architect MMLU-Pro hardened controls prospectively.** The 2026-08-12
      A1/A3/A4 v9 panel carries native captures, exact claims, pinned source/manifest digests and
      an attestation, but no producer-authored `ClaimTuple` row. Add write-side rows plus a strict
      adapter before any successor run; the completed panel remains pre-hook and emits zero.
      **STATUS 2026-08-26 morning: the 2026-08-12 A1/A3/A4 v9 panel remains pre-hook and emits
      zero; a successor control is named, not hypothetical — `reboot-gated-inventory-and-staging.md`
      carries the missing A4 arm as "dispatchable today".
      EVENING: write side WIRED prospectively — `v7_quality_gate_runner.py` emits
      producer-authored `belief_measurements` at result-finalize when invoked with
      `--belief-category` (BASELINE anchor arm / CANDIDATE controls), forwarded by
      `mmlu_pro_hardened_control.py` through `architect_bench_gpu_arm.sh`; reps read from the
      run's own scored `n`, attestation sha256 over the manifest at collect time; 24/24 tests.
      The A4 `gpqa_diamond_cot` successor IS EXECUTING TODAY (`gpqa-cj1-2026-08-25/`, EVL-08 cut
      n=198→50) — WITHOUT the flag, so it is pre-hook and emits zero rows, always. NEW TRIGGER:
      any successor control run WITH `--belief-category` → first tuple → close**
- [ ] **SC41 — Wire AutoKernel GPU discovery baseline and candidate-only screens prospectively.**
      *(Filed 2026-08-13 as "SC37" by the AutoKernel wrap session — see
      `progress/2026-08/2026-08-13-root-autokernel-wrap.md` — and renumbered to SC41 on forward-port
      because SC37 was independently taken on 2026-08-15 by the eval-tower resolution-band row below,
      which the wiki and the 2026-08-15 progress entry already cite by that number. Content unchanged.)*
      The new `epyc.autokernel.gpu_screening_baseline.v2` and
      `epyc.autokernel.gpu_candidate_only_screen.v2` producers need a write-side ClaimTuple row plus a
      strict root reader before any successor screen. Bind exact source/build/binary/linkage/model,
      device and released-claim identities; scored invocation basis; sole-factor identity; KFD/VRAM
      residency; baseline/result hashes; run-level locator; and the nonpromotable/no-bank/no-readiness/
      no-release authority boundary. Delegate grading to `claim_tuple.grade()`; do not create a second
      ladder. The 2026-08-13 MMQ-MFMA s2 screen predates the hook and must emit zero rows rather than be
      retrofitted. Source-register row is in `scripts/vidya/adapters/README.md`; producer/read hook is
      being implemented prospectively.
      **STATUS 2026-08-26: unchanged since filing — the completed 2026-08-13 MMQ-MFMA s2 screen is
      the only screen, no successor has run, and the root adapter is still planned-not-built.
      SHARPENED TRIGGER: before any successor screen (AutoKernel V27 pre-launch; freeze-gated),
      implement the producer rows + strict reader with the full binding set (source/build/binary/
      linkage/model/device/claim, scored invocation basis, sole-factor identity, KFD/VRAM residency,
      nonpromotable/no-bank/no-readiness/no-release authority); s2 emits zero rows, always
      **EVENING 2026-08-26: write side WIRED and the first screen is post-hook.** The research
      producer (`scripts/benchmark/autokernel_gpu_discovery_beliefs.py`, v4) seals
      `belief_measurements` + `baseline_sha256`/`result_sha256` into every complete
      bank/result before its atomic write, and the V27 deployment's pinned execution closure
      carries exactly those bytes (producer sha256 matches research main). Root strict reader
      `autokernel_gpu_screening.py` re-derives every binding (producer id/path/sha, source
      commits, binary/linkage/model/device, the admitted sole-factor transitions, scored
      invocation basis 3/5/9, per-arm KFD/VRAM residency, self-hashes, authority boundary);
      24/24 tests; E2E: real V27-shaped output projects Witnessed/Attested. The V27 screen is
      RUNNING NOW (llama-bench in flight) — NEW TRIGGER: screen completes → adapter projects
      the first tuples → close**
- [ ] **VB-SC42-CPU-MATCHED18-WIRE** — capture the prospective Unlimited-OCR CPU default/canonical matched 18-page attempts, native response and stripped prediction identities, complete-denominator scorer outputs/errors, GT/image/model/mmproj/binary/source/runtime/argv and actual grant/window evidence; retain failed, interrupted and missing requests as UNKNOWN. Verify the canonical media-marker form against the pinned native test. Distinguish this private producer from the existing `odl_bench` writer until a matching attested writer/projector and real planning-context canary pass; use `ClaimTuple.grade()` only, with no new ladder, historical warrant, GPU or promotion claim.

- [ ] **SC42 — Wire the ODL-P2 model-gated arm (`odl_bench` Unlimited-OCR) on the write side,
      prospectively before its next run.** *(Filed as "SC37" on lane/mainD 2026-08-13 by `mainD`,
      the author of the run, at the run; renumbered on forward-port because SC37 was independently
      taken by the eval-tower resolution-band row below.)* The first demo
      (`.../odl-p2-unlimited-ocr-demo-20260813T221821Z/`) produced protocol-admissible evidence —
      `adapter.py run-model --engine unlimited_ocr`, n=18 GT pages, dated, durable
      `model_gated_row_set.json` + per-page response JSONs + the shared inference-call-window
      receipt (`inference_window.json`) — with median latency 5857 ms/page, decode ~392 t/s,
      text_block edit_dist 0.3624, table TEDS 0.0117, reading_order edit_dist 0.2165, plus the
      verified finding that the model emits coordinate-tagged layout dumps, not markdown. The
      adapter has no `ClaimTuple` write hook — add one (measurement class, run-level locator, one
      witness per run) before any successor run so the tuple records what this run actually
      captured; retrofitting on read is impossible (the `benchmarks/results` lesson).
      Source-table row is already in `scripts/vidya/adapters/README.md`.
      **STATUS 2026-08-26: the 2026-08-13 demo remains the only run; the ODL handoff names the
      successor — the canonical-profile matched A/B — and it is blocked only on the operator lifting
      the all-inference-stop order plus a new inference grant (also: the PIP-05 evidence correction
      to the demo record landed 2026-08-25). SHARPENED TRIGGER: wire the write hook (measurement
      class, run-level locator, one witness per run) before that canonical A/B executes; the demo
      stays immutable pre-hook evidence
      **EVENING 2026-08-26: blocker CORRECTED — the all-inference-stop is not in force.** The
      serving stack (5 llama-servers + `lightonocr_llama_server.py` :9001, up since 08-21 — a
      production OCR serving path, not the A/B) is live, and lease-based campaigns ran 08-25/26
      (inf11/inf40/inf42-g1). The canonical-profile matched A/B is therefore SCHEDULE-gated (a
      lease window), not operator-gated. NEW TRIGGER: run the canonical A/B with `odl_bench`
      under a lease window → first tuple → close**
- [ ] SC21 **The contention matrix became gradeable on 2026-08-12 — wire it while the producer is warm**
      (filed by `mainC`; the emitting change is orchestrator `77e5a214`, landed hours earlier). Before
      that commit the artifact carried a bare `verdict: allow/block` with no warrant, which is precisely
      the shape that cannot be graded. It now emits `decision_grade`, `decision_grade_blockers` and
      `host_health_warnings`, so a ClaimTuple can be projected honestly. **Carry the scope limit into the
      adapter, not just the docs**: `decision_grade` attests HOST STATE only — every pair is still
      `samples: 1`, so a projection that reads `decision_grade: true` as "this ratio is statistically
      solid" would manufacture confidence the run never had. The blockers list is the useful field: it
      names *why* a run is ungradeable, which is exactly what a refuted/conflicted disposition needs.
      **STATUS 2026-08-26: still warm, still unwired — the matrix emitted decision-grade artifacts as
      recently as 2026-08-24 (`op21-overlap-decisiongrade-20260824`), and no vidya adapter exists
      for it. SHARPENED TRIGGER: build the adapter now, not at the next run — carry the scope limit
      into the projection (`decision_grade` attests HOST STATE only; every pair is `samples: 1`) and
      make the blockers list the refuted/conflicted input; the producer's activity window is the
      trigger, and it is open today**
- [ ] SC20 **LoRA/SFT training runs need a write-side ClaimTuple hook — filed 2026-08-12 by `mainC`
      at the moment the producer became real, not afterwards.** `memento_sft.py` had never completed a
      run until 2026-08-12 (its `get_peft_model()` was commented out behind a TODO), so it emits
      measurements for the first time: s/sample, trainable-param count, per-quarter loss, and an
      adapter-integrity check (all tensors finite, `lora_B` off zero init). It is therefore in the ideal
      state to wire — **the producer is being actively modified right now**, which is exactly the window
      the register says not to miss. Retrofitting is impossible rather than merely expensive: a tuple
      invented on read claims warrant the run never captured, which is why `benchmarks/results` is
      permanently rejected at 0/200. Note the natural claim here is **not** "the model improved" — a
      16-step smoke supports no such thing — but the far more defensible "this configuration trains at
      X s/sample with an adapter that provably updated", which is what a promote/stop decision on the
      1.7B validation target will actually rest on.
      **STATUS 2026-08-26: the Stage-1 job ran 2026-08-12 (the filing day, pre-hook) and no successor
      has run since — S2 LoRA validation on the 1.7B target is the next producer event and is
      GPU-gated. SHARPENED TRIGGER: wire `memento_sft.py` to emit the tuple (s/sample, trainable
      params, per-quarter loss, adapter-integrity) before the S2 validation run — the claim shape
      stays "this configuration trains at X s/sample with an adapter that provably updated", never
      "the model improved"
      **EVENING 2026-08-26: write side WIRED — `memento_sft.py` emits
      `stage{N}_belief_measurements.json` at train-stage finalize (s/sample lower_better,
      trainable params, quarter losses, adapter-integrity: all tensors finite + `lora_B` off
      zero-init, fail-closed otherwise; protocol `epyc.memento_sft.lora_training.v1`);
      14/14 tests (research `da06b371`).
      2026-08-27: S2 IN FLIGHT — smallest real Stage-1 format-learning job** (Qwen3-0.6B,
      126 train samples, 1 epoch, seq 4096, GPU; launched 16:07Z, ~6-10 min). The belief hook
      fires at train-stage finalize → `stage1_belief_measurements.json` beside the run record
      → first SC20 tuple.
      **2026-08-27 20:10Z: FIRST TUPLE EMITTED AND INGESTED ✅.** The re-run (deterministic —
      identical Step-0 loss to the refused first run) completed 16 steps / 126 samples on CPU
      (18.8 s/sample) and the fixed hook emitted `stage1_belief_measurements.json`:
      integrity 168/168 lora_B nonzero, all tensors finite, quarters 1.485→1.337.
      Root reader `memento_lora.py` (strict: measurement_sha256 self-hash re-derives, canonical
      attestation over the run record re-derives, refusal artifacts project zero rows; 7 tests)
      projected the row; frames ingested; fold `Witnessed/Attested`. NOTE: the first run's
      refusal was a CHECK BUG (endswith vs substring on lora_B.default.weight), and its
      artifacts were deleted before re-emission — the re-run recovered the measurement
      deterministically. The 1.7B validation (the S2 gate proper) is IN FLIGHT: the HF repo is
      GATED (no token on the host; the HF download is dead) and the ModelScope mirror download
      is running into hf-home (~5 MB/s, weights expected complete 2026-08-27 ~21:30Z); the same
      smoke config launches on completion.
      **2026-08-27 21:40Z: 1.7B TUPLE INGESTED.** The smoke completed (16 steps / 126 samples,
      29.9 s/sample CPU, loss quarters 1.68→1.25, integrity 168/168 lora_B nonzero, all
      finite) and its row is in the ledger (Witnessed/Attested). KNOWN DEFECT, producer-fixed:
      the first two smokes (0.6B + 1.7B) collided on the stage-only `measurement_id`
      (`memento_sft_stage1_seconds_per_sample`), merging two measurements into one fold
      belief — the hook now mints run-unique ids (model + stage + UTC timestamp); the two
      already-ingested tuples remain merged under the old id (both Attested, so the fold
      verdict is unchanged either way). Row residual = format compliance (GGUF convert +
      masked-prompt structure test) + MATH-500 delta in the S2 table; no more training
      runs until those are measured.
      **2026-08-27 23:15Z: S2 GATE MEASURED.** Format compliance: FAIL at smoke scale —
      with the corrected serving stack (extended-vocab base; the original serving vocab
      cannot emit the memento tokens — they split into 6), the 126-sample smoke generates
      only `<think>` reasoning, zero block/summary tokens. MATH-500 delta: 0.440 → 0.420
      (n=50, within noise). Decision per the fork: CONTINUE — the pipeline is verified
      end-to-end; the fix is stage-1 training scale (few thousand samples), not a stop.
      All measurement tooling (math500 harness, extended base, lora convert) committed.
      **2026-08-27 23:40Z: SCALED RUN GPU-GATED + DEFERRED (operator).** CPU cost is 10-40 h
      @ seq 4096 (measured ~4.7 min/step); the operator decided the scaled run happens on
      the GPU. Prereqs when picked up: (1) ROCm torch build in the ml-training venv (the
      current torch is CUDA-only; the ROCm install was explicitly declined this session),
      (2) a GPU window, (3) the recommended first checkpoint: 1,000 samples @ seq 2048. If
      the format still fails there, the diagnosis shifts to the training objective (stage-2
      masking) before any larger investment. Row residual = the GPU-gated scaled run.**
- [ ] SC12 **Kernel promotion/certification and K35 paired kernel/speculation receipts need a
      write-side ClaimTuple hook.**
      The first bounded receipt is `artifacts/audit/v9-dspark-autokernel-base-20260810.json`; the v9
      promotion then produced K35 GPU/DSpark and DFlash production-certification summaries. The K35
      runner now also emits quant-specific paired receipts, first
      `data/deepseek-v4-flash/iq3-dspark-quick-20260811T063729Z/summary.json`. The artifacts are
      durable, but their producers still do not emit the full tuple at write time and must not be
      retrofitted on read. Before the next promotion or K35 paired run, add protocol id, scored
      reps/basis, date, durable attestation locator+digest, category, and metric direction to the
      K35, DFlash, qualification, and final-freeze write paths. Project into the existing
      `ClaimTuple`; `claim_tuple.grade()` remains the only grading rule. Only then price/build the
      adapter
      **STATUS 2026-08-26 morning: no successor run had emitted since filing — the v9 freeze held
      (no promotions) and the only K35 receipt (`iq3-dspark-quick-20260811T063729Z`) predated the
      hook; three empty `dspark-sidecar-match-20260825T*` dirs showed the producer exercised
      without producing artifacts.
      EVENING 2026-08-26: successor fired and the write side is now wired.** A K35-paired run
      (`dspark-sidecar-match-20260826T140422Z`) started today — attempt 1 aborted 13:57Z (path
      typo), attempt 2 in flight — and the runner (`k35_stack_context_matrix_runner.py`, research)
      now emits `belief_measurements` (one row per quant-specific paired receipt, house envelope,
      protocol `epyc.k35_stack_context_matrix.summary.v1`, attestation = sha256 over the summary
      at write time) plus a full-document `summary_sha256`; 33/33 tests. The IN-FLIGHT run predates
      the hook and emits zero rows, always. NEW TRIGGER: first COMPLETED post-hook K35 paired run
      closes this row**
- [ ] SC12-ARTIFACT **Model artifact acquisition/integrity receipts need a prospective write-side
      ClaimTuple hook.** The standardized DeepSeek-V4 DFlash acquisition established the source
      repository and pinned revision, expected/observed byte count, publisher/local SHA-256,
      selected-file scope, metadata summary, process exit and incomplete-file cleanup, but those
      facts were captured in session prose rather than a native receipt. Before the next model
      acquisition, emit one run-level record with those fields plus timestamp, protocol id,
      category, metric direction and durable attestation locator+digest. Project it into the
      existing `ClaimTuple`; `claim_tuple.grade()` remains the only grading rule. Do not retrofit
      this completed acquisition on read
      **STATUS 2026-08-26 morning: the DFlash2 27B GGUF for the np1 campaign
      (`models/Qwen3.8-27B-DFlash2-Q8_0.gguf`, ~2026-08-20) was acquired with no native receipt.
      EVENING: seven acquisitions since 08-11, none with a native receipt — the last,
      LFM2.5-2.6B-Q4_K_M (08-21), is the exact "next acquisition" the row names, missed again.
      The run-level record spec now lives with the acquisition runbook; the next acquisition
      emits it, or the miss becomes a tracked pattern, not an accident**
- [ ] SC7 Ingest autopilot trials into the ledger once SC6-LIVE confirms rows are landing. Deferred
      deliberately: appending 1,372 retro-graded claims now would record provenance the original
      runs never captured, and the corpus is worth ingesting only once it is born attested. Note
      `data/benchmark_artifact_inventory.json` is EMPTY (0 rows), which is its own finding
      **SHARPENED TRIGGER (2026-08-26): re-open this the day SC6-LIVE reports its first non-zero
      cycle — both rows ride the same restart, and SC6-LIVE is the only watchdog**
- [x] SC6-HAZARD Before any bulk ingest is ever reconsidered: support is counted by **source
      locator** ✅ 2026-08-26 — **premise answered; hazard preserved as vocabulary.** The bulk-ingest
      question was settled by SC6-PRICE (rejected on evidence, 0/200 full tuple), so the guard has
      no live referent; the hazard itself is canonical — it lives in the adapters register's locator
      warning and is cited as the trap by SC38, SC40 and SC43. If bulk ingest is ever reconsidered,
      the re-consideration re-files this guard at that moment (SC9 rule); a permanently-open box is
      not a decision

- [ ] SC37 **The eval-tower resolution band needs a write-side ClaimTuple hook — filed 2026-08-15
      from the intake-1128..1147 research cohort, BEFORE the producer exists.** `eval-tower-verification.md`
      EV-14a will measure a per-suite resolution band by rescoring ONE UNCHANGED config with
      `core_v2_calibrate.py --repeats` and deriving the band from the retained spread. That is a
      measurement, so under the belief-kernel rule the write side is filed now rather than after the
      first band lands. The producer already knows every element a tuple needs — suite id, K, the
      unchanged-config identity, the per-repeat scores, the instrument era, and which baseline the band
      was measured against — so nothing has to be invented on read, which is exactly the condition that
      made `benchmarks/results` unusable. **Carry the scope limit into the ADAPTER, not just the docs**:
      a band attests the RESOLUTION OF THE INSTRUMENT and says nothing about the quality of any config.
      A projection that reads a band as "this delta is statistically solid" is the same category error
      SC21 records for `decision_grade`, one level up. Two dependencies, both real: EV-14c must land
      first, because while `safety_gate.py` `update_tier()` writes baselines with `dict.update`
      (last-write-wins) a band can be measured against a silently-moved reference; and the tuple must
      record K explicitly, because the whole downstream value is that a claim can never assert a delta
      finer than its own suite's measured resolution. Adapters PROJECT into the existing `ClaimTuple`;
      `claim_tuple.grade()` remains the only grading rule — do not add a second ladder.
      **STATUS 2026-08-26: filed before the producer existed and the producer still does not exist —
      EV-14a has not run (eval-tower-verification.md, both EV-14a and its EV-14c prerequisite open).
      SHARPENED TRIGGER: EV-14c lands (baseline last-write-wins fix), then EV-14a runs
      `core_v2_calibrate.py --repeats` — wire the write side before that first band, and keep the
      scope limit (band = instrument resolution, never config quality) inside the adapter
      **EVENING 2026-08-26: EV-14c LANDED + write side built; EV-14a staged.** `safety_gate.py`
      now keeps per-tier baseline REVISIONS (bumped by every identity-changing `update_tier()`
      write, persisted through load/save), logs an explicit BASELINE MOVED line naming
      prior→new + invalidated pins, and `update_baseline()` REFUSES a promotion whose
      compare-to-write span saw the reference move (11 new orchestrator tests + 262 passing).
      Write side: `eval_tower_band.py` emits ONE self-hashed `.band.json` per suite (refuses a
      degraded repeat, K mismatch, <2 scored repeats, or a moved reference) and projects one
      ClaimTuple with the *INSTRUMENT RESOLUTION ONLY* scope limit enforced verbatim (17/17
      tests). EV-14a remains inference-gated and the host is mid-deployment — staged:
      `python3 scripts/autopilot/core_v2_calibrate.py --n 300 --repeats 3 --seed 4242
      --trial-id-base 900000` (+ `pin_tier` before repeat 0, `pin_moved` after,
      `build_band_artifact`). NEW TRIGGER: first real band → first tuple → close
      **ATTEMPTED 2026-08-28 (CPU-only session): repeat 1 of 3 ran clean on protocol
      (q=1.410 r=0.943 n=300, 4-wide, ~3.9h) but 17 infra-failed questions voided the band
      fail-closed — no `.band.json`, no tuple, run stopped. Corrected root cause: 10×
      physreason = missing images (zip extracted to /mnt/raid0/llm/tmp/physreason/, 0 missing
      now); 5× architect_general = GPU-lane generation escalations (not judge calls —
      LLM_JUDGE_ROLE override would not help); 2× transient. HELD until architect_general /
      worker_vision are realized again (operator: GPU occupied). Adapter and write side remain
      verified and staged; first band → first tuple trigger stands.****

- [ ] SC38 **Wire worker-pool completion reports on the write side — filed 2026-08-16 by the
      loop-owned-fleet session, WHILE `scripts/coordination/worker_runner.py` is still being
      authored** (`loop-owned-fleet-implementation.md` P2-10, before the P2-9 pilot runs). The runner
      writes `<runtime_root>/runs/<batch_id>/report.json` (`worker_report.v1`, default runtime root
      `/mnt/raid0/llm/worker-pool`) per batch, and `validate_report()` already REFUSES a batch that
      omits `subagents_spawned`, `tokens_used` or `denials` — so an unreported run and a clean run
      cannot render identically, which is the precondition a tuple needs. `subagents_spawned` is the
      pool tier's fan-out multiplier and closes the RTG-49/F-15 gap for that tier; `tokens_used` is
      the D1 ceiling's only input and the mandatory input to the Phase-3 go decision.
      **Why now rather than after the pilot:** retrofitting the read side is impossible — a tuple
      invented on read claims warrant the original run never captured, which is exactly why
      `benchmarks/results` is permanently rejected (4,562 files, no write-side hook, 0 of 200 sampled
      carrying a usable tuple).
      **Projection, not a ladder.** Protocol id = the native schema version (SC19's precedent);
      metric direction recorded, never inferred; `reps` = the rows that SCORED (`outcome ∈
      pass|fail`), never the rows dispatched, because `skipped` is attempted-not-scored (SC6-REPS);
      category `CANDIDATE` for pilot batches. The adapter PROJECTS into the existing `ClaimTuple` and
      `claim_tuple.grade()` decides — the `measurement` ladder already exists and
      `register_ladder()` refuses a second.
      **Locator: the BATCH, never the row.** P2-6 puts up to 3 rows in one invocation and both
      counters are batch-level, so a per-row key reads one fan-out number as three witnesses and
      tokens/row becomes a derived quotient masquerading as a measured value. Same class as the
      SC13 run-level trap and SC6-HAZARD.
      **Honest scope, and it must land in the ADAPTER not only the docs:** both counters are written
      by the WORKER into its own report file. Schema-required and type-validated is a genuine upgrade
      on RTG-49's prose self-report, but it is still self-reported; an independent count would come
      from the harness transcript / provider usage the runner already keeps a pointer to
      (`transcript_path`). Until that exists the projection must say *self-reported* rather than
      claim an independent witness.
      **Attestation:** the runtime root is OUTSIDE any git tree, so a path proves nothing on read
      (`feedback_verify_evidence_in_git_not_filesystem`). Write a sha256 over the report content at
      collect time or the claim honestly tops out at `Witnessed/Anchored`. Source-register row added
      in [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md).
      **STATUS 2026-08-26: the producer exists and ran — 8 pilot batches on 2026-08-16, all pre-hook
      `worker_report.v1` files — and the pool has been switched OFF by policy since (fleet gate:
      `worker_pool.enabled is false`), so no successor report exists to wire against. SHARPENED
      TRIGGER: wire the collect-time sha256 hook and the batch-level projection before the next
      batch after the pool is re-enabled (Phase-4 P4-1 gate check is the plan's next event); the
      pilot reports remain pre-hook evidence, never reconstructed**

- [ ] SC39 **Wire headless audit verdicts (P2-7) on the write side — filed 2026-08-16, BEFORE
      `scripts/coordination/headless_audit.py` exists.** The auditor consumes the pointer-only packet,
      re-derives the diff from git independently, runs one mutation probe and writes a typed verdict
      per completion: `accept | accept-with-followups | needs-rework | blocked-evidence`. Filing at
      design time is the whole point — the module is unwritten, so the write side costs one field
      today and is unrecoverable later.
      **Classify it deliberately, the SC21 call one level up: a single verdict is CATEGORICAL — no
      metric, no direction — and MUST NOT be forced through `ClaimTuple`.** Never invent a metric
      direction to push it through the carrier. What *is* an honest measurement is a RATE over a
      declared window: the verdict-mix share and, above all, the operator-vs-auditor disagreement
      rate, which this plan's own kill criterion reads at a 20% threshold over any 7-day window (and
      the pilot's overturn count over 3 spot-reviewed rows). Those are lower-is-better fractions whose
      scored denominator is the audits actually ADJUDICATED, not the audits emitted.
      **Projection only.** Rates project into the existing `ClaimTuple` with an explicit window,
      classifier/prompt version as protocol id, and the recorded direction; `claim_tuple.grade()`
      remains the sole grading rule and no second ladder is registered. Individual verdicts are
      retained natively and, if anything, classified the way SC30 classified rehearsal legs — never
      coerced into a measurement.
      **Locator: the audit window (or the batch, for a per-batch rate), never the verdict** — the
      same trap as the completion report it reviews.
      **Do not spend the independence property.** The audit packet is a pointer WHITELIST precisely
      so the review is not anchored on the defendant's statement of the case; a projection that folded
      worker-reported outcomes into the verdict rate would destroy the property being measured.
      Source-register row added in the adapters README.
      **STATUS 2026-08-26: the module is no longer unwritten — `headless_audit.py` exists and the
      P2-7 audit invocation is wired into the runner (`n.py audit --packet --emit`), but no verdict
      stream exists because the pool has been OFF by policy since the 2026-08-16 pilot. SHARPENED
      TRIGGER: project the RATES (verdict-mix share, operator-vs-auditor disagreement over its
      declared window), never a single verdict, at the first verdict emission after the pool
      re-enables — the categorical-never-coerced and independence-property constraints are already
      settled in the row**

- [ ] SC40 **Wire the loop-owned-fleet plan metrics on the write side BEFORE the first unattended
      night is scored** (filed 2026-08-16, P2-10). Four producers, all of which GATE a decision — the
      Phase-4 gate check and the plan's kill criteria — and all of which are computed nowhere today,
      which is the ideal moment: compute duty cycle on unattended nights (higher-better fraction,
      8–9% baseline → >40%), operator delivery interventions (lower-better count, ~daily → 0),
      coordination self-repair share (lower-better fraction, ~50% → <10%, computed by **commit-path
      classification over `scripts/coordination/`**, which D9 requires to be measured and *never*
      self-reported), and alarm fidelity (drill alarms delivered / drill alarms fired, plus false
      alarms on well-run nights). Anything that gates a grade or a go/no-go is exactly what the
      register says needs a tuple — the SC13 test.
      **Projection, not a ladder:** each metric needs a protocol id naming the classifier and its
      version, an explicit window, recorded direction, scored basis, and a durable attested artifact;
      the adapter projects into the existing `ClaimTuple` and `claim_tuple.grade()` decides.
      **Locator: the WINDOW (a night, a 7-day span), never the sample.** A 60s duty-cycle poller keyed
      per sample would read one night as 1,440 independent witnesses — SC6-HAZARD in its purest form.
      **Two scope limits that belong in the adapter, not just the docs:** duty cycle attests HARDWARE
      OCCUPANCY and says nothing about useful work (reading it as productivity is the SC21 category
      error); and the self-repair share is a ratio over commits classified by path, so it moves
      whenever the path taxonomy moves — pin the classifier version inside the tuple or two windows
      are not comparable. **Price it first** per the P2 discipline before building any adapter: the
      corpus is one row per night/window, so the honest answer may be a hand-written record rather
      than an adapter — in which case record that verdict here instead of leaving the row open.
      **STATUS 2026-08-26: the producers are partially real — `fleet_metrics.py` computed the derived
      set (self-repair share 11.1% via commit-path classification) on 2026-08-16 — but the Phase-4
      gate check (P4-1) has not started and the pool is OFF by policy. SHARPENED TRIGGER: the first
      scored unattended night of P4-1 is the event; before it, each metric needs its protocol id
      (classifier+version), window, direction and durable artifact, with the window locator and the
      two scope limits in the adapter — a 60s poller still reads one night as 1,440 witnesses**

- [ ] SC43 **Wire the verifier/selector measurement on the write side BEFORE the first RM-11 run is
      scored** (filed 2026-08-19 via research intake, operator-approved Stage-3 plan
      `cuddly-sauteeing-cherny`). RM-11a/RM-11b in
      [`reviewer-model-ablations.md`](reviewer-model-ablations.md) and RC-10 in
      [`reviewer-calibration-accounting.md`](reviewer-calibration-accounting.md) will produce verifier
      gain, recovery rate, within-prompt correlation, tie rate and reviewer solve-accuracy — a
      measurement class this substrate does not currently carry. The nearest existing row is the
      eval-tower per-suite resolution band (SC37), which measures *instrument resolution*, not verifier
      quality; this is adjacent, not the same source.
      **Locator — this is the hazard that decides the row.** Key on the **run / selection episode**,
      never on the individual score. A verification pass is C criteria × K repeats × N candidates, so a
      single run emits C·K·N scores; keyed per-score, support would be counted C·K·N times and the run
      would manufacture its own corroboration. That is exactly SC6-HAZARD (support counted by source
      locator) in a new costume.
      **Emit the raw K-vector, not just the scalar.** Per call record the full probability vector over
      the K score tokens, `retained_mass`, `K`, the read-out method and the aggregation timing
      (pre- vs post-order-aggregation). The scalar alone cannot be reconstructed into anything richer
      later — `benchmarks/results` (4,562 files, 0 of 200 sampled carrying a usable claim tuple) is the
      standing proof that the read side cannot be retrofitted.
      **Authority boundary.** The adapter *projects* into a `ClaimTuple`; `claim_tuple.grade()` decides.
      Do not author a second grading ladder — the registry refuses one. Class is `measurement`; carry
      `protocol_id`, `reps` + `reps_basis`, `date`, `attestation_*`, `category` and `metric_direction`.
      Note that until RC-6a merges these are **observations** and cannot gate a decision, so the tuple
      must not be graded as if they could.
      **Price it first** per the P2 discipline: if RM-11 turns out to be a one-shot pair of runs rather
      than a recurring producer, the honest answer may be a hand-written record instead of an adapter —
      in which case record that verdict here rather than leaving the row open. Add the matching source
      row to [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md) either way.
      **STATUS 2026-08-26: still filed-before-producer — RM-11a/RM-11b have not run (row open) and
      their gating prerequisite RC-6a (operator PR on MEASUREMENT.md) is open, so every reviewer
      number remains an observation. SHARPENED TRIGGER: RC-6a merges → first RM-11a run; before it,
      the producers must emit the raw K-vector, `retained_mass`, K, read-out method and aggregation
      timing, keyed on the run/episode never the score; until RC-6a, the tuple must not be graded as
      decision-gating**

### Consumption — opened 2026-08-10 (operator question: what consumes these beliefs?)

Audit finding that opened this section: **nothing outside `scripts/vidya/` read the fold.** A grep
across `scripts/`, `repos/epyc-orchestrator/scripts/` and `.claude/` returned zero references, and
the only projection on disk was a 2026-08-09 demo. The engine was complete and had no drivetrain.

- [x] SC14-A **Planner read-side seam.** AutoPilot's
      planner has independently reinvented much of this kernel: a mandatory falsifier, an append-only
      resolution ledger (confirmed/refuted/inconclusive), and `evidence_trial_ids: []` refused on a
      prior because *"being the operator's idea is not new evidence"* (`operator_hypotheses.py`).
      The stale file-ownership marker was cleared after confirming AutoPilot was stopped. The inbound
      operator-hypothesis channel is now wired into every planner turn and records resolutions only
      after the cited trial is durable. `scripts/vidya/autopilot_settled.py` folds AutoPilot
      supersessions, grades the cited measurement tuple with Vidya's canonical ladder, fails explicit
      on ambiguous recycled trial ids, and renders sealed/provisional/review-required ground through
      `vidya_planner_bridge.py`. This is advisory for proposal selection and never gates generation
      ✅ 2026-08-10
- [ ] SC14-B **Promotion gate and shared resolution frames.** Gate only the CANDIDATE →
      BASELINE/OPTIMUM transition with `gate.evaluate`; append resolution/evidence links so AutoKernel
      sees the same negative, and use `impact_of_retracting` to reopen downstream promotions. Do not
      activate until the pre-promotion journal ordering supplies a durable current-trial attestation
      **STATUS 2026-08-26: not activated — no promotion has occurred since filing (v9 freeze) and the
      pre-promotion journal ordering still lacks the durable current-trial attestation (confirmed
      absent in the orchestrator today). SHARPENED TRIGGER: build the attestation into the journal
      ordering first, then activate the gate at the first promotion event after the freeze lift
      (AutoKernel V27 is candidate-only — instrument/target-equality receipts, no promotion)**
- [x] **SC55 — wire the INF-70 per-node / per-thread graph profiler as a measurement source, write side ✅ 2026-10-29 (audit: SC55-WRITE/READ accepted with native43/48 controls: commit bf7901fa5 (2026-10-08) and docs/reference/ni08-non-inference-continuation.md:416,558; source row in adapters/README.md; live capture owner-gated (no first-tup...) [no-belief: audit-reconciliation]
      FIRST.** Filed 2026-09-05 by INF-70 as its arms began producing them. This instrument
      (`GGML_CPU_PROF` + SYNC-1's aggregate thread extension: `wall_max_us`, `wall_max_ev`, `spikes`,
      `thr_max_us/thr_mean_us/thr_min_us`, `NNODES_EQ/MIN/MAX` graph-shape filters, `PATHROW` with
      `calls_per_eval`, `bytes_per_eval`, `GBs_on_compute/GBs_on_wall`) now
      produces the campaign's primary evidence and has already overturned four published figures.
      **Project, not grade.** Caveats that MUST ride in every tuple, each one a measured way these numbers
      have already been misread: (a) **thread-0 vs mean-thread** — a dead-time figure from thread 0
      understates coordination by ~half (57.6 vs 46.9 ms), so the measuring thread must be recorded;
      (b) **graph identity** — plain and MTP configs differ by 3.1× on barrier cost, so `nnodes` / graph shape
      is part of the key, not metadata; (c) **eval-count semantics** — empty catch-up evals (`logits=0`,
      `dst ne[1]=0`) are charged full weight bytes unless excluded, which is what forced one derived rate;
      (d) **dispersion** — a per-node mean over N evals with no max/spike count can hide a discrete host stall
      (4 nodes, 2.39 ms/token, measured), so a tuple without dispersion is an upper bound, not a value;
      (e) **binary attestation** by `.so` hash AND `strings` proof of the knobs, since every shared build dir
      in the tree was found stale; (f) **`GGML_IQK` state**, which is load-bearing for cache-residency rates.
      Source-table row to be added to `scripts/vidya/adapters/README.md` alongside SC54's.

- [ ] **SC54 — wire the qwen4exp `llama-perplexity` / KLD quality gate as a measurement source, write side
      FIRST.** Filed 2026-09-04 by INF-70 the moment the gate was restored (C9: it returned `nan` on this model
      until a rebuild fixed it). This is the ONLY PPL/KL instrument for qwen4exp, so every quant-quality decision
      on the model routes through it. B7's PLE-Q8_0 A/B was the first consumer and closed on 2026-09-04;
      its pre-hook records remain historical and cannot become source-authored tuples. **Project, not grade.** Four caveats are mandatory in every tuple and are the whole reason to wire the write side now:
      `GGML_IQK` state (kernel-path offsets must stay scoped to the captured binary/corpus/window), determinism (the ± is corpus
      sampling, not run noise — two binaries reproduced to every digit, so overlapping bars are NOT agreement),
      Ny regime (perplexity runs Ny>=32, serving runs Ny=1 — a PPL observation says nothing about the serving
      path), and BINARY attestation by `.so` hash + mtime rather than commit alone, because C9 was a stale
      artifact whose library predated its own fix. Source-table row added to `scripts/vidya/adapters/README.md`.


- [x] **SC54-WRITE — implement prospective immutable PPL/PPL-anchor/KLD capture before new measurements.** MAIN enrollment 2026-10-08. Capture source-authored metric labels/unit/direction/category/protocol availability before the original child invocation; retain exact argv, run/pair/arm, model/corpus/window, binary and contemporaneous loaded-library identities, compiled-knob bytes and effective runtime IQK state. Preserve original native logs and seal receipts without overwriting originals; keep bounded first/latest observations, exact poll counts and sticky identity-change/error evidence. Source controls use a model-free synthetic child on the existing off-host carrier. Historical B7/C9 outputs are never backfilled; real quality runs remain inference gated and the parent stays open.

- [x] **SC54-READ — validate the strict quality reader and normal ROOT ingestion after source capture.** MAIN enrollment 2026-10-08. Verify exact immutable output, source identities, original native metric grammar/counts/window and pre-run declaration; KLD must bind its matching prospective PPL-anchor receipt. Read the exact pinned reader bytes through one no-follow FD; use ordinary `qwen4exp-quality-measurement` Source/CLI dispatch and the existing measurement ClaimTuple ladder. Missing, ambiguous, changed or malformed evidence refuses projection. Whole synthetic controls must retain original JUnit identities and receipt/readset custody; no new grading rule or retrospective provenance.

- [x] **VB-INGEST-CONTRACT-SYNC — synchronize existing Source registrations, CLI choices and named fixture coverage.** MAIN discovery 2026-10-08: current ROOT79ac has45 Source names, but `odl-unlimited-ocr-run` is absent from the CLI literal choices; graph-profiler and ODL lack their named exemptions in the whole ingestion fixture coverage assertion. Add the existing ODL choice and references to their already accepted dedicated source controls, then validate the unchanged whole ingestion module alongside SC54. Preserve every source entry and all existing assertions; no new source class, measurement ladder, historical backfill or live process change.

- [ ] SC18 **Wire the `test-backend-ops` property layer as a measurement source — write side FIRST**
      (filed 2026-08-10 per CLAUDE.md's belief-kernel rule, at the layer's *design* time rather than
      after it ships). The property layer specified as `RVP-C2-2` in
      [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md) **produces measurements**:
      a per-op, per-backend, per-shape property residual. Two things make it a good source and both
      are cheap only right now — `RVP-C2-1` adds a deterministic `suite_seed`, which is what makes a
      residual re-derivable rather than an anecdote; and the layer is reference-free, so its residual
      is a claim about the candidate alone rather than about a candidate/reference pair. Add the
      adapter row (already recorded in [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md))
      and the `ClaimTuple` projection. **Do not write a new grading rule** — the adapter projects into
      a `ClaimTuple` and `claim_tuple.grade()` decides; the `measurement` ladder already exists and the
      registry refuses a second. This is the case `benchmarks/results` is the standing proof of: 4,562
      files with no write-side hook can never gate a decision, and no read-side pass can repair that.
      **2026-08-11 static implementation:** research commit `70766412` parses `AK_PROP_V1`, re-derives
      its verdict, refuses suite-seed mismatches and preserves each residual as a structured
      `evaluation_event` gate measurement. Root `autokernel_property.py` projects only those written
      rows into the single measurement ladder and explicitly yields nothing for older events. This
      row remains open until the experimental `test-backend-ops` producer is committed and its first
      real event proves the write path.
      **STATUS 2026-08-26: unchanged — research `70766412` (parsing `AK_PROP_V1`, suite-seed refusal)
      remains the static read path; the experimental `test-backend-ops` producer itself has never
      been committed (RVP-C2-2 still open) and no real event exists to prove the write path.
      SHARPENED TRIGGER: commit the RVP-C2-2 property layer to `llama.cpp-experimental`, then the
      first real event closes this row — both events, not just the adapter**
  - [ ] extend write-side wiring to the prospective GPU pool v1 records (epyc.model_free_backend_correctness.v1, ni-gpu-pool-*-20261026-v1): strict future projection preserves native candidate-local reference provenance and the exact artifact/source UNKNOWN limits; no historical backfill; no new grading rule (filed ws58 2026-10-26)
  - [x] GPU-pool v1 matmul family COMPLETE (`ni-gpu-pool-matmul-20261026-v1`, build c463f601b HIP): MUL_MAT 201/201 + MUL_MAT_ID 370/370 = 571/571 native CPU-reference comparisons PASS, 0 unsupported, 0 failed, NMSE tolerance 5e-4 met (exact residuals / max NMSE NOT recorded); residency proven DURING the run (KFD, positive VRAM, pinned HIP maps, task masks 184-191). Caveats: c463 source dirty state UNKNOWN; shim source receipt mismatches its recreation; no clean-C5/release/production/performance claim. Artifact-specific correctness only: does NOT close SC18, the `AK_PROP_V1` property layer or the parent GPU programme. Evidence: research `data/gpu-pool/matmul-20261026/` (origin/main 9cf3c860a). [no-belief: adapter pending for epyc.model_free_backend_correctness.v1] (filed ws58 2026-10-26)
  - [x] GPU-pool v3 attention COMPLETE (`ni-gpu-sampler-attention-20261026-v3`, build c463f601b HIP, supersedes v1): ROPE 328 + SOFT_MAX 207 + FLASH_ATTN_EXT 528 = 1063/1063 native CPU-reference comparisons PASS, 0 unsupported, 0 failed, 3 runs rc0 (residuals NOT recorded); residency proven DURING the run: 1277 of 1331 samples qualified on masks 184-191, 7 vanished-TID events excluded. Caveats: c463f601b source dirty state UNKNOWN; shim source receipt mismatches its recreation; no clean-C5/release/production/performance claim. Artifact-specific correctness only: does NOT close SC18, the `AK_PROP_V1` property layer or the parent GPU programme. Evidence: research `data/gpu-pool/attention-20261026/` (origin/main ceb08a491). [no-belief: adapter pending for epyc.model_free_backend_correctness.v1] (filed ws58 2026-10-26)
  - [x] GPU-pool v3 elementwise COMPLETE (`ni-gpu-sampler-elementwise-20261026-v3`, build c463f601b HIP, supersedes v1): 3360 observed = 2816 supported PASS + 544 explicit UNSUPPORTED (NORM 320, SUM 32, SUM_ROWS 192), 0 failed, 224 rc0 runs (7 ops x 32 seeds 2026102600..2631); it is NOT 3360 PASS. Residency proven DURING the runs: 5502 of 9571 samples qualified on masks 184-191. Caveats: c463f601b source dirty state UNKNOWN; shim source receipt mismatches its recreation; no clean-C5/release/production/performance claim. Artifact-specific correctness only: does NOT close SC18, the `AK_PROP_V1` property layer or the parent GPU programme. Evidence: research `data/gpu-pool/elementwise-20261026/` (origin/main ceb08a491). [no-belief: adapter pending for epyc.model_free_backend_correctness.v1] (filed ws58 2026-10-26)
  - [ ] elementwise UNSUPPORTED follow-up: champion owner compares the 544 UNSUPPORTED cases (NORM 320, SUM 32, SUM_ROWS 192; old-artifact c463f601b results, NOT proof of a missing kernel in current C5) against the current C5 build and records whether each op/shape is supported there (`data/gpu-pool/elementwise-20261026/`, RAW-CASE-COUNTS.tsv) (filed ws58 2026-10-26)
- [x] SC27 **Wire AutoKernel live-control and governed replay receipts on the write side before the
      next run.** ✅ 2026-08-12 — research `730adb1d` adds prospective producer-written belief rows
      to live controls and the async-prefetch replay; root `2a4e170a` adds the
      `autokernel_governed_receipt.py` projection and source-register entry. Protocol, direction,
      scored-block basis, source/binary/model/claim/producer identities, native verdict, and immutable
      evidence digests are independently re-derived before the shared measurement ladder grades the
      tuple. Focused producer tests pass 23/23 and adapter tests 24/24. The 2026-08-12 smoke, controls,
      and GPU replay predate the hook and remain deliberately unprojected; only future receipts may
      enter this source.
  - [ ] **VB-AK-GPU-CONTROLS — extend the existing governed-control source before its first direct GPU replay.**
    Producer: research `loop/direct_gpu_control.py:run_or_reopen`; retain `direct-gpu-control`,
    `direct-gpu-bench-launch` and `direct-gpu-t0` originals. Capture producer-authored native
    belief rows at write time for completed measurements and explicit failed-setup findings;
    preserve exact frame/model/build/loader/claim identities, raw repetitions/process-pair basis,
    actual T0–T2 outcomes and the fixed engineering tolerance. Extend the existing
    `autokernel_governed_receipt.py` source class/ladder, not a duplicate adapter or grading rule.
    Independent recall remains observation-only; never invent a tuple on read, qualify a candidate
    from a control result, or backfill the original September 7 evidence.
- [ ] **SC51 — Wire portfolio-v2 autonomous GPU-source screens on the write side before their first
      real run.** *(Renumbered from "SC32" on 2026-08-26 — the MMLU-Pro row filed 2026-08-12 holds
      SC32 seniority; the adapters register reference follows.)* Research `2153ccac` makes the source-discovery producer launchable with exact
      portfolio/manifest/series identity, balanced S1/S2 order, raw native samples, model/runtime/
      source evidence, borrowed GPU-claim phases, residency proof and nonpromotion authority. It
      still emits no producer-authored `belief_measurements`. Add prospective rows for whole-model
      effect and exact-family attribution, then implement a strict adapter that independently
      re-derives the paired samples and every identity before calling the existing measurement
      ladder. Do not back-fill any pre-hook receipt.
- [ ] **SC52 — wire the INF-42 G1 S-NIAH-2 exact-match probe on the write side before any successor
      run.** Add a producer-written, self-hashed belief-measurement vector to
      `g1_amnesia_probe.py` at per-question persistence/finalization, then a strict adapter that
      projects only post-hook rows into the existing measurement `ClaimTuple` ladder. Emit separate
      per-length/per-depth accuracy claims and paired 4K→long-context drop/CI claims; bind the full
      model/kernel/server/request/CPU-placement/KV-control identity, count only scored questions as
      reps, state metric direction explicitly, and use one run-level source locator/support key so
      question files cannot manufacture corroboration. Producer categories are q8 `BASELINE` and
      f16 diagnostic-control `CANDIDATE`; the adapter must not infer them. Refuse malformed, partial,
      mixed-placement, unhashed, and pre-hook records; do not back-fill the 2026-08-25/27 in-flight
      corpus. Test unique real-corpus identity, scored-vs-attempted reps, q8↔f16/4K control binding,
      direction, tamper refusal, pre-hook refusal, and absence of private grading logic. The adapter
      PROJECTS; `claim_tuple.grade()` decides.

- [ ] **VB-COPYSPEC — adapter for copy-spec results, and re-grade the 2026-07-30 ngram retraction claim's scope.** The retraction `intake-1153#record` measured non-copy prompts with crippled defaults; it must not gate copy-heavy decisions. Wire a producer-written `belief_measurements` vector at copy-spec eval completion (`phase1` and `phase2`), capturing acceptance rate, mean draft length, and throughput per arm (P / ngram-mod / ngram-only / P2) and per implementation (CPU frontdoor, CPU worker, GPU 27B if available). Create a strict adapter that projects only post-hook rows into the existing speculative-decoding `ClaimTuple` ladder, binding model/device/server/request identity, prompt composition (% copied), all-arm run-level locator, and authority boundary (candidate-only, no promotion until operator review). Done when the adapter passes 20 tests and the first copy-spec arm emits a non-zero tuple.
  - *(2026-10-06, workspace-ec)* First results now exist: P1 and width sweep (`artifacts/copyspec-20261006/p1-summary.md`, `artifacts/copyspec-20261006/width-summary.md`); the adapter should ingest both, including the ngram-only 32/85 divergence as a flagged arm.

- [ ] **VB-YARN-KSHIFT-AB — adapter rows for the YaRN mscale A/B (N/Y/YM identity + MTP acceptance) and the K-shift H1-H3 / Jet-Long T1-T3 test results.** Owner: workspace-ec. (filed 2026-10-06) Source table row in `scripts/vidya/adapters/README.md`; evidence under `artifacts/yarn-ctx-20261006/`. Done when each arm emits a tuple with model/device/build-sha identity, and the CTX-1 FAIL verdict grades via `claim_tuple.grade()` (no new grading rule).

- [ ] **VB-INF70-ARMS — adapter for the INF-70 serving-harness ARM records** (filed 2026-09-07 by
      HARNESS-1; distinct producer from the already-wired `inf70_roofline_ledger.py`). Each arm emits a
      token-weighted rate with a `pred_n>=16` floor, per-node placement, build id, artifact SHA,
      coherence classified by REASON, and — since 2026-09-07 — a per-arm **CONTENTION verdict**
      (`foreign_cpu_max`, `foreign_cpu_mean`, DIRECT vs SMT-SIBLING).
      **The contention verdict is the write-side hook that matters, and it is unrecoverable after the
      fact**: it decides whether an arm can support a claim at all. The measured argument is this
      campaign's own — pair p95 moved **19.89% → 6.25%** purely by dropping one contended arm, and that
      was only possible because the sampler recorded contention *during* the arm, not before it (a
      `loadavg` pre-gate provably cannot: one arm passed at load 11.61 and then ran through 23.9 → 32.0
      → 55.7).
      **Pre-2026-09-07 arms are PRE-HOOK and are worse than absent**: the sampler compared
      `Cpus_allowed_list` literally against `0-95`, so work pinned to `184-191` — the SMT siblings of
      bench cores 88-95 — was labelled `disjoint-from-0-95`. Their labels are **WRONG, not missing**.
      They emit zero rows and must never be reconstructed on read (the DF2-4 precedent).
      **Locator/support key = the ARM, never the per-prompt row.** 20 per-prompt wins inside one
      pairing are not 20 independent witnesses — a quiet moment lifts all 20 (SC6-HAZARD class).
      The adapter PROJECTS into `ClaimTuple`; **do not write a new grading rule** —
      `claim_tuple.grade()` decides (`docs/design/vidya-pilot-spec.md` §4.7).
      Source-table row added to `scripts/vidya/adapters/README.md` the same day.

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **VB-LB1 — Wire the write side before first run: add source-table rows (diagnostic, aggregate-only) for the dev-harness mining reports, the structured-output repair and finish_reason counters, the opencode prefix/gap baseline and the interrupt and violation series (intake-2387, intake-2388, intake-2389, intake-2429).** ✅ 2026-10-22
  - Four rows added to `scripts/vidya/adapters/README.md` (dev-harness mining reports, UFH14-LB2 repair/finish_reason
    counters, UFH14-LB8 opencode prefix/gap baseline, DHM-1/DHM-3 interrupt + violation series), all diagnostic and
    aggregate-only, carrier = `dev-harness-aggregate.v1` via `dh_privacy.publish_aggregate`.
  - [ ] **VB-LB1.1 — Adapter projecting `dev-harness-aggregate.v1` documents into ClaimTuples** (diagnostic class,
    existing ladder via `claim_tuple.grade()`; no new grading rule); first input = the first DHM report.

## Cross-cutting concerns

- Any new freshness state must name its mapping onto `dashboard/freshness.py` classes.
- Any measurement claim consumed by the pilot cites protocol + era per MEASUREMENT.md; the pilot
  never re-grades measurement evidence.
- The P2 adapter changes the research-intake skill's write path — coordinate with any parallel
  intake session; never edit the skill mid-run.
- Judgment frames (any LLM verdict entering the ledger) must satisfy the V2.7 keying rules from
  day one — retrofitting replay keys is not possible.
- **A field used to discriminate KIND must BE an explicit kind, never a present/absent test.**
  Raised 2026-08-11 by `mainA` from four absence-inferred fields found in one night — and the
  generalisable point is not carelessness: **two of the four were introduced by the person fixing
  that exact class, hours apart.** Presence/absence is the cheapest discriminator available at
  design time, and its whole cost lands on whoever reads the store months later, who cannot tell
  *"this kind has no value"* from *"nobody wrote one"* from *"the writer predates the field"*.
  Same asymmetry as the write-side rule above: cheap and permanent to state now, impossible to
  retrofit — a reader cannot recover a distinction the writer never recorded.
  Three independent instances the same day show it is not confined to manifests: `mainB` read merge
  stage `:3` after a `git add` (which collapses stages 1/2/3, so `:3` returned EMPTY and empty made
  every comparison pass); `mainD`'s `backfill-receipts --check` reported "index is current" while
  covering only bus-known gates; the `auditor`'s receipt index asserted `ratified` over files that
  were untracked. **Each was true about a smaller set than it appeared to speak for** — the read-side
  face of the same defect.

## Reporting

Standard checkbox discipline (`- [x] … ✅ YYYY-MM-DD`; mid-flight discoveries get their own task
lines). Maintain the master-index and research-evaluation-index rows; on completion, extract
findings to docs, move to `completed/`, delete the master-index row.

- [x] ~~**SC48 — wire the MI210 power-sensor probe suite into the belief kernel on the write side**~~ (closed 2026-10-29 audit: OBSOLETE → Priced-and-declined, verdict applied 2026-09-07 (box text) and listed under closed-with-verdicts at progress/2026-08/2026-08-26.md:64; commits bf920b468, 9787b1eda.)
      (filed 2026-08-21 by the session that produced it, at first measurement per the immediate-wiring
      rule). `scripts/benchmark/power_sensor_probe/` (research @ `df40658a`) emits per-run JSON
      (`analysis*.json`): idle/plateau watts, averaged-field t_d/t_r/t_f, derived-power response, FFT
      peak/floor per commanded frequency, sampler cadence. Two runs exist with persistence. These are
      OBSERVATIONS (no protocol id, gate nothing) — the adapter must carry that grade, PROJECT into a
      `ClaimTuple` (metric_direction varies per field: watts lower-is-better only for idle; response
      times lower-better; peak_over_floor higher-better) and let `claim_tuple.grade()` decide; it must
      NOT write a new grading rule. Every tuple must carry the API-scaling caveat (raw counter x 15.3)
      and the load-generator identity (1024^2 fp16 mm, sync-per-op).
      **CLOSED 2026-08-26 (inline verdict applied 2026-09-07) — priced-and-declined.** The decision is
      recorded in the program summary above (:78-79) and `progress/2026-08/2026-08-26.md` §Track E; this
      row was never updated with its inline verdict, which is why it kept rendering open. The corpus is
      two persistent observations — the SC9 pay-line judgment applies. Re-file per the SC9 rule at the
      first successor power-probe campaign with a larger corpus.
- [x] **SC47 — evaluate the FlashInfer Trace schema as the carrier shape for kernel-candidate records.** ✅ 2026-10-29 (audit: Evaluation verdict recorded (decline as carrier, adopt as corroboration): progress/2026-08/2026-08-26.md:64-66 and commit 9787b1eda; box text itself says verdict never ticked.) [no-belief: audit-reconciliation]
      Filed 2026-08-21 from `intake-1245#record` (FlashInfer-Bench, arXiv:2601.00227v1, Apache-2.0, repo @
      `40e6ca78`). **It is a write-side claim-tuple carrier in all but name**: an immutable
      `Definition x Solution x Workload x Evaluation` record with a declared PyTorch reference function, a
      hardware-parameterised `target_hardware` field on the Solution, an environment snapshot, a correctness
      verdict and a performance summary — i.e. exactly the shape `benchmarks/results` failed to have, which
      is why 0 of 200 sampled files there carry a usable claim tuple. Two things to take and one caution.
      **TAKE (1):** the record shape, as a candidate for our own kernel-candidate carrier. **TAKE (2):** its
      per-operation-class **evaluator registry** (`default` / `lowbit` / `sampling` / `dsa_sparse_attention`
      / `dsa_topk_indexer`) is structurally identical to our adapter contract — one ladder per source class,
      registered, never re-invented per call site — which is **external corroboration that the registry
      design is right**, and worth recording as such. **CAUTION:** `target_hardware` is DECLARATIVE. Nothing
      in the 423-path tree implements a non-CUDA device backend, so declaring `gfx90a` would not by itself
      make anything run, and every measurement in the published corpus is a B200 number. As always the
      adapter must **PROJECT into a `ClaimTuple` and let `claim_tuple.grade()` decide — it must NOT write a
      new grading rule.** Read `flashinfer_bench/bench/evaluators/{lowbit,default}.py` at the pinned SHA for
      the actual tolerance constants before adopting anything (also tracked as RVP-C6-23).
      **CLOSED 2026-08-26 (inline verdict applied 2026-09-07) — declined as a carrier, adopted as
      corroboration.** The decision is recorded in the program summary above (:78-79) and
      `progress/2026-08/2026-08-26.md` §Track E; this row was never updated with its inline verdict. The
      two TAKEs above stand as the record — the record-shape comparison for a kernel-candidate carrier
      and the evaluator-registry corroboration of the adapter contract; the tolerance-constant read stays
      tracked as RVP-C6-23.
- [ ] **SC45 — wire ParEval runs into the belief kernel BEFORE the first run, not after.** Filed
      2026-08-21 by the `/research-intake` Stage-4 pass that ingested it (`intake-1225`, dive-verified,
      MIT, HPDC'24, credibility 6/6 — the highest of that cohort). ParEval is a candidate C5 secondary
      layer whose serial+omp arms are runnable on the EPYC 9655 today with nothing but `g++ -fopenmp`, and
      it PRODUCES MEASUREMENTS: `pass@k`, `build@k`, `speedup_n@k`, `efficiency_n@k`, plus a locally
      measured `best_sequential_runtime` baseline. Per the standing rule, the write side is cheap and
      permanent while the read side cannot be retrofitted — `benchmarks/results` is the standing proof at
      4,562 files with no usable claim tuple. The adapter must **PROJECT** a driver record
      `{problem, parallelism_model, k, pass@k, speedup_n@k, efficiency_n@k, best_sequential_runtime,
      hardware}` into a `ClaimTuple` and let `claim_tuple.grade()` decide; it must **NOT write a new
      grading rule** — the carrier is shared, each source class has exactly one ladder, and the registry
      refuses a second (`docs/design/vidya-pilot-spec.md` §4.7). Note the measurement caveat that must ride
      with any tuple: ParEval wraps its timed region in `__attribute__((optimize("O0")))` at a fixed
      problem size, so its absolute numbers are NOT comparable to our llama-bench protocol and must never
      be graded against it. Source-table row added in `scripts/vidya/adapters/README.md`.
      **STATUS 2026-08-26: still before-the-first-run — no ParEval execution since intake-1225; the
      owning program rows are open (`RVP-C5-6` serial+omp trial on the EPYC 9655, CPU-only,
      `RVP-C5-7` HIP arm). SHARPENED TRIGGER: wire the driver-record projection
      (`{problem, parallelism_model, k, pass@k, speedup_n@k, efficiency_n@k, best_sequential_runtime,
      hardware}`) before RVP-C5-6 executes — C5-6 needs no inference grant, so this trigger is
      scheduler-gated, not operator-gated; the `O0`-wrapped timing caveat rides in every tuple
      **EVENING 2026-08-26: adapter WIRED before any run — `pareval.py` (17/17 tests), checkout
      cloned + pinned at `/mnt/raid0/llm/pareval` `9e2a9afafa2c`; one ClaimTuple per
      (problem, parallelism_model, k, n) cell, serial=BASELINE/parallel=CANDIDATE enforced, O0
      caveat enforced verbatim in every claim, attestation honest (Attested only in a pinned git
      tree). C5-6 runbook staged (serial+omp, 96-thread sweep, CPU-only); the ONE remaining
      prerequisite is LLM-generated outputs for the 60+60 prompt subset (the repo's generate
      scripts need a base_url shim). NEW TRIGGER: RVP-C5-6 executes → first tuple → close**

## SC49 — write-side hook for the research-intake compute-gated sweeps (filed 2026-08-21)

Four sweeps specified by the 2026-08-21 Stage-2b wave will produce measurements, so the write-side
task is filed **now, before any of them runs** — not when results land. Source row added to
[`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md).

| Sweep | Owning handoff | Emits |
|---|---|---|
| **G1** #27442 greedy boundary sweep | `log-linear-gated-deltanet-readiness.md` | prompt token count, prompt class, **first sampled token id**, stop reason |
| **G2** redesigned DF2-5 concurrency grid | `dflash2-block-drafter-experimental-build.md` | per-slot acceptance, mean accepted length, drafter arm, `--kv-unified` state |
| **G3** MI210 quantized-KV verify probe | `speculative-decoding-mtp-refresh.md` | selected FA kernel per `draft_max` |
| **G4** post-restore prompt-reuse rate | `dynamic-stack-concurrency.md` | reuse fraction per migration |

- [ ] **SC49 — build the adapter that projects these into `ClaimTuple`s.** It must **project, not
      grade**: the carrier is shared, each source class has exactly one ladder, and the registry
      refuses a second. Two caveats are load-bearing and must ride in every tuple: **G1 is a
      correctness observation, not a throughput one**, and its repeated-pangram arm is a *negative
      control* whose result must never be projected as a model-quality claim; **G2's acceptance ratio
      is not comparable across `--spec-draft-n-max` values**, so `n_max` and mean accepted length must
      travel together or the tuple is uninterpretable.
      *Rationale for filing pre-run:* wiring the write side is cheap and permanent; retrofitting the
      read side is impossible, and a tuple invented on read claims warrant the original run never
      captured.
      **STATUS 2026-08-26: unchanged — filed before any run and none of the four sweeps has run (G1
      open in `log-linear-gated-deltanet-readiness` with gates fired; G2 is DF2-5, open; G3 open in
      `speculative-decoding-mtp-refresh`; G4 open in `dynamic-stack-concurrency`). SHARPENED
      TRIGGER: the adapter's build is gated on the first G-sweep execution — build it before that
      first run per the filed spec, with the two load-bearing caveats (G1 negative control never a
      model-quality claim; G2 `n_max` + mean accepted length travel together) in every tuple
      **EVENING 2026-08-26: unchanged — no sweep has run (verified). G1 is CPU-runnable and the
      lease regime is granting compute, so the trigger is schedule-gated, not operator-gated
      **CLOSED-ISH 2026-08-27 — G1 EXECUTED and its tuples are live.** The sweep ran 10/10 trials
      (frozen v9 llama-completion, frontdoor Q8_0, 5 lengths × pangram/meaningful, greedy
      seed 27442, cold prefill): first token uniformly `248068` (`<think>`), never EOS — the
      #27442 exposure is NOT reproducible on our path (gate verdict, G1 row ticked in
      `log-linear-gated-deltanet-readiness.md`). `research_sweeps.py` projected all 10 claims,
      frames ingested (ledger frontier 12,532), fold `Witnessed/Anchored`; runner
      (`g1_27442_boundary_sweep.sh`) fixed en route (tokenize stdin round-trip, proportional
      prompt-step, console-notice hygiene) and committed. G2/G3/G4 remain pending their own
      first runs — this row's residual is them, not G1**

## SC50 — write-side hook for the wave-2 research-intake sweeps (filed 2026-08-22)

The 2026-08-22 Stage-2b wave (15 dives, `intake-1280`…`1294`) specified a further set of
compute-gated measurements across **three distinct source classes**. Filed **before any of them
runs**, same rule and same reason as SC49. Source row added to
[`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md).

| Class | Sweeps | Owning handoff | Emits |
|---|---|---|---|
| **KV-quantization eval** | G2 outlier ratio · G3 GSM8K-class reasoning · G4 IFEval CondFlip · G5 rotated incoherence ratio | `tq3-quantization-evaluation.md` | per-layer/per-head max÷median for K and V separately; paired exact-match deltas; FP16-anchored CondFlip; per-group max/RMS at G=32 |
| **Draft-acceptance sweep** | G8 KV-asymmetric self-speculation α · G9 DF2-6 ngram arm | `speculative-decoding-mtp-refresh.md`, `dflash2-block-drafter-experimental-build.md` | mean accepted length and per-token agreement per `--draft-max`; per-prompt PASS/FAIL and first-differing-token index |
| **Retrieval fidelity fixture** | G11 INT8-vs-fp32 and mirror-vs-upstream parity · G12 verbose-query arm · G13 doc-truncation recall | `internal-kb-rag.md` | per-token cosine distribution, max abs Δ, MaxSim top-1 agreement; recall@10 per arm |

**G13 producer projection detail (R2 preparation, no full-result tuple):** extend this existing retrieval-fidelity source class and SC50 implementation; do not add a second source row, ladder, checkbox, or canary. A future native result record must preserve source/model/index pins, raw-corpus SHA and changed-snapshot flags, arm/chunker/doc-cap/punctuation-mask identity, all 70 truth denominators, doc-cap-256 matched-baseline recall@10/delta, and canonical stored-index score separately; other arms remain candidate comparisons. Carry historical-gate-unassessable/no-adoption as scope. Project the native record through the existing `ClaimTuple`; `claim_tuple.grade()` owns grading. Preparation/admission smoke supports no retrieval conclusion. Future G13 successors must also bind per-query ranked outputs, actual grant, exposures and native cache/worker custody in their write-time attestation. The existing SC50 task covers strict source/arm/model validation and its planning-context canary; do not add a parallel task, canary or ladder. Completed R2 conclusions are observations only; no historical backfill.

- [ ] **SC50 — build the adapters that project these into `ClaimTuple`s.** **Project, not grade** —
      the carrier is shared, each source class has exactly one ladder, and the registry refuses a
      second (`docs/design/vidya-pilot-spec.md` §4.7). Four caveats are load-bearing and must ride
      in the tuple, because each is a way the number gets read as something it is not:
      **(a)** a **fidelity** cosine (G11) is a claim about ONE graph pair, never a retrieval-quality
      claim — the two must not share a ladder rung;
      **(b)** G4's CondFlip is **paired and FP16-anchored**; an aggregate pass rate is a different
      quantity and is not interchangeable with it;
      **(c)** G8 measures **α, not speedup** — the drafter is the full model, so the win is
      KV-traffic only, and a tuple that omits this invites a throughput reading;
      **(d)** G2's dynamic range is meaningful only **per layer and per head, K and V separately** —
      a pooled max÷median hides exactly the asymmetry the sweep exists to find.
      *Why pre-run, again:* `benchmarks/results` is the standing proof — 4,562 files, no write-side
      hook, 0 of 200 sampled carrying a usable tuple, so none of it can gate a decision.
      **STATUS 2026-08-26: unchanged — the three source classes have produced nothing yet (tq3
      G3/G5, speculative G8/G9, internal-kb G11/G12 all open). SHARPENED TRIGGER: build the three
      adapters before the first sweep in each class executes, each carrying its class caveat
      (fidelity cosine = one graph pair; CondFlip paired+FP16-anchored; α = acceptance not speedup;
      dynamic range per-layer/per-head K and V separately) — the first run in any class is the
      trigger, and it is compute-gated
      **EVENING 2026-08-26: unchanged — no sweep has run (verified)**

  - **2026-10-30 G11 R2 preparation update:** The G11 R2 diagnostic packet qualified and was
    accepted by the live keeper as READY-WAIT. Its native record fields and scope limits are filed
    in [`internal-kb-rag.md`](internal-kb-rag.md) and the existing source row above. The full
    200-chunk cohort has not run. The SC50 write/read projection work remains open; no adapter,
    ingest, emitted ClaimTuple, or planning-context canary is claimed. G11 remains fidelity only,
    with the existing measurement carrier and `claim_tuple.grade()`; no new ladder or retrospective
    run warrant is introduced.
  - **2026-10-30 G11 R2 completed diagnostic:** 200/200 chunks in both roles and 70/70 K7 queries were captured for each applicable graph pair; 59/70 FP32–INT8 primary top-1 agreements in each source fail the 100% rule. Source/pair fidelity is not retrieval quality. Preserve all denominators, graph/prompt/model pins, quantiles, maxabs and literal-prefix refusal in the existing SC50 projection; it is not yet wired, and this committed conclusion does not create a retrospective measurement warrant. [belief: cc]
  - **2026-10-30 G12 preparation update:** The fixed paired query-shift packet is qualified and
    keeper-accepted as READY at rank 59. Its 110-query cohort has since completed; the 20-pair short-minus-verbose result did not open B7 (see 2026-10-30 result below). The record schema retains case IDs,
    existing truth paths and missingness, evidence-file recall@10, uncapped token counts, and
    source/index/model pins. The existing SC50 adapter/projection task remains open; smoke output
    is not a retrieval measurement, and no cap change, new ladder, ingest, or planning-context
    canary is claimed.

## SC56–SC60 — Prove2Me intake wave (filed 2026-09-07)

Source: `intake-1297`…`1310` (Prove2Me coordination harness + the sources behind its claims), all
`dive-verified`. The wave's relevance here is **one finding and one convergence**. The finding is
that a machine-checked verdict certifies *the proposition the checker decided*, and nothing binds
that proposition to the claim someone cites it for. The convergence is that a platform with every
commercial incentive to accrue reputation arrived independently at this program's two-plane split.

- [ ] **SC60 — rank open obligations by discharge leverage** (how many beliefs' gate outcomes would
      change if this obligation were discharged), modelled on Prove2Me's `closability`. **LOW
      priority, and filed with its own deflation:** measured on our dependency graph the metric
      would be 0 for roughly 85% of nodes, because their graph is a dense proof tree and ours is a
      sparse hand-authored annotation. Copying the metric without the density copies the ceremony,
      not the signal. File it; do not start it.

- [ ] **SC64 — a sequential certification that cannot fail.**
      `scripts/vidya/adapters/autokernel_aux_receipt.py:584-585` pins an anytime-valid sequential
      test's STOPPING TIME to the value it happened to take (`first_crossing_block != 9` and
      `signs != [1.0]*20` are both treated as malformed). A genuine re-run that crosses at block 8
      or 10 is rejected. The check therefore certifies *this run's transcript*, not the procedure —
      the opposite of what an anytime-valid test is for. Found 2026-09-07 by the RC-12 audit.
      Not fixed inline: choosing what the admissible stopping-time envelope IS is a judgment about
      the test's design, not a typo.

- [ ] **SC63 — wire blind read-back outcomes into the belief kernel.** RA-13b (landed 2026-09-07)
      is a NEW WRITE-TIME MEASUREMENT SOURCE: caught-discrepancy / false-discrepancy /
      agreement-with-author counts over a partitioned denominator. Filed the same day per CLAUDE.md.
      **It has no rows yet** — the N=20 pilot is operator-gated and unrun — so this is the write-side
      hook going in BEFORE the first measurement, which is the whole point (retrofitting the read
      side is impossible). **Project, never grade**; no new ladder. The citability threshold is
      part of the claim, not a convention: a read-back result below n=20 must not project at all,
      and `citable_summary()` already refuses it. Source-table row to be added to
      `scripts/vidya/adapters/README.md` when the adapter lands.

**Declined from this wave, recorded so they are not re-derived.** A dead-end/negative-evidence
ledger (real problem, but a coordination artifact rather than a claim-level belief — it would widen
this program past its ratified three gaps); a guard against deleting retraction records (already
structurally impossible under append-only JSONL §11.0 — worth stating as a defended property, since
the source platform's own milestone delete cascades its edit history with no undo); and an
audit-envelope fix for claims reused outside the context that vetted them (already solved — the
grade travels with the claim, and the `intake-NNN` / `#NN` / `#record` citation forms already encode
that relying on a whole entry inherits every defect of every claim in it).

## SC65–SC68 — research-intake wave 2026-09-07 (filed 2026-09-07)

Source: the 2026-09-07 `/research-intake` wave (`intake-1311`…`1345` + the `intake-408` re-dive).
Four measurement sources are specified by this wave, and all four are filed **now, before any of
them produces a row** — the standing rule: wiring the write side is cheap and permanent, retrofitting
the read side is impossible, and `benchmarks/results` is the standing proof. Source rows added to
[`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md).

*Id note: the plan allocated SC63/SC64 for the first two rows; both ids were claimed in this file
between plan and apply, so this wave takes the next free block, SC65–SC68.*

| Source | Owning handoff | Emits |
|---|---|---|
| **PS-1** sink+window floor sweep | `streaming-llm-baseline.md` (INF-51) | per arm×workload cell: `K_sink`/`K_win`/budget, `-c` sizing + chunk, tokens generated + eviction regime, benchmark id + scored-n, paired teacher identity |
| **MoE routing tap** | `moe-routing-tap-and-locality-measurement.md` (INF-72) | per (model, layer, domain, m): SRP, SCH(m), EOR/IR_t + the chance baseline |
| **`tulving_episodic`** scored runs | `episodic-memory-integrity.md` (M-12) | per run: `f1`, `nb_gt`, `nb_pred`, `retrieval_type`, `get_style`, arm, scorer version, n scored |
| **BEAM** benchmark runs | `episodic-memory-integrity.md` (M-12) | per run: the BEAM-fold headline, with the rubric-item micro-average and binarised pass count as recorded context |

- [ ] **SC65 — build the adapter that projects the PS-1 floor-sweep cells into ClaimTuples.**
      Project, not grade — the carrier is shared, each source class has exactly one ladder, and the
      registry refuses a second (`docs/design/vidya-pilot-spec.md` §4.7). Three caveats are
      load-bearing and must ride in every tuple: the recovery ratio is **paired to the SAME teacher,
      per model per workload, never pooled**; the **long-INPUT retrieval arm measures a different
      method** (full-attention prefill + streaming decode) and must never be graded against a
      published SWA table; **accuracy is the primary axis** — a speed null on weight-bandwidth-bound
      CPU decode is not a refutation. A cell that never evicts did not test the mask and must be
      labelled, not silently pooled. Trigger: the first sweep cell, which is compute-gated.
      Pre-hook artifacts (the 2026-07-20 Qwen3-1.7B sweep, the 2026-08-25 zero-cell 72-cell daemon)
      emit zero rows and are never reconstructed on read.
      Sources: `intake-1315#record`, `intake-1334#record`, `intake-1340#record`.

- [ ] **SC66 — build the adapter that projects SRP/SCH/EOR tap output into ClaimTuples.**
      Filed at stub creation, not at first trace, per the standing rule. Four caveats ride in every
      tuple: **SCH is a diagnostic, never a throughput claim**; a **stride-hazard signature** (every
      expert appearing exactly k times, sub-chance reuse) **refuses the row fail-closed** — it is a
      broken read, not a negative result; **domains are never pooled** (mixing manufactures
      uniformity); and **v9 does not cover `qwen4exp`/`glm5next`**, so a qwen4exp tuple cannot exist
      yet. The chance baseline (3.13% = 8/256 qwen35moe; 1.95% = 10/512 qwen4exp) rides in the same
      tuple, because an EOR figure is uninterpretable without it. The derived +1.58–2.03%
      end-to-end ceiling is a **CLAIM ON THIS ROW, never a second source** — it is an arithmetic
      consequence of two existing first-party measurements, and a second source row for a derived
      quantity would put one measurement behind two ladders. Trigger: the tap port, which is
      compute-gated. Sources: `intake-1328#record`, `intake-1336#record`, `intake-1338#03`.

- [x] **SC74 — repair the blocking `intake-1300#record` citation in `docs/design/vidya-pilot-spec.md`.** The 2026-09-07 external-corroboration paragraph cites the entry at ENTRY level, so it inherits that entry's overturned deprecation claim (`intake-1300#record`) and `scripts/handoffs/index_state.py --check` reports it as the one blocking cite-check problem on main. The faithful narrowing is ambiguous between claim 0 (immutability is half-scoped) and claim 2 (the trust score gates nothing), so the author of the paragraph decides which claim the corroboration actually rests on — a passing session must not guess. Introduced by commit `51f9ef61`; surfaced by the 2026-09-07 research-intake wrap-up. Filed as SC69, renumbered to SC74 the same day because a concurrent session claimed SC69-SC73 in commit `6ebb8878`. Zero compute. ✅ 2026-10-07 — [MAIN current source/prose review](../../artifacts/ni08/registry-docs-and-stale-vidya-source-20261007/README.md); no new native execution claimed.

### VB-AK-LEGACY-SERVING — direct serving comparison and CPU facts (2026-09-10)

- [x] **VB-AK-LEGACY-SERVING — wire the direct legacy serving comparison at write time.** ✅ 2026-09-10
  Owner `autokernel-unified-20260908`; producer is research `loop/run.py:cpu_compare`
  through `ServingComparison.to_dict`, `Outcome.to_attempt`, `archive.record` and
  `controller/experiments.py:ExperimentStore.record`, not an `evaluation_event` or
  a unified planned/native arm. The full comparison is retained in the archive,
  including future per-launch `cpu_lifecycle` facts from the on-disk collector.
  Research source `86179a8c` / main `0a815338` now captures original inputs before
  `serving.compare` launches, then seals two arm observations in `belief_capture` /
  `belief_measurements`. The strict ROOT `autokernel_legacy_serving.py` reader and
  existing corpus dispatcher reopen the bounded original source. They preserve
  original model/build/recipe/metric direction, request-bound floor,
  arm/launch membership, PID/TID-start and phase-time evidence, read failures,
  gaps, bounds and immutable source identity. The independent unit is the original
  process launch, never an affinity sample, thread or prompt. Allowed CPU/NUMA lists
  are permissions, not actual NUMA page placement or a contention verdict. Keep
  `cpu_placement`/`contention=unproven` unless an actual owning verifier supplies
  more; raw facts confer no qualified measurement or promotion authority. The
  capture leaves `protocol_id` empty, so the unchanged shared ladder returns
  `Judged/Located`, not qualified measurement. Unresolved legacy arm build paths
  remain paths; missing resolved/loaded identity is not upgraded into a verified binary.
  Main verified 33 research tests plus 8 subtests and 15 ROOT tests, including the
  actual compare→archive→original-source reader→corpus→Ledger path with synthetic
  observations. Moved/tampered source refuses; export faults remain visible after
  durable archive without changing the experiment result. Pre-hook records emit
  zero rows. That write/read checkpoint did not reload the live process or run a
  live ingest; the subsequent planner feedback checkpoint is recorded below.

  - [ ] **VB-AK-LEGACY-SERVING-LIVE — verify a future post-hook direct-serving capture and
    its explicit corpus ingestion at the owning run boundary.** Do not reload the current
    trial or invent historical carriers as a documentation action. Retain the real source
    reference, import report and observation-only grade; this does not qualify hardware gates.
  - [x] **VB-AK-LEGACY-SERVING-FEEDBACK — connect original direct-serving observation rows
    to an appropriate planner read-feedback path.** ✅ 2026-09-10 — Research source
    `8360d3e1` / main `ba5abca4` installs one synchronous bridge in the existing loop.
    A bounded startup receipt scan is followed by exact newly exported receipt IDs,
    using a private per-store `serving-beliefs/feedback-ledger.jsonl`, not a new service
    or a full corpus re-ingest per hypothesis. ROOT joins the strict original source
    to existing claim IDs, then uses the unchanged fold/query gate. Original model
    descriptor, recipe/request digests, epoch and current anchor identity scope the
    separate `serving_observations` context; the actual comparison rebind supplies
    post-keep anchor identity without extra prompt-time binary hashing. Existing
    `prior_experiments` recall remains unchanged, including historical/pre-hook nulls.
    `Judged/Located` observation status is not a gain, ranking or promotion warrant.
    Main verified 28 ROOT tests (0.63s) and 55 research tests (4.17s), including the
    actual loop→archive→ingest→planner path, post-keep changed bytes/subsequent null,
    restart without duplicate frames, scope/source refusal and nonfatal reader faults.
    Providers/measurements in those tests are synthetic. For a future owning start use
    `--belief-root-repo /mnt/raid0/llm/worktrees/mains/autokernel-unified-20260908`
    ([operating instructions](../../docs/guides/agent-workflows/agent-loop-design.md#operating-the-existing-loop-across-targets));
    the live PID was not reloaded and real post-hook hardware/live ingestion remains
    the separate open LIVE task, not an achieved qualification gate.

### VB-AK-UNIFIED — unified current-loop producer hook (filed 2026-09-09)

- [ ] **VB-AK-UNIFIED — wire the unified current loop before its first new measurement**
      (`autokernel-unified-surface-program.md` §9 AKU-08). Emit producer-authored, self-hashed carriers
      at sealed experiment/arm boundaries with exact immutable model/build/recipe, protocol and metric
      direction, independent-unit/paired execution membership, raw evidence and during-arm contention,
      placement and GPU residency witnesses. Reuse SC75 for serving arms and the shared `ClaimTuple`
      grader. Preserve intended-use/applicability separately from grade; search-only results cannot
      become bank/release claims through projection. Historical pre-hook rows remain history, never
      retrofitted warrant. Journal `LOOP_BUNDLE_SAVED` records are operational snapshots, not measurements
      or a new source class, and produce zero tuples. Add strict reader and replay/outage fixtures,
      mandatory pre-top-k conflict checks and dependency-generation admission checks. This is source
      wiring authority only; live research/resource gates remain unchanged.
      **2026-09-09 source checkpoint:** AKU-04c/08b implements the prospective sealed-arm producer,
      strict shared-ladder reader and existing corpus dispatch, including actual raw-byte rederivation
      and same-ID conflicting-carrier quarantine. Supported scalar is serving/process/level/median;
      absent witnesses remain diagnostic. No historical ingestion or warrant backfill occurred.
      AKU-03c additionally wires verified native controller events, exact retry and restart; the actual
      producer→Journal→reader path passes hermetic integration. No live worker fence is inferred.
      This parent remains open for bounded cursor/feed replay, producer-side
      planner question bindings and registered current-use consumers. Evaluator identity/lifecycle
      instrumentation remain separately required; a source schema is not a protocol registration.

  - [ ] **VB-AK-UNIFIED-LIFECYCLE — bind prospective whole-lifecycle observations and loaded
    instrument identity to native arm evidence.** Owner `autokernel-unified-20260908`; source work
    under review. Reuse the existing immutable ArtifactStore and native Journal, with exact
    worker/grant/container/PID-start and actual probe intervals. Missing attribution, exceeded
    observation budgets, incomplete shutdown and unproven loaded code stay explicit unknowns.
    Native attachment and strict reader must agree on the versioned identity; old records are never
    relabelled using today's source. Observations alone produce no gain claim, quiet-host rule or
    competing grader. Wire the actual serving/worker consumer before claiming lifecycle completion.
  - [ ] **VB-AK-UNIFIED-PARENT — wire parent per-witness receipts prospectively.** Owner
    `autokernel-unified-20260908`; producer/native replay published as research 0a4aada6 with
    AKU-07m; finish ROOT per-witness consumer, not merely native issuance checks. Retain exact
    native/lifecycle artifacts, loaded source pins, parent-issued worker/grant/container/process/
    unit/phase identities and the finding underlying each non-unknown witness. Carry the sealed
    artifact through closed completion IPC; native capture and the existing ROOT arm reader must
    reopen the same receipt and reject mismatched witness/finding references. Unsupported purpose,
    correctness/contention/GPU warrants stay unknown. Reuse the existing source-class grading;
    these supporting receipts are not an independent performance claim or a second ladder.
    Include prospective original T0 issuance/full-report/raw-capture receipts and complete model
    inventory receipts (separate inventory and native entry-file digests). Native deterministic
    reducer replay is not independent reparsing or fresh observation. Also register same-server
    raw request/response/token evidence before any real run; missing seed/token contracts cannot
    establish determinism. These supporting records use this existing task and source ladder.
    Research 8f582b22 now writes `epyc.autokernel.native_server_response.v1` leaves and
    `epyc.autokernel.native_server_response_unit.v1` ordered units in the actual contained
    serving lifecycle. Original instrument pins and exact request/response bytes are retained;
    ROOT per-witness consumption remains required, and raw capture alone grants no grade.
    Research 9e2125b1 / main 625348f8 additionally retains same-attempt raw window receipts:
    original marker bounds, host/claim/storage samples and lifecycle interval joins with
    prospective source/configuration identity. Extend this same consumer to reopen those
    dependencies; raw factual coverage is not a quiet-window or calibration/control verdict.
    Research 8f536e0e additionally emits separate parent-final trial/pair records and native
    unified-arm capture v3 referencing unchanged original v2 carriers. The ROOT reader must
    verify original/final/source joins and preserve diagnostic unknowns under the existing
    source class/ladder; never relabel the child v2 producer closure as a parent v3 writer.
    ROOT direct arm/corpus reopening is implemented under AKU-08j with actual producer and
    malformed-reference tests. Registered feed source closure now captures the final-trial
    helper prospectively (AKU-08k, research bcd32f1d), with actual v3 ingestion/restart and
    six-file compatibility tests. Separate semantic receipt source/version integration and
    actual historical consumer restart are implemented under AKU-08l (90 independent tests).
    Diagnostics retain no tuple/grade or scientific permission. Qualified serving-decision
    consumption remains AKU-08m; this parent task remains open.
  - [ ] **VB-AK-UNIFIED-DISCOVERY — wire the generic A2 runtime-screen producer prospectively.**
    Owner `autokernel-unified-20260908`; source work under review. Preserve fixed three-anchor-bank /
    three-candidate-only membership and zero fresh anchors on reuse, exact single-factor semantics,
    prospective effect question and original raw/phase provenance. The bounded feed consumes the
    sealed receipt rather than inventing an improvement by joining independently emitted arm levels.
    Strict reader and the shared ClaimTuple ladder remain separate from registered nomination/use
    eligibility. Do not change historical GGML_IQK bank semantics, backfill missing claims, or treat
    an A2 nomination as a keep, validation or release result.

  - [ ] **VB-AK-UNIFIED-PROFILE — wire selected target-profile results prospectively.**
    - [x] **2026-09-17 sampled-location extension, before first live GLM use** (GLM-5.3-Flash deleted 2026-09-22; read as "before first live use on the next CPU target", e.g. DeepSeek-V4.1-Flash): write bounded per-TID×symbol-family×sampled-CPU/NUMA-location period fields and the `perf --sample-cpu` capture identity in the original immutable profile receipt. Project only native sampled fields through the existing measurement ladder; old captures remain location-unknown, and CPU location alone cannot establish remote memory traffic or a throughput gain.
      ✅ 2026-10-22. Write side: research `07333b884`. Read side: ROOT `autokernel_profile.py` reader v2
      (`SAMPLED_CPU_CAPTURE`). The version is read from the receipt's own `perf record` command; legacy
      captures keep exactly the old checks and projection. v2 validates the per-phase topology (digest
      rederived) and the location periods (they rederive the sample totals) and pins two source digests
      (07333b884, research main b93017dc9). Only the version and the topology digests are projected;
      `claim_tuple.grade()` is unchanged. Tests use real producers at 83334d892, 07333b884, b93017dc9
      and live. `progress/2026-10/2026-10-22-ak-profile-reader-v2.md`.
    - [x] **VB-AK-PIN-REPIN — recurring re-pin of the VB adapters' pinned source digests.** The reader v2 pins two research source digests (07333b884, research main b93017dc9, `progress/2026-10/2026-10-22-ak-profile-reader-v2.md`), so every change to research main that touches a producer file makes the adapter's digest stale and its tests fail (the 15 failures found 2026-10-22 had this shape). Add a check that lists each adapter pin whose file changed on research main (read-only `git log -- <file>` against the pinned sha) and re-pin after re-running the producer-backed tests; run it whenever research main changes a producer file and at every operator `/wrap-up`. Zero inference. ✅ 2026-10-23 — `scripts/vidya/producer_pins.py` (`check` / `digest` / `repin [--apply]`), `tests/vidya/test_producer_pins.py`. `check` is the task's read-only `git log <pinned-commit>..<ref> -- <file>` over 8 file pins (the pinned commit is found by walking the file's history for the blob whose sha256 equals the pin) and the sampled-CPU closure pin (last entry of the new append-only `autokernel_profile.SAMPLED_CPU_ROLLING_PINS`); exit 3 on stale/unresolved/unmapped, and a new `*_SHA256`/`*_DIGEST` pin constant in neither `FILE_PINS` nor `EXEMPT` fails it. It found the live drift immediately: research main had moved the closure (`8320de269`, `4d95c05e5`) so `sampled-cpu@live` failed; re-pinned research `62c2e09da` -> `d0bf62e9…` (method check: `digest` reproduces the `b93017dc9` pin `69dea977…`), producer-backed tests green with `EPYC_RESEARCH_ROOT` set. Command: `python3 scripts/vidya/producer_pins.py check` (run when research/orchestrator main changes a producer file and at every operator `/wrap-up`; nothing is cron-installed).
    - [x] **Direct existing-loop CPU observation/corpus and actor read-side connection**:
      ✅ 2026-09-10. `loop_cpu_profile.v1` binds the producer's original compact capture,
      actual execution/frozen-request identity and sampled-period measurement. The existing
      registered measurement projector and canonical grader are reused; there is no direct
      verifier/`PROFILE_VERIFIED`, model verification or comparable speedup claim. ROOT
      40-case actual-producer/corpus/old-profile acceptance passed; research 114 cases passed.
    Concrete emitter now exists: research `cpu_profile.run_profile_request`, compact
    `epyc.autokernel.cpu_profile_capture.v1` and two authored mappings in
    `epyc.autokernel.profile_measurement_carrier.v1`, checked by `reopen_capture` before
    output. Producer SHA256 `e626efddf14530a7d4eb3f2ec06b5b86b70a14a2b329a2e59b9054b46cdb20eb`.
    Registered ROOT projection and durable feed terminal/profile pairing are implemented
    for this concrete CPU producer under AKU-06q. Preserve sampled-period attribution and receipt-integrity-only
    scope; neither is model correctness, comparable performance or production validation.
    Owner `autokernel-unified-20260908`; implementation assigned to the actor/profile consumer.
    Preserve the selected profiling request and original target/model/quant/recipe, loaded
    profiler identity, actual owned worker result, raw artifacts and observation intervals when
    deriving hotspots/opportunities. Reuse an existing profiler source/adapter where applicable;
    configuration metadata cannot substitute for observed profile freshness. Project measured
    findings only through the existing source-class ladder; retain unsupported/unknown states.
    - [x] CPU producer's prospective measurement/integrity projection and durable pairing:
      ✅ 2026-09-09. Exact original identity joins, bounded compact capture, before-ACK pair
      persistence, restart/retraction and capacity-one failed/conflicting attempts verified.
      Main89 research and65 ROOT combined tests pass; broader selected-profiler wiring remains open.
  - [ ] **VB-AK-UNIFIED-PREPARATION — wire source/build preparation findings at write time.**
    - Codex3 prospective build extension (2026-10-30): full C3-native479ee3bbb and KPF item4 trace84d0a316 build records belong to this existing source family. Preserve source-time identity, recipe, commands, actual completion/refusal and linked-artifact/help/knob proofs; project dependency or categorical findings through the existing carrier. Object smokes and plain success markers create no retrospective measurement warrant. Source rows are updated now; do not call the loops wired until their planning-context canary passes.
    Owner `autokernel-unified-20260908`; bind selected actor advice/assignment, authored immutable
    manifest and patch, actual guarded source commit/tree, derived diff-policy checks and original
    mutation receipt before the first live preparation. Persist through the owning native artifact
    transaction; strict reopening projects only the proposition actually verified. Build findings
    additionally require the actual owning build identity and inputs, never a runner return label.
    Reuse the canonical verifier-class ladder; no new grading rule, retrospective warrant,
    model-correctness claim or performance inference from successful source application.
  - [ ] **VB-AK-UNIFIED-VALIDATION — wire owning objective and LOO decisions at write time.**
    Owner `autokernel-unified-20260908`; implementation assigned to the semantic consumer.
    Preserve the exact proposition decided by the existing production-validation protocol,
    objective identity, batch/row/manifests and native measurement/calibration evidence, decision
    and immutable artifact references. Reopen through the concrete row/LOO verifier without a
    history scan. Reuse canonical verifier-class grading and proposition-binding rules; do not
    manufacture a scientific policy, combine measurement grades into a new ladder, or reconstruct
    a missing decided proposition on read. Source quality and permitted scientific use stay separate.

## SC76–SC81 — research-intake wave 2026-09-15 (noninf-20260914)

- [x] **SC76 (S3-VID-02) — claim_anchors are re-verified, not self-consistent.** The only hasher runs at
      write time (machine_anchor.py) and the validator has zero claim_anchors checks. Add a
      re-verification call: re-find the quote in the RAW fetched artifact whose sha256 is recorded (not
      a summary, not a paraphrase), and recompute quote_sha256 over canonical.normalized_quote
      (scripts/vidya/canonical.py:116-141, which already exists; cite it, do not define a second one).
      Reference implementation: /mnt/raid0/llm/tmp/stage2b/s2b-valid-anchors.py (re-found every quote in
      intake-1373/1374/1377). This is the ONE re-verifier that SC77, SC79 and SC80 build on.
      (intake-1367#record; intake-1373#record; intake-1386#record)
- [x] **SC77 (S3-VID-03) — research_intake adapter tier comes from a verified hash, not record shape.**
      research_intake.py returns Attested whenever quote_sha256 and source_revision are both present,
      and the machine-anchor cap applies only to located_by: machine, so a human-labelled anchor with a
      fabricated quote reaches Attested. Tie the tier to SC76's verification result. intake-1367#record.
- [ ] **SC78 (S3-VID-04) — dilemmatic regression fixtures for research-intake, scored mechanically.**
      4–6 frozen fixtures whose only correct Stage-1/2 output is an honest non-claim: abstract-only
      fetch; 404/empty body; results table stripped; headline number only in a figure image; repo README
      with no license. Pass: every claim_anchors quote is a normalized substring of the stored fixture
      and its hash recomputes; any key_claim number absent from the artifact is absent from key_claims
      (allowed only in notes as unverified). Built on SC76 (one checker). intake-1376#00, #02.
- [ ] **SC79 (S3-VID-05) — citation-class fixtures on the SC78 harness and SC76 re-verifier.** (a)
      IH-anchor: quote verbatim in a DIFFERENT document/revision than source_revision names,
      self-consistent hash → FAIL. (b) TF-anchor: quote absent, hash well-formed → FAIL. (c) SH-anchor:
      one-word or one-number paraphrase → FAIL. (d) PAC-claim: quote present but key_claim
      number/attribution differs → FAIL on a number/named-entity consistency check (real examples:
      dive-1367's MLGym→X. Li attribution; the Ansari taxonomy attributed to GPTZero). (e) PH-anchor:
      12-hex or zero hash, "<excerpt>"/"TBD" quote, "Section X" locator → FAIL at schema. (f)
      IH-identifier: arxiv_id whose abs-page title mismatches the recorded title → FAIL. (g) HONEST
      NON-CLAIM: a title-only surfaced source with no resolvable id, and a paper whose reference list
      contains a fabricated citation; the only pass is "unresolved, no entry". Fixture data:
      gptzero.me/news/neurips (read) and 2412.13176 as the F9 seed, cited from intake-1386.
      (intake-1386#01, #05)
- [x] **SC80 (S3-VID-06) — cite-check: an out-of-range claim index is dangling, not unknown.**
      intake-NNN#NN with NN ≥ the entry's key_claims count must return status dangling (blocking, exit
      3), distinct from unknown (claims not yet ingested). Today both return unknown, non-blocking
      (citation_gate.py). Fixtures: in range and ingested → graded; in range, not ingested → unknown;
      out of range → dangling. intake-1386#record.
- [ ] **VB-INF75-W1-PRIMARY-WIRE — capture a future eligible W1 primary-target census.** Preserve the exact original cold request set, observed fanout and per-phase native graph/shape, model/head/binary/tracer, real device and grant evidence, partials and failures at write time. The current preconnected successor is unsealed diagnostic only: never retrofit a tuple, conflate the shorter constructed prefill with the original workload, or claim the full six-workload P0d. Use the existing census carrier and grading policy, and prove the planning-context canary before decision-class use.

- [ ] **SC81 (S3-VID-07) — write-side wiring for AutoKernel workload census + blast-radius rows
      (INF-75).** Census rows (epyc.autokernel.workload_census.v1) and patch-footprint/classification
      rows (epyc.autokernel.patch_footprint.v1) are verified structural findings: project them via an
      adapter into ClaimTuple (no new grading rule). Non-regression rows reuse the existing serving A/B
      archive/belief export.

  W5s prepares a private prospective primary-target structural carrier before its first census, with prelaunch intent, source-bound journals and one shared-grade observation per shape. Model-free controls pass; it has not emitted a real observation and has not passed a planning-context canary. Separate draft-head inventory/graphs, patch-footprint projection and broader producer adoption remain outside that preparation. Source-table status remains candidate.

  - [ ] **SC81-W5S-CURRENT-WRITE:** Adopt the current W5s successor’s native capture journals and structural result writer prospectively through the existing census adapter and shared carrier. Preserve primary/head scope and both-clock request windows; do not backfill the old WITHHELD rows or invent their measurement warrant. ClaimTuple ingestion and the planning-context canary remain unproven; pass that canary before calling the loop wired. Prepared r2 source (normal entry refused at the disk floor; successor pending): `/mnt/raid0/llm/tmp/codex-w5s-current-census-r2-20261029/{full_main.py,server_probe_full.py}`.

  - [x] **SC81-NEXT-01a16fc3:** prepared and delivered the q2 validation packet; two-core q0 preflight passed, NEXT receipt `3dd7a1cb-1e01-47cb-a387-20b909f35906`. Nine compatibility tests and producer adoption remain; SC81 stays open. ✅ 2026-10-27 [no-belief: packet preparation]
  - *(2026-10-27 21:35Z, ws58 results filing, SC81 CPU source integration.)* `sc81-cpu-source-integration-20261027` rc0 at 19:05:19Z (CPUs 48-71, model-free): `test_rc=0`, unittest `Ran 22 tests ... OK` (`/mnt/raid0/llm/tmp/refactor-01a16fc3/sc81-cpu-ready-1728/results/sc81-cpu-source-integration-20261027-20261027T190516714552241/{receipt.txt,unittest.log}`). Compatibility/source-integration controls only; producer adoption and the nine compatibility tests remain, SC81 stays open. [no-belief: model-free unit tests, no measurement]

## SC69–SC73 — kernel audit survivors, 2026-09-07 (filed 2026-09-07)

*Source: the Q.1 mutation audit of `tests/vidya/` run at the end of the Prove2Me wave — 62 mutations
introduced, **32 survived**. Two P1s were fixed in that pass (`fold.py:409` retraction wildcard,
`projection.py:124`/`:288` review-cause disjunction) and are not rows. The five below are the
defects the audit REPORTED but did not fix; each is a place where the kernel grants standing that
its own spec says must be earned. They share one shape — **a presence check standing in for a
verification** — which is SC58's shape and SC56's, so treat the block as one theme, not five chores.*

- [x] **SC71 — vacuous obligation satisfaction in `impact.py:352` and `:318-329`.** An obligation ✅ 2026-10-07 — [MAIN current source/prose review](../../artifacts/ni08/registry-docs-and-stale-vidya-source-20261007/README.md); no new native execution claimed.
      with an empty required-set is reported satisfied, which fills an absence the pilot spec says
      must be *recorded* (§4.7, "absence is recorded, never filled"). Same class as the `blocked = 0`
      uncountability found in the fan-out corpus this week: nothing to check reads identically to
      everything checked.
      **✅ 2026-09-08 (`5d7f14be`).** `impact.py` `_evaluate` refuses an empty required-set under
      `all`/`any` with a ValueError ("an obligation that requires nothing reads identical to one whose
      requirements all passed"). Red-first: `{"all": []}` graded SATISFIED before; 4/5 new tests in
      `tests/vidya/test_vidya_obligation_vacuity.py` failed first; mutation companion (non-empty
      `all` still evaluates) green.
**Audit coverage bound — do not read this block as exhaustive.** Q.1 did **not** reach
`scripts/vidya/adapters/`, `canonical.py`, `checkpoint.py`, `evaluate.py`, `cli.py`,
`citation_gate.py`, `correction_queue.py`, `machine_anchor.py`, or ~29 adapter test files. 32
surviving mutations over the portion it *did* reach is the measured rate; the unreached portion has
no rate at all. A later session may extend the audit but may not report these five as "the defects".


## VB-GLM53-MTP — prospective validation producer (2026-09-08)

- [ ] **VB-GLM53-MTP — wire the GLM53 text/MTP validation producer at write time.**
  **[Retargeted 2026-09-22]** GLM-5.3-Flash was deleted from disk (operator-directed), so no new
  GLM53 records will be produced. The completed GLM53 evidence below is still history to project
  as-is. The *prospective* half now applies to the DeepSeek-V4.1-Flash text/MTP validation
  producer (3 native MTP layers) in [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md).
  Its source-table row goes in before that model's first run, with the same identity and caveat fields.
  Producer work: [INF-69](../completed/glm53-flash-evaluation.md), runtime validation under
  `/mnt/raid0/llm/tmp/glm53-validation-20260908/runtime/`. Preserve the original launch's
  model/binary/source/recipe identity, native draft/accept/reject counts, in-window contention,
  observation-only host caveats, and forced-prefix rollback/replay results. Project quantitative
  records through the existing ClaimTuple ladder; categorical correctness verdicts stay categorical.
  Do not turn per-token or forced-prefix samples into independent run witnesses. Source table entry
  filed before the first run; completed CPU evidence now exists. The 2026-09-08
  profiling extension also preserves perf/tool/event identity, symbols, phase boundaries,
  sample counts and loss/overhead caveats. Profile shares are attribution, not realized
  optimization speedups; no second grading rule is introduced. The row-exact extension
  preserves explicit prefill/verification policy, checkpoint chunk boundaries,
  cached-plan toggle verdicts, and supersession of failed row-count-only runs.
  The September9 reprofile adds per-output sampled-period normalization, matched
  plain/MTP capture identity, request-local depth controls and parity failures,
  aborted-capture exclusion, and long-prefill bug-fix/negative-control lineage.
  The authorized three-lever implementation adds bitwise kernel controls, per-node
  critical-path timing with instrumentation-off controls, individual switch ablations,
  and matched unprofiled baseline/integrated repetitions. Preserve rejected variants.

## VB-DSV41 — DeepSeek-V4.1-Flash port validation producer (2026-09-22)

- [ ] **VB-DSV41 — wire the `deepseek41` validation/serving producer at write time, before DS41-T1.**
  Producer work: [INF-77](deepseek-v41-flash-evaluation.md) (successor to INF-69; VB-GLM53-MTP's
  subject was deleted 2026-09-22 and it produces no further records). Reuse the VB-GLM53-MTP carrier:
  artifact header/size identity, candidate source/binary digests with linkage proof, full recipe,
  per-depth native MTP draft/accept/reject counts, forced-prefix rollback/replay results, in-window
  contention and GPU residency witnesses. Add reference-parity records bound to the official
  `inference/` revision and fixture scope, with quantization drift kept separate from port defects.
  Categorical verdicts stay categorical. Source-table row filed in `scripts/vidya/adapters/README.md`.

- [ ] **VB-AK-DS41-OPS — add a prospective write-side producer for AutoKernel actor-repair and planner-seat
  operational measurements before the next such run.** Record actor repair shape/outcome and latency, planner
  endpoint/model plus prefill/decode rates, proposal/author timings, and timeout/partial-output disposition with
  run, recipe and artifact identity. The 2026-09-24 progress narrative is retrospective and yields zero tuples;
  do not backfill. Any eligible native record projects through `ClaimTuple` and `claim_tuple.grade()`; no new
  ladder or campaign/keep authority. Source-table row: `scripts/vidya/adapters/README.md`.


- [ ] **VB-AK-SERVING-PROFILE-WIRE — add prospective write-side capture and projection for AKX-ALL-16/29.2a native GPU serving profiles and NEMO-LILI-2 native profiler outputs before future profile evidence is used for planner ranking or candidate timing order.** Preserve native SSE/token counts (null when absent), frozen request/window and model/target/drafter inputs, executable/DSO hashes, live PID/birth/executable/maps and loader linkage, during-run KFD/VRAM, trace clock/fiducial, per-window counters/denominators, partial/refusal state and cleanup. NEMO-LILI-2 additionally binds ordered stage kernel-name hashes, target/drafter/plain counts and edge exclusions, the source-derived target/drafter boundary, and summed kernel duration separately from elapsed time. Strictly join the native record to its source and inputs, then project through existing `ClaimTuple` and `claim_tuple.grade()` only; keep null/missing outcomes explicit. Run the actual planning-context canary before calling this source wired. Current private qualification is diagnostic and has no tuple/canary; do not backfill its measurements, change the keep gate, or add a ladder. The completed prep/keeper conclusion may use `VB-CC-PILOT` only after that future/conditional register is implemented; no register ingestion is available now.
## VB-GPU-PREP — write-side hooks for three GPU-runner producers (filed 2026-09-16, sub-gpu-prep)

Ported by wrap-up pass 2 from the /workspace working copy. The sub-gpu-prep producers `a454b7fd` and
`e70b6974` reached research `main` as `76f5132b` / `726e2676` (merge `a280853d`, sub-gpuprep-port);
the SL-2 commit `5368766b` did not. The sub-gpu-runner notes (the TALE capture wiring and VB-GPU-RUNNER)
are left to that still-running agent.

- [x] **VB-RUNNER-PATHS — make the GPU-runner capture call sites portable and loud** (filed 2026-09-17 from
  `2026-09-16-sub-runner-adapters.md`). Research `scripts/benchmark/review_f1/ev13b_run.py:197` (on research main)
  hard-codes `sys.path.insert(0, "/workspace/scripts/vidya")`, as does the unmerged PRB-T4 driver
  `prb_t4_tale_gpu.py` (`sub/gpu-runner-20260916`). Both swallow a capture failure into their log. Resolve the
  root checkout from `EPYC_ROOT` (or refuse), and make a failed capture visible. Then port `prb_t4_tale_gpu.py`
  to research main without its tmp-path literals. VB-PRB-T4 cannot close until that driver merges.
  ✅ 2026-09-17
  - Done (sub-vb-wire, research `0b295a25`). The new `scripts/benchmark/belief_capture.py` resolves the
    capture writer from `EPYC_ROOT` and refuses if it is unset or wrong. It loads the writer by file path.
    - Both drivers resolve the writer before the GPU claim, and refuse with exit 2 if they cannot.
    - A failed capture prints a stderr banner, is recorded under `belief_capture`, and makes the exit
      code 3.
    - `prb_t4_tale_gpu.py` was ported from `91d66725` (on main as `0b295a25`). It runs the harness from its own checkout,
      which has the stratified sampler. `--pool` and `--python` are checked before the server starts.
    - Tests: `scripts/benchmark/test_belief_capture.py`, 10 passed.
  - [x] **VB-RUNNER-PATHS-2 — convert the remaining guessed-root capture loaders** (filed 2026-09-17,
    sub-vb-wire). Research `scripts/benchmark/score_tulving_run.py` (`_ROOT_CANDIDATES`) and
    `scripts/benchmark/occ1/run_occ1.py` (`ROOT_CANDIDATES`) fall back to `/mnt/raid0/llm/epyc-root`
    and then `/workspace` when `EPYC_ROOT` is unset. They are loud when nothing resolves, but they can
    silently pick a checkout other than the intended one. Move both to `belief_capture.load_capture`.
    Their tests (`test_score_tulving_run.py`, `test_beam_adapter.py`) must set `EPYC_ROOT`.
    ✅ 2026-09-17 (`sub-small-audits`, research `ae92ac5c`).
    - **Converted.** `score_tulving_run.py`, `occ1/run_occ1.py` and `score_beam_run.py` (the same
      shape, and the loader that `test_beam_adapter.py` tests) now call
      `belief_capture.load_capture`.
      - An unset or wrong `EPYC_ROOT` is refused through each script's existing `SystemExit`. So is
        a module that lacks `write_belief_measurements`.
      - Nothing falls back to `/mnt/raid0/llm/epyc-root` or `/workspace`. That fallback was live
        risk: the shared clone is behind origin/main and lacks these capture modules.
    - **Tests.** The loader and round-trip tests set `EPYC_ROOT` explicitly. 10 new cases fail on
      the old code.
      - With `EPYC_ROOT` unset: 118 passed, 11 skipped.
      - With `EPYC_ROOT` set to root origin/main: 124 passed, 5 skipped (pyarrow).
    - [ ] **VB-RUNNER-PATHS-3 — audit the other hard-coded root defaults in research** (filed
      2026-09-17).
      - **Belief write paths:** `scripts/kernel_rnd/autokernel/loop/serving_beliefs.py:148`,
        `claim.py:40` and `serial_run.py:393` default `EPYC_ROOT_REPO` to `/workspace`.
      - **Fixed roots:** `k35_vision_matrix_runner.py:30`, `run_batch_entry.py:86`,
        `laguna_pgpu1_dflash_runner.py:69` and `op2_quiet_window_prep.py:30` pin
        `/mnt/raid0/llm/epyc-root`.
      - **Candidate list:** `scripts/validate/check_evidence_durability.py:168` walks the same
        candidate list.
      - **Action.** Decide per site whether it writes belief rows or governs a decision, and if so
        route it through `belief_capture.root_checkout`. AutoKernel sites need its quiet window.
- [ ] **VB-PRB-T4-CAVEAT — mark the 24 ingested PRB-T4 TALE rows as sample-scoped (filed 2026-09-17,
  sub-scorer-fix).**
  - **Affected rows.** The ledger holds 24 `vidya.adapters.tale_budget/v1` claims from run
    `prb_t4_gpu_20260916_191049`: 12 `math`, 12 `olympiadbench`. They are
    `tale_suite_accuracy`, `tale_mean_answer_tokens`, `tale_mean_tokens_incl_estimator` and
    `tale_mean_latency_s_incl_estimator` × baseline/static/tale.
  - **Defect.** The harness sampled the first n rows in file order.
    - The `math` claims describe **GSM8K only** (150/150 `gsm8k_*`), not the math suite, which also
      has 500 MATH-500 rows.
    - The `olympiadbench` claims come from a subject-skewed draw: geometry 15/300 trials against a
      19% population share.
  - **Status.** The sampler is fixed (research `52595b9b`). The rows are real measurements of that
    sample, not scorer artifacts.
  - **Action.** Record a correction/scope frame through the kernel's correction path, never by editing
    the ledger. It should narrow the suite label (math → gsm8k subset; olympiadbench → skewed subset),
    or supersede the rows with the PRB-T4-RERUN rows once they exist.
  - **Other affected results (not in the ledger).**
    - The livecodebench sidecar stays withheld. Its accuracy is vacuous, and the stale rows are now
      refused by the scorer.
    - The CT-1/CT-1b/E-7 `mmlu_pro` cells are under-scored (`qwen-chat-template-evaluation.md`,
      CAVEAT 2026-09-17). Their sidecars under `/workspace/tmp/e7-recal/` must not be ingested
      without that correction.
- [ ] **VB-GPU-RUNNER — write hooks for the sub-gpu-runner recipe sweeps (filed 2026-09-16, sub-gpu-runner).**
  These 2026-09-16 runs are PRE-HOOK and emit zero rows. None has a write hook: `serving_beliefs` fires only
  inside `serving.compare`. Do not project their JSONL on read.

  | Run | Went through | Evidence (research) |
  |---|---|---|
  | INF-62 SL-1 / SL-5 | `serving.calibrate_floor(samples=1)` | `8146880b` |
  | DF2-6 serial-exact | `df2_greedy_parity` | `8146880b` |
  | fable5 §5 #1 MoE sweep | `llama-batched-bench` wrapper | `6cbdd856` |
  | ERNIE-Image-Turbo ROCm rebench | sd-server wrapper | `cf05eefc` |
  | INF-61 Qwen3.8 np×depth grid, MTP n-max 8 | `v7_quality_gate_runner` wrapper (throughput only) | `0a711890` |

  Before any successor sweep:
  - Give `calibrate_floor`-based recipe sweeps, and the batched-bench, sd-server and np-grid wrappers, a
    producer hook. Carry per launch: recipe_hash, residency, unit=launch, and the tok/s (or s/image)
    estimator string.
  - Give the parity and A/A runners one too. Categorical PASS/FAIL per prompt stays categorical.
- [ ] **VB-SL2-STEPS — decide whether the serving A/B's `target_sample_steps_est` block (INF-62 SL-2, research
  branch `sub/gpu-prep-20260916`) gets its own `belief_measurements` rows.** Today it rides inside the
  `serving_beliefs` native body (so `native_sha256` binds it) but only tok/s is projected. It is an ESTIMATE
  (`predicted_n - draft_n_accepted`), not the server's `n_draft_verif_steps`; project it only with that
  estimator string in the tuple. (The serving belief READER `scripts/vidya/adapters/autokernel_legacy_serving.py`, reported absent when
  filed, is on root `main` now; see the VB-WIRE status table.)

## VB-HARNESS-AUDIT — harness source-audit findings (filed 2026-09-16, sub-harness)

- [ ] **VB-HARNESS-AUDIT — decide how pinned source-audit findings enter the ledger, before HS-4 cites them.**
  `harness-selection-and-integration.md` now holds three families of source-read findings. Each one carries
  a pinned `repo@sha path:line`, and HS-4 (operator) will read them:
  - the HS-1g call-verb matrix (HONOURED / SILENT-NO-OP / N/A per request path × lever, for 5 candidates);
  - the HS-13 structured-output capability record (llama.cpp `0db32c06e` + orchestrator);
  - the HS-6c conformant Harness Card (eval-tower settings at orchestrator `92bbeb06`, plus 13 named gaps).

  They are **categorical and re-derivable**: a third party can re-read the pinned lines. They are neither
  measurements nor literature, and no adapter projects them today. Choose one:
  - (a) project them through the `verifier` class, with `decided_proposition_field` = the cell verdict and
    locator = `repo@sha path:line`;
  - (b) record them as dependency edges only, like wiki pages;
  - (c) decline them explicitly.

  Do not write a new grading rule. Pins go stale when a candidate moves, so the locator must carry the sha.
  README source-table row added.


- [ ] **VB-MHS-GATES — wire the write side of the RTG-55 gate verdicts when AP-53's rejected-mutation
  ledger lands** (orchestrator `8219d8e8`, branch `sub/autopilot-safety-20260916`, under review, unmerged;
  AP-53's ledger itself is on orchestrator `main` at `753343f5`). Persist
  `rejecting_gate` (static screen / `eval_instance_leakage` / `eval_leakage_vocabulary_unavailable` /
  `effect_risk_gate`), `effect`, `effect_risk`, the gate value and the vocabulary identity per
  proposal. Then project RATES per window (leakage-rejection rate; CONSTRAIN-vs-REPLACE share of
  proposed and of accepted mutations, which is the AP-52 read) into ClaimTuples. Hold
  vocabulary-unavailable rejections out of the leakage denominator. No new grading rule. The locator
  is the window, never the proposal. README row: "PromptForge mutation-safety gate verdicts".
  - Note 2026-09-16 (`sub-mhs3b`, additive): MHS-3's structural refusals (`eval_content_ngram_overlap`,
    `eval_expected_answer_leakage`, `eval_source_identity_leakage`, `eval_suite_special_casing`) write to the same
    `gate_detail` ledger, and each reason string now carries the matched source id. A projection can key on that id.
    No new adapter row is needed.
- [x] **VB-MHS-OPS — project the `eval_leakage_guard` ledger events into claim tuples** (filed 2026-09-16,
  `sub-gate-frontier`; producer on orchestrator `sub/gate-frontier-20260916`, under review, unmerged). Each
  `preflight_failed`/`alarm_raised`→`alarm_cleared` interval is an instrument-unavailable interval;
  VB-MHS-GATES consumes them as the leakage-denominator exclusion. No new grading rule. README row:
  "AutoPilot eval-leakage guard operability events". ✅ 2026-09-16
  - Done (`sub-vbmhsops`, root branch `sub/vb-mhs-ops-20260916`): `scripts/vidya/adapters/mhs_guard.py`
    is the adapter pair, and it only projects.
    - `ingest mhs-guard-ops`: one row per `preflight_failed` event and one per closed alarm interval.
    - `ingest mhs-guard-verdicts`: per closed UTC-day window, the rejection rate for each reason
      class over the mutations the guard screened (AP-53 ledger joined to journal rows by
      `trial_id`). `vocabulary_unavailable` is held out of the leakage denominator.
    - The fixture is written by the producer code, and the producer vocabulary is pinned against
      the branch source.
  - State: adapter ready, producer pending merge. Both README rows are updated. Detail:
    `progress/2026-09/2026-09-16-sub-vbmhsops.md`.
- [ ] **VB-MHS-OPS-HOOK — after `sub/gate-frontier-20260916` merges and AutoPilot restarts on it, set
  `mhs_guard.HOOK_SINCE` to that restart time, then run the first real `cli.py ingest mhs-guard-verdicts`
  and `mhs-guard-ops`** (filed 2026-09-16, `sub-vbmhsops`). Waiting on an external event: the merge
  and the restart. Until the epoch is set, the verdict source declines every unit, because nothing
  persisted marks a clean window as screened, so pre-hook data must get zero rows.
- [x] **VB-AP-PROMO-RULE — project `eval_details.promotion_rule` and `eval_details.frontier_admission` from the
  AutoPilot trial journal into the support frame** (filed 2026-09-17 from `2026-09-16-sub-gate-frontier.md`). Both
  fields come from gate-frontier (c)+(b) (orchestrator `sub/gate-frontier-20260916`, in the AutoPilot merge train).
  The change is additive for the `autopilot_journal` adapter and changes no grade. Do it once the train is on
  orchestrator main. ✅ 2026-09-17
  - Done (sub-vb-wire, root `f71277f7`, against orchestrator main `a1a0251a`).
    - The support frame carries `promotion_rule` (`frontier` / `empty_frontier_repro` / `seed` /
      `archive_unavailable_no_baseline` / `refused_guard_unavailable`), `promotion_status`
      (`pending_commit` / `refused`) and `frontier_admission` (`representative`), all verbatim.
    - It also carries `promotion_committed`. This is True only when a `pending_commit` row has its
      `baseline_promotion` ledger event in the same shard. An uncommitted pending row gets a stated
      "NOT promoted" reason.
    - A pending row on the shard's newest trial is held back until its state is final, because the
      commit event is appended after the row.
    - Keys are absent on rows that lack them, so pre-train frames stay byte-identical. Grade unchanged.
  - Tests: `tests/vidya/test_autopilot_journal_adapter.py`, 17 passed, including an end-to-end run
    against the real writer (`EPYC_ORCH_ROOT`).
  - Ingest: 0 rows. The live journal (`autopilot_journal{,_1}.jsonl`) was last written 2026-08-09, so
    it has no measured rows and no decision fields. The dry run matched 1 unit, projected 0 and
    declined 1.
  - [ ] **VB-AP-PROMO-RULE-INGEST — run `cli.py ingest autopilot-journal` after AutoPilot restarts on
    orchestrator main** (filed 2026-09-17, sub-vb-wire). Blocked on an external event: the first
    post-restart trials. Report how many rows carry `frontier_admission` and `promotion_rule`.
- [x] **VB-AP53-RATE — project the AutoPilot re-proposal rate and the rejected-mutation ledger as
  per-window rates** (filed 2026-09-16, sub-autopilot-evidence; orchestrator `203cb6e2`, merged at `753343f5`). ✅ 2026-09-17
  - Producers:
    - `orchestration/autopilot_rejected_mutations.jsonl`, harness-written, one record per reject;
    - the journal fold `rejected_mutation_ledger.rejected_configs_from_entries()`.
  - Measurement: per trial-id window, the share of trials re-proposing a still-standing
    hard-rejected config, split by action type.
  - The one-off zero-compute value (9.7% of all trials, 31.3% keyed, trials 0–1505) came from a
    scratch script. It is an OBSERVATION until a producer-authored row pins the window, the key
    definition (`config_fingerprint`, narrative fields dropped) and the rejection classes.
  - No new grading rule. Locator: the window.
  - Also done: the autopilot-journal adapter now carries AP-55 `infra_fingerprint` + `comparability`
    through the support frame (grade unchanged; `tests/vidya/test_autopilot_journal_adapter.py`,
    11 passed, including a fixed `sys.path` in the end-to-end test).
  - The AP-54 structural answer (AMBIGUOUS, file-tool reachability of the wiki) is a pinned
    source-read finding of the VB-HARNESS-AUDIT kind; route it through that decision.
  - 2026-09-16 (`sub-vb-writers`): durable writers built on orchestrator `sub/vb-writers-orch-20260916`
    and root `sub/vb-writers-root-20260916`. The SC83 writer is on the same branches. Detail:
    `progress/2026-09/2026-09-16-sub-vb-writers.md`.
  - **Landed 2026-09-17.** The orchestrator side is on orchestrator main (`2789b56d` + review fix `e93edfdb`,
    merged in the AutoPilot train `a1a0251a`). The root side is on root main via the `sub-land-vidya`
    merge of `sub/vb-writers-root-20260916`. It was ticked on the branch on 2026-09-16 but had not reached
    root main until then. Detail: `progress/2026-09/2026-09-17-sub-land-vidya.md`.
  - Writer: `scripts/autopilot/reproposal_rate.py`. `autopilot.py` calls it fail-open after both
    `journal.record` sites. Its first call writes an `armed` record. Each closed 100-trial window then gets
    one self-hashed line in `orchestration/autopilot_reproposal_rates.jsonl`. The line carries:
    - counts split by action type and by standing rejection class;
    - the planner fold's key, rejection classes and frontier clearing, pinned by `definition_sha256`, and a
      test proving this fold equals `rejected_configs_from_entries`;
    - the journal-shard and ledger prefix digests;
    - rows for `all_trials`, `keyed_trials` and `diff_repeat_rate`, each with its numerator and denominator
      stated. A zero denominator writes no row.
  - Locator: the window.
  - Rewind guard (Fable review fix): an emitted window whose recorded journal prefix digest no longer
    matches rotates the file to `*.rewound-<utc>` and re-arms.
  - Reader: `adapters/autopilot_reproposal_rate.py`, dispatched as `cli.py ingest autopilot-reproposal-rate`.
  - Tests: orchestrator 12; root 10, including a live cross-repo test.
  - **Backfill: zero belief rows, per spec §4.7.** A pre-hook row is skipped, not back-filled: today's key
    definition and supersessions are not the ones in force at those trials.
    - `reproposal_rate.py backfill` writes `*.retrospective.jsonl`, labelled `retrospective: true` with
      `belief_measurements: []`. The reader declines that file.
    - The read-only run over trials 0-1505 (14 windows) found 48 re-proposals: 48 of 216 keyed trials and
      48 of 1366 trials overall. This matches the AP-53 planner-fold replay.
    - The one-off 133/1372 counted numeric trials, which this key excludes. It stays a non-gating
      observation.
  - Remaining trigger: an AutoPilot restart on orchestrator main (already due for AP-53/AP-55/W3), then the
    first closed window.

## VB-KBRAG-QLEN — KB-RAG live query-length telemetry (filed 2026-09-16, sub-tooling)

- [x] **VB-KBRAG-QLEN-W — wire the write side and the projection at instrument-creation time**
  (`internal-kb-rag.md` H2). ✅ 2026-09-16
  - Producer: orchestrator `32336445` on branch `sub/tooling-orch-20260916`, merged at `370dc715`. `kb_rag.query()` appends one
    UNTRUNCATED query token count per live query. `query_length_report.py --out` persists
    producer-authored `belief_measurements` rows, per (encoder, cap, convention) group, for over-cap rate,
    p50, p95 and max.
    - These rows cite no protocol, so they are OBSERVATIONS.
    - `metric_direction` is recorded by the producer.
    - The attestation is the log path plus the exact byte prefix read. The prefix sha256 is carried in
      `extra`, never as a whole-file digest.
    - An empty log yields no rows.
  - Adapter: root `039a4f3b` on branch `sub/tooling-root-20260916` (merged at `719ac638`), `scripts/vidya/adapters/kb_rag_query_length.py`
    plus `tests/vidya/test_kb_rag_query_length_adapter.py`: 12 passed, 1 skipped. The skip is the
    live-producer drift guard, which skipped until the producer merged. Run by hand against the branch
    producer, it passes. It projects only; no grading rule was added.
- [x] **VB-KBRAG-QLEN-R — wire `cli.py ingest` for persisted reports once the producer branch merges.**
  ✅ 2026-09-16 — `cli.py ingest kb-rag-qlen` (VB-WIRE-1, `sub-vidya-wire`, root merge `87109bb2`).
  The first real tuples need live traffic after the merge, then a `query_length_report.py --out` snapshot.
  Until then the adapter has no corpus. That is expected, not a gap.

## VB-EVCONF2 — eval-tower confidence-source calibration axes (filed 2026-09-16, sub-evconf2)

- [ ] **VB-EVCONF2-CAVEAT — attach a speculative-decoding caveat to every belief or citation built on
  the E7c or EV-4c calibration numbers** (filed 2026-09-16, sub-evconf2-probe). Both runs took
  token-probability confidence from servers with `draft-mtp` on:
  - E7c: gemma-4-26B-A4B `draft_max=2`.
  - EV-4c: frontdoor Qwen3.6-35B-A3B-MTP `draft_max=4`, plus worker_general gemma MTP.

  llama.cpp reports p=1.0 for draft-accepted tokens. The effect differs by run:
  - E7c is visibly saturated: 1528/1684 and 1485/1628 rows have confidence ≥ 0.999999.
  - EV-4c is not saturated (0/820 and 2/817), so its contamination is real but unmeasured.

  Scope: any `intake-*`/wiki/handoff claim, or a future adapter tuple, that cites math ECE
  0.2114/0.2199 and AUROC 0.4013/0.4114, or code ECE 0.2532/0.3216 and AUROC 0.6337/0.5751, as
  calibration evidence. Carry them as `spec-on, confidence void pending the EV-CONF-2 A-specoff arm`.
  Where each is quoted is listed in `progress/2026-09/2026-09-16-sub-evconf2.md`. Do NOT edit P-CAL
  or `MEASUREMENT.md`: that amendment is human-only. Its decision-capable uses (RLVR code
  calibration, EV-5/EV-7 verifier promotion) currently gate on the EV-4c baseline.
  - 2026-09-16 (`sub-pcal-ratify`): the caveats OUTSIDE the trust boundary landed (root `fbd40fec`, merge
    `17619015`: ESC-7 draft, wiki `benchmark-methodology.md`, CURRENT-CAMPAIGN pointer, ledger caveat rows).
    Box stays open for the P-CAL amendment itself (operator option (a)), which is prepared at root `17619015`
    (`scripts/operator/run_pcal_ratify_20260916.sh`) and waits for the operator to run it.

## SC84 — VB-VGPR-STATIC: static compile-sweep register stats (filed 2026-09-15 as SC76)

*Renumbered 2026-09-16 (sub-vidya-wire): `SC76` was allocated twice on 2026-09-15. The
claim_anchor re-verifier (S3-VID-02, above) keeps SC76, since SC77-SC80 and the research-intake
skill cite it.*

Source: zero-GPU reads of per-kernel register allocation (`.vgpr_count`, `.vgpr_spill_count`,
`.sgpr_count`) from the AMDGPU `.note` of compiled gfx90a device objects, produced by compile-flag and
pragma sweeps (first run: `artifacts/gpu-aux-baselines/a10_iq2_vgpr_compiler_ab_20260915.md`, research
intake-1398). They gate the latent compile-control arm (autokernel-research-loop AK-QL-7/AK-QL-8) and are
OBSERVATION grade: register counts, not throughput. Source row added to `scripts/vidya/adapters/README.md`.

- [ ] **SC84 (VB-VGPR-STATIC) — wire static compile-sweep register reads on the WRITE side** before AK-QL-7/AK-QL-8 run: each read emits a ClaimTuple (source commit, toolchain id, flag/pragma set, kernel symbol, vgpr/spill/sgpr, OBSERVATION grade); no new grading rule.
- [ ] **SC84a — widen the SC84 tuple for INF03-REGAUDIT-1 (intake-1823/1826).** Add agpr_count, accum_offset,
  in-hot-loop spill reloads, in-loop v_accvgpr_read/write and the toolchain's MFMA-form regime (ROCm 6.2 rule vs
  #159493 default) to the native record before INF03-REGAUDIT-1 or INF03-AGPR-1 produce governed reads. OBSERVATION
  grade; no new grading rule.
  - Producer landed 2026-09-27: research e603216f (`claim_projection`, schema `epyc.gfx90a.isa_audit.v1`; pre-hook docs emit 0). Root adapter drafted (`adapters/gfx90a_static_register.py`, draft at the session scratchpad `isa-audit/`), not yet wired.
  - PARKED 2026-09-27 (operator): read side wired at root `341fef03` (`scripts/vidya/adapters/gfx90a_static_register.py`, `SOURCE_KIND = epyc.gfx90a.isa_audit.v1`, Source `gfx90a-static-register` in `ingest_sources.py`, `cli.py ingest gfx90a-static-register --path <audit dir>`, 28 tests in `tests/vidya/test_gfx90a_static_register_adapter.py`); nothing ingested — every audit on disk is pre-hook and yields 0 tuples; resume by pulling the shared research checkout to ≥ `e603216f`, running `gfx90a_isa_audit.py audit … --category {BASELINE|CANDIDATE} --source-commit <sha> --json <dir>/audit_<arm>.json` for INF03-REGAUDIT-1 / INF03-AGPR-1 / AK-QL-7/8, then `cli.py ingest gfx90a-static-register --path <dir>`, and tick SC84a on the first governed row.

## SC82 — VB-AK-MAXPERF: champion max-performance serving sweeps (filed 2026-09-16)

Source: the `serving.calibrate_floor` np sweeps behind the canonical headline serving rates in
`docs/design/champion-max-performance-20260908.md` (27B: research `data/ak-champion-maxperf-2026-09-08/`;
35B-A3B-MTP: research `data/ak-champion-maxperf-35b-2026-09-08/`, promotion completed at research
`1eb4a89b`). No adapter covers them — `calibrate_floor` writes no `belief_capture`; only `serving.compare`
does. Source row added to `scripts/vidya/adapters/README.md`.

- [ ] **SC82 (VB-AK-MAXPERF) — wire max-performance serving sweeps on the WRITE side** before the next
  sweep (HEAD-3 np=24/32, MTP-27B-1 in `autokernel-champion-aggregate.md`): one producer-authored row per
  np point carrying `recipe_hash`, build/executable/DSO digests, model digest, frozen request digest,
  the per-LAUNCH run vector (n, unit LAUNCH), median aggregate t/s, `_spread` p95 dev/cv, and the
  in-window residency record as a dependency. Strict reader re-derives the median and spread from the
  run vector; `claim_tuple.grade()` decides; no new ladder. The 2026-09-08 27B and 35B sweeps are
  PRE-HOOK and emit zero rows (their per-point JSON lacks build/model/request digests) — never
  reconstruct them on read.

## SC83 — reviewer negative-control FA rate + machine-review envelopes (filed 2026-09-16)

*Allocated as `SC76` in the /workspace working copy, which collided with two existing SC76
allocations; renumbered SC83 on 2026-09-16 (sub-vidya-wire). SC82 is VB-AK-MAXPERF (filed on
`sub/misc-fixes-root-20260916`, now merged).*

Source: `reviewer-typed-artifacts.md` RA-9 and RA-12, landed 2026-09-16 in `epyc-orchestrator` on branch
`sub/reviewer-artifacts-20260916` (not yet merged). The RA-9 dual-gold corpus adds `status: invalid` decoys,
which make a reviewer **false-accept rate** measurable from our own data for the first time. RA-12 binds
every machine review to the exact inputs it was produced against. Filed at producer creation, per the
standing rule. Source row added to [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md).

- [x] **SC83 — wire the negative-control FA rate on the WRITE side before the first decoy corpus is scored.**
      Class `measurement`, **rates only**. A single verdict or objection is categorical and must not be
      forced through `ClaimTuple` (the same call as the headless-audit row). Project
      `gold_annotations.FalseAcceptResult.as_dict()`: numerator, denominator, `lower_is_better`, and the
      unscored and arbitration-excluded ids. A rate whose denominator dropped decoys silently must be refused.
      **Locator = the scoring run (reviewer config × corpus version)**, never the decoy (SC6-HAZARD).
      **Staleness is a write-side filter:** only verdicts whose RA-12 envelope passes
      `review_envelope.check_binding` against current inputs may contribute; a stale verdict emits zero
      rows and is never re-bound on read. Machine objections are `unverified_lead` and never corroboration.
      **Do NOT write a grading rule**: project, and let `claim_tuple.grade()` decide. Until RC-6a merges,
      these are observations and must not be graded as decision-gating.
      Trigger: the first decoy rows plus a scored reviewer run. Zero compute to file.
      *2026-09-16 status:* `gold_annotations.py` and `review_envelope.py` are on orchestrator main, but
      no scoring run persists `FalseAcceptResult` yet. There is nothing to project until one does.
      ✅ 2026-09-17: landed. Built 2026-09-16 (sub-vb-writers) as orchestrator `2789b56d` + `e93edfdb`, which are on
      orchestrator main via `a1a0251a`, plus root `sub/vb-writers-root-20260916`. That root branch reached root main
      only on 2026-09-17, via the `sub-land-vidya` merge (`progress/2026-09/2026-09-17-sub-land-vidya.md`).
      - Writer: `false_accept_record.py` plus `scripts/review/score_false_accept.py` append one self-hashed
        `epyc.reviewer.false_accept_run.v1` line per scoring run to `data/reviewer_eval/false_accept_runs.jsonl`.
        - The RA-12 filter runs BEFORE scoring. Stale verdicts are listed with their reasons and counted as
          unscored.
        - The endorsement is read only from the signed body.
        - A run that mixes reviewer configs is refused.
        - A stale verdict on a decoy awaiting arbitration is listed in `stale_excluded`, not `stale`
          (Fable review fix). The reader checks it against `excluded_for_arbitration`.
        - `n_decoys == scored + unscored + excluded` is checked before the line is written.
        - A run with no scored decoy writes no row.
      - Reader: `adapters/reviewer_false_accept.py`, dispatched as `cli.py ingest reviewer-fa`. It refuses a
        dropped denominator, a re-bound stale id, edited lines or rows, and any `protocol_id`. It carries input
        decay as `attestation_present=False`. The shared ladder grades each row `Judged/Located`.
      - Tests: orchestrator 7; root 9, including a live cross-repo run of writer → CLI → ingest → tuple.
      - Backfill: none possible, because no decoy corpus exists.
      - Remaining trigger: the first decoy corpus plus a scored reviewer run, then `cli.py ingest reviewer-fa`.

## SC85 — OCC-1 optical-compression runs (filed 2026-09-16)

Source: `optical-context-compression.md` OCC-1. The harness is `epyc-inference-research`
`scripts/benchmark/occ1/` (branch `sub/occ1-20260916`), and it compares bitmap frames with raw text on
the served Qwen3-VL-30B-A3B reader. The source row is in `scripts/vidya/adapters/README.md`. The hook
was filed and built before the first GPU run, so that run will not fall in a pre-hook era.

- [x] **SC85 — wire OCC-1 on the WRITE side, plus a strict reader.** ✅ 2026-09-16 (both sides on origin/main: root `1d5f5314`, research `2f053f61` + `e2c48c13`) Root side (branch
  `sub/occ1-root-20260916`): `adapters/occ1_optical_compression_capture.py` (writer and `validate_row`),
  `adapters/occ1_optical_compression.py` (reader), the `cli.py ingest occ1` source, and
  `tests/vidya/test_occ1_optical_compression_adapter.py`. The rows per arm are F1, EM, the paired
  F1 delta with its CI and verdict, and the prompt-token ratio. The locator is the run, a VOID run is
  refused, and `claim_tuple.grade()` decides (no new ladder). The research side is `run_occ1.py
  report`, which writes the sidecar by default. Both sides still need to be merged.
- [ ] **SC85b — codify the OCC protocol** under `measurement/protocols/`, and have the runner pass
  `--protocol-id`. Until then, every OCC-1 tuple is `Judged/Located`.

## VB-WIRE — `cli.py ingest` wiring and reconciliation of the 2026-09-16 filings (sub-vidya-wire)

- [x] **VB-WIRE-1 — give every file-shaped adapter an `ingest` name.** ✅ 2026-09-16
  - `scripts/vidya/ingest_sources.py` is a dispatcher, not a grader. It uses each adapter's own
    `native_rows` and its registered projection, and emits through `claim_tuple.to_frames`.
  - 15 names: `kb-rag-qlen` (closes VB-KBRAG-QLEN-R), `inf70-arms` (SC75), `contention-gate`,
    `contention-matrix`, `beam`, `tulving`, `chat-template-ab`, `memento-lora`, `pareval`,
    `eval-tower-band`, `fanout-outcome`, `research-sweep-g1`, `research-sweep-g234`,
    `autopilot-journal`, `sealed-manifest`. `dflash2_experimental_runtime` is left out on purpose,
    with the reason in `UNWIRED`.
  - `tests/vidya/test_ingest_sources.py` (22 pass): each source ingests a fixture through the CLI.
    Each ledger grade equals `claim_tuple.grade()` of the adapter's own projection.
  - Real-corpus dry runs on 2026-09-16:
    - `contention-gate`: 382 rows.
    - `fanout-outcome`: 5 rows.
    - `sealed-manifest`: 6 rows; 8 manifests are unsealed and declined.
    - `contention-matrix`: 6 runs, all pre-hook and declined.
    - `inf70-arms`: 0 sidecars.
    - `autopilot-journal`: 0 measured rows.
  - Also ported from the /workspace working copy, where both producers are already on orchestrator
    main: AP-55 `infra_fingerprint`/`comparability` in `autopilot_journal.py` and the RTG-35
    foreign-process gate in `contention_matrix.py`. Both are carried, never graded.
- [x] **VB-WIRE-2 — SC75's producer does not call the hook yet.** `agents/harness1/arm_hot.sh` and
  `arm_cold.sh` under `/mnt/raid0/llm/tmp/inf70`, which are not in git, never invoke
  `inf70_serving_arm_capture.py`. Until they do, `ingest inf70-arms` will keep reading zero sidecars.
  Add the call at arm end before the next serving-harness arm. Owner: the INF-70 harness session.
  ✅ 2026-09-16 (`sub-own`, operator-directed): root `b57b1efb` promotes the harness and everything it
  sources to `scripts/inf70/harness1/`; `3c5a4b30` + `b68ce8bf` wire the capture. The scratch copies got
  the same edit. 7 tests in `tests/vidya/test_inf70_harness_sc75_hook.py`, including a fixture arm
  ingested end to end.
  - The first real arm still needs two things. `gguf_sha256` must be supplied (`$GGUF_SHA256` or a
    `<gguf>.sha256` sidecar); it is never hashed inline, because hashing would refill the page cache
    the eviction just emptied.
  - The scratch copies resolve the writer from `/workspace`, which lacks it until that checkout
    reaches origin/main. Until then their capture fails loudly, and the measurement is unaffected.

Status of the 2026-09-16 filings, as of origin/main `c57b0b6c`. VB-KBRAG-QLEN, VB-PRB-T4,
VB-REVIEW-F1, VB-SL2-STEPS, VB-HARNESS-AUDIT, VB-AP53-RATE and VB-EVCONF2 are so far written only in
the /workspace working copy of this file. Their owners commit those boxes.
*Update 2026-09-16 (wrap-up pass 2):* those boxes are now on origin/main (VB-GPU-PREP section and the
sections after it). VB-EVCONF2's producer merged (orchestrator `d8b915ee`/`88a2902d`, root `1e1de5fb`).

| task | adapter exists where | ingest wired | remaining |
|---|---|---|---|
| VB-KBRAG-QLEN | origin/main `kb_rag_query_length.py` | yes, `kb-rag-qlen --path <report.json>` | first traffic, then a `query_length_report.py --out` snapshot, then ingest |
| SC75 / VB-INF70-ARMS | origin/main `inf70_serving_arm{,_capture}.py` | yes, `inf70-arms` | none: VB-WIRE-2 wired (root `3c5a4b30`); first real arm pending |
| VB-PRB-T4 | root `tale_budget{,_capture}.py` (ported 2026-09-16, branch `sub/runner-adapters-20260916`) | yes, `tale-budget --path <out dir>` | none: the first run landed (24 rows), and the driver is on research main at `0b295a25` with an `EPYC_ROOT` loader (2026-09-17) |
| VB-REVIEW-F1 | root `review_f1{,_capture}.py` (ported 2026-09-16, branch `sub/runner-adapters-20260916`) | yes, `review-f1 --path <out dir>` | none: the driver merged (`59d0bc73`), the first run landed (6 rows), and its loader uses `EPYC_ROOT` since research `0b295a25` (2026-09-17) |
| VB-SL2-STEPS | n/a (a decision) | n/a | still a decision; the serving-belief reader `autokernel_legacy_serving.py` IS on origin/main now |
| VB-EVCONF2 | none | no | `confidence_source_compare.py` is on unmerged orchestrator `sub/evconf2-20260916` |
| VB-HARNESS-AUDIT | none | no | decision (a)/(b)/(c); the findings are handoff prose with no machine-readable record to project |
| VB-AP53-RATE | origin/main `autopilot_reproposal_rate.py` (landed 2026-09-17) | yes, `autopilot-reproposal-rate` | restart AutoPilot on orchestrator main, then wait for the first closed window |
| SC83 (was SC76, reviewer FA rate) | origin/main `reviewer_false_accept.py` (landed 2026-09-17) | yes, `reviewer-fa` | the first decoy corpus plus a scored reviewer run |
| VB-MHS-GATES | none | no | producer is on unmerged orchestrator `sub/autopilot-safety-20260916` |
| VB-GPU-RUNNER | none | no | the sweeps (INF-62 SL-1/SL-5, DF2-6, §5 MoE batched, ERNIE, INF-61) are pre-hook; each needs a producer hook (`calibrate_floor`, batched-bench, sd-server and np-grid wrappers) |

## SC86 — HS-4 OpenCode-shell runs (filed 2026-09-16)

- [x] **SC86 — wire HS-4 shell runs on the WRITE side**: each run emits a ClaimTuple carrying the harness pin, plugin and config hash, Harness Card version, `x_memory` arm, and the HS-14 column set; locator = run. Must land before the first measured shell run (HS-4 P0.4). Design: `docs/design/hs4-shell-and-orchestrator-features-20260916.md` §4 (P0.5). ✅ 2026-10-29 (audit: Box text: "tick condition is met"; adapter opencode_shell_run*.py on main, commit 934317b2f (SC86 write-side hook + strict reader); scripts/vidya/adapters/opencode_shell_run_capture.py exists.) [no-belief: audit-reconciliation]
  Status 2026-09-16 (`sub-sc86`, branch `sub/sc86-20260916`, unmerged): **adapter ready, producer pending (HS-4 P0.4 driver).** `adapters/opencode_shell_run_capture.py` (run-sidecar schema `epyc.hs4.opencode_shell_run.v1`, writer, `validate_row`), `adapters/opencode_shell_run.py` (strict reader), `cli.py ingest opencode-shell`, and `tests/vidya/test_opencode_shell_run_adapter.py` (32 pass, including writer → `cli.py ingest` → tuple). Rows: the four HS-14 columns, re-derived from recorded counts; refused on a missing pin or config hash and on pre-hook or backfilled runs. The P0.4 driver must write `opencode_shell_run.json` and call the writer at run end; that call is the HS-4 P0.4 owner's. Tick this box when the branch is merged and the driver calls the writer (the SC85 precedent).
  - 2026-09-17 (`sub-hs4-mcp`): the P0.4 driver now calls the writer. `scripts/harness/hs4_p04_acceptance.py verify` writes the run sidecar and `attempts.jsonl`, then calls `write_belief_measurements`, and its tests run `validate_run_sidecar`/`validate_row` on the output. The adapter is on main (`934317b2`). The tick condition is met, so the SC86 owner can tick this box.
- [ ] **SC86b — codify the shell-run protocol** under `measurement/protocols/` (task suite, trials per task, serving at production `enable_thinking`, the HS-14 column definitions), and have the P0.4/HS-14 driver pass `protocol_id`. Until then, every OpenCode-shell tuple is `Judged/Located`.

## SC88 — AutoKernel fresh seeded operation correctness (filed 2026-09-17)

- [ ] **SC88 — wire fresh seeded operation correctness on the WRITE side before first real invocation.** The opt-in producer emits a self-hashed ClaimTuple-shaped receipt joining arm ID, selected candidate source/binary and trusted instrument digests, serving recipe, suite seed, console evidence, and per-case reference/property residuals. `reference_valid`, `property_only`, and `oracle_unavailable` retain their exact provenance; CPU candidate-local references cannot be upgraded to independent anchor correctness. Strict read-side projection accepts only post-hook receipts and delegates grading to `claim_tuple.grade()` without a new ladder. Report-only: no ranked-time or promotion authority. Source: `autokernel-research-loop.md` AK-integrity pack (intake-1454#record).

## SC89 — AutoKernel observed plateau diagnostic provenance (filed 2026-09-17)

- [ ] **SC89 — bind the read-only AK-plateau reporter on the WRITE side before its first real-store report.** Author a self-hashed ClaimTuple-shaped receipt with immutable input experiment row IDs/payload digests, exact anchor epoch/metric/direction/surface/recipe/request grouping, reporter version/parameters, and output digest. The strict reader delegates grading to `claim_tuple.grade()` and cannot infer a causal policy improvement, cost-credit score, or champion gain from an observed historical trajectory. Source: `autokernel-research-loop.md` AK-plateau pack (intake-1440#record, intake-1446#record).

## VB-AK-LINEAGE — AutoKernel code-lineage diagnostic capture (filed 2026-09-17)

- [ ] **VB-AK-LINEAGE — finish prospective AutoKernel lineage source/outcome binding before the first real diagnostic run.** The default-off source/patch capture helper and offline line-level detector do not themselves authorize a run. At authoring, the producer must mint a durable attempt ID, bind it to the original outcome row, capture immutable parent/child source bytes and patch, and export verified `programs.jsonl`/blobs/capture receipts. Add strict read-side ClaimTuple projection of producer-authored diagnostic measurements; never backfill from overwritten `<mechanism>.<lane>.patch` paths or tree hashes. No live search-policy or promotion authority. Source: `autokernel-research-loop.md` AK-lineage diagnostics (intake-1451#record, intake-1458#record, intake-1442#record).

## VB-AK-HISTORY — AutoKernel closed-history replay capture (filed 2026-10-20)

- [ ] **VB-AK-HISTORY — Keep AK-HR-1 and AK-HR-2 retrospective and wire the prospective AK-HR-3 fields on the WRITE side before their first post-change run.** The census and diagnostic read historical stores that have no producer hook, so they emit zero ClaimTuples and are reported as descriptive census (the VB-TD-21-CENSUS stance). The fields AK-HR-3 adds (attempt-to-call key, cumulative budget, failure class, stage seconds, typed knob descriptor) are written natively with self-hashed receipts and projected through `ClaimTuple` and `claim_tuple.grade()` only (no new ladder, no backfill). Add the candidate source row to `scripts/vidya/adapters/README.md` with this plan's text now; the ROOT reader is not required before AK-HR-3 lands.
  - 2026-10-21 audit-ticks verification (NOT ticked): source row (`scripts/vidya/adapters/README.md:275`) and `ak_history` carrier landed, but the task is to wire the fields on the WRITE side before the first post-change run. Remaining: the research-loop producer call (epyc-inference-research, INF-73 loop owner) is not wired, and no post-change AK-HR-1 re-run has confirmed the fields project through `claim_tuple.grade()` with self-hashed receipts.
  - 2026-10-21 EXECUTOR NOTE (noninf-vidya; box NOT ticked). Carrier `scripts/vidya/adapters/ak_history.py` + `_native_sidecar.py` + `cli.py ingest ak-history`, tests `tests/vidya/test_prospective_ab_carriers.py`. Per-trial self-hashed row over the AK-HR-3 field set (closed; unknown fields refused), receipt file re-hashed on read, graded by `claim_tuple.grade()` only. AK-HR-1/2 stay retrospective (zero tuples). NOT done: the research-loop producer call (epyc-inference-research, INF-73 loop owner) and the first post-change run.
  - 2026-10-20 (checkbox NOT ticked, factual): source row added at `scripts/vidya/adapters/README.md:275`; AK-HR-3 nullable fields written natively (research `fef9b11ae`, `578e546ea`, `6e9ed20aa`); open: re-run AK-HR-1 on a post-change store and confirm the fields project through `claim_tuple.grade()` with self-hashed receipts.

## VB-NIAH-E1A — RLM E1 NIAH dual-scored arms (filed 2026-09-16, sub-e1a)

Source: `rlm-contested-claims-self-evaluation.md` E1/E1a. The scorer is epyc-inference-research `scripts/benchmark/niah_scorer.py` (branch `sub/e1a-niah-20260916` `d8fab068`, pending merge). The source row is in `scripts/vidya/adapters/README.md`. No E1 arm has run, so nothing is pre-hook.

- [ ] **VB-NIAH-E1A — wire E1 NIAH arms on the WRITE side before the first E1 run.** One self-hashed ClaimTuple per arm (Base / D1 / D2) with strict and lenient accuracy together, `format_gap`, `scorer_id`, n/undecidable counts, reps, and latency and tokens as separate fields; refuse a row with only one accuracy. Locator = run × arm. Adapter projects; `claim_tuple.grade()` decides (no new ladder).

## VB-TD-21-CENSUS — structured-output consumer audit capture (filed 2026-09-24)

- [ ] **VB-TD-21-CENSUS — add a prospective, source-pinned evidence writer before the next consumer census or re-audit.** Capture consumer identity, parse/constraint path, failure disposition, and endpoint capability in a self-hashed native record; the 2026-09-24 static census/audit stays retrospective and emits zero tuples. Project eligible fields through `ClaimTuple` and `claim_tuple.grade()`; no backfill, new grading rule, or conversion/promotion authority. Source row: `scripts/vidya/adapters/README.md`.

## VB-FW-1 — GUI-authored fuzzy workflows (filed 2026-09-17, FW-4)

- [ ] **VB-FW-1 — wire the write side before the first GUI-authored workflow run.** Source row added to
  [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md) the day the GUI was designed, not the
  day it runs: the read side cannot be retrofitted, so a run that executes before the hook exists can never gate a
  decision. Each run of a workflow document emits **one** self-hashed `ClaimTuple` carrying: the workflow-document
  hash (the canvas is the unit of identity, not the session), the node types actually executed, each fuzzy node's
  model pin **and** question catalogue (both, because FW-1's L2 lift is per `(model pin, catalogue)` — a calibration
  record keyed on one of them is unusable), and the per-gate outcomes with their rejection destinations. A fuzzy
  node's confidence is **recorded and never read by an edge** (FW-1 L2), so the tuple carries it as evidence, not as
  a gate input. **Project, do not grade:** the adapter emits the tuple and `claim_tuple.grade()` decides — no new
  ladder (`docs/design/vidya-pilot-spec.md` §4.7). Lands with the FW-2 executor; the adapter has nothing to read
  until then, which is exactly why the row is filed now. Owner: whoever builds the FW-2 executor.
  Locator = run. Zero inference to author.

## VB-AK-HELDOUT — AutoKernel CPU held-out confirmation (filed 2026-09-18)

- [ ] **VB-AK-HELDOUT — capture the held-out serving comparison and integrity-gate disposition at the write side.** Research `9eee67c1` introduced `epyc.autokernel.heldout_serving_confirm.v1` as plain per-candidate JSON before the first GLM v27 confirmation. Add a producer-authored, self-hashed ClaimTuple binding exact attempt/tree, distinct public and held-out request digests, model, recipe, both executable/build identities, instrument, separately calibrated floor, paired raw vectors, units and actual veto outcome. A strict reader must reopen the native bytes and project them through `claim_tuple.grade()`; no new ladder and no champion-promotion warrant. Pre-hook plain records remain historical evidence but emit no graded row. Source row: `scripts/vidya/adapters/README.md`.

## VB-KVQ-V10 — MI210 KV-quant decode sweep at v10 (filed 2026-09-22)

- [x] **VB-KVQ-V10 — author the read-side adapter for the v10 KV-quant sweep.** ✅ 2026-09-25. The WRITE side is already
  wired (research `scripts/benchmark/kv_quant_27b_v10_sweep.py`, schema
  `epyc.vidya.kv_quant_27b_v10_capture.v1`, sidecar `belief_measurements.jsonl` beside `summary.json`,
  self-hashed `row_sha256`, shared `validate_row()`), filed BEFORE the sweep runs — the read side cannot be
  retrofitted, and `benchmarks/results` is the standing proof of what that costs. Author
  `scripts/vidya/adapters/kv_quant_27b_v10.py`: `@register("kv-quant-27b-v10-measurement")`, import and
  re-run the producer's `validate_row()` (pinning the producer file's sha256) so a mutated or pre-hook row is
  refused and the WHOLE file voids to zero rows; re-hash `scored_path` at the adapter boundary to set
  `attestation_verified`; use `attestation_locator`, because the artifact lives in the research repo outside
  `REPO_ROOT` and `attestation_path` must stay empty; and add a `Source(...)` row to
  `scripts/vidya/ingest_sources.py` — wiring the ingest name IS the write side being finished.
  **Project, do not grade:** `claim_tuple.grade()` decides and the `measurement` ladder is already registered
  (`docs/design/vidya-pilot-spec.md` §4.7); the registry refuses a second. Carry the five cautions from the
  source-table row verbatim, especially K-and-V-separately and the fixed `-fa on` — this host measured a 1.52x
  swing from that flag alone, so a KV ratio quoted without it is a flash-attention number.
  Locator = run x arm x depth x metric, never a replicate file.
  Owner: the session that runs the sweep in the operator stack-down window.
  The strict reader is `scripts/vidya/adapters/kv_quant_27b_v10.py`; `cli.py ingest
  kv-quant-27b-v10-measurement` and the read-only `kvq_planner_context.py` are wired. The
  AutoPilot planner includes a separate advisory KV-quant block; the active AutoKernel
  `loop/run.py` → `AgentPlanner.propose()` path reads the same bounded context for the
  matching Qwen3.8-27B-Q8_0 GPU target only. The existing 2026-09-22 run
  directories contain zero `belief_measurements.jsonl` sidecars, so the real-corpus dry run
  projects zero rows and the planner reports unavailable. Historical runs are not backfilled.
  The 2026-09-25 fixture round-trip and focused tests pass (127 across the adapter, ingest and
  shared ClaimTuple suites; 58 AutoPilot bridge/prompt tests).
- [x] **VB-KVQ-V10-AP-RECEIPT — bind the AutoPilot planner's KV-quant evidence to its decision record.** ✅ 2026-09-25.
  The Vidya lookup emits a structured run/frontier/fold-hash/12-claim manifest with its text;
  AutoPilot passes one snapshot to its prompt and existing `planner_coordinator` archive row
  with the trial ID. The rationale may declare exact `vidya_claim_ids`; the archive counts
  only IDs actually shown, and clears reliance when an action is blocked or substituted
  without a matching revised rationale. Invalid manifests fail closed. Focused validation:
  192 orchestrator and 8 Vidya tests; no live KV-quant tuple exists yet.
- [ ] **VB-KVQ-V10-INGEST — ingest the first post-hook complete v10 KV-quant sweep.** After the
  owning stack-down session produces its new sidecar, run `cli.py ingest
  kv-quant-27b-v10-measurement`, verify 12 rows from one run reach the fold, and check that the
  AutoPilot planner block names the run, grades and bench-only cautions. No old summary or
  pre-hook run may be backfilled into a ClaimTuple.
- [ ] **VB-KVQ-V10-RECONSIDER — flag archived AutoPilot decisions that declared reliance when their Vidya support is corrected or retracted.**
  Use the recorded claim IDs and fold frontier, preserve human promotion authority, and
  distinguish a review prompt from an automatic reversal. Exercise against a synthetic
  correction before enabling the live path.

## VB-AK-BELIEF — generic belief-kernel reader for the AutoKernel planner (filed 2026-09-25, main-ak-seat)

**Ownership (2026-09-25).** The operator directed a GENERIC belief-kernel reader for the AutoKernel planner, not a
hypothesis-specific seed, and moved the KV-quant planner wiring to main-ak-seat (workspace-8d agreed). Codex owns
AutoPilot and asked main-ak-seat to own the AutoKernel side: code stays in research; any change to shared
`/workspace/scripts/vidya/*` is coordinated with Codex first; no grading rule and no promotion authority;
orchestrator `scripts/autopilot/` is left alone. **Every task below that touches root `scripts/vidya/` needs
Codex's sign-off before it lands** (shared files).

- [ ] **VB-AK-BELIEF-1 — land the generic reader after Codex signs off the receipt.** Research
  `lane/belief-reader-20260925` @ `56cb9493` (unmerged; on research main `0555cd2b`): `8b7b8bed` adds
  `loop/belief_context.py` (reader, `epyc.vidya.planner_evidence_receipt.v1` receipts in
  `belief-receipts.jsonl`, optional `relies_on_claims` in `HYPOTHESIS_SCHEMA`, reliance = declared ∩ presented),
  `--actor-belief-context` (default on) and the post-sweep ingester `scripts/benchmark/kv_quant_27b_v10_ingest.py`;
  `56cb9493` retires the KV-quant-specific block (`8ba5ca61`, on research main via `0555cd2b`), which printed a
  section, including an "inapplicable" line, into every planner prompt. The receipt proposal is
  `/mnt/raid0/llm/tmp/vidya-planner-receipt-proposal-20260925.md`, relayed to Codex via the operator. Merge only
  between campaign runs, and not into run 10's frozen worktree. Also apply the proposal's §7 consumer-table row
  to `scripts/vidya/adapters/README.md` (Codex coordination). Acceptance: Codex sign-off recorded, the lane
  merged, and one planner call writes a receipt with `evidence_status` set.
- [x] **VB-KVQ-V10-DICT — BLOCKING: the producer writes stats dicts where the root adapter requires numbers.**
  `kv_quant_27b_v10_sweep.summarize_cell` returns `prompt_tokens`, `kv_k_mib`, `kv_v_mib` as `{n, median, mad}`,
  and `belief_capture_rows` copies them into `extra.arm.prefill_tokens_measured` and
  `extra.kv_buffer_{k,v}_mib`. Root `scripts/vidya/adapters/kv_quant_27b_v10.py` `_check_row` requires plain
  numbers there (~L81-84), so the first real complete sweep's sidecar would be refused wholesale and nothing would
  reach the ledger. Both test suites miss it: root's fixture hand-builds scalars, and the producer's test asserts
  the dict shape. Recommendation (proposal §4.6, option c): the root adapter accepts a stats dict with a finite
  numeric `median` now, before anyone runs the sweep; the producer emits medians and `validate_row` enforces
  numbers in its next revision, with the `PRODUCER_SHA256` bump. Replace root's fixture with the producer's real
  `summarize_cell` output. The research test `test_the_producers_native_summary_shape_is_ingestable` is a strict
  xfail that flips when this is fixed. Blocks VB-KVQ-V10-INGEST. Needs Codex coordination (root adapter).
- [x] **VB-APPLICABILITY — persist an applicability scope in the ledger.** `claim_tuple.to_frames()` drops
  `ClaimTuple.extra`, where adapters keep model/quant/backend/device, so a reader cannot match a claim to a target
  from the ledger alone. Add an optional `ClaimTuple.applicability` (`{model_file, quant, backend, device,
  context_tokens, kernel}`), filled from native fields only and emitted as a CONDITIONAL key in the
  `source_observed` assertion, so frames without it stay byte-identical. Add `run_id` + `run_expected_keys` on the
  same key, so both planners apply one completeness rule. Until it lands, the AutoKernel reader matches through a
  declared per-source scope table with a producer pin per entry. Needs Codex coordination (shared contract).
- [x] **VB-INGEST-IDEMPOTENT — make a repeated ingest a no-op.** `ingest_sources.ingest()` appends every projected
  frame, and frame ids include `created_at`, so a second ingest duplicates evidence. The AutoKernel post-sweep
  ingester guards this caller-side (deterministic `as_of` = the sidecar's `emitted_at`, a pre-check of the claim
  ids, refusal of partial ledger state, a run-dir lock). Add an `--only-new` mode (skip frames whose claim id
  already has live evidence) to root `ingest_sources`. Acceptance: ingesting the same sidecar twice leaves the
  ledger's frame count unchanged. Needs Codex coordination (root file).
- [ ] **VB-AK-RELIANCE-REVIEW — flag AutoKernel proposals whose relied-on claims are corrected or retracted.**
  The AutoKernel analogue of VB-KVQ-V10-RECONSIDER: join a claim's correction or retraction to every experiments
  row carrying it in `relies_on_claims`, and raise a review flag, never an automatic reversal. Depends on
  VB-AK-BELIEF-1. Acceptance: a synthetic retraction flags exactly the rows that relied on it.

## VB-VRAM-1 — MI210 per-process VRAM decomposition (filed 2026-09-23)

- [ ] **VB-VRAM-1 — author the read-side adapter for the VRAM headroom probe.** The producer already
  emits a self-describing `epyc.vram_headroom_probe.v1` report (`scripts/measure/vram_headroom_probe.py`,
  epyc-root `e9ecdda6`) and it has RUN TWICE, so the write side exists and the read side is the gap.
  Author `scripts/vidya/adapters/vram_headroom.py`: `@register("vram-headroom-measurement")`, re-hash the
  report at the adapter boundary, use `attestation_locator` (reports live in the research repo, outside
  `REPO_ROOT`), and add a `Source(...)` row to `scripts/vidya/ingest_sources.py`.
  **Project, do not grade** — `claim_tuple.grade()` decides and the `measurement` ladder is registered.
  Carry all five cautions from the source-table row verbatim, especially: `transient_headroom_gib` is a
  FLOOR for the workload named in `exercised` and must never be generalised; a `NOT TESTED` fragmentation
  verdict is not `absent`; and **the first 2026-09-22 run is INADMISSIBLE** (its driver failed silently
  after cycle 1, so its `RATCHET` verdict is an artifact of cycle marks landing in idle time) — the
  admissible run is the six-verified-cycle one that replaced it.
  Locator = run x metric. Owner: whoever next runs the probe.

## VB-ARCH-CPU-QUAL — architect quality gate, CPU live-serving and GPU (filed 2026-09-23)

- [ ] **VB-ARCH-CPU-QUAL — author the read-side adapter for the architect quality gate, covering BOTH the
  CPU live-serving arms and the existing GPU control arms.** The WRITE side is already wired on both:
  `v7_quality_gate_runner.py` emits producer-authored rows under `epyc.v7_quality_gate_runner.accuracy.v1`
  via `v7_quality_gate_beliefs.attach_accuracy_beliefs`, EMBEDDED in the run's own `result.json` as
  `belief_measurements` + `belief_attestation`. SC32 wired the GPU forwarder 2026-08-26 and SSU-F2 wired
  the CPU forwarder 2026-09-23; **neither has ever been ingested** — there is no `Source("quality-gate", …)`
  in `scripts/vidya/ingest_sources.py` and no adapter. One adapter covers both; they are one schema.
  Author `scripts/vidya/adapters/v7_quality_gate.py`: `@register("v7-quality-gate-accuracy")`, import and
  re-run the producer's own validation (pinning `v7_quality_gate_beliefs.py`'s sha256) so a mutated or
  pre-hook row is refused and the WHOLE file voids to zero rows; re-hash the `attestation_path` result.json
  at the adapter boundary to set `attestation_verified`; add the `Source(...)` row.
  **Project, do not grade** — `claim_tuple.grade()` decides; the `measurement` ladder is registered.
  Two cautions are load-bearing enough to restate: **`instrument_class` must reach the tuple** (CPU arms are
  `serving`, GPU arms an owned bench; flattening them manufactures exactly the cross-class comparison the
  measurement constitution forbids), and **truncation must be projected next to accuracy** — on 2026-09-23
  Flash-Next scored 0.5650 mmlu_pro against the retired 122B's 0.6450 at an identical cap while truncating
  46/200 against the incumbent's 0, so the accuracy alone reads as an 8-point regression the decomposition
  does not support.
  Pre-hook runs emit zero rows and are NEVER retrofitted. Locator = arm x suite.
  Owner: whoever next touches either architect bench.

## VB-MFVBS-1 / VB-EVALDISC-1 — two orchestrator analysis sources (filed 2026-09-24)

- [x] **VB-MFVBS-1 — author the read-side adapter for the verify-before-stop measurement.** Producer:
  orch `scripts/analysis/mf_vbs1_verify_before_stop.py` (`86471b1f`), deterministic JSON with n,
  denominator and Wilson CI per rate. `@register("verify-before-stop-measurement")`, re-hash at the
  boundary, `Source(...)` row in `scripts/vidya/ingest_sources.py`. Carry the three source-table cautions
  (one day / one role / one voluntarily-stopping task; the rider never asks for verification; forced stops
  outside the voluntary denominator). Project, do not grade.
- [x] **VB-EVALDISC-1 — author the read-side adapter for the eval-suite discriminability audit.**
  Producer: orch `scripts/analysis/eval_suite_discriminability.py` (`eval_suite_discriminability_report.v1`).
  Locator = report × suite × metric. Reports older than orch `8a829233` must have their
  `run_unstable`/`brittle`/flip_rate claims refused wherever an input run was error-dominated (RTG-16);
  their MDE/pass_rate stay admissible. Project, do not grade.

### Prospective native provenance before the two analysis adapters — 2026-10-06

Current APP e2d3a670 source review finds no read-side Source registration for either producer. The MF aggregate drops input content/source identities; EvalDisc v1 records paths but no byte/source binding. Deterministic historical JSON does not supply a missing original warrant. The existing caution/direction/denominator rules remain; no new ladder or historical identity reconstruction is authorized.

- [x] **VB-MFVBS1-PROV — capture verify-before-stop report provenance at its native writer.** Bind exact parsed input bytes and preserved snapshot/manifest, original report/source schema and revision, stable native record identity and corpus scope before the strict VB-MFVBS-1 adapter. Preserve all metric bodies and denominators; unknown stays unknown. Historical identityless output remains descriptive and is refused for ClaimTuple projection. Validate writer/reader controls in isolated native CI through the existing shared grade only; no actual BEP run or efficacy claim.
- [x] **VB-EVALDISC1-PROV — capture discriminability report provenance at its native writer.** Bind exact selected input bytes/snapshots, original report/source schema/revision and record identity before the strict VB-EVALDISC-1 adapter. Preserve current error filtering, native denominators and metric direction. No lexical ordering of Git hashes or guessed legacy era; missing original identities are refused. Existing observation carrier/shared grade only, no historical backfill or experiment run.

## VB-AK-SEAT — AutoKernel actor-seat efficiency records (filed 2026-09-24, main-ak-seat)

Producer: research lane `lane/ak-actor-seat-20260924` @ `e9495971` (`loop/actors.py` appends
`actor-replies/actor-calls.jsonl` per call; `/mnt/raid0/llm/tmp/ak-seat-ab/driver.py` writes
`result-<arm>.json`). The A/B that gates DS41-C20 is n = 1 per arm with a prompt that differs between
the old plain run and the new arms — recorded as the claim's scope, never as a seat effect. Source-table
row: `scripts/vidya/adapters/README.md`. Project, do not grade.

- [ ] **VB-AK-SEAT-b2 — arm-record producer in the seat A/B driver.** Emit `epyc.autokernel.seat_ab_arm.v1`
  via `build_arm_record` from the driver that OAB-4 (`autokernel-orchestrator-actor-backend.md`) extends:
  `ab_id`/`arm_id`/`category`/`scope`, driver and lane-anchor identity, the schema-valid verdict
  (`template_echo` recorded as itself), per-session export digests with one `root: true`, totals over root +
  scouts; a session whose export fails to parse is not written as v1. Not done now: the live DS41-C20c driver
  (`/mnt/raid0/llm/tmp/ak-seat-ab/driver.py`) must not be edited while its arms run, and both of its arms
  started before `HOOK_SINCE` (12:00Z), so they could not be v1 records anyway. Acceptance: one post-hook arm
  record that `cli.py ingest ak-actor-seat --dry-run` projects with `refused=0`.
- [ ] **VB-AK-SEAT-b1w — fill `server.build_info` and `server.served_model` in the call record.** Both are `null`
  in run 8's line, so a call record cannot say which server build or model answered it. When the backend endpoint
  is a llama-server, read `/props` (`build_info`, `model_alias` / `model_path`) once per actor process and cache
  it. Add `n_ctx` per slot as well: it is 98,304 split vs 196,608 unified on :8083 (RTG-57), and it decides
  whether a reply could be truncated. Keep the v1 contract, or version it to v2 if the fields become required.
  Acceptance: the next campaign call line carries non-null values and still ingests with `refused=0`.
- [ ] **VB-AK-SEAT-b1x — accept the `orchestrator` backend kind (INF-78 OAB-2).** Root side done
  2026-09-25 (`main-ak-seat`, root `lane/ak-seat-vbseat-orch-20260925`, merged to `main`): `BACKEND_KINDS` in
  `autokernel_actor_seat_capture.py` now includes `orchestrator` alongside `codex`/`claude`/`opencode` —
  no new field (`workspace` already carries the `task_root` scope, and the generic "not opencode"
  branches of `_seat` already force a plain, config-less seat for it, same as `codex`/`claude`) — plus two
  new `_server` rules specific to this kind: `endpoint` must be the orchestrator's own loopback base URL
  (never a model-serving port) and `served_model` must stay null (model provenance is the `ChatResponse`'s
  `routed_to`/`role_history`, carried on the sibling `actor_call_metrics.v1` row, not this contract). Tests:
  `tests/vidya/test_autokernel_actor_seat_adapter.py` (46, +13). **Remaining, research side (not done here —
  the owning session applies it):** `loop/actors.py` `_backend()`/`_call_record_v1` (~L822-833) already builds
  a valid `orchestrator`-kind seat/backend/server for every `orch:` call; only root's contract was missing the
  kind, so every orchestrator call today still writes the legacy `v1_refused` line via `_record_call`'s
  `except` branch (~L556-561). Once research vendors this commit (or bumps its `EPYC_ROOT_REPO` pin), that
  branch stops firing on its own — no producer code change needed, only re-vendoring root's module. The one
  actual code edit needed research-side is the test fixture that pins the OLD behavior:
  `scripts/kernel_rnd/autokernel/loop/test_actors.py::OrchestratorBackendKind
  .test_a_schema_valid_reply_parses_and_records_provenance` (~L1536-1541) asserts
  `self.assertIn("backend.kind must be one of", v1["v1_refused"])` and `v1["backend"] ==
  "orchestrator:architect_general@high"` (the pre-hook legacy shape) — replace with a v1 record assertion
  (`v1["schema"] == "epyc.autokernel.actor_call.v1"`, `v1["backend"]["kind"] == "orchestrator"`, no
  `v1_refused` key) once the vendored contract module is current. Acceptance: `cli.py ingest ak-actor-seat
  --dry-run` over a fresh orchestrator campaign call shows `refused=0` and one projected
  `actor_call_wall_s` observation.
  **Research side done 2026-09-25:** research `67cac838` makes the fixture contract-version aware (a v1 record
  under root ≥ `fa8d0fa1`, `v1_refused` under an older root; tested against both). Campaign `EPYC_ROOT_REPO`
  checkouts must be at ≥ `fa8d0fa1` (run 10's is at `117370a8`). Only the acceptance remains: the first real
  `orch:` campaign call (INF-78 OAB-4) ingests with `refused=0`.
- [ ] **VB-AK-METRICS-1 — make `epyc.autokernel.actor_call_metrics.v1` contract-grade, then project it** (filed
  2026-09-24, main-ak-seat, reduced-scope planner build). Producer: research `lane/ak-turns-20260924` `0bf2d7c2`,
  `loop/actor_metrics.py`, which writes a sibling line to `actor-calls.jsonl` just BEFORE each `actor_call.v1`
  line. Source-table row: `scripts/vidya/adapters/README.md`.
  - Today the row has no self-hash, no root contract module and no `call_id` join.
  - [ ] Preserve OAB-21 reasoning provenance in the existing contract/projection: per-step chars, tokens
    and usage/estimate/unavailable source; aggregate usage/estimated/unknown-step counts; explicit estimator
    label when used; decoded includes reasoning, so never add reasoning to decoded twice. Preserve unknown
    evidence as unknown. This extends this source contract; it creates no new ladder or historical warrant.
  - Add a closed schema plus a reference writer and validator in root, beside `autokernel_actor_seat_capture.py`,
    so writer and reader share one definition (the VB-AK-SEAT-a pattern).
  - Carry an explicit join to the v1 record: return the v1 `call_id` from `build_call_record`'s caller path, or
    bind both lines to one shared `call_nonce`.
  - Carry the four cautions from the source row: decoded includes reasoning; totals over novelty-identified
    sessions; absent, never zero, for per-tool latency; `metrics_error` is not zero cost.
  - Then add a projection: extend `autokernel-actor-seat`, or register a sibling. Project, do not grade.
  - Do it before the INF-78 OAB-9 A/B verdict gates a campaign default. Acceptance: one post-hook metrics row that
    `cli.py ingest ak-actor-seat --dry-run` projects with `refused=0`.
  - **Update 2026-09-25.** The producer is merged to research main `30631761`. OAB-9 ran and kept the existing
    default (`inline`), so no default changed on an unprojected record. Post-hook rows now exist for the acceptance
    check:
    - research `605e8301` `artifacts/autokernel_ctx_ab_20260925/actor-calls.jsonl` (4 calls);
    - DS41 run 9b's `state-run9b/targets/*/workers/actor-replies/actor-calls.jsonl` (live).

    The A/B driver's own `results.jsonl` is NOT a separate source. Its columns are these rows plus a server
    fingerprint, and its read counts belong to VB-AK-CTX-1's read facet.
- [ ] **VB-AK-CTX-1 — join `epyc.autokernel.actor_context_bundle.v1` manifests to their call records** (filed
  2026-09-24, main-ak-seat). Producer: research `lane/ak-ctxvar-20260924` `ce5800cb`, `loop/actor_context.py`,
  writing `workers/actor-context/<stamp>-<role>-*/manifest.json` bound to the prompt sha256.
  - Read the manifest as the context-provenance facet of an `actor_call.v1` claim, joined on `prompt.sha256`, so a
    variable-arm call says which sections were inline and which were file-only.
  - Refuse a manifest whose prompt sha matches no call record, or whose section files no longer concatenate to the
    recorded digest.
  - The manifest records what was OFFERED, never what was READ. Reads come from the export's tool parts (INF-78
    OAB-12) and must not be synthesized from the manifest.
  - Acceptance: an OAB-9 variable-arm call projects with its bundle facet; an inline-arm call projects with none.
  - **Update 2026-09-25.** The producer is merged to research main `30631761`. Both OAB-9 variable-arm manifests
    and their prompt indexes are committed in research `135b8492`
    (`artifacts/autokernel_ctx_ab_20260925/bundle-manifests/`). The manifests are byte-identical. The INDEX copies
    carry the PII hook's period redaction (TOC-RD-1b); the originals are under `/mnt/raid0/llm/tmp/ak-ctx-ab/`.
    Their call records are in `actor-calls.jsonl` beside them. The A/B driver derived the READ side from the
    export's tool parts (`results.jsonl` → `bundle.access`: read counts per section, no bytes). That derivation is
    the reference for the read facet once OAB-12 moves it into the exporter.

## VB-KVU-1 / VB-SPEECH-CPU-1 — stack-window measurement sources (filed 2026-09-24, main-ak-seat)

Two measurement sources landed on research main on 2026-09-24 without a write-side hook. Both rows are in
`scripts/vidya/adapters/README.md` → *Known and candidate sources*. The retrospective records produce zero tuples,
and they are **not** backfilled: a tuple invented on read would claim a warrant that the run never captured.
Owner: RTG-57 (`kv-unified-stack-rollout.md`).

- [ ] **VB-KVU-1 — write side for the np × ctx `--kv-unified` driver, before the KVU-8 rerun.**
  - The drivers (research `artifacts/np_context_kvu_study_20260924/driver/study_*.sh`) write `summary.tsv` plus
    per-cell `r.json` / `pq.jsonl` / `server.stderr`. None of these has a schema version, row hash or binary
    digest.
  - Move the per-cell summary into a small Python emitter with these parts:
    - schema `epyc.vidya.np_ctx_kvu_capture.v1`;
    - one self-hashed row per (model × arm × np × L × metric);
    - fields: binary digest, `kv_unified` as read from the launch log, `n_ctx_slot`, `c`, draft depth and
      draft KV type;
    - a shared `validate_row()` that the adapter imports.
  - Parse acceptance from the full log line, `draft acceptance = 0.36355 ( 1215 accepted /  3342 generated), mean
    len =  3.91`. Record the token-weighted value as well as the per-request mean: the v1 driver's `draft
    acceptance rate` pattern returned NA.
  - Then write the adapter (`@register("np-ctx-kvu-measurement")`, `attestation_locator`, a `Source(...)` row).
    Project, do not grade: `claim_tuple.grade()` decides.
  - Carry the three cautions from the source row: KV mode as an argv fact, output divergence across arms, and
    headroom.
  - Never edit a driver while it runs. The 35B driver was live at filing time.
  - [ ] **VB-KVU-1a — the two production-follow-up producers in the same study directory** (added 2026-09-24,
    wrap-up #4). `m4_np4_concurrent_live.py` (live-server fixed-length concurrency) writes one JSON with no schema
    version, row hash or server identity; give it the same emitter, with the live pid, `/proc/<pid>/cmdline` and
    the launch log's `kv_unified` line captured at run time. `m3_depth_production.md` is a log-derived analysis
    whose depth-4 figure is a truncation **projection**: if a script produces it, its rows must mark the
    projection as a model (`estimate_kind: projection`), never as a measured arm, and carry the log window and
    the organic/probe split.
- [ ] **VB-R2364-SWEEP-WIRE** - native adapter for INF-66 R23-64 thread-sweep ANALYSIS.json + runs/*.rows.jsonl (research data/inf66/r23-64-thread-sweep-20261025/); launch-unit floor sd 0.609%, verdicts RESOLVED/UNRESOLVED carried verbatim, no new grading rule; add the source-table row in scripts/vidya/adapters/README.md. (filed ws58 2026-10-25)
  - *(2026-10-27, workspace-58 results harvest — projectability)* INF-66 R23-64 sweep (t48 44.30 tok/s; t64 -15.01% resolved; t96 -1.88% unresolved): ANALYSIS.json + rows exist, projectable now; no adapter yet.
- [ ] **VB-KVU-HPR-PREFIX — prospective HPR prefix extension of the existing CPU KVU family.** Preserve producer c4c2a3638 hash-covered raw SSE and prompt/generated IDs, request binding and prior-state semantics; validate complete/incomplete prefix provenance with the existing reader. The first absent raw seed IDs remain producer-attested. Synthetic110 and cheap R2 six-case receipts accepted; owner-reviewed golden chat/native control and new predeclaration required before measurement admission. No new class/metric/ladder or historical regrade. Native contract stays UNVERIFIED; source enrollment must precede fresh live capture.

- [x] **VB-KVU-CPU — write side + projection for the CPU np × ctx × KV-mode study (KVU-12, reopened 2026-10-20).**
  - Producer: research `artifacts/np_context_kvu_cpu_study_20261020/driver/kvu_cpu_matrix.py`. Its per-cell rows are being given
    the VB-KVU-1 schema (`epyc.vidya.np_ctx_kvu_capture.v1`, self-hashed) before the first timing cell runs; the source row is in
    `scripts/vidya/adapters/README.md`.
  - Then reuse VB-KVU-1's adapter (`np-ctx-kvu-measurement`) for these rows, not a second one: one source class, one ladder.
    Project, do not grade.
  - Done when the first Tier-0 timing window's rows ingest and `claim_tuple.grade()` returns a tier for each.
  - *(2026-10-22, workspace-f8.)* KVU-12.1 arm rows now exist through the same emitter: `/mnt/raid0/llm/tmp/kvu121-arms/out/requests.jsonl` (68 rows, schema `epyc.vidya.np_ctx_kvu_capture.v1`, `row_sha256`, `validation_problems=[]`, `pmode` `ckpt_arms`; 2 rows are HTTP-400 errors and stay in the denominator). The per-cell decision rows `cells.jsonl` (schema `epyc.kvu121.ckpt_arms.v1`, 22 rows) have no self-hash and no adapter. Project the request rows through the same `np-ctx-kvu-measurement` adapter as the rest of KVU-12, and add a row hash to the driver's cell row so the KVU-12.1 decide inputs are attested. No second adapter, no new rule.
  - *(2026-10-21.)* First timing producers exist and are persisted: epyc-inference-research `artifacts/np_context_kvu_cpu_study_20261020/w2_20261021/` (READOUT.md, capture rows, SHA256SUMS) — summary.jsonl + waves_capture.jsonl rows (schema epyc.vidya.np_ctx_kvu_capture.v1, row_sha256, validation_problems=[]). Project them through the np-ctx-kvu-measurement adapter (no second adapter); the HTTP-400 error rows (s1a, s1c) enter the denominator, never dropped.
  - ✅ 2026-10-24 (workspace-f8 vidya batch). The `np-ctx-kvu-measurement` adapter did not exist yet, so it was built as the ONE adapter VB-KVU-1 names: `scripts/vidya/adapters/np_ctx_kvu.py` (strict: re-hashes `row_sha256`, re-runs the producer's `validate_row`, re-derives every cell median from `waves_capture.jsonl`; `decode_tps_overlap_med` not projected, no per-wave value to re-derive it from; HTTP errors stay in the denominator via `request_ok`/`request_ok_fraction`), tests `tests/vidya/test_np_ctx_kvu.py`. INGESTED into the canonical ledger 2026-10-24 (`--only-new`): W2 Tier-0 window (`w2_20261021`) 4 units, 36 tuples, 108 frames; KVU-12.1 `requests.jsonl` 200 tuples, 600 frames; every tuple grades Judged/Located (no protocol citation); idempotent re-run skips all 708. Producer defect found: the KVU-12.1 request `row_sha256` was computed before `validation_problems` was added (0/68 verify); the reader accepts that legacy hash only when it re-derives `validation_problems == []`. Write side: research `f8/kvu121-cell-hash-20261024` @ `0bda5f323` (cell rows of `epyc.kvu121.ckpt_arms.v1` now carry `row_sha256`; request rows rehashed after validation; 98 driver tests) awaits the owning session's merge. `cells.jsonl` decision rows are not read (a different record class). The kvu121 arms ran a worktree build, flagged `binary_not_kernel_store` on every tuple.
    - *(2026-10-24, workspace-f8 main; merge record.)* Research `f8/kvu121-cell-hash-20261024` @ `0bda5f323` MERGED to research main as `bbb502812` (reviewed MERGE, LOW risk): KVU-12.1 request rows are now hashed after validation and `epyc.kvu121.ckpt_arms.v1` cell rows carry `row_sha256` for every future run.
- [x] **VB-READBW-DS41 — route ad-hoc `bench_readbw` runs into the INF-70 corpus.** Point `readbw_gap.sh` (and future AK readbw probes) at `/mnt/raid0/llm/tmp/inf70/results-<tag>-<UTC>/c0-readbw.txt` and emit `OMP stack ON` in banners when the stack is set; then ingest the 2026-09-26T10:55:35Z run (raw bytes unchanged; the directory stamp equals the file header) via `cli.py ingest inf70 --as-of <ts>`. Acceptance: 24 readbw claims, `omp_stack=ON`, source sha matches the raw file. No new adapter or ladder.
  - [x] Producer fixed ✅ 2026-09-26: `readbw_gap.sh` now writes `/mnt/raid0/llm/tmp/inf70/results-ds41scope-<UTC>/c0-readbw.txt` and banners carry `OMP stack ON`.
  - [x] 2026-09-26T10:55:35Z run ingested ✅ 2026-09-26 (operator-authorized): 24 readbw claims, 72 frames, via an isolated root `/mnt/raid0/llm/tmp/inf70-ingest-ds41scope` (symlink to the corpus run; the ingest does not dedupe, so the full corpus was not re-walked). `omp_stack` projects `unstated` because the raw banners predate the fix — raw bytes kept unchanged rather than rewritten.
  - [x] `omp_stack=ON` acceptance ✅ 2026-09-26: `results-ds41scope-20260926T135451Z/c0-readbw.txt` (run in the DS41 10h→10i pause) ingested, 24 claims tagged omp-on. Note: its full-screen t=96 read-sum sample is 178.9 GB/s vs 449.4 at 10:55Z (t=48 408.1 vs 399.6; half screen consistent) — a single anomalous sample, not a new ceiling; repeat before quoting t=96.

- [x] **VB-SPEECH-CPU-1 — write side for `speech_cpu_bench.py`, before any CPU speech re-measurement** (KVU-11 B/C).
  - ✅ 2026-10-22 — producer research `d2e3283be` `artifacts/speech_cpu_realtime_20260924/speech_cpu_capture.py` (schema `epyc.vidya.speech_cpu_capture.v1`, self-hashed rows, shared `validate_row()`); `speech_cpu_bench.py` writes capture rows when `SPEECH_CPU_CAPTURE_DIR` names a new directory (legacy path unchanged; the 2026-09-24 `raw/` is refused): whisper/qwentts binary digests, exact core list and thread count, `SHIM_NPROCS`, frontdoor :8070 argv/`-t`/cores and CPU ticks sampled DURING each request with a `generating` verdict and basis. Adapter `scripts/vidya/adapters/speech_cpu_measurement.py` (`speech-cpu-measurement`, producer pinned by sha256; the three cautions are required fields and ride every tuple). 19 producer tests + 9 adapter tests. The 2026-09-24 rows still yield zero tuples (not backfilled).
  - Add a schema version, row hash, whisper/qwentts binary digests, the exact core list and thread count, and
    `SHIM_NPROCS`. Also capture the co-tenant state: frontdoor `-t`/cores and whether it was generating, sampled
    during the row.
  - Then the adapter. Carry the three cautions from the source row: layout is part of the measurand, the shim is
    the only thread control, and co-tenant state decides the result.
  - [x] **VB-SPEECH-CPU-1a — write side for `live_llm_contention.py`** (the addendum-3 harness, research
    - ✅ 2026-10-22 — research `d2e3283be` `live_llm_contention_capture.py` (the 6afc7eed `live_llm_contention.py` stays byte-identical because SHA256SUMS and an ni08 prebinding pin it): live-server placement and binary digests from `/proc` resolved before any traffic, the co-tenant LLM pid/argv/cores sampled during each request, each request's cap, and `guard_aborted` decided before the repetition's rows are written. A capped/aborted row has `completed: false`, value null, and is counted (`n_censored_in_run`), never projected.
    `6afc7eed`; added 2026-09-24, wrap-up #4). Its `raw/live_contention.jsonl` rows carry RTF, first packet and
    `llm_overlap` but no schema version, row hash, binary digests or the co-tenant LLM's pid/argv/cores. Add them
    (sampled during the row), and record each speech request's cap and whether a guard aborted the arm, so a
    capped or aborted row can never read as a completed measurement.

## VB-SPEECH-CONV-1 — conversation-stack voice measurements (filed 2026-09-24, speech vision session)

- [ ] **VB-SPEECH-CONV-STT2-NATIVE — wire converted-asset CPU smoke native records before belief-gated use.** Extend the existing conversation-stack source and writer for prospective CS-8.STT2 separately converted Parakeet-v3 F16 and Whisper-large-v3-turbo F16 per-clip records. Bind original PCM/manifest, immutable model acquisition/provenance, runner source/binary/ggml linkage, CPU backend/mapping/KFD observation, grant/argv/decode options, per-clip status/transcript/raw digests, partial/failure and unknown denominator. Comparison to exact sealed reference is descriptive; no production-weight equivalence, STT3, WER or timing qualification. Preserve empty protocol/unknown co-tenancy when applicable. Existing ClaimTuple.grade decides; no second ladder or historical warrant. Require native record/tamper/incomplete fixtures and planning-context canary before claiming wired. Packets /mnt/raid0/llm/tmp/refactor-01a16fc3/speech-next-runners-ready/.

The operator ratified the speech vision on 2026-09-24. It lives in
[`conversation-stack.md`](conversation-stack.md) (INF-79), and it will produce a new measurement family:

- the interlocutor bake-off on a PyTorch reference harness;
- GPU co-residency and CU masking on the second MI210;
- end-to-end voice turns;
- a quantization ladder for the ported model.

No run exists yet, so the write side is filed **before** the first run. The row is in
`scripts/vidya/adapters/README.md` → *Known and candidate sources*. Owner: INF-79.

**2026-10-20 extension (research intake, no new checkbox):** the conversation-stack measurement family now also covers the CS-22 turn-end arm bake-off (CS-47) and the CS-23 barge-in ablation (CS-49); both emit their records through this write side. Carry `metric_direction` per metric: false-cut rate, EOT FPR, INT FPR, latency, interruption t_stop, cancel latency and CPU ms are lower_better; EOT recall, PASR and interruption Respond rate are higher_better; t_stop for backchannel, off-talk and background speech is higher-is-correct. Reference rows copied from published papers (TurnBench, Full-Duplex-Bench, HumDial, VAP) are tagged as such and never graded as our measurements.

- [x] **VB-SPEECH-CONV-1 — write side for the conversation-stack harnesses, before the first CS-8/CS-9 run.**
  - ✅ 2026-10-22 — write side and adapter: `scripts/vidya/adapters/conversation_stack_measurement.py` (`@register("conversation-stack-measurement")`, `attestation_locator`, `Source(...)` row, `cli.py ingest conversation-stack-measurement`). The writer `write_belief_measurements()` refuses a row without schema, row hash, `protocol_id` (null = observation), reps + basis, per-metric direction, model and quant, runtime with digest, device and host lane, and co-tenant state sampled during the row; the four cautions are enforced (per-metric direction table, required harness block, SC58 judge pin when `llm_judged`, reference-harness marker with `serving_claim=False`). No CS-8/CS-9 harness exists yet; each calls this writer when built. Every kind projects as an OBSERVATION: P-STT-1 WER is "not a claim without its owning release protocol" (MEASUREMENT.md), so `ADMISSIBLE_PROTOCOLS` is empty until CS-2 ratifies an amendment. Tests `tests/vidya/test_conversation_stack_measurement_adapter.py` (26).
  - Every harness row carries: a schema version, a row hash, `protocol_id` (null until the CS-2 Annex S amendment
    is ratified, so the row is an observation), reps and reps basis, `metric` with an explicit per-metric
    `metric_direction`, the model and quant, the runtime (reference vs port) with binary or upstream digest, the
    device and host-lane placement, and the co-tenant state (LLM, device, np, generating yes/no) sampled during
    the row.
  - Then write the adapter (`@register("conversation-stack-measurement")`, `attestation_locator`, a `Source(...)` row).
    Project, do not grade: `claim_tuple.grade()` decides.
  - Carry the four cautions from the source row: mixed directions, co-tenant state as measurand, LLM-judged fidelity
    (SC58), and reference-harness numbers as never being serving claims.

**2026-10-22 extension (research intake `intake-underdog-bark-20261021`):** the STT bake-off, VAD/end-of-turn, interruption, degraded-mode and speech op-test producers write through these field extensions before their first run.

- [x] **VB-SPEECH-CONV-1B — STT-arm and scoring record fields on the VB-SPEECH-CONV-1 write side, before the first CS-8.STT5 run (the dives' draft 1b).** Each STT-arm WER record carries: runner id, runner commit and ggml version, quant, backend and device with residency proof, weights sha256, decode options (and KV dtype for transcribe.cpp whisper rows), language mode (forced or auto), att_context right or delay_ms or the unified (L,C,R) lookahead for a streaming arm, normaliser id+hash, reference-set id and track, scorer sha (plus the secondary scorer sha and package versions when used), manifest sha256, n, unk_count and the unk-ban flag, segmentation mode, stratum, corpus_id@manifest_sha256[:12], confirmation_reuse_n and metric_direction=lower. The fitting-screen record (arm, model revision, probe, accept_ref with interval, n_eligible, panel, predictions sha256, language, stratum) is written in the same write as the WER record; the lexicon-trial record adds lexicon sha256, boost alpha, list scope, case policy, term recall, term precision, insertions per hour and non-list-word WER. The projection REFUSES a tuple without `whisper_parity_gate_ref` when the runner is not `production-speech-v1`, and refuses a confirmation-stratum tuple that carries per-utterance values. Extend the existing conversation-stack row in `scripts/vidya/adapters/README.md` with these fields; project, do not grade (`claim_tuple.grade()` decides). Vendor, card, leaderboard and hosted-board numbers enter only as literature-class claims with date, set list and normaliser. Acceptance: adapter fixtures for one record of each kind and the two refusals. (intake-2346#record, intake-2351#record, intake-2352#record, intake-2353#record, intake-2354#record, intake-2372#record, intake-2378#record)
  - ✅ 2026-10-22 — kinds `stt_arm_wer`, `stt_fitting_screen`, `stt_lexicon_trial` in `scripts/vidya/adapters/conversation_stack_measurement.py`; refusals: non-`production-speech-v1` runner without `whisper_parity_gate_ref`, per-utterance values on a confirmation/private stratum; `stt_record_from_scorer()` maps the research `d2e3283be` `stt_bakeoff` scorer records (cross-repo seam test: a real scorer record writes, projects and grades; an unsealed confirmation record is refused). `corpus_id` binds the corpus manifest hash (identical across arms). Vendor/leaderboard numbers only via `literature_rows()`. README row updated.
- [ ] **VB-SPEECH-CONV-1B-LEX2 — wire prospective CS-8.LEX2 native boosting evidence before its first scored grid.** Extend the existing `stt_lexicon_trial` source/writer and projection, preserving the existing source class and `claim_tuple.grade()` ladder. Bind frozen dataset revision and dev/test manifests, call-overlap exclusion, native clip/context identities and hashes, configured and effective alpha, list scope and tokenizer plus per-ID vocabulary verification, model/source/binary and ggml identities, CPU placement and actual grant, exact attempt/exposure/result identities and unknown/failure/partial dispositions. Require positive native nonempty-trie/effective-alpha evidence for boosted cells; no-warning alone is not proof. Preserve the dev-selected configuration before test and exclude exposed unknowns from redraw. Tests cover native positive, alpha-zero, mismatched vocabulary, failed or interrupted attempt, call-overlap, and held-out split refusal; run the planning-context canary before calling the loop wired. Existing protocol and parity refusals apply; observations only, no invented warrant or new grading rule.

- [x] **VB-SPEECH-CONV-1C — VAD, end-of-turn and time-to-final record fields, before CS-22.V1, CS-22.T1 and CS-22.L1 run (the dives' draft 1c).** VAD-arm records carry vad_model, weights_sha256, runtime (onnx, ggml or jit), hop, the arm's full parameter set (threshold, smoothing, padding, min speech/silence), language, dataset revision, corpus manifest hash and confidence mask; end-of-turn records carry turn_arm in {silence, smart_turn, parakeet_eou, text_llm_prompt}, interim_source (the STT arm that produced the transcript) and prompt_sha256; time-to-final records carry metric `time_to_final_after_vad_end_s`, protocol `aa-forced-endpoint-v1`, chunk_ms, the Silero pin sha, the STT arm, its att_context or delay setting, device, clip id@manifest hash and language. metric_direction per metric as already listed for VB-SPEECH-CONV-1. Refuse a VAD tuple without its weights sha. Acceptance: fixtures and one refusal. (intake-2360#record, intake-2363#record, intake-2364#record, intake-2373#record, intake-2376#record, intake-2380#record)
  - ✅ 2026-10-22 — kinds `vad_arm`, `end_of_turn`, `time_to_final` (protocol `aa-forced-endpoint-v1`) in `scripts/vidya/adapters/conversation_stack_measurement.py`; a VAD tuple without its weights sha256 is refused.
- [x] **VB-SPEECH-CONV-1D — interruption and barge-in records name their timing oracle and the gate under test (the dives' draft 1d).** CS-49 and CS-4 set-5 records carry timing_oracle (synthetic_timeline, or asr_word_times with the merge parameters) and gate_under_test; the projection refuses a tuple whose timing oracle is the gate under test (the circularity rule in CS-45.2). Acceptance: one fixture and one refusal. (intake-2365#record)
  - ✅ 2026-10-22 — kind `interruption` in `scripts/vidya/adapters/conversation_stack_measurement.py`; a tuple whose timing oracle is the gate under test is refused (CS-45.2 circularity rule).
- [x] **VB-SPEECH-CONV-1E — CS-26 co-residency and degraded-mode records carry A/B/A arm ids and the region-claim id (the dives' draft 1e).** CS-26.F1 records (and any arm the M14 trigger later adds) carry the arm id of each A/B/A leg, the region-lock claim id and cpu list, thread counts, the neighbour's identity and its tok/s per leg, and the per-thread CPU time of the speech process; refuse a tuple without A/B/A arm ids or claim id. Acceptance: fixtures and one refusal. (intake-2378#record, intake-2379#record)
  - ✅ 2026-10-22 — kind `coresidency_degraded` in `scripts/vidya/adapters/conversation_stack_measurement.py`; a tuple without A/B/A arm ids or the region-lock claim id is refused.
- [x] **VB-SPEECH-KOPT-1 — write side for the speech-ggml and v11 gfx90a op-test records (CS-43.1, CH-18.d) before they run.** Each op-test record carries backend, device arch, rocm_version, ggml sha and version, local_patch_count, suite case count, op and case columns, HIP graphs on/off, fusion on/off and the first-divergence step; add a source row to `scripts/vidya/adapters/README.md` beside the existing test-backend-ops row and project into the existing kernel-correctness ladder (no new grading rule). Upstream PR statements and author-run op-test counts enter only as literature-class claims. Acceptance: one fixture per record kind. (intake-2361#record, intake-2362#record, intake-2385#record)
  - ✅ 2026-10-22 — `scripts/vidya/adapters/speech_ggml_optest.py` (`@register("speech-ggml-optest-measurement")`, `cli.py ingest speech-ggml-optest`): kinds `cs43_1_speech_ggml_optest`, `ch18d_v11_gfx90a_optest` and literature `upstream_statement` (never projected). Projects into the same `measurement` class and single ladder as the test-backend-ops source (`autokernel_property.py`); value = failed cases, lower_better; experimental-tree runs are P-AK-SEARCH-1 search records, so every tuple is an observation. README source row updated. Tests `tests/vidya/test_speech_ggml_optest_adapter.py` (8).
  - [ ] **INF-50 CPU-native extension (prospective).** Extend the existing measurement projection to the original `inf50-native-proof-v1` grammar/sanitizer records at the owned results root. Bind exact input provenance and original phase/native logs, source/build/compiler/linkage/binary seals and cleanup; validate native assertions/counts from original test logs, exposing failures, held/partial sanitizers and unsupported runtimes. Orchestration COMPLETE alone is never a successful native-case count or whole-INF50 acceptance. Preserve direction `lower_better` for actual failed-case counts only; do not manufacture counts from process rc. Reuse `claim_tuple.grade()` and existing measurement authority without adding a registry class or ladder. Add planning-context canary before calling the loop wired. No run has occurred; all inputs/results remain PENDING. Native proof cannot establish GPU/full-candidate regressions, SPEC-GRAM byte identity or original >=5x peaked-p95 gate.
  - [ ] **VB-INF50-SW2 — wire prospective request-local speculative-cap observations.** Add a write-time native producer and adapter for successor SW-2 matrices, binding request/launch and effective cap, slot/cache and prompt identity, per-step draft evidence, instrument/source/model/binary/live-library custody and cleanup. Delegate grading to `claim_tuple.grade()` without a new grading rule or parallel ladder. Preserve the 2026-10-28 CPU/ngram/Gemma diagnostic as PRE-HOOK; never backfill its measurement warrant. If its scoped conclusion is accepted and committed, register it separately as a Judged/Located committed conclusion. Validate producer/adapter round-trip, refusal of unbound and pre-hook measurements, and a planning-context canary before calling the loop wired.
    - Private v9/tiny draft-simple successor instance: preserve exact archived v9/runtime/model/drafter/source identities, contemporaneous distinct requests and raw cap/draft/slot evidence; verify default reset and over-limit clamping through the actual live private server. Missing counters remain unknown unless justified by the pinned native serialization contract. Preserve interrupted sequence boundaries and refuse cross-server continuation, tampered input and retrospective warrant. Extend this existing source and its round-trip/refusal/planning-context tests; no parallel task, ladder or production-deployment claim.

    - *(Evidence, workspace-58, 2026-10-26; not a tick.)* `/mnt/raid0/llm/tmp/codex-ni-20261026-inf50-window-successor/margin-recovery/results/RESULT.json`: inf50-native-proof-v1 COMPLETE, native_proof_only true, INF50_complete false; Release/ASAN+UBSAN/TSAN builds and native rc0; GNX qualified UNKNOWN. Still OPEN: champion fold review, full CPU/GPU candidate regressions, SPEC-GRAM byte identity, the >=5x front-door peaked-p95 gate. Box and INF-50 stay open.

## Research Intake Update — 2026-09-25 (shared screen evidence)

**Durable activation triggers — these are records, not active tasks**

- **VB-LENS-1:** activate with `MM-LENS-1/2` only when visual-token processing is a measured latency, memory, or quality bottleneck, or a named deployment requires LensVLM. Then bind repository/model/runtime revisions, sample digest, expansion accounting, ECR components, in-window residency, and result hash. No Lens-specific grading ladder.
- **VB-PROG-1:** activate when a long-horizon or adversarial program-search campaign is selected after the shared selector screen, or when an opponent-defined workload exhibits cycling, forgetting, or nontransitivity. Then bind task/view/scorer/container/model/config identities, controls, seeds, budgets, failures, raw candidates, per-iteration outcomes, private-call receipts, wall time, and terminal selection. One run or selection episode is one locator.
- **VB-AK-OEE:** activate when a live evolutionary campaign uses QD diversity or open-endedness diagnostics to make a decision. Then bind the immutable event log, task/config, criterion/metric/descriptor, controls, sampling budget, horizon, raw/corrected archives, and finite-horizon/no-promotion scope. Only post-hook producer records project.
- **VB-AISCI-1:** activate when EPYC begins proposal-to-execution scientific experiments that consume RA-14/RC-13 artifacts. Then bind system/task/scaffold versions, independent-study cluster, denominator unit, interventions, budgets, artifact states, grader/rubric identities, and terminal decisions. Pre-hook studies and prose summaries emit zero tuples.
- **VB-FORMAL-1:** activate before a formal artifact is used for an EPYC claim, evaluator, policy, or promotion decision. Bind repository commit, toolchain, dependency lock, command transcript, source/output digests, build result, axiom report, `native_decide` boundary, runner, and timestamp; project build and axiom findings separately.
- **VB-SPILL-TTFT:** activate when the fabric's spillover partial-offload arm (heterogeneous-slot-fabric-residency.md, under the GPU-as-placement-target task) is scheduled. Bind r grid, load points, served artifacts and store digests, P-GPU-1 device-state capture, per-request TTFT/TPOT/outcome class and completed-requests/min; the Dynamo PR ratios are never projected.
- **VB-KT-BUILD:** activate when F6 (the kt-kernel build check, fable5-window2-findings-02-heterogeneous-gpu.md R-A9) runs. Per the operator OD-A decision of 2026-09-26 ("KTransformers runtime DECLINED for now; MI210 port investigation OPEN"), F6 now runs only after F7's source-only feasibility read names a build as the next step, and any build runs only on an experimental tree or the second MI210, never on a frozen production tree. Bind kt commit, host cpuinfo flags, toolchain versions, env, build-log digests, per-arm attribute readout and failure class; project as a verified finding that updates intake-1809#01, never as a performance claim.
- **VB-KT-PORT:** activate when F7 (the OD-A MI210 port feasibility read, same rider) starts. Bind the kvcache-ai/ktransformers and sglang-kt commits read, the per-question finding class with file:line (ROCm flag and HIP shim; hipify / ROCm 6.2 port of the GPU half; gfx90a build of the fork), and the effort estimate with its basis; project as a verified source-level finding updating intake-1809#03, never as a performance claim.
- **VB-NPD-1:** activate when numa-prefill-decode-disaggregation.md's reopen trigger fires (PF1 finds L* ≤ 32K). Bind the served artifact and store digests, argv, the concurrent-prefill schedule, per-token decode TPOT with and without the concurrent prefill, and the manifest's predeclared inflation bound.

## VB-ROUTE-LAT / VB-UFH12-RETR / VB-UFH12-PLACEMENT / VB-TD-ADVICE — routing and REPL-retrieval measurement sources (filed 2026-09-26)

Filed at design time, before any producer exists, per the CLAUDE.md belief-kernel rule. Source-table rows in
`scripts/vidya/adapters/README.md`.

- [ ] **VB-SPEECH-KOPT-1-FA6A — add the standalone OFF-image FA6a producer to the existing native op-test writer.** Before a claim-bearing future full run, preserve original invocation, source/test-case/ELF/build/device/ROCm identities, HIP graph/fusion settings, case coverage, pass/fail/not-supported counts and decided native comparison, raw log hash, UTC bounds, own PID/birth and during-run residency. Write the existing `speech_ggml_optest.beliefs.jsonl` carrier at that same run boundary and project with the existing measurement ladder; require the original planning-context canary. Preserve the 260.101 s rc75 diagnostic smoke as partial with no terminal suite verdict and do not backfill its warrant.
- [ ] **VB-SPEECH-KOPT-1-META-FULL-ARCH — wire the META full-arch native worker instance into the existing speech op-test writer/reader.** Source instance: `/mnt/raid0/llm/tmp/codex-ni-meta-full-arch-ready-20261030/worker.py`. At the native write boundary preserve original invocation, source/ELF/build/device/ROCm identities, complete row/case coverage and statuses, expected SKIPs as SKIPs, raw record/log hashes, UTC bounds, own-process residency and cleanup. Extend the existing strict `speech_ggml_optest.py` reader only against this actual record shape; do not claim the worker already emits its sidecar or that the existing reader accepts it. Keep the actual 432-row smoke (535 OK cells, 329 expected SKIP cells, 118 meaningful HIP NMSE OK cells, 93 residency samples) distinct from the 10 scheduled full repetitions, which are not results. Require the planning-context canary for this producer/reader instance before calling it wired. Reuse the existing measurement class and kernel-correctness ladder; no new source class or grading rule, no retroactive measurement warrant, and no full champion-fold claim. The current smoke and cutoff remain raw diagnostic evidence only.
- [ ] **VB-ROUTE-LAT — wire the write side of routing-decision latency telemetry** (`routing-intelligence.md`
  RI-16). The producer emits per-request, per-stage timings (role priors, route, mode, review gate) with backend
  and index size; then author the read-side adapter. Locator = request x stage aggregated to a run window;
  never project the unmeasured "<1 ms / 10-50 ms" doc figures.
  - Progress 2026-09-30: the producer exists. Orch `78847544` (RI-16) writes `routing_path` + `stage_ms` into the
    progress JSONL `routing_decision` and `task_completed`/`task_failed` events, and it serves from 2026-09-30 04:52Z
    (API PID 1930724). Still owed: backend, index size and `instrument_class` on the producer, a ClaimTuple-shaped
    sidecar or strict reader, the adapter and a `cli.py ingest` verb. Source-table row updated.
- [x] ~~**VB-UFH12-EMBSPEED — wire the write side of the embedder speed records** (`repl-embedding-retrieval.md` REPL-EMB-2.7 speed block; filed 2026-10-20). VB-UFH12-RETR covers recall, not timing. The pilot `artifacts/research/emb-speed-20261020/results.jsonl` is retrospective and contended (no claim tuple; peer load recorded only in `ctx0/ctx1`); the in-launch speed block must emit chunks/s, tokens/s, p50/p95, RSS and index-build time with model/revision/dtype/runtime identity, cpu-list, region-lock claim, loadavg/GPU/frequency context and the A/A noise floor in its unit, through the same writer as 2.4. The source-table row in `scripts/vidya/adapters/README.md` goes with it.~~ (closed 2026-10-29 audit: OBSOLETE → Speed block DROPPED by operator ruling 2026-10-20 (box text: "moot unless the speed block is re-opened"); writer reused only if EG2 throughput run is made.)
  - 2026-10-20 (build note, factual; checkbox NOT ticked): **write and read side built, no run written yet.** Same module and same reader as VB-UFH12-RETR: `SpeedRun.add_speed` / `add_noise_floor` / `finalize()` → `<run_id>.speed.record.json` + `<run_id>.speed.belief_measurements.jsonl`, ingest name `repl-embedder-speed` (instrument `offline_speed`, projection `project_speed`, same shared ladder). Metrics: `chunks_per_s`, `tokens_per_s`, `query_p50_ms`/`query_p95_ms`/`query_max_ms`, `cpu_s_per_query`, `index_build_s_4096`, `rss_mb`, `disk_mb`, each with n, spread and `config_echo`. Refused at construction without the full timing context (cpu-list, observed affinity inside it, region-lock claim tag, loadavg at both ends, frequency governor/range/throttled); `finalize()` raises on any speed row without an A/A noise floor for its (arm, metric), carried in the metric's own unit with its replication unit (arm|session|process) and n >= 2. The 2026-10-20 pilot `results.jsonl` stays retrospective (no sidecar, zero tuples). Source-table row: `scripts/vidya/adapters/README.md`. Still owed before a tick: the 2.7 speed harness calling this API under a held region-lock claim.
  - 2026-10-21 (text re-scope, factual; checkbox NOT ticked, main to tick): the "speed harness calling this API under a held region-lock claim" is no longer owed as written. The REPL-EMB-2.7 speed block was DROPPED by operator ruling 2026-10-20 ("we don't need to get precious about measuring the speedup properly on a quiet host"), so this box is moot unless the speed block is re-opened. The remaining use of the writer is EG2's as-served throughput (G-T1) in REPL-EMB-2.12, which must carry its contention label; if that run is made, it goes through this writer.
- [ ] **VB-UFH12-PARITY-BINARY214-WIRE** — capture the prospective REPL-EMB-2.14 fixed 200-text v9/v10 binary comparison, per-item native vectors and cosine, source/model/binary/runtime/argv/grant identities and every attempted or UNKNOWN record; use the original per-item >=0.9999 rule and complete denominator. Keep this instance distinct from the 0.99 G-P1/G-P2 EG2 gate, project only attested native observations with the existing `ClaimTuple.grade()` ladder, and pass a real planning-context canary before calling it wired. No historical backfill or default-change claim.

- [ ] **VB-UFH12-PARITY - wire the write side of the embedder parity gate (`scripts/benchmark/repl_emb_parity_gate.py`) before G-P1 / G-P2 run (filed 2026-10-20; REPL-EMB-2.11; EG2 package section 14).** The script has no belief-kernel write side (no capture or vidya reference found in it), and the 2026-10-20 parity runs (2.5 proxy and probe45, 2.6 BF16 / Q8_0, the champion rebase) produced per-item cosines with no claim tuple. Fields: arm identity, runtime / argv / binary sha256, per-item min and mean cosine vs ST FP32, non-finite count, input-set digest, `flash_attn` resolution. Add the source-table row to `scripts/vidya/adapters/README.md` and project through the existing `measurement` ladder only (no new grading rule). The 2026-10-20 parity results stay retrospective (no backfill). Done when a G-P1 dry run emits a record the read side projects and grades.
  - *(2026-10-24, 3c4ca599 subagent; landed by integrator)* Wrote `repl_embedder_parity.py` (`cli.py ingest repl-embedder-parity`) and the opt-in `--belief-out` / `--runtime-meta` producer emit in orch `repl_emb_parity_gate.py`. A synthetic G-P1 dry run through the gate's real `compare` emits 9 rows that the read side projects and grades (Judged/Located). The 2026-10-20 results stay retrospective (writer refuses a parity.json older than 1 h). Real ingest: `python3 cli.py ingest repl-embedder-parity --path <belief-out dir> --as-of <ts>`. Box stays OPEN until main inserts the `adapters/README.md` source-table row (text: `/mnt/raid0/llm/tmp/batch-20261024/scratch-ufh12parity/README_row.txt`, after the "Embedder placement gate" row); the guard hook `agents_reference_guard.sh` blocked the subagent's edit.
  - *(2026-10-24, 3c4ca599.)* Source row added to `scripts/vidya/adapters/README.md` by main (the subagent's edit was refused by `agents_reference_guard.sh`: the row's bare handoff filename did not resolve, and 6 pre-existing bare `.md` references in other rows blocked every edit of the file; all 7 now use resolvable paths). Not ticked: no real G-P1/G-P2 run has emitted yet (the dry run was synthetic and was NOT ingested).
- [ ] **VB-UFH12-RETR — wire the write side of the UFH-12 retrieval eval** (`repl-embedding-retrieval.md`
  REPL-EMB-2.1/2.2/2.3) before its first run: per-arm recall@k, CPU-s, latency, with the pre-registered rule,
  corpus digest and embedding-model identity; the online `spill_pointer_follows` shadow is a separate instrument.
  - 2026-10-20 (build note, factual; checkbox NOT ticked): **write and read side built, no run written yet.** Write side: epyc-orchestrator `scripts/benchmark/repl_retrieval_capture.py` (`RetrievalRun.add_recall` / `add_paired_diff` / `add_cost` / `finalize()` → `<run_id>.record.json` + `<run_id>.belief_measurements.jsonl`; `registered_rule()`, `HostWindow`), lane `lane/repl-emb-25-20261020`, sha256 `be6a0499…`, tests `tests/unit/test_repl_retrieval_capture.py` (82 passed). Read side: `scripts/vidya/adapters/repl_retrieval_eval.py`, ingest name `repl-retrieval-eval` (registered in `ingest_sources.py` and `cli._FILE_SOURCES`), pinned to the capture sha256, tests `tests/vidya/test_repl_retrieval_eval_adapter.py` (19 passed with `EPYC_REPLRET_CAPTURE` naming the lane file until it lands; 18 skip without it) and `test_ingest_sources.py` + `test_claim_tuple.py` (186 passed with `UFH13_RESEARCH_ROOT` set, the unrelated ufh13 fixture's prerequisite), root lane `lane/repl-emb-25-root-20261020`. Instrument `offline_recall` only; the REPL-EMB-2.1 rule (k=5, M=0.10, X=0.05, n>=120, bootstrap lower bound > 0) rides in every row and different values are refused without a dated amendment; the online `spill_pointer_follows` shadow has no writer and is refused as a foreign instrument. Locator = run × arm × mode × query category × k × metric. Schema, refusals and cautions: the source-table row in `scripts/vidya/adapters/README.md`. Still owed before a tick: the 2.2 harness calling this API and a real run's sidecar ingesting with zero refusals.
  - 2026-10-20 (first run written; box stays OPEN, factual): run `repl-emb-22-20261020` (REPL-EMB-2.2) went through the writer: 275 rows (260 recall, 15 paired-diff, 0 cost) in epyc-orchestrator `data/repl_retrieval_eval/repl-emb-22-20261020/`, read side dry-run 275/275 projected and graded, no ledger append. Not met yet: (a) the done criterion names CPU-s and latency per arm and the run wrote NO cost rows (the speed block was dropped by operator ruling and the run's timings are contended; `add_cost` needs a timing context the run did not take), (b) a real `cli.py ingest repl-retrieval-eval` has not run because the adapter pins the capture module at `/workspace/repos/epyc-orchestrator/scripts/benchmark/repl_retrieval_capture.py`, which is absent on that shared checkout until it is updated from main. Not projected (record is immutable): vs-BGE diffs, per-stratum diffs, secondary decision sets and the kill-rule verdict (all in `analysis.json`).
- [x] **VB-UFH12-PLACEMENT — wire the write side of the embedder placement gate** (`repl-embedding-retrieval.md`
  REPL-EMB-0.2 / 1.4; `epyc-orchestrator` `scripts/server/embedder_placement_gate.py`) before the REPL-EMB-1.4 G1
  re-measure. Done 2026-09-27: write side `scripts/server/embedder_placement_capture.py` (orch lane
  `lane/repl-emb-gate-capture-20260926`, on top of `lane/repl-emb-11-14-20260926`) emits
  `<record-stem>.belief_measurements.jsonl`; read side `scripts/vidya/adapters/embedder_placement_gate.py`, ingest name
  `embedder-placement-gate`. Schema and refusals: the source-table row in `scripts/vidya/adapters/README.md`. The
  2026-09-26 Phase-0 files stay retrospective. A G3 re-run must write an `epyc.embedder_placement_g3.v1` record through
  the same `CaptureWindow` (the Phase-0 G3 driver is an out-of-repo tmp script).
- [x] **VB-UFH12-PLACEMENT-DISC — make `embedder-placement-gate` discovery recurse into `arms/`** (filed
  2026-09-27). The A0 and A3 arm sidecars live at
  `epyc-orchestrator/data/embedder_placement/arms/<run>/<N>-{base,cand}.belief_measurements.jsonl`, nine files. But
  `scripts/vidya/ingest_sources.py`'s `Source("embedder-placement-gate", ...)` globs only `*.belief_measurements.jsonl`
  at the root, so `cli.py ingest` never sees them.
  - Add `arms/*/*.belief_measurements.jsonl` (or `*/*/…`, following the `kv-quant-27b-v10-measurement` pattern).
  - Add a discovery test over a two-level fixture.
  - Confirm the nine arm sidecars project, and that any refusal names its reason.
  ✅ 2026-10-29 source `6ffee0ec72e1be2b1a04c9f4e9c48945908ae565`, integrated root `faf388a58af2cafaa482c6d036284661612a89df`: bounded two-level discovery preserves root/explicit-file layouts. Thirteen adapter controls pass; 41 carrier fixtures have zero grade/byte-identity changes. Read-only audit discovers and projects all nine original sidecars (99 rows, 297 frames), zero refusals; native hashes and producer pin unchanged. No ledger writes. [no-belief: discovery repair and read-only compatibility controls]
- [ ] ❄ FROZEN 2026-09-27 — resume only once TD-28 unfreezes (v11 promoted AND autopilot has trained on the swapped stack AND UFH-13 re-opened; operator ruling 2026-09-29) — **VB-TD-ADVICE — wire the write side of the typed-routing advice A/B** (`typed-decision-plane.md` TD-28):
  arm, typed mode, workload digest, override rate and per-item outcome split. Project, do not grade.
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): its only producer, TD-28, is frozen; wiring a source with no producer is dead code; unfreeze trigger: TD-28 unfreezes. The box stays open: frozen is not done.


## VB-V1-BACKPRESSURE / VB-SEL-LOADAB / VB-SWAP-C / VB-PREFILL-XOVER / VB-GAP-DIST / VB-MT-REPLAY — orchestration prior-art intake sources (filed 2026-09-26, research-intake)

Filed at design time, before any producer exists, per the CLAUDE.md belief-kernel rule. Source-table rows in
`scripts/vidya/adapters/README.md`; the three trigger-gated sources from the same intake (VB-SPILL-TTFT, VB-KT-BUILD,
VB-NPD-1) are activation records in the durable-triggers list above.

- [ ] **VB-V1-BACKPRESSURE — wire the write side of `/v1` backpressure receipts** (`harness-selection-and-integration.md` HS-OD-9) before the first live bounce: one receipt per bounce with the dispatch-ledger snapshot, estimator version, `retry_after_ms`, `retry_after_basis`, next-attempt time and admission, and turn outcome. Locator = request; never graded above observation until a codified protocol exists. Distinct from SC19 (`ChatResponse.contention_gate`, `/chat` only).
- [ ] ❄ FROZEN 2026-09-27 — resume only once DAR-LAT-3 unfreezes (autopilot has trained on the swapped stack AND UFH-13 re-opened; operator ruling 2026-09-29) — **VB-SEL-LOADAB — wire the write side of the selection load-sweep A/B (decision-aware-routing.md DAR-LAT-3)
  before its first block.**
  - Per-request rows carry: arm, ρ, block, manifest/prior-table/episodic-snapshot digests, TTFT budget, outcome class,
    selection receipt, final role, grader verdict, and `instrument_class=serving`.
  - Locator = block (arm × ρ × window). Floor pairs are their own locators.
  - Project; do not grade. The grade comes from the protocol id: P-SERVE-SEL-1 was ratified 2026-09-26 (operator,
    orchestrator-design session); the annex lands when the operator runs the ratify script, and the A/B grade follows
    that protocol once it is applied (observation before that).
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): its producer, DAR-LAT-3, is frozen; unfreeze trigger: DAR-LAT-3 unfreezes. The box stays open: frozen is not done.
- [ ] **VB-SWAP-C — wire the write side of the launch-phase receipts (heterogeneous-slot-fabric-residency.md HSF-1).**
  - One launch = one locator, with GGUF/binary digests, argv hash, page-cache fraction, phase timings and outcome class.
  - Cold/partial-cache launches project with their label and never merge into hot C.
- [ ] **VB-FA4-BIAS-WIRE — capture prospective FA4 value-bias diagnostics.** Preserve native per-arm, case, repetition and actual bias; binary/source identities, component input identities, output finiteness, raw logs, device witness and failures. Project only through the existing carrier and grade, before decision-class use; do not convert an unsealed diagnostic or finite-output observation into a mechanism, quality, timing or promotion claim.

- [ ] **VB-FA4-EXACT-WIRE — project prospective FA4 C5 exact-set native records.** Bind the frozen source, models, FA4/C5 ELFs, six-field 228-case input universe, actual arm/pair, native per-case outcomes and nonfinite counts, device/process/grant evidence, raw custody and cleanup at write. Distinguish R17's qualified smoke and partial cutoff from a completed original three-pair, 22-band, two-KV-type comparison. Use the existing `ClaimTuple` carrier and grade, with no new ladder or historical backfill; prove a planning-context canary before decision-class use. The R17 queue capsule is an operational conclusion, not a sealed full-result tuple.

- [ ] **VB-META-ASSERT1-WIRE — preserve native candidate architecture findings at source.** Bind the exact source/patch, built libraries, native command and seed, device witness, raw outputs and failure/partial state to the existing carrier before any decision-class use. Small-model lifecycle smokes are unsealed diagnostics; synthetic architecture tests do not establish model-level or promotion outcomes.

- [ ] **VB-M4-C3-ORDER-WIRE — capture prospective controlled-order C3 comparisons.** Preserve the original failed comparison separately and bind each future arm, prompt, pass, model, binary and inputs to observed admission order, actual overlap, native outputs and failures at write time. Use the existing carrier and grading ladder and verify the planning-context canary before decision-class use. Do not invent a historical warrant or seal diagnostic smokes; order observations alone do not establish causation.

- [ ] **VB-LB49-FA-NODE-WIRE — capture prospective paired attention-node diagnostics.** Bind source, canonical model, mapped libraries, two prompts, both thread counts, attention-node identities, sink presence, outputs, differences, failures and cleanup at write time. Use the existing carrier and grading ladder and prove the planning-context canary before decision-class use. Sink presence does not prove an IQK route or causation; exclude synthetic smoke tuples and seals. Prospective QKV extension: bind actual synchronized-after first-FA Q/K/V/mask/sinks/output buffers with native dtype/ne/nb/op_params/presence/exact-alias hashes; require strict schema/phase/bounds and original-output bitwise replay before reference/ON sink interventions. Standalone historical-image source helpers and generated prior-op/stride/alias fixtures are engineering-only ([capsule](../../artifacts/autokernel/lb49-qkv-source-prep-20261031/README.md)); actual DS41 custody/planning canary and implied-logit propagation remain open.

- [ ] **VB-PAW2-COMPILE-WIRE — capture prospective self-hosted compile and runtime observations.** Bind the exact server, SDK, compiler, mapper, interpreter and input revisions to native compile artifacts, local execution, wall time, measured RAM and disk scope, failures and the Compact GPT-2 position-limit caveat. Use the existing claim carrier and grading policy; prove the planning-context canary before decision-class use. Do not retrofit unsealed diagnostic smokes or introduce a new grading ladder.
- [ ] **VB-PAW3-EVAL-WIRE — capture prospective PAW task and abstention evaluation.** Bind the predeclared split and case selection, exact input and program/compiler/runtime identities, native outputs and references, observed labels, abstentions, and full attempted/scored/invalid denominators at write time. Preserve the original semantic and first-token confidence methods, the overlap between `test` and `test_clean`, and uncertainty about historical program bytes. Project through the existing carrier and grading policy without a new ladder; prove the planning-context canary before decision use. Do not retrofit tuples to old runs.
- [ ] **VB-INF58-RESIDENT-CALIBRATION-WIRE — capture future eligible resident-versus-fresh calibration.** Bind exact model, executable, serving recipe, prompts, paired launch identities, cache state, native responses and per-cell timing, actual GPU residency and quiet-grant/lock observations, coactivity, incomplete runs and fallback at the producer boundary. Keep the self-comparison calibration descriptive and distinguish fresh-fallback cells. Project through the existing carrier and grading policy; no retroactive tuples, new ladder or decision-grade claim before the planning-context canary.
- [ ] **VB-EVL34-DELEGATION-WIRE — capture prospective natural-delegation comparison.** Bind the exact task snapshot and selection, real model and substrate identities, declared arm semantics, natural tool-call events and depth, prompts and outputs, accuracy, wall time, token usage, errors and attempted denominators at write time. Treat the historical REPL emulation and small-model smoke as diagnostic rather than actual production REPL evidence. Use the existing carrier and grading policy, retain partials and prove the planning-context canary before decision use; do not retrofit tuples.
- [ ] **VB-EVL39-E3B-WIRE — capture prospective matched context comparison.** Bind the full task and corpus snapshot, matched model and actual direct, Context-Folding and REPL/search arms, native request timing/token observations, evidence recall, tool calls and precision, root/subcall counts, resource/KV witnesses and all partial/invalid denominators at write time. Preserve missing or ambiguous measurements as UNKNOWN; use the shared carrier and grading policy and prove its planning-context canary before decision use. Do not backfill or equate a proxy arm to the native implementation.
- [ ] **VB-RTG16-EXPANDED-WIRE — capture the prospective mixed-population eval suite.** Bind the predeclared question selection, original and prospective provenance, exclusions and scoreability, exact suite and scoring bytes, model/runtime identities, per-question outcomes and attempted/valid/invalid denominators at write time. Preserve the population change and unproven leakage explicitly; project through the shared carrier and grading policy and prove the planning-context canary before decision use. Do not backfill historical measurement warrant.
- [ ] **VB-S19-VISION-PAIR-WIRE — capture prospective vision/frontdoor contention.** Bind actual live placement and role recipes, model/binary identities, each paired leg, native matrix, host-health observations, failures and partial denominators at write time. Preserve diagnostic scope and host-state versus ratio uncertainty; use the existing contention-matrix source ladder and shared carrier, and prove the planning-context canary before decision use. No historical backfill.
- [ ] **VB-PIP05-QUALITY-WIRE — capture prospective matched OCR quality.** Bind exact source page pixels/PDFs and references, LightOnOCR and docling-fast identities, scorer and settings, native outputs, exclusions, failures and denominators at write time. Preserve metric direction, use the existing shared carrier and grading policy, and prove a planning-context canary before decision use; never infer historical baseline identity or backfill warrant.
- [ ] **VB-EVL29-FRONTIERCS-WIRE — capture prospective FrontierCS floor.** Bind the preregistered problem selection, exact upstream revision and checker/interactive protocol, model/runtime and sandbox identities, per-case input/output and dispositions, resource limits and full attempted/invalid denominators at write time. Preserve historical benchmark coverage differences, use the shared carrier and grading policy and prove its planning-context canary before decision use; never backfill warrant.
- [ ] **VB-INF26-CL3-PROFILE-WIRE — capture prospective quant decode profiling.** Bind exact GSQ and UD model shards, production binary and loaded library identities, compiled knobs, workload/geometry, native timing and per-process counters, missing events, failed cells and denominators at write time. Keep structural code observations distinct from runtime attribution; use the existing carrier and grading policy and prove the planning-context canary before decision use. Do not backfill profiling warrant.
- [ ] **VB-EVL33-BUDGET-WIRE — capture prospective reasoning-budget diagnostics.** Bind the exact request forms, source/binary/model identities, native responses, usage, stopping and censor observations, errors and attempted denominators at write time. Preserve the distinction between observed interface behavior and unproven historical race causes; use the shared carrier and grading policy and prove a planning-context canary before decision use. No historical backfill.
- [ ] **VB-INF49-INTERFERENCE-WIRE — capture prospective prefill/decode interference.** Bind model and serving identity, actual slot geometry, declared ubatch and context settings, concurrent prefill/decode window and token timestamps, reference baseline, failed cells and denominators at write time. Preserve the lower-is-better spike metric and distinguish concurrent evidence from post-window observations; use the shared carrier and grading policy and prove a planning-context canary before decision use. No historical backfill.
- [ ] **VB-INF43-E5-PLACEMENT-WIRE — capture prospective E5 placement recertification.** Bind exact model, binary, serving recipe, cell identity, requested and observed CPU/NUMA/GPU placement, native timing, host-health evidence and failed/partial denominators at write time. Preserve the earlier placement confound; use existing source ladders and shared grading and prove a planning-context canary before decision use. No historical backfill.
- [ ] **VB-UFH07-TRAJECTORY-WIRE — capture prospective trajectory-context comparison.** Bind exact tasks/model, append-only and compact implementations, trigger settings, wall time, token/cache counts, trajectory growth/search observations, accuracy strata and all failed/partial denominators at write time. Preserve model restoration or prospective replacement explicitly; use the shared carrier and grading policy and prove a planning-context canary before decision use. No historical backfill.
- [ ] **VB-INF22-M4-GPU-LOAD-WIRE — capture prospective paired GPU load.** Bind original target/drafter and candidate binary identities, exact arguments, real grant and GPU-quiet custody, in-window own-PID GPU residency, load and cleanup results, errors and partial denominators at write time. A successful load is not a performance, quality or promotion verdict; use the shared carrier and grading policy and prove the planning-context canary before decision use. No historical backfill.
- [ ] **VB-EVL37-RUS3-WIRE — capture prospective repeated-sample trace probe.** Bind role/suite/question, pinned model and runtime, nonzero sampling temperature, sample identity, full reasoning trace, native token count, correctness, finish reason, errors and all attempted denominators at write time. Preserve question-fixed grouping, mixed-outcome N, truncation exclusions and small-pilot limits; use the shared carrier and grading policy and prove a planning-context canary before decision use. No historical backfill.
- [ ] **VB-EVL48-A3-VISION-WIRE — capture prospective vision-encoder prefill baseline.** Bind exact image, model/projector and binary identities, device and residency observations, native prefill timings, errors and all attempted denominators at write time. Preserve the separate completed embedding half and do not impute vision timings; use the shared carrier and grading policy and prove a planning-context canary before decision use. No historical backfill.
- [ ] **VB-INF24-RE42-WIRE — capture prospective LongCoT non-saturation probe.** Bind current role/topology, quiet-window evidence, stratified selection, two-phase requests, budget and native responses, deterministic scoring, marker/canary outcomes, failures and complete denominators at write time. Preserve the declared 10–90% accuracy and marker gate, with infrastructure failures excluded rather than scored wrong; use the shared carrier and grading policy and prove a planning-context canary before decision use. No historical backfill.
- [ ] **VB-UFH05-CVEC-SAFETY-WIRE — capture prospective steering safety checks.** Bind model/vector identity and each actual scale, harmful and benign prompts, evaluator identity, native outputs, refusal and false-refusal counts, harmless KL or perplexity, failures and attempted denominators at write time. Preserve per-scale distinctions and unproven vector/model compatibility; use the shared carrier and grading policy and prove a planning-context canary before decision use. No historical backfill.
- [ ] **VB-CJ17-BEAM-AGREEMENT-WIRE — capture prospective question-anchored BEAM judge agreement.** Bind exact question, rubric and response identities, per-nugget judgments and invalids, native event-order alignment and tau, paired human and GPT references, attempted denominators, actual execution provenance and judge/arm family identities. Use the existing shared carrier and grading policy; validate a planning-context canary before decision use. Do not synthesize tuples from historical fixtures.
- [ ] **VB-INF18-BIDIR-MECHANISM-WIRE — capture prospective bidirectional transfer mechanism evidence.** Bind per-direction timestamps and overlap, host-thread placement and NUMA memory snapshots, paired baseline/diagnostic measurements, binary/runtime/source identities, timing-window coverage and attribution uncertainty. Use the existing shared carrier and grading policy; validate a planning-context canary before decision use. Do not backfill historical aggregate-only observations.
- [ ] **VB-INF70-XFER4B-WIRE — capture prospective prefill and paired-quality records.** Bind source, recipe, model, arm and question identities, observed shape and timing custody, per-item responses, scoring, errors and partial states at write time. Project through the existing shared carrier and grading policy, with refusal/partial controls and a planning-context canary. Reject test-only and DO-NOT-INGEST artifacts, `worker-fixture-*` and anything outside validated actual attempt custody. Preserve the historical 90c12df42→8c4b282ae comparison; do not infer current-champion or fold warrant, impute missing scores or retrofit historical fixtures.
- [ ] **VB-ARCH-GPQA-COT-1 — capture prospective EVL-02 GPQA-Diamond-CoT paired GPU arms.** Bind the full 198-item manifest, actual scored count, truncation and parse failures, source/model/arm identities and original writer-time attestation. Project through the existing quality-gate carrier and shared grading policy; test missing-tuple refusal and a planning-context canary. Do not reconstruct tuples for prior pre-hook runs.
- [ ] **VB-INF20-DR3E-CERT-WIRE — capture prospective quant-asymmetric K2 certification.** Bind verifier/drafter shard and binary/linkage identities, matched 8K/16K task outputs and denominators, speculative counters, host/GPU occupancy, frontdoor opportunity cost, failures and cleanup at write time. Project through the existing shared carrier and grading policy with a planning-context canary; do not backfill historical v7 observations.
- [ ] **VB-EVL19-R2-CURRENT-WIRE — capture prospective per-question accrual.** Bind actual state-era fence, source identity, trial trust, native item outcome/disposition and attempted/excluded denominators. Apply the existing shared grading policy and validate a planning-context canary. Do not backfill old records or activate the core without the operator-owned era decision.
- [ ] **VB-INF42-HRM1-COMPARE-WIRE — capture prospective matched HRM-1 comparison.** Bind task/dataset, prompt and PrefixLM condition, model/source identity, native responses and scoring, invalid/overlength/error/missing dispositions, controls, execution window and clean drain. Preserve native fractional invalid-answer credit and report invalid counts separately. Project through the existing shared carrier and grading policy with a planning-context canary; no historical backfill or inference from missing rows. This is distinct from INF-42 G1.
- [ ] **VB-RTG23-W5 — capture prospective offered-load profiles.** Bind the exact workload corpus, profile schedule, native request and arrival observations, attempted and completed counts, wall time and achieved lane width at the producer boundary. Preserve unratified or incomplete profiles as UNKNOWN, do not pool profiles or backfill historical warrant, and project through the existing carrier and grading policy; prove the planning-context canary before decision use.
- [ ] **VB-REV06-PLAN-WRITE — capture prospective scoped plan-review diagnostics.** Bind the native per-question result and trace, corpus and synthetic acceptance-check-derived plans, source/model/runtime identity, actual HTTP counts and prompt bytes, service and client duration, missing usage and incomplete or ambiguous exposures at write time. Use the shared carrier and grading policy and prove the planning-context canary; the original July plan lengths and architect-queue attribution remain open. Do not retrofit tuples.

- [ ] **VB-PIP02-PIPELINE-WIRE — capture the native three-stage document table pipeline at write time.** Bind source page, canonical layout and recognition models, runtime, server, stage outputs and table artifacts; preserve partial and failed stages. Implement the producer and strict projection through the existing claim carrier before decision-class capture. Exclude void whole-page single-shot outputs and diagnostic smoke tuples.

- [ ] **VB-PIP03-IMAGE-WIRE — capture matched image outputs at write time.** Bind original prompt/seed, per-model runtime and settings, unaltered image artifacts and validity, and separately attributed human admissibility/quality observations. Project only evidence actually captured through the existing claim grammar and source registry; no new grading rule, retrospective tuples or diagnostic smoke seals.
  - Prospective ERNIE-only typography slice binds exact EN/ZH prompts/requested text, seed/settings and enhancer state or UNKNOWN, source/model/encoder/VAE identities, grant/timing, PNG validity/hashes and separately attributed human review. Preserve failures and missing attempts; no redraw, matched-Qwen or official benchmark claim. Existing producer, reader and canary remain pending.

- [ ] **VB-RTG28-E2-WIRE — capture paired prompt-effort GPQA measurements at write time.** Bind the exact enrolled plan, model, quant, kernel, template, sampling and item identities to native finish/scoring status and result artifacts. Use the existing registered `ClaimTuple` carrier and grade; preserve excluded and truncated outcomes, fail closed on missing provenance, and wire before the first decision-class run. No retrospective warrant or diagnostic smoke tuple.

- [ ] **VB-DTAP-FINANCE-ENV-WRITE — capture the scoped Finance quote injection pair.** Bind exact native source, newer cache, NVDA account, payload registration, observed model-visible quote delivery or nondelivery, transactions, judgment, actual grant, failures and teardown. Use the existing carrier and grade and prove the planner canary; smokes are unsealed and no broad security inference is implied.

- [ ] **VB-DTAP-FINANCE-PAIRED-WRITE — capture the scoped finance action-reversal pair at write time.** Bind both actual model/tool trajectories, account/email initialization, source and pinned newer-cache identities, native transactions, injection payload and observed delivery order, explicit nondelivery and failures, real grant and teardown. Project through the existing carrier and grade, then prove the CLI-to-planner canary; do not convert a smoke or missing delivery into a security result. The remaining cases and services remain open.

- [ ] **VB-DTAP-CRM-PILOT-WRITE — capture the scoped CRM pilot at write time.** Bind model/template/schema/upstream source/image/grant identities, attempts and errors, request/tool/response, full service state, native judge and cleanup. Project through the existing carrier and `ClaimTuple.grade()` and prove the normal CLI-to-planner canary; refuse smoke or fixture as a real run and do not infer missing warrant. The other cases, service families and indirect-injection arms remain TU-DTAP-2 open.

- [ ] **VB-EVL20-F1-WIRE — capture F1 original decision-scope measurement at write time.** Preserve the declared rule, model/binary/instrument identities, complete token/layer denominator and raw timing/placement evidence, ambiguous or missing attribution, in-window GPU witness and matched instrumentation overhead control. Project only measured, unambiguous values through the existing carrier and grade; retain failed/null rows. Small-model normal/cutoff smokes are unsealed diagnostics with no tuple or receipt. No historical reconstruction, new ladder or end-to-end speedup claim.

- [ ] **VB-INF34-A2-DIAG-WIRE — preserve the raw A2 single-cell observation.** Capture native output, canonical model and binary identities, exact recipe, GPU residency, window context and partial/cleanup state at write time; project only eligible observations through the existing prefill carrier and `ClaimTuple.grade()`. No diagnostic seal, receipt, retrospective warrant, crossover claim or new ladder; run the planning-context canary before calling wired. The full PF1 grid remains separate.

- [ ] **VB-PREFILL-XOVER — wire PF1 on the WRITE side before its first cell runs.** Emit one self-hashed ClaimTuple-shaped record per cell (artifact + binary digests, build line, protocol id or observation, n, date, VRAM-during-run witness, failure reason when failed) into the PF1 run dir; no read-side reconstruction.
- [x] **VB-GAP-DIST — wire the write side of the session inter-call gap measurement** (`heterogeneous-slot-fabric-residency.md` HSF-3) before its first extraction: one row per gap (session hash, role, client class, t_done, t_next, gap_s, source), with the log-manifest digest, extractor revision and window. Locator = window × class; W1 and W2 never pool. Observation-grade.
  2026-10-05 checkpoint: native extractor/reader and CLI source are on root main `d61ae218`;
  original CI `37294486291` passes 21 cases (19 gap fixtures, two registration/CLI cases).
  Existing grader only. Passive admission-enqueue field is on app main `b01ab993`, with no
  reload. Bounded Oct 3/4 existing-log census requires a CPU claim; original timestamps are
  retained as exact/proxy/unavailable, with no historical backfill or TTL authority.

- [ ] **VB-DS41-C57 — project the DS41-C57 barrier-sleep probe records (INF-77, 2026-09-27).** Source row in
  `scripts/vidya/adapters/README.md`. Raw per-arm artifacts under `/mnt/raid0/llm/tmp/ds41-c57-cpu0-20260927/`
  (`probe*/NN-ARM/`, `probe_table*.tsv`, `gomp/`). One locator per launch × arm; carry binary digest (anchor-gen-001-prof,
  anchor-gen-001, anchor-gen-002 `c0ef39613`), argv/env hash (OMP_PLACES, load threads), vcs and tok/s per request.
  OBSERVATION grade (1-2 launches per arm); never merge into the loop's matched-floor rows. The follow-on DS41-C59
  runtime-arm compare rides the loop's evaluation-event path and needs no new adapter. Copy the raw dir into a
  durable location first — `/mnt/raid0/llm/tmp` is scratch.
- [ ] **VB-DS41-C95 — project the DS41-C95 blind-graded planner-harness records (INF-77 DS41-C95/C101, 2026-10-01).** Source row in
  `scripts/vidya/adapters/README.md`. Inputs: `/mnt/raid0/llm/tmp/ds41-c95/grading/{report.json,grades/,key.json,items.jsonl}` and the
  per-call `results/<ctx>/<arm>/r<k>/result.json`. Locator = context × arm × repeat; `asran-*` calibration rows are labelled and never
  pooled. OBSERVATION grade (2-4 calls per arm); per-call keep-class verdicts project as verifier records with an explicit decided
  proposition; no-reply calls are misses. Carry `recovered_by` for run-1 calls rebuilt by `run2.py finalize`. Add the write-side
  `belief_measurements.jsonl` to `run2.py`/`grade.py` BEFORE DS41-C102 runs, so orv/orsv rows are born with their tuple. Copy the dir
  somewhere durable first — `/mnt/raid0/llm/tmp` is scratch.
  - 2026-10-03 extension (UFH14-A1 F12 run): two more arms, same grading pass and same ladder, no new source class.
    `cxf1` (F1 serving fixes) and `cxf12` (F1 + F2 answer protocol), 4 calls each on C2/C4, per-call
    `results/C{2,4}/cxf{1,12}/r{1,2}/result.json`; grades already in `grading/report.{md,json}` (cxf12 P(keep) 0.75, 0 exact / 3
    partial; cxf1 0.50, 2 partial). Project them with the existing locator. One call (C2/cxf1/r2) is graded `contaminated=True`:
    carry that flag into the tuple and exclude it from any pooled arm verdict. Later runs (`run3.py`, Landlock sandbox) must emit the
    write-side `belief_measurements.jsonl` row at call end — see UFH14-A5.
  - 2026-10-04 extension (UFH-14 run-3 A3/A4, `run3.py`): four more arms, same source class and ladder (UFH14-A5: extend,
    no new ladder). Per-call `results/C2/cxa+a3{cold,warm}/r<k>/result.json` and `results/C4/cxa+a4{base,fix}/r<k>/result.json`
    add three fields the earlier projection does not cover: `first_request` (prompt_n, cache_n, cache_hit, prompt_s,
    decode_tps, held_s, ttft_after_release_s), `compactions` (n, rewritten, reprefill tokens/s sums, unfinished) and
    `sandbox_denials` (denied_hits). Project each as an OBSERVATION metric on the existing context × arm × repeat locator,
    with its own unit and direction; `sandbox_denials.denied_hits` is a run-validity fact carried on the tuple, not graded.
    A `compactions.unfinished > 0` call is censored. These arms are pre-hook too: copy `results/C{2,4}/cxa+a*` durably first.  - 2026-10-30 writer source is available in research `276d75fab` (`scripts/harness/ds41_c95/`): future calls publish exclusive pre-exposure metadata and reference its SHA in results; verified backend identity/grade unknowns remain null. Project the existing `contamination_crosscheck` and normal native isolation fields using the same source ladder, never backfill a warrant for historical calls. Adapter/reader and planning-context canary are still required before any fully-wired claim. [Source/proof](../../artifacts/compute/refactor-a6-source-build-ready-20261030.json).

- [ ] **VB-MT-REPLAY — wire the write side of the multi-turn replay** (`dynamic-stack-concurrency.md` "(G) #25592" row and its G5 extension) before the first replay: per-turn rows keyed by `x_session_id` with prompt_n, cache_n, forced-re-prefill cause (a/b/c/unattributed), N, gap lengths and the HSF-3 receipt digest, plus binary/store digests and argv. Locator = run × N. Project; do not grade.

## VB-THESIS-1 — the thesis experiment's per-item receipts (filed 2026-09-27, narrowed plan)

Filed at design time, before any producer exists, per the CLAUDE.md belief-kernel rule. Source-table row in
`scripts/vidya/adapters/README.md`. Experiment: [`thesis-experiment-orchestrator-vs-strongest-model.md`](thesis-experiment-orchestrator-vs-strongest-model.md) (UFH-13, TOP priority).

- [ ] **VB-THESIS-1 — wire the write side of the thesis experiment before its first scored item (UFH-13 TE-4).**
  - Per-item rows: arm (A0/A1/A2, riders labelled), item id, suite, correct, escalation fired / reason / final serving
    role, consultant and frontdoor device-seconds from the inference tap, wall, truncation, failure class.
  - Run-level rows: G and d with their paired-bootstrap CIs and the verdict class, plus the `FROZEN-AT-LAUNCH.sha256`
    digest and any post-hoc amendment.
  - Locator = run × arm × item; `instrument_class=serving`. Project; do not grade (P-AB-1 / PAIRED-CI-1 /
    BOUNDED-NULL-1 decide).
  - Progress 2026-09-27: research `2b59bebe` writes the sidecar — `run_thesis.py score` emits
    `belief_measurements.jsonl` (`ufh13-thesis-belief/v1`) with per-arm and run-level rows; per-item rows live in the
    attestation `records.jsonl`. No run yet.
- [x] **VB-THESIS-2 — write the `ufh13-thesis-measurement` adapter (read side for VB-THESIS-1).** Project research
  `scripts/benchmark/thesis_ufh13/run_thesis.py score`'s `belief_measurements.jsonl` (`ufh13-thesis-belief/v1`) into
  `ClaimTuple`, re-hashing the attestation `records.jsonl` against `attestation_sha256` and refusing on mismatch.
  Register it as class `measurement`, add a `cli.py ingest` verb, and update the source-table row. Why now: the
  producer exists and TE-5 is the next inference; wiring the read side before the first scored run means the verdict
  is ingestible the day it lands. Project; do not grade (empty `protocol_id` grades as an observation).

## VB-DISPATCH-S2 — HS-19 stage-2 dispatch receipts (filed 2026-09-27, hs19-stage2 design)

Filed at design time, before any producer exists, per the CLAUDE.md belief-kernel rule. Source-table row in
`scripts/vidya/adapters/README.md`. Design: [`hs19-stage2-dispatch-20260927.md`](../../docs/design/hs19-stage2-dispatch-20260927.md) §12-13.

- [ ] ❄ FROZEN 2026-09-27 — resume only once the UFH-13 thesis experiment shows A2 pays — **VB-DISPATCH-S2 — wire the write side of the stage-2 dispatch receipts before the gate shadow run (HS-19d P3a)
  and the first eval block (P5).**
  - Record one row per plan: gate value and confidence, planner role and fallback, plan sha256, validation outcome,
    `N_now`/`N_total`, and the capacity snapshot with its source.
  - Record one row per subtask: `plan_id`, `subtask_id`, type, selected role and selection receipt, `queued_s`,
    status, wall time and tokens.
  - Carry both on the HS-19a link spine.
  - Locator = plan for shadow rows. Locator = arm × workload class × block for eval rows.
  - Shadow rows project as observations. Eval rows grade only under the protocol annex that §13 pre-registers. Project; do not grade.
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): its producers, HS-19d P3a and P5, are frozen; unfreeze trigger: HS-19d P3a or P5 unfreezes. The box stays open: frozen is not done.

## VB-REVIEW-GATE / VB-RI18 — review-gate telemetry and the RI-18 counterfactual (filed 2026-09-30, RI-18 build)

Filed with the producers, before either has run, per the CLAUDE.md belief-kernel rule. Source-table rows in
`scripts/vidya/adapters/README.md`. Design: `/mnt/raid0/llm/tmp/ri18/DESIGN.md` (`routing-intelligence.md` RI-18).
RI-16's routing `stage_ms` is covered by VB-ROUTE-LAT above, not by a new task.

- [x] **VB-REVIEW-GATE — write the read-side adapter for the `review_gate` tap events** (RI-18 C1; orch main
  `08edc054`). The orchestrator emits one `review_gate/v1` event per review-site
  evaluation to `/mnt/raid0/llm/tmp/inference_tap_events.jsonl` (fields: the source-table row).
  - Project trigger rate, skip-reason coverage, verdict mix (`ok`/`wrong`/`unavailable`) and gate/verdict/revision
    ms per `path` as **observations**. Never infer "the review helped" from them: live traffic has no ground truth.
  - Keep `unavailable` (and `null`, no verdict requested) distinct from `ok`, never folded into it; never pool across
    `path` values or thresholds. Locator = event, aggregated to a run window.
  - Register as class `measurement`, add a `cli.py ingest` verb, and update the source-table row. No back-fill: before
    C1 is deployed there is no structured record. Project; do not grade.
  - **DECLINED 2026-10-03** ✅ 2026-10-03. RI-18 scored DROP (`routing-intelligence.md` RI-18, 2026-10-01), and its
    pre-registered action RI-18c removes the gate, and C1's `review_gate` event with it. An adapter for a producer
    being deleted is not worth writing. The events the API wrote between C1's deploy and RI-18c stay on disk and are
    not ingested. Reopen trigger: RI-18c is reversed, or a new review trigger lands with its own event.
    The source-table row update is prepared for the owning session, not applied.
- [ ] **VB-RI18 — write the read-side adapter for RI-18's `belief_measurements.jsonl` sidecar** (research
  `scripts/benchmark/ri18_review_gate/run_ri18.py score`, research main `6b2366e2`).
  - Project the per-policy, per-stratum rows (net per 100, accuracy, precision/recall, AUROC, reviewer
    sensitivity/specificity, device-seconds per net fix with GPU and CPU separate), re-hashing the per-item records
    against `attestation_sha256` and refusing on mismatch.
  - Refuse rows from a VOID run, rows missing the served orch commit or store-snapshot sha, and a pooled GPU+CPU cost.
    Split-A (tune) rows project but never as the decision. Locator = run x split x stratum x policy x metric.
  - Register as class `measurement`, add a `cli.py ingest` verb, and update the source-table row. Why now: wiring the
    read side before the first scored run makes the verdict ingestible the day it lands. Project; do not grade (the
    pre-registered rule, PAIRED-CI-1 and BOUNDED-NULL-1 decide).
  - 2026-10-03: the first scored run exists: `ri18-v1`, DROP, 2026-10-01 18:53Z. Its sidecar is
    `/mnt/raid0/llm/tmp/ri18/run-v1/belief_measurements.jsonl`, 6 rows. The rows are pooled `pi1`, `piQ@0.60`,
    `piQ_tstar_splitB`, AUROC, `unavailable` rate and the 0.6 trigger count. It falls short of this task's contract
    (VB-RI18a).
  - [ ] **VB-RI18a — close the gap between the RI-18 sidecar and its contract, and make the run durable.** (filed
    2026-10-03)
    - No row carries the served orch commit or the store-snapshot sha. Both are in `run_manifest.json` (`served`,
      `snapshot`). The contract above refuses such rows, so as written the adapter would ingest nothing.
    - The rows are pooled only. There are no per-stratum or per-split rows, and no reviewer sensitivity or
      specificity, precision/recall or device-seconds rows; `score.json` holds them all. `protocol_id` is empty.
    - The whole run lives under `/mnt/raid0/llm/tmp/ri18/`, which is scratch, not git.
    - Fix: either (a) extend the research `score` sidecar writer and re-run `score`, which is offline, takes seconds,
      runs no inference and is not a confirmation re-run under RI-18's stopping rule; or (b) have the adapter join
      `run_manifest.json` through the attestation. Then copy `score.json`, `run_manifest.json`, the sidecar and the
      per-item records to a durable research results path, and repoint `attestation_path`.

## VB-SERVING-DF2 — production serving producers from STACKCHG-DFLASH2 (filed 2026-10-03)

- [ ] **VB-SERVING-DF2 — wire the write side for three new serving measurement sources** (filed 2026-10-03,
  workspace-ec; CLAUDE.md *Belief Kernel — wiring new sources*). STACKCHG-DFLASH2 PACKAGE §7.4 and the :8083
  KV-sizing package both name these as new measurement producers; none writes a claim tuple yet.
  - **Orchestrator per-call serving telemetry** (`src/backends/serving_calls`, KVU-17 in
    `kv-unified-stack-rollout.md`): server-reported `prompt_ms`, `predicted_ms`, `cache_n`, `draft_n`,
    `draft_n_accepted` per call. Locator = served orch commit × role × port × drafter × endpoint × stream.
  - **DFlash2 at the production shape** (Q38-T7 in `qwen38-27b-replace-qwen36.md`): decode tok/s paired with a
    correctness check, coherence at production prompt length, acceptance. Must carry the kernel store build id
    (`gpu-20260921-ffc1bac82`), the drafter GGUF sha and the full argv.
  - **Qwen3-VL-30B on CPU** (S-18 in `multimodal-pipeline.md`): decode tok/s and MMMU parity at NUMA_HALF_A `-t 48`.
  - Also: the measured DFlash2 VRAM components in `/mnt/raid0/llm/tmp/kv-sizing-8083-20261003/DECISION.md` §1.3
    (drafter weights, GDN state per draft depth, KQ-mask slope) are a capacity source for SSU-F3's claim tuple.
  - Add one source-table row per producer in `scripts/vidya/adapters/README.md` (row text prepared for the owning
    session to apply), project each native record into a `ClaimTuple`; do not write a grading rule.
  - 2026-10-03 ~17:15Z (workspace-ec): the Q38-T7 producer now exists: `q38_t7.py` in the GPU-block runner
    (`/mnt/raid0/llm/tmp/gpu-block-27b-20261003/`), schema `epyc.gpublock.q38_t7.v1`, not yet run. The adapter README row for it
    (line 341, still naming the old 196608 shape and no producer) has replacement text PREPARED in
    `/mnt/raid0/llm/tmp/wrapup-ec-maskskip/INDEX_ROWS.md`, for the owning session to apply. First step for the
    adapter: copy the runner's `results/` tree durably (tmp is scratch).
- [ ] **VB-FA-MASKSKIP — write side for the KVU-19a masked-block-skip measurements** (filed 2026-10-03, workspace-ec;
  CLAUDE.md *Belief Kernel — wiring new sources*). New producers:
  - the FA kernel micro-bench and exactness harness (`/mnt/raid0/llm/tmp/fa-maskskip-20261003/harness/`, driven by
    `gpu_slot.sh`): µs per FA op by rows × foreign cells × arm (base / skip on / skip off), and per-case output hashes;
  - P3-mini (gemma-3-1b) and small batched-bench `-kvu` vs `-no-kvu` from the same `gpu_slot.sh`.
  The full-scale 27B P3 re-run uses workspace-89's `p3_kvu_probe` and projects under VB-KVU-P3, not here. Bind the
  store build id (`gpu-20261003-a0d0ae238`), the branch commits ac97e305a / a0d0ae238, the knob values
  (`GGML_CUDA_FA_MASK_SKIP`, `GGML_CUDA_FA_MASK_SKIP_MIN_KV`) and KFD residency. Caution that must ride every
  projection: the 2026-10-03 dev-build micro-bench ran on a contended GPU and is indicative only; only `gpu_slot.sh`
  store-build rounds count. n = 3 alternating rounds, no codified protocol, so tuples grade `Judged/Located` through
  `claim_tuple.grade()`; no new ladder. Source-table row text PREPARED in
  `/mnt/raid0/llm/tmp/wrapup-ec-maskskip/INDEX_ROWS.md`. Done when the row is applied and a strict adapter projects the
  store-build `gpu_slot.sh` records (copied durably first) into `ClaimTuple`s.
  - [ ] **VB-FA-MASKSKIP-b — write side for the KVU-19b `gpu_slot2.sh` records** (filed 2026-10-04, workspace-ec, from
    KVU-19b-1). A new producer generation of the same harness, already copied durably to
    `artifacts/kvu19b-20261004/slot2-20261004T044448Z/`. Its records are harness-v2 exactness (119 GPU cases ×
    arms on / skipoff / seqoff / alloff / k19a, plus the CPU reference), µs per FA op for multi-sequence shapes
    (kvu / kvu-uneven / streams × rows per sequence), p3batch tok/s (draft 1 / 8 / [1,8,8,8], arms k19a / on /
    seqoff / no-kvu), `llama-batched-bench` S_TG/S_PP JSONL and `test-backend-ops` counts. Bind the store build
    `gpu-20261004-c7f5ac9ad`, commits `1bceceb05` / `c7f5ac9ad` on base `a0d0ae238`, and the knob tuple
    (`GGML_CUDA_FA_SEQ_ROWS`, `GGML_CUDA_FA_MASK_SKIP`, `GGML_CUDA_FA_MASK_SKIP_MIN_KV`; later
    `GGML_CUDA_FA_SEQ_TILES` from KVU-19b-rework-c2). Cautions that must ride every projection: (1) commit 2's
    "skip on/off bit-identical" claim is REFUTED on 6 cases, so project it as a refuted exactness claim, not a pass;
    (2) a kernel µs figure is not a serving tok/s claim; (3) p3batch is gemma-3-1b, not the 27B. n = 3 rounds, no
    protocol → `Judged/Located` via `claim_tuple.grade()`; no new ladder. Source-table row PREPARED in
    `/mnt/raid0/llm/tmp/wrapup-ec-kvu19b/INDEX_ROWS.md`. Done when the row is applied and the strict adapter that
    VB-FA-MASKSKIP builds also projects these records.
  - [ ] **VB-FA-MASKSKIP-c — write side for the champion-fold GPU slot (`gpu_slot_fold.sh`) and the standing receipt**
    (filed 2026-10-04, workspace-ec, from KVU-19b-fold-c1). Producers: `slot-20261004T073429Z/summary.txt` and its
    per-check files (exactness E1-E8 per case × arm, 27B DFlash2 smoke text sha + accept rate, `test-backend-ops`
    counts, perf2 µs per shape × arm champ / on / seqoff), durable copy
    `artifacts/champion-fold-kvu19-20261004/`; and the single-arm standing receipt
    (`loop-memory/champion-vs-production.<sha12>.json`, schema `epyc.autokernel.champion_vs_production.v1`, written by
    research `production.refresh()` through `standing_receipt.py`). Bind champion `1bceceb05` (build 10311, store
    `gpu-20261004-1bceceb05`), base `90c12df42`, the knob tuple, and for the receipt the cited baseline record (FOLD-2
    G5 `ef81196d5`, sha256 `71344d34…`). Cautions: (1) G0 is vacuous for HIP kernels, so the slot, not G0, carries the
    GPU claim; (2) the receipt is UNPAIRED against a 26-day-old record across a BIOS change, `calibrated: false`, and
    its `confidence_interval` field is not a valid paired interval; (3) tg128 never exercises the mask skip. Grade
    through `claim_tuple.grade()` (`Judged/Located` for the slot; the receipt's unpaired ratio no higher); no new
    ladder. Source-table row PREPARED in `/mnt/raid0/llm/tmp/wrapup-ec-fold/INDEX_ROWS.md`. Done when the row is
    applied and the VB-FA-MASKSKIP adapter projects the slot records, and the receipt projects with its caveats.
- [ ] **VB-KVU16H — write side for the KVU-16h VRAM attribution (allocator shim + phase replay)** (filed 2026-10-04,
  workspace-ec, CLAUDE.md *Belief Kernel*). Producer: `kvu16h_run.py` + `analyze.py` with the LD_PRELOAD allocator shim
  → `results/<ts>/summary.{md,json}` (per-phase KFD delta, shim net bytes by allocator class × context, residual,
  verdict), durable copy `artifacts/kvu16h-vram-20261004/`; the follow-up runner `kvu16h_followup_c.py` (row 4c) emits
  the fix-vs-control growth per `n_max: 0` event. Bind build, argv sha, `-b/-ub`, shim on/off and the phase script.
  Cautions: (1) KFD growth and shim net bytes are different quantities (the residual is the runtime's), never fold
  one into the other; (2) the replay's PLATEAU is a property of its traffic mix, not of production — the production
  mechanism needs `n_max: 0` alternation; (3) the same transient-peak vs ratchet split as the MI210 VRAM
  decomposition row. Grade via `claim_tuple.grade()`; no new ladder. Row PREPARED in
  `/mnt/raid0/llm/tmp/wrapup-ec-fold/INDEX_ROWS.md`. Done when the row is applied and an adapter projects the
  20261004T063830Z summary and the row-4c result.
  - *(2026-10-04 PM.)* The row is applied, and row 4c ran (`results/fuc-20261004T110509Z/`, durable copy under
    `artifacts/kvu16h-vram-20261004/`); the adapter itself is still to be written.
- [ ] **VB-CPU-FA-VKQ — write side for the CPU FlashAttention FP16-VKQ harness and probe** (filed 2026-10-04,
  workspace-ec). Producers: the CPU FA harness (`harness-out/{nan,det,perf}_*.txt`: per-case finite/mismatch verdict
  and nmse vs a CPU-exact reference, determinism hashes, µs per FA op) and the model probe `fa_vkq_probe`
  (`acc_peak`, `max_v_chansum`, non-finite node per prompt), durable copy `artifacts/cpu-fa-fp32-vkq-20261004/`. Bind
  build (`cpu-20260925-90c12df42` base, the `2ad8bff36` build), arm (base / fix / `GGML_FA_VKQ_F16=1` legacy) and
  thread placement. Cautions: (1) the harness's large-V inputs are synthetic stress, not a serving distribution;
  (2) the probe's `acc_peak` ≤ 238 is for the named prompts on the architect only. Grade via `claim_tuple.grade()`;
  no new ladder. Row PREPARED in `/mnt/raid0/llm/tmp/wrapup-ec-fold/INDEX_ROWS.md`. Done when the row is applied and
  an adapter projects the harness summaries.
- [ ] **VB-DF2-REPLAY — write side for CPU-only DF2 n-gram replays (DF2-14, DF2-19)** (filed 2026-10-20, agent df2-19;
  CLAUDE.md *Belief Kernel*). No adapter row exists for these replays, and none is written here.
  - Source: `epyc-root` `artifacts/research/df2-19-20261020/` (`results.json` carries the outcomes, chosen gates, seed count and corpus sizes;
    `provenance.json` carries the dataset/tokenizer/COUNT pins and file sha256s; `positions.csv.gz` is the per-position raw table).
  - Caution: token-level n-gram predictability under a Dolma2 retokenization proxy and a fitted overlap model, not drafter acceptance;
    per-position DFlash2 acceptance is not on the wire. Two prompt groups only; the DF2-14 numbers (320 turns / 630k) are not re-checkable.
  - Done when an adapter projects the arm hit rates and the holdout simulated gains with the pinned inputs as the locator.
- [ ] **VB-T1-LAUNCH-PREFLIGHT-WRITESIDE — capture native T1 launch-preflight receipts at the producer boundary.** Add a source-table row for the existing `dryrun_check.py` / `filler_run12` preflight receipt and a producer-side self-hashed record that binds the exact launcher/job/source manifest, native `decided_proposition` (the concrete preflight assertion), argv/resource envelope, runner/build identity, and PASS/FAIL/INCOMPLETE outcome before the NORMAL WORKLOAD grant/model launch. Retain refusals and absent fields; do not infer booking, execution, GPU residency, correctness, or performance from a preflight PASS. Project through the existing verifier/`ClaimTuple.grade()` contract only; no new ladder or read-side reconstruction. Done when producer fixtures/refusals and `cli.py`/planning-context canary prove the captured receipt is consumed before any loop is called wired. (filed 2026-10-27, checkpoint-0945; derived from accepted launch-gate code 35348712 / 6909d2a0d and its fixtures.)
- [ ] **VB-V11FA — write side for the v11 FA routing A/B slot and the DF2-9 model probe** (filed 2026-10-04,
  - *(2026-10-27, workspace-58 results harvest — projectability)* FA4 attempt 3 (10-27) native_records/*.json + proofs.jsonl self-describing but NOT projectable (no v11fa adapter); needs producer addendum for the C5 driver and the server text-agreement field (prod greedy 14/15).
  workspace-ec, CLAUDE.md *Belief Kernel*).
  - Producers: `gpu_slot_v11fa.sh` → `slot-<ts>/summary.txt` and `perf_table.tsv` (µs per FA op × layout × rows ×
    n_kv × arm), `det/` exactness, `tbo/` counts; `fa_nan_probe` per arm (verdict, runs_nonfinite, first bad node).
  - Durable copy: `artifacts/v11-fa-ab-20261004/`.
  - Bind the arm build and commit, the ROCWMMA flag, the cherry-picks and the knobs.
  - Cautions: (1) kernel µs is not serving tok/s; (2) the server DF2-9 arm has no verdict (port busy); (3) a probe
    PASS is 0/10 on the named prompts only.
  - Grade via `claim_tuple.grade()`; no new ladder. The source-table rows are applied in `scripts/vidya/adapters/README.md`.
  - Done when an adapter projects both slots' perf tables and the per-arm probe verdicts.
  - [ ] VB-V11FA prospective matched-current-C5 producer (2026-10-27, owner-applied from codex-ni BK-OWNER-DRAFT; source seal `4e309975`): write side ACCEPTED at enrollment. The read side `adapter-v11_fa_native.py` (source kind v11-fa-native, existing measurement ladder) is prepared, NOT applied. Still owed: raw case-membership re-derivation, tamper/refusal controls, CLI ingest registration and the planning-context canary. Not wired until the canary passes.
    - 2026-10-27 rebind (workspace-58): producer source seal is now `97810628` (`/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-gpu-recovery/packet/`; the timeout --foreground PGID fix plus a DRY-only OMP=1). It supersedes `4e309975`, whose receipt stays historical. ELF manifest `39333d32` and data `09814745` are unchanged. QUARANTINE: the failed 04:21Z run (`fa4-c5-matched-bands`, stage nan_A) emitted 228 rows (capture sha `a642902d`) and 228 tuples (`ee929479`) with an erroneous partial=false and zero own-process residency proofs. They must never be ingested as qualified evidence. Read-side ingest is not wired (`v11_fa_native.py` is not applied), so nothing was ingested and no refutation filing is needed. Draft: `FAILED-NAN-A-QUARANTINE-DRAFT.md` in that recovery dir.
    - 2026-10-27 attempt-3 rebind (workspace-58): producer `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-attempt2-fix/driver.py`, source seal `3a28f55e`, shared launch-evidence helper `02462393`. The fix captures env/ownership at launch from the ancestor wrapper, and EACCES on /proc environ/fd is recorded as unavailable evidence. The cause was Yama ptrace_scope=1 blocking non-ancestor reads; no host setting was changed. Fresh output: `out/capture/`, `out/native_records/`. It supersedes `97810628`. Attempt-2 raw output is preserved and quarantined; there is no retro capture.
    - *(2026-10-30, accepted R12 preparation)* The frozen-byte actual `launch.sh --smoke` completed in 67.765s: original model_A helper ran two declared contexts, A returned HTTP 200, filtered A/B helpers completed 80/80 cases per arm, all four stages had positive in-window residency and verified cleanup, and 713 current-live censuses were COMPLETE with zero unresolved live observations. READY `fa4-c5-exact-set-r12-20261030` was keeper-validated READY-WAIT rank 3 at 15:22:23Z; the actual normal no-argument launcher independently proved `RUS3_DIAGNOSTIC=1` at 15:23:01Z. Optional `pidfd_bindings` capture metadata is unavailable (native arrays empty); do not claim it exists or use it to prove R11's exact cause. This remains diagnostic lifecycle/custody qualification, not the full three-pair/22-band/two-KV/228-case comparison. Source-family projection remains through the existing `ClaimTuple` and `claim_tuple.grade()`; no new ladder. Read-side re-derivation, refusal controls, CLI registration and planning-context canary remain open. Evidence: `/mnt/raid0/llm/tmp/codex-ni-fa4-exact-set-successor-r12-20261030/review-evidence/`. [belief: cc — committed operational observation, not original measurement warrant]
  - [x] VB-V11FA diagnostic child: FA4-SIXKEY-DIAG-1 (2026-10-27, owner-applied by workspace-58; drafted by codex-ni). Producer `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-sixkey-diagnostic/driver.py`, source seal `d72fafdf`. K=5 fresh-process ABAB reproducibility on the 8 bias1024/diffuse keys, full 228 cases per process. Write side ACCEPTED as UNGRADED diagnostic records: no measurement grade, no retro warrant for attempt 3. Fields the immutable runner does not emit are recorded UNAVAILABLE. Systematic vs nondeterministic per the predeclared rule (`tasks-from-ws58/FA4-SIXKEY-DIAG-20261027.md`). ✅ 2026-10-27 — post-disk audit accepted 09:08Z: 80/80 records SHA-linked, 10/10 228-case processes and distinct identities, 31–34 positive own-process KFD/VRAM samples per process during the run; six keys classify SYSTEMATIC and two are both-nonfinite controls. This remains ungraded and does not establish WMMA/F32 causality or performance. [belief: cc]
- [ ] **VB-LONGCTX-KERNEL — write side for the DCA perplexity and FA-INT64-OFFSET slots** (filed 2026-10-04,
  workspace-ec).
  - Producers: `gpu_slot_dca.sh` and `real_model_ppl_cpu.sh` (PPL ± per arm), and `gpu_slot_fa_int64.sh`
    (`test-backend-ops` counts, bit-identity).
  - Durable copy: `artifacts/dca-yarn-kernel-20261004/`.
  - Bind the build commit, model, scored window and device.
  - Cautions: one window per arm, and the GPU-vs-CPU offset is unexplained (YARN-DCA-XDEV).
  - Grade via `claim_tuple.grade()`; no new ladder. The row is applied.
  - Done when an adapter projects both slots' summaries.
  - [ ] **YARN-DCA-XDEV per-token attribution producer (prospective extension; no historical backfill).** Before any new diagnostic capture, emit a native self-hashed record binding the source commit, evaluator binary and loaded CPU/HIP library identities, target model and corpus hashes, exact token IDs, full-context/batch recipe, backend/residency evidence and scored window. For each arm, write only the first 64 original scored logits as aligned `predict_pos`, `target_pos`, target token ID, target NLL, target logit and target probability; the current exact evaluator maps prediction positions 32768–32831 to target positions 32769–32832. Use the same full-context prefill and batch protocol for both arms. Strict projection refuses absent or mismatched identity/window/token rows; retain native originals and preserve aggregate PPL as within-arm observation. This is attribution evidence, not a cross-device quality comparison or kernel claim. Use only the existing measurement source class and `claim_tuple.grade()`; no new ladder. The 2026-10-30 CPU/GPU smoke CSVs are bounded 8K diagnostics and must not be retroactively ingested. A CPU 65,536-context arm has since emitted a 64-row CSV, still diagnostic and not wired; the matching GPU 65,536-context attribution capture remains pending. Close this producer subtask when native pre-capture identity and bounded rows are emitted, deterministic off/on controls and same-window alignment tests pass, and the existing reader projects/refuses the corresponding records correctly.
- [ ] **VB-SERVE-CACHE-STATE-WRITE — prospective native prompt-cache entry-size capture and projection.** Capture source-owned records when llama-server saves/updates a prompt-cache entry, including base state/draft, checkpoint objects and the native full retained entry plus run/window, slot, token length and exact served binary/model/argv/maps identity. Preserve native raw line hashes/offsets and explicit absence; never infer full entry size by summing components or fill old logs with a measurement tuple. Add a strict reader that verifies the recorded hashes and projects into the shared measurement `ClaimTuple`; `claim_tuple.grade()` decides. The 2026-10-30 UFH14-B4g scratch observation is a design example only. Done when a fresh record is captured by the writer, strict reader tests pass and the planning-context canary passes; until then this source is not wired.
  - 2026-10-31 prospective CPU-FA-VKQ-3 instance: extend this existing family before its full target replay. Bind original task/source and untruncated conversation identity, native historical architect tokenizer count, all model shards/MTP head, ELF/source/build/knob/plan, live grant/placement, ordered attempted arms and process/drain results. Compare hybrid-default and legacy native draft/accept counts and token IDs only when positive native MTP draft counts exist; otherwise both acceptance and divergence are UNKNOWN. The single agentic replay is not claimed to be a historical architect exchange, serving distribution or deployment verdict. Existing shared grade only; projection/canary remain OPEN. [no-belief: prospective source-instance preparation]

- [ ] **VB-TD29-M4-PAIRED — add prospective paired-cache write-side capture and a strict reader.** At producer write time capture the native measurement warrant, sidecar identity and original TD-4 case/schema digests in the existing ClaimTuple carrier; add a strict reader for `td29_m4_actual_shadow_pair.v1` that checks source/launcher/model/binary and result byte identities, exact ordered case IDs, accepted actual dispatch receipts, raw integer per-call `prompt_n/cache_n` (unknown never zero), and exact first differing rendered chat-prompt byte/token. Project only producer-authored per-pair measurements through the shared `ClaimTuple` carrier and `claim_tuple.grade()` as observations with no new ladder or protocol. Do not project R11 smoke or pre-hook raw runs retroactively or infer a latency gain from cache counts. Acceptance: a new post-hook capture is strictly read or refused and the planning-context canary passes before calling this source wired. The current READY diagnostic can run and retain raw paired records independently; this adapter task does not hold inference.

- [x] **VB-SERVE-TIMING-1 — read side for the orchestrator per-call serving records** (`epyc.orchestrator.serving_call.v1`, orchestrator `src/backends/serving_calls.py`, orch main 9a0d38e0; filed 2026-10-03 from the workspace-89 prefill-share analysis). The write side is LIVE since 2026-10-03T04:59Z (orch 9a0d38e0 on main, API reload); the launch sidecar goes live at each server's next stack launch. Strict adapter steps:
  - discover `logs/serving_calls/serving_calls.jsonl*`;
  - refuse lines whose `record_sha256` does not re-derive, or whose schema is not `serving_call.v1`;
  - project each `timings` metric (`prompt_ms`, `predicted_ms`, `prompt_per_second`, `predicted_per_second`, `draft_n_accepted/draft_n`) plus `queue.pre_dispatch_wait_ms` into `ClaimTuple`, with unit and `metric_direction` fixed by the schema (ms and wait: `lower_better`; t/s and acceptance: `higher_better`).

  Rules for what gets projected:
  - Carry `server.argv_sha256`, `server.binary_realpath`, `server.model_path`, `provenance.orch_commit` and `provenance.run_id` as identity, never graded.
  - Skip `timings_source="absent"` rows; never emit zeros.
  - Mark `server.identity_source="absent"` rows unscoped rather than inferring the launch.

  Grading: `Judged/Located` via `claim_tuple.grade()`; no new ladder and no backfill.
  ✅ 2026-10-23 (3c4ca599): all adapter steps above already exist in `scripts/vidya/adapters/serving_call.py` (`project_record`, strict `record_sha256`/schema refusal, absent-timing skip) and are wired in `scripts/vidya/ingest_sources.py` (`orchestrator-serving-call`); `tests/vidya/test_serving_call_adapter.py` + `test_ingest_sources.py` 106 pass. The README source row was stale ("none (TODO)") and is corrected. Window aggregates stay under the 'Remaining window-aggregate design' note above (separate producer).

  Remaining window-aggregate design: seal native window membership and denominators before consumption; decide whether these are a separate producer or a projection over that sealed manifest. The accepted per-call reader emits no share. `cache_n` is validated native metadata, not a projected metric without an established improvement direction.

  - [x] **VB-SERVE-TIMING-READER — implement bounded strict per-call reader/join contracts.** ✅ 2026-10-06 — [Reader contract](../../docs/reference/serving-call-reader-contract.md), original CI37443323928 TRUE87/87, exact tested source promoted mainaf27797f. No organic/window timing claim; parent remains open.

  Era row ST1 (`scope: serving_timing`) is in `epyc-orchestrator/orchestration/instrument_eras.yaml` (orch 4e23e553). This is the read side of VB-SERVING-DF2's first producer.

## VB-KVU-P3 — 2026-10-03 MI210 X0-window measurements (filed 2026-10-03, ak-ds41-main)

- [ ] **VB-KVU-P3 — write side + projection for the 2026-10-03 X0-window measurement records** (CLAUDE.md *Belief
  Kernel — wiring new sources*; source row in `scripts/vidya/adapters/README.md`). None of these is covered by
  VB-SERVE-TIMING-1, which reads only the orchestrator's per-call `serving_call.v1` records; these are standalone
  probe and profiler outputs that today exist only under `/mnt/raid0/llm/tmp/` (scratch).
  - **KVU-18 / P3** (`/mnt/raid0/llm/tmp/x0-27b-quants/results/p3/{a1,a0,b,p3_result}.json`, producer
    `p3_kvu_probe.py`): per-level decode tok/s (drafted and no-draft), acceptance, neighbour count and restore
    records, ABA drift; batched-bench S_PP/S_TG kvu vs no-kvu. Locator = run × level × variant × rep. Caution that
    must ride every projection: `/slots` under-reports restored slots (fill comes from the restore records).
  - **INF-80 EXL3-X0** (`results/shape_{a,b}.*.json`, `kld.{base,q4}.json`, `summary.json`; producers
    `x0_shape_a.py`, `x0_shape_b.py`, `x0_kld.py`): per-launch serving tok/s, acceptance, own-PID VRAM peak, HIP
    dlopen proof; KLD/PPL statistics. Locator = run × arm × shape × np × context × sampling × launch.
  - **UFH14-A2 probe** (`results/probe/probe-decode-vs-context.*.json`): the DFlash2 production-shape cells also
    satisfy VB-SERVING-DF2's "DFlash2 at the production shape" producer — project them there, not twice.
  - **EXL3-LB1 profile** (`/mnt/raid0/llm/tmp/lb1-profile-20261003/summary.json`): per-kernel % of HBM roofline,
    VGPR/waves, dispatches. Locator = model × shape (tg128/pp8/pp16) × kernel × weight type.
  - First step: copy the four result trees to a durable research results path and record their digests (tmp is
    scratch). Then one strict adapter per producer; all grade `Judged/Located` through `claim_tuple.grade()` (n ≤ 3,
    no codified protocol). No new ladder.
  - 2026-10-04 extension: the kernel-route A/B (VB-KQROUTE-1) ran `x0_shape_b.py` as its serving leg,
    `/mnt/raid0/llm/tmp/kqroute-build-20261003/results/20261004T021143Z/x0b/{A,B}/shape_b.q4.rep1.json`
    (`x0.shape_b.launch.v1`). Same producer class as INF-80 EXL3-X0 above, so it projects through this task's
    shape_b adapter with the arm's kernel-store build id added to the locator; it is not a second source.

## VB-KQROUTE-1 / VB-CPU-XFER-1 — 2026-10-03/04 kernel A/B harnesses (filed 2026-10-04, ak-ds41-main)

- [ ] **VB-KQROUTE-1 — write side + projection for the GPU kernel-route A/B harness** (CLAUDE.md *Belief Kernel —
  wiring new sources*; source row in `scripts/vidya/adapters/README.md`). Producer
  `/mnt/raid0/llm/tmp/kqroute-build-20261003/ab_kqroute.sh`; first run `results/20261004T021143Z/` (EXL3-LB1 seed #1,
  gfx90a MMVQ→MMQ route, commit `289cbafa3`). Inputs: per-launch `bench.<model>.<round><arm>.json` llama-bench JSON with
  `.stderr.log` and `.vram.txt`, `route.*.log`, `tbo.{A,B}.log` (`test-backend-ops` correctness), `report.txt`.
  First step: copy the raw evidence (the whole `results/<ts>/` tree, plus `patched_commit.txt` and the linkage logs) to a
  durable location and record digests — `/mnt/raid0/llm/tmp` is scratch. Then a strict adapter: locator = run × model ×
  test (pp<n>/tg128) × arm × launch; arm = kernel-store build id from the launch (A `gpu-20260929-90c12df42`, B
  `gpu-20261003-289cbafa3-kqroute`); carry binary digest, ggml linkage proof and own-PID VRAM; a `tbo` FAIL voids that
  arm's speed rows; report the A-spread as the floor. The `x0b/` serving leg projects under VB-KVU-P3, not here. n = 2 A /
  1 B per test, no protocol → `Judged/Located` via `claim_tuple.grade()`; no new ladder. Add a write-side
  `belief_measurements.jsonl` to `ab_kqroute.sh` before its next run.
- [ ] **VB-CPU-XFER-1 — write side + projection for the CPU transfer A/B harness (`q38fn-transfer` `report.py`)**
  (CLAUDE.md *Belief Kernel — wiring new sources*; source row in `scripts/vidya/adapters/README.md`). One source class,
  two runs: `/mnt/raid0/llm/tmp/q38fn-transfer-20261003/runs/20261003T172030Z/` and the iqk allowlist A/B
  `/mnt/raid0/llm/tmp/iqk-allow-20261003/ab-runs/20261003T174700Z/` (same `report.py`). Inputs per run: per-launch
  `bench-*.jsonl` llama-bench JSON, `.sidecar.json` (load time, THP state, foreign CPU %, NUMA placement), greedy coherence
  token ids, `REPORT.txt`. First step: copy the raw evidence (both run dirs plus `report.py`/`run_transfer.sh` and their
  digests) to a durable location — `/mnt/raid0/llm/tmp` is scratch. Then a strict adapter: unit = one launch, value =
  `avg_ts` (t/s, higher = better), locator = run × model × round × arm; sidecar-excluded launches (foreign CPU over
  `FOREIGN_MAX_PCT`, THP shim off) are declined with the reason, never projected; the coherence comparison against the
  reference arm rides as a verifier fact per arm; arm identity from `build_commit`/binary digest and the env arm. n =
  rounds per arm, no protocol → `Judged/Located` via `claim_tuple.grade()`; no new ladder. Add a write-side
  `belief_measurements.jsonl` to `report.py report` before its next run.

## VB-COHGATE-1 / VB-SC75-CLS / VB-YARN-E1 — coherence verdicts and the long-context needle runs (filed 2026-10-04, workspace-ec)

- [ ] **VB-COHGATE-1 — write side for `coherence_gate` verdicts.** (CLAUDE.md *Belief Kernel — wiring new sources*;
  RECTIFY §6c.) The shared library on research main 95157ad7 (`scripts/lib/coherence_gate/`, schema
  `epyc.coherence_gate.v1`) and the tier-2 judge `POST /v1/typed/coherence_judge` (orch f8c9c0a3, TD-30 in
  `typed-decision-plane.md`) produce verified findings, but no tuple is written yet.
  - Fields, per stream: anchor id, tier-0 identity, ground-truth result, `degeneracy.v2` class plus classifier id,
    judge verdict plus `calibration_id`, and text/ids digests.
  - Per gate: aggregate PASS / FAIL / INCOMPLETE. INCOMPLETE never projects as a pass.
  - A strict adapter projects the verdict record and `claim_tuple.grade()` decides; no new ladder.
  - Era-labelled by `schema` once TD-30e's OC1 row is ratified. Before that, project as a prior only.
  - The source-table row text is prepared for the owning session in `/mnt/raid0/llm/tmp/wrapup-ec-gpublock2/INDEX_ROWS.md`.
  - Done when a `belief_measurements.jsonl` write-side hook exists in `coherence_gate`'s CLI / `evaluate()` and one
    real gate run ingests.
- [ ] **VB-SC75-CLS — SC75 sidecars must say which classifier labelled them (patch 05, owner workspace-ec under
  EVL-47).** Apply `classifier-rectify/05-vidya-inf70-arm-capture.patch` (durable copy
  `artifacts/gpu-block-27b-20261004/analysis/classifier-rectify/`). It adds an informational
  `extra.coherence_classifier` census to `scripts/vidya/adapters/inf70_serving_arm_capture.py`. Rows with no
  `classifier` are named `inf70-classify.v1|synthetic-ids(uniq/top/run vacuous)`. It also adds one test. All 37
  adapter tests pass on the patched copy, and the grade is unchanged. Done when the patch is on root main with tests
  green, and the next `inf70-arms` ingest shows the census.
- [ ] **VB-YARN-E1 — write side for the INF-59 long-context needle runs (E0 runner, E1 window).** (CLAUDE.md *Belief
  Kernel — wiring new sources*; ASSESSMENT §6 E0.) The runner forked from Q38-T7's needle logic
  (`yarn-context-extension-research.md` YARN-E0) produces, per (arm, length): needle correctness in `coherence_gate`
  `needle` grader form, prefill/decode tok/s, KFD peak and the rope proof lines. The locator is model × arm (A0 native,
  A1 YaRN f2, A2 raw extrapolation) × haystack length × depth × build id × argv digest. The paired short-context set
  projects through VB-COHGATE-1, not twice. With n=1 per cell and no codified protocol, it grades as
  `Judged/Located` via `claim_tuple.grade()`. Write a `belief_measurements.jsonl` from the runner before E1 runs.
  The source-table row text is prepared in the INDEX_ROWS file above. Done when E1's records ingest.
  - *(2026-10-04, workspace-ec; not ticked.)* E1 ran (FAIL by C4 memory only) **before** the write side existed: the
    runner wrote no `belief_measurements.jsonl`. The gate records are durable in `artifacts/yarn-e1-20261004/`
    (`gate/verdict.json`: per-criterion results and per-depth needle status for A0/A1 at 128K/240K and A1 at
    400K/500K; `kfd/*.summary.json`: peaks). An adapter projecting `verdict.json` must carry only what it records — the
    build id and argv digest sit in `run_e1*.log`, not the verdict — and grades no higher than `Judged/Located`.
    Wire the runner's write side before YARN-E1-MEM / YARN-E1-A2 / YARN-DCA-E1 run, so those windows ingest natively.
  - *(2026-10-05, workspace-ec; not ticked.)* The INF-59 CPU leg (YARN-CPU, Qwen3.6-35B-A3B, CN vs CY2) also ran
    pre-hook: `yarn_cpu_leg.py` wrote no `belief_measurements.jsonl`. Its durable record is
    `artifacts/yarn-e1-20261004/cpu_leg/verdict.json` (schema `inf59.yarn_cpu_leg.v1`), and its locator adds device
    (CPU) and the turn index. The projection carries what that file records and nothing more; the build id and argv sit
    only in `block.log` and the scratch server logs. Wire both runners' write side before YARN-CPU-512k runs.

  - [ ] **VB-YARN-E1-JETLONG-4XJ — project complete full-scope records for the new JETLONG-SMALL-RECALL 4xJ/static-YaRN comparison.** Accept only original COMPLETE arm records with `native_prompt_n=130000` and unchanged fixture/model/build/recipe identity; require both Y and J arms before emitting a comparison. Preserve six-needle count/6 as one prompt/run (not six reps), strict ordered-JSON scoring, source/binary/DSO identity, captured process/affinity/maps, sampled RSS, and explicit failed, cutoff, malformed, missing, or incomplete dispositions. Do not compare against historical Y3/6, backfill tuples, or infer from the short smoke. Reuse INF-59/VB-YARN-E1's measurement source class and `claim_tuple.grade()`; run the planning-context canary before any belief-gated use. Current preparation has no tuple/canary and full scientific work remains open.
- [ ] **VB-YARN-DEPTH-RECIPE — write side and adapter for the q36 depth-recipe native-window validation** (filed 2026-10-05,
  workspace-ec). Producer: `q36_depth_recipe.py` on Qwen3.6-35B-A3B CPU, canonical :8070 recipe, 2026-10-05 12:10Z.
  Record shape: per (arm: native vs YaRN ×2) and (depth: 0%/30%/50%/70%/90%), needle correctness, decode tok/s, and
  MTP acceptance; summary.json and summary.md durable copies in `artifacts/yarn-native-window-20261005/`.
  Verdict: static YaRN ×2 **FAILS the operator rule** "YaRN must not regress inside native window" (1.3% cost at depth 0,
  7.6% at 34k decode, MTP 53%→48%, greedy diverge 7/20). Grades as `Judged/Located`, not qualified measurement.
  Done when the adapter projects the result and the verdict rides through the fold.

## VB-KVU-PF — KV prefix-fork program measurement sources (filed 2026-10-04, ak-ds41-main)

  - Prospective DF2-13 and DF2-12 instances capture exact inputs and model/ELF/source/grant identity, native output tokens and actual draft/accept counts, warm/cold or mixed-slot interleaving and checkpoint/fork traces; missing evidence is UNKNOWN. The inherited 0.001-nat comparator is historical, not a same-run floor. KPF-18.2 also captures active task/slot IDs and native fork-operation trace; absent hit/minimum values remain NULL and SWA bounds are not prefix hits. Preserve partials and original exposures; use the existing shared grade, with writer/reader and planning canary still pending.

- [ ] **VB-KVU-PF-KPF181-WIRE** — wire and verify prospective KPF-18.1 native capture; preserve every attempted and ambiguous cell, configuration and identity; refuse incomplete/tampered attestation, preserve unknowns, test real native records and pass the planning-context canary before calling it wired. Capture raw active-request slot observations and errors with monotonic windows and match native task/slot IDs to response timings; keep post-completion state separate and refuse missing, conflicting, unmatched or late samples as UNKNOWN. No retrospective measurement invention or grading rule.

- [ ] **VB-KVU-PF-CHAT-TRACE-WIRE** — capture the prospective KPF-18.3 chat attribution raw events and identities at write time; project only complete attested observations via existing `ClaimTuple.grade()`, refuse missing/tampered/mismatched inputs, preserve unknowns and pass the real planning-context canary before calling it wired. No new grading rule or historical backfill.

- [ ] **VB-KVU-PF — write side + projection for RTG-58's measurement records** (CLAUDE.md *Belief Kernel*). Producers:
  [`kv-prefix-fork-and-paged-attention.md`](kv-prefix-fork-and-paged-attention.md) KPF-18 (fork-vs-fresh equivalence + TTFT),
  KPF-26 (trunk-first dispatch), KPF-33 (sequence-affine allocation), KPF-42 (`kv_rows` A/B vs KVU-19b), KPF-53 (cascade).
  Record shape: per-run JSON with binary sha, argv, arm, prompt-set hash, equivalence verdict, TTFT, prefill tokens,
  unique cells, decode tok/s. Wire the write side before KPF-18's first run; project into `ClaimTuple` and let
  `claim_tuple.grade()` decide — one ladder, no new grading rule. Done when KPF-18's runner emits the record and the
  adapter projects it.
  - Record (`epyc.kpf.run.v1`, one JSON per run, appended to a `belief_measurements.jsonl` by the runner): `binary_sha256`,
    `argv` (full list; `--slot-fork-min-tokens`, `-b/-ub`, KV mode read back from the launch log), `arm` in
    {`fork_off`,`fork_on`}, `prompt_set_sha256`, `equivalence` COUNTS vs the fresh-vs-fresh control floor, `ttft_ms`,
    `prompt_tokens_processed`, `cache_n`/`n_fork_tokens`, `unique_cells_peak`, `decode_tok_s`, `window_id`,
    `gpu_window_id`, `start_utc`/`end_utc`, `host`. Source class `measurement`; n=1 without a cited protocol grades
    `Judged/Located`; no backfill. Unchanged ladder, no new rule.
  - Done-when addendum: the adapter test projects a KPF-18 dry-run record (not a hand-written one) and the
    source-table row (`KV prefix fork / cache-aware dispatch` in `scripts/vidya/adapters/README.md`) is amended to name the locator and the window ids.
  - Producers (2026-10-20): the P1 branch is `experimental/kv-prefix-fork-p1r-20261020` (worktree
    `/mnt/raid0/llm/worktrees/kv-prefix-fork-p1r-20261020`); the KPF-18 runner is
    `/mnt/raid0/llm/tmp/kpf-p1-20261004/kpf18/kpf18_gate.py` (not yet run; emits the record above).
- [x] **VB-KVU-PF.1 — extend the epyc.kpf.run.v1 record for the KPF-17.x/18.x rows before they run.** Add the fields the new rows produce (checkpoint_set, per-component hit lengths and their minimum, hit tokens, tokens lost to a missing checkpoint, drafter drop kind, request lane, cache-skip control, pinned count) to the runner's emit and the adapter test, fix the known runner gaps listed in the source-table row (arm label on the off run, null unique_cells_peak and aggregate decode outside item 7, eq_summary key names), and project them through claim_tuple.grade() with no new ladder or rule. Done when the adapter test projects a dry-run record carrying the new fields. ✅ 2026-10-20 — adapter `scripts/vidya/adapters/kv_prefix_fork.py` (ingest source `kv-prefix-fork`) + `kpf_ext` runner emit; adapter test projects a dry-run record generated by the real runner (branch feat/vb-kvupf1-20261020 @ 8fab559fa, merged to main); runner swapped in at /mnt/raid0/llm/tmp/kpf-p1-20261004/kpf18/kpf18_gate.py (sha256 8ec9ec1c…, previous kept as .pre-vbkvupf1-20261020).
- [x] **VB-KVU-PF.2 — the read side rejects the KPF-18-S1 sidecar, so 0 of 15 records project** (filed 2026-10-22, workspace-f8). The write side is wired: `/mnt/raid0/llm/tmp/kpf18-s1/out/belief_measurements.jsonl` carries all 15 S1 records (`epyc.kpf.run.v1`, self-hashed). But `kv_prefix_fork.native_rows()` voids the whole file on the first invalid line, and 13 lines are invalid: `validate_row` allows `arm` only in {fork_off, fork_on, fork_on_dflash2_off, champion}, while S1 emits sub-arm names (`A_ckpt`, `A_tailonly`, `B_identical_resend_and_child_eq_trunk`, `C_length_sweep_drafter_on`, `D_hit_count_prediction_dflash2`, `cold_control_probe`, `parity_dflash2_*`, `policy_control_dflash2`, `chunk_split_cost`, `warm_vs_cold_long_prompt`, `item3_localisation`), and `parity_summary` has no `rows_sha256`. Checked read-only on 2026-10-22: `native_rows()` returned 0 natives. Fix: one contract, one ladder. Either the runner emits `arm` in the fork vocabulary and moves the sub-arm to `kpf18_arm` (already present on S1 records), or the adapter takes `kpf18_arm` as the locator and validates `arm` against the vocabulary plus a declared sub-arm set. Summary rows with no rows file are emitted as attested-absent, never dropped. No new grading rule. Done when the adapter test projects the real S1 sidecar (15 natives, the item-2 and item-3 records included) and `cli.py ingest kv-prefix-fork` on a copy produces one claim per record. ✅ 2026-10-22 — adapter accepts the declared KPF-18 sub-arm set (`KPF18_SUB_ARMS` per `kpf18_item`, `kpf18_arm` as locator) and projects a no-`rows_sha256` record attested-absent; real S1 sidecar 0→15 natives (all Judged/Located, 1 attested-absent: parity_summary), committed as fixture `tests/vidya/fixtures/kpf18_s1`; `cli.py ingest kv-prefix-fork` on a copy into a scratch ledger = 15 rows, 15 claims (45 frames); writer now always hashes a rows file (research f8/kpf18-rowsha-20261022 @ 5ed8a628d; root branch f8/vbkvupf2-20261022).
- [x] **VB-KVU-PF.3 — the KPF-18-S1 remainder sidecar uses `kpf18_item` 185, which `KPF18_SUB_ARMS` does not declare, so the read side would void all 14 records** (filed 2026-10-23, workspace-f8). Source-table row `KV prefix fork / cache-aware dispatch` already exists and covers this source; no new row. Write side is live: `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf18-s1-remainder/out/belief_measurements.jsonl` (14 records, arms `A_tailonly_tail512|tail1000`, `item2_pcache_g<G>s<S>`, `long_teacher_forced`, `kpf191a_flagoff_g<G>`, `hsf_L<L>`). Next step: add `185: (...)` to `KPF18_SUB_ARMS` in `scripts/vidya/adapters/kv_prefix_fork.py` with those patterns, extend `tests/vidya/fixtures/kpf18_s1`, run `cli.py ingest kv-prefix-fork --path` on the sidecar and require 14 of 14 project; note that step-7 `hsf_*` timings carry the `graphs disabled` label and must not be graded as the production rate. The `kpf13_restore_ab.py` and `kpf174_swa_drafter.py` drivers have no adapter hook yet: check whether they emit a sidecar and, if not, wire it at the first result, not after.
  - *(2026-10-23, f8 vb-kvu.)* **DONE.** `KPF18_SUB_ARMS[185]` declared (`A_tailonly_tail<N>`, `item2_pcache_g<G>s<S>`, `long_teacher_forced`, `kpf191a_flagoff_g<G>`, `hsf_L<L>`); fixture `tests/vidya/fixtures/kpf18_s1r` (sidecar only, aggregates); `cli.py ingest kv-prefix-fork --dry-run` on the real sidecar: rows=14, projected, refused=0, 42 frames. The `hsf_*` records project only equivalence counts or hit tokens, never a timing, so none is read as a production rate (the `graphs disabled` label stays in `launch_prefix`).
- [x] **VB-KVU-PF.4 — the kpf13 and kpf174 sidecars void on read (filed 2026-10-23, f8 KPF read-out).**
  - The write side is live. Both files are under `/mnt/raid0/llm/tmp/f8-launchers-20261023/`:
    - `kpf13-1-reduced/out/run/belief_measurements.jsonl` holds 2 `epyc.kpf.run.v1` records (`kpf_task` KPF-13.1, arm `restore_default`).
    - `kpf17-4-19-1a-27b-dflash2/out/run/belief_measurements.jsonl` holds 5 records (`KPF-17.4+17.4a+19.1a`; arms `kpf174_191a_flag_off`, `kpf174_mut_dft_partial_noop`, `kpf191a_flag_on`, `kpf191a_mut_dft_no_transfer`).
  - `kv_prefix_fork.validate_row` rejects every line: the arm is in neither `ARMS` nor `KPF18_SUB_ARMS`, and the kpf174 records also lack `equivalence`. So `native_rows()` returns 0 of 2 and 0 of 5 (read-only dry check, 2026-10-23).
  - No new source row is needed: the `KV prefix fork / cache-aware dispatch` row covers RTG-58 native records.
  - Next steps:
    - Declare a vocabulary keyed by `kpf_task`: the KPF-13.1 arm (`restore_<config>`) and the kpf174 launch arms.
    - Project the rule COUNTS as the tuple, not a pass word: cell pass/fail/invalid per arm, `decision_grade`, and the mutant DETECTED counts.
    - Make kpf174 emit an `equivalence` block, or make that block optional for correctness-class records.
    - Add fixtures from these two sidecars and require 2/2 and 5/5 to project.
    - The first record in each file is the aborted 14:19Z launch (0 cells). It must project as an attested zero-cell attempt, not be dropped.
  - *(2026-10-23, f8 vb-kvu; partial, NOT ticked.)* Read side done: `CONFORMANCE_ARMS` keyed by `kpf_task` (KPF-13.1 `restore_<config>`; KPF-17.4+17.4a+19.1a four launch arms), `equivalence` not required for conformance records, counts from the record's own verdict block (kpf13 `equivalence.configs` A+B; kpf174 `launch_verdict`; mutants project the DETECTED fraction), a zero-cell record projects as `kpf_conformance_cells_scored` = 0 attested-absent. Fixtures `kpf13_restore`, `kpf174_swa`.
    - kpf13: dry-run ingest rows=2, projected, refused=0 (0 cells; 20/24 pass).
    - kpf174: still 0 of 5, and now for a different reason than the arm vocabulary: `record_sha256` does not re-derive. The writer hashes `geometry.pruned`, a dict with INT keys (`{2148, 4096, 10240}`), before JSON stringifies them, so `sort_keys` orders `[2148, 4096, 10240]` at write time but `["10240", "2148", "4096"]` on re-read. Re-sealing with int keys re-derives all 5. The read side refuses (with that reason in the message) rather than loosening the integrity gate. Write-side fix filed as **VB-KVU-PF.5**; the .4 done-condition (5/5) closes when it lands and the launch is re-recorded or the 5 records are re-sealed by the writer.
  - ✅ 2026-10-23 (f8): closed by VB-KVU-PF.5 — kpf18 185 14/14 and kpf13 2/2 (adapter 6f1443abd), kpf174 5/5 after the write-side reseal.
- [x] **VB-KVU-PF.5 — `kpf174_swa_drafter.py` `finish_record` hashes int-keyed `geometry.pruned`, so its `record_sha256` cannot be re-derived from the stored JSON** (filed 2026-10-23, f8 vb-kvu). Research-driver task, not a read-side one. Next step: in epyc-inference-research `scripts/benchmark/kpf174/kpf174_swa_drafter.py` (and any driver using `k13.sha256_json` over int-keyed dicts) stringify dict keys (e.g. `{str(c): ...}`) when building `geometry` or hash the JSON round-trip of the record; add a test that `sha256_json(json.loads(json.dumps(rec))) == rec['record_sha256']`; then a one-shot writer-side re-seal of the 5 records from `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf17-4-19-1a-27b-dflash2/out/run/belief_measurements.jsonl` (no field changes beyond the digest) and `cli.py ingest kv-prefix-fork --path` requiring 5 of 5.
  - *(2026-10-23 17:05Z, f8 subagent; write side FIXED, re-ingest is the coordinator's.)* Cause confirmed on all 5 records: each stored sha equals the hash of its body with `geometry.pruned` keys turned back into ints.
    - Fix on research `f8/kpf-gpu-followups-20261023` @ `0208f4918` (pushed, in `1db8ac394`). `kpf13_restore_ab.seal_record` hashes the JSON round-trip form, which is the adapter's `_digest` form, and both the kpf13 and kpf174 `finish_record` use it.
    - Tests: `sha256_json(json.loads(json.dumps(rec))) == rec['record_sha256']` for a kpf174 record with int-keyed `pruned`, plus the adapter digest on the written record and the belief line.
    - Re-seal script `scripts/benchmark/kpf174/reseal_records.py`. It writes a NEW file and never overwrites; it refuses a mismatch that the int-key cause does not explain.
    - Applied: `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf17-4-19-1a-27b-dflash2/out/run/belief_measurements.resealed-vbkvupf5.jsonl`, sha256 `e312bb8b…`, with a `.manifest.json` beside it.
      - 5/5 rows were resealed. No field changed beyond the digest (verified row by row).
      - The original `belief_measurements.jsonl` (sha256 `1f5f9a81…`) is kept.
      - All 5 resealed rows pass `validate_row` in the origin/main adapter, and `native_rows` returns 5.
    - Next: `cli.py ingest kv-prefix-fork --path <resealed file>` requiring 5 of 5 (coordinator), then tick.
  - ✅ 2026-10-23 (f8): research `0208f4918` — `seal_record` hashes the JSON round-trip form (the adapter's digest form) + round-trip digest test; `scripts/benchmark/kpf174/reseal_records.py` wrote `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf17-4-19-1a-27b-dflash2/out/run/belief_measurements.resealed-vbkvupf5.jsonl` (5/5 resealed, only the digest changed, original kept). Re-ingest on origin/main `cli.py ingest kv-prefix-fork --path <resealed> --dry-run`: units 1, projected 1, refused 0, rows 5, frames 15 → 5 of 5.
  - *(2026-10-23, f8; per-arm coverage note, no task to tick.)* 17.4b rules-v2 arms `kpf174b_c1_spec_off` and `kpf174b_junction_sweep` added to `CONFORMANCE_ARMS["KPF-17.4+17.4a+19.1a"]` (honest arms, pass fraction; no new rule). Fixture `kpf174b_rules_v2`. Dry-run: `kpf-gpu-followups/out/kpf174b-specoff` 1/2 and `kpf174b-sweep` 4/10 now project 1 each, refused 0. Their `records/*.json` copies are pretty-printed duplicates of the same records: they decline (the reader is JSONL-only) and are outside the source's discovery globs, so they never double-count.
  - [x] **VB-KPF174C-ARM — declare the KPF-17.4c bisect arm before its run lands (filed 2026-10-24, workspace-f8 sweep).** Add `kpf174c_bisect_spec_off` (rules v1 sha `b871d9a0…`, research `f8/kpf174c-bisect-20261024`) to `CONFORMANCE_ARMS` in `scripts/vidya/adapters/kv_prefix_fork.py` as an honest arm (pass fraction over the judged layout-matched pairs; `locus` / `explains_174b` carried in `extra`, never re-derived), plus a fixture from the driver's fake-server record. No new rule; the existing KV prefix fork source row covers it. Done when a dry-run ingest of a fixture record projects 1 and refuses 0. ✅ 2026-10-24
    - *(2026-10-24, workspace-f8 sweep.)* Writer: research `f8/kpf174c-bisect-20261024` @ `1157adc2f` adds `launch_verdict` {verdict = the predeclared `locus` word, attempts/pass/fail/invalid/out_of_scope} counted in layout-matched PAIRS (Xc~Cmask, Xe~C0, Ks~C0 per attempted cell, so pass + fail + invalid = attempts exactly), derived from the same `decide()` output as the decisions; `cells_interrupted` now also counts an attempt a later resume completed; rules sha `b871d9a0…` and PREDECLARATION sha `1aca75d5…` unchanged (a test pins the rules sha); 141 tests. Launcher pin moved 18c3b9800 -> 1157adc2f (`AMENDMENT-pin.md`, DRY rc 0). Reader: `kv_prefix_fork.py` `CONFORMANCE_ARMS["KPF-17.4c"] = kpf174c_bisect_spec_off`, metric `kpf174c_matched_pair_identical_fraction` (pairs basis), `locus` / `explains_174b` / `decision_grade` copied verbatim into `extra`, varied = restore_path, kv_layout; fixture `tests/vidya/fixtures/kpf174c_bisect/` from the driver's own LayoutFake run (aggregates only); 3 new tests; `pytest tests/vidya` 2889 passed, 369 skipped. Dry-run ingest of the fixture (as-of 2026-10-24T09:40Z): matched 1, projected 1, declined 0, refused 0, frames 3.

- [x] **VB-KVU-PF.6 — the KPF-18 item-3 v2 sidecar voids on read, and the step-7 graphs-ON sidecar projects only a vacuous hit count (filed 2026-10-24, workspace-f8 read-out).** The `KV prefix fork / cache-aware dispatch` source row already covers both, so no new row is needed. The write side is live.
  - `kpf18-item3-v2-sameshape` (`/mnt/raid0/llm/tmp/f8-launchers-20261022/kpf18-item3-v2-sameshape/out/belief_measurements.jsonl`, 4 lines). `cli.py ingest kv-prefix-fork --dry-run` gives matched 1, projected 0, declined 1, rows 0. `validate_row` rejects all 4 lines because arm `item3v2_load<N>` is not a declared sub-arm of `kpf18_item` 3. The lines also carry no `kpf18_arm`, and line 3 is the budget-aborted partial load 2. The verdict (`FORK_EFFECT`, per-load classes) lives in the records' `extra.item3v2`, not in `equivalence` (vs_fresh n = 0).
  - `kpf18-s1-step7-graphs-on` (`/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf18-s1-step7-graphs-on/out/belief_measurements.jsonl`). The dry run gives projected 1, rows 3, 9 frames, but each claim is `kpf_hit_tokens = 0`. The rates and the predeclared graphs-sensitivity label are not projected. The `KPF18_SUB_ARMS[185]` comment says `hsf_*` timings are graphs-disabled, which is false for this sidecar (graphs ON, proven from the server environ).
  - Next steps:
    - Declare the item-3 v2 arms (research writer: add `kpf18_arm`; read side: `KPF18_SUB_ARMS[3]`).
    - Project the per-load class counts as the tuple. The aborted partial load must project as an attested incomplete attempt, not void the file.
    - For `hsf_L<L>`, either project nothing (decline) or project the per-cell medians with the run's graphs state read from `launch_prefix`/`env`. Never project a hit count of 0 as a measurement, and never word a claim as a graphs-only cause: the rule attributes the ON/OFF difference to graphs ON plus the knob plus the fresh load / step-7-only history jointly.
    - Add fixtures from both sidecars (aggregates only).
  - ✅ 2026-10-24 (f8, branch `f8/vidya-wire-1024`): `kv_prefix_fork.py` now declares `KPF18_SUB_ARMS[3] = item3v2_load<N>`.
    - Locator: the launcher wrote no `kpf18_arm`, so the record is located by its arm token plus its own `item3v2.load` (a partial record by `partial: true`). A `kpf18_arm` that is present must still match. This replaces the writer-side `kpf18_arm` step for this record set; a future item-3 writer should still emit it.
    - Each load projects `kpf18_item3v2_judged_pairs_fork_effect_candidate`. This counts the judged pairs (the `*_recorded` pairs are left out) and keeps each pair's class, margin and floor in `extra`. The verdict word is not re-derived.
    - The aborted partial load 2 projects `kpf18_item3v2_judged_pairs_scored = 0`, an attested incomplete attempt.
    - `hsf_L<L>` records validate but project nothing (declined). No 0 hit count is projected, and no graphs-only wording is used. The per-cell medians wait on a write-side change: the hsf record must carry its own graphs state.
    - Fixtures `kpf18_item3v2` and `kpf18_step7_graphs_on` (trimmed, resealed). Tests in `test_kv_prefix_fork_kpf_readout.py`; the S1R 14-of-14 test is now 11 of 14 with hsf declined.
    - Dry runs with `--as-of 2026-10-24T09:00:00Z`: item3v2 gives matched 1, projected 1, rows 4, frames 12, refused 0. Step 7 gives matched 1, declined 1, rows 0.
- [ ] **VB-KVU-PF.6a — write-side residuals of VB-KVU-PF.6** (filed 2026-10-24, f8 wrap-up; the midday wrap-up found them with no open box): (1) the KPF-18 `hsf_L<L>` step-7 records must carry their own graphs state (`hip_graphs`) before their timings can project, since they are declined today; (2) the item-3 writer must emit `kpf18_arm` so records stop being located by arm name plus `item3v2.load`. Producer side: the kpf18 driver on the research repo. Done when a fresh record of each projects with no read-side inference.
- [x] **VB-KVU-PF.7 — the KPF-18-S1.R3 sidecar voids on read (2026-10-24, workspace-f8 subagent).** `/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf18-s1-r3/out/belief_measurements.jsonl` (2 `epyc.kpf.run.v1` records, `kpf18_item` 186, arms `long6_teacher_forced` and `item2q_g3s2`) was DECLINED: `validate_row` refused both arms as undeclared sub-arms of item 186 (`KPF18_SUB_ARMS` had 3 and 181-185 only), and the verdict inputs live in each record's own top-level `r3.result`, not in `equivalence` (vs_fresh n = 0). Fix (`kv_prefix_fork.py`, modelled on VB-KVU-PF.6): `KPF18_SUB_ARMS[186]` = `long6_teacher_forced`, `item2q_g<G>s<S>` (research `kpf18_r3.py` `_step_open` names); a record must carry `kpf18_arm == arm` and its own `r3` block whose `step_id` is the arm's step, a predeclaration sha256 and a `step_complete` flag (a complete step must carry `result`). `long6` projects `kpf18_r3_long6_worst_child_vs_cold_mean_abs_dlogprob` (worst child-vs-cold, reps = `n_common_valid` positions, the six-pair cold floor as `observation.anchor_value` with `effect_rel`); `item2q` projects `kpf18_r3_item2q_fork_vs_own_pairs_ok` (`judge.n_ok` of `judge.n_pairs`, valid-Q count in claim and `extra`). The predeclared verdict word (`NOT_SATISFIED`, `G3S2_WITHIN_PLACEMENT_FLOOR`) rides verbatim in `extra.verdict` and `observation.outcome_native`, never normalised or re-derived; an unfinished step (or a result without the counts) projects `kpf18_r3_steps_scored = 0` as an attested incomplete attempt. Dry run (`--as-of 2026-10-24T12:00:00Z`): before matched 1, projected 0, declined 1, rows 0; after matched 1, projected 1, declined 0, refused 0, rows 2, frames 6; both claims grade `Judged`. Fixture `kpf18_s1_r3` (trimmed, resealed); tests in `test_kv_prefix_fork_kpf_readout.py`. No non-dry ingest was run.

## Research Intake Update — 2026-10-04 (decision tools, operator-approved Stage 4)

- [x] **VB-RI-CORRECTION-REFRESH-1 — Wire pinned research-intake correction/refresh events for graded current warrants and scoped withdrawals.** Extend the existing `research_intake.py` write path so an approved, digest-pinned correction retires only named current native support/opposition warrants and reprojects only reviewed current source claims through the existing literature ladder. Stage-1 demotions retain Hinted discovery projections; explicitly bound administrative `record_status` placeholders retain address/history without source-evidence warrants. Preserve immutable history, unaffected siblings and exact-ID retry after interrupted append. Validate against the approved filtered-index and warrant manifest; do not add a grading ladder or change policy. ✅ 2026-10-06 — scoped native producer/replay validated and canonical application verified; [final findings](../../docs/reference/intake-reverification-20261006.md).

- [ ] **VB-RI-OPS-WIRE — Capture and project the selected operational probe findings before their first run.** Register the six prospective source rows above at filing; integrate producer-authored claim elements and exact verifier propositions at each named task's native finalize boundary, reusing existing receipt/test/evaluation/SFT hooks where sufficient. Add only the necessary native-field projections and ingest dispatch; preserve unique run/case/arm/metric identity and bound read-set/raw-output digests. Leave absent protocol, counts, identity, labels and attestations absent; no historical tuple reconstruction. Adapters project ClaimTuple and claim_tuple.grade() alone decides warrant under the existing source-class rules; add no ladder or trust-boundary amendment. Test actual post-hook discovery/projection, missing-field refusal, changed-byte refusal and distinct-case identity before accepting the first result. Production-code fixes may proceed independently of measurement projection, but a new decision-bearing probe may not run before its write-side capture is present.

The six prospective producers are registered in [the source table](../../scripts/vidya/adapters/README.md#known-and-candidate-sources): REPL containment/Monty slice, paired REPL/OpenCode tasks, Memento selection, observed-outcome routing, native xLLM prefill, and intake payload conformance. Their exact original-write fields, controls and execution conditions are in the [approved plan](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#approval-and-exact-stage-4-filing-scope). Filing is not implemented capture; absence remains absence until each native hook and projection is verified. Current typed and SFT registrations retain their owners. No application probe, adapter deployment, warrant change or retrospective backfill is authorized by this filing.

**Proposed follow-up — 2026-10-04 retrospective:** VB-RI-OPS-WIRE also owns write-side capture
for `LRC-RI-CONCURRENCY`'s zero-inference event-loop conformance fixture, newly registered in
the source table. Bind the actual routing seam, delayed fake-backend identity, every request outcome,
fixture/read-set/producer digests and exact decided proposition; never interpret it as production
contention, routing quality or a measured speedup. Reuse existing native test hooks and the shared
projection rule. `EXL3-GRAPH-1` instead reuses the already-live
`VB-EXL3-CPU-GFX90A` writer/projection; it creates no second source or ladder.
The qualitative [retrospective](../../docs/reviews/research-intake-practical-applications-20261004.md)
itself is not a measurement-rate producer. These are proposed extensions, not amendments to the
already-completed decision-tools Stage-4 payload or authorization to run new probes.

**ID-RI-COVERAGE-DELTA implementation scope — 2026-10-04:** the existing intake conformance
source also covers version-2 source-scan coverage, owner/task-text outcome bindings and read-only
actionable/steering reconciliation fixtures. VB-RI-OPS-WIRE retains the prospective native capture
and projection task: bind the producer revision, fixture/read-set hashes, complete case results
and exact structural proposition at the test/check finalize boundary. A passing structural fixture
does not establish semantic equivalence, research completeness or project ROI. No new source class,
ladder or historical tuple reconstruction is introduced; ordinary regression results remain ordinary
test evidence until their native capture and projection are implemented.

**Additional PROPOSED follow-up — 2026-10-04 earlier-intake retrospective:** VB-RI-OPS-WIRE
also owns the four prospective profiles registered in the source table for `AC-CHECKPOINT-ALLOC`,
TD-1d.3's isolated question branches, mtp-refresh's same-backend target-precision control and
`INF37-MOE-Q8-FUSION`'s bounded GLU correctness/performance screen.
Reuse the shared research-screen receipt, typed decision receipts/VB-TDP-1 and native DFlash
carriers and native kernel evidence where their actual contracts suffice; add only missing producer-authored fields and
thin strict profile projections. Bind source/read-set/input/raw-output identities, exact
checkpoint or branch support, all outcomes and the task's deciding controls before the first
new decision-bearing run. Missing native fields remain absent; do not backfill old run pools,
double-project an existing metric or invent a grade/protocol. Allocation replay is not live
allocation performance; prefix cache reuse is not isolated-readout correctness; a CPU–HIP bridge
cannot establish a precision cause; static MoE tensor eligibility is not a runtime-path or performance claim. The [selected-source review](../../docs/reviews/research-intake-earlier-applications-20261004.md)
is qualitative and emits no omission rate or promotion warrant. These are new proposed owner
extensions, not amendments to the completed decision-tools checkpoint or application approval.

## VB-KVU-16B — concurrent-residency replay records (filed 2026-10-04, ak-ds41-main)

- [ ] **VB-KVU-16B — write side + projection for the KVU-16b concurrent-residency replay** (CLAUDE.md *Belief
  - *(2026-10-27, workspace-58 results harvest — projectability)* KVU-16b re-run PASS wrote out/belief_measurements.jsonl (2 ClaimTuples, source VB-KVU-16B); not projectable until a kvu16b adapter exists.
  Kernel*; source row in `scripts/vidya/adapters/README.md`). Producers: `kvu16b_residency.py` (workspace-ec, run
  `artifacts/gpu-block-27b-20261004/results/kvu16b/`, the invalid-PASS predicate) and its fixed-predicate slot copy
  `kvu16b_residency_slot.py` + `slot_report.py` (ak-ds41-main, `artifacts/gpu-slot-ak-20261004/`, arms skip OFF/ON ×
  `-b 2048`/`-b 512`). Records: per-request TTFT, max requests decoding at once, max resident cells, decode tok/s per
  request while all decode and while each prefill runs, s/iteration by occupied-cell bucket, KFD peak, coherence sha.
  Bind build id, argv sha, live knob env (`GGML_CUDA_FA_MASK_SKIP`, `GGML_CUDA_FA_SEQ_ROWS`), `-b/-ub`, and the
  predicate version. Cautions that ride every projection: the original runner's PASS is INVALID (stale `n_decoded`);
  skip-ON arms are the 19a+19b build INCLUDING commit 2, never the fold. One replay per arm, no protocol →
  `Judged/Located` via `claim_tuple.grade()`; no new ladder. Done when the runner (after KVU-16b-1) emits the record and
  the adapter projects the two durable runs above.
  2026-10-26 (workspace-58, drafted by codex-ni): the prospective current-champion replay at
  `/mnt/raid0/llm/tmp/cal-1026/kvu-16b/` writes `belief_measurements.jsonl` BEFORE its completion marker, using
  native admission metrics, report/predeclaration hashes, predicate version, argv and grant. Project these records
  and exercise the planning-context canary with the existing source class and `grade()`. This write hook alone
  does not close read-side wiring or validate old PASSes.

## VB-CH26A-M12-WRITE — M12 long-context reader recipe records (filed 2026-10-26, workspace-58; drafted by codex-ni)

- [ ] **VB-CH26A-M12-WRITE — project prospective M12 long-context recipe records through the existing measurement source class.** Preserve the writer's identity-before, original HTTP request/response JSONL, native checker receipt and overlapping per-request PID/startticks/KFD/VRAM/maps/affinity readings. Re-derive cache share and processed-token reuse predicates from original responses and bind source/recipe/model/server/library/grant/predeclaration digests. Missing or failed legs stay missing/failed; no generated performance/quality/protocol warrant. Existing ClaimTuple + claim_tuple.grade only; no second source-class ladder. Complete only after the native reader and planning-context canary pass. Producer scoped to CH-26a current-C5 recipe remeasurement, no AK search or promotion.
  - *(2026-10-27, workspace-58 results harvest — projectability)* CH-26a M12 C5 run PASS: HTTP JSONL + receipts exist (projectable), but no belief_measurements.jsonl was emitted and the ledger has 0 matches; projection + canary owed.

## KPF174D-C1-LAYOUT-SOURCE — KPF-17.4d c1 layout producer enrollment (filed 2026-10-26, workspace-58; drafted by codex-ni)

- [ ] **KPF174D-C1-LAYOUT-SOURCE** — register native honest/flag_on KPF-17.4d producer IDs in the existing kv-prefix-fork adapter, run server-free real-writer/projection fixtures before either GPU load, ingest each sealed run after completion, and prove planning-context retrieval canary before calling the loop wired. Evidence producer: /mnt/raid0/llm/tmp/cal-1026/kpf174d-c1-layout-source/; run data sibling honest/flag-on dirs.
  - *(2026-10-27, workspace-58 results harvest — projectability)* both kpf174d belief_measurements.jsonl files exist; projectable now, ingest + canary owed.

## VB-KPF18-G3-PHYSICAL-LAYOUT — KPF18 group-3 native layout control (filed 2026-10-27, workspace-58; drafted by codex-ni)

- [ ] **VB-KPF18-G3-PHYSICAL-LAYOUT** — the model-free gate is ACCEPTED: data-r4 57/57 + 6/6 controls, rc0 (source seal `be726b7a`, receipts `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-q0-r4/results/{data,controls}/UNITTEST.json`). Adapter IDs are registered. Still owed: validate the sealed r5 integration/phase bridge and canonical writer through an admitted PF (r5 must first rebind to the r4 packet/seal); capture ONE bounded original-a1 group-3 diagnostic only under an owner grant; keep every INVALID construction and the historical verdicts; inspect native target partitions and final-draft geometry before any scoped finding. No parent closure. The planning-context canary is still needed before calling the loop wired.
  - *(2026-10-27, workspace-58 results harvest — projectability)* r6 native control INVALID and r7/r8/r10-r13 replays failed: nothing projectable (r9 format regression is model-free correctness).

  - *(2026-10-30, R7 bounded software/native-writer diagnostic.)* Positive same-byte binding/resolver/writer evidence: 1,128 grids/eight events, fork 1, resolved-used 68,767/child maximum 35,999, actual final adjacent target/source partitions (256/4 tokens), both draft witnesses, four payload hashes and five native hashes. Explicit partial/framing-false; no full-series or measurement conclusion, no task tick, and no new source family/adapter/ladder. R6 remains INVALID; full integration/phase bridge and planning-context canary remain open. Keeper accepted the READY declaration only (READY-WAIT); no ARM, grant, or full normal execution is claimed. [Evidence](../../progress/2026-10/2026-10-30-hpr-r4-kpf18-r7-repairs.md) [belief: cc]

## VB-AK-LONGCTX — AutoKernel long-context surfaces and the production context-bucket analysis (filed 2026-10-04, ak-ds41-main)

- [ ] **VB-AK-LONGCTX — write side + projection for INF-81's long-context measurement sources** (CLAUDE.md *Belief
  Kernel — wiring new sources*; source row in `scripts/vidya/adapters/README.md`). Producers, all in
  [`autokernel-all-devices-all-dimensions.md`](autokernel-all-devices-all-dimensions.md):
  - **Production context-bucket analysis** (audit `/mnt/raid0/llm/tmp/ak-longctx-audit-20261004/REPORT.md` §0,
    produced PRE-HOOK; regenerated by AKX-ALL-7 from `llama-server-{8074,8083,8070}.log`). First step: copy the
    audit's bucket table and the log byte ranges it read (with digests) to a durable location — `/mnt/raid0/llm/tmp`
    is scratch. The regenerator writes `belief_measurements.jsonl` from its first run: server, log window, bucket
    edges, request count, decode wall share, decode/prefill rate per bucket. `:8083` per-request rates are
    concurrency-confounded: project wall shares only.
  - **C1 long-context surface** (AKX-ALL-4, floors AKX-ALL-6, DS41 restore-identity gate AKX-ALL-5) and **G4 GPU
    surfaces** (AKX-ALL-18). Per launch: target, anchor/candidate build id, recipe execution digest, prompt digest,
    slot-file digest, depth, np, request A `prompt_per_second`, request B `predicted_per_second`, request B `prompt_n`,
    restore verdict, held claims, residency proof (GPU), floor id + unit. Refusals are records with a reason and never
    project as speed rows. The restore-identity verdict rides as a verifier fact on the target, not as a measurement.
  - Locator is run-level (target × build × digests × depth × np × request × launch), never file-level.
  - A strict adapter projects into `ClaimTuple`; `claim_tuple.grade()` decides — one ladder, no new grading rule.
    Without a codified depth protocol every row is an OBSERVATION (`Judged/Located`).
  - Read side: VB-AK-BELIEF's planner reader presents these beliefs to the AutoKernel planner alongside the
    at-depth profile (AKX-ALL-7). G5 keep verdicts (AKX-ALL-17) cite the long-surface claims they rest on.
  - Done when AKX-ALL-4's runner and the AKX-ALL-7 regenerator emit the record shape, and one real long-surface run
    plus one bucket regeneration ingest.

## VB-AK-REALMASK — DS41 CPU FA real-mask identity source (filed 2026-10-07)

- [ ] **VB-AK-REALMASK — wire the producer-authored DS41 real-mask anchor-identity finding before its first real capture.** The native record binds model identity, the DS41 C++ mask source `src/models/deepseek41.cpp`, source/build commit and binary digest, recipe execution and request digests, actual mask dimensions/type/raw bytes and SHA-256, capture timestamp, original anchor/candidate repeat observations, and the exact identity proposition/verdict with any divergence detail. The strict reader reopens the producer bytes and projects only the verifier finding through the existing verifier carrier and `claim_tuple.grade()`. Synthetic fixtures prove source conformance only; do not relabel them as real-mask observations or reconstruct historical tuples. No throughput, candidate-promotion warrant, new ClaimTuple class, or grading rule. OP80 accepts wiring `check_cpu_fa_real_mask_identity` fail-closed into `cpu_fa_schedule` until the C++ probe/dump producer is available. Land capture and read-path controls before the first real-mask run.

## VB-AK-GPU-LOCAL-PHASES — original GPU local-owner receipts (filed 2026-10-07)

- [ ] **VB-AK-GPU-LOCAL-PHASES — enroll original `direct_held_intervals.v2` GPU/local release captures prospectively before consumption.** Bind selection, device/phase component artifact identities, exact decided ownership/exclusion proposition, original clock/acquire/release facts and v1/v2 provenance; project through existing ClaimTuple grading only. Never reconstruct missing ownership on read or infer CPU fraction from affinity, prediction or quiet. Capture starts only after independent harness review, targeted tests and owner-agreed live window.

## VB-AK-CPU-HELD-SEGMENTS — original CPU yielded-resource segments (filed 2026-10-07)

- [ ] **VB-AK-CPU-HELD-SEGMENTS — capture original native CPU per-generation close/release and reacquire/open components before prospective settlement.** Bind selection, native lock identities, original clock domain, actual physical fraction, generations and failed-owner refusals. Add a compatible versioned reader and completed-batch/new-watchdog epoch transition; preserve CPU v1 journals and never infer their missing held gaps from a side ledger on read. Project through existing ClaimTuple grading only; no new grading or policy amendment. Source audit confirms the v1 writer retains the first-acquire/final-release envelope and both serial settlement paths charge it unchanged; the CPU-window side ledger is not a discount input. No particular historical journal's overcharge is quantified or rewritten. This repair is separate from GPU local v2 and the bounded CPU quiet-wait fix.

## Non-inference campaign source wiring — 2026-10-05

- [x] **VB-NI-DURABILITY — capture and project docs/handoff durability scan receipts before the first broad scan.**
  Native carrier `epyc.evidence_durability_scan.v1` binds the source bytes actually read, document/line/target,
  emitted UTC, checker revision/digest, read-set and exact decided proposition. Project only native durability
  findings through the existing verifier class and `claim_tuple.grade()`. Preserve withheld, shared-clone-only
  and waived-lost outcomes as distinct caveats; never invent protocol, attestation or repetitions. Ordinary
  registry validation and its strict exit behavior remain independent of legacy-prose advisories.
  Owner: Codex NI05-13; scratch `/mnt/raid0/llm/worktrees/codex-ni-durability-20261005` and a separate root adapter lane.

- [x] **VB-CI-CONFORMANCE — capture original off-host selected-fixture conformance before artifact upload.**
  NI05-15's leaf producer records exact command/cases/statuses, UTC, tested source SHA(s), allowlisted runner
  context, explicit exclusions and original JUnit/log/source readset hashes. Project the exact native bounded
  boolean proposition through the existing verifier class and `ClaimTuple.grade()`; counts remain descriptive.
  Missing, inconsistent or entirely skipped cases stay diagnostics. No old-run backfill, protocol/trust
  amendments, scientific attestation, inference, performance or promotion authority. Initial CI runs remain
  ordinary validation evidence. Owner: Codex NI05-15; retired scratch custody `/mnt/raid0/llm/tmp/codex-ni-root-legacy-retirement-20261030/trees/codex-ni-ci-capture-20261005`.

  Completion evidence: 25/25 original execution and CLI-to-ledger fixtures passed in run `37278646239`;
  byte-preserved native receipt/request/log/JUnit/source artifacts are in `artifacts/ni05/ci-conformance-37278646239/`.
  Main progress: `progress/2026-10/2026-10-05-ni15-ci-conformance.md`. Existing shared grading only.


- [x] **VB-CI-CONFORMANCE-ATTACHMENTS — bind declared generated artifacts to prospective fixture receipts.**
  NI05-23: retain original generated bytes with named SHA-256 attachments beside the sealed request,
  log, JUnit and pre-execution source readset. Extend the existing strict CI reader to reopen and
  verify these bytes while projecting only the native `record.decided_proposition` through the
  existing verifier `ClaimTuple` and shared grade. No artifact-summary ladder, positive AST tuple
  inferred from a failed suite, or historical backfill. Outputs that never existed produce no
  attachment or generated-artifact claim. Preserve legacy receipt/projection behavior.
  Trigger: original run `37287200587` retains nine typed-AST pairs, a patch and summary; selected
  conformance remains false because the current position normalization and original gates fail.
  Owner: Codex NI05-23; existing source row `NI05 off-host selected fixture command executions`.

  Completion: NI23 source integrated as `a37c022fa6` and original CI `37291798409` passes 41
  producer/reader fixtures. Declared generated bytes are mandatory for decided receipts; legacy
  omitted extensions retain their shape. Original bounded capture is retained at
  `artifacts/ni05/custody-validation-37291798409/`; no historic receipt was resealed.

- [x] **VB-CI-CONFORMANCE-API-WIRING — capture subsequent named API and off-host unit commands prospectively.**
  NI05-25: use the existing producer/reader and sole grading ladder before each command runs.
  Keep distinct phase receipts, source readsets and exact argv; identify the entire synthetic-RAM
  pytest process as mocked host capacity, with a separate ordinary actual-host refusal fixture.
  Name unavailable GPU-store exclusions. Missing/failed collection remains a diagnostic or the
  original bounded false proposition, never a complete-unit pass. Earlier API runs remain ordinary
  validation evidence without retrospective tuples. Owner: Codex CI worker, main integration.


- [x] **VB-CI-PREFIX-DURABILITY — retain each original prospective phase before a later timeout.**
  NI05-29: original ninth `37295291738` loses all runner receipts before final upload. Preserve
  every completed phase independently, with unique immutable artifact names; declare the
  broad attempt timeout before execution and capture its actual interrupt/result. Original
  logs remain ordinary evidence, never a repaired/resealed receipt. Existing producer,
  verifier and shared grade only. The source table owns this prospective CI-command class.

- [ ] **VB-LINKAGE-GUARD — bind prospective static ggml dependency receipts at write time.**
  NI05-28 / NIB2-85: before fresh host execution, define a native dependency receipt and
  producer hook binding verifier/binary/tree identity, canonical expected roots, exact loader
  environment, original stdout/exit, UTC and immutable hashes. Reuse the existing typed linkage
  receipt precedent; refuse wrong identities, edits, missing hooks, vacuous and nonzero checks.
  Bind the receipt digest prospectively into eligible producer measurements. Dependency evidence
  has no ClaimTuple carrier class or standalone evidence_supports_claim until its warrant is
  ratified; no adapter or new ladder, historical backfill, dlopen/runtime-residency, performance
  or promotion claim. Source-table row filed before execution; no kernel modification.

- [x] **VB-PII-STAGED-WIRE — capture actual staged-index privacy findings at the write boundary.**
  Filed with NI31 before new gate validation: the pre-commit gate produces verified findings,
  but its current stdout/exit is not a native gate-result receipt. Bind the actual staged Git
  objects and original policy/provenance identities, exact bounded verdict and emitted UTC
  before any result is relied on outside its commit boundary. Preserve sensitive original
  inputs privately; no public secret material, historical reconstruction or new grading ladder.
  NI31's prospective CI hook fixtures use the existing selected-command receipt/class; they
  cannot stand in for arbitrary production-index findings. Source-table row filed now.


2026-10-05 NI25/NI29 acceptance: recovery `37299780302` binds ordinary guards (2/2), CPU leaves (13/13), API forward and reverse orders (376/376 each), and the declared synthetic-capacity broad attempt. Four true observations project through the existing sole verifier carrier; the timed-out broad phase has no JUnit, a null native proposition and no tuple. All five original prefixes are unchanged and reopenable at `artifacts/ni05/recovery-37299780302/`. This closes prospective command wiring and prefix durability, not SSU-F13 wider-unit acceptance.

VB-GAP-DIST write-side wiring is complete at the named fixture/native-custody boundary. The claimed 2026-10-05 private census source snapshot has 19 records, all missing session keys, zero pairs and zero emitted tuples; no distribution or TTL is established. HSF-3 remains open. NI32 adds synthetic source-schema refusal/coverage controls; tap/progress/checkpoints cannot independently supply the current exact enqueue/class contract. [Schema finding](../../progress/2026-10/2026-10-05-hsf3-source-map-ni32-proposal.md). VB-PII-STAGED-WIRE/NI34 is implemented and accepted: immutable private original-index/policy/events/terminal custody, strict reader and explicit CLI enrollment. Original hosted 74+10 fixtures pass. Main independently projects the original corrected two-path normal sub-gate finding as Judged/Located; no whole-privacy or promotion authority. Original inherited-setgid custody is refused unchanged.


- [x] **VB-MANAGED-TOOLING-WIRE (NI05-35)** — capture prospective named managed-interpreter import results at the write boundary, with actual interpreter/module/check-source hashes, argv, original stdout/exit and UTC. Narrow import-check scope only; existing verifier carrier/shared grade, no second ladder or full-host-health claim. Preserve refusals and missing inputs as false/diagnostic rather than imported success. NI12's original plain stdout stays ordinary evidence; source table row filed when the additional health producer gap was identified.

NI28 standalone dependency producer/reader accepted through original 12-case CI `37307888066`; source `79622da8` preserves ordinary verifier parity and owned timeout cleanup. Actual claimed store capture independently verifies four production links and seven zero-exit static-linkage child rows; native readback is `(True, [])`. VB-LINKAGE-GUARD remains open for prospective eligible measurement-producer digest bindings; the standalone dependency record has no ClaimTuple or new ladder.


NI35 named managed-import source accepted through original CI `37322527474` (11/11, no skips/errors/failures). Its own sole native reader projects TRUE/FALSE controls through the shared grade; missing interpreter/source, source drift and timeout yield zero tuples, and four mutation/collision controls refuse. The actual named health callers are wired; no actual host-health check or retrospective NI12 tuple is claimed. [Progress and original archive custody](../../progress/2026-10/2026-10-05-ni35-managed-tooling-check.md).

2026-10-05 reviewed source boundary: NI10 explicit optional `x_client_class` validates and forwards self-reported metadata with `caller_supplied:x_client_class` provenance; omitted fields remain absent. App source is published at `099dc1af69cf`. Original CI 37325396069 verifies 1/1 ordinary capacity refusal and 17/17 synthetic request-to-record controls. NI32 source59e adds 12/12 native/exact/proxy and tap/progress/checkpoint schema controls; original CI37326107920 is TRUE Judged/Located. The preceding 8/12 failed fixture expectation remains FALSE unchanged; missing-ledger custody correctly refuses to report OK (SC73). Neither fixture result supplies live gap data. HSF-3 remains open pending ≥50 properly keyed/classed sessions per reported basis in each independent window; no percentile, client brand, TTL or inferred enqueue. Delivery tally **34/36**.

- [x] **VB-DTAP-TIMEOUT-REPORT-WIRE (NI05-37)** — before the next DTAP timeout summary, bind typed terminal/recovered timeout outcomes, original trace bytes/digests, actual cap/scope/attempt counts, config/model/arm/seed/argv/source identities and original UTC to exclusive immutable native summary custody. Dry-run applicability is explicit and historical traces remain ordinary evidence. Reader projects only report integrity through the existing verifier carrier/shared grade; rates/counts are descriptive, no new ladder or elapsed-performance authority. Missing/false/censored inputs are preserved. TU-TM-1 owns reporting semantics; main owns enrollment/acceptance.

- [x] **VB-CONTEXTBENCH-SCORE-WIRE (NI05-38)** ✅ 2026-10-05 — before the next scored output, capture an exclusive pre-run request with immutable input/dataset/disposition/prediction/config/arm/source identities, original score/error/output bytes and UTC; preserve unresolved/malformed/refused/empty outcomes and explicit fixture applicability. Strict trusted reader projects report integrity using the existing verifier carrier/shared grade, with scores/counts descriptive; no new ladder, live-dataset count, token-measurement or historical warrant. DCP-10-SCORE-PREP owns pure scorer fixtures; full discovery benchmark stays open.


- [x] **VB-CI-OPTIONAL-SCORING-LOCK (NI05-41) ✅ 2026-10-05** — bind the newly resolved optional math-scoring lock, exact package metadata/audit and original resolver bytes as explicit source/readset inputs to the next prospective frozen scoring-fixture capture. Use the existing `ci-fixture-conformance` carrier and shared grade for the selected fixture command; the preparatory resolver artifact is ordinary dependency evidence and emits no standalone ClaimTuple. Preserve first failed/NULL fixtures, intentional missing-package hard failures and default dependency identities. No new ladder, evaluation-quality assertion or historical warrant. SSU-SCORING-EXTRA owns implementation; main owns acceptance.


NI37 bounded implementation accepted from original CI37341395541:112/112 app and82/82 reader/ingestion fixtures, zero skips/failures/errors, independently reopened TRUE Judged/Located. Main verifies the captured safe five-unit reporting proof; private inner capsules remain unexported and were verified during CI only. Actual primary boolean/nullable secondary semantics retain judge coercion, timeout classification and all failure denominators. App sourcef809b9d7 and root source bytes are promoted unchanged; [original public custody](../../artifacts/ni05/dtap-timeout-37341395541/README.md) and [accepted progress](../../progress/2026-10/2026-10-05-ni37-dtap-timeout-native-report.md). NI43 pure filesystem opt-in fixtures and NI44 surviving idle-prefilter safety are now indexed/claimed after current-source review. Delivery tally **37/44**; NI18/38/40/41/42/43/44 continue.

NI40/NI42 accepted 2026-10-05: main independently reopened original CI37339651393 (13/13 spill cases) and CI37339553198 (five graph modules,65/65 cases), all TRUE Judged/Located with zero skips/failures/errors. Declared source snapshots match pinned appdb38737d and exact workflow/producer originals. Independent postchecks prove all three binary targets absent/non-symlink; graph uses temporary databases and mocked embeddings. Spill scratch ownership/emptiness is attested before execution only, with no separate original post-run scratch check. Original fullscan failures/skips and first graph diagnostic NULL records remain unchanged. Public originals are preserved at artifacts/ni05/repl-spill-37339651393 and artifacts/ni05/graph-fixtures-37339553198. Accepted tally **39/44**; NI18/38/41/43/44 continue.

NI38 bounded offline score preparation accepted 2026-10-05: original CI37345306976 passes12/12 scorer and67/67 reader/ingestion cases, zero skips/failures/errors. Main independently reopens both CI receipts TRUE Judged/Located and the bound original synthetic scored-report archive in owned0700 custody: one TRUE report and two diagnostic NULL/zero-row originals, preserving original UUIDs/modes/bytes. Descriptive macro file/span metrics retain failure/empty denominators and caller-declared dispositions/costs; no official dataset denominator or quality claim. Reviewed app sourcec8851695 and root sourcecab789885 are promoted unchanged; recipe remains separate. Original public prefixes: artifacts/ni05/contextbench-score-37345306976. Full DCP-10 benchmark stays open; tally **40/44**, NI18/41/43/44 continue.

- [x] **VB-NI18-SCOPED-CI-WIRE (NI05-45–50, NI05-54–75)** — before each new source/fixture follow-on command, bind exact code/test pins, original runner-only configuration, source readset and selected cases through the existing native CI producer and shared verifier carrier. Preserve original fullscan FALSE receipts and intentional dependency/ownership/path/probe refusals; main independently reopens new originals before acceptance. No live embedding/model/service, host quiescence assertion, new grader or historical warrant. SSU scoped tasks own implementation. ✅ 2026-10-06

- [x] **VB-OFFHOST-CODE-INDEX-CUSTODY (NI05-52)** — before refreshing an exact offhost code snapshot, record immutable source/tool/npm-artifact identities and actual CLI no-embedding flags, original bounded analyze/status/impact streams and index metadata/clean-tree checks. Bind this ordinary code-intelligence dependency in subsequent source reviews; it emits no standalone ClaimTuple, new ladder, historical warrant or canonical-index deployment. SSU-OFFHOST-CODE-INDEX owns preparation and main owns readback. ✅ 2026-10-05 — main accepted originalCI37358369281; historical c885 scope, exact LOW targets and clean-state proofs, no host-index deployment.

- [x] **VB-CODE-INDEX-CLAIM-CONTROLS (NI05-76)** — prospectively capture ONE actual native pytest testcase covering103 descriptive actual-FLOCK controls: original101 plus two CPU-hardlink refusal cases. Require exact completeness, all statuses and real child exit; bind source/tool/readset/context before execution with unchanged native_conformance/shared grade. Source review proves one GLOBAL inode can satisfy several pathname checks in the prior guard, so require CPU single-link files and eight distinct identities (four GLOBAL plus four build). Earlier101 TRUE remains its bounded slice, not proof of the new property. Retain all FALSE/NULL/custom-audit originals, no fabricated JUnit, retrofitted tuples, second ladder or continuous-lifetime claim. SSU-CODE-INDEX-COMPUTE-CLAIM owns enforcement; main owns acceptance/integration. ✅ 2026-10-06 — original native evidence reviewed and published.

2026-10-05 NI41 accepted: originalCI37351080596 passes68/68 cases (18confidence-probe/9EV11stats/41verifier-mode), zero skips/failures/errors; allfive named positive/missing-package hard-fail controls pass. Main independently reopens allthree TRUE Judged/Located receipts and verifies exact source/dependency/context bytes, installed versions, frozen additive lock and absent binary postchecks. Rawresolver unrelated changes are preserved but rejected for promotion; all214original nonproject lock records/top-level fields remain unchanged. Only the optional extra and its three-package closure are published to appmain65599ff2b02fcf10a9631376e143e507717469b6. Original public custody: artifacts/ni05/eval-scoring-37351080596. SSU-SCORING-EXTRA and VB-CI-OPTIONAL-SCORING-LOCK close; tally **44/52**, NI18/45–50/52 continue. No inference, scientific quality, capacity, default-serving change or runtime reload claim.

- [x] **VB-AP-STRATEGY-PROJECTION-REPORT-WIRE (NI05-53)** — add opt-in prospective private original custody for the active Strategy Projection Report CLI. Bind source, journal and StrategyStore input identities plus dry-run/write-missing and explicit fallback-permitted policy before invocation; retain untouched JSON/Markdown, stdout/stderr, actual exit and UTC. Project only the original boolean projection-integrity assertion and its prebound proposition through the existing verifier/report-integrity carrier and shared grade. Counts remain descriptive, permission does not identify an actual embedding method, and old outputs get no reconstructed warrant. Synthetic owned-store positive/drift/partial/private-custody controls only; no live store/model, new ladder or embedding-quality claim. Main reviews exact producer/reader/adapter and original artifacts. ✅ 2026-10-05 — original 10/10 and synthetic integrity/refusal controls; source published.

2026-10-05 NI46–50 accepted: originalCI37352568892 passes101/101 whole-module cases (8vision/10quiescence/48requestschema/13pairwiseplanner/22parkedrole), zero skips/failures/errors. Main independently reopens allfive TRUE Judged/Located receipts, verifies31Git-boundsource snapshots+4context/install originals per capture and five absent-path/unchanged-lock postchecks. Exact four fixture files and one schema-description file are published to appmain64843e13642930895bb2e52694cd444de5892903; runtime policies and original FALSE sweep outcomes remain unchanged. NI45 still requires fresh source analysis and prospective evidence. NI53 newly filed before execution for active strategy-report original boolean integrity custody, with descriptive counts and no new ladder/method/quality claim. Tally **49/53**; NI18/45/52/53 continue. No inference, liveKFD/GPU/hold/store access or API reload.

- [x] **VB-MEMINFO-PRIVACY-CONTROLS (NI05-77)** — Prospectively bind exact privacy-hook source, staged fixture bytes and original command/JUnit/refusal outcomes through the existing CI/PII verifier carrier before capture. A known Linux counter false positive needs a narrowly reviewed control with real secret/account refusals retained; no new grading ladder or memory-capacity claim. Original private meminfo carriers remain unchanged and public-subset limitations stay explicit. ✅ 2026-10-05 — CI37384312011,19 staged controls; existing carrier/ladder.

2026-10-05 NI05-45 completed: original CI37378870278 attempt1 passes11/11 strategy CLI cases, zero skips/failures/errors, native TRUE Judged/Located and all11 postchecks. Main verifies148 private custody files,88 ZIP-member comparisons,19 Git-backed+6 context/install inputs and integration source parity. Explicit write/fallback permission is scoped and restored across constructor/sync/close errors; default semantic/owned-store guards remain and report permission does not identify the actual embedding method. Exact two source/test files are published to APP mainf884406e76d12a98254372a819e1fa6248c9223c. Public originals: `artifacts/ni05/strategy-cli-fixtures-37378870278`. The separate NI53 ROOT job remains original FALSE8/10 and open; no full-run/full-suite, live-store, model-quality or inference claim. Published scoped completion tally59/77,18 open.

2026-10-05 NI05-64 completed: unchanged design-archive whole-module fixtures pass16/16, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches570 Git-backed+5 context/install inputs and20 true postchecks, and proves current APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/design-archive-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally60/77,17 open.

2026-10-05 NI05-65 completed: unchanged q-scorer whole-module fixtures pass79/79, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches570 Git-backed+5 context/install inputs and20 true postchecks, and proves current APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/q-scorer-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally61/77,16 open.

2026-10-05 NI05-66 completed: unchanged inference-lock whole-module fixtures pass2/2, zero skips/failures/errors, in original CI37381716978 attempt1. Main verifies1,747 private custody files and1,731 ZIP-member comparisons, strictly reopens native TRUE Judged/Located, matches519 Git-backed+5 context/install inputs and20 true postchecks, and proves reviewed APP mainf884 source parity. Finite verbose prospective attribution is complete; the historical missing-JUnit NULL remains unchanged and cannot establish the original interrupted node/root cause. Public untouched metadata/log subset and derivative review: `artifacts/ni05/inference-lock-37381716978`; full source/context snapshots remain private, so the public prefix is explicitly not independently reopenable. No source change, inference, kernel/capacity, host-lock, quality or whole-suite claim. Published scoped completion tally62/77,15 open.

2026-10-05 NI05-59 completed: reviewed owned0700 scratch fixtures pass140 REPL+12 code-execution cases in original CI37383742953 attempt1, zero skips/failures/errors. Main verifies191 private original files and180 ZIP-member comparisons, strictly reopens both TRUE Judged/Located receipts, matches62 Git-backed+10 context/install inputs each and22 true postchecks each. Real spill-file assertions, missing-scratch refusal before Popen and bounded child-cleanup controls remain. Only two test files are published to APP mainad477541dbc2e6da4cfe4176d5f85045f64c6069; runtime behavior is unchanged. The runner custody gate admits only owned direct pytest *current links targeting captured same-parent private0700 directories; all other links/native-prefix links refuse. Prior FALSE/setup originals remain unchanged. Public original metadata/log subset: artifacts/ni05/runner-scratch-37383742953; excluded private source/context/meminfo snapshots are explicitly hashed, and the public prefix cannot independently reopen. Published completion tally63/77,14 open; no inference, live store/kernel, capacity, quality or whole-suite claim.

2026-10-05 NI05-77 completed: a narrowly typed known Linux VmallocTotal counter exemption resolves the privacy-gate false positive while retaining account/secret refusals, serialized-line boundaries and unchanged original bytes. Original CI37384312011 attempt1 passes19/19 real staged-hook controls, zero skips/failures/errors; main verifies378 private original files and372 ZIP-member comparisons, strictly reopens TRUE Judged/Located, matches68 Git-backed+5 installer inputs and14 true postchecks. Existing51 baseline fixtures separately observe false accepts0/21 must-block and false rejects0/30 must-not-block; these synthetic counts are descriptive, not field-quality estimates or a new claim tuple. Exact reviewed hook, fixture and test are integrated with this ROOT publication; prior setup/generic-test failures and raw meminfo originals stay unchanged. Public original metadata/log subset: artifacts/ni05/meminfo-privacy-37384312011; intentional synthetic account/secret payloads and source snapshots remain private with explicit hashes, so the public prefix cannot independently reopen. Published completion tally64/77,13 open; no filename wildcard, hook bypass, new ladder, memory-capacity or whole-suite claim.

2026-10-05 NI05-67 completed as a bounded attribution audit: pinned pytest9.0.3 emits successful subTest reports under their parent node IDs, incrementing suite statistics while retaining six parent testcase nodes. Main source review traces this in exact upstream commit a7d58d7a21b78581e636bbbdea13c66ad1657c1e. Fresh original CI37384625409 reproduces command exit0 with suite12/nodes6 and strict native NULL/no rows; the separate four-method control passes4/4 TRUE Judged/Located with zero skips/errors/failures. Main verifies six API-digest ZIPs and182 original-member byte comparisons,13 Git-backed+7 context/install inputs each and all four named postchecks per phase. Source/test and native count grammar remain unchanged; historical XML is never rewritten. Complete public native prefixes: artifacts/ni05/junit-count-attribution-37384625409. This closes attribution, not whole-six conformance. NI78 is newly filed from the actual precommit advisory before its guard repair; total78, published scoped tally65/78,13 open.

2026-10-05 NI05-63 completed: four source-pinned child probes pass4/4 with zero skips/failures/errors in original CI37385650047. Main verifies623 custody files and616 ZIP-member byte comparisons, strictly reopens TRUE Judged/Located, matches592 Git-backed+5 context/install inputs and21 true postchecks. Real foreign /usr/bin/python3.12 children retain hostile-argv, process survival and explicit entry-point reexec assertions. The fitting and oversized owned lineup fixtures use actual unchanged MemTotal/MemAvailable; the oversized control proves the unchanged capacity guard refuses. Complete canonical registry dependency closure is pinned, including loader/descriptors and compatibility shim. Six test/fixture files only are integrated to APP mainb27e5543199ba4f7a8c3fec87c263f35fb5bcbf1; all30 pinned source dependencies match current bytes. Initial checkout failure and subsequent missing-registry FALSE remain unchanged. Public untouched metadata/log subset: artifacts/ni05/argv-capacity-child-37385650047; private source/context originals are explicitly hashed, so the public prefix cannot independently reopen. No production launch/capacity measurement, memory override, kernel, inference or whole-suite claim. Published scoped tally67/78,11 open.

2026-10-05 NI05-73 completed: original CI37389045961 passes13/13, zero failures/errors/skips, strict native TRUE Judged/Located. Main independently verifies six API-digest ZIPs and468 byte-identical original members across both phases, and this phase binds85 Git-backed+7 external context/install inputs with all original postchecks true. Tested APP sourcefe29834d3bc0e203845effc699abddf0f2e3e2f0 remains the receipt identity; only the reviewed test file is integrated to APP maind31ac2e1f6595e126627ab177cb9449ee2e181a2, with selected production source bytes unchanged. Thirteen selected synthetic oracle/scorer and missing-manifest controls retain real bounded local Python scoring children in owned0700 scratch; exact argv/kwargs and child termination are asserted, and teardown leaves scratch empty. The missing-manifest case uses a finite in-memory row rather than the cached-JSONL helper. Dataset acquisition, full cached JSONL and model quality remain outside this scope. Public untouched metadata/log subset: artifacts/ni05/synthetic-oracle-37389045961; all excluded private input/context files are explicitly hashed, so this public prefix cannot independently reopen. Existing native CI carrier/shared grader only; no new grading rule, production kernel, inference or whole-suite claim. Published scoped tally68/78,10 open.

2026-10-05 NI05-74 completed: original CI37389045961 passes6/6, zero failures/errors/skips, strict native TRUE Judged/Located. Main independently verifies six API-digest ZIPs and468 byte-identical original members across both phases, and this phase binds85 Git-backed+7 external context/install inputs with all original postchecks true. Tested APP sourcefe29834d3bc0e203845effc699abddf0f2e3e2f0 remains the receipt identity; only the reviewed test file is integrated to APP main9d553e863ff8ef7954803cb83d415eeda7940aab, with selected production source bytes unchanged. Six tiny seeded T1/T2 question-vector selection and refusal controls exercise local algorithm behavior. The full-corpus property remains unchanged and unselected, with its existing human-authorization requirement preserved; no corpus access, model quality or live quality-baseline warrant. Public untouched metadata/log subset: artifacts/ni05/synthetic-vectors-37389045961; all excluded private input/context files are explicitly hashed, so this public prefix cannot independently reopen. Existing native CI carrier/shared grader only; no new grading rule, production kernel, inference or whole-suite claim. Published scoped tally69/78,9 open.

2026-10-05 NI05-53 completed: prospective private original Strategy Projection Report custody and strict reader/CLI enrollment are published to ROOT main 7c782a266b2551127aff1dd93f29a9e597321117. Original CI37390356985 passes 10/10 selected cases with zero failures, errors or skips; main independently reopens TRUE Judged/Located, compares all 50 original members in three API-digest ZIPs, verifies 30 Git-backed plus six external context/install inputs, and checks all ten true postchecks. The earlier six failures came from a stale exact producer digest; the reviewed correction updates that digest without relaxing equality. Every prior FALSE/NULL/setup original remains unchanged. The capture retains original CLI status, stdout/stderr, JSON/Markdown and prebound source/input/policy identities; the adapter projects only report.ok integrity through the existing verifier carrier/shared grade. Counts are descriptive, and fallback permission does not identify an actual embedding method. Synthetic owned-store controls cover positive/false reports, original exception/NULL disposition, input drift, resealed boolean mismatch, duplicate/member identity, symlinks/private-directory refusal and source enrollment. No live store, model, inference, embedding quality, transitive completeness or historical warrant. Five integrated source files match tested candidate 69c368204e8e582a10ed163574c8c08583eef7cd byte for byte; the new test module retains its entire original AST plus a refusing direct-entry guard, verified separately by the existing AST-only collectability checker (zero blocking/advisory). This ordinary file-integrity supplement is not another CI execution. Public original metadata/log subset: artifacts/ni05/strategy-report-custody-37390356985; private source/context exclusions are explicitly hashed, so the public prefix cannot independently reopen. Published completion tally 70/78; eight tasks remain open.

2026-10-06 NI05-68 completed: original CI37391662467 passes13/13 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Both missing-priors fallback assertions retain their original renderer/compiler bodies. Owned empty backend directories allow metadata compilation; only the exact read-only Git provenance child contract is admitted and its real successful exit is required. The earlier two failures remain preserved; their exact internally caught exception was not observed. Only the reviewed test fixture is published to APP main94d34949e16ce3a0b7827dcbcfa6d7fca0b6c171; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-system-card-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-69 completed: original CI37391662467 passes12/12 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Original external-drafter argv, compile-refusal and runtime-field assertions are unchanged. Owned empty backend directory metadata replaces production-store discovery; Popen refuses every child, so this is not a drafter launch. Only the reviewed test fixture is published to APP main7f36af77dcb90651067398474372536b9db271e2; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-external-drafter-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-70 completed: original CI37391662467 passes44/44 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. All original compiler/policy assertion bodies remain unchanged. Fixtures declare absent binary paths and admit only the exact read-only Git provenance child contract. Nine named compiler consumers must capture a successful provenance read; direct helper consumers may make no Git call. Only the reviewed test fixture is published to APP main75688b0523093b67af99bc87fb34b629ff2a3d20; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-priors-compiler-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-71 completed: original CI37391662467 passes7/7 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Original full/quarter/both NUMA reader-agreement assertions remain unchanged. Owned empty backend path metadata is bound and every child launch is refused. This proves metadata agreement, not host placement or residency. Only the reviewed test fixture is published to APP mainee4b60d253e382b60ceb8f930cae99f2a8617275; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-numa-readers-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-72 completed: original CI37391662467 passes7/7 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. Seven original speech environment-composition cases use owned empty STT/TTS paths and refuse all child launches. Real library-path/vendor policy is unchanged. The two actual frozen-service loader cases remain unchanged and unselected. Only the reviewed test fixture is published to APP maincb0a6eb57eca58830b076d4e2e1eb8057ac97031; its original function bodies remain unchanged. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-speech-composition-37391662467; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-76 checkpoint (task remains open): main independently verifies original failed CI37391222859 API ZIP712625349bytes/600 members and strict native FALSE1/1. The actual wrapper timed out after600 seconds with85 recorded expected control statuses and no complete marker; its deeper time cost is not exclusively attributed. Prospective streaming result custody retains full snapshot windows. Separate source review finds a real distinct-grant attribution gap: GLOBAL q0–q3 names hardlinked to one held inode can satisfy repeated checks, with five distinct CPU FLOCKs, or four if aliased to build.q0. This proves incorrect grant attribution, not unsafe concurrent overlap. New proposal015a9253bf7398bb71593b85401dbcadc4558c50c6b346fa4a488e6aab74d91d adds single-link and eight-distinct-identity checks, two real hardlink refusal controls and future transport compression6 preserving inner original bytes. Native denominator stays one testcase; descriptive denominator becomes103. No new source promotion or test run is counted here; no host code-index recovery or execution. Prospective native source wiring is recorded before that capture.

2026-10-06 NI05-62 completed: original CI37392512279 passes18/18 selected cases with zero failures, errors or skips; main strictly reopens TRUE native receipts through the existing adapter/shared grade as Judged/Located. The original per-token module passes10 cases and quant-width module passes8. Fixed arithmetic inputs/assertions, production helper source and the eager capacity guard are unchanged. The proposed HIGH-impact pure-module extraction remains unauthorized and is unnecessary for this bounded validation; no architectural extraction was performed. No APP source edit was needed; the existing original test modules ran unchanged. Recipea291322bfc9cdb678aa2081ca786a16c057f41f3 is published on its owned validation branch. Receipt APP identity remains45607fda456b6cc26796136a661e2e7f41cbbcdc. Main independently verifies the API ZIP digests and original member bytes; each receipt binds4176 inputs including2069 canonical and2069 fixture Python copies matching that Git source. The committed owned clone changes only two YAML declarations; actual MemAvailable and the real capacity guard remain in force, with all four independent postchecks true. Small declaration values are synthetic and warrant no production capacity. Public metadata/log originals are at artifacts/ni05/owned-kv-arithmetic-37392512279; excluded private source/context inputs are explicitly hashed, so the public prefix cannot independently reopen. Prior failed originals remain unchanged. Peer CPU-lock changes already on APP main are preserved and receive no new validation warrant. No inference, kernel execution, loader proof, production capacity or whole-suite claim.

2026-10-06 NI05-76 completed: original CI37396700409 at recipe591bd02d148bba94ee1ecc271183337493665c85 passes ONE native pytest testcase with103 actual descriptive controls, including CPU GLOBAL shared-inode and GLOBAL/build-alias refusals. Main independently verifies the complete API ZIP seal, every original member,103 exclusive sidecars equal to aggregate records, original statuses and denial snapshots, the exact50-input readset (15 ROOT Git,16 APP Git,7 approved fixture,12 context), pre-execution bindings and postchecks. Strict native TRUE1/1 projects through the existing shared grader as Judged/Located; no second ladder or retrofit. ROOT4 and APP3 guard-related implementation files are published; APP main405a5e7c162480c6cbc5919ecfa626850c08c7e0. All seven native CLI closure files remain byte-identical to tested APPb27e5543199ba4f7a8c3fec87c263f35fb5bcbf1; peer FIFO/runtime changes are preserved, without a new whole-current-main validation claim. CPU admission requires eight distinct single-link files, four GLOBAL plus four build, with actual write flocks attributed to one live same-UID ancestor. Refusal64 occurs before downstream index/global-tool mutation; nontruncating writer-lock contention returns75 and its FD is carried across child/exec. CI=true grants no exemption. Validation bypasses API preflight only on the disposable runner while real CPU claims remain mandatory. This is point-in-time admission, not continuous CPU-owner supervision, host-index execution/recovery, runtime deployment, or inference-noninterference evidence. The canonical host index remains untrusted after the recorded incident. Earlier ordinary audit negatives, native600s/85-record failure, prior101-control TRUE slice and failed103/16-record FIFO-message run remain private and unchanged; the original race assertion was preserved. New single-link diagnostics are separate from the original regular-file message. Public metadata/log originals are at artifacts/ni05/code-index-admission-37396700409; excluded private inputs/control snapshots are explicitly hashed, so the public prefix cannot independently reopen. GitNexus impact for new helpers remains UNASSESSED with manual caller review; no host graph query or rebuild was run.

- [x] **VB-EXECUTOR-REGISTRY-FALLBACK-CI (NI05-75)** — capture six focused no-launch executor fallback cases at APP `fa1eb43a2c4431d695e5c4339373ecbf3b96aed6`, producer `2dff56e6c9263fe982b12b91eab0552e50610635`, recipe `e1c234b527900c8096032122eaa3c844fd837356`. Bind exact whole tracked Python/config/lock/dependency/tool/workflow/runner context before execution; retain native originals and independent source/mount/absent-path postchecks. Main strictly reopens receipt through the unchanged verifier/shared grade before accepting. Bind three nonexistent import-only ambient overrides; selected cases clear/set the CPU override themselves. Synthetic fixture warrant only; no launch, production capacity or historical backfill. Main owns prospective wiring, approval and final checkbox. ✅ 2026-10-06

2026-10-06 NI75 approval checkpoint: operator explicitly approved the reviewed HIGH-impact executor fallback repair. Exact dependency scope remains10 affected nodes/one direct caller/three modules; the prior negative query is retained. Reviewed APP candidatefa1eb43a2c4431d695e5c4339373ecbf3b96aed6 changes only the registry-failure branch and adds six no-launch unit cases. Single prospective recipe45660107ffa880c2b97f08f5c775a5cf4aeb943c uses unchanged ROOT producer2dff56e6c9263fe982b12b91eab0552e50610635. Main verified exact diffs and source AST scope; publication/capture is authorized only after this prospective wiring is pushed. No validation outcome or completion is claimed; tally77/78 remains. Main owns original review, integration and per-task wrap-up.

2026-10-06 NI75 corrected-capture checkpoint: main independently verifies all three API ZIP digests and 5,564 original members from CI37406127191, plus exact2,757 readset inputs (2,129 APP Git,617 producer Git,1 recipe and10 context). Strict native result is NULL, exit4, no JUnit/summary and zero projected rows: eager PathsConfig resolution refused the absent CPU store before test collection. All seven independent postchecks pass. Original receipt FILEcb6726d07d366bf0e0f8d18a6a12834b02e33e948c6821a431f0b64d30b1f5e3/selfeafd884c0d25216fa668feab22692d32820ecb3c09571ab13ab87f24d0ad5fbb remain unchanged. Main reviews exact one-workflow correctione1c234b527900c8096032122eaa3c844fd837356, sole child45660107, binding three private nonexistent import-only paths and before/after absence checks. APPfa1eb43a and all six test assertions, capacity guards, source pins and time limits remain unchanged. Test fixtures explicitly clear/set the CPU override before exercising fallback policy. Prospective wiring now points to the corrected recipe before its single new capture. No fallback outcome, tuple or task completion is inferred from the earlier NULL; tally remains77/78.

2026-10-06 NI05-75 completed after MAIN review and publication: original CI37406900511 at recipee1c234b527900c8096032122eaa3c844fd837356 passes all six focused executor fallback cases with no skips/failures/errors. APPfa1eb43a2c4431d695e5c4339373ecbf3b96aed6 changes only get_binary_paths registry-load failure handling: one patchable load attempt, unchanged legacy names, stripped explicit override precedence, otherwise CPU kernel-store resolution with KernelPathError propagated before any Popen. Successful registry delegation/custom names remain unchanged. Original native TRUE6/6 is captured prospectively through unchanged producer2dff56e6 and existing shared grader; MAIN independently reopens all original ZIP/readset/context/fixture/postcheck evidence before acceptance. Three private nonexistent ambient overrides permit eager configuration imports; each fallback test explicitly clears/sets the CPU override and no kernel/model process is launched or store directory materialized. Prior original CI37406127191 remains NULL/exit4/noJUnit before collection, with zero projected rows; original HIGH-impact negative query CI37361379823 remains unchanged ordinary evidence, and the operator approved its10-node/one-direct/three-module repair scope. No production capacity, binary linkage, deployment, inference noninterference or whole-suite pass is claimed. Scoped published completion tally78/78; larger parent programs and standing rules remain open.

- [x] **VB-NI-WRAP-WIKI-DEPS (NI05-79)** — record that the 2026-10-06 full-wrap wiki coverage ledger is dependency evidence only: compiled pages remain graph edges, not a belief source class or ClaimTuple producer. The published NI05-79 store-defaults change is ordinary documentation/source verification; it adds no measurement, adapter, grader, or `.vidya` write. Preserve `wiki_dependents.py` as an edge recomputation consumer; do not import its historical hardcoded fold into this wrap. Current `cite-check --as-of 2026-10-06T04:08:48Z` returned exit 0 (3,382 citations / 189 documents; review 808, weak 8, unknown 37, ok 1,689, record 840 classifications remain visible). The final source coverage and citation policy are linked from the [adapter source table](../../scripts/vidya/adapters/README.md#known-and-candidate-sources) and [full-wrap report](../../progress/2026-10/2026-10-06-codex-ni-final-wrap.md#wiki-incremental-sweep). ✅ 2026-10-06

## MAIN-reviewed JEV refinement — 2026-10-06 (VB-SERVE-TIMING-1)

Include a synthetic fixture for the already-defined typed judge-to-serving-call join (`serving.caller.parent_request_id == judge.call_id`), retaining native task/caller identity. Test unmatched and repeated IDs, record-hash/schema mismatch, absent timings and absent launch identity. Keep typed `record_llm_calls` accounting separate from server queue/placement/timing records; never double-count one inference. Use the native server record for serving metrics.

Preserve the original absence rules: skip absent timings, never invent zeros, and leave absent server identity unscoped rather than inferring a launch or rejecting an otherwise valid unscoped observation. An ID match is necessary for a join, not proof of grading quality or complete provenance. This is offline reader/fixture preparation; change neither the Claude-owned judge producer nor its calibration, and keep window aggregation as the original separate decision. The shared grader alone determines warrant; add no source class or ladder.

## JEV-aware handoff audit dependency capture — 2026-10-06

- [x] **VB-NI06-CI-WIRE — capture the three selected non-inference fixture executions prospectively.** Use the existing native CI producer and adapter/shared grader. Bind exact reviewed source pins, selected tests/import readset, workflow/harness and package inventory before execution; preserve original request, JUnit, command/status and snapshots. MAIN reopens original custody before accepting each bounded result. Fake reader/model primitives and temporary graph/SQLite/tokenizer bytes only; no live inference, embedding, performance, migration, deployment or whole-suite authority. Source table enrollment precedes capture. ✅ 2026-10-06 — MAIN reopened the three accepted original receipts and exact source/context custody, then ingested them into `/workspace/.vidya/ledger.jsonl`: three units/rows, nine frames, no missing/declined/refused units. Existing Judged/Located observations only; failures/nulls preserved separately. [Ingestion report](../../artifacts/ni06/belief-ingest-original-report.json).

- [x] **VB-HANDOFF-JEV-AUDIT — preserve and check the prospective documentation dependency inventory.** Bind the pre-review source manifest, every original task key, delegated review and MAIN acceptance/rejection/applied text in the audit artifacts. Check complete file/key coverage and original source identities before final reporting; preserve the distinct audit snapshot and subsequent edits/peer deltas. This is documentation/source review, not a new measurement or ClaimTuple producer. Use existing document dependency handling; no grading ladder, historical tuple reconstruction, runtime or scientific authority. Source row filed before final audit consumption. ✅ 2026-10-06 — all 528 original file hashes and 3,558 task keys validated, with MAIN decisions/applied text preserved in artifacts/handoff-audit/2026-10-06.

### VB-INF70-ARMS — source-verified remaining scope (MAIN, 2026-10-06)

The capture module, strict reader, CLI ingestion and producer hook already exist (`inf70_serving_arm{,_capture}.py`, `scripts/inf70/harness1/sc75_capture.sh`, `arm_cold.sh`, `arm_hot.sh`; VB-WIRE-2 / SC75). Do not rebuild that adapter. The existing unchecked parent now means first real post-hook arm acceptance at the INF-70 owner's granted window: reopen its producer-written sidecar and launch/contention identities through the strict reader and shared `ClaimTuple` grading. Keep pre-hook arms refused, arm-level support identity and all existing quality/authority gates. Existing wiring and synthetic checks cannot substitute for the first real arm.


- [x] **VB-KB-CATALOG-IDENTITY — capture successful catalog-write identity prospectively as dependency evidence.** ✅ 2026-10-06 — APP sourceefd67c52 promoted maine2ad3dbf supplies five named final transaction hooks and strict read-only native record reopening. [Contract](../../docs/reference/kb-catalog-dependency-contract.md) excludes vectors, init/checkpoints/VACUUM and whole-operation/concurrent-writer guarantees; stored/native loaded identities remain distinct, missing legacy unknown. Original synthetic CI37441909661 TRUE108/108 accepted through existing CI carrier/shared grader after MAIN original custody review; no new ClaimTuple source or ladder. K2/OP-24 cap transitions remain separate.

- [x] **VB-KB-CATALOG-CONSUMERS — bind producer-written current catalog dependencies into KB-backed evidence consumers.** ✅ 2026-10-06 — MAIN accepted the [source audit](../../artifacts/ni08/source-audits-20261006/kb-consumer-findings.md) at APP `48a546e90fbc202a0c2ae103203621ba29175915`: both K7 report and Lab context manifest already attach strict-reader native records; direct reader use satisfies the contract without an exporter call. Missing legacy remains unknown; malformed/mismatched native rows refuse. Cumulative query-length telemetry is a separately bound historical measurement stream and is not retroactively joined to today's catalog. No code, new test run, retrieval-quality, actual reindex, new ladder or concurrent-writer claim.

- [ ] **VB-NI07-DOC-DEPS — preserve source-backed contract dependencies at each NI07/NI08 document boundary.** Bind exact source Git pins/readset and reviewed drafts/applied documents for HG-9, TU-GR-1 and subsequent accepted contract/governance maps, including the ungraded R25/AUD12 source identities and exact proposed/applied document dependencies. Use existing document dependency handling only; no new ClaimTuple producer, inferred runtime state, historical backfill or isolation/quality claim. MAIN owns canonical records.
- [ ] **VB-NI07-CI-WIRE — prospectively capture accepted NI07 non-inference fixtures.** Use the existing native CI producer and adapter/shared grader with exact source/test/readset/recipe/context bindings before execution. Preserve original request/JUnit/output/status and every failed/null outcome; MAIN reopens original custody at each acceptance boundary. Fake/temp fixtures only; no inference, re-embedding, serving/kernel, scientific or whole-suite authority.

  - [x] **VB-NI07-DOC-TUGR — preserve the accepted isolation specification source dependencies.** ✅ 2026-10-06 — [25 pinned paths/blobs/hashes](../../artifacts/ni07/tu-grader-isolation-source-inventory.json) independently reopened by MAIN; [review/applied-content identities](../../artifacts/ni07/tu-grader-isolation-main-review.json). Document dependency only, no ClaimTuple, OS isolation, model or grading claim.

  - [x] **VB-NI07-DOC-HG9 — preserve accepted topology source dependencies.** ✅ 2026-10-06 — [14 pinned source files and two drafts](../../artifacts/ni07/hg9-source-readset.md) independently reopened; [MAIN review/applied identity](../../artifacts/ni07/hg9-main-review.json). Document dependency only, no model/route/cost/quality claim.

  - [x] **VB-NI07-CI-K2 — ingest accepted original cap fixtures.** ✅ 2026-10-06 — Original run37436700878 TRUE54/54, 3,330 exact pinned Git inputs plus two sealed runner contexts, all 3,340 ZIP/extracted members reopened. [MAIN review and canonical ingest](../../artifacts/ni07/run-37436700878/README.md): one projected observation, three new ledger frames through the existing native CI adapter/shared grader (Judged/Located, no protocol). Previous failed/null originals preserved; no retrieval or deployment claim.

  - [x] **VB-NI07-CI-S9 — ingest accepted original locking fixtures.** ✅ 2026-10-06 — Original run37439049934 TRUE68/68; 3,331 exact Git bindings plus two contexts, all 3,341 original ZIP/extracted members reopened and API seal matched. [MAIN review and canonical ingest](../../artifacts/ni07/run-37439049934/README.md): one Judged/Located observation through existing native CI carrier/shared grader, three new frames. No new protocol, class, ladder, live deployment or quality claim.

- [x] **VB-DTAP-NATIVE-TOOLS-DEPS — preserve public tool-schema/request-contract dependency identity prospectively.** ✅ 2026-10-06 — [Source/case readset](../../artifacts/ni07/tool-rendering/dtap-ni07-11-ci-readset.json) and [MAIN original review](../../artifacts/ni07/run-37444164809/README.md) bind public case mapping, catalog/per-case schema hashes, explicit endpoint mode, tool choice and validator source. Native fake request traces emit identity before consumption. Existing document/artifact dependency handling only; no service-state, human-gold or judge result reconstructed on read.

  - [x] **VB-NI07-DOC-TUHR — preserve static tool-rendering dependencies.** ✅ 2026-10-06 — [35 static source entries and 19 catalog/case entries](../../artifacts/ni07/tool-rendering/main-review.json), all pinned blobs/SHA independently reopened, upstream tree verified and every public catalog source covered. Eighteen case catalogs are source-backed; runtime route/template identity remains unknown. Document dependencies only, no ClaimTuple or live tool-use validity.

  - [x] **VB-NI07-CI-CATALOG — ingest original catalog/deletion synthetic fixtures.** ✅ 2026-10-06 — [Original CI37441909661](../../artifacts/ni07/run-37441909661/README.md) TRUE108/108,3333independent Git bindings plus2contexts,3343original members reopened and API ZIP digest matched. Existing shared grade Judged/Located observation;3canonical frames. Forty new cases include the separately tracked NI07-12 rollback correction,68previous regression cases unchanged. No new protocol or live quality claim.

- [x] **VB-NI07-UTM-READOUT — preserve native synthetic memory conformance readout at execution.** ✅ 2026-10-06 — [Original native readout/custody](../../artifacts/ni07/run-37444684189/README.md) reopened by MAIN: case/rubric/per-case hashes,8store categories,5parser batches/6attempts and separate denominators. Existing generated-output carrier/shared grading only; semantic gold null, six axes unassessed and calibration unmeasured.

- [x] **VB-DTAP-FAILURE-LEDGER — preserve native per-run outcomes and usage prospectively.** ✅ 2026-10-06 — [Accepted additive write-side report](../../docs/reference/dtap-native-failure-ledger-contract.md) binds native closed trace bytes/IDs and projects restricted typed facts before consumption; no reconstructed grade or estimated total-attempt cost. [OriginalCI37451263389](../../artifacts/ni07/run-37451263389/README.md) accepted via existing native carrier/shared grader; live DTAP remains separate.

  - [x] **VB-NI07-CI-SERVING — ingest accepted original serving-reader fixtures.** ✅ 2026-10-06 — [Original CI37443323928](../../artifacts/ni07/run-37443323928/README.md) TRUE87/87;3332pinned Git bindings plus2contexts,3342API ZIP members reopened. Existing shared Judged/Located observation,3new canonical frames; original FALSE unchanged. No live timing or window/quality warrant.

  - [x] **VB-NI07-CI-UTM — ingest original synthetic memory conformance fixtures.** ✅ 2026-10-06 — Original CI37444684189 TRUE2/2;3336Git bindings plus2contexts,3347original API members reopened. Existing Judged/Located observation emits3canonical frames. Initial collection NULL unchanged; no memory semantic accuracy or protocol warrant.

  - [x] **VB-NI07-CI-DTAP — ingest accepted original native tool-contract fixtures.** ✅ 2026-10-06 — Original CI37444164809 TRUE127/127;2745Git bindings plus2contexts,2755original API ZIP members reopened by MAIN. One existing shared Judged/Located observation emits3canonical frames; original FALSE124/127 unchanged. No live service/model/judge-quality warrant.

  - [x] **VB-NI07-CI-RC — ingest original supplied-score expectation fixtures.** ✅ 2026-10-06 — [Original CI37446388954](../../artifacts/ni07/run-37446388954/README.md) TRUE26/26;3338Git inputs plus2contexts,3348API ZIP members independently reopened. One existing shared Judged/Located observation emits3canonical frames; no native probability or calibration warrant.

  - [x] **VB-KB-CATALOG-K7-REPORT — preserve the existing native catalog dependency in K7 summary artifacts.** ✅ 2026-10-06 — [Accepted strict consumer](../../docs/reference/k7-report-catalog-dependency-contract.md) publishes original validated report-time record, null unknown and refusal without reconstruction. OriginalCI37450891733 TRUE11/11 accepted through existing native CI carrier; broader consumers stay open, no new class/ladder or all-query warrant.

  - [x] **VB-NI07-CI-CS — ingest original provisional conversation-shadow fixtures.** ✅ 2026-10-06 — [Original CI37447169966](../../artifacts/ni07/run-37447169966/README.md) TRUE19/19;3340Git inputs plus2contexts,3350API members reopened. Existing shared Judged/Located observation emits3canonical frames; original FALSE unchanged, no corpus schema/calibration/routing warrant.


  - [x] **VB-NI07-CI-FORCE — ingest accepted original forced-build duplicate fixtures.** ✅ 2026-10-06 — [CI37447817516](../../artifacts/ni07/run-37447817516/README.md) TRUE113/113;3335Git bindings plus2contexts,3345API members reopened. One existing shared Judged/Located observation emits3canonical frames; three original FALSEs unchanged. No native vector-integrity/quality/concurrent-writer warrant.


- [x] **VB-KB-VECTOR-PUBLISH — prospectively capture staged vector publication source contracts.** ✅ 2026-10-06 — [OriginalCI37451221250](../../artifacts/ni07/run-37451221250/README.md) TRUE122/122 accepted through existing native CI carrier/shared grader after MAIN3349Git+2contexts/all3359APImember review. Fake/source partial/refused/successful-write identity only, no new ladder/source class, vector attestation or cross-resource transaction claim.


  - [x] **VB-NI07-CI-K7-REPORT — ingest original report-consumer fixtures.** ✅ 2026-10-06 — [OriginalCI37450891733](../../artifacts/ni07/run-37450891733/README.md) TRUE11/11; MAIN3351Git+2contexts/all3361API members verified. Existing Judged/Located observation emits3frames; synthetic report contracts only.


  - [x] **VB-NI07-CI-FAILURE-LEDGER — ingest original additive reporting controls.** ✅ 2026-10-06 — [OriginalCI37451263389](../../artifacts/ni07/run-37451263389/README.md) TRUE141/141; MAIN2758Git+2contexts/all2768API members verified. Existing Judged/Located observation emits3frames; descriptive native integrity only.


  - [x] **VB-NI07-CI-VECTOR-STAGE — ingest original staged-write fixtures.** ✅ 2026-10-06 — [OriginalCI37451221250](../../artifacts/ni07/run-37451221250/README.md) TRUE122/122; existing Judged/Located observation and3canonical frames, complete MAIN source/API custody review.


- [x] **VB-BSV-INPUT-STRICT — bind strict standalone native-outcome input handling prospectively.** ✅ 2026-10-06 — [OriginalCI37454712581](../../artifacts/ni07/run-37454712581/README.md) TRUE38/38 after MAIN3357Git+2contexts/all3367API member review; existing native carrier/shared grader, no new taxonomy/ladder/model quality warrant. Original FALSE31/38 remains separate and unchanged.
  - [x] **VB-KB-LAB-CONTEXT — capture existing native catalog dependency at lab context collection.** ✅ 2026-10-06 — [OriginalCI37454908617](../../artifacts/ni07/run-37454908617/README.md) TRUE19/19 after MAIN3357Git+2contexts/all3367API review. Existing native record/null unknown/refusal before query/backend, no reconstruction/new class/all-query snapshot. Original FALSE17/19 retained independently.
- [x] **VB-TOOL-REPAIR-LOG — prospectively capture repair-log minimization source contracts.** ✅ 2026-10-06 — [OriginalCI37456098288](../../artifacts/ni07/run-37456098288/README.md) TRUE149/149 after MAIN3593Git+2contexts/all3603API review; existing carrier/shared grading and no new class/ladder. Initial NULL preflight had no native receipt/JUnit and remains separate; synthetic sentinel/outcome/counter facts only.

- [x] **VB-NI07-CI-BSV-INPUT — ingest strict standalone input fixtures.** ✅ 2026-10-06 — [OriginalCI37454712581](../../artifacts/ni07/run-37454712581/README.md) TRUE38/38, one existing Judged/Located observation and three canonical frames; original FALSE31/38 independently reopened and retained, not regraded.

  - [x] **VB-NI07-CI-LAB-CONTEXT — ingest lab dependency-consumer fixtures.** ✅ 2026-10-06 — [OriginalCI37454908617](../../artifacts/ni07/run-37454908617/README.md) TRUE19/19; one existing Judged/Located observation and3canonical frames after MAIN exact source/API review. Initial FALSE17/19 original retained, not resealed or regraded.

- [x] **VB-K2-QUERY-EXPANSION-REFUSAL — bind optional config capability refusal prospectively.** ✅ 2026-10-06 — [OriginalCI37456357367](../../artifacts/ni07/run-37456357367/README.md) TRUE24/24 after MAIN3359Git+2contexts/all3369API review; existing native carrier/shared grade, no new class/ladder/expansion/model/live claim.

- [x] **VB-DCP-RENDER-IDENTITY — bind render-time DCP source-identity refusal prospectively.** ✅ 2026-10-06 — [OriginalCI37457222213](../../artifacts/ni07/run-37457222213/README.md) TRUE17/17, MAIN3357Git+2contexts/all3367original API verification through existing carrier/shared grader. No new source class/ladder, discovery/quality/live claim; worker review-order deviation explicitly retained and MAIN source-first review independently completed.

- [x] **VB-NI07-CI-TOOL-REPAIR-LOG — ingest original repair-log synthetic controls.** ✅ 2026-10-06 — [OriginalCI37456098288](../../artifacts/ni07/run-37456098288/README.md) TRUE149/149, one existing Judged/Located observation and3canonical frames, full MAIN source/API review; no fabricated native claim for NULL original.

- [x] **VB-NI07-CI-QUERY-EXPANSION — ingest optional capability-refusal fixtures.** ✅ 2026-10-06 — [OriginalCI37456357367](../../artifacts/ni07/run-37456357367/README.md) TRUE24/24, one existing Judged/Located observation and3canonical frames, complete MAIN source/context/API review. Separate generic-suite24producer failures remain separate and now have NI07-22 owner.

- [x] **VB-CI-RESEARCH-PRODUCERS — supply exact reviewed research source to hermetic producer-backed tests.** ✅ 2026-10-06 — [Contract](../../docs/reference/hermetic-research-producer-ci-contract.md), ROOTmainf01aea743; finalnative37461044899 TRUE29/29 after MAIN1452Git+2contexts/all1462original API review. Separate generic37461044908 passes1720/165standing skips with index/ratification checks green. Exact pinned three producer families/test-only seams and isolated checkout; production guards/selection/skips unchanged. Historical nativeTRUE/genericfailed originals and MAIN checkout-collision review miss retained; no model/benchmark/kernel/live execution.

- [x] **VB-DCP-HIT-SPAN-POLICY — prospectively bind deterministic DCP policy preparation.** ✅ 2026-10-06 — [OriginalCI37458830138](../../artifacts/ni07/run-37458830138/README.md) TRUE33/33 after MAIN3361Git+2contexts/all3371original API review, existing carrier/shared grader only. Bounded source/range/mode policy facts; parent DCP-11/live gate remains open, no new class/ladder or AST-complete quality claim.

- [x] **VB-NI07-CI-DCP-RENDER — ingest deterministic DCP render identity fixtures.** ✅ 2026-10-06 — [OriginalCI37457222213](../../artifacts/ni07/run-37457222213/README.md) TRUE17/17, one Judged/Located observation and3canonical frames after MAIN source-first full custody verification. Bound old/new body, three rendering modes and unbound/unreadable controls only; no gate or measured quality claim.

- [x] **VB-NI07-CI-DCP-HIT-SPAN — ingest deterministic budget-policy preparation fixtures.** ✅ 2026-10-06 — [OriginalCI37458830138](../../artifacts/ni07/run-37458830138/README.md) TRUE33/33, one Judged/Located observation and3canonical frames; MAIN source-first full original custody verified. Policy preparation only; DCP-11 live validation and feature activation remain separate.

- [x] **VB-REPL-PICKLE-PASS — prospectively bind signed checkpoint payload transport conformance.** ✅ 2026-10-06 — [Contract](../../docs/reference/signed-checkpoint-payload-transport.md), APPc61c4e8e/ROOT881afccf; original37465024500 TRUE116/116 after MAIN3361Git+2context/all3371original custody review. Both producers/SQLite/restore/tamper/unsupported controls, combined persister caps and deterministic eviction; existing signed boundary/fencing unchanged. Prior setup/collectionNULL preserved; no live session/model/kernel/host tests.
- [x] **VB-EVAL-CAPTURE-STATUS — bind question-writer status failure controls.** ✅ 2026-10-06 — [Contract](../../docs/reference/eval-question-sidecar-persistence-status.md), APP05a18b4e/ROOT490b7030; native37463260425 TRUE9/9 after MAIN3361Git+2context/all3371original custody review. Bounded per-batch status reaches aggregate/filter/role summaries, grades/dispositions unchanged. Prior diagnosticNULL and FALSE6/9 retained; fixture-only0..3 baseline correction, no live eval/model/host tests.
- [x] **VB-EVAL-RECONNECT-COST — bind original reconnect cost conformance.** ✅ 2026-10-06 — [Contract](../../docs/reference/eval-outer-reconnect-cost.md), native37466167911 TRUE57/57 after MAIN3363Git+2contexts/all3373original-member review; APP726084a8/ROOTa5929784. Outer attempts/backoff/reason reach original question rows; inner retry counts and grading unchanged. No live eval/model/host tests.
- [x] **VB-REPL-TIMEOUT-STATE — bind terminal timeout reuse/persistence refusal.** ✅ 2026-10-06 — [Contract](../../docs/reference/repl-terminal-timeout-state.md), original37469999403 TRUE123/123 after MAIN3369Git+4contexts/all3431original-member review; APP733623f4/ROOTf8ba8487. Sticky timeout rejects reuse/checkpoints, suppresses FINAL/artifact rescue; bounded late-worker and lease cleanup controls. No worker termination/host-effect isolation or live lease acceptance.

- [x] **VB-NI07-CI-RESEARCH-DEPS — ingest full-module producer dependency conformance.** ✅ 2026-10-06 — [Finaloriginal37461044899](../../artifacts/ni07/run-37461044899/README.md) TRUE29/29 after source-first complete MAIN custody review, one Judged/Located observation and3canonical frames. Synthetic producer-shaped measurements inside tests stay outside canonical ledger; original29TRUE/generic2fail retained separately.

- [x] **VB-NI07-EVAL-CAPTURE-STATUS — ingest sidecar status conformance.** ✅ 2026-10-06 — [Original37463260425](../../artifacts/ni07/run-37463260425/README.md) TRUE9/9 after complete source-first MAIN custody review, one Judged/Located observation and three canonical frames, no live/quality/physical-storage gate.

- [x] **VB-TD-OPTION-DESCRIPTIONS — bind candidate-description structural conformance.** ✅ 2026-10-06 — [Contract](../../docs/reference/typed-candidate-description-preparation.md), original37468262427 TRUE14/14 after MAIN3367Git+2contexts/all3377member review; APPa6883d04/ROOT4a46ac2f. Empty-default compatibility, strict descriptions, original-label/key and ordered layout/reader controls accepted. PriorFALSE13/14 preserved; parentTD14/TD16 live no-harm remains open.

- [x] **VB-NI07-CHECKPOINT-TRANSPORT — ingest signed payload transport conformance.** ✅ 2026-10-06 — [Original37465024500](../../artifacts/ni07/run-37465024500/README.md) TRUE116/116 after source-first MAIN/API custody review, one Judged/Located observation and three canonical frames; real restricted boundary with synthetic SQLite state, no live persistence/quality gate.

- [x] **VB-NI07-RECONNECT-COST — ingest outer reconnect conformance.** ✅ 2026-10-06 — [Original evidence](../../artifacts/ni07/run-37466167911/README.md) TRUE57/57, one Judged/Located observation and three shared-grade frames, no live/quality warrant.

- [x] **VB-NI07-CANDIDATE-DESCRIPTIONS — ingest structural conformance.** ✅ 2026-10-06 — [Original evidence](../../artifacts/ni07/run-37468262427/README.md) TRUE14/14, one Judged/Located observation and three canonical frames; no live/adoption/quality gate.

- [x] **VB-TD-CAL-INPUT-BINDINGS — capture input-binding structural conformance prospectively.** ✅ 2026-10-06 — [Original evidence](../../artifacts/ni07/run-37473538913/README.md) TRUE34/34; one Judged/Located observation and three shared-grade frames. Source-byte identities are dependency evidence only, not a standalone calibration ClaimTuple; VB-TDP-1/shared-screen retains original source/model/protocol/custody and live-quality requirements. No second ladder, historical backfill, or calibration-quality warrant.

- [x] **VB-STANDALONE-NUMA-GUARD — capture standalone NUMA guard source/fixture conformance through the existing native carrier and shared grade.** ✅ 2026-10-06 — Original run 37476312545, 14 node IDs / 20 cases; MAIN source/custody review accepted; APP main 48a546e90fbc202a0c2ae103203621ba29175915. The evidence covers deterministic CLI resolution and selected portable-path controls only. It does not establish live topology, capacity behavior, deployment, kernel/server execution, model behavior, or production acceptance; no new grading ladder.

- [x] **VB-NI07-TERMINAL-REPL — ingest timeout structural conformance.** ✅ 2026-10-06 — [Original evidence](../../artifacts/ni07/run-37469999403/README.md) TRUE123/123, one Judged/Located observation and three canonical frames; no live lease/cancellation/host-effect gate.

- [x] **VB-PII-ED25519-CONFORMANCE — bind staged-header structural controls.** ✅ 2026-10-06 — existing native CI carrier/shared grade captured the disposable staged-blob controls; run 37474797195 TRUE9/9; one Judged/Located observation and three canonical frames. No privacy/promotion warrant, extra per-fixture rows, new ladder, policy exemption, or historical backfill.

- [x] **VB-NI07-CALIBRATION-INPUTS — ingest calibration input-binding structural conformance.** ✅ 2026-10-06 — [Original evidence](../../artifacts/ni07/run-37473538913/README.md) TRUE34/34, one Judged/Located observation and three canonical frames; source hashes are dependency evidence only, no live/calibration-quality gate.

- [x] **VB-NI07-PII-HEADERS — ingest staged-header native structural conformance.** ✅ 2026-10-06 — [Original evidence](../../artifacts/ni07/run-37474797195/README.md) TRUE9/9; one shared native Judged/Located observation, three canonical frames. Synthetic control outcomes remain inside the single fixture execution; no extra ledger rows or privacy authority.

- [x] **VB-NI07-30-STANDALONE-NUMA — ingest standalone guard synthetic conformance.** ✅ 2026-10-06 — [Original evidence](../../artifacts/ni07/run-37476312545/README.md), TRUE20/20 across 14 node IDs, using the existing native carrier/shared grade. This records deterministic source/fixture behavior only; synthetic import-time MemTotal and empty backend directories are test scaffolding, not hardware/production observations. No live topology, kernel/server/model execution, production acceptance, or new ladder.

- [x] **VB-SCRATCH-ROOT-KEEP — bind declared-root retention structural conformance.** ✅ 2026-10-06 — Original37482120866 TRUE27/27 uses the existing native CI carrier/shared grade; one Judged/Located observation, three frames. Synthetic root/marker/ancestor/overlap/late-marker and existing cleanup controls only; no host evidence-survival, process liveness, whole-host safety, new ladder or backfill.

- [x] **VB-NI07-SCRATCH-ROOT-KEEP — ingest original retention fixture observation.** ✅ 2026-10-06 — [Native evidence](../../artifacts/ni07/run-37482120866/README.md), TRUE27/27; one outer observation and three existing-carrier frames, synthetic fixture scope retained.

- [x] **VB-HOST-SUPERVISION-ACTIVATION — prospectively write and integrity-classify host activation dependency records.** ✅ 2026-10-06 — MAIN accepted nativewriter/callback source77704fe,81/81 hosted conformance and existing shared outer grade Judged/Located; [originals/failed-predecessor/limits](../../artifacts/ni08/host-native-receipt-source-20261006/README.md). Operational rows remain ungraded; no host execution or old bootstrap backfill. NI08-02: future explicit installer capture and an eligible subsequent durable heartbeat write self-hashed native rows. Reuse the dependency-evidence pattern in `autokernel_fault_rehearsal.py`; classify integrity only. §4.7 forbids ClaimTuple/support-frame registration until a shared dependency carrier and warrant are human-approved; do not invent measurement fields or a new ladder. Preserve the immutable OP-73 package/PIN00e and all ungraded bootstrap receipts, with no backfill. Current installation LR-6a is accepted; NIB2-88 recovery remains distinct. Source wiring completion does not claim the first future installation receipt or authorize restart/cleanup.

- [x] **VB-LR8-EVENT-DUTY — capture prospective synthetic event-duty verification.** ✅ 2026-10-06 — MAIN accepted native88/88 run37514086438 and unchanged shared-grade analysis37515763800, Judged/Located; [exact inputs/originals/limits](../../artifacts/ni08/lr8-source-acceptance-20261006/README.md). Use the existing NI07 native CI carrier and shared `claim_tuple.grade()`. Bind exact source/recipe/carrier pins, selected test inputs, original JUnit/status, environment and artifact hashes at capture; preserve failed originals. Off-host temporary fixtures only: inactive defaults, handover refusal, cadence, CPU gate, overlap and result/alarm semantics. No live daemon handover, host cleanup, atomic exclusion against the unchanged daemon or deployment warrant.

- [ ] **VB-AK-LANE-OWNERSHIP — write future lane ownership dependency records at creation.** Current-metadata audit found33 frozen-clone lane registrations but no accountable session identity in native campaign/status metadata. Update the AutoKernel-owned creation writer at its owning session boundary to capture session/campaign, exact source/common-dir identity, lane path/HEAD, creation timestamp and manifest hashes prospectively. Preserve historical uncertainty; never infer an owner from directory/status or reconstruct a tuple on read. Integrity/dependency evidence only until a human-approved shared carrier/warrant exists; no new ladder, frozen-kernel modification or autonomous cleanup. [Audit](../../artifacts/ni08/nib77-ownership-audit-20261006/README.md).


## NI08 prospective harness and diagnostic sources

- [ ] **VB-HIL-WRITE — wire HIL feature A/B measurements prospectively before their first suite run.** The owning evaluation producer writes an immutable, self-hashed sidecar at run finalize with one native row per run × arm × feature × objective metric. Bind the run locator, feature ID, baseline/candidate arm, exact prompt/parameter path and SHA-256, harness/config/Harness Card pin where applicable, suite/version/split, metric/value/unit/direction, native verdict, scored and attempted denominators, date, and only the model/server/recipe/host identities the actual suite used. Carry an owning protocol ID only when one already applies; otherwise preserve a truthful observation. The strict adapter reopens the producer-authored bytes, refuses missing/mismatched identity or digest, projects only facts present in the sidecar into the existing `measurement` `ClaimTuple`, and lets `claim_tuple.grade()` decide. Reuse the existing shared measurement ladder; add no ladder, retroactive rows, evaluator scoring rule, policy mutation authority, or promotion authority. For the HS-14 shell bake-off, reuse SC86's shell-run writer/reader fields rather than duplicating them. Land the row, producer hook, and strict read-path checks before the first future HIL efficacy run; no run is authorized by this filing.
  - 2026-10-21 NOTE (noninf-vidya): the carrier now exists, `scripts/vidya/adapters/harness_improvement.py` (root `7335da327`) with the HIL-2 item 14 pins required, strict reader, tests and `cli.py ingest harness-improvement`. Only the producer hook (a sub-bullet under HIL-6 in `harness-improvement-loop.md`) is owed; box left unticked.

- [x] **VB-AP-ME-DIAGNOSTICS — verify native failure identity/count/rendering source prospectively.** Before synthetic capture, bind exact APP source, ROOT recipe and existing native CI carrier; retain original JUnit/status, runtime context, readset and hashes. Diagnostic fields are native metadata only, not measurements or root-cause proof. Delegate outer synthetic conformance to the existing shared `claim_tuple.grade()`; no new operational ladder, legacy backfill, tuning, serving reload or change to existing AP measurement authority.

✅ 2026-10-06 VB-AP-ME-DIAGNOSTICS source verification accepted by MAIN: [native21/21, independent originals and unchanged existing grade](../../artifacts/ni08/failure-signatures-source-20261006/README.md). Native diagnostic fields remain ungraded; existing AP measurement authority unchanged.

## NI08 prospective metadata and offline diagnostic producers

- [ ] **VB-M19-WRITE — wire memory-write decision metadata at its native writer before first capture.** Follow APP `memory-write-decision-record-v1.md`; preserve initial producer bytes, opaque references, honest human/typed/unknown provenance and immutable external calibration joins. Metadata is ungraded dependency only, not a ClaimTuple/authorization. Existing native CI carrier/shared grade verifies a future writer; any actual calibration study requires its own native measurement record and existing ladder. No historical backfill or confidence gate.
- [x] **VB-AP-ME-CONTEXT — verify default-off prospective mutation-context capture and crossover diagnostics.** Bind exact native assembled input SHA/bytes/chars and observed source/config/trial identity without raw content; preserve unknowns. Shared feature comparison must preserve BSV policy, with fail-closed same-context recorded donor eligibility. Grade synthetic conformance through existing carrier/shared grade only; native diagnostics remain ungraded. No budget changes, gate decisions or inference authorization.
- [x] **VB-ETVT2-DIAGNOSTICS — verify offline tool-use report source prospectively.** Before synthetic capture bind exact APP source/tests, ROOT recipe and existing carrier, retaining original selected JUnit/context/readset hashes. Report native attempted/scoreable denominators and unknown/partial states, never causal blame, a new scoring rule or decision-grade efficacy. Existing shared grade governs source conformance; actual tool_use data needs a future authorized owner cohort.

- [x] **VB-DCP-LOG-USAGE — preserve prospective privacy-bounded transcript usage snapshots.** Capture only allowlisted usage/time and private opaque identities, source before/after hashes, exact schema/parser/runner pins and immutable private projection. Unknown/moving/malformed and duplicate/ambiguous records remain explicit. Descriptive cache-input shares only; no content, pricing estimate, billing authority, task-quality or Definition-1 prediction. Native metadata is ungraded; no reconstructed ClaimTuple or new ladder. MAIN independently recomputes aggregates from the private allowlisted projection before accepting DCP-9a scoped usage audit.

✅2026-10-06 VB-ETVT2-DIAGNOSTICS accepted by MAIN: [native11/11, independent input/original custody and unchanged shared grade](../../artifacts/ni08/tool-use-report-source-20261006/README.md); diagnostics remain ungraded and parent cohort remains open.

- [x] **VB-TD30F-REPLAY — bind prospective authored-Markdown repetition-detector replay.** Before the approved hosted successor capture, bind exact corpus Git pin/selector/schema and source-manifest digest, exact guard AST/config/source hashes, original aggregate output and native CI receipt/readset. MAIN reconstructs the manifest independently. Existing native carrier/shared grade verifies runner conformance only; provenance-based trigger shares stay ungraded descriptive, no gold false-positive labels, production streaming or model-output claims, threshold change, new ladder or historical corpus reconstruction. Preserve parent TD-30f.

✅2026-10-06 VB-DCP-LOG-USAGE accepted: [approved source, immutable private projection and independent MAIN aggregate recomputation](../../artifacts/ni08/usage-source-audit-20261006/README.md); ungraded metadata only, no billing/Definition1 warrant.

- [x] **VB-MFVBS-VERIFIER — bind batch-verifier reporting source conformance prospectively.** Exact APP source/tests, AST-isolated actual batch helper functions with explicit bootstrap/stub scope, actual sandbox apply/verify/promote modules, exact ROOT recipe/carrier and selected original test bytes. Capture original JUnit/context/readset/member hashes through existing native carrier/shared grade only. Verify owner-command snapshot, syntax-only honesty, command failure/no-promotion, stale-base and inactive compatibility. No model-authored postcondition execution, semantic policy enforcement, host tests, full-graph inference or BEP efficacy claim. Parent MF-VBS-2 keeps inference remeasurement separate.

✅2026-10-06 VB-TD30F-REPLAY accepted by MAIN: [independent predispatch source/corpus binding, original native custody and unchanged shared grade](../../artifacts/ni08/td30f-public-replay-20261006/README.md). Runner conformance only; descriptive trigger shares remain ungraded and parent TD-30f stays open.

✅2026-10-06 VB-MFVBS-VERIFIER accepted by MAIN: [original native nine-case conformance, source/fixture/context binding and unchanged existing shared grade](../../artifacts/ni08/batch-verifier-source-20261006/README.md). No actual BEP or semantic-policy result; parent remains open.

✅2026-10-06 VB-AP-ME-CONTEXT accepted at the source boundary after [independent original88/88 review](../../artifacts/ni08/mutation-context-source-20261006/README.md). Native metadata remains ungraded; capture defaults off.

## NI08 prospective harness transport and period-cell controls

- [x] **VB-HS4-P7-CONFORMANCE — bind generated stdin transport source conformance before capture.** Use the existing native CI carrier and shared `claim_tuple.grade()`. Bind exact ROOT source/recipe/carrier, dependency-lock source, expanded case identities, config/linter closure, original JUnit/status and runtime readset. Synthetic long/Unicode prompt and exact argv controls plus full existing HS-4/HS-19a/task-delegation compatibility suites only. Preserve original historical r3 bytes and failures; no actual OpenCode/model invocation, efficacy, serving acceptance, new ladder or historical warrant. ✅ 2026-10-06 — [Original138/138 and MAIN source/API review](../../artifacts/ni08/harness-stdin-source-20261006/README.md); unchanged existing Judged/Located outer observation,33Git+2contexts/all44members reopened. No host/model execution or historical warrant.
- [x] **VB-PII-PERIOD-CONFORMANCE — bind observed-periods cell controls before capture.** Use the existing native CI carrier and shared grade. Bind exact hook/tests, public four-column schema, recipe/carrier, expanded case identities, source/readset/context and original JUnit/status. Seven synthetic 12/13-digit cells must pass while account/secret, other-column and context-boundary controls refuse. No raw historical prompt/PII retrieval, blanket file exemption, original unredacted-fixture acceptance, privacy/promotion authority or new grading ladder. ✅ 2026-10-06 — [Original73/73 and MAIN2,276Git+2contexts/all2,287API-member review](../../artifacts/ni08/pii-period-source-20261006/README.md), existing shared Judged/Located only. Original failed53/73 retained; no parent/privacy warrant.

- [x] **VB-C5-JOIN-CONFORMANCE — bind persisted seed/provider join source verification before capture.** Existing native CI carrier/shared grade only. Bind exact Research corpus/loader/oracle/tests, ROOT recipe/carrier and runtime closure; verify eight exact joins, 193 unchanged workload counts, dtype/correctness-only compatibility, missing/ambiguous/mismatched fields and rendered reverse map. Preserve original JUnit/native receipt and failures. No provider benchmark, SOL port, model, GPU, build, measured correctness or timing/promotion claim.


## NI08 thesis reader prospective verification

- [x] **VB-THESIS-CONFORMANCE — bind the prospective UFH-13 thesis reader source controls before capture.** Use the existing native CI carrier and shared grade, with exact ROOT adapter/CLI/dispatcher/test/recipe/import sources, pinned Research producer helper/constants and explicit checkout, hash-locked runtime dependencies and expanded case identities. Preserve original JUnit/receipt/readset/context and failures. Synthetic producer-native pooled rows only; verify manifest/source identity, sibling records digest and native dates/reps/verdict/preregistration consistency, omission/refusal/no-raw-answer controls. Empty native protocol remains empty; no scored thesis run, inference, rescoring, historical tuples or new grading ladder. VB-THESIS-1 first scored-run boundary remains separate.


C5 source conformance accepted2026-10-06: [original27/27, MAIN32-Git input binding and all43 original members](../../artifacts/ni08/c5-seed-provider-join-20261006/README.md). Existing shared Judged/Located observation only; no missing historical policy reconstruction or production run.


- [x] **VB-AP60-CONFORMANCE — bind per-instance QScorer environment source verification before capture.** Exact reviewed APP constructor/write/retrieval paths and full115 changed-plus-compatibility identities, actual exercised import/dependency closure, recipe and existing native carrier/shared grade. Synthetic temporary-store controls only; preserve originals and refusal/failures. No model/embedding/ONNX startup, production retrieval/write, runtime deployment or scoring-quality claim.


UFH-13 reader source accepted2026-10-06: [MAIN original29/29 source/custody review](../../artifacts/ni08/thesis-reader-source-20261006/README.md), exact30Git+4contexts/all45members. VB-THESIS-2 projection and conformance are complete; VB-THESIS-1 actual first scored run remains open, protocol empty, existing observation grade only.


## Prospective remaining source verification — 2026-10-06

- [x] **VB-AP62-CONFORMANCE — Bind the exact reviewed invocation-ring locking and full current request-scope/route-guard module before hosted synthetic capture. Verify append/clear serialization with real locks, paused readers and writer-specific acquisition signals; preserve source/readset/case identities and originals through existing carrier/shared grade. No serving reload, request-quality claim or host project execution.**
- [x] **VB-RTG02-CONFORMANCE — Bind the exact programmatic input-echo probe, existing deterministic scorer and explicit unsafe-method refusal controls before hosted capture. Synthetic rows only; unchanged scorer/metric semantics, exact source/import closure, expanded cases and original readset/JUnit/carrier output. No actual pool rebuild, model/code-execution/math/LLM scorer calls, replay or new ladder.**
- [x] **VB-RAW-ANCHOR-CONFORMANCE — Bind the reviewed prospective retained-RAW store, versioned source resolution and shared literature proof verifier before hosted synthetic capture. Exact bytes/private identity/revision/extractor controls, missing/changed/FIFO/hardlink refusal, original source/readset/case/carrier output; no live fetch, historical anchor reconstruction, canonical intake/ledger write or new semantic grading rule.**
- [x] **VB-TUADV-CONFORMANCE — Bind the exact DTAP synthetic invalid-capability/repeated-payload fixture controls and unchanged runner/catalog/judge/trace closure before hosted capture. Preserve typed failure chains, positive benign/attack verdict and immutable originals through existing carrier/shared grade. No live endpoint, attack search, new scoring or global skill-store claim.**


- [x] **VB-C5-POLICY-CONFORMANCE — bind recovered historical-policy carrier source verification before capture.** Exact preserved policy Git blob/SHA, reviewed Research loader/corpus/tests and existing native carrier; full28-method source/compatibility selection, actual default `load()` positive and tamper/missing/symlink/hardlink/traversal refusal controls. Bind exact recipe/runtime/source/readset before hosted capture and retain originals. Same policy ID/claims/pin and shared grade; no replacement authority, GPU/SOL run or reconstructed historical tuple.


- [ ] **VB-OBS1-CONFORMANCE — bind reviewed coordinator-observer source controls before any hosted synthetic verification.** Exact private source/recipe/carrier, synthetic activation/source inode/PID-start-tick identity, both singleton locks, three-valued refusal and confirmed-exit restart suppression; actual closure and expanded cases, original readset/JUnit/status retained through existing native carrier/shared grade. No host lock/process probe, signal, launch, activation, grading change or deployment warrant. Protected coordination merge separately requires the exact D9 operator acknowledgement.
- [x] **VB-HS4-P6-SOURCE-CONFORMANCE — bind the shared exploration core’s source verification prospectively.** Exact reviewed APP/Research caller and fence identities, pure explicit-root service, compatible REPL adapters, bounded synthetic traversal/symlink/read-cap controls and original source/JUnit/carrier artifacts. Existing native carrier/shared grade only; no active MCP catalog change, semantic-index rebuild, embedding/model invocation, live task rerun or new read authority. Parent P6 catalog-growth acceptance remains separate. ✅ 2026-10-07

2026-10-06 MAIN acceptance: VB-C5-POLICY-CONFORMANCE completed after exact source publication and independently reviewed original28/28; [bounded acceptance](../../artifacts/ni08/c5-policy-path-source-20261006/README.md). Historical policy bytes and existing grader unchanged; no SOL/GPU/runtime warrant.

2026-10-06 MAIN source acceptance: the two prospective report writers/readers and SC80 completed after originalROOT38/38+APP20/20 and byte-identical APP publication. [Bounded source/evidence](../../artifacts/ni08/analysis-report-source-20261006/README.md); legacy reports refused, existing metric/shared-grade authority unchanged.

- [x] **VB-HS19D-P0-DESCRIPTIVE-CONFORMANCE — bind exact prospective sanitized-summary source controls before hosted capture.** Existing shared CI verifier only; synthetic redaction, unknown/ambiguous/failed-record, filesystem identity refusal and actual default pinned committed-verdict positive controls. Native count readout remains descriptive/ungraded; no global corpus, served-template or dispatch warrant. Preserve all original source/context/JUnit receipts and unchanged shared grade.

2026-10-06 MAIN accepts VB-RTG02-CONFORMANCE after original23/23 and exact source publication; [review](../../artifacts/ni08/rtg02-echo-source-20261006/README.md). Existing shared grade unchanged, no live pool/effect warrant.

2026-10-06 MAIN accepts VB-TUADV-CONFORMANCE after independently reviewed original6/6 and test-only source publication; [scope](../../artifacts/ni08/tuadv-contract-source-20261006/README.md). Parent global/external attack work remains open, shared grade unchanged.

- [x] **VB-AUD11-F08-CONFORMANCE — bind exact actual-command interval-refusal fixtures and mutation source before off-host capture.** Existing shared native CI carrier only, original unmodified-source controls plus explicitly recorded AST mutation/refusal sensitivity. Test-only source, no real nudge/bus/process, protected source change, operator inference or new grade.
- [x] **VB-RTG23-W8-CONFORMANCE — bind planner-display missing-versus-zero source controls before capture.** Preserve legacy stored/helper zero/math; actual missing/malformed display n/a, valid zero and positive unchanged. Exact source/cases/context and existing native carrier/shared grade only; no live frontier, rate improvement or objective amendment.

2026-10-07 MAIN accepts SC76/SC77 and VB-RAW-ANCHOR-CONFORMANCE after exact source review and original51/51 hosted synthetic controls; [evidence/scope](../../artifacts/ni08/raw-anchor-source-20261007/README.md). Retained RAW verification replaces shape-only proof prerequisites through one checker; missing originals stay unknown, machine cap/shared ladder unchanged. SC78/SC79 remain separately open; no actual fetch or historical intake/ledger write.

2026-10-07 MAIN accepts the fixed-verdict descriptive-summary source and its prospective conformance companion after original4/4, full source/API custody review and normal APP publication; [scope](../../artifacts/ni08/hs19d-p0-summary-source-20261007/README.md). Broader P0/template and unknown native fields remain separate; counts ungraded, no historical or global-corpus warrant.

## Newly unlocked retained-source numeric controls

- [x] **SC78/79-NUMERIC-ANCHOR-CHILD — refuse claim-to-quote numeric mismatches through the retained-RAW verifier.** Pass indexed claim text at both research-intake projection sites into the existing numeric-agreement helper. Synthetic response → fetch → RAW-store → anchor/projection controls only. One shared magnitude is sufficient under the existing helper; no full numeric entailment, semantic/name/title/negation verdict, real fetch, Stage-1/2 extraction, canonical intake/ledger write, historical backfill or new ladder. Parent SC78/SC79 remain open. ✅ 2026-10-07 — MAIN accepted exact source and original23/23; [bounded evidence](../../artifacts/ni08/sc78-numeric-anchor-source-20261007/README.md).
- [x] **VB-SC78-79-NUMERIC-ANCHOR-CONFORMANCE — prospectively bind the reviewed numeric-mismatch source and actual synthetic producer/projection controls before hosted capture.** Exact source/cases/readset/original JUnit through the existing native CI verifier and shared grade. Preserve missing-source unknowns and earlier failures; no literature-truth warrant or historical reconstruction. ✅ 2026-10-07 — MAIN accepted exact source and original23/23; [bounded evidence](../../artifacts/ni08/sc78-numeric-anchor-source-20261007/README.md).

## Newly unlocked prospective source verification — 2026-10-07

- [x] **VB-SSBENCH-SMT-CONFORMANCE — bind the reviewed physical-core launch-guard source and both direct/API synthetic controls before hosted capture.** Exact source/callers/topology fixtures/dependencies/readset/JUnit and original native receipts through the unchanged native CI carrier/shared grade. Unknown topology refuses; no live host probe, reload, kernel change or production isolation warrant. Runtime activation remains the owning session’s boundary.
- [x] **VB-INF41-S20-CONFORMANCE — bind the reviewed server-only route fallback source before hosted capture.** Actual handler with fake HTTP/OCR boundaries, explicit server/auto/cli/malformed/default and healthy-path controls; exact source/context/cases/native artifacts through existing carrier/shared grade. No live vision, CLI/model launch, measured timing bound or parent S-20 acceptance.
- [x] **VB-EVL38-PERIODIC-CANDIDATE-GATE — capture scheduled complete root candidate-gate executions prospectively.** Bind exact ROOT/APP/Research/frozen-llama commit IDs, whole actual validator/test/config/readiness/registry/PII input closure, unchanged native carrier files, workflow/driver/test, Python 3.13.15 and hash-locked binary-only dependency environment before invocation. A wrapper must assert the actual full gate exit; strict `CANDIDATE_EVAL_REQUIRE_DEPS` avoids missing-dependency skips. Keep original argv, gate exit/log/JUnit/status and red/NULL originals. Existing codex-ni-main session maintains the scheduled workflow. No readiness/promotion/continuous-health authority, future-source claim, strict-doc-drift claim unless invoked, inference/performance warrant, tuple backfill or new ladder. ✅ 2026-10-07
  MAIN accepted bounded source/evidence: [review](../../artifacts/ni08/evl38-periodic-gate-20261007/README.md).

2026-10-07 MAIN accepts VB-RTG23-W8-CONFORMANCE after original3/3 and exact source publication; [bounded acceptance](../../artifacts/ni08/rtg23-w8-display-source-20261007/README.md). Missing/malformed display stays distinct from valid zero; historical/objective math and shared grade unchanged.

2026-10-07 MAIN accepts VB-AP60-CONFORMANCE after exact115/115, all original bindings/shared grade and source publication; [bounded source acceptance](../../artifacts/ni08/ap60-instance-settings-source-20261007/README.md). Runtime, historical population capture and distillation remain separate.

2026-10-07 MAIN accepts VB-AP62-CONFORMANCE after original14/14, complete actual source/context custody and shared grade; [source publication](../../artifacts/ni08/ap62-invocation-ring-source-20261007/README.md). No live concurrency or runtime claim.

2026-10-07 MAIN accepts VB-AUD11-F08-CONFORMANCE after baseline2/2, ungraded predicate-disable witness and full55-member original custody; [acceptance](../../artifacts/ni08/aud11-f08-source-20261007/README.md). Existing shared grade unchanged, no live coordination authority.

2026-10-07 MAIN accepts VB-HS4-P6-SOURCE-CONFORMANCE after exact source publication and original11/11, complete source/API custody and unchanged shared grade; [bounded acceptance](../../artifacts/ni08/hs4-p6-exploration-source-20261007/README.md). Parent catalog-growth acceptance and actor deployment remain open. ✅ 2026-10-07

## Prospective formatter, teardown and protected assignment controls — 2026-10-07

- [x] **VB-RTG23-W9-CONFORMANCE — bind reviewed planner formatter missing/invalid-versus-zero source controls before hosted capture.** Full existing formatter unit module, exact APP source/import/read closure, ROOT task/source table, unchanged native carrier/shared grade and hash-locked compatible wheels. Original JUnit/status/readsets unchanged across grading. Missing quality/rate stays non-replayable; no objective/sequential/archive writes, live frontier/rate/quality, inference or reconstructed tuple. ✅ 2026-10-07
  MAIN accepted bounded source/evidence: [review](../../artifacts/ni08/rtg23-w9-display-source-20261007/README.md).
- [x] **VB-EXL3-3B-CONFORMANCE — bind exact teardown polling source and full existing claimed-run test module before hosted capture.** Synthetic fake-clock delayed-clear and persistent/unknown census controls, exact ROOT/Research/carrier/dependency identities, original JUnit/native receipt through existing CI adapter/shared grade. No GPU/HIP, build, physical claim or device re-run; parent EXL3-3b physical acceptance remains open. ✅ 2026-10-07 — MAIN accepted [original39/39 and exact source](../../artifacts/ni08/exl3-teardown-source-20261007/README.md).
- [ ] **VB-RTG52-D9-CONFORMANCE — bind the protected source proposal and full selected coordination test modules before hosted capture.** Exact six-file source/read closure, strict direct-target grammar and ambiguous/negated abstention, fake stdin/Popen exact bytes, oversized refusal and bounded confirmed child cleanup. Existing native CI carrier/shared grade only. No host dispatch/signal/assignment correctness authority or protected merge; D9 operator acknowledgement remains separate.

## Prospective conversation persistence/controller and trace registrar controls

- [x] **VB-CS15-STORE-CONFORMANCE — bind actual session transcript and incremental-summary source before hosted synthetic execution.** Exact APP source/import/tests, session lease/lifecycle compatibility, actual SQLite round trips, history/overflow/frontier/refusal controls, dependency/source-context closure and original JUnit/native receipts. Existing native CI adapter/shared grade; no live memory/voice/model/schema migration, historical rewrite or semantic summary quality warrant. ✅ 2026-10-07 — MAIN authenticated [original31/31 and complete457-input custody](../../artifacts/ni08/cs15-conversation-store-source-20261007/README.md).
- [x] **VB-CS-VOICE-CONTROLLER-CONFORMANCE — bind the transport-neutral controller and injected cascade source before hosted capture.** Real controller/service adapter paths, synthetic queue/backend events, concurrent-turn refusal and cancellation/fallback/bounded-stream controls; exact source/cases/original custody through existing carrier/shared grade. No concrete endpoint/audio/model/timing or parent live voice acceptance. Reopened 2026-10-07: original276/276 and declared463-input custody remain unchanged, but eight existing import inputs were omitted. [MAIN correction](../../artifacts/ni08/cs14-import-manifest-correction-20261007/README.md); corrected prospective full276 rerun and independent original review are now complete. ✅ 2026-10-07 — [Corrected prospective original276/276](../../artifacts/ni08/cs14-corrected-acceptance-20261007/README.md), MAIN full472-input custody accepted; verifier restored without changing historical originals.
- [x] **VB-UTM-B1-CONFORMANCE — bind read-only trace MCP registrar source controls prospectively.** Actual off-host FastMCP dotted-name/schema/defaults and synthetic SQLite navigation, exact APP source/import/cases/environment/native readset and immutable original JUnit through existing carrier/shared grade. Default server catalog unchanged; no live trace DB, model/embedding, deployed MCP or catalog-growth acceptance. ✅ 2026-10-07 — MAIN accepted [original5/5 and full31-input custody](../../artifacts/ni08/utm-b1-read-only-mcp-source-20261007/README.md).

- [x] **VB-M11-WORK-CAP-CONFORMANCE — prospectively bind memory work-cap source and actual regression cases before hosted execution.** Exact APP producer/sanitizer/tests/import closure, locked dependencies, original source/environment/JUnit/native receipt and unchanged complete fresh result-tree custody through existing CI native adapter/shared grade. Synthetic forged-marker/large-input controls only; no live traffic, store migration, privacy or semantic quality warrant. ✅ 2026-10-07 — MAIN accepted [source and original41/41](../../artifacts/ni08/m11-work-cap-source-20261007/README.md).

- [x] **VB-UTM-B4-CONFORMANCE — bind the existing Tulving retrieved-arm trace backend and full synthetic module before hosted execution.** Exact published Research source, APP trace SQLite/FTS/navigation imports and full23-case identities; set the exact orchestrator checkout and private RUNNER_TEMP store so all four trace-only controls execute, with zero skips. Retain installed wheel/source/context identities and complete original native/JUnit/result-tree custody through existing CI carrier/shared grade. Existing source implementation only, no actual dataset/model/embedding, retrieval quality or live-memory warrant. ✅ 2026-10-07 — MAIN accepted [original23/23 including all four trace controls](../../artifacts/ni08/utm-b4-tulving-source-20261007/README.md).

- [x] **VB-UTM-B3-CONFORMANCE — prospectively bind BEAM ingest-provenance producer and synthetic memory-arm controls.** Exact Research adapter/chunking/question-to-QuestionResult source closure, full static case identities, lock-derived installed dependencies and actual native original JUnit/receipt/source/environment/full fresh result-tree custody through unchanged CI carrier/shared grade. Verify all-role/source-order counts and range, pair-chunk granularity and full-arm no-retriever label. No dataset, model, retrieval-quality or historical run warrant. ✅ 2026-10-07 — [Complete original21/21 and source custody](../../artifacts/ni08/utm-b3-beam-provenance-source-20261007/README.md) MAIN accepted.

- [x] **VB-SC42-ODL-WRITER-CONFORMANCE — bind the prospective ODL producer and strict reader to actual hosted synthetic controls.** Exact Research659d154be/ROOTc8f2de90 source, dependencies, relevant complete tests and writer-to-reader roundtrip; retain original native/JUnit/environment/readset and unchanged complete result-tree custody through existing native CI adapter/shared grade. Fake model/window values are synthetic only; no actual ODL measurement, legacy backfill or new grading ladder. SC42 source closure requires integration after this check. ✅ 2026-10-07 — [MAIN accepted exact source and original8/8](../../artifacts/ni08/sc42-odl-write-source-20261007/README.md); full38-input/50-member custody, synthetic only.
- [x] **VB-W4-STACK-CHANGE-GATE — capture the bounded real stack-change promotion gate with exact source/config/fixture pins.** Execute the six original target suites in each temporary swapped world and retain their actual output/counts plus outer original JUnit and whole gate exit, pass/refusal controls and unchanged native shared-grade receipt. No skipped target, fake subprocess, model/server or host mutation; a synthetic pass establishes execution only, never stack readiness/deployment. ✅ 2026-10-07 — [MAIN exact original acceptance](../../artifacts/ni08/w4-real-gate-success-acceptance-20261007/README.md).

2026-10-07 SC42 source-review boundary: the old successor-inference gate applies to the real matched A/B run, not prospective write-hook authoring. MAIN reviewed Research`659d154bea1daba3406a04a766fa09810fb0aeb6` and ROOT`c8f2de90abf6f79c0637cdc0b1de8f346921a44b`; VB-SC42-ODL-WRITER-CONFORMANCE now owns synthetic full-source proof before integration. Existing SC42 remains open until that source boundary closes; historical demo is never upgraded.

2026-10-07 MAIN accepted VB-INF41-S20-CONFORMANCE: run37563431358, allfive actual controls, nativeTRUE, existing Judged/Located with complete original2,833-input/result-tree custody. Source integrated; synthetic policy conformance only, no latency/model/live-warrant.

- [x] **VB-FW1-MOCK-CONFORMANCE — prove the documented mocked GUI/CLI decision and refusal paths.** ✅ 2026-10-07 — Execute the bounded test module against the authored graph and injected mock worker; retain exact module/caller/config inputs, collected identities, JUnit, native receipt and unchanged shared-grade output. Include accepted think/retry/approval → worker → validation, denied approval → zero worker calls, and V1 accepted/refused terminal controls. No model/server, production executor, canonical measurement tuple or change to measurement VB-FW-1. MAIN source-reviewed APP `38d4ab72fe95ef7c1064d6574b3552a182023850` before native preparation.


## Prospective reference and registry/environment source controls — 2026-10-07

- [x] **VB-EVL38-REFERENCE-CONFORMANCE — capture the existing governance-reference validator against the nine corrected documents.** Bind exact ROOT recipe/source, validator, complete actual scanned source/local-target bytes, source/task context, unchanged native carrier and locked environment; require the single selected validator case to pass and retain original JUnit/receipt/full fresh result/source shared-grade custody. No whole-candidate readiness, validator policy waiver, host shim, frozen-kernel or measurement-trust amendment. ✅ 2026-10-07 — [MAIN accepted original1/1 and exact source/custody](../../artifacts/ni08/evl38-reference-conformance-20261007/README.md).
- [x] **VB-SW-SCG-SOURCE-CONFORMANCE — capture canonical registry-banner and uncovered undeclared override source controls.** Bind exact APP0a40117c five-file source plus full registry-compiler, env-attestation, diagnostic-override and UFH12 embedder modules (97 prospective AST-expanded items), unchanged native carrier and full locked import/environment/readset closure. Original actual JUnit/result/source bytes remain unchanged through shared grading. Fake process env/PIDs/temp records only; no live /proc, reload, stack/runtime change or policy/measurement warrant. Source SW-5/SW-6 and SCG-ENVOVR-EXPIRED stay unchecked until evidence and integration. ✅ 2026-10-07 — [MAIN original97/97 acceptance](../../artifacts/ni08/registry-banner-override-source-20261007/README.md).


## Prospective voice payload and explicit-choice controls — 2026-10-07

- [x] **VB-CS16-18-CONFORMANCE — bind the exact APP source, full affected test modules, dependency lock, context, and unchanged native CI carrier before off-host execution.** Run the actual complete `tests/unit/test_voice_route_contract.py` and `tests/unit/test_voice_controller_contract.py` modules (31 AST function identities, with decorator-expanded native identities to bind separately, at reviewed proposal pin `bbf38c98b6a9984d6fc6f8f9f7656dd0cad0ec3f`). Retain authenticated native receipt/JUnit/readset/environment and complete result-tree custody through the existing carrier/shared grade. Controls are synthetic in-process fakes only. Do not claim spoken quality, exact audio realization, first-token/cancel latency, microphone/device support, or real Whisper/QwenTTS/service behavior. ✅ 2026-10-07 — [MAIN accepted published source and original31/31](../../artifacts/ni08/cs16-18-success-acceptance-20261007/README.md); no live speech/timing warrant.


2026-10-07 MAIN acceptance: [normally published source and original97/97](../../artifacts/ni08/registry-banner-override-source-20261007/README.md) close SW-6, SCG-ENVOVR-EXPIRED and the prospective verifier. SW-5 keeps its wider active editing-reference documentation sweep open. Full source/result custody verified; original capacity collection NULL retained; no shared-host test, runtime reload or measurement warrant.


## Prospective lane-hook and static pin-checker sources — 2026-10-07

- [x] **VB-LR12-REFERENCE-HOOK-CONFORMANCE — verify the edited-file Git-root reference hook with all five actual subprocess controls.** Bind exact hook/test/document/target bytes, runner bash/git/python3/rg/jq tools, unchanged native carrier and full source/result custody; retain three baseline tests and two real temporary Git lane tests, original JUnit/receipt and shared grade. Explicit runner-created synthetic queue existence fixture is a generated input, never a copy of the live queue. No host tests or broad cleanup.
- [x] **VB-EVL42-PIN-STATIC-CONFORMANCE — capture the complete static benchmark pin-checker synthetic controls.** ✅ 2026-10-07 — Bind exact Research checker/test source, actual AST/JUnit identities, locked test environment, unchanged native carrier and full source/result custody. Cover tracked temporary Git scan/CLI exits and unsafe or unstable paths; no actual benchmark execution, re-pin, or current production pin-health projection.
- [x] **SC-EVL42-PIN-REPORT-WIRING — bind future categorical pin-scan findings at write time and prepare their existing-ladder projection.** Preserve exact checker/scanned-source byte identities, Git HEAD/dirty context, scan membership and per-row current/stale/missing/unresolved reasons before the original scan is consumed. MAIN reviews the native record-to-ClaimTuple projection; no second ladder, retrospective warrant, numeric performance claim or automatic pin repair. Synthetic CI acceptance does not complete actual-scan wiring. ✅ 2026-10-07 — [MAIN original44 controls plus actual-wrapper acceptance and exact public source](../../artifacts/ni08/evl42-actual-pin-scan-source-acceptance-20261007/README.md). Historical checker rc1/incomplete report remains explicit; no pin-health tuple.

Prospective CPU v2 implementation received independent static source PASS on 2026-10-07 in the dedicated `ak-codex-cpu-held-segments-v2-20261007` worktree (base `9fca6a5d`); original native tests remain queued. The sealed carrier separates completed per-generation CPU ownership from the original outer completed `stage_elapsed` clock frame. Physical accumulation, fairness and CPU forecasts use held segments; full campaign/seed budgets and failed-duration fences use the separately validated wall frame, digest-bound to receipt IDs. Preserve that distinction in the existing adapter projection, with no new ladder or historical retrofit. A later caller audit found an interruption-recovery holder join still using the first component instead of the original outer clock identity; its CPU-only repair and added native regression require a refreshed review beyond that eight-file snapshot. Runtime PASS, compatible parent/worker activation and adapter integration are still required.

The refreshed nine-file CPU v2 snapshot subsequently received independent SOURCE PASS (report SHA-256 `90957711fe7e70653738244447b29137ee467477ec3d194c30ae16f2d71ba10c`). Recovery applies authoritative capture refusal and validates native segments before using the outer clock identity; replacement still requires a freshly live original native owner. This supersedes the eight-file source review. The original exited-child regression and existing recovery tests remain queued; the revised durable commit gate binds all nine files. No runtime PASS or activation is asserted.

  Prospective helper preparation is bounded to strict original report attachment through the existing CI verifier. A complete report with stale rows is preserved; fixture conformance does not assert current pin health. The future actual scan/write/read acceptance remains a separate parent event.
  - [x] **VB-EVL42-PIN-REPORT-CONFORMANCE — verify prospective strict pin-report attachments through the existing native CI carrier.** Bind exact helper/test and unchanged Research checker Git blobs, all29 expanded actual outer identities, real nested receipt/JUnit attachments, isolated locked pytest environment and complete before/after source/result custody. Exercise current/stale/missing/unresolved, original TRUE/FALSE/NULL, absent/tampered/mixed receipts and owned-inode partial-write/fsync cleanup/refusal. Use unchanged native_rows/project_ci_conformance and shared grade only; synthetic source conformance does not close SC-EVL42-PIN-REPORT-WIRING or claim an actual Research scan, pin-health, loaded-code, readiness or automatic repair warrant.


- [x] **VB-RVP-SSM-ROLLBACK-CONFORMANCE — bind actual fresh experimental CPU rollback initializer and graph controls before hosted execution.** Sixteen seeds and two independent raw captures per seed invoke the reviewed actual C++ initializer; independently replay the unchanged CPU-reference backend graph. Bind complete source, compiler/header/build/runtime-library identities, original outputs, exact native receipt and unchanged shared-grade custody. Synthetic off-host CPU source conformance only; no model, GPU, frozen production modification, performance/promotion or accepted live measurement event warrant.


- [x] **SC42-SOURCE — publish the prospective ODL writer and strict native-record ingest bridge before successor inference.** ✅ 2026-10-07 — [Actual source and original8/8](../../artifacts/ni08/sc42-odl-write-source-20261007/README.md) accepted by MAIN; existing shared measurement ladder and legacy-null behavior retained. SC42 parent stays open for actual canonical matched A/B and its first measured tuple.

2026-10-07 MAIN: [LR12 source/native acceptance](../../artifacts/ni08/lr12-reference-hook-source-20261007/README.md) closes the enrolled five-case verifier after authenticated48-member/34readset original custody review; the hosted empty runtime fixture proves no live bus state.

✅ 2026-10-07 VB-FW1-MOCK-CONFORMANCE: [MAIN original custody and accepted source](../../artifacts/ni08/fw1-success-acceptance-20261007/README.md), through the existing native CI carrier/shared grade. Future live/measurement source tasks retain their independent gates.

✅ 2026-10-07 VB-EVL42-PIN-STATIC-CONFORMANCE: [MAIN original custody and accepted source](../../artifacts/ni08/evl42-success-acceptance-20261007/README.md), through the existing native CI carrier/shared grade. Future live/measurement source tasks retain their independent gates.

- [x] **VB-CS20-21-HTTP-CONFORMANCE — bind the complete injected voice HTTP and WAV source controls.** MAIN reviewed private APP `9c76824f549f45f22cf315e1fb3cb7f832558a13`: actual controller/cascade with Whisper/SSE/Qwen MockTransport clients, bounded WAV file CLI, exact terminal/cancel identity, precise media type, iterator-close and payload-free JSONL controls. Capture the whole26-function module with all expanded cases and exact eager source/config/locked environment before existing native execution; retain complete original API/JUnit/shared-grade source/result custody. No actual service/model, voice quality, latency, GPU, Annex S ratification or runtime activation. ✅ 2026-10-07 — [MAIN isolated source and original26/26](../../artifacts/ni08/cs20-http-wav-success-acceptance-20261007/README.md).
- [x] **VB-RTG23-W6E-SOURCE-CONFORMANCE — capture the full W6 diagnostic producer module controls.** MAIN reviewed private APP `129a58c29d3ed1814caa1acfa29d14f604020886`: descriptive optional core/fresh partition means and quality-denominator counts, nullable absence/reasons, positive core-minus-fresh direction, differing suite/question mixes, task-failed wrong-answer denominator, infra/scoring-failure exclusion and unchanged shadow-only objective. Capture all34 actual test functions and all38 expanded native case identities, exact eager sources and complete locked wheel closure; existing native CI carrier/shared grade only. No live trial, causal overfitting estimate, calibration or promotion rule. ✅ 2026-10-07 — [MAIN separate fresh original38/38 and published source](../../artifacts/ni08/w6e-success-acceptance-20261007/README.md).
- [x] **VB-RTG23-W6E-DIAGNOSTIC-CARRY — carry only the optional authored W6 block into existing autopilot-journal informational support.** Read `eval_details.details.w6_generalization` on future native producer rows; preserve nullable fields and reasons, leave absent legacy rows byte-stable, and do not reconstruct old trials, infer missing partitions, change the quality ClaimTuple/shared grade or feed this descriptive gap into promotion. Bind real writer/reader source and synthetic absent/measured/disabled/off-cadence/empty/task-failed/infra/scoring-failure controls prospectively; one existing journal class/ladder. ✅ 2026-10-07 — [MAIN optional-carry source and original31/31](../../artifacts/ni08/w6e-journal-carry-success-acceptance-20261007/README.md); raw authored diagnostics/canonical JSON support, legacy/quality/grade unchanged; two FALSE and setup originals preserved.

✅ 2026-10-07 VB-SSBENCH-SMT-CONFORMANCE: [MAIN original81/81 custody and exact source publication](../../artifacts/ni08/ssbench-smt-success-acceptance-20261007/README.md). Source conformance only; runtime-owner activation and real isolation evidence remain independent.

- [ ] **VB-INF64-REACHABILITY-CONFORMANCE — bind the completed per-file reachability manifest and actual source/reference controls before capture.** Exact Git blobs/modes, candidate/test/data/entrypoint/HOLD edges and original outputs through the existing native verifier/shared grade. Missing source references remain unknown; no historical tuple reconstruction, runtime reachability, deletion authority or new grading ladder.
  - [ ] Include the 2026-10-25 accepted re-screen/readset in this existing task: [durable findings](../../docs/reference/cme7t-inf64-accepted-findings-20261025.md), report SHA-256 94ad54ced756508606eb508a48dec964e2b1e480154870a400973a6efee2073c plus module/test/data/guard inventories. Observational source matrix only; native controls, runtime reachability and deletion authorization remain unproved. Reuse the native verifier/shared grader; no backfill or new ladder.

✅ 2026-10-07 VB-RVP-SSM-ROLLBACK-CONFORMANCE: [MAIN actual original3/3 and experimental source publication](../../artifacts/ni08/rvp-rollback-success-acceptance-20261007/README.md). Actual64 raw initializer captures/CPU-reference replay; no production/GPU regression, live event, performance or promotion warrant.


## Prospective shared helper and test-log isolation source controls — 2026-10-07

- [x] **VB-S49-MTMD-PROBE-CONFORMANCE — bind the shared executable-discovery helper and its distinct callers before hosted synthetic capture.** Bind exact APP source/test/config/import pins, all selected cases, the runner-only configuration (including explicit hosted timeout control), original argv/JUnit/status and complete source readset through the existing native CI producer and `ci-fixture-conformance` adapter/shared grader. The bounded suite covers the common Bash executable/LD-library-prefix/timeout/status/output contract, symlink target resolution, strict versus tolerant Python parsing, resolver order/overrides, and the exact real bounded timeout child-death control. Preserve every original result and failure. No configured model/server binary, inference, build, performance, promotion, or runtime-use warrant; no new source class or grading ladder. MAIN independently reopens source and original custody before acceptance. ✅ 2026-10-07 — [MAIN acceptance](../../artifacts/ni08/s49-mtmd-probe-success-acceptance-20261007/README.md): original37597364740 TRUE11/11,63 frozen Git inputs/65 native reads,29 packages/all412 wheels; prior NULL/setup originals retained. Source published APP7134d796; runtime warrant remains excluded.

- [x] **VB-SCG-TEST-LOGDIR-CONFORMANCE — bind the real pytest bootstrap and progress-log construction-time destination controls before hosted capture.** The actual root conftest establishes a unique temporary environment override before application imports; the real no-argument logger writes during test execution. Bind the complete actual conftest/AppState/import/dependency closure, unchanged selected module cases, private default-destination sentinel preservation, isolated rows, explicit constructor precedence, ordinary runtime default without override and teardown environment restoration through the existing native CI producer/shared grader. No collection-time logger construction is claimed: the current real API construction is inside lifespan initialization. No copied bootstrap, --noconftest shortcut, shared-host tests/log writes, API/model/server activity, inference, deployment or new grading ladder. MAIN reopens original source/JUnit/custody before acceptance. ✅ 2026-10-07 — [MAIN source/original4/4 acceptance](../../artifacts/ni08/scg-test-logdir-success-acceptance-20261007/README.md), APPb87998e3; actual root bootstrap/real during-test logger, constructor override/default/sentinel/teardown and authenticated temporary JSONL copies. Original NULL/setup evidence unchanged; no shared-host tests/logs or runtime warrant.

- [x] **VB-NI08-FAILED-ORIGINAL-CUSTODY — independently authenticate the twelve retained failed native/setup endpoints without regrading or rewriting outcomes.** ✅ 2026-10-07 — [MAIN exact original-record review](../../artifacts/ni08/failed-original-custody-review-20261007/README.md) binds fresh API/ZIP/receipt/attachment/JUnit identities:10FALSE,1NULL,1setup with no receipt. No implementation, source-validity, deployment or scientific warrant is inferred.


✅ 2026-10-07 VB-EVL42-PIN-REPORT-CONFORMANCE: [MAIN exact source and original29/29](../../artifacts/ni08/evl42-report-success-acceptance-20261007/README.md).10unique nested original seals retained (8TRUE/1FALSE/1NULL),13archive path copies only;11symlink/91empty-directory archive limitations explicit. Actual pin-health scan/wiring remains independently open.


- [x] **VB-K11-REPEAT-SUMMARY-CONFORMANCE — bind the actual requested-repeat summary producer and full synthetic controls before capture.** Exact Research source/test blobs, complete eager source/config and lock-wheel closure, actual run_execute fake-server/persisted per-run and summary TRUE/FALSE/NULL tests, original nonpositive-repeat refusal and owned-process cleanup; existing native verifier/CI family/shared grade only. No server/model, kernel build, live determinism or new ladder; original source/result/readset/API/JUnit custody retained at capture. ✅ 2026-10-07 — [MAIN exact source and original30/30](../../artifacts/ni08/k11-repeat-summary-success-acceptance-20261007/README.md). Live K11 determinism remains independently gated.

- [ ] **VB-PIP02-FRESH-COHORT-WIRE** — wire fresh PIP02 native Paddle/ODL attempt capture and the later common scorer into the source registry and planning context; preserve original request/grant/source/config and censored region state, and pass the planning-context canary. Collection projectors retain operational page-count/output-byte observations only; scorer-native TEDS and structure-only TEDS require their own same-GT/cohort/coverage record and actual protocol. Use shared ClaimTuple.grade(); never reconstruct a quality warrant from operational counts. Prospective declaration and producer roots are registered in `scripts/vidya/adapters/README.md`.
  - 2026-10-29 23:40: original ODL relocatable-r2 shards16/17/5/8/9 now have125 reopened native page records with original pre-client producer/source/plan bindings, matching predictions and DONE digests; preserve them for the strict common-score projector. YARN-JUDGE-1 integration closure is also a committed-conclusion candidate backed by one native judged cell and its exact original50-item judge pin. [Filing register](../../artifacts/compute/results-filing-20261029-2340.json); no retrospective quality warrant or planning-context canary claimed. [belief: cc]
  - 2026-10-29 include the native relocatable ODL source-manifest/row binding and multi-shard Paddle r7/r8 capture roots now registered in the existing source row. Keep native operational observations separate from quality grading; original source/body/response and unknown records remain authoritative. [no-belief: source registration for existing wiring task]
  - 2026-10-29 the frozen common scorer now emits an ungated retained-output snapshot: `artifacts/compute/pip02-partial-teds-20261029/`. Extend the existing strict lineage adapter to original generic/parallel ODL packets, separate provably unexposed recoveries and native multi-shard Paddle captures before decision use; preserve current refusals and null gates until their evidence and full coverage are valid. No new grading ladder or retrospective measurement tuple. [belief: cc]
  - 2026-10-31 register the literal original R32 pool1 continuation and Research `3da40c0942c1` immutable scorer in the existing PIP-02 source family; preserve 30 unmatched region starts and prior response lineage. Public controls and READY are prospective setup, not a quality measurement or completion. [no-belief: source registration for existing wiring task]

- [x] **VB-PIP02-SELECTED-LIBRARY-CONFORMANCE** — freeze/review the actual two-file PIP02 selected-binary library correction and whole original ODL module, all original Research/APP/OmniDocBench/carrier/lock inputs and hosted-only synthetic contexts. Capture one approved hosted native run with all30 exact current whole-module controls (the earlier prospectively enrolled source had29), original JUnit/receipt/API/artifact bytes and full source/result/external-lock custody through the existing CI carrier/projector/shared grade. Preserve TRUE/FALSE/NULL/setup originals and ZIP symlink/empty-directory limitations. Acceptance applies only to selected-binary launch-argument source conformance, not actual ggml linkage, GPU residency, parser quality, production role or performance. MAIN applies source/native acceptance; document-parser parent remains open. ✅ 2026-10-07 — [MAIN current-source/original30/30 acceptance](../../artifacts/ni08/pip02-current-provenance-source-acceptance-20261007/README.md); TRUE30/30, source/publication5fd103e8,664 Git/727 native inputs; older29-case source observation unchanged.

- [x] **VB-ET13-ROUTING-CONFORMANCE — bind the reviewed routing implementation and complete selected source controls before hosted capture.** Freeze the exact two-file APP candidate, four whole test modules/140 expanded identities, eager source/config and all locked dependency wheels. Exercise frontdoor/worker/architect precedence plus unknown/empty/model-ID routing; preserve original route bytes, original native receipt/JUnit/readset/environment/result-tree custody through unchanged native_conformance.py → ci_conformance.native_rows → project_ci_conformance → shared claim_tuple.grade(). No new ladder, denominator/gate/default/objective, runtime process/kernel, inference or release authority. MAIN independently reviews original custody before acceptance; the mixed E5 parent remains open. ✅ 2026-10-07 — [MAIN exact source and original140/140](../../artifacts/ni08/et13-honest-routing-source-acceptance-20261007/README.md); native TRUE/shared Judged/Located, original setup/NULL/FALSE retained; live/runtime and mixed E5 remain open.

- [x] **VB-EVL24-DISTINCT-RUN-CONFORMANCE** — bind actual source92c9ec87, complete original16-case promote-job module, package initializers, PyYAML/pytest six-package ALL52-wheel lock closure and actual MAIN prospective source/context enrollment before one reviewed GitHub-hosted capture. Exercise duplicate/invalid/missing logged-run apply refusal with original temporary jobs/records/verdict/gold files and preserve unchanged positive stages/risk/gold/operator behavior. Retain original API/job/artifact/ZIP/JUnit/native receipt, source/readset/environment and typed result/error custody through existing native_conformance.py, ci_conformance projector and shared claim_tuple.grade(). No new source class/ladder, retroactive lab claims, actual live promotion/queue/model or inference warrant. MAIN reviews and applies bounded source/native acceptance. ✅ 2026-10-07 — [MAIN source/original16/16 acceptance](../../artifacts/ni08/evl24-distinct-run-source-acceptance-20261007/README.md); exact APP73984542, TRUE16/16; live parent gates unchanged.

- [x] **VB-NI08-DCP2-COLGREP-SCORE-CONFORMANCE** — prospectively bind exact APP sourceb21e45af, whole tests/unit/test_context_discovery.py25 cases, both parser/direct routes, complete executed source/config envelope and minimal ALL-wheel locked dependency identities before one MAIN-approved GitHub-hosted capture. Retain original JUnit/output/receipt/self-seal/source/readset/dependency log/runner environment/API/job/artifact/ZIP and typed result/error custody. Inject search inputs and prove the ColGREP binary absent; no live search/model/embedding execution. Reuse existing native CI producer/projector and shared claim_tuple.grade(), no source class/ladder or retrospective tuple. Native acceptance covers only exact synthetic source conformance, not live ranking quality, broad integration, performance or promotion. MAIN reviews/apply; preserve FALSE/NULL/setup originals. ✅ 2026-10-07 — [MAIN exact source/original25 acceptance](../../artifacts/ni08/dcp2-finite-score-source-acceptance-20261007/README.md); APPf0df, native TRUE25/25, original status/grade/custody preserved; broader live gates remain open.


- [x] **VB-NI08-UFH12-SPILL-SUMMARY-CONTEXT-BUDGET — prospectively bind the actual spill-summary context-budget source controls.** ✅ 2026-10-07 — [MAIN original and product acceptance](../../artifacts/ni08/ufh12-spill-summary-source-acceptance-20261007/README.md). Exact APP source `63399d6` / public product `8108452`, ROOT recipe `533d649`, whole15 identities, 3,829 native source reads, 52 locked packages/714 wheel hashes and original run `37664607006` attempt1 passed15/15 with native TRUE/exit0. MAIN independently accepted the original API/JUnit/ZIP/native receipt and typed source/result/fixture custody; the existing `native_conformance.py` → `ci_conformance.native_rows` → `project_ci_conformance` → shared `claim_tuple.grade()` yields one Located/Judged observation, no new ladder or protocol decision warrant. Original NULL runs `37649822725` and `37659831973` remain NULL with no retrospective tuple. Mocked workers and owned temporary spills only; no quality/quote fidelity, evidence-retention, ColGREP/embedding, inference, runtime/performance/promotion warrant.

- [x] **VB-RVP-C6-26-C-POINTER-CONFORMANCE — prospectively bind the actual C-pointer lexical source controls.** Exact Researchb2b44 repair descending9f415,6 actual source/metadata inputs,9 class-qualified whole controls (original37617279801 FALSE8/9 retained; no acceptance), explicit separate APP70096 lock5packages/all5wheels, unchanged carrier and actual owning/table contexts. Preserve original receipt/JUnit/API/ZIP/environment/readset and full typed source/result/error phases through existing CI projection/shared grade; NULL remains no tuple. No new source class/ladder, arbitrary memoization absence, GPU timing/ranking, kernel, native performance or parent completion. MAIN reviews originals before acceptance. ✅ 2026-10-07 — [MAIN exact source/original9 acceptance](../../artifacts/ni08/c-pointer-literal-source-acceptance-20261007/README.md); Researchaefa, original TRUE9/9 and prior FALSE retained. Publication lease deviation recorded; parent/GPU/kernel gates unchanged.


- [x] **VB-INF50-LEAN-DOC-PROJECTION — bind the INF50 source-to-generated-lean document check.** ✅ 2026-10-07 — Bound the exact source context and corrected original hosted capture `37637333789`; MAIN independently accepted complete native output/cache custody, including the supported writer banner. Public APP main commit `01db99c03451ac3c4d2e7593a53781486707595f` carries the same captured output bytes (SHA-256 `3f1f52b7…bdb04f2`). It is UNGRADED and differs from the pinned current APP baseline only at the retired historical prose scalar. Source and existing cache stayed unchanged. No JUnit, native receipt, ClaimTuple, new ladder, runtime selection authority, or historical backfill. [MAIN original custody/publication](../../artifacts/ni08/inf50-native-writer-product-acceptance-20261007/README.md).

- [x] **VB-DS41-C104-FUTURE-WRITER-CONFORMANCE — bind future-writer decisive-flag source controls before isolated native capture.** Freeze exact two-file Research1880877, whole8 actual controls, adjudicated eager/selected helper/config closure and explicit separate APP70096 pytest/jsonschema lock11packages/all110wheel hashes. Actual temporary SQLite/Comparison/Outcome/render-context controls only, no actor/CLI/model/real store execution. Existing native CI producer/projector/shared grade with immutable original TRUE/FALSE/NULL/error/readset/environment/API/ZIP/source/result custody; no new ladder or historical14 projection. MAIN reviews exact recipe/original before source publication. ✅ 2026-10-07 — [MAIN exact source/original8 acceptance](../../artifacts/ni08/c104-decisive-source-acceptance-20261007/README.md); Research9299 publishes only the accepted two blobs. Parent/historical14/live-owner gates remain open.

- [x] **VB-DS41-C106-HOLD-CONFORMANCE — bind the existing HOLD enum/constructor source correction.** Prospectively bind exact Researchb223b53 two-file product, all16 whole-module synthetic control identities, actual eager/deferred-control source/config/readset and complete locked ALL-wheel identities to the owning DS41-C106 and source-table context before one MAIN-approved hosted capture. Reuse native_conformance.py, ci_conformance projector and shared claim_tuple.grade(); preserve original API/job/artifact/ZIP/JUnit/receipt/source/result/error snapshots and all TRUE/FALSE/NULL/no-receipt distinctions. No new source class/ladder, policy floor/cadence/keep/serving changes, production kernel, live loop/reload, inference or promotion warrant. MAIN reviews original and exact publication before acceptance. ✅ 2026-10-07 — MAIN original synthetic16 acceptance/run37635340254, exact Research product `3613455d5114d78968fab464b9cdc8a18df2f306`; [original source/readset/mode/grade/API custody](../../artifacts/ni08/c106-hold-source-acceptance-20261007/README.md). Existing Judged/Located identity matches receipt seal; no new grade/warrant or retrospective tuples.

INF50 prospective writer boundary, 2026-10-07: VB-INF50-LEAN-DOC-PROJECTION now binds the exact supported native generated writer output/cache/banner in fresh absent custody paths in addition to the accepted original ungraded dry-run. Final actual recipe/K/context must be reviewed before one new original; no fabricated CI receipt/JUnit/claim or scalar hand-edit. Existing source/cache and all operative semantics remain immutable; parent/source task remains unchecked until product publication.

- [x] **VB-NI08-SPARSE-CAPACITY-CUSTODY — wire original guarded sparse-operation receipts as ungraded document/artifact dependencies.** ✅ 2026-10-07 — [MAIN original helper/plan/process/sample custody](../../artifacts/ni08/sparse-capacity-custody-20261007/README.md) preserves every original byte and source/index/KEEP conservation boundary through existing VB-NI07-DOC-DEPS source handling. Seven approved own idle worktrees sparsely exclude tracked duplicate benchmarks/data; two final available-byte samples exceed the peer gate52.591536328seconds apart. Native/test/measurement grade remains absent; no ClaimTuple on read, new ladder, permanent capacity or peer runtime/inference authority. Current gate is rechecked by its owner.


## Prospective late-entry literature coverage — 2026-10-07

- [x] **VB-RI-INTAKE-DELTA-1333 — project the unchanged current dive-verified intake-1333 record to resolve the in-range #01 ledger-coverage miss.** ✅ 2026-10-07 — MAIN accepted the one-entry native projection of intake-1333#record through the existing literature adapter and owned-inode ledger lease. Exactly 13 reviewed frames were appended. Independent whole-prefix and full-fold review confirms 14,354 records with a clean chain, five new Verified/Located beliefs, no changes to existing beliefs, and claim 04 still review-required. The index record and all fourteen governance modules remain unchanged. Missing retained source-artifact anchors stay UNKNOWN; the existing shared grade remains Located. [Original custody](../../artifacts/ni08/intake1333-literature-coverage-20261007/README.md). NI08 now **175 = 110 existing checkbox closures + 65 completed scoped children**.


## Prospective C26 initial-floor stop cancellation source — 2026-10-07

- [x] **VB-DS41-C26-CANCEL-CONFORMANCE — bind the bounded DS41-C26-CANCEL-SOURCE original controls.** Freeze Research0858dc64 four-file candidate, whole20 CPU/GPU startup parameter cases and all26 test_serving methods, full selected source/config/deferred-import envelope and separate APP70096 lock11packages/ALL156 wheel hashes. Real Popen/server/region-lock seams are mocked; GPU quiet-window seam is explicitly nullcontext. Existing native CI producer/projector/shared grade, exact pre-grade/error/final source/result/API/ZIP/JUnit custody only. MAIN publishes enrollment before final recipe/K/capture and reviews originals before source publication. Parent mixed-runtime stop behavior, live serving, inference, quality/performance and production promotion remain separate; no new source/grade ladder. ✅ 2026-10-07

2026-10-07 MAIN accepted current source checkpoint: Research `e136226d00421742645bf2f157737a8cedf348f1` is public on main; original ROOT `5933d75d2d935edc2f3d542fd3240863548be8ab` push attempt passed all46 selected fixtures. Complete1588-path readset, seven stable inventories, five typed snapshots/6407 regular-file checks and existing shared Judged/Located grade are independently accepted. The original0858 NULL, aad7 FALSE and17f FALSE remain unchanged. This completes only the bounded source/control tasks; actual C26 runtime/floor/cadence evidence remains with its owner. [Accepted source and original custody](../../artifacts/ni08/c26-current-source-acceptance-20261007/README.md).

2026-10-07 second capacity-source association: existing VB-NI08-SPARSE-CAPACITY-CUSTODY / VB-NI07-DOC-DEPS expands to the [original second-request safe-alternate custody](../../artifacts/ni08/sparse-capacity-second-request-20261007/README.md). MAIN completed exactly two additional idle historical Research worktree hydration exclusions. The semantic full indexes, source metadata/bytes, HEADs, branches, KEEP and Git objects remain preserved; only tracked duplicate benchmarks/data copies were sparsely excluded. Allocated recoverable copies totaled **3,360,518,144 bytes**. Original final free-space samples **111,330,381,824** and **111,329,828,864 bytes**, **54.629409002 seconds** apart, both exceeded the **110,500,000,000-byte engineering target** and 100 GiB hard floor. This safe alternate does not promise eight billion bytes of recovery or inference admission. Original helper/manifest/process/command/sample custody stays ungraded through existing VB-NI07-DOC-DEPS handling; no new ClaimTuple, ladder, native test, inference or runtime warrant. One operational child is completed; no additional source class or grade is introduced.

2026-10-07 three-view operational source association: existing VB-NI07-DOC-DEPS / VB-NI08-SPARSE-CAPACITY-CUSTODY expands to [bounded original three-view custody](../../artifacts/ni08/three-source-view-sparse-custody-20261007/README.md). MAIN accepted the guarded sparse materialization of exactly three own unused committed source views: two C26 Research views retain four physical source files each and the UFH ROOT recipe view retains three. All eleven kept source byte/mode/physical-metadata records, semantic full indexes, HEADs, branches, Git objects and the existing ignored cache remain conserved. The 302 original command records and three completed checkpoints are retained unchanged; both earlier eligibility refusals remain separate originals with no sparse application. Raw index cache inode/mtime/ctime volatility was explicitly reviewed before apply. This is ungraded operational source-view custody through existing VB-NI07-DOC-DEPS handling; it closes no native/source task and asserts no measured allocated recovery, free space, runtime activity, inference admission, grade or new ladder. One operational child completes; no native/source checkbox closure or new grading rule.


## RTG-39 administrative source reconciliation — 2026-10-07

The existing literature association for intake-913#record is retained. MAIN closed the two source/documentation tasks in the blocked RTG-39 owner and corrected its two stale recommended-action strings, leaving verification status, source claims, dive corrections and native ledger unchanged. The [inert data contract](../../docs/design/experience-distillation-data-contract.md) defines provenance only and produces no source record; prospective teacher/student producer wiring remains required before any future execution. No new checkbox, adapter, ladder or current warrant is created.

## TD-29.M0a raw prefill source controls — prospective companion

- [x] **VB-TD29-PREFILL-SOURCE-CONFORMANCE — bind the whole-module `/completion` prefill controls before off-host capture.** After MAIN pins the prospective ROOT filing and the APP source commit, capture the complete `test_llama_server.py`, `test_inference_mixin.py` and `test_typed_decisions_call_recorder.py` modules, their 119 AST test definitions as currently pinned, exact function bodies, in-module fixtures, both applicable conftests, `pyproject.toml`, and `uv.lock` with every locked package version and wheel hash. Preserve the exact existing controls `TestEarlyStopTiming::test_early_stop_produces_timing`, `TestRecordLlmCalls::test_every_call_is_logged_and_summed`, and `TestRecordLlmCalls::test_absent_telemetry_is_none_not_zero`; do not substitute guessed test names. Bind ROOT's existing native CI producer, verifier, adapter, shared ClaimTuple carrier, exact command/readset and original request/log/JUnit/receipt before execution. The original JUnit supplies actual collected/executed counts; AST counts are source inventory only. Existing `ci-fixture-conformance` and `claim_tuple.grade()` remain the sole verifier/ladder. No inference, sidecar/runtime/three-arm claim, performance result, source-quality claim, duplicate parent closure or new grading rule. Historical prospective condition at filing: capture was pending MAIN's prospective filing and execution authorization. ✅ 2026-10-08 — [Accepted original209 source/control custody](../../artifacts/ni08/td29-current-source209-acceptance-20261008/README.md); APP main eadb. This paired source child is complete; parent sidecar/inference gates remain open.

### Accepted native CI receipts: canonical ledger projection follow-up — 2026-10-07

- [x] **VB-NI08-ACCEPTED-CI-LEDGER-PROJECTION — project five prospectively enrolled original native receipts into the canonical belief ledger through its existing leased writer.** Use the existing ci-fixture-conformance adapter and shared grade only: EVL42 controls and actual-wrapper TRUE, C26 current 5933 TRUE, and preserved C26 aad7/17f FALSE; earlier 0858 NULL emits no tuple. Bind exact original sealed request/readset/receipt bytes, reject duplicates, conserve the complete prior ledger prefix, acquire the owned-inode write lease, and verify the appended chain and deterministic fold. MAIN reviews the exact wrapper before append and accepts the original execution at the task boundary. This projects source-conformance observations, not pin health, inference, runtime or promotion authority. Original receipt identity/warrant is unchanged. ✅ 2026-10-07 — [MAIN exact five-receipt canonical append acceptance](../../artifacts/ni08/accepted-ci-ledger-projection-20261007/README.md).

SC-EVL42-PIN-REPORT-WIRING is complete through the real historical checker attachment and original44 controls; [original source/native/publication custody](../../artifacts/ni08/evl42-actual-pin-scan-source-acceptance-20261007/README.md). The earlier29-control synthetic task remains closed and is not counted twice. MAIN's read-only canonical ledger snapshot had14,354 frames and none of the five native receipt identities; the bounded projection task above tracks that still-open physical ingest gap independently of source wiring.


2026-10-07 MAIN accepted the existing CI-family projection: exactly five original receipts (EVL actual-wrapper and44 controls plus currentC26 TRUE; preservedaad7/17f FALSE) append15frames to canonicalledger14354→14369. The complete14642518-byte prior prefix and all5819 prior beliefs remain unchanged; independent whole-chain/same-asof fold verifies five new Judged/Located observations. Both private V4/V5 wrapper refusals happened before append and retain original custody; the separately approved V6 succeeds with actual inode lease and44-byte sidecar lifecycle/release/absence proof. Original booleans and seals remain unchanged; oldestNULL emitszero tuples. This means source fixture conformance only, never pin health, runtime, performance or promotion authority.


## Prospective HG5 and SC55 source boundaries — MAIN enrollment 2026-10-07

- [x] **VB-HG5-FORCE-SOURCE-CONFORMANCE — capture the exact focused force-mode source controls before source acceptance.** Bind whole APP source envelope and four whole modules: tests/unit/test_v1_escalation.py, test_v1_escalation_off_golden.py, test_openai_compat_default_golden.py and test_stages.py. Pin source/config/lock/all-wheel identities before one later MAIN-approved original off-host push event. Existing native CI producer, ci-fixture-conformance reader and shared claim_tuple.grade() only. Preserve original TRUE/FALSE/NULL, JUnit identity multiset, source/result/error/readset/API/ZIP custody. No live model, inference, quality, routing activation, runtime or deployment warrant. Parent HG5 remains open for runtime/H3 scope. ✅ 2026-10-08 — [MAIN original87 source and publication acceptance](../../artifacts/ni08/hg5-force-source-20261008/README.md).

- [x] **VB-HG5-TAP-WRITE — preserve new source-owned request escalation events at capture time.** Prepare producer/schema and synthetic fixtures after HG5 source acceptance: requested mode, feature/eligibility result, initial role, quality/caller_forced trigger, target, step outcome, actual calls/token/timing counters, bounded failure, final role and source revision. Bind immutable event bytes and contemporaneous source/window; missing or ambiguous counters refuse projection. Live capture remains with its inference owner; no historical backfill, correctness claim or new ladder. MAIN source review2026-10-08: writer coverage is the completed post-answer explicit-plan boundary only; upstream failure before that boundary emits no event and cannot enter an all-request denominator. Preserve observed outcome separately from nullable call-count status, clear one owned event attempt after finalization, and contain emitter failures. ✅ 2026-10-08 — [Original240 source controls](../../artifacts/ni08/hg5-request-event-writer-source240-20261008/README.md); MAIN independently accepted source, original publication, native240 and completed ordinary APP main promotion (acceptance SHA256 `330b4a252ed1b5a1a7624fc4fe94b903b72c914c2a5dae3bd247c6429adeff0d`). TAP-READ and runtime/H3 parents remain open.

- [x] **VB-HG5-TAP-PROJECTION-LABELS-WRITE — capture explicit source-owned metric declarations before a new HG5 request window.** Optional version2 declaration in source-authored pre-run context: exact category, direction for each known cost metric, and explicit protocol_id. Category/direction have no defaults. An explicitly empty protocol string records no citation and remains an observation under the existing ladder; a nonempty native citation never asserts human ratification. Bind canonical declaration digest before capture, preserve runtime origin unknown and default-off behavior, and keep all974 v1 events unchanged/ungraded. Strict reader refuses absent/malformed labels, validates native version2 source/declaration/envelope custody, and copies only recorded labels into the existing measurement ClaimTuple. Exercise actual writer/reader/Source/CLI controls before task closure. MAIN accepted the ten-file source design (SHA-256 `ed05c5568db21aed698dc43685aebb3309e53dbb1a7262c963eda421129f6ee9`); ordinary source commits and original APP249/ROOT84 controls are independently accepted. No historical backfill, runtime activation, policy/ladder change, correctness/efficacy or parent completion. ✅ 2026-10-08 — [Native label and strict reader source boundary](../../artifacts/ni08/hg5-native-labels-reader-source-20261008/README.md); ordinary APP main promotion and normal ROOT source integration independently accepted. Runtime/H3 parents remain open.

- [x] **VB-HG5-TAP-READ — strictly project an accepted new request-event envelope.** After the writer and MAIN-accepted source-owned envelope, validate exact version/schema/hash, request/step cardinality, finite nonnegative timing, integer token/call counts and trigger/result/final-role/failure consistency. Project factual intervention/cost through the existing measurement ladder, never answer correctness; no runtime authorization. Static reader and refusal fixtures are non-inference work. ✅ 2026-10-08 — [MAIN original84 reader/Source/CLI/ledger controls](../../artifacts/ni08/hg5-native-labels-reader-source-20261008/README.md), coupled to the independently accepted original APP249 writer source. No live request activation or parent completion.

- [x] **SC55-WRITE — implement capture-time immutable graph-profiler provenance before new measurements.** ✅ 2026-10-08 — [Source contract and MAIN original43/43 review](../../artifacts/ni08/sc55-source-contract-20261008/README.md); Research main c722, strict writer/reader source controls; owner-controlled live capture remains separate. In Research, prepare a source-owned envelope binding raw TSV/node table/log/run receipts by path/size/hash, actual source commit/tree, capture window, profiler .so digest and compiled-knob strings proof, effective knobs/thread count, graph identity/filter, eval/warmup semantics, measuring-thread/dispersion and IQK state. Capture pre/during-run facts contemporaneously; finalization only seals them after raw outputs close. Missing/unknown provenance is unprojectable. Implement static writer/schema/refusal fixtures without host inference or production-kernel changes; owner-controlled live capture follows later. Historical files are never backfilled.

- [x] **SC55-READ — implement a strict graph-profiler reader after the source writer contract.** ✅ 2026-10-08 — [Original native48/48 and normal-ingest source](../../artifacts/ni08/sc55-source-contract-20261008/README.md); strict seal-file custody wrapper, dispatcher Source and CLI choice, unchanged measurement ladder. Historical data remains unprojectable; live SC55 parent stays open. Validate exact producer headers (19 node columns, seven PATHROW columns), bound digests/sizes, unique node identities/cardinality, integer identities/evals, finite nonnegative values and graph/thread/filter semantics. Use an accepted source-owned envelope and existing measurement ClaimTuple ladder; malformed/ambiguous/unknown provenance emits no tuple. Synthetic controls are non-inference work; no new grading rule.

Actual-source clarification: node fields use wall_max_us/wall_max_ev and aggregate thr_max_us/thr_mean_us/thr_min_us, not per-thread vectors. PATHROW uses calls_per_eval, bytes_per_eval, GBs_on_compute and GBs_on_wall. The output knob is GGML_CPU_PROF_PERNODE_FILE; absent GGML_CPU_PROF_THREADS makes zero thread columns unavailable evidence, not measured balance. Current shape/node indices do not prove structural graph identity. Source audit retains production commitffc1bac and grammar blobebc487; no frozen tree modification. Existing aggregate node_profile.py JSON and ROOT cycle samples are different native producers.


## MAIN source review boundary — 2026-10-08

HG5's five-file source commit `c12c9c5` and five native recipe files are statically reviewed; 87 proposed identities are unexecuted. TD29 original run `37707130166` is independently verified NULL (missing FastAPI before collection, exit 4, no JUnit); its three-file dependency successor is source-reviewed against the same lock, with 64 versions and all 905 wheel hashes. Original NULL receipts are immutable. SC55's initial writer is statically reviewed, with 20 controls unexecuted; write-side native measurement labels, strict reader and ordinary ROOT consumer loading are being completed within the existing SC55-WRITE/SC55-READ tasks. All companion boxes remain open. Existing native CI and measurement adapters project into the shared carrier; no new grading rule or retrospective tuple. See the periodic full custody package and NI08 reference for original review pins.

- [x] **VB-MFFS1-DOC-DEPS — preserve and review the original MF-FS-1 diagnostic input/source dependencies before canonical use.** MAIN prospectively enrolled2026-10-08: exact bounded classifier source, current APP producer/emitter pins, original private same-FD snapshots, sorted read-set and aggregate digests through existing VB-NI07-DOC-DEPS only. Legacy producer origin remains unattested; substring flags and marker categories do not establish causal stop reasons. No new adapter/class/ladder, historical tuple or inference/quality claim. Existing MF-FS-1 owns classification; no duplicate MF-FS source child.

✅2026-10-08 VB-MFFS1-DOC-DEPS: [MAIN source/input snapshot and independent aggregate acceptance](../../artifacts/ni08/mf-fs1-diagnostic-20261008/README.md).72 original inputs, three source snapshots, prospective enrollment before capture, no native grade or reconstructed legacy tuple.

- [x] **VB-MF-TURN-WRITE — implement and validate the prospective BEP turn scalar contract for MF-NDG-1/MF-RR-1.** MAIN reviewed the bounded APP62ee source candidate and frozen `announced_action.lex-v1` grammar on 2026-10-08. Preserve one default-off row per turn and existing raw-text limits; record post-extraction state before execution, primary/retry completion metadata separately, requested caps with unknown effective caps/token basis, and boolean/null lexical status with explicit ambiguity/truncation/retry exclusions. Producer path is not runtime revision attestation: keep runtime origin explicitly unknown until the owning harness authors contemporaneous custody. Validate source-first publication with the existing off-host native carrier and exact synthetic controls. This child covers instrumentation only; fresh owner-controlled inference traces, rate estimates, prompt changes and efficacy remain with the original MF parents. Existing shared ladder only; no historical backfill or new grading rule.

2026-10-08 VB-HG5 source acceptance:87/87 exact original synthetic controls at e54175dc, zero failures/errors/skips,2,229 preserved native readset hashes and2,243 archive members verified. APP main76624a91 publishes the accepted default-off source; original FALSE/NULL records remain immutable. Source fixture conformance is one completed scoped child; VB-HG5-TAP-WRITE/READ and owner-controlled runtime/H3 scope remain open.


### 2026-10-08 TD29 prospective companion accepted

Original push run `37729628899` attempt1 at ROOT `11f1b00ae478a76544eb3b649f4b0d9af199095a` passed all209 cases from seven whole mocked modules (175 AST definitions): TD122 plus unchanged HG87, zero failures/errors/skips. APP current-tip merge `eadb959172fbc433da41aaf069c1bcf20c6ce98f` is promoted to remote main by one ordinary nonforce fast-forward from76624a91. MAIN independently accepted the source merge, four-file recipe commit,123-command source-first publication, original209 custody and120-command main promotion. Earlier FALSE/NULL archives remain immutable. Existing native CI adapter/shared carrier returns Judged/Located observation only; no runtime activation, model quality, inference, performance or three-arm sidecar result.

[Original209 source custody](../../artifacts/ni08/td29-current-source209-acceptance-20261008/README.md) completes the single existing VB companion paired with TD-29.M0a.S0. Synthetic controls are not separate tasks; no second source ladder or retrospective tuple is authored. Parent inference gates remain open.

- [x] **VB-RTG48-DOC-DEPS — preserve ungraded Git/document dependencies for the RTG-48 A-2/A-3/A-4/A-5/A-6 source adjudications.** Bind the original incident-report commit bodies, supervisor source, current test/source and A-1 audit identities before downstream documentation consumption. Keep historical reports distinct from original runtime authentication; selected rows provide no population denominators. Use ordinary document dependencies without a ClaimTuple producer, read-side tuple invention or new ladder. ✅ 2026-10-08 — MAIN accepted [exact source custody](../../artifacts/ni08/rtg48-a2-source-review-20261008/README.md) and the bounded adjudication.

### 2026-10-08 prospective HG5 request-event writer source boundary

APP source `974cb4017791a5d500269fd44f7d9903528e1d5d` implements the default-off source-owned HG5 request event writer. The independent writer directory knob captures only completed post-answer explicit-plan outcomes, with one bounded immutable event attempt, nullable actual call/token/timing counters, distinct outcome/call status, bounded failure class and final role. Optional source-authored context leaves loaded runtime origin unknown. Quality/force failures and emitter exceptions preserve answer/legacy receipt behavior; initial upstream failures before the finalizer produce no event. No all-request denominator, historical backfill, efficacy/correctness grade or runtime activation is claimed. Original push run `37734573366` attempt1 at ROOT `5e653b10f2bf2853f4f8f40c69eb24c91f877837` passed all240 whole-module synthetic controls (TD122+HG87+TAP31;205 AST definitions/eight modules), zero failures/errors/skips. The original ZIP2246members/readset2232hashes/2220APPenvelope rows are retained with exactJUnit multiset/seal and original Judged/Located shared grade.

MAIN closes exactly one scoped child, VB-HG5-TAP-WRITE, after independently accepting the completed APP main FF. VB-HG5-TAP-READ remains open for strict source reader/projection controls; owner-controlled runtime/H3 gates remain open.

- [x] **VB-M12H-CI-CAPTURE — prospectively capture the original eight M-12h source controls before the first ROOT push event.** Bind Research daa1855aee005c0da53398ea2a102a3436b2fb6a, private unexecuted ROOT recipe predecessor d5d7448ac723e65cd5d65fe949dad00a28c40979 and its later reviewed successor, carrier4c0c653baf1654c8c25c66433cf39c8faefd8e52, six locked packages, exact eight parent identities/argv/UTC/native JUnit/log/readset and native receipt. Existing ci-fixture-conformance verifier projection/shared grade only. Publish this named enrollment before the original event. The final recipe must separately check out the exact published enrollment commit and capture this task and source-table bytes in the native readset; it must not claim the future enrollment commit is an ancestor of the private predecessor. Missing collection remains original NULL, failed controls remain FALSE; never synthesize cases, retry old events, or infer semantic alignment or improved temporal quality. M-12h remains open until MAIN accepts source/native evidence and its canonical boundary. No historical backfill or model calls. Owner: Codex NI08 source worker; MAIN applies/reviews.

2026-10-08 RTG-48 A-3/A-5: MAIN accepted overlapping control-point taxonomy and all eight correction rulings with historical-source limits. [Exact ungraded dependencies](../../artifacts/ni08/rtg48-a3-a5-source-review-20261008/README.md) extend the same VB-RTG48-DOC-DEPS custody family; no additional custody task, source ladder or read-time tuple is invented.

2026-10-08 RTG-48 A-4/A-6: [Exact ordinary source dependencies](../../artifacts/ni08/rtg48-a4-a6-source-review-20261008/README.md) extend the same VB-RTG48-DOC-DEPS custody family. MAIN accepted qualitative mechanism costs/deletions and the architecture recommendation; no new source ladder or extra custody-task completion.

2026-10-08 VB-RTG48-DOC-DEPS accepted dependency extension: [A7–A9 original-source and approved comment-operation custody](../../artifacts/ni08/rtg48-a7-a9-source-review-20261008/README.md) joins the existing A2/A3/A4/A5/A6 document family. Original23 source hashes describe pre-edit11f; post-edit comment hashes and lossless receipt/diff bytes are distinct. These are ungraded documentation dependencies, not authenticated runtime events, human actors, population rates or reconstructed ClaimTuples. Three original RTG audit tasks close; no extra custody checkbox or completion is created.

### MAIN source integration boundary — 2026-10-08

[Original source and native acceptances](../../artifacts/ni08/sc54-mf-m12h-source-integration-20261008/README.md) close five existing source/capture children. SC54 original102/102 covers prospective writer/strict reader and unchanged whole-ingestion controls; original97/102,101/102,101/102 failures remain immutable. MF original4/4 and APPmaina4cc establish default-off scalar instrumentation only. M12h original8/8 and Researchmain daa preserve deterministic match evidence on the judge path; no actual LLM judge was invoked. Twenty-eight exact ROOT Git blobs are integrated, with existing shared ladders intact. Owner-controlled quality measurements, runtime provenance, MF rate parents and HG5 version2 controls remain open.

- [x] **VB-EVL49-S04-V10-DRY-PLAN — capture the actual three model-free E5 planning controls prospectively.** Bind the reviewed Research runbook/source3907 successor, complete six-source import closure, all31 W1/W2/W4 manifests (11/8/12), external prompt input, actual interpreter/dependencies, wrapper/case identities and existing native carrier before invocation. Use exclusive source-owned outputs and record original argv/exit/stdout/stderr/JUnit/native receipt/readset and unchanged shared grading. The actual harness must retain its default dry branch and produce non-decision-grade manifests; never pass --execute or --i-have-operator-grant, invoke affinity preflight, launch a server, read model weights or infer current host quiet. Failed or missing collection remains original FALSE/NULL; no historical repair or new grading rule. This verifies plan execution only; actual benchmark admission, quality evidence and live-host readiness remain separate owner/operator gates. ✅ 2026-10-08

- [x] **VB-TULVING-SRS-WORKFLOW-CI — capture the original whole-module SRS comparison controls.** ✅ 2026-10-08; [MAIN original 32/32 and source publication](../../artifacts/ni08/tulving-srs-workflow-controls-20261008/README.md). Enroll the reviewed Research scorer/comparison implementation and all 32 prospective controls, including the existing ROOT sidecar fixtures, before the first source-push event. Preserve complete source/import/wheel/environment/readset custody, original JUnit identity multiset, argv/stdout/stderr/exit and unchanged CI carrier/shared grade. Failed or absent collection remains original FALSE/NULL. This validates source behavior; no metric/ladder change, historical score warrant, inference, protocol ratification or tuple backfill.

**VB-EVL49-S04-V10-DRY-PLAN complete, 2026-10-08:** [MAIN original capture review](../../artifacts/ni08/evl49-m12j-source-closure-20261008/README.md). V5 original three controls pass with all 16 generated outputs, including raw harness streams and exits; 77 carrier readset hashes and 75 unchanged pre/post input paths verified. Existing shared grader only, Judged/Located, non-decision-grade. Earlier NULL/TRUE events retain their original identities. This closes capture, not benchmark admission or live-host readiness. ✅ 2026-10-08

- [ ] **VB-M12I-REPLAY-CUSTODY — preserve one newly executed historical Tulving offline replay without projecting quality claims.** Enroll this task and the existing `tulving_episodic` source-row note before replay. Bind the actual owned five-wheel environment, original native/stdlib/source/raw/gold closure, exclusive output custody, original argv/status/stdout/stderr/UTC, and source/readset hashes before scorer invocation. Execute exactly one model-free replay over the frozen June responses, with no `--belief-measurements`, `--arm`, or `--run-id`. Compare named deterministic report components while preserving both original reports; then call the existing `tulving_episodic.rows_for_run` reader on the original and replay directories. Both missing-sidecar paths must return zero rows. If an unexpected sidecar exists, refuse and preserve it; never repair/delete it or call the writer/projector. No inferred arm, new inference run, quality tuple, backfill, new source class/ladder, grade or protocol ratification. A replay failure remains original and is not retried. Close only after MAIN accepts the exact source enrollment publication and one original replay custody record.


- [x] **VB-PROPOSAL-FIXTURE-CAPTURE — wire future copied-proposal CI fixture custody through the existing CI class.** Before any future result-bearing copied-proposal fixture event, bind original source-authored request/case scope, copied candidate source and dependency hashes, runner/runtime/argv/UTC/status/raw outputs/JUnit/generated artifact custody using the existing native_conformance carrier and strict ci-fixture-conformance reader/shared ladder. Reuse the accepted M12g/4c0 wrapper machinery where bounded. Verify projection/refusal from newly authored captures only; no new source class, grading rule, metric or SC67 quality admission. Preserve existing ordinary M12f63/AUD10 26 original records permanently without resealing/backfilled tuple. ✅ 2026-10-21 — Original source event 2026-10-08; MAIN acceptance retained. Original proposal captures at 9ed97e6e, hosted63/26; [original custody](../../artifacts/ci/proposal-native-fixtures-20261008/README.md).

- [x] **VB-EVL49-S05-CORRECTED-ROSTER-CAPTURE — prospectively capture corrected33 roster source and model-free dry planning successor.** Bind the opt-in roster leaf, pinned Research generator/runbook/unchanged harness plus actual complete import/input/environment readset, frozen33 generated manifests and roster index, synthetic exact-topology/refusal controls and W1/W4 unchanged-harness dry plans. Use a fresh original branch-push event and preserve original native/JUnit/raw argv/status/generated-output bytes through existing ci-fixture-conformance producer/adapter/shared grade; retain FALSE/NULL originals. Existing S04 v5 three controls/16 outputs/77 readset entries remain historical originals. No owner observations, model/server, quality/performance/live readiness, rerun/reseal/backfill or new class/ladder. MAIN owns publication and acceptance after exact source review; actual owner-window capture remains a separate S05 clause. ✅ 2026-10-21 — Original source event 2026-10-08; MAIN acceptance retained. Original S05 push8168cb17 outer1/1;33 manifests/two dry plans/48outputs/2764inputs; [original custody](../../artifacts/ci/evl49-s05-native-source-20261008/README.md).

- [x] **VB-DS41-1017-WIRE — capture the DS41-1017 validation measurements at write time.** Source: INF-77 DS41-W5/W6 (`deepseek-v41-flash-evaluation.md` section W). The 1017 MXFP4-experts build is served directly (operator 2026-10-20). Capture the load check, ppl, coherence, NMSE spot checks, serving speed vs the Sept Q4 headline, and the converted-drafter alpha. Each record binds the 9 shard sha256s and the drafter digest. Project through the existing VB-DSV41 measurement carrier; no new grading rule. Must land before the W5 runs. ✅ 2026-10-21: producer `epyc-inference-research/scripts/benchmark/ds41_1017_capture.py`, reader `scripts/vidya/adapters/ds41_1017_validation.py` (source `ds41-1017-validation`, test `tests/vidya/test_ds41_1017_validation_adapter.py`). The W6 alpha rows use the same producer and must bind the drafter digest.
- [x] **VB-DS41-1017-AKSCOPE — finish AK-planner visibility for DS41-1017 validation and ABA evidence.** The source adapter emits explicit applicability for the exact validated CPU artifacts; `loop_beliefs.collect()` prefers it over legacy `SOURCE_SCOPES`. The five original W5 native rows were ingested separately and remain `Judged/Located` observations without protocol warrant. ✅ 2026-10-24: historical ABA commit `da71fa603084b5f293dec6d7e9f15242129b034a` contains no native ABA `bench`/`served` capture; the commit covers 49 files total (48 ABA files plus `SUMMARY.md`), whose served outputs, logs and harness inputs cannot warrant retrospective tuples. Preserve only the original five native rows. Exact source pins, retained fields, missing write-side warrant and safe applicability are documented in [the historical ABA source audit](../../docs/reference/ds41-1017-aba-native-source-audit-2026-10-24.md). No new source class, ladder, grade or quant claim.
  - [x] **VB-DS41-1017-AKSCOPE.SRC — correct the producer-authored validation scope for the exact CPU artifacts.** ✅ 2026-10-24 (Codex source child). ROOT's `loop_beliefs.collect()` consumes explicit source `applicability`; the `SOURCE_SCOPES` table is only the fallback for legacy rows. The DS41 adapter now binds the exact producer-verified model path and CPU backend and omits `quant`, which the native producer does not census. Adapter validation pins both arm identities and rejects path aliases. The 1017 W5a native tensor manifest counts Q8_0=321 and MXFP4=120; the Sept-Q4 file is absent, so no quant was inferred for it. Actual adapter projection and reader matching tests pass (10 total): exact CPU model accepted, model/backend mismatch not target evidence, explicit quant mismatch still refused. No new source class, ladder, grader, or source-table row. At source-child close, before canonical ingestion, the ledger had zero `ds41-1017-validation` frames; the later ingestion is recorded in the sibling child below. The parent closed 2026-10-24 after the separate historical ABA source/applicability audit; no ABA tuple was manufactured.
  - [x] **VB-DS41-1017-AKSCOPE.NATIVE-INGEST — ingest the original five W5 native rows through the integrated adapter and verify idempotency.** ✅ 2026-10-24 (calendar-granted q1 correctness window, 13:07–13:17Z; job rc 0 at 13:08:13Z). Source sidecar `/workspace/repos/epyc-inference-research/data/ds41-1017-w5-20261021/belief_measurements.jsonl`, SHA-256 `483b67f595467877f1b12c241f266677666b4cd5e7b3d71d76165e8661cacbc0`; strict preflight matched/projected one unit and five native rows (15 frames; 0 refused, missing, or declined) after verifying all five IDs/digests and scored artifacts. Canonical `--only-new` append at 13:08:04Z emitted 15 frames; repeat dry-run emitted 0 and skipped all 15. The 15 appended frames occupy ledger seq 37956–37970 (three frames per native row); all five tuples grade `Judged/Located`, with no protocol citation, so these are observations and cannot gate decisions. No retrospective ABA rows, new grading rule, or claim about the missing Sept-Q4 quant. Parent closed 2026-10-24 after the historical ABA source/applicability audit; this child retains only the five original native W5 rows.
- [ ] **VB-DS41-1017-W62-WIRE — ingest the DS41-W5a/W5b/W6.2 slot rows (extends VB-DS41-1017-WIRE).** Source: the 2026-10-22 night slot driver `/mnt/raid0/llm/tmp/ds41-w5ab-w62-20261021/driver2.sh` (research `73aab47cc`, `d0b392982`, `c036eaa40`). Write side is built: `artifacts/ds41_w6_dspark_1017_20261021/w6.2/analyze_post.py` calls the pinned producer `ds41_1017_capture.py` for gate `nmse` (CPU_REPACK MXFP4 kernel vs f32 ref; weight NMSE vs the HF source, measured in the claim), `coherence` (W5b EOS probe count) and `alpha` (W6.2 per-block, per-drafter, both drafter digests bound); mock rows pass the producer validator. Remaining: after `analyze_post.py --commit --push`, sync the research clone and run `cli.py ingest ds41-1017-validation --path <research>/data/ds41-1017-w5-20261021` and `--path <research>/artifacts/ds41_w6_dspark_1017_20261021/w6.2` (today's ingest from `/workspace/repos/epyc-inference-research` fails because the shared clone does not yet carry the producer file). No new grading rule; OBSERVATIONS. Owner: the session that runs the post-run analysis. (filed 2026-10-21)
- [ ] **VB-DS41-1017-QUEUE-WIRE — write-side capture for the queued DS41-1017 runners before they run.** The 2026-10-21 queue rows `ds41-c72` (C7.2 top-k/indexer share), `ds41-w61` (W6.1 card-sampling alpha), `ds41-t33c`, `ds41-conf1` (CONF.1 confidence AUC/ECE), `ds41-w51a-ab` (W5.1a FP8-QDQ KLD A/B), `ds41-t32-kvfq` (T3.2 KV fake-quant port sensitivity) and `ds41-t71a-drafter-timing` produce measurements with no adapter row yet. Extend the VB-DSV41 source row and project each through the existing measurement carrier (bind the 9 shard sha256s + build sha); no new grading rule. Land before the first grant (earliest 2026-10-22 18:00Z). (filed 2026-10-21)
- [ ] **VB-Q38FN-SERVED-SWEEP-WIRE — wire the manual served thread x depth sweep records as a belief-kernel source.** Source: `epyc-inference-research/data/q38fn-threads-depth-20261020/results.jsonl` and `followup_128k.jsonl` (one JSON object per request with arm/t/tb/depth/prompt_tps|pred_tps/draft counts/content_sha), plus `SUMMARY.md`. Project through the existing `measurement` ladder only (`claim_tuple.grade()`); no new grading rule, and no retrospective tuple where protocol/attestation is missing.
- [x] **VB-AKX-ALL-26-CELLS-WIRE — wire the AKX-ALL-26 width-invariance cell records as a candidate measurement source.** Source: `epyc-inference-research/artifacts/akx_all_26_cpu_20261020/cells.jsonl.gz` (CPU half, research `f1bf316a7`; the HIP half lands from the GPU-queue agent) with `group_headers.jsonl` (env/nth/CPU-flag echo) and the frozen predicted-fail list hashes. Project through the existing `measurement` ladder only (`claim_tuple.grade()`); claim scope = op/type/shape/route/ids-mode/nth at the champion tip build; a cell counts only with its 3-rep A/A digests and config echo, and control and UNSUPPORTED cells stay rows. No retrospective tuple. Surfaced at the time of measurement per CLAUDE.md; owner: AKX-ALL-27 consumes the table. **HIP half ✅ 2026-10-22** (AKX-ALL-27 `width_dimension.json` wired as `ak-width-dimension`; strict re-derivation from the parent/keep HIP cell tables). **CPU half ✅ 2026-10-22** (`autokernel_width_cells_cpu.py`, source `ak-width-cells-cpu`; strict re-derivation of every cell verdict, A/A flag, control pattern, summary count and the frozen addendum hash; ingested live: 10 count tuples, all Judged/Located, `--only-new` re-run adds 0). Both halves wired.
- [x] **VB-CH19-T3-SCREEN-WIRE — wire the CH-19.2 T3 fused MoE up+gate speed-screen records as a candidate measurement source before the screen runs.** Source: `/mnt/raid0/llm/tmp/intake-fixes-20261020/t3-ch19-screen/<UTC>/records.jsonl` (written by `/mnt/raid0/llm/tmp/cpu-queue-f8/timing/t3-ch19-screen.sh`; one row per llama-bench result per arm with pair, switch state, fused-marker presence, valid/why, wrapper rc, binary and libggml-cpu sha256, build commit, samples_ts) plus `provenance.json` and the per-arm bench_canonical placement proof. Project through the existing `measurement` ladder only (`claim_tuple.grade()`); claim scope = Qwen3.6-35B-A3B-MTP-Q8_0 under the canonical recipe, pp512/tg128 at d0 and d8192, same-window ABAB, carrying the same-window noise floor; INVALID arms stay rows. No new grading rule, no retrospective tuple. Surfaced at the time the producer was written per CLAUDE.md; owner: the CH-19 session (`autokernel-champion-aggregate.md` CH-19.2). The screen ran 2026-10-21 19:10-19:16Z (0 invalid arms); `records.jsonl` now exists at `/mnt/raid0/llm/tmp/intake-fixes-20261020/t3-ch19-screen/20261021T191000Z/`, so the wiring can be written against real records.
  - ✅ 2026-10-24 (workspace-f8 vidya batch). `scripts/vidya/adapters/ch19_t3_screen.py` (`cli.py ingest ch19-t3-screen`), tests `tests/vidya/test_ch19_t3_screen.py`. Strict: avg/stddev from `samples_ns`, valid/why from the script's own rule, bench.jsonl vs records, placement proof (rc 0, max node share <= 40%), binary/libggml digests vs provenance, ABAB order, canonical recipe argv/env, every line of `summary.txt`/`end.txt` re-rendered; producer pinned `f44f12ad...`; llama-bench hardened rule via `_llama_bench_protocol` (all rows ordinary). Noise floor: no A/A arm, so `noise_floor_rel` = largest adjacent OFF/OFF deviation (needs >= 3 valid OFF processes, else absent with the reason), 1.4-5.2%; ON/OFF ratios 0.985 / 0.996 / 0.990 / 0.976, none clears its floor, no keep verdict derived. `preflight-on` (rc 1, lost placement proof) stays a valueless INVALID row. INGESTED 2026-10-24: 13 rows, 39 frames, Judged/Located.
- [ ] **VB-DS41-1017-BASELINE-WIRE — wire the DS41-1017 target-only baseline (A/A floor and champion-vs-C compare) as a candidate measurement source BEFORE it runs (tomorrow 06:30Z).** Source: `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/` (`aa/floor-store/*.json`, `cmp/compare-1017.json`, `aa/launches-calibrate.jsonl`, `cmp/launches-compare.jsonl`, `RUN_RECORD.json`, `PREDECLARED.md`, `model_identity_1017.json`, `README.txt`). Project through the existing `measurement` ladder only (`claim_tuple.grade()`); claim scope = recipe `ds41-1017-mxfp4-cpu-t48-targetonly`, request digest `e50732d9...`, split-model digest `ba9f129c...`, build execution digests, process unit, N_AA=24 / N_CMP=5 as predeclared; the floor row carries `content_sha256`, the instrument's own `serving_beliefs` capture is the native write side; invalid arms stay rows; the floor must not be compared with the Sept Q4+DSpark floors. No new grading rule, no retrospective tuple. Surfaced at the time the producer was built per CLAUDE.md (2026-10-21, runner for coordinator 3c4ca599); owner: the DS41-W5 / AK session that reads the floor.
  - *(2026-10-22, f8; box stays open.)* The producer has now run: floor 2.862% sealed 08:36Z (floor file + `FLOOR_SENSITIVITY.md`, `HOST_ACTIVITY_DISCLOSURES.md` beside it); the compare is still running. The write side must carry the floor's annotation verbatim (cold-start launch 1 = 10.67 tok/s, floor without it 2.445%, launch 39 inside a disclosed-activity window, post-hoc exclusion forbidden by PREDECLARED) and the epoch limit (build `dd3d9721c`, pre-W5.1a), as qualifiers on the row, never as a re-graded floor.
- [x] **VB-Q38-T10-1-GATE-WIRE — wire the Q38-T10.1 serving-gate per-prompt records (GPU phase run 2026-10-21, CPU phase owed) as a candidate measurement source.** Source: `artifacts/gpu-queue-20261020/q38-t10-1/serving-gate/gpu-run-20261021T092041Z/` (`*.records.jsonl`, `per_prompt.tsv`, `summary.json`, `config_echo.gpu.json`, `phase.gpu.json`) and the CPU-phase run dir when it exists. Project through the existing `measurement` ladder only; claim scope = corpus sha `224e7d92...`, role/model/build/argv from the config echo, predeclared rule sha `350a2a20...ffb3`, A/A 80/80 as validity precondition; truncated prompts stay listed rows. No new grading rule, no retrospective tuple. Surfaced at the time of measurement per CLAUDE.md; owner: the Q38-T10.1 task owner. ✅ 2026-10-24
  - 2026-10-21 (wrapup2-3c4ca599) update: the CPU phase finished 14:10Z (`SGCPU_DONE`) and the gate was ticked PASS under the predeclared Net-paired rule (R=0, G=0, p=1.0, both phases, 160 pairs), so the CPU-phase run dir now exists and the row must carry both phases. Still no writer call; box stays open.
  - *(2026-10-24, 3c4ca599 subagent; landed by integrator)* Wired `q38_serving_gate.py` (`q38-serving-gate`): 5 re-derived rows per phase run (R, G, exact one-sided p, token-identical fraction, pass/fail concordance); writer emits nothing unless rule sha (350a2a20..ffb3), corpus sha, A/A fully identical, phase COMPLETE and guards hold; truncated prompts stay listed. Real GPU run dry-runs to 5 rows / 15 frames. CPU phase uses the same path (synthetic fixture tested). Real: `python3 scripts/vidya/adapters/q38_serving_gate.py write --run-dir /workspace/artifacts/gpu-queue-20261020/q38-t10-1/serving-gate/gpu-run-20261021T092041Z --out-dir <dir>` then `cd scripts/vidya && python3 cli.py ingest q38-serving-gate --path <dir> --as-of <ts> --only-new`. CPU phase still owes its own run + write.
- [x] **VB-TOC-AB-WRITE — wire the tool-output-compression A/B and trajectory-artifact events as a candidate measurement source before the first compression A/B run.** The trajectory-artifact writer (TOC-SP-6 schema) writes, at its native finalize boundary, a self-hashed per-run sidecar carrying arm identity (policy digest, trigger fraction, window denominator), terminal_state, rolling input tokens, turns, prefix-cache invalidations, compressor wall time and per-task outcome; the strict reader reopens the hashes and projects authored fields to the existing measurement ClaimTuple and lets `claim_tuple.grade()` decide. No retrospective tuple, no new ladder; the adapter-table row is added in the same change. Surfaced now per the CLAUDE.md Belief Kernel rule; owner: the TOC A/B session. ✅ 2026-10-22
  - 2026-10-21 EXECUTOR NOTE (noninf-vidya; box NOT ticked). Carrier `adapters/toc_ab.py` + `cli.py ingest toc-ab`, written against the FILED TOC-SP-6/A-B-COST/A-B-TRIG event fields, not against the unmerged orchestrator writer (`noninf-toc` is editing it). Adapter-table row added. NOT done: the trajectory-artifact writer must call `toc_ab.write_belief_measurements` at finalize.
  - 2026-10-22 (rte-toc-writers) DONE. Writer call site wired: `epyc-orchestrator/scripts/benchmark/toc_ab_sidecar.py` (orchestrator `e9cf0949`) builds arms from the trajectory artifacts plus GRADED outcomes (`--outcomes`; `--outcome-from-finish` is plumbing only), concatenates the per-task files into one run trajectory and calls `adapters.toc_ab.write_belief_measurements` (root located by `--epyc-root`, same pattern as `l2_scan.py --belief-sidecar`). Refuses a missing artifact, a missing graded outcome, or partial token observation (no partial sums). `tests/unit/test_trajectory_artifact.py::test_sidecar_roundtrips_through_strict_reader_and_projects` writes a sidecar, reopens it with `toc_ab.native_rows` and projects each row through `toc_ab.project` (ran, not skipped). Note: the sidecar is emitted by the run's finalize step (the CLI), not per task; the first real emission waits on the first compression A/B run.
- [x] **VB-SKILLBANK-AB-WRITE — wire the M-23 SkillBank A/B per-cell readout as a candidate measurement source before its first arm runs.** One native record per role plus model-pin cell with skill-on and skill-off scored and attempted counts, the bootstrap CI, adoption and the detector digest; negative cells stay rows; the strict reader projects one tuple per cell and lets `claim_tuple.grade()` decide; a pooled mean is not emitted. No retrospective tuple, no new ladder; the adapter-table row is added in the same change. Owner: the M-23 session. ✅ 2026-10-21
  - 2026-10-21 EXECUTOR NOTE (noninf-vidya; box NOT ticked). Carrier `adapters/skillbank_ab.py` + `cli.py ingest skillbank-ab`; per-cell rows, negative cells kept, pooled cell refused, per-protocol and ITT deltas re-derived. Adapter-table row added. NOT done: the M-23 runner does not exist yet, so no producer call.
- [x] **VB-M26-DISTILL-POOL-WRITE — write and verify selected-memory integrity before teacher execution.** In `StructuralLab.distill_skillbank`, write one immutable receipt after retrieval and before the teacher call. Capture invocation/time, exact returned IDs and native metadata (`action_type`, `q_value`, `outcome`, `model_id`, captured tier endpoints with missing values preserved as null), selector/backend/query/filter details, source-store identity/path, orchestrator HEAD plus dirty status, source-file digests and loaded-function fingerprints, requested teacher pin and teacher object's declared model ID (served identity only when independently observed), and a canonical digest of selected metadata. Record descriptive totals/groups plus the native decided proposition, Boolean and errors: the returned rows must meet recorded top-k/Q filters; their IDs/groups and M-25 outcome counts must recompute from captured rows; and projected escalation marker IDs must match rows whose native action_type is escalation. Persist false verdicts and prevent a real teacher call when integrity fails. The store query is two-phase/top-k; receipt binds returned metadata and does not assert atomic snapshot or whole-store completeness. Historical rows may be used as input to a new invocation, but old invocations are never reconstructed/backfilled; mock/synthetic receipts never enter ingestion. Counts are descriptive, with no metric direction or skill-quality claim. The strict reader refuses missing/altered provenance and projects the native Boolean as integer 0/1 under unit `false_0_true_1`; the exact Boolean remains in the receipt and `extra.native_verdict`. The result-specific proposition and existing verifier `ClaimTuple`/`claim_tuple.grade()` path remain authoritative; no new grade, source class or ladder. Keep M-25 report keys qualified as `episodic_memory_pattern`, not full task traces. Source enrollment is recorded in `scripts/vidya/adapters/README.md`. Published ROOT source commit `0d9b34e152c9f1b5960960377b69e27ead1ddb61` (main promotion `2387f65d75289471b112e992575164efddeff2ea`) and orchestrator source commit `71210d1f2fc854b52f52e202bf3ed1a267a02980` (main promotion `2cefc241152b36f125e76bacb38b4fe9e1b016cf`). Tested pins were ROOT `90482f6beb0a78de745e074ffb93023ea3a503a3` and orchestrator `ae32f964c09113d6a0d262ae4bd8c277faf1adb1`. Acceptance: producer write and strict root reader plus focused tests demonstrate the pre-teacher capture and rejection contract without running a teacher. Owner: M-26 source-fix session. ✅ 2026-10-24.
- [x] **VB-HIL-WRITE-FIELDS — add the HIL-2 item 14 pins to the VB-HIL-WRITE carrier.** The sidecar also binds the tool-surface digest (tool names and schemas), the served context window, the compaction-policy digest, the wall-time and turn budget and the final-result selection rule; these are write-side fields that cannot be recovered on read, so they land before the first HIL efficacy run (`intake-2154#00`, `intake-2007#04`). Check first whether the SC86 `opencode_shell_run` capture already records the tool-surface digest and reuse it rather than duplicating it. ✅ 2026-10-21
  - 2026-10-21 EXECUTOR NOTE (noninf-vidya; box NOT ticked). Check result: SC86 `RUN_SIDECAR_FIELDS` (`opencode_shell_run_capture.py`) records NO tool-surface digest, and no VB-HIL-WRITE carrier existed in the tree, so `adapters/harness_improvement.py` was built with the item 14 pins required (`ARM_PIN_FIELDS`, shared `arm_pin_problems`) + `cli.py ingest harness-improvement`. The base VB-HIL-WRITE row (line ~2814) is therefore also partly satisfied by this carrier; its producer hook and first-run check remain owed, and main should decide whether to tick/retarget it. SC86 was not modified (closed field set).
- [x] **VB-HIL17-WRITE — write side for the HIL-17 attribution-ladder tables, before the first HIL-17a/17b window run.** Filed 2026-10-22 (a1-orch-code, 3c4ca599) per the belief-kernel wiring rule: orchestrator `scripts/trace/attribution_ladder.py` (`src/trace/attribution/report.py`, orchestrator `40560f2f`) will produce per-rung accuracy/token tables and aggregated nDCG@5 vs the random and temperature-0 arms. Producer: an immutable self-hashed sidecar at the driver's finalize, one row per run x rung (and per aggregate arm) x metric, binding the slice manifest sha256, judge families (model + quant + port role, `quantised` flag), k, temperature, policy (`calibrate`/`escalate`), `--with-reference` setting, scored/abstained/attempted denominators and the raw results digest; a `mock: true` dry run is refused. Adapter: project into the existing `measurement` ClaimTuple, `claim_tuple.grade()` decides; no new ladder or grading rule; add the source-table row in `scripts/vidya/adapters/README.md`. ✅ 2026-10-22 write side landed in root `scripts/vidya/adapters/hil17_attribution.py` (source `hil17-attribution-ladder`, tests `tests/vidya/test_hil17_attribution.py`); the orchestrator driver emits it through opt-in `--belief-out`. Empty protocol_id, mock/unlabelled/undigested reports refused. README row added.
- [x] **VB-HILLB1-WRITE — write side for the HIL-LB1 loop-detector scores (`scripts/trace/hil_lb1_loop_score.py`, orchestrator `258ce2d7`) before any re-score is filed.** Filed 2026-10-22 (a1-orch-code, 3c4ca599). Producer sidecar: one row per detector x population x metric (precision, recall, F1, FP rate), binding the labelled-set digest (Who&When Pro text split sha256, label = mode A.4), the tokenizer sha256, the detector profile parameters, the exemption on/off setting, TP/FP/FN/TN denominators and the results digest; unlabelled firing counts (tap replies, coding sessions) are observations, never accuracy. Project into the existing `measurement` ClaimTuple; `claim_tuple.grade()` decides; add the README source-table row. ✅ 2026-10-22 write side landed in root `scripts/vidya/adapters/hil_lb1_loop_score.py` (source `hil-lb1-loop-score`, tests `tests/vidya/test_hil_lb1_loop_score.py`); the orchestrator scorer emits it through opt-in `--belief-out`. Empty protocol_id; rates re-derived from counts; labelled-set digest and code ref recorded or listed as absent. README row added.
- [x] **VB-GPU-CPU-NOISE-WIRE — wire the GPU -> CPU timing contamination experiment (U4-NOISE-1) as a candidate measurement source before it runs.** ✅ 2026-10-23
  - **Sources:** `/mnt/raid0/llm/tmp/gpu-cpu-noise-20261021/runs/<session>/`, written by research `b65284539` `scripts/benchmark/gpu_cpu_noise/gpu_cpu_noise_driver.py`:
    - `reps.jsonl`: schema `epyc.gpu_cpu_noise.rep.v1`, self-hashed `content_sha256`, one row per llama-bench rep;
    - `RUN_RECORD.json`: prereg sha256, code HEAD, binary sha256, host state;
    - `schedule.json`, plus its sha256;
    - `ANALYSIS.json`: the pre-registered estimators and the decision table.
  - **Projection:** through the existing `measurement` ladder only (`claim_tuple.grade()`). One tuple per (condition, metric, quantity):
    - quantities: bias %, process-unit VR, arm-unit VR, sigma_add %;
    - claim scope: W1 = bench_canonical Qwen3.6-35B-A3B-MTP-Q8_0 pp512/tg128 on the v10 store binary, GPU champion `dd3d9721c` 27B Q8+DFlash2, `instrument_class=bench`, the floor unit on every tuple, the prereg sha256 as the protocol reference;
    - invalid reps stay rows (with `why_invalid`).
  - **Transfer caveat:** a bench-class contamination estimate is NOT a serving speed number (INSTRUMENT-CLASS-1).
  - No new grading rule, no retrospective tuple. Surfaced when the producer was built, per CLAUDE.md. Owner: the U4-NOISE-1 runner.
  - *(2026-10-22, workspace-58 wrap-up; box stays open.)* The experiment RAN before the adapter was built: session `20261022T170902Z` (10 blocks, 329 rows, `reps.jsonl` + `RUN_RECORD.json` + `ANALYSIS.json` present) and the aborted `20261022T164830Z` (0 blocks, END rc=5). The native write side carried every field the projection needs, so a tuple projected now reads the original records and is not retrospective. Remaining: the adapter plus its controls; tick when both sessions project (the aborted one as zero rows with its END reason).
  - ✅ 2026-10-23 (ws58 subagent): adapter `scripts/vidya/adapters/gpu_cpu_noise.py`, source `gpu-cpu-noise` (`cli.py ingest gpu-cpu-noise --as-of <ts> --only-new`; default path the `runs/` dir), root `ab82e317d` on branch `ws58/vb-noise-affinity-20261023`. Strict reader: prereg, `schedule.json` and every rep row re-hashed; every deterministic analyzer number (counts, valid fractions, pooled-median biases incl. A/A, paired blocks, process/arm VR, sigma_add, sd, df) re-derived from `reps.jsonl` and matched to 1e-9; CIs and verdicts carried verbatim. Empty `protocol_id` (prereg is harness-local, OCC-1 precedent), so all tuples are Judged/Located; the prereg sha256 rides in the claim text. Producer write side: research `5fe010c63` (branch `ws58/noise-analyzer-identity-20261023`) adds an `analyzer` block (analyzer sha256, seed, N_BOOT, reps.jsonl and RUN_RECORD sha256) to ANALYSIS.json, which the reader verifies when present. INGESTED into the canonical ledger at 2026-10-23T15:16:28Z with `--only-new`: 5 units, 2 projected (W1 `20261022T170902Z` 42 rows; W2-Q38FN `20261023T111836Z` 9 rows, no prefill arm-VR tuple because there is 1 sample per rep), 3 declined (aborted `20261022T164830Z`, END rc=5 `gpu-warmup-failed`; two dry runs), 0 refused, **51 rows, 153 frames**. A `--dry-run` re-run skips all 153. Tests: `tests/vidya/test_gpu_cpu_noise_adapter.py` (12).
- [x] **VB-LLAMA-BENCH-HARDEN-PROTOCOL — carry `autokernel_hardened` as a protocol field in every llama-bench adapter and refuse unrequested hardened rows.** Filed 2026-10-23 (workspace-f8). Defect: builds from `0492c2319` (2026-08-11) through the champion `49550eda5` leave llama-bench's `autokernel_harden` uninitialised, so about half of runs without `--autokernel-harden` emit `"autokernel_hardened": true` rows (fix V11-103 / CH-28; fleet audit LBH-1..3 in `autokernel-rebuild-program.md`). None of the four adapters that project llama-bench output reads the field today: `autokernel_aux_receipt.py` (`samples_ts`, metrics `t1b.llama_cpu.llama_bench_{decode,prefill}.v1`), `autokernel_governed_receipt.py` (`avg_ts`), `autokernel_gpu_screening.py` (`epyc.autokernel.native_llama_bench_metric.v1`), `inf70_roofline_ledger.py` (markdown logs; markdown has no hardened column, so its rows are request-unknown). Do: (1) project the row's `autokernel_hardened` into the tuple's protocol identity and the request (argv carries `--autokernel-harden`) beside it, write side first where the producer does not record argv; (2) refuse at projection, before grading, any row whose hardened flag differs from the request, and any hardened row with an unrecoverable request from a build in the defect window; (3) treat a missing key as unknown; (4) count refusals in each adapter's report; (5) one shared helper in the adapter layer, not four copies. Controls: a requested-hardened row grades as before; an unrequested-hardened row refuses; a request-unknown row from a V11-103 build grades; a request-unknown hardened row from `49550eda5` refuses. No new grading rule (projection precondition only; `claim_tuple.grade()` decides). README source-table row added 2026-10-23.
  - *(2026-10-23, workspace-f8, DONE pending landing; branch `f8/vb-llama-bench-harden`, commit `4a842465a`.)* Shared helper `scripts/vidya/adapters/_llama_bench_protocol.py` (`assess`, `LlamaBenchProtocolRefusal`, `RefusalTally`; mirrors research LBH-3 `5c3ad96c3`) called by `autokernel_gpu_screening`, `autokernel_aux_receipt` (GPU discovery runs and IQ2 invocations), `autokernel_governed_receipt` (direct-GPU launches) and `inf70_roofline_ledger`. The GPU producer already records `argv` and `raw_row` per run, so no write-side change was needed there; inf70 reads the request from the recorded command and its row state is `unknown` by construction. Protocol identity rides in `extra.llama_bench_protocol` (measurement ids unchanged). Refusals are `ProjectionError`s with a `llama_bench_protocol:<code>:` prefix and are counted by code in `ingest_corpus` (`llama_bench_protocol_refused`) and `ingest_sources.ingest`. Controls tested: requested-hardened accepts, unrequested-hardened refuses, request-unknown from a V11-103 build grades, request-unknown hardened from `49550eda5` refuses. `tests/vidya` 2669 passed. Owed (not blocking): `BenchRow.to_dict()` drops `autokernel_hardened_reported`, so an IQ2 row from a flag-less build reads `ordinary` rather than `unknown`; the fix touches sealed IQ2 row dicts and needs a replay-compat check (research, with LBH-3.1 owner). `FIXED_BUILD_PREFIXES` must gain each new champion/production build.
- [x] **VB-LAUNCH-AFFINITY-WIRE — project per-task launch-affinity readings into claim tuples.** Filed 2026-10-22 (workspace-58, STACKCHG-GPUPIN-20261022, `gpu-serving-tie-in-program.md` GPS-PIN-1). Write side: the serving_gate arm record (`affinity`, `affinity_escapes_at_stop`) and AK `residency.affinity` already carry pid, cpus, tasks_seen, repinned and escapes. Add the read timestamp and the binary identity at write time, then a ~40-line adapter projecting "N/N tasks inside <cpus> at <t> for <pid, binary, recipe>" for `claim_tuple.grade()`. A reading is per pid, per task and per moment (a clean read at health does not cover later threads); absence of the field means unchecked, never clean. No new grading rule. Source row: `scripts/vidya/adapters/README.md` "Launch-affinity per-task readings". After GPS-PIN-1 lands (the fields exist only on its branches until then). ✅ 2026-10-24 — adapter already on main (ab82e317d), orchestrator write side 26affbf8; confirmed by workspace-58 batch.
  - 2026-10-23 (ws58 subagent; box stays open for the AK half). Orchestrator write side: `e34eb5b4` (branch `ws58/launch-affinity-reading-20261023`) adds `affinity_reading()`, one self-hashed `epyc.launch_affinity.reading.v1` record per pid per moment (UTC read time, pid start time, exe realpath + sha256 via `/proc/<pid>/exe`, the ROCr knob from the process's own environ, every task's mask, escapes, PinResult). `launch_affinity.py --check/--repin ... --record FILE` appends one, and `serving_gate.py` appends `post_health_pin` + `pre_stop` readings to `<out>/affinity_readings.jsonl` (39 tests pass). Reader: root `scripts/vidya/adapters/launch_affinity.py`, source `launch-affinity` (`cli.py ingest launch-affinity --path <dir|file> --as-of <ts> --only-new`), root `ab82e317d`. It checks the closed field set, re-hashes, re-counts and re-derives escapes, and declines a reading with no readable task. The pre-hook diag dumps and the P1 probe are read as written (retrofit, placement and knob from the named launch script, read time from the dump mtime, no binary sha256). INGESTED at 2026-10-23T15:16:28Z: 3 units (two `diag-affinity-*.out` files, `probe-p1-gpupin-20261023/`), **4 rows, 12 frames**: diag 195/196 inside (1 ROCr thread on 0-191, BASELINE); diag + `taskset -a` 196/196; P1 knob-only 196/196 at health and after a completion (CANDIDATE). An idempotent re-run skips all 12. Tests: `tests/vidya/test_launch_affinity_adapter.py` (13). **Remaining (the open box):** AutoKernel `residency.affinity` (research `scripts/kernel_rnd/autokernel/loop/serving.py`, `loop/launch_affinity.py` twin) does not write the v1 record yet. Wiring it means adding the read time and exe sha256 to an AK serving record that strict AK adapters read with closed field sets, so it has to land together with those readers.
- [ ] **VB-AK-R18-INDEPENDENT-SYMBOL-FINDINGS** — enroll the eventual full R18-A independent CPU/HIP symbol comparison as a producer-authored source finding. Bind exact v10 comparator, source/compiler/build identities, CPU/HIP symbol-set artifacts and digests, output verdict, and complete/partial/failure/missing state. Reuse the existing AutoKernel ClaimTuple ladder (`Judged/Located` observation); no new grader or historical tuple. The current rank-23 READY is launcher qualification only: no full independent build or symbol comparison has run, and `PRODUCTION_RECIPE_IS_VERIFIABLE` remains false. Source row is filed above; planning-context canary is pending, so do not call wired.
- [ ] **VB-NEMO-C3-NATIVE-PROFILE-WIRE** — enroll and wire the prospective NEMO-native `c3.v1` source era through the existing NEMO-native ClaimTuple adapter and ladder; do not create a class or grader. Before consumption, implement a producer-authored record and strict reader binding final source/image/loaded DSO identities, build flags, exact L/B request and model identities, profiler/tool settings, in-request MI210 residency, raw traces and reader outputs. Retain failed, partial and missing feature-count states explicitly; no v10 backfill or zero-nonfinite inference from HTTP success. The source-table row is filed above. The immutable L prerequisite plus fresh R2 B/active-cutoff compatibility controls now pass; terminal drain and raw join are complete, but the B control was correctly refused for scoring and emitted zero ClaimTuples. Corrected READY is queued, not a completed profile. The R3 original B profile has since completed (see 2026-10-30 result below); the planning-context canary remains pending, and only passing it permits calling the loop wired. Existing NEMO-native ClaimTuple ladder remains the sole grader.
- [ ] **VB-NEMOTRON-BOLT-FOLD-WIRE — project the Nemotron 3.5 Bolt pending-fold records into ClaimTuples.** Sources: llama-bench markdown + `bench_load.txt` (pp512/tg128 on MI210 and CPU), `gpu_coh.json` (coherence, reasoning on/off, VRAM/KFD residency samples), `greedy_{ctl,cand}.json` (Qwen3.6 byte identity vs champion `dd3d9721c`), `tbo_*.log` (test-backend-ops counts), all under `/mnt/raid0/llm/tmp/nemotron-bolt-champion-20261021/` for build `59c1b915f`. Copy the cited files into a research artifact dir with SHA256SUMS first (scratch is not durable). Speed rows are indicative (shared GPU claim, host load ~98, no A/B, no floor) and must not grade as a gating measurement; identity/op-test rows are correctness evidence. Existing ladders only.
  - 2026-10-21 (wrapup2-3c4ca599) additional sources from the C2 re-gate (C2 = `49550eda5`, stores `kernels/builds/{cpu,gpu}-20261021-49550eda5-c-nemotron`): the Nemotron GPU leg (ROCm0 test-backend-ops on the Bolt ops plus coherence, 52-55 t/s, all ops pass) and the `nemotron_omni` mmproj smoke (PASS) under `/mnt/raid0/llm/tmp/c2-regate-20261021/`. Same indicative-only rule; copy into a research artifact dir with SHA256SUMS before wiring.
  - *(2026-10-24, 3c4ca599 subagent; landed by integrator)* Wired `nemotron_bolt_fold.py` (`nemotron-bolt-fold`): 30 observation rows (MI210 llama-bench + server-recipe speed as indicative with caveat and no floor/decisive field, coherence, residency, Qwen3.6 greedy identity 3/3 vs dd3d9721c, 22 test-backend-ops rows). Sources copied to research `artifacts/nemotron-bolt-champion-20261021/` with SHA256SUMS. Dry run 30 rows / 90 frames. Box stays OPEN (CPU speed leg unmet): no CPU pp512/tg128 llama-bench exists in the scratch record, so no CPU speed rows. Real: write the sidecar via the module's `write` command, then `cli.py ingest nemotron-bolt-fold --path <dir> --as-of <ts> --only-new`.
  - *(2026-10-24, 3c4ca599.)* The 30 MI210 rows were really ingested by main (`cli.py ingest nemotron-bolt-fold --only-new`, 30 rows / 90 frames, 0 refused). Box stays open: the CPU pp512/tg128 llama-bench leg has no source record.
- [x] **VB-CT18-SKILLINJECT-WRITE - wire the CT-18 Skill-Inject arm results as the third injection fixture set before the arms finish.** The adapter row for CT-18 names the IB2 and SP1 sets; the Skill-Inject arms (`/mnt/raid0/llm/tmp/ct18-run-20261021/RESULTS.skillinject.{architect,worker}.jsonl`, 317 items x 3 arms per role; architect 128/317 and worker 51/317 on 2026-10-21) are a third fixture set, and their runner (`ct18_resume.py`) does not call `write_belief_measurements`. Project through `injection_fixture.py` only, claim form `static-attack ASR on fixture set X [hash]` per arm and thinking setting on the named served pin; partial arms must not project as complete (record items completed). No new grading rule, no retrospective tuple. Surfaced 2026-10-21 by wrapup2-3c4ca599 per the CLAUDE.md Belief Kernel rule; owner: the CT-18 task owner (`qwen-chat-template-evaluation.md` CT-18.1). ✅ 2026-10-22
  - 2026-10-22 (ct18-final) WIRED retroactively by the CT-18 task owner at finalize, NOT a reader-side reconstruction: `injection_fixture.write_belief_measurements` called by `/mnt/raid0/llm/tmp/ct18-run-20261021/write_belief_si.py` on the complete RESULTS files, one run per served pin (a worker run mixing CPU and GPU kernels would break the one-pin-per-row contract): sidecars `.../belief/skillinject-{architect-gpu,worker-gpu,worker-cpu}/injection_fixture.beliefs.jsonl` (3 arms each: A BASELINE, B/C CANDIDATE; thinking=off; fixture set `skillinject-canary-v1`, fixture sha256 `c104a3d8c269...` = `skill_inject_pairs.json`; kernel_ref `gpu-20261020-dd3d9721c` / `cpu-20261020-dd3d9721c`). Complete triples only (architect 316, worker GPU 250, worker CPU 66; SI-C037 excluded from all arms). Verified: `validate_row` returns [] for all 9 rows, `rows_for_run` reads back attestation_present=True, `frames_for_sidecar` yields 9 frames per sidecar; values match the analysis (architect 62/50/58 of 316; worker GPU 62/80/59 of 250; worker CPU 20/21/15 of 66). Claim wording is the fixed form only. IB2 (`ib2-ct18-v1`) has no sidecar yet and was not written here (outside this task's text). Sidecars live in scratch; copy to a durable artifact dir with SHA256SUMS before anything gates on them.
- [x] **VB-EV19-GOLD-SELFCHECK-WIRE - wire the EV-19 scorer gold self-check and pool-swap gate as an instrument-validity source.** Producer: `src/autopilot_core/gold_self_check.py` / `scripts/autopilot/gold_self_check.py` (orchestrator), full-pool run `--max-per-suite 0` on pool `corpus-ev19b-20261021` (sha256 `73a2ed5a...`): 0 wrong, 0 scorer_error, per suite; era row E20-eval-corpus-ev19-quality ratified 2026-10-21 (orchestrator `04685908`). Claim is about the SCORER and POOL (wrong-on-own-gold fraction per suite, N and sample mode recorded), never about a model; a 300-row-per-suite sample missed a 22-row defect, so a sampled run must carry its sampling mode and cannot ground a pool-gate claim. Project through the existing `measurement` ladder, add the adapter-table row in the same change. Surfaced 2026-10-21 by wrapup2-3c4ca599; owner: the EV-19 task owner (`eval-tower-verification.md`). ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`. Producer call ✅ 2026-10-22 (orch main `b0cf16ba`): `gold_self_check.py --belief-out DIR --eval-era-row ROW` records `pool_sha256`/`pool_rows`/`generated_at` and calls the writer.
- [x] **VB-OOLONG-WIRE — wire the Oolong adapter records (OOL-1) as a candidate measurement source before the first Oolong run.** Source: the per-question JSONL written by `scripts/benchmark/oolong_adapter.py` (epyc-inference-research; fields `parse_confidence`, `score`, `failure_class`, `attempted`/`answered`/`no_answer`, `arm`, `labels_given`, `source_revision`, `context_window_id`, vendored scorer sha). Project through the existing `measurement` ladder only (`claim_tuple.grade()`); claim scope = model pin, context length, thinking arm, pinned dataset revisions; CIs are context-clustered; `labels_given: true` records are excluded from any gate and must not project as a gating tuple. No new grading rule, no retrospective tuple. Surfaced with the adapter per CLAUDE.md (2026-10-21, `rao-redel-substrate-spike.md` OOL-1); owner: the OOL-1 / YARN-AGG-1 session. The adapter-table row is added in the same change. ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`.

## Belief-kernel refocus on AutoKernel + autopilot — operator decision 2026-10-21

Operator decision: REFOCUS the belief kernel around AutoKernel and autopilot consumers rather than retire it (independent review: `/mnt/raid0/llm/tmp/belief-kernel-review-20261021/REPORT.md`, verdict RETIRE, overruled). Landed: one canonical ledger `/mnt/raid0/llm/state/vidya/ledger.jsonl` with flock-serialised writers and event-driven sync from origin/main (`da59bb4de`); correction backlog drained 905 -> 0 on the canonical ledger (worksheets and replay in `/mnt/raid0/llm/tmp/vidya-corrections-20261021/`); adapter fix plus 121 index blocks committed as `2c0c7334b` on branch `f8/vidya-correction-fix`, NOT pushed (operator decision pending). Consumer wiring in progress on `lane/belief-reader-20261021` (root) and `lane/ak-belief-reader-20261021` (research). KEY FINDING: the AutoKernel reader merged 2026-09-25 read the ledger 933 times and found nothing, because no stored measurement record targets the scope AutoKernel asks about. Wiring more producers into the same schema will not change that.

- [x] **VB-REFOCUS-SCOPE-REDESIGN — decide WHAT beliefs are stored: demand-driven loop-belief schema keyed by the scope AutoKernel/autopilot actually queries.** Operator is considering this redesign; it is the open decision that gates new producer wiring. Deliver a decision package (options: keep the measurement-record schema and add a scope index; demand-driven loop-belief records written by the loop itself; hybrid) with a recommendation, derived from the 933 empty reads (enumerate the query scopes from the reader logs first). Must not add a second grading ladder (`claim_tuple.grade()` stays the only grader). Decision part ✅ 2026-10-21: operator APPROVED the redesign; design `/mnt/raid0/llm/tmp/belief-redesign-20261021/DESIGN.md`; implementation tracked as P1-A..P1-H, Phase 2 and DP-1 below.
- [ ] **VB-REFOCUS-PUSH-CORRECTION-FIX — push `f8/vidya-correction-fix` (`2c0c7334b`: adapter fix + 121 intake index blocks) after the operator's go.** Blocked only on the operator decision named above; run `cite-check` on the merged tree before the push and confirm the canonical ledger pending-corrections count stays 0.
- [x] **VB-REFOCUS-AUTOPILOT-READER-LANDING — land the root reader and the autopilot consumer.** ✅ 2026-10-21 (orch 955b6f28; root reader `0ed65d1c5` already on main). Orchestrator `lane/belief-reader-20261021` merged: `scripts/autopilot/loop_beliefs_bridge.py` runs ROOT `loop_beliefs.py prepare` as a child before every planner turn (refuse blind planning; degraded mode runs only critic-approved preseeded items), `plan_with_providers` requires a sealed `ReadyBeliefs`, and a missing reader raises a critical alarm through `alarm_channel`. Post-review additions: reader path resolves `/workspace` first, then the epyc-root-main view (`/workspace` was 466 commits behind and lacked the reader); reader deadline 30 -> 120 s; belief text goes through the CT-12.3a neutraliser; targets derive from the live stack's compiled priors (`stack_priors`) plus explicit open-hypothesis models instead of `[]`; `vidya_planner_bridge` resolves its lookups the same way; the stale `FakeVerdict` double fixed (7 pre-existing failures gone). 1494 tests passed. Real-ledger smoke (no sync, scratch outputs): ready, 30813 frames, 4 derived targets, 12 usable claims with the CPU targets and 0 for Qwen3.8-27B/gpu. Spin-up costs: the first prepare of a cold turn takes 20-25 s, then about 1.6 s warm.
- [x] **VB-REFOCUS-CONSUMER-LANDING — land the AutoKernel consumer branch.** ✅ 2026-10-21 (research `b7b23fe1c`, push verified; the non-empty-read proof is split out below). Research `lane/ak-belief-reader-20261021` merged: before each plan AutoKernel runs ROOT `loop_beliefs.py prepare` as a child (self-heals a stale ledger, refuses blind planning, degraded mode runs only queued/preseeded work with the critic kept) and ingests the loop store's `serving-beliefs` A/B receipts through `--source-root`. Post-review additions: ROOT resolves `--belief-root-repo`, then `EPYC_ROOT_REPO`, then `/workspace` only if it has the reader, then the epyc-root-main view (`resolve_root_repo`, used by `run.py` and `serial_run.py`); reader deadline 30 -> 120 s (a prepare took 24-26 s with three source stores at host load ~600, and one timed out at 30 s on a healthy ledger); six test fixes after the rebase. Real-ledger smoke (copy of the canonical ledger, no sync needed, 30813 frames): ready, no alarm; 12 claims for the DS41 CPU targets (new 1017 MXFP4 recipe and Q4) and for Q38FN, 0 for Qwen3.8-27B/gpu. These are the same 12 device-scoped claims autopilot gets (see VB-LOOP-TEXT). Ledger sync status at the smoke: fresh, lag 0.
- [ ] **VB-REFOCUS-NONEMPTY-READ-PROOF — show one AutoKernel or autopilot decision whose input came from a ledger read that returned a record.** Count reads with a non-empty result, not total reads, and name the decision (receipt id from `belief-receipts.jsonl` / the autopilot bridge receipt, with the claim ids it relied on). Not satisfied by either smoke: both loops return the same 12 device-scoped claims regardless of model, which is VB-LOOP-TEXT; a decision that relies on those claims proves the plumbing, not that model-specific evidence reached the plan. Needs a live planner turn in each loop, so it follows the spin-ups.
- [ ] **VB-LOOP-TEXT — make the claim payload the planner receives say what the claim is about.** **Subsumed by the belief storage redesign (DESIGN.md §9); stays open until P1 acceptance (`p1_acceptance.py`) passes.** The autopilot smoke returned the same 12 claims for three different CPU models (Qwen3.6-35B-A3B-MTP-Q8_0, Qwen3-VL-30B-Q4_K_M, Qwen3.8-Flash-Next-UD-IQ4_XS), so they are scoped by device only (`epyc-9655`) and carry INF-70 roofline / serving-rate text with no model-specific content. Review what `loop_beliefs.render` puts in the section (claim text, scope line, source label), and decide whether device-only claims should count as usable evidence for a model target or be shown as a separate "device-scope" group. No new grading rule: `claim_tuple.grade()` stays the only grader. Filed from the autopilot reader smoke 2026-10-21; owner decision pending (coordinator referenced this id).
- [ ] **VB-AP-SPINUP-AP3-SCOPED — set `AUTOPILOT_AP3_ROLE_RESTART_ENABLE=scoped` in the autopilot spin-up environment (operator DP-4 = A, 2026-10-21).** Scope: `spec_draft` and `kv_profile` only, on `architect_critic`, `frontdoor` and `worker_general`; no other knob family or role may restart. Verify the process environment of the started autopilot (not the launcher script) shows the value before the first trial iteration.
  - *(2026-10-24, workspace-f8 vidya batch; box stays open.)* Prepared as code, not applied: orchestrator `f8/ap3-scoped-spinup-20261024` @ `9d20439d` pins `AUTOPILOT_AP3_ROLE_RESTART_ENABLE=scoped` in `start_authority_daemon.AUTHORITY_ENV` (an inherited `1` or empty value cannot change it) and adds the key to `autopilot._required_gate_env`, so a daemon whose live process env lacks it refuses to start before the first trial (168 + 49 tests pass). AutoPilot is not running (lock empty since 2026-08-08). Remaining, named events: the orchestrator owner merges the branch, then the spin-up; at that start read `/proc/<pid>/environ` of the started process for the value.
    - *(2026-10-24, workspace-f8 main; merge record.)* Orchestrator `f8/ap3-scoped-spinup-20261024` @ `9d20439d` MERGED to orch main as `a85973a9` (reviewed MERGE, LOW risk); the merge event above is done. Box stays open (b) on ONE named event: the next AutoPilot daemon start through `start_authority_daemon.py`, where `/proc/<pid>/environ` must show `AUTOPILOT_AP3_ROLE_RESTART_ENABLE=scoped`. AutoPilot is not running.
- [ ] **VB-AP-SPINUP-ORCH-CLONE — fast-forward the shared orchestrator clone (`/mnt/raid0/llm/epyc-orchestrator`) to origin/main immediately before the autopilot spin-up.** Autopilot runs from that clone, which sat at `65fbdce3` on 2026-10-21 while origin/main had the reader lane (`955b6f28`). Without it the first start runs pre-reader code. The operator decides when; do it in the same step as the start, not earlier, and never over another session's uncommitted edits (see `kv-unified-stack-rollout.md` merge note).
- [ ] **VB-AP-SPINUP-STRATEGY-STORE — check the strategy store before the first start.** `orchestration/repl_memory/strategies/strategies.db` has 1428 strategies but `strategy_conventions` is 0 (planner hints will be empty) and `strategy_embeddings.faiss` is dated 2026-08-04, older than the db (2026-08-08). Confirm whether the empty conventions table is expected after the 2026-08 rewinds and whether the faiss index and `strategy_id_map.npy` still cover the db rows (see the atomic co-location note in `autopilot-decision-plane-audit-2026-07-22.md`); rebuild the index if it is stale. Read-only first; no autopilot process running.
- [ ] **VB-AP-SPINUP-MANIFEST-DRIFT — on the first start, record the run-manifest drift reasons.** Upstream added three baseline runtime flags to `orchestration/runtime_flags.spec.yaml` (`observed_dependency_logging`, `skill_injection_scan`, `voice_turn`). `manifest_drift_reasons` compares the run manifest against the last state, so the first start may report drift. Not checked (needs the start path). Expected result: drift names only those flags and is acknowledged, not a blocker. In the same pass re-read the W8 promotion-evidence line of `restart_readiness_report.py` (see the decline below).
  - *Declined as a separate task: W8 promotion evidence "blocked (stale-reference)".* The 2026-10-21 report shows no pending candidate, no finalized trial, `baseline_reference=fresh` and `Restart ready: true`; the block is a historic last-blocked reason from trial 1436 and cannot bind until a candidate exists. It is re-read in the manifest-drift pass above instead of becoming its own box.
- **Trial clock (belief-kernel refocus).** The refocus is evaluated on 2026-11-30 (moved 2026-11-11 → 2026-11-30 by operator 2026-10-21) and needs at least 7 days of live running of BOTH consumers to count: AutoKernel and autopilot each need at least 7 days live by 2026-11-30, so each must be started by about 2026-11-23 (was 2026-11-04). AutoKernel's reader landed 2026-10-21 (research `b7b23fe1c`), so its start is the next CPU window it runs in; autopilot's spin-up tasks are above and are on the same path. A loop that starts later than 2026-11-23 does not count toward the evaluation.
- [ ] **VB-REFOCUS-TRIAL-REMINDER — durable operator reminders for the trial clock (installed: remove after 2026-11-30).** `scripts/vidya/belief_trial_reminder.py` notifies through `alarm_channel.py` every Monday, on 2026-11-20 / 11-23 / 11-30, daily from 11-23 while a loop is not running (critical), and once after the evaluation. Installed 2026-10-21 as an hourly nohup loop, NOT cron (the container has no `crontab` binary): `/mnt/raid0/llm/tmp/belief-trial-reminder/run-loop.sh`, log `/mnt/raid0/llm/logs/belief_trial_reminder.log`. It survives Claude crashes but not host reboots; the re-arm command is in the script header. Tick when the loop is verified running with one `--dry-run` and re-armed after any host reboot; stop the loop and delete this row after the final message.
- **P1 integration state (2026-10-21 evening).** Root `f8/belief-p1-integrated` @ `d83f69357` (31 commits over main: lanes A carrier, B serving v2, C experiments adapter, D floor, E reader with knob/lineup tiers, K KPF-18 scope, L PB-HOL-1 adapter, M `autopilot_journal` belief_scope, plus a fix for the pre-existing `test_odl_model_gated` double import). Full `tests/vidya`: 2390 passed, 2 failed (the known `evidence_durability` pair, see the box below). Orchestrator `f8/belief-p1-ap-consumer` @ `f0e670a1` (P1-G, P1-J, P1-M write side; 62 + 125 tests passed). Research `f8/belief-p1-ak-consumer` @ `2a2b5c823` (328 tests passed) and `f8/pb-hol-1-producer` @ `d6604b32c` (the PB-HOL-1 producer moved into the repo). Landing is GATED on DP-1; DP-4 is open beside it. NOTHING is on main yet.
- [x] **P1-A — carrier.** `claim_tuple.py`: inert `observation` block, new applicability keys, conditional emission in `to_frames` (existing frames byte-identical; floats encoded as `.12g` strings). Root `f8/belief-p1-integrated`; tested. DESIGN.md §9. ✅ 2026-10-21
- [x] **P1-B — serving A/B v2 projection.** One value-bearing claim per capture (`legacy-serving-v2:<capture_id>`). Integrated branch; tested. DESIGN.md §9. ✅ 2026-10-21
- [x] **P1-C — `autokernel_experiments` adapter.** Read-only `experiments.db` rows → measurement/verifier/BASELINE claims, incremental ingest at planning time; one store-manifest owner shared with the floor adapter. Integrated branch; tested. DESIGN.md §9. ✅ 2026-10-21
- [x] **P1-D — serving-floor adapter.** `autokernel_serving_floor.py` (BASELINE floor claims). Integrated branch; tested. DESIGN.md §9. ✅ 2026-10-21
- [x] **P1-E — reader.** `loop_beliefs.py`: target/sibling/host tiers, model lineage, ranking, value-bearing lines, tried-mechanisms index, empty-target banner, refuted bucket; plus `p1_acceptance.py`. Integrated branch; tested. DESIGN.md §9. ✅ 2026-10-21
- [x] **P1-F — backfill, canonical run GATED ON DP-1.** The canonical-ledger backfill waits for the DP-1 operator decision. DESIGN.md §9.
  - [x] Rehearsal on a ledger COPY: +942 frames; `p1_acceptance.py` AC1-AC4, AC7, AC8 and AC9 PASS. ✅ 2026-10-21
  - [x] AC5 (Qwen3.6-35B-A3B and Qwen3-VL-30B get different usable sets) was AMENDED in `d83f69357` because the 35B now has real KPF-18 target beliefs, so "target tier 0 with the banner" no longer holds for it. Run the amended AC5 on the copy after 2026-10-22 06:30Z (CPU timing ends then; `prepare` is CPU work).
    - ✅ already done 2026-10-22 08:49Z (found 2026-10-24): `/mnt/raid0/llm/tmp/belief-p1-20261021/laneA/acceptance.txt` AC5 PASS (Qwen3-VL-30B target 0 + banner; Qwen3.6-35B target 25, all scoped to its own model file, source `kv-prefix-fork-measurement`; the five CPU usable sets pairwise distinct), with AC1-AC4, AC7-AC9 PASS on the rehearsal copy.
  - [x] Canonical backfill run (after DP-1 and the AC5 run).
    - ✅ already done 2026-10-22 08:51-08:58Z (found 2026-10-24): `run_p1f.sh` against `/mnt/raid0/llm/state/vidya/ledger.jsonl` with `--i-own-the-canonical-ledger` (27B 18 frames / 6 claims; DS41 543 / 181; Q38FN 273 / 91; KPF-18 and PB-HOL-1 0 refused), logs `p1f-*.json` and pre/post copies `ledger.canonical.{pre,post}-p1f.jsonl` in `/mnt/raid0/llm/tmp/belief-p1-20261021/laneA/`.
  - ✅ 2026-10-24: all three sub-steps done (rehearsal 10-21, AC5 run and canonical run 10-22); see the sub-bullets.
- [x] **P1-G — loop consumers.** Research `f8/belief-p1-ak-consumer` @ `2a2b5c823` (`relies_on_claims` in the planner reply, belief section after "Already tried", v2 receipt fields; 328 tests) and orch `f8/belief-p1-ap-consumer` @ `f0e670a1` (v2 answer keys, host/refuted premises refused; 62 + 125 tests). Code complete and tested; LANDING is the separate box `P1-LAND` below. DESIGN.md §9. ✅ 2026-10-21
- [x] **P1-H — adapter README rows.** Source-table rows for autokernel-experiment, autokernel-serving-floor, kv_prefix_fork and pb_hol, amended legacy-serving v2 row (`scripts/vidya/adapters/README.md`). Integrated branch. DESIGN.md §9. ✅ 2026-10-21
- [x] **VB-FLOOR-REGISTRY-WIRE — floor-registry adapter (wiring task, filed with the write side 2026-10-21).** The serving-floor registry (`scripts/utils/floor_registry.py` shim over research `loop/floor_registry.py`; storage = the top-level `serving_floors:` section of the research MASTER model registry, keyed by role, each entry pinning its sealed record by sha256 -- operator 2026-10-22: the master is the only floor store) is a NEW floor source: project each entry as a `BASELINE` claim carrying `applicability{equivalence_key, recipe_hash, request_digest, model_sha, numerics_epoch, claim_class, threads, co_tenancy}` and `observation.noise_floor_rel`. Adapter must refuse a `claim_class=indicative` entry as decision-gating, and reuse `autokernel_serving_floor` projection for v1 rows. v2 matched floors carry no median (the existing adapter projects nothing for them by design): the value-bearing field for v2 is `floor_pct` + `n` + `unit=process`, so this task owns the v2 projection ruling. Add the source-table row to `scripts/vidya/adapters/README.md` when the adapter lands. Never a new grading rule: project to `ClaimTuple`, `grade()` decides. ✅ 2026-10-24 — adapters/floor_registry.py, ingest `floor-registry` (indicative entries withheld as non-gating; sealed-record sha re-derived on DS41-1017 v2).
- [x] **P1-I — applicability keys + knob/lineup tiers.** `role`, `knob_family`, `knobs`, `varied`, `stack_regime`, `role_models` in the carrier; knob tier, ranking and render in the reader (DESIGN.md §12.7). Integrated branch; tested. ✅ 2026-10-21
- [x] **P1-J — per-role, per-family autopilot targets + lineup target.** Orchestrator `loop_beliefs_bridge.py`; tests in `test_autopilot_loop_beliefs.py`. Orch `f8/belief-p1-ap-consumer` @ `f0e670a1`. ✅ 2026-10-21
- [x] **P1-K — `kv_prefix_fork` scope.** Shared `_argv_scope` helper; paired value-bearing serving claims; KPF-18 sidecars ingested (items 7 CPU and GPU fixtures). Integrated branch; tested. ✅ 2026-10-21
- [x] **P1-L — `pb_hol` adapter (retrofit, off arms).** `adapters/pb_hol.py` over the run-20261021T160010Z summary; the producer moved into research (`f8/pb-hol-1-producer` @ `d6604b32c`) so a prospective `belief_measurements.jsonl` can be emitted. Retrofit rows are DP-1 scope. ✅ 2026-10-21
- [x] **P1-M — `autopilot_journal` belief_scope.** Root adapter scopes rows that carry `belief_scope` (prospective only); orchestrator write side records `belief_scope` on journal rows going forward (`f0e670a1`). ✅ 2026-10-21
- [x] **P1-N — receipt fields + shadow-draft counterfactual (ONLY if DP-4 = A).** Orchestrator `planner_coordinator.py:314-336, 1829-1880`; about 1.0 d. If DP-4 = C, close this box as declined by the operator's choice. DESIGN.md §12.7.
  - ✅ already done (found 2026-10-24): orchestrator `175ef6af` "autopilot beliefs P1-N (DP-4=A): receipt tier/knob_family, never-dispatched shadow draft with counterfactual, scoped AP3 gate, pass-rule checker" and `9856ba0b` (the `0e9795f48` branch tip) are on orchestrator origin/main.
- [ ] **P1-LAND — land the Phase-1 branches (root, orchestrator, research x2).** Gated on DP-1 (operator); push order and the research merge "between campaign runs" per P1-G. Do not push before DP-1 is decided. Acceptance (`p1_acceptance.py` on the canonical ledger after P1-F) stays open until then.
- [x] **P1-EVDUR-FIX — fix the 2 failing `tests/vidya/test_evidence_durability_adapter.py` tests.** Pre-existing and independent of Phase 1: the adapter's producer sha / CLI invocation has drifted from `epyc-inference-research/scripts/validate/check_evidence_durability.py`. Re-pin the sha and the CLI call to the current producer (do not loosen the assertions), run `tests/vidya` to 0 failed. Filed 2026-10-21 from the P1 integration run (2390 passed, 2 failed).
  - ✅ already passing (checked 2026-10-24): `tests/vidya/test_evidence_durability_adapter.py` 7 passed, 0 failed on origin/main, and the full `tests/vidya` suite runs 0 failed; `producer_pins.py check` has no evidence-durability pin to re-pin (its one STALE pin is `autokernel_profile.SAMPLED_CPU_ROLLING_PINS[-1]`, a different task). The fixing commit was not isolated.
- Phase 1 integration order (from 2026-10-22 06:30Z, remaining): AC5 on the copy → DP-1 → canonical backfill → P1-LAND.
- [ ] **P1-PHASE2 — Phase 2 of the belief storage redesign** (after P1 acceptance). Scope per DESIGN.md §9.
  - *(2026-10-24, workspace-f8 vidya batch; box stays open on the two sub-boxes below.)* Built against DESIGN.md §9 Phase 2, all projection only (`claim_tuple.grade()` decides; no new ladder):
    - Experiment-row writer: research `f8/ak-exp-belief-capture-20261024` @ `28a83db5e` seals a self-hashed `epyc.autokernel.experiment_belief_capture.v1` in `ExperimentStore.record` (opt-in, passed by `archive.record`; built there because the attempt_id exists only there); root `autokernel_experiments.capture_refusal` re-hashes it and re-derives the subject from the stored row: exact match projects prospective (retrofit false), any difference refuses (never demoted to retrofit). Rows without a capture are byte-identical to Phase 1 (27B 15, Q38FN 162, loop-memory 2601 frame ids).
    - `focus_symbols`: root `Target` already ranked by them (now tested); `owned-targets.json` gains an optional `focus_symbols` list that `serial_roster` -> `run.py` -> `belief_context.prepare` passes through (same research branch; excluded from `resume_binding`).
    - `kv_quant_27b_v10` run-c retrofit (`cli.py ingest kv-quant-27b-v10-retrofit`): runs a/b declined (all cells `status: error`), run-c 5 ok cells x decode/prefill. INGESTED 2026-10-24: 10 rows, 30 frames, all on the knob tier of the Qwen3.8-27B-Q8_0 gpu target (`kv_profile`).
    - `autopilot_journal` applicability: rows without `belief_scope` but with a native AP-55 `infra_fingerprint` now carry `stack_regime` (+ `role_models` from the row's own block); no fingerprint = no regime, whatever the date; lineup-tier end-to-end tests in `tests/vidya/test_autopilot_lineup_tier.py`. The real journal has no post-AP-55 trial yet (0 rows projected).
    - `autokernel_served_shape` (`cli.py ingest autokernel-served-shape`, also globbed by `scoped_ingest` inside a store): per shape x quant type, max NMSE (measurement) and NMSE-over-cap (verifier, `decided_proposition` names anchor, case, widths, `patch.cpp` digest and cap rule). Caps and the anchor-relative set re-derived exactly; anchor `bin/` 16/16 re-hash. INGESTED 2026-10-24 from the DS41-1017 store: 148 rows, 444 frames, 74/74 within cap (worst 0.79 of cap).
    - VB-REFOCUS-READ-COUNTER and VB-AK-PAIRED-LOADGEN-WRITE: done (their own boxes).
    - DS41-1017 floor through `ds41_1017_validation`: covered by the open box VB-DS41-1017-BASELINE-WIRE (same floor, its owner), not duplicated here.
  - [x] **P1-PHASE2-AKEXP-MERGE** ✅ 2026-10-24 — merge research `f8/ak-exp-belief-capture-20261024` (`28a83db5e`) between AutoKernel campaign runs (research merges only between runs, per P1-G). Until then every live experiment row stays retrofit. Owner: the AutoKernel / research-repo session.
    - *(2026-10-24, workspace-f8 main; merge record.)* MERGED to research main as `41c334e6e` between campaign runs (no AutoKernel campaign was running; reviewed MERGE, LOW risk). New live experiment rows can now carry the prospective capture.
  - [x] **P1-PHASE2-SERVED-SHAPE-RECAL** — re-run the DS41-1017 served-shape calibration against the current launch recipe (deterministic, about 50 min on cpus 0-47; needs a CPU window). The calibration records `launch_sha256` `fc9e9ced...`, but `inputs/ds41-1017-cpu-t48.launch.json` was regenerated 2m25s later and hashes `ee30f9b5...`; the launch recipe is the only place the model is named, so the 148 claims carry lane/anchor scope only (`extra.launch_binding: drifted`) and do not reach the DS41-1017 target until the re-run re-projects the same claim ids with model scope. ✅ 2026-10-24 [belief: clm_servedshape:v1:ds41:1ae07dd2aad0:ds41_shexp_gate_up:Q8_0:verify +147 more (autokernel-served-shape, re-projected 2026-10-24T17:14Z)]
    - *(2026-10-24, ws58 wrap-up.)* PASS: run `/mnt/raid0/llm/tmp/f8-launchers-20261024/p1-phase2-served-shape-calib/` VERDICT.json PASS at 17:12:58Z; record `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-1017-cpu-decode-20261021/store/served_shape/calibration-20261024T171254Z.json` sha `4a013b13…`; PREDECLARATION sha256 `90fbc40f…`. Its line 49 rule: the sub-box ticks once the owning session runs the real (non-dry) ingest against the canonical ledger and the claims read on the DS41-1017 model target. Both done: real ingest 2026-10-24T17:14:21Z (`cli.py ingest autokernel-served-shape … --as-of 2026-10-24T17:14:21Z`, run from the origin/main worktree because /workspace lacks `495a62d0f`): 148 rows, 444 frames, 0 refused (log `/mnt/raid0/llm/tmp/ws58-p1-ingest-20261024.log`); `loop_beliefs.py prepare` on target `DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf` / cpu reads target tier 151 claims (`/mnt/raid0/llm/tmp/ws58-p1-read.out`). The parent P1-PHASE2 box stays open (AKEXP-MERGE).
    - *(2026-10-24, workspace-f8 subagent; PREPARED, not armed.)* Launcher `/mnt/raid0/llm/tmp/f8-launchers-20261024/p1-phase2-served-shape-calib/`: block-correctness (NMSE against f32 only, no speed figure). Two quarters preferred (q0,q1; about 50 min), one quarter works (about 100 min); min-window 4200 s, 16 GiB, no model and no port, DRY rc 0, pre-check 15/15. PREDECLARATION sha256 `90fbc40f8a83…`. Calibrator: research pin `d0ebe05f5`. Anchor calibration build used in place, 16/16 files re-hash to the 10-21 digests. Adapter fix landed at root `495a62d0f`: the model is bound from ANY matching calibration that recorded the current recipe sha, not only from the oldest one. After PASS, run `INGEST_CMD.txt`, then tick.
  - *(2026-10-24, workspace-f8 vidya batch.)* `p1_acceptance.py` on a copy of today's canonical ledger (after this batch's ingests; `/mnt/raid0/llm/tmp/f8-vb-batch-20261024/p1acc/acceptance.now-fix.txt`): AC1-AC5 PASS. AC7 PASSES on the backfill delta (`--before pre-p1f --ledger post-p1f`); against today's ledger 10 `clm_intake_2341_*` claims moved Hinted -> Verified from evidence ingested after the backfill, which is outside AC7's scope. AC8 had a sampler defect: its pool admitted every `gate_refused` row by status, so Q38FN `akm-cpu-fa-sparse-mask-bitwalk` (three `oracle_unavailable` scope refusals, which the adapter never projects) was sampled and reported missing; the pool now uses the adapter's own `classify` (test `tests/vidya/test_p1_acceptance_ac8_pool.py`) and AC8 passes 10/10. **AC9 now FAILS**: architect_critic shows 0 KPF-18 item-7 value lines (frontdoor 1). Cause: the 10 kv-quant run-c retrofit claims are `kv_profile`, so they sit on the knob tier, which by the tested design (`test_knob_and_target_share_the_target_budget`) ranks first and shares the 16-claim model budget; they take 10 of the 16 slots. AC9 passed on the pre-batch copy. This needs a decision (options in the batch report): cap the knob tier at half the shared budget while target-tier claims exist (recommended), or amend AC9 to JSON presence, or leave AC9 failing.
    - *(2026-10-24, workspace-f8 backlog sweep; operator chose option A.)* **Option A is landed, but AC9 still FAILS, for a second cause.** `loop_beliefs.render` now caps the knob tier at `KNOB_CAP_WITH_TARGET = 8` of the shared 16 model slots whenever any target-tier claim exists. With no target-tier claim the knob tier keeps all 16. Tests: `test_knob_and_target_share_the_target_budget` (now 8/8), `test_knob_tier_keeps_the_whole_budget_without_target_claims`, `test_knob_cap_leaves_room_for_target_claims_ac9`. Full `tests/vidya`: 3056 passed, 370 skipped.
      - Re-run on the same ledger copy (`ledger.canonical.20261024b.jsonl`; out `/mnt/raid0/llm/tmp/f8-ac9-knobcap-20261024/acceptance.fix-b.txt`): AC1-AC5 and AC8 PASS. AC7 FAILS for the same reason as before, outside its scope. AC9 still FAILS: architect_critic shows 0 KPF-18 item-7 value lines.
      - Why AC9 still fails: architect_critic has 64 target-tier rows (`diag2.py` in the same dir). 14 of them rank in outcome groups 1-3 (pb-hol 1, autokernel-experiment 5, spec-rng-1-2 8), and the forced serving floor takes one more slot. The 8 target slots go to 7 of those plus the floor. KPF-18 item 7 is group 5 (plain measurement), at rank position 54 of 64.
      - Even a 0-claim knob tier (target 16) would not fit KPF: groups 1-3 plus the floor take 15 slots, and the 16th goes round-robin over 6 group-5 sources. The 8 `spec-rng-1-2` claims, ingested today, crowd it out as much as the knob tier did.
      - Open decision: P1-AC9-TARGET-CROWDING (box below).
  - [ ] **P1-AC9-TARGET-CROWDING — operator decision: AC9 cannot pass on today's ledger at a 16-claim model budget (found 2026-10-24 after option A landed).** Higher-ranked target-tier claims (outcome groups 1-3, 14 rows) fill the budget before any plain measurement such as KPF-18 item 7. Options:
    - (B) Amend AC9 to "KPF-18 item 7 is on the knob or target tier in the reader's collected evidence and is counted in the section's `Shown n of N target` line". This is what the reader guarantees under a bounded budget. Recommended.
    - (C) Raise the shared model budget (e.g. 24) under the same 14 KB byte cap. The byte trim then decides, and other targets already render at 13.9 KB.
    - (D) Leave AC9 failing and record it as known.
    - *(2026-10-24, f8 main.)* **Operator decided: (B) amend AC9** to collected-evidence presence plus the count line, over (C) a 24-claim budget and (D) leaving it failing. Not implemented yet: the AC9 definition change, its test and a P1 acceptance re-run (one CPU quarter, no model load, needs a grant) transfer to workspace-58 with the f8 handover. Tick this box once the amended AC9 passes.
- [x] **DP-4 operator decision — AutoPilot PASS rule (A counterfactual-confirmed reliance, B declared reliance + reviewer, C AutoKernel carries PASS, AutoPilot on no-harm only), and the AP3 role-restart gate during the trial.** Recommendation A with AP3 enabled for `spec_draft`/`kv_profile` on the 27B and 35B roles; C if AP3 stays off. DESIGN.md §10 and §12.6. Gates only P1-N. ✅ 2026-10-21 (operator): **DP-4 = (A), counterfactual-confirmed reliance.** P1-N is built on orchestrator `f8/belief-p1-ap-consumer` @ `0e9795f48`. AP3 role-restart runs scoped during the trial: see `VB-AP-SPINUP-AP3-SCOPED`.
- [x] **DP-1 operator decision — retrofit projection of historical AutoKernel records (graded Judged, flagged retrofit).** The one open operator decision; it gates only P1-F, nothing else in Phase 1. Options and tradeoffs in DESIGN.md §9. ✅ 2026-10-21 (operator): **DP-1 = (a), retrofit backfill allowed** (graded Judged, flagged retrofit). P1-F's canonical run is no longer gated on a decision; it still follows the AC5 run.
- [x] **VB-REFOCUS-READ-COUNTER — report non-empty vs empty reader hits as a standing metric.** The 933-reads-found-nothing result was only visible by manual review; emit empty/non-empty counts per consumer so a consumer that never changes an outcome is visible without a review.
  - ✅ 2026-10-24 (workspace-f8 vidya batch). `scripts/vidya/read_counter.py`: every `loop_beliefs.prepare` (ready or refused) appends one record (consumer, target_key, as_of, status, `nonempty_target`, `usable_count`, `tier_counts`) to `reads.jsonl` beside the resolved ledger (override `--read-log` / `VIDYA_READ_LOG`; a failed write shows as `read_log_error`, never a refusal); `loop_beliefs.py read-counter [--days|--since|--until] [--json]` tallies nonempty / empty / refused / no_read per consumer, per target and per source, and also reads the consumers' own history (AutoKernel `belief-receipts.jsonl`, v2 `evidence_v2.nonempty_target`, v1 = exposed-a-claim proxy; AutoPilot `planner_archive.jsonl` rows with `vidya_loop_beliefs`), de-duplicated. First real read-out: 937 reads, all `autokernel.planner`, 933 empty / 4 non-empty (0.4%; DS41-Q4 0/662, 27B 0/3, Q38FN 4/268); AutoPilot 0 reads (no archive row carries `vidya_loop_beliefs` yet). Tests `tests/vidya/test_read_counter.py` (6).
- [x] **VB-AK-PAIRED-LOADGEN-WRITE — Belief-kernel write side for `paired_loadgen` A/B/A/B records.** `scripts/kernel_rnd/autokernel/loop/paired_loadgen.py` (research, AKR-SG-2, `ba1f758a4`) emits `epyc.autokernel.serving_ab.v1` records with no `belief_capture`, so `serving_beliefs.export` skips them and its A/B/A/B results never reach `<store>/serving-beliefs/` or the reader (found in the AK reader merge review 2026-10-21; nothing in `run.py` calls it today, it is an operator wrapper). Wire the write side now, at the producer, not on read: emit the capture the strict adapter `autokernel_legacy_serving.py` already accepts (do not add a second parser or a grading rule; `claim_tuple.grade()` grades), and add the row to the source table in `scripts/vidya/adapters/README.md` in the SAME commit. Acceptance: a fixture `paired_loadgen` record whose export is read back by the adapter and grades; a record without the capture is refused loudly rather than skipped. ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`.
- [ ] **VB-AK-ROOT-RESOLVE-REMAINING — move the other direct-`/workspace` ROOT consumers in AutoKernel to `belief_context.resolve_root_repo`.** `actors._seat_capture` (VB-AK-SEAT write side), `ak_check.py`, `claim.py` and `cpu_window.py` still read `EPYC_ROOT_REPO` with a hard `/workspace` default (research `scripts/kernel_rnd/autokernel/loop/`), so on a host where `/workspace` is a diverged clone they read stale ROOT code while the belief reader and the serving-receipt adapter read the hub view. Check each consumer's need first: `claim.py` resolves the orchestrator CPU-lock owner and may need `/workspace` deliberately (its error text names `EPYC_ROOT_REPO`); move only those that read ROOT code that exists in origin/main, and say why for any left alone. Tests: the resolution order cases in `test_belief_context.py` plus one per moved consumer.
  - *Declined as a separate task: wiring `ak-ds41-1017-cpu-decode-20261021/store` into ingest (checked 2026-10-21).* Not a gap. The store has no `serving-beliefs/` directory yet (only `scratch/` and `served_shape/`; nothing captured), the loop already passes its own `--store` to the reader as `--source-root` (`run._belief_config`), so the first receipt it archives is ingested before the next plan, and `ingest autokernel` walks `/mnt/raid0/llm/autokernel` for the rest. The real gap is the producer side, filed as VB-AK-PAIRED-LOADGEN-WRITE.
- [x] **VB-L2-WRITE — Belief-kernel write side for the L2 scan and its calibration tables.** Add the source-table row in `scripts/vidya/adapters/README.md` and the write-side hook so HIL-13 and HIL-14 outputs (per-category counts with denominators, calibration precision and recall with N, baselines) are emitted with a claim tuple at run time, not retrofitted; no new grading rule: the adapter projects into a ClaimTuple and the registry ladder grades. Acceptance: a row in the adapter table and a fixture record that grades. Estimate: 0.5 day. ✅ 2026-10-21
  - 2026-10-21 done (dpf-hil): `scripts/vidya/adapters/l2_scan_capture.py` (writer, opt-in `--belief-sidecar` on both orchestrator CLIs) + `l2_scan.py` (reader, projects only; `claim_tuple.grade()` grades) + README source-table row; `tests/vidya/test_l2_scan_adapter.py` passes (13 with the TALE regression). Real sidecars generated at run time for the HIL-13 task-level report (11 rows) and the HIL-14 calibration (17 rows), kept in `artifacts/dpf-hil-20261021/` (their `report_path` points at the deleted scratch copy, so they read back as attestation-absent and grade down by design; the committed JSON has the same sha256).
- [x] **VB-HIL-REPLAY-WRITE — Belief-kernel write side for the replay-flip report and the spectrum report, before their first filed run.** Reuse the VB-L2-WRITE pattern (`scripts/vidya/adapters/l2_scan_capture.py`): opt-in sidecar emitted by `scripts/trace/replay_flip_run.py flip` (`replay_flip_report/v1`) and `scripts/trace/spectrum_replay.py report` (`spectrum_report/v1`) at write time, one claim-tuple-shaped row per arm rate / per ranked top key / per agreement count with its denominator in `reps`; README rows already added (prospective). No new grading rule: the adapter projects into a ClaimTuple and the registry ladder grades; a report without a sidecar is pre-hook and emits zero rows. Acceptance: writer and reader with a fixture record that grades, and both orchestrator CLIs calling the writer. Must land before HIL-16b and HIL-18a file their reports. Estimate: 0.5 day.
  - 2026-10-21 done (hil16b; root `116356c87`, orchestrator `64aa7f8f`): writer `scripts/vidya/adapters/hil_replay_capture.py` and reader `hil_replay.py` (no new grading rule; rows project into a ClaimTuple with empty protocol, graded Judged). Both orchestrator CLIs take `--belief-sidecar`. The writer refuses any report whose `label` is not exactly `measurement`, so the committed synthetic `replay_flip_report.example.json` is refused, and a forged sidecar over it reads back as zero rows (void). `hil_decisive` echoes the report's own `decisive`, so a flip alone never reads back as decisiveness. Tests `tests/vidya/test_hil_replay_adapter.py` (9), orchestrator `tests/unit/test_hil_replay_sidecar.py` (3, real `build_report` -> writer -> reader). README rows moved from prospective to wired.
- [x] **VB-HIL15A-WRITE — Belief-kernel write side for the flag-on dependency AUC table (before the first live filed table).** Sidecar `<out>/auc_table.beliefs.jsonl` emitted by `epyc-orchestrator` `scripts/trace/hil15a_flagon_run.py` at write time (opt-in, never backfilled); rows per feature set and per delta with CI, `reps` = runs, tasks and failed in `extra`, edge grade `observed`; the writer refuses `"mock": true` manifests. README row added (prospective). Acceptance: writer and reader with a fixture record that grades, driver calling the writer. Must land before the s5-hil15a-flagon window files its table. Estimate: 0.5 day. (queue-builders-3, 2026-10-21) ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`.
- [x] **VB-DRIPREVIEW-WRITE — Belief-kernel write side for the D-RI-PREVIEW-1 comparator result.** Sidecar from `run_repl_preview.py` at write time: per role x rendering correct-rate with the class counts, `reps` = samples started, locator = GGUF x rendering x fixture sha256; refuses `mock` and partial (`complete` false) results. README row added. Acceptance: writer and reader with a fixture that grades; driver calls the writer. Must land before `s5-dripreview1` files a result. Estimate: 0.3 day. (queue-builders-3, 2026-10-21) ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`.
- [x] **VB-AKRSG-WRITE — Belief-kernel hook for `paired_loadgen` records.** `serving_beliefs` fires only inside `serving.compare`; a record from `run_paired_serving_ab.py` has no hook. Add the write at record time, session-unit floor stated, A/A shakedown rows marked pipeline-only. README row added. Acceptance: a toy-endpoint record grades through the adapter; driver calls the writer. Estimate: 0.3 day. (queue-builders-3, 2026-10-21) ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`.
- [x] **VB-AKRSG-INGEST — ingest the first live `serving_ab.v1` record as a pipeline-only row, and wire the AKX-ALL-27b `width_dimension` record.** Checked 2026-10-22: `/mnt/raid0/llm/tmp/akrsg-out/run-20261022T130855Z/serving_ab.json` has no `belief` key and the run dir holds no `legacy_serving_capture.v1`, because the VB-AKRSG-WRITE writer (`export_belief`) is on research branch `vb-write-akpl-3c4ca599`, unmerged to research main. Merge that branch, re-export the capture from the stored record (A/A, so `pipeline_only`; no tuple invented), and ingest through `autokernel_legacy_serving`. Also: the AKX-ALL-27b record `/mnt/raid0/llm/tmp/v11-runs/akx27/20261022T124733Z/width_dimension.json` (`epyc.autokernel.width_invariance_dimension.v1`) has no adapter; fold it into VB-AKX-ALL-26-CELLS-WIRE's source row (HIP half). Acceptance: both records appear in the ledger via their adapters, or the README row names the refusal. (filed 2026-10-22) ✅ 2026-10-22 both records in the ledger via their adapters. akrsg: research branch merged to main (`121b822bc`, `0b86b08b7`); capture re-exported from the stored record (`pipeline_only`, windows = run envelope) and ingested through `autokernel_legacy_serving`: `legacy-serving:452adb89...:{anchor,candidate}` + `legacy-serving-v2:452adb89...`, all Judged/Located; session `reps_basis` text fixed on both sides. akx: new `autokernel_width_dimension.py` (`cli.py ingest ak-width-dimension`), 4 tuples `akx-width:14e74971...:*` Judged/Located. See README rows and `progress/2026-10/2026-10-22-vb-akrsg-akx-ingest.md`.
- [x] **VB-HSPROF1-WRITE — Belief-kernel write side for the HS-PROF-1 profile-arm table.** The BEAM `--belief-measurements --arm` path cannot express two arms that share context mode `profile`; add a profile-arm projection (per ability and arm judge-scored mean with n, paired delta with win/loss/tie, judge and reader identity in `extra`) or extend `beam_memory_capture` with a profile ladder. README row added. Acceptance: writer and reader with a fixture that grades. Must land before `s5-hsprof1-beam` files its table. Estimate: 0.5 day. (queue-builders-3, 2026-10-21) ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`.
- [x] **VB-IBENCH-WRITE — Belief-kernel write side for injection fixture results.** Wire CT-18 results as a source with the claim grammar static-attack ASR on fixture set X (fixture hash, arm, thinking setting, served pin) so no result can be read back as robustness; add the adapter row. Acceptance: a row in the adapter table and a fixture record that grades. Estimate: 0.5 day. ✅ 2026-10-21
  - *(2026-10-21, dpf-specs.)* Adapter `scripts/vidya/adapters/injection_fixture.py` (`injection-fixture`), adapter-table row, fixture record grades Witnessed/Attested (`tests/vidya/test_ibench_kvchunk_carriers.py`).
- [x] **VB-KVCHUNK-WRITE — Belief-kernel write side for chunk-KV and prefix-hit measurements.** Wire KPF-60 and KPF-64 outputs (per-role prefill rate, inject latency, drift curve, realised versus ideal prefix-hit share) and the RTE-LOG-1 reader reports as a source with the served pin and window claim recorded; add the adapter row when KPF-60 starts producing numbers. Acceptance: a row in the adapter table and a fixture record that grades. Estimate: 0.5 day. ✅ 2026-10-21
  - *(2026-10-21, dpf-specs.)* Adapter `scripts/vidya/adapters/chunk_kv.py` (`chunk-kv`), adapter-table row, fixture record grades Witnessed/Attested. KPF-60/KPF-64/RTE-LOG-1 producers must call `write_belief_measurements` when they first produce numbers.
  - *(2026-10-21 note, dpf-kpf62.)* KPF-62 (chunk-KV phase 1) G1 and G3 records feed this source. Existing kinds cover its speed rows (`prefill_rate`, `inject_latency`, `source_program: KPF-62`, served pin + window). G1 exactness NMSEs and the G3 approximation metrics (KL, top-1, logits NMSE, retention, naive-baseline ratio) fit no current kind: the adapter needs `KPF-62` in `PROGRAMS` plus two kinds, tracked as KPF-62.2 in `kv-prefix-fork-and-paged-attention.md`. First G1 numbers (tiny-model CPU run) exist now, so a fixture can be built from them.
  - 2026-10-24 source correction: the retained G1 text logs contain aggregates, not native per-position payloads; they cannot be reconstructed into the new reader's input. ROOT source support is now on main at `8f4fea302798d9b938e2da655cee86ca3d14f09d`; the prospective producer tasks below retain the missing write side.
- [x] **VB-KPF62-POSITIONS-WRITE — same-run write path for KPF-62 native G1 positions.** Capture schema-v1 per-position sufficient statistics at the producer boundary and finalize them into the existing chunk-kv carrier with the actual invocation, ROOT adapter pin, producer source/binary/model hashes, grant/window IDs and UTC bounds, and raw-input hash. Require every requested delta/component/comparison/position. Preserve raw failure/partial output and emit no accepted complete sidecar for it. Producer `0a9fa2c29bc0929d7a2493a8416659ca892ae3d6` is proposed/unbuilt; no fold or build is authorized by this row. Acceptance: an owner-booked generated-tiny-model run emits complete groups at deltas 1/17/300, finalizes from its new JSONL at that same run boundary, and grades through existing `claim_tuple.grade()`. No legacy backfill, serving/quality/performance/cost/production claim, new class/ladder, or protocol inferred from the schema; retain unknown protocol when none applies. Also completes parent KPF-62.2's native G1 acceptance. Evidence 2026-10-27: native dir /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build/native-20261027T205829Z; 324 rows, 18 complete groups, 27 shared grades Judged/Located; G1a mismatch is zero at deltas 1/17/300; build receipt sha256 6cddb24429ce2a590f83a0303d88719ee2183b5c036ee4ac861d42f1a883fdca; raw sha256 6d0640fb37805a9be99d6eebdb0a88bc22cb5d75b707e55d9f4fb4fc107f1328. Committed snapshot: artifacts/engineering/kpf62-fixed-build-20261027/native-result (branch codex/kpf62-fixed-build-20261027 @ 2d0bb20a0f33e325739a4321d206e6e99fb4bfa8; progress/2026-10/2026-10-27-kpf62-native-g1-result.md). [belief: cc]
- [ ] **VB-KPF62-G3-WRITE — wire KPF-62.6 G3 native positions at run finalization.** Before its next eligible dev/corpus capture, bind the native requests.jsonl and positions.jsonl with source/model/binary pins, invocation and granted window, and call the existing chunk-kv writer at that same run boundary. Keep G3 per-metric observations separate from `g3_gate.py` corpus gates; retain failed/partial originals and omit retention until its separately bound paired score payload exists. No old-log tuple reconstruction, new class/ladder, or invented protocol. Acceptance: a new granted G3 dev capture writes reader-valid per-metric rows through the existing grader; corpus-gate readiness still depends on the KPF-60 frozen manifest, and no corpus PASS follows from this wiring.


- [x] **VB-NI08-CI-PII-METADATA-SOURCE — capture typed CI identifier and owned-operation timestamp metadata disambiguation controls through the existing native CI family.** Before any hosted source event, bind the exact approved normal PII scanner/helper/context source, full import/config/dependency closure and positive/negative controls. Preserve original request, argv, status/stdout/stderr, JUnit case identities, receipt, readset and shared-grade outputs with native_conformance carrier `4c0c653baf1654c8c25c66433cf39c8faefd8e52`. The intended source correction is limited to two typed metadata contexts; actual secret/account refusal controls must remain load-bearing. Retain original FALSE/NULL and failures. Original source-control outcome follows; no host hook installation, new grading class/ladder, production safety claim or historical backfill. MAIN published enrollment before the original source event. ✅ 2026-10-21 — MAIN accepted source `587a47edd8c1b791b2eed8a228c5f2647734a348`, original GitHub push [39596348505](https://github.com/pestopoppa/epyc-root/actions/runs/39596348505), attempt 1: all 52 selected cases passed, zero failures/errors/skips, native TRUE and existing Judged/Located shared grade. Eight baseline metadata false positives are reproduced; positive/refusal and opposite-working-tree staged controls pass. The 52 distinct PII-family originals contain 12 expected TRUE and 40 expected FALSE outcomes; three byte-identical pytest-current archive aliases remain retained. [Original source custody](../../artifacts/ci/pii-native-metadata-source-20261021/README.md). This closes source validation only; installed/shared policy was unchanged by the source event and no privacy or production-safety guarantee follows.

## Source controls accepted — 2026-10-21

MAIN accepted all six prospective source-capture tasks: NIB83 7/7, PII metadata 52/52, CJ10 59/59, S05 observer 11/11, CJ14 44/44 and CJ5/6/7 27/27, each with zero skips, failures or errors: **200 passing controls across six tasks**, not 200 task closures. Existing shared grade is Judged/Located. CJ10 file inventories remain ten Research and nineteen ROOT files; the five earlier PyArrow skips and CJ567 first custodian timeout remain immutable history. No quality, cohort, owner-window, live inference, protocol, fleet-discrimination or performance parent closes.

- [x] **VB-NIB83-NATIVE-E17-HISTOGRAM — capture opt-in standalone native-era histogram source controls.** Before first test event, bind future MAIN enrollment/readset/source blobs and ordinary seven-allA OWN constructor; publish one fresh push-only hosted event through existing ci-fixture-conformance producer/adapter/shared grade at carrier4c0c653baf1654c8c25c66433cf39c8faefd8e52. Seven synthetic controls preserve explicit `journalTimestamp`/`eval_quality_era` and native sidecar `ended_at_s` with its declared authority, timestamp/era/error missingness, and historical/mixed-era and malformed/unknown-category refusals. Bind the exact current producer/adapter schema; do not invent aliases such as a substitute timestamp or inferred authority. Preserve original JUnit/receipt/source readset/false/null. No actual post-E17 cohort, new infra taxonomy, product imports/inference, new class/ladder or ledger append from source publication. ✅ 2026-10-21 — Original source-control event: ROOT commit `ee7428992d3cb157bb054967ea08d6f4e5f76de5`; GitHub push run [39596176243](https://github.com/pestopoppa/epyc-root/actions/runs/39596176243), attempt 1, native TRUE with seven synthetic cases passed (0 failed, 0 errors, 0 skipped); existing shared grade is Judged/Located. [Original receipt](../../artifacts/ci/nib83-native-source-20261021/README.md#native-custody) and [shared grade](../../artifacts/ci/nib83-native-source-20261021/README.md#shared-grade). This closes only source-control capture: no actual post-E17 cohort or real histogram was produced; parent cohort analysis remains outstanding.

- [x] **VB-CJ10-PROMPT-SOURCE-CONFORMANCE — capture pinned prompt and provenance source controls prospectively.** Bind the ten-file Research source candidate `c43ce72f22501944eb76d40ce6af6e696d6c3931` and copied hosted recipe, upstream full-source/literal/blob attestations, wrapper identity, 12,000-character substitution cap, preserved untagged historical missingness and byte-preserving mixed/unversioned partial refusal before any judge call/output mutation. Capture whole test_beam_adapter.py, test_judge_beam_run.py and test_beam_judge_provenance.py with synthetic fixtures/stub transport and existing carrier4c0/ci-fixture-conformance/shared grade; freeze exact enrollment/carrier/readset/requirements/source bytes before fresh OWN push. Retain original false/null; no live JSON reliability/judge-agreement, inferred old provenance, score rewrite, new ladder or ledger append from source publication. Current inventories are 10 Research files and 19 ROOT files, not executed-case counts; rebind current source before capture. ✅ 2026-10-21 — MAIN accepted original [run 39597112001](https://github.com/pestopoppa/epyc-root/actions/runs/39597112001) attempt one, native TRUE 59/59 with zero skips/failures/errors and existing Judged/Located. [Original custody and secondary grade](../../artifacts/ci/cj10-prompt-source-20261021/README.md). Source-capture child only; quality/cohort/live-inference parents remain open.

- [x] **VB-EVL49-S05-OBSERVER-SOURCE-CAPTURE — prospectively capture the narrow unchanged-harness observation launcher controls.** Bind accepted S05 source leaf8168cb17089e60c098ffa8b9a501440e1435ebaf plus reviewed observer/test/capture source and eleven synthetic controls in a fresh hosted push event through existing ci-fixture-conformance/shared grade. Source wraps pinned start_server/preflight/driver/teardown seams; proposed native reader retains original launch/PID startticks/cmdline, meminfo/cache, NUMA/status/pages before/DURING/after request window, archive reopening and verified owned-PID teardown. This child is synthetic sourcecapture only; current prompt pool, owner window, cache effects, page residency and live benchmark evidence remain open in S05. Original33 manifests/48 generated outputs/2764 native readset stay unchanged; no new class/ladder or grading rule. ✅ 2026-10-21 — MAIN accepted original [run 39596455619](https://github.com/pestopoppa/epyc-root/actions/runs/39596455619) attempt one, native TRUE 11/11 with zero skips/failures/errors and existing Judged/Located. [Original custody and secondary grade](../../artifacts/ci/s05-observer-source-20261021/README.md). Source-capture child only; quality/cohort/live-inference parents remain open.

- [x] **VB-CJ14-REDUNDANCY-SOURCE-CAPTURE — prospectively capture the current APP typed-decision judge-redundancy source controls.** The current audit identified `tests/unit/test_typed_decisions_judge_redundancy.py`, which was not included in HG249. Before any hosted source event, bind the exact current approved APP source commit and complete `spec_policy` source closure, manifest and hash, preregistration identity, case mapping and case-blind-majority protocol references, complete imports/dependencies and runner context. Preserve original argv, exit/stdout/stderr, JUnit case identities, receipt, source readset and outputs with the existing CI producer/adapter/shared grade. The eventual case count is set by the exact bound manifest; do not guess it here. This source task does not establish live judge quality, agreement, model behavior, protocol ratification or decision-grade evidence. MAIN reviews and applies enrollment; source owner performs future capture. Current typed_redundancy imports require the actual spec_policy source closure; native case count remains unknown. ✅ 2026-10-21 — MAIN accepted original [run 39596520546](https://github.com/pestopoppa/epyc-root/actions/runs/39596520546) attempt one, native TRUE 44/44 with zero skips/failures/errors and existing Judged/Located. [Original custody and secondary grade](../../artifacts/ci/cj14-redundancy-source-20261021/README.md). Source-capture child only; quality/cohort/live-inference parents remain open.

- [x] **VB-CJ5-6-7-FIXTURE-SOURCE — prospectively capture six fixture source files through the existing CI family.** Bind current source/requirements/import/readset and original request/argv/status/JUnit/outputs before new events. The source inventory has 3 reporting, 6 IFBench and 5 edit test functions; executed native case counts are unknown until capture. Preserve FALSE/NULL; no runtime quality, new source class, second ladder or historical tuple. ✅ 2026-10-21 — MAIN accepted original [run 39596675122](https://github.com/pestopoppa/epyc-root/actions/runs/39596675122) attempt one, native TRUE 27/27 with zero skips/failures/errors and existing Judged/Located. [Original custody and secondary grade](../../artifacts/ci/cj567-fixture-source-20261021/README.md). Source-capture child only; quality/cohort/live-inference parents remain open.


### PII native metadata source validation accepted — 2026-10-21

One existing source-control checkbox closes after original 52/52 capture acceptance. The preceding two-task checkpoint was **216 = 141 existing checkbox closures + 75 scoped children**. NIB83 seven-case custody and its existing checkbox closure remain intact; the PII fixture count is not a task count. The source fix recognizes only typed native CI fields and the supplied owned-operation path with a sole matched numeric token; actual account/secret refusal controls remain load-bearing. Integration and normal governance are handled at the owning FULL checkpoint.


### Four additional source-capture tasks accepted — 2026-10-21

The scoped total is **220 = 145 existing checkbox closures + 75 scoped children**. This update flips exactly four existing source-capture checkboxes after MAIN acceptance; NIB83 and PII metadata had already raised the prior working total to 216. Parent tasks remain open. [CJ10](../../artifacts/ci/cj10-prompt-source-20261021/README.md), [S05 observer](../../artifacts/ci/s05-observer-source-20261021/README.md), [CJ14](../../artifacts/ci/cj14-redundancy-source-20261021/README.md), [CJ5/6/7](../../artifacts/ci/cj567-fixture-source-20261021/README.md). Secondary grade source commit `fda2174b115d0eabcd9fa1abd88e2461a2685d2e` is an additional integration parent, not another source task closure.


### Prospective staged-shell SIGPIPE lint source controls — 2026-10-21

- [x] **VB-LINT-SIGPIPE-GREP-Q-CONFORMANCE — prospectively capture the staged-shell SIGPIPE lint controls.** Bind the exact checker, optional versioned pre-commit call, full tests and source readset, native producer/projector/shared-grade bytes, Python/Git/shell toolchain and runner recipe before the first hosted event. Synthetic controls cover pipefail-enabled producer pipelines, grep option arguments, quoted/commented text, line continuation, safe alternatives, staged-versus-working-tree disagreement in both directions, warning exit-zero and failed Git-scan exit-zero. The checker inspects staged blobs only; findings and scan errors stay warn-only and source content is not printed. Use the existing `native_conformance.py` → `ci_conformance.py` → `claim_tuple.grade()` path. Preserve original request/argv/JUnit/receipt/readset and FALSE/NULL. No host-wide scan, actual recurrence rate, inference, production safety claim, new source class or ladder; MAIN reviews and applies source enrollment before capture. ✅ 2026-10-21; [lint native evidence](../../artifacts/ci/lint-sigpipe-source-20261021/README.md).

### Prospective ingestion reliability source controls — 2026-10-21

- [ ] **VB-CLI-INGEST-CONFORMANCE — capture native source controls for CLI preflight and ODL import identity.** Bind the exact CLI/adapter/test source closure, original three failed identities and added regression identities, runner/toolchain, request/readset/argv/JUnit and original receipt before the first hosted event. Cover missing-root refusal before ledger/lock creation, preserved valid-write serialization, both import orders and genuine duplicate-projection refusal. Missing-root CLI diagnostics must create no belief claim; preserve native TRUE/FALSE/NULL and original failures through existing `ci-fixture-conformance` carrier4c0, `ci_conformance.py` and shared `claim_tuple.grade()`. No new source class, grading ladder, inference, historical reseal or protocol admission. MAIN reviews and applies enrollment before capture.

### Lint capture accepted — 2026-10-21

MAIN accepted original selected run `39617059382` attempt1 at source `56b782ebf20a88b356057983bf73594b5e22a907`: 11/11 controls passed, zero failures/errors/skips. Receipt seal `610399bb60f55ee6e3dffe541db0f9b83f53eaa8877753a10c57be4d59f81555`; unchanged shared grade Judged/Located describes warrant, while native JUnit reports the verdict. The checker reads staged shell blobs and warns about producer pipelines with `grep -q` under pipefail; warnings and scan errors remain advisory. Versioned installer wiring was source-inspected; these 11 controls exercise the checker, not a live installer. No installed-hook activation is claimed. [lint native evidence](../../artifacts/ci/lint-sigpipe-source-20261021/README.md). No new source class or grading ladder. Two lint task closures raise the historical220 boundary to222; test cases are not tasks. CLI and M12i replay custody remain open.

- [x] **VB-YARN-AGG-1 — write side for the YaRN gate aggregation, recall and judged arms, before their first window run.** Filed 2026-10-21 beside YARN-AGG-1 / YARN-JUDGE-1. The emitters in research `scripts/benchmark/yarn_gate/` (`agg_scoring.py`, `helmet_judged_cell.py`, `judge_validation_kit.py`) already write the judge pin, the HELMET and generator pins, the real prompt_n bin and zone, and the noninferiority verdict. Add a projection into a `ClaimTuple` (no new ladder, `claim_tuple.grade()` decides) and the adapter row in `scripts/vidya/adapters/README.md` (added). Done when a mock-judged cell round-trips to a tuple carrying the judge pin and zone, and the adapter test passes. ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`.

- [x] **VB-RUS2-PROBE-WIRE — wire the RUS-2 probe output as a measurement adapter.** Projection only into a ClaimTuple; record that temperature and finish_reason are absent from the source records so grade() downgrades (RUS-2, 2026-10-21; `artifacts/rus-2-20261021/rus2_result.json`). ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`. Producer call ✅ 2026-10-22 (research main `04d4c1788`): result carries `generated_at`, `input_digests`, `script_sha256`; `--belief-out DIR` calls the writer.

- [x] **VB-RTEPFX2-WIRE — write side for the RTE-PFX-2 stagger probe, before its first window run.** Filed 2026-10-21 (queue-builders-2). The probe (`epyc-orchestrator` `scripts/benchmark/rte_pfx2_stagger_probe.py`, launched by `rte_pfx2_role_recipe.py`) writes `probe.json` and `RUN_HEADER.json`; project per-arm uncached prompt tokens and sibling cache-hit counts into the `chunk-kv` carrier with the served pin and window, graded by `claim_tuple.grade()` only. Acceptance: adapter-table row (added) plus a fixture record that grades. Also KPF-64's `analysis.write_belief_measurements` (research repo) must be called on its first numbers (covered by VB-KVCHUNK-WRITE). ✅ 2026-10-22 write side landed (root `scripts/vidya/adapters/`, tests in `tests/vidya/`); producer-side calls/gaps in README rows 'VB write sides, 2026-10-22' and `progress/2026-10/2026-10-22-vb-write-sides.md`.

- [x] **VB-CAL-OVERRUN-WIRE — emit estimate-vs-actual claim tuples from the compute-calendar overrun check.** Filed 2026-10-22 (workspace-58, after D4 k5_s4 ran 2.1x its estimate: the estimator was wrong, see `/mnt/raid0/llm/tmp/d4-why-20261022/REPORT.md`). Project each finished granted job's (estimated wall, actual wall, ratio, rc, co-residents) into a `ClaimTuple` (measurement class, `claim_tuple.grade()` decides). Acceptance: adapter-table row (added) plus a fixture `.ended` record that grades. ✅ 2026-10-24 — read side: adapters/calendar_overrun.py, ingest `calendar-overrun` (D4 k5_s4 fixture grades). Write side filed as VB-CAL-OVERRUN-WRITE below.
- [x] **VB-CAL-OVERRUN-WRITE — append the overrun keys at job end.** (filed 2026-10-24, workspace-58) The job-end record (`.ended`, written by `filler_run9.sh`) must append `estimated_wall_s` (from the FILLERS row duration) and the other key=value lines the calendar-overrun adapter reads (`scripts/vidya/adapters/calendar_overrun.py`, `cli.py ingest calendar-overrun`). Keep line 1 (`rc= time= reason=`) unchanged — grant writers read `head -1`. Required: `job_id=`, `owner=`, `step=`, `estimated_wall_s=` (>0), and `actual_wall_s=` or `started=<ISO UTC>` (paired with line-1 `time`). Optional: `ratio=` (re-derived; mismatch refused), `regions=`, `co_residents=`, `np=`, `ctx=`, `estimator=`. A job without an estimate omits `estimated_wall_s` (skipped, never invented). Done when a real finished filler `.ended` ingests as one tuple. ✅ 2026-10-27 — owner-adopted source engine run12 emitted a real `.ended` event (job codex-ni-inf50-existing-graph-r10-20261027; actual 27s / estimated 900s; rc=0). Owner ingest with `--only-new`: matched=1, projected=1, declined=0, refused=0, rows=1, frames=3, skipped=0; claim `clm_calendar-overrun:codex-ni-inf50-existing-graph-r10-20261027:004e6e8ba668ad01` appended to `/mnt/raid0/llm/state/vidya/ledger.jsonl`. Dry run admitted/projected 1 with 0 refused. No patch required: source engine run12 was already adopted. This claim supports wall/estimate only for this job; graph r10 rc=0 does not certify semantic completeness or fold trust. [belief: clm_calendar-overrun:codex-ni-inf50-existing-graph-r10-20261027:004e6e8ba668ad01] Second live ingest 2026-10-28 (workspace-58, EVL-47): `fd-div-1b-c5-asan-t1-repair.ended` (sha256 `8fe11d2f966df747412edf9fa87c9bb3dee28abb2fbbf438c67f75ff8a691839`; est 1800 s, actual 133 s, 02:22:28Z..02:24:41Z, ratio 0.073889, rc=0, regions 78-95), 1 unit / 3 frames, grade Judged/Located (observation). Eligibility only: no planning-context canary has run, loop NOT claimed wired. A first ingest stamped as-of 00:00:00Z also reached the canonical ledger (`--ledger` placed after the subcommand), so this claim has duplicate frames (seq 38575-38577 and 38578-38580). [belief: clm_calendar-overrun:fd-div-1b-c5-asan-t1-repair:8fe11d2f966df747]
- [ ] **VB-EVL47-DUP-FRAME-SUPERSEDE — record a supersede for the duplicate `fd-div-1b-c5-asan-t1-repair` calendar-overrun frames.** (filed 2026-10-28, workspace-58 wrap-up) The canonical ledger holds the claim twice (seq 38575-38577 stamped as-of 00:00:00Z, and 38578-38580; file lines 38576-38581) because a ws58 subagent placed `--ledger` after the `ingest` subcommand. Append-only ledger: do not edit lines; append a supersede/retraction record for the 00:00:00Z frames through the leased writer, then verify the fold counts one claim. [no-belief: tooling-repair]
- [x] **VB-CLI-LEDGER-FLAG-GUARD — honor explicit ledger selection before opening any ledger or writer lock.** ✅ 2026-10-29 root `04b4d85a672e4901221e6a2d73328826fa475807`, integrated `c34d9ab79248197afae15e542c68fe7739508075`: both argument positions work; ingest-local selection wins when both appear. 301 tests cover public entry points and fallback precedence; 368 fixture tuples retain byte identity and grades. Constructor spies and temporary ledgers only, no canonical ledger writes. [no-belief: tooling-repair]
  - 2026-10-28 EVL-47 exact-record ingest (workspace-58, NI draft): the completed `fd-div-1b-c5-asan-t1-repair.ended` was privately ingested successfully (one tuple / three frames, no refusals); record and source hash fixed in `/mnt/raid0/llm/tmp/codex-ni-20261028-rtg54/rearm-r1/EVL47-OWNER-APPLY-DRAFT.md`. Supports eligibility/ingest only. The planning-context canary is partial: known row337 appears, but the calendar-overrun claim is absent from the unrelated Q38FN context and the repeat guard is null. EVL-47 is not retrieval-wired; the canary task stays open and no new measurement warrant is inferred. Existing source class and shared `claim_tuple.grade()` remain authoritative; no new ladder. [belief: cc]
- [x] **VB-CLBENCH-CACHE-WIRE — project the CL-Bench cache-hit report into claim tuples.** Filed 2026-10-22 (3c4ca599): no adapter exists for `epyc.clbench_cache_hit.v1` (checked `scripts/vidya/adapters/`, grep of the schema string across `scripts/vidya` and this program: no hits). The research `cache_hit_report.py --out` JSON (`/mnt/raid0/llm/tmp/cme7-poker-out/run-20261022T131252Z/clbench/cache_hit_report.json` is the first live record) is a measurement with no write-side hook. Wire the write side first: one tuple per (run, basis) for `hit_ratio_prompt_prefix` and `hit_ratio_reusable`, carrying the served model, recipe name, np, ctx, slots, kernel build, research SHA that produced it and `basis`, plus the `missed_split` buckets as separate OBSERVATION rows; `claim_tuple.grade()` decides. Acceptance: adapter-table row (added, see README) plus a fixture built from the 2026-10-22 record (0.7948 / 0.868 and the 11,028 / 1,743 / 14,058 split) that grades, and a producer `--belief-out` emit in `cache_hit_report.py`. Read-side caution: records written before research `08ace05fd` have no `basis` / `missed_split` fields and must not be back-filled; the 0.7948 record is a pre-fix layout measurement, not evidence about the fixed layout.
  - *(2026-10-24, 3c4ca599 subagent; landed by integrator)* Wired `clbench_cache_hit.py` (`clbench-cache-hit`) and research `cache_hit_report.py --belief-out` (+ identity flags, research_sha). 5 rows per report (two ratios + 3 missed_split observation rows); fixture restates the 10-22 counts (0.7948 / 0.868, 11,028 / 1,743 / 14,058) and grades; the pre-08ace05fd report yields no rows. Dry run on the post-fix s2 report: 5 rows / 15 frames, 0 refused. Box stays OPEN until the real ingest: `cd scripts/vidya && python3 cli.py ingest clbench-cache-hit --path <dir with sidecar> --as-of <ts> --only-new`.
  - *(2026-10-24, 3c4ca599.)* ✅ Real ingest by main from origin/main (root `3edf2ce13`, research `d0ebe05f5`): `cli.py ingest clbench-cache-hit` on the post-fix CME-7S report sidecar, 5 rows / 15 frames, 0 refused (prompt-prefix hit 0.9977).

- [x] **VB-PRODUCER-EMITS-1 — wire the PRODUCER-side emit calls the 2026-10-22 write sides need, before each producer's first run (3c4ca599).** ✅ 2026-10-22 HIL-15a driver `--served-model` + `--belief-sidecar` (orch branch `hil15a-flagon-fix-20261022` @51bcc77b; job repinned); HS-PROF-1 research branches `hsprof1-belief-write` and `vb-write-akpl-3c4ca599` pushed, `s5-hsprof1-beam_job.sh` repinned to `1d6359490` with EPYC_ROOT; RTE-PFX-2 recipe records window id / region-lock claim / UTC span / role, calls `rte_pfx2_capture` after rc=0, skips `-1`-timing trials with a reason (orch branch `lane/qb2-rtepfx2-20261021` @e6f3c8e4); Oolong records carry run_id, GGUF sha256, sampling params and the server's real prompt tokens (research main `6ddc19d4b`); D-RI-PREVIEW-1 driver calls the adapter after a complete non-mock result (orch main `8eaec813`). Evidence: `progress/2026-10/2026-10-22-producer-belief-emits.md`.
- [x] **VB-OBS-PROTOCOL-FIX — observation rows must carry an EMPTY `protocol_id` (never `observation:none` or the capture schema string).** ✅ 2026-10-22 `harness_improvement`, `hil15a_auc`, `repl_preview`, `toc_ab`, `skillbank_ab`, `ak_history` wrote a non-empty pseudo-protocol, so `grade()` returned Witnessed/Attested for rows with no ratified protocol. Writers now store `""`; projection re-maps legacy ids; tests assert Judged/Located. Ledger rows already written for these six source kinds: 0 (not rewritten). Same class still open in `chunk_kv`/`hs_prof1_profile_arms`/`ibench`: they store their capture schema as `protocol_id`; those carriers are measurement-class with their own owners, so each owner must say whether a ratified protocol applies.
- [x] **VB-YARN-AGG-EMIT — the yarn_gate runner must emit `epyc.yarn_gate_decision.v1` records and call `yarn_gate_agg.write_belief_measurements`.** ✅ 2026-10-22 research branch `yarn-native-gate-runner-20261022` @`46d26f626` (new `decision_records.py`): `arm_runner decide` builds per-(suite, task, REAL-length bin, zone) cell records (mean_score, no_answer_rate) and A1_vs_A0 verdict records (paired digests of the cell files) and calls the writer once per pass, FINAL only (INTERIM writes nothing); Oolong buckets split mixed zones instead of labelling them; `helmet_judged_cell.score_cell` emits judged cell records with `judge_pin` + `judge_validation` (from `judge_pin.json`) and `--emit-belief-dir`; ruler items are excluded WITH a reason (no schema slot). Failure is recorded in `decision.json` `belief_emit`, never fatal. Jobs repinned (`YG_RESEARCH_SHA=46d26f626de0`) while both pollers were idle. Evidence: `progress/2026-10/2026-10-22-final-producer-emits.md`.
- [x] **VB-YARN-AGG-RULER — add a `ruler` suite to `yarn_gate_agg.py` and make the research emitter stop excluding RULER items.** ✅ 2026-10-22 root adapter: `ruler` suite with `source_pins` = RULER checkout pin (`ab17b78`), `essay_sha256`, `words_source=essay_vocab_hyphen_pairs` and the non-empty local-generation `deviations` list; `comparable_to_published:false` kept; projection only, `claim_tuple.grade()` decides, empty protocol_id. Tests in `tests/vidya/test_yarn_gate_agg.py`. Research side: `decision_records.py` emits ruler cells and verdicts (see `progress/2026-10/2026-10-22-yarn-ruler-schema.md` for shas and the repin).
- [x] ✅ 2026-10-22 **VB-SPEECH-LISTEN-1 — write side for human speech listen/rating records (first record: CS-8.L, 2026-10-22).** The README row is in `scripts/vidya/adapters/README.md` (Human speech listen/rating checks). Add a record emitter so a listen-check export writes a self-hashed row (schema `epyc.cs8l_italian_listen.v1` fields, rating-docs sha256, kit-manifest sha256, rater label, per-metric direction: naturalness and intelligibility higher_better, WER lower_better) and projects it as an observation (empty `protocol_id`) through the existing `conversation-stack-measurement` adapter; extend that adapter only if a human-rating metric kind is missing, and do not write a grading rule. Backfill the 2026-10-22 aggregate once the emitter exists (its inputs are hashed, so the backfill is exact). Before the next listen check (CS-8.L re-run after CS-8.L1/L2, or CS-8.G1B de/fr).

## Research intake 2026-10-22 — SLQ / IST-DASLab / kaitchup Qwen3.8-27B SLQ (intake-2461..2493)

Source: research intake session intake-ist-slq-20261022, Stage-3 plan `/mnt/raid0/llm/tmp/intake-ist-slq-20261022/stage3/STAGE3_PLAN.md` (sha256 db108374cd1bd164e5baaac2586b9d3abf26daaba46aec4085192e4b0c0232ad); operator ruling 2026-10-22 approved a subset. Trigger prose and knowledge notes from that plan are still pending the operator and are not filed here.

- [x] **VB-QUANTCMP-WIRE — write side for quant-comparison receipts (KLD, same-top-1, EAR, DFlash2 acceptance) before the first EAR-bearing run (EXL3-EAR1).** (filed 2026-10-22 via research intake, operator-approved 2026-10-22, intake-2461#record) Add a source-table row in scripts/vidya/adapters/README.md and an adapter projecting each llama-perplexity KLD run into a ClaimTuple carrying model and base file sha256, corpus, ctx, chunks, the EAR variant (full-vocab or top-10 renormalized) and HIP residency proof; the existing grade() decides, no new ladder.
  - 2026-10-22 (workspace-58): landed. `scripts/vidya/qwen4exp_quality_capture.py --mode kld-quantcmp` extends the SC54 receipt (no new adapter, same source kind and ingest source): native `Same top p`, `EAR full vocab`, `EAR top10 renorm` (each EAR tuple carries its `ear_variant`), the native Pinsker check re-derived by the reader, `--substrate cpu|hip` with residency proven during the child (loaded ggml backend objects + per-PID KFD VRAM, two-sample rule), optional DFlash2 acceptance (`--acceptance-log` + `--drafter-model` + `--acceptance-server-binary`, its own tuple, server custody stated as not captured). Tuples carry model, base-model and base-logits sha256, corpus sha256, n_ctx, chunks, binary sha256. Strict reader extended and re-pinned (`407af3fe7172`); `scripts/vidya/adapters/README.md` row updated. Controls: `tests/vidya/test_vb_quantcmp_wire.py` 16/16 (incl. anchor + candidate through the real writer, parsing the exact EXL3-EAR1 output format), SC54 42/42, ingest + claim_tuple green. No live capture yet.
- [x] **VB-QUANTCMP-NEW10 — land NEW-10's FAIL as belief tuples; its job-written receipt does not ingest.** NEW-10 (`iqk-iquant-enablement.md`) wrote `/mnt/raid0/llm/tmp/new10-q38fn-20261022/out/quantcmp_receipt.json` as a hand-rolled `epyc.quantcmp.receipt.v0`. The strict reader refuses it (`qwen4exp_quality_reader.read_project` → `ValueError: unsupported receipt schema`, checked 2026-10-22): it accepts only `epyc.vidya.qwen4exp_quality_measurement.v1` from `qwen4exp_quality_capture.py`, which proves residency while the child runs, so a post-hoc translation would invent warrant. Fix: re-run NEW-10's two KLD steps through `qwen4exp_quality_capture.py` (`--mode ppl-anchor` on UD-IQ4_XS, then `--mode kld-quantcmp --substrate cpu` on GSQ IQ3_XXS, with the same corpus, c512/b512/40 chunks, `GGML_FUSED_DECODE_OFF=1` and v10 store binaries). That is about 15 min of CPU correctness work on one quarter. It must run before NEW-13-RM deletes the IQ3_XXS weights. Rule for later quant-comparison jobs (NEW-13 included): call the capture tool, and do not hand-write a receipt. Done when the ledger holds the G1-G3 tuples for this run and they match `RESULT.json` within rounding. (filed 2026-10-22, workspace-58 wrap-up)
  ✅ 2026-10-23 — captured and INGESTED. The capture ran as the first two steps of the NEW-13 job (10:06-10:12Z, 0-95 grant): `vbqa` (`--mode ppl-anchor`, UD-IQ4_XS) and `vbqk` (`--mode kld-quantcmp --substrate cpu`, GSQ IQ3_XXS), both rc 0, both accepted by `qwen4exp_quality_reader` (`out/vb-capture/reader-check.txt`: 1 + 20 ClaimTuple rows; `VBQ_STATUS ok`). Receipts: `/mnt/raid0/llm/tmp/new10-q38fn-20261022/out/vb-capture/new10-vbq-a1-{anchor.anchor,cand1.candidate}.quality.json`. Ingest (workspace-58 wrap-up): `python3 scripts/vidya/cli.py ingest qwen4exp-quality-measurement --path <anchor> --path <candidate> --as-of 2026-10-23T13:55:00Z --only-new` → units 2, projected 2, refused 0, **21 rows, 63 frames** into the canonical ledger; an identical `--dry-run` re-run skips all 63 (idempotent).
  - **Deviation from the done-criterion, stated rather than hidden: the values match `RESULT.json` within the native ±1σ spread, not within rounding.** The capture tool's `kld-quantcmp` mode needs the native EAR rows, which only the EAR build prints (`experimental/ear-kld-column-20261022` @ `782c11ae4`), and the reader requires anchor and candidate to share one producer binary. So both passes ran on that build, at `-t 96` on 0-95; NEW-10 ran the v10 store binary at `-t 24` on q3. Capture vs NEW-10: G1 mean ln-PPL ratio 0.0215 ± 0.0099 vs 0.0150 ± 0.0100; G2 mean KLD 0.3206 ± 0.0070 vs 0.3222 ± 0.0070; G3 same-top-1 82.77% ± 0.37 vs 82.88% ± 0.37; anchor PPL 2.9868 vs 2.9925. The verdict re-derives identically (G1-G3 all FAIL their bars ≤ 0.005 / ≤ 0.1045 / ≥ 88.55%). The ledger tuples carry the EAR binary's identity, so nothing is attributed to the v10 store binary.
- [x] **VB-NEW13-WIRE — write side for NEW-13-class weight-handoff receipts (filed 2026-10-23, workspace-58 wrap-up; harness subagent's finding).** NEW-13 (`iqk-iquant-enablement.md`, PASS 2026-10-23) wrote `/mnt/raid0/llm/tmp/new13-weight-handoff-20261022/out/handoff_receipt.json` as a hand-written `epyc.new13.receipt.v0` (keys: weights P/D shard sha256, reference choice + sha, passages manifest/binary sha + n, harness branch @ `6b3ac87fe`, tool sha256, store, env, backend, metrics KLD/R/R_ci95/G0_gap, PREDECLARED sha). No strict reader accepts it, and a post-hoc translation would invent warrant the run never captured (same lesson as VB-QUANTCMP-NEW10). Fix: either extend `qwen4exp_quality_capture.py` with a `--mode weight-handoff` that wraps `llama-weight-handoff` and proves CPU residency during the child, or add a dedicated adapter reading a capture-written receipt; per-arm KLD, R with its paired-bootstrap CI and Gate 0 become ClaimTuples; `claim_tuple.grade()` decides, no new ladder. Source row added to `scripts/vidya/adapters/README.md`. Needed before C-L3 runs, so C-L3's receipt is captured, not hand-written. NEW-13's own v0 receipt is pre-hook and is NOT backfilled. Done when a dry capture of a tiny-model handoff projects through the strict reader and C-L3's job calls it. ✅ 2026-10-24 — qwen4exp_quality_capture.py --mode weight-handoff + weight_handoff_capture.py; adapters/weight_handoff.py over a hash-pinned weight_handoff_reader.py (READER_SHA256); ingest `weight-handoff`.
- [x] **VB-LB7-STALL-WIRE — adapter for the UFH14-LB7 stall-attribution records (filed with the write side 2026-10-23).** Project `VERDICT.json` + per-session `*.attrib.json` (`/mnt/raid0/llm/tmp/f8-launchers-20261023/locals-ufh14-lb7-stall/out/`) into ClaimTuples (protocol from PREDECLARATION.md, n = valid ABBAAB pairs, build sha from RUN_RECORD); `claim_tuple.grade()` decides; no grade for INCOMPLETE / INSTRUMENT_FAIL. Source row in `scripts/vidya/adapters/README.md`.
  - ✅ 2026-10-24 (workspace-f8 vidya batch). `scripts/vidya/adapters/ufh14_lb7_stall.py` (`cli.py ingest ufh14-lb7-stall --path <launcher dir>`: VERDICT/RUN_RECORD sit in the launcher dir, not `out/`), tests `tests/vidya/test_ufh14_lb7_stall.py` (18). Per-session turn-2+ summaries re-derived from `per_turn`, the aggregate (pair deltas, gates, verdict word) re-implemented from `lb7_parse.aggregate` and matched exactly (UNATTRIBUTED). Six tuples: median ON-minus-OFF client-gap delta 38.973 s, four group deltas, ON copy-throughput 0.117 GiB/s; reps = 3 valid ABBAAB pairs; scope from the ON preflight (pid owns KFD VRAM, build `49550eda5`). `protocol_id` left empty (harness-local PREDECLARATION.md, sha in `extra`; same rule as spec_rng/pb_hol/gpu_cpu_noise), so Judged/Located. INCOMPLETE / INSTRUMENT_FAIL decline. INGESTED 2026-10-24: 6 rows, 18 frames.
- [x] **VB-PBQ-1 — wire the PB-QCOST-1 prefill-cost records as belief tuples (filed 2026-10-23, workspace-f8 offline re-analysis).** Source row added to `scripts/vidya/adapters/README.md`. Project `pb_qcost_1.jsonl` / `summary.json` from `/mnt/raid0/llm/tmp/pb-qcost-1/runs/20261021T212922Z/` (sha256 `a82cdf93...` for the jsonl) into ClaimTuples: per-n intercept, c-slope, noise floor, held-out P99 abs residual, each with unit (ms per server iteration), n generating slots, q held fixed, `-np`, binary sha and argv from the run's `port_ownership` record. Carry the INDICATIVE grade and the single-q caveat in `applicability`; do not grade. Write side: the confirm run (PB-QCOST-1 confirm) should emit `belief_measurements.jsonl` itself. Reuse `docs/design/pb-qcost-1-results-20261023.md` as the cross-check (it reproduces the run's own summary to the printed precision).
  - *(2026-10-24, workspace-f8 read-out.)* A second PB-QCOST-1 record set now exists, from the confirm run: `/mnt/raid0/llm/tmp/f8-launchers-20261023/pb-qcost-1-confirm/`.
    - Files: `out/run/pb_qcost_1.jsonl`, `VERDICT.json` (label `confirm CONFIRMED; q axis PASS; grade INDICATIVE`), `RUN_RECORD.json`, and `out/sibling_load.csv` + `out/sibling_summary.json`. The rule is PREDECLARATION.md sha256 `f45aef1a43976af3d707aea4e7d61875a83e343ec726a61e1725316b385d3e06`.
    - The run did NOT write `belief_measurements.jsonl`, so the write-side ask above is still open.
    - No adapter covers either record set. Dry run 2026-10-24 with `--as-of 2026-10-24T08:00:00Z`: the closest kind, `pb-hol`, declines the run directory (matched 1, projected 0).
    - Widen this task to project the confirm run as well. Add per-n b (ms/token) and d (ms per token x cached token) with their CIs, and the per-phase proofs. The INDICATIVE grade and its cause (the sibling-summary path defect) must ride along in `applicability`.
  - *(2026-10-24, f8, branch `f8/vidya-wire-1024`.)* The read side is done for both record sets: `adapters/pb_qcost.py` (`cli.py ingest pb-qcost`), tests in `tests/vidya/test_pb_qcost.py`.
    - The original run gives 8 tuples: intercept, c-slope, noise and held-out P99 per n=1,4. The confirm run gives 18: the same four from ub-512, plus q-axis a/b/d/noise/P99 with the producer's bootstrap CIs.
    - Everything is refit from the jsonl with the producer's own fit code, and the proofs are recomputed. The reader refuses on any difference.
    - INDICATIVE and its cause ride in `applicability.recipe` and `extra`. Grades are Judged/Located.
    - Dry runs: original gives matched 1, projected 1, rows 8, frames 24. Confirm gives matched 1, projected 1, rows 18, frames 54.
    - **Left (write side):** neither producer emits `belief_measurements.jsonl`. The next PB-QCOST run must write one itself, with its grade cause in words; the confirm's VERDICT states no cause, so the adapter derives it from the missing sibling-summary path.
  - ✅ 2026-10-24 (workspace-f8 vidya batch). Write side: research `f8/pb-qcost-write-20261024` @ `623d4ec98` adds `scripts/benchmark/pb_qcost/` (byte-identical pinned copies of both drivers + `emit_belief_measurements.py`, a post-hoc emitter: self-hashed `epyc.pbqcost1.belief_measurement.v1` rows, numbers re-derived with the drivers' own functions, grade cause in words, exit 3 on any disagreement; 9 tests). Root `pb_qcost.py` reads `belief_measurements.jsonl` when present and checks it row for row against its own refit (a `readout` file clears retrofit, a `backfill` file keeps it); confirm-R verdict shape and amendment digest handled. Both existing runs INGESTED 2026-10-24 (no sidecar, retrofit): 8 + 18 rows, 24 + 54 frames. The ARMED `pb-qcost-1-confirm-r` read-out must call, after job.sh writes VERDICT/RUN_RECORD: `/usr/bin/python3 -B <research>/scripts/benchmark/pb_qcost/emit_belief_measurements.py --run-dir /mnt/raid0/llm/tmp/f8-launchers-20261024/pb-qcost-1-confirm-r --out /mnt/raid0/llm/tmp/f8-launchers-20261024/pb-qcost-1-confirm-r/belief_measurements.jsonl` then `python3 scripts/vidya/cli.py ingest pb-qcost --path /mnt/raid0/llm/tmp/f8-launchers-20261024/pb-qcost-1-confirm-r --as-of <now> --only-new` (`<research>` = `/mnt/raid0/llm/worktrees/f8-pb-qcost-write` until the branch merges).
    - *(2026-10-24, workspace-f8 main; merge record.)* Research `f8/pb-qcost-write-20261024` @ `623d4ec98` MERGED to research main as `759a20113` (reviewed MERGE, LOW risk). `<research>` above can now be any research checkout at or after `759a20113`.

- [x] **VB-M4-PBHOL-WIRE — adapter for the M4.2 PB-HOL-1-on-candidate records (filed 2026-10-24, workspace-f8 read-out).** `cli.py ingest pb-hol --path .../m4-srpf-pbhol/out --dry-run` matches 6 phase dirs and declines all 6 (0 projected): the adapter only knows the PB-HOL-1 arm names and the producer's own verdict. Extend `adapters/pb_hol.py` (or add a sibling) to read the phase-suffixed arms and the launcher `VERDICT.json` from `verdict.py`: one claim per C1 phase (B/A short-TTFT medians, n = valid reps), C2 off-identity, C3 byte identity with the champion-determinism control; invalid runs stay rows with their reasons; protocol = PREDECLARATION.md sha; scope from the argv readback. `claim_tuple.grade()` decides; no grade for INCOMPLETE; no new ladder. Source row in `scripts/vidya/adapters/README.md`.
  - 2026-10-29: recut C1 native verdict and raw phase records are available at `/mnt/raid0/llm/tmp/codex3-gpu-ready-20261029/attempts/run-20261029T172159321082012/`. Existing M4 PB-HOL projection covers phase-suffixed arms, but this recut's C1-only verdict shape has not been verified against the adapter; projection readiness is unverified, no ingest claimed. Filed C1 conclusion is a committed-conclusion candidate. [belief: cc]
- [ ] **VB-M4-RECUT-C3-WIRE — verify the recut C3 diagnostic source and design a future eligible producer.** Confirm read-only PB-HOL projection against real output from `/mnt/raid0/llm/tmp/codex-m4-c3-original-20261028/attempts/`, including exact prompt/pass coverage, verdict consistency and rejection of incomplete or tampered phases. For a future non-diagnostic prospectively enrolled producer, capture condition, prompt/pass, binary/model, launch environment and grant identity, native rows and verdict/input bindings at write time; use the existing grading ladder and verify the planning-context canary. Do not add diagnostic receipts or invent a historical measurement warrant.
- [ ] **VB-M4-ORDER-DIAGNOSTIC-WIRE — register the controlled-arrival-order source.** Verify read-only projection of the actual diagnostic records from `/mnt/raid0/llm/tmp/codex-m4-order-diag-20261028/`, including admitted order, client overlap, repeated pairs, invalid output and native token/text evidence. For any future eligible non-diagnostic producer, design write-side capture and a planning-context canary with the existing grading ladder; do not create diagnostic receipts or infer causal or promotion warrant. Also cover the separately recorded speculative-on/off diagnostic `/mnt/raid0/llm/tmp/codex-m4-order-spec-diag-20261028/`, preserving requested and actual server configuration and the limits of any null result.
- [ ] **VB-LB49-DS41-DIAGNOSTIC-WIRE — register the revised LB4.9 DS41 diagnostic source.** Preserve actual source/build/library/model and grant identities, arm argv, native results, raw logs, and partial/refusal/cleanup evidence from `/mnt/raid0/llm/tmp/lb49-r11-source-draft-20261028/job.py` SHA-256 `7c5b88eb8be243168f6dea172313eac404b289215ae21e62333fb1782d2b44b2`. The scheduled diagnostic uses canonical DS41; the small Gemma R11 smoke does not establish DS41 behavior or admission. Verify strict read-only projection and planning-context canary for any future eligible producer using the existing ladder; no diagnostic seal, receipt, retrospective measurement warrant, or speed, route-coverage or promotion claim from a smoke.
  - ✅ 2026-10-24 (f8, branch `f8/vidya-wire-1024`): `pb_hol.py` reads M4.2 phase dirs, with the launcher VERDICT/RUN_RECORD/PREDECLARATION re-hashed and the verdict partition re-derived. Each phase gives one claim:
    - C1 srpf512 / srpf2048: 0.997x / 0.994x, n=3 valid, PASS.
    - srpf2048cap0: informational.
    - C2 off512: NOT_MEASURED, no value, 3 invalid runs with reasons.
    - C3 on comp-m4off: 5/5 byte-identical.
    - comp-champion control: 5/7.
    - `protocol_id` is empty and no outcome is given while INCOMPLETE; all claims are Judged/Located.
    - Dry run `m4-srpf-pbhol/out`: matched 6, projected 6, refused 0, rows 6, frames 18. Original `pb-hol-1/runs` is unchanged (2 units, 3 rows).
    - Tests in `tests/vidya/test_pb_hol_m4.py`.
- [ ] **VB-CAFE1 — capture the CAFE-1 frontdoor MTP p-min timing sweep before its first measured run.** A native producer records the frozen binary/libraries/model/recipe, prompt identities and classes, each fresh-server birth and actual whole-host timing grant/CPU/NUMA placement, paired arm/order, request tokens, decode timings/acceptance, matched baseline and within-window A/A floor, identity comparisons, and every failed/aborted/unknown attempt. A small no-MTP control qualifies launcher mechanics only. Project the native source through the existing shared `claim_tuple.grade()` ladder; no new grade rule, invented warrant or backward reconstruction. Tests cover paired arms, required window floor, identity mismatch, interrupted unknown and drift; run the planning-context canary before calling this source wired.

- [x] **VB-SPEC-RNG-1-2-WIRE — adapter for the SPEC-RNG.1.2 poskey depth-invariance records (filed 2026-10-24, workspace-f8 read-out).** Project `/mnt/raid0/llm/tmp/f8-launchers-20261023/spec-rng-1-2-gpu-run/` (`out/records.jsonl`, `out/verdict.json`, `VERDICT.json`) into ClaimTuples: one per comparison (P3/P7 primary, C3/C7/X0 controls; min p vs Bonferroni threshold, n per cell), acceptance per depth, and the probe (net_gain, sign p); the strict reader re-derives the chi-square and acceptance statistics from the request rows and refuses on a difference; `decided_proposition` = the verdict word with its rule sha `0af228a0...`; INDICATIVE correctness, no throughput value. `claim_tuple.grade()` decides; no new ladder. Write side: the runner (`f8/spec-rng-1-2-runner`) should emit `belief_measurements.jsonl` on its next use. Source row in `scripts/vidya/adapters/README.md`.
  - *(2026-10-24, f8, branch `f8/vidya-wire-1024`.)* The read side is done: `adapters/spec_rng_1_2.py` (`cli.py ingest spec-rng-1-2`), tests in `tests/vidya/test_spec_rng_1_2.py`.
    - Each valid run gives 8 verifier-class (unbound) observations: 5 comparisons, acceptance at depth 3 and 7, and the probe. Each carries `decided_proposition` = the verdict word plus the rule sha.
    - Every statistic, gate and the verdict is re-derived from `out/records.jsonl` (stdlib chi-square, Welch and sign tests). The reader refuses on any difference.
    - Grades are Judged/Located; no throughput is projected; INCONCLUSIVE runs are declined.
    - Dry run: matched 1, projected 1, refused 0, rows 8, frames 24.
    - **Left (write side, research):** the runner emits `belief_measurements.jsonl` on its next use, and its verdict files carry the rule sha and an ISO timestamp.
  - ✅ 2026-10-24 (workspace-f8 vidya batch). Write side: research `f8/spec-rng-1-2-write-20261024` @ `116d31c33` (from `f8/spec-rng-1-2-runner`): `analyze` stamps `out/verdict.json` with the full predeclaration sha and an ISO-8601 UTC `analyzed_at`, `--summary <path>` writes the top-level VERDICT.json with the same stamps plus records/verdict sha256, and `out/belief_measurements.jsonl` gets 8 self-hashed rows (none for INCONCLUSIVE); 27 runner tests. Root `spec_rng_1_2.py` verifies the stamps and the sidecar row for row when present; legacy runs read as before. The 10-23 run INGESTED 2026-10-24 (retrofit): 8 rows, 24 frames. For the next launcher: its job.sh calls `analyze ... --summary $HERE/VERDICT.json` instead of writing VERDICT.json itself. Request rows still carry epoch times and no model sha (runner owner).
    - *(2026-10-24, workspace-f8 main; merge record.)* Research `f8/spec-rng-1-2-write-20261024` @ `116d31c33` MERGED to research main as `58ce732e8` (reviewed MERGE, LOW risk).


## Producer write-side wiring, 2026-10-23 (session 3c4ca599)

- [x] **VB-GPU-LEAK-WRITE — GPU-LEAK-1 / 1d VRAM-slope probes (filed and landed 2026-10-23).** Per-arm own-PID VRAM slope (and the 1d segment slopes) as OBSERVATION tuples; slopes re-derived from the recorded series on read, producer verdict carried verbatim, `grade()` decides. ✅ 2026-10-23 — `scripts/vidya/adapters/gpu_leak_probe.py` (`cli.py ingest gpu-leak-probe`), `tests/vidya/test_gpu_leak_probe.py`; both existing records ingested (`gpu_leak_probe.beliefs.jsonl` beside each RESULT.json): GPU-LEAK-1 2 rows / 6 frames, GPU-LEAK-1d 6 rows / 18 frames. Source-table row in `scripts/vidya/adapters/README.md`.
- [x] **VB-FUSED-DECODE-DIV-WIRE — adapter for the FD-DIV-1a smoke receipt (filed 2026-10-23, workspace-58 wrap-up).** `/mnt/raid0/llm/tmp/fd-div-1a-20261023/out/fd_div_1a_receipt.json` (schema `epyc.fd_div_1a.smoke_receipt.v1`, written by `fd_div_1a_job.sh` + `analyze.py`) carries per-smoke byte-identity checks (output sha256 test vs ref, first_diff_byte), the abort signature of the v10 fused-ON control, and descriptive decode ms/token. Project each smoke's identity check as a categorical correctness claim with `decided_proposition` naming the identity decided (never a bare PASS), the pass rule `PREDECLARED.json` sha256 `02251f47...` and subject/base commits as the attestation; decode ms/token as OBSERVATION only. Verifier projection (no new ladder) plus a `cli.py ingest` name. Done when re-ingesting the receipt yields one claim per smoke. Source-table row filed. ✅ 2026-10-24 — adapters/fused_decode_div.py (verifier class), ingest `fused-decode-div`; real receipts project 6 claims (FD-DIV-1a S1/S2; FD-DIV-1b ctl + 3 w cells).
- [x] **VB-LB49-COMBINED-DIAGNOSTIC-WRITE — prospectively wire the combined LB4.9 op-case and teacher-forced diagnostic source.** Capture exact native op-case rows and inputs, independent baseline generation plus fresh-KV repeat, pinned token IDs, separate feature-on forced replay, prompt/position/margin joins, model/build/library/source/grant identity, partial/refusal/error state and child cleanup at write time. Project only captured native records through the existing measurement carrier and `claim_tuple.grade()`; no new source-class ladder and no retrospective warrant from the Gemma smoke. Add strict read-only reader/refusal controls and prove the complete planning-context canary before calling the source wired. ✅ 2026-10-30 — `scripts/vidya/adapters/lb49_combined_diagnostic.py` and `cli.py ingest lb49-combined-diagnostic` prospectively project producer-authored `native.json` / `beliefs.jsonl` through the existing measurement carrier/grade, with empty protocol and one native-launch rep (Judged/Located). Deterministic QKV/mask/sink inputs are explicitly **DECLARED_BY_PINNED_SOURCE**, never claimed as observed buffers; source/model-pin/build/grant identities are declared prospectively, while actual mapped ELF/DSO and PID/birth/affinity/KFD proofs are captured during the native window, with partial/refusal/error and cleanup retained. Installed CLI ingested the new Gemma smoke's 68 rows / 204 private-ledger frames; repeat `--only-new` emitted 0; 13 strict refusal controls passed. Actual AutoKernel `belief_context.prepare` → ROOT reader child → `actors.render_context` displays four model/positions2/prompts1/mode-qualified mechanisms plus tried history, with Gemma-only plumbing and positions-not-launch-replicates caveats. The actual DS41/65-position/3-prompt negative canary has **no claim IDs and no tried mechanisms**. Final same-source native cutoff is rc75/partial with captured-child cleanup; keeper accepted the corrected own READY row at 16:53:40Z (rank5, 739GiB/7200s), actual poller retained dynamic CPUs and diagnostic environment. Evidence: `/mnt/raid0/llm/tmp/codex-ni-lb49-write-wiring-20261030/INSTALLED-VERIFICATION.json`, `REVIEW.md`, `KEEPER-FINAL.json`. **Subsequent full DS41 event:** all native phases completed but the original aggregate refused rc1 because the reader compared the requested entry to the first nine-shard pin-map key. Original `REFUSED.json`, native record, declaration and source bytes remain immutable; selection now joins the original pinned job/PLAN/native argv to the complete pin set, and future declarations explicitly record `selected_entry_model`. Arbitrary token-display bytes are preserved while ASCII log-framing markers decode safely. Separate **projection-only** recovery revalidated every original source/window/cleanup/opcase/metadata/token/prompt/position/metric join and yields 840 observations / 2520 private-ledger frames; actual installed CLI reingest emits 0. Actual DS41 selected-entry `00001` / 65-position / 3-prompt planning canary displays four scoped mechanisms and original-rc1 caveats; Gemma cross-model negative is empty, and the original Gemma-positive / DS41-negative controls still pass. Nine pin-order permutations, a wrong-selected-entry negative and raw-byte log framing are covered by the 19 passing dedicated tests. Evidence: `/mnt/raid0/llm/tmp/codex-ni-lb49-write-wiring-20261030/recovered-original-20261030/INSTALLED-RECOVERY-VERIFICATION.json` and `original-before-model-join-fix/archive.json`. This closes native write/read/planning plumbing only; scientific FU acceptance belongs to its result filer, and no scientific algorithm, NMSE5e-4 threshold, sink-fold, timing or promotion authority changed. [belief: cc]
- [ ] **VB-LB49-CLI-REPEAT-WIRE — extend the existing LB4.9 diagnostic measurement family for the distinct FU-DIVERGE-03 CLI repeat.** Capture prospectively at its native producer boundary each baseline-repeat and candidate arm, original argv, per-arm binary/library and nine-shard model identities, raw output bytes, return status, interruption/unknown and child cleanup. Preserve the distinction between prompt display and generated bytes; do not infer a template or output identity from READY or control smokes. Extend the existing carrier and shared `claim_tuple.grade()` with strict source/arm/model and partial/refusal tests; prove the planning-context canary before calling this CLI instance wired. The combined op-case/teacher-forced source is already wired; its canary does not cover this separate CLI producer. No historical tuple graft, new ladder, threshold, fold, timing or promotion claim. Source row: `scripts/vidya/adapters/README.md`.
- [ ] **VB-FOLDGATE-WRITE — write side for the champion fold gate (CH-28; filed 2026-10-23).** Outputs `/mnt/raid0/llm/tmp/ch28-fold-20261023/gate_{cpu,gpu}.v2.out` + `GATE_ACCEPTANCE.md` are text. The reusable tool is being written under research `scripts/kernel_rnd/fold_gate/`; it must emit, per library, a record (soname stem, verdict class IDENTICAL/EXPLAINED/EXPECTED/CODE-DIFF, code-identical flag, differing sections) plus the accepted exception as its own record with the acceptor named, the base/new store paths and their SHA256SUMS digests as the attestation, and a `decided_proposition` that states the identity decided (never a bare PASS). Then an adapter on the verifier projection (precondition, no new ladder) and a `cli.py ingest` name. Done when the next fold's gate run ingests one claim per library. Source-table row filed.
- [ ] **VB-V11-ORACLE-WRITE — V11-086 FP32-oracle rerun (filed 2026-10-23; adapter and scorer hook landed, first real record pending).** ✅ 2026-10-23 adapter `v11_oracle_rerun.py` (`cli.py ingest v11-oracle-rerun`), `tests/vidya/test_v11_oracle_rerun.py`, and the scorer `fa086v2_oracle_rerun.py` now writes `v11_oracle_rerun.beliefs.jsonl` beside `ORACLE_RERUN.json` (best effort; edited via `.new`/`mv`, no process running it). Remaining: after the rerun produces `ORACLE_RERUN.json`, confirm the sidecar exists (8 rows) and run `python3 scripts/vidya/cli.py ingest v11-oracle-rerun --only-new --as-of <now> --path /mnt/raid0/llm/tmp/v11-runs/086v2/fp32oracle/v11_oracle_rerun.beliefs.jsonl`; if the scorer's WARNING says the adapter was not found (root not yet synced), run the printed manual command first. External event: the rerun.
- [ ] **VB-DS41-W5D-WRITE — DS41-W5d 1017 baseline + MUL_MAT_ID microbench (filed 2026-10-23; post-processor and job hook landed, first real record pending).** ✅ 2026-10-23 adapter `ds41_w5d.py` (`cli.py ingest ds41-w5d`), `tests/vidya/test_ds41_w5d.py`; `analyze.py` untouched (sha-pinned by `PREDECLARED.md`), `job.sh` `finish()` calls the post-processor non-fatally (`.new`/`mv`, backup kept, `bash -n` ok, pins re-verified). Remaining: after the 2026-10-24 10:00Z run, confirm `out/ds41_w5d.beliefs.jsonl` and run `python3 scripts/vidya/cli.py ingest ds41-w5d --only-new --as-of <now> --path /mnt/raid0/llm/tmp/ds41-1017-baseline-mmid-20261023/out/ds41_w5d.beliefs.jsonl`. External event: the run.
  - Prospective DS41-W5d.1 successor instance: extend this existing `ds41_w5d.py` family for `/mnt/raid0/llm/tmp/codex3-wholehost-20261031-0310/full/`, preserving native pre-compute declaration/source/binary/model/grant capture, retained warmup, six fixed pp512/tg128 sample units, quiet/residency windows, interrupted/invalid units, the unchanged original strict validity verdict and separate W5d.1 tg128-CV condition. Project complete native attestations through `ClaimTuple.grade()`; refuse missing/tampered/mixed/retrospective inputs and validate the existing source-family planning-context canary before calling this instance wired. Native raw capture is implemented; full inference and projection remain unproven. No new source ladder or historical warrant.

- [x] **VB-MOE-ROUTING-WIRE — write side and adapter for the INF-72 RT-1 routing-trace analyses (filed 2026-10-23, 3c4ca599).** Source row added to `scripts/vidya/adapters/README.md`. Project the analysis records (`skew_report.json` per-layer top-10/25 % share with held-out and null, `residency_curve.json` h(k) per (A, B, k), `placement_replay_*.json` per-arm max/mean with CI, `locality_report.json` IR_t / LRU / co-activation) from research `data/moe-routing-rt1-q38fn-20261023/` into measurement tuples whose scope carries model file, arch, workload corpus sha256, phase, chunk size, calibration source and `n` (windows / steps); add a `content_sha256` + input-trace `ids_sha256` list to each analysis JSON on the write side now (the scripts do not yet emit them) so the read side never re-derives scope. Re-run for the Qwen3.6 frontdoor trace (RT-9) and DS41 (RT-10) through the same adapter. Do not write a new grading rule (`claim_tuple.grade()` decides). Done when `cli.py ingest moe-routing` ingests the Q38FN set and a re-ingest with `--only-new` is a no-op.
  - *(2026-10-23, 3c4ca599, RT-9.)* The RT-9 analysis set now exists and is the second input for this adapter: `/mnt/raid0/llm/tmp/roi-prep-20261023/INF-72-RT1/analysis-q36/` (`rt5_skew`, `rt6_placement`, `rt7_residency`, `locality`, `validation.json`; traces `.../results-q36/`, 256 experts, top-8, scope arch `qwen35moe`). It still lacks `content_sha256` / `ids_sha256` on the write side, so it is not yet ingestable; the Q38FN-only done criterion should be widened to both models.
  - *(2026-10-24, 3c4ca599 subagent; landed by integrator)* Producer stamp (`content_sha256`, `input_traces` with ids_sha256, `analysis_kind`) in the four research moe_routing analyses; `moe_routing.py` reader (`moe-routing`). Dry-run: Q38FN 309 rows / 927 frames, 0 refused; committed pre-stamp JSONs yield 0 rows; Q36 (RT-9) also 309 rows from regenerated JSONs (scratch-moe/q36). --only-new no-op is unit-proven via claim identity (content_sha256 + metric + scope). Box stays OPEN until real ingest and the re-ingest no-op check. Owed: RT-10 (DS41) has no traces yet; Q36 code shards carry guard sub_chance_checks 1-2 (fatal 0), counted in scope. Real: put stamped JSONs (scratch-moe/q38fn) in a dir, `python3 scripts/vidya/adapters/moe_routing.py write --analysis-dir <dir>`, `python3 cli.py ingest moe-routing --path <dir> --as-of <ts> --only-new`, then repeat to confirm no-op.
  - *(2026-10-24, 3c4ca599.)* ✅ Real ingest by main: `cli.py ingest moe-routing --only-new` on the stamped Q38FN (309 rows / 927 frames) and Q36 RT-9 (309 / 927) analyses, 0 refused; a repeat Q38FN ingest skipped all 927 frames (no-op proven on a real second ingest). RT-10 (DS41) still has no traces.

## Producer write-side wiring, 2026-10-24 (workspace-f8 read-out)

- [ ] **VB-GNX-REINDEX-1 — classify the GitNexus re-index receipt as dependency evidence (filed 2026-10-24, workspace-f8 read-out of `nib2-gnx1-reindex`).**
  - Record: `/mnt/raid0/llm/tmp/f8-launchers-20261023/nib2-gnx1-reindex/RESULT.json` (state, head sha, analyze rc, backup, restore), plus `out/status.clean.txt` and `out/analyze.out`. Producer: `job.sh` sha256 `8b204799...`.
  - It is a verified finding about tool state (index fresh at a commit), not a measurement. So, as with the NI52 code-intelligence row, it is dependency evidence: no ClaimTuple projection and no `evidence_supports_claim` until a shared dependency warrant rule exists.
  - Remaining: have the next re-index job write a self-hashed receipt (repo, branch, indexed commit, origin/main at read time, node/edge counts, gitnexus version) so that orchestrator impact checks can cite index freshness by sha.
  - Source row added to `scripts/vidya/adapters/README.md`.
  - *(2026-10-24, f8, branch `f8/vidya-wire-1024`.)* The write-side tool now exists: `scripts/gitnexus-index-receipt.py` (`epyc.gitnexus.index_receipt.v1`, test `tests/test_gitnexus_index_receipt.py`).
    - It is self-hashed with `content_sha256`. It reads the repo, branch, indexed commit, indexedAt and the node/edge counts from the index's own `.gitnexus/meta.json`, and records that file's sha256. It also records git HEAD, `origin/main` (the local ref, no fetch), the gitnexus version and the job RESULT sha.
    - First receipt for this re-index: `/mnt/raid0/llm/tmp/f8-launchers-20261023/nib2-gnx1-reindex/out/index_receipt.json`. Its meta.json `indexedAt` is the job's 01:09:19Z, the index is fresh at HEAD `fd1a894`, and the clone's origin/main `26affbf` is 2 commits ahead.
    - Left: the next re-index job calls the tool after `gitnexus-analyze.sh` returns 0. That is an external event: the next re-index.
  - *(2026-10-24, workspace-f8 vidya batch; box stays open.)* Waits on one event: the ARMED `/mnt/raid0/llm/tmp/f8-launchers-20261024/nib2-gnx1-reindex-2/` run (not edited). Its read-out, after `RESULT.json` reports PASS, runs from an origin/main root checkout (`/workspace` lags and lacks the tool): `/usr/bin/python3 scripts/gitnexus-index-receipt.py --repo /mnt/raid0/llm/epyc-orchestrator --out /mnt/raid0/llm/tmp/f8-launchers-20261024/nib2-gnx1-reindex-2/out/index_receipt.json --job-result /mnt/raid0/llm/tmp/f8-launchers-20261024/nib2-gnx1-reindex-2/RESULT.json`, then ticks this box. Future re-index jobs call the same line after `gitnexus-analyze.sh` returns 0.
  - *(2026-10-24, ws58 wrap-up; box stays open.)* nib2-gnx1-reindex-2 ended ANALYZE_FAILED (gitnexus SIGSEGV rc 139 in the incremental write window, 16:20Z; untrusted index moved aside, backup restored). The orchestrator gitnexus index was then rebuilt by a forced full analyze under a whole-host claim and now reads `Indexed commit 84f6f6f = current, up-to-date` (19:52Z). Remaining: the receipt (`gitnexus-index-receipt.py --job-result`) still needs a job result from a passing job run. Step: write the receipt against the forced-analyze log `/mnt/raid0/llm/tmp/ws58-gnx-force2-20261024.log` if the tool accepts it, else re-run nib2 under a whole-host grant.
  - *(2026-10-29, ws58 results filing batch B; box stays open.)* `root-gitnexus-cb9f4d17-20261029` (FILLERS owner codex-refactor-01a16fc3) rc0 complete 01:47:20Z under a whole-host 0-95 grant: a fresh root index of a private worktree pinned at `cb9f4d17`. 95.8 s analyze, 9,589 files, 87,754 nodes, 134,727 edges, 1,963 clusters, 300 flows, 0 embeddings (vector search unavailable), sampled peak tree RSS 9.94 GB. No predeclared rule ("n/a (index preparation)"), so it is a diagnostic observation. The filer ran the receipt tool against this passing job result: `scripts/gitnexus-index-receipt.py --repo /mnt/raid0/llm/worktrees/codex-root-gnx-paw3-20261029 --job-result …/runs/real-179*/result.json` wrote `index_receipt.json` beside it (content_sha256 `44d28a8319c0…`, indexed_commit = git_head `cb9f4d17`, `fresh_at_head: true`, gitnexus 1.6.8). That proves the receipt path on a real passing job, but for the root repo and written post hoc. The orchestrator receipt this box names still needs the job itself to call the tool. [belief: cc]
    - [ ] **VB-GNX-REINDEX-1 job-side call (filed 2026-10-29, ws58 filer B):** add the `gitnexus-index-receipt.py --job-result` line to the re-index job templates (root-gnx `job.py` and the orchestrator nib2 job) so the job writes the receipt itself after analyze returns 0. Done when one job writes the receipt itself.
- [x] **VB-HSF5P-WRITE — HSF-5.P host KV mirror microbench write side and reader (filed and done 2026-10-24, workspace-f8).** ✅ 2026-10-24 producer `/mnt/raid0/llm/tmp/f8-launchers-20261024/hsf-5p/gpu/analyze.py` writes `hsf5p.beliefs.jsonl` (self-hashed rows, zero rows for an INCONCLUSIVE run, non-fatal; selftest 10 cases); adapter `scripts/vidya/adapters/hsf5p_microbench.py` (`cli.py ingest hsf5p-microbench`), test `tests/vidya/test_hsf5p_microbench_adapter.py` with fixture `tests/vidya/fixtures/hsf5p/` produced by the real analyzer; source row in `scripts/vidya/adapters/README.md`. No new ladder. The first real record arrives with the HSF-5.P microbench run (`heterogeneous-slot-fabric-residency.md` HSF-5.P), which is that box's event, not this one's.
- [x] ~~**VB-DF2-QWOPUS-K1-WIRE — prospective K1 speed/acceptance capture** (filed 2026-10-27, codex-refactor-01a16fc3).~~ CANCELLED administratively after verified operator withdrawal of Qwopus at13:48:29 UTC. No actual K1 measurement or wiring exists; numerical pre-registration is void. Private writer/readback and synthetic checks are historical preparation only. No future acquisition, inference or CLI/planning wiring is planned. [no-belief: administrative cancellation, no measurement produced]
- [ ] **VB-XGRAMMAR-TIMING-WRITE-READ** (2026-10-27, codex-refactor-01a16fc3): wire the prospective vocabulary-only benchmark writer and strict reader. Bind pre-run model/grammar/schema/instrument/images/grant/recipe, raw first-traversal and post-warmup arrays and sample identities; emit separate lower_better p95 tuples through existing measurement `ClaimTuple.grade()` only. Refuse summary-only, incomplete/mismatched and retrospective rows. Synthetic logits are not serving latency; validate any actual automated planner's own canary before claiming that loop wired. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/xgrammar-paired-v2/`.
- [ ] **VB-XGRAMMAR-OUTPUT-PARITY** (2026-10-27, codex-refactor-01a16fc3): retain the original 32 responses/contents, paired request hashes, schema/corpus/model/images/grant/source pins and schema validation for the 16-case CPU comparison. Writer emits schema-valid byte-identical pair fraction through the existing measurement grade, no new ladder; register a strict reader and refuse incomplete, tampered or retrospective input. No mask-parity, population or speed claim. Any future automated loop needs its own context canary before being called wired. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/xgrammar-parity-cpu-v1/`.
- [ ] **VB-M4-FOLD-SPEED-WRITE — prospective native current-C5/M4 speed source (filed 2026-10-27, codex-refactor-01a16fc3).** Review source-authored CPU process rows, strict reader and CLI integration in `/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-fold-gates/REGISTRATION-PROPOSAL.md`; preserve exact recipe/model/image/treatment/prompt/cleanup identities. The adapted22-core worker_general observation is not full scope, a best-recipe gate or promotion. Reuse existing measurement class and `ClaimTuple.grade()`, keep failure/incomplete records and require actual planning-context canary before wiring. No new ladder or reconstructed historical warrant.
- [ ] **VB-HIL15B-PILOT-WIRE — prospective second-taskset pilot assessment (filed 2026-10-27, codex-refactor-01a16fc3).** Reuse existing HIL native writer and measurement projection for exact task/gold manifests, all native outcomes/step/replay/CAS joins and incomplete attempts from `/mnt/raid0/llm/tmp/refactor-01a16fc3/hil15b-pilot/`. Bind each of three isolated native replays to its parent task and preserve per-replay reset scope. Native answer scores, ordered same-path protocol observations and exact captured-content checks are separate. Single-task AUC is insufficient; never pool its AUC values. Project through shared grader and pass planning-context canary before wiring; no mock measurement or population pass-band claim.
  - Include the original `hil15-target-calibration/v1` target request/response, model/kernel identity and watcher RSS/scratch readiness capture registered in the adapter README; retain actual fixed seed and predicted token count, failed startup originals and capture windows. This extends readiness observations only, without a replay/quality or normal-peak warrant, through the same carrier and shared grader.
- [ ] **VB-HSF5P-NEXT-TRACE-WRITE — HSF-5.P native profiler trace write side (filed 2026-10-26, workspace-58).** Review the HSF5P source-row extension in `scripts/vidya/adapters/README.md` for native trace/config/identity/window/denominator data captured by `run-v1.py` before the first run, extend the existing `hsf5p_microbench.py` reader (no new ladder), then require a planning-context canary before calling it wired. Write-side capture only: no substrate-wiring claim, no backfill of old measurements; the GPU run itself is unbooked. Draft: `/mnt/raid0/llm/tmp/codex-ni-20261026-hsf5p-profile-row/BELIEF-WRITE-DRAFT.md`.
  - PROFILE-6 prospective extension (2026-10-29): include `/mnt/raid0/llm/tmp/codex3-hsf-profile6-20261029/out/` and producer `run-v2.py`; retain original identity-before, arms, bodies/tokens, residency events, native traces, summary and interruptions in the same source-family reader extension. Do not ingest or claim attribution/wiring before native review and the planning-context canary. Real model smoke and campaign remain unrun. [no-belief: prospective producer registration]

  - *(2026-10-27, workspace-58 results harvest — projectability)* PROFILE-1..5 all INVALID/INCONCLUSIVE, zero rows; determinism-1 is an observation only; nothing projectable.
- [ ] **VB-HSF-ORIGINAL-IMAGE-DETERMINISM-1 — write side for the process-start determinism diagnostic (filed 2026-10-27, workspace-58; drafted by codex-ni).** Wire the native diagnostic summary and the exact-body token records to the existing HSF5P source family and the planning context. Bind the producer seal `d8dcfb6f`, the event/response paths and the actual run identity. Preserve absent/unavailable cache and incomplete-control states. Pass the planning-context canary. `ClaimTuple.grade()` is the only grader; no invented warrant, no new ladder.
- [ ] **VB-HSF5P-RESTORE-DIAG-WIRE — preserve native repaired-C5 restore observations.** Capture the three save/erase/restore/continuation checks with their raw responses, source/build/model/recipe identity, contemporaneous own-PID residency and linkage, and failure/unknown state. Project eligible native observations using the existing HSF5P source family and `ClaimTuple.grade()`; no new ladder, diagnostic seal, retrospective measurement warrant, timing or promotion claim. Run the planning-context canary before calling the loop wired.

- [ ] **VB-HSF5P-NEXT-PROFILE-5 — write side + projection for the PROFILE-5 attribution rerun (filed 2026-10-27, workspace-58; drafted by codex-ni).** Extend the existing HSF5P source-class adapter to this run output dir (bind RUN-OUTPUT, producer seal `b83d0b59`, run identity), project native records through the shared `ClaimTuple.grade()`, and keep an INVALID-for-attribution run as a determinism observation. Pass the planning-context canary before calling it wired.
- [x] **VB-AKX-LB32-WRITE — write side and adapter for the AKX-ALL-LB3.2 attribution run (filed and done 2026-10-24, workspace-f8).** ✅ 2026-10-24
  - Producer: research `scripts/benchmark/akx_lb3_attribution/beliefs.py`; `verdict.py --predeclaration` writes self-hashed `akx_lb32.beliefs.jsonl` beside `VERDICT.json` (branch `f8/akx-lb3-2a-attribution-20261024` @ c0d77e890, 40 tests). One row per (threads, N) cell (value = FA node-wall share of the 64k step) plus one verdict/seed-class row; `results_sha256` = VERDICT.json, `extra.predeclaration_sha256` = the frozen rule; an INVALID run writes zero rows. The launcher `/mnt/raid0/llm/tmp/f8-launchers-20261024/akx-lb3-2/job.sh` passes `--predeclaration`.
  - Reader: `scripts/vidya/adapters/akx_lb32.py` (`cli.py ingest akx-lb32`), strict: value, verdict and measurement_id re-derive from the row; an edited PREDECLARATION voids the file; Judged/Located via `claim_tuple.grade()`, empty `protocol_id`, no new ladder. Tests: `tests/vidya/test_akx_lb32_adapter.py` + fixture `tests/vidya/fixtures/akx_lb32/` + the end-to-end builder in `test_ingest_sources.py`. Source row added to `scripts/vidya/adapters/README.md`.
  - First record: after the run, `python3 scripts/vidya/cli.py ingest akx-lb32 --path /mnt/raid0/llm/tmp/f8-launchers-20261024/akx-lb3-2 --as-of <now> --only-new` (part of AKX-ALL-LB3.2 read-out).

### 2026-10-25 — belief capture made systematic (workspace-58; design `docs/design/committed-conclusions-belief-capture-2026-10-25.md`)
- [ ] **VB-TICK-CONTRACT** — every result tick carries `[belief: clm_…]`, `[belief: cc]` or `[no-belief: <reason>]`; wrap-up gate `scripts/handoffs/belief_capture_check.py` (Codex C6), advisory first. Wrap-up text change = free edit; CLAUDE.md + SESSION_LIFECYCLE.md lines = operator ratify.
- [ ] **VB-CC-PILOT** — committed-conclusions register (`data/belief/committed_conclusions.jsonl`, Judged/Located, existing measurement ladder, no run_id), pilot on the 120 Class-A items (54 gold conclusions) from `docs/reference/tmp-loss-inventory-2026-10-25.tsv`; acceptance AC0–AC9 in the design.
  - [ ] **VB-AK-PM16-CC — Capture the pinned AutoKernel AK-PM-16 selector-compatibility finding through the existing committed-conclusions pilot once its register, CLI and canary are implemented.** Bind the exact root commit/path/line plus source, upstream MIT license, replay and historical G15 receipt hashes from `artifacts/autokernel/ak-pm16-retrodict-20261030/`; classify Judged/Located OBSERVATION, no `run_id`, empty `protocol_id`. Preserve the bounded finding: the per-kernel classifier/extractor excludes actual high-share gather and recurrent rows as unsupported; this does not show it selected norm, and G15 remains `CLOSED_NO_GO` under its original 20% floor. No retrospective measurement tuple or new ladder; do not claim register ingestion before pilot implementation.
  - [ ] **VB-HYMT-Q4-OBSERVATION** — once VB-CC-PILOT is implemented, file the committed Hy-MT2 Q4_K_M launch finding as one prospective Judged/Located OBSERVATION. This task is conditional; the pilot/register/CLI/ingest/canary is not installed today. Preserve exact variant, source/model/launcher/job pins, exact native template match, retained Chinese + JSON response identities, structural preservation, cleanup and READY-WAIT context. Record that canonical 1.25-bit/2-bit tensor IDs collide with frozen-v10 Q2_0/NVFP4 and were never loaded; do not claim their compatibility, speed, translation quality, ABC or RAG. This is an operational conclusion, not a measurement tuple or retroactive warrant; no new ladder. Packet: `/mnt/raid0/llm/tmp/codex-ni-hymt-q4-recipe-r1-20261030`. Original quality and lowbit checkboxes stay open.
  - [ ] Capture the newly committed accepted GPU-preparation findings after their source checkpoint lands: Q38 omitted-`dryrun_pass` packet defect and private-admission repair; V11-FA-4b matrix/admission preparation and subsequent `no_reference` refusal; KPF-18 R15 source/PF/admission. Bind exact committed source hashes and file/line/quote locators through the existing committed-conclusion register; Judged/Located OBSERVATION, empty `protocol_id`, no `run_id`. Do not claim GPU quality, graph completion, migration PASS, or recreate native warrants. Use existing `claim_tuple.grade()` only. (Filed 2026-10-27; checkpoint `42f1d1aac` was merged by `8066bf575` on 2026-10-27. Capture remains open because this snapshot has no committed-conclusion register or CLI/read path; implement/land VB-CC-PILOT before recording the Judged/Located observation. Do not add protocol or run_id.)
  - *(2026-10-30, codex-ni prep; main applies conditionally.)* If the META full-suite diagnostic conclusion is accepted after the ROOT commit, capture it through the existing `VB-CC-PILOT` path using the exact ROOT commit/path/line and native proof locators `/mnt/raid0/llm/tmp/codex-ni-meta-full-arch-ready-20261030/{FULL-SMOKE-PROOF.json,CUTOFF-PROOF.json,ELF-SOURCE-PROOF.json}`. This is a Judged/Located committed conclusion only (no `run_id`, no reconstructed measurement tuple); the scheduled ten repetitions remain pending. No register ingestion or planning-context canary is claimed here. CH-27 stays in its existing calibration-loop source family and needs no generic committed-conclusion source row.
  - [ ] Capture the CME-7T committed conclusion after publication: [durable findings](../../docs/reference/cme7t-inf64-accepted-findings-20261025.md). One Judged/Located conclusion with secondary raw response SHA and exact response-ID/baseline join, protocol_id empty, no run_id or instruction-efficacy claim. Register ingestion has not run; use the existing pilot/ladder, no duplicate corroboration.
- [x] **VB-NATIVE-INGEST-10-24** — run the native-adapter ingests that never ran for the 10-24 result ticks (dry-run table in `/mnt/raid0/llm/tmp/ws58-canary-20261025/CANARY.md`), then cite frames on the ticks; adapter coverage gaps → Codex C5. ✅ 2026-10-25 (7 real ingests, 102 frames appended; every projecting tick and every decline annotated) [no-belief: not-a-result]
  - *(2026-10-25, workspace-58 wrap-up.)* Real ingests from `/mnt/raid0/llm/views/epyc-root-main` (`dbca39760`), `--as-of 2026-10-25T09:38:32Z --only-new`, canonical ledger 38,452 → 38,554 lines (+102). Canary copy: [`docs/reference/loop-canary-2026-10-25.md`](../../docs/reference/loop-canary-2026-10-25.md).

    | tick | adapter | path | rows | frames appended | skipped (already live) |
    |---|---|---|---|---|---|
    | M4.2 | pb-hol | `f8-launchers-20261023/m4-srpf-pbhol/out` | 6 | 18 | 0 |
    | KPF-17.4c | kv-prefix-fork | `f8-launchers-20261024/kpf17-4c-bisect` | 2 | 6 | 0 |
    | KPF-18.0b | kv-prefix-fork | `overnight-20261020/kpf18-run` | 7 | 21 | 0 |
    | KPF-18.0d item 3 | kv-prefix-fork | `overnight-20261020/kpf18-run-w1c` | 1 | 3 | 0 |
    | AKX-ALL-26b (CPU) | ak-width-cells-cpu | research `artifacts/akx_all_26_cpu_20261020` | 10 | 0 | 30 |
    | PB-QCOST-1 confirm | pb-qcost | `f8-launchers-20261023/pb-qcost-1-confirm` | 18 | 0 | 54 |
    | PB-QCOST-1 confirm-R | pb-qcost | `f8-launchers-20261024/pb-qcost-1-confirm-r` | 18 | 54 | 0 |

    - Two of the canary's "never ran" claims were wrong: PB-QCOST-1 confirm and the AKX-ALL-26 CPU artifact were already in the ledger.
    - The canary pointed AKX-ALL-26b at the 10-20 AKX-ALL-26 artifact, which is not that run. The run's own dir (`batch-20261024/akx26b/out/`) matches 0 units, so the `GGML_FA_SPLIT_KV=0` column has no belief. That is a new adapter gap for Codex C5, alongside the gaps BATCH-2 already lists: pb-hol M4.2a single arm and M4.2b nested `L*/summary.json`, KPF-18-S1.R4 with no `belief_measurements.jsonl`, the AKX-ALL-26b HIP half, and NIB2-GNX-1 with no module.
    - Nothing refused. The ticks carry `[belief: clm_…]` or `[no-belief: …]` (M4.2/a/b, PB-QCOST-1 confirm/confirm-R and GPU-ZOS-2.1 in `gpu-serving-tie-in-program.md`; KPF-17.4c, KPF-18.0b, KPF-18.0d item 3 and KPF-18-S1.R4 in `kv-prefix-fork-and-paged-attention.md`; AKX-ALL-26b; SEC-ART-POST-b; NIB2-GNX-1; P1-PHASE2-SERVED-SHAPE-RECAL above).
- [x] **VB-C5-PBHOL-M4.2B-NATIVE-READ — read the original nested PB-HOL M4.2b packet through the existing adapter (filed/done 2026-10-26, Codex NI).** Commit `b8397f3a4b02a4c33f6f38391cc1b0bfba7763dc`, `codex/pbhol-m42b-native-projection-20261026`; 80 tests PASS and original native projection PASS (`22.014`). Four path aliases locate one measurement; three overlapping pairs are not independent repeats. Existing PB-HOL source class and `claim_tuple.grade()` only; no new run, grade, or ledger append. `[no-belief: tooling-repair]`
- [x] **VB-C5-KPF-S1R4-NATIVE-READ — project the original KPF S1.R4 native record through the existing reader (filed/done 2026-10-26, Codex NI).** Commit `8175fca24b38bffcc8f635d2d762c2753abfd5c6`, `codex/kpf-r4-native-reader-20261026`; 74 tests PASS and native projection PASS, 256 positions, ONE fresh load, `0.03224632537967409` vs `0.027456215011625318`; stored seal preserved. Existing KPF source class and `claim_tuple.grade()` only; no new run, grade, or ledger append. `[no-belief: tooling-repair]`
- [ ] **VB-CANARY-GATE** — make VB-REFOCUS-NONEMPTY-READ-PROOF executable: a planning-context canary per loop (AK + AutoPilot, no inference) that must show a known historical conclusion in the assembled context; loops are not "wired" while it fails.
  - *(2026-10-25, first canary run, workspace-58; not ticked: the gate is not yet executable, and AutoPilot did not pass.)* Report: [`docs/reference/loop-canary-2026-10-25.md`](../../docs/reference/loop-canary-2026-10-25.md) (from `/mnt/raid0/llm/tmp/ws58-canary-20261025/CANARY.md` + `B-summary.json`). No inference, scratch ledger copies, canonical ledger unchanged.
    - **AutoKernel Q38FN: PASS with caveats.** The 10-22 query-major replicate null (row 337, −1.10%) reaches the context through the in-store "Already tried" channel on every ROOT. Defects: **D-A1** a producer-time ingest is hidden from the plan that ran it (`as_of` fixed before `ensure_current`); **D-A2** the do-not-repeat guard is inert for Q38FN (quant None on split GGUFs, `research_scope` dropped over 2 MiB, surface mismatch, ≥3-answer threshold); **D-A3** ranked recall drops the current-epoch keep_candidate (row 335); **D-A4** the default ROOT is the stale `/workspace`.
    - **AutoPilot: PARTIAL/FAIL.** Passes: the numeric-trial insight, the opseed convention, and the pbhol REGRESSED claim. Fails: the trial-1472 frontier keep appears only as a bare id, and the Pareto summary says 0 entries. Defects: **D-B1** unit tests write the LIVE seeding telemetry (20/20 rows polluted); **D-B2** two contradictory frontier sizes in one prompt (the journal path ignores the epoch fence); **D-B3** stale ROOT (= D-A4); **D-B4** the kvq block says "unavailable" while the belief block lists kvq claims; **D-B5** the bridge prepare cannot forward a read log.
    - All of these are assigned to Codex: D-A1..A3 and D-B1, B2, B4, B5 in `LOOP-SAFETY-C-BUNDLE` C2/C3 via BATCH-2 (`codex-ni-20261024-scheduling/tasks-from-ws58/BATCH-2-20261025.md`, due 10-26 18:00Z); D-A4/D-B3 in C1.
    - [ ] **VB-CANARY-GATE-1 — re-run both canaries after the Codex C1-C3 fixes land, and script them as the gate (filed 2026-10-25).** Promote `harness/canary_a.py` and `harness/canary_b.py` from the tmp run into a committed `scripts/vidya/canary/`, each with its known-conclusion assertion (A: row 337 in the belief section and a guard refusal; B: the 1472 keep with its numbers, and a non-zero Pareto count). Done when both exit 0 on the fixed code; then tick VB-CANARY-GATE.

- [ ] **VB-AK-NATIVE-WIRE-WRITE** (filed 2026-10-26) — first step: audit existing actor-call adapter coverage against native `epyc.autokernel.actor_wire.v1`; reuse its existing ladder if reusable, no new grader (`claim_tuple.grade()` decides). Wire prospective native matrix finalization to capture the exact decided proposition, original status/checks, seat/client/config/suite identity, request/capture attestations, cleanup and completeness state, separating native protocol proof from mocked controls. Preserve PASS/FAIL/aborted/unvisited. Native wire outputs are verifier findings, not model-quality measurements; no timing or merge-validity claim; no retroactive warrant (historic R11 only as a located committed conclusion). Add strict reader mutation/refusal tests and the planning-context canary. Source-table row: `scripts/vidya/adapters/README.md`.

- [ ] **VB-HIL-LB1A-CUT-WRITE** — prospectively capture actual streaming-guard outcomes at the request writer: bind one inference request id across request-start constraints/grammar presence, model/runtime/binary identity, stream chunks, guard version/config and stop event, raw partial/final response, parse status and owned-process cleanup. Preserve missing fields and incomplete/failed requests as unknown; never backfill old tap rows or code-inferred call-site labels as recorded flags. Validate an existing measurement carrier and use only `claim_tuple.grade()`; do not add a grading ladder. Add strict native-writer/reader refusal tests for missing constraints, mismatched request ids, altered chunks/stop reason, and incomplete cleanup, then prove a planning-context canary before calling the source wired. The controlled 2026-10-29 one-request observation shows a legitimate repeated-object JSON response can be cut by the current default guard; this is a single diagnostic, not prevalence or protocol-grade evidence. The historical 16 apparent cuts remain unproven.

## Projectability notes — results harvest 10-22..10-25 (workspace-58, 2026-10-27)

These are notes only. The adapters README is not edited here; the owner applies any source rows.

**Already projectable**

| Rows | Adapter / source |
|---|---|
| KPF-64 replay A-D and arm E | chunk_kv (`--belief-out`) |
| KPF-17/18/62 fork rows | kv_prefix_fork (VB-KVU-PF family) |
| inf72 RT-1/RT-9 | moe-routing |
| ds41-w5d | `ds41_w5d.py` |
| spec-rng-1-2 | VB-SPEC-RNG-1-2-WIRE |
| yarn native and extension arms | VB-YARN-AGG |
| pb-qcost confirms | `clm_pbqcost:v1` |
| new10-q38fn | VB-QUANTCMP-NEW10 |
| CME-7S | clbench-cache-hit |
| GPU-LEAK-1 probes | `gpu_leak_probe.beliefs.jsonl` |
| s5-rtepfx2 | its emitted `chunk_kv.beliefs.jsonl` |

- kpf18 `item3v2_load<N>` and the `hsf_*` sub-arms remain read-side gaps (VB-KVU-PF.2 / .6a).

**Needs a write side**
- [ ] VB-HARVEST-1022.a: the llama-bench ABA timing source should project the v11-050/051/052 GPU HOLDs, q38fn armP/armP2 speed, hsf-5p-microbench, c5-gate-b (sign-only, indicative) and kvu19b-p3.
- [ ] VB-HARVEST-1022.b: fold-gate verdict records should project c3/c4/c5 gates, g2conc-c3/c5 and the correctness slices. This depends on VB-FOLDGATE-WRITE.
- [ ] VB-HARVEST-1022.c: a stage1.verdicts parser for kpf62-g0 (bit-identical gates).
- [ ] VB-HARVEST-1022.d: a cluster-bootstrap capability row for ufh14-lb3-4-confirm (+21.51 pp, CI [+11.83, +32.26]).
- [ ] VB-HARVEST-1022.e: no adapter yet for the following, so each needs a source row:
  - inf48-g10 (ORACLE_CULPRIT)
  - inf42-g1 (frontdoor recall)
  - fd-div-1b (ANOTHER_CAUSE)
  - speech-d1 probes
  - kpf60-p0-gpu
  - m27-live-recall

**Must project nothing**
- s5-dripreview1, an all-`bad_final` vacuous run.
- akx-lb3-2-attribution, hpr-b-64k-holdout and ufh14-lb7-1 (INVALID or report-only).

- [ ] **VB-GNX-C5-CALLER-AUDIT-1 — wire original INF-50 C5 GitNexus caller-graph audit dependency evidence.** Preserve the actual r11 baseline, tool repair identity, original sealed results, audited caller scope and withdrawn r10 finding; do not invent a measurement warrant or new grading ladder. Define the dependency evidence write-side and demonstrate the planning-context canary before calling it wired. [Source and limits](../../artifacts/ni08/inf50-c5-gitnexus-r11-20261027/README.md).

- [ ] **VB-HSF4-CPU-PAIR — project prospective HSF-4 frontdoor CPU paired measurements through the existing KPF source class.** Before the first capture, enroll the item-185 `hsf_L<L>` source row in `scripts/vidya/adapters/README.md`. The private S1R writer emits sealed per-length native run records and rows JSONL with restore+first-token and re-prefill first-token pairs, validity and original S1R source-phase cells; `summarize_pairs.py` is a derivative, not a native measurement warrant. Current `kv_prefix_fork.py` declares `hsf_L<L>` but declines projection. Extend that reader only against prospective native evidence, verifying predeclaration, model, binary, prompt, argv, rows hash, paired order, first-token match, actual context/CPU scope and partial/incomplete state; preserve warm-tmpfs/cache and within-load ordering confounds. Use the existing source ladder and `claim_tuple.grade()`, never a new grading rule or invented historic warrant. Add strict positive and refusal/partial fixtures and demonstrate the planning-context canary before calling the loop wired. No inference result or whole HSF-4 closure is asserted.

- [ ] **VB-RVP-ATT-CANARY-WIRE — enroll the RVP-ATT model-free native trace producer.** Capture prospective source/ISA/recipe/device/window and original raw trace, live library and residency evidence at write time, preserve unavailable and loss states; project eligible native records through the existing native-profile carrier and `ClaimTuple.grade()` with no new ladder. For the separate unsealed diagnostic `/mnt/raid0/llm/tmp/att-decoded-r5-prep-20261028/`, distinguish no-warrant diagnostic observations, preserve unknown loss/loop states, and refuse retrospective measurement tuples or new diagnostic seals and receipts. Establish loop boundaries and calibration before any efficiency claim; run the planning-context canary before calling wired. No historical warrant backfill.
- [ ] **VB-B2-PRODUCER-E-WIRE — preserve scoped producer-E comparison provenance.** The existing re-derived JUnit comparison under `/mnt/raid0/llm/tmp/refactor-01a16fc3/b2-producer-e-comparison-20261028/` may enter the committed-conclusion register as an observation only. For any future eligible native producer, capture test identities, original result hashes, historical-failure basis and custody at write time and use the existing carrier and grading rules; do not fabricate a historical warrant, diagnostic receipt, seal or new ladder.
- [ ] **VB-INF26-NEW8-WIRE — capture the private ik self-quant experiment at write time.** Preserve source and binary/library hashes, canonical input and quantized model identities, exact tensor mapping and recipe, shared comparison inputs, quality, timing, device/placement and contemporaneous contention for the actual run. Project eligible native records through the existing shared carrier and grading rules; the instrument build and metadata scan are only committed conclusions and supplies no retrospective measurement warrant. No new ladder or serving-path claim.

- [ ] **VB-UFH14-A3A-DIAGNOSTIC-WIRE — project future descriptive cold/one-warm capture records.** Bind the producer's actual model and draft, source, grant, window and request identities to its retained cache, timing and SSE observations; preserve partial/unavailable states. Use the existing observation carrier and `ClaimTuple.grade()` without a new ladder. The tiny-model launcher smoke is not an A3a measurement; no historical warrant backfill. The prospective source is registered in `scripts/vidya/adapters/README.md`.
      The 2026-10-30 F1 option (a) successor `/mnt/raid0/llm/tmp/codex-ni-ufh14-a3af1-20261030/` remains in this existing task: preserve COLD / ONE-WARM / ALL4-WARM arm and native requested-versus-selected slot identities, exact historical prompt pins, request/proxy hashes, native cache/prompt counts and prefill timings, raw SSE and recorded arrivals, model/runtime/library/grant/window identity and in-workload KFD/VRAM and cleanup. The strict offline reader must verify the original event count, ordinal, ordered type and timing before projecting client TTFT from first nonempty generated-output delta arrival; preserve first-byte and first-event latencies separately. TTFT and prefill seconds lower=better; same-load arms are not independent witnesses. Qualifying smoke is not the full historical result or an F2/keep verdict. Planning-context canary remains required before calling wired; existing carrier and grade only. [no-belief: prospective wiring scope extension]

- [ ] **VB-M4-GPU-OFF-IDENTITY-WIRE** (2026-10-27, codex-refactor-01a16fc3): Register a strict reader for the prospective M4 OFF current-C5 GPU response identity source. Bind pre-request provenance, grant, full model/image/recipe/prompt/source/rule pins, two C5 controls, original responses and all failure/truncation outcomes. Project decided identity using the existing shared class and `ClaimTuple.grade()` without a new ladder; refuse missing, tampered or retrospective records. Do not claim any automated loop wired without its planning-context canary. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-gpu-off-ready/`.

- [ ] **VB-KVU-LB1D-WRITE — project prospective KVU-LB1.d frontdoor-model F16-V diagnostic records.** Preserve the original pre-model grant, source/image/model provenance, exact six-arm argv and switches, native per-cell timing, placement, process/cleanup and invalid/partial outcomes, and inherited 1% predeclared rule. Project only eligible native records through the existing measurement class and `ClaimTuple.grade()`, with no new grading ladder or retrospective warrant. Require strict positive/refusal fixtures and the planning-context canary before calling wired. The quarter F16-V diagnostic cannot establish an effect on the live q8-V recipe or authorize deployment. Private producer `/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-cpu-frontdoor-worker-ready/frontdoor/driver.py`.

- [ ] **VB-NIB98-SAMPLED-FD-VERIFIER** — Before any authorized loaded C5 DS41 canary, finalize and enroll its native verifier write-side record and a strict adapter that projects the explicitly recorded proposition: “At each recorded C5 server-executable sample across readiness and the shutdown boundary, including at least two after owned-port readiness and one immediately before the shutdown signal, the server retained a descriptor for the same private lease inode.” Bind each run's sample stream, timestamps, executable and lease identities, owned-port readiness, exit/partial state, source-sealed argv/env, input provenance, linkage and grant. Refuse missing proposition, evidence or contradictions. Project only; `claim_tuple.grade()` decides via the existing shared grader. Do not claim continuous retention between samples, global exclusion, or a proof for any different server. The held model has not run; do not invent a prior claim tuple. Run the planning-context canary before calling the loop wired.

- [ ] **VB-INF30-Z9-WIRE — prospective restricted simple-GLA oracle conformance.** Before a future verifier claim, write an atomic structured record of the explicit restricted CPU-f32 forward-recurrence proposition, named synthetic test IDs/results, argv, exit status and source/test digests at execution. Project only complete well-formed producer records through the existing verifier class and `ClaimTuple.grade()`; test refusals and the planning-context canary. The 2026-10-28 plain test output is pre-hook; do not backfill it or infer HF SALA integration, model/GGUF parity, or GPU behavior.
- [ ] **VB-INF12-G2-WRITE** — Add a producer-time, self-hashed native `belief_measurement` envelope to `summarize_full.py` only after full Gate2 completion and strict input/output/run-config validation; add the existing-class adapter projection and tests for complete, partial, duplicate/mismatched run fingerprints, altered outputs and absent protocol pins. Smoke and historical records without producer-time fields remain unprojected. No new grading ladder and no retrospective tuple.
- [ ] **VB-CME7T-RESPONSE-WIRE** — integrate and strictly project the private prospective native capture for CME-7T bounded-rationale outcomes before a claim-bearing run: bind prompt, model, recipe, binary and run identity, trace/cohort and response IDs, raw and trace digests, unique failure/length counts, all denominators and missing/unmatched outcomes, source/cleanup/residency proofs. Reuse `ClaimTuple.grade()` and the existing source-class ladder; no historical warrant invention. Existing `clbench_cache_hit.py` handles cache ratios only, not response outcomes. Native v2 projection must also rederive canonical hand/interaction/attempt joins and worker terminal states from original journals, verify the closed artifact seal including raw replies and native traces, and distinguish diagnostic accounting from native success. No incomplete or unattempted hand is zero credit or a replacement draw.
  - [ ] **EVL50 native-summary producer extension.** Wire the distinct `job/summarize_raw.py` output (`candidate/failure-summary.json` and `COMPLETE.json`) into the existing CME-7T response source at the original future run boundary. Bind raw-reply, result-writer and summary-source hashes; run, model and server identity; arm definitions; exact denominators; per-arm unique schema-failure and runaway counts; and incomplete/cleanup state. Refuse malformed or incomplete inputs and require the planning-context canary. The 2026-10-28 bounded diagnostic predates the hook: do not backfill its measurement warrant or infer efficacy or GPU residency. Reuse the existing measurement ladder.

- [ ] **VB-MOE-RT10-CAPTURE-LINK — integrate the prospective DS41 original-attempt capture extension of the existing MoE routing source.** Preserve the before-load grant/source/binary/model provenance, raw corpus and exact C5 effective-prompt digests, native recipe/log and same-attempt shard link. Require native model/architecture/corpus/hash/recipe agreement before projecting RT6/RT7 through the existing moe-routing source and `ClaimTuple.grade()`. Retain partial, missing, gap and tamper states; never reconstruct an old run's warrant, infer throughput, or claim DSpark/MTP coverage. Synthetic pipeline and refusal fixtures passed in `rt10-ds41-tap-ready`; actual DS41 capture/analysis and planning-context canary remain required before claiming this extension wired. No DS41 HOLD release or production change is authorized.

- [ ] **VB-RTG57-VKQ-WIRE — RTG57 native VKQ timing capture and planning context.** Merge and install source branch `codex/rtg57-vkq-wire-20261027`; bind each T48/T96 packet's exact source, producer, protocol and enrollment commit; independently verify the private writer→ingest→planner canary on installed bytes. Capture prospective native timings using the shared ClaimTuple measurement carrier, 3 process pairs, empty protocol and indicative throughput only. T96 is an experimental topology-shape, not registered adoption; preserve original model-free oracle's n=1 and unknown original producer hashes without model/device scope. On first real complete run ingest and prove planner context; no model-quality, speed adoption or GPU claim follows from the oracle. Owner applies index row if required.
  T96 repair successor `/mnt/raid0/llm/tmp/codex-rtg57-t96-repair-20261028/` needs its exact new producer/source/enrollment binding and same-entry CPU smoke before source acceptance or a fresh claim-bearing run. The old rc125 partial contains three full arms and half of the fourth, no six-arm verdict. Retain its failure; future rc75 attempts are separate fresh windows. The existing projector remains prospective; an operational smoke or monitor unit test does not establish timing or whole-task completion.
  - 2026-10-28 (ws58 filer): FAILED-RUN `rtg57-c5-vkq-t96-repair-20261028` rc=1 (job-rc-1), whole host 0-95, 41.6 min (20:10:26Z-20:52:03Z). Class harness: all six arms (ABBAAB) ran to completion and `native-receipt.json` + `verdict.json` were written, then `projector.py` resolved `PROTOCOL.md` as `out.parent.parent/PROTOCOL.md` (the run dir; the file lives in the scratch root) -> FileNotFoundError -> driver CalledProcessError, `projected-claims.json` empty, so no claim was ingested. Receipt content (indicative, unprojected, no correctness, no ladder grade): F32 vs HYBRID effect medians N=1/8192 -0.39%, N=1/32768 -1.10%, N=5/8192 +3.52%, N=5/32768 +0.28%; draft verdict COSTS, scope indicative only. Owner action: fix the projector PROTOCOL path (`out.parent.parent.parent`), re-run it on the retained `run-20261028T201026Z-1835607/attempt-0/out/native-receipt.json` (no new window), then ingest. Filed at `/mnt/raid0/llm/tmp/compute-flags/filing-done/rtg57-c5-vkq-t96-repair-20261028.FILED`. [no-belief: failed-run]
- [ ] **VB-KVU16H-DEDICATED-WRITE — prospective dedicated-server P3 write-side projection and planning canary.** Bind the RTG57 producer above before any claim-bearing future run; finalize source/model/kernel/recipe/request/owned-process/window/raw-input identities at the original run boundary, project into the existing measurement class via shared `claim_tuple.grade()` only, retain partial/failure absence semantics, and prove the writer→ingest→planner canary. Do not retrofit a measurement warrant into the 2026-10-28 smoke or already-started full run; a later committed conclusion may be recorded as an OBSERVATION with its committed path. The original KVU-16h task remains open beyond this private P3 producer.
- [ ] **VB-DF2-ROW-EXACT-WRITE** — Install reviewed DF2 output and byte native producer/projector; register explicit-path ingest, source table and source-seal-bound receipts; require same-device residency, full per-shape/repeat coverage and negative controls; verify actual planning-context canary before calling either loop wired. Reuse measurement ClaimTuple.grade(), never invent a protocol or new ladder.
- [ ] **VB-META-QWEN4EXP-NATIVE** — integrate the reviewed adapter/writer into owner-approved root view, install source table row, execute writer→ingest→planning-context canary with a known historical conclusion and do-not-repeat history; retain host-only scope and the shared measurement ladder. Do not tick until canary passes.
  - 2026-10-29: META r3 private CPU/HIP profile build and model-free host fixtures are a committed-conclusion candidate (correctness-only); the build marker and fixture logs do not carry the existing qwen4exp native measurement tuple. No retrospective measurement warrant or planning-context canary is claimed. [belief: cc]
- [ ] **VB-PARAKEET-STT0-VERIFIER — wire CS-8.STT0 native paired transcript identity verifier.** Reopen original retained predeclarations, input and grant/source/linkage warrants, 40 correlated clip raw outputs and sampler hashes; strictly rederive the predeclared identity proposition, Boolean and matched count/40, rejecting incomplete or changed evidence. Project via the existing verifier ClaimTuple carrier with empty protocol and UNKNOWN/unobserved co-tenancy; preserve false verdicts, no timing, general quality or equivalent-weight claim, no new ladder and no retrospective warrant. Add source-table row, registered reader/CLI ingestion, verify real original custody and planning-context canary before calling wired. For the unsealed diagnostic successor `/mnt/raid0/llm/tmp/codex-cs8-cpu-full-20261028/`, preserve the exact clip/PCM, model and binary identities, commands, device witnesses, native raw outputs, partial state and unknown co-tenancy; project only what the records actually capture. No new diagnostic seal, receipt or invented measurement warrant.

- [ ] **VB-SPEECH-CS22V0-VERIFIER — wire CS-22.V0 deterministic fixed-corpus parity receipts before their first run.** Add the prospective source row and a strict native verifier adapter, rederive exact predeclared per-arm equality propositions against all 224 pinned clips and six threshold/silence settings from stored raw posteriors and statuses, preserve finite posterior maximum deltas as descriptive native numbers without adding a tolerance, and decline incomplete or mismatched receipts. Bind input, model, binary, package, corpus/PCM, comparator and linkage warrants as recorded at write time. Co-tenant state is UNKNOWN/unobserved; no native segment API, timing, population quality or equivalent-weight claim. Project via the existing verifier carrier and `claim_tuple.grade()` only, with empty protocol_id; no new grading rule or retrospective warrant. Fixture valid/negative/tampered/incomplete cases and pass the planning-context canary before calling the loop wired.
- [ ] **VB-SPEECH-CS22V0-SAME-RELEASE — extend the existing verifier family for prospective first-four-clip three-arm diagnostic records.** Reopen/hash original predeclaration, grant/source/input/model/package provenance and every raw/status/stderr; refuse missing/mutated/incomplete records and rederive frame counts, paired maximum differences and exact stop/segment equality at original six settings. Preserve same-release versus unproved weight identity, pinned original reference, subset scope, unknown co-tenancy and empty protocol/no timing or qualification. Use existing verifier carrier and ClaimTuple.grade only; native contemporaneous capture/enrollment precedes run, strict projection and planning canary precede belief use. Historical CS22 evidence is never backfilled.

- [ ] **VB-KPF621-YARN-SELFCHECK-WIRE** — Wire the KPF62.1 YaRN same-context startup selfcheck native capture and its eventual committed conclusion to the existing committed-conclusion register, preserving original raw evidence and provenance; validate planning-context canary. KPF62.1 remains open pending actual owner-run result.
- [ ] **VB-UFH14-LB51-WRITE — wire the live template-prefix fixture producer prospectively:** record native run identity, per-turn prefix checks and error/partial state at write time; project through one source-class adapter to the shared `ClaimTuple` and `grade()` ladder. Preserve thinking setting, fixture/template/model/kernel pins and exact covered roles. Do not invent measurement warrant for prior runs. Prove the planning-context canary before calling the loop wired.

- [ ] **VB-UFH12-GS — wire the prospective coverage record for G-S token and paired proxy-query diagnostics.** Transfer reviewed writer/projector into maintained repos; register one source kind and CLI adapter; validate fixed-seed paired ID membership, source and model hashes, per-tranche proof and checkpoint digests; emit coverage counts with complete only at expected total, preserve raw score/token distributions as descriptive evidence. Use the existing shared measurement ladder and `ClaimTuple.grade()`, no new grading rule. Verify native synthetic refusal cases and a real prospective planning-context canary. Do not ingest fixture or reconstruct old measurement warrant. Status 2026-10-27: writer/projector, `ufh12-gs-coverage` source kind and canary merged (a945a35fb); installed-root canary + enrollment run by workspace-58; REPL-EMB-2.11 and R5 stay open until real prospective evidence exists. Owner: UFH-12 / belief substrate lane.

- [ ] **VB-M4-C5-OFF-C2-WIRE** — extend the existing PB-HOL reader to locate four alternating current-C5/M4 OFF loads, reopen original preload/source/model/recipe/grant/rule warrants and native records, verify all attempted repetitions and failures, and rederive the ratified paired relative ratio. Preserve overlapping-pair dependence and incomplete outcomes; use existing ClaimTuple.grade only. Add fixtures and planning-context canary before calling wired. No historical measurement warrant or new ladder.

- [ ] **VB-YARN-CPU-SHARDS** — extend the existing yarn-gate-agg projection/planning canary to the prospective CPU-only fixed120-pair/four-shard layout. Reopen all before-load model/image/DSO/template/source/recipe/prompt/grant warrants and raw outcomes, verify exact-union120/botharms/zero exclusions, refuse changed/missing/incomplete or mixed CPU/GPU data, and reuse the existing fixed-sample decision and shared grade. Native producer emission happens only after the complete cohort merge; verify its emitted file and registered ingest/planning-context canary before calling wired. No sequential stop or historical backfill.
- [ ] **VB-CL3-QUARTER-PROFILE** — implement strict native benchmark/profile capture projection for prospective quarter locality cells. Bind original proposition/source/model/store/recipe/region/shape, per-attempt native samples and raw profile hashes, workload sampling scope, interrupted exposures and completed checkpoints. Preserve unknown protocol/co-tenancy and no-baseline/no-full-thread-attribution limits; refuse missing or mutated evidence. Add source-bound adversarial fixtures and the planning-context canary before belief use; no new grader or retrospective measurement tuple.

- [ ] **VB-HIL15B-DISCOVERY — wire the fixed-cohort discovery assessment.** Reopen the original pre-load warrants and immutable native task/replay receipts, rederive the exact four-shard 60-case union, all denominators and censors, actual answer/tool/native-join observations and deterministic same-data selection. Refuse missing, mutated, substituted, incomplete or fixture records. Project via the existing measurement carrier and ClaimTuple.grade without a new ladder, preserving discovery scope and unknown protocol/co-tenancy; validate adversarial writer/reader fixtures and planning-context canary before belief use. Existing L2/AUC sources remain distinct; never retrofit earlier measurement warrant.
- [ ] **CT21-DIRECT-WRITE — wire the CT21 exploratory direct-interface v2 diagnostic.** Project its prospective producer-authored `belief_measurements.jsonl` through `chat_template_ab.py` and shared `ClaimTuple.grade()`; bind the enrolled source/profile/fixture/manifest and capture request/response provenance. No aggregate when direct answers are unobservable; no original CT21 competence gate or retrospective tuple. Prove the complete planning-context canary including tried history before calling the loop wired. Owner: CT21 diagnostic owner. [no-belief: tooling-repair]
  - *(2026-10-28 producer-side smoke.)* The corrected actual direct-interface smoke emitted four unique producer rows after 80 real requests and in-window residency checks; IDs differ across invocation/collection. Empty protocol ID and diagnostic scope remain. Canonical reader integration plus complete planning-context/tried-history canary are still open; no older measurement warrant was backfilled. [belief: cc]
  - 2026-10-29 (ws58 filer A): the normal run `ct21-direct-v2-repair-20261028` (rc0 00:30:13Z) wrote its producer sidecar natively, 4 rows in `/mnt/raid0/llm/tmp/codex-ct21-direct-repair-20261028/run-20261029T002822Z-3838926/collection-0/belief_measurements.jsonl`, with 80/80 outcomes observable. This is the first normal-run input for the reader integration; the canonical reader and the planning-context/tried-history canary are still open, so the loop is not wired. [belief: cc]
- [ ] **VB-KPF623-CORRECTNESS-WRITE — prospective KPF-62.3 correctness observations.** Capture each named native verdict, test identity, source/binary/model hashes, grant and interval at the producer boundary; fail closed on missing or partial controls, project through the shared ladder, and test the planning-context canary. Preserve 2026-10-28 raw logs; register the owner-committed conclusion separately as a Judged/Located observation, without inventing a measurement tuple.
- [ ] **VB-KPF623-AUX-WRITE — capture auxiliary attention source at write time.** Preserve native per-key/query/head score payload and validated logical/physical mapping plus invocation, source/binary/model identity and grant/window at producer boundary; refuse partial maps/rows, project through the shared ladder and pass a planning-context canary. Register the owner-committed 2026-10-28 bounded conclusion separately as an observation; never invent a measurement warrant.

- [ ] **VB-UFH12-IRT-PAIRED-WRITE — qualify the prospective paired IRT source and its native planning loop.** Reuse the existing measurement carrier for the fixed 510/408/102 cohort and both arm/metric observations, retaining historical truncated-BGE input scope, observed masks, training-only fits, held-out predictions and blank protocol. Test the installed producer→normal CLI→private planner canary, real-context fixture exclusion and rejection of fixtures presented as real. The strict-runtime reader remains OPEN: independently reopen and validate original binary/library/source/grant/pre-load warrants rather than treating record-bound digest strings as verified runtime identity. Capture the first real run prospectively and prove its planning-context canary before calling the loop wired. No adoption, retrospective warrant or new ladder.

- [ ] **VB-M4-GPU-QUALITY-WRITE** — project prospective native v7 GPU quality results with exact role/recipe/model/image and paired-question provenance, all errors and truncation, and device residency. Refuse incomplete or mismatched arms/suites; use the existing measurement carrier and ClaimTuple.grade without a new ladder. Verify the planning-context canary before calling the loop wired. GPU quality is supplemental; CPU quality, full-role speed and the fold verdict remain separate. No retrospective warrant. Prospective R12 producer: `/mnt/raid0/llm/tmp/codex-m4-gpu-quality-r12-native/collect.py`, SHA-256 `9abde1f113d2401c4dc46dd09af3183204331acee524a1bde86108e154d35cf3`; no R12 runtime result is claimed.

- [ ] **VB-M4-CPU-CAL-WRITE** — project prospective C5/M4 architect CPU memory-calibration samples through the existing measurement carrier, preserving source, recipe, model, image, grant, sampled-not-peak limits, cleanup and incomplete attempts. Verify strict native evidence and the planner-context canary before calling the loop wired. No new grading rule, speed/quality gate or retrospective warrant.

- [ ] **VB-M4-CPU-WORKER-CAL-WRITE** — project source-authored worker/frontdoor full-topology calibration records through the existing measurement ladder, preserving sampled-not-peak limitations, identity, grant, cleanup warrant and incomplete outcomes; prove the actual planner-context canary before claiming the loop wired.

- [ ] **VB-M4-CPU-VISION-CAL-WRITE** — project prospective native vision calibration records through the existing measurement ladder, preserving pre-load target/projector hashes, sampled-not-peak limitations, source, recipe, image, grant and cleanup warrant and incomplete outcomes; prove the actual planner-context canary before claiming the loop wired.

- [ ] **VB-M4-FOLD-TOPOLOGY-CANARY** — extend VB-M4-FOLD-SPEED-WRITE validation to the separately sealed topology-aware producer, including actual native entries, role-bound topology and planner-context canary; retain original-source compatibility. No new grading rule or historical warrant.

- [ ] **VB-SSU-F16-CRITIC-WRITE — wire prospective architect critic plan-critique evidence.** Before the first scored run, capture the original source-authored item set, DELETE-lens rubric, model/role/recipe and runtime identity, native per-item outcomes, truncation and repetition caveats. Project only eligible native records through the existing carrier and `claim_tuple.grade()`; do not create a new grading ladder or backfill historical warrant. The private exploratory packet has three unscored excerpts and no live observation; the canonical scored corpus and rubric are unresolved. Prove the planning-context canary before calling the loop wired.

## PAW-3 prospective own-slice capture — 2026-10-29

- [ ] **VB-PAW3-OWNSLICE-WIRE — capture the FuzzyBench own-slice paired abstention record at write time.** Bind the predeclaration, frozen cases, actual compiler and binary/semantic bundles, runtime model and libraries, grant/CPU identity, raw outputs and native first-token logits, all failure/invalid/unknown outcomes, and terminal disposition; project the verified native record through the existing PAW shared `ClaimTuple`/`grade()` carrier. Verify tamper/refusal controls and the planning-context canary before calling the loop wired; do not invent a grading ladder or retrofit a measurement warrant.
  - 2026-10-29 own-slice producer captured native record and projected one shared-grade `Judged/Located` observation (no protocol citation; not decision-gating) in `/mnt/raid0/llm/tmp/codex3-cpu-ready-20261029/results/real-179*//claim-tuples.json`. Capture/projection exists; planning-context canary remains unproven, so the loop is not yet wired. Candidate committed conclusion: PAW-3 exploratory own-slice TRANSFER_NOT_SHOWN, 5/8 semantic exact matches against the enrolled ≥90% rule. [belief: cc]
  - 2026-10-29 prospective q0 source extension: task index 6 keeps its native negative/neutral/positive labels; semantic arm adds UNSURE. The predeclared three-label normalized-confidence comparison is a multiclass extension, not a literal binary replication. Scratch `/mnt/raid0/llm/tmp/codex3-paw3-q0-20261029/`; per-case raw logits/output and grant custody use the existing producer carrier with strict declared-label validation. No selected-case outcome or wired-loop claim.
  - 2026-10-29 preparation: scratch producer and shared-carrier projector pass synthetic source/grant tamper, duplicate-exposure refusal and interrupted-projection resume controls. At this preparation checkpoint (before the 15:41 UTC result above), the paired evaluation and native projection had not run. This standalone evaluator has no planning loop; a planning-context canary is needed upon loop adoption, not claimed here. [belief: cc]

  - 2026-10-29 q0 completed 16 cells and projected one `Judged/Located` OBSERVATION without protocol citation; candidate committed conclusion: sentiment extension TRANSFER_NOT_SHOWN, 3/6 decided vs ≥90%. No planning loop has been adopted; no loop-wiring or canary claim. [belief: cc]

## PAW-3 paraphrase own-slice capture — 2026-10-29

- [ ] **VB-PAW3-PARAPHRASE-WIRE — capture the FuzzyBench paraphrase own-slice paired abstention record at write time.** Bind predeclaration, frozen cases, compiler and binary/semantic bundles, runtime model and libraries, grant/CPU identity, raw outputs and native first-token logits, all failure/invalid/unknown outcomes, and terminal disposition; project the verified native record through existing PAW shared `ClaimTuple`/`grade()`. Verify tamper/refusal controls and the planning-context canary before calling the loop wired; do not invent a grading ladder or retrofit a measurement warrant.
  - 2026-10-29 producer completed 16 cells and projected one `Judged/Located` OBSERVATION without protocol citation; candidate committed conclusion: paraphrase slice TRANSFER_SUPPORTED, 7/7 decided vs ≥90%. No planning loop has been adopted; no loop-wiring or canary claim. [belief: cc]


## PAW-3 standard-arm capability source — 2026-10-29

- [ ] **VB-PAW3-STANDARD-WIRE — capture standard-arm FuzzyBench capability diagnostics.** Bind both prospective shards' declaration, fixed task/case identities, standard programs, native decoded outputs, source/model/library/grant identities and every disposition at write time; project verified native records through shared ClaimTuple/grade and exercise tamper/no-redraw/resume controls. The standalone evaluator has no planning loop; a planning-context canary is required only upon loop adoption before a wired-loop claim. No new grading ladder. Scratch `/mnt/raid0/llm/tmp/codex3-paw-standard-20261029/{A,B}`.

- [ ] **VB-EVL34-NATIVE-PAIR-WRITE** — before prospective model exposure, audit existing evaluation source-class adapter and reuse its ladder; project the native per-case/per-arm result, predeclared pins and original completeness/containment evidence into ClaimTuple, using `claim_tuple.grade()` without a new grader. Preserve no-delegation, failures and in-flight unknowns; implement write-side emission, refusal/mutation controls and planning-context canary. Historical emulated-REPL records remain historical, never paired with new real-REPL outcomes.

- [ ] **VB-INF05-KV6-TIMING-WRITE** — add prospective native canonicalization timing capture and projection, binding original source hash, input shape and length, raw timing batches, CPU affinity, runtime and incomplete outcomes; use the shared grade and verify the planning-context canary. Keep synthetic isolated timing separate from production request latency and do not backfill measurement warrant.

- [ ] **VB-RTG56-RAW-CASE-WRITE** — capture prospective TD-29 raw-completion three-arm native case records at source with prompt/case, model and binary hashes, actual arm, token counts, request settings, CPU window and incomplete outcomes; project through the shared grade and prove the planning-context canary. Preserve the diagnostic raw-lane and production-chat distinction; no backfilled warrant or new ladder.

- [ ] **VB-RTG15-LRC-SDM-WRITE** — wire prospective grouped observed-outcome screen records before scoring: bind original input, semantic group and split hashes, fit/calibration/test decisions, eligibility masks and denominators, and native per-group paired outcomes; project with the existing shared grade and prove the planning-context canary. Preserve unopened holdout and incomplete results; no historical warrant or new ladder.

- [ ] **VB-RTG28-TB1-BUDGET-WRITE** — wire prospective native per-item reasoning-budget records before measurement, carrying exact role/model, corpus and scorer hashes, budget, seed, truncation and finish reason, attempted denominators, window and observed versus carried lineage. Project through the existing shared grade, retain incomplete/unknown items and prove the planning-context canary; do not backfill historical tuples.

- [ ] **VB-INF50-SR6-SPEC-WRITE** — capture and project prospective SR-6 paired composed-spec n_max 3/4 native trials through the existing shared grade, binding source/model/quant, full recipe, corpus/seed, arm order, counters, timings and admitted window, and retaining all attempted, incomplete and invalid arms. Prove the planning-context canary before calling wired; no historical backfill.

- [ ] **VB-MFVBS2-MEASURE-WRITE** — before prospective BEP inference capture native task/prompt and verifier bytes, four-block ABBA arm/order, turn cap, role/model and source/runtime identities, per-trajectory result and full per-turn trace, verifier outcome, raw errors, inference/custody evidence and classifier version/config. Project through the existing shared grade, preserve unknown and incomplete outcomes, and prove the planning-context canary; do not backfill historical trajectories or invent a new ladder.

- [ ] **VB-INF50-SR7-BRANCH-WRITE** — capture prospective SR-7 per-request branch attribution with original cumulative native trace, response counters, model/quant, n_max, recipe, prompt, arm order, runtime and window identity. Reconcile branch deltas against each native response; preserve missing/partial attempts and diagnostic scope. Project through the existing shared grade and prove the planning-context canary; no historical backfill or 122B inference from small-model runs.

- [ ] **VB-INF72-RT10-FIXTURE-WRITE** — capture prospective computed GET_ROWS tap fixture results with original fixture/source/binary/library identities, I32 positive values, F32 refusal and incomplete execution; project via the existing shared grade and prove the planning-context canary. Keep synthetic graph scope separate from DS41 model dtype, coverage and held inference; no retrospective warrant.

- [ ] **VB-INF30-Z9-ORACLE-WRITE** — capture prospective SimpleGLA CPU oracle and packed-sequence fixture outcomes with original source/runtime, shapes, boundaries, initial-state and numeric comparison identities, including invalid-input and partial outcomes. Project via shared grade and prove planning-context canary; do not infer native FLA equivalence, model integration or retroactive warrant.

- [ ] **VB-INF30-SALA-ORACLE-WRITE** — capture prospective native three-prompt SALA CPU oracle records at original write, binding exact prompt/model/source/runtime identities, generated token IDs and all attempted, failed and partial outcomes. Project through the existing shared grade and prove a planning-context canary; do not infer native FLA parity or backfill prior runs.

- [ ] **VB-EVL39-E3B-WRITE** — wire prospective original-write E3b matched-context records and native reader before scheduled measurement, binding exact task/corpus/context, model/config/source identities, each direct/folded/REPL request and score, native tool/accounting records, in-flight unknowns, times and cleanup. Refuse fixture-only or incomplete records for decisions; use the shared grade and prove the planning-context canary without historical backfill.

- [ ] **VB-MOE-RT62-LAG** - Bind RT6.2 causal history/lag outputs, including full_replay.py native epyc.moe.policy_lag_replay.v1 records, to existing moe-routing carrier. Export full native trace `input_traces` and canonical content SHA at producer write time, retain exact sequence/layer/calibration/evaluation boundaries and policy source SHA. Refuse expected-uniform-replica-load rows as realized-dispatch DI-081 evidence; use existing shared grade, no new ladder. Acceptance: a zero-replica native-proxy fixture projects with full source scope, replicated expectation is refused for realized-dispatch decisions, and planning-context canary passes. For full replay, verify content/config/source hashes and native input_traces, preserve selected sequence, phase, layer, nonoverlapping causal intervals, per-step realized-dispatch axes and deterministic seed; reject malformed, empty or partial cells. Add a native-cell projection and tamper/refusal fixture; no T=3 or pooled-workload decision is implied.

- [ ] **VB-GPU-LEAK-1E-EMIT — extend the existing GPU-leak observation projection to the one-factor result producer and validate its planning-context canary.** Existing source/ladder remains gpu_leak_probe; preserve each at-start argv/model/server binding and native series, and emit prospectively from future producer runs. Current factor conclusions enter only through their committed-conclusion register, not invented retrospective measurement warrants. [Native record and filed conclusion](../../artifacts/compute/results-filing-20261030-0000.json). [belief: cc]

- [ ] **VB-ARCH-SLOW-CRR-WRITE — capture prospective Architect Slow/CRR conditional results at analysis time.** Bind candidate/baseline arm IDs, source run and input identities, analyzer digest, candidate-correct matched denominator, no-faster numerator, fraction or explicit unavailable reason and counts, and completion state. Project only through the existing measurement carrier and `claim_tuple.grade()`; no new grading ladder, score, threshold or retrospective tuple. Historical A1/A3 rows with invalid candidate speeds remain unavailable.


### Prospective NEMO native producer

- [ ] **VB-NEMO-PROF-TOKEN-BINDING** — finalize/project the prospective native NEMO producer through the existing measurement ladder and adapter. Preserve source-time API/request/context/scope/position/sequence/HIP/clock identities, exact unknown/partial/coverage accounting and separate encode/dispatch-sum/union-busy/wall semantics. Reopen one owner-scheduled original L/B capture through the strict reader and pass its planning-context canary; tiny CPU/GPU plumbing canaries and old counts do not substitute. No historical warrant or second grading ladder. Source packet: `/mnt/raid0/llm/tmp/nemo-prof-reseg-review-20261030/PROSPECTIVE-CAPTURE-PACKET.json`, SHA `df16eb2c39dc87d978b44ef21e954fda5c96a673f1334ad8069674bb18816f14`. Native source `b1e820a0ad8bc2192fc38c3c1beda7abf3a28ecf`; strict reader assigned to refactor worker. Original measurement remains open.


### NI source custody relocation — 2026-10-30

Unused NI Research/Orchestrator linked checkouts were retired through `scripts/system/worktree_gate.py`; original branches and exact patches/indexes remain preserved under `/mnt/raid0/llm/tmp/codex-ni-repo-legacy-retirement-20261030/`. The prospective HPR producer remains `c4c2a3638cf6a62c823920c3d9d271e6aec8f911` on retained `codex/hpr-b-sim-fix-2-20261025`; its seven-file driver readset is in `source-readsets/codex-ni-20261024-hpr-recovery/MANIFEST.json`. Raw/golden captures stay at their existing locations. The earlier dirty HPR suffix draft was archived as superseded by that producer; no new source was landed. VB-KVU-HPR-PREFIX, native contract UNVERIFIED and owner-reviewed admission/holdout requirements remain open. Finished historical launch scripts retain exact bytes at `.sh.retired-20261030`, catalogued in `retired-scripts.json`; those archived scripts are not runnable scheduling inputs. [no-belief: source custody relocation]

- [x] **VB-KPF-PLAN-STEPS-WIRE — controlled native planner capture and real-planner recipient canary.** ✅ 2026-10-30. The completed native run journalled 52 actions across 23 plans (next position 24), including one-action plans. Read-only planner-context canary reopened that record and showed numeric 52, n=1, and native-own history; wrong-model and pre-as-of checks refused, while the real index was fresh (max=2521, lag=0, no stub). Separate manual TERSE review is already closed on main 31f: 0/52 TERSE, 0 WORKING, 0 UNKNOWN; this adapter does not project that classification. The strict writer/reader and seven portable/native refusal controls use the existing carrier and shared grade. No normal API reload or live-traffic/adoption claim; the separate harness item remains open for literal first KEEP traffic. [Continuation evidence](../../artifacts/compute/codex3-kpf261-continuation-v2-20261030.json). [belief: cc] See the source table.
  - [x] **VB-KPF-PLAN-STEPS-WIRE strict ingest implementation.** The source registry, CLI and pinned native reader project journal action count through the existing shared grade; seven portable controls plus native fixtures reject synthetic, malformed and resealed task/prompt/action/actor/persona/wire records. This completes the source integration only; real capture and the planning-context canary remain in the parent task. ✅ 2026-10-30 [no-belief: source implementation and bounded fixture verification]


- [ ] **VB-AK-R24-9-REPEAT — project prospectively captured same-code excursion findings through the existing AutoKernel experiment family.** Extend the `autokernel-experiment` adapter to recognize only `measurement_invalid` rows with producer-sealed `invalid_measurement.same_code_tripwire.schema=epyc.autokernel.same_code_tripwire.v1`, `status=same_code_excursion`, an earlier experiment attempt id, both captured code manifests/work key, both signed effects/floors, and the new native comparison/raw samples. Verify the existing `belief_capture`, prior attempt reference and arithmetic; emit a verifier/observation claim about the evaluator/session excursion with the original journal warrant. Keep `effect_fraction` null on the invalid row, no candidate performance claim, no new source kind/ladder/protocol/grade, and no retroactive tuple for earlier journals. Prove the planning-context canary before calling the source wired. Source producer landed research `8b1cdb6fb8dd2255acf3f4194e690d1a23465510`; no adapter/canary completion claimed.

- [ ] **VB-WG-LFMI-NATIVE-QUALITY-WRITE-READ** — after the full scheduled native run, audit supported scorer outcomes and project eligible prospective results through the existing measurement source family and shared `ClaimTuple.grade()`. Preserve the raw outputs, all 422 arm-case denominators, the 33 separate arithmetic cases, seven context-missing unknowns, unsupported execution/judge scores, transport/cutoff/partial states, and pinned source/oracle/model/runtime identities. READY, smoke and cutoff alone emit no tuple or quality/decision claim. A committed preparation conclusion is an OBSERVATION only through the committed-conclusion route; never invent a retrospective measurement warrant, second ladder, representative-traffic claim or historical wire equivalence. Require CLI integration and the planning-context canary before saying wired. Source packet `/mnt/raid0/llm/tmp/codex-ni-wg-lfmi-quality-native-20261030/`.
  - 2026-10-30: full native run now has 422/422 response records and diagnostic scored outcomes; projection and canary remain open. Filed findings are committed-conclusion candidates, not invented measurement warrants. [belief: cc]

- [x] **VB-PIP02-INCREMENTAL-TEDS-WRITE** — Wire the prospective per-invocation incremental scorer record and strict projection. Bind original cohort/split/page/table identities, prediction/GT/plan/scorer/config/source and original request/finish lineage hashes, coverage including unknown/error cases, native matching, both per-table TEDS variants, execution boundary and immutable output digest. Project through the existing measurement ClaimTuple and shared claim_tuple.grade(); no second ladder or invented historical warrant. Keep already-written score snapshots as ordinary evidence; pass the planning-context canary before calling the loop wired. Source table row added immediately with this new scoring process. ✅ 2026-10-30. Implemented in Research source cbd7ee026 (main6d2ab2803) and ROOT source ebc48f2d7 (main55bbca49): immutable begin/end score receipts bind selected original request/finish evidence, source images and metric inputs; strict projection uses the shared grade, empty protocol and one invocation per capture. Actual Paddle s021 receipt dd41924d02e279cb76eae7c56fc388bf1818199d543de2015bbe2eb5884c599d covers five pages/five tables. The real planner recipient canary sees both numeric metrics and their own tried mechanisms; wrong-model and pre-capture-as-of controls exclude them, with the real intake index fresh at max2521/lag0. This closes the writer, strict reader and eligible Paddle model-scoped canary scope. ODL receipts lacking compatible model scope stay explicitly unprojected; raw ODL scores remain ordinary evidence. No model-weight identity is invented, and the full755-page quality gate remains open. [belief: cc]
  - 2026-10-31 source-catalog extension: Research `4fd00eb02` and `d2b95912cedd` add a versioned exact R28/R29 head and original fresh-s1 catalog, preserve all source/grant/request/finish checks, and leave the prior absolute scorer path untouched. The exact existing adapter/ClaimTuple bytes are deployed with the scorer; no new source ladder or retrospective measurement warrant is introduced. Six native source controls and original s128/new s001/s003 receipt replays pass. Post-freeze deduplicated coverage is 344 English pages / 82 GT tables; ten newly eligible pages add zero GT and leave both table-weighted means unchanged. The full 755-page/243-table quality and paired gates remain open. [belief: cc]
  - 2026-10-31 correction/R30 extension: the earlier d2 portability claim was wrong: its watcher still imports the ROOT lane and omits r29 legacy epochs. Keep old receipt-bound paths and the lane available. Research `261f7804a037` supplies a separate immutable R30 scorer; actual cold HOST imports resolve both native adapter and shared grade from its packaged snapshot, and it includes r29/r30 baseline epochs. The literal R30 registration has synthetic controls only before cohort execution; the 16 historical no-layout page bindings are correlated from original source/capture evidence, never invented intrinsic PID identities. All 24 unmatched region starts remain protected. No new source family/task/ladder, historical regrade or full-population verdict. [no-belief: prospective catalog correction]
  - Prospective offline page assembly recovery captures pre-computation START, original source/image/layout and authenticated response hashes, no-network/no-model execution, new output/finish and scorer/GT identity. The new record attests the recovery only; it does not invent an old finishing event or another grading ladder.
  - 2026-10-31 R31 catalog extension: Research `e27883ff25cf` registers the exact producer and original pool3 groups 110/122/134/146 in a separate immutable scorer version. Record source, cohort, grant/request/finish and scoring lineage before projection; the no-start inventory protects this 60-page subset and other unmatched starts remain untouched. Qualification only at publication; no real-grant cohort or full-population verdict. [no-belief: prospective catalog extension]

2026-10-30 original-event filing: Original FA4 C5 exact-set R12 failed rc1 in exact_B: evidence_exec.py read /proc/2423529/exe after the child exited. FAILED is INCOMPLETE; exact_B rc-15/partial and the228-case arm/full comparison are unfulfilled; cleanup verified with no cleanup error. Preserve all raw native outcomes and numerical rules. NI was notified to capture executable identity while the child is live, with captured birth, then qualify a new run. This is an instrumentation race, not a numerical/kernel finding. [Original event audits](../../artifacts/compute/results-filing-20261030-1842.json). [belief: cc]

- [ ] **VB-G16A-NATIVE-WIRE** — Prospectively project future G16a native per-case status, trace, source/image and live-residency records into the existing ClaimTuple carrier before the next run; use the shared measurement ladder, preserve failure/unsupported/partial rows and prove a planning-context canary. The original 2026-10-31 conclusion is a committed-conclusion OBSERVATION only; never retrofit a measurement warrant or unrecorded NMSE value or seed.

- [ ] **VB-SPEECH-STT2-A1-NATIVE — wire prospective CS-8.STT2 and CS-22.A1 native records.** Bind contemporaneously recorded source/commit, runner/library/linkage, model/quant, corpus/PCM, request/configuration, resource admission and UNKNOWN co-tenancy to per-clip raw output/status/errors, actual request/cleanup and resumable partial artifacts; preserve cross-runner reference transcript differences as descriptive, and accept streaming parity/soak/startup claims only where their own full native evidence exists. Reopen and hash evidence, refuse incomplete or altered records, and project via existing observation/verifier carriers and shared `claim_tuple.grade()` with empty protocol and no new grading rule or retrospective warrant. Include valid/tamper/incomplete controls and a planning-context canary before declaring wired. Diagnostic R11 smokes remain unsealed.

- [ ] **VB-EV5-PROCESS-ATTRIBUTION-WIRE — wire prospective T2 process-verifier attribution before it informs planning or promotion.** Candidate producer: orchestrator `scripts/benchmark/eval_t2_process_verification.py` / `scripts/autopilot/process_verification.py`, published as orchestrator `de6c56e34f5f23c2155d2b7dc839554ae692f771`; source publication does not complete this wiring task. Bind original scored row IDs, prompt/answer hashes and confidence source; actual generator/verifier families; model, runtime, source and request configuration; raw native CoT/step spans; single-token Yes/No IDs and observed log probabilities, common bias and available unbiased control; and explicit partial/error/resume counts in a producer-written immutable record. A conditional Yes probability is a verifier judgment, not a correctness label or calibration result. Project through the existing measurement carrier and shared `claim_tuple.grade()` with no new ladder, invented protocol or retrospective warrant. The operational Gemma N1 smoke and duplicated resume-control IDs are not independent quality evidence. Require valid/tamper/unknown/partial controls, CLI/read integration and a planning-context canary before declaring wired. Source-table row added by owning NI session at this boundary; no adapter, tuple, or canary completion claimed.

- [ ] **VB-SPEECH-STT3-PARITY — wire prospective CS-8.STT3 transcribe.cpp and CrispASR parity evidence.** Bind native per-case exposure and results, frozen datasets, production model and binary/library/linkage, decode/VAD/prompt/KV options, admission and co-tenancy to a reader that rehashes contemporaneous artifacts, refuses incomplete or changed sources, and projects the predeclared paired P-STT-1 and silent-tail rule through the existing carriers and shared `claim_tuple.grade()`. Include valid, tamper, incomplete, unknown-exposure and denominator controls, and a planning-context canary before calling it wired. No full-cohort acceptance until capture is enrolled.

- [ ] **VB-SPEECH-CPU-LID-WIRE — wire prospective CS-26.LID1 native CPU LID records.** Bind original native probability/logit vectors and classification, exact common crop/PCM/offset/padding, model/quant/library/linkage, code, PID/affinity and admission identities, plus explicit failure, unknown and partial outcomes. Validate and project original producer-written evidence through the existing Speech family and shared `ClaimTuple.grade()`; no new grader, invented protocol, retrospective warrant, or recommendation from READY/smoke. Require tamper/unknown/partial controls and a real planning-context canary before calling wired. [Predeclared preparation](../../artifacts/speech/cs26-lid1-20261030/README.md).

- [ ] **VB-SPEECH-G1B-WIRE — capture prospective CS-8.G1B cascade-language records at write side.** Bind per-cell audio/transcript and errors, fixed cohort, seeds, model/binary and admission hashes, full denominators, per-mode same-run English M17 comparison and bootstrap, separately represented repeat seed and listener status. Project through the existing Speech family and shared `ClaimTuple.grade()`; require tamper/unknown/partial controls and a real planning-context canary. No new grading rule or retrospective warrant.

- [ ] **VB-SPEECH-CS45-TAIL-WIRE — capture prospective CS-45.1 synthetic-tail records at write side.** Bind native per-clip/configuration outputs, complete 820-clip manifest, QA, model and environment hashes, selection/confirmation split and five synthetic tail conditions; preserve undefined INT-FPR, no-human-advance and failure/unknown states. Project through the existing Speech family and shared `ClaimTuple.grade()`; require tamper/unknown/partial controls and a real planning-context canary. No new grading rule or retrospective warrant.

- [ ] **VB-SPEECH-STT5-RAW — wire prospective CS-8.STT5 native raw records.** Bind native per-chunk raw output and validated result manifest, plan/input, runner/model/library/code/process/admission pins, and explicit failures, partial and unknown exposures. Reopen original source artifacts and project through existing Speech family and shared `ClaimTuple.grade()`; preserve failure denominator, no redraw, no new grading rule or retrospective warrant. Require tamper/incomplete controls and a real planning-context canary before calling wired. [Predeclared plan](../../artifacts/speech/cs26-lid1-20261030/STT5-PLAN.md). Extend the same native Speech source projection to the independent Ultra engineering-stage records: original PCM/model/processor/generation/source pins, masks and raw shapes, frontend/encoder/joint-logit arrays, token IDs/durations, per-arm exposure/result fingerprints, failures and no-redraw boundaries. Preserve numerical differences without inventing tolerances, keep engineering reuse separate from accuracy and CPU/HIP gates, and require a real strict-reader planning-context canary. [Qualified source checkpoint](../../artifacts/compute/codex3-speech-prep-20261031/README.md).
- [ ] **VB-GPU-ZOS-2.3-WRITE — project prospective native C5 GPU-ZOS gate records through the existing measurement carrier.** Producer `/mnt/raid0/llm/tmp/codex-ni-gpu-zos-build-prep-20261031/successor/gpu/gpu_gate.py` records immutable mode-specific run intent before native work, binding source/patch, image/model, predeclaration, prompt/argv, arm order, metric direction and validity. Preserve per-arm process identity, each original response and token/content/acceptance/rate, contemporaneous KFD/graphs evidence, complete/partial/error state and raw digests. Distinguish per-request paired ratios from independent process witnesses; retain original conditional serial/A3-B3 outcomes and indicative-only DEBUG attribution. Complete the producer carrier and one strict reader/CLI projection through shared `ClaimTuple` and `claim_tuple.grade()`, with valid/tamper/missing/partial controls and a planning-context canary before calling it wired. Native records or the task's SHIP label alone do not establish an adoption warrant. No retrospective tuple, invented protocol, second ladder, or current adapter/canary completion is claimed. Source registration is applied by the owning NI session; native preparation uses the existing owner loop rather than a new approval gate.

- 2026-10-30 C3 R3 original B and G12 completed: C3's prospective native receipt carries one 95-step union-busy observation and raw join, G12 retains 110 per-case query/source/index pins and original truth; results and limitations are in [filing artifact](../../artifacts/compute/results-filing-c3-g12-20261030.json). Existing VB-NEMO-C3-NATIVE-PROFILE-WIRE and SC50 reader/projection tasks remain open; no canary or retrospective measurement warrant is claimed. [belief: cc]


- [ ] **VB-PRB-T4-RESUME-WIRE — validate the prospective segmented TALE rerun through the existing TALE adapter and planning-context canary.** Verify original request/response/finish, start/end/cost and contemporaneous source/model/kernel/process/admission envelope for every attempted cell; preserve interrupted, capped, policy-limited and unknown cases and their original 400-per-suite denominator. Exercise missing/tampered/mixed-warrant and partial-resume controls, verify the unchanged `tale_budget_capture.py` output projects only eligible completed records through existing `ClaimTuple.grade()`, and require a real planning-context canary before calling the new source wired. No historical measurement warrant, new protocol or second grading ladder. Full observational rerun keeps all 1,600 questions, estimator plus three answer arms, original fixed-rule interpretation, 10,000 paired bootstrap draws and OAA; the reference ADOPT label is an experimental readout, not a production adoption gate. [Prospective source and rule snapshot](../../artifacts/compute/codex3-ready-checkpoint-20261031-0105/prb-prospective/PREDECLARED.md); native qualification remains separate.

## C6 served-shape Q4_K microbench source — 2026-10-31

- [ ] **VB-C6-Q4-MICROBENCH-WIRE — project prospective C6 Q4_K native microbench captures through the existing measurement carrier/ladder and pass its planning-context canary.** Producer is `/mnt/raid0/llm/tmp/c6-35186-q4-microbench-prep-20261031/`: actual pinned 27B Q4_K tensor shapes plus a separately labeled synthetic Q4_K reference on the existing DS41 MXFP4 expert dimensions. Before each full calendar run, preserve instrument/model-header/case/recipe/source/image/seed/thread/grant/affinity identities; retain per-case native latency units and repeat coordinates plus raw hashes afterwards. Project observations only, using shared `claim_tuple.grade()`; do not invent a grading rule, missing input-byte identity, protocol/noise-floor, or historical warrant for R11 component controls. Acceptance: strict raw reread, incomplete/tampered/mismatched inputs refuse, source registry/reader coverage and planning-context canary. Existing G-AK op correctness and named serving-cell predicates remain separate. Source table: `scripts/vidya/adapters/README.md`.

- [ ] **VB-C6-CPU-OPS-WIRE** — capture future C6 native per-op CPU run/source/binary identities, hashed stdout/stderr, seed, actual CPU/IQK environment and grant, with supported/unsupported counts at write time; project complete attestations through the existing seeded-operation source ladder and `ClaimTuple.grade()`. Refuse missing/tampered identities, preserve unsupported and unknown outcomes, and pass the real planning-context canary before calling it wired. Historical R3 remains a committed-conclusion observation; no new grading rule or historical backfill.

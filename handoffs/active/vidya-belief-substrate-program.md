# Vidya Belief-Substrate Program

**Scratch**: `/mnt/raid0/llm/tmp/vidya-belief-substrate-program/` · worktrees: `/mnt/raid0/llm/worktrees/vidya-belief-substrate-program-*` NI08 source and native review and private ledger coverage preparation: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/`, `/mnt/raid0/llm/tmp/ni08-inf50-projection-finish-20261007/`; MAIN acceptance originals `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/`. Further own recipe and original publication custody: `/mnt/raid0/llm/worktrees/ni08-c26-native-recipe-20261007/`, `/mnt/raid0/llm/tmp/c106-root-wrap-publish-*`, `/mnt/raid0/llm/tmp/threeview-narrow-validation-*`, `/mnt/raid0/llm/tmp/intake175-narrow-validation-*`.

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

For the current queue, use the open checkboxes below and the generated
[`master-handoff-index.md`](master-handoff-index.md) rollup. KV-quant: `VB-KVQ-V10-DICT` first (root adapter
must accept the producer's stats-dict medians; Codex coordination) — it blocks `VB-KVQ-V10-INGEST`, which also
waits on the first post-hook sweep sidecar. `VB-KVQ-V10-RECONSIDER` (AutoPilot correction review, synthetic
correction first) is dispatchable now.


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
- [ ] **SC55 — wire the INF-70 per-node / per-thread graph profiler as a measurement source, write side
      FIRST.** Filed 2026-09-05 by INF-70 as its arms began producing them. This instrument
      (`GGML_CPU_PROF` + SYNC-1's per-(node,thread) extension: `wall_max`, `argmax_ev`, `spikes`, per-thread
      compute, `NNODES_EQ/MIN/MAX` graph-shape filters, `PATHROW` with `ne_calls`/`GBs_per_ne_call`) now
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
      on the model routes through it — B7's PLE-Q8_0 A/B is its first consumer and is running now. **Project, not
      grade.** Four caveats are mandatory in every tuple and are the whole reason to wire the write side now:
      `GGML_IQK` state (a real 2.2% systematic offset between kernel paths), determinism (the ± is corpus
      sampling, not run noise — two binaries reproduced to every digit, so overlapping bars are NOT agreement),
      Ny regime (perplexity runs Ny>=32, serving runs Ny=1 — a PPL observation says nothing about the serving
      path), and BINARY attestation by `.so` hash + mtime rather than commit alone, because C9 was a stale
      artifact whose library predated its own fix. Source-table row added to `scripts/vidya/adapters/README.md`.

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

- [ ] **SC48 — wire the MI210 power-sensor probe suite into the belief kernel on the write side**
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
- [ ] **SC47 — evaluate the FlashInfer Trace schema as the carrier shape for kernel-candidate records.**
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
    - [ ] **2026-09-17 sampled-location extension, before first live GLM use** (GLM-5.3-Flash deleted 2026-09-22; read as "before first live use on the next CPU target", e.g. DeepSeek-V4.1-Flash): write bounded per-TID×symbol-family×sampled-CPU/NUMA-location period fields and the `perf --sample-cpu` capture identity in the original immutable profile receipt. Project only native sampled fields through the existing measurement ladder; old captures remain location-unknown, and CPU location alone cannot establish remote memory traffic or a throughput gain.
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
- [ ] **SC81 (S3-VID-07) — write-side wiring for AutoKernel workload census + blast-radius rows
      (INF-75).** Census rows (epyc.autokernel.workload_census.v1) and patch-footprint/classification
      rows (epyc.autokernel.patch_footprint.v1) are verified structural findings: project them via an
      adapter into ClaimTuple (no new grading rule). Non-regression rows reuse the existing serving A/B
      archive/belief export.

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

- [ ] **SC86 — wire HS-4 shell runs on the WRITE side**: each run emits a ClaimTuple carrying the harness pin, plugin and config hash, Harness Card version, `x_memory` arm, and the HS-14 column set; locator = run. Must land before the first measured shell run (HS-4 P0.4). Design: `docs/design/hs4-shell-and-orchestrator-features-20260916.md` §4 (P0.5).
  Status 2026-09-16 (`sub-sc86`, branch `sub/sc86-20260916`, unmerged): **adapter ready, producer pending (HS-4 P0.4 driver).** `adapters/opencode_shell_run_capture.py` (run-sidecar schema `epyc.hs4.opencode_shell_run.v1`, writer, `validate_row`), `adapters/opencode_shell_run.py` (strict reader), `cli.py ingest opencode-shell`, and `tests/vidya/test_opencode_shell_run_adapter.py` (32 pass, including writer → `cli.py ingest` → tuple). Rows: the four HS-14 columns, re-derived from recorded counts; refused on a missing pin or config hash and on pre-hook or backfilled runs. The P0.4 driver must write `opencode_shell_run.json` and call the writer at run end; that call is the HS-4 P0.4 owner's. Tick this box when the branch is merged and the driver calls the writer (the SC85 precedent).
  - 2026-09-17 (`sub-hs4-mcp`): the P0.4 driver now calls the writer. `scripts/harness/hs4_p04_acceptance.py verify` writes the run sidecar and `attempts.jsonl`, then calls `write_belief_measurements`, and its tests run `validate_run_sidecar`/`validate_row` on the output. The adapter is on main (`934317b2`). The tick condition is met, so the SC86 owner can tick this box.
- [ ] **SC86b — codify the shell-run protocol** under `measurement/protocols/` (task suite, trials per task, serving at production `enable_thinking`, the HS-14 column definitions), and have the P0.4/HS-14 driver pass `protocol_id`. Until then, every OpenCode-shell tuple is `Judged/Located`.

## SC88 — AutoKernel fresh seeded operation correctness (filed 2026-09-17)

- [ ] **SC88 — wire fresh seeded operation correctness on the WRITE side before first real invocation.** The opt-in producer emits a self-hashed ClaimTuple-shaped receipt joining arm ID, selected candidate source/binary and trusted instrument digests, serving recipe, suite seed, console evidence, and per-case reference/property residuals. `reference_valid`, `property_only`, and `oracle_unavailable` retain their exact provenance; CPU candidate-local references cannot be upgraded to independent anchor correctness. Strict read-side projection accepts only post-hook receipts and delegates grading to `claim_tuple.grade()` without a new ladder. Report-only: no ranked-time or promotion authority. Source: `autokernel-research-loop.md` AK-integrity pack (intake-1454#record).

## SC89 — AutoKernel observed plateau diagnostic provenance (filed 2026-09-17)

- [ ] **SC89 — bind the read-only AK-plateau reporter on the WRITE side before its first real-store report.** Author a self-hashed ClaimTuple-shaped receipt with immutable input experiment row IDs/payload digests, exact anchor epoch/metric/direction/surface/recipe/request grouping, reporter version/parameters, and output digest. The strict reader delegates grading to `claim_tuple.grade()` and cannot infer a causal policy improvement, cost-credit score, or champion gain from an observed historical trajectory. Source: `autokernel-research-loop.md` AK-plateau pack (intake-1440#record, intake-1446#record).

## VB-AK-LINEAGE — AutoKernel code-lineage diagnostic capture (filed 2026-09-17)

- [ ] **VB-AK-LINEAGE — finish prospective AutoKernel lineage source/outcome binding before the first real diagnostic run.** The default-off source/patch capture helper and offline line-level detector do not themselves authorize a run. At authoring, the producer must mint a durable attempt ID, bind it to the original outcome row, capture immutable parent/child source bytes and patch, and export verified `programs.jsonl`/blobs/capture receipts. Add strict read-side ClaimTuple projection of producer-authored diagnostic measurements; never backfill from overwritten `<mechanism>.<lane>.patch` paths or tree hashes. No live search-policy or promotion authority. Source: `autokernel-research-loop.md` AK-lineage diagnostics (intake-1451#record, intake-1458#record, intake-1442#record).

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
- [x] **VB-READBW-DS41 — route ad-hoc `bench_readbw` runs into the INF-70 corpus.** Point `readbw_gap.sh` (and future AK readbw probes) at `/mnt/raid0/llm/tmp/inf70/results-<tag>-<UTC>/c0-readbw.txt` and emit `OMP stack ON` in banners when the stack is set; then ingest the 2026-09-26T10:55:35Z run (raw bytes unchanged; the directory stamp equals the file header) via `cli.py ingest inf70 --as-of <ts>`. Acceptance: 24 readbw claims, `omp_stack=ON`, source sha matches the raw file. No new adapter or ladder.
  - [x] Producer fixed ✅ 2026-09-26: `readbw_gap.sh` now writes `/mnt/raid0/llm/tmp/inf70/results-ds41scope-<UTC>/c0-readbw.txt` and banners carry `OMP stack ON`.
  - [x] 2026-09-26T10:55:35Z run ingested ✅ 2026-09-26 (operator-authorized): 24 readbw claims, 72 frames, via an isolated root `/mnt/raid0/llm/tmp/inf70-ingest-ds41scope` (symlink to the corpus run; the ingest does not dedupe, so the full corpus was not re-walked). `omp_stack` projects `unstated` because the raw banners predate the fix — raw bytes kept unchanged rather than rewritten.
  - [x] `omp_stack=ON` acceptance ✅ 2026-09-26: `results-ds41scope-20260926T135451Z/c0-readbw.txt` (run in the DS41 10h→10i pause) ingested, 24 claims tagged omp-on. Note: its full-screen t=96 read-sum sample is 178.9 GB/s vs 449.4 at 10:55Z (t=48 408.1 vs 399.6; half screen consistent) — a single anomalous sample, not a new ceiling; repeat before quoting t=96.

- [ ] **VB-SPEECH-CPU-1 — write side for `speech_cpu_bench.py`, before any CPU speech re-measurement** (KVU-11 B/C).
  - Add a schema version, row hash, whisper/qwentts binary digests, the exact core list and thread count, and
    `SHIM_NPROCS`. Also capture the co-tenant state: frontdoor `-t`/cores and whether it was generating, sampled
    during the row.
  - Then the adapter. Carry the three cautions from the source row: layout is part of the measurand, the shim is
    the only thread control, and co-tenant state decides the result.
  - [ ] **VB-SPEECH-CPU-1a — write side for `live_llm_contention.py`** (the addendum-3 harness, research
    `6afc7eed`; added 2026-09-24, wrap-up #4). Its `raw/live_contention.jsonl` rows carry RTF, first packet and
    `llm_overlap` but no schema version, row hash, binary digests or the co-tenant LLM's pid/argv/cores. Add them
    (sampled during the row), and record each speech request's cap and whether a guard aborted the arm, so a
    capped or aborted row can never read as a completed measurement.

## VB-SPEECH-CONV-1 — conversation-stack voice measurements (filed 2026-09-24, speech vision session)

The operator ratified the speech vision on 2026-09-24. It lives in
[`conversation-stack.md`](conversation-stack.md) (INF-79), and it will produce a new measurement family:

- the interlocutor bake-off on a PyTorch reference harness;
- GPU co-residency and CU masking on the second MI210;
- end-to-end voice turns;
- a quantization ladder for the ported model.

No run exists yet, so the write side is filed **before** the first run. The row is in
`scripts/vidya/adapters/README.md` → *Known and candidate sources*. Owner: INF-79.

- [ ] **VB-SPEECH-CONV-1 — write side for the conversation-stack harnesses, before the first CS-8/CS-9 run.**
  - Every harness row carries: a schema version, a row hash, `protocol_id` (null until the CS-2 Annex S amendment
    is ratified, so the row is an observation), reps and reps basis, `metric` with an explicit per-metric
    `metric_direction`, the model and quant, the runtime (reference vs port) with binary or upstream digest, the
    device and host-lane placement, and the co-tenant state (LLM, device, np, generating yes/no) sampled during
    the row.
  - Then write the adapter (`@register("conversation-stack-measurement")`, `attestation_locator`, a `Source(...)` row).
    Project, do not grade: `claim_tuple.grade()` decides.
  - Carry the four cautions from the source row: mixed directions, co-tenant state as measurand, LLM-judged fidelity
    (SC58), and reference-harness numbers as never being serving claims.

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

- [ ] **VB-ROUTE-LAT — wire the write side of routing-decision latency telemetry** (`routing-intelligence.md`
  RI-16). The producer emits per-request, per-stage timings (role priors, route, mode, review gate) with backend
  and index size; then author the read-side adapter. Locator = request x stage aggregated to a run window;
  never project the unmeasured "<1 ms / 10-50 ms" doc figures.
  - Progress 2026-09-30: the producer exists. Orch `78847544` (RI-16) writes `routing_path` + `stage_ms` into the
    progress JSONL `routing_decision` and `task_completed`/`task_failed` events, and it serves from 2026-09-30 04:52Z
    (API PID 1930724). Still owed: backend, index size and `instrument_class` on the producer, a ClaimTuple-shaped
    sidecar or strict reader, the adapter and a `cli.py ingest` verb. Source-table row updated.
- [ ] **VB-UFH12-RETR — wire the write side of the UFH-12 retrieval eval** (`repl-embedding-retrieval.md`
  REPL-EMB-2.1/2.2/2.3) before its first run: per-arm recall@k, CPU-s, latency, with the pre-registered rule,
  corpus digest and embedding-model identity; the online `spill_pointer_follows` shadow is a separate instrument.
- [x] **VB-UFH12-PLACEMENT — wire the write side of the embedder placement gate** (`repl-embedding-retrieval.md`
  REPL-EMB-0.2 / 1.4; `epyc-orchestrator` `scripts/server/embedder_placement_gate.py`) before the REPL-EMB-1.4 G1
  re-measure. Done 2026-09-27: write side `scripts/server/embedder_placement_capture.py` (orch lane
  `lane/repl-emb-gate-capture-20260926`, on top of `lane/repl-emb-11-14-20260926`) emits
  `<record-stem>.belief_measurements.jsonl`; read side `scripts/vidya/adapters/embedder_placement_gate.py`, ingest name
  `embedder-placement-gate`. Schema and refusals: the source-table row in `scripts/vidya/adapters/README.md`. The
  2026-09-26 Phase-0 files stay retrospective. A G3 re-run must write an `epyc.embedder_placement_g3.v1` record through
  the same `CaptureWindow` (the Phase-0 G3 driver is an out-of-repo tmp script).
- [ ] **VB-UFH12-PLACEMENT-DISC — make `embedder-placement-gate` discovery recurse into `arms/`** (filed
  2026-09-27). The A0 and A3 arm sidecars live at
  `epyc-orchestrator/data/embedder_placement/arms/<run>/<N>-{base,cand}.belief_measurements.jsonl`, nine files. But
  `scripts/vidya/ingest_sources.py`'s `Source("embedder-placement-gate", ...)` globs only `*.belief_measurements.jsonl`
  at the root, so `cli.py ingest` never sees them.
  - Add `arms/*/*.belief_measurements.jsonl` (or `*/*/…`, following the `kv-quant-27b-v10-measurement` pattern).
  - Add a discovery test over a two-level fixture.
  - Confirm the nine arm sidecars project, and that any refusal names its reason.
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
    A `compactions.unfinished > 0` call is censored. These arms are pre-hook too: copy `results/C{2,4}/cxa+a*` durably first.
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
- [ ] **VB-V11FA — write side for the v11 FA routing A/B slot and the DF2-9 model probe** (filed 2026-10-04,
  workspace-ec, CLAUDE.md *Belief Kernel*).
  - Producers: `gpu_slot_v11fa.sh` → `slot-<ts>/summary.txt` and `perf_table.tsv` (µs per FA op × layout × rows ×
    n_kv × arm), `det/` exactness, `tbo/` counts; `fa_nan_probe` per arm (verdict, runs_nonfinite, first bad node).
  - Durable copy: `artifacts/v11-fa-ab-20261004/`.
  - Bind the arm build and commit, the ROCWMMA flag, the cherry-picks and the knobs.
  - Cautions: (1) kernel µs is not serving tok/s; (2) the server DF2-9 arm has no verdict (port busy); (3) a probe
    PASS is 0/10 on the named prompts only.
  - Grade via `claim_tuple.grade()`; no new ladder. The source-table rows are applied in `scripts/vidya/adapters/README.md`.
  - Done when an adapter projects both slots' perf tables and the per-arm probe verdicts.
- [ ] **VB-LONGCTX-KERNEL — write side for the DCA perplexity and FA-INT64-OFFSET slots** (filed 2026-10-04,
  workspace-ec).
  - Producers: `gpu_slot_dca.sh` and `real_model_ppl_cpu.sh` (PPL ± per arm), and `gpu_slot_fa_int64.sh`
    (`test-backend-ops` counts, bit-identity).
  - Durable copy: `artifacts/dca-yarn-kernel-20261004/`.
  - Bind the build commit, model, scored window and device.
  - Cautions: one window per arm, and the GPU-vs-CPU offset is unexplained (YARN-DCA-XDEV).
  - Grade via `claim_tuple.grade()`; no new ladder. The row is applied.
  - Done when an adapter projects both slots' summaries.
- [ ] **VB-SERVE-TIMING-1 — read side for the orchestrator per-call serving records** (`epyc.orchestrator.serving_call.v1`, orchestrator `src/backends/serving_calls.py`, orch main 9a0d38e0; filed 2026-10-03 from the workspace-89 prefill-share analysis). The write side is LIVE since 2026-10-03T04:59Z (orch 9a0d38e0 on main, API reload); the launch sidecar goes live at each server's next stack launch. Strict adapter steps:
  - discover `logs/serving_calls/serving_calls.jsonl*`;
  - refuse lines whose `record_sha256` does not re-derive, or whose schema is not `serving_call.v1`;
  - project each `timings` metric (`prompt_ms`, `predicted_ms`, `prompt_per_second`, `predicted_per_second`, `draft_n_accepted/draft_n`) plus `queue.pre_dispatch_wait_ms` into `ClaimTuple`, with unit and `metric_direction` fixed by the schema (ms and wait: `lower_better`; t/s and acceptance: `higher_better`).

  Rules for what gets projected:
  - Carry `server.argv_sha256`, `server.binary_realpath`, `server.model_path`, `provenance.orch_commit` and `provenance.run_id` as identity, never graded.
  - Skip `timings_source="absent"` rows; never emit zeros.
  - Mark `server.identity_source="absent"` rows unscoped rather than inferring the launch.

  Grading: `Judged/Located` via `claim_tuple.grade()`; no new ladder and no backfill.

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

- [ ] **VB-YARN-DEPTH-RECIPE — write side and adapter for the q36 depth-recipe native-window validation** (filed 2026-10-05,
  workspace-ec). Producer: `q36_depth_recipe.py` on Qwen3.6-35B-A3B CPU, canonical :8070 recipe, 2026-10-05 12:10Z.
  Record shape: per (arm: native vs YaRN ×2) and (depth: 0%/30%/50%/70%/90%), needle correctness, decode tok/s, and
  MTP acceptance; summary.json and summary.md durable copies in `artifacts/yarn-native-window-20261005/`.
  Verdict: static YaRN ×2 **FAILS the operator rule** "YaRN must not regress inside native window" (1.3% cost at depth 0,
  7.6% at 34k decode, MTP 53%→48%, greedy diverge 7/20). Grades as `Judged/Located`, not qualified measurement.
  Done when the adapter projects the result and the verdict rides through the fold.

## VB-KVU-PF — KV prefix-fork program measurement sources (filed 2026-10-04, ak-ds41-main)

- [ ] **VB-KVU-PF — write side + projection for RTG-58's measurement records** (CLAUDE.md *Belief Kernel*). Producers:
  [`kv-prefix-fork-and-paged-attention.md`](kv-prefix-fork-and-paged-attention.md) KPF-18 (fork-vs-fresh equivalence + TTFT),
  KPF-26 (trunk-first dispatch), KPF-33 (sequence-affine allocation), KPF-42 (`kv_rows` A/B vs KVU-19b), KPF-53 (cascade).
  Record shape: per-run JSON with binary sha, argv, arm, prompt-set hash, equivalence verdict, TTFT, prefill tokens,
  unique cells, decode tok/s. Wire the write side before KPF-18's first run; project into `ClaimTuple` and let
  `claim_tuple.grade()` decide — one ladder, no new grading rule. Done when KPF-18's runner emits the record and the
  adapter projects it.

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
  ordinary validation evidence. Owner: Codex NI05-15; scratch `/mnt/raid0/llm/worktrees/codex-ni-ci-capture-20261005`.

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
- [ ] **SC-EVL42-PIN-REPORT-WIRING — bind future categorical pin-scan findings at write time and prepare their existing-ladder projection.** Preserve exact checker/scanned-source byte identities, Git HEAD/dirty context, scan membership and per-row current/stale/missing/unresolved reasons before the original scan is consumed. MAIN reviews the native record-to-ClaimTuple projection; no second ladder, retrospective warrant, numeric performance claim or automatic pin repair. Synthetic CI acceptance does not complete actual-scan wiring.

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

✅ 2026-10-07 VB-RVP-SSM-ROLLBACK-CONFORMANCE: [MAIN actual original3/3 and experimental source publication](../../artifacts/ni08/rvp-rollback-success-acceptance-20261007/README.md). Actual64 raw initializer captures/CPU-reference replay; no production/GPU regression, live event, performance or promotion warrant.


## Prospective shared helper and test-log isolation source controls — 2026-10-07

- [x] **VB-S49-MTMD-PROBE-CONFORMANCE — bind the shared executable-discovery helper and its distinct callers before hosted synthetic capture.** Bind exact APP source/test/config/import pins, all selected cases, the runner-only configuration (including explicit hosted timeout control), original argv/JUnit/status and complete source readset through the existing native CI producer and `ci-fixture-conformance` adapter/shared grader. The bounded suite covers the common Bash executable/LD-library-prefix/timeout/status/output contract, symlink target resolution, strict versus tolerant Python parsing, resolver order/overrides, and the exact real bounded timeout child-death control. Preserve every original result and failure. No configured model/server binary, inference, build, performance, promotion, or runtime-use warrant; no new source class or grading ladder. MAIN independently reopens source and original custody before acceptance. ✅ 2026-10-07 — [MAIN acceptance](../../artifacts/ni08/s49-mtmd-probe-success-acceptance-20261007/README.md): original37597364740 TRUE11/11,63 frozen Git inputs/65 native reads,29 packages/all412 wheels; prior NULL/setup originals retained. Source published APP7134d796; runtime warrant remains excluded.

- [x] **VB-SCG-TEST-LOGDIR-CONFORMANCE — bind the real pytest bootstrap and progress-log construction-time destination controls before hosted capture.** The actual root conftest establishes a unique temporary environment override before application imports; the real no-argument logger writes during test execution. Bind the complete actual conftest/AppState/import/dependency closure, unchanged selected module cases, private default-destination sentinel preservation, isolated rows, explicit constructor precedence, ordinary runtime default without override and teardown environment restoration through the existing native CI producer/shared grader. No collection-time logger construction is claimed: the current real API construction is inside lifespan initialization. No copied bootstrap, --noconftest shortcut, shared-host tests/log writes, API/model/server activity, inference, deployment or new grading ladder. MAIN reopens original source/JUnit/custody before acceptance. ✅ 2026-10-07 — [MAIN source/original4/4 acceptance](../../artifacts/ni08/scg-test-logdir-success-acceptance-20261007/README.md), APPb87998e3; actual root bootstrap/real during-test logger, constructor override/default/sentinel/teardown and authenticated temporary JSONL copies. Original NULL/setup evidence unchanged; no shared-host tests/logs or runtime warrant.

- [x] **VB-NI08-FAILED-ORIGINAL-CUSTODY — independently authenticate the twelve retained failed native/setup endpoints without regrading or rewriting outcomes.** ✅ 2026-10-07 — [MAIN exact original-record review](../../artifacts/ni08/failed-original-custody-review-20261007/README.md) binds fresh API/ZIP/receipt/attachment/JUnit identities:10FALSE,1NULL,1setup with no receipt. No implementation, source-validity, deployment or scientific warrant is inferred.


✅ 2026-10-07 VB-EVL42-PIN-REPORT-CONFORMANCE: [MAIN exact source and original29/29](../../artifacts/ni08/evl42-report-success-acceptance-20261007/README.md).10unique nested original seals retained (8TRUE/1FALSE/1NULL),13archive path copies only;11symlink/91empty-directory archive limitations explicit. Actual pin-health scan/wiring remains independently open.


- [x] **VB-K11-REPEAT-SUMMARY-CONFORMANCE — bind the actual requested-repeat summary producer and full synthetic controls before capture.** Exact Research source/test blobs, complete eager source/config and lock-wheel closure, actual run_execute fake-server/persisted per-run and summary TRUE/FALSE/NULL tests, original nonpositive-repeat refusal and owned-process cleanup; existing native verifier/CI family/shared grade only. No server/model, kernel build, live determinism or new ladder; original source/result/readset/API/JUnit custody retained at capture. ✅ 2026-10-07 — [MAIN exact source and original30/30](../../artifacts/ni08/k11-repeat-summary-success-acceptance-20261007/README.md). Live K11 determinism remains independently gated.

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

- [ ] **VB-DS41-C26-CANCEL-CONFORMANCE — bind the bounded DS41-C26-CANCEL-SOURCE original controls.** Freeze Research0858dc64 four-file candidate, whole20 CPU/GPU startup parameter cases and all26 test_serving methods, full selected source/config/deferred-import envelope and separate APP70096 lock11packages/ALL156 wheel hashes. Real Popen/server/region-lock seams are mocked; GPU quiet-window seam is explicitly nullcontext. Existing native CI producer/projector/shared grade, exact pre-grade/error/final source/result/API/ZIP/JUnit custody only. MAIN publishes enrollment before final recipe/K/capture and reviews originals before source publication. Parent mixed-runtime stop behavior, live serving, inference, quality/performance and production promotion remain separate; no new source/grade ladder.

2026-10-07 second capacity-source association: existing VB-NI08-SPARSE-CAPACITY-CUSTODY / VB-NI07-DOC-DEPS expands to the [original second-request safe-alternate custody](../../artifacts/ni08/sparse-capacity-second-request-20261007/README.md). MAIN completed exactly two additional idle historical Research worktree hydration exclusions. The semantic full indexes, source metadata/bytes, HEADs, branches, KEEP and Git objects remain preserved; only tracked duplicate benchmarks/data copies were sparsely excluded. Allocated recoverable copies totaled **3,360,518,144 bytes**. Original final free-space samples **111,330,381,824** and **111,329,828,864 bytes**, **54.629409002 seconds** apart, both exceeded the **110,500,000,000-byte engineering target** and 100 GiB hard floor. This safe alternate does not promise eight billion bytes of recovery or inference admission. Original helper/manifest/process/command/sample custody stays ungraded through existing VB-NI07-DOC-DEPS handling; no new ClaimTuple, ladder, native test, inference or runtime warrant. One operational child is completed; no additional source class or grade is introduced.

2026-10-07 three-view operational source association: existing VB-NI07-DOC-DEPS / VB-NI08-SPARSE-CAPACITY-CUSTODY expands to [bounded original three-view custody](../../artifacts/ni08/three-source-view-sparse-custody-20261007/README.md). MAIN accepted the guarded sparse materialization of exactly three own unused committed source views: two C26 Research views retain four physical source files each and the UFH ROOT recipe view retains three. All eleven kept source byte/mode/physical-metadata records, semantic full indexes, HEADs, branches, Git objects and the existing ignored cache remain conserved. The 302 original command records and three completed checkpoints are retained unchanged; both earlier eligibility refusals remain separate originals with no sparse application. Raw index cache inode/mtime/ctime volatility was explicitly reviewed before apply. This is ungraded operational source-view custody through existing VB-NI07-DOC-DEPS handling; it closes no native/source task and asserts no measured allocated recovery, free space, runtime activity, inference admission, grade or new ladder. One operational child completes; no native/source checkbox closure or new grading rule.


## RTG-39 administrative source reconciliation — 2026-10-07

The existing literature association for intake-913#record is retained. MAIN closed the two source/documentation tasks in the blocked RTG-39 owner and corrected its two stale recommended-action strings, leaving verification status, source claims, dive corrections and native ledger unchanged. The [inert data contract](../../docs/design/experience-distillation-data-contract.md) defines provenance only and produces no source record; prospective teacher/student producer wiring remains required before any future execution. No new checkbox, adapter, ladder or current warrant is created.

## TD-29.M0a raw prefill source controls — prospective companion

- [ ] **VB-TD29-PREFILL-SOURCE-CONFORMANCE — bind the whole-module `/completion` prefill controls before off-host capture.** After MAIN pins the prospective ROOT filing and the APP source commit, capture the complete `test_llama_server.py`, `test_inference_mixin.py` and `test_typed_decisions_call_recorder.py` modules, their 119 AST test definitions as currently pinned, exact function bodies, in-module fixtures, both applicable conftests, `pyproject.toml`, and `uv.lock` with every locked package version and wheel hash. Preserve the exact existing controls `TestEarlyStopTiming::test_early_stop_produces_timing`, `TestRecordLlmCalls::test_every_call_is_logged_and_summed`, and `TestRecordLlmCalls::test_absent_telemetry_is_none_not_zero`; do not substitute guessed test names. Bind ROOT's existing native CI producer, verifier, adapter, shared ClaimTuple carrier, exact command/readset and original request/log/JUnit/receipt before execution. The original JUnit supplies actual collected/executed counts; AST counts are source inventory only. Existing `ci-fixture-conformance` and `claim_tuple.grade()` remain the sole verifier/ladder. No inference, sidecar/runtime/three-arm claim, performance result, source-quality claim, duplicate parent closure or new grading rule. Capture remains pending MAIN's prospective filing and execution authorization.

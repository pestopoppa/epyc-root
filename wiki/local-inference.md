# Local Inference

**Category**: `local_inference`
**Confidence**: verified
**Last compiled**: 2026-09-18 (TD-1d re-measured at n=4: id-only 9.60x not 11.98x, the `inference_lock` serialization and the SSM checkpoint-quantized prefix reuse behind fan-out losing, `/v1` dropping `grammar`); 2026-09-17 (wrap-up sweep: the typed-decision worker-measured readout — id-only cue 11.98x at 15/16 agreement, batched fan-out 2.2x at 87.5%, and the llama-server multi-slot readout limit; sources: typed-decision-plane final rounds, the intake session record, vidya VB-TDP-1); 2026-09-17 (research-intake delta: PAW compiled specialists on the frozen v9 stack, the license-scope ruling, and the honest local one-pass speedup; incremental: rtx6kpro steals measured: p-min no-op on DFlash2, longest block wins, A/A noise absent at temp 0, RNG lead ruled out, steps/s only estimated); earlier: 2026-09-08 (the rtx6kpro intake — a same-class 96 GB single-GPU local-inference field wiki read for stealable hypotheses: p-min sweep, steps/s keep gate, long-context + sustained-C8 cells, A/A losslessness control, the RNG-entanglement lead, and the contradictions/non-transferables vs our record; earlier 2026-07-31 note: adds the ggml-linkage landmine: `LD_LIBRARY_PATH` ordering silently loads the frozen production CPU-only ggml into fresh HIP builds, producing full-CPU runs that self-report `use gpu = 1`; every future ggml build on this host is exposed; earlier 2026-07-20 note: adds the deployed-lane throughput table, the living model-probe scoreboard + stop-list, and the CPU-prefill local lever; earlier 2026-07-19 note: adds v7 promotion boundary, GLM reviewer residency decision, and post-promotion P-GPU-1 certification)
**Sources**: 45 documents (added 2026-09-18: the TD-1d re-measurement record, typed-decision-plane TD-1d.0–1d.4) (added 2026-09-17 wrap-up sweep: typed-decision-plane TD-1b/1c/1d/TD-3b, the intake session record, and vidya VB-TDP-1) (added 2026-09-17 research-intake: paw-compiled-specialists, typed-decision-plane, vidya-belief-substrate VB-TDP-1, and the intake session record) (added 2026-09-17: dflash2 handoff, sub-akfix, sub-gpu-prep, gpu-candidates)

## Compiled Update — 2026-09-18: the id-only readout re-measured at n=4, and two mechanisms behind fan-out losing on this GPU

**Confidence: verified** for the run (frozen-v9 HIP server, Qwen3.6-35B-A3B-Q8_0, MI210, 4 slots, ctx 131072, fa on, temp 0, host threads `taskset -c 184-191`, `LD_LIBRARY_PATH` pinned to `build-hip/bin`; launched and killed by the session, VRAM 59% in all 24 in-run samples). These correct the 2026-09-17 section below, which was one run per arm.

### Key findings

- **Corrected readout, n=4 alternated rounds, same catalogue and state hash**: JSON 14.02 ± 1.82 s; `full` 6.52 ± 0.05 s (2.15x); `short` 3.03 ± 0.12 s (4.63x); **`id_only` 1.46 ± 0.03 s (9.60x)**; `pq1` (1 slot) 2.09 s (6.69x); `pq3` (3 slots) 5.24 ± 0.93 s (2.67x); `pq3_id_only` 2.27 ± 0.45 s (6.17x). Agreement 15/16 in every round. The native times reproduce the 09-17 numbers; the 09-17 JSON baseline (19.3 s) does not — it is above the four-sample maximum here. Per decision (16 native vs 24 JSON) the id-only lead is 6.40x. The 09-17 acceptance is under TD-1d.0. ([typed-decision-plane](../handoffs/active/typed-decision-plane.md), [td1d-remeasure](../progress/2026-09/2026-09-18-td1d-remeasure.md))
- **Concurrent in-process `llm_call`s are serialized by the cross-process `inference_lock`** (TD-1d.2): parallel wall == serial wall, max 1 slot busy. This is the primitives-layer counterpart of the `heavy_model` lock observation and constrains every fan-out design on this stack, not just typed decisions.
- **`qwen35moe` is hybrid-recurrent (SSM layers), so prefix reuse is checkpoint-quantized** (TD-1d.3). Back-to-back per-question reads on one slot reuse **0** tokens (~450 ms each) unless a prefix-only request first leaves a checkpoint at the prefix end (then `cache_n` 1105, ~128 ms/read); under 3-way concurrency they stretch to 585–900 ms. Any prefix-cache reasoning about this model class has to include the checkpoint boundary.
- **`/v1/chat/completions` forwards neither `grammar` nor `json_schema`** (TD-1d.1): through `frontdoor` the native arm produced 515 free-form tokens and 0/24 decisions. Every measured arm used a direct `/completion` adapter. No typed-decision arm is deployable through `LLMPrimitives` until `/v1` forwards the fields for internal callers or a declared direct lane exists.

### Open questions

- Is the checkpoint-quantized prefix reuse specific to `qwen35moe`, or does every hybrid-recurrent GGUF on this server behave the same way?
- Does a prefix-only warm request per slot make option (b) viable, or does the `inference_lock` make the question moot?

### Source References (2026-09-18)

- [2026-09-18-td1d-remeasure.md](../progress/2026-09/2026-09-18-td1d-remeasure.md) — server recipe, residency proof, the table.
- [typed-decision-plane.md](../handoffs/active/typed-decision-plane.md) — TD-1d.0–TD-1d.4.

## Compiled Update — 2026-09-17 (wrap-up sweep: the typed-decision readout measured on the worker — 11.98x native at parity, and the generation-API limit behind it)

**Confidence: verified** for the worker runs (Qwen3.6-35B-A3B-Q8_0, MI210, frozen-v9 HIP server launched and killed by the session; one run per cue style on a 24-question fixture); **external** for the intake contrast figures. These are worker-throughput observations, not serving headlines.

### Key findings

- **The local one-pass typed readout is now measured end-to-end, not just cited.** TD-1's JSON arm ran the 24-question fixture 24/24 clean (36.7 s on the 27B). TD-1b fixed the native candidate path to tokenize candidates through the server `/tokenize` seam and build exact-token grammar terminals, so the earlier 23/24 `native_unknown_candidate` failures fell to zero; candidates that tokenize to multiple tokens are explicitly unsupported and fall back to JSON (8/24 on this fixture). ([typed-decision-plane](../handoffs/active/typed-decision-plane.md))
- **TD-1d cue sweep, same 35B / same fixture / one run each**: JSON 19.3 s / 1,354 tok; native `full` cue 7.3 s (2.66x) / 523 tok; `short` cue 3.2 s (6.0x) / 239 tok; **`id_only` cue 1.6 s / 112 tok = 11.98x**, all three native styles at 15/16 agreement and 15/16 accuracy on the overlap (JSON 14/16 on the same 16). The prompt catalogue carries the grounding; the id-only cue re-anchors position. TD-6 (adopt `id_only` as the native default after review) is open. ([typed-decision-plane](../handoffs/active/typed-decision-plane.md), [session record](../progress/2026-09/2026-09-17-intake-jev-sageattn.md))
- **The multi-slot logit readout does not exist in llama-server's generation API, so the vendor's parallel-sampler shape stays out of reach.** Parallel per-question native reads were tested and rejected on this stack: the exclusive `heavy_model` lock serializes workers (client concurrency 0.65x vs batched) and the generation API exposes no multi-slot logit readout. Batched fan-out is the available lever instead: 1.54x at small state (100% agreement), 3.22x long-context (three 40k-char states), and 2.2x at 87.5% agreement on the real 24-question catalogue (TD-3b, 17.2 s batched vs 37.9 s singleton). ([typed-decision-plane](../handoffs/active/typed-decision-plane.md))
- **The native arm fails closed, and its speed is not a serving authority.** A failure surfaces as a typed error (`native_unknown_candidate`) rather than a wrong answer; semantic parity had to be earned separately (TD-1c: the 5/16 disagreement was prompt cueing — later positions were conditioned on prior answer tokens — fixed by replaying each question's cue as tokenized grammar terminals). Confidence is **not** calibrated (ECE 0.0625 on the 27B, 0.267 on LFM2.5-2.6B), so no gate may threshold on it. ([typed-decision-plane](../handoffs/active/typed-decision-plane.md), [benchmark methodology](benchmark-methodology.md))
- **The write side was wired before the runs.** `scripts/vidya/adapters/typed_decisions_measurement.py` projects the TD-2/TD-3/TD-4 receipts into self-hashed ClaimTuples (VB-TDP-1, write side first); a bench report is refused as a non-measurement. ([vidya-belief-substrate-program](../handoffs/active/vidya-belief-substrate-program.md))

### Open questions

- Does the id-only cue's 11.98x hold across a second run and a second model, or is it a single-run artifact?
- Does any runtime in consideration expose a multi-slot logit readout, or is batched fan-out the ceiling for the parallel-sampler shape?

### Source References (2026-09-17 wrap-up sweep)

- [typed-decision-plane.md](../handoffs/active/typed-decision-plane.md) — TD-1b/1c/1d, TD-3b, the cue sweep and the parallel-read rejection.
- [2026-09-17-intake-jev-sageattn.md](../progress/2026-09/2026-09-17-intake-jev-sageattn.md) — the four implementation rounds and the worker runs.
- [vidya-belief-substrate-program.md](../handoffs/active/vidya-belief-substrate-program.md) — VB-TDP-1 write-side rule.
- [benchmark-methodology.md](benchmark-methodology.md) — the contamination/calibration/fan-out measurement design.

## Compiled Update — 2026-09-17 (research-intake delta: compiled specialists on the frozen stack, and the honest one-pass speedup)

**Confidence: verified** for the filings and the license ruling; **external** for the intake figures (dive-verified primary sources; the 5.21x was measured on a 3090, not this host). The re-opened PAW line and the local typed-decision readout both target the frozen v9 stack.

### Key findings

- **PAW is artifact-available but not officially self-hostable.** Compiler weights (2026-06-07) and FuzzyBench eval data (2026-02-17) both predate the 2026-07-11 "compiler is CLOSED" blocker recorded in intake-811 — the re-open trigger is MET on availability. An unofficial MIT self-hosted compile server compiles for the default Qwen3 compiler (intake-1481#record), with no ROCm proof, and the Compact GPT-2 SDK-compat claim was overturned. Independent eval on one adversarial task: standard 94 / finetuned 97 / compact 85 (n=100, author labels); semantic abstention 98.9% on decided cases while logit-confidence thresholding fails (intake-1482). ([paw-compiled-specialists](../handoffs/active/paw-compiled-specialists.md))
- **License scope is resolved for internal work only.** Operator ruling (OP-43 closed 2026-09-17): "everything we do is internal research" — the unlicensed weights, the FuzzyBench dataset (43,128 + 7,550 rows, no train split) and the 7,226-program corpus are usable internally; no redistribution, no deployed-service use, no shipping of outputs. Distribution would re-open the question.
- **The local target question is open on economics, not capability.** PAW-2 must prove one end-to-end compile to a GGUF-ZIP `.paw` and one local call, including whether CPU-only is workable before MI210; whether the Qwen3-0.6B interpreter (594 MB Q6_K) is fast enough per call for always-on loops versus the current cheap-first models is filed as an open question.
- **The local one-pass readout's real numbers.** A fully local pinned implementation measures **5.21x vs same-model JSON on a 3090** and 20.03 decisions/s under parallel reuse (intake-1487); the honest pattern range is **3.4–7.9x**, not the vendor's 40–200x (intake-1474). Reuse drifts 5–6 of 777 argmaxes under BF16 — acceptable only where the consumer tolerates it.
- **No gate before calibration.** Candidate-softmax confidence is uncalibrated: 65% of a 7B's wrong fields scored >0.90 (intake-1474), and the owner stub makes local ECE/reliability (TD-2) the prerequisite for any gated use.
- **Write-side wiring precedes the first PAW/TD measurement run** — one self-hashed ClaimTuple per run at the vidya source table (VB-TDP-1). ([vidya-belief-substrate-program](../handoffs/active/vidya-belief-substrate-program.md))

### Open questions

- Compile-once economics without an accelerator: compile wall time vs adapter lifetime on this host.
- Does intake-1482's abstention finding transfer to our task slices, or is it task-specific?

### Source References (2026-09-17 research-intake delta)

- [paw-compiled-specialists.md](../handoffs/active/paw-compiled-specialists.md) — availability, license scope, PAW-2/PAW-3, and the open economics.
- [typed-decision-plane.md](../handoffs/active/typed-decision-plane.md) — the local one-pass mechanism (TD-1a) and the TD-2 calibration gate.
- [vidya-belief-substrate-program.md](../handoffs/active/vidya-belief-substrate-program.md) — VB-TDP-1 write-side requirement.
- [2026-09-17-intake-jev-sageattn.md](../progress/2026-09/2026-09-17-intake-jev-sageattn.md) — the session's verified findings of record.

## Compiled Update — 2026-09-17: the rtx6kpro steals, measured — two held, one was a no-op, one was ruled out, and one external noise figure does not exist here

**Confidence: verified** for our own runs on champion `ef81196d5` (unit = launch, residency proven on every launch). The external figures they answer keep their `external` grade from the 09-08 section below.

Four of the five hypotheses this page took from the rtx6kpro field wiki on 2026-09-08 now have local answers. The pattern is that the external observations transfer only after they are checked against our own source tree. A knob can be clamped or ignored by our build, and a noise band measured on another stack can be zero on ours.

### Key findings

- **The p-min half of the n-max × p-min sweep was a no-op.** On our DFlash2 build the drafter's block size is 8, so `--spec-draft-n-max 8` is clamped to 7, and the DFlash2 draft branch never reads `p_min`. The external per-position acceptance-decay argument therefore did not apply as posed. The longest block still wins at every in-flight level: +30% vs n4 at np1, +21% at np2, +16% at np4, and +5% (inside the floor) at np8. Verifier steps/s falls 19% at np8, as the external S6 predicted, but tokens/step rises faster. ([dflash2 handoff](../handoffs/active/dflash2-block-drafter-experimental-build.md))
- **The A/A losslessness control: the external identical-checkpoint noise (95.24 vs 90.69) does not exist here at temp 0.** Every arm reproduces itself 12/12 byte-for-byte across fresh processes. Pass counts are deterministic per (build, arm, prompt). ([dflash2 handoff](../handoffs/active/dflash2-block-drafter-experimental-build.md))
- **The RNG-entanglement lead is ruled out.** The drafter and verify samplers are separate objects, and at temp 0 / top_k 1 no RNG is drawn. The shared failing indices come instead from the batched-verify numeric split. Under a 1-row serial verify (`LLAMA_SPEC_EXACT=serial`), both spec arms are 12/12 bit-exact. The divergent tokens had top-1/top-2 logit margins of only 0.005–0.079. ([sub-akfix](../progress/2026-09/2026-09-16-sub-akfix.md), [dflash2 handoff](../handoffs/active/dflash2-block-drafter-experimental-build.md))
- **The steps/s keep-gate metric is only partly available.** The champion server counts verify steps but does not export them, so the loop reports an estimate (`predicted_n − draft_n_accepted`) and the gate is unchanged. ([sub-gpu-prep](../progress/2026-09/2026-09-16-sub-gpu-prep.md))
- **The long-context and sustained-C8 cell (SL-4) is still unrun**, so the external "DFlash2 −19% at sustained C8" vs our +47.8% contradiction stays open.
- **The same caution applies to MTP.** On production v9, the Qwen3.8 MTP n-max 8 grid came out below the older n-max 4 grid at np≥2 (cross-session observation). A single-stream depth optimum is therefore not assumed to hold for batched local serving. See [Inference Serving](inference-serving.md). ([gpu-candidates](../handoffs/active/gpu-candidates-surface-qwen38-update.md))

### Open questions

- SL-4: the ~32k context cell and the sustained-C8 cell.
- A same-window MTP n-max 4 vs 8 ABA at np≥2.

### Sources

- [dflash2-block-drafter-experimental-build.md](../handoffs/active/dflash2-block-drafter-experimental-build.md): the SL-1, SL-5 and DF2-8 results.
- [2026-09-16-sub-akfix.md](../progress/2026-09/2026-09-16-sub-akfix.md): the DF2-RNG source reading.
- [2026-09-16-sub-gpu-prep.md](../progress/2026-09/2026-09-16-sub-gpu-prep.md): the SL-2 estimator.
- [gpu-candidates-surface-qwen38-update.md](../handoffs/active/gpu-candidates-surface-qwen38-update.md): the MTP n-max 8 grid.

## Compiled Update — 2026-09-08: the rtx6kpro intake — a same-class local-GPU field wiki, read for our hypotheses

**Confidence: `external`** — third-party measurements (the intake's own credibility audit: ~35% rigorous-with-conditions, ~35% measured-but-underconditioned, ~20% attributed Discord anecdote — several retracted in-repo — ~10% config dumps). Zero llama.cpp/GGUF and zero ROCm content; every CUDA item was dispositioned with a gfx90a/HIP analog or an explicit "no analog".

The intake record ([`docs/research-intake/rtx6kpro-20260907.md`](../docs/research-intake/rtx6kpro-20260907.md), source pinned at upstream `44e817b`, 739 commits / 399 pages, active to 2026-09-07) is a community field wiki for exactly the class this page covers — serving frontier open-weight models on ONE 96 GB-class workstation GPU (NVIDIA RTX PRO 6000 Blackwell: SM120, 96 GB GDDR7, PCIe, no NVLink) with vLLM/SGLang plus their own kernel library. The local-serving-relevant steals, each filed to a local row:

- **`--spec-draft-n-max` × `--spec-draft-p-min` sweep under np4** — p-min has never been set on any GPU arm here; external per-position acceptance decay says draft positions 6–8 carry 10–30%, and n-max 7 makes the np1 verify batch exactly 8 (confound-free test of the MMQ-verify premise). Filed SL-1.
- **Verifier steps/s as the serving keep-gate metric** (`tok/s = steps/s × accepted/step`; only steps/s is a kernel property). Filed SL-2.
- **A long-context (~32k) cell + arm-order randomisation in the serving gate** (external: cc64 reads −15–20% after a 128k sweep; spec gain can collapse with context for some quants) — doubles as the sustained-C8 cell against external "DFlash2 −19% at C8" (vs our +47.8%). Filed SL-4.
- **An A/A control on the losslessness gate** before 7/12-vs-5/12 is read as a difference. Filed SL-5.
- **Draft RNG entangled with acceptance RNG** — the lead for why both DFlash2 AND `draft_simple` fail at identical indices (34/216/238). Filed DF2-RNG.

Full dispositions: [Speculative Decoding](speculative-decoding.md) (SL-1/2/4/5, DF2-RNG, RULE-RESCOPE), [Hardware Optimization](hardware-optimization.md) (kernel candidates AK-H-*, the MMQ-M=9..36 serving-verify finding, protocol rows R23-46/47, and the INF-70 CPU-path note).

**Contradictions with our record worth keeping visible** (flagged, not resolved): their spec-dec-vs-concurrency numbers contradict the "single-stream only" rule (RULE-RESCOPE filed); external "DFlash2 −19% at sustained C8" vs our +47.8% at 8 in-flight; their HIP-graph "4.3×" is vs an eager baseline while ours is +4..14%; power: they scale +30% at C64 from 300→600 W while our MI210 draws ~200 W of its 300 W — **re-check draw DURING np4 serving** (only proven under llama-bench/GEMM windows so far).

**Not transferable here:** GDDR7 memory overclock (+7–10% decode there) — MI210 HBM2e has no overdrive exposed under ROCm 6.2 on Instinct, and we run at 47% of HBM bandwidth, so clock is not binding (named, declined); FP8 KV as a hardware cast; NVFP4 weights/KV; vLLM/SGLang scheduler/loader/allocator internals; DCP-replicated drafts; WSL; multi-GPU PCIe/NCCL/topology. Their Qwen3.8 TP1/TP4 absolute numbers are not comparable to a 64 GB HBM2e llama.cpp Q8_0 path, and all their kernel-level numbers are CUDA-only (no HIP analog).

### Source References (2026-09-08, rtx6kpro)

- [`docs/research-intake/rtx6kpro-20260907.md`](../docs/research-intake/rtx6kpro-20260907.md) — credibility breakdown, the filed-candidate destinations, contradictions 1–10, and the complete not-transferable/deferred list.
- [`dflash2-block-drafter-experimental-build.md`](../handoffs/active/dflash2-block-drafter-experimental-build.md) — SL-1/2/4/5 and DF2-RNG filing rows.

## Compiled Update — 2026-07-31: a `LD_LIBRARY_PATH` ordering landmine silently redirects fresh ggml builds to the frozen production kernel

**Confidence: verified** — reproduced by a standing guard script; direct artifact read of the two
offending config lines.

### The mechanism

`/etc/environment:5` and `.devcontainer/devcontainer.json:57` both place the **frozen production**
kernel's `build/bin` early in `LD_LIBRARY_PATH`, on the reasoning that production tooling needs to
find the production libraries there. The unintended consequence: **any freshly built ggml-based
binary on this host** — whisper.cpp, `qwentts.cpp`, `llama.cpp-experimental` — resolves
`libggml-base` / `libggml` / `libggml-cpu` from the **production tree first**, ahead of its own build
directory, unless the invocation explicitly overrides the search order.

This is exactly what happened building the HIP whisper leg of the 2026-07-31 speech work (see
[Multimodal](multimodal.md)): a HIP-built `whisper-cli` loaded the production **CPU-only** ggml,
found no GPU backend, and ran the entire job on CPU — **while printing `use gpu = 1`**, because that
flag reports what was *requested*, not what was actually loaded. GPU backends are `dlopen`ed at
runtime and are therefore invisible to `ldd`, which is why this survives casual review: the binary
launches, reports a device, and produces plausible numbers.

### Why this is worse than an ordinary misconfiguration

The failure mode is **silent and produces plausible output**. A CPU-only fallback that crashed, or
that logged a visible warning, would be caught immediately. This one does neither — it is the same
"fail-open default conceals its own corruption" shape as other host-hygiene incidents on this project,
applied to shared library resolution instead of a service flag. Had nobody checked, CPU numbers would
have been published and labelled GPU.

### The guard, and the fix

`scripts/utils/verify_ggml_linkage.sh` reproduces the defect: of the five ggml-family shared
libraries a freshly built binary needs, **3 of 5 resolve from the production tree** even in a build
that also correctly picks up `libggml-hip.so.0` from its own directory — a mixed state that still
initializes and still reports a device, which is precisely why it is easy to miss on casual review.
The fix is **per-invocation** (prepend the project's own `build/bin` ahead of the production path for
that one command), **not** editing `/etc/environment` — production tooling genuinely depends on
finding the production libraries there by default, so the global ordering is not itself wrong, only
unsafe to inherit unmodified into a fresh build's environment.

### The generalizable rule

**Every future ggml build on this host is exposed to this**, not just the ones already discovered.
Any session building whisper.cpp, an experimental llama.cpp branch, or any other ggml-based project
on this host must run `scripts/utils/verify_ggml_linkage.sh` (or equivalently prepend its own
`build/bin`) before trusting a "GPU" number from that binary — `use gpu = 1` in the log is not
evidence the GPU backend was actually loaded.

### Source References

- `epyc-inference-research` commit `7f310022` — commit message cites `INC-20260731-ggml-linkage-silent-cpu-fallback`; the `verify_ggml_linkage.sh` guard and its 3-of-5 reproduction (as of this compile, that incident ID is not yet a filed heading in `docs/reference/agent-config/INCIDENT_LOG.md` — the commit is the primary record)
- [`progress/2026-07/2026-07-31.md`](../progress/2026-07/2026-07-31.md) — §18, the landmine summary and the "every future ggml build is exposed" scope statement
- [Multimodal](multimodal.md) — the HIP whisper build this defect was first caught on, and the corrected STT measurement it fed into

## Current Production — 2026-07-26

Production is frozen on `production-consolidated-v8` at
`67a433bf45a8a091d83b4ea0b32ff0735fd51800` (binary `10107`). The terminal
both-mode lineup passed 24/24 endpoint smoke and API 6/6, including the live
Qwen3.5-122B CPU Q4 architect at port 8083. The final freeze attestation is
[`ratify_v8_final_freeze_20260725.json`](../artifacts/operator/ratify_v8_final_freeze_20260725.json);
v7 at `6ad45fa3ff6718c07c000061dbc6e29c1771f6e3` remains the rollback/history
anchor.

## Compiled Update — 2026-07-20

v7 is promoted as `production-consolidated-v7` at frozen candidate `6ad45fa3ff` (binary `10098`). Two new reference artifacts organize the local-serving picture: a **deployed-lane throughput table** (what each role actually runs today) and a **living model-probe scoreboard** (how every candidate model/quant performs, all observation-grade). Confidence: `verified` for deployed CPU-lane facts and the OP-2 canonical control; `observation` for every MI210 throughput row that has not been rerun under `P-GPU-1`.

### Key Findings (2026-07-20)

- **v7 promoted; cutover complete.** Frozen-candidate gates were green: K5 quality +0.0%, OP-2 CPU-regression PASS (frontdoor Q8 tg128 canonical control `12.44 t/s`), final coherence+garbage smoke 4/4 non-vision + 3/3 vision, upstream-ahead narrow audit applied, live quarter-mode smoke `21/21`, and attestation clean except `gitnexus_stale_or_error=4`. The reviewer/control-plane route is **decoupled** from v7 (GLM failed P-REV-1, no clean replacement), so the banked production-model wins are no longer held hostage to it. ([v7-promotion](../handoffs/completed/v7-promotion.md))
- **Deployed-lane throughput (each "CPU opt" is the fastest deployed spec-dec+OMP config, NOT a no-spec baseline):** frontdoor Qwen3.6-35B-A3B Q8 native-MTP ~34.5 CPU / 119.7 GPU-MTP; worker gemma-4-26B-A4B Q4KM `ngram-mod,draft-mtp` 126/97/83 t/s (2K/8K/14K); architect Qwen3.5-122B UD-Q4KM 23.5/20.7; ingest Qwen3-Next-80B-A3B Q4KM 20.5/15.9/9.7; GLM-5.2 UD-IQ2 CPU-only 2.49→5.33 MTP. The MI210 fits everything but the 122B-Q4 architect and GLM-5.2 (~238 GB) — those are CPU-only. ([v7-stack-throughput-full-optimization](../docs/reference/v7-stack-throughput-full-optimization.md))
- **Model-probe scoreboard (living, glance-able, all OBSERVATION-grade):** clear wins = Qwable-v1 IQ4_XS MI210 (91–100 t/s), MiniCPM-o-4_5 Q4KM vision (111–127, `--reasoning off`), frontdoor 35B-A3B native-MTP, gemma-4-26B CPU worker (K5 +0.0%). Fast-but-quality-blocked = Bonsai Q1_0 (fails 6-word IF gate), Ternary Q2_g64 (6/8), gemma4 MI210 *natural free-form* (K11.1 nondeterminism, GPU-backend-path specific). Broken load = Ternary Bonsai Q2_0 (498/498 tensors short, noncanonical PrismML packing). Stop-list policy: **no speed-reruns without a named quality/loader/protocol/parser fix hypothesis.** ([model-probe-scoreboard](../docs/reference/model-probe-scoreboard.md))
- **CPU prefill is a real local lever for large/long-context models** — compute-bound `M>1` GEMM, distinct from the BW-bound decode roofline; the first landed experimental win is a default-off CPU `CONCAT` dim0 row-partition (`pp8192` +3–9% single-seq, batched prompt +22–54%). ([cpu-prefill-compute-large-models](../handoffs/active/cpu-prefill-compute-large-models.md))

### Open Questions (2026-07-20)

- The frontdoor **CPU-MTP** context curve on v7 is a measured gap (only the ~34.5 prod point exists; K35 measured GPU-MTP).
- GPU-worker eligibility for gemma-4 is unresolved (natural free-form multi-slot determinism fails, K11.1) even though the model fits.
- At this 2026-07-20 boundary, architect ≥32K context throughput was
  unmeasured and decision-grade reruns required the then-current
  `production-consolidated-v7`. Current reruns use the production-named v8
  kernel in the 2026-07-26 note above.

### Source References (2026-07-20)

- [v7-promotion.md](../handoffs/completed/v7-promotion.md) — promoted v7 cutover evidence, reviewer decoupling, post-promotion certification follow-ups.
- [v7-stack-throughput-full-optimization.md](../docs/reference/v7-stack-throughput-full-optimization.md) — deployed-lane vs candidate-bench table + provenance guards.
- [model-probe-scoreboard.md](../docs/reference/model-probe-scoreboard.md) — living per-model/quant scoreboard, verdict buckets, stop-list.
- [cpu-prefill-compute-large-models.md](../handoffs/active/cpu-prefill-compute-large-models.md) — CPU-prefill regime + CONCAT dim0 lever.
- [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md) — K11 gemma4 free-form determinism status.

## Summary

The project runs all production inference locally through llama-server (from a custom llama.cpp fork) serving GGUF-quantized models on the EPYC 9655 CPU, using 1.13 TB of DDR5 RAM. There is no cloud API dependency for inference and no network-dependent model serving. As of the **2026-07-25 v8 final freeze** the entire stack -- from a 0.5B draft model to a 122B architect -- runs on **ONE kernel, `production-consolidated-v8`** at `67a433bf45a8a091d83b4ea0b32ff0735fd51800` / binary `10107`. `GGML_IQK=1` supports IQ2/IQ3 and IQ4_XS as well as the existing supported types; IQ1 remains non-accelerated. The v7 kernel (`6ad45fa3ff6718c07c000061dbc6e29c1771f6e3` / binary `10098`) is the rollback/history anchor. The earlier 2026-06-26 v6 cutover consolidated the gemma worker off the separate `ik_llama.cpp` binary; **ik_llama.cpp is now fully deprecated — there is no second binary**. (The `production-consolidated-v3` fork described in the historical findings below is a prior era of the same lineage.)

As of **2026-07-02 an AMD Instinct MI210 (gfx90a, CDNA2, 64 GB HBM2e) is installed**, opening a GPU serving tier for the first time — earlier eras of this page correctly stated "no GPU," which is now superseded. The MI210 is a *latency tier on top of* the CPU+RAM tier, not a replacement: the fork's HIP build leg is verified on gfx90a and GPU-resident decode (including gemma4 NEXTN-MTP and qwen35 delta-net) runs clean and is fully insulated from the concurrent CPU stack. Vulkan is architecturally impossible on the compute-only MI200 family (no CDNA2 ICD exists); the GPU path is HIP/ROCm only.

The custom fork implements features critical for the orchestrator: native MTP/NEXTN self-speculation, MoE expert count override (hard mask / REAP), SWA slot reuse optimization, CPU paged attention for flash attention, server slot dynamic management, prompt n-gram lookup, tree speculation with DySpec, HSD capped branch resampling, and freeze-recurrent speculation for hybrid SSM models. Experimental work always happens in a separate worktree at `/mnt/raid0/llm/llama.cpp-experimental` (and isolated GPU worktrees such as `/mnt/raid0/llm/llama.cpp-mi210-hip`) -- the production repo is never used for debug or experimental builds.

GGUF model management follows a strict regime. Models reside on the RAID array at `/mnt/raid0/llm/models/` (~2.1 TB across 90 models) with HuggingFace source models at `/mnt/raid0/llm/hf/` (~850 GB). Q4_K_M is the standard quantization for most models -- empirically validated as optimal for both hybrid and dense architectures on this hardware. Q4_K_M matches f16 quality on the coder benchmark (74% vs 74%) while being 1.7x faster and using 3.5x less RAM. The only exception is the 7B worker (Qwen2.5-7B-Instruct), which runs at f16 because at 14 GB it fits easily in a NUMA quarter and benefits from near-flat verification curves.

Speculative decoding is the primary acceleration method. The production stack uses external draft models (Qwen2.5-Coder-0.5B at 185 t/s, Qwen3-Coder-0.75B at 181 t/s) with configuration validated by a comprehensive 1,290-measurement sweep. Key parameters are model-specific: coder_escalation uses dm=32/ps=0.05 (tree beneficial), architect uses dm=24/ps=0 (tree harmful), and the 480B coding architect uses dm=24/ps=0 (tree harmful at -19%, overturning prior assumption). No speculation is used on hybrid SSM models (Qwen3.5-*) -- all draft configurations are net-negative due to recurrent state overhead.

## 2026-07-19 Update — model residency follows role admission and measurement authority

- GLM-5.2 physically fits the host as a CPU-only reviewer candidate, but its roughly 224--225 GiB residency and failed C-CRAB P-REV-1 admission make always-resident production reviewer service unjustified. Keep it for diagnostics, repair validation, and matched ablations until a new route or admission gate clears it. Sources: [GLM RAM residency decision input](../docs/reference/glm52-ram-residency-decision-input-2026-07-18.md), [GLM reviewer capability gates](../handoffs/active/glm52-reviewer-capability-gates.md), [model-probe scoreboard](../docs/reference/model-probe-scoreboard.md).
- The repaired native GLM-MTP path is an available acceleration feature, not role admission: the CPU A/B reached `5.33` decode t/s and `alpha=0.933`, but the model remains out of the production patch-review role. Sources: [GLM reviewer capability gates](../handoffs/active/glm52-reviewer-capability-gates.md), [tree-draft forward-port plan](../handoffs/completed/tree-draft-forward-port-plan.md), [GLM RAM residency decision input](../docs/reference/glm52-ram-residency-decision-input-2026-07-18.md).
- Experimental-v7 residency and throughput observations informed promotion; production-named v7 reruns now carry the decision-grade GPU certification burden under P-GPU-1. Sources: [v7 promotion](../handoffs/completed/v7-promotion.md), [P-GPU-1 ratification package](../docs/reference/p-gpu-1-ratification-package-2026-07-18.md), [model-probe scoreboard](../docs/reference/model-probe-scoreboard.md).

## Key Findings

### New Findings (2026-07-02) — v6 single-kernel cutover, MI210 GPU tier, CPU/GPU MTP, and stalled ports

- **Historical 2026-06-26 v6-iqk cutover: one-kernel consolidation and ik_llama deprecation.** That cutover moved every hot role onto `production-consolidated-v6` (upstream framework + native MTP/NEXTN + our CPU kernels + ik's iqk AVX-512 GEMM, `GGML_IQK`-gated) and retired the separate ik_llama binary. Current production is now `production-consolidated-v8`; the v6 row remains the evidence record for the one-kernel architecture. [v6-iqk-promotion.md](../handoffs/completed/v6-iqk-promotion.md)
- **iqk kernels give ~+38% throughput at zero quality cost — matched full-port eval-parity.** On `worker_general`, IQK-on vs IQK-off over N=206 matched AA Omniscience questions (deterministic F1): accuracy unchanged (0.111650 vs 0.111650), avg F1 +0.008365, hallucination rate −0.010929, and throughput 38.46 vs 27.78 t/s = **1.38×**. This is the P-QUAL-PROMO eval-parity evidence; a clean post-reboot bench and any operator production-policy decision remain the only open tail. [v6-iqk-promotion.md](../handoffs/completed/v6-iqk-promotion.md)
- **An AMD Instinct MI210 (gfx90a, 64 GB HBM2e) is installed and the fork's HIP build leg is verified — GPU inference now works.** Isolated worktree `mi210-hip-enable` built with `-DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a`. One build break: ROCm 6.2 ships only `_fnuz` fp8 types (OCP landed in 6.3), so `ggml-cuda/vendors/hip.h` fp8 guard had to bump to `>=60300000` (committed `0ebf1b4d7`). Runtime gotcha: `BUILD_SHARED_LIBS=ON` binaries resolve the production CPU `libggml` via inherited `LD_LIBRARY_PATH` → SIGSEGV; must prepend the HIP build's `bin` + `/opt/rocm/lib`. [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md), [gpu-drafter-mi200-investigation.md](../handoffs/archived/gpu-drafter-mi200-investigation.md)
- **GPU-side MTP self-speculation works on the MI210 (evidence for the MTP head-split thesis).** gemma-4-31B-Q4_K_M target + the 514 MB NEXTN head both on ROCm0 (`--spec-type draft-mtp -ngl 99 --spec-draft-ngl 99`, server-only — the CLI/speculative example is not MTP-wired): decode **43.25 t/s = 1.44× over plain (30.01)**, draft acceptance 59.7% (163/273), mean accept length 2.79 of n_max=3. The per-step hidden-state hop is a ~µs PCIe memcpy, not CPU compute. [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md)
- **qwen35 (GDN / hybrid-SSM) decodes cleanly on the GPU HIP path — localizing the CPU spec failures to the CPU codepath.** Qwen3.6-27B-Q8_0 (arch `qwen35`, gated-delta-net + full attention) ran at 28.69 t/s with `-ngl 99` and no M-RoPE/GDN decode failures; the fork's `ggml-cuda` carries full delta-net/ssm-conv kernels (superset of the `dflash` tree). This contrasts with the CPU external-draft/tree-spec qwen35 failures, isolating those to the CPU speculative path, not the qwen35 forward pass. [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md), [gpu-drafter-mi200-investigation.md](../handoffs/archived/gpu-drafter-mi200-investigation.md)
- **The MI210's low roofline utilization is a quantized-dequant artifact, not general CDNA2 kernel immaturity.** llama.cpp gfx90a decode reaches ~33% (Q4_K) / ~47% (Q8_0) of the ~1.64 TB/s HBM roofline, but at **fp16 (no dequant) it reaches 62%** — so the residual gap is specifically the quantized MMQ dequant kernels. Flash-attn does not help decode here (`-fa 0` beats `-fa 1`; FA helps prefill only); default MMQ beats forced rocBLAS. [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md)
- **vLLM vs llama.cpp-HIP on gfx90a (matched Qwen3-8B fp16): vLLM +11% per-stream, +24% batched.** Per-stream decode llama.cpp-HIP 62.45 t/s vs vLLM ~69 t/s; 32-way batched 909.8 vs 1129 gen tok/s. vLLM's decisive edge is continuous-batching aggregate serving, not per-stream kernels. Quantized-vs-quantized was not measured; vLLM 0.10.1 predates the `gemma4`/`qwen35` archs so the head-to-head used Qwen3-8B. [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md)
- **Vulkan is definitively impossible on the MI210, complementing the GT 1030 falsification.** RADV enumerates zero devices for CDNA2 and no ICD (RADV/AMDVLK/amdgpu-pro) targets the compute-only Instinct MI200 family — use HIP/ROCm. Separately, the GT 1030 (~30 GB/s, less BW than one CPU NUMA node) is falsified for any drafter role — a GPU drafter only pays off when the device is BW-richer than the displaced CPU work, which the MI210 (1.6 TB/s ≈ 3.5× CPU aggregate) is and the GT 1030 is not. [gpu-drafter-mi200-investigation.md](../handoffs/archived/gpu-drafter-mi200-investigation.md)
- **Dense CPU MTP delivers a real ~1.84× (and 2.5–3.2× on structured/code output), confirming the dense-vs-MoE thesis.** gemma-4-31B dense CPU MTP gate-bench (quiesced host, draft_max=3 optimal): 9.14 → 16.79 t/s = 1.84× on prose; on checkable code/math tasks 26–32 t/s = 2.55×–3.19× because predictable tokens draft at very high acceptance. This corrects a prior single-run 2.98× and confirms dense is where CPU MTP wins, vs MoE's ≤1.06× (expert-verification overhead is the wall, not draft quality). **Output is distribution-lossless, NOT byte-exact greedy** (batched verification FP rounding flips greedy near-ties) — acceptable for chat/architect, do not rely on bit-determinism. [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md)
- **gemma-4-31B dense MTP is Pareto-dominated by the gemma-4-26B-A4B MoE worker — do NOT promote.** Equal ~90% quality but the A4B reads ~3.8B active params/token vs 31B dense, so on BW-bound CPU it is structurally faster (44.7 vs 26–32 t/s). Caveat: the ~90% tie is a saturated-suite resolution artifact (both near the 90–94% ceiling), not true capability parity — the dense 31B's real edge would show on a harder frontier tier, keeping a deliberate "fast architect" trade open. [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md)
- **Landing upstream Qwen MTP in our fork by cherry-pick is INFEASIBLE — a model-framework generation gap.** PR #22673 targets upstream's new `llama_model_<arch> : llama_model_base` classes (nested `graph`/`build_arch_graph`), while our fork still uses the older `llm_build_<arch> : llm_graph_context` builder pattern (~901 commits behind); the MTP graph cannot be lifted in. PR #22400 (GDN seq_rm dependency) was ported (`b139eba138`) but does not build standalone. Options are reimplement-in-fork or ride a fresh upstream-master build. [qwen-mtp-llamacpp-port.md](../handoffs/active/qwen-mtp-llamacpp-port.md), [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md)
- **A fresh upstream-master build runs dense Qwen3.5-9B MTP on CPU at ~2× — a proven standing-up path (but loses our kernels).** `--spec-type draft-mtp --spec-draft-n-max 3` on `Qwen3.5-9B-Q4_K_M`: baseline 14.90 → 29.30 t/s = 1.97×, 87% draft acceptance (184/211), correct output. The verified quantity is the ~2× *multiplier* and end-to-end path, not the absolute t/s (upstream-master kernels carry none of our NUMA/CPU optimizations). [qwen-mtp-llamacpp-port.md](../handoffs/active/qwen-mtp-llamacpp-port.md)
- **Per-model MTP verdicts (2026-06-22 refresh):** dense gemma-4-31B and dense Qwen3.5-9B = viable (gate-benched); Qwen3.6-35B-A3B MoE = worth-investigating but low EV (worst CPU-MTP case); Qwen3.5-122B-A10B GDN-hybrid architect = **the earlier "0.56× dead / GDN wall" is refuted — architect MTP is now confirmed live** on v6 NEXTN self-draft (same size-independent loader as the +103% frontdoor); Qwen3.5-27B/Qwen3-Next-80B hybrids remain the Delta-Net "hybrid trap" (net-negative). [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md), [v6-iqk-promotion.md](../handoffs/completed/v6-iqk-promotion.md)

### New Findings (2026-07-17) — Qwen3-VL-8B local image smoke on experimental v7

- **Qwen3-VL-8B's local image path is now validated on experimental v7 after a `llama-mtmd-cli` rebuild.** The initial `--version` segfault was resolved by rebuilding the experimental multimodal CLI, after which the CPU-shape smoke and MI210 OCR fixture both passed under `/mnt/raid0/llm/tmp/qwen3-vl8-image-smoke-20260717T115124Z/`. This closes the local image runtime/coherence check for the current model/decoder pair without touching production v6. Sources: [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md), [`progress 2026-07-17`](../progress/2026-07/2026-07-17.md).
- **The DeepSeek-V4-Flash CPU port is a provisional throughput FAIL and remains operator-gated.** V4-Flash is a 284B/13B-active MoE with a genuinely new arch (compressed-sparse + hierarchical-compressed attention, indexer, compressor, manifold-constrained Hyper-Connections). Cherry-pick into ik_llama was infeasible (mainstream `llm_graph_context` idiom vs ik's `llm_build_context` — a structural rewrite), so it runs as a separate auxiliary binary via the antirez mainstream fork. The Q4 GGUF (153.32 GiB) smoke-passed but measured **9.13 t/s eval-time decode vs an 18 t/s floor (~49% below)**; three independent measurements cluster 8–11 t/s. The floor itself is suspect (it ignored V4's per-token arch overhead), and the quality gate is externally blocked on Mac/ds4 reference logprobs. [deepseek-v4-flash-cpu-port.md](../handoffs/completed/deepseek-v4-flash-cpu-port.md)
- **The MI200 hardware gate opens a staged GPU spec-dec plan whose gating number (frontdoor drafter α) still has no valid evidence.** The single highest-leverage measurement — α of a validated frontdoor drafter against Qwen3.6 — gates cascade / custom-training / adaptive-K decisions via a 3-bin rule (≥0.7 / 0.55–0.7 / <0.55). The Qwen3-1.7B attempt is invalid (qwen2 vs qwen35 tokenizer mismatch, n_vocab 151936 vs 248320); Qwen3.5-0.8B is the correct qwen35-family candidate and metadata-alignment clears the special-token gate, but the CPU path still fails in qwen35/qwen35moe M-RoPE/GDN decode. llama.cpp `a6c793fc6` fixes the tree-spec `seq_id >= 1` capacity bug; a clean aligned retest that reaches draft/verify is the next gate. [gpu-drafter-mi200-investigation.md](../handoffs/archived/gpu-drafter-mi200-investigation.md)

### New Findings (2026-06-26) — NUMA-concurrent MTP throughput suite CORRECTED (`--no-mmap`, all 7 models)

> SUPERSEDES the earlier "Clean NUMA-concurrent MTP suite" figures. Those numbers were contaminated by **mmap
> page-cache sharing** (one shared node-pinned copy across the concurrent quarter instances → bandwidth-starved;
> full cells inherited the quarter loads' node-local placement). The "large-active/dense → 1×full" rule was the
> artifact and is RETRACTED. The corrected `--no-mmap` private-node-local results are below.

- **MTP speculative decode is the dominant throughput lever on the v6-iqk kernel, and with `--no-mmap` (a private node-local weight copy per instance) 4×quarter wins aggregate throughput for ~all models.** Corrected suite (quiesced host, `--no-mmap`, `drop_caches` between models; aggregate t/s across instances, MTP-on, q=4×quarter / f=1×full / h=2×half): gemma-26B small MoE — **4×quarter 109.6** / full 49.1 / half 83.3; gemma-31B dense — **4×quarter 30.1** / full 23.9 / half 17.5; Qwen3.6-27B dense — quarter 20.0 ≈ **half 20.2** / full 15.8 (tie); Qwen3.5-27B hybrid-SSM — **4×quarter 18.7** / full 14.4 / half 16.8; Qwen3.6-35B Q8 frontdoor MoE — **4×quarter 71.9** / full 42.3 / half 65.3; Qwen3-Next-80B SSM-MoE (no MTP path) — **4×quarter 49.2** / full 23.8 / half 39.8; Qwen3.5-122B architect MoE — **4×quarter 28.3** / full 18.0 / half 26.2. Topology rule (CORRECTED): **4×quarter wins aggregate throughput for every model** (6/7 outright; Qwen3.6-27B quarter≈half) — including the large/dense ones (gemma-31B 30.1 > full 23.9; 122B-A10B 28.3 > full 18.0); **1×full wins only single-stream LATENCY** (per-instance t/s = aggregate / n_inst); **2×half is never the best at any cell** (confirms the dual-half penalty). MTP helps every MTP-capable model and compounds hardest on dense/low-active at quarter (gemma-31B 4×quarter 7.2→30.1, +319%). **Production update 2026-06-27:** role-equivalent N12 A/Bs later refuted the private `--no-mmap` flip for `vision_escalation`, `frontdoor`, and `ingest_long_context`; keep the current shared-mmap production launch for those roles unless a materially different protocol is measured. Sources: [iqk-port.md](../handoffs/completed/iqk-port.md) (NUMA Phase-3B), [progress 2026-06-25](../progress/2026-06/2026-06-25.md), [progress 2026-06-27](../progress/2026-06/2026-06-27.md), [numa-private-weights-quarter-roles.md](../handoffs/completed/numa-private-weights-quarter-roles.md).
- **ARCHITECT MTP IS CONFIRMED LIVE end-to-end — the prior "no-MTP / GDN-wall" dismissal is refuted.** Qwen3.5-122B-A10B (architect) loads and drafts with NO spec-assertion crash, validated download → load → draft → measure. The earlier "0.56× dead-end / GDN wall" verdict was measured on an old fork with no `draft-mtp` (stale); the qwen35moe arch uses the same size-independent NEXTN loader as the +103% frontdoor and its MTP blocks are dense attention, not recurrent. Under the corrected `--no-mmap` suite its best aggregate operating point is **4×quarter+MTP 28.3 t/s** (> full 18.0, > half 26.2) — the same "quarter wins aggregate throughput" bucket as the rest of the stack (the earlier "large-active → 1×full" placement was the mmap contamination artifact). Sources: [iqk-port.md](../handoffs/completed/iqk-port.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md).
- **Root cause of the prior NUMA contamination: mmap page-cache sharing, NOT membind and NOT host noise alone.** A/B proof: gemma-26B 4×quarter **43.5 t/s (shared mmap) → 119.5 t/s (`--no-mmap` private node-local) = ~2.7×**; a dedicated-config A/B (both arms clean) read 64–73 t/s, so the launch params were fine — the bug was mmap-sharing + cross-cell cache contamination. The `numactl --membind` hypothesis (from an even earlier note) was already refuted (membind vs interleave 9.92 vs 10.05; settings A/B 11.73 vs 11.88) and is NOT reintroduced. The fix is `--no-mmap` (one private copy per instance) + `drop_caches` between models. Absolutes stay throttle-suspect at ~4-week uptime (+ ~12 h sustained bench → cross-model drift); only same-window per-model topology/MTP deltas are load-bearing. Sources: [iqk-port.md](../handoffs/completed/iqk-port.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md), [orchestrator_numa_finding](../handoffs/completed/numa-private-weights-quarter-roles.md).

### New Findings (2026-06-21) — Frontier CPU-runnable model candidates (storage- and fork-gated)

- **GLM-5.2 (754B GLM-MoE-DSA, MIT) is now the PRIMARY GLM target, superseding GLM-5.1, but is gated on the DSA forward pass.** intake-699 elevates GLM-5.2 over the GLM-5.1-REAP candidate in `glm51-reap-cpu-evaluation.md`. It is CPU-runnable via the unsloth UD dynamic-quant ladder: the storage-viable path is **UD-IQ2 (~238 GB)**, which fits under the ~633 GB raid0 free with headroom (UD-Q4_K_M=466 GB exceeds the ~250 GB working-set budget). Storage is NOT the blocker here — the blocker is that `LLM_ARCH_GLM_DSA` still dispatches to a **dense-MLA fallback** in our fork (gated on PR #21149, tracked in `llama-cpp-dsa-contribution.md`); without DSA the 1M-context value collapses to short-context dense fallback. New technique vs prior GLM intakes is IndexShare (arxiv:2603.12201), which reuses one sparse-attention indexer across every four sparse-attn layers (vendor-claimed 2.9x per-token FLOP cut at 1M ctx). Card benchmarks (AIME 2026 99.2, GPQA-Diamond 91.2, SWE-bench Pro 62.1) are vendor self-reported observations. [intake-699], [glm51-reap-cpu-evaluation.md], [llama-cpp-dsa-contribution.md] `vendor benchmarks=external; storage/fork facts=verified`
- **Nemotron-Nano quiet-host repeat confirmed the earlier ~83 t/s decode observation, but it remains throughput-only and stale-binary-caveated (2026-07-17).** The repeat at `/mnt/raid0/llm/tmp/model-admission-gpu-20260717-nemotron-nano/` measured prompt `448.9 t/s` and generation `83.3 t/s` under a 1536-token cap after Firefox/MegaSync removal. Output drifted into prompt-file/meta help text, so this is still admission-throughput evidence rather than a clean quality gate; the invoked experimental `build-hip` binary self-reported stale `9d70bae4b` while source HEAD was `2e79e10cc`. [model-admission-2026-07-16.md](../repos/epyc-inference-research/docs/reference/models/model-admission-2026-07-16.md)
- **Kimi-K2.7-Code (~1T-total / 32B-active MoE) is a frontier coder/agentic candidate but a storage near-blocker, and its vision path is unsupported in the fork.** intake-703: GGUF footprints are Q4_K_M 620.7 GB / Q3_K_M 489.2 GB / Q2_K 373 GB — all fit 1.1 TB RAM, but raid0 has only **~633 GB FREE**, so Q4_K_M is effectively non-viable without offloading cold models; Q3_K_M or lower is required (the "~480 GB headroom" figure in some notes is RAM, not disk). The model is now multimodal (400M MoonViT encoder + separate mmproj files) but **MoonViT is UNSUPPORTED in our fork** — only the text path is plausibly served, via deepseek2/MLA + the kimi-k2 tokenizer (384 experts, top-8 + 1 shared, 61 layers, MLA, 256K ctx). CPU decode t/s on a ~1T MoE is unmeasured and expected low. Moonshot's self-reported numbers (Kimi Code Bench v2 62.0, MCP Mark Verified 81.1) are observations with no protocol. Maps onto the deferred coder_escalation slot; update belongs on the existing Kimi-K2 deferral row in `large-moe-expert-parallelism-completed-through-2026-05-28.md`. [intake-703] `vendor benchmarks=external; storage/fork facts=verified`
- **A dense gemma-4-12B coder fine-tune (Q4_K_M ~7.38 GB) is a CPU-runnable specialist candidate, but a free no-inference loader kill-gate must clear first.** intake-702: community execution-verified-CoT coder SFT of dense `google/gemma-4-12B-it` (gemma4_unified arch, 256K ctx, Apache-2.0, distilled from Composer 2.5 + Fable 5 traces, test-gated). Caveat: a dense 12B reads ~12B params/token vs the ~3B active of the MoE incumbent worker_general (gemma4-26B-A4B) — on BW-bound CPU it is **likely slower per-token**, and it has no MTP drafter head. Critical kill-gate before any benchmark: confirm dense gemma-4-12B (gemma4_unified) actually **loads on the mainline production-consolidated-v5 build** — the deployed gemma4-26B-A4B MoE runs on a *separate* ik_llama.cpp gemma-mtp binary, so MoE-worker success does NOT prove dense-12B mainline support. v1 card omits coding benchmarks (only a v2 successor self-reports ~55% tau2-bench telecom). [intake-702] `vendor benchmarks=external; storage/fork facts=verified`

- **llama.cpp custom fork carries 23+ production-critical patches**: MoE expert override (#1), SWA slot reuse (#5-6), CPU paged attention (#7-10), server slot management (#14-15), prompt lookup (#19), tree speculation (#22), HSD+freeze-recurrent (#20), SSM checkpointing (#16), and Differential Transformer V2 architecture support (2026-04-14). The v2-to-v3 rebuild absorbed 517 upstream commits while preserving all patches. [llama-cpp-v3-upstream-rebuild.md, progress/2026-04-14 session 22]
- **Differential Transformer V2 implemented in llama.cpp** (2026-04-14): Full architecture support added across 9 files (155 LOC core graph builder in `src/models/diff-transformer.cpp`). Algorithm: Q doubled to 2h heads, K/V unchanged, single FlashAttention, split even/odd heads, `output = attn_even - sigmoid(W_lambda @ hidden) * attn_odd`. KV cache unaffected. Uses zero new ggml ops. Regression tests passed on all production models (Qwen3.5-35B hybrid SSM, Qwen3-Coder-30B MoE, Qwen2.5-Coder-32B dense). Synthetic test model loads and runs. Accuracy testing blocked on Microsoft releasing pretrained weights. Commits: `llama.cpp-experimental` `3b5514d46`, `llama.cpp` (production) `8bd57177f`. [progress/2026-04-14 session 22]
- **4 patches were dropped in the v3 rebuild**: MTP-1/MoE self-draft mega-commit (all techniques NOT VIABLE), Hadamard KV smoothing (superseded by upstream auto-enabling), enable_thinking Jinja fix (superseded by upstream refactor), and a merge commit. [llama-cpp-v3-upstream-rebuild.md]
- **Q4_K_M is the standard quantization**: Validated across coder (Q4KM 74% = f16 74%, 1.7x faster, 3.5x less RAM), hybrid models (recurrent state update is constant cost, Q8 costs 17-39% speed for marginal quality), and all production roles. The quality ceiling is the model itself, not the quantization. [numa-orchestrator-deployment.md]
- **Draft model selection is critical**: Qwen2.5-Coder-0.5B at 185 t/s generates 4x faster than Qwen3.5-0.8B at 44 t/s, despite similar parameter counts. The Qwen3.5 architecture (752M actual params) has higher per-token overhead. Best production pair: Qwen2.5-7B-f16 + Qwen2.5-Coder-0.5B (42 t/s, 91% acceptance). [specexec-verification-profile.md]
- **Speculation is architecture-dependent, not universally beneficial**: External draft on dense Qwen3-32B gives +55% (13.07 vs 8.44 t/s baseline). All speculation on hybrid SSM (Qwen3.5-*) is net-negative: external draft -33%, self-spec -44% to -52%, tree -53% to -66%, prompt lookup segfaults. Only MoE expert reduction works on hybrids. [hsd-hierarchical-self-speculation.md, self-speculation-benchmark.md]
- **Tree speculation is viable only for specific configurations**: Q4_K_M coder benefits from tree (ps=0.05, +2.7%), f16 targets benefit significantly (+15.8-17%), 480B MoE is harmed (-19%). Tree vs linear is a wash at 48t per instance. DySpec heap-based dynamic construction replaced simpler per-depth expansion. [tree-speculation-numa-drafting.md]
- **HSD capped branch resampling provides free marginal gain**: +0.8% throughput, +0.98pp acceptance rate. When target disagrees with draft, stochastically accepts based on p_draft if above 0.3 threshold. At most one recovery per sequence. [hsd-hierarchical-self-speculation.md]
- **Prompt lookup (--lookup) works on dense models and via freeze-recurrent on hybrid models**, but segfaults on Qwen3.5 hybrids after 1-3 prompts due to prompt cache + recurrent state corruption. Do not use on Qwen3.5 until fixed. [numa-orchestrator-deployment.md]
- **MoE self-drafting is NOT VIABLE**: Using the same model with reduced experts as draft. Raw speedup is promising (1.79x at 1-expert on 235B), but acceptance collapses: 2.9% at 1-expert (categorically different token distributions), 55% at 2-expert (but speedup too small to overcome draft overhead). No sweet spot exists. [ssm-hybrid-acceleration.md]
- **Self-speculation (layer skip) not viable without early-exit fine-tuning**: Dense models achieve 0.5-1.5% acceptance (intermediate logits untrained). Hybrid models suffer -44% to -52% from SSM checkpoint/restore overhead even with 77% acceptance. [hsd-hierarchical-self-speculation.md]
- **CPU paged attention enabled for models >= 39 GB**: Patches #7-10 in the custom fork. Dynamic block allocation with pool statistics. CLI flags exposed for orchestrator integration. RSS impact under NUMA 4-way not yet validated. [llama-cpp-v3-upstream-rebuild.md]
- **--draft-p-split 0 must be explicit for linear speculation**: The production binary defaults p_split=0.1 (tree ON). Silent tree activation causes kv_unified=true, n_seq_max=9, and draft truncation overhead. [numa-orchestrator-deployment.md]
- **Cherry-picked upstream commits fix Qwen3.6 think-loops and Gemma4 template issues (2026-04-20).** Four upstream commits were cleanly cherry-picked onto `production-consolidated-v3` with zero conflicts: `56666fa60` (skip reasoning budget sampler when no budget requested -- the Qwen3.6 fix), `ddf03c6d9` (fix ambiguous Gemma4 grammar rule), `d7ff074c8` (enable reasoning budget sampler for Gemma4), `3fc65063d` (better align to updated Gemma4 template). Validated: Qwen3.6 CLI test produced coherent thinking + correct answer, no `</think>` loops. The reasoning budget sampler was unconditionally activating and trapping models -- the skip commit was the root cause fix. Current HEAD: `cd5f4fcd0`, 35 custom commits ahead of merge base, 121 behind upstream (was 125). Full rebase deferred but no longer blocking. [llama-cpp-fork-rebase.md](../handoffs/completed/llama-cpp-fork-rebase.md)
- **Fork conflict risk is lower than initially assessed.** Actual code analysis found: `src/llama-kv-cache*` has ZERO conflict risk (10 of our patches, 0 upstream changes), `common/chat*` has ZERO risk (0 ours, 10 upstream all cherry-pickable), `tools/server/server.cpp` has ZERO risk (handoff was wrong). Real battleground is `common/common.h` (6 ours vs 4 upstream, including `libcommon->libllama-common` rename). Recommended: drop 7 experimental patches during full rebase to reduce conflict surface from 41 to 24 patches. [llama-cpp-fork-rebase.md](../handoffs/completed/llama-cpp-fork-rebase.md)
- **GLM-5.1-555B-A14B-REAP GGUF as potential stack addition.** 325GB Q4_K_M fits in 1052GB available RAM with 14B active parameters for an estimated ~25-40 tok/s on CPU. Stack simplification candidate: could replace architect_general (69GB) + architect_coding (139GB) = 208GB with a single 325GB model. Storage constraint: 417GB free on RAID, 92GB remaining after download. llama.cpp launch flags: `--reasoning on --reasoning-format deepseek --jinja`. DSA indexer tensors loaded but forward pass not implemented — dense MLA fallback. [intake-427, glm51-reap-cpu-evaluation.md]
- **Stock upstream produces 73.8% quality on Qwen3.6 vs 0% on our fork (pre-fix).** The reasoning budget sampler bug caused 100% degenerate `</think>` loops on all thinking-capable models. Post cherry-pick, CLI testing confirms the fix. Quality benchmarks should confirm the 0%->73.8% improvement at scale. M2.7 scored worse on upstream (41.1% vs 55.7%) because 4x token budget gave room for more training data leakage -- the model needs `max_tokens` tuning independently. [llama-cpp-fork-rebase.md](../handoffs/completed/llama-cpp-fork-rebase.md)

## Actionable for EPYC

- **Standard launch pattern**: `taskset -c <cpulist> llama-server -m <model>.gguf [-md <draft>.gguf --draft-max N --draft-p-split P] [--kv-unified] [--lookup] [-t <threads>] [-np <slots>] [--mlock] [--override-kv key=type:value]`
- **Never run experimental work on the production repo**: Use `/mnt/raid0/llm/llama.cpp-experimental` for all debug, benchmark, and feature development. The production binary at `/mnt/raid0/llm/llama.cpp/build/bin/llama-server` must remain stable.
- **Model registry drives configuration**: `model_registry.yaml` in both epyc-orchestrator and epyc-inference-research defines acceleration type, draft model, draft_max, p_split, thread count, NUMA config, and mlock for each role. orchestrator_stack.py reads this and applies spec_overrides per role.
- **All acceleration params must be sweep-verified**: bench_all_spec_sweeps.sh produces comprehensive measurements. Prior assumptions have been overturned multiple times (coder tree beneficial, 480B tree harmful, registry values 3.6x inflated).
- **v3 rebuild pending validations**: Paged attention RSS under NUMA 4-way, PPL sweep (done 2026-04-13). No blocking issues but measurement confirmation needed.
- **CPU+GPU hybrid inference** is a potential future direction (intake-310: expert offloading guide for MoE models in llama.cpp). No GPU hardware is currently present.

## Open Questions

- **Clean post-reboot v6 throughput bench + operator production-policy decision** remain the only open tail of the v6 cutover (pre-reboot numbers are throttle-caveated). [v6-iqk-promotion.md](../handoffs/completed/v6-iqk-promotion.md)
- **How much of the MI210's quantized roofline gap can gfx90a MMQ-dequant kernel tuning close?** fp16 hits 62% of roofline vs ~33% (Q4_K) / ~47% (Q8_0), so the headroom is real and specifically in the dequant path; whether an agentic ROCm kernel-authoring loop can recover it is untested. [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md)
- **Does the frontdoor drafter α ever clear a validated qwen35-compatible path?** No valid acceptance-rate evidence exists yet; the retest is gated on the `a6c793fc6` tree-spec fix + an aligned Qwen3.5-0.8B draft reaching draft/verify without qwen35 M-RoPE/GDN CPU failures. [gpu-drafter-mi200-investigation.md](../handoffs/archived/gpu-drafter-mi200-investigation.md)
- **DeepSeek-V4-Flash: recalibrate the throughput floor V4-arch-aware, and decide Strategy A (ik_llama translation, ~3–5d) go/park.** At 9.13 t/s it fails a gemma-derived 18 t/s floor, but that floor did not model V4's CSA/HCA/indexer/compressor overhead; a V4-aware floor may land ~8–12 t/s. The quality gate is externally blocked. [deepseek-v4-flash-cpu-port.md](../handoffs/completed/deepseek-v4-flash-cpu-port.md)
- **Qwen MTP in-fork: reimplement the MTP graph in our `llm_build_qwen35*` idiom, or catch the fork up ~901 commits to upstream's model framework?** Both are larger than a cherry-pick; neither is justified until a Qwen-MTP model becomes deployable (current candidates are Pareto-dominated or MoE-dead on CPU). [qwen-mtp-llamacpp-port.md](../handoffs/active/qwen-mtp-llamacpp-port.md)
- **A vLLM-on-gfx90a MI210 number is still un-measured** (prebuilt `rocm6.4.1_vllm_0.10.1` image = fast route; from-source current-vLLM @ ROCm 6.2 `gfx90a` = documented fallback; AITER/MORI/DeepEP exclude gfx90a so it is a reference-kernel Triton/CK build). [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md)
- The v3 upstream rebuild absorbed 517 commits. Subtle behavior changes in GGML backend dispatch, KV cache management, or sampler logic may emerge in production. PPL sweep completed 2026-04-13 but production stress testing under full orchestrator load is needed.
- CPU paged attention (patches #7-10) interaction with NUMA 4-way multi-instance is untested. Each instance's paged blocks should be NUMA-local but this is not verified.
- Prompt lookup segfault on Qwen3.5 hybrids (related to llama.cpp PR #13194) may be fixed in a future upstream commit. Monitor for fixes.
- TQ3 / TurboQuant quantization (intake-246) is on the monitor list but not yet merged. 3.5-bit Walsh-Hadamard Transform quantization could change the Q4_K_M optimality conclusion.
- REAP permanent pruning (deployed for architect_coding) creates a genuinely smaller model that may interact differently with speculation than dynamic expert override. Needs acceleration benchmarks on the REAP-246B model.

## Related Categories

- [Hardware Optimization](hardware-optimization.md) -- NUMA topology, memory bandwidth, and thread allocation determine inference performance
- [Inference Serving](inference-serving.md) -- the orchestrator stack built on top of llama-server instances
- [Speculative Decoding](speculative-decoding.md) -- detailed analysis of draft/target pairs and tree speculation
- [MoE Optimization](moe-optimization.md) -- expert reduction and REAP pruning for MoE models
- [Benchmark Methodology](benchmark-methodology.md) -- sweep methodology for validating inference configurations

## Source References

- [v6-iqk-promotion.md](../handoffs/completed/v6-iqk-promotion.md) -- The 2026-06-26 v6 single-kernel cutover: full ik_llama deprecation, GGML_IQK gating, per-role garbage-check log, architect NEXTN MTP going live, and the N=206 IQK-on/off eval-parity evidence (+38% t/s, no accuracy regression).
- [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md) -- First-touch MI210 GPU inference: HIP build recipe + fp8 guard fix, GPU decode/roofline table, gemma4 NEXTN-MTP 1.44×, qwen35 clean GPU decode, Vulkan-impossible verdict, and the vLLM-vs-llama.cpp fp16 head-to-head.
- [gpu-drafter-mi200-investigation.md](../handoffs/archived/gpu-drafter-mi200-investigation.md) -- GPU-as-latency-tier thesis, GT 1030 falsification, MI210 hardware-gate opening, cross-tokenizer spec-dec math, the frontdoor drafter α gating measurement + 3-bin decision rule, and the N5 blocker chronology.
- [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md) -- Per-model MTP verdict table, the gemma-4-31B dense gate-bench (1.84× / 2.5–3.2×, distribution-lossless), the Pareto-domination decision, and the saturated-suite resolution caveat.
- [qwen-mtp-llamacpp-port.md](../handoffs/active/qwen-mtp-llamacpp-port.md) -- Why #22673 cherry-pick is infeasible (model-framework generation gap), the verified fresh-upstream Qwen3.5-9B MTP path (~2×, 87% accept), and the in-fork reimplementation task/conflict map.
- [deepseek-v4-flash-cpu-port.md](../handoffs/completed/deepseek-v4-flash-cpu-port.md) -- DeepSeek-V4-Flash arch, merge gates, Strategy B auxiliary-binary execution, the provisional 9.13 t/s throughput FAIL, and the operator-gated D1/D2/D3 decisions.
- [intake-637](https://huggingface.co/antirez/deepseek-v4-gguf) antirez/deepseek-v4-gguf -- The V4-Flash Q2/Q4/MTP GGUFs (asymmetric routed-expert imatrix quant) that the CPU port evaluates.
- [intake-721](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF) / [intake-723](https://huggingface.co/unsloth/Qwen3.5-9B-MTP-GGUF) / [intake-724](https://huggingface.co/google/gemma-4-31B-it-assistant) -- Native NEXTN/MTP GGUF heads (Qwen3.6-35B MoE, dense Qwen3.5-9B, official dense gemma-4-31B drafter) grounding the MTP-refresh per-model verdicts.
- [intake-737](https://github.com/deepseek-ai/DeepSpec) DeepSpec / [intake-738](https://github.com/deepseek-ai/DeepSpec/blob/main/DSpark_paper.pdf) DSpark -- MIT draft-model training/eval framework (DSpark/DFlash/EAGLE-3) and the semi-AR adaptive-depth draft head; candidate MI210-side trained-drafter paths gated by the same α bins (GPU-only, no CPU/GGUF path today).
- [intake-740](https://github.com/ggml-org/llama.cpp/issues/25187) FR-Spec draft-vocab trim -- Lossless (temp-0) −85% draft-head kernel cut for native MTP; expected only +1–3% end-to-end on BW-bound decode, reinforcing that expert-verification (not draft quality) is the CPU MTP wall.
- [llama.cpp v3 Upstream Rebuild](/workspace/handoffs/completed/llama-cpp-v3-upstream-rebuild.md) -- Patch inventory (23 carry-forward, 4 dropped), conflict hotspot map, build configuration
- [NUMA Orchestrator Deployment](/workspace/handoffs/completed/numa-orchestrator-deployment.md) -- Per-model launch configuration, coder quant decision matrix, comprehensive sweep
- [Tree Speculation + NUMA Drafting](/workspace/handoffs/completed/tree-speculation-numa-drafting.md) -- Phase 1-8 implementation, DySpec, multi-path verification, NUMA 4-way results
- [HSD + Hierarchical Self-Speculation](/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md) -- HSD capped branch, layer-skip benchmarks, HiSpec, orchestrator integration
- [SSM Hybrid Acceleration](/workspace/handoffs/completed/ssm-hybrid-acceleration.md) -- MoE self-draft failure analysis, architecture properties, Q4_K_M optimality
- [SpecExec Verification Profile](/workspace/handoffs/completed/specexec-verification-profiling.md) -- Draft model cost profiling, critical ratios, large-K linear results
- [SpecExec Experiment](/mnt/raid0/llm/epyc-inference-research/docs/experiments/specexec-verification-profile.md) -- Raw data, NUMA impact, inflection points
- [Self-Speculation Benchmark](/mnt/raid0/llm/epyc-inference-research/docs/experiments/self-speculation-benchmark.md) -- SSM checkpoint overhead measurements
- [HiSpec External Draft Benchmark](/mnt/raid0/llm/epyc-inference-research/docs/experiments/hispec-external-draft-benchmark.md) -- Double-buffer optimization, freeze-recurrent validation
- [Chapter 01: Hardware System](/workspace/docs/infrastructure/01-hardware-system.md) -- Baseline performance, runtime optimizations
- [Progress 2026-03-21](/workspace/progress/2026-03/2026-03-21.md) -- Worker swap, registry corrections, sweep-verified params
- [Progress 2026-04-14 Session 22](/workspace/progress/2026-04/2026-04-14.md) -- Differential Transformer V2 implementation (9 files, 155 LOC core), zero new ggml ops, regression-safe on all production models, blocked on pretrained weights
- [llama-cpp-fork-rebase.md](/workspace/handoffs/completed/llama-cpp-fork-rebase.md) -- Cherry-pick results (4 commits, zero conflicts), Qwen3.6 think-loop fix confirmed, conflict risk reassessment (lower than estimated), experimental patch drop strategy, full rebase deferred but unblocked
- Intake entries: 5 results including CPU+GPU hybrid MoE inference guide (intake-310, high relevance), rocWMMA (intake-303), and community model evaluations
- [intake-427] GLM-5.1-555B-A14B-REAP GGUF -- 325GB Q4_K_M, 14B active, ~25-40 tok/s CPU estimate, stack simplification candidate
- [glm51-reap-cpu-evaluation.md] GLM-5.1 REAP CPU Evaluation -- deployment feasibility, storage constraints, llama.cpp flags
- [intake-699](https://huggingface.co/unsloth/GLM-5.2-GGUF) GLM-5.2 (754B GLM-MoE-DSA, MIT) -- now PRIMARY GLM target (supersedes GLM-5.1); unsloth UD-IQ2 ~238GB fits ~633GB raid0 free; IndexShare indexer-reuse (arxiv:2603.12201); gated on DSA forward pass (dense-MLA fallback today, PR #21149). vendor benchmarks=external; storage/fork facts=verified
- [intake-703](https://huggingface.co/mradermacher/Kimi-K2.7-Code-GGUF) Kimi-K2.7-Code (~1T-total/32B-active MoE) -- GGUF Q4_K_M 620.7GB / Q3_K_M 489.2GB / Q2_K 373GB; storage near-blocker (raid0 ~633GB free); MoonViT vision unsupported in fork (text path via deepseek2/MLA + kimi-k2 tokenizer); deferred coder_escalation candidate. vendor benchmarks=external; storage/fork facts=verified
- [intake-702](https://huggingface.co/yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF) gemma-4-12B coder fine-tune (dense, Q4_K_M ~7.38GB) -- CPU-runnable specialist candidate; dense 12B reads ~12B/token vs ~3B active MoE incumbent (likely slower); execution-verified-CoT SFT; needs a free loader kill-gate (gemma4_unified on mainline production-consolidated-v5 build) before benchmarking. vendor benchmarks=external; storage/fork facts=verified

## 2026-04-23 Additions — Single-instance peak throughput backlog

Three new handoffs (2026-04-23) open the forward-looking CPU throughput backlog for single-instance decode on EPYC 9655:

- **[Intra-Process Tensor-Parallel Decode](../handoffs/completed/intra-process-tensor-parallel-decode.md)** — shard each matmul column-wise across 12 CCDs with shared-L3 reduction (effectively free on CPU, unlike GPU where NVLink reduce dominates) and next-layer weight prefetch overlapping the barrier. Per-CCD hierarchical thread pool replaces GGML's global 192-thread barrier. Projected 2–5× single-instance decode, depending on NPS mode. Closes the gap between 1×instance throughput and the N×instance aggregate that NUMA 4-way deployment currently delivers only to concurrent sessions. No known CPU prior art — the design pattern is GPU-native (Megatron-LM column-sharded attention + row-sharded MLP) ported to CPU, where "communication" = shared memory traffic, not a separate fabric.

- **[Single-Instance System Tuning](../handoffs/completed/single-instance-system-tuning.md)** — exhaustive audit of system knobs that affect single-instance decode but have never been systematically measured on our hardware: NPS mode (NPS2 → NPS4 / L3-as-NUMA), THP (`madvise` → `always`), explicit 1 GB hugepages (currently 0 allocated), IRQ affinity, per-CCD sync primitive (replaces GGML global barrier), SMT toggle for AVX-512-heavy workloads, per-NUMA weight replication. Projected 15–40% alone; required for TP-sharding's full gain under NPS4/L3aaN. Phases staged so reboot windows are batched.

- **[CPU Inference Optimization Index](../handoffs/archived/cpu-inference-optimization-index-history-through-2026-06-19.md)** — backlog index aggregating all 14 unimplemented CPU throughput techniques (CPU1–CPU14): TP sharding, GEMV ukernels, system tuning, per-CCD sync, hugepages, ZenDNN 5.2 eval, tinyBLAS integration, weight replication, dense-weight sparsity, sub-Q4 quant eval, compiler/PGO/LTO, BOLT post-link, prefill optimizations, `--parallel` slot decode benchmarks. Includes dependency graph (CPU3 Phase 0 baseline gates everything), composition matrix (TP × ukernel × tuning multiplicative up to 460 GB/s BW ceiling), and explicit list of what's deployed or concluded-not-viable so future agents don't re-open closed work.

Start gate for the entire backlog: **CPU3 Phase 0 baseline measurement** — `perf stat` uncore counters + barrier-time profiling on Qwen3-Coder-30B-A3B Q4_K_M at 192t. Tells us which lever has the most headroom before committing to any code.

## 2026-04-23 late-session — Phase 0 executed, CPU2 falsified

Phase 0 ran end-to-end on 2026-04-23 in `llama.cpp-experimental` on `cpu-optimization/backlog-2026-04-23` (HEAD `9e048fbc1`). Key measurements and decisions:

- **Thread sweep** on Qwen3-Coder-30B-A3B Q4_K_M (`-p 0 -n 64 -r 3`, quiet host): 24t=40.8 t/s, 48t=39.6, **96t whole-machine (`taskset -c 0-95`, all physical cores) = 49.1 (PEAK)**, 144t cross-NUMA=25.7 bimodal, 192t `--numa distribute`=18.7 bimodal.
- **perf profile Qwen3.6-27B Q8_0 @ 96t (4.41 t/s)**: 63.43% `ggml_vec_dot_q8_0_q8_0`, 32.34% libomp spin/barrier, 0.11% DeltaNet (`gated_delta_net` + `ssm_conv` combined — refutes the feared DeltaNet-dominates gate).
- **CPU2 Phase 1 Target #1 implemented and tested**: ported `ggml_vec_dot_q8_0_q8_0` from AVX2 (256-bit) to AVX-512VNNI (512-bit) using existing `mul_sum_i8_pairs_acc_int32x16` helper. Disassembly confirmed `vpdpbusd %zmm` in new path. Measured +1.7% at 96t / −3.6% at 1t — projection of 1.46× falsified. Cause: perf cycles inside the dot loop are DRAM-wait, not ALU. Change reverted.
- **Promotions based on measurement**:
  - CPU1 (TP-sharding) Phase 0 gate PASSED (192t at 8% of 460 GB/s roofline; barrier >15% required, measured 32–45%). Phase 1 prototype remains ~1 week of work.
  - CPU4 (per-CCD sync primitive) promoted from MED-bundled to HIGH standalone on measured 32–45% barrier cost.
  - CPU2 (GEMV ukernels on quantized decode) deprioritized.
- **CPU3 zero-reboot knobs applied via user sudo**: THP→always, numa_balancing=0, 1GB hugepage on node 1. Net within noise on canonical workload.
- **96t whole-machine operating point** emerged as actionable: +26% vs production worker_general (1×24t, 39.1 t/s) with no code change. Worth a production sweep separately from CPU1. *(Label corrected 2026-07-30: originally "96t-single-NUMA-node". The config is `taskset -c 0-95` = all 96 physical cores across all four NPS4 nodes, not one node; canonical placement adds `numactl --interleave=all`. Same misnomer as `stack_numa.py`'s `NUMA_NODE0`/`NUMA_NODE1`, which each span two nodes.)*

See `research/deep-dives/cpu-optimization-phase0-baseline.md` for full analysis + revised gate decisions. Auto-memory entry `feedback_cpu_decode_bw_bound.md` captures the lesson: when perf shows high overhead inside a quantized-decode inner dot loop on this hardware, those samples are typically DRAM-wait cycles; a cheap wider-SIMD A/B test resolves the question in hours before committing to shape-specialized ukernel work.

## 2026-05-06: Production stack consolidation merged

The May 4-6 consolidation arc closed with `epyc-orchestrator` main merge commit `a268040` (9 stack-swap commits). Single GGUF mmap now serves three roles (frontdoor + coder_escalation + worker_summarize) — kernel page cache holds one physical copy of Qwen3.6-35B-A3B Q8 (~37 GB) instead of three. Same pattern for worker_general / worker_math / toolrunner (Qwen3-Coder-30B-A3B Q4 ~16 GB shared).

Hot-tier resident model footprint is ~167 GB (well under 1.13 TB host); ~600 GB free for KV caches + OS. Net warm-tier savings vs pre-2026-05-04: ~157 GB.

### Pipelines using the stack (final)

- **Three_stage_summarization** (≥5000 tokens, lower for multi-doc): Stage 1 = ingest_long_context (Qwen3-Next-80B-A3B Q4 SSM-hybrid for full-context fast draft) → Stage 2 = frontdoor (Qwen3.6-35B-A3B Q8 for quality review on ~15% reduced context).
- **Coder escalation chain**: frontdoor → coder_escalation (same model on separate slot for crash isolation) → FAIL. Shortened from 3 to 2 levels by architect_coding removal.
- **Architect (synthesis/IR)**: routes to architect_general (Qwen3.5-122B-A10B Q4 + Qwen3.5-0.8B Q8 spec draft, 1×96t canonical wiring per Probe B).

### Launcher single-source-of-truth refactor

`scripts/server/orchestrator_stack.py` HOT_SERVERS + WARM_SERVERS now COMPUTED from `ROLE_LAUNCH_META` (tier + mode + aliases) + `NUMA_CONFIG` (wiring spec). Module-load validation rejects misconfiguration; start-time validation cross-checks against registry's `process_layout`. Adding/removing roles is now safer (catches dangling refs before launch).

Source: [progress/2026-05/2026-05-06.md](../progress/2026-05/2026-05-06.md), [handoffs/active/qwen36-production-upgrade.md](../handoffs/completed/qwen36-production-upgrade.md).


## Detecting MTP/NEXTN tensors in a GGUF (2026-07-25)

**Do not infer MTP presence from file size.** Counterexample from real artifacts:
`ThinkingCap-Qwen3.6-27B` Q4_K_M is **722 MB smaller** than our non-MTP
`Qwen_Qwen3.6-27B-Q4_K_M.gguf` and demonstrably **has** MTP tensors. Size deltas only hold within a
single quantizer's recipe.

**Reliable fingerprint** (Qwen3.6-27B family), readable in a **24-byte ranged HTTP read** of the
GGUF header — no download:

| Tensor count | Meaning |
|---|---|
| 851 | no MTP |
| 866 | MTP present (+15 = the `blk.64.nextn.*` block) |

Corroborate with KV key `qwen35.nextn_predict_layers`.

**Related trap — confounded A/B pairs.** Two locally-held artifacts can both be valid yet not be a
controlled pair: `Qwen3.6-27B-MTP-Q4_K_M.gguf` (17,106,773,120 B, 866 tensors) is *smaller* than
`Qwen_Qwen3.6-27B-Q4_K_M.gguf` (17,533,552,192 B, 851 tensors) — 15 extra tensors yet smaller, so
they were built with different recipes. Any MTP-vs-non-MTP benchmark across those two is
confounded. The Q8_0 pair is clean.

**Provenance technique**: to test whether a finetune retrained or inherited a draft head, compare
the actual tensor bytes, not sizes. A byte-identical `blk.64.*` region (single sha256) plus a
genuinely-differing control tensor proves both inheritance and that the offset arithmetic is sound.
Applied to ThinkingCap, this showed a **stock MTP head on a LoRA-modified trunk** — a co-trained-head
vs modified-trunk mismatch, with the differing set matching the adapter's 256 target modules exactly.

_Sources: `handoffs/active/speculative-decoding-mtp-refresh.md` § 2026-07-25;
`handoffs/active/intake-derived-work-2026-07-25.md` ID-15/ID-16._

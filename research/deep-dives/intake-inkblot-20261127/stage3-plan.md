# Proposed Inkblot comparison in the Inkling 2 Mini study

**Decision for the operator.** Approve adding three boxes to the existing EVL-02 study. They cover artifact verification, a native-depth CPU comparison and a concurrency check after the existing HIP port. No GPU, CPU inference or training run was booked during intake.

## Evidence and scope

Three of four authorized sweeps covered eight sources. Three gpt-6.2-sol researchers at medium effort inspected the sources and exchanged second reads. The 24 retained quotes were checked separately from their interpretation. The publisher’s best native-depth signal is 44/64 versus 32/64. On the same slice a fourth pass yields 45/64. The release lacks the paired outcomes needed to compute uncertainty for the historical comparison. The repair PR supplies software and metadata checks, while the weight reports give incompatible audit counts without a shared artifact identity. See [the intake summary](README.md).

**Current owner.** The active model-evaluation-queue track at root 396582da9 owns INK2-PORT-1, MEAS-1, PORT-2a, placement and quantization. The experimental kernel at 3d01b5e50 contains the SITU prerequisites and lacks an Inkling model graph in its file tree. The base handoff records the v11 promotion boundary. The orchestrator’s paired_stats.py at 59a1d4695 already checks profile agreement and computes paired discordances. Its intersection-based statistics require an explicit, checked 64-ID denominator in the input. Reuse these, the existing role fixtures and linkage/residency probes. The intake index already feeds Vidya. No new producer or grading ladder is proposed here. The scan covered the named sources and owners; no local paired outcome or qualified derivative GGUF was found.

## Filing scope

| Packet | Operational outcome |
|---|---|
| P1 | Bind the compared artifacts |
| P2 | Decide whether the edited checkpoint merits a role trial |
| P3 | Protect the HIP port acceptance comparison |
| M1 | Evaluate the marginal value of a fourth pass |
| M2 | Decide whether the training intervention merits reproduction |
| K1 | Preserve source attribution across model studies |

## Exact handoff changes

Use the existing model-evaluation-queue track under EVL-02. Add these boxes at the end of its Backlog using the standard box renderer. The owning research-evaluation index already routes all candidate trials here. Its current higher-priority next action stands. No new stub or second index row is proposed.

```text
- [ ] **INK2-INKBLOT-ART** [non-inference] Build a matched IQ4_NL artifact pair from the pinned Base and Inkblot releases and produce a per-tensor change and conversion manifest for the CPU comparison.
      · done when: Both input shard hashes, all 1,244 named tensors, comparison classifications, quantizer and converter revisions, output hashes, tokenizer and template identities are recorded. Unexpected expert or vision changes and any conversion drift have explicit dispositions.
      · gate: none        · inputs: `research/deep-dives/intake-inkblot-20261127/intake-3026.md`

- [ ] **INK2-INKBLOT-PAIR** [inference] Compare reloaded Inkling Base and Inkblot at three passes on the same CPU quarter using the frozen 64-item held-out manifest, complete paired outcomes and matched decode timing.
      · done when: A result exists for every expected ID and arm, including failures, with source and build digests, per-item outputs, matched profile, paired counts and the predeclared decision.
      · gate: INK2-INKBLOT-ART, INK2-MEAS-1        · inputs: `research/deep-dives/intake-inkblot-20261127/intake-3026.md` `research/deep-dives/intake-inkblot-20261127/intake-3027.md`

- [ ] **INK2-INKBLOT-SLOTS** [inference] Validate the MI210 indexed-bias port on matched native Base prompts with one and two active requests on the same two-slot server before interpreting Inkblot outputs.
      · done when: The same 12 frozen tool IDs have raw outputs, slot and stop records under both occupancy settings, plus recorded backend residency and a repeat or parity verdict for every ID.
      · gate: INK2-PORT-2a        · inputs: `research/deep-dives/intake-inkblot-20261127/intake-3029.md` `research/deep-dives/intake-inkblot-20261127/intake-3030.md`

```

**Artifact brief.** Where: epyc-root:handoffs/active/model-evaluation-queue.md and the existing experimental Inkling converter/quantizer. Verify both source LFS identities and pairwise per-tensor hashes, including expert and vision tensors, and bind any type/quantization exceptions. Use the same converter revision, importance matrix or no matrix, quantizer settings, and template on both arms. Bind the final GGUF digests and a structural CPU reload check. Keep MTP off. Acceptance is the first box’s done-when.

**CPU brief.** Where: epyc-orchestrator:scripts/autopilot/paired_stats.py and epyc-root:handoffs/active/model-evaluation-queue.md. Acceptance is the second box’s done-when and the protocol below. Save the item manifest, raw outputs, result and effective configuration with the study, including hardware and binary/library identity.

**HIP brief.** Where: the experimental indexed-bias path from INK2-PORT-2a and its EPYC linkage probe. Acceptance: the third box’s done-when. MI210 acceptance addendum. Use the merged indexed-bias implementation at 2a335259 as a reference for the existing slot re-home. With the pinned Base artifact, FA on, f16 KV and two configured slots, replay identical frozen tool prompts with one busy slot and then two. Keep context, template, token cap, seed and request-to-slot mapping recorded. Preserve every output and stop cause. If repetition or numerical parity diverges reproducibly on Base, isolate that first. Add q8_0 KV as a separate comparison only when that path qualifies.

Use the same fixed 12 tool/format smoke IDs on both occupancy settings. Archive all requests, results, slot IDs and failures. Stop on reproducible same-ID Base divergence; repeat that ID twice before diagnosing. A clean screen permits the existing port acceptance to continue. After CPU qualification, any GPU derivative comparison requires equal Base and Inkblot quant/settings and the same held-out IDs.

## CPU evaluation protocol

Use a disjoint 12-case plumbing set followed by 64 held-out IDs drawn before model output: 24 exact-answer math, 20 coding tasks graded with frozen tests, 20 worker/tool tasks scored against fixed expected actions. Freeze item IDs/hashes, gold/tests, grader versions, budgets, raw prompt bytes, strata and order. Seal the 64 during smoke. Screen the saved, reloaded matched IQ4_NL files on the same CPU quarter, binary, template, reasoning setting, context, seed and greedy token cap (2,048), speculation off. Interleave arms with balanced order. Save output/token IDs, timings, stop cause, grader outcome, repeats, truncations, invalids, abstentions, crashes, timeouts and missing attempts per arm. Count absent/invalid answers as failures in the fixed denominator. Flag infrastructure failures separately. Record paired discordances and exact two-sided McNemar on all 64. Use the existing Base-vs-served Qwen reference from INK2-MEAS-1 as role context. Record median tg128 at d=0 and d=8192 from three interleaved timing pairs per depth, separately from accuracy. On smoke, stop for failed parity or reproducible pathological repeats. At 64, advance to a later role evaluation only for at least 8 net wins, exact p<0.05, no critical fixture regression, no excess pathological repetitions and median candidate throughput at least 95% of Base at each depth. Otherwise stop. With 64 items a single net win is 1.56 points; exact uncertainty depends on discordance. This screen targets a large effect and makes a small or unclear change inconclusive.

## Triggers and consumers

Only if the native three-pass screen passes and the fixed-checkpoint forced-depth implementation has independent three-pass logit/cache parity, compare Base and Inkblot at both 3 and 4 passes. Hold items, conversion, prompt, generation budget and grader fixed. Report depth-specific repeat/completion rates and wall time per correct result on CPU and on qualified MI210. No production depth switch follows from the author table.

Only reopen training attribution if the checkpoint passes the held-out screen and the historical owner supplies hash-bound parents, realized merge weights, calibration/train/gate splits and historical per-item records, or a separately approved new experiment has a specific model-development decision. Compare FP-Solve alone, a simple selection baseline, GSPO without the deeper-mode bonus and the complete policy under matched generation and validation budgets. Freeze an untouched test set, rescore the exported checkpoint and separate the new run from the historical claim.

EVL-02 owns the three proposed boxes. INK2-MEAS-1 supplies the qualified CPU base, the worker/frontdoor evaluation supplies the target tasks, and INK2-PORT-2a owns GPU correctness. The placement and quantization tasks can consume the artifact inventory without a new dependency. Serving and routing remain prospective consumers of a separate role evaluation. No production activation is part of this proposal.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| RI-ART | intake-3026#record and intake-3027#record | Bind both source and converted checkpoints, prove the scope of changes and preserve reload identities before the quality comparison. | P1 / INK2-INKBLOT-ART |
| RI-PAIR | intake-3026#01 and intake-3026#03 | Compare the saved models at native three-pass depth with paired held-out correctness, cost and complete failure counts. | P2 / INK2-INKBLOT-PAIR |
| RI-HIP | intake-3030#00 and intake-3029#00 | Exercise the qualified HIP path with identical Base items under one and two active requests and isolate any repeated-output failure. | P3 / INK2-INKBLOT-SLOTS |
| RI-DEPTH | intake-3028#00 and intake-3031#01 | Gate a four-pass study on a successful three-pass screen and independently validated runtime parity. | M1 |
| RI-TRAIN | intake-3025#03, intake-3027#03 and intake-3032#record | Gate a training attribution experiment on recoverable lineage and include a simple matched-budget control. | M2 |
| RI-PROVENANCE | intake-3028#record and intake-3026#record | Distinguish author-shared figures, inherited benchmark YAML and distinct task suites from independent evidence. | K1 |

## Stage-3 filing payload

```json
{
  "format_version": 2,
  "entry_updates": [
    {
      "id": "intake-3025",
      "integration_disposition": "monitor",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "Only reopen training attribution if the checkpoint passes the held-out screen and the historical owner supplies hash-bound parents, realized merge weights, calibration/train/gate splits and historical per-item records, or a separately approved new experiment has a specific model-development decision. Compare FP-Solve alone, a simple selection baseline, GSPO without the deeper-mode bonus and the complete policy under matched generation and validation budgets. Freeze an untouched test set, rescore the exported checkpoint and separate the new run from the historical claim."
      ]
    },
    {
      "id": "intake-3026",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/model-evaluation-queue.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Owned same-depth CPU checkpoint comparison."
      ]
    },
    {
      "id": "intake-3027",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/model-evaluation-queue.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Use saved-artifact validation and frozen pairing in the CPU study."
      ]
    },
    {
      "id": "intake-3028",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/model-evaluation-queue.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Separate actual task success, matched depth and diagnostic indicators in the CPU protocol."
      ]
    },
    {
      "id": "intake-3029",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/model-evaluation-queue.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Use the merge as a reference within the existing HIP acceptance."
      ]
    },
    {
      "id": "intake-3030",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/model-evaluation-queue.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Add matched busy-slot acceptance to the existing HIP task."
      ]
    },
    {
      "id": "intake-3031",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "Independent variable-depth training is context for the fixed-model baseline."
      ]
    },
    {
      "id": "intake-3032",
      "integration_disposition": "monitor",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "Only reopen training attribution if the checkpoint passes the held-out screen and the historical owner supplies hash-bound parents, realized merge weights, calibration/train/gate splits and historical per-item records, or a separately approved new experiment has a specific model-development decision. Compare FP-Solve alone, a simple selection baseline, GSPO without the deeper-mode bonus and the complete policy under matched generation and validation budgets. Freeze an untouched test set, rescore the exported checkpoint and separate the new run from the historical claim."
      ]
    }
  ],
  "opportunity_reviews": {
    "P1": {
      "project_objective": "Bind the compared artifacts",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "gap": "Published report and LFS identities leave the individual changes and GGUF conversion unverified.",
      "operational_change": "Build a matched IQ4_NL artifact pair from the pinned Base and Inkblot releases and produce a per-tensor change and conversion manifest for the CPU comparison.",
      "benefit_direction": "Higher confidence that any later difference belongs to the chosen checkpoints.",
      "owner": "handoffs/active/model-evaluation-queue.md",
      "execution_conditions": "Start with static per-tensor inspection on approval. Use one pinned converter and quantizer for both artifacts and schedule the reload through the existing experimental port. Respect the v11 boundary on kernel builds.",
      "closure_basis": "Both input shard hashes, all 1,244 named tensors, comparison classifications, quantizer and converter revisions, output hashes, tokenizer and template identities are recorded. Unexpected expert or vision changes and any conversion drift have explicit dispositions."
    },
    "P2": {
      "project_objective": "Decide whether the edited checkpoint merits a role trial",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "gap": "Existing CPU task compares Base to served Qwen. It contains no same-depth derivative arm.",
      "operational_change": "Compare reloaded Inkling Base and Inkblot at three passes on the same CPU quarter using the frozen 64-item held-out manifest, complete paired outcomes and matched decode timing.",
      "benefit_direction": "Resolve a practically large quality gain at measured decode cost.",
      "owner": "handoffs/active/model-evaluation-queue.md",
      "execution_conditions": "After a usable converted pair and clean native Base acceptance; book the same CPU quarter under the INK2 owner.",
      "closure_basis": "A result exists for every expected ID and arm, including failures, with source and build digests, per-item outputs, matched profile, paired counts and the predeclared decision."
    },
    "P3": {
      "project_objective": "Protect the HIP port acceptance comparison",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "gap": "Existing HIP port checks FA residency and CPU tolerance. Its current text has no concurrency control.",
      "operational_change": "MI210 acceptance addendum. Use the merged indexed-bias implementation at 2a335259 as a reference for the existing slot re-home. With the pinned Base artifact, FA on, f16 KV and two configured slots, replay identical frozen tool prompts with one busy slot and then two. Keep context, template, token cap, seed and request-to-slot mapping recorded. Preserve every output and stop cause. If repetition or numerical parity diverges reproducibly on Base, isolate that first. Add q8_0 KV as a separate comparison only when that path qualifies.",
      "benefit_direction": "Reduce false model failures caused by backend or concurrency differences.",
      "owner": "handoffs/active/model-evaluation-queue.md",
      "execution_conditions": "The new concurrency check depends on acceptance of the existing HIP port. Run after its post-v11 GO gate on a single MI210 with confirmed resident build and VRAM during decode.",
      "closure_basis": "Retain identical input IDs, runtime parity, one-busy and two-busy raw outputs and complete failure counts."
    },
    "M1": {
      "project_objective": "Evaluate the marginal value of a fourth pass",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "gap": "One extra correct on the publisher slice does not price or establish a fourth-pass benefit.",
      "operational_change": "Only if the native three-pass screen passes and the fixed-checkpoint forced-depth implementation has independent three-pass logit/cache parity, compare Base and Inkblot at both 3 and 4 passes. Hold items, conversion, prompt, generation budget and grader fixed. Report depth-specific repeat/completion rates and wall time per correct result on CPU and on qualified MI210. No production depth switch follows from the author table.",
      "benefit_direction": "Measure quality per unit time over both hardware paths.",
      "owner": "handoffs/active/model-evaluation-queue.md",
      "execution_conditions": "Dormant until the two named conditions hold.",
      "closure_basis": "An approved subsequent factorial experiment would answer the marginal-depth question."
    },
    "M2": {
      "project_objective": "Decide whether the training intervention merits reproduction",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "gap": "Original released gate, inputs and checkpoint export do not establish realized lineage.",
      "operational_change": "Only reopen training attribution if the checkpoint passes the held-out screen and the historical owner supplies hash-bound parents, realized merge weights, calibration/train/gate splits and historical per-item records, or a separately approved new experiment has a specific model-development decision. Compare FP-Solve alone, a simple selection baseline, GSPO without the deeper-mode bonus and the complete policy under matched generation and validation budgets. Freeze an untouched test set, rescore the exported checkpoint and separate the new run from the historical claim.",
      "benefit_direction": "Isolate which edit provides value before assigning training compute.",
      "owner": "handoffs/active/model-evaluation-queue.md",
      "execution_conditions": "Dormant pending the quality/lineage conditions or a distinct approved new-study decision.",
      "closure_basis": "No training reproduction is needed to compare downloadable checkpoints."
    },
    "K1": {
      "project_objective": "Preserve source attribution across model studies",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "gap": "Inherited YAML, shared paper and card tables, and tool-use proxies can be mistaken for new outcomes.",
      "operational_change": "Keep source and scope in the dive notes; grade each future task against its own expected answer.",
      "benefit_direction": "Prevent a copied result or command count from being counted as independent success.",
      "owner": "handoffs/active/model-evaluation-queue.md",
      "execution_conditions": "Available for interpretation at every future study stage.",
      "closure_basis": "The retained study notes distinguish source, model, loop depth, exact count and benchmark."
    }
  },
  "actionable_additions": [],
  "steering_reconciliation": [
    {
      "seq": 1,
      "stage": 1,
      "verbatim": "Perform a research intake on these two sources: https://github.com/eelbaz/Recursive-Self-Improving-Loopers https://huggingface.co/Ex0bit/Inkblot-2-mini. Approve all recommended deepdives for up to four stage 2 sweeps. These sources are pertinent to Inkling 2 Mini which we plan to study in the near future and for which a handoff should already exist",
      "disposition": "planned",
      "plan_ref": "P2",
      "reason": "The selected sweeps are complete. The proposed native-depth study is owned by the existing Inkling evaluation handoff."
    }
  ],
  "opportunity_scan": [
    {
      "scan_id": "scan-1",
      "source_ref": "intake-3026#record and intake-3027#record",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "mechanism": "Shards share a tensor map while the audit aggregates disagree.",
      "consumer": "EVL-02 / Bind the compared artifacts",
      "application": "Build a matched IQ4_NL artifact pair from the pinned Base and Inkblot releases and produce a per-tensor change and conversion manifest for the CPU comparison.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-ART"
      ],
      "basis": "Published report and LFS identities leave the individual changes and GGUF conversion unverified."
    },
    {
      "scan_id": "scan-2",
      "source_ref": "intake-3026#01 and intake-3026#03",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "mechanism": "Native three-pass model pair on a small author-reported math slice.",
      "consumer": "EVL-02 / Decide whether the edited checkpoint merits a role trial",
      "application": "Compare reloaded Inkling Base and Inkblot at three passes on the same CPU quarter using the frozen 64-item held-out manifest, complete paired outcomes and matched decode timing.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-PAIR"
      ],
      "basis": "Existing CPU task compares Base to served Qwen. It contains no same-depth derivative arm."
    },
    {
      "scan_id": "scan-3",
      "source_ref": "intake-3030#00 and intake-3029#00",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "mechanism": "Upstream indexed bias support and repetition under two active requests.",
      "consumer": "EVL-02 / Protect the HIP port acceptance comparison",
      "application": "MI210 acceptance addendum. Use the merged indexed-bias implementation at 2a335259 as a reference for the existing slot re-home. With the pinned Base artifact, FA on, f16 KV and two configured slots, replay identical frozen tool prompts with one busy slot and then two. Keep context, template, token cap, seed and request-to-slot mapping recorded. Preserve every output and stop cause. If repetition or numerical parity diverges reproducibly on Base, isolate that first. Add q8_0 KV as a separate comparison only when that path qualifies.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-HIP"
      ],
      "basis": "Existing HIP port checks FA residency and CPU tolerance. Its current text has no concurrency control."
    },
    {
      "scan_id": "scan-4",
      "source_ref": "intake-3028#00 and intake-3031#01",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "mechanism": "Fixed-depth edit and distinct variable-depth training.",
      "consumer": "EVL-02 / Evaluate the marginal value of a fourth pass",
      "application": "Only if the native three-pass screen passes and the fixed-checkpoint forced-depth implementation has independent three-pass logit/cache parity, compare Base and Inkblot at both 3 and 4 passes. Hold items, conversion, prompt, generation budget and grader fixed. Report depth-specific repeat/completion rates and wall time per correct result on CPU and on qualified MI210. No production depth switch follows from the author table.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-DEPTH"
      ],
      "basis": "One extra correct on the publisher slice does not price or establish a fourth-pass benefit."
    },
    {
      "scan_id": "scan-5",
      "source_ref": "intake-3025#03, intake-3027#03 and intake-3032#record",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "mechanism": "Regularized edit and gated training, with a recorded regressing acceptance.",
      "consumer": "EVL-02 / Decide whether the training intervention merits reproduction",
      "application": "Only reopen training attribution if the checkpoint passes the held-out screen and the historical owner supplies hash-bound parents, realized merge weights, calibration/train/gate splits and historical per-item records, or a separately approved new experiment has a specific model-development decision. Compare FP-Solve alone, a simple selection baseline, GSPO without the deeper-mode bonus and the complete policy under matched generation and validation budgets. Freeze an untouched test set, rescore the exported checkpoint and separate the new run from the historical claim.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-TRAIN"
      ],
      "basis": "Original released gate, inputs and checkpoint export do not establish realized lineage."
    },
    {
      "scan_id": "scan-6",
      "source_ref": "intake-3028#record and intake-3026#record",
      "implementation_ref": "epyc-root 396582da9, model-evaluation-queue.md L725–784 (INK2-PORT-1, INK2-MEAS-1, INK2-PORT-2a, INK2-MI210-PLACE-1, INK2-MEAS-2); experimental llama.cpp 3d01b5e50; orchestrator 59a1d4695, scripts/autopilot/paired_stats.py::require_matched_comparison and mcnemar_from_vectors.",
      "mechanism": "Same-publisher tables, copied metadata, and separate terminal benchmark suites.",
      "consumer": "EVL-02 / Preserve source attribution across model studies",
      "application": "Keep source and scope in the dive notes; grade each future task against its own expected answer.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-PROVENANCE"
      ],
      "basis": "Inherited YAML, shared paper and card tables, and tool-use proxies can be mistaken for new outcomes."
    }
  ],
  "outcome_reviews": {
    "RI-ART": {
      "required_outcome": "Bind both source and converted checkpoints, prove the scope of changes and preserve reload identities before the quality comparison.",
      "review_status": "preserved",
      "review_basis": "Published report and LFS identities leave the individual changes and GGUF conversion unverified. Both input shard hashes, all 1,244 named tensors, comparison classifications, quantizer and converter revisions, output hashes, tokenizer and template identities are recorded. Unexpected expert or vision changes and any conversion drift have explicit dispositions.",
      "task_refs": [
        {
          "owner": "handoffs/active/model-evaluation-queue.md",
          "task_id": "INK2-INKBLOT-ART",
          "task_text": "- [ ] **INK2-INKBLOT-ART** [non-inference] Build a matched IQ4_NL artifact pair from the pinned Base and Inkblot releases and produce a per-tensor change and conversion manifest for the CPU comparison.",
          "acceptance": "Both input shard hashes, all 1,244 named tensors, comparison classifications, quantizer and converter revisions, output hashes, tokenizer and template identities are recorded. Unexpected expert or vision changes and any conversion drift have explicit dispositions."
        }
      ]
    },
    "RI-PAIR": {
      "required_outcome": "Compare the saved models at native three-pass depth with paired held-out correctness, cost and complete failure counts.",
      "review_status": "preserved",
      "review_basis": "Existing CPU task compares Base to served Qwen. It contains no same-depth derivative arm. A result exists for every expected ID and arm, including failures, with source and build digests, per-item outputs, matched profile, paired counts and the predeclared decision.",
      "task_refs": [
        {
          "owner": "handoffs/active/model-evaluation-queue.md",
          "task_id": "INK2-INKBLOT-PAIR",
          "task_text": "- [ ] **INK2-INKBLOT-PAIR** [inference] Compare reloaded Inkling Base and Inkblot at three passes on the same CPU quarter using the frozen 64-item held-out manifest, complete paired outcomes and matched decode timing.",
          "acceptance": "A result exists for every expected ID and arm, including failures, with source and build digests, per-item outputs, matched profile, paired counts and the predeclared decision."
        }
      ]
    },
    "RI-HIP": {
      "required_outcome": "Exercise the qualified HIP path with identical Base items under one and two active requests and isolate any repeated-output failure.",
      "review_status": "preserved",
      "review_basis": "Existing HIP port checks FA residency and CPU tolerance. Its current text has no concurrency control. Retain identical input IDs, runtime parity, one-busy and two-busy raw outputs and complete failure counts.",
      "task_refs": [
        {
          "owner": "handoffs/active/model-evaluation-queue.md",
          "task_id": "INK2-INKBLOT-SLOTS",
          "task_text": "- [ ] **INK2-INKBLOT-SLOTS** [inference] Validate the MI210 indexed-bias port on matched native Base prompts with one and two active requests on the same two-slot server before interpreting Inkblot outputs.",
          "acceptance": "Retain identical input IDs, runtime parity, one-busy and two-busy raw outputs and complete failure counts."
        }
      ]
    },
    "RI-DEPTH": {
      "required_outcome": "Gate a four-pass study on a successful three-pass screen and independently validated runtime parity.",
      "review_status": "closed-with-basis",
      "review_basis": "One extra correct on the publisher slice does not price or establish a fourth-pass benefit. An approved subsequent factorial experiment would answer the marginal-depth question.",
      "task_refs": []
    },
    "RI-TRAIN": {
      "required_outcome": "Gate a training attribution experiment on recoverable lineage and include a simple matched-budget control.",
      "review_status": "closed-with-basis",
      "review_basis": "Original released gate, inputs and checkpoint export do not establish realized lineage. No training reproduction is needed to compare downloadable checkpoints.",
      "task_refs": []
    },
    "RI-PROVENANCE": {
      "required_outcome": "Distinguish author-shared figures, inherited benchmark YAML and distinct task suites from independent evidence.",
      "review_status": "closed-with-basis",
      "review_basis": "Inherited YAML, shared paper and card tables, and tool-use proxies can be mistaken for new outcomes. The retained study notes distinguish source, model, loop depth, exact count and benchmark.",
      "task_refs": []
    }
  },
  "proposed_tasks": [
    {
      "owner": "handoffs/active/model-evaluation-queue.md",
      "task_text": "- [ ] **INK2-INKBLOT-ART** [non-inference] Build a matched IQ4_NL artifact pair from the pinned Base and Inkblot releases and produce a per-tensor change and conversion manifest for the CPU comparison."
    },
    {
      "owner": "handoffs/active/model-evaluation-queue.md",
      "task_text": "- [ ] **INK2-INKBLOT-PAIR** [inference] Compare reloaded Inkling Base and Inkblot at three passes on the same CPU quarter using the frozen 64-item held-out manifest, complete paired outcomes and matched decode timing."
    },
    {
      "owner": "handoffs/active/model-evaluation-queue.md",
      "task_text": "- [ ] **INK2-INKBLOT-SLOTS** [inference] Validate the MI210 indexed-bias port on matched native Base prompts with one and two active requests on the same two-slot server before interpreting Inkblot outputs."
    }
  ]
}
```

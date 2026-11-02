# AutoKernel CPU floor frame requirements

Date: 2026-11-02  
Scope: frame/admission specification for the unchecked CPU A/A calibration in `handoffs/active/autokernel-unified-surface-program.md` (CPU A/A section, task beginning “CPU A/A calibration: screen floor + serving floor…”). This file records known identities and required evidence; it is not a runtime receipt and authorizes no inference, build, benchmark, or store mutation.

## Known authoritative identities

| Item | Known identity | Status / authority |
|---|---|---|
| Selected source champion | `b0ba1d42783585e15b0a0464715fd1fb6a808888` (`b0ba1d427`) | Current unified-surface handoff champion-of-record. |
| Canonical subject | Served Qwen3.8-Flash-Next CPU recipe | UD-1 says this is the CPU surface gate; a bench proxy is inadmissible. |
| Recipe contract | Research commit `6cf25cfab8e45e760cbe4291134b58730ae1eb70`; schema `epyc.autokernel.canonical_recipe.v1` | Defines CPU device, explicit CPU list, NUMA and thread policy, validation, and mismatch refusal. It does not select today's concrete resolved recipe. |
| Contract source files | `resolved_recipe.py` SHA-256 `4f841f1f01c7d8329ffe5c1be2199922d8878a7d02b1224964679309f784984a`; `serving.py` SHA-256 `772177dd47012ba18b1b05621305eccb0bd15ad49d2605ed5da07b3679f6c462` | Recorded by `artifacts/compute/task-evidence-repair-20261031/serving-recipe-cpu/EVIDENCE.json`. |
| Model identity | Three-shard UD-IQ4_XS Qwen3.8-Flash-Next at `/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/`; shard SHA-256s: `00001-of-00003` `5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4`, `00002-of-00003` `577a38a2392b40ca2193cea502e1d92f60b8cd370675d308e0ec21885d9daaa7`, `00003-of-00003` `d4634e6d84f0ebb0940be15c90d3790bf6464e3dea3a1cddc567dc0e83ad8833` | Identity recorded in the CPU identity review; gate must recheck bytes at admission. |
| Drafter identity | `/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf`, SHA-256 `5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6` | MTP self-draft is part of the selected workload; not a no-drafter control. |
| Existing candidate recipe | `/mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/inputs-b0ba1d427/q38fn-cpu-t48-mtp-d4.recipe.json`, SHA-256 `2282bf05ec30c99953a6f39dd6cdb250cb379edfd1f38dca5cdea821b2f63d7f` | Historical executable specification only, not evidence of the current resolved recipe. It specifies CPU/48 threads, `cpu_list=0-95`, ctx 8192, np 1, 256 output tokens, aggregate tok/s and MTP draft_n_max 4. Do not silently reuse it as current. |

## Explicitly unresolved frame fields

These must be supplied and frozen together before any A/A launch. `UNKNOWN` is the present value; do not fill from directory names, old receipts, or assumptions.

| Field | Required frozen value / witness |
|---|---|
| Current resolved recipe | Exact canonical recipe document, schema validation result, canonical serialized bytes and SHA-256; must resolve from the recipe contract for the selected champion. |
| Selected build | Exact source commit/lineage and build manifest/configuration, compiler identity, build outputs; selected `llama-server` executable digest and each loaded ggml DSO digest/linkage. Champion source identity alone does not identify a binary. |
| Requests and estimator | Exact serving request set (prompt/input identities or hashes, request order, context and output limits), repetitions/seed policy, and estimator definition. The historical aggregate tok/s setting is not an approved current request frame. |
| Model and drafter at launch | Resolved paths plus fresh byte digests for all three model shards and the MTP drafter; confirm recipe references those exact files. |
| CPU/NUMA placement | Resolved `cpu_list`, NUMA policy, thread count, process affinity and observed placement witness for each run/session. A broad affinity mask is not proof of actual placement. |
| Host state | Captured host-state payload and its SHA-256, including the declared variables used to admit/stratify runs; exact contention class and observation window. |
| Floors and units | Separately declared screen-floor workload/model and serving-floor harness/measurement; `unit` (`arm`, `session`, or `process`), n, contention model, host-state hash, and interval method for each. |
| A/A design | Matched-arm pairing key and launch/session identity; at least 24 independent pairs for gating-floor calibration and a reported interval. The completed handoff's separate headline rule requires 14 independent launches per arm (28 total) for its stated MDE/power design; do not conflate that headline sample rule with the calibration task's n≥24 pairs. |

## Reproducible admission checks (must pass before accepting floor evidence)

1. **Freeze the frame.** Persist the resolved canonical recipe and request/build/placement/host-state manifests as immutable input files. Record each file's SHA-256. Validate the recipe with the implementation at the pinned Research commit and reject absent or mismatched required CPU/NUMA/thread fields. Record the validation command, exit status and tool version.
2. **Verify champion/build binding.** Record the full selected source commit and prove the build manifest names it. Hash the exact server binary and every loaded ggml DSO. Capture linkage using the project `verify_ggml_linkage.sh` procedure appropriate to this tree; preserve its raw output and exit status. Refuse if lineage, digest, or linkage cannot be established. A version string or build path alone is insufficient.
3. **Verify workload bytes and launch binding.** Recompute SHA-256 for all model shards and MTP drafter; compare to the identities above and to the frozen recipe. Verify request-set hashes, estimator, draft settings and output limits match the frozen frame. Refuse any unlisted input or silent recipe fallback.
4. **Verify placement and host state.** Preserve per-run affinity and NUMA placement observations, host-state payload/hash and contention class. Require each run's witness to match its declared frame; an allowed CPU mask alone does not satisfy observed placement.
5. **Verify floor records.** Require screen and serving floor records to name their own harness, model/workload, estimator, `unit`, n, contention model, host-state hash and interval. Apply the existing unit compatibility rule; reject unit mismatch or missing fields. Keep screen and serving floors distinct.
6. **Verify calibration sufficiency and pairing.** Count at least 24 valid matched A/A pairs under the frozen frame; verify unique independent pair/session identities and report the predeclared interval. Exclude incomplete, mismatched, or contaminated pairs by an explicit recorded rule. Do not substitute the historical five-pair serving floor or Qwen3-4B shakedown.
7. **Emit an admission receipt.** Store exact input paths and hashes, check commands/tool versions/exit statuses, pair ledger, exclusions, floor values and intervals. Any failed or unproven check yields `REFUSED`; it must not produce an accepted floor.

## Provenance boundary

Historical source `acde471c280bdcbcbd346bbe47340ba8c688601b` and later CPU characterization source `141e4bcf5` are not the selected champion identity for this frame. The old anchor-gen-009 provenance does not prove a fresh gate executable or loaded DSO identities. No current resolved recipe, selected binary, request set, placement witness, host-state payload/hash, contention class, or floor measurement is asserted here. No runtime provenance has been inferred.

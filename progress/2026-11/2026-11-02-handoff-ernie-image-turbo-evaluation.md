# 2026-11-02 — handoff ernie-image-turbo-evaluation

## 00:13Z — Resolve typography capture status and inspect retained comparison inputs

### ERNIE handoff: inference inventory and next steps

The 20-prompt typography capture `codex3-ernie-typo20-20261031` already completed rc=0 with 40/40 images; its retained outputs and terminal record are at `/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/`. Do not recapture it: separately attributed human typography review is still needed; the run does not validate the official benchmark score. Qwen-Image-2.1 and ERNIE model bundles and retained ERNIE CPU/HIP launchers exist; a matched comparison still needs a prepared launcher, verified runtime identities, pinned prompts/settings and a published row. The content-filter harness uses the configured ImageGenerator backend, now Qwen, so verify or isolate ERNIE backend identity before attributing an audit to ERNIE. The prior 1024² GPU white-output failure remains unresolved; the handoff says its next test is subject to the 2026-09-17 GPU hold. A bounded row-publication review is in progress with its output registered under the handoff session awaiting directory. No inference, benchmark verdict or checkbox completion occurred. [no-belief: inventory and preparation only]

## 01:24Z — Prepare matched image comparison, ROCm diagnostic, and typography review

### Parallel inference preparation

Dispatched bounded preparation for the matched Qwen/ERNIE comparison launcher and row, the MI210 white-output diagnostic including its hold, and a review packet for the 40 already captured typography images. Registered each result file in this handoff session awaiting directory for event-driven continuation. No row was ready to publish at this boundary; no inference ran and no quality verdict or checkbox completion is asserted. The previous wrap-up committed `462d32c11e83` but failed its serialized push after the push lock remained held; this wrap-up must publish that commit as well. [no-belief: preparation only]

## 01:25Z — Integrate ERNIE typography review packet and matched comparison plan

### ERNIE captured-image review preparation

Prepared `artifacts/compute/ernie-typography-review-20261102/` with all 40 captured outputs, prompts, settings, hashes and unfilled attributed-review fields. Native producer flagged 0/20 896² and 20/20 1024² as possibly blank; this is not a human typography verdict. Prepared four prompt-matched Qwen requests against retained 896² ERNIE outputs in `artifacts/compute/ernie-qwen-matched-prep-20261102/PLAN.json`; a review established that at CFG 1 the Qwen service does not pass the submitted negative prompt, so effective conditioning must not be represented as identical. Qwen CPU versus prior ERNIE GPU timings are not comparable. Qwen and MI210 launcher preparation are underway with event files registered; no row or inference yet. Restored the tracked ratifier absent from the sparse worktree to resolve the pre-commit observer census failure; census now passes. Previous wrap-up failed before commit, so this turn includes its already-staged progress. [no-belief: preparation only]

## 01:25Z — Integrate ERNIE typography review packet and matched comparison plan

### ERNIE captured-image review preparation

Prepared `docs/evidence/ernie-image-evaluation-20261102/typography/` with all 40 captured outputs, prompts, settings, hashes and unfilled attributed-review fields. Native producer flagged 0/20 896² and 20/20 1024² as possibly blank; this is not a human typography verdict. Prepared four prompt-matched Qwen requests against retained 896² ERNIE outputs in `docs/evidence/ernie-image-evaluation-20261102/matched/PLAN.json`; at CFG 1 the Qwen service does not pass the submitted negative prompt, so effective conditioning must not be represented as identical. Qwen CPU versus prior ERNIE GPU timings are not comparable. Qwen launcher preparation is underway; FA diagnostic needs a new launcher and evidence of actual operation selection, since fallback is possible. No row or inference yet. Restored a tracked ratifier absent from this sparse worktree; the pre-commit observer census now passes. Previous failed wrap-ups appended progress, and earlier artifact paths in those entries are superseded by the `docs/evidence/` paths above. [no-belief: preparation only]

## 07:39Z — Integrate image review packets and prepare Qwen and GPU rows

### ERNIE image evaluation: row preparation

The Qwen diagnostic launcher and worker are prepared in `/mnt/raid0/llm/tmp/ernie-qwen-pip03-20261102/`; input weight digest and an independent readiness audit are pending event receipts, so the row is not published. The GPU flash-attention A/B needs a v15 worker and proof of selected operation because requested flash may fall back; preparation is assigned with an event receipt. The typography and matched review packets are included in this commit under `docs/evidence/ernie-image-evaluation-20261102/`. Earlier wrap-up attempts failed the observer census because sparse checkout excluded a tracked ratifier; the lane sparse rules now include that exact file and the census passes. [no-belief: preparation only]

## 07:41Z — Review GPU attention diagnostic preparation

### GPU diagnostic and Qwen capture preparation

Consumed GPU implementation review: `/mnt/raid0/llm/tmp/ernie-fa-ab-20261102/` contains a syntax-checked v15 launcher and worker draft. Its source receipt and native capture still need review, and requested flash attention is not proof of the selected graph operation; fallback must be observed before a causal interpretation. An independent bounded GPU review is underway. Qwen candidate audit fixed a dry-run failure that previously could count an invalid PNG as a native unit. Model digest completion receipt remains missing; an independent custody review is underway. No inference, qualification or publication occurred. The prior wrap-up successfully published `cf110dff4875fe23ab90c90cb5a9a2b0cb009016`, including both durable review packets. [no-belief: preparation only]

## 07:41Z — Review GPU attention diagnostic preparation

### GPU diagnostic and Qwen capture preparation

Consumed GPU implementation review: `/mnt/raid0/llm/tmp/ernie-fa-ab-20261102/` contains a syntax-checked v15 launcher and worker draft. Its source receipt and native capture still need review, and requested flash attention is not proof of the selected graph operation; fallback must be observed before a causal interpretation. An independent bounded GPU review is underway. Qwen candidate audit fixed a dry-run failure that previously could count an invalid PNG as a native unit. Model digest completion receipt remains missing; an independent custody review is underway. No inference, qualification or publication occurred. The prior wrap-up successfully published `cf110dff4875fe23ab90c90cb5a9a2b0cb009016`, including both durable review packets. [no-belief: preparation only]

## 07:43Z — Consume Qwen model digest and GPU diagnostic review

### ERNIE comparison input custody

Consumed the Qwen input digest receipt: 59 files, manifest `/mnt/raid0/llm/tmp/ernie-qwen-pip03-20261102/MODEL-SHA256SUMS`, manifest SHA-256 `d45112904c7f69c3b015006af03d55bf8ec38c0873258ef20838ad43a116f93d`. Runtime metadata and preparation-time server/source digests are recorded in the adjacent `runtime-custody.json`; 896² memory and timing are unmeasured. Independent launcher completion and resource review are underway with registered event files. GPU review repaired dry-run isolation, grant directory handling, incomplete exit status and source-file digest manifest; selected graph operation remains UNKNOWN, so an operation-trace preparation was assigned. No rows published and no inference run. [no-belief: preparation only]

## 07:45Z — Consume GPU trace and Qwen runtime reviews

### Attention trace and Qwen admission preparation

Consumed the GPU trace review: the unapplied patch at `docs/evidence/ernie-image-evaluation-20261102/gpu/trace-graph-selection.patch` passes `git apply --check` against sd.cpp `f3a7fe957d1e615d8766084f000dc3fabf8d7775`; it records graph selection, not actual kernel execution, and shared-helper logs need ERNIE DiT attribution. Experimental source/build preparation is assigned. Qwen runtime review found the default 48 GiB reservation unsupported by measurement and recommended provisional 192 GiB; 896² peak RSS and runtime remain unmeasured. A 300 s exposure start margin can leave interrupted fixed prompts UNKNOWN. A bounded owner is correcting admission and deadline handling, with completion registered. No inference, qualification or row publication. [no-belief: preparation only]

## 07:45Z — Review Qwen resource controls and GPU trace recipe

### Qwen row and GPU trace readiness

Consumed Qwen control and trace-build preparation. The Qwen diagnostic row now reserves provisional 192 GiB and retains affinity, elapsed generation and process peak RSS; the initial 896² request has a provisional two-hour admission guard, with later guards based on prior completed durations. Neither RAM nor time is a measured 896² bound. An independent launcher review is underway before publication. GPU trace build recipe `/mnt/raid0/llm/tmp/ernie-fa-ab-20261102/trace-build-recipe.json` pins sd.cpp `f3a7fe957d1e615d8766084f000dc3fabf8d7775`, ggml `404fcb9d7c96989569e68c9e7881ee3465a05c50`, trace patch and the previously dirty HIP FP8 guard; no source tree was modified and no build or inference was run. Build needs keeper scheduling and selected-operation attribution. Independent reviews have event registrations. [no-belief: preparation only]

# Foundry Local — embeddable ONNX Runtime on-device inference runtime with SDKs, curated model catalog and automatic execution-provider selection

**Intake**: intake-2651 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://github.com/microsoft/foundry-local

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; foundry-local at 48e4e629257a827a464bda9874d0dd2bd2012adf, onnxruntime-genai v0.19.0 at d01b244, ORT 1.31.0, live catalog 2026-11-06). Four of five claims narrowed, one confirmed. Material corrections: 'automatic acceleration' is auto-DETECT plus explicit ACQUIRE (catalog queries are filtered by already-registered EPs, so an app that skips DownloadAndRegisterEps silently runs CPU); WebGPU is not compiled or shipped on Linux; '~20 MB' is the core library only, with ~65-90 MB per process before weights; 'best-performing variant' is device-tier order plus cached-first, never measured throughput; and although no ROCm EP is supported or shipped, ORT-GenAI 0.19 carries an AMDGPU/MIGraphX umbrella EP that Foundry enumerates and never registers. Port-cost estimate for the reusable detect->variant->select pattern: 4-6 engineer-days, excluding any fetch/cache layer.

## Claims and corrections

- claim 0: **narrowed** — C ABI, six advertised SDKs (plus an unadvertised Java SDK) and ONNX Runtime are confirmed. '~20 MB' is the core library on Windows (win-x64 14.6 MB; linux-x64 lib 24.0 MB + 18.5 MB host binary), and the runtime package also pulls ORT 1.31 (~29 MB) and GenAI 0.19 (~36 MB) before weights. In-process is the default, not the only mode: useSharedHost routes the same APIs through foundry-local-host.

- claim 1: **narrowed** — Hardware discovery is automatic but EP acquisition is a two-step explicit flow (GetDiscoverableEps then DownloadAndRegisterEps; no startup auto-registration). Catalog queries are pre-filtered by EPs already registered with ORT, so a GPU host that never registers EPs silently resolves CPU variants. CPU fallback is unconditional and confirmed. EP choice follows the model's own device hint, with CUDA->WebGPU only for generic-GPU models.

- claim 2: **narrowed** — 'No ROCm' is correct for the supported matrix and the live catalog (261 variants, zero ROCm/MIGraphX), but the matrix is not exactly six entries (TensorRT, NvTensorRTRTX, AMDGPU/WinML, OpenVINO CPU/NPU also appear), WebGPU is not compiled or shipped on Linux despite the Learn table, and ORT-GenAI 0.19 exposes an AMDGPU umbrella EP (libamdgpu-ep.so, routes to MIGraphX/DirectX) that Foundry enumerates but never ships or registers.

- claim 3: **narrowed** — Catalog, ONNX-only models, per-device variants, explicit download and local cache are confirmed. Download is an explicit Model::Download() call, not a first-lookup side effect, and selection is not 'best-performing': it takes the first eligible variant under a device-tier sort (NPU > vendor GPU > CUDA GPU > generic GPU > vendor CPU > generic CPU) and prefers any cached variant over a better uncached one. It never ranks by measured throughput.

- claim 4: **unaffected** — Confirmed: /v1/chat/completions, /v1/embeddings, /v1/audio/transcriptions and the full /v1/responses surface; README disclaims multi-user serving, request queuing, continuous batching and GPU sharing. Nuance: there is a serialized wait queue for concurrent engine requests and no authentication in the web service (loopback default).


## Anchors

intake-2651 carries 8 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.

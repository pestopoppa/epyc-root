# P2-2 Tenant Landing — Pre-Reboot Readiness Record (2026-07-29)

**Session**: `claude-gpu-lane` · **Program**: [`handoffs/active/gpu-serving-tie-in-program.md`](../../handoffs/active/gpu-serving-tie-in-program.md) P2-2, decision **D2** (tenant set) under **D11** (activation sequencing, hybrid option C).

**Scope of this pass** — operator constraints in force: master registry **FROZEN**, **proposal diffs only**, **no activation**, no Steps 0-7, no CPU lane, **no region claim**, **no stack or API reload**. A host reboot is imminent, so everything below was chosen to be safely interruptible: read-only inspection and hashing only. **Nothing here is in a state a hard stop would corrupt, and no download was started.**

---

## Headline

**All three D2 tenants are already on disk. P2-2 requires zero downloads** — so the documented `curl -C -` resume-corruption hazard is not on this critical path at all.

Two of three are landing-verified. The third (**whisper**) has a **capability blocker** that D2 did not anticipate — see §3. **The operator resolved it 2026-07-29 with W3 (defer): P2-2 is rescoped to the two verified tenants and whisper is refiled as P2-9, downstream of the bake-off** (§5).

---

## 1. Tenant 1 — dense-27B stock: **VERIFIED LANDED**

| Field | Value | Status |
|---|---|---|
| Path | `/mnt/raid0/llm/models/Qwen_Qwen3.6-27B-Q8_0.gguf` | present |
| Bytes | `28,665,067,072` | matches tenancy row |
| sha256 | `5927dc06c2b19f732fb6e2a6546dff4c130b552f2ab5f91feb3daafe43897b2a` | **independently re-hashed 2026-07-29, matches** |

The tenancy row `qwen36_27b_stock_q8` in `epyc-orchestrator/orchestration/gpu_shadow_lane_tenancy.yaml` already declares exactly these bytes and this sha with `sha256_status: attested`. This pass is an **independent local re-hash** of that attestation, not a restatement of it — the file has not rotted since it was attested at §7 Step 0 P4.

**Nothing further is required of P2-2 for this tenant.** It is landed; residency happens at activation (Steps 0-7), which is out of scope by D11 sequencing.

## 2. Tenant 2 — MiniCPM-o: **artifacts verified, promotion NOT executable pre-reboot**

### 2a. Artifacts (runbook precondition P4) — verified

| Artifact | Bytes | sha256 (re-hashed 2026-07-29) | vs runbook P4 |
|---|---|---|---|
| `MiniCPM-o-4_5-Q4_K_M.gguf` | `5,026,714,400` | `1237a97ee081b8abebc47aa7dad565701e8f5f904cdc92f6723ac4281bbc0932` | **match** |
| `vision/MiniCPM-o-4_5-vision-F16.gguf` | `1,095,113,184` | `1453678cc4e4fe18de241952962e234f265cb8dda780773526103ab8ba82f421` | **match** |
| `audio/MiniCPM-o-4_5-audio-F16.gguf` | `660,167,904` | `d5b188ac7feaf98e17175c3f9bd14bf269301bfd187439fdaa3e3a494fc32ef7` | *new record* — audio is out of runbook scope (vision projector only), hash recorded here so a later audio decision starts from a verified artifact |

**Why this re-hash was worth doing rather than trusting the runbook**: the runbook's P4 sha values are *cited from two different second-hand sources* — the Q4_K_M hash from master-registry `artifact_status.hf_metadata.q4_k_m`, the mmproj hash from lean-era commit `4ab4e0ee`. Neither had been re-verified against the bytes on this disk. They now have been, and both hold.

### 2b. Remaining preconditions — measured 2026-07-29

| # | Precondition | Result |
|---|---|---|
| P1 | Operator grant for promotion + Step-4/6 inference | **not granted** (and out of scope this session) |
| P2 | MI210 free | **PASS** — `rocm-smi`: VRAM 0%, **no KFD PIDs**, nothing on 18072 |
| P3 | Quiet window | **PASS (trivially)** — no AutoPilot process; whole fleet down |
| P4 | Artifacts on disk + hash-known | **PASS** — §2a above |
| P5 | Production v8 HIP binary healthy | **PASS** — `/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server --version` → `version: 10107 (67a433bf4)` |
| P6 | Clean git baselines | research: no tracked modifications (untracked artifacts only), 0 unpushed |
| P7 | Realized fleet = big+quarters, mode `both` | **FAIL** — **no fleet ports are listening** (8000/8070/8072/8083/8085/8086/8087/9000 all empty). The host is already quiesced ahead of the reboot. |

### 2c. Consequence: Steps 1-6 cannot run, and that is the runbook's own rule

The runbook states it explicitly at Step 2: *"If it refuses with `StackPriorsModeError`, nothing is listening — that means P7 failed; do not pass a manual mode override."* With the fleet down, Step 2's pipeline gates compile against no realized mode; Steps 3-6 additionally need a server swap, an API reload, and inference — all excluded by the constraints in force *and* by P7 independently.

So the executable pre-reboot deliverable is the **proposal**, not the promotion. This is a genuine constraint, not a deferral: post-reboot the runbook is mechanical, because every anchor below has now been validated against the live files.

### 2d. Runbook Step-1 anchors — re-validated against the current master registry

Every literal the runbook's Step 1 depends on still resolves exactly as written (checked 2026-07-29 against `epyc-inference-research/orchestration/model_registry.yaml`):

- `roles.vision_escalation` begins at line **4072**; `worker_summarize` at **4139** → the replacement span **4072-4138** is correct and unshifted.
- Line **249** reads verbatim `      vision_escalation: 60    # temporary Qwen2.5-VL alias while 30B escalation replacement is gated`.
- The current block is State A as documented: `Qwen2.5-VL-7B-Instruct`, `Q4_K_M`, `size_gb: 4.4`, no `device`/`runtime_requirements` under `server:`.

**The Step-1 replacement block in the runbook is therefore the proposal diff, verbatim and pre-validated** — no re-derivation is needed post-reboot. The two deliberate deviations it flags (production v8 HIP `binary_dir` per P5; retain historical `k35_*_observation` rows per append-only discipline) both remain correct: P5 re-verified above, and the append-only rule is unchanged.

**Not applied.** No file in either repo was edited by this pass.

## 3. Tenant 3 — whisper: **BLOCKED — the D2 tenant cannot run on the MI210 as implemented**

### 3a. What is actually deployed

D2 budgets whisper at **~1.6 GB** of MI210 VRAM. The deployed whisper is:

- **faster-whisper `large-v3-turbo`**, a **CTranslate2** model (`model.bin`), cached at `/mnt/raid0/llm/cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo` — **1.6 GB on disk**.
- Served by `epyc-inference-research/scripts/voice/whisper_server.py`, hard-coded `device="cpu", compute_type="int8"` (`:61-62`), launched via `scripts/voice/start_whisper_server.sh` on port 9000 out of the `/mnt/raid0/llm/pace-env` venv, and registered as a stack-managed service by `orchestrator_stack.py start_whisper()`.

### 3b. The blocker (measured, not inferred)

**CTranslate2 has no ROCm/HIP backend.** Probed on the actual runtime, `/mnt/raid0/llm/pace-env`:

```
ct2 4.7.2
cuda_devices 0
cpu {'int8', 'float32', 'int8_float32'}
device-ish symbols: ['Device', 'get_cuda_device_count']
get_supported_compute_types('cuda') -> CUDA driver version is insufficient for CUDA runtime version
```

The library exposes exactly two device concepts — CPU and **CUDA**. There is no HIP path, and the CUDA path is dead on this host (no NVIDIA device). **faster-whisper cannot use the MI210 at all**, at any quantization.

The natural alternative — **whisper.cpp**, the ggml-family sibling that *does* build against HIP — **is not on this host**. `/mnt/raid0/llm/whisper-test` contains only audio samples (`audio.wav`, `audio.m4a`, an mp4); there is no whisper.cpp clone, no HIP build, and no `ggml-*whisper*` GGUF anywhere under `/mnt/raid0/llm`.

### 3c. Where D2's 1.6 GB number came from

The `~1.6GB` in D2 is **the disk footprint of the CTranslate2 directory** — i.e. the size of a model that cannot execute on the device. It was never a measured MI210 VRAM figure.

### 3d. Blast radius — small, and in the safe direction

`gpu_shadow_lane_np_ceiling.yaml` bakes whisper's 1.6 GB into the **`phase2_resident_set`** budget rows (`dynamic_budget_gib: 27.0`, derived as 64 − 27.74 − ~8.6 co-resident). If whisper is never GPU-resident, that budget is **conservative by ~1.6 GiB**: it under-states available dynamic VRAM, so every ceiling derived from it remains **safe** — no ceiling authorises more than the hardware can give. The error polarity is fail-safe, and no `np`/context cell needs to be withdrawn.

The cost is therefore opportunity, not correctness: the lane is carrying a reservation for a tenant that may never arrive.

### 3e. Decision — **operator chose W3 (defer), 2026-07-29**

**Outcome: P2-2 is rescoped to the two verified tenants; whisper is refiled as P2-9, downstream of the bake-off. W2 is explicitly ruled out for now — no whisper.cpp clone, no HIP build, no GGUF download.** The W1-vs-W2 question itself stays open and is decided later, with the bake-off numbers in hand. The options as put to the operator:

This is an operator call and is being routed as a decision package rather than resolved unilaterally, because every option changes what "P2-2 complete" means:

- **W1 — whisper stays on CPU; drop it from the GPU tenant set.** Cheapest and zero-risk; the ASR service already works and is not a GPU bottleneck. Reclaims ~1.6 GiB of the `phase2_resident_set` budget (a ceiling-table amendment, downstream of the P2-5j sweep by the same gate as every other carve variant). Closes P2-2 with a two-tenant set and an amended D2.
- **W2 — port whisper to whisper.cpp on HIP.** Clone + HIP build + a ~1.6 GB `ggml-large-v3-turbo` download, a new launcher, and a transcription-parity check against the current CPU service before anything swaps. Real work, a new download (reboot-hazard class), and a quality re-validation — none of it on the P3 bake-off critical path.
- **W3 — defer whisper, land the two verified tenants now.** Mark P2-2 complete for dense-27B + MiniCPM-o, file whisper as its own item downstream of the bake-off. Keeps D11's sequencing moving at full speed.

**Recommendation given: W3 now, W1 as the likely eventual verdict — and W3 is what the operator chose.** W3 unblocks the decided D11 sequence immediately without pre-committing the tenant-set question; W1 is where the evidence points, since the only thing whisper gains from the GPU is throughput on a service that is already meeting its duty on CPU — but that is a judgement the operator should make with the bake-off numbers in hand, not before them. **Default if no choice is made: W3**, which forecloses nothing.

---

## 4. Net state of P2-2 after this pass

| Tenant | State | Blocking on |
|---|---|---|
| dense-27B stock | **verified landed** (bytes + sha re-hashed, tenancy row already correct) | nothing — residency is an activation-time act |
| MiniCPM-o | **artifacts verified; promotion proposal pre-validated** | P1 operator grant + P7 fleet up (i.e. post-reboot) — **the sole remaining P2-2 task** |
| whisper | **out of P2-2 scope — deferred by operator choice W3** | refiled as **P2-9**, downstream of the P3 bake-off |

**Interruption safety**: nothing started by this pass must survive the reboot. All three verification results are recorded above; every one is reproducible from scratch in minutes by re-hashing.


---

## 5. Post-decision state (2026-07-29, after the operator's W3)

- **P2-2 rescoped to two tenants.** dense-27B stock is landed and verified; MiniCPM-o's promotion (P2-2c) is the sole remaining task and is post-reboot by the runbook's own P7 rule.
- **Whisper refiled as P2-9**, downstream of the bake-off, with W1 (stay on CPU, amend D2) as the standing recommendation and **W2 explicitly ruled out for now** — no clone, no HIP build, no `ggml` GGUF download.
- **The fail-safe note is now where a VRAM reader will actually hit it**: a banner at the head of `epyc-orchestrator/orchestration/gpu_shadow_lane_np_ceiling.yaml` (commit `f7a02d94`, comment-only — 170 lane tests pass, Stage-0 smoke `pass`). It exists to block the obvious wrong reaction to §3: *"whisper isn't landing, so free up its 1.6 GiB."* Those rows are conservative, not wrong, and reclaiming the headroom is a ceiling amendment gated downstream of P2-5j.

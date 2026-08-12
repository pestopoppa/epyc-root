# P-GPU-1 retro-certification of the ggml-linkage window (2026-07-31 → 2026-08-12)

**Author** Phase 7 audit session, 2026-08-12. **Authority** operator decision H-6, *Option A —
audit-first* (`~/.claude/plans/serialized-jumping-aho.md` § "Operator decisions (locked in,
2026-08-12)"): retro-certify the in-window GPU-attributed set, re-run only what a live decision
cites.

**Governing text** `measurement/protocols/gpu-cross-device.md` (Annex G of `MEASUREMENT.md`, same
human-only trust boundary):

- `:28` — *"Required evidence fields — ALL mandatory; a claim missing ANY field is an observation."*
- `:36-38` — field 3, **Binary/model identity**: *"exact worktree, branch, commit, binary path,
  `LD_LIBRARY_PATH`, backend list; exact model path, mmproj (if used), quant, context, KV quant,
  reasoning/sampling flags, spec-dec mode."*
- `:16-21` — **kernel-provenance rule**: a decision-grade claim MAY ONLY be produced on a
  production-named kernel; measurements on `llama.cpp-experimental` / candidate / fork kernels are
  **OBSERVATIONS ONLY** and *"MUST NOT gate any keep / revert / deploy / promote / buy / close
  decision."*
- `:49-53` — **retro-certification**: upgrade ONLY IF (a) produced on a production-named kernel AND
  (b) a field-by-field audit confirms **every** mandatory field present, *"including the
  before-and-after clocks/power/temperature record. Any absent field → the artifact remains
  observation-grade and MUST be re-run. **No partial upgrades.**"*

This audit ran **zero inference**. Every statement below is from reading committed artifacts,
`git log`, `jq` key inventories, and file metadata.

---

## 1. The hazard, and why the window has this shape

`INC-20260731-ggml-linkage-silent-cpu-fallback`
(`docs/reference/agent-config/INCIDENT_LOG.md:129-141`) records the mechanism: `/etc/environment:5`
and `devcontainer.json:57` placed the production **CPU-only** `build/bin` early in
`LD_LIBRARY_PATH`, so a freshly built HIP binary resolved the frozen production ggml, found no GPU,
and ran full-CPU **while printing `use gpu = 1`**. `ldd` cannot detect this because llama.cpp
*dlopens* `libggml-hip.so`.

**Window opens** at the fix: epyc-root commit `136894e8` *"ggml linkage: drop CPU-only llama.cpp
dirs from global LD_LIBRARY_PATH"*, **2026-07-31T16:04:17Z**, editing `.devcontainer/devcontainer.json`.

**Window does not close for long-lived containers.** Measured first-hand in this session's shell on
2026-08-12 (instrument: `echo $LD_LIBRARY_PATH`, one sample, this container):

```
/etc/environment (on disk, post-fix): LD_LIBRARY_PATH="/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib"
this container (live):                /opt/AMD/aocc-compiler-5.0.0/lib:/mnt/raid0/llm/llama.cpp/build/bin:/mnt/raid0/llm/llama.cpp-dflash/build/bin:/opt/rocm/lib
```

The CPU-only production `build/bin` still leads `/opt/rocm/lib` here, twelve days after the fix.
The window is therefore **not** "before 2026-07-31T16:04Z" — it is "any run whose process
inherited a pre-fix environment", which is why the audit covers the whole 07-31 → 08-12 span rather
than stopping at the fix commit.

**Scope note that carries most of the weight below.** P-GPU-1 governs *"decision-gating GPU
throughput, spec-dec, and residency numbers"* (`:12-14`). The linkage hazard corrupts **speed and
device-residency** numbers. It does **not** corrupt an **accuracy** number: a model that silently
executed on the CPU produces the same tokens, so the same score. This distinction determines the
verdict on the vision cutover in §4.

---

## 2. Method

1. **Window enumeration** — `git log --since=2026-07-30 --until=2026-08-13 --name-only` over
   `data/` and `benchmarks/` in both repos; directory/file name date stamps; embedded
   `date_utc` / `created_at` / `started_utc` fields. **File mtimes were used only as a hint** — the
   research repo is a shared clone whose checkouts rewrite mtimes (a `find -newermt` sweep of
   `benchmarks/results/` returned only the two 2026-08-12 `scout/` dirs, which is a checkout
   artifact, not the truth).
2. **GPU attribution** — content markers: `ROCm`, `MI210`, `gfx90a`, `--device ROCm0`, `-ngl`,
   `rocm-smi`, `build-hip`, `KFD`, VRAM fields.
3. **Field audit** — full key inventory per JSON via
   `jq -r 'paths(scalars)|join(".")' <file> | sort -u`, so that **absence is proven from the whole
   key set** rather than inferred from a failed grep for one spelling.
4. **Citation check** — identifier grep across `handoffs/active/`, `handoffs/blocked/`,
   `handoffs/completed/`, `wiki/`, `docs/`, `MEASUREMENT.md`, `agents/`, and the
   `epyc-orchestrator` registry/descriptor/derived tree.

Note on locations: **epyc-root has no `benchmarks/results/` tree.** All measurement artifacts in
this audit live under `/workspace/repos/epyc-inference-research/data/` (= `/mnt/raid0/llm/epyc-inference-research/data/`).
The prior sweep's `benchmarks/results/.../gpu_coresidency_20260731` path does not exist; the real
path is `data/gpu_coresidency_20260731`.

---

## 3. The enumerated set

Classification key: **CERTIFIABLE** = every mandatory field present on a production-named kernel ·
**OBSERVATION-GRADE** = one or more mandatory fields absent, or produced on a non-production kernel;
must be re-run before it can gate anything · **OUT OF SCOPE** = not a P-GPU-1 claim class.

| # | Artifact (under `/workspace/repos/epyc-inference-research/data/`) | Kernel | LD_LIB | backend list | binary path | commit | outside-binary residency | Class |
|---|---|---|---|---|---|---|---|---|
| 1 | `gpu_coresidency_20260731/gpu_coresidency_results.json` | **experimental** `llama.cpp-experimental/build-v8-hip` | ✗ | ✗ | partial (`binary_tree`, no sha256) | ✗ | **partial ✓** — `gpu_busy_pct_during_decode "99-100"`, `state1_util.txt` 14 samples, `vram_gib` 36.7/61.66/62.58 | **OBSERVATION-GRADE** |
| 2 | `vision_mmmu_cutover_20260731/results.json` | **experimental** `build-v8-hip` | ✗ (harness-only, `harness.py:242`) | ✗ | `_meta.server` only, no sha256 | ✗ | **partial ✓** — sampled VRAM per arm, 7,685 / 8,079 / 12,069 / 21,049 MB model-VRAM | **OBSERVATION-GRADE** |
| 3 | `vision_quality_42q_20260731/vlquality_results.json` | **experimental** `build-v8-hip` | ✗ (harness-only, `vlquality.py:144`) | ✗ | ✗ (harness-only) | ✗ | ✗ — **no `_meta` block at all** | **OBSERVATION-GRADE** (weakest) |
| 4 | `vision_kv_q8_ab_20260802/arm_{f16,q8_0}.json` | production **v8** `b10107-67a433bf4` | ✗ (harness-only, `run_kv_ab.py:171`) | ✗ | ✓ argv, no sha256 | ✓ `_meta.props.build_info` | ✗ — VRAM **predicted**, not sampled | **OBSERVATION-GRADE** |
| 5 | `mi210-h2d-d2h/20260803T131500Z/receipt.json` | n/a — `rocm-bandwidth-test 2.6.0` | n/a | n/a | n/a | n/a | device identity verified 3 ways (PCI `0x740f`, NUMA node, KFD node 4) | **OUT OF SCOPE** (self-graded `"grade":"OBSERVATION"`, `"protocol":null`) |
| 6 | `mi210-mfma-peak/20260803T143200Z/`, `mi210-achievable-bandwidth/20260803T124401Z/` | n/a — custom HIP microbenchmarks | n/a | n/a | n/a | n/a | — | **OUT OF SCOPE** (both self-graded `"grade":"OBSERVATION"`) |
| 7 | `batched_decode/e5-gemma-nomtp-v9-20260812T0818Z/` | production **v9** `10125 (0db32c06e)` | **✓ recorded** | ✗ | ✓ path, no sha256 | ✓ `attestation.binary_version` | CPU-side ✓ (`live_affinity_verified`, page-placement) | **OUT OF SCOPE for P-GPU-1** — it is a **CPU** run (`attestation.binary = .../llama.cpp/build/bin/llama-server`, `protocol_id "P-BENCH-3"`), self-voided to observation grade on host uptime |
| 8 | `batched_decode/e5-gemma-nomtp-v9-20260812T0800Z/`, `.../e5-gemma-crossbinary-repair-20260812T0745Z/` | production v9 | ✓ | ✗ | ✓ | ✓ | — | **VOID — zero measurements** (see §3.1) |
| 9 | `judge_suite_headtohead_20260802/` | production **v8** `b10107-67a433bf4` | ✗ | ✗ | ✗ | ✓ `live_shape.json props.build_info` | ✗ — device `"MI210 ROCm0"` is **hardcoded in the harness** (`run_judge_suite.py:167`), never verified against the live server | **OBSERVATION-GRADE** as a GPU claim; quality-instrument scope otherwise |
| 10 | `kernel-v9-candidate/promotion-plan-20260810/production-v9-gpu-cert-run-locked/` | production **v9** `0db32c06e`, branch `production-consolidated-v9` | **✓** `commands.sh:5` + `guard_state.json` | **✓** `--list-devices` → `ROCm0: AMD Instinct MI210 (65520 MiB…)` | **✓** `/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server` | **✓** `guard_state.json.git.binary.head` `0db32c06e`, `production_named_kernel: true` | **✓** `rocm` snapshots at 5 phases incl. `before_launch` / `after_cleanup`, with clocks + power + temp | **CERTIFIABLE** (see §3.2) |
| 11 | `gpu-mi210/qwen36-27b-q8-dflash-pgpu1-v9/cert-run-20260811-locked/run-20260811T010339Z/` | production **v9** `0db32c06e`, branch `production-consolidated-v9` | **✓** `binary_identity.json.environment.LD_LIBRARY_PATH = "/mnt/raid0/llm/llama.cpp/build-hip/bin:/opt/rocm/lib"` + per-rep `environment.json` | **✓** `hardware_state.json` (live `rocminfo`) | **✓** + **binary sha256** `21cfb750dc0ba4b3add0674fcb9dd061d77b3604ebf8e1d063ba0e2c51902feb` | **✓** `git.commit.stdout 0db32c06e3e550065b78311a6031ef3dd2c4f27c` | **✓** `vram_pid_util_samples`, `rocm_{clocks,power,temp}_before_after`, `cleanup_proof` — all graded `present` | **CERTIFIABLE** (see §3.2a) |

Additional in-window GPU-attributed artifacts found in the extended sweep, **not** individually
field-audited here because **no live decision cites them** (verified in §4) — listed so the
enumeration is honest about its own edges, and flagged for audit before any of them is ever cited:

- **epyc-root `/workspace/artifacts/gpu-aux-baselines/`** (all 2026-08-12): `a3_bge_mi210_20260812.jsonl`
  (`"backend":"ROCm"`, `"ngl":99`); `a9_stage{1,2}_result.json` + `a9_gfx90a_training_viability_20260812.md`
  (`torch 2.5.1+rocm6.2`, `hip 6.2.41133`, sampled `peak_vram_torch_mb`); `a10_iq2_decode_attribution_20260812.md`
  (rocprof-v1, `-ngl 99`, 39.40 t/s). `a10_iq2_vgpr_lever_20260812.md` and
  `artifacts/audit/autokernel-static-probes-20260810.md` are **static disassembly** — zero GPU time,
  so the linkage hazard cannot apply.
- **`data/kernel-v9-candidate/promotion-plan-20260810/`** — the non-`-locked` siblings
  `v9-gpu-smoke-{plan,run}` and `production-v9-gpu-cert-{plan,run}`.
- **`data/gfx90a-counters/gfx90a-counters-20260803.txt`** — hardware counter dump, not a claim.
- **`/workspace/artifacts/operator/v9-qualification-20260810T235723Z-0db32c06e/summary.json`** —
  carries `hip_server_sha256` and decode_tps figures but is already flagged `decision_grade: false`.
- **`data/speech_kernel_freeze_20260731/`** — contains MI210 GPU STT arms, but it is a *preservation
  copy*; the measurements predate the window. Out of scope, recorded to prevent a future sweep
  re-flagging it.

### 3.1 The two VOID runs — not measurements, and a trap in them

Both carry `VOID-DO-NOT-USE.md` and `void_detail.measurements_present: false`. Both failed at
`affinity preflight exited 1` — an absolute-import `sys.path` bug in `affinity_preflight.py`, fixed
in epyc-orchestrator `efbbbbe9`. `e5-gemma-crossbinary-repair-20260812T0745Z/VOID-DO-NOT-USE.md`
additionally **retracts its own original diagnosis** (an alleged gemma4-MTP-on-v9 defect) and
records that gemma4 MTP is verified working on production v9.

**Trap worth propagating:** both `summary.csv` files report `error_rate = 1.0` computed from
**0/0** — a value manufactured from an empty denominator. Any scraper reading `summary.csv` without
reading the manifest's `void_detail` ingests a fabricated 100% error rate. This is the "EMPTY input"
member of the vacuous-verification family.

### 3.2 The one artifact that passes — and what it proves

`kernel-v9-candidate/promotion-plan-20260810/production-v9-gpu-cert-run-locked/` is the only
in-window GPU artifact that satisfies field 3 in full. It matters twice over.

It banks `LD_LIBRARY_PATH` **as a single-entry override**, not as an inherited value —
`commands.sh:5`:

```
env LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp/build-hip/bin GGML_IQK=1 ROCR_VISIBLE_DEVICES=0 \
  HIP_VISIBLE_DEVICES=0 CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=1 numactl --interleave=all \
  /mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server -m .../Qwen3.6-27B-MTP-Q8_0.gguf ... --device ROCm0 -ngl 999 ...
```

Because the assignment *replaces* the inherited variable, the stale container path could not
participate in resolution — this run is immune to INC-20260731 **by construction**, and it proves
it rather than asserting it. `guard_state.json` independently records the binary path, a live
`--list-devices` backend enumeration, `branch: production-consolidated-v9`, `head: 0db32c06e`, and
`production_named_kernel: true`; `summary.json` carries `rocm` snapshots (clocks, power,
temperature, memory, utilisation) at `before_launch`, `after_health`, `after_request`,
`before_cleanup`, `after_cleanup`.

**This is the template every re-run in §6 should be executed against.** It also settles the highest
stake in the window: the v9 promotion attestation
(`handoffs/active/v9-kernel-promotion-attestation.json`), which gates the CLAUDE.md-level production
freeze, rests on an artifact that survives this audit.

One caveat recorded, not resolved: `summary.json`'s own `pgpu1_protocol_fields` block contains
*policy descriptions* (e.g. `"post_cleanup_vram_sample": "collected as memory_samples
phase=after_cleanup after server termination"`), not values — a grep for `LD_LIBRARY_PATH` in
`summary.json` returns **0**. The evidence is real but lives in sibling files (`commands.sh`,
`guard_state.json`). A verifier that reads only the summary would wrongly fail this run. That is an
argument for the field-3 amendment already queued for operator ratification (plan Phase 5,
*"P-GPU-1 amendment text"*): name a **verifier-produced linkage receipt** at a fixed path.

### 3.2a The second certifiable artifact — and a machine verifier nobody pointed at the window

`data/gpu-mi210/qwen36-27b-q8-dflash-pgpu1-v9/cert-run-20260811-locked/run-20260811T010339Z/` is the
most completely evidenced GPU run in the window. It is the only artifact carrying the **full
outside-the-binary kit** the constitution asks for: `binary_identity.json` (binary path + **sha256**
+ `environment.LD_LIBRARY_PATH` + `git.branch`/`git.commit` stdout), `hardware_state.json` (live
`rocminfo`), per-rep `environment.json`, `pre_execution_binding.json` / `post_execution_binding.json`,
and `guard_state.json`.

Its `summary.json.status` is `"failed"` — the DFlash lane was ruled ineligible (pooled acceptance
below the `0.60` P-DFLASH-LINEUP-1 floor). **That is a properly certified negative result, not a
failed measurement**, and it is the correct outcome to have banked.

**It also contains a checked-in machine verifier's verdict.** `completeness_audit.json` records
`"overall": "complete"` with all **13** required P-GPU-1 fields `present` —
`binary_model_identity`, `production_named_kernel_identity`, `rocm_clocks_before_after`,
`rocm_power_before_after`, `rocm_temp_before_after`, `vram_pid_util_samples`, `cleanup_proof`,
`post_cleanup_vram_sample`, `warmup_discard_policy`, `rep_count`, `result_grammar`,
`cpu_interference_policy`, `summary_json`. The verifier is
`epyc-inference-research/scripts/benchmark/pgpu1_artifact_completeness_audit.py`, and it emits
exactly the verdict this Phase 7 was chartered to produce: `"recommendation":
"retro_cert_candidate"` or `"rerun_required"`.

**Nobody ran it across the window.** Doing so is cheap, read-only, and should be the standing gate
— but *not before the defect below is fixed*.

### 3.2a-bis The verifier's field-3 check is vacuous — demonstrated, not asserted

`pgpu1_artifact_completeness_audit.py:243-246` computes
`state = "present" if matches else "missing"`, where `matches` is **any** hit among a rule's
pattern tuple. The `binary_model_identity` rule (`:73-84`) ORs six patterns:

```
r"llama-server", r"llama\.cpp-experimental", r"\.gguf\b", r"rev-parse", r"ld_library_path", r"rocm0"
```

So an artifact containing the string `llama-server` **passes field 3 without banking
`LD_LIBRARY_PATH` at all** — the exact field this entire audit exists to check. Two further
consequences: the scanner reads *every file in the directory*, so shipping the harness source is
enough to match `ld_library_path` even when no artifact records a value; and
`llama\.cpp-experimental` is a **positive** identity pattern, so an experimental-kernel path counts
*toward* completeness while `:16-21` makes it disqualifying.

Demonstrated on a known-deficient artifact (read-only, 2026-08-12):

```
$ python3 scripts/benchmark/pgpu1_artifact_completeness_audit.py data/vision_mmmu_cutover_20260731
binary_model_identity: present
  matched: ['llama-server', 'llama\\.cpp-experimental', '\\.gguf\\b', 'ld_library_path', 'rocm0']
```

`results.json` for that campaign banks **no** `LD_LIBRARY_PATH` (§3, row 2) — the `ld_library_path`
hit comes from `harness.py:242`, the source line that *sets* it. The verifier graded field 3
**present** on an artifact that fails it.

**No wrong conclusion resulted here** — the artifact was still correctly graded `incomplete` overall
(`missing_required_fields`: `summary_json`, `rocm_clocks_before_after`,
`production_named_kernel_identity`, `warmup_discard_policy`, `rep_count`, `cpu_interference_policy`,
`cleanup_proof`, `post_cleanup_vram_sample`) because eight other fields were absent. The exposure is
an artifact that is complete in every field *except* the linkage one: it would be stamped
`retro_cert_candidate`. This is the **"KEY too wide"** member of the vacuous-verification family —
a check that passes for a reason unrelated to what it is testing. Fix proposed in §7.

### 3.2b The stronger pattern already in this repo — `autokernel_controls_*`

The in-window AutoKernel control campaigns (`data/autokernel_controls_20260805/`,
`data/autokernel_controls_3pct_20260805/`) are **CPU** runs (`libggml-cpu.so`, no HIP), so they are
outside P-GPU-1. They are recorded here because they solve the field-3 problem more completely than
row 10 does, and the amendment should copy them rather than invent something:

- **`linkage.copy.txt` + `linkage.production.txt`** — banked, per-library resolved-path receipts
  (`ldd` output), one for the pinned copy and one for production, so the two can be diffed. This is
  the artifact shape that `gpu_coresidency`'s unfalsifiable `ggml_linkage_verified: true` boolean
  should have been.
- **`anchor_binary_copy/`** — the binary *and all its ggml libraries* are **copied into the
  campaign directory**, and `linkage.copy.txt` proves every `libggml-*.so.0` resolved to that copy
  (`.../data/autokernel_controls_20260805/anchor_binary_copy/libggml-cpu.so.0`). Resolution is
  self-contained, so INC-20260731 is impossible **and** the exact binary survives for replay — a
  property row 10 does not have (§3.4: the experimental `bin/` holds seven build numbers and its
  identity at run time is unrecoverable).
- Alongside: `claim_receipt.json`, `region_claim.jsonl`, `host.json`, `preflight.json`,
  `campaign_declaration.json`, `runtime-source-label.json`.

For GPU the same pattern needs one addition `ldd` cannot supply — because llama.cpp **dlopens**
`libggml-hip.so`, a link-time receipt does not prove the HIP backend was *loaded*. Pair it with the
row-10 `--list-devices` capture and a during-run VRAM/KFD sample.

### 3.3 Cross-cutting field findings

- **`LD_LIBRARY_PATH` is banked in 2 of the 10 rows** (#7, a CPU run; #10). In the three vision
  artifacts it exists **only inside harness source**. Code that *sets* an env var is not an artifact
  that *records* it — and given the three-ggml-generations hazard, that is precisely the field a
  retro-certification cannot infer.
- **No artifact except #10 carries rocm-smi records before AND after.** Clocks, power and
  temperature are absent from every other row. Field 1 fails universally outside #10.
- **No binary sha256, no per-lib sha256, no `binary_identity.json` / `environment.json` /
  `linkage_receipt`** in rows 1–4 or 9. `gpu_coresidency_results.json` asserts
  `method.ggml_linkage_verified: true` with **no receipt to inspect** — an unfalsifiable field, and
  the exact shape the amendment should replace.
- **Mitigating, and worth stating plainly:** the three vision harnesses **prepend** their HIP build
  dir (`harness.py:242`, `vlquality.py:144`, `run_kv_ab.py:171` — the last carries the comment
  `# build-hip MUST lead: three ggml`). Prepending defeats the hazard. The harnesses were right;
  the artifacts merely failed to bank the proof. This is why the verdicts below distinguish
  *"formally observation-grade"* from *"probably wrong"* — **nothing in this audit shows any number
  to be wrong.**

### 3.4 Kernel provenance is the harder blocker

Rows 1–3 ran on `/mnt/raid0/llm/llama.cpp-experimental/build-v8-hip`. Under `:16-21` that is an
**automatic** observation grade regardless of field completeness, and retro-certification condition
(a) fails outright. Forensics on the build tree (mtimes, not banked evidence): every `libggml-*.so`
there is dated **2026-07-25 10:06**, and the `libllama-common.so` soname resolves to build `10107`
— numerically the v8 production build number. So the tree was plausibly stable and v8-equivalent at
run time. **This does not certify anything**: the same `bin/` holds seven co-resident build numbers
(`10098, 10100, 10101, 10102, 10104, 10106, 10107`), so which one a given run linked is not
recoverable from the artifact, and the protocol's rule is about the *named tree*, not the build
number. Recorded because it bears on re-run cost: the binary and libraries still exist, so a re-run
needs no rebuild.

---

## 4. Citation findings — does a live decision cite an in-window GPU number?

**Yes. Three live gating citations, one of which is constitutional.**

### C1 — Vision cutover → `vision_mmmu_cutover_20260731` — **LIVE, GATING**

The deployed swap of `worker_vision` / `vision_escalation` from Qwen2.5-VL-7B to
Qwen3-VL-30B-A3B-Instruct Q4_K_M, landed in epyc-orchestrator `a517793c` (2026-08-01).

| Citation | Content |
|---|---|
| `orchestration/model_registry.yaml:2229-2230`, `:2302` | `evidence: data/vision_mmmu_cutover_20260731/results.json`, `evidence_harness: .../harness.py` |
| `orchestration/model_registry.yaml:2227` | `vl_score_protocol: 'MMMU-val, 250 multiple-choice single-image questions, MI210 (ROCm0), 2026-07-31. Paired exact McNemar vs Qwen2.5-VL-7B (131/250): +11.2 pp, p=0.0011.'` |
| `orchestration/model_registry.yaml:1470`, `model_registry_full.yaml:1034` | role description carrying `MMMU-250 63.6% vs Qwen2.5-VL-7B 52.4%, +11.2 pp` |
| `orchestration/model_descriptors.yaml:398-419`, `derived/stack_priors.yaml:1995,2013-2014,3081,3099-3100` | same evidence keys, compiled/derived |
| `handoffs/active/multimodal-pipeline.md:311-321`, `wiki/multimodal.md:583-588` | the same table — but citing the **scratch path** `/mnt/raid0/llm/tmp/vision_final_results.json` (`:314` and `:588` respectively; a third stale copy at `multimodal-pipeline.md:105` still calls the run *"IN FLIGHT … (no numbers yet)"*) |

**Verdict — the accuracy numbers do NOT need to be re-run on account of the linkage hazard.**
Three independent reasons, in decreasing strength:

1. **Class.** `63.6% vs 52.4%, +11.2 pp, McNemar p=0.0011` is an **accuracy** claim. A silent CPU
   fallback changes *where* the tokens were computed, not *which* tokens. The hazard cannot move
   this number, so P-GPU-1's linkage requirement has no purchase on it. P-GPU-1 governs throughput,
   spec-dec and residency (`:12-14`).
2. **Mechanism.** `harness.py:242` prepends the HIP build dir, so the hazard's precondition did not
   hold for this run.
3. **Residency.** Model-VRAM sampled per arm scales monotonically with model size — 7,685 / 8,079 /
   12,069 / 21,049 MB (instrument `rocm-smi --showmeminfo vram`, sampled before and after each model
   load, `harness.py:269-283`; window = model load, not decode). Weights were on the GPU.

**But two numbers in the same artifact ARE in P-GPU-1 scope and ARE observation-grade**, because
the run was on an experimental kernel:

- **`vram_mb_total 21061`** (quoted in the registry as the vision role's VRAM budget) — a residency
  number.
- **`decode is ~1.9x SLOWER (112.20 vs 214.54 t/s median…)`**
  (`model_registry.yaml:2231-2238`) — a **throughput** number, the exact class the hazard corrupts,
  measured with no linkage evidence on `llama.cpp-experimental`. This one should not gate a
  capacity or routing decision as written.

### C2 — `gpu_coresidency_20260731` → `architect_general` throughput priors — **LIVE, GATING**

`orchestration/model_registry.yaml:2478` (and L1166, L1168, L2136, L9439, L9962 per the artifact's
own README) carry
`attest: "published stack measurement record §01, 2026-07-31; co-residency data/gpu_coresidency_20260731/gpu_coresidency_results.json"`
backing `qwen36_27b_mtp_q8_local.production_throughput`: `baseline_tps: 30.87`,
`contended_tps: 19.81`, `vram_gib: 36.7`. These feed `q_scorer` baselines and `routing_hints`.

**This is the sharpest problem in the window.** These are **throughput and residency** numbers —
squarely in P-GPU-1 scope, the exact class the linkage hazard corrupts — measured on an
**experimental** kernel with **no `LD_LIBRARY_PATH`, no commit, no version, and only
`ggml_linkage_verified: true` as an unfalsifiable assertion**. It further fails P-BENCH-1: `n=3` per
state supporting a **−35.8%** contention claim (n≥5 required for ≥5% claims).

Compounding: the artifact **grades itself as non-gating**. `gpu_coresidency_results.json:1` reads
`"title": "GPU co-residency curiosity measurement (no gate)"`, and its `caveats[2]` states *"No
gate, no threshold, no pass/fail is attached to any number here."* **The registry attests to it
anyway.** That is a citation defect independent of the linkage question: a live production config
cites an artifact that disclaims the role it has been given.

Mitigating: this artifact is the only one in rows 1–4 carrying genuine during-run residency evidence
(`gpu_busy_pct_during_decode "99-100"`, sampled across 14 `rocm-smi` reads in `state1_util.txt`;
`vram_gib` 36.7 → 61.66 → 62.58 across states). The run was GPU-resident. The **magnitudes** remain
uncertifiable.

### C3 — `mi210-h2d-d2h` (+ mfma-peak, achievable-bandwidth) → `MEASUREMENT.md` — **LIVE, GATING, CONSTITUTIONAL**

`MEASUREMENT.md:278-292`, `MI210-SUBSTRATE-CONSTANTS-1 — measured substrate constants (RATIFIED
2026-08-03)`, ratifies three in-window receipts as the roofline denominators of the project:
`172.2 TFLOPS`, `1433.3 GB/s`, `28.89 / 28.20 GB/s`, `Ridge 120.1 FLOP/byte`. Consumed by
`handoffs/active/gpu-acceleration-path.md:310-315` (which used it to retire a prior figure *"wrong
by 2.2×"*) and `handoffs/active/autokernel-research-loop.md:2700-2712` (imported into
`substrate_facts.json` / `substrate.py`).

**Verdict: OUT OF SCOPE for the linkage hazard, but flagged for the operator.** All three are
non-llama.cpp microbenchmarks (`rocm-bandwidth-test 2.6.0`; custom HIP kernels) — no `dlopen` of
`libggml-hip.so`, so INC-20260731 cannot touch them. However **all three receipts self-declare
`"grade": "OBSERVATION"` and `"protocol": null`**, and `mi210-h2d-d2h/receipt.json` `notes[2]`
concedes *"With n=2-3 per node and no CI this does not support a per-node ranking."* They are
ratified constants standing on self-declared observations. That is a governance question for the
measurement trust boundary, not a linkage question, and **this audit does not propose changing it.**

### C4 — v9 kernel promotion — **LIVE, GATING, and it survives**

`handoffs/active/v9-kernel-promotion-attestation.json:40,46,51` cites the row-10 artifacts;
status `production_promoted_frozen`, `promoted_at 2026-08-10T23:59:00Z`. Per §3.2 the GPU
certification run is CERTIFIABLE. **No action.**

### C5 — `judge_suite_headtohead_20260802` — LIVE, gating, but not as a GPU claim

`handoffs/active/architect-model-selection-bench.md:365-369` uses the `tool_compliance` spread
(85.2% … 70.4%, 14.8 pp) to gate an architect model decision. These are **quality** scores; the
linkage hazard cannot move them. Noted only because
`arm_architect_general_27b/report.json` sets `headline_may4_comparable.decision_grade: true` with no
attestation ref, and the harness *hardcodes* `"device": "MI210 ROCm0"` rather than verifying it.

### C6 — Orphans and stale rows (no live decision cites them)

- **`vision_quality_42q_20260731`** — cited by **name** nowhere in handoffs/wiki/docs. Yet its
  numbers (`36/42 · 35/42 · 33/42 · 31/42`) are quoted at `handoffs/active/multimodal-pipeline.md:492`
  and `wiki/multimodal.md:557-563`, where they justify deprecating MiniCPM-o **and deleting ~22 GB
  of weights**. A live consequential decision resting on an artifact it does not name.
- **`vision_kv_q8_ab_20260802`** — **zero citations repo-wide.** Meanwhile
  `handoffs/active/multimodal-pipeline.md:309` (S-17) still says the KV-quantization quality test is
  *"in flight … do not add a fifth resident model before it reports"*. It reported on 2026-08-02.
- **`autokernel_controls_20260805`** (non-`_3pct` variant) — exists as data, cited nowhere. The
  `2.1310%` threshold from `autokernel_aa_20260804` was retired as live authority ✅ 2026-08-11
  (`handoffs/active/autokernel-research-loop.md:3394`); the live calibration is
  `autokernel_controls_3pct_20260805`.
- **`e5-gemma-nomtp-v9-20260812*`** — `docs/reviews/campaign-py-claim-integrity-adjudication-20260812.md:197-198`
  explicitly leaves these behind the human-only measurement trust boundary. No decision rests on
  them. No action here.

### C7 — Evidence-path split-brain (found incidentally, worth fixing)

The orchestrator cites the durable `data/vision_mmmu_cutover_20260731/results.json`, but
`handoffs/active/multimodal-pipeline.md:314`, `multimodal-pipeline.md:105` and `wiki/multimodal.md:588` still cite
**`/mnt/raid0/llm/tmp/vision_final_results.json`** — the exact scratch-path class `MEASUREMENT.md:169`
was written to outlaw (*"on 2026-08-02 the master registry was found citing 158 unique scratch
paths, including the MMMU-250 result that gated a live vision model cutover"*).

---

## 5. What this sweep cannot see

Stated plainly, because a retro-certification that overstates its own coverage is worse than none.

1. **Bare `llama-bench` output is invisible to every content-based method — measured, not asserted.**
   Of the **1,616** committed `.md`/`.json`/`.csv` paths touched by in-window commits under
   `data/` + `benchmarks/`, **1,048 carry no embedded date**, **938 carry no device/GPU string**,
   and **780 carry neither** (instrument: `grep -qE "2026-0[78]|202607[0-9]{2}|202608[0-9]{2}"` and
   `grep -qiE "rocm|mi210|gfx90a|ngl|amdgpu|kfd|hipblas|build-hip"` per file, 2026-08-12, epyc-root
   HEAD `acfc9d95`, epyc-inference-research `main`). Those 780 were caught **only** by the
   git-commit-window method.

   **The specific "bare `llama-bench`" fear is smaller than expected — corrected on measurement.**
   Of 83 in-window-added `llama-bench` outputs (75 research, 8 root), **zero** lack both axes: a
   `llama-bench` markdown table *structurally* emits `backend` and `ngl` columns, so it always
   carries a device signal. The residual is **date-only: 12 files**, and all 12 were caught anyway
   via their directory name. `llama-bench` output is therefore **not** the blind spot this audit
   feared.

   **The real blind spot is the decoupling of commit date from run date**, and it cuts both ways.
   The in-window `git log` surfaced dozens of directories whose campaign dates are
   `20260716`/`20260717` — bulk commits move old files *into* the window — so conversely, an
   in-window run committed after 2026-08-13, or never committed, is invisible to method 1 entirely,
   and the 780 undated/deviceless files are exactly the population that would hide it. Residual
   uncovered set: **60 research-repo files sit in a path with no date stamp anywhere** (chiefly
   `data/batched_decode/e5_manifests*/`), and 831 in-window additions were excluded by the
   extension filter altogether — including the `.time` sidecars beside every bench `.md`, and
   `.tsv`/`.manifest`/`.sha256` files that are genuine measurement outputs. Those were never
   classified.
2. **mtime is not evidence in this repo.** Both working paths are one shared clone; checkouts and
   merges rewrite mtimes wholesale. A `find -newermt 2026-07-31` sweep of `benchmarks/results/`
   returned only two directories, which is demonstrably an artifact of checkout order, not the truth.
   The git-window and embedded-date methods carried the enumeration; mtime was used only to bound
   the experimental build tree in §3.4.
3. **Uncommitted and scratch artifacts are out of reach.** Anything that lived only under
   `/mnt/raid0/llm/tmp/` and was never migrated is gone or unfindable — which is exactly the failure
   `MEASUREMENT.md:169` records (152 of 158 scratch paths still existed on 2026-08-02; **six did
   not**). Those six are permanently outside any retro-certification. This class has already
   destroyed at least one GPU result: `data/autokernel_aa_20260804/README.md:11-14` records that
   *"the 2026-07-04 async-prefetch win — the one real result this project ever produced — was
   written to `/mnt/raid0/llm/tmp/mi210-build/campaign/kernel_rnd_results.jsonl`, and that directory
   no longer exists."* That loss is **outside this window** (2026-07-04), so it changes no verdict
   above; it is cited as proof that the blind spot is real rather than theoretical.
4. **Absence of an env field cannot distinguish "not recorded" from "not applicable".** For a CPU
   run the missing ROCm fields are correct; the audit resolved this by reading each artifact's
   declared protocol, but a purely mechanical sweep could not.

4b. **Marker-based device attribution is unreliable in BOTH directions, so every call above was
   made by reading `server_argv` / a bench `backend` column / a server log — never by counting
   markers.** Two proofs from this window:
   `data/deepseek-v4-flash/iq3-dspark-quick-20260811T063729Z` scores *maximally* GPU by marker count
   (262 `ROCm`, 100 `rocm-smi`, 42 `VRAM`) yet ran with the GPU **explicitly masked off**
   (`ROCR_VISIBLE_DEVICES=-1 HIP_VISIBLE_DEVICES=-1`) — the markers are the tenancy guard sampling,
   not compute. Inversely, `judge_suite_headtohead_20260802` reads as non-GPU until
   `run_judge_suite.py:167`. And in `kernel-v9-candidate/.../v9-quality-run`, 272 `ngl` hits are the
   *ignored* flag: the server log's first line is `warning: no usable GPU found, --gpu-layers option
   will be ignored`. **A marker-count sweep would have misclassified at least three campaigns here.**
5. **The window is defined by process inheritance, not wall-clock.** Because long-lived containers
   keep the pre-fix path indefinitely (§1), a run *after* 2026-08-12 in an old container is equally
   exposed. This audit certifies a time range; it does not certify the future.
6. **This audit read artifacts, not runs.** Where an artifact records `ggml_linkage_verified: true`
   with no receipt, the audit can only report that the field is unfalsifiable — it cannot recover
   what actually happened.
7. **Coverage claim.** The enumeration is exhaustive over *committed, GPU-marked, in-window*
   artifacts in both repos' `data/` and `benchmarks/` trees. It is **not** exhaustive over all GPU
   work performed in the window.

---

## 6. What must be re-run before it gates anything

Ordered by consequence. Every re-run should be executed against the §3.2 template: explicit
single-entry `LD_LIBRARY_PATH=<hip-build>/bin`, a `--list-devices` capture, `guard_state.json`-style
git identity, and rocm snapshots before and after.

| Priority | Number | Where it gates | Why |
|---|---|---|---|
| **1** | `baseline_tps 30.87` · `contended_tps 19.81` · `vram_gib 36.7` (`gpu_coresidency_20260731`) | `model_registry.yaml:2478` etc. → `q_scorer` baselines, `routing_hints` throughput priors | Throughput + residency class · experimental kernel · no LD_LIB, no commit, no version · unfalsifiable linkage assertion · `n=3` against a −35.8% claim (P-BENCH-1 needs n≥5) · **artifact self-declares "no gate"** |
| **2** | `decode 112.20 vs 214.54 t/s median` and `vram_mb_total 21061` (`vision_mmmu_cutover_20260731`) | `model_registry.yaml:2231-2238` — vision role VRAM budget and speed characterisation | Throughput + residency class · experimental kernel · no banked LD_LIB. **The accuracy half of the same artifact does not need re-running — see §4/C1.** |
| **3** | `36/42 · 35/42 · 33/42 · 31/42` (`vision_quality_42q_20260731`) | `multimodal-pipeline.md:492`, `wiki/multimodal.md:557-563` — MiniCPM-o deprecation, ~22 GB weights deleted | Accuracy class, so **not** a linkage re-run. Re-run only if the deletion is ever revisited; the real defect is that the artifact carries **no `_meta` at all** and is cited by numbers rather than by path |
| — | **Not to be re-run** | | v9 GPU certification (§3.2) and the DFlash P-GPU-1 cert run (§3.2a) are certifiable · `mi210-*` substrate receipts are non-llama.cpp (§4/C3) · the two VOID runs contain nothing to re-run · `judge_suite`, `vision_kv_q8_ab` accuracy numbers are device-invariant · the `artifacts/gpu-aux-baselines/` set is uncited, so nothing gates on it today |

**Zero-inference work that should precede any re-run.** Fix
`pgpu1_artifact_completeness_audit.py` per §7 item 8, then run it across the full in-window set and
bank the verdicts. It is read-only, costs no GPU time, and converts this prose audit into a
reproducible gate. Doing it in the other order would stamp `retro_cert_candidate` on artifacts that
fail field 3.

**A cheaper alternative to re-running #1 and #2**, offered because both are contended-throughput
numbers whose *sign* nobody disputes: re-measure only the un-contended `baseline_tps` for
`qwen36_27b_mtp_q8` on production v9 under the §3.2 template, and demote the contention deltas to
explicitly-labelled observations in the registry rather than attested throughput. That closes the
gating exposure at a fraction of the cost. **Operator's call — this audit does not make it.**

---

## 7. Proposed handoff / registry edits — NOT APPLIED

Index rows and registry entries require operator approval; nothing below was edited. Listed so the
approval can be a single yes/no.

1. **`handoffs/active/multimodal-pipeline.md:308`** — S-16 (*"promote Qwen3-VL-30B-A3B Q4_K_M to the
   vision role and retire Qwen2.5-VL-7B"*) is still `- [ ]` for work that **shipped** in
   epyc-orchestrator `a517793c` on 2026-08-01 and is live in `model_registry.yaml`,
   `model_descriptors.yaml` and `derived/stack_priors.yaml`. Propose: flip to `- [x] ✅ 2026-08-01`
   with the commit as evidence.
2. **`handoffs/active/multimodal-pipeline.md:492`** — states *"`worker_vision` stays on
   Qwen2.5-VL"*. This **contradicts the live registry**. Propose: append a dated correction pointing
   at `a517793c` and the MMMU result that superseded the 42q ranking (the file's own V-1 at `:326`
   already records the supersession).
3. **`handoffs/active/multimodal-pipeline.md:309`** — S-17 says the KV-quantization quality test is
   *"in flight"*; `data/vision_kv_q8_ab_20260802/` reported on 2026-08-02. Propose: close the row
   against that path.
4. **`handoffs/active/multimodal-pipeline.md:314`, `:105`, and `wiki/multimodal.md:588`** — repoint from
   `/mnt/raid0/llm/tmp/vision_final_results.json` to
   `data/vision_mmmu_cutover_20260731/results.json`. This is a `check_evidence_durability.py`
   violation as written.
5. **`orchestration/model_registry.yaml`** (epyc-orchestrator) — the `attest:` string at `:2478` and
   the throughput block it backs should be relabelled **observation** pending item 1 of §6, since
   the cited artifact self-declares *"no gate"*. **Registry edit — operator only.**
6. **`data/vision_kv_q8_ab_20260802/SHA256SUMS`** — contains a self-referential vacuous row
   `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  SHA256SUMS`, which is the
   sha256 of the **empty string** and can never verify. The file also mixes bare basenames with one
   repo-relative path, so `sha256sum -c` cannot succeed from any single cwd. Propose: regenerate.
7. **P-GPU-1 field-3 amendment** (already queued for ratification, plan Phase 5) — §3.2 supplies the
   concrete argument: the one compliant run in the window would **fail** a summary-only verifier
   because its evidence lives in `commands.sh` / `guard_state.json`. The amendment should name a
   verifier-produced **linkage receipt at a fixed path within the run directory**, and should
   explicitly retire the unfalsifiable `ggml_linkage_verified: true` boolean shape. §3.2b supplies a
   working precedent already in this repo — `autokernel_controls_*`'s `linkage.copy.txt` +
   `anchor_binary_copy/` — which the amendment can adopt rather than design from scratch, provided
   it adds a loaded-backend capture (`--list-devices`) since `ldd` cannot see a `dlopen`.

8. **`epyc-inference-research/scripts/benchmark/pgpu1_artifact_completeness_audit.py:73-84,243-246`**
   — the `binary_model_identity` rule ORs six patterns and marks the field `present` on any single
   hit, so an artifact banking **no `LD_LIBRARY_PATH`** passes field 3 (demonstrated in §3.2a-bis).
   Propose: split `ld_library_path` (and a backend-list pattern) into **their own required rules**
   so they must each match independently; restrict the scan for those rules to result/receipt files
   rather than the whole directory, so harness source cannot satisfy them; and **remove
   `llama\.cpp-experimental` from the positive pattern set** — it belongs in `near_patterns`, where
   the `production_named_kernel_identity` rule already correctly places it. Add a mutation test that
   garbles the banked `LD_LIBRARY_PATH` in a fixture and **asserts the audit turns `incomplete`**
   (`test_pgpu1_artifact_completeness_audit.py` exists alongside it). This is a code fix, not an
   index or registry edit — it needs review, not operator ratification, but it is listed here
   because it changes what a governance gate accepts.

---

## 8. Bottom line

Of the eleven in-window GPU-attributed artifact groups audited in detail, **two are certifiable** —
the v9 promotion GPU certification (§3.2) and the DFlash P-GPU-1 cert run (§3.2a), which together
carry the largest stakes in the window — **five are observation-grade**, two are out of P-GPU-1's
claim class, and two are void. A further set of in-window GPU artifacts in
`/workspace/artifacts/gpu-aux-baselines/` and the `kernel-v9-candidate` plan siblings was
enumerated but not field-audited, because no live decision cites them.

**Nothing in this audit shows any measured number to be wrong.** The three vision harnesses
defeated the linkage hazard by prepending their HIP build directory; they simply did not bank the
proof. What the audit establishes is narrower and still worth acting on: **three live production
citations rest on artifacts that cannot be certified**, and one of them
(`gpu_coresidency_20260731`) is a throughput-and-residency claim on an experimental kernel that
**explicitly disclaims being a gate** while a registry `attest:` string points at it.

**Answer to the operator's question:** the vision-cutover **accuracy** numbers do **not** need to be
re-run — accuracy is invariant to which device executed, and the hazard's precondition did not hold.
The vision-cutover **throughput and VRAM** numbers, and the `architect_general` co-residency
throughput priors, **do** — before they continue to gate.

**The cheapest durable win in this audit is not a re-run at all.** A P-GPU-1 completeness verifier
already exists, already emits `retro_cert_candidate` / `rerun_required`, and already ran clean on
the two certifiable artifacts. It was never pointed at the window, and its field-3 check is
currently vacuous. Fix it (§7 item 8), run it across the set, and the next retro-certification is a
command instead of a document.

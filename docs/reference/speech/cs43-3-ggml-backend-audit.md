# CS-43.3 audit: `GGML_BACKEND` and `QT_ABI_VERSION` consumers (upstream-based qwentts candidate)

**Status**: audit table, read-only; filed with the speech-kernel promotion package ([`docs/reference/kernel-manifests/speech-v2-manifest.md`](../kernel-manifests/speech-v2-manifest.md)). **No launcher, test or script is edited** while `production-speech-v1` serves: for the frozen binary the env var is correct. Task: CS-43.3 in [`handoffs/active/conversation-stack.md`](../../../handoffs/active/conversation-stack.md). Run 2026-10-22 against `origin/main` of each repo (after `git fetch`): epyc-orchestrator `109bc37b`, epyc-inference-research `b3fe1448a`, epyc-root `e95107499`.

## 1. What the frozen binary does, and what upstream changed

| Fact | Evidence |
|---|---|
| Frozen `production-speech-v1` qwentts (`2c1b518`) reads the env var: `std::getenv("GGML_BACKEND")`, if set `ggml_backend_init_by_name(...)` (error and empty backend pair if not found), else `ggml_backend_init_best()` | `/mnt/raid0/llm/qwentts.cpp` `src/backend.h:105-115` |
| Frozen library ABI is `QT_ABI_VERSION 4` (accepts the closed range `[QT_ABI_MIN_VERSION, 4]`) | `src/qwen.h:62`, checks at `src/qwen.cpp:332-336, 564` |
| It is the only `GGML_BACKEND` reader in that tree (tests set it in `tests/debug-*-cossim.sh`). The whisper tree (`/mnt/raid0/llm/whisper.cpp` @ `b3073792`) has **no** `GGML_BACKEND` or `QT_ABI_VERSION` reference in `*.c *.cpp *.h`, so no whisper launcher is affected | `git grep -nw` on `HEAD` of both trees |
| Upstream commit `01b6127c2aab` ("cli: select the GGML device with --device", 2026-10-12) removes the env var in `src/backend.h`, adds `--device <name>` to `tts-server`, `qwen-tts`, `qwen-codec`, and adds a `device` field to the init params, behind an ABI bump | upstream checkout `/mnt/raid0/llm/tmp/dive-qwentts-upstream/repo` (HEAD `5916bf7`), `git show --stat 01b6127` |
| **Correction to the task text**: the bump in `01b6127` is **5 to 6** (`QT_ABI_VERSION 6`, `device` "Since ABI 6"); upstream HEAD is 6 with `QT_ABI_MIN_VERSION 5`. The frozen tree is at 4, so an upstream-based build jumps 4 to 6 | `git show 01b6127 -- src/qwen.h` |
| Behaviour of an upstream binary with no `--device`: `ggml_backend_init_best()` (best available, "default: best available"). The upstream commit message states no environment variable configures the binaries any more. A stale `GGML_BACKEND=CPU` is **silently ignored** | `tools/tts-server.cpp` usage text; `src/backend.h` |
| Replacement for `GGML_BACKEND: "CPU"` is `--device CPU` on the argv (device names as `ggml_backend_dev_name`: CPU, CUDA0, Vulkan0, MTL0; for this ROCm build the GPU name is whatever `tts-server --device nonsense` prints under "Available:", unverified here) | upstream `backend_check_device` |

**Risk statement**: every hit below also sets `HIP_VISIBLE_DEVICES=-1`, which hides the GPU, so an upstream binary would most likely still land on CPU. The failure is not necessarily a GPU run; it is that the env var no longer expresses (or guards) the intent, and an attestation that checks the env var proves nothing about the device. A launcher that drops `HIP_VISIBLE_DEVICES` later would go to the GPU silently. Residency still has to be proven by `verify_ggml_linkage.sh` and a CPU-thread log line, not by the env var.

## 2. Hit table (`origin/main`, exact-word `GGML_BACKEND`; `GGML_BACKEND_DL`, `GGML_BACKEND_BUFFER_*` etc. are unrelated ggml symbols and excluded)

"Live" = read by a running service or a test gating one. Consumer binary is the qwentts `tts-server` / `qwen-tts` unless noted.

| # | Repo @ sha | path:line | Context | Live? | `--device` replacement | Proposed fix (NOT applied) |
|---|---|---|---|---|---|---|
| 1 | epyc-orchestrator `109bc37b` | `orchestration/launch_manifest.yaml:938` | `aux_services.tts` env `GGML_BACKEND: "CPU"` for :9002 (comment at `:917`); consumer `tts-server` | **LIVE** (v1 binary needs it) | add `"--device", "CPU"` to argv (`:930-936`) | On candidate promotion: add `--device CPU` to argv, delete the env key, keep `HIP_VISIBLE_DEVICES`/`SHIM_NPROCS`/`LD_PRELOAD`; update comment `:917` |
| 2 | epyc-orchestrator `109bc37b` | `tests/unit/test_aux_service_env.py:272` | `assert tts.env.get("GGML_BACKEND") == "CPU"` | live test of #1 | assert `--device CPU` in argv instead | Change together with #1 |
| 3 | epyc-orchestrator `109bc37b` | `tests/unit/test_env_attestation.py:88-91` | uses `GGML_BACKEND` as the example env key in an attestation mismatch test (`CPU` declared, `GPU` observed) | test fixture only | none; the fixture is generic | Switch the key to a still-valid one (e.g. `HIP_VISIBLE_DEVICES`) or leave; no behaviour tie to the binary |
| 4 | epyc-orchestrator `109bc37b` | `scripts/server/stack_env.py:258` (comment, no literal match) | "Ambient GGML_* must not reach a different kernel"; `strip_ambient_ggml(..., declared_env)` keeps declared GGML keys | live code, no change needed | none | None. It correctly keeps a declared `GGML_BACKEND` today and will pass through harmlessly once removed |
| 5 | epyc-inference-research `b3fe1448a` | `scripts/voice/turn_taking/tt_render_pipeline.py:107` | CS-45 render env `tts_env()`: `HIP_VISIBLE_DEVICES=-1, GGML_BACKEND=CPU, SHIM_NPROCS=2, LD_PRELOAD=SHIM`, spawns qwentts `tts-server` | live (CS-45 render) | `--device CPU` in the spawned argv (find the `tts-server` Popen in the same file) | Add to argv when rendering with a candidate binary; leave env until then |
| 6 | epyc-inference-research `b3fe1448a` | `orchestration/model_registry.yaml:2398` | comment, "Same frozen production-speech-v1 binary with GGML_BACKEND=CPU + HIP_VISIBLE_DEVICES=-1" | comment | none | Reword on promotion |
| 7 | epyc-inference-research `b3fe1448a` | `data/turn-taking-cs45-v1/pins.json:81` | pinned-instrument "use" text mentions `GGML_BACKEND=CPU` for a read-only CLI | evidence file, hashed | none | **Do not edit** (hash-pinned corpus evidence); note in the CS-45 era record if a candidate render is ever added |
| 8 | epyc-inference-research `b3fe1448a` | `artifacts/speech_cpu_realtime_20260924/README.md:39,161,336`; `speech_cpu_bench.py:7,113`; `raw/pids_started.txt` (argv logs) | 2026-09-24 CPU speech measurement recipe and its bench driver | historical, but `speech_cpu_bench.py` is re-runnable | `--device CPU` | Leave as the record of the v1 measurement; if re-run against a candidate, pass `--device CPU` and drop the env var |
| 9 | epyc-root `e95107499` | `artifacts/qwentts_threadpool_20261020/scripts/{corr_qwentts.py:42,timing.py:181,timing_tune.py:185}`, `artifacts/qwentts_threads_20261020/{sweep.sh:18,sweep2.sh:42}` | qwentts threadpool/threads experiment drivers set `GGML_BACKEND=CPU` with `LD_LIBRARY_PATH=$bindir` | historical, re-runnable (SP2 / CS-43.2 A/B reuse them) | `--device CPU` | The CS-43.2 CPU A/B against an upstream binary must add `--device CPU` to its argv or the env var is ignored |
| 10 | epyc-root `e95107499` | `artifacts/speech-queue-20261021/g1/g1_cascade_language.py:192,218` | G1 cascade harness env for qwentts | historical, re-runnable | `--device CPU` | Same as #9 |
| 11 | epyc-root `e95107499` | `artifacts/operator/stack-change-kvu-20260924/revision-3/{PACKAGE.md:24,expected-argv.txt:7,patches/*.patch}` | the ratified stack-change package that introduced #1/#5/#6 | signed record | none | **Do not edit** |
| 12 | epyc-root `e95107499` | `docs/reference/speech/cpu-speech-contention-20260924.md:31`; `dashboard/static/amd-ai-lab/app.js:681` | prose/label `GGML_BACKEND=CPU` | documentation / UI label | none | Reword when the production kernel changes (the dashboard label is a display string, not a launcher) |
| 13 | epyc-root `e95107499` | `artifacts/ni05/**` (captured copies, about 35 lines), `.research-session.json`, `research/intake_index.yaml`, `handoffs/active/conversation-stack.md:701` | captured copies of #1/#2/#3 (`read-*.bin`), research-session records, the intake record of the upstream change, and this task | derived / records | none | None |

Notes: no `GGML_BACKEND` literal exists in epyc-orchestrator `src/`; the only production consumer is the manifest env (#1). `whisper.cpp` launchers are unaffected (no reader of the variable). A repo-wide `git grep -nw GGML_BACKEND` in epyc-root also hits `.research-session.json` and `research/intake_index.yaml` (records only).

## 3. `QT_ABI_VERSION` / library consumers

`git grep -nw "QT_ABI_VERSION|QT_ABI_MIN_VERSION|libqwentts|qt_init_params|abi_version"` on `origin/main` of all three repos finds **no consumer outside the qwentts tree itself** (only epyc-root `research/intake_index.yaml` and `.research-session.json` mention the symbols as text). No Python, shell or YAML file in epyc-orchestrator or epyc-inference-research links or loads the qwentts shared library; `tts-server` is launched as an executable built from the same tree, so there is no pinned `QT_ABI_VERSION` below 5 (or at all) anywhere to break. In the frozen tree, `QT_ABI_VERSION` appears only inside `src/qwen.*`, `tests/abi-c.c` and `docs/ARCHITECTURE.md:506`. Residual caveat: the CMake target `qwen` in the tree is a SHARED library (`CMakeLists.txt:147`); if an out-of-tree consumer outside these three repos exists, this grep cannot see it. **Result: PASS, no ABI consumer pinned below 5.** Inside the tree, `tests/abi-c.c` must be run by the candidate build (accepts `[5,6]`, rejects 4).

## 4. Re-run command (run when an upstream-based candidate is packaged)

```bash
for r in /workspace /workspace/repos/epyc-orchestrator /workspace/repos/epyc-inference-research; do
  git -C "$r" fetch -q origin
  git -C "$r" grep -nw "GGML_BACKEND\|QT_ABI_VERSION\|QT_ABI_MIN_VERSION" origin/main -- . ':!artifacts/ni05'
done
# the frozen reader, and the candidate's reader (expect: no getenv GGML_BACKEND on the candidate)
git -C /mnt/raid0/llm/qwentts.cpp grep -n "getenv\|QT_ABI_VERSION" HEAD -- '*.c' '*.cpp' '*.h'
git -C /mnt/raid0/llm/tmp/dive-qwentts-upstream/repo show --stat 01b6127
```

Compare every hit with table section 2 (a new hit in a launcher is a finding). Also `strings <candidate tts-server> | grep -c GGML_BACKEND` must be 0 and `tts-server --help` must list `--device`, per the build-artifact rule in CLAUDE.md (prove the binary, not the source).

## 5. Proposed fixes (NOT applied; apply only when an upstream-based candidate is packaged, through the speech-kernel promotion)

1. `epyc-orchestrator` `orchestration/launch_manifest.yaml`: add `"--device", "CPU"` to the :9002 argv, remove `GGML_BACKEND`, update the `:917` comment; update `tests/unit/test_aux_service_env.py:272` to assert the argv flag.
2. `epyc-inference-research` `scripts/voice/turn_taking/tt_render_pipeline.py:107` and its spawn argv: same change; reword `orchestration/model_registry.yaml:2398`.
3. Re-runnable drivers (rows 8-10): pass `--device CPU` when pointed at a candidate binary; keep v1 behaviour for v1 re-runs (the env var is harmless to an upstream binary, and required by the frozen one, so the safest transitional launcher passes both only for a single experiment, never in the production manifest).
4. Attestation: after the launcher change, the env-attestation check cannot prove the device from env; require the serving proof (`verify_ggml_linkage.sh`, CPU-thread log line `CPU threads: 16`, zero VRAM sampled during synthesis).
5. Promotion checklist additions: candidate binary shows `--device` in `--help`, `strings` shows no `GGML_BACKEND`, `tests/abi-c.c` passes at ABI 6, and the nprocs shim still applies (the thread-count flag is a separate upstream change not audited here).

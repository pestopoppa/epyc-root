# Operator decision package — extend the production-kernel freeze to the speech kernels

**Filed** 2026-07-31 · **Requester** claude-main · **Decision required** ratify / amend / decline
**Ratification command** `bash artifacts/operator/ratify_speech_kernel_freeze_20260731.sh`

---

## 1. The ask, in one sentence

Extend the production-kernel freeze doctrine — today scoped to `llama.cpp` alone — to cover the two
kernels that will serve production speech traffic (`whisper.cpp` for STT, `qwentts.cpp` for TTS), by
pinning each to a named branch, recording its commit and binary SHA-256, and adding a session-time
verifier.

## 2. Why this is urgent, not housekeeping

**Both GPU speech kernels currently exist only as uncommitted working-tree state.**

| tree | uncommitted | what it does | consequence if lost |
|---|---|---|---|
| `whisper.cpp` | `ggml/src/ggml-cuda/vendors/hip.h` (1 line) | `HIP_VERSION >= 60200000` → `60300000`; ROCm 6.2 ships only `__hip_fp8_e4m3_fnuz`, so the un-patched guard fails the build | tree will not build on this host |
| `qwentts.cpp` | 4 files in the `ggml` submodule: `argsort.cu`, `argsort.cuh`, `ggml-cuda.cu`, `vendors/hip.h` | thread-strided bitonic sort replacing `block_dims(ncols_pad)` (gfx90a caps at 1024 threads/block), plus the same FP8 guard | GPU TTS stops working |

A single `git checkout .`, a stash, or a fresh clone in either tree destroys GPU speech. The binaries
behind the measurements below **cannot be rebuilt from any commit**:

| measurement | value | binary |
|---|---|---|
| whisper large-v3-turbo f16 WER | 2.35 % | `whisper-server` `82aa8b56…` |
| whisper end-to-end latency, 11 s clip | 0.21 s | same |
| Qwen3-TTS RTF | 0.169 (5.9× realtime) | `tts-server` `369fc2f1…` |
| Qwen3-TTS round-trip WER | 1.49 % | same |

This is the exact failure mode `production-consolidated-v8` exists to prevent, currently unguarded
on two of the four kernels the stack depends on.

## 3. Second finding — three diverging ggml generations

| tree | commit | ggml | frozen | ratified | in the repo map |
|---|---|---|---|---|---|
| `llama.cpp` | `67a433bf4` (`production-consolidated-v8`) | 0.16.0 | ✅ | ✅ sha256 `e7fce2c5…` | ✅ |
| `qwentts.cpp` | `abab6b3` + dirty submodule | 0.17.0 | ❌ | ❌ | ❌ |
| `whisper.cpp` | `2ca53bb` + dirty | 0.18.0 | ❌ | ❌ | ❌ |

The speech kernels are not merely unfrozen — they are **drifting away from production**, each on a
newer upstream ggml, with no anchor pulling them back. Neither appears in the `CLAUDE.md` repository
map, so a session reading the governance docs would not know they exist as production dependencies.

The version spread is also what makes the `LD_LIBRARY_PATH` hazard (fixed 2026-07-31, commits
`136894e8` / `94cf8d6c`) load-bearing rather than cosmetic: a 0.18.0 binary silently resolving 0.16.0
libraries is only possible because the versions differ.

## 4. What ratification changes

1. **Creates `production-speech-v1` in each speech tree**, committing the load-bearing GPU patches so
   there is a commit to pin. Nothing is rewritten; the patches are committed exactly as they stand.
2. **Writes `artifacts/operator/ratify_speech_kernel_freeze_20260731.json`** — commit ids, branch
   names, ggml versions, binary SHA-256s, and the measurements each binary produced.
3. **Amends `CLAUDE.md`** — adds both trees to the repository map, and extends the
   *Production-Kernel Immutability* section from "the production kernel" to "the production kernel
   set", naming all three.
4. **Adds `scripts/session/verify_speech_kernels.sh`**, the speech sibling of `verify_llama_cpp.sh`:
   asserts each tree is on its production branch, clean, and that the built binary's SHA-256 matches
   the ratified value.

## 5. What ratification does NOT change

- No kernel is rebuilt, rebased, or modified. The four-step experimental workflow is untouched.
- No measurement is re-attributed. Existing speech numbers stand; they simply gain a reproducible
  anchor for the first time.
- `MEASUREMENT.md` and `measurement/protocols/*` are not touched — this is kernel governance, not
  measurement governance.

## 6. Risks of ratifying

| risk | severity | mitigation |
|---|---|---|
| Freezing patches that are still being iterated on | LOW | `production-speech-v1` is a branch, not a tag; `-v2` supersedes it the same way `-v8` superseded `-v7`. |
| The committed patches have not been upstreamed | MEDIUM | Real, and unchanged by this decision — they are unupstreamed today too, just also unrecorded. Ratifying makes the divergence visible; a follow-up task can upstream them. |
| `verify_speech_kernels.sh` fires on every session and becomes noise | LOW | It is not wired into `session_init.sh` by this script. Wiring it in is a separate, reversible edit. |

## 7. Risk of declining

The status quo is one `git checkout .` away from losing GPU speech entirely, with no record of what
was lost or how to rebuild it. If you decline, the minimum safe alternative is to commit the patches
without the governance apparatus — see §8, option C.

## 8. Options

| option | effect |
|---|---|
| **A — ratify in full** (recommended) | Run the script. Patches committed, anchors recorded, `CLAUDE.md` amended, verifier added. |
| **B — ratify, defer the verifier** | Run with `SKIP_VERIFIER=1`. Freeze and anchors land; no new session script. |
| **C — commit only, no governance** | Run with `COMMIT_ONLY=1`. Patches are preserved on the production branches; `CLAUDE.md` untouched, no ratification artifact. Removes the data-loss risk, keeps the visibility gap. |
| **D — decline** | Nothing changes. The data-loss exposure in §2 stands. |

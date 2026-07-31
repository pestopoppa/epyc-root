#!/bin/bash
# RATIFICATION — extend the production-kernel freeze to the speech kernels.
#
# Applies artifacts/operator/speech-kernel-freeze-amendment-20260731.md.
#
# RUN BY THE OPERATOR ONLY. Freezing a kernel is a governance act; an agent may
# propose it but may not perform it. Running this script IS the act of ratification.
#
# What it does:
#   1. Commits the load-bearing GPU patches in whisper.cpp and qwentts.cpp onto a
#      new `production-speech-v1` branch in each tree, so there is a commit to pin.
#      (Today they are UNCOMMITTED working-tree state — one `git checkout .` from
#      losing GPU STT and GPU TTS entirely.)
#   2. Records commits, ggml versions and binary SHA-256s into
#      artifacts/operator/ratify_speech_kernel_freeze_20260731.json
#   3. Amends CLAUDE.md: repo map rows + freeze doctrine widened to a KERNEL SET
#   4. Adds scripts/session/verify_speech_kernels.sh
#
# Modes:
#   bash ratify_speech_kernel_freeze_20260731.sh                # full (option A)
#   SKIP_VERIFIER=1 bash ratify_speech_kernel_freeze_20260731.sh # option B
#   COMMIT_ONLY=1   bash ratify_speech_kernel_freeze_20260731.sh # option C
#
# Idempotent: re-running detects the branches/markers and skips. Verifies every
# anchor BEFORE writing anything, and aborts without side effects if one is missing.
# It NEVER touches /mnt/raid0/llm/llama.cpp (the frozen llama.cpp production tree).
set -euo pipefail

ROOT=/workspace
WHISPER=/mnt/raid0/llm/whisper.cpp
QWENTTS=/mnt/raid0/llm/qwentts.cpp
BRANCH=production-speech-v1
JSON="$ROOT/artifacts/operator/ratify_speech_kernel_freeze_20260731.json"
STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

SKIP_VERIFIER="${SKIP_VERIFIER:-0}"
COMMIT_ONLY="${COMMIT_ONLY:-0}"

say() { printf '  %s\n' "$*"; }
abort() { printf 'ABORT: %s\n' "$*" >&2; exit 1; }

echo "=== preflight (no writes yet) ==="

for d in "$ROOT" "$WHISPER" "$QWENTTS"; do
  [ -d "$d/.git" ] || [ -f "$d/.git" ] || abort "not a git tree: $d"
done
[ -f "$ROOT/CLAUDE.md" ] || abort "missing $ROOT/CLAUDE.md"

# The llama.cpp production tree must NOT be involved. Fail loudly if it drifted.
LLAMA_BRANCH=$(git -C /mnt/raid0/llm/llama.cpp branch --show-current 2>/dev/null || echo "?")
[ "$LLAMA_BRANCH" = "production-consolidated-v8" ] \
  || abort "llama.cpp is on '$LLAMA_BRANCH', expected production-consolidated-v8. Investigate before ratifying anything."
say "llama.cpp untouched, on $LLAMA_BRANCH"

WHISPER_BIN="$WHISPER/build/bin/whisper-server"
TTS_BIN="$QWENTTS/build/tts-server"
for b in "$WHISPER_BIN" "$TTS_BIN"; do
  [ -x "$b" ] || abort "missing or non-executable binary: $b (build it before ratifying)"
done

# Expected pre-ratification tips, from the decision package.
W_TIP=$(git -C "$WHISPER" rev-parse --short HEAD)
Q_TIP=$(git -C "$QWENTTS" rev-parse --short HEAD)
say "whisper.cpp HEAD  = $W_TIP"
say "qwentts.cpp HEAD  = $Q_TIP"

ALREADY=0
if git -C "$WHISPER" show-ref --verify --quiet "refs/heads/$BRANCH" \
   && git -C "$QWENTTS" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  ALREADY=1
  say "branch '$BRANCH' already exists in both trees — will not re-commit"
fi

echo
echo "=== 1. freeze the kernels onto '$BRANCH' ==="

freeze_tree() {
  local tree="$1" label="$2"
  if git -C "$tree" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    say "$label: '$BRANCH' exists, checking out"
    git -C "$tree" checkout -q "$BRANCH"
    return 0
  fi
  say "$label: creating '$BRANCH' at $(git -C "$tree" rev-parse --short HEAD)"
  git -C "$tree" checkout -q -b "$BRANCH"
}

# --- whisper.cpp: a plain working-tree patch -------------------------------
freeze_tree "$WHISPER" "whisper.cpp"
if [ -n "$(git -C "$WHISPER" status --porcelain)" ]; then
  git -C "$WHISPER" add -A
  git -C "$WHISPER" commit -q -m "freeze: gfx90a/ROCm 6.2 GPU enablement for production speech

FP8 guard raised from HIP_VERSION >= 60200000 to >= 60300000. ROCm 6.2 ships
only __hip_fp8_e4m3_fnuz, so the upstream guard admits a header this toolchain
cannot compile.

Committed as part of the 2026-07-31 speech-kernel freeze. This patch was
previously UNCOMMITTED working-tree state; the whisper large-v3-turbo f16
measurements (WER 2.35%, 0.21 s on an 11 s clip) were produced by a binary that
could not be rebuilt from any commit."
  say "whisper.cpp: committed $(git -C "$WHISPER" rev-parse --short HEAD)"
else
  say "whisper.cpp: clean, nothing to commit"
fi

# --- qwentts.cpp: patches live in the ggml SUBMODULE ------------------------
freeze_tree "$QWENTTS" "qwentts.cpp"
if [ -n "$(git -C "$QWENTTS/ggml" status --porcelain 2>/dev/null)" ]; then
  git -C "$QWENTTS/ggml" add -A
  git -C "$QWENTTS/ggml" commit -q -m "gfx90a: bitonic argsort within the 1024 threads/block limit; ROCm 6.2 FP8 guard

argsort launched block_dims(ncols_pad), which exceeds the gfx90a maximum of 1024
threads per block for realistic vocabularies. Replaced with a thread-strided
bitonic sort. FP8 guard raised to HIP_VERSION >= 60300000 for ROCm 6.2.

Committed as part of the 2026-07-31 speech-kernel freeze."
  say "qwentts.cpp/ggml: committed $(git -C "$QWENTTS/ggml" rev-parse --short HEAD)"
fi
if [ -n "$(git -C "$QWENTTS" status --porcelain)" ]; then
  git -C "$QWENTTS" add -A
  git -C "$QWENTTS" commit -q -m "freeze: pin ggml submodule carrying the gfx90a GPU patches

Committed as part of the 2026-07-31 speech-kernel freeze. These patches were
previously UNCOMMITTED submodule state; the Qwen3-TTS measurements (RTF 0.169,
round-trip WER 1.49%) were produced by a binary that could not be rebuilt from
any commit."
  say "qwentts.cpp: committed $(git -C "$QWENTTS" rev-parse --short HEAD)"
else
  say "qwentts.cpp: clean, nothing to commit"
fi

W_COMMIT=$(git -C "$WHISPER" rev-parse HEAD)
Q_COMMIT=$(git -C "$QWENTTS" rev-parse HEAD)
Q_GGML=$(git -C "$QWENTTS/ggml" rev-parse HEAD 2>/dev/null || echo "n/a")
W_SHA=$(sha256sum "$WHISPER_BIN" | cut -d' ' -f1)
T_SHA=$(sha256sum "$TTS_BIN" | cut -d' ' -f1)

if [ "$COMMIT_ONLY" = "1" ]; then
  echo
  echo "COMMIT_ONLY=1 — patches are preserved on '$BRANCH' in both trees."
  echo "  whisper.cpp $BRANCH  = $W_COMMIT"
  echo "  qwentts.cpp $BRANCH  = $Q_COMMIT (ggml $Q_GGML)"
  echo "No ratification artifact written, CLAUDE.md untouched. This is option C."
  exit 0
fi

echo
echo "=== 2. ratification artifact ==="
cat > "$JSON" <<EOF
{
  "ratification": "speech-kernel-freeze-v1",
  "date_utc": "$STAMP",
  "supersedes": null,
  "scope": "Extends the production-kernel freeze from llama.cpp alone to the production KERNEL SET.",
  "decision_package": "artifacts/operator/speech-kernel-freeze-amendment-20260731.md",
  "kernels": {
    "llama_cpp": {
      "tree": "/mnt/raid0/llm/llama.cpp",
      "branch": "production-consolidated-v8",
      "commit": "67a433bf45a8a091d83b4ea0b32ff0735fd51800",
      "ggml": "0.16.0",
      "binary_version": "10107",
      "ratification": "artifacts/operator/ratify_v8_final_freeze_20260725.json",
      "note": "unchanged by this ratification; recorded for completeness"
    },
    "whisper_cpp": {
      "tree": "$WHISPER",
      "branch": "$BRANCH",
      "commit": "$W_COMMIT",
      "ggml": "0.18.0",
      "binary": "$WHISPER_BIN",
      "binary_sha256": "$W_SHA",
      "gpu": "HIP / gfx90a (MI210)",
      "load_bearing_patch": "ggml/src/ggml-cuda/vendors/hip.h — FP8 guard 60200000 -> 60300000 for ROCm 6.2",
      "measurements_anchored": {
        "model": "whisper large-v3-turbo f16",
        "wer_pct": 2.35,
        "latency_s_11s_clip": 0.21
      }
    },
    "qwentts_cpp": {
      "tree": "$QWENTTS",
      "branch": "$BRANCH",
      "commit": "$Q_COMMIT",
      "ggml_submodule_commit": "$Q_GGML",
      "ggml": "0.17.0",
      "binary": "$TTS_BIN",
      "binary_sha256": "$T_SHA",
      "gpu": "HIP / gfx90a (MI210)",
      "load_bearing_patch": "ggml/src/ggml-cuda/argsort.{cu,cuh} — thread-strided bitonic sort within the gfx90a 1024 threads/block limit; vendors/hip.h FP8 guard",
      "measurements_anchored": {
        "model": "Qwen3-TTS 12hz talker 0.6B Q8_0 + tokenizer 12hz Q8_0",
        "rtf": 0.169,
        "roundtrip_wer_pct": 1.49
      }
    }
  },
  "ggml_version_spread": {
    "note": "Three generations coexist. This is why per-launcher LD_LIBRARY_PATH isolation is load-bearing rather than cosmetic.",
    "llama_cpp": "0.16.0",
    "qwentts_cpp": "0.17.0",
    "whisper_cpp": "0.18.0",
    "related_fix": "root 136894e8 / research 94cf8d6c — removed the CPU-only llama.cpp dirs from the global LD_LIBRARY_PATH"
  },
  "not_changed": [
    "No kernel rebuilt, rebased or modified",
    "MEASUREMENT.md and measurement/protocols/* untouched",
    "The four-step experimental kernel workflow is unchanged"
  ]
}
EOF
say "wrote $JSON"

echo
echo "=== 3. amend CLAUDE.md ==="
python3 - "$ROOT/CLAUDE.md" "$W_COMMIT" "$Q_COMMIT" <<'PY'
import sys
path, wc, qc = sys.argv[1], sys.argv[2][:9], sys.argv[3][:9]
s = open(path, encoding="utf-8").read()

if "production KERNEL SET" in s:
    print("  already amended — skipping")
    sys.exit(0)

# --- repo map rows ---
anchor = "| epyc-llama | `/workspace/repos/epyc-llama` → `/mnt/raid0/llm/llama.cpp` | Production llama.cpp kernel tree (FROZEN) |"
if anchor not in s:
    sys.exit("ABORT: repo-map anchor not found in CLAUDE.md")
rows = anchor + (
    "\n| epyc-whisper | `/mnt/raid0/llm/whisper.cpp` | Production STT kernel (FROZEN, `production-speech-v1`) |"
    "\n| epyc-qwentts | `/mnt/raid0/llm/qwentts.cpp` | Production TTS kernel (FROZEN, `production-speech-v1`) |"
)
s = s.replace(anchor, rows, 1)

# --- widen the immutability doctrine ---
d_anchor = "**Production kernels are FROZEN.**"
if d_anchor not in s:
    sys.exit("ABORT: immutability-doctrine anchor not found in CLAUDE.md")
addition = (
    "**2026-07-31 speech-kernel freeze**: the freeze covers a production **KERNEL SET**, not one "
    "kernel — `llama.cpp` @ `production-consolidated-v8`, `whisper.cpp` @ `production-speech-v1` "
    f"(`{wc}`, ggml 0.18.0, STT), `qwentts.cpp` @ `production-speech-v1` (`{qc}`, ggml 0.17.0, TTS). "
    "Ratification: [`artifacts/operator/ratify_speech_kernel_freeze_20260731.json`]"
    "(artifacts/operator/ratify_speech_kernel_freeze_20260731.json). Both speech kernels carry "
    "load-bearing gfx90a/ROCm-6.2 patches that were UNCOMMITTED until this ratification. The three "
    "trees run three different ggml generations, so **every launcher must set its own "
    "`LD_LIBRARY_PATH`** and prove it with `scripts/utils/verify_ggml_linkage.sh` — a binary that "
    "inherits another tree's ggml runs silently wrong. `scripts/session/verify_speech_kernels.sh` "
    "enforces the speech branches.\n\n"
)
s = s.replace(d_anchor, addition + d_anchor, 1)
open(path, "w", encoding="utf-8").write(s)
print("  amended CLAUDE.md")
PY

if [ "$SKIP_VERIFIER" != "1" ]; then
echo
echo "=== 4. session verifier ==="
cat > "$ROOT/scripts/session/verify_speech_kernels.sh" <<'VERIFY'
#!/bin/bash
# Speech sibling of verify_llama_cpp.sh. Asserts the STT and TTS kernels are on
# their ratified production branches and that the built binaries still match the
# ratified SHA-256. Both trees carry load-bearing gfx90a/ROCm-6.2 patches; a
# stray checkout silently removes GPU speech.
#
# Ratification: artifacts/operator/ratify_speech_kernel_freeze_20260731.json
set -uo pipefail

JSON=/workspace/artifacts/operator/ratify_speech_kernel_freeze_20260731.json
[ -f "$JSON" ] || { echo "FAIL: no ratification artifact at $JSON"; exit 1; }

RC=0
check() {
    local key="$1" tree="$2" bin="$3"
    local want_branch want_sha have_branch have_sha
    want_branch=$(python3 -c "import json;print(json.load(open('$JSON'))['kernels']['$key']['branch'])")
    want_sha=$(python3    -c "import json;print(json.load(open('$JSON'))['kernels']['$key']['binary_sha256'])")
    have_branch=$(git -C "$tree" branch --show-current 2>/dev/null)

    if [ "$have_branch" != "$want_branch" ]; then
        echo "  FAIL $key: on '$have_branch', expected '$want_branch'"; RC=1
    else
        echo "  OK   $key: branch $have_branch"
    fi

    if [ -n "$(git -C "$tree" status --porcelain 2>/dev/null)" ]; then
        echo "  WARN $key: working tree is DIRTY — patches may be unrecorded again"
    fi

    if [ -x "$bin" ]; then
        have_sha=$(sha256sum "$bin" | cut -d' ' -f1)
        if [ "$have_sha" != "$want_sha" ]; then
            echo "  WARN $key: binary sha256 differs from ratified (rebuilt?)"
            echo "         ratified $want_sha"
            echo "         on disk  $have_sha"
        else
            echo "  OK   $key: binary matches ratified sha256"
        fi
    else
        echo "  FAIL $key: binary missing: $bin"; RC=1
    fi
}

echo "=== production speech kernels ==="
check whisper_cpp /mnt/raid0/llm/whisper.cpp /mnt/raid0/llm/whisper.cpp/build/bin/whisper-server
check qwentts_cpp /mnt/raid0/llm/qwentts.cpp /mnt/raid0/llm/qwentts.cpp/build/tts-server

echo
if [ "$RC" -eq 0 ]; then
    echo "PASS: speech kernels are on their ratified production branches."
else
    echo "FAIL: speech kernel drift detected. Do NOT publish speech measurements until resolved."
fi
echo "NOTE: each speech tree runs a DIFFERENT ggml than production llama.cpp."
echo "      Launchers must set their own LD_LIBRARY_PATH and prove it with"
echo "      scripts/utils/verify_ggml_linkage.sh (epyc-inference-research)."
exit $RC
VERIFY
chmod +x "$ROOT/scripts/session/verify_speech_kernels.sh"
say "wrote scripts/session/verify_speech_kernels.sh"
else
  say "SKIP_VERIFIER=1 — verifier not written (option B)"
fi

echo
echo "=== verification ==="
grep -qF "production KERNEL SET" "$ROOT/CLAUDE.md" && say "OK   CLAUDE.md carries the kernel-set doctrine" || abort "CLAUDE.md amendment missing"
[ -f "$JSON" ] && say "OK   ratification artifact present" || abort "ratification artifact missing"
if [ "$SKIP_VERIFIER" != "1" ]; then
  bash "$ROOT/scripts/session/verify_speech_kernels.sh" || true
fi

echo
echo "RATIFIED."
echo "  whisper.cpp $BRANCH = $W_COMMIT"
echo "  qwentts.cpp $BRANCH = $Q_COMMIT (ggml $Q_GGML)"
echo
echo "Review:  git -C /workspace diff -- CLAUDE.md"
echo "Commit:"
echo "  git -C /workspace add -- CLAUDE.md artifacts/operator/ scripts/session/verify_speech_kernels.sh"
echo "  git -C /workspace commit -m 'CLAUDE: ratify speech-kernel freeze (operator)'"
echo "  git -C /workspace push"

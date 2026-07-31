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

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

# The sanctioned ggml linkage verifier. Same absolute spelling as
# orchestrator_stack.py's _VERIFY_GGML_LINKAGE_SCRIPT so both enforce the same
# file rather than two drifting copies.
LINKAGE=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh

RC=0

# Coverage counters. A verification that inspected NOTHING must not be able to
# report PASS: an empty kernel list, a missing binary and an absent verifier all
# produce "no findings", which is byte-identical to "no problems" unless the
# script counts what it actually looked at.
KERNELS_DECLARED=0
KERNELS_BRANCH_CHECKED=0
KERNELS_LINKAGE_PROVEN=0

check() {
    local key="$1" tree="$2" bin="$3"
    local want_branch want_sha have_branch have_sha
    KERNELS_DECLARED=$((KERNELS_DECLARED+1))
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
    KERNELS_BRANCH_CHECKED=$((KERNELS_BRANCH_CHECKED+1))
}

# ---------------------------------------------------------------------------
# ggml linkage — the check this script used to only TALK about
# ---------------------------------------------------------------------------
#
# Until 2026-08-12 the tail of this script printed a sentence telling the reader
# that launchers "must prove it with verify_ggml_linkage.sh" and then exited 0
# without ever running it. Branch + sha256 prove WHICH BINARY exists on disk;
# they say nothing about WHICH LIBRARIES that binary will load. Those are
# different failures, and only the second one is silent: on 2026-07-31 a
# HIP-built whisper-cli loaded the production llama.cpp CPU-only ggml, printed
# `use gpu = 1`, and produced well-formed transcripts at CPU speed
# (INC-20260731-ggml-linkage-silent-cpu-fallback).
#
# Two environments are checked per kernel, because they answer two questions
# that can disagree:
#
#   1. LAUNCH RECIPE — with the kernel's own lib dir prepended, exactly what
#      orchestrator_stack.py composes for a backend-resolved aux service. This
#      asserts the frozen TREE is self-sufficient. If this fails, the kernel
#      itself is broken and no launcher can rescue it.
#   2. AMBIENT — this shell's LD_LIBRARY_PATH, unmodified. This asserts the
#      ENVIRONMENT is not poisoned. It is the condition that produced the
#      incident, and it is invisible to check 1: a hand-run whisper-cli, a
#      benchmark harness or any launcher that forgets to prepend inherits this
#      environment and mis-resolves silently.
#
# Both are RC=1. This script's headline is "do NOT publish speech measurements
# until resolved", and a poisoned ambient path is precisely a state in which
# speech measurements are wrong. session_init.sh treats a non-zero exit here as
# a loud warning, not an abort, so failing closed costs a message, not a session.
#
# NOTE ldd cannot see everything: ggml backends (ggml-hip, ggml-cpu-<arch>) are
# DLOPENED at runtime. verify_ggml_linkage.sh checks the DT_NEEDED set and says
# so itself. Passing here does not prove the GPU was used — confirm the device
# line in the server's own startup log for that.

# Fail-closed on an unavailable verifier. A skip is indistinguishable from a
# pass to every caller, and the state it would conceal is CPU numbers published
# as GPU numbers.
if [ ! -r "$LINKAGE" ]; then
    echo "FAIL: ggml linkage verifier not readable: $LINKAGE"
    echo "      Speech-kernel ggml linkage CANNOT be proven. Treating as FAILED,"
    echo "      not skipped — see epyc-inference-research/scripts/utils/."
    RC=1
fi

linkage() {
    local key="$1" bin="$2"
    local lib_dir out st inspected core

    if [ ! -r "$LINKAGE" ]; then
        echo "  FAIL $key: verifier unavailable — linkage NOT verified"; RC=1; return
    fi
    if [ ! -x "$bin" ]; then
        echo "  FAIL $key: binary missing, nothing to link-check: $bin"; RC=1; return
    fi
    lib_dir=$(cd "$(dirname "$bin")" && pwd)

    # --- 1. launch recipe: own lib dir first, as the orchestrator composes it
    out=$(LD_LIBRARY_PATH="$lib_dir:${LD_LIBRARY_PATH:-}" bash "$LINKAGE" "$bin" "$lib_dir" 2>&1)
    st=$?

    # Non-vacuity gate, and it is load-bearing. `verify_ggml_linkage.sh /bin/true
    # <tree>` exits 0 and prints PASS — it only reports "(no ggml libs in ldd
    # output)" and moves on. Exit status alone therefore cannot distinguish
    # "every library resolved correctly" from "there were no libraries". Demand
    # evidence that ggml was actually inspected: libggml-base is linked by every
    # ggml binary on this host (whisper-server, tts-server, llama-server).
    inspected=$(printf '%s\n' "$out" | grep -cE '^[[:space:]]+(OK|BAD)[[:space:]]+lib(ggml|whisper|llama|mtmd)')
    core=$(printf '%s\n' "$out" | grep -cE '^[[:space:]]+(OK|BAD)[[:space:]]+libggml-base\.so')
    if [ "$inspected" -eq 0 ] || [ "$core" -eq 0 ]; then
        echo "  FAIL $key: linkage check inspected NO ggml libraries — vacuous, not a pass"
        echo "         binary $bin"
        echo "         (ldd reported $inspected ggml/whisper/llama libs, libggml-base seen $core times)"
        RC=1
        return
    fi

    if [ "$st" -ne 0 ]; then
        echo "  FAIL $key: launch-recipe linkage FAILED — the frozen tree is not self-sufficient"
        printf '%s\n' "$out" | grep -E '^[[:space:]]+BAD ' | sed 's/^/       /'
        RC=1
        return
    fi
    echo "  OK   $key: $inspected ggml libs resolve inside $lib_dir (launch recipe)"

    # --- 2. ambient environment, untouched
    out=$(bash "$LINKAGE" "$bin" "$lib_dir" 2>&1)
    st=$?
    if [ "$st" -ne 0 ]; then
        echo "  FAIL $key: AMBIENT LD_LIBRARY_PATH mis-resolves this kernel's ggml"
        printf '%s\n' "$out" | grep -E '^[[:space:]]+BAD ' | sed 's/^/       /'
        echo "         The kernel is fine; this SHELL is poisoned. Anything launched"
        echo "         from it without prepending $lib_dir runs another tree's ggml."
        echo "         Fix:  export LD_LIBRARY_PATH=\"$lib_dir:\$LD_LIBRARY_PATH\""
        RC=1
        return
    fi
    echo "  OK   $key: ambient LD_LIBRARY_PATH also resolves in-tree"
    KERNELS_LINKAGE_PROVEN=$((KERNELS_LINKAGE_PROVEN+1))
}

echo "=== production speech kernels ==="
check whisper_cpp /mnt/raid0/llm/whisper.cpp /mnt/raid0/llm/whisper.cpp/build/bin/whisper-server
check qwentts_cpp /mnt/raid0/llm/qwentts.cpp /mnt/raid0/llm/qwentts.cpp/build/tts-server

echo
echo "=== ggml linkage (each speech tree runs its OWN ggml generation) ==="
linkage whisper_cpp /mnt/raid0/llm/whisper.cpp/build/bin/whisper-server
linkage qwentts_cpp /mnt/raid0/llm/qwentts.cpp/build/tts-server

# Coverage assertion. Without it, deleting both `check`/`linkage` calls above —
# or a future refactor that builds the kernel list dynamically and yields an
# empty one — would leave a script that prints PASS and exits 0 having verified
# nothing at all.
if [ "$KERNELS_DECLARED" -lt 2 ] || [ "$KERNELS_BRANCH_CHECKED" -lt 2 ]; then
    echo
    echo "FAIL: expected 2 speech kernels, inspected $KERNELS_BRANCH_CHECKED of $KERNELS_DECLARED."
    echo "      An empty or truncated kernel list is a verification defect, not a pass."
    RC=1
fi

echo
if [ "$RC" -eq 0 ]; then
    echo "PASS: speech kernels are on their ratified production branches, and"
    echo "      both resolve their own ggml ($KERNELS_LINKAGE_PROVEN/2 linkage-proven)."
else
    echo "FAIL: speech kernel drift or ggml mis-linkage detected."
    echo "      Do NOT publish speech measurements until resolved."
fi
echo "NOTE: ggml backends are DLOPENED at runtime and are invisible to ldd."
echo "      A linkage PASS proves the right libraries are reachable, not that the"
echo "      GPU was used — confirm the device line in the server's own startup log."
exit $RC

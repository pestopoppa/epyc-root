#!/bin/bash
# verify_kernel_store.sh — Attest the KERNEL STORE, not the source trees.
#
# WHY THIS EXISTS
#
# `/mnt/raid0/llm/kernels/production/<backend>` is the only path the orchestrator
# names: `registry/kernel_paths.py` resolves a BACKEND (a capability) to that
# symlink, and every launcher builds its LD_LIBRARY_PATH from it. Nothing
# enforcing has ever checked that layer.
#
#   * verify_llama_cpp.sh      attests the llama.cpp SOURCE TREE and its two build
#                              dirs by branch/commit/sha256, naming them directly.
#   * verify_speech_kernels.sh does the same for whisper.cpp and qwentts.cpp.
#   * verify_ggml_linkage.sh   attests one (binary, tree) pair it is handed.
#
# All three name build directories. NONE of them dereferences the symlink the
# orchestrator actually resolves, so a mis-pointed, dangling, or stale
# `production/gpu` passes every existing gate while the dashboard — the only
# reader of the store — is not a gate at all. This script closes that hole: it
# starts from the symlink and proves, end to end, that what the orchestrator
# would launch exists, is the right kind of binary, and resolves its own ggml.
#
# This is a STORE verifier, deliberately not a second identity verifier. It says
# nothing about which commit built the target — that is verify_llama_cpp.sh's and
# verify_speech_kernels.sh's job, and duplicating their sha256 constants here
# would create exactly the drifting-copy problem those two avoid by sharing one
# LINKAGE spelling.
#
# Read-only and safe at any time: stats, readlink, ldd. No process is started
# from the store (not even `--version`), nothing is written, nothing is
# restarted, no benchmark is run.
#
# Exit: 0 = every declared backend resolves to a usable, self-linking kernel dir
#       1 = at least one backend is missing, dangling, incomplete, mis-linked, or
#           the check could not be performed (fail-closed)
set -euo pipefail

# Overridable ONLY so the failure paths can be exercised against a synthetic store
# (a verifier whose red branches have never run is not known to be able to go red).
# Production callers pass nothing.
KERNEL_ROOT="${KERNEL_STORE_ROOT:-/mnt/raid0/llm/kernels}"
PRODUCTION_ROOT="$KERNEL_ROOT/production"
ARCHIVE_ROOT="$KERNEL_ROOT/archive"

# The authoritative backend -> binary map lives with the resolver that the
# orchestrator actually uses. Hardcoding a copy here would drift silently the
# first time a backend is added, and a verifier that checks a stale list reports
# PASS over the one backend nobody verified.
KERNEL_PATHS_PY=/mnt/raid0/llm/epyc-orchestrator/src/registry/kernel_paths.py

# The sanctioned ggml linkage verifier. Same absolute spelling as
# verify_llama_cpp.sh, verify_speech_kernels.sh and orchestrator_stack.py's
# _VERIFY_GGML_LINKAGE_SCRIPT, so all four enforce one file rather than four
# drifting copies. It lives in the RESEARCH repo, not this one.
LINKAGE=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh

RC=0

# Coverage counters. A verification that inspected NOTHING must not be able to
# report PASS: an empty backend map, an unreadable store and an absent linkage
# verifier all produce "no findings", which is byte-identical to "no problems"
# unless the script counts what it actually looked at.
BACKENDS_DECLARED=0
BACKENDS_RESOLVED=0
BACKENDS_LINKAGE_PROVEN=0
UNVERSIONED_TARGETS=0

# ---------------------------------------------------------------------------
# Backend map, read from the resolver itself
# ---------------------------------------------------------------------------
# Loaded by file path, not as a package import, so no orchestrator package
# __init__ runs. Fail-closed if it cannot be read: an unresolvable map means the
# store CANNOT be attested, and a skip is indistinguishable from a pass to every
# caller.
if [ ! -r "$KERNEL_PATHS_PY" ]; then
    echo "FAIL: backend map not readable: $KERNEL_PATHS_PY"
    echo "      The store cannot be attested against what the orchestrator resolves."
    exit 1
fi

# Emits one TAB-separated row per backend: name, binary, needs_prepend, vendor dirs.
MAP=$(python3 - "$KERNEL_PATHS_PY" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("kernel_paths", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
no_prepend = getattr(mod, "_BACKENDS_NEEDING_NO_PREPEND", frozenset())
for backend in sorted(mod.BACKEND_BINARIES):
    vendor = ":".join(str(p) for p in mod.BACKEND_VENDOR_LIB_DIRS.get(backend, ()))
    print("\t".join([
        backend,
        mod.BACKEND_BINARIES[backend],
        "0" if backend in no_prepend else "1",
        vendor,
    ]))
PY
) || {
    echo "FAIL: could not read BACKEND_BINARIES from $KERNEL_PATHS_PY"
    exit 1
}

if [ ! -r "$LINKAGE" ]; then
    echo "FAIL: ggml linkage verifier not readable: $LINKAGE"
    echo "      Store linkage CANNOT be proven. Treating as FAILED, not skipped —"
    echo "      see epyc-inference-research/scripts/utils/."
    RC=1
fi

# ---------------------------------------------------------------------------
# Provenance: versioned build dir vs live source tree
# ---------------------------------------------------------------------------
# REPORT, never fail. `production/cpu` and `production/gpu` currently point INSIDE
# the frozen v9 llama.cpp working tree (build/bin, build-hip/bin) rather than at an
# immutable, dated directory under kernels/builds/. That is the known present state
# and a v10 promotion is meant to fix it, so failing on it would make this script
# red on a healthy store and it would be ignored. It is still a real durability
# defect — a rebuild or a branch switch in that tree mutates production in place,
# with no archived predecessor to roll back to — so it is always printed.
provenance() {
    local key="$1" target="$2" note=""
    case "$target" in
        "$KERNEL_ROOT"/builds/*|"$KERNEL_ROOT"/archive/*|"$KERNEL_ROOT"/candidates/*)
            echo "  OK   $key: target is a versioned store dir (${target#"$KERNEL_ROOT"/})"
            return
            ;;
    esac
    UNVERSIONED_TARGETS=$((UNVERSIONED_TARGETS+1))
    # If the target sits inside a git work tree, name the branch — that is the
    # thing that can move production without touching the store.
    local tree
    tree=$(git -C "$target" rev-parse --show-toplevel 2>/dev/null || true)
    if [ -n "$tree" ]; then
        local branch
        branch=$(git -C "$target" branch --show-current 2>/dev/null || echo DETACHED)
        note=" (inside source tree $tree, branch '$branch')"
    fi
    echo "  WARN $key: target is NOT a versioned build dir$note"
    echo "         $target"
    echo "         A rebuild or checkout there mutates production in place and there"
    echo "         is no archived predecessor to roll back to. Promote into"
    echo "         $KERNEL_ROOT/builds/<backend>-<YYYYMMDD>-<short-sha> and repoint."
}

# ---------------------------------------------------------------------------
# The store check proper
# ---------------------------------------------------------------------------
check_backend() {
    local key="$1" binary_name="$2" needs_prepend="$3" vendor="$4"
    local link="$PRODUCTION_ROOT/$key" target binary
    BACKENDS_DECLARED=$((BACKENDS_DECLARED+1))

    if [ ! -L "$link" ]; then
        if [ -e "$link" ]; then
            echo "  FAIL $key: $link exists but is NOT a symlink — the store's upgrade"
            echo "         path (archive old, repoint) does not apply to it."
        else
            echo "  FAIL $key: $link is MISSING. Nothing resolves this backend."
            echo "         Repoint it with: ln -sfn <build dir> $link"
        fi
        RC=1
        return
    fi

    target=$(readlink -f -- "$link" 2>/dev/null || true)
    if [ -z "$target" ] || [ ! -e "$target" ]; then
        echo "  FAIL $key: DANGLING symlink -> $(readlink -- "$link")"
        RC=1
        return
    fi
    if [ ! -d "$target" ] || [ ! -r "$target" ] || [ ! -x "$target" ]; then
        echo "  FAIL $key: target is not a readable directory: $target"
        RC=1
        return
    fi
    echo "  OK   $key: $link -> $target"

    binary="$target/$binary_name"
    if [ ! -f "$binary" ] || [ ! -x "$binary" ]; then
        echo "  FAIL $key: expected binary '$binary_name' missing or not executable there"
        echo "         $binary"
        RC=1
        return
    fi
    echo "  OK   $key: $binary_name present and executable"

    # COMPANION TOOLS. The primary binary is not the whole kernel: scripts/lib/executor.py
    # resolves llama-completion / llama-speculative / llama-lookup / llama-mtmd-cli / llama-cli
    # through this same store (scripts/lib/executor_paths.py get_binary()). A promotion that
    # built only `--target llama-server llama-bench` produces a directory that passes every
    # other check here and then FileNotFoundErrors at launch -- observed 2026-09-21, which is
    # why this block exists. Checked only for the llama backends; stt/tts ship one binary.
    if [ "$key" = "cpu" ] || [ "$key" = "gpu" ]; then
        local missing_tools=""
        local tool
        for tool in llama-completion llama-speculative llama-lookup llama-mtmd-cli llama-cli; do
            if [ ! -x "$target/$tool" ]; then
                missing_tools="$missing_tools $tool"
            fi
        done
        if [ -n "$missing_tools" ]; then
            echo "  FAIL $key: companion tools missing from the resolved kernel dir:$missing_tools"
            echo "         executor.py resolves these through the store; a partial build"
            echo "         (e.g. --target llama-server only) fails at launch, not here."
            RC=1
        else
            echo "  OK   $key: 5 companion tools present (completion/speculative/lookup/mtmd-cli/cli)"
        fi
    fi

    # libggml-hip presence is a CAPABILITY assertion, and it is the exact shape of
    # INC-20260731: a GPU-resolved directory with no HIP backend does not raise, it
    # just runs on the CPU with well-formed output. The store README states the
    # invariant directly — present on gpu/stt/tts, correctly absent on cpu.
    if [ "$key" = "cpu" ]; then
        if [ -e "$target/libggml-hip.so" ]; then
            echo "  WARN $key: libggml-hip.so present in the CPU backend dir (README says"
            echo "         it is correctly absent there) — is cpu pointing at a HIP build?"
        else
            echo "  OK   $key: no libggml-hip.so, as expected for the CPU backend"
        fi
    else
        if [ ! -e "$target/libggml-hip.so" ]; then
            echo "  FAIL $key: no libggml-hip.so in the resolved dir — an accelerated"
            echo "         backend that would silently serve on CPU."
            RC=1
        else
            echo "  OK   $key: libggml-hip.so present"
        fi
    fi

    provenance "$key" "$target"
    BACKENDS_RESOLVED=$((BACKENDS_RESOLVED+1))

    linkage "$key" "$binary" "$target" "$needs_prepend" "$vendor"
}

# ggml linkage, composed EXACTLY as the orchestrator composes it.
#
# kernel_paths.backend_ld_library_path() prepends the backend dir (plus any vendor
# runtime) for every backend except `cpu`, for which it deliberately returns [] —
# the ambient environment already resolves to the CPU tree. So for `cpu` the
# AMBIENT environment IS the launch environment and a poisoned one is a real
# failure; for the others the launch recipe is load-bearing and ambient is only
# informational, because the launcher always prepends.
linkage() {
    local key="$1" binary="$2" target="$3" needs_prepend="$4" vendor="$5"
    local ldpath out st inspected core

    if [ ! -r "$LINKAGE" ]; then
        echo "  FAIL $key: verifier unavailable — store linkage NOT verified"
        RC=1
        return
    fi

    if [ "$needs_prepend" = "1" ]; then
        ldpath="$target${vendor:+:$vendor}:${LD_LIBRARY_PATH:-}"
    else
        ldpath="${LD_LIBRARY_PATH:-}"
    fi

    set +e
    out=$(LD_LIBRARY_PATH="$ldpath" bash "$LINKAGE" "$binary" "$target" 2>&1)
    st=$?
    set -e

    # Non-vacuity, counted here as well as inside the verifier. The verifier gained
    # an intrinsic gate (exit 2) on 2026-08-12; counting anyway keeps this script's
    # own coverage claim ("N/M linkage-proven") honest rather than inherited.
    inspected=$(printf '%s\n' "$out" | grep -cE '^[[:space:]]+(OK|BAD)[[:space:]]+lib(ggml|whisper|llama|mtmd|parakeet)' || true)
    core=$(printf '%s\n' "$out" | grep -cE '^[[:space:]]+(OK|BAD)[[:space:]]+libggml-base\.so' || true)

    if [ "$st" -eq 2 ] || [ "$inspected" -eq 0 ] || [ "$core" -eq 0 ]; then
        echo "  FAIL $key: linkage check inspected NO ggml libraries — vacuous, not a pass"
        echo "         binary $binary"
        echo "         (inspected $inspected ggml libs, libggml-base seen $core times, rc=$st)"
        RC=1
        return
    fi
    if [ "$st" -ne 0 ]; then
        if [ "$needs_prepend" = "1" ]; then
            echo "  FAIL $key: launch-recipe linkage FAILED — the resolved store dir is"
            echo "         not self-sufficient under the environment the orchestrator builds."
        else
            echo "  FAIL $key: AMBIENT LD_LIBRARY_PATH mis-resolves this backend's ggml, and"
            echo "         '$key' is the backend the orchestrator prepends NOTHING for, so"
            echo "         the ambient environment IS its launch environment."
            echo "         Fix:  export LD_LIBRARY_PATH=\"$target:\$LD_LIBRARY_PATH\""
        fi
        printf '%s\n' "$out" | grep -E '^[[:space:]]+BAD ' | sed 's/^/       /'
        RC=1
        return
    fi
    echo "  OK   $key: $inspected ggml libs resolve inside $target (as launched)"
    BACKENDS_LINKAGE_PROVEN=$((BACKENDS_LINKAGE_PROVEN+1))

    # Informational second environment for prepend backends. Not a failure: the
    # orchestrator always prepends, so a poisoned ambient path only bites a
    # hand-run binary or a harness that forgets — worth knowing, not worth red.
    if [ "$needs_prepend" = "1" ]; then
        set +e
        out=$(bash "$LINKAGE" "$binary" "$target" 2>&1)
        st=$?
        set -e
        if [ "$st" -ne 0 ]; then
            echo "  WARN $key: ambient LD_LIBRARY_PATH mis-resolves this kernel (rc=$st)."
            echo "         Harmless for orchestrator launches, which prepend; NOT harmless"
            echo "         for anything hand-run from such a shell."
        fi
    fi
}

echo "=== kernel store: $PRODUCTION_ROOT ==="
if [ ! -d "$PRODUCTION_ROOT" ]; then
    echo "  FAIL store root missing: $PRODUCTION_ROOT"
    echo
    echo "FAIL: the kernel store does not exist; every backend is unresolvable."
    exit 1
fi

while IFS=$'\t' read -r backend binary needs_prepend vendor; do
    [ -n "$backend" ] || continue
    check_backend "$backend" "$binary" "$needs_prepend" "${vendor:-}"
    echo
done <<< "$MAP"

# ---------------------------------------------------------------------------
# Archive, reported only
# ---------------------------------------------------------------------------
# The README's upgrade procedure archives the outgoing target before repointing.
# An empty archive alongside unversioned production targets means no promotion has
# ever gone through that procedure, i.e. there is no rollback anchor IN THE STORE.
echo "=== archive (rollback anchors) ==="
if [ ! -d "$ARCHIVE_ROOT" ]; then
    echo "  WARN archive dir missing: $ARCHIVE_ROOT"
else
    archived=$(find "$ARCHIVE_ROOT" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)
    if [ "$archived" -eq 0 ]; then
        echo "  WARN archive is EMPTY — no outgoing kernel has ever been archived here,"
        echo "         so the store holds no rollback anchor of its own."
    else
        echo "  OK   $archived archived entr(y|ies):"
        find "$ARCHIVE_ROOT" -mindepth 1 -maxdepth 1 -printf '         %f -> %l\n' 2>/dev/null | sort
    fi
fi
echo

# Coverage assertion. Without it, an empty or truncated backend map would leave a
# script that prints PASS having verified nothing at all.
if [ "$BACKENDS_DECLARED" -lt 4 ]; then
    echo "FAIL: expected at least 4 backends (cpu, gpu, stt, tts), the map declared"
    echo "      $BACKENDS_DECLARED. An empty or truncated backend list is a verification"
    echo "      defect, not a pass."
    RC=1
fi

if [ "$RC" -eq 0 ]; then
    echo "PASS: $BACKENDS_RESOLVED/$BACKENDS_DECLARED backends resolve to a usable kernel directory, and"
    echo "      $BACKENDS_LINKAGE_PROVEN/$BACKENDS_DECLARED resolve their own ggml under the environment they are launched with."
else
    echo "FAIL: the kernel store does not resolve correctly."
    echo "      Do NOT launch or publish measurements from an unresolved backend —"
    echo "      a missing ggml backend does not raise, it silently is not used."
fi
if [ "$UNVERSIONED_TARGETS" -gt 0 ]; then
    echo "NOTE: $UNVERSIONED_TARGETS backend(s) point into a live source tree rather than a versioned"
    echo "      build dir. Reported, not failed — this is the known pre-v10 state."
fi
echo "NOTE: this verifies the STORE (symlink -> target -> binary -> ggml linkage)."
echo "      It does NOT attest kernel IDENTITY — run verify_llama_cpp.sh and"
echo "      verify_speech_kernels.sh for branch/commit/sha256. And ggml backends are"
echo "      DLOPENED at runtime, so a linkage PASS proves the right libraries are"
echo "      reachable, not that the GPU was used."
exit $RC

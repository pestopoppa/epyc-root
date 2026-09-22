#!/bin/bash
# =============================================================================
# OPERATOR-EXECUTED: rebuild the speech kernels relocatable ($ORIGIN) and
# re-ratify their digests.
# =============================================================================
#
# WHY THIS NEEDS YOU AND NOT AN AGENT
# -----------------------------------
# whisper.cpp and qwentts.cpp are FROZEN production kernels, ratified BY SHA256 in
# artifacts/operator/ratify_speech_kernel_freeze_20260731.json and enforced by
# scripts/session/verify_speech_kernels.sh. A rebuild necessarily changes those
# digests. Re-ratifying a production freeze is a human-only trust boundary
# (MEASUREMENT.md: "production freezes/cutovers"). Nothing here runs without you.
#
# WHAT PROBLEM THIS SOLVES
# ------------------------
# Both speech binaries carry an ABSOLUTE RUNPATH into their own source trees:
#   whisper-server -> /mnt/raid0/llm/whisper.cpp/build/bin:/opt/rocm/lib
#   tts-server     -> /mnt/raid0/llm/qwentts.cpp/build:/opt/rocm/lib
# So kernels/production/{stt,tts} cannot be repointed at a versioned copy and have
# it be self-contained. Measured 2026-09-21 on the staged copies: under the real
# launch recipe (LD_LIBRARY_PATH prepended) 0 libs resolve outside the copy, but
# with LD_LIBRARY_PATH unset, 5 (stt) / 4 (tts) resolve back into the SOURCE TREE.
# That works only because these use RUNPATH (searched after LD_LIBRARY_PATH) rather
# than RPATH. It is a latent trap: anything launching them without the orchestrator's
# env silently loads the source tree.
#
# cpu/gpu do not have this problem -- v9 and the v10 candidate are both $ORIGIN.
# This script brings stt/tts up to the same standard.
#
# WHAT IT DOES
# ------------
#   1. Verifies the frozen trees are on their ratified branches/commits FIRST.
#   2. Builds each into a NEW build dir with -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON.
#      The existing build dirs and the source trees are NOT touched, so the current
#      ratified binaries remain byte-identical and verify_speech_kernels.sh keeps
#      passing throughout.
#   3. Proves each new binary is relocatable: RUNPATH is $ORIGIN, and ggml resolves
#      inside the tree with LD_LIBRARY_PATH UNSET.
#   4. Copies them into kernels/builds/<backend>-<date>-origin-<sha>/ with SHA256SUMS.
#   5. Emits a ratification JSON with the NEW digests for you to sign.
#
# WHAT IT DOES NOT DO
# -------------------
#   * does NOT repoint kernels/production/{stt,tts}
#   * does NOT modify the frozen source trees or their existing build dirs
#   * does NOT edit verify_speech_kernels.sh or the existing ratification artifact
#   * runs NO inference and starts NO server
# After you sign, repointing is two ln -sfn calls and a verify_kernel_store.sh run.
#
# USAGE:  bash artifacts/operator/ratify_speech_origin_rebuild_20260921.sh
# =============================================================================
set -euo pipefail

STAMP=$(date -u +%Y%m%d)
OUT=/workspace/artifacts/operator/speech-origin-rebuild-${STAMP}.json
WH=/mnt/raid0/llm/whisper.cpp
TT=/mnt/raid0/llm/qwentts.cpp

echo "=== 0. the frozen kernels must verify BEFORE we touch anything ==="
bash /workspace/scripts/session/verify_speech_kernels.sh || {
    echo "REFUSING: speech kernels do not verify at their ratified state." >&2
    echo "Fix that first; a rebuild from an unverified tree ratifies nothing." >&2
    exit 1
}

for spec in "stt:${WH}:build-origin:whisper-server:production-speech-v1" \
            "tts:${TT}:build-origin:tts-server:production-speech-v1"; do
    B=${spec%%:*}; rest=${spec#*:}; TREE=${rest%%:*}; rest=${rest#*:}
    BDIR=${rest%%:*}; rest=${rest#*:}; BIN=${rest%%:*}; WANT_BRANCH=${rest#*:}

    HAVE_BRANCH=$(git -C "$TREE" rev-parse --abbrev-ref HEAD)
    if [ "$HAVE_BRANCH" != "$WANT_BRANCH" ]; then
        echo "REFUSING: $TREE is on '$HAVE_BRANCH', expected '$WANT_BRANCH'." >&2
        exit 1
    fi
    if [ -n "$(git -C "$TREE" status --porcelain)" ]; then
        echo "REFUSING: $TREE has uncommitted changes; a frozen kernel must be clean." >&2
        exit 1
    fi
    SHA=$(git -C "$TREE" rev-parse --short HEAD)
    echo ""
    echo "=== $B: rebuilding $TREE @ $SHA with \$ORIGIN into $BDIR ==="
    echo "    (source tree and existing build dir are NOT modified)"

    # Reuse the tree's own cache so the build options match the ratified one; the
    # ONLY intentional difference is the RPATH mode.
    SRC_CACHE=""
    for c in "$TREE/build/CMakeCache.txt" "$TREE/build-hip/CMakeCache.txt"; do
        [ -f "$c" ] && { SRC_CACHE="$c"; break; }
    done
    FLAGS=()
    if [ -n "$SRC_CACHE" ]; then
        while IFS= read -r line; do FLAGS+=("$line"); done < <(
            grep -E '^(GGML|WHISPER|QWENTTS|LLAMA|AMDGPU|CMAKE_BUILD_TYPE|CMAKE_HIP_COMPILER)[A-Za-z0-9_]*:' "$SRC_CACHE" \
            | grep -v ':INTERNAL=' | grep -v 'NOTFOUND' \
            | sed -E 's/^([^:]+):[A-Z]+=(.*)$/-D\1=\2/'
        )
        echo "    carried ${#FLAGS[@]} build options forward from $(basename "$(dirname "$SRC_CACHE")")/CMakeCache.txt"
    else
        echo "    WARNING: no CMakeCache found; building with defaults + \$ORIGIN" >&2
    fi

    cmake -S "$TREE" -B "$TREE/$BDIR" "${FLAGS[@]}" -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON
    cmake --build "$TREE/$BDIR" -j 40

    NEWBIN=$(find "$TREE/$BDIR" -name "$BIN" -type f -perm -u+x | head -1)
    [ -n "$NEWBIN" ] || { echo "REFUSING: $BIN not produced by the rebuild." >&2; exit 1; }

    echo "--- proving relocatability (this is the whole point) ---"
    RP=$(readelf -d "$NEWBIN" | grep -oE 'Library runpath: \[[^]]*\]' || true)
    echo "    $RP"
    case "$RP" in
        *'$ORIGIN'*) echo "    OK: RUNPATH carries \$ORIGIN" ;;
        *) echo "REFUSING: RUNPATH is not \$ORIGIN -- the rebuild did not achieve its purpose." >&2; exit 1 ;;
    esac

    NEWDIR=$(dirname "$NEWBIN")
    echo "--- ggml must resolve with LD_LIBRARY_PATH UNSET ---"
    env -u LD_LIBRARY_PATH bash \
        /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh \
        "$NEWBIN" "$NEWDIR" || {
        echo "REFUSING: the rebuilt $B kernel is still not self-contained." >&2; exit 1; }

    DEST=/mnt/raid0/llm/kernels/builds/${B}-${STAMP}-origin-${SHA}
    echo "--- staging into $DEST ---"
    mkdir -p "$DEST"
    cp -a "$NEWDIR" "$DEST/bin"
    ( cd "$DEST" && find bin -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS )
    echo "    staged; $(wc -l < "$DEST/SHA256SUMS") files hashed"
    echo "${B}|${TREE}|${SHA}|${DEST}|$(sha256sum "$DEST/bin/$BIN" | cut -d' ' -f1)" \
        >> /tmp/speech-origin-rows.$$
done

echo ""
echo "=== emitting the ratification bundle ==="
python3 - "$OUT" /tmp/speech-origin-rows.$$ <<'PY'
import json, sys, datetime
out, rows_file = sys.argv[1], sys.argv[2]
kernels = {}
for line in open(rows_file):
    b, tree, sha, dest, digest = line.strip().split("|")
    kernels[b] = {"source_tree": tree, "commit": sha, "staged_build_dir": dest,
                  "binary_sha256": digest, "runpath": "$ORIGIN",
                  "self_contained_without_ld_library_path": True}
json.dump({
  "schema": "epyc.speech_kernel_origin_rebuild.v1",
  "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "status": "AWAITING OPERATOR RATIFICATION",
  "what_changed": "speech kernels rebuilt with CMAKE_BUILD_RPATH_USE_ORIGIN=ON so "
                  "kernels/production/{stt,tts} can point at a versioned, self-contained "
                  "build dir instead of into a live source tree",
  "supersedes_digests_in": "artifacts/operator/ratify_speech_kernel_freeze_20260731.json",
  "kernels": kernels,
  "not_done_by_this_script": [
      "kernels/production/{stt,tts} NOT repointed",
      "frozen source trees and their existing build dirs NOT modified",
      "verify_speech_kernels.sh NOT edited -- it still attests the OLD digests and still passes",
  ],
  "to_activate_after_signing": [
      "update the binary_sha256 values in verify_speech_kernels.sh's ratification source to the digests above",
      "ln -sfn <staged_build_dir>/bin /mnt/raid0/llm/kernels/production/stt",
      "ln -sfn <staged_build_dir>/bin /mnt/raid0/llm/kernels/production/tts",
      "bash /workspace/scripts/session/verify_kernel_store.sh   # must exit 0",
      "bash /workspace/scripts/session/verify_speech_kernels.sh # must exit 0 against the NEW digests",
  ],
}, open(out, "w"), indent=2)
print("wrote", out)
PY
rm -f /tmp/speech-origin-rows.$$
echo ""
echo "=== DONE. Nothing in production changed. Review ${OUT} and sign. ==="

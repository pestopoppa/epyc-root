#!/bin/bash
# v11 FA routing A/B: store builds of the CURRENT GPU champion (ak/champion/llama-cpp-ffc1bac82eec @ 90c12df42).
# NOT production, NOT the champion branch tip (untouched), never the frozen tree.
#
#   A  src-champion (90c12df42, detached clone --shared)  GGML_HIP_ROCWMMA_FATTN=ON   champion recipe as is
#   B  src-champion (90c12df42)                           GGML_HIP_ROCWMMA_FATTN=OFF  exact v11 D=256 routing
#   C  src-c  (experimental/v11-fa-ab-20261004 = 90c12df42 + #27870 b74f590ea + #28576 bfdc32183)  ROCWMMA OFF
#   D  src-d  (C + local ncols-cap patch, see NCOLS_CAP.md)  ROCWMMA OFF   [optional; only if src-d exists]
#
# Recipe: gfx90a-house-v1 (= build_store.sh / gpu-20260929-90c12df42) with only the ROCWMMA flag varied.
# Contention: the WHOLE configure+build runs inside ONE region-lock hold on cpu 0-95 (role build, tag v11fa),
# pinned to 0-95 with taskset (region-lock does not pin), nice 19, ionice idle, -j24.
# Verification (strings / code-object audit / linkage / digests) runs after the lock is released (light, 1 core).
#
# usage: build_arms.sh [A B C D ...]   (default: A B C, plus D if src-d exists)
set -euo pipefail

W=/mnt/raid0/llm/tmp/v11-fa-ab-20261004
STORE=/mnt/raid0/llm/kernels/builds
LOCK=/workspace/repos/epyc-orchestrator/scripts/region-lock
LINK=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh

ARMS=("$@")
if [ ${#ARMS[@]} -eq 0 ]; then
    ARMS=(A B C)
    [ -d "$W/src-d" ] && ARMS+=(D)
fi

src_of() { case "$1" in A|B) echo "$W/src-champion" ;; C) echo "$W/src-c" ;; D) echo "$W/src-d" ;; *) return 1 ;; esac; }
wmma_of() { case "$1" in A) echo ON ;; *) echo OFF ;; esac; }
dir_of() {
    local src; src=$(src_of "$1")
    echo "$STORE/gpu-20261004-$(git -C "$src" rev-parse --short=9 HEAD)-$1"
}

# preflight: clean sources, no pre-existing build dir (never overwrite a store dir)
for a in "${ARMS[@]}"; do
    src=$(src_of "$a") || { echo "unknown arm $a"; exit 2; }
    [ -z "$(git -C "$src" status --porcelain)" ] || { echo "FAIL: $src dirty"; exit 1; }
    d=$(dir_of "$a")
    [ ! -e "$d" ] || { echo "FAIL: $d exists (refusing to overwrite a store dir)"; exit 1; }
    echo "arm $a: src=$src sha=$(git -C "$src" rev-parse HEAD) rocwmma=$(wmma_of "$a") -> $d"
done

# ---- builds: one lock hold ------------------------------------------------------------------------------
INNER=$(mktemp -p "$W" inner_build.XXXXXX.sh)
{
    echo '#!/bin/bash'
    echo 'set -euo pipefail'
    echo 'RUN="nice -n 19 ionice -c3 taskset -c 0-95"'
    for a in "${ARMS[@]}"; do
        src=$(src_of "$a"); d=$(dir_of "$a"); wm=$(wmma_of "$a")
        cat <<EOF
echo "[\$(date -u +%FT%TZ)] arm $a configure"
\$RUN cmake -S "$src" -B "$d" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a \\
    -DGGML_HIP_ROCWMMA_FATTN=$wm -DGGML_NATIVE=ON \\
    -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=\$ORIGIN;/opt/rocm/lib' \\
    > "$d.configure.log" 2>&1
mv "$d.configure.log" "$d/CONFIGURE.log"
echo "build start \$(date -u +%FT%TZ)" > "$d/BUILD.log"
\$RUN cmake --build "$d" -j24 >> "$d/BUILD.log" 2>&1
echo "build end \$(date -u +%FT%TZ) rc=0" >> "$d/BUILD.log"
echo "[\$(date -u +%FT%TZ)] arm $a built"
EOF
    done
} > "$INNER"
chmod +x "$INNER"
echo "[$(date -u +%FT%TZ)] waiting for region lock cpu 0-95 (role build, tag v11fa)"
"$LOCK" run --cpu-list 0-95 --role build --tag v11fa -- "$INNER"
rm -f "$INNER"
echo "[$(date -u +%FT%TZ)] lock released"

# ---- verification (after the lock; 1 core, nice 19) -------------------------------------------------------
V="nice -n 19 ionice -c3 taskset -c 183"
for a in "${ARMS[@]}"; do
    src=$(src_of "$a"); d=$(dir_of "$a"); wm=$(wmma_of "$a")
    lib=$(readlink -f "$d/bin/libggml-hip.so")
    (cd "$d/bin" && sha256sum $(find . -maxdepth 1 -type f | sort) > ../SHA256SUMS)
    {
        echo "# $(basename "$d") — v11 FA routing A/B arm $a (NOT production, NOT the champion branch)"
        echo
        echo "- source: \`$src\` (git clone --shared of /mnt/raid0/llm/llama.cpp, read-only use), HEAD \`$(git -C "$src" rev-parse HEAD)\`"
        echo "  - $(git -C "$src" log --oneline 90c12df42..HEAD | sed 's/^/commit /' | tr '\n' ';' ) (empty = champion tip 90c12df42)"
        echo "- recipe: gfx90a-house-v1 with GGML_HIP_ROCWMMA_FATTN=$wm (only variation); relocatability flags as build_store.sh"
        echo "- built under: region-lock --cpu-list 0-95 --role build --tag v11fa, nice 19, ionice idle, taskset 0-95, -j24"
        echo "- builder: $W/build_arms.sh"
        echo "- version: \`$(env -u LD_LIBRARY_PATH "$d/bin/llama-server" --version 2>&1 | grep -m1 version)\`"
        echo "- CMakeCache: $(grep -E '^GGML_HIP_ROCWMMA_FATTN:' "$d/CMakeCache.txt")"
        echo "- \`strings libggml-hip.so | grep -ci wmma\` = $(strings "$lib" | grep -ci wmma) (host launcher symbol + source path; present in every arm, not a discriminator)"
        echo "- device code-object audit (fa_codeobj_audit.py):"
        $V python3 "$W/fa_codeobj_audit.py" "$lib" "$W/audit-$a" | sed 's/^/    /'
        echo "- linkage (env -u LD_LIBRARY_PATH verify_ggml_linkage.sh llama-server):"
        env -u LD_LIBRARY_PATH "$LINK" "$d/bin/llama-server" 2>&1 | tail -3 | sed 's/^/    /' || true
        echo "- ldd libggml-hip.so not-found: $(ldd "$lib" | grep -c 'not found' || true)"
        echo "- digests: SHA256SUMS ($(wc -l < "$d/SHA256SUMS") files); libggml-hip $(sha256sum "$lib" | cut -c1-64)"
    } > "$d/PROVENANCE.md" 2>&1
    expect=$wm
    got=$(grep -o 'VERDICT rocwmma_fattn=[A-Z]*' "$d/PROVENANCE.md" | cut -d= -f2)
    [ "$got" = "$expect" ] && echo "arm $a: rocwmma device code $got == expected $expect OK" \
                           || { echo "arm $a: rocwmma device code '$got' != expected $expect FAIL"; exit 1; }
    cp "$W/audit-$a/fa_kernels.tsv" "$d/fa_kernels.tsv"
    echo "OK $d"
done

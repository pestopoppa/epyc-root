#!/bin/bash
# Seal the exact v9 candidate CPU/HIP runtime trees into a relocatable,
# hash-bound stage. This script does not mutate the frozen production clone.
set -euo pipefail

ROOT=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
EXPERIMENTAL=/mnt/raid0/llm/llama.cpp-experimental
EXPECTED_BRANCH=experimental-v9-dspark-promotion
EXPECTED_HEAD=0db32c06e3e550065b78311a6031ef3dd2c4f27c
EXPECTED_VERSION_LINE='version: 10125 (0db32c06e)'
CPU_SOURCE="$EXPERIMENTAL/build-v9-cpu/bin"
HIP_SOURCE="$EXPERIMENTAL/build-v9-hip/bin"
STAGE_PARENT=/mnt/raid0/llm/kernel-runtime-stages
STAGE="$STAGE_PARENT/production-consolidated-v9-0db32c06e"
# Literal loader token; expansion must happen in the ELF loader, not this shell.
# shellcheck disable=SC2016
CPU_RPATH='$ORIGIN'
# shellcheck disable=SC2016
HIP_RPATH='$ORIGIN:/opt/rocm/lib'

: "${PACKAGED_AT:?set PACKAGED_AT to an RFC3339 timestamp with timezone}"
: "${PACKAGING_ID:?set PACKAGING_ID to a unique letters/numbers/dot/underscore/dash identifier}"
[[ $PACKAGED_AT =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$ ]] || {
    printf 'PACKAGED_AT must be an RFC3339 timestamp with timezone\n' >&2
    exit 2
}
[[ $PACKAGING_ID =~ ^[A-Za-z0-9._-]+$ ]] || {
    printf 'PACKAGING_ID contains unsupported characters\n' >&2
    exit 2
}

ARTIFACT_REL="artifacts/operator/v9-runtime-packaging-$PACKAGING_ID"
ARTIFACT="$ROOT/$ARTIFACT_REL"
TMP_STAGE=''
stage_installed=0
completed=0

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    local status=$?
    trap - EXIT
    if (( ! completed )); then
        if [[ -n $TMP_STAGE && -d $TMP_STAGE ]]; then
            rm -rf -- "$TMP_STAGE"
        fi
        if (( stage_installed )) && [[ -d $STAGE ]]; then
            rm -rf -- "$STAGE"
        fi
        if [[ -d $ARTIFACT ]]; then
            rm -rf -- "$ARTIFACT"
        fi
    fi
    exit "$status"
}
trap cleanup EXIT

require_source_identity() {
    [[ $(git -C "$EXPERIMENTAL" branch --show-current) == "$EXPECTED_BRANCH" ]] ||
        fail "experimental branch is not $EXPECTED_BRANCH"
    [[ $(git -C "$EXPERIMENTAL" rev-parse HEAD) == "$EXPECTED_HEAD" ]] ||
        fail "experimental HEAD is not $EXPECTED_HEAD"
    git -C "$EXPERIMENTAL" diff --quiet || fail 'experimental tracked worktree is dirty'
    git -C "$EXPERIMENTAL" diff --cached --quiet || fail 'experimental index is dirty'
    [[ -x $CPU_SOURCE/llama-server && -x $HIP_SOURCE/llama-server ]] ||
        fail 'candidate CPU/HIP server binary is missing'
}

tree_hashes() {
    local tree=$1 output=$2
    (
        cd "$tree"
        find . -type f -print0 | LC_ALL=C sort -z | xargs -0r sha256sum --
    ) >"$output"
}

symlinks() {
    local tree=$1 output=$2
    (
        cd "$tree"
        find . -type l -printf '%p -> %l\n' | LC_ALL=C sort
    ) >"$output"
}

rewrite_elf_rpaths() {
    local class=$1 tree=$2 wanted=$3 file rel old
    while IFS= read -r -d '' file; do
        readelf -h "$file" >/dev/null 2>&1 || continue
        rel=${file#"$tree/"}
        old=$(patchelf --print-rpath "$file" 2>/dev/null || true)
        patchelf --set-rpath "$wanted" "$file"
        printf '%s\t%s\t%s\t%s\n' "$class" "$rel" "$old" "$wanted" >>"$ARTIFACT/rpath-rewrites.tsv"
    done < <(find "$tree" -type f -print0)
}

require_rpaths() {
    local tree=$1 wanted=$2 file actual count=0
    while IFS= read -r -d '' file; do
        readelf -h "$file" >/dev/null 2>&1 || continue
        actual=$(patchelf --print-rpath "$file" 2>/dev/null || true)
        [[ $actual == "$wanted" ]] || fail "unexpected RPATH for $file: ${actual:-none}"
        [[ $actual != *llama.cpp-experimental* ]] || fail "experimental path remains in $file"
        count=$((count + 1))
    done < <(find "$tree" -type f -print0)
    printf '%s\n' "$count"
}

require_tree() {
    local tree=$1
    [[ -d $tree && ! -L $tree && -x $tree/llama-server ]] || fail "invalid runtime tree: $tree"
    if find "$tree" -xtype l -print -quit | grep -q .; then
        find "$tree" -xtype l -print >&2
        fail "dangling symlink in $tree"
    fi
}

verify_clean_binary() {
    local class=$1 tree=$2 ldd_out=$3 version_out=$4 expected_rpath=$5 output line
    [[ $(patchelf --print-rpath "$tree/llama-server") == "$expected_rpath" ]] ||
        fail "$class llama-server RPATH mismatch"
    output=$(env -i PATH=/usr/bin:/bin LANG=C LC_ALL=C ldd "$tree/llama-server") ||
        fail "$class clean-environment ldd failed"
    printf '%s\n' "$output" >"$ldd_out"
    [[ $output != *'not found'* ]] || fail "$class has unresolved libraries"
    [[ $output != *llama.cpp-experimental* ]] || fail "$class resolves into the experimental tree"
    while IFS= read -r line; do
        case $line in
            *libllama*' => '*|*libggml*' => '*|*libmtmd*' => '*)
                [[ $line == *"=> $tree/"* ]] || fail "$class runtime library escaped $tree: $line"
                ;;
        esac
    done <<<"$output"
    env -i PATH=/usr/bin:/bin LANG=C LC_ALL=C "$tree/llama-server" --version >"$version_out" 2>&1 ||
        fail "$class clean-environment --version failed"
    [[ $(sed -n '1p' "$version_out") == "$EXPECTED_VERSION_LINE" ]] ||
        fail "$class version mismatch"
}

command -v patchelf >/dev/null || fail 'patchelf is unavailable'
command -v jq >/dev/null || fail 'jq is unavailable'
require_source_identity
[[ ! -e $STAGE ]] || fail "sealed stage already exists: $STAGE"
[[ ! -e $ARTIFACT ]] || fail "packaging artifact already exists: $ARTIFACT"
mkdir -p "$STAGE_PARENT"
[[ $(stat -c %d "$STAGE_PARENT") == $(stat -c %d /mnt/raid0/llm/llama.cpp) ]] ||
    fail 'stage and production clone are not on the same filesystem'
available=$(df -PB1 "$STAGE_PARENT" | awk 'NR == 2 {print $4}')
[[ $available =~ ^[0-9]+$ && $available -ge 1073741824 ]] || fail 'less than 1 GiB free for packaging'

mkdir "$ARTIFACT"
TMP_STAGE=$(mktemp -d "$STAGE_PARENT/.production-consolidated-v9-0db32c06e.tmp.XXXXXX")
mkdir "$TMP_STAGE/cpu" "$TMP_STAGE/hip"
cp -a -- "$CPU_SOURCE" "$TMP_STAGE/cpu/bin"
cp -a -- "$HIP_SOURCE" "$TMP_STAGE/hip/bin"
require_tree "$TMP_STAGE/cpu/bin"
require_tree "$TMP_STAGE/hip/bin"
tree_hashes "$TMP_STAGE/cpu/bin" "$ARTIFACT/cpu-before.sha256"
tree_hashes "$TMP_STAGE/hip/bin" "$ARTIFACT/hip-before.sha256"
symlinks "$TMP_STAGE/cpu/bin" "$ARTIFACT/cpu-symlinks.txt"
symlinks "$TMP_STAGE/hip/bin" "$ARTIFACT/hip-symlinks.txt"
printf 'class\tpath\told_rpath\tnew_rpath\n' >"$ARTIFACT/rpath-rewrites.tsv"
rewrite_elf_rpaths cpu "$TMP_STAGE/cpu/bin" "$CPU_RPATH"
rewrite_elf_rpaths hip "$TMP_STAGE/hip/bin" "$HIP_RPATH"
cpu_elfs=$(require_rpaths "$TMP_STAGE/cpu/bin" "$CPU_RPATH")
hip_elfs=$(require_rpaths "$TMP_STAGE/hip/bin" "$HIP_RPATH")
tree_hashes "$TMP_STAGE/cpu/bin" "$ARTIFACT/cpu-after.sha256"
tree_hashes "$TMP_STAGE/hip/bin" "$ARTIFACT/hip-after.sha256"
patchelf --version >"$ARTIFACT/patchelf-version.txt"

mv "$TMP_STAGE" "$STAGE"
TMP_STAGE=''
stage_installed=1
verify_clean_binary cpu "$STAGE/cpu/bin" "$ARTIFACT/cpu-server.ldd.txt" "$ARTIFACT/cpu-version.txt" "$CPU_RPATH"
verify_clean_binary hip "$STAGE/hip/bin" "$ARTIFACT/hip-server.ldd.txt" "$ARTIFACT/hip-version.txt" "$HIP_RPATH"
cpu_sha=$(sha256sum -- "$STAGE/cpu/bin/llama-server" | awk '{print $1}')
hip_sha=$(sha256sum -- "$STAGE/hip/bin/llama-server" | awk '{print $1}')
find "$STAGE" -xtype l -print >"$ARTIFACT/dangling-symlinks.txt"
[[ ! -s $ARTIFACT/dangling-symlinks.txt ]] || fail 'sealed stage has dangling symlinks'

jq -n \
    --arg packaged_at "$PACKAGED_AT" \
    --arg candidate_branch "$EXPECTED_BRANCH" \
    --arg candidate_head "$EXPECTED_HEAD" \
    --arg candidate_version "$EXPECTED_VERSION_LINE" \
    --arg stage "$STAGE" \
    --arg cpu_source "$CPU_SOURCE" \
    --arg hip_source "$HIP_SOURCE" \
    --arg cpu_sha "$cpu_sha" \
    --arg hip_sha "$hip_sha" \
    --arg cpu_rpath "$CPU_RPATH" \
    --arg hip_rpath "$HIP_RPATH" \
    --argjson cpu_elfs "$cpu_elfs" \
    --argjson hip_elfs "$hip_elfs" '
    {
      schema: "epyc.kernel_v9.runtime_packaging.v1",
      status: "sealed",
      packaged_at: $packaged_at,
      candidate_branch: $candidate_branch,
      candidate_head: $candidate_head,
      candidate_version: $candidate_version,
      stage: $stage,
      source: {cpu: $cpu_source, hip: $hip_source},
      deployed_server_sha256: {cpu: $cpu_sha, hip: $hip_sha},
      rpath: {cpu: $cpu_rpath, hip: $hip_rpath},
      rewritten_elfs: {cpu: $cpu_elfs, hip: $hip_elfs},
      clean_environment_version_verified: true,
      clean_environment_ldd_verified: true,
      experimental_runpath_hits: 0,
      dangling_symlinks: 0,
      production_mutated: false
    }' >"$ARTIFACT/summary.json"

completed=1
printf 'Sealed v9 runtime: %s\nProvenance: %s\n' "$STAGE" "$ARTIFACT/summary.json"

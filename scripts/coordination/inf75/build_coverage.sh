#!/bin/bash
# AKX-P1c CPU coverage build helper; invoke only as the command of a granted
# filler_run engine holding its build-role region lock. This is NOT a launcher:
# it cannot grant, qualify, or schedule itself. HIP requires a separate recipe.
set -euo pipefail

printf '%s\n' 'REFUSED: prototype build recipe requires parity, linkage, deadline and rowflow review' >&2
exit 78

refuse() { printf 'REFUSED: %s\n' "$*" >&2; exit 64; }
[[ $# == 6 ]] || refuse 'usage: build_coverage.sh SOURCE COMMIT SCRATCH CC CC_SHA256 CXX_SHA256'
source_dir=$(realpath -e -- "$1")
commit=$2
scratch=$(realpath -e -- "$3")
cc=$(realpath -e -- "$4")
cc_sha=$5
cxx_sha=$6
cxx=$(realpath -e -- "${cc%/*}/g++")
case "$commit" in
  ef81196d5bdd4190b46dff4ae7eecc333a46c8ce|2516c9807b8a92d472c8e75a0a1ce8558d2e34a7) ;;
  *) refuse 'commit must be a full P1c source commit' ;;
esac
[[ $cc_sha =~ ^[0-9a-f]{64}$ && $cxx_sha =~ ^[0-9a-f]{64}$ ]] || refuse 'compiler digests must be SHA-256'
[[ "$source_dir" == /mnt/raid0/llm/tmp/* && "$scratch" == /mnt/raid0/llm/tmp/* && "$scratch" != "$source_dir"/* ]] || refuse 'source and separate scratch must be under tmp'
[[ -n ${FILLER_DEADLINE:-} && ${FILLER_DEADLINE} =~ ^[0-9]+$ && $(date +%s) -lt $FILLER_DEADLINE ]] || refuse 'active engine deadline required'
[[ ${AKX_BUILD_JOBS:-} =~ ^[1-9][0-9]*$ && ${FILLER_THREADS:-} =~ ^[1-9][0-9]*$ ]] || refuse 'bounded job and granted thread counts required'
(( AKX_BUILD_JOBS <= FILLER_THREADS )) || refuse 'build jobs exceed granted threads'
[[ $(git -C "$source_dir" rev-parse HEAD) == "$commit" ]] || refuse 'source HEAD mismatch'
[[ -z $(git -C "$source_dir" status --porcelain --untracked-files=all) ]] || refuse 'source checkout has tracked or untracked changes'
[[ -z $(git -C "$source_dir" ls-tree -r "$commit" | awk '$1 == "160000" { print; exit }') ]] || refuse 'submodules require separate source custody'
[[ $(sha256sum "$cc" | cut -d' ' -f1) == "$cc_sha" && $(sha256sum "$cxx" | cut -d' ' -f1) == "$cxx_sha" ]] || refuse 'compiler digest mismatch'
[[ $($cc -dumpmachine) == x86_64* && $($cc -dumpversion) == "$($cxx -dumpversion)" ]] || refuse 'expected matching x86-64 GCC toolchain'
[[ ! -e "$scratch/build" && ! -e "$scratch/src" && ! -e "$scratch/BUILD-RECEIPT.sha256" ]] || refuse 'scratch already used'

# The keeper owns resource admission and invokes this helper inside its lock.
# Capture full invocation and tool identity; do not modify the source checkout.
mkdir "$scratch/build" "$scratch/src"
git -C "$source_dir" archive "$commit" | tar -xf - -C "$scratch/src"
printf '%s\n' "$commit" > "$scratch/source-commit.txt"
printf '%s  %s\n%s  %s\n' "$cc_sha" "$cc" "$cxx_sha" "$cxx" > "$scratch/compiler-sha256.txt"
"$cc" --version > "$scratch/cc-version.txt"
"$cxx" --version > "$scratch/cxx-version.txt"
cmake --version > "$scratch/cmake-version.txt"
cmake -S "$scratch/src" -B "$scratch/build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER="$cc" -DCMAKE_CXX_COMPILER="$cxx" \
  -DCMAKE_C_FLAGS='--coverage -fprofile-update=atomic' \
  -DCMAKE_CXX_FLAGS='--coverage -fprofile-update=atomic' \
  -DCMAKE_EXE_LINKER_FLAGS=--coverage -DCMAKE_SHARED_LINKER_FLAGS=--coverage \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DGGML_HIP=OFF -DGGML_BLAS=OFF -DGGML_NATIVE=ON \
  > "$scratch/configure.log" 2>&1
cmake --build "$scratch/build" --target llama-server --parallel "${AKX_BUILD_JOBS:?bounded AKX_BUILD_JOBS required}" > "$scratch/build.log" 2>&1
[[ -x "$scratch/build/bin/llama-server" ]] || refuse 'server missing'
[[ -n $(find "$scratch/build" -name '*.gcno' -print -quit) ]] || refuse 'coverage notes absent'
[[ -z $(git -C "$source_dir" status --porcelain --untracked-files=all) ]] || refuse 'source changed during build'
(
  cd "$scratch"
  find build/bin -type f \( -name 'llama-server' -o -name '*.so' -o -name '*.so.*' \) -print0 | sort -z | xargs -0 -r sha256sum
  sha256sum source-commit.txt compiler-sha256.txt cc-version.txt cxx-version.txt cmake-version.txt build/CMakeCache.txt build/compile_commands.json configure.log build.log
) > "$scratch/BUILD-RECEIPT.sha256.tmp"
[[ -s "$scratch/BUILD-RECEIPT.sha256.tmp" ]] || refuse 'empty receipt'
mv "$scratch/BUILD-RECEIPT.sha256.tmp" "$scratch/BUILD-RECEIPT.sha256"
printf 'CPU coverage build complete: %s\n' "$scratch/BUILD-RECEIPT.sha256"

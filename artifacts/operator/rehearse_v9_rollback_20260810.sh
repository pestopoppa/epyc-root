#!/bin/bash
# Exercise the v8 -> v9 runtime rename/switch/rollback sequence in a disposable
# same-filesystem clone. The live production source and build trees are read-only.
set -euo pipefail

ROOT=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
PRODUCTION=/mnt/raid0/llm/llama.cpp
STAGE=/mnt/raid0/llm/kernel-runtime-stages/production-consolidated-v9-0db32c06e
PROVENANCE="$ROOT/artifacts/operator/v9-runtime-packaging-20260810T224026Z-0db32c06e/summary.json"
V8_BRANCH=production-consolidated-v8
V8_HEAD=67a433bf45a8a091d83b4ea0b32ff0735fd51800
V9_BRANCH=production-consolidated-v9
V9_HEAD=0db32c06e3e550065b78311a6031ef3dd2c4f27c
EXPECTED_VERSION_LINE='version: 10125 (0db32c06e)'
CPU_SHA=8ebb1355593121a231735d7b58ad076f4539d2c5e3847fa09d2922fa8a980499
HIP_SHA=21cfb750dc0ba4b3add0674fcb9dd061d77b3604ebf8e1d063ba0e2c51902feb
REHEARSAL_PARENT=/mnt/raid0/llm/kernel-cutover-rehearsals

: "${REHEARSED_AT:?set REHEARSED_AT to an RFC3339 timestamp with timezone}"
: "${REHEARSAL_ID:?set REHEARSAL_ID to a unique letters/numbers/dot/underscore/dash identifier}"
[[ $REHEARSED_AT =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$ ]] || {
    printf 'REHEARSED_AT must be an RFC3339 timestamp with timezone\n' >&2
    exit 2
}
[[ $REHEARSAL_ID =~ ^[A-Za-z0-9._-]+$ ]] || {
    printf 'REHEARSAL_ID contains unsupported characters\n' >&2
    exit 2
}

ARTIFACT_REL="artifacts/operator/v9-rollback-rehearsal-$REHEARSAL_ID"
ARTIFACT="$ROOT/$ARTIFACT_REL"
SANDBOX=''
completed=0

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    local status=$?
    trap - EXIT
    if [[ -n $SANDBOX && -d $SANDBOX ]]; then
        rm -rf -- "$SANDBOX"
    fi
    if (( ! completed )) && [[ -d $ARTIFACT ]]; then
        rm -rf -- "$ARTIFACT"
    fi
    exit "$status"
}
trap cleanup EXIT

tree_manifest() {
    local tree=$1 output=$2
    (
        cd "$tree"
        find . -type f -print0 | LC_ALL=C sort -z | xargs -0r sha256sum --
        find . -type l -printf 'symlink %p -> %l\n' | LC_ALL=C sort
    ) >"$output"
}

require_manifest() {
    local tree=$1 expected=$2 actual=$3
    tree_manifest "$tree" "$actual"
    cmp -s "$expected" "$actual" || fail "manifest mismatch for $tree"
}

require_identity() {
    local repo=$1 branch=$2 head=$3
    [[ $(git -C "$repo" branch --show-current) == "$branch" ]] || fail "$repo is not on $branch"
    [[ $(git -C "$repo" rev-parse HEAD) == "$head" ]] || fail "$repo is not at $head"
    git -C "$repo" diff --quiet || fail "$repo tracked worktree is dirty"
    git -C "$repo" diff --cached --quiet || fail "$repo index is dirty"
}

require_runtime() {
    local tree=$1 expected_sha=$2 label=$3 output
    [[ -x $tree/llama-server ]] || fail "$label llama-server missing"
    [[ $(sha256sum -- "$tree/llama-server" | awk '{print $1}') == "$expected_sha" ]] ||
        fail "$label llama-server hash mismatch"
    [[ $(env -i PATH=/usr/bin:/bin LANG=C LC_ALL=C "$tree/llama-server" --version 2>&1 | sed -n '1p') == "$EXPECTED_VERSION_LINE" ]] ||
        fail "$label version mismatch"
    output=$(env -i PATH=/usr/bin:/bin LANG=C LC_ALL=C ldd "$tree/llama-server") || fail "$label ldd failed"
    [[ $output != *'not found'* && $output != *llama.cpp-experimental* ]] || fail "$label linkage is not clean"
}

require_identity "$PRODUCTION" "$V8_BRANCH" "$V8_HEAD"
[[ -d $STAGE/cpu/bin && -d $STAGE/hip/bin ]] || fail 'sealed v9 stage is missing'
jq -e --arg head "$V9_HEAD" --arg stage "$STAGE" --arg cpu "$CPU_SHA" --arg hip "$HIP_SHA" '
    .schema == "epyc.kernel_v9.runtime_packaging.v1" and .status == "sealed" and
    .candidate_head == $head and .stage == $stage and
    .deployed_server_sha256 == {cpu: $cpu, hip: $hip} and
    .clean_environment_version_verified == true and .clean_environment_ldd_verified == true
    ' "$PROVENANCE" >/dev/null || fail 'sealed provenance predicate failed'
[[ ! -e $ARTIFACT ]] || fail "artifact already exists: $ARTIFACT"
mkdir -p "$REHEARSAL_PARENT"
[[ $(stat -c %d "$REHEARSAL_PARENT") == $(stat -c %d "$PRODUCTION") ]] ||
    fail 'rehearsal and production are not on the same filesystem'
mkdir "$ARTIFACT"
SANDBOX=$(mktemp -d "$REHEARSAL_PARENT/v9-rollback-$REHEARSAL_ID.XXXXXX")

git clone --shared --no-checkout "$PRODUCTION" "$SANDBOX/source" >/dev/null
git -C "$SANDBOX/source" switch "$V8_BRANCH" >/dev/null
git -C "$SANDBOX/source" cat-file -e "$V9_HEAD^{commit}" 2>/dev/null ||
    git -C "$SANDBOX/source" fetch "$PRODUCTION" "$V9_HEAD" >/dev/null
cp -al -- "$PRODUCTION/build" "$SANDBOX/source/build"
cp -al -- "$PRODUCTION/build-hip" "$SANDBOX/source/build-hip"
mkdir "$SANDBOX/stage"
cp -al -- "$STAGE/cpu" "$SANDBOX/stage/cpu"
cp -al -- "$STAGE/hip" "$SANDBOX/stage/hip"

tree_manifest "$SANDBOX/source/build" "$ARTIFACT/v8-cpu.manifest"
tree_manifest "$SANDBOX/source/build-hip" "$ARTIFACT/v8-hip.manifest"
tree_manifest "$SANDBOX/stage/cpu/bin" "$ARTIFACT/v9-cpu.manifest"
tree_manifest "$SANDBOX/stage/hip/bin" "$ARTIFACT/v9-hip.manifest"
mkdir "$SANDBOX/rollback" "$SANDBOX/failure"

# Same rename/install/source-switch sequence as the live transaction.
mv "$SANDBOX/source/build" "$SANDBOX/rollback/build"
mv "$SANDBOX/source/build-hip" "$SANDBOX/rollback/build-hip"
mkdir "$SANDBOX/source/build" "$SANDBOX/source/build-hip"
mv "$SANDBOX/stage/cpu/bin" "$SANDBOX/source/build/bin"
mv "$SANDBOX/stage/hip/bin" "$SANDBOX/source/build-hip/bin"
require_manifest "$SANDBOX/source/build/bin" "$ARTIFACT/v9-cpu.manifest" "$ARTIFACT/v9-cpu-installed.manifest"
require_manifest "$SANDBOX/source/build-hip/bin" "$ARTIFACT/v9-hip.manifest" "$ARTIFACT/v9-hip-installed.manifest"
require_runtime "$SANDBOX/source/build/bin" "$CPU_SHA" 'installed CPU'
require_runtime "$SANDBOX/source/build-hip/bin" "$HIP_SHA" 'installed HIP'
git -C "$SANDBOX/source" branch "$V9_BRANCH" "$V9_HEAD"
git -C "$SANDBOX/source" switch "$V9_BRANCH" >/dev/null
require_identity "$SANDBOX/source" "$V9_BRANCH" "$V9_HEAD"

# Inject the pre-governance failure, preserve failed v9, and restore exact v8.
mv "$SANDBOX/source/build-hip" "$SANDBOX/failure/build-hip"
mv "$SANDBOX/rollback/build-hip" "$SANDBOX/source/build-hip"
mv "$SANDBOX/source/build" "$SANDBOX/failure/build"
mv "$SANDBOX/rollback/build" "$SANDBOX/source/build"
git -C "$SANDBOX/source" switch "$V8_BRANCH" >/dev/null
require_identity "$SANDBOX/source" "$V8_BRANCH" "$V8_HEAD"
require_manifest "$SANDBOX/source/build" "$ARTIFACT/v8-cpu.manifest" "$ARTIFACT/v8-cpu-restored.manifest"
require_manifest "$SANDBOX/source/build-hip" "$ARTIFACT/v8-hip.manifest" "$ARTIFACT/v8-hip-restored.manifest"
require_manifest "$SANDBOX/failure/build/bin" "$ARTIFACT/v9-cpu.manifest" "$ARTIFACT/v9-cpu-preserved.manifest"
require_manifest "$SANDBOX/failure/build-hip/bin" "$ARTIFACT/v9-hip.manifest" "$ARTIFACT/v9-hip-preserved.manifest"

jq -n \
    --arg rehearsed_at "$REHEARSED_AT" \
    --arg v8_branch "$V8_BRANCH" --arg v8_head "$V8_HEAD" \
    --arg v9_branch "$V9_BRANCH" --arg v9_head "$V9_HEAD" \
    --arg cpu_sha "$CPU_SHA" --arg hip_sha "$HIP_SHA" '
    {
      schema: "epyc.kernel_v9.rollback_rehearsal.v1",
      status: "pass",
      rehearsed_at: $rehearsed_at,
      live_production_mutated: false,
      transaction: {
        source_before: {branch: $v8_branch, head: $v8_head},
        candidate_installed: {branch: $v9_branch, head: $v9_head},
        injected_failure_phase: "after_runtime_install_and_source_switch_before_governance_commit",
        source_after_rollback: {branch: $v8_branch, head: $v8_head}
      },
      runtime: {
        installed_v9_hashes: {cpu: $cpu_sha, hip: $hip_sha},
        v8_manifests_restored_exactly: true,
        failed_v9_manifests_preserved_exactly: true,
        clean_environment_linkage_verified: true
      },
      disposable_sandbox_removed_after_verification: true
    }' >"$ARTIFACT/summary.json"

completed=1
printf 'Rollback rehearsal passed: %s\n' "$ARTIFACT/summary.json"

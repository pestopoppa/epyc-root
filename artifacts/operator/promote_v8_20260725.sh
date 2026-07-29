#!/bin/bash
# One-shot v7 -> v8 cutover.  This consumes the sealed, relocatable runtime
# stage; it never copies a runtime from the experimental worktree.
set -euo pipefail

ROOT=/mnt/raid0/llm/epyc-root
CANONICAL=/mnt/raid0/llm/llama.cpp
V7_BRANCH=production-consolidated-v7
V7_HEAD=6ad45fa3ff6718c07c000061dbc6e29c1771f6e3
V8_BRANCH=production-consolidated-v8
V8_HEAD=67a433bf45a8a091d83b4ea0b32ff0735fd51800
EXPECTED_VERSION_LINE='version: 10107 (67a433bf4)'
CPU_SHA=a4b667163022aa166ade7c0e00fa4e775b37662e02c10da7642c8c23a4d6b414
HIP_SHA=112c560f1c978c584a9899539851348a0ce1e05cde458061c281758aff066882
CPU_RPATH='$ORIGIN'
HIP_RPATH='$ORIGIN:/opt/rocm/lib'
STAGE="$CANONICAL/.v8-runtime-stage-67a433bf4"
PROVENANCE="$ROOT/artifacts/operator/v8-runtime-packaging-20260725T183000Z/summary.json"
ROOT_VERIFIER_REL=scripts/session/verify_llama_cpp.sh
ATTESTATION_REL=handoffs/active/laguna-pgpu1-v8-promotion-attestation.json

: "${PROMOTED_AT:?set PROMOTED_AT to the timezone-bearing v8 promotion timestamp}"
: "${CUTOVER_ID:?set CUTOVER_ID to a unique cutover identifier}"
: "${ROOT_BASE_HEAD:?set ROOT_BASE_HEAD to the exact pre-cutover epyc-root HEAD}"
[[ $PROMOTED_AT =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$ ]] || {
    printf 'PROMOTED_AT must be an RFC3339 timestamp with timezone\n' >&2
    exit 2
}
[[ $CUTOVER_ID =~ ^[A-Za-z0-9._-]+$ ]] || {
    printf 'CUTOVER_ID may contain only letters, numbers, dot, underscore, and dash\n' >&2
    exit 2
}
[[ $ROOT_BASE_HEAD =~ ^[0-9a-f]{40}$ ]] || {
    printf 'ROOT_BASE_HEAD must be a lowercase 40-hex commit\n' >&2
    exit 2
}

source "$ROOT/scripts/utils/agent_log.sh"
agent_session_start "v8 reversible production cutover"
agent_task_start "Promote sealed v8 runtime trees" "Journaled v7-to-v8 transaction with verified rollback before governance commit"

JOURNAL_DIR="$ROOT/artifacts/operator/v8-cutover-$CUTOVER_ID"
JOURNAL="$JOURNAL_DIR/journal.json"
JOURNAL_TMP="$JOURNAL_DIR/journal.json.tmp"
V7_CPU_MANIFEST="$JOURNAL_DIR/v7-cpu.manifest"
V7_HIP_MANIFEST="$JOURNAL_DIR/v7-hip.manifest"
STAGE_CPU_MANIFEST="$JOURNAL_DIR/v8-cpu.manifest"
STAGE_HIP_MANIFEST="$JOURNAL_DIR/v8-hip.manifest"
V7_BUILD_BACKUP="$CANONICAL/build-v7-rollback-$CUTOVER_ID"
V7_HIP_BACKUP="$CANONICAL/build-hip-v7-rollback-$CUTOVER_ID"
FAILED_V8_BUILD="$CANONICAL/build-v8-failed-$CUTOVER_ID"
FAILED_V8_HIP="$CANONICAL/build-hip-v8-failed-$CUTOVER_ID"

cpu_backed_up=0
hip_backed_up=0
cpu_installed=0
hip_installed=0
root_committed=0
completed=0
journal_ready=0
cutover_started=0

exec 9>"$ROOT/artifacts/operator/.v8-cutover.lock"
flock -n 9 || {
    printf 'Another cooperating v8 cutover holds %s\n' "$ROOT/artifacts/operator/.v8-cutover.lock" >&2
    exit 1
}

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

is_exact_tracked_clean() {
    local repo=$1 branch=$2 head=$3
    [[ $(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null) == "$branch" ]] &&
        [[ $(git -C "$repo" rev-parse HEAD 2>/dev/null) == "$head" ]] &&
        git -C "$repo" diff --quiet &&
        git -C "$repo" diff --cached --quiet
}

require_exact_tracked_clean() {
    is_exact_tracked_clean "$@" || fail "$1 is not clean at the required $2 identity"
}

runtime_users_present() {
    local pid exe found=1
    for pid_dir in /proc/[0-9]*; do
        pid=${pid_dir##*/}
        exe=$(readlink "$pid_dir/exe" 2>/dev/null || true)
        case ${exe##*/} in
            llama-server|llama-cli|llama-bench)
                printf '%s %s\n' "$pid" "$exe" >&2
                found=0
                ;;
        esac
    done
    if pgrep -af '[a]utopilot|[a]uto_pilot' >&2; then
        found=0
    fi
    if command -v lsof >/dev/null && lsof -t /dev/kfd >/dev/null 2>&1; then
        lsof /dev/kfd >&2 || true
        found=0
    fi
    return "$found"
}

require_no_runtime_users() {
    if runtime_users_present; then
        fail "runtime, AutoPilot, or /dev/kfd users are still active"
    fi
}

require_tree() {
    local tree=$1
    [[ -d "$tree" && ! -L "$tree" ]] || fail "runtime tree is missing or is a symlink: $tree"
    [[ -x "$tree/llama-server" ]] || fail "missing executable llama-server: $tree"
    if find "$tree" -xtype l -print -quit | grep -q .; then
        find "$tree" -xtype l -print >&2
        fail "dangling symlink in $tree"
    fi
}

tree_manifest() {
    local tree=$1 output=$2
    (
        cd "$tree"
        find . -type f -print0 | LC_ALL=C sort -z | xargs -0r sha256sum --
        find . -type l -printf 'symlink %p -> %l\n' | LC_ALL=C sort
    ) >"$output"
}

verify_manifest() {
    manifest_matches "$@" || fail "runtime tree manifest mismatch: $1"
}

manifest_matches() {
    local tree=$1
    local expected=$2
    local actual="$expected.actual"
    tree_manifest "$tree" "$actual"
    cmp -s "$expected" "$actual"
    local result=$?
    rm -f "$actual"
    return "$result"
}

require_server_hash() {
    local server=$1 expected=$2 label=$3
    [[ $(sha256sum -- "$server" | awk '{print $1}') == "$expected" ]] || fail "$label server hash mismatch"
}

rpath_of() {
    readelf -d "$1" | sed -nE 's/.*Library (rpath|runpath): \[(.*)\].*/\2/p'
}

require_rpath() {
    local server=$1 expected=$2 label=$3 actual
    actual=$(rpath_of "$server")
    [[ $actual == "$expected" ]] || fail "$label RPATH mismatch: expected '$expected', got '${actual:-none}'"
}

require_clean_ldd() {
    local server=$1 expected_dir=$2 label=$3 output line
    output=$(env -i PATH=/usr/bin:/bin LANG=C LC_ALL=C ldd "$server") || fail "$label ldd failed in a clean environment"
    [[ $output != *'not found'* ]] || fail "$label has unresolved dynamic libraries"
    [[ $output != *'/llama.cpp-experimental/'* ]] || fail "$label resolves a library from the experimental worktree"
    while IFS= read -r line; do
        case $line in
            *libllama*' => '*|*libggml*' => '*|*libmtmd*' => '*)
                [[ $line == *"=> $expected_dir/"* ]] || fail "$label resolves a runtime library outside $expected_dir: $line"
                ;;
        esac
    done <<<"$output"
}

require_version_clean() {
    local server=$1 label=$2 version_line
    version_line=$(env -i PATH=/usr/bin:/bin LANG=C LC_ALL=C "$server" --version 2>&1 | sed -n '1p')
    [[ $version_line == "$EXPECTED_VERSION_LINE" ]] || fail "$label version mismatch: expected '$EXPECTED_VERSION_LINE', got '$version_line'"
}

require_same_device_and_space() {
    local canonical_device path path_device available
    canonical_device=$(stat -c %d "$CANONICAL")
    for path in "$STAGE" "$STAGE/cpu/bin" "$STAGE/hip/bin" "$CANONICAL/build" "$CANONICAL/build-hip"; do
        path_device=$(stat -c %d "$path")
        [[ $canonical_device == "$path_device" ]] || fail "$path is not on the canonical filesystem"
    done
    available=$(df -PB1 "$CANONICAL" | awk 'NR == 2 {print $4}')
    [[ $available =~ ^[0-9]+$ && $available -ge 1073741824 ]] || fail "less than 1 GiB free on the canonical filesystem"
}

write_journal() {
    local phase=$1
    cat >"$JOURNAL_TMP" <<EOF
{
  "schema": "epyc.kernel_cutover_journal.v1",
  "cutover_id": "$CUTOVER_ID",
  "promoted_at": "$PROMOTED_AT",
  "phase": "$phase",
  "production_branch": "$V8_BRANCH",
  "production_head": "$V8_HEAD",
  "rollback_branch": "$V7_BRANCH",
  "rollback_head": "$V7_HEAD",
  "stage": "$STAGE",
  "rollback_build_dir": "$V7_BUILD_BACKUP",
  "rollback_hip_build_dir": "$V7_HIP_BACKUP",
  "failed_v8_build_dir": "$FAILED_V8_BUILD",
  "failed_v8_hip_dir": "$FAILED_V8_HIP",
  "cpu_backed_up": $cpu_backed_up,
  "hip_backed_up": $hip_backed_up,
  "cpu_installed": $cpu_installed,
  "hip_installed": $hip_installed,
  "root_governance_committed": $root_committed,
  "completed": $completed
}
EOF
    mv -f "$JOURNAL_TMP" "$JOURNAL"
    sync -f "$JOURNAL"
    sync -f "$JOURNAL_DIR"
}

require_root_governance() {
    local staged expected
    [[ $(git -C "$ROOT" rev-parse HEAD) == "$ROOT_BASE_HEAD" ]] || fail "epyc-root HEAD is not ROOT_BASE_HEAD"
    staged=$(git -C "$ROOT" diff --cached --name-only | LC_ALL=C sort)
    expected=$(printf '%s\n%s\n' "$ATTESTATION_REL" "$ROOT_VERIFIER_REL" | LC_ALL=C sort)
    [[ $staged == "$expected" ]] || fail "only $ROOT_VERIFIER_REL and $ATTESTATION_REL may be staged in epyc-root"
    git -C "$ROOT" diff --quiet -- "$ROOT_VERIFIER_REL" "$ATTESTATION_REL" || fail "governance files have unstaged changes"
    grep -Fq "EXPECTED_BRANCH=\"$V8_BRANCH\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier does not name $V8_BRANCH"
    grep -Fq "EXPECTED_COMMIT=\"$V8_HEAD\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier does not name $V8_HEAD"
    grep -Fq "EXPECTED_VERSION_LINE=\"$EXPECTED_VERSION_LINE\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier has the wrong v8 version"
    grep -Fq "EXPECTED_CPU_SERVER_SHA256=\"$CPU_SHA\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier has the wrong CPU SHA"
    grep -Fq "EXPECTED_HIP_SERVER_SHA256=\"$HIP_SHA\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier has the wrong HIP SHA"
    jq -e \
        --arg branch "$V8_BRANCH" --arg head "$V8_HEAD" --arg promoted_at "$PROMOTED_AT" \
        --arg hip_sha "$HIP_SHA" --arg v7_branch "$V7_BRANCH" --arg v7_head "$V7_HEAD" \
        --arg server "$CANONICAL/build-hip/bin/llama-server" '
        .schema == "epyc.kernel_promotion_attestation.v1" and
        .status == "production_promoted_pending_gpu_certification" and
        .production_branch == $branch and .production_head == $head and
        .frozen == false and .promoted_at == $promoted_at and
        .server_binary.path == $server and .server_binary.sha256 == $hip_sha and
        .rollback.branch == $v7_branch and .rollback.head == $v7_head and
        .rollback.backup_ref == ("refs/heads/" + $v7_branch) and
        .rollback.source_ref == ("refs/heads/" + $branch)
        ' "$ROOT/$ATTESTATION_REL" >/dev/null || fail "staged provisional P-GPU attestation does not bind this exact promotion"
}

verify_root_restored() {
    [[ $(git -C "$ROOT" rev-parse HEAD) == "$ROOT_BASE_HEAD" ]] || return 1
    git -C "$ROOT" diff --quiet "$ROOT_BASE_HEAD" -- "$ROOT_VERIFIER_REL" "$ATTESTATION_REL" || return 1
    git -C "$ROOT" diff --cached --quiet "$ROOT_BASE_HEAD" -- "$ROOT_VERIFIER_REL" "$ATTESTATION_REL"
}

rollback() {
    local status=$? rollback_ok=1
    trap - EXIT
    if (( completed )); then
        agent_task_end "Promote sealed v8 runtime trees" success
        exit "$status"
    fi
    if (( root_committed )) || [[ $(git -C "$ROOT" rev-parse HEAD 2>/dev/null) != "$ROOT_BASE_HEAD" ]]; then
        printf 'ERROR: root governance commit succeeded; preserving v8 and journal for manual recovery.\n' >&2
        write_journal post_root_commit_failure || true
        agent_task_end "Promote sealed v8 runtime trees" failure
        exit 2
    fi
    if (( ! cutover_started )); then
        if (( journal_ready )); then
            write_journal aborted_before_production_mutation || true
        fi
        agent_task_end "Promote sealed v8 runtime trees" failure
        exit "$status"
    fi

    set +e
    printf 'Cutover failed before the root governance commit; attempting verified rollback.\n' >&2
    write_journal rollback_started || rollback_ok=0
    if runtime_users_present; then
        printf 'ERROR: users appeared during cutover; preserving runtime directories rather than moving them.\n' >&2
        rollback_ok=0
    else
        # Detect the filesystem state, not only shell flags: a signal can land
        # between a successful rename and the corresponding flag assignment.
        if [[ -e "$V7_HIP_BACKUP" ]]; then
            if [[ -e "$CANONICAL/build-hip" ]]; then
                mv "$CANONICAL/build-hip" "$FAILED_V8_HIP" || rollback_ok=0
            fi
            mv "$V7_HIP_BACKUP" "$CANONICAL/build-hip" || rollback_ok=0
            manifest_matches "$CANONICAL/build-hip" "$V7_HIP_MANIFEST" || rollback_ok=0
        fi
        if [[ -e "$V7_BUILD_BACKUP" ]]; then
            if [[ -e "$CANONICAL/build" ]]; then
                mv "$CANONICAL/build" "$FAILED_V8_BUILD" || rollback_ok=0
            fi
            mv "$V7_BUILD_BACKUP" "$CANONICAL/build" || rollback_ok=0
            manifest_matches "$CANONICAL/build" "$V7_CPU_MANIFEST" || rollback_ok=0
        fi
    fi
    if [[ $(git -C "$CANONICAL" rev-parse --abbrev-ref HEAD 2>/dev/null) != "$V7_BRANCH" ]]; then
        git -C "$CANONICAL" switch "$V7_BRANCH" || rollback_ok=0
    fi
    is_exact_tracked_clean "$CANONICAL" "$V7_BRANCH" "$V7_HEAD" || rollback_ok=0
    git -C "$ROOT" restore --source "$ROOT_BASE_HEAD" --staged --worktree -- "$ROOT_VERIFIER_REL" "$ATTESTATION_REL" || rollback_ok=0
    verify_root_restored || rollback_ok=0
    if (( rollback_ok )); then
        write_journal rolled_back || rollback_ok=0
    else
        write_journal rollback_incomplete || true
    fi
    agent_task_end "Promote sealed v8 runtime trees" failure
    if (( rollback_ok )); then
        exit "$status"
    fi
    printf 'ERROR: rollback is incomplete; inspect %s before touching production.\n' "$JOURNAL" >&2
    exit 2
}
trap rollback EXIT

[[ ! -e "$JOURNAL_DIR" && ! -e "$V7_BUILD_BACKUP" && ! -e "$V7_HIP_BACKUP" ]] || fail "cutover journal or rollback directory already exists for $CUTOVER_ID"
[[ ! -e "$FAILED_V8_BUILD" && ! -e "$FAILED_V8_HIP" ]] || fail "failed-v8 preservation directory already exists for $CUTOVER_ID"
mkdir "$JOURNAL_DIR"

require_exact_tracked_clean "$CANONICAL" "$V7_BRANCH" "$V7_HEAD"
git -C "$CANONICAL" rev-parse --verify --quiet "$V8_HEAD^{commit}" >/dev/null || fail "v8 candidate commit is unavailable"
require_tree "$STAGE/cpu/bin"
require_tree "$STAGE/hip/bin"
require_same_device_and_space
jq -e --arg head "$V8_HEAD" --arg stage "$STAGE" --arg cpu "$CPU_SHA" --arg hip "$HIP_SHA" '
    .schema == "epyc.kernel_v8.runtime_packaging.v1" and
    .candidate_head == $head and .stage == $stage and
    .deployed_server_sha256.cpu == $cpu and .deployed_server_sha256.hip == $hip and
    .rpath.cpu == "$ORIGIN" and .rpath.hip == "$ORIGIN:/opt/rocm/lib" and
    .clean_environment_version_verified == true and .clean_environment_ldd_verified == true and
    .experimental_runpath_hits == 0 and .dangling_symlinks == 0
    ' "$PROVENANCE" >/dev/null || fail "runtime packaging provenance does not bind this exact sealed stage"
require_server_hash "$STAGE/cpu/bin/llama-server" "$CPU_SHA" "sealed CPU"
require_server_hash "$STAGE/hip/bin/llama-server" "$HIP_SHA" "sealed HIP"
require_rpath "$STAGE/cpu/bin/llama-server" "$CPU_RPATH" "sealed CPU"
require_rpath "$STAGE/hip/bin/llama-server" "$HIP_RPATH" "sealed HIP"
require_clean_ldd "$STAGE/cpu/bin/llama-server" "$STAGE/cpu/bin" "sealed CPU"
require_clean_ldd "$STAGE/hip/bin/llama-server" "$STAGE/hip/bin" "sealed HIP"
require_version_clean "$STAGE/cpu/bin/llama-server" "sealed CPU"
require_version_clean "$STAGE/hip/bin/llama-server" "sealed HIP"
require_root_governance
require_no_runtime_users
tree_manifest "$CANONICAL/build" "$V7_CPU_MANIFEST"
tree_manifest "$CANONICAL/build-hip" "$V7_HIP_MANIFEST"
tree_manifest "$STAGE/cpu/bin" "$STAGE_CPU_MANIFEST"
tree_manifest "$STAGE/hip/bin" "$STAGE_HIP_MANIFEST"
write_journal prepared
journal_ready=1

printf '%s\n' "This will promote $V8_HEAD to $V8_BRANCH, consume the sealed v8 runtime stage, and commit only the staged governance files."
read -r -p 'Type PROMOTE-V8 to continue: ' confirmation
[[ $confirmation == PROMOTE-V8 ]] || fail "operator confirmation not provided"

# Revalidate the mutable boundaries immediately before the first production mutation.
require_exact_tracked_clean "$CANONICAL" "$V7_BRANCH" "$V7_HEAD"
require_root_governance
require_no_runtime_users

if git -C "$CANONICAL" show-ref --verify --quiet "refs/heads/$V8_BRANCH"; then
    [[ $(git -C "$CANONICAL" rev-parse "$V8_BRANCH") == "$V8_HEAD" ]] || fail "$V8_BRANCH already names a different commit"
else
    cutover_started=1
    git -C "$CANONICAL" branch "$V8_BRANCH" "$V8_HEAD"
fi
cutover_started=1
write_journal v8_ref_ready

mv "$CANONICAL/build" "$V7_BUILD_BACKUP"
cpu_backed_up=1
write_journal v7_cpu_backed_up
mv "$CANONICAL/build-hip" "$V7_HIP_BACKUP"
hip_backed_up=1
write_journal v7_hip_backed_up
mkdir "$CANONICAL/build" "$CANONICAL/build-hip"

mv "$STAGE/cpu/bin" "$CANONICAL/build/bin"
cpu_installed=1
write_journal v8_cpu_installed
mv "$STAGE/hip/bin" "$CANONICAL/build-hip/bin"
hip_installed=1
write_journal v8_hip_installed

require_tree "$CANONICAL/build/bin"
require_tree "$CANONICAL/build-hip/bin"
verify_manifest "$CANONICAL/build/bin" "$STAGE_CPU_MANIFEST"
verify_manifest "$CANONICAL/build-hip/bin" "$STAGE_HIP_MANIFEST"
require_server_hash "$CANONICAL/build/bin/llama-server" "$CPU_SHA" "installed CPU"
require_server_hash "$CANONICAL/build-hip/bin/llama-server" "$HIP_SHA" "installed HIP"
require_rpath "$CANONICAL/build/bin/llama-server" "$CPU_RPATH" "installed CPU"
require_rpath "$CANONICAL/build-hip/bin/llama-server" "$HIP_RPATH" "installed HIP"
require_clean_ldd "$CANONICAL/build/bin/llama-server" "$CANONICAL/build/bin" "installed CPU"
require_clean_ldd "$CANONICAL/build-hip/bin/llama-server" "$CANONICAL/build-hip/bin" "installed HIP"
require_version_clean "$CANONICAL/build/bin/llama-server" "installed CPU"
require_version_clean "$CANONICAL/build-hip/bin/llama-server" "installed HIP"

git -C "$CANONICAL" switch "$V8_BRANCH"
require_exact_tracked_clean "$CANONICAL" "$V8_BRANCH" "$V8_HEAD"
write_journal v8_source_switched

bash "$ROOT/$ROOT_VERIFIER_REL"
write_journal root_verifier_passed

# This is intentionally the final fallible transaction mutation.  The index was
# bound above, so a plain commit can include only the two reviewed governance files.
require_root_governance
git -C "$ROOT" commit -m "chore: promote frozen llama.cpp kernel to v8"
root_committed=1
write_journal root_governance_committed
completed=1
write_journal complete
printf 'Cutover complete. Durable journal: %s\n' "$JOURNAL"

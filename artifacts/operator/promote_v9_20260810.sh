#!/bin/bash
# One-shot v8 -> v9 cutover. This consumes the sealed, relocatable runtime
# stage and keeps the entire v8 runtime available for verified rollback.
set -euo pipefail

MODE=promote
case ${1:-} in
    --validate-only) MODE=validate ;;
    '') ;;
    *) printf 'usage: %s [--validate-only]\n' "$0" >&2; exit 2 ;;
esac

ROOT=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
CANONICAL=/mnt/raid0/llm/llama.cpp
V8_BRANCH=production-consolidated-v8
V8_HEAD=67a433bf45a8a091d83b4ea0b32ff0735fd51800
V9_BRANCH=production-consolidated-v9
V9_HEAD=0db32c06e3e550065b78311a6031ef3dd2c4f27c
EXPECTED_VERSION_LINE='version: 10125 (0db32c06e)'
CPU_SHA=8ebb1355593121a231735d7b58ad076f4539d2c5e3847fa09d2922fa8a980499
HIP_SHA=21cfb750dc0ba4b3add0674fcb9dd061d77b3604ebf8e1d063ba0e2c51902feb
# Literal loader token; expansion must happen in the ELF loader, not this shell.
# shellcheck disable=SC2016
CPU_RPATH='$ORIGIN'
# shellcheck disable=SC2016
HIP_RPATH='$ORIGIN:/opt/rocm/lib'
STAGE=/mnt/raid0/llm/kernel-runtime-stages/production-consolidated-v9-0db32c06e
PROVENANCE="$ROOT/artifacts/operator/v9-runtime-packaging-20260810T224026Z-0db32c06e/summary.json"
ROOT_VERIFIER_REL=scripts/session/verify_llama_cpp.sh
ATTESTATION_REL=handoffs/active/v9-kernel-promotion-attestation.json

: "${PROMOTED_AT:?set PROMOTED_AT to the timezone-bearing v9 promotion timestamp}"
: "${CUTOVER_ID:?set CUTOVER_ID to a unique cutover identifier}"
if [[ $MODE == validate ]]; then
    ROOT_BASE_HEAD=${ROOT_BASE_HEAD:-$(git -C "$ROOT" rev-parse HEAD)}
else
    : "${ROOT_BASE_HEAD:?set ROOT_BASE_HEAD to the exact pre-cutover epyc-root HEAD}"
fi
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

logging_active=0
if [[ $MODE == promote ]]; then
    source "$ROOT/scripts/utils/agent_log.sh"
    agent_session_start "v9 reversible production cutover"
    agent_task_start "Promote sealed v9 runtime trees" "Journaled v8-to-v9 transaction with verified rollback before governance commit"
    logging_active=1
fi

JOURNAL_DIR="$ROOT/artifacts/operator/v9-cutover-$CUTOVER_ID"
JOURNAL="$JOURNAL_DIR/journal.json"
JOURNAL_TMP="$JOURNAL_DIR/journal.json.tmp"
V8_CPU_MANIFEST="$JOURNAL_DIR/v8-cpu.manifest"
V8_HIP_MANIFEST="$JOURNAL_DIR/v8-hip.manifest"
STAGE_CPU_MANIFEST="$JOURNAL_DIR/v9-cpu.manifest"
STAGE_HIP_MANIFEST="$JOURNAL_DIR/v9-hip.manifest"
ROLLBACK_ROOT="/mnt/raid0/llm/kernel-runtime-rollbacks/v8-$CUTOVER_ID"
V8_BUILD_BACKUP="$ROLLBACK_ROOT/build"
V8_HIP_BACKUP="$ROLLBACK_ROOT/build-hip"
FAILURE_ROOT="/mnt/raid0/llm/kernel-runtime-failures/v9-$CUTOVER_ID"
FAILED_V9_BUILD="$FAILURE_ROOT/build"
FAILED_V9_HIP="$FAILURE_ROOT/build-hip"

cpu_backed_up=0
hip_backed_up=0
cpu_installed=0
hip_installed=0
root_committed=0
completed=0
journal_ready=0
cutover_started=0

exec 9>"$ROOT/artifacts/operator/.v9-cutover.lock"
flock -n 9 || {
    printf 'Another cooperating v9 cutover holds %s\n' "$ROOT/artifacts/operator/.v9-cutover.lock" >&2
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
    local pid exe comm cmdline found=1
    for pid_dir in /proc/[0-9]*; do
        pid=${pid_dir##*/}
        exe=$(readlink "$pid_dir/exe" 2>/dev/null || true)
        case ${exe##*/} in
            llama-server|llama-cli|llama-bench)
                printf '%s %s\n' "$pid" "$exe" >&2
                found=0
                ;;
        esac
        comm=$(dd if="$pid_dir/comm" status=none 2>/dev/null || true)
        cmdline=$(dd if="$pid_dir/cmdline" status=none 2>/dev/null | tr '\0' ' ' || true)
        case "$comm:$cmdline" in
            *:*/epyc-orchestrator/*autopilot*|*:*-m\ epyc_orchestrator.autopilot*|autopilot:*)
                printf '%s autopilot %s\n' "$pid" "$cmdline" >&2
                found=0
                ;;
        esac
    done
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
    for path in "$STAGE" "$STAGE/cpu/bin" "$STAGE/hip/bin" "$CANONICAL/build" "$CANONICAL/build-hip" /mnt/raid0/llm; do
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
  "production_branch": "$V9_BRANCH",
  "production_head": "$V9_HEAD",
  "rollback_branch": "$V8_BRANCH",
  "rollback_head": "$V8_HEAD",
  "stage": "$STAGE",
  "rollback_build_dir": "$V8_BUILD_BACKUP",
  "rollback_hip_build_dir": "$V8_HIP_BACKUP",
  "failed_v9_build_dir": "$FAILED_V9_BUILD",
  "failed_v9_hip_dir": "$FAILED_V9_HIP",
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
    grep -Fq "EXPECTED_BRANCH=\"$V9_BRANCH\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier does not name $V9_BRANCH"
    grep -Fq "EXPECTED_COMMIT=\"$V9_HEAD\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier does not name $V9_HEAD"
    grep -Fq "EXPECTED_VERSION_LINE=\"$EXPECTED_VERSION_LINE\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier has the wrong v9 version"
    grep -Fq "EXPECTED_CPU_SERVER_SHA256=\"$CPU_SHA\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier has the wrong CPU SHA"
    grep -Fq "EXPECTED_HIP_SERVER_SHA256=\"$HIP_SHA\"" "$ROOT/$ROOT_VERIFIER_REL" || fail "staged verifier has the wrong HIP SHA"
    jq -e \
        --arg branch "$V9_BRANCH" --arg head "$V9_HEAD" --arg promoted_at "$PROMOTED_AT" \
        --arg hip_sha "$HIP_SHA" --arg v8_branch "$V8_BRANCH" --arg v8_head "$V8_HEAD" \
        --arg server "$CANONICAL/build-hip/bin/llama-server" '
        .schema == "epyc.kernel_promotion_attestation.v1" and
        .status == "production_promoted_pending_gpu_certification" and
        .production_branch == $branch and .production_head == $head and
        .frozen == false and .promoted_at == $promoted_at and
        .server_binary.path == $server and .server_binary.sha256 == $hip_sha and
        .rollback.branch == $v8_branch and .rollback.head == $v8_head and
        .rollback.backup_ref == ("refs/heads/" + $v8_branch) and
        .rollback.source_ref == ("refs/heads/" + $branch)
        ' "$ROOT/$ATTESTATION_REL" >/dev/null || fail "staged provisional v9 attestation does not bind this exact promotion"
}

verify_root_restored() {
    [[ $(git -C "$ROOT" rev-parse HEAD) == "$ROOT_BASE_HEAD" ]] || return 1
    git -C "$ROOT" diff --quiet "$ROOT_BASE_HEAD" -- "$ROOT_VERIFIER_REL" "$ATTESTATION_REL" || return 1
    git -C "$ROOT" diff --cached --quiet "$ROOT_BASE_HEAD" -- "$ROOT_VERIFIER_REL" "$ATTESTATION_REL" || return 1
    [[ -z $(git -C "$ROOT" status --porcelain --untracked-files=all -- "$ROOT_VERIFIER_REL" "$ATTESTATION_REL") ]]
}

restore_root_governance() {
    git -C "$ROOT" restore --source "$ROOT_BASE_HEAD" --staged --worktree -- "$ROOT_VERIFIER_REL" || return 1
    if git -C "$ROOT" cat-file -e "$ROOT_BASE_HEAD:$ATTESTATION_REL" 2>/dev/null; then
        git -C "$ROOT" restore --source "$ROOT_BASE_HEAD" --staged --worktree -- "$ATTESTATION_REL"
    else
        git -C "$ROOT" restore --staged -- "$ATTESTATION_REL" 2>/dev/null || true
        rm -f -- "$ROOT/$ATTESTATION_REL"
    fi
}

rollback() {
    local status=$? rollback_ok=1
    trap - EXIT
    if (( completed )); then
        (( logging_active == 0 )) || agent_task_end "Promote sealed v9 runtime trees" success
        exit "$status"
    fi
    if (( root_committed )) || [[ $(git -C "$ROOT" rev-parse HEAD 2>/dev/null) != "$ROOT_BASE_HEAD" ]]; then
        printf 'ERROR: root governance commit succeeded; preserving v9 and journal for manual recovery.\n' >&2
        write_journal post_root_commit_failure || true
        (( logging_active == 0 )) || agent_task_end "Promote sealed v9 runtime trees" failure
        exit 2
    fi
    if (( ! cutover_started )); then
        if (( journal_ready )); then
            write_journal aborted_before_production_mutation || true
        fi
        (( logging_active == 0 )) || agent_task_end "Promote sealed v9 runtime trees" failure
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
        mkdir -p "$FAILURE_ROOT" || rollback_ok=0
        if [[ -e "$V8_HIP_BACKUP" ]]; then
            if [[ -e "$CANONICAL/build-hip" ]]; then
                mv "$CANONICAL/build-hip" "$FAILED_V9_HIP" || rollback_ok=0
            fi
            mv "$V8_HIP_BACKUP" "$CANONICAL/build-hip" || rollback_ok=0
            manifest_matches "$CANONICAL/build-hip" "$V8_HIP_MANIFEST" || rollback_ok=0
        fi
        if [[ -e "$V8_BUILD_BACKUP" ]]; then
            if [[ -e "$CANONICAL/build" ]]; then
                mv "$CANONICAL/build" "$FAILED_V9_BUILD" || rollback_ok=0
            fi
            mv "$V8_BUILD_BACKUP" "$CANONICAL/build" || rollback_ok=0
            manifest_matches "$CANONICAL/build" "$V8_CPU_MANIFEST" || rollback_ok=0
        fi
    fi
    if [[ $(git -C "$CANONICAL" rev-parse --abbrev-ref HEAD 2>/dev/null) != "$V8_BRANCH" ]]; then
        git -C "$CANONICAL" switch "$V8_BRANCH" || rollback_ok=0
    fi
    is_exact_tracked_clean "$CANONICAL" "$V8_BRANCH" "$V8_HEAD" || rollback_ok=0
    restore_root_governance || rollback_ok=0
    verify_root_restored || rollback_ok=0
    if (( rollback_ok )); then
        write_journal rolled_back || rollback_ok=0
    else
        write_journal rollback_incomplete || true
    fi
    (( logging_active == 0 )) || agent_task_end "Promote sealed v9 runtime trees" failure
    if (( rollback_ok )); then
        exit "$status"
    fi
    printf 'ERROR: rollback is incomplete; inspect %s before touching production.\n' "$JOURNAL" >&2
    exit 2
}
trap rollback EXIT

[[ ! -e "$JOURNAL_DIR" && ! -e "$ROLLBACK_ROOT" ]] || fail "cutover journal or rollback directory already exists for $CUTOVER_ID"
[[ ! -e "$FAILURE_ROOT" ]] || fail "failed-v9 preservation directory already exists for $CUTOVER_ID"

require_exact_tracked_clean "$CANONICAL" "$V8_BRANCH" "$V8_HEAD"
git -C "$CANONICAL" rev-parse --verify --quiet "$V9_HEAD^{commit}" >/dev/null || fail "v9 candidate commit is unavailable"
require_tree "$STAGE/cpu/bin"
require_tree "$STAGE/hip/bin"
require_same_device_and_space
jq -e --arg head "$V9_HEAD" --arg stage "$STAGE" --arg cpu "$CPU_SHA" --arg hip "$HIP_SHA" '
    .schema == "epyc.kernel_v9.runtime_packaging.v1" and .status == "sealed" and
    .candidate_head == $head and .stage == $stage and .production_mutated == false and
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
if [[ $MODE == validate ]]; then
    require_no_runtime_users
    completed=1
    printf 'Validated sealed v9 cutover inputs; production was not mutated.\n'
    exit 0
fi
require_root_governance
require_no_runtime_users
mkdir "$JOURNAL_DIR"
tree_manifest "$CANONICAL/build" "$V8_CPU_MANIFEST"
tree_manifest "$CANONICAL/build-hip" "$V8_HIP_MANIFEST"
tree_manifest "$STAGE/cpu/bin" "$STAGE_CPU_MANIFEST"
tree_manifest "$STAGE/hip/bin" "$STAGE_HIP_MANIFEST"
write_journal prepared
journal_ready=1

printf '%s\n' "This will promote $V9_HEAD to $V9_BRANCH, consume the sealed v9 runtime stage, and commit only the staged governance files."
read -r -p 'Type PROMOTE-V9 to continue: ' confirmation
[[ $confirmation == PROMOTE-V9 ]] || fail "operator confirmation not provided"

# Revalidate the mutable boundaries immediately before the first production mutation.
require_exact_tracked_clean "$CANONICAL" "$V8_BRANCH" "$V8_HEAD"
require_root_governance
require_no_runtime_users

if git -C "$CANONICAL" show-ref --verify --quiet "refs/heads/$V9_BRANCH"; then
    [[ $(git -C "$CANONICAL" rev-parse "$V9_BRANCH") == "$V9_HEAD" ]] || fail "$V9_BRANCH already names a different commit"
else
    cutover_started=1
    git -C "$CANONICAL" branch "$V9_BRANCH" "$V9_HEAD"
fi
cutover_started=1
write_journal v9_ref_ready

mkdir -p "$ROLLBACK_ROOT"
mv "$CANONICAL/build" "$V8_BUILD_BACKUP"
cpu_backed_up=1
write_journal v8_cpu_backed_up
mv "$CANONICAL/build-hip" "$V8_HIP_BACKUP"
hip_backed_up=1
write_journal v8_hip_backed_up
mkdir "$CANONICAL/build" "$CANONICAL/build-hip"

mv "$STAGE/cpu/bin" "$CANONICAL/build/bin"
cpu_installed=1
write_journal v9_cpu_installed
mv "$STAGE/hip/bin" "$CANONICAL/build-hip/bin"
hip_installed=1
write_journal v9_hip_installed

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

git -C "$CANONICAL" switch "$V9_BRANCH"
require_exact_tracked_clean "$CANONICAL" "$V9_BRANCH" "$V9_HEAD"
write_journal v9_source_switched

bash "$ROOT/$ROOT_VERIFIER_REL"
write_journal root_verifier_passed

# This is intentionally the final fallible transaction mutation.  The index was
# bound above, so a plain commit can include only the two reviewed governance files.
require_root_governance
git -C "$ROOT" commit -m "chore: promote frozen llama.cpp kernel to v9"
root_committed=1
write_journal root_governance_committed
completed=1
write_journal complete
printf 'Cutover complete. Durable journal: %s\n' "$JOURNAL"

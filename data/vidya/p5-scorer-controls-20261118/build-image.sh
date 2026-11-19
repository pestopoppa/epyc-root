#!/bin/bash
set -euo pipefail

D=$(dirname "$(readlink -f "$0")")
LAUNCHER=${P5_BUILD_LAUNCHER:-$0}
ID=vb-p5-sphinx-image-rebuild-20261118
BASE='swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8593@sha256:bf09a4f64ca8a2dd3c9e2d252d640ed0239e6b2927fa524e40b6cde7aa0fafc0'
BASE_ID=sha256:84fd7981cbcb53fe42d3f314cac61670175b9429ec51abea180f258d6e66f293
DOCKERFILE_SHA=9ff861978efad7f1452da229378b3e87c91f0c17089036cd903a28ca0cd919d0

if [[ ${1:-} == --preflight ]]; then
    printf '%s  %s\n' "$DOCKERFILE_SHA" "$D/context/Dockerfile" | sha256sum --check --status
    test "$(docker image inspect --format '{{.Id}}' "$BASE")" = "$BASE_ID"
    exit
fi

if [[ ${1:-} == --job || ${1:-} == --complete ]]; then
    result="$D/official/RESULT.json"
    mode=official
    if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
        result=${FILLER_DRYRUN_RESULT_PATH:?}
        mode=smoke
        [[ $result == "${FILLER_DRYRUN_DIR:?}"/native-attempts/attempt-*/native-result.json ]]
    fi
    if [[ $1 == --complete ]]; then
        jq -e --arg mode "$mode" --arg id "$ID" --arg base "$BASE_ID" --arg dockerfile "$DOCKERFILE_SHA" \
            '.status == "COMPLETE" and .mode == $mode and .id == $id and
             .base_image_id == $base and .dockerfile_sha256 == $dockerfile' "$result" >/dev/null
        build_log=$(jq -er '.build_log' "$result")
        build_log=$(realpath -e "$build_log")
        attempt=$(dirname "$build_log")
        [[ $(dirname "$attempt") == "$(realpath -e "$(dirname "$result")")" ]]
        [[ $(basename "$attempt") == build-* && $(basename "$build_log") == build.log ]]
        expected_log_sha=$(jq -er '.build_log_sha256' "$result")
        test "$(sha256sum "$build_log" | cut -d ' ' -f 1)" = "$expected_log_sha"
        image=$(jq -er '.image_id' "$result")
        [[ $image =~ ^sha256:[a-f0-9]{64}$ ]]
        grant_sha=$(jq -er '.grant_sha256' "$result")
        test "$(sha256sum "$(dirname "$build_log")/rowflow.grant" | cut -d ' ' -f 1)" = "$grant_sha"
        test "$(docker image inspect --format '{{.Id}}' "$image")" = "$image"
        exit
    fi

    mkdir -p "$(dirname "$result")"
    attempt=$(mktemp -d "$(dirname "$result")/build-XXXXXXXX")
    started=$(date -u +%FT%TZ)
    actual_cpus=$(awk '/^Cpus_allowed_list:/ {print $2}' "/proc/$$/status")
    grant_sha=
    terminal() {
        local rc=$1
        if (( rc != 0 )); then
            jq -n --arg id "$ID" --arg mode "$mode" --arg started "$started" --arg cpus "$actual_cpus" \
                --arg grant_sha "$grant_sha" --arg utc "$(date -u +%FT%TZ)" --argjson rc "$rc" \
                '{id:$id,mode:$mode,status:"UNKNOWN",started_utc:$started,completion_utc:$utc,actual_cpus:$cpus,grant_sha256:$grant_sha,runner_rc:$rc}' \
                >"$attempt/terminal.json"
        fi
    }
    trap 'terminal "$?"' EXIT
    trap 'exit 75' INT TERM
    "$LAUNCHER" --preflight
    test "${FILLER_ID:?}" = "$ID"
    test "${FILLER_NEEDGPU:?}" = 0
    test ! -e "${FILLER_STOPFILE:?}"
    remaining=$((FILLER_DEADLINE - $(date +%s)))
    test "$remaining" -gt 60
    (( remaining <= 300 )) || remaining=300
    if [[ $mode == smoke ]]; then
        grants="${FILLER_DRYRUN_DIR:?}/grants"
        test "${FILLER_SMOKE:?}" = 1
    else
        grants="${FILLER_FLAGS_DIR:-/mnt/raid0/llm/tmp/compute-flags}/grants"
    fi
    cp -- "$grants/$ID.grant" "$attempt/rowflow.grant"
    grant_sha=$(sha256sum "$attempt/rowflow.grant" | cut -d ' ' -f 1)
    test -n "$actual_cpus"
    DOCKER_BUILDKIT=0 timeout --foreground "$remaining" docker build --pull=false --network=none \
        --cpuset-cpus "${FILLER_CPUS:?}" --cpu-period 100000 --cpu-quota 400000 --memory 6g \
        --iidfile "$attempt/image.iid" "$D/context" >"$attempt/build.log" 2>&1
    test ! -e "$FILLER_STOPFILE"
    "$LAUNCHER" --preflight
    test "$(date +%s)" -lt "$FILLER_DEADLINE"
    image=$(cat "$attempt/image.iid")
    [[ $image =~ ^sha256:[a-f0-9]{64}$ ]]
    test "$(docker image inspect --format '{{.Id}}' "$image")" = "$image"
    build_log_sha=$(sha256sum "$attempt/build.log" | cut -d ' ' -f 1)
    jq -n --arg id "$ID" --arg mode "$mode" --arg image "$image" --arg base "$BASE_ID" \
        --arg dockerfile "$DOCKERFILE_SHA" --arg log "$attempt/build.log" --arg log_sha "$build_log_sha" \
        --arg started "$started" --arg cpus "$actual_cpus" --arg grant_sha "$grant_sha" --arg utc "$(date -u +%FT%TZ)" \
        '{id:$id,mode:$mode,status:"COMPLETE",image_id:$image,base_image_id:$base,dockerfile_sha256:$dockerfile,build_log:$log,build_log_sha256:$log_sha,started_utc:$started,completion_utc:$utc,actual_cpus:$cpus,grant_sha256:$grant_sha,runner_rc:0}' \
        >"$attempt/receipt.json"
    ln "$attempt/receipt.json" "$result"
    exit
fi

exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class cpu --role build --min-window 300 --stop "$D/STOP" --workdir "$D" \
    --precond-cmd "$LAUNCHER --preflight" --cmd "$LAUNCHER --job" \
    --complete-cmd "$LAUNCHER --complete"

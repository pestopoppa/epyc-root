#!/bin/bash
set -euo pipefail

ROOT=/mnt/raid0/llm/epyc-root
RESEARCH=/mnt/raid0/llm/epyc-inference-research
PRODUCTION=/mnt/raid0/llm/llama.cpp
CANDIDATE=/mnt/raid0/llm/llama.cpp-experimental
OUTPUT="$ROOT/artifacts/operator/waive_q8_cpu_prefill_v8_20260725.json"

EXPECTED_ROOT_HEAD=0fd2bacab89f03cc0d51b5b243d4b20fb2c6058d
EXPECTED_RESEARCH_HEAD=618c0c69
EXPECTED_RUNNER_SHA256=2fb0013d2cb71b149a7429995830ac0356048582671ae83428cb1ef15ccfe024
EXPECTED_PRODUCTION_HEAD=6ad45fa3ff6718c07c000061dbc6e29c1771f6e3
EXPECTED_CANDIDATE_HEAD=67a433bf45a8a091d83b4ea0b32ff0735fd51800
EXPECTED_MEASUREMENT_SHA256=6c894c302aa4ad868cd66ad36814fded1937cb84d097724feffc25f6f1468e88

if [[ -e "$OUTPUT" ]]; then
    printf 'Refusing: waiver attestation already exists: %s\n' "$OUTPUT" >&2
    exit 1
fi
if [[ "$(git -C "$ROOT" rev-parse HEAD)" != "$EXPECTED_ROOT_HEAD" ]]; then
    printf 'Refusing: epyc-root HEAD drifted.\n' >&2
    exit 1
fi
if [[ "$(git -C "$RESEARCH" rev-parse --short=8 HEAD)" != "$EXPECTED_RESEARCH_HEAD" ]]; then
    printf 'Refusing: epyc-inference-research HEAD drifted.\n' >&2
    exit 1
fi
if [[ "$(sha256sum "$RESEARCH/scripts/benchmark/cpu_prefill_v8_regression_runner.py" | awk '{print $1}')" != "$EXPECTED_RUNNER_SHA256" ]]; then
    printf 'Refusing: CPU-prefill runner content drifted.\n' >&2
    exit 1
fi
if [[ "$(git -C "$PRODUCTION" rev-parse HEAD)" != "$EXPECTED_PRODUCTION_HEAD" ]]; then
    printf 'Refusing: production v7 HEAD drifted.\n' >&2
    exit 1
fi
if [[ "$(git -C "$CANDIDATE" rev-parse HEAD)" != "$EXPECTED_CANDIDATE_HEAD" ]]; then
    printf 'Refusing: v8 candidate HEAD drifted.\n' >&2
    exit 1
fi
if [[ "$(sha256sum "$ROOT/MEASUREMENT.md" | awk '{print $1}')" != "$EXPECTED_MEASUREMENT_SHA256" ]]; then
    printf 'Refusing: MEASUREMENT.md drifted.\n' >&2
    exit 1
fi
if (
    ! git -C "$ROOT" diff --quiet -- MEASUREMENT.md CHANGELOG.md ||
    ! git -C "$ROOT" diff --cached --quiet -- MEASUREMENT.md CHANGELOG.md
); then
    printf 'Refusing: protected measurement files have staged or unstaged changes.\n' >&2
    exit 1
fi

printf '%s\n' \
    'This records the campaign-scoped WAIVE-Q8 decision for v8.' \
    'It excludes four Qwen3.6 Q8 arm runs (two matched pairs) from B4.' \
    'It does not change the ratified 72-core protocol.' \
    'Gemma Q4 and every IQ arm remain mandatory.' \
    'The v8 promotion will make no Q8 non-regression claim.' \
    'Type WAIVE-Q8 to attest this decision; anything else aborts.'
read -r -p '> ' confirmation
if [[ "$confirmation" != "WAIVE-Q8" ]]; then
    printf 'Aborted; no attestation created.\n'
    exit 1
fi

ratified_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat >"$OUTPUT" <<JSON
{
  "schema": "epyc.cpu_prefill_v8.operator_waiver.v1",
  "decision": "WAIVE-Q8",
  "ratified_at": "$ratified_at",
  "protocol": "P-BENCH-PREFILL-1",
  "protocol_changed": false,
  "candidate_head": "$EXPECTED_CANDIDATE_HEAD",
  "production_head": "$EXPECTED_PRODUCTION_HEAD",
  "runner_sha256_before_waiver_implementation": "$EXPECTED_RUNNER_SHA256",
  "scope": {
    "excluded_model": "qwen36_q8",
    "excluded_model_path": "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
    "excluded_pairs": [
      "qwen36_q8-tg128-iqk1",
      "qwen36_q8-pp2048-iqk1"
    ],
    "excluded_arm_runs": 4,
    "remaining_matched_pairs": 14,
    "remaining_arm_runs": 28
  },
  "reason": "The Qwen3.6 Q8 workload naturally sustains about 50-55 target core-equivalents and cannot satisfy the ratified 72-core eligibility floor.",
  "consequences": [
    "No v8 Q8 non-regression claim may be made from this campaign.",
    "The ratified 72-core eligibility floor remains unchanged for every remaining arm.",
    "The Gemma Q4 non-IQ B4 pairs remain mandatory.",
    "All retained IQ B3 pairs remain mandatory.",
    "Pre-waiver artifacts remain ineligible and cannot be retro-certified."
  ]
}
JSON

python3 -m json.tool "$OUTPUT" >/dev/null
printf '\nWAIVE-Q8 attestation created:\n%s\n' "$OUTPUT"
sha256sum "$OUTPUT"

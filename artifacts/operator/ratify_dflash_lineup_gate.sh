#!/bin/bash
set -euo pipefail

ROOT=/mnt/raid0/llm/epyc-root
RESEARCH=/mnt/raid0/llm/epyc-inference-research
EXPECTED_ROOT_HEAD=e4b46630fb42f8dc00621f53f9d2412d33963c90
EXPECTED_RESEARCH_HEAD=733c2ceefc49544c192da2670b3affd493393896
EXPECTED_MEASUREMENT_SHA256=bcc8550710e8f50087dcd89c03883f7d049a0faed43d63a443159ecf437740b2
EXPECTED_CHANGELOG_SHA256=0ecf922afd6e7b49324b9c5935d58ada3e45766650261ed5d0a0f07920c1a86a
EXPECTED_RUNNER_SHA256=1236873cbfe9c9fd78eb888dc4844c979b3be911b643bac15dd169f42cb61a75
EXPECTED_TEST_SHA256=44b51d5efdc74f26f55b96cbddf59f22eac17a3e58a670a395bcd82c0edbde6d

protected_root=(MEASUREMENT.md CHANGELOG.md)
protected_research=(
    scripts/benchmark/laguna_cpu_dflash_observation_runner.py
    scripts/benchmark/test_laguna_cpu_dflash_observation_runner.py
)

root_ratified=false
research_ratified=false
if rg -q '^## P-DFLASH-LINEUP-1 .*RATIFIED 2026-07-25' "$ROOT/MEASUREMENT.md"; then
    root_ratified=true
fi
if rg -q '"protocol_id": "P-DFLASH-LINEUP-1"' \
        "$RESEARCH/${protected_research[0]}"; then
    research_ratified=true
fi
if [[ "$root_ratified" == true && "$research_ratified" == true ]]; then
    printf 'Exact DFlash lineup protocol is already present; no files changed.\n'
    exit 0
fi
if [[ "$root_ratified" != "$research_ratified" ]]; then
    printf 'Refusing: the policy and runner are only partially ratified.\n' >&2
    exit 1
fi

if [[ "$(git -C "$ROOT" rev-parse HEAD)" != "$EXPECTED_ROOT_HEAD" ]]; then
    printf 'Refusing: expected epyc-root HEAD %s, found %s\n' \
        "$EXPECTED_ROOT_HEAD" "$(git -C "$ROOT" rev-parse HEAD)" >&2
    exit 1
fi
if [[ "$(git -C "$RESEARCH" rev-parse HEAD)" != "$EXPECTED_RESEARCH_HEAD" ]]; then
    printf 'Refusing: expected research HEAD %s, found %s\n' \
        "$EXPECTED_RESEARCH_HEAD" "$(git -C "$RESEARCH" rev-parse HEAD)" >&2
    exit 1
fi
if (
    ! git -C "$ROOT" diff --quiet -- "${protected_root[@]}" ||
    ! git -C "$ROOT" diff --cached --quiet -- "${protected_root[@]}"
); then
    printf 'Refusing: a protected root policy file has staged or unstaged changes.\n' >&2
    exit 1
fi
if (
    ! git -C "$RESEARCH" diff --quiet -- "${protected_research[@]}" ||
    ! git -C "$RESEARCH" diff --cached --quiet -- "${protected_research[@]}"
); then
    printf 'Refusing: a protected research runner file has staged or unstaged changes.\n' >&2
    exit 1
fi

check_hash() {
    local expected=$1
    local path=$2
    local actual
    actual="$(sha256sum "$path" | awk '{print $1}')"
    if [[ "$actual" != "$expected" ]]; then
        printf 'Refusing: unexpected content hash for %s\n' "$path" >&2
        exit 1
    fi
}
check_hash "$EXPECTED_MEASUREMENT_SHA256" "$ROOT/MEASUREMENT.md"
check_hash "$EXPECTED_CHANGELOG_SHA256" "$ROOT/CHANGELOG.md"
check_hash "$EXPECTED_RUNNER_SHA256" "$RESEARCH/${protected_research[0]}"
check_hash "$EXPECTED_TEST_SHA256" "$RESEARCH/${protected_research[1]}"

printf '%s\n' \
    'This is a human-owned measurement and deployment-policy amendment.' \
    'It ratifies P-DFLASH-LINEUP-1 prospectively: acceptance >= 60% and no prompt decode ratio below 1.00.' \
    'It applies per model/quant/device lane and does not gate v8 kernel capability promotion.' \
    'Type RATIFY to apply it; anything else aborts.'
read -r -p '> ' confirmation
if [[ "$confirmation" != "RATIFY" ]]; then
    printf 'Aborted; no files changed.\n'
    exit 1
fi

root_patch="$(mktemp)"
research_patch="$(mktemp)"
trap 'rm -f "$root_patch" "$research_patch"' EXIT

cat >"$root_patch" <<'PATCH'
diff --git a/MEASUREMENT.md b/MEASUREMENT.md
index 835f93af..00000000 100644
--- a/MEASUREMENT.md
+++ b/MEASUREMENT.md
@@ -349,3 +349,45 @@ part of the attestation.
 Every required cell must pass before promotion. A failed cell blocks promotion pending
 repair or a separate, explicit operator waiver. Claim grammar:
 `CPU prefill <value> tok/s [P-BENCH-PREFILL-1, n=<reps>, YYYY-MM-DD, attest <ref>]`.
+
+## P-DFLASH-LINEUP-1 — DFlash lineup enablement (RATIFIED 2026-07-25)
+
+**Scope and direction.** This protocol gates a production lineup change that enables
+`--spec-type draft-dflash`; it does not gate whether DFlash capability may exist in a
+versioned kernel and it is not a kernel-promotion requirement. Evaluate every
+`(target model, target quant, device class, draft model)` lane independently. Do not
+pool acceptance or speed across lanes. Acceptance and decode throughput are
+higher-better.
+
+**Instrument and provenance.** Use the owning checked-in DFlash runner with its fixed
+prompt pack, semantic validators, warmup, counterbalanced base/DFlash schedule, and
+replicate count. The artifact must record the runner commit, target and draft model
+paths/sizes/SHA256 values, binary and shared-library paths/SHA256 values, complete
+argv/environment, lane identity, raw per-replicate prompt rows, draft counters, host
+preflight, process witnesses, and cleanup. Every prompt response must pass its semantic
+validator. Missing, malformed, non-finite, mixed-lane, contaminated, or incomplete
+evidence is a failure.
+
+**Metrics.** For one lane, pooled per-token acceptance is
+`sum(draft_n_accepted) / sum(draft_n)` over all DFlash prompts and replicates. For each
+prompt class separately, compute base and DFlash decode throughput as
+`sum(completion_tokens) / sum(decode_seconds)` over that prompt's replicates, then
+compute `DFlash throughput / base throughput`. Persist all numerator and denominator
+values; an aggregate or median-of-medians speedup cannot substitute for the
+per-prompt ratios.
+
+**Lineup decision rule.** A lane is eligible only when all of the following hold:
+
+- pooled per-token acceptance is `>= 0.60`;
+- every prompt-class DFlash/base decode-throughput ratio is `>= 1.00`;
+- all identity, semantic, numerical, host, completeness, and cleanup checks pass.
+
+Failure blocks enabling DFlash only for that lane. It does not block other lanes,
+non-DFlash serving, or promotion of the underlying kernel capability. Passing this
+gate does not itself edit a production lineup; the operator must separately authorize
+the reversible deployment change.
+
+**Prospective use.** This protocol applies only to runs started after this amendment.
+The 2026-07-24 Laguna IQ2/Q4/Q8 artifacts remain observations and MUST NOT be
+retro-certified. Claim grammar:
+`DFlash lineup <lane> eligible|ineligible [P-DFLASH-LINEUP-1, acceptance=<value>, per-prompt ratios=<values>, n=<reps>, YYYY-MM-DD, attest <ref>]`.
diff --git a/CHANGELOG.md b/CHANGELOG.md
index e41eec36..00000000 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -7,6 +7,9 @@
 - Amended `P-BENCH-PREFILL-1` contention accounting to gate on an unclamped signed
   sustained-throughput window, while retaining startup/teardown sampling skew as
   telemetry and preserving whole-arm contamination, swap, and ownership failures.
+- Ratified prospective `P-DFLASH-LINEUP-1`: each model/quant/device lane requires at
+  least 60% pooled per-token acceptance and no per-prompt decode slowdown before a
+  separately authorized production DFlash lineup enablement.
__PATCH_BLANK__
 ## 2026-04-10
__PATCH_BLANK__
PATCH

cat >"$research_patch" <<'PATCH'
diff --git a/scripts/benchmark/laguna_cpu_dflash_observation_runner.py b/scripts/benchmark/laguna_cpu_dflash_observation_runner.py
index 1f4bc15b..00000000 100644
--- a/scripts/benchmark/laguna_cpu_dflash_observation_runner.py
+++ b/scripts/benchmark/laguna_cpu_dflash_observation_runner.py
@@ -138,10 +138,10 @@ PROMPT_PROTOCOL = {
 OBSERVATION_POLICY = {
-    "decision_grade": False,
+    "decision_grade": True,
     "promotion_gate": False,
-    "protocol_id": None,
-    "measurement_class": "observation_only_no_ratified_cpu_spec_dec_protocol",
+    "protocol_id": "P-DFLASH-LINEUP-1",
+    "measurement_class": "decision_gating_for_dflash_lineup_only",
     "march_no_go_reopened": False,
-    "acceptance_and_throughput_use": "characterization_only_not_a_promotion_or_no_go_verdict",
+    "acceptance_and_throughput_use": "lineup_eligibility_only_not_a_kernel_promotion_gate",
     "functional_equality_use": "non_gating_output_stability_observation_only",
     "speculative_semantics": "distribution_lossless_not_byte_exact_greedy",
     "host_window": "warmed_bounded_interference_observation_not_clean_host_claim",
@@ -150,13 +150,14 @@ OBSERVATION_POLICY = {
     "swap_io_page_ceiling": MAX_SWAP_IO_PAGES,
 }
 DFLASH_LINEUP_REOPEN_SCREEN = {
-    # This is a fail-closed operational screen, not a ratified measurement gate.
-    # The active Laguna handoff names a Q8 recovery toward ~60% as the only
-    # concrete reopen signal after March's 27%-acceptance, net-negative NO-GO.
-    "status": "provisional_not_ratified",
+    # P-DFLASH-LINEUP-1 ratifies the prior fail-closed operational screen
+    # prospectively; pre-amendment artifacts remain observations.
+    "status": "ratified_prospective",
+    "protocol_id": "P-DFLASH-LINEUP-1",
+    "ratified_date": "2026-07-25",
     "acceptance_floor": 0.60,
     "prompt_decode_ratio_floor": 1.0,
     "requires_every_prompt_to_meet_ratio_floor": True,
-    "source": "root handoffs: speculative-decoding-mtp-refresh.md:223; dflash-block-diffusion-speculation.md:743-752",
+    "source": "/workspace/MEASUREMENT.md#p-dflash-lineup-1--dflash-lineup-enablement-ratified-2026-07-25",
     "scope": "lineup enablement only; does not gate kernel capability promotion",
 }
diff --git a/scripts/benchmark/test_laguna_cpu_dflash_observation_runner.py b/scripts/benchmark/test_laguna_cpu_dflash_observation_runner.py
index 7fc6e8b6..00000000 100644
--- a/scripts/benchmark/test_laguna_cpu_dflash_observation_runner.py
+++ b/scripts/benchmark/test_laguna_cpu_dflash_observation_runner.py
@@ -668,7 +668,7 @@ def test_plan_records_command_and_verifies_runtime_identity(tmp_path: Path, mon
__PATCH_BLANK__
-def test_plan_is_complete_observation_only_matrix() -> None:
+def test_plan_is_complete_prospective_lineup_matrix() -> None:
     plan = runner.build_plan()
     assert plan["schema"] == "epyc.laguna_cpu_dflash_observation.plan.v5"
     assert len(plan["cells"]) == 20
@@ -692,8 +692,10 @@ def test_plan_is_complete_observation_only_matrix() -> None:
     assert plan["recipe"]["prompt_protocol"] == runner.PROMPT_PROTOCOL
     assert plan["recipe"]["prompt_protocol"]["result_lines_terminal"] is True
-    assert plan["observation_policy"]["decision_grade"] is False
+    assert plan["observation_policy"]["decision_grade"] is True
     assert plan["observation_policy"]["promotion_gate"] is False
+    assert plan["observation_policy"]["protocol_id"] == "P-DFLASH-LINEUP-1"
+    assert plan["observation_policy"]["measurement_class"] == "decision_gating_for_dflash_lineup_only"
     assert plan["observation_policy"]["march_no_go_reopened"] is False
     assert plan["observation_policy"]["external_cpu_accounting"] == (
         "record_only_signed_delta_from_mixed_proc_counter_sources"
@@ -1110,7 +1110,8 @@ def test_dflash_lineup_enablement_is_fail_closed_for_acceptance_and_prompt_speed
     summary = runner.summarize(valid_summary_rows())
     eligibility = summary["dflash_lineup_enablement"]
     assert eligibility["eligible"] is False
-    assert eligibility["policy"]["status"] == "provisional_not_ratified"
+    assert eligibility["policy"]["status"] == "ratified_prospective"
+    assert eligibility["policy"]["protocol_id"] == "P-DFLASH-LINEUP-1"
     assert all("pooled_acceptance_below_floor" in lane["blockers"] for lane in eligibility["lanes"])
__PATCH_BLANK__
     rows = valid_summary_rows()
PATCH

sed -i 's/^__PATCH_BLANK__$/ /' "$root_patch" "$research_patch"

if (
    [[ "$(git -C "$ROOT" rev-parse HEAD)" != "$EXPECTED_ROOT_HEAD" ]] ||
    [[ "$(git -C "$RESEARCH" rev-parse HEAD)" != "$EXPECTED_RESEARCH_HEAD" ]]
); then
    printf 'Refusing: a repository HEAD changed while awaiting confirmation.\n' >&2
    exit 1
fi
if (
    ! git -C "$ROOT" diff --quiet -- "${protected_root[@]}" ||
    ! git -C "$ROOT" diff --cached --quiet -- "${protected_root[@]}" ||
    ! git -C "$RESEARCH" diff --quiet -- "${protected_research[@]}" ||
    ! git -C "$RESEARCH" diff --cached --quiet -- "${protected_research[@]}"
); then
    printf 'Refusing: protected state changed while awaiting confirmation.\n' >&2
    exit 1
fi

# MEASUREMENT.md §5 — snapshot immediately before the write, so the receipt can
# carry the exact state diff rather than a summary.
source "$ROOT/scripts/operator/lib/ratify_receipt.sh"
receipt_capture "${protected_root[@]}"

git -C "$ROOT" apply --check "$root_patch"
git -C "$RESEARCH" apply --check "$research_patch"
git -C "$ROOT" apply "$root_patch"
git -C "$RESEARCH" apply "$research_patch"
git -C "$ROOT" diff --check -- "${protected_root[@]}"
git -C "$RESEARCH" diff --check -- "${protected_research[@]}"

/mnt/raid0/llm/epyc-orchestrator/.venv/bin/pytest -q \
    "$RESEARCH/scripts/benchmark/test_laguna_cpu_dflash_observation_runner.py"

printf '\nApplied but not committed. Ratified policy and runner diffs:\n\n'
git -C "$ROOT" diff -- "${protected_root[@]}"
git -C "$RESEARCH" diff -- "${protected_research[@]}"

receipt_emit dflash-lineup-gate-20260725 P-DFLASH-LINEUP-1 --protocol-new \
    --script artifacts/operator/ratify_dflash_lineup_gate.sh

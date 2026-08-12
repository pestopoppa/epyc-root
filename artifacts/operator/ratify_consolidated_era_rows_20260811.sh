#!/bin/bash
# Human-only consolidated instrument-era amendment. Appends up to FOUR era rows to
# orchestration/instrument_eras.yaml (HUMAN-AMENDMENT-ONLY). Never runs inference,
# never mutates any other file. Each row is INDEPENDENTLY validated and can be
# struck with --skip <id> without invalidating the rest (R8 consolidated shape).
#
# Design note (auditor, 2026-08-11): this ratifier deliberately pins SEMANTIC
# preconditions per row (id absent, unique insertion anchor, YAML parse, per-scope
# chronology) instead of a whole-file sha256 — autopilot seals eras into this file
# autonomously, so a whole-file pin rots in hours (see RATIFY-E9-ROUTING-REWARD-ERA-
# 20260729, dead on arrival for exactly that reason). What the operator signs is the
# EXACT ROW TEXTS embedded below; the receipt records their sha256.
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-CONSOLIDATED-ERA-ROWS-20260811"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
TARGET="$ORCH/orchestration/instrument_eras.yaml"
ROOT="/mnt/raid0/llm/epyc-root"
RECEIPT="$ROOT/artifacts/operator/ratify_consolidated_era_rows_20260811.json"
TRUST_LOCK="/run/lock/epyc-measurement-trust-boundary.lock"
PYTHON="/usr/bin/python3"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() { printf 'usage: %s (--validate-only|--attest %s|--emit-candidate <path-outside-repos>) [--skip <row-id>]...\n' "$0" "$TOKEN" >&2; }

MODE=""; EMIT_PATH=""; SKIPS=()
case "${1:-}" in
    --validate-only) MODE="validate"; shift ;;
    --attest) [[ "${2:-}" == "$TOKEN" ]] || { usage; exit 2; }; MODE="attest"; shift 2 ;;
    --emit-candidate) [[ -n "${2:-}" ]] || { usage; exit 2; }; MODE="emit"; EMIT_PATH="$2"; shift 2 ;;
    *) usage; exit 2 ;;
esac
while [[ $# -gt 0 ]]; do
    [[ "$1" == "--skip" && -n "${2:-}" ]] || { usage; exit 2; }
    SKIPS+=("$2"); shift 2
done

[[ -x "$PYTHON" ]] || fail "trusted interpreter unavailable"
[[ -f "$TARGET" ]] || fail "target registry is missing: $TARGET"
[[ "$MODE" != "attest" || ! -e "$RECEIPT" ]] || fail "receipt already exists (token is SPENT): $RECEIPT"
[[ "$MODE" != "attest" || ! -e "$ROOT/artifacts/operator/receipts/$TOKEN.json" ]] || fail "receipt index already exists (token is SPENT): receipts/$TOKEN.json"
if [[ "$MODE" == "emit" ]]; then
    case "$EMIT_PATH" in
        "$ORCH"/*|"$ROOT"/*) fail "--emit-candidate must write OUTSIDE the repo trees" ;;
    esac
fi
if [[ "$MODE" == "attest" ]]; then
    git -C "$ORCH" diff --quiet -- orchestration/instrument_eras.yaml || fail "registry has unstaged changes; resolve before amending"
    git -C "$ORCH" diff --cached --quiet -- orchestration/instrument_eras.yaml || fail "registry has staged changes; resolve before amending"
fi

mkdir -p -- "$(dirname -- "$TRUST_LOCK")"
exec 8<>"$TRUST_LOCK"
/usr/bin/flock -n 8 || fail "measurement trust-boundary lock is already held"

"$PYTHON" - "$MODE" "$TARGET" "$RECEIPT" "$TOKEN" "$EMIT_PATH" "${SKIPS[@]+"${SKIPS[@]}"}" <<'PY'
import hashlib, json, os, sys, tempfile
from datetime import UTC, datetime

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required for validation; refusing without it")

mode, target, receipt, token, emit_path, *skips = sys.argv[1:]
skips = set(skips)
MARKER = "\nknown_dead_instrument_items:"

# The four row texts the operator is signing. Chronological order. Sources:
#  1. RATIFY-E9-ROUTING-REWARD-ERA-20260729 (mainB) — text verbatim from that token chain.
#  2. E5-THROTTLE-SCOPE-ERA-ROW-20260729 (mainA) — note verbatim from
#     /mnt/raid0/llm/tmp/mainA-era-candidate/instrument_eras.candidate.yaml.
#  3. Seeding-scorer B7-guard boundary (auditor, msg-20260729T160328Z-51; guard landed
#     as epyc-orchestrator e108ec9f 2026-07-29T18:20:36Z).
#  4. v9 production cutover (mainA A7 decision package; promoted_at from
#     v9-cutover-20260810T235900Z-0db32c06e/journal.json; freeze
#     ratify_v9_final_freeze_20260811.json).
ROWS = [
    (
        "E9-routing-reward",
        "routing_reward",
        '''  - id: E9-routing-reward
    from: "2026-07-21T15:27:04Z"
    scope: routing_reward
    note: >
      Reward saturation repair boundary. epyc-orchestrator 6344fbdb58497edd5b92a1f2f2c81ee504e1383f
      changed q_reward role resolution from the absent role field to
      producer_role then final_answer_role; replay of 20,526 historical completions changed
      reward entropy from 0.0000 to 2.4580 bits. RECONCILIATION: stored pre-boundary q_value and
      reward values are demote-to-prior for policy training or pre/post reward comparison; use
      deterministic replay under the repaired scorer or data collected at/after this boundary.
''',
    ),
    (
        "E8-cpu-bench-throttle-scope",
        "cpu_bench",
        '''  - id: E8-cpu-bench-throttle-scope
    from: "2026-07-29T14:50:06Z"
    scope: cpu_bench
    note: >
      P-BENCH-3 under-load throttle-gate SCOPE correction (epyc-inference-research
      98cfff44, operator-ratified 2026-07-29). Before this boundary the gate counted
      boosting cores across all 96 physical cores machine-wide and required >=80, so a
      cell that deliberately pins only part of the machine could never pass: E5 C1 pins
      48 physical cores and C2 pins 48, and the idle remainder parks near base clock.
      W0 evidence, zero counterexamples: every 96-core cell passed (C1b 15/15, C3 11/12)
      and every 48-core cell failed (C1-half 0/13, C2 0/10) at counts 53-78. From this
      boundary the gate is scoped to the cell's PINNED physical cores at the UNCHANGED
      2.5 GHz threshold and the UNCHANGED 80/96 ratio, so a full-machine cell still
      requires exactly 80 of 96 and no previously-correct gate loosens. throttle_check
      additionally persists the full per-core frequency vector, so from here a throttle
      verdict is re-derivable offline.
      RECONCILIATION: this boundary changes DECISION-GRADE ELIGIBILITY ONLY - no measured
      throughput, latency or quality value is altered, rescaled or reinterpreted by it.
      Pre-boundary partial-machine cells (C1, C2) carry an eligibility verdict produced by
      the unscoped gate and are NOT strictly comparable to post-boundary cells of the same
      shape; they are historical priors for decision-grade eligibility. Full-machine cells
      (C1b, C3) are unaffected in both directions. Pre-boundary throttle verdicts are also
      NOT re-derivable, because only the aggregate boosting count was persisted.
''',
    ),
    (
        "E8-seeding-reward-b7-guard",
        "seeding_reward",
        '''  - id: E8-seeding-reward-b7-guard
    from: "2026-07-29T18:20:36Z"
    scope: seeding_reward
    note: >
      Seeding-scorer B7-guard boundary. epyc-orchestrator e108ec9f guarded the legacy
      comparative reward path in the default seeding flow (seed_specialist_routing ->
      run_batch -> evaluate_question), which previously scored with ZERO B7 guards
      (auditor msg-20260729T160328Z-51; disposition GUARD, not delete, because the
      path is the reachable default). RECONCILIATION: seeding rewards collected
      pre-boundary are stamped pre-B7-scorer; where a decision depends on them,
      re-score offline from the persisted raw answers (deterministic replay before
      regeneration) rather than trusting stored values or re-running inference.
''',
    ),
    (
        "E9-cpu-kernel",
        "cpu_bench",
        '''  - id: E9-cpu-kernel
    from: "2026-08-10T23:59:00Z"
    scope: cpu_bench
    note: >
      v9 production cutover. Single kernel: production-consolidated-v9 at
      llama.cpp commit 0db32c06e3e550065b78311a6031ef3dd2c4f27c
      (binary version 10125 / 0db32c06e), promoted via cutover
      20260810T235900Z-0db32c06e (promoted_at 2026-08-10T23:59:00Z) and frozen by
      ratify_v9_final_freeze_20260811.json (ratified 2026-08-11T01:16:00Z);
      v8 (67a433bf45a8a091d83b4ea0b32ff0735fd51800, binary 10107) is the rollback
      anchor. RECONCILIATION: pre-boundary CPU throughput and eligibility rows
      measured on v8 are historical priors for decisions about the
      production-consolidated-v9 stack. Do not rescale across this boundary;
      re-measure within era under P-BENCH protocols with host attestation.
''',
    ),
]

original = open(target, "r", encoding="utf-8").read()
if original.count(MARKER) != 1:
    raise SystemExit("insertion anchor 'known_dead_instrument_items:' is not unique; refuse")
base = yaml.safe_load(original)
base_ids = [r["id"] for r in base["eras"]]
if len(base_ids) != len(set(base_ids)):
    raise SystemExit("pre-existing duplicate era ids; refuse")

unknown = skips - {rid for rid, _, _ in ROWS}
if unknown:
    raise SystemExit(f"--skip names unknown row id(s): {sorted(unknown)}")

report, insert_text, applied = [], "", []
for rid, scope, text in ROWS:
    if rid in skips:
        report.append((rid, "STRUCK by operator"))
        continue
    if f"id: {rid}" in original:
        report.append((rid, "SKIP - already present (idempotent)"))
        continue
    parsed = yaml.safe_load("eras:\n" + text)["eras"]
    if len(parsed) != 1 or parsed[0]["id"] != rid or parsed[0]["scope"] != scope:
        raise SystemExit(f"row text for {rid} does not parse to itself; refuse")
    insert_text += "\n" + text
    applied.append(rid)
    report.append((rid, f"APPLY sha256={hashlib.sha256(text.encode()).hexdigest()[:16]}"))

candidate = original.replace(MARKER, insert_text + MARKER) if insert_text else original
if len(candidate) != len(original) + len(insert_text):
    raise SystemExit("candidate size delta does not equal inserted bytes; refuse")
cand = yaml.safe_load(candidate)
cand_ids = [r["id"] for r in cand["eras"]]
if len(cand_ids) != len(set(cand_ids)):
    raise SystemExit("candidate has duplicate era ids; refuse")
if cand.get("known_dead_instrument_items") != base.get("known_dead_instrument_items"):
    raise SystemExit("known_dead_instrument_items block changed; refuse")
if [r for r in cand["eras"] if r["id"] in base_ids] != base["eras"]:
    raise SystemExit("a pre-existing era row changed; refuse")
for scope in {"cpu_bench", "routing_reward", "seeding_reward"}:
    rows = [r for r in cand["eras"] if r.get("scope") == scope]
    froms = [str(r["from"]) for r in rows if "from" in r]  # E0 genesis row has only `until`
    if froms != sorted(froms):
        raise SystemExit(f"scope {scope} rows are not chronological in file order; refuse")
cpu_rows = [r["id"] for r in cand["eras"] if r.get("scope") == "cpu_bench"]
expected_last = "E9-cpu-kernel" if "E9-cpu-kernel" in cand_ids else cpu_rows[-1]
if cpu_rows[-1] != expected_last:
    raise SystemExit("cpu_bench scoped[-1] is not the expected active row; refuse")

for rid, verdict in report:
    print(f"{rid}: {verdict}")
print(f"cpu_bench active row after amendment: {cpu_rows[-1]}")

if mode == "validate":
    print("preflight-valid")
    raise SystemExit(0)
if mode == "emit":
    with open(emit_path, "w", encoding="utf-8") as fh:
        fh.write(candidate)
    print(f"candidate written (validate-grade, not applied): {emit_path}")
    raise SystemExit(0)

fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".era-rows-")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(candidate)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)
except BaseException:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise
dfd = os.open(os.path.dirname(target), os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(dfd)
finally:
    os.close(dfd)

payload = {
    "schema": "epyc.operator_consolidated_era_rows.v1",
    "status": "ratified",
    "human_attestation": token,
    "ratified_at": datetime.now(UTC).isoformat(),
    "target": target,
    "applied_rows": applied,
    "struck_rows": sorted(skips),
    "row_sha256": {rid: hashlib.sha256(text.encode()).hexdigest() for rid, _, text in ROWS},
    "target_sha256_after": hashlib.sha256(candidate.encode()).hexdigest(),
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
# Keyed receipt-index pointer (C39 contract): the daemon's spent-gate check stats
# exactly artifacts/operator/receipts/<GATE_ID>.json, so write it at signing time.
index_dir = os.path.join(os.path.dirname(receipt), "receipts")
os.makedirs(index_dir, exist_ok=True)
index_path = os.path.join(index_dir, f"{token}.json")
with open(index_path, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": token, "indexed_by": "attest", "receipt": receipt,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
print(f"ratified: {receipt}")
print(f"receipt index: {index_path}")
PY

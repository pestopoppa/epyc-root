#!/bin/bash
# ratify_autopilot_relaunch_era_20261109.sh -- append ONE autopilot_speed instrument-era row
# (default id E21-autopilot-relaunch-speed) to epyc-orchestrator/orchestration/instrument_eras.yaml.
#
# WHY. The era registry is human-amendment-only (agents/shared/MEASUREMENT_POLICY.md ->
# Consolidated apply-time ratification), so an agent cannot apply this. Operator, 2026-11-09:
# "by the time we relaunch autopilot, we will need a brand new era setup; we can do this now".
# This is the pre-validated command: the operator runs it at the relaunch boundary, with the
# values the kernel promotion and stack reorg produce, reviews the diff and commits.
#
# WHAT IT RECORDS. A speed/frontier boundary: AutoPilot restarts on a new production kernel and a
# new serving lineup, so pre-boundary autopilot_speed rows and the Pareto frontier built from them
# are demote-to-prior for decisions about the relaunched stack (MEASUREMENT_POLICY: era-label, then
# apply the verb; never rescale across a boundary). One row, scope autopilot_speed. It carries the
# kernel identity (kernel_name / binary_version / kernel_commit, the field set E6/E8/E9 cpu-kernel
# rows use) and the lineup hash, plus the three instrument fields E9..E16 carry, copied by default
# from the latest autopilot_speed row (the eval instrument is unchanged by a relaunch).
#
# WHAT IT DOES NOT DO (each is a separate, existing path; named in the row's note):
#   - write orchestration/autopilot_state.json (pareto_epoch_ts, active_instrument_eras,
#     frontier_rerun_required): the autopilot-side ratify_and_apply_* path does that at start;
#   - append the cpu_bench kernel row: the kernel promotion does (this script CHECKS it exists);
#   - add an eval_quality row: quality scores transfer across kernel eras once parity is proven
#     (MEASUREMENT_POLICY, deterministic replay). Add one only if the eval instrument changes.
#
# REQUIRED ARGUMENTS (no defaults on purpose: each depends on the upcoming promotion / reorg and
# a guessed value would be a false identity in an append-only registry):
#   --from            relaunch boundary, UTC, YYYY-MM-DDTHH:MM:SSZ (the moment AutoPilot restarts
#                     on the new stack; must be later than every existing autopilot_speed `from`)
#   --kernel-name     e.g. production-consolidated-v11
#   --binary-version  llama-server --version number of the served binary (integer)
#   --kernel-commit   40-hex source commit the served binary was built from
#   --lineup-sha256   64-hex sha256 of the compiled lineup. Recommended source, AFTER the stack
#                     reorg has been compiled:  sha256sum orchestration/derived/stack_priors.yaml
#                     (its compiled content pins registry, descriptors and topology sources).
# OPTIONAL: --era-id, --policy-version, --execution-instrument-id, --scoring-schedule-id,
#   --allow-unregistered-kernel (skip the cpu_bench kernel-row cross-check), ORCH_ROOT=<path>.
#
# Usage (from /workspace):
#   bash scripts/operator/ratify_autopilot_relaunch_era_20261109.sh --dry-run <required args>
#   RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_autopilot_relaunch_era_20261109.sh --apply <required args>
#   ... --apply --commit <required args>        # also stage + commit the one file in ORCH_ROOT
# --dry-run (the default if neither --dry-run nor --apply is given) works on a COPY and writes
# nothing; the copy is where the diff preview comes from.
#
# Idempotent: re-running after a successful apply exits 0 and changes nothing (marker: the era id).
set -euo pipefail

ORCH_ROOT="${ORCH_ROOT:-/workspace/repos/epyc-orchestrator}"
ERAS_REL="orchestration/instrument_eras.yaml"
ERAS="$ORCH_ROOT/$ERAS_REL"
PRIOR_ANCHOR_ID="E20-eval-corpus-ev19-quality"
TAIL_ANCHOR="known_dead_instrument_items:"

ERA_ID="E21-autopilot-relaunch-speed"
MODE="dry-run"; DO_COMMIT=0; ALLOW_UNREG=0
FROM=""; KNAME=""; KBIN=""; KCOMMIT=""; LINEUP=""
POLICY=""; EXEC_ID=""; SCHED_ID=""

die() { echo "REFUSING: $*" >&2; exit "${2:-65}"; }
need_val() { [ $# -ge 2 ] || die "$1 needs a value" 64; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE="dry-run" ;;
    --apply)   MODE="apply" ;;
    --commit)  DO_COMMIT=1 ;;
    --allow-unregistered-kernel) ALLOW_UNREG=1 ;;
    --from)            need_val "$@"; FROM="$2"; shift ;;
    --kernel-name)     need_val "$@"; KNAME="$2"; shift ;;
    --binary-version)  need_val "$@"; KBIN="$2"; shift ;;
    --kernel-commit)   need_val "$@"; KCOMMIT="$2"; shift ;;
    --lineup-sha256)   need_val "$@"; LINEUP="$2"; shift ;;
    --era-id)          need_val "$@"; ERA_ID="$2"; shift ;;
    --policy-version)  need_val "$@"; POLICY="$2"; shift ;;
    --execution-instrument-id) need_val "$@"; EXEC_ID="$2"; shift ;;
    --scoring-schedule-id)     need_val "$@"; SCHED_ID="$2"; shift ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
  shift
done
[ "$DO_COMMIT" -eq 0 ] || [ "$MODE" = "apply" ] || die "--commit requires --apply" 64

[ -f "$ERAS" ] || die "$ERAS not found (set ORCH_ROOT=)" 66

# Idempotency BEFORE argument checks: a second run is a no-op, not an error.
if grep -qE "^  - id: ${ERA_ID}\$" "$ERAS"; then
  echo "already ratified: era '${ERA_ID}' is present in $ERAS -- nothing to do."
  exit 0
fi

# Required arguments: refused, never guessed.
missing=""
for pair in "--from:$FROM" "--kernel-name:$KNAME" "--binary-version:$KBIN" \
            "--kernel-commit:$KCOMMIT" "--lineup-sha256:$LINEUP"; do
  [ -n "${pair#*:}" ] || missing="$missing ${pair%%:*}"
done
[ -z "$missing" ] || die "required argument(s) not given:$missing
  These depend on the kernel promotion and stack reorg and are never defaulted." 64

# Unique anchors: the prior-era anchor and the insertion tail must each appear exactly once.
for a in "  - id: ${PRIOR_ANCHOR_ID}" "${TAIL_ANCHOR}"; do
  n=$(grep -cxF -- "$a" "$ERAS" || true)
  [ "$n" -eq 1 ] || die "anchor '$a' found $n time(s) in $ERAS, expected exactly 1; the registry has drifted, re-derive the insertion point." 65
done

if [ "$MODE" = "apply" ]; then
  source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ratify_operator.sh"
  ratify_require_operator
  git -C "$ORCH_ROOT" diff --quiet -- "$ERAS_REL" || die "$ERAS has uncommitted edits." 65
  git -C "$ORCH_ROOT" diff --cached --quiet || die "something is already staged in $ORCH_ROOT; refusing to commit alongside it." 65
fi

WORK="$(mktemp)"; trap 'rm -f "$WORK"' EXIT
cp "$ERAS" "$WORK"

# Append + validate in one place (python: YAML-aware checks, string insertion so the file keeps
# its comments and formatting). Prints the new row; exits non-zero with a reason on any refusal.
python3 - "$WORK" "$ERA_ID" "$FROM" "$KNAME" "$KBIN" "$KCOMMIT" "$LINEUP" \
          "$POLICY" "$EXEC_ID" "$SCHED_ID" "$ALLOW_UNREG" "$TAIL_ANCHOR" <<'PY'
import re, sys, datetime
import yaml
(path, era_id, frm, kname, kbin, kcommit, lineup, policy, exec_id, sched_id,
 allow_unreg, tail) = sys.argv[1:13]

def refuse(msg):
    sys.exit(f"REFUSING: {msg}")

if not re.fullmatch(r"E[0-9]+[A-Za-z0-9_.-]*", era_id):
    refuse(f"era id {era_id!r} does not look like an era id (E<n>-...)")
if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", frm):
    refuse(f"--from {frm!r} must be UTC YYYY-MM-DDTHH:MM:SSZ")
try:
    frm_dt = datetime.datetime.strptime(frm, "%Y-%m-%dT%H:%M:%SZ")
except ValueError as exc:
    refuse(f"--from {frm!r}: {exc}")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", kname):
    refuse(f"--kernel-name {kname!r} has unexpected characters")
if not re.fullmatch(r"[0-9]+", kbin):
    refuse(f"--binary-version {kbin!r} must be an integer (llama-server --version number)")
if not re.fullmatch(r"[0-9a-f]{40}", kcommit):
    refuse("--kernel-commit must be a full 40-hex commit")
if not re.fullmatch(r"[0-9a-f]{64}", lineup):
    refuse("--lineup-sha256 must be a 64-hex sha256")

text = open(path, encoding="utf-8").read()
doc = yaml.safe_load(text)
eras = doc["eras"]

def parse(ts):
    ts = str(ts)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(ts, fmt)
        except ValueError:
            pass
    return None

speed = [e for e in eras if e.get("scope") == "autopilot_speed" and e.get("from")]
latest = max(speed, key=lambda e: parse(e["from"]))
if frm_dt <= parse(latest["from"]):
    refuse(f"--from {frm} is not after the latest autopilot_speed era {latest['id']} ({latest['from']}); eras are append-only and ordered.")

# The kernel identity must already be a registered cpu_bench kernel era (the promotion writes it).
reg = [e for e in eras if e.get("scope") == "cpu_bench" and e.get("kernel_name") == kname
       and str(e.get("binary_version")) == kbin and str(e.get("kernel_commit")) == kcommit]
if not reg and allow_unreg != "1":
    refuse(f"no cpu_bench era with kernel_name={kname} binary_version={kbin} kernel_commit={kcommit[:12]}... "
           "is registered. The kernel promotion appends that row first; pass --allow-unregistered-kernel "
           "only if this kernel is deliberately not a registered cutover.")

# Instrument fields: carried from the latest autopilot_speed row unless given.
def carry(given, key):
    v = given or latest.get(key)
    if not v:
        refuse(f"no {key} given and the latest autopilot_speed era {latest['id']} carries none")
    return str(v)
policy = carry(policy, "policy_version")
exec_id = carry(exec_id, "execution_instrument_id")
sched_id = carry(sched_id, "scoring_schedule_id")
carried = f"carried from {latest['id']}"

row = f'''  - id: {era_id}
    from: "{frm}"
    scope: autopilot_speed
    kernel_name: {kname}
    binary_version: {kbin}
    kernel_commit: "{kcommit}"
    lineup_sha256: {lineup}
    policy_version: "{policy}"
    execution_instrument_id: "{exec_id}"
    scoring_schedule_id: "{sched_id}"
    note: >
      AutoPilot relaunch boundary (operator 2026-11-09: "by the time we relaunch autopilot, we
      will need a brand new era setup"). AutoPilot restarts on kernel {kname}
      (llama-server version {kbin}, source {kcommit[:12]}) and on the serving lineup whose
      compiled sha256 is {lineup[:16]}... (full value in lineup_sha256). The instrument fields
      above are {carried} unless they differ from it: a relaunch does not change the eval instrument.
      RECONCILIATION: pre-boundary autopilot_speed rows and the Pareto frontier built
      from them are demote-to-prior for decisions about the relaunched stack. Do not rescale
      across this boundary; rebuild the frontier from post-boundary numeric trials only.
      Era-label by timestamp against this id, never by eval_details.speed_metric_mode.
      NOT recorded by this row: autopilot_state.json (pareto_epoch_ts, active_instrument_eras,
      frontier_rerun_required) is advanced by the autopilot-side era-advance path at start;
      the cpu_bench kernel row belongs to the kernel promotion; quality scores transfer across
      the kernel boundary only once parity is proven (MEASUREMENT_POLICY), and an eval_quality
      row is added only if the eval instrument itself changes.

'''
if text.count("\n" + tail + "\n") != 1:
    refuse(f"expected exactly one '{tail}' line")
new = text.replace("\n" + tail + "\n", "\n" + row + tail + "\n", 1)
d2 = yaml.safe_load(new)
got = [e for e in d2["eras"] if e.get("id") == era_id]
assert len(got) == 1, got
g = got[0]
assert g["scope"] == "autopilot_speed" and g["from"] == frm and str(g["binary_version"]) == kbin, g
assert g["lineup_sha256"] == lineup and g["kernel_commit"] == kcommit, g
assert [e["id"] for e in d2["eras"][:-1]] == [e["id"] for e in eras], "existing rows changed or reordered"
assert d2["eras"][-1]["id"] == era_id, "new row is not the last era"
assert d2.get("known_dead_instrument_items") == doc.get("known_dead_instrument_items"), "tail changed"
open(path, "w", encoding="utf-8").write(new)
print(f"row parses: {g['id']} from {g['from']} scope {g['scope']} (carried instrument fields from {latest['id']})", file=sys.stderr)
PY

added=$(( $(wc -l < "$WORK") - $(wc -l < "$ERAS") ))
[ "$added" -gt 0 ] || die "transform added no lines; $ERAS untouched." 70
echo "--- diff (${added} lines added) ---"
diff -u "$ERAS" "$WORK" || true
echo "--- end diff ---"

if [ "$MODE" = "dry-run" ]; then
  echo
  echo "DRY RUN - nothing written to $ERAS. Re-run with --apply (and RATIFY_OPERATOR set) to apply."
  exit 0
fi

BACKUP="$ERAS.bak-$(date +%Y%m%d%H%M%S)"
cp "$ERAS" "$BACKUP"
cat "$WORK" > "$ERAS"
echo "APPLIED to $ERAS (backup: $BACKUP)."

if [ "$DO_COMMIT" -eq 1 ]; then
  git -C "$ORCH_ROOT" add -- "$ERAS_REL"
  git -C "$ORCH_ROOT" commit -m "RATIFIED: era ${ERA_ID} (AutoPilot relaunch boundary, kernel ${KNAME}, lineup ${LINEUP:0:12})

Operator-ratified (${RATIFY_OPERATOR}). One autopilot_speed era row appended; no existing row edited.
Pre-boundary autopilot_speed rows and the frontier built from them are demote-to-prior."
  echo "committed."
else
  echo "NOT committed. Review, then:  git -C $ORCH_ROOT add -- $ERAS_REL && git -C $ORCH_ROOT commit"
fi

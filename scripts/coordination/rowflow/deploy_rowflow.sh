#!/bin/bash
# deploy_rowflow.sh - the ONLY sanctioned way to install rowflow into compute-flags/bin/rowflow/ (operator 2026-11-05,
# "Harness first, then class fixes"; keeper-friction review P2.4 #3/#4).
#
#   deploy_rowflow.sh [--ref origin/main] [--repo /workspace] [--check-only] [--allow-open-grants] [--no-rollback] [--keep-stage]
#   deploy_rowflow.sh --parity [--ref origin/main] [--repo /workspace]
#   Takes a deploy flock (<flags>/.deploy_rowflow.lock; a second deploy is refused, rc 79) and a LIGHT claim on 84-87 (--by <owner>,
#   default $USER; retried every 60 s up to 15 tries) under which both test gates run (nice -n 19 taskset -c 84-87); released on exit.
#
# WHAT is installed: every line of scripts/coordination/INSTALL.manifest at <ref> (published path under compute-flags/,
# repo source path, class) - bin/rowflow, bin/churn, bin/job_templates, bin/ helpers and the keeper/loop scripts. There is
# no second installer: churn_up.sh only runs --parity (pipeline audit 2026-11-10 #6).
# --parity  read-only: per manifest line print SAME / DIFF / MISSING (installed file vs <ref>'s source blob); exit 0 when
#           everything is SAME, 1 on any DIFF or MISSING. Stages nothing, runs no gate, touches nothing.
#
# 1. stage    a detached `git worktree add` of <ref> in a fresh scratch dir (never the shared working tree: what is
#             tested is exactly what is installed); this run's stage (and the replay scratch inside it, $STAGE/.replay-scratch)
#             is removed on EVERY exit (2026-11-24; logs deploy-<ts>-{unit,replay}.log live beside it and are kept). A non-zero
#             exit keeps ONLY the newest stage as deploy-<ts>-REFUSED-keep (an older REFUSED-keep is replaced);
#             --keep-stage keeps this run's stage. Removal is `git worktree remove` only, never rm.
# 2. test     the staged tree's unit tests (tests/test_rowflow*.py, test_allocator.py, test_churn_*.py, test_auto_file.py,
#             test_install_manifest.py, test_handoff_ref.py) AND the replay gate
#             (tests/replay/test_replay_gate.py from THIS script's tree, run against the staged rowflow/). Any failure
#             refuses the deploy; nothing under bin/ is touched.
# 3. guard    an engine file a running poller re-reads (filler_run15.sh, filler_lib.sh, notify.py, diskpause.py) is never
#             swapped while LEGACY grants are open (pollers on the live path) unless --allow-open-grants; snapshot-launched
#             grants (armed since 2026-11-07, engine copied into dryrun/<id>/engine/) never block (rowflow.py deploy-guard)
# 4. install  per changed manifest entry: backup <f>.bak-<UTC>-deploy, copy to <f>.part, chmod, mv -f (atomic), verify sha256
# 5. record   bin/rowflow/DEPLOYED.json {ref, sha, at, files{name: sha256}, gate}
# 6. verify   the keeper log must show a SNAPSHOT after the install and no Traceback within --verify-s (300 s);
#             otherwise the backups are restored (unless --no-rollback) and the script exits 3.
#
# FREEZE: only filler_run15.sh (the engine running pollers re-read) is frozen, at 9218dffd131008117a5f341848dce572b4669486.
# A deploy that would change it is REFUSED (exit 77) before the gates run, unless --emergency "<reason>" is given; the
# reason, the file and the UTC time are recorded in DEPLOYED.json (`emergency`, appended to `emergency_log`). The unit +
# replay gates still apply. rowflow.py and publish_row.py were frozen 2026-11-05 ("Freeze current + build rowflow2") and
# UNFROZEN by operator decision 2026-11-10 ("Lift freeze on 2, keep engine (Recommended)", pipeline audit finding #14):
# they deploy through the unit + replay gates with a D9-ack on the commit and no per-change emergency override.
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPLAY_DIR=$(cd "$HERE/../tests/replay" && pwd)
REF=origin/main
REPO=/workspace
FLAGS=${ROWFLOW_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
BIN="$FLAGS/bin/rowflow"
LOG="$FLAGS/ws58-calendar-keeper.log"
KEEP_STAGE=0; CHECK_ONLY=0; PARITY=0; ALLOW_OPEN=0; ROLLBACK=1; VERIFY_S=300; EMERGENCY=""
BY=${DEPLOY_BY:-${USER:-pipeline-mgmt}}; NO_LIGHT=${DEPLOY_NO_LIGHT:-0}; SELFTEST_CLAIM=0
LOCK_FILE=${DEPLOY_LOCK_FILE:-$FLAGS/.deploy_rowflow.lock}
FROZEN=(bin/rowflow/filler_run15.sh)   # operator 2026-11-10: rowflow.py/publish_row.py unfrozen
FROZEN_AT=9218dffd131008117a5f341848dce572b4669486
MANIFEST_REL=scripts/coordination/INSTALL.manifest
SCRATCH=${REPLAY_SCRATCH:-/mnt/raid0/llm/tmp/rowflow-replay}

while [ $# -gt 0 ]; do
  case "$1" in
    --ref) REF=$2; shift 2 ;;
    --repo) REPO=$2; shift 2 ;;
    --keep-stage) KEEP_STAGE=1; shift ;;
    --check-only) CHECK_ONLY=1; shift ;;
    --parity) PARITY=1; shift ;;
    --allow-open-grants) ALLOW_OPEN=1; shift ;;
    --no-rollback) ROLLBACK=0; shift ;;
    --verify-s) VERIFY_S=$2; shift 2 ;;
    --by) BY=$2; shift 2 ;;
    --no-light-claim) NO_LIGHT=1; shift ;;
    --selftest-claim) SELFTEST_CLAIM=1; shift ;;
    --emergency) EMERGENCY=${2:-}; shift 2
      [ -n "${EMERGENCY// /}" ] || { echo "REFUSED: --emergency needs a non-empty reason" >&2; exit 64; } ;;
    -h|--help) sed -n 2,37p "$0"; exit 0 ;;
    *) echo "unknown arg $1" >&2; exit 64 ;;
  esac
done

# manifest_entries <manifest file>: "published source class" per non-comment line
manifest_entries() { sed -e 's/#.*//' "$1" | awk 'NF >= 2 {print $1, $2, ($3 == "" ? "hot" : $3)}'; }

if [ "$PARITY" = 1 ]; then
  PSHA=$(git -C "$REPO" rev-parse --verify "$REF^{commit}")
  PMAN=$(git -C "$REPO" show "$PSHA:$MANIFEST_REL") || { echo "PARITY: $REF has no $MANIFEST_REL" >&2; exit 65; }
  DRIFT=0
  while read -r pub src _cls; do
    want=$(git -C "$REPO" show "$PSHA:$src" 2>/dev/null | sha256sum | cut -c1-64)
    if ! git -C "$REPO" cat-file -e "$PSHA:$src" 2>/dev/null; then printf 'MISSING-SRC %-40s %s\n' "$pub" "$src"; DRIFT=1
    elif [ ! -f "$FLAGS/$pub" ]; then printf 'MISSING     %-40s %s\n' "$pub" "$src"; DRIFT=1
    elif [ "$(sha256sum < "$FLAGS/$pub" | cut -c1-64)" = "$want" ]; then printf 'SAME        %-40s %s\n' "$pub" "$src"
    else printf 'DIFF        %-40s %s\n' "$pub" "$src"; DRIFT=1; fi
  done < <(manifest_entries <(printf '%s\n' "$PMAN"))
  [ "$DRIFT" = 0 ] && echo "PARITY OK: $FLAGS equals $MANIFEST_REL @ ${PSHA:0:9}" \
    || echo "PARITY DRIFT: $FLAGS differs from $MANIFEST_REL @ ${PSHA:0:9}; install with deploy_rowflow.sh --ref $REF" >&2
  exit "$DRIFT"
fi

# ---- 0. one deploy at a time (2026-11-23: two ran concurrently) + the test gate runs on a LIGHT claim (84-87, <= 15 min, retried
# every 60 s), never on the cores a quiet row or a build holds. The flock is released by the kernel when this shell exits.
mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "REFUSED: another deploy_rowflow.sh holds $LOCK_FILE (two deploys must never run at once); retry when it ends" >&2; exit 79
fi
LIGHT_GID=""; GATE_PREFIX=()
release_light() {
  if [ -n "$LIGHT_GID" ]; then
    nice -n 19 taskset -c 84-87 python3 "$BIN/rowflow.py" --flags "$FLAGS" release "$LIGHT_GID" --by "$BY" --reason deploy-gate-done >/dev/null 2>&1 || true
    LIGHT_GID=""
  fi
}
take_light() {
  [ "$NO_LIGHT" = 1 ] && return 0
  local i out
  for i in $(seq 1 ${DEPLOY_LIGHT_TRIES:-15}); do
    if out=$(nice -n 19 taskset -c 84-87 python3 "$BIN/rowflow.py" --flags "$FLAGS" claim --build --light --owner "$BY" --cpus 84-87 --minutes 15 2>&1); then
      LIGHT_GID=$(printf '%s\n' "$out" | awk '/^BUILD-GRANT/ {print $2; exit}')
      [ -n "$LIGHT_GID" ] && { GATE_PREFIX=(nice -n 19 taskset -c 84-87); echo "deploy_rowflow: light claim $LIGHT_GID on 84-87 (owner $BY)"; return 0; }
    fi
    echo "deploy_rowflow: light claim refused (${out##*$'\n'}); retry in ${DEPLOY_LIGHT_RETRY_S:-60}s ($i/${DEPLOY_LIGHT_TRIES:-15})" >&2
    sleep "${DEPLOY_LIGHT_RETRY_S:-60}"
  done
  echo "REFUSED: no light claim on 84-87 within the retry budget; nothing installed" >&2; exit 80
}
trap release_light EXIT
if [ "$SELFTEST_CLAIM" = 1 ]; then take_light; echo "GATE_PREFIX=${GATE_PREFIX[*]:-}"; exit 0; fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$SCRATCH"
STAGE=$(mktemp -d "$SCRATCH/deploy-$TS-XXXX")
SHA=$(git -C "$REPO" rev-parse --verify "$REF^{commit}")
echo "deploy_rowflow: ref=$REF sha=$SHA stage=$STAGE"
rmdir "$STAGE"
git -C "$REPO" worktree add --detach -q "$STAGE" "$SHA"
cleanup_stage() {
  local rc=$?
  trap - EXIT
  release_light
  if [ "$KEEP_STAGE" = 1 ]; then
    echo "deploy_rowflow: --keep-stage: stage left at $STAGE" >&2
  elif [ "$rc" != 0 ] && [ -d "$STAGE" ]; then
    local old
    for old in "$SCRATCH"/deploy-*-REFUSED-keep; do      # only the previous REFUSED-keep is replaced; no other deploy's path is matched
      [ -d "$old" ] && { git -C "$REPO" worktree remove --force "$old" >/dev/null 2>&1 || true; }
    done
    if git -C "$REPO" worktree move "$STAGE" "$SCRATCH/deploy-$TS-REFUSED-keep" >/dev/null 2>&1; then
      echo "deploy_rowflow: refused (rc $rc); newest stage kept at $SCRATCH/deploy-$TS-REFUSED-keep" >&2
    else
      git -C "$REPO" worktree remove --force "$STAGE" >/dev/null 2>&1 || true
    fi
  else
    git -C "$REPO" worktree remove --force "$STAGE" >/dev/null 2>&1 || true
  fi
  exit "$rc"
}
trap cleanup_stage EXIT
take_light
CAND="$STAGE/scripts/coordination/rowflow"
[ -f "$CAND/rowflow.py" ] || { echo "REFUSED: $SHA has no scripts/coordination/rowflow/rowflow.py" >&2; exit 65; }
[ -f "$STAGE/$MANIFEST_REL" ] || { echo "REFUSED: $SHA has no $MANIFEST_REL" >&2; exit 65; }
declare -A SRC_OF=()
ENTRIES=()
while read -r pub src _cls; do
  [ -f "$STAGE/$src" ] || { echo "REFUSED: $MANIFEST_REL names $src, missing at $SHA" >&2; exit 65; }
  SRC_OF[$pub]=$src; ENTRIES+=("$pub")
done < <(manifest_entries "$STAGE/$MANIFEST_REL")

# ---- 1b. freeze (before any gate: a frozen file never reaches the gates without an emergency reason)
FROZEN_TOUCHED=()
for f in "${FROZEN[@]}"; do
  src=${SRC_OF[$f]:-}
  if [ -n "$src" ] && { [ ! -f "$FLAGS/$f" ] || [ "$(sha256sum < "$STAGE/$src")" != "$(sha256sum < "$FLAGS/$f")" ]; }; then
    FROZEN_TOUCHED+=("$(basename "$f")")
  fi
done
if [ ${#FROZEN_TOUCHED[@]} -gt 0 ]; then
  if [ -z "$EMERGENCY" ]; then
    echo "REFUSED: FROZEN at ${FROZEN_AT:0:9} (operator 2026-11-05, kept 2026-11-10): $SHA changes ${FROZEN_TOUCHED[*]}; pass --emergency \"<reason>\" (logged in DEPLOYED.json)" >&2
    exit 77
  fi
  echo "deploy_rowflow: EMERGENCY override of the freeze for ${FROZEN_TOUCHED[*]}: $EMERGENCY"
fi

# ---- 2. tests
UNIT=()
for t in "$STAGE"/scripts/coordination/tests/test_rowflow*.py "$STAGE"/scripts/coordination/tests/test_allocator.py \
         "$STAGE"/scripts/coordination/tests/test_churn_*.py "$STAGE"/scripts/coordination/tests/test_auto_file.py \
         "$STAGE"/scripts/coordination/tests/test_install_manifest.py "$STAGE"/scripts/coordination/tests/test_handoff_ref.py; do
  [ -f "$t" ] && UNIT+=("$t")
done
echo "deploy_rowflow: unit tests (${#UNIT[@]} files)"
if ! (cd "$STAGE" && "${GATE_PREFIX[@]}" python3 -m pytest -q -p no:cacheprovider "${UNIT[@]}" > "$SCRATCH/deploy-$TS-unit.log" 2>&1); then
  tail -30 "$SCRATCH/deploy-$TS-unit.log"; echo "REFUSED: unit tests failed ($SCRATCH/deploy-$TS-unit.log); nothing installed" >&2; exit 1
fi
tail -1 "$SCRATCH/deploy-$TS-unit.log"
# NIB2-108 scan gate: a deployed script the repo hook would refuse (delete primitive + literal scratch root) can never be run by an agent
for pub in "${ENTRIES[@]}"; do
  src=${SRC_OF[$pub]}; case "$src" in *.sh) interp=bash ;; *.py) interp=python3 ;; *) continue ;; esac
  if ! printf '%s %s\n' "$interp" "$STAGE/$src" | python3 "$REPO/scripts/hooks/destructive_scratch_scan.py" >/dev/null 2>&1 \
     && ! python3 -c 'import json,os,sys; sys.exit(0 if os.path.realpath(sys.argv[1]) in json.load(open(sys.argv[2])) else 1)' "$FLAGS/$pub" "$REPO/scripts/hooks/destructive_scratch_pins.json" 2>/dev/null; then
    echo "REFUSED: $src would be blocked by the NIB2-108 hook (delete primitive + literal scratch root); reword it or pin $FLAGS/$pub in scripts/hooks/destructive_scratch_pins.json; nothing installed" >&2; exit 78
  fi
done
echo "deploy_rowflow: replay gate (harness $REPLAY_DIR)"
if ! ROWFLOW_CANDIDATE="$CAND" REPLAY_SCRATCH="$STAGE/.replay-scratch" "${GATE_PREFIX[@]}" python3 -m pytest -q -p no:cacheprovider "$REPLAY_DIR/test_replay_gate.py" > "$SCRATCH/deploy-$TS-replay.log" 2>&1; then
  sed -n "/^\(FAILED\|E  \)/p" "$SCRATCH/deploy-$TS-replay.log" | sed -n 1,30p; echo "REFUSED: replay gate failed ($SCRATCH/deploy-$TS-replay.log); nothing installed" >&2; exit 1
fi
tail -1 "$SCRATCH/deploy-$TS-replay.log"
if [ "$CHECK_ONLY" = 1 ]; then echo "deploy_rowflow: --check-only: gates PASS, nothing installed"; exit 0; fi

# ---- 3. guard
CHANGED=()
GUARD_NAMES=()   # deploy-guard speaks bin/rowflow basenames (rowflow.ENGINE_REREAD)
for f in "${ENTRIES[@]}"; do
  if [ ! -f "$FLAGS/$f" ] || [ "$(sha256sum < "$STAGE/${SRC_OF[$f]}")" != "$(sha256sum < "$FLAGS/$f")" ]; then
    CHANGED+=("$f"); [ "${f#bin/rowflow/}" != "$f" ] && GUARD_NAMES+=("${f#bin/rowflow/}")
  fi
done
[ ${#CHANGED[@]} -gt 0 ] || { echo "deploy_rowflow: $FLAGS already equals $MANIFEST_REL @ $SHA"; exit 0; }
# no-hold deploys (operator 2026-11-07): rows armed by a snapshot-aware keeper run their own engine copy
# (<flags>/dryrun/<id>/engine/), so only LEGACY open grants - pollers that still read bin/rowflow/ - can block a change to
# a file a running poller re-reads (rowflow.ENGINE_REREAD). The candidate's own deploy_guard decides.
GUARD_ARGS=(); [ "$ALLOW_OPEN" = 1 ] && GUARD_ARGS=(--allow-open-grants)
if [ ${#GUARD_NAMES[@]} -gt 0 ]; then
  if ! GUARD=$(ROWFLOW_FLAGS="$FLAGS" python3 -I "$CAND/rowflow.py" --flags "$FLAGS" deploy-guard --changed "${GUARD_NAMES[@]}" "${GUARD_ARGS[@]}" 2>&1); then
    echo "$GUARD" >&2
    exit 75
  fi
  echo "deploy_rowflow: guard: $GUARD"
fi

# ---- 4. install
T0=$(date -u +%s)
for f in "${CHANGED[@]}"; do
  src="$STAGE/${SRC_OF[$f]}"; dst="$FLAGS/$f"
  mkdir -p "$(dirname "$dst")"
  [ -f "$dst" ] && cp -p "$dst" "$dst.bak-$TS-deploy"
  cp "$src" "$dst.part"
  case "$f" in *.py|*.sh) chmod 0755 "$dst.part" ;; *) chmod 0644 "$dst.part" ;; esac
  mv -f "$dst.part" "$dst"
  [ "$(sha256sum < "$src")" = "$(sha256sum < "$dst")" ] || { echo "INSTALL VERIFY FAILED: $f" >&2; exit 2; }
  echo "  installed $f (backup $(basename "$f").bak-$TS-deploy)"
done
ROWFLOW_EMERGENCY="$EMERGENCY" ROWFLOW_FROZEN_TOUCHED="${FROZEN_TOUCHED[*]:-}" ROWFLOW_FROZEN_AT="$FROZEN_AT" \
ROWFLOW_INSTALLED="${ENTRIES[*]}" python3 - "$BIN/DEPLOYED.json" "$REF" "$SHA" "$TS" "$FLAGS" "${CHANGED[@]}" <<'PY'
import hashlib, json, os, sys
out, ref, sha, ts, flags, *changed = sys.argv[1:]
try:
    prev = json.load(open(out))
except (OSError, ValueError):
    prev = {}
elog = list(prev.get("emergency_log") or [])
reason, touched = os.environ.get("ROWFLOW_EMERGENCY", ""), os.environ.get("ROWFLOW_FROZEN_TOUCHED", "").split()
emergency = {"reason": reason, "files": touched, "at": ts, "sha": sha} if (reason and touched) else None
if emergency:
    elog.append(emergency)
files = {f: hashlib.sha256(open(os.path.join(flags, f), "rb").read()).hexdigest()
         for f in os.environ.get("ROWFLOW_INSTALLED", "").split() if os.path.isfile(os.path.join(flags, f))}
json.dump({"ref": ref, "sha": sha, "at": ts, "changed": changed, "files": files, "gate": "unit+replay PASS",
           "manifest": "scripts/coordination/INSTALL.manifest",
           "frozen": {"files": ["filler_run15.sh"], "at": os.environ.get("ROWFLOW_FROZEN_AT"),
                      "exit": "rowflow2 passes its shadow week (docs/design/rowflow2-20261105.md)",
                      "unfrozen": {"files": ["rowflow.py", "publish_row.py"], "at": "2026-11-10", "by": "operator: Lift freeze on 2, keep engine"}},
           "emergency": emergency, "emergency_log": elog},
          open(out + ".part", "w"), indent=1, sort_keys=True)
os.replace(out + ".part", out)
PY

# ---- 6. verify
rollback() {
  [ "$ROLLBACK" = 1 ] || { echo "deploy_rowflow: --no-rollback: leaving $SHA installed" >&2; return; }
  for f in "${CHANGED[@]}"; do
    if [ -f "$FLAGS/$f.bak-$TS-deploy" ]; then cp -p "$FLAGS/$f.bak-$TS-deploy" "$FLAGS/$f.part" && mv -f "$FLAGS/$f.part" "$FLAGS/$f"; fi
  done
  echo "deploy_rowflow: ROLLED BACK to the $TS backups" >&2
}
echo "deploy_rowflow: waiting up to ${VERIFY_S}s for a keeper SNAPSHOT after the install"
DEADLINE=$((T0 + VERIFY_S))
while :; do
  NEW=$(python3 - "$LOG" "$T0" <<'PY'
import datetime as dt, sys
log, t0 = sys.argv[1], int(sys.argv[2])
snap = bad = 0
try:
    with open(log, "rb") as f:
        f.seek(0, 2); f.seek(max(0, f.tell() - (8 << 20)))
        for raw in f.read().decode("utf8", "replace").splitlines():
            try:
                t = dt.datetime.strptime(raw[:20], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
            except ValueError:
                t = None
            if t is not None and t < t0:
                continue
            if "Traceback" in raw or "SyntaxError" in raw or "ImportError" in raw:
                bad += 1
            if " SNAPSHOT " in raw:
                snap += 1
except OSError:
    pass
print(f"{snap} {bad}")
PY
)
  SNAP=${NEW% *}; BAD=${NEW#* }
  if [ "$BAD" -gt 0 ]; then echo "POST-DEPLOY FAIL: $BAD traceback line(s) in $LOG" >&2; rollback; exit 3; fi
  if [ "$SNAP" -gt 0 ]; then echo "deploy_rowflow: OK - $SNAP SNAPSHOT line(s) since install, no traceback; $SHA live"; exit 0; fi
  if [ "$(date -u +%s)" -ge "$DEADLINE" ]; then echo "POST-DEPLOY FAIL: no keeper SNAPSHOT within ${VERIFY_S}s" >&2; rollback; exit 3; fi
  sleep 10
done

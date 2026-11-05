#!/bin/bash
# deploy_rowflow.sh - the ONLY sanctioned way to install rowflow into compute-flags/bin/rowflow/ (operator 2026-11-05,
# "Harness first, then class fixes"; keeper-friction review P2.4 #3/#4).
#
#   deploy_rowflow.sh [--ref origin/main] [--repo /workspace] [--check-only] [--allow-open-grants] [--no-rollback]
#
# 1. stage    a detached `git worktree add` of <ref> in a fresh scratch dir (never the shared working tree: what is
#             tested is exactly what is installed); removed on exit
# 2. test     the staged tree's unit tests (tests/test_rowflow*.py, test_allocator.py) AND the replay gate
#             (tests/replay/test_replay_gate.py from THIS script's tree, run against the staged rowflow/). Any failure
#             refuses the deploy; nothing under bin/ is touched.
# 3. guard    filler_run15.sh is never swapped under open grants (running pollers re-read it) unless --allow-open-grants
# 4. install  per changed file: backup <f>.bak-<UTC>-deploy, copy to <f>.part, chmod, mv -f (atomic), verify sha256
# 5. record   bin/rowflow/DEPLOYED.json {ref, sha, at, files{name: sha256}, gate}
# 6. verify   the keeper log must show a SNAPSHOT after the install and no Traceback within --verify-s (300 s);
#             otherwise the backups are restored (unless --no-rollback) and the script exits 3.
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPLAY_DIR=$(cd "$HERE/../tests/replay" && pwd)
REF=origin/main
REPO=/workspace
FLAGS=${ROWFLOW_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
BIN="$FLAGS/bin/rowflow"
LOG="$FLAGS/ws58-calendar-keeper.log"
CHECK_ONLY=0; ALLOW_OPEN=0; ROLLBACK=1; VERIFY_S=300
FILES=(rowflow.py publish_row.py notify.py hostutil.py grant_ok_launcher.py filler_run15.sh filler_lib.sh run_direct.py run_direct.sh)
SCRATCH=${REPLAY_SCRATCH:-/mnt/raid0/llm/tmp/rowflow-replay}

while [ $# -gt 0 ]; do
  case "$1" in
    --ref) REF=$2; shift 2 ;;
    --repo) REPO=$2; shift 2 ;;
    --check-only) CHECK_ONLY=1; shift ;;
    --allow-open-grants) ALLOW_OPEN=1; shift ;;
    --no-rollback) ROLLBACK=0; shift ;;
    --verify-s) VERIFY_S=$2; shift 2 ;;
    -h|--help) sed -n 2,20p "$0"; exit 0 ;;
    *) echo "unknown arg $1" >&2; exit 64 ;;
  esac
done

TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$SCRATCH"
STAGE=$(mktemp -d "$SCRATCH/deploy-$TS-XXXX")
SHA=$(git -C "$REPO" rev-parse --verify "$REF^{commit}")
echo "deploy_rowflow: ref=$REF sha=$SHA stage=$STAGE"
rmdir "$STAGE"
git -C "$REPO" worktree add --detach -q "$STAGE" "$SHA"
trap 'git -C "$REPO" worktree remove --force "$STAGE" >/dev/null 2>&1 || true' EXIT
CAND="$STAGE/scripts/coordination/rowflow"
[ -f "$CAND/rowflow.py" ] || { echo "REFUSED: $SHA has no scripts/coordination/rowflow/rowflow.py" >&2; exit 65; }

# ---- 2. tests
UNIT=()
for t in "$STAGE"/scripts/coordination/tests/test_rowflow*.py "$STAGE"/scripts/coordination/tests/test_allocator.py; do
  [ -f "$t" ] && UNIT+=("$t")
done
echo "deploy_rowflow: unit tests (${#UNIT[@]} files)"
if ! (cd "$STAGE" && python3 -m pytest -q -p no:cacheprovider "${UNIT[@]}" > "$SCRATCH/deploy-$TS-unit.log" 2>&1); then
  tail -30 "$SCRATCH/deploy-$TS-unit.log"; echo "REFUSED: unit tests failed ($SCRATCH/deploy-$TS-unit.log); nothing installed" >&2; exit 1
fi
tail -1 "$SCRATCH/deploy-$TS-unit.log"
echo "deploy_rowflow: replay gate (harness $REPLAY_DIR)"
if ! ROWFLOW_CANDIDATE="$CAND" REPLAY_SCRATCH="$SCRATCH/deploy-$TS-replay" python3 -m pytest -q -p no:cacheprovider "$REPLAY_DIR/test_replay_gate.py" > "$SCRATCH/deploy-$TS-replay.log" 2>&1; then
  grep -E "^(FAILED|E  )" "$SCRATCH/deploy-$TS-replay.log" | head -30; echo "REFUSED: replay gate failed ($SCRATCH/deploy-$TS-replay.log); nothing installed" >&2; exit 1
fi
tail -1 "$SCRATCH/deploy-$TS-replay.log"
if [ "$CHECK_ONLY" = 1 ]; then echo "deploy_rowflow: --check-only: gates PASS, nothing installed"; exit 0; fi

# ---- 3. guard
CHANGED=()
for f in "${FILES[@]}"; do
  [ -f "$CAND/$f" ] || continue
  if [ ! -f "$BIN/$f" ] || [ "$(sha256sum < "$CAND/$f")" != "$(sha256sum < "$BIN/$f")" ]; then CHANGED+=("$f"); fi
done
[ ${#CHANGED[@]} -gt 0 ] || { echo "deploy_rowflow: bin/rowflow already equals $SHA"; exit 0; }
OPEN=$(find "$FLAGS/grants" -maxdepth 1 -name '*.grant' | wc -l)
for f in "${CHANGED[@]}"; do
  if [ "$f" = filler_run15.sh ] || [ "$f" = filler_lib.sh ]; then
    if [ "$OPEN" -gt 0 ] && [ "$ALLOW_OPEN" = 0 ]; then
      echo "REFUSED: $f changes while $OPEN grant(s) are open (running pollers re-read the engine); retry when grants/ is empty or pass --allow-open-grants" >&2
      exit 75
    fi
  fi
done

# ---- 4. install
T0=$(date -u +%s)
for f in "${CHANGED[@]}"; do
  [ -f "$BIN/$f" ] && cp -p "$BIN/$f" "$BIN/$f.bak-$TS-deploy"
  cp "$CAND/$f" "$BIN/$f.part"
  chmod 0755 "$BIN/$f.part"
  mv -f "$BIN/$f.part" "$BIN/$f"
  [ "$(sha256sum < "$CAND/$f")" = "$(sha256sum < "$BIN/$f")" ] || { echo "INSTALL VERIFY FAILED: $f" >&2; exit 2; }
  echo "  installed $f (backup $f.bak-$TS-deploy)"
done
python3 - "$BIN/DEPLOYED.json" "$REF" "$SHA" "$TS" "$CAND" "${CHANGED[@]}" <<'PY'
import hashlib, json, os, sys
out, ref, sha, ts, cand, *changed = sys.argv[1:]
files = {f: hashlib.sha256(open(os.path.join(os.path.dirname(out), f), "rb").read()).hexdigest()
         for f in os.listdir(os.path.dirname(out)) if f.endswith((".py", ".sh")) and ".bak" not in f}
json.dump({"ref": ref, "sha": sha, "at": ts, "changed": changed, "files": files, "gate": "unit+replay PASS"},
          open(out + ".part", "w"), indent=1, sort_keys=True)
os.replace(out + ".part", out)
PY

# ---- 6. verify
rollback() {
  [ "$ROLLBACK" = 1 ] || { echo "deploy_rowflow: --no-rollback: leaving $SHA installed" >&2; return; }
  for f in "${CHANGED[@]}"; do
    if [ -f "$BIN/$f.bak-$TS-deploy" ]; then cp -p "$BIN/$f.bak-$TS-deploy" "$BIN/$f.part" && mv -f "$BIN/$f.part" "$BIN/$f"; fi
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

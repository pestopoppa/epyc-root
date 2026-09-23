#!/bin/bash
# Regression test: daemon_provenance.sh's startup self-attestation.
#
# WHY THIS EXISTS (NIB2-81, remedy (a); tmp/daemon-staleness-20260917/report.md).
# bash holds a script's inode open for the life of the process, so a committed
# fix never reaches a daemon that started before the commit landed. dp_attest
# is the startup gate ("a lane may develop a daemon, never run it") and
# dp_stale_since_start is the cheap per-iteration check a daemon loop polls to
# LOG that a commit has since replaced the file it is executing.
#
# SCOPE: this exercises the two functions directly, in throwaway temp dirs and
# a throwaway git repo — never real pidfiles/logs, never the shared clone.
# Modelled on scripts/coordination/tests/test_supervisor_stale_source.sh
# (extract-and-source the functions under test, isolate every global).
set -euo pipefail
cd "$(dirname "$0")/../../.." || exit 1
HELPER=scripts/coordination/daemon_provenance.sh

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

# shellcheck source=../daemon_provenance.sh
source "$HELPER"

# ---------------------------------------------------------------------------
# Fixture: a throwaway CANONICAL root — a real git repo, so `git hash-object`
# and `git rev-parse HEAD:<path>` (which dp_attest actually runs) are tested
# for real, not stubbed. DP_CANONICAL_ROOT points dp_attest at this fixture
# instead of the real /workspace — the override this repo's own scripts use
# only from tests (mirrors EPYC_BUS_ROOT in bus_supervisor.sh).
CANON="$TMP/canon"
mkdir -p "$CANON/scripts/system"
cat > "$CANON/scripts/system/daemon.sh" <<'EOF'
#!/bin/bash
echo "daemon v1"
EOF
git -C "$CANON" init -q
git -C "$CANON" -c user.email=t@t -c user.name=t add scripts/system/daemon.sh >/dev/null
git -C "$CANON" -c user.email=t@t -c user.name=t commit -qm init >/dev/null
export DP_CANONICAL_ROOT="$CANON"

# A LANE dir, structurally identical, but never the canonical root.
LANE="$TMP/lane-worktree"
mkdir -p "$LANE/scripts/system"
cp "$CANON/scripts/system/daemon.sh" "$LANE/scripts/system/daemon.sh"

PROV="$TMP/daemon.pid.provenance.json"

# --------------------------------------------------------------- case 1: OK
rc=0; dp_attest "$CANON/scripts/system/daemon.sh" "$PROV" || rc=$?
chk "script under fake canonical root -> attest OK" "$rc" 0
if [ -s "$PROV" ]; then echo "  PASS  provenance file written"; pass=$((pass+1));
else echo "  FAIL  provenance file NOT written"; fail=$((fail+1)); fi

# NOTE the pid this test process checks against is $$ (this script's own pid),
# because dp_attest's `$$` inside the sourced function IS this test process —
# sourcing, not a subshell.
if python3 - "$PROV" "$CANON/scripts/system/daemon.sh" "$$" <<'PY_EOF'
import json, os, sys
prov_path, script, want_pid = sys.argv[1], sys.argv[2], int(sys.argv[3])
rec = json.load(open(prov_path))
real = os.path.realpath(script)
errs = []
if rec.get("pid") != want_pid:
    errs.append(f"pid {rec.get('pid')} != {want_pid}")
if rec.get("script_realpath") != real:
    errs.append(f"script_realpath {rec.get('script_realpath')} != {real}")
if rec.get("inode") != os.stat(real).st_ino:
    errs.append(f"inode {rec.get('inode')} != {os.stat(real).st_ino}")
if not rec.get("blob"):
    errs.append("blob missing")
if not rec.get("started_at"):
    errs.append("started_at missing")
if errs:
    sys.stderr.write("BAD: " + "; ".join(errs) + "\n")
    sys.exit(1)
PY_EOF
then
  echo "  PASS  provenance JSON fields (pid, script_realpath, inode, blob, started_at)"; pass=$((pass+1))
else
  echo "  FAIL  provenance JSON fields wrong"; fail=$((fail+1))
fi

# ------------------------------------------------------------ case 2: refused
rc=0; err="$(dp_attest "$LANE/scripts/system/daemon.sh" "$TMP/lane.provenance.json" 2>&1 1>/dev/null)" || rc=$?
chk "script under a fake lane dir -> refused non-zero" "$rc" 3
case "$err" in
  *"REFUSING"*"never run it"*) echo "  PASS  refusal names the never-run-it rule"; pass=$((pass+1));;
  *) echo "  FAIL  refusal message missing expected text: $err"; fail=$((fail+1));;
esac
if [ -e "$TMP/lane.provenance.json" ]; then
  echo "  FAIL  provenance file written on a REFUSED attest (must not happen)"; fail=$((fail+1))
else
  echo "  PASS  no provenance file written on refusal"; pass=$((pass+1))
fi

# --------------------------------------------------------- case 3: uncommitted
echo '# a hotfix on canon' >> "$CANON/scripts/system/daemon.sh"
rc=0; err="$(dp_attest "$CANON/scripts/system/daemon.sh" "$TMP/edit.provenance.json" 2>&1 1>/dev/null)" || rc=$?
chk "uncommitted edit -> NOT refused" "$rc" 0
case "$err" in
  *"WARNING"*"differs from its committed blob"*) echo "  PASS  loud warning on content mismatch"; pass=$((pass+1));;
  *) echo "  FAIL  expected a committed-blob warning, got: $err"; fail=$((fail+1));;
esac
if [ -s "$TMP/edit.provenance.json" ]; then
  echo "  PASS  provenance file still written on a warn-not-refuse attest"; pass=$((pass+1))
else
  echo "  FAIL  provenance file missing after a warn-not-refuse attest"; fail=$((fail+1))
fi
# restore for the remaining cases
git -C "$CANON" checkout -q -- scripts/system/daemon.sh

# ------------------------------------------------------- case 4/5: staleness
SCRIPT="$CANON/scripts/system/daemon.sh"
STALE_PROV="$TMP/stale.provenance.json"
dp_attest "$SCRIPT" "$STALE_PROV"

rc=0; dp_stale_since_start "$SCRIPT" "$STALE_PROV" || rc=$?
chk "unchanged inode -> not stale" "$rc" 1

# Replace the file the way git actually does it: write to a temp file in the
# same directory, then rename over the original — a NEW inode at the SAME
# path, exactly the mechanism the whole class is about (never edit in place).
NEWTMP="$(dirname "$SCRIPT")/.daemon.sh.new"
printf '#!/bin/bash\necho "daemon v2, post-commit"\n' > "$NEWTMP"
mv -f "$NEWTMP" "$SCRIPT"

rc=0; dp_stale_since_start "$SCRIPT" "$STALE_PROV" || rc=$?
chk "inode replaced via write-then-rename (git's own mechanism) -> stale" "$rc" 0

# --------------------------------------------------------- unknown / fail-closed
rc=0; dp_stale_since_start "$SCRIPT" "$TMP/does-not-exist.json" || rc=$?
chk "missing provenance file -> cannot tell (fail closed)" "$rc" 2

rc=0; dp_stale_since_start "$TMP/does-not-exist-either.sh" "$STALE_PROV" || rc=$?
chk "script path no longer stats -> cannot tell (fail closed)" "$rc" 2

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]

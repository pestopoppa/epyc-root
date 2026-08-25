#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Bash | Write | Edit  (ONE wrapper, ONE scanner)
# Refuses privileged host-level operations and writes outside the containment
# root — the MECHANICAL GUARD for INC-20260823-filesystem-containment-gap.
#
# Origin: 2026-08-23 — an agent ran
#     sudo -n mkdir -p /mnt/bigdisk && sudo -n mount /dev/sdb1 /mnt/bigdisk
# planned writes to /mnt/bigdisk/epyc-backup/, and `sudo apt-get install restic`,
# against the operator directive "do not touch anything outside /mnt/raid0/llm/".
# Nothing stopped it: the Bash surface had no guard at all (the Write|Edit-only
# check_filesystem_path.sh reads tool_input.file_path, and no Bash hook scanned
# commands). This wrapper + filesystem_containment_scan.py closes BOTH Claude
# surfaces; .opencode/plugins/filesystem-containment.ts closes the opencode
# surface — ALL call the ONE shared scanner.
#
# INPUT ROUTING (both matchers register this same wrapper):
#   tool_name Bash      → tool_input.command    → scanner --command   (CLASS A+B)
#   tool_name Write|Edit → tool_input.file_path → scanner --check-path (containment set)
#
# SEMANTIC NOTE (the Write|Edit unification, 2026-08-23): the superseded
# check_filesystem_path.sh allowed /mnt/raid0/* broadly; the scanner allows
# /mnt/raid0/llm/** — equivalent in practice because /mnt/raid0 contains only
# llm/ (verified at unification time). It also allowed `*/.claude/*` anywhere;
# the scanner allows ~/.claude/** (project .claude/ lives under /workspace or
# /mnt/raid0/llm, so nothing real changes). The /workspace device check is
# gone: /workspace/** is unconditionally inside the containment set.
#
# CLASS A (operator-only): mount/umount/mkfs*/fdisk/parted/mkswap/systemctl/
# modprobe/shutdown/reboot, apt/dpkg package mutation, dd of=/dev/*.
# CLASS B: writes (mkdir/cp/mv/tee/redirection/rsync/tar -C/restic/borg/rclone/
# chown/chmod/ln/install/rm/git clone...) whose target resolves OUTSIDE
# /mnt/raid0/llm/**, /workspace/**, /tmp/opencode/**, ~/.claude/**, ~/.codex/**
# (bare /tmp/** is tolerated scratch). See the scanner docstring for the full
# policy and its stated scope limits.
#
# OPERATOR OVERRIDES, visible in the record, never silent:
#   * EPYC_FS_ACK="operator: <who> <date>: <reason>" in the environment of the
#     tool call allows anything (both classes, both surfaces). Read from the
#     HOOK's environment — a command cannot self-authorize by embedding the
#     ack text.
#   * scripts/hooks/filesystem_allowlist.yaml (schema
#     session_bus.filesystem_allowlist.v1) approves CLASS B path prefixes for
#     the operator, in the repo, forever. CLASS A always needs the env ack.
#
# TESTS: scripts/hooks/tests/test_filesystem_containment.py,
#        scripts/hooks/tests/test_harness_guard_parity.py

INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')
case "$TOOL" in
  Bash|"") MODE="--command";  FIELD="command" ;;
  Write|Edit) MODE="--check-path"; FIELD="file_path" ;;
  *) exit 0 ;;
esac

VALUE=$(printf '%s' "$INPUT" | jq -r --arg f "$FIELD" '.tool_input[$f] // empty')
[[ -z "$VALUE" ]] && exit 0

SCAN="$(dirname "${BASH_SOURCE[0]}")/filesystem_containment_scan.py"

# Fail CLOSED when the scanner cannot run, but only for the unambiguous
# privileged verbs / the big roots — a missed mount/install costs another
# incident, and the literal forms below cannot be false-positive'd by path
# resolution. This is a DEGRADED mode: no allowlist, no ack, no runner
# skipping; it exists only so a broken python3 cannot re-open the gap.
if ! command -v python3 >/dev/null 2>&1 || [[ ! -f "$SCAN" ]]; then
  if [[ "$MODE" == "--command" ]]; then
    if printf '%s' "$VALUE" | grep -qE \
      '(^|[;&|]|\s)(sudo[[:space:]]+)?(mount|umount|mkfs|fdisk|parted|mkswap|systemctl|modprobe|shutdown|reboot)([[:space:]]|$)' ||
       printf '%s' "$VALUE" | grep -qE \
      '(^|[;&|]|\s)(sudo[[:space:]]+)?(apt|apt-get)[[:space:]]+(install|remove|purge)' ||
       printf '%s' "$VALUE" | grep -qE \
      '(^|[;&|]|\s)(sudo[[:space:]]+)?dpkg[[:space:]]+(-i|--install|-r|--remove)'; then
      echo "BLOCKED: the filesystem-containment scanner is unavailable and this command" >&2
      echo "invokes a privileged host-level verb. Refusing rather than guessing." >&2
      exit 2
    fi
  else
    case "$VALUE" in
      /mnt/raid0/llm/*|/workspace/*|/workspace) ;;
      *)
        echo "BLOCKED: the filesystem-containment scanner is unavailable and this path" >&2
        echo "is outside /mnt/raid0/llm/**. Refusing rather than guessing." >&2
        exit 2
        ;;
    esac
  fi
  exit 0
fi

# Scanner stdout = JSON verdict (captured); scanner stderr = the human refusal
# message (passes through to the session, untouched).
set +e
JSON=$(python3 "$SCAN" "$MODE" "$VALUE" 2>/dev/null)
RC=$?
set -e

case "$RC" in
  0)
    exit 0
    ;;
  2)
    MSG=$(printf '%s' "$JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("detail",""))' 2>/dev/null) || MSG=""
    [[ -z "$MSG" ]] && MSG="this tool call was refused by the containment scanner."
    cat >&2 <<EOF
BLOCKED: filesystem containment (INC-20260823).

$MSG

The operator directive is: do not touch anything outside /mnt/raid0/llm/.
Operator-approved overrides, both visible in the record:
  - one-off: EPYC_FS_ACK="operator: <who> <date>: <reason>" on the tool call
  - permanent (CLASS B paths): an entry in scripts/hooks/filesystem_allowlist.yaml
EOF
    exit 2
    ;;
  *)
    echo "BLOCKED: the filesystem-containment scanner failed (exit $RC) — refusing " >&2
    echo "rather than re-opening the 2026-08-23 gap." >&2
    printf '%s\n' "$JSON" | tail -3 >&2
    exit 2
    ;;
esac

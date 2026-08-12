#!/bin/bash
set -euo pipefail
#
# git pre-push hook — PUSH SERIALIZATION GUARD
#
# Run:   pre_push_serialization_guard.sh <remote-name> <remote-url>   < <ref updates on stdin>
# Tests: scripts/hooks/tests/test_pre_push_serialization_guard.sh
#
# NOT INSTALLED BY THIS FILE. Writing the guard and wiring it into .git/hooks or
# core.hooksPath are separate decisions; this file only implements the contract.
#
# ─── WHY THIS EXISTS ─────────────────────────────────────────────────────────
#
# Several agent sessions share ONE clone per repo and all sit on `main`.
# `git push` publishes a BRANCH, not a commit: whoever pushes publishes every
# commit every other session has landed since the last push, reviewed or not.
# On 2026-08-11 one repo sat 29 commits ahead of origin with 349 commits landed
# across all sessions in a day — so any single `git push` would have published
# hundreds of other sessions' commits.
#
# Pushes are serialized today by CONVENTION (an operator instruction on the
# message bus). Convention is exactly what this guard replaces: a push that has
# not taken the serialization lock is refused, mechanically, at the point of
# push. The companion writer is scripts/coordination/serialized_push.py, which
# takes the lock and then runs the push. This guard NEVER imports it, calls it,
# or assumes its internals — it depends only on the lock FILE.
#
# ─── DECISION: WHICH REFS ARE GUARDED ────────────────────────────────────────
#
# GUARDED: updates and deletions of PROTECTED remote refs — by default
# refs/heads/main and refs/heads/master (override: EPYC_PUSH_PROTECTED_REFS).
# EVERYTHING ELSE PASSES: lane/<agent> branches, tags, notes, refs/for/*, any
# branch that is not the shared trunk, and deletions thereof.
#
# Reasoning:
#   1. The hazard is co-tenancy, not pushing. A lane/<agent> branch has exactly
#      one writer, so pushing it publishes only that agent's own commits. There
#      is nothing to serialize; serializing it would be ceremony with no
#      referent.
#   2. Over-blocking is how guards get deleted. A guard that stops an agent from
#      publishing its own side branch produces a `--no-verify` habit, or a
#      request to uninstall, and then the trunk is unguarded too. The guard's
#      survival is part of its correctness.
#   3. The decision is keyed on the REMOTE ref, never the local one, because the
#      remote ref is what actually gets published. `git push origin HEAD:main`
#      and `git push origin lane/x:main` are both trunk publishes and are both
#      guarded; `git push origin main:refs/heads/lane/x` is not a trunk publish
#      and is not guarded.
#   4. DELETIONS of a protected ref are guarded, not exempted. Deleting the
#      shared trunk on origin is strictly worse than an unserialized append, and
#      "it was only a delete" is not a reason to skip the lock. Deletions of
#      non-protected refs pass with everything else. Both directions are tested.
#
# EMPTY STDIN IS ALLOWED, and that is a measurement, not an assumption: git
# invokes pre-push with ZERO ref-update lines when the push is a no-op
# ("Everything up-to-date"), verified 2026-08-12 in a throwaway repo against a
# local bare origin. Zero ref updates publishes zero commits, so refusing there
# would block only harmless no-ops — the over-blocking failure mode above. Any
# stdin line that IS present must parse, or the push is refused.
#
# ─── FAIL-CLOSED POSTURE ─────────────────────────────────────────────────────
#
# Every ambiguity about a guarded ref refuses, and names the specific cause:
# lock missing, lock empty, lock unreadable, schema unrecognisable, holder
# mismatch, lock expired, unknown session identity, malformed stdin, repo
# undeterminable. There is no generic "push blocked" message anywhere in here.
# In particular an unparseable lock file is treated as UNREADABLE SCHEMA and
# refused — never as "no lock is held" and never as "a lock is held".
#
# ─── BYPASS ──────────────────────────────────────────────────────────────────
#
# EPYC_ALLOW_UNSERIALIZED_PUSH='<who and why>' git push ...
#
# An unbypassable guard on a shared host gets deleted rather than respected, so
# there is a hatch — but it is attributable: the value must be a reason string,
# not a boolean. Every use is announced on stderr and appended, best-effort, to
# a log. Failing to write that log never blocks the push (the stderr
# announcement is the part that always happens).
#
# ─── WHAT THIS GUARD DOES NOT DO ─────────────────────────────────────────────
#
# Stated plainly, because a guard whose limits are not written down gets trusted
# for things it never did:
#
#   * `git push --no-verify` skips every pre-push hook. So does
#     `git -c core.hooksPath=/dev/null push`, and so does uninstalling the hook —
#     hooks live in a clone, not in the repository, and nothing here can defend
#     its own installation. Only a SERVER-side hook (pre-receive on origin) makes
#     unserialized publication impossible rather than merely hard. This guard
#     raises the floor for the accidental and habitual case; it is not a
#     defence against a determined bypass, and the bypass env var above means it
#     is not trying to be.
#   * Serialization is not review. Holding the lock and pushing still publishes
#     every other session's commits on the branch — it makes exactly one session
#     responsible for that at a time, which is what the convention asked for.
#     Scoping WHAT gets published is a different mechanism (lane branches, or
#     pushing an explicit ref).
#   * Staleness: the guard honours `expires_at` if a lock carries one, but the
#     current writer does not emit one, and — like that writer — the guard does
#     NOT auto-expire a lock whose holder died. Residue left by a crashed holder
#     with a matching id is accepted. Displacing residue is deliberate and
#     attributable there (`--force-release`), and is not this hook's job.
#   * The DECLARED proof trusts the environment: `AGENT_ID=<holder> git push`
#     satisfies it. The STRUCTURAL proof (holder pid is an ancestor) cannot be
#     spoofed by an env var, but is only available when pushing under the
#     wrapper. Anyone able to set env vars can present themselves as the holder.
#   * TOCTOU: the lock is read when the hook runs, not held across the ref
#     update. A holder releasing mid-push is a millisecond-wide window, unguarded.
#   * With EPYC_PUSH_LOCK_FILE pointed at some OTHER repo's lock that you hold,
#     this repo's push is allowed. The default path cannot do this (its name is
#     the repo's own device+inode), but the override is unchecked.

GUARD="pre-push serialization guard"
BYPASS_VAR="EPYC_ALLOW_UNSERIALIZED_PUSH"

REMOTE_NAME="${1-}"
REMOTE_URL="${2-}"

# ── output helpers ───────────────────────────────────────────────────────────

banner() { printf '\n' >&2; printf '========== %s ==========\n' "$1" >&2; }

# refuse <cause> [detail lines...]
refuse() {
  local cause="$1"; shift
  banner "PUSH REFUSED — ${GUARD}"
  printf 'cause: %s\n' "$cause" >&2
  local line
  for line in "$@"; do printf '       %s\n' "$line" >&2; done
  printf '\n' >&2
  printf 'This repo has one clone shared by several agent sessions, all on the trunk.\n' >&2
  printf 'A push publishes the whole branch, so an unserialized push publishes other\n' >&2
  printf "sessions' unreviewed commits. Take the lock and push through the wrapper:\n" >&2
  printf '    python3 scripts/coordination/serialized_push.py   (holds the lock, then pushes)\n' >&2
  printf '\n' >&2
  printf 'Genuine emergency (attributable, announced, logged):\n' >&2
  printf "    %s='<your-agent-id>: <why>' git push ...\n" "$BYPASS_VAR" >&2
  printf '\n' >&2
  exit 1
}

note() { printf '%s: %s\n' "$GUARD" "$1" >&2; }

# ── 1. read stdin ONCE, verbatim ─────────────────────────────────────────────
# Read before anything else: stdin is a one-shot pipe from git and every later
# branch (including the bypass announcement) wants to name the refs involved.

REF_LINES="$(cat || true)"

# ── 2. bypass ────────────────────────────────────────────────────────────────
# Checked before parsing so that an emergency push cannot be trapped by a parse
# quirk in the very code path being escaped. The reason string is required to
# be a reason: a bare boolean is refused, because "1" attributes nothing.

BYPASS_VALUE="${!BYPASS_VAR:-}"
if [[ -n "$BYPASS_VALUE" ]]; then
  case "$(printf '%s' "$BYPASS_VALUE" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|y|on|enable|enabled)
      refuse "${BYPASS_VAR} was set to a boolean ('${BYPASS_VALUE}'), which attributes nothing" \
             "the bypass exists to be auditable, so it requires a reason string" \
             "use: ${BYPASS_VAR}='<your-agent-id>: <why>' git push ..."
      ;;
  esac
  banner "PUSH SERIALIZATION BYPASSED — ${GUARD}"
  printf '%s was set; the serialization lock was NOT checked.\n' "$BYPASS_VAR" >&2
  printf 'reason : %s\n' "$BYPASS_VALUE" >&2
  printf 'agent  : %s\n' "${EPYC_PUSH_LOCK_HOLDER:-${AGENT_ID:-<no AGENT_ID in env>}}" >&2
  printf 'remote : %s %s\n' "${REMOTE_NAME:-<none>}" "${REMOTE_URL:-<none>}" >&2
  printf 'refs   : %s\n' "$(printf '%s' "$REF_LINES" | tr '\n' ';' | sed 's/;$//')" >&2
  printf '\n' >&2

  BYPASS_LOG="${EPYC_PUSH_GUARD_LOG:-${EPYC_PUSH_LOCK_DIR:-/workspace/coordination/push-locks}/push-guard-bypass.log}"
  {
    mkdir -p "$(dirname "$BYPASS_LOG")" 2>/dev/null &&
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      "${EPYC_PUSH_LOCK_HOLDER:-${AGENT_ID:-unattributed}}" \
      "$(id -un 2>/dev/null || echo '?')@$(hostname 2>/dev/null || echo '?')" \
      "${REMOTE_NAME:-<none>} ${REMOTE_URL:-<none>}" \
      "$(printf '%s' "$REF_LINES" | tr '\n' ';')" \
      "$BYPASS_VALUE" >> "$BYPASS_LOG"
  } 2>/dev/null || note "bypass logged to stderr only — could not write ${BYPASS_LOG}"
  exit 0
fi

# ── 3. parse stdin ───────────────────────────────────────────────────────────
# Real format, verified against git rather than assumed (see header):
#
#   <local ref> <local oid> <remote ref> <remote oid>
#
#   refs/heads/main   90507d7…  refs/heads/main   4b59a5c…   ordinary update
#   refs/heads/lane/a 4b59a5c…  refs/heads/lane/a 000000000  new remote branch
#   (delete)          000000000 refs/heads/lane/b 4b59a5c…   deletion
#
# The local ref of a deletion is the literal token "(delete)", the OIDs are
# all-zero (40 hex for sha1, 64 for sha256 — matched as ^0+$, not by length),
# and the line order is whatever git chose. A mis-parse here blocks everything
# or nothing, so every line must have exactly 4 fields or the push is refused.

GUARDED_REFS=()      # protected remote refs in this push
UNGUARDED_REFS=()    # everything else, for the allow message
TOTAL_LINES=0

protected_patterns() {
  local raw="${EPYC_PUSH_PROTECTED_REFS:-refs/heads/main refs/heads/master}"
  printf '%s' "$raw" | tr ',' ' '
}

is_protected() {
  # $1 = remote ref as git printed it. Compared both fully qualified and short
  # so that EPYC_PUSH_PROTECTED_REFS accepts "main" as readily as
  # "refs/heads/main".
  local ref="$1" short="${1#refs/heads/}" p
  for p in $(protected_patterns); do
    [[ -z "$p" ]] && continue
    if [[ "$ref" == "$p" || "$short" == "$p" || "$ref" == "refs/heads/$p" ]]; then
      return 0
    fi
  done
  return 1
}

while IFS= read -r line; do
  [[ -z "${line//[[:space:]]/}" ]] && continue
  TOTAL_LINES=$((TOTAL_LINES + 1))

  # shellcheck disable=SC2206
  fields=( $line )
  if [[ "${#fields[@]}" -ne 4 ]]; then
    refuse "malformed ref-update line on stdin: expected 4 fields, got ${#fields[@]}" \
           "line: ${line}" \
           "expected: <local ref> <local oid> <remote ref> <remote oid>" \
           "the guard refuses rather than guess which ref is being published"
  fi

  local_ref="${fields[0]}"; local_oid="${fields[1]}"
  remote_ref="${fields[2]}"; remote_oid="${fields[3]}"

  if [[ ! "$local_oid" =~ ^[0-9a-fA-F]+$ || ! "$remote_oid" =~ ^[0-9a-fA-F]+$ ]]; then
    refuse "malformed object id on stdin" \
           "line: ${line}" \
           "local oid '${local_oid}' / remote oid '${remote_oid}' are not hex" \
           "the guard refuses rather than treat an unrecognised line as harmless"
  fi

  if [[ "$local_oid" =~ ^0+$ ]]; then
    kind="delete"
  elif [[ "$remote_oid" =~ ^0+$ ]]; then
    kind="create"
  else
    kind="update"
  fi

  if is_protected "$remote_ref"; then
    GUARDED_REFS+=( "${kind} ${remote_ref} (from ${local_ref})" )
  else
    UNGUARDED_REFS+=( "${kind} ${remote_ref}" )
  fi
done <<< "$REF_LINES"

# ── 4. nothing guarded → allow ───────────────────────────────────────────────

if [[ "${#GUARDED_REFS[@]}" -eq 0 ]]; then
  if [[ "$TOTAL_LINES" -eq 0 ]]; then
    note "no ref updates on stdin (git reports nothing to publish) — allowing"
  else
    note "no protected ref in this push (${UNGUARDED_REFS[*]}) — allowing without a lock"
  fi
  exit 0
fi

# ── 5. who is this session? ──────────────────────────────────────────────────
# Two independent proofs that the lock is THIS push's lock. Either suffices;
# neither is required to exist for the other to work.
#
#   DECLARED  — the holder id in the lock equals this session's id, taken from
#               EPYC_PUSH_LOCK_HOLDER or, failing that, the fleet roster id
#               AGENT_ID. Cheap, but only as honest as the environment.
#
#   STRUCTURAL — the process recorded in the lock is an ANCESTOR of this hook.
#               When the wrapper holds the lock and runs `git push`, git spawns
#               this hook as its child, so the lock holder is literally this
#               push's grandparent. Nothing needs to be exported for that to be
#               true, and nothing a caller sets can fake it.
#
# The structural proof is here because it is load-bearing, not decorative: the
# companion wrapper's do_push() shells out to `git push` WITHOUT putting the
# holder id in the child's environment (read 2026-08-12), so on a host where a
# session has not exported AGENT_ID the declared proof is simply unavailable and
# the compliant path would refuse itself. Ancestry is checked by reading
# /proc/<pid>/status — no signals are sent, nothing is started or stopped.

SESSION_ID="${EPYC_PUSH_LOCK_HOLDER:-${AGENT_ID:-}}"
SESSION_ID="${SESSION_ID#"${SESSION_ID%%[![:space:]]*}"}"
SESSION_ID="${SESSION_ID%"${SESSION_ID##*[![:space:]]}"}"

pid_is_ancestor() {
  # True if $1 is this process, or any parent of it. Refuses pid<=1: in a
  # container init IS everyone's ancestor, so honouring it would turn a stale
  # "pid": 1 record into a universal pass.
  local target="${1:-}" p="$$" ppid hops=0
  [[ "$target" =~ ^[0-9]+$ ]] || return 1
  [[ "$target" -le 1 ]] && return 1
  [[ -r "/proc/$$/status" ]] || return 1        # no procfs → no structural proof
  [[ "$target" == "$$" ]] && return 0
  while [[ "$p" -gt 1 && "$hops" -lt 64 ]]; do
    ppid="$(awk '/^PPid:/{print $2; exit}' "/proc/$p/status" 2>/dev/null || true)"
    [[ -z "$ppid" ]] && return 1
    [[ "$ppid" == "$target" ]] && return 0
    p="$ppid"
    hops=$((hops + 1))
  done
  return 1
}

# ── 6. where is the lock? ────────────────────────────────────────────────────
# The path must agree, byte for byte, with what the writer
# (scripts/coordination/serialized_push.py) produces, or the guard would refuse
# every compliant push. Read off that writer on 2026-08-12 and reproduced here
# WITHOUT importing it (this hook must keep working if that file is absent):
#
#   dir  : SERIALIZED_PUSH_LOCK_DIR, else <repo-root>/coordination/push-locks
#   file : push-<st_dev>-<st_ino>.json  of the git COMMON dir
#
# Keyed on device+inode rather than a path because this fleet reaches one clone
# through several paths — /workspace/.git and /mnt/raid0/llm/epyc-root/.git are
# a BIND MOUNT, not a symlink, so realpath does not collapse them, and a
# path-keyed lock would hand two "different" repos to two sessions and serialize
# nothing. Keyed on the COMMON dir rather than the per-worktree git dir because
# every worktree of a clone pushes the same branch to the same remote and must
# contend for one lock. `stat -c %d-%i` is byte-identical to python's
# st_dev/st_ino (verified on this host: 2431-96604699 both ways).
#
# EPYC_PUSH_LOCK_FILE (exact path) and EPYC_PUSH_LOCK_DIR (directory) override,
# in that order, for tests and for an operator relocating the lock.

LOCK_FILE="${EPYC_PUSH_LOCK_FILE:-}"
if [[ -z "$LOCK_FILE" ]]; then
  COMMON_DIR="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  if [[ -z "$COMMON_DIR" ]]; then
    COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null || true)"
    [[ -n "$COMMON_DIR" ]] && COMMON_DIR="$(cd "$COMMON_DIR" 2>/dev/null && pwd || true)"
  fi
  if [[ -z "$COMMON_DIR" ]]; then
    refuse "cannot determine which clone is being pushed, so the lock file path is unknown" \
           "git rev-parse --git-common-dir produced nothing from $(pwd)" \
           "guarded refs: ${GUARDED_REFS[*]}" \
           "set EPYC_PUSH_LOCK_FILE=<path> if this hook is being run outside a work tree"
  fi
  REPO_KEY="$(stat -c '%d-%i' "$COMMON_DIR" 2>/dev/null || true)"
  if [[ -z "$REPO_KEY" || "$REPO_KEY" == "-" ]]; then
    refuse "cannot stat the git common dir ${COMMON_DIR}, so the repo's lock key is unknown" \
           "the lock is keyed on device+inode; without it the guard cannot find the lock" \
           "guarded refs: ${GUARDED_REFS[*]}" \
           "set EPYC_PUSH_LOCK_FILE=<path> to name the lock explicitly"
  fi
  LOCK_DIR="${EPYC_PUSH_LOCK_DIR:-${SERIALIZED_PUSH_LOCK_DIR:-/workspace/coordination/push-locks}}"
  LOCK_FILE="${LOCK_DIR}/push-${REPO_KEY}.json"
fi

# ── 7. lock present? ─────────────────────────────────────────────────────────

if [[ ! -e "$LOCK_FILE" ]]; then
  refuse "the push serialization lock is NOT HELD — no lock file at ${LOCK_FILE}" \
         "guarded refs: ${GUARDED_REFS[*]}" \
         "session: ${SESSION_ID}" \
         "a push to the shared trunk must run under the serialization lock"
fi
if [[ ! -f "$LOCK_FILE" || ! -r "$LOCK_FILE" ]]; then
  refuse "the lock file ${LOCK_FILE} exists but is not a readable regular file" \
         "the guard cannot tell who holds the lock, so it refuses" \
         "guarded refs: ${GUARDED_REFS[*]}"
fi

# ── 8. parse the lock, defensively ───────────────────────────────────────────
# The writer is another agent's script and its schema is NOT settled. Anything
# unrecognisable is UNREADABLE SCHEMA and refuses. Recognised shapes:
#   * JSON object with a holder-ish string field
#     (holder/holder_id/agent/agent_id/session/session_id/owner/owner_id),
#     optionally expires_at/expires/expiry as epoch seconds or ISO-8601
#   * a single bare line containing just the holder id
#   * key=value lines carrying one of the holder-ish keys
#
# The parse runs in python3 so that a malformed JSON lock produces a precise
# cause rather than a shell mis-read. No python3 → only the bare-line shape is
# understood, and anything else refuses rather than being waved through.

LOCK_PARSE=""
if command -v python3 >/dev/null 2>&1; then
  LOCK_PARSE="$(python3 - "$LOCK_FILE" <<'PY' 2>/dev/null || true
import json, re, sys, datetime

HOLDER_KEYS = ("holder", "holder_id", "agent", "agent_id",
               "session", "session_id", "owner", "owner_id")
PID_KEYS = ("pid", "holder_pid", "owner_pid")
HOST_KEYS = ("host", "hostname", "holder_host")
EXPIRY_KEYS = ("expires_at", "expires", "expiry", "expires_at_epoch")

def err(msg):
    print("ERR\x1f" + msg)
    raise SystemExit(0)

def to_epoch(v, key):
    if isinstance(v, bool):
        err("lock field %r is a boolean, not a timestamp" % key)
    if isinstance(v, (int, float)):
        return str(int(v))
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return ""
        if re.fullmatch(r"\d+(\.\d+)?", s):
            return str(int(float(s)))
        try:
            d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            err("lock field %r is %r, which is neither epoch seconds nor ISO-8601" % (key, s))
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        return str(int(d.timestamp()))
    err("lock field %r has type %s, which is not a timestamp" % (key, type(v).__name__))

try:
    raw = open(sys.argv[1], "rb").read()
except OSError as e:
    err("lock file could not be read: %s" % e)
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError:
    err("lock file is not valid UTF-8 text (binary content?)")

s = text.strip()
if not s:
    err("lock file is empty")

if s[0] in "{[":
    try:
        obj = json.loads(s)
    except Exception as e:
        err("lock file looks like JSON but does not parse: %s" % e)
    if not isinstance(obj, dict):
        err("lock JSON top level is %s, expected an object" % type(obj).__name__)
    holder = None
    for k in HOLDER_KEYS:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            holder, hkey = v.strip(), k
            break
    if holder is None:
        err("lock JSON has no non-empty string holder field (looked for %s); keys present: %s"
            % ("/".join(HOLDER_KEYS), ", ".join(sorted(map(str, obj.keys()))) or "<none>"))
    exp = ""
    for k in EXPIRY_KEYS:
        if k in obj and obj[k] is not None:
            exp = to_epoch(obj[k], k)
            break
    pid = ""
    for k in PID_KEYS:
        v = obj.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            pid = str(v); break
        if isinstance(v, str) and v.strip().isdigit():
            pid = v.strip(); break
    host = ""
    for k in HOST_KEYS:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            host = v.strip(); break
    print("OK\x1f%s\x1f%s\x1fJSON field %r\x1f%s\x1f%s" % (holder, exp, hkey, pid, host))
    raise SystemExit(0)

lines = [ln.strip() for ln in s.splitlines()
         if ln.strip() and not ln.strip().startswith("#")]
kv = {}
for ln in lines:
    if "=" in ln:
        k, _, v = ln.partition("=")
        kv[k.strip().lower()] = v.strip().strip('"').strip("'")
for k in HOLDER_KEYS:
    if kv.get(k):
        exp = ""
        for ek in EXPIRY_KEYS:
            if kv.get(ek):
                exp = to_epoch(kv[ek], ek)
                break
        pid = kv.get("pid", "")
        pid = pid if pid.isdigit() else ""
        print("OK\x1f%s\x1f%s\x1fkey=value field %r\x1f%s\x1f%s"
              % (kv[k], exp, k, pid, kv.get("host", "")))
        raise SystemExit(0)
if len(lines) == 1 and re.fullmatch(r"[A-Za-z0-9._:@+\-]{1,128}", lines[0]):
    print("OK\x1f%s\x1f\x1fbare single-line holder id\x1f\x1f" % lines[0])
    raise SystemExit(0)

err("lock file content matches no known schema — not JSON, not key=value with a "
    "holder key, and not a single bare holder id (%d non-comment line(s), first: %r)"
    % (len(lines), lines[0][:80] if lines else ""))
PY
)"
else
  LOCK_CONTENT="$(tr -d '\r' < "$LOCK_FILE")"
  STRIPPED="$(printf '%s' "$LOCK_CONTENT" | sed '/^[[:space:]]*$/d;/^[[:space:]]*#/d')"
  if [[ "$(printf '%s\n' "$STRIPPED" | wc -l)" -eq 1 && "$STRIPPED" =~ ^[A-Za-z0-9._:@+-]{1,128}$ ]]; then
    LOCK_PARSE="$(printf 'OK\037%s\037\037bare single-line holder id (no python3)\037\037' "$STRIPPED")"
  else
    LOCK_PARSE="$(printf 'ERR\037python3 is unavailable and the lock is not a single bare holder id, so its schema cannot be read')"
  fi
fi

if [[ -z "$LOCK_PARSE" ]]; then
  refuse "the lock file ${LOCK_FILE} could not be parsed: the schema reader produced no output" \
         "SCHEMA UNREADABLE — refusing rather than assuming the lock is unheld or held" \
         "guarded refs: ${GUARDED_REFS[*]}"
fi

LOCK_STATUS="${LOCK_PARSE%%$'\037'*}"
if [[ "$LOCK_STATUS" != "OK" ]]; then
  LOCK_REASON="${LOCK_PARSE#*$'\037'}"
  refuse "the lock file ${LOCK_FILE} has an UNREADABLE SCHEMA: ${LOCK_REASON}" \
         "the guard will not assume an unparseable lock means 'unheld' or 'held'" \
         "guarded refs: ${GUARDED_REFS[*]}" \
         "fix the lock file, or re-take the lock via serialized_push.py"
fi

IFS=$'\037' read -r _ LOCK_HOLDER LOCK_EXPIRES LOCK_SOURCE LOCK_PID LOCK_HOST <<< "$LOCK_PARSE"
LOCK_PID="${LOCK_PID:-}"
LOCK_HOST="${LOCK_HOST:-}"

if [[ -z "${LOCK_HOLDER//[[:space:]]/}" ]]; then
  refuse "the lock file ${LOCK_FILE} has an UNREADABLE SCHEMA: holder field parsed to an empty value" \
         "guarded refs: ${GUARDED_REFS[*]}"
fi

# ── 9. is it OUR lock, and is it still valid? ────────────────────────────────

OWNERSHIP=""
if [[ -n "$SESSION_ID" && "$LOCK_HOLDER" == "$SESSION_ID" ]]; then
  OWNERSHIP="declared: lock holder id == this session (${SESSION_ID})"
elif [[ -n "$LOCK_PID" ]] \
     && { [[ -z "$LOCK_HOST" ]] || [[ "$LOCK_HOST" == "$(hostname 2>/dev/null || true)" ]]; } \
     && pid_is_ancestor "$LOCK_PID"; then
  OWNERSHIP="structural: the lock-holding process (pid ${LOCK_PID}) is an ancestor of this push"
elif [[ -z "$SESSION_ID" ]]; then
  refuse "this process has no session identity, and the lock does not prove ownership structurally either" \
         "neither EPYC_PUSH_LOCK_HOLDER nor AGENT_ID is set in this environment" \
         "lock holder : ${LOCK_HOLDER}   (${LOCK_SOURCE} in ${LOCK_FILE})" \
         "lock pid    : ${LOCK_PID:-<none recorded>}${LOCK_HOST:+ on ${LOCK_HOST}} — not an ancestor of this push" \
         "guarded refs: ${GUARDED_REFS[*]}" \
         "push through serialized_push.py (its git push runs as a child of the holder), or export AGENT_ID=<roster id>"
else
  refuse "the serialization lock is held by ANOTHER session" \
         "lock holder : ${LOCK_HOLDER}   (${LOCK_SOURCE} in ${LOCK_FILE})" \
         "this session: ${SESSION_ID}" \
         "lock pid    : ${LOCK_PID:-<none recorded>}${LOCK_HOST:+ on ${LOCK_HOST}} — not an ancestor of this push" \
         "guarded refs: ${GUARDED_REFS[*]}" \
         "wait for the holder to release, then push through serialized_push.py"
fi

if [[ -n "${LOCK_EXPIRES//[[:space:]]/}" ]]; then
  NOW="$(date -u +%s)"
  if [[ ! "$LOCK_EXPIRES" =~ ^-?[0-9]+$ ]]; then
    refuse "the lock file ${LOCK_FILE} has an UNREADABLE SCHEMA: expiry parsed to '${LOCK_EXPIRES}', not epoch seconds" \
           "guarded refs: ${GUARDED_REFS[*]}"
  fi
  if [[ "$LOCK_EXPIRES" -le "$NOW" ]]; then
    refuse "the serialization lock EXPIRED $((NOW - LOCK_EXPIRES))s ago (expiry ${LOCK_EXPIRES}, now ${NOW})" \
           "holder ${LOCK_HOLDER} still matches this session, but an expired lock guarantees nothing" \
           "guarded refs: ${GUARDED_REFS[*]}" \
           "re-take the lock via serialized_push.py and push again"
  fi
fi

# ── 10. compliant path ───────────────────────────────────────────────────────

note "serialization lock held by ${LOCK_HOLDER} (${LOCK_SOURCE}; ${OWNERSHIP}) — allowing push of: ${GUARDED_REFS[*]}"
exit 0

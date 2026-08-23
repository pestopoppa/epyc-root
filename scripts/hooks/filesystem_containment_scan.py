#!/usr/bin/env python3
"""Filesystem containment guard: scan a Bash command for out-of-root writes and
privileged host-level operations, as INVOCATIONS, not as text.

INCIDENT RECORD (2026-08-23, INC-20260823-filesystem-containment-gap). An agent ran

    sudo -n mkdir -p /mnt/bigdisk && sudo -n mount /dev/sdb1 /mnt/bigdisk

planned writes to ``/mnt/bigdisk/epyc-backup/`` — a device OUTSIDE the data root —
and ``sudo apt-get install restic``, all against the operator's directive *do not
touch anything outside /mnt/raid0/llm/*. Nothing stopped it. The verified gap was a
TWO-SURFACE hole, both surfaces Bash:

  * Claude surface: ``.claude/settings.json`` registers six PreToolUse Bash hooks
    (check_pytest_safety, check_live_holder_interference, check_commit_hygiene,
    check_d9_loop_plane, check_process_pattern_kill, check_operator_apply_copy) and
    ``check_filesystem_path.sh``, which reads ``tool_input.file_path`` and matches
    Write|Edit ONLY. No Bash hook scanned commands for mounts, privileged verbs, or
    writes outside the root — every violation went through Bash.
  * opencode surface: ``~/.config/opencode/opencode.jsonc`` had no permission rules
    and no plugins — opencode sessions (including the one that made the mistake)
    had NO guard at all.

This scanner is the ONE shared implementation both surfaces call — the repo's
hard-won lesson (operator_apply_copy_scan.py, RTG-52): never a fifth parser. It
reuses ``shell_scan.segments()`` and nothing else. ``check_filesystem_containment.sh``
wraps it for the Claude PreToolUse hook; ``.opencode/plugins/filesystem-containment.ts``
wraps it for the opencode plugin.

TWO REFUSAL CLASSES.

  CLASS A — privileged host-level operations, OPERATOR-ONLY: sudo/su-prefixed or
  bare ``mount`` ``umount`` ``mkfs*`` (plus ``mke2fs``, same family) ``fdisk``
  ``parted`` ``mkswap`` ``systemctl`` ``modprobe`` ``shutdown`` ``reboot``,
  ``apt|apt-get install|remove|purge|autoremove``, ``dpkg -i|--install|-r|--remove``,
  and ``dd`` with ``of=/dev/*`` (except ``/dev/null`` — a discard device, zero
  risk; stated so a clean scan is not mistaken for laziness). Refused with code
  ``host_level_privileged_operation`` naming the exact command token.

  CLASS B — writes OUTSIDE the containment root: ``mkdir`` ``touch`` ``cp`` ``mv``
  ``tee`` ``dd of=`` ``>``/``>>`` redirection ``rsync`` ``tar -C``/``--directory``
  ``restic backup|init --repo`` ``borg create|init`` ``rclone`` (write verbs)
  ``chown`` ``chmod``, plus deliberate siblings ``ln`` ``install`` ``rm`` ``rmdir``
  (deletion of data outside the root is the same incident class) and
  ``git clone|init|worktree add``. Refused with ``write_outside_containment_root``
  naming the path.

CONTAINMENT SET (realpath'd, ``~`` expanded via ``$HOME``): ``/mnt/raid0/llm/**``
(the data root), ``/workspace/**``, ``/tmp/opencode/**``, ``~/.claude/**``,
``~/.codex/**``. EVERYTHING else is refused — ``/mnt/bigdisk``, ``/mnt/*`` generally,
``/opt/*``, ``/etc/*``, ``/usr/*``, ``/var/*``, ``/media/*``, ``/home/*`` outside
the two config dirs.

/TMP POLICY, chosen and pinned by tests: bare ``/tmp/**`` writes are ALLOWED for
ephemeral scratch. The repo's own tooling writes throwaway proofs to ``/tmp``
constantly; refusing them would break legitimate audit work (the C21 lesson
applied to ourselves), and scratch dies with the host. CLASS A still refuses
mounts/devices anywhere, and ``/mnt/bigdisk`` etc. stay refused. The approved
SCRATCH ROOT is ``/tmp/opencode``; bare ``/tmp`` is tolerated, not blessed.

PATH RESOLUTION. Targets are ``os.path.realpath``'d and compared against the
realpath'd roots. ``~`` and the literal ``$HOME`` expand (known-safe literals).
A target that cannot be resolved — quoted (the quote-stripping the repo trusts
blanks the content, per C21/C47), ``$OTHER`` variable, rclone ``remote:`` target —
is REFUSED with ``unresolvable_target``. The guard does NOT fail open on ambiguity.
Relative targets resolve against ``--cwd`` (the plugin passes the session's
directory; the Claude hook runs in the session's project dir). ``cd`` inside a
chained command tracks a VIRTUAL cwd, so ``cd /mnt/bigdisk && mkdir -p x`` resolves
``x`` against the device — closing a bypass the naif implementation would have
shipped.

KNOWN SCOPE LIMITS, stated so a clean scan is not mistaken for containment
(same trade-offs ``operator_apply_copy_scan.py`` and the pattern-kill guard make
and document):
  * A PreToolUse hook sees the command an AGENT TYPES. A daemon, a cron job, or a
    script that internally shells out is invisible to it — the enforcing layer
    there is OS-level (separate uid / read-only mounts), as
    ``coordination/session-bus/human_only_paths.yaml`` already records.
  * The inner command of ``bash -c '...'``/``sh -c '...'`` is quoted data and is
    blanked like any other quoted run. ``xargs``-dispatched verbs ARE caught (the
    runner is skipped, the verb after it is read).
  * A path spelled with a variable other than ``$HOME`` is refused as
    unresolvable, not silently allowed.
  * ``pushd``/``popd`` are not followed; the enumerated tool list is deliberate
    and extended only with same-class siblings, each documented.

EXIT PROTOCOL. 0 = allowed. 2 = refused: human message on stderr, JSON verdict
on stdout: ``{"verdict": "refused", "code": ..., "detail": ..., "tool": ...}``.
Empty input NEVER produces a verdict (the ``process_pattern_kill_scan.py``
defect: a guard that says `clean` for input it never read is worse than no guard).

ACKNOWLEDGED OPERATOR OVERRIDES — both visible in the record, never silent:
  * Env ``EPYC_FS_ACK="operator: <who> <date>: <reason>"`` in the environment of
    the Bash tool call allows ANY command (both classes) and is logged. The ack
    is read from the scanner process environment ONLY — never from the command
    text, so a command cannot self-authorize by writing its own ack.
  * ``scripts/hooks/filesystem_allowlist.yaml`` (schema
    ``session_bus.filesystem_allowlist.v1``) lists realpath prefixes the operator
    has approved for CLASS B. It NEVER opens CLASS A. If the allowlist is missing
    or unparseable the guard FAILS CLOSED: out-of-root writes are refused with
    ``allowlist_unavailable`` until the file parses. An override path may be
    given with ``--allowlist`` (tests only); production reads the canonical file
    — deliberately NOT an env override, so an agent's shell export cannot re-point
    the guard at a file it wrote itself.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_scan import segments  # noqa: E402  — the repo's ONE shell scanner

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALLOWLIST_PATH = REPO_ROOT / "scripts" / "hooks" / "filesystem_allowlist.yaml"
ALLOWLIST_SCHEMA = "session_bus.filesystem_allowlist.v1"
ACK_ENV = "EPYC_FS_ACK"

# --------------------------------------------------------------------------- #
# Containment roots
# --------------------------------------------------------------------------- #

_RAW_ROOTS = (
    "/mnt/raid0/llm",   # the data root — everything beneath it
    "/workspace",       # devcontainer view of the same md127 device
    "/tmp",             # bare /tmp/** scratch is allowed (dies with the host);
                        # CLASS A still refuses mounts/devices everywhere
    "/tmp/opencode",    # the pre-approved scratch root (redundant under /tmp,
                        # kept so the approved root is visible in the set)
    "~/.claude",        # agent config
    "~/.codex",         # agent config
)


def containment_roots() -> tuple[str, ...]:
    return tuple(os.path.realpath(os.path.expanduser(r)) for r in _RAW_ROOTS)


def _inside(path: str, roots: tuple[str, ...]) -> bool:
    return any(path == root or path.startswith(root + os.sep) for root in roots)


# --------------------------------------------------------------------------- #
# CLASS A — privileged host-level operations (operator-only)
# --------------------------------------------------------------------------- #

_CLASS_A_VERBS = frozenset(
    "mount umount fdisk parted mkswap systemctl modprobe shutdown reboot mke2fs".split()
)
_PKG_TOOLS = frozenset("apt apt-get dpkg".split())
_PKG_ACTIONS = frozenset("install remove purge autoremove".split())
_DPKG_INSTALL_FLAGS = ("-i", "--install", "-r", "--remove", "-P", "--purge")

# Runner prefixes: skipped over so the VERB after them is found. Includes
# timeouts, env wrappers, and the shell launchers whose -c VALUE is quoted
# (and therefore blanked — see scope limits above).
_RUNNERS = frozenset(
    """sudo su env timeout nice nohup setsid stdbuf taskset numactl command
       xargs strace time bash sh zsh dash ksh python python3 python3.11
       python3.12 python3.13 uv pipenv poetry""".split()
)
# Runner flags that CONSUME the following token as their value, PER RUNNER.
# `-n` is a bare flag on sudo but takes a value on nice; `-c` is the inner
# command on bash but a bare flag on stdbuf. A single global set would read
# `sudo -n mkdir` as "value mkdir" and lose the verb — the exact defect class
# this repo has paid for four times. Default: no value flags.
_RUNNER_VALUE_FLAGS: dict[str, frozenset[str]] = {
    "sudo": frozenset(("-u", "-U", "-g", "-G", "-p", "-h")),
    "su": frozenset(("-c", "-l", "-s", "-p", "-m")),
    "env": frozenset(("-u", "-C", "--unset", "--chdir")),
    "nice": frozenset(("-n",)),
    "timeout": frozenset(("-s", "-k", "--signal", "--kill-after")),
    "stdbuf": frozenset(("-i", "-o", "-e")),
    "taskset": frozenset(("-c",)),
    "numactl": frozenset(("-m", "-N", "-i", "-C", "-p")),
    "xargs": frozenset(("-I", "-L", "-n")),
    "bash": frozenset(("-c",)),
    "sh": frozenset(("-c",)),
    "zsh": frozenset(("-c",)),
    "dash": frozenset(("-c",)),
    "ksh": frozenset(("-c",)),
}
_TRIM = "\"'`()[]{};,&<>|$"
# Paths keep `$` visible: stripping it would launder `$DEST/x` into a relative
# path and silently ALLOW a variable target instead of refusing it.
_PATH_TRIM = "\"'`()[]{};,&<>|"


def _normalize(tok: str) -> str:
    return tok.strip(_TRIM)


def _env_assignment(tok: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok))


def verb_of(tokens: list[str]) -> tuple[str | None, int]:
    """(verb token, index of its first token) for one invocation segment.

    VERB POSITION, not word-anywhere: ``grep mount /etc/fstab`` has verb
    ``grep`` — ``mount`` there is an operand, not a command, and must not be
    refused (the C21 lesson: a guard that fires on text blocks the grep
    searching for it). Env assignments (``VAR=x``) and runner prefixes
    (``sudo -n``, ``timeout 5``, ``env -i``) are skipped; path-qualified
    verbs (``/usr/bin/mount``) are normalized; command substitution
    (``$(mount ...)``) and quoted verbs (``"mount"``) survive stripping.
    """
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if _env_assignment(tok):
            i += 1
            continue
        norm = _normalize(tok)
        base = norm.split("/")[-1]
        if not norm.strip():
            # a quoted run blanked by strip_quoted — data, not a command word
            i += 1
            continue
        if base not in _RUNNERS:
            return norm, i
        flags = _RUNNER_VALUE_FLAGS.get(base, frozenset())
        i += 1
        while i < len(tokens):
            t = tokens[i]
            tn = _normalize(t)
            if tn.startswith("-"):
                i += 1
                if tn.split("=")[0] in flags and i < len(tokens):
                    i += 1
                continue
            if re.match(r"^[+-]?\d+(\.\d+)?[smhd]?$", tn):
                i += 1
                continue
            break
    return None, i


def class_a_verdict(tokens: list[str], verb: str | None) -> dict | None:
    """Refusal dict for a privileged host-level operation, or None."""
    if verb is None:
        return None
    base = verb.split("/")[-1]
    if base in _CLASS_A_VERBS:
        return {"code": "host_level_privileged_operation", "tool": base,
                "detail": f"privileged host-level operation '{base}' is operator-only"}
    if base.startswith("mkfs"):
        return {"code": "host_level_privileged_operation", "tool": base,
                "detail": f"filesystem creation '{base}' is operator-only"}
    if base in _PKG_TOOLS:
        idx = next((i for i, t in enumerate(tokens)
                    if _normalize(t).split("/")[-1] == base), -1)
        if base == "dpkg":
            for t in tokens[idx + 1:]:
                flag = _normalize(t).split("=")[0]
                if flag in _DPKG_INSTALL_FLAGS:
                    return {"code": "host_level_privileged_operation",
                            "tool": f"dpkg {flag}",
                            "detail": f"package mutation 'dpkg {flag}' is operator-only"}
        else:
            for t in tokens[idx + 1:]:
                if _normalize(t) in _PKG_ACTIONS:
                    return {"code": "host_level_privileged_operation",
                            "tool": f"{base} {_normalize(t)}",
                            "detail": f"package mutation '{base} {_normalize(t)}' is "
                                      "operator-only"}
    if base == "dd":
        for t in tokens:
            m = re.match(r"^of=(/dev/[^\s]+)$", _normalize(t))
            if m and m.group(1) != "/dev/null":
                return {"code": "host_level_privileged_operation",
                        "tool": f"dd of={m.group(1)}",
                        "detail": f"dd writing to device '{m.group(1)}' is operator-only"}
    return None


# --------------------------------------------------------------------------- #
# CLASS B — writes outside the containment root
# --------------------------------------------------------------------------- #

def _positionals(tokens: list[str], value_flags: frozenset[str]) -> list[str]:
    """Positional args after the verb; `--` makes everything after it positional."""
    out: list[str] = []
    i, after_ddash = 0, False
    while i < len(tokens):
        t = tokens[i]
        if after_ddash:
            out.append(t)
            i += 1
            continue
        if t == "--":
            after_ddash = True
            i += 1
            continue
        if t.startswith("-"):
            key = t.split("=")[0]
            if "=" in t:
                i += 1
                continue
            if key in value_flags and i + 1 < len(tokens):
                i += 2
            else:
                i += 1
            continue
        out.append(t)
        i += 1
    return out


_RESTIC_WRITE_VERBS = frozenset("backup init".split())
_BORG_WRITE_VERBS = frozenset("create init".split())
_RCLONE_WRITE_VERBS = frozenset("copy sync move delete deletefile purge rcat".split())
_GIT_WRITE_VERBS = frozenset("clone init".split())


def class_b_targets(verb: str | None, tokens: list[str], verb_idx: int) -> list[str]:
    """Raw target strings the invocation writes to, or [] if none."""
    if verb is None:
        return []
    base = verb.split("/")[-1]
    rest = tokens[verb_idx + 1:] if verb_idx >= 0 else tokens
    if base == "mkdir":
        return _positionals(rest, frozenset(("-m", "--mode")))
    if base == "touch":
        return _positionals(rest, frozenset(("-d", "-t", "-r", "--date", "--reference")))
    if base in ("cp", "mv", "ln", "install"):
        for i, t in enumerate(rest):
            if t in ("-t", "--target-directory") and i + 1 < len(rest):
                return [rest[i + 1]]
            if t.startswith("--target-directory="):
                return [t.split("=", 1)[1]]
        pos = _positionals(rest, frozenset(("-m", "--mode", "-o", "-g", "-s",
                                            "--preserve", "--no-target-directory",
                                            "--backup")))
        return pos[-1:] if pos else []
    if base in ("chown", "chmod"):
        return _positionals(rest, frozenset())[-1:]
    if base == "tee":
        return _positionals(rest, frozenset(("-a", "-i", "-p")))[-1:]
    if base == "dd":
        return [t[3:] for t in rest if t.startswith("of=")]
    if base == "rsync":
        pos = _positionals(rest, frozenset(("-e", "--rsh", "--log-file", "--backup-dir")))
        extra = [t.split("=", 1)[1] for t in rest
                 if t.startswith("--log-file=") or t.startswith("--backup-dir=")]
        return (pos[-1:] if pos else []) + extra
    if base == "tar":
        for i, t in enumerate(rest):
            if t == "-C" and i + 1 < len(rest):
                return [rest[i + 1]]
            if t.startswith("--directory="):
                return [t.split("=", 1)[1]]
        return []
    if base == "restic":
        pos = _positionals(rest, frozenset(("-r", "--repo", "--password-file", "--cache-dir")))
        if not pos or pos[0] not in _RESTIC_WRITE_VERBS:
            return []
        repo = None
        for i, t in enumerate(rest):
            if t in ("-r", "--repo") and i + 1 < len(rest):
                repo = rest[i + 1]
            if t.startswith("--repo="):
                repo = t.split("=", 1)[1]
        if repo is None:
            return ["<unresolvable repo: no --repo flag>"]
        return [repo]
    if base == "borg":
        pos = _positionals(rest, frozenset(("--repo", "-r", "--stats")))
        if not pos or pos[0] not in _BORG_WRITE_VERBS:
            return []
        if len(pos) < 2:
            return ["<unresolvable repo: no repository argument>"]
        return [pos[1].split("::", 1)[0]]
    if base == "rclone":
        pos = _positionals(rest, frozenset(("--config", "--log-file", "--backup-dir")))
        if not pos or pos[0] not in _RCLONE_WRITE_VERBS:
            return []
        if len(pos) < 2:
            return ["<unresolvable target: rclone write with no destination>"]
        dest = pos[-1]
        if re.match(r"^[A-Za-z0-9_.-]+:", dest):
            return ["<unresolvable target: remote>"]
        return [dest]
    if base == "git":
        pos = _positionals(rest, frozenset(("-C", "-c", "-b", "-B", "--branch")))
        if not pos:
            return []
        sub = pos[0]
        if sub in _GIT_WRITE_VERBS:
            return pos[-1:] if len(pos) > 1 else []
        if sub == "worktree" and len(pos) > 1 and pos[1] == "add":
            return pos[-1:] if len(pos) > 2 else []
        return []
    if base in ("rm", "rmdir"):
        return _positionals(rest, frozenset(("-r", "-f", "-d", "-v", "--dir", "--preserve-root")))
    return []


_REDIRECT = re.compile(r"(?:^|[\s;])[0-9&]*(>>?)\s*(\S+)")


def redirect_targets(segment: str) -> list[str]:
    out = []
    for m in _REDIRECT.finditer(segment):
        target = m.group(2).rstrip(";&|")
        if target:
            out.append(target)
    return out


def _resolve(raw: str, cwd: str) -> tuple[str | None, str | None]:
    """(resolved path, None) or (None, reason) when it cannot be resolved."""
    if raw.startswith("<unresolvable"):
        # internal sentinels from the tool-specific target extractors —
        # checked BEFORE trimming so their angle brackets survive
        return None, raw.strip("<>")
    raw = raw.strip(_PATH_TRIM)
    if not raw or raw.startswith("-"):
        return None, "not a target"
    if re.match(r"^[A-Za-z0-9_.-]+:", raw):
        return None, f"remote or URI target '{raw}' cannot be resolved"
    if "$" in raw:
        if raw == "$HOME" or raw.startswith("$HOME/"):
            home = os.environ.get("HOME", "")
            if not home:
                return None, "cannot expand $HOME (HOME unset)"
            raw = home + raw[len("$HOME"):]
        else:
            return None, f"variable-expanded target '{raw}' is not resolvable"
    if raw.startswith("~"):
        expanded = os.path.expanduser(raw)
        if "~" in expanded:
            return None, f"cannot expand '~' in target '{raw}'"
        raw = expanded
    if '"' in raw or "'" in raw:
        return None, (f"quoted target '{raw}' is not resolvable — the guard strips "
                      "quoted runs before scanning, so write the path unquoted")
    if not raw.startswith(os.sep):
        raw = os.path.join(cwd, raw)
    return os.path.realpath(raw), None


def class_b_verdict(segment: str, tokens: list[str], verb: str | None, verb_idx: int,
                    cwd: str, roots: tuple[str, ...],
                    allowlist: list[str] | None) -> dict | None:
    """Refusal dict for a CLASS B violation, or None.

    ``allowlist`` is None when it could not be loaded — fail closed: any
    out-of-root target is refused as ``allowlist_unavailable`` rather than
    guessed at.
    """
    targets = class_b_targets(verb, tokens, verb_idx) + redirect_targets(segment)
    for raw in targets:
        path, why = _resolve(raw, cwd)
        if path is None:
            return {"code": "unresolvable_target", "tool": verb or "redirection",
                    "detail": f"write target '{raw}' cannot be resolved: {why}. "
                              "The guard does not fail open on ambiguity."}
        if path == "/dev/null":
            continue  # discard device — a deliberate carve-out, zero risk
        if not _inside(path, roots):
            if allowlist is None:
                return {"code": "allowlist_unavailable", "tool": verb or "redirection",
                        "detail": f"write to '{path}' is outside the containment root but "
                                  "the operator allowlist could not be read — refusing "
                                  "out-of-root writes until it parses."}
            if any(path == p or path.startswith(p + os.sep) for p in allowlist):
                continue
            return {"code": "write_outside_containment_root", "tool": verb or "redirection",
                    "detail": f"write to '{path}' is outside the containment root. Allowed: "
                              "/mnt/raid0/llm/**, /workspace/**, /tmp/opencode/**, "
                              "~/.claude/**, ~/.codex/**, bare /tmp/**. Operators may add "
                              "this path prefix to scripts/hooks/filesystem_allowlist.yaml "
                              "(or set EPYC_FS_ACK for a one-off)."}
    return None


# --------------------------------------------------------------------------- #
# Allowlist (operator-maintained, fail-closed)
# --------------------------------------------------------------------------- #

class AllowlistError(Exception):
    pass


def _validate_entries(entries) -> list[str]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise AllowlistError("entries must be a list")
    prefixes = []
    for e in entries:
        if not isinstance(e, dict):
            raise AllowlistError("each entry must be a mapping")
        for key in e:
            if key not in ("path", "reason", "added_by", "added_on"):
                raise AllowlistError(f"unknown entry key '{key}'")
        for key in ("path", "reason", "added_by", "added_on"):
            value = e.get(key)
            # YAML 1.1 parses `2026-08-23` as a timestamp; the strict parser
            # and the operator's own file use the string form. Normalise.
            if key == "added_on" and not isinstance(value, str):
                try:
                    value = value.isoformat()
                except (AttributeError, TypeError, ValueError):
                    raise AllowlistError(f"entry '{key}' must be a date or string")
                e[key] = value
            if not isinstance(value, str) or not value.strip():
                raise AllowlistError(f"entry missing non-empty '{key}'")
        path = e["path"].strip()
        if not path.startswith(os.sep):
            raise AllowlistError(f"entry path '{path}' must be absolute")
        prefixes.append(os.path.realpath(os.path.expanduser(path)))
    return prefixes


def _parse_strict_yaml(text: str) -> list[str]:
    """PyYAML-free parser for EXACTLY the documented allowlist shape.

    Runs where PyYAML is absent (the repo's ``uv run --with pytest`` test
    environment). Any construct outside the shape — anchors, inline lists,
    tabs, unknown keys, a different schema version — is a parse ERROR and the
    guard fails closed. Production uses PyYAML via ``safe_load``; both paths
    converge on ``_validate_entries``, and the shipped file parses identically
    under both.
    """
    schema = None
    entries: list[dict] = []
    cur: dict | None = None
    in_entries = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            raise AllowlistError(f"line {lineno}: tabs are not allowed")
        m = re.match(r"^schema:\s*(.+)$", line)
        if m:
            schema = m.group(1).strip().strip("\"'")
            continue
        m = re.match(r"^entries:\s*\[\]\s*$", line)
        if m:
            in_entries = True
            continue
        m = re.match(r"^entries:\s*$", line)
        if m:
            in_entries = True
            continue
        m = re.match(r"^  - (?:([a-z_]+):\s*(.*))?$", line)
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {}
            if m.group(1):
                key, value = m.group(1), m.group(2).strip()
                if key not in ("path", "reason", "added_by", "added_on"):
                    raise AllowlistError(f"line {lineno}: unknown key '{key}'")
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                cur[key] = value
            continue
        m = re.match(r"^    ([a-z_]+):\s*(.*)$", line)
        if m and in_entries and cur is not None:
            key, value = m.group(1), m.group(2).strip()
            if key not in ("path", "reason", "added_by", "added_on"):
                raise AllowlistError(f"line {lineno}: unknown key '{key}'")
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            cur[key] = value
            continue
        raise AllowlistError(f"line {lineno}: cannot parse '{line}'")
    if cur is not None:
        entries.append(cur)
    if schema != ALLOWLIST_SCHEMA:
        raise AllowlistError(f"schema must be '{ALLOWLIST_SCHEMA}', got '{schema}'")
    return _validate_entries(entries)


def load_allowlist(path: Path) -> list[str] | None:
    """realpath'd prefixes from the allowlist; None when it cannot be read.

    None is NOT an empty allowlist: it is a broken guard, and CLASS B treats it
    as ``allowlist_unavailable`` — refuse out-of-root writes until the file
    parses. A valid-but-empty allowlist returns [].
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        import yaml  # lazy: absent in the uv test env, present in production
    except ImportError:
        try:
            return _parse_strict_yaml(text)
        except AllowlistError:
            return None
    try:
        data = yaml.safe_load(text)
        if data is None:
            return []
        if not isinstance(data, dict):
            raise AllowlistError("allowlist document must be a mapping")
        if data.get("schema") != ALLOWLIST_SCHEMA:
            raise AllowlistError(f"schema must be '{ALLOWLIST_SCHEMA}', got "
                                 f"{data.get('schema')!r}")
        return _validate_entries(data.get("entries"))
    except (yaml.YAMLError, AllowlistError):
        return None


# --------------------------------------------------------------------------- #
# The scan
# --------------------------------------------------------------------------- #

def scan_command(command: str, cwd: str | None = None,
                 allowlist_path: Path | None = None) -> dict:
    """One refusal dict (code/detail/tool) or an allowed dict."""
    cwd = os.path.realpath(cwd or os.getcwd())
    roots = containment_roots()
    allowlist = load_allowlist(allowlist_path or ALLOWLIST_PATH)

    vcwd = cwd
    class_a: dict | None = None
    class_b: dict | None = None
    for seg in segments(command):
        seg = seg.strip()
        if not seg:
            continue
        tokens = [t for t in seg.split() if t]
        verb, verb_idx = verb_of(tokens)
        if verb == "cd":
            pos = _positionals(tokens[verb_idx + 1:], frozenset(("-P", "-L")))
            if pos:
                nxt, _ = _resolve(pos[-1], vcwd)
                if nxt:
                    vcwd = nxt
        a = class_a_verdict(tokens, verb)
        if a is not None and class_a is None:
            class_a = a
        b = class_b_verdict(seg, tokens, verb, verb_idx, vcwd, roots, allowlist)
        if b is not None and class_b is None:
            class_b = b
    if class_a is not None:
        return class_a
    if class_b is not None:
        return class_b
    return {"verdict": "allowed"}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _read_command(argv: list[str]) -> tuple[str | None, str | None]:
    """(command, cwd) from argv `--command`, or the PreToolUse stdin shape."""
    cwd = None
    cmd = None
    i = 0
    while i < len(argv):
        if argv[i] == "--command" and i + 1 < len(argv):
            cmd = argv[i + 1]
            i += 2
        elif argv[i] == "--cwd" and i + 1 < len(argv):
            cwd = argv[i + 1]
            i += 2
        elif argv[i] == "--allowlist" and i + 1 < len(argv):
            global ALLOWLIST_PATH
            ALLOWLIST_PATH = Path(argv[i + 1])
            i += 2
        else:
            return None, None
    if cmd is not None:
        return cmd, cwd
    data = sys.stdin.read()
    if not data.strip():
        return None, None
    try:
        payload = json.loads(data)
        if isinstance(payload, dict) and isinstance(payload.get("tool_input"), dict):
            cmd = payload["tool_input"].get("command")
            if isinstance(cmd, str) and cmd.strip():
                return cmd, cwd
    except json.JSONDecodeError:
        pass
    return data, cwd


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--help" in argv or "-h" in argv:
        print(__doc__.split("EXIT PROTOCOL")[0].split('"""')[0].strip())
        return 0
    try:
        cmd, cwd = _read_command(argv)
        if cmd is None or not cmd.strip():
            print("error: no command given (--command <cmd> or PreToolUse JSON on stdin) "
                  "— refusing to emit a verdict (empty input must never produce a clean scan)",
                  file=sys.stderr)
            return 2
        ack = os.environ.get(ACK_ENV, "").strip()
        if ack:
            print(json.dumps({"verdict": "allowed", "ack": ack,
                              "note": "operator ack EPYC_FS_ACK present in the hook "
                                      "environment; command allowed and recorded"}))
            return 0
        verdict = scan_command(cmd, cwd=cwd)
        if verdict.get("verdict") == "allowed":
            return 0
        detail = verdict.get("detail", "refused")
        print(detail, file=sys.stderr)
        print(json.dumps(verdict))
        return 2
    except AllowlistError as exc:
        print(f"error: allowlist configuration is broken: {exc} — failing closed",
              file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — a crashed guard must refuse, not allow
        print(f"error: scanner failed: {exc!r} — failing closed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

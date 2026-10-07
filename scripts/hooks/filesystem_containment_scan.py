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
wraps it for the opencode plugin; ``codex_filesystem_containment.py`` bridges the
codex PreToolUse hook; ``generate_opencode_permissions.py`` derives the opencode
permission.bash deny block from ``--dump-rules`` (the ONE exported truth; the
harness-parity tests fail on any drift).

THREE CLI MODES, one rule set:

  * ``--command "<cmd>"`` — scan a Bash command (CLASS A + CLASS B). The
    PreToolUse JSON stdin shape (``tool_input.command`` / ``tool_input.file_path``)
    is also accepted with no flags.
  * ``--check-path <path>`` — decide one FILE path (the Write|Edit surface) with
    the SAME containment roots + operator allowlist as CLASS B: 0 if the
    realpath'd path is inside a root, under an allowlist prefix, or /dev/null;
    2 otherwise (fail-closed when the allowlist cannot be read). This replaced
    the old hand-written allow-set in ``check_filesystem_path.sh`` (which allowed
    ``/mnt/raid0/*`` broadly; the scanner allows ``/mnt/raid0/llm/**`` —
    equivalent in practice because /mnt/raid0 contains only llm/).
  * ``--dump-rules`` — emit the canonical rule tables (class A verbs, package
    tools/actions, dpkg flags, write verbs by tool, containment roots realpath'd)
    as deterministic JSON. Generators and parity tests consume THIS, never a
    hand-copied table.

TWO REFUSAL CLASSES.

  CLASS A — privileged host-level operations, OPERATOR-ONLY: sudo/su-prefixed or
  bare ``mount`` ``umount`` ``mkfs*`` (plus ``mke2fs``, same family) ``fdisk``
  ``parted`` ``mkswap`` ``systemctl`` ``modprobe`` ``shutdown`` ``reboot``,
  ``apt|apt-get install|remove|purge|autoremove``, ``dpkg -i|--install|-r|--remove``,
  and ``dd`` with ``of=/dev/*`` (except ``/dev/null`` — a discard device, zero
  risk; stated so a clean scan is not mistaken for laziness). Refused with code
  ``host_level_privileged_operation`` naming the exact command token.

  CLASS B — writes OUTSIDE the containment root: ``mkdir`` ``touch`` ``cp`` ``mv``
  ``tee`` ``dd of=`` write redirection (``>`` ``>>`` ``>|`` ``&>`` ``<>``; fd
  duplication ``2>&1``/``>&2`` writes no file) ``rsync`` ``tar`` (``-f`` unless
  extracting or listing; extraction into ``-C`` or the cwd), ``restic backup|init --repo``
  ``borg create|init`` ``rclone`` (write verbs) ``chown`` ``chmod``, plus
  deliberate siblings ``ln`` ``install`` ``rm`` ``rmdir`` ``unlink`` ``shred``
  ``truncate`` ``chgrp`` ``sed -i`` ``find -delete|-exec`` (deletion of data
  outside the root is the same incident class, so ``mv``'s SOURCES are targets,
  and so are a hard link's — ``ln``, ``cp -l`` alias the file) and ``git
  clone|init|worktree add`` (``-C`` honoured). Refused with
  ``write_outside_containment_root`` naming the path. Targets come from a
  per-tool option grammar (``_ARG_SPECS``), never from "the last word":
  redirections are removed from the argument list first, and where an operand
  might be an option's value it is checked both ways.

THE COMMAND IS READ AS BASH READS IT (``shell_scan.lex``, one pass): quotes,
escapes, line continuations, comments and heredocs. Shell keywords (``do``,
``then``, ``!``) are skipped like runners. Subshells, ``$(...)``, backticks,
process substitutions, ``sh -c`` strings and heredocs/here-strings fed to a
shell are each scanned as commands, with the cwd of the moment they run.

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
Quoted text is read (``"/x"`` is /x), but a target holding a quoted or escaped
special character (``"$D"``, ``my\\ file``), a ``$OTHER`` variable, a command
substitution or an rclone ``remote:`` is REFUSED with ``unresolvable_target``.
The guard does NOT fail open on ambiguity. Brace lists are expanded and globs
matched on disk (a match may be a symlink out of the root); a target under a
link made earlier in the same command is refused, since realpath cannot see it yet.
Relative targets resolve against ``--cwd`` (the plugin passes the session's
directory; the Claude hook runs in the session's project dir). ``cd`` inside a
chained command tracks a VIRTUAL cwd, so ``cd /mnt/bigdisk && mkdir -p x`` resolves
``x`` against the device — closing a bypass the naif implementation would have
shipped. ``pushd``/``popd``, ``env -C`` and ``sudo -D`` are followed; a cd in a
subshell, pipeline stage or background job does not persist. A directory change
it cannot resolve (``cd $X``, ``cd -``, ``sudo -i``) makes every later relative
target unresolvable, rather than resolving it against the old directory.

KNOWN SCOPE LIMITS, stated so a clean scan is not mistaken for containment
(same trade-offs ``operator_apply_copy_scan.py`` and the pattern-kill guard make
and document):
  * A PreToolUse hook sees the command an AGENT TYPES. A daemon, a cron job, or a
    script that internally shells out is invisible to it — the enforcing layer
    there is OS-level (separate uid / read-only mounts), as
    ``coordination/session-bus/human_only_paths.yaml`` already records.
  * Code the guard cannot read as a command is not scanned: a verb spelled
    with a variable or substitution (``$RM -rf x``), text piped into a shell
    (``echo CMD | sh``), interpreter code (``python -c``, ``perl -i``), and
    operands fed on stdin (``... | xargs rm``). ``xargs``- and ``find
    -exec``-dispatched verbs with literal operands ARE caught.
  * A path spelled with a variable other than ``$HOME`` is refused as
    unresolvable, not silently allowed.
  * A link moved or copied into place within ONE command (``mv``/``cp -a``/
    ``tar x`` of a symlink) is not followed; realpath sees it from the next
    command on. ``git -C DIR`` subcommands other than clone/init/worktree add
    are not checked. The enumerated tool list is deliberate and extended only
    with same-class siblings, each documented.
  * The option tables approximate GNU getopt, not each tool's full flag set:
    an unlisted value option AFTER the destination is caught by the both-ways
    check only for long options (``--opt VALUE``), not short ones.

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

import glob
import itertools
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_scan import SEPARATORS, lex  # noqa: E402  — the repo's ONE shell scanner

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
       python3.12 python3.13 uv pipenv poetry run exec builtin busybox ionice chrt
       doas eval coproc if then else elif do while until !""".split()
)
# Runner flags that CONSUME the following token as their value, PER RUNNER.
# `-n` is a bare flag on sudo but takes a value on nice; `-c` is the inner
# command on bash but a bare flag on stdbuf. A single global set would read
# `sudo -n mkdir` as "value mkdir" and lose the verb — the exact defect class
# this repo has paid for four times. Default: no value flags. Origin
# 2026-10-07: shell keywords (`do cp ... /outside`), `exec`/`builtin`, a
# clustered `sudo -nu root`, `numactl --interleave all` and `xargs -a FILE`
# all hid the verb; `env --unset=X mkdir` swallowed it.
_RUNNER_VALUE_FLAGS: dict[str, frozenset[str]] = {k: frozenset(v.split()) for k, v in {
    "sudo": "-u -U -g -G -p -h -C -D -r -t -T --user --group --host --prompt "
            "--chdir --close-from --role --type --command-timeout",
    "su": "-c -l -s -p -m",
    "env": "-u -C -S --unset --chdir --split-string",
    "nice": "-n --adjustment",
    "timeout": "-s -k --signal --kill-after",
    "stdbuf": "-i -o -e --input --output --error",
    "taskset": "-c",
    "numactl": "-m -N -i -C -p -P -w --membind --cpunodebind --interleave "
               "--physcpubind --preferred --preferred-many --weighted-interleave",
    "xargs": "-I -L -n -a -d -E -s -P --arg-file --delimiter --max-args --max-procs "
             "--max-chars --process-slot-var",
    "strace": "-o -e -p -s -u -E -a -b -I -O -P -S -X",
    "time": "-o -f --output --format",
    "ionice": "-c -n -p -P -u --class --classdata --pid --pgid --uid",
    "exec": "-a", "doas": "-u -C",
    "run": "-p --with --with-requirements --with-editable --python --project --directory "
           "--env-file --group --extra --package --index --from",   # `uv run`
    "bash": "-c", "sh": "-c", "zsh": "-c", "dash": "-c", "ksh": "-c",
}.items()}
_TRIM = "\"'`()[]{};,&<>|$"
# Paths keep `$` visible: stripping it would launder `$DEST/x` into a relative
# path and silently ALLOW a variable target instead of refusing it.
_PATH_TRIM = "\"'`()[]{};,&<>|"
# A `(...)` or `` `...` `` cut out of a segment is replaced by OPEN n CLOSE
# (_groups); lex() maps any private-use input character away, so neither these
# nor its quoted/escaped-character stand-ins (U+E000-E07F) can be typed.
_OPEN, _CLOSE = chr(0xE100), chr(0xE101)
_STAND_IN = re.compile(f"[{chr(0xE000)}-{chr(0xE07F)}]")
_NOT_A_VERB = re.compile(rf"[^()]*\)|\w*{_OPEN}\d+{_CLOSE}")


def _normalize(tok: str) -> str:
    # quote removal first: `"mkdir"` and `m"kd"ir` are mkdir (lex keeps the text)
    return re.sub("[\"']", "", tok).strip(_TRIM)


def _takes_value(flag: str, flags: frozenset[str]) -> bool:
    """Does FLAG consume the NEXT token? `-u` yes; `-uroot`, `--user=x` no; a
    cluster yes when its last letter is a value flag (`sudo -nu root`)."""
    if flag.startswith("--"):
        return flag in flags
    for j, ch in enumerate(flag[1:], 1):
        if "-" + ch in flags:
            return j == len(flag) - 1
    return False


def _env_assignment(tok: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok))


def verb_of(tokens: list[str]) -> tuple[str | None, int]:
    """(verb token, index of its first token) for one invocation segment.

    VERB POSITION, not word-anywhere: ``grep mount /etc/fstab`` has verb
    ``grep`` — ``mount`` there is an operand, not a command, and must not be
    refused (the C21 lesson: a guard that fires on text blocks the grep
    searching for it). Env assignments (``VAR=x``) and runner prefixes
    (``sudo -n``, ``timeout 5``, ``env -i``) are skipped; path-qualified
    verbs (``/usr/bin/mount``) are normalized; quoted (``"mount"``) and
    escaped (``\\mount``) verbs are read as the verb; shell keywords (``do``,
    ``then``, ``!``) are skipped like runners. Command substitutions and
    subshells arrive here already cut out and scanned on their own (_groups).
    """
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        norm = _normalize(tok)
        base = norm.split("/")[-1]
        if _env_assignment(tok) or not norm.strip() or _NOT_A_VERB.fullmatch(tok):
            # a quoted run lex blanked, a case pattern `a)`, a cut-out
            # subshell or `f()` header — data or syntax, not a command word
            i += 1
            continue
        if base in ("case", "function"):   # `case W in`, `function NAME`
            i += 2 if base == "function" else (tokens[i:] + ["in"]).index("in") + 1
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
                # the RAW flag: normalizing `-I{}` to `-I` made it swallow the
                # verb (`xargs -I{} cp {} /outside`) — origin 2026-10-07
                if _takes_value(t, flags) and i < len(tokens):
                    i += 1
                continue
            if re.match(r"^(?:[+-]?\d+(\.\d+)?[smhd]?|0x[0-9a-fA-F]+)$", tn):
                i += 1   # a timeout, nice level or taskset mask
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

# Per-tool option grammar: (short letters that take a value, long options that
# REQUIRE one). Optional-argument long options (`--backup[=C]`, `--preserve[=A]`)
# take a value only with `=` and are deliberately absent; booleans are never
# listed. Origin 2026-10-07: one global value-flag list per tool listed booleans
# (`rm -r /x`, `tee -a /x`, `cp a --preserve /x`, `cd -P /x`) so the flag
# swallowed the destination and nothing was checked — a containment bypass.
_ARG_SPECS: dict[str, tuple[str, str]] = {
    "cd": ("", ""), "tee": ("", ""), "rm": ("", ""), "rmdir": ("", ""),
    "unlink": ("", ""), "truncate": ("rs", "reference size"),
    "shred": ("ns", "iterations size random-source"),
    "sed": ("efl", "expression file line-length"),
    "mkdir": ("m", "mode"),
    "touch": ("dtr", "date reference time"),
    "cp": ("St", "no-preserve sparse suffix target-directory"),
    "mv": ("St", "suffix target-directory"),
    "ln": ("St", "suffix target-directory"),
    "install": ("gmoSt", "group mode owner strip-program suffix target-directory"),
    "chown": ("", "from reference"), "chgrp": ("", "from reference"),
    "chmod": ("", "reference"),
    "borg": ("eCr", "repo exclude exclude-from pattern patterns-from compression "
             "comment timestamp chunker-params checkpoint-interval files-cache "
             "remote-path rsh lock-wait umask upload-ratelimit encryption storage-quota"),
    "git": ("CcbBoju", "git-dir work-tree namespace config-env branch origin upload-pack "
            "reference reference-if-able depth shallow-since shallow-exclude "
            "separate-git-dir config template filter jobs server-option bundle-uri "
            "revision initial-branch object-format ref-format reason"),
    # partial tables — options whose VALUES are read, plus common ones. An
    # unlisted value option is harmless where no operand is a target (tar,
    # restic) and covered by _getopt's ambiguity set where one is (rsync, rclone)
    "rsync": ("efBTM@", "rsh filter exclude include log-file backup-dir temp-dir "
              "write-batch only-write-batch"),
    "tar": ("bCfFgHIKLNTVX", "directory file listed-incremental"),
    "restic": ("r", "repo"),
    "rclone": ("", "config log-file backup-dir exclude include filter transfers checkers"),
}


def _getopt(tokens: list[str], short_vals: str = "", long_vals: str = ""
            ) -> tuple[list[str], list[tuple[str, str | None]], set[int]]:
    """(positionals, [(option, value-or-None)], ambiguous) — a getopt_long
    approximation.

    Short clusters stop at the first value letter (`-at DIR`, `-tDIR`). A long
    option consumes the next token on an exact name or a getopt prefix
    abbreviation (`--target DIR`). ``ambiguous`` holds indices of positionals
    that may instead be an option's value: an abbreviation's value (kept as a
    positional too — a boolean can prefix a value option, install `--strip`
    vs `--strip-program`) and a word after an unlisted `--option` (the
    rsync/rclone tables are partial). A bare `-` (stdin/stdout) is neither;
    `--` makes the rest positional.
    """
    longs = long_vals.split()
    pos: list[str] = []
    opts: list[tuple[str, str | None]] = []
    amb: set[int] = set()
    i = 0
    while i < len(tokens):
        t = tokens[i]
        i += 1
        if t == "--":
            pos += tokens[i:]
            break
        if t.startswith("--"):
            name, eq, val = t[2:].partition("=")
            full = name if name in longs else next(
                (v for v in longs if name and v.startswith(name)), None)
            if eq:
                opts.append((full or name, val))
            elif full and i < len(tokens):
                opts.append((full, tokens[i]))
                if full != name:
                    amb.add(len(pos))
                    pos.append(tokens[i])
                i += 1
            else:
                opts.append((name, None))
                if i < len(tokens) and not tokens[i].startswith("-"):
                    amb.add(len(pos))
        elif t.startswith("-") and t != "-":
            for j, ch in enumerate(t[1:], 1):
                if ch in short_vals:
                    val = t[j + 1:]
                    if not val and i < len(tokens):
                        val, i = tokens[i], i + 1
                    opts.append((ch, val))
                    break
                opts.append((ch, None))
        elif t != "-":
            pos.append(t)
    return pos, opts, amb


def _last_dest(pos: list[str], amb: set[int]) -> list[str]:
    """The destination operand; when it may be an option's value (see
    _getopt), the operand before it too — checked both ways, fail-closed."""
    return pos[-2:] if len(pos) > 1 and len(pos) - 1 in amb else pos[-1:]


_RESTIC_WRITE_VERBS = frozenset("backup init".split())
_BORG_WRITE_VERBS = frozenset("create init".split())
_RCLONE_WRITE_VERBS = frozenset("copy sync move delete deletefile purge rcat".split())
_GIT_WRITE_VERBS = frozenset("clone init".split())


def rules_dump() -> dict:
    """The canonical rule tables as a JSON-serializable, deterministically
    ordered dict — the ONE exported truth every derived surface consumes.

    Consumed by ``generate_opencode_permissions.py`` (the opencode
    permission.bash deny block) and by the harness-parity tests. NEVER
    hand-copy these tables into another file: a second copy is drift by
    construction (INC-20260823-filesystem-containment-gap built the guard in
    two surfaces with duplicated hand-written rules). Ordering: frozenset
    tables are sorted (sets have no order); the dpkg flag tuple keeps its
    source order.
    """
    return {
        "class_a_verbs": sorted(_CLASS_A_VERBS),
        "mkfs_prefix": "mkfs",  # class A treats any base.startswith("mkfs") as privileged
        "pkg_tools": sorted(_PKG_TOOLS),
        "pkg_actions": sorted(_PKG_ACTIONS),
        "dpkg_install_flags": list(_DPKG_INSTALL_FLAGS),
        "write_verbs": {
            "restic": sorted(_RESTIC_WRITE_VERBS),
            "borg": sorted(_BORG_WRITE_VERBS),
            "rclone": sorted(_RCLONE_WRITE_VERBS),
            "git": sorted(_GIT_WRITE_VERBS),
        },
        "containment_roots": list(containment_roots()),
    }


def class_b_targets(verb: str | None, tokens: list[str], verb_idx: int) -> list[str]:
    """Raw target strings the invocation writes to, or [] if none.

    ``tokens`` must already be free of redirections (scan_command strips them;
    redirect_targets() checks them) — see the origin note on _REDIRECT.
    """
    if verb is None:
        return []
    base = verb.split("/")[-1]
    rest = tokens[verb_idx + 1:] if verb_idx >= 0 else tokens
    if base == "dd":
        return [t[t.index("=") + 1:] for t in rest if _normalize(t).startswith("of=")]
    if base not in _ARG_SPECS or base == "cd":
        return []
    spec = _ARG_SPECS[base]
    if base == "tar" and rest and not rest[0].startswith("-"):
        # old-style bundle (`tar czf F src`): values follow in letter order
        out, k = [], 1
        for c in rest[0]:
            out.append("-" + c)
            if c in spec[0] and k < len(rest):
                out, k = out + [rest[k]], k + 1
        rest = out + rest[k:]
    pos, opts, amb = _getopt(rest, *spec)

    def vals(*names: str) -> list[str]:
        return [v for n, v in opts if n in names and v and v != "-"]

    names = {n for n, _ in opts}
    if base in ("mkdir", "touch", "tee", "rm", "rmdir", "unlink", "truncate", "shred"):
        return pos  # every operand is written (tee writes ALL its files)
    if base == "sed":  # -i rewrites every FILE; operand 1 is the script unless -e/-f
        edits = names & {"i", "in-place"}
        return [] if not edits else pos if vals("e", "f", "expression", "file") else pos[1:]
    if base in ("cp", "mv", "ln", "install"):
        to = vals("t", "target-directory")
        if base == "install" and not to and names & {"d", "directory"}:
            return pos  # install -d: every operand is a directory created
        dest = to or (["."] if len(pos) == 1 else _last_dest(pos, amb))  # `ln -s X`: ./X
        # Origin 2026-10-07: mv DELETES its sources (rm's incident class), and
        # a hard link (ln, cp -l) is a writable alias of an out-of-root file
        # that realpath can never see through: their sources are targets too.
        aliased = (base == "mv" or names & {"l", "link"} and base == "cp"
                   or base == "ln" and not names & {"s", "symbolic"})
        return dest + (pos if to or len(pos) == 1 else pos[:-1]) * bool(aliased)
    if base in ("chown", "chgrp", "chmod"):
        # operand 1 is OWNER/MODE — unless --reference, or chmod got the mode
        # as an option-looking word (`chmod -w f`): then every operand is a file
        mode_opt = base == "chmod" and any(len(n) == 1 and n in "rwxXst" for n in names)
        return pos if vals("reference") or mode_opt else pos[1:]
    if base == "rsync":
        return (_last_dest(pos, amb) + vals("log-file", "backup-dir", "T", "temp-dir",
                                            "write-batch", "only-write-batch")
                + pos[:-1] * ("remove-source-files" in names))
    if base == "tar":
        # -f is a write unless a read mode is named; extraction writes into -C
        # (cumulative, like cd) or the cwd — origin 2026-10-07: `tar xzf a.tgz`
        # from an out-of-root cwd was never checked. -C on create is a read
        # dir, refused anyway (fail-closed, as before).
        reading = names & {"x", "t", "d", "extract", "get", "list", "diff", "compare"}
        into = names & {"x", "extract", "get"} and not names & {"O", "to-stdout"}
        cdir = [os.path.join(*vals("C", "directory"))] if vals("C", "directory") else []
        return (cdir + vals("g", "listed-incremental", "one-top-level")
                + (["."] if into and not cdir else [])
                + ([] if reading else vals("f", "file"))
                + pos * ("remove-files" in names))
    if base == "restic":
        if not any(p in _RESTIC_WRITE_VERBS for p in pos):
            return []
        return vals("r", "repo")[-1:] or ["<unresolvable repo: no --repo flag>"]
    if base == "borg":
        k = next((i for i, p in enumerate(pos) if p in _BORG_WRITE_VERBS), None)
        if k is None:
            return []
        repo = vals("r", "repo")[-1:] or pos[k + 1:k + 2]
        return ([repo[0].split("::", 1)[0]] if repo
                else ["<unresolvable repo: no repository argument>"])
    if base == "rclone":
        k = next((i for i, p in enumerate(pos) if p in _RCLONE_WRITE_VERBS), None)
        if k is None:
            return []
        dest = _last_dest(pos, amb) if len(pos) > k + 1 else []
        return (dest + vals("log-file", "backup-dir")
                or ["<unresolvable target: rclone write with no destination>"])
    # git. Origin 2026-10-07: `worktree add <path> <commit-ish>` took the last
    # positional (the BRANCH) as the target, so `git worktree add /outside/x br`
    # passed from an in-root cwd; -C was ignored (`git -C /outside init`).
    sub = pos[0] if pos else None
    if sub == "clone" and len(pos) > 1:
        # dir is operand 2 (else ./<repo>); also pos[-1], in case an unlisted
        # value option shifted the front count — both ways
        found = list(dict.fromkeys([pos[2], pos[-1]])) if len(pos) > 2 else ["."]
    elif sub == "init":
        found = pos[1:2] or ["."]
    elif sub == "worktree" and pos[1:2] == ["add"]:
        found = pos[2:3]  # the path; a trailing commit-ish is not a target
    else:
        return []
    found += vals("separate-git-dir", "git-dir", "work-tree") if found else []
    return [os.path.join(*vals("C"), t) for t in found]


# A redirection anywhere in a segment (lex() has made quoted and escaped
# characters data). [n] / {var} prefix only as a whole word; `>(...)` is
# process substitution (cut out by _groups). Groups: & before, operator, & after, word.
# Origin 2026-10-07: the old pattern `[0-9&]*(>>?)\s*(\S+)` (1) read fd
# duplication `2>&1` / `>&2` as a write to the FILE '<cwd>/1' — refused from
# any out-of-root cwd; (2) missed `x>/f` (no space before `>`), `>& /f` and
# `>|` (split at its `|` by segments()) — bypasses; and (3) left redirection
# words in the tokens, so `cp s /outside 2>/dev/null` checked '2>/dev/null' as
# cp's destination and never the real one — a bypass. Tokens are now built
# from the segment with redirections removed (_argv).
_REDIRECT = re.compile(
    r"(?:(?<![^\s<>;&|()])(?:\d+|\{\w+\}))?(&?)(>>?|<>|<<<|<<-?|<)(&?)[ \t]*"
    rf"(?![({_OPEN}])([^\s<>;&|()]*)")


def _dequote(word: str) -> str:
    """Quote removal. lex(keep_quoted) left quoted characters as data: plain ones
    as themselves, the rest as stand-ins that _resolve refuses — so `"-t"` is
    the option -t and `"/x"` the path /x, exactly as the command receives them.
    Origin 2026-10-07: `cp "-t" /outside a` read "-t" as a source and checked
    `a`. An empty quoted word stays a (refused) operand."""
    return re.sub("[\"']", "", word) or word


_SHELLS = frozenset("bash sh zsh dash ksh su".split())


def _decode(word: str) -> str:
    """A -c string back to shell text: lex's stand-ins become their characters."""
    return "".join(chr(ord(c) - 0xE000) if _STAND_IN.match(c) else c for c in word)


def _argv(segment: str) -> list[str]:
    """The segment's words minus redirections and process substitutions —
    neither is an argument of the command (origin note on _REDIRECT)."""
    return [_dequote(t) for t in
            _REDIRECT.sub(" ", re.sub(rf"[<>]{_OPEN}\d+{_CLOSE}", " ", segment)).split()]


def redirect_targets(segment: str) -> list[str]:
    """File words of write redirections: `>F` `>>F` `>|F` `<>F` `&>F` `&>>F`,
    and `>&F` when F is not a number or `-`. Fd duplication or closing
    (`2>&1`, `>&2`, `3>&-`, `1>&2-`) is not a file write."""
    out = []
    if re.match(r"(?:!\s+)?\[\[\s", segment):          # `[[ a > b ]]` compares
        segment = segment[segment.rfind(" ]]") + 3:]
    for m in _REDIRECT.finditer(segment):
        amp_before, op, amp_after, word = m.groups()
        if (not word or (op.startswith("<") and op != "<>")
                or (amp_after and not amp_before and re.fullmatch(r"\d+-?|-", word))):
            continue
        out.append(_dequote(word))
    return out


def _resolve(raw: str, cwd: str | None) -> tuple[str | None, str | None]:
    """(resolved path, None) or (None, reason) when it cannot be resolved."""
    if raw.startswith("<unresolvable"):
        # internal sentinels from the tool-specific target extractors —
        # checked BEFORE trimming so their angle brackets survive
        return None, raw.strip("<>")
    if any(q in raw for q in "\"'`") or _STAND_IN.search(raw) or _OPEN in raw:
        # checked BEFORE trimming: trimming first laundered `"$D"/workspace/x`
        # into `/workspace/x` and allowed it (origin 2026-10-07). A quoted or
        # escaped special character (a lex stand-in: `my\ file`, `"$D"`) is
        # refused the same way; an escaped plain one is already itself.
        return None, (f"target '{raw}' holds a quoted, escaped or substituted "
                      "character the guard does not interpret — write the path plainly")
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
    if not raw.startswith(os.sep):
        if cwd is None:
            return None, (f"relative target '{raw}' follows a cd the guard could "
                          "not resolve")
        raw = os.path.join(cwd, raw)
    return os.path.realpath(raw), None


def _paths(raw: str, cwd: str | None) -> tuple[list[str], str | None]:
    """Every path RAW names: each brace alternative, and for a glob each match
    as well as the pattern itself. Origin 2026-10-07: `mkdir {/workspace/a,
    /outside/b}` resolved as ONE path under /workspace, and `rm -rf /tmp/l*/x`
    was checked as text, not through the symlink /tmp/l* matches."""
    words, out = [raw], []
    while words:
        word = words.pop()
        m = re.search(r"\{([^{},]*(?:,[^{},]*)+)\}", word)       # innermost list
        if m:
            words += [word[:m.start()] + alt + word[m.end():] for alt in m.group(1).split(",")]
            if len(words) + len(out) > 256:
                return [], f"brace expansion of '{raw}' is too large to check"
            continue
        path, why = _resolve(word, cwd)
        if path is None:
            return [], why
        if any(c in path for c in "*?["):
            if ".." in word.split("/"):
                return [], f"a glob with '..' in '{raw}' cannot be resolved"
            matches = list(itertools.islice(glob.iglob(path), 10001))
            if len(matches) > 10000:
                return [], f"glob '{raw}' matches too many paths to check"
            out += [os.path.realpath(p) for p in matches]
        out.append(path)
    return out, None


def _runner_cwd(prefix: list[str], cwd: str | None) -> str | None:
    """Where a runner starts its command: `env -C DIR` / `sudo -D DIR` (or
    `--chdir`); unknown after a login (`sudo -i`, `su -`) or a clustered form.
    Origin 2026-10-07: `env -C /outside mkdir x` resolved x against the cwd."""
    runner = ""
    for i, t in enumerate(prefix):
        b = _normalize(t).split("/")[-1]
        letter = {"env": "C", "sudo": "D"}.get(runner, "")
        m = re.fullmatch(rf"-{letter}(.*)|--chdir(?:=(.+))?", t) if letter else None
        if b in _RUNNERS:
            runner = b
        elif m:
            d = m.group(1) or m.group(2) or (prefix[i + 1:i + 2] or [""])[0]
            cwd = _resolve(d, cwd)[0] if d else None
        elif (letter and re.fullmatch(rf"-\w*{letter}\w*", t)
              or runner == "sudo" and re.fullmatch(r"-\w*i\w*|--login", t)
              or runner == "su" and t in ("-", "-l", "--login")):
            cwd = None
    return cwd


def _write_targets(segment: str, tokens: list[str], verb: str | None, verb_idx: int,
                   cwd: str | None) -> list[tuple[str, str | None]]:
    """(raw target, directory it resolves against): the command's operands
    against its runner's directory, redirections against the shell's."""
    rcwd = _runner_cwd(tokens[:verb_idx], cwd) if verb_idx > 0 else cwd
    return ([(t, rcwd) for t in class_b_targets(verb, tokens, verb_idx)]
            + [(t, cwd) for t in redirect_targets(segment)])


def class_b_verdict(segment: str, tokens: list[str], verb: str | None, verb_idx: int,
                    cwd: str | None, roots: tuple[str, ...],
                    allowlist: list[str] | None) -> dict | None:
    """Refusal dict for a CLASS B violation, or None.

    ``allowlist`` is None when it could not be loaded — fail closed: any
    out-of-root target is refused as ``allowlist_unavailable`` rather than
    guessed at.
    """
    for raw, base in _write_targets(segment, tokens, verb, verb_idx, cwd):
        paths, why = _paths(raw, base)
        if why:
            return {"code": "unresolvable_target", "tool": verb or "redirection",
                    "detail": f"write target '{raw}' cannot be resolved: {why}. "
                              "The guard does not fail open on ambiguity."}
        for path in paths:
            if path == "/dev/null" or _inside(path, roots):
                continue  # /dev/null: discard device — a deliberate carve-out
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


def _link_verdict(segment: str, tokens: list[str], verb: str | None, verb_idx: int,
                  cwd: str | None, links: set[str]) -> dict | None:
    """Refuse a target reached through a link made earlier in the SAME command,
    then record this command's own links. realpath sees a link only once it
    exists: `ln -s /outside /tmp/l && rm -rf /tmp/l/x` resolved inside /tmp
    (origin 2026-10-07). Later commands are covered by realpath itself."""
    tool = (verb or "").split("/")[-1]
    if not links and tool not in ("ln", "cp"):
        return None
    paths = [p for raw, base in _write_targets(segment, tokens, verb, verb_idx, cwd)
             for p in _paths(raw, base)[0]]
    hit = next((p for p in paths for k in links if p == k or p.startswith(k + os.sep)), None)
    if tool == "ln" or tool == "cp" and re.search(r"(?<!\S)(-[^-\s]*s|--sym)", " ".join(tokens)):
        links.update(paths)
    return hit and {"code": "unresolvable_target", "tool": verb,
                    "detail": f"write target '{hit}' passes through a link created earlier "
                              "in this command; the guard cannot see where it points yet."}


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

# Separators, with the two shell_scan.SEPARATORS does not model: a lone `&`
# (background) ends a command as `;` does — origin 2026-10-07: `sleep 1 & mkdir
# /outside` hid mkdir behind verb `sleep` — and `>|` (rewritten to `> ` before
# splitting, or its `|` would split off the redirect target).
_SPLIT = re.compile(rf"({SEPARATORS.pattern}|(?<![<>&])&(?![>&]))")


def _groups(text: str, bodies: list[str]) -> str:
    """TEXT with each outermost `(...)` — subshell, `$(...)`, `<(...)`, `>(...)`,
    `((...))` — and `` `...` `` cut out to a numbered placeholder, plus the
    bodies, each scanned as commands of its own where it runs. Origin
    2026-10-07: `x=$(rm -rf /outside)`, `echo "$(mkdir /outside)"` and
    `> >(tee /outside)` hid their verb inside a word; `(cd /workspace && ls);
    touch f` let the subshell's cd leak to `f`. An unbalanced bracket (a case
    pattern's `)`) is left as text. BODIES is the scan's one list, so a
    placeholder means the same body wherever its text travels (find -exec)."""
    match, opened = {}, []
    for i, c in enumerate(text):
        if c == "(":
            opened.append(i)
        elif c == ")" and opened:
            match[opened.pop()] = i
    out, i = [], 0
    while i < len(text):
        c = text[i]
        j = match.get(i, -1) if c == "(" else text.find("`", i + 1) if c == "`" else -1
        if j < 0:
            out.append(c)
            i += 1
            continue
        bodies.append(text[i + 1:j])
        out.append(("$" if c == "`" else "") + f"{_OPEN}{len(bodies) - 1}{_CLOSE}")
        i = j + 1
    return "".join(out)


def _find_exec(args: list[str], cwd: str | None) -> list[tuple[str, str | None]]:
    """(command text, cwd) for what `find` runs: `-delete` is `rm START...`,
    `-exec CMD {} ;` is CMD with {} as each START (`-execdir` runs in it).
    Origin 2026-10-07: `find /outside -delete` and `find . -exec cp {}
    /outside ';'` hid the write behind verb `find`."""
    i0 = 0
    while i0 < len(args) and re.fullmatch(r"-[HLP]|-O\d*|-D", args[i0]):
        i0 += 1 + (args[i0] == "-D")                  # find -L /x: options first
    k = next((i for i in range(i0, len(args)) if args[i][:1] in "-(!"), len(args))
    starts, out = args[i0:k] or ["."], []
    if "-delete" in args:
        out.append(("rm " + " ".join(starts), cwd))
    out += [("touch " + args[i + 1], cwd) for i, a in enumerate(args[:-1])
            if a in ("-fprint", "-fprint0", "-fprintf", "-fls")]
    for i, a in enumerate(args):
        if a in ("-exec", "-execdir", "-ok", "-okdir"):
            end = next((j for j in range(i + 1, len(args))
                        if _normalize(args[j]) in (";", "+", chr(0xE03B))), len(args))
            for st in starts:
                run_in = _resolve(st, cwd)[0] if a.endswith("dir") else cwd
                out.append((" ".join(args[i + 1:end]).replace("{}", st), run_in))
    return out


def _scan(text: str, cwd: str | None, ctx: dict) -> None:
    """Scan lexed TEXT into ctx["a"] / ctx["b"] (the FIRST verdict of each
    class). Cut-out groups are scanned where they occur with the cwd of that
    moment, so a subshell's `cd` never leaks out; a `cd`/`pushd` that is a
    pipeline stage or backgrounded runs in a subshell too, and is ignored."""
    roots, allowlist = ctx["roots"], ctx["allowlist"]
    ctx["depth"] = ctx.get("depth", 0) + 1
    if ctx["depth"] > 40:
        ctx["b"] = ctx.get("b") or {"code": "unresolvable_target", "tool": "nesting",
                                    "detail": "commands nested over 40 deep are not "
                                              "scanned; the guard does not fail open."}
        return
    text = _groups(text.replace(">|", "> "), ctx["groups"])
    parts = _SPLIT.split(text)
    vcwd: str | None = cwd
    dirs: list[str | None] = []   # pushd's stack
    for k in range(0, len(parts), 2):
        seg = parts[k].strip()
        for g in re.findall(rf"{_OPEN}(\d+){_CLOSE}", seg):
            _scan(ctx["groups"][int(g)], vcwd, ctx)
        if not seg:
            continue
        tokens = _argv(seg)
        verb, verb_idx = verb_of(tokens)
        base = (verb or "").split("/")[-1]
        subshell = "|" in parts[k - 1:k] + parts[k + 1:k + 2] or parts[k + 1:k + 2] == ["&"]
        if base in ("cd", "pushd", "popd") and not subshell:
            # an unresolvable cd (`cd $X`, `cd -`, `pushd +1`, a CDPATH lookup)
            # poisons relative targets rather than leaving them resolved
            # against the old directory
            args = tokens[verb_idx + 1:]
            pos = _getopt(args)[0]
            if base == "pushd":
                dirs.append(vcwd)
            to = pos[0] if len(pos) == 1 else "~" if not pos and base == "cd" else ""
            if base == "popd":
                vcwd = dirs.pop() if dirs else None
            elif ("-" in args or not to or to[0] in "+-"
                  or ctx["cdpath"] and not to.startswith(("/", ".", "~"))):
                vcwd = None
            else:
                vcwd = _resolve(to, vcwd)[0]
        if base == "find":
            for body, run_in in _find_exec(tokens[verb_idx + 1:], vcwd):
                _scan(body, run_in, ctx)
        # A shell's -c string and the heredoc it reads are commands. Origin
        # 2026-10-07: both were blanked as data, so `sudo sh -c 'echo x >
        # /etc/f'` and `bash <<EOF` + `mkdir /outside` were never scanned.
        shell = [j for j, t in enumerate(tokens[:verb_idx + 1])
                 if _normalize(t).split("/")[-1] in _SHELLS]
        flag = next((j for j in range(shell[0] + 1, len(tokens))
                     if re.fullmatch(r"-\w*c", tokens[j])), None) if shell else None
        script = next((t for t in tokens[flag + 1:] if t[:1] != "-"), "") if flag else ""
        for cmd in filter(None, [script] + re.findall(r"<<<\s*(\S+)", seg) * bool(shell)):
            _scan(lex(_decode(_dequote(cmd)), keep_quoted=True), vcwd, ctx)
        for tag in re.findall(rf"<<-?([{chr(0xE080)}-{chr(0xE0FF)}])", seg) if shell else ():
            n = ord(tag) - 0xE080                         # lex's heredoc tag (capped)
            for body in ctx["bodies"][n:n + 1] if n < 127 else ctx["bodies"][n:]:
                _scan(lex(body, keep_quoted=True, bodies=ctx["bodies"]), vcwd, ctx)
        a = class_a_verdict(tokens, verb)
        if a is not None and ctx.get("a") is None:
            ctx["a"] = a
        b = class_b_verdict(seg, tokens, verb, verb_idx, vcwd, roots, allowlist)
        b = b or _link_verdict(seg, tokens, verb, verb_idx, vcwd, ctx["links"])
        if b is not None and ctx.get("b") is None:
            ctx["b"] = b
    ctx["depth"] -= 1


def scan_command(command: str, cwd: str | None = None,
                 allowlist_path: Path | None = None) -> dict:
    """One refusal dict (code/detail/tool) or an allowed dict."""
    cwd = os.path.realpath(cwd or os.getcwd())
    ctx = {"roots": containment_roots(), "links": set(), "bodies": [], "groups": [],
           "allowlist": load_allowlist(allowlist_path or ALLOWLIST_PATH),
           "cdpath": "CDPATH" in command or bool(os.environ.get("CDPATH"))}
    _scan(lex(command, keep_quoted=True, bodies=ctx["bodies"]), cwd, ctx)
    return ctx.get("a") or ctx.get("b") or {"verdict": "allowed"}


def check_path(path: str, cwd: str | None = None,
               allowlist_path: Path | None = None) -> dict:
    """Refusal dict for a file path outside the containment set, or allowed.

    Serves the Write|Edit surfaces (Claude Write|Edit hook, opencode
    write/edit plugin interception, codex file_path tool_input) with the SAME
    rules as the command scanner: realpath'd containment roots, the operator
    allowlist (fail-closed when unreadable), and the /dev/null carve-out.
    ``~``/``$HOME`` expand; a quoted, variable-tainted, or remote target is
    refused as ``unresolvable_target`` — never guessed at.
    """
    resolved, why = _resolve(path, cwd or os.getcwd())
    if resolved is None:
        return {"code": "unresolvable_target", "tool": "check_path",
                "detail": f"path '{path}' cannot be resolved: {why}. "
                          "The guard does not fail open on ambiguity."}
    if resolved == "/dev/null":
        return {"verdict": "allowed"}  # discard device — same carve-out as CLASS B
    if _inside(resolved, containment_roots()):
        return {"verdict": "allowed"}
    allowlist = load_allowlist(allowlist_path or ALLOWLIST_PATH)
    if allowlist is None:
        return {"code": "allowlist_unavailable", "tool": "check_path",
                "detail": f"path '{resolved}' is outside the containment root but "
                          "the operator allowlist could not be read — refusing "
                          "until it parses."}
    if any(resolved == p or resolved.startswith(p + os.sep) for p in allowlist):
        return {"verdict": "allowed"}
    return {"code": "write_outside_containment_root", "tool": "check_path",
            "detail": f"path '{resolved}' is outside the containment root. Allowed: "
                      "/mnt/raid0/llm/**, /workspace/**, /tmp/opencode/**, "
                      "~/.claude/**, ~/.codex/**, bare /tmp/**. Operators may add "
                      "this path prefix to scripts/hooks/filesystem_allowlist.yaml "
                      "(or set EPYC_FS_ACK for a one-off)."}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _parse_args(argv: list[str]) -> dict:
    """(opts) from argv. Unknown flags are an error (refuse, never guess)."""
    opts: dict = {"cwd": None, "allowlist": None}
    i = 0
    while i < len(argv):
        if argv[i] == "--command" and i + 1 < len(argv):
            opts["command"] = argv[i + 1]
            i += 2
        elif argv[i] == "--check-path" and i + 1 < len(argv):
            opts["check_path"] = argv[i + 1]
            i += 2
        elif argv[i] == "--cwd" and i + 1 < len(argv):
            opts["cwd"] = argv[i + 1]
            i += 2
        elif argv[i] == "--allowlist" and i + 1 < len(argv):
            opts["allowlist"] = argv[i + 1]
            i += 2
        elif argv[i] in ("--dump-rules",):
            opts["dump_rules"] = True
            i += 1
        else:
            opts["bad_arg"] = argv[i]
            break
    return opts


def _refusal_exit(verdict: dict) -> int:
    """Emit a refusal exactly like the pre-existing protocol: human message on
    stderr, JSON verdict on stdout, exit 2."""
    print(verdict.get("detail", "refused"), file=sys.stderr)
    print(json.dumps(verdict))
    return 2


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--help" in argv or "-h" in argv:
        print(__doc__.split("EXIT PROTOCOL")[0].split('"""')[0].strip())
        return 0
    try:
        if "--dump-rules" in argv:
            opts = _parse_args([a for a in argv if a != "--dump-rules"])
            if opts.get("bad_arg"):
                print(f"error: unknown argument '{opts['bad_arg']}'", file=sys.stderr)
                return 2
            print(json.dumps(rules_dump(), indent=2))
            return 0
        opts = _parse_args(argv)
        if opts.get("bad_arg"):
            print(f"error: unknown argument '{opts['bad_arg']}'", file=sys.stderr)
            return 2
        if opts.get("allowlist"):
            global ALLOWLIST_PATH
            ALLOWLIST_PATH = Path(opts["allowlist"])
        cmd = opts.get("command")
        path = opts.get("check_path")
        cwd = opts.get("cwd")
        ack = os.environ.get(ACK_ENV, "").strip()
        if ack:
            print(json.dumps({"verdict": "allowed", "ack": ack,
                              "note": "operator ack EPYC_FS_ACK present in the hook "
                                      "environment; call allowed and recorded"}))
            return 0
        if cmd is not None:
            if not cmd.strip():
                print("error: empty command — refusing to emit a verdict", file=sys.stderr)
                return 2
            verdict = scan_command(cmd, cwd=cwd)
            if verdict.get("verdict") == "allowed":
                return 0
            return _refusal_exit(verdict)
        if path is not None:
            if not path.strip():
                print("error: empty path — refusing to emit a verdict", file=sys.stderr)
                return 2
            verdict = check_path(path, cwd=cwd)
            if verdict.get("verdict") == "allowed":
                return 0
            return _refusal_exit(verdict)
        # No --command / --check-path: the PreToolUse stdin shape, or a bare
        # command string (the historical fallback), or nothing (must refuse).
        data = sys.stdin.read()
        if not data.strip():
            print("error: no command given (--command <cmd>, --check-path <path>, "
                  "or PreToolUse JSON on stdin) — refusing to emit a verdict "
                  "(empty input must never produce a clean scan)",
                  file=sys.stderr)
            return 2
        try:
            payload = json.loads(data)
            if isinstance(payload, dict) and isinstance(payload.get("tool_input"), dict):
                cmd = payload["tool_input"].get("command")
                path = payload["tool_input"].get("file_path")
                if isinstance(cmd, str) and cmd.strip():
                    verdict = scan_command(cmd, cwd=cwd)
                    if verdict.get("verdict") == "allowed":
                        return 0
                    return _refusal_exit(verdict)
                if isinstance(path, str) and path.strip():
                    verdict = check_path(path, cwd=cwd)
                    if verdict.get("verdict") == "allowed":
                        return 0
                    return _refusal_exit(verdict)
        except json.JSONDecodeError:
            pass
        if isinstance(data, str) and data.strip():
            verdict = scan_command(data, cwd=cwd)
            if verdict.get("verdict") == "allowed":
                return 0
            return _refusal_exit(verdict)
        print("error: no command could be read from stdin — refusing to emit a "
              "verdict", file=sys.stderr)
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

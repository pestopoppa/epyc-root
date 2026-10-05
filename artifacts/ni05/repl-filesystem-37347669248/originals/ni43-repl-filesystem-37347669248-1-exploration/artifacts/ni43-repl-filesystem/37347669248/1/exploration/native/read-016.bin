"""Model task-root override for the BEP-2 / DCP-6 falsification harness.

`ORCHESTRATOR_EDIT_ROOT`, when set to an existing directory, redirects MODEL-FACING
filesystem surfaces — file write/read/peek/grep/list/file_info, ``run_shell`` cwd,
``code_search``/ColGREP root, the batch-edit repo root, and DCP file discovery — to a
scratch task repo, so a BEP/DCP A/B never mutates the orchestrator's own checkout.

CONTROL-PLANE paths stay on the real ``project_root`` (registry, model/tool config,
sessions, orchestration logs, patch ledgers, procedures/checkpoints, benchmarks) — those
keep calling the existing ``_get_project_root()`` copies, NOT these accessors.

Default (env unset / not a dir) == today's behavior exactly: ``get_task_root()`` returns
``project_root`` and ``resolve_task_path`` resolves relative paths against the process cwd,
so production is unchanged. See ``data/bep_sandbox/task_root_surface_audit.md`` (Phase 0) and
``handoffs/active/bep-dcp-falsification-harness.md``.
"""
from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

ENV_VAR = "ORCHESTRATOR_EDIT_ROOT"

# ── Per-request task scope (INF-78 OAB-1) ────────────────────────────────────
#
# ``ChatRequest.task_root`` / ``edit_mode`` / ``read_roots`` scope ONE /chat request to a
# caller-named directory (the AutoKernel loop runs one lane worktree per candidate). The API
# serves concurrent requests per worker, so the scope can never be process-wide state (an env
# var or a module attribute would race; compare TD-21.33c, c347600e). It lives behind a
# ContextVar, the same carrier shape as the AP-54 knowledge fence: ``asyncio`` tasks and
# ``asyncio.to_thread`` copy the context, and the two ThreadPoolExecutor hops on the tool path
# (``tools.base.with_timeout``, REPL parallel dispatch) submit through
# ``knowledge_fence.run_in_context``, so every tool call of the request sees it.
#
# Precedence: request scope > ``$ORCHESTRATOR_EDIT_ROOT`` > project root. With no scope set,
# every accessor below behaves exactly as before (production unchanged).
#
# Semantics under a scope:
# * reads (peek/grep/list_dir/file_info/peek_grep, read-only registry tools, run_shell path
#   arguments) are confined to ``root`` plus the explicit ``read_roots``;
# * writes: ``edit_mode="none"`` refuses every write; ``edit_mode="direct"`` lets
#   ``file_write_safe`` write inside ``root`` (never inside a read root) with no approval queue
#   and no ``.bak`` litter. The only other writers allowed under ``direct`` target the same
#   root through the same check (``extract_figure(output_path=...)``) or are flag-gated
#   whole-edit paths that already apply into the task root (batch-edit patchsets,
#   ``force_mode="edit"``). Everything else — log_append, the patch queue, shell writers,
#   run_python_code, SCRIPT, control-plane mutators, non-allowlisted registry tools — is
#   refused in both modes.

EDIT_MODE_NONE = "none"
EDIT_MODE_DIRECT = "direct"
EDIT_MODES = (EDIT_MODE_NONE, EDIT_MODE_DIRECT)
SCOPE_DENY_PREFIX = "TASK SCOPE"


@dataclass(frozen=True)
class TaskScope:
    """One request's task scope. ``root`` and ``read_roots`` are realpaths, no trailing '/'."""

    root: str
    edit_mode: str = EDIT_MODE_NONE
    read_roots: tuple[str, ...] = ()

    @property
    def can_write(self) -> bool:
        return self.edit_mode == EDIT_MODE_DIRECT

    @staticmethod
    def _under(resolved: str, base: str) -> bool:
        return resolved == base or resolved.startswith(base.rstrip("/") + "/")

    def read_denial(self, resolved: str) -> str | None:
        """None when ``resolved`` (a realpath) is inside root or a read root."""
        for base in (self.root, *self.read_roots):
            if self._under(resolved, base):
                return None
        return (
            f"{SCOPE_DENY_PREFIX}: {resolved} is outside task_root {self.root}"
            + (f" and read_roots {list(self.read_roots)}" if self.read_roots else "")
        )

    def write_denial(self, resolved: str) -> str | None:
        """None when this request may write ``resolved`` (a realpath)."""
        if not self.can_write:
            return f"{SCOPE_DENY_PREFIX}: edit_mode='none' — this request cannot write files"
        if not self._under(resolved, self.root) or resolved == self.root:
            return f"{SCOPE_DENY_PREFIX}: write to {resolved} refused — outside task_root {self.root}"
        return None

    def snapshot(self) -> dict:
        return {"task_root": self.root, "edit_mode": self.edit_mode,
                "read_roots": list(self.read_roots)}


_scope: ContextVar[TaskScope | None] = ContextVar("orchestrator_task_scope", default=None)


def _allowed_prefixes() -> list[str]:
    """Prefixes a scope root must sit strictly under (the REPL's allowed file paths)."""
    try:
        from src.config import get_config

        llm_root = str(get_config().paths.llm_root)
    except Exception:
        llm_root = os.environ.get("ORCHESTRATOR_PATHS_LLM_ROOT", "/mnt/raid0/llm")
    out = []
    for p in (llm_root, "/tmp"):
        rp = os.path.realpath(p)
        out.append(rp)
    return out


# F6 (review fix, INF-78): the frozen production kernel trees and the kernel/model stores are
# never a scope directory, but not symmetrically:
#   - as task_root (writable_root=True): NEVER. A scope's write root must never resolve into a
#     frozen tree, the kernel store, or the model store — there is no legitimate case for a
#     scoped agent run to write a kernel binary or a model file, and the frozen trees are
#     "NEVER modified, rebased, built, or committed to unless the operator EXPLICITLY
#     authorizes it" (CLAUDE.md) — a task_root is exactly a write scope.
#   - as read_roots (writable_root=False): the three FROZEN kernel SOURCE trees plus
#     kernels/ are denied outright — inspecting a frozen tree or the serving kernel store goes
#     through the sanctioned verify_*/agent-file surfaces, not an ad-hoc scoped read_root, and
#     read access here would let a scoped run grep the actual frozen patches/binaries a task_root
#     run has no reason to see. models/ is the one exception: it is ALLOWED as a read_root,
#     because a scoped run (e.g. an AutoKernel candidate comparing tokenizer/config against a
#     reference model) legitimately needs to READ a GGUF/tokenizer under models/ — it just may
#     never be pointed there as its WRITE root (task_root), which stays denied above.
_FROZEN_KERNEL_TREES = (
    "/mnt/raid0/llm/llama.cpp",
    "/mnt/raid0/llm/whisper.cpp",
    "/mnt/raid0/llm/qwentts.cpp",
)
_DENY_AS_TASK_ROOT = _FROZEN_KERNEL_TREES + ("/mnt/raid0/llm/kernels", "/mnt/raid0/llm/models")
_DENY_AS_READ_ROOT = _FROZEN_KERNEL_TREES + ("/mnt/raid0/llm/kernels",)


def validate_scope_dir(path: str, *, field: str = "task_root", writable_root: bool = True) -> str:
    """Validate a caller-supplied scope directory and return its realpath.

    Rules: absolute; an existing directory; strictly below the llm root or /tmp (never one of
    those roots itself). A ``task_root`` (``writable_root``) additionally may not contain the
    orchestrator's own project root, so a scoped request can never be pointed at the control
    plane. Neither a ``task_root`` nor a ``read_roots`` entry may resolve into a frozen
    production kernel tree or the kernel store; a ``task_root`` additionally may not resolve
    into the model store (``read_roots`` may — see ``_DENY_AS_READ_ROOT`` above). Raises
    ``ValueError`` (pydantic turns it into a 422).
    """
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"{field} must be a non-empty absolute path")
    raw = path.strip()
    if not os.path.isabs(raw):
        raise ValueError(f"{field} must be absolute, got {raw!r}")
    resolved = os.path.realpath(raw)
    if not os.path.isdir(resolved):
        raise ValueError(f"{field} {raw!r} is not an existing directory")
    prefixes = _allowed_prefixes()
    if not any(resolved.startswith(p.rstrip("/") + "/") for p in prefixes):
        raise ValueError(f"{field} {resolved!r} must be strictly below one of {prefixes}")
    if writable_root:
        project = os.path.realpath(str(_project_root()))
        if project == resolved or project.startswith(resolved.rstrip("/") + "/"):
            raise ValueError(
                f"{field} {resolved!r} contains the orchestrator project root {project!r}"
            )
    for denied in (_DENY_AS_TASK_ROOT if writable_root else _DENY_AS_READ_ROOT):
        d = os.path.realpath(denied)
        if (resolved == d or resolved.startswith(d.rstrip("/") + "/")
                or d.startswith(resolved.rstrip("/") + "/")):
            raise ValueError(
                f"{field} {resolved!r} is a frozen production kernel tree or model/kernel "
                f"store ({d!r}); never a {'task_root' if writable_root else 'read_root'}"
            )
    return resolved


def begin_request_scope(
    task_root: str | None,
    edit_mode: str = EDIT_MODE_NONE,
    read_roots: list[str] | tuple[str, ...] | None = None,
) -> TaskScope | None:
    """Install this request's scope. ``task_root=None`` installs nothing (production)."""
    if task_root is None:
        _scope.set(None)
        return None
    if edit_mode not in EDIT_MODES:
        raise ValueError(f"edit_mode must be one of {EDIT_MODES}, got {edit_mode!r}")
    root = validate_scope_dir(task_root)
    reads = tuple(
        dict.fromkeys(
            validate_scope_dir(r, field="read_roots", writable_root=False)
            for r in (read_roots or ())
        )
    )
    scope = TaskScope(root=root, edit_mode=edit_mode, read_roots=reads)
    _scope.set(scope)
    return scope


def clear_request_scope() -> None:
    """Remove the scope. Call in a ``finally`` so it never outlives its request."""
    _scope.set(None)


def request_scope() -> TaskScope | None:
    """This request's scope, or None (production / env-only BEP mode)."""
    return _scope.get()


def scope_refusal(tool: str) -> str | None:
    """Refusal text for a tool that is unavailable under ANY request scope, else None."""
    scope = _scope.get()
    if scope is None:
        return None
    return (
        f"{SCOPE_DENY_PREFIX}: {tool} is not available in a task_root-scoped request "
        f"(task_root={scope.root}, edit_mode={scope.edit_mode})"
    )


def _project_root() -> Path:
    """The real orchestrator project root (control-plane anchor)."""
    try:
        from src.config import get_config

        return Path(get_config().paths.project_root)
    except Exception:
        # Mirror file_mutation/external_access fallback so this never hard-fails.
        return Path(os.getcwd())


def task_root_active() -> bool:
    """True iff this request carries a task scope, or ORCHESTRATOR_EDIT_ROOT is set to an
    existing directory."""
    if _scope.get() is not None:
        return True
    v = os.environ.get(ENV_VAR, "").strip()
    return bool(v) and Path(v).is_dir()


def get_task_root() -> Path:
    """Model task-root: the request scope's root (``ChatRequest.task_root``) if set, else
    ``$ORCHESTRATOR_EDIT_ROOT`` if set + an existing dir, else ``project_root``. Read live (no
    caching) so an A/B can flip it via env across restarts and tests can monkeypatch it."""
    scope = _scope.get()
    if scope is not None:
        return Path(scope.root)
    v = os.environ.get(ENV_VAR, "").strip()
    if v:
        p = Path(v)
        if p.is_dir():
            return p
    return _project_root()


def resolve_task_path(path: str) -> str:
    """Resolve a model-supplied path to a realpath string.

    When the task-root is active, a RELATIVE path resolves against the task-root (so the model
    inspecting/editing ``cart.py`` hits the scratch repo, not the orchestrator's cwd). Absolute
    paths pass through unchanged. When inactive, behaves exactly like ``os.path.realpath(path)``
    (today's behavior).
    """
    p = Path(path)
    if not p.is_absolute() and task_root_active():
        return os.path.realpath(str(get_task_root() / path))
    return os.path.realpath(path)


# ── run_shell under a request scope ──────────────────────────────────────────
#
# ``run_shell`` runs WITHOUT a shell (``shlex.split`` + ``subprocess.run``), so redirection
# tokens are literal arguments and cannot write. The allowlisted commands that CAN write, or run
# arbitrary code, are refused here; every path-like argument must sit inside the scope's read
# set (task_root + read_roots). Shell writes are refused in BOTH edit modes: under
# ``edit_mode="direct"`` the one write surface is ``file_write_safe``.

_FIND_WRITE_ACTIONS = frozenset({
    "-delete", "-exec", "-execdir", "-ok", "-okdir",
    "-fprint", "-fprint0", "-fprintf", "-fls",
})


def check_shell_scope(parts: list[str], cwd: str) -> str | None:
    """Refusal text for a ``run_shell`` argv under this request's scope, else None."""
    scope = _scope.get()
    if scope is None or not parts:
        return None
    from src.repl_environment import _fence_rules as _rules
    from src.repl_environment.knowledge_fence import (
        _AWK_IO_RE,
        _script_program,
        _sed_does_io,
    )

    base = parts[0].split("/")[-1]
    args = parts[1:]

    def _refuse(why: str) -> str:
        return f"{SCOPE_DENY_PREFIX}: run_shell {base} refused — {why}"

    def _short_cluster_has(a: str, letter: str) -> bool:
        """True for a short-option cluster (``-xyz``, never ``--long``) containing ``letter``."""
        return a.startswith("-") and not a.startswith("--") and letter in a[1:]

    # F1(d): generic — any command's ``--output``/``--out`` flag writes a file, and the
    # per-argument confinement loop below only catches an EXISTING path, so a target that does
    # not exist yet (the normal case for an output file) would sail through unchecked.
    if any(
        a in {"--output", "--out"} or a.startswith("--output=") or a.startswith("--out=")
        for a in args
    ):
        return _refuse("--output/--out writes a file")

    if base.startswith(_rules.PYTHON_EXECUTABLE_PREFIXES):
        return _refuse("arbitrary code execution is not available in a scoped request")
    if base == "sed":
        if any(a.startswith("--in-place") or _short_cluster_has(a, "i") for a in args):
            return _refuse("in-place editing writes files; use file_write_safe")
        program = _script_program(base, args)
        if program is not None and _sed_does_io(program):
            return _refuse("program performs file or command I/O")
        # F1(b): a short cluster such as ``-nf`` bundles ``-f`` with other flags; the exact
        # ``-f``/``--file`` match above misses it.
        if any(a in {"-f", "--file"} or a.startswith("--file=") or _short_cluster_has(a, "f")
               for a in args):
            return _refuse("-f program files cannot be inspected")
    if base in {"awk", "gawk", "mawk", "nawk"}:
        program = _script_program(base, args)
        if program is not None and _AWK_IO_RE.search(program):
            return _refuse("program performs file or command I/O")
        if any(a in {"-f", "--file"} or a.startswith("--file=") or _short_cluster_has(a, "f")
               for a in args):
            return _refuse("-f program files cannot be inspected")
    if base == "find" and any(a in _FIND_WRITE_ACTIONS for a in args):
        return _refuse("-delete/-exec/-fprint actions can write or run commands")
    # F1(a): ``-ro`` (or any other short cluster containing ``o``) bundles ``-o`` with other
    # flags; the previous ``a.startswith("-o")`` check missed a cluster where ``o`` is not the
    # first letter, e.g. ``sort -ro out.txt kernel.c``.
    if base == "sort" and any(a == "-o" or a.startswith("--output") or _short_cluster_has(a, "o")
                              for a in args):
        return _refuse("-o/--output writes a file")
    if base == "uniq" and len([a for a in args if not a.startswith("-")]) >= 2:
        return _refuse("a second positional is an output file")
    if base == "date" and any(a in {"-s"} or a.startswith("--set") for a in args):
        return _refuse("setting the clock is not a read")
    # F4: dereferencing a symlink can walk outside the scope's read set even though the link
    # itself resolves inside it (the confinement loop below realpaths each ARGUMENT, not
    # every path find/du/ls/grep may descend into while following links).
    if base in {"find", "du", "ls"} and any(
        a in {"-L", "-H"} or a.startswith("--dereference") or
        _short_cluster_has(a, "L") or _short_cluster_has(a, "H")
        for a in args
    ):
        return _refuse("dereferencing symlinks can walk outside the scope")
    if base == "grep" and any(
        a == "-R" or a.startswith("--dereference-recursive") or _short_cluster_has(a, "R")
        for a in args
    ):
        return _refuse("dereferencing symlinks can walk outside the scope")
    if base == "git":
        # F1(c): any arg starting with --output or -o writes a file (the generic F1(d) check
        # above only catches the exact --output/--out spellings; git also takes forms like
        # ``-oFILE``). ``git branch`` mutates refs. In a lane worktree ``.git`` is a gitdir
        # POINTER file, not a real repo — ``git branch``'s ref writes land in the SHARED clone
        # every lane worktree points at, not in the scoped task_root.
        if any(a.startswith("--output") or (a.startswith("-o") and not a.startswith("--"))
               for a in args):
            return _refuse("--output/-o writes a file")
        subcommand = next((a for a in args if not a.startswith("-")), None)
        if subcommand == "branch":
            idx = args.index("branch")
            rest = args[idx + 1:]
            non_flag = [a for a in rest if not a.startswith("-")]
            _branch_write_flags = {"-d", "-D", "-m", "-M", "-c", "-C", "-u"}
            if non_flag or any(
                a in _branch_write_flags or a.startswith("--set-upstream") for a in rest
            ):
                return _refuse(
                    "git branch can create/delete/rename/set-upstream a branch in the "
                    "SHARED clone (a lane worktree's .git is a gitdir pointer)"
                )

    # Confinement of reads: every argument that names an existing location must resolve
    # inside the scope's read set. Flag values (--foo=/path) count too.
    candidates = [a for a in args if not a.startswith("-")]
    candidates += [a.split("=", 1)[1] for a in args if a.startswith("--") and "=" in a]
    for value in candidates:
        if not value:
            continue
        joined = value if os.path.isabs(value) else os.path.join(cwd, value)
        if not os.path.lexists(joined):
            continue  # a pattern / program text / missing path: nothing to read there
        denial = scope.read_denial(os.path.realpath(joined))
        if denial is not None:
            return denial
    return scope.read_denial(os.path.realpath(cwd))


# ── registry tools (TOOL/CALL) under a request scope ─────────────────────────

_PATH_ARG_NAMES = ("path", "file_path", "directory", "dir", "root", "image_path", "pdf_path")


# Registry tools a scoped request may run. An explicit allowlist, because declared
# side_effects are neither complete (read_file declares none) nor trustworthy (compatibility
# stubs such as start_service declare "read_only"). Everything else is refused.
SCOPED_READ_ONLY_REGISTRY_TOOLS = frozenset({"read_file", "list_files", "search_files", "read_json"})


def check_registry_tool_scope(tool_name: str, kwargs: dict, side_effects=None) -> str | None:
    """Refusal text for a registry tool call under this request's scope, else None.

    Only the allowlisted read-only file tools run, and every path-like argument must
    resolve inside task_root + read_roots.
    """
    scope = _scope.get()
    if scope is None:
        return None
    if tool_name not in SCOPED_READ_ONLY_REGISTRY_TOOLS:
        return (
            f"{SCOPE_DENY_PREFIX}: tool {tool_name!r} is not on the scoped read-only allowlist "
            f"{sorted(SCOPED_READ_ONLY_REGISTRY_TOOLS)}; refused in a task_root-scoped request"
        )
    # The handlers open their path arguments RAW (relative to the process cwd), so each one is
    # rewritten IN PLACE to its resolved absolute path under the scope — the check and the
    # read then name the same file. ``kwargs`` is the dict ToolRegistry.invoke hands on.
    for name in _PATH_ARG_NAMES:
        v = kwargs.get(name)
        if isinstance(v, str) and v:
            resolved = resolve_task_path(v)
            denial = scope.read_denial(resolved)
            if denial is not None:
                return denial
            kwargs[name] = resolved
    for name in ("paths", "files"):
        v = kwargs.get(name)
        if isinstance(v, (list, tuple)):
            out = []
            for x in v:
                if isinstance(x, str) and x:
                    resolved = resolve_task_path(x)
                    denial = scope.read_denial(resolved)
                    if denial is not None:
                        return denial
                    out.append(resolved)
                else:
                    out.append(x)
            kwargs[name] = type(v)(out)
    pattern = kwargs.get("pattern")
    if isinstance(pattern, str) and (".." in pattern.split("/") or pattern.startswith("/")):
        return f"{SCOPE_DENY_PREFIX}: glob pattern {pattern!r} may not leave its directory"
    return None

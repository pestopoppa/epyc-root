#!/usr/bin/env python3
"""Privacy gate for dev-harness trace-derived outputs (F3-LB1).

epyc-root is a PUBLIC repository. Everything derived per session from Claude Code, Codex or
opencode transcripts is private: it lives only under PRIVATE_ROOT (default
/mnt/raid0/llm/private/dev-harness-traces, mode 0700, outside every git work tree). What may
be committed is an AGGREGATE (counts and rule text only) that passed both
``validate_aggregate`` here and the orchestrator's ``raw_trace_publish_preflight``.

Three guarantees this module enforces, so a caller cannot forget them:

* ``private_dir`` / ``private_write`` refuse any path inside a git work tree, inside the
  backup (cloud-llm-vault, claude-backups) or inside a harness's own store (~/.claude,
  ~/.codex, ~/.local/share/opencode); they create dirs 0700 and files 0600.
* ``validate_aggregate`` refuses a document carrying a per-session key (session/conversation
  ids, source paths, block hashes, content) or a non-numeric count leaf.
* ``publish_aggregate`` writes nothing into the repo unless the preflight exits 0.

The staged PII guard (scripts/hooks/pii_precommit.sh) blocks the other direction: a
transcript-shaped or per-session projection line staged by mistake.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
from pathlib import Path
from typing import Any

PRIVATE_ROOT = Path(os.environ.get("DEV_HARNESS_PRIVATE_ROOT", "/mnt/raid0/llm/private/dev-harness-traces"))
VAULT_ROOT = Path("/mnt/raid0/llm/cloud-llm-vault")
BACKUP_DIR = Path("/mnt/raid0/llm/claude-backups")
ORCHESTRATOR_ROOT = Path(os.environ.get("EPYC_ORCHESTRATOR_ROOT", "/workspace/repos/epyc-orchestrator"))
PREFLIGHT_REL = "scripts/datasets/raw_trace_publish_preflight.py"

AGGREGATE_SCHEMA = "dev-harness-aggregate.v1"
# Keys that only per-session (private) records carry. An aggregate containing any is refused.
FORBIDDEN_AGGREGATE_KEYS = frozenset({
    "session_id", "sessionid", "conversation_id", "gen_ai.conversation.id", "parent_conversation_id",
    "source_path", "source_line", "block_hashes", "content", "text", "message", "messages", "prompt",
    "command", "arguments", "output", "tool_call_id", "gen_ai.tool.call.id", "uuid", "cwd",
    "transcripts", "commit_shas",
})


class PrivacyError(RuntimeError):
    """A write or publish would break the privacy contract."""


def _protected_roots() -> list[Path]:
    home = Path(os.path.expanduser("~"))
    return [VAULT_ROOT, BACKUP_DIR, home / ".claude", home / ".codex", home / ".local/share/opencode"]


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve() if root.exists() else root)
        return True
    except ValueError:
        return False


def _git_work_tree(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def check_private_path(path: Path | str) -> Path:
    """Resolve ``path`` and refuse it unless it is a legitimate private output location."""
    p = Path(path).expanduser().resolve()
    for root in _protected_roots():
        if _inside(p, root):
            raise PrivacyError(f"refusing to write under protected store {root}: {p}")
    tree = _git_work_tree(p)
    if tree is not None:
        raise PrivacyError(f"refusing to write per-session output inside git work tree {tree}: {p}")
    return p


def private_dir(path: Path | str) -> Path:
    """Create (0700) and return a private directory; refuse non-private locations."""
    p = check_private_path(path)
    missing = [d for d in [p, *p.parents] if not d.exists()]
    for d in reversed(missing):          # every component WE create is 0700, not umask-default
        d.mkdir(mode=0o700, exist_ok=True)
        os.chmod(d, 0o700)
    os.chmod(p, 0o700)
    if p.stat().st_mode & 0o077:
        raise PrivacyError(f"{p} is group/other accessible")
    return p


def private_write(path: Path | str, text: str) -> Path:
    """Write ``text`` to a 0600 file under a private dir (atomic replace)."""
    p = check_private_path(path)
    private_dir(p.parent)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, p)
    return p


def hmac_key(root: Path | str | None = None) -> bytes:
    """The per-host block-hash key (32 random bytes, 0600, never committed, never logged)."""
    kdir = private_dir(Path(root or PRIVATE_ROOT) / "keys")
    kp = kdir / "block_hmac.key"
    if not kp.exists():
        fd = os.open(kp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(secrets.token_bytes(32))
    if kp.stat().st_mode & 0o077:
        raise PrivacyError(f"{kp} is group/other accessible")
    return kp.read_bytes()


def validate_aggregate(doc: Any) -> list[str]:
    """Return the list of violations (empty = publishable shape)."""
    errs: list[str] = []
    if not isinstance(doc, dict):
        return ["aggregate must be a JSON object"]
    if doc.get("schema") != AGGREGATE_SCHEMA:
        errs.append(f"schema must be {AGGREGATE_SCHEMA}")
    allowed_top = {"schema", "generated_at", "source", "counts", "rules", "notes", "spec"}
    for k in doc:
        if k not in allowed_top:
            errs.append(f"top-level key {k!r} not allowed (allowed: {sorted(allowed_top)})")
    for k in ("source", "notes", "generated_at", "spec"):
        if k in doc and not isinstance(doc[k], str):
            errs.append(f"{k} must be a string")
    rules = doc.get("rules", [])
    if not isinstance(rules, list) or not all(isinstance(r, str) for r in rules):
        errs.append("rules must be a list of strings (rule text only)")

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if str(k).lower() in FORBIDDEN_AGGREGATE_KEYS:
                    errs.append(f"{path}.{k}: per-session key not allowed in an aggregate")
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            errs.append(f"{path}: lists are not allowed under counts (use keyed counts)")
        elif isinstance(node, bool) or not isinstance(node, (int, float)):
            errs.append(f"{path}: count leaves must be numbers")

    walk(doc.get("counts", {}), "$.counts")
    return errs


def run_preflight(path: Path, report_path: Path, orchestrator_root: Path = ORCHESTRATOR_ROOT) -> int:
    """Run the orchestrator's raw_trace_publish_preflight on ``path``; returns its exit code."""
    py = orchestrator_root / ".venv/bin/python"
    exe = str(py) if py.exists() else "python3"
    proc = subprocess.run(
        [exe, PREFLIGHT_REL, str(path), "--output", str(report_path)],
        cwd=orchestrator_root, capture_output=True, text=True, timeout=300, check=False,
    )
    return proc.returncode


def publish_aggregate(doc: dict, dest: Path | str, *, private_root: Path | str | None = None,
                      orchestrator_root: Path = ORCHESTRATOR_ROOT) -> Path:
    """Validate, preflight and only then write an aggregate to ``dest`` (which may be in a repo)."""
    errs = validate_aggregate(doc)
    if errs:
        raise PrivacyError("aggregate refused: " + "; ".join(errs))
    stage = private_dir(Path(private_root or PRIVATE_ROOT) / "publish-staging")
    text = json.dumps(doc, sort_keys=True) + "\n"
    cand = private_write(stage / f"candidate-{os.getpid()}.jsonl", text)
    report = stage / f"preflight-{os.getpid()}.json"
    rc = run_preflight(cand, report, orchestrator_root)
    if rc != 0:
        raise PrivacyError(f"raw_trace_publish_preflight refused the aggregate (rc={rc}); report {report}")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cand.unlink(missing_ok=True)
    return dest

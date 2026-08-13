#!/usr/bin/env python3
"""Persist one worker boundary without invoking the full wrap-up or session bus."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Sequence

SCHEMA = "worker_checkpoint.v1"
RECEIPT_SCHEMA = "worker_checkpoint.receipt.v1"
PHASES = (
    "prepared",
    "handoff_written",
    "progress_written",
    "validation_passed",
    "committed",
    "pushed",
    "receipt_ready",
    "published",
)
OUTPUT_PREVIEW_BYTES = 4096
WORKER_RE = re.compile(r"main[A-D]\Z")
CHECKBOX_RE = re.compile(
    r"^(?P<indent>\s*)(?P<bullet>[-*]) \[(?P<state>[ xX])\] "
    r"(?P<body>.*?)(?P<nl>\r?\n)?\Z"
)
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
FORBIDDEN_EXACT = frozenset({
    "handoffs/active/.index-state.json",
    "handoffs/active/.index-graph.json",
    "handoffs/active/master-handoff-index.md",
    "handoffs/active/inference-batch-loop.md",
    "data/handoff_timeline.json",
    "wiki/source_manifest.json",
    "wiki/.last_compile",
})


class CheckpointError(RuntimeError):
    """Refusal to violate checkpoint ownership or durability."""


class InjectedCrash(RuntimeError):
    """Test-only crash after a durable transaction phase."""


class ValidationError(CheckpointError):
    """A safe argv validation failed; carries bounded evidence for journaling."""

    def __init__(self, message: str, results: list[dict]):
        super().__init__(message)
        self.results = results


class PublicationError(CheckpointError):
    """The pushed checkpoint could not be published through the session bus."""


@dataclass(frozen=True)
class Request:
    agent: str
    task_id: str
    task_text: str
    handoff: str
    outcome: str
    summary: str
    spec_ref: str
    boundary_reason: str
    next_context: str
    major_checkpoint: bool
    validations: tuple[tuple[str, ...], ...]
    resume_action: str = ""
    blocker_class: str = ""
    blocked_on: str = ""
    blocking_owner_or_event: str = ""
    evidence_refs: tuple[str, ...] = ()
    alternatives_exhausted: tuple[str, ...] = ()
    compute_request: dict | None = None
    paths: tuple[str, ...] = ()
    boundary_key: str = ""
    completed_at: str = ""


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if check and proc.returncode:
        raise CheckpointError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip() or 'no diagnostic'}"
        )
    return proc


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _atomic_json(path: Path, value: dict) -> None:
    _atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _scalar(name: str, value: str, required: bool = True) -> str:
    value = value.strip()
    if required and not value:
        raise CheckpointError(f"{name} is required")
    if any(token in value for token in ("\n", "\r", "\x00")):
        raise CheckpointError(f"{name} must be one line")
    return value


def _scalars(name: str, values: Sequence[str], required: bool = False) -> tuple[str, ...]:
    cleaned = tuple(_scalar(name, value) for value in values)
    if required and not cleaned:
        raise CheckpointError(f"one or more {name} values are required")
    if len(set(cleaned)) != len(cleaned):
        raise CheckpointError(f"duplicate {name} values are forbidden")
    return cleaned


def _validations(values: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    commands = []
    for index, value in enumerate(values, 1):
        if not isinstance(value, (list, tuple)) or not value:
            raise CheckpointError(f"validation {index} must be a non-empty argv array")
        argv = tuple(_scalar(f"validation {index} argv", str(arg)) for arg in value)
        commands.append(argv)
    if not commands:
        raise CheckpointError("one or more validation argv arrays are required")
    return tuple(commands)


def _utc(value: str) -> str:
    if value:
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CheckpointError(f"completed_at must be RFC3339: {exc}") from exc
        if stamp.tzinfo is None:
            raise CheckpointError("completed_at must include a timezone")
        stamp = stamp.astimezone(timezone.utc)
    else:
        stamp = datetime.now(timezone.utc)
    return stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_identity(start: Path, agent: str) -> tuple[Path, Path, str]:
    if not WORKER_RE.fullmatch(agent):
        raise CheckpointError("agent must be one of mainA, mainB, mainC, or mainD")
    root = Path(_git(start, "rev-parse", "--show-toplevel").stdout.strip())
    git_dir = Path(_git(root, "rev-parse", "--path-format=absolute", "--git-dir").stdout.strip())
    common = Path(_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
    try:
        shared = os.path.samefile(git_dir, common)
    except OSError:
        shared = os.path.normpath(str(git_dir)) == os.path.normpath(str(common))
    if shared:
        raise CheckpointError("worker checkpoint requires a linked private worktree, not the shared clone")
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    expected = f"lane/{agent}"
    if branch != expected:
        raise CheckpointError(f"branch ownership mismatch: expected {expected!r}, got {branch!r}")
    return root, common, branch


def _normal_rel(raw: str) -> str:
    if not raw or "\x00" in raw:
        raise CheckpointError("empty or NUL-containing path")
    pure = PurePosixPath(raw.replace(os.sep, "/"))
    if pure.is_absolute() or ".." in pure.parts:
        raise CheckpointError(f"path must be repository-relative without '..': {raw!r}")
    rel = pure.as_posix()
    return rel[2:] if rel.startswith("./") else rel


def _forbidden(rel: str) -> bool:
    name = PurePosixPath(rel).name
    return (
        rel in FORBIDDEN_EXACT
        or rel == "wiki"
        or rel.startswith("wiki/")
        or rel == ".git"
        or rel.startswith(".git/")
        or rel == "repos"
        or rel.startswith("repos/")
        or (rel.startswith("handoffs/") and name.startswith("."))
        or (rel.startswith("handoffs/active/") and name.endswith("-index.md"))
    )


def _validate_paths(root: Path, handoff: str, progress: str, requested: Sequence[str]) -> tuple[str, ...]:
    if not handoff.startswith("handoffs/active/") or _forbidden(handoff):
        raise CheckpointError(f"handoff must be one non-index active handoff: {handoff!r}")
    result: list[str] = []
    for raw in (*requested, handoff, progress):
        rel = _normal_rel(raw)
        if _forbidden(rel):
            raise CheckpointError(f"wrap-up-owned/generated path is forbidden: {rel}")
        if rel.startswith("handoffs/") and rel != handoff:
            raise CheckpointError(f"foreign handoff path is forbidden: {rel}")
        if rel.startswith("progress/") and rel != progress:
            raise CheckpointError(f"foreign or unsuffixed progress path is forbidden: {rel}")
        try:
            (root / rel).resolve(strict=False).relative_to(root.resolve())
        except ValueError as exc:
            raise CheckpointError(f"path escapes the private worktree: {rel}") from exc
        if rel not in result:
            result.append(rel)
    return tuple(result)


def _identity(req: Request, handoff: str) -> tuple[str, str, dict]:
    identity = {
        "agent": req.agent,
        "task_id": req.task_id,
        "boundary_key": req.boundary_key or req.task_id,
        "task_text": req.task_text,
        "handoff": handoff,
        "outcome": req.outcome,
    }
    stable = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    checkpoint_id = f"wcp-{hashlib.sha256(stable.encode()).hexdigest()[:24]}"
    spec = asdict(req)
    spec.update(handoff=handoff, paths=list(req.paths))
    spec.pop("completed_at", None)
    spec_hash = hashlib.sha256(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return checkpoint_id, spec_hash, identity


def _phase_at_least(journal: dict, phase: str) -> bool:
    try:
        return PHASES.index(str(journal["phase"])) >= PHASES.index(phase)
    except (KeyError, ValueError) as exc:
        raise CheckpointError(f"invalid journal phase: {journal.get('phase')!r}") from exc


def _advance(path: Path, journal: dict, phase: str, fail_after: str | None) -> None:
    if not _phase_at_least(journal, phase):
        journal["phase"] = phase
        _atomic_json(path, journal)
    if fail_after == phase:
        raise InjectedCrash(f"injected crash after {phase}")


def _done_body(req: Request, day: str, checkpoint_id: str) -> str:
    return f"{req.task_text} ✅ {day} <!-- worker-checkpoint:{checkpoint_id} -->"


def _child_body(req: Request, checkpoint_id: str) -> str:
    label = "Blocked" if req.outcome == "blocked" else "Partial"
    return (
        f"**{label} checkpoint `{checkpoint_id}`** — {req.summary}; "
        f"resume: {req.resume_action} <!-- worker-checkpoint:{checkpoint_id} -->"
    )


def _update_handoff(path: Path, req: Request, checkpoint_id: str, day: str) -> None:
    try:
        before = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CheckpointError(f"handoff not found: {path}") from exc
    lines = before.splitlines(keepends=True)
    boxes = [(i, match) for i, line in enumerate(lines) if (match := CHECKBOX_RE.match(line))]
    opens = [(i, m) for i, m in boxes if m.group("state") == " " and m.group("body") == req.task_text]
    marker = f"<!-- worker-checkpoint:{checkpoint_id} -->"
    marked = [(i, m) for i, m in boxes if marker in m.group("body")]
    if req.outcome == "completed":
        expected = _done_body(req, day, checkpoint_id)
        exact_done = [(i, m) for i, m in marked if m.group("body") == expected]
        if len(exact_done) == 1 and not opens:
            return
        if marked and not exact_done:
            raise CheckpointError("checkpoint marker collision in handoff")
        if len(opens) != 1:
            checked = [m for _, m in boxes if m.group("state").lower() == "x" and m.group("body").startswith(req.task_text)]
            if checked:
                raise CheckpointError("task is already checked by a different checkpoint")
            raise CheckpointError(f"exact task text resolved to {len(opens)} open checkboxes; expected 1")
        index, match = opens[0]
        lines[index] = (
            f"{match.group('indent')}{match.group('bullet')} [x] {expected}"
            f"{match.group('nl') or ''}"
        )
    else:
        if len(opens) != 1:
            raise CheckpointError(f"exact task text resolved to {len(opens)} open checkboxes; expected 1")
        index, match = opens[0]
        child = f"{match.group('indent')}  - [ ] {_child_body(req, checkpoint_id)}"
        expected_body = child.lstrip().split("] ", 1)[1]
        if marked:
            if len(marked) == 1 and marked[0][1].group("body") == expected_body:
                return
            raise CheckpointError("checkpoint marker collision in handoff")
        newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
        lines.insert(index + 1, child + newline)
    _atomic_text(path, "".join(lines))


def _progress_block(req: Request, checkpoint_id: str, completed_at: str, handoff: str) -> str:
    resume = req.resume_action or "n/a"
    return (
        f"<!-- worker-checkpoint:{checkpoint_id}:start -->\n"
        f"## Worker checkpoint `{checkpoint_id}`\n\n"
        f"- boundary_id: `{checkpoint_id}`\n"
        f"- task_id: `{req.task_id}`\n"
        f"- task: {req.task_text}\n"
        f"- outcome: `{req.outcome}`\n"
        f"- boundary_reason: `{req.boundary_reason}`\n"
        f"- spec_ref: `{req.spec_ref}`\n"
        f"- next_context: `{req.next_context}`\n"
        f"- major_checkpoint: `{str(req.major_checkpoint).lower()}`\n"
        f"- handoff: `{handoff}`\n"
        f"- completed_at: `{completed_at}`\n"
        f"- summary: {req.summary}\n"
        f"- resume_action: {resume}\n"
        f"<!-- worker-checkpoint:{checkpoint_id}:end -->\n"
    )


def _update_progress(path: Path, block: str, checkpoint_id: str) -> None:
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    start = f"<!-- worker-checkpoint:{checkpoint_id}:start -->"
    end = f"<!-- worker-checkpoint:{checkpoint_id}:end -->"
    if start in before or end in before:
        if before.count(start) != 1 or before.count(end) != 1:
            raise CheckpointError("progress checkpoint marker is duplicated or incomplete")
        existing = before[before.index(start):before.index(end) + len(end)] + "\n"
        if existing != block:
            raise CheckpointError("progress checkpoint_id collision with different content")
        return
    separator = "" if not before else ("\n" if before.endswith("\n") else "\n\n")
    _atomic_text(path, before + separator + block)


def _output_evidence(data: bytes) -> dict:
    preview = data[:OUTPUT_PREVIEW_BYTES].decode("utf-8", errors="replace")
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "preview": preview,
        "preview_truncated": len(data) > OUTPUT_PREVIEW_BYTES,
    }


def _run_validations(root: Path, commands: Sequence[Sequence[str]]) -> list[dict]:
    results = []
    for argv in commands:
        try:
            proc = subprocess.run(
                list(argv),
                cwd=root,
                capture_output=True,
                check=False,
                timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, bytes) else b""
            stderr = exc.stderr if isinstance(exc.stderr, bytes) else str(exc).encode()
            result = {
                "argv": list(argv),
                "rc": 124,
                "stdout": _output_evidence(stdout),
                "stderr": _output_evidence(stderr),
            }
            results.append(result)
            raise ValidationError(
                f"validation timed out rc=124: {list(argv)!r}", results
            ) from exc
        except OSError as exc:
            result = {
                "argv": list(argv),
                "rc": 127,
                "stdout": _output_evidence(b""),
                "stderr": _output_evidence(str(exc).encode()),
            }
            results.append(result)
            raise ValidationError(
                f"validation could not execute rc=127: {list(argv)!r}", results
            ) from exc
        result = {
            "argv": list(argv),
            "rc": proc.returncode,
            "stdout": _output_evidence(proc.stdout),
            "stderr": _output_evidence(proc.stderr),
        }
        results.append(result)
        if proc.returncode != 0:
            raise ValidationError(
                f"validation failed rc={proc.returncode}: {list(argv)!r}; "
                f"stderr={result['stderr']['preview']!r}",
                results,
            )
    return results


def _validate_recorded_results(commands: Sequence[Sequence[str]], results: object) -> list[dict]:
    if not isinstance(results, list) or len(results) != len(commands):
        raise CheckpointError("validation journal is missing or has the wrong command count")
    for command, result in zip(commands, results, strict=True):
        if not isinstance(result, dict) or result.get("argv") != list(command) or result.get("rc") != 0:
            raise CheckpointError("validation journal does not prove the requested argv passed")
        for stream in ("stdout", "stderr"):
            evidence = result.get(stream)
            if not isinstance(evidence, dict) or not re.fullmatch(
                r"[0-9a-f]{64}", str(evidence.get("sha256", ""))
            ):
                raise CheckpointError(f"validation journal has invalid {stream} evidence")
    return results


def _subject(checkpoint_id: str, req: Request) -> str:
    return f"checkpoint({checkpoint_id}): {req.task_id} {req.outcome}"


def _commit_candidates(root: Path, subject: str) -> list[str]:
    proc = _git(root, "log", "--all", "--format=%H%x00%s", "--fixed-strings", f"--grep={subject}")
    found = []
    for line in proc.stdout.splitlines():
        sha, _, got = line.partition("\x00")
        if got == subject and SHA_RE.fullmatch(sha):
            found.append(sha)
    return found


def _validate_commit(
    root: Path,
    sha: str,
    paths: Sequence[str],
    handoff: str,
    progress: str,
    checkpoint_id: str,
) -> None:
    if not SHA_RE.fullmatch(sha):
        raise CheckpointError(f"invalid commit SHA: {sha!r}")
    names = set(
        _git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha)
        .stdout.splitlines()
    )
    if not names.issubset(set(paths)):
        raise CheckpointError(f"checkpoint commit swept foreign paths: {sorted(names - set(paths))}")
    missing = {handoff, progress} - names
    if missing:
        raise CheckpointError(f"checkpoint commit omitted required paths: {sorted(missing)}")
    if checkpoint_id not in _git(root, "show", f"{sha}:{handoff}").stdout:
        raise CheckpointError("checkpoint commit lacks the handoff marker")
    if checkpoint_id not in _git(root, "show", f"{sha}:{progress}").stdout:
        raise CheckpointError("checkpoint commit lacks the progress marker")


def _changed_paths(root: Path, sha: str) -> list[str]:
    return sorted(
        _git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha)
        .stdout.splitlines()
    )


def _receipt_validation(results: Sequence[dict]) -> list[dict]:
    converted = []
    for result in results:
        evidence = json.dumps(
            {"stdout": result["stdout"], "stderr": result["stderr"]},
            sort_keys=True,
            separators=(",", ":"),
        )
        converted.append(
            {
                "command": result["argv"],
                "exit_code": result["rc"],
                "evidence_ref": f"inline-json:{evidence}",
            }
        )
    return converted


def _commit(
    root: Path,
    req: Request,
    checkpoint_id: str,
    paths: Sequence[str],
    handoff: str,
    progress: str,
) -> str:
    subject = _subject(checkpoint_id, req)
    candidates = _commit_candidates(root, subject)
    if len(candidates) > 1:
        raise CheckpointError(f"multiple commits claim checkpoint_id {checkpoint_id}")
    if candidates:
        sha = candidates[0]
        if _git(root, "merge-base", "--is-ancestor", sha, "HEAD", check=False).returncode:
            raise CheckpointError("recovered checkpoint commit is not on the current lane")
        _validate_commit(root, sha, paths, handoff, progress, checkpoint_id)
        return sha
    # Pathspec commit reads worktree content for only these paths. Intent-to-add
    # makes new progress/artifact files addressable without staging their content.
    for rel in paths:
        if _git(root, "ls-files", "--error-unmatch", "--", rel, check=False).returncode:
            _git(root, "add", "--intent-to-add", "--", rel)
    changed = _git(
        root, "status", "--porcelain=v1", "--untracked-files=all", "--", *paths
    ).stdout
    if not changed.strip():
        raise CheckpointError("no changes to commit and no recoverable checkpoint commit")
    _git(root, "commit", "-m", subject, "--", *paths)
    sha = _git(root, "rev-parse", "HEAD").stdout.strip()
    _validate_commit(root, sha, paths, handoff, progress, checkpoint_id)
    return sha


def _push_and_verify(root: Path, agent: str, branch: str, sha: str, progress: str) -> str:
    serializer = Path(__file__).with_name("serialized_push.py")
    if not serializer.is_file():
        raise CheckpointError(f"serialized push helper is missing: {serializer}")
    proc = subprocess.run(
        [
            sys.executable,
            str(serializer),
            "--agent",
            agent,
            "--repo",
            str(root),
            "--fetch",
            "--push",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode:
        raise CheckpointError(
            f"lane push failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
        )
    pushed_ref = f"refs/remotes/origin/{branch}"
    _git(root, "fetch", "--quiet", "origin", f"+refs/heads/{branch}:{pushed_ref}")
    if _git(root, "merge-base", "--is-ancestor", sha, pushed_ref, check=False).returncode:
        raise CheckpointError(f"commit {sha} is not reachable from pushed ref {pushed_ref}")
    if _git(root, "show", f"{sha}:{progress}").stdout != _git(root, "show", f"{pushed_ref}:{progress}").stdout:
        raise CheckpointError("pushed progress blob differs from checkpoint commit")
    return pushed_ref


def _verify_pushed(root: Path, journal: dict) -> None:
    sha = str(journal.get("commit_sha", ""))
    ref = str(journal.get("pushed_ref", ""))
    progress = str(journal.get("progress_path", ""))
    if not sha or not ref or not progress:
        raise CheckpointError("pushed journal is missing reachability fields")
    if _git(root, "merge-base", "--is-ancestor", sha, ref, check=False).returncode:
        raise CheckpointError("journal commit is no longer reachable from its pushed ref")
    if _git(root, "show", f"{sha}:{progress}").stdout != _git(root, "show", f"{ref}:{progress}").stdout:
        raise CheckpointError("pushed progress evidence was superseded without a newer checkpoint")


def _bus_envelope(req: Request, payload: dict, completed_at: str) -> dict:
    stamp = datetime.fromisoformat(completed_at.replace("Z", "+00:00")).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    sequence = int(str(payload["boundary_id"]).removeprefix("wcp-")[:15], 16)
    return {
        "schema_version": "session_bus.msg.v1",
        "id": f"msg-{stamp}-{sequence}-{req.agent}",
        "ts": completed_at,
        "from": req.agent,
        "to": "coordinator-agent",
        "kind": "task-checkpoint",
        "task_id": req.task_id,
        "payload": payload,
    }


def _bus_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise PublicationError(f"malformed outbox JSONL at {path}:{number}: {exc}") from exc
    return rows


def _verify_bus_message(bus_root: Path, agent: str, envelope: dict) -> None:
    matches = [
        row
        for row in _bus_rows(bus_root / "outbox" / f"{agent}.jsonl")
        if row.get("id") == envelope["id"]
    ]
    if len(matches) != 1:
        raise PublicationError(
            f"expected exactly one published message {envelope['id']}, found {len(matches)}"
        )
    if matches[0] != envelope:
        raise PublicationError(f"published message id collision for {envelope['id']}")


def _publish_bus_message(bus_root: Path, req: Request, envelope: dict) -> None:
    outbox = bus_root / "outbox" / f"{req.agent}.jsonl"
    existing = [row for row in _bus_rows(outbox) if row.get("id") == envelope["id"]]
    if existing:
        _verify_bus_message(bus_root, req.agent, envelope)
        return
    bus_script = Path(__file__).with_name("session_bus.py")
    proc = subprocess.run(
        [
            str(bus_script),
            "--bus-root",
            str(bus_root),
            "append",
            "--agent",
            req.agent,
            "--target",
            "outbox",
            "--json",
            json.dumps(envelope, sort_keys=True, separators=(",", ":")),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode:
        raise PublicationError(
            f"session-bus publication failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip() or 'no diagnostic'}"
        )
    _verify_bus_message(bus_root, req.agent, envelope)


def _normalize_request(request: Request) -> Request:
    compute_request = request.compute_request
    if compute_request is not None:
        if not isinstance(compute_request, dict) or not compute_request:
            raise CheckpointError("compute_request must be a non-empty JSON object")
        try:
            json.dumps(compute_request, sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise CheckpointError(f"compute_request must be finite JSON data: {exc}") from exc
    req = Request(
        agent=_scalar("agent", request.agent),
        task_id=_scalar("task_id", request.task_id),
        task_text=_scalar("task_text", request.task_text),
        handoff=_normal_rel(_scalar("handoff", request.handoff)),
        outcome=_scalar("outcome", request.outcome).lower(),
        summary=_scalar("summary", request.summary),
        spec_ref=_scalar("spec_ref", request.spec_ref),
        boundary_reason=_scalar("boundary_reason", request.boundary_reason).lower(),
        next_context=_scalar("next_context", request.next_context).lower(),
        major_checkpoint=bool(request.major_checkpoint),
        validations=_validations(request.validations),
        resume_action=_scalar("resume_action", request.resume_action, False),
        blocker_class=_scalar("blocker_class", request.blocker_class, False).lower(),
        blocked_on=_scalar("blocked_on", request.blocked_on, False),
        blocking_owner_or_event=_scalar(
            "blocking_owner_or_event", request.blocking_owner_or_event, False
        ),
        evidence_refs=_scalars("evidence_ref", request.evidence_refs),
        alternatives_exhausted=_scalars(
            "alternative_exhausted", request.alternatives_exhausted
        ),
        compute_request=compute_request,
        paths=tuple(_normal_rel(path) for path in request.paths),
        boundary_key=_scalar("boundary_key", request.boundary_key, False),
        completed_at=request.completed_at,
    )
    if req.outcome not in {"completed", "blocked", "partial"}:
        raise CheckpointError("outcome must be completed, blocked, or partial")
    if req.next_context not in {"related", "disjoint", "dry", "pre-reboot"}:
        raise CheckpointError("next_context must be related, disjoint, dry, or pre-reboot")
    if req.boundary_reason not in {"task-boundary", "pre-reboot"}:
        raise CheckpointError("boundary_reason must be task-boundary or pre-reboot")
    blocker_values = (
        req.resume_action,
        req.blocker_class,
        req.blocked_on,
        req.blocking_owner_or_event,
        req.evidence_refs,
        req.alternatives_exhausted,
        req.compute_request,
    )
    if req.outcome == "completed":
        if any(blocker_values):
            raise CheckpointError("completed checkpoints reject blocker fields")
        if req.boundary_reason != "task-boundary":
            raise CheckpointError("completed checkpoints require boundary_reason=task-boundary")
    else:
        missing = [
            name
            for name, value in (
                ("resume_action", req.resume_action),
                ("blocker_class", req.blocker_class),
                ("blocked_on", req.blocked_on),
                ("blocking_owner_or_event", req.blocking_owner_or_event),
                ("evidence_refs", req.evidence_refs),
                ("alternatives_exhausted", req.alternatives_exhausted),
            )
            if not value
        ]
        if missing:
            raise CheckpointError(
                "blocked/partial checkpoints require structured fields: " + ", ".join(missing)
            )
        if req.outcome == "partial" and req.boundary_reason != "pre-reboot":
            raise CheckpointError("partial checkpoints are allowed only for boundary_reason=pre-reboot")
        if req.outcome == "partial" and req.next_context != "pre-reboot":
            raise CheckpointError("partial checkpoints require next_context=pre-reboot")
        if req.blocker_class not in {
            "dependency",
            "operator-decision",
            "external-event",
            "compute",
        }:
            raise CheckpointError(
                "blocker_class must be dependency, operator-decision, external-event, or compute"
            )
        if req.blocker_class == "compute" and req.compute_request is None:
            raise CheckpointError("blocker_class=compute requires compute_request")
        if req.blocker_class != "compute" and req.compute_request is not None:
            raise CheckpointError("compute_request is allowed only for blocker_class=compute")
    return req


def run_checkpoint(
    request: Request,
    *,
    repo: Path | str = ".",
    fail_after: str | None = None,
    publish: bool = False,
    bus_root: Path | str | None = None,
    include_publication: bool = False,
) -> dict:
    """Run/resume a checkpoint; ``fail_after`` exists only for crash tests."""
    req = _normalize_request(request)
    if fail_after is not None and fail_after not in PHASES:
        raise CheckpointError(f"unknown fail_after phase: {fail_after}")
    root, common, branch = _repo_identity(Path(repo), req.agent)
    checkpoint_id, spec_hash, identity = _identity(req, req.handoff)
    journal_dir = common / "worker-checkpoints" / req.agent
    journal_path = journal_dir / f"{checkpoint_id}.json"
    lock_path = journal_dir / f"{checkpoint_id}.lock"
    journal_dir.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        created = not journal_path.exists()
        if not created:
            try:
                journal = json.loads(journal_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CheckpointError(f"checkpoint journal is unreadable: {exc}") from exc
            if journal.get("schema_version") != SCHEMA or journal.get("spec_hash") != spec_hash:
                raise CheckpointError(f"checkpoint_id collision for {checkpoint_id}")
            completed_at = str(journal.get("completed_at", ""))
        else:
            completed_at = _utc(req.completed_at)
            journal = {}

        stamp = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        progress = f"progress/{stamp:%Y-%m}/{stamp:%Y-%m-%d}-{req.agent}.md"
        # Reject path mistakes before creating a durable identity journal. A
        # correctable typo must not poison this stable checkpoint_id forever.
        paths = _validate_paths(root, req.handoff, progress, req.paths)
        if created:
            journal = {
                "schema_version": SCHEMA,
                "checkpoint_id": checkpoint_id,
                "boundary_id": checkpoint_id,
                "spec_hash": spec_hash,
                "identity": identity,
                "completed_at": completed_at,
                "phase": "prepared",
            }
            _atomic_json(journal_path, journal)
        _advance(journal_path, journal, "prepared", fail_after)

        journal.update(
            paths=list(paths),
            handoff_path=req.handoff,
            progress_path=progress,
            branch=branch,
        )
        _atomic_json(journal_path, journal)

        try:
            _update_handoff(
                root / req.handoff, req, checkpoint_id, stamp.strftime("%Y-%m-%d")
            )
        except CheckpointError:
            # No durable task mutation occurred. Let the caller correct an exact
            # task-text/ownership mistake and retry the same stable identity.
            if created and journal.get("phase") == "prepared":
                journal_path.unlink(missing_ok=True)
            raise
        _advance(journal_path, journal, "handoff_written", fail_after)

        _update_progress(
            root / progress,
            _progress_block(req, checkpoint_id, completed_at, req.handoff),
            checkpoint_id,
        )
        _advance(journal_path, journal, "progress_written", fail_after)

        if not _phase_at_least(journal, "validation_passed"):
            try:
                journal["validation_results"] = _run_validations(root, req.validations)
            except ValidationError as exc:
                journal["validation_results"] = exc.results
                journal["validation_failed"] = True
                _atomic_json(journal_path, journal)
                raise
            journal.pop("validation_failed", None)
            _atomic_json(journal_path, journal)
        else:
            journal["validation_results"] = _validate_recorded_results(
                req.validations, journal.get("validation_results")
            )
        _advance(journal_path, journal, "validation_passed", fail_after)

        if not _phase_at_least(journal, "committed"):
            journal["commit_sha"] = _commit(
                root, req, checkpoint_id, paths, req.handoff, progress
            )
            _atomic_json(journal_path, journal)
        else:
            _validate_commit(
                root,
                str(journal.get("commit_sha", "")),
                paths,
                req.handoff,
                progress,
                checkpoint_id,
            )
        _advance(journal_path, journal, "committed", fail_after)

        if not _phase_at_least(journal, "pushed"):
            journal["pushed_ref"] = _push_and_verify(
                root, req.agent, branch, str(journal["commit_sha"]), progress
            )
            _atomic_json(journal_path, journal)
        else:
            _verify_pushed(root, journal)
        _advance(journal_path, journal, "pushed", fail_after)

        changed_paths = _changed_paths(root, str(journal["commit_sha"]))
        artifact_paths = sorted(set(changed_paths) - {req.handoff, progress})
        receipt = {
            "schema_version": RECEIPT_SCHEMA,
            "kind": "task-checkpoint",
            "checkpoint_id": checkpoint_id,
            "payload": {
                "boundary_id": checkpoint_id,
                "agent": req.agent,
                "task_id": req.task_id,
                "task_text": req.task_text,
                "outcome": req.outcome,
                "boundary_reason": req.boundary_reason,
                "spec_ref": req.spec_ref,
                "major_checkpoint": req.major_checkpoint,
                "next_context": req.next_context,
                "resume_action": req.resume_action,
                "blocker_class": req.blocker_class,
                "blocked_on": req.blocked_on,
                "blocking_owner_or_event": req.blocking_owner_or_event,
                "evidence_refs": list(req.evidence_refs),
                "alternatives_exhausted": list(req.alternatives_exhausted),
                "compute_request": req.compute_request,
                "completed_at": completed_at,
                "handoff_paths": [req.handoff],
                "artifact_paths": artifact_paths,
                "changed_paths": changed_paths,
                "progress_path": progress,
                "branch": branch,
                "pushed_ref": journal["pushed_ref"],
                "commit_sha": journal["commit_sha"],
                "checkbox_flips": (
                    [{
                        "task_text": req.task_text,
                        "before": "open",
                        "after": "done",
                    }]
                    if req.outcome == "completed"
                    else []
                ),
                "new_tasks": (
                    []
                    if req.outcome == "completed"
                    else [{
                        "owner": req.agent,
                        "task_text": _child_body(req, checkpoint_id),
                    }]
                ),
                "validation": _receipt_validation(journal["validation_results"]),
                "completion_msg_id": None,
            },
        }
        if req.outcome == "completed":
            for field in (
                "resume_action",
                "blocker_class",
                "blocked_on",
                "blocking_owner_or_event",
                "evidence_refs",
                "alternatives_exhausted",
                "compute_request",
            ):
                receipt["payload"].pop(field)
        if _phase_at_least(journal, "receipt_ready") and journal.get("receipt") != receipt:
            raise CheckpointError("stored receipt differs from reconstructed receipt")
        journal["receipt"] = receipt
        _atomic_json(journal_path, journal)
        _advance(journal_path, journal, "receipt_ready", fail_after)

        publication: dict = {"status": "disabled", "message_id": None, "envelope": None}
        if publish:
            selected_bus_root = Path(bus_root or "/workspace/coordination/session-bus").resolve()
            envelope = _bus_envelope(req, receipt["payload"], completed_at)
            if _phase_at_least(journal, "published"):
                if journal.get("bus_root") != str(selected_bus_root):
                    raise PublicationError(
                        "published journal is bound to a different session-bus root"
                    )
                if journal.get("bus_envelope") != envelope:
                    raise PublicationError("published journal envelope differs from checkpoint")
                _verify_bus_message(selected_bus_root, req.agent, envelope)
            else:
                try:
                    _publish_bus_message(selected_bus_root, req, envelope)
                except PublicationError as exc:
                    journal["publication_failure"] = {
                        "bus_root": str(selected_bus_root),
                        "message_id": envelope["id"],
                        "error": str(exc),
                    }
                    _atomic_json(journal_path, journal)
                    raise
                journal.pop("publication_failure", None)
                journal.update(
                    bus_root=str(selected_bus_root),
                    bus_message_id=envelope["id"],
                    bus_envelope=envelope,
                )
                _atomic_json(journal_path, journal)
            _advance(journal_path, journal, "published", fail_after)
            publication = {
                "status": "published",
                "message_id": envelope["id"],
                "envelope": envelope,
            }
        elif _phase_at_least(journal, "published"):
            publication = {
                "status": "published",
                "message_id": journal["bus_message_id"],
                "envelope": journal["bus_envelope"],
            }
        result = {"journal_receipt": receipt, "bus_publication": publication}
        return result if include_publication else receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-text", required=True)
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--outcome", required=True, choices=("completed", "blocked", "partial"))
    parser.add_argument("--summary", required=True)
    parser.add_argument("--spec-ref", required=True)
    parser.add_argument(
        "--boundary-reason",
        required=True,
        choices=("task-boundary", "pre-reboot"),
    )
    parser.add_argument(
        "--next-context", required=True, choices=("related", "disjoint", "dry", "pre-reboot")
    )
    parser.add_argument("--major-checkpoint", action="store_true")
    parser.add_argument(
        "--validation-json",
        action="append",
        required=True,
        help='repeatable JSON argv array; e.g. ["python3","-m","pytest","-q"]',
    )
    parser.add_argument("--resume-action", default="")
    parser.add_argument("--blocker-class", default="")
    parser.add_argument("--blocked-on", default="")
    parser.add_argument("--blocking-owner-or-event", default="")
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--alternative-exhausted", action="append", default=[])
    parser.add_argument("--compute-request-json", default="")
    parser.add_argument("--path", action="append", default=[], dest="paths")
    parser.add_argument("--boundary-key", default="")
    parser.add_argument("--completed-at", default="")
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--bus-root",
        default="/workspace/coordination/session-bus",
        help="session bus root; defaults to the one canonical runtime plane",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="test/development escape hatch: create and push the journal receipt only",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validations = tuple(json.loads(raw) for raw in args.validation_json)
        compute_request = (
            json.loads(args.compute_request_json) if args.compute_request_json else None
        )
    except (json.JSONDecodeError, TypeError) as exc:
        print(f"worker_checkpoint: REFUSING — invalid JSON argument: {exc}", file=sys.stderr)
        return 2
    req = Request(
        agent=args.agent,
        task_id=args.task_id,
        task_text=args.task_text,
        handoff=args.handoff,
        outcome=args.outcome,
        summary=args.summary,
        spec_ref=args.spec_ref,
        boundary_reason=args.boundary_reason,
        next_context=args.next_context,
        major_checkpoint=args.major_checkpoint,
        validations=validations,
        resume_action=args.resume_action,
        blocker_class=args.blocker_class,
        blocked_on=args.blocked_on,
        blocking_owner_or_event=args.blocking_owner_or_event,
        evidence_refs=tuple(args.evidence_ref),
        alternatives_exhausted=tuple(args.alternative_exhausted),
        compute_request=compute_request,
        paths=tuple(args.paths),
        boundary_key=args.boundary_key,
        completed_at=args.completed_at,
    )
    try:
        result = run_checkpoint(
            req,
            repo=args.repo,
            publish=not args.no_publish,
            bus_root=args.bus_root,
            include_publication=True,
        )
    except CheckpointError as exc:
        print(f"worker_checkpoint: REFUSING — {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Dry-run Hermes upstream pin audit.

This script intentionally does not fetch, checkout, install, or start Hermes.
It only inspects the local checkout and the remote refs needed to plan a safe
pin bump.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_HERMES_REPO = Path("/mnt/raid0/llm/hermes-agent")
DEFAULT_ROOT_REPO = Path("/mnt/raid0/llm/epyc-root")
DEFAULT_TARGET_TAG = "v2026.7.1"


@dataclass(frozen=True)
class SmokeGate:
    name: str
    inference_required: bool
    command: str
    purpose: str


@dataclass(frozen=True)
class PinAudit:
    hermes_repo: str
    current_commit: str
    current_describe: str
    current_subject: str
    dirty_entries: list[str]
    local_tags: list[str]
    remote_main: str | None
    latest_remote_tag: str | None
    target_tag: str
    target_tag_sha: str | None
    target_tag_present_local: bool
    target_is_latest_tag: bool
    epyc_config_path: str
    epyc_config_model_base_url: str | None
    epyc_config_platform_toolsets: str | None
    smoke_gates: list[SmokeGate]
    recommendation: str


def _run_git(repo: Path, *args: str, timeout: int = 20) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return proc.stdout.strip()


def _run_git_maybe(repo: Path, *args: str, timeout: int = 20) -> str | None:
    try:
        return _run_git(repo, *args, timeout=timeout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def _remote_refs(repo: Path, *refs: str) -> dict[str, str]:
    out = _run_git_maybe(repo, "ls-remote", "origin", *refs, timeout=45)
    result: dict[str, str] = {}
    if not out:
        return result
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, ref = line.split(None, 1)
        result[ref] = sha
    return result


def _remote_tag_map(repo: Path) -> dict[str, str]:
    out = _run_git_maybe(repo, "ls-remote", "--tags", "origin", timeout=45)
    result: dict[str, str] = {}
    if not out:
        return result
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, ref = line.split(None, 1)
        if not ref.endswith("^{}"):
            continue
        name = ref.removeprefix("refs/tags/").removesuffix("^{}")
        result[name] = sha
    return result


def _tag_key(tag: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"v(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\.(\d+))?", tag)
    if not match:
        return (0, 0, 0, 0)
    year, month, day, patch = match.groups()
    return (int(year), int(month), int(day), int(patch or 0))


def _local_tags(repo: Path) -> list[str]:
    out = _run_git_maybe(repo, "tag", "--sort=-creatordate")
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _dirty_entries(repo: Path) -> list[str]:
    out = _run_git_maybe(repo, "status", "--short")
    if not out:
        return []
    return [line.rstrip() for line in out.splitlines()]


def _extract_config_value(config_text: str, key_path: list[str]) -> str | None:
    indent_stack: list[tuple[int, str]] = []
    for raw in config_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        while indent_stack and indent_stack[-1][0] >= indent:
            indent_stack.pop()
        indent_stack.append((indent, key))
        path = [item[1] for item in indent_stack]
        if path == key_path:
            stripped = value.strip()
            if not stripped:
                return None
            return stripped.strip("'\"")
    return None


def _platform_toolsets(config_text: str) -> str | None:
    for line in config_text.splitlines():
        if line.strip().startswith("cli:"):
            return line.strip()
    return None


def _smoke_gates(root_repo: Path) -> list[SmokeGate]:
    return [
        SmokeGate(
            name="static-config-audit",
            inference_required=False,
            command=f"python3 {root_repo}/scripts/hermes/hermes_pin_audit.py --target-tag {DEFAULT_TARGET_TAG}",
            purpose="Confirm local pin, remote target, dirty state, and EPYC config assumptions before any checkout.",
        ),
        SmokeGate(
            name="setup-dry-run-by-inspection",
            inference_required=False,
            command=f"bash -n {root_repo}/scripts/hermes/setup_hermes.sh && bash -n {root_repo}/scripts/hermes/launch_hermes_backend.sh",
            purpose="Catch shell drift in EPYC setup/launcher without starting services.",
        ),
        SmokeGate(
            name="reference-client-print-only",
            inference_required=False,
            command=f"python3 {root_repo}/scripts/hermes/reference_openai_client.py --print-only --x-show-routing",
            purpose="Verify the documented non-Hermes override recipe still renders without traffic.",
        ),
        SmokeGate(
            name="live-chat-overrides",
            inference_required=True,
            command=f"python3 {root_repo}/scripts/hermes/reference_openai_client.py --send --x-show-routing --stream",
            purpose="Quiet-window check that role override, routing metadata, and streaming still pass through /v1/chat/completions.",
        ),
        SmokeGate(
            name="hermes-cli-smoke",
            inference_required=True,
            command="cd /mnt/raid0/llm/hermes-agent && hermes",
            purpose="After a pin bump, manually verify basic chat, tool use, multi-turn context, streaming, and compression trigger.",
        ),
    ]


def build_audit(hermes_repo: Path, root_repo: Path, target_tag: str) -> PinAudit:
    remote_tags = _remote_tag_map(hermes_repo)
    remote_refs = _remote_refs(hermes_repo, "refs/heads/main", f"refs/tags/{target_tag}^{{}}")
    local_tags = _local_tags(hermes_repo)
    latest_remote_tag = max(remote_tags, key=_tag_key) if remote_tags else None
    config_path = root_repo / "scripts/hermes/hermes-config.yaml"
    config_text = config_path.read_text() if config_path.exists() else ""
    target_sha = remote_tags.get(target_tag) or remote_refs.get(f"refs/tags/{target_tag}^{{}}")
    target_is_latest = latest_remote_tag == target_tag if latest_remote_tag else False
    dirty = _dirty_entries(hermes_repo)
    recommendation = (
        f"Target {target_tag} is the latest visible release tag; plan a quiet-window checkout and smoke."
        if target_is_latest
        else f"Target {target_tag} is not the latest visible release tag ({latest_remote_tag}); choose target explicitly before checkout."
    )
    if dirty:
        recommendation += " Resolve or document dirty entries before changing the upstream checkout."
    if target_sha and target_tag not in local_tags:
        recommendation += " Local tags are stale; fetch tags before checkout."
    return PinAudit(
        hermes_repo=str(hermes_repo),
        current_commit=_run_git(hermes_repo, "rev-parse", "HEAD"),
        current_describe=_run_git(hermes_repo, "describe", "--tags", "--always", "--dirty"),
        current_subject=_run_git(hermes_repo, "show", "-s", "--format=%ci %s", "HEAD"),
        dirty_entries=dirty,
        local_tags=local_tags[:20],
        remote_main=remote_refs.get("refs/heads/main"),
        latest_remote_tag=latest_remote_tag,
        target_tag=target_tag,
        target_tag_sha=target_sha,
        target_tag_present_local=target_tag in local_tags,
        target_is_latest_tag=target_is_latest,
        epyc_config_path=str(config_path),
        epyc_config_model_base_url=_extract_config_value(config_text, ["model", "base_url"]),
        epyc_config_platform_toolsets=_platform_toolsets(config_text),
        smoke_gates=_smoke_gates(root_repo),
        recommendation=recommendation,
    )


def render_markdown(audit: PinAudit) -> str:
    dirty = "\n".join(f"- `{entry}`" for entry in audit.dirty_entries) or "- none"
    tags = ", ".join(f"`{tag}`" for tag in audit.local_tags) or "none"
    gates = "\n".join(
        f"| {gate.name} | {'yes' if gate.inference_required else 'no'} | `{gate.command}` | {gate.purpose} |"
        for gate in audit.smoke_gates
    )
    return f"""# Hermes Pin Audit

| Field | Value |
|---|---|
| checkout | `{audit.hermes_repo}` |
| current | `{audit.current_describe}` |
| current commit | `{audit.current_commit}` |
| current subject | {audit.current_subject} |
| remote main | `{audit.remote_main or 'unavailable'}` |
| latest remote tag | `{audit.latest_remote_tag or 'unavailable'}` |
| target tag | `{audit.target_tag}` |
| target sha | `{audit.target_tag_sha or 'unavailable'}` |
| target tag present locally | `{audit.target_tag_present_local}` |
| target is latest remote tag | `{audit.target_is_latest_tag}` |
| EPYC config | `{audit.epyc_config_path}` |
| EPYC model base_url | `{audit.epyc_config_model_base_url or 'unknown'}` |
| EPYC platform toolsets | `{audit.epyc_config_platform_toolsets or 'unknown'}` |

## Dirty Entries

{dirty}

## Local Tags

{tags}

## Smoke Gates

| Gate | Inference | Command | Purpose |
|---|---:|---|---|
{gates}

## Recommendation

{audit.recommendation}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-repo", type=Path, default=DEFAULT_HERMES_REPO)
    parser.add_argument("--root-repo", type=Path, default=DEFAULT_ROOT_REPO)
    parser.add_argument("--target-tag", default=DEFAULT_TARGET_TAG)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    args = parser.parse_args(argv)

    try:
        audit = build_audit(args.hermes_repo, args.root_repo, args.target_tag)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"hermes_pin_audit: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    else:
        print(render_markdown(audit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

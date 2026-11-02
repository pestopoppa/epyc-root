#!/usr/bin/env python3
"""Lint the project knowledge base for governance hygiene issues.

Runs lint passes against handoffs, intake index, wiki pages, and cross-references.
Reads thresholds from wiki.yaml, falls back to sensible defaults.

Exit code: 1 if any ERRORs found, 0 otherwise.
"""

from __future__ import annotations

import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is not installed in " + sys.executable + ". Run this script with the "
        "orchestrator venv: /workspace/repos/epyc-orchestrator/.venv/bin/python .claude/skills/project-wiki/scripts/lint_wiki.py",
        file=sys.stderr,
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[4]  # epyc-root

# Severity levels
ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"

Issue = tuple[str, str, str]  # (severity, file, message)

ADMIN_WIKI_FILES = {"INDEX.md", "SCHEMA.md"}
SOURCE_REFERENCE_HEADINGS = {"Source References", "References"}


def load_wiki_config() -> dict:
    """Load wiki.yaml from repo root. Returns empty dict if not found."""
    wiki_path = ROOT / "wiki.yaml"
    if wiki_path.exists():
        with open(wiki_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _get_lint_config(config: dict) -> dict:
    """Extract lint thresholds from config with defaults."""
    lint = config.get("lint", {})
    return {
        "stale_days": lint.get("stale_days", 30),
        "aging_days": lint.get("aging_days", 14),
        "unactioned_intake_days": lint.get("unactioned_intake_days", 7),
        "enabled_passes": lint.get("enabled_passes", [
            "orphan_handoffs", "stale_entries", "contradictory_status",
            "unactioned_intake", "missing_cross_refs", "wiki_article_structure",
            "wiki_link_targets", "wiki_orphans", "unsourced_bullets",
            "conflicted_citations", "contradictions",
        ]),
    }


def _extract_md_links(content: str) -> list[str]:
    """Extract markdown link targets from content: [text](target.md)."""
    return re.findall(r'\[(?:[^\]]*)\]\(([^)]+\.md)\)', content)


def _extract_h2_headings(content: str) -> set[str]:
    """Extract level-2 markdown headings without trailing anchor text."""
    headings = set()
    for match in re.finditer(r"^##\s+(.+?)\s*$", content, flags=re.MULTILINE):
        heading = match.group(1).strip()
        headings.add(heading)
    return headings


def _extract_category(content: str) -> str | None:
    """Return the wiki category metadata value if present."""
    match = re.search(r"^\*\*Category\*\*:\s*`?([^`\n]+)`?\s*$", content, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _extract_referenced_handoffs(active_dir: Path) -> set[str]:
    """Parse all *-index.md files and extract referenced handoff filenames."""
    referenced = set()
    for index_file in active_dir.glob("*-index.md"):
        content = index_file.read_text(errors="replace")
        for link in _extract_md_links(content):
            # Normalize: strip relative paths, keep just filename
            referenced.add(Path(link).name)
    # Also check master-handoff-index.md
    master = active_dir / "master-handoff-index.md"
    if master.exists():
        content = master.read_text(errors="replace")
        for link in _extract_md_links(content):
            referenced.add(Path(link).name)
    return referenced


def check_orphan_handoffs(active_dir: Path) -> list[Issue]:
    """Pass 1: Find handoff files not referenced by any index."""
    issues: list[Issue] = []
    referenced = _extract_referenced_handoffs(active_dir)

    # Index files themselves are not orphans
    index_files = {f.name for f in active_dir.glob("*-index.md")}
    index_files.add("master-handoff-index.md")

    for md_file in sorted(active_dir.glob("*.md")):
        name = md_file.name
        if name in index_files:
            continue
        if name not in referenced:
            issues.append((WARNING, name, "Not referenced by any index file (orphan)"))

    return issues


def check_stale_entries(active_dir: Path, aging_days: int, stale_days: int) -> list[Issue]:
    """Pass 2: Flag files not modified recently."""
    issues: list[Issue] = []
    now = time.time()

    for md_file in sorted(active_dir.glob("*.md")):
        age_days = int((now - md_file.stat().st_mtime) / 86400)
        if age_days > stale_days:
            issues.append((ERROR, md_file.name, f"STALE ({age_days}d, threshold {stale_days}d)"))
        elif age_days > aging_days:
            issues.append((WARNING, md_file.name, f"Aging ({age_days}d, threshold {aging_days}d)"))

    return issues


def check_contradictory_status(active_dir: Path, completed_dir: Path) -> list[Issue]:
    """Pass 3: Flag status vs directory mismatches."""
    issues: list[Issue] = []
    # Match status lines that START with a done keyword (not "active (X complete, Y pending)")
    done_start = re.compile(r'^(completed|archived|done)\b', re.IGNORECASE)
    active_pattern = re.compile(r'\b(active|in.progress)\b', re.IGNORECASE)

    # Check active/ files claiming to be done
    for md_file in sorted(active_dir.glob("*.md")):
        content = md_file.read_text(errors="replace")
        status_match = re.search(r'\*\*Status\*\*:\s*(.+)', content)
        if status_match:
            status_text = status_match.group(1).strip()
            if done_start.search(status_text):
                issues.append((ERROR, md_file.name,
                    f"In active/ but status says '{status_text}' — should be moved to completed/"))

    # Check completed/ files claiming to be active
    if completed_dir.exists():
        for md_file in sorted(completed_dir.glob("*.md")):
            content = md_file.read_text(errors="replace")
            status_match = re.search(r'\*\*Status\*\*:\s*(.+)', content)
            if status_match:
                status_text = status_match.group(1).strip()
                if active_pattern.search(status_text) and not done_start.search(status_text):
                    issues.append((WARNING, f"completed/{md_file.name}",
                        f"In completed/ but status says '{status_text}'"))

    return issues


INTAKE_REFERENCE_RE = re.compile(
    r"(?i)\bintake-(\d+)((?:\s*/\s*(?:intake-)?\d+)*)"
)


def _intake_handoff_routes(
    active_dir: Path | None,
    completed_dir: Path | None,
) -> dict[str, set[str]]:
    """Map intake IDs to non-index handoffs that cite them.

    Slash shorthand such as ``intake-902/903/907`` expands to all three IDs.
    Coordination indices are excluded because an index listing is not an owner.
    """
    routes: dict[str, set[str]] = {}
    for directory in (active_dir, completed_dir):
        if directory is None or not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name.endswith("index.md") or path.name == "master-handoff-index.md":
                continue
            content = path.read_text(errors="replace")
            for match in INTAKE_REFERENCE_RE.finditer(content):
                numbers = [match.group(1), *re.findall(r"\d+", match.group(2))]
                for number in numbers:
                    intake_id = f"intake-{int(number):03d}"
                    routes.setdefault(intake_id, set()).add(str(path))
    return routes


def check_unactioned_intake(
    index_path: Path,
    max_age_days: int,
    active_dir: Path | None = None,
    completed_dir: Path | None = None,
) -> list[Issue]:
    """Pass 4: classify aged actionable intake instead of conflating states."""
    issues: list[Issue] = []
    if not index_path.exists():
        return issues

    with open(index_path) as f:
        entries = yaml.safe_load(f)
    if not isinstance(entries, list):
        entries = entries.get("entries", []) if isinstance(entries, dict) else []

    today = date.today()
    actionable_verdicts = {"worth_investigating", "new_opportunity"}
    handoff_routes = _intake_handoff_routes(active_dir, completed_dir)

    for entry in entries:
        verdict = entry.get("verdict", "")
        if verdict not in actionable_verdicts:
            continue
        if entry.get("handoffs_created") or entry.get("handoffs_updated"):
            continue

        ingested = entry.get("ingested_date", "")
        if not ingested:
            continue
        try:
            ingested_date = datetime.strptime(str(ingested), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        age = (today - ingested_date).days
        if age > max_age_days:
            eid = entry.get("id", "unknown")
            title = entry.get("title", "untitled")[:60]
            disposition = entry.get("integration_disposition")
            verification = entry.get("verification")
            if handoff_routes.get(eid) or disposition == "integrated":
                category = "missing-routing-metadata"
                detail = "handoff citation/integrated disposition exists but routing fields are absent"
            elif disposition in {"knowledge_only", "monitor", "declined"}:
                continue
            elif disposition == "awaiting_dive" or verification == "stage1-unverified":
                category = "stage1-awaiting-dive"
                detail = "Stage-1 review still needs a primary-source dive"
            elif verification in {"dive-verified", "dive-overturned"}:
                category = "verified-unactioned"
                detail = "dive verification exists but no route or terminal disposition is recorded"
            else:
                category = "legacy-needs-disposition"
                detail = "legacy actionable entry has no explicit disposition"
            issues.append((
                WARNING,
                eid,
                f"[{category}] {detail}; verdict='{verdict}', {age}d old: {title}",
            ))

    return issues


_CLONE_REPOS_FARM_ENTRY_RE = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9_-]*):[^:\s]+:[^:\s]+$"
)


def _symlink_farm_members(repo_root: Path) -> set[str]:
    """Return the sibling-repo names the repos/ symlink farm defines.

    The farm itself (repos/<name> symlinks into /mnt/raid0/llm) is created
    only in the shared clone by scripts/clone-repos.sh, but that script is
    tracked, so a lane worktree can read it and prove a target is
    cross-repo rather than dangling. An unreadable or unparseable script
    yields no members and the linter fails closed (no skips).
    """
    members: set[str] = set()
    path = repo_root / "scripts" / "clone-repos.sh"
    if not path.exists():
        return members
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return members
    in_farm = False
    for line in lines:
        if "repos=(" in line:
            in_farm = True
            continue
        if not in_farm:
            continue
        if ")" in line:
            break
        match = _CLONE_REPOS_FARM_ENTRY_RE.match(line)
        if match:
            members.add(match.group(1))
    return members


def _cross_repo_skip_message(repo_root: Path, target: Path) -> str | None:
    """Explain why ``target`` is skipped, or None when it must be checked.

    A target is provably cross-repo when its repo-relative path enters
    ``repos/<member>/`` for a member of the symlink farm, and this worktree
    does not actually carry that farm entry (a lane worktree, or a shared
    clone before clone-repos.sh ran). When the farm entry is present the
    target resolves normally and a real dangling link stays an ERROR.
    """
    normalized = Path(os.path.normpath(str(target)))
    try:
        parts = normalized.relative_to(repo_root).parts
    except ValueError:
        return None
    if len(parts) < 2 or parts[0] != "repos":
        return None
    member = parts[1]
    if member not in _symlink_farm_members(repo_root):
        return None
    farm_entry = repo_root / "repos" / member
    if farm_entry.is_symlink() or farm_entry.exists():
        return None
    return (
        "cross-repo target under repos/"
        f"{member} cannot be verified from this worktree (the repos/ symlink "
        "farm exists only in /workspace); skipped, not flagged dangling"
    )


def check_missing_crossrefs(active_dir: Path, completed_dir: Path) -> list[Issue]:
    """Pass 5: Check that markdown links in handoffs point to existing files."""
    issues: list[Issue] = []

    for md_file in sorted(active_dir.glob("*.md")):
        content = md_file.read_text(errors="replace")
        for link in _extract_md_links(content):
            # Skip external links and anchors
            if link.startswith("http") or link.startswith("#") or link.startswith("/"):
                continue
            # Resolve relative to the handoff's directory
            target_name = Path(link).name
            # Check in active/ and completed/
            found = (active_dir / target_name).exists()
            if not found and completed_dir.exists():
                found = (completed_dir / target_name).exists()
            # Also check parent-relative paths like ../completed/foo.md
            if not found:
                resolved = (active_dir / link).resolve()
                found = resolved.exists()
            if not found:
                skip = _cross_repo_skip_message(
                    active_dir.parent.parent, active_dir / link
                )
                if skip:
                    issues.append((INFO, md_file.name, f"{skip}: {link}"))
                    continue
                issues.append((ERROR, md_file.name,
                    f"Broken link: [{link}] target not found"))

    return issues


def check_wiki_article_structure(wiki_dir: Path) -> list[Issue]:
    """Pass 6: Check generated wiki pages have minimum reviewable structure."""
    issues: list[Issue] = []
    if not wiki_dir.exists():
        return [(ERROR, str(wiki_dir), "Wiki directory not found")]

    required_sections = {"Summary"}
    recommended_sections = {"Key Findings", "Open Questions", "Related Categories"}

    for md_file in sorted(wiki_dir.glob("*.md")):
        if md_file.name in ADMIN_WIKI_FILES:
            continue

        content = md_file.read_text(errors="replace")
        target = f"wiki/{md_file.name}"
        h1_count = len(re.findall(r"^#\s+.+", content, flags=re.MULTILINE))
        if h1_count == 0:
            issues.append((ERROR, target, "Missing top-level H1 heading"))
        elif h1_count > 1:
            issues.append((WARNING, target, f"Expected one H1 heading, found {h1_count}"))

        category = _extract_category(content)
        if not category:
            issues.append((
                WARNING,
                target,
                "Missing **Category** metadata; treating as a legacy/reference page",
            ))
            continue

        expected_slug = category.replace("_", "-")
        if md_file.stem != expected_slug:
            issues.append((
                WARNING,
                target,
                f"Category `{category}` does not match filename slug `{md_file.stem}`",
            ))

        headings = _extract_h2_headings(content)
        for section in sorted(required_sections):
            if section not in headings:
                issues.append((ERROR, target, f"Missing required section: ## {section}"))

        if not headings & SOURCE_REFERENCE_HEADINGS:
            issues.append((
                ERROR,
                target,
                "Missing source-reference section: ## Source References or ## References",
            ))

        for section in sorted(recommended_sections):
            if section not in headings:
                issues.append((WARNING, target, f"Missing recommended section: ## {section}"))

    return issues


def check_wiki_link_targets(wiki_dir: Path) -> list[Issue]:
    """Pass 7: Resolve every relative link a wiki page makes against the filesystem.

    Nothing else here does this. `check_missing_crossrefs` looks the other way
    (handoff -> wiki) and matches on basename found in EITHER active/ or
    completed/, so relocating a handoff between the two is invisible to it. That
    is how 151 wiki links rotted on 2026-08-16 — six handoffs moved to
    completed/ during a routine wrap-up prune and every lint pass stayed green.

    A link is a claim that a document says something. When it dangles, the claim
    is unsupported, so this is an ERROR, not a style warning.

    One deliberate exception: targets that enter repos/<member>/ for a member
    of the cross-repo symlink farm (scripts/clone-repos.sh). The farm exists
    only in the shared clone, so a lane worktree cannot verify such targets —
    they are reported as INFO there, and verified as hard errors in the shared
    clone where the farm is present.
    """
    issues: list[Issue] = []
    if not wiki_dir.exists():
        return [(ERROR, str(wiki_dir), "Wiki directory not found")]

    # Only relative links are ours to resolve; http(s) and bare anchors are not.
    link_re = re.compile(r"\[(?:[^\]]*)\]\((\.{1,2}/[^)\s]+?\.md)(#[^)\s]*)?\)")

    for md_file in sorted(wiki_dir.rglob("*.md")):
        content = md_file.read_text(errors="replace")
        # Strip fenced code blocks and inline code: a path inside backticks is
        # being *discussed*, not followed, and flagging it is a false positive.
        stripped = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        stripped = re.sub(r"`[^`\n]*`", "", stripped)

        seen: set[str] = set()
        for match in link_re.finditer(stripped):
            target, anchor = match.group(1), match.group(2)
            # Key on target AND anchor: two links to one file with different
            # anchors are two distinct claims, and keying on the path alone lets
            # a plain link earlier in the page mask a broken anchor later.
            key = f"{target}{anchor or ''}"
            if key in seen:
                continue
            seen.add(key)
            resolved = (md_file.parent / target).resolve()
            if not resolved.exists():
                skip = _cross_repo_skip_message(
                    wiki_dir.parent, md_file.parent / target
                )
                if skip:
                    issues.append((INFO, f"wiki/{md_file.name}", f"{skip}: {target}"))
                    continue
                issues.append((
                    ERROR, f"wiki/{md_file.name}",
                    f"Dangling link target: {target} (resolves to {resolved})",
                ))
                continue
            # An anchor that names a heading the target no longer has is the
            # same defect one level down: the citation points at a document,
            # but not at the passage it claims.
            if anchor:
                slug = anchor[1:].lower()
                body = resolved.read_text(errors="replace")
                heads = {
                    re.sub(r"[^a-z0-9\s-]", "", h.lower()).strip().replace(" ", "-")
                    for h in re.findall(r"^#{1,6}\s+(.+?)\s*$", body, flags=re.MULTILINE)
                }
                if slug and slug not in heads:
                    issues.append((
                        WARNING, f"wiki/{md_file.name}",
                        f"Link anchor not found in target: {target}{anchor}",
                    ))
    return issues


# ---------------------------------------------------------------- KT-1 passes

_INTAKE_CITE = re.compile(r"intake-\d+")
_PATH_CITE = re.compile(r"\]\([^)]+\)|`[^`\s]*/[^`\s]*`|\b[0-9a-f]{7,40}\b")


def check_wiki_orphans(wiki_dir: Path) -> list[Issue]:
    """Wiki pages with no inbound link from another page and absent from INDEX.md."""
    pages = {p.name for p in wiki_dir.glob("*.md")} - ADMIN_WIKI_FILES
    linked: set[str] = set()
    for p in wiki_dir.glob("*.md"):
        for link in _extract_md_links(p.read_text(encoding="utf-8", errors="ignore")):
            target = Path(link.split("#", 1)[0]).name
            if target and target != p.name:
                linked.add(target)
    return [(WARNING, f"wiki/{n}", "orphan page: no inbound wiki link and not in INDEX.md")
            for n in sorted(pages - linked)]


def check_unsourced_bullets(wiki_dir: Path) -> list[Issue]:
    """Bullets in `## Compiled Update` sections citing neither an intake entry, a path/link nor a SHA.

    A bullet whose section carries a non-empty Source References/Sources sub-list is only
    section-sourced (INFO: provenance exists but is not bound to the bullet). A bullet in a section
    with no source list at all is a WARNING. `### Open questions` / `### Related` are exempt.
    """
    issues: list[Issue] = []
    for p in sorted(wiki_dir.glob("*.md")):
        if p.name in ADMIN_WIKI_FILES:
            continue
        sections: list[tuple[list[tuple[int, str]], bool]] = []
        cur: list[tuple[int, str]] | None = None
        has_src = in_src = exempt = False
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            # KT-4 pages keep their updates demoted to `### Compiled Update` under `## Compile Log`
            if line.startswith("## ") or line.startswith("### Compiled Update"):
                if cur is not None:
                    sections.append((cur, has_src))
                cur = [] if line.lstrip("#").startswith(" Compiled Update") else None
                has_src = in_src = exempt = False
                continue
            if cur is None:
                continue
            if line.startswith(("### ", "#### ")):
                low = line.lower()
                in_src = "source" in low or "reference" in low
                exempt = any(k in low for k in ("open question", "related"))
                continue
            stripped = line.lstrip()
            if stripped[:2] not in ("- ", "* "):
                continue
            cited = bool(_INTAKE_CITE.search(line) or _PATH_CITE.search(line))
            if in_src:
                has_src = has_src or cited
            elif not exempt and not cited:
                cur.append((n, stripped))
        if cur is not None:
            sections.append((cur, has_src))
        for bullets, sourced in sections:
            for n, text in bullets:
                issues.append((INFO if sourced else WARNING, f"wiki/{p.name}:{n}",
                               ("section-sourced bullet: " if sourced else "unsourced bullet: ")
                               + text[:80]))
    return issues


def check_conflicted_citations(wiki_dir: Path, as_of: str | None = None) -> list[Issue]:
    """Run `vidya cite-check` over the wiki and report blocking citations (conflicted/refuted/dangling).

    Uses the CLI rather than re-implementing it, so the lint and the gate cannot disagree.
    """
    import json as _json
    import subprocess

    as_of = as_of or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    cli = ROOT / "scripts" / "vidya" / "cli.py"
    try:
        out = subprocess.run([sys.executable, str(cli), "--json", "cite-check", "--as-of", as_of,
                              str(wiki_dir)], capture_output=True, text=True, timeout=300, cwd=ROOT)
        data = _json.loads(out.stdout)
    except Exception as exc:  # noqa: BLE001 -- an unavailable gate is reported, never silently passed
        return [(WARNING, "wiki/", f"cite-check unavailable: {exc}")]
    return [(ERROR if v["status"] in ("conflicted", "overturned") else WARNING, v["path"],
             f"intake-{v['entry']} citation is {v['status']}")
            for v in data.get("verdicts", []) if v["status"] in ("conflicted", "overturned", "dangling")]


def check_contradictions(queue: Path | None = None) -> list[Issue]:
    """Pending KT-2 contradiction pairs (quote-hashed, operator-adjudicated, never auto-resolved)."""
    import json as _json

    queue = queue or ROOT / "data" / "vidya" / "contradiction_queue.jsonl"
    if not queue.exists():
        return []
    rows = [_json.loads(ln) for ln in queue.read_text().splitlines() if ln.strip()]
    return [(WARNING, f"{r['a']['path']}:{r['a']['line']}",
             f"contradicts {r['b']['path']}:{r['b']['line']} ({r['id']}, pending adjudication)")
            for r in rows if r.get("status") == "pending"]


def main() -> int:
    import argparse
    import json as _json

    ap = argparse.ArgumentParser(description="Lint the project knowledge base")
    ap.add_argument("--json", action="store_true", help="emit a JSON report instead of text")
    ap.add_argument("--json-out", help="also write the JSON report to this path")
    ap.add_argument("--only", help="comma-separated pass names to run (default: wiki.yaml)")
    args = ap.parse_args()
    config = load_wiki_config()
    lint_cfg = _get_lint_config(config)
    enabled = set(args.only.split(",")) if args.only else set(lint_cfg["enabled_passes"])

    active_dir = ROOT / "handoffs" / "active"
    completed_dir = ROOT / "handoffs" / "completed"
    index_path = ROOT / "research" / "intake_index.yaml"
    wiki_dir = ROOT / "wiki"

    if not active_dir.exists():
        print(f"ERROR: Active handoffs directory not found at {active_dir}")
        return 1

    all_issues: list[Issue] = []
    pass_names = []

    # Pass 1: Orphan handoffs
    if "orphan_handoffs" in enabled:
        issues = check_orphan_handoffs(active_dir)
        all_issues.extend(issues)
        pass_names.append(("Orphan handoffs", issues))

    # Pass 2: Stale entries
    if "stale_entries" in enabled:
        issues = check_stale_entries(active_dir, lint_cfg["aging_days"], lint_cfg["stale_days"])
        all_issues.extend(issues)
        pass_names.append(("Stale entries", issues))

    # Pass 3: Contradictory status
    if "contradictory_status" in enabled:
        issues = check_contradictory_status(active_dir, completed_dir)
        all_issues.extend(issues)
        pass_names.append(("Contradictory status", issues))

    # Pass 4: Intake disposition
    if "unactioned_intake" in enabled:
        issues = check_unactioned_intake(
            index_path,
            lint_cfg["unactioned_intake_days"],
            active_dir,
            completed_dir,
        )
        all_issues.extend(issues)
        pass_names.append(("Intake disposition", issues))

    # Pass 5: Missing cross-refs
    if "missing_cross_refs" in enabled:
        issues = check_missing_crossrefs(active_dir, completed_dir)
        all_issues.extend(issues)
        pass_names.append(("Missing cross-refs", issues))

    # Pass 6: Generated wiki article structure
    if "wiki_article_structure" in enabled:
        issues = check_wiki_article_structure(wiki_dir)
        all_issues.extend(issues)
        pass_names.append(("Wiki article structure", issues))

    # Pass 7: Wiki link targets resolve
    if "wiki_link_targets" in enabled:
        issues = check_wiki_link_targets(wiki_dir)
        all_issues.extend(issues)
        pass_names.append(("Wiki link targets", issues))

    # KT-1 passes
    for key, label, fn in (
        ("wiki_orphans", "Wiki orphan pages", lambda: check_wiki_orphans(wiki_dir)),
        ("unsourced_bullets", "Unsourced bullets", lambda: check_unsourced_bullets(wiki_dir)),
        ("conflicted_citations", "Conflicted citations", lambda: check_conflicted_citations(wiki_dir)),
        ("contradictions", "Contradictions", check_contradictions),
    ):
        if key in enabled:
            issues = fn()
            all_issues.extend(issues)
            pass_names.append((label, issues))

    total_errors = sum(1 for i in all_issues if i[0] == ERROR)
    report = {
        "schema": "epyc.wiki/lint_report/v1",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {"errors": total_errors,
                    "warnings": sum(1 for i in all_issues if i[0] == WARNING)},
        "passes": {name: {"count": len(iss), "issues": [
            {"severity": sv, "target": t, "message": m} for sv, t, m in iss]}
            for name, iss in pass_names},
    }
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(_json.dumps(report, indent=2) + "\n")
    if args.json:
        print(_json.dumps(report, indent=2))
        return 1 if total_errors else 0

    # Print report
    print("=" * 70)
    print("  Knowledge Base Lint Report")
    print("=" * 70)
    print()

    for pass_name, issues in pass_names:
        errors = [i for i in issues if i[0] == ERROR]
        warnings = [i for i in issues if i[0] == WARNING]
        print(f"### {pass_name}: {len(errors)} errors, {len(warnings)} warnings")
        if not issues:
            print("  (clean)")
        infos = sum(1 for i in issues if i[0] == INFO)
        for severity, target, msg in issues:
            if severity != INFO:
                print(f"  [{severity}] {target}: {msg}")
        if infos:
            print(f"  ({infos} INFO items; see --json)")
        print()

    # Summary
    total_errors = sum(1 for i in all_issues if i[0] == ERROR)
    total_warnings = sum(1 for i in all_issues if i[0] == WARNING)
    print("-" * 70)
    print(f"Summary: {total_errors} errors, {total_warnings} warnings")

    if total_errors > 0:
        print("FAILED: Fix errors above before proceeding.")
        return 1

    print("PASSED: No errors found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

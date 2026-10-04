#!/usr/bin/env python3
"""Validate the research intake index and taxonomy."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is not installed in " + sys.executable + ". Run this script with the "
        "orchestrator venv: /workspace/repos/epyc-orchestrator/.venv/bin/python .claude/skills/research-intake/scripts/validate_intake.py",
        file=sys.stderr,
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[4]  # epyc-root
RESEARCH = ROOT / "research"
INDEX_PATH = RESEARCH / "intake_index.yaml"
CROSS_REFERENCE_MAP_PATH = (
    ROOT / ".claude" / "skills" / "research-intake" / "references" / "cross-reference-map.md"
)

REQUIRED_FIELDS = {
    "id", "arxiv_id", "url", "source_type", "title", "categories",
    "novelty", "relevance", "discovered_via", "verdict", "ingested_date",
}
SOURCE_TYPES = {"paper", "blog", "repo"}
NOVELTY_VALUES = {"high", "medium", "low", "duplicate"}
RELEVANCE_VALUES = {"high", "medium", "low", "none"}
DISCOVERED_VIA_VALUES = {"seed", "input", "expansion", "search"}
VERDICT_VALUES = {
    "new_opportunity", "already_integrated", "worth_investigating",
    "not_applicable", "superseded", "adopt_patterns", "adopt_component",
}
# What a dive found a correction did to ONE claim. `unaffected` is the load-bearing member:
# without a way to say "this sibling survived", the only expressible verdict is blanket doubt.
# `uncertain` = a reader examined the correction prose and it still does not say what happened
# to this claim. Distinct from an absent record, which means nobody looked. Clears nothing.
CORRECTION_EFFECTS = {"overturned", "narrowed", "reattributed", "unaffected", "uncertain"}
INTEGRATION_DISPOSITION_VALUES = {
    "integrated", "knowledge_only", "monitor", "declined", "awaiting_dive",
}

# Default paths — overridden by wiki.yaml if present
_RESEARCH_ROOT_DEFAULT = "/mnt/raid0/llm/epyc-inference-research"


def _expand_path(p: str) -> Path:
    """Expand ${ENV_VAR:-default} patterns and return a Path.

    os.path.expandvars does not handle the bash ${VAR:-default} syntax,
    so we pre-process those patterns before calling expandvars.
    """
    def _replace_with_default(match: re.Match) -> str:
        var, default = match.group(1), match.group(2)
        return os.environ.get(var, default)

    p = re.sub(r'\$\{(\w+):-([^}]*)\}', _replace_with_default, p)
    return Path(os.path.expandvars(p))


def load_wiki_config() -> dict:
    """Load wiki.yaml from repo root. Returns empty dict if not found."""
    wiki_path = ROOT / "wiki.yaml"
    if wiki_path.exists():
        with open(wiki_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _get_crossref_dirs(config: dict) -> dict:
    """Build CROSSREF_DIRS from wiki.yaml config, falling back to defaults."""
    xref = config.get("cross_references", {})
    research_root = os.environ.get("EPYC_RESEARCH_ROOT", _RESEARCH_ROOT_DEFAULT)

    chapters_path = xref.get("chapters", {}).get("path", f"{research_root}/docs/chapters")
    experiments_path = xref.get("experiments", {}).get("path", f"{research_root}/docs/experiments")

    handoff_paths_cfg = xref.get("handoffs", {}).get("paths",
        ["handoffs/active", "handoffs/completed", "handoffs/archived"])
    handoff_paths = []
    for p in handoff_paths_cfg:
        expanded = _expand_path(p)
        handoff_paths.append(expanded if expanded.is_absolute() else ROOT / expanded)

    return {
        "chapters": _expand_path(chapters_path),
        "handoffs": handoff_paths,
        "experiments": _expand_path(experiments_path),
    }


def _get_taxonomy_path(config: dict) -> Path:
    """Get taxonomy path from wiki.yaml config, falling back to default."""
    tax_cfg = config.get("taxonomy", {})
    legacy = tax_cfg.get("legacy", "research/taxonomy.yaml")
    legacy_path = ROOT / legacy
    return legacy_path


def _load_aliases(config: dict) -> dict[str, str]:
    """Load category aliases from wiki/SCHEMA.md if it exists.

    Parses the Aliases table in SCHEMA.md. Each row maps one or more
    alias keys to a canonical category.
    Returns: {alias: canonical} mapping.
    """
    aliases = {}
    tax_cfg = config.get("taxonomy", {})
    schema_rel = tax_cfg.get("source", "wiki/SCHEMA.md")
    schema_path = ROOT / schema_rel
    if not schema_path.exists():
        return aliases

    with open(schema_path) as f:
        content = f.read()

    # Find the Aliases section and parse table rows
    in_aliases = False
    for line in content.splitlines():
        if line.strip().startswith("## Aliases"):
            in_aliases = True
            continue
        if in_aliases and line.strip().startswith("## "):
            break  # next section
        if not in_aliases:
            continue
        # Parse table rows: | alias1, alias2 | canonical |
        m = re.match(r'\|\s*`?([^|`]+?)`?\s*\|\s*`?([^|`]+?)`?\s*\|', line)
        if m:
            alias_part = m.group(1).strip()
            canonical = m.group(2).strip()
            # Skip header rows
            if alias_part in ("Alias", "---", "-----"):
                continue
            # Handle comma-separated aliases
            for alias in alias_part.split(","):
                alias = alias.strip().strip("`")
                if alias and alias not in ("Alias", "---"):
                    aliases[alias] = canonical

    return aliases


class _DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently dropping them.

    WHY THIS EXISTS: PyYAML's default behaviour on a duplicate key is last-one-wins, with no
    warning. On 2026-08-09 an audit found 538 index entries carrying two
    `cross_references.intake_entries` blocks each — the earlier list silently discarded on every
    load — and this validator had passed cleanly through all 538 for as long as they existed,
    because by the time it inspects the parsed structure the duplicate is already gone. The check
    therefore has to happen at PARSE time; there is no way to see it afterwards.

    Nothing was lost in that particular case (the surviving block was a superset every time), but
    the file was malformed YAML that a strict parser rejects, and the next occurrence has no
    reason to be so lucky.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duplicate_keys: list[str] = []

    def construct_mapping(self, node, deep=False):  # noqa: D102 - see class docstring
        seen: set = set()
        for key_node, _ in node.value:
            try:
                key = self.construct_object(key_node, deep=deep)
            except yaml.constructor.ConstructorError:
                continue
            try:
                if key in seen:
                    line = key_node.start_mark.line + 1
                    self.duplicate_keys.append(f"line {line}: duplicate key '{key}'")
                seen.add(key)
            except TypeError:  # unhashable key — YAML itself will complain
                continue
        return super().construct_mapping(node, deep=deep)


def load_yaml(path: Path, dup_errors: list[str] | None = None) -> object:
    """Load YAML. If `dup_errors` is given, duplicate-key findings are appended to it."""
    with open(path) as f:
        loader = _DuplicateKeyLoader(f)
        try:
            data = loader.get_single_data()
            if dup_errors is not None:
                dup_errors.extend(loader.duplicate_keys)
        finally:
            loader.dispose()
    return data


def validate_taxonomy(taxonomy: dict) -> list[str]:
    errors = []
    cats = taxonomy.get("categories", {})
    if not cats:
        errors.append("Taxonomy has no categories defined")
    for key, val in cats.items():
        if not isinstance(val, dict):
            errors.append(f"Category '{key}' is not a mapping")
            continue
        for field in ("label", "description", "related_chapters"):
            if field not in val:
                errors.append(f"Category '{key}' missing field '{field}'")
    return errors


def _absorbed_ids(entries: list[dict]) -> set[str]:
    """Ids a surviving entry declares it absorbed, from its `merged_ids` field.

    Merging a duplicate away leaves a hole in the id sequence forever, and renumbering to close it
    is refused (schema § ID Sequencing). So the allowance is data: a gap is accepted only where a
    surviving entry names the id it absorbed.

    Read from a structured field rather than parsed out of the `merge_history` prose. The first
    version regexed the note for "Merged intake-NNN", which quietly made a validation rule depend
    on how a human worded a sentence -- reword the note and four entries become sequencing errors
    with no hint why. The prose is still there for the reader; this is for the program.
    """
    out: set[int] = set()
    for entry in entries:
        for mid in entry.get("merged_ids") or []:
            if isinstance(mid, str) and mid.startswith("intake-"):
                try:
                    out.add(int(mid.split("-", 1)[1]))   # compare as ints: intake-002 == intake-2
                except ValueError:
                    continue
    return out


def validate_index(entries: list[dict], valid_categories: set[str],
                   crossref_dirs: dict | None = None) -> list[str]:
    errors = []
    seen_ids = set()
    seen_arxiv = set()
    prev_num = 0
    absorbed_ids = _absorbed_ids(entries)

    for i, entry in enumerate(entries):
        eid = entry.get("id", f"<missing at index {i}>")

        # Required fields
        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            errors.append(f"{eid}: missing required fields: {missing}")

        # Required fields must be NON-EMPTY, not merely present.
        #
        # WHY: on 2026-08-09 an audit found 9 entries whose required `url` was present with a null
        # value, which the presence check above accepts. This is the same shape as the duplicate-key
        # gap fixed the same day -- a check that looks like it enforces something and does not.
        #
        # `url` has a legitimate empty case: operator-supplied inline material (a pasted write-up, a
        # screenshot, a leaked archive) genuinely has no canonical URL, and inventing one would be
        # worse than leaving it blank. So the rule is that an entry must be LOCATABLE by at least one
        # of url / arxiv_id / locator_note, where locator_note is a written explanation of why
        # neither identifier exists. That keeps the honest case honest and still refuses a silently
        # blank field.
        if not any(
            str(entry.get(k) or "").strip() for k in ("url", "arxiv_id", "locator_note")
        ):
            errors.append(
                f"{eid}: not locatable — needs a non-empty 'url' or 'arxiv_id', or a "
                f"'locator_note' explaining why neither exists"
            )
        for field in ("title", "id", "source_type", "verdict"):
            if field in entry and not str(entry.get(field) or "").strip():
                errors.append(f"{eid}: required field '{field}' is present but empty")

        # ID format and sequencing
        if isinstance(eid, str) and eid.startswith("intake-"):
            try:
                num = int(eid.split("-", 1)[1])
                # A merged-away id leaves a permanent gap: renumbering would break every
                # reference, and the gap is not an accident. The allowance is derived from the
                # data rather than hardcoded -- a surviving entry has to SAY it absorbed that id
                # in its `merge_history`, so a gap nobody explained is still an error.
                expected = prev_num + 1
                while expected in absorbed_ids:
                    expected += 1
                if num != expected:
                    errors.append(f"{eid}: ID not sequential (expected intake-{expected:03d})")
                prev_num = num
            except ValueError:
                errors.append(f"{eid}: malformed ID number")
        else:
            errors.append(f"Entry {i}: ID must start with 'intake-'")

        # Uniqueness
        if eid in seen_ids:
            errors.append(f"{eid}: duplicate ID")
        seen_ids.add(eid)

        arxiv_id = entry.get("arxiv_id")
        if arxiv_id is not None:
            if arxiv_id in seen_arxiv:
                errors.append(f"{eid}: duplicate arxiv_id '{arxiv_id}'")
            seen_arxiv.add(arxiv_id)

        # Enum validation
        st = entry.get("source_type")
        if st and st not in SOURCE_TYPES:
            errors.append(f"{eid}: invalid source_type '{st}'")

        nov = entry.get("novelty")
        if nov and nov not in NOVELTY_VALUES:
            errors.append(f"{eid}: invalid novelty '{nov}'")

        rel = entry.get("relevance")
        if rel and rel not in RELEVANCE_VALUES:
            errors.append(f"{eid}: invalid relevance '{rel}'")

        dv = entry.get("discovered_via")
        if dv and dv not in DISCOVERED_VIA_VALUES:
            errors.append(f"{eid}: invalid discovered_via '{dv}'")

        ver = entry.get("verdict")
        if ver and ver not in VERDICT_VALUES:
            errors.append(f"{eid}: invalid verdict '{ver}'")

        disposition = entry.get("integration_disposition")
        if disposition and disposition not in INTEGRATION_DISPOSITION_VALUES:
            errors.append(
                f"{eid}: invalid integration_disposition '{disposition}'"
            )

        evidence = entry.get("disposition_evidence")
        if evidence is not None:
            if not isinstance(evidence, list) or not evidence:
                errors.append(
                    f"{eid}: disposition_evidence must be a non-empty list"
                )
            elif not all(isinstance(item, str) and item.strip() for item in evidence):
                errors.append(
                    f"{eid}: disposition_evidence must contain non-empty strings"
                )

        if disposition:
            if not evidence:
                errors.append(
                    f"{eid}: integration_disposition requires disposition_evidence"
                )
            if disposition == "integrated" and not (
                entry.get("handoffs_created") or entry.get("handoffs_updated")
            ):
                errors.append(
                    f"{eid}: integrated disposition requires a created or updated handoff"
                )
            if (
                disposition == "awaiting_dive"
                and entry.get("verification") != "stage1-unverified"
            ):
                errors.append(
                    f"{eid}: awaiting_dive disposition requires "
                    "verification='stage1-unverified'"
                )

        # Credibility score validation (optional field)
        cred = entry.get("credibility_score")
        if cred is not None:
            if not isinstance(cred, int) or cred < 0 or cred > 6:
                errors.append(f"{eid}: credibility_score must be integer 0-6, got {cred!r}")

        # Contradicting evidence validation (optional field)
        contra = entry.get("contradicting_evidence")
        if contra is not None:
            if not isinstance(contra, list):
                errors.append(f"{eid}: contradicting_evidence must be a list, got {type(contra).__name__}")
            elif not all(isinstance(s, str) for s in contra):
                errors.append(f"{eid}: contradicting_evidence must contain only strings")

        # Category validation
        cats = entry.get("categories", [])
        if not isinstance(cats, list) or len(cats) == 0:
            errors.append(f"{eid}: categories must be a non-empty list")
        else:
            for cat in cats:
                if cat not in valid_categories:
                    errors.append(f"{eid}: unknown category '{cat}'")

        # claim_corrections: which claims a dive's correction actually touched (schema
        # § claim_corrections). Shape-checked because a malformed record is worse than none: it
        # looks like per-claim precision and silently reverts to blanketing the entry.
        corr = entry.get("claim_corrections")
        if corr is not None:
            n_claims = len(entry.get("key_claims") or [])
            if not isinstance(corr, list):
                errors.append(f"{eid}: claim_corrections must be a list")
            else:
                for j, rec in enumerate(corr):
                    if not isinstance(rec, dict):
                        errors.append(f"{eid}: claim_corrections[{j}] must be a mapping")
                        continue
                    ci = rec.get("claim_index")
                    if not isinstance(ci, int) or not (0 <= ci < n_claims):
                        errors.append(
                            f"{eid}: claim_corrections[{j}].claim_index must index key_claims "
                            f"(0..{n_claims - 1})"
                        )
                    if rec.get("effect") not in CORRECTION_EFFECTS:
                        errors.append(
                            f"{eid}: claim_corrections[{j}].effect must be one of "
                            f"{sorted(CORRECTION_EFFECTS)}"
                        )
                    if not str(rec.get("note") or "").strip():
                        errors.append(
                            f"{eid}: claim_corrections[{j}] needs a 'note' — an unexplained "
                            "per-claim verdict cannot be reviewed or overturned later"
                        )

        # depends_on: the evidential edge (schema § depends_on). Shape-checked here because a
        # malformed dependency is worse than an absent one -- it looks like propagation coverage
        # and provides none.
        deps = entry.get("depends_on")
        if deps is not None:
            if not isinstance(deps, list):
                errors.append(f"{eid}: depends_on must be a list")
            else:
                for j, dep in enumerate(deps):
                    if not isinstance(dep, dict):
                        errors.append(f"{eid}: depends_on[{j}] must be a mapping")
                        continue
                    target = dep.get("entry")
                    if not isinstance(target, str) or not target.startswith("intake-"):
                        errors.append(
                            f"{eid}: depends_on[{j}].entry must be an intake id"
                        )
                    elif target == eid:
                        errors.append(f"{eid}: depends_on[{j}] points at itself")
                    if not str(dep.get("why") or "").strip():
                        errors.append(
                            f"{eid}: depends_on[{j}] needs a 'why' -- an unexplained dependency "
                            "cannot be reviewed, and 18% of citations are dependencies, so the "
                            "reason is the only thing separating this from a cross-reference"
                        )
                    ci = dep.get("claim_index")
                    if ci is not None and not isinstance(ci, int):
                        errors.append(f"{eid}: depends_on[{j}].claim_index must be an integer")

        # Cross-reference file existence (warn, don't error)
        xrefs = entry.get("cross_references", {})
        if isinstance(xrefs, dict) and crossref_dirs:
            for ref_type, ref_list in xrefs.items():
                if not isinstance(ref_list, list):
                    continue
                for ref_file in ref_list:
                    if ref_type == "chapters" and "chapters" in crossref_dirs:
                        path = crossref_dirs["chapters"] / ref_file
                        if not path.exists():
                            errors.append(f"{eid}: cross-ref chapter '{ref_file}' not found")
                    elif ref_type == "handoffs" and "handoffs" in crossref_dirs:
                        found = any(
                            (d / ref_file).exists() for d in crossref_dirs["handoffs"]
                        )
                        if not found:
                            errors.append(f"{eid}: cross-ref handoff '{ref_file}' not found")
                    elif ref_type == "experiments" and "experiments" in crossref_dirs:
                        path = crossref_dirs["experiments"] / ref_file
                        if not path.exists():
                            errors.append(f"{eid}: cross-ref experiment '{ref_file}' not found")

    return errors


_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9v.]+)", re.I)


def _locator_key(entry: dict) -> str:
    """Normalized identity of the source an entry points at, or '' if it has no locator.

    `arxiv_id: 2604.08224` and `url: https://arxiv.org/abs/2604.08224` name the same paper. The
    existing duplicate-`arxiv_id` check cannot see that, which is how intake-418 and intake-797 —
    the same arXiv paper, recorded once each way — both passed validation for months. Found on
    2026-08-10 by the Vidya alias-candidate generator, not by the validator.
    """
    arxiv = entry.get("arxiv_id")
    if isinstance(arxiv, str) and arxiv.strip():
        return "arxiv:" + re.sub(r"v\d+$", "", arxiv.strip().lower().removesuffix(".pdf"))
    url = entry.get("url")
    if isinstance(url, str) and url.strip():
        m = _ARXIV_URL_RE.search(url)
        if m:
            return "arxiv:" + re.sub(r"v\d+$", "", m.group(1).lower())
        return "url:" + re.sub(r"^https?://(www\.)?", "", url.strip().lower().rstrip("/"))
    return ""


def check_laundered_arxiv_ids(entries: list[dict]) -> list[str]:
    """Flags an entry with an arXiv URL and a null `arxiv_id`.

    A hard ERROR since 2026-08-10, when the D5 merges removed the last three instances. It was
    a warning only while those existed, because filling the field in on any of them trips the
    duplicate-`arxiv_id` error and would have left the index un-validatable for every session.

    The duplicate-`arxiv_id` rule above is a hard error, so an entry that fills the field in and
    collides cannot be saved. On 2026-08-10 a sweep found **exactly 3** entries in 1,067 with an
    arXiv URL and no `arxiv_id` — all three `novelty: duplicate`, all three from one 2026-07-08
    batch, and all three carrying an id that already existed on another entry. Every one of them
    would have failed validation had the field been present.

    That is the "can I pass this check by deleting what it inspects?" failure, and the check cannot
    see it by construction: absence of a field is indistinguishable from a source that has no
    arXiv id, unless you look at the URL. So this looks at the URL.
    """
    out = []
    for entry in entries:
        url = entry.get("url")
        if not isinstance(url, str) or entry.get("arxiv_id"):
            continue
        m = _ARXIV_URL_RE.search(url)
        if m:
            out.append(
                f"{entry.get('id')}: url is an arXiv link ({m.group(1)}) but arxiv_id is empty — "
                "fill it in; an omitted identifier silently bypasses the duplicate-arxiv_id check"
            )
    return out


def check_duplicate_locators(entries: list[dict]) -> list[str]:
    """WARNINGS (not errors) for entries pointing at an identical normalized locator.

    Deliberately not fatal. A shared URL is strong evidence of a duplicate entry but not proof:
    a repository or project page can legitimately back two distinct artifacts, and this project
    has a recorded lesson against conflating a companion repo with the paper it accompanies. So
    this reports and a human decides — the failure it prevents is the silent one, where nobody
    ever learns the two entries exist.
    """
    groups: dict[str, list[str]] = {}
    explained: dict[str, int] = {}
    for entry in entries:
        key = _locator_key(entry)
        eid = entry.get("id")
        if key and isinstance(eid, str):
            groups.setdefault(key, []).append(eid)
            if str(entry.get("shared_locator_rationale") or "").strip():
                explained[key] = explained.get(key, 0) + 1
    # A group every member of which explains the sharing is a decided case, not an open one. The
    # warning exists to surface undecided collisions; leaving it firing forever after the decision
    # is how a check trains people to ignore it.
    groups = {k: v for k, v in groups.items() if explained.get(k, 0) < len(v)}
    return [
        f"{len(ids)} entries share locator {key}: {sorted(ids)} — merge, or record why they differ"
        for key, ids in sorted(groups.items())
        if len(ids) > 1
    ]


def check_merge_map(entries: list[dict]) -> list[str]:
    """The redirect map must list every absorbed id.

    A merged id resolves to nothing rather than to the wrong paper -- that is the whole reason
    renumbering is refused -- but "nothing" is only acceptable if it is recoverable. The map is
    what makes it recoverable, so a merge that does not reach the map re-creates exactly the
    unresolvable reference the policy claims to avoid. Checked here rather than trusted to a
    generation step somebody remembers to run.
    """
    absorbed = {mid for e in entries for mid in (e.get("merged_ids") or [])
                if isinstance(mid, str)}
    map_path = RESEARCH / "intake_merge_map.md"
    if not absorbed:
        return []
    if not map_path.exists():
        return [
            f"{len(absorbed)} merged id(s) recorded but research/intake_merge_map.md is missing "
            "— run resolve_intake_id.py --write-map"
        ]
    text = map_path.read_text()
    missing = sorted(m for m in absorbed if m not in text)
    return [
        f"intake_merge_map.md is missing {len(missing)} absorbed id(s) ({', '.join(missing[:5])})"
        " — run resolve_intake_id.py --write-map"
    ] if missing else []


def validate_cross_reference_map(map_path: Path, crossref_dirs: dict) -> list[str]:
    """Verify Markdown targets listed in the intake cross-reference map.

    Only Category-to-File Mapping rows are inspected.  The File Locations section
    is documentation about directories, not a source of references.  The map has
    historically used both bare handoff names and ``completed/name.md`` forms, so
    both are resolved against the configured handoff roots.
    """
    if not map_path.exists():
        return [f"cross-reference-map: not found at {map_path}"]

    errors = []
    row_pattern = re.compile(
        r"^\s*-\s+\*\*(Chapters|Handoffs|Experiments)\*\*:\s*(.*)$"
    )
    reference_pattern = re.compile(r"`([^`]+\.md)`")

    in_category_mapping = False
    for line in map_path.read_text().splitlines():
        if line.startswith("## Category → File Mapping"):
            in_category_mapping = True
            continue
        if in_category_mapping and line.startswith("## "):
            break
        if not in_category_mapping:
            continue
        row = row_pattern.match(line)
        if not row:
            continue
        ref_type, content = row.groups()
        for ref in reference_pattern.findall(content):
            if ref_type == "Chapters":
                found = (crossref_dirs["chapters"] / ref).is_file()
            elif ref_type == "Experiments":
                found = (crossref_dirs["experiments"] / ref).is_file()
            else:
                ref_path = Path(ref)
                if ref_path.parts and ref_path.parts[0] in {
                    "active", "completed", "archived"
                }:
                    found = (ROOT / "handoffs" / ref_path).is_file()
                else:
                    found = any((directory / ref_path).is_file()
                                for directory in crossref_dirs["handoffs"])
            if not found:
                errors.append(
                    f"cross-reference-map: {ref_type.lower()} '{ref}' not found"
                )

    return errors


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _plan_cells(line: str) -> list[str]:
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        raise ValueError("unsupported Markdown row: expected enclosing pipes")
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line[1:-1])]


def _unique_json_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _handoff_path(ref: object, root: Path) -> Path | None:
    if not _nonempty_text(ref):
        return None
    path = Path(ref)
    roots = (root / "handoffs/active", root / "handoffs/completed")
    if path.suffix != ".md":
        return None
    if len(path.parts) == 1:
        found = [d / path for d in roots if (d / path).is_file()]
        if len(found) > 1:
            return None
        path = found[0] if found else roots[0] / path
    elif len(path.parts) == 3 and path.parts[:2] in {
        ("handoffs", "active"), ("handoffs", "completed"),
    }:
        path = root / path
    else:
        return None
    path = path.resolve()
    return path if path.parent in roots else None


def session_cleanup_eligible(session: object) -> bool:
    """Ingestion completion alone cannot discard steering/actionable state."""
    if not isinstance(session, dict):
        return False
    stage4 = session.get("stage4")
    return (
        isinstance(stage4, dict) and stage4.get("reconciled") is True
        and (session.get("stage") == "stage4-complete"
             or (session.get("stage") == 4 and stage4.get("status") == "complete"))
    )


_V2_FILING_FIELDS = {
    "format_version", "entry_updates", "opportunity_reviews", "actionable_additions",
    "steering_reconciliation", "opportunity_scan", "outcome_reviews", "proposed_tasks",
}
_TASK_ID_PATTERN = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?:\.[A-Za-z0-9]+)*"
_CHECKBOX_TASK = re.compile(
    rf"^[ \t]*-[ \t]+\[[ xX]\][ \t]+(?:\*\*)?({_TASK_ID_PATTERN})"
    r"(?=[ \t]*(?:—|:|\*\*)|[ \t]+)"
)


def _checkbox_task_id(line: object) -> str | None:
    """Extract an ID from one actual checkbox line, not a prose/JSON mention."""
    if (not isinstance(line, str) or not line or "\n" in line or "\r" in line
            or len(line.splitlines()) != 1):
        return None
    match = _CHECKBOX_TASK.match(line)
    return match.group(1) if match else None


def _owner_checkboxes(text: str) -> dict[str, list[str]]:
    """Keep exact lines, excluding fenced examples, for owner-bound evidence."""
    tasks: dict[str, list[str]] = {}
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^[ \t]*(`{3,}|~{3,})(.*)$", line)
        if fence is not None:
            if (marker and marker[1][0] == fence[0]
                    and len(marker[1]) >= len(fence) and not marker[2].strip()):
                fence = None
            continue
        if marker:
            fence = marker[1]
            continue
        task_id = _checkbox_task_id(line)
        if task_id is not None:
            tasks.setdefault(task_id, []).append(line)
    return tasks


def _v2_actionable_union(session: dict, filing: dict, preapproval: bool,
                         recommendations: dict[str, str], errors: list[str]) -> dict[str, dict]:
    """Stage 3 unions in memory; Stage 4 requires already reconciled additions."""
    ledger = session.get("actionable_ledger")
    additions = filing.get("actionable_additions")
    if not isinstance(ledger, list) or not isinstance(additions, list):
        raise ValueError("actionable_ledger and actionable_additions must be lists")
    retained = {}
    fields = {"ledger_id", "source", "action", "terminal_mapping"}
    for row in ledger:
        if not isinstance(row, dict) or not all(
                _nonempty_text(row.get(f)) for f in ("ledger_id", "source", "action")):
            raise ValueError("retained actionable row requires nonempty ledger_id/source/action")
        rid = row["ledger_id"]
        if rid in retained:
            errors.append(f"session: duplicate recommendation ID {rid}")
        retained[rid] = row
        if preapproval:
            if ("terminal_mapping" in row and row["terminal_mapping"] is not None
                    and not _nonempty_text(row["terminal_mapping"])):
                raise ValueError(f"{rid}: retained terminal_mapping must be text or null")
        elif (not _nonempty_text(row.get("terminal_mapping"))
              or row["terminal_mapping"] != recommendations.get(rid)):
            errors.append(f"{rid}: terminal_mapping must exactly match the approved table")
    union = dict(retained)
    seen_additions = set()
    for row in additions:
        if not isinstance(row, dict) or set(row) != fields or not all(
                _nonempty_text(row[f]) for f in fields):
            raise ValueError("actionable addition requires exactly nonempty ledger_id/source/action/terminal_mapping")
        rid = row["ledger_id"]
        if rid in seen_additions:
            errors.append(f"actionable_additions: duplicate recommendation ID {rid}")
        seen_additions.add(rid)
        if row["terminal_mapping"] != recommendations.get(rid):
            errors.append(f"{rid}: addition terminal_mapping must exactly match the plan table")
        if preapproval:
            if rid in retained:
                errors.append(f"{rid}: actionable addition shadows retained ledger ID")
            else:
                union[rid] = row
        elif retained.get(rid) != row:
            errors.append(f"{rid}: Stage-4 addition must already occur identically in reconciled actionable_ledger (including source/action)")
    if set(union) != set(recommendations):
        errors.append(f"recommendation coverage mismatch: missing={sorted(set(recommendations) - set(union))}, extra={sorted(set(union) - set(recommendations))}")
    return union


def _v2_steering_rows(rows: object, label: str, final: bool,
                      definitions: set[str], errors: list[str]) -> dict[int, dict]:
    if not isinstance(rows, list):
        raise ValueError(f"{label} must be a list")
    result = {}
    previous = 0
    fields = {"seq", "stage", "verbatim", "disposition", "plan_ref"}
    for row in rows:
        if not isinstance(row, dict) or not fields <= set(row):
            raise ValueError(f"{label} row requires seq/stage/verbatim/disposition/plan_ref")
        seq = row["seq"]
        if type(seq) is not int or seq <= 0:
            raise ValueError(f"{label}.seq must be a positive integer")
        if seq <= previous:
            errors.append(f"{label}: seq must be unique and increasing ({seq})")
        previous = seq
        if (type(row["stage"]) is not int or row["stage"] not in (1, 2, 3)
                or not _nonempty_text(row["verbatim"])):
            raise ValueError(f"{label}[{seq}] requires stage 1/2/3 and nonempty verbatim")
        if "ts" in row and not _nonempty_text(row["ts"]):
            raise ValueError(f"{label}[{seq}].ts must be nonempty text when present")
        disposition = row["disposition"]
        ref = row["plan_ref"]
        if not isinstance(disposition, str) or disposition not in {"planned", "context-only", "declined"}:
            raise ValueError(f"{label}[{seq}]: unsupported steering disposition")
        if ref is not None and not _nonempty_text(ref):
            raise ValueError(f"{label}[{seq}].plan_ref must be text or null")
        if "reason" in row and not isinstance(row["reason"], str):
            raise ValueError(f"{label}[{seq}].reason must be text")
        if final:
            if "reason" not in row:
                raise ValueError(f"{label}[{seq}] requires reason")
            if disposition == "planned":
                if ref not in definitions:
                    errors.append(f"{label}[{seq}]: planned steering requires a declared P/K/M reference")
            elif ref is not None or not _nonempty_text(row["reason"]):
                errors.append(f"{label}[{seq}]: {disposition} requires null plan_ref and a nonempty grounded reason")
        result[seq] = row
    return result


def _validate_v2_coverage(session: dict, filing: dict, recommendations: dict[str, str],
                          definitions: set[str], preapproval: bool, root: Path,
                          proposed_owners: set[Path],
                          recommendation_cells: dict[str, tuple[str, str]]) -> list[str]:
    """Check declarations and evidence presence, never operational equivalence.

    A source-first scan can expose an action absent from both inventories through
    its explicit ledger_ids. It does not establish corpus completeness. Acceptance,
    closure premises, owner suitability and truth remain independent main review.
    Inputs and checkpoint files are never changed.
    """
    errors: list[str] = []
    union = _v2_actionable_union(session, filing, preapproval, recommendations, errors)
    for rid, row in union.items():
        cells = recommendation_cells.get(rid)
        if cells is None:
            continue  # Coverage mismatch is already reported by the union check.
        source, action = cells
        # Preserve the source spelling; citation suffixes identify a record or
        # one claim, not a license to replace the retained source identity.
        source_refs = [row["source"]]
        if _nonempty_text(row.get("source_ref")):
            source_refs.append(row["source_ref"])
        source_matches = any(
            source == original or ("#" not in original and re.fullmatch(
                re.escape(original) + r"#(?:record|[0-9]{2})", source))
            for original in source_refs)
        if not source_matches:
            errors.append(f"{rid}: table Source or review must match the immutable ledger source/source_ref (optional #record/#NN suffix)")
        if action != row["action"]:
            errors.append(f"{rid}: table Retained recommendation must exactly match immutable ledger action")
    retained = _v2_steering_rows(
        session.get("steering_ledger"), "session.steering_ledger", False, definitions, errors)
    reconciled_rows = filing.get("steering_reconciliation")
    reconciled = _v2_steering_rows(
        reconciled_rows, "steering_reconciliation", True, definitions, errors)
    for seq, row in retained.items():
        final_row = reconciled.get(seq)
        immutable = ("seq", "stage", "verbatim") + (("ts",) if "ts" in row else ())
        if final_row is None or any(final_row.get(f) != row[f] for f in immutable):
            errors.append(f"steering_reconciliation[{seq}]: retained steering lost or reworded (including timestamp)")
    for seq in set(reconciled) - set(retained):
        if retained and seq <= max(retained):
            errors.append(f"steering_reconciliation[{seq}]: new seq collides with retained sequence range")
    if not preapproval and session["steering_ledger"] != reconciled_rows:
        errors.append("Stage-4 steering_ledger must exactly match full steering_reconciliation")

    scan = filing.get("opportunity_scan")
    if not isinstance(scan, list) or not scan:
        raise ValueError("opportunity_scan must be a nonempty list")
    scan_fields = {"scan_id", "source_ref", "implementation_ref", "mechanism", "consumer",
                   "application", "disposition", "ledger_ids", "basis"}
    scan_ids = set()
    covered = set()
    for row in scan:
        if not isinstance(row, dict) or set(row) != scan_fields:
            raise ValueError("opportunity_scan row requires exactly " + ", ".join(sorted(scan_fields)))
        if not all(_nonempty_text(row[f]) for f in scan_fields - {"ledger_ids", "basis"}):
            raise ValueError("opportunity_scan source/implementation/mechanism/consumer/application/disposition/scan_id must be nonempty text")
        scan_id = row["scan_id"]
        if scan_id in scan_ids:
            errors.append(f"opportunity_scan: duplicate scan_id {scan_id}")
        scan_ids.add(scan_id)
        disposition = row["disposition"]
        if disposition not in {"actionable", "covered", "context-only", "declined"}:
            raise ValueError(f"{scan_id}: unsupported opportunity_scan disposition")
        ids = row["ledger_ids"]
        if not isinstance(ids, list) or not all(map(_nonempty_text, ids)):
            raise ValueError(f"{scan_id}: ledger_ids must be a list of nonempty strings")
        if len(ids) != len(set(ids)):
            errors.append(f"{scan_id}: duplicate ledger_ids")
        if disposition == "actionable" and not ids:
            errors.append(f"{scan_id}: actionable scan requires nonempty ledger_ids")
        if not isinstance(row["basis"], str) or (disposition != "actionable" and not _nonempty_text(row["basis"])):
            raise ValueError(f"{scan_id}: non-actionable scan requires explicit basis (basis must be text)")
        missing = set(ids) - set(union)
        if missing:
            errors.append(f"{scan_id}: unresolved opportunity_scan ledger_ids {sorted(missing)}")
        covered.update(ids)
    if set(recommendations) - covered:
        errors.append(f"opportunity_scan missing recommendations: {sorted(set(recommendations) - covered)}")

    proposed_tasks = filing.get("proposed_tasks")
    if not isinstance(proposed_tasks, list):
        raise ValueError("proposed_tasks must be a list")
    owner_tasks: dict[Path, dict[str, list[str]]] = {}

    def current_tasks(owner: str) -> tuple[Path, dict[str, list[str]]]:
        path = _handoff_path(owner, root)
        if path is None or not (path.is_file() or (preapproval and path in proposed_owners)):
            raise ValueError(f"task owner {owner!r} does not resolve to an existing owner or packaged stub")
        if path not in owner_tasks:
            owner_tasks[path] = (_owner_checkboxes(path.read_text(encoding="utf-8"))
                                 if path.is_file() else {})
        return path, owner_tasks[path]

    packaged_tasks = {}
    proposed_keys = set()
    for task in proposed_tasks:
        if (not isinstance(task, dict) or not {"owner", "task_text"} <= set(task)
                or set(task) - {"owner", "task_text", "previous_task_text"}
                or not _nonempty_text(task["owner"])):
            raise ValueError("proposed task requires owner/task_text and permits optional previous_task_text")
        task_id = _checkbox_task_id(task["task_text"])
        if task_id is None:
            raise ValueError("proposed task_text must be one paste-ready checkbox line with a task ID")
        has_previous = "previous_task_text" in task
        if has_previous and _checkbox_task_id(task["previous_task_text"]) != task_id:
            raise ValueError(f"{task_id}: previous_task_text must be an exact incumbent checkbox line with the same ID")
        path, existing = current_tasks(task["owner"])
        key = (path, task_id)
        if key in proposed_keys:
            errors.append(f"proposed_tasks: duplicate owner/task ID {task['owner']} / {task_id}")
        proposed_keys.add(key)
        packaged_tasks[key] = task["task_text"]
        if len(existing.get(task_id, [])) > 1:
            errors.append(f"{task_id}: current owner has ambiguous duplicate checkbox IDs")
        if preapproval:
            incumbent = existing.get(task_id, [])
            if has_previous and incumbent != [task["previous_task_text"]]:
                errors.append(f"{task_id}: previous_task_text must match the exact current owner checkbox")
            if incumbent and incumbent != [task["task_text"]] and not has_previous:
                errors.append(f"{task_id}: changing an existing checkbox requires exact previous_task_text; silent task ID collision")
        if not preapproval and existing.get(task_id) != [task["task_text"]]:
            errors.append(f"{task_id}: Stage-4 proposed task must match exact applied owner checkbox")

    outcomes = filing.get("outcome_reviews")
    if not isinstance(outcomes, dict):
        raise ValueError("outcome_reviews must be an object keyed by recommendation ID")
    if set(outcomes) != set(recommendations):
        errors.append(f"outcome review coverage mismatch: missing={sorted(set(recommendations) - set(outcomes))}, extra={sorted(set(outcomes) - set(recommendations))}")
    outcome_fields = {"required_outcome", "review_status", "review_basis", "task_refs"}
    ref_fields = {"owner", "task_id", "task_text", "acceptance"}
    referenced_keys = set()
    for rid, review in outcomes.items():
        if not isinstance(review, dict) or set(review) != outcome_fields or not all(
                _nonempty_text(review[f]) for f in outcome_fields - {"task_refs"}):
            raise ValueError(f"{rid}: outcome review requires required_outcome/review_status/review_basis/task_refs")
        status = review["review_status"]
        if status not in {"preserved", "closed-with-basis"}:
            errors.append(f"{rid}: unresolved or unsupported outcome review_status {status!r}")
        task_refs = review["task_refs"]
        if not isinstance(task_refs, list):
            raise ValueError(f"{rid}: outcome task_refs must be a list")
        terminal = recommendations.get(rid, "")
        packets = set(re.findall(r"\b[PKM]\d+\b", terminal))
        if any(p.startswith("P") for p in packets) and (status != "preserved" or not task_refs):
            errors.append(f"{rid}: immediate mapping requires preserved outcome and nonempty task_refs")
        if not any(p.startswith("P") for p in packets) and status != "closed-with-basis":
            errors.append(f"{rid}: closure/decline requires closed-with-basis outcome review")
        if not packets and task_refs:
            errors.append(f"{rid}: explicit decline must not carry task_refs")
        if status == "preserved" and not task_refs:
            errors.append(f"{rid}: preserved outcome requires nonempty task_refs")
        ref_keys = set()
        ids = set()
        for ref in task_refs:
            if not isinstance(ref, dict) or set(ref) != ref_fields or not all(
                    _nonempty_text(ref[f]) for f in ref_fields):
                raise ValueError(f"{rid}: task_ref requires exactly nonempty owner/task_id/task_text/acceptance")
            task_id = _checkbox_task_id(ref["task_text"])
            if task_id != ref["task_id"]:
                errors.append(f"{rid}: task_id must match ID extracted from exact checkbox task_text")
            path, existing = current_tasks(ref["owner"])
            key = (path, ref["task_id"])
            if key in ref_keys:
                errors.append(f"{rid}: duplicate task_ref owner/task ID")
            ref_keys.add(key)
            referenced_keys.add(key)
            ids.add(ref["task_id"])
            in_owner = existing.get(ref["task_id"]) == [ref["task_text"]]
            in_package = packaged_tasks.get(key) == ref["task_text"]
            # A proposed edit supersedes the current line only for this owner.
            proposed_key = (path, ref["task_id"])
            matches = (in_package if preapproval and proposed_key in proposed_keys else in_owner)
            if not matches:
                errors.append(f"{rid}: task_ref {ref['owner']} / {ref['task_id']} does not match exact owner checkbox or Stage-3 proposed_tasks package")
        terminal_ids = set(re.findall(
            rf"(?<![A-Za-z0-9-]){_TASK_ID_PATTERN}(?![A-Za-z0-9-])", terminal))
        if terminal_ids - ids:
            errors.append(f"{rid}: terminal task references missing owner-bound task_refs {sorted(terminal_ids - ids)}")
    for path, task_id in sorted(proposed_keys - referenced_keys):
        errors.append(f"proposed_tasks: {path.relative_to(root)} / {task_id} has no outcome_review.task_ref mapping")
    return errors


def validate_plan_payload(session: dict, plan_path: Path, entries: list[dict],
                          categories: set[str], root: Path) -> list[str]:
    """Read-only structural checks, without approval inference or semantic grading.

    Stage 3 requires a format_version=2 JSON fence under '## Stage-3 filing payload'
    when checkpoint stage3_filing is absent. That fence cannot contain its own hash.
    Persisted payloads must carry the exact plan digest; Stage 4 never falls back
    to the fence. Unversioned and explicit v1 Stage-4 payloads retain legacy checks.
    """
    errors = []
    try:
        root = Path(root).resolve()
        plan_bytes = Path(plan_path).read_bytes()
        text = plan_bytes.decode("utf-8")
        digest = hashlib.sha256(plan_bytes).hexdigest()
        if not isinstance(session, dict):
            raise ValueError("session must be an object")
        preapproval = "stage3_filing" not in session
        if preapproval:
            if session.get("stage") not in (3, "stage3"):
                raise ValueError("Stage 4 requires persisted session.stage3_filing")
            sections = re.findall(
                r"(?ms)^## Stage-3 filing payload[ \t]*\r?\n(.*?)(?=^## |\Z)", text)
            if len(sections) != 1:
                raise ValueError("expected one 'Stage-3 filing payload' section")
            fence = re.fullmatch(
                r"\s*```json[ \t]*\r?\n(.*?)\r?\n```[ \t]*\s*", sections[0], re.S)
            if fence is None:
                raise ValueError("filing payload section must contain exactly one JSON fence")
            filing = json.loads(fence.group(1), object_pairs_hook=_unique_json_object)
            if not isinstance(filing, dict):
                raise ValueError("Stage-3 filing payload must be an object")
        else:
            filing = session["stage3_filing"]
            if not isinstance(filing, dict):
                raise ValueError("session.stage3_filing must be an object")
            if filing.get("plan_sha256") != digest:
                errors.append("stage3_filing.plan_sha256 does not match exact plan bytes")

        version = filing.get("format_version")
        if "format_version" in filing and (type(version) is not int or version not in (1, 2)):
            raise ValueError("format_version must be integer 1 or 2; unsupported explicit version")
        stage = session.get("stage")
        stage3 = stage in (3, "stage3")
        stage4 = stage in (4, "stage4", "stage4-in-progress", "stage4-complete")
        if version == 1 and (preapproval or not stage4):
            raise ValueError("format_version: 1 is supported only for persisted Stage-4 payloads")
        v2 = version == 2
        if (preapproval or stage3) and not v2:
            raise ValueError("new Stage-3 filing fence requires format_version: 2")
        if v2:
            allowed = _V2_FILING_FIELDS | {"proposed_stubs"}
            if not preapproval:
                allowed.add("plan_sha256")
            if not _V2_FILING_FIELDS <= set(filing) or set(filing) - allowed:
                raise ValueError("v2 filing requires " + ", ".join(sorted(_V2_FILING_FIELDS))
                                 + "; permits only optional proposed_stubs and persisted plan_sha256")

        marker = "## Complete recommendation mapping\n"
        if text.count(marker) != 1:
            raise ValueError("expected one 'Complete recommendation mapping' section")
        section = text.split(marker, 1)[1].split("\n## ", 1)[0]
        rows = [_plan_cells(line) for line in section.splitlines()
                if line.lstrip().startswith("|")]
        header = ["Ledger row", "Source or review", "Retained recommendation",
                  "Terminal plan mapping"]
        if (len(rows) < 3 or rows[0] != header or len(rows[1]) != 4
                or not all(re.fullmatch(r":?-+:?", cell) for cell in rows[1])):
            raise ValueError("unsupported recommendation table: expected approved four-column format")
        recommendations = {}
        recommendation_cells = {}
        definitions = set(re.findall(
            r"(?m)^\|[ \t]*([PKM]\d+)(?:[ \t]+[^\n|]*)?[ \t]*\|", text))
        for cells in rows[2:]:
            if len(cells) != 4 or not all(cells):
                raise ValueError("recommendation rows require four nonempty cells")
            rid, source, action, terminal = cells
            if rid in recommendations:
                errors.append(f"plan: duplicate recommendation ID {rid}")
            recommendations[rid] = terminal
            recommendation_cells[rid] = (source, action)
            refs = set(re.findall(r"\b[PKM]\d+\b", terminal))
            if refs - definitions:
                errors.append(f"{rid}: undefined terminal references {sorted(refs - definitions)}")
            if not refs and not re.fullmatch(r"decline\s*(?::|→)\s*\S.*", terminal):
                errors.append(f"{rid}: terminal needs a declared P/K/M reference or explicit decline")

        stubs = filing.get("proposed_stubs", [])
        if not isinstance(stubs, list):
            raise ValueError("proposed_stubs must be a list")
        proposed_owners = set()
        for stub in stubs:
            if not isinstance(stub, dict) or set(stub) != {
                "path", "content", "index_file", "index_row",
            }:
                raise ValueError("stub package requires path/content/index_file/index_row")
            path = _handoff_path(stub["path"], root)
            if (path is None or path.parent != root / "handoffs/active"
                    or path in proposed_owners):
                raise ValueError("stub path must name a unique active handoff")
            if v2 and not preapproval:
                if not path.is_file():
                    raise ValueError("Stage-4 packaged stub must resolve to an applied active handoff")
            elif path.exists():
                raise ValueError("stub path must name a unique new active handoff")
            if not _nonempty_text(stub["content"]):
                raise ValueError("stub content must be nonempty text")
            if v2 and not preapproval and path.read_bytes() != stub["content"].encode("utf-8"):
                errors.append(f"Stage-4 packaged stub {stub['path']!r} content does not match the approved stub")
            domain = r"(?:inference-research|routing-and-optimization|research-evaluation|user-facing-harness|pipeline-integration|reviewer-control-plane)"
            if (not isinstance(stub["index_file"], str)
                    or not re.fullmatch(rf"handoffs/active/{domain}-index\.md", stub["index_file"])
                    or not (root / stub["index_file"]).is_file()):
                raise ValueError("stub index_file must name an existing domain index")
            row = stub["index_row"]
            if not isinstance(row, str) or len(row.splitlines()) != 1:
                raise ValueError("stub package requires exactly one index row")
            cells = _plan_cells(row)
            if (len(cells) != 5 or not all(cells) or len(cells[3]) > 140
                    or not re.fullmatch(r"[A-Z]+-\d+", cells[0])):
                raise ValueError("stub index_row violates the five-cell thin-row contract")
            link = re.fullmatch(r"\[[^\]]+\]\(([^)]+)\)", cells[2])
            if link is None or _handoff_path(link.group(1), root) != path:
                raise ValueError("stub index_row must link to its packaged handoff")
            if v2 and not preapproval:
                index_text = (root / stub["index_file"]).read_text(encoding="utf-8")
                if index_text.splitlines().count(row) != 1:
                    errors.append(f"Stage-4 packaged stub {stub['path']!r} requires its exact approved index_row once in the applied index")
            proposed_owners.add(path)

        updates = filing.get("entry_updates")
        if not isinstance(updates, list):
            raise ValueError("stage3_filing.entry_updates must be a list")
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise ValueError("index entries must be a list of mappings")
        proposed = copy.deepcopy(entries)
        by_id = {entry.get("id"): entry for entry in proposed}
        patch_fields = {"id", "integration_disposition", "handoffs_updated",
                        "handoffs_created", "disposition_evidence"}
        seen_updates = set()
        for patch in updates:
            if not isinstance(patch, dict) or set(patch) != patch_fields:
                raise ValueError("entry update requires exactly " + ", ".join(sorted(patch_fields)))
            eid = patch["id"]
            if not _nonempty_text(eid) or eid not in by_id or eid in seen_updates:
                raise ValueError(f"unknown or duplicate entry update ID {eid!r}")
            seen_updates.add(eid)
            if not _nonempty_text(patch["integration_disposition"]):
                raise ValueError(f"{eid}: proposed integration_disposition must be text")
            for field in ("handoffs_updated", "handoffs_created", "disposition_evidence"):
                if not isinstance(patch[field], list) or not all(map(_nonempty_text, patch[field])):
                    raise ValueError(f"{eid}: proposed {field} must contain nonempty strings")
            for ref in patch["handoffs_updated"] + patch["handoffs_created"]:
                path = _handoff_path(ref, root)
                if path is None or not (path.is_file() or path in proposed_owners):
                    errors.append(f"{eid}: proposed owner {ref!r} does not resolve")
            by_id[eid].update(copy.deepcopy(patch))
        errors.extend(validate_index(proposed, categories))

        if v2:
            errors.extend(_validate_v2_coverage(
                session, filing, recommendations, definitions, preapproval, root,
                proposed_owners, recommendation_cells))
        else:
            ledger = session.get("actionable_ledger")
            if not isinstance(ledger, list) or not ledger:
                raise ValueError("session.actionable_ledger must be a nonempty list")
            seen = set()
            for row in ledger:
                if not isinstance(row, dict) or not _nonempty_text(row.get("ledger_id")):
                    raise ValueError("actionable ledger row requires a nonempty ledger_id")
                rid = row["ledger_id"]
                if rid in seen:
                    errors.append(f"session: duplicate recommendation ID {rid}")
                seen.add(rid)
                if not preapproval and (
                        not _nonempty_text(row.get("terminal_mapping"))
                        or row["terminal_mapping"] != recommendations.get(rid)):
                    errors.append(f"{rid}: terminal_mapping must exactly match the approved table")
            if seen != set(recommendations):
                errors.append(f"recommendation coverage mismatch: missing={sorted(set(recommendations) - seen)}, extra={sorted(seen - set(recommendations))}")

        reviews = filing.get("opportunity_reviews")
        if not isinstance(reviews, dict):
            raise ValueError("stage3_filing.opportunity_reviews must be an object")
        required_reviews = definitions if v2 else {packet for packet in definitions if packet.startswith("P")}
        if required_reviews - set(reviews):
            label = "P/K/M" if v2 else "immediate"
            errors.append(f"missing {label} opportunity reviews: {sorted(required_reviews - set(reviews))}")
        fields = ("project_objective", "implementation_ref", "gap", "operational_change",
                  "benefit_direction", "owner", "execution_conditions", "closure_basis")
        for packet, review in reviews.items():
            if packet not in definitions and (v2 or f"**{packet} —" not in text):
                errors.append(f"opportunity review {packet!r} is not declared in the plan")
            if not isinstance(review, dict) or not all(_nonempty_text(review.get(f)) for f in fields):
                errors.append(f"{packet}: opportunity review requires nonempty text in {fields}")
                continue
            path = _handoff_path(review["owner"], root)
            if path is None or not (path.is_file() or path in proposed_owners):
                errors.append(f"{packet}: opportunity review owner does not resolve")

        if v2:
            return errors

        # Resolve task references from definitions, never from their own mentions
        # in the terminal table. Only declared owners are read; no corpus sweep.
        task_pattern = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?:\.[A-Za-z0-9]+)*"
        definition_pattern = rf"\*\*({task_pattern})(?=[ \t]*(?:—|:|\*\*))"
        task_definitions = set(re.findall(definition_pattern, text))
        owner_refs = [
            ref for patch in updates
            for ref in patch["handoffs_updated"] + patch["handoffs_created"]
        ] + [
            review["owner"] for review in reviews.values()
            if isinstance(review, dict) and _nonempty_text(review.get("owner"))
        ]
        for ref in set(owner_refs):
            path = _handoff_path(ref, root)
            if path is not None and path.is_file():
                task_definitions.update(re.findall(
                    definition_pattern, path.read_text(encoding="utf-8")))
        for stub in stubs:
            task_definitions.update(re.findall(definition_pattern, stub["content"]))
        for rid, terminal in recommendations.items():
            tasks = set(re.findall(rf"(?<![A-Za-z0-9-]){task_pattern}(?![A-Za-z0-9-])", terminal))
            missing = tasks - task_definitions
            if missing:
                errors.append(f"{rid}: undefined terminal task references {sorted(missing)}")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        errors.append(f"plan/session: unsupported format or unreadable input: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file", type=Path)
    parser.add_argument("--session-file", type=Path)
    args = parser.parse_args()
    if (args.plan_file is None) != (args.session_file is None):
        parser.error("--plan-file and --session-file must be supplied together")
    errors = []
    config = load_wiki_config()
    crossref_dirs = _get_crossref_dirs(config)

    # Validate taxonomy
    taxonomy_path = _get_taxonomy_path(config)
    if not taxonomy_path.exists():
        print(f"ERROR: Taxonomy not found at {taxonomy_path}")
        return 1
    taxonomy = load_yaml(taxonomy_path)
    errors.extend(validate_taxonomy(taxonomy))
    valid_categories = set(taxonomy.get("categories", {}).keys())

    # Load aliases from SCHEMA.md (extends valid categories without modifying taxonomy.yaml)
    aliases = _load_aliases(config)
    if aliases:
        # Add alias keys and their canonical targets to valid set
        valid_categories.update(aliases.keys())
        valid_categories.update(aliases.values())
        print(f"INFO: Loaded {len(aliases)} category aliases from SCHEMA.md")

    errors.extend(validate_cross_reference_map(CROSS_REFERENCE_MAP_PATH, crossref_dirs))

    # Validate index
    if not INDEX_PATH.exists():
        if args.plan_file is not None:
            errors.append("plan/session validation requires the intake index")
        print(f"WARNING: Index not found at {INDEX_PATH} — skipping index validation")
        if errors:
            for e in errors:
                print(f"  ERROR: {e}")
            return 1
        print("OK: Taxonomy valid, no index to validate")
        return 0

    dup_errors: list[str] = []
    data = load_yaml(INDEX_PATH, dup_errors=dup_errors)
    if dup_errors:
        shown = dup_errors[:20]
        for d in shown:
            errors.append(f"{INDEX_PATH.name}: {d}")
        if len(dup_errors) > len(shown):
            errors.append(
                f"{INDEX_PATH.name}: ... and {len(dup_errors) - len(shown)} more duplicate keys "
                "(a duplicate key is silently last-one-wins in YAML — the earlier value is lost)"
            )
    entries = data if isinstance(data, list) else data.get("entries", [])
    if not entries:
        print("WARNING: Index is empty")
    else:
        errors.extend(validate_index(entries, valid_categories, crossref_dirs))
        errors.extend(check_laundered_arxiv_ids(entries))
        errors.extend(check_merge_map(entries))
        for warning in check_duplicate_locators(entries):
            print(f"WARNING: {warning}")

    if args.plan_file is not None:
        try:
            session = json.loads(args.session_file.read_text(encoding="utf-8"),
                                 object_pairs_hook=_unique_json_object)
            errors.extend(validate_plan_payload(
                session, args.plan_file, entries, valid_categories, ROOT))
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"session-file: unreadable or unsupported JSON: {exc}")

    if errors:
        print(f"FAILED: {len(errors)} error(s) found:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"OK: Taxonomy valid, {len(entries)} index entries validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

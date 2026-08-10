#!/usr/bin/env python3
"""Validate the research intake index and taxonomy."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
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


_MERGED_RE = re.compile(r"\bMerged (intake-\d+)\b")


def _absorbed_ids(entries: list[dict]) -> set[str]:
    """Ids a surviving entry declares it absorbed, from its `merge_history` notes.

    Merging a duplicate away leaves a hole in the id sequence forever. Deriving the allowance from
    `merge_history` keeps the sequential check meaningful: a gap is forgiven only when some entry
    takes responsibility for it in writing.
    """
    out: set[str] = set()
    for entry in entries:
        for note in entry.get("merge_history") or []:
            out.update(_MERGED_RE.findall(str(note)))
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
                while f"intake-{expected}" in absorbed_ids:
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


def main() -> int:
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
        for warning in check_duplicate_locators(entries):
            print(f"WARNING: {warning}")

    if errors:
        print(f"FAILED: {len(errors)} error(s) found:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"OK: Taxonomy valid, {len(entries)} index entries validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

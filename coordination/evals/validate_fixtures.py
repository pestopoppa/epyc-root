#!/usr/bin/env python3
"""Validate labeled eval fixtures against fixtures/fixture.schema.json.

Stdlib only — no jsonschema dependency, so this runs anywhere the daemon runs.

Hard failures (exit 1):
  * a fixture missing `label_provenance`, or carrying a value outside the enum;
  * a PROMOTION-GATING fixture whose `label_provenance` is `ledger-narrative`
    (the ledger graded itself; it may seed few-shot prompts, never gate a
    promotion);
  * any other schema violation (missing required field, wrong type, bad enum,
    pattern mismatch, unknown property);
  * a duplicate `id`, or an `id` whose prefix disagrees with `decision`;
  * a `primary-artifact` fixture whose `evidence_ref` names a repo path that
    does not exist — a label claiming an artifact proves it must resolve.

Usage:
    python3 coordination/evals/validate_fixtures.py [--dir DIR] [--quiet]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
SCHEMA_PATH = os.path.join(HERE, "fixtures", "fixture.schema.json")

# Provenance classes whose labels may gate a classifier promotion.
PROMOTION_SAFE_PROVENANCE = frozenset({"primary-artifact", "operator"})

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
}

# Strip a trailing :LINE or :LINE-LINE locator from an evidence path.
_LINE_SUFFIX = re.compile(r":\d+(?:-\d+)?$")


def _check(schema, value, path, errors):
    """Recursively validate `value` against a draft-07 subset."""
    expected = schema.get("type")
    if expected:
        py = _TYPES.get(expected)
        # bool is a subclass of int; keep them distinct.
        if py is not None:
            bad = not isinstance(value, py)
            if expected in ("integer", "number") and isinstance(value, bool):
                bad = True
            if expected != "boolean" and py is bool:
                bad = not isinstance(value, bool)
            if bad:
                errors.append("%s: expected type %s, got %s"
                              % (path, expected, type(value).__name__))
                return

    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: %r not in enum %s" % (path, value, schema["enum"]))

    if isinstance(value, str):
        pattern = schema.get("pattern")
        if pattern and not re.search(pattern, value):
            errors.append("%s: %r does not match pattern %s" % (path, value, pattern))
        minlen = schema.get("minLength")
        if minlen is not None and len(value) < minlen:
            errors.append("%s: shorter than minLength %d" % (path, minlen))

    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append("%s: missing required field %r" % (path, key))
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append("%s: unknown property %r" % (path, key))
        for key, sub in props.items():
            if key in value:
                _check(sub, value[key], "%s.%s" % (path, key), errors)

    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _check(schema["items"], item, "%s[%d]" % (path, i), errors)


def _is_promotion_gating(fixture):
    """Default TRUE. Opting out is explicit, and that direction is deliberate.

    Defaulting a `ledger-narrative` fixture to non-gating would make the gate
    below vacuous: it could then only fire on a fixture whose author had
    already gone out of their way to set the flag. Fail closed instead — a
    ledger-narrative fixture must carry `"promotion_gating": false` and say in
    `notes` why no primary artifact was reachable.
    """
    if "promotion_gating" in fixture:
        return bool(fixture["promotion_gating"])
    return True


def _evidence_paths(ref):
    """Repo-relative path tokens inside an evidence_ref, minus :LINE suffixes.

    `evidence_ref` is prose that CONTAINS pointers; it is not itself a path. So
    tokens are extracted permissively and judged in two tiers by the caller:
    at least one must resolve, and a non-resolving token that carries a source
    file extension is reported as probable anchor rot.
    """
    out = []
    for token in re.split(r"[\s,;]+", ref or ""):
        token = token.strip().strip("`'\"()[]").rstrip(".,)")
        if not token or "/" not in token:
            continue
        # git rev syntax: `HEAD:path/to/file` names a blob, not a worktree path.
        rev, sep, rest = token.partition(":")
        if sep and "/" in rest and "/" not in rev:
            token = rest
        out.append(_LINE_SUFFIX.sub("", token))
    return out


# A non-resolving token with one of these suffixes is probable anchor rot, not prose.
_FILE_SUFFIXES = (".md", ".py", ".sh", ".json", ".jsonl", ".yaml", ".yml", ".html", ".txt")


def validate_dir(fixtures_dir, schema, quiet=False):
    errors = []
    warnings = []
    seen_ids = {}
    count = 0

    names = sorted(
        n for n in os.listdir(fixtures_dir)
        if n.endswith(".json") and n != "fixture.schema.json"
    )
    if not names:
        # An empty corpus must never pass silently as "all green".
        errors.append("%s: no fixture files found (an empty run is not a pass)"
                      % os.path.relpath(fixtures_dir, REPO_ROOT))

    for name in names:
        full = os.path.join(fixtures_dir, name)
        try:
            with open(full, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
        except (OSError, ValueError) as exc:
            errors.append("%s: unreadable/invalid JSON: %s" % (name, exc))
            continue

        items = loaded if isinstance(loaded, list) else [loaded]
        for idx, fixture in enumerate(items):
            count += 1
            where = "%s[%d]" % (name, idx) if isinstance(loaded, list) else name
            if not isinstance(fixture, dict):
                errors.append("%s: fixture is not an object" % where)
                continue

            _check(schema, fixture, where, errors)

            fid = fixture.get("id")
            prov = fixture.get("label_provenance")
            decision = fixture.get("decision")

            # --- the two mandated hard gates -----------------------------
            if prov is None:
                errors.append("%s: label_provenance is MANDATORY and absent" % where)
            elif _is_promotion_gating(fixture) and prov not in PROMOTION_SAFE_PROVENANCE:
                errors.append(
                    "%s (%s): promotion-gating fixture has label_provenance %r — "
                    "only %s may gate a classifier promotion"
                    % (where, fid, prov, sorted(PROMOTION_SAFE_PROVENANCE)))
            # -------------------------------------------------------------

            if isinstance(fid, str):
                if fid in seen_ids:
                    errors.append("%s: duplicate id %r (also in %s)"
                                  % (where, fid, seen_ids[fid]))
                seen_ids[fid] = where
                if isinstance(decision, str) and not fid.startswith(decision + "-"):
                    errors.append("%s: id %r does not carry its decision prefix %r"
                                  % (where, fid, decision))

            ref = fixture.get("evidence_ref")
            if prov == "primary-artifact" and isinstance(ref, str):
                paths = _evidence_paths(ref)
                resolved = [p for p in paths
                            if os.path.exists(os.path.join(REPO_ROOT, p))]
                if not resolved:
                    errors.append(
                        "%s (%s): primary-artifact fixture cites no artifact that "
                        "exists — evidence_ref %r resolves to nothing" % (where, fid, ref))
                for p in paths:
                    if p not in resolved and p.endswith(_FILE_SUFFIXES):
                        warnings.append("%s (%s): evidence_ref names a file that does "
                                        "not exist (anchor rot?): %s" % (where, fid, p))

            if prov == "ledger-narrative" and not (fixture.get("notes") or "").strip():
                warnings.append("%s (%s): ledger-narrative fixture must explain in "
                                "notes why no primary artifact was reachable" % (where, fid))

    if not quiet:
        print("fixtures checked: %d (in %d file(s))" % (count, len(names)))
        for fid, where in sorted(seen_ids.items()):
            print("  %-24s %s" % (fid, where))
    for w in warnings:
        print("WARN  %s" % w)
    for e in errors:
        print("FAIL  %s" % e)

    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.join(HERE, "fixtures"),
                    help="fixtures directory (default: %(default)s)")
    ap.add_argument("--quiet", action="store_true", help="errors and warnings only")
    args = ap.parse_args()

    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
    except (OSError, ValueError) as exc:
        print("FAIL  cannot load schema %s: %s" % (SCHEMA_PATH, exc))
        return 2

    errors = validate_dir(args.dir, schema, quiet=args.quiet)
    if errors:
        print("\nRESULT: FAIL (%d error(s))" % len(errors))
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

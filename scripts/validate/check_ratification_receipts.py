#!/usr/bin/env python3
"""Fail when a script amends the measurement trust boundary without a receipt.

WHY THIS EXISTS
---------------
`MEASUREMENT.md` §5 requires the human to sign ONCE, at apply time, over a
consolidated bundle: protocol + evidence hashes + validation results + exact
state diff. Every 2026-07 ratification amended the constitution and emitted no
such bundle; each verified instead that its own edit had ARRIVED. One of them
tore a wrapped bullet in §3 in half and its grep-for-my-marker check passed.

Fixing those scripts one by one closes those instances. This closes the CLASS:
any script that writes a trust-boundary artifact must also emit a receipt, and a
new one that does not is caught the first time this runs.

DERIVED, NOT RESTATED
---------------------
The boundary is read from `coordination/session-bus/human_only_paths.yaml` —
the same human-amendment-only list the PreToolUse hook enforces — so a path added
there is covered here automatically, with nobody needing to remember. A
hand-maintained second copy is exactly the defect this repository has already
been bitten by twice (`REQUIRED_SOURCE_ARTIFACTS` 9 emitted / 7 checked, and the
`device` field absent from runtime attestation). The list itself and its .sha256
pin are inside the boundary too (the hook guards them by name, not by glob), so
they are added implicitly: the file that DEFINES the boundary is the last one an
unreceipted script should be able to rewrite.

HOW A SCRIPT IS CLASSIFIED AS BOUNDARY-WRITING (any one suffices)
-----------------------------------------------------------------
  patch     a `.patch`/`.diff` file the script references has a `+++ b/<path>`
            (or `diff --git`) header matching a boundary glob, and the script
            writes files. STRUCTURAL: it holds however the script spells or
            builds the path to the patch or to the target.
  declared  a `# ratify-targets: <path> [<path> ...]` line in the script. For
            targets built at runtime that no static reading can resolve.
            Declarations only ever WIDEN the classification; there is no
            opt-out.
  text      the script, with comment lines stripped and quoting/path-joining
            normalised away, names a boundary path AND contains any file-write
            idiom (redirect, tee, cp/mv/install, sed -i, open(..., "w"), ...).

Until 2026-09-26 only the third rule existed, and its write idioms were keyed to
LITERAL spellings (`open("x.md", "w")`, `> $ROOT/MEASUREMENT`, `cp ... $ROOT/
MEASUREMENT`). A script that wrote through a variable — `open(path, "w")`,
`cp "$MERGED" "$REPO_ROOT/$TARGET"`, `cat > "$ANNEX"` — escaped it silently.
The receipt idiom had the mirror defect: `"$ROOT/.../ratification_receipt.py"
emit` has a quote between `.py` and `emit`, so a script that DID emit the §5
receipt was reported as failing to. And the default `--repo-root` was the literal
`/workspace`, so running the checker from any other worktree silently scanned a
different, possibly stale checkout, untracked files included.

A script that emits no receipt itself but runs a scanned script that does (a
`run_*` wrapper) is PASS by delegation.

HISTORICAL EXEMPTIONS
---------------------
Ratifications executed before their script was compliant are NOT rewritten to
pretend they emitted a receipt: §5 has no backfill clause, and the human signed
what they signed. They are listed in `ratification_receipt_exemptions.json`
beside this file. Every entry is pinned to the script's sha256 — edit an exempted
script and its exemption lapses, so the edit must add a receipt — and carries a
reason. Three kinds, each verified, never taken on trust:
  historical            `applied_in` is an ancestor of HEAD, touches a boundary
                        path the script is classified as writing, and the
                        script is in the tree at that commit — or, for a
                        parallel-lane or hand-applied case, `script_committed_in`
                        adds it, is in history, and is within 48 h of it.
  superseded            never run; `superseded_by` names a successor that is
                        itself receipted or exempt.
  not-a-boundary-write  a reviewed false positive of the heuristic TEXT rule
                        (it names a boundary path and writes something else).
                        Refused when the classification is structural (patch
                        or declared).
An exemption that matches no unreceipted boundary-writing script is an error.
The list is meant to be human-only: once it is, adding an entry is an operator
act, like every other change to what the boundary lets through.

THREE OUTCOMES
--------------
PASS / FAIL / COULD-NOT-CHECK. If the boundary list cannot be read, that is
COULD-NOT-CHECK and exits non-zero — it is NOT "no violations found".
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BOUNDARY_REL = "coordination/session-bus/human_only_paths.yaml"
BOUNDARY_PIN_REL = "coordination/session-bus/human_only_paths.sha256"
EXEMPTIONS_REL = "scripts/validate/ratification_receipt_exemptions.json"
SCAN_GLOBS = (
    "artifacts/**/*.sh",
    "artifacts/**/*.py",
    "scripts/operator/**/*.sh",
    "scripts/operator/**/*.py",
    "scripts/**/ratify_*.sh",
    "scripts/**/ratify_*.py",
)
# Consolidated receipts are written to receipts/ (the original convention) and,
# since receipts/ became the keyed-index namespace, beside the decision receipt.
RECEIPT_GLOBS = ("artifacts/operator/receipts/*.receipt.json", "artifacts/operator/*.receipt.json")
SKIP_NAMES = ("ratify_receipt.sh", "ratification_receipt.py", "check_ratification_receipts.py")

# Idioms that WRITE a file, matched on comment-stripped text. Deliberately broad:
# a false positive costs a reviewer one look, a false negative is an unreceipted
# amendment of the constitution.
WRITE_IDIOMS = (
    re.compile(r"\bgit\b[^\n|;&]*?\sapply\b"),
    re.compile(r"(?:^|[\s;&|(])patch\s+(?:-|<|\S+\s+<)", re.M),
    re.compile(r"""\bopen\([^)\n]*?,\s*(?:mode\s*=\s*)?["'](?:[wax]|r\+)"""),
    re.compile(r"\.write_(?:text|bytes)\("),
    re.compile(r"\b(?:shutil\.(?:copy\w*|move)|os\.(?:replace|rename))\("),
    re.compile(r"^\s*edit\(", re.M),
    re.compile(r"\bsed\s+(?:-\w+\s+)*-i"),
    re.compile(r"\bperl\s+-\w*i"),
    re.compile(r"\btee\b"),
    re.compile(r"(?:^|[\s;&|(])(?:cp|mv|install|rsync|ln)\s", re.M),
    # A redirect into a file: not `2>/dev/null`, not `>&2`, not `->`/`=>`/`>=`.
    re.compile(r"""(?<![0-9&=<>\-])>{1,2}[ \t]*(?![&=>]|/dev/)["']?[$\w./{]"""),
)
RECEIPT_IDIOMS = (
    re.compile(r"(?<![\w.])receipt_emit\b(?!\s*\(\))"),
    re.compile(r"ratification_receipt\.py\s+emit\b"),
)
DECLARED_RE = re.compile(r"^\s*#\s*ratify-targets:\s*(.+)$", re.M)
PATCH_REF_RE = re.compile(r"[\w$.{}/-]*[\w-]\.(?:patch|diff)\b")
DIFF_TARGET_RE = re.compile(r"^(?:\+\+\+ b/(\S+)|--- a/(\S+)|diff --git a/(\S+) b/(\S+))", re.M)
TOOL_ASSIGN_RE = re.compile(r"\b(\w+)=\S*ratification_receipt\.py\b")
_JOIN_CALL_RE = re.compile(r"\b(?:os\.path\.join|joinpath|PurePath|Path)\(([^()\n]*)\)")

PASS, FAIL, COULD_NOT_CHECK, EXEMPT = "PASS", "FAIL", "COULD-NOT-CHECK", "EXEMPT"


def boundary_tokens(path: Path) -> tuple[list[str], list[str]]:
    """Return (globs, errors) for the epyc-root half of the trust boundary."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [], [
            f"{COULD_NOT_CHECK}: trust-boundary list {path} is unreadable ({exc}); "
            "no script could be classified, so a clean result here would be a lie"
        ]
    if not isinstance(doc, dict) or not isinstance(doc.get("paths"), list):
        return [], [
            f"{COULD_NOT_CHECK}: trust-boundary list {path} has no 'paths' list; "
            "nothing could be derived"
        ]
    globs = [
        str(entry["glob"])
        for entry in doc["paths"]
        if isinstance(entry, dict)
        and entry.get("repo") == "epyc-root"
        and isinstance(entry.get("glob"), str)
    ]
    if not globs:
        return [], [
            f"{COULD_NOT_CHECK}: trust-boundary list {path} declares no epyc-root paths"
        ]
    for implicit in (BOUNDARY_REL, BOUNDARY_PIN_REL):
        if implicit not in globs:
            globs.append(implicit)
    return globs, []


# ------------------------------------------------------------------ text model


def strip_comments(text: str) -> str:
    """Drop whole-line `#` comments (shell and Python), shebang included.

    A path named only in a comment is documentation, not a write target. Inline
    trailing comments are kept: stripping them safely needs a real parser, and
    keeping them can only over-classify, never under-classify.
    """
    return "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("#"))


def normalise(text: str) -> str:
    """Erase quoting and path-building so every spelling of a path reads alike.

    `"$ROOT"/"MEASUREMENT.md"`, `"${REPO_ROOT}/measurement/protocols/x.md"`,
    `ROOT / "measurement" / "protocols"` and `os.path.join("agents", "shared")`
    all normalise to a contiguous `a/b/c` spelling.
    """
    text = _JOIN_CALL_RE.sub(lambda m: "/".join(p.strip() for p in m.group(1).split(",")), text)
    text = text.replace('"', "").replace("'", "").replace("`", "")
    return re.sub(r"[ \t]*/[ \t]*", "/", text)


def glob_hits(candidate: str, globs: list[str]) -> list[str]:
    candidate = re.sub(r"^\./", "", candidate)
    return [g for g in globs if fnmatch.fnmatchcase(candidate, g)]


def mentions_boundary(text: str, globs: list[str]) -> list[str]:
    hits = []
    for glob in globs:
        if "*" in glob:
            prefix = glob.split("*")[0]
            if prefix and prefix in text:
                hits.append(glob)
        elif glob in text or Path(glob).name in text:
            hits.append(glob)
    return hits


def patch_targets(
    code: str, script: Path, repo_root: Path, globs: list[str]
) -> tuple[list[str], list[str], list[str]]:
    """(boundary globs hit, patch files read, patch references that did not resolve)."""
    hits: set[str] = set()
    read: list[str] = []
    unresolved: list[str] = []
    for ref in sorted(set(PATCH_REF_RE.findall(normalise(code)))):
        rel = re.sub(r"^(?:\$\{?\w+\}?/)+", "", ref)  # drop $ROOT/, ${REPO_ROOT}/, ...
        if "$" in rel or "{" in rel:
            unresolved.append(ref)
            continue
        found = None
        for base in (repo_root, script.parent):
            cand = Path(rel) if rel.startswith("/") else base / rel
            if cand.is_file():
                found = cand
                break
        if found is None:
            unresolved.append(ref)
            continue
        body = found.read_text(encoding="utf-8", errors="replace")
        read.append(str(found.relative_to(repo_root)) if found.is_relative_to(repo_root) else str(found))
        for match in DIFF_TARGET_RE.finditer(body):
            for path in filter(None, match.groups()):
                hits.update(glob_hits(path, globs))
    return sorted(hits), read, unresolved


def declared_targets(text: str, globs: list[str]) -> list[str]:
    hits: set[str] = set()
    for line in DECLARED_RE.findall(text):
        for token in line.split():
            hits.update(glob_hits(token, globs))
    return sorted(hits)


def emits_receipt(text: str) -> bool:
    code = normalise(strip_comments(text))
    if any(rx.search(code) for rx in RECEIPT_IDIOMS):
        return True
    # Indirection: R=scripts/operator/ratification_receipt.py ; python3 $R emit
    for var in set(TOOL_ASSIGN_RE.findall(code)):
        if re.search(rf"\$\{{?{re.escape(var)}\}}?\s+emit\b", code):
            return True
    return False


def writes_files(text: str) -> bool:
    code = strip_comments(text)
    return any(rx.search(code) for rx in WRITE_IDIOMS)


# ------------------------------------------------------------------ exemptions


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True)


def load_exemptions(path: Path) -> tuple[dict[str, dict], list[str]]:
    if not path.exists():
        return {}, []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return {e["script"]: e for e in doc["exemptions"]}, []
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {}, [f"{COULD_NOT_CHECK}: exemption list {path} is unreadable ({exc})"]


EXEMPTION_KINDS = ("historical", "superseded", "not-a-boundary-write")


def verify_exemption(
    entry: dict, finding: dict, repo_root: Path, globs: list[str], verdicts: dict[str, str]
) -> str | None:
    """Return None when the exemption holds, else the reason it does not."""
    script = finding["script"]
    digest = hashlib.sha256((repo_root / script).read_bytes()).hexdigest()
    if digest != entry.get("script_sha256"):
        return (
            f"script changed since it was exempted (sha256 {digest[:12]} != pinned "
            f"{str(entry.get('script_sha256'))[:12]}); an edited ratifier must emit the receipt"
        )
    if not str(entry.get("reason", "")).strip():
        return "an exemption without a stated reason is not auditable"
    kind = entry.get("kind")
    if kind == "not-a-boundary-write":
        # Only the heuristic text rule can be overruled. A patch header or a
        # declaration naming a boundary path is structural and stands.
        if finding["classified_via"] != ["text"]:
            return (f"classified via {'+'.join(finding['classified_via'])}, which is structural; "
                    "only a text-only classification can be declared a non-write")
        return None
    if kind == "superseded":
        successor = str(entry.get("superseded_by", ""))
        if not (repo_root / successor).is_file():
            return f"superseded_by {successor!r} does not exist"
        if verdicts.get(successor) not in (PASS, EXEMPT):
            return f"superseded_by {successor} is not itself receipted or exempt"
        return None
    if kind != "historical":
        return f"unknown exemption kind {kind!r}; expected one of {EXEMPTION_KINDS}"
    commit = str(entry.get("applied_in", ""))
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        return f"applied_in {commit!r} is not a commit id"
    if _git(repo_root, "merge-base", "--is-ancestor", commit, "HEAD").returncode != 0:
        return f"applied_in {commit} is not an ancestor of HEAD"
    touched = _git(repo_root, "show", "--name-only", "--format=", commit).stdout.split()
    if not any(set(glob_hits(p, globs)) & set(finding["boundary_paths"]) for p in touched):
        return f"applied_in {commit} touches none of {finding['boundary_paths']}, so it is not the application"
    if _git(repo_root, "cat-file", "-e", f"{commit}:{script}").returncode == 0:
        return None
    # Parallel lanes (v10 freeze, AK-SEARCH-1-A3) and hand-applied amendments
    # recorded as a script minutes later (Prove2Me) put the script in a sibling
    # or child commit. Accept that only when the entry names the commit that
    # ADDED the script, it is in history, and it is within 48 h of applied_in.
    added = str(entry.get("script_committed_in", ""))
    if not re.fullmatch(r"[0-9a-f]{7,40}", added):
        return (f"{script} is not in the tree at applied_in {commit}; name the commit that "
                "added it as script_committed_in")
    if _git(repo_root, "merge-base", "--is-ancestor", added, "HEAD").returncode != 0:
        return f"script_committed_in {added} is not an ancestor of HEAD"
    if script not in _git(repo_root, "show", "--diff-filter=A", "--name-only", "--format=", added).stdout.split():
        return f"script_committed_in {added} does not add {script}"
    stamps = [_git(repo_root, "show", "-s", "--format=%ct", c).stdout.strip() for c in (commit, added)]
    if not all(t.isdigit() for t in stamps) or abs(int(stamps[0]) - int(stamps[1])) > 48 * 3600:
        return f"script_committed_in {added} is not within 48 h of applied_in {commit}"
    return None


# ------------------------------------------------------------------ scan


def classify(path: Path, text: str, repo_root: Path, globs: list[str]) -> dict | None:
    code = strip_comments(text)
    writes = writes_files(text)
    via: dict[str, list[str]] = {}
    p_hits, p_read, p_unresolved = patch_targets(code, path, repo_root, globs)
    if p_hits and writes:
        via["patch"] = p_hits
    d_hits = declared_targets(text, globs)
    if d_hits:
        via["declared"] = d_hits
    t_hits = mentions_boundary(normalise(code), globs)
    if t_hits and writes:
        via["text"] = t_hits
    if not via:
        return None
    return {
        "script": str(path.relative_to(repo_root)),
        "boundary_paths": sorted({g for hits in via.values() for g in hits}),
        "classified_via": sorted(via),
        "patches_read": p_read,
        "patches_unresolved": p_unresolved,
        "emits_receipt": emits_receipt(text),
        "verdict": None,
    }


def scan(
    repo_root: Path, globs: list[str], exemptions: dict[str, dict] | None = None
) -> tuple[list[dict], list[str]]:
    exemptions = exemptions or {}
    findings: list[dict] = []
    errors: list[str] = []
    texts: dict[str, str] = {}
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            if path.name in SKIP_NAMES:
                continue
            if any(fnmatch.fnmatch(str(path), f"*{s}*") for s in ("/receipts/", "/__pycache__/")):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                errors.append(f"{COULD_NOT_CHECK}: could not read {path}: {exc}")
                continue
            finding = classify(path, text, repo_root, globs)
            if finding is not None:
                texts[finding["script"]] = text
                findings.append(finding)

    # Verdicts after the whole set is known, so delegation can resolve.
    direct = {f["script"] for f in findings if f["emits_receipt"]}
    for f in findings:
        if f["emits_receipt"]:
            f["verdict"] = PASS
            continue
        code = strip_comments(texts[f["script"]])
        delegates = sorted(s for s in direct if s != f["script"] and Path(s).name in code)
        if delegates:
            f["verdict"] = PASS
            f["delegated_to"] = delegates
            continue
        f["verdict"] = FAIL
    # Exemptions last, superseded ones after the rest: a superseded script is
    # excused only by a successor that is itself receipted or exempt.
    order = sorted(findings, key=lambda f: exemptions.get(f["script"], {}).get("kind") == "superseded")
    for f in order:
        entry = exemptions.get(f["script"])
        if f["verdict"] != FAIL or entry is None:
            continue
        verdicts = {g["script"]: g["verdict"] for g in findings}
        problem = verify_exemption(entry, f, repo_root, globs, verdicts)
        if problem is None:
            f["verdict"] = EXEMPT
            f["exemption"] = {k: entry[k] for k in
                              ("kind", "applied_in", "script_committed_in", "superseded_by", "evidence", "reason") if k in entry}
        else:
            f["exemption_lapsed"] = problem
    for script in sorted(set(exemptions) - {f["script"] for f in findings if f["verdict"] == EXEMPT}
                         - {f["script"] for f in findings if f.get("exemption_lapsed")}):
        errors.append(
            f"exemption for {script} matches no unreceipted boundary-writing script; "
            "remove the stale entry"
        )
    return findings, errors


# ------------------------------------------------------------------ receipts


def check_receipts(repo_root: Path, directory: Path | None = None) -> tuple[list[dict], list[str]]:
    """Every consolidated receipt must be RATIFIED, unless it is a preserved refusal.

    A ratify script that gets REFUSED rolls the amendment back and keeps the
    receipt as `<name>.refused-<stamp>.receipt.json` for reading. That file is an
    audit record of an attempt that did NOT ratify, not a ratification: it is an
    error only at a canonical (non-`.refused-`) name, where it would be read as
    the ratification itself.
    """
    receipts: list[dict] = []
    errors: list[str] = []
    paths: set[Path] = set()
    if directory is not None:
        paths.update(directory.glob("*.receipt.json"))
    else:
        for pattern in RECEIPT_GLOBS:
            paths.update(repo_root.glob(pattern))
    for path in sorted(paths):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{COULD_NOT_CHECK}: receipt {path.name} is unreadable ({exc})")
            continue
        receipts.append(
            {
                "receipt": str(path.relative_to(repo_root)) if path.is_relative_to(repo_root) else path.name,
                "ratification_id": doc.get("ratification_id"),
                "protocol_id": doc.get("protocol_id"),
                "verdict": doc.get("verdict"),
                "emitted_at_utc": doc.get("emitted_at_utc") or doc.get("generated_at"),
                "preserved_refusal": ".refused-" in path.name,
            }
        )
    ratified_at: dict[str, list[str]] = {}
    for r in receipts:
        if r["verdict"] == "RATIFIED":
            ratified_at.setdefault(r["ratification_id"], []).append(r["emitted_at_utc"] or "")
    for r in receipts:
        if r["verdict"] == "RATIFIED":
            continue
        if r["preserved_refusal"]:
            later = [t for t in ratified_at.get(r["ratification_id"], []) if t > (r["emitted_at_utc"] or "")]
            r["status"] = "superseded by a later RATIFIED receipt" if later else "not ratified"
            continue
        errors.append(
            f"receipt {r['receipt']} carries verdict {r['verdict']!r} at a canonical name; a "
            "ratification whose own receipt is not RATIFIED must not be treated as ratified "
            "(a rolled-back attempt is kept as <name>.refused-<stamp>.receipt.json)"
        )
    return receipts, errors


# ------------------------------------------------------------------ main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT,
                        help="checkout to scan (default: the one this file lives in)")
    parser.add_argument("--boundary-list", type=Path, default=None)
    parser.add_argument("--receipt-dir", type=Path, default=None,
                        help="read receipts from this directory only (default: every receipt location)")
    parser.add_argument("--exemptions", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    boundary_list = args.boundary_list or repo_root / BOUNDARY_REL
    exemptions_path = args.exemptions or repo_root / EXEMPTIONS_REL

    globs, errors = boundary_tokens(boundary_list)
    exemptions, ex_errors = load_exemptions(exemptions_path)
    errors.extend(ex_errors)
    findings, scan_errors = ([], []) if not globs else scan(repo_root, globs, exemptions)
    errors.extend(scan_errors)
    receipts, receipt_errors = check_receipts(repo_root, args.receipt_dir)
    errors.extend(receipt_errors)

    missing = [f for f in findings if f["verdict"] == FAIL]
    # Reported, not failed: the list becomes human-only by operator ratification,
    # and until then this line says plainly that an agent could still widen it.
    protected = bool(glob_hits(EXEMPTIONS_REL, globs))
    if args.json:
        print(json.dumps({"repo_root": str(repo_root), "boundary_globs": globs, "scripts": findings,
                          "receipts": receipts, "errors": errors,
                          "exemption_list_protected": protected}, indent=2, sort_keys=True))
    else:
        print(f"repo root: {repo_root}")
        print(f"trust-boundary globs (derived from {boundary_list.name}): {globs}")
        for f in findings:
            extra = ""
            if f.get("delegated_to"):
                extra = f"  [delegates to {', '.join(f['delegated_to'])}]"
            elif f["verdict"] == EXEMPT:
                ex = f["exemption"]
                detail = {"historical": f"applied in {ex.get('applied_in')}",
                          "superseded": f"superseded by {ex.get('superseded_by')}",
                          "not-a-boundary-write": "reviewed: mentions, does not write"}.get(ex.get("kind"), "")
                extra = f"  [{ex.get('kind')}: {detail}]"
            elif f.get("exemption_lapsed"):
                extra = f"  [exemption lapsed: {f['exemption_lapsed']}]"
            print(f"  [{f['verdict']:>17s}] {f['script']}  -> {', '.join(f['boundary_paths'])}"
                  f"  (via {'+'.join(f['classified_via'])}){extra}")
        for r in receipts:
            note = f"  [preserved refusal: {r['status']}]" if r["preserved_refusal"] else ""
            print(f"  receipt {r['verdict']!s:<10s} {r['ratification_id']} ({r['protocol_id']}){note}")
        for e in errors:
            print(f"  ! {e}")
        if exemptions and not protected:
            print(f"  NOTE: {EXEMPTIONS_REL} is not in {boundary_list.name}, so an agent can still "
                  "add an exemption; it becomes human-only when the operator ratifies that")
        counts = {v: sum(1 for f in findings if f["verdict"] == v) for v in (PASS, EXEMPT, FAIL)}
        print(f"\n{len(findings)} boundary-amending script(s): {counts[PASS]} receipted, "
              f"{counts[EXEMPT]} exempt, {counts[FAIL]} failing.")
        if missing:
            print(f"FAIL: {len(missing)} script(s) amend the measurement trust boundary "
                  "without emitting the MEASUREMENT.md §5 consolidated receipt.")
        elif errors:
            print(f"{COULD_NOT_CHECK}: {len(errors)} condition(s) could not be evaluated.")
        else:
            print("OK")

    if missing:
        return 1
    if errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

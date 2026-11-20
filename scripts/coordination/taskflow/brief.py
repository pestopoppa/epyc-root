#!/usr/bin/env python3
"""taskflow/brief.py — task briefs (`epyc.brief.v1`, docs/design/task-brief-layer.md §2/§4, stage P1).

A brief is a typed SIDECAR to one handoff box: `handoffs/active/briefs/<ID>.md`, a YAML front-matter block.

    ---
    schema: epyc.brief.v1
    id: TU-GR-1
    box_text_sha: 0123456789abcdef      # box_index.text_sha of the box's first line when the brief was written
    author: owner                        # intake|planning|wrap-up|owner|coordinator|self
    written: 2026-11-20
    accepted: owner                      # owner|auto|pending|rejected
    review: backfill                     # only on author=self (amendment 2026-11-20): flagged for backfill review
    where:                               # repo-qualified; optional @rev; optional ::symbol
      - epyc-root:scripts/handoffs/box_index.py::text_sha
    approach: |                          # <= 5 lines: the decision, not a plan
      ...
    acceptance: "pytest -q tests/x.py::test_y"   # the RUNNABLE form of the box's done-when, never a second target
    non_goals: [ "do not change routing weights" ]
    tier: local                          # local|luna|terra|sol
    grounded: {at: <date>, blobs: {<where-path>: <blob sha>}}   # written by `write`/`accept` only
    ---

The brief never alters box identity: the box text stays identity (HS §2.2), the brief is guidance.

COMPILE (deterministic, zero LLM tokens) -> state:
  none      no sidecar for the box
  orphaned  box_text_sha != the box's current text_sha, or the box is gone / its ID is ambiguous
  stale     some check failed (path missing, symbol missing, acceptance dry check failed, schema invalid)
  drift     every check passed but a where-file's blob changed since `grounded`
  fresh     every check passed and the where-files match `grounded` (or nothing was grounded)
Checks: path existence (filesystem at HEAD, `git cat-file -e rev:path` for `@rev`); `::symbol` via `gitnexus context`
(skipped when `gitnexus status` says stale or the CLI is unavailable -> plain grep in the named file, marked `weak`);
acceptance dry check (pytest `--collect-only -q`, `bash -n`, `python3 -m py_compile`; anything else is parsed only).
Nothing runs for real. CACHE key = (box text_sha, brief sha, content hashes of the named files) — HEAD is deliberately
not in it. The cache is `handoffs/active/briefs/.compile-cache.json` (gitignored).

CLI:
  brief.py compile <ID> [--json] [--no-cache]        exit 0 fresh/drift, 1 stale/orphaned, 2 none
  brief.py write <ID> --where W [W ...] --approach TEXT --acceptance CMD [--non-goal NG ...] [--tier T]
                 [--author A] [--accepted A] [--json]   write/replace the sidecar (grounded + box_text_sha filled in),
                                                        then compile; exit as compile
  brief.py accept <ID> [--by owner]                   accepted: <by>, clears `review`, re-grounds
  brief.py reject <ID> [--by owner]                   accepted: rejected
  brief.py sweep [--json] [--stale-list]              compile every sidecar; --stale-list prints only non-fresh
                                                        briefs with their failing items (the nightly zero-token sweep)
P3-P5 hooks: `compile()` returns `stale_list` (worker `## STALE` section), `acceptance_matches_done_when` (D3
accepted:auto), `inputs_ext` (cross-repo/@rev packaging), and `blast_radius` (gitnexus impact, when available).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA = "epyc.brief.v1"
REPO_ROOT = Path(__file__).resolve().parents[3]
BRIEF_DIR = "handoffs/active/briefs"
CACHE_REL = f"{BRIEF_DIR}/.compile-cache.json"
BOX_DIRS = ("handoffs/active", "handoffs/blocked")
STATES = ("none", "fresh", "drift", "stale", "orphaned")
REQUIRED = ("schema", "id", "box_text_sha", "where", "approach", "acceptance", "non_goals", "tier")
AUTHORS = ("intake", "planning", "wrap-up", "owner", "coordinator", "self")
ACCEPTED = ("owner", "auto", "pending", "rejected")
TIERS = ("local", "luna", "terra", "sol")
APPROACH_MAX_LINES = 5
REPOS = {"epyc-root": None,  # None = the root the brief lives in
         "epyc-orchestrator": Path("/mnt/raid0/llm/epyc-orchestrator"),
         "epyc-inference-research": Path("/mnt/raid0/llm/epyc-inference-research"),
         "epyc-web": Path("/mnt/raid0/llm/epyc-web"),
         "epyc-llama": Path("/mnt/raid0/llm/llama.cpp")}
GITNEXUS_ENV = "EPYC_BRIEF_GITNEXUS"     # path to the gitnexus binary ("" or missing -> unavailable -> weak)
_WHERE = re.compile(r"^(?:(?P<repo>[A-Za-z0-9_.-]+):)?(?P<path>[^@:]+?)(?:@(?P<rev>[0-9A-Za-z_./-]+))?"
                    r"(?:::(?P<sym>[A-Za-z_][A-Za-z0-9_.]*))?$")


def _handoff_libs():
    p = str(REPO_ROOT / "scripts" / "handoffs")
    if p not in sys.path:
        sys.path.insert(0, p)
    import box_index  # noqa: PLC0415 — lazy: box_index imports task_lint, which lazily imports this module
    import task_lint
    import task_lint_core
    return box_index, task_lint, task_lint_core


# ------------------------------------------------------------------------------------------------- parse / render
def brief_path(root: Path, bid: str) -> Path:
    return Path(root) / BRIEF_DIR / f"{bid}.md"


def parse_text(text: str) -> dict:
    """Front-matter YAML -> dict (raises ValueError on a malformed sidecar). The prose body, if any, is `_body`."""
    import yaml
    if not text.startswith("---"):
        raise ValueError("no YAML front matter")
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        raise ValueError("unterminated front matter")
    doc = yaml.safe_load(parts[0][3:]) or {}
    if not isinstance(doc, dict):
        raise ValueError("front matter is not a mapping")
    body = parts[1].split("\n", 1)[1] if "\n" in parts[1] else ""
    doc["_body"] = body.strip()
    return doc


def render(doc: dict) -> str:
    import yaml
    order = ("schema", "id", "box_text_sha", "author", "written", "accepted", "review", "where", "approach",
             "acceptance", "non_goals", "tier", "grounded")
    d = {k: doc[k] for k in order if k in doc and doc[k] is not None}
    d.update({k: v for k, v in doc.items() if k not in d and not k.startswith("_") and v is not None})
    return "---\n" + yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=120) + "---\n"


def schema_errors(doc: dict) -> list[str]:
    errs = [f"missing key `{k}`" for k in REQUIRED if k not in doc or (doc[k] in (None, "") and k != "non_goals")]
    if doc.get("schema") not in (None, SCHEMA):
        errs.append(f"schema is {doc.get('schema')!r}, want {SCHEMA}")
    if "where" in doc and not (isinstance(doc["where"], list) and doc["where"]):
        errs.append("`where` must be a non-empty list")
    if "non_goals" in doc and not isinstance(doc["non_goals"], list):
        errs.append("`non_goals` must be a list")
    if doc.get("tier") and doc["tier"] not in TIERS:
        errs.append(f"`tier` must be one of {TIERS}")
    if doc.get("author") and doc["author"] not in AUTHORS:
        errs.append(f"`author` must be one of {AUTHORS}")
    if doc.get("accepted") and doc["accepted"] not in ACCEPTED:
        errs.append(f"`accepted` must be one of {ACCEPTED}")
    if isinstance(doc.get("approach"), str) and len(doc["approach"].strip().split("\n")) > APPROACH_MAX_LINES:
        errs.append(f"`approach` exceeds {APPROACH_MAX_LINES} lines")
    for w in doc.get("where") or []:
        if not isinstance(w, str) or not _WHERE.match(w.strip()):
            errs.append(f"bad where entry {w!r}")
    return errs


# ------------------------------------------------------------------------------------------------- box lookup
def find_box(root: Path, bid: str) -> dict | None:
    """The OPEN box with this ID in handoffs/{active,blocked}: {file, line, text_sha, done_when, n}. n>1 = ambiguous."""
    BI, TL, L1 = _handoff_libs()
    hits = []
    for d in BOX_DIRS:
        base = Path(root) / d
        for p in sorted(base.glob("*.md")) if base.exists() else []:
            lines = p.read_text(encoding="utf-8", errors="replace").split("\n")
            fenced = L1.fenced_lines(lines)
            for i, line in enumerate(lines):
                if i in fenced or L1.head_id(line) != bid:
                    continue
                m = L1.CHECKBOX.match(line)
                if not m or m.group(2) in "xX":
                    continue
                txt, ch = L1.block(lines, i)
                f = TL.parse_fields(txt)
                hits.append({"file": str(p.relative_to(root)), "line": i + 1, "text_sha": BI.text_sha(line),
                             "done_when": f.get("done when"), "brief_ref": f.get("brief")})
    if not hits:
        return None
    return {**hits[0], "n": len(hits)}


# ------------------------------------------------------------------------------------------------- where checks
def parse_where(w: str) -> dict:
    m = _WHERE.match(w.strip())
    if not m:
        return {"raw": w, "repo": None, "path": w, "rev": None, "sym": None}
    return {"raw": w, "repo": m.group("repo") or "epyc-root", "path": m.group("path"), "rev": m.group("rev"),
            "sym": m.group("sym")}


def repo_dir(root: Path, repo: str) -> Path | None:
    if repo in (None, "epyc-root"):
        return Path(root)
    for cand in (Path(root) / "repos" / repo, REPOS.get(repo)):
        if cand is not None and Path(cand).exists():
            return Path(cand)
    return None


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env, timeout=60)


def blob_sha(rdir: Path, path: str, rev: str | None) -> str | None:
    """Content hash of a where-file: git blob sha (same as `git hash-object`), or None when it does not exist."""
    if rev:
        r = _git(rdir, "rev-parse", "--verify", "-q", f"{rev}:{path}")
        return r.stdout.strip() or None if r.returncode == 0 else None
    p = rdir / path
    if not p.is_file():
        return None
    data = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


_GN_STATUS: dict[str, str] = {}


def gitnexus_bin() -> str | None:
    if GITNEXUS_ENV in os.environ:
        b = os.environ[GITNEXUS_ENV]
        return b if b and (os.path.isfile(b) or shutil.which(b)) else None
    return shutil.which("gitnexus")


def gitnexus_state(rdir: Path) -> str:
    """'ok' | 'stale' | 'unavailable' for the repo (cached per process)."""
    key = str(rdir)
    if key in _GN_STATUS:
        return _GN_STATUS[key]
    b = gitnexus_bin()
    st = "unavailable"
    if b:
        try:
            r = subprocess.run([b, "status"], cwd=rdir, capture_output=True, text=True, timeout=30)
            out = (r.stdout + r.stderr).lower()
            st = ("stale" if "stale" in out else
                  "unavailable" if r.returncode != 0 or "no indexed" in out or "not indexed" in out else "ok")
        except (OSError, subprocess.SubprocessError):
            st = "unavailable"
    _GN_STATUS[key] = st
    return st


def _grep_symbol(rdir: Path, path: str, rev: str | None, sym: str) -> bool:
    name = sym.split(".")[-1]
    rx = re.compile(r"(?m)^\s*(?:async\s+)?(?:def|class|function|fn|struct|enum|const|let|var|static)\s+"
                    + re.escape(name) + r"\b|^\s*" + re.escape(name) + r"\s*[:=]|\b" + re.escape(name) + r"\s*\(")
    if rev:
        r = _git(rdir, "show", f"{rev}:{path}")
        text = r.stdout if r.returncode == 0 else ""
    else:
        p = rdir / path
        text = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    return bool(rx.search(text))


def check_symbol(rdir: Path, path: str, rev: str | None, sym: str) -> dict:
    """{ok, strength: strong|weak, how, blast_radius}. gitnexus when its index is fresh, else grep marked weak."""
    st = gitnexus_state(rdir) if not rev else "historical"
    if st == "ok":
        b = gitnexus_bin()
        try:
            r = subprocess.run([b, "context", sym], cwd=rdir, capture_output=True, text=True, timeout=60)
            out = r.stdout + r.stderr
            if r.returncode == 0 and path in out:
                blast = None
                try:
                    ri = subprocess.run([b, "impact", sym, "--direction", "upstream"], cwd=rdir,
                                        capture_output=True, text=True, timeout=60)
                    mm = re.search(r"\b(LOW|MEDIUM|HIGH|CRITICAL)\b", ri.stdout)
                    blast = mm.group(1) if mm else None
                except (OSError, subprocess.SubprocessError):
                    pass
                return {"ok": True, "strength": "strong", "how": "gitnexus context", "blast_radius": blast}
        except (OSError, subprocess.SubprocessError):
            pass
        st = "no-match"
    ok = _grep_symbol(rdir, path, rev, sym)
    return {"ok": ok, "strength": "weak", "how": f"grep (gitnexus {st})", "blast_radius": None}


# ------------------------------------------------------------------------------------------------- acceptance
_PYTEST = re.compile(r"^(?:python3?\s+-m\s+)?pytest\b")


def acceptance_dry(root: Path, cmd: str) -> dict:
    """{ok, kind, detail}: a DRY check only — nothing runs for real."""
    cmd = (cmd or "").strip().strip("`").strip()
    if not cmd:
        return {"ok": False, "kind": "empty", "detail": "acceptance is empty"}
    try:
        argv = shlex.split(cmd)
    except ValueError as e:
        return {"ok": False, "kind": "unparsable", "detail": str(e)}
    if _PYTEST.match(cmd):
        targets = [a for a in argv[1:] if not a.startswith("-") and a not in ("-m", "pytest")]
        ok_paths = [t for t in targets if (Path(root) / t.split("::")[0]).exists()]
        if targets and len(ok_paths) != len(targets):
            return {"ok": False, "kind": "pytest", "detail": f"missing test path(s): "
                    f"{[t for t in targets if t not in ok_paths]}"}
        try:
            r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                                *targets], cwd=root, capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "kind": "pytest", "detail": f"collect failed: {e}"}
        ok = r.returncode == 0
        return {"ok": ok, "kind": "pytest", "detail": "collected" if ok else (r.stdout + r.stderr).strip()[-300:]}
    if argv[0] in ("bash", "sh") and len(argv) > 1 or argv[0].endswith(".sh"):
        f = argv[1] if argv[0] in ("bash", "sh") else argv[0]
        if not (Path(root) / f).is_file():
            return {"ok": False, "kind": "shell", "detail": f"missing script {f}"}
        r = subprocess.run(["bash", "-n", f], cwd=root, capture_output=True, text=True, timeout=30)
        return {"ok": r.returncode == 0, "kind": "shell", "detail": (r.stderr or "bash -n ok").strip()[-300:]}
    if argv[0] in ("python3", "python") and len(argv) > 1 and argv[1].endswith(".py"):
        f = argv[1]
        if not (Path(root) / f).is_file():
            return {"ok": False, "kind": "python", "detail": f"missing script {f}"}
        r = subprocess.run([sys.executable, "-m", "py_compile", f], cwd=root, capture_output=True, text=True,
                           timeout=30)
        return {"ok": r.returncode == 0, "kind": "python", "detail": (r.stderr or "py_compile ok").strip()[-300:]}
    return {"ok": True, "kind": "parse-only", "detail": "not a runnable command shape; parsed only (file+field / verdict)"}


def acceptance_matches(acceptance: str | None, done_when: str | None) -> bool:
    """True when acceptance IS the box's done-when (literally, or as one of its backticked commands)."""
    norm = lambda s: " ".join((s or "").strip().strip("`").split())  # noqa: E731
    a, d = norm(acceptance), norm(done_when)
    if not a or not d:
        return False
    return a == d or a in [norm(x) for x in re.findall(r"`([^`]+)`", done_when or "")]


# ------------------------------------------------------------------------------------------------- compile
def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_cache(root: Path) -> dict:
    try:
        return json.loads((Path(root) / CACHE_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(root: Path, cache: dict) -> None:
    p = Path(root) / CACHE_REL
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(cache, sort_keys=True, indent=0), encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass


def where_blobs(root: Path, where: list) -> dict:
    out = {}
    for w in where or []:
        pw = parse_where(str(w))
        rd = repo_dir(root, pw["repo"])
        key = f"{pw['repo']}:{pw['path']}" + (f"@{pw['rev']}" if pw["rev"] else "")
        out[key] = blob_sha(rd, pw["path"], pw["rev"]) if rd else None
    return out


def cache_key(box_sha: str | None, brief_text: str, blobs: dict) -> str:
    return _sha(json.dumps([box_sha, _sha(brief_text), sorted(blobs.items())]))


def compile_brief(bid: str, root: Path = REPO_ROOT, use_cache: bool = True, box: dict | None = None) -> dict:
    """The deterministic compile. Returns {id, state, brief_sha, box_text_sha, checks, stale_list, weak, cache, ...}."""
    root = Path(root)
    box = find_box(root, bid) if box is None else box
    ref = (box or {}).get("brief_ref") or bid
    path = brief_path(root, ref)
    res = {"id": bid, "brief": str(path.relative_to(root)), "state": "none", "checks": [], "stale_list": [],
           "weak": False, "cache": "miss", "box": box}
    if not path.exists():
        return res
    text = path.read_text(encoding="utf-8", errors="replace")
    res["brief_sha"] = _sha(text)
    try:
        doc = parse_text(text)
    except Exception as e:  # noqa: BLE001
        res.update(state="stale", stale_list=[f"schema: {e}"])
        return res
    res.update(accepted=doc.get("accepted"), author=doc.get("author"), review=doc.get("review"),
               box_text_sha=doc.get("box_text_sha"))
    if box is None or box.get("n", 1) != 1:
        why = "box not found (open, in handoffs/active|blocked)" if box is None else f"box ID matches {box['n']} boxes"
        res.update(state="orphaned", stale_list=[f"identity: {why}"])
        return res
    if str(doc.get("box_text_sha")) != box["text_sha"]:
        res.update(state="orphaned", stale_list=[f"identity: brief box_text_sha {doc.get('box_text_sha')} != box "
                                                 f"text_sha {box['text_sha']} — box text changed; re-brief"])
        return res
    blobs = where_blobs(root, doc.get("where") or [])
    key = cache_key(box["text_sha"], text, blobs)
    cache = _load_cache(root) if use_cache else {}
    hit = cache.get(bid)
    if use_cache and hit and hit.get("key") == key:
        return {**res, **hit["result"], "cache": "hit", "box": box}
    errs = schema_errors(doc)
    stale = [f"schema: {e}" for e in errs]
    checks, inputs_ext, blast = [], [], {}
    for w in doc.get("where") or []:
        pw = parse_where(str(w))
        rd = repo_dir(root, pw["repo"])
        c = {"where": pw["raw"], "ok": True, "strength": "strong"}
        if rd is None:
            c.update(ok=False, detail=f"repo {pw['repo']} not found")
        elif blob_sha(rd, pw["path"], pw["rev"]) is None:
            c.update(ok=False, detail=f"path missing at {pw['rev'] or 'HEAD'}")
        elif pw["sym"]:
            s = check_symbol(rd, pw["path"], pw["rev"], pw["sym"])
            c.update(ok=s["ok"], strength=s["strength"], detail=s["how"] + ("" if s["ok"] else ": symbol not found"))
            if s.get("blast_radius"):
                blast[pw["sym"]] = s["blast_radius"]
        if pw["repo"] != "epyc-root" or pw["rev"]:
            inputs_ext.append({"repo": pw["repo"], "path": pw["path"], "rev": pw["rev"]})
        checks.append(c)
        if not c["ok"]:
            stale.append(f"where: {pw['raw']}: {c['detail']}")
    acc = acceptance_dry(root, str(doc.get("acceptance") or ""))
    checks.append({"acceptance": doc.get("acceptance"), **acc})
    if not acc["ok"]:
        stale.append(f"acceptance: {acc['kind']}: {acc['detail']}")
    grounded = ((doc.get("grounded") or {}).get("blobs") or {}) if isinstance(doc.get("grounded"), dict) else {}
    drifted = sorted(k for k, v in blobs.items() if k in grounded and grounded[k] != v)
    state = "stale" if stale else ("drift" if drifted else "fresh")
    out = {"state": state, "checks": checks, "stale_list": stale, "drifted": drifted,
           "weak": any(c.get("strength") == "weak" for c in checks), "inputs_ext": inputs_ext,
           "blast_radius": blast, "acceptance_matches_done_when": acceptance_matches(doc.get("acceptance"),
                                                                                        box.get("done_when")),
           "accepted": doc.get("accepted"), "author": doc.get("author"), "review": doc.get("review"),
           "box_text_sha": doc.get("box_text_sha"), "brief_sha": res["brief_sha"], "blobs": blobs}
    if use_cache:
        cache = _load_cache(root)
        cache[bid] = {"key": key, "result": out}
        _save_cache(root, cache)
    return {**res, **out}


def cached_state(root: Path, bid: str, box_sha: str, brief_ref: str | None = None) -> dict:
    """CHEAP state for the box index (no checks run): none | orphaned | <cached compile state> | unverified."""
    path = brief_path(root, brief_ref or bid)
    if not path.exists():
        return {"brief": "none"}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        doc = parse_text(text)
    except Exception:  # noqa: BLE001
        return {"brief": "stale", "brief_sha": _sha(text)}
    out = {"brief_sha": _sha(text), "accepted": doc.get("accepted"), "brief_author": doc.get("author"),
           "brief_review": doc.get("review")}
    if str(doc.get("box_text_sha")) != box_sha:
        return {**out, "brief": "orphaned"}
    hit = _load_cache(root).get(bid)
    if hit and hit.get("key") == cache_key(box_sha, text, where_blobs(root, doc.get("where") or [])):
        return {**out, "brief": hit["result"]["state"]}
    return {**out, "brief": "unverified"}


# ------------------------------------------------------------------------------------------------- write / accept
def write_brief(bid: str, where: list[str], approach: str, acceptance: str, non_goals: list[str] | None = None,
                tier: str = "local", author: str = "owner", accepted: str | None = None, root: Path = REPO_ROOT,
                today: str | None = None) -> Path:
    """Write (replace) the sidecar for an EXISTING open box; fills box_text_sha + grounded. Refuses an unknown box."""
    root = Path(root)
    box = find_box(root, bid)
    if box is None or box.get("n", 1) != 1:
        raise ValueError(f"box **{bid}** not found exactly once among open boxes in {BOX_DIRS}")
    today = today or _dt.date.today().isoformat()
    accepted = accepted or ("pending" if author == "self" else
                            "auto" if acceptance_matches(acceptance, box.get("done_when")) else "owner")
    doc = {"schema": SCHEMA, "id": bid, "box_text_sha": box["text_sha"], "author": author, "written": today,
           "accepted": accepted, "review": "backfill" if author == "self" else None,
           "where": list(where), "approach": approach.strip() + "\n", "acceptance": acceptance,
           "non_goals": list(non_goals or []), "tier": tier,
           "grounded": {"at": today, "blobs": where_blobs(root, where)}}
    errs = schema_errors(doc)
    if errs:
        raise ValueError("; ".join(errs))
    p = brief_path(root, box.get("brief_ref") or bid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(doc), encoding="utf-8")
    return p


def set_accepted(bid: str, by: str, root: Path = REPO_ROOT, today: str | None = None) -> Path:
    if by not in ACCEPTED:
        raise ValueError(f"--by must be one of {ACCEPTED}")
    p = brief_path(root, bid)
    if not p.exists():
        raise ValueError(f"no brief at {p}")
    doc = parse_text(p.read_text(encoding="utf-8"))
    doc.pop("_body", None)
    doc["accepted"] = by
    if by != "rejected":
        doc.pop("review", None)
        doc["grounded"] = {"at": today or _dt.date.today().isoformat(),
                           "blobs": where_blobs(Path(root), doc.get("where") or [])}
    p.write_text(render(doc), encoding="utf-8")
    return p


def all_briefs(root: Path) -> list[str]:
    d = Path(root) / BRIEF_DIR
    return sorted(p.stem for p in d.glob("*.md")) if d.exists() else []


def _exit(state: str) -> int:
    return 0 if state in ("fresh", "drift") else 2 if state == "none" else 1


def _show(r: dict) -> str:
    s = f"{r['id']}: {r['state']}" + (" (weak)" if r.get("weak") else "") + f" [cache {r.get('cache')}]"
    return s + "".join(f"\n  STALE {x}" for x in r.get("stale_list") or [])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(REPO_ROOT))
    sub = ap.add_subparsers(dest="op", required=True)
    p = sub.add_parser("compile"); p.add_argument("id"); p.add_argument("--json", action="store_true")
    p.add_argument("--no-cache", action="store_true")
    p = sub.add_parser("write"); p.add_argument("id"); p.add_argument("--where", nargs="+", required=True)
    p.add_argument("--approach", required=True); p.add_argument("--acceptance", required=True)
    p.add_argument("--non-goal", action="append", default=[]); p.add_argument("--tier", default="local", choices=TIERS)
    p.add_argument("--author", default="owner", choices=AUTHORS); p.add_argument("--accepted", choices=ACCEPTED)
    p.add_argument("--json", action="store_true")
    for op in ("accept", "reject"):
        p = sub.add_parser(op); p.add_argument("id"); p.add_argument("--by", default="owner")
    p = sub.add_parser("sweep"); p.add_argument("--json", action="store_true")
    p.add_argument("--stale-list", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    try:
        if a.op in ("compile", "write"):
            if a.op == "write":
                write_brief(a.id, a.where, a.approach, a.acceptance, a.non_goal, a.tier, a.author, a.accepted, root)
            r = compile_brief(a.id, root, use_cache=not getattr(a, "no_cache", False))
            print(json.dumps(r, sort_keys=True, default=str) if a.json else _show(r))
            return _exit(r["state"])
        if a.op in ("accept", "reject"):
            print(set_accepted(a.id, "rejected" if a.op == "reject" else a.by, root))
            return 0
        rs = [compile_brief(b, root) for b in all_briefs(root)]
        if a.stale_list:
            rs = [r for r in rs if r["state"] not in ("fresh", "drift")]
        for r in rs:
            print(json.dumps({k: r.get(k) for k in ("id", "state", "weak", "stale_list", "brief")}, sort_keys=True)
                  if a.json else _show(r))
        return 0
    except ValueError as e:
        print(f"brief: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

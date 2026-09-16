#!/usr/bin/env python3
"""Closure-inflation audit: verify code references in CHECKED handoff boxes.

For every `- [x]` box in origin/main:handoffs/active/*.md (epyc-root), extract
concrete code references (function/class identifiers, file paths, commit SHAs)
and verify them against origin/main of the three EPYC repos (plus the llama.cpp
production tree and the speech kernels as "external" references).

Classes for unresolved references:
  a  exists only off-main (unmerged branch, or an unreachable/dangling object)
  b  exists nowhere
  c  probable rename/move (close name / same basename elsewhere on main)
  d  external / upstream (found only in llama.cpp / whisper / qwentts / ik trees)

Read-only: uses git plumbing only (no checkout, no writes to any repo; --fetch updates
remote-tracking refs only).

Usage:
  closure_audit.py [--fetch] [--strict-idents] [--only REGEX] [--triage OVERRIDES.json]
                   [--json OUT.json] [--md OUT.md] [--tsv OUT.tsv]
A full run over handoffs/active takes ~30 min (mostly the unmerged-branch-tip grep).
Guide: docs/guides/agent-workflows/handoff-closure-audit.md
Origin: progress/2026-09/2026-09-16-sub-closure-audit.md (the 4762625d "2026-07-29" cohort).
Extra class "e": evidence/runtime artifact path (untracked by design) -- reported, not a code claim.
Known limits: a SHA-b is frequently an upstream pin / digest / store-row id / GC'd pre-cherry-pick
SHA -- triage by reading the context; commits found only off-main should be checked for a
subject-equivalent commit on main (done automatically: detail says "equiv on main").
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import threading
from collections import defaultdict
from dataclasses import dataclass, field, asdict

ROOT = os.environ.get("CLOSURE_AUDIT_ROOT", "/workspace")
REPOS = {
    "root": ROOT,
    "orch": "/mnt/raid0/llm/epyc-orchestrator",
    "research": "/mnt/raid0/llm/epyc-inference-research",
}
# external trees: (path, rev) — rev None = HEAD
EXTERNAL = {
    "llama.cpp": "/mnt/raid0/llm/llama.cpp",
    "whisper.cpp": "/mnt/raid0/llm/whisper.cpp",
    "qwentts.cpp": "/mnt/raid0/llm/qwentts.cpp",
    "ik_llama.cpp": "/mnt/raid0/llm/ik_llama.cpp",
}
MAIN = "origin/main"
HANDOFF_DIR = "handoffs/active"
CLONE_GLOBS = ["/mnt/raid0/llm/*/.git", "/mnt/raid0/llm/*/*/.git", "/mnt/raid0/llm/tmp/*/.git",
               "/mnt/raid0/llm/tmp/*/*/.git"]
DEFAULT_OUT = "/mnt/raid0/llm/tmp/closure-audit"

CODE_EXCLUDES = [":(exclude)*.md", ":(exclude)*.json", ":(exclude)*.jsonl",
                 ":(exclude)*.txt", ":(exclude)*.log", ":(exclude)*.csv"]
ROOT_EXTRA_EXCLUDES = [":(exclude)handoffs", ":(exclude)progress", ":(exclude)wiki",
                       ":(exclude)research", ":(exclude)coordination", ":(exclude)logs"]

PATH_EXTS = (".py", ".sh", ".md", ".json", ".yaml", ".yml", ".toml", ".cpp", ".c", ".h",
             ".hpp", ".rs", ".js", ".ts", ".html", ".jsonl", ".cfg", ".ini", ".cuh",
             ".cu", ".comp", ".metal", ".sql", ".css", ".txt", ".csv")
ASSERT_RE = re.compile(
    r"✅|\b(landed|implemented|added|adds|shipped|now (provides|has|emits|exposes|carries|"
    r"records|writes|uses)|created|wired|merged|committed|built|exists|fixed|DONE|done|"
    r"delivered|introduced|extended|rewritten|replaced|ported|pushed)\b", re.I)
CLOSED_OTHERWISE_RE = re.compile(r"\b(supersed\w*|declin\w*|design[- ]only|not (yet )?built|ruled out|retired|"
                                 r"deleted|removed|NOT-FEASIBLE|no-go|won't|wontfix|resolved-by-decision|"
                                 r"evidence-gated|deferred|refiled|moot|obsolete)\b", re.I)
PLAN_RE = re.compile(r"\b(plan(ned)?|propos(e|ed)|design(ed)? only|TODO|future|deferred|"
                     r"would|should)\b", re.I)
HEX_RE = re.compile(r"(?<![0-9A-Za-z/_.\-])([0-9a-f]{7,40})(?![0-9A-Za-z_\-])")
DIGEST_CTX = re.compile(r"(sha-?256|sha256|digest|blob|sha1sum|md5|checksum|hash|uuid|"
                        r"token|id=|0x)\W{0,3}$", re.I)
TICK_SPAN = re.compile(r"`([^`\n]+)`")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
FUNC_RE = re.compile(r"^(?:[A-Za-z_][\w]*(?:\.|::))*([A-Za-z_]\w*)\s*\((.*)\)$")
CAMEL_RE = re.compile(r"^(?:[A-Za-z_]\w*\.)*([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+)$")
BUILTINS = set("""print len str int dict list set tuple open range main init run get
set_ max min sum sorted isinstance super repr format type id hash any all zip map
filter enumerate json load loads dump dumps exit time sleep""".split())


STRICT_IDENTS = False
GREP_TIMEOUT = 3600  # --strict-idents roughly triples the pattern set; 600 s was measured too short


def git(repo, *args, check=False, input=None, timeout=600):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                       input=input, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"git {args} in {repo}: {p.stderr}")
    return p


@dataclass
class Ref:
    kind: str       # ident | path | sha
    value: str
    raw: str
    cls: str = ""   # ok | a | b | c | d | e | skip
    detail: str = ""
    triage_class: str = ""    # from --triage overrides (empty = untriaged)
    triage_action: str = ""


@dataclass
class Box:
    handoff: str
    line: int
    text: str
    refs: list = field(default_factory=list)
    asserts_built: bool = False
    ticked_by: str = ""


# ---------------------------------------------------------------- extraction
def iter_boxes(fname: str, content: str):
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^(\s*)[-*] \[[xX]\]\s", lines[i])
        if not m:
            i += 1
            continue
        indent = len(m.group(1))
        buf = [lines[i]]
        j = i + 1
        while j < len(lines):
            l = lines[j]
            if not l.strip():
                break
            lm = re.match(r"^(\s*)([-*]|\d+\.) ", l)
            if lm and len(lm.group(1)) <= indent:
                break
            if re.match(r"^\s*[-*] \[[ xX~!]\]", l):
                break
            if l.startswith("#") or l.startswith("|"):
                break
            buf.append(l)
            j += 1
        yield Box(fname, i + 1, "\n".join(buf))
        i = j


def looks_like_path(s: str) -> bool:
    if " " in s or "://" in s or any(c in s for c in "<>*{}$|,;=\"'"):
        return False
    if s.startswith("-") or s.startswith("@"):
        return False
    core = re.sub(r":\d+(-\d+)?$", "", s)
    core = re.sub(r"#.*$", "", core)
    if core.lower().endswith(PATH_EXTS):
        return True
    if "/" in core and re.match(r"^[\w./\-~]+$", core) and not re.match(r"^[\d./]+$", core):
        # at least one segment w/ letters and not a ratio like 3/4
        segs = [x for x in core.split("/") if x]
        return len(segs) >= 2 and all(re.match(r"^[\w.\-~]+$", x) for x in segs)
    return False


def extract_refs(box: Box):
    refs, seen = [], set()

    def add(kind, value, raw):
        k = (kind, value)
        if k not in seen:
            seen.add(k)
            refs.append(Ref(kind, value, raw))

    text = box.text
    for sp in TICK_SPAN.findall(text):
        s = sp.strip()
        fm = FUNC_RE.match(s)
        if fm and not looks_like_path(s):
            name = fm.group(1)
            if len(name) >= 4 and name not in BUILTINS and not name.startswith("intake"):
                add("ident", name, s)
            continue
        if STRICT_IDENTS and re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+){1,}", s) and len(s) >= 8 \
                and ASSERT_RE.search(text):
            add("ident", s, s)   # snake_case symbol/column in an asserting box (noisier; opt-in)
            continue
        cm = CAMEL_RE.match(s)
        if cm:
            add("ident", cm.group(1), s)
            continue
        if looks_like_path(s):
            add("path", s, s)
            continue
        if re.fullmatch(r"[0-9a-f]{7,40}", s) and re.search(r"[0-9]", s) and re.search(r"[a-f]", s):
            add("sha", s, s)
    for lk in LINK_RE.findall(text):
        if "://" in lk or lk.startswith("#") or lk.startswith("mailto:"):
            continue
        add("path", "LINK:" + lk, lk)
    # bare SHAs outside backticks
    stripped = TICK_SPAN.sub(lambda m: " " * len(m.group(0)), text)
    stripped = LINK_RE.sub(lambda m: " " * len(m.group(0)), stripped)
    for m in HEX_RE.finditer(stripped):
        h = m.group(1)
        if not (re.search(r"[0-9]", h) and re.search(r"[a-f]", h)):
            continue
        if DIGEST_CTX.search(stripped[max(0, m.start() - 14):m.start()]):
            continue
        add("sha", h, h)
    # backticked shas that sit in a digest context -> drop
    box.refs = refs
    box.asserts_built = bool(ASSERT_RE.search(text)) and not CLOSED_OTHERWISE_RE.search(text)


# ---------------------------------------------------------------- indices
def scan_words(repo, specs, words):
    """Return the subset of `words` occurring as whole words in blobs `specs` ("<rev>:<path>")."""
    files = specs
    want = set(words)
    simple = {w for w in want if re.fullmatch(r"\w+", w)}
    odd = want - simple
    found = set()
    if not files or not want:
        return found
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    payload = "".join(f + "\n" for f in files).encode()

    def feed():
        proc.stdin.write(payload)
        proc.stdin.close()

    feeder = threading.Thread(target=feed, daemon=True)
    feeder.start()
    tok = re.compile(r"\w+")
    for _ in files:
        header = proc.stdout.readline().split()
        if len(header) < 3:          # "<name> missing"
            continue
        body = proc.stdout.read(int(header[2]))
        proc.stdout.read(1)          # trailing LF
        if b"\0" in body[:8000]:     # binary blob (tip diffs are not -I filtered)
            continue
        text = body.decode("utf-8", "replace")
        found.update(simple.intersection(tok.findall(text)))
        for w in odd - found:
            if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text):
                found.add(w)
    feeder.join()
    proc.wait()
    return found


class RepoIndex:
    def __init__(self, name, path, rev):
        self.name, self.path, self.rev = name, path, rev
        out = git(path, "ls-tree", "-r", "--name-only", rev).stdout.splitlines()
        self.files = set(out)
        self.dirs = set()
        self.by_base = defaultdict(list)
        for f in out:
            self.by_base[os.path.basename(f)].append(f)
            parts = f.split("/")
            for k in range(1, len(parts)):
                self.dirs.add("/".join(parts[:k]))
        self._suffix_cache = {}
        self.vocab = None

    def has_path(self, p):
        p = p.strip("/")
        if p in self.files or p in self.dirs:
            return "exact"
        if p in self._suffix_cache:
            return self._suffix_cache[p]
        suf = "/" + p
        r = None
        base = os.path.basename(p)
        for f in self.by_base.get(base, []):
            if f.endswith(suf):
                r = "suffix:" + f
                break
        if r is None and "/" in p:
            for d in self.dirs:
                if d.endswith(suf):
                    r = "suffix:" + d
                    break
        self._suffix_cache[p] = r
        return r

    def grep_words(self, words, rev=None, excludes=None):
        """Return set of words (from `words`) matched as whole words at rev."""
        if not words:
            return set()
        rev = rev or self.rev
        excl = list(CODE_EXCLUDES) + (excludes or [])
        # One tokenizing pass instead of `git grep -w -F -f`: with ~2k patterns (--strict-idents)
        # git's fixed-string word matching ran >20 min at 500% CPU on the root tree (2026-09-16).
        # Tokens are \w+ runs, which is exactly -w semantics for identifier-shaped words; any word
        # with other characters falls back to a bounded regex search on the same text.
        files = git(self.path, "grep", "-I", "-l", "-e", "", rev, "--", ".", *excl,
                    timeout=GREP_TIMEOUT).stdout.splitlines()
        return scan_words(self.path, files, words)
        proc = subprocess.Popen(["git", "-C", self.path, "cat-file", "--batch"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        payload = "".join(f + "\n" for f in files).encode()

        def feed():
            proc.stdin.write(payload)
            proc.stdin.close()

        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
        tok = re.compile(r"\w+")
        for _ in files:
            header = proc.stdout.readline().split()
            if len(header) < 3:          # "<name> missing"
                continue
            body = proc.stdout.read(int(header[2]))
            proc.stdout.read(1)          # trailing LF
            text = body.decode("utf-8", "replace")
            found.update(simple.intersection(tok.findall(text)))
            for w in odd - found:
                if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text):
                    found.add(w)
        feeder.join()
        proc.wait()
        return found

    def definitions(self):
        if self.vocab is None:
            p = git(self.path, "grep", "-I", "-h", "-o", "-E",
                    r"(def|class|function|fn|struct) +[A-Za-z_][A-Za-z0-9_]*", self.rev,
                    "--", ".", *CODE_EXCLUDES)
            self.vocab = sorted({l.split()[-1] for l in p.stdout.splitlines()})
        return self.vocab

    def batch_objects(self, shas):
        if not shas:
            return {}
        p = git(self.path, "cat-file", "--batch-check", input="\n".join(shas) + "\n")
        res = {}
        for s, line in zip(shas, p.stdout.splitlines()):
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ("commit", "tree", "blob", "tag"):
                res[s] = (parts[1], parts[0])
            elif "ambiguous" in line:
                res[s] = ("ambiguous", s)
        return res

    def is_ancestor(self, full, rev=None):
        return git(self.path, "merge-base", "--is-ancestor", full, rev or self.rev).returncode == 0

    def containing_branches(self, full, limit=4):
        p = git(self.path, "for-each-ref", "--contains", full, "--format=%(refname:short)",
                "refs/heads", "refs/remotes", timeout=300)
        brs = [b for b in p.stdout.split() if b]
        return brs[:limit], len(brs)

    def unmerged_tips(self):
        p = git(self.path, "for-each-ref", "--no-merged", self.rev, "--format=%(refname)",
                "refs/heads", "refs/remotes")
        return [r for r in p.stdout.split() if r]


def excludes_for(name):
    return ROOT_EXTRA_EXCLUDES if name == "root" else []


# ---------------------------------------------------------------- verification
def verify(boxes, idx, ext_idx, log):
    idents = {r.value for b in boxes for r in b.refs if r.kind == "ident"}
    log(f"identifiers: {len(idents)}")
    found_main = defaultdict(set)
    for n, ri in idx.items():
        for w in ri.grep_words(idents, excludes=excludes_for(n)):
            found_main[w].add(n)
    # a backticked test/script name is often a file stem (`test_foo` -> tests/unit/test_foo.py)
    for n, ri in idx.items():
        stems = {os.path.splitext(b)[0] for b in ri.by_base}
        for w in idents & stems:
            found_main[w].add(f"{n}(file stem)")
    unresolved = idents - set(found_main)
    log(f"  unresolved on main: {len(unresolved)}")
    # off-main branches
    found_branch = defaultdict(set)
    for n, ri in idx.items():
        tips = ri.unmerged_tips()
        log(f"  {n}: {len(tips)} unmerged tips")
        if not tips or not unresolved:
            continue
        excl = list(CODE_EXCLUDES) + excludes_for(n)
        # Only files a tip changed since its merge-base can hold a word that main lacks.
        for tip in tips:
            mb = git(ri.path, "merge-base", ri.rev, tip).stdout.strip()
            if not mb:
                continue
            changed = git(ri.path, "diff", "--name-only", "--diff-filter=AMR", mb, tip, "--", ".",
                          *excl, timeout=GREP_TIMEOUT).stdout.splitlines()
            if not changed:
                continue
            short = tip.replace("refs/remotes/", "").replace("refs/heads/", "")
            for word in scan_words(ri.path, [f"{tip}:{c}" for c in changed], unresolved):
                found_branch[word].add(f"{n}:{short}")
    rem = unresolved - set(found_branch)
    # history (deleted from main / dangling in history)
    # external trees first: an upstream symbol that also appeared in a vendored copy is (d), not (a)
    found_ext = defaultdict(set)
    for n, ri in ext_idx.items():
        for w in ri.grep_words(rem):
            found_ext[w].add(n)
    found_hist = {}
    for w in sorted(rem - set(found_ext)):
        for n, ri in idx.items():
            p = git(ri.path, "log", "--all", "-S", w, "--format=%h %ad", "--date=short",
                    "-1", "--", ".", *CODE_EXCLUDES, *excludes_for(n), timeout=900)
            if p.stdout.strip():
                found_hist[w] = f"{n}@{p.stdout.strip()} (history only)"
                break

    for b in boxes:
        for r in b.refs:
            if r.kind != "ident":
                continue
            w = r.value
            if w in found_main:
                r.cls, r.detail = "ok", ",".join(sorted(found_main[w]))
            elif w in found_ext:
                r.cls, r.detail = "d", "external:" + ",".join(sorted(found_ext[w]))
            elif w in found_branch:
                br = sorted(found_branch[w])
                r.cls, r.detail = "a", f"off-main: {', '.join(br[:3])}" + (f" (+{len(br)-3})" if len(br) > 3 else "")
            elif w in found_hist:
                r.cls, r.detail = "a", found_hist[w]
            else:
                cands = []
                for n, ri in idx.items():
                    for c in difflib.get_close_matches(w, ri.definitions(), n=2, cutoff=0.82):
                        cands.append(f"{n}:{c}")
                if cands:
                    r.cls, r.detail = "c", "similar: " + ", ".join(cands[:3])
                else:
                    r.cls, r.detail = "b", "not found on any ref"

    # ---- paths
    for b in boxes:
        for r in b.refs:
            if r.kind != "path":
                continue
            v = r.value
            is_link = v.startswith("LINK:")
            v = v[5:] if is_link else v
            v = re.sub(r"#.*$", "", v)
            v = re.sub(r":\d+(-\d+)?$", "", v)
            if is_link:
                base = os.path.dirname(b.handoff)
                v = os.path.normpath(os.path.join(base, v)) if not v.startswith("/") else v
            cand = []  # (repo, relpath)
            if v.startswith("/"):
                mapped = False
                for n, ri in list(idx.items()):
                    for pref in {ri.path + "/", f"/workspace/repos/{os.path.basename(ri.path)}/"}:
                        if v.startswith(pref):
                            cand.append((n, v[len(pref):])); mapped = True
                if v.startswith("/workspace/") and not v.startswith("/workspace/repos/"):
                    cand.append(("root", v[len("/workspace/"):])); mapped = True
                for n, ep in EXTERNAL.items():
                    if v.startswith(ep + "/") or v.startswith("/workspace/repos/epyc-llama/"):
                        r.cls, r.detail = "skip", "external tree path"; mapped = None
                        break
                if mapped is None:
                    continue
                if not mapped:
                    r.cls, r.detail = "skip", ("fs-present" if os.path.exists(v) else "fs-absent (non-repo abs path)")
                    continue
            else:
                v2 = v[2:] if v.startswith("./") else v
                if v2.startswith("repos/"):
                    v2 = v2[len("repos/"):]
                pfx = v2.split("/", 1)
                nm = {"epyc-orchestrator": "orch", "epyc-inference-research": "research",
                      "epyc-root": "root"}.get(pfx[0])
                if nm and len(pfx) > 1:
                    cand.append((nm, pfx[1]))
                    v2 = pfx[1]
                if re.search(r"\.(com|co|org|io|ai)/", v2) or re.search(r"^[\d.]+s?/[\d.]+s?$", v2) \
                        or v2.startswith(("ak/", "lane/", "codex/", "feat/", "origin/")) \
                        or "…" in v2 or re.fullmatch(r"[\w\-]+(/[\w\-]+)+", v2) and not v2.startswith(
                            ("src/", "scripts/", "tests/", "orchestration/", "tools/", "dashboard/", "docs/",
                             "agents/", "handoffs/", "config", "measurement/", "ggml/", "benchmarks/")):
                    r.cls, r.detail = "skip", "branch name / URL / prose slash"
                    continue
                if not nm:
                    for n in idx:
                        cand.append((n, v2))
            if any(seg.startswith("..") for seg in v.split("/")):
                r.cls, r.detail = "skip", "escapes repo"
                continue
            hit = None
            for n, rel in cand:
                h = idx[n].has_path(rel)
                if h:
                    hit = f"{n}:{h}"
                    if h == "exact":
                        break
            if hit:
                r.cls, r.detail = "ok", hit
                continue
            rel = cand[0][1] if cand else v
            if re.match(r"^(data|artifacts|logs|tmp|results|reports|loop-memory|calibration|models|"
                        r"orchestration/reports|benchmarks/results|agents/[^/]+/results|token_traces)(/|$)", rel) \
                    or re.search(r"(20\d{6}T?\d*Z?|/results[-/]|/runs?/|\.(gguf|parquet|so|tsv|sha256|db)$)", rel):
                on_disk = any(os.path.exists(os.path.join(ri.path, rel)) for ri in idx.values()) or \
                    (rel.startswith("/") and os.path.exists(rel))
                r.cls, r.detail = "e", "evidence/runtime artifact " + ("present on disk (untracked)" if on_disk else "ABSENT on disk and untracked")
                continue
            # kernel trees, any branch
            kh = None
            for n, ri in ext_idx.items():
                if ri.has_path(rel):
                    kh = f"{n} HEAD"; break
                pk = git(ri.path, "log", "--all", "-1", "--format=%h %D", "--", f"*{rel}", timeout=600)
                if pk.stdout.strip():
                    kh = f"{n} branch commit {pk.stdout.strip()[:60]}"; break
            if kh:
                r.cls, r.detail = "d", "kernel/external tree: " + kh
                continue
            # untracked-but-generated? (runtime artifact dirs)
            if re.match(r"^(logs|tmp|/tmp|benchmarks/results|artifacts/runs|\.)", rel) or \
                    any(seg in rel for seg in ("/runs/", "results/", "/tmp/", "cache/")):
                r.cls, r.detail = "skip", "runtime artifact path"
                continue
            segs = rel.strip("/").split("/")
            if re.search(r"[:.]\d+(-\d+)?$", r.value) is None and False:
                pass
            if len(segs) == 2 and "." not in segs[1] and not any(ri.has_path(segs[0]) for ri in idx.values()):
                r.cls, r.detail = "skip", "looks like org/repo or prose slash"
                continue
            if not ("/" in rel or rel.lower().endswith((".py", ".sh", ".cpp", ".h", ".rs", ".js", ".ts"))):
                r.cls, r.detail = "skip", "bare filename not resolvable"
                continue
            # off-main
            offm = None
            for n, ri in idx.items():
                p = git(ri.path, "log", "--all", "-1", "--format=%h %ad %D", "--date=short",
                        "--", f"*{rel}" if not rel.startswith("*") else rel, timeout=600)
                if p.stdout.strip():
                    offm = f"{n}: last touched {p.stdout.strip()}"
                    break
            base = os.path.basename(rel)
            moved = [f"{n}:{f}" for n, ri in idx.items() for f in ri.by_base.get(base, [])]
            if offm:
                # was on main history but deleted, or only on branches
                r.cls, r.detail = ("c" if moved else "a"), offm + (f"; same basename now at {moved[:2]}" if moved else "")
            elif moved:
                r.cls, r.detail = "c", f"same basename at {moved[:3]}"
            else:
                on_disk = [pp for pp in [os.path.join(ri.path, rel) for ri in idx.values()] if os.path.exists(pp)]
                ext = [n for n, ri in ext_idx.items() if ri.has_path(rel)]
                if ext:
                    r.cls, r.detail = "d", "external:" + ",".join(ext)
                elif on_disk:
                    r.cls, r.detail = "a", f"untracked on disk only: {on_disk[0]}"
                else:
                    r.cls, r.detail = "b", "no tracked path on any ref, not on disk"

    # ---- SHAs
    shas = sorted({r.value for b in boxes for r in b.refs if r.kind == "sha"})
    log(f"shas: {len(shas)}")
    objs = {n: ri.batch_objects(shas) for n, ri in idx.items()}
    eobjs = {n: ri.batch_objects(shas) for n, ri in ext_idx.items()}
    sha_res = {}
    for s in shas:
        hits = [(n, o) for n in idx for o in [objs[n].get(s)] if o and o[0] == "commit"]
        if hits:
            onmain = [n for n, o in hits if idx[n].is_ancestor(o[1])]
            if onmain:
                sha_res[s] = ("ok", f"{onmain[0]} main")
            else:
                n, o = hits[0]
                subj = git(idx[n].path, "log", "-1", "--format=%s", o[1]).stdout.strip()
                eq = git(idx[n].path, "log", idx[n].rev, "-1", "--format=%h", "-F", "--grep=" + subj).stdout.strip() if subj else ""
                if eq:
                    sha_res[s] = ("ok", f"{n}: off-main SHA, subject-equivalent commit {eq} on main (re-point)")
                    continue
                brs, cnt = idx[n].containing_branches(o[1])
                if cnt:
                    sha_res[s] = ("a", f"{n}: on {cnt} non-main ref(s): {', '.join(brs)}")
                else:
                    sha_res[s] = ("a", f"{n}: UNREACHABLE object (no ref contains it)")
            continue
        ehits = [n for n in ext_idx if eobjs[n].get(s) and eobjs[n][s][0] == "commit"]
        if ehits:
            sha_res[s] = ("d", "external:" + ",".join(ehits))
            continue
        clones = [c for c in scan_clones() if clone_has_commit(c, s)]
        if clones:
            nm = ", ".join(os.path.relpath(c, "/mnt/raid0/llm") for c in clones[:3])
            kern = all("llama.cpp" in c or "whisper" in c or "qwentts" in c for c in clones)
            sha_res[s] = ("d", ("kernel scratch clone only: " if kern else "other local clone: ") + nm)
            continue
        other = [f"{n}:{o[0]}" for n in idx for o in [objs[n].get(s)] if o]
        if other:
            sha_res[s] = ("skip", "matches non-commit object " + ",".join(other))
        elif len(s) >= 12 and len(s) != 40:
            sha_res[s] = ("skip", "hex token, likely digest/id (len %d)" % len(s))
        else:
            sha_res[s] = ("b", "no such commit in any repo/kernel tree")
    for b in boxes:
        for r in b.refs:
            if r.kind == "sha":
                r.cls, r.detail = sha_res[r.value]


_CLONES = None
_CLONE_CACHE = {}


def scan_clones():
    global _CLONES
    if _CLONES is None:
        import glob
        skip = set(REPOS.values()) | set(EXTERNAL.values())
        found = set()
        for pat in CLONE_GLOBS:
            for g in glob.glob(pat):
                d = os.path.dirname(g)
                if d not in skip:
                    found.add(d)
        _CLONES = sorted(found)
    return _CLONES


def clone_has_commit(clone, sha):
    key = (clone, sha)
    if key not in _CLONE_CACHE:
        p = git(clone, "cat-file", "-t", sha)
        _CLONE_CACHE[key] = p.stdout.strip() == "commit"
    return _CLONE_CACHE[key]


def ticked_by(box: Box):
    body = re.sub(r"^\s*[-*] \[[xX]\]\s*", "", box.text.splitlines()[0])
    # a distinctive probe: first 50 chars of the box's first line
    probe = body[:50]
    p = git(ROOT, "log", MAIN, "--reverse", "-S", "[x] " + probe[:40], "--format=%h %ad %an",
            "--date=short", "--", "handoffs/", timeout=600)
    lines = p.stdout.strip().splitlines()
    if not lines:
        p = git(ROOT, "log", MAIN, "--reverse", "-S", probe, "--format=%h %ad %an",
                "--date=short", "--", "handoffs/", timeout=600)
        lines = p.stdout.strip().splitlines()
        return ("text-introduced " + lines[0]) if lines else "unknown"
    return lines[0]


# ---------------------------------------------------------------- triage overrides
def load_triage(path):
    """Load manual triage overrides.

    JSON object: {"overrides": [{"key": K, "class": C, "action": A}, ...],
                  "sha_equiv": {"<off-main sha>": "<same-subject sha on main>", ...}}
    Key forms, most specific first: "<handoff>.md:<line>|<ref>", "<handoff>.md|<ref>",
    "<handoff>.md:<line>", "<handoff>.md", "*|<ref>". Handoff = basename. Prefer the
    line-free forms: line numbers rot as handoffs are edited, the ref text does not.
    """
    if not path:
        return {}, {}
    with open(path) as fh:
        d = json.load(fh)
    ov = {}
    for o in d.get("overrides", []):
        ov[o["key"]] = (o["class"], o.get("action", ""))
    return ov, d.get("sha_equiv", {})


def triage_ref(handoff, line, ref, ov, eq):
    base = os.path.basename(handoff)
    for k in (f"{base}:{line}|{ref.raw}", f"{base}:{line}|{ref.value}", f"{base}|{ref.raw}",
              f"{base}|{ref.value}", f"{base}:{line}", base, f"*|{ref.raw}", f"*|{ref.value}"):
        if k in ov:
            return ov[k]
    if ref.kind == "sha" and ref.value in eq:
        return f"ok-equiv (same-subject commit {eq[ref.value]} is on main)", "re-point (cosmetic)"
    if "subject-equivalent" in ref.detail:
        return "ok-equiv", "re-point (cosmetic)"
    return "", "UNTRIAGED"


def main():
    global STRICT_IDENTS, ROOT, MAIN, HANDOFF_DIR, CLONE_GLOBS, GREP_TIMEOUT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--json", default=f"{DEFAULT_OUT}/closure_audit.json")
    ap.add_argument("--md", default=f"{DEFAULT_OUT}/closure_audit_table.md")
    ap.add_argument("--tsv", default=None, help="flat triaged table (one row per flagged a/b/c ref)")
    ap.add_argument("--triage", default=None, help="JSON triage-override file (see load_triage)")
    ap.add_argument("--root", default=REPOS["root"], help="epyc-root clone (handoffs are read from it)")
    ap.add_argument("--orch", default=REPOS["orch"])
    ap.add_argument("--research", default=REPOS["research"])
    ap.add_argument("--rev", default=MAIN, help="rev verified against in every repo (default origin/main)")
    ap.add_argument("--handoff-dir", default=HANDOFF_DIR)
    ap.add_argument("--git-timeout", type=int, default=GREP_TIMEOUT,
                    help="seconds per bulk git-grep (default %(default)s)")
    ap.add_argument("--no-external", action="store_true",
                    help="skip kernel trees and the local-clone scan (tests / hosts without them)")
    ap.add_argument("--strict-idents", action="store_true",
                    help="also verify backticked snake_case names in asserting boxes (catches RC-9-style column claims; noisy)")
    ap.add_argument("--only", help="restrict to handoff basenames matching regex")
    args = ap.parse_args()
    STRICT_IDENTS = args.strict_idents
    GREP_TIMEOUT = args.git_timeout
    ROOT, MAIN, HANDOFF_DIR = args.root, args.rev, args.handoff_dir
    REPOS.update({"root": args.root, "orch": args.orch, "research": args.research})
    if args.no_external:
        EXTERNAL.clear()
        CLONE_GLOBS = []
    for outp in (args.json, args.md, args.tsv):
        if outp:
            os.makedirs(os.path.dirname(os.path.abspath(outp)), exist_ok=True)
    ov, eq = load_triage(args.triage)
    log = lambda m: print(m, file=sys.stderr, flush=True)
    if args.fetch:
        for pth in REPOS.values():
            git(pth, "fetch", "-q")
    # dedupe repos that point at the same clone (e.g. tests)
    seen_paths, uniq = set(), {}
    for n, pth in REPOS.items():
        rp = os.path.realpath(pth)
        if rp not in seen_paths:
            seen_paths.add(rp)
            uniq[n] = pth
    idx = {n: RepoIndex(n, p, MAIN) for n, p in uniq.items()}
    ext_idx = {n: RepoIndex(n, p, "HEAD") for n, p in EXTERNAL.items() if os.path.isdir(p + "/.git") or os.path.isfile(p + "/.git")}
    files = [f for f in git(ROOT, "ls-tree", "--name-only", MAIN, HANDOFF_DIR + "/").stdout.split()
             if f.endswith(".md") and (not args.only or re.search(args.only, f))]
    boxes = []
    for f in files:
        content = git(ROOT, "show", f"{MAIN}:{f}").stdout
        for b in iter_boxes(f, content):
            extract_refs(b)
            boxes.append(b)
    log(f"boxes: {len(boxes)} with refs: {sum(1 for b in boxes if b.refs)}")
    verify(boxes, idx, ext_idx, log)
    flagged = [b for b in boxes if any(r.cls in ("a", "b") for r in b.refs)]
    log(f"flagged boxes: {len(flagged)}")
    for b in flagged:
        b.ticked_by = ticked_by(b)
    counts = defaultdict(lambda: defaultdict(int))
    for b in boxes:
        for r in b.refs:
            counts[r.kind][r.cls] += 1
    for b in flagged:
        for r in b.refs:
            if r.cls in ("a", "b", "c"):
                r.triage_class, r.triage_action = triage_ref(b.handoff, b.line, r, ov, eq)
    out = {"main_revs": {n: git(p, "rev-parse", "--short", MAIN).stdout.strip() for n, p in uniq.items()},
           "strict_idents": STRICT_IDENTS,
           "n_boxes": len(boxes), "n_boxes_with_refs": sum(1 for b in boxes if b.refs),
           "counts": {k: dict(v) for k, v in counts.items()},
           "flagged": [asdict(b) for b in flagged],
           "c_and_d": [{"handoff": b.handoff, "line": b.line, **asdict(r)} for b in boxes for r in b.refs if r.cls in ("c", "d")]}
    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    with open(args.md, "w") as fh:
        fh.write("| handoff | box excerpt | reference | class | detail | asserts built | ticked-by | triage | action |\n"
                 "|---|---|---|---|---|---|---|---|---|\n")
        for b in flagged:
            ex = re.sub(r"\s+", " ", re.sub(r"^\s*[-*] \[[xX]\]\s*", "", b.text))[:90].replace("|", "\\|")
            for r in b.refs:
                if r.cls in ("a", "b", "c"):
                    fh.write(f"| {os.path.basename(b.handoff)}:{b.line} | {ex} | `{r.raw}` ({r.kind}) | {r.cls} | "
                             f"{r.detail.replace('|', '/')} | {'yes' if b.asserts_built else 'no'} | {b.ticked_by} | "
                             f"{r.triage_class.replace('|', '/')} | {r.triage_action.replace('|', '/')} |\n")
    if args.tsv:
        with open(args.tsv, "w") as fh:
            for b in flagged:
                for r in b.refs:
                    if r.cls in ("a", "b", "c"):
                        fh.write("\t".join([f"{os.path.basename(b.handoff)}:{b.line}", r.kind, r.cls, r.value,
                                            r.detail, str(b.asserts_built), b.ticked_by, r.triage_class,
                                            r.triage_action, b.text.splitlines()[0][:110]]) + "\n")
    log(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()

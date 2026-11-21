#!/usr/bin/env python3
"""handback_verify.py - AK parallel-loop P5(a): run references/handback-checklist.md mechanically.

A subagent hand-back is a set of claims. Every claim is checked against git / the rowflow pipeline directories and gets
a per-claim result; the whole hand-back gets ONE stamp:

    VERIFIED    >=1 claim, every claim verified
    UNVERIFIED  anything else (a failed claim, an unprovable claim, or no checkable claim at all)

Input: a hand-back text file (claims are extracted by line patterns, see CLAIM_PATTERNS) or JSON claims
(`{"claims":[{"type":"pushed","sha":"..."}, ...]}` or a bare list). Read-only: git queries, file stats, an optional
test re-run (--rerun) and nothing else. No compute, no network (--fetch is opt-in and only `git fetch origin`).

    handback_verify.py --text handback.md [--json-out stamp.json]
    handback_verify.py --claims claims.json --rerun
Exit 0 = VERIFIED, 1 = UNVERIFIED, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

LIVE_FLAGS = "/mnt/raid0/llm/" + "tmp/compute-flags"
DEFAULT_REPO = "/workspace"
SHA = r"[0-9a-f]{7,40}"
ID = r"[A-Za-z0-9][A-Za-z0-9_.\-]{5,}"

# text pattern -> claim builder. Matched per line, case-insensitive; backticks are stripped first.
CLAIM_PATTERNS = [
    ("pushed", re.compile(rf"\bpushed\s+(?P<sha>{SHA})(?:\s+(?:on|to)\s+(?P<branch>[\w./\-]+))?", re.I)),
    ("published", re.compile(rf"\bpublished\s+(?P<id>{ID})", re.I)),
    ("smoke_pass", re.compile(rf"\bsmoke\s+pass(?:ed)?\s+(?:for\s+)?(?P<id>{ID})", re.I)),
    ("filed", re.compile(rf"\bfiled\s+(?P<id>{ID})", re.I)),
    ("ticked", re.compile(rf"\bticked\s+(?P<tid>[A-Za-z0-9][\w\-:.]+)\s+in\s+(?P<file>\S+)", re.I)),
    ("built", re.compile(r"\bbuilt\s+(?P<lib>\S+)\s+with\s+(?P<symbol>[\w.\-]+)", re.I)),
    ("branch_contains", re.compile(rf"\bbranch\s+(?P<branch>[\w./\-]+)\s+contains\s+(?P<sha>{SHA})", re.I)),
    ("tests", re.compile(r"\btests?\s+(?:passed|pass)\b[:\s]*(?:log\s+(?P<log>\S+))?(?:\s*cmd\s+(?P<cmd>.+))?", re.I)),
]


def _run(argv, cwd=None, timeout=60):
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 99, "", f"{type(e).__name__}: {e}"


def extract_claims(text):
    claims = []
    for line in text.splitlines():
        line = line.replace("`", "")
        for typ, rx in CLAIM_PATTERNS:
            m = rx.search(line)
            if m:
                c = {"type": typ, "source": line.strip()[:200]}
                c.update({k: v for k, v in m.groupdict().items() if v})
                if typ == "ticked":
                    c["id"] = c.pop("tid")
                claims.append(c)
    return claims


def load_claims(path):
    with open(path) as f:
        d = json.load(f)
    if isinstance(d, dict):
        d = d.get("claims", [])
    if not isinstance(d, list) or not all(isinstance(c, dict) and "type" in c for c in d):
        raise ValueError("claims must be a list (or {'claims': [...]}) of objects with a 'type'")
    return d


class Ctx:
    def __init__(self, repo=DEFAULT_REPO, flags=LIVE_FLAGS, rerun=False, fetch=False, remote_ref="origin/main"):
        self.repo, self.flags, self.rerun, self.fetch, self.remote_ref = repo, flags, rerun, fetch, remote_ref
        self._fetched = False

    def git(self, *a):
        return _run(["git", "-C", self.repo, *a])

    def maybe_fetch(self):
        if self.fetch and not self._fetched:
            self.git("fetch", "-q", "origin")
            self._fetched = True


def _res(ok, detail, proof=""):
    return {"ok": ok, "detail": detail, "proof": proof}


def _need(c, *keys):
    miss = [k for k in keys if not c.get(k)]
    return _res(False, f"claim missing field(s): {', '.join(miss)}") if miss else None


def check_pushed(c, x):
    bad = _need(c, "sha")
    if bad:
        return bad
    x.maybe_fetch()
    rc, out, err = x.git("branch", "-r", "--contains", c["sha"])
    if rc != 0:
        return _res(False, f"sha {c['sha']} unknown to repo: {err.strip()[:120]}")
    if x.remote_ref not in [l.strip() for l in out.splitlines()]:
        return _res(False, f"{c['sha']} is not on {x.remote_ref}", f"git branch -r --contains {c['sha']}")
    if c.get("branch"):
        rc, out, _ = x.git("cherry", x.remote_ref, c["branch"])
        if rc == 0 and out.strip():
            return _res(False, f"branch {c['branch']} still has unpushed commits:\n{out.strip()[:200]}", f"git cherry {x.remote_ref} {c['branch']}")
    return _res(True, f"{c['sha']} is on {x.remote_ref}", f"git branch -r --contains {c['sha']}")


def check_branch_contains(c, x):
    bad = _need(c, "branch", "sha")
    if bad:
        return bad
    rc, _, err = x.git("merge-base", "--is-ancestor", c["sha"], c["branch"])
    if rc == 0:
        return _res(True, f"{c['branch']} contains {c['sha']}", "git merge-base --is-ancestor")
    return _res(False, f"{c['branch']} does not contain {c['sha']}" + (f" ({err.strip()[:100]})" if rc > 1 else ""))


def check_published(c, x):
    bad = _need(c, "id")
    if bad:
        return bad
    p = os.path.join(x.flags, "ready", c["id"] + ".json")
    if os.path.isfile(p):
        return _res(True, f"ready/{c['id']}.json exists", p)
    d = os.path.join(x.flags, "dryrun", c["id"])
    if os.path.isdir(d):
        hits = [f for f in os.listdir(d) if f.endswith("SMOKE-QUEUED.json")]
        if hits:
            return _res(True, f"smoke-queued marker {hits[0]}", os.path.join(d, hits[0]))
    return _res(False, f"no ready/{c['id']}.json and no SMOKE-QUEUED marker")


def check_smoke_pass(c, x):
    bad = _need(c, "id")
    if bad:
        return bad
    d = os.path.join(x.flags, "dryrun", c["id"])
    lo = os.path.join(d, "launcher.out")
    try:
        with open(lo, errors="replace") as f:
            lines = [l for l in f if re.match(r"==== dry run (PASS|FAIL)", l)]
    except OSError:
        return _res(False, f"cannot read {lo}")
    if not lines or not lines[-1].startswith("==== dry run PASS"):
        return _res(False, f"last dry-run verdict line is not PASS: {lines[-1].strip()[:100] if lines else 'none'}", lo)
    pj = os.path.join(d, "PASS.json")
    if not os.path.isfile(pj):
        return _res(False, "no PASS.json", pj)
    ready = os.path.join(x.flags, "ready", c["id"] + ".json")
    if os.path.isfile(ready) and os.path.getmtime(pj) < os.path.getmtime(ready):
        return _res(False, "PASS.json is older than the last publish", pj)
    return _res(True, "launcher.out ends PASS and PASS.json is not older than the publish", pj)


def check_filed(c, x):
    bad = _need(c, "id")
    if bad:
        return bad
    p = os.path.join(x.flags, "filing-done", c["id"] + ".FILED")
    return _res(os.path.isfile(p), ("exists: " if os.path.isfile(p) else "missing: ") + p, p)


def check_built(c, x):
    bad = _need(c, "lib", "symbol")
    if bad:
        return bad
    try:
        data = open(c["lib"], "rb").read()
    except OSError as e:
        return _res(False, f"cannot read {c['lib']}: {e}")
    ok = c["symbol"].encode() in data
    d = _res(ok, f"symbol {c['symbol']!r} {'found' if ok else 'NOT found'} in {c['lib']} (content proof, never mtime)", "strings|grep")
    if ok and c.get("commit"):
        d["detail"] += "; commit binding is the caller's to prove (symbol presence only)"
    return d


def check_ticked(c, x):
    bad = _need(c, "id", "file")
    if bad:
        return bad
    x.maybe_fetch()
    rc, out, err = x.git("show", f"{x.remote_ref}:{c['file']}")
    if rc != 0:
        return _res(False, f"cannot read {x.remote_ref}:{c['file']}: {err.strip()[:100]}")
    for n, line in enumerate(out.splitlines(), 1):
        if c["id"] in line:
            if re.search(r"\[x\]", line, re.I):
                if re.search(r"\[(?:no-)?belief:", line):
                    return _res(True, f"{c['file']}:{n} is [x] with a belief tag", f"git show {x.remote_ref}:{c['file']}")
                return _res(False, f"{c['file']}:{n} is [x] but has no belief tag")
            return _res(False, f"{c['file']}:{n} mentions {c['id']} but is not [x]")
    return _res(False, f"{c['id']} not found in {x.remote_ref}:{c['file']}")


PYTEST_SUM = re.compile(r"(\d+)\s+passed")
PYTEST_BAD = re.compile(r"(\d+)\s+(failed|errors?)\b")


def _judge_test_output(text):
    p, b = PYTEST_SUM.findall(text), PYTEST_BAD.findall(text)
    if b and any(int(n) for n, _ in b):
        return False, f"failures reported: {b}"
    if p:
        return True, f"{p[-1]} passed, no failures"
    if re.search(r"^OK\s*$", text, re.M):
        return True, "unittest OK"
    return False, "no pass/fail summary found"


def check_tests(c, x):
    if c.get("log"):
        try:
            text = open(c["log"], errors="replace").read()
        except OSError as e:
            return _res(False, f"cannot read test log {c['log']}: {e}")
        ok, why = _judge_test_output(text)
        if ok and c.get("expect_passed") and int(c["expect_passed"]) != int(PYTEST_SUM.findall(text)[-1]):
            return _res(False, f"log says {PYTEST_SUM.findall(text)[-1]} passed, claim says {c['expect_passed']}", c["log"])
        return _res(ok, f"log: {why}", c["log"])
    if c.get("cmd") and x.rerun:
        rc, out, err = _run(["bash", "-c", c["cmd"]], cwd=c.get("cwd") or x.repo, timeout=int(c.get("timeout", 900)))
        ok, why = _judge_test_output(out + err)
        return _res(ok and rc == 0, f"re-ran, rc={rc}: {why}", c["cmd"])
    return _res(False, "tests claimed but no log to read and no --rerun (or no cmd): unprovable")


def check_file_exists(c, x):
    bad = _need(c, "path")
    if bad:
        return bad
    return _res(os.path.exists(c["path"]), ("exists: " if os.path.exists(c["path"]) else "missing: ") + c["path"], c["path"])


CHECKS = {"pushed": check_pushed, "branch_contains": check_branch_contains, "published": check_published,
          "smoke_pass": check_smoke_pass, "filed": check_filed, "built": check_built, "ticked": check_ticked,
          "tests": check_tests, "file_exists": check_file_exists}


def verify(claims, ctx=None):
    ctx = ctx or Ctx()
    results = []
    for c in claims:
        fn = CHECKS.get(c.get("type"))
        r = fn(c, ctx) if fn else _res(False, f"unknown claim type {c.get('type')!r}: unprovable")
        try:
            r = r if isinstance(r, dict) else _res(False, "checker returned junk")
        except Exception as e:  # noqa: BLE001
            r = _res(False, f"checker crashed: {e}")
        results.append({"claim": c, **r})
    if not results:
        stamp, why = "UNVERIFIED", "no checkable claims found in the hand-back"
    elif all(r["ok"] for r in results):
        stamp, why = "VERIFIED", f"{len(results)} claim(s) verified"
    else:
        n = sum(1 for r in results if not r["ok"])
        stamp, why = "UNVERIFIED", f"{n} of {len(results)} claim(s) failed"
    return {"schema": "epyc.handback.stamp.v1", "stamp": stamp, "reason": why,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results}


def render(stamp):
    out = [f"{stamp['stamp']}: {stamp['reason']}"]
    for r in stamp["results"]:
        out.append(f"  [{'ok' if r['ok'] else 'NO'}] {r['claim'].get('type')}: {r['detail']}")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="hand-back text file")
    g.add_argument("--claims", help="JSON claims file")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--flags", default=LIVE_FLAGS)
    ap.add_argument("--rerun", action="store_true", help="re-run `cmd` of tests claims that have no log")
    ap.add_argument("--fetch", action="store_true", help="git fetch origin first")
    ap.add_argument("--json-out")
    a = ap.parse_args(argv)
    try:
        claims = extract_claims(open(a.text).read()) if a.text else load_claims(a.claims)
    except (OSError, ValueError) as e:
        print(f"usage error: {e}", file=sys.stderr)
        return 2
    stamp = verify(claims, Ctx(a.repo, a.flags, a.rerun, a.fetch))
    if a.json_out:
        with open(a.json_out, "w") as f:
            json.dump(stamp, f, indent=1)
    print(render(stamp))
    return 0 if stamp["stamp"] == "VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())

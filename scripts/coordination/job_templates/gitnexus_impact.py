#!/usr/bin/python3
"""Shared GitNexus impact job (replaces the ~40 vendored kvfork / slot-fabric `job.py` copies; operator decision
2026-11-06, friction review Pass 4 change 3a).

Deployed at /mnt/raid0/llm/tmp/compute-flags/bin/job_templates/gitnexus_impact.py; source of truth
scripts/coordination/job_templates/gitnexus_impact.py.

The old template ran analyze (~29 min, whole host) and scan in one process and exited rc=1 on any scan problem, so
every re-run repeated the analyze: 40 non-rc0 runs, ~9 host-hours. Here:
  * ANALYZE and SCAN are separate phases. A successful analyze writes out/ANALYZED.json (head, tree, repo name,
    parse probes). A later run whose graph is still fresh SKIPS analyze; a scan failure never triggers one.
  * Parse-cache staleness check (from KPF-41 r9/r10): `parse_probes` name nodes the patched parser must NOT emit
    (e.g. `__launch_bounds__` misparse in fattn-vec.cuh). A graph that still has them was built by a stale parser /
    parse cache -> re-analyze once with --force; if a FRESH analyze still shows them, rc=1 (parser defect).
  * A scan that cannot clear (ambiguous / partial / unresolved / vacuous) is an INCONCLUSIVE result: rc=0 with
    out/INCONCLUSIVE and a `scan_inconclusive` record, not rc=1. HIGH/CRITICAL risk -> rc=3 + OWNER_WARNING.

Config (JSON, `--config`): tree, head, repo_name, out, symbols [[name, file], ...], optional target_uids {name: uid},
require_callers [name...], parse_probes [{file, bad_names[], unique_function?}], analyze_argv (default: gitnexus
analyze --index-only ...), env {}, max_file_size (KiB, 512).

  gitnexus_impact.py --config job.json [--phase analyze|scan|all] [--check]
Exit: 0 complete or inconclusive, 1 analyze failed / stale parser after fresh analyze, 3 risk stop, 64 usage.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RC_OK, RC_ANALYZE_FAIL, RC_RISK, RC_USAGE = 0, 1, 3, 64
VALID_RISK = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class StepFailed(RuntimeError):
    pass


def default_runner(args, cwd, env, timeout=7200):
    p = subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout)
    return p.returncode, p.stdout, p.stderr


class ImpactJob:
    def __init__(self, cfg, runner=default_runner):
        self.cfg = cfg
        self.tree = Path(cfg["tree"])
        self.head = cfg["head"]
        self.repo_name = cfg["repo_name"]
        self.out = Path(cfg["out"])
        self.symbols = [tuple(s) for s in cfg["symbols"]]
        self.uids = dict(cfg.get("target_uids") or {})
        self.require_callers = set(cfg.get("require_callers") or [])
        self.probes = list(cfg.get("parse_probes") or [])
        self.env = dict(os.environ, GITNEXUS_REPO_NAME=self.repo_name, **(cfg.get("env") or {}))
        mfs = str(cfg.get("max_file_size", 512))
        self.analyze_argv = cfg.get("analyze_argv") or [
            "gitnexus", "analyze", "--index-only", "--workers", "1", "--force", "--verbose",
            "--max-file-size", mfs, "--name", self.repo_name, "--allow-duplicate-name"]
        self.runner = runner
        self.marker = self.out / "ANALYZED.json"

    # ------------------------------------------------------------ io
    def run(self, args, name=None):
        rc, out, err = self.runner(args, str(self.tree), self.env)
        if name:
            self.out.mkdir(parents=True, exist_ok=True)
            (self.out / f"{name}.stdout").write_text(out or "")
            (self.out / f"{name}.stderr").write_text(err or "")
        if rc:
            raise StepFailed(f"{args[:3]!r} rc={rc}" + (f"; see out/{name}.stderr" if name else ""))
        return out

    def emit(self, rec):
        self.out.mkdir(parents=True, exist_ok=True)
        with (self.out / "results.jsonl").open("a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

    # ------------------------------------------------------------ freshness
    def status_ok(self):
        try:
            status = self.run(["gitnexus", "status"], "status")
        except StepFailed:
            return False
        m = re.search(r"^Current commit:\s*([0-9a-f]{7,40})\s*$", status, re.M)
        printed = m.group(1) if m else ""
        return (str(self.tree) in status and bool(printed)
                and (self.head.startswith(printed) or printed.startswith(self.head)))

    def stale_parse(self):
        """Return a list of stale-parser findings (empty = fresh). Records unique Function uids it resolves."""
        bad = []
        for i, pr in enumerate(self.probes):
            names = list(pr.get("bad_names") or []) + ([pr["unique_function"]] if pr.get("unique_function") else [])
            q = ("MATCH (n) WHERE n.filePath = '%s' AND n.name IN [%s] RETURN n.id AS id"
                 % (pr["file"], ", ".join("'%s'" % n for n in names)))
            raw = self.run(["gitnexus", "cypher", "--repo", str(self.tree), q], f"parse-probe-{i}")
            try:
                md = json.loads(raw).get("markdown", "")
            except (ValueError, AttributeError):
                md = raw
            ids = re.findall(r"\| ((?:Function|Template|Method|Class|Struct):[^|]+?) \|", md)
            hits = [k for k in ids if any(k.endswith(":" + b) or (":" + b + ":") in k or k.endswith(b)
                                          for b in pr.get("bad_names") or [])]
            if hits:
                bad.append({"file": pr["file"], "misparse": hits})
                continue
            uf = pr.get("unique_function")
            if uf:
                funcs = [k for k in ids if k.startswith("Function:") and k.endswith(":" + uf)]
                if len(funcs) != 1:
                    bad.append({"file": pr["file"], "function_not_unique": uf, "nodes": ids})
                else:
                    self.uids.setdefault(uf, funcs[0])
        return bad

    def graph_fresh(self):
        if not self.marker.exists():
            return False, "no ANALYZED marker"
        try:
            m = json.loads(self.marker.read_text())
        except ValueError:
            return False, "unreadable ANALYZED marker"
        if m.get("head") != self.head or m.get("repo_name") != self.repo_name:
            return False, "marker for another head/repo"
        if not self.status_ok():
            return False, "gitnexus status does not identify the head"
        bad = self.stale_parse()
        if bad:
            return False, "stale parse cache: " + json.dumps(bad)
        return True, "fresh"

    # ------------------------------------------------------------ phases
    def analyze(self, force=False):
        """Returns (rc, why). Skips when the cached graph is fresh unless force."""
        if not force:
            fresh, why = self.graph_fresh()
            if fresh:
                self.emit({"type": "analyze_skipped", "head": self.head, "reason": "cached graph fresh"})
                return RC_OK, "cached"
            self.emit({"type": "analyze_needed", "head": self.head, "reason": why})
        try:
            self.run(self.analyze_argv, "analyze")
            if not self.status_ok():
                raise StepFailed("gitnexus status does not identify the exact head after analyze")
            bad = self.stale_parse()
        except StepFailed as e:
            self.emit({"type": "analyze_failed", "head": self.head, "error": str(e)})
            return RC_ANALYZE_FAIL, str(e)
        if bad:
            self.emit({"type": "analyze_failed", "head": self.head, "error": "parser defect after fresh analyze",
                       "findings": bad})
            return RC_ANALYZE_FAIL, "stale parser after fresh analyze"
        self.out.mkdir(parents=True, exist_ok=True)
        self.marker.write_text(json.dumps({"head": self.head, "tree": str(self.tree), "repo_name": self.repo_name,
                                           "parse_probes": self.probes}, indent=1, sort_keys=True) + "\n")
        self.emit({"type": "analyze_complete", "head": self.head})
        return RC_OK, "analyzed"

    def inconclusive(self, why):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "INCONCLUSIVE").write_text(f"STOP: {why}\n")
        self.emit({"type": "scan_inconclusive", "head": self.head, "reason": why, "partial": True})
        return RC_OK

    def scan(self):
        """Never analyzes. Needs a fresh graph; otherwise INCONCLUSIVE (rc 0)."""
        fresh, why = self.graph_fresh()
        if not fresh:
            return self.inconclusive(f"graph not fresh ({why}); run --phase analyze")
        n = len(self.symbols)
        for i, (sym, src) in enumerate(self.symbols, 1):
            cmd = ["gitnexus", "impact", sym, "--repo", str(self.tree), "--direction", "upstream"]
            cmd += ["--uid", self.uids[sym]] if sym in self.uids else ["--file", src]
            try:
                data = json.loads(self.run(cmd, f"impact-{i}"))
            except (StepFailed, ValueError) as e:
                return self.inconclusive(f"impact {sym}: {e}")
            valid = (isinstance(data, dict) and data.get("target") and not data.get("error")
                     and not data.get("partial") and not data.get("truncated")
                     and data.get("status") not in ("ambiguous", "not_found") and data.get("risk") in VALID_RISK)
            if not valid:
                return self.inconclusive(f"impact unresolved/partial for {sym}")
            if sym in self.require_callers and not data.get("impactedCount"):
                return self.inconclusive(f"{sym} has zero upstream callers (vacuous)")
            self.emit({"type": "native_impact", "head": self.head, "unit": i, "count": n, "symbol": sym,
                       "source": src, "impact": data})
            if data["risk"] in ("HIGH", "CRITICAL"):
                (self.out / "OWNER_WARNING").write_text(
                    f"STOP: {sym} upstream impact {data['risk']}; owner review required before source edits.\n")
                self.emit({"type": "risk_stop", "head": self.head, "symbol": sym, "risk": data["risk"]})
                return RC_RISK
        self.emit({"type": "scan_complete", "head": self.head, "impact_count": n, "partial": False})
        (self.out / "COMPLETE").write_text(f"All {n} upstream impact scans retained.\n")
        return RC_OK

    def main(self, phase="all"):
        if phase in ("analyze", "all"):
            rc, _ = self.analyze()
            if rc or phase == "analyze":
                return rc
        return self.scan()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gitnexus_impact.py")
    ap.add_argument("--config", required=True)
    ap.add_argument("--phase", choices=("analyze", "scan", "all"), default="all")
    ap.add_argument("--check", action="store_true", help="validate config only")
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.config).read_text())
    missing = [k for k in ("tree", "head", "repo_name", "out", "symbols") if k not in cfg]
    if missing:
        print(f"config missing {missing}", file=sys.stderr)
        return RC_USAGE
    if a.check:
        print("config ok; no graph work")
        return RC_OK
    return ImpactJob(cfg).main(a.phase)


if __name__ == "__main__":
    sys.exit(main())

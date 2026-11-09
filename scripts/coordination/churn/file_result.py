#!/usr/bin/env python3
"""CAF-5 — file a row's run result without an agent turn when its decision_rule is machine-checkable.

    python3 scripts/coordination/churn/file_result.py <row-id> [--flags DIR] [--verdict-json FILE]
                                                          [--lane DIR] [--dry-run]
                                                          [--allow-no-scratch-root] [--no-reclaim]

Reads the epyc.row.v3 manifest (<flags>/ready/<id>.json or ready/*/<id>.json), the end record
(<flags>/grants/<id>.ended|.complete, first line `rc=N ...`) and the result at `result_path`
(json: top-level keys, dotted paths allowed; jsonl: LAST record's keys plus `units` = record count;
`rc` always available). A decision_rule is MACHINE-CHECKABLE when it is a conjunction/disjunction
of `<metric> <op> <number>[%]` (ops < <= > >= == !=, `and`/`or`, parentheses). `%` and a leading
sign are notation only: the metric is compared against the bare number.

Exit codes: 0 verdict filed (pass|fail|inconclusive — a missing metric is inconclusive, never pass);
4 NEEDS-AGENT-VERDICT (rule not machine-checkable and no --verdict-json); 2 manifest or end record
missing / bad --verdict-json; 5 checkbox tick failed (verdict still written, FILED not touched);
6 REFUSED: the manifest has no absolute scratch_root under the tmp root ($RECLAIM_TMP_ROOT, default
/mnt/raid0/llm/tmp) — nothing written; `--allow-no-scratch-root` files anyway (operator 2026-11-07: a row with
no scratch_root can never be reclaimed).
COMMIT RECEIPT (operator 2026-11-07): `file_result.py <id> --receipt <commit>:<handoff.md>#<BOX-ID> [--verdict V] [--answer A]
[--repo DIR]` files a row from a verified verdict commit: the commit must be on origin/main, touch the named box line, and that
box line must mention the row id or its lineage; FILED quotes the box line. `--verdict SUPERSEDED|WITHDRAWN` (+ `--superseded-by ID`)
files a row that has no result of its own; `--answer NAME` (e.g. SURFACE_E2E_OK) is stored in the receipt. Every path is a no-op
(exit 0, NOOP) when filing-done/<id>.FILED exists, and FILED is written atomically (filing.write_filed). Exit 8: receipt refused.
SCOPE (CHURN-CONT-SCOPE): with --receipt, the commit's changed paths (`git diff-tree --raw`) must stay inside the row's
`scope` (optional manifest list of repo-relative globs; else default = the row's scratch_root/workdir/output_dir/result dir where
inside the repo, plus the receipt's handoff). `..`/absolute paths, gitlinks (160000), paths under a symlinked dir and symlinks
resolving outside scope are refused (exit 8, REFUSED ... scope: ...). The receipt's handoff is always in scope.
RECLAIM-AT-FILING: once the FILED receipt is written, reclaim_row.py <id> --apply --pre-filed frees the row's
declared raw scratch and row-owned worktrees (`--no-reclaim` skips; --dry-run runs it in dry-run mode). A reclaim
error or non-zero exit prints RECLAIM-ERROR and never changes the filing outcome.
The verdict record validates against scripts/coordination/filed_verdict.schema.json
(epyc.filed.verdict.v1, additionalProperties) and adds {row, verdict, rule, values, rc, result_path,
filed_by, at}. Stdlib only.
"""
import argparse, datetime, glob, hashlib, json, os, re, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "..", "..", "champion", "keep_tail"))
DEFAULT_FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")
OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b,
       ">=": lambda a, b: a >= b, "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
TOKEN = re.compile(r"\s*(?:(?P<num>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?%?)|(?P<op><=|>=|==|!=|<|>)"
                   r"|(?P<kw>\b(?:and|or)\b)|(?P<par>[()])|(?P<id>[A-Za-z_][\w.\-]*))")


class RuleError(ValueError):
    pass


class Missing(KeyError):
    pass


def tokenize(rule):
    pos, out = 0, []
    while pos < len(rule.rstrip()):
        m = TOKEN.match(rule, pos)
        if not m or m.end() == pos:
            raise RuleError(f"unparseable at {rule[pos:pos + 20]!r}")
        pos = m.end()
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
    return out


def parse(rule):
    """Return a nested tuple AST or raise RuleError. ('cmp', name, op, number) | ('and'|'or', a, b)."""
    toks = tokenize(rule)
    if not toks:
        raise RuleError("empty rule")
    i = [0]

    def peek():
        return toks[i[0]] if i[0] < len(toks) else (None, None)

    def take(kind=None, val=None):
        k, v = peek()
        if k is None or (kind and k != kind) or (val and v != val):
            raise RuleError(f"expected {val or kind}, got {v!r}")
        i[0] += 1
        return v

    def atom():
        if peek() == ("par", "("):
            take(); node = expr(); take("par", ")"); return node
        name = take("id"); op = take("op"); num = take("num")
        return ("cmp", name, op, float(num.rstrip("%")))

    def term():
        node = atom()
        while peek() == ("kw", "and"):
            take(); node = ("and", node, atom())
        return node

    def expr():
        node = term()
        while peek() == ("kw", "or"):
            take(); node = ("or", node, term())
        return node

    node = expr()
    if i[0] != len(toks):
        raise RuleError(f"trailing tokens from {toks[i[0]][1]!r}")
    return node


def lookup(metrics, name):
    cur = metrics
    for part in name.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise Missing(name)
        cur = cur[part]
    if isinstance(cur, bool):
        return float(cur)
    if isinstance(cur, (int, float)):
        return float(cur)
    try:
        return float(str(cur).strip().rstrip("%"))
    except ValueError:
        raise Missing(name)


def evaluate(node, metrics, values):
    if node[0] == "cmp":
        _, name, op, num = node
        v = lookup(metrics, name); values[name] = v
        return OPS[op](v, num)
    a = evaluate(node[1], metrics, values)
    b = evaluate(node[2], metrics, values)
    return (a and b) if node[0] == "and" else (a or b)


def load_manifest(flags, rid):
    # ready/.withdrawn/ too: glob's * skips dot-dirs, and a superseded predecessor must stay fileable (2026-11-05)
    for p in ([os.path.join(flags, "ready", rid + ".json")] + sorted(glob.glob(os.path.join(flags, "ready", "*", rid + ".json")))
              + [os.path.join(flags, "ready", ".withdrawn", rid + ".json")]):
        if os.path.isfile(p):
            with open(p) as fh:
                return p, json.load(fh)
    # A complete-in-smoke row is deliberately removed from READY. Accept its
    # archived manifest only with the matching completed-smoke receipt and
    # terminal grant, never an unpublished/failed qualification manifest.
    archive = os.path.join(flags, "dryrun", rid, "completed-manifest.json")
    receipt = os.path.join(flags, "dryrun", rid, "PASS.json")
    complete = os.path.join(flags, "grants", rid + ".complete")
    try:
        with open(archive) as fh:
            m = json.load(fh)
        with open(receipt) as fh:
            p = json.load(fh)
        if (os.path.isfile(complete) and isinstance(m, dict) and isinstance(p, dict)
                and m.get("schema") == "epyc.row.v3" and m.get("id") == rid
                and p.get("id") == rid and p.get("job_complete") is True
                and re.fullmatch(r"[0-9a-f]{64}", str(p.get("launcher_sha256") or ""))
                and re.fullmatch(r"[0-9a-f]{64}", str(p.get("engine_sha256") or ""))
                and (m.get("launcher") or {}).get("sha256") == p["launcher_sha256"]
                and (m.get("engine") or {}).get("sha256") == p["engine_sha256"]
                and m.get("result_format") == p.get("result_format")):
            return archive, m
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None, None


def load_end(flags, rid):
    for suf in (".ended", ".complete"):
        p = os.path.join(flags, "grants", rid + suf)
        if os.path.isfile(p):
            with open(p, errors="replace") as fh:
                line = fh.readline().strip()
            m = re.search(r"\brc=(\d+)", line)
            return p, (int(m.group(1)) if m else (0 if suf == ".complete" else None)), line
    return None, None, ""


def load_result(path, fmt):
    """Return (metrics dict, sha256 or None). Globs resolve to the last match in sorted order."""
    paths = sorted(glob.glob(path)) if any(c in path for c in "*?[") else [path]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        return {}, None
    with open(paths[-1], "rb") as fh:
        raw = fh.read()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    if fmt == "jsonl":
        recs = [json.loads(l) for l in text.splitlines() if l.strip()]
        last = recs[-1] if recs and isinstance(recs[-1], dict) else {}
        return dict(last, units=len(recs)), sha
    if fmt == "json":
        try:
            d = json.loads(text)
        except ValueError:
            return {}, sha
        return d if isinstance(d, dict) else {"value": d}, sha
    return {}, sha  # csv/tsv/text: only rc is checkable


def decide(rule, metrics):
    """-> (verdict, values, machine_checkable, reason)."""
    try:
        ast = parse(rule)
    except RuleError as e:
        return None, {}, False, str(e)
    values = {}
    try:
        ok = evaluate(ast, metrics, values)
    except Missing as e:
        return "inconclusive", values, True, f"metric missing from result: {e.args[0]}"
    return ("pass" if ok else "fail"), values, True, ""


def _gpu_row(m):
    return any("gpu" in str(m.get(k) or "").lower() or "mi210" in str(m.get(k) or "").lower()
               for k in ("lane", "declared_shape", "regions"))


def keep_tail_report(m, metrics, rid, flags, journal=None):
    """KEEP-TAIL-1 (operator 2026-11-06): every GPU A/B row's verdict carries P and F, automatically.

    A GPU row whose result carries per-arm timed samples (`samples_a`, `samples_b`; optional `effect_pct`,
    `timing_region` {warm_up,timed_loop,compile_import_check}) gets keep_tail.verdict() appended as rec["keep_tail"] and
    one line in <flags>/filing-done/keep_tail_counter.jsonl (the counter wrap-up checks: `keep_tail.py --counter`).
    A GPU row without samples records reported=false and is NOT counted. Never raises: reporting must not block filing."""
    if not _gpu_row(m):
        return None
    sa, sb = metrics.get("samples_a"), metrics.get("samples_b")
    if not (isinstance(sa, list) and isinstance(sb, list)):
        return {"reported": False, "reason": "no samples_a/samples_b in result"}
    try:
        import statistics
        import keep_tail
        eff = metrics.get("effect_pct")
        eff = float(eff) if isinstance(eff, (int, float)) else (statistics.median(sb) / statistics.median(sa) - 1.0) * 100.0
        region = metrics.get("timing_region") if isinstance(metrics.get("timing_region"), dict) else None
        j = journal or os.environ.get("KEEP_TAIL_JOURNAL")
        out = keep_tail.verdict(rid, eff, sa, sb, region=region, journal=Path(j) if j else None)
        return dict(out, reported=True)
    except Exception as e:  # noqa: BLE001
        return {"reported": False, "reason": f"keep_tail failed: {type(e).__name__}: {e}"}


def tick_line(rid, rc, verdict, values, filed_by):
    vals = " ".join(f"{k}={v:g}" for k, v in values.items())
    return (f"{rid} … ✅ {datetime.date.today().isoformat()} rc={rc} {verdict} {vals} "
            f"[no-belief: row verdict filed by {filed_by}]").replace("  ", " ")


def handoff_path(lane, hpath):
    """Resolve manifest basename aliases without allowing a tick outside the lane."""
    if not hpath or os.path.isabs(hpath) or ".." in hpath.split("/"):
        raise ValueError("handoff path must be lane-relative without parent traversal")
    if not hpath.endswith(".md"):
        raise ValueError("handoff path must name a Markdown file")
    if "/" not in hpath:
        hpath = os.path.join("handoffs", "active", hpath)
    root = os.path.realpath(lane)
    target = os.path.realpath(os.path.join(root, hpath))
    if os.path.commonpath((root, target)) != root:
        raise ValueError("handoff path resolves outside the lane")
    return target


def run_reclaim(argv):
    """Call reclaim_row.main(argv); any exception or non-zero exit prints RECLAIM-ERROR, never raises."""
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import reclaim_row
        code = reclaim_row.main(argv)
        if code:
            print(f"RECLAIM-ERROR {argv[0]}: reclaim_row exit {code}")
        return code
    except BaseException as e:  # noqa: BLE001 — SystemExit from argparse too
        print(f"RECLAIM-ERROR {argv[0]}: {type(e).__name__}: {e}")
        return -1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("row_id")
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--verdict-json", help="agent-written {verdict, rationale[, tick_text, filed_by]}")
    ap.add_argument("--lane", default=os.getcwd(), help="worktree root that holds handoffs/ (for --verdict-json tick_text)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-no-scratch-root", action="store_true")
    ap.add_argument("--no-reclaim", action="store_true")
    ap.add_argument("--receipt", metavar="COMMIT:HANDOFF#BOX", help="file from a verified verdict commit on origin/main")
    ap.add_argument("--verdict", help="with --receipt: the verdict word; alone: SUPERSEDED|WITHDRAWN (no result needed)")
    ap.add_argument("--answer", help="named answer stored in the receipt, e.g. SURFACE_E2E_OK")
    ap.add_argument("--superseded-by", metavar="ID")
    ap.add_argument("--filed-by", default=None)
    ap.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..", "..")))
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args(argv)
    rid, flags = a.row_id, a.flags
    import filing
    if filing.is_filed(flags, rid):
        print(f"NOOP {rid}: already FILED ({filing.filed_path(flags, rid)})"); return 0
    if a.receipt:
        code, msg = filing.file_receipt(flags, rid, a.receipt, repo=a.repo, verdict=a.verdict or "RECEIPT", answer=a.answer,
                                        by=a.filed_by or "file_result --receipt", reclaim=not a.no_reclaim, fetch=not a.no_fetch)
        if code != 0:
            print(msg, file=sys.stderr if code == 2 else sys.stdout)
        return {0: 0, 1: 0, 2: 8}[code]
    if a.verdict and a.verdict.upper() in filing.TERMINAL_VERDICTS and not a.verdict_json:
        r = filing.file_terminal(flags, rid, a.verdict, by=a.filed_by or "file_result", superseded_by=a.superseded_by,
                                 answer=a.answer, reclaim=not a.no_reclaim, dry_run=a.dry_run)
        print(r)
        return 0 if r in ("FILED", "NOOP") else 2
    mp, m = load_manifest(flags, rid)
    if not m:
        print(f"ERROR {rid}: no manifest in {flags}/ready/ or eligible completed-smoke archive", file=sys.stderr); return 2
    ep, rc, endline = load_end(flags, rid)
    if ep is None:
        print(f"ERROR {rid}: no grants/{rid}.ended|.complete in {flags}", file=sys.stderr); return 2
    agent = None
    if a.verdict_json:
        try:
            with open(a.verdict_json) as fh:
                agent = json.load(fh)
            if str(agent.get("verdict")).upper() in filing.TERMINAL_VERDICTS:
                r = filing.file_terminal(flags, rid, str(agent["verdict"]), by=str(agent.get("filed_by") or "agent"),
                                         superseded_by=agent.get("superseded_by"), answer=agent.get("answer"),
                                         note=str(agent.get("rationale") or ""), reclaim=not a.no_reclaim, dry_run=a.dry_run)
                print(r); return 0 if r in ("FILED", "NOOP") else 2
            assert agent.get("verdict") in ("pass", "fail", "inconclusive")
        except (OSError, ValueError, AssertionError) as e:
            print(f"ERROR {rid}: bad --verdict-json ({e}); need {{verdict: pass|fail|inconclusive|SUPERSEDED|WITHDRAWN, rationale[, answer]}}", file=sys.stderr); return 2
    rule = str(m.get("decision_rule") or "")
    result_path, fmt = str(m.get("result_path") or ""), str(m.get("result_format") or "json")
    metrics, sha = load_result(result_path, fmt) if result_path else ({}, None)
    metrics = dict(metrics, rc=rc if rc is not None else "?")
    verdict, values, machine, reason = decide(rule, metrics)
    filed_by = "file_result.py"
    if not machine:
        if agent is None:
            print(f"NEEDS-AGENT-VERDICT {rid}: {rule}"); return 4
        verdict, filed_by, reason = agent["verdict"], str(agent.get("filed_by") or "agent"), str(agent.get("rationale") or "")
    if not a.allow_no_scratch_root:
        sys.path.insert(0, os.path.join(HERE, "..", "job_templates"))
        import row_worktree
        serr = row_worktree.scratch_root_error(m.get("scratch_root"))
        if serr:
            print(f"REFUSED {rid}: {serr}; a row with no scratch_root can never be reclaimed "
                  f"(--allow-no-scratch-root to file anyway)", file=sys.stderr); return 6
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    rec = {"$schema": "epyc.filed.verdict.v1", "id": rid, "row": rid, "owner": str(m.get("owner") or "?"), "filed_at": now, "at": now,
           "outcome_class": "SCIENCE-VERDICT" if verdict in ("pass", "fail") else "PARTIAL-VERDICT", "phase": "filing",
           "compute_burned": True, "root_cause_family": None,
           "verdict": {"status": "filed", "kind": "science", "native_result_sha256": sha or hashlib.sha256(b"").hexdigest(),
                       "result": verdict}, "native_result_path": result_path, "result_exists": sha is not None,
           "row_verdict": verdict, "rule": rule, "machine_checkable": machine, "values": values, "rc": rc, "end_line": endline,
           "result_path": result_path, "result_format": fmt, "handoff_task": m.get("handoff_task"), "manifest": mp,
           "filed_by": filed_by, "reason": reason, "agent_verdict": agent, "dry_run": a.dry_run,
           "answer": (agent or {}).get("answer") or a.answer}
    kt = keep_tail_report(m, metrics, rid, flags)
    if kt is not None:
        rec["keep_tail"] = kt
    done = os.path.join(flags, "filing-done")
    summary = f"FILED {rid}: {verdict} rc={rc} rule={rule!r} values={json.dumps(values)} by={filed_by}" + (" (dry-run)" if a.dry_run else "")
    print(summary)
    if a.dry_run:
        print("SUGGESTED-TICK " + tick_line(rid, rc, verdict, values, filed_by))
        if not a.no_reclaim:
            run_reclaim([rid, "--flags", flags, "--pre-filed"])
        return 0
    os.makedirs(done, exist_ok=True)
    vtmp = os.path.join(done, f".{rid}.verdict.{os.getpid()}.tmp")
    with open(vtmp, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    os.replace(vtmp, os.path.join(done, rid + ".verdict.json"))
    if kt and kt.get("reported"):
        with open(os.path.join(done, "keep_tail_counter.jsonl"), "a") as fh:
            fh.write(json.dumps({"row": rid, "at": now, "P_pct": kt["P_pct"], "F_pct": kt["F_pct"], "refused": kt["refused"]}, sort_keys=True) + "\n")
    tick = (agent or {}).get("tick_text")
    task = str(m.get("handoff_task") or "")
    if tick and ":" in task:
        import flip_checkbox
        hpath, token = task.rsplit(":", 1)
        try:
            flip_checkbox.flip(handoff_path(a.lane, hpath), token, datetime.date.today().isoformat(),
                               f"rc={rc} {verdict}; {tick}", dry_run=False)
            print(f"TICKED {token} in {hpath}")
        except (flip_checkbox.CheckboxFlipError, ValueError) as e:
            print(f"ERROR tick failed: {e}", file=sys.stderr); return 5
    else:
        print("SUGGESTED-TICK " + tick_line(rid, rc, verdict, values, filed_by))
    if rec.get("answer"):
        summary += f" answer={rec['answer']}"
    if not filing.write_filed(flags, rid, summary, rec):
        print(f"NOOP {rid}: filed concurrently by another filer"); return 0
    if not a.no_reclaim:
        run_reclaim([rid, "--flags", flags, "--apply", "--pre-filed"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

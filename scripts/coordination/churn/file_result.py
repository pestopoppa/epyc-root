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

NO RESULT -> NO CLAIM (operator ruling 2026-11-21): a row with no FINISHED RESULT (no result file, run not ended rc 0
complete, or complete:false) whose verdict would be inconclusive / needs-agent is filed SUPERSEDED (a successor row
exists: filing.no_result_successor) or WITHDRAWN by default - never inconclusive. A measured pass/fail stays as decided.

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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import filing  # noqa: E402  (filing owns the end-record / manifest readers; filing never imports file_result)
from filing import DEFAULT_FLAGS, end_source, load_end, load_manifest, run_reclaim, smoke_complete_end  # noqa: E402,F401
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


def window_end_resumable(m, rc, endline):
    """A row published resumable: true whose engine ended it at the grant end (rc=75 reason=hard-end, or the job's own
    rc=75 window exit reason=exited) - not a stop, not the disk floor."""
    if not m.get("resumable") or rc != 75:
        return False
    r = re.search(r"\breason=(\S+)", endline or "")
    return bool(r) and r.group(1) in ("hard-end", "exited")


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


def token_accounting(m, flags, compute=None):
    """TOKEN-AUDIT-6: the filing record carries the token figure of the row's owner session (churn/tokens_per_task.py).

    Scope is honest: Codex rollouts are attributed per SESSION per UTC day, not per row, so the figure is the owner session's
    tokens today, its completed-task count and tokens per task (None when nothing completed). Never raises."""
    try:
        if compute is None:
            import tokens_per_task
            compute = tokens_per_task.compute
        owner = str(m.get("owner") or "")
        slug = re.sub(r"^(handoff-|h-)", "", owner)
        r = (compute(flags=flags).get("per") or {}).get(slug)
        if r is None:
            return {"available": False, "owner_slug": slug, "reason": "no rollout tokens attributed to the owner session today"}
        return {"available": True, "owner_slug": slug, "scope": "owner session, UTC day of filing",
                "tokens": r["tokens"], "input": r["input"], "output": r["output"], "completed": r["completed"],
                "tokens_per_task": r["tokens_per_task"]}
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"token accounting failed: {type(e).__name__}: {e}"}


def tick_line(rid, rc, verdict, values, filed_by):
    vals = " ".join(f"{k}={v:g}" for k, v in values.items())
    return (f"{rid} … ✅ {datetime.date.today().isoformat()} rc={rc} {verdict} {vals} "
            f"[no-belief: row verdict filed by {filed_by}]").replace("  ", " ")


def done_when_refusal(lane, task, verdict, result_path, rec):
    """C2 / AK audit B13: reason string when the row's box has a MACHINE-CHECKABLE done-when (verdict / file /
    artifact class) that this filed result does not satisfy, else None. Free-text and command done-whens never
    refuse here (a row result carries no command rc)."""
    try:
        for cand in (os.path.join(os.path.dirname(HERE), "handoffs"),                    # deployed: bin/handoffs
                     os.path.join(os.path.dirname(os.path.dirname(HERE)), "handoffs")):  # repo: scripts/handoffs
            if cand not in sys.path:
                sys.path.insert(0, cand)
        import done_when as _dw
        import task_lint_core as _l1
    except ImportError:
        return None
    hpath, token = task.rsplit(":", 1)
    try:
        lines = open(handoff_path(lane, hpath), encoding="utf-8").read().split("\n")
    except (OSError, ValueError):
        return None
    idx = next((i for i, l in enumerate(lines) if _l1.CHECKBOX.match(l) and _l1.head_id(l) == token.strip()), None)
    if idx is None:
        return None
    paths = [p for p in (result_path, (rec or {}).get("result_path")) if p]
    res, why, text = _dw.check_box(lines, idx, {"verdict": verdict, "paths": paths,
                                                "artifact_class": (rec or {}).get("artifact_class")}, lane)
    if res == "fail" and _dw.parse(text)["kind"] in ("verdict", "file", "artifact_class"):
        return f"done when: {text!r}; {why}"
    return None


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


DECLARED_NONPASS = re.compile(r"^\s*(?:DROP\b|DROP\(|FUTILITY_|diagnostic\b)|\bDROP\(diagnostic|\bFUTILITY_[A-Z]", re.I)


def coerce_declared_nonpass(agent):
    """D9 2026-11-19: an agent verdict of pass whose own rationale/answer declares DROP(diagnostic...) or FUTILITY_*
    is not a pass (c6-admission-live-proof-r12 was filed pass with a DROP rationale). File it inconclusive, recorded."""
    if not isinstance(agent, dict) or agent.get("verdict") != "pass":
        return agent
    text = f"{agent.get('answer') or ''}\n{agent.get('rationale') or ''}"
    if DECLARED_NONPASS.search(text):
        agent["coerced_from"] = "pass"
        agent["verdict"] = "inconclusive"
        agent["rationale"] = ("[coerced pass->inconclusive: rationale declares DROP/diagnostic/FUTILITY] "
                              + str(agent.get("rationale") or ""))
    return agent


RECORD_NONPASS_TOKEN = re.compile(r"\bDROP\(|\bFUTILITY_[A-Z]")
RECORD_STATUS_DIAGNOSTIC = re.compile(r"^\s*(?:DROP\b|diagnostic\b)", re.I)


def record_declares_nonpass(metrics):
    """F3 (AK audit B3): the result record's own text when it declares a non-pass, else None. Review S3: only the
    `DROP(` / `FUTILITY_<X>` tokens count in status/rationale/answer (a passing answer may mention "diagnostic"); the
    word diagnostic (or a bare DROP) counts only as the leading word of the `status` field."""
    if not isinstance(metrics, dict):
        return None
    texts = [str(metrics.get(k) or "") for k in ("status", "rationale", "answer")]
    if any(RECORD_NONPASS_TOKEN.search(t) for t in texts) or RECORD_STATUS_DIAGNOSTIC.match(texts[0]):
        return "\n".join(t for t in texts if t).strip()
    return None


def correct_filed(flags, rid, verdict, by, reason, dry_run=False):
    """D9 2026-11-19: the row OWNER re-files an already-FILED row. The old FILED + verdict record are kept beside the
    new ones (<rid>.FILED.superseded-<ts>, <rid>.verdict.superseded-<ts>.json). -> exit code."""
    if verdict not in ("pass", "fail", "inconclusive"):
        print(f"ERROR {rid}: --correct takes pass|fail|inconclusive", file=sys.stderr); return 2
    if not reason:
        print(f"ERROR {rid}: --correct needs --reason", file=sys.stderr); return 2
    if not filing.is_filed(flags, rid):
        print(f"ERROR {rid}: --correct needs an existing FILED receipt", file=sys.stderr); return 2
    _, m = load_manifest(flags, rid)
    owner = str((m or {}).get("owner") or "")
    if not owner or by != owner:
        print(f"REFUSED {rid}: --correct only by the row owner ({owner or 'unknown'}); --filed-by {by!r}", file=sys.stderr); return 8
    done = os.path.join(flags, "filing-done")
    fp, vp = filing.filed_path(flags, rid), os.path.join(done, rid + ".verdict.json")
    old_line = open(fp).read().strip()
    old = json.load(open(vp)) if os.path.exists(vp) else {}
    old_v = old.get("row_verdict") or (old_line.split(":", 1)[1].split()[0] if ":" in old_line else "?")
    coerced = None
    if verdict == "pass":   # F3: --correct pass is coerced like an agent pass when the reason or the record declares DROP
        rp, fmt = str((m or {}).get("result_path") or ""), str((m or {}).get("result_format") or "json")
        declared = (reason if DECLARED_NONPASS.search(reason) else None) or (record_declares_nonpass(load_result(rp, fmt)[0]) if rp else None)
        if declared:
            coerced, verdict = "pass", "inconclusive"
            reason = f"[coerced pass->inconclusive: declares DROP/diagnostic/FUTILITY: {declared[:120]}] {reason}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    rec = dict(old, row_verdict=verdict, filed_by=by, filed_at=now, at=now, reason=reason,
               outcome_class="SCIENCE-VERDICT" if verdict in ("pass", "fail") else "PARTIAL-VERDICT",
               corrected_from=old_v, corrected_at=now, superseded_filed_line=old_line)
    if coerced:
        rec["coerced_from"] = coerced
    if isinstance(rec.get("verdict"), dict):
        rec["verdict"] = dict(rec["verdict"], result=verdict)
    summary = f"FILED {rid}: {verdict} rc={old.get('rc', '?')} by={by} corrected_from={old_v} reason={reason!r}"
    print(summary + (" (dry-run)" if dry_run else ""))
    if dry_run:
        return 0
    ts = now.replace(":", "").replace("+0000", "Z")
    os.replace(fp, f"{fp}.superseded-{ts}")
    if os.path.exists(vp):
        os.replace(vp, os.path.join(done, f"{rid}.verdict.superseded-{ts}.json"))
    if not filing.write_filed(flags, rid, summary, rec):
        print(f"ERROR {rid}: filed concurrently during correction; old receipt kept at {fp}.superseded-{ts}", file=sys.stderr); return 2
    return 0



def _default_repo():
    """F5 review S2: config/repo reads go through toolroot.resolve (hub view first), never a stale checkout's copy."""
    own = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    try:
        try:
            import toolroot
        except ImportError:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import toolroot
        hub = toolroot.resolve(".", __file__)
        return os.path.normpath(hub) if os.path.isdir(os.path.join(hub, "handoffs")) else own
    except Exception:  # noqa: BLE001
        return own


def _toolroot_banner():
    """F5: print tool-commit / stale-checkout WARN (toolroot.py beside this file when installed, else the checkout's)."""
    try:
        try:
            import toolroot
        except ImportError:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import toolroot
        toolroot.banner(__file__)
    except Exception:  # noqa: BLE001 - never blocks the tool
        pass


def main(argv=None):
    _toolroot_banner()
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
    ap.add_argument("--repo", default=_default_repo(), help="repo for --receipt verification (default: the hub view via "
                    "toolroot.resolve, else this file's checkout)")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--no-manifest", action="store_true",
                    help="LEGACY row that never had a manifest: close from its .ended record (needs --owner; --verdict SUPERSEDED|"
                         "WITHDRAWN or --verdict-json; refused if a manifest or FILED exists; never reclaims)")
    ap.add_argument("--owner", help="with --no-manifest: the owner recorded on the filing")
    ap.add_argument("--correct", metavar="VERDICT", help="re-file an already-FILED row (pass|fail|inconclusive); owner only "
                                                          "(--filed-by must equal the manifest owner), needs --reason")
    ap.add_argument("--reason", help="with --correct: why the filed verdict was wrong")
    a = ap.parse_args(argv)
    rid, flags = a.row_id, a.flags
    if a.correct:
        return correct_filed(flags, rid, a.correct, a.filed_by or "", a.reason or "", a.dry_run)
    if filing.is_filed(flags, rid):
        print(f"NOOP {rid}: already FILED ({filing.filed_path(flags, rid)})"); return 0
    if a.no_manifest:
        if a.receipt:
            print("ERROR --no-manifest cannot be combined with --receipt", file=sys.stderr); return 2
        agent = {}
        if a.verdict_json:
            try:
                with open(a.verdict_json) as fh:
                    agent = json.load(fh)
                assert isinstance(agent, dict) and agent.get("verdict")
                coerce_declared_nonpass(agent)
            except (OSError, ValueError, AssertionError) as e:
                print(f"ERROR {rid}: bad --verdict-json ({e})", file=sys.stderr); return 2
        verdict = agent.get("verdict") or a.verdict
        if not verdict:
            print(f"ERROR {rid}: --no-manifest needs --verdict SUPERSEDED|WITHDRAWN or --verdict-json", file=sys.stderr); return 2
        if not a.verdict_json and str(verdict).upper() not in filing.TERMINAL_VERDICTS:
            print(f"ERROR {rid}: plain --verdict under --no-manifest allows only SUPERSEDED|WITHDRAWN; "
                  f"pass|fail|inconclusive need --verdict-json with a rationale", file=sys.stderr); return 2
        r = filing.file_legacy_no_manifest(
            flags, rid, verdict, owner=a.owner, by=str(agent.get("filed_by") or a.filed_by or "file_result --no-manifest"),
            note=str(agent.get("rationale") or ""), superseded_by=agent.get("superseded_by") or a.superseded_by,
            answer=agent.get("answer") or a.answer, dry_run=a.dry_run)
        print(r)
        return 0 if r in ("FILED", "NOOP", "WOULD-FILE") else 2
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
        print(f"ERROR {rid}: no grants/{rid}.ended|.complete (or completed-smoke dryrun/{rid}/ended) in {flags}", file=sys.stderr); return 2
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
            coerce_declared_nonpass(agent)
        except (OSError, ValueError, AssertionError) as e:
            print(f"ERROR {rid}: bad --verdict-json ({e}); need {{verdict: pass|fail|inconclusive|SUPERSEDED|WITHDRAWN, rationale[, answer]}}", file=sys.stderr); return 2
    rule = str(m.get("decision_rule") or "")
    result_path, fmt = str(m.get("result_path") or ""), str(m.get("result_format") or "json")
    metrics, sha = load_result(result_path, fmt) if result_path else ({}, None)
    metrics = dict(metrics, rc=rc if rc is not None else "?")
    verdict, values, machine, reason = decide(rule, metrics)
    filed_by = "file_result.py"
    coerced_from = None
    declared = record_declares_nonpass(metrics) if machine and verdict == "pass" else None
    if declared:   # F3: the machine rule passed but the record itself says DROP(...)/FUTILITY_/diagnostic
        coerced_from, verdict = "pass", "inconclusive"
        reason = f"[coerced pass->inconclusive: result record declares {declared[:120]}] {reason or ''}".strip()
    resumable_end = window_end_resumable(m, rc, endline)
    if not resumable_end and not filing.finished_result(rc, endline, metrics, sha is not None) \
            and (not machine or verdict == "inconclusive") and (agent is None or agent.get("verdict") == "inconclusive"):
        # NO RESULT -> NO CLAIM (operator ruling 2026-11-21): a row that never produced a finished RESULT is filed
        # SUPERSEDED when a successor row exists, otherwise WITHDRAWN - never inconclusive. Owners need not remember it.
        succ = filing.no_result_successor(flags, rid)
        term = "SUPERSEDED" if succ else "WITHDRAWN"
        note = (f"no finished RESULT (rc={rc}, result_exists={sha is not None}); no result -> no claim "
                f"(filing rule 2026-11-21)" + (f"; was {agent['verdict']}" if agent else ""))
        r = filing.file_terminal(flags, rid, term, by=str((agent or {}).get("filed_by") or "file_result.py:no-result-rule"),
                                 superseded_by=succ, note=note, reclaim=not a.no_reclaim, dry_run=a.dry_run)
        print(r)
        return 0 if r in ("FILED", "NOOP") else 2
    if resumable_end and verdict != "pass":
        # ONE BOOKING DURATION (pipeline audit 2026-11-10 #3): a resumable row's window end is a normal end
        verdict, machine = "partial", True
        reason = "resumable row reached its window end: partial, resumes (republish the next round; the job continues from its checkpoint)"
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
           "end_record": ep, "source": end_source(ep), "result_path": result_path, "result_format": fmt, "handoff_task": m.get("handoff_task"), "manifest": mp,
           "filed_by": filed_by, "reason": reason, "agent_verdict": agent, "dry_run": a.dry_run,
           "answer": (agent or {}).get("answer") or a.answer}
    if coerced_from:
        rec["coerced_from"] = coerced_from
    kt = keep_tail_report(m, metrics, rid, flags)
    if kt is not None:
        rec["keep_tail"] = kt
    rec["tokens"] = token_accounting(m, flags)
    done = os.path.join(flags, "filing-done")
    summary = (f"FILED {rid}: {verdict} rc={rc} rule={rule!r} values={json.dumps(values)} by={filed_by}"
               + (" source=smoke-complete" if end_source(ep) == "smoke-complete" else "")) + (" (dry-run)" if a.dry_run else "")
    print(summary)
    if a.dry_run:
        print("SUGGESTED-TICK " + tick_line(rid, rc, verdict, values, filed_by))
        if not a.no_reclaim:
            run_reclaim([rid, "--flags", flags, "--pre-filed"])
        return 0
    tick = (agent or {}).get("tick_text")
    task = str(m.get("handoff_task") or "")
    try:   # C4: a box moved by a track split since publish is ticked where it lives now (.moves.jsonl)
        import handoff_ref as _hr
        moved = _hr.resolve(task, a.lane, m.get("handoff_task_sha")) if ":" in task else None
        if moved and moved != _hr.key(task):
            print(f"NOTE handoff_task {task} moved -> {moved}")
            task = moved
    except (ImportError, AttributeError):
        pass
    refused = done_when_refusal(a.lane, task, verdict, result_path, rec) if tick and ":" in task else None
    if refused:
        rec["tick_refused"] = refused      # C2: durable in verdict.json, so dashboard/verdict_count see it without notify
    os.makedirs(done, exist_ok=True)
    vtmp = os.path.join(done, f".{rid}.verdict.{os.getpid()}.tmp")
    with open(vtmp, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    os.replace(vtmp, os.path.join(done, rid + ".verdict.json"))
    if kt and kt.get("reported"):
        with open(os.path.join(done, "keep_tail_counter.jsonl"), "a") as fh:
            fh.write(json.dumps({"row": rid, "at": now, "P_pct": kt["P_pct"], "F_pct": kt["F_pct"], "refused": kt["refused"]}, sort_keys=True) + "\n")
    if refused:
        # C2: the result is FILED (verdict written, FILED below) but the box is NOT ticked; the owner is alerted
        print(f"TICK-REFUSED {task}: {refused}", file=sys.stderr)
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rowflow"))
            import notify as _nt
            _nt.emit(flags, "tick-refused", rid, hashlib.sha1(refused.encode()).hexdigest()[:10],
                     f"tick refused for {task}: {refused}", "warning", owner=str(m.get("owner") or ""),
                     detail={"handoff_task": task, "verdict": verdict, "result_path": result_path, "reason": refused})
        except Exception as e:  # noqa: BLE001 -- the alert is best effort; the refusal itself already happened
            print(f"WARN tick-refused alert not sent: {type(e).__name__}: {e}", file=sys.stderr)
        tick = None
    if tick and ":" in task:
        import flip_checkbox
        hpath, token = task.rsplit(":", 1)
        try:
            flip_checkbox.flip(handoff_path(a.lane, hpath), token, datetime.date.today().isoformat(),
                               "; ".join(x for x in (f"{verdict} rc={rc}", flip_checkbox.evidence_note_text(tick),
                                                    f"result {result_path or 'n/a'}") if x), dry_run=False,
                               belief="cc")   # review S2: a filed row result is a result tick, result path on the line
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

#!/usr/bin/env python3
"""propose_rewrites.py — LLM rewrite PROPOSALS for open boxes that fail lint a / e / s (handoff standard Stage C, C1;
operator decision 6). Proposals land as NEEDS-OWNER children via `handoff_box.py propose`; the parent is never edited
and nothing is ever applied here. The owning session accepts / edits / rejects them at its wrap-up
(agents/commands/wrap-up.md Step 2 -> "Proposals").

Selection: `.box-index.json` records with state `open`, an `**ID**`, no hold, lint fails ⊇ {a} or {e} or {s}, no
pending proposal child yet, in the top-N rows of `backlog-priority.json` (row_rank order, then backlog position).

Model: the cheapest capable tier, one turn per box -- `claude -p --model haiku` with tools, MCP, settings and the
project context stripped (~0.6 k tokens of overhead per call). Input: the box's own block, its heading chain and the 20
lines above it. Output JSON: {"done_when": str} | {"split": [{"text", "done_when"}]} | {"stop_rule": str}, plus
"rationale".

Budget (standard §6 step 3): <= --per-box-tokens uncached tokens per box (default 30 k), <= --max-boxes boxes
(default 900), <= --budget-tokens total (default 30 M). Back-pressure is PER HANDOFF: a file whose pending proposals
reach max(8, 20 % of its dispatchable+pending) is skipped and the run moves to the next file; the global pending share
in the top rows is reported only. Owners are asked by the dispatcher (`proposals-pending` event, handoff_sessions);
ownerless handoffs go to the pipeline-mgmt queue (--review-queue); proposals pending > 14 d expire (--expire).
Every call is appended to --ledger (JSONL: box, tokens, outcome). `--dry-run` prints, writes nothing to handoffs.

    python3 scripts/handoffs/propose_rewrites.py [--top-rows 10] [--max-boxes N] [--dry-run] [--ledger PATH]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "coordination"))
import box_index as BI  # noqa: E402
import handoff_box as HB  # noqa: E402
import task_lint_core as L1  # noqa: E402

TARGET_FAILS = ("a", "e", "s")
SYSTEM = ("You rewrite backlog task boxes into dispatchable form. Reply with ONE JSON object and nothing else. Never "
          "change the task's meaning or invent facts not present in the box.")
PROMPT = """A handoff task box fails these lint rules: {fails}
  a = no mechanically checkable `done when` (test command / file+field / verdict text / row PASS)
  e = too big for one turn (needs a split into <= 4 children)
  s = a measurement without a stop rule (question / effect vs error / checkpoints / stop-on-answer / futility)

Heading chain: {heads}

Context (20 lines above the box):
{context}

The box (its own block):
{box}

Return exactly one JSON object:
- for a: {{"done_when": "<checkable condition>", "rationale": "<one sentence>"}}
- for e: {{"split": [{{"text": "<imperative one-sentence child task>", "done_when": "<checkable condition>"}}, ...], "rationale": "..."}}
- for s: {{"stop_rule": "<question; effect vs error; checkpoints; stop-on-answer; futility>", "done_when": "...", "rationale": "..."}}
Prefer the first applicable of e, s, a. Keep each value under 240 characters."""


def heading_chain(lines: list[str], i: int) -> str:
    chain = {}
    for line in lines[:i]:
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            chain = {k: v for k, v in chain.items() if k < lvl}
            chain[lvl] = m.group(2).strip()
    return " > ".join(chain[k] for k in sorted(chain))


def candidates(doc: dict, top_rows: int) -> list[tuple[str, dict]]:
    boxes = doc.get("boxes") or {}
    has_child = {r.get("parent") for r in boxes.values() if r.get("proposed_by")}
    ranks = sorted({r["row_rank"] for r in boxes.values() if r.get("row_rank") is not None})[:top_rows]
    out = []
    for k, r in boxes.items():
        if r.get("row_rank") not in ranks or r.get("state") != "open" or not r.get("id") or r.get("holds"):
            continue
        if r.get("proposed_by") or r["id"] in has_child:
            continue
        if k != r["id"]:
            continue                     # duplicate ID in the repo (box_index keys it file#sha): not addressable
        fails = set((r.get("lint") or {}).get("fails") or [])
        if fails & set(TARGET_FAILS):
            out.append((k, r))
    out.sort(key=lambda kr: (kr[1]["row_rank"], kr[1].get("file", ""), kr[1].get("pos_in_backlog") or 10 ** 6,
                             kr[1].get("line", 0)))
    return out


def pending_share(doc: dict, top_rows: int) -> float:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "coordination"))
    boxes = doc.get("boxes") or {}
    ranks = sorted({r["row_rank"] for r in boxes.values() if r.get("row_rank") is not None})[:top_rows]
    top = [r for r in boxes.values() if r.get("row_rank") in ranks]
    pending = sum(1 for r in top if r.get("proposed_by") and r.get("state") == "needs-owner")
    admitted = sum(1 for r in top if BI.dispatchable(r))
    return pending / max(1, pending + admitted)


FILE_CAP_SHARE, FILE_CAP_MIN = 0.20, 8


def file_at_cap(doc: dict, rel: str) -> tuple[bool, int, int]:
    """Per-handoff back-pressure (C1 review): (at cap?, pending, cap) where cap = max(8, 20% of dispatchable+pending
    in THAT file). A file at cap is skipped; the run continues with the next file."""
    recs = [r for r in (doc.get("boxes") or {}).values() if r.get("file") == rel]
    pending = sum(1 for r in recs if r.get("proposed_by") and r.get("state") == "needs-owner")
    disp = sum(1 for r in recs if BI.dispatchable(r))
    cap = max(FILE_CAP_MIN, int(FILE_CAP_SHARE * (disp + pending)))
    return pending >= cap, pending, cap


def expire(root: Path, days: int = 14, today: str | None = None, dry_run: bool = False) -> list[str]:
    """C1 expiry: a proposal pending more than `days` is auto-rejected to `## History` as
    `[declined: taskflow-expiry <date> pending > <days> d]` (handoff_box.py reject). Returns the expired ids."""
    import datetime as _d
    now = _d.date.fromisoformat(today) if today else _d.date.today()
    doc = BI.load(root, regenerate=not dry_run)
    out = []
    for k, r in (doc.get("boxes") or {}).items():
        if not (r.get("state") == "needs-owner" and r.get("proposed_by") and r.get("id") == k):
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(r["proposed_by"]))
        if not m or (now - _d.date.fromisoformat(m.group(1))).days <= days:
            continue
        a = argparse.Namespace(box=k, by="taskflow-expiry", reason=f"pending > {days} d", date=now.isoformat())
        try:
            HB.apply(root / r["file"], "reject", a, root, dry_run=dry_run)
            out.append(k)
        except HB.BoxError as exc:
            print(f"EXPIRE-SKIP {k}: {exc}", file=sys.stderr)
    return out


def owner_of(rel: str, registry: dict, root: Path) -> str:
    """Who reviews a handoff's proposals: a live (not done/retired) registry session whose handoff is this file, else
    the handoff's `**Owner**:` header, else `pipeline-mgmt` (delegated review)."""
    name = Path(rel).name
    live = [s for s, e in (registry.get("sessions") or {}).items() if isinstance(e, dict)
            and Path(str(e.get("handoff") or "")).name == name and e.get("status") not in ("done", "retired")]
    if live:
        return sorted(live)[0]
    try:
        for line in (root / rel).read_text(encoding="utf-8").split("\n")[:60]:
            m = re.match(r"^\*\*Owner\*\*:\s*(.+?)\s*$", line.strip())
            if m and m.group(1).strip() and m.group(1).strip().lower() not in ("none", "-", "—"):
                return m.group(1).strip()
    except OSError:
        pass
    return "pipeline-mgmt"


def review_queue(root: Path, registry: dict, out_path: str) -> int:
    """Write the pipeline-mgmt delegated-review queue: pending proposals in handoffs with no live owner session and no
    `**Owner**` header. pipeline-mgmt ACCEPTS only when the child's done-when is checkable against the parent, else
    rejects with `[declined: pipeline-mgmt <date> no owner to judge]`."""
    doc = BI.load(root, regenerate=False)
    rows = []
    for k, r in sorted((doc.get("boxes") or {}).items(), key=lambda kr: (kr[1].get("file", ""), kr[1].get("line", 0))):
        if r.get("state") == "needs-owner" and r.get("proposed_by") and owner_of(r["file"], registry, root) == "pipeline-mgmt":
            rows.append(f"- [ ] `{r['file']}` **{k}** (parent {r.get('parent')}) — done when: {r.get('done_when') or '—'}")
    head = ("# pipeline-mgmt proposal review queue (generated by propose_rewrites.py --review-queue)\n\n"
            "Handoffs with pending proposals and NO live owner session or `**Owner**` header. Rule: ACCEPT only when "
            "the child's done-when is checkable against the parent (delete NEEDS-OWNER + `· proposed-by:`); otherwise "
            "`handoff_box.py reject --file <f> <ID> --by pipeline-mgmt --reason \"no owner to judge\"`.\n\n")
    Path(out_path).write_text(head + ("\n".join(rows) or "_(empty)_") + "\n", encoding="utf-8")
    return len(rows)


def claude_runner(prompt: str, timeout: int = 180) -> tuple[str, dict]:
    """(text, usage) from one stripped-context haiku turn."""
    cwd = os.environ.get("PROPOSE_SCRATCH") or "/tmp"
    r = subprocess.run(["claude", "-p", "--model", "haiku", "--output-format", "json", "--no-session-persistence",
                        "--tools", "", "--strict-mcp-config", "--setting-sources", "", "--system-prompt", SYSTEM, prompt],
                       cwd=cwd, capture_output=True, text=True, timeout=timeout)
    d = json.loads(r.stdout or "{}")
    return str(d.get("result") or ""), d.get("usage") or {}


def uncached(usage: dict) -> int:
    return int(usage.get("input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0) + \
        int(usage.get("output_tokens") or 0)


def parse_reply(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    return d if isinstance(d, dict) and (d.get("done_when") or d.get("split") or d.get("stop_rule")) else None


_UNSAFE = re.compile(r"[·\u2022]|<!--|-->|\[\s*[xX ]?\s*\]|\bNEEDS-(?:OWNER|OPERATOR|DECOMPOSITION)\b|✅|❄|\*\*")


def clean(value, limit: int = 240) -> str:
    """Model text is DATA: one line, no field separators (`·`), no checkbox / tick / freeze markers, no HTML
    comments, no bold-ID markup, no NEEDS-* tokens -- so a reply can never inject a `· gate:` / `· done when:` field,
    a second box, a tick or an ID into someone else's handoff."""
    t = _UNSAFE.sub(" ", " ".join(str(value or "").split()))
    return " ".join(t.split())[:limit]


def parent_headline(rec: dict) -> str:
    """The parent's FULL headline minus the checkbox, the `**ID**` token (task_lint_core.head_id) and markup, <= 200
    chars. Legacy headlines put the whole task inside the bold (`**S-19 — port the encoder (PACKAGE M-4) …**`), so
    stripping "the first bold span" would leave garbage (C1 review B1)."""
    line = rec.get("text", "")
    m = L1.CHECKBOX.match(line)
    body = m.group(3) if m else line
    bid = rec.get("id") or L1.head_id(line) or ""
    bold = re.match(r"^\s*\*\*(.+?)\*\*", body)
    inner = bold.group(1).strip() if bold else ""
    # strip the ID only when the bold span IS the id, or the id is followed by a separator ("S-19 — port …");
    # a bold TITLE that merely starts with an id-shaped word ("Strategy-prompt-length ablation.") keeps every word
    strip = bool(bid) and (inner == bid or re.match(re.escape(bid) + r"\s*[—:–.\-]", inner) is not None
                           or not bold)
    body = body.replace("**", " ")
    if strip:
        body = re.sub(r"^\s*(?:❄\s*)?" + re.escape(bid) + r"\b\s*", "", body)
    body = re.sub(r"^\s*(?:\[[a-z-]+\]\s*)?[—:–.\-]*\s*", "", body)
    return shorten(clean(body, 10_000)) or f"(proposal for {bid})"


_DATED_PAREN = re.compile(r"\s*\([^()]*\b20\d{2}-\d{2}-\d{2}\b[^()]*\)\s*$")


def shorten(text: str, limit: int = 200) -> str:
    """C1 cosmetics: drop trailing parentheticals that carry a date; past `limit`, cut at the last sentence or clause
    boundary (`. ; : , —`) before it and append `…`."""
    t = text.strip()
    while _DATED_PAREN.search(t):
        t = _DATED_PAREN.sub("", t).strip()
    if len(t) <= limit:
        return t
    head = t[:limit - 1]
    cut = max(head.rfind(x) for x in (". ", "; ", ": ", ", ", " — "))
    head = head[:cut + 1] if cut >= limit // 3 else head[:head.rfind(" ")] if " " in head else head
    return head.rstrip(" ,;:—") + "…"


def recently_edited(root: Path, rel: str, minutes: int) -> bool:
    """C1 review B2: True when origin/main changed this file less than `minutes` ago (its owner is likely mid-edit)."""
    import time
    try:
        r = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%ct", "origin/main", "--", rel],
                           capture_output=True, text=True, timeout=20)
        ts = int((r.stdout or "0").strip() or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return True                         # unknown -> treat as busy (never write into a file we cannot date)
    return ts > 0 and time.time() - ts < minutes * 60


def child_class(text: str, done_when=None) -> str:
    """Classify a child on ITS OWN text (task_lint's classifier), never inherited from the parent: a code task under an
    [inference] parent is non-inference. Anything but inference/non-inference falls back to non-inference."""
    import task_lint as TL
    c = TL.dispatch_result(f"- [ ] **X-1** {text}" + (f"\n      · done when: {clean(done_when)}" if done_when else ""),
                           0).get("class")
    return c if c in ("non-inference", "inference") else "non-inference"


def write_proposals(path: Path, rec: dict, reply: dict, who: str, dry_run: bool) -> list[str]:
    base = parent_headline(rec)
    items = []
    if reply.get("split"):
        for c in reply["split"][:4]:
            if isinstance(c, dict) and c.get("text"):
                items.append((c["text"], c.get("done_when"), None))
    else:
        items.append((base[:200] or rec["id"], reply.get("done_when"), reply.get("stop_rule")))
    diffs = []
    for text, dw, stop in items:
        if not clean(text):
            continue
        cls = child_class(clean(text), dw)
        a = argparse.Namespace(box=rec["id"], cls=cls, text=clean(text), done_when=(clean(dw) or None),
                               inputs=None, tier=None, owner=None, needs_owner=True, proposed_by=who,
                               stop_rule=(clean(stop) or None))
        diffs.append(HB.apply(path, "propose", a, REPO_ROOT, dry_run=dry_run))
    return diffs


def main(argv=None, runner=claude_runner, root: Path = REPO_ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--top-rows", type=int, default=10)
    ap.add_argument("--max-boxes", type=int, default=900)
    ap.add_argument("--budget-tokens", type=int, default=30_000_000)
    ap.add_argument("--per-box-tokens", type=int, default=30_000)
    ap.add_argument("--stop-share", type=float, default=0.20,
                    help="REPORT ONLY: the global pending share in the top rows (back-pressure is per file, see file_at_cap)")
    ap.add_argument("--expire", action="store_true", help="only auto-reject proposals pending > --expire-days, then exit")
    ap.add_argument("--expire-days", type=int, default=14)
    ap.add_argument("--review-queue", default=None, help="only write the pipeline-mgmt ownerless review queue to PATH")
    ap.add_argument("--flags", default="/mnt/raid0/llm/tmp/compute-flags")
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--files", nargs="*", default=None, help="restrict to these handoff basenames (batch 2-3 per run)")
    ap.add_argument("--recent-minutes", type=int, default=30,
                    help="skip a file whose last origin/main commit is younger than this (0 = off)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.expire:
        ids = expire(root, a.expire_days, dry_run=a.dry_run)
        print(json.dumps({"expired": ids}))
        return 0
    if a.review_queue:
        reg = {}
        try:
            reg = json.load(open(os.path.join(a.flags, "handoff-sessions.json")))
        except (OSError, ValueError):
            pass
        print(json.dumps({"review_queue": a.review_queue, "rows": review_queue(root, reg, a.review_queue)}))
        return 0
    doc = BI.load(root)
    if doc.get("stale") and not doc.get("boxes"):
        print(BI.stale_note(doc, "propose_rewrites"), file=sys.stderr)
        return 2
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    who = f"taskflow {ts}"
    ledger = open(a.ledger, "a", encoding="utf-8") if a.ledger else None
    total = done = written = 0
    stats = {"proposed": 0, "no-json": 0, "over-budget": 0, "error": 0, "skip": 0}
    busy: set[str] = set()
    idle: set[str] = set()
    capped: set[str] = set()
    if a.dry_run:
        print("DRY-RUN: child IDs shown are NOT final (nothing is written, so every child of a box renders as .p1)")
    for key, rec in candidates(doc, a.top_rows):
        if a.files and Path(rec["file"]).name not in a.files:
            continue
        if rec["file"] in busy or (a.recent_minutes and rec["file"] not in idle
                                   and recently_edited(root, rec["file"], a.recent_minutes)):
            if rec["file"] not in busy:
                print(f"SKIP-FILE {rec['file']}: changed on origin/main < {a.recent_minutes} min ago", file=sys.stderr)
            busy.add(rec["file"])
            stats["skip"] += 1
            continue
        idle.add(rec["file"])
        if done >= a.max_boxes or total >= a.budget_tokens:
            break
        cur = BI.load(root, regenerate=not a.dry_run) if written else doc
        at_cap, pend, cap = file_at_cap(cur, rec["file"])
        if at_cap:
            if rec["file"] not in capped:
                print(f"FILE-AT-CAP {rec['file']}: {pend} pending >= cap {cap}; next file", file=sys.stderr)
            capped.add(rec["file"])
            stats["skip"] += 1
            continue
        path = root / rec["file"]
        lines = path.read_text(encoding="utf-8").split("\n")
        i = next((n for n, l in enumerate(lines) if L1.CHECKBOX.match(l) and L1.head_id(l) == rec["id"]), None)
        if i is None:
            continue
        own, _ = L1.own_block(lines, i)
        fails = [f for f in (rec.get("lint") or {}).get("fails") or [] if f in TARGET_FAILS]
        prompt = PROMPT.format(fails=", ".join(fails), heads=heading_chain(lines, i),
                               context="\n".join(lines[max(0, i - 20):i])[-4000:], box=own[:4000])
        done += 1
        try:
            text, usage = runner(prompt)
        except Exception as exc:  # noqa: BLE001
            stats["error"] += 1
            print(f"ERROR {rec['id']}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        tok = uncached(usage)
        total += tok
        reply = parse_reply(text)
        outcome = "proposed"
        if tok > a.per_box_tokens:
            outcome = "over-budget"
        elif reply is None:
            outcome = "no-json"
        else:
            try:
                for d in write_proposals(path, rec, reply, who, a.dry_run):
                    print(d)
                written += 0 if a.dry_run else 1
            except HB.BoxError as exc:
                outcome = "skip"
                print(f"SKIP {rec['id']}: {exc}", file=sys.stderr)
        stats[outcome] += 1
        if ledger:
            ledger.write(json.dumps({"at": ts, "box": rec["id"], "file": rec["file"], "fails": fails, "tokens": tok,
                                     "usage": usage, "outcome": outcome, "reply": reply}, sort_keys=True) + "\n")
            ledger.flush()
    share = pending_share(BI.load(root, regenerate=False) if written else doc, a.top_rows)
    print(json.dumps({"boxes": done, "tokens_uncached": total, "global_pending_share": round(share, 3),
                      "global_share_report_threshold": a.stop_share, **stats}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

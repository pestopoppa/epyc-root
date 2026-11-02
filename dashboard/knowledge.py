"""Read-only claim browser over the vidya belief ledger (KT-3).

claim -> evidence -> run (the ``source_observed`` frame: kind, locator,
revision) -> commit (any recorded git identity on those frames).

READ-ONLY by construction: the ledger is opened for reading only, nothing is
graded here (grading is ``scripts/vidya/claim_tuple.grade()``'s job and the
grade shown is the one the adapter wrote), and no commit is invented — a claim
whose frames carry no git identity says ``not recorded``.

The ledger is the canonical one (``scripts/vidya/ledger_home.py``:
``$VIDYA_LEDGER`` or ``$VIDYA_STATE_DIR/ledger.jsonl``, default
``/mnt/raid0/llm/state/vidya/ledger.jsonl``), ~45 MB. It is parsed once per
(size, mtime) and cached; the index is rebuilt only when the file changes.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Optional

DEFAULT_STATE_DIR = "/mnt/raid0/llm/state/vidya"
_FT = re.compile(r"^epyc\.vidya/frame/([a-z_]+)/v\d+$")
_HEX = re.compile(r"^[0-9a-f]{7,40}$")
_HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
_COMMIT_KEY = re.compile(r"(commit|build_sha|source_sha|git_sha|^sha$|revision$)", re.I)
TEXT_CAP = 160

_lock = threading.Lock()
_cache: dict[str, Any] = {"key": None, "index": None}


def ledger_path() -> Path:
    explicit = os.environ.get("VIDYA_LEDGER")
    if explicit:
        return Path(explicit)
    return Path(os.environ.get("VIDYA_STATE_DIR") or DEFAULT_STATE_DIR) / "ledger.jsonl"


def _commits(obj: Any, prefix: str = "", out: Optional[list] = None) -> list:
    """Every recorded git identity in ``obj``: ``[{field, value}]``. Never inferred."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str) and _COMMIT_KEY.search(k) and _HEX.match(v):
                out.append({"field": path, "value": v})
            elif isinstance(v, str) and k == "locator":
                for h in _HEX40.findall(v):
                    out.append({"field": path, "value": h})
            else:
                _commits(v, path, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _commits(v, f"{prefix}[{i}]", out)
    return out


def build_index(path: Path) -> dict:
    claims: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    frame_owner: dict[str, str] = {}
    retracted_frames: dict[str, dict] = {}
    counts: dict[str, int] = {}
    bad = 0
    last_created = None
    last_seq = None
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
                frame = rec["frame"]
                m = _FT.match(frame["frame_type"])
                kind = m.group(1) if m else frame["frame_type"]
                a = frame.get("assertion") or {}
            except (ValueError, KeyError, TypeError):
                bad += 1
                continue
            counts[kind] = counts.get(kind, 0) + 1
            created = (frame.get("pubinfo") or {}).get("created_at")
            if created and (last_created is None or created > last_created):
                last_created = created
            last_seq = rec.get("seq", last_seq)
            meta = {"seq": rec.get("seq"), "frame_id": frame.get("frame_id"), "created_at": created,
                    "actor": (frame.get("pubinfo") or {}).get("actor"),
                    "authority_scope": (frame.get("pubinfo") or {}).get("authority_scope"),
                    "method": (frame.get("provenance") or {}).get("method")}
            if kind == "source_observed":
                sources[a.get("source_id")] = {**meta, "assertion": a}
            elif kind == "claim_proposed":
                cid = a.get("claim_id")
                c = claims.setdefault(cid, {"evidence": [], "depends_on": [], "corrections": [],
                                            "retractions": [], "aliases": []})
                c.update({"claim_id": cid, "text": a.get("display_text") or a.get("decided_proposition"),
                          "source_id": a.get("source_id"), "proposed": meta, "assertion": a,
                          "provenance": frame.get("provenance")})
                frame_owner[frame.get("frame_id")] = cid
            elif kind in ("evidence_supports_claim", "evidence_opposes_claim"):
                cid = a.get("claim_id")
                c = claims.setdefault(cid, {"evidence": [], "depends_on": [], "corrections": [],
                                            "retractions": [], "aliases": []})
                c["evidence"].append({**meta, "direction": "supports" if "supports" in kind else "opposes",
                                      "assertion": a, "provenance": frame.get("provenance")})
                frame_owner[frame.get("frame_id")] = cid
            elif kind == "claim_depends_on":
                claims.setdefault(a.get("claim_id"), {"evidence": [], "depends_on": [], "corrections": [],
                                                      "retractions": [], "aliases": []})["depends_on"].append(a)
            elif kind == "correction_recorded":
                for cid in a.get("claim_ids") or []:
                    claims.setdefault(cid, {"evidence": [], "depends_on": [], "corrections": [],
                                            "retractions": [], "aliases": []})["corrections"].append(
                        {"seq": rec.get("seq"), "created_at": created, "entry_id": a.get("entry_id"),
                         "classification": a.get("classification"),
                         "text": (a.get("correction_text") or "")[:600]})
            elif kind == "retraction":
                retracted_frames[a.get("retracts")] = {"seq": rec.get("seq"), "created_at": created,
                                                       "reason": a.get("reason")}
            elif kind == "claim_alias":
                ids = a.get("claim_ids") or []
                for cid in ids:
                    claims.setdefault(cid, {"evidence": [], "depends_on": [], "corrections": [],
                                            "retractions": [], "aliases": []})["aliases"].append(
                        {"claim_ids": ids, "independent": a.get("independent")})
    for fid, r in retracted_frames.items():
        cid = frame_owner.get(fid)
        if cid and cid in claims:
            claims[cid]["retractions"].append({**r, "frame_id": fid})
    rows = []
    for cid, c in claims.items():
        if "claim_id" not in c:
            continue  # evidence/depends for a claim never proposed in this ledger: not listed
        src = sources.get(c.get("source_id")) or {}
        sup = sum(1 for e in c["evidence"] if e["direction"] == "supports")
        rows.append({"id": cid, "t": (c.get("text") or "")[:TEXT_CAP],
                     "k": (src.get("assertion") or {}).get("source_kind"),
                     "s": sup, "o": len(c["evidence"]) - sup, "r": len(c["retractions"]),
                     "c": len(c["corrections"]), "ts": (c.get("proposed") or {}).get("created_at"),
                     "q": next(((e["assertion"].get("grade") or {}).get("Q") for e in c["evidence"]
                                if isinstance(e["assertion"].get("grade"), dict)), None)})
    rows.sort(key=lambda r: (r["ts"] or "", r["id"]), reverse=True)
    return {"claims": claims, "sources": sources, "rows": rows, "counts": counts,
            "malformed_lines": bad, "last_created_at": last_created, "last_seq": last_seq}


def index() -> tuple[Optional[dict], Optional[str], Path]:
    """``(index, error, path)``; error is set when the ledger is absent/unreadable."""
    path = ledger_path()
    try:
        st = path.stat()
    except FileNotFoundError:
        return None, None, path
    except OSError as exc:
        return None, f"ledger unreadable: {exc}", path
    key = (str(path), st.st_size, st.st_mtime_ns)
    with _lock:
        if _cache["key"] == key:
            return _cache["index"], None, path
        try:
            idx = build_index(path)
        except OSError as exc:
            return None, f"ledger unreadable: {exc}", path
        _cache.update(key=key, index=idx)
        return idx, None, path


def claim_detail(idx: dict, claim_id: str) -> Optional[dict]:
    c = idx["claims"].get(claim_id)
    if not c or "claim_id" not in c:
        return None
    src = idx["sources"].get(c.get("source_id"))
    evidence = []
    for e in c["evidence"]:
        esrc = idx["sources"].get(e["assertion"].get("source_id"))
        evidence.append({**e, "run": esrc,
                         "commits": _commits(e["assertion"]) + _commits(e.get("provenance") or {})
                         + (_commits(esrc["assertion"]) if esrc else [])})
    commits = _commits(c.get("assertion")) + (_commits(src["assertion"]) if src else [])
    for e in evidence:
        commits += e["commits"]
    seen, uniq = set(), []
    for cm in commits:
        k = (cm["field"], cm["value"])
        if k not in seen:
            seen.add(k)
            uniq.append(cm)
    return {"claim_id": claim_id, "text": c.get("text"), "proposed": c.get("proposed"),
            "assertion": c.get("assertion"), "provenance": c.get("provenance"),
            "run": src, "evidence": evidence, "commits": uniq,
            "depends_on": c["depends_on"], "corrections": c["corrections"][-20:],
            "retractions": c["retractions"], "aliases": c["aliases"]}

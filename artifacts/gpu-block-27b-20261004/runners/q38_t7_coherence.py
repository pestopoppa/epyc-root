"""Q38-T7 successor adapter: the paired `coherence_gate.evaluate` gate for phases A and the needle pairs.

TD-30d item 1 (epyc-inference-research docs/coherence-gate.md section 2). It REPLACES, for a
successor run, `q38_t7.pair_a` / `grade` / `classify_text` with the shared library; it does NOT edit
`q38_t7.py` or `degeneracy.py`, because those files are digest-pinned (sealed runner source:
`q38_t7_rowflow.SOURCE_FILES` and the `scripts/ci/*readset.json` pins). Cutting `q38_t7_payloads.py`
over to `pair_a_gate` / `needle_gate` / `gate_verdict` is a re-seal step for the run owner, and the
`OC1-coherence-gate-v1` era row (TD-30e, operator-signed) must exist before a gate verdict from this
adapter is quoted as an instrument verdict. Nothing here starts a server or reads a model.

Row shape (the patched runner's phase A): {"id", "arm": "dflash2" | "nodraft", "text", "token_ids",
"http", "finish"?}. Drafted = candidate, no-draft = base (the anchor). HTTP-failed pairs are listed
and excluded, as before: a measurement without both arms is invalid, never a pass. Phase C streams
have no no-draft pair and stay on the documented single-arm `degeneracy.fails`.

Default off: `enabled()` reads Q38_T7_COHERENCE_GATE.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

LIB_ENV = "COHERENCE_GATE_LIB"
DEFAULT_LIB = "/mnt/raid0/llm/epyc-inference-research/scripts/lib"
ANCHOR = {"arm": "speculative.n_max=0", "binary_version": "10303"}
FLAG = "Q38_T7_COHERENCE_GATE"


def enabled(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return str(env.get(FLAG, "")).strip().lower() in {"1", "true", "yes", "on"}


def load_gate():
    lib = os.environ.get(LIB_ENV, DEFAULT_LIB)
    if lib not in sys.path:
        sys.path.insert(0, lib)
    import coherence_gate  # noqa: PLC0415

    return coherence_gate


def _gate_row(r: Mapping[str, Any]) -> dict:
    row = {"id": r["id"], "text": r.get("text") or "", "http": r.get("http")}
    if r.get("token_ids"):
        row["token_ids"] = list(r["token_ids"])
    if r.get("finish") is not None:
        row["finish"] = r["finish"]
    return row


def _truth(truth_by_id: Mapping[str, dict], ids: Sequence[str]) -> list[dict]:
    out = []
    for i in ids:
        t = truth_by_id.get(i)
        if t:
            out.append({**t, "id": i})
    return out


def _paired_shape(report: dict, http: list[str]) -> dict:
    items = report["items"]
    graded: dict[str, list[str]] = {"dflash2": [], "nodraft": []}
    for it in items:
        ac = it.get("answer_check")
        if ac:
            if ac.get("cand"):
                graded["dflash2"].append(ac["cand"]["status"])
            if ac.get("base"):
                graded["nodraft"].append(ac["base"]["status"])
    return {
        "regressions": [{"id": i["id"], "why": list(i["reasons"])} for i in items if i["verdict"] == "REGRESSION"],
        "shared_nonok": [f"{i['id']}: {'; '.join(i['reasons'])}" for i in items if i["verdict"] == "BOTH_BAD"],
        "http_error": http,
        "needs_review": [i["id"] for i in items if i["verdict"] == "NEEDS_REVIEW"],
        "non_identical": [i["id"] for i in items if not (i.get("identity") or {}).get("identical")],
        "graded": {arm: f"{sum(s == 'correct' for s in v)}/{len(v)} correct" for arm, v in graded.items()},
        "gate": report["aggregate"]["gate"],
        "gate_reasons": report["aggregate"]["gate_reasons"],
        "report": report,
    }


def pair_a_gate(
    rows: Sequence[Mapping[str, Any]],
    truth_by_id: Mapping[str, dict],
    *,
    anchor: Mapping[str, str] | None = None,
    tokenizer=None,
    judge_fn=None,
) -> dict:
    """Phase A: drafted vs no-draft per prompt through `coherence_gate.evaluate`."""
    CG = load_gate()
    by = {(r["id"], r["arm"]): r for r in rows}
    ids = sorted({r["id"] for r in rows})
    http = [i for i in ids if any(
        (by.get((i, a)) or {}).get("http") not in (None, 200) for a in ("dflash2", "nodraft"))]
    ids = [i for i in ids if i not in http and (i, "dflash2") in by and (i, "nodraft") in by]
    report = CG.evaluate(
        [_gate_row(by[(i, "nodraft")]) for i in ids],
        [_gate_row(by[(i, "dflash2")]) for i in ids],
        _truth(truth_by_id, ids),
        judge_fn=judge_fn, tokenizer=tokenizer, anchor=dict(anchor or ANCHOR),
    )
    return _paired_shape(report, http)


def needle_gate(needle_rows: Sequence[Mapping[str, Any]], *, anchor: Mapping[str, str] | None = None) -> dict:
    """Phase B needle pairs: rows {"target", "variant": "needle" | "needle (no-draft)", "answer",
    "expected": [code, name], "http"}. Answers carry no token ids, so the degeneracy leg uses a
    DECLARED text-only surrogate (recorded in the report's `text_only_declared`)."""
    CG = load_gate()
    base, cand, truth, http = [], [], [], []
    for r in needle_rows:
        rid = f"needle@{r['target']}"
        row = {"id": rid, "text": r.get("answer") or "", "http": r.get("http")}
        if r["variant"] == "needle":
            cand.append(row)
            truth.append({"id": rid, "grader": "needle", "expected": list(r["expected"])})
        elif r["variant"] == "needle (no-draft)":
            base.append(row)
    for b in list(base):
        if b["http"] not in (None, 200):
            http.append(b["id"])
    http += [c["id"] for c in cand if c["http"] not in (None, 200)]
    base = [b for b in base if b["id"] not in http]
    cand = [c for c in cand if c["id"] not in http]
    report = CG.evaluate(base, cand, truth, allow_text_only=True, anchor=dict(anchor or ANCHOR))
    return _paired_shape(report, sorted(set(http)))


def gate_verdict(rep: Mapping[str, Any]) -> dict:
    """Aggregate: FAIL on any regression/HTTP error/single-arm fail (B drafted, C); INCOMPLETE (never
    PASS) when any item is NEEDS_REVIEW. `rep` = {"A": {"paired": pair_a_gate(...)}, "B": {"rows": [...],
    "needle": needle_gate(...)}, "C": {"rows": [...]}} with rows carrying a v2.1 `degeneracy` dict."""
    CG = load_gate()
    reasons: list[str] = []
    incomplete: list[str] = []
    notes: list[str] = []
    for name, blk in (("A", (rep.get("A") or {}).get("paired")), ("B needle", (rep.get("B") or {}).get("needle"))):
        if not blk:
            continue
        for g in blk["regressions"]:
            reasons.append(f"phase {name} drafting regression {g['id']}: {'; '.join(g['why'])}")
        if blk["http_error"]:
            reasons.append(f"phase {name} HTTP error (measurement invalid): {blk['http_error']}")
        if blk["needs_review"]:
            incomplete.append(f"phase {name} unjudged divergences: {blk['needs_review']}")
        notes += [f"phase {name} shared (not a drafting failure): {s}" for s in blk["shared_nonok"]]
    for r in (rep.get("B") or {}).get("rows", []):
        if r.get("variant") == "drafted" and CG.degeneracy.fails(r["degeneracy"]):
            reasons.append(f"phase B ~{r['target']} rep{r['rep']} {r['degeneracy']['cls']}")
    for r in (rep.get("C") or {}).get("rows", []):
        if CG.degeneracy.fails(r["degeneracy"]):
            reasons.append(f"phase C stream {r['stream']} {r['degeneracy']['cls']}")
    status = "FAIL" if reasons else ("INCOMPLETE" if incomplete else "PASS")
    return {"schema": CG.SCHEMA_ID, "correctness": status, "reasons": reasons, "incomplete": incomplete,
            "model_behaviour": notes, "speed_valid": status == "PASS", "classifier": CG.V21_ID,
            "anchor": dict(ANCHOR)}

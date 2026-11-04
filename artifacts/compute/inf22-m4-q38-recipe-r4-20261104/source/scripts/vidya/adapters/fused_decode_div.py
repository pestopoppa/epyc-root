"""FD-DIV fused-decode divergence receipts -> verifier ClaimTuples (VB-FUSED-DECODE-DIV-WIRE).

Two job-written native records, both read as written and re-derived, never repaired:

* **FD-DIV-1a** ``epyc.fd_div_1a.smoke_receipt.v1`` (``fd_div_1a_receipt.json``): per smoke, byte-identity
  of greedy output between a test arm and a reference arm. One claim per DECIDED smoke (S1 GSQ IQ3_XXS
  fused-ON-with-refusal vs ``GGML_FUSED_DECODE_OFF=1`` on the v10 store; S2 UD-IQ4_XS patched vs the v10
  store fused-ON). A smoke the receipt did not decide (``result`` null, e.g. S3 SKIPPED) projects nothing:
  absence is recorded, never filled. The v10 fused-ON abort (rc 134 signature) is the DEFECT CONTROL of S1
  and rides in that claim's ``extra``. Decode ms/token is descriptive OBSERVATION only (``extra``), never a
  value and never a speed claim.
* **FD-DIV-1b** ``epyc.fd_div_1b.result.v1`` (``RESULT.json``): the ported ASAN repro at router-weight
  scales; one claim per cell (the ``ctl`` control and each ``w``), class CLEAN / DIVERGE / ABORT.
  ``FD-DIV-1a``'s own ``RESULT.json`` (schema ``epyc.fd_div_1a.result.v1``) is its analyzer echo, not a
  receipt, and declines.

Re-derivation: the stated smoke ``result`` must equal what the cell rows give (rc, stdout sha256 equality
test vs ref, refusal counts); each 1b cell class must equal what its config lines and rc give. The pass
rule ``PREDECLARED.json`` is re-hashed when it can be read and must equal the sha256 the record states.

PROJECTION ONLY. Verifier class: ``decided_proposition`` names the identity/defect decided (never a bare
PASS), ``claim`` is that same text (binding ``identity``), the pass rule sha256 and the subject/base commits
are the attestation. No protocol is cited (the receipt says so), so ``claim_tuple.grade()`` places every
tuple at ``Judged/...``. No ladder.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.fused_decode_div/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "fused-decode-div"
SCHEMA_1A = "epyc.fd_div_1a.smoke_receipt.v1"
SCHEMA_1B = "epyc.fd_div_1b.result.v1"
MAX_BYTES = 16 << 20
PROMPTS = ("paris", "short40", "short90", "long1")
GSQ_REFUSAL = "blk.0.ffn_down_shexp.weight"
_SHA = frozenset("0123456789abcdef")


def _read(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ProjectionError(f"fused-decode-div input unreadable: {path}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ProjectionError(f"fused-decode-div input exceeds bound: {path}")
    return raw


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA


def _rule(rule_path: Any, stated: Any, where: str) -> dict:
    """The pass rule: its stated sha256 is required; when the file is readable it must re-hash to it."""
    if not _is_sha(stated):
        raise ProjectionError(f"fused-decode-div {where}: pass-rule sha256 missing or malformed")
    verified = False
    if isinstance(rule_path, str) and Path(rule_path).is_file():
        if hashlib.sha256(_read(Path(rule_path))).hexdigest() != stated:
            raise ProjectionError(f"fused-decode-div {where}: PREDECLARED file does not re-hash to the stated sha256")
        verified = True
    return {"path": rule_path, "sha256": stated, "rehashed": verified}


def _cell(cells: dict, key: str) -> dict:
    c = cells.get(key)
    if not isinstance(c, dict) or c.get("present") is not True or type(c.get("rc")) is not int:
        raise ProjectionError(f"fused-decode-div: cell {key} absent or malformed")
    return c


def _ms(c: dict) -> Any:
    return c.get("eval_ms_per_token")


# ------------------------------------------------------------------ FD-DIV-1a

def _rows_1a(doc: dict, path: Path, sha: str) -> list[dict]:
    rule = _rule((doc.get("predeclared") or {}).get("path"), (doc.get("predeclared") or {}).get("sha256"), path.name)
    cells, subj = doc.get("cells"), doc.get("subject") or {}
    if not isinstance(cells, dict) or not subj.get("commit") or not subj.get("base"):
        raise ProjectionError(f"fused-decode-div {path.name}: cells or subject commit/base missing")
    props = {p.get("id"): p for p in doc.get("propositions") or [] if isinstance(p, dict)}
    out = []
    for sid in ("S1", "S2", "S3"):
        p = props.get(sid)
        if p is None:
            continue
        text, result = p.get("decided_proposition"), p.get("result")
        if result is None:
            continue                                   # not decided (SKIPPED): nothing to project
        if type(result) is not bool or not isinstance(text, str) or not text.strip():
            raise ProjectionError(f"fused-decode-div {path.name}: {sid} result/proposition malformed")
        if sid == "S3":
            raise ProjectionError(f"fused-decode-div {path.name}: S3 carries a result but no re-derivation exists")
        if sid == "S1":
            derived, rows, extra = _s1(cells)
        else:
            derived, rows, extra = _s2(cells)
        if derived != result:
            raise ProjectionError(f"fused-decode-div {path.name}: {sid} stated result {result} but the cells give {derived}")
        out.append({"shape": "1a", "smoke": sid, "result": result, "proposition": text, "rows": rows,
                    "extra": extra, "rule": rule, "subject": subj, "path": str(path), "sha256": sha,
                    "time": doc.get("time"), "protocol_note": doc.get("protocol_note")})
    return out


def _identity(cells: dict, test: str, ref: str) -> tuple[bool, dict]:
    t, r = _cell(cells, test), _cell(cells, ref)
    same = t["rc"] == 0 and r["rc"] == 0 and _is_sha(t.get("stdout_sha256")) and t["stdout_sha256"] == r["stdout_sha256"]
    return same, {"test": test, "ref": ref, "test_sha256": t.get("stdout_sha256"), "ref_sha256": r.get("stdout_sha256"),
                  "test_rc": t["rc"], "ref_rc": r["rc"], "identical": same,
                  "decode_ms_per_token_descriptive": {"test": _ms(t), "ref": _ms(r)}}


def _s1(cells: dict) -> tuple[bool, list, dict]:
    ok, rows = True, []
    for pr in PROMPTS:
        same, row = _identity(cells, f"g_test.{pr}", f"g_ref.{pr}")
        refusals = _cell(cells, f"g_test.{pr}").get("warn_tensors")
        row["refusals"] = refusals
        ok &= same and refusals == [GSQ_REFUSAL]
        rows.append(row)
    ctl = _cell(cells, "g_v10on.paris")
    control = {"cell": "g_v10on.paris", "rc": ctl["rc"], "abort_signature": ctl.get("abort_signature"),
               "v10_fused_prints": ctl.get("v10_fused_prints"),
               "defect_reproduced": bool(ctl["rc"] == 134 and ctl.get("abort_signature") is True)}
    return ok, rows, {"defect_control_v10_fused_on": control}


def _s2(cells: dict) -> tuple[bool, list, dict]:
    ok, rows = True, []
    for pr in PROMPTS:
        same, row = _identity(cells, f"u_test.{pr}", f"u_ref.{pr}")
        ref, test = _cell(cells, f"u_ref.{pr}"), _cell(cells, f"u_test.{pr}")
        took_fused = type(ref.get("v10_fused_prints")) is int and ref["v10_fused_prints"] > 0
        row.update({"test_refusals": test.get("warn_tensors"), "reference_took_fused_path": took_fused})
        ok &= same and test.get("warn_tensors") == [] and took_fused
        rows.append(row)
    return ok, rows, {}


# ------------------------------------------------------------------ FD-DIV-1b

def _class_1b(cell: dict) -> str:
    cfgs = cell.get("configs") or []
    if cell.get("rc") == 134 and cell.get("abort_line"):
        return "ABORT"
    if cfgs and all(c.get("line_verdict") == "OK" for c in cfgs) and cell.get("rc") == 0:
        return "CLEAN"
    if cfgs and any(c.get("line_verdict") == "FAIL" for c in cfgs):
        return "DIVERGE"
    raise ProjectionError(f"fused-decode-div: cell {cell.get('id')} is not interpretable")


def _rows_1b(doc: dict, path: Path, sha: str) -> list[dict]:
    rule_path = path.parent.parent / "job" / "PREDECLARED.json"
    rule = _rule(str(rule_path), doc.get("pred_sha256"), path.name)
    valid = doc.get("valid") or {}
    if valid.get("control_clean") is not True or valid.get("all_cells_present_and_interpretable") is not True:
        return []                                      # void run: the control did not hold
    cells = doc.get("cells")
    if not isinstance(cells, dict) or "ctl" not in cells:
        raise ProjectionError(f"fused-decode-div {path.name}: no control cell")
    meta: dict = {}
    mp = path.parent / "JOB_META.json"
    if mp.is_file():
        meta = json.loads(_read(mp))
    out = []
    for key, cell in cells.items():
        if not isinstance(cell, dict) or cell.get("id") != key:
            raise ProjectionError(f"fused-decode-div {path.name}: cell {key} malformed")
        klass = _class_1b(cell)
        if cell.get("class") != klass:
            raise ProjectionError(f"fused-decode-div {path.name}: cell {key} stated class {cell.get('class')} but rows give {klass}")
        out.append({"shape": "1b", "cell": key, "class": klass, "data": cell, "rule": rule, "path": str(path),
                    "sha256": sha, "time": doc.get("time"), "verdict": doc.get("verdict"), "why": doc.get("why"),
                    "job_meta": meta})
    return out


# ------------------------------------------------------------------ entry points

def native_rows(path: str | Path) -> tuple[dict, ...]:
    p = Path(path)
    if not p.is_file():
        return ()
    raw = _read(p)
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise ProjectionError(f"fused-decode-div {p.name}: not JSON") from exc
    schema = doc.get("schema") if isinstance(doc, dict) else None
    sha = hashlib.sha256(raw).hexdigest()
    if schema == SCHEMA_1A:
        return tuple(_rows_1a(doc, p, sha))
    if schema == SCHEMA_1B:
        return tuple(_rows_1b(doc, p, sha))
    return ()


def units(path: Path) -> list[Path]:
    path = Path(path)
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    found = set()
    for base in (path, path / "out"):
        for name in ("fd_div_1a_receipt.json", "RESULT.json"):
            if (base / name).is_file():
                found.add(base / name)
    return sorted(found)


def _claim_1b(n: dict) -> tuple[str, dict]:
    c, k = n["data"], n["cell"]
    lines = "; ".join(
        f"{x['cfg']}: fused {x['fused']}/{x['expected']}, K {x['K_nmse']:.3g}, idx {x['idx_nmse']:.3g}, "
        f"logits {x['logits_nmse']:.3g} NMSE ({x['line_verdict']})" for x in c.get("configs") or [])
    scale = "the unscaled control" if k == "ctl" else f"router-weight scale {k[1:]}"
    text = (f"On the FD-DIV-1b ASAN fixture (F32/F16 tensors only, source {n['job_meta'].get('head', 'unknown')}), "
            f"the fused decode path versus the graph path at {scale} is {n['class']} (rc {c['rc']})"
            + (f": {lines}" if lines else f": aborts with '{c.get('abort_line')}'")
            + f"; pass rule PREDECLARED sha256 {n['rule']['sha256'][:12]}.")
    return text, {"cell": k, "class": n["class"], "rc": c["rc"], "configs": c.get("configs"),
                  "abort_line": c.get("abort_line"), "run_verdict": n["verdict"], "run_why": n["why"],
                  "job_meta": n["job_meta"]}


@register(SOURCE_KIND, source_class="verifier", decided_proposition_field="proposition")
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or native.get("shape") not in ("1a", "1b"):
        raise ProjectionError("fused-decode-div native row missing")
    rule = native["rule"]
    if native["shape"] == "1a":
        text, ident = native["proposition"], f"fd-div-1a:{native['smoke']}:{native['sha256'][:16]}"
        subj = native["subject"]
        extra = {"smoke": native["smoke"], "identity_rows": native["rows"], "subject_commit": subj["commit"],
                 "base_commit": subj["base"], "protocol_note": native["protocol_note"], **native["extra"]}
        value, unit = int(native["result"]), "boolean"
        locator = f"fd-div-1a:{native['path']}#{native['smoke']}"
    else:
        text, extra = _claim_1b(native)
        ident = f"fd-div-1b:{native['cell']}:{native['sha256'][:16]}"
        value, unit = int(native["class"] == "CLEAN"), "boolean"
        locator = f"fd-div-1b:{native['path']}#{native['cell']}"
        extra["subject_commit"] = native["job_meta"].get("head")
    extra.update({"adapter": ADAPTER_ID, "pass_rule": rule})
    return ClaimTuple(
        measurement_id=ident, metric="fused_decode_identity_holds" if native["shape"] == "1a" else "fused_decode_matches_graph",
        value=value, date=str(native["time"])[:10], category="CANDIDATE", metric_direction="higher_better",
        claim=text, decided_proposition=text, source_class="verifier", binding_kind="identity",
        protocol_id="", unit=unit, attestation_path=native["path"], attestation_sha256=native["sha256"],
        attestation_locator=locator, attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND, extra=extra)


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project", "units", "frames_for_path"]

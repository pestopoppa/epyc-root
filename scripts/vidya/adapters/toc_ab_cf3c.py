"""VB-CF3C-POLICY-WIRE : ``epyc.cf3c.native.v1`` from the ``cf3c-live`` producer.

Member of the ``toc_ab`` source family (same ``claim_tuple`` carrier, same shared sealed-file
plumbing, same refusal discipline). The unit is ONE ``RESULT.json`` or ``PARTIAL.json`` plus the sealed ``window-*``
directory it names. ``claim_tuple.grade()`` decides every grade; this module holds no ladder.

The reader REFUSES THE WHOLE UNIT (raises :class:`ProjectionError`, which the ingest report lists
under ``refused`` and which writes nothing) on any of:

* a sealed file missing, or whose sha256 differs from ``window_sha256``; a file in the window that
  the manifest does not seal;
* a per-cell ``TRAJECTORY.json`` that disagrees with the sealed ``WINDOW.json`` schedule, with the
  ``paired`` record in RESULT, or whose ``evidence_sha256`` map names a file the window does not
  seal under the same digest;
* a per-arm summary (``correct`` / ``graded`` / ``abstained`` / accuracy / mean tokens / mean
  wall) that does not re-derive from the per-cell trajectories (the summary is never trusted);
* smoke, server-still-running or inconsistent count records. Sealed partial/failed windows
  retain native UNKNOWN/NA cells and explicit unattempted placeholders without replacing them.

Activation receipts and exact-request digests travel with each arm, as do treatment-minus-A0
per-case deltas. Missing costs/verdicts give null deltas, never zero. Cost means use only observed
cells and carry their separate denominators; no cost tuple is emitted without a native observation.
Protected-zone semantics are bound by producer policy custody, with no separate receipt invented.

Projection: per arm, three tuples (accuracy, mean total tokens, mean wall seconds). Accuracy is
``correct / scheduled`` -- an abstention or UNKNOWN cell is NOT silently dropped from the
denominator, and the abstention count rides in the claim text. ``reps`` is the number of cells for
that arm (3 in the first real window, one per case), so the grade shows the small n. There is NO
protocol id: the record is ``diagnostic_only`` and no codified protocol covers it, so every tuple is
an OBSERVATION (``Judged``), exactly as ``claim_tuple.grade()`` computes. A diagnostic matrix does
not establish the parent 1-percentage-point accuracy adoption rule, and nothing here claims it.

Scope (``applicability``) is only what the sealed window names: ``model_file`` and
``model_sha256`` (``WINDOW.json`` inputs), ``quant`` (``SERVER.json`` ``ftype``), ``backend``
(``--n-gpu-layers 0`` in the sealed server argv => ``cpu``). A server argv that offloads layers
declares no backend. ``context_tokens`` is deliberately NOT scoped: the cell's 12288 is the case
budget, not the served context regime. No ``stack_regime`` is claimed (the record names no lineup
digest).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path, PurePath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters import toc_ab  # noqa: E402

SCHEMA = "epyc.cf3c.native.v1"
ADAPTER_ID = "vidya.adapters.toc_ab_cf3c/v1"
AUTHORITY = toc_ab.AUTHORITY
SOURCE_KIND = "toc-ab-cf3c-measurement"
PRODUCER = "cf3c-live"
M_ACC = "cf3c_arm_accuracy_over_scheduled"
M_TOK = "cf3c_arm_mean_total_tokens"
M_WALL = "cf3c_arm_mean_wall_s"
METRICS = (M_ACC, M_TOK, M_WALL)
_TOL = 1e-9


def _refuse(msg: str):
    raise ProjectionError(f"cf3c native unit refused: {msg}")


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        _refuse(f"{path.name} unreadable ({exc})")


def _sha(path: Path) -> str:
    try:
        return ns.file_sha256(path)
    except OSError as exc:
        _refuse(f"sealed file {path} unreadable ({exc})")


def _window(result_path: Path, result: dict) -> Path:
    name = PurePath(str(result.get("window") or "")).name
    if not name or name in (".", ".."):
        _refuse("RESULT.json names no window directory")
    window = result_path.parent / name
    if not window.is_dir():
        _refuse(f"window directory {name!r} is not beside RESULT.json")
    return window


def _verify_seal(window: Path, sealed: Any) -> None:
    if not isinstance(sealed, dict) or not sealed:
        _refuse("window_sha256 must be a non-empty map")
    for rel, digest in sealed.items():
        parts = PurePath(rel).parts
        if (not isinstance(rel, str) or not parts or PurePath(rel).is_absolute() or ".." in parts
                or not ns.SHA256.fullmatch(str(digest))):
            _refuse(f"malformed sealed entry {rel!r}")
        target = window / rel
        if not target.is_file():
            _refuse(f"sealed file missing: {rel}")
        if _sha(target) != digest:
            _refuse(f"sealed file hash mismatch: {rel}")
    on_disk = {p.relative_to(window).as_posix() for p in window.rglob("*") if p.is_file()}
    extra = sorted(on_disk - set(sealed))
    if extra:
        _refuse(f"window holds files the manifest does not seal: {extra[:3]}")


def _close(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is b
    return ns.finite(a) and ns.finite(b) and math.isclose(a, b, rel_tol=_TOL, abs_tol=_TOL)


def _derive(cells: list[dict]) -> dict:
    """Per-arm summary from per-cell trajectories ONLY."""
    out: dict[str, dict] = {}
    for c in cells:
        a = out.setdefault(c["arm"], {"scheduled": 0, "correct": 0, "graded": 0, "abstained": 0,
                                      "UNKNOWN": 0, "NA": 0, "unattempted": 0, "non_termination": 0, "attempted": 0,
                                      "tokens": [], "walls": []})
        a["scheduled"] += 1
        status = c["status"]
        if status == "graded":
            a["graded"] += 1
            a["correct"] += 1 if c["correct"] is True else 0
        elif status == "abstained":
            a["abstained"] += 1
        else:
            a[status] += 1
        a["attempted"] += int(status != "unattempted")
        a["non_termination"] += int(c.get("non_termination") or 0)
        u = c.get("usage")
        if isinstance(u, dict) and ns.nonneg_int(u.get("total_tokens")):
            a["tokens"].append(u["total_tokens"])
        if status != "unattempted" and ns.finite(c.get("wall_s")):
            a["walls"].append(c["wall_s"])
    for a in out.values():
        a["accuracy_among_graded"] = a["correct"] / a["graded"] if a["graded"] else None
        a["accuracy_over_attempted"] = a["correct"] / a["attempted"] if a["attempted"] else None
        a["accuracy_over_scheduled"] = a["correct"] / a["scheduled"]
        a["tokens_cases"] = len(a["tokens"])
        a["mean_total_tokens"] = sum(a["tokens"]) / len(a["tokens"]) if a["tokens"] else None
        a["wall_cases"] = len(a["walls"])
        a["mean_wall_s"] = sum(a["walls"]) / len(a["walls"]) if a["walls"] else None
    return out


def _scope(window: Path, inputs: dict, argv: Any) -> dict:
    scope: dict[str, Any] = {}
    model = str(inputs.get("model_path") or "")
    sha = str(inputs.get("model_sha256") or "")
    if model:
        scope["model_file"] = PurePath(model).name
    if ns.SHA256.fullmatch(sha):
        scope["model_sha256"] = sha
    try:
        ftype = _load(window / "SERVER.json")["model"]["meta"]["ftype"]
    except (KeyError, TypeError, ProjectionError):
        ftype = None
    if isinstance(ftype, str) and ftype.strip():
        scope["quant"] = ftype.strip()
    if isinstance(argv, list) and "--n-gpu-layers" in argv:
        i = argv.index("--n-gpu-layers")
        if i + 1 < len(argv) and str(argv[i + 1]) == "0":
            scope["backend"] = "cpu"
    return scope


def _activation(folder: Path, cell: dict) -> dict:
    """Carry native receipts; check recorded changed-index witnesses against exact requests.

    Missing evidence on a failed cell is explicit, never reconstructed as a successful policy.
    Protected-zone semantics remain the producer's source-pinned policy, not a new reader rule.
    """
    names = ("policy.json", "original-messages.json", "template.request.body")
    missing = [name for name in names if name not in cell["evidence_sha256"]]
    if missing:
        if cell["status"] != "UNKNOWN":
            _refuse(f"{cell['unit']}: missing activation evidence {missing}")
        return {"unavailable": missing, "status": cell["status"],
                "evidence_sha256": dict(cell["evidence_sha256"])}
    policy, original, request = (_load(folder / name) for name in names)
    selected = request.get("messages") if isinstance(request, dict) else None
    if (not isinstance(policy, dict) or policy.get("arm") != cell["arm"]
            or not isinstance(original, list) or not isinstance(selected, list)
            or len(original) != len(selected)
            or any(not isinstance(m, dict) for m in original + selected)):
        _refuse(f"{cell['unit']}: invalid policy/history custody")
    for key, role in (("changed_observations", "tool"), ("changed_assistant_entries", "assistant")):
        changed = [i for i, (a, b) in enumerate(zip(original, selected))
                   if a.get("role") == role and a != b]
        if policy.get(key) != changed:
            _refuse(f"{cell['unit']}: {key} activation witness disagrees with request")
    if cell["arm"] == "A0" and original != selected:
        _refuse("A0 mutated the control history")
    if "completion.request.body" in cell["evidence_sha256"]:
        if _load(folder / "completion.request.body") != request:
            _refuse(f"{cell['unit']}: completion and template requests differ")
    return {"policy": policy, "evidence_sha256": dict(cell["evidence_sha256"]),
            "protected_zone_witness": "source-pinned policy; no separate native receipt"}


# Profile recognition is native grant identity, never a directory-name inference.
_ACTIVE_GRANT = "cf3c-active-evidence-20261118"
_ACTIVE_POLICY = "703eca6437f75d328998ed2636a1e3bf3d59f10abc542f634e59618b64ca83b2"


def _active_packet(path: Path, window: dict, result: dict) -> dict | None:
    if window.get("grant") != _ACTIVE_GRANT:
        if window.get("grant") != "cf3c-pilot-20261118":
            _refuse("unrecognized native producer profile")
        return None
    packet = path.parent.parent / "packet"
    inputs_path = packet / "inputs.json"
    if _sha(inputs_path) != result["packet_sha256"]:
        _refuse("active-evidence packet inputs digest mismatch")
    inputs = _load(inputs_path)
    if inputs != window.get("inputs") or inputs.get("source") != result["source"]:
        _refuse("active-evidence packet/window inputs disagree")
    _verify_seal(packet, {**inputs.get("packet_sha256", {}), "inputs.json": result["packet_sha256"]})
    pins = inputs.get("packet_sha256", {})
    if pins.get("policies.py") != _ACTIVE_POLICY or not pins.get("protocol.md"):
        _refuse("active-evidence unrecognized policy or missing motivating protocol")
    cases = _load(packet / "cases.json")
    dimensions = [("old-deep", "tool-tail"), ("old-head", "tool-head"),
                  ("old-reasoning", "assistant-reasoning")]
    if (not isinstance(cases, list) or len(cases) != 3
            or any(not isinstance(c, dict) for c in cases)
            or [(c.get("id"), c.get("location")) for c in cases] != dimensions
            or any(c.get("steps") != 10 or c.get("target") != 2 for c in cases)):
        _refuse("active-evidence equal-length fixture dimensions disagree")
    if any(not isinstance(c.get("decoys"), list) or not ns.nonneg_int(c.get("seed")) for c in cases):
        _refuse("active-evidence malformed fixture seeds or decoys")
    if len({c["seed"] for c in cases}) != 3:
        _refuse("active-evidence paired seeds must be distinct")
    values = [v for c in cases for v in [c.get("answer"), *c.get("decoys", [])]]
    if (any(not isinstance(v, str) or len(v) != 16 or any(x not in "0123456789abcdef" for x in v)
            for v in values) or len(values) != 33 or len(set(values)) != 33
            or any(len(c.get("decoys", [])) != 10 for c in cases)):
        _refuse("active-evidence fixture receipts malformed or duplicated")
    arms = ("A0", "A1-k4", "A1-k8", "A1-k12", "A2", "A3")
    expected = []
    for i, c in enumerate(cases):
        for arm in arms[i:] + arms[:i]:
            expected.append(dict(case=c["id"], arm=arm, seed=c["seed"],
                                 unit=f"{c['id']}/{arm}", ordinal=len(expected)))
    if window.get("schedule") != expected:
        _refuse("active-evidence paired all-threshold schedule disagrees with fixtures")
    return {"producer": "cf3c-active-evidence", "cases": {c["id"]: c for c in cases},
            "packet_path": str(packet), "packet_sha256": pins,
            "interpretation": "equal-length development fixtures; no task-level adoption margin"}


def _active_witness(folder: Path, cell: dict, receipt: dict, profile: dict) -> dict:
    case = profile["cases"][cell["case"]]
    if cell["seed"] != case["seed"]:
        _refuse("active-evidence fixture seed mismatch")
    if "unavailable" in receipt:
        return {"unavailable": receipt["unavailable"]}
    original = _load(folder / "original-messages.json")
    request = _load(folder / "template.request.body")
    if request.get("seed") != cell["seed"]:
        _refuse("active-evidence native request seed mismatch")
    selected = request["messages"]
    policy = receipt["policy"]
    arm = cell["arm"]
    observations = [i for i, m in enumerate(original) if m.get("role") == "tool"]
    assistants = [i for i, m in enumerate(original) if m.get("role") == "assistant"]
    if len(original) != 23 or len(observations) != 10 or len(assistants) != 10:
        _refuse("active-evidence fixture history length mismatch")
    # The pinned compressor aligns the protected prefix past the first tool pair.
    expected_tools = observations[1:7] if arm.startswith("A1-") else observations[:7] if arm == "A2" else []
    expected_assistants = assistants[:7] if arm == "A3" else []
    if (policy.get("changed_observations") != expected_tools
            or policy.get("changed_assistant_entries") != expected_assistants
            or policy.get("pairs_fixed") != 0 or policy.get("compaction_model_calls") != 0):
        _refuse("active-evidence all-threshold activation or tool-pair custody mismatch")
    if arm.startswith("A1-") and (policy.get("production_stubbed") != 6
            or policy.get("production_threshold") != int(arm.split("-k")[1])):
        _refuse("active-evidence threshold receipt mismatch")
    reasoning = case["location"] == "assistant-reasoning"
    position, field = (4, "reasoning_content") if reasoning else (5, "content")
    exposed = not (arm == "A3" if reasoning else
                   arm.startswith("A1-") or (arm == "A2" and case["location"] == "tool-tail"))
    for messages, visible in ((original, True), (selected, exposed)):
        for i, message in enumerate(messages):
            for key, value in message.items():
                count = json.dumps(value, ensure_ascii=False).count(case["answer"])
                if count != int(visible and i == position and key == field):
                    _refuse("active-evidence target receipt placement mismatch")
        if reasoning and "receipt=" in messages[5].get("content", ""):
            _refuse("active-evidence reasoning-only receipt leaked into tool")
    names = cell["evidence_sha256"]
    if "template.response.body" not in names:
        if cell["status"] != "UNKNOWN":
            _refuse("active-evidence missing native rendered prompt")
        return {"fixture": case, "unavailable": "native render", "selected_target_exposed": exposed}
    rendered = _load(folder / "template.response.body").get("prompt")
    if (not isinstance(rendered, str) or rendered.count(case["answer"]) != int(exposed)
            or cell.get("target_exposed") is not exposed):
        _refuse("active-evidence native rendered target exposure mismatch")
    for index, (tool, assistant) in enumerate(zip(observations, assistants), 1):
        for marker, text in ((f"ObservationHead{index:02}", selected[tool].get("content", "")),
                             (f"ObservationTail{index:02}", selected[tool].get("content", "")),
                             (f"ReasoningTrace{index:02}", selected[assistant].get("reasoning_content", ""))):
            if (marker in rendered) != (marker in text):
                _refuse("active-evidence native rendered marker mismatch")
    if "tokenize.request.body" in names and _load(folder / "tokenize.request.body").get("content") != rendered:
        _refuse("active-evidence tokenizer prompt differs from native render")
    return {"fixture": case, "original_target_exposed": True, "selected_target_exposed": exposed,
            "native_rendered_target_exposed": exposed, "policy_sha256": _ACTIVE_POLICY,
            "motivating_protocol_sha256": profile["packet_sha256"]["protocol.md"]}


def _deltas(cells: list[dict]) -> dict:
    """Per-case paired differences, treatment minus A0; unavailable pairs stay null."""
    controls = {(c["case"], c["seed"]): c for c in cells if c["arm"] == "A0"}
    out = {}
    for c in cells:
        if c["arm"] == "A0":
            continue
        base = controls.get((c["case"], c["seed"]))
        row = {"case": c["case"], "seed": c["seed"], "status": c["status"],
               "control_status": base["status"] if base else "unavailable"}
        for key in ("correct", "total_tokens", "wall_s"):
            a = ((base or {}).get("usage") or {}).get(key) if key == "total_tokens" else (base or {}).get(key)
            b = (c.get("usage") or {}).get(key) if key == "total_tokens" else c.get(key)
            if key == "correct":
                row[key] = int(b) - int(a) if isinstance(a, bool) and isinstance(b, bool) else None
            else:
                row[key] = b - a if ns.finite(a) and ns.finite(b) else None
        out.setdefault(c["arm"], []).append(row)
    return out


def read_unit(result_path: str | Path) -> dict:
    """Strict reader. Returns the verified, re-derived unit or raises :class:`ProjectionError`."""
    path = Path(result_path)
    result = _load(path)
    if not isinstance(result, dict) or result.get("schema") != SCHEMA:
        raise ProjectionError("not an epyc.cf3c.native.v1 RESULT")
    if result.get("server_exited") is not True:
        _refuse("server still running or exit custody absent")
    if result.get("diagnostic_only") is not True:
        _refuse("diagnostic_only must be explicit")
    if result.get("category") not in ns.CATEGORIES or not ns.SHA256.fullmatch(str(result.get("packet_sha256"))):
        _refuse("category or packet_sha256 malformed")
    window = _window(path, result)
    _verify_seal(window, result.get("window_sha256"))
    wjson = _load(window / "WINDOW.json")
    if wjson.get("smoke") is not False:
        _refuse("smoke window is not a measurement")
    if wjson.get("packet_sha256") != result["packet_sha256"] or wjson.get("source") != result.get("source"):
        _refuse("WINDOW.json packet/source disagree with RESULT")
    profile = _active_packet(path, wjson, result)
    schedule = wjson.get("schedule")
    if not isinstance(schedule, list) or len(schedule) != result["scheduled"] or not schedule:
        _refuse("sealed schedule does not match the scheduled count")
    sealed = result["window_sha256"]
    paired = result.get("paired") or {}
    cells: list[dict] = []
    identities = set()
    ordinals = set()
    witnesses = {}
    for entry in schedule:
        if (not isinstance(entry, dict) or not ns.nonneg_int(entry.get("ordinal"))
                or not all(ns.text(entry.get(k)) for k in ("case", "arm", "unit"))
                or not ns.nonneg_int(entry.get("seed"))):
            _refuse("malformed schedule entry")
        identity = (entry.get("case"), entry.get("arm"))
        if identity in identities or entry.get("ordinal") in ordinals:
            _refuse("duplicate schedule identity or ordinal")
        identities.add(identity)
        ordinals.add(entry.get("ordinal"))
        if paired.get(entry.get("case"), {}).get("seed") != entry.get("seed"):
            _refuse("paired seed disagrees with schedule")
        ordinal = entry.get("ordinal")
        rel = f"cell-{ordinal:02d}/TRAJECTORY.json" if ns.nonneg_int(ordinal) else ""
        if rel not in sealed:
            placeholder = paired.get(entry.get("case"), {}).get("arms", {}).get(entry.get("arm"))
            if not rel or placeholder != {"status": "unattempted", "correct": None}:
                _refuse(f"schedule ordinal {ordinal!r} has no sealed trajectory or native unattempted marker")
            cells.append({**entry, **placeholder})
            continue
        cell = _load(window / rel)
        for key in ("arm", "case", "ordinal", "seed", "unit"):
            if cell.get(key) != entry.get(key):
                _refuse(f"{rel}: {key} disagrees with the sealed schedule")
        if (cell.get("schema") != SCHEMA or cell.get("packet_sha256") != result["packet_sha256"]
                or cell.get("source") != result.get("source")
                or cell.get("category") != result["category"]):
            _refuse(f"{rel}: schema/packet/source/category disagree with RESULT")
        if cell.get("status") not in {"graded", "abstained", "NA", "UNKNOWN"}:
            _refuse(f"{rel}: unsupported native status")
        if cell.get("status") in {"NA", "UNKNOWN"} and cell.get("correct") is not None:
            _refuse(f"{rel}: non-graded cell carries a verdict")
        if not ns.finite(cell.get("wall_s")) or cell["wall_s"] < 0:
            _refuse(f"{rel}: invalid wall time")
        if cell.get("usage") is not None and (not isinstance(cell["usage"], dict)
                or not ns.nonneg_int(cell["usage"].get("total_tokens"))):
            _refuse(f"{rel}: invalid native total token usage")
        if cell.get("status") == "graded" and not isinstance(cell.get("correct"), bool):
            _refuse(f"{rel}: graded cell without a boolean verdict")
        if cell.get("status") == "abstained" and cell.get("correct") is not None:
            _refuse(f"{rel}: abstained cell carries a verdict")
        ev = cell.get("evidence_sha256")
        if not isinstance(ev, dict) or not ev:
            _refuse(f"{rel}: no evidence map")
        prefix = rel.rsplit("/", 1)[0]
        for name, digest in ev.items():
            if sealed.get(f"{prefix}/{name}") != digest:
                _refuse(f"{rel}: evidence {name} is not sealed under the same digest")
        if (paired.get(cell["case"], {}).get("arms", {}).get(cell["arm"])) != cell:
            _refuse(f"{rel}: RESULT.paired disagrees with the sealed trajectory")
        witnesses[cell["unit"]] = _activation(window / prefix, cell)
        if profile:
            witnesses[cell["unit"]]["active_evidence"] = _active_witness(
                window / prefix, cell, witnesses[cell["unit"]], profile)
        cells.append(cell)
    recorded = sum(c["status"] != "unattempted" for c in cells)
    completed = sum(c["status"] in {"graded", "abstained", "NA"} for c in cells)
    if (result.get("recorded") != recorded or result.get("completed") != completed
            or result.get("coverage_complete") is not (recorded == len(schedule))):
        _refuse("window counts/coverage do not re-derive from schedule and trajectories")
    if sum(len(v.get("arms", {})) for v in paired.values()) != len(cells):
        _refuse("RESULT.paired holds cells the sealed schedule does not")
    derived = _derive(cells)
    summary = result.get("arms")
    if not isinstance(summary, dict) or set(summary) != set(derived):
        _refuse("per-arm summary arms differ from the trajectories' arms")
    for arm, d in derived.items():
        s = summary[arm]
        for key in ("scheduled", "correct", "graded", "abstained", "UNKNOWN", "NA", "attempted",
                    "non_termination", "tokens_cases"):
            if s.get(key) != d[key]:
                _refuse(f"arm {arm}: summary {key}={s.get(key)!r} does not re-derive ({d[key]!r})")
        for key in ("accuracy_among_graded", "accuracy_over_attempted", "mean_total_tokens", "mean_wall_s"):
            if not _close(s.get(key), d[key]):
                _refuse(f"arm {arm}: summary {key}={s.get(key)!r} does not re-derive ({d[key]!r})")
    return {"result_path": str(path), "result_sha256": ns.file_sha256(path), "result": result,
            "window": str(window), "derived": derived, "cells": cells,
            "activation_witnesses": witnesses, "paired_deltas": _deltas(cells),
            "profile": profile,
            "scope": _scope(window, wjson.get("inputs") or {}, wjson.get("argv"))}


def native_rows(result_path: str | Path) -> tuple[dict, ...]:
    """One native per (arm, metric). A non-cf3c ``RESULT.json`` declines; a bad cf3c one refuses."""
    path = Path(result_path)
    if not path.is_file():
        return ()
    try:
        head = json.loads(path.read_text())
    except (OSError, ValueError):
        raise ProjectionError("cf3c native unit refused: RESULT.json is not JSON") from None
    if not isinstance(head, dict) or head.get("schema") != SCHEMA:
        return ()
    unit = read_unit(path)
    return tuple({"result_path": unit["result_path"], "arm": arm, "metric": metric}
                 for arm, d in sorted(unit["derived"].items()) for metric in METRICS
                 if metric == M_ACC or d["mean_total_tokens" if metric == M_TOK else "mean_wall_s"] is not None)


def _fmt(x: Any, nd: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or native.get("metric") not in METRICS or not native.get("arm"):
        raise ProjectionError("cf3c native must name a result_path, arm and metric")
    unit = read_unit(native["result_path"])  # re-open and re-verify on every projection
    arm, metric, d = native["arm"], native["metric"], unit["derived"].get(native["arm"])
    if d is None:
        raise ProjectionError(f"cf3c arm {arm!r} is not in the verified unit")
    r = unit["result"]
    cases = sorted(c["case"] for c in unit["cells"] if c["arm"] == arm)
    ident = ns.content_hash({"packet": r["packet_sha256"], "result": unit["result_sha256"],
                             "arm": arm, "metric": metric})[:24]
    producer = unit["profile"]["producer"] if unit["profile"] else PRODUCER
    label = "active-evidence development fixtures" if unit["profile"] else "deterministic-policy pilot"
    head = (f"cf3c {label} (diagnostic_only; n={d['scheduled']} cells for arm "
            f"{arm}, one per case {cases}; no adoption claim)")
    if metric == M_ACC:
        value, unit_name, direction = d["accuracy_over_scheduled"], "fraction_correct", "higher_better"
        reps = d["scheduled"]
        basis = "scheduled:cells"
        claim = (f"{head}: correct {d['correct']}/{d['scheduled']} (graded {d['graded']}, abstained "
                 f"{d['abstained']}, UNKNOWN {d['UNKNOWN']}, NA {d['NA']}, unattempted {d['unattempted']}); accuracy over scheduled "
                 f"{_fmt(value)}, among graded {_fmt(d['accuracy_among_graded'])}")
    elif metric == M_TOK:
        value, unit_name, direction = d["mean_total_tokens"], "tokens", "lower_better"
        reps, basis = d["tokens_cases"], "observed:cells"
        claim = f"{head}: mean native total tokens {_fmt(value, 1)} over {reps} cells"
    else:
        value, unit_name, direction = d["mean_wall_s"], "seconds", "lower_better"
        reps, basis = d["wall_cases"], "observed:cells"
        claim = f"{head}: mean wall {_fmt(value, 1)} s over {reps} cells"
    if value is None:
        raise ProjectionError(f"cf3c arm {arm!r} has no observation for {metric}")
    claim += (f"; recorded {d['attempted']}/{d['scheduled']}; window error={r.get('error')!r}; "
              f"cost denominators tokens={d['tokens_cases']}, wall={d['wall_cases']}; "
              "cost means cover observed cells only")
    locator = f"{producer}:{r['packet_sha256'][:16]}:{arm}:{PurePath(native['result_path']).name}"
    return ClaimTuple(
        measurement_id=f"cf3c_{ident}", metric=metric, value=value, date="",
        category=r["category"], claim=claim, metric_direction=direction, protocol_id="",
        reps=reps, reps_basis=basis, unit=unit_name,
        attestation_sha256=unit["result_sha256"], attestation_locator=locator,
        # RESULT.json was re-opened and hashed now, but the producer recorded no external digest of
        # it, so "verified against a recorded digest" is not claimable; the 223 sealed files ARE.
        attestation_present=True, attestation_verified=None, source_kind=SOURCE_KIND,
        extra={"schema": SCHEMA, "producer": producer, "arm": arm, "profile": unit["profile"],
               "packet_sha256": r["packet_sha256"], "source": r["source"],
               "diagnostic_only": r.get("diagnostic_only"), "instrument_class": r.get("instrument_class"),
               "sealed_files_verified": len(r["window_sha256"]), "n_cells": d["scheduled"],
               "result_path": unit["result_path"], "window_error": r.get("error"),
               "outcomes": {k: d[k] for k in ("graded", "abstained", "UNKNOWN", "NA", "unattempted")},
               "activation_witnesses": {c["unit"]: unit["activation_witnesses"].get(c["unit"],
                    {"unavailable": "unattempted"}) for c in unit["cells"] if c["arm"] == arm},
               "paired_deltas": unit["paired_deltas"].get(arm, [])},
        applicability=dict(unit["scope"]))


def frames_for_result(result_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(result_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames

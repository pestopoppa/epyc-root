"""AutoKernel served-shape oracle calibration as scoped MEASUREMENTS and VERIFIER verdicts (VB-AK-SERVED-SHAPE).

Native record: one lane's ``store/served_shape/`` directory, e.g.
``/mnt/raid0/llm/autokernel/campaigns/ak-ds41-1017-cpu-decode-20261021/store/served_shape/``:

* ``calibration-<ts>.json``  (``epyc.autokernel.served_shape_calibration.v2``) -- per (shape, quant type, served
  width n) the NMSE of the ANCHOR build's MUL_MAT / MUL_MAT_ID against the f32 reference, seeded per case, plus
  provenance (anchor commit, binary digests, launch recipe and its sha256);
* ``manifest.json`` / ``manifest-routed.json``  -- the per-case ``max_nmse`` caps baked into ``patch.cpp``, derived
  by research ``served_shape_cases.tightened_nmse_bound`` (factor 3, floor 1e-8, legacy cap 1e-4, generic cap 5e-4,
  ``anchor_relative`` for anchors at/above the generic cap; research ``3cf5e5b0f`` added DS41-1017 MXFP4);
* ``patch.cpp``              -- the compiled-in case set (re-hashed, every cap literal must appear in it).

STRICT READER. Every manifest cap is RE-DERIVED from the calibration NMSE with the producer's formula (mirrored
here, three constants and one function) and the ``anchor_relative`` set from the measurements at/above the generic
cap; a difference is REFUSED. A calibration that does not reproduce the manifest is not the manifest's source and
is ignored; no matching calibration => refuse. All matching calibrations must share the anchor's binary digests
and agree exactly on every NMSE (the seeded oracle is deterministic); their number is ``reps``. The anchor build's
files named in ``binary_digests`` are RE-HASHED when the build directory exists. ``launch_sha256`` is re-hashed
against the launch recipe, for EVERY matching calibration: when at least one recorded the sha256 the recipe has now,
that recipe's ``model`` (path + sha256) scopes the claims to the model file and ``extra.launch_bound_calibrations``
names the bound runs; when none did (the recipe was regenerated after every calibration), the model binding is NOT
declared, the tuples carry the lane/anchor scope only and ``extra.launch_binding`` says why. Nothing is inferred.

PROJECTION ONLY. ``claim_tuple.grade()`` decides; no ladder here. Per (shape, quant type), across widths n=1..5:

* measurement  ``servedshape_max_nmse`` -- the worst NMSE of the anchor build over the widths (lower_better), the
  per-width values in ``extra``; empty ``protocol_id`` (retrofit reading, not a protocol run) => Judged/Located;
* verifier     ``servedshape_nmse_over_cap`` -- worst NMSE/cap over the widths; ``decided_proposition`` names the
  anchor, the case, the widths and the cap rule verbatim and says PASS/FAIL. Unbound, so SC56 holds it at Judged.

Both carry ``observation.retrofit`` and ``outcome: anchor`` (a reading OF the anchor build, not a candidate).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_served_shape/v1"
AUTHORITY = "measurement"
MEASUREMENT_KIND = "autokernel-served-shape-measurement"
VERIFIER_KIND = "autokernel-served-shape-verifier"
CAL_SCHEMA = "epyc.autokernel.served_shape_calibration.v2"
MANIFEST_SCHEMAS = {"epyc.autokernel.served_shape_manifest.v1": "served_shape_lowbit_v1",
                    "epyc.autokernel.served_shape_routed_manifest.v1": "served_shape_lowbit_routed128_v1"}
SEED_SCHEME = "ak-served-shape-fnv1a64-casekey-v1"
# research served_shape_cases.py (3cf5e5b0f): mirrored, not imported (the module is a package member).
NMSE_CAP, NMSE_LEGACY_CAP, NMSE_FLOOR, NMSE_FACTOR = 5e-4, 1e-4, 1e-8, 3.0
SOURCE_ARTIFACT = "research scripts/kernel_rnd/autokernel/loop/served_shape_cases.py @3cf5e5b0f"
_HEX64 = re.compile(r"[0-9a-f]{64}")


def _sha(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"served-shape file unreadable: {path.name}: {exc}") from exc


def _num(v: Any, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")) or v < 0:
        raise ProjectionError(f"served-shape {what} is not a finite non-negative number")
    return float(v)


def derive_bound(anchor_nmse: float, anchor_relative: bool) -> float | None:
    """The producer's ``tightened_nmse_bound``; ``None`` where it would raise (anchor at/above the generic cap
    without an anchor-relative record)."""
    if anchor_nmse >= NMSE_CAP:
        return anchor_nmse * NMSE_FACTOR if anchor_relative else None
    if anchor_nmse < NMSE_LEGACY_CAP:
        return min(NMSE_LEGACY_CAP, max(NMSE_FLOOR, anchor_nmse * NMSE_FACTOR))
    return min(NMSE_CAP, anchor_nmse * NMSE_FACTOR)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


def _load_manifests(unit: Path) -> tuple[dict, dict, str, list[str]]:
    caps: dict[tuple, float] = {}
    rel: set[tuple] = set()
    lane = ""
    files: list[str] = []
    for name in ("manifest.json", "manifest-routed.json"):
        path = unit / name
        if not path.is_file():
            continue
        body = _json(path)
        if body.get("schema") not in MANIFEST_SCHEMAS or body.get("case_set_id") != MANIFEST_SCHEMAS[body["schema"]] \
                or body.get("seed_scheme") != SEED_SCHEME or not isinstance(body.get("cases"), list) \
                or not body["cases"]:
            raise ProjectionError(f"served-shape {name} has the wrong schema, case set or seed scheme")
        if lane and body.get("lane") != lane:
            raise ProjectionError("served-shape manifests name different lanes")
        lane = str(body.get("lane") or "")
        for row in body["cases"]:
            key = (row["shape_name"], row["type_a"], row["n"])
            if key in caps:
                raise ProjectionError(f"served-shape manifest repeats case {key}")
            caps[key] = _num(row["max_nmse"], "manifest max_nmse")
        for k in body.get("anchor_relative", []):
            rel.add(tuple(k))
        files.append(name)
    if not caps or not lane:
        raise ProjectionError("served-shape directory holds no manifest for a lane")
    return caps, {k: True for k in rel}, lane, files


def _rederive(cal: dict, caps: dict, rel: dict) -> bool:
    """True when this calibration reproduces every manifest cap and the anchor_relative set exactly."""
    nm: dict[tuple, float] = {}
    for row in cal.get("measurements", []):
        nm[(row["shape_name"], row["type_a"], row["n"])] = _num(row["nmse"], "calibration nmse")
    if set(caps) - set(nm):
        return False
    derived_rel = {k for k in caps if nm[k] >= NMSE_CAP}
    if derived_rel != set(rel):
        return False
    return all((b := derive_bound(nm[k], k in rel)) is not None and _close(b, caps[k]) for k in caps)


def _launch_binding(matching: list[tuple[Path, dict]]) -> dict:
    """The launch recipe is the only place the model file is named. EVERY matching calibration is checked (they
    share the anchor binary and every NMSE, so any one of them is the same reading): the model binding is declared
    when at least one of them recorded the sha256 its launch recipe has NOW, and only from that recipe. A recipe
    regenerated after an earlier calibration therefore stays drifted for that run, while a re-calibration against
    the current recipe binds the unit (P1-PHASE2-SERVED-SHAPE-RECAL). Bound runs that name different models refuse.
    No recipe on disk => absent; none bound => drifted against the newest run."""
    launch = {"binding": "absent", "model_file": "", "model_sha256": ""}
    bound: dict[str, tuple[str, str]] = {}
    drift = ""
    for path, cal in sorted(matching, key=lambda pc: str(pc[1]["provenance"].get("measured_at") or "")):
        prov = cal["provenance"]
        launch_path = Path(str(prov.get("launch") or ""))
        if not launch_path.is_file():
            continue
        actual = _sha(launch_path)
        if actual != prov.get("launch_sha256"):
            drift = f"drifted: launch recipe sha256 {actual[:12]} != calibration {str(prov.get('launch_sha256'))[:12]}"
            continue
        model = (_json(launch_path).get("model") or {})
        if not _HEX64.fullmatch(str(model.get("sha256") or "")) or not model.get("path"):
            raise ProjectionError("served-shape launch recipe names no model path/sha256")
        bound[path.name] = (Path(model["path"]).name, model["sha256"])
    if bound:
        models = set(bound.values())
        if len(models) != 1:
            raise ProjectionError(f"served-shape calibrations bound to current launch recipes name different models: "
                                  f"{sorted(models)}")
        (model_file, model_sha), = models
        return {"binding": "verified", "model_file": model_file, "model_sha256": model_sha,
                "bound_calibrations": sorted(bound)}
    if drift:
        return {"binding": drift, "model_file": "", "model_sha256": ""}
    return launch


def native_rows(unit_dir: str | Path) -> list[dict]:
    unit = Path(unit_dir)
    if unit.is_file():
        unit = unit.parent
    cal_files = sorted(unit.glob("calibration-*.json"))
    if not cal_files or not (unit / "manifest.json").is_file():
        return []
    caps, rel, lane, manifest_files = _load_manifests(unit)
    patch = unit / "patch.cpp"
    if not patch.is_file():
        raise ProjectionError("served-shape patch.cpp is absent: the compiled-in case set cannot be checked")
    patch_text = patch.read_text(encoding="utf-8", errors="replace")
    for key, cap in caps.items():
        if f"{cap:g}" not in patch_text:
            raise ProjectionError(f"served-shape patch.cpp does not carry the manifest cap for {key}")
    matching: list[tuple[Path, dict]] = []
    for path in cal_files:
        cal = _json(path)
        if cal.get("schema") != CAL_SCHEMA or cal.get("seed_scheme") != SEED_SCHEME or cal.get("lane") != lane:
            continue
        if _rederive(cal, caps, rel):
            matching.append((path, cal))
    if not matching:
        raise ProjectionError("no served-shape calibration re-derives the manifest caps (stale or foreign manifest)")
    first = matching[0][1]
    digests = first["provenance"]["binary_digests"]
    anchor_commit = str(first["provenance"].get("anchor_commit") or "")
    for _, cal in matching[1:]:
        if cal["provenance"].get("binary_digests") != digests or cal["provenance"].get("anchor_commit") != anchor_commit:
            raise ProjectionError("matching served-shape calibrations disagree on the anchor binary digests")
        a = {(r["shape_name"], r["type_a"], r["n"]): r["nmse"] for r in first["measurements"]}
        b = {(r["shape_name"], r["type_a"], r["n"]): r["nmse"] for r in cal["measurements"]}
        if a != b:
            raise ProjectionError("matching served-shape calibrations disagree on a NMSE (seeded oracle must repeat)")
    if not re.fullmatch(r"[0-9a-f]{40}", anchor_commit) or "libggml-cpu.so" not in digests \
            or "test-backend-ops" not in digests:
        raise ProjectionError("served-shape calibration provenance lacks the anchor commit or binary digests")
    rehashed, not_rehashed = [], []
    build_bin = Path(str(first["provenance"].get("anchor_build") or "")) / "bin"
    for name, digest in sorted(digests.items()):
        if not _HEX64.fullmatch(str(digest)):
            raise ProjectionError("served-shape binary digest malformed")
        f = build_bin / name
        if f.is_file():
            if _sha(f) != digest:
                raise ProjectionError(f"served-shape anchor build file {name} re-hashes to a different digest")
            rehashed.append(name)
        else:
            not_rehashed.append(name)
    launch = _launch_binding(matching)
    measured = max(str(c["provenance"].get("measured_at") or "") for _, c in matching)
    nmse = {(r["shape_name"], r["type_a"], r["n"]): float(r["nmse"]) for r in first["measurements"]}
    groups: dict[tuple, list] = {}
    for (shape, typ, n) in sorted(caps):
        groups.setdefault((shape, typ), []).append(n)
    anchor_id = hashlib.sha256((digests["libggml-cpu.so"] + digests["test-backend-ops"]).encode()).hexdigest()[:12]
    common = {"unit_dir": str(unit), "lane": lane, "anchor_commit": anchor_commit, "anchor_id": anchor_id,
              "measured_at": measured, "reps": len(matching), "launch": launch,
              "calibrations": {p.name: _sha(p) for p, _ in matching},
              "manifests": {n: _sha(unit / n) for n in manifest_files}, "patch_sha256": _sha(patch),
              "rehashed": rehashed, "not_rehashed": not_rehashed,
              "cpu_only": "libggml-cpu.so" in digests and not any("hip" in k for k in digests)}
    rows: list[dict] = []
    for (shape, typ), widths in sorted(groups.items()):
        per = [{"n": n, "nmse": nmse[(shape, typ, n)], "cap": caps[(shape, typ, n)],
                "anchor_relative": (shape, typ, n) in rel} for n in sorted(widths)]
        for kind in ("measurement", "verifier"):
            rows.append({"kind": kind, "shape": shape, "type_a": typ, "widths": per, **common})
    return rows


def _proposition(row: dict) -> str:
    worst = max(row["widths"], key=lambda w: w["nmse"] / w["cap"])
    verdict = "PASS" if all(w["nmse"] <= w["cap"] for w in row["widths"]) else "FAIL"
    rel = [w["n"] for w in row["widths"] if w["anchor_relative"]]
    return (f"{verdict}: the anchor build (commit {row['anchor_commit'][:9]}, anchor {row['anchor_id']}) computes "
            f"lane {row['lane']} served shape {row['shape']} at quant {row['type_a']} for served widths "
            f"n={row['widths'][0]['n']}..{row['widths'][-1]['n']} with NMSE <= the per-case max_nmse baked into "
            f"patch.cpp {row['patch_sha256'][:12]} (anchor NMSE x3 clamped to [1e-8, 1e-4] / <= 5e-4"
            f"{', anchor-relative for n=' + ','.join(map(str, rel)) if rel else ''}); worst width n={worst['n']}: "
            f"NMSE {worst['nmse']:.4g} vs cap {worst['cap']:.4g}")


def _scope(row: dict) -> dict:
    scope: dict = {"scope_basis": "native", "build_sha": row["anchor_commit"], "shape": f"{row['shape']}/{row['type_a']}",
                   "surface": f"autokernel-served-shape:{row['lane']}"}
    if row["cpu_only"]:
        scope["backend"] = "cpu"
    if row["launch"]["model_file"]:
        scope["model_file"] = row["launch"]["model_file"]
        scope["model_sha256"] = row["launch"]["model_sha256"]
    return scope


def _row(native: dict) -> dict:
    if not isinstance(native, dict) or native.get("kind") not in ("measurement", "verifier") \
            or not native.get("widths"):
        raise ProjectionError("served-shape native row malformed")
    for w in native["widths"]:
        expected = derive_bound(_num(w["nmse"], "nmse"), w["anchor_relative"])
        if expected is None or not _close(expected, _num(w["cap"], "cap")):
            raise ProjectionError("served-shape cap does not re-derive from the NMSE")
    return native


def _date(row: dict) -> str:
    try:
        t = _dt.datetime.fromisoformat(row["measured_at"])
    except ValueError as exc:
        raise ProjectionError("served-shape measured_at is not an ISO timestamp") from exc
    return t.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extra(row: dict) -> dict:
    return {"lane": row["lane"], "shape_name": row["shape"], "type_a": row["type_a"], "anchor_id": row["anchor_id"],
            "anchor_commit": row["anchor_commit"], "per_width": row["widths"], "calibrations": row["calibrations"],
            "manifests": row["manifests"], "patch_sha256": row["patch_sha256"], "launch_binding": row["launch"]["binding"],
            "rehashed": row["rehashed"], "not_rehashed": row["not_rehashed"], "cap_rule": SOURCE_ARTIFACT,
            "unit_dir": row["unit_dir"], "retrofit": True,
            # only when bound, so a drifted unit projects exactly as before (no ledger churn)
            **({"launch_bound_calibrations": row["launch"]["bound_calibrations"]}
               if row["launch"].get("bound_calibrations") else {})}


def _common(row: dict, metric: str, value: float, unit: str, claim: str, **kw) -> ClaimTuple:
    ident = f"servedshape:v1:{row['lane']}:{row['anchor_id']}:{row['shape']}:{row['type_a']}"
    return ClaimTuple(
        measurement_id=ident + (":verify" if kw.get("source_class") == "verifier" else ""),
        metric=metric, value=value, unit=unit, date=_date(row), category="BASELINE", claim=claim,
        metric_direction="lower_better", protocol_id="", reps=row["reps"],
        reps_basis="scored:matching calibration runs of the one anchor build (identical binary digests, identical NMSE)",
        attestation_locator=f"{row['unit_dir']}/calibration|{','.join(sorted(row['calibrations']))}",
        attestation_sha256=sorted(row["calibrations"].values())[-1], attestation_present=True,
        attestation_verified=True, source_kind=kw.pop("source_kind"), applicability=_scope(row),
        extra=_extra(row), **kw)


@register(MEASUREMENT_KIND)
def project_measurement(native: dict) -> ClaimTuple:
    row = _row(native)
    if row["kind"] != "measurement":
        raise ProjectionError("served-shape measurement projection given a verifier row")
    worst = max(row["widths"], key=lambda w: w["nmse"])
    claim = (f"Served-shape oracle, lane {row['lane']}, anchor build {row['anchor_commit'][:9]}: {row['shape']} at "
             f"{row['type_a']} has worst NMSE {worst['nmse']:.4g} vs the f32 reference over served widths "
             f"{', '.join('n=%d %.3g' % (w['n'], w['nmse']) for w in row['widths'])} (cap at worst width "
             f"{worst['cap']:.4g}); seeded per case, {row['reps']} matching calibration run(s)")
    t = _common(row, "servedshape_max_nmse", worst["nmse"], "nmse", claim, source_kind=MEASUREMENT_KIND)
    from dataclasses import replace
    return replace(t, observation={"retrofit": True, "outcome": "anchor", "anchor_value": worst["nmse"],
                                   "outcome_native": f"anchor NMSE; cap {worst['cap']:.4g} at n={worst['n']}"[:120]})


@register(VERIFIER_KIND, source_class="verifier", decided_proposition_field="decided_proposition")
def project_verifier(native: dict) -> ClaimTuple:
    row = _row(native)
    if row["kind"] != "verifier":
        raise ProjectionError("served-shape verifier projection given a measurement row")
    ratio = max(w["nmse"] / w["cap"] for w in row["widths"])
    prop = _proposition(row)
    claim = (f"Served-shape cap check, lane {row['lane']}, anchor {row['anchor_commit'][:9]}: {row['shape']} at "
             f"{row['type_a']} worst NMSE/cap = {ratio:.3g} over n={row['widths'][0]['n']}..{row['widths'][-1]['n']} "
             f"-> {'within' if ratio <= 1 else 'OVER'} the per-case cap")
    t = _common(row, "servedshape_nmse_over_cap", ratio, "ratio", claim, source_kind=VERIFIER_KIND,
                decided_proposition=prop, source_class="verifier", binding_kind="")
    from dataclasses import replace
    return replace(t, observation={"retrofit": True, "outcome": "anchor", "anchor_value": ratio,
                                   "outcome_native": prop.split(":", 1)[0]})


__all__ = ["ADAPTER_ID", "AUTHORITY", "MEASUREMENT_KIND", "VERIFIER_KIND", "derive_bound", "native_rows",
           "project_measurement", "project_verifier"]

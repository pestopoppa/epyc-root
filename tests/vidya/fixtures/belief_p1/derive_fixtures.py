#!/usr/bin/env python3
"""Derive the belief-redesign P1 fixtures from REAL AutoKernel records, trimmed and re-sealed.

Run once (never from a test), outside CPU timing windows:

    python3 -I tests/vidya/fixtures/belief_p1/derive_fixtures.py

What it writes under `tests/vidya/fixtures/belief_p1/`:

  serving/<label>/serving-beliefs/<capture>.json            receipt (re-sealed)
  serving/<label>/serving-beliefs/sources/<capture>.json    source  (trimmed, re-sealed)
      labels: ds41 (serving_ab.v2, a DECISIVE capture), q38fn (serving_ab.v2),
              runtime_ab (serving_runtime_ab.v1)
  floor/q27b/serving-floor.<recipe>.requests-<digest>.json  27B GPU floor (launch_residency trimmed)
  floor/q27b/loop-status.json                               the store's target block only
  PROVENANCE.json                                           original path + sha256 per fixture

TRIMMING. A real serving source is 0.5-47 MB because every launch window carries its CPU
lifecycle samples. Each window is cut to its scalar keys (backend, window_start/_end, status, ...).
Every NUMBER the adapters read -- the per-launch samples, medians, effect, floor, decisive, pairs,
plan, recipe, model, build paths, epoch, mechanism -- is the real one, untouched.

RE-SEALING. The strict reader replays the producer's seal chain, so after trimming it is
recomputed exactly as the producer computes it: matched-plan membership residency digests ->
native digest -> capture id -> belief rows' ids -> capture digest -> receipt. A fixture is
therefore a real record whose residency bulk was removed and whose seal was re-derived; the
script then reads each fixture back through the unchanged strict reader (v1 and v2) and refuses
to finish if either refuses it.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from adapters import autokernel_legacy_serving as reader  # noqa: E402

CAMPAIGNS = Path("/mnt/raid0/llm/autokernel/campaigns")
SUMMARY = Path("/mnt/raid0/llm/tmp/belief-redesign-20261021/serving_sources_summary.json")
FLOOR = (CAMPAIGNS / "ak-27b-gpu-verify-20261004/store/serving-floor.q27b-9a3f1392a-gpu-dflash2-"
         "np1.requests-baa3aa6d30b8bef8263480a6d84250fabadfaac2944359111fb0a5cf9bd428ed.json")
WINDOW_KEYS = ("backend", "window_start", "window_end", "status", "gpu_residency",
               "clock_stable", "contention", "cpu_placement", "covers_request_phase", "resident",
               "schema")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pick(summary: list[dict]) -> dict[str, dict]:
    def path_of(row: dict) -> Path:
        directory = CAMPAIGNS / row["store"] / "serving-beliefs"
        matches = sorted(directory.glob(f"{row['capture']}*.json"))
        if len(matches) != 1:
            raise SystemExit(f"capture {row['capture']} is not unique in {directory}")
        return matches[0]

    def smallest(rows: list[dict]) -> dict:
        rows = [dict(r, receipt=path_of(r)) for r in rows]
        for r in rows:
            r["source"] = r["receipt"].parent / "sources" / r["receipt"].name
            r["size"] = r["source"].stat().st_size
        return min(rows, key=lambda r: (r["size"], r["capture"]))

    v2 = "epyc.autokernel.serving_ab.v2"
    runtime = "epyc.autokernel.serving_runtime_ab.v1"
    return {
        "ds41": smallest([r for r in summary if r["store"].startswith("ak-ds41")
                          and r["schema"] == v2 and r.get("decisive") is True]),
        "q38fn": smallest([r for r in summary if r["store"].startswith("ak-q38fn")
                           and r["schema"] == v2]),
        "runtime_ab": smallest([r for r in summary if r["schema"] == runtime]),
    }


def _trim_window(window: dict) -> dict:
    return {k: window[k] for k in WINDOW_KEYS if k in window}


def _reseal(source: dict) -> tuple[dict, dict, bytes]:
    comparison = source["comparison"]
    capture = comparison["belief_capture"]
    for arm in ("anchor", "candidate"):
        comparison[f"{arm}_residency"] = [_trim_window(w) for w in comparison[f"{arm}_residency"]]
    for entry in comparison.get("launch_membership") or []:
        arm, index = entry["arm"], entry["arm_sample_index"]
        entry["residency_sha256"] = reader._digest([comparison[f"{arm}_residency"][index]])
    native = {k: v for k, v in comparison.items()
              if k not in {"belief_capture", "surface", "baseline_scope"}}
    native_sha = reader._digest(native)
    capture_id = reader._digest({"native_sha256": native_sha, "inputs": capture["inputs"]})
    capture["native_sha256"] = native_sha
    capture["capture_id"] = capture_id
    for row in capture["belief_measurements"]:
        row["measurement_id"] = f"legacy-serving:{capture_id}:{row['extra']['arm']}"
        row["extra"]["capture_id"] = capture_id
        row["extra"]["native_sha256"] = native_sha
    capture["capture_sha256"] = reader._digest(
        {k: v for k, v in capture.items() if k != "capture_sha256"})
    raw = json.dumps(source, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    receipt = {"schema": reader.RECEIPT_SCHEMA, "capture_id": capture_id,
               "capture_sha256": capture["capture_sha256"],
               "native_reference": {"path": f"sources/{capture_id}.json", "sha256": _sha(raw),
                                    "size": len(raw)}}
    return source, receipt, raw


def _write_serving(label: str, pick: dict, provenance: list) -> None:
    original = pick["source"].read_bytes()
    source, receipt, raw = _reseal(json.loads(original))
    out = HERE / "serving" / label / "serving-beliefs"
    (out / "sources").mkdir(parents=True, exist_ok=True)
    for stale in list(out.glob("*.json")) + list((out / "sources").glob("*.json")):
        stale.unlink()
    (out / "sources" / f"{receipt['capture_id']}.json").write_bytes(raw)
    receipt_raw = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt_path = out / f"{receipt['capture_id']}.json"
    receipt_path.write_bytes(receipt_raw)
    locator = f"autokernel:{receipt_path}"
    v1 = reader.native_rows(receipt, receipt_locator=locator, receipt_sha256=_sha(receipt_raw))
    v2 = reader.native_rows_v2(receipt, receipt_locator=locator, receipt_sha256=_sha(receipt_raw))
    assert len(v1) == 2 and len(v2) == 1, (label, len(v1), len(v2))
    provenance.append({"fixture": str(receipt_path.relative_to(HERE)), "label": label,
                       "original_source": str(pick["source"]),
                       "original_source_sha256": _sha(original),
                       "original_receipt": str(pick["receipt"]),
                       "schema": source["comparison"]["schema"],
                       "mechanism_id": source.get("mechanism_id"),
                       "decisive": source["comparison"].get("decisive"),
                       "trimmed": "residency windows cut to scalar keys; seal re-derived"})


def _write_floor(provenance: list) -> None:
    original = FLOOR.read_bytes()
    floor = json.loads(original)
    floor["launch_residency"] = [_trim_window(w) for w in floor.get("launch_residency") or []][:1]
    out = HERE / "floor" / "q27b"
    out.mkdir(parents=True, exist_ok=True)
    (out / FLOOR.name).write_text(json.dumps(floor, indent=2, sort_keys=True) + "\n")
    status_path = FLOOR.parent / "loop-status.json"
    status_raw = status_path.read_bytes()
    status = json.loads(status_raw)
    target = status["target"]
    execution = target["original_target"]["execution"]
    trimmed = {"schema": status["schema"], "surface": status.get("surface"),
               "target": {"campaign_id": target.get("campaign_id"),
                          "selected_id": target.get("selected_id"),
                          "original_target": {"execution": {
                              "backend": execution.get("backend"),
                              "model": execution.get("model"),
                              "build": execution.get("build")}}}}
    (out / "loop-status.json").write_text(json.dumps(trimmed, indent=2, sort_keys=True) + "\n")
    provenance.append({"fixture": f"floor/q27b/{FLOOR.name}", "original": str(FLOOR),
                       "original_sha256": _sha(original),
                       "trimmed": "launch_residency cut to its first window's scalar keys"})
    provenance.append({"fixture": "floor/q27b/loop-status.json", "original": str(status_path),
                       "original_sha256": _sha(status_raw),
                       "trimmed": "target.selected_id/campaign_id and execution backend/model/"
                                  "build only"})


def main() -> int:
    picks = _pick(json.loads(SUMMARY.read_text()))
    provenance: list[dict] = []
    for label, pick in picks.items():
        _write_serving(label, pick, provenance)
    _write_floor(provenance)
    (HERE / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(json.dumps(provenance, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

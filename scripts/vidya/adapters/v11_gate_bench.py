"""VB-HARVEST-1022.a: V11 GPU gate llama-bench A/B alternating-launch timing (v11-050/051/052) as measurement OBSERVATIONS.

Source: one gate run dir (``COMPLETE``, ``DECISION.json``, ``PREDECLARED.md``, ``manifest.json``,
``bench_<set>-<arm><launch>.json`` llama-bench ``-o json`` files; arm letters ``A`` (base), ``B``, ``B2``).
Read-side post-processor of a COMPLETE run: no producer change, no inference.

One tuple per (arm, cell): the effect ``median(arm)/median(A) - 1`` in percent over the per-launch ``avg_ts`` values,
with the A-arm between-launch spread (the predeclared noise unit) carried in the observation. The strict reader
RE-DERIVES effect, both spreads and n from the raw llama-bench rows and refuses any difference from the gate's own
``DECISION.json``; it also refuses an incomplete run, a ``PREDECLARED.md`` whose sha256 differs from the decision's,
and any row whose ``autokernel_hardened`` state is not the ordinary protocol (the request cannot be recovered from
these dirs; see ``_llama_bench_protocol``). The gate's decision word is carried as ``outcome_native`` only.
``protocol_id`` is empty (a predeclared one-window gate is not a codified protocol), so the shared ladder caps
every tuple at an observation; ``claim_tuple.grade()`` is the only grader.
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.v11_gate_bench/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "v11-gate-bench"
MAX_BYTES = 32 << 20
TOL = 0.0015  # DECISION.json rounds to 3 decimals
_FILE = re.compile(r"bench_(?P<set>[a-z]+)-(?P<tag>[AB]2?\d)\.json")
# DECISION.json key holding each non-base arm's effects
_EFFECT_KEYS = {"B": ("effects", "effects_default"), "B2": ("effects_max_cols_32",)}


def _read(path: Path) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ProjectionError(f"v11-gate-bench input unreadable: {path}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ProjectionError(f"v11-gate-bench input exceeds bound: {path}")
    return raw


def _tag(tag: str) -> tuple[str, int]:
    return (tag[:2], int(tag[2])) if len(tag) == 3 else (tag[0], int(tag[1]))


def _cell(r: dict) -> str:
    n_p, n_g, depth = r["n_prompt"], r["n_gen"], r["n_depth"]
    name = f"pp{n_p}" if n_p and not n_g else f"tg{n_g}" if n_g and not n_p else f"pp{n_p}+tg{n_g}"
    return name + (f"@d{depth}" if depth else "")


def _spread(vals: list[float]) -> float:
    return round(100.0 * (max(vals) - min(vals)) / statistics.median(vals), 3)


def native_rows(path: str | Path) -> tuple[dict, ...]:
    d = Path(path)
    if d.is_file():
        d = d.parent
    dec_p = d / "DECISION.json"
    if not dec_p.is_file():
        return ()
    if not (d / "COMPLETE").is_file():
        raise ProjectionError(f"v11-gate-bench {d}: no COMPLETE marker (an unfinished run projects nothing)")
    dec_raw = _read(dec_p)
    dec = json.loads(dec_raw)
    if dec.get("complete") is not True or dec.get("decision") not in ("hold", "keep_default_on", "keep_opt_in"):
        raise ProjectionError(f"v11-gate-bench {d}: DECISION.json is not a complete decision")
    pre = _read(d / "PREDECLARED.md")
    if hashlib.sha256(pre).hexdigest() != dec.get("predeclared_sha256"):
        raise ProjectionError(f"v11-gate-bench {d}: PREDECLARED.md sha256 differs from the decision's")
    launches: dict[tuple[str, str], dict[int, float]] = {}
    builds: dict[str, set[str]] = {}
    models: set[str] = set()
    for f in sorted(d.glob("bench_*.json")):
        m = _FILE.fullmatch(f.name)
        if not m:
            raise ProjectionError(f"v11-gate-bench {d}: unrecognised bench file {f.name}")
        arm, launch = _tag(m["tag"])
        for r in json.loads(_read(f)):
            if r.get("autokernel_hardened") is not False:
                raise ProjectionError(f"v11-gate-bench {f.name}: autokernel_hardened is {r.get('autokernel_hardened')!r}; "
                                      "only the ordinary protocol is projectable (request unrecoverable)")
            if not isinstance(r.get("avg_ts"), (int, float)) or r["avg_ts"] <= 0:
                raise ProjectionError(f"v11-gate-bench {f.name}: avg_ts missing or non-positive")
            cell = launches.setdefault((arm, _cell(r)), {})
            if launch in cell:
                raise ProjectionError(f"v11-gate-bench {f.name}: duplicate launch {arm}{launch} for {_cell(r)}")
            cell[launch] = float(r["avg_ts"])
            builds.setdefault(arm, set()).add(str(r.get("build_commit")))
            models.add(str(r.get("model_filename")))
    if not launches:
        raise ProjectionError(f"v11-gate-bench {d}: no llama-bench rows")
    dec_sha = hashlib.sha256(dec_raw).hexdigest()
    out = []
    for arm, keys in _EFFECT_KEYS.items():
        effects = next((dec[k] for k in keys if k in dec), None)
        if effects is None or not any(a == arm for a, _ in launches):
            continue
        for cell, want in effects.items():
            base, mine = launches.get(("A", cell)), launches.get((arm, cell))
            if not base or not mine:
                raise ProjectionError(f"v11-gate-bench {d}: decision cell {arm}/{cell} has no raw launches")
            n_base, n_arm = len(base), len(mine)
            got = {"effect_pct": round(100.0 * (statistics.median(mine.values()) / statistics.median(base.values()) - 1.0), 3),
                   "base_spread_pct": _spread(list(base.values())), "arm_spread_pct": _spread(list(mine.values())),
                   "n_base": n_base, "n_arm": n_arm}
            for k, v in got.items():
                if abs(v - want[k]) > TOL:
                    raise ProjectionError(f"v11-gate-bench {d} {arm}/{cell}: {k} {want[k]} in DECISION.json does not "
                                          f"re-derive from the raw rows ({v})")
            out.append({"item": dec["item"], "arm": arm, "cell": cell, "eff": got, "decision": dec["decision"],
                        "decided_at": dec["decided_at"], "base_build": sorted(builds["A"]), "arm_build": sorted(builds[arm]),
                        "model": sorted(models), "path": str(dec_p), "sha256": dec_sha,
                        "locator": f"v11-gate-bench:{d.name}:{arm}:{cell}"})
    if not out:
        raise ProjectionError(f"v11-gate-bench {d}: DECISION.json carries no effect table")
    return tuple(out)


def units(path: Path) -> list[Path]:
    path = Path(path)
    if path.is_file():
        return [path.parent] if path.name == "DECISION.json" else []
    if not path.is_dir():
        return []
    return sorted({p.parent for p in (path / "DECISION.json", *path.glob("*/DECISION.json"), *path.glob("*/*/DECISION.json"))
                   if p.is_file() and any(p.parent.glob("bench_*.json"))})


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or "eff" not in native:
        raise ProjectionError("v11-gate-bench native row missing")
    e = native["eff"]
    floor = e["base_spread_pct"]
    claim = (f"{native['item']} llama-bench {native['cell']}: arm {native['arm']} ({','.join(native['arm_build'])}) vs base A "
             f"({','.join(native['base_build'])}) median-of-launches effect {e['effect_pct']:+.3f}% over n={e['n_arm']} vs "
             f"{e['n_base']} alternating launches; base between-launch spread {floor}%, arm {e['arm_spread_pct']}% "
             f"(one host, one window). Gate decision: {native['decision']}.")
    return ClaimTuple(
        measurement_id=f"{native['item']}:{native['arm']}:{native['cell']}", metric="v11_bench_effect_pct",
        value=e["effect_pct"], date=native["decided_at"][:10], category="CANDIDATE", claim=claim,
        metric_direction="higher_better", protocol_id="", reps=e["n_arm"],
        reps_basis="scored: alternating launches of the arm; each launch is one llama-bench invocation", unit="pct",
        attestation_path=native["path"], attestation_sha256=native["sha256"], attestation_locator=native["locator"],
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={"scope_basis": "native", "build_sha": native["arm_build"][0]},
        observation={"outcome_native": f"{native['arm']}/{native['cell']} {e['effect_pct']:+.3f}% ({native['decision']})"[:120]},
        extra={"adapter": ADAPTER_ID, "item": native["item"], "cell": native["cell"], "arm": native["arm"],
               "effect": e, "model": native["model"]})


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project", "units", "frames_for_path"]

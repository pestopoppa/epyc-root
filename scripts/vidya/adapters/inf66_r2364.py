"""INF-66 R23-64 CPU decode thread re-sweep -> strict native reader -> shared grade (VB-R2364-SWEEP-WIRE).

Native unit: one sweep directory (``ANALYSIS.json``, ``RESULT.txt``, ``SHA256SUMS``, ``runs/<arm>_r<N>.*``).
Producer: research ``data/inf66/r23-64-thread-sweep-20261025/``; unit of replication = LAUNCH.

The adapter PROJECTS, it never grades (spec 4.7). Nothing here is a ladder, a threshold or a verdict
rule: ``RESOLVED`` / ``UNRESOLVED`` are copied verbatim from the producer's ``RESULT.txt`` line for the
arm (the analyzer's own word) into ``observation.outcome_native`` and the claim text, and are NOT
re-derived. Before projecting, the reader re-opens the sealed bytes and refuses anything that does not
re-derive: every file it reads must match ``SHA256SUMS``; every launch's token-weighted t/s is recomputed
from its ``rows.jsonl`` (sum pred_n / sum pred_ms over rows with pred_n >= 16, the producer's own
definition) and must equal ``ANALYSIS.json``; arm mean / sd / n must equal the launch values; the floor
must be the launch-unit floor (an arm-unit floor is refused: FLOOR-UNIT-1); each launch's argv thread
count must equal its arm label and the GGML_* env must be one set across all launches.

Two claims shapes, one tuple each:
* per arm: mean decode t/s over the arm's launches (the serving rate per thread count; the t48 control
  is category BASELINE);
* per non-control arm: effect vs control in percent, floor and MDE carried in the observation.

``protocol_id`` is empty: the producer declares no registered protocol and none is invented.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.inf66_r2364/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "inf66-r2364-thread-sweep"
DEFAULT_ROOT = Path("/workspace/repos/epyc-inference-research/data/inf66")
MAX_BYTES = 64 << 20
MIN_PRED_N = 16
_VERDICT_LINE = re.compile(r"^\s*(t\d+)\s+(-?\d+(?:\.\d+)?)%\s+CI \[([^\]]+)\]%.*?\s(RESOLVED|UNRESOLVED)\s*$")
_FINISHED = re.compile(r"finished:\s*(\d{4}-\d{2}-\d{2})T")
_CHAMPION = re.compile(r"champion\s+([0-9a-f]{7,40})\b")
_BUILD = re.compile(r"/(cpu-\d{8}-([0-9a-f]{7,40})[^/]*)/bin/")
_ARM = re.compile(r"t(\d+)\Z")


def _fail(msg: str):
    raise ProjectionError(f"inf66-r2364 sweep refused: {msg}")


def _sums(unit: Path) -> dict[str, str]:
    path = unit / "SHA256SUMS"
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        _fail(f"cannot read SHA256SUMS: {exc}")
    found: dict[str, str] = {}
    for line in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  \./(.+)", line)
        if not m or ".." in Path(m.group(2)).parts or m.group(2) in found:
            _fail(f"malformed or duplicate SHA256SUMS entry {line[:80]!r}")
        found[m.group(2)] = m.group(1)
    return found


class _Sealed:
    """Reads only files the producer sealed, and only if their bytes still match."""

    def __init__(self, unit: Path):
        self.unit, self.sums = unit, _sums(unit)

    def read(self, rel: str) -> bytes:
        want = self.sums.get(rel)
        if want is None:
            _fail(f"{rel} is not covered by SHA256SUMS")
        p = self.unit / rel
        try:
            if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_BYTES:
                _fail(f"unsafe or oversized input {rel}")
            raw = p.read_bytes()
        except OSError as exc:
            _fail(f"cannot read {rel}: {exc}")
        if hashlib.sha256(raw).hexdigest() != want:
            _fail(f"{rel} no longer matches SHA256SUMS")
        return raw


def _num(x: Any, what: str) -> float:
    if type(x) not in (int, float) or not math.isfinite(x):
        _fail(f"{what} is not a finite number")
    return float(x)


def _launch_tps(rows: list[dict], label: str) -> tuple[float, int]:
    ok = [r for r in rows if type(r.get("pred_n")) is int and r["pred_n"] >= MIN_PRED_N]
    ms = sum(_num(r.get("pred_ms"), f"{label} pred_ms") for r in ok)
    if not ok or ms <= 0:
        _fail(f"{label}: no decode rows with pred_n >= {MIN_PRED_N}")
    return sum(r["pred_n"] for r in ok) / (ms / 1000.0), len(ok)


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _argv_threads(raw: bytes, label: str) -> tuple[int, str, str]:
    toks = raw.decode("utf-8", "replace").split("\n")
    try:
        threads = int(toks[toks.index("-t") + 1])
        model = Path(toks[toks.index("-m") + 1]).name
    except (ValueError, IndexError):
        _fail(f"{label}: argv lacks -t / -m")
    build = next((t for t in toks if _BUILD.search(t)), "")
    m = _BUILD.search(build)
    if not m:
        _fail(f"{label}: argv names no cpu build directory")
    return threads, model, m.group(2)


def _ggml_env(raw: bytes) -> tuple[tuple[str, str], ...]:
    out = []
    for line in raw.decode("utf-8", "replace").splitlines():
        k, _, v = line.partition("=")
        if k.startswith("GGML_"):
            out.append((k, v))
    return tuple(sorted(out))


def native_rows(path) -> tuple[dict, ...]:
    unit = Path(path)
    unit = unit.parent if unit.is_file() else unit
    sealed = _Sealed(unit)
    try:
        ana = json.loads(sealed.read("ANALYSIS.json"))
    except ValueError as exc:
        _fail(f"ANALYSIS.json is not JSON: {exc}")
    result = sealed.read("RESULT.txt").decode("utf-8", "replace")
    if not isinstance(ana, dict) or not isinstance(ana.get("arms"), dict) or not isinstance(ana.get("launches"), list):
        _fail("ANALYSIS.json lacks arms/launches")
    if ana.get("unit") != "launch":
        _fail(f"unit is {ana.get('unit')!r}, not launch (FLOOR-UNIT-1)")
    floor = ana.get("floor") or {}
    if floor.get("unit") != "launch":
        _fail("floor is not the launch-unit floor (FLOOR-UNIT-1)")
    floor_pct = _num(floor.get("sd_pct"), "floor.sd_pct")
    control = ana.get("control")
    if control not in ana["arms"]:
        _fail("control arm absent")
    if ana.get("excluded"):
        _fail("analysis excluded launches; the reader projects only the full valid set")

    fin, champ = _FINISHED.search(result), _CHAMPION.search(result)
    if not fin or not champ:
        _fail("RESULT.txt lacks finish date or champion sha")
    verdicts: dict[str, dict] = {}
    for line in result.splitlines():
        m = _VERDICT_LINE.match(line)
        if m:
            verdicts[m.group(1)] = {"verdict": m.group(4), "line": line.strip()}

    by_arm: dict[str, list[float]] = {}
    envs, models, builds = set(), set(), set()
    thread_of: dict[str, int] = {}
    for ln in ana["launches"]:
        label, arm = ln.get("label"), ln.get("arm")
        if not isinstance(label, str) or ln.get("status") != "valid" or arm not in ana["arms"]:
            _fail(f"launch {label!r} is not a valid launch of a known arm")
        tps, n_dec = _launch_tps([json.loads(x) for x in sealed.read(f"runs/{label}.rows.jsonl").decode().splitlines() if x.strip()], label)
        if not _close(tps, _num(ln.get("tps"), f"{label} tps")) or n_dec != ln.get("n_dec"):
            _fail(f"{label}: recomputed {tps!r} over {n_dec} rows differs from ANALYSIS {ln.get('tps')!r}/{ln.get('n_dec')!r}")
        th, model, build = _argv_threads(sealed.read(f"runs/{label}.argv"), label)
        if f"t{th}" != arm or thread_of.setdefault(arm, th) != th:
            _fail(f"{label}: argv -t {th} does not match arm {arm}")
        envs.add(_ggml_env(sealed.read(f"runs/{label}.env")))
        models.add(model)
        builds.add(build)
        by_arm.setdefault(arm, []).append(tps)
    if len(envs) != 1 or len(models) != 1 or len(builds) != 1:
        _fail("launches differ in GGML_* env, model or build")
    build_sha = builds.pop()
    if not champ.group(1).startswith(build_sha[:7]) and not build_sha.startswith(champ.group(1)[:7]):
        _fail("build directory sha differs from the champion named in RESULT.txt")

    arms: dict[str, dict] = {}
    for arm, rec in ana["arms"].items():
        vals = by_arm.get(arm, [])
        if not _ARM.fullmatch(arm) or len(vals) != rec.get("n") or len(vals) < 2:
            _fail(f"arm {arm}: launches {len(vals)} vs recorded n {rec.get('n')!r}")
        mean = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))
        if not _close(mean, _num(rec.get("mean"), f"{arm} mean")) or not _close(sd, _num(rec.get("sd"), f"{arm} sd")):
            _fail(f"arm {arm}: recomputed mean/sd differ from ANALYSIS")
        arms[arm] = {"mean": mean, "sd": sd, "n": len(vals), "values": vals, "threads": thread_of[arm],
                     "ci95": rec.get("ci95"), "cv_pct": rec.get("cv_pct")}
    vs = ana.get("vs_control") or {}
    if set(vs) != set(arms) - {control}:
        _fail("vs_control does not cover exactly the non-control arms")
    for arm, eff in vs.items():
        if not _close(_num(eff.get("effect_pct"), f"{arm} effect_pct"), (arms[arm]["mean"] / arms[control]["mean"] - 1) * 100):
            _fail(f"{arm}: effect_pct does not re-derive from arm means")
        if arm not in verdicts:
            _fail(f"RESULT.txt carries no RESOLVED/UNRESOLVED line for {arm}")
    model_file = models.pop()
    return tuple([{"kind": "arm", "arm": arm, "unit": str(unit), "analysis_sha256": sealed.sums["ANALYSIS.json"],
                   "arms": arms, "control": control, "floor_pct": floor_pct, "date": fin.group(1),
                   "build_sha": build_sha, "model_file": model_file, "env": dict(next(iter(envs))), "vs": vs,
                   "verdicts": verdicts, "n_launches": len(ana["launches"])} for arm in arms] +
                 [{"kind": "effect", "arm": arm, "unit": str(unit), "analysis_sha256": sealed.sums["ANALYSIS.json"],
                   "arms": arms, "control": control, "floor_pct": floor_pct, "date": fin.group(1),
                   "build_sha": build_sha, "model_file": model_file, "env": dict(next(iter(envs))), "vs": vs,
                   "verdicts": verdicts, "n_launches": len(ana["launches"])} for arm in vs])


def _applicability(n: dict, arm: str) -> dict[str, Any]:
    app: dict[str, Any] = {"model_file": n["model_file"], "backend": "cpu", "build_sha": n["build_sha"],
                           "threads": n["arms"][arm]["threads"], "scope_basis": "native",
                           "knobs": {k: v for k, v in n["env"].items()}, "varied": ["threads"]}
    q = re.search(r"-(UD-[A-Z0-9_]+|Q\d\w*|IQ\d\w*)-\d{5}-of-", n["model_file"])
    if q:
        app["quant"] = q.group(1)
    return app


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    arm, ctl = native["arm"], native["control"]
    a = native["arms"][arm]
    base = dict(
        date=native["date"], protocol_id="", reps=a["n"], attestation_path=f"{native['unit']}/ANALYSIS.json",
        attestation_sha256=native["analysis_sha256"], attestation_locator="inf66-r2364:ANALYSIS.json",
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability=_applicability(native, arm))
    floor = native["floor_pct"]
    common = {"launch_unit_floor_sd_pct": floor, "unit": "launch", "n_launches_total": native["n_launches"]}
    if native["kind"] == "arm":
        return ClaimTuple(
            measurement_id=f"inf66-r2364:{arm}:decode_tps_mean", metric=f"decode_tokens_per_s_mean_{arm}",
            value=a["mean"], category="BASELINE" if arm == ctl else "CANDIDATE",
            claim=(f"INF-66 R23-64: mean decode throughput at -t {a['threads']} over {a['n']} launches is "
                   f"{a['mean']:.3f} t/s (sd {a['sd']:.3f}, CV {a['cv_pct']:.2f}%); launch-unit floor sd {floor}%."),
            metric_direction="higher_better", reps_basis=f"scored:{a['n']} launches (unit = launch)",
            unit="tokens_per_second", observation={"noise_floor_rel": floor / 100.0},
            extra={**common, "arm": arm, "launch_tps": a["values"], "sd": a["sd"], "ci95": a["ci95"]}, **base)
    eff, v = native["vs"][arm], native["verdicts"][arm]
    ce = native["arms"][ctl]
    return ClaimTuple(
        measurement_id=f"inf66-r2364:{arm}:vs_{ctl}:effect_pct", metric=f"decode_tps_effect_pct_{arm}_vs_{ctl}",
        value=eff["effect_pct"], category="CANDIDATE",
        claim=(f"INF-66 R23-64: -t {a['threads']} vs -t {ce['threads']} decode throughput effect "
               f"{eff['effect_pct']:+.2f}% (bootstrap 95% CI [{eff['boot_ci95_pct'][0]:.2f}, "
               f"{eff['boot_ci95_pct'][1]:.2f}]%, {a['n']} v {ce['n']} launches); producer verdict {v['verdict']} "
               f"(carried verbatim); launch-unit floor sd {floor}%."),
        metric_direction="higher_better",
        reps_basis=f"scored:{a['n']} launches vs {ce['n']} control launches (unit = launch)", unit="percent",
        observation={"effect_rel": eff["effect_pct"] / 100.0, "noise_floor_rel": floor / 100.0,
                     "anchor_value": ce["mean"], "outcome_native": v["verdict"]},
        extra={**common, "arm": arm, "control": ctl, "verdict_native": v["verdict"], "verdict_line": v["line"],
               "mde_floor_pct": eff.get("mde_floor_pct"), "mde_observed_pct": eff.get("mde_observed_pct"),
               "ci_excludes_zero": eff.get("ci_excludes_zero"), "boot_ci95_pct": eff["boot_ci95_pct"]}, **base)


def units(path) -> list[Path]:
    p = Path(path)
    if p.is_file():
        return [p.parent] if p.name == "ANALYSIS.json" else []
    if not p.is_dir():
        return []
    if (p / "ANALYSIS.json").is_file() and (p / "SHA256SUMS").is_file():
        return [p]
    return sorted(c.parent for c in p.glob("*/ANALYSIS.json") if (c.parent / "SHA256SUMS").is_file()
                  and (c.parent / "runs").is_dir() and "r23-64" in c.parent.name)

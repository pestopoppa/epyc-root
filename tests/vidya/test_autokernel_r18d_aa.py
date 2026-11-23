"""R18-D A/A adapter: synthetic producer-boundary controls (never a real GPU run or planner canary)."""
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
from adapters import autokernel_r18d_aa as a  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402


class _Stream:
    def __init__(self, path):
        self.rows, self.prev, self.path = [], None, path

    def add(self, kind, native):
        body = {"schema": a.SCHEMA, "run_id": "r1", "seq": len(self.rows), "kind": kind,
                "recorded_at_utc": "2026-11-08T01:13:00+00:00", "recorded_monotonic_s": 1.0,
                "previous_sha256": self.prev, "native": native}
        body["content_sha256"] = hashlib.sha256(a._canonical(body)).hexdigest()
        self.prev = body["content_sha256"]
        self.rows.append(body)

    def write(self):
        self.path.write_bytes(b"".join(a._canonical(r) + b"\n" for r in self.rows))
        return self.path


_POLICY = {"schema": "epyc.autokernel.gpu_clock_policy.v1", "mode": "request_phase_band",
           "pinned_level": "high", "nominal_sclk_mhz": 1700, "droop_band_mhz": 120,
           "min_request_samples": 8, "max_sample_gap_s": 1.0, "ratification": "test"}


def _trace(dip=None, level="high"):
    """Epoch trace 0..4.75 s at 0.25 s ticks; request phase 1..4.5 s; optional dip to `dip` MHz."""
    t_ms = [i * 250 for i in range(20)]
    mhz = [1650] * 20
    if dip:
        mhz[8] = dip
    return {"t0": 1000.0, "t_ms": t_ms, "mhz": mhz, "level_changes": [[0, level]]}


def fixture(root, *, unstable=False, marker=True, partial=False, missing_dso=False, no_trace=False,
            dip=None, level="high", pairs=None, reps=None):
    n = a.DEFAULT_PAIRS if pairs is None else pairs
    ctx = {"prospective_capture": a.MARKER if marker else None,
           "identities": {"files": [{"path": "/model", "sha256": "a" * 64, "ino": 1},
                                    {"path": "/bin/llama-bench", "sha256": "b" * 64, "ino": 2},
                                    {"path": "/bin/libggml-hip.so", "sha256": "c" * 64, "ino": 3}],
                          "grant": {"FILLER_ID": "s", "FILLER_END": "1", "FILLER_CPUS": "1", "FILLER_THREADS": "1"}},
           "model": "/model", "model_pregrant_identity": {"sha256": "a" * 64},
           "workload": {"pp": 512, "tg": 0}, "surface": "pp512", "quant": "Q8_0", "backend": "gpu"}
    if pairs is not None:
        ctx["pairs_per_condition"] = pairs
    if reps is not None:
        ctx["reps_per_invocation"] = reps
    s = _Stream(Path(root) / "r18d-capture-r1.jsonl")
    s.add("run_start", ctx)
    s.add("claim", {"owner": {"start_ticks": 1}})
    for cond, warm in a.CONDITIONS:
        for i in range((n + warm) * 2):
            phase = "warmup" if i < warm * 2 else "scored"
            sample = {"binary_match": True, "mapping": {"status": "matched"}, "vram_bytes": 2 << 30,
                      "monotonic_s": 1.5,
                      "mapped_dso_identities": [] if missing_dso else
                      [{"path": "/bin/libggml-hip.so", "sha256": "c" * 64, "inode_match": True}]}
            s.add("invocation", {"condition": cond, "phase": phase,
                                 "pair_index": i // 2 + 1 if phase == "warmup" else (i - warm * 2) // 2 + 1,
                                 "arm": "anchor" if i % 2 == 0 else "candidate", "returncode": 0, "error": None,
                                 "started_monotonic_s": 1, "ended_monotonic_s": 2, "pid": 1,
                                 "residency": {"clock_stable": not unstable, **({} if no_trace else {
                                                   "clock_trace": _trace(dip, level), "window_start": 1000.0,
                                                   "window_end": 1005.0, "request_start": 1001.0,
                                                   "request_end": 1004.5}),
                                               "own_process": {"verified": True, "pid": 1,
                                                               "joint_samples": [sample, sample]}},
                                 "argv": ["/bin/llama-bench"], "stdout": "synthetic"})
        s.add("condition", {"condition": cond, "native_result": {"anchor_samples": [100.0] * n,
                                                                  "candidate_samples": [100.0] * n}})
    floors = {str(k): 0.0 for k in (1, 3, 5, 9, 20)}
    s.add("run_end", {"disposition": "partial" if partial else "complete",
                      "outcome": {"bootstrap_floor_pct": floors}})
    return s.write()


@pytest.fixture(autouse=True)
def fake_policy(tmp_path_factory):
    """The real research clock_policy module, loaded from a temp tree with the ratified band values."""
    import subprocess
    root = tmp_path_factory.mktemp("research")
    loop = root / "scripts" / "kernel_rnd" / "autokernel" / "loop"
    loop.mkdir(parents=True)
    (loop.parent / "__init__.py").write_text("")
    (loop / "__init__.py").write_text("")
    research = os.environ.get("AUTOKERNEL_R18D_RESEARCH", "/workspace/repos/epyc-inference-research")
    rel = "scripts/kernel_rnd/autokernel/loop/clock_policy.py"
    res = subprocess.run(["git", "-C", research, "show", f"origin/main:{rel}"], capture_output=True, text=True)
    if res.returncode != 0 or not res.stdout:
        p = Path(research) / rel
        if not p.is_file():
            pytest.skip(f"research clock_policy.py not resolvable at {research} (set AUTOKERNEL_R18D_RESEARCH)")
        src = p.read_text()
    else:
        src = res.stdout
    (loop / "clock_policy.py").write_text(src)
    (loop / "gpu_clock_policy.json").write_text(json.dumps(_POLICY))
    for m in [m for m in sys.modules if m.startswith("autokernel")]:
        del sys.modules[m]
    with patch.object(a, "_RESEARCH", (str(root),)), patch.object(sys, "path", list(sys.path)):
        yield
    for m in [m for m in sys.modules if m.startswith("autokernel")]:
        del sys.modules[m]


@pytest.fixture(autouse=True)
def fake_bench():
    bench = SimpleNamespace(hardened_row=lambda *x, **k: SimpleNamespace(avg_ts=100),
                            bootstrap_floor=lambda x, y: {k: 0.0 for k in (1, 3, 5, 9, 20)})
    with patch.object(a, "_bench", return_value=bench):
        yield


def test_positive_projects_through_shared_ladder(tmp_path):
    p = fixture(tmp_path)
    (row,) = a.native_rows(p)
    t = a.project(row)
    assert t.observation["n_pairs"] == 20 and t.applicability["backend"] == "gpu" and t.source_class == "measurement"
    assert grade(t)


def test_in_band_dip_passes_and_clock_stable_flag_is_not_consulted(tmp_path):
    (row,) = a.native_rows(fixture(tmp_path, unstable=True, dip=1600))
    assert a.project(row).observation["n_pairs"] == 20


@pytest.mark.parametrize("mut", [{"no_trace": True}, {"dip": 1500}, {"level": "auto"}])
def test_clock_band_refusals(tmp_path, mut):
    with pytest.raises(ProjectionError, match="clock"):
        a.native_rows(fixture(tmp_path, **mut))


def test_unavailable_policy_refused(tmp_path):
    with patch.object(a, "_RESEARCH", (str(tmp_path / "none"),)), pytest.raises(ProjectionError, match="clock_policy"):
        a.native_rows(fixture(tmp_path))


@pytest.mark.parametrize("mut", [{"marker": False}, {"marker": False}, {"partial": True}, {"missing_dso": True}])
def test_refusals(tmp_path, mut):
    with pytest.raises(ProjectionError):
        a.native_rows(fixture(tmp_path, **mut))


def test_tamper_refused(tmp_path):
    p = fixture(tmp_path)
    p.write_text(p.read_text().replace("synthetic", "tampered", 1))
    with pytest.raises(ProjectionError):
        a.native_rows(p)


def test_truncated_stream_refused(tmp_path):
    p = fixture(tmp_path)
    p.write_bytes(b"\n".join(p.read_bytes().splitlines()[:5]) + b"\n")
    with pytest.raises(ProjectionError):
        a.native_rows(p)


def test_registered_and_wired():
    import cli
    import ingest_sources
    src = ingest_sources.SOURCES["ak-r18d-aa"]
    assert src.module == "autokernel_r18d_aa" and "ak-r18d-aa" in cli._FILE_SOURCES


def _reseal(path, name, **ctx_extra):
    """Copy a fixture stream with run_start context fields overridden, re-chained (a validly sealed variant)."""
    rows = [json.loads(x) for x in Path(path).read_text().splitlines()]
    s = _Stream(Path(path).parent / name)
    for r in rows:
        native = dict(r["native"])
        if r["kind"] == "run_start":
            native.update(ctx_extra)
        s.add(r["kind"], native)
    return s.write()


def test_pairs_and_reps_read_from_context(tmp_path):
    """The 1.5B rows seal pairs_per_condition=24 and reps_per_invocation; N and -r are read, never hardcoded."""
    seen = []
    bench = SimpleNamespace(hardened_row=lambda *x, **k: seen.append(k["reps"]) or SimpleNamespace(avg_ts=100),
                            bootstrap_floor=lambda x, y: {k: 0.0 for k in (1, 3, 5, 9, 20)})
    row = a.native_rows(fixture(tmp_path, pairs=24, reps=45))[0]
    with patch.object(a, "_bench", return_value=bench):
        t = a.project(row)
    assert t.observation["n_pairs"] == 24 and t.reps == 24 and "at 20 pairs" in t.claim
    assert seen and set(seen) == {45}


def test_unit_count_disagreeing_with_sealed_pairs_refused(tmp_path):
    path = _reseal(fixture(tmp_path, pairs=24), "r18d-capture-n25.jsonl", pairs_per_condition=25)
    with pytest.raises(ProjectionError, match="missing/retried units"):
        a._derive(path)


@pytest.mark.parametrize("key,bad", [("pairs_per_condition", 19), ("pairs_per_condition", "24"),
                                     ("pairs_per_condition", True), ("reps_per_invocation", 0),
                                     ("reps_per_invocation", None)])
def test_malformed_declared_ints_refused(tmp_path, key, bad):
    path = _reseal(fixture(tmp_path, pairs=24), "r18d-capture-bad.jsonl", **{key: bad})
    with pytest.raises(ProjectionError, match=key + " malformed"):
        a._derive(path)

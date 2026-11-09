"""R18-D A/A adapter: synthetic producer-boundary controls (never a real GPU run or planner canary)."""
import hashlib
import json
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


def fixture(root, *, unstable=False, marker=True, partial=False, missing_dso=False):
    ctx = {"prospective_capture": a.MARKER if marker else None,
           "identities": {"files": [{"path": "/model", "sha256": "a" * 64, "ino": 1},
                                    {"path": "/bin/llama-bench", "sha256": "b" * 64, "ino": 2},
                                    {"path": "/bin/libggml-hip.so", "sha256": "c" * 64, "ino": 3}],
                          "grant": {"FILLER_ID": "s", "FILLER_END": "1", "FILLER_CPUS": "1", "FILLER_THREADS": "1"}},
           "model": "/model", "model_pregrant_identity": {"sha256": "a" * 64},
           "workload": {"pp": 512, "tg": 0}, "surface": "pp512", "quant": "Q8_0", "backend": "gpu"}
    s = _Stream(Path(root) / "r18d-capture-r1.jsonl")
    s.add("run_start", ctx)
    s.add("claim", {"owner": {"start_ticks": 1}})
    for cond, warm in a.CONDITIONS:
        for i in range((a.PAIRS + warm) * 2):
            phase = "warmup" if i < warm * 2 else "scored"
            sample = {"binary_match": True, "mapping": {"status": "matched"}, "vram_bytes": 2 << 30,
                      "monotonic_s": 1.5,
                      "mapped_dso_identities": [] if missing_dso else
                      [{"path": "/bin/libggml-hip.so", "sha256": "c" * 64, "inode_match": True}]}
            s.add("invocation", {"condition": cond, "phase": phase,
                                 "pair_index": i // 2 + 1 if phase == "warmup" else (i - warm * 2) // 2 + 1,
                                 "arm": "anchor" if i % 2 == 0 else "candidate", "returncode": 0, "error": None,
                                 "started_monotonic_s": 1, "ended_monotonic_s": 2, "pid": 1,
                                 "residency": {"clock_stable": not unstable,
                                               "own_process": {"verified": True, "pid": 1,
                                                               "joint_samples": [sample, sample]}},
                                 "argv": ["/bin/llama-bench"], "stdout": "synthetic"})
        s.add("condition", {"condition": cond, "native_result": {"anchor_samples": [100.0] * a.PAIRS,
                                                                  "candidate_samples": [100.0] * a.PAIRS}})
    floors = {str(k): 0.0 for k in (1, 3, 5, 9, 20)}
    s.add("run_end", {"disposition": "partial" if partial else "complete",
                      "outcome": {"bootstrap_floor_pct": floors}})
    return s.write()


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


@pytest.mark.parametrize("mut", [{"unstable": True}, {"marker": False}, {"partial": True}, {"missing_dso": True}])
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

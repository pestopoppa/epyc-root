"""Launch-affinity readings -> strict reader -> shared grade (VB-LAUNCH-AFFINITY-WIRE). No process is touched.

Prospective v1 records are built here with the producer's hash rule (epyc-orchestrator
``scripts/server/launch_affinity.py`` ``reading_body_sha256``: sha256 of the sorted-key, compact
JSON body without ``content_sha256``). The real pre-hook evidence is read only, when present.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import launch_affinity as reader  # noqa: E402

EVIDENCE = Path("/mnt/raid0/llm/tmp/gpu-cpu-noise-20261021")
LANE = "184-191"


def _seal(rec: dict) -> dict:
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    rec["content_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return rec


def _reading(escape: bool = True, moment: str = "post_health_pin", n: int = 196, **over) -> dict:
    tasks = [{"tid": 1000 + i, "comm": "llama-server", "cpus": LANE} for i in range(n)]
    if escape and n:
        tasks[7]["cpus"] = "0-191"
    rec = {"schema": reader.READING_SCHEMA, "producer": "epyc-orchestrator scripts/server/launch_affinity.py",
           "read_at": "2026-10-23T06:37:31.000000Z", "moment": moment, "label": "arm-a", "recipe": "q38-gpu",
           "host": "epyc", "pid": 1000, "pid_starttime_ticks": 987654,
           "exe": "/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c/bin/llama-server",
           "exe_sha256": "ab" * 32, "declared_cpus": LANE, "rocr_env_key": reader.ROCR_KEY,
           "rocr_env_readable": True, "rocr_env_value": "0", "tasks": tasks, "tasks_seen": len(tasks),
           "escapes": [t for t in tasks if t["cpus"] != LANE], "pin": None}
    rec.update(over)
    return _seal(rec)


def _write(tmp_path: Path, *recs: dict, name: str = "affinity_readings.jsonl") -> Path:
    p = tmp_path / name
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    return p


def test_v1_reading_projects_n_of_n_inside_with_pid_binary_and_moment(tmp_path):
    p = _write(tmp_path, _reading(), _reading(escape=False, moment="pre_stop"))
    natives = reader.native_rows(p)
    assert len(natives) == 2
    a, b = (reader.project(n) for n in natives)
    assert (a.value, a.reps, b.value) == (1, 196, 0)
    assert a.metric_direction == "lower_better" and a.unit == "tasks" and a.category == "BASELINE"
    assert "195/196 tasks of pid 1000" in a.claim and "1007(llama-server)=0-191" in a.claim
    assert "Covers this pid at this moment only" in a.claim and "HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0" in a.claim
    assert a.applicability["kernel"]["binary_sha256"] == "ab" * 32 and a.applicability["build_sha"] == "dd3d9721c"
    assert a.measurement_id != b.measurement_id
    assert ct.grade(a)[:2] == ("Judged", "Located") and a.attestation_verified is True
    assert "retrofit" not in a.observation


def test_unchecked_reading_projects_nothing(tmp_path):
    # a vanished pid: tasks_seen 0 is UNCHECKED, never clean
    assert reader.native_rows(_write(tmp_path, _reading(n=0, exe=None, exe_sha256=None))) == ()


@pytest.mark.parametrize("mutate,match", [
    (lambda r: r.update(tasks_seen=195), "content_sha256"),
    (lambda r: r.update(_seal(dict(r, tasks_seen=195))), "tasks_seen differs"),
    (lambda r: r.update(_seal(dict(r, escapes=[]))), "escapes do not re-derive"),
    (lambda r: r.update(_seal(dict(r, moment="whenever"))), "unknown moment"),
    (lambda r: r.update(_seal({**r, "extra_field": 1})), "field set"),
])
def test_v1_reading_that_does_not_re_derive_is_refused(tmp_path, mutate, match):
    rec = _reading()
    mutate(rec)
    with pytest.raises(ct.ProjectionError, match=match):
        reader.native_rows(_write(tmp_path, rec))


def test_narrower_omp_submask_is_not_an_escape(tmp_path):
    rec = _reading(escape=False)
    rec["tasks"][3]["cpus"] = "184-185"
    rec = _seal(dict(rec, escapes=[]))
    assert reader.project(reader.native_rows(_write(tmp_path, rec))[0]).value == 0


def _probe(tmp_path: Path, outside_line: str = "outside_184-191=0", knob: bool = True) -> Path:
    d = tmp_path / "probe-p1-x"
    d.mkdir(parents=True)
    env = "HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0 " if knob else ""
    (tmp_path / "probe-p1-x.sh").write_text(
        "#!/bin/bash\n# probe: does it stay inside `taskset -c 184-191`?\nB=/k/builds/gpu-20261020-dd3d9721c/bin\n"
        f"{env}LD_LIBRARY_PATH=$B taskset -c 184-191 numactl --membind=3 $B/llama-server -m $M &\n")
    dump = "".join(f"{500 + i} llama-server     {LANE}\n" for i in range(4))
    (d / "a_health.tasks").write_text(dump)
    (d / "SUMMARY").write_text(
        ("env: knob present in /proc/500/environ\n" if knob else "")
        + f"a_health: tasks=4 {outside_line}\nkilled 500 (verified)\nP1 PASS\n")
    return d


def test_pre_hook_probe_dump_projects_as_retrofit_without_a_binary_digest(tmp_path):
    natives = reader.native_rows(_probe(tmp_path))
    assert len(natives) == 1
    t = reader.project(natives[0])
    assert (t.value, t.reps, t.category) == (0, 4, "CANDIDATE")
    assert t.observation["retrofit"] is True and "binary sha256 not captured" in t.claim
    assert "binary_sha256" not in t.applicability["kernel"]
    assert ct.grade(t)[:2] == ("Judged", "Located")


def test_pre_hook_probe_whose_summary_does_not_re_count_is_refused(tmp_path):
    with pytest.raises(ct.ProjectionError, match="do not re-derive"):
        reader.native_rows(_probe(tmp_path, outside_line="outside_184-191=1"))


def test_units_find_readings_dumps_and_probe_dirs(tmp_path):
    _probe(tmp_path)
    _write(tmp_path, _reading())
    (tmp_path / "unrelated.jsonl").write_text("{}\n")
    found = {p.name for p in reader.units(tmp_path)}
    assert found == {"probe-p1-x", "affinity_readings.jsonl"}


@pytest.mark.skipif(not (EVIDENCE / "probe-p1-gpupin-20261023" / "SUMMARY").is_file(),
                    reason="real STACKCHG-GPUPIN evidence not on this host")
def test_real_diag_and_p1_probe_evidence(tmp_path):
    from ledger import Ledger  # noqa: PLC0415

    by_moment = {}
    for unit in reader.units(EVIDENCE):
        for native in reader.native_rows(unit):
            t = reader.project(native)
            by_moment[(Path(native["path"]).name, t.extra["moment"])] = t
    diag = by_moment[("diag-affinity-20261022.out", "post_health")]
    assert (diag.value, diag.reps, diag.category) == (1, 196, "BASELINE")      # the one ROCr thread on 0-191
    pin = by_moment[("diag-affinity-pin-20261022.out", "post_health_after_taskset_a")]
    assert (pin.value, pin.category) == (0, "CANDIDATE")
    p1 = [t for (f, _), t in by_moment.items() if f.endswith(".tasks")]
    assert len(p1) == 2 and all(t.value == 0 and t.reps == 196 for t in p1)     # P1 PASS: knob alone
    assert all("HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0" in t.claim for t in p1)
    assert len({t.measurement_id for t in by_moment.values()}) == 4
    report = ingest_sources.ingest(Ledger(tmp_path / "l.jsonl"), "launch-affinity", [EVIDENCE],
                                   as_of="2026-10-23T16:00:00Z", dry_run=True)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (4, 12, [])


def test_adapter_registers_a_projection_and_no_ladder():
    assert ct.source_classes()[reader.SOURCE_KIND] == ct.MEASUREMENT_CLASS
    assert all("launch_affinity" not in module for module, _ in ct.ladders().values())

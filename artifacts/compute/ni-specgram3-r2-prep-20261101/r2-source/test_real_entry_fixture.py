#!/usr/bin/env python3
"""Canonical v14 model-free same-entry and active-STOP conformance fixture.

All grants, manifests, receipts, and nonce state are under fixture-run/flags.
The final receipt is epyc.qual.fixture.v1; this test cannot qualify the science row.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

D = Path(__file__).resolve().parent
PARENT = D.parent
ENGINE_DIR = D / ".." / "engine-exact-fixture"
QUAL = ENGINE_DIR / "qualify_launcher.py"
TEST_ID = "codex-ni-specgram3-llg101-cpu-r2-20261101-fixture-" + secrets.token_hex(4)
ACTIVE_TEST_ID = "codex-ni-specgram3-llg101-cpu-r2-20261101-active-stop-fixture-" + secrets.token_hex(4)
PAIR = "132-133"
SCRATCH = D / ("fixture-run-" + secrets.token_hex(4))
FLAGS = SCRATCH / "flags"
MANIFEST = SCRATCH / "manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_manifest(identifier: str, production: bool) -> dict:
    manifest = {
        "schema": "epyc.ready.v2",
        "id": identifier,
        "owner": "codex-ni",
        "production": production,
        "workload_kind": "command",
        "regions": PAIR,
        "claimed_cpus": "dynamic",
        "window_s": 21600,
        "min_window_s": 1200,
        "gib": 8,
        "scratch_root": str(SCRATCH),
        "launcher": {"path": str(D / "launch.sh"), "sha256": sha(D / "launch.sh")},
        "engine": {"path": str(ENGINE_DIR / "filler_run14.sh"),
                   "sha256": sha(ENGINE_DIR / "filler_run14.sh")},
        "job": {"path": str(D / "job_entry.sh"), "sha256": sha(D / "job_entry.sh")},
        "qual_fixture": {"path": str(D / "qual_fixture.py"),
                         "sha256": sha(D / "qual_fixture.py"), "items": 2},
        "source_manifest": str(D / "SOURCES.fixture.sha256"),
        "request_manifest_sha256": hashlib.sha256((D / "PREDECLARATION.md").read_bytes()).hexdigest(),
        "requires_tools": ["/usr/bin/python3", "/usr/bin/taskset"],
        "qual_interpreter": "/usr/bin/python3.13",
        "ports": [],
        "shared_state": [],
        "exclusive_class": None,
        "items": 1,
        "est_output_GiB": 0.01,
        "job_floor_gib": 150,
        "qual_timeout_s": 300,
        "command": {"work_unit": "model-free-first-compute", "planned_work_units": 1},
        "rate_basis": {"scope": "command-same-recipe", "production_threads": 2},
        "qualification": {"receipt": str(SCRATCH / "qualification" / f"QUAL-{identifier}.json")},
    }
    if production:
        recipe = D / "PREDECLARATION.md"
        manifest["production_recipe"] = {"path": str(recipe), "sha256": sha(recipe)}
    return manifest


def write_fixture_row(identifier: str, manifest: dict) -> None:
    FLAGS.mkdir(parents=True, exist_ok=True)
    notes = (f"requested_window_s={manifest['window_s']}; claimed_cpus=dynamic; "
             f"est_output_GiB={manifest['est_output_GiB']}; scratch_root={manifest['scratch_root']}; "
             f"process_limit_GiB=8; launcher_path={manifest['launcher']['path']}; "
             f"job_path={manifest['job']['path']}; source_manifest={manifest['source_manifest']}")
    cells = [identifier, "codex-ni", manifest["launcher"]["path"], manifest["regions"],
             "60 s", "8", str(SCRATCH / "STOP"), "BACKLOG", "block-correctness",
             "21600 s", "1200 s", "n", "y", str(SCRATCH / "RESULT.json"),
             "model-free v14 execution plumbing fixture only", "n/a (non-science fixture)",
             "cpu", notes]
    (FLAGS / "FILLERS.md").write_text("| " + " | ".join(cells) + " |\n")
    allow = {"kind": "epyc.engine-allowlist.v1",
             "engine": {"path": str(ENGINE_DIR / "filler_run14.sh"),
                        "sha256": sha(ENGINE_DIR / "filler_run14.sh")}}
    (FLAGS / "engine-allowlist.json").write_text(json.dumps(allow, sort_keys=True, indent=2) + "\n")


def run_nonproduction_qualification() -> dict:
    m = base_manifest(TEST_ID, False)
    write_fixture_row(TEST_ID, m)
    MANIFEST.write_text(json.dumps(m, sort_keys=True, indent=2) + "\n")
    env = os.environ.copy()
    env.update({"FILLER_FLAGS_DIR": str(FLAGS), "WS58_QUAL_CPUS": PAIR,
                "WS58_QUAL_GPU_HELD": "0", "WS58_QUALIFIER_PATH": str(QUAL), "WS58_MANIFEST_PATH": str(MANIFEST), "OMP_NUM_THREADS": "1"})
    issue = subprocess.run(["/usr/bin/python3", "-I", str(QUAL), "issue",
                            "--manifest", str(MANIFEST), "--flags", str(FLAGS)],
                           env=env, text=True, capture_output=True, check=True)
    nonce = issue.stdout.strip()
    assert len(nonce) == 64 and all(c in "0123456789abcdef" for c in nonce)
    run = subprocess.run(["/usr/bin/python3", "-I", str(QUAL), "run",
                          "--manifest", str(MANIFEST), "--flags", str(FLAGS),
                          "--nonce", nonce, "--timeout", "300"],
                         env=env, text=True, capture_output=True, timeout=310)
    (SCRATCH / "nonproduction-run.stdout").write_text(run.stdout)
    (SCRATCH / "nonproduction-run.stderr").write_text(run.stderr)
    if run.returncode:
        raise RuntimeError(f"nonproduction canonical qualification rc={run.returncode}: {run.stderr[-1000:]}")
    receipt = json.loads(Path(m["qualification"]["receipt"]).read_text())
    assert receipt["kind"] == "epyc.qual.fixture.v1"
    assert receipt["rc75"]["exit_code"] == 75 and receipt["children_drained"] is True
    assert receipt["result_writer"]["ok"] is True and receipt["completion"]["is_complete_rc"] == 0
    return {"kind": receipt["kind"], "nonce": nonce, "receipt": m["qualification"]["receipt"],
            "result_writer": receipt["result_writer"], "rc75": receipt["rc75"],
            "children_drained": receipt["children_drained"]}


def env_for(manifest: dict, nonce: str, phase: str, qdir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "WS58_QUAL": "1", "WS58_QUAL_NONCE": nonce,
        "WS58_QUAL_CPUS": PAIR, "WS58_REGIONS": PAIR,
        "WS58_QUAL_RESULTS": str(qdir / "results"),
        "WS58_QUAL_FIXTURE": str(D / "qual_fixture.py"),
        "WS58_QUAL_PRODUCTION": str(int(bool(manifest["production"]))), "WS58_QUAL_ACTIVE_STOP": "1" if phase == "cutoff" else "0",
        "WS58_QUAL_WINDOW_S": str(manifest["window_s"]),
        "WS58_MANIFEST_PATH": str(MANIFEST),
        "WS58_QUALIFIER_PATH": str(QUAL),
        "WS58_QUAL_CUTOFF_EVENT": str(qdir / "cutoff-event.json"),
        "FILLER_FLAGS_DIR": str(FLAGS), "FILLER_GRANTS_DIR": str(qdir / "grants"),
        "FILLER_STATE_DIR": str(qdir / "state"), "FILLER_CPUS": PAIR,
        "FILLER_THREADS": "2", "FILLER_ID": manifest["id"],
        "FILLER_QUAL_PHASE": phase, "FILLER_QUAL_FIXTURE": str(D / "qual_fixture.py"),
        "FILLER_RESULTS_DIR": str(qdir / "results"),
        "WS58_QUAL_PROOF": str(qdir / f"proof-{phase}.json"),
        "FILLER_STOPFILE": str(qdir / "cutoff.stop"),
        "FILLER_PIDFILE": str(qdir / "state" / f"{manifest['id']}.pids"),
        "FILLER_END": str(int(time.time()) + 500),
        "FILLER_DEADLINE": str(int(time.time()) + 400),
        "OMP_NUM_THREADS": "1",
    })
    (qdir / "results").mkdir(parents=True, exist_ok=True)
    (qdir / "grants").mkdir(parents=True, exist_ok=True)
    (qdir / "state").mkdir(parents=True, exist_ok=True)
    return env


def run_active_stop_fixture() -> dict:
    nonce = secrets.token_hex(32)
    m = base_manifest(ACTIVE_TEST_ID, False)
    m["qualification"]["receipt"] = str(SCRATCH / "qualification" / f"QUAL-{ACTIVE_TEST_ID}.json")
    MANIFEST.write_text(json.dumps(m, sort_keys=True, indent=2) + "\n")
    qdir = FLAGS / "qual" / nonce
    qdir.mkdir(parents=True)
    write_fixture_row(ACTIVE_TEST_ID, m)

    normal_env = env_for(m, nonce, "normal", qdir)
    normal = subprocess.run(["/usr/bin/taskset", "-c", PAIR, "/bin/bash", str(D / "launch.sh"), "--job"],
                            cwd=D, env=normal_env, text=True, capture_output=True, timeout=30)
    if normal.returncode != 0:
        raise RuntimeError(f"normal same-entry rc={normal.returncode}: {normal.stderr[-1000:]}")
    complete = subprocess.run(["/bin/bash", str(D / "complete.sh")], cwd=D,
                              env=normal_env, text=True, capture_output=True, timeout=10)
    if complete.returncode != 0:
        raise RuntimeError(f"completion predicate refused normal result: {complete.stderr}")
    normal_result = qdir / "results" / "QUAL-RESULT.json"
    normal_result_sha = sha(normal_result)

    cutoff_env = env_for(m, nonce, "cutoff", qdir)
    cutoff_env["FILLER_DEADLINE"] = str(int(time.time()) + 400)
    proc = subprocess.Popen(["/usr/bin/taskset", "-c", PAIR, "/bin/bash", str(D / "launch.sh"), "--job"],
                            cwd=D, env=cutoff_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, close_fds=True)
    event_path = qdir / "cutoff-event.json"
    limit = time.monotonic() + 20
    while not event_path.exists() and time.monotonic() < limit:
        if proc.poll() is not None:
            raise RuntimeError("cutoff job exited before its first-compute event")
        time.sleep(0.01)
    if not event_path.exists():
        proc.terminate(); proc.wait(timeout=5)
        raise RuntimeError("active cutoff event timed out")
    (qdir / "cutoff.stop").touch()
    output, _ = proc.communicate(timeout=10)
    assert proc.returncode == 75, (proc.returncode, output)
    proof = json.loads((qdir / "proof-cutoff.json").read_text())
    event = json.loads(event_path.read_text())
    partial = json.loads((qdir / "results" / "PARTIAL.json").read_text())
    assert sha(normal_result) == normal_result_sha, "cutoff overwrote the normal result writer"
    assert proof["partial"] is True and proof["unknown_disposition"] == "UNKNOWN"
    assert proof["stop_observed"] is True and proof["children_drained"] is True
    assert event["native_first_event"] is True
    assert event["native_pid"] != proc.pid and partial["unknown_disposition"] == "UNKNOWN"
    event_sha = sha(event_path)
    try:
        birth = int(Path(f"/proc/{event['native_pid']}/stat").read_text().rsplit(") ", 1)[1].split()[19])
    except (OSError, ValueError, IndexError):
        birth = None
    assert birth != event["native_birth_ticks"]

    # This is a direct nonproduction fixture only; canonical production trigger-cutoff
    # remains inaccessible until the real same-job science entry exists.
    return {"job_rc": proc.returncode, "partial_unknown": True,
            "normal_result_preserved": True,
            "first_event_pid": event["native_pid"], "first_event_birth_ticks": event["native_birth_ticks"],
            "event_sha256": event_sha, "child_drained": True,
            "official_nonce_issued": False, "hard_qualification": False}


def run_production_toy_refusal() -> dict:
    cases = []
    for label, production_value in (("true", True), ("missing", None), ("string_false", "false")):
        identifier = "codex-ni-specgram3-llg101-cpu-r2-invalid-production-" + label + "-" + secrets.token_hex(3)
        m = base_manifest(identifier, False)
        if production_value is None:
            m.pop("production", None)
        else:
            m["production"] = production_value
        write_fixture_row(m["id"], m)
        MANIFEST.write_text(json.dumps(m, sort_keys=True, indent=2) + "\n")
        env = os.environ.copy()
        env.update({"WS58_QUAL": "1", "WS58_MANIFEST_PATH": str(MANIFEST),
                    "FILLER_QUAL_PHASE": "normal", "FILLER_QUAL_FIXTURE": str(D / "qual_fixture.py")})
        run = subprocess.run(["/bin/bash", str(D / "job_entry.sh")], cwd=D, env=env,
                             text=True, capture_output=True, timeout=10)
        assert run.returncode == 70, (label, run.returncode, run.stderr)
        expected = ("production qualification cannot use the model-free command fixture"
                    if production_value is True else "requires an explicit JSON boolean false")
        assert expected in run.stderr, (label, run.stderr)
        direct_env = env | {"WS58_QUAL_NONCE": "a" * 64, "FILLER_ID": m["id"],
                            "FILLER_RESULTS_DIR": str(SCRATCH / ("direct-results-" + label)),
                            "WS58_QUAL_PROOF": str(SCRATCH / ("direct-proof-" + label + ".json")),
                            "FILLER_FLAGS_DIR": str(FLAGS), "FILLER_STOPFILE": str(SCRATCH / ("STOP-" + label)),
                            "FILLER_QUAL_FIXTURE": str(D / "qual_fixture.py")}
        direct = subprocess.run(["/usr/bin/python3", "-I", "-B", str(D / "qual_fixture.py")],
                                cwd=D, env=direct_env, text=True, capture_output=True, timeout=10)
        assert direct.returncode != 0 and "requires explicit production=false" in direct.stderr
        cases.append({"case": label, "job_entry_rc": run.returncode,
                      "direct_fixture_refused": True, "no_science_work_started": True})
    return {"cases": cases, "refusal": "only an explicit JSON boolean production=false enables the toy fixture"}


def main() -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    result = {"model_free_engine_fixture": run_nonproduction_qualification(),
              "nonproduction_active_stop_fixture": run_active_stop_fixture(),
              "production_toy_entry_refusal": run_production_toy_refusal(),
              "interpretation": "model-free mechanics only; no production qualification, keeper HARD receipt, or science result"}
    path = SCRATCH / "FIXTURE-RESULT.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return result


def test_all() -> None:
    result = main()
    assert result["model_free_engine_fixture"]["kind"] == "epyc.qual.fixture.v1"
    assert result["nonproduction_active_stop_fixture"]["partial_unknown"] is True
    assert result["nonproduction_active_stop_fixture"]["normal_result_preserved"] is True
    cases = result["production_toy_entry_refusal"]["cases"]
    assert len(cases) == 3 and all(c["direct_fixture_refused"] and c["no_science_work_started"] for c in cases)


if __name__ == "__main__":
    main()

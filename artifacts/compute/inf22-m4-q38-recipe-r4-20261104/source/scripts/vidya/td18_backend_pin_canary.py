#!/usr/bin/env python3
"""Synthetic APP producer -> existing registry -> isolated planning-context canary."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claim_tuple  # noqa: E402
import ingest_sources  # noqa: E402
import loop_beliefs  # noqa: E402
from ledger import Ledger  # noqa: E402

APP_COMMIT = "a68318e39581e7f4a0730da264657eab726b4d4e"


class Sync:
    def status(self, *args, **kwargs):
        return {
            "fresh": True,
            "lag_entries": 0,
            "index_max_id": 1,
            "synced_max_id": 1,
            "last_sync": datetime.now(timezone.utc).isoformat(),
        }

    def sync(self, *args, **kwargs):
        raise AssertionError("unexpected sync")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--app-root", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    app = Path(args.app_root).resolve(strict=True)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    # Exact implementing APP source bytes, even if its worktree is now at proof commit.
    for name in (
        "src/typed_decisions/measure.py",
        "src/typed_decisions/decision_backend_pin.py",
        "tests/unit/fake_decision_server.c",
    ):
        source = subprocess.check_output(
            ["git", "show", f"{APP_COMMIT}:{name}"], cwd=app
        )
        if source != (app / name).read_bytes():
            raise RuntimeError("APP source differs: " + name)

    def string(value):
        raw = value.encode()
        return struct.pack("<Q", len(raw)) + raw

    model = out / "synthetic-canary.gguf"
    model.write_bytes(
        b"GGUF"
        + struct.pack("<IQQ", 3, 0, 3)
        + string("general.architecture")
        + struct.pack("<I", 8)
        + string("lfm3")
        + string("lfm3.decision.temperature.choice")
        + struct.pack("<If", 6, 2.0)
        + string("other.decision.temperature.noul")
        + struct.pack("<If", 6, 3.0)
    )
    server = out / "fake-server"
    subprocess.run(
        ["cc", str(app / "tests/unit/fake_decision_server.c"), "-o", str(server)],
        check=True,
    )
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    child = subprocess.Popen(
        [
            str(server),
            "-m",
            str(model),
            "--port",
            str(port),
            "-np",
            "1",
            "-b",
            "32",
            "-ub",
            "16",
        ]
    )
    try:
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    pass
                break
            except OSError:
                time.sleep(0.01)
        else:
            raise RuntimeError("fake listener not ready")
        for name, data in [
            ("state.json", "synthetic state"),
            (
                "questions.json",
                [
                    {
                        "id": "cal-0",
                        "kind": "choice",
                        "text": "Pick.",
                        "options": ["a", "b"],
                    }
                ],
            ),
            ("labels.json", {"cal-0": "a"}),
        ]:
            (out / name).write_text(json.dumps(data))
        receipt = out / "native-receipt.json"
        env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            OMP_NUM_THREADS="1",
            ORCHESTRATOR_MOCK_MODE="1",
            ORCHESTRATOR_PROGRESS_LOG_DIR=str(out / "progress"),
        )
        command = [
            sys.executable,
            "-m",
            "src.typed_decisions.measure",
            "calibration",
            "--live",
            "--role",
            "worker",
            "--state-file",
            str(out / "state.json"),
            "--questions-file",
            str(out / "questions.json"),
            "--labels-file",
            str(out / "labels.json"),
            "--receipt",
            str(receipt),
            "--decision-backend-pid",
            str(child.pid),
            "--decision-backend-url",
            f"http://127.0.0.1:{port}",
            "--decision-model-path",
            str(model),
        ]
        result = subprocess.run(
            command, cwd=app, env=env, capture_output=True, text=True, timeout=90
        )
        (out / "app.stdout").write_text(result.stdout)
        (out / "app.stderr").write_text(result.stderr)
        if result.returncode:
            raise RuntimeError("APP producer failed")
    finally:
        child.terminate()
        child.wait(timeout=5)
        if child.poll() is None:
            raise RuntimeError("fake server survived")
    # Producer's original JSON is consumed after the originating PID is dead.
    original = json.loads(receipt.read_text())
    pin = original["decision_backend_pin"]
    if (
        pin["gguf_sha256"] != sha(model)
        or pin["decision_temperatures"]["other.decision.temperature.noul"] != 3.0
    ):
        raise RuntimeError("APP receipt did not carry expected pin")
    module = ingest_sources.SOURCES["typed-decisions-measurement"].load()
    rows = module.native_rows(receipt)
    claims = [module.project(row) for row in rows]
    if len(claims) != 2 or any(
        c.extra.get("decision_backend_pin") != pin
        or c.applicability.get("model_sha256") != sha(model)
        or claim_tuple.grade(c)[:2] != ("Judged", "Located")
        for c in claims
    ):
        raise RuntimeError("projection mismatch")
    ledger = out / "private-ledger.jsonl"
    asof = datetime.now(timezone.utc).isoformat()
    report = ingest_sources.ingest(
        Ledger(ledger), "typed-decisions-measurement", [receipt], as_of=asof
    )
    if report["rows_projected"] != 2 or report["refused"]:
        raise RuntimeError("registry ingest failed")
    cfg = out / "alarm.yaml"
    cfg.write_text("backend: file\nfile:\n  path: " + str(out / "alarm.jsonl") + "\n")

    def plan(model_file, model_sha, suffix):
        return loop_beliefs.prepare(
            "test.td18",
            {"backend": "cpu", "model_file": model_file, "model_sha256": model_sha},
            ledger=ledger,
            index_path=out / "index.yaml",
            as_of=asof,
            sync_module=Sync(),
            known_good=out / ("known-" + suffix + ".json"),
            alarm_state=out / ("alarm-" + suffix + ".json"),
            alarm_config=cfg,
            read_log=out / ("reads-" + suffix + ".jsonl"),
        )

    answer = plan(model.name, sha(model), "matched")
    other = plan("unrelated.gguf", "f" * 64, "other")
    collision = plan(model.name, "f" * 64, "collision")
    visible = [
        c
        for c in answer.get("evidence", {}).get("claims", [])
        if c.get("source_kind") == "typed-decisions-measurement"
    ]
    wrong = [
        c
        for c in other.get("evidence", {}).get("claims", [])
        if c.get("source_kind") == "typed-decisions-measurement"
    ]
    collision_claims = [
        c
        for c in collision.get("evidence", {}).get("claims", [])
        if c.get("source_kind") == "typed-decisions-measurement"
    ]
    if answer["status"] != "ready" or len(visible) != 2 or wrong or collision_claims:
        raise RuntimeError("planning applicability mismatch")
    frames = [json.loads(line)["frame"] for line in ledger.read_text().splitlines()]
    sources = [frame["assertion"] for frame in frames if frame["frame_type"].endswith("/source_observed/v1")]
    temperature_bytes = json.dumps(pin["decision_temperatures"], sort_keys=True,
                                   ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()
    expected_knobs = {"server_argv_np": pin["server_argv_flags"]["np"],
                      "server_argv_batch": pin["server_argv_flags"]["batch"],
                      "server_argv_ubatch": pin["server_argv_flags"]["ubatch"],
                      "decision_temperatures_json_sha256": hashlib.sha256(temperature_bytes).hexdigest(),
                      "transport_method": pin["transport_method"],
                      "source_receipt_sha256": sha(receipt)}
    if any(claim.get("knobs") != expected_knobs for claim in visible):
        raise RuntimeError("planning context omitted recorded configuration")
    if len(sources) != 2 or any(source["locator"] != "typed-decisions-receipt:" + str(receipt)
        or source["applicability"]["build_sha"] != pin["server_build_commit"]
        or source["applicability"]["model_sha256"] != sha(model)
        or source["applicability"]["knobs"] != expected_knobs for source in sources):
        raise RuntimeError("source frame custody or configuration mismatch")
    ledger_bytes = ledger.read_bytes()
    if (
        pin["gguf_sha256"].encode() not in ledger_bytes
        or str(receipt).encode() not in ledger_bytes
    ):
        raise RuntimeError(
            "model scope or original receipt locator missing from ledger"
        )
    (out / "canary.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "app_commit": APP_COMMIT,
                "receipt_sha256": sha(receipt),
                "projected": len(claims),
                "matched_claims": len(visible),
                "unrelated_claims": len(wrong),
                "same_name_wrong_digest_claims": len(collision_claims),
                "server_stopped_before_projection": True,
                "pin_storage": "ClaimTuple.extra and producer receipt; source frame carries model/build, requested flags, temperature digest, transport and receipt locator/digest",
                "grading": "shared ClaimTuple.grade",
                "report": report,
            },
            indent=2,
            default=str,
        )
        + "\n"
    )
    print((out / "canary.json").read_text())


if __name__ == "__main__":
    main()

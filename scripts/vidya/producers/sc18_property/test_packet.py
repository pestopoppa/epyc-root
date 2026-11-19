#!/usr/bin/env python3
"""Exercise staged parse, journal, CLI and terminal checks without invoking the native binary."""

from pathlib import Path
import json
import runpy
import sys
import tempfile


def check_fixture(packet, rc, residual, terminal, detail):
    r = runpy.run_path(str(packet / "run_property.py"))
    passed = 1 - rc
    stdout = f"""Testing 1 devices
Backend 1/1: CPU
  SOFT_MAX({r['PARAMS']}): AK_PROP_V2 metric=softmax_invariants/v1 residual={residual} tolerance=0.0001 passed={passed} suite_seed=4711 transform=identity {detail}{terminal}
  {passed}/1 tests passed
  Backend CPU: {terminal}
{passed}/1 backends passed
{terminal}
""".encode()
    self_test = (b"AUTOKERNEL_PROPERTY_SELF_TEST suite_seed=4711 sensitivity=1.000 "
                 b"specificity=1.000 planted=5 clean=5\n")
    with tempfile.TemporaryDirectory() as temporary:
        out = Path(temporary)
        request = {"created_at": "2026-11-18T09:30:00Z", "campaign": "ak-synthetic-sc18-control",
                   "purpose": "publisher_smoke", "argv": r["ARGV"], "environment": r["ENV"],
                   "seed": r["SEED"]}
        for name in ("request.json", "host.json", "grant.txt"):
            r["write_json"](out / name, request)
        (out / "stdout.log").write_bytes(stdout)
        (out / "stderr.log").write_bytes(self_test)
        r["write_json"](out / "native.json", {"exit": rc,
            "request_sha256": r["sha"](out / "request.json"),
            "raw_sha256": {name: r["sha"](out / name) for name in ("stdout.log", "stderr.log")}})
        gate = r["gate_from_output"](stdout, self_test, rc, r["reference"](out / "native.json"))
        assert gate["measurements"][0]["passed"] == (rc == 0)
        manifests, _ = r["input_check"]()
        event = r["make_event"](out, request, manifests, gate)
        entry = r["append_event"](out, event)
        first, retry = (r["ingest"](out, request["created_at"], "write") for _ in range(2))
        r["assert_ingest"](first, 3)
        r["assert_ingest"](retry, 0)
        r["write_json"](out / "ingest.json", {"first": first, "retry": retry})
        r["write_json"](out / "RESULT.json", r["result_for"](out, request, entry, gate))
        r["validate_capture"](out)
        with (out / "stdout.log").open("ab") as stream:
            stream.write(b"tampered\n")
        try:
            r["validate_capture"](out)
        except ValueError as error:
            assert "changed native logs" in str(error), str(error)
        else:
            raise AssertionError("tampered logs accepted")
        print(f"synthetic {terminal} fixture passed")


def run_fixtures(packet_path):
    check_fixture(packet_path, 0, "2.5e-08", "OK", "")
    check_fixture(packet_path, 1, "0.01", "FAIL", "| native property failure ")


def test_all():
    import pytest

    spec = json.loads(Path(__file__).with_name("spec.json").read_text())
    packet = Path(spec["scratch_root"])
    if not (packet / "PINNED.sha256").is_file():
        pytest.skip("the host-specific SC18 packet has not been staged")
    run_fixtures(packet)


if __name__ == "__main__":
    run_fixtures(Path(sys.argv[1]))

"""Exercise actual once/loop consumers, not a mirrored predicate."""

from pathlib import Path
import json
import pytest
from hub_supervisor_contract import Fixture, listener, unused_port, battery

SCRIPT = Path(__file__).parents[1] / "scripts/dashboard/hub_supervisor.sh"


def test_actual_http_observation_contract(tmp_path):
    assert battery(SCRIPT, tmp_path) == []


@pytest.mark.parametrize("mode", ["once", "loop"])
@pytest.mark.parametrize(
    "failure", ["timeout", "missing_tool", "wrong_port", "missing_manifest"]
)
def test_unknown_never_launches_and_alarms(tmp_path, mode, failure):
    f = Fixture(SCRIPT, tmp_path, unused_port())
    if failure == "timeout":
        f.curl_rc(28)
    elif failure == "missing_tool":
        f.without_curl()
    elif failure == "wrong_port":
        f.entry["port"] += 1
        f.write_manifest()
    else:
        f.manifest.unlink()
    if mode == "once":
        result = f.run("once")
        assert result.returncode == 3, result.stderr
    else:
        f.loop_until("OBSERVER-BLIND")
    assert not f.marker.exists()
    alarm = json.loads(next((tmp_path / "alerts").glob("*.json")).read_text())
    assert alarm["state"] == "unobservable"


def test_timeout_with_live_listener_is_identity_present_but_not_restart_authority(
    tmp_path,
):
    with listener() as port:
        f = Fixture(SCRIPT, tmp_path, port)
        f.curl_rc(28)
        result = f.run("observe")
        assert result.returncode == 0 and "state=present" in result.stdout
        result = f.run("once")
        assert result.returncode == 3, result.stderr
        assert not f.marker.exists()


def test_confirmed_absence_reaches_real_launch_and_blind_streak_caps_retries(tmp_path):
    f = Fixture(SCRIPT, tmp_path, unused_port())
    for _ in range(3):
        result = f.run("once")
        assert f.marker.exists(), result.stderr
        f.marker.unlink()
    result = f.run("once")
    assert result.returncode == 3 and not f.marker.exists(), result.stderr
    assert "BLIND STREAK" in result.stderr


@pytest.mark.parametrize("mode", ["once", "loop"])
def test_actual_healthy_consumer_executes_stale_source_check(tmp_path, mode):
    with listener() as port:
        f = Fixture(SCRIPT, tmp_path, port)
        if mode == "once":
            result = f.run(mode)
            assert result.returncode == 0, result.stderr
            output = result.stderr
        else:
            output = f.loop_until("stale-source check UNAVAILABLE")
        assert "stale-source check UNAVAILABLE" in output
        assert not f.marker.exists()


def test_http_error_is_present_identity_and_confirmed_unhealthy(tmp_path):
    with listener(status=503) as port:
        f = Fixture(SCRIPT, tmp_path, port)
        result = f.run("observe")
        assert result.returncode == 0 and "state=present" in result.stdout
        result = f.run("once")
        assert f.marker.exists(), result.stderr
        assert "confirmed by two probes" in result.stderr


def test_status_names_unavailable_health(tmp_path):
    f = Fixture(SCRIPT, tmp_path, unused_port())
    f.curl_rc(28)
    result = f.run("status")
    assert "UNOBSERVABLE" in result.stdout
    assert not f.marker.exists()


def test_recovered_health_clears_alarm(tmp_path):
    with listener() as port:
        f = Fixture(SCRIPT, tmp_path, port)
        f.curl_rc(28)
        assert f.run("once").returncode == 3
        assert list((tmp_path / "alerts").glob("*.json"))
        (f.tools / "curl").unlink()
        result = f.run("once")
        assert result.returncode == 0, result.stderr
        assert not list((tmp_path / "alerts").glob("*.json"))
        assert not f.marker.exists()


@pytest.mark.parametrize("mode", ["once", "loop"])
@pytest.mark.parametrize(
    "body", [b'{"status":"not ok"}', b'{"status":"error","note":"ok"}']
)
def test_valid_nonok_json_is_unhealthy_without_substring_false_positive(
    tmp_path, mode, body
):
    with listener(body=body) as port:
        f = Fixture(SCRIPT, tmp_path, port)
        f.env["POLL_INTERVAL"] = "1"
        if mode == "once":
            result = f.run("once")
            assert result.returncode == 1, result.stderr
            assert "confirmed by two probes" in result.stderr
        else:
            f.loop_until("restart failed")
        assert f.marker.exists()
        assert not list((tmp_path / "alerts").glob("*.json"))


@pytest.mark.parametrize("mode", ["once", "loop"])
@pytest.mark.parametrize(
    "body", [b"not JSON", b'{"note":"ok"}', b'{"status":true}', b"[]"]
)
def test_unparseable_or_untyped_json_cannot_authorize_restart(tmp_path, mode, body):
    with listener(body=body) as port:
        f = Fixture(SCRIPT, tmp_path, port)
        if mode == "once":
            result = f.run("once")
            assert result.returncode == 3, result.stderr
        else:
            f.loop_until("OBSERVER-BLIND")
        assert not f.marker.exists()
        alarm = json.loads(next((tmp_path / "alerts").glob("*.json")).read_text())
        assert alarm["state"] == "unobservable"

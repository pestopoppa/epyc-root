"""NIB2-98: job_fence RAM admission (MemAvailable - need >= 100 GiB margin), fake /proc/meminfo, no real exec/Landlock."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "job_fence.py"
sys.path.insert(0, str(HERE.parent))
import job_fence as jf  # noqa: E402


def meminfo(tmp_path, avail_gib):
    p = tmp_path / "meminfo"
    p.write_text(f"MemTotal: 999999999 kB\nMemFree: 1 kB\nMemAvailable: {int(avail_gib * 1024 ** 2)} kB\n")
    return str(p)


def test_default_margin_is_the_ratified_100():
    assert jf.RAM_MARGIN_GIB == 100


def test_admit_and_refuse_at_the_boundary(tmp_path):
    m = meminfo(tmp_path, 900)
    assert jf.ram_admission(739, 100, m)[0] is True       # 900-739=161 >= 100
    ok, why, avail = jf.ram_admission(800, 100, m)
    assert ok and avail == 900 and "admit" in why         # exactly at margin is admitted
    ok, why, _ = jf.ram_admission(801, 100, m)
    assert not ok and "refuse" in why and "margin 100" in why


def test_second_ds41_scenario_refused_first_admitted(tmp_path):
    # one DS41-class server running leaves ~(1128-739)=~389 GiB available; a second 739 GiB load must be refused.
    assert jf.ram_admission(739, 100, meminfo(tmp_path, 1100))[0] is True
    assert jf.ram_admission(739, 100, meminfo(tmp_path, 389))[0] is False


@pytest.mark.parametrize("need,margin", [(True, 100), (100, False), (-1, 100), (float("nan"), 100), (float("inf"), 100),
                                         ("abc", 100), (None, 100), (10, -5), (1e9, 100)])
def test_bad_inputs_fail_closed(tmp_path, need, margin):
    ok, why, _ = jf.ram_admission(need, margin, meminfo(tmp_path, 1000))
    assert not ok and why.startswith("refuse")


def test_unreadable_or_missing_memavailable_fails_closed(tmp_path):
    assert jf.ram_admission(1, 100, str(tmp_path / "absent"))[0] is False
    p = tmp_path / "nomem"
    p.write_text("MemTotal: 5 kB\n")
    assert jf.ram_admission(1, 100, str(p))[0] is False
    p.write_text("MemAvailable: oops kB\n")
    assert jf.ram_admission(1, 100, str(p))[0] is False


def test_take_ram_flags_and_env_fallback():
    head, need, margin = jf._take_ram(["/w", "--need-ram-gib", "739", "--ram-margin-gib", "64"], env={})
    assert (head, need, margin) == (["/w"], "739", "64")
    assert jf._take_ram(["/w"], env={}) == (["/w"], None, jf.RAM_MARGIN_GIB)
    assert jf._take_ram(["/w"], env={"JOB_FENCE_NEED_RAM_GIB": "50"})[1:] == ("50", jf.RAM_MARGIN_GIB)
    with pytest.raises(ValueError):
        jf._take_ram(["/w", "--need-ram-gib"], env={})


class Spy:
    def __init__(self):
        self.applied, self.execd = [], []


@pytest.fixture
def spy(monkeypatch, tmp_path):
    s = Spy()
    monkeypatch.setattr(jf, "apply", lambda *a, **k: s.applied.append(a))
    monkeypatch.setattr(jf.os, "execve", lambda *a: s.execd.append(a))
    monkeypatch.setattr(jf.resource, "setrlimit", lambda *a: None)
    monkeypatch.delenv("JOB_FENCE_NEED_RAM_GIB", raising=False)
    return s


def test_fence_refuses_before_landlock_and_exec(spy, capsys):
    rc = jf.main(["fence", "/mnt/raid0/llm/tmp", "--need-ram-gib", "999999", "--", "/bin/true"])
    assert rc == 75 and spy.applied == [] and spy.execd == []
    assert "refuse" in capsys.readouterr().err


def test_smoke_refuses_before_exec(spy, tmp_path):
    rc = jf.main(["smoke", str(tmp_path), "--need-ram-gib", "999999", "--", "/bin/true"])
    assert rc == 75 and spy.applied == [] and spy.execd == []


def test_negative_control_same_command_without_need_still_execs(spy, tmp_path):
    jf.main(["fence", str(tmp_path), "--", "/bin/true"])
    assert len(spy.execd) == 1 and spy.execd[0][0] == "/bin/true"


def test_fence_admits_when_need_is_zero(spy, tmp_path):
    jf.main(["fence", str(tmp_path), "--need-ram-gib", "0", "--ram-margin-gib", "0", "--", "/bin/true"])
    assert len(spy.execd) == 1


def test_env_injection_refuses_without_touching_the_command_line(spy, monkeypatch, tmp_path):
    monkeypatch.setenv("JOB_FENCE_NEED_RAM_GIB", "999999")
    assert jf.main(["fence", str(tmp_path), "--", "/bin/true"]) == 75 and spy.execd == []


def run_cli(*a):
    return subprocess.run([sys.executable, str(MOD), *a], capture_output=True, text=True)


def test_cli_ram_subcommand_refuse_and_admit():
    r = run_cli("ram", "--need-gib", "999999")
    assert r.returncode == 75 and json.loads(r.stdout)["admit"] is False
    r = run_cli("ram", "--need-gib", "0", "--margin-gib", "0")
    assert r.returncode == 0 and json.loads(r.stdout)["admit"] is True

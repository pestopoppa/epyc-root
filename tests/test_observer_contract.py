"""Conformance harness for the OBSERVATION CONTRACT.

WHAT THIS IS FOR
================
2026-08-12: ``scripts/coordination/bus_supervisor.sh`` identified the
coordinator-daemon with ``pgrep -f "session_bus_coordinator\\.py run"``. The live
daemon's argv was ``... session_bus_coordinator.py --bus-root <path> run``, so the
pattern matched nothing. The watchdog declared a healthy, actively heartbeating
daemon dead — **forever** — and relaunch-looped every ten seconds until somebody
happened to read its log hours later.

The bug is not the regex. The bug is that a guard could not observe the thing it
guards **and nothing detected that**. It held two independent signals, a fresh
heartbeat and a pid, and required BOTH, so the working signal was overruled by the
broken one and "cannot determine" was silently collapsed into "dead".

WHY THIS IS A RUNTIME HARNESS AND NOT A LINT
--------------------------------------------
A static rule ("never ``pgrep -f`` in a supervisor") would not have caught it. The
supervisor's own launch line agreed with its own pattern; *reality* did not,
because the running daemon had been started by a different caller with an extra
flag. Nothing in the file was wrong when read. The mismatch existed only at
runtime, so only a runtime check can see it. This suite therefore drives each
observer's real ``observe`` entrypoint against a real process in a sandbox.

WHY IT DISCOVERS ITS OWN SUBJECTS
---------------------------------
A test asserting "the bus supervisor sees the daemon" is worth having and is not
the deliverable: a *sibling* watchdog would still fail the same way in silence.
So the subjects are found structurally from the source tree (see
``scripts/coordination/observer_registry.json``), and anything found that is not
registered turns this suite red. Nobody has to remember to enroll a new watchdog,
which is the only property that survives the person who wrote the convention.

THE FOUR THINGS EVERY REGISTERED-ADOPTED OBSERVER MUST DO
---------------------------------------------------------
1. ``present``      when its target is genuinely running.
2. ``absent``       when its target is genuinely gone — and it must still ACT on
                    that. A guard that cries wolf at its own compliant path is a
                    defect this repo has shipped before.
3. ``unobservable`` when its channels DISAGREE (the specimen) or when it is
                    partially blind — never ``absent``.
4. take **no corrective action** while ``unobservable``, and say so loudly.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "coordination"))
import observer_census as census  # noqa: E402  (path set above)

REGISTRY_PATH = REPO / "scripts" / "coordination" / "observer_registry.json"
GUARD = REPO / "scripts" / "coordination" / "observer_guard.sh"
FIXTURES = REPO / "tests" / "fixtures" / "observer_contract"

# A mark that exists nowhere on this host but in the stand-in we spawn.
STANDIN_MARK = "epyc_obs_contract_standin_7f3a1c"

VALID_STATES = ("present", "absent", "unobservable")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def _registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


REGISTRY = _registry()
OBSERVERS = REGISTRY["observers"]
ADOPTED = [o for o in OBSERVERS if o["contract"] == "v1"]
UNADOPTED = [o for o in OBSERVERS if o["contract"] == "unadopted"]


def _ids(rows):
    return [r["id"] for r in rows]


# --------------------------------------------------------------------------- #
# Discovery — the part that does not rely on anyone remembering
# --------------------------------------------------------------------------- #

# The static checks live in scripts/coordination/observer_census.py so that the
# pre-commit hook and this suite run the SAME code. Two implementations of "is this
# repo's observer census honest" would be two things to keep in sync, and the one
# nobody runs would be the one that rots. Each check is surfaced as its own named
# test below, so a failure names the rule it broke — and is COUNTED by the reporter,
# which an assertion buried in a module's main() would not be.

@pytest.mark.parametrize("check_name", sorted(census.CHECKS))
def test_static_census(check_name):
    """DISCOVERY + REGISTRY HYGIENE, one named test per rule.

    ``rule-a-*`` is the one that makes this measure outlive whoever wrote it: it
    finds its own subjects in the source tree, so a new watchdog that identifies its
    target by name/argv enrols itself and fails here until somebody decides — out
    loud, in the registry — whether it is adopted, deferred, or exempt.
    """
    problems = census.CHECKS[check_name](REGISTRY)
    assert not problems, f"[{check_name}]\n  " + "\n  ".join(problems)


@pytest.mark.parametrize("row", UNADOPTED, ids=_ids(UNADOPTED))
def test_unadopted_instance_has_a_live_open_task(row):
    """A deferral must be attached to an UNCHECKED task in a real handoff.

    Deferring is allowed. Deferring *silently* is what let the specimen run for
    hours. Check the box without doing the migration, or delete the line, and this
    goes red — the deferral cannot decay into a forgotten one.
    """
    handoff = REPO / row["owning_handoff"]
    assert handoff.exists(), f"{row['id']}: owning handoff {row['owning_handoff']} does not exist"
    marker = row["task_marker"]
    open_lines = [
        ln for ln in handoff.read_text(errors="replace").splitlines()
        if marker in ln and re.search(r"-\s*\[\s\]", ln)
    ]
    assert open_lines, (
        f"{row['id']}: no OPEN '- [ ]' task carrying marker '{marker}' in "
        f"{row['owning_handoff']}. Either the migration landed (change the registry "
        f"row to contract 'v1') or the deferral was lost."
    )


# --------------------------------------------------------------------------- #
# The behavioural battery
# --------------------------------------------------------------------------- #

class Standin:
    """A real process whose argv contains STANDIN_MARK, so a /proc walk finds it."""

    def __init__(self, tmp: Path):
        self.path = tmp / f"{STANDIN_MARK}.sh"
        self.path.write_text("#!/bin/bash\nsleep 120\n")
        self.path.chmod(0o755)
        self.proc = None

    def start(self) -> int:
        self.proc = subprocess.Popen(
            ["/bin/bash", str(self.path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        # Wait until the kernel actually shows the argv, else the scan races us.
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                cmd = Path(f"/proc/{self.proc.pid}/cmdline").read_bytes()
                if STANDIN_MARK.encode() in cmd:
                    return self.proc.pid
            except OSError:
                pass
            time.sleep(0.05)
        raise AssertionError("stand-in process never became visible in /proc")

    def stop(self):
        # Only ever the pid this test itself created — never a pattern.
        if self.proc is not None and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGKILL)
            self.proc.wait(timeout=10)
            assert self.proc.poll() is not None, "stand-in did not die"
        self.proc = None


def _dead_pid() -> int:
    """A pid that is certainly not running: spawn one and reap it."""
    p = subprocess.Popen(["/bin/true"])
    p.wait()
    time.sleep(0.05)
    assert not Path(f"/proc/{p.pid}").exists(), "reaped pid still present"
    return p.pid


def _expand(value, mapping: dict) -> str:
    out = str(value)
    for k, v in mapping.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def _run_observe(script: Path, argv, env: dict) -> tuple[int, str]:
    full = dict(os.environ)
    full.update({k: str(v) for k, v in env.items()})
    full.pop("OG_BLIND_STREAK_MAX", None)
    res = subprocess.run(
        ["/bin/bash", str(script), *argv],
        capture_output=True, text=True, env=full, timeout=120,
    )
    m = re.search(r"^state=(\w+)", res.stdout, re.M)
    return res.returncode, (m.group(1) if m else f"<no state line> stdout={res.stdout!r} stderr={res.stderr[-400:]!r}")


def _write_heartbeat(path: Path, pid):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": time.time()}
    if pid is not None:
        payload["pid"] = pid
    path.write_text(json.dumps(payload))


def _sandbox_env(row: dict, tmp: Path, hb: Path, extra: dict | None = None) -> dict:
    mapping = {"root": REPO, "tmp": tmp, "mark": STANDIN_MARK, "heartbeat": hb}
    env = {k: _expand(v, mapping) for k, v in row["sandbox"]["env"].items()}
    if extra:
        env.update({k: _expand(v, mapping) for k, v in extra.items()})
    return env


def battery(script: Path, row: dict, tmp: Path) -> list[str]:
    """Run the four contract cases. Returns a list of failure descriptions.

    Returned rather than asserted so the SAME battery can be pointed at the broken
    fixture and its failures asserted *positively* — a mutation test that is a real
    collected test, not an assertion inside a main() the reporter never counts.
    """
    hb = Path(_expand(row["sandbox"]["heartbeat"], {"tmp": tmp}))
    hb.parent.mkdir(parents=True, exist_ok=True)
    argv = row["sandbox"].get("observe_argv", ["observe"])
    env = _sandbox_env(row, tmp, hb)
    failures = []
    standin = Standin(tmp)

    def check(case, expect_state, expect_rc):
        rc, state = _run_observe(script, argv, env)
        if state != expect_state or rc != expect_rc:
            failures.append(
                f"[{case}] expected state={expect_state} rc={expect_rc}, "
                f"got state={state} rc={rc}"
            )

    try:
        # ---- 1. COMPLIANT PATH: target genuinely running, both channels agree.
        pid = standin.start()
        _write_heartbeat(hb, pid)
        check("present", "present", 0)

        # ---- 2. COMPLIANT PATH: target genuinely gone, nothing to see anywhere.
        standin.stop()
        hb.unlink(missing_ok=True)
        check("absent", "absent", 1)

        # ---- 3. THE SPECIMEN. One channel sees the target, the other does not.
        #         The heartbeat names a dead pid while a live target is right there
        #         under a different identity — exactly the shape of an argv that
        #         drifted out from under a pattern. Two-state code answers "absent"
        #         here and starts killing.
        pid = standin.start()
        _write_heartbeat(hb, _dead_pid())
        check("channel-disagreement", "unobservable", 3)

        # ---- 4. PARTIAL BLINDNESS. A channel that cannot be evaluated at all is
        #         not a negative. Heartbeat present but carrying no pid, no target.
        standin.stop()
        _write_heartbeat(hb, None)
        check("partial-blindness", "unobservable", 3)
    finally:
        standin.stop()
    return failures


# --------------------------------------------------------------------------- #
# Mutation tests — the battery's own teeth, permanently pinned
# --------------------------------------------------------------------------- #

BROKEN_ROW = {
    "id": "broken_fixture",
    "script": "tests/fixtures/observer_contract/broken_watchdog.sh",
    "contract": "v1",
    "sandbox": {
        "env": {"EPYC_ROOT": "{root}", "HEARTBEAT": "{heartbeat}",
                "OG_STATE_DIR": "{tmp}/alerts", "RUNNER_MARK": "{mark}"},
        "heartbeat": "{tmp}/hb.json",
        "observe_argv": ["observe"],
    },
}
COMPLIANT_ROW = dict(BROKEN_ROW, id="compliant_fixture",
                     script="tests/fixtures/observer_contract/compliant_watchdog.sh")


def test_mutation_battery_detects_a_two_state_observer(tmp_path):
    """THE MUTATION. The preserved defect must be caught, and caught for the right reason.

    ``broken_watchdog.sh`` is the specimen reduced: one channel, believed
    absolutely, two states where three are needed. If the battery ever stops
    failing this, the battery has gone vacuous and every green run above it means
    nothing.
    """
    failures = battery(FIXTURES / "broken_watchdog.sh", BROKEN_ROW, tmp_path)
    assert failures, (
        "the battery PASSED a watchdog that cannot express 'I cannot tell'. "
        "The harness is vacuous."
    )
    joined = " | ".join(failures)
    assert "channel-disagreement" in joined, (
        "the battery failed the broken fixture, but not on the disagreement case — "
        f"i.e. not for the specimen's reason. Got: {joined}"
    )
    assert "partial-blindness" in joined, (
        f"the battery missed the unevaluable-channel case. Got: {joined}"
    )
    # And it must fail by reporting `absent` where `unobservable` was required —
    # the exact collapse that made a healthy daemon look dead.
    assert "got state=absent" in joined, (
        f"expected the broken fixture to collapse unknown into absent. Got: {joined}"
    )


def test_compliant_path_the_battery_accepts_a_conforming_observer(tmp_path):
    """THE COMPLIANT PATH. A guard that forbids its own idiom is a shipped defect.

    The minimal conforming watchdog must pass all four cases — including still
    answering a plain ``absent`` when the target really is gone. A harness that
    only ever demands ``unobservable`` would teach watchdogs to never act.
    """
    failures = battery(FIXTURES / "compliant_watchdog.sh", COMPLIANT_ROW, tmp_path)
    assert not failures, "the conforming fixture failed the battery:\n  " + "\n  ".join(failures)


# --------------------------------------------------------------------------- #
# The real observers
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("row", ADOPTED, ids=_ids(ADOPTED))
def test_adopted_observer_exposes_the_observe_entrypoint(row):
    script = REPO / row["script"]
    assert script.exists()
    assert re.search(r"^\s*observe\)", script.read_text(), re.M), (
        f"{row['id']} is registered contract v1 but exposes no `observe` subcommand"
    )


@pytest.mark.parametrize("row", ADOPTED, ids=_ids(ADOPTED))
def test_adopted_observer_passes_the_battery(row, tmp_path):
    failures = battery(REPO / row["script"], row, tmp_path)
    assert not failures, f"{row['id']} violates the observation contract:\n  " + "\n  ".join(failures)


@pytest.mark.parametrize("row", [r for r in ADOPTED if "action_probe" in r],
                         ids=[r["id"] for r in ADOPTED if "action_probe" in r])
def test_adopted_observer_suppresses_action_while_blind_but_acts_when_absent(row, tmp_path):
    """The consequence, not just the verdict.

    Reporting ``unobservable`` and then relaunching anyway would be the specimen
    with extra logging. Both halves are asserted here, because only asserting the
    first half would pass a watchdog that had simply stopped working.
    """
    probe = row["action_probe"]
    hb = Path(_expand(row["sandbox"]["heartbeat"], {"tmp": tmp_path}))
    marker = Path(_expand(probe["marker"], {"tmp": tmp_path}))

    stub = tmp_path / "stub_runner.sh"
    stub.write_text(f"#!/bin/bash\n: > {marker}\nexit 0\n")
    stub.chmod(0o755)

    mapping = {"root": REPO, "tmp": tmp_path, "mark": STANDIN_MARK,
               "heartbeat": hb, "stub": stub}
    env = _sandbox_env(row, tmp_path, hb,
                       {k: _expand(v, mapping) for k, v in probe["env"].items()})
    env["OG_STATE_DIR"] = str(tmp_path / "alerts")

    standin = Standin(tmp_path)
    try:
        # --- BLIND: channels disagree. Nothing may be launched, and it must shout.
        pid = standin.start()
        _write_heartbeat(hb, _dead_pid())
        marker.unlink(missing_ok=True)
        subprocess.run(["/bin/bash", str(REPO / row["script"]), *probe["argv"]],
                       capture_output=True, text=True, env={**os.environ, **env},
                       timeout=180)
        assert not marker.exists(), (
            f"{row['id']} launched its target while UNOBSERVABLE — the specimen's "
            "relaunch loop, reproduced"
        )
        alerts = list((tmp_path / "alerts").glob("*.json"))
        assert alerts, f"{row['id']} went blind SILENTLY — no alarm breadcrumb written"
        payload = json.loads(alerts[0].read_text())
        assert payload["state"] == "unobservable"
        assert payload["detail"].strip(), "alarm written with no reason"

        # --- COMPLIANT PATH: genuinely absent. It MUST still act.
        standin.stop()
        hb.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)
        subprocess.run(["/bin/bash", str(REPO / row["script"]), *probe["argv"]],
                       capture_output=True, text=True, env={**os.environ, **env},
                       timeout=180)
        assert marker.exists(), (
            f"{row['id']} did NOT start its target when it was genuinely absent — "
            "the guard has disabled the watchdog it was meant to protect"
        )
    finally:
        standin.stop()


# --------------------------------------------------------------------------- #
# Unit coverage of the guard primitives
# --------------------------------------------------------------------------- #

def _guard(snippet: str, tmp: Path) -> str:
    script = tmp / "g.sh"
    script.write_text(
        "set -euo pipefail\n"
        f"source {GUARD}\n"
        "og_init unit\n" + snippet
    )
    res = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True,
                         env={**os.environ, "OG_STATE_DIR": str(tmp / "s")}, timeout=60)
    assert res.returncode == 0, res.stderr[-2000:]
    return res.stdout.strip()


@pytest.mark.parametrize("channels,expected", [
    ("og_channel a present; og_channel b present", "present"),
    ("og_channel a absent; og_channel b absent", "absent"),
    ("og_channel a present; og_channel b absent", "unobservable"),
    ("og_channel a absent; og_channel b unavailable x", "unobservable"),
    ("og_channel a unavailable x; og_channel b unavailable y", "unobservable"),
    ("", "unobservable"),
])
def test_fold_truth_table(channels, expected, tmp_path):
    out = _guard(f"og_round_begin; {channels}\nog_verdict || true\n", tmp_path)
    assert out == expected


def test_unavailable_never_becomes_absent(tmp_path):
    """The single most important row: a tool that is missing is not a dead target."""
    out = _guard(
        "og_round_begin\n"
        "og_channel probe \"$(og_tool_channel definitely_no_such_tool_xyz foo)\" missing\n"
        "og_verdict || true\n", tmp_path)
    assert out == "unobservable"


def test_blind_streak_forces_unobservable(tmp_path):
    """Launch is the positive control: N launches with no sighting indicts the observer."""
    out = _guard(
        "og_round_begin; og_channel a absent\n"
        "printf 'before=%s\\n' \"$(og_verdict || true)\"\n"
        "og_note_launch; og_note_launch; og_note_launch\n"
        "og_round_begin; og_channel a absent\n"
        "printf 'after=%s\\n' \"$(og_verdict || true)\"\n"
        "og_note_sighting\n"
        "og_round_begin; og_channel a absent\n"
        "printf 'recovered=%s\\n' \"$(og_verdict || true)\"\n", tmp_path)
    assert "before=absent" in out
    assert "after=unobservable" in out
    assert "recovered=absent" in out


def test_proc_scan_excludes_its_own_argv(tmp_path):
    """CLAUDE.md: 'a guard process's argv necessarily contains the names it guards.'

    Caught for real while writing this: the scan reported `present` for a string
    that existed nowhere but in the scanning shell's own command line, because a
    command-substitution subshell is a different pid carrying an identical cmdline.
    """
    out = _guard(
        "og_round_begin\n"
        "printf 'miss=%s\\n' \"$(og_present_if_any \"$(og_proc_scan zzz_no_such_process_zzz)\")\"\n",
        tmp_path)
    assert out == "miss=absent"


def test_alarm_writes_a_machine_readable_breadcrumb(tmp_path):
    state = tmp_path / "s"
    _guard("og_round_begin; og_channel a present; og_channel b absent\n"
           "og_verdict || true\nog_alarm \"$(og_why)\" 2>/dev/null\n", tmp_path)
    files = list(state.glob("*.json"))
    assert files, "og_alarm wrote no breadcrumb"
    payload = json.loads(files[0].read_text())
    assert payload["state"] == "unobservable"
    assert "DISAGREE" in payload["detail"]


def test_alerts_cli_exits_nonzero_while_any_observer_is_blind(tmp_path):
    """The surface anything can poll without knowing which watchdogs exist."""
    state = tmp_path / "s"
    state.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "OG_STATE_DIR": str(state)}

    clean = subprocess.run(["/bin/bash", str(GUARD), "alerts"],
                           capture_output=True, text=True, env=env, timeout=60)
    assert clean.returncode == 0, clean.stdout

    (state / "someone.json").write_text(json.dumps(
        {"observer": "someone", "state": "unobservable", "ts": "x", "detail": "y"}))
    blind = subprocess.run(["/bin/bash", str(GUARD), "alerts"],
                           capture_output=True, text=True, env=env, timeout=60)
    assert blind.returncode == 3, blind.stdout
    assert "OBSERVER-BLIND" in blind.stdout


def test_guard_is_executable_and_syntactically_valid():
    assert os.access(GUARD, os.X_OK), f"{GUARD} is not executable"
    for path in [GUARD, FIXTURES / "compliant_watchdog.sh", FIXTURES / "broken_watchdog.sh",
                 *[REPO / r["script"] for r in ADOPTED if r["script"].endswith(".sh")]]:
        res = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        assert res.returncode == 0, f"{path}: {res.stderr}"

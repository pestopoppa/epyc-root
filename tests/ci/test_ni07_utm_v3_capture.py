import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/ci/ni07_utm_v3_capture.py"
SPEC = importlib.util.spec_from_file_location("ni07_utm_v3_capture", SCRIPT)
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


def test_capture_passes_declared_readout_to_child_and_preserves_environment(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    runner_temp = tmp_path / "runner-temp"
    recipe, carrier, app = (workspace / name for name in ("recipe", "carrier", "app"))
    for path in (recipe / ".github/workflows", carrier / "scripts/ci", app / "tests/unit/fixtures/utm_v3"):
        path.mkdir(parents=True)
    (recipe / ".github/workflows/ni07-utm-v3.yml").touch()
    (carrier / "scripts/ci/native_conformance.py").touch()
    for name in ("test_utm_v3_conformance.py", "fixtures/utm_v3/synthetic_cases.json",
                 "fixtures/utm_v3/rubric.json", "uv.lock"):
        (app / "tests/unit" / name if name != "uv.lock" else app / name).touch()

    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))
    monkeypatch.setenv("RUNNER_TEMP", str(runner_temp))
    monkeypatch.setenv("APP_PIN", "app-pin")
    monkeypatch.setenv("ROOT_CARRIER_PIN", "carrier-pin")
    monkeypatch.setenv("NI07_UTM_INSTALL_COMMAND", "install")
    monkeypatch.setenv("PARENT_SENTINEL", "preserve-me")
    monkeypatch.setattr(CAPTURE, "tracked_inputs", lambda _repo: ())

    def check_output(args, **_kwargs):
        return b"dependency==1\n" if "freeze" in args else "recipe-pin\n"

    calls = []

    def call(args, **kwargs):
        calls.append((args, kwargs))
        return 0

    monkeypatch.setattr(subprocess, "check_output", check_output)
    monkeypatch.setattr(subprocess, "call", call)

    assert CAPTURE.main() == 0

    args, kwargs = calls[0]
    declared = app / CAPTURE.GENERATED_OUTPUT
    assert kwargs["env"]["NI07_UTM_READOUT"] == str(declared)
    assert kwargs["env"]["PARENT_SENTINEL"] == "preserve-me"
    assert args[args.index("--generated-output") + 1] == CAPTURE.GENERATED_OUTPUT

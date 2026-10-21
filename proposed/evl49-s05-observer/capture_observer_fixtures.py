"""Offhost original synthetic capture; observer launcher is never invoked."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

workspace = Path(os.environ["GITHUB_WORKSPACE"])
recipe, enrollment, carrier, leaf = [workspace / name for name in ("recipe", "enrollment", "carrier", "leaf")]
temp = Path(os.environ["RUNNER_TEMP"])
fixture = temp / "observer-test"
result = temp / "observer-result"
result.mkdir(exist_ok=False)
if sys.version_info[:3] != (3, 13, 15):
    raise RuntimeError("reviewed interpreter mismatch")
if hashlib.sha256((fixture / "s05_sourceprep.py").read_bytes()).hexdigest() != "2a87c2e3adb9a028335c7be4bd7e801d9e3efddbbf631346efae04bce9bd75e7":
    raise RuntimeError("accepted source leaf mismatch")
expected = {"iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0", "Pygments": "2.20.0", "pytest": "9.0.3", "PyYAML": "6.0.3"}
for name, version in expected.items():
    if importlib.metadata.version(name) != version:
        raise RuntimeError("reviewed fixture dependency mismatch")
context = result / "runtime.json"
context.write_text(json.dumps({"python": sys.version, "executable": sys.executable, "dependencies": expected,
    "scope": "synthetic raw files and validator only; launcher/proc/cache/server/measurement not executed"}, indent=2) + "\n")
reads = [context, Path(sys.executable).resolve(), *(fixture / name for name in ("s05_observer.py", "test_s05_observer.py", "s05_sourceprep.py")),
         recipe / "proposed/evl49-s05-observer/capture_observer_fixtures.py", recipe / ".github/workflows/s05-observer-fixtures.yml",
         enrollment / "scripts/ci/vb_rtg23w9_native_requirements.txt", enrollment / "scripts/vidya/adapters/README.md",
         enrollment / "handoffs/active/vidya-belief-substrate-program.md"]
reads += [carrier / name for name in ("scripts/ci/native_conformance.py", "scripts/vidya/adapters/ci_conformance.py", "scripts/vidya/claim_tuple.py",
                                     "scripts/vidya/canonical.py", "scripts/vidya/frames.py", "scripts/vidya/lattice.py")]
for distribution in importlib.metadata.distributions():
    for name in distribution.files or ():
        path = Path(distribution.locate_file(name)).resolve()
        if path.is_file() and (path.suffix in (".py", ".so") or path.name in ("METADATA", "RECORD", "WHEEL")):
            reads.append(path)
stdlib = Path(sysconfig.get_path("stdlib"))
reads += [path for pattern in ("*.py", "*.so") for path in stdlib.rglob(pattern)
          if "site-packages" not in path.parts and path.is_file() and not path.is_symlink()]
command = [sys.executable, "-B", str(carrier / "scripts/ci/native_conformance.py"), "--cwd", str(fixture),
           "--junit", str(result / "original-junit.xml"), "--output", str(result / "native")]
for label, path in (("recipe", recipe), ("enrollment", enrollment), ("carrier", carrier), ("leaf", leaf)):
    command += ["--repo", f"{label}={path}"]
for path in dict.fromkeys(reads):
    command += ["--read-path", str(path)]
selections = ["test_original_raw_bindings_pass", *[f"test_original_raw_binding_refusals[{defect}]" for defect in
              ("missing", "posthoc", "stale_pid", "tampered_raw", "contradictory_policy", "failed_cache", "survivor", "outside_request")], "test_nonregular_raw_artifact_refused", "test_existing_lifecycle_seams_preserve_owned_identity"]
for selection in selections:
    command += ["--select", selection]
command += ["--", sys.executable, "-B", "-m", "pytest", "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider", "-q",
            "-o", "junit_logging=all", "-o", "junit_log_passing_tests=true", f"--junitxml={result / 'original-junit.xml'}", str(fixture / "test_s05_observer.py")]
completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
(result / "outer.stdout.raw").write_bytes(completed.stdout)
(result / "outer.stderr.raw").write_bytes(completed.stderr)
(result / "outer.argv-exit.json").write_text(json.dumps({"argv": command, "exit": completed.returncode}, indent=2) + "\n")
sys.path.insert(0, str(carrier / "scripts/vidya"))
sys.path.insert(0, str(carrier))
from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
from claim_tuple import grade
grades = [{"Q": q, "T": t, "reasons": reasons} for row in native_rows(result / "native/receipt.json")
          for q, t, reasons in [grade(project_ci_conformance(row))]]
(result / "shared-grade.json").write_text(json.dumps(grades, indent=2) + "\n")
raise SystemExit(completed.returncode)

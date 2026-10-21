"""DRAFT prospective existing native CI carrier; intentionally unbound until MAIN enrollment."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
ENROLLMENT_PIN = "a4b6bac87b4c9692271e12caa7bfd9a37c4e643a"
ENROLLMENT_ID = "VB-CJ10-PROMPT-SOURCE-CONFORMANCE"

def main():
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    recipe, carrier, enrollment = [workspace / name for name in ("recipe", "carrier", "enrollment")]
    if len(ENROLLMENT_PIN) != 40:
        raise RuntimeError("MAIN prospective enrollment is not bound")
    for tree, pin in ((recipe, os.environ["GITHUB_SHA"]), (carrier, CARRIER_PIN), (enrollment, ENROLLMENT_PIN)):
        if subprocess.check_output(["git", "-C", str(tree), "rev-parse", "HEAD"]).decode().strip() != pin:
            raise RuntimeError("checkout identity mismatch")
    if os.environ.get("GITHUB_EVENT_NAME")!="push" or os.environ.get("GITHUB_RUN_ATTEMPT")!="1" or os.environ.get("GITHUB_REF")!="refs/heads/codex/cj10-source-conformance-json-fixtures-20261021": raise RuntimeError("fresh original OWN push only")
    research=workspace/"research"
    if subprocess.check_output(["git","-C",str(research),"rev-parse","HEAD"]).decode().strip()!="c43ce72f22501944eb76d40ce6af6e696d6c3931": raise RuntimeError("Research source boundary mismatch")
    manifest = json.loads((HERE / "source-map.json").read_text())
    if manifest.get("status") != "BOUND_MAIN_REVIEWED" or manifest.get("pending_readset"):
        raise RuntimeError("prospective source readset is not fully bound")
    if manifest["enrollment_commit"] != ENROLLMENT_PIN:
        raise RuntimeError("enrollment manifest mismatch")
    readset = [HERE / "source-map.json"]
    if (HERE / "source-map.json").read_bytes() != subprocess.check_output(["git", "-C", str(recipe), "show", os.environ["GITHUB_SHA"] + ":proposed/cj10/source-map.json"]):
        raise RuntimeError("source manifest changed")
    for row in manifest["files"]:
        path = {"recipe": recipe, "carrier": carrier, "enrollment": enrollment,"research":research}[row["repo"]] / row["path"]
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise RuntimeError("readset changed: " + row["path"])
        if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=row["Gitblob"]: raise RuntimeError("frozen Gitblob differs")
        readset.append(path)
    for relative in ("scripts/vidya/adapters/README.md", "handoffs/active/vidya-belief-substrate-program.md"):
        if ENROLLMENT_ID not in (enrollment / relative).read_text():
            raise RuntimeError("prospective source enrollment absent")
    result = Path(os.environ["RUNNER_TEMP"]) / "cj10-native-original"
    result.mkdir()
    junit, native = result / "original-junit.xml", result / "native"
    argv = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"), "--cwd", str(recipe),
            "--junit", str(junit), "--output", str(native), "--repo", "recipe=" + str(recipe),
            "--repo", "carrier=" + str(carrier), "--repo", "enrollment=" + str(enrollment), "--repo", "research=" + str(research)]
    for path in readset:
        argv += ["--read-path", str(path)]
    for name in ("test_beam_adapter.py", "test_judge_beam_run.py", "test_beam_judge_provenance.py"):
        argv += ["--select", "recipe:proposed/cj10/payload/research/scripts/benchmark/" + name]
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    env.pop("PYTHONPATH", None)
    return subprocess.call(argv + ["--", sys.executable, "-I", str(HERE / "bootstrap.py"), str(junit), str(carrier)], cwd=recipe, env=env)

if __name__ == "__main__":
    raise SystemExit(main())

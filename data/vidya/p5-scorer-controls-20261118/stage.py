"""Build a sealed private Sphinx P5 successor from the retained scorer sources."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/coordination/gpu-serving-tie-in/p5-gold-validation/prepared-sphinx-r2-20261104"
ORIGINAL_MANIFEST = "0d7bda06d2df025afe509b9b78981c80ea96e3bff6b78f212d76ee2bcfaf87c7"
ROW = "vb-p5-sphinx-scorer-native-20261118"
PYTHON = "/mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python"
FILES = ("case.json", "job.py", "complete.py", "pins.json", "offline_eval.py", "source_guard.py",
         "run-controls.py", "test_native_outcome.py", "test_parser_reporting.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(dest, *, image_receipt=None, build=False):
    if not re.fullmatch(r"/mnt/raid0/llm/tmp/vidya-belief-substrate/[a-z0-9-]+", str(dest)):
        raise ValueError("stage to a new Vidya scratch directory without shell metacharacters")
    packet = Path(__file__).parent
    if build:
        dest.mkdir()
        (dest / "context").mkdir()
        shutil.copyfile(SOURCE / "Dockerfile", dest / "context/Dockerfile")
        shutil.copyfile(packet / "build-image.sh", dest / "build-image.sh")
        (dest / "build-image.sh").chmod(0o750)
        manifest = dest / "SOURCE.sha256"
        manifest.write_text("".join(f"{sha(dest / name)}  {name}\n"
                                    for name in ("build-image.sh", "context/Dockerfile")))
        launcher = dest / "launch.sh"
        launcher.write_text(f"""#!/bin/bash
set -euo pipefail
cd {dest}
printf '%s  %s\\n' '{sha(manifest)}' SOURCE.sha256 | sha256sum --check --status
sha256sum --check --status SOURCE.sha256
export P5_BUILD_LAUNCHER={dest}/launch.sh
exec {dest}/build-image.sh "$@"
""")
        launcher.chmod(0o750)
        template = (packet / "build.spec.template.json").read_text()
        (dest / "spec.json").write_text(template.replace("@SCRATCH@", str(dest)))
        return
    manifest = SOURCE / "SOURCE.sha256"
    if sha(manifest) != ORIGINAL_MANIFEST:
        raise ValueError("historical source manifest drift")
    original = {name: digest for digest, name in (line.split() for line in manifest.read_text().splitlines())}
    for name in FILES:
        if sha(SOURCE / name) != original[name]:
            raise ValueError(f"historical scorer source drift: {name}")
    dest.mkdir()
    for name in FILES:
        shutil.copyfile(SOURCE / name, dest / name)
    source = (dest / "job.py").read_text()
    edits = {
        "output=D/'RESULT.json'": "output=Path(os.environ['P5_NATIVE_RESULT'])",
        "try:\n for arm,patch in arms:": "result['arm_attempts']={}\ntry:\n for arm,patch in arms:",
        "  ret=ev.run_instance(spec,pred,False,False,client,run_id,timeout=remaining)\n"
        "  d=D/'logs/run_evaluation'/run_id/arm/case['instance_id']; report=":
        "  d=D/'logs/run_evaluation'/run_id/arm/case['instance_id']\n"
        "  result['arm_attempts'][arm]={'native_report':str(d/'report.json'),"
        "'test_log':str(d/'test_output.txt')}\n"
        "  ret=ev.run_instance(spec,pred,False,False,client,run_id,timeout=remaining)\n"
        "  report=",
    }
    for before, after in edits.items():
        if source.count(before) != 1:
            raise ValueError("historical scorer finalization changed")
        source = source.replace(before, after)
    # The original job stays byte-for-byte intact for its existing AST-based controls.
    (dest / "scorer.py").write_text(source)
    shutil.copyfile(ROOT / "scripts/vidya/producers/p5_scorer_custody.py", dest / "custody.py")
    names = (*FILES, "scorer.py", "custody.py")
    if image_receipt is not None:
        image_receipt = image_receipt.resolve(strict=True)
        receipt = json.loads(image_receipt.read_bytes())
        build_log = Path(receipt["build_log"]).resolve(strict=True)
        pins_file = dest / "pins.json"
        pins = json.loads(pins_file.read_bytes())
        if (image_receipt.name != "RESULT.json" or image_receipt.parent.name != "official"
                or receipt["id"] != "vb-p5-sphinx-image-rebuild-20261118" or receipt["mode"] != "official"
                or receipt["status"] != "COMPLETE" or receipt["base_image_id"] != pins["base_image_id"]
                or receipt["dockerfile_sha256"] != pins["dockerfile_sha256"]
                or image_receipt.parent != build_log.parent.parent
                or sha(build_log) != receipt["build_log_sha256"]):
            raise ValueError("official image build custody refused")
        pins.update(image_id=receipt["image_id"], image_build_log_sha256=receipt["build_log_sha256"])
        pins_file.write_text(json.dumps(pins, indent=2) + "\n")
        shutil.copyfile(image_receipt, dest / "build-receipt.json")
        shutil.copyfile(build_log, dest / "build.log")
        names += ("build-receipt.json", "build.log")
    (dest / "SOURCE.sha256").write_text("".join(f"{sha(dest / name)}  {name}\n" for name in names))
    image = json.loads((dest / "pins.json").read_bytes())["image_id"]
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise ValueError("invalid pinned scorer image")
    (dest / "preflight.sh").write_text(f"""#!/bin/bash
set -euo pipefail
cd {dest}
printf '%s  %s\\n' '{sha(dest / "SOURCE.sha256")}' SOURCE.sha256 | sha256sum --check --status
sha256sum --check --status SOURCE.sha256
test -x {PYTHON}
docker image inspect '{image}' >/dev/null
""")
    (dest / "launch.sh").write_text(f"""#!/bin/bash
set -euo pipefail
D={dest}
cd "$D"
printf '%s  %s\\n' '{sha(dest / "preflight.sh")}' preflight.sh | sha256sum --check --status
if [[ ${{1:-}} == --job ]]; then
  /bin/bash "$D/preflight.sh"
  unset PYTHONPATH PYTHONHOME
  exec {PYTHON} -B "$D/custody.py" run
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \\
  --id {ROW} --class cpu --role bench --min-window 300 \\
  --stop "$D/STOP" --workdir "$D" --precond-cmd "/bin/bash $D/preflight.sh" \\
  --cmd "/bin/bash $D/launch.sh --job" --complete-cmd "{PYTHON} -B $D/custody.py complete"
""")
    (dest / "launch.sh").chmod(0o750)
    template = json.loads((Path(__file__).parent / "spec.template.json").read_bytes())
    for name, value in template.items():
        if isinstance(value, str):
            template[name] = value.replace("@SCRATCH@", str(dest)).replace("@PYTHON@", PYTHON)
    (dest / "spec.json").write_text(json.dumps(template, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch", type=Path)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--build", action="store_true")
    options.add_argument("--image-receipt", type=Path)
    args = parser.parse_args()
    stage(args.scratch, build=args.build, image_receipt=args.image_receipt)

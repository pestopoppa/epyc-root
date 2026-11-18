"""Prepare a sealed Astropy scorer successor from an official rebuild receipt."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import shutil
import tempfile

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
SCRATCH_ROOT = Path("/mnt/raid0/llm/tmp/vidya-belief-substrate")
SOURCE = ROOT / "scripts/coordination/gpu-serving-tie-in/p5-gold-validation/prepared-20261104"
CUSTODY = ROOT / "scripts/vidya/producers/p5_scorer_custody.py"
ORIGINAL_MANIFEST = "f4cbcf8b12ddd6063f6d185638342f9ac3c43ed834dde9760471a0734cc55443"
ROW = "vb-p5-astropy-scorer-native-20261118"
BUILD_ROW = "vb-p5-astropy-image-rebuild-20261118"
BASE_REF = ("swebench/sweb.eval.x86_64.astropy_1776_astropy-12907@"
            "sha256:7485c1e3c8861efd0c6a4a78b952857592e541031039000d25e9481f045dc4a3")
PYTHON = "/mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python"
FILES = ("case.json", "job.py", "complete.py", "pins.json", "offline_eval.py", "source_guard.py",
         "test_native_outcome.py", "Dockerfile", "BUILD-SOURCE.sha256", "WHEELHOUSE.sha256")
VALIDATOR = runpy.run_path(str(PACKET / "complete.py"))


def sha(contents):
    return hashlib.sha256(contents).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rewrite(source, edits):
    for before, after in edits:
        require(source.count(before) == 1, f"staging source anchor changed: {before!r}")
        source = source.replace(before, after, 1)
    compile(source, "<private scorer source>", "exec")
    return source.encode()


def official_build(path, pins):
    path = path.resolve(strict=True)
    require(path.name == "RESULT.json" and path.parent.name == "official",
            "expected official Astropy build RESULT.json")
    original = path.read_bytes()
    receipt = json.loads(original)
    require(receipt["schema"] == "epyc.p5.image-build-capture.v1" and receipt["id"] == BUILD_ROW
            and receipt["mode"] == "official" and receipt["status"] == "COMPLETE"
            and type(receipt["runner_rc"]) is int and receipt["runner_rc"] == 0,
            "official Astropy image build custody refused")
    require(receipt["base_ref"] == BASE_REF and receipt["base_image_id"] == pins["base_image_id"]
            and receipt["dockerfile_sha256"] == pins["dockerfile_sha256"]
            and receipt["context_sha256"] == pins["build_context_seal_sha256"]
            and re.fullmatch(r"sha256:[0-9a-f]{64}", receipt["image_id"])
            and receipt["image_id"] != pins["base_image_id"],
            "Astropy build input or output identity refused")
    root = path.parent.parent
    sources, launcher = (root / "SOURCE.sha256").read_bytes(), (root / "launch.sh").read_bytes()
    require(sha(sources) == receipt["source_manifest_sha256"] and sha(launcher) == receipt["launcher_sha256"],
            "build source or launcher drift")
    log_path = Path(receipt["build_log"]).resolve(strict=True)
    require(log_path.name == "build.log" and log_path.parent.parent == path.parent
            and log_path.parent.name.startswith("build-"),
            "official Astropy build log path refused")
    attempt_receipt = log_path.parent / "receipt.json"
    require(path.samefile(attempt_receipt) and original == attempt_receipt.read_bytes(),
            "official Astropy terminal is not the original build attempt receipt")
    iid_path = (log_path.parent / "image.iid").resolve(strict=True)
    iid = iid_path.read_bytes()
    require(iid_path.parent == log_path.parent and iid.decode().strip() == receipt["image_id"],
            "original build image ID differs from the receipt")
    grant_path = (log_path.parent / "rowflow.grant").resolve(strict=True)
    require(grant_path.parent == log_path.parent, "official Astropy build grant path refused")
    log, grant = log_path.read_bytes(), grant_path.read_bytes()
    require(bool(log) and sha(log) == receipt["build_log_sha256"] and sha(grant) == receipt["grant_sha256"],
            "build log or grant digest mismatch")
    fields = VALIDATOR["read_grant"](grant)
    utc_epoch, cpu_set = VALIDATOR["utc_epoch"], VALIDATOR["cpu_set"]
    start, end = (utc_epoch(fields[key]) for key in ("start", "end"))
    started, finished = (utc_epoch(receipt[key]) for key in ("started_utc", "completion_utc"))
    allowed, actual, build = map(cpu_set, (fields["regions"], receipt["actual_cpus"], receipt["build_cpus"]))
    require(fields.get("kind") != "rowflow-dryrun" and fields.get("id", BUILD_ROW) == BUILD_ROW
            and start == receipt["grant_start_epoch"] <= started <= finished < min(end - 90, started + 270)
            and receipt["deadline_epoch"] == end - 90
            and len(build) == 4 and build <= actual <= allowed, "official Astropy build grant refused")
    return receipt, {"build-receipt.json": original, "build.log": log, "build.grant": grant,
                     "build-launch.sh": launcher, "build-SOURCE.sha256": sources, "build-image.iid": iid}


def native_scorer(source):
    return rewrite(source, (
        ("from source_guard import verify_checkout", "from source_guard import verify_checkout\nfrom complete import diagnostic"),
        ("deadline=float(os.environ['FILLER_DEADLINE'])", "deadline=float(os.environ['P5_INSTRUMENT_DEADLINE'])"),
        ("owned.append(c)\n return c", "owned.append(c)\n"
         " if arm in result['arm_container_ids']: raise RuntimeError('more than one container for arm: '+arm)\n"
         " result['arm_container_ids'][arm]=c.id\n return c"),
        ("try:\n for arm,patch in arms:", "result.update(arm_attempts={},arm_container_ids={})\ntry:\n for arm,patch in arms:"),
        ("  remaining=int(deadline-time.time())-40", "  if Path(os.environ['FILLER_STOPFILE']).exists(): raise SystemExit(75)\n"
         "  remaining=int(deadline-time.time())-40"),
        ("  ret=ev.run_instance(spec,pred,False,False,client,run_id,timeout=remaining)\n"
         "  d=D/'logs/run_evaluation'/run_id/arm/case['instance_id']; report=",
         "  d=D/'logs/run_evaluation'/run_id/arm/case['instance_id']\n"
         "  result['arm_attempts'][arm]={'native_report':str(d/'report.json'),'test_log':str(d/'test_output.txt')}\n"
         "  ret=ev.run_instance(spec,pred,False,False,client,run_id,timeout=remaining)\n"
         "  report="),
        ("  if arm=='gold': assert resolved and all(x=='PASSED' for x in failstat.values()) and all(x=='PASSED' for x in passstat.values())\n"
         "  else: assert not resolved and any(x=='FAILED' for x in failstat.values()) and all(x=='PASSED' for x in passstat.values())\n", ""),
        (" result['status']='PASS'", " result['decision']=diagnostic(result['arms'])\n result['status']='COMPLETE'"),
        ("\n result['status']='FAIL'", "\n result['status']='UNKNOWN'"),
        ("  result['status']='FAIL'", "  result['status']='UNKNOWN'"),
        ("  output=D/'RESULT.json'", "  result['owned_container_ids']=[c.id for c in owned]\n  output=Path(os.environ['P5_NATIVE_RESULT'])"),
        (""" for c in owned[::-1]:
  try: c.remove(force=True)
  except docker.errors.NotFound: pass
  try: client.containers.get(c.id)
  except docker.errors.NotFound: continue
  raise RuntimeError('owned container still exists: '+c.id)
""", """ errors=[]
 for c in owned[::-1]:
  try:
   try: c.remove(force=True)
   except docker.errors.NotFound: pass
   try: client.containers.get(c.id)
   except docker.errors.NotFound: continue
   raise RuntimeError('owned container still exists: '+c.id)
  except Exception as exc:
   errors.append((c.id,repr(exc)))
 if errors: raise RuntimeError('owned container cleanup refused: '+repr(errors))
"""),
    ))


def native_custody(source):
    return rewrite(source, (
        ('ROW = "vb-p5-sphinx-scorer-native-20261118"', f'ROW = "{ROW}"'),
        ("from datetime import datetime, timezone", "from datetime import datetime, timezone\n"
         "from complete import cpu_set, read_grant, utc_epoch, validate_window"),
        (source[source.index("def cpu_set"):source.index("def grant_context")], ""),
        ('else flags / "grants"', 'else Path(env.get("FILLER_GRANTS_DIR", flags / "grants"))'),
        ('fields = dict(field.split("=", 1) for field in contents.decode().split())\n'
         '    start, end = (datetime.fromisoformat(fields[key]).timestamp() for key in ("start", "end"))',
         'fields = read_grant(contents)\n    start, end = (utc_epoch(fields[key]) for key in ("start", "end"))'),
        ('os.environ["P5_INSTRUMENT_DEADLINE"] = str(min(time.time() + 270, result["grant"]["deadline_epoch"]))',
         'result["instrument_deadline_epoch"] = min(time.time() + 270, result["grant"]["deadline_epoch"])\n'
         '        os.environ["P5_INSTRUMENT_DEADLINE"] = str(result["instrument_deadline_epoch"])'),
        ("result[\"decision\"] = validate_native(raw, json.loads((ROOT / \"case.json\").read_bytes()))",
         """if (set(result["arm_artifacts_sha256"]) != {f"{arm}-{name}" for arm in ("gold", "negative")
                                                                     for name in ("report.json", "test_output.txt")}
                            or raw["producer_source_manifest_sha256"] != result["source_manifest_sha256"]
                            or raw["producer_launcher_sha256"] != result["launcher_sha256"]):
                        raise ValueError("original scorer result binding refused")
                    result["decision"] = validate_native(raw, json.loads((ROOT / "case.json").read_bytes()), attempt, ROOT)
                    result["completion_utc"] = utc()
                    validate_window(result, attempt)"""),
        ('if time.time() >= result["grant"]["deadline_epoch"] or Path(os.environ["FILLER_STOPFILE"]).exists():',
         'if time.time() >= result["instrument_deadline_epoch"] or Path(os.environ["FILLER_STOPFILE"]).exists():'),
        ('result["completion_utc"] = utc()\n        result["runner_rc"]', 'result.setdefault("completion_utc", utc())\n        result["runner_rc"]'),
        ('or validate_native(raw, json.loads((ROOT / "case.json").read_bytes())) != result["decision"]',
         'or validate_native(raw, json.loads((ROOT / "case.json").read_bytes()), attempt, ROOT) != result["decision"]'),
        ('            or result["status"] != "COMPLETE"', '            or not path.samefile(attempt / "terminal.json")\n'
         '            or result["schema"] != "epyc.p5.scorer-control-capture.v1"\n'
         '            or result["status"] != "COMPLETE"'),
        ('    return 0\n\n\nif __name__', '    validate_window(result, attempt)\n    return 0\n\n\nif __name__'),
    ))


def stage(dest, image_receipt):
    require(dest.parent == SCRATCH_ROOT and re.fullmatch(r"[a-z0-9-]+", dest.name)
            and dest.parent.resolve(strict=True) == dest.parent, "expected a new private Vidya scratch directory")
    require(not dest.exists() and not dest.is_symlink(), f"destination already exists: {dest}")
    original_manifest = (SOURCE / "SOURCE.sha256").read_bytes()
    require(sha(original_manifest) == ORIGINAL_MANIFEST, "historical source manifest drift")
    original_hashes = {name: digest for digest, name in (line.split() for line in original_manifest.decode().splitlines())}
    names = {name: (SOURCE / name).read_bytes() for name in FILES}
    for name, contents in names.items():
        require(sha(contents) == original_hashes[name], f"historical scorer source drift: {name}")
    pins = json.loads(names["pins.json"])
    receipt, build_files = official_build(image_receipt, pins)
    names.update(build_files)
    names["historical-SOURCE.sha256"] = original_manifest
    names["historical-pins.json"] = names["pins.json"]
    names["historical-complete.py"] = names["complete.py"]
    pins.update(image_id=receipt["image_id"], image_build_log_sha256=receipt["build_log_sha256"])
    names["pins.json"] = (json.dumps(pins, indent=2) + "\n").encode()
    for name in ("complete.py", "run-controls.py"):
        names[name] = (PACKET / name).read_bytes()
    names["scorer.py"] = native_scorer(names["job.py"].decode())
    names["custody.py"] = native_custody(CUSTODY.read_text())
    manifest = "".join(f"{sha(contents)}  {name}\n" for name, contents in sorted(names.items())).encode()
    preflight = f"""#!/bin/bash
set -euo pipefail
cd {dest}
printf '%s  %s\\n' '{sha(manifest)}' SOURCE.sha256 | sha256sum --check --status
sha256sum --check --status SOURCE.sha256
test -x {PYTHON}
test "$(docker image inspect --format '{{{{.Id}}}}' '{receipt["image_id"]}')" = '{receipt["image_id"]}'
"""
    launch = f"""#!/bin/bash
set -euo pipefail
D={dest}
cd "$D"
printf '%s  %s\\n' '{sha(preflight.encode())}' preflight.sh | sha256sum --check --status
if [[ ${{1:-}} == --job ]]; then
  /bin/bash "$D/preflight.sh"
  unset PYTHONPATH PYTHONHOME PYTHONOPTIMIZE
  exec {PYTHON} -B "$D/custody.py" run
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \\
  --id {ROW} --class cpu --role bench --min-window 300 \\
  --stop "$D/STOP" --workdir "$D" --precond-cmd "/bin/bash $D/preflight.sh" \\
  --cmd "/bin/bash $D/launch.sh --job" --complete-cmd "{PYTHON} -B $D/custody.py complete"
"""
    template = (PACKET / "spec.template.json").read_text().replace("@SCRATCH@", str(dest)).replace("@PYTHON@", PYTHON)
    names.update({"SOURCE.sha256": manifest, "preflight.sh": preflight.encode(),
                  "launch.sh": launch.encode(), "spec.json": template.encode()})
    with tempfile.TemporaryDirectory(prefix=".astropy-stage-", dir=dest.parent) as temporary:
        private = Path(temporary)
        for name, contents in names.items():
            (private / name).write_bytes(contents)
        (private / "launch.sh").chmod(0o750)
        # A concurrent stage or a prior stage's packet must keep its own files.
        dest.mkdir(mode=0o700)
        for name in names:
            shutil.move(private / name, dest / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("--image-receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        stage(args.scratch, args.image_receipt)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"staging refused: {exc}\n")

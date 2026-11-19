#!/usr/bin/env python3
"""Prepare R13 in the existing packet; never write retained units or start inference."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from prepared_inputs import file_identity
from repair_smoke_stop import repair_source

ROW = "hil15b-heavy-18-20-r13-20261119"
OLD_ROW = "hil15b-heavy-06-20-r12-20261105"
OLD_PINS = "/mnt/raid0/llm/tmp/refactor-01a16fc3/hil15b-source-pins-20261105"
PINS = "/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/hil15b-r13"
MODEL = Path("/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf")
MODEL_SHA = "c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131"
PY = "/workspace/repos/epyc-orchestrator/.venv/bin/python"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def replace_one(text, old, new):
    if text.count(old) != 1:
        raise ValueError("expected exactly one occurrence: " + old[:90])
    return text.replace(old, new, 1)


def prepare(packet):
    packet = packet.resolve()
    if (packet / "results-tail-r13").exists():
        raise ValueError("fresh R13 namespace already exists")
    source_pins = (packet / "source.sha256").read_text().splitlines()
    ss = Path(PINS) / "tools/bin/ss"
    subprocess.run([str(ss), "-H", "-ltn", "sport = :18983"], check=True, capture_output=True)
    for line in source_pins:
        sha, path = line.split("  ", 1)
        if digest(path) != sha:
            raise ValueError("source pin mismatch: " + path)
    replacements = {}
    replacements["checkpoint_controller.py"] = repair_source((packet / "checkpoint_controller.py").read_text())
    for name in ("job.sh", "server_bootstrap.py", "native_entry.py", "driver.py"):
        replacements[name] = (packet / name).read_text().replace(OLD_PINS, PINS)
    job = replacements["job.sh"].replace(OLD_ROW, ROW).replace("results-remaining-r12", "results-tail-r13")
    job = replace_one(job, "set -euo pipefail\n", f'set -euo pipefail\nexport PATH="{ss.parent}:$PATH"\n')
    job = replace_one(job, 'sha256sum --quiet -c "$HERE/prior-unit04.sha256"',
                      'sha256sum --quiet -c "$HERE/prior-unit04.sha256"\nsha256sum --quiet -c "$HERE/retained-06-17.sha256"')
    replacements["job.sh"] = job
    bootstrap = replacements["server_bootstrap.py"].replace("results-remaining-r12", "results-tail-r13")
    bootstrap = replace_one(bootstrap, "'unit':'06'", "'unit':'18'")
    bootstrap = replace_one(bootstrap, "unit_index=6", "unit_index=18")
    bootstrap = replace_one(bootstrap, "scope=units-06-20 complete;", "scope=tail-units-18-20 complete; units-06-17 retained in results-remaining-r12;")
    replacements["server_bootstrap.py"] = bootstrap
    native = replacements["native_entry.py"]
    replacements["native_entry.py"] = replace_one(native, "'job.sh',", f"'job.sh','prepared-model.json','prepared-runtime.json','{ss}',")
    observer = (packet / "server_observer.py").read_text()
    start = observer.index("def model_pin(")
    end = observer.index("\ndef observe(", start)
    replacements["server_observer.py"] = observer[:start] + (
        "def model_pin(path,expected_sha):\n"
        "    from prepared_inputs import model_pin as prepared_model_pin\n"
        "    try: return prepared_model_pin(path,expected_sha,Path(__file__).parent/'prepared-model.json')\n"
        "    except (OSError,ValueError) as exc: raise Refusal(str(exc)) from exc\n"
    ) + observer[end:]
    runtime = (packet / "runtime_binding.py").read_text()
    start = runtime.index("def pin():")
    end = runtime.index("\ndef verify(", start)
    replacements["runtime_binding.py"] = runtime[:start] + (
        "def pin():\n"
        "    from prepared_inputs import runtime_pin\n"
        "    record=runtime_pin(Path(__file__).parent/'prepared-runtime.json')\n"
        "    verify(record)\n"
        "    return record\n"
    ) + runtime[end:]
    # Offline content verification happens once, before any row is published.
    before = file_identity(MODEL)
    if digest(MODEL) != MODEL_SHA or file_identity(MODEL) != before:
        raise ValueError("model content or identity mismatch")
    model_receipt = {"schema": "hil15-prepared-model/v1", "path": str(MODEL.resolve()),
                     "sha256": MODEL_SHA, "identity": list(before)}
    subprocess.run([PY, "-S", "-B", "-c",
                    "import json; from pathlib import Path; from runtime_binding import pin; "
                    "r=pin(); r.pop('records'); Path('prepared-runtime.json').write_text(json.dumps(r,sort_keys=True)+'\\n')"],
                   cwd=packet, check=True, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(packet),
                                              "PYTHONDONTWRITEBYTECODE": "1"})
    (packet / "prepared-model.json").write_text(json.dumps(model_receipt, sort_keys=True) + "\n")
    for name, text in replacements.items():
        (packet / name).write_text(text)
    (packet / "prepared_inputs.py").write_bytes(Path(__file__).with_name("prepared_inputs.py").read_bytes())
    # Hash receipts and retained results, never duplicate their contents into the repo.
    retained = []
    for unit in range(6, 18):
        directory = packet / "results-remaining-r12" / f"unit-{unit:02d}"
        if not directory.is_dir():
            raise ValueError("missing retained unit: " + str(directory))
        retained.extend(p for p in directory.rglob("*") if p.is_file())
    (packet / "retained-06-17.sha256").write_text("".join(f"{digest(p)}  {p}\n" for p in sorted(retained)))
    entries = {line.split("  ", 1)[1] for line in source_pins}
    entries.update(str(packet / name) for name in ("prepared_inputs.py", "prepared-model.json", "prepared-runtime.json"))
    entries.add(str(ss))
    (packet / "source.sha256").write_text("".join(f"{digest(p)}  {p}\n" for p in sorted(entries)))
    capsule = [packet / name for name in ("source.sha256", "launcher.sha256", "prior-unit04.sha256", "retained-06-17.sha256")]
    (packet / "capsule.sha256").write_text("".join(f"{digest(p)}  {p}\n" for p in capsule))
    launch = (packet / "launch.sh").read_text().replace(OLD_ROW, ROW).replace("results-remaining-r12", "results-tail-r13")
    launch = replace_one(launch, "80819bb60501e32aeaac678e8843effd619a5d344b6284ed767469982e4b5aa9", digest(packet / "capsule.sha256"))
    (packet / "launch.sh").write_text(launch)
    print(json.dumps({"row": ROW, "launcher_sha256": digest(packet / "launch.sh"),
                      "source_manifest_sha256": digest(packet / "source.sha256"),
                      "retained_files": len(retained), "retained_manifest_sha256": digest(packet / "retained-06-17.sha256")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    prepare(args.packet)

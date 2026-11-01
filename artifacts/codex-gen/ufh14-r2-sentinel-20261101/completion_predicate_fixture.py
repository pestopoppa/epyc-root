import gzip
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import completion_unit as cu

ROW = "ufh14-a3a-single-warm-r2-20261028"

def make_leg(root, name, warm):
    leg = root / name
    (leg / "group").mkdir(parents=True)
    (leg / "proxy-wire").mkdir()
    req = {"request_sha256": "a" * 64}
    group = {"warm_requests": [req] if warm else [], "members": [] if warm else [req]}
    (leg / "group/native-group.json").write_text(json.dumps(group))
    timing = {k: 1.0 for k in cu.REQUIRED_TIMINGS}
    (leg / "group/timing-bindings.json").write_text(json.dumps([{"timings": timing}]))
    (leg / "proxy-wire/wire.jsonl").write_text(json.dumps({"seq": 0}) + "\n")
    with gzip.open(leg / "proxy-wire/wire-bodies.jsonl.gz", "wt") as f:
        f.write(json.dumps({"seq": 0, "body": {}}) + "\n")
    (leg / "cleanup.json").write_text(json.dumps({"server_dead": True, "proxy_dead": True}))

with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "new-packet"
    root.mkdir()
    old = Path(td) / "old-packet"
    old.mkdir()
    old_attempt = old / "attempts/run.legacy"
    old_attempt.mkdir(parents=True)
    (old_attempt / "RUN_COMPLETE.json").write_text(json.dumps({"scope": "fixed historical first requests only"}))
    (old / "RUN_COMPLETE.json").write_text(str(old_attempt / "RUN_COMPLETE.json"))
    assert not cu.production_unit_is_current(root, ROW), "old packet marker cannot complete successor"
    attempt = root / "attempts/run.DryRun123"
    attempt.mkdir(parents=True)
    for name, warm in (("cold", False), ("warm", True)):
        make_leg(attempt, name, warm)
    unit = cu.write_rowflow_unit(attempt, ROW)
    cu.publish_production_marker(root, unit, dry_run=True)
    assert not (root / "RUN_COMPLETE.json").exists()
    assert not cu.production_unit_is_current(root, ROW)
    cu.publish_production_marker(root, unit, dry_run=False)
    assert cu.production_unit_is_current(root, ROW)
    cli = subprocess.run([sys.executable, str(Path(cu.__file__)), "--check-production", str(root), ROW])
    assert cli.returncode == 0
    (attempt / "cold/proxy-wire/wire.jsonl").write_text("tampered\n")
    assert not cu.production_unit_is_current(root, ROW), "unit output tampering must invalidate completion"
    cli = subprocess.run([sys.executable, str(Path(cu.__file__)), "--check-production", str(root), ROW])
    assert cli.returncode != 0

launcher = Path(__file__).with_name("launcher.v15.sh").read_text()
assert "/mnt/raid0/llm/tmp/codex-ufh14-repair-20261028/RUN_COMPLETE.json" not in launcher
assert "--check-production" in launcher
assert "FILLER_DRYRUN_DIR:?}/complete" in launcher
assert "--check-production" in launcher and ROW in launcher
spec = json.loads(Path(__file__).with_name("rowflow-spec.json").read_text())
assert spec["admission_class"] == "diagnostic"
assert spec["regions"] == "mi210_0,72-95,184-191"
assert "--gpu-quiet exclusive --claim-cpus 184-191" in launcher
print("UFH14 current-unit completion predicate: PASS")

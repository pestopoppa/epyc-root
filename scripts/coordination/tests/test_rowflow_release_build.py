"""Release build claims whose only grant record is build.json."""
import json
import os
import subprocess
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

RID = "build-autokernel-20261124T100323Z-cc70ff"
OWNER = "autokernel"


@pytest.fixture
def build_claim(tmp_path):
    grants = tmp_path / "grants"
    grants.mkdir()
    (tmp_path / "ready").mkdir()
    record = grants / (RID + ".build.json")
    record.write_text(json.dumps({"id": RID, "owner": OWNER, "kind": "build",
                                  "quarters": ["q0"], "cpus": "0-23,96-119"}))
    return tmp_path, grants, record


def test_release_build_json_only_cli(build_claim):
    flags, grants, _ = build_claim
    result = subprocess.run(
        [sys.executable, rf.__file__, "--flags", str(flags), "release", RID,
         "--by", OWNER, "--reason", "build finished"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert f"RELEASED {RID}" in result.stdout
    assert f"GRANT-RELEASED {RID}" in result.stdout
    receipt = (grants / (RID + ".ended")).read_text()
    assert "rc=75 " in receipt
    assert "reason=released-early by=autokernel note=build_finished" in receipt
    assert f"job_id={RID}" in receipt
    assert not (grants / (RID + ".grant")).exists()
    with pytest.raises(rf.Refused, match="already ended"):
        rf.release_grant(str(flags), RID, OWNER, "again")


def test_release_build_json_only_requires_owner(build_claim):
    flags, grants, _ = build_claim
    with pytest.raises(rf.Refused, match="only the row owner"):
        rf.release_grant(str(flags), RID, "someone-else", "done")
    assert not (grants / (RID + ".ended")).exists()


def test_release_build_withdrawn_is_idempotent(build_claim):
    flags, grants, record = build_claim
    data = json.loads(record.read_text())
    data["heal_withdrawn"] = True
    record.write_text(json.dumps(data))
    logs = []
    assert rf.release_grant(str(flags), RID, OWNER, "done", log=logs.append, now="fixed") == "RELEASED"
    receipt = (grants / (RID + ".ended")).read_text()
    assert rf.release_grant(str(flags), RID, OWNER, "again", log=logs.append, now="later") == "RELEASED"
    assert (grants / (RID + ".ended")).read_text() == receipt
    assert all(f"GRANT-RELEASED {RID}" in line for line in logs)
    assert len(logs) == 2

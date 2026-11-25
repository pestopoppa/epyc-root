"""AK smoke failures reach the responsible owner even if dedicated routing fails."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import rowflow as rf


def test_smoke_alert_owner_follows_classification(tmp_path, monkeypatch):
    sent = []
    class Notify:
        def smoke_fail(self, flags, rid, path, rec, owner):
            sent.append((owner, json.loads(Path(path).read_text())))

    monkeypatch.setattr(rf, "notify", Notify())
    monkeypatch.setattr(rf, "row_sha", lambda *args: "sha")
    monkeypatch.setattr(rf, "poke_keeper", lambda *args: None)
    launcher = tmp_path / "launcher"
    launcher.write_text("#!/bin/sh\n")
    flags = tmp_path / "flags"
    rid = "akc-example"
    (flags / "dryrun" / rid).mkdir(parents=True)
    d = {"launcher": {"path": str(launcher)}, "owner": "autokernel"}

    # The row owner is ALWAYS told (they must republish); pipeline-mgmt gets a copy only for a
    # harness failure whose dedicated route did not deliver.
    for classification, expected in [({"side": "harness", "routed": False}, ["autokernel", "pipeline-mgmt"]),
                                     ({"side": "harness", "routed": True}, ["autokernel"]),
                                     ({"side": "candidate"}, ["autokernel"]),
                                     ({"side": "unknown"}, ["autokernel"]),
                                     (None, ["autokernel"])]:
        sent.clear()
        monkeypatch.setattr(rf, "ak_failclass", lambda *args, c=classification: c)
        rf.record_fail(str(flags), rid, d, "failure", {})
        assert [o for o, _ in sent] == expected
        assert sent[-1][1].get("failclass") == classification


def test_route_exception_preserves_harness_classification(tmp_path, monkeypatch):
    class Classifier:
        @staticmethod
        def row_dir_from_result_path(path):
            return None

        @staticmethod
        def classify_fail(*args):
            class Result:
                side = "harness"
                def to_dict(self):
                    return {"side": self.side}
            return Result()

        @staticmethod
        def route(*args, **kwargs):
            raise OSError("bus unavailable")

    monkeypatch.setattr(rf, "_failclass_mod", lambda: Classifier)
    result = rf.ak_failclass(str(tmp_path), "akc-example", {}, {})
    assert result == {"side": "harness", "routed": False, "route_error": "OSError: bus unavailable"}

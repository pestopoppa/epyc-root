"""An absent telemetry file is not created or mistaken for existing content."""
import importlib.util
from pathlib import Path

MODULE=Path(__file__).resolve().parents[2]/'scripts/vidya/canary/optional_digest.py'
spec=importlib.util.spec_from_file_location('canary_optional_digest',MODULE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_presence_changes_are_observable_without_creating_file(tmp_path):
    path=tmp_path/'telemetry'
    absent=m.optional_digest(path)
    assert absent == {'present':False,'sha256':None} and not path.exists()
    path.write_bytes(b'')
    empty=m.optional_digest(path)
    assert empty['present'] and empty != absent
    path.write_text('event')
    assert m.optional_digest(path) != empty
    path.unlink()
    assert m.optional_digest(path) == absent

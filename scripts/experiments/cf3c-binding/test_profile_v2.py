"""Refuse drift between the sealed recovery profile and fixed quality cohort."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('binding_prepare_v2', Path(__file__).with_name('prepare_v2.py'))
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def test_v2_keeps_all_quality_cells_and_seals_probe():
    inputs = profile.verify_packet(profile.SCRATCH / 'packet')
    assert profile.RECOVERY_PROBE_V1 is True
    assert 'recovery_probe.py' in inputs['packet_sha256']
    schedule = json.loads((profile.SCRATCH / 'packet/schedule.json').read_text())
    assert schedule == {'coverage': profile.cohort()['schedule']}
    assert len(schedule['coverage']) == 24
    assert all(row['case'] != 'native_recovery_control_v1' for row in schedule['coverage'])
    assert profile.ROW != 'cf3c-binding-20261119'


def test_v2_refuses_probe_byte_drift(tmp_path):
    packet = profile.SCRATCH / 'packet'
    # Immutable module fixtures only; never copy source trees or native logs.
    for name in (*profile.FILES, 'inputs.json'):
        (tmp_path / name).write_bytes((packet / name).read_bytes())
    (tmp_path / 'recovery_probe.py').write_text('# altered probe\n')
    with pytest.raises(ValueError, match='sealed binding file changed: recovery_probe.py'):
        profile.verify_packet(tmp_path)

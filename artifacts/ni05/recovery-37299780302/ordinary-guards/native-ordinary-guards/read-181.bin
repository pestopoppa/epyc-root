from __future__ import annotations

import os

from src.features import Features
from src.runtime import config_attestation


def test_publish_and_read_worker_attestation(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config_attestation, "attestation_dir", lambda: tmp_path)

    path = config_attestation.publish_config_attestation(Features(memrl=True))
    loaded = config_attestation.read_config_attestations([os.getpid(), 999999])

    assert path == tmp_path / f"{os.getpid()}.json"
    assert loaded[os.getpid()]["flags"]["memrl"] is True
    assert 999999 not in loaded

    config_attestation.remove_config_attestation()
    assert not path.exists()

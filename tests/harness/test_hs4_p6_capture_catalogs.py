import asyncio
import hashlib
import json
from pathlib import Path
import sys

import pytest

from scripts.harness import hs4_p6_capture_catalogs as capture


@pytest.fixture
def launches(tmp_path):
    pytest.importorskip("fastmcp")
    paths = []
    for arm in ("baseline", "candidate"):
        source = tmp_path / f"{arm}.py"
        source.write_text(
            'from fastmcp import FastMCP\nmcp = FastMCP("test")\n'
            '@mcp.tool()\ndef existing(value: str) -> str:\n'
            '    raise AssertionError("capture must not call tools")\n'
            + ('@mcp.tool()\ndef added() -> str:\n'
               '    raise AssertionError("capture must not call tools")\n'
               if arm == "candidate" else "")
            + 'mcp.run(transport="stdio")\n'
        )
        spec = {"command": [sys.executable, str(source)], "cwd": str(tmp_path),
                "files": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (Path(sys.executable), source)}}
        path = tmp_path / f"{arm}.json"
        path.write_text(json.dumps(spec))
        paths.append(path)
    return paths


def test_real_stdio_catalogs_preserve_baseline_and_never_call_tools(launches, tmp_path):
    out = tmp_path / "capture"
    receipt = asyncio.run(capture.capture(*launches, out))
    assert receipt["added_tools"] == ["added"]
    assert receipt == json.loads((out / "receipt.json").read_text())
    for arm in ("baseline", "candidate"):
        raw = (out / f"{arm}-tools-list.json").read_bytes()
        assert receipt["catalogs"][arm] == hashlib.sha256(raw).hexdigest()
        assert json.loads(raw)[0]["name"] in {"added", "existing"}


@pytest.mark.parametrize("candidate", [[], [{"name": "old", "inputSchema": {"type": "string"}}],
                                      [{"name": "old"}],
                                      [{"name": "old"}, {"name": "old"}]])
def test_refuses_removal_schema_change_no_growth_and_duplicates(candidate):
    with pytest.raises(ValueError):
        capture.check_growth([{"name": "old", "inputSchema": {}}], candidate)


@pytest.mark.parametrize("mutation", ["source", "spec"])
def test_refuses_drift_during_live_capture(launches, tmp_path, mutation):
    async def reader(spec):
        if "candidate.py" in spec["command"][1]:
            target = Path(spec["command"][1]) if mutation == "source" else launches[0]
            target.write_text(target.read_text() + "\n")
            return [{"name": "old"}, {"name": "new"}]
        return [{"name": "old"}]
    with pytest.raises(ValueError, match="drift"):
        asyncio.run(capture.capture(*launches, tmp_path / "out", reader=reader))
    assert not (tmp_path / "out").exists()


def test_refuses_existing_capture_and_preserves_bytes(launches, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "receipt.json").write_text("original")
    async def reader(spec):
        return ([{"name": "old"}, {"name": "new"}]
                if "candidate.py" in spec["command"][1] else [{"name": "old"}])
    with pytest.raises(FileExistsError):
        asyncio.run(capture.capture(*launches, out, reader=reader))
    assert (out / "receipt.json").read_text() == "original"


def test_transport_failure_cannot_freeze_partial_pair(launches, tmp_path):
    async def reader(spec):
        raise ConnectionError("server unavailable")
    with pytest.raises(ConnectionError):
        asyncio.run(capture.capture(*launches, tmp_path / "out", reader=reader))
    assert not (tmp_path / "out").exists()

#!/usr/bin/env python3
"""Disposable synthetic-only smoke for task8; never opens production source paths."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="hsf3-task8-smoke-", dir=str(HERE)) as td:
    root = Path(td)
    log = root / "synthetic.jsonl"
    private_token = "SYNTHETIC_PRIVATE_SENTINEL_DO_NOT_EMIT"
    log.write_bytes((json.dumps({"event_type": "session_created", "timestamp": "2030-01-01T00:00:00Z",
                                 "data": {"session_id": private_token}}) + "\n" +
                     "[]\n" + "{" + "x" * (1024 * 1024 + 10) + "}\n" + "{" ).encode())
    db = root / "sessions.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE sessions (id TEXT, created_at TEXT, last_checkpoint_at TEXT)")
    conn.execute("CREATE TABLE checkpoints (session_id TEXT, created_at TEXT)")
    conn.execute("INSERT INTO sessions VALUES ('" + private_token + "', 'x', 'y')")
    conn.execute("INSERT INTO checkpoints VALUES ('" + private_token + "', 'x')")
    conn.commit()
    conn.close()
    out = root / "out"
    subprocess.run([sys.executable, str(HERE / "census.py"), "--progress", str(log),
                    "--checkpoint-db", str(db), "--out", str(out)], check=True,
                   stdout=subprocess.DEVNULL)
    result = json.loads((out / "aggregate.json").read_text())
    assert result["progress"]["target_events"] == 1
    assert result["progress"]["invalid_json"] == 1
    assert result["progress"]["oversize_records"] == 1
    assert result["checkpoint_db"]["sessions_rows"] == 1
    assert result["checkpoint_db"]["checkpoints_rows"] == 1
    assert "wal" in result["source_frontiers"][-1]["sqlite_mode"]
    payload = (out / "aggregate.json").read_text()
    assert private_token not in payload
    missing = subprocess.run([sys.executable, str(HERE / "census.py"), "--progress", str(root / "missing-*.jsonl"),
                              "--checkpoint-db", str(db), "--out", str(root / "missing-out")],
                             capture_output=True, text=True)
    assert missing.returncode != 0 and "matched no files" in missing.stderr
    progress_result = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    if progress_result:
        Path(progress_result).parent.mkdir(parents=True, exist_ok=True)
        Path(progress_result).write_text(json.dumps({"progress": {"files": 1}}) + "\n")
print("synthetic-only HSF-3 census smoke: PASS")

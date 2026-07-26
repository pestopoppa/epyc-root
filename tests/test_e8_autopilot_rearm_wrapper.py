"""Focused failure cleanup coverage for the E8 AutoPilot rearm wrapper."""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "artifacts/operator/rearm_e8_autopilot_20260726.sh"


def test_postlaunch_cleanup_terms_then_kills_child_and_supervisor(
    tmp_path: Path,
) -> None:
    log = tmp_path / "signals.log"
    command = f'''\
source "{SCRIPT}"
cleanup_armed=1
child_pid=111
supervisor_pid=222
declare -A alive=([111]=1 [222]=1)
process_alive() {{ [[ "${{alive[$1]:-0}}" == 1 ]]; }}
kill() {{
    printf '%s %s\\n' "$1" "$2" >>"{log}"
    if [[ "$1" == -KILL ]]; then alive[$2]=0; fi
}}
sleep() {{ :; }}
cleanup_after_failed_start
'''

    result = subprocess.run(["bash", "-c", command], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == [
        "-TERM 111",
        "-KILL 111",
        "-TERM 222",
        "-KILL 222",
    ]

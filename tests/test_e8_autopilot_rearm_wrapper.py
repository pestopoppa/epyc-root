"""Focused failure cleanup coverage for the E8 AutoPilot rearm wrapper."""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "artifacts/operator/rearm_e8_autopilot_20260726.sh"


def test_postlaunch_cleanup_terms_then_kills_only_owned_process_groups(
    tmp_path: Path,
) -> None:
    log = tmp_path / "signals.log"
    command = f'''\
source "{SCRIPT}"
cleanup_armed=1
child_pid=111
supervisor_pid=222
child_pgid=111
supervisor_pgid=222
declare -A group_alive=([111]=1 [222]=1 [333]=1 [444]=1)
process_group_alive() {{ [[ "${{group_alive[$1]:-0}}" == 1 ]]; }}
kill() {{
    printf '%s %s %s\\n' "$1" "$2" "$3" >>"{log}"
    if [[ "$1" == -KILL ]]; then group_alive[${{3#-}}]=0; fi
}}
sleep() {{ :; }}
cleanup_after_failed_start
'''

    result = subprocess.run(["bash", "-c", command], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == [
        "-TERM -- -222",
        "-KILL -- -222",
        "-TERM -- -111",
        "-KILL -- -111",
    ]


def test_await_child_ignores_unrelated_concurrent_autopilot_child() -> None:
    command = f'''\\
source "{SCRIPT}"
supervisor_pid=222
process_alive() {{ [[ "$1" == 111 || "$1" == 333 ]]; }}
process_parent_pid() {{
    case "$1" in
        111) printf '222\\n' ;;
        333) printf '444\\n' ;;
    esac
}}
process_group_id() {{ printf '%s\\n' "$1"; }}
pgrep() {{ printf '333\\n111\\n'; }}
await_child
[[ "$child_pid" == 111 ]]
[[ "$child_pgid" == 111 ]]
'''

    result = subprocess.run(["bash", "-c", command], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

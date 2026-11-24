"""The calendar keeper re-pins itself off the MI210 host cores (88-95, threads 184-191) at the top of its loop,
so un-hk'd per-tick children (rowflow allocate) never run on a GPU host core (2026-11-24, core 88 incident)."""
import re
from pathlib import Path

KEEPER = Path(__file__).resolve().parents[1] / "rowflow" / "ws58-calendar-keeper-v13.sh"


def test_keeper_loop_self_pins_to_housekeeping_cpus():
    text = KEEPER.read_text(encoding="utf-8")
    m = re.search(r"^KEEPER_HOUSEKEEPING_CPUS=(\S+)", text, re.M)
    assert m and m.group(1) == "0-87,96-183"
    loop = text.split('while [ "$(date -u +%s)" -lt "$STOP_AT" ]; do', 1)[1].split("\ndone", 1)[0]
    lines = [l.strip() for l in loop.splitlines() if l.strip() and not l.strip().startswith("#")]
    assert lines[0].startswith('taskset -acp "$KEEPER_HOUSEKEEPING_CPUS" $$'), lines[0]

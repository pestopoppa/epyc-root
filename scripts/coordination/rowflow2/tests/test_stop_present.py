"""ROWFLOW2-STOP-PRESENT-FIXTURE (docs/design/rowflow2-20261105.md, STOP-released grant loop): a ready row whose resolved
stop_file exists is skipped and never granted; a grant released unrun by the launcher (its STOP-present exit) counts as an
arming failure and parks the row. Negative controls included."""
import glob
import os

from rf2 import Sim, rf, spec


def _touch_stop(sim, rid):
    p = sim.specs[rid]["stop_file"]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").close()


def test_ready_row_with_present_stop_file_is_skipped_never_granted(tmp_path):
    """lsa-oracle-reference-build-f6dddb7-20261104: stop_file existed, the live keeper re-granted ~1166x. rowflow2 never grants it."""
    rid = "lsa-oracle-reference-build-f6dddb7-20261104"
    sim = Sim(tmp_path)
    assert sim.publish(spec(rid, cpus="q1", threads=12, est=1800)) == []
    _touch_stop(sim, rid)
    for _ in range(60):   # 2 h of ticks
        sim.step()
    assert rid not in sim.granted_ever and not any(f" GRANT {rid} " in x for x in sim.lines)
    assert not glob.glob(os.path.join(sim.flags, "grants", rid + ".*"))
    assert rf.load_world(sim.flags, sim.now).state[rid] == "stopped"


def test_negative_control_without_the_stop_file_the_same_row_is_granted(tmp_path):
    rid = "lsa-oracle-reference-build-f6dddb7-20261104"
    sim = Sim(tmp_path)
    assert sim.publish(spec(rid, cpus="q1", threads=12, est=1800)) == []
    for _ in range(30):
        sim.step()
    assert rid in sim.granted_ever


def test_stop_appears_after_grant_launcher_releases_unrun_counts_as_arming_failure_and_parks(tmp_path):
    """The STOP-released loop: the launcher logs 'STOP present before start: grant released' and deletes the grant, writing no
    .ended. That exit is a refusal: ONE launcher attempt, the row parks, and is not re-granted every tick."""
    rid = "lsa-oracle-reference-build-f6dddb7-20261104"
    sim = Sim(tmp_path)
    assert sim.publish(spec(rid, cpus="q1", threads=12, est=1800), refuse="released") == []
    for _ in range(12):
        if any(f" GRANT {rid} " in x for x in sim.lines):
            break
        sim.step()
    _touch_stop(sim, rid)   # the STOP the launcher found at start
    for _ in range(90):
        sim.step()
    assert len([x for x in sim.lines if f" GRANT {rid} " in x]) == 1
    assert len(sim.refusals) == 1, "the released grant was re-granted: not counted as an arming failure"
    assert glob.glob(os.path.join(sim.flags, "dryrun", rid, "FAIL-refused-*.json"))

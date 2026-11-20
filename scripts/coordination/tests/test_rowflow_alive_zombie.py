import os, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rowflow"))
import rowflow as rf


def test_live_process_is_alive():
    p = subprocess.Popen(["sleep", "5"])
    try:
        assert rf.alive(p.pid)
    finally:
        p.kill(); p.wait()


def test_zombie_is_not_alive():
    p = subprocess.Popen(["true"])
    for _ in range(50):  # not reaped yet: the child is a zombie of this test process
        st = subprocess.run(["ps", "-o", "stat=", "-p", str(p.pid)], capture_output=True, text=True).stdout.strip()
        if st.startswith("Z"):
            break
        time.sleep(0.05)
    assert st.startswith("Z")
    assert not rf.alive(p.pid)
    p.wait()


def test_missing_and_bad_pid():
    assert not rf.alive(0) and not rf.alive(None) and not rf.alive("x")

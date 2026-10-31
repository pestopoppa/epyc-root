"""Retain parent custody while lock-holding adopted children drain themselves."""
import os
import signal
import time
import pidfd_custody_v2 as custody
import pidfd_subreaper_v3 as subreaper

def drain(signalled=None, leader=None, leaders=None):
    """Signal only captured direct children; never kill a possible lock holder."""
    warned = False
    if signalled is None: signalled = set()
    leaders = {} if leaders is None else leaders
    if leader is not None: leaders[leader.pid] = leader
    while True:
        try:
            pids = subreaper.children()
            if not pids:
                return
            for pid in pids:
                try:
                    fd, identity = custody.open_child(pid)
                except ProcessLookupError:
                    continue
                try:
                    # Popen owns its wait status; never consume it via waitid.
                    if pid in leaders and leaders[pid].returncode is None:
                        if leaders[pid].poll() is not None: continue
                    elif subreaper.reap(fd):
                        continue
                    key = (pid, identity["birth"])
                    if key not in signalled:
                        try:
                            # Record first: an exception after delivery must not resend.
                            signalled.add(key)
                            custody.send(fd, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                finally:
                    os.close(fd)
        except Exception as exc:
            if not warned:
                print('owned child drain incomplete; retaining lock custody:', exc, flush=True)
                warned = True
        time.sleep(.1)

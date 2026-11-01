# S2 v15 process custody controls

Two model-free controls exercise the candidate `owned_window.py` with only processes and lock files created by the tests. Ordinary active STOP drains a fake worker and grandchild. In the parent-loss control, the test-owned lock-holder is killed and its fake server remains alive while another holder reacquires the lock: the actual `close_fds=True` spawn does not preserve the old cohort lock across parent death. Both tests pass; the latter is a positive reproduction of a defect, not a safety pass. Independently, a minimal two-lock control demonstrated direct `pass_fds` retention, which does not cover detached descendants.

The candidate must stay disabled until whole descendant lifetime, lock inode identity and native active-stop/drain are proven. These controls do not run a model or touch real scheduler/cohort state. Run from this directory: `python3 -m unittest -v tests/test_owned_window_stop.py tests/test_lock_custody_parent_loss.py`.

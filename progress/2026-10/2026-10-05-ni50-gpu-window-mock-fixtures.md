# NI50 parked GPU-window mock fixtures — 2026-10-05

The bounded off-host run [37352568892](https://github.com/pestopoppa/epyc-root/actions/runs/37352568892) passed the reviewed `test_gpu_window_parked_role.py` selection: 22 collected, 22 passed, no skips, failures, or errors. Main independently reopened the original native receipt and shared projection as Judged/Located. The source candidate is orchestrator commit `8e953994e2d975157bddd24daf1da57ea633a3ed`, changing only `tests/unit/test_gpu_window_parked_role.py`.

The matrix bound the frozen app/root producer and workflow pins, installed from the frozen lock, and preserved original receipt, JUnit, log, and postcheck artifacts under `/mnt/raid0/llm/artifacts/ni18-offhost-fixture-matrix-37352568892/`. It recorded the three configured backend executable paths absent and non-symlink, with the lockfile hash unchanged. These are mocked parked-role fixtures; they make no live KFD, GPU residency, or scheduler observation claim.

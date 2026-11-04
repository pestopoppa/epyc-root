# KPF-18 native-control output supervision qualification

Two model-free tests exercise the pinned successor supervisor and guard snapshots in this directory. Run with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s progress/evidence/kpf18-supervisor-qualification-20261104 -p 'test_*.py' -v`.

The periodic supervisor test injects output-budget failure on its second loop sample and checks rc 75, a PARTIAL receipt with unknown overshoot, and calls to stop and drain the owned child. The guard test exercises the real output-reserve logic against a sparse file grown to the 64 GiB logical cap. Both passed on 2026-11-04. Process control, GPU admission and free-disk readings are mocked; this establishes neither real process cleanup nor a hard quota, bounded overshoot, end-to-end coverage, GPU admission or native-control readiness. Source snapshots are pinned by hashes in the tests; they do not qualify the successor's separately missing or changed historical source inputs.

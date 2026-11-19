# KPF-18 group-3 full driver import

Full row `kvu-kpf18-g3-full-import-20261105` passed, rc=0, ending 2026-11-05T04:00:13Z. The existing verdict and `.FILED` receipt were filed by `h-kvu` at 04:04:50Z that day; the pending handoff note was reconciled on 2026-11-19 without rerunning the row.

The native result reports `IMPORTED`, 20 candidate modules and callable `main`, `setup` and `gate.Run`. The sealed job requires successful source-custody checks before and after import, checks the inventory and launcher seals, and removes its private attempt directory in `finally`; an import, custody or cleanup failure prevents rc=0. The decision rule therefore passes for full import compatibility.

Evidence remains at its original paths:

- Native result: `/mnt/raid0/llm/tmp/kvu/kpf18-g3-full-import-20261105/out/RESULT.json`, SHA-256 `8daac03993890adb94f108c8eb387ef1373d3942db07ecf9cc4f736553ffef8c` (also bound by the filed verdict).
- Filed verdict: `/mnt/raid0/llm/tmp/compute-flags/filing-done/kvu-kpf18-g3-full-import-20261105.verdict.json`.
- Launcher-pinned job: `/mnt/raid0/llm/tmp/kvu/kpf18-g3-full-import-20261105/job.py`, SHA-256 `e80ef6be717a82129c4254998f2cfd56ff44e7f30e01fb492c310b488a64a80f`; worker SHA-256 `0bdb5f18033d041a43f1ca7031b6c6c97a4daa83dee597a80973d8268e1fef1e`.
- Published packet provenance: this directory at commit `21c60e0c0fa942f9c8f77e7dc0404f282603cd11`.

The driver main was never called. The candidate remains disabled. This result establishes import compatibility only; it does not establish native lifecycle, model execution, GPU residency, interval custody, admission or historical control. The group-3 localisation box remains open. [no-belief: scoped model-free software qualification]

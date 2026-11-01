# PB-QCOST confirm-q r2: failed run, 2026-11-01

Run `codex-ni-pbqcost-confirm-q-r2-20261030` ended at 03:17:53 UTC with rc 1: **FAILED-RUN, class harness**. The resource and runtime pin checks passed, but the full-mode wrapper supplied `2026-11-01T04:59:30+00:00`; the native deadline parser rejected it, requiring a UTC `Z` timestamp or `HH:MM`. `run.py` constructs the argument with `datetime.isoformat()`. The failure is before any completed phase: `VERDICT.json` records `phases_done: []`, overall `INCOMPLETE`, label `NOT_RUN`, zero sibling sampler windows, and no coefficients. `RESULT.json` reports `FAILED`, rc 1, wall 0.1203 s, cleanup verified. This is an early harness failure, not a completed native validator failure or evidence of model performance. The records do not establish a confirm or q-axis verdict; no task is closed and no adoption or performance certification follows.

The armed manifest specifies the original 66 requests: ub 512, 256, 1024; n=1 and 4; original exact lengths and repeats; raw wall-clock log-pump intervals at three decimal seconds. Per-n q-coefficient comparison to 0.9865 ms/token uses the original training RMSE tolerance; otherwise the measured coefficient replaces the assumption. Identification requires three q levels and spread >=500 tokens, with held-out interval MAPE <=10%; the original confirmation and amended per-phase CPU 88–95 contention criteria remain in force. These rules were not evaluated here.

Owner action: fix the full-mode deadline serialization to an accepted UTC format, exercise the actual full-mode argument path against the native parser, then rebook the complete unchanged protocol with the original per-phase contention checks. Retain the run as failed evidence; no inference or rescoring is warranted for this attempt.

Evidence retained under `/mnt/raid0/llm/tmp/codex-ni-pbqcost-confirm-q-r2-20261030/`:

- `PREDECLARATION.md` SHA-256 `f45aef1a43976af3d707aea4e7d61875a83e343ec726a61e1725316b385d3e06`; `AMENDMENT-confirm-R.md` SHA-256 `14f4d3c15d46190afa27a5e495350a6d7412defa17f8be330ca2bb2849e4a33f`.
- `run.py` SHA-256 `27aba61f8ce212501dc36978e0715e5c3f7ca339b74cdf31c324cfa907924ca9`; `out/RESULT.json` SHA-256 `bc38fba070d31234a0a8614bcf7ffc8ac5240f87044e3e40e1df61eb3864da27`; `VERDICT.json` SHA-256 `8a5688efcb5c5c6a2e099b030eeb671a127ffc4c128d3c71f168a7cd4de57fd3`.
- `ws58-launcher.out` SHA-256 `bc3d36f34362bd4707b6932ebfb7f97af9029e49b5db98285ad7633073dddfca`; the exact ended record and armed manifest reside in `/mnt/raid0/llm/tmp/compute-flags/grants/` and `ready/armed/`, respectively.

These scratch paths are retained operational evidence, not permanent archives; the bounded facts above do not include the private prompt set.

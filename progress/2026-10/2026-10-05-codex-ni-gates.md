# 2026-10-05 — NIB2-86 Makefile gate contract

Orchestrator source commit `261c6873153b87948e4775c861dd6280fffdc796` makes missing or failing
shellcheck, shfmt, and markdownlint fail their quality gates; adds a check-only shfmt target; removes
nonexistent numerics targets; and moves service-dependent NextPLAID reindexing out of `make gates`.
The six real-Makefile stdlib fixtures passed in off-host CI run `37275807626` (6/6). The devcontainer
image at root commit `7b48473d2a80b5ff1ddf58251d692ab7f50fc4ea` installs shellcheck `0.10.0-1`, shfmt
`3.8.0-1`, and markdownlint-cli `0.49.1`; the actual image/version fixture passed in native CI run
`37282353793`.

Native run `37282353793` truthfully failed `make gates` after schema and shellcheck passed:
check-only shfmt found formatting debt in nine tracked shell scripts, so the ordered lint stage did
not run. A separate actual `make mdlint` case ran and passed in run `37285928039`, so no markdown
cleanup was needed. That run's formatter-copy diagnostic exposed an AST mismatch at
`scripts/diffusion/start_sd_server.sh`; no formatting patch was accepted. The container permission
issue was fixed narrowly with the workflow runner's UID/GID, and run `37287200587` is checking a
recipe that preserves raw before/after typed ASTs, patch, and summary before reporting any mismatch.
The host has none of the three linters on `PATH`; no tools were installed and no local gates or tests
were run.

**Checkbox proposal for NIB2-86:** mark complete. The task was to make the Makefile gates honest and
available in the devcontainer; six fixtures pass, the pinned real tools are installed and verified,
the actual markdownlint target passed, and the static gate fails loudly on existing source-formatting
debt. Track only the nine-file shell formatting debt as NI21, then rerun the real gate after that
patch is reviewed.

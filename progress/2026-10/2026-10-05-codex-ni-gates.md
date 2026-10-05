# 2026-10-05 — NIB2-86 Makefile gate contract

Orchestrator source commit `261c6873153b87948e4775c861dd6280fffdc796` changes Makefile quality gates to
fail when shellcheck, shfmt, or markdownlint is missing or fails; adds a check-only shfmt target; removes
the nonexistent numerics targets; and takes the service-dependent NextPLAID reindex out of `make gates`.
The six real-Makefile stdlib fixtures passed in off-host CI run `37275807626` (6/6). The host currently has
none of those three linters on `PATH`, as read-only `command -v` checks confirmed; I did not install tools,
run `make gates`, or run any local tests.

**Checkbox proposal for the canonical NI05-03 row:** keep NIB2-86 unchecked. Its full canonical task text
also requires installing the linters in the devcontainer; the source commit documents installation but
does not change the devcontainer image or prove a real-tool gate run. The code and fixture substep is
complete, while tool availability and a real `make gates` pass remain. Proposed next action: add the three
linters to the devcontainer, then run `make gates` under the correct host claim and record the real-tool
result. NextPLAID remains an explicit service operation outside local verification gates.

# P6.5 — Retire the legacy Kernel API surface

Date: 2026-11-01<br>
Repository: epyc-root<br>
Implementing commit: `e035bc86917b179de0e17d8c66180c60615849cf`

## Scope and result

Completed P6.5 as written in `handoffs/active/autokernel-rebuild-program.md`.
The `/api/kernel`, `/api/kernel/live`, and `/api/kernel/health` routes are no
longer registered and return HTTP 404. The `kernel` and `kernel_live` sources
are no longer in `dashboard.panels.PANELS`, no longer have registry entries,
and no longer contribute to `/api/health` or its fold. The top-level `kernel`
health alias is removed. `/kernel` keeps its permanent redirect to `/loop`;
the served `/api/loop` and `/api/loop/health` endpoints and their independent
loop/operator-gate envelopes remain intact.

The retired kernel and discovery readers remain available under explicitly
legacy/offline helper names for parser and contract regression tests. Their
metadata is held outside the active registry. This avoids discarding useful
reader coverage while ensuring retired data cannot enter the served routes or
global health fold. No old-reader purge, P6.8 rehosting, or cross-repository
digest repin was included.

Source and caller audit found no in-repository HTTP consumers of the retired
routes. Unknown external clients remain a compatibility risk of the instructed
API retirement; they must migrate to the served `/api/loop` contract where
applicable. The original P6.5 task wording remains in the handoff as the task
identity.

## Verification

Focused acceptance command:

```text
pytest -q tests/test_dashboard_kernel_api_retirement.py \
  tests/test_dashboard_loop_surface.py tests/test_dashboard_panels.py \
  tests/test_dashboard_panels_redteam.py
```

Result: **234 passed, 61 subtests passed** in 41.40 seconds. This covered real
HTTP 404 responses for all three retired API routes; HTTP 200 responses for
`/api/loop` and `/api/loop/health`; registry absence; retired malformed/stale
producer exclusion from the global health fold; and the active loop and
operator-gate behavior.

R6 model-free prep constraints used: nonblocking lock
`/mnt/raid0/llm/tmp/compute-flags/prep-locks/36-37.lock`, CPU set
`36-37,132-133` (physical pair 36–37 and SMT siblings), `OMP_NUM_THREADS=1`,
8 GiB virtual-memory ceiling, and 900-second timeout. The measured focused run
used 171244 KiB maximum resident memory. No inference, native build, or
resource-heavy activity was run.

The initial broader acceptance run also reported seven failures outside this
change. They reproduced unchanged with the lane's original `HEAD` versions of
`dashboard/server.py` and `dashboard/panels.py`, under the same environment:

- `tests/test_dashboard_kernel_freshness_envelopes.py`: `test_a_superseded_bundle_renders_a_loud_verdict_beside_the_number`, `test_a_promoted_past_bundle_renders_the_loud_verdict_too`, `test_an_unverifiable_subject_says_so_and_renders_no_calm_state`, `test_a_relevant_OLD_bundle_renders_CALM`, and `test_an_EXTREME_age_renders_advice_and_stays_calm`.
- `tests/test_production_kernel_set.py`: `test_llama_identity_is_NOT_read_from_the_speech_attestation` and `test_all_four_stable_links_are_projected_and_resolved`; their expectations assume v9 while this host's production kernel is v10.

The source tests and implementation were committed before this artifact so the
implementing SHA above identifies exactly the code/test change. The acceptance
run is recorded as software verification only; no measurement belief is
claimed.

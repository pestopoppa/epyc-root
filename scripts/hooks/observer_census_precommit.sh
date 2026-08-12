#!/bin/bash
# =============================================================================
# observer_census_precommit.sh — commit gate for the OBSERVATION CONTRACT
# =============================================================================
#
# Blocks a commit that adds a watchdog/monitor/health-probe which identifies its
# target by a name/argv pattern without declaring it in
# scripts/coordination/observer_registry.json, or that silently drops a deferral
# for one that already exists.
#
# WHY A HOOK AND NOT A RULE IN A DOC. On 2026-08-12 `bus_supervisor.sh` identified
# a healthy, actively heartbeating coordinator-daemon with an argv pattern that had
# drifted out from under it, declared it dead FOREVER, and relaunch-looped every
# ten seconds for hours with nobody watching. The repo already had the rule written
# down — in that very file, three lines from the code that broke it. A rule decays
# the moment somebody does not read it; the only thing that does not is a check
# that runs whether or not anyone remembers it exists.
#
# WHAT IT IS NOT. It is not the whole measure. The runtime half —
# tests/test_observer_contract.py — drives every adopted watchdog's `observe`
# entrypoint against a REAL process and proves it answers `unobservable` when its
# channels disagree, suppresses corrective action while blind, and still acts when
# its target is genuinely absent. That cannot run in a pre-commit budget. This is
# the fast static half: census hygiene and discovery.
#
# STDLIB ONLY, ON PURPOSE. No pytest, no jq, no venv. A gate that needs a tool
# acquires a third state of its own — "the checker could not run" — and a checker
# for THIS defect class arriving WITH this defect class is not a gate. The only
# hard dependency is python3, whose absence is reported loudly and blocks, because
# in a repo where python3 is missing nothing else works either.
set -uo pipefail

REPO="$(git rev-parse --show-toplevel 2>/dev/null || echo /workspace)"
CENSUS="${REPO}/scripts/coordination/observer_census.py"

# Nothing to enforce in a checkout that does not carry the contract (the sibling
# repos share these hooks and have never carried it). Absence of the file is a
# fact about scope, not a violation.
[[ -f "$CENSUS" ]] || exit 0

if ! command -v python3 >/dev/null 2>&1; then
  printf 'observer census: python3 not found — CANNOT VERIFY, blocking.\n' >&2
  printf '  This gate refuses to pass silently when it cannot run; that failure mode\n' >&2
  printf '  is the exact one it exists to prevent.\n' >&2
  exit 1
fi

python3 "$CENSUS"
exit $?

"""`contention_nway_restricted_count` must reach the contention-gate panel.

The counter is computed in `src/scheduling/contention_gate.py::ContentionGate.evaluate()`
(J4c: the measured N-way matrix can restrict an active role set even when every
pairwise combination in it is ALLOW) and was already wired into
`ContentionGate.metrics_snapshot()` and the `/dashboard/api/contention` JSON payload
(`src/api/routes/dashboard.py::contention_gate_snapshot`). It stopped one layer short
of the operator: `updateContentionGate()` in `dashboard.html` read every other key off
that same payload (`contention_admitted_count`, `contention_timeout_count`,
`contention_degraded_allow_count`, `contention_unknown_pair_count`,
`contention_wait_seconds`) but never `contention_nway_restricted_count` — a number
computed correctly and then dropped by the one function that renders it for a human.

These tests exercise the REAL browser-side renderer (via `node`), not a description of
it, and require the count to carry its denominator (admitted decisions this window) per
`agents/shared/OPERATING_CONSTRAINTS.md` ## Reporting Units — a bare count is a
producer's tick rate, not a claim about the fleet.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

_HTML_PATH = (
    Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
)


def _extract_update_contention_gate() -> str:
    body = _HTML_PATH.read_text()
    start = body.index("async function updateContentionGate(")
    end = body.index("async function updateRegionLocks(", start)
    return body[start:end]


def _run_with_payload(payload: dict) -> str:
    """Execute the real `updateContentionGate()` JS against a stubbed fetch/DOM."""
    fn = _extract_update_contention_gate()
    script = f"""
let _regionLocksRefreshSeq = 1;
const escapeHTML = value => String(value);
const fetchJSON = async () => ({json.dumps(payload)});
const el = {{innerHTML: ''}};
const document = {{getElementById: (id) => (id === 'contention-gate-compact' ? el : null)}};
{fn}
(async () => {{
  await updateContentionGate(1);
  process.stdout.write(JSON.stringify({{html: el.innerHTML}}));
}})().catch(err => {{ console.error(err); process.exit(1); }});
"""
    result = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["html"]


_BASE_PAYLOAD = {
    "matrix_status": "ok",
    "contention_admitted_count": 42,
    "contention_timeout_count": 0,
    "contention_degraded_allow_count": 0,
    "contention_wait_seconds": 1.5,
    "contention_unknown_pair_count": 0,
    "contention_blocked_count": {},
    "per_role_scheduling": {},
}


def test_dashboard_html_reads_nway_restricted_key() -> None:
    """Static guard: the renderer source must reference the payload key at all."""
    fn = _extract_update_contention_gate()
    assert "contention_nway_restricted_count" in fn


def test_nway_restricted_count_reaches_rendered_panel_html() -> None:
    """The real JS renderer must put the count (and its denominator) in the DOM."""
    payload = dict(_BASE_PAYLOAD, contention_nway_restricted_count=3)
    html = _run_with_payload(payload)

    assert "nway-restricted" in html
    assert ">3<" in html
    # Reporting Units: the bare count must carry its denominator (admitted
    # decisions this window), not appear as an unscoped tally.
    assert "3 of 42 admitted decision" in html


def test_nway_restricted_count_zero_does_not_fabricate_a_denominator_mismatch() -> None:
    """Zero case: still rendered (not silently dropped), not colored as a warning."""
    payload = dict(_BASE_PAYLOAD, contention_nway_restricted_count=0)
    html = _run_with_payload(payload)

    assert "nway-restricted" in html
    assert ">0<" in html
    assert "0 of 42 admitted decision" in html

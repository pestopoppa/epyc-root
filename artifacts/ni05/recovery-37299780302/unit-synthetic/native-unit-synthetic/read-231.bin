"""Route-level test for the /dashboard endpoint after Tranche-3 HTML extraction.

Verifies that the route returns the HTML loaded from dashboard.html (the
extracted static file) — guards against the file going missing or the
loader path breaking after future refactors.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def dashboard_route():
    """Import dashboard.py + return the route handler function for /dashboard."""
    from src.api.routes import dashboard

    # Find the GET /dashboard route in the router and return its endpoint
    for route in dashboard.router.routes:
        if getattr(route, "path", None) == "/dashboard":
            return route.endpoint
    pytest.skip("/dashboard route not registered")


def test_dashboard_route_returns_extracted_html(dashboard_route) -> None:
    """The /dashboard endpoint serves the same HTML body that's in dashboard.html."""
    response = asyncio.run(dashboard_route())
    # FastAPI HTMLResponse has .body as bytes
    body = response.body.decode("utf-8") if isinstance(response.body, bytes) else response.body
    expected = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    ).read_text()
    assert body == expected


def test_dashboard_html_response_starts_with_doctype(dashboard_route) -> None:
    response = asyncio.run(dashboard_route())
    body = response.body.decode("utf-8") if isinstance(response.body, bytes) else response.body
    assert body.startswith("<!doctype html>")


def test_dashboard_html_response_ends_with_closing_tags(dashboard_route) -> None:
    response = asyncio.run(dashboard_route())
    body = response.body.decode("utf-8") if isinstance(response.body, bytes) else response.body
    assert body.rstrip().endswith("</body></html>")


def test_dashboard_html_file_exists_at_expected_path() -> None:
    """The extracted dashboard.html file must live alongside dashboard.py."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    assert html_path.exists()
    assert html_path.stat().st_size > 40_000  # ~43KB after extraction


def test_dashboard_html_loaded_at_module_import() -> None:
    """_DASHBOARD_HTML constant in dashboard.py should be populated."""
    from src.api.routes import dashboard

    assert len(dashboard._DASHBOARD_HTML) > 40_000


def test_dashboard_html_distinguishes_waiting_tap_from_active_locks() -> None:
    """The live tap can show CPU-lock wait states without counting them as holders."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "waiting_cpu_lock" in body
    assert "structuredTapPrimaryRole" in body
    assert "function inferStructuredTapLockIdentity(req, byRole = null)" in body
    assert "const topoNode = (topology && Number.isFinite(port))" in body
    assert "const roleCandidates = [" in body
    assert "roleCandidates.find(r => byRole[r])" in body
    assert "status === 'quiet'" in body
    assert "every overlap as locked" in body
    assert "must not make an" in body
    assert "occupied CPU region look physically free" in body
    assert "lockOnlyStructuredTapHolders" in body
    assert "chat.* tap absent" in body
    assert "holders · ${tapped} tapped · ${offTap} off-tap" in body
    assert "live tap request(s)" in body
    assert "prefill/decode pending" in body
    assert "tapLiveRequestCount" in body
    assert "buildTapInferredRegionLocks" not in body
    assert "TAP ACTIVE" not in body


def test_dashboard_html_live_tap_ignores_stale_region_lock_frames() -> None:
    """Aborted lock refreshes must not leave stale blockers on newer tap rows."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "let _latestRegionLockFrame = { valid: false" in body
    assert "const _REGION_LOCK_TAP_FRESH_S = 20;" in body
    assert "function latestRegionLockFrameUsableForTap(req = null)" in body
    assert "_REGION_LOCK_TAP_REQ_SKEW_S" not in body
    assert "structuredTapRequestStartEpoch" not in body
    assert (
        "if (!req || !_latestRegionLocksByRole || !latestRegionLockFrameUsableForTap(req)) return false;"
        in body
    )
    assert (
        "if (!req || !_latestRegionLocksByRole || !latestRegionLockFrameUsableForTap(req)) return [];"
        in body
    )
    assert "if (!latestRegionLockFrameUsableForTap()) return [];" in body
    assert body.index("if (!hasOutput && lockActive)") < body.index(
        "if (quietS >= _STRUCTURED_TAP_STALLED_S)"
    )
    assert "long prompt prefill may produce no tap chunks until the first token" in body
    assert "generatedAt: Number((((d.live_frame || {}).observed_at || {}).tap)" in body
    assert "frameId," in body
    assert "source: regionLocks ? 'snapshot' : 'direct'" in body
    assert (
        "_latestRegionLockFrame = { valid: false, generatedAt: 0, appliedAtMs: Date.now(), source: 'error' };"
        in body
    )


def test_dashboard_html_copy_snapshot_stays_on_the_click_activation_path() -> None:
    """Copy should build synchronously and fall back to execCommand when needed."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    start = body.index("function copySnapshotFallback(text) {")
    end = body.index("async function downloadSnapshot() {")
    copy_body = body[start:end]

    assert "const text = buildTextSnapshot();" in copy_body
    assert "await navigator.clipboard.writeText(text);" in copy_body
    assert "document.execCommand('copy')" in copy_body
    assert "fetch(`/dashboard/api/task/" not in copy_body
    assert "clipboard write failed:" in copy_body


def test_dashboard_task_detail_renders_available_input_image() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    detail_start = body.index("async function openDetail(taskId, port, slotId) {")
    detail_end = body.index("function closeDetail()", detail_start)
    detail_body = body[detail_start:detail_end]

    assert "if (image.available && image.url)" in detail_body
    assert 'class="task-image-frame"' in detail_body
    assert 'src="${escapeHTML(image.url)}"' in detail_body
    assert "image.reason" in detail_body


def test_dashboard_task_detail_uses_terminal_answer_when_tap_is_empty() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    detail_start = body.index("async function openDetail(taskId, port, slotId) {")
    detail_end = body.index("function closeDetail()", detail_start)
    detail_body = body[detail_start:detail_end]

    assert "const terminalAnswer = (d.terminal_answer || '').toString();" in detail_body
    assert "if (!initialContent && terminalAnswer)" in detail_body
    assert "final answer (task event)" in detail_body


def test_dashboard_html_separates_placement_leases_from_live_tap_requests() -> None:
    """The lock panel distinguishes canonical leases from tap inference."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "leaseHolderCount" in body
    assert "tapInferredCount" in body
    assert "slotInferredCount" in body
    assert "tapLiveStateBits" in body
    assert "live tap request(s)" in body
    assert "placement lease instance(s)" in body
    assert "placement telemetry conflict" in body
    assert "structuredTapLockCandidates" in body
    assert "shared cohorts use the atomic occupancy ledger" in body
    assert "tap rows into synthetic lock holders" in body
    assert "tap-inferred request(s)" not in body


def test_dashboard_html_keeps_tap_rows_out_of_lock_ownership() -> None:
    """Live tap rows describe work but cannot synthesize placement leases."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "function structuredTapLockCandidates()" in body
    assert "shared cohorts use the atomic occupancy ledger" in body
    assert "visible work, but it must not synthesize lock ownership" in body
    assert "function buildTapInferredRegionLocks" not in body
    assert "tap-inferred" not in body


def test_dashboard_html_proc_summary_has_no_tap_merge_state() -> None:
    """The proc holder summary should not read a synthetic tap-inferred map."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    summary_start = body.index("function formatRegionLockHolderSummary()")
    summary_end = body.index("function refreshLiveDotsFromStructuredTap()")
    summary_body = body[summary_start:summary_end]

    assert "procRegionLockHolders().map" in summary_body
    assert "openStructuredTapRequests().some" in summary_body
    assert (
        "formatPhysicalRoleWithLogicalAliases(holder.role, holder.shape, holder.idx)"
        in summary_body
    )
    assert "Inferred" not in summary_body


def test_dashboard_html_region_lock_summary_is_proc_payload_only() -> None:
    """The Regions Lock header should not synthesize holders from tap rows."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "function formatRegionLockHolderSummary()" in body
    assert "const displayHeldBySummary = formatRegionLockHolderSummary();" in body
    summary_start = body.index("function formatRegionLockHolderSummary()")
    summary_end = body.index("function refreshLiveDotsFromStructuredTap()")
    summary_body = body[summary_start:summary_end]
    assert "procRegionLockHolders().map" in summary_body
    assert "_latestTapInferredRegionLocksByRole" not in summary_body
    assert "tapInferredHolderLabel" not in body
    assert "buildTapInferredRegionLocks" not in body


def test_dashboard_html_region_lock_grid_uses_backend_display_matrix() -> None:
    """The normal lock-grid renderer should consume the backend display_matrix."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "function renderRegionLocksDisplayMatrix(grid, d)" in body
    assert "const matrix = d && d.display_matrix ? d.display_matrix : null;" in body
    assert "row.label || row.role" in body
    assert "configured and free" in body
    assert "× overlaps an active CPU placement lease" in body
    assert "× cells overlap active placement leases" in body
    assert "invalid placement telemetry provenance" in body
    assert "serving-capacity telemetry conflict" in body
    assert "configured but not selected by this launch mode" not in body
    assert "const matrixPainted = renderRegionLocksDisplayMatrix(grid, d);" in body
    assert (
        "backend display_matrix unavailable; lock-grid rendering is intentionally disabled" in body
    )
    assert "using by_role fallback" not in body
    assert "display_matrix render failed" in body
    assert "renderRegionLocksBasicGrid(grid," not in body
    assert "pickInstForCol" not in body
    assert "SLOT ACTIVE" not in body


def test_region_lock_primer_cannot_overwrite_a_coupled_frame() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    update_start = body.index("async function updateRegionLocks(")
    update_end = body.index("async function ensureRegionLocksPanelPainted()", update_start)
    update_function = body[update_start:update_end]
    primer_start = update_end
    primer_end = body.index("function startPanelSafely", primer_start)
    primer_function = body[primer_start:primer_end]

    assert "if (refreshSeq !== _regionLocksRefreshSeq) return;" in update_function
    assert "if (!incomingFrameId && _latestRegionLockFrame.valid) return;" in update_function
    assert "fetchJSON('/dashboard/api/region_locks')" not in primer_function
    assert "requestCoherentDashboardSnapshot('region_locks_primer');" in primer_function

    script = f"""
let _regionLocksRefreshSeq = 7;
let _latestRegionLockFrame = {{valid:true, frameId:'live-coupled'}};
let touched = false;
const fetchJSON = async () => {{ throw new Error('standalone fetch forbidden'); }};
const document = {{getElementById: () => {{ touched = true; throw new Error('painted'); }}}};
{update_function}
(async () => {{
  await updateRegionLocks(7, {{live_frame: {{frame_id:null}}}});
  process.stdout.write(JSON.stringify({{touched, frame:_latestRegionLockFrame.frameId}}));
}})().catch(err => {{ console.error(err); process.exit(1); }});
"""
    proc = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(proc.stdout) == {"touched": False, "frame": "live-coupled"}


def test_region_lock_renderer_replaces_owner_and_frame_identity() -> None:
    """Actual JS renderer must replace stale role HTML on every frame."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    start = body.index("function renderRegionLocksDisplayMatrix")
    end = body.index("\nfunction rememberStructuredTapAccordion", start)
    renderer = body[start:end]
    script = f"""
const _latestSnapshot = {{activity: {{}}, topology: {{nodes: []}}}};
const escapeHTML = value => String(value);
const gpuDeviceRegionRows = () => [];
const document = {{createElement: () => ({{style: {{}}, innerHTML: ''}})}};
{renderer}
const grid = {{dataset: {{}}, style: {{}}, innerHTML: '', appendChild(el) {{ this.innerHTML += el.innerHTML; }}}};
const payload = (frame, role, count) => ({{
  live_frame: {{frame_id: frame, observed_at: {{tap: Number(frame.slice(1))}}}},
  display_matrix: {{
    columns: [{{key: 'full', label: 'Full'}}], row_kind: 'role', launch_mode: 'both',
    rows: ['frontdoor', 'worker_general'].map(name => ({{
      role: name,
      cells: [name === role
        ? {{state: 'active', label: `🔒 ${{count}}/4 lease · ⚙ ${{count}}/4 slots · ✦ ${{count}} tap`, load: count / 4}}
        : {{state: 'ready', label: '✅'}}],
    }})),
  }},
}});
const out = [];
for (const [frame, role, count] of [['f1','frontdoor',2], ['f2','worker_general',2], ['f3','frontdoor',1]]) {{
  renderRegionLocksDisplayMatrix(grid, payload(frame, role, count));
  out.push({{frame:grid.dataset.liveFrameId, html:grid.innerHTML}});
}}
process.stdout.write(JSON.stringify(out));
"""
    result = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    frames = json.loads(result.stdout)

    assert [item["frame"] for item in frames] == ["f1", "f2", "f3"]
    assert "frontdoor" in frames[0]["html"] and "🔒 2/4" in frames[0]["html"]
    assert "worker_general" in frames[1]["html"] and "🔒 2/4" in frames[1]["html"]
    assert "🔒 1/4" in frames[2]["html"]
    assert frames[0]["html"] != frames[1]["html"] != frames[2]["html"]


def test_snapshot_poll_budget_covers_retrying_server_fanout_and_surfaces_timeout() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    timeout_line = next(
        line for line in body.splitlines() if "const _SNAPSHOT_POLL_TIMEOUT_MS =" in line
    )
    timeout_ms = int(timeout_line.split("=", 1)[1].strip().rstrip(";"))
    watchdog_line = next(
        line for line in body.splitlines() if "const _SNAPSHOT_WATCHDOG_STALL_MS =" in line
    )
    watchdog_ms = int(watchdog_line.split("=", 1)[1].strip().rstrip(";"))

    # A torn placement window permits two bounded 10s /slots fan-outs. The
    # poll covers both plus overhead, and self-heal must not cancel retry #2.
    assert timeout_ms == 30_000
    assert timeout_ms > 2 * 10_000 > 9_000
    assert watchdog_ms == 35_000
    assert watchdog_ms > timeout_ms
    assert "renderSnapshotTransportError(err);" in body

    helper_start = body.index("function renderSnapshotTransportError(err)")
    helper_end = body.index("\nfunction updatePanelSafely", helper_start)
    helper = body[helper_start:helper_end]
    script = f"""
const _SNAPSHOT_POLL_TIMEOUT_MS = {timeout_ms};
const status = {{textContent:'— loading CPU region-lock matrix…', style:{{}}}};
const badge = {{textContent:'', className:'', title:'', dataset:{{}}}};
const document = {{getElementById: id => id === 'region-locks-status' ? status : badge}};
{helper}
const err = new Error('This operation was aborted');
err.name = 'AbortError';
renderSnapshotTransportError(err);
process.stdout.write(JSON.stringify({{status, badge}}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = json.loads(result.stdout)

    assert "timed out after 30s" in rendered["status"]["textContent"]
    assert rendered["badge"]["textContent"] == "⚠ transport timeout"
    assert rendered["badge"]["dataset"]["panelError"] == "region_locks"


def test_region_render_error_replaces_loading_state_with_exact_diagnostic() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    constant_line = next(
        line for line in body.splitlines() if "const _REGION_LOCK_DIAGNOSTIC_BUILD =" in line
    )
    render_start = body.index("function renderPanelErrorChip(name, err)")
    render_end = body.index("\nfunction clearPanelErrorChip", render_start)
    renderer = body[render_start:render_end]
    script = f"""
const _PANEL_ERROR_BADGE_KEYS = {{region_locks:'region_locks'}};
{constant_line}
const _buildRevLoaded = {{git_sha:'9b85bc7'}};
const badge = {{textContent:'', className:'', title:'', dataset:{{}}}};
const status = {{textContent:'— loading CPU region-lock matrix…', style:{{}}}};
const grid = {{innerHTML:'', dataset:{{}}, style:{{}}}};
const elements = {{'fresh-region_locks':badge, 'region-locks-status':status, 'region-locks-grid':grid}};
const document = {{getElementById: id => elements[id] || null}};
const window = {{}};
const console = {{error(){{}}}};
const escapeHTML = value => String(value).replaceAll('<', '&lt;').replaceAll('>', '&gt;');
{renderer}
renderPanelErrorChip('region_locks', new ReferenceError('activity is not defined'));
process.stdout.write(JSON.stringify({{badge, status, grid, last:window.__dashboardLastPanelError}}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = json.loads(result.stdout)

    diagnostic = "region lock render error [git 9b85bc7]: activity is not defined"
    assert rendered["status"]["textContent"] == f"— {diagnostic}"
    assert diagnostic in rendered["grid"]["innerHTML"]
    assert rendered["grid"]["dataset"]["regionLocksPainted"] == "1"
    assert rendered["badge"]["textContent"] == "⚠ render error"
    assert rendered["last"]["message"] == "activity is not defined"


def test_full_dashboard_script_snapshot_can_resolve_region_lock_writer() -> None:
    """Exercise the real lexical scope, not an extracted renderer function."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    script_start = body.index("<script>\nconst NODE_RADIUS") + len("<script>\n")
    script_end = body.index("\n</script>", script_start)
    dashboard_script = body[script_start:script_end]
    harness = f"""
const vm = require('vm');
const elements = {{
  'topology-strip': {{dataset:{{}}, children:[{{}}]}},
  'status': {{textContent:''}},
}};
let domReadyHandler = null;
const document = {{
  readyState:'loading',
  addEventListener(name, handler) {{ if (name === 'DOMContentLoaded') domReadyHandler = handler; }},
  getElementById:id => elements[id] || null,
  querySelectorAll:() => [],
}};
const window = {{addEventListener(){{}}}};
const localStorage = {{getItem:() => null, setItem(){{}}, removeItem(){{}}}};
const sessionStorage = {{getItem:() => null, setItem(){{}}, removeItem(){{}}}};
const context = {{
  document, window, console, Date, Math, JSON, Promise, Map, Set, URLSearchParams,
  AbortController, TextDecoder, setTimeout, clearTimeout, setInterval, clearInterval,
  localStorage, sessionStorage,
}};
context.globalThis = context;
vm.createContext(context);
vm.runInContext({json.dumps(dashboard_script)}, context);
vm.runInContext(`
  updateTopology = () => {{}};
  updateContentionGate = () => {{}};
  updateCounters = () => {{}};
  updateTasks = () => {{}};
  updateDecisions = () => {{}};
  activeStream = null;
  _latestRegionLockFrame = {{valid:true, frameId:'existing-coupled'}};
  window.__dashboardLastPanelError = null;
  applyDashboardSnapshot({{
    generated_at:100,
    region_locks:{{live_frame:{{frame_id:null}}}},
    activity:{{}},
    in_flight_tasks:[],
  }}, 'stream');
`, context);
process.stdout.write(JSON.stringify({{
  writerType:vm.runInContext('typeof updateRegionLocks', context),
  startupType:vm.runInContext('typeof startDashboard', context),
  domReadyHandlerType:typeof domReadyHandler,
  lastError:context.window.__dashboardLastPanelError,
}}));
"""
    result = subprocess.run(
        ["node", "-"],
        input=harness,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    rendered = json.loads(result.stdout)

    assert rendered["writerType"] == "function"
    assert rendered["startupType"] == "function"
    assert rendered["domReadyHandlerType"] == "function"
    assert rendered["lastError"] is None


def test_valid_live_region_frame_clears_stale_error_and_paints_full_matrix() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()
    clear_start = body.index("function clearPanelErrorChip(name)")
    clear_end = body.index("\nfunction renderSnapshotTransportError", clear_start)
    clear_helper = body[clear_start:clear_end]
    renderer_start = body.index("function renderRegionLocksDisplayMatrix")
    renderer_end = body.index("\nfunction rememberStructuredTapAccordion", renderer_start)
    renderer = body[renderer_start:renderer_end]
    update_start = body.index("async function updateRegionLocks(")
    update_end = body.index("async function ensureRegionLocksPanelPainted()", update_start)
    update_function = body[update_start:update_end]

    script = f"""
const badge = {{textContent:'⚠ render error', className:'freshness-badge stale', title:'old', dataset:{{panelError:'region_locks'}}}};
const status = {{textContent:'— loading CPU region-lock matrix…', style:{{}}, dataset:{{}}}};
const grid = {{dataset:{{}}, style:{{}}, innerHTML:'', appendChild(el) {{ this.innerHTML += el.innerHTML; }}}};
const dot = {{classList:{{remove(){{}}, add(){{}}}}, title:''}};
const elements = {{'fresh-region_locks':badge, 'region-locks-status':status, 'region-locks-grid':grid, 'region-locks-dot':dot}};
const document = {{
  getElementById: id => elements[id] || null,
  createElement: () => ({{style:{{}}, innerHTML:''}}),
}};
const window = {{__dashboardLastPanelError:{{name:'region_locks', message:'old renderer failure'}}}};
const _PANEL_ERROR_BADGE_KEYS = {{region_locks:'region_locks'}};
let _regionLocksRefreshSeq = 4;
let _latestRegionLockFrame = {{valid:false, generatedAt:0, appliedAtMs:0, source:'error'}};
let _latestRegionLocksByRole = {{}};
let _lastRegionLocksPayload = null;
let _latestRegionLockActivitySignature = '';
let _latestRegionLockSummary = null;
const _latestSnapshot = {{activity:{{'8083':{{n_active:1}}}}, topology:{{nodes:[]}}, in_flight_tasks:[]}};
const _rawTapRenderMode = 'structured';
const escapeHTML = value => String(value == null ? '' : value);
const fetchJSON = async () => {{ throw new Error('unexpected fetch'); }};
const liveStructuredTapRequests = () => [];
const structuredTapActivity = () => ({{state:'queued'}});
const paintRawTap = () => {{}};
const formatRegionLockHolderSummary = () => 'frontdoor.half0';
const renderAutopilotRunStrip = () => {{}};
const _setDotState = () => {{}};
const regionLockNoHolderContext = () => ({{busy:false, text:'fleet idle'}});
const regionLockPayloadFrameEpoch = () => 100;
const gpuDeviceRegionRows = () => [];
const liveFrameFreshness = () => ({{generated_at:100, staleness_class:'fresh'}});
const setPanelFreshness = () => {{ badge.textContent='live'; badge.className='freshness-badge fresh'; badge.title='healthy'; }};
const updateTopologyInflight = () => {{}};
{clear_helper}
{renderer}
{update_function}
const payload = {{
  per_region_locks_enabled:true,
  by_role:{{frontdoor:{{wired:true, active_instance_idxs:[1], instances:[{{idx:1, shape:'half0'}}], regions:[{{region:'q0', held:true, holder_pids:['77'], holder_instance_idxs:[1]}}]}}}},
  placement_telemetry:{{status:'coherent', conflict:false, capacity_conflicts:[]}},
  coherence:{{status:'coherent'}},
  lock_root:{{suspicious_test_root:false}},
  live_frame:{{frame_id:'live-e12', status:'coherent', reason:'signals agree', observed_at:{{tap:100}}, reconciliation:{{status:'agreement'}}}},
  display_matrix:{{
    columns:[{{key:'full',label:'Full'}},{{key:'half0',label:'Half0'}},{{key:'half1',label:'Half1'}}],
    row_kind:'role', launch_mode:'both',
    rows:[
      {{role:'frontdoor', cells:[{{state:'blocked',label:'×'}},{{state:'active',label:'🔒 1/1 lease · ⚙ 1/1 slots',load:1}},{{state:'na',label:'—'}}]}},
      {{role:'architect_general',label:'architect_general :8083',ports:[8083],no_lock_domain:true,lock_state:'n/a (no lock domain)',cells:[{{state:'nolock',label:'▣ GPU (MI210)'}},{{state:'na',label:'—'}},{{state:'na',label:'—'}}]}},
    ],
  }},
}};
(async () => {{
  await updateRegionLocks(4, payload, 9, []);
  process.stdout.write(JSON.stringify({{
    badge, status, gridHtml:grid.innerHTML, gridFrame:grid.dataset.liveFrameId,
    latest:_latestRegionLockFrame, lastError:window.__dashboardLastPanelError,
  }}));
}})().catch(err => {{ console.error(err); process.exit(1); }});
"""
    result = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = json.loads(result.stdout)

    assert rendered["gridFrame"] == "live-e12"
    assert "frontdoor" in rendered["gridHtml"]
    assert "linear-gradient" in rendered["gridHtml"]
    assert "architect_general :8083" in rendered["gridHtml"]
    assert rendered["latest"]["valid"] is True
    assert rendered["badge"]["textContent"] == "live"
    assert "panelError" not in rendered["badge"]["dataset"]
    assert rendered["lastError"] is None
    assert "loading CPU region-lock matrix" not in rendered["status"]["textContent"]


def test_coupled_panels_advance_freshness_only_after_same_frame_paint() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "function liveFrameFreshness(snap)" in body
    assert "grid.dataset.liveFrameId = frameId;" in body
    assert "strip.dataset.liveFrameId = String(snap.frame_id || 'unknown');" in body
    assert "tapPanel.dataset.liveFrameId = String(snap.frame_id || 'unknown');" in body
    assert "setPanelFreshness('region_locks', liveFrameFreshness" in body
    assert "setPanelFreshness('topology', liveFrameFreshness(snap));" in body
    assert "setPanelFreshness('inference_tap', liveFrameFreshness(snap));" in body
    assert "setPanelFreshness('region_locks', snap._freshness)" not in body
    assert "setPanelFreshness('topology', snap._freshness)" not in body
    assert "paintTap: false" in body
    assert "? slots unknown" in body
    assert "? partial /slots" in body
    assert "const reconciliation = frame.reconciliation || {};" in body
    assert "reconciliation.status === 'drift'" in body
    assert "event history was not overwritten" in body
    assert "updateTopologyFlow(inflight, snapshotSeq, liveFrame || {});" in body
    assert "route → lease → backend → output" in body
    assert "API lifecycle seq" in body
    assert "Unresolved remains nonzero until the handler finally exits." in body


def test_dashboard_run_state_active_inference_overrides_quiet_log() -> None:
    """Active tap/lock work should not render the top run-state as quiet."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "activeInferenceCount > 0 || activeLockCount > 0" in body
    assert "runState = 'inference active'" in body
    assert "runState = hasActiveInference ? 'orphan inference' : 'down'" in body


def test_dashboard_autopilot_log_render_dedupes_adjacent_lines() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "function _dedupeAdjacentAutopilotLines(lines)" in body
    assert "_dedupeAdjacentAutopilotLines(_autopilotLogBuffer.split('\\n'))" in body


def test_dashboard_planner_status_distinguishes_history_from_active_stream() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "function _plannerTapStatusText(lines)" in body
    assert "planner history · autopilot stopped" in body
    assert "planner active" in body
    assert "plannerStatus.textContent = _plannerTapStatusText(plannerLines);" in body


def test_dashboard_surfaces_realized_numa_mode_provenance_badge() -> None:
    """C1/M2: the topology panel must carry a provenance badge that renders the
    realized-fleet-first NUMA mode, its source, and any lower-precedence
    disagreement (so a lying env can never silently invert fleet health again)."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert 'id="topology-numa-badge"' in body
    assert "function updateTopologyNumaBadge(topo)" in body
    assert "updateTopologyNumaBadge(topo);" in body
    assert "topo.stack_numa_mode_provenance" in body
    assert "numa-mode-warn" in body


def test_dashboard_topology_activity_stats_refresh_with_live_age_tick() -> None:
    """Topology activity text should not lag behind lock/tap freshness signals."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "TOPOLOGY_ACTIVITY_WINDOW_S = 60" in body
    assert "TOPOLOGY_ACTIVITY_AGE_TICK_MS = 1000" in body
    assert "topologyActivityAgeS" in body
    assert "renderTopologyActivity" in body
    assert "requestCoherentDashboardSnapshot('topology_activity_refresh')" in body
    assert (
        "fetchJSON(`/dashboard/api/topology_activity?window_s=${TOPOLOGY_ACTIVITY_WINDOW_S}`)"
        not in body
    )
    assert "scheduleRegionLocksRefresh(true)" in body
    assert "snap.region_locks" in body
    assert "const snapshotSeq = ++_latestSnapshotSeq;" in body
    assert (
        "return updateRegionLocks(refreshSeq, snap.region_locks, snapshotSeq, snap.in_flight_tasks || [])"
        in body
    )
    assert "const refreshSeq = ++_regionLocksRefreshSeq;" in body
    assert "updatePanelSafely('contention', () => updateContentionGate(refreshSeq));" in body
    assert (
        "function updateTopology(activity, inflight, snapshotSeq = null, liveFrame = null)" in body
    )
    assert "snap.activity || {}" in body
    assert "snap.live_frame || {}" in body
    assert "let _latestStructuredTapFrameTs = 0;" in body
    assert "function applyStructuredTapFrame(data, {" in body
    assert "if (Array.isArray(snap.structured_requests))" in body
    assert "applyStructuredTapFrame(snap, {" in body
    assert "requestSnapshot: false" in body
    assert "acceptCoherentSnapshot: true" in body
    assert (
        "if (!acceptCoherentSnapshot && frameTs + 0.001 < _latestStructuredTapFrameTs) return false;"
        in body
    )
    assert "tap activity and proc/payload lock state share one frame" in body
    assert "let _topologyActivityRefreshSeq = 0;" in body
    assert (
        "async function updateTopologyActivity(refreshSeq = ++_topologyActivityRefreshSeq)" in body
    )
    assert (
        "if (snap.topology_activity) applyTopologyActivityPayload(snap.topology_activity);" in body
    )
    assert "idle, not an active-holder signal" in body
    assert 'last <span class="stat-stale">${formatTopologyActivityAge(age)}</span>' in body
    assert "not an active-holder signal" in body
    assert "historical avg ${stats.avg_tps_recent.toFixed(2)} t/s" in body
    assert 'history <span class="stat-stale">${nCompleted}</span> done' in body
    assert "t/s hist" in body
    assert "servers up${suffix}" in body
    assert "setInterval(() => scheduleRegionLocksRefresh(true), 1500)" in body
    assert "setInterval(renderTopologyActivity, TOPOLOGY_ACTIVITY_AGE_TICK_MS)" in body
    assert "lockActivitySignature" in body
    assert "const liveActiveCount = Math.max(lockActiveCount, tapActiveCount);" in body
    assert "active CPU-region/tap holder(s)" in body
    assert "request/tps fields are recent history from the same coherent snapshot" in body
    assert "recent req" in body
    assert "live req" not in body
    assert "historical summary ${stats.avg_tps_recent.toFixed(2)} t/s" in body
    assert "renderRegionLocksBasicGrid(grid, d);" not in body
    assert "grid.dataset.regionLocksPainted = '1';" in body
    assert "waiting for coherent lock metadata" in body
    assert "but no CPU lock holder correlated in this frame" in body
    assert "loading CPU region-lock matrix" in body
    assert "function startPanelSafely(name, fn)" in body
    assert "startPanelSafely('region-locks-primer', ensureRegionLocksPanelPainted);" in body
    assert (
        "startPanelSafely('region-locks-refresh', () => scheduleRegionLocksRefresh(true));" in body
    )
    assert "startPanelSafely('topology', loadTopology);" in body
    assert "startPanelSafely('snapshot-poll', updateSnapshotPoll);" in body
    assert "setTimeout(ensureRegionLocksPanelPainted, 750)" in body
    assert "_latestSnapshot = snap || {};" in body
    assert "it must not synthesize lock ownership" in body
    assert "tap rows into synthetic lock holders" in body
    assert "Tap PIDs identify backend llama-server processes" in body
    assert "active.instanceIdxs && active.instanceIdxs.has(Number(idx))" in body
    assert "function requestCoherentDashboardSnapshot(reason = '')" in body
    assert "requestCoherentDashboardSnapshot('structured_tap')" in body
    assert "function structuredTapLogicalAliasesForIdentity(role, idx)" in body
    assert "formatPhysicalRoleWithLogicalAliases(holder.role, holder.shape, holder.idx)" in body
    assert "logical ${escapeHTML(req.role)}" in body


def test_dashboard_topology_active_badge_does_not_create_fake_counts() -> None:
    """Grouped rows must not render as `x50` or append active text to aliases."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert ".topology-row .active-badge.zero {\n    display: none;" in body
    assert (
        '<span class="active-badge zero" id="active_badge_${g.base}" '
        'title="${g.base}: priority chat-XXX tasks' in body
    )
    assert ">0</span>${aliasChip}</div>`" in body
    assert '${aliasChip}` +\n            `<span class="active-badge zero"' not in body


def test_dashboard_live_panel_refreshes_ignore_stale_responses_where_possible() -> None:
    """Live inference and CPU-lock refreshes should not repaint older responses."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "let _processStatusFetchSeq = 0;" in body
    assert "const requestSeq = ++_processStatusFetchSeq;" in body
    assert "if (requestSeq !== _processStatusFetchSeq) return;" in body
    assert "let _regionLocksRefreshSeq = 0;" in body
    assert "const refreshSeq = ++_regionLocksRefreshSeq;" in body
    assert "async function updateRegionLocks(" in body
    assert "snapshotSeq = null," in body
    assert "snapshotInflightTasks = null" in body
    assert "updatePanelSafely('contention', () => updateContentionGate(refreshSeq));" in body
    assert "function applyTopologyActivityPayload(d)" in body
    assert "function applyDashboardSnapshot(snap, source)" in body
    assert "updatePanelSafely('completed', () => updateTasks(snap));" in body
    assert "updatePanelSafely('decisions', () => updateDecisions(snap));" in body
    assert "const result = fn();" in body
    assert "result.catch((err) =>" in body
    assert (
        "return updateRegionLocks(refreshSeq, snap.region_locks, snapshotSeq, snap.in_flight_tasks || [])"
        in body
    )
    assert "function requestCoherentDashboardSnapshot(reason = '')" in body
    assert "requestCoherentDashboardSnapshot('region_locks_refresh')" in body
    assert "function updateTopologyInflight(inflight, snapshotSeq = null)" in body
    assert "const safeInflight = snapshotSeq == null ? [] : (inflight || []);" in body
    assert "let _lastRegionLocksPayload = null;" in body
    assert "display_matrix render failed" in body
    assert "fetchJSON('/dashboard/api/snapshot'" in body
    assert "timeoutMs: _SNAPSHOT_POLL_TIMEOUT_MS" in body
    assert "setInterval(updateSnapshotPoll, 2500)" in body
    assert (
        "fetchJSON(`/dashboard/api/topology_activity?window_s=${TOPOLOGY_ACTIVITY_WINDOW_S}`)"
        not in body
    )
    assert "fetchJSON('/dashboard/api/contention')" in body
    assert "if (refreshSeq !== _regionLocksRefreshSeq) return;" in body


def test_dashboard_snapshot_to_region_lock_overlay_choreography() -> None:
    """Region-lock refreshes should only reuse in-flight tasks from the same snapshot frame."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "let _latestSnapshotSeq = 0;" in body
    assert "const snapshotSeq = ++_latestSnapshotSeq;" in body
    assert (
        "return updateRegionLocks(refreshSeq, snap.region_locks, snapshotSeq, snap.in_flight_tasks || []);"
        in body
    )
    assert (
        "function updateTopology(activity, inflight, snapshotSeq = null, liveFrame = null)" in body
    )
    assert "updateTopologyInflight(inflight, snapshotSeq)" in body
    assert "const safeInflight = snapshotSeq == null ? [] : (inflight || []);" in body
    assert "const overlayInflight = snapshotSeq != null" in body
    assert "updateTopologyInflight(overlayInflight, snapshotSeq);" in body


def test_dashboard_transport_self_heals_without_page_reload() -> None:
    """Wedge-killers + watchdog: a dead stream, hung fetch, or poisoned frame
    watermark must recover on its own — the trio of stream-fed panels
    (topology / region locks / live tap) froze permanently on these before."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    # B1: timeout-bounded snapshot poll with a self-expiring in-flight guard.
    assert "async function fetchJSON(url, { timeoutMs = _FETCH_JSON_TIMEOUT_MS } = {})" in body
    assert "let _snapshotPollInFlightSince = 0;" in body
    assert "_snapshotPollInFlightSince &&" in body
    assert "now - _snapshotPollInFlightSince < _SNAPSHOT_POLL_TIMEOUT_MS + 2000" in body
    assert "_snapshotPollInFlight = false" not in body  # old permanent-wedge boolean

    # B2: no client-clock fallback for the frame watermark; null frames apply
    # but never advance it; watermark resets on every (re)connect.
    assert "if (!Number.isFinite(ts)) return null;" in body
    assert "Date.now() / 1000 + 120" in body
    assert (
        body.count("_latestSnapshotFrameTs = 0;") >= 3
    )  # decl init + both stream starters + watchdog
    assert "if (frameTs !== null) {" in body

    # B3: universal watchdog rebuilds the stream + fires a poll when snapshots
    # stop applying; hooks cover sleep/wake and network flaps.
    assert "function snapshotTransportWatchdog()" in body
    assert "setInterval(snapshotTransportWatchdog, 5000)" in body
    assert "document.addEventListener('visibilitychange'" in body
    assert "window.addEventListener('online', snapshotTransportWatchdog)" in body
    assert "let _lastSnapshotAppliedAt = Date.now();" in body

    # B7: every legacy EventSource reconnect is guarded (no stampedes) and
    # identity-checked (no stale-closure restarts).
    assert body.count("es._reconnectScheduled = true;") >= 5
    assert "if (_autopilotLogStream === es) startAutopilotLogStream();" in body
    assert "if (_rawTapStream === es) startRawTapStream();" in body
    assert "if (_structuredTapStream === es) startStructuredTapStream();" in body
    assert "if (_plannerTapStream === es) startPlannerTapStream();" in body


def test_optimization_brief_retries_across_api_reload_and_refreshes() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "const _OPTIMIZATION_BRIEF_TIMEOUT_MS = 15000;" in body
    assert "brief temporarily unavailable:" in body
    assert "setTimeout(() => updateOptimizationBrief(attempt + 1), retryMs)" in body
    assert "'optimization-brief-refresh'" in body
    assert "if (_optimizationBriefLastGood)" in body


def test_dashboard_pareto_plot_uses_journal_sources_and_nonnegative_axes() -> None:
    """Quality/speed axes should not render negative tick labels from padding."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "startsWith('journal_')" in body
    assert "const xLo = Math.max(0, xMin - xPad)" in body
    assert "const yLo = Math.max(0, yMin - yPad)" in body
    assert "d.canonical_tier" in body
    assert "d.frontiers_by_tier" in body
    assert "outer lanes ${tierKeys.map" in body
    assert "const legendY = VB.h - PAD.b - 4;" in body
    assert "paretoTierLegend(legendKeys, VB.w - 44, legendY, eraMode)" in body
    assert "paretoTierLegend(series.map(s => s[0]), VB.w - 38, legendY)" in body
    # All-era scope wiring: toggle, era-labeled fetch, underlay clouds + bands.
    assert "setParetoScope('all_eras')" in body
    assert "/dashboard/api/pareto?scope=" in body
    assert "function convexHull2D(pts)" in body
    assert "paretoEraLegend(eras, PAD.l + 6, PAD.t + 12)" in body
    assert "setPanelFreshness('pareto', d._freshness || {" in body
    assert "Pareto panel rendered successfully" in body
    assert "const eraLabel = activeSpeedEra || 'current testing era';" in body
    assert "frontier rebuild${progress} required" in body
    assert "${activeSpeedEra || 'current speed era'} rebuild${progress}" in body


def test_dashboard_gepa_and_pareto_surface_real_suite_metrics() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "function realSuiteBadge(metric)" in body
    assert "real_suite_v1 · q=" in body
    assert "realSuiteBadge(t.real_suite_v1)" in body
    assert "const suiteTip = p =>" in body
    assert "p.real_suite_v1" in body
    assert "real_suite_v1 q=" in body
    assert "setPanelFreshness('gepa', d._freshness || {" in body
    assert "GEPA panel rendered successfully" in body
    assert "function decisionQuestionMixLabel(mix, includeScored)" in body
    assert "evaluation lane → decision mix → pareto outcome" in body
    assert "<div>trial</div><div>lane</div><div>decision core</div>" in body
    assert "decision mix ${mixText}" in body
    assert "decision core ${label}" in body
    assert "lane T${Number(t)} audit" in body


def test_dashboard_autopilot_progress_includes_eval_label() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert "const evalLabel = prog.eval_label || phase.eval_label || '';" in body
    assert "evalLabel ? `trial #${d.trial_id} (${action}, ${evalLabel})`" in body
    assert "${evalLabel || 'T?'} tower ${lp.completed}/${lp.total}" in body
    assert (
        "${escapeHTML(String(evalLabel)) || 'T?'} tower ${prog.log_tail_progress.completed}/${prog.log_tail_progress.total}"
        in body
    )
    assert "const promotions = d.baseline_promotions || {};" in body
    assert "baseline promotions ${promotions.count}" in body
    assert "const outcome = d.outcome_kpis || {};" in body
    assert "keepable ${fmtRate(keepable)}" in body
    assert "wasted-eval ${fmtRate(wasted)}" in body
    assert "learning-excluded ${fmtRate(excluded)}" in body
    assert "const currentCodeHealthChip = _autopilotStatusChip(" in body
    assert "_currentCodeHealthLabel(currentCodeHealth)" in body
    assert "healthChips ? `<div style=\"margin-top:3px\">${healthChips}</div>` : ''" in body
    assert "current code ${health.status}" in body
    assert "const advice = health.restart_advice || {};" in body
    assert "restart wait for boundary" in body
    assert "restart ready" in body


def test_dashboard_repo_readiness_panel_is_advisory_only() -> None:
    """Repo-readiness queue can render in the dashboard without becoming a gate."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert 'id="repo-readiness-panel"' in body
    assert 'id="repo-readiness-open"' in body
    assert 'id="repo-readiness-list"' in body
    assert "/dashboard/api/repo_readiness" in body
    assert "function renderRepoReadiness(data)" in body
    assert "setInterval(updateRepoReadiness, 60000)" in body
    assert "data.authority || 'advisory'" in body
    assert "data.autopilot_gate ? 'true' : 'false'" in body


def test_dashboard_insight_graph_panel_is_wired_read_only() -> None:
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    assert 'id="insight-graph-panel"' in body
    assert "planner insight graph" in body
    assert 'id="insight-graph-svg"' in body
    assert 'id="insight-graph-query"' in body
    assert "focus by trial, strategy, hint, campaign, species, or handoff" in body
    assert "/dashboard/api/insight_graph" in body
    assert "function renderInsightGraph(graph)" in body
    assert "function updateInsightGraph(focusOverride)" in body
    assert "setInterval(() => updateInsightGraph(_insightGraphFocus), 20000)" in body


def test_dashboard_operational_panels_stay_directly_under_topology() -> None:
    """Completed/routing must stay directly under topology in the right-column scan path."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    topology_idx = body.index('id="topology-strip"')
    completed_idx = body.index('id="completed-tasks"')
    routing_idx = body.index('id="decision-feed"')
    readiness_idx = body.index('id="repo-readiness-panel"')

    assert topology_idx < completed_idx < routing_idx < readiness_idx


# ----- dashboard_tasks: timezone-aware UTC (Tranche-8 polish) -----


def test_task_text_snapshot_uses_timezone_aware_utc(monkeypatch) -> None:
    """Tranche-8 fix: datetime.utcnow() replaced with datetime.now(timezone.utc).

    No DeprecationWarning should be emitted by _task_text_snapshot.
    """
    import warnings
    from src.api.routes import dashboard_tasks

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        # Run with an empty event list — exercises the timestamp formatting path
        out = dashboard_tasks._task_text_snapshot("chat-test", [], None)
    # Header should still contain the "Z" suffix marker
    assert "@ " in out
    assert "Z ===" in out


def test_dashboard_folds_devices_into_regions_lock_and_tap_panels() -> None:
    """MI210/extern servers bypass the orchestrator pipeline; the Regions Lock
    grid and the live tap panel must still surface their occupancy instead of
    rendering an idle machine while a device is visibly working."""
    html_path = (
        Path(__file__).resolve().parents[1].parent / "src" / "api" / "routes" / "dashboard.html"
    )
    body = html_path.read_text()

    # Panel renamed + device fold (operator request 2026-07-05).
    assert "regions lock" in body
    assert "cpu region locks" not in body
    assert "function gpuDeviceRegionRows()" in body
    assert body.count("rows.push(...gpuRows);") == 1  # display matrix only
    assert "device occupancy from /slots, not a CPU region lock" in body

    # Orphan (off-pipeline) inference cards in the live tap panel.
    assert "function orphanDeviceSlots()" in body
    assert "function orphanDeviceSlotCards()" in body
    assert "orphan inference" in body
    assert "no token tap — off-pipeline" in body
    assert "!requests.length && !lockOnlyHolders.length && !orphanCards.length" in body

    # A degraded contention matrix reads as an incident, not a status chip.
    assert "admission gate degraded" in body
    assert "contention-matrix-v6-quarter-refresh.md" in body

"""Execute the machine page's actual transport callers under Node."""

import json
from pathlib import Path
import shutil
import subprocess
import unittest

from tests.test_dashboard_machine_provenance import _extract_function


_PAGE = Path(__file__).resolve().parents[1] / "dashboard/static/machine.html"


@unittest.skipUnless(shutil.which("node"), "node not available")
class MachineFrameCallers(unittest.TestCase):
    def test_sse_and_fallback_poll_request_machine_view(self):
        source = _PAGE.read_text()
        script = """
const API = 'http://fixture.invalid:8000', T_SNAPSHOT = 15000;
let es = null, esRetryAt = 0, esOpenedAt = 0, snapInFlight = false;
const calls = [], applications = [];
const EventSource = function(url) { calls.push(['sse', url]); this.readyState = 1; };
const getJSON = async (url, timeout) => { calls.push(['poll', url, timeout]); return {generated_at: 123}; };
const applySnapshot = (frame, source) => applications.push([frame, source]);
const fail = () => { throw new Error('unexpected transport failure'); };
"""
        script += _extract_function(source, "openStream") + "\n"
        script += _extract_function(source, "pollSnapshot") + "\n"
        script += """
(async () => {
  openStream();
  es.onmessage({data: '{"generated_at":122}'});
  await pollSnapshot();
  process.stdout.write(JSON.stringify({calls, applications, snapInFlight}));
})().catch(error => { console.error(error); process.exit(1); });
"""
        result = subprocess.run(
            ["node", "-e", script], check=True, capture_output=True, text=True, timeout=30
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["calls"], [
            ["sse", "http://fixture.invalid:8000/dashboard/events/stream?view=machine"],
            ["poll", "http://fixture.invalid:8000/dashboard/api/snapshot?view=machine", 15000],
        ])
        self.assertEqual(output["applications"], [
            [{"generated_at": 122}, "sse"], [{"generated_at": 123}, "poll"],
        ])
        self.assertFalse(output["snapInFlight"])

    def test_projection_retains_the_renderers_native_inputs_and_freshness(self):
        frame = {
            "generated_at": 123,
            "topology": {"nodes": [{"role": "frontdoor", "port": 8070}]},
            "region_locks": {"frame_id": "fixture", "by_role": {"frontdoor": {"unknown": True}}},
            "placement_telemetry": {"status": "backend_unknown"},
            "api_lifecycle": {"certificate_valid": False, "worker_coverage": {"missing_pids": [103]}},
            "live_frame": {"frame_id": "fixture", "observed_at": {"tap": 122}},
            "_freshness": {"status": "stale", "generated_at": 123},
        }
        script = """
let lastFrameMs = 0, frameSource = '', latestSnap = null, cadenceMs = 0;
const PANELS = {topology: {}, decisions: {}, outcomes: {}};
const captures = [];
const fail = () => { throw new Error('unexpected failure'); };
const ok = () => {};
const renderTopology = value => captures.push(['topology', value]);
const renderDecisions = value => captures.push(['decisions', value]);
const renderOutcomes = value => captures.push(['outcomes', value]);
const renderProcessApi = value => captures.push(['process', value]);
const renderLocks = (locks, telemetry, source) => captures.push(['locks', locks, telemetry, source]);
"""
        script += _extract_function(_PAGE.read_text(), "applySnapshot") + "\n"
        script += f"const frame = {json.dumps(frame)};\n"
        script += "applySnapshot(frame, 'sse'); process.stdout.write(JSON.stringify({captures, latestSnap}));"
        result = subprocess.run(
            ["node", "-e", script], check=True, capture_output=True, text=True, timeout=30
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["latestSnap"], frame)
        for name, value, *rest in output["captures"]:
            if name == "locks":
                self.assertEqual(value, frame["region_locks"])
                self.assertEqual(rest, [frame["placement_telemetry"], "frame"])
            else:
                self.assertEqual(value, frame)


if __name__ == "__main__":
    unittest.main()

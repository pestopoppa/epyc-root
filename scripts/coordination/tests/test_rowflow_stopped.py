"""ws58 2026-11-05 keeper STOP deadlock: lsa-oracle-reference-build-f6dddb7-20261104's manifest carried an unexpanded
`stop_file: $D/oracle-build.STOP` (its launcher sets D=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)), so the STOP file was
never seen; the allocator granted q0 every pass, the armed poller released it on "STOP present before start", and a
quiet-host drain needing q0 never completed. A row whose resolved STOP exists is `stopped`: never granted, never a drain
candidate. Unknown STOP paths keep the old behaviour."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402
from test_rowflow_arming_park import Fixture, QUIET_OPT  # noqa: E402

Q0_OPT = [frozenset({"q0"})]


class Stopped(Fixture):
    def dollar_d_row(self, rid, rank, opts, shape, d_line, stop_arg="$D/x.STOP", stop_file=None):
        d = self.row(rid, rank, opts, shape)
        lp = d["launcher"]["path"]
        with open(lp, "w") as f:
            f.write(f"#!/bin/bash\nset -euo pipefail\nD={d_line}\nexec /x/filler_run15.sh --id {rid} \\\n  --stop \"{stop_arg}\" --workdir \"$D\"\n")
        d["stop_file"] = stop_arg if stop_file is None else stop_file
        rf.atomic_json(rf.ready_path(self.flags, rid), d)
        rf.atomic_json(rf.pass_path(self.flags, rid), {"id": rid, "passed_at": "2026-11-04T17:33:24Z", "launcher_sha256": rf.sha256(lp)})
        return d

    def test_resolves_each_launcher_dir_idiom_and_literal(self):
        here = self.flags
        for i, line in enumerate(['$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)', '$(cd -- "$(dirname -- "$0")" && pwd)',
                                  '$(cd "$(dirname "$0")" && pwd)', '$(dirname "$(readlink -f "$0")")', f'"{here}"']):
            d = self.dollar_d_row(f"r{i}", 10, Q0_OPT, "quarter", line)
            self.assertEqual(rf.resolve_stop_path(d), os.path.join(os.path.realpath(here) if "readlink" in line else here, "x.STOP"))

    def test_unresolvable_is_unknown(self):
        for i, (line, arg) in enumerate([("$(mktemp -d)", "$D/x.STOP"), ('"$HOME/x"', "$D/x.STOP"),
                                         ('$(cd "$(dirname "$0")" && pwd)', "$OTHER/x.STOP"), ('/a', "rel/x.STOP")]):
            d = self.dollar_d_row(f"u{i}", 10, Q0_OPT, "quarter", line, stop_arg=arg)
            self.assertIsNone(rf.resolve_stop_path(d), (line, arg))

    def test_stopped_row_never_granted_and_returns_when_stop_deleted(self):
        rid = "lsa-oracle-reference-build-f6dddb7-20261104"
        self.dollar_d_row(rid, 10, Q0_OPT, "quarter", '$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)', "$D/oracle-build.STOP")
        sf = os.path.join(self.flags, "oracle-build.STOP")
        open(sf, "w").close()
        st = rf.status(self.flags, rid)
        self.assertEqual((st["state"], st["reason"]), ("stopped", sf))
        for _ in range(3):
            self.assertEqual(self.tick(), [])
        self.assertEqual(self.armed_calls, [])
        os.remove(sf)
        self.assertEqual(rf.status(self.flags, rid)["state"], "grantable")
        self.assertEqual([r for _, r, _ in self.tick()], [rid])

    def test_unknown_stop_behaves_as_before(self):
        rid = "row-unknown"
        self.dollar_d_row(rid, 10, Q0_OPT, "quarter", "$(mktemp -d)")
        open(os.path.join(self.flags, "x.STOP"), "w").close()
        self.assertEqual(rf.status(self.flags, rid)["state"], "grantable")
        self.assertEqual([r for _, r, _ in self.tick()], [rid])

    def test_stopped_quiet_host_row_is_not_a_drain_candidate(self):
        big = self.dollar_d_row("big-quiet", 5, QUIET_OPT, "quiet-host", '$(cd "$(dirname "$0")" && pwd)')
        open(os.path.join(self.flags, "x.STOP"), "w").close()
        self.row("small", 50, Q0_OPT, "quarter")
        rf.rl_status = lambda: {r: ("busy" if r == "q1" else "free", "foreign") for r in rf.REGIONS}
        out = self.tick()
        self.assertEqual([r for _, r, _ in out], ["small"])
        self.assertFalse([l for l in self.lines if big["id"] in l and (l.startswith("DRAIN") or l.startswith("RANK-SKIP"))], self.lines)


if __name__ == "__main__":
    unittest.main()

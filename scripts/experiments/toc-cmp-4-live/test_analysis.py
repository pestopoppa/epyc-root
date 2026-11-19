import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import analysis


def make_runs(strata, repeats):
    return [
        {
            "point_id": f"point-{index:02}",
            "stratum": stratum,
            "arm": arm,
            "repeat": repeat,
            "baps": (2 * arm_index + (index % 2) + (repeat % 2)) / 10,
            "correct": repeat < 5 - arm_index,
            "wall_s": 20 + repeat,
            "valid": True,
        }
        for index, stratum in enumerate(strata)
        for arm_index, arm in enumerate(analysis.ARMS)
        for repeat in range(repeats)
    ]


def full_cell():
    return make_runs([stratum for stratum in analysis.STRATA for _ in range(10)], 8)


class EndpointTests(unittest.TestCase):
    def test_window_counts_errors_and_blocks_once_and_excludes_reread_from_numerator(self):
        def action(blocked=False, error=False, deliberate_reread=False):
            return {"blocked": blocked, "error": error, "deliberate_reread": deliberate_reread}

        actions = [
            action(blocked=True, error=True),
            action(blocked=True, error=True, deliberate_reread=True),
            action(error=True),
            action(),
            action(),
            action(blocked=True),
        ]
        self.assertEqual(analysis.calculate_baps(actions), {"baps": 2 / 5, "deliberate_rereads": 1})
        self.assertEqual(analysis.calculate_baps(actions[:2]), {"baps": 1 / 2, "deliberate_rereads": 1})
        self.assertEqual(analysis.calculate_baps([]), {"baps": None, "deliberate_rereads": 0})

    def test_pass3_without_replacement(self):
        self.assertEqual(analysis.pass3(5, 8), 10 / 56)
        self.assertEqual(analysis.pass3(2, 8), 0)
        self.assertEqual(analysis.pass3(2, 2), "UNKNOWN")


class AnalysisTests(unittest.TestCase):
    def test_pilot_uses_only_feasibility_metrics_and_identifies_stratum_coverage(self):
        rows = make_runs(["early"] * 8, 4)
        rows[0]["correct"] = None
        report = analysis.analyze(rows, "pilot")
        self.assertEqual(report["points"], 8)
        self.assertAlmostEqual(report["base_baps"], 0.10)
        self.assertEqual(report["run_wall_s"], {"count": 96, "mean": 21.5, "median": 21.5})
        self.assertTrue(all(value < 1e-15 for value in report["paired_difference_sd"].values()))
        self.assertEqual(report["strata"]["early"]["included"], 8)
        self.assertEqual(report["strata"]["middle"]["included"], 0)
        self.assertIn("cannot assess the MDE across all strata", report["sd_scope"])
        self.assertTrue({"arms", "contrasts", "bootstrap"}.isdisjoint(report))

    def test_confirmatory_pairs_point_and_repeat_resampling_and_reports_secondary_metrics(self):
        rows = full_cell()
        report = analysis.analyze(rows, "confirmatory", seed=2, draws=250)
        self.assertEqual(report, analysis.analyze(list(reversed(rows)), "confirmatory", seed=2, draws=250))
        self.assertEqual(report["bootstrap"], {"seed": 2, "draws": 250})
        for name, delta in zip(report["contrasts"], (-0.2, -0.4, -0.2)):
            contrast = report["contrasts"][name]
            self.assertAlmostEqual(contrast["mean_difference"], delta)
            for end in contrast["bonferroni_interval_95_familywise"]:
                self.assertAlmostEqual(end, delta)
            self.assertLess(contrast["holm_adjusted_bootstrap_p"], 0.05)
            self.assertEqual(contrast["decision"], "effect")
        baseline = report["arms"]["summary_only"]
        self.assertEqual(baseline["accuracy"]["mean"], 5 / 8)
        self.assertAlmostEqual(baseline["pass3"]["mean"], 10 / 56)
        self.assertEqual(baseline["pass3"]["total_repeats"], 240)

    def test_void_excludes_other_arm_rows_and_keeps_stratum_denominator(self):
        rows = full_cell()
        rows += [
            dict(rows[0], point_id="voided", baps=1.0),
            {"point_id": "voided", "stratum": "early", "valid": False, "status": "void_point"},
        ]
        report = analysis.analyze(rows, "confirmatory", draws=40)
        self.assertEqual(report["points"], 30)
        self.assertEqual(report["strata"]["early"], {"included": 10, "voided": 1, "void_rate": 1 / 11})
        self.assertAlmostEqual(report["base_baps"], 0.10)

    def test_missing_external_grade_preserves_baps_and_reports_unknown(self):
        rows = full_cell()
        rows[0]["correct"] = None
        report = analysis.analyze(rows, "confirmatory", draws=40)
        metrics = report["arms"]["summary_only"]
        self.assertAlmostEqual(metrics["baps"]["mean"], 0.1)
        for key in ("accuracy", "pass3"):
            self.assertEqual(metrics[key], {
                "mean": "UNKNOWN", "interval_95": None, "scored_repeats": 239, "total_repeats": 240,
            })
        self.assertEqual(report["arms"]["pointer_only"]["accuracy"]["mean"], 0.5)

    def test_confirmatory_rejects_incomplete_and_mismatched_repeats(self):
        rows = full_cell()
        with self.assertRaisesRegex(ValueError, "at least 10"):
            analysis.analyze(make_runs(["early"] * 30, 8), "confirmatory")
        with self.assertRaisesRegex(ValueError, "8–12 repeats"):
            analysis.analyze([row for row in rows if row["repeat"] < 7], "confirmatory")
        with self.assertRaisesRegex(ValueError, "mismatched repeat IDs"):
            analysis.analyze(rows[:-1], "confirmatory")
        with self.assertRaisesRegex(ValueError, "missing zero-based repeat IDs"):
            analysis.analyze([row for row in rows if row["repeat"] != 1], "confirmatory")
        with self.assertRaisesRegex(ValueError, "invalid run"):
            analysis.analyze([dict(rows[0], valid=False), *rows[1:]], "confirmatory")

    def test_confirmatory_distinguishes_floor_and_below_mde(self):
        rows = full_cell()
        floor = analysis.analyze([dict(row, baps=0) for row in rows], "confirmatory", draws=250)
        self.assertTrue(floor["floor_effect"])
        floor_decisions = {contrast["decision"] for contrast in floor["contrasts"].values()}
        self.assertEqual(floor_decisions, {"floor_effect"})
        small_rows = [dict(row, baps=row["baps"] / 5) for row in rows]
        small = analysis.analyze(small_rows, "confirmatory", draws=250)
        self.assertEqual({contrast["decision"] for contrast in small["contrasts"].values()}, {"below_mde"})

    def test_holm_steps_up_adjustment_for_marginal_false_positive(self):
        samples = [[-1] * (1000 - positives) + [1] * positives for positives in (19, 1, 49)]
        adjusted = analysis._holm_p_values(samples)
        self.assertLess(2 * 20 / 1001, analysis.ALPHA)
        self.assertGreater(adjusted[0], analysis.ALPHA)
        self.assertAlmostEqual(adjusted[0], 2 * 40 / 1001)
        self.assertAlmostEqual(adjusted[1], 3 * 4 / 1001)
        self.assertAlmostEqual(adjusted[2], 100 / 1001)

    def test_cli_reads_normalized_jsonl_and_json(self):
        rows = make_runs(["early"] * 8, 4)
        script = Path(analysis.__file__)
        with tempfile.TemporaryDirectory() as directory:
            jsonl_path = Path(directory) / "runs.jsonl"
            json_path = Path(directory) / "runs.json"
            jsonl_path.write_text("".join(json.dumps(run) + "\n" for run in rows))
            json_path.write_text(json.dumps({"runs": rows}))
            for path in (jsonl_path, json_path):
                result = subprocess.run([sys.executable, script, "pilot", path],
                                        check=True, capture_output=True, text=True)
                self.assertEqual(json.loads(result.stdout), analysis.analyze(rows, "pilot"))


if __name__ == "__main__":
    unittest.main()

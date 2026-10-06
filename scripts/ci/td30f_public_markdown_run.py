"""Run the original aggregate writer and its exact offline test cohort."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SELECTIONS = (
    "tests/ci/test_td30f_public_markdown_report.py::test_original_aggregate_is_218_row_public_successor_and_non_gold",
    "tests/ci/test_td30f_public_markdown_report.py::test_word_trigram_guards_keep_strict_threshold_and_minimum_boundaries",
    "tests/ci/test_td30f_public_markdown_report.py::test_streaming_block_controls_are_body_only_and_match_pinned_boundaries",
    "tests/ci/test_td30f_public_markdown_report.py::test_streaming_precondition_exclusions_use_tail_line_count",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-corpus", type=Path, required=True)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    args = parser.parse_args()
    report = Path(__file__).with_name("td30f_public_markdown_report.py")
    subprocess.run([sys.executable, str(report), "--root-corpus", str(args.root_corpus),
                    "--app", str(args.app), "--output", str(args.output)], check=True)
    env = os.environ.copy()
    env["TD30F_REPORT_OUTPUT"] = str(args.output.resolve())
    env["TD30F_APP_ROOT"] = str(args.app.resolve())
    command = [sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
               "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={args.junit}"]
    return subprocess.call(command, env=env)


if __name__ == "__main__":
    raise SystemExit(main())

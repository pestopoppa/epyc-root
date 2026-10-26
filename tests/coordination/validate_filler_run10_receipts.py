"""Scoped structured GNX risk and exact adapter collection/JUnit validation."""
from collections import Counter
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

mode = sys.argv[1]
if mode == "impact":
    path, symbol = Path(sys.argv[2]), sys.argv[3]
    assert symbol in {"write_ended", "run_one", "snapshot_overrun"}
    try:
        value = json.loads(path.read_text())
    except (ValueError, OSError):
        value = None
    risks = []
    def inspect(node):
        if isinstance(node, dict):
            for key, item in node.items():
                if key in {"risk", "risk_level", "riskLevel"} and isinstance(item, str):
                    risks.append(item.upper())
                elif isinstance(item, (dict, list)):
                    inspect(item)
        elif isinstance(node, list):
            for item in node:
                inspect(item)
    if isinstance(value, (dict, list)):
        inspect(value)
    receipt = {"symbol": symbol, "direction": "upstream", "structured_risks": risks,
               "result": "STOP" if any(r in {"HIGH", "CRITICAL"} for r in risks) else "UNKNOWN",
               "scope": "private empty registry; no indexed native producer; no diagnostic text interpreted as a risk"}
    path.with_suffix(".risk.json").write_text(json.dumps(receipt, indent=2) + chr(10))
    if receipt["result"] == "STOP":
        raise SystemExit(69)
elif mode == "adapter":
    collect, junit, out = map(Path, sys.argv[2:5])
    prefix = "tests/vidya/test_calendar_overrun_adapter.py::"
    declared = [line[len(prefix):] for line in collect.read_text().splitlines() if line.startswith(prefix)]
    expected_methods = Counter({"test_d4_record_projects_censored_ratio_with_shape_and_grades": 1,
                                "test_legacy_ended_without_estimate_is_unchecked": 1,
                                "test_bad_records_refuse": 6,
                                "test_clean_finish_not_censored_and_actual_derived_from_started": 1,
                                "test_units_and_registration": 1})
    assert len(declared) == 10 and len(set(declared)) == 10, declared
    assert Counter(name.split("[", 1)[0] for name in declared) == expected_methods
    root = ET.parse(junit).getroot()
    cases = list(root.iter("testcase"))
    assert len(cases) == len(declared)
    assert all(case.get("classname") == "tests.vidya.test_calendar_overrun_adapter" for case in cases)
    ran = [case.get("name") for case in cases]
    assert Counter(ran) == Counter(declared), (declared, ran)
    for tag in ("skipped", "failure", "error"):
        assert not list(root.iter(tag)), tag
    out.write_text(json.dumps({"collected": declared, "run": ran, "tests": len(ran),
                               "skipped": 0, "failures": 0, "errors": 0}, indent=2) + chr(10))
else:
    raise SystemExit("unknown receipt mode")

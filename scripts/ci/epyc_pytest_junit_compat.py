"""Prospective pytest 9.0.3 JUnit accounting; load with -p epyc_pytest_junit_compat.

Put this directory on PYTHONPATH and declare this source in the native readset.
Only redundant passed SubtestReport counters are excluded before XML emission.
"""
import pytest
from _pytest.junitxml import xml_key
from _pytest.subtests import SubtestReport

POLICY = "pytest-9.0.3-passed-subtest-reports-v1"


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    # Workers forward typed reports; only the controller owns the JUnit exporter.
    if hasattr(config, "workerinput"):
        return
    if pytest.__version__ != "9.0.3":
        raise pytest.UsageError("epyc JUnit compatibility requires pytest 9.0.3")
    xml = config.stash.get(xml_key, None)
    if xml is None:
        raise pytest.UsageError("epyc JUnit compatibility requires --junitxml")
    config.pluginmanager.register(_Accounting(xml), "epyc-junit-accounting")


class _Accounting:
    def __init__(self, xml):
        self.xml = xml
        self.excluded = 0

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_runtest_logreport(self, report):
        redundant = (isinstance(report, SubtestReport)
                     and report.when == "call" and report.passed)
        before = self.xml.stats["passed"]
        result = yield
        if redundant:
            if self.xml.stats["passed"] != before + 1:
                raise RuntimeError("unexpected pytest passed-subtest JUnit accounting")
            self.xml.stats["passed"] -= 1
            self.excluded += 1
        return result

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_sessionfinish(self):
        if self.excluded:
            if any(name.startswith("epyc.junit.") for name, _ in self.xml.global_properties):
                raise RuntimeError("reserved epyc JUnit accounting property already exists")
            self.xml.add_global_property("epyc.junit.accounting_policy", POLICY)
            self.xml.add_global_property("epyc.junit.excluded_passed_subtest_reports", self.excluded)
        return (yield)

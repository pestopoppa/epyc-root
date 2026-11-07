from scripts.harness import flag_liveness as fl


def test_unwired_consumer_trips_once_and_is_excluded():
    r = fl.evaluate({"reuse_graph": {"writes": 40, "consumer_reads": 0},
                     "prefix": {"writes": 40, "consumer_reads": 12}})
    assert r["verdicts"] == {"reuse_graph": "silent", "prefix": "live"}
    assert [e["flag"] for e in r["silent_events"]] == ["reuse_graph"]
    assert r["silent_events"][0]["schema_version"] == fl.EVENT_SCHEMA
    assert r["sweep_eligible"] == ["prefix"]


def test_clean_run_is_silent():
    r = fl.evaluate({"a": {"writes": 3, "consumer_reads": 3}})
    assert r["silent_events"] == [] and r["sweep_eligible"] == ["a"]


def test_negative_controls_zero_writes_and_absent_counter_are_not_silent():
    r = fl.evaluate({"never_fired": {"writes": 0, "consumer_reads": 0},
                     "no_counter": {"writes": 5, "consumer_reads": None},
                     "no_key": {"writes": 5}})
    assert r["silent_events"] == []
    assert r["verdicts"] == {"never_fired": "idle", "no_counter": "unmeasured",
                             "no_key": "unmeasured"}
    assert r["sweep_eligible"] == ["never_fired", "no_counter", "no_key"]

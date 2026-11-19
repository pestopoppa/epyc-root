from scripts.research.delegation_context_sizes import summarize


def start(role, text, ts=1, **kwargs):
    return dict(
        event="start",
        role=role,
        prompt=text,
        ts_epoch=ts,
        parent_request_id="p",
        **kwargs,
    )


def test_exclusions_and_character_units():
    events = [
        start("architect_general", "é" * 10),
        start("worker_general", "中" * 4, 2),
        start("worker_general", "partial", 3, prompt_truncated=True),
        start("worker_general", None, 4),
    ]
    report = summarize(events)
    assert report["included"] == 1
    assert report["paired"] == 3
    assert report["excluded"] == {"truncated": 1, "unparsable": 1}
    assert report["by_role"][0]["worker_chars"]["total"] == 4
    assert report["mode_available"] is False


def test_later_parent_and_orphans_are_not_size_evidence():
    assert summarize(
        [start("architect_general", "p", 2), start("worker_general", "c", 1)]
    )["excluded"] == {"later_parent": 1}
    report = summarize([start("worker_general", "orphan")])
    assert report["no_parent_prompt"] == {"worker_general": 1}
    assert report["by_role"] == []


def test_latest_parent_and_role_groups():
    report = summarize(
        [
            start("architect_general", "a", 1),
            start("architect_general", "bb", 2),
            start("worker_general", "ccc", 3),
            start("worker_vision", "d", 4),
        ]
    )
    assert len(report["by_role"]) == 2
    assert all(row["parent_chars"]["total"] == 2 for row in report["by_role"])

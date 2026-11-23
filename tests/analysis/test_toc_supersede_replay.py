import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "analysis"))
import toc_supersede_replay as T  # noqa: E402


def _cc(*turns):
    """turns: list of rounds; each round = list of (name, input, result_text, is_error)."""
    lines = []
    n = 0
    for r, calls in enumerate(turns):
        content, results = [], []
        for name, inp, out, err in calls:
            n += 1
            content.append({"type": "tool_use", "id": f"t{n}", "name": name, "input": inp})
            results.append({"type": "tool_result", "tool_use_id": f"t{n}", "content": out, "is_error": err})
        lines.append(json.dumps({"type": "assistant", "message": {"id": f"m{r}", "content": content}}).encode())
        lines.append(json.dumps({"type": "user", "message": {"content": results}}).encode())
    return lines


def _run(*turns):
    segs, _ = T.parse_claude_code(_cc(*turns))
    assert len(segs) == 1
    return segs[0], T.supersession(segs[0]), T.analyze_segment(segs[0])


BIG = "x" * 100


def test_read_then_edit_and_read_supersede():
    seg, sup, _ = _run([("Read", {"file_path": "/a.py"}, BIG, False)],
                       [("Edit", {"file_path": "/a.py"}, "ok", False)],
                       [("Read", {"file_path": "/a.py"}, BIG + "y", False)])
    assert sup == {0: 1, 1: 2}


def test_different_path_not_superseded():
    _, sup, _ = _run([("Read", {"file_path": "/a.py"}, BIG, False)], [("Read", {"file_path": "/b.py"}, BIG, False)])
    assert sup == {}


def test_command_rerun_normalized():
    _, sup, _ = _run([("Bash", {"command": "cd /x && git status  2>&1"}, BIG, False)],
                     [("Bash", {"command": "git status"}, BIG, False)])
    assert sup == {0: 1}


def test_cat_is_a_read_of_path():
    _, sup, _ = _run([("Bash", {"command": "cat /a.py"}, BIG, False)], [("Read", {"file_path": "/a.py"}, BIG, False)])
    assert sup == {0: 1}


def test_build_overlap_and_failed_build_does_not_supersede():
    _, sup, _ = _run([("Bash", {"command": "make -j8 foo bar"}, BIG, False)],
                     [("Bash", {"command": "make foo"}, "err", True)],
                     [("Bash", {"command": "make baz"}, BIG, False)],
                     [("Bash", {"command": "make bar"}, BIG, False)])
    assert sup == {0: 3}


def test_test_requires_passing_rerun():
    _, sup, _ = _run([("Bash", {"command": "pytest tests/x"}, "1 failed", True)],
                     [("Bash", {"command": "pytest tests/x"}, "2 failed " + BIG, False)],
                     [("Bash", {"command": "pytest tests/x"}, "3 passed", False)])
    assert sup == {0: 2, 1: 2}


def test_candidate_round_needs_all_outputs_and_grace():
    # round0 has two calls, only one superseded -> not a candidate
    seg, sup, res = _run([("Read", {"file_path": "/a"}, BIG, False), ("Read", {"file_path": "/b"}, BIG, False)],
                         [("Read", {"file_path": "/a"}, BIG, False)],
                         [("Bash", {"command": "echo 1"}, BIG, False)],
                         [("Bash", {"command": "echo 2"}, BIG, False)])
    assert res["cand_rounds"] == 0
    # all superseded and grace elapsed (superseded in round1, last round 3 >= 1+2)
    seg, sup, res = _run([("Read", {"file_path": "/a"}, BIG, False)],
                         [("Read", {"file_path": "/a"}, BIG + "z", False)],
                         [("Bash", {"command": "echo 1"}, BIG, False)],
                         [("Bash", {"command": "echo 2"}, BIG, False)])
    assert res["cand_rounds"] == 1 and res["cand_round_chars"] == 100
    # grace not elapsed
    _, _, res = _run([("Read", {"file_path": "/a"}, BIG, False)], [("Read", {"file_path": "/a"}, BIG + "z", False)])
    assert res["cand_rounds"] == 0


def test_regret_by_content_hash():
    old = "line one of the old file content that is long enough\n" * 3
    new = "completely different\n" * 5
    _, _, res = _run([("Read", {"file_path": "/a"}, old, False)],
                     [("Read", {"file_path": "/a"}, new, False)],
                     [("Bash", {"command": "echo 1"}, BIG, False)],
                     [("Bash", {"command": "echo 2"}, BIG, False)],
                     [("Bash", {"command": "git show HEAD:a"}, old, False)])
    assert res["evicted"] == 1 and res["evicted_info_losing"] == 1 and res["regret_hash"] == 1


def test_identical_superseder_is_not_info_losing():
    _, _, res = _run([("Read", {"file_path": "/a"}, BIG, False)], [("Read", {"file_path": "/a"}, BIG, False)],
                     [("Bash", {"command": "echo 1"}, BIG + "1", False)], [("Bash", {"command": "echo 2"}, BIG + "2", False)])
    assert res["evicted_info_losing"] == 0 and res["dedup_repeats"] == 1


def test_baseline_age_clear_keeps_last_two():
    big = "q" * 5000
    _, _, res = _run(*[[("Bash", {"command": f"echo {i}"}, big + str(i), False)] for i in range(5)])
    assert res["base_evicted"] == 3 and res["base_cleared_chars"] == 3 * 5001


def test_bench_adapter_and_compact_segments():
    rec = {"turn": 1, "action": "bash", "command": "cat /testbed/a.py", "exit": 0,
           "assistant_responses": [{"text": "hi"}], "raw_observation": {"text": BIG}}
    rec2 = dict(rec, turn=2, action="edit", command="a.py", raw_observation={"text": "APPLIED"})
    segs, _ = T.parse_bench([json.dumps(rec).encode(), json.dumps(rec2).encode()])
    assert T.supersession(segs[0]) == {0: 1}
    lines = _cc([("Read", {"file_path": "/a"}, BIG, False)])
    lines.append(json.dumps({"type": "system", "subtype": "compact_boundary"}).encode())
    lines += _cc([("Read", {"file_path": "/a"}, BIG, False)])
    segs, _ = T.parse_claude_code(lines)
    assert len(segs) == 2 and T.supersession(segs[0]) == {}


def test_manifest_digest_stable(tmp_path):
    f = tmp_path / "s.jsonl"
    f.write_bytes(b"\n".join(_cc([("Read", {"file_path": "/a"}, BIG, False)])) + b"\n")
    size = f.stat().st_size
    r1 = T.analyze_file(str(f), size, "cc")
    with open(f, "ab") as fh:
        fh.write(b'{"type":"user"}\n')  # growth after manifest must not change the digest
    r2 = T.analyze_file(str(f), size, "cc")
    assert r1["sha256"] == r2["sha256"]
    r1.update(path=str(f))
    assert T.manifest_digest([r1]) == T.manifest_digest([dict(r2, path=str(f))])

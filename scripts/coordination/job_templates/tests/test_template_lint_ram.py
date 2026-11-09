"""NIB2-98 publish-time lint: big-RAM rows must reference the load-time RAM admission (WARN only)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import template_lint as tl  # noqa: E402


def row(tmp_path, gib, job_text, key="gib"):
    (tmp_path / "row.json").write_text(json.dumps({"schema": "epyc.row.v3", "id": "r1", key: gib,
                                                   "budget_gib": 1, "raw": ["x"]}))
    (tmp_path / "job.py").write_text(job_text)
    return [w for w in tl.lint_dir(tmp_path) if "RAM admission" in w]


def test_big_row_without_admission_warns(tmp_path):
    w = row(tmp_path, 739, "import subprocess\nsubprocess.run(['/x/llama-server','-t','4'])\n")
    assert len(w) == 1 and "739" in w[0] and "NIB2-98" in w[0]


def test_big_row_with_each_admission_form_is_quiet(tmp_path):
    for t in ("# job_fence fence --need-ram-gib 739 -- /x\n", "env JOB_FENCE_NEED_RAM_GIB=739\n",
              "run(['job_fence.py','ram','--need-gib','739'])\n", "ram_admit.py -- /x\n"):
        assert row(tmp_path, 739, t) == []


def test_small_or_undeclared_row_is_quiet_negative_control(tmp_path):
    assert row(tmp_path, 99, "x=1\n") == []
    assert row(tmp_path, 739, "x=1\n", key="ram_gib") != []   # the other manifest key is honoured
    (tmp_path / "row.json").write_text(json.dumps({"schema": "epyc.row.v3", "id": "r1", "budget_gib": 1, "raw": ["x"]}))
    assert [w for w in tl.lint_dir(tmp_path) if "RAM admission" in w] == []


def test_lint_never_raises_and_main_exits_zero(tmp_path, capsys):
    row(tmp_path, 739, "x=1\n")
    assert tl.main([str(tmp_path)]) == 0
    assert "WARN" in capsys.readouterr().out

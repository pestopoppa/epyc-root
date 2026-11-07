"""gitnexus_impact: analyze/scan split, parse-cache staleness, scan failure never repeats analyze, rc semantics."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import gitnexus_impact as gi  # noqa: E402
import template_lint  # noqa: E402

HEAD = "8952a0f693fb923918157eb25117641b74766230"


class Fake:
    def __init__(self, tree, misparse_until=0, impact=None):
        self.tree, self.calls, self.analyzes = tree, [], 0
        self.misparse_until = misparse_until   # analyze count before the parser emits a clean graph
        self.impact = impact or {"target": "x", "risk": "LOW", "impactedCount": 2}

    def __call__(self, args, cwd, env):
        self.calls.append(args)
        if args[:2] == ["gitnexus", "analyze"]:
            self.analyzes += 1
            return 0, "ok", ""
        if args[:2] == ["gitnexus", "status"]:
            return 0, f"Repository: {self.tree}\nCurrent commit: {HEAD[:7]}\n", ""
        if args[:2] == ["gitnexus", "cypher"]:
            ids = ["Function:k.cuh:flash_attn_ext_vec"]
            if self.analyzes <= self.misparse_until:
                ids.append("Function:k.cuh:__launch_bounds__")
            return 0, json.dumps({"markdown": "\n".join(f"| {i} |" for i in ids)}), ""
        if args[:2] == ["gitnexus", "impact"]:
            return 0, json.dumps(self.impact), ""
        return 1, "", "unexpected"


def job(tmp_path, fake, **kw):
    cfg = {"tree": str(tmp_path / "src"), "head": HEAD, "repo_name": "r", "out": str(tmp_path / "out"),
           "symbols": [["flash_attn_ext_vec", "k.cuh"], ["other", "a.c"]], "require_callers": ["flash_attn_ext_vec"],
           "parse_probes": [{"file": "k.cuh", "bad_names": ["__launch_bounds__"], "unique_function": "flash_attn_ext_vec"}]}
    cfg.update(kw)
    return gi.ImpactJob(cfg, runner=fake)


def test_all_then_rerun_skips_analyze(tmp_path):
    f = Fake(str(tmp_path / "src"))
    assert job(tmp_path, f).main() == 0 and f.analyzes == 1
    assert (tmp_path / "out" / "COMPLETE").exists()
    assert job(tmp_path, f).main() == 0 and f.analyzes == 1   # cached graph reused


def test_scan_failure_is_inconclusive_rc0_and_never_reanalyzes(tmp_path):
    f = Fake(str(tmp_path / "src"), impact={"status": "ambiguous"})
    assert job(tmp_path, f).main() == 0
    assert (tmp_path / "out" / "INCONCLUSIVE").exists() and f.analyzes == 1
    assert job(tmp_path, f).main("scan") == 0 and f.analyzes == 1
    assert job(tmp_path, f).main() == 0 and f.analyzes == 1


def test_scan_phase_alone_never_analyzes(tmp_path):
    f = Fake(str(tmp_path / "src"))
    assert job(tmp_path, f).main("scan") == 0 and f.analyzes == 0
    assert (tmp_path / "out" / "INCONCLUSIVE").exists()


def test_stale_parse_cache_forces_reanalyze(tmp_path):
    f = Fake(str(tmp_path / "src"))
    job(tmp_path, f).main("analyze")
    f.misparse_until = 99                                       # cached graph now shows the misparse
    assert job(tmp_path, f).main("analyze") == 1 and f.analyzes == 2   # re-analyzed once; parser still bad -> rc1
    f.misparse_until = 2
    assert job(tmp_path, f).main() == 0 and f.analyzes == 3


def test_vacuous_and_risk(tmp_path):
    f = Fake(str(tmp_path / "src"), impact={"target": "x", "risk": "LOW", "impactedCount": 0})
    assert job(tmp_path, f).main() == 0 and (tmp_path / "out" / "INCONCLUSIVE").exists()
    f2 = Fake(str(tmp_path / "s2"), impact={"target": "x", "risk": "HIGH", "impactedCount": 3})
    assert job(tmp_path / "b", f2, tree=str(tmp_path / "s2"), out=str(tmp_path / "b" / "out")).main() == 3


def test_template_lint_warns_on_vendored_copies(tmp_path):
    (tmp_path / "write_fence.py").write_bytes((HERE / "fixtures" / "write_fence_v40_template.py").read_bytes())
    (tmp_path / "job.py").write_text('run(["gitnexus","analyze"]); run(["gitnexus", "impact"]) # "impact"')
    w = template_lint.lint_dir(tmp_path / "launch.sh")
    assert any("write_fence.py" in x for x in w) and any("gitnexus-impact" in x for x in w)
    ok = tmp_path / "ok"
    ok.mkdir()
    (ok / "job.py").write_text("import gitnexus_impact")
    assert template_lint.lint_dir(ok) == []


def test_fence_lint_import_rule(tmp_path):
    bad, good, none = (tmp_path / n for n in ("bad", "good", "none"))
    for d in (bad, good, none):
        d.mkdir()
    (bad / "smoke_admission.py").write_text("def apply(paths): pass\n")
    (good / "write_fence.py").write_text("from job_fence import fence\n")
    (none / "job.py").write_text("print(1)\n")
    assert any("smoke_admission.py" in x and "job_fence" in x for x in template_lint.lint_dir(bad))
    assert template_lint.lint_dir(good) == []
    assert template_lint.lint_dir(none) == []

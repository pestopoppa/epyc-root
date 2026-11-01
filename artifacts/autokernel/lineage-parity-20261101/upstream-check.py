import importlib.util, sys, types
from pathlib import Path
for name in ("evo_replay", "evo_replay.core", "evo_replay.core.checkpoints"):
    sys.modules[name] = types.ModuleType(name)
sys.modules["evo_replay.core.checkpoints"].load_programs = lambda _: None

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
up = load("pinned_upstream", "/mnt/raid0/llm/tmp/codex3-evoreplay-detect-1773db16.py")
local = load("local_lineage", "scripts/autokernel/lineage_diagnostics.py")
def row(i, it, p, code):
    return {"id": i, "iteration_found": it, "parent_id": p, "solution": code,
            "metrics": {}, "edit_labels": [], "edit_label_source": {"annotator":"fixture", "rubric_revision":"1773db16"}}
rows = [row("a",0,None,"alpha();\n123;\nfoo\nlong_base();"),
        row("b",1,"a","long_base();"),
        row("c",2,"a","long_base();\nalpha();\nalpha();\nalpha();\n123;\nfoo\nnew_line();")]
_, summaries = up.detect_cycles({r["id"]: r for r in rows})
expected = (sum(x.total_added for x in summaries.values()), sum(x.recycled_added for x in summaries.values()))
actual_report = local.analyze(rows, direction="higher_better")["cycling"]
actual = actual_report["added_lines"], actual_report["recycled_added_lines"]
print("pinned upstream added/recycled:", expected, "local:", actual)
if expected != actual:
    raise SystemExit(1)

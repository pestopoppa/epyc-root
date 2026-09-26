"""Regression tests for scripts/validate/check_ratification_receipts.py.

Every fixture script below is written in a style a REAL ratifier in this repo
used. Before 2026-09-26 the checker (a) missed every write made through a
variable, (b) reported op60's `"$ROOT/.../ratification_receipt.py" emit` as
not emitting a receipt, and (c) defaulted --repo-root to /workspace, so it
scanned a different checkout when run from a worktree.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate" / "check_ratification_receipts.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_ratification_receipts_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = _load()

BOUNDARY_YAML = """\
schema_version: session_bus.human_only_paths.v1
paths:
  - repo: epyc-root
    glob: "MEASUREMENT.md"
  - repo: epyc-root
    glob: "CLAUDE.md"
  - repo: epyc-root
    glob: "agents/shared/*.md"
  - repo: epyc-root
    glob: "measurement/protocols/*.md"
  - repo: epyc-orchestrator
    glob: "orchestration/instrument_eras.yaml"
"""

PATCH_MEAS = """\
diff --git a/MEASUREMENT.md b/MEASUREMENT.md
--- a/MEASUREMENT.md
+++ b/MEASUREMENT.md
@@ -1 +1,2 @@
 # M
+- new clause
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
             "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin", "HOME": str(repo)},
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / "coordination" / "session-bus").mkdir(parents=True)
    (tmp_path / "coordination" / "session-bus" / "human_only_paths.yaml").write_text(BOUNDARY_YAML)
    (tmp_path / "MEASUREMENT.md").write_text("# M\n")
    (tmp_path / "agents" / "shared").mkdir(parents=True)
    (tmp_path / "agents" / "shared" / "OPERATING_CONSTRAINTS.md").write_text("# OC\n")
    (tmp_path / "artifacts" / "operator" / "receipts").mkdir(parents=True)
    (tmp_path / "scripts" / "operator").mkdir(parents=True)
    (tmp_path / "artifacts" / "operator" / "meas.patch").write_text(PATCH_MEAS)
    _git(tmp_path, "init", "-q")
    return tmp_path


def _script(repo: Path, name: str, body: str) -> str:
    path = repo / "scripts" / "operator" / name
    path.write_text("#!/bin/bash\nset -euo pipefail\n" + body)
    return f"scripts/operator/{name}"


def _run(repo: Path, *extra: str) -> tuple[int, dict]:
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main(["--repo-root", str(repo), "--json", *extra])
    return rc, json.loads(buf.getvalue())


def _verdicts(report: dict) -> dict[str, str]:
    return {f["script"]: f["verdict"] for f in report["scripts"]}


# ------------------------------------------------------------------ receipt idioms


def test_op60_quoting_style_counts_as_emitting_the_receipt(repo: Path) -> None:
    """op60/pcal: a quote sits between `.py` and `emit`. Was a false FAIL."""
    s = _script(repo, "ratify_op60_style.sh", (
        'PATCH_REL="artifacts/operator/meas.patch"\n'
        'git -C "$ROOT" apply "$ROOT/$PATCH_REL"\n'
        'python3 "$ROOT/scripts/operator/ratification_receipt.py" emit \\\n'
        '  --repo-root "$ROOT" --out "$CONSOLIDATED"\n'
    ))
    rc, report = _run(repo)
    assert _verdicts(report)[s] == "PASS"
    assert rc == 0


def test_p_serve_sel_quoting_style_counts(repo: Path) -> None:
    s = _script(repo, "ratify_pserve_style.sh", (
        'git -C "$ROOT" apply "$ROOT/artifacts/operator/meas.patch"\n'
        'python3 "$ROOT"/scripts/operator/ratification_receipt.py emit --out x\n'
    ))
    assert _verdicts(_run(repo)[1])[s] == "PASS"


def test_receipt_tool_through_a_variable_counts(repo: Path) -> None:
    s = _script(repo, "ratify_var_style.sh", (
        'R=scripts/operator/ratification_receipt.py\n'
        'cat > "$ROOT/MEASUREMENT.md" < new.md\n'
        'python3 $R emit --pre /x\n'
    ))
    assert _verdicts(_run(repo)[1])[s] == "PASS"


def test_receipt_emit_definition_or_comment_is_not_an_emission(repo: Path) -> None:
    s = _script(repo, "ratify_fake_receipt.sh", (
        '# receipt_emit my-id P-X   <- only a comment\n'
        '# python3 scripts/operator/ratification_receipt.py emit\n'
        'receipt_emit() { :; }\n'
        'git -C "$ROOT" apply "$ROOT/artifacts/operator/meas.patch"\n'
    ))
    rc, report = _run(repo)
    assert _verdicts(report)[s] == "FAIL"
    assert rc == 1


# ------------------------------------------------------------------ write detection


def test_patch_targets_classify_a_script_that_never_names_the_target(repo: Path) -> None:
    """The structural rule: the patch header names MEASUREMENT.md, the script does not."""
    s = _script(repo, "ratify_patch_only.sh", (
        'PATCH="${REPO_ROOT}/artifacts/operator/meas.patch"\n'
        'git -C "${REPO_ROOT}" apply --index "${PATCH}"\n'
    ))
    finding = {f["script"]: f for f in _run(repo)[1]["scripts"]}[s]
    assert finding["verdict"] == "FAIL"
    assert finding["classified_via"] == ["patch"]
    assert finding["boundary_paths"] == ["MEASUREMENT.md"]


@pytest.mark.parametrize(
    "body",
    [
        # ratify_operating_constraints_destructive_ops_20260828.sh
        'TARGET="agents/shared/OPERATING_CONSTRAINTS.md"\ncp "${MERGED}" "${REPO_ROOT}/${TARGET}"\n',
        # ratify_measurement_annex_d_20260823.sh
        'ANNEX="$ROOT/measurement/protocols/determinism-parity.md"\ncat > "$ANNEX" <<\'EOF\'\nx\nEOF\n',
        # ratify_20260827_session.sh / eq1 / rtg09: python open(path, "w") through a variable
        'python3 - "$ROOT/agents/shared/OPERATING_CONSTRAINTS.md" <<\'PY\'\nimport sys\npath = sys.argv[1]\n'
        'open(path, "w", encoding="utf-8").write("x")\nPY\n',
        # python path-joining: no contiguous path string anywhere
        'python3 - <<\'PY\'\nimport os\np = os.path.join(root, "agents", "shared", "X.md")\n'
        'with open(p, "w") as fh: fh.write("x")\nPY\n',
        'python3 - <<\'PY\'\nfrom pathlib import Path\n(ROOT / "measurement" / "protocols" / "a.md").write_text("x")\nPY\n',
        # ratify_mi210_substrate_constants_20260803.sh
        'M="$ROOT/MEASUREMENT.md"\nprintf \'%s\\n\' "$block" >> "$M"\n',
        # ratify_v10_final_freeze_20260922.sh
        'CLAUDE_MD="${REPO_ROOT}/CLAUDE.md"\npython3 - "${CLAUDE_MD}" <<\'PY\'\nimport sys\nmd = sys.argv[1]\n'
        's = open(md).read()\nopen(md, "w").write(s)\nPY\n',
        'sed -i "s/a/b/" "$ROOT"/"MEASUREMENT.md"\n',
    ],
    ids=["cp-var", "cat-heredoc", "py-open-var", "os-path-join", "pathlib-div", "printf-append",
         "py-claude-md", "sed-split-quotes"],
)
def test_writes_through_variables_are_classified(repo: Path, body: str) -> None:
    s = _script(repo, "ratify_style.sh", body)
    rc, report = _run(repo)
    assert _verdicts(report).get(s) == "FAIL", report["scripts"]
    assert rc == 1


def test_declared_targets_classify_runtime_built_paths(repo: Path) -> None:
    s = _script(repo, "ratify_declared.sh", (
        '# ratify-targets: CLAUDE.md\n'
        'f="$(compute_target)"\n'
        'mutate "$f"\n'
    ))
    finding = {f["script"]: f for f in _run(repo)[1]["scripts"]}[s]
    assert finding["classified_via"] == ["declared"]
    assert finding["verdict"] == "FAIL"


def test_the_boundary_list_itself_is_inside_the_boundary(repo: Path) -> None:
    s = _script(repo, "ratify_widen.sh", (
        'L="$ROOT/coordination/session-bus/human_only_paths.yaml"\n'
        'printf "  - repo: epyc-root\\n" >> "$L"\n'
    ))
    finding = {f["script"]: f for f in _run(repo)[1]["scripts"]}[s]
    assert "coordination/session-bus/human_only_paths.yaml" in finding["boundary_paths"]


def test_mentions_without_writes_and_comment_only_mentions_are_ignored(repo: Path) -> None:
    _script(repo, "check_only.sh", 'grep -qF "x" "$ROOT/MEASUREMENT.md"\nsha256sum "$ROOT/CLAUDE.md"\n')
    _script(repo, "doc_only.sh", '# amends MEASUREMENT.md in a later step\necho hi > "$ROOT/out.txt"\n')
    rc, report = _run(repo)
    assert report["scripts"] == []
    assert rc == 0


def test_other_repo_globs_are_not_root_boundary(repo: Path) -> None:
    _script(repo, "eras.sh", 'echo row >> "$ORCH/orchestration/instrument_eras.yaml"\n')
    assert _run(repo)[1]["scripts"] == []


def test_wrapper_passes_by_delegation(repo: Path) -> None:
    _script(repo, "ratify_real.sh", (
        'git -C "$ROOT" apply "$ROOT/artifacts/operator/meas.patch"\n'
        'python3 "$ROOT/scripts/operator/ratification_receipt.py" emit\n'
    ))
    w = _script(repo, "run_real.sh", (
        'RATIFY_REL="scripts/operator/ratify_real.sh"\n'
        'printf "will amend MEASUREMENT.md\\n"\n'
        'ROOT="$WT" bash "$WT/$RATIFY_REL" --apply | tee "$LOG"\n'
    ))
    finding = {f["script"]: f for f in _run(repo)[1]["scripts"]}[w]
    assert finding["verdict"] == "PASS"
    assert finding["delegated_to"] == ["scripts/operator/ratify_real.sh"]


# ------------------------------------------------------------------ exemptions


def _exempt(repo: Path, script: str, commit: str) -> Path:
    path = repo / "exemptions.json"
    path.write_text(json.dumps({"exemptions": [{
        "script": script,
        "kind": "historical",
        "script_sha256": hashlib.sha256((repo / script).read_bytes()).hexdigest(),
        "applied_in": commit,
        "evidence": "test",
        "reason": "test",
    }]}))
    return path


def _historical(repo: Path) -> tuple[str, str]:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    s = _script(repo, "ratify_old.sh", 'git -C "$ROOT" apply "$ROOT/artifacts/operator/meas.patch"\n')
    _git(repo, "add", s)
    _git(repo, "commit", "-qm", "add ratifier")
    _git(repo, "apply", "artifacts/operator/meas.patch")
    _git(repo, "add", "MEASUREMENT.md")
    _git(repo, "commit", "-qm", "RATIFIED: old")
    return s, _git(repo, "rev-parse", "HEAD")


def test_valid_exemption_is_honoured(repo: Path) -> None:
    s, applied = _historical(repo)
    rc, report = _run(repo, "--exemptions", str(_exempt(repo, s, applied)))
    assert _verdicts(report)[s] == "EXEMPT"
    assert rc == 0


def test_exemption_lapses_when_the_script_is_edited(repo: Path) -> None:
    s, applied = _historical(repo)
    ex = _exempt(repo, s, applied)
    with open(repo / s, "a") as fh:
        fh.write("echo edited\n")
    rc, report = _run(repo, "--exemptions", str(ex))
    finding = {f["script"]: f for f in report["scripts"]}[s]
    assert finding["verdict"] == "FAIL"
    assert "changed since it was exempted" in finding["exemption_lapsed"]
    assert rc == 1


def test_exemption_must_cite_a_commit_that_touches_the_boundary(repo: Path) -> None:
    s, _ = _historical(repo)
    base = _git(repo, "rev-parse", "HEAD~1")  # adds the script, touches no boundary path
    rc, report = _run(repo, "--exemptions", str(_exempt(repo, s, base)))
    assert _verdicts(report)[s] == "FAIL"


def test_stale_exemption_is_an_error(repo: Path) -> None:
    s, applied = _historical(repo)
    ex = _exempt(repo, s, applied)
    (repo / s).unlink()
    rc, report = _run(repo, "--exemptions", str(ex))
    assert any("remove the stale entry" in e for e in report["errors"])
    assert rc == 2


def _pin(repo: Path, script: str, **fields) -> Path:
    path = repo / "exemptions.json"
    entry = {"script": script, "reason": "test",
             "script_sha256": hashlib.sha256((repo / script).read_bytes()).hexdigest(), **fields}
    path.write_text(json.dumps({"exemptions": [entry]}))
    return path


def test_not_a_boundary_write_overrules_only_the_text_rule(repo: Path) -> None:
    """waive_q8_cpu_prefill_v8_20260725.sh: hashes MEASUREMENT.md, writes its own JSON."""
    s = _script(repo, "waive.sh", 'sha256sum "$ROOT/MEASUREMENT.md"\ncat > "$OUT" <<JSON\n{}\nJSON\n')
    rc, report = _run(repo, "--exemptions", str(_pin(repo, s, kind="not-a-boundary-write")))
    assert _verdicts(report)[s] == "EXEMPT" and rc == 0


def test_not_a_boundary_write_cannot_overrule_a_patch(repo: Path) -> None:
    s = _script(repo, "sneaky.sh", 'git -C "$ROOT" apply "$ROOT/artifacts/operator/meas.patch"\n')
    rc, report = _run(repo, "--exemptions", str(_pin(repo, s, kind="not-a-boundary-write")))
    finding = {f["script"]: f for f in report["scripts"]}[s]
    assert finding["verdict"] == "FAIL" and "structural" in finding["exemption_lapsed"]


def test_superseded_needs_a_compliant_successor(repo: Path) -> None:
    old = _script(repo, "ratify_v1.sh", 'git -C "$ROOT" apply "$ROOT/artifacts/operator/meas.patch"\n')
    new = _script(repo, "ratify_v2.sh", 'git -C "$ROOT" apply "$ROOT/artifacts/operator/meas.patch"\n')
    ex = _pin(repo, old, kind="superseded", superseded_by=new)
    assert _verdicts(_run(repo, "--exemptions", str(ex))[1])[old] == "FAIL"  # v2 unreceipted
    with open(repo / new, "a") as fh:
        fh.write('python3 "$ROOT/scripts/operator/ratification_receipt.py" emit\n')
    rc, report = _run(repo, "--exemptions", str(ex))
    assert _verdicts(report)[old] == "EXEMPT" and rc == 0


def test_exemption_without_reason_is_refused(repo: Path) -> None:
    s = _script(repo, "waive.sh", 'sha256sum "$ROOT/MEASUREMENT.md"\necho x > "$OUT"\n')
    ex = _pin(repo, s, kind="not-a-boundary-write")
    doc = json.loads(ex.read_text()); doc["exemptions"][0]["reason"] = " "; ex.write_text(json.dumps(doc))
    assert _verdicts(_run(repo, "--exemptions", str(ex))[1])[s] == "FAIL"


# ------------------------------------------------------------------ receipts


def _receipt(repo: Path, name: str, verdict: str, at: str) -> None:
    (repo / "artifacts" / "operator" / "receipts" / name).write_text(json.dumps(
        {"ratification_id": "rid", "protocol_id": "P-X", "verdict": verdict, "emitted_at_utc": at}))


def test_preserved_refusal_superseded_by_later_ratified_is_not_an_error(repo: Path) -> None:
    _receipt(repo, "rid.refused-abc.receipt.json", "REFUSED", "2026-08-13T16:00:14Z")
    _receipt(repo, "rid.receipt.json", "RATIFIED", "2026-08-13T16:28:46Z")
    rc, report = _run(repo)
    refused = [r for r in report["receipts"] if r["verdict"] == "REFUSED"][0]
    assert refused["status"].startswith("superseded")
    assert report["errors"] == [] and rc == 0


def test_refused_receipt_at_canonical_name_is_an_error(repo: Path) -> None:
    _receipt(repo, "rid.receipt.json", "REFUSED", "2026-08-13T16:00:14Z")
    rc, report = _run(repo)
    assert any("canonical name" in e for e in report["errors"])
    assert rc == 2


def test_receipts_beside_the_decision_receipt_are_read(repo: Path) -> None:
    (repo / "artifacts" / "operator" / "x.receipt.json").write_text(json.dumps(
        {"ratification_id": "x", "verdict": "REFUSED"}))
    rc, report = _run(repo)
    assert rc == 2


# ------------------------------------------------------------------ plumbing


def test_missing_boundary_list_is_could_not_check(repo: Path) -> None:
    (repo / "coordination" / "session-bus" / "human_only_paths.yaml").unlink()
    rc, report = _run(repo)
    assert rc == 2
    assert report["errors"][0].startswith("COULD-NOT-CHECK")


def test_default_repo_root_is_this_checkout_not_workspace() -> None:
    assert mod.REPO_ROOT == ROOT


def test_live_repository_is_clean() -> None:
    """The gate itself: every boundary-writing script in THIS checkout is receipted or exempt."""
    proc = subprocess.run([sys.executable, str(MODULE_PATH)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-4000:]


# ------------------------------------------------------------------ receipt tool


def test_receipt_tool_accepts_a_doctrine_anchor_in_the_amended_file(repo: Path) -> None:
    """A doctrine ratifier (agents/shared/*.md, CLAUDE.md) must be ABLE to comply.

    Before 2026-09-26 every --anchor was looked up in MEASUREMENT.md only, so a
    doctrine amendment could not get a RATIFIED receipt without citing
    constitution text it never touched.
    """
    tool = ROOT / "scripts" / "operator" / "ratification_receipt.py"
    oc = "agents/shared/OPERATING_CONSTRAINTS.md"
    pre = repo / "pre.json"
    subprocess.run([sys.executable, str(tool), "capture", "--repo-root", str(repo),
                    "--state", oc, "--out", str(pre)], check=True, capture_output=True)
    (repo / oc).write_text("# OC\n\n- **New doctrine clause.** Text.\n")
    out = repo / "doctrine.receipt.json"
    proc = subprocess.run(
        [sys.executable, str(tool), "emit", "--repo-root", str(repo), "--pre", str(pre),
         "--protocol-id", "DOCTRINE-TEST-1", "--anchor", "- **New doctrine clause.**",
         "--ratification-id", "doctrine-test", "--no-evidence-reason", "doctrine; no measurement",
         "--validation", f"grep -qF 'New doctrine clause' {oc}", "--out", str(out)],
        capture_output=True, text=True,
    )
    receipt = json.loads(out.read_text())
    protocol = receipt["sections"]["protocol"]
    assert protocol["verdict"] == "PASS", protocol
    assert any(oc in d for d in protocol["detail"])
    assert receipt["verdict"] == "RATIFIED" and proc.returncode == 0, proc.stdout[-2000:]

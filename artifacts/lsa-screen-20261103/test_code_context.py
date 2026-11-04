import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('lsa_code_context', HERE/'code_context.py')
ctx = importlib.util.module_from_spec(spec); spec.loader.exec_module(ctx)
RECEIPT = HERE.parents[2]/'native-verifier-real-canary-20261104/receipt/receipt.json'
COMMIT = 'd424aba6eeed88004d45a10d0c98c7e52986419e'
CASE = 'lsa-runtime-cpu-command-exit'


def query(path=RECEIPT, *, label='native', commit=COMMIT, case=CASE):
    if path == RECEIPT and not RECEIPT.is_file():
        pytest.skip('original native verifier receipt is external scratch evidence')
    return ctx.collect([path], repo_label=label, commit=commit, case=case)


def test_original_code_revision_observation():
    out = query()
    assert not out['refused'] and len(out['claims']) == 1
    claim = out['claims'][0]
    native = json.loads(RECEIPT.read_text())
    assert claim['claim_id'] == 'clm_ci-fixture:' + native['receipt_sha256']
    assert claim['value'] is True and claim['grade'] == ['Judged', 'Located']
    assert claim['native_locator'] == str(RECEIPT.resolve())


@pytest.mark.parametrize('kwargs', [{'label':'root'}, {'commit':'0'*40}, {'case':'lsa-wrong-case'}])
def test_wrong_revision_label_or_case_is_not_visible(kwargs):
    result = query(**kwargs)
    assert result['claims'] == [] and len(result['omitted']) == 1


@pytest.mark.skipif(not RECEIPT.is_file(), reason='original native verifier receipt is external scratch evidence')
def test_tampered_native_receipt_refuses(tmp_path):
    copied = tmp_path/'receipt'; shutil.copytree(RECEIPT.parent, copied)
    path = copied/'receipt.json'; record = json.loads(path.read_text()); record['repositories']['native'] = '0'*40
    path.write_text(json.dumps(record))
    result = query(path)
    assert not result['claims'] and len(result['refused']) == 1


def test_unusable_grade_not_visible(monkeypatch):
    monkeypatch.setattr(ctx, 'grade', lambda claim: ('Refused', 'Invalid', ['test']))
    assert query()['claims'] == []


def test_missing_readset_not_visible(monkeypatch):
    original = ctx.ci_conformance.native_rows
    def missing(path):
        rows = original(path)
        rows[0]['record']['readset'] = []
        return rows
    monkeypatch.setattr(ctx.ci_conformance, 'native_rows', missing)
    assert query()['claims'] == []


@pytest.mark.parametrize('status', ['failure', 'skipped'])
def test_synthetic_failure_or_skipped_is_honest(tmp_path, status):
    sys.path.insert(0, str(HERE.parents[1]))
    from scripts.ci.native_conformance import capture_fixture_execution
    repo = tmp_path/'repo'; repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)], check=True)
    source = repo/'fixture.txt'; source.write_text('synthetic')
    subprocess.run(['git','-C',str(repo),'add','fixture.txt'], check=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture'], check=True)
    commit = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'], text=True).strip()
    junit = tmp_path/'unit.xml'; out = tmp_path/'receipt'
    xml = f'<testsuite tests="1" failures="{int(status == "failure")}" errors="0" skipped="{int(status == "skipped")}"><testcase classname="lsa_native_unit" name="{CASE}"><{status}/></testcase></testsuite>'
    code = f'from pathlib import Path; import sys; Path({str(junit)!r}).write_text({xml!r}); sys.exit({int(status == "failure")})'
    capture_fixture_execution(argv=[sys.executable,'-c',code], cwd=repo, junit=junit, output=out,
        repositories={'native':repo}, read_paths=[source], selections=[CASE])
    result = query(out/'receipt.json', commit=commit)
    assert not result['refused']
    if status == 'failure':
        assert len(result['claims']) == 1 and result['claims'][0]['value'] is False
    else:
        assert not result['claims'] and result['omitted'][0]['reason'] == 'no decided verifier claim'

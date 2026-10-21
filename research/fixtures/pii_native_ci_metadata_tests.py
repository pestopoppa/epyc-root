"""Hosted-only actual staged-hook controls; explicit synthetic fixture literals."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

POLICY = Path(os.environ['PII_NATIVE_POLICY'])
sys.path.insert(0, str(POLICY))
sys.path.insert(0, str(POLICY/'scripts/vidya'))
from scripts.hooks import pii_staged_capture as capture
from scripts.vidya.adapters import pii_staged_gate as adapter
from claim_tuple import grade
ROWS = [json.loads(x) for x in Path(os.environ['PII_NATIVE_FIXTURES']).read_text().splitlines()]
CANDIDATE = POLICY/'scripts/hooks/pii_precommit.sh'
BASELINE = Path(os.environ['PII_NATIVE_BASELINE'])

def git(repo, *args):
    return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True)

@pytest.fixture
def repo(tmp_path):
    p=tmp_path/'staged-repo';p.mkdir()
    git(p,'init','--quiet');git(p,'config','user.name','Synthetic staged controls')
    git(p,'config','user.email','fixture@example.invalid');git(p,'config','commit.gpgsign','false')
    git(p,'config','core.hooksPath','.git/hooks')
    git(p,'commit','--allow-empty','--quiet','-m','Synthetic baseline')
    return p

def stage(repo, row):
    p=repo/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(row['text'])
    git(repo,'add','--',row['path'])
    return p

def run(repo, hook):
    receipts=repo/'.git/epyc-private/pii-gates'
    previous=set(receipts.glob('*/receipt.json'))
    process=subprocess.run(['bash',str(hook)],cwd=repo,capture_output=True,timeout=60)
    originals=set(receipts.glob('*/receipt.json'))-previous
    assert len(originals)==1,'one original existing-family receipt required'
    path=next(iter(originals));record,_=capture.read_receipt(path)
    assert record['policy'][0]['artifact']['sha256']==hashlib.sha256(hook.read_bytes()).hexdigest()
    assert record['pii_staged_policy_check_passed'] is (process.returncode==0)
    claim=adapter.project(adapter.native_rows(path)[0])
    assert grade(claim)[:2]==('Judged','Located')
    return process,record,path

@pytest.mark.parametrize('row',ROWS,ids=[r['id'] for r in ROWS])
def test_exact_staged_native_metadata_boundaries(repo,row):
    stage(repo,row)
    process,record,path=run(repo,CANDIDATE)
    assert process.returncode==int(row['expected_match']),'candidate must preserve declared staged decision'
    if row['expected_match']:
        assert ('['+row['labels'][0]['label']+']').encode() in process.stderr,'actual scanner label required'
    item=record['inputs'][0]
    assert (path.parent/item['artifact']['name']).read_text()==row['text']

@pytest.mark.parametrize('row',[r for r in ROWS if r['id'].startswith('original-')],ids=[r['id'] for r in ROWS if r['id'].startswith('original-')])
def test_original_hook_reproduces_eight_metadata_false_positives(repo,row):
    stage(repo,row)
    process,record,_=run(repo,BASELINE)
    assert process.returncode==1 and b'[account_number]' in process.stderr
    assert record['pii_staged_policy_check_passed'] is False

@pytest.mark.parametrize('staged_account',[False,True])
def test_staged_original_wins_over_opposite_worktree(repo,staged_account):
    allowed=next(r for r in ROWS if r['id']=='original-suite-id-0')
    account=next(r for r in ROWS if r['id']=='json-account')
    row=dict(account if staged_account else allowed)
    row["path"]=allowed["path"]
    p=stage(repo,row)
    p.write_text((allowed if staged_account else account)['text'])
    process,record,path=run(repo,CANDIDATE)
    assert process.returncode==int(staged_account)
    item=record['inputs'][0]
    assert (path.parent/item['artifact']['name']).read_text()==row['text']

@pytest.mark.parametrize('row',[r for r in ROWS if r['id'].startswith('original-job-')],ids=[r['id'] for r in ROWS if r['id'].startswith('original-job-')])
def test_published_f250_hook_reproduces_job_metadata_false_positives(repo,row):
    stage(repo,row)
    process,record,_=run(repo,Path(os.environ['PII_NATIVE_JOB_BASELINE']))
    assert process.returncode==1 and b'[account_number]' in process.stderr
    assert record['pii_staged_policy_check_passed'] is False

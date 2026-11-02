"""Run the current native planner-context canary, never trust plan-supplied text.

This verifier invokes the tracked canary itself in fresh private scratch, with
source views bound to current origin/main. A failed or unavailable replay is a
refusal, not a measurement. The predeclared historical target is code-owned.
"""
from __future__ import annotations
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT_VIEW = Path('/mnt/raid0/llm/worktrees/inf22-canary-root-origin')
RESEARCH_VIEW = Path('/mnt/raid0/llm/worktrees/inf22-canary-research-origin')
ROOT_SOURCE = Path('/workspace')
RESEARCH_SOURCE = Path('/workspace/repos/epyc-inference-research')
PYTHON = Path('/workspace/repos/epyc-orchestrator/.venv/bin/python3')
KNOWN = 'akm-cpu-fa-query-major-row-schedule'
OWNERSHIP_FILES = ('entry.py','native_authorization.py','planning_canary.py','watch.py',
                   'owned.py','m4_cgroup_guard.py','lease_owner.py')


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.PIPE).strip()


def _verify_view(view: Path, canonical: Path, protected: list[str]) -> str:
    # git-common-dir proves this is an actual worktree of the canonical repo;
    # origin/main identifies the independent authority, not the supplied plan.
    common = Path(_git(view,'rev-parse','--path-format=absolute','--git-common-dir')).resolve()
    expected = Path(_git(canonical,'rev-parse','--path-format=absolute','--git-common-dir')).resolve()
    head = _git(view,'rev-parse','HEAD')
    if common != expected or head != _git(canonical,'rev-parse','origin/main'):
        raise ValueError('canary source view is not canonical current origin/main')
    if _git(view,'status','--porcelain','--untracked-files=all','--',*protected):
        raise ValueError('canary source view has modified/untracked protected code')
    return head


def verify_native_result(result: dict, summary: dict, belief: str, prompt: str) -> None:
    """Check only real replay outputs; synthetic tests do not establish wiring."""
    status = result.get('status')
    # Native A's formation-guard assertion is a separate AutoKernel gate.
    # Do not relabel its FAIL: accept it here only when the exact native
    # result says known context is present and its sole failed check is guard.
    expected_guard = True if status == 'PASS' else False if status == 'FAIL' else None
    if result.get('loop') != 'A' or expected_guard is None or result.get('known_line') is not True or result.get('guard_refusal') is not expected_guard or result.get('canonical_ledger_unchanged') is not True or result.get('telemetry_unchanged') is not True:
        raise ValueError('native planning context is unavailable or inconsistent')
    if summary.get('belief_status') != 'ready' or not summary.get('section_bytes') or not summary.get('prior_rows') or not summary.get('tried_index_count'):
        raise ValueError('native planner context or tried history missing')
    if not any(KNOWN in line and 'measured_null' in line and '-1.10%' in line for line in belief.splitlines()):
        raise ValueError('code-owned historical conclusion absent')
    if '## Already tried' not in prompt or KNOWN not in prompt.split('## Already tried',1)[1][:20000]:
        raise ValueError('historical conclusion absent from actual already-tried context')
    hit = (summary.get('known_hits') or {}).get(KNOWN) or {}
    if hit.get('in_belief_section') is not True or hit.get('in_already_tried_window') is not True:
        raise ValueError('native source summary disagrees with actual context')


def _verify_owned_sources() -> None:
    local = Path(__file__).resolve().parent
    trusted = ROOT_VIEW/'scripts/benchmark/m4_cpu_ownership'
    for name in OWNERSHIP_FILES:
        if (local/name).read_bytes() != (trusted/name).read_bytes():
            raise ValueError(f'owner source differs from reviewed origin/main: {name}')


def run() -> dict:
    root_head = _verify_view(ROOT_VIEW, ROOT_SOURCE, ['scripts/vidya','scripts/benchmark/m4_cpu_ownership','research/intake_index.yaml'])
    research_head = _verify_view(RESEARCH_VIEW, RESEARCH_SOURCE, ['scripts/kernel_rnd'])
    _verify_owned_sources()
    if not PYTHON.is_file():
        raise ValueError('canary interpreter unavailable')
    scratch = Path('/mnt/raid0/llm/tmp') / ('m4-native-canary-' + uuid.uuid4().hex)
    env = {'PATH':'/usr/bin:/bin',
           'CANARY_SCRATCH':str(scratch), 'CANARY_STATE':str(scratch/'state/A'),
           'CANARY_ROOT':str(ROOT_VIEW), 'CANARY_ORCH_SOURCE':'/workspace/repos/epyc-orchestrator',
           'CANARY_INDEX':str(ROOT_VIEW/'research/intake_index.yaml'),
           'EPYC_ROOT_REPO':str(ROOT_VIEW), 'PYTHONDONTWRITEBYTECODE':'1',
           'GIT_OPTIONAL_LOCKS':'0','PYTHONPATH':str(RESEARCH_VIEW)+':'+str(RESEARCH_VIEW/'scripts/kernel_rnd')+':'+str(ROOT_VIEW/'scripts/vidya'),
           'OMP_NUM_THREADS':'1'}
    canary = ROOT_VIEW/'scripts/vidya/canary'
    setup=subprocess.run([str(PYTHON),str(canary/'setup_scratch.py')],cwd='/tmp',env=env,capture_output=True,text=True,timeout=120)
    if setup.returncode:
        raise ValueError(f'canary scratch setup refused: {setup.stderr[-500:]}')
    proc=subprocess.run([str(PYTHON),str(canary/'run.py'),'a','gate',str(ROOT_VIEW)],cwd='/tmp',env=env,capture_output=True,text=True,timeout=240)
    markers=[line[len('GATE_RESULT: '):] for line in proc.stdout.splitlines() if line.startswith('GATE_RESULT: ')]
    if len(markers) != 1:
        raise ValueError(f'native planning canary missing result; scratch={scratch}; stderr={proc.stderr[-2500:]}')
    native=json.loads(markers[0])
    if {'PASS':0,'FAIL':1}.get(native.get('status')) != proc.returncode:
        raise ValueError(f'native planning canary refused or returned UNKNOWN; scratch={scratch}; result={markers}; stderr={proc.stderr[-2500:]}')
    out=scratch/'A-gate'
    summary=json.loads((out/'summary.json').read_bytes())
    reader = ROOT_VIEW/'scripts/vidya/loop_beliefs.py'
    reader_hash = hashlib.sha256(reader.read_bytes()).hexdigest()
    if (summary.get('root_head') != root_head or summary.get('root_used') != str(ROOT_VIEW)
            or summary.get('reader') != str(reader) or summary.get('reader_sha256') != reader_hash):
        raise ValueError('native canary used wrong root or reader identity')
    verify_native_result(native,summary,(out/'belief_section.txt').read_text(),(out/'prompt.txt').read_text())
    if _verify_view(ROOT_VIEW,ROOT_SOURCE,['scripts/vidya','scripts/benchmark/m4_cpu_ownership','research/intake_index.yaml']) != root_head or _verify_view(RESEARCH_VIEW,RESEARCH_SOURCE,['scripts/kernel_rnd']) != research_head:
        raise ValueError('canary source changed during replay')
    _verify_owned_sources()
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'m4-native-stdout.txt').write_text(proc.stdout)
    (out/'m4-native-stderr.txt').write_text(proc.stderr)
    receipt={'schema':'epyc.m4.native_planner_canary.v1','m4_context_visibility':'PASS',
             'formation_guard_result':native['status'], 'root_head':root_head,
             'research_head':research_head,'scratch':str(scratch),'result':native,
             'native_stdout_sha256':digest(out/'m4-native-stdout.txt'),
             'summary_sha256':digest(out/'summary.json'),'prompt_sha256':digest(out/'prompt.txt'),
             'belief_sha256':digest(out/'belief_section.txt')}
    with (out/'m4-verifier-receipt.json').open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,sort_keys=True,indent=2);stream.write('\n')
    return receipt

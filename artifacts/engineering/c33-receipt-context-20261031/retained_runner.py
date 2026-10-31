#!/usr/bin/env python3
"""C33-only retained fixture controls. No cleanup, rename, delete, or child process."""
from __future__ import annotations
import argparse
import atexit
import hashlib
import json
import os
from pathlib import Path
import re
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--new-tests',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--baseline',action='store_true')
args=parser.parse_args()
root=args.source_root.resolve(strict=True)
test=args.new_tests.resolve(strict=True)
output=args.output.absolute()
if output.exists() or output.is_symlink():raise SystemExit('fresh retained output required; never remove/reuse it')
output.mkdir(mode=0o700)
fixtures=output/'fixtures';fixtures.mkdir(mode=0o700)
os.environ['C33_RETAINED_BASE']=str(fixtures)
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
for name in ['PYTEST_ADDOPTS','PYTEST_PLUGINS','PYTEST_DEBUG']:
    os.environ.pop(name,None)
sys.path.insert(0,str(root))
blocked=[];probes=[];probing=[False]
forbidden={'os.remove','os.rmdir','os.rename','shutil.rmtree',
           'subprocess.Popen','os.system','os.posix_spawn','os.fork','os.forkpty'}
def audit(event,values):
    if event in forbidden:
        item={'event':event,'arguments':repr(values)}
        (probes if probing[0] else blocked).append(item)
        raise RuntimeError('retained C33 runner refused '+event)
sys.addaudithook(audit)
# These are synthetic audit events only, never calls to an OS deletion/rename API.
for event in ['os.remove','os.rmdir','os.rename','shutil.rmtree','subprocess.Popen']:
    probing[0]=True
    try:sys.audit(event,'synthetic guard probe only')
    except RuntimeError:pass
    else:raise AssertionError('audit guard did not refuse '+event)
    finally:probing[0]=False

import pytest  # after bytecode/plugin restrictions and operation guard

class Factory:
    _retention_policy='all'
    def __init__(self,path):self.path=path;self.count=0
    def getbasetemp(self):return self.path
    def mktemp(self,basename,numbered=True):
        self.count+=1
        name=re.sub(r'[^A-Za-z0-9_.-]','_',str(basename))[:80]
        if not name or name in ('.','..'):name='fixture'
        path=self.path/(name+'-'+str(self.count))
        path.mkdir(mode=0o700)
        if path.resolve().parent!=self.path.resolve():raise RuntimeError('fixture escaped retained root')
        return path
factory=Factory(fixtures)
class RetainedFixtures:
    @pytest.fixture(scope='session',name='tmp_path_factory')
    def factory_fixture(self):return factory
    @pytest.fixture(name='tmp_path')
    def path_fixture(self,request,tmp_path_factory):
        return tmp_path_factory.mktemp(request.node.name)

existing=[
 'test_spent_receipt_is_found_only_for_a_status_that_means_signed',
 'test_a_spent_gate_is_ANNOTATED_and_never_suppressed',
 'test_an_unspent_gate_is_presented_with_no_annotation',
 'test_a_gate_already_in_the_queue_gets_a_notice_because_the_block_is_never_rewritten',
]
pytest_args=['-q','-p','no:tmpdir','-p','no:cacheprovider','--capture=sys','-o','addopts=',str(test)]
if not args.baseline:
    pytest_args += [str(root/'tests/test_session_bus.py')+'::'+name for name in existing]
code=pytest.main(pytest_args,plugins=[RetainedFixtures()])
# Flush and clear registered callbacks while the refusal hook is active, before receipt.
atexit._run_exitfuncs()
module=sys.modules.get('scripts.coordination.session_bus_coordinator')
actual=Path(module.__file__).resolve() if module is not None else None
if actual != (root/'scripts/coordination/session_bus_coordinator.py').resolve():
    raise RuntimeError('tests did not import the selected coordinator source')
files=sorted(p for p in fixtures.rglob('*') if p.is_file())
manifest=[{'path':str(p.relative_to(output)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files]
receipt={'scope':'C33 retained model-free source controls; no live bus/model/native run',
         'pytest_returncode':int(code),'source_root':str(root),'coordinator_sha256':hashlib.sha256(actual.read_bytes()).hexdigest(),
         'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),
         'fixture_count':sum(p.is_dir() for p in fixtures.iterdir()),'pytest_factory_fixture_count':factory.count,'retained_files':manifest,
         'blocked_real_operations':blocked,'synthetic_audit_probes':probes,
         'pytest_tmpdir_plugin':False,'pytest_cache_plugin':False,'plugin_autoload':False,
         'retention':'all fixtures retained; no cleanup/current symlink/lock files created',
         'public_evidence':'synthetic fixtures and source hashes only; historical deletion audit remains separate'}
with (output/'RECEIPT.json').open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
print(json.dumps({'pytest_returncode':int(code),'retained_files':len(manifest),'fixture_count':sum(p.is_dir() for p in fixtures.iterdir()),'pytest_factory_fixture_count':factory.count,'blocked_real_operations':len(blocked),'receipt':str(output/'RECEIPT.json')}))
raise SystemExit(1 if blocked else int(code))

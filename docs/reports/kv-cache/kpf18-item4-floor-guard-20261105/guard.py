"""Prospective item-4 mixed-batch witness guard. No native source or request binding is manufactured here."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'kpf174-prefix-request-integration-20261105' / 'layout_witness.py'
spec = importlib.util.spec_from_file_location('kpf_layout', ROOT)
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)

class Refused(ValueError): pass

def guard(raw, *, target, src, decoders, prefix):
    """Require independently captured {slot,task} bindings; returns selected raw native witness.

    Binding to HTTP and executable/library custody MUST be performed by the caller;
    passing this guard proves neither. Target must be in slot 3, source 0,
    decoders 1 and 2. Each selected native batch must contain source prefill,
    two decoder rows, and target prefix-boundary prefill.
    """
    bindings=[src,*decoders,target]
    if len(decoders)!=2 or any(type(x)!=dict for x in bindings):
        raise Refused('four task bindings required')
    if [x.get('slot') for x in bindings] != [0,1,2,3]:
        raise Refused('slot allocation mismatch')
    tasks=[x.get('task') for x in bindings]
    for x in bindings:
        response=x.get('response') or {}
        t=response.get('timings') or {}
        if response.get('http') != 200 or t.get('id_slot') != x['slot'] or t.get('id_task') != x.get('task'):
            raise Refused('missing or mismatched final HTTP task binding')
    if any(type(x)!=int or x<0 for x in tasks) or len(set(tasks))!=4:
        raise Refused('invalid/duplicate tasks')
    try:
        w=layout.witness(raw,target['task'],target['slot'],prefix)
    except (layout.Invalid, KeyError) as e:
        raise Refused(str(e)) from e
    rows=w['rows']
    expected={(0,src['task'],'prefill'), (1,decoders[0]['task'],'decode'),
              (2,decoders[1]['task'],'decode'), (3,target['task'],'prefill')}
    actual={(r[0],r[1],r[4]) for r in rows}
    if not expected.issubset(actual) or not actual.issubset(expected):
        raise Refused('not exact requested mixed-batch tasks/phases')
    return w

def compare(a,b):
    """Fail closed unless full selected native geometry and batch rows match."""
    r=layout.compare(a,b)
    if a.get('cells') != b.get('cells'):
        raise Refused('native cell ownership masks differ')
    if r['verdict']!='MATCHED':
        raise Refused('physical layout or batch mismatch')
    return r

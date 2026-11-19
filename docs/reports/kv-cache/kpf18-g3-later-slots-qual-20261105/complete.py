import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
try:
    r=json.loads(Path(os.environ['G3_LATER_RESULT']).read_text())
    assert r['schema']=='kpf18.g3.later-slots.v1' and r['status']=='PASS' and r['controls']==12 and r['error'] is None
    assert {(o['phase'],o['mode']) for o in r['observations']}=={(p,m) for p in (2,3) for m in ('success','headers','body','trickle','stop_headers','stop_body')}
    for o in r['observations']:
        phase,mode=o['phase'],o['mode']
        calls=o['calls']
        assert o['peer_joined'] and len(calls)>=phase and o['elapsed_s']<3
        assert all(c['status']=='returned' for c in calls[:phase-1])
        expected='SyntheticStop' if mode.startswith('stop_') else ('returned' if mode=='success' else 'TimeoutError')
        assert calls[phase-1]['status']==expected
        assert 0<=calls[phase-1]['end']-calls[phase-1]['start']<.8
        terminal='returned' if mode=='success' else ('SyntheticStop' if mode.startswith('stop_') else ('TimeoutError' if phase==3 else 'Deadline'))
        assert o['status']==terminal
        if mode=='success':assert len(calls)==3
        assert all(c['status'] not in ('GrantStop','GrantDeadline') for c in calls)

    assert r['inputs']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
    assert not (ROOT/'STOP').exists()
except (OSError,ValueError,KeyError,TypeError,AssertionError):sys.exit(1)

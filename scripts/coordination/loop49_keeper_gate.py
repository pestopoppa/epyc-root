#!/usr/bin/env python3
"""Fail-closed v7f candidate hook. Never writes production grants or moves rows."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
from types import SimpleNamespace
from qualify_launcher import load, verify, static_check, scheduling_state, run, Refused


def options(manifest=None):
    root = Path(os.environ['WS58_ROOT'])
    return SimpleNamespace(manifest=str(manifest), nonce_store=os.environ['WS58_NONCE_STORE'],
        allowlist=os.environ['WS58_ENGINE_ALLOWLIST'], policy=str(root/'scripts/coordination/dryrun_disk_policy.json'),
        flags_dir=os.environ['WS58_FLAGS_DIR'], fingerprint_now=False)


def manifests(root):
    result=[]
    for directory in (root/'ready',root/'ready'/'armed'):
        for p in directory.glob('*.json'):
            try: result.append((p,load(p)))
            except (ValueError,OSError): pass
    return result


def state(path, namespace=False):
    args=options(path); args.fingerprint_now=namespace
    m=load(path)
    if m.get('hold') is not None: raise Refused('hold='+str(m['hold']))
    flags=Path(args.flags_dir)
    if any((flags/'grants'/(m['id']+ext)).exists() for ext in ('.ended','.complete','.grant')):
        raise Refused('terminal-or-live-id')
    verify(m,args)
    active=[other for p,other in manifests(flags) if other['id'] != m['id'] and
            ((flags/'grants'/(other['id']+'.grant')).exists() or p.parent.name=='armed')]
    # READY port reservations are checked independently of active resources.
    for p,other in manifests(flags):
        if other['id'] != m['id'] and set(m['ports']) & set(other.get('ports',[])):
            raise Refused('port-overlap')
    stats=os.statvfs(flags)
    result=scheduling_state(m,active,stats.f_bavail*stats.f_frsize/1024**3,args.policy)
    return m,result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('scan','before-arm','pending'))
    p.add_argument('--manifest'); p.add_argument('--dry',action='store_true')
    args=p.parse_args()
    flags=Path(os.environ['WS58_FLAGS_DIR']); ready=Path(os.environ.get('WS58_READY_DIR',str(flags/'ready')))
    if args.command=='before-arm':
        try:
            m,status=state(Path(args.manifest),True)
            if status!='READY-QUALIFIED': print(status); return 2
            return 0
        except Exception as exc: print('READY-SKIP qual:'+str(exc)); return 2
    for path in sorted(ready.glob('*.json')):
        rid=path.stem
        try:
            if args.command=='pending':
                m=load(path); opts=options(path); static_check(m,opts.allowlist)
                try: verify(m,opts); continue
                except Exception: pass
                if args.dry:
                    print('QUAL-PENDING '+rid); continue
                # The scheduler must issue this qualification compute grant;
                # never steal supposedly idle CPUs based on a sample.
                grant=os.environ.get('WS58_QUAL_COMPUTE_GRANT')
                if not grant: raise Refused('qualification-compute-grant-required')
                from dryrun_check import parse_grant
                import time
                regions,start,end=parse_grant(Path(grant))
                if not start.timestamp() <= time.time() < end.timestamp()-m.get('qual_timeout_s',300):
                    raise Refused('qualification-compute-grant-not-current')
                opts.nonce=secrets.token_hex(32); opts.regions=regions; opts.out=None
                run(m,opts)
            else:
                m,status=state(path)
                if status!='READY-QUALIFIED':
                    print('\t'.join(('bad','-',rid,status))); continue
                print('\t'.join(('ok',str(m.get('priority_rank',1e17)),rid,str(m['regions']),
                    str(m['launcher']['path'] if isinstance(m['launcher'],dict) else m['launcher']),str(m['window_s']),str(m['gib']))))
        except Exception as exc:
            if args.command=='scan': print('\t'.join(('bad','-',rid,'qual:'+str(exc))))
            else: print('QUAL-SKIP '+rid+': '+str(exc))
    return 0

if __name__=='__main__': sys.exit(main())

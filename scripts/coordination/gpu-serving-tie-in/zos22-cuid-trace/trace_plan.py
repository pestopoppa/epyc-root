#!/usr/bin/env python3
"""Prepare a source-bound, non-executing GDB plan to inspect a compiler child.

No compiler is launched by this helper. Review the emitted plan before use;
the debugger must stop at the first child exec before any frontend instruction.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shlex
from pathlib import Path

EXPECTED_DB='cd08bb489fbc6c67a28f870b598fff1a7cdf6790274435b0e8ab34e71d9ed832'
EXPECTED_MAP='f29c69ae9490787f747f430d77400ef9c03e0b44d3a6a05d774161f60d12d149'
COMPILER='/opt/rocm/lib/llvm/bin/clang++'
EXPECTED_COMPILER='d7abf6eb6db27e3ead0be22aed5688b51ea4ab64831476f68434087155a68b21'
EXPECTED_GDB='e4602ab9111e3f6cc481933e9b80695e5f074a74039a6bb45bf55fa2498dc017'
BASELINE=Path('/mnt/raid0/llm/kernels/builds/gpu-20261024-c72ec82f5-c5')

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def hip_symbol(cuid):
    return '__hip_cuid_'+hashlib.md5(cuid.encode()).digest()[:8][::-1].hex()

def validate_command(row, rel, scratch):
    argv=shlex.split(row['command'])
    if not argv or argv[0]!=COMPILER or argv.count('-o')!=1 or argv.count('-c')!=1:
        raise ValueError('unexpected compiler command')
    if any(x.startswith(('-cuid=', '-fuse-cuid=', '-save-temps', '-MJ', '-MF', '-serialize-diagnostics')) for x in argv):
        raise ValueError('unsafe or overridden driver option')
    inp=Path(argv[argv.index('-c')+1]).resolve(strict=True)
    if not str(inp).endswith('/ggml/src/'+rel) or str(inp)!=str(Path(row['file']).resolve(strict=True)):
        raise ValueError('source path mismatch')
    target=Path(argv[argv.index('-o')+1])
    if target.is_absolute() or not (scratch/target).resolve().is_relative_to(scratch.resolve()):
        raise ValueError('compiler output escapes isolated scratch cwd')
    return argv,inp,target

def make_plan(db, mapping, rel, scratch, gdb):
    if sha(db)!=EXPECTED_DB or sha(mapping)!=EXPECTED_MAP or sha(COMPILER)!=EXPECTED_COMPILER or sha(gdb)!=EXPECTED_GDB:
        raise ValueError('compiler, debugger, commands, or CUID map identity mismatch')
    meta=json.loads(Path(mapping).read_text());entry=meta['sources'][rel]
    rows=[r for r in json.loads(Path(db).read_text()) if r['file'].endswith('/ggml/src/'+rel)]
    if len(rows)!=1:raise ValueError('source command missing or ambiguous')
    scratch=Path(scratch).resolve(strict=True)
    if not scratch.is_dir() or not str(scratch).startswith('/mnt/raid0/llm/tmp/gpu-serving-tie-in/'):
        raise ValueError('scratch must be under task tmp root')
    argv,inp,target=validate_command(rows[0],rel,scratch)
    if sha(inp)!=entry['source_sha256'] or sha(BASELINE/entry['baseline_object_relative_path'])!=entry['baseline_object_sha256']:
        raise ValueError('baseline source or object identity mismatch')
    configs=[Path('/opt/rocm/lib/llvm/bin/clang++.cfg'),Path('/opt/rocm/lib/llvm/bin/rocm.cfg')]
    if [sha(p) for p in configs]!=['e795800978f7e1ad08f20c0b3d51b97fe34c17204f6a0a71cac55de593524e40','f727028429d05c7b24050d54d06f7a92ec8a785b13ac4e664ab609073bcb0fe5']:
        raise ValueError('compiler config changed')
    return {'schema':'zos22.cuid-trace-plan.v1','compiler_argv':argv,'cwd':str(scratch),'output':str(target),
            'baseline_symbol':'__hip_cuid_'+entry['cuid'],'source_sha256':entry['source_sha256'],
            'baseline_object_sha256':entry['baseline_object_sha256'],'commands_sha256':EXPECTED_DB,
            'map_sha256':EXPECTED_MAP,'compiler_sha256':EXPECTED_COMPILER,'gdb_sha256':EXPECTED_GDB,
            'compiler_configs':{str(p):sha(p) for p in configs},
            'scope':'plan only; first child exec and no baseline output writes must be proven before real use'}

def verify_capture(plan, argv):
    if not isinstance(argv,list) or '-cc1' not in argv:
        raise ValueError('captured exec is not a compiler frontend')
    vals=[x.split('=',1)[1] for x in argv if x.startswith('-cuid=')]
    if len(vals)!=1 or not vals[0] or hip_symbol(vals[0])!=plan['baseline_symbol']:
        raise ValueError('captured CUID does not reproduce baseline symbol')
    return vals[0]

def main():
    p=argparse.ArgumentParser();p.add_argument('--commands',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--source',required=True);p.add_argument('--scratch',type=Path,required=True);p.add_argument('--gdb',type=Path,default=Path('/usr/bin/gdb'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if os.environ.get('FILLER_ID') or os.environ.get('FILLER_DRYRUN'):raise ValueError('preparation forbidden inside grant')
    plan=make_plan(a.commands,a.map,a.source,a.scratch,a.gdb)
    with a.output.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
if __name__=='__main__':main()

"""Descriptive C5/C6 GPU native custody; never returns a G-AK pass verdict."""
import dataclasses
import hashlib
import json
from pathlib import Path

from strict_capture import read_complete

SOURCE='729599d69871181d67af715a4c2f9162d5153a2e'
C5=Path('/mnt/raid0/llm/kernels/builds/gpu-20261024-c72ec82f5-c5')
C6=Path('/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6')
EXPECTED=[f'{image}-{op}' for image in ('C5','C6') for op in
          ('MUL_MAT','MUL_MAT_ID','FLASH_ATTN_EXT')]+['C6-G10']


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def validate_native(out, rc):
    out=Path(out)
    native=json.loads((out/'result.json').read_text())
    assert rc==0 and native['source_sha']==SOURCE and native['status']=='NATIVE_COMPLETE'
    assert native['process']['children_drained'] and native['process']['reason'] is None
    assert native['process']['rc']==0 and native['qualification_only'] is False
    raw=json.loads((out/'native-records.json').read_text())
    assert raw['source_sha']==SOURCE and raw['aggregate_gate_pass'] is None
    records=raw['records']
    assert len(records)==15 and len({r['raw_log'] for r in records})==15
    phases=[r for r in records if r['name'] in EXPECTED]
    assert [r['name'] for r in phases]==EXPECTED
    for r in records:
        for key,digest in [('raw_log','raw_sha256'),('stderr_log','stderr_sha256')]:
            p=Path(r[key])
            assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(out.resolve())
            assert sha(p)==r[digest]
    checks=[]
    for r in phases:
        name=r['name'];image=C5 if name.startswith('C5-') else C6
        sampler=r.get('sampler') or {};maps=r.get('gpu_maps_during',{})
        assert r['confirmed_dead'] and sampler.get('own_pid_kfd_reads',0)>=2
        assert sampler.get('own_pid_peak_vram_bytes',0)>0 and maps
        assert all(v['inside_selected_image'] and Path(v['resolved']).is_relative_to((image/'bin').resolve())
                   and sha(v['resolved'])==v['sha256'] for v in maps.values())
        cases=read_complete(Path(r['raw_log']).read_text(),r['native_rc'])
        assert [dataclasses.asdict(c) for c in cases]==r['native_cases']
        if name=='C6-G10':
            assert len(cases)==25 and all('g10=' in c.params for c in cases)
        status={s:sum(c.status==s for c in cases) for s in ('ok','fail','not_supported')}
        failures=[{'params':c.params,'metric_id':p.metric_id,'residual':p.residual,
                   'tolerance':p.tolerance,'suite_seed':p.suite_seed,'transform':p.transform}
                  for c in cases for p in c.properties if p.passed is False]
        assert len(failures)==r['failed_property_count']
        assert status['fail']==r['failed_case_count']
        assert status['not_supported']==r['unsupported_count']
        checks.append({'name':name,'native_rc':r['native_rc'],'case_count':len(cases),
                       'status_counts':status,'failed_property_count':r['failed_property_count'],
                       'property_failures':failures,
                       'raw_sha256':r['raw_sha256'],'stderr_sha256':r['stderr_sha256'],
                       'own_peak_vram_bytes':sampler['own_pid_peak_vram_bytes'],
                       'own_kfd_reads':sampler['own_pid_kfd_reads']})
    desc=json.loads((out/'DESCRIPTIVE.json').read_text())
    assert desc['source_sha']==SOURCE and desc['full_gak_pass'] is None
    assert [x['name'] for x in desc['cohorts']]==EXPECTED
    for a,b in zip(checks,desc['cohorts']):
        assert a['native_rc']==b['native_rc'] and a['status_counts']==b['status_counts']
        assert a['property_failures']==b['property_failures']
        assert a['raw_sha256']==b['raw_sha256'] and a['stderr_sha256']==b['stderr_sha256']
        assert b['input_bytes'].startswith('UNKNOWN')
    return {'native_result_sha256':sha(out/'result.json'),
            'native_records_sha256':sha(out/'native-records.json'),
            'descriptive_sha256':sha(out/'DESCRIPTIVE.json'),
            'records':len(records),'phases':checks,
            'input_byte_pairing':'UNKNOWN; suite seed and case names are not byte proof',
            'gpu_execution':True,'full_gak_pass':None}

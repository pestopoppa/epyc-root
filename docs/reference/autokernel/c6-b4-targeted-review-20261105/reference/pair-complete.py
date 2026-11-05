import json, os, pathlib
import job
D=pathlib.Path(__file__).resolve().parent
dry=os.environ.get('FILLER_DRYRUN') == '1'
result_path=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if dry else D/'RESULT.json'
r=json.loads(result_path.read_text())
assert r['status']=='COMPLETE_DIAGNOSTIC_ONLY' and len(r['pairs'])==2 and len(r['records'])==4 and r['cleanup'] is True
assert r['run_mode']==('dryrun' if dry else 'grant') and r['invocation_id']==os.environ['C6_INVOCATION_ID']
assert not dry or result_path.resolve() != (D/'RESULT.json').resolve()
root=pathlib.Path(r['run']).resolve()
assert root.is_relative_to((D/'runs').resolve()) and r['pins']==job.PINS
job.check_inputs()
for ci,case in enumerate(job.CASES):
    rows=[x for x in r['records'] if x['case']==case['name']]
    assert len(rows)==2 and {x['arm'] for x in rows}=={'generic','candidate'}
    byarm={x['arm']:x for x in rows}
    assert job.compare_pair(root,71,ci,byarm)==r['pairs'][ci]
    for arm,row in byarm.items():
        out=root/'seed-071'/case['name']/arm
        assert row['seed']==71 and row['binary_sha256']==job.PINS[arm]['binary_sha256']
        assert row['native_rc'] in (0,1) and (row['native_rc']==0)==row['property']['passed']
        assert row['stdout_sha256']==job.sha(out/'stdout.log') and row['stderr_sha256']==job.sha(out/'stderr.log')
        assert row['capture_sha256']=={n:job.sha(out/n) for n in job.CAPTURES}
        assert row['residency']['own_pid_kfd_reads']>=2 and row['residency']['own_pid_peak_vram_bytes']>0
        assert row['hip_maps'] and any(pathlib.Path(p).name.startswith('libggml-hip.so') and h==job.PINS[arm]['hip_library_sha256'] for p,h in row['hip_maps'].items())
        assert all(pathlib.Path(p).resolve().is_relative_to(pathlib.Path(job.PINS[arm]['library_dir']).resolve()) and job.sha(p)==h for p,h in row['hip_maps'].items())

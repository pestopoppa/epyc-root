import json,os,pathlib,sys
B=pathlib.Path(__file__).resolve().parent
try:
    r=json.loads(pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(B/'out'/'RESULT.json'))).read_text())
    mode='smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full'
    allowed={'SMOKE_REFUSAL_OBSERVED','SMOKE_ACQUISITION_QUALIFIED'} if mode=='smoke' else {'ACQUISITION_QUALIFIED'}
    good=r['id']=='kpf50-own-child-map-acquisition-20261105' and r['mode']==mode and r['status'] in allowed
    cases={x['case']:x['record'] for x in r['records']}
    good=good and 'honest' in cases and 'malformed-bound' in cases and cases['malformed-bound']['status']=='UNKNOWN'
    if r['status']!='SMOKE_REFUSAL_OBSERVED': good=good and cases['honest']['status']=='OBSERVED_FILE_RANGES' and cases['denied']['status']=='UNKNOWN'
    good=good and len(r['cleanup'])==(1 if r['status']=='SMOKE_REFUSAL_OBSERVED' else 2) and all(x['captured_process_absent'] for x in r['cleanup'])
except (OSError,ValueError,KeyError,TypeError): good=False
sys.exit(0 if good else 1)

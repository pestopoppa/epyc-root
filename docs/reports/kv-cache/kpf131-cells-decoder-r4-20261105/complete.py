import json,os,pathlib,sys,time
D=pathlib.Path(__file__).resolve().parent
try:
 assert not (D/'STOP').exists() and not pathlib.Path(os.getenv('FILLER_STOPFILE',str(D/'STOP'))).exists()
 if os.getenv('FILLER_DEADLINE'): assert time.time()<float(os.environ['FILLER_DEADLINE'])
 r=json.loads((D/'out/full/RESULT.json').read_text())
 assert r['row_id']=='kpf131-cells-abi-decoder-r4-20261105' and r['status']=='FIXTURE_PASS' and not r['smoke']
 assert [x['mode'] for x in r['records']]==['honest','pos','owner'] and all(x['cleanup_confirmed'] for x in r['records'])
except Exception: sys.exit(1)

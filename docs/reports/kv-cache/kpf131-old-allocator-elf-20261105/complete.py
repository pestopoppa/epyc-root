import json,os,pathlib,sys
b=pathlib.Path(__file__).resolve().parent
p=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(b/'out'/'RESULT.json')))
try:
 r=json.loads(p.read_text())
 mode='smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full'
 records=r.get('records',[])
 good=(r.get('row_id')=='kpf131-old-allocator-elf-20261105' and r.get('status')=='ALLOCATOR_ELF_CAPTURED' and r.get('mode')==mode and r.get('processed_files')==1 and len(records)==5 and all(x.get('rc')==0 for x in records) and r.get('lineage')==json.loads((b/'lineage.json').read_text()))
except (OSError,ValueError,TypeError):good=False
sys.exit(0 if good else 1)

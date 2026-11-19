"""Read one current range replay through isolated shared ingest and task context."""
import json
import shutil
from pathlib import Path
from adapters import nemo_range_join as adapter
from ingest_sources import ingest
from ledger import Ledger
from loop_beliefs import prepare

CONSUMER = adapter.CONSUMER
TASK = 'VB-NEMO-RANGE-JOIN-WIRE'

def run(result, output, as_of, smoke, checkpoint):
    output.mkdir()
    ledger = Ledger(output / 'ledger.jsonl')
    with ledger.write_lock():
        receipt = ingest(ledger, adapter.SOURCE_KIND, [result], as_of=as_of, only_new=True)
    (output / 'ingest.json').write_text(json.dumps(receipt, indent=2))
    chain_errors = ledger.verify()
    if receipt['rows_projected'] != 1 or receipt['frames_emitted'] != 3 or receipt['refused'] or receipt['declined'] or receipt['missing'] or chain_errors:
        raise ValueError('isolated ingest refused: ' + json.dumps({'receipt': receipt, 'chain_errors': chain_errors}, sort_keys=True))
    index=output/'index.yaml'; index.write_text('[]\n')
    config=output/'alarm-config.json'; config.write_text(json.dumps({'backend':'file','file':{'path':str(output/'alarm.jsonl')}}))
    counts={}
    for name,consumer,target in [
        ('exact',CONSUMER,{'scope':'task','task_id':TASK}),
        ('wrong-task',CONSUMER,{'scope':'task','task_id':'VB-OTHER'}),
        ('wrong-consumer','other.consumer',{'scope':'task','task_id':TASK}),
        ('model',CONSUMER,{'model_file':'Qwen3.8-27B-Q8_0.gguf','backend':'gpu'})]:
        checkpoint()
        answer=prepare(consumer,target,ledger=ledger.path,index_path=index,as_of=as_of,
          known_good=output/f'{name}.known-good.json',read_log=output/'reads.jsonl',
          alarm_config=config,alarm_state=output/'alarm-state.json',check_reader_checkout=False)
        (output/f'{name}.json').write_text(json.dumps(answer,indent=2))
        if answer['status']!='ready' or answer.get('read_log_error'): raise ValueError('reader refused')
        e=answer['evidence']; counts[name]={'recognized':e['tiers']['target'],'displayed':len(e['claims'])}
        expected=1 if name=='exact' else 0
        if counts[name]!={'recognized':expected,'displayed':expected}: raise ValueError('scope control '+name)
    controls={}
    if smoke:
        record=json.loads(result.read_text())
        shutil.copyfile(result.parent/'grant.copy', output/'grant.copy')
        for name in ('tamper','partial','missing-grant','source-drift'):
            checkpoint(); changed=json.loads(json.dumps(record))
            if name=='tamper': changed['result']['0-sdk']['joins'][0]['kernel_count']=99
            if name=='partial': changed['result'].pop('0-sdk')
            if name=='missing-grant': changed.pop('grant')
            if name=='source-drift': changed['source_pins'][next(iter(changed['source_pins']))]='0'*64
            path=output/f'{name}.json'; path.write_text(json.dumps(changed))
            scratch=Ledger(output/f'{name}.ledger.jsonl')
            with scratch.write_lock(): rejected=ingest(scratch,adapter.SOURCE_KIND,[path],as_of=as_of,only_new=True)
            if len(rejected['refused'])!=1 or rejected['rows_projected'] or rejected['frames_emitted']: raise ValueError('control admitted '+name)
            controls[name]='refused'
    return {'cases':counts,'controls':controls,'rows':1,'frames':3,'refusals':0}

"""Synthetic only: execute the real successor loop with fake engine executables."""
import hashlib, importlib.util, json, os, sys, tempfile, time, shutil
from pathlib import Path
import importlib
from unittest.mock import patch

def test_native_successor():
 D=Path(__file__).resolve().parent.parent; sys.path.insert(0,str(D))
 spec=importlib.util.spec_from_file_location('lex2_grid_fixture',D/'grid_job.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
 import complete_predicate as predicate
 def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
 with patch.dict(os.environ, {}, clear=False):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'run').mkdir();wav=p/'clip.wav';wav.write_bytes(b'synthetic clip');ann=p/'ann.json';ann.write_text('{}')
   manifest=p/'data.json';manifest.write_text(json.dumps({'records':[{'file_id':'fake','call_id':'fakecall','wav_path':str(wav),'wav_sha256':digest(wav),'annotations_path':str(ann),'annotations_sha256':digest(ann)}]}))
   (p/'GRID-PLAN.json').write_text('{}');(p/'SOURCE-SHA256SUMS').write_text('synthetic');(p/'DOMAIN-LEXICON-PROPOSAL.json').write_text(json.dumps({'phrases':{'en':['term']}}));(p/'CONVERSATION-CONTEXTS.json').write_text(json.dumps({'dev_manifest_sha256':digest(manifest),'calls':{'fakecall':['term']}}))
   engine=p/'fake-engine';engine.write_text('''#!/usr/bin/env python3
import sys,time,os,mmap
if not os.getenv('FAKE_SKIP_MAP'):
 ggml=open(os.environ['FAKE_GGML'],'rb'); mapped=mmap.mmap(ggml.fileno(),0,access=mmap.ACCESS_READ)
args=sys.argv
print('synthetic hypothesis',flush=True)
if 'transcribe' in args:
 print('LEX2 external tokenizer vocabulary verified (128 pieces)',file=sys.stderr,flush=True)
 a=float(args[args.index('--asr.decoder.boosting_tree_alpha')+1])
 if a: print('RNNT word boosting active phrases=1 effective_alpha=%.6f'%a,file=sys.stderr,flush=True)
time.sleep(.15)
''');engine.chmod(0o755)
   h='a'*64; modeldir=p/'models';modeldir.mkdir();model=modeldir/'nemotron-3.5-asr-streaming-0.6b.q8_0.gguf';model.write_bytes(b'fake model');tok=modeldir/'tokenizer.model';tok.write_bytes(b'fake tokenizer');ggml=p/'ggml';ggml.write_bytes(b'fake ggml');source=p/'source';source.write_bytes(b'fake source')
   common={k:h for k in ('dev_manifest_sha256','test_manifest_sha256','overlap_exclusions_sha256','request_sha256')};common.update(dataset_revision='fixture',split='dev')
   def ec(tokenizer):
    result={}
    for label,path in [('binary',engine),('model',model),('source',source),('ggml',ggml)]+([('tokenizer',tok)] if tokenizer else []):result[label+'_path']=str(path);result[label+'_sha256']=digest(path)
    result['ggml_version']='fixture';return result
   config={'common':common,'engines':{'nemo':ec(True),'whisper':ec(False)}};cfg=p/'config.json';cfg.write_text(json.dumps(config))
   g.D=p;g.DATA=manifest;g.N=engine;g.WH=engine;g.M=modeldir;g.W=model;os.environ['FAKE_GGML']=str(ggml)
   g.observation=lambda:{'epoch':time.time(),'grant_id':'synthetic-grant','grant_sha256':h,'co_tenant_generating':'unknown'}
   os.environ.update(LEX2_MODE='full',LEX2_OUT='run',LEX2_CAPTURE_CONFIG=str(cfg),FILLER_DEADLINE=str(int(time.time()+900)),FILLER_ID='synthetic-grant',FILLER_CPUS='124-125',LEX2_NEMO_MODEL_SHA=digest(model),LEX2_WHISPER_MODEL_SHA=digest(model),LEX2_SPM_SHA=digest(tok))
   assert g.main()==0
   assert predicate.complete(p/'run',1,15)
   terminal=json.loads((p/'run/TERMINAL.json').read_text());assert terminal['counts']=={'ok':15,'failure':0,'unknown':0},terminal
   assert len(list((p/'run').glob('*.belief-attempt.json')))==15
   assert len(list((p/'run').glob('*.belief-disposition.json')))==15
   bundler=importlib.import_module('bundle_lex2');bundler.bundle(p/'run',manifest,'nemo','local',1,p/'bundle.json')
   assert len(json.loads((p/'bundle.json').read_text())['items'])==1
   (p/'run/TERMINAL.json').unlink()
   assert g.main()==0 # full cache verification; no native child is redrawn
   # Start-only window: retain as unknown and never launch that cell again.
   start_only=p/'start-only';start_only.mkdir();first=next((p/'run').glob('*.belief-attempt.json'));shutil.copy(first,start_only/first.name)
   os.environ['LEX2_OUT']='start-only'
   assert g.main()==0
   assert predicate.complete(start_only,1,15)
   (start_only/'EXHAUSTED.json').unlink()
   assert g.main()==0 and predicate.complete(start_only,1,15) # recover marker only
   assert json.loads((start_only/'EXHAUSTED.json').read_text())['scientific_completion'] is False
   assert not (start_only/first.name.replace('.belief-attempt.json','.exposure.json')).exists()
   assert json.loads((start_only/'TERMINAL.json').read_text())['counts']['unknown']==1
   assert 'capture start without exposure' in next(start_only.glob('*.belief-unknown.json')).read_text()
   # Result-without-disposition window is preserved, never re-run.
   os.environ['LEX2_OUT']='run';(p/'run/TERMINAL.json').unlink()
   removed=next((p/'run').glob('*.belief-disposition.json'));ident=removed.name.replace('.belief-disposition.json','');removed.unlink();before=(p/'run'/f'{ident}.result.json').read_bytes()
   assert g.main()==0
   assert json.loads((p/'run/EXHAUSTED.json').read_text())['scientific_completion'] is False
   assert (p/'run'/f'{ident}.result.json').read_bytes()==before
   assert 'result without contemporaneous capture or disposition' in (p/'run'/f'{ident}.belief-unknown.json').read_text()
   # Native success without mapped-library proof persists its actual result and becomes unknown.
   os.environ.update(LEX2_OUT='nomap',FAKE_SKIP_MAP='1')
   assert g.main()==0
   q=p/'nomap';term=json.loads((q/'TERMINAL.json').read_text());assert term['counts']['unknown']==15 and term['partial'] is True
   assert all(json.loads(x.read_text())['status']=='ok' for x in q.glob('*.result.json'))
   assert all(json.loads(x.read_text())['status']=='unknown' for x in q.glob('*.belief-disposition.json'))
   assert predicate.complete(q,1,15)
   (q/'EXHAUSTED.json').write_text('{}')
   assert not predicate.complete(q,1,15)
   assert len(list(q.glob('*.result.json')))==15
   print('synthetic actual successor: 15-cell success/resume, start-only, missing disposition, and unmapped-success preserve receipts without redraw')

if __name__ == "__main__":
 test_native_successor()

import json,pathlib,subprocess,sys
D=pathlib.Path(__file__).resolve().parent; m=json.loads((D/'cohort.json').read_text()); o=D/'fixture'; (o/'cells').mkdir(parents=True,exist_ok=True)
for c in m['cells']:
 # English WER 0.1, de 0.4, it/fr 0.1; missing waveform represented as all deletions for one French cell.
 er=4 if c['lang']=='de' else 1
 if c['lang']=='fr' and c['id'].endswith('-tts-1234') and c['source_id'].endswith('1599'): er=10
 mode={'ref_words':10,'word_errors':er,'ref_chars':20,'char_errors':er,'hyp':'fixture'}
 (o/'cells'/f"{c['id']}.json").write_text(json.dumps({'id':c['id'],'modes':{'forced':mode,'auto':mode}}))
subprocess.run([sys.executable,str(D/'analyze.py'),str(o),str(D/'cohort.json')],check=True)
s=json.loads((o/'summary.json').read_text()); assert s['summary']['tts_rt|forced|de']['automated_m17_trigger'] is True; assert s['summary']['tts_rt|forced|de']['n']==60; assert s['summary']['repeated_seed|forced|de']['n']==10; assert 'automated_m17_trigger' not in s['summary']['stt|forced|de']; assert s['native_listener']=='NOT_ASSESSED'
print('fixture full 520 cells, mode-matched trigger and separate repeat PASS')

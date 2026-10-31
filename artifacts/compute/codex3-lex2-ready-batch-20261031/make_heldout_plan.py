#!/usr/bin/env python3
"""Make a future held-out plan only from this packet's actual frozen dev selection."""
import hashlib,json,os,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
selection=D/'DEV-SELECTION.json';terminal=D/'run/TERMINAL.json';spec=D/'SCORER-PREDECLARED.json';grid=D/'GRID-PLAN.json'
if not selection.is_file():raise SystemExit('HELD: actual dev selection absent')
x=json.loads(selection.read_text());d=json.loads(spec.read_text());
if x.get('schema')!='cs8.lex2.dev-selection.v1' or x.get('test_opened') is not False or x.get('quality_verdict') is not None:raise SystemExit('invalid dev selection')
if x['grid_plan_sha256']!=sha(grid) or x['scorer_predeclared_sha256']!=sha(spec) or x['raw_terminal_sha256']!=sha(terminal):raise SystemExit('selection evidence drift')
for p,v in d['source_sha256'].items():
 if sha(D/p)!=v:raise SystemExit('scorer source drift: '+p)
if x.get('nonlist_noise_floor_state')!='known_lexical' or x.get('nonlist_noise_floor') is None:raise SystemExit('HELD: LEX1 lexical non-list WER noise floor is unknown')
chosen=x['selection'];
if chosen['engine']!='nemo' or chosen['scope'] not in ('global','local') or chosen['alpha'] not in (0,.5,1,2,3,5):raise SystemExit('selection outside predeclared grid')
assets={'contextual_test_manifest':('/mnt/raid0/llm/data/contextual-earnings22-59d7f947/test-native/MANIFEST-V2.json','bf5a32fb1a74d6cac4950f8973abc2583c08ad4e71a1169399aa8eb443188fd7'),'fleurs_test_source':('/mnt/raid0/llm/data/stt-cs8-public-20261030/stt5-baseline-test-manifest.json','242be009933eaf7e6b2e70e56b0f55f76a3d22b815eb4ce7fcf95a1467b72362'),'aa_comparison_view':(str(D/'AA-COMPARISON-VIEW-PROPOSAL.json'),'61f9e74173ee5ae9ec25a59c31c55e1a28ddf51fe78f030db032f400e1e6064c')}
for name,(path,expected) in assets.items():
 if sha(path)!=expected:raise SystemExit(name+' drift')
ctx=json.loads(pathlib.Path(assets['contextual_test_manifest'][0]).read_text());allrows=ctx['records'];held=[r for r in allrows if r['eligibility']=='heldout'];excluded=[r for r in allrows if r['eligibility']=='excluded'];
if len(allrows)!=772 or len(held)!=755 or len(excluded)!=17 or sum(r.get('aa_overlap_status')=='unknown' for r in held)!=19:raise SystemExit('test membership mismatch')
plan={'schema':'cs8.lex2.heldout-plan.v1','created_before_test':True,'selection_sha256':sha(selection),'dev_plan_sha256':sha(grid),'scorer_predeclared_sha256':sha(spec),'raw_terminal_sha256':sha(terminal),'selection':chosen,'nonlist_noise_floor':x['nonlist_noise_floor'],'metric_label':'LEX1 lexical reference agreement, not P-STT-1 v1 WER or speech-release claim','assets':{k:{'path':p,'sha256':h} for k,(p,h) in assets.items()},'original_contextual_n':772,'excluded_dev_call_n':17,'heldout_contextual_n':755,'aa_call_flagged_unknown_n':19,'arms':['selected Nemo','alpha-zero Nemo baseline','frozen Whisper no prompt','frozen Whisper selected-scope prompt'],'fleurs':'all pinned test en/it/de/fr; selected context and alpha-zero baseline, per-source list semantics predeclared in final launcher','unknown_policy':'all original attempts retained, no redraw, unknown/discordant overlap never counted as clean','decision_rule':'CS-8.LEX2: paired test keyword F gain 95% interval above zero, lexicon-free insertions <= 1/hour, term-masked WER rise <= frozen dev noise floor; undefined evidence cannot pass','scorer_semantics_sha256':sha(spec),'test_inference_started':False,'test_scoring_started':False,'ready':False,'remaining':'materialize exact selected and baseline command matrix, write-side capture, final launcher and same-launcher real/STOP proof before any READY'}
out=D/'HELDOUT-PLAN.json';raw=(json.dumps(plan,sort_keys=True,indent=2)+'\n').encode();fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
fd=os.open(D,os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
print('heldout plan written, NOT READY',sha(out))

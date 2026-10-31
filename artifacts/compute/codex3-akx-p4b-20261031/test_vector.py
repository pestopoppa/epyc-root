import ast
import pathlib
from collections.abc import Mapping
root=pathlib.Path(__file__).parent/'private'
def get_function(path,name):
    tree=ast.parse(path.read_text())
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    m=ast.Module(body=[f],type_ignores=[])
    ns={'Mapping':Mapping}
    exec(compile(m,str(path),'exec'),ns)
    return ns[name]
champ=get_function(root/'dashboard/loop_status.py','_champion_workload_vector')
op=get_function(root/'dashboard/server.py','_operator_workload_vector')
assert champ(None)==[]
x=champ({'metrics':{'tg':{'surface':'decode','effect_fraction':.1},'pp':{'surface':'prefill','effect_fraction':-.02}},'protocols':{'tg':{'model':'M','argv':['x']}},'evidence':'e'})
assert len(x)==2 and x[0]['recipe']=={'model':'M','argv':['x']} and x[1]['recipe'] is None
assert x[0]['workload']=='decode' and x[1]['workload']=='prefill'
x=champ({'effect_fraction':0.0,'surface':'tg128'})
assert len(x)==1 and x[0]['cell']=='legacy_primary' and x[0]['recipe'] is None and x[0]['effect_fraction']==0
x=op([{'gate':'anchor','artifact':'a','artifact_sha256':'h','surfaces':[{'surface':'pp','delta_pct':1}]},{'gate':'spec','points':[{'in_flight':2,'delta_pct':3}]}])
assert len(x)==2 and x[0]['workload']=='pp' and x[0]['recipe'] is None and x[0]['artifact_sha256']=='h'
assert x[1]['workload'] is None and x[1]['recipe'] is None and x[1]['in_flight']==2
assert op([None,{'points':[None]}])==[]
s=(root/'research/production.py').read_text()
assert '"protocols": {m: dict(protocols[m]) for m in order}' in s
print('vector fixture assertions passed')
import json,re,subprocess,tempfile
html=(root/'dashboard/static/loop.html').read_text()
js='\n'.join(re.findall(r'<script[^>]*>(.*?)</script>',html,re.S))
payload={'champion_vs_production':{'workload_vector':[{'workload':'<img onerror=x>','recipe':None,'effect_fraction':0.1,'metric':'tok_s'}],'freshness':{'state':'stale'},'baseline_check':'superseded','capabilities':{}},'operator_gates':{'available':True,'freshness':{'state':'relevant','age_s':2},'headline':{},'gates':[],'workload_vector':[{'gate':'spec','in_flight':2,'workload':None,'recipe':None,'delta_pct':12.3}]}}
with tempfile.TemporaryDirectory() as d:
    d=pathlib.Path(d); (d/'page.js').write_text(js);(d/'payload.json').write_text(json.dumps(payload))
    r=subprocess.run(['node',str(pathlib.Path(__file__).parent/'render_harness.js'),str(d/'page.js'),str(d/'payload.json'),'renderChampion','renderOperatorGate'],capture_output=True,text=True,check=True,timeout=20)
    out=json.loads(r.stdout)
    assert out['threw']==[]
    c=out['by_id']['champion-capabilities']; o=out['by_id']['opgate']
    assert '&lt;img onerror=x&gt;' in c and '<img' not in c and 'recipe: UNKNOWN' in c
    assert 'freshness: stale' in c and 'baseline: superseded' in c
    assert 'in-flight 2' in o and 'workload: UNKNOWN' in o and 'recipe: UNKNOWN' in o
    assert out['class_by_id']['opgate-badge']=='badge relevant'
print('DOM and escape assertions passed')
# Exercise the actual producer function with a recording in-memory writer.
import types
source=(root/'research/production.py').read_text(); tree=ast.parse(source)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_write_serving_receipt')
mod=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),fn],type_ignores=[])
records=[]
class Writer:
    @staticmethod
    def write_json(store,name,body,**kwargs):
        records.append((name,body)); return pathlib.Path('/')/name
ns={'status':Writer,'PROTOCOL_KIND_SERVING_PROBE':'serving','SCHEMA':'s','STALE_AFTER_S':1,'MECHANISM_ID':'m','headline_admissibility':types.SimpleNamespace(contract=lambda:{}),'_serving_headline':lambda legs,order:'headline','_leg_headline_fragment':lambda m,leg:m}
exec(compile(ast.fix_missing_locations(mod),'production.py','exec'),ns)
leg={'surface':'decode','baseline_record':'p','baseline_record_sha256':'h','baseline_measured_at':'t','effect_fraction':.1,'baseline_launches':1,'champion_launches':1,'confidence_interval':[],'verdict':'x'}
protocols={'tg':{'model':'M','server_argv':['tg']},'pp':{'model':'M','server_argv':['pp']}}
ns['_write_serving_receipt'](pathlib.Path('/tmp'),legs={'tg':leg,'pp':dict(leg,surface='prefill')},protocols=protocols,paired=True,primary='tg',champion_commit='a'*40,champion_build=None,frozen_commit='b'*40,frozen_label='frozen',production_build=None,carryover={},source=None,bundle_name='bundle',now=lambda:'today')
bundle=records[1][1]
assert bundle['protocols']==protocols and bundle['metrics']['pp']['surface']=='prefill'
assert bundle['protocol']==protocols['tg'] and bundle['effect_fraction']==.1
print('actual producer per-leg binding assertions passed')

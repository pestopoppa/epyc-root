"""Offline, byte-preserving comparison of V5 and V6 recipe-link acceptance."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
DOC=Path('docs/research/qwen3.6-35b-a3b-q8-gpu-mtp-cache-sizing.md')
RECIPE=Path('artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json')
UNIT=BASE.parent/'ws58-a3b-frozen-revalidation-20261126/quality-runs/cache-safe-01/units/gpu-PFXC-A3-on-coding-guidance-2'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')

def main():
    main_lane=BASE/'main-comparison/runs/PFXC-A3/direct-1/lane'
    actual_lane=UNIT/'independent/work'
    originals=[main_lane/DOC,main_lane/RECIPE,actual_lane/DOC,UNIT/'RESULT.json',BASE/'pfxc-oracle-v5/paid-on-assessment/REPORT.json']
    witnesses={str(p):sha(p) for p in originals}
    raw=(actual_lane/DOC).read_text();main_body=(main_lane/DOC).read_text();recipe=(main_lane/RECIPE).read_bytes()
    assert hashlib.sha256(recipe).hexdigest()=='d3a3cf4f935a00dd9b020ea409f52a26caedfe3cf2325f636ae7c4edd5cf302b'
    label='artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json'
    bad='['+label+'](../'+label+')';good='['+label+'](../../'+label+')'
    assert raw.count(bad)==1
    fixed=raw.replace(bad,good)
    variants={
        'actual-main-direct':(main_body,0,0),
        'actual-paid-on2-broken-link':(raw,0,1),
        'corrected-link-fixture':(fixed,0,0),
        'reference-style':(raw.replace(bad,'[canonical recipe][serving recipe]')+'\n[serving recipe]: ../../'+label+' "Pinned canonical recipe"\n',0,0),
        'collapsed-reference':(raw.replace(bad,'[canonical recipe][]')+'\n[canonical recipe]: ../../'+label+'\n',0,0),
        'angle-target-title':(raw.replace(bad,'[canonical recipe](<../../'+label+'> "Pinned recipe")'),0,0),
        'html-anchor':(raw.replace(bad,'<a href="../../'+label+'">canonical recipe</a>'),0,0),
        'valid-two-column-colon':(re.sub(r'(?m)(^\|\s*1\s*\|\s*)558(\s*\|)',r'\g<1>:558\2',fixed,count=1),0,0),
        'external-wrong':(raw.replace(bad,'[canonical recipe](https://example.invalid/'+label+')'),0,1),
        'case-wrong':(raw.replace(bad,'[canonical recipe](../../Artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json)'),0,1),
        'missing-hyperlink':(raw.replace(bad,'`'+label+'`'),0,1),
        'unused-reference-only':(raw.replace(bad,'`'+label+'`')+'\n[unused recipe]: ../../'+label+'\n',0,1),
        'code-example-only':(raw.replace(bad,'`'+label+'`')+'\n```markdown\n'+good+'\n```\n',0,1),
        'image-only':(raw.replace(bad,'!'+good),0,1),
        'wrong-local-identical-bytes':(raw.replace(bad,'[canonical recipe](../../other/'+RECIPE.name+')'),0,1),
        'canonical-recipe-bytes-changed':(fixed,0,1),
        'wrong-event-regression':(fixed.replace('329.659','329.658',1),1,1),
    }
    old=ast.parse((HERE/'previous-v5.py').read_text());new=ast.parse((HERE/'oracle.py').read_text())
    old_functions={n.name:n for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    new_functions={n.name:n for n in new.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    for name,node in old_functions.items():
        if name!='verify':assert ast.dump(node)==ast.dump(new_functions[name]),name
    old_verify=old_functions['verify'];new_verify=new_functions['verify']
    assert [ast.dump(n) for n in old_verify.body]==[ast.dump(n) for n in new_verify.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='verify_recipe_hyperlink')]
    results=[]
    for name,(body,old_rc,new_rc) in variants.items():
        dest=HERE/'controls'/name;lane=dest/'lane';(lane/DOC).parent.mkdir(parents=True,exist_ok=True);(lane/RECIPE).parent.mkdir(parents=True,exist_ok=True)
        (lane/DOC).write_text(body);(lane/RECIPE).write_bytes(recipe if name!='canonical-recipe-bytes-changed' else recipe+b' ')
        if name=='wrong-local-identical-bytes':
            p=lane/'other'/RECIPE.name;p.parent.mkdir();p.write_bytes(recipe)
        rec={'id':name,'candidate_sha256':sha(lane/DOC),'receipts':{}}
        for version,checker,expected in [('v5',HERE/'previous-v5.py',old_rc),('v6',HERE/'oracle.py',new_rc)]:
            q=subprocess.run([sys.executable,'-IB',str(checker),str(lane)],capture_output=True,timeout=30)
            (dest/(version+'.stdout.log')).write_bytes(q.stdout);(dest/(version+'.stderr.log')).write_bytes(q.stderr)
            rec['receipts'][version]={'rc':q.returncode,'expected_rc':expected,'checker_sha256':sha(checker),'stdout_sha256':hashlib.sha256(q.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(q.stderr).hexdigest(),'diagnostic':q.stderr.decode().strip()}
            assert q.returncode==expected,(name,version,q.returncode,q.stderr.decode())
        write(dest/'RESULT.json',rec);results.append(rec)
    assert all(sha(Path(p))==s for p,s in witnesses.items())
    result={'version':'pfxc.recipe-hyperlink.v6','checks':results,'all_expected':True,'v5_functions_and_checks_retained_ast':True,'raw_scores_and_candidates_unchanged':True,'original_source_sha256':witnesses,'oracle_sha256':sha(HERE/'oracle.py'),'previous_v5_sha256':sha(HERE/'previous-v5.py'),'model_calls':0,'semantic_review_performed':False}
    write(HERE/'REPLAY.json',result)
    case=BASE/'main-comparison/cases/PFXC-A3/case.json';brief=json.loads(case.read_text())['worker_task']['approach']
    write(HERE/'acceptance-migration.json',{'case':'PFXC-A3','version':'pfxc.recipe-hyperlink.v6','oracle_sha256':sha(HERE/'oracle.py'),'previous_oracle_sha256':sha(HERE/'previous-v5.py'),'control_receipt':'REPLAY.json','control_receipt_sha256':sha(HERE/'REPLAY.json'),'original_requirement':brief.split('\n')[0],'original_requirement_source_sha256':sha(case),'change':'Retain every V5 check and require an actual CommonMark or HTML hyperlink resolving from the document to the supplied byte-pinned canonical recipe. Words, unused definitions, images and code examples are not hyperlinks. No new task requirement.','raw_scores_unchanged':True,'extra_native_attempts':0,'extra_paid_model_calls':0})
    print(len(results),'V5/V6 replay controls passed; raw inputs unchanged')

if __name__=='__main__':main()

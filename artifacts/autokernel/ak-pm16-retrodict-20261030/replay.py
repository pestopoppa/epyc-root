#!/usr/bin/env python3
"""Isolated pinned AutoKernel classifier replay; no torch or external agent imports."""
import ast, hashlib, json, re
from pathlib import Path
R=Path(__file__).parent
source=R/'profile.py'
receipt=Path('/mnt/raid0/llm/autokernel/probes/inf36-g15-profile-v9-20260811-r4/receipt.json')
extract=R/'extract.py'
tree_response=R/'github-tree-response.json'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='c79ea394e49e0e52de500ad25a4761c3fd375fee95f5a2d3b03c9268fd67ad36'
assert hashlib.sha256(receipt.read_bytes()).hexdigest()=='d7a0c8c257c2a59435b95c39b988485a8283d709d83ef7397b3c67ee7ec8cca9'
assert hashlib.sha256(extract.read_bytes()).hexdigest()=='e911972f9879309cbf68bd3e11521d783697c61fd7bc1d9032e371e553f216e7'
assert hashlib.sha256(tree_response.read_bytes()).hexdigest()=='2f7f21a22cb6c1b9ed972d091b76add0cb3ba742e92e05e4f1cac0e657d7966c'
tree_listing=json.loads(tree_response.read_bytes())
assert tree_listing['sha']=='78435821cc3d5756ba6ee1785c397f6d8fa8c90d' and not tree_listing.get('truncated')
supported_types=sorted(Path(x['path']).stem for x in tree_listing['tree'] if x['path'].startswith('kernels/') and x['path'].count('/')==1 and x['path'].endswith('.py') and x['path']!='kernels/__init__.py')
saved_types=json.loads((R/'supported-types.json').read_text())
assert saved_types['source_tree_sha']==tree_listing['sha'] and saved_types['types']==supported_types
tree=ast.parse(source.read_text())
rules=next(n for n in tree.body if isinstance(n,ast.AnnAssign) and getattr(n.target,'id',None)=='_KERNEL_CLASSIFICATION')
classification=ast.literal_eval(rules.value)
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('classify_kernel','is_autokernel_supported','_priority_label')]
assert len(functions)==3
namespace={'re':re,'_KERNEL_CLASSIFICATION':classification,'_SUPPORTED_OP_TYPES':set(supported_types)}
module=ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+functions,type_ignores=[]))
exec(compile(module,str(source),'exec'),namespace)
extract_tree=ast.parse(extract.read_text())
extract_function=next(n for n in extract_tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_supported_kernels')
extract_module=ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),extract_function],type_ignores=[]))
exec(compile(extract_module,str(extract),'exec'),namespace)
d=json.loads(receipt.read_text()); p=next(x for x in d['profiles'] if x['bench']['pl']==128); a=p['attribution']; rows=[]
for rank,k in enumerate(sorted(a['kernel_table'],key=lambda k:k['device_duration_ns_total'],reverse=True),1):
 op=namespace['classify_kernel'](k['kernel']); supported=namespace['is_autokernel_supported'](op); share=k['summed_kernel_time_share']
 rows.append({'rank':rank,'name':k['kernel'],'share_pct':round(share*100,6),'op_type':op,'supported':supported,'priority':namespace['_priority_label'](share*100)})
by_type={}
for x in rows:by_type[x['op_type']]=by_type.get(x['op_type'],0)+x['share_pct']
supported=namespace['get_supported_kernels']({'top_kernels':[{'rank':x['rank'],'op_type':x['op_type'],'autokernel_supported':x['supported'],'pct_total':x['share_pct']} for x in rows]})
family={x['family']:x['summed_kernel_time_share']*100 for x in a['family_table']}
result={'source_commit':'78435821cc3d5756ba6ee1785c397f6d8fa8c90d','source_profile_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_extract_sha256':hashlib.sha256(extract.read_bytes()).hexdigest(),'g15_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'actual_b128_family_pct':family,'kernel_count':len(rows),'actual_classifier_type_pct':by_type,'supported_total_pct':sum(x['share_pct'] for x in rows if x['supported']),'top_actual_kernel_rows':rows[:20],'top_supported_for_extraction':supported[:5],'literal_name_probes':{name:{'classified':namespace['classify_kernel'](name),'supported':namespace['is_autokernel_supported'](namespace['classify_kernel'](name))} for name in ['gather','scatter','recurrent','rms_norm_f32','silu']},'family_input_interface':'ABSENT: build_report expects List[KernelRecord] individual names+GPU times, not a family-share map; this replay uses actual receipt kernel_table to avoid invented per-kernel records.'}
out=R/'REPLAY-RESULT.json';out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'family':family,'by_type':by_type,'supported_total_pct':result['supported_total_pct'],'top5':[{k:v for k,v in x.items() if k!='name'} for x in rows[:5]],'extracted_top5':supported[:5],'literal_name_probes':result['literal_name_probes']},indent=2))

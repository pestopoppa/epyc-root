#!/usr/bin/env python3
"""Deterministic, read-only-source KPF17.4d(a) offline re-judgment."""
import hashlib, json, re
from pathlib import Path

OUT = Path('/mnt/raid0/llm/tmp/codex3-kpf174d-offline-a-20261030')
SRC = {
 'root_handoff': '/mnt/raid0/llm/tmp/codex3-kpf174d-offline-a-20261030/source-context/kv-prefix-fork-and-paged-attention.md',
 'root_progress_20261026': '/mnt/raid0/llm/tmp/codex3-kpf174d-offline-a-20261030/source-context/2026-10-26-workspace-58.md',
 'root_source_context_record': '/mnt/raid0/llm/tmp/codex3-kpf174d-offline-a-20261030/source-context/ROOT-SOURCE-CONTEXT.json',
 'prior_draft_only': '/mnt/raid0/llm/tmp/refactor-01a16fc3/kpf174b-offline-rejudge/CUSTODY-DRAFT.md',
 'predecl_174b_and_131b_v4': '/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf-gpu-followups/PREDECLARATION.md',
 'rules_131b_v4': '/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf-gpu-followups/out/kpf131b/rules.json',
 'original_174b_verdict': '/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf-gpu-followups/VERDICT.kpf174b-specoff.json',
 'original_174b_cell': '/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf-gpu-followups/out/kpf174b-specoff/cells/honest_specoff/g2-c2148.json',
 'original_174b_rows': '/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf-gpu-followups/out/kpf174b-specoff/rows/honest_specoff.jsonl',
 'original_174b_run_record': '/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf-gpu-followups/out/kpf174b-specoff/records/kpf174-honest_specoff-20261023T182942Z.json',
 'original_174b_rules': '/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf-gpu-followups/out/kpf174b-specoff/rules.json',
 '174c_predeclaration': '/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf17-4c-bisect/PREDECLARATION.md',
 '174c_verdict': '/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf17-4c-bisect/VERDICT.json',
 '174c_rules': '/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf17-4c-bisect/out/kpf174c/rules.json',
 '174c_run_record': '/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf17-4c-bisect/out/kpf174c/records/kpf174c-bisect_specoff-20261024T110836Z.json',
 '174c_cell_g2_c2148': '/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf17-4c-bisect/out/kpf174c/cells/bisect_specoff/g2-c2148.json',
 '174c_rows': '/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf17-4c-bisect/out/kpf174c/rows/bisect_specoff.jsonl',
}
def j(name): return json.loads(Path(SRC[name]).read_text())
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def exact(a,b): return a['tokens']==b['tokens'] and a['top2']==b['top2']
def diffidx(a,b): return next((i for i,(x,y) in enumerate(zip(a['tokens'],b['tokens'])) if x!=y),None)

handoff=Path(SRC['root_handoff']).read_text()
assert 'KPF-17.4d remaining re-judge scope' in handoff
assert 'do NOT file a GPU run' in handoff and 'OFFLINE re-judgment plus custody filing' in handoff
assert 'five spec-off cells on `a1f0c8cf9` still need their own image-specific layout-matched controls' in handoff
prior=Path(SRC['prior_draft_only']).read_text()
assert 'proposed custody record, not a new predeclared verdict' in prior
assert 'must not be presented as a new predeclaration' in prior

old=j('original_174b_verdict'); oldcell=j('original_174b_cell'); oldrec=j('original_174b_run_record')
oldrow=old['cells']['honest_specoff:g2-c2148']
assert oldrow['verdict']=='FAIL' and oldrow['first_divergence']==56
assert oldrow['runs'][0]['first_divergence_gap']==0.09389
assert oldrow['runs'][0]['first_divergence_near_tie'] is False
assert oldrec['binary_sha256']=='18afca1656b2d93e65312e0a8bcc3bc9f62ac0405fcb8d629c4634f16e48f078'
v4=j('rules_131b_v4')
assert re.search(r'0\.031567',json.dumps(v4,sort_keys=True))
band=0.031567
v4decl=Path(SRC['predecl_174b_and_131b_v4']).read_text()
assert 'GPU near-tie band is 0.031567, fixed' in v4decl and 'Speculation off:' in v4decl and 'Tokens only' in v4decl

cell=j('174c_cell_g2_c2148'); assert cell['cell']=='g2-c2148' and cell['device']=='gpu'
r=cell['runs']; X,M,F,C0=r['Xc'],r['Cmask'],r['Cf'],r['C0']
assert (len(X),len(M),len(F),len(C0))==(2,3,3,3)
for group in (X,M,F,C0):
 assert all(len(x['tokens'])==64 and len(x['top2'])==64 for x in group)
matched=[exact(x,m) for x in X for m in M]
reproduced=[exact(x,f) for x in X for f in F]
layout=[exact(m,c) for m in M for c in C0]
assert len(matched)==6 and all(matched)
assert not all(reproduced) and not all(layout)
idx=diffidx(X[0],F[0]); assert idx==56
xmargin=X[0]['top2'][idx][0][1]-X[0]['top2'][idx][1][1]
assert oldrow['runs'][0]['first_divergence_gap']>band and xmargin>band
pre4c=Path(SRC['174c_predeclaration']).read_text()
assert 'Xc~Cmask | matched' in pre4c and 'Xc~Cf | reproduce' in pre4c and 'control_layout_numerics' in pre4c
v4c=j('174c_verdict')
assert v4c['decisions']['locus']=='none_reproduced'
assert v4c['decisions']['explains_174b']=='control_layout_numerics'
assert 'g2-c2148' in v4c['decisions']['matched']['Xc~Cmask']['identical']
assert 'g2-c2148' in v4c['decisions']['reproduces_174b']['differs']
newrec=j('174c_run_record')
assert oldrec['binary_sha256']==newrec['binary_sha256']
assert oldcell['prompt_sha256']==cell['prompt_sha256']

result={
 'schema':'epyc.kpf17_4d.offline_rejudgment/v1','task':'KPF-17.4d(a)',
 'scope':'KPF-17.4b spec-off g2-c2148 only','result':'CONTROL_LAYOUT_NUMERICS',
 'target_restore_defect_supported_for_scope':False,
 'original_verdict_preserved':{'verdict':'FAIL','path':SRC['original_174b_verdict'],'meaning':'historical v2 result remains unchanged; this scoped re-judgment supplies its layout-matched interpretation'},
 'basis':{
  'predeclared_174c_mechanical_outcome':'none_reproduced / control_layout_numerics',
  'cell':'g2-c2148',
  'matched_Xc_vs_Cmask':{'pairs':6,'identical_all_64_tokens_and_top2':True},
  'original_comparison_reproduced_Xc_vs_Cf':{'pairs':6,'identical_all':False,'first_token_divergence_index':idx},
  'layout_control_Cmask_vs_C0':{'all_pairs_identical':False},
  'same_binary_and_image':{'binary_sha256':oldrec['binary_sha256'],'historical_image':'gpu-20261023-82c16126f-kpf191'},
  'near_tie_context':{'fixed_gpu_band':band,'source':'KPF-13.1b predeclared v4; label only, not a spec-off verdict clause','historical_17_4b_first_divergence_gap':0.09389,'historical_gap_within_band':False,'Xc_top2_margin_at_Xc_vs_Cf_divergence':xmargin,'Xc_margin_within_band':False}},
 'decision_rule_provenance':'No new rule. Applies KPF-17.4c PREDECLARATION.md exact matched Xc~Cmask comparison and existing explains_174b mapping; reads fixed 0.031567 context from KPF-13.1b rules v4. The v4 predeclaration says spec-off is tokens-only and the near-tie label is not a verdict. Original KPF-17.4b FAIL remains intact.',
 'non_scope':'No KPF-13.1b cells, no KPF-17.4b g1-c2148, no KPF-17.4 parent/drafter-on clause, no new execution, no GPU run, no ledger write.'}
(OUT/'verdict.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
files={name:sha(path) for name,path in SRC.items()}
custody={
 'schema':'epyc.kpf17_4d.offline_custody/v1','task':'KPF-17.4d(a)','prepared_utc':'2026-10-30',
 'method':'read-only source comparison; deterministic model-free derivation; no inference/GPU execution',
 'scope':'KPF-17.4b spec-off g2-c2148 only','filing_status':'prepared for owning ROOT session to apply; no ROOT handoff/index/progress edits made',
 'already_filed_check':{'fully_qualified_A_filing_found':False,'evidence':'immutable ROOT handoff/progress snapshots at commit 7edab852fb2e2718d540763f962c408d8a8fc1d7 and scratch context contain the 2026-10-26 checkpoint and a prior file explicitly marked draft; no qualifying A verdict/custody was found'},
 'verdict_artifact':'verdict.json','source_artifacts_sha256':files,
 'derived_integrity':{
  'original_174b_cell_prompt_sha256':oldcell['prompt_sha256'],'174c_cell_prompt_sha256':cell['prompt_sha256'],
  'original_and_174c_binary_sha256_equal':True,'original_and_174c_binary_sha256':oldrec['binary_sha256'],
  'original_and_174c_prompt_sha256_equal':True,'original_and_174c_prompt_sha256':oldcell['prompt_sha256'],
  'original_and_174c_recorded_rules_sha256':{'174b':old['rules_sha256'],'174c':v4c['rules_sha256']},
  'matched_comparisons':{'Xc_runs':2,'Cmask_runs':3,'exact_pair_count':sum(matched)},
  'reproduced_comparisons':{'Xc_runs':2,'Cf_runs':3,'differing_pair_count':sum(not x for x in reproduced)},
  'layout_comparisons':{'Cmask_runs':3,'C0_runs':3,'differing_pair_count':sum(not x for x in layout)}},
 'limitations':['same-load repeats are not independent loads','re-judgment is scoped to this exact image and g2-c2148 cell','KPF-13.1b five spec-off cells on image a1f0c8cf9 remain separate and untouched'],
 'proposed_handoff_text':'handoff-child-proposed.md','proposed_progress_text':'progress-proposed.md'}
(OUT/'custody.json').write_text(json.dumps(custody,indent=2,sort_keys=True)+'\n')
child=('      - [x] **KPF-17.4d(a) — KPF-17.4b spec-off g2-c2148 layout-matched offline re-judgment.** The stored KPF-17.4c g2-c2148 native cell on the same image `gpu-20261023-82c16126f-kpf191` (binary SHA-256 `18afca16…`) has Xc~Cmask exact across all 64 token IDs and top-2 logprobs (2 Xc × 3 Cmask comparisons); Xc~Cf reproduces the original token divergence at index 56, and Cmask~C0 shows layout sensitivity. Applying the existing KPF-17.4c predeclared `explains_174b` mapping yields `control_layout_numerics`; the original 17.4b FAIL remains recorded. The fixed KPF-13.1b v4 band is 0.031567; the original first-divergence gap 0.09389 and matched-run Xc top-2 margin 0.446976 are outside that band, and the v4 near-tie label is not a spec-off verdict clause. No inference or GPU run. Evidence/custody: `/mnt/raid0/llm/tmp/codex3-kpf174d-offline-a-20261030/`. ✅ 2026-10-30 [belief: cc]\n')
(OUT/'handoff-child-proposed.md').write_text(child)
progress=('## KPF-17.4d(a) — offline re-judgment\n\nOn 2026-10-30, the stored KPF-17.4c g2-c2148 cell supplied an exact same-layout reference for KPF-17.4b spec-off: Xc~Cmask matches over 64 tokens and top-2 logprobs, while Xc~Cf reproduces the original token divergence at index 56 and Cmask~C0 shows layout sensitivity. Under KPF-17.4c\'s predeclared mapping, the scoped interpretation is `control_layout_numerics`; the original KPF-17.4b FAIL artifact remains unchanged. The 0.031567 fixed v4 near-tie band is context only here (original gap 0.09389; matched-run Xc top-2 margin 0.446976), since v4 makes spec-off tokens-only and the near-tie label is not a verdict clause. No inference/GPU run. Evidence: `/mnt/raid0/llm/tmp/codex3-kpf174d-offline-a-20261030/`. [belief: cc]\n')
(OUT/'progress-proposed.md').write_text(progress)
custody['prepared_artifacts_sha256']={name:sha(OUT/name) for name in ('verdict.json','handoff-child-proposed.md','progress-proposed.md','derive.py')}
(OUT/'custody.json').write_text(json.dumps(custody,indent=2,sort_keys=True)+'\n')
with (OUT/'INPUTS.sha256').open('w') as f:
 for name,path in SRC.items(): f.write(f'{files[name]}  {path}\n')
print(json.dumps({'status':'prepared','result':result['result'],'source_count':len(SRC),'output':str(OUT)},sort_keys=True))

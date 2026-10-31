#!/usr/bin/env python3
import hashlib,json,pathlib
D=pathlib.Path(__file__).resolve().parent;wiki=pathlib.Path('/mnt/raid0/llm/data/wikitext2_test.txt');files=[pathlib.Path('/mnt/raid0/llm/epyc-inference-research/scripts/speech/stt_bakeoff')/x for x in ('align.py','lexicon.py','stt_norm.py','scorer.py')]+[pathlib.Path('/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/occ1/prompts.py')]
sha=lambda b:hashlib.sha256(b).hexdigest();paras=[x.strip() for x in wiki.read_text().split('\n\n') if len(x.strip())>=800];assert len(paras)>=10
prompts=[]
for i,f in enumerate(files):
 text=f.read_text();snippet=text[:5000];msg='Review this real Python excerpt. Propose one small maintainability edit, preserving behavior, and give the revised code where applicable.\n\n'+snippet;prompts.append({'id':f'code-{i}','class':'code','source':str(f),'source_sha256':sha(f.read_bytes()),'excerpt_start':0,'excerpt_chars':len(snippet),'prompt':msg,'prompt_sha256':sha(msg.encode())})
for i in range(5):
 for kind,j in (('rag',i),('prose',i+5)):
  excerpt=paras[j][:5000];lead='Using only the following retrieved passage, explain its main points and cite short phrases from it.\n\n' if kind=='rag' else 'Continue this real prose passage in a coherent, neutral style without copying it verbatim.\n\n';msg=lead+excerpt;prompts.append({'id':f'{kind}-{i}','class':kind,'source':str(wiki),'source_sha256':sha(wiki.read_bytes()),'paragraph_index':j,'excerpt_chars':len(excerpt),'prompt':msg,'prompt_sha256':sha(msg.encode())})
assert len(prompts)==15 and len({p['prompt_sha256'] for p in prompts})==15
out=D/'PROMPTS.json';out.write_text(json.dumps({'schema':'cafe1.prompt-set.v1','prompts':prompts},sort_keys=True,ensure_ascii=False,indent=2)+'\n');print('prompts',len(prompts),'sha256',sha(out.read_bytes()))

from pathlib import Path
import ast,hashlib,json,os,subprocess
D=Path('/mnt/raid0/llm/tmp/df2/cafe4-v5-frozen-build'); model=Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf');store=Path('/mnt/raid0/llm/kernels/production/cpu');tokenizer=store/'llama-tokenize'
prompts=['Explain two ways to organize a workshop.','Describe three ways roots protect soil.','Explain how a lock prevents a race condition.','Outline how to test a search feature.','Summarize why bridges need expansion joints.','Describe a safe procedure for inspecting a bicycle.','Explain the purpose of a database index.','List three ways to make a meeting agenda clear.','Describe how water moves through a watershed.']
previous=json.loads(Path('/mnt/raid0/llm/worktrees/mains/h-df2/docs/reports/cafe4-rollback-preparation/native-rewind-unknown-20261104/RESULT.json').read_text())['model']; st=model.stat(); current={'dev':st.st_dev,'ino':st.st_ino,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns};assert current==previous['stat']
env=dict(os.environ,LD_LIBRARY_PATH=str(store));cmd=[str(tokenizer),'--ids','--model',str(model),'--prompt']; link=subprocess.check_output(['ldd',str(tokenizer)],text=True,env=env);assert 'not found' not in link
paths=[]
for line in link.splitlines():
 if '=>' in line:
  name,path=line.strip().split('=>',1); p=Path(path.strip().split()[0]);
  if name.startswith(('libllama','libggml')):
   assert p.resolve().is_relative_to(store.resolve());paths.append(str(p.resolve()))
assert any('libllama' in p for p in paths)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
rows=[]
for prompt in prompts:
 out=subprocess.run([*cmd,prompt],env=env,text=True,capture_output=True,check=True)
 ids=ast.literal_eval(out.stdout.strip());assert isinstance(ids,list) and 1<=len(ids)<120 and all(type(v) is int and v>=0 for v in ids)
 rows.append({'text':prompt,'utf8_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'ids':ids})
m={'schema':'cafe4.frozen.prompt.ids.v1','model':{'path':str(model),'sha256':previous['sha256'],'hash_mode':'prior content verification plus unchanged full stat','stat':current},'tokenizer':{'path':str(tokenizer.resolve()),'sha256':digest(tokenizer),'dsos':{p:digest(p) for p in sorted(set(paths))},'ld_library_path':str(store),'flags':['--ids','--model','--prompt'],'add_special':'model default','parse_special':True,'vocab_only':True},'prompts':rows}
(D/'frozen-prompts.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
header=['#pragma once','// Prepared with content-bound v10 vocabulary-only tokenizer.','static const std::vector<llama_tokens> cafe4_frozen_prompts = {']
for row in rows: header.append('    {'+', '.join(map(str,row['ids']))+'},')
header.append('};');(D/'frozen_prompt_ids.hpp').write_text('\n'.join(header)+'\n');(D/'tokenizer-linkage.txt').write_text(link)
print('Prepared',len(rows),'prompt ID arrays; token lengths:',[len(row['ids']) for row in rows])

#!/usr/bin/env python3
"""Freeze full-file prompts with the v10 native renderer and tokenizer, no inference."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
BIN = Path('/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin')
MODEL = Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
TEMPLATE = Path('/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja')
EXPECTED = {'test-chat-template': '6f90322839d2f436ac410437f2610346fe93c2544eacee63358a7eef06d8238f',
            'llama-tokenize': '3893e741f796e21342fd0d5a599db9e9eb3050448532689339f2523f19776407'}
IDS = ['fresh_shipping', 'fresh_time', 'fresh_inventory', 'fresh_pricing', 'fresh_measurement']
ORDERS = [['current_dflash2','plain','prompt_lookup'], ['prompt_lookup','current_dflash2','plain'],
          ['plain','prompt_lookup','current_dflash2'], ['current_dflash2','prompt_lookup','plain'],
          ['plain','current_dflash2','prompt_lookup']]

def digest(data): return hashlib.sha256(data).hexdigest()

def build_prompt(task):
    parts = [task['prompt'].strip(), '', 'Current file contents:']
    for name, body in task['files'].items(): parts.append(f'\n--- {name} ---\n{body}')
    parts.append('\nReturn the COMPLETE final content of EVERY file that should exist after your change, '
                 'each in exactly this format (and nothing else):\n<<<FILE: filename>>>\n<full file content>\n'
                 '<<<END>>>\nTo delete a file, output: <<<DELETE: filename>>>')
    return '\n'.join(parts)

def tokenize(text, env):
    p=subprocess.run([str(BIN/'llama-tokenize'),'-m',str(MODEL),'--offline','--ids','--stdin'],
                     input=text.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=180,env=env)
    tokens=ast.literal_eval(p.stdout.decode().strip())
    if not isinstance(tokens,list) or len(tokens)<5 or any(type(x) is not int or x<0 for x in tokens):
        raise ValueError('invalid native token IDs')
    grams=[tuple(tokens[i:i+5]) for i in range(len(tokens)-4)]
    return {'count':len(tokens),'token_ids_sha256':digest(json.dumps(tokens).encode()),
            'repeated_5gram_fraction':(len(grams)-len(set(grams)))/len(grams)}

def main():
    for name, expected in EXPECTED.items():
        if digest((BIN/name).read_bytes()) != expected: raise RuntimeError(f'{name} digest mismatch')
    if digest(TEMPLATE.read_bytes()) != TEMPLATE.stem: raise RuntimeError('template digest mismatch')
    source=(HERE/'corpus.json').read_bytes(); corpus=json.loads(source)
    byid={x['id']:x for x in corpus}
    if len(byid)!=5 or set(byid)!=set(IDS): raise ValueError('unexpected corpus task IDs')
    env=dict(os.environ,LD_LIBRARY_PATH=str(BIN))
    tasks=[]
    scratch=Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp')
    with tempfile.TemporaryDirectory(dir=scratch) as td:
        for ident in IDS:
            task=byid[ident]; prompt=build_prompt(task)
            data={'messages':[{'role':'user','content':prompt}], 'enable_thinking':False, 'add_generation_prompt':True, 'tools':[]}
            ip=Path(td)/'input.json'; op=Path(td)/'output.txt'
            ip.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            subprocess.run([str(BIN/'test-chat-template'),'--no-common','--json',str(ip),'--output',str(op),str(TEMPLATE)],
                           env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
            rendered=op.read_text(encoding='utf-8')
            if not rendered or prompt not in rendered: raise ValueError('renderer output missing prompt')
            tokens=tokenize(rendered,env)
            tasks.append({'id':ident,'prompt':task['prompt'],'files':task['files'],'rendered_prompt':prompt,
                          'native_rendered_prompt':rendered,'native_tokenization':dict(tokens,
                          prompt_sha256=digest(rendered.encode()),formatter_input=data)})
    plan={'schema':'epyc.sr8.fresh-edit-plan.v1','corpus_sha256':digest(source),
          'corpus_source':'corpus.json','schedule':[{'rep':i+1,'task':ident,'arms':ORDERS[i]}
                                                   for i,ident in enumerate(IDS)],'tasks':tasks,
          'native_renderer':{'path':str(BIN/'test-chat-template'),'sha256':EXPECTED['test-chat-template'],
                             'template':str(TEMPLATE),'template_sha256':TEMPLATE.stem,
                             'tokenizer_path':str(BIN/'llama-tokenize'),'tokenizer_sha256':EXPECTED['llama-tokenize'],
                             'tokenizer_model':str(MODEL)},
          'limitations':['Fresh synthetic BEP-style multi-file edits, different from the canonical BEP track; not a route authority.',
                         'Prior exposure review is scoped; no claim of global or pretraining independence.',
                         'Each arm has fresh server and one active request; no concurrency throughput claim.',
                         'Reference solutions and verifier controls are excluded from model prompts.']}
    (HERE/'candidate-plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'tasks':len(tasks),'corpus_sha256':digest(source),'plan_sha256':digest((HERE/'candidate-plan.json').read_bytes())}))

if __name__=='__main__': main()

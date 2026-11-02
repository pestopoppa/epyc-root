#!/usr/bin/env python3
"""Render and tokenize the SR-6 candidate corpus without inference.

Uses pinned v10 test-chat-template's native direct Jinja engine and tokenizer.
The native renderer is checked against every archived full-model server exposure.
Output remains preparation only; model hash, inventory completeness, sampler,
semantic separation, placement, and publication are separate requirements.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from prompt_audit import audit, hashes

ROOT = Path('/mnt/raid0/llm')
BIN = ROOT / 'kernels/production/cpu'
MODEL = ROOT / 'models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
TEMPLATE = ROOT / 'models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja'
PREVIOUS = ROOT / 'tmp/sr6-qwen36-draft-width-20261101'
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'tmp/speculative-decoding-mtp/prompt-prep-v2'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def render(prompt, directory):
    data = {'messages':[{'role':'user','content':prompt}], 'enable_thinking':False,
            'add_generation_prompt':True, 'tools':[]}
    spec=directory/'input.json'; result=directory/'output.txt'
    spec.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    env=os.environ.copy(); env['LD_LIBRARY_PATH']=str(BIN)
    subprocess.run([str(BIN/'test-chat-template'),'--no-common','--json',str(spec),
                    '--output',str(result),str(TEMPLATE)], env=env, check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
    return result.read_text(encoding='utf-8')


def tokenize(prompt):
    env=os.environ.copy(); env['LD_LIBRARY_PATH']=str(BIN)
    r=subprocess.run([str(BIN/'llama-tokenize'),'-m',str(MODEL),'--offline','--ids','--stdin'],
                     input=prompt.encode('utf-8'), env=env, check=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, timeout=60)
    tokens=ast.literal_eval(r.stdout.decode('utf-8').strip())
    if not isinstance(tokens,list) or len(tokens)<5 or any(type(x) is not int or x<0 for x in tokens):
        raise ValueError('bad token output')
    return tokens


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    template_hash=sha(TEMPLATE.read_bytes())
    if template_hash != TEMPLATE.stem:
        raise ValueError('template digest mismatch')
    candidate_path=HERE/'candidate-upstream-corpus-2023.json'
    raw=candidate_path.read_bytes(); corpus=json.loads(raw)
    inv_paths=[HERE/'prior-sr6-diagnostic-hashes.json',HERE/'copyspec-p1-exclusions.json']
    exclusions=set()
    for path in inv_paths: exclusions.update(hashes(json.loads(path.read_bytes())))
    prior={x['id']:x for x in json.loads((PREVIOUS/'PROMPTS.json').read_bytes())['prompts']}
    # Compare all actual server renderings, retaining both raw and formatted hashes.
    comparisons=[]; seen={}
    for path in sorted((PREVIOUS/'run').glob('*.exposure.json')):
        item=json.loads(path.read_bytes()); ident=item['prompt_id']
        if ident not in prior: raise ValueError('unknown archived exposure')
        seen.setdefault(ident,item['request']['prompt'])
        if seen[ident] != item['request']['prompt']:
            raise ValueError('prior rendering varies by arm')
    if len(seen)!=15 or len(prior)!=15: raise ValueError('incomplete archived control')
    with tempfile.TemporaryDirectory(dir=OUT) as tmp:
        d=Path(tmp)
        for ident, expected in sorted(seen.items()):
            obtained=render(prior[ident]['prompt'],d)
            if obtained != expected: raise ValueError('native renderer differs from server')
            comparisons.append({'id':ident,'sha256':sha(obtained.encode())})
        rows=[]
        for item in corpus['prompts']:
            rendered=render(item['prompt'],d)
            row=dict(item,rendered_prompt=rendered,rendered_token_ids=tokenize(rendered),
                     source_reference=item['source'],
                     source=json.dumps(item['source'],sort_keys=True,separators=(',', ':')))
            rows.append(row)
    manifest={'schema':'sr6.rendered-candidate.v1','prompts':rows}
    # Audit only the structural fields: the provenance in the output remains
    # upstream_git_human_authorship_not_independently_verified. This temporary
    # adapter satisfies the older auditor's asserted source_kind convention;
    # it is not evidence that authorship has been established.
    audit_rows=[dict(row,source_kind='non_model') for row in rows]
    results=audit({'prompts':audit_rows},exclusions,set())
    # Exact comparisons include both raw and rendered forms of archived exposures.
    seen_all=exclusions | {sha(x.encode()) for x in seen.values()}
    if any(sha(row[k].encode()) in seen_all for row in rows for k in ('prompt','rendered_prompt')):
        raise ValueError('candidate matches archived raw/rendered exposure')
    manifest_bytes=json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2).encode()
    (OUT/'rendered-candidate.json').write_bytes(manifest_bytes)
    summary={'status':'PREPARATION_ONLY_NOT_PUBLICATION_AUTHORITY',
             'candidate_sha256':sha(raw), 'rendered_manifest_sha256':sha(manifest_bytes),
             'template_sha256':template_hash,
             'renderer_sha256':sha((BIN/'test-chat-template').read_bytes()),
             'tokenizer_sha256':sha((BIN/'llama-tokenize').read_bytes()),
             'archived_server_render_controls':comparisons,
             'prior_inventory_sha256':[sha(x.read_bytes()) for x in inv_paths],
             'repetition':results['prompts'],
             'limitations':['full model digest recorded separately', 'known exposure inventory may be incomplete',
                            'source authorship and semantic overlap unproven', 'runtime and sampler not sealed']}
    (OUT/'rendered-candidate-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({'status':summary['status'],'prompts':len(rows),'archived_controls':len(comparisons),
                      'rendered_manifest_sha256':summary['rendered_manifest_sha256']}))

if __name__=='__main__': main()

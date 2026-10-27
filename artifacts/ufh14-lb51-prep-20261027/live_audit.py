#!/usr/bin/env python3
"""Audit original LB5 fixtures through an already-running scratch llama-server."""
import json, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'source/scripts/benchmark/prefix_property'))
import harness as h
from verdict_check import validate_verdict

FIXTURE_IDS = {'agent_tool_loop', 'agent_tool_loop_b', 'chat_multiturn', 'repl_code_lines'}

def validate_fixtures(fixtures):
    ids = [f['id'] for f in fixtures]
    if len(ids) != 4 or set(ids) != FIXTURE_IDS:
        raise ValueError('fixture set does not match the four original LB5 fixtures')
    if any(not h.assistant_turns(f['messages']) for f in fixtures):
        raise ValueError('fixture contains no checkable assistant turn')

class ServerRenderer:
    def __init__(self, url, template):
        self.url, self.template_text = url, template
    def __call__(self, messages, *, add_generation_prompt=True, enable_thinking=False, tools=None, extra=None):
        if extra: raise ValueError('unexpected template kwargs')
        # Fixture-only generated fields describe the simulated response, not chat protocol fields.
        clean = [{k:v for k,v in m.items() if not k.startswith('generated')} for m in messages]
        body = {'messages': clean, 'add_generation_prompt': add_generation_prompt,
                'chat_template_kwargs': {'enable_thinking': enable_thinking}}
        if tools: body['tools'] = tools
        req = urllib.request.Request(self.url + '/apply-template', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, timeout=30) as response:
            obj = json.load(response)
        if not isinstance(obj.get('prompt'), str): raise ValueError('server returned no string prompt')
        return obj['prompt']

def main():
    if len(sys.argv) != 4: raise SystemExit('usage: live_audit.py URL TEMPLATE RESULT')
    template = Path(sys.argv[2]).read_text()
    eng = ServerRenderer(sys.argv[1], template)
    tok = h.VocabTokenizer('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
    wire = h.tool_wire(template); fixtures = h.all_fixtures(); rows = {}
    validate_fixtures(fixtures)
    for fx in fixtures:
        p1 = h.check_reply_prefix(eng, fx, eog='<|im_end|>', wire=wire)
        p2 = h.check_token_prefix(eng, tok, fx, eog='<|im_end|>', wire=wire)
        if not p1 or not p2 or len(p1) != len(h.assistant_turns(fx['messages'])) or len(p2) != len(p1):
            raise ValueError('missing per-turn checks')
        rows[fx['id']] = {'P1': [vars(x) for x in p1], 'P2': [vars(x) for x in p2]}
    t = h.check_shared_trunk(eng, tok, h.load_fixture('agent_tool_loop'), h.load_fixture('agent_tool_loop_b'))
    verdict = {'P1': all(x['ok'] for r in rows.values() for x in r['P1']), 'P2': all(x['ok'] for r in rows.values() for x in r['P2']), 'P3': t.ok}
    result = {'model':'Qwen3.8-27B-Q8_0', 'roles':['architect_critic','coder_escalation','ingest_long_context'], 'thinking':False, 'wire':wire, 'fixtures':rows, 'trunk':vars(t), 'verdict':verdict}
    Path(sys.argv[3]).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(verdict)); return 0 if validate_verdict(verdict) else 1
if __name__ == '__main__': sys.exit(main())

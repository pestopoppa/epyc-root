from pathlib import Path
import flash_resolution as f
D=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-shipped-parity/successor')
actual_failed=(D/'failed-startup.log').read_text()
actual_on=(D/'real-fa-enabled-server.log').read_text()
assert f.resolve(actual_on)=='on'
try: f.resolve(actual_failed)
except ValueError: pass
else: raise AssertionError('actual level-3 log lacked resolution but was accepted')
# Synthetic controls model literal branches in pinned llama-context.cpp; no model output claimed.
request='0.11.883.249 I llama_context: flash_attn    = auto\n'
off='0.13.011.581 W resolve_fused_ops: Flash Attention not supported, set to disabled\n'
on='0.13.011.581 I resolve_fused_ops: Flash Attention enabled\n'
assert f.resolve(request+off)=='off'
for s in (actual_failed+request,request+on+off,request+'unrelated Flash Attention enabled\n',on,request+'llama_context: flash_attn = enabled\n'+on):
 try: f.resolve(s)
 except ValueError: pass
 else: raise AssertionError('absent/ambiguous/unrelated line accepted')
print('PASS actual failed startup refused, preserved real server enabled parsed; source-derived synthetic off, auto, conflict and unrelated controls')

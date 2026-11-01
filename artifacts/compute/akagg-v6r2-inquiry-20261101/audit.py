#!/usr/bin/env python3
"""Read-only streaming KV source ancestry and image custody inquiry."""
import hashlib,json,pathlib,subprocess
repo='/mnt/raid0/llm/llama.cpp'; commit='111bff89da1f06939908781ca5156d5fca24e875'
bases={'v9':'0db32c06e3e550065b78311a6031ef3dd2c4f27c','v10':'ffc1bac82eeca6f9099e1ccd9ba49703c460a115','c5':'c72ec82f5417bb2937310326120f149b665e8400'}
ancestry={}
for k,base in bases.items():
 p=subprocess.run(['git','-C',repo,'merge-base','--is-ancestor',commit,base]); assert p.returncode==0; ancestry[k]={'commit':base,'ancestor_rc':p.returncode}
img=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5'); lib=img/'bin/libllama-common.so.0.0.10419'; h=hashlib.sha256(lib.read_bytes()).hexdigest(); matches=[x for x in (img/'SHA256SUMS').read_text().splitlines() if x.endswith('  ./libllama-common.so.0.0.10419')]; assert len(matches)==1 and matches[0].split()[0]==h
strings=subprocess.run(['strings',str(lib)],check=True,capture_output=True,text=True).stdout.splitlines(); flags=['--kv-streaming-sink','--kv-streaming-window']; assert all(x in strings for x in flags)
out={'schema':'epyc.akagg.v6r2.source-inquiry.v1','v6_source':'632ce0f927','forward_port':commit,'ancestry':ancestry,'ancestry_command':['git','-C',repo,'merge-base','--is-ancestor',commit,'<base>'],'image_path':str(lib),'image_sha256':h,'manifest_path':str(img/'SHA256SUMS'),'manifest_entry':matches[0],'observed_strings':flags,'scope':'Source and content proof only; no execution, speed, parity or production behavior claim. Edge-case discard clamps differ between original v6 patch and port.'}
p=pathlib.Path(__file__).with_name('RESULT.json');p.write_text(json.dumps(out,indent=2)+'\n');print(hashlib.sha256(p.read_bytes()).hexdigest())

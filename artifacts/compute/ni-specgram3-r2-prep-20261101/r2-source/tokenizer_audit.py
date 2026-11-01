from pathlib import Path
import os
OUT=Path(os.environ["SPECGRAM3_REPLAY_OUT"]);OUT.mkdir(exist_ok=True)
import sys,json,hashlib
from gguf import GGUFReader
from tokenizers import Tokenizer
M="/mnt/raid0/llm/models/"
ggufs={"frontdoor Qwen3.6-35B-A3B-MTP":M+"Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
"Qwen3.8-27B":M+"Qwen3.8-27B-Q8_0.gguf",
"Qwen3.8-Flash-Next":M+"unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf",
"Qwen3-VL-30B":M+"lmstudio-community/Qwen3-VL-30B-A3B-Instruct-GGUF/Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf"}
hf={"27B":M+"turboderp/Qwen3.8-27B-exl3-4.00bpw/tokenizer.json","Flash":M+"turboderp/Qwen3.8-Flash-Next-exl3-3.05bpw/tokenizer.json","q36-27b-dflash":M+"dflash/Qwen3.6-27B-DFlash/tokenizer.json","q3-4b":"/mnt/raid0/llm/hf-models/Qwen3-4B-Instruct-2507/tokenizer.json"}
hv={}
for k,p in hf.items():
    if not Path(p).exists():
        print("UNAVAILABLE original tokenizer",k,p,flush=True);continue
    t=Tokenizer.from_file(p); v=t.get_vocab(with_added_tokens=True); n=max(v.values())+1
    arr=[None]*n
    for s,i in v.items(): arr[i]=s
    hv[k]=arr
out={}
for name,p in ggufs.items():
    r=GGUFReader(p)
    f=r.fields
    def s(k):
        x=f[k]; return bytes(x.parts[x.data[0]]).decode()
    toks=[bytes(f["tokenizer.ggml.tokens"].parts[i]).decode(errors="replace") for i in f["tokenizer.ggml.tokens"].data]
    (OUT/("tokens-"+name.split()[0]+".json")).write_text(json.dumps(toks))
    (OUT/("header-"+name.split()[0]+".json")).write_text(json.dumps({'path':p,'size':Path(p).stat().st_size,'tokens_sha256':hashlib.sha256(json.dumps(toks).encode()).hexdigest(),'n_tokens':len(toks)}))
    model=s("tokenizer.ggml.model"); pre=s("tokenizer.ggml.pre") if "tokenizer.ggml.pre" in f else None
    ct=s("tokenizer.chat_template") if "tokenizer.chat_template" in f else ""
    print(name,"n_tok",len(toks),model,pre,"tmpl_len",len(ct),"has <function=",("<function=" in ct),"has tool_call json", ('"name": "' in ct or "'name'" in ct), flush=True)
    for k,arr in hv.items():
        m=min(len(arr),len(toks)); diff=sum(1 for i in range(m) if arr[i]!=toks[i])
        print("   vs",k,"len",len(arr),"diff",diff, flush=True)
    open(OUT/f"tmpl_{name.split()[0].replace('/','_')}.txt","w").write(ct)
    hashlib.sha256("\n".join(toks).encode()).hexdigest()

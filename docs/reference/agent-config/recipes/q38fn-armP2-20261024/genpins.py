import re,sys
# argv: COPY-dry-run.log out.txt. Pin EVERY tensor to its UD type except:
#  (a) blk.N.ffn_gate_exps / ffn_up_exps -> iq4_xs                      (ARM P part)
#  (b) Q8_0 attn_* / ssm_* / *_shexp 2D weights with ncols%256==0 -> q6_K (ARM P2 part)
# Q8_0 tensors of those classes with ncols%256!=0 cannot be Q6_K (llama.cpp's own fallback is Q8_0): pinned unchanged, listed as FALLBACK.
rx=re.compile(r'^\[\s*\d+/\d+\]\s+(\S+)\s+-\s+\[\s*(\d+),[^\]]*\],\s+type\s+=\s*(\S+?),')
cls=re.compile(r'\.(attn_[a-z_]*|ssm_[a-z_0-9]*|ffn_(gate|up|down)_shexp)\.weight$')
n=g=q=fb=0; fbn=set()
with open(sys.argv[2],'w') as o:
    for l in open(sys.argv[1]):
        m=rx.match(l)
        if not m: continue
        name,nc,t=m.group(1),int(m.group(2)),m.group(3); n+=1
        if re.search(r'\.ffn_(gate|up)_exps\.weight$',name): t='iq4_xs'; g+=1
        elif t=='q8_0' and cls.search(name):
            if nc%256==0: t='q6_K'; q+=1
            else: fb+=1; fbn.add(re.sub(r'blk\.\d+\.','blk.N.',name)+" ncols=%d"%nc)
        o.write("^%s$=%s\n"%(re.escape(name),t))
print("tensors",n,"gate_up_pinned",g,"q8_to_q6k",q,"fallback_kept_q8_0",fb,sorted(fbn))
assert n==1224 and g==96,(n,g)

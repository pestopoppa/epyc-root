import subprocess,glob,re,yaml,sys
rows=[]
for f in sorted(glob.glob(sys.argv[1]+'/*.co')):
    out=subprocess.run(['/opt/rocm/llvm/bin/llvm-readelf','--notes',f],capture_output=True,text=True).stdout
    i=out.find('---'); j=out.find('...',i)
    if i<0: continue
    try: md=yaml.safe_load(out[i:j])
    except Exception as e: continue
    for k in md.get('amdhsa.kernels',[]):
        n=k.get('.name','')
        if 'flash_attn' not in n: continue
        rows.append((n,k.get('.vgpr_count'),k.get('.agpr_count'),k.get('.vgpr_spill_count'),k.get('.sgpr_spill_count'),k.get('.group_segment_fixed_size'),k.get('.private_segment_fixed_size')))
for r in rows: print(*r,sep='\t')

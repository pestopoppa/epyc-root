import re,subprocess,os,sys
d=open(sys.argv[1],'rb').read()
offs=[m.start() for m in re.finditer(b'__CLANG_OFFLOAD_BUNDLE__',d)]
offs.append(len(d))
L='/opt/rocm/llvm/bin'
os.makedirs('co',exist_ok=True)
n=0
for i in range(len(offs)-1):
    chunk=d[offs[i]:offs[i+1]]
    p=f'co/b{i}.bin'; open(p,'wb').write(chunk)
    r=subprocess.run([f'{L}/clang-offload-bundler','--unbundle','--type=o',f'--input={p}','--targets=hipv4-amdgcn-amd-amdhsa--gfx90a',f'--output=co/b{i}.co'],capture_output=True)
    os.remove(p)
    if r.returncode==0: n+=1
print(len(offs)-1,n)

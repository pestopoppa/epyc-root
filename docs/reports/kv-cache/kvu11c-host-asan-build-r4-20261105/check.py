import hashlib,json,subprocess
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu11c-asan-build-20261105/packet-r4'); S=Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu11c-asan-build-20261105/source')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for root,rev in [(S,"aca703283192f892f1e85636fbc48832c4d5560a"),(S/"ggml","b86f660238dcc1a83b7cbf5a72d355a965de9245")]:
 def git(*a): return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()
 assert git("rev-parse","HEAD")==rev and (root/".git").is_file()
 assert subprocess.run(["git","-C",str(root),"symbolic-ref","-q","HEAD"],stdout=subprocess.DEVNULL).returncode==1
 assert not git("status","--porcelain","--untracked-files=all")
 assert all(x[0]=="H" for x in git("ls-files","-v").splitlines())
for name,digest in json.loads((D/"pins.json").read_text()).items(): assert sha(Path(name))==digest,name
print("source and input pins verified")

import json,subprocess
base='d16bfe05a744909de4b27f5875fe0d4ed41ce607'
def tree(ref):
 out={}
 for line in subprocess.check_output(['git','-C','/testbed','ls-tree','-rz',ref]).split(b'\0'):
  if line:
   meta,path=line.split(b'\t');mode,kind,oid=meta.split();out[path.decode()]=(mode.decode(),kind.decode(),oid.decode())
 return out
a,b=tree(base),tree('HEAD');changes=[];modes=0
for path in sorted(a.keys()|b.keys()):
 if a.get(path,(None,None,None))[1:] != b.get(path,(None,None,None))[1:]:changes.append({'path':path,'base':a.get(path),'head':b.get(path)})
 elif a[path][0]!=b[path][0]:modes+=1
print(json.dumps({'base':base,'head':subprocess.check_output(['git','-C','/testbed','rev-parse','HEAD']).decode().strip(),'blob_or_kind_changes':changes,'mode_only_changes':modes},indent=2))

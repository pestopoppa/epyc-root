"""Acquire immutable original archives and run only existing read-only shared grader."""
from pathlib import Path,PurePosixPath
import os,sys,json,hashlib,subprocess,time,zipfile,stat
H=Path(__file__).resolve().parent;M=json.loads((H/"source-input.json").read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
assert os.environ["GITHUB_EVENT_NAME"]=="push" and os.environ["GITHUB_RUN_ATTEMPT"]=="1" and os.environ["GITHUB_REF"]=="refs/heads/"+M["branch"]
assert sha((H/"safe_download05c54.py").read_bytes())==M["safe_download_sha256"]
assert sha((H/"grade_original_batch.py").read_bytes())==M["batch_script_sha256"]
assert subprocess.check_output(["git","-C",str(H/"carrier4c0"),"rev-parse","HEAD"]).decode().strip()==M["reader_commit"]
for row in M["reader_sources"]:assert sha((H/"carrier4c0"/row["path"]).read_bytes())==row["sha256"]
root=Path(os.environ["RUNNER_TEMP"])/"ni08-grade-inputs";root.mkdir();out=Path(os.environ["RUNNER_TEMP"])/"ni08-secondary-grades";out.mkdir();journal=(out/"acquisition-journal.jsonl").open("x");receipts=[]
def command(argv,stdout=None,timeout=300):
 start=time.time_ns();r=subprocess.run(argv,stdout=stdout or subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout);row={"argv":argv,"start_ns":start,"end_ns":time.time_ns(),"exit":r.returncode,"stderr_sha256":sha(r.stderr)};journal.write(json.dumps(row)+"\n");journal.flush();assert r.returncode==0,"original acquisition command failed; no retry";return r.stdout
def api(endpoint,family,kind):
 raw=command(["/usr/bin/gh","api",endpoint]);(out/(family+"-"+kind+".json")).write_bytes(raw);return json.loads(raw)
for item in M["originals"]:
 family=item["family"];a=item["artifact"];r=item["run"];live=api("repos/pestopoppa/epyc-root/actions/runs/"+str(r["id"]),family,"original-run-api")
 for key in ["id","head_sha","head_branch","run_attempt","event"]:assert live[key]==r[key]
 current=api("repos/pestopoppa/epyc-root/actions/artifacts/"+str(a["id"]),family,"original-artifact-api")
 for key in ["id","name","size_in_bytes","digest"]:assert current[key]==a[key]
 assert not current["expired"] and current["workflow_run"]["id"]==r["id"] and current["workflow_run"]["head_sha"]==r["head_sha"]
 directory=root/family;directory.mkdir();archive=directory/"original.zip"
 with archive.open("xb") as f:command([sys.executable,str(H/"safe_download05c54.py"),"--dest",str(directory),"--ledger",str(out/(family+"-safe-download-ledger.jsonl")),"--","/usr/bin/gh","api","repos/pestopoppa/epyc-root/actions/artifacts/"+str(a["id"])+"/zip"],stdout=f)
 assert archive.stat().st_size==a["size_in_bytes"] and "sha256:"+sha(archive.read_bytes())==a["digest"]
 dest=directory/"extracted"
 with zipfile.ZipFile(archive) as z:
  names=set();assert sum(x.file_size for x in z.infolist())<=2*1024**3
  for member in z.infolist():
   pure=PurePosixPath(member.filename);n=member.filename.rstrip("/");assert n and not pure.is_absolute() and "\\"not in member.filename and ":"not in member.filename and not any(p in(".","..")for p in pure.parts) and pure.as_posix().rstrip("/")==n and n not in names;names.add(n);assert stat.S_IFMT(member.external_attr>>16)in(0,stat.S_IFREG,stat.S_IFDIR) and not member.flag_bits&1
  assert z.testzip()is None;dest.mkdir()
  for member in z.infolist():
   q=dest/member.filename;assert q.resolve().is_relative_to(dest.resolve())
   if member.is_dir():q.mkdir(parents=True,exist_ok=True);continue
   q.parent.mkdir(parents=True,exist_ok=True)
   with q.open("xb")as f:f.write(z.read(member))
 found=list(dest.rglob("native/receipt.json"));assert len(found)==1 and sha(found[0].read_bytes())==item["receipt_sha256"];receipts.append({"family":family,"path":str(found[0]),"sha256":item["receipt_sha256"]})
 (out/(family+"-archive-custody.json")).write_text(json.dumps({"original_artifact":a,"original_run":r,"receipt_sha256":item["receipt_sha256"],"API_digest_size_CRC_paths_types_verified":True,"native_execution":False},indent=2)+"\n")
inputfile=root/"four-originals.json";inputfile.write_text(json.dumps({"reader_commit":M["reader_commit"],"reader_sources":M["reader_sources"],"receipts":receipts},indent=2)+"\n");command([sys.executable,"-I",str(H/"grade_original_batch.py"),str(inputfile),str(out/"shared-grades")]);(out/"source-input.json").write_bytes((H/"source-input.json").read_bytes());journal.close()

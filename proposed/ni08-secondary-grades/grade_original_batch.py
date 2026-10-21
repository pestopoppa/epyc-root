"""Read-only original tuple projection/shared grade; no native execution or ledger writes."""
from pathlib import Path
import sys,json,hashlib
H=Path(__file__).resolve().parent
manifest=json.loads(Path(sys.argv[1]).read_bytes());out=Path(sys.argv[2]);assert not out.exists()
for row in manifest["reader_sources"]:
 raw=(H/"carrier4c0"/row["path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==row["sha256"]
sys.path[:0]=[str(H/"carrier4c0"),str(H/"carrier4c0/scripts/vidya")]
from adapters.ci_conformance import native_rows,project_ci_conformance
from claim_tuple import grade
out.mkdir(mode=0o700);results=[]
for row in manifest["receipts"]:
 path=Path(row["path"]);assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
 native=native_rows(path)
 if native:
  record=native[0]["record"];projected=project_ci_conformance(native[0]);graded=grade(projected)
  result={"family":row["family"],"original_receipt_path":str(path),"original_receipt_file_sha256":row["sha256"],"reader_commit":manifest["reader_commit"],"native_value":record["fixture_execution_conformant"],"counts":record["summary"]["counts"],"shared_grade":graded,"new_native_execution":False,"ledger_append":False,"note":"Secondary read-only grade output; original native receipt remains unchanged."}
 else:result={"family":row["family"],"original_receipt_path":str(path),"native_value":None,"shared_grade":None,"new_native_execution":False,"ledger_append":False}
 q=out/(row["family"]+"-shared-grade.json");q.write_text(json.dumps(result,indent=2,default=str)+"\n");results.append({"family":row["family"],"path":str(q),"sha256":hashlib.sha256(q.read_bytes()).hexdigest()})
(out/"batch-result.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps(results,indent=2))

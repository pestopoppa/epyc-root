"""Read-only predecessor evidence gate; cutoff classification preserved."""
import hashlib,json
from pathlib import Path
from cutoff_policy import censored,record_cutoff
E=Path("/mnt/raid0/llm/tmp/yarn-native-count-forensic-20261029/s2-native-count-evidence.json")
SHA="70f883a39e2639612aa75d2a2ed0b85d698433e9c2a8b8c4f196352e0c9ceb4a"
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify_old():
 if digest(E)!=SHA:raise ValueError("s2 evidence changed")
 x=json.loads(E.read_bytes())
 for item in x["logs"]+x["count_files"]:
  if digest(item["path"])!=item["sha256"]:raise ValueError("s2 source evidence changed")
 if digest(x["model_edge_witness"])!=x["model_edge_witness_sha256"]:raise ValueError("model witness changed")
 return x

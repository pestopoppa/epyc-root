import subprocess,os,sys,json
from pathlib import Path
from datetime import datetime,timezone
p=Path(__file__).resolve().parent;o=Path("original");o.mkdir(exist_ok=True)
argv=[sys.executable,"-m","pytest","-p","no:cacheprovider",str(p/"payload/research/scripts/benchmark/test_score_tulving_run.py"),str(p/"payload/research/scripts/benchmark/test_tulving_srs_comparison.py"),str(p/"payload/candidate-ROOT/test_m12f_capture_admission.py"),"--basetemp",str(o.resolve()/"fake-tmp"),"--junitxml",str(o.resolve()/"junit.xml")]
start=datetime.now(timezone.utc).isoformat();(o/"test-start.json").write_text(json.dumps({"argv":argv,"cwd":os.getcwd(),"start_UTC":start},indent=2)+"\n")
with open(o/"stdout","xb") as stdout,open(o/"stderr","xb") as stderr:r=subprocess.run(argv,stdout=stdout,stderr=stderr)
(o/"test-receipt.json").write_text(json.dumps({"argv":argv,"cwd":os.getcwd(),"start_UTC":start,"end_UTC":datetime.now(timezone.utc).isoformat(),"raw_exit":r.returncode},indent=2)+"\n")
(o/"exit").write_text(str(r.returncode)+"\n");print((o/"stdout").read_text());print((o/"stderr").read_text(),file=sys.stderr);sys.exit(r.returncode)

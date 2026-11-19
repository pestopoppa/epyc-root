import json, os, re, sys
from pathlib import Path
log = Path(sys.argv[1]).read_text()
m = re.search(r'\b(\d+) passed\b', log)
if not m or int(m.group(1)) < 30 or re.search(r'\b\d+ (failed|error)', log):
    raise SystemExit('unit suite did not pass')
dry = os.environ.get('FILLER_DRYRUN') == '1'
out = Path(sys.argv[2])
if dry and not out.parent.resolve().is_relative_to(Path(os.environ['FILLER_DRYRUN_DIR']).resolve()):
    raise SystemExit('dry output escaped fixture root')
fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump({'schema':'dtap.crm_live_source_tests.v1','passed':int(m.group(1)),'capture_kind':'fixture' if dry else 'source-test','model_invoked':False,'source_commit':'ec063054d2d7e2e801b130d124fec18683a96a15'}, f)
    f.write('\n'); f.flush(); os.fsync(f.fileno())

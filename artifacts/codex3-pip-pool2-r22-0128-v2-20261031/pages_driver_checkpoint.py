"""Shard integration; caller owns process, admission and deadline."""
import hashlib, os
from pathlib import Path
import json
def name_key(page):return json.dumps(page,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def run(pages, image_root, layout_dir, endpoint, factory, journal, worker, active, trace, context):
    if not pages or len({p["image"] for p in pages}) != len(pages): raise ValueError("empty or duplicate pages")
    counts={"complete":0,"unknown":0,"missing":0,"invalid":0}
    for page in pages:
        state=journal.state(page)
        if state=="complete": counts[state]+=1; continue
        prefix="region-"+hashlib.sha256(name_key(page)).hexdigest()[:24]+"-"
        if state=="unknown":
            root=journal.writer.root
            starts=journal.writer.glob(prefix+"*.start.json")
            if not journal.writer.exists(prefix+"layout.json") or any(not journal.writer.exists(p.name.replace(".start.json",".result.json")) for p in starts): counts[state]+=1; continue
        elif state!="missing": counts[state]+=1; continue
        if not active(): counts["missing"]+=1; continue
        name=page["image"]
        if Path(name).name!=name: raise ValueError("invalid image name")
        path=Path(image_root)/name
        h=hashlib.sha256()
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            before=os.fstat(fd)
            with os.fdopen(fd,"rb",closefd=False) as f:
                for chunk in iter(lambda:f.read(1048576),b""): h.update(chunk)
            after=os.fstat(fd); current=path.stat(follow_symlinks=False)
        finally: os.close(fd)
        identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if identity(before)!=identity(after) or identity(after)!=identity(current) or h.hexdigest()!=page["sha256"] or after.st_size!=page["bytes"]: raise RuntimeError("image identity mismatch")
        if not active(): counts["missing"]+=1; continue
        if state=="missing":journal.begin(page)
        checkpoint=dict(context,writer=journal.writer,prefix=prefix)
        markdown=worker.run(path,layout_dir,endpoint,factory,trace,lambda when:journal.sent(page,when),checkpoint)
        if not active(): counts["unknown"]+=1; continue
        journal.finish(page,markdown)
        result_path=journal.writer.root/journal.name(page,"result")
        raw=journal.writer.read(result_path.name); result=json.loads(raw)
        provenance=context["provenance"];identity=provenance["identity"]
        receipt={"schema":"pip02-paddle-page-finish/v1","page":page,"campaign_sha256":identity["campaign_sha256"],"result_sha256":hashlib.sha256(raw).hexdigest(),"markdown_sha256":result["markdown_sha256"],"capture_sha256":provenance["origin_capture_sha256"],"grant_sha256":hashlib.sha256(provenance["origin_grant"].encode()).hexdigest() if provenance["origin_grant"] is not None else None,"source_pins_sha256":hashlib.sha256(json.dumps(identity["source_pins"],sort_keys=True,separators=(",",":")).encode()).hexdigest()}
        journal.writer.create(journal.name(page,"finish.json"),json.dumps(receipt,sort_keys=True,separators=(",",":")).encode())
        counts["complete"]+=1
    return counts

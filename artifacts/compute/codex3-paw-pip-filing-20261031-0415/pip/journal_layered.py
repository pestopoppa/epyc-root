"""No-reexposure page journal. Writer supplies no-clobber fsynced create."""
import hashlib, json, time
from pathlib import Path

def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def digest(v): return hashlib.sha256(canon(v)).hexdigest()
class Journal:
    def __init__(self, writer, campaign):
        self.writer=writer; self.root=Path(writer.root); self.campaign=digest(campaign)
    def name(self, page, kind): return digest({"campaign":self.campaign,"page":page})+"."+kind
    def state(self, page):
        start=self.root/self.name(page,"start"); end=self.root/self.name(page,"result")
        if not self.writer.exists(start.name): return "invalid" if self.writer.exists(end.name) else "missing"
        if not self.writer.exists(end.name): return "unknown"
        try:
            raw=self.writer.read(start.name); a=json.loads(raw); b=json.loads(self.writer.read(end.name))
            if set(a)!={"campaign","page","started_monotonic_ns"} or a["campaign"]!=self.campaign or a["page"]!=page or type(a["started_monotonic_ns"]) is not int or a["started_monotonic_ns"]<=0: return "invalid"
            if b["start_sha256"] != hashlib.sha256(raw).hexdigest() or b["markdown_sha256"] != hashlib.sha256(b["markdown"].encode()).hexdigest(): return "invalid"
            return "complete"
        except (OSError,ValueError,TypeError,KeyError): return "invalid"
    def begin(self,page):
        if self.state(page)!="missing": raise RuntimeError("page exposed or invalid")
        self.writer.create(self.name(page,"start"),canon({"campaign":self.campaign,"page":page,"started_monotonic_ns":time.monotonic_ns()}))
    def sent(self,page,when_ns):
        if self.state(page)!="unknown" or type(when_ns) is not int:raise RuntimeError("invalid request event")
        start=self.writer.read(self.name(page,"start")); obj=json.loads(start)
        if obj.get("campaign")!=self.campaign or obj.get("page")!=page or type(obj.get("started_monotonic_ns")) is not int or when_ns<obj["started_monotonic_ns"]:raise RuntimeError("request event binding")
        name=self.name(page,"sent"); path=self.root/name
        if self.writer.exists(name):
            prior=json.loads(self.writer.read(name))
            if prior.get("start_sha256")!=hashlib.sha256(start).hexdigest() or type(prior.get("sent_monotonic_ns")) is not int:raise RuntimeError("damaged request event")
            return
        self.writer.create(name,canon({"start_sha256":hashlib.sha256(start).hexdigest(),"sent_monotonic_ns":when_ns}))
    def finish(self,page,markdown):
        if self.state(page)!="unknown" or not isinstance(markdown,str) or len(markdown.encode())>8388608: raise RuntimeError("invalid page result")
        raw=self.writer.read(self.name(page,"start"))
        a=json.loads(raw)
        if set(a)!={"campaign","page","started_monotonic_ns"} or a["campaign"]!=self.campaign or a["page"]!=page or type(a["started_monotonic_ns"]) is not int or a["started_monotonic_ns"]<=0: raise RuntimeError("damaged start")
        self.writer.create(self.name(page,"result"),canon({"start_sha256":hashlib.sha256(raw).hexdigest(),"markdown":markdown,"markdown_sha256":hashlib.sha256(markdown.encode()).hexdigest()}))

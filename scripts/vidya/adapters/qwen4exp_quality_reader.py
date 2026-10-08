"""Strict SC54 receipt verifier/projector. No grading logic lives here."""
from __future__ import annotations
import hashlib, json, math, os, stat
import re
from collections import Counter
from pathlib import Path
from datetime import datetime

SCHEMA = "epyc.vidya.qwen4exp_quality_measurement.v1"
DECL_SCHEMA = "epyc.vidya.qwen4exp_quality_metric_declaration.v1"
_PPL_FINAL=re.compile(r"Final estimate: PPL = ([^\s]+) \+/- ([^\s]+)")
_KLD_ROW=re.compile(r"^\s*(Maximum|99\.9%|99\.0%|95\.0%|90\.0%|Median|10\.0%|5\.0%|1\.0%|0\.1%|Minimum)\s+KLD:\s*([^\s]+)\s*$",re.M)
_KLD_LABELS=("Maximum","99.9%","99.0%","95.0%","90.0%","Median","10.0%","5.0%","1.0%","0.1%","Minimum")
_RUN=re.compile(r"(?:calculating perplexity|computing):? (?:computing over|over) (\d+) chunks, n_ctx=(\d+), batch_size=(\d+), n_seq=(\d+)")
_PPL_CHUNKS=re.compile(r"\[(\d+)\][0-9.eE+-]+")
_KLD_CHUNKS=re.compile(r"^\s*(\d+)\s+[0-9.eE+-]+\s+±",re.M)

def _unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError("duplicate JSON key: "+key)
        result[key]=value
    return result

def _json(raw):
    return json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError("non-finite JSON constant: "+x)))

def _read_stable(path: Path, limit: int = 128 << 20, retain_bytes: bool = True):
    """Hash by streaming; bound only bytes retained for structured/text parsing."""
    parent = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(path.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode): raise ValueError("input is not a regular file")
            digest = hashlib.sha256(); chunks = [] if retain_bytes else None; size = 0
            while True:
                b = os.read(fd, 8 << 20)
                if not b: break
                size += len(b); digest.update(b)
                if retain_bytes:
                    if size > limit: raise ValueError("retained structured/text input exceeds size bound")
                    chunks.append(b)
            after = os.fstat(fd); named_after = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            fields = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
            if fields(before) != fields(after) or fields(named) != fields(named_after) or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino) or size != before.st_size:
                raise ValueError("input changed or path was replaced during read")
            raw = b"".join(chunks) if retain_bytes else None
            return raw, {"path": str(path.absolute()), "sha256": digest.hexdigest(), "size_bytes": size,
                         "mode": before.st_mode, "device": before.st_dev, "inode": before.st_ino,
                         "mtime_ns": before.st_mtime_ns, "ctime_ns": before.st_ctime_ns}
        finally: os.close(fd)
    finally: os.close(parent)

def _verify_identity(identity, retain_bytes: bool = False):
    if not isinstance(identity, dict) or set(identity) != {"path", "sha256", "size_bytes", "mode", "device", "inode", "mtime_ns", "ctime_ns"}:
        raise ValueError("identity fields differ")
    raw, actual = _read_stable(Path(identity["path"]), retain_bytes=retain_bytes)
    if actual != identity: raise ValueError("captured identity no longer names the same bytes/inode")
    return raw

def _identity_exact_c_string(identity, expected: bytes) -> bool:
    """Re-scan the same stable object bytes; self-authored evidence flags are never trusted."""
    raw, actual = _read_stable(Path(identity["path"]), retain_bytes=False)
    if actual != identity: raise ValueError("binary identity changed during compiled-knob scan")
    parent=os.open(Path(identity["path"]).parent,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0))
    try:
        fd=os.open(Path(identity["path"]).name,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)|getattr(os,"O_NONBLOCK",0),dir_fd=parent)
        try:
            overlap=b""; found=False; digest=hashlib.sha256()
            while True:
                block=os.read(fd,8<<20)
                if not block: break
                digest.update(block); scan=overlap+block
                if expected in scan: found=True
                overlap=scan[-max(1,len(expected)-1):]
            after=os.fstat(fd); named=os.stat(Path(identity["path"]).name,dir_fd=parent,follow_symlinks=False)
            fields=lambda x:(x.st_dev,x.st_ino,x.st_mode,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
            if fields(after)!=(identity["device"],identity["inode"],identity["mode"],identity["size_bytes"],identity["mtime_ns"],identity["ctime_ns"]) or digest.hexdigest()!=identity["sha256"] or (named.st_dev,named.st_ino)!=(after.st_dev,after.st_ino): raise ValueError("binary pathname changed during exact-byte scan")
            return found
        finally: os.close(fd)
    finally: os.close(parent)

def _aware(value, name):
    if not isinstance(value,str) or not value: raise ValueError(name+" missing")
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError(name+" must include timezone")
    return dt

def _check_native_log(raw, mode, receipt_metrics, window):
    if mode not in {"ppl","ppl-anchor","kld"}: raise ValueError("unsupported producer mode")
    text=raw.decode("utf-8",errors="replace")
    settings=_RUN.findall(text)
    if len(settings)!=1: raise ValueError("native scoring settings are not unique")
    n,ctx,batch,nseq=map(int,settings[0])
    if window.get("native_chunks_requested_and_reported")!=n or window.get("n_ctx")!=ctx or window.get("batch_size")!=batch or window.get("n_seq")!=nseq or window.get("ny_derived_from_native_n_ctx")!=ctx//2:
        raise ValueError("captured scoring window does not replay from native log")
    ids=list(map(int,(_PPL_CHUNKS if mode in {"ppl","ppl-anchor"} else _KLD_CHUNKS).findall(text)))
    if ids!=list(range(1,n+1)): raise ValueError("native chunk rows missing, repeated or unordered")
    expected={}
    if mode in {"ppl","ppl-anchor"}:
        rows=_PPL_FINAL.findall(text)
        if len(rows)!=1: raise ValueError("native PPL final row not unique")
        expected["Final estimate: PPL"]=(float(rows[0][0]),float(rows[0][1]))
    else:
        for label,expr in (("Mean PPL(Q)",r"^Mean PPL\(Q\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$"),
                           ("Mean PPL(base)",r"^Mean PPL\(base\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$"),
                           ("Mean PPL(Q)/PPL(base)",r"^Mean PPL\(Q\)/PPL\(base\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$"),
                           ("Mean PPL(Q)-PPL(base)",r"^Mean PPL\(Q\)-PPL\(base\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$"),
                           ("Mean ln(PPL(Q)/PPL(base))",r"^Mean ln\(PPL\(Q\)/PPL\(base\)\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$"),
                           ("Mean KLD",r"^Mean\s+KLD:\s*([^\s]+)\s*±\s*([^\s]+)\s*$")):
            rows=re.findall(expr,text,re.M)
            if len(rows)!=1: raise ValueError(f"native {label} row not unique")
            expected[label]=(float(rows[0][0]),float(rows[0][1]))
        rows=_KLD_ROW.findall(text)
        if Counter(x[0] for x in rows)!=Counter(_KLD_LABELS): raise ValueError("native KLD labels duplicated/missing")
        expected.update({f"{label} KLD":(float(value),None) for label,value in rows})
    actual={m["native_label"]:(m["value"],m.get("native_spread")) for m in receipt_metrics}
    if actual!=expected: raise ValueError("receipt metrics do not rederive from original native output")

def _verify_ppl_anchor(anchor_ref, candidate):
    """Reverify the original source-side PPL anchor that authored KLD input origin."""
    if not isinstance(anchor_ref,dict) or set(anchor_ref)!={"before","after"} or anchor_ref["before"]!=anchor_ref["after"]:
        raise ValueError("KLD lacks a stable prospective PPL-anchor receipt identity")
    ident=anchor_ref["before"]; raw=_verify_identity(ident,retain_bytes=True); a=_json(raw)
    digest=a.get("self_sha256"); unsigned={k:v for k,v in a.items() if k!="self_sha256"}
    canonical=json.dumps(unsigned,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    if not isinstance(digest,str) or hashlib.sha256(canonical).hexdigest()!=digest:
        raise ValueError("PPL-anchor producer receipt digest mismatch")
    if a.get("schema")!=SCHEMA or a.get("schema_version")!=1 or a.get("mode")!="ppl-anchor" or a.get("capture_status")!="captured" or a.get("exit_code")!=0 or a.get("refusal_reasons"):
        raise ValueError("referenced PPL-anchor receipt is not a successful native anchor capture")
    if a.get("pair_id")!=candidate.get("pair_id") or a.get("run_id")==candidate.get("run_id") or not all(isinstance(a.get(k),str) and a[k] for k in ("run_id","pair_id","arm_id")):
        raise ValueError("PPL anchor and KLD candidate do not share a distinct paired run identity")
    started=_aware(a.get("started_at_utc"),"anchor started_at_utc");ended=_aware(a.get("ended_at_utc"),"anchor ended_at_utc")
    cstart=_aware(candidate.get("started_at_utc"),"candidate started_at_utc")
    if started>ended or ended>cstart: raise ValueError("PPL anchor does not precede the KLD candidate window")
    for key in ("producer_binary","model","model_after","corpus","corpus_after","output_logits","native_log","native_scoring_window","metric_declaration","metrics","protocol_id"):
        if key not in a: raise ValueError("PPL-anchor receipt missing "+key)
    for key,after in (("model","model_after"),("corpus","corpus_after")):
        identity={k:v for k,v in a[key].items() if k in {"path","sha256","size_bytes","mode","device","inode","mtime_ns","ctime_ns"}}
        if identity!=a[after]: raise ValueError("PPL-anchor input changed during source run")
        _verify_identity(identity)
        if key=="model": a[key]=identity
    if a["model"]!=candidate.get("reference_model") or a["output_logits"]!=candidate.get("reference_logits"):
        raise ValueError("KLD reference model/logits are not the exact outputs of the cited PPL-anchor receipt")
    if a["corpus"]!=candidate.get("corpus"):
        raise ValueError("KLD anchor and candidate corpus identities differ")
    if a["native_scoring_window"]!=candidate.get("native_scoring_window") or a.get("ny")!=candidate.get("ny"):
        raise ValueError("KLD anchor and candidate scoring windows differ")
    if a["producer_binary"].get("before")!=candidate.get("producer_binary",{}).get("before") or a["producer_binary"].get("after")!=a["producer_binary"].get("before"):
        raise ValueError("KLD anchor and candidate producer binary provenance differs")
    if not a["producer_binary"].get("stable_during_capture"):
        raise ValueError("PPL-anchor producer binary was not stable")
    _verify_identity(a["producer_binary"]["before"])
    _verify_identity(a["output_logits"])
    declaration=a["metric_declaration"]
    if not isinstance(declaration,dict) or set(declaration)!={"before","after","author","issued_at_utc","metrics"} or declaration["before"]!=declaration["after"]:
        raise ValueError("PPL anchor declaration is not stable")
    decl=_json(_verify_identity(declaration["before"],retain_bytes=True))
    issued=_aware(str(declaration["issued_at_utc"]),"anchor declaration timestamp")
    if (decl.get("schema")!="epyc.vidya.qwen4exp_quality_metric_declaration.v1" or decl.get("run_id")!=a["run_id"] or decl.get("pair_id")!=a["pair_id"] or decl.get("arm_id")!=a["arm_id"] or decl.get("mode")!="ppl-anchor" or decl.get("author")!=declaration["author"] or decl.get("issued_at_utc")!=declaration["issued_at_utc"] or decl.get("protocol_id")!=a["protocol_id"] or decl.get("metrics")!=declaration["metrics"] or issued>started):
        raise ValueError("PPL-anchor declaration is not original pre-run source-authored evidence")
    labels={m.get("native_label") for m in a["metrics"]}
    if labels!={"Final estimate: PPL"} or set(declaration["metrics"])!=labels:
        raise ValueError("PPL-anchor metric declaration/rows differ")
    metric=a["metrics"][0]; md=declaration["metrics"]["Final estimate: PPL"]
    if (not all(isinstance(md.get(k),str) and md[k].strip() for k in ("unit","metric_direction","category","metric")) or
        md.get("metric_direction") not in {"higher_better","lower_better"} or md.get("category") not in {"OPTIMUM","BASELINE","CANDIDATE"} or
        any(metric.get(k)!=md.get(k) for k in ("unit","metric_direction","category","metric"))):
        raise ValueError("PPL-anchor native metric differs from its source-authored declaration")
    log=a["native_log"]
    if not isinstance(log,dict) or set(log)!={"path","sha256"}: raise ValueError("PPL-anchor original native output locator missing")
    logbytes,_=_read_stable(Path(log["path"]))
    if hashlib.sha256(logbytes).hexdigest()!=log["sha256"]: raise ValueError("PPL-anchor original producer log digest mismatch")
    _check_native_log(logbytes,"ppl-anchor",a["metrics"],a["native_scoring_window"])
    argv=a.get("argv")
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str) for x in argv): raise ValueError("PPL-anchor exact producer argv missing")
    def values(*names):return [argv[i+1] for i,x in enumerate(argv[:-1]) if x in names]
    modelarg=values("-m","--model");corpusarg=values("-f","--file");ctxarg=values("-c","--ctx-size");chunksarg=values("--chunks");basearg=values("--kl-divergence-base")
    if (Path(argv[0]).absolute()!=Path(a["producer_binary"]["before"]["path"]).absolute() or
        len(modelarg)!=1 or Path(modelarg[0]).absolute()!=Path(a["model"]["path"]).absolute() or
        len(corpusarg)!=1 or Path(corpusarg[0]).absolute()!=Path(a["corpus"]["path"]).absolute() or
        len(ctxarg)!=1 or int(ctxarg[0])!=a["native_scoring_window"].get("n_ctx") or
        len(chunksarg)!=1 or int(chunksarg[0])!=a["native_scoring_window"].get("native_chunks_requested_and_reported") or
        len(basearg)!=1 or argv.count("--kl-divergence")!=0 or
        argv.index("--kl-divergence-base")+2!=len(argv) or Path(basearg[0]).absolute()!=Path(a["output_logits"]["path"]).absolute()):
        raise ValueError("PPL-anchor producer argv does not bind model, corpus, window and newly written logits")
    return {"receipt_sha256":ident["sha256"],"receipt_path":ident["path"],"anchor_run_id":a["run_id"],"anchor_pair_id":a["pair_id"]}

def read_project(receipt_path, ClaimTuple):
    """Return ClaimTuple rows only for fully declared and reverified native metrics."""
    raw, receipt_file = _read_stable(Path(receipt_path))
    r = _json(raw)
    if not isinstance(r, dict) or r.get("schema") != SCHEMA or r.get("schema_version") != 1:
        raise ValueError("unsupported receipt schema")
    self_hash = r.get("self_sha256")
    unsigned = {k:v for k,v in r.items() if k != "self_sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    if not isinstance(self_hash, str) or hashlib.sha256(canonical).hexdigest() != self_hash:
        raise ValueError("receipt self digest mismatch")
    if r.get("capture_status") != "captured" or r.get("exit_code") != 0 or r.get("refusal_reasons"):
        raise ValueError("refused or unsuccessful capture")
    if not all(isinstance(r.get(k),str) and r[k] for k in ("run_id","pair_id","arm_id","ended_at_utc")):
        raise ValueError("run/arm identity or timestamp missing")
    ended_dt=_aware(r["ended_at_utc"],"ended_at_utc")
    started_dt=_aware(r.get("started_at_utc"),"started_at_utc")
    if started_dt > ended_dt: raise ValueError("measurement start is after end")
    base_model={k:v for k,v in r["model"].items() if k in {"path","sha256","size_bytes","mode","device","inode","mtime_ns","ctime_ns"}}
    for ident in (r["producer_binary"]["before"], r["producer_binary"]["after"], base_model, r["model_after"], r["corpus"], r["corpus_after"]): _verify_identity(ident)
    if base_model != r["model_after"] or r["corpus"] != r["corpus_after"]: raise ValueError("model/corpus changed during run")
    mode=r.get("mode")
    if mode=="kld":
        if not isinstance(r.get("reference_model"),dict) or not isinstance(r.get("reference_logits"),dict): raise ValueError("KLD requires paired reference model and logits identities")
        r["verified_anchor_origin"]=_verify_ppl_anchor(r.get("anchor_receipt"),r)
    elif mode=="ppl-anchor":
        if not isinstance(r.get("output_logits"),dict): raise ValueError("PPL anchor requires a new output logits identity")
        if r.get("reference_model") is not None or r.get("reference_logits") is not None: raise ValueError("PPL anchor cannot carry KLD reference inputs")
    elif mode=="ppl":
        if any(r.get(k) is not None for k in ("reference_model","reference_logits","output_logits")): raise ValueError("plain PPL cannot carry KLD references/output")
    else: raise ValueError("unknown producer mode")
    for key in ("reference_model", "reference_logits", "output_logits"):
        if r.get(key) is not None: _verify_identity(r[key])
    for key, after_key in (("reference_model","reference_model_after"),("reference_logits","reference_logits_after")):
        if r.get(key) != r.get(after_key): raise ValueError("KLD reference input changed during run")
        if r.get(after_key) is not None: _verify_identity(r[after_key])
    log = r.get("native_log")
    if not isinstance(log,dict) or set(log)!={"path","sha256"}: raise ValueError("native log reference malformed")
    log_bytes, log_ident = _read_stable(Path(log["path"]))
    if hashlib.sha256(log_bytes).hexdigest()!=log["sha256"]: raise ValueError("native log digest mismatch")
    _check_native_log(log_bytes,r.get("mode"),r.get("metrics",[]),r.get("native_scoring_window",{}))
    if r["producer_binary"]["before"] != r["producer_binary"]["after"] or not r["producer_binary"].get("stable_during_capture"):
        raise ValueError("producer binary did not remain stable")
    argv=r.get("argv")
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str) for x in argv): raise ValueError("exact argv missing")
    def option(*names):
        found=[argv[i+1] for i,x in enumerate(argv[:-1]) if x in names]
        if len(found)!=1: raise ValueError("required argv option missing or duplicated")
        return found[0]
    if (Path(argv[0]).absolute()!=Path(r["producer_binary"]["before"]["path"]).absolute() or
        Path(option("-m","--model")).absolute()!=Path(r["model"]["path"]).absolute() or
        Path(option("-f","--file")).absolute()!=Path(r["corpus"]["path"]).absolute() or
        int(option("-c","--ctx-size"))!=r.get("n_ctx") or
        int(option("--chunks"))!=r.get("native_scoring_window",{}).get("native_chunks_requested_and_reported")):
        raise ValueError("argv disagrees with sealed inputs/native window")
    has_kld="--kl-divergence" in argv; base_opts=[i for i,x in enumerate(argv[:-1]) if x=="--kl-divergence-base"]
    if mode=="kld":
        if argv.count("--kl-divergence")!=1 or len(base_opts)!=1 or base_opts[0]+2!=len(argv)-1 or argv[-1]!="--kl-divergence" or Path(argv[base_opts[0]+1]).absolute()!=Path(r["reference_logits"]["path"]).absolute() or Path(r["reference_model"]["path"]).absolute()==Path(r["model"]["path"]).absolute(): raise ValueError("KLD mode/reference argv is not exact and paired")
    elif mode=="ppl-anchor":
        if argv.count("--kl-divergence") or len(base_opts)!=1 or base_opts[0]+2!=len(argv) or Path(argv[base_opts[0]+1]).absolute()!=Path(r["output_logits"]["path"]).absolute(): raise ValueError("PPL anchor mode/output argv is not exact")
    elif argv.count("--kl-divergence") or base_opts: raise ValueError("plain PPL argv contains KLD mode flags")
    env=r.get("effective_environment",{})
    iqk_raw=env.get("GGML_IQK","unknown")
    iqk_state={"0":"disabled","1":"enabled"}.get(iqk_raw,"unknown")
    if iqk_state!=r.get("runtime_knobs",{}).get("GGML_IQK",{}).get("value"):
        raise ValueError("runtime IQK declaration does not match child environment")
    compiled_iqk_found=False
    for row in r["loaded_shared_objects"]:
        if row.get("identity_error"):
            raise ValueError(row["identity_error"])
        if row.get("identity_state") != "matched" or row.get("path", "").endswith(" (deleted)"):
            raise ValueError("loaded object custody unknown")
        identity = row.get("after")
        _verify_identity(identity)
        maps = row.get("mapping_observation")
        if not isinstance(maps, dict) or maps.get("sample_basis") != "distinct maps snapshots containing this path/device/inode/deleted identity" or type(maps.get("sample_count")) is not int or maps["sample_count"] < 1:
            raise ValueError("maps sample count/basis missing or invalid")
        if maps.get("deleted_mapping_observed") is not False:
            raise ValueError("deleted shared-object mappings are unknown")
        mapping_endpoints = [maps.get("first"), maps.get("latest")]
        if any(not isinstance(m, dict) or m.get("deleted") or m.get("inode") != identity["inode"] or
               m.get("device_major") != os.major(identity["device"]) or
               m.get("device_minor") != os.minor(identity["device"]) for m in mapping_endpoints):
            raise ValueError("deleted shared-object mappings are unknown") if maps.get("deleted_mapping_observed") else ValueError("maps identity not contemporaneous or mismatched")
        for m in mapping_endpoints:
            when = _aware(m.get("observed_at_utc"), "mapping observation timestamp")
            if not started_dt <= when <= ended_dt:
                raise ValueError("mapping observation outside measured process window")
        live = row.get("live_identity_observation")
        if not isinstance(live, dict) or live.get("sample_basis") != "successful stable same-inode content hash observations while child was live" or type(live.get("sample_count")) is not int or live["sample_count"] < 1:
            raise ValueError("shared object lacks stable in-process identity sample count/basis")
        if live.get("error_observed") is not False:
            raise ValueError("shared-object identity observation had an incomplete sample")
        if live.get("identity_change_observation_count") != 0 or live.get("first_changed_identity") is not None:
            raise ValueError("loaded object content identity changed during measured process")
        live_endpoints = [live.get("first"), live.get("latest")]
        if any(not isinstance(x, dict) or x.get("identity") != identity for x in live_endpoints):
            raise ValueError("shared object lacks stable in-process identity observation")
        for x in live_endpoints:
            when = _aware(x.get("observed_at_utc"), "live identity timestamp")
            if not started_dt <= when <= ended_dt:
                raise ValueError("shared-object identity was not hashed during the child window")
        if row.get("path", "").endswith(" (deleted)"):
            raise ValueError("deleted shared-object mappings are unknown")
        evidence = row.get("compiled_knob_evidence", {})
        exact=_identity_exact_c_string(identity,b"GGML_IQK\0")
        if evidence.get("required_bytes_hex")!="47474d4c5f49514b00" or evidence.get("found_exact") is not exact:
            raise ValueError("compiled IQK evidence does not rederive from hashed object bytes")
        if exact: compiled_iqk_found=True
    if not compiled_iqk_found: raise ValueError("no loaded-object compiled IQK evidence")
    runtime=r.get("runtime_knobs",{}).get("GGML_IQK",{})
    if runtime.get("value") not in {"enabled","disabled"} or runtime.get("raw_value") not in {"0","1"}:
        raise ValueError("runtime IQK state unknown")
    if type(r.get("ny")) is not int or r["ny"] < 32 or r.get("ny") != r.get("native_scoring_window",{}).get("ny_derived_from_native_n_ctx"):
        raise ValueError("Ny not proven in the supported native evaluation regime")
    decl = r.get("metric_declaration")
    if not isinstance(decl, dict) or set(decl) != {"before", "after", "author", "issued_at_utc", "metrics"}:
        raise ValueError("metric declaration envelope missing")
    if decl["before"] != decl["after"]: raise ValueError("metric declaration changed during run")
    _verify_identity(decl["before"])
    source_decl=_json(_verify_identity(decl["before"], retain_bytes=True))
    issued=_aware(str(decl["issued_at_utc"]),"declaration timestamp")
    started=started_dt
    if (source_decl.get("schema")!=DECL_SCHEMA or source_decl.get("run_id")!=r["run_id"] or
            source_decl.get("pair_id")!=r["pair_id"] or source_decl.get("arm_id")!=r["arm_id"] or
            source_decl.get("mode")!=r.get("mode") or source_decl.get("author")!=decl.get("author") or
            source_decl.get("issued_at_utc")!=decl.get("issued_at_utc") or
            source_decl.get("metrics")!=decl.get("metrics") or source_decl.get("protocol_id")!=r.get("protocol_id") or
            issued > started):
        raise ValueError("captured declaration differs from original pre-run source-authored bytes")
    metrics = r.get("metrics")
    if not isinstance(metrics, list) or not metrics: raise ValueError("native metrics missing")
    labels = [m.get("native_label") for m in metrics]
    if len(labels) != len(set(labels)) or set(labels) != set(decl["metrics"]):
        raise ValueError("native metric labels differ from source-authored declaration")
    result=[]
    for m in metrics:
        d=decl["metrics"][m["native_label"]]
        required={"unit","metric_direction","category","metric"}
        if not isinstance(d,dict) or set(d)!=required or not all(isinstance(d[k],str) and d[k].strip() for k in required):
            raise ValueError("metric declaration incomplete")
        if d["metric_direction"] not in {"higher_better","lower_better"} or d["category"] not in {"OPTIMUM","BASELINE","CANDIDATE"}:
            raise ValueError("metric direction/category outside ClaimTuple vocabulary")
        if d["metric"] != m.get("metric") or d["unit"] != m.get("unit") or d["metric_direction"] != m.get("metric_direction") or d["category"] != m.get("category"):
            raise ValueError("metric declaration does not match captured row")
        if type(m.get("value")) not in (int,float) or not math.isfinite(m["value"]): raise ValueError("nonfinite metric")
        if m.get("native_spread") is not None and (type(m["native_spread"]) not in (int,float) or not math.isfinite(m["native_spread"])): raise ValueError("nonfinite sampling spread")
        mid=f"qwen4exp-quality:{r['run_id']}:{r['arm_id']}:{m['native_label']}"
        claim=(f"Observed {m['native_label']}={m['value']} {d['unit']} from llama-perplexity; "
               f"corpus={r['corpus']['sha256']}, Ny={r['ny']}, IQK={r['runtime_knobs']['GGML_IQK']['value']}; "
               "PPL quality-evaluation scope only, not a Ny=1 serving warrant.")
        result.append(ClaimTuple(measurement_id=mid, metric=d["metric"], value=m["value"],
            date=r["ended_at_utc"], category=d["category"], claim=claim,
            metric_direction=d["metric_direction"], protocol_id=r.get("protocol_id") or "",
            reps=None, reps_basis="native aggregate; producer did not author independent run count",
            unit=d["unit"], attestation_path=str(Path(receipt_path).absolute()),
            attestation_sha256=receipt_file["sha256"], attestation_locator=f"sc54:{receipt_file['path']}#{m['native_label']}",
            attestation_present=True, attestation_verified=True, source_kind="measurement",
            extra={"native_label":m["native_label"],"native_spread":m.get("native_spread"),
                   "spread_semantics":m.get("spread_semantics"),"run_id":r["run_id"],"pair_id":r["pair_id"],
                   "arm_id":r["arm_id"],"corpus_sha256":r["corpus"]["sha256"],"ny":r["ny"],
                   "iqk_state":r["runtime_knobs"]["GGML_IQK"]["value"],"producer_binary_sha256":r["producer_binary"]["before"]["sha256"],
                   "anchor_receipt_sha256":r.get("verified_anchor_origin",{}).get("receipt_sha256"),
                   "anchor_run_id":r.get("verified_anchor_origin",{}).get("anchor_run_id")}))
    return result

#!/usr/bin/env python3
"""Bounded MF-FS-1 forced-stop diagnostics. Stdlib only; aggregate output only."""
from __future__ import annotations
import argparse, hashlib, json, os, stat, subprocess
from pathlib import Path, PurePosixPath
from typing import Any

APP_COMMIT = "62ee3ba69eed64d8f17268a18b39c131aea90760"
PRODUCER_PATH = "scripts/analysis/mf_vbs1_verify_before_stop.py"
PRODUCER_SHA256 = "7463afeab66a20c274314e5f0a85472e271dc7e12e10f052b874039d4c0b44da"
EMITTER_PATH = "src/graph/helpers.py"
EMITTER_SHA256 = "dfb2dd16f5496121f5f683aa95feb85cede82a44557549c0c1dde6c0eb364fa3"
SCHEMA = "mf_fs1_forced_stop_diagnostic.v1"
COMPANION_PATH = Path(__file__).absolute()
SCRATCH = COMPANION_PATH.parent
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_RESULT_FILES = 1000
MAX_TOTAL_INPUT_BYTES = 64 * 1024 * 1024

class InputBudgetExceeded(RuntimeError):
    """Fatal bound refusal; must never be downgraded to an invalid input row."""

def _capture_companion_bytes() -> bytes:
    fd=os.open(COMPANION_PATH,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): raise ValueError("companion source is not regular")
        chunks=[]
        while True:
            part=os.read(fd,1024*1024)
            if not part: break
            chunks.append(part)
        after=os.fstat(fd)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError("companion source changed during capture")
        raw=b"".join(chunks)
        if len(raw)!=after.st_size: raise ValueError("companion source size mismatch")
        return raw
    finally: os.close(fd)

COMPANION_SOURCE_BYTES=_capture_companion_bytes()
COMPANION_SOURCE_SHA256=hashlib.sha256(COMPANION_SOURCE_BYTES).hexdigest()

def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def _safe_read(root: Path, relative: PurePosixPath) -> bytes:
    if relative.is_absolute() or not relative.parts or any(p in ("", ".", "..") for p in relative.parts):
        raise ValueError("unsafe relative input path")
    flags_dir = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags_file = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fds: list[int] = []
    try:
        fd = os.open(root, flags_dir); fds.append(fd)
        for part in relative.parts[:-1]:
            fd = os.open(part, flags_dir, dir_fd=fd); fds.append(fd)
        fd = os.open(relative.parts[-1], flags_file, dir_fd=fd); fds.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("input is not a regular file")
        if before.st_size > MAX_INPUT_BYTES:
            raise InputBudgetExceeded("input exceeds per-file byte bound")
        chunks = []; total = 0
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block: break
            total += len(block)
            if total > MAX_INPUT_BYTES:
                raise InputBudgetExceeded("input exceeds per-file byte bound")
            chunks.append(block)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("input changed during read")
        data = b"".join(chunks)
        if len(data) != after.st_size:
            raise ValueError("input size changed during read")
        return data
    finally:
        for fd in reversed(fds): os.close(fd)

def _jsonl(raw: bytes) -> tuple[list[dict], int, int]:
    rows, malformed, nonobject = [], 0, 0
    try: text = raw.decode("utf-8")
    except UnicodeDecodeError: return rows, 1, 0
    for line in text.splitlines():
        if not line.strip(): continue
        try: value = json.loads(line)
        except (json.JSONDecodeError, ValueError): malformed += 1; continue
        if not isinstance(value, dict): nonobject += 1; continue
        rows.append(value)
    return rows, malformed, nonobject

def eligible_result(row: dict) -> tuple[bool, str]:
    if row.get("mode") != "real": return False, "not_real"
    task, arm, block, turns, preview = (row.get(k) for k in ("task", "arm", "block", "turns", "answer_preview"))
    if (not isinstance(task, str) or not task or not isinstance(arm, str) or not arm
        or not isinstance(block, int) or isinstance(block, bool)
        or not isinstance(turns, int) or isinstance(turns, bool) or turns < 0
        or not isinstance(preview, str)):
        return False, "malformed_required_fields"
    trace = row.get("trace")
    if trace is not None and not isinstance(trace, dict): return False, "malformed_trace_reference"
    if isinstance(trace, dict) and trace.get("path") is not None and not isinstance(trace.get("path"), str):
        return False, "malformed_trace_path"
    return True, "eligible"

def terminal_status(preview: str) -> str:
    cap = "[Max turns" in preview
    error = preview.strip().startswith("[ERROR") or preview.strip().startswith('"[ERROR')
    if cap and error: return "unknown_ambiguous_terminal"
    if cap: return "forced_max_turns"
    if error: return "forced_error"
    return "non_forced"

def trace_rel(result_rel: PurePosixPath, trace_path: str) -> PurePosixPath:
    part = PurePosixPath(trace_path)
    if part.is_absolute() or not part.parts or any(x in ("", ".", "..") for x in part.parts):
        raise ValueError("unsafe trace path")
    rel = result_rel.parent / part
    if any(x in ("", ".", "..") for x in rel.parts): raise ValueError("trace path escapes source directory")
    return rel

def trace_signals(rows: list[dict]) -> dict:
    turns = []
    for row in rows:
        turn = row.get("turn")
        if not isinstance(turn, int) or isinstance(turn, bool) or turn < 0:
            raise ValueError("invalid turn field")
        turns.append(turn)
    if any(b <= a for a, b in zip(turns, turns[1:])):
        raise ValueError("turn fields are not strictly increasing")
    for row in rows:
        for key in ("calls_open", "calls_file_write_safe", "prompt_has_loop_halt"):
            if key in row and row[key] is not None and not isinstance(row[key], bool):
                raise ValueError("invalid boolean signal field")
        value = row.get("repeat_count_seen")
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise ValueError("invalid repeat_count_seen field")
    if not rows: raise ValueError("empty trace")
    def tri_state(field: str, positive) -> bool | None:
        if any(positive(row.get(field)) for row in rows): return True
        if all(field in row and row[field] is not None for row in rows): return False
        return None
    nopen = sum(row.get("calls_open") is True for row in rows)
    all_open_known = all("calls_open" in row and row["calls_open"] is not None for row in rows)
    repeated_open = True if nopen >= 2 else (False if all_open_known else None)
    return {
        "trace_valid": True, "trace_turn_count": len(rows),
        "loop_halt_observed": tri_state("prompt_has_loop_halt", lambda v: v is True),
        "loop_repeat_count_observed": (True if any(isinstance(row.get("repeat_count_seen"), int)
            and not isinstance(row.get("repeat_count_seen"), bool) for row in rows) else None),
        "open_positive_turns": nopen, "repeated_open_activity": repeated_open,
        "write_signal_observed": tri_state("calls_file_write_safe", lambda v: v is True),
    }

def real_root(path: Path) -> Path:
    root = path.resolve(strict=True)
    if not root.is_dir(): raise ValueError("data root must be a directory")
    return root

def candidate_files(data_root: Path, c: dict[str, int]) -> list[Path]:
    found = []
    try: entries = sorted(data_root.iterdir(), key=lambda p: p.name)
    except OSError:
        c["source_directory_read_errors"] += 1
        return found
    for entry in entries:
        try: mode = entry.lstat().st_mode
        except OSError:
            c["source_entry_stat_errors"] += 1
            continue
        if "INVALID" in entry.name:
            c["invalid_run_directories_excluded"] += 1
            continue
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            c["non_directory_source_entries_excluded"] += 1
            continue
        result = entry / "results.jsonl"
        try: rmode = result.lstat().st_mode
        except FileNotFoundError:
            c["source_directories_without_results"] += 1
            continue
        except OSError:
            c["results_stat_errors"] += 1
            continue
        if stat.S_ISLNK(rmode) or not stat.S_ISREG(rmode):
            c["non_regular_results_excluded"] += 1
            continue
        found.append(result)
        if len(found) > MAX_RESULT_FILES:
            raise ValueError("result-file count exceeds bound")
    return found

def _ensure_private_dir(path: Path) -> None:
    if path == SCRATCH:
        path.mkdir(mode=0o700,parents=True,exist_ok=True)
    else:
        path.mkdir(mode=0o700,exist_ok=True)
    if path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path:
        raise ValueError("private snapshot directory is not a real directory")
    path.chmod(0o700)

def _snapshot_once(folder: str, filename: str, raw: bytes) -> str:
    _ensure_private_dir(SCRATCH)
    folder_path=SCRATCH/folder
    _ensure_private_dir(folder_path)
    if folder_path.parent != SCRATCH: raise ValueError("snapshot path escaped scratch")
    flags_dir=os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0)
    dirfd=os.open(folder_path,flags_dir)
    try:
        try:
            fd=os.open(filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600,dir_fd=dirfd)
        except FileExistsError:
            relative=PurePosixPath(folder)/filename
            old=_safe_read(SCRATCH,relative)
            if old != raw: raise ValueError("content-addressed snapshot bytes mismatch")
            checkfd=os.open(filename,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0),dir_fd=dirfd)
            try:
                if not stat.S_ISREG(os.fstat(checkfd).st_mode): raise ValueError("snapshot is not regular")
                os.fchmod(checkfd,0o600)
            finally: os.close(checkfd)
        else:
            with os.fdopen(fd,"wb") as handle:
                handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        os.fsync(dirfd)
        return (PurePosixPath(folder)/filename).as_posix()
    finally: os.close(dirfd)

def verify_companion_unchanged() -> None:
    if _capture_companion_bytes() != COMPANION_SOURCE_BYTES:
        raise ValueError("companion source changed after module load")

def verify_source_pins(repo_root: Path) -> dict:
    proc = subprocess.run(["git","-C",str(repo_root),"rev-parse","HEAD"],
        check=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=5)
    commit = proc.stdout.strip()
    if commit != APP_COMMIT: raise ValueError("APP HEAD differs from pinned source commit")
    pins=[]
    for path, expected in ((PRODUCER_PATH,PRODUCER_SHA256),(EMITTER_PATH,EMITTER_SHA256)):
        raw=_safe_read(repo_root,PurePosixPath(path))
        actual=hashlib.sha256(raw).hexdigest()
        if actual != expected: raise ValueError("pinned producer/emitter source hash mismatch")
        snap=_snapshot_once("source-snapshots",f"{Path(path).name}-{actual}.raw",raw)
        pins.append({"path":path,"sha256":actual,"byte_count":len(raw),"snapshot_path":snap})
    return {"commit":commit,"files":pins}

def analyze(data_root_arg: Path, repo_root_arg: Path, *, check_pins: bool = True) -> dict:
    verify_companion_unchanged()
    companion_snapshot=_snapshot_once("source-snapshots",f"{COMPANION_PATH.name}-{COMPANION_SOURCE_SHA256}.raw",
        COMPANION_SOURCE_BYTES)
    data_root, repo_root = real_root(data_root_arg), repo_root_arg.resolve(strict=True)
    source_pins=verify_source_pins(repo_root) if check_pins else {"synthetic_test_bypass":True}
    try: data_rel = data_root.relative_to(repo_root).as_posix()
    except ValueError as exc: raise ValueError("data root outside APP checkout") from exc
    if data_rel != "data/bep_sandbox": raise ValueError("data root must be exactly APP:data/bep_sandbox")
    keys = ("results_files_discovered results_files_read invalid_run_directories_excluded "
        "non_directory_source_entries_excluded source_directories_without_results source_entry_stat_errors "
        "source_directory_read_errors results_stat_errors non_regular_results_excluded "
        "results_malformed_json_lines results_nonobject_json_lines result_rows_parsed non_real_rows_excluded "
        "malformed_required_rows_excluded malformed_trace_reference_rows_excluded "
        "duplicate_result_identities_excluded real_rows_eligible missing_trace_reference trace_files_read "
        "trace_missing trace_malformed_json_lines trace_nonobject_json_lines trace_invalid_order_or_fields "
        "trace_valid trace_empty trace_invalid_or_missing forced_max_turns forced_error non_forced "
        "ambiguous_terminal_unknown other_terminal_unknown").split()
    c = {k: 0 for k in keys}; readset=[]; records=[]; seen=set()
    files = candidate_files(data_root, c); c["results_files_discovered"] = len(files)
    total_bytes=0
    for path in files:
        rel = PurePosixPath(path.relative_to(repo_root).as_posix())
        raw = _safe_read(repo_root, rel)
        snap_path=_snapshot_once("input-snapshots",hashlib.sha256(raw).hexdigest()+".raw",raw)
        total_bytes += len(raw)
        if total_bytes > MAX_TOTAL_INPUT_BYTES: raise InputBudgetExceeded("read-set exceeds total byte bound")
        rows, bad, nonobj = _jsonl(raw)
        c["results_files_read"] += 1; c["results_malformed_json_lines"] += bad
        c["results_nonobject_json_lines"] += nonobj; c["result_rows_parsed"] += len(rows)
        readset.append({"path": rel.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_count": len(raw), "snapshot_path":snap_path,
            "parsed_object_rows": len(rows), "malformed_lines": bad, "nonobject_lines": nonobj})
        for row in rows:
            ok, why = eligible_result(row)
            if not ok:
                if why == "not_real": c["non_real_rows_excluded"] += 1
                elif why.startswith("malformed_trace"): c["malformed_trace_reference_rows_excluded"] += 1
                else: c["malformed_required_rows_excluded"] += 1
                continue
            ident = (rel.as_posix(), row["task"], row["arm"], row["block"])
            if ident in seen:
                c["duplicate_result_identities_excluded"] += 1
                continue
            seen.add(ident); c["real_rows_eligible"] += 1
            terminal = terminal_status(row["answer_preview"])
            counter = {"forced_max_turns":"forced_max_turns", "forced_error":"forced_error",
                "non_forced":"non_forced", "unknown_ambiguous_terminal":"ambiguous_terminal_unknown"}[terminal]
            c[counter] += 1
            tref = row.get("trace") or {}; tpath = tref.get("path"); signals=None; trace_bad=False
            if not tpath:
                c["missing_trace_reference"] += 1; c["trace_invalid_or_missing"] += 1; trace_bad=True
            else:
                try:
                    trel=trace_rel(rel,tpath); traw=_safe_read(repo_root,trel)
                    trace_snap=_snapshot_once("input-snapshots",hashlib.sha256(traw).hexdigest()+".raw",traw)
                    total_bytes += len(traw)
                    if total_bytes > MAX_TOTAL_INPUT_BYTES: raise InputBudgetExceeded("read-set exceeds total byte bound")
                    trows,tbad,tnon=_jsonl(traw); c["trace_files_read"] += 1
                    c["trace_malformed_json_lines"] += tbad; c["trace_nonobject_json_lines"] += tnon
                    readset.append({"path":trel.as_posix(),"sha256":hashlib.sha256(traw).hexdigest(),
                        "byte_count":len(traw),"snapshot_path":trace_snap,
                        "parsed_object_rows":len(trows),"malformed_lines":tbad,"nonobject_lines":tnon})
                    if tbad or tnon: raise ValueError("malformed trace")
                    if not trows:
                        c["trace_empty"] += 1
                        raise ValueError("empty trace")
                    signals=trace_signals(trows); c["trace_valid"] += 1
                except FileNotFoundError:
                    c["trace_missing"] += 1; c["trace_invalid_or_missing"] += 1; trace_bad=True
                except InputBudgetExceeded:
                    raise
                except (OSError, ValueError):
                    c["trace_invalid_order_or_fields"] += 1; c["trace_invalid_or_missing"] += 1; trace_bad=True
            records.append({"terminal":terminal,"signals":signals,"trace_bad":trace_bad,"task":row["task"],"arm":row["arm"]})
    readset.sort(key=lambda x:x["path"])
    unique_readset={}
    for item in readset:
        old=unique_readset.get(item["path"])
        if old is not None and (old["sha256"],old["byte_count"]) != (item["sha256"],item["byte_count"]):
            raise ValueError("input bytes changed during the read-set capture")
        unique_readset[item["path"]]=item
    readset=list(unique_readset.values())
    by_task_arm={}
    signal_names=("loop_halt_observed","loop_repeat_count_observed","repeated_open_activity","write_signal_observed")
    for rec in records:
        group_key=rec["task"]+"|"+rec["arm"]
        g=by_task_arm.setdefault(group_key, {"task":rec["task"],"arm":rec["arm"],"eligible":0,
            "terminal":{"forced_max_turns":0,"forced_error":0,"non_forced":0,
                "ambiguous_terminal_unknown":0,"other_terminal_unknown":0},
            "trace_missing_or_invalid":0,"signals_by_terminal":{}})
        g["eligible"]+=1
        tk={"unknown_ambiguous_terminal":"ambiguous_terminal_unknown"}.get(rec["terminal"],rec["terminal"])
        if tk not in g["terminal"]: tk="other_terminal_unknown"
        g["terminal"][tk]+=1
        if rec["trace_bad"]: g["trace_missing_or_invalid"]+=1
        signal_bucket=g["signals_by_terminal"].setdefault(tk,{name:{"true":0,"false":0,"unknown":0} for name in signal_names})
        for name in signal_names:
            state = rec["signals"].get(name) if rec["signals"] else None
            label = "unknown" if state is None else ("true" if state else "false")
            signal_bucket[name][label]+=1
    report = {
        "schema":SCHEMA,
        "scope":{"app_commit":APP_COMMIT,"source_pins":source_pins,
            "companion_source":{"path":COMPANION_PATH.name,"sha256":COMPANION_SOURCE_SHA256,
                "byte_count":len(COMPANION_SOURCE_BYTES),"snapshot_path":companion_snapshot},
            "producer_path":PRODUCER_PATH,"producer_sha256":PRODUCER_SHA256,
            "trace_emitter_path":EMITTER_PATH,"trace_emitter_sha256":EMITTER_SHA256,
            "companion_path":COMPANION_PATH.name,
            "companion_sha256":COMPANION_SOURCE_SHA256,
            "eligible_source_glob":"data/bep_sandbox/*/results.jsonl",
            "selection":"Exclude directory names containing INVALID; retain mode=real only; follow each row trace.path.",
            "data_root":data_rel,
            "terminal_markers":{"cap":"[Max turns","error":"answer_preview starts [ERROR or quoted [ERROR"},
            "open_signal":"calls_open true on at least two strictly ordered trace turns; read activity only.",
            "metric_direction":"Forced-stop counts/shares are descriptive; lower forced-cap share is better completion, while forced-error share indicates harness/backend failure and is not model-choice evidence.",
            "unknown_semantics":"Ambiguous terminal, malformed/missing data, or unsupported cause is unknown; no causal attribution.",
            "output_privacy":"Aggregate counts only; no row IDs, raw output, prompt/code excerpts, or model/user code.",
            "signal_absence":"Signal false means the relevant field was present and false on every ordered turn; otherwise absence is unknown."},
        "eligibility":c,"by_task_arm":by_task_arm,"readset":readset,"readset_sha256":canonical_sha(readset),
        "limitations":["Trace booleans are observed signals, not successful native tool outcomes.",
            "Loop-halt injection does not establish stop causation.",
            "The current emitter digest pins the source schema, not the origin/version of legacy May 2026 input traces.",
            "The emitter stores raw_output truncated to 4,000 chars and extracted_code truncated to 2,000 chars; this analyzer ignores both.",
            "calls_open and calls_file_write_safe are substring flags, not verified tool calls or successful outcomes.",
            "Repeated open activity is not thrash or a cause.",
            "A write signal does not establish successful edit execution or edit failure.",
            "No grading rule, ClaimTuple, historical backfill, capability claim, or inference effect claim."]}
    verify_companion_unchanged()
    return report

def self_test() -> None:
    assert terminal_status("[Max turns (8) reached]")=="forced_max_turns"
    assert terminal_status("[ERROR: unavailable]")=="forced_error"
    assert terminal_status("[ERROR: overlap [Max turns]")=="unknown_ambiguous_terminal"
    assert terminal_status("done")=="non_forced"
    assert trace_signals([{"turn":1,"calls_open":False}])["repeated_open_activity"] is False
    assert trace_signals([{"turn":1}])["repeated_open_activity"] is None
    two=trace_signals([{"turn":1,"calls_open":True},{"turn":3,"calls_open":True}])
    assert two["repeated_open_activity"] and two["open_positive_turns"]==2
    mixed=trace_signals([{"turn":1,"calls_open":True},{"turn":2,"calls_file_write_safe":True,
        "prompt_has_loop_halt":True,"repeat_count_seen":2}])
    assert mixed["loop_halt_observed"] and mixed["write_signal_observed"] and mixed["repeated_open_activity"] is None
    for rows in ([{"turn":2},{"turn":1}],[{"turn":True}],[{"turn":1,"calls_open":"yes"}]):
        try: trace_signals(list(rows))
        except ValueError: pass
        else: raise AssertionError("invalid trace fields must be rejected")
    assert eligible_result({"mode":"stub"})==(False,"not_real")
    assert eligible_result({"mode":"real","task":"t","arm":"off","block":0,"turns":2,
        "answer_preview":"done","trace":{"path":"trace.jsonl"}})[0]
    try: trace_rel(PurePosixPath("results-x/results.jsonl"),"../../escape.jsonl")
    except ValueError: pass
    else: raise AssertionError("escaping trace path must be rejected")
    print("MF-FS-1 synthetic controls: PASS")

def write_private(out: Path, raw: bytes) -> Path:
    verify_companion_unchanged()
    target=out if out.is_absolute() else SCRATCH/out
    parent=target.parent.resolve(strict=True)
    try: parent.relative_to(SCRATCH)
    except ValueError as exc: raise ValueError("output must be inside private scratch") from exc
    fd=os.open(parent/target.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600)
    with os.fdopen(fd,"wb") as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    return parent/target.name

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--data-root",type=Path)
    p.add_argument("--repo-root",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test: self_test(); return 0
    if a.data_root is None or a.repo_root is None or a.out is None:
        p.error("--data-root, --repo-root, and --out are required outside --self-test")
    report=analyze(a.data_root,a.repo_root)
    raw=(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+"\n").encode()
    path=write_private(a.out,raw)
    print(json.dumps({"schema":SCHEMA,"eligible":report["eligibility"]["real_rows_eligible"],
        "forced_max_turns":report["eligibility"]["forced_max_turns"],
        "forced_error":report["eligibility"]["forced_error"],"report_path":str(path)},sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())

"""Off-host PREP unittest controls; deliberately NOT run in this environment.
When copied into the authorized ROOT carrier checkout, uses ROOT's real ClaimTuple and grade.
"""
from __future__ import annotations
import copy, hashlib, importlib.util, itertools, json, mmap, os, shutil, stat, subprocess, sys, tempfile, textwrap, time, unittest
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1].resolve(strict=True)
sys.path.insert(0,str(ROOT/"scripts"/"vidya"))
import claim_tuple as ct
import adapters.qwen4exp_quality as quality_adapter
from adapters.qwen4exp_quality import SOURCE_KIND, _reader, native_rows
ClaimTuple, grade = ct.ClaimTuple, ct.grade
_reader_module = _reader()
DECL_SCHEMA, SCHEMA = _reader_module.DECL_SCHEMA, _reader_module.SCHEMA
_read_stable, read_project = _reader_module._read_stable, _reader_module.read_project

START="2026-10-08T00:00:30Z"; END="2026-10-08T00:01:30Z"
PPL_LOG=("calculating perplexity over 1 chunks, n_ctx=64, batch_size=64, n_seq=1\n"
         "[1]2.5,\nFinal estimate: PPL = 2.5 +/- 0.1\n")
KLD_LABELS=("Maximum","99.9%","99.0%","95.0%","90.0%","Median","10.0%","5.0%","1.0%","0.1%","Minimum")
KLD_MEANS=("Mean PPL(Q)","Mean PPL(base)","Mean PPL(Q)/PPL(base)","Mean PPL(Q)-PPL(base)","Mean ln(PPL(Q)/PPL(base))","Mean KLD")
def identity(path): return _read_stable(Path(path),retain_bytes=False)[1]
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def write_receipt(path,record,allow_nan=False):
    record=copy.deepcopy(record);record.pop("self_sha256",None)
    unsigned=json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=allow_nan).encode()
    record["self_sha256"]=hashlib.sha256(unsigned).hexdigest()
    path.write_text(json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=allow_nan))
    return record

def make_fixture(testcase,mode="ppl",large_model=False):
    temp=Path(tempfile.mkdtemp(prefix="sc54-independent-case-"));testcase.addCleanup(shutil.rmtree,temp,ignore_errors=True)
    binary=temp/"producer-fixture";binary.write_bytes(b"synthetic executable identity")
    model=temp/"candidate.gguf"
    if large_model:
        with model.open("wb") as f:f.truncate((128<<20)+1)
    else:model.write_bytes(b"candidate model fixture")
    corpus=temp/"fixed-corpus.txt";corpus.write_bytes(b"fixed corpus fixture")
    so=temp/"libggml-cpu.so";so.write_bytes(b"fixture-object-prefix\0GGML_IQK\0fixture-object-suffix")
    argv=[str(binary),"-m",str(model),"-f",str(corpus),"-c","64","--chunks","1"]
    refs={"reference_model":None,"reference_model_after":None,"reference_logits":None,"reference_logits_after":None,"output_logits":None}
    if mode=="kld":
        ref_model=temp/"anchor.gguf";ref_model.write_bytes(b"anchor model fixture")
        ref_logits=temp/"anchor.logits";ref_logits.write_bytes(b"anchor logits fixture")
        refs.update(reference_model=identity(ref_model),reference_model_after=identity(ref_model),reference_logits=identity(ref_logits),reference_logits_after=identity(ref_logits))
        argv += ["--kl-divergence-base",str(ref_logits),"--kl-divergence"]
    elif mode=="ppl-anchor":
        output=temp/"new-anchor.logits";output.write_bytes(b"new anchor logits fixture")
        refs["output_logits"]=identity(output);argv += ["--kl-divergence-base",str(output)]
    if mode=="kld":
        log=("computing over 1 chunks, n_ctx=64, batch_size=64, n_seq=1\n1 2.4 ± 0.1\n"+
             "".join(f"{name}: 2.4 ± 0.1\n" for name in KLD_MEANS)+
             "".join(f"{name} KLD: 2.4\n" for name in KLD_LABELS))
        labels=list(KLD_MEANS)+[f"{name} KLD" for name in KLD_LABELS]
        units={"Mean PPL(Q)":"perplexity","Mean PPL(base)":"perplexity","Mean PPL(Q)/PPL(base)":"dimensionless","Mean PPL(Q)-PPL(base)":"perplexity","Mean ln(PPL(Q)/PPL(base))":"dimensionless","Mean KLD":"nats",**{f"{x} KLD":"nats" for x in KLD_LABELS}}
        metricrows=[]
        for name in labels:
            percentile=name.endswith(" KLD") and name!="Mean KLD"
            metricrows.append({"native_label":name,"value":2.4,"unit":units[name],"native_direction":"unknown","native_spread":None if percentile else .1,"spread_semantics":"corpus sampling uncertainty; not run-to-run noise" if not percentile else "not emitted","metric":name.lower().replace(" ","_"),"metric_direction":"lower_better","category":"CANDIDATE"})
    else:
        log=PPL_LOG;labels=["Final estimate: PPL"]
        metricrows=[{"native_label":labels[0],"value":2.5,"unit":"perplexity","native_direction":"unknown","native_spread":.1,"spread_semantics":"corpus sampling uncertainty; not run-to-run noise","metric":"perplexity","metric_direction":"lower_better","category":"CANDIDATE"}]
        units={labels[0]:"perplexity"}
    logpath=temp/"native.log";logpath.write_text(log)
    decl={"schema":DECL_SCHEMA,"run_id":"case-run","pair_id":"case-pair","arm_id":"candidate","mode":mode,"author":"synthetic pre-run source author","issued_at_utc":"2026-10-08T00:00:00Z","protocol_id":"synthetic-offhost-control","metrics":{name:{"unit":units[name],"metric_direction":"lower_better","category":"CANDIDATE","metric":row["metric"]} for name,row in zip(labels,metricrows)}}
    declpath=temp/"metric-declaration.json";declpath.write_bytes(canonical(decl))
    bi=identity(binary);mi=identity(model);ci=identity(corpus);si=identity(so);di=identity(declpath);sost=os.stat(so)
    rec={"schema":SCHEMA,"schema_version":1,"run_id":"case-run","pair_id":"case-pair","arm_id":"candidate","mode":mode,"argv":argv,"n_ctx":64,"chunks_arg":"1","effective_environment":{"GGML_IQK":"1"},"capture_status":"captured","exit_code":0,"refusal_reasons":[],"started_at_utc":START,"ended_at_utc":END,"producer_binary":{"before":bi,"after":bi,"stable_during_capture":True},"model":{**mi,"model_name":"synthetic-model","quant":"Q4"},"model_after":mi,"corpus":ci,"corpus_after":ci,"native_log":{"path":str(logpath),"sha256":hashlib.sha256(logpath.read_bytes()).hexdigest()},**refs,"loaded_shared_objects":[{"path":str(so),"identity_state":"matched","after":si,"mapping_observation":{"first":{"deleted":False,"inode":sost.st_ino,"device_major":os.major(sost.st_dev),"device_minor":os.minor(sost.st_dev),"observed_at_utc":"2026-10-08T00:01:00Z"},"latest":{"deleted":False,"inode":sost.st_ino,"device_major":os.major(sost.st_dev),"device_minor":os.minor(sost.st_dev),"observed_at_utc":"2026-10-08T00:01:00Z"},"sample_count":1,"sample_basis":"distinct maps snapshots containing this path/device/inode/deleted identity","deleted_mapping_observed":False},"live_identity_observation":{"first":{"identity":si,"observed_at_utc":"2026-10-08T00:01:00Z"},"latest":{"identity":si,"observed_at_utc":"2026-10-08T00:01:00Z"},"sample_count":1,"sample_basis":"successful stable same-inode content hash observations while child was live","identity_change_observation_count":0,"first_changed_identity":None,"error_observed":False},"compiled_knob_evidence":{"required_bytes_hex":"47474d4c5f49514b00","found_exact":True}},],"runtime_knobs":{"GGML_IQK":{"value":"enabled","raw_value":"1"}},"ny":32,"native_scoring_window":{"native_chunks_requested_and_reported":1,"scored_chunk_ids":[1],"scored_chunk_range":[1,1],"n_ctx":64,"batch_size":64,"n_seq":1,"ny_rule":"llama-perplexity all-logits implementation uses n_ctx/2","ny_derived_from_native_n_ctx":32},"metric_declaration":{"before":di,"after":di,"author":decl["author"],"issued_at_utc":decl["issued_at_utc"],"metrics":decl["metrics"]},"protocol_id":decl["protocol_id"],"metrics":metricrows}
    if mode=="kld":
        anchor_log=temp/"anchor-native.log";anchor_log.write_text(PPL_LOG)
        anchor_label="Final estimate: PPL"
        anchor_metrics=[{"native_label":anchor_label,"value":2.5,"unit":"perplexity","native_direction":"unknown","native_spread":.1,"spread_semantics":"corpus sampling uncertainty; not run-to-run noise","metric":"perplexity","metric_direction":"lower_better","category":"CANDIDATE"}]
        anchor_decl={"schema":DECL_SCHEMA,"run_id":"case-anchor-run","pair_id":"case-pair","arm_id":"anchor","mode":"ppl-anchor","author":"synthetic pre-run anchor author","issued_at_utc":"2026-10-08T00:00:00Z","protocol_id":"synthetic-offhost-control","metrics":{anchor_label:{"unit":"perplexity","metric_direction":"lower_better","category":"CANDIDATE","metric":"perplexity"}}}
        anchor_decl_path=temp/"anchor-declaration.json";anchor_decl_path.write_bytes(canonical(anchor_decl));adi=identity(anchor_decl_path)
        anchor={"schema":SCHEMA,"schema_version":1,"run_id":"case-anchor-run","pair_id":"case-pair","arm_id":"anchor","mode":"ppl-anchor","capture_status":"captured","exit_code":0,"refusal_reasons":[],"started_at_utc":"2026-10-08T00:00:05Z","ended_at_utc":"2026-10-08T00:00:25Z","producer_binary":{"before":bi,"after":bi,"stable_during_capture":True},"argv":[bi["path"],"-m",refs["reference_model"]["path"],"-f",ci["path"],"-c","64","--chunks","1","--kl-divergence-base",refs["reference_logits"]["path"]],"model":{**refs["reference_model"],"model_name":"synthetic-anchor","quant":"Q4"},"model_after":refs["reference_model"],"corpus":ci,"corpus_after":ci,"output_logits":refs["reference_logits"],"native_log":{"path":str(anchor_log),"sha256":hashlib.sha256(anchor_log.read_bytes()).hexdigest()},"native_scoring_window":{"native_chunks_requested_and_reported":1,"scored_chunk_ids":[1],"scored_chunk_range":[1,1],"n_ctx":64,"batch_size":64,"n_seq":1,"ny_rule":"llama-perplexity all-logits implementation uses n_ctx/2","ny_derived_from_native_n_ctx":32},"ny":32,"metric_declaration":{"before":adi,"after":adi,"author":anchor_decl["author"],"issued_at_utc":anchor_decl["issued_at_utc"],"metrics":anchor_decl["metrics"]},"metrics":anchor_metrics,"protocol_id":anchor_decl["protocol_id"]}
        anchor_path=temp/"anchor-receipt.json";anchor_record=write_receipt(anchor_path,anchor);ai=identity(anchor_path);rec["anchor_receipt"]={"before":ai,"after":ai}
    else:rec["anchor_receipt"]=None
    return temp,rec,so,declpath

class SC54ProjectionControls(unittest.TestCase):
    def accept(self,mode="ppl",large=False):
        d,r,_,_=make_fixture(self,mode,large);receipt=d/"receipt.json";write_receipt(receipt,r)
        rows=read_project(receipt,ClaimTuple)
        self.assertTrue(rows);self.assertTrue(all(isinstance(x,ClaimTuple) for x in rows))
        for row in rows:
            result=grade(row);self.assertIsInstance(result,tuple);self.assertEqual(len(result),3)
        return d,r,rows
    def refuse_reason(self,record,d,expected):
        receipt=d/"negative.json";write_receipt(receipt,record)
        with self.assertRaises((ValueError,OSError,KeyError,TypeError)) as ctx:read_project(receipt,ClaimTuple)
        self.assertIn(expected,str(ctx.exception))
    def test_plain_ppl_projection(self):
        _,_,rows=self.accept();self.assertEqual(len(rows),1)
    def test_streamed_large_model_projection(self):
        _,_,rows=self.accept(large=True);self.assertEqual(len(rows),1)
    def test_valid_paired_kld_projects_all_native_rows(self):
        _,_,rows=self.accept("kld");self.assertEqual(len(rows),17)
        labels={x.extra["native_label"] for x in rows};self.assertEqual(len(labels),17)
    def test_paired_native_ppl_anchor_receipt_binds_kld_origin(self):
        d,r,rows=self.accept("kld");self.assertEqual(len(rows),17);self.assertEqual(r["anchor_receipt"]["before"],r["anchor_receipt"]["after"])
        self.assertTrue(all(x.extra["anchor_receipt_sha256"]==r["anchor_receipt"]["before"]["sha256"] for x in rows))
        self.assertTrue(all(x.extra["anchor_run_id"]=="case-anchor-run" for x in rows))
    def test_valid_anchor_ppl_output_logits(self):
        _,_,rows=self.accept("ppl-anchor");self.assertEqual(len(rows),1)
    def test_writer_retains_only_bounded_endpoints_for_50000_maps_samples(self):
        writer_path = ROOT / "scripts" / "vidya" / "qwen4exp_quality_capture.py"
        spec = importlib.util.spec_from_file_location("_sc54_writer_monitor_control", writer_path)
        writer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(writer)
        count = 50000
        path = "/synthetic/libggml-cpu.so"
        maprow = {"path": path, "deleted": False, "device_major": 8,
                  "device_minor": 1, "inode": 77, "observed_at_utc": START}
        ident = {"path": path, "sha256": "a" * 64, "size_bytes": 12,
                 "mode": 0o100644, "device": os.makedev(8, 1), "inode": 77,
                 "mtime_ns": 1, "ctime_ns": 2}
        writer.maps_shared_objects = lambda _pid: [maprow, dict(maprow)]
        writer.file_identity = lambda _path: ident
        ticks = itertools.count(0, 1_000_000_001)
        class FakeProcess:
            pid = 123
            def poll(self): return 0 if stop.calls >= count else None
        class FakeStop:
            calls = 0
            def is_set(self): return self.calls >= count
            def wait(self, _seconds): self.calls += 1
        stop = FakeStop()
        seen = {}
        writer.monitor_maps(FakeProcess(), seen, stop, monotonic_ns=lambda: next(ticks))
        self.assertEqual(len(seen), 1)
        slot = next(iter(seen.values()))
        self.assertEqual(slot["mapping_sample_count"], count)
        self.assertEqual(slot["live_hash_sample_count"], count)
        self.assertEqual(slot["mapping_first"], slot["mapping_latest"])
        self.assertEqual(slot["live_first"]["identity"], slot["live_latest"]["identity"])
        self.assertNotIn("observations", slot)
        self.assertNotIn("live_identity_observations", slot)
        self.assertLess(len(json.dumps(slot)), 4096)

        # A maps snapshot or hash may complete after the process exits. Neither is live evidence.
        class RaceProcess:
            pid = 123
            dead = False
            def poll(self): return 0 if self.dead else None
        class RaceStop:
            def is_set(self): return False
            def wait(self, _seconds): raise AssertionError("terminated sample must exit")
        for phase in ("maps", "hash"):
            proc = RaceProcess()
            def maps(_pid):
                if phase == "maps": proc.dead = True
                return [maprow]
            def identity(_path):
                proc.dead = True
                return ident
            writer.maps_shared_objects = maps
            writer.file_identity = identity
            race_seen = {}
            writer.monitor_maps(proc, race_seen, RaceStop(), monotonic_ns=lambda: 0)
            if phase == "maps":
                self.assertEqual(race_seen, {})
            else:
                race_slot = next(iter(race_seen.values()))
                self.assertEqual(race_slot["mapping_sample_count"], 1)
                self.assertEqual(race_slot["live_hash_sample_count"], 0)
                self.assertIsNone(race_slot["live_first"])
                self.assertIsNone(race_slot["live_latest"])

        # Preserve earlier successful hashes and sticky live errors when the final hash is interrupted.
        for live_error in (False, True):
            proc = RaceProcess()
            hash_calls = [0]
            class CountStop(RaceStop):
                def wait(self, _seconds): pass
            writer.maps_shared_objects = lambda _pid: [maprow]
            def completing_identity(_path):
                hash_calls[0] += 1
                if live_error and hash_calls[0] == 2:
                    raise OSError("synthetic live hash error")
                if hash_calls[0] == 4:
                    proc.dead = True
                    raise OSError("synthetic interrupted final hash")
                return ident
            writer.file_identity = completing_identity
            retained = {}
            ticks = itertools.count(0, 1_000_000_001)
            writer.monitor_maps(proc, retained, CountStop(), monotonic_ns=lambda: next(ticks))
            saved = next(iter(retained.values()))
            self.assertEqual(saved["live_hash_sample_count"], 2 if live_error else 3)
            self.assertEqual(saved["live_first"]["identity"], ident)
            self.assertEqual(saved["live_latest"]["identity"], ident)
            self.assertEqual(saved["live_identity_error"], "OSError: synthetic live hash error" if live_error else None)

    def test_writer_latches_identity_change_for_reader_refusal(self):
        writer_path = ROOT / "scripts" / "vidya" / "qwen4exp_quality_capture.py"
        spec = importlib.util.spec_from_file_location("_sc54_writer_change_control", writer_path)
        writer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(writer)
        path = "/synthetic/libggml-cpu.so"
        maprow = {"path": path, "deleted": False, "device_major": 8,
                  "device_minor": 1, "inode": 77, "observed_at_utc": START}
        base = {"path": path, "sha256": "a" * 64, "size_bytes": 12,
                "mode": 0o100644, "device": os.makedev(8, 1), "inode": 77,
                "mtime_ns": 1, "ctime_ns": 2}
        variants = iter((base, {**base, "sha256": "b" * 64}, base))
        writer.maps_shared_objects = lambda _pid: [maprow]
        writer.file_identity = lambda _path: next(variants)
        ticks = itertools.count(0, 1_000_000_001)
        class FakeStop:
            calls = 0
            def is_set(self): return self.calls >= 3
            def wait(self, _seconds): self.calls += 1
        stop = FakeStop()
        class FakeProcess:
            pid = 123
            def poll(self): return 0 if stop.calls >= 3 else None
        seen = {}
        writer.monitor_maps(FakeProcess(), seen, stop, monotonic_ns=lambda: next(ticks))
        slot = next(iter(seen.values()))
        self.assertEqual(slot["live_hash_sample_count"], 3)
        self.assertEqual(slot["identity_change_observation_count"], 1)
        self.assertEqual(slot["first_changed_identity"]["sha256"], "b" * 64)

    def test_long_window_monitor_receipt_is_bounded_and_counts_exact_samples(self):
        d, r, _, _ = make_fixture(self)
        row = r["loaded_shared_objects"][0]
        row["mapping_observation"]["sample_count"] = 50000
        row["live_identity_observation"]["sample_count"] = 50000
        receipt = d / "long-window.quality.json"
        write_receipt(receipt, r)
        raw = receipt.read_bytes()
        self.assertLess(len(raw), 65536)
        self.assertEqual(len(read_project(receipt, ClaimTuple)), 1)
        self.assertEqual(row["mapping_observation"]["sample_count"], 50000)
        self.assertEqual(row["live_identity_observation"]["sample_count"], 50000)

    def test_live_identity_change_is_preserved_and_refused(self):
        d, r, _, _ = make_fixture(self)
        row = r["loaded_shared_objects"][0]
        changed = copy.deepcopy(row["after"])
        changed["sha256"] = "f" * 64
        row["live_identity_observation"]["identity_change_observation_count"] = 1
        row["live_identity_observation"]["first_changed_identity"] = changed
        row["identity_state"] = "unknown"
        row["identity_error"] = "loaded object content identity changed during measured process"
        self.refuse_reason(r, d, "loaded object content identity changed during measured process")

    def test_forged_compiled_knob_state_refuses(self):
        d,r,so,_=make_fixture(self);so.write_bytes(b"object");badso=identity(so);bad=copy.deepcopy(r);row=bad["loaded_shared_objects"][0];row["after"]=badso;row["live_identity_observation"]["first"]={"identity":badso,"observed_at_utc":"2026-10-08T00:01:00Z"};row["live_identity_observation"]["latest"]={"identity":badso,"observed_at_utc":"2026-10-08T00:01:00Z"};row["mapping_observation"]["first"]["inode"]=badso["inode"];row["mapping_observation"]["latest"]["inode"]=badso["inode"];self.refuse_reason(bad,d,"compiled IQK evidence does not rederive")
    def test_compiled_knob_near_match_refuses(self):
        d,r,so,_=make_fixture(self);so.write_bytes(b"GGML_IQKfoo\0");badso=identity(so);bad=copy.deepcopy(r);row=bad["loaded_shared_objects"][0];row["after"]=badso;row["live_identity_observation"]["first"]={"identity":badso,"observed_at_utc":"2026-10-08T00:01:00Z"};row["live_identity_observation"]["latest"]={"identity":badso,"observed_at_utc":"2026-10-08T00:01:00Z"};row["mapping_observation"]["first"]["inode"]=badso["inode"];row["mapping_observation"]["latest"]["inode"]=badso["inode"];self.refuse_reason(bad,d,"compiled IQK evidence does not rederive")
    def test_missing_maps_refuses(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["loaded_shared_objects"][0].pop("mapping_observation");self.refuse_reason(bad,d,"maps sample count/basis missing or invalid")
    def test_deleted_maps_refuse(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["loaded_shared_objects"][0]["mapping_observation"]["deleted_mapping_observed"]=True;bad["loaded_shared_objects"][0]["mapping_observation"]["first"]["deleted"]=True;bad["loaded_shared_objects"][0]["mapping_observation"]["latest"]["deleted"]=True;self.refuse_reason(bad,d,"deleted shared-object mappings are unknown")
    def test_wrong_maps_inode_refuses(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["loaded_shared_objects"][0]["mapping_observation"]["first"]["inode"]+=1;self.refuse_reason(bad,d,"maps identity not contemporaneous or mismatched")
    def test_missing_live_library_hash_refuses(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["loaded_shared_objects"][0].pop("live_identity_observation");self.refuse_reason(bad,d,"shared object lacks stable in-process identity sample count/basis")
    def test_mapping_timestamp_outside_window_refuses(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["loaded_shared_objects"][0]["mapping_observation"]["first"]["observed_at_utc"]="2026-10-08T00:02:00Z";self.refuse_reason(bad,d,"mapping observation outside measured process window")
    def test_live_hash_timestamp_outside_window_refuses(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["loaded_shared_objects"][0]["live_identity_observation"]["first"]["observed_at_utc"]="2026-10-08T00:02:00Z";self.refuse_reason(bad,d,"shared-object identity was not hashed during the child window")
    def test_timezone_and_order_refused(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["started_at_utc"]="2026-10-08T00:00:30";self.refuse_reason(bad,d,"started_at_utc must include timezone")
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["started_at_utc"]="2026-10-08T00:02:00Z";self.refuse_reason(bad,d,"measurement start is after end")
    def test_kld_missing_reference_model_refuses(self):
        d,r,_,_=make_fixture(self,"kld");bad=copy.deepcopy(r);bad["reference_model"]=None;bad["reference_model_after"]=None;self.refuse_reason(bad,d,"KLD requires paired reference model and logits identities")
    def test_kld_missing_anchor_provenance_refuses(self):
        d,r,_,_=make_fixture(self,"kld");bad=copy.deepcopy(r);bad["anchor_receipt"]=None;self.refuse_reason(bad,d,"KLD lacks a stable prospective PPL-anchor receipt identity")
    def test_kld_mismatched_anchor_logits_refuse(self):
        d,r,_,_=make_fixture(self,"kld");bad=copy.deepcopy(r);wrong=d/"unpaired.logits";wrong.write_bytes(b"different prospective logits");bad["reference_logits"]=identity(wrong);bad["reference_logits_after"]=identity(wrong);bad["argv"][bad["argv"].index("--kl-divergence-base")+1]=str(wrong);self.refuse_reason(bad,d,"KLD reference model/logits are not the exact outputs")
    def test_kld_mismatched_anchor_model_refuses(self):
        d,r,_,_=make_fixture(self,"kld");bad=copy.deepcopy(r);wrong=d/"unpaired.gguf";wrong.write_bytes(b"different anchor model");bad["reference_model"]=identity(wrong);bad["reference_model_after"]=identity(wrong);self.refuse_reason(bad,d,"KLD reference model/logits are not the exact outputs")
    def test_kld_wrong_base_argv_refuses(self):
        d,r,_,_=make_fixture(self,"kld");bad=copy.deepcopy(r);bad["argv"][bad["argv"].index("--kl-divergence-base")+1]=str(d/"wrong.logits");self.refuse_reason(bad,d,"KLD mode/reference argv is not exact and paired")
    def test_plain_ppl_with_kld_flag_refuses(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["argv"].append("--kl-divergence");self.refuse_reason(bad,d,"plain PPL argv contains KLD mode flags")
    def test_kld_trailing_argument_after_mode_flag_refuses(self):
        d,r,_,_=make_fixture(self,"kld");bad=copy.deepcopy(r);bad["argv"].append("--help");self.refuse_reason(bad,d,"KLD mode/reference argv is not exact and paired")
    def test_duplicate_json_receipt_key_refuses(self):
        d,r,_,_=make_fixture(self);path=d/"duplicate.json";write_receipt(path,r);raw=path.read_text();path.write_text(raw[:-1]+',"mode":"ppl"}');
        with self.assertRaises(ValueError) as ctx:read_project(path,ClaimTuple)
        self.assertIn("duplicate JSON key",str(ctx.exception))
    def test_duplicate_json_declaration_key_refuses(self):
        d,r,_,declp=make_fixture(self);raw=declp.read_text();declp.write_text(raw[:-1]+',"mode":"ppl"}');di=identity(declp);bad=copy.deepcopy(r);bad["metric_declaration"]["before"]=di;bad["metric_declaration"]["after"]=di;self.refuse_reason(bad,d,"duplicate JSON key")
    def test_changed_corpus_bytes_refuse(self):
        d,r,_,_=make_fixture(self);Path(r["corpus"]["path"]).write_bytes(b"changed");self.refuse_reason(copy.deepcopy(r),d,"captured identity no longer names the same bytes/inode")
    def test_unknown_direction_refuses(self):
        d,r,_,declp=make_fixture(self);bad=copy.deepcopy(r);decl=json.loads(declp.read_text());label=bad["metrics"][0]["native_label"];decl["metrics"][label]["metric_direction"]="unknown";declp.write_bytes(canonical(decl));did=identity(declp);bad["metric_declaration"]["before"]=did;bad["metric_declaration"]["after"]=did;bad["metric_declaration"]["metrics"]=decl["metrics"];bad["metrics"][0]["metric_direction"]="unknown";self.refuse_reason(bad,d,"metric direction/category outside ClaimTuple vocabulary")
    def test_missing_unit_refuses(self):
        d,r,_,declp=make_fixture(self);bad=copy.deepcopy(r);decl=json.loads(declp.read_text());label=bad["metrics"][0]["native_label"];decl["metrics"][label]["unit"]="";declp.write_bytes(canonical(decl));did=identity(declp);bad["metric_declaration"]["before"]=did;bad["metric_declaration"]["after"]=did;bad["metric_declaration"]["metrics"]=decl["metrics"];bad["metrics"][0]["unit"]="";self.refuse_reason(bad,d,"metric declaration incomplete")
    def test_nonfinite_value_refuses(self):
        d,r,_,_=make_fixture(self);bad=copy.deepcopy(r);bad["metrics"][0]["value"]=float("inf");p=d/"nonfinite.json";write_receipt(p,bad,allow_nan=True)
        with self.assertRaises(ValueError) as ctx:read_project(p,ClaimTuple)
        self.assertIn("non-finite JSON constant: Infinity",str(ctx.exception))
    def test_mutated_library_digest_refuses(self):
        d,r,so,_=make_fixture(self);so.write_bytes(b"mutated");self.refuse_reason(copy.deepcopy(r),d,"captured identity no longer names the same bytes/inode")

class SC54PinnedReaderAndImmutableOutputControls(unittest.TestCase):
    def _writer(self):
        path = ROOT / "scripts" / "vidya" / "qwen4exp_quality_capture.py"
        spec = importlib.util.spec_from_file_location("_sc54_output_control_writer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_reader_compiles_fd_verified_bytes_after_path_replacement(self):
        reader_name = "_epyc_qwen4exp_quality_reader_v1"
        prior = sys.modules.pop(reader_name, None)
        old_path, old_pin = quality_adapter.READER_PATH, quality_adapter.READER_SHA256
        old_read = quality_adapter._read_pinned_source
        temp = Path(tempfile.mkdtemp(prefix="sc54-reader-fd-race-control-"))
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        source = old_path.read_bytes()
        digest = hashlib.sha256(source).hexdigest()
        path = temp / "strict_reader.py"
        path.write_bytes(source)
        quality_adapter.READER_PATH = path
        quality_adapter.READER_SHA256 = digest
        def replace_after_verified_read():
            verified = old_read()
            path.write_bytes(verified[0] + b"\n# replacement after verified FD read\n")
            return verified
        quality_adapter._read_pinned_source = replace_after_verified_read
        try:
            module = quality_adapter._reader()
            self.assertEqual(module.__sc54_source_bytes__, source)
            self.assertEqual(module.__sc54_source_sha256__, digest)
            self.assertEqual(module.read_project.__code__.co_filename, str(path))
            self.assertNotEqual(path.read_bytes(), module.__sc54_source_bytes__)
        finally:
            quality_adapter.READER_PATH = old_path
            quality_adapter.READER_SHA256 = old_pin
            quality_adapter._read_pinned_source = old_read
            sys.modules.pop(reader_name, None)
            if prior is not None:
                sys.modules[reader_name] = prior

    def test_cached_reader_module_must_match_pinned_identity_and_functions(self):
        module = _reader()
        previous_hash = module.__sc54_source_sha256__
        previous_function = module.read_project
        previous_schema = module.SCHEMA
        try:
            module.__sc54_source_sha256__ = "0" * 64
            with self.assertRaisesRegex(Exception, "cached SC54 reader module"):
                quality_adapter._reader()
            module.__sc54_source_sha256__ = previous_hash
            module.read_project = lambda *_args: ()
            with self.assertRaisesRegex(Exception, "cached SC54 reader module"):
                quality_adapter._reader()
            module.read_project = previous_function
            module.SCHEMA = "tampered schema"
            with self.assertRaisesRegex(Exception, "cached SC54 reader module"):
                quality_adapter._reader()
        finally:
            module.__sc54_source_sha256__ = previous_hash
            module.read_project = previous_function
            module.SCHEMA = previous_schema

    def test_pinned_reader_refuses_final_symlink(self):
        old_path, old_pin = quality_adapter.READER_PATH, quality_adapter.READER_SHA256
        temp = Path(tempfile.mkdtemp(prefix="sc54-reader-symlink-control-"))
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        target = temp / "reader-target.py"
        target.write_bytes(old_path.read_bytes())
        link = temp / "reader.py"
        link.symlink_to(target)
        quality_adapter.READER_PATH = link
        quality_adapter.READER_SHA256 = hashlib.sha256(target.read_bytes()).hexdigest()
        try:
            with self.assertRaises(Exception):
                quality_adapter._read_pinned_source()
        finally:
            quality_adapter.READER_PATH = old_path
            quality_adapter.READER_SHA256 = old_pin

    def test_run_and_arm_ids_cannot_escape_receipt_directory(self):
        writer = self._writer()
        good_log, good_receipt = writer.output_paths(Path("/tmp/sc54-control"), "run-1", "arm_A")
        self.assertEqual(good_log.name, "run-1.arm_A.native.log")
        self.assertEqual(good_receipt.name, "run-1.arm_A.quality.json")
        for bad in ("../escape", "a/b", ".", "", ".."):
            with self.assertRaises(ValueError):
                writer.output_paths(Path("/tmp/sc54-control"), bad, "arm")

    def test_output_preflight_refuses_existing_receipt_or_symlink_before_child(self):
        writer = self._writer()
        temp = Path(tempfile.mkdtemp(prefix="sc54-output-preflight-control-"))
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        log, receipt = writer.output_paths(temp, "run", "arm")
        receipt.write_bytes(b"original receipt")
        with self.assertRaises(FileExistsError):
            writer.refuse_existing_outputs(log, receipt)
        self.assertFalse(log.exists())
        self.assertEqual(receipt.read_bytes(), b"original receipt")
        receipt.unlink()
        target = temp / "target"
        target.write_bytes(b"protected")
        receipt.symlink_to(target)
        with self.assertRaises(FileExistsError):
            writer.refuse_existing_outputs(log, receipt)
        self.assertFalse(log.exists())
        self.assertTrue(receipt.is_symlink())
        self.assertEqual(target.read_bytes(), b"protected")

    def test_receipt_publish_refuses_existing_regular_file_and_symlink(self):
        writer = self._writer()
        temp = Path(tempfile.mkdtemp(prefix="sc54-receipt-immutable-control-"))
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        existing = temp / "existing.json"
        existing.write_bytes(b"original receipt bytes")
        with self.assertRaises(FileExistsError):
            writer.atomic_json(existing, {"schema": "synthetic"})
        self.assertEqual(existing.read_bytes(), b"original receipt bytes")
        target = temp / "protected.json"
        target.write_bytes(b"protected target")
        link = temp / "receipt-link.json"
        link.symlink_to(target)
        with self.assertRaises(OSError):
            writer.atomic_json(link, {"schema": "synthetic"})
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_bytes(), b"protected target")

    def test_native_log_create_refuses_existing_file_and_symlink(self):
        writer = self._writer()
        temp = Path(tempfile.mkdtemp(prefix="sc54-native-log-exclusive-control-"))
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        existing = temp / "native.log"
        existing.write_bytes(b"original log bytes")
        with self.assertRaises(FileExistsError):
            writer.open_native_log(existing)
        self.assertEqual(existing.read_bytes(), b"original log bytes")
        target = temp / "protected.log"
        target.write_bytes(b"protected log")
        link = temp / "native-link.log"
        link.symlink_to(target)
        with self.assertRaises(OSError):
            writer.open_native_log(link)
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_bytes(), b"protected log")

class SC54NormalIngestControls(unittest.TestCase):
    def test_normal_ingest_projects_valid_native_receipt_through_shared_ladder(self):
        from ingest_sources import SOURCES, ingest
        from ledger import Ledger
        self.assertIn("qwen4exp-quality-measurement", SOURCES)
        self.assertEqual(ct.source_classes()[SOURCE_KIND], ct.MEASUREMENT_CLASS)
        temp, record, _, _ = make_fixture(self, "ppl")
        receipt = temp / "sample.quality.json"
        write_receipt(receipt, record)
        ledger = Ledger(temp / "ledger.jsonl")
        report = ingest(ledger, "qwen4exp-quality-measurement", [receipt],
                        as_of="2026-10-08T01:00:00Z", dry_run=True)
        self.assertEqual(report["rows_projected"], 1)
        self.assertEqual(report["frames_emitted"], 3)
        native = native_rows(receipt)
        self.assertEqual(len(native), 1)
        self.assertEqual(grade(native[0]), grade(ct.registered()[SOURCE_KIND](native[0])))

    def test_normal_ingest_refuses_mutated_native_identity(self):
        from ingest_sources import ingest
        from ledger import Ledger
        temp, record, _, _ = make_fixture(self, "ppl")
        receipt = temp / "broken.quality.json"
        record["corpus_after"]["sha256"] = "0" * 64
        write_receipt(receipt, record)
        report = ingest(Ledger(temp / "ledger.jsonl"), "qwen4exp-quality-measurement",
                        [receipt], as_of="2026-10-08T01:00:00Z", dry_run=True)
        self.assertEqual(report["rows_projected"], 0)
        self.assertEqual(len(report["refused"]), 1)
        self.assertIn("captured identity no longer names the same bytes/inode", report["refused"][0]["reason"])

class SC54FakeChildWrapperControl(unittest.TestCase):
    def test_wrapper_captures_model_free_fake_child(self):
        d=Path(tempfile.mkdtemp(prefix="sc54-fake-child-wrapper-"));self.addCleanup(shutil.rmtree,d,ignore_errors=True)
        fake=d/"fake-perplexity";fake.write_text(textwrap.dedent("""\
            #!/usr/bin/env python3
            import mmap,os,sys,time
            args=sys.argv[1:]
            so=args[args.index('--fixture-object')+1]
            fd=os.open(so,os.O_RDONLY);mapping=mmap.mmap(fd,0,access=mmap.ACCESS_READ)
            time.sleep(0.25)
            print('calculating perplexity over 1 chunks, n_ctx=64, batch_size=64, n_seq=1')
            print('[1]2.5,')
            print('Final estimate: PPL = 2.5 +/- 0.1')
            mapping.close();os.close(fd)
        """));fake.chmod(0o755)
        so=d/"libggml-cpu.so";so.write_bytes(b"model-free data fixture\0GGML_IQK\0not executable code")
        model=d/"not-loaded-model.gguf";model.write_bytes(b"opaque model fixture never opened by fake child")
        corpus=d/"corpus.txt";corpus.write_bytes(b"synthetic corpus")
        out=d/"receipts";out.mkdir()
        spec={"schema":DECL_SCHEMA,"run_id":"fake-run","pair_id":"fake-pair","arm_id":"fake-arm","mode":"ppl","author":"offhost source fixture","issued_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"protocol_id":"synthetic-wrapper-control","metrics":{"Final estimate: PPL":{"unit":"perplexity","metric_direction":"lower_better","category":"CANDIDATE","metric":"perplexity"}}}
        sp=d/"metric-spec.json";sp.write_bytes(canonical(spec))
        argv=[sys.executable,str(ROOT/"scripts"/"vidya"/"qwen4exp_quality_capture.py"),"--run-id","fake-run","--pair-id","fake-pair","--arm-id","fake-arm","--mode","ppl","--source-revision","synthetic-only","--model-name","fixture","--quant","Q4","--protocol-id","synthetic-wrapper-control","--metric-spec",str(sp),"--model",str(model),"--corpus",str(corpus),"--ny","32","--out-dir",str(out),"--env","GGML_IQK=1","--",str(fake),"-m",str(model),"-f",str(corpus),"-c","64","--chunks","1","--fixture-object",str(so)]
        result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors="replace"))
        receipt=out/"fake-run.fake-arm.quality.json";rows=read_project(receipt,ClaimTuple)
        self.assertEqual(len(rows),1);self.assertIsInstance(rows[0],ClaimTuple)
        self.assertIsInstance(grade(rows[0]),tuple)

if __name__=="__main__":unittest.main()

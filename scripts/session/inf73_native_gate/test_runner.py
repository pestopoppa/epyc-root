"""Model-free synthetic controls; never enters actual native/main Runtime.__init__."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import runner as r
import materialize as m
import capture_native
import driver
import prepare
from owned import OwnedProcesses

GRANT = "regions=q1 start=2026-10-25T17:00Z end=2026-10-25T18:00Z\n"
NOW = 1792948500.0  # replaced below from canonical parsed epoch
FIELDS = r.grant_fields(GRANT)
NOW = FIELDS["start_epoch"] + 1
ENV = {"FILLER_CPUS": "24-47,120-135", "FILLER_END": str(int(FIELDS["end_epoch"])),
       "FILLER_DEADLINE": str(int(FIELDS["end_epoch"] - 90))}

def blob(body):
    return hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()

def tree(body=b"fixture\n", path="a.py"):
    return "100644 blob " + blob(body) + "\t" + path + "\n"

class GrantControls(unittest.TestCase):
    def test_quarter_subset_is_valid_without_numeric2_grant(self):
        chosen, deadline = r.verify_grant(GRANT, ENV, {24, 25}, 2, NOW)
        self.assertEqual(chosen, {24, 25})
        self.assertLess(deadline, FIELDS["end_epoch"])
    def test_empty_declared_refused(self):
        with self.assertRaises(r.Refused): r.verify_grant(GRANT, ENV, set(), 2, NOW)
    def test_foreign_cpu_refused(self):
        with self.assertRaises(r.Refused): r.verify_grant(GRANT, ENV, {0, 24}, 2, NOW)
    def test_declared_over_budget_refused(self):
        with self.assertRaises(r.Refused): r.verify_grant(GRANT, ENV, {24,25,26}, 2, NOW)
    def test_exported_cpu_forgery_refused(self):
        with self.assertRaises(r.Refused): r.verify_grant(GRANT, dict(ENV, FILLER_CPUS="0-191"), {24}, 2, NOW)
    def test_expired_refused(self):
        with self.assertRaises(r.Refused): r.verify_grant(GRANT, ENV, {24}, 2, FIELDS["end_epoch"])
    def test_future_grant_refused(self):
        with self.assertRaises(r.Refused): r.verify_grant(GRANT, ENV, {24}, 2, FIELDS["start_epoch"]-1)
    def test_overlong_deadline_refused(self):
        with self.assertRaises(r.Refused): r.verify_grant(GRANT, dict(ENV, FILLER_DEADLINE=str(int(FIELDS["end_epoch"]+1))), {24}, 2, NOW)
    def test_replaced_grant_refused(self):
        with self.assertRaises(r.Refused): r.verify_grant(GRANT+"extra=changed\n", ENV, {24}, 2, NOW, hashlib.sha256(GRANT.encode()).hexdigest())
    def test_invalid_ranges_refused(self):
        for value in ("", "1-0", "0-999999", "mi210_0", "q7"):
            with self.subTest(value=value), self.assertRaises(r.Refused): r.cpus(value)

class SourceControls(unittest.TestCase):
    def test_spoofed_filler_cannot_enter_materializer_cli(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            plan = Path(temp, "spoof-plan.json")
            plan.write_text(json.dumps({"status": "MAIN_APPROVED_MATERIALIZATION"}))
            result = subprocess.run([sys.executable, "-I", "-S", "-B", m.__file__,
                "--plan", str(plan), "--approved-plan-sha", hashlib.sha256(plan.read_bytes()).hexdigest()],
                env={"FILLER_ID": "spoof"}, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("library-only materializer", result.stderr)
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), ["spoof-plan.json"])
    def test_private_clone_is_local_sparse_exact_commit_only(self):
        commands=[]
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp,"clone")
            def run(args,**kwargs):
                commands.append(args)
                if args[1]=="clone":
                    dest.mkdir();(dest/"a.py").write_bytes(b"fixture\n")
            self.assertEqual(m.private_clone("/fake-source","0"*40,tree(),tree(),dest,run),1)
            self.assertEqual(commands[0][1:5],["clone","--shared","--no-hardlinks","--no-checkout"])
            self.assertIn("--no-cone",commands[1]);self.assertEqual(commands[2][-1],"0"*40)
    def test_only_approved_runtime_link_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp,"source");root.mkdir();target=Path(temp,"orch");target.mkdir()
            (root/"a.py").write_bytes(b"fixture\n");(root/"repos").mkdir()
            (root/"repos/epyc-orchestrator").symlink_to(target,target_is_directory=True)
            r.verify_materialized(root,r.read_tree(tree()),approved_links={"repos/epyc-orchestrator":str(target)})
            with self.assertRaises(r.Refused):r.verify_materialized(root,r.read_tree(tree()))
    def test_runtime_copy_is_exact_and_refuses_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp,"source");source.mkdir();file=source/"package.py";file.write_text("fixture")
            closure={"files":{str(file):r.digest(file)},"symlinks":{}}
            m.copy_runtime(closure,source,Path(temp,"good"))
            self.assertEqual(Path(temp,"good/package.py").read_text(),"fixture")
            file.write_text("changed")
            with self.assertRaises(r.Refused):m.copy_runtime(closure,source,Path(temp,"bad"))
    def test_reader_missing_fixture_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(r.Refused,"missing"):
                r.verify_materialized(temp, r.read_tree(tree(path="tests/vidya/test_autokernel_unified_arm.py")))
    def test_exact_source_and_fixture_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,"a.py").write_bytes(b"fixture\n")
            r.verify_materialized(temp, r.read_tree(tree()))
    def test_stale_source_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,"a.py").write_bytes(b"stale\n")
            with self.assertRaisesRegex(r.Refused,"differs"): r.verify_materialized(temp, r.read_tree(tree()))
    def test_untracked_import_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,"a.py").write_bytes(b"fixture\n")
            Path(temp,"shadow.py").write_text("ambience")
            with self.assertRaisesRegex(r.Refused,"file set"): r.verify_materialized(temp, r.read_tree(tree()))
    def test_symlink_source_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,"target.py").write_bytes(b"fixture\n")
            Path(temp,"a.py").symlink_to("target.py")
            with self.assertRaises(r.Refused): r.verify_materialized(temp,r.read_tree(tree()))
    def test_duplicate_and_traversal_refused(self):
        for text in (tree()+tree(), tree(path="../outside.py"), tree().replace("100644","120000")):
            with self.subTest(text=text), self.assertRaises(r.Refused): r.read_tree(text)
    def test_full_tree_symlink_is_identity_only_not_readset(self):
        result=r.read_tree(tree().replace("100644","120000"), regular_only=False)
        self.assertEqual(result["a.py"][0],"120000")
    def test_materializer_uses_immutable_blob_and_no_checkout(self):
        body=b"fixture\n"; calls=[]
        def git(args, **kwargs):
            calls.append(args)
            return tree() if "ls-tree" in args else body
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp,"new")
            self.assertEqual(m.materialize("/fake","0"*40,tree(),tree(),dest,git),1)
            self.assertEqual(dest.joinpath("a.py").read_bytes(),body)
            self.assertTrue(all("checkout" not in args for args in calls))
            with self.assertRaises(r.Refused): m.materialize("/fake","0"*40,tree(),tree(),dest,git)
    def test_corrupt_git_transport_refused(self):
        def git(args, **kwargs): return tree() if "ls-tree" in args else b"corrupt"
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(r.Refused,"different blob"):
                m.materialize("/fake","0"*40,tree(),tree(),Path(temp,"new"),git)

class EnvironmentControls(unittest.TestCase):
    def test_rogue_sibling_package_outside_selected_roots_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            own=Path(temp);site=own/"site";site.mkdir();(site/"unapproved.py").write_text("shadow")
            closure=own/"closure.json";closure.write_text(json.dumps({"roots":[],"files":{},"symlinks":{},"elf_libraries":{}}))
            runtime=object.__new__(r.Runtime)
            runtime.approval={"canonical_provider_files":{},"runner_files":{},"materialized":{},"environment":{
                "interpreter":{"path":sys.executable,"sha256":r.digest(sys.executable)},
                "runtime_files_manifest":{"path":str(closure),"sha256":r.digest(closure)},"import_roots":[str(site)]}}
            with self.assertRaisesRegex(r.Refused,"unapproved module"):
                runtime.verify_sources()
    def test_materialization_unarmed_before_any_gnx_or_source_action(self):
        with tempfile.TemporaryDirectory() as temp:
            plan=Path(temp,"plan.json");plan.write_text(json.dumps({"status":"PROPOSED_UNARMED","source_review_approved":False}))
            with patch.object(sys,"argv",["prepare.py","--plan",str(plan),"--sha",r.digest(plan)]),self.assertRaisesRegex(r.Refused,"UNARMED"):
                prepare.main()
    def test_ambient_credentials_paths_and_gpu_never_inherited(self):
        a={"materialized":{name:{"root":"/private/"+name} for name in ("research","root","orchestrator")},"environment":{"import_roots":["/sealed/site"]}}
        inherited={key:"x" for key in ("FILLER_ID","FILLER_END","FILLER_DEADLINE","FILLER_CPUS","FILLER_STOPFILE")}
        inherited.update(OPENAI_API_KEY="secret",PYTHONPATH="/poison",LD_LIBRARY_PATH="/production",HOME="/operator",OMP_NUM_THREADS="96")
        env=r.clean_environment(a,Path("/private/result"),inherited)
        self.assertNotIn("OPENAI_API_KEY",env)
        self.assertNotIn("/poison",env["PYTHONPATH"])
        self.assertEqual(env["LD_LIBRARY_PATH"],"")
        self.assertEqual(env["OMP_NUM_THREADS"],"1")
        self.assertEqual(env["EPYC_ROOT_REPO"],env["EPYC_REALMASK_ROOT"])
        self.assertEqual(env["ROCR_VISIBLE_DEVICES"],"")
    def test_unarmed_approval_refused_before_state_or_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            approval=Path(temp,"approval.json"); approval.write_text(json.dumps({"schema":r.SCHEMA,"approved":False,"status":"PROPOSED_UNARMED"}))
            with self.assertRaisesRegex(r.Refused,"UNARMED"):
                r.Runtime(approval,r.digest(approval),Path(temp,"run"))
            self.assertFalse(Path(temp,"run").exists())

class BoundaryControls(unittest.TestCase):
    def runtime(self,temp):
        runtime=object.__new__(r.Runtime)
        runtime.flags=Path(temp); runtime.grant=Path(temp,"grant"); runtime.grant.write_text(GRANT)
        runtime.grant_sha=r.digest(runtime.grant)
        runtime.approval_path=Path(temp,"approval"); runtime.approval_path.write_text("{}")
        runtime.approval_sha=r.digest(runtime.approval_path)
        runtime.approval={"maximum_declared_cpus":2}; runtime.declared={24,25};runtime.owner=(42,99);runtime.cancelled=None
        return runtime
    def check(self, mutation=None, affinity={24,25},owner=True):
        with tempfile.TemporaryDirectory() as temp:
            runtime=self.runtime(temp)
            env=dict(ENV,FILLER_STOPFILE=str(Path(temp,"STOP")))
            if mutation: mutation(runtime)
            with patch.dict(os.environ,env,clear=True), patch.object(r.time,"time",return_value=NOW), patch.object(r.os,"sched_getaffinity",return_value=affinity), patch.object(r,"owner_is_ancestor",return_value=owner):
                return runtime.boundary()
    def test_actual_subset_passes(self): self.check(affinity={24})
    def test_actual_excess_refused(self):
        with self.assertRaises(r.Refused): self.check(affinity={24,26})
    def test_hold_refused(self):
        with self.assertRaises(r.Refused): self.check(lambda x:(x.flags/"HOLD_other").touch())
    def test_stop_refused(self):
        with self.assertRaises(r.Refused): self.check(lambda x:(x.flags/"STOP").touch())
    def test_acquired_owner_lost_refused(self):
        with self.assertRaises(r.Refused): self.check(owner=False)
    def test_source_approval_drift_refused(self):
        with self.assertRaises(r.Refused): self.check(lambda x:x.approval_path.write_text("changed"))

class CleanupControls(unittest.TestCase):
    def owned(self,stat):
        own=object.__new__(OwnedProcesses)
        class Module:
            @staticmethod
            def read_stat(root,pid): return stat
        own.module=Module(); own.captured={};own.errors=[];own.resolved_owned_errors=[]
        own.live=lambda exclude=(): []
        own.resolve_owned_errors=lambda:None
        return own
    def test_original_owner_and_two_empty_censuses_required(self):
        own=self.owned((1,99,"S",0,0))
        with patch("owned.time.sleep"):
            receipt=own.cleanup((42,99),timeout_s=1)
        self.assertTrue(receipt["verified"])
        self.assertTrue(receipt["empty_tree_verified"])
    def test_reused_owner_identity_refuses_even_empty_tree(self):
        own=self.owned((1,100,"S",0,0))
        with patch("owned.time.sleep"):
            receipt=own.cleanup((42,99),timeout_s=1)
        self.assertFalse(receipt["verified"])
        self.assertFalse(receipt["owner_held_during_cleanup"])

class StageWaitControls(unittest.TestCase):
    def exercise(self, returncode=0, cancel=False):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp); entry=output/"stage_exec.py"; entry.write_text("fixture")
            runtime=object.__new__(r.Runtime); runtime.output=output;runtime.owner=(42,99)
            runtime.approval_path=output/"approval";runtime.approval_sha="sealed"
            runtime.approval={"stage_timeouts_s":{"focused":100,"full":100},"cleanup_reserve_s":1,
                "runner_files":{"stage_exec":{"path":str(entry),"sha256":r.digest(entry)}},
                "materialized":{"research":{"root":temp}}}
            calls=[]
            def boundary():
                calls.append(1)
                if cancel and len(calls)==3: raise r.Refused("STOP active")
                return NOW+300
            runtime.boundary=boundary;runtime.verify_sources=lambda:None
            class Child:
                rc=None if cancel else returncode
                def poll(self): return self.rc
                def wait(self): return self.rc
            child=Child()
            class Owned:
                def child_env(self,env): return env
                def capture(self): pass
                def cleanup(self,owner,timeout_s):
                    if cancel: child.rc=-15
                    return {"verified":True,"empty_tree_verified":True}
            (output/"focused.junit.xml").write_text("<testsuite/>")
            import shutil
            with patch.object(r.subprocess,"Popen",return_value=child),patch.object(r,"clean_environment",return_value={}),patch.object(shutil,"disk_usage",return_value=type("Usage",(),{"free":200*1024**3})()),patch.object(r.time,"time",return_value=NOW):
                if returncode or cancel:
                    with self.assertRaises(r.Refused): runtime.stage("focused",[],Owned())
                else:
                    self.assertEqual(runtime.stage("focused",[],Owned())["original_wait"],0)
            receipt=json.loads((output/"focused.original.json").read_text())
            self.assertEqual(receipt["original_wait"],-15 if cancel else returncode)
            self.assertFalse((output/".validated").exists())
            return receipt
    def test_success_preserves_original_wait_zero(self): self.exercise()
    def test_failure_preserves_original_wait_seven(self): self.exercise(returncode=7)
    def test_stop_preserves_term_wait_and_policy_refusal(self):
        receipt=self.exercise(cancel=True)
        self.assertEqual(receipt["policy_refusal"],"STOP active")

class NativeWaitControls(unittest.TestCase):
    def test_native_provider_cannot_inherit_python_or_library_poison(self):
        env=capture_native.provider_environment({"PYTHONHOME":"/poison","PYTHONPATH":"/poison",
            "LD_PRELOAD":"/poison","OPENAI_API_KEY":"secret","FILLER_ID":"fixture","FILLER_STUB_CMD":"fake"},Path("/private"))
        self.assertNotIn("PYTHONHOME",env);self.assertNotIn("OPENAI_API_KEY",env)
        self.assertNotIn("FILLER_STUB_CMD",env)
        self.assertEqual(env["PYTHONPATH"],"");self.assertEqual(env["LD_PRELOAD"],"")
        self.assertEqual(env["FILLER_ID"],"fixture")
    def test_canonical_native_original_nonzero_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            own=Path(temp);(own/"capture_native.py").write_text("fake source")
            bootstrap=own/"site";bootstrap.mkdir()
            (own/"MAIN-APPROVED-NATIVE-LAUNCH.json").write_text(json.dumps({"status":"MAIN_APPROVED_NATIVE","approved":True,"native_launch_approved":True,"row_id":"fixture-only","canonical_region_lock":{},"canonical_provider_files":{},"canonical_provider_bootstrap":{"root":str(bootstrap),"files":[str(bootstrap/"_virtualenv.py")]}}))
            child=type("Child",(),{"pid":123,"wait":lambda self:7})()
            with patch.object(capture_native,"__file__",str(own/"capture_native.py")),patch.dict(os.environ,{"FILLER_ID":"fixture-only"},clear=True),patch.object(capture_native,"checked_reference",return_value=Path("/fake/region-lock")),patch.object(capture_native,"digest",return_value="sealed"),patch.object(capture_native.subprocess,"Popen",return_value=child),patch.object(capture_native,"proc_identity",return_value=((123,99),1,"S")),patch.object(capture_native.signal,"signal"):
                self.assertEqual(capture_native.main(),7)
            receipt=json.loads((own/"NATIVE_OWNER_ORIGINAL_WAIT.json").read_text())
            self.assertEqual(receipt["popen_wait_returncode"],7)
            self.assertEqual(receipt["policy_returncode"],7)
    def test_original_driver_nonzero_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            own=Path(temp);(own/"driver.py").write_text("fake source")
            (own/"MAIN-APPROVED-NATIVE-LAUNCH.json").write_text("fixture")
            (own/"MAIN-NATIVE-LAUNCH.sha256").write_text("approval_sha256=sealed")
            (own/"NATIVE_OWNER_LIVE.json").write_text("fixture")
            child=type("Child",(),{"pid":124,"wait":lambda self:5})()
            with patch.object(driver,"__file__",str(own/"driver.py")),patch.object(driver,"digest",return_value="sealed"),patch.object(driver.subprocess,"Popen",return_value=child),patch.object(driver,"proc_identity",return_value=((124,100),1,"S")),patch.object(driver.signal,"signal"):
                self.assertEqual(driver.main(),5)
            self.assertEqual(json.loads((own/"DRIVER_ORIGINAL_WAIT.json").read_text())["popen_wait_returncode"],5)

if __name__ == "__main__": unittest.main()

#!/usr/bin/env python3
"""PROPOSED official-quarter materialization job, after main/private-GNX review.
Pins the complete preparation body to2 CPUs inside whichever quarter owner selects.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runner import Refused, checked_reference, digest, grant_fields, grant_cpus, verify_grant, write_json
from materialize import private_clone, copy_runtime

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--plan",required=True);parser.add_argument("--sha",required=True)
    args=parser.parse_args();plan_path=Path(args.plan)
    if digest(plan_path)!=args.sha:raise Refused("preparation plan digest changed")
    plan=json.loads(plan_path.read_text())
    if plan.get("status")!="MAIN_APPROVED_MATERIALIZATION" or plan.get("source_review_approved") is not True:
        raise Refused("UNARMED source preparation")
    clearance=json.loads(checked_reference(plan["private_gnx_review"]).read_text())
    if clearance.get("status")!="MAIN_ACCEPTED_PRIVATE_GNX" or clearance.get("unresolved_high_or_critical") is not False:
        raise Refused("private GNX/source caller review incomplete")
    row="codex-ni-inf73-source-prepare-20261025"
    if os.environ.get("FILLER_ID")!=row:raise Refused("wrong preparation row")
    flags=Path("/mnt/raid0/llm/tmp/compute-flags");grant=flags/"grants"/(row+".grant")
    original=grant.read_text();grant_sha=digest(grant)
    declared=set(sorted(grant_cpus(grant_fields(original)["regions"]))[:2])
    if len(declared)!=2:raise Refused("owner quarter has fewer than2 CPUs")
    os.sched_setaffinity(0,declared)
    def boundary():
        if digest(plan_path)!=args.sha:raise Refused("plan changed")
        if list(flags.glob("HOLD_*")) or Path(os.environ["FILLER_STOPFILE"]).exists():raise Refused("HOLD/STOP")
        verify_grant(grant.read_text(),os.environ,declared,2,time.time(),grant_sha)
        actual=os.sched_getaffinity(0)
        if not actual or not actual<=declared:raise Refused("preparation affinity exceeds declared<=canonical")
    own=Path(plan["own_state_root"]).resolve();counts={}
    for name,spec in plan["materialized"].items():
        boundary()
        destination=Path(spec["root"]).absolute()
        if not destination.is_relative_to(own) or destination==own:raise Refused("private source escapes own state")
        counts[name]=private_clone(spec["repository"],spec["commit"],checked_reference(spec["complete_tree"]).read_text(),checked_reference(spec["readset"]).read_text(),destination)
    for spec in plan["materialized"].values():
        boundary()
        for relative,target in spec.get("runtime_links",{}).items():
            link=Path(spec["root"])/relative
            if ".." in Path(relative).parts or Path(relative).is_absolute():raise Refused("unsafe runtime link")
            link.parent.mkdir(parents=True,exist_ok=True);link.symlink_to(target,target_is_directory=True)
            with (Path(spec["root"])/".git/info/exclude").open("a") as excluded:excluded.write("/"+relative+"\n")
    boundary()
    environment=plan["environment"];destination=Path(environment["import_roots"][0]).absolute()
    if not destination.is_relative_to(own):raise Refused("private runtime escapes own state")
    closure=json.loads(checked_reference(environment["runtime_files_manifest"]).read_text())
    copy_runtime(closure,environment["package_source_root"],destination)
    boundary()
    write_json(own/"MATERIALIZED.json",{"source_plan_sha256":args.sha,"counts":counts,
        "runtime_approved":False,"native_original_wait":None,"gpu_clearance":False})
if __name__=="__main__":
    try:main()
    except (Refused,OSError,ValueError,KeyError) as error:raise SystemExit("REFUSED: "+str(error))

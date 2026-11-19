#!/usr/bin/env python3
"""Operator 2026-11-06 "Yes, both" (2): docker containers started UNDER a row are stopped + removed when the row ends
(STOP, hard end, exit); containers the row did not start are never touched. A FAKE docker binary keeps its state in a temp
dir - no real docker command runs here. Origin: ak-asm-t1-harness-r3-20261106-r2 left `ak-asm-t1-h3-fmoe-16bit-<pid>`
(0.8 GB VRAM on the MI210) running past its STOP, overlapping the next timing row.
Also: gpu-quiet counts a container's KFD client (host pid, outside any grant tree) as foreign occupancy."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_RF = os.path.join(os.path.dirname(_HERE), "rowflow")

FAKE_DOCKER = r"""#!/bin/bash
db=$FAKE_DOCKER_DB
echo "$*" >> "$db/calls"
live() { for l in "$db"/*.labels; do [ -e "$l" ] || continue; i=$(basename "$l" .labels); [ "$(cat "$db/$i.state")" != gone ] && echo "$i"; done; }
case "$1" in
  run|create)
    shift; lab=""
    while [ $# -gt 0 ]; do case "$1" in --label) lab="$lab $2"; shift 2;; *) shift;; esac; done
    id="c$RANDOM$RANDOM$RANDOM"; echo "$lab" > "$db/$id.labels"; echo running > "$db/$id.state"; echo "$id";;
  ps)
    want=""; while [ $# -gt 0 ]; do case "$1" in --filter) want=${2#label=}; shift 2;; *) shift;; esac; done
    for i in $(live); do [ -z "$want" ] && { echo "$i"; continue; }; [[ " $(cat "$db/$i.labels") " == *" $want "* ]] && echo "$i"; done;;
  stop) echo stopped > "$db/$4.state" 2>/dev/null || echo stopped > "$db/${@: -1}.state";;
  rm) echo gone > "$db/${@: -1}.state";;
  *) exit 0;;
esac
"""
# the job starts one labelled-by-shim container, one --rm container, then idles
JOB = "docker run -d --name ak-asm-t1-h3-fmoe-16bit-1 vllm/vllm-openai-rocm; docker run --rm -d img2; sleep 1000"


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class DockerCleanup(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="filler-docker-")
        self.bin = os.path.join(self.d, "bin")
        self.db = os.path.join(self.d, "dockerdb")
        self.grants = os.path.join(self.d, "grants")
        for p in (self.bin, self.db, self.grants):
            os.makedirs(p)
        shutil.copy(os.path.join(_RF, "filler_run15.sh"), self.bin)
        self.fake = os.path.join(self.bin, "fake-docker")
        open(self.fake, "w").write(FAKE_DOCKER)
        os.chmod(self.fake, 0o755)
        self.stop = os.path.join(self.d, "row.STOP")
        self.proc = None
        # a container the row did NOT start (no label / another row's label): must survive everything below
        self.foreign = []
        for i, lab in enumerate(("", "epyc.filler.row=some-other-row")):
            cid = f"foreign{i}"
            open(os.path.join(self.db, cid + ".labels"), "w").write(lab + "\n")
            open(os.path.join(self.db, cid + ".state"), "w").write("running\n")
            self.foreign.append(cid)

    def tearDown(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        shutil.rmtree(self.d, ignore_errors=True)

    def state(self, cid):
        return open(os.path.join(self.db, cid + ".state")).read().strip()

    def mine(self):
        return [f[:-7] for f in os.listdir(self.db) if f.endswith(".labels") and f[:-7] not in self.foreign]

    def grant(self, rid, secs=900):
        now = datetime.now(timezone.utc)
        with open(os.path.join(self.grants, rid + ".grant"), "w") as f:
            f.write(f"regions=q0 start={iso(now - timedelta(seconds=5))} end={iso(now + timedelta(seconds=secs))}\n")

    def launch(self, rid, job=JOB, extra=(), docker=True):
        env = dict(os.environ, FILLER_FLAGS_DIR=self.d, FILLER_GRANTS_DIR=self.grants, FILLER_STATE_DIR=os.path.join(self.d, "state"),
                   FILLER_POLL="1", FILLER_DISK_FLOOR_GIB="0", FAKE_DOCKER_DB=self.db)
        env["FILLER_DOCKER_BIN"] = self.fake if docker else "/nonexistent/docker"   # never the host's real docker
        rl = os.path.join(self.bin, "region-lock")
        open(rl, "w").write('#!/bin/bash\nwhile [ $# -gt 0 ] && [ "$1" != -- ]; do shift; done; shift\n"$@" &\nwait\n')
        os.chmod(rl, 0o755)
        env["FILLER_RL"] = rl
        argv = ["bash", os.path.join(self.bin, "filler_run15.sh"), "--id", rid, "--class", "cpu", "--cmd", job, "--min-window", "60",
                "--stop", self.stop, "--complete-cmd", "false", "--workdir", self.d, "--stop-grace", "3", *extra]
        self.log = open(os.path.join(self.d, rid + ".out"), "w")
        self.proc = subprocess.Popen(argv, env=env, stdout=self.log, stderr=subprocess.STDOUT)

    def out(self, rid):
        return open(os.path.join(self.d, rid + ".out")).read()

    def wait_until(self, fn, t=30):
        end = time.time() + t
        while time.time() < end and not fn():
            time.sleep(0.2)
        return fn()

    def test_stop_stops_and_removes_row_containers_only(self):
        rid = "dk-stop"
        self.grant(rid)
        self.launch(rid)
        self.assertTrue(self.wait_until(lambda: len(self.mine()) == 2), self.out(rid))
        for c in self.mine():
            self.assertEqual(self.state(c), "running")
            self.assertIn(f"epyc.filler.row={rid}", open(os.path.join(self.db, c + ".labels")).read())
        open(self.stop, "w").close()
        self.assertEqual(self.proc.wait(timeout=60), 0, self.out(rid))
        self.assertEqual([self.state(c) for c in self.mine()], ["gone", "gone"], self.out(rid))
        self.assertEqual([self.state(c) for c in self.foreign], ["running", "running"], "a container the row did not start was touched")
        calls = open(os.path.join(self.db, "calls")).read().splitlines()
        touched = [x.split()[-1] for x in calls if x.startswith(("stop", "rm"))]
        self.assertTrue(touched and set(touched) <= set(self.mine()), calls)
        self.assertIn("docker: row containers stopped", self.out(rid))

    def test_normal_exit_also_cleans_up(self):
        rid = "dk-exit"
        self.grant(rid)
        self.launch(rid, job="docker run -d --name leak img; sleep 1")
        self.assertEqual(self.proc.wait(timeout=60), 0, self.out(rid))
        self.assertEqual([self.state(c) for c in self.mine()], ["gone"])
        self.assertEqual([self.state(c) for c in self.foreign], ["running", "running"])

    def test_no_docker_binary_is_a_noop(self):
        rid = "dk-none"
        self.grant(rid)
        self.launch(rid, job="sleep 1", docker=False)
        self.assertEqual(self.proc.wait(timeout=60), 0, self.out(rid))
        self.assertNotIn("REFUSED", self.out(rid))

    def test_negative_control_without_cleanup_container_survives(self):
        """Control: the same scenario against the pre-fix engine (15804eaf5) leaves the container running."""
        repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True, cwd=_HERE).stdout.strip()
        old = subprocess.run(["git", "-C", repo, "show", "15804eaf5:scripts/coordination/rowflow/filler_run15.sh"], capture_output=True, check=True).stdout
        open(os.path.join(self.bin, "filler_run15.sh"), "wb").write(old)
        rid = "dk-neg"
        self.grant(rid)
        # the pre-fix engine installs no shim: use the fake directly, as the real incident's `docker run` did
        self.launch(rid, job=f"{self.fake} run -d --name leak img; sleep 1000")
        self.assertTrue(self.wait_until(lambda: len(self.mine()) == 1), self.out(rid))
        open(self.stop, "w").close()
        self.assertEqual(self.proc.wait(timeout=60), 0, self.out(rid))
        self.assertEqual([self.state(c) for c in self.mine()], ["running"], "control: pre-fix engine cleaned up - test proves nothing")


class GpuQuietCountsContainers(unittest.TestCase):
    def test_container_kfd_client_outside_grant_tree_is_foreign(self):
        sys.path.insert(0, _RF)
        import rowflow as rf
        d = tempfile.mkdtemp(prefix="kfd-")
        try:
            kfd = os.path.join(d, "kfd")
            os.makedirs(os.path.join(kfd, "4242"))     # host pid of a process inside a docker container
            open(os.path.join(kfd, "4242", "vram_0"), "w").write(str(800 * (1 << 20) + (300 << 20)))   # 1.07 GiB
            old = rf.KFD_PROC
            rf.KFD_PROC = kfd
            try:
                occ = rf.gpu_occupancy()
                pids, v = rf.gpu_foreign(occ, own={1, 2, 3})   # the row's own tree does not contain the container's pid
                self.assertEqual(pids, [4242])
                self.assertGreaterEqual(v, rf.GPU_FOREIGN_VRAM_MAX)
                flags = os.path.join(d, "flags")
                os.makedirs(os.path.join(flags, "state"), exist_ok=True)
                why = rf.gpu_quiet_gate(flags, [], {}, lambda *_: None, set())
                self.assertIn("device not quiet", why or "")
                self.assertIn("4242", why)
            finally:
                rf.KFD_PROC = old
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

# AK-DISCOVERY-OWNED-CGROUP: job-owned cgroup for the one native discovery compiler probe

Status: DESIGN (2026-11-09). Nothing here is armed; no compiler or cgroup operation was run to write it. Owner of the
box: the AutoKernel owner (3c4ca599). This closes the box's "needs a separate design with the exact owned path, cleanup, and
one native compiler probe" and nothing else; the arming row is a separate, operator-visible step (section 6).

## 1. The problem, precisely

Test: `scripts/kernel_rnd/autokernel/controller/test_discovery_static_registry.py::StaticBuildCacheTests::
test_static_build_source_enters_real_runner_with_supervised_cgroup` (Research origin/main `1a78d2990` at the time of
writing; line numbers drift, the name is the identity). Its fixture (`fixture(real_run_build_probe=True)`) derives the
build-sandbox parent from the test process's own membership:

    unified = [line.split("::",1)[1] for line in Path("/proc/self/cgroup").read_text().splitlines() if "::" in line]
    controller_cgroup = "/sys/fs/cgroup" / unified[0].lstrip("/")

and the test asserts `Path(disposition.sandbox_receipt["cgroup_path"]).parent == controller_cgroup` for the configure and
build dispositions, plus `sandbox_teardown["removed"]`. Each real `worktree.run_build` creates one leaf
`<parent>/autokernel-<pid>-<token>` (`execution/sandbox.py::_join_owned_cgroup`: `mkdir(0o700)` then writes its own PID
to the leaf's `cgroup.procs`) and `cleanup_cgroup` drains and `rmdir`s only that leaf.

Measured here (read-only, 2026-11-09): `/proc/self/cgroup` is `0::/`, so the parent resolves to `/sys/fs/cgroup` itself.
That directory is the container's cgroup-namespace root: uid `node`, mode 0755, `cgroup.procs` writable by `node`,
`cgroup.kill` root-owned and NOT writable, `cgroup.type` domain, controllers `cpuset cpu io memory hugetlb pids rdma misc`.
`/sys/fs/cgroup/autokernel` (the narrow delegation `default_cgroup_root` prefers) does not exist. The test would therefore
put real leaves directly in the namespace root next to every other session's processes, and the sandbox's escalation
path (`cgroup.kill`) is only available on the leaf, never on the root. One empty leaf from an earlier run is already there
(`/sys/fs/cgroup/autokernel-3699565-233fdc4fe52099f8`, created 2026-11-09 11:03, PID 3699565 gone, `cgroup.procs` empty):
direct evidence that today's un-owned placement leaks leaves. It is not cleaned by this design (not ours; see 5).

No source or assertion change is needed or proposed: the fixture already follows whatever cgroup the test process is
in. The fix is to make the process start inside a cgroup that the job owns.

## 2. Exact owned path

    OWNED = /sys/fs/cgroup/akd-<run_id>

* `/sys/fs/cgroup` is the delegation parent because it is the only writable cgroup directory this uid has (section 1);
  `HOST_CGROUP_ROOT`/`EPYC_AUTOKERNEL_CGROUP_ROOT` are not involved (the probe passes the controller cgroup as
  `sandbox_cgroup_root`, which is what the test checks).
* `<run_id>` = the filler row id plus a 16-hex random token, e.g. `akd-ak-discovery-native-toy-cgroup-20261025-3f9c1e0a77d24b18`.
  Regex enforced by the wrapper: `^akd-[A-Za-z0-9._-]{8,96}$`. The `akd-` prefix is deliberately different from the
  sandbox's `autokernel-` prefix so a sweep for one can never match the other.
* Created by the wrapper with `mkdir(mode=0o700)` (exclusive, never adopts an existing path), recorded in
  `<scratch>/cgroup-receipt.json`: `{path, dev, ino, uid, nlink, mode, created_utc, run_id, wrapper_pid}`.
* Entered by the child only: the wrapper starts the test as `sh -c 'echo $$ > <OWNED>/cgroup.procs && exec <argv>'`, so
  `/proc/self/cgroup` of the test is `0::/akd-<run_id>` before Python starts. The wrapper itself stays in `0::/`.
  The test's computed parent is then exactly `OWNED` and every leaf is `OWNED/autokernel-<pid>-<token>`.
* No controllers are enabled (no write to any `cgroup.subtree_control`), so the cgroup-v2 no-internal-process rule is not
  triggered by the test process living in a cgroup that also has children.

## 3. Cleanup (owned path only, rmdir only, fail closed)

After the child exits (or at the deadline, section 4), the wrapper, in order:

1. Re-validate ownership: `OWNED` matches the regex, is a direct child of `/sys/fs/cgroup`, is not a symlink, and its
   `(dev, ino, uid)` equal the receipt. Any mismatch: stop, touch nothing, exit 3 with the mismatch in the receipt.
2. Read `OWNED/cgroup.procs` and every descendant's. Non-empty: write `1` to `OWNED/cgroup.kill` (owned by `node`, kills the
   whole subtree), poll up to 5 s (`cgroup.events` `populated 0`). Still populated: exit 4 and leave the directory for
   the operator; never retry with a wider target.
3. Remove descendants deepest-first with `os.rmdir` (the sandbox normally already removed its leaves; leftovers are
   `autokernel-*` children of `OWNED` only), then `os.rmdir(OWNED)`. No `rm -r`, no recursive helper: the kernel refuses
   `rmdir` on a populated cgroup, which is the safety property.
4. Record `{removed: true, leftover_leaves: [...], killed: bool}` in the receipt.

Never touched: `/sys/fs/cgroup` itself, any sibling (including the leaked `autokernel-3699565-...`), any cgroup the
wrapper did not create. The wrapper never moves other PIDs.

## 4. Deadline and stop

The row's deadline/STOP file terminates the captured child session (own PGID, SIGTERM then SIGKILL, verified dead with
`ps -p`); the `cgroup.kill` step in section 3 then catches any escaped compiler descendant. A deadline hit is a FAIL,
never a PASS; the receipt keeps the process receipts the sandbox wrote.

## 5. Why not the alternatives

* Run under `/sys/fs/cgroup` as-is: the gap described above (shared namespace root, no kill authority, observed leak).
* `systemd-run --user --scope` / `Delegate=yes`: `systemd-run` exists (`/usr/bin/systemd-run`) but whether this
  container has a user manager with delegation was not verified; it would also add a second owner of the lifecycle. Not needed when the namespace root is
  already `node`-writable.
* Patching the test to inject a parent: weakens what the test proves (that the real runner nests under the supervised
  controller cgroup) and needs a qualified caller audit. Not needed.
* Leave the existing empty leaked leaf: it is another run's residue; removing it is a single non-recursive `rmdir` of an
  empty cgroup the owner (AK) can do, separate from this design and not required for the probe.

## 6. The one native compiler probe

Exactly one execution, after the owner arms it through the existing filler launcher and grant guard (no new publisher):

| Field | Value |
|---|---|
| id | `ak-discovery-native-toy-cgroup-20261025` |
| class / pool | cpu / `pool:gap-filler`, one quarter, thread 1, 4 GiB, 600 s deadline, 300 s min window |
| command | `/usr/bin/python3 -m unittest -v scripts.kernel_rnd.autokernel.controller.test_discovery_static_registry.StaticBuildCacheTests.test_static_build_source_enters_real_runner_with_supervised_cgroup` inside the owned cgroup, in a private mirror of Research at an accepted pin |
| env | `TMPDIR` under the row scratch, `PYTHONDONTWRITEBYTECODE=1`, compiler jobs 1 (test uses `BuildParallelism(jobs=1)`), thread env 1 |
| compiler work | toy tree only: `probe-source/CMakeLists.txt` + `main.c` (`int main(void){return 0;}`), one `cmake` configure + one build. No llama.cpp, no model, no serving or champion path, no network, no fetch/install |
| precondition | `cmake` and `cc` resolve (`/usr/bin/cmake`, `/usr/bin/cc` verified present); test, `worktree.py` and `sandbox.py` blobs equal the accepted pin at grant time |

PASS requires all of: unittest rc 0 and `OK` for that one test; the receipt shows configure and build dispositions
`sandbox_teardown.removed == true`; both `cgroup_path` parents equal `OWNED`; after cleanup `OWNED` does not exist and
`ls /sys/fs/cgroup` shows no new `autokernel-*` or `akd-*` entry compared with the pre-run listing. The result log must
label it "native toy-compiler fixture PASS", distinct from the 53 model-free discovery methods already passing.
Negative controls to run first in the prototype (temp-dir fake cgroup root, no real cgroup writes): wrapper refuses a
non-matching name, a symlink, a changed inode, and a populated path (exit 4), and leaves them untouched.

## 7. What is still open (one sentence)

The wrapper above is not written or armed: it needs the AK owner to schedule the single gap-filler row (or the operator to
approve running one real cgroup mkdir/rmdir pair under `/sys/fs/cgroup`); the box stays unticked until that probe passes.

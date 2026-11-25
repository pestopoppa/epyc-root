"""INSTALL.manifest + deploy_rowflow.sh --parity (pipeline audit 2026-11-10 #6): one install list, a read-only drift check."""
import ast
import os
import subprocess
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
CO = os.path.dirname(_TESTS)
REPO = os.path.dirname(os.path.dirname(CO))
MANIFEST = os.path.join(CO, "INSTALL.manifest")
DEPLOY = os.path.join(CO, "rowflow", "deploy_rowflow.sh")


def entries():
    out = []
    for line in open(MANIFEST):
        f = line.split("#", 1)[0].split()
        if len(f) >= 2:
            out.append((f[0], f[1], f[2] if len(f) > 2 else "hot"))
    return out


class ManifestTest(unittest.TestCase):
    def test_every_source_exists_and_published_paths_are_unique(self):
        es = entries()
        pubs = [p for p, _, _ in es]
        self.assertEqual(len(pubs), len(set(pubs)))
        for pub, src, cls in es:
            self.assertTrue(os.path.isfile(os.path.join(REPO, src)), src)
            self.assertIn(cls, ("hot", "engine"))
            self.assertFalse(os.path.isabs(pub) or ".." in pub.split("/"), pub)

    def test_reclaim_imports_are_installed_beside_it(self):
        pubs = {p for p, _, _ in entries()}
        for mod in ("reclaim_row", "file_result", "filing", "auto_file", "scratch_guard", "row_disk_budget",
                    "row_worktree", "worktree_gate", "worktree_salvage", "scratch_lease"):
            self.assertIn(f"bin/churn/{mod}.py", pubs)
        for f in ("rowflow.py", "publish_row.py", "notify.py", "diskpause.py", "hostutil.py", "grant_ok_launcher.py",
                  "filler_run15.sh", "filler_lib.sh", "run_direct.py", "run_direct.sh"):
            self.assertIn(f"bin/rowflow/{f}", pubs)

    def import_problems(self, es):
        # Search every source directory represented in the install, including modules
        # omitted from the manifest; ast.walk also sees imports inside functions.
        source_dirs = {os.path.dirname(os.path.join(REPO, src)) for _, src, _ in es}
        repo_modules = {f[:-3] for d in source_dirs for f in os.listdir(d) if f.endswith(".py")}
        installed = {os.path.splitext(os.path.basename(pub))[0] for pub, _, _ in es if pub.endswith(".py")}
        problems = []
        for pub, src, _ in es:
            if not src.endswith(".py"):
                continue
            with open(os.path.join(REPO, src)) as f:
                tree = ast.parse(f.read(), filename=src)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                elif isinstance(node, ast.ImportFrom) and node.level == 1 and not node.module:
                    names = [a.name for a in node.names]
                for name in names:
                    if name in repo_modules and name not in installed:
                        problems.append(f"{pub}:{node.lineno} imports uninstalled repo module {name}")
        return problems

    def test_installed_files_import_only_installed_repo_modules(self):
        problems = self.import_problems(entries())
        self.assertEqual(problems, [], "\n".join(problems))

    def test_cross_directory_function_import_missing_is_detected(self):
        es = [entry for entry in entries() if os.path.basename(entry[0]) != "typed_classify.py"]
        problems = self.import_problems(es)
        self.assertTrue(any("bin/rowflow/publish_row.py:" in p and "typed_classify" in p for p in problems), problems)


class ParityTest(unittest.TestCase):
    def parity(self, flags):
        env = dict(os.environ, ROWFLOW_FLAGS=flags)
        return subprocess.run(["bash", DEPLOY, "--parity", "--ref", "HEAD", "--repo", REPO], env=env,
                              capture_output=True, text=True, timeout=120)

    def test_missing_then_same_then_diff(self):
        if subprocess.run(["git", "-C", REPO, "diff", "--quiet", "HEAD", "--", "scripts"], capture_output=True).returncode:
            self.skipTest("uncommitted changes under scripts/: parity compares against HEAD blobs")
        with tempfile.TemporaryDirectory() as flags:
            r = self.parity(flags)
            self.assertEqual(r.returncode, 1)
            self.assertIn("MISSING ", r.stdout)
            for pub, src, _ in entries():
                dst = os.path.join(flags, pub)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                blob = subprocess.run(["git", "-C", REPO, "show", f"HEAD:{src}"], capture_output=True, check=True).stdout
                open(dst, "wb").write(blob)
            r = self.parity(flags)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("DIFF", r.stdout)
            with open(os.path.join(flags, "bin/rowflow/rowflow.py"), "a") as f:
                f.write("# drift\n")
            r = self.parity(flags)
            self.assertEqual(r.returncode, 1)
            self.assertRegex(r.stdout, r"DIFF\s+bin/rowflow/rowflow.py")


if __name__ == "__main__":
    unittest.main()

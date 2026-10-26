"""Grant-only, model-free regression of invocation/data and temp-root boundaries."""
import os
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))
from destructive_scratch_scan import scan

P = "/mnt/raid0/llm/tmp"


class ScratchInvocationTests(unittest.TestCase):
    def assertAllowed(self, command):
        self.assertIsNone(scan(command), command)

    def assertBlocked(self, command):
        self.assertIsNotNone(scan(command), command)

    def setUp(self):
        self.environ = patch.dict(os.environ, {}, clear=False)
        self.environ.start()
        for key in ("EPYC_TEST_TMP", "EPYC_TEST_TMP_ID", "EPYC_DESTRUCTIVE_SCRATCH_ROOTS"):
            os.environ.pop(key, None)

    def tearDown(self):
        self.environ.stop()

    def test_existing_37_case_harness_is_an_invocation(self):
        self.assertAllowed("bash " + shlex.quote(str(HOOKS / "tests/test_destructive_scratch_hook.sh")))
        self.assertAllowed("python3 " + shlex.quote(str(HOOKS / "tests/destructive_scratch_cases.py")))

    def test_bundle_regression_is_an_invocation(self):
        source = HOOKS.parents[1] / "scripts/champion/fold_gates/regression/test_bundle_gate_verdict.sh"
        self.assertTrue(source.is_file())
        self.assertAllowed("bash " + shlex.quote(str(source)))

    def test_inline_python_writes_json_containing_delete_text(self):
        code = f'import json; open("/tmp/out.json", "w").write(json.dumps({{"command": "rm -rf {P}/evidence"}}))'
        self.assertAllowed("python3 -c " + shlex.quote(code))
        self.assertAllowed("python3 - <<'PY'\n" + code + "\nPY")

    def test_script_file_invocations_remain_refused(self):
        with tempfile.TemporaryDirectory(prefix="epyc-hook-source-", dir="/tmp") as temporary:
            python = Path(temporary) / "delete.py"
            shell = Path(temporary) / "delete.sh"
            python.write_text(f'import shutil; shutil.rmtree("{P}/evidence")\n')
            shell.write_text(f'#!/bin/bash\nrm -rf {P}/evidence\n')
            self.assertBlocked("python3 " + shlex.quote(str(python)))
            self.assertBlocked("bash " + shlex.quote(str(shell)))

    def test_python_data_and_comments_do_not_invoke_delete(self):
        code = f'payload = "shutil.rmtree({P}/evidence)"\n# os.unlink("{P}/evidence")\nprint(payload)'
        self.assertAllowed("python3 -c " + shlex.quote(code))
        self.assertAllowed(f"cat <<'DOC'\nrm -rf {P}/evidence\nDOC")
        self.assertAllowed(f"echo '$(rm -rf {P}/evidence)'")

    def test_real_python_delete_calls_remain_refused(self):
        codes = [
            f'import shutil; shutil.rmtree("{P}/evidence")',
            f'import shutil as s; s.rmtree("{P}/evidence")',
            f'from shutil import rmtree as delete; delete("{P}/evidence")',
            f'import os; victim="{P}/evidence"; os.remove(victim)',
            f'from pathlib import Path; Path("{P}/evidence").unlink()',
            f'from pathlib import Path; p=Path("{P}/evidence"); p.rmdir()',
            f'from pathlib import Path; (Path("{P}") / "evidence").unlink()',
            f'import os, shutil; shutil.rmtree(os.path.join("{P}", unknown))',
            f'import subprocess; subprocess.run(["rm", "-rf", "{P}/evidence"])',
            f'exec("import shutil; shutil.rmtree(\\\"{P}/evidence\\\")")',
        ]
        for code in codes:
            with self.subTest(code=code):
                self.assertBlocked("python3 -c " + shlex.quote(code))

    def test_shell_data_and_invocations_are_distinct(self):
        self.assertAllowed(f'bash -c \'printf "%s\\n" "rm -rf {P}/evidence"\'')
        for command in (f'bash -c \'rm -rf {P}/evidence\'',
                        f'bash <<\'SH\'\nrm -rf {P}/evidence\nSH',
                        f'echo "$(rm -rf {P}/evidence)"',
                        f'printf "%s" `rm -rf {P}/evidence`',
                        f'cleanup() {{ rm -rf {P}/evidence; }}',
                        f'if rm -rf {P}/evidence; then echo ok; fi'):
            with self.subTest(command=command):
                self.assertBlocked(command)
        self.assertBlocked(f'CODE="rm -rf {P}/evidence"; eval "$CODE"')

    def test_exact_mktemp_cleanup_is_scoped(self):
        self.assertAllowed('TMP=$(mktemp -d); rm -rf "$TMP"')
        self.assertAllowed(f'TMP=$(mktemp -d {P}/hook-test.XXXXXX); trap \'rm -rf "$TMP"\' EXIT')
        self.assertAllowed(f'rm -rf "$(/usr/bin/mktemp -d {P}/hook-test.XXXXXX)"')
        bad = [
            'TMP=$(mktemp -d); rm -rf "$TMP/../evidence"',
            'TMP=$(mktemp -d); rm -rf "$TMP/"',
            'TMP=$(mktemp -d); rm -rf $TMP',
            'TMP=$(mktemp -d); rm -rf "${TMP%/*}"',
            f'TMP=$(mktemp -d); rm -rf "$TMP" {P}/evidence',
            f'TMP=$(mktemp -d); TMP={P}/evidence; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); trap \'rm -rf "$TMP"\' EXIT; TMP={P}/evidence',
            f'TMP={P}/evidence; trap "rm -rf \\"$TMP\\"" EXIT; TMP=$(mktemp -d)',
            f'rm -rf "$(mktemp -d {P}/test.XXXXXX)/../evidence"',
            f'TMP=$(mktemp -du {P}/known.XXXXXX); rm -rf "$TMP"',
            f'PATH=/untrusted; rm -rf "$(mktemp -d {P}/test.XXXXXX)"',
            f'TMP=$(mktemp -d); read TMP <<<\'{P}/evidence\'; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); declare TMP={P}/evidence; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); local TMP={P}/evidence; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); readonly TMP={P}/evidence; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); typeset TMP={P}/evidence; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); printf -v TMP "%s" {P}/evidence; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); mapfile TMP <<<\'{P}/evidence\'; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); readarray TMP <<<\'{P}/evidence\'; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); source /dev/stdin <<<\'TMP={P}/evidence\'; rm -rf "$TMP"',
            'TMP=$(mktemp -d); alias anything=true; rm -rf "$TMP"',
            f'TMP=$(mktemp -d); find "$TMP" -exec rm -rf {{}} {P}/evidence \\;',
        ]
        for command in bad:
            with self.subTest(command=command):
                self.assertBlocked(command)
        self.assertAllowed('TMP=$(mktemp -d); read l <<<"harmless"; rm -rf "$TMP"')

    def test_declared_test_root_requires_identity_and_exact_target(self):
        with tempfile.TemporaryDirectory(prefix="epyc-hook-regression-", dir="/tmp") as temporary:
            base = Path(temporary)
            owned = base / "owned-test-root"
            sibling = base / "evidence"
            owned.mkdir()
            sibling.mkdir()
            st = owned.stat()
            os.environ.update(EPYC_DESTRUCTIVE_SCRATCH_ROOTS=str(base), EPYC_TEST_TMP=str(owned),
                              EPYC_TEST_TMP_ID=f"{st.st_dev}:{st.st_ino}:{st.st_uid}")
            self.assertAllowed('rm -rf "$EPYC_TEST_TMP"')
            self.assertAllowed("rm -rf " + str(owned))
            for command in ('rm -rf "$EPYC_TEST_TMP/"', 'rm -rf "$EPYC_TEST_TMP/../evidence"',
                            'rm -rf $EPYC_TEST_TMP', 'rm -rf "${EPYC_TEST_TMP%/*}"',
                            'rm -rf "$EPYC_TEST_TMP" ' + str(sibling),
                            'find "$EPYC_TEST_TMP" -delete'):
                with self.subTest(command=command):
                    self.assertBlocked(command)
            os.environ["EPYC_TEST_TMP_ID"] = f"{st.st_dev}:{st.st_ino + 1}:{st.st_uid}"
            self.assertBlocked('rm -rf "$EPYC_TEST_TMP"')
            os.environ.pop("EPYC_TEST_TMP_ID")
            self.assertBlocked('rm -rf "$EPYC_TEST_TMP"')
            os.environ.pop("EPYC_TEST_TMP")
            self.assertBlocked(f'EPYC_TEST_TMP={owned}; rm -rf "$EPYC_TEST_TMP"')
            root_st = base.stat()
            os.environ.update(EPYC_TEST_TMP=str(base),
                              EPYC_TEST_TMP_ID=f"{root_st.st_dev}:{root_st.st_ino}:{root_st.st_uid}")
            self.assertBlocked('rm -rf "$EPYC_TEST_TMP"')
            link = base / "alias"
            link.symlink_to(owned, target_is_directory=True)
            os.environ.update(EPYC_TEST_TMP=str(link),
                              EPYC_TEST_TMP_ID=f"{st.st_dev}:{st.st_ino}:{st.st_uid}")
            self.assertBlocked('rm -rf "$EPYC_TEST_TMP"')
            self.assertTrue(owned.is_dir() and sibling.is_dir())
            os.environ.update(EPYC_TEST_TMP=str(owned),
                              EPYC_TEST_TMP_ID=f"{st.st_dev}:{st.st_ino}:{st.st_uid}")
            with patch("destructive_scratch_scan.declared_forbidden_roots", return_value=[str(owned)]):
                self.assertBlocked('rm -rf "$EPYC_TEST_TMP"')
            nested_repo = owned / "shared-repository"
            nested_repo.mkdir()
            (nested_repo / ".git").write_text("gitdir: /unrelated/shared/metadata\n")
            self.assertBlocked('rm -rf "$EPYC_TEST_TMP"')


if __name__ == "__main__":
    unittest.main()

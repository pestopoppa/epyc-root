"""Negative-control fixture for verify_kernel_store.sh custody checks (LOOP-48 / LOOP-59).

Reproduces the 2026-11-03 incident on a SYNTHETIC store: a regular-file
libggml-hip.so replacing the libggml-hip.so -> libggml-hip.so.0 symlink in a build dir.
The clean store must pass; each mutation must turn the verifier red with the specific
custody finding. A verifier whose red branches have never run is not known to go red.

Synthetic only: nothing here touches /mnt/raid0/llm/kernels. Foreground, file-scoped:
    python3 -B tests/test_verify_kernel_store_custody.py -v
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/session/verify_kernel_store.sh"
RESOLVER_PATH = "/mnt/raid0/llm/epyc-orchestrator/src/registry/kernel_paths.py"
LINKAGE_PATH = "/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh"

RESOLVER = (
    "from pathlib import Path\n"
    "BACKEND_BINARIES = {'cpu':'llama-server','gpu':'llama-server',"
    "'stt':'whisper-server','tts':'tts-server'}\n"
    "BACKEND_VENDOR_LIB_DIRS = {k:(Path('/opt/rocm')/'lib',) for k in ('gpu','stt','tts')}\n"
    "_BACKENDS_NEEDING_NO_PREPEND = frozenset({'cpu'})\n"
)
# Always-green linkage stand-in: this file tests the CUSTODY layer, not ldd.
LINKAGE = """#!/bin/bash
for n in libggml-base.so.0 libggml.so.0 libggml-cpu.so.0; do
  printf '  OK   %s -> %s/%s\\n' "$n" "$2" "$n"
done
echo 'PASS: all ggml libraries are inside expected root'
exit 0
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class KernelStoreCustodyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.kroot = self.base / "kernels"
        (self.kroot / "production").mkdir(parents=True)
        (self.kroot / "builds").mkdir()
        (self.kroot / "archive").mkdir()
        resolver = self.base / "kernel_paths.py"
        resolver.write_text(RESOLVER, encoding="utf-8")
        linkage = self.base / "verify_ggml_linkage.sh"
        linkage.write_text(LINKAGE, encoding="utf-8")
        linkage.chmod(0o755)
        src = VERIFIER.read_text(encoding="utf-8")
        self.assertIn(RESOLVER_PATH, src)
        self.assertIn(LINKAGE_PATH, src)
        self.script = self.base / "verify.sh"
        self.script.write_text(
            src.replace(RESOLVER_PATH, str(resolver)).replace(LINKAGE_PATH, str(linkage)),
            encoding="utf-8")
        self.script.chmod(0o755)
        self.bins = {}
        for backend, binary in (("cpu", "llama-server"), ("gpu", "llama-server"),
                                ("stt", "whisper-server"), ("tts", "tts-server")):
            self._make_build(backend, binary)

    def _make_build(self, backend, binary, spelling="bin/"):
        build = self.kroot / "builds" / f"{backend}-20260101-fixture"
        bindir = build / "bin"
        bindir.mkdir(parents=True)
        files = {binary: b"synthetic exe " + backend.encode()}
        for name in ("libggml-base.so.0.16.0", "libggml.so.0.16.0", "libggml-cpu.so.0.16.0"):
            files[name] = (backend + ":" + name).encode()
        if backend != "cpu":
            files["libggml-hip.so.0.16.0"] = b"genuine hip library " + backend.encode()
        if backend in ("cpu", "gpu"):
            for tool in ("llama-completion", "llama-speculative", "llama-lookup",
                         "llama-mtmd-cli", "llama-cli"):
                files[tool] = b"tool " + tool.encode()
        for name, data in files.items():
            (bindir / name).write_bytes(data)
            (bindir / name).chmod(0o755)
        for stem in ("libggml-base.so", "libggml.so", "libggml-cpu.so"):
            (bindir / f"{stem}.0").symlink_to(f"{stem}.0.16.0")
            (bindir / stem).symlink_to(f"{stem}.0")
        if backend != "cpu":
            (bindir / "libggml-hip.so.0").symlink_to("libggml-hip.so.0.16.0")
            (bindir / "libggml-hip.so").symlink_to("libggml-hip.so.0")
        self._write_sums(build, spelling)
        (self.kroot / "production" / backend).symlink_to(bindir, target_is_directory=True)
        self.bins[backend] = bindir

    @staticmethod
    def _write_sums(build, spelling):
        bindir = build / "bin"
        rows = []
        for f in sorted(bindir.iterdir()):
            if f.is_symlink() or not f.is_file():
                continue
            rows.append(f"{sha(f.read_bytes())}  {spelling}{f.name}")
        (build / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")

    def run_verifier(self):
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "KERNEL_STORE_ROOT": str(self.kroot), "LD_LIBRARY_PATH": ""}
        return subprocess.run(["bash", str(self.script)], env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              check=False, timeout=120)

    def assert_red(self, result, *needles):
        self.assertEqual(result.returncode, 1, result.stdout)
        for needle in needles:
            self.assertIn(needle, result.stdout)

    # -- positive controls ------------------------------------------------
    def test_clean_store_passes_and_reports_custody(self):
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.count("custody: "), 4, result.stdout)
        self.assertIn("gpu: custody:", result.stdout)
        self.assertNotIn("FAIL", result.stdout)

    def test_all_three_sha256sums_path_spellings_are_accepted(self):
        for spelling in ("./", "bin/", "./bin/"):
            with self.subTest(spelling=spelling):
                build = self.bins["gpu"].parent
                if spelling == "./":
                    # bin-relative rows live beside the binaries in some builds
                    self._write_sums(build, "bin/")
                    rows = (build / "SHA256SUMS").read_text().replace("  bin/", "  ./")
                    (build / "SHA256SUMS").write_text(rows)
                else:
                    self._write_sums(build, spelling)
                result = self.run_verifier()
                self.assertEqual(result.returncode, 0, result.stdout)

    # -- negative controls: the five mutations ---------------------------
    def test_m1_regular_file_replaces_alias_the_incident(self):
        alias = self.bins["gpu"] / "libggml-hip.so"
        alias.unlink()
        alias.write_bytes(b"stray hip library - different build")  # the 2026-10-27 shape
        alias.chmod(0o755)
        result = self.run_verifier()
        self.assert_red(result, "UNLISTED regular file (not in SHA256SUMS): libggml-hip.so",
                        "REGULAR FILE where a symlink alias belongs: libggml-hip.so")
        # The pre-patch checks were green on this exact mutation: -e is true, the
        # fake linkage is green. Prove the failure is the custody layer alone.
        for line in result.stdout.splitlines():
            if line.startswith("  FAIL"):
                self.assertIn("custody", line)

    def test_m1b_identical_bytes_replacing_alias_still_fails(self):
        alias = self.bins["gpu"] / "libggml-hip.so"
        alias.unlink()
        alias.write_bytes((self.bins["gpu"] / "libggml-hip.so.0.16.0").read_bytes())
        result = self.run_verifier()
        self.assert_red(result, "REGULAR FILE where a symlink alias belongs: libggml-hip.so")

    def test_m2_unlisted_extra_regular_file(self):
        (self.bins["gpu"] / "libggml-hip.so.0.16.0.objcopy-rewritten-20261105").write_bytes(b"x")
        result = self.run_verifier()
        self.assert_red(result, "UNLISTED regular file (not in SHA256SUMS): "
                                "libggml-hip.so.0.16.0.objcopy-rewritten-20261105")

    def test_m3_listed_file_hash_mismatch(self):
        (self.bins["gpu"] / "libggml-hip.so.0.16.0").write_bytes(b"tampered hip library")
        result = self.run_verifier()
        self.assert_red(result, "HASH MISMATCH")

    def test_m4_missing_sha256sums_on_versioned_build(self):
        (self.bins["gpu"].parent / "SHA256SUMS").unlink()
        result = self.run_verifier()
        self.assert_red(result, "gpu: custody: no SHA256SUMS")

    def test_m5_dangling_alias(self):
        alias = self.bins["gpu"] / "libggml-hip.so"
        alias.unlink()
        alias.symlink_to("libggml-hip.so.9")
        result = self.run_verifier()
        self.assert_red(result, "DANGLING")

    # -- extra negatives for the symlink rules ---------------------------
    def test_symlink_with_path_target_is_refused(self):
        alias = self.bins["gpu"] / "libggml-hip.so"
        alias.unlink()
        alias.symlink_to(str(self.bins["gpu"] / "libggml-hip.so.0"))
        result = self.run_verifier()
        self.assert_red(result, "must be a bare same-dir basename")

    def test_stray_in_cpu_build_is_caught_too(self):
        (self.bins["cpu"] / "libggml-cpu.so").unlink()
        (self.bins["cpu"] / "libggml-cpu.so").write_bytes(b"stray cpu lib")
        result = self.run_verifier()
        self.assert_red(result, "cpu: custody:")

    def test_unlisted_dotfile_warns_but_does_not_fail(self):
        (self.bins["gpu"] / ".scratch-marker").write_bytes(b"x")
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("WARN gpu: custody: UNLISTED regular file (not in SHA256SUMS): .scratch-marker",
                      result.stdout)

    def test_empty_manifest_is_not_a_pass(self):
        (self.bins["gpu"].parent / "SHA256SUMS").write_text("")
        result = self.run_verifier()
        self.assert_red(result, "attests nothing")


if __name__ == "__main__":
    unittest.main()

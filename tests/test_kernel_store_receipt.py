"""Synthetic-only coverage for opt-in kernel-store dependency receipts."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "scripts/session/kernel_store_receipt.py"


def _producer():
    module = types.ModuleType("kernel_store_receipt")
    module.__file__ = str(PRODUCER)
    exec(compile(PRODUCER.read_bytes(), str(PRODUCER), "exec", dont_inherit=True), module.__dict__)
    return module


class KernelStoreReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.kernel_root = self.base / "kernels"
        self.receipts = self.base / "receipts"
        for path in (self.kernel_root / "production", self.kernel_root / "builds",
                     self.kernel_root / "archive", self.receipts):
            path.mkdir(parents=True, exist_ok=True)
        self.resolver = self.base / "kernel_paths.py"
        self.resolver.write_text(
            "from pathlib import Path\n"
            "BACKEND_BINARIES = {'cpu':'llama-server','gpu':'llama-server',"
            "'stt':'whisper-server','tts':'tts-server'}\n"
            "BACKEND_VENDOR_LIB_DIRS = {k:(Path('/opt/rocm')/'lib',) "
            "for k in ('gpu','stt','tts')}\n"
            "_BACKENDS_NEEDING_NO_PREPEND = frozenset({'cpu'})\n", encoding="utf-8")
        self.linkage = self.base / "verify_ggml_linkage.sh"
        self.linkage.write_text(self._fake_linkage(), encoding="utf-8")
        self.linkage.chmod(0o755)
        self.targets = {}
        for backend, binary_name in (("cpu", "llama-server"), ("gpu", "llama-server"),
                                     ("stt", "whisper-server"), ("tts", "tts-server")):
            target = self.kernel_root / "builds" / f"{backend}-fixture"
            target.mkdir()
            (self.kernel_root / "production" / backend).symlink_to(target, target_is_directory=True)
            self.targets[backend] = target
            binary = target / binary_name
            binary.write_bytes(b"synthetic executable\n")
            binary.chmod(0o755)
            for soname in ("libggml-base.so.0", "libggml.so.0", "libggml-cpu.so.0"):
                (target / soname).write_bytes(f"{backend}:{soname}\n".encode())
            if backend != "cpu":
                (target / "libggml-hip.so.0").write_bytes(b"synthetic hip library\n")
                (target / "libggml-hip.so").symlink_to("libggml-hip.so.0")
            if backend in ("cpu", "gpu"):
                for name in ("llama-completion", "llama-speculative", "llama-lookup",
                             "llama-mtmd-cli", "llama-cli"):
                    companion = target / name
                    companion.write_text("fixture\n", encoding="utf-8")
                    companion.chmod(0o755)
        self.ambient = str(self.targets["cpu"])

    @staticmethod
    def _fake_linkage():
        return """#!/bin/bash
set -u
binary=$1
expected=$2
backend=$(basename "$expected")
backend=${backend%%-*}
printf 'binary : %s\\n' "$binary"
printf 'expect : libraries under %s\\n' "$expected"
if [ "${LD_LIBRARY_PATH+x}" = x ]; then state=PRESENT
else state=UNSET; fi
phase=launch
if [ "$backend" != cpu ]; then
  case ":${LD_LIBRARY_PATH:-}:" in *":$expected:"*) phase=launch ;;
    *) phase=ambient ;;
  esac
fi
if [ -n "${NI28_FAKE_OBSERVATION_ROOT:-}" ]; then
  mkdir -p "$NI28_FAKE_OBSERVATION_ROOT"
  printf '%s\\n' "$state" > "$NI28_FAKE_OBSERVATION_ROOT/$backend-$phase"
fi
if [ -f "$expected/.vacuous" ]; then
  echo 'FAIL: VACUOUS CHECK — nothing was inspected'
  exit 2
fi
if [ -f "$expected/.timeout" ]; then
  ( trap '' TERM; exec >/dev/null 2>&1; sleep 30 ) &
  echo $! > "$expected/.child.pid"
  wait
fi
bad=0
for soname in libggml-base.so.0 libggml.so.0 libggml-cpu.so.0; do
  if [ -f "$expected/.bad" ]; then
    printf '  BAD  %s -> /foreign/%s\\n' "$soname" "$soname"; bad=1
  else case ":${LD_LIBRARY_PATH:-}:" in *":$expected:"*)
    printf '  OK   %s -> %s/%s\\n' "$soname" "$expected" "$soname" ;;
  *) if [ -f "$expected/.ambient-ok" ]; then
       printf '  OK   %s -> %s/%s\\n' "$soname" "$expected" "$soname"
     else printf '  BAD  %s -> /foreign/%s\\n' "$soname" "$soname"; bad=1; fi ;;
  esac; fi
done
if [ "$backend" != cpu ]; then
  if [ -f "$expected/.bad" ]; then
    printf '  BAD  libggml-hip.so.0 -> /foreign/libggml-hip.so.0\\n'; bad=1
  else case ":${LD_LIBRARY_PATH:-}:" in *":$expected:"*)
    printf '  OK   libggml-hip.so.0 -> %s/libggml-hip.so.0\\n' "$expected" ;;
  *) if [ -f "$expected/.ambient-ok" ]; then
       printf '  OK   libggml-hip.so.0 -> %s/libggml-hip.so.0\\n' "$expected"
     else printf '  BAD  libggml-hip.so.0 -> /foreign/libggml-hip.so.0\\n'; bad=1; fi ;;
  esac; fi
fi
echo 'LD_LIBRARY_PATH order as the loader sees it:'
printf '%s\\n' "${LD_LIBRARY_PATH:-}" | tr ':' '\\n' | nl -ba
if [ "$bad" -eq 0 ]; then echo 'PASS: all ggml libraries are inside expected root'; exit 0; fi
echo 'FAIL: a library resolves outside expected root'
exit 1
"""

    def _capture(self, timeout=180):
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "LD_LIBRARY_PATH": self.ambient, "ROCM_PATH": "/opt/rocm"}
        return subprocess.run(
            [sys.executable, str(PRODUCER), "capture", "--receipt-root", str(self.receipts),
             "--synthetic", "--kernel-root", str(self.kernel_root),
             "--resolver", str(self.resolver), "--linkage-verifier", str(self.linkage),
             "--timeout", str(timeout)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)

    def _run_dir(self, result):
        for line in result.stdout.splitlines():
            if line.startswith("receipt="):
                return Path(line.split("=", 1)[1])
        self.fail(f"no retained receipt: rc={result.returncode}; stderr={result.stderr}")

    def _baseline_verifier(self):
        checkout = os.environ.get("NI28_BASELINE_CHECKOUT")
        self.assertTrue(checkout, "NI28_BASELINE_CHECKOUT must name the separate pinned CI checkout")
        checkout_path = Path(checkout).resolve(strict=True)
        revision = subprocess.run(["git", "-C", str(checkout_path), "rev-parse", "HEAD"],
                                  check=True, capture_output=True, text=True).stdout.strip()
        self.assertEqual(revision, "3872413fbcf0c945f44b8ca46df48f82adbb1c5e",
                         "parity baseline checkout is not the reviewed immutable revision")
        source_path = checkout_path / "scripts/session/verify_kernel_store.sh"
        source = source_path.read_text(encoding="utf-8")
        readset = {"path": str(source_path), "revision": revision,
                   "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest()}
        self.baseline_readset = readset
        return source

    def _copied_verifier(self, *, baseline):
        source = self._baseline_verifier() if baseline else (
            ROOT / "scripts/session/verify_kernel_store.sh").read_text(encoding="utf-8")
        for original, replacement in (
                ("/mnt/raid0/llm/epyc-orchestrator/src/registry/kernel_paths.py", str(self.resolver)),
                ("/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh",
                 str(self.linkage))):
            occurrences = 1 if baseline else 2
            self.assertEqual(source.count(original), occurrences,
                             f"unexpected recognized synthetic path substitution count: {original}")
            source = source.replace(original, replacement)
        path = self.base / ("baseline-verify.sh" if baseline else "current-verify.sh")
        path.write_text(source, encoding="utf-8")
        path.chmod(0o755)
        return path

    def _run_copied_verifier(self, script, *, unset_ld=False):
        observation_root = self.base / "observations"
        observation_root.mkdir(exist_ok=True)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "KERNEL_STORE_ROOT": str(self.kernel_root),
               "NI28_FAKE_OBSERVATION_ROOT": str(observation_root)}
        if not unset_ld:
            env["LD_LIBRARY_PATH"] = self.ambient
        for marker in observation_root.iterdir():
            if marker.is_file():
                marker.unlink()
        result = subprocess.run(["bash", str(script)], env=env, cwd=str(self.base),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False, text=True)
        observations = {}
        for backend in self.targets:
            for phase in ("launch", "ambient"):
                marker = observation_root / f"{backend}-{phase}"
                if marker.exists():
                    observations[f"{backend}:{phase}"] = marker.read_text(encoding="utf-8").strip()
        return result, observations

    def test_capture_binds_actual_launch_recipe_and_separate_ambient_diagnostics(self):
        result = self._capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = self._run_dir(result)
        producer = _producer()
        valid, problems = producer.verify(run_dir)
        self.assertTrue(valid, problems)
        request = json.loads((run_dir / "request.json").read_text())
        captured = json.loads((run_dir / "capture.json").read_text())
        self.assertEqual(len(request["backends"]), 4)
        self.assertTrue(captured["dependency_verification_passed"])
        records = captured["child_linkage_invocations"]
        cpu = next(r for r in records if r["backend"] == "cpu" and r["phase"] == "launch")
        gpu = next(r for r in records if r["backend"] == "gpu" and r["phase"] == "launch")
        ambient = next(r for r in records if r["backend"] == "gpu" and r["phase"] == "ambient")
        self.assertEqual(cpu["ld_library_path"], self.ambient)
        self.assertEqual(gpu["ld_library_path"],
                         f"{self.targets['gpu']}:/opt/rocm/lib:{self.ambient}")
        self.assertEqual(ambient["ld_library_path"], self.ambient)
        self.assertTrue(captured["ambient_diagnostics"])
        self.assertTrue(all(row["sha256"] for row in gpu["resolved_libraries"]))
        self.assertEqual(run_dir.stat().st_mode & 0o777, 0o500)

    def test_ordinary_mode_matches_prechange_copied_script_for_real_subprocess_fixtures(self):
        current = self._copied_verifier(baseline=False)
        baseline = self._copied_verifier(baseline=True)
        cases = ("pass", "cross-tree", "vacuous", "ambient-warning", "unset-ambient")
        for case in cases:
            for target in self.targets.values():
                for marker in (".bad", ".vacuous", ".ambient-ok"):
                    (target / marker).unlink(missing_ok=True)
            if case == "pass":
                for backend in ("gpu", "stt", "tts"):
                    (self.targets[backend] / ".ambient-ok").touch()
            elif case == "cross-tree":
                (self.targets["gpu"] / ".bad").touch()
            elif case == "vacuous":
                (self.targets["gpu"] / ".vacuous").touch()
            # The fixture lets the pass case resolve ambient libraries in
            # every backend; the warning case retains a CPU-only ambient path.
            expected = 1 if case in ("cross-tree", "vacuous", "unset-ambient") else 0
            unset_ld = case == "unset-ambient"
            before, before_env = self._run_copied_verifier(baseline, unset_ld=unset_ld)
            after, after_env = self._run_copied_verifier(current, unset_ld=unset_ld)
            self.assertEqual(before.returncode, expected, f"{case}: {before.stdout}")
            self.assertEqual((after.returncode, after.stdout),
                             (before.returncode, before.stdout), case)
            self.assertEqual(after_env, before_env, f"{case}: child env observations differ")
            if case == "ambient-warning":
                self.assertIn("ambient LD_LIBRARY_PATH mis-resolves", after.stdout)
            elif case == "pass":
                self.assertNotIn("ambient LD_LIBRARY_PATH mis-resolves", after.stdout)
            elif case == "unset-ambient":
                self.assertEqual(after_env.get("gpu:launch"), "PRESENT", after_env)
                self.assertEqual(after_env.get("gpu:ambient"), "UNSET", after_env)
        self.assertEqual(hashlib.sha256(Path(self.baseline_readset["path"]).read_bytes()).hexdigest(),
                         self.baseline_readset["sha256"], "parity baseline changed during the test")

    def test_vacuous_child_is_retained_and_receipt_is_false(self):
        (self.targets["gpu"] / ".vacuous").touch()
        result = self._capture()
        self.assertNotEqual(result.returncode, 0)
        run_dir = self._run_dir(result)
        captured = json.loads((run_dir / "capture.json").read_text())
        receipt = json.loads((run_dir / "receipt.json").read_text())
        gpu = next(r for r in captured["child_linkage_invocations"]
                   if r["backend"] == "gpu" and r["phase"] == "launch")
        self.assertIn("VACUOUS", base64.b64decode(gpu["combined_output_b64"]).decode())
        self.assertEqual(gpu["exit_code"], 2)
        self.assertFalse(receipt["dependency_verification_passed"])

    def test_missing_binary_refuses_before_execution_and_keeps_reason(self):
        (self.targets["gpu"] / "llama-server").unlink()
        result = self._capture()
        self.assertEqual(result.returncode, 2)
        run_dir = self._run_dir(result)
        refusal = json.loads((run_dir / "refusal.json").read_text())
        self.assertFalse(refusal["execution_started"])
        self.assertIn("executable missing", refusal["reason"])
        self.assertFalse((run_dir / "capture.json").exists())

    def test_missing_verifier_source_refuses_before_execution(self):
        self.linkage.unlink()
        result = self._capture()
        self.assertEqual(result.returncode, 2)
        run_dir = self._run_dir(result)
        refusal = json.loads((run_dir / "refusal.json").read_text())
        self.assertFalse(refusal["execution_started"])
        self.assertIn("linkage_verifier source is missing", refusal["reason"])
        self.assertFalse((run_dir / "capture.json").exists())

    def test_empty_resolver_map_refuses_before_execution(self):
        self.resolver.write_text("BACKEND_BINARIES = {}", encoding="utf-8")
        result = self._capture()
        self.assertEqual(result.returncode, 2)
        run_dir = self._run_dir(result)
        refusal = json.loads((run_dir / "refusal.json").read_text())
        self.assertFalse(refusal["execution_started"])
        self.assertIn("empty or invalid", refusal["reason"])
        self.assertFalse((run_dir / "capture.json").exists())

    def test_validator_rejects_resealed_empty_and_duplicate_backend_coverage(self):
        producer = _producer()
        for mutation in ("empty-map", "empty-snapshots", "duplicate-map"):
            result = self._capture()
            self.assertEqual(result.returncode, 0, f"{mutation}: {result.stderr}")
            run_dir = self._run_dir(result)
            os.chmod(run_dir, 0o700)
            request_path = run_dir / "request.json"
            capture_path = run_dir / "capture.json"
            receipt_path = run_dir / "receipt.json"
            request = json.loads(request_path.read_bytes())
            captured = json.loads(capture_path.read_bytes())
            if mutation == "empty-map":
                request["declared_backend_map"] = []
            elif mutation == "empty-snapshots":
                request["backends"] = []
            else:
                request["declared_backend_map"].append(request["declared_backend_map"][0])
            request["declared_backend_map_sha256"] = producer.sha256_bytes(
                producer.canonical_bytes(request["declared_backend_map"]))
            request_bytes = producer.canonical_bytes(request)
            receipt = json.loads(receipt_path.read_bytes())
            for path in (request_path, capture_path, receipt_path):
                path.chmod(0o600)
            try:
                request_path.write_bytes(request_bytes)
                captured["request_sha256"] = producer.sha256_bytes(request_bytes)
                capture_bytes = producer.canonical_bytes(captured)
                capture_path.write_bytes(capture_bytes)
                receipt["request_sha256"] = producer.sha256_bytes(request_bytes)
                receipt["capture_sha256"] = producer.sha256_bytes(capture_bytes)
                body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
                receipt["receipt_sha256"] = producer.sha256_bytes(producer.canonical_bytes(body))
                receipt_path.write_bytes(producer.canonical_bytes(receipt))
            finally:
                for path in (request_path, capture_path, receipt_path):
                    path.chmod(0o400)
                os.chmod(run_dir, 0o500)
            valid, problems = producer.verify(run_dir)
            self.assertFalse(valid, mutation)
            self.assertTrue(any("nonempty" in item or "unique coverage" in item
                                for item in problems), (mutation, problems))

    def test_child_replay_rejects_missing_duplicate_core_and_bad_rows(self):
        result = self._capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = self._run_dir(result)
        request = json.loads((run_dir / "request.json").read_bytes())
        captured = json.loads((run_dir / "capture.json").read_bytes())
        records = captured["child_linkage_invocations"]
        gpu = next(row for row in records if row["backend"] == "gpu" and row["phase"] == "launch")
        original = base64.b64decode(gpu["combined_output_b64"]).decode()
        core_line = next(line for line in original.splitlines(keepends=True)
                         if "OK   libggml-base.so" in line)
        for changed, expected in ((original.replace(core_line, ""), "exactly one"),
                                  (original + core_line, "exactly one"),
                                  (original + "  BAD  libggml-extra.so -> /foreign/libggml-extra.so\n",
                                   "bad row")):
            row = dict(gpu)
            row["combined_output_b64"] = base64.b64encode(changed.encode()).decode()
            problems, _ = _producer()._check_child_records(
                request, [row if item is gpu else item for item in records])
            self.assertTrue(any(expected in item for item in problems), problems)

        cpu = next(row for row in records if row["backend"] == "cpu" and row["phase"] == "launch")
        extra_cpu_ambient = dict(cpu, phase="ambient")
        problems, _ = _producer()._check_child_records(request, [*records, extra_cpu_ambient])
        self.assertTrue(any("unexpected child record: ('cpu', 'ambient')" in item
                            for item in problems), problems)

    def test_resealed_launch_row_cannot_resolve_to_hashed_ambient_library(self):
        result = self._capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = self._run_dir(result)
        producer = _producer()
        request_path = run_dir / "request.json"
        capture_path = run_dir / "capture.json"
        receipt_path = run_dir / "receipt.json"
        request = json.loads(request_path.read_bytes())
        captured = json.loads(capture_path.read_bytes())
        gpu_target, cpu_target = self.targets["gpu"], self.targets["cpu"]
        records = captured["child_linkage_invocations"]
        gpu = next(row for row in records if row["backend"] == "gpu" and row["phase"] == "launch")
        changed_output = base64.b64decode(gpu["combined_output_b64"]).decode().replace(
            f"{gpu_target}/libggml.so.0", f"{cpu_target}/libggml.so.0")
        self.assertNotEqual(changed_output,
                            base64.b64decode(gpu["combined_output_b64"]).decode(),
                            "foreign-library injection must land in the actual captured output")
        changed_bytes = changed_output.encode()
        gpu["combined_output_b64"] = base64.b64encode(changed_bytes).decode()
        gpu["combined_output_sha256"] = producer.sha256_bytes(changed_bytes)
        producer._check_child_records(request, records)  # refresh re-sealed derived digest rows

        outer = captured["outer_invocation"]
        outer_stdout = base64.b64decode(outer["stdout_b64"], validate=True)
        rewritten_lines = []
        for line in outer_stdout.splitlines(keepends=True):
            if not line.startswith(producer.CAPTURE_MARKER):
                rewritten_lines.append(line)
                continue
            fields = line.rstrip(b"\r\n").split(b"\t")
            if fields[1:3] == [b"gpu", b"launch"]:
                fields[7] = base64.b64encode(changed_bytes)
                line = b"\t".join(fields) + b"\n"
            rewritten_lines.append(line)
        outer_stdout = b"".join(rewritten_lines)
        outer["stdout_b64"] = base64.b64encode(outer_stdout).decode()
        outer["stdout_sha256"] = producer.sha256_bytes(outer_stdout)

        os.chmod(run_dir, 0o700)
        request_bytes = producer.canonical_bytes(request)
        request_path.chmod(0o600)
        request_path.write_bytes(request_bytes)
        captured["request_sha256"] = producer.sha256_bytes(request_bytes)
        capture_bytes = producer.canonical_bytes(captured)
        capture_path.chmod(0o600)
        capture_path.write_bytes(capture_bytes)
        receipt = json.loads(receipt_path.read_bytes())
        receipt["request_sha256"] = producer.sha256_bytes(request_bytes)
        receipt["capture_sha256"] = producer.sha256_bytes(capture_bytes)
        body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        receipt["receipt_sha256"] = producer.sha256_bytes(producer.canonical_bytes(body))
        receipt_path.chmod(0o600)
        receipt_path.write_bytes(producer.canonical_bytes(receipt))
        for path in (request_path, capture_path, receipt_path):
            path.chmod(0o400)
        os.chmod(run_dir, 0o500)
        valid, problems = producer.verify(run_dir)
        self.assertFalse(valid)
        self.assertTrue(any("launch library resolves outside its backend target" in item
                            for item in problems), problems)

    def test_timeout_kills_owned_verifier_process_group(self):
        (self.targets["cpu"] / ".timeout").touch()
        result = self._capture(timeout=0.5)
        self.assertNotEqual(result.returncode, 0)
        run_dir = self._run_dir(result)
        capture = json.loads((run_dir / "capture.json").read_bytes())
        self.assertEqual(capture["outer_invocation"]["execution_error"], "timeout")
        child_pid_path = self.targets["cpu"] / ".child.pid"
        self.assertTrue(child_pid_path.exists(), "fixture must start its owned child")
        pid = int(child_pid_path.read_text())
        for _ in range(40):
            try:
                stat_text = Path(f"/proc/{pid}/stat").read_text()
            except FileNotFoundError:
                break
            if stat_text.split()[2] == "Z":
                break
            time.sleep(0.05)
        else:
            self.fail(f"owned verifier child {pid} remained live after timeout cleanup")

    def test_cross_tree_launch_failure_keeps_bad_rows(self):
        (self.targets["gpu"] / ".bad").touch()
        result = self._capture()
        self.assertNotEqual(result.returncode, 0)
        run_dir = self._run_dir(result)
        captured = json.loads((run_dir / "capture.json").read_text())
        receipt = json.loads((run_dir / "receipt.json").read_text())
        gpu = next(r for r in captured["child_linkage_invocations"]
                   if r["backend"] == "gpu" and r["phase"] == "launch")
        self.assertEqual(gpu["exit_code"], 1)
        output = base64.b64decode(gpu["combined_output_b64"]).decode()
        self.assertIn("BAD", output)
        self.assertFalse(receipt["dependency_verification_passed"])

    def test_changed_binary_and_capture_bytes_refuse_readback(self):
        result = self._capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = self._run_dir(result)
        (self.targets["gpu"] / "llama-server").write_bytes(b"changed after capture\n")
        valid, problems = _producer().verify(run_dir)
        self.assertFalse(valid)
        self.assertTrue(any("binary changed" in item for item in problems), problems)

        os.chmod(run_dir, 0o700)
        capture_path = run_dir / "capture.json"
        os.chmod(capture_path, 0o600)
        capture_path.write_bytes(capture_path.read_bytes() + b" ")
        valid, problems = _producer().verify(run_dir)
        self.assertFalse(valid)
        self.assertTrue(any("capture digest binding" in item for item in problems), problems)


if __name__ == "__main__":
    unittest.main()

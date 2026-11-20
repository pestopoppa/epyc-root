"""Build-receipt contract tests with real git worktrees and a simulated toolchain.

No kernel build or GPU/model run is performed by this suite.
"""
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import build


class Builds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git(self.repo, 'init', '-q')
        self.git(self.repo, 'config', 'user.name', 'Fixture')
        self.git(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/code').write_text('original\n')
        (self.repo / '.gitignore').write_text('ignored\n')
        self.git(self.repo, 'add', 'src/code', '.gitignore')
        self.git(self.repo, 'commit', '-qm', 'fixture')
        pin = self.git(self.repo, 'rev-parse', 'HEAD').strip().decode()
        self.source = self.root / 'source'
        self.git(self.repo, 'worktree', 'add', '--detach', str(self.source), pin)
        # Use a patch produced by git, exactly as the production installer does.
        (self.repo / 'src/code').write_text('patched\n')
        integration = self.git(self.repo, 'diff')
        self.owned = self.root / 'owned'
        self.owned.mkdir()
        for name in build.OWNED:
            (self.owned / name).write_bytes(integration if name == 'integration.patch' else b'fixture\n')
        for module in (build, __import__('apply_integration')):
            for name, value in [('PIN', pin), ('HERE', self.owned)]:
                p = patch.object(module, name, value)
                p.start()
                self.addCleanup(p.stop)
        self.real_run = subprocess.run

    @staticmethod
    def git(repo, *args):
        return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL)

    def fake_run(self, command, **kwargs):
        # check_output uses run too; retain real git semantics.
        if command[0] != 'cmake':
            return self.real_run(command, **kwargs)
        kwargs['stdout'].write(('simulated ' + repr(command)).encode())
        if command[1] == '-S':
            self.output = Path(command[2])
            self.hip = '-DGGML_HIP=ON' in command
            (self.output / 'build').mkdir()
            (self.output / 'build/CMakeCache.txt').write_text('\n'.join(command))
        else:
            bindir = self.output / 'build/bin'
            bindir.mkdir()
            files = ['am-control', 'libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so']
            if 'am-driver' in (self.output / 'CMakeLists.txt').read_text():
                files += ['am-driver']
            if self.hip:
                files += ['libggml-hip.so']
            for name in files:
                (bindir / name).write_text('simulated artifact ' + name)
        return subprocess.CompletedProcess(command, 0)

    def make(self, variant='patched', backend='cpu'):
        with patch.object(build.subprocess, 'run', self.fake_run):
            return build.build(self.source, self.root / 'output', variant, backend,
                               arch='gfx90a' if backend == 'hip' else None)

    def test_patched_build_binds_inputs_and_full_targets(self):
        path = self.make()
        m = build.verify(path)
        self.assertEqual(m['variant'], 'patched')
        self.assertEqual(m['source_state']['commit'], build.PIN)
        self.assertEqual(set(m['tooling_sha256']), set(build.OWNED))
        self.assertIn('build/bin/am-driver', m['artifacts_sha256'])
        self.assertIn('build/bin/libggml-cpu.so', m['artifacts_sha256'])
        self.assertIn('-DGGML_BACKEND_DL=OFF', m['commands'][0])
        self.assertNotIn('--target', m['commands'][1])  # Full kernel, including shared backends.
        cmake = (path.parent / 'CMakeLists.txt').read_text()
        includes = next(line for line in cmake.splitlines() if line.startswith('target_include_directories(am-driver'))
        self.assertLess(includes.index(str(self.source / 'src')), includes.index(str(path.parent / 'tooling')))

    @unittest.skipUnless(shutil.which('cmake') and shutil.which('c++'), 'native toolchain required')
    def test_real_link_resolves_direct_cpu_dependency(self):
        # Reproduce the pinned fused-model dependency with tiny real libraries.
        # MODULE mode fails the executable link; the generated wrapper must pass.
        (self.repo / 'CMakeLists.txt').write_text("""cmake_minimum_required(VERSION 3.22)
project(link_fixture LANGUAGES CXX)
add_library(ggml-base SHARED base.cpp)
add_library(ggml SHARED base.cpp)
if(GGML_BACKEND_DL)
  add_library(ggml-cpu MODULE cpu.cpp)
  add_dependencies(ggml ggml-cpu)
else()
  add_library(ggml-cpu SHARED cpu.cpp)
  target_link_libraries(ggml PUBLIC ggml-cpu)
endif()
add_library(llama SHARED model.cpp)
target_link_libraries(llama PUBLIC ggml)
""")
        (self.repo / 'base.cpp').write_text('int base() { return 0; }\n')
        (self.repo / 'cpu.cpp').write_text('int cpu_symbol() { return 7; }\n')
        (self.repo / 'model.cpp').write_text('int cpu_symbol(); int model() { return cpu_symbol(); }\n')
        self.git(self.repo, 'add', 'CMakeLists.txt', 'base.cpp', 'cpu.cpp', 'model.cpp')
        self.git(self.repo, 'commit', '-qm', 'native link fixture')
        pin = self.git(self.repo, 'rev-parse', 'HEAD').strip().decode()
        self.git(self.source, 'checkout', '--detach', pin)
        (self.owned / 'control.cpp').write_text('int model(); int main() { return model() == 7 ? 0 : 1; }\n')
        with patch.object(build, 'PIN', pin):
            def reaping_native(command, **kwargs):
                if command[0] == 'cmake' and command[1] == '--build':
                    shutil.rmtree(self.owned)
                return self.real_run(command, **kwargs)
            with patch.object(build.subprocess, 'run', reaping_native):
                path = build.build(self.source, self.root / 'output', 'baseline', 'cpu')
            shutil.copytree(path.parent / 'tooling', self.owned)
            build.verify(path)
            subprocess.run([str(path.parent / 'build/bin/am-control')], check=True)
            # Demonstrate the same fixture catches the actual old failure mode.
            broken = self.root / 'module-build'
            subprocess.run(['cmake', '-S', str(path.parent), '-B', str(broken),
                            '-DBUILD_SHARED_LIBS=ON', '-DGGML_BACKEND_DL=ON'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            result = subprocess.run(['cmake', '--build', str(broken), '--parallel', '4'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('undefined reference', result.stderr)
            self.assertIn('cpu_symbol', result.stderr)

    def test_snapshot_tampering_refused(self):
        path = self.make()
        (path.parent / 'tooling/control.cpp').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'snapshot changed'):
            build.verify(path)

    def test_lane_reaped_between_configure_and_compile(self):
        def reaping(command, **kwargs):
            if command[0] == 'cmake' and command[1] == '--build':
                shutil.rmtree(self.owned)
                wrapper = (self.root / 'output/CMakeLists.txt').read_text()
                self.assertNotIn(str(self.owned), wrapper)
                self.assertIn(str(self.root / 'output/tooling/control.cpp'), wrapper)
            return self.fake_run(command, **kwargs)
        with patch.object(build.subprocess, 'run', reaping):
            path = build.build(self.source, self.root / 'output', 'patched', 'cpu')
        build.verify(path, current_tooling=False)
        # A fresh lane can validate the exact original inputs after rotation.
        shutil.copytree(path.parent / 'tooling', self.owned)
        build.verify(path)

    def test_baseline_build_has_no_experimental_driver(self):
        m = build.verify(self.make('baseline'))
        self.assertNotIn('build/bin/am-driver', m['artifacts_sha256'])
        self.assertFalse(self.git(self.source, 'diff'))

    def test_hip_requires_and_binds_backend(self):
        m = build.verify(self.make(backend='hip'))
        self.assertEqual(m['architecture'], 'gfx90a')
        self.assertIn('build/bin/libggml-hip.so', m['artifacts_sha256'])
        (self.root / 'output/build/bin/libggml-hip.so').unlink()
        with self.assertRaises(FileNotFoundError):
            build.verify(self.root / 'output/BUILD.json')

    def test_artifact_mutation_refused(self):
        path = self.make()
        (path.parent / 'build/bin/am-driver').write_text('stale')
        with self.assertRaisesRegex(ValueError, 'artifacts changed'):
            build.verify(path)

    def test_tooling_mutation_refused(self):
        path = self.make()
        (self.owned / 'control.cpp').write_text('different')
        with self.assertRaisesRegex(ValueError, 'tooling changed'):
            build.verify(path)

    def test_source_mutation_refused(self):
        path = self.make()
        (self.source / 'src/code').write_text('other patch')
        with self.assertRaisesRegex(ValueError, 'tracked source'):
            build.verify(path)

    def test_installed_header_mutation_refused(self):
        path = self.make()
        (self.source / 'src/native_runtime.h').write_text('other')
        with self.assertRaisesRegex(ValueError, 'header mismatch'):
            build.verify(path)

    def test_ignored_injection_refused(self):
        (self.source / 'ignored').write_text('injected')
        with self.assertRaisesRegex(ValueError, 'untracked/ignored'):
            self.make()
        self.assertFalse((self.source / 'src/native_runtime.h').exists())

    def test_main_checkout_refused(self):
        with self.assertRaisesRegex(ValueError, 'detached'):
            build.build(self.repo, self.root / 'output', 'baseline', 'cpu')

    def test_reused_output_and_in_source_output_refused(self):
        for output in (self.source / 'out', self.repo):
            with self.assertRaisesRegex(ValueError, 'new output'):
                build.build(self.source, output, 'baseline', 'cpu')

    def test_failed_build_never_emits_manifest(self):
        def fail(command, **kwargs):
            if command[0] == 'cmake':
                raise subprocess.CalledProcessError(1, command)
            return self.real_run(command, **kwargs)
        with patch.object(build.subprocess, 'run', fail):
            with self.assertRaises(subprocess.CalledProcessError):
                build.build(self.source, self.root / 'output', 'patched', 'cpu')
        self.assertFalse((self.root / 'output/BUILD.json').exists())

    def test_external_library_symlink_refused(self):
        path = self.make()
        lib = path.parent / 'build/bin/libllama.so'
        lib.unlink()
        lib.symlink_to(self.owned / 'driver.cpp')
        with self.assertRaisesRegex(ValueError, 'self-contained'):
            build.verify(path)

    def test_invalid_settings_refused_before_mutation(self):
        for kwargs in ({'jobs': 0}, {'jobs': 65}, {'backend': 'hip'}, {'backend': 'hip', 'arch': 'gfx90a;bad'}):
            settings = dict(variant='patched', backend='cpu')
            settings.update(kwargs)
            with self.assertRaises(ValueError):
                build.build(self.source, self.root / 'output', **settings)
        self.assertFalse((self.source / 'src/native_runtime.h').exists())

    def test_build_log_mutation_refused(self):
        path = self.make()
        (path.parent / 'build-0.log').write_text('substituted')
        with self.assertRaisesRegex(ValueError, 'logs changed'):
            build.verify(path)

    def test_configure_cache_mutation_refused(self):
        path = self.make()
        (path.parent / 'build/CMakeCache.txt').write_text('different flags')
        with self.assertRaisesRegex(ValueError, 'artifacts changed'):
            build.verify(path)

    def test_no_manifest_on_midbuild_tooling_mutation(self):
        def changing(command, **kwargs):
            r = self.fake_run(command, **kwargs)
            if command[0] == 'cmake' and command[1] == '--build':
                (self.owned / 'driver.cpp').write_text('changed during compilation')
            return r
        with patch.object(build.subprocess, 'run', changing):
            with self.assertRaisesRegex(ValueError, 'during build'):
                build.build(self.source, self.root / 'output', 'patched', 'cpu')
        self.assertFalse((self.root / 'output/BUILD.json').exists())


if __name__ == '__main__':
    unittest.main()

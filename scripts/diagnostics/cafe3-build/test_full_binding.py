"""Synthetic full receipts must bind markers to the linked server implementation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def load(folder):
    spec = importlib.util.spec_from_file_location(folder, Path(__file__).parents[1] / folder / 'driver.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FullBindingTest(unittest.TestCase):
    def test_legacy_supervisor_protocol_is_refused_before_source_or_command(self):
        for folder in ('cafe3-build', 'cafe3-hip-build'):
            m = load(folder)
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'inputs.json').write_text('{}')
                with patch.object(m, 'D', root), patch.object(m.subprocess, 'check_output') as command:
                    with self.assertRaisesRegex(ValueError, 'supervisor protocol'):
                        m.inputs()
                    command.assert_not_called()

    def test_cpu_and_hip_full_component_binding(self):
        for folder in ('cafe3-build', 'cafe3-hip-build'):
            m = load(folder)
            hip = folder == 'cafe3-hip-build'
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                run = root / 'runs/one'
                bindir = run / 'build/bin'
                bindir.mkdir(parents=True)
                libs = ['libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libllama-server-impl.so']
                if hip:
                    libs.append('libggml-hip.so')
                for name in ['llama-server', *libs]:
                    (bindir / name).write_bytes(b'fixture')
                cache = run / 'build/CMakeCache.txt'
                cache.write_text('GGML_HIP:BOOL=' + ('ON' if hip else 'OFF') + '\nGGML_BACKEND_DL:BOOL=OFF\nLLAMA_BUILD_UI:BOOL=OFF\nLLAMA_USE_PREBUILT_UI:BOOL=OFF\n' + (m.IQK_COMPAT + '\n' + m.CLANGXX + '\nCMAKE_HIP_ARCHITECTURES:STRING=gfx90a\n' if hip else ''))
                linkage = run / 'linkage.log'
                linkage.write_text('\n'.join(f'{name} => {bindir / name} (0x123)' for name in libs))
                r = dict(inputs={}, base=m.BASE, run=str(run), mode='build')
                def bind():
                    r['files'] = {str(p): m.digest(p) for p in run.rglob('*') if p.is_file()}
                def output(command, **kwargs):
                    if command[0] == 'nm':
                        return 'iqk_mul_mat T 0\nggml_iqk_try_mul_mat T 0\nggml_backend_cuda_reg T 0\n'
                    if Path(command[-1]).name == 'libggml-hip.so':
                        return b'gfx90a'
                    self.assertEqual(Path(command[-1]).name, 'libllama-server-impl.so')
                    return b'\n'.join(m.MARKERS)
                bind()
                with patch.object(m, 'D', root), patch.object(m, 'inputs', return_value={}), patch.object(m.subprocess, 'check_output', side_effect=output):
                    m.validate(r)
                    saved = r['files'].pop(str(bindir / 'llama-server'))
                    with self.assertRaisesRegex(ValueError, 'unbound build control'):
                        m.validate(r)
                    r['files'][str(bindir / 'llama-server')] = saved
                    del r['files'][str(bindir / 'libllama-server-impl.so')]
                    with self.assertRaisesRegex(ValueError, 'unbound compiled'):
                        m.validate(r)
                    bind()
                    linkage.write_text('\n'.join(f'{n} => {bindir / n} (0x123)' for n in libs if n != 'libllama-server-impl.so'))
                    bind()
                    with self.assertRaisesRegex(ValueError, 'missing required'):
                        m.validate(r)
                    cache.write_text(cache.read_text().replace('LLAMA_BUILD_UI:BOOL=OFF', 'LLAMA_BUILD_UI:BOOL=ON'))
                    bind()
                    with self.assertRaisesRegex(ValueError, 'UI build'):
                        m.validate(r)


    def test_versioned_sonames_preserve_exact_identity_and_hash_custody(self):
        cases = ('valid-major', 'valid-full-version', 'missing-component', 'external',
                 'external-symlink', 'unbound', 'tampered', 'wrong-component',
                 'alias-mismatch', 'soname-mismatch', 'lookalike', 'malformed')
        for folder in ('cafe3-build', 'cafe3-hip-build'):
            for case in cases:
                with self.subTest(folder=folder, case=case), tempfile.TemporaryDirectory() as tmp:
                    m = load(folder)
                    root = Path(tmp)
                    run = root / 'runs/one'
                    bindir = run / 'build/bin'
                    bindir.mkdir(parents=True)
                    hip = folder == 'cafe3-hip-build'
                    libs = ['libllama.so', 'libggml.so', 'libggml-base.so',
                            'libggml-cpu.so', 'libllama-server-impl.so']
                    if hip:
                        libs.append('libggml-hip.so')
                    suffix = '.0.0.1' if case == 'valid-full-version' else '.0'
                    for name in libs:
                        (bindir / (name + suffix)).write_bytes(name.encode())
                        (bindir / name).symlink_to(name + suffix)
                    (bindir / 'llama-server').write_bytes(b'server')
                    cache = run / 'build/CMakeCache.txt'
                    cache.write_text('GGML_HIP:BOOL=' + ('ON' if hip else 'OFF') +
                                     '\nGGML_BACKEND_DL:BOOL=OFF\nLLAMA_BUILD_UI:BOOL=OFF\n'
                                     'LLAMA_USE_PREBUILT_UI:BOOL=OFF\n' +
                                     (m.IQK_COMPAT + '\n' + m.CLANGXX +
                                      '\nCMAKE_HIP_ARCHITECTURES:STRING=gfx90a\n' if hip else ''))
                    lines = {name: f'{name}{suffix} => {bindir / (name + suffix)} (0x123)'
                             for name in libs}
                    victim = 'libggml-cpu.so' if hip else 'libggml-base.so'
                    target = bindir / (victim + suffix)
                    error = None
                    if case == 'missing-component':
                        del lines[victim]
                        error = 'missing required'
                    elif case in ('external', 'external-symlink'):
                        outside = root / 'outside.so'
                        outside.write_bytes(target.read_bytes())
                        if case == 'external':
                            lines[victim] = f'{victim}{suffix} => {outside} (0x123)'
                        else:
                            target.unlink()
                            target.symlink_to(outside)
                        error = 'nonlocal/unbound'
                    elif case == 'wrong-component':
                        lines[victim] = f'{victim}{suffix} => {bindir / ("libggml.so" + suffix)} (0x123)'
                        error = 'identity mismatch'
                    elif case == 'alias-mismatch':
                        alias = bindir / victim
                        alias.unlink()
                        alias.symlink_to('libggml.so' + suffix)
                        error = 'identity mismatch'
                    elif case == 'soname-mismatch':
                        (bindir / (victim + '.1')).symlink_to('libggml.so' + suffix)
                        lines[victim] = f'{victim}.1 => {target} (0x123)'
                        error = 'identity mismatch'
                    elif case == 'lookalike':
                        lines[victim] = f'{victim}.0evil => {target} (0x123)'
                        error = 'malformed library'
                    elif case == 'malformed':
                        lines[victim] = f'{victim}{suffix} {target}'
                        error = 'malformed library'
                    linkage = run / 'linkage.log'
                    linkage.write_text('\n'.join(lines.values()))
                    record = dict(inputs={}, base=m.BASE, run=str(run), mode='build',
                                  files={str(p.resolve()): m.digest(p) for p in run.rglob('*')
                                         if p.is_file() and p.resolve().is_relative_to(run)})
                    if case == 'unbound':
                        del record['files'][str(target)]
                        error = 'nonlocal/unbound'
                    elif case == 'tampered':
                        target.write_bytes(b'tampered')
                        error = 'artifact mismatch'
                    def output(command, **kwargs):
                        if command[0] == 'nm':
                            return 'iqk_mul_mat T 0\nggml_iqk_try_mul_mat T 0\nggml_backend_cuda_reg T 0\n'
                        if Path(command[-1]).name.startswith('libggml-hip.so'):
                            return b'gfx90a'
                        return b'\n'.join(m.MARKERS)
                    with patch.object(m, 'D', root), patch.object(m, 'inputs', return_value={}), patch.object(m.subprocess, 'check_output', side_effect=output):
                        if error:
                            with self.assertRaisesRegex(ValueError, error):
                                m.validate(record)
                        else:
                            m.validate(record)


if __name__ == '__main__':
    unittest.main()

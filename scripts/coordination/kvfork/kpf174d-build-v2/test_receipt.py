#!/usr/bin/env python3
"""Regression tests for receipt compiler and CMake option binding."""
import hashlib
import importlib.util
import pathlib

import pytest


HERE = pathlib.Path(__file__).parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


complete = load_module('kpf174d_complete', HERE / 'complete.py')
proof = load_module('kpf174d_proof', HERE / 'proof.py')


def test_compiler_record_must_cover_all_expected_paths(tmp_path):
    compiler = tmp_path / 'cc'
    compiler.write_bytes(b'compiler')

    with pytest.raises(ValueError, match='compiler set mismatch'):
        complete.verify_compilers({}, expected_paths=[str(compiler)])


def test_compiler_digest_must_match_current_file(tmp_path):
    compiler = tmp_path / 'cc'
    compiler.write_bytes(b'compiler')
    receipt = {str(compiler): hashlib.sha256(b'compiler').hexdigest()}
    complete.verify_compilers(receipt, expected_paths=[str(compiler)])

    compiler.write_bytes(b'replaced compiler')
    with pytest.raises(ValueError, match='compiler missing or digest mismatch'):
        complete.verify_compilers(receipt, expected_paths=[str(compiler)])


def test_compiler_path_must_still_exist(tmp_path):
    compiler = tmp_path / 'clang++'
    compiler.write_bytes(b'compiler')
    receipt = {str(compiler): hashlib.sha256(b'compiler').hexdigest()}
    compiler.unlink()

    with pytest.raises(ValueError, match='required compiler missing'):
        complete.verify_compilers(receipt, expected_paths=[str(compiler)])


def test_proof_compiler_receipt_uses_validator_path_keys(tmp_path):
    compiler = tmp_path / 'cc'
    compiler.write_bytes(b'compiler')
    receipt = proof.compiler_receipt([str(compiler)])

    assert set(proof.COMPILER_PATHS) == set(complete.COMPILER_PATHS)
    assert set(receipt) == {str(compiler)}
    complete.verify_compilers(receipt, expected_paths=[str(compiler)])


def test_cache_comparison_rejects_extra_boolean_options():
    with pytest.raises(SystemExit, match=r'"extra": \["GGML_NEW_SWITCH"\]'):
        proof.compare_caches({'GGML_HIP': 'ON'}, {'GGML_HIP': 'ON', 'GGML_NEW_SWITCH': 'ON'})

# KPF-64 coverage-key correction, review candidate

The successor coverage audit treats Python `bool` as an integer, so a JSON `true` or `false` turn index can falsely cover turn 1 or 0. `coverage-bool.patch` rejects Boolean indices while preserving integer indices; `cohort_audit.py` is the patched isolated copy and `test_bool_coverage.py` exercises the two false-coverage cases and valid integer controls. The source file before patch had SHA-256 `2576f5c24ff8cc81b1869967df925ea256e050bd0a7126f32331fa80d1c1364d`.

Run `python3 -m unittest discover -s docs/reports/kv-cache/kpf64-coverage-key-20261104 -p test_bool_coverage.py`. This is not integrated into research, a sealed launcher, or an inference row; it does not establish any cohort verdict. The lane GitNexus index was unavailable, so upstream impact and owner integration remain required.

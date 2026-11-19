"""Bind one offline setup replacement plus reporting-only pytest suffix.

The exact official script is hashed first. The original selectors, test contents,
patch application, official parser and verdict rules remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re

INSTALL = 'python -m pip install -e .[test]'
CHECK = ("python -c 'from pathlib import Path; import sphinx, pytest, tox; "
         "assert Path(sphinx.__file__).resolve().is_relative_to(Path(\"/testbed\"))' "
         "&& python -m pip check || exit 90")
_FORBIDDEN = re.compile(r'^\s*(?:(?:python\S*\s+-m\s+)?pip\s+install|conda\s+install|curl\b|wget\b)', re.M)


def digest_lines(lines: list[str]) -> str:
    return hashlib.sha256(json.dumps(lines, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def make_offline_eval(lines: list[str], expected_original: str, image_id: str, expected_image: str) -> tuple[list[str], dict]:
    """Replace exactly one known setup command after verifying script and image pins."""
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        raise ValueError('script must be a list of strings')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', expected_image or '') or image_id != expected_image:
        raise ValueError('derived image identity mismatch')
    original = digest_lines(lines)
    if not re.fullmatch(r'[0-9a-f]{64}', expected_original or '') or original != expected_original:
        raise ValueError('official script identity mismatch')
    if lines.count(INSTALL) != 1:
        raise ValueError('expected exactly one official setup command')
    index = lines.index(INSTALL)
    out = list(lines)
    out[index] = CHECK
    if any(_FORBIDDEN.search(line) for line in out):
        raise ValueError('another install or fetch remains in the generated script')
    official_test = 'tox --current-env -epy39 -v -- tests/roots/test-ext-autodoc/target/private.py tests/test_ext_autodoc_private_members.py'
    if lines.count(official_test) != 1:
        raise ValueError('expected exact single official Sphinx test command')
    test_index = lines.index(official_test)
    out[test_index] = official_test + ' -rA --color=no'
    return out, {'official_script_sha256': original, 'offline_script_sha256': digest_lines(out),
                 'setup_index': index, 'derived_image_id': image_id,
                 'reporting_command_index': test_index, 'reporting_only_suffix': '-rA --color=no', 'scope': 'exact offline setup substitution and reporting-only pytest suffix; selectors, patches and parser unchanged'}

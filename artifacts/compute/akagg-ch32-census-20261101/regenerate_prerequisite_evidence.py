#!/usr/bin/env python3
"""Read-only CH-32 prerequisite evidence. No index, checkout, refs or source changes.

Usage: python3 regenerate_prerequisite_evidence.py SOURCE_DIR OUTPUT_DIR
SOURCE_DIR supplies pinned SUMMARY.json and the 13 retained *.patch-check.log files.
Requires the original llama.cpp object store and all 13 pinned commits locally.
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = '/mnt/raid0/llm/llama.cpp'
BASE = 'c72ec82f5417bb2937310326120f149b665e8400'
source, out = map(pathlib.Path, sys.argv[1:3])
out.mkdir(parents=True, exist_ok=True)
groups = json.loads((source / 'SUMMARY.json').read_text())['groups']

def git(*args, check=True):
    return subprocess.run(['git', '-C', REPO, *args], text=True, capture_output=True, check=check)

def write(name, value):
    (out / name).write_text(json.dumps(value, indent=2) + '\n')

# Missing-file creator is evidence for upstream patch context; a hand-port may differ.
missing = {}
for key, info in groups.items():
    commit = info['commit']
    log = (source / (key + '.patch-check.log')).read_text()
    paths = re.findall(r'^error: (.*?): does not exist in index$', log, re.M)
    entries = []
    for path in paths:
        creator = git('log', '--first-parent', '--diff-filter=A', '--format=%H %s', '-1', commit + '^', '--', path).stdout.strip()
        sha = creator.split(' ', 1)[0] if creator else ''
        exists = git('cat-file', '-e', f'{BASE}:{path}', check=False).returncode == 0
        entries.append({'path': path, 'latest_first_parent_add_before_target': creator or None, 'exists_at_c5': exists,
                        'creator_is_requested_group_tip': next((g for g, v in groups.items() if v['commit'] == sha), None)})
    missing[key] = {'commit': commit, 'missing_path_creation_evidence': entries}
write('MISSING-PATH-PREREQS.json', missing)

# Text scan of feature-patch additions against public headers (not compiled evidence).
base_headers = git('grep', '-h', '-I', '-E', 'ggml_[a-zA-Z0-9_]+', BASE, '--', 'ggml/include', 'include').stdout
available = set(re.findall(r'\bggml_[A-Za-z0-9_]+\b', base_headers))
scan = {}
for key, info in groups.items():
    commit = info['commit']
    diff = git('diff', commit + '^', commit, '--', '.').stdout
    added = '\n'.join(line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
    tokens = sorted(set(re.findall(r'\bggml_[A-Za-z0-9_]+\b', added)))
    scan[key] = {'introduced_ggml_tokens': tokens, 'absent_from_c5_public_headers_tokens': sorted(set(tokens) - available),
                 'warning': 'Text token scan only; misses macros/types, comments may create false positives, and header declaration presence does not establish ABI or required behavior.'}
write('GGML-API-TOKEN-SCAN.json', scan)

def declarations(rev):
    result = {}
    paths = git('ls-tree', '-r', '--name-only', rev, 'ggml/include', 'include').stdout.splitlines()
    for path in paths:
        if not path.endswith('.h'):
            continue
        text = git('show', rev + ':' + path).stdout
        text = re.sub(r'/\*.*?\*/|//[^\n]*', ' ', text, flags=re.S)
        for match in re.finditer(r'\b(ggml_[A-Za-z0-9_]+)\s*\(([^;{}]*)\)\s*;', text, flags=re.S):
            result.setdefault(match.group(1), []).append({'file': path, 'args': re.sub(r'\s+', ' ', match.group(2)).strip()})
    return result

base_decls = declarations(BASE)
signatures = {}
for key, info in groups.items():
    upstream_decls = declarations(info['commit'] + '^')
    tokens = set(scan[key]['introduced_ggml_tokens'])
    both = sorted(tokens & base_decls.keys() & upstream_decls.keys())
    differences = {name: {'c5': base_decls[name], 'upstream_parent': upstream_decls[name]}
                   for name in both if base_decls[name] != upstream_decls[name]}
    signatures[key] = {'compared_function_tokens': both, 'non_function_or_not_extracted': sorted(tokens - set(both)),
                       'differences': differences,
                       'method': 'Regex of comments-stripped .h declarations compares argument text, not return type, struct layout, enums/macros, ABI or semantics.'}
write('GGML-API-SIGNATURE-TEXT.json', signatures)

edges = []
for a, va in groups.items():
    for b, vb in groups.items():
        if a != b and git('merge-base', '--is-ancestor', va['commit'], vb['commit'], check=False).returncode == 0:
            edges.append([a, b])
write('UPSTREAM-ANCESTRY-EDGES.json', {'edges': edges,
    'scope': 'Complete upstream commit ancestry is ordering evidence only; it does not prove individual patches are prerequisite or sufficient for a hand-port.'})

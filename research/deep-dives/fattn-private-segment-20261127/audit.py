#!/usr/bin/env python3
"""Join gfx90a dispatch rows to notes and ISA from the exact host ELF."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile

MAGIC = b'__CLANG_OFFLOAD_BUNDLE__'
TARGET = 'hipv4-amdgcn-amd-amdhsa--gfx90a'
LLVM = Path('/opt/rocm/llvm/bin')
ATTENTION = re.compile(r'flash_attn|gv_fattn|gv_rf_kernel|gv_merge\d?_kernel|gv7_(?:merge_)?kernel')
FIELDS = ('agpr_count', 'vgpr_count', 'sgpr_count', 'sgpr_spill_count', 'vgpr_spill_count',
          'private_segment_fixed_size', 'group_segment_fixed_size', 'name', 'symbol')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs)


def hip_objects(lib, data):
    sections = command('readelf', '-SW', lib)
    section = re.search(r'\.hip_fatbin\s+PROGBITS\s+[0-9a-f]+\s+([0-9a-f]+)\s+([0-9a-f]+)', sections)
    start, size = (int(x, 16) for x in section.groups())
    end = start + size
    for bundle in re.compile(MAGIC).finditer(data, start, end):
        cur = bundle.end()
        count, = struct.unpack_from('<Q', data, cur)
        cur += 8
        for _ in range(count):
            relative, extent, name_length = struct.unpack_from('<QQQ', data, cur)
            cur += 24
            target = data[cur:cur + name_length].decode('ascii')
            cur += name_length
            if target == TARGET:
                offset = bundle.start() + relative
                assert offset + extent <= end and data[offset:offset + 4] == b'\x7fELF', (lib, offset, extent)
                yield offset, data[offset:offset + extent]


def kernel_metadata(notes):
    for block in re.split(r'(?m)^  - ', notes)[1:]:
        values = {}
        for field in FIELDS:
            match = re.search(rf'(?m)^(?:    )?\.{field}:[ \t]+(\S+)', block)
            if match:
                values[field] = int(match[1]) if field not in ('name', 'symbol') else match[1]
        if ATTENTION.search(values.get('name', '')):
            assert set(values) == set(FIELDS), values
            yield values


def traces_for(cases, root, lib, library_sha):
    traces = []
    names = set()
    for case in cases:
        path = root / case['trace']
        raw = path.read_bytes()
        rows = csv.DictReader(raw.decode().splitlines())
        supplemental = {}
        if 'panel' in case:
            request_raw = path.with_name('requests.json').read_bytes()
            run_raw = path.with_name('run.json').read_bytes()
            assert json.loads(run_raw)['identity'][str(lib)] == library_sha
            panel, = [x for x in json.loads(request_raw) if x['panel'] == case['panel']]
            assert all(x['hip_store_mapped'] and x['vram_b'] > 0 and x['pid'] in x['kfd_pids']
                       for x in panel['residency']) and panel['residency'], panel['panel']
            windows = [(req['start_ns'], req['end_ns']) for req in panel['requests']]
            rows = (row for row in rows if any(begin <= int(row['Start_Timestamp']) and
                                               int(row['End_Timestamp']) <= end for begin, end in windows))
            supplemental = {'requests_sha256': sha(request_raw), 'run_sha256': sha(run_raw),
                            'input_token_counts': [r['input_token_count'] for r in panel['requests']]}
        groups = Counter()
        auxiliaries = Counter()
        duration = Counter()
        for row in rows:
            name = row['Kernel_Name']
            if not ATTENTION.search(name):
                continue
            key = (name, int(row['Kernel_Id']), int(row['Private_Segment_Size']), int(row['Group_Segment_Size']))
            if case.get('main_only') and ('mask_to_KV' in name or 'combine_results' in name):
                auxiliaries[key] += 1
                continue
            groups[key] += 1
            duration[key] += int(row['End_Timestamp']) - int(row['Start_Timestamp'])
        assert groups, path
        names.update(name for name, *_ in groups)
        traces.append({**case, **supplemental, 'trace_sha256': sha(raw), 'dispatches': [
            {'trace_symbol': name, 'kernel_id': kernel_id, 'hits': hits, 'private_bytes': private,
             'group_bytes': group, 'sum_duration_ns': duration[(name, kernel_id, private, group)]}
            for (name, kernel_id, private, group), hits in sorted(groups.items())], 'unjoined_auxiliary_dispatches': [
                {'trace_symbol': name, 'kernel_id': kernel_id, 'hits': hits, 'private_bytes': private, 'group_bytes': group}
                for (name, kernel_id, private, group), hits in sorted(auxiliaries.items())]})
    return traces, names


def check_library(store, lib, sha256):
    expected = [line.split()[0] for line in (store / 'SHA256SUMS').read_text().splitlines()
                if line.split()[-1].removeprefix('./') == f'bin/{lib.name}']
    assert expected == [sha256], (lib, expected, sha256)


def obj_inventory(lib, data):
    for offset, co in hip_objects(lib, data):
        if not ATTENTION.search(co.decode('latin1')):
            continue
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / 'object.hsaco'
            path.write_bytes(co)
            notes = command(LLVM / 'llvm-readelf', '-n', path)
            assert 'amdgcn-amd-amdhsa--gfx90a' in notes, offset
            for meta in kernel_metadata(notes):
                yield offset, co, meta


def isa_instructions(isa, symbol):
    source = isa.split(f'<{symbol}>:\n', 1)[1]
    return [line.partition('//')[0].strip() for line in source.splitlines() if re.match(r'^\s+\w', line)]


def isa_summary(co_path, meta):
    symbol = meta['name']
    isa = command(LLVM / 'llvm-objdump', '-d', f'--disassemble-symbols={symbol}', co_path)
    assert f'<{symbol}>:' in isa and re.search(r'^\s+s_endpgm\b', isa, re.M), symbol
    instructions = isa_instructions(isa, symbol)
    scratch = [line for line in instructions if re.match(r'(?:scratch_(?:store|load)|buffer_(?:store|load))', line)]
    flat = sum(line.startswith(('flat_store', 'flat_load')) for line in instructions)
    calls = sum(line.startswith(('s_swappc_', 's_setpc_')) for line in instructions)
    return {'instructions': len(instructions), 'flat_memory_instructions': flat, 'device_calls': calls,
            'buffer_or_scratch_instruction_counts': dict(Counter(line.split()[0] for line in scratch)),
            'buffer_or_scratch_instructions': scratch, 'prologue': instructions[:12] if scratch else []}


def audit(build, trace_root):
    store = Path(build['store'])
    lib = (store / 'bin/libggml-hip.so').resolve()
    data = lib.read_bytes()
    library_sha = sha(data)
    check_library(store, lib, library_sha)
    link_notes = command('readelf', '-n', lib)
    build_id = re.search(r'Build ID: ([0-9a-f]+)', link_notes)
    traces, trace_names = traces_for(build['cases'], trace_root, lib, library_sha)
    objects = defaultdict(list)
    meta_by_offset = {}
    for offset, co, meta in obj_inventory(lib, data):
        objects[meta['name']].append(offset)
        meta_by_offset.setdefault(offset, (co, {}))[1][meta['name']] = meta
    demangled = command('c++filt', input='\n'.join(objects) + '\n').splitlines()
    lookup = {name: mangled for mangled, name in zip(objects, demangled, strict=True)}
    tus = store / 'ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/__/ggml-cuda'
    selected_objects = {}
    for symbol_fragment, relative_tu in build.get('translation_units', {}).items():
        tu = tus / relative_tu
        _, payload = next(hip_objects(tu, tu.read_bytes()))
        selected_objects[symbol_fragment] = (relative_tu, sha(payload))
    matches = {}
    bindings = {}
    for raw_name in trace_names:
        name = raw_name.removesuffix('.kd')
        mangled = name if name in objects else lookup.get(name)
        assert mangled in objects, (raw_name, mangled)
        offsets = objects[mangled]
        if len(offsets) != 1:
            (relative_tu, tu_hash), = [binding for key, binding in selected_objects.items() if key in raw_name]
            offsets = [offset for offset in offsets if sha(meta_by_offset[offset][0]) == tu_hash]
            bindings[mangled] = relative_tu
        offset, = offsets
        matches[raw_name] = mangled
        objects[mangled] = offsets
    inspected = {}
    with tempfile.TemporaryDirectory() as tempdir:
        for mangled in sorted(set(matches.values())):
            offset, = objects[mangled]
            co, all_meta = meta_by_offset[offset]
            meta = all_meta[mangled]
            co_path = Path(tempdir) / 'object.hsaco'
            co_path.write_bytes(co)
            inspected[mangled] = {**meta, 'code_object_sha256': sha(co), 'code_object_file_offset': offset,
                                  'code_object_bytes': len(co), 'isa': isa_summary(co_path, meta),
                                  'translation_unit': bindings.get(mangled)}
    for trace in traces:
        for dispatch in trace['dispatches']:
            mangled = matches[dispatch['trace_symbol']]
            meta = inspected[mangled]
            assert dispatch['private_bytes'] == meta['private_segment_fixed_size'], dispatch
            assert dispatch['group_bytes'] >= meta['group_segment_fixed_size'], dispatch
            dispatch['mangled_symbol'] = mangled
    negative_controls = []
    for fragment in build.get('negative_controls', []):
        symbol, = [name for name in objects if fragment in name]
        offset, = objects[symbol]
        co, all_meta = meta_by_offset[offset]
        with tempfile.TemporaryDirectory() as tempdir:
            co_path = Path(tempdir) / 'object.hsaco'
            co_path.write_bytes(co)
            isa = command(LLVM / 'llvm-objdump', '-d', f'--disassemble-symbols={symbol}', co_path)
            symtab = command(LLVM / 'llvm-readelf', '-sW', co_path)
            trap_handler, = [line.strip() for line in symtab.splitlines() if '_ZL14no_device_code' in line]
        negative_controls.append({'metadata': all_meta[symbol], 'code_object_sha256': sha(co),
                                  'code_object_file_offset': offset, 'no_device_code_symbol': trap_handler,
                                  'isa': isa_instructions(isa, symbol)})
    return {'negative_controls': negative_controls, 'label': build['label'], 'source_commit': build['commit'], 'hip_sha256': library_sha,
            'host_build_id': build_id[1] if build_id else None, 'library': str(lib), 'kernels': inspected, 'traces': traces}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    case_spec = json.loads(args.cases.read_text())
    evidence = {'tool': command(LLVM / 'llvm-objdump', '--version').splitlines()[0],
                'target': TARGET, 'builds': [audit(build, Path(case_spec['trace_root'])) for build in case_spec['builds']]}
    args.report.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()

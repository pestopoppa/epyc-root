"""Bind serialized native arms to the retained sequential execution evidence."""
import json
import re
from pathlib import Path


def validate_arm_order(data, run, expected_bins):
    """Refuse incomplete, reordered or contradictory native evidence; no grading."""
    run = Path(run)
    if set(expected_bins) != {'P', 'C'} or expected_bins['P'] == expected_bins['C']:
        raise ValueError('distinct pinned P/C binaries required')
    expected = [f'{i}{"P" if i % 2 else "C"}' for i in range(1, 31)]
    arms = data.get('arms')
    if data.get('kind') != 'mtp' or not isinstance(arms, list) or len(arms) != 30:
        raise ValueError('original 30-arm result missing')
    by_tag = {}
    for arm in arms:
        if not isinstance(arm, dict):
            raise ValueError('invalid serialized arm')
        tag = arm.get('tag')
        if not isinstance(tag, str) or tag not in expected or tag in by_tag:
            raise ValueError('duplicate or unexpected serialized tag')
        by_tag[tag] = arm
    if set(by_tag) != set(expected):
        raise ValueError('missing serialized tag')
    events = []
    launches = {}
    deaths = {}
    for line in (run / 'ab_arms.log').read_text().splitlines():
        match = re.fullmatch(r'\[ab \d{2}:\d{2}:\d{2}Z\] arm (\S+): launching (.+)', line)
        if match:
            tag, binary = match.groups()
            events.append(('launch', tag))
            if tag in launches:
                raise ValueError('duplicate native launch')
            launches[tag] = binary
            continue
        match = re.fullmatch(r'\[ab \d{2}:\d{2}:\d{2}Z\] arm (\S+) server PID (\d+) verified dead', line)
        if match:
            tag, pid = match.groups()
            events.append(('dead', tag))
            if tag in deaths:
                raise ValueError('duplicate native death')
            deaths[tag] = int(pid)
            continue
        match = re.fullmatch(r'\[ab \d{2}:\d{2}:\d{2}Z\] arm (\S+) done \(\d+ s\)', line)
        if match:
            events.append(('done', match[1]))
    if events != [(phase, tag) for tag in expected for phase in ('launch', 'dead', 'done')]:
        raise ValueError('native execution sequence incomplete or changed')
    previous = None
    for tag in expected:
        arm = by_tag[tag]
        meta = json.loads((run / f'arm-{tag}.meta.json').read_text())
        if arm.get('meta') != meta or arm.get('arm') != tag[-1] or meta.get('tag') != tag or meta.get('arm') != tag[-1]:
            raise ValueError('serialized/native metadata mismatch')
        start = meta.get('started_epoch')
        if type(start) is not int or (previous is not None and start <= previous):
            raise ValueError('native start epochs not strictly increasing')
        previous = start
        binary = str(Path(meta.get('bin_dir', '')) / 'llama-server')
        argv = meta.get('cmdline')
        if binary != str(expected_bins[tag[-1]]) or launches[tag] != binary or not isinstance(argv, list) or not argv or argv[0] != binary:
            raise ValueError('native launch binary mismatch')
        if type(meta.get('pid')) is not int or meta['pid'] != deaths[tag]:
            raise ValueError('native death PID mismatch')
        if arm.get('probe_file') != f'arm-{tag}.probe.json':
            raise ValueError('native probe tag mismatch')
    return {'tags_in_execution_order': expected, 'provenance': 'native_launch_dead_done_log_and_exact_per_arm_metadata'}

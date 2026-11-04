#!/usr/bin/env python3
"""Prospective wrapper: report one native unit command as a JUnit case.

Run this *inside* scripts/ci/native_conformance.py capture. The outer capture
binds the command, selected case, clean repository revision, read set and this
wrapper; the case asserts only the command's exit status, not GPU residency.
Never apply it retrospectively to a saved log.
"""
import argparse
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--junit', required=True)
    p.add_argument('--case', required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    args = p.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or not args.case.strip():
        p.error('a named case and command are required')
    target = Path(args.junit)
    if target.exists():
        p.error('JUnit path must not already exist')
    try:
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        status, output = result.returncode, result.stdout
    except OSError as exc:
        status, output = 127, str(exc)
    skipped = status == 77
    suite = ET.Element('testsuite', name='lsa_native_unit', tests='1', failures=str(int(status != 0 and not skipped)), errors='0', skipped=str(int(skipped)))
    case = ET.SubElement(suite, 'testcase', classname='lsa_native_unit', name=args.case)
    if skipped:
        ET.SubElement(case, 'skipped', message='command exit 77')
    elif status != 0:
        ET.SubElement(case, 'failure', message=f'command exit {status}')
    ET.SubElement(case, 'system-out').text = output
    with target.open('xb') as f:
        ET.ElementTree(suite).write(f, encoding='utf-8', xml_declaration=True)
    return 0 if status in (0, 77) else 1


if __name__ == '__main__':
    raise SystemExit(main())

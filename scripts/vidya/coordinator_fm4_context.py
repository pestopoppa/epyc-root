#!/usr/bin/env python3
"""Assemble the interactive coordinator's FM-4 diagnostic review context."""

import argparse
import json

from adapters.fm4_gate_acceptance import PLANNER_CONSUMER
import loop_beliefs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--ledger')
    parser.add_argument('--index')
    parser.add_argument('--known-good')
    parser.add_argument('--read-log')
    parser.add_argument('--alarm-state')
    parser.add_argument('--alarm-config')
    parser.add_argument('--allow-stale-reader', action='store_true',
                        help='skip the checkout check for content-pinned isolated replay')
    args = parser.parse_args(argv)
    answer = loop_beliefs.prepare(
        PLANNER_CONSUMER, {'scope': 'lineup', 'stack_regime': 'fm4'},
        ledger=args.ledger, index_path=args.index, known_good=args.known_good,
        read_log=args.read_log, alarm_state=args.alarm_state, alarm_config=args.alarm_config,
        check_reader_checkout=not args.allow_stale_reader,
    )
    answer['reader_checkout_check'] = not args.allow_stale_reader
    print(json.dumps(answer, sort_keys=True, default=str))
    return loop_beliefs.EXIT_READY if answer['status'] == 'ready' else loop_beliefs.EXIT_REFUSED


if __name__ == '__main__':
    raise SystemExit(main())

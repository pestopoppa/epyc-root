#!/usr/bin/env python3
"""Safe entry point for the retained Q38-T7 runner.

The historical A/B phases send request-level ``speculative.n_max=0`` to the
same drafted server as their DFlash2 arms. Until separate server lifecycles and
warm-ups are implemented, refuse those phases before the original runner can
perform preflight, create results, or contact a server. Phase C is unchanged.
The historical result artifacts remain unchanged; the original file now also
refuses its unsafe A/B entrypoints.
"""

import argparse
import importlib
import sys


def _refuse(*_args, **_kwargs):
    raise RuntimeError(
        "KVU-16h: Q38-T7 phases A/B need separate drafted and no-draft "
        "server lifecycles and separately warmed prefixes"
    )


def main() -> int:
    # Match the original argparse option, including its accepted abbreviations
    # and last-value-wins behavior. It handles all other arguments itself.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--phases", default="A,B,C")
    args, _ = parser.parse_known_args()
    phases = {p.strip().upper() for p in args.phases.split(",") if p.strip()}
    if phases & {"A", "B"} and not ({"-h", "--help"} & set(sys.argv[1:])):
        parser.error("KVU-16h: phases A/B require separate server lifecycles")

    original = importlib.import_module("q38_t7")
    # Defense in depth if the original main is later changed or invoked by an
    # embedding caller after this entry point is initialized.
    original.phase_a = _refuse
    original.phase_b = _refuse
    return original.main()


if __name__ == "__main__":
    sys.exit(main())

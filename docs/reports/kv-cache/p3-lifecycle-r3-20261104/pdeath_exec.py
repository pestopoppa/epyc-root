"""Contain one native child against unexpected worker death, then exec it in place."""
import os
import sys
import parent_death


def main(args):
    if len(args) < 2:
        raise ValueError('expected parent PID and command')
    parent_death.contain(int(args[0]))
    os.execvp(args[1], args[1:])


if __name__ == '__main__':
    main(sys.argv[1:])

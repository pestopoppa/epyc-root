#!/usr/bin/env python3
"""Accept only a completed capture as the row result."""
import json, sys
try:
    with open(sys.argv[1], 'rb') as f:
        result = json.load(f)
    if result.get('status') != 'capture-complete':
        raise ValueError('capture incomplete')
except (OSError, ValueError, TypeError, AttributeError, IndexError):
    sys.exit(1)

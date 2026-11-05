#!/usr/bin/env python3
import sys
from qualify import ROOT, validate_result
try:
    validate_result(ROOT/'out/RESULT.json')
except Exception:
    sys.exit(1)

"""Run the original Astropy synthetic controls against the untouched prepared job."""
import unittest

from test_native_outcome import NativeOutcome


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeOutcome)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)

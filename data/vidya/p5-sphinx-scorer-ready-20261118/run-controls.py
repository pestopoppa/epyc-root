import unittest,sys,signal
signal.signal(signal.SIGTERM,lambda *_:sys.exit(75))
import test_native_outcome,test_parser_reporting
suite=unittest.TestSuite()
for case in [test_native_outcome.NativeOutcome,test_parser_reporting.Reporting]:
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)

import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('smoke_unit', Path(__file__).with_name('smoke_unit.py'))
smoke_unit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke_unit)


class OutputPathTests(unittest.TestCase):
    def test_attempt_scoped_and_fresh(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            attempt = root / 'native-attempts' / 'attempt-test'
            attempt.mkdir(parents=True)
            result = attempt / 'native-result.json'
            smoke_unit.validate_output(result, root)
            with self.assertRaises(ValueError):
                smoke_unit.validate_output(root / 'RESULT.json', root)
            result.write_text('{}')
            with self.assertRaises(ValueError):
                smoke_unit.validate_output(result, root)


if __name__ == '__main__':
    unittest.main()

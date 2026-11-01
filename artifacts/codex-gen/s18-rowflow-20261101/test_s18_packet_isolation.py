import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('s18_packet_job', PKG / 's18_job.py')
job = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = job
spec.loader.exec_module(job)


def test_dryrun_output_is_separate_and_never_satisfies_production_completion():
    with tempfile.TemporaryDirectory(prefix='s18-output-isolation-') as td:
        root = Path(td)
        dry = job.output_dir_for(root, 'full', None, 'attempts/dryrun-abc')
        prod = job.output_dir_for(root, 'full', None, 'attempts/production')
        assert dry != prod and dry.is_relative_to(root) and prod.is_relative_to(root)
        (root / 'dataset').mkdir()
        checker = root / 'check_complete.py'
        checker.write_bytes((PKG / 'check_complete.py').read_bytes())
        expected = [f'row-{n:02d}' for n in range(60)]
        (root / 'dataset/cohort.json').write_text(json.dumps([{'id': x} for x in expected]))
        dry.mkdir(parents=True)
        (dry / 'results.jsonl').write_text(''.join(json.dumps({'id': x}) + '\n' for x in expected))
        prod.mkdir(parents=True)
        (prod / 'results.jsonl').write_text(json.dumps({'id': expected[0]}) + '\n')
        (prod / 'run.json').write_text(json.dumps({'exit_code': 75, 'rows_written': 1}))
        first = subprocess.run([sys.executable, str(checker)], cwd=root)
        assert first.returncode != 0, 'complete dry-run results must not complete production'
        # Complete IDs without native throughput fields are not valid measurement rows.
        (prod / 'results.jsonl').write_text(''.join(json.dumps({'id': x, 'decode_tokens': 4}) + '\n' for x in expected))
        (prod / 'run.json').write_text(json.dumps({'exit_code': 0, 'rows_written': 60}))
        missing = subprocess.run([sys.executable, str(checker)], cwd=root)
        assert missing.returncode != 0, 'missing decode_tok_s must not complete production'
        (prod / 'results.jsonl').write_text(''.join(json.dumps({'id': x, 'decode_tok_s': None, 'decode_tokens': 4}) + '\n' for x in expected))
        null = subprocess.run([sys.executable, str(checker)], cwd=root)
        assert null.returncode != 0, 'null decode_tok_s must not complete production'
        (prod / 'results.jsonl').write_text(''.join(json.dumps({'id': x, 'decode_tok_s': 1.25, 'decode_tokens': 4}) + '\n' for x in expected))
        second = subprocess.run([sys.executable, str(checker)], cwd=root)
        assert second.returncode == 0


if __name__ == '__main__':
    test_dryrun_output_is_separate_and_never_satisfies_production_completion()
    print('S18 packet output isolation: PASS')

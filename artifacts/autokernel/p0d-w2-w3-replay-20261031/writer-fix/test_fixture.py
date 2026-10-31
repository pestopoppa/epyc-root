"""Fixture for the proposed W2/W3 full-census request-field correction."""
import ast
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
for source in (HERE / 'W2-future-work.py', HERE / 'W3-future-work.py'):
    tree = ast.parse(source.read_text())
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == 'full_census_request_fields')
    ns = {'json': json, 'Path': Path}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), ns)
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        record = root / 'native.json'
        summary = root / 'SUMMARY.json'
        summary.write_text(json.dumps({'state': 'OBSERVED', 'native_record': str(record)}))
        record.write_text(json.dumps({'graph': {'per_shape': [
            {'request_windows': [{'success': True}]},
            {'request_windows': [{'success': False}]},
            {'request_windows': [{'success': True}]},
        ]}}))
        result = ns['full_census_request_fields'](summary)
        assert result == {'requests_completed': 2, 'first_request_ok': True,
                          'request_count_evidence_error': None, 'result_writer_ok': True}
        record.write_text(json.dumps({'graph': {'per_shape': [{'request_windows': [{'success': False}]}]}}))
        summary.write_text(json.dumps({'state': 'UNKNOWN', 'native_record': str(record)}))
        result = ns['full_census_request_fields'](summary)
        assert result == {'requests_completed': 0, 'first_request_ok': False,
                          'request_count_evidence_error': None, 'result_writer_ok': True}
        for malformed in (
            {'graph': {'per_shape': [{}]}},
            {'graph': {'per_shape': [{'request_windows': [{'started': 1}]}]}},
            {'graph': {'per_shape': [{'request_windows': 'bad'}]}},
            {'graph': {'per_shape': []}},
        ):
            record.write_text(json.dumps(malformed))
            result = ns['full_census_request_fields'](summary)
            assert result['requests_completed'] is None and result['first_request_ok'] is None
            assert result['request_count_evidence_error'] and result['result_writer_ok'] is True
    text = source.read_text()
    assert 'result_writer_ok=True' not in text or '**full_census_request_fields(latest)' in text
print('PASS: W2/W3 request counts distinguish true, false, and missing/malformed windows; negative-state result writing remains successful')

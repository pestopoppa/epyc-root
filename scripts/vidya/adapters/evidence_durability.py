"""Prospective citation observations; immutable native custody, shared grading only."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = 'vidya.adapters.evidence_durability/v1'
AUTHORITY = 'diagnostic_no_promotion'
SCHEMA = 'epyc.evidence_durability_scan.v1'
PRODUCER_SHA256 = '47846292cdb2a9e5e3d4ab81dc49f6bebdd90db137a4805debec1b76e5489067'
DETERMINATE = {'OK': True, 'EPHEMERAL': False, 'MISSING': False, 'UNREADABLE': False}
QUALIFIED = {'WITHHELD', 'PRESENT_IN_MAIN_CLONE', 'WAIVED_LOST'}


def _require(condition, reason):
    if not condition:
        raise ProjectionError('durability receipt refused: ' + reason)


def native_rows(path):
    """Read only hash-named archives. Null caveats stay in their original receipt."""
    path = Path(path)
    try:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        _require(path.name == digest + '.json', 'immutable archive filename/hash mismatch')
        receipt = json.loads(raw)
        _require(receipt.get('schema') == SCHEMA, 'unknown schema')
        _require(receipt.get('metric') == 'citation_durability_verified' and
                 receipt.get('metric_direction') == 'higher_better', 'metric contract')
        stamp = datetime.fromisoformat(receipt['emitted_at_utc'].replace('Z', '+00:00'))
        _require(stamp.utcoffset() is not None and stamp.utcoffset().total_seconds() == 0, 'UTC required')
        checker = receipt['checker']
        _require(checker['source_sha256'] == PRODUCER_SHA256, 'unreviewed checker bytes')
        _require(bool(re.fullmatch(r'[0-9a-f]{40,64}', checker['git_revision'] or '')), 'checker revision absent')
        readset = receipt['readset']
        _require(isinstance(readset, list) and bool(readset), 'native readset absent')
        sources = {}
        for source in readset:
            _require(source['kind'] in {'registry', 'prose'} and bool(source['path']) and
                     bool(re.fullmatch(r'[0-9a-f]{64}', source['sha256'])), 'malformed native readset')
            _require(source['path'] not in sources or sources[source['path']] == source['sha256'], 'conflicting source hashes')
            sources[source['path']] = source['sha256']
        rows = receipt['target_verdicts']
        _require(isinstance(rows, list), 'target verdicts absent')
        for row in rows:
            _require(sources.get(row['source']) == row['source_sha256'], 'source/readset binding')
            _require(type(row['line']) is int and row['line'] > 0 and bool(row['target']), 'target locator')
            proposition = (f"The evidence reference {row['target']!r} from {row['source']!r}:{row['line']} "
                           "resolves on this host through the checker's declared "
                           "repo/main-clone resolution rules to a readable artifact outside "
                           "the checker's configured scratch roots.")
            _require(row['decided_proposition'] == proposition, 'producer proposition binding')
            verdict = row['verdict']
            _require(verdict in DETERMINATE or verdict in QUALIFIED, 'unknown verdict')
            _require((type(row['result']) is bool and row['result'] == DETERMINATE[verdict])
                     if verdict in DETERMINATE else row['result'] is None, 'verdict/result binding')
        caveats = [row for row in rows if row['result'] is None]
        return [dict(row, receipt=receipt, receipt_sha256=digest, receipt_path=str(path),
                     row_index=index, qualified_caveats=caveats)
                for index, row in enumerate(rows) if row['result'] is not None]
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ProjectionError(f'durability receipt refused: {exc}') from exc


@register('evidence_durability', source_class='verifier', decided_proposition_field='decided_proposition')
def project(row):
    originals = native_rows(row.get('receipt_path', ''))
    _require(any(original == row for original in originals), 'projection differs from immutable native row')
    receipt = row['receipt']
    _require(type(row.get('result')) is bool, 'qualified caveat is not a boolean')
    # CANDIDATE is the unqualified diagnostic carrier category, never a baseline.
    return ClaimTuple(measurement_id=f"durability:{row['receipt_sha256']}:{row['row_index']}",
                      metric=receipt['metric'], value=row['result'], date=receipt['emitted_at_utc'],
                      category='CANDIDATE', claim=row['decided_proposition'],
                      attestation_locator=row['receipt_path'],
                      metric_direction=receipt['metric_direction'], source_kind='evidence-durability',
                      source_class='verifier', decided_proposition=row['decided_proposition'],
                      binding_kind='identity', binding_ref=row['decided_proposition'],
                      extra={'native_receipt_path': row['receipt_path'],
                             'native_receipt_sha256': row['receipt_sha256'],
                             'checker': receipt['checker'], 'readset': receipt['readset'],
                             'target_verdict': {key: row[key] for key in
                                               ('source', 'source_sha256', 'line', 'target', 'resolved', 'verdict', 'severity')},
                             'qualified_caveats': row['qualified_caveats'], 'promotion_authority': False})

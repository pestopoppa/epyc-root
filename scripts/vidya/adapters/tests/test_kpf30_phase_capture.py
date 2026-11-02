import json
from pathlib import Path
import tempfile
import unittest

from adapters.kpf30_phase_capture import parse_log, write_phase_capture
from adapters.kv_prefix_fork import ProjectionError, project, validate_row
from claim_tuple import grade


def mask(seq, pos, live=2, mixed=1, unknown=0):
    return (f'KPF30 row=0 seq={seq} pos={pos} n_tokens=2 n_seqs=2 swa=0 causal=1 n_kv=512 '
            f'blocks=2 live={live} mixed={mixed} unknown={unknown} live_unknown=0 invalid_mask=0\n')


def corpus():
    return ['KPF30_BEGIN call=1 count=2\n',
            'KPF30_PHASE call=1 index=0 seq=0 pos=3 phase=decode\n',
            'KPF30_PHASE call=1 index=1 seq=1 pos=7 phase=verify\n',
            mask(1, 7), mask(0, 3, mixed=0), 'KPF30_END call=1 rc=0\n']


class PhaseCapture(unittest.TestCase):
    def test_positions_and_source_line_provenance(self):
        rows, prestart = parse_log(corpus())
        self.assertEqual(prestart, 0)
        self.assertEqual([(x['phase'],x['phase_line'],x['mask_line'],x['end_line']) for x in rows],
                         [('verify',3,4,6),('decode',2,5,6)])

    def test_bad_sources_fail_closed(self):
        bad = [corpus()[:-1], [mask(0, 3)],
               corpus()[:2]+['KPF30_PHASE call=1 index=1 seq=0 pos=3 phase=verify\n']+corpus()[3:],
               corpus()[:-1]+['KPF30_END call=1 rc=1\n'],
               corpus()[:4]+corpus()[5:],
               corpus()[:3]+[mask(1,7,unknown=1)]+corpus()[4:],
               corpus()[:3]+['KPF30 row=0 seq=1 live=1\n']+corpus()[4:],
               corpus()[:2]+['KPF30_PHASE call=1 index=1 seq=1 pos=7 phase=unknown\n']+corpus()[3:]]
        for lines in bad:
            with self.subTest(lines=lines), self.assertRaises(ValueError): parse_log(lines)

    def test_startup_rows_are_disclosed_not_attributed(self):
        rows, prestart = parse_log([mask(0,0)] + corpus())
        self.assertEqual(prestart, 1)
        self.assertEqual(len(rows), 2)
        with self.assertRaises(ValueError): parse_log(corpus() + [mask(0,4)])
        with self.assertRaises(ValueError): parse_log(corpus() + ['KPF30_UNSCOPED_TARGET kind=serial_verify\n'])

    def test_writer_projects_exact_phase_and_shared_grade(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); log=p/'server.log'; log.write_text(''.join(corpus()))
            m={'run_id':'r','window_id':'w','host':'h','binary_sha256':'a'*64,'prompt_set_sha256':'b'*64,
               'start_utc':'2026-11-02T00:00:00Z','category':'CANDIDATE','argv':['llama-server','--device','none'],
               'fan_completed':True,'process_reaped':True,'server_returncode':-15}
            records=write_phase_capture(log,p/'capture',m)
            self.assertEqual({x['phase'] for x in records},{'decode','verify'})
            self.assertTrue(all(validate_row(x)==[] for x in records))
            claims=[project({'row':x,'sidecar_path':str(p/'capture'/'belief_measurements.jsonl')}) for x in records]
            self.assertEqual({x.extra['phase']:x.value for x in claims},{'decode':0,'verify':.5})
            self.assertTrue(all(x.attestation_verified for x in claims))
            self.assertTrue(all(grade(x) for x in claims))
            # Modification of the original phase source must never be accepted.
            log.write_text(log.read_text().replace('phase=verify','phase=decode'))
            with self.assertRaises(ProjectionError): project({'row':records[0],'sidecar_path':str(p/'capture'/'belief_measurements.jsonl')})

    def test_no_sidecar_on_invalid_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); log=p/'bad'; log.write_text(mask(0,3))
            m={'run_id':'r','window_id':'w','host':'h','binary_sha256':'a'*64,'prompt_set_sha256':'b'*64,
               'start_utc':'2026-11-02T00:00:00Z','category':'CANDIDATE','argv':['llama-server'],
               'fan_completed':True,'process_reaped':True,'server_returncode':-15}
            with self.assertRaises(ValueError): write_phase_capture(log,p/'capture',m)
            self.assertFalse((p/'capture'/'belief_measurements.jsonl').exists())

if __name__ == '__main__': unittest.main()

from datetime import datetime, timezone
from pathlib import Path
import csv
import json
import re
import subprocess
import sys

BASE = Path(__file__).parent
STUDY = Path('/mnt/raid0/llm/tmp/ws58-conclusions-adapter-design-20261025/work/a1')
REF = '6f201114228d0ad8d03877b61c58f74eb1ea3dbd'
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import committed_conclusion as ccm
from cc_extract import draft_row

GEMMA = 'gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf'
Q35 = 'Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
Q27 = 'Qwen3.8-27B-Q8_0.gguf'
Q38U = 'Qwen3.8-Flash-Next-IQ4_XS-uniform.gguf'
Q38UD = 'Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'

def scope(backend=None, model=None, quant=None, epoch=None, build=None, ctx=None):
    out = {}
    if backend:
        out.update(backend=backend, device={'cpu': 'epyc-9655', 'gpu': 'gfx90a'}[backend])
    for key, val in [('model_file', model), ('quant', quant), ('epoch', epoch),
                     ('build_sha', build), ('context_tokens', ctx)]:
        if val is not None:
            out[key] = val
    return out

def metric(name, value, unit='', arm=None):
    row = dict(metric=name, value=value, unit=unit)
    if arm is not None:
        row['arm'] = arm
    return row

def ms(name, unit, pairs):
    return [metric(name, value, unit, arm) for arm, value in pairs]

def c(task=None, *, verdict=None, metrics=(), sc=None, evidence=None,
      lower=False, category='CANDIDATE', kind='result', date=None, n=None, also=(), ref=REF,
      shifted=None, note=None):
    return dict(task=task, stated=dict(verdict_native=verdict, metrics=list(metrics),
                                      date=date, n=n, protocol_named=None),
                scope=sc or {}, scope_evidence=evidence or ('line' if sc else 'none'),
                direction='lower_better' if lower else 'higher_better', category=category,
                kind=kind, also=also, ref=ref, shifted=shifted, note=note)

gold = {
    3: c( verdict='no keeps', n=5, date='2026-09-10',
         metrics=ms('iteration_effect', '%', [(str(k), x) for k, x in enumerate(
             [0.950164, 1.454288, 1.181050, 1.248272, 0.332447], 1)])),
    5: c('DS41-C112', date='2026-10-03', sc=scope('cpu', Q38U, 'IQ4_XS', 'E9-cpu-kernel'),
         metrics=[dict(metric('pp256_effect', -4.4, '%', 'COR vs champion'), outcome='null')],
         note='Structured effect is the unambiguous uniform-file comparison. Corrected bisect sign-only verdict stays in quote.'),
    7: c('EXL3-6c6', date='2026-10-04',
         metrics=ms('attn_q_b_n1_latency', 'µs', [('EXL3_K4 donor VBMI native', 120.3),
                     ('IQ4_XS', 55.3), ('Q4_K', 46.1)]), lower=True),
    12: c('G3-3a', date='2026-07-28',
          metrics=ms('correct_items', 'items', [('receiver-nothink (all 48 imported)', 25),
                                              ('Qwable-prefix (5 imported, 43 fresh)', 42)]), n=48),
    14: c('G1-GPQA', verdict='REOPENED + VALIDATED', date='2026-07-05', n=48,
          metrics=ms('gpqa_accuracy', '%', [('scaffold-Qwable', 73), ('nothink', 48),
                                           ('ownthink (lower bound, truncated)', 67)])),
    16: c('G1-i', date='2026-07-05', note='Historical slice-2 result. Later baseline cleanups are preserved at gold item 17.'),
    17: c('G2-G1-ii', date='2026-07-05',
          metrics=[metric('format_native_cross_family_accuracy_lift', 11, 'pp')]),
    21: c('DS41-C127', verdict='PASS', date='2026-10-07',
          metrics=ms('calibration_cases', 'cases', [('Q38FN', 250), ('DS41', 348)])),
    23: c('DS41-C83', date='2026-09-30', metrics=[metric('post_c76_successes', 0, 'cases', '27B, 5 replays')]),
    24: c('DS41-C98', verdict='operator chose D: status quo', kind='decision', date='2026-10-03'),
    26: c('E5-A6', date='2026-08-11', metrics=[metric('blocked_cells_rescued', 5, 'cells', 'decouple'),
                                            metric('banked_cells_moved_gt_5pct', 0, 'cells', 'decouple')]),
    28: c('E5-A11', date='2026-08-11',
          metrics=[metric('reasoning_present_manifests', 19, 'manifests'),
                   metric('binary_version_present_cpu_bench', 3, 'rows')]),
    34: c('FOLD-2', verdict='PASS', date='2026-09-08', sc=scope('gpu', build='ef81196d5'),
          metrics=[metric('hip_ssm_scan_ok', 7, 'tests'), metric('hip_mul_mat_ok', 1140, 'tests'),
                   metric('hip_gated_delta_net_ok', 39, 'tests')],
          also=('handoffs/active/autokernel-unified-surface-program.md:1290',)),
    37: c('K23', verdict='passed', date='2026-07-17',
          note='Current-source coherence and stale-binary scaling are distinct; keep their native limits in the quote.'),
    38: c('D1-dense-mask', date='2026-07-17',
          note='Confirmed current-source fixed-top-k dense-mask KV scaling, distinct from K23 stale-binary throughput.'),
    41: c('UFH14-B4i', date='2026-10-04', lower=True, n=18,
          metrics=ms('turn_2plus_ttft_median', 's', [('ON (default)', 66.4), ('OFF', 16.3)]),
          also=('handoffs/active/agentic-serving-harness-fixes.md:311',)),
    47: c('Q38-T7', verdict='PASS', date='2026-10-04', sc=scope('gpu', Q27, 'Q8_0'),
          metrics=ms('production_mix_token_weighted_decode', 'tok/s', [('DFlash2', 60.02), ('no draft', 31.07)])),
    50: c('V6R-4d', verdict='not completed', date='2026-09-29',
          note='Record three preprobe admission refusals and artifact/linkage checks. Live A/B is item 52 only.'),
    52: c('V6R-4d.2', verdict='PASS', date='2026-10-01',
          sc=scope('gpu', Q27, 'Q8_0', build='90c12df42'),
          metrics=[metric('pp_tps_median_effect', 0.39, '%'), metric('tg_tps_median_effect', -0.46, '%')]),
    54: c('A2/H1', verdict='NOT significant', date='2026-07-24', n=141,
          metrics=[metric('paired_mcnemar_p', 0.096)]),
    61: c('XFER-4', verdict='NOT folded', date='2026-10-03', n=3,
          sc=scope('cpu', Q38UD, 'UD-IQ4_XS', 'E9-cpu-kernel', '8c4b282ae'),
          evidence='handoff-header',
          metrics=ms('bench_throughput_effect', '%', [('pp5', -12.2), ('pp256', -3.9), ('tg128', -3.2)])),
    63: c('K24', date='2026-07-17',
          metrics=ms('paired_cpu_decode_effect', '%', [('frontdoor', -2.64), ('architect', -3.05), ('ingest', 1.00)])),
    64: c('K25.2a', verdict='falsified', date='2026-07-17',
          metrics=[metric('greedy_draft_tokens_returned', 0, 'tokens')]),
    65: c('K25.2c', date='2026-07-17',
          metrics=[metric('external_draft_tree_decode', 40.55, 't/s')],
          note='Route proof only; native quote retains negative serving economics.'),
    66: c('K25.1', verdict='passed', date='2026-07-17', lower=True,
          sc=scope('gpu', quant='Q8_0'),
          metrics=ms('mmq_dispatch_mean', 'us', [('lower reported endpoint n=2..8', 10.16),
                                                ('upper reported endpoint n=2..8', 11.20)])),
    68: c('K26', date='2026-07-17', sc=scope('gpu', Q35, 'Q8_0', build='9d70bae4b'),
          metrics=ms('llama_bench_decode', 't/s', [('f16/f16', 100.013), ('bf16/f16', 12.936),
                  ('f16/bf16', 12.885), ('bf16/bf16', 80.896)])
                + ms('server_decode_median', 't/s', [('f16/f16', 104.375), ('bf16/f16', 91.100),
                  ('f16/bf16', 88.213), ('bf16/bf16', 100.224)])
                + ms('llama_bench_prompt_processing', 't/s', [('f16/f16', 2256.079),
                  ('bf16/f16', 1110.047), ('f16/bf16', 531.281), ('bf16/bf16', 2253.098)])),
    70: c('K27.2', date='2026-07-17',
          metrics=ms('smoke_decode', 't/s', [('default', 8.47), ('legacy env set', 8.40)])),
    71: c('K34.1', date='2026-07-17', n=3,
          metrics=ms('v7_vs_prod_default_cpu_decode_effect', '%', [('frontdoor', -0.73),
                     ('architect', 3.84), ('ingest', 0.68)])),
    72: c('K35.3', date='2026-07-17',
          metrics=ms('cpu_server_decode', 't/s', [('architect 837 prompt tokens', 23.53),
                     ('architect 6725 prompt tokens', 20.72), ('corrected ingest 575 prompt tokens', 19.82),
                     ('corrected ingest 6719 prompt tokens', 15.94), ('corrected ingest 14528 prompt tokens', 13),
                     ('corrected ingest 28528 prompt tokens', 10.13)])),
    74: c('K35.13b', date='2026-07-17', category='OPTIMUM', sc=scope('gpu', Q35, 'Q8_0'),
          metrics=ms('operational_decode', 't/s', [('2K prompt', 100.55), ('8K prompt', 95.56), ('32K prompt', 77.67)])),
    75: c('K35.7', verdict='ok', date='2026-07-17', lower=True,
          metrics=ms('post_request_host_rss', 'GiB', [('frontdoor 2K', 1.37), ('frontdoor 8K', 1.38),
                     ('frontdoor 32K', 1.40), ('worker 2K', 17.48), ('worker 8K', 17.74),
                     ('architect 2K', 75.56), ('architect 8K', 76.46), ('ingest 2K', 45.84),
                     ('ingest 8K', 46.11), ('ingest 32K', 46.35)])),
    76: c('K35.12', verdict='passed', date='2026-07-17',
          metrics=[metric('chart_fixture_score_pass', 1, '', 'MiniCPM-o, truthful boolean')]),
    77: c('K35.13a', date='2026-07-17', n=2, sc=scope('gpu', Q35, 'Q8_0'),
          evidence='handoff-header',
          metrics=ms('frontdoor_decode', 't/s', [('alone request 1', 101.68), ('alone request 2', 101.84),
                     ('MiniCPM-o idle request 1', 101.89), ('MiniCPM-o idle request 2', 101.86),
                     ('MiniCPM-o active request 1', 80.16), ('MiniCPM-o active request 2', 80.34)]),
          also=('handoffs/active/gemma-challenge-kernel-techniques-v7.md:465',)),
    78: c('K35.11', date='2026-07-17',
          metrics=ms('ocr_chart_fixture_passes', 'fixtures', [('default reasoning', 0),
                     ('CPU reasoning off', 4), ('MI210 reasoning off', 4)])),
    80: c('K35.10', date='2026-07-17',
          metrics=ms('ocr_chart_fixture_passes', 'fixtures', [('CPU', 4), ('MI210', 3), ('MI210 default image-token shape', 3)])),
    81: c('K35.14', date='2026-07-17',
          metrics=ms('ocr_chart_fixture_passes', 'fixtures', [('CPU', 4), ('MI210', 4)])),
    83: c('K35.8', date='2026-07-17',
          metrics=ms('ocr_chart_fixture_passes', 'fixtures', [('worker_vision', 4), ('vision_escalation', 3)])),
    84: c('K35.4', verdict='passed', date='2026-07-17',
          metrics=ms('single_ocr_request_decode', 't/s', [('worker_vision', 10.93), ('vision_escalation', 27.18)])),
    89: c('Post-E8-rebuild', date='2026-07-29',
          metrics=[metric('eligible_selected_items', 2, 'items'), metric('pre_era_excluded_rows', 1317, 'rows')]),
    90: c('AK-MMQ-H10', verdict='NEGATIVE', date='2026-09-27', sc=scope('gpu', Q27, 'Q8_0', build='36e83c0f2'),
          metrics=ms('llama_bench_prefill_effect', '%', [('p64', -12.6), ('p112', -9.1), ('p128', -9.9)])),
    91: c('AK-MMQ-H10b', date='2026-09-27',
          note='The aborted invariance check is a stated observation. The follow-up diagnosis remained unticked and unproved.'),
    94: c('K35.17', verdict='negative', date='2026-07-17',
          metrics=[metric('html_table_tags', 0, 'tags'), metric('table_teds', 0.0), metric('completed_pages', 18, 'pages')]),
    98: c('DF2-14', verdict='no material signal', date='2026-10-03',
          metrics=ms('lookup_coverage', '%', [('all', 8.0), ('reasoning', 5.6), ('tool-call args', 45),
                                            ('patches', 30), ('final answer', 17)])),
    101: c('T3', verdict='FUNCTIONALLY VERIFIED', date='2026-07-17',
           metrics=ms('mi210_broad_decode_mean', 't/s', [('no-spec', 105.88), ('native MTP', 114.09),
                      ('ngram-mod,draft-mtp', 113.24)])),
    102: c('R23-5', verdict='CONFIRMED', date='2026-09-01', n=20,
           metrics=ms('surface_throughput_effect', '%', [('tg128', 17.259), ('dec-b2', 3.834),
                      ('dec-b4', 1.178), ('dec-b8', -1.462)])),
    103: c('RI-16', date='2026-10-01', n=30, lower=True,
           metrics=ms('routing_total_latency', 'ms', [('p50', 622), ('p95', 1159)]),
           also=('handoffs/active/routing-intelligence.md:67',)),
    107: c('STT-CPU-baseline', date='2026-07-31', n=100, lower=True, category='BASELINE',
           metrics=[metric('wer', 2.35, '%', 'faster-whisper large-v3-turbo int8 CPU')]),
    108: c('S-10', verdict='DROPPED', date='2026-07-31', lower=True,
           metrics=[metric('wer', 3.37, '%', 'whisper.cpp large-v3-turbo f16 GPU greedy'),
                    metric('wall_median', 0.124, 's', 'whisper.cpp large-v3-turbo f16 GPU greedy')],
           note='Exact study snapshot carries the historical 2026-10-20 correction; 2.35% survives only as item 107 CPU WER.'),
    109: c('EVL25-LoRA-fit', date='2026-09-15', lower=True,
           metrics=ms('measured_peak_memory', 'GB', [('Qwen2.5-7B stand-in r16/seq512/batch4', 39.32),
                      ('Qwen2.5-7B stand-in r32/seq2048/batch1', 39.99)])),
    110: c('T5', date='2026-07-18', sc=scope('cpu', GEMMA, 'Q4_K_M', 'E5-cpu-kernel', ctx=8192),
           evidence='handoff-header',
           metrics=ms('worker_decode', 't/s', [('512 tokens depth 2', 87.76), ('512 tokens depth 3', 76.38),
                      ('512 tokens depth 4', 84.40), ('1024 tokens depth 2', 105.20),
                      ('1024 tokens depth 3', 93.91), ('1024 tokens depth 4', 101.00)])),
    112: c('Bonsai-8B-v7-bench', date='2026-07-18', n=3, sc=scope('gpu', quant='Q1_0', build='d1e5a20eb'),
           metrics=ms('llama_bench_throughput', 't/s', [('pp2048', 2349.46), ('pp8192', 1750.72), ('tg1024', 38.37)])),
    113: c('K20', date='2026-07-16',
           metrics=ms('v7_vs_production_decode_effect', '%', [('architect base decode', -9.24),
                      ('ingest base decode', 0.93), ('frontdoor draft-mtp', -2.12),
                      ('architect draft-mtp', -0.25), ('ingest server', -1.06)])),
    114: c('K17', date='2026-07-16',
           metrics=ms('v7_vs_production_base_decode_effect', '%', [('Gemma worker CPU', -2.88),
                      ('Qwen3.6 frontdoor CPU', -6.55)])),
}
# The exact source itself preserves these non-numeric results without making up quantities.
gold[76]['stated']['metrics'] = []
gold[54]['stated']['metrics'] = [metric('q4_only_correct_pairs', 13, 'pairs'),
                                 metric('iq2_only_correct_pairs', 5, 'pairs')]

def run():
    items = json.loads((STUDY / 'class_a_items.json').read_text())
    indices = set(json.loads((STUDY / 'labels_classA_true.json').read_text()))
    assert len(items) == 120 and len(indices) == 54 and set(gold) == indices - {35}
    by_name = {}
    with Path('docs/reference/tmp-loss-inventory-2026-10-25.tsv').open() as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            if r['class'] == 'A':
                by_name.setdefault(Path(r['path']).name, []).append(r)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    batch = BASE / 'gold-register.jsonl'
    batch.unlink(missing_ok=True)
    existing = ccm.read_register(Path(ccm.REGISTER_REL))
    known_ids = {row['cc_id'] for row in existing}
    report = []
    at = []
    for i in sorted(indices):
        item = items[i]
        path = item['handoff']
        line = item['start']
        if i == 35:
            report.append(dict(gold_index=i, disposition='also_anchored', primary_gold=34,
                               path=path, line=line))
            continue
        meta = gold[i]
        ref = meta['ref']
        line = meta['shifted'] or line
        data = ccm.blob_lines(ROOT, ref, path)
        start, end = ccm.item_extent(data, line)
        quote = '\n'.join(data[start-1:end])
        proposal = draft_row(path, start, end, quote, item['head'])
        assert proposal['cc_id'] not in known_ids
        source = [('primary', quote)]
        for locator in meta['also']:
            k, _, n = locator.rpartition(':')
            arr = ccm.blob_lines(ROOT, ref, k)
            first, last = ccm.item_extent(arr, int(n))
            source.append((locator, '\n'.join(arr[first-1:last])))
        whole = '\n'.join(text for label, text in source)
        for m in meta['stated']['metrics']:
            num = format(m['value'], 'g')
            if isinstance(m['value'], float):
                num = str(m['value'])
            normalized = whole.replace('−', '-').replace('1,317', '1317')
            assert num in normalized, (i, m, num, source)
        paths = []
        for name in item['paths']:
            matching = [r['path'] for r in by_name.get(name, []) if r['path'] in item['text']]
            if len(matching) == 1:
                paths += matching
        args = [sys.executable, 'scripts/vidya/cli.py', '--json', 'conclusion', 'add',
                '--path', path, '--line', str(line), '--ref', ref,
                '--kind', meta['kind'], '--stated-json', json.dumps(meta['stated']),
                '--scope-json', json.dumps(meta['scope']), '--scope-evidence', meta['scope_evidence'],
                '--category', meta['category'], '--direction', meta['direction'], '--retrofit',
                '--actor', 'h-vidya-belief-substrate/class_a_fill', '--at', stamp, '--register', str(batch)]
        if meta['task']:
            args += ['--task-id', meta['task']]
        for anchor in meta['also']:
            args += ['--also', anchor]
        for raw in sorted(set(paths)):
            args += ['--raw', raw]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError((i, result.stderr))
        entry = json.loads(result.stdout)
        assert entry['written'] and entry['cc_id'] == proposal['cc_id'], (i, entry)
        report.append(dict(gold_index=i, disposition=meta['kind'], cc_id=entry['cc_id'],
                           path=path, study_line=item['start'], cli_line=line, note=meta['note'],
                           scope=meta['scope'], metrics=len(meta['stated']['metrics']),
                           extractor_proposed=proposal['proposal']['proposed']))
        at.append(args)
        (BASE / 'partial.json').write_text(json.dumps(report, indent=2) + '\n')
    (BASE / 'confirmation.json').write_text(json.dumps(report, indent=2) + '\n')
    (BASE / 'commands.json').write_text(json.dumps(at, indent=2) + '\n')
    print('prepared', len(report), 'gold labels and', len(ccm.read_register(batch)), 'distinct register rows')

if __name__ == '__main__':
    run()

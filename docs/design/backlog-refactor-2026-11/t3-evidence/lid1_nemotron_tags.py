#!/usr/bin/env python3
"""CS-26.LID1 arm (b) replay: Nemotron 3.5 auto-detect tags banked in CS-8.STT5 validation (zero inference).
Stop rule: one pass over the 1437 banked rows; stop when per-language accuracy, Wilson CI, confusion and the
input-compatibility verdict against the LID1 crop protocol are recorded. Report only; no decision rule is applied.
Denominator = every row; a row with no tag or an out-of-mask tag counts WRONG (never dropped)."""
import collections, hashlib, json, math, sys
RAW = '/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-nemotron-tc-r2-20261030/validation-results/raw-r0-auto.json'
CROPS = '/mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030/crops.jsonl'
MASK = ('en', 'it', 'de', 'fr')
def wilson(k, n, z=1.959964):
    if n == 0: return [None, None]
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def lang_of(tag):
    t = tag.strip('<>').split('-')[0].lower()
    return t
d = json.load(open(RAW)); rows = d['rows']
out = {'schema': 'brf-t3/lid1-nemotron-tags/1', 'source': RAW, 'source_sha256': sha(RAW), 'arm': d['arm'],
       'language_mode': d['language_mode'], 'segmentation_mode': d['segmentation_mode'], 'corpus_id': d['corpus_id'],
       'n_rows': len(rows)}
per = {l: {'n': 0, 'first_tag_correct': 0, 'majority_tag_correct': 0, 'no_tag': 0, 'out_of_mask': 0,
           'mixed_tags_in_row': 0, 'confusion_first': collections.Counter()} for l in MASK}
dur = collections.defaultdict(list)
for r in rows:
    ref = r['language']; tags = [lang_of(t) for te in r['token_evidence'] for t in te['language_tags']]
    p = per[ref]; p['n'] += 1; dur[ref].append(r['duration_s'])
    if not tags: p['no_tag'] += 1; p['confusion_first']['<none>'] += 1; continue
    first = tags[0]; maj = collections.Counter(tags).most_common(1)[0][0]
    if len(set(tags)) > 1: p['mixed_tags_in_row'] += 1
    p['confusion_first'][first] += 1
    if first not in MASK: p['out_of_mask'] += 1
    p['first_tag_correct'] += first == ref; p['majority_tag_correct'] += maj == ref
tot_n = sum(p['n'] for p in per.values()); tot_c = sum(p['first_tag_correct'] for p in per.values())
for l, p in per.items():
    p['accuracy_first'] = round(p['first_tag_correct'] / p['n'], 4); p['ci95_wilson_first'] = wilson(p['first_tag_correct'], p['n'])
    p['accuracy_majority'] = round(p['majority_tag_correct'] / p['n'], 4)
    p['tag_emitted_rows'] = p['n'] - p['no_tag']; p['precision_when_emitted'] = round(p['first_tag_correct'] / max(1, p['tag_emitted_rows']), 4)
    p['confusion_first'] = dict(p['confusion_first']); s = sorted(dur[l]); p['duration_s'] = {'min': s[0], 'median': s[len(s) // 2], 'max': s[-1]}
out['per_language'] = per
out['pooled_first'] = {'n': tot_n, 'correct': tot_c, 'accuracy': round(tot_c / tot_n, 4), 'ci95_wilson': wilson(tot_c, tot_n)}
# input compatibility with the pre-declared LID1 crop protocol (1/2/3 s crops, 9,150 cases)
crops = [json.loads(l) for l in open(CROPS)]
crop_pcm = {c['source_pcm_sha256'] for c in crops}; banked_pcm = {r['pcm_sha256'] for r in rows}
out['crop_protocol_compat'] = {'crops_file': CROPS, 'crops_sha256': sha(CROPS), 'n_crop_cases': len(crops),
    'crop_durations_s': sorted({c['duration_requested_s'] for c in crops}),
    'banked_row_duration_s_min': min(r['duration_s'] for r in rows), 'banked_row_duration_s_max': max(r['duration_s'] for r in rows),
    'banked_rows_le_3s': sum(r['duration_s'] <= 3 for r in rows),
    'banked_source_pcm_in_lid1_test_manifest': len(banked_pcm & crop_pcm),
    'verdict': 'INCOMPATIBLE: banked rows are full-length FLEURS-validation clips; the protocol takes Nemotron tags only from runs with identical input and duration (1/2/3 s test crops), so these tags cannot enter the LID1 comparison'}
json.dump(out, open(sys.argv[1], 'w'), indent=1, sort_keys=True); print(json.dumps({k: out[k] for k in ('n_rows', 'pooled_first', 'crop_protocol_compat')}, indent=1)[:2000])
for l, p in per.items(): print(l, p['n'], p['tag_emitted_rows'], p['precision_when_emitted'], p['accuracy_first'], p['ci95_wilson_first'], p['accuracy_majority'], p['no_tag'], p['out_of_mask'], p['mixed_tags_in_row'], p['confusion_first'])

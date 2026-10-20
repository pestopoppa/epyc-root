#!/usr/bin/env python3
"""Offline stage-2 grading of DF2-17 divergent pairs (spec-off baseline vs dflash_n7 arm).

No inference, no network. Gold is read ONLY from the repo's question pool (by id) or from the
prompt text itself (mbpp asserts). Run as:  python3 -I grade_stage2.py
"""
import ast, importlib.util, json, os, re, shutil, string, subprocess, sys, tempfile, unicodedata
from pathlib import Path

ROOT = Path('/mnt/raid0/llm/tmp/gpu-queue-20261020/df2-17')
OUT = ROOT / 'grading'
WORK = OUT / '_work'
BASE_P = ROOT / 'stage2/off_A/records.jsonl'
ARM_P = ROOT / 'stage2/dflash_n7/records.jsonl'
PROMPTS_P = ROOT / 'stage2_rendered_prompts.json'
POOL_P = Path('/workspace/repos/epyc-inference-research/benchmarks/prompts/question_pool.jsonl')
PROD_P = '/workspace/repos/epyc-orchestrator/scripts/benchmark/debug_scorer.py'


def load(p):
    return {json.loads(l)['id']: json.loads(l) for l in open(p)}


base, arm = load(BASE_P), load(ARM_P)
prompts = {x['id']: x for x in json.load(open(PROMPTS_P))}
div = [i for i in base if base[i]['tokens'] != arm[i]['tokens']]
pool = {}
for l in open(POOL_P):
    d = json.loads(l)
    if d.get('id') in div:
        pool[d['id']] = d

# production scorer (cross-check only; loaded read-only)
os.environ['TMPDIR'] = str(WORK)
WORK.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('prod_scorer', PROD_P)
prod = importlib.util.module_from_spec(spec); sys.modules['prod_scorer'] = prod
spec.loader.exec_module(prod)


def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFKD', s or '') if not unicodedata.combining(c))
    s = s.lower().translate(str.maketrans('', '', string.punctuation))
    s = re.sub(r'\b(a|an|the)\b', ' ', s)
    return ' '.join(s.split())


def last_line(s):
    ls = [x.strip() for x in (s or '').strip().split('\n') if x.strip()]
    return ls[-1] if ls else ''


# ---------------------------------------------------------------- code (mbpp)
def extract_code(content):
    blocks = re.findall(r'```(?:python|py)[ \t]*\n(.*?)```', content, re.S | re.I)
    if blocks:
        return blocks[-1], 'last_closed_python_block'
    m = re.search(r'```(?:python|py)?[ \t]*\n(.*)\Z', content, re.S | re.I)
    if m:
        return m.group(1), 'unclosed_fence_tail(truncated_output)'
    return content, 'whole_content'


def mbpp_asserts(raw_prompt):
    return [l.strip() for l in raw_prompt.split('\n') if l.strip().startswith('assert ')]


def run_py(code, asserts, timeout=10):
    d = tempfile.mkdtemp(prefix='mbpp_', dir=WORK)
    try:
        f = Path(d) / 'sol.py'
        f.write_text(code + '\n\n' + '\n'.join(asserts) + '\n')
        try:
            r = subprocess.run([sys.executable, '-I', str(f)], cwd=d, capture_output=True,
                               text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            return r.returncode == 0, (r.stderr.strip().splitlines() or [''])[-1][:200]
        except subprocess.TimeoutExpired:
            return False, 'timeout 10s'
    finally:
        shutil.rmtree(d, ignore_errors=True)


def grade_mbpp(i):
    asserts = mbpp_asserts(prompts[i]['raw_prompt'])
    res = {}
    for nm, rec in (('base', base[i]), ('arm', arm[i])):
        code, how = extract_code(rec['content'])
        ok, err = run_py(code, asserts)
        if not ok and how != 'whole_content':
            # spec fallback: whole content
            ok2, err2 = run_py(rec['content'], asserts)
            if ok2:
                ok, err, how = ok2, err2, 'whole_content(fallback)'
        res[nm] = {'pass': ok, 'extract': how, 'err': err}
    return asserts, res


# ---------------------------------------------------------------- ifeval
def ifeval_checks(resp, kw_list, ids):
    out = {}
    for iid, kw in zip(ids, kw_list):
        if iid == 'detectable_format:number_highlighted_sections':
            n = 0
            for h in re.findall(r'\*[^\n\*]*\*', resp):
                if h.strip('*').strip():
                    n += 1
            for h in re.findall(r'\*\*[^\n\*]*\*\*', resp):
                if h.removeprefix('**').removesuffix('**').strip():
                    n += 1
            out[iid] = (n >= kw['num_highlights'], f'highlights={n} need>={kw["num_highlights"]}')
        elif iid == 'change_case:english_capital':
            out[iid] = (resp.isupper(), f'isupper={resp.isupper()} (langdetect==en check NOT implemented: package absent)')
        elif iid == 'detectable_format:multiple_sections':
            pat = r'\s?' + kw['section_spliter'] + r'\s?\d+\s?'
            n = len(re.split(pat, resp)) - 1
            out[iid] = (n >= kw['num_sections'], f'sections={n} need>={kw["num_sections"]}')
        elif iid == 'detectable_format:number_bullet_lists':
            n = len(re.findall(r'^\s*\*[^\*].*$', resp, flags=re.M)) + len(re.findall(r'^\s*-.*$', resp, flags=re.M))
            out[iid] = (n == kw['num_bullets'], f'bullets={n} need=={kw["num_bullets"]}')
        else:
            raise ValueError(iid)
    return out


def ifeval_loose_variants(resp):
    r = resp.split('\n')
    v = [resp, resp.replace('*', ''), '\n'.join(r[1:]).strip(), '\n'.join(r[:-1]).strip(), '\n'.join(r[1:-1]).strip()]
    v += [x.replace('*', '') for x in v[2:5]]
    return [x for x in v if x.strip()]


def grade_ifeval(i, rec):
    q = pool[i]
    ids = q['ifeval_instructions']
    kws = [{k: v for k, v in kw.items() if v is not None} for kw in q['ifeval_kwargs']]
    strict = ifeval_checks(rec['content'], kws, ids)
    loose = {}
    for iid, kw in zip(ids, kws):
        loose[iid] = any(ifeval_checks(v, [kw], [iid])[iid][0] for v in ifeval_loose_variants(rec['content']))
    return strict, loose


# ---------------------------------------------------------------- math / mc helpers
def boxed_last(t):
    m = None
    for mm in re.finditer(r'\\boxed\{', t or ''):
        k = mm.end(); depth = 1; j = k
        while j < len(t) and depth:
            depth += (t[j] == '{') - (t[j] == '}'); j += 1
        m = t[k:j - 1]
    return m


def answer_tag_last(t):
    m = re.findall(r'<answer>(.*?)</answer>', t or '', re.S)
    return m[-1].strip() if m else None


def to_num(s):
    try:
        return float(re.sub(r'[,$\s]', '', s))
    except Exception:
        return None


def strict_letter(t):
    ln = last_line(t)
    m = re.fullmatch(r'\**\s*ANSWER:\s*\**\s*\(?([A-D])\)?\**\.?', ln, re.I)
    return m.group(1).upper() if m else None


def prod_try(fn):
    try:
        return fn()
    except Exception as e:  # noqa
        return f'ERR:{type(e).__name__}:{str(e)[:120]}'


# ---------------------------------------------------------------- per-pair grading
records = []

for i in div:
    suite = prompts[i]['suite']
    b, a = base[i], arm[i]
    rec = {
        'id': i, 'suite': suite,
        'base_tokens': len(b['tokens']), 'arm_tokens': len(a['tokens']),
        'base_stop': b['stop_type'], 'arm_stop': a['stop_type'],
        'grader': 'none', 'baseline_pass': None, 'arm_pass': None, 'graded_flip': None,
        'proxy': None, 'answers_equal_proxy': None, 'notes': '',
    }
    q = pool.get(i, {})
    pf = None  # (basis, equal)

    if i.startswith('mbpp_'):
        asserts, res = grade_mbpp(i)
        rec['grader'] = 'mbpp_prompt_asserts_exec(python3 -I, 10s, tempdir)'
        rec['baseline_pass'], rec['arm_pass'] = res['base']['pass'], res['arm']['pass']
        rec['notes'] = (f'{len(asserts)} asserts parsed from prompt "Test cases:" block. '
                        f'base: extract={res["base"]["extract"]} pass={res["base"]["pass"]} err="{res["base"]["err"]}"; '
                        f'arm: extract={res["arm"]["extract"]} pass={res["arm"]["pass"]} err="{res["arm"]["err"]}". '
                        'Pool gold for mbpp is only a function-name substring (vacuous), so the prompt asserts are the oracle.')
        ca, _ = extract_code(b['content']); cb, _ = extract_code(a['content'])
        try:
            ta, tb = ast.dump(ast.parse(ca)), ast.dump(ast.parse(cb))
            pf = ('AST of extracted code (comments ignored; docstrings kept)', ta == tb)
        except SyntaxError:
            pf = ('final non-empty line (extracted code is not parseable: truncated at cap)',
                  norm(last_line(b['content'])) == norm(last_line(a['content'])))
        if i == 'mbpp_0303':
            rec['notes'] += (' BOTH outputs hit the 1600-token cap inside an unterminated docstring of the first (only) ```python block '
                             '(model was still deliberating the task semantics); no complete function exists in either, so both fail by construction '
                             '(cap artifact, not a judgement of the algorithm).')
        if i == 'mbpp_0508':
            rec['notes'] += ' The two code blocks are identical except one comment ("same order" vs "same sequence"); token streams differ only there.'

    elif suite == 'livecodebench':
        rec['grader'] = 'none'
        slug = i.removeprefix('leetcode_')
        ca, _ = extract_code(b['content']); cb, _ = extract_code(a['content'])
        same = ast.dump(ast.parse(ca)) == ast.dump(ast.parse(cb))
        smoke = []
        for nm, c in (('base', ca), ('arm', cb)):
            ok, err = run_py(c, ['assert smallestChair([[1,4],[2,3],[4,6]], 1) == 1',
                                 'assert smallestChair([[3,10],[1,5],[2,6]], 0) == 2'])
            smoke.append(f'{nm}={ok}')
        rec['notes'] = (f'UNGRADED: no executable tests for this id. Searched: question_pool.jsonl row (scoring_method=substring needle "def " = '
                        f'vacuous, production scorer itself refuses it for language rows); epyc-orchestrator data/benchmark/livecodebench_oracle_manifest.json '
                        f'(704 validated slugs; "{slug}" NOT among them); hf-home greengerong/leetcode snapshot (problem text + reference solutions only, '
                        f'no tests; its python reference keys events by time in a dict so arrival/leave collisions overwrite - not used as gold). '
                        f'Supplementary (NOT a grader): the two extracted solutions have IDENTICAL AST (differ only in comments): {same}; '
                        f'the 2 worked examples in the prompt text pass: {", ".join(smoke)}. Identical AST implies identical behaviour on any test, so no flip is possible, '
                        f'but that is an inference, not a graded outcome.')
        pf = ('AST of extracted code (comments ignored)', same)

    elif i.startswith('gsm8k_'):
        gold = to_num(q['expected'])
        gb, ga = answer_tag_last(b['content']), answer_tag_last(a['content'])
        rec['grader'] = 'gsm8k_answer_tag_numeric_vs_pool_gold'
        rec['baseline_pass'] = to_num(gb) == gold if gb else False
        rec['arm_pass'] = to_num(ga) == gold if ga else False
        pb = prod_try(lambda: prod.score_answer(b['content'], q['expected'], q['scoring_method'], q['scoring_config']))
        pa = prod_try(lambda: prod.score_answer(a['content'], q['expected'], q['scoring_method'], q['scoring_config']))
        rec['notes'] = f'gold={q["expected"]} (question_pool.jsonl); base answer tag={gb!r}, arm={ga!r}. Production scorer cross-check (debug_scorer.exact_match): base={pb}, arm={pa}.'
        pf = ('<answer> tag value', to_num(gb) == to_num(ga) and gb is not None)

    elif suite == 'gpqa_diamond_cot':
        gold = q['expected']
        lb, la = strict_letter(b['content']), strict_letter(a['content'])
        rec['grader'] = 'gpqa_final_line_ANSWER_letter_vs_pool_gold'
        rec['baseline_pass'] = lb == gold if lb else False
        rec['arm_pass'] = la == gold if la else False
        pb = prod_try(lambda: prod.score_answer(b['content'], gold, 'multiple_choice', {'choice_labels': 'ABCD'}))
        pa = prod_try(lambda: prod.score_answer(a['content'], gold, 'multiple_choice', {'choice_labels': 'ABCD'}))
        lenb = prod._extract_multiple_choice_letter(b['content'], 'ABCD'); lena = prod._extract_multiple_choice_letter(a['content'], 'ABCD')
        rec['notes'] = (f'gold={gold} (question_pool.jsonl, multiple_choice). Strict rule = prompt contract (letter on the last line as "ANSWER: X"): '
                        f'base={lb}, arm={la}; a missing line = fail. base stop={b["stop_type"]}@{len(b["tokens"])} tok, arm stop={a["stop_type"]}@{len(a["tokens"])} tok. '
                        f'Cross-check with the LENIENT production extractor (debug_scorer.multiple_choice, which guesses the last standalone letter in a truncated reply): '
                        f'base letter={lenb} score={pb}, arm letter={lena} score={pa}.')
        if i == 'gpqa_diamond_cot_5fd3fe9084c9':
            rec['notes'] += (' The lenient "pass" for both is SPURIOUS: both replies are cut off mid-deliberation (computing 10E/15E/20E and saying no option matches 20E), '
                             'with no committed answer, and the extractor merely picks the last standalone letter in the text. Strict (and any honest) reading: no answer in either.')
        if i == 'gpqa_diamond_cot_8116937b0ca6':
            rec['notes'] += (' The flip holds under BOTH the strict and the lenient grader (lenient base letter B is a stray token, not an answer). '
                             'Baseline visible reasoning at the cap already favoured option A ("Option A matches our derivation"), so the flip is an answered-vs-cut-off difference, not a wrong-vs-right difference.')
        pf = ('ANSWER: letter (fallback: normalized final line when a letter is missing)',
              (lb == la) if (lb and la) else norm(last_line(b['content'])) == norm(last_line(a['content'])))
        rec['_lenient'] = {'base': pb, 'arm': pa}

    elif suite == 'physics':
        gold = q['expected']
        bb, ba = boxed_last(b['content']), boxed_last(a['content'])
        rec['grader'] = 'phybench_boxed_final_answer_vs_pool_gold(string-normalized)'
        nb = lambda s: re.sub(r'\\left|\\right|\\!|\\,|\\;|\s|\$|\{|\}', '', s or '').replace('\\dfrac', '\\frac')
        rec['baseline_pass'] = bool(bb) and nb(bb) == nb(gold)
        rec['arm_pass'] = bool(ba) and nb(ba) == nb(gold)
        rec['notes'] = (f'gold={gold!r} (question_pool.jsonl; production scoring_method is llm_judge = needs a model, unavailable offline). '
                        f'Mechanical fallback: last \\boxed{{}} must string-match gold. base boxed={bb!r}, arm boxed={ba!r}. '
                        f'Both outputs hit the 1600-token cap mid-derivation; neither contains "\\boxed" or even the substring "cos" (no final trajectory stated anywhere), '
                        f'so no judge could credit either - both are fails for lack of a final answer (cap artifact).')
        pf = ('\\boxed{} value (fallback: normalized final line; both lack a final answer)',
              norm(last_line(b['content'])) == norm(last_line(a['content'])))

    elif suite == 'instruction_precision':
        sb, lb_ = grade_ifeval(i, b); sa, la_ = grade_ifeval(i, a)
        rec['grader'] = 'ifeval_official_checkers(strict+loose; subset implemented)'
        rec['baseline_pass'] = all(v[0] for v in sb.values())
        rec['arm_pass'] = all(v[0] for v in sa.values())
        detail = lambda s: '; '.join(f'{k.split(":")[1]}: {"PASS" if v[0] else "FAIL"} ({v[1]})' for k, v in s.items())
        rec['notes'] = (f'Instruction ids/kwargs from question_pool.jsonl ifeval_instructions/kwargs. Implemented (re-implementation of google IFEval checkers): '
                        f'{", ".join(sb)}. STRICT base [{detail(sb)}]; arm [{detail(sa)}]. LOOSE (IFEval first/last-line + asterisk-stripped variants) all-pass: '
                        f'base={all(lb_.values())}, arm={all(la_.values())}.')
        if i == 'ifeval_3456':
            def listinfo(t):
                names = [re.sub(r'^\s*\d+\.\s*', '', x).strip('* ').strip() for x in t.split('\n') if x.strip()]
                return len(names), len(set(names))
            rec['notes'] += (f' Informational, not scored by IFEval: list length/unique base={listinfo(b["content"])}, arm={listinfo(a["content"])}. '
                             'Both give 4 italicised names where 5 were requested (prompt: "Italicize 5"); caps constraint met by both. langdetect not installed, so the english_capital language check is reduced to str.isupper().')
        pf = ('final non-empty line', norm(last_line(b['content'])) == norm(last_line(a['content'])))

    elif i == 'real_suite_v1_0003':
        rec['grader'] = 'real_suite_v1_native_substring("retrieval", case-insensitive)'
        rec['baseline_pass'] = 'retrieval' in b['content'].lower()
        rec['arm_pass'] = 'retrieval' in a['content'].lower()
        pb = prod_try(lambda: prod.score_answer(b['content'], q['expected'], q['scoring_method'], q['scoring_config']))
        pa = prod_try(lambda: prod.score_answer(a['content'], q['expected'], q['scoring_method'], q['scoring_config']))
        rec['notes'] = (f'Suite-native oracle from question_pool.jsonl: substring "{q["expected"]}" (case-insens). WEAK ORACLE: any reply containing the word passes, including a prompt echo; '
                        f'it cannot discriminate the two essays. Production scorer cross-check: base={pb}, arm={pa}. Both essays recommend RAG (+ optional light fine-tune) for the legal task; no quality judgement attempted.')
        pf = ('final non-empty line', norm(last_line(b['content'])) == norm(last_line(a['content'])))

    elif i == 'real_suite_v1_0032':
        rec['grader'] = 'real_suite_v1_native_f1(<answer> block vs pool gold, threshold 0.5)'
        pb = prod_try(lambda: prod.score_answer(b['content'], q['expected'], q['scoring_method'], q['scoring_config']))
        pa = prod_try(lambda: prod.score_answer(a['content'], q['expected'], q['scoring_method'], q['scoring_config']))
        # independent F1
        def f1(t):
            from collections import Counter
            ex = answer_tag_last(t) or last_line(t)
            p, g = norm(ex).split(), norm(q['expected']).split()
            c = sum((Counter(p) & Counter(g)).values())
            if not c: return 0.0
            pr, rc = c / len(p), c / len(g)
            return 2 * pr * rc / (pr + rc)
        fb, fa = f1(b['content']), f1(a['content'])
        rec['baseline_pass'], rec['arm_pass'] = fb >= 0.5, fa >= 0.5
        rec['notes'] = (f'Suite-native token-F1 (SQuAD-normalised) vs pool gold, threshold 0.5: base F1={fb:.3f}, arm F1={fa:.3f}. '
                        f'Production scorer cross-check: base={pb}, arm={pa}. The gold is a semicolon-joined string, so F1 is an approximate/coarse oracle; the two outputs differ only by inserted articles ("the").')
        pf = ('<answer> block, SQuAD-normalised (articles/punctuation removed)',
              norm(answer_tag_last(b['content']) or '') == norm(answer_tag_last(a['content']) or ''))
    else:
        rec['notes'] = 'no handler'

    if rec['baseline_pass'] is not None and rec['arm_pass'] is not None:
        rec['graded_flip'] = bool(rec['baseline_pass']) != bool(rec['arm_pass'])
    if pf:
        rec['proxy'] = {'label': 'PROXY: normalized answer/final-line equality of the two outputs; NOT a correctness grade',
                        'basis': pf[0], 'answers_equal': bool(pf[1])}
        rec['answers_equal_proxy'] = bool(pf[1])
    records.append(rec)

# ------------------------------------------------ flip annotations
for r in records:
    if r.get('graded_flip'):
        if r['id'] == 'gpqa_diamond_cot_8116937b0ca6':
            r['flip_kind'] = 'truncation_driven: baseline hit the 1600-token cap before writing ANSWER (fail by missing answer); arm finished at 1435 tok with ANSWER: A (=gold). Not a wrong-vs-right answer flip. Lenient production extractor result in notes.'
        elif r['id'] == 'ifeval_1481':
            r['flip_kind'] = 'content-driven: arm emitted 4 markdown bullets where exactly 2 were required (base emitted 2); sections constraint met by both.'
    r.pop('_lenient', None)

(OUT / 'stage2_grading.json').write_text(json.dumps(records, indent=1))

# ------------------------------------------------ markdown
def yn(x):
    return 'n/a' if x is None else ('PASS' if x else 'FAIL')
lines = ['# DF2-17 stage 2 - graded outcomes on the 11 divergent pairs (baseline off_A vs dflash_n7)', '',
         '"proxy" = normalized answer/final-line equality of the two outputs (labelled proxy; not a correctness grade).', '',
         '| id | suite | grader | base | arm | graded flip | answers_equal (proxy) | stop base/arm |', '|---|---|---|---|---|---|---|---|']
for r in records:
    lines.append(f"| {r['id']} | {r['suite']} | {r['grader'].split('(')[0]} | {yn(r['baseline_pass'])} | {yn(r['arm_pass'])} | "
                 f"{'n/a (ungraded)' if r['graded_flip'] is None else str(r['graded_flip']).upper()} | {r['answers_equal_proxy']} | {r['base_stop']}/{r['arm_stop']} |")
g = [r for r in records if r['graded_flip'] is not None]
lines += ['', f"Graded: {len(g)}/{len(records)}; graded flips: {sum(1 for r in g if r['graded_flip'])}; ungraded: "
          f"{', '.join(r['id'] for r in records if r['graded_flip'] is None) or 'none'}.", '', '## Notes per pair', '']
for r in records:
    lines.append(f"- **{r['id']}** - {r['notes']}" + (f" FLIP KIND: {r['flip_kind']}" if r.get('flip_kind') else ''))
(OUT / 'stage2_grading.md').write_text('\n'.join(lines) + '\n')
shutil.rmtree(WORK, ignore_errors=True)
print(json.dumps([{k: r[k] for k in ('id', 'grader', 'baseline_pass', 'arm_pass', 'graded_flip', 'answers_equal_proxy')} for r in records], indent=1))

import sys
from pathlib import Path
sys.path.insert(0, '/mnt/raid0/llm/worktrees/prep-01a16fc3-ct21/scripts/benchmark')
sys.path.insert(0, '/mnt/raid0/llm/worktrees/prep-01a16fc3-ct21/scripts/security')
import debug_scorer as native
import ct18_graders as ib2
from decision_envelope import parse_decision, score_direct, diagnostic_prefix

cfg = {'choices': ['correct', 'incorrect']}
def score(text, expected='correct', config=cfg):
    return score_direct(text, expected, 'multiple_choice', config, native.score_answer, native.AnswerParseError, parse_errors_enabled=native.EXCLUDE_UNPARSEABLE_ANSWERS)

# Positive controls reproduce both historical defects before exercising fixes.
assert native.score_answer('D|correct', 'correct', 'multiple_choice', cfg) is False
assert not ib2.grade([{'op': 'startswith', 'v': 'PINEAPPLE'}], 'D|PINEAPPLE hello')
assert score('D|correct')['correct'] is True
assert score('D|incorrect', 'incorrect')['correct'] is True
assert score('D|incorrect')['correct'] is False
assert score('D|D', 'D', {'choices':['one','two','three','four']})['correct'] is True
assert diagnostic_prefix('D|PINEAPPLE hello', 'PINEAPPLE')['matches'] is True
assert diagnostic_prefix('D|hello', 'PINEAPPLE')['matches'] is False
for line, reason in [('D|Approved','approved'),('I|brief:inspect|to:coder_escalation','delegation'),('correct','malformed'),('D|','malformed'),('D|correct\nextra','malformed'),('I|brief:|to:coder','malformed')]:
    got = score(line)
    assert got == {'status':'unobservable','reason':reason,'correct':None}, (line,got)
    assert diagnostic_prefix(line,'PINEAPPLE')['status'] == 'unobservable'
# A failed native parse cannot be silently dropped or counted correct.
old = native.EXCLUDE_UNPARSEABLE_ANSWERS
native.EXCLUDE_UNPARSEABLE_ANSWERS = True
try:
    assert score('D|No verdict was provided.')['reason'] == 'native_parse_failure'
finally:
    native.EXCLUDE_UNPARSEABLE_ANSWERS = old
assert parse_decision('D|Approved ').kind == 'approved'
print('PASS: legacy failures, direct controls, option D, unobservable outcomes, diagnostic prefix')
from decision_envelope import complete_metric
assert complete_metric([score('D|correct'),score('D|incorrect')]) == {'status':'complete','reason':None,'correct':1,'n':2}
assert complete_metric([score('D|correct'),score('D|Approved')]) == {'status':'refused','reason':'unobservable','correct':None,'n':2}
assert complete_metric([])['status'] == 'refused'
print('PASS: aggregate refuses incomplete and empty measurements')

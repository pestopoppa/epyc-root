from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
OLD=BASE/'main-comparison'
DOC='docs/reference/harness-candidates/paw-5-compile-once-candidates.md'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
colon=(OLD/'controls/fixtures/paw5-original-oracle.md').read_text()
fields = ("Compile-once candidate", "Direct-model baseline", "Comparison")
period = re.sub(r"(?m)^\*\*(.+?):\*\*", r"**\1.**", colon)
controls = [
    ("legacy-colon-accepted", colon, True, ""),
    ("period-inside-bold-accepted", period, True, ""),
    ("colon-outside-bold-accepted", re.sub(r"(?m)^\*\*(.+?):\*\*", r"**\1**:", colon), True, ""),
    ("plaintext-inline-label-accepted", re.sub(r"(?m)^\*\*(.+?):\*\*", r"\1:", colon), True, ""),
]
for label in fields:
    missing = re.sub(rf"(?m)^\*\*{re.escape(label)}\.\*\*.*\n?", "", period)
    assert missing != period
    controls.append((f"missing-{label}", missing, False, f"AssertionError: {label}"))
    empty = re.sub(rf"(?m)^(\*\*{re.escape(label)}\.\*\*).*", r"\1", period)
    assert empty != period
    controls.append((f"empty-{label}", empty, False, f"AssertionError: {label}"))
controls.extend([
    ("missing-revision", period.replace("332ceb2e14d16f2031bd17b1f7c839ce8276a24b", "0" * 40),
     False, "candidate has no pinned source"),
    ("missing-seam", period.replace("src/api/routes/chat_pipeline/repl_executor.py", "unrelated.py"),
     False, "candidate has no reviewed loop seam"),
    ("missing-prerequisite", period.replace("PAW-2", "(removed)"), False, "compilation prerequisites missing"),
    ("no-candidate", period.replace("## Candidate:", "## Other:"), False, "expected 1-3 named candidates"),
    ("excluded-json-repair", period.replace("Shadow review of ambiguous retained tool failures", "JSON repair"),
     False, "excluded JSON repair"),
])

heading=re.sub(r"(?m)^\*\*(.+?):\*\* (.+)$",r"### \1\n\n\2",colon)
assert heading != colon
controls.append(('heading-paragraphs',heading,True,''))
for field in fields:
    pattern=rf"(?ms)^### {re.escape(field)}\n.*?(?=^### |^## |\Z)"
    for kind,body in [('empty-heading',''),('empty-table','| Label | Value |\n| --- | --- |\n| | |'),('absent-heading',None)]:
        replacement='' if body is None else f'### {field}\n{body}\n\n'
        candidate,n=re.subn(pattern,replacement,heading)
        assert n>0,(field,kind)
        controls.append((kind+'-'+field,candidate,False,'AssertionError: '+field))
table_heading=heading
for field in fields:
    table_heading,n=re.subn(rf"(?ms)^### {re.escape(field)}\n.*?(?=^### |^## |\Z)",f'### {field}\n\n| Aspect | Evidence |\n| --- | --- |\n| Scope | bounded comparison |\n\n',table_heading)
    assert n>0
controls.append(('heading-nonempty-tables',table_heading,True,''))
controls.append(('heading-colon-and-closing-hashes',re.sub(r'(?m)^### (.+)$',r'### \1: ###',heading),True,''))
standalone=re.sub(r"(?m)^\*\*(.+?):\*\* (.+)$",r"**\1**:\n\n- \2",colon)
assert standalone!=colon
controls.append(('standalone-bold-label-following-bullets',standalone,True,''))
for field in fields:
    pattern=rf"(?ms)^\*\*{re.escape(field)}\*\*:\n.*?(?=^\*\*(?:Compile-once candidate|Direct-model baseline|Comparison)\*\*:|^## |\Z)"
    empty,n=re.subn(pattern,f'**{field}**:\n\n',standalone)
    assert n>0
    controls.append(('empty-standalone-label-'+field,empty,False,'AssertionError: '+field))
rows=[]
with tempfile.TemporaryDirectory(dir=HERE,prefix='controls-') as d:
    lane=Path(d);target=lane/DOC;target.parent.mkdir(parents=True)
    for name,text,expected,witness in controls:
        target.write_text(text)
        q=subprocess.run(['/usr/bin/python3','-IB',str(HERE/'oracle.py'),str(lane)],capture_output=True,text=True,timeout=10)
        assert q.returncode==(0 if expected else 1) and witness in q.stderr,(name,q.stderr)
        rows.append({'name':name,'candidate_sha256':sha(target),'rc':q.returncode,'expected':expected,'witness':witness})
(HERE/'CONTROLS.json').write_text(json.dumps({'controls':rows,'all_passed':True,'oracle_sha256':sha(HERE/'oracle.py'),'old_controls_source_sha256':sha(OLD/'verify_paw_format.py')},indent=2)+'\n')
print(len(rows),'controls PASS')

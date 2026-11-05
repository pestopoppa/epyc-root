#!/usr/bin/env python3
"""Transform an impact-row job.py: exempt [gitnexus-heap] instrumentation from the unknown-skip scan while
verifying every scope-extraction skip it reports (sr-extract-end skipped=N) is a whitespace-only tracked file
outside the impact targets, and recording those files in coverage.json."""
import sys
OLD_UNKNOWN = """    unknown=[line for i,line in enumerate(lines) if i not in covered and
             re.search(r'(?i)\\b(?:skip|skipped|skipping|omitted|truncated)\\b',line)]"""
NEW_UNKNOWN = """    # [gitnexus-heap] lines are GitNexus memory instrumentation; their skip counts are verified, not trusted.
    scope_skips=verified_scope_skips(lines,clean)
    heap={i for i,line in enumerate(lines) if line.startswith('[gitnexus-heap] ')}
    unknown=[line for i,line in enumerate(lines) if i not in covered and i not in heap and
             re.search(r'(?i)\\b(?:skip|skipped|skipping|omitted|truncated)\\b',line)]"""
OLD_RESULT = "'native_analyze_complete':True,'verbose_skip_coverage_verified':True,"
NEW_RESULT = "'scope_extract_skips':scope_skips,'native_analyze_complete':True,'verbose_skip_coverage_verified':True,"
HELPER = '''
# gitnexus dist core/ingestion/scope-resolution/pipeline/run.js: sr-extract-end skipped=N counts files for which
# extractParsedFile() returned undefined: whitespace-only source, or an extractor exception (which also logs
# "scope extraction failed for <path>"). Such files get no scope model, so require every one to be a whitespace-only
# tracked file (no symbols, so outside every impact target) and record them; anything else fails coverage.
SCOPE_EXTS={'python':('.py','.pyi'),'c':('.c','.h'),'cpp':('.cpp','.cc','.cxx','.hpp','.hh','.hxx','.h','.cu','.cuh'),
            'typescript':('.ts','.tsx','.mts','.cts'),'javascript':('.js','.jsx','.mjs','.cjs')}
def verified_scope_skips(lines,clean):
    assert 'scope extraction failed for' not in clean, 'scope extractor exception'
    starts={}; out=[]
    named=[]
    for line in lines:
        m=re.match(r'^\\[KPF_SCOPE_SKIPPED\\] (\\{.*\\})\\s*$',line)
        if m: named.append(json.loads(m.group(1)))
    for line in lines:
        if not line.startswith('[gitnexus-heap] '): continue
        m=re.search(r' sr-extract-start .*\\blang=(\\S+) files=(\\d+)\\b',line)
        if m: starts[m.group(1)]=int(m.group(2)); continue
        m=re.search(r' sr-extract-end .*\\blang=(\\S+) parsedFiles=(\\d+) preExtractedHits=\\d+ skipped=(\\d+)\\s*$',line)
        if not m:
            assert not re.search(r'(?i)skip',line), f'unparsed heap skip line: {line!r}'
            continue
        lang,parsed,skipped=m.group(1),int(m.group(2)),int(m.group(3))
        assert lang in starts and starts.pop(lang)==parsed+skipped, f'scope extract count mismatch: {line!r}'
        entry={'lang':lang,'files':parsed+skipped,'parsed':parsed,'skipped':skipped}
        if skipped:
            assert lang in SCOPE_EXTS, f'unverifiable scope skips for {lang}'
            tracked=[p for p in run(['git','ls-files','-z']).split('\\0') if p.endswith(SCOPE_EXTS[lang])]
            blank=sorted(p for p in tracked if (TREE/p).is_file() and not (TREE/p).read_bytes().strip())
            assert len(blank)>=skipped, f'{lang}: {skipped} scope skips but only {len(blank)} whitespace-only files'
            ours=[n['path'] for n in named if n.get('language')==lang]
            if ours:
                assert len(ours)==skipped and set(ours)<=set(blank), f'{lang}: named scope skips not whitespace-only'
            assert not {s for _,s in SYMBOLS}&set(blank), 'impact target file has no scope model'
            entry.update(whitespace_only_candidates=blank,named_paths=ours)
        out.append(entry)
    return out

def verified_coverage('''
LARGE = [  # progress-bar erase-line (\x1b[2K) residue interleaves blank lines inside the large-file list
    ("for following in lines[index+1:]:", "for offset,following in enumerate(lines[index+1:],index+1):"),
    ("if path: paths.append(path.group(1)); continue", "if path: paths.append(path.group(1)); covered.add(offset); continue"),
    ("if item: paths.append(item.group(1)); continue", "if item: paths.append(item.group(1)); covered.add(offset); continue"),
    ("if paths or following.strip(): break", "if following.strip(): break  # blank = ANSI erase-line residue between entries"),
    ("covered.update(range(index,index+1+len(paths)))", "covered.add(index)"),
]
def main(path):
    src=open(path).read()
    n=0
    for old,new in LARGE:
        c=src.count(old); assert c<=1, (path,old); n+=c; src=src.replace(old,new)
    assert n==4 or (n==3 and "if not following.strip(): continue\n            break" in src), (path,'large-block patch',n)
    ZERO = """    # Zero-count scope diagnostics are not skips; positive counts lack path identity.
    for i,line in enumerate(lines):
        match=re.search(r'\\bsr-extract-end\\b.*\\bskipped=(\\d+)\\b',line)
        if match:
            assert int(match.group(1)) == 0, f'unlocated scope extraction skips: {line}'
            covered.add(i)
"""
    assert src.count(ZERO)<=1; src=src.replace(ZERO,'')  # superseded by verified_scope_skips (locates every skip)
    if '[KPF_SCOPE_SKIPPED] ' in src and "sr-extract-end[^\\n]*skipped" in src:
        pass  # this job already verifies every scope skip by name (kpf131 lineage)
    else:
        assert src.count(OLD_UNKNOWN)==1 and src.count(OLD_RESULT)==1 and src.count('\ndef verified_coverage(')==1, path
        src=src.replace(OLD_UNKNOWN,NEW_UNKNOWN).replace(OLD_RESULT,NEW_RESULT).replace('\ndef verified_coverage(',HELPER,1)
    assert 'unlocated scope extraction skips' not in src, path
    open(path,'w').write(src)
if __name__=='__main__':
    for p in sys.argv[1:]: main(p)

import re, sys

def expand(text):
    if not re.fullmatch(r'[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*', text):
        raise ValueError('numeric CPU ranges required')
    xs=[]
    for part in text.split(','):
        ab=[int(v) for v in part.split('-')]
        if len(ab)==1: xs.append(ab[0])
        else:
            a,b=ab
            if b<a: raise ValueError('reversed CPU range')
            xs.extend(range(a,b+1))
    if not xs or min(xs)<0 or max(xs)>191 or len(xs)!=len(set(xs)):
        raise ValueError('CPU range outside host or duplicate')
    return sorted(xs)

def quarter(text):
    xs=expand(text)
    if len(xs)!=24 or xs!=list(range(xs[0],xs[-1]+1)) or xs[0]%24 or xs[-1]!=xs[0]+23:
        raise ValueError('exact full numeric quarter required')
    return xs

def smoke(text):
    xs=expand(text)
    if len(xs)!=2 or any(x<96 or x>183 for x in xs) or len({x%96 for x in xs})!=2:
        raise ValueError('R11 smoke needs two distinct CPUs in 96-183')
    return xs

if __name__=='__main__':
    try:
        mode, value=sys.argv[1:3]
        xs=quarter(value) if mode=='quarter' else smoke(value) if mode in ('smoke','qual') else None
        if xs is None: raise ValueError('unknown CPU validation mode')
        print(','.join(map(str,xs)))
    except Exception as e:
        print('REFUSED: '+str(e),file=sys.stderr);raise SystemExit(64)

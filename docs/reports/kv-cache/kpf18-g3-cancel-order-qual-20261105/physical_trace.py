"""Strict decoder for the *native* a1f0c8cf9 LLAMA_KV_CACHE_DEBUG=3 grids.

No allocator simulation and no inference from lengths. Incomplete, truncated,
ambiguous, or unsupported grids refuse. Each returned cell has its physical
index, native ownership character, and native position. Multi-owner M does
not identify its member sequences: callers must retain native fork telemetry.
"""
import re

HEADER = re.compile(r'find_slot: stream\[(\d+)\], n =\s*(\d+), used =\s*(\d+), head =\s*(\d+), size =\s*(\d+), n_swa =\s*(\d+)')

class TraceError(ValueError):
    pass

def snapshots(lines):
    """Decode a bounded request log slice, preserving snapshot order.

    Logger prefixes may precede headers. Native multiline grid continuation
    rows must have no prefix. Position fields are width FIVE in this image;
    positions >=100000 are unsupported rather than guessed.
    """
    current = None
    owners = []
    positions = []
    for line in lines:
        match = HEADER.search(line)
        if match:
            if current is not None:
                raise TraceError('new header before complete native grid')
            stream,n,used,head,size,swa = map(int,match.groups())
            if not 0 < size <= 4_194_304 or size % 256:
                raise TraceError('unsupported native grid size')
            if not 0 <= used <= n <= size or not 0 <= head <= size:
                raise TraceError('invalid native counters')
            current = dict(stream=stream,n=n,used=used,head=head,size=size,n_swa=swa)
            owners=[]; positions=[]
            continue
        if current is None:
            continue
        if len(owners) < current['size']:
            row = re.fullmatch(r'([0-3M.]{256}) \*\s*',line.rstrip('\n'))
            if row:
                owners.extend(row[1])
            elif not line.strip() or '[' in line[:32]:
                continue
            else:
                raise TraceError('malformed native ownership row')
            continue
        row = line.rstrip('\n').replace(' *','')
        if not row.strip():
            continue
        if len(row) != 64*5:
            # Header timestamp lines belong only before the first position row.
            if not positions and '[' in row[:32]:
                continue
            raise TraceError('ambiguous/truncated native position row')
        for offset in range(0,len(row),5):
            token=row[offset:offset+5].strip()
            if token=='.': positions.append(None)
            elif token.isdecimal(): positions.append(int(token))
            else: raise TraceError('invalid native position field')
        if len(positions)==current['size']:
            cells=list(zip(owners,positions))
            if any((own=='.') != (pos is None) for own,pos in cells):
                raise TraceError('ownership/position disagreement')
            used=sum(own!='.' for own in owners)
            last=max((i+1 for i,own in enumerate(owners) if own!='.'),default=0)
            if used!=current['used'] or last!=current['n']:
                raise TraceError('native grid/counter disagreement')
            yield {**current,'cells':cells}
            current=None
    if current is not None:
        raise TraceError('incomplete native physical grid')

def attended(snapshot, owner, *, start=0, end=32000):
    return [(i,pos) for i,(seq,pos) in enumerate(snapshot['cells'])
            if seq==owner and pos is not None and start<=pos<end]

def witness(fork,control,*,T=32000):
    """Both snapshots are native TARGET n_swa=0, before first suffix batch.

    M may be treated as the child only after independent native telemetry
    proved checkpoint fork src0->dst1 and exactly T shared cells. This API
    deliberately requires that telemetry at the caller, not invented here.
    """
    if fork['n_swa'] or control['n_swa'] or fork['size']!=control['size']:
        raise TraceError('target stream/size mismatch')
    fa=attended(fork,'M',end=T); ca=attended(control,'1',end=T)
    if len(fa)!=T or len(ca)!=T or fa!=ca:
        raise TraceError('actual attended physical index/position mismatch')
    if sorted(p for _,p in fa)!=list(range(T)):
        raise TraceError('attended prefix not bijective')
    occupancy=lambda s:[seq!='.' for seq,_ in s['cells']]
    if occupancy(fork)!=occupancy(control):
        raise TraceError('actual physical masked occupancy mismatch')
    if fork['head']!=control['head']:
        raise TraceError('actual suffix allocation head mismatch')
    return {'matched':True,'prefix_physical_index_positions':fa,
            'occupied_cells':fork['used'],'native_head':fork['head'],
            'scope':'pre-suffix target map only; suffix partitions require trace-series comparison'}

def suffix_partitions(series,owner,*,T=32000,S=4000):
    """Raw native attended map before EACH allocation; retains holes/rollback.

    The caller stops at the first decode allocation, when every suffix
    position exists. Comparing the full series proves the exact partition
    and actual physical destination of suffix tokens, not merely a sum.
    """
    result=[]
    for snap in series:
        if snap['n_swa']!=0: continue
        pairs=attended(snap,owner,start=T,end=T+S)
        if len({p for _,p in pairs})!=len(pairs):
            raise TraceError('duplicate native suffix position')
        result.append({'head':snap['head'],'suffix':pairs})
        if sorted(p for _,p in pairs)==list(range(T,T+S)):
            return result
    raise TraceError('missing complete pre-decode suffix allocation witness')

def prefix_partitions(series,owner,*,T=32000):
    result=[]
    for snap in series:
        if snap['n_swa']!=0:continue
        pairs=attended(snap,owner,end=T)
        result.append({'head':snap['head'],'prefix':pairs})
        if sorted(p for _,p in pairs)==list(range(T)):
            return result
    raise TraceError('missing complete native prefix allocation witness')

def cache_roles(series,*,allow_draft_restore=False,expected_swa=2048):
    """Classify actual native call order for THIS single-slot DFlash2 recipe.

    Target hybrid prepare emits n_swa0. Successful target decode then calls
    DFlash.process(), whose decoder prepare emits base0 followed by SWA2048.
    Both base0 caches have size393216, so n_swa alone is NOT identification.
    A checkpoint load may emit standalone SWA (PARTIAL_ONLY skips draftbase),
    accepted only where the caller explicitly permits native fork restore.
    Retries/extra contexts/changed recipe refuse instead of guessed pairing.
    """
    pending=[]
    for snap in series:
        if snap['n_swa']==0:
            pending.append(snap)
            if len(pending)>2:raise TraceError('ambiguous extra non-SWA cache snapshot')
        elif snap['n_swa']==expected_swa:
            if len(pending)==2:
                yield {'event':'forward','target':pending[0],'draft_base':pending[1],'draft_swa':snap}
                pending=[]
            elif not pending and allow_draft_restore:
                yield {'event':'draft_partial_restore','draft_swa':snap}
            else:raise TraceError('unpaired native DFlash SWA cache snapshot')
        else:raise TraceError('unexpected native SWA generation/recipe')
    if pending:raise TraceError('incomplete native target/draft forward snapshot group')

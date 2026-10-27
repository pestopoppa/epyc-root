"""Scope/coverage checks over genuine GNX results; native risk is not regraded."""
def qualify(catalog,expected_commit,tuples,contexts,impacts,status_ok):
    missing=[]; high=[]
    for symbol,file in tuples.items():
        context=contexts.get(symbol,{}) or {}; impact=impacts.get(symbol,{}) or {}
        cs=context.get('symbol',{}) or {}; target=impact.get('target',{}) or {}
        pagination=impact.get('pagination',{}) or {}
        if impact.get('risk') in {'HIGH','CRITICAL'}: high.append(symbol)
        depths=impact.get('byDepth'); counts=impact.get('byDepthCounts')
        detailed=(isinstance(depths,dict) and isinstance(counts,dict)
                  and type(impact.get('impactedCount')) is int
                  and impact['impactedCount']>=0
                  and all(type(value) is int and value>=0 for value in counts.values())
                  and all(isinstance(items,list) and len(items)==counts.get(depth)
                          for depth,items in depths.items())
                  and set(depths)==set(counts)
                  and sum(counts.values())==impact['impactedCount'])
        if (not isinstance(cs,dict) or not isinstance(target,dict) or not isinstance(pagination,dict)
            or context.get('status')!='found' or cs.get('name')!=symbol or cs.get('filePath')!=file
            or not isinstance(cs.get('uid'),str) or not cs['uid']
            or context.get('epistemic')!='exact' or context.get('error')
            or not isinstance(context.get('incoming'),dict) or not isinstance(context.get('outgoing'),dict)
            or target.get('name')!=symbol or target.get('filePath')!=file
            or impact.get('direction')!='upstream' or impact.get('risk') not in {'LOW','MEDIUM','HIGH','CRITICAL'}
            or impact.get('epistemic')!='exact' or impact.get('error') or impact.get('partial')
            or pagination.get('truncated') or not detailed or target.get('id')!=cs.get('uid')):
            missing.append(symbol)
    source_current=catalog.get('metadata_commit')==expected_commit
    complete=bool(status_ok and source_current and not missing and not high)
    return {'classification':'HIGH_CRITICAL' if high else 'QUALIFIED_NATIVE_GRAPH' if complete else 'UNKNOWN_STALE_OR_MISSING_COVERAGE',
            'source_current':source_current,'missing_or_partial_targets':missing,'high_critical':high,
            'publication_qualified':complete,'native_risk_unchanged':True}

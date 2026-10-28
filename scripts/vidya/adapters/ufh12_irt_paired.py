"""Strict projection of prospective paired IRT Spearman observations."""
import importlib.util
from pathlib import Path
from claim_tuple import ProjectionError, register
SOURCE_KIND='ufh12-irt-paired'
ADAPTER_ID='vidya.adapters.ufh12_irt_paired/v1'
AUTHORITY='measurement'
s=importlib.util.spec_from_file_location('irt_paired_capture',Path(__file__).resolve().parents[1]/'producers/ufh12_irt_paired_capture.py')
p=importlib.util.module_from_spec(s); s.loader.exec_module(p)
def native_rows(path):
 path=Path(path).resolve(); rows=p.c.load_rows(path,p.validate)
 if rows is None or len(rows)!=4 or len({x['metric'] for x in rows})!=4: raise ProjectionError('invalid paired IRT sidecar')
 return tuple({'row':r,'path':str(path)} for r in rows)
@register(SOURCE_KIND)
def project(native):
 if native not in native_rows(native['path']): raise ProjectionError('paired IRT capture does not rederive')
 try: return p.project(native['row'])
 except (ValueError,KeyError,OSError) as exc: raise ProjectionError('invalid paired IRT record') from exc

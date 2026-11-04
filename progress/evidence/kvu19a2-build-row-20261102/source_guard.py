"""Open a preflight-verified source tree and hold its identity through a build.

The caller must bind receipt_sha256 in reviewed launcher bytes and keep the
returned descriptor open while every build subprocess uses proc_path(fd).
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _identity(st):
    return {'dev': st.st_dev, 'ino': st.st_ino,
            'mode': stat.S_IMODE(st.st_mode), 'uid': st.st_uid}


def open_sealed_source(row_root, receipt_sha256, *, owner=None):
    """Validate pinned receipt, source directory identities and return open fd."""
    if owner is None: owner=os.geteuid()
    if not isinstance(receipt_sha256,str) or not _SHA.fullmatch(receipt_sha256):
        raise ValueError('invalid receipt pin')
    if not Path(row_root).is_absolute():
        raise ValueError('row root must be absolute')
    rowfd=os.open(row_root,_DIR)
    try:
        rowstat=os.fstat(rowfd)
        if rowstat.st_uid!=owner or rowstat.st_mode & 0o022:
            raise ValueError('row root not protected')
        recfd=os.open('sealed-source-receipt.json',_FILE,dir_fd=rowfd)
        try:
            rst=os.fstat(recfd)
            if not stat.S_ISREG(rst.st_mode) or rst.st_uid!=owner or rst.st_mode & 0o022:
                raise ValueError('receipt not protected')
            raw=b''
            while len(raw)<=65536:
                chunk=os.read(recfd,min(65537-len(raw),65536))
                if not chunk:break
                raw+=chunk
            if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=receipt_sha256:
                raise ValueError('receipt pin mismatch')
        finally:os.close(recfd)
        rec=json.loads(raw)
        if (not isinstance(rec,dict) or rec.get('schema')!='kvu19a2.sealed-source.v1'
            or not isinstance(rec.get('identities'),dict)
            or set(rec['identities'])!={'.','base','candidate'}
            or not isinstance(rec.get('files_sha256'),str) or not _SHA.fullmatch(rec['files_sha256'])
            or type(rec.get('file_count')) is not int or rec['file_count']<=0):
            raise ValueError('invalid receipt')
        fd=os.open('source-sealed-20261102',_DIR,dir_fd=rowfd)
        try:
            for name in ('.','base','candidate'):
                child=fd if name=='.' else os.open(name,_DIR,dir_fd=fd)
                try:
                    st=os.fstat(child)
                    if st.st_uid!=owner or st.st_mode & 0o022 or _identity(st)!=rec['identities'][name]:
                        raise ValueError('source directory identity mismatch: '+name)
                finally:
                    if child!=fd:os.close(child)
            result=fd;fd=-1
            return result
        finally:
            if fd!=-1:os.close(fd)
    finally:os.close(rowfd)


def proc_path(fd):
    if type(fd) is not int or fd<0:raise ValueError('invalid source fd')
    return Path('/proc')/str(os.getpid())/'fd'/str(fd)

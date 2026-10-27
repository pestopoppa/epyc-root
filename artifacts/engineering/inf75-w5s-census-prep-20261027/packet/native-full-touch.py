"""Touch every byte of an anonymous allocation with four native memset workers."""
import ctypes, mmap, sys
from concurrent.futures import ThreadPoolExecutor
n = int(sys.argv[1]) << 30
m = mmap.mmap(-1, n, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
              prot=mmap.PROT_READ | mmap.PROT_WRITE)
anchor = ctypes.c_char.from_buffer(m)
libc = ctypes.CDLL(None)
libc.memset.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t)
libc.memset.restype = ctypes.c_void_p
address = ctypes.addressof(anchor)
def touch(i):
    begin = n * i // 4
    end = n * (i + 1) // 4
    if libc.memset(address + begin, 1, end - begin) != address + begin:
        raise RuntimeError('native memset returned wrong address')
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(touch, range(4)))
if m[0] != 1 or m[-1] != 1:
    raise RuntimeError('native memset verification failed')
del anchor
m.close()

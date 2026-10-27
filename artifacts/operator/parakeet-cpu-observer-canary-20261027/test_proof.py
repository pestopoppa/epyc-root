import copy
from proof import check
err='''CPU_OBSERVER hooks pid=42 count=5
CPU_OBSERVER buffer pid=42 name=CPU host=1 size=100 device_type=0
CPU_OBSERVER usage pid=42 usage=1 name=CPU host=1 size=100 device_type=0
CPU_OBSERVER sched_new pid=42 devices=1 backends=1
CPU_OBSERVER device index=0 type=0 name=CPU
CPU_OBSERVER backend index=0 type=0 name=CPU
CPU_OBSERVER graph pid=42 backends=1
CPU_OBSERVER graph_backend index=0 type=0
CPU_OBSERVER direct_graph pid=42 device_type=0'''
s=[dict(time=t,pid=42,birth=7,affinity='24-25',maps={'/x':'a'},kfd_present=True,vram={'vram_0':0}) for t in (1,1.25,1.5,1.75,2)]
def test(e=err, ss=s, pins={'/x':'a'}, start=1,end=2): return check(e,ss,42,7,pins,start,end)
test()
def reject(fn):
 try: fn()
 except ValueError: return
 raise AssertionError('accepted bad proof')
for bad in (err.replace('type=0','type=1',1),err.replace('type=0','type=3',1),err.replace('CPU_OBSERVER hooks','DISABLED hooks'),err.replace('usage=1','usage=0')): reject(lambda: test(e=bad))
for field,value in (('maps',{'/foreign':'a'}),('birth',8),('vram',{'vram_0':1}),('vram',{}),('affinity','0-1')):
 ss=copy.deepcopy(s);ss[2][field]=value;reject(lambda:test(ss=ss))
reject(lambda:test(ss=s[:1]+s[4:]));reject(lambda:test(start=.1));reject(lambda:test(end=3));reject(lambda:test(pins={}))
print('CPU KFD zero accepted; GPU/ACCEL/missing hook/foreign pins/birth/window/VRAM refused: PASS')

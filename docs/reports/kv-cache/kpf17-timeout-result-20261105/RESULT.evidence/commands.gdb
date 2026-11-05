set confirm off
set startup-with-shell off
set disable-randomization off
start
python
import gdb
p=gdb.selected_inferior().pid
s=open("/proc/%d/stat"%p).read().rsplit(")",1)[1].split()
gdb.write("KPF17T_PID=%d\nKPF17T_BIRTH=%s\n"%(p,s[19]))
gdb.flush()
end
continue

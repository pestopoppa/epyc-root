# Historical allocator ELF qualification

`kpf131-old-allocator-elf-20261105` was published after four-CPU smoke PASS, rc0 `complete`. An earlier smoke refused an empty disassembly caused by using mangled selectors with demangling enabled; the corrected packet uses matching raw symbols and preserves the failed attempt. The full read-only inspection remains pending.

The row captures machine-code custody only. It does not establish native layout, offsets, historical control, task or request binding, or any model/GPU result.

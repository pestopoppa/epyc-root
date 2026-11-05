# Historical allocator ELF capture

Row `kpf131-old-allocator-elf-20261105` completed rc 0 with `ALLOCATOR_ELF_CAPTURED`. Five retained tool outputs include `find_slot`, `apply_ubatch` and its `part.0` bodies; the result records pinned ELF and tool identities and successful tool exits. [RESULT.json](RESULT.json) SHA-256 `1adbacefd71ec14ef049d31bc315fd65e5787315912507ca00698f46e7249e1d`; [archived outputs](allocator-elf.tar.gz) SHA-256 `032b6687703f7d41723c676f2bedb768cb14ebc94cd1e07483eacac9f0af9eb5`.

This preserves read-only machine-code evidence. It does not validate object offsets or physical cache layout, establish server task/slot/batch binding, or resolve a historical control. The source binding is retained digest metadata, not independent reproducible-build provenance.

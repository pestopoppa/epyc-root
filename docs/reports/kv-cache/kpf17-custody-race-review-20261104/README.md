# KPF-17 custody-race fixture review

The first proposed isolated race fixture used its own SHA-256 and inode comparisons rather than invoking the retained KPF-17 `custody.py` implementation. It cannot establish whether the actual custody checks detect mutation, and was not published. A successor must bind and exercise the actual retained implementation on private fixtures, identify the tested mutation window, and preserve unsafe or inconclusive outcomes. Even a detected pre-revalidation mutation would not prove that same-user mutation after the last check is prevented during native loading.

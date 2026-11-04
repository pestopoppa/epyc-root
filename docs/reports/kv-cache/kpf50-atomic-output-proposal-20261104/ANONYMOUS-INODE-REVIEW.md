# Anonymous-inode follow-up review

A follow-up `O_TMPFILE` sketch was considered to avoid a replaceable named temporary entry. Its first draft closes the temporary descriptor and sets it to `None` before linking `/proc/self/fd/<fd>`, so it cannot publish successfully and must not be applied. An implementation must keep the descriptor open through publication and prove that the actual filesystem supports the chosen no-replace link operation.

Anonymous-inode publication is Linux/filesystem specific. A directory writable by an adversary can still have a published entry removed or replaced; directory fsync after publication can fail after the entry becomes visible, leaving durability uncertain. The source-bound impact prerequisite and existing-output behavior decision remain open.

# KPF-18 group-3 full driver import

The pending row imports the actual disabled preload-integrated driver and its transitive modules, with an isolated empty attempt directory and source-custody checks before and after. It never calls driver main, starts a server, reads model weights or uses GPU. It reports imported module paths and callable entry points. This tests full import compatibility only, not native lifecycle, model execution, interval custody, admission, or historical control. The candidate remains disabled. Publisher smoke and full execution are pending.

# Backward-compatible shim — actual module at src/registry/registry_loader.py
import importlib as _il
import sys as _sys
_real = _il.import_module("src.registry.registry_loader")
_real.__name__ = __name__
_sys.modules[__name__] = _real

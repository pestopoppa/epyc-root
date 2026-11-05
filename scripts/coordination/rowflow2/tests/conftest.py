import os
import sys
import tempfile

from hypothesis import settings  # noqa: F401  - hard import: a missing hypothesis must ERROR, never skip
from hypothesis.configuration import set_hypothesis_home_dir

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
set_hypothesis_home_dir(tempfile.mkdtemp(prefix="rowflow2-hypothesis-"))   # never a .hypothesis dir in the tree
settings.register_profile("rowflow2", database=None, print_blob=True)
settings.load_profile("rowflow2")

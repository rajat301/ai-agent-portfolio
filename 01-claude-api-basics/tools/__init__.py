# tools/__init__.py — makes the tools/ directory a Python package and re-exports the public API
#
# Importing from the package (e.g. `from tools import get_current_time`) works because
# this file exposes those names at the package level. Without this, callers would need
# the full path: `from tools.time_tools import get_current_time`.

from tools.time_tools import get_current_time  # pull get_current_time up to the package level
from tools.math_tools import calculate  # pull calculate up to the package level

__all__ = ["get_current_time", "calculate"]  # declare the public API — controls what `from tools import *` exports

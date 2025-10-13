"""Root-level proxy_config shim.

Delegates to utils.proxy_config so that imports like `import proxy_config` work
from different working directories (scripts/tests).
"""
from utils.proxy_config import *  # noqa: F401,F403
